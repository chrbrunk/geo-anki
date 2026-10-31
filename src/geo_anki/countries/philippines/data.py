import hashlib
import io
import unicodedata
import warnings
from difflib import get_close_matches
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd

# PSGC 3Q 2026; province boundaries from NAMRIA/PSA via OCHA COD-AB.
DATA_REVISION = "bf7060598ff5a5d160917f1dcb9622dbaef85ff7"
DATA_URL = (
    "https://codeload.github.com/faeldon/philippines-json-maps/zip/" + DATA_REVISION
)
DATA_SHA256 = "53f7340d73272920cdb2f2ba2d5eaf8efed850b60a5f6eb0f5890745b4dad1f4"
DATA_ATTRIBUTION = (
    "Boundaries: NAMRIA / PSA via OCHA COD-AB (CC BY-IGO 3.0); "
    "JSON maps: James Faeldon (MIT)."
)


def download_data(cache_dir: Path) -> Path:
    """Download or reuse the pinned, checksum-verified Philippines archive.

    Args:
        cache_dir: Directory for the downloaded ZIP.

    Returns:
        Path to the verified archive.

    Raises:
        ValueError: The downloaded or cached archive fails checksum verification.
    """
    path = cache_dir / f"philippines-{DATA_REVISION}.zip"
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
    """Normalize Unicode, case, and whitespace for province matching.

    Args:
        name: Province name to normalize.

    Returns:
        Normalized name with single spaces between words.
    """
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def load_data(path: Path) -> gpd.GeoDataFrame:
    """Load provinces and non-province context areas from regional GeoJSON layers.

    Args:
        path: ZIP containing medium-resolution province/district layers.

    Returns:
        Validated boundaries in EPSG:4326, including non-province map context.

    Raises:
        ValueError: Required layers, names, codes, CRS, or polygons are invalid.
    """
    layers = []
    with ZipFile(path) as archive:
        members = [
            member
            for member in archive.infolist()
            if Path(member.filename).parts[-4:-1] == ("geojson", "regions", "medres")
            and Path(member.filename).name.startswith("provdists-region-")
            and Path(member.filename).suffix == ".json"
        ]
        if not members or len({m.filename for m in members}) != len(members):
            raise ValueError("Expected unique province/district layers in ZIP.")
        for member in sorted(members, key=lambda m: m.filename):
            if member.file_size > 20_000_000:
                raise ValueError(f"Boundary layer is too large: {member.filename}.")
            frame = gpd.read_file(io.BytesIO(archive.read(member)))
            if frame.empty or not {"adm2_en", "adm2_psgc", "geo_level"}.issubset(
                frame.columns
            ):
                raise ValueError("Missing records or required boundary fields.")
            if frame.crs is None:
                raise ValueError("Missing coordinate reference system.")
            if frame.adm2_en.isna().any() or frame.adm2_psgc.isna().any():
                raise ValueError("Missing boundary names or codes.")
            frame["adm2_en"] = frame.adm2_en.astype(str).str.strip()
            frame["adm2_psgc"] = frame.adm2_psgc.astype(str)
            if (frame.adm2_en == "").any() or (frame.adm2_psgc == "").any():
                raise ValueError("Empty boundary names or codes.")
            if (~frame.geometry.is_valid).any():
                warnings.warn(
                    f"Repairing invalid geometries in {member.filename}.", stacklevel=2
                )
                frame.geometry = frame.geometry.make_valid()
            if (
                frame.geometry.isna().any()
                or frame.geometry.is_empty.any()
                or not frame.geom_type.isin(["Polygon", "MultiPolygon"]).all()
            ):
                raise ValueError("Expected nonempty polygon geometries.")
            layers.append(frame.to_crs(4326))
    boundaries = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True), crs=4326)
    provinces = boundaries[boundaries.geo_level == "Prov"]
    if provinces.empty:
        raise ValueError("Dataset contains no provinces.")
    if boundaries.adm2_psgc.duplicated().any():
        raise ValueError("Duplicate boundary codes in dataset.")
    if provinces.adm2_en.map(normalize).duplicated().any():
        raise ValueError("Duplicate province names in dataset.")
    return boundaries


def select_targets(boundaries: gpd.GeoDataFrame, names: list[str]) -> gpd.GeoDataFrame:
    """Select provinces by name, preserving request order and excluding districts.

    Args:
        boundaries: Validated province and context boundaries.
        names: Requested province names.

    Returns:
        Copy of matched provinces in request order.

    Raises:
        ValueError: Names are empty, unknown, ambiguous, or duplicated.
    """
    if not names:
        raise ValueError("Target list is empty.")
    provinces = boundaries[boundaries.geo_level == "Prov"]
    keys = provinces.adm2_en.map(normalize)
    selected = []
    seen = set()
    for name in names:
        key = normalize(name)
        matches = provinces.index[keys == key].tolist()
        if not matches:
            suggestions = get_close_matches(key, keys.tolist(), n=3)
            raise ValueError(f"Unknown province: {name!r}. Similar: {suggestions}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous province: {name!r}; dataset needs review.")
        if key in seen:
            raise ValueError(f"Duplicate target: {name!r}.")
        seen.add(key)
        selected.append(matches[0])
    return provinces.loc[selected].copy()
