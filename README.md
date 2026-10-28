# geo-anki

A Python package for generating map-based Anki flashcards from real geographic
boundary data. Indonesia is the first supported country.

## Generate an Indonesia deck

```bash
uv sync --locked
uv run python -m geo_anki.scripts.run \
  --country indonesia \
  --targets examples/indonesia.txt \
  --output outputs/indonesia.apkg
```

The runner downloads and caches a pinned boundary ZIP automatically. Subsequent
runs reuse the checksum-verified cache. To supply your own ZIP with the same schema,
pass `--data path/to/indonesia.zip`. Change the download location with `--cache-dir`
and the Anki deck name with `--deck-name`.

The UTF-8 target file contains one kabupaten/kota name per line, without a province.
Blank lines and lines starting with `#` are ignored. Matching ignores case and extra
whitespace, but requires the full dataset name: for example, `Jambi` and `Kota Jambi`
identify different subdivisions. Unknown, ambiguous, or duplicate targets cause an
error before maps are generated; similar names are suggestions, never auto-selected.

Outputs include the `.apkg`, individual PNGs in `<deck-name>_maps/` alongside it,
and a JSON manifest recording targets and the dataset checksum. Import the `.apkg`
into Anki. The front shows `Indonesia: <name>`; the back shows the province and map.
Stable note IDs support updates when importing later batches. Keep the deck name
unchanged to keep adding to the same deck.

Java, Sulawesi, Kalimantan, and Sumatra have island-wide contexts, province outlines,
and reference cities. Java includes Madura and the other islands belonging to its
six provinces. Sulawesi includes the islands belonging to its six provinces.
Kalimantan covers the Indonesian portion of Borneo. Sumatra includes Bangka
Belitung and excludes Kepulauan Riau. Other provinces currently use province-wide
framing without configured reference cities. Configure contexts and cities in
`countries/indonesia/regions.py`.

### Boundary source and limitations

The default is the third-party
[Indonesia-Geojson-2026](https://github.com/mashadinoor/Indonesia-Geojson-2026)
dataset at revision `c95911f3f23af6e01c3bf706c80e36a9f3958588` (MIT, credit to
mashadinoor and ardian28; upstream cites BIG). It contains 38 provinces and 507
subdivision records. It is simplified geography and is not guaranteed to be a
complete or current official administrative inventory. Name validation checks
against this dataset. Invalid province geometries are repaired with a warning;
empty or non-polygon results are rejected. Both shapes and city points are
projected together for plotting. Custom datasets must provide province `PROVINSI`
and subdivision `WADMKK` / `WADMPR` fields.

Tests inspect generated Anki notes and embedded media. Importing into the actual
Anki application remains a manual compatibility check.

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
- `examples/indonesia.txt`: initial two-card selection.
- `outputs/`: ignored location for generated maps and decks.
