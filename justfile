@help:
    just -l -u

test threads="32":
    uv run tires get \
        --threads {{ threads }} \
        --python 3.12 \
        examples/short-manifest.toml \
        wheels

[confirm("Proceed?")]
[private]
@_bump kind:
    uv version --bump {{ kind }}
    git tag "v$(uv version --short)"
    git commit -am "update to $(uv version --short)"
    git push
    git push --tags

@bump kind:
    echo "About to perform the following update:"
    uv version --bump {{ kind }} --dry-run
    just -f {{ justfile() }} _bump {{ kind }}

clean:
    rm -rf tests/wheels dist/

publish: clean
    uv build && uv publish

lint:
    uv run ruff format
    uv run ruff check --fix

type:
    uv run ty check
