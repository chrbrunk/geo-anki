# geo-anki

A Python package for generating map-based Anki flashcards from real geographic
boundary data. Currently contains the package skeleton; map rendering and deck
generation will follow.

## Development

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
Run commands from the repository root.

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pre-commit install
uv run pre-commit run --all-files
uv build
```

`uv sync` installs the package in editable mode and includes the development tools.
Runtime dependencies will be added as features are implemented. Commit `uv.lock`
when changing dependencies to keep development environments reproducible.

Install the pre-commit hooks once per checkout. They run Ruff linting, formatting
checks, and ty type checking before each commit, using the versions in `uv.lock`.
Keep `uv` on your PATH when committing. Formatting checks report changes to make;
run `uv run ruff format .` to apply them.

## Layout

- `src/geo_anki/`: Python package (import as `geo_anki`).
- `tests/`: tests run with pytest.
- `outputs/`: ignored location for generated maps and decks.
