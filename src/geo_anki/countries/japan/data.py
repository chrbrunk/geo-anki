import hashlib
import io
import unicodedata
import warnings
from difflib import get_close_matches
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import geopandas as gpd

from geo_anki.countries.japan.prefectures import PREFECTURES

DATA_REVISION = "513fb852832c99470e16b95a30ddd68bf3469dc0"
DATA_URL = (
    "https://codeload.github.com/piuccio/open-data-jp-prefectures-geojson/zip/"
    + DATA_REVISION
)
DATA_SHA256 = "eda3fbad87d9f39df424d8acc09c053215e8e1c18b1e20d287671a9cfead07f5"
DATA_ATTRIBUTION = "Boundaries: MLIT N03 (2019), converted by Fabio Crisci."


def download_data(cache_dir: Path) -> Path:
    """Download or reuse a pinned, checksum-verified Japan archive.

    Args:
        cache_dir: Directory for the downloaded ZIP.

    Returns:
        Path to the verified archive.

    Raises:
        ValueError: The downloaded or cached archive fails checksum verification.
    """
    path = cache_dir / f"japan-{DATA_REVISION}.zip"
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
    """Normalize Unicode, case, and whitespace for Japanese and English matching.

    Args:
        name: District name to normalize.

    Returns:
        Normalized name with single spaces between words.
    """
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def load_data(path: Path) -> gpd.GeoDataFrame:
    """Load and validate Japanese prefecture boundaries and bilingual names.

    Args:
        path: ZIP containing the source prefectures GeoJSON.

    Returns:
        Prefecture polygons with Japanese/English names and JIS codes, EPSG:4326.

    Raises:
        ValueError: Source names, geometry, CRS, or archive members are invalid.
    """
    with ZipFile(path) as archive:
        members = [
            m
            for m in archive.infolist()
            if m.filename.endswith("/output/prefectures.geojson")
        ]
        if len(members) != 1 or members[0].file_size > 100_000_000:
            raise ValueError(
                "Expected one reasonably sized prefectures.geojson in ZIP."
            )
        frame = gpd.read_file(io.BytesIO(archive.read(members[0])))
    if frame.empty or "P" not in frame.columns:
        raise ValueError("Missing prefecture records or required names.")
    if frame.crs is None:
        raise ValueError("Missing coordinate reference system.")
    lookup = {normalize(ja): (code, ja, en) for code, (ja, en) in PREFECTURES.items()}
    if frame.P.isna().any() or not frame.P.map(lambda n: isinstance(n, str)).all():
        raise ValueError("Missing prefecture names.")
    keys = frame.P.map(normalize)
    if keys.duplicated().any():
        raise ValueError("Duplicate prefecture boundaries.")
    if not set(keys).issubset(lookup):
        raise ValueError("Unknown prefecture names in boundary data.")
    for position, field in enumerate(("prefecture_code", "name_ja", "name_en")):
        frame[field] = keys.map(lambda key: lookup[key][position])
    if (~frame.geometry.is_valid).any():
        warnings.warn("Repairing invalid prefecture geometries.", stacklevel=2)
        frame.geometry = frame.geometry.make_valid()
    if (
        frame.geometry.isna().any()
        or frame.geometry.is_empty.any()
        or not frame.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ):
        raise ValueError("Expected nonempty polygon geometries.")
    return frame.to_crs(4326)


def select_targets(prefectures: gpd.GeoDataFrame, names: list[str]) -> gpd.GeoDataFrame:
    """Select prefectures by English, Japanese, or two-digit JIS code.

    Args:
        prefectures: Validated prefecture boundaries.
        names: Requested names in card order; Japanese suffixes are optional.

    Returns:
        Copy of matching prefectures in request order.

    Raises:
        ValueError: Input is empty or contains unknown or duplicate targets.
    """
    if not names:
        raise ValueError("Target list is empty.")
    aliases = {}
    for index, row in prefectures.iterrows():
        ja = str(row.name_ja)
        short = ja[:-1] if ja.endswith(("都", "府", "県")) else ja
        for alias in (ja, short, row.name_en, row.prefecture_code):
            aliases[normalize(str(alias))] = index
    selected = []
    for name in names:
        key = normalize(name)
        if key not in aliases:
            suggestions = get_close_matches(key, list(aliases), n=3)
            raise ValueError(f"Unknown prefecture: {name!r}. Similar: {suggestions}")
        index = aliases[key]
        if index in selected:
            raise ValueError(f"Duplicate target: {name!r}.")
        selected.append(index)
    return prefectures.loc[selected].copy()
