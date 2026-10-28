# geo-anki

Generate map-based Anki flashcards from real geographic boundary data. Choose the
subdivisions you want to learn and export an Anki deck with embedded maps.
Cards show the country and subdivision on the front, and a highlighted map on the
back.

Currently, only Indonesia is implemented. More countries are planned.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
```

## Usage

Example for Indonesia:

```bash
uv run python -m geo_anki.scripts.run \
  --country indonesia \
  --targets examples/indonesia.txt \
  --output outputs/indonesia.apkg
```

The target file contains one kabupaten/kota name per line, without a province:

```text
Kutai Kartanegara
Muaro Jambi
```

Boundary data downloads automatically and is cached locally. Unknown or ambiguous
names raise an error. The command produces an `.apkg` to import into Anki, PNG
maps, and a JSON manifest. Use `--help` for additional options.

Indonesia boundaries come from
[Indonesia-Geojson-2026](https://github.com/mashadinoor/Indonesia-Geojson-2026)
(MIT; mashadinoor and ardian28). Coverage may be incomplete or outdated.

## Development

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
