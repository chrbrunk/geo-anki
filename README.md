# 🌍 Geo Anki

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/geo-anki)](https://pypi.org/project/geo-anki/)
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

The primary goal is to help you learn geography for
[GeoGuessr](https://www.geoguessr.com/), which guides the selection of countries
and subdivisions supported below.

### 🌐 Current country coverage

- **Indonesia:** kabupaten (regencies) and kota (cities), below provinces.
- **Philippines:** provinces.
- **Bangladesh:** districts.
- **Germany:** Landkreise (districts) and kreisfreie Städte (independent cities).
- **Japan:** prefectures.
- **India:** districts.
- **Romania:** counties (județe) and the municipality of Bucharest.

More countries are planned.

> [!NOTE]
> 🤖 **Built with Codex.** This repository was coded with OpenAI Codex.

## 🚀 Getting started

Geo Anki is available on [PyPI](https://pypi.org/project/geo-anki/).

- To install Geo Anki, see [Installation](#-installation).
- To create a deck, see [Usage](#-usage).

## 🖼️ Example flashcards

### Indonesia

**Front:** `Indonesia: Muaro Jambi`

**Back:** `Kabupaten Muaro Jambi — Jambi`

Here, Jambi is the province, highlighted with a pale fill and bold outline.

<img src="examples/images/muaro_jambi.png" alt="Map of Sumatra highlighting Muaro Jambi in orange and Jambi province with a bold outline" width="450">

### Philippines

**Front:** `Philippines: Camarines Sur`

**Back:** `Camarines Sur`

Camarines Sur is highlighted in orange on a map of the whole Philippines.

<img src="examples/images/camarines_sur.png" alt="Map of the Philippines highlighting Camarines Sur on Luzon in orange" width="450">

The map also names a reference city or town for the province.

### Bangladesh

**Front:** `Bangladesh: ঢাকা`

**Back:** `Dhaka`

Dhaka district is highlighted in orange on a map of the whole country, with
reference cities marked. Card fronts use the English country name followed by
the Bengali district name; map titles show both Bengali and English names.

<img src="examples/images/dhaka.png" alt="Map of Bangladesh highlighting Dhaka district, with a Bengali and English title and reference cities" width="450">

### Germany

**Front:** `Germany: Nordfriesland`

**Back:** `Kreis Nordfriesland — Schleswig-Holstein`

The district is highlighted on a map of its entire Bundesland, with fixed
reference cities for that state.

<img src="examples/images/nordfriesland.png" alt="Map of Schleswig-Holstein highlighting Landkreis Nordfriesland with reference cities" width="450">

### Japan

**Front:** `Japan: 広島県`

**Back:** `Hiroshima`

Hiroshima is highlighted on a map of Japan's main islands, with reference cities
and Okinawa in a boxed inset. Remote southern and southeastern islands are omitted.
Card fronts use Japanese prefecture names; map titles show Japanese and English.

<img src="examples/images/hiroshima.png" alt="Map of Japan highlighting Hiroshima, with reference cities and a boxed Okinawa inset" width="450">

### India

**Front:** `India: वाराणसी`

**Back:** `Varanasi — Uttar Pradesh`

Varanasi is highlighted on a map of Uttar Pradesh, with reference cities marked.

<img src="examples/images/varanasi.png" alt="Map of Uttar Pradesh highlighting Varanasi, with Devanagari and English titles and reference cities" width="450">

District names on fronts use Devanagari in the Hindi-language states, Maharashtra,
Goa and Sikkim; Bengali in West Bengal and Tripura; and English elsewhere.

### Romania

**Front:** `Romania: Bistrița-Năsăud`

**Back:** `Bistrița-Năsăud`

Bistrița-Năsăud is highlighted on a map of the whole country, with reference
cities marked.

<img src="examples/images/bistrita_nasaud.png" alt="Map of Romania highlighting Bistrița-Năsăud county with reference cities" width="450">

## 📦 Installation

Requires Python 3.12+. Install the current release from PyPI:

```bash
pip install geo-anki
```

For development installation, see [Development](#-development).

## 🃏 Usage

Generate a deck using the example Indonesia selection:

```bash
geo_anki \
  --country indonesia \
  --targets examples/indonesia.txt \
  --output outputs/indonesia.apkg
```

`--targets` accepts your own UTF-8 text file with one subdivision name per line.
For Indonesia, use kabupaten/kota names without a province. For example:

```text
Kutai Kartanegara
Muaro Jambi
```

Each supported country has a sample selection of 10 subdivisions in
[examples/](examples/), with generated decks in
[examples/outputs/](examples/outputs/):

- **Indonesia:** [example input](examples/indonesia.txt) ·
  [generated deck](examples/outputs/indonesia.apkg)
- **Philippines:** [example input](examples/philippines.txt) ·
  [generated deck](examples/outputs/philippines.apkg)
- **Bangladesh:** [example input](examples/bangladesh.txt) ·
  [generated deck](examples/outputs/bangladesh.apkg)
- **Germany:** [example input](examples/germany.txt) ·
  [generated deck](examples/outputs/germany.apkg)
- **Japan:** [example input](examples/japan.txt) ·
  [generated deck](examples/outputs/japan.apkg)
- **India:** [example input](examples/india.txt) ·
  [generated deck](examples/outputs/india.apkg)
- **Romania:** [example input](examples/romania.txt) ·
  [generated deck](examples/outputs/romania.apkg)

Copy or edit an example input to choose your own subdivisions.

**🧭 Build your own selection: [targets/](targets/) contains the full lists,
with the exact dataset spellings to copy into your target file.**

- **Indonesia:** [kabupaten/kota names](targets/indonesia.txt)
- **Philippines:** [province names](targets/philippines.txt)
- **Bangladesh:** [district names](targets/bangladesh.txt)
- **Germany:** [district names](targets/germany.txt)
- **Japan:** [prefecture names](targets/japan.txt)
- **India:** [district names](targets/india.txt)
- **Romania:** [county and municipality names](targets/romania.txt)

> [!TIP]
> **Create a custom target list with an AI chatbot.** Ask it to filter a list from
> [targets/](targets/), for example, "only Java kabupaten & kota", and save the
> result as your `--targets` file.

Boundary data downloads automatically and is cached locally. Unknown or ambiguous
names raise an error. The command produces an `.apkg` to import into Anki, PNG
maps, and a JSON manifest. Run `geo_anki --help` for additional options.

### Country-specific details

For Bangladesh, target files accept either Bengali or English district names.

For Japan, target files accept English or Japanese prefecture names (including
Japanese names without their suffix) and two-digit JIS codes. Card fronts use
the Japanese name, while backs show its English name and a map with reference
cities and a boxed Okinawa inset. Remote southern and southeastern islands are
omitted. Map titles show both names.

For Germany, a shared name such as `München` selects the Landkreis;
`München (kreisfreie Stadt)` selects the separate city. Official five-digit
district codes (AGS) are also accepted.

For India, targets accept English or supported native district names, names
qualified as `District — State`, or LGD district codes. Fronts use Devanagari in
the Hindi-language states, Maharashtra, Goa and Sikkim; Bengali in West Bengal
and Tripura; and English elsewhere. Backs show the English district and state
or union territory, with a map of that state or territory.

For Romania, targets accept Romanian names with or without diacritics, ISO county
codes, and `Bucharest` for `București`. All 41 counties and Bucharest are supported;
maps always show the whole country.

## 📍 Data sources

Geo Anki's code is MIT-licensed; third-party data and fonts retain their own terms.
See [Third-party notices](THIRD_PARTY_NOTICES.md) for source and license links,
attribution, and outstanding source-license verification.

Indonesia boundaries come from
[Indonesia-Geojson-2026](https://github.com/mashadinoor/Indonesia-Geojson-2026)
(MIT; mashadinoor and ardian28). Coverage may be incomplete or outdated.

Philippines boundaries come from
[philippines-json-maps](https://github.com/faeldon/philippines-json-maps)
(PSGC 3Q 2026; MIT maps by James Faeldon), based on NAMRIA and PSA boundaries via
[OCHA COD-AB](https://data.humdata.org/dataset/cod-ab-phl)
([CC BY-IGO 3.0](https://creativecommons.org/licenses/by/3.0/igo/)).

Bangladesh district boundaries and bilingual names come from
[bangladesh-geocode](https://github.com/nuhil/bangladesh-geocode)
(MIT; Nuhil Mehdy). Bengali text uses the bundled Noto Sans Bengali font
([SIL Open Font License 1.1](src/geo_anki/countries/bangladesh/fonts/OFL.txt)).

Germany uses BKG VG250 state and district boundaries (2026-01-01), converted to
GeoJSON by [Michael Kreil](https://github.com/MichaelKreil/verwaltungsgebiete).
© GeoBasis-DE / BKG 2026 (Daten verändert), licensed under
[Datenlizenz Deutschland – Namensnennung 2.0](https://www.govdata.de/dl-de/by-2-0).

Japan prefecture boundaries come from MLIT National Land Numerical Information
(N03, 2019-01-01), converted by Fabio Crisci in
[open-data-jp-prefectures-geojson](https://github.com/piuccio/open-data-jp-prefectures-geojson)
(MIT conversion; [MLIT source and terms](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-v2_3.html)).
Japanese text uses a renamed subset of Noto Sans CJK JP, bundled under the
[SIL Open Font License 1.1](src/geo_anki/countries/japan/fonts/GeoAnkiJapanese-LICENSE.txt).

India uses Survey of India boundaries from
[ramSeraph / DataMeet's district collection](https://github.com/ramSeraph/indian_admin_boundaries/releases/tag/districts),
released 2023-12-11: 731 districts in a historical snapshot, excluding later changes.
Native names are curated; bundled Noto Sans Devanagari and Noto Sans Bengali fonts
use SIL OFL 1.1. See [source notes](src/geo_anki/countries/india/SOURCES.md) for
coverage and licensing details.

Romania county boundaries come from [Natural Earth's public-domain 1:10m admin-1
layer](https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19).
Romanian names retain their diacritics; boundaries are generalized for display.

## 💻 Development

Clone the repository and install its dependencies with
[uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/chrbrunk/geo-anki.git
cd geo-anki
uv sync --locked
```

From a repository checkout, use `uv run geo_anki` instead of `geo_anki` for
the commands in [Usage](#-usage).

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

Tox tests the built wheel with independently resolved dependencies on Python
3.12–3.15 in CI, without using `uv.lock`. To run locally (requires those Python
versions), use `uvx tox`; for just Python 3.12, use `uvx tox -e py312`.
