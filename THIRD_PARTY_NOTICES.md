# Third-party notices

Geo Anki's original code is licensed under the MIT license in [LICENSE](LICENSE).
Third-party boundary data, derived maps and bundled fonts retain their applicable
licenses and attribution requirements; they are not all relicensed under MIT.
This notice also applies to the example maps and Anki decks distributed with the
repository. When redistributing those assets separately, retain the applicable
notices, source references and license links with them.

The boundary source archives are downloaded at runtime rather than bundled in the
Python wheel. License statements below distinguish an upstream repository's
license from the rights in the original geometry. Unresolved provenance is noted
explicitly; this file does not establish permission where the source is unclear.

## Sources and licenses

- **Indonesia:** [boundary source](https://github.com/mashadinoor/Indonesia-Geojson-2026/tree/c95911f3f23af6e01c3bf706c80e36a9f3958588) · [MIT notice](https://github.com/mashadinoor/Indonesia-Geojson-2026/blob/c95911f3f23af6e01c3bf706c80e36a9f3958588/LICENSE). Original BIG geometry terms require confirmation.
- **Philippines:** [boundary conversion](https://github.com/faeldon/philippines-json-maps/tree/bf7060598ff5a5d160917f1dcb9622dbaef85ff7) · [MIT notice](https://github.com/faeldon/philippines-json-maps/blob/bf7060598ff5a5d160917f1dcb9622dbaef85ff7/LICENSE). Original boundaries: NAMRIA / PSA via [OCHA COD-AB](https://data.humdata.org/dataset/cod-ab-phl), [CC BY-IGO 3.0](https://creativecommons.org/licenses/by/3.0/igo/legalcode).
- **Bangladesh:** [boundary and name source](https://github.com/nuhil/bangladesh-geocode/tree/5622f68bd07a98e076edcf8100bf0db6a75b9854) · [MIT notice](https://github.com/nuhil/bangladesh-geocode/blob/5622f68bd07a98e076edcf8100bf0db6a75b9854/LICENSE). Original geometry provenance requires confirmation.
- **Germany:** [boundary conversion by Michael Kreil](https://github.com/MichaelKreil/verwaltungsgebiete/tree/fed7e454c2a618360ae152f59959d824030d45ac) · [BKG source](https://daten.gdz.bkg.bund.de/produkte/vg/) · [Datenlizenz Deutschland BY 2.0](https://www.govdata.de/dl-de/by-2-0). © GeoBasis-DE / BKG 2026 (Daten verändert).
- **Japan:** [boundary conversion by Fabio Crisci](https://github.com/piuccio/open-data-jp-prefectures-geojson/tree/513fb852832c99470e16b95a30ddd68bf3469dc0) · [MIT notice](https://github.com/piuccio/open-data-jp-prefectures-geojson/blob/513fb852832c99470e16b95a30ddd68bf3469dc0/LICENSE) · [original MLIT N03 source](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-v2_3.html). Original MLIT terms require confirmation.
- **India:** [Survey of India district collection by ramSeraph / DataMeet](https://github.com/ramSeraph/indian_admin_boundaries/releases/tag/districts) (released 2023-12-11) · [collector's CC0 notice](https://github.com/ramSeraph/indian_admin_boundaries/blob/552a971d866324f9a7fa2be6665c07e35f98af5d/LICENSE). Original Survey of India terms require confirmation; see [source notes](src/geo_anki/countries/india/SOURCES.md) for reuse guidance and historical coverage.
- **Noto Sans Bengali:** [bundled SIL OFL 1.1 notice](src/geo_anki/countries/bangladesh/fonts/OFL.txt).
- **Noto Sans Devanagari:** [upstream font](https://github.com/notofonts/noto-fonts/tree/ffebf8c1ee449e544955a7e813c54f9b73848eac/hinted/ttf/NotoSansDevanagari), [bundled SIL OFL 1.1 notice](src/geo_anki/countries/india/fonts/OFL-Devanagari.txt).
- **Geo Anki Japanese:** renamed subset of [Noto Sans CJK JP](https://github.com/notofonts/noto-cjk), [bundled SIL OFL 1.1 notice](src/geo_anki/countries/japan/fonts/GeoAnkiJapanese-LICENSE.txt).

Geo Anki's maps modify the source presentation through projection, highlights,
labels and, where applicable, simplification or cropping. Retain any required
upstream copyright and license notices when distributing derived assets; the
links above do not replace those requirements.
