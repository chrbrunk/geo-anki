"""Pinned Survey of India district boundaries, validation and target selection."""

import hashlib
import io
import unicodedata
import warnings
from collections.abc import Hashable
from difflib import get_close_matches
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile

import geopandas as gpd
import py7zr
from py7zr.io import BytesIOFactory

from geo_anki.countries.india.names import FRONT_LANGUAGES, NATIVE_NAMES
from geo_anki.countries.india.regions import STATES

DATA_REVISION = "soi-districts-2023-12-11"
DATA_VINTAGE = "Collection released 2023-12-11; historical district extents/names"
DATA_URL = (
    "https://github.com/ramSeraph/indian_admin_boundaries/releases/download/"
    "districts/SOI_Districts.geojsonl.7z"
)
DATA_SHA256 = "d160bc8cab093d58ba7f400a4ae44bd3d0ff521b7955bedfb0ff5dc5e8cc72ba"
LAYER = "SOI_Districts.geojsonl"
LAYER_SHA256 = "92ef5f36f67f73d616ad9fc529b74b58ac5708efee6f0010f691806b2c7badfd"
MAX_LAYER_BYTES = 128_000_000
DATA_ATTRIBUTION = (
    "Survey of India; ramSeraph / DataMeet collection (2023-12-11). "
    "Historical boundaries; district names adapted for display."
)

# These source polygons have no LGD district code: disputed/context areas, not
# administrative districts. Keep their geometry but never invent target IDs.
CONTEXT_NAMES = {
    "DISPUTED (RATLAM & MANDSAUR)",
    "DISPUTED (ALIRAJPUR & DAHOD)",
    "DISPUTED (RATLAM & BANSWARA)",
    "DISPUTED (SAHIBGANJ, MALDAH & KATIHAR)",
    "DISPUTED (MANDSAUR & JHALAWAR)",
    "MIRPUR",
    "MUZAFFARABAD",
    "DISPUTED (NIMACH & CHITTAURGARH )",
    "DISPUTED (BARAN & SHEOPUR",
    "DISPUTED (SABAR KANTHA & UDAIPUR)",
    "DISPUTED (SABAR KANTHA & SIROHI)",
}


def _verified_layer(archive: ZipFile) -> bytes:
    """Read the sole pinned layer without extracting paths, verifying its hash."""
    if archive.namelist() != [LAYER]:
        raise ValueError("Expected exactly one pinned Indian district layer.")
    if archive.getinfo(LAYER).file_size > MAX_LAYER_BYTES:
        raise ValueError("Indian district layer is too large.")
    content = archive.read(LAYER)
    if hashlib.sha256(content).hexdigest() != LAYER_SHA256:
        raise ValueError("Dataset checksum mismatch; remove cache and retry.")
    return content


def download_data(cache_dir: Path) -> Path:
    """Download a verified 7z source and cache its verified layer in a ZIP."""
    path = cache_dir / f"india-{DATA_REVISION}.zip"
    if path.exists():
        with ZipFile(path) as archive:
            _verified_layer(archive)
        return path
    with urlopen(DATA_URL, timeout=120) as response:
        source = response.read(64_000_001)
    if hashlib.sha256(source).hexdigest() != DATA_SHA256:
        raise ValueError("Downloaded dataset checksum mismatch.")
    factory = BytesIOFactory(limit=MAX_LAYER_BYTES)
    with py7zr.SevenZipFile(io.BytesIO(source)) as archive:
        entries = archive.list()
        if (
            len(entries) != 1
            or entries[0].filename != LAYER
            or entries[0].uncompressed > MAX_LAYER_BYTES
        ):
            raise ValueError("Expected one reasonably sized Indian district layer.")
        archive.extractall(factory=factory)
    layer = factory.get(LAYER)
    layer.seek(0)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(LAYER, layer.read())
    with ZipFile(buffer) as archive:
        _verified_layer(archive)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buffer.getvalue())
    return path


def normalize(name: str) -> str:
    """Match Unicode, case and whitespace consistently across scripts."""
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def load_data(path: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load source polygons and selectable districts; reject malformed records.

    Local ZIP overrides may contain compatible source-format data. The automatic
    downloader verifies exact bytes; local overrides still undergo validation.
    """
    with ZipFile(path) as archive:
        if archive.namelist() != [LAYER]:
            raise ValueError("Expected exactly one Indian district layer.")
        if archive.getinfo(LAYER).file_size > MAX_LAYER_BYTES:
            raise ValueError("Indian district layer is too large.")
        frame = gpd.read_file(io.BytesIO(archive.read(LAYER)), driver="GeoJSONSeq")
    required = {"District_C", "STATE_C", "State_LGD", "DISTRICT_L"}
    if frame.empty or not required.issubset(frame.columns):
        raise ValueError("Missing required district fields or records.")
    if frame.crs is None:
        raise ValueError("Missing coordinate reference system.")
    for field in ("District_C", "STATE_C"):
        if frame[field].isna().any() or frame[field].str.strip().eq("").any():
            raise ValueError("Missing boundary names.")
    if frame.State_LGD.isna().any():
        raise ValueError("Missing state codes.")
    frame["state_code"] = frame.State_LGD.astype(str).str.removesuffix(".0")
    frame["district_id"] = frame.DISTRICT_L.fillna("").astype(str)
    uncoded = frame.district_id.eq("")
    if not frame.loc[uncoded, "District_C"].isin(CONTEXT_NAMES).all():
        raise ValueError("Missing district codes on administrative records.")
    if not frame.loc[~uncoded, "district_id"].str.fullmatch(r"[1-9]\d*").all():
        raise ValueError("Invalid district codes.")
    if frame.loc[~uncoded, "district_id"].duplicated().any():
        raise ValueError("Duplicate district codes.")
    if not set(frame.loc[~uncoded, "state_code"]).issubset(STATES):
        raise ValueError("District refers to an unknown state.")
    if not set(frame.state_code).issubset({"0", *STATES}):
        raise ValueError("Unknown context state.")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Expected nonempty polygon geometries.")
    if (~frame.geometry.is_valid).any():
        warnings.warn("Repairing invalid Indian district geometries.", stacklevel=2)
        frame.geometry = frame.geometry.make_valid(
            method="structure", keep_collapsed=False
        )
    if (
        frame.geometry.isna().any()
        or frame.geometry.is_empty.any()
        or not frame.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ):
        raise ValueError("Expected nonempty polygon geometries.")
    frame = frame.to_crs(4326)
    districts = frame.loc[~uncoded].copy()
    if districts.empty:
        raise ValueError("No coded districts in dataset.")
    districts["state"] = districts.state_code.map(STATES)
    districts["name_en"] = districts.District_C.map(
        lambda s: " ".join(s.title().split())
    )
    districts["language"] = districts.state_code.map(FRONT_LANGUAGES).fillna("en")
    districts["name_native"] = districts.district_id.map(NATIVE_NAMES)
    native = districts.language.ne("en")
    if districts.loc[native, "name_native"].isna().any():
        raise ValueError("Missing native district name; update the curated catalog.")
    districts.loc[~native, "name_native"] = districts.loc[~native, "name_en"]
    districts["target_name"] = districts.name_en + " — " + districts.state
    if districts.target_name.map(normalize).duplicated().any():
        raise ValueError("Ambiguous district labels within a state.")
    return frame, districts


def select_targets(districts: gpd.GeoDataFrame, names: list[str]) -> gpd.GeoDataFrame:
    """Accept English/native names, qualified labels or LGD codes in input order."""
    if not names:
        raise ValueError("Target list is empty.")
    aliases: dict[str, list[Hashable]] = {}
    for index, row in districts.iterrows():
        for label in {
            row.name_en,
            row.name_native,
            row.target_name,
            row.district_id,
            f"{row.name_native} — {row.state}",
        }:
            aliases.setdefault(normalize(label), []).append(index)
    selected = []
    for name in names:
        matches = set(aliases.get(normalize(name), []))
        if not matches:
            similar = get_close_matches(normalize(name), aliases, n=3)
            raise ValueError(f"Unknown district: {name!r}. Similar: {similar}")
        if len(matches) != 1:
            choices = districts.loc[list(matches), "target_name"].tolist()
            raise ValueError(f"Ambiguous district: {name!r}. Use one of {choices}")
        index = matches.pop()
        if index in selected:
            raise ValueError(f"Duplicate target: {name!r}.")
        selected.append(index)
    return districts.loc[selected].copy()
