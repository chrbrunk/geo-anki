# 🌍 Geo Anki

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/managed_with-uv-DE5FE9)](https://docs.astral.sh/uv/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-FAB040?logo=pre-commit&logoColor=black)](https://pre-commit.com/)
[![pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Ruff](https://img.shields.io/badge/linting-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fchrbrunk%2Fed1d7568fa8ea07f78781ddf965f603f%2Fraw%2Fpytest-coverage-comment.json%3Fv%3D2&label=Coverage&cacheSeconds=300)](https://gist.github.com/chrbrunk/ed1d7568fa8ea07f78781ddf965f603f#file-pytest-coverage-comment-json)

## 🗺️ Overview

Generate map-based [Anki](https://apps.ankiweb.net/) flashcards from real geographic
boundary data. Choose the
subdivisions you want to learn and export a deck with embedded maps. Cards show
the country and subdivision on the front, and a highlighted map on the back.

> [!IMPORTANT]
> **Currently, only Indonesia's kabupaten (regencies) and kota (cities) are
> implemented.** These are second-level administrative divisions, below provinces.
> More countries are planned.

> [!NOTE]
> 🤖 **Built with Codex.** This repository was coded with OpenAI Codex.

## 🖼️ Example flashcard

**Front:** `Indonesia: Muaro Jambi`

**Back:** `Kabupaten Muaro Jambi — Jambi`

Here, Jambi is the province, highlighted with a pale fill and bold outline.

<img src="examples/muaro_jambi.png" alt="Map of Sumatra highlighting Muaro Jambi in orange and Jambi province with a bold outline" width="450">

## 🚀 Setup / Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).
For now, clone the repository and install its dependencies with uv:

```bash
git clone https://github.com/chrbrunk/geo-anki.git
cd geo-anki
uv sync --locked
```

Installation from PyPI via `pip` will be added later.

## 🃏 Usage

Generate a deck using the example Indonesia selection:

```bash
uv run geo_anki \
  --country indonesia \
  --targets examples/indonesia.txt \
  --output outputs/indonesia.apkg
```

`--targets` accepts your own UTF-8 text file with one kabupaten/kota name per line,
without a province. For example:

```text
Kutai Kartanegara
Muaro Jambi
```

The supplied target file is a sample selection of 10 kabupaten across several
islands. Find the [example input](examples/indonesia.txt) and
[generated deck](examples/outputs/indonesia.apkg) in [examples/](examples/).
Copy or replace the target file to choose your own subdivisions.

**🧭 Build your own selection: [targets/indonesia.txt](targets/indonesia.txt) lists
every kabupaten/kota name available in the pinned dataset, with the exact spelling
to copy into your target file.**

Boundary data downloads automatically and is cached locally. Unknown or ambiguous
names raise an error. The command produces an `.apkg` to import into Anki, PNG
maps, and a JSON manifest. Run `uv run geo_anki --help` for additional options.

## 📍 Data sources

Indonesia boundaries come from
[Indonesia-Geojson-2026](https://github.com/mashadinoor/Indonesia-Geojson-2026)
(MIT; mashadinoor and ardian28). Coverage may be incomplete or outdated.

## 🛠️ Development

After setup, install the Git hooks once per checkout:

```bash
uv run pre-commit install
```

Hooks check configuration files, merge conflicts, filename case conflicts,
debugger statements, whitespace, Ruff linting and formatting, and ty types.
Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/),
for example `feat: add a country` or `fix: correct a map label`.
To run all configured checks across the repository manually:

```bash
uv run pre-commit run --all-files
```
