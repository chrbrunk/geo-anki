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
uv build
```

`uv sync` installs the package in editable mode and includes the development tools.
Runtime dependencies will be added as features are implemented. Commit `uv.lock`
when changing dependencies to keep development environments reproducible.

## Layout

- `src/geo_anki/`: Python package (import as `geo_anki`).
- `tests/`: tests run with pytest.
- `outputs/`: ignored location for generated maps and decks.
