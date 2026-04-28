# Contributing

Contributions are welcome. Please open an issue before submitting a PR.

## Development setup

```bash
git clone https://github.com/daudee215/ifc-slab-mesh
cd ifc-slab-mesh
uv sync --all-extras
uv run pre-commit install
```

## Running tests

```bash
uv run pytest
uv run pytest benchmarks/ --benchmark-only
```

## Code style

Enforced by `ruff` (lint) and `mypy` (types). Run before committing:

```bash
uv run ruff check . --fix
uv run mypy src/
```
