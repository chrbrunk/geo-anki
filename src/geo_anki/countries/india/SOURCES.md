# India source and language notes

Boundaries: Survey of India, collected by ramSeraph / DataMeet, asset
`SOI_Districts.geojsonl.7z` from the [district release](https://github.com/ramSeraph/indian_admin_boundaries/releases/tag/districts).
The asset was released on 2023-12-11. This is a historical, mixed-vintage snapshot,
not a claim to India's current district inventory: for example Andhra Pradesh has
13 source districts and Sikkim has four. Later splits and renamings are not added
without corresponding geometry. Both archive and decompressed layer hashes are
pinned in `data.py`, since the upstream release tag itself can move.

There are 742 source features: 731 LGD-coded district records covering 36 states
and union territories, plus 11 uncoded context/dispute polygons. Only the coded
records are selectable. The others remain source context, never invented targets.
Maps preserve the source's boundary depiction, including disputed areas; they do
not express a position on sovereignty. Invalid polygon topology is repaired with
a warning; non-polygonal/collapsed results are rejected.

The collector provides a [CC0 notice](https://github.com/ramSeraph/indian_admin_boundaries/blob/552a971d866324f9a7fa2be6665c07e35f98af5d/LICENSE)
and cites India's 2021 Geospatial Guidelines allowing display/printing of SoI
boundary data. This does not independently confirm every original SoI term.
Keep the original-source attribution with derived maps and decks. Display changes
include projection, highlighting, city labels, topology repair and curated names.

`names.py` contains human-curated native district spellings keyed by source LGD
codes, rather than automatic transliteration. They follow the source's historical
district identities. They are editorial labels, not an official multilingual LGD
export. Review spelling changes together with the corresponding target/code.

Front languages: Hindi in Himachal Pradesh, Chandigarh, Uttarakhand, Haryana,
Delhi, Rajasthan, Uttar Pradesh, Bihar, Jharkhand, Chhattisgarh and Madhya Pradesh;
Marathi in Maharashtra; Konkani in Goa; Nepali in Sikkim; Bengali in West Bengal
and Tripura. These are state-wide conventions, not district-level language claims.
Assam uses English by explicit user choice. Other states and multilingual
territories use English. No required native name silently falls back to English.
Backs and map subtitles are always English. Target selection accepts source
English names, native names, state-qualified names and unpadded LGD district codes.
Full-list targets include a state suffix only to resolve repeated district names.

Noto Sans Devanagari Regular is bundled unchanged from
`notofonts/noto-fonts` commit `ffebf8c1ee449e544955a7e813c54f9b73848eac`.
The existing bundled Noto Sans Bengali is reused. Both fonts and their OFL notices
are embedded in India decks; CSS explicitly provides both fonts as fallbacks.
Map titles use the appropriate font and language-aware text shaping.

Example generation from the checkout:

```bash
uv run --locked geo_anki --country india --targets examples/india.txt \
  --output examples/outputs/india.apkg
```
