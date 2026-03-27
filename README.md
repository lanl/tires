# Tires
[![CI Status][ci-status-img]](https://github.com/lanl/tires/actions)
[![PyPI Version][pypi-version]](https://pypi.org/project/tires/)
[![PyPI Downloads][pypi-downloads]](https://pypistats.org/packages/tires)

A CLI tool to download wheels in parallel.

`tires` is a solution for mirroring packages. Tools like [`bandersnatch`][1]
will download every PyPI version of a package, which can be overkill if you
want only a single version of a package. `bandersnatch` also does not download
the dependencies. On the other hand, `pip wheel` downloads wheels for your
package and its dependencies, and nothing more, but the downloads are
sequential.

`tires` seeks to be something in the middle . `tires` compiles the dependencies
listed in a `toml` file with `uv pip compile` (fast/parallel due to `uv`),
enumerates the unique packages, then downloads and, if needed, builds the
wheels with `uvx -p <python-version> pip wheel --no-deps` in parallel. Multiple
versions of the same package, for different python versions, can be
downloaded. Wheels are built only for the current platform.

## Installation

```sh
uv tool install tires

# Or
pip install tires
```

## Usage

The following will download wheels for packages listed in `manifest.toml` (can
be named `anything.toml`) to `wheels/`.

```sh
tires get /path/to/manifest.toml /path/to/wheels/
```

## Manifest File Format

The manifest file is a TOML file with a `[packages]` table. Each package is
defined as a key under `[packages]` with a table of options.

### Options

- `versions`: A list of version specifiers (strings). Each specifier can be:
    - An exact version (e.g., "1.26.4")
    - A version range (e.g., ">=70,<73")
    - An empty string (meaning "latest")
- `python`: A list of Python version strings (e.g., ["3.10", "3.12"]) for which
  to build wheels.
- `torch-backend`: (Optional) A list of torch backends 
  (e.g., ["cu126", "auto"]) as supported by `uv`.
- `index`: (Optional) A custom package index URL.

### Examples
See the `examples/` directory for sample manifest files.

#### Basic manifest (examples/manifest.toml)

```toml
# Basic usage. Can specify a PyPI package name or github url.
[packages]
scipy = {}  # just a package name from PyPI
'git+https://github.com/lanl/tires.git' = {}  # GitHub URL to python package

# Inline specification of package versions and python versions
# The empty string triggers download of the latest numpy version.
numpy = { versions = ["2.4.1", "1.26.4", ""], python = ["3.10", "3.13"] }

# Table specification of package versions and python versions 
[packages.setuptools]
versions = [">=70,<73", ">79", ">81"] # can specify versions and bounds
python = ["3.12"] # can specify python version

# Can specify torch backend, like in uv
[packages.torch]
torch-backend = ["cu126"]
python = ["3.12"]
```

### Notes

- If `versions` is not specified, it defaults to the latest stable release version.
- If `python` is not specified, it defaults to the Python versions provided to
  the `tires get` command (or the default: "3.10 3.11 3.12 3.13 3.14").
- An empty string in `versions` (`""`) is interpreted as "latest".
- Version specifiers that do not start with an operator (like "==", ">=", etc.)
  are treated as exact versions and will be prefixed with "==".
- Git dependencies can be specified directly as a string (e.g.,
  `'git+https://github.com/lanl/tires.git' = {}`) or as a key with options.
- The `toml` file must not list the same package more than once. For example,
  the following is not allowed.

  ```toml
  numpy = { python = ["3.11"] }
  numpy = { python = ["3.10"] }
  ```

  You must rewrite as 

  ```toml
  numpy = { python = ["3.10", "3.11"] }
  ```

  However, including both `scipy` and `numpy` is fine, even though `scipy`
  depends on `numpy`.

## LANL Software Release Information
* O5084

[ci-status-img]: https://img.shields.io/github/actions/workflow/status/lanl/tires/CI.yaml?style=flat-square&label=CI
[pypi-version]: https://img.shields.io/pypi/v/tires?style=flat-square&label=PyPI
[pypi-downloads]: https://img.shields.io/pypi/dm/tires?style=flat-square&label=Downloads&color=blue
[examples-demos]: https://github.com/lanl/tires/tree/main/examples
[1]: https://bandersnatch.readthedocs.io/en/latest/
