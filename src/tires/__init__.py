import itertools
import logging
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from importlib.metadata import version as get_version
from pathlib import Path
from tempfile import NamedTemporaryFile

from rich.logging import RichHandler
from rich.progress import track
from typer import Typer

app = Typer(name="tires")

logger = logging.getLogger(__name__)

__version__ = get_version(__name__)

# Includes: "==", ">=", "<=", ">", "<", "~="
version_specifier_operators = set("=!><~")


def has_version_specifier_operator(version: str) -> bool:
    """Checks for operator in version"""
    # All that's actually needed is to check the first charachter is one of the
    # listed operators.
    return version[0] in version_specifier_operators


@app.command()
def version():
    print(__version__)


@app.command()
def get(
    manifest: Path,
    wheels_dir: Path,
    python: str = "3.10 3.11 3.12 3.13 3.14",
    threads: int = 8,
    loglevel: str = "WARNING",
):
    logging.basicConfig(
        level=loglevel.upper(),
        handlers=[RichHandler()],
        # format="%(name)s:%(levelname)-8s > %(message)s",
        datefmt="[%X]",
        format="%(message)s",
    )

    content = tomllib.loads(manifest.read_text())
    packages = content["packages"]
    default_python = python.split()
    reqs = get_all_requirements(packages, default_python, threads=threads)
    get_all_wheels(list(reqs), wheels_dir, threads=threads)


# TODO: Add --find-links?
def get_all_requirements(
    package_data: dict[str, dict],
    default_python: Iterable[str],
    threads: int,
):
    items = []
    for name, data in package_data.items():
        python = data.get("python", default_python)
        versions = data.get("versions", [None])
        index = data.get("index", [None])
        torch_backend = data.get("torch-backend", [None])
        items.extend(
            list(
                itertools.product(
                    [name],
                    python,
                    versions,
                    index,
                    torch_backend,
                )
            )
        )

    with ThreadPoolExecutor(threads) as pool:
        reqs = []
        for r in track(
            pool.map(_get_reqs, items),
            description="Enumerating",
            total=len(items),
        ):
            reqs.extend(r)

        yield from sorted(set(reqs))


def _get_reqs(args):
    return list(get_requirements(*args))


def parse_uv_pip_compile_output(lines: list[str]):
    for line in lines:
        if "==" in line:
            # regular dependency
            dep = line
        elif line.strip().startswith("# from"):
            # dependency url for dep
            url = line.replace("# from", "--index-url").strip()
            yield f"{dep} {url}"
        elif " @ git+" in line:
            # git dependency
            yield line.rsplit(" ", 1)[-1].strip()
        else:
            logger.warning(
                f"Could not parse [red]{line}[/]",
                extra={"markup": True, "highlighter": False},
            )


def get_requirements(
    pkg_name: str,
    python: str,
    version: str | None,
    index: str | None,
    torch_backend: str | None,
):
    # Write a temporary requirements.in file.
    with NamedTemporaryFile(mode="w+t", encoding="utf-8") as f:
        if version:
            if has_version_specifier_operator(version):
                pkg_name = f"{pkg_name}{version}"
            else:
                pkg_name = f"{pkg_name}=={version}"

        f.write(pkg_name)
        f.flush()

        try:
            cmd = [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "compile",
                "-p",
                python,
                f.name,
                "--no-header",
                "--no-annotate",
                "--emit-index-annotation",
            ]

            if index:
                cmd.extend(["--index", index])

            if torch_backend:
                cmd.extend(["--torch-backend", torch_backend])

            logger.debug(f"cmd: {' '.join(cmd)}")

            reqs = subprocess.run(
                cmd,
                check=True,
                text=True,
                capture_output=True,
            )

            lines = reqs.stdout.strip().split("\n")
            deps = parse_uv_pip_compile_output(lines)
            for d in deps:
                yield (python, d)

            # deps = lines[::2]
            # urls = lines[1::2]
            # for d, u in zip(deps, urls):
            #     u = u.replace("# from", " --index-url").strip()
            #     yield (python, f"{d} {u}")

        except Exception:
            info = (
                pkg_name.replace(version, "") if version else pkg_name,
                version or "latest",
                f"python=={python}",
                index or "Default PyPI",
                torch_backend or "no torch backend",
            )
            logger.warning(
                f"Could not find [red]{info}[/]",
                extra={"markup": True, "highlighter": False},
            )


def get_all_wheels(all_reqs: list[str], wheels_dir: Path, threads: int):
    wheels_dir.mkdir(exist_ok=True, parents=True)
    _get_wheels = partial(get_wheels, wheels_dir=wheels_dir)

    with ThreadPoolExecutor(threads) as pool:
        for r in track(
            pool.map(_get_wheels, all_reqs),
            description="Fetching wheels",
            total=len(all_reqs),
        ):
            pass


def get_wheels(info: tuple[str, str], wheels_dir: Path):
    python, package = info

    try:
        cmd = [
            sys.executable,
            "-m",
            "uv",
            "tool",
            "run",
            "-p",
            python,
            "pip",
            "wheel",
            "-w",
            str(wheels_dir.resolve()),
            "--no-deps",
        ] + package.split()
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        logger.warning(
            f"Could not build wheel for [red]{info}[/]",
            extra={"markup": True, "highlighter": False},
        )


def main() -> None:
    app()
