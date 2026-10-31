import hashlib
import io
import unicodedata
import warnings
from difflib import get_close_matches
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import brotli
import geopandas as gpd

DATA_REVISION = "fed7e454c2a618360ae152f59959d824030d45ac"
DATA_VINTAGE = "2026-01-01"
DATA_URL = (
    "https://raw.githubusercontent.com/MichaelKreil/verwaltungsgebiete/"
    f"{DATA_REVISION}/data/{DATA_VINTAGE}"
)
DATA_FILES = {
    "1_bundeslaender.geojson.br": (
        "ca41cefdb37536e93bb4f5ca53d1d226bcbf28df4fc564442c1c1d2fe94fda2f"
    ),
    "3_kreise.geojson.br": (
        "5de37c39ea217a50f32a74a01366cd2cd050455137c86ad1c8907301b59432f4"
    ),
}
DATA_ATTRIBUTION = "© GeoBasis-DE / BKG 2026 (Daten verändert); dl-de/by-2-0."


def _verified_members(archive: ZipFile) -> dict[str, bytes]:
    """Verify each pinned source layer in the cached archive.

    Args:
        archive: Open cache ZIP.

    Returns:
        Original Brotli-compressed source layers.

    Raises:
        ValueError: Members are missing, duplicated, oversized, or corrupted.
    """
    if sorted(archive.namelist()) != sorted(DATA_FILES):
        raise ValueError("Expected exactly the pinned state and district layers.")
    members = {}
    for name, checksum in DATA_FILES.items():
        if archive.getinfo(name).file_size > 50_000_000:
            raise ValueError(f"Boundary layer is too large: {name}.")
        content = archive.read(name)
        if hashlib.sha256(content).hexdigest() != checksum:
            raise ValueError(
                f"Dataset checksum mismatch: {name}; remove cache and retry."
            )
        members[name] = content
    return members


def download_data(cache_dir: Path) -> Path:
    """Download or reuse independently checksum-verified German boundary layers.

    Args:
        cache_dir: Directory for a ZIP containing the two pinned source layers.

    Returns:
        Path to the verified cache ZIP; no historical datasets are downloaded.

    Raises:
        ValueError: A downloaded or cached source layer fails verification.
    """
    path = cache_dir / f"germany-{DATA_REVISION}.zip"
    if path.exists():
        with ZipFile(path) as archive:
            _verified_members(archive)
        return path
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name in DATA_FILES:
            with urlopen(f"{DATA_URL}/{name}", timeout=120) as response:
                archive.writestr(name, response.read(50_000_001))
    with ZipFile(buffer) as archive:
        _verified_members(archive)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buffer.getvalue())
    return path


def normalize(name: str) -> str:
    """Normalize Unicode, case, and whitespace for German district matching.

    Args:
        name: District name or qualified target label.

    Returns:
        Normalized name with single spaces between words.
    """
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def _load_layer(archive: ZipFile, name: str, code_length: int) -> gpd.GeoDataFrame:
    """Load and validate one state or district layer, excluding water-only areas.

    Args:
        archive: Open ZIP with the source-format compressed layers.
        name: Exact source member name.
        code_length: Expected official code length (two for states, five for districts).

    Returns:
        Validated land-area polygons in EPSG:4326.

    Raises:
        ValueError: Layer structure, IDs, names, CRS, or geometry is invalid.
    """
    if (
        archive.namelist().count(name) != 1
        or archive.getinfo(name).file_size > 50_000_000
    ):
        raise ValueError(f"Expected one reasonably sized {name} in ZIP.")
    try:
        content = brotli.decompress(archive.read(name))
    except brotli.error as error:
        raise ValueError(f"Invalid compressed boundary layer: {name}.") from error
    if len(content) > 100_000_000:
        raise ValueError(f"Decompressed boundary layer is too large: {name}.")
    frame = gpd.read_file(io.BytesIO(content))
    if not {"GF", "AGS", "GEN", "BEZ"}.issubset(frame.columns):
        raise ValueError(f"Missing required boundary fields in {name}.")
    # BKG also supplies separate sea/water polygons carrying the same codes.
    frame = frame[frame.GF == 4].copy()
    if frame.empty:
        raise ValueError(f"Missing land-area records in {name}.")
    if frame.crs is None:
        raise ValueError(f"Missing coordinate reference system in {name}.")
    for field in ("AGS", "GEN", "BEZ"):
        if frame[field].isna().any():
            raise ValueError(f"Missing boundary names, types, or codes in {name}.")
        frame[field] = frame[field].astype(str).str.strip()
        if (frame[field] == "").any():
            raise ValueError(f"Empty boundary names, types, or codes in {name}.")
    if not frame.AGS.str.fullmatch(rf"\d{{{code_length}}}").all():
        raise ValueError(f"Invalid official boundary codes in {name}.")
    if frame.AGS.duplicated().any():
        raise ValueError(f"Duplicate boundary codes in {name}.")
    if (~frame.geometry.is_valid).any():
        warnings.warn(f"Repairing invalid geometries in {name}.", stacklevel=2)
        frame.geometry = frame.geometry.make_valid()
    if (
        frame.geometry.isna().any()
        or frame.geometry.is_empty.any()
        or not frame.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ):
        raise ValueError(f"Expected nonempty polygon geometries in {name}.")
    return frame.to_crs(4326)


def load_data(path: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load Bundesländer and districts, adding unambiguous selection labels.

    Args:
        path: ZIP containing the source's state and district Brotli GeoJSON files.

    Returns:
        States and districts, including names, official codes, and target labels.

    Raises:
        ValueError: Data is invalid or a district refers to an unknown state.
    """
    with ZipFile(path) as archive:
        states = _load_layer(archive, "1_bundeslaender.geojson.br", 2)
        districts = _load_layer(archive, "3_kreise.geojson.br", 5)
    state_names = dict(zip(states.AGS, states.GEN, strict=True))
    districts["state_code"] = districts.AGS.str[:2]
    if not set(districts.state_code).issubset(state_names):
        raise ValueError("District refers to an unknown Bundesland.")
    if not districts.BEZ.isin(
        ["Landkreis", "Kreis", "Kreisfreie Stadt", "Stadtkreis"]
    ).all():
        raise ValueError("Unsupported district type in dataset.")
    districts["state"] = districts.state_code.map(state_names)
    city = districts.BEZ.isin(["Kreisfreie Stadt", "Stadtkreis"])
    county_names = set(districts.loc[~city, "GEN"].map(normalize))
    shared_name = districts.GEN.map(normalize).isin(county_names)
    districts["target_name"] = districts.GEN
    districts.loc[city & shared_name, "target_name"] += " (kreisfreie Stadt)"
    if districts.target_name.map(normalize).duplicated().any():
        raise ValueError("Ambiguous district target labels in dataset.")
    return states, districts


def select_targets(districts: gpd.GeoDataFrame, names: list[str]) -> gpd.GeoDataFrame:
    """Select districts by target label or official five-digit code.

    Args:
        districts: Validated district frame with qualified city labels.
        names: Requested target labels or official codes, in card order.

    Returns:
        Matched rows; a bare shared name selects the Landkreis.

    Raises:
        ValueError: Targets are empty, unknown, ambiguous, or duplicated.
    """
    if not names:
        raise ValueError("Target list is empty.")
    labels = districts.target_name.map(normalize)
    selected = []
    seen = set()
    for name in names:
        key = normalize(name)
        matches = districts.index[(labels == key) | (districts.AGS == key)].tolist()
        if not matches:
            suggestions = get_close_matches(key, labels.tolist(), n=3)
            raise ValueError(f"Unknown district: {name!r}. Similar: {suggestions}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous district: {name!r}.")
        index = matches[0]
        if index in seen:
            raise ValueError(f"Duplicate target: {name!r}.")
        seen.add(index)
        selected.append(index)
    return districts.loc[selected].copy()
