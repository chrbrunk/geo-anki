import hashlib
import io
import unicodedata
import warnings
from difflib import get_close_matches
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import geopandas as gpd

DATA_REVISION = "c95911f3f23af6e01c3bf706c80e36a9f3958588"
DATA_URL = (
    "https://codeload.github.com/mashadinoor/Indonesia-Geojson-2026/zip/"
    + DATA_REVISION
)
DATA_SHA256 = "1ace962c5c1617ed3c8c3104b9ff0ddc1047c9e0a4d345dd8c23bb38602406b9"


def download_data(cache_dir: Path) -> Path:
    """Download or reuse a pinned, checksum-verified boundary archive.

    Args:
        cache_dir: Directory for the downloaded ZIP.

    Returns:
        Path to the verified archive.

    Raises:
        ValueError: The downloaded or cached archive fails checksum verification.
    """
    path = cache_dir / f"indonesia-{DATA_REVISION}.zip"
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
    """Normalize Unicode, case, and whitespace for name matching.

    Args:
        name: Geographic name to normalize.

    Returns:
        Normalized name with single spaces between words.
    """
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def load_data(path: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load and validate Indonesian province and subdivision boundaries.

    Args:
        path: ZIP containing the province and kabupaten GeoJSON files.

    Returns:
        Province and subdivision frames, in that order, using EPSG:4326.

    Raises:
        ValueError: Required layers, names, CRS, or polygon geometries are invalid.
    """
    layers = []
    with ZipFile(path) as archive:
        for filename, fields in (
            ("indonesia_provinsi.geojson", ["PROVINSI"]),
            ("indonesia_kabupaten.geojson", ["WADMKK", "WADMPR"]),
        ):
            members = [
                m for m in archive.infolist() if Path(m.filename).name == filename
            ]
            if len(members) != 1 or members[0].file_size > 100_000_000:
                raise ValueError(f"Expected one reasonably sized {filename} in ZIP.")
            # Read only the required members, without extracting archive paths.
            frame = gpd.read_file(io.BytesIO(archive.read(members[0])))
            if frame.empty or not set(fields).issubset(frame.columns):
                raise ValueError(f"Missing records or required fields in {filename}.")
            if frame.crs is None:
                raise ValueError(f"Missing coordinate reference system in {filename}.")
            for field in fields:
                if frame[field].isna().any():
                    raise ValueError(f"Missing names in {filename}: {field}.")
                frame[field] = frame[field].astype(str).str.strip()
                if (frame[field] == "").any():
                    raise ValueError(f"Empty names in {filename}: {field}.")
            if (~frame.geometry.is_valid).any():
                warnings.warn(
                    f"Repairing invalid geometries in {filename}.", stacklevel=2
                )
                frame.geometry = frame.geometry.make_valid()
            if (
                frame.geometry.isna().any()
                or frame.geometry.is_empty.any()
                or not frame.geom_type.isin(["Polygon", "MultiPolygon"]).all()
            ):
                raise ValueError(f"Expected nonempty polygon geometries in {filename}.")
            layers.append(frame.to_crs(4326))
    provinces, districts = layers
    if provinces.PROVINSI.map(normalize).duplicated().any():
        raise ValueError("Duplicate province names in dataset.")
    parents = set(provinces.PROVINSI.map(normalize))
    if not set(districts.WADMPR.map(normalize)).issubset(parents):
        raise ValueError("Subdivision refers to an unknown province.")
    return provinces, districts


def select_targets(districts: gpd.GeoDataFrame, names: list[str]) -> gpd.GeoDataFrame:
    """Select subdivisions by full name, preserving Kota prefixes.

    Args:
        districts: Subdivision frame with WADMKK names and a unique index.
        names: Requested names, in the desired card order.

    Returns:
        Copy of the matched rows in request order.

    Raises:
        ValueError: Names are empty, unknown, ambiguous, or duplicated.
    """
    if not names:
        raise ValueError("Target list is empty.")
    keys = districts.WADMKK.map(normalize)
    selected = []
    seen = set()
    for name in names:
        key = normalize(name)
        matches = districts.index[keys == key].tolist()
        if not matches:
            suggestions = get_close_matches(key, keys.tolist(), n=3)
            raise ValueError(
                f"Unknown kabupaten/kota: {name!r}. Similar: {suggestions}"
            )
        if len(matches) != 1:
            raise ValueError(
                f"Ambiguous kabupaten/kota: {name!r}; dataset needs review."
            )
        if key in seen:
            raise ValueError(f"Duplicate target: {name!r}.")
        seen.add(key)
        selected.append(matches[0])
    return districts.loc[selected].copy()
