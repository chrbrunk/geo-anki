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
- **Noto Sans Bengali:** [bundled SIL OFL 1.1 notice](src/geo_anki/countries/bangladesh/fonts/OFL.txt).
- **Geo Anki Japanese:** renamed subset of [Noto Sans CJK JP](https://github.com/notofonts/noto-cjk), [bundled SIL OFL 1.1 notice](src/geo_anki/countries/japan/fonts/GeoAnkiJapanese-LICENSE.txt).

Geo Anki's maps modify the source presentation through projection, highlights,
labels and, where applicable, simplification or cropping. Retain any required
upstream copyright and license notices when distributing derived assets; the
links above do not replace those requirements.
