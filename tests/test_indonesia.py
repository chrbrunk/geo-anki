import io
import json
import sqlite3
from zipfile import ZipFile

import geopandas as gpd
import pytest
from PIL import Image
from shapely.geometry import box

from geo_anki.countries.indonesia import data
from geo_anki.scripts.run import build_indonesia


@pytest.fixture
def dataset(tmp_path):
    """Create a minimal boundary archive for offline tests.

    Args:
        tmp_path: Pytest-provided temporary directory.

    Returns:
        Path to a ZIP with one province and two subdivisions.
    """
    provinces = gpd.GeoDataFrame(
        {"PROVINSI": ["Jambi"]}, geometry=[box(102, -3, 105, -1)], crs=4326
    )
    districts = gpd.GeoDataFrame(
        {"WADMKK": ["Muaro Jambi", "Kota Jambi"], "WADMPR": ["Jambi", "Jambi"]},
        geometry=[box(102, -3, 103.5, -1), box(103.5, -3, 105, -1)],
        crs=4326,
    )
    archive = tmp_path / "boundaries.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("data/indonesia_provinsi.geojson", provinces.to_json())
        z.writestr("data/indonesia_kabupaten.geojson", districts.to_json())
    return archive


def test_target_matching(dataset):
    """Verify normalized matching preserves the subdivision and parent names.

    Args:
        dataset: Boundary ZIP fixture.

    Returns:
        None. Asserts the selected name and inferred province.
    """
    _, districts = data.load_data(dataset)
    target = data.select_targets(districts, ["  MUARO   JAMBI  "])
    assert target.iloc[0].WADMPR == "Jambi"
    assert target.iloc[0].WADMKK == "Muaro Jambi"


@pytest.mark.parametrize(
    "names, message",
    [
        (["Not a kabupaten"], "Unknown"),
        (["Muaro Jambi", "muaro jambi"], "Duplicate"),
        ([], "empty"),
    ],
)
def test_invalid_targets(dataset, names, message):
    """Verify invalid target lists fail with a useful error.

    Args:
        dataset: Boundary ZIP fixture.
        names: Invalid target names for this case.
        message: Expected error-message pattern.

    Returns:
        None. Asserts a matching ValueError is raised.
    """
    _, districts = data.load_data(dataset)
    with pytest.raises(ValueError, match=message):
        data.select_targets(districts, names)


def test_ambiguous_target(dataset):
    """Verify repeated dataset names cannot silently select a subdivision.

    Args:
        dataset: Boundary ZIP fixture.

    Returns:
        None. Asserts ambiguous matches raise ValueError.
    """
    _, districts = data.load_data(dataset)
    districts.loc[1, "WADMKK"] = "Muaro Jambi"
    with pytest.raises(ValueError, match="Ambiguous"):
        data.select_targets(districts, ["Muaro Jambi"])


def test_download_cache_and_checksum(tmp_path, monkeypatch):
    """Verify download reuse and rejection of corrupted cached data.

    Args:
        tmp_path: Pytest-provided temporary cache directory.
        monkeypatch: Pytest helper for replacing the network call and checksum.

    Returns:
        None. Asserts cache reuse and checksum validation.
    """
    payload = b"test archive"
    monkeypatch.setattr(data, "DATA_SHA256", data.hashlib.sha256(payload).hexdigest())
    calls = []

    def fetch(url, timeout):
        """Record a simulated download and return its content.

        Args:
            url: Requested archive URL.
            timeout: Request timeout accepted to match urlopen's interface.

        Returns:
            In-memory stream containing the test archive payload.
        """
        calls.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr(data, "urlopen", fetch)
    path = data.download_data(tmp_path)
    assert data.download_data(tmp_path) == path
    assert len(calls) == 1
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(tmp_path)


def test_map_and_deck(tmp_path, dataset, monkeypatch):
    """Verify map rendering, packaged notes and media, and manifest output.

    Args:
        tmp_path: Pytest-provided temporary output directory.
        dataset: Boundary ZIP fixture.
        monkeypatch: Pytest helper for selecting a small test map context.

    Returns:
        None. Asserts generated files contain the expected cards and images.
    """
    # Use a small province context so this fixture need not mimic all of Sumatra.
    from geo_anki.countries.indonesia.regions import Region

    monkeypatch.setattr(
        "geo_anki.scripts.run.region_for",
        lambda province: Region(province, (province,)),
    )
    targets = tmp_path / "targets.txt"
    targets.write_text("# My selections\nMuaro Jambi\n\nKota Jambi\n")
    output = tmp_path / "deck.apkg"
    images = build_indonesia(targets, output, dataset, "Test deck")
    assert len(images) == 2
    with Image.open(images[0]) as image:
        assert image.width > 500 and image.height > 500
        colors = image.convert("RGB").getcolors(image.width * image.height)
        assert colors is not None and len(colors) > 20
    with ZipFile(output) as archive:
        media = json.loads(archive.read("media"))
        assert set(media.values()) == {image.name for image in images}
        for key in media:
            assert archive.read(key).startswith(b"\x89PNG")
        database = tmp_path / "collection.sqlite"
        database.write_bytes(archive.read("collection.anki2"))
    with sqlite3.connect(database) as connection:
        notes = connection.execute("SELECT guid, flds FROM notes").fetchall()
        assert len(notes) == 2
        assert len({note[0] for note in notes}) == 2
        assert "Indonesia: Muaro Jambi" in notes[0][1]
        assert "Jambi, Indonesia" in notes[0][1]
        assert connection.execute("SELECT count(*) FROM cards").fetchone()[0] == 2
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert manifest["cards"][0]["province"] == "Jambi"
