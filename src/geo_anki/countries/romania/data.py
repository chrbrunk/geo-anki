"""Public-domain Romanian county boundaries and Romanian name matching."""

import hashlib
import io
import json
import unicodedata
import warnings
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile

import geopandas as gpd

DATA_REVISION = "ca96624a56bd078437bca8184e78163e5039ad19"
DATA_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    f"{DATA_REVISION}/geojson/ne_10m_admin_1_states_provinces.geojson"
)
DATA_SHA256 = "22d0e3ad85eb3e27f17cabf8ba2d50e554fbc27a87796ff891d958185da62fb5"
DATA_ATTRIBUTION = "Made with Natural Earth (public domain); county names adapted."
LAYER = "ne_10m_admin_1_states_provinces.geojson"
MAX_LAYER_BYTES = 50_000_000

# ISO 3166-2:RO codes. Bucharest is a municipality, not a 42nd județ.
COUNTIES = {
    "AB": "Alba",
    "AG": "Argeș",
    "AR": "Arad",
    "B": "București",
    "BC": "Bacău",
    "BH": "Bihor",
    "BN": "Bistrița-Năsăud",
    "BR": "Brăila",
    "BT": "Botoșani",
    "BV": "Brașov",
    "BZ": "Buzău",
    "CJ": "Cluj",
    "CL": "Călărași",
    "CS": "Caraș-Severin",
    "CT": "Constanța",
    "CV": "Covasna",
    "DB": "Dâmbovița",
    "DJ": "Dolj",
    "GJ": "Gorj",
    "GL": "Galați",
    "GR": "Giurgiu",
    "HD": "Hunedoara",
    "HR": "Harghita",
    "IF": "Ilfov",
    "IL": "Ialomița",
    "IS": "Iași",
    "MH": "Mehedinți",
    "MM": "Maramureș",
    "MS": "Mureș",
    "NT": "Neamț",
    "OT": "Olt",
    "PH": "Prahova",
    "SB": "Sibiu",
    "SJ": "Sălaj",
    "SM": "Satu Mare",
    "SV": "Suceava",
    "TL": "Tulcea",
    "TM": "Timiș",
    "TR": "Teleorman",
    "VL": "Vâlcea",
    "VN": "Vrancea",
    "VS": "Vaslui",
}


def _read_layer(archive: ZipFile) -> bytes:
    """Read one bounded member directly, without extracting archive paths."""
    if archive.namelist() != [LAYER]:
        raise ValueError("Expected exactly one Natural Earth boundary layer.")
    if archive.getinfo(LAYER).file_size > MAX_LAYER_BYTES:
        raise ValueError("Natural Earth boundary layer is too large.")
    return archive.read(LAYER)


def _verify(content: bytes) -> None:
    """Verify both downloaded and cached source bytes against the pinned hash."""
    if len(content) > MAX_LAYER_BYTES:
        raise ValueError("Natural Earth boundary layer is too large.")
    if hashlib.sha256(content).hexdigest() != DATA_SHA256:
        raise ValueError("Dataset checksum mismatch; remove cache and retry.")


def download_data(cache_dir: Path) -> Path:
    """Cache the checksum-verified source GeoJSON in a standard boundary ZIP."""
    path = cache_dir / f"romania-{DATA_REVISION}.zip"
    if path.exists():
        with ZipFile(path) as archive:
            _verify(_read_layer(archive))
        return path
    with urlopen(DATA_URL, timeout=120) as response:
        content = response.read(MAX_LAYER_BYTES + 1)
    _verify(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(LAYER, content)
    return path


def normalize(name: str) -> str:
    """Match case, spacing, modern/legacy Romanian diacritics and plain Latin."""
    folded = "".join(
        c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)
    ).casefold()
    for dash in ("-", "–", "—"):
        folded = folded.replace(dash, " ")
    return " ".join(folded.split())


def load_data(path: Path) -> gpd.GeoDataFrame:
    """Load all 41 counties and Bucharest, excluding foreign country records.

    Local ZIP overrides must contain a compatible complete Romania layer so maps
    always show the whole country. Automatic downloads additionally verify hashes.
    """
    with ZipFile(path) as archive:
        payload = json.loads(_read_layer(archive))
    if (
        not isinstance(payload, dict)
        or payload.get("type") != "FeatureCollection"
        or not isinstance(payload.get("features"), list)
    ):
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    features = []
    for feature in payload["features"]:
        if not isinstance(feature, dict) or not isinstance(
            feature.get("properties"), dict
        ):
            raise ValueError("Malformed boundary feature.")
        if feature["properties"].get("adm0_a3") == "ROU":
            properties = feature["properties"]
            if not {"name", "iso_3166_2", "type_en"}.issubset(properties):
                raise ValueError("Missing required county fields.")
            for field in ("name", "iso_3166_2", "type_en"):
                value = properties[field]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("Missing county names, codes or types.")
            features.append(feature)
    if not features:
        raise ValueError("Missing Romanian county records.")
    layer = {"type": "FeatureCollection", "features": features}
    if "crs" in payload:
        layer["crs"] = payload["crs"]
    frame = gpd.read_file(io.BytesIO(json.dumps(layer).encode()))
    if not {"name", "iso_3166_2", "type_en"}.issubset(frame.columns):
        raise ValueError("Missing required county fields.")
    if frame.crs is None:
        raise ValueError("Missing coordinate reference system.")
    for field in ("name", "iso_3166_2", "type_en"):
        if not frame[field].map(lambda s: isinstance(s, str) and bool(s.strip())).all():
            raise ValueError("Missing county names, codes or types.")
        frame[field] = frame[field].str.strip()
    if frame.iso_3166_2.duplicated().any():
        raise ValueError("Duplicate county codes.")
    if set(frame.iso_3166_2) != {f"RO-{code}" for code in COUNTIES}:
        raise ValueError("Expected all 41 Romanian counties and Bucharest (42 units).")
    expected_types = frame.iso_3166_2.map(lambda c: "City" if c == "RO-B" else "County")
    if not frame.type_en.eq(expected_types).all():
        raise ValueError("Expected counties and the separate Bucharest municipality.")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Expected nonempty polygon geometries.")
    if (~frame.geometry.is_valid).any():
        warnings.warn("Repairing invalid Romanian county geometries.", stacklevel=2)
        frame.geometry = frame.geometry.make_valid(
            method="structure", keep_collapsed=False
        )
    if (
        frame.geometry.is_empty.any()
        or not frame.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ):
        raise ValueError("Expected nonempty polygon geometries.")
    frame["county_code"] = frame.iso_3166_2
    frame["county_name"] = frame.county_code.str.removeprefix("RO-").map(COUNTIES)
    return frame.to_crs(4326)


def select_targets(counties: gpd.GeoDataFrame, names: list[str]) -> gpd.GeoDataFrame:
    """Select Romanian/source names or ISO codes, preserving order and identity."""
    if not names:
        raise ValueError("Target list is empty.")
    canonical = counties.county_name.map(normalize)
    source_names = counties["name"].map(normalize)
    codes = counties.county_code.map(normalize)
    selected = []
    for name in names:
        key = normalize("București" if normalize(name) == "bucharest" else name)
        matches = counties.index[
            (canonical == key)
            | (source_names == key)
            | (codes == key)
            | (codes == normalize(f"RO-{name}"))
        ].tolist()
        if not matches:
            raise ValueError(f"Unknown county: {name!r}.")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous county: {name!r}.")
        index = matches[0]
        if index in selected:
            raise ValueError(f"Duplicate target: {name!r}.")
        selected.append(index)
    return counties.loc[selected].copy()
