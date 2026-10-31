import hashlib
import io
import json
import unicodedata
import warnings
from difflib import get_close_matches
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import geopandas as gpd

DATA_REVISION = "5622f68bd07a98e076edcf8100bf0db6a75b9854"
DATA_URL = "https://codeload.github.com/nuhil/bangladesh-geocode/zip/" + DATA_REVISION
DATA_SHA256 = "51a4b6a6cbd7b3917a32b99f67e4dc9b52924d7dfd6cb06007f6e1b4c7f4b355"
DATA_ATTRIBUTION = "District data: Nuhil Mehdy / bangladesh-geocode (MIT)."

# Reconcile the archive's boundary names with its bilingual reference tables.
NAME_ALIASES = {
    "barisal": "Barishal",
    "bogra": "Bogura",
    "brahamanbaria": "Brahmanbaria",
    "chittagong": "Chattogram",
    "comilla": "Cumilla",
    "coxsbazar": "Cox's Bazar",
    "jessore": "Jashore",
    "jhalokati": "Jhalakathi",
    "maulvibazar": "Moulvibazar",
    "nawabganj": "Chapainawabganj",
    "netrakona": "Netrokona",
}


def download_data(cache_dir: Path) -> Path:
    """Download or reuse a pinned, checksum-verified Bangladesh archive.

    Args:
        cache_dir: Directory for the downloaded ZIP.

    Returns:
        Path to the verified archive.

    Raises:
        ValueError: The downloaded or cached archive fails checksum verification.
    """
    path = cache_dir / f"bangladesh-{DATA_REVISION}.zip"
    if path.exists():
        content = path.read_bytes()
    else:
        with urlopen(DATA_URL, timeout=120) as response:
            content = response.read(50_000_001)
    if hashlib.sha256(content).hexdigest() != DATA_SHA256:
        raise ValueError(f"Dataset checksum mismatch: {path}; remove it and retry.")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return path


def normalize(name: str) -> str:
    """Normalize Unicode, case, and whitespace for Bengali and English matching.

    Args:
        name: District name to normalize.

    Returns:
        Normalized name with single spaces between words.
    """
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def canonical_name(name: str) -> str:
    """Resolve known legacy English district names.

    Args:
        name: Bengali, English, or legacy English district name.

    Returns:
        Current English spelling for known aliases, otherwise the original name.
    """
    return NAME_ALIASES.get(normalize(name), name.strip())


def _read_member(archive: ZipFile, suffix: str) -> bytes:
    """Read one bounded archive member without extracting paths.

    Args:
        archive: Open source archive.
        suffix: Required path relative to the archive's repository directory.

    Returns:
        Contents of the unique matching member.

    Raises:
        ValueError: The layer is missing, duplicated, or oversized.
    """
    members = [m for m in archive.infolist() if m.filename.endswith("/" + suffix)]
    if len(members) != 1 or members[0].file_size > 20_000_000:
        raise ValueError(f"Expected one reasonably sized {suffix} in ZIP.")
    return archive.read(members[0])


def _read_table(archive: ZipFile, name: str) -> list[dict]:
    """Read a reference table from the source's phpMyAdmin JSON export.

    Args:
        archive: Open source archive.
        name: Table and directory name.

    Returns:
        Table records as dictionaries.

    Raises:
        ValueError: The export is malformed, empty, or contains duplicate tables.
    """
    payload = json.loads(_read_member(archive, f"{name}/{name}.json"))
    if not isinstance(payload, list):
        raise ValueError(f"Invalid {name} table export.")
    tables = [
        p
        for p in payload
        if isinstance(p, dict) and p.get("name") == name and p.get("type") == "table"
    ]
    if (
        len(tables) != 1
        or not isinstance(tables[0].get("data"), list)
        or not tables[0]["data"]
    ):
        raise ValueError(f"Expected one nonempty {name} table.")
    rows = tables[0]["data"]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Invalid records in {name} table.")
    return rows


def load_data(path: Path) -> gpd.GeoDataFrame:
    """Join district boundaries to verified Bengali and English district names.

    Args:
        path: ZIP with district GeoJSON and district/division reference tables.

    Returns:
        Validated district polygons in EPSG:4326 with IDs and bilingual names.

    Raises:
        ValueError: Layers, names, IDs, joins, CRS, or polygons are invalid.
    """
    with ZipFile(path) as archive:
        frame = gpd.read_file(
            io.BytesIO(_read_member(archive, "geojson/districts.geojson"))
        )
        rows = _read_table(archive, "districts")
        division_rows = _read_table(archive, "divisions")
    if frame.empty or not {"ADM2_EN"}.issubset(frame.columns):
        raise ValueError("Missing records or required district boundary fields.")
    if frame.crs is None:
        raise ValueError("Missing coordinate reference system.")
    if (
        frame.ADM2_EN.isna().any()
        or (frame.ADM2_EN.astype(str).str.strip() == "").any()
    ):
        raise ValueError("Missing district boundary names.")
    divisions = {}
    for row in division_rows:
        if not all(
            isinstance(row.get(k), str) and row[k].strip() for k in ("id", "name")
        ):
            raise ValueError("Missing division names or IDs.")
        if row["id"] in divisions:
            raise ValueError("Duplicate division IDs.")
        divisions[row["id"]] = row["name"].strip()
    records = {}
    ids = set()
    bengali_names = set()
    for row in rows:
        fields = ("id", "name", "bn_name", "division_id")
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in fields):
            raise ValueError("Missing district IDs or bilingual names.")
        if not any("\u0980" <= char <= "\u09ff" for char in row["bn_name"]):
            raise ValueError("Expected a Bengali district name.")
        name = canonical_name(row["name"])
        key = normalize(name)
        bn_name = normalize(row["bn_name"])
        if key in records or row["id"] in ids or bn_name in bengali_names:
            raise ValueError("Duplicate district names or IDs.")
        if row["division_id"] not in divisions:
            raise ValueError("District refers to an unknown division.")
        records[key] = {
            "district_id": row["id"],
            "name_en": name,
            "name_bn": unicodedata.normalize("NFC", row["bn_name"].strip()),
            "division": divisions[row["division_id"]],
        }
        ids.add(row["id"])
        bengali_names.add(bn_name)
    keys = frame.ADM2_EN.map(lambda name: normalize(canonical_name(name)))
    if keys.duplicated().any():
        raise ValueError("Duplicate district boundaries.")
    if set(keys) != set(records):
        raise ValueError("District boundaries and bilingual names do not match.")
    for field in ("district_id", "name_en", "name_bn", "division"):
        frame[field] = keys.map(lambda key: records[key][field])
    if (~frame.geometry.is_valid).any():
        warnings.warn("Repairing invalid district geometries.", stacklevel=2)
        frame.geometry = frame.geometry.make_valid()
    if (
        frame.geometry.isna().any()
        or frame.geometry.is_empty.any()
        or not frame.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ):
        raise ValueError("Expected nonempty polygon geometries.")
    return frame.to_crs(4326)


def select_targets(districts: gpd.GeoDataFrame, names: list[str]) -> gpd.GeoDataFrame:
    """Select districts by Bengali or English names, including legacy spellings.

    Args:
        districts: Validated bilingual district boundaries.
        names: Requested names in card order.

    Returns:
        Copy of matched districts in request order.

    Raises:
        ValueError: Names are empty, unknown, ambiguous, or duplicated.
    """
    if not names:
        raise ValueError("Target list is empty.")
    english = districts.name_en.map(normalize)
    bengali = districts.name_bn.map(normalize)
    selected = []
    seen = set()
    for name in names:
        key = normalize(canonical_name(name))
        matches = districts.index[(english == key) | (bengali == key)].tolist()
        if not matches:
            suggestions = get_close_matches(
                key, english.tolist() + bengali.tolist(), n=3
            )
            raise ValueError(f"Unknown district: {name!r}. Similar: {suggestions}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous district: {name!r}; dataset needs review.")
        index = matches[0]
        if index in seen:
            raise ValueError(f"Duplicate target: {name!r}.")
        seen.add(index)
        selected.append(index)
    return districts.loc[selected].copy()
