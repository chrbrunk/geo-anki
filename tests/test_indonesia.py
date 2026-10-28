import io
import json
import sqlite3
import sys
from unittest.mock import Mock, patch
from zipfile import ZipFile

import geopandas as gpd
import pytest
from matplotlib.axes import Axes
from PIL import Image
from shapely.geometry import Polygon, box

from geo_anki.countries.indonesia import data
from geo_anki.countries.indonesia.regions import Region, region_for
from geo_anki.scripts import run
from geo_anki.scripts.run import build_indonesia
from geo_anki.utils.anki import write_deck


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
    monkeypatch.setattr(
        "geo_anki.scripts.run.region_for",
        lambda province: Region(
            province, (province,), (("Jambi", 103.6131, -1.6101, 5, 5),)
        ),
    )
    targets = tmp_path / "targets.txt"
    targets.write_text("# My selections\nMuaro Jambi\n\nKota Jambi\n")
    output = tmp_path / "deck.apkg"
    with patch.object(
        Axes, "set_title", autospec=True, side_effect=Axes.set_title
    ) as title:
        images = build_indonesia(targets, output, dataset, "Test deck")
    titles = [call.args[1] for call in title.call_args_list]
    assert "Muaro Jambi\nJambi · Jambi" in titles
    assert all("Indonesia" not in text for text in titles)
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
        fields = notes[0][1].split("\x1f")
        assert fields[0] == "Indonesia: Muaro Jambi"
        assert fields[1] == "Kabupaten Muaro Jambi — Jambi"
        assert all("Indonesia" not in note[1].split("\x1f")[1] for note in notes)
        assert connection.execute("SELECT count(*) FROM cards").fetchone()[0] == 2
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert manifest["cards"][0]["province"] == "Jambi"


def test_region_selection():
    """Verify island contexts and the province-only fallback.

    Returns:
        None. Asserts framing choices and shared extents within each island.
    """
    for province, neighbor, island in (
        ("Jawa Barat", "Jawa Timur", "Java"),
        ("Sulawesi Selatan", "Gorontalo", "Sulawesi"),
        ("Kalimantan Timur", "Kalimantan Barat", "Kalimantan"),
        ("Jambi", "Aceh", "Sumatra"),
    ):
        region = region_for(province)
        assert region.name == island
        assert {province, neighbor}.issubset(region.provinces)
        assert region_for(neighbor) == region
        assert region.cities
    assert region_for("Bali") == Region("Bali", ("Bali",))


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("WADMKK", None, "Missing names"),
        ("WADMKK", "  ", "Empty names"),
        ("WADMPR", "Unknown province", "unknown province"),
    ],
)
def test_invalid_boundary_data(dataset, field, value, message):
    """Reject missing subdivision names and unknown parent provinces.

    Args:
        dataset: Boundary ZIP fixture to modify.
        field: Subdivision property to replace.
        value: Invalid property value.
        message: Expected error-message pattern.

    Returns:
        None. Asserts invalid data raises ValueError.
    """
    with ZipFile(dataset) as archive:
        layers = {name: archive.read(name) for name in archive.namelist()}
    name = "data/indonesia_kabupaten.geojson"
    layer = json.loads(layers[name])
    layer["features"][0]["properties"][field] = value
    layers[name] = json.dumps(layer).encode()
    with ZipFile(dataset, "w") as archive:
        for name, content in layers.items():
            archive.writestr(name, content)
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_anki_ids_survive_reordered_batches(tmp_path):
    """Verify later exports preserve note, model, and deck identities.

    Args:
        tmp_path: Pytest-provided temporary output directory.

    Returns:
        None. Asserts identities persist after reordering and editing card text.
    """
    image = tmp_path / "map.png"
    Image.new("RGB", (2, 2)).save(image)
    identities = []
    for batch in (0, 1):
        cards = [(key, key, f"Answer {batch}", image) for key in ("a", "b")]
        if batch:
            cards.reverse()
        output = tmp_path / f"batch{batch}.apkg"
        write_deck(cards, output, "Test deck")
        with ZipFile(output) as archive:
            database = tmp_path / f"batch{batch}.sqlite"
            database.write_bytes(archive.read("collection.anki2"))
        with sqlite3.connect(database) as connection:
            notes = connection.execute("SELECT guid, mid, flds FROM notes").fetchall()
            note_ids = {
                fields.split("\x1f")[0]: (guid, mid) for guid, mid, fields in notes
            }
            deck_ids = connection.execute("SELECT DISTINCT did FROM cards").fetchall()
            identities.append((note_ids, deck_ids))
    assert len(identities[0][0]) == 2
    assert len({guid for guid, _ in identities[0][0].values()}) == 2
    assert identities[0] == identities[1]


@pytest.mark.parametrize("local_data", [True, False])
def test_cli_builds_deck(tmp_path, dataset, monkeypatch, capsys, local_data):
    """Exercise CLI generation with a local ZIP or a simulated download.

    Args:
        tmp_path: Temporary output directory.
        dataset: Boundary ZIP fixture.
        monkeypatch: Helper for setting CLI arguments and the map context.
        capsys: Captured CLI output.
        local_data: Whether to pass an explicit dataset path.

    Returns:
        None. Asserts the package, manifest, and download selection are correct.
    """
    targets = tmp_path / "targets.txt"
    targets.write_text("Muaro Jambi\n", encoding="utf-8")
    output = tmp_path / "deck.apkg"
    cache = tmp_path / "cache"
    arguments = [
        "geo_anki",
        "--country",
        "Indonesia",
        "--targets",
        str(targets),
        "--output",
        str(output),
        "--cache-dir",
        str(cache),
        "--deck-name",
        "CLI example",
    ]
    if local_data:
        arguments.extend(["--data", str(dataset)])
    download = Mock(return_value=dataset)
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(run, "download_data", download)
    monkeypatch.setattr(
        run, "region_for", lambda province: Region(province, (province,))
    )
    run.main()
    assert "1 cards and 1 PNG maps" in capsys.readouterr().out
    if local_data:
        download.assert_not_called()
    else:
        download.assert_called_once_with(cache)
    with ZipFile(output) as archive:
        assert len(json.loads(archive.read("media"))) == 1
        database = tmp_path / "collection.sqlite"
        database.write_bytes(archive.read("collection.anki2"))
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM notes").fetchone()[0] == 1
        decks = json.loads(connection.execute("SELECT decks FROM col").fetchone()[0])
        assert "CLI example" in [deck["name"] for deck in decks.values()]
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert manifest["cards"][0]["name"] == "Muaro Jambi"


@pytest.mark.parametrize(
    "case,message",
    [
        ("suffix", "--output must end in .apkg"),
        ("target", "Unknown kabupaten/kota"),
        ("missing_file", "No such file"),
        ("country", "invalid choice"),
    ],
)
def test_cli_rejects_invalid_input(
    tmp_path, dataset, monkeypatch, capsys, case, message
):
    """Verify CLI failures report an error without generating a deck.

    Args:
        tmp_path: Temporary input and output directory.
        dataset: Boundary ZIP fixture.
        monkeypatch: Helper for setting CLI arguments.
        capsys: Captured CLI output.
        case: Invalid-input scenario.
        message: Expected error text.

    Returns:
        None. Asserts exit code 2 and absence of generated output.
    """
    targets = tmp_path / "targets.txt"
    if case != "missing_file":
        targets.write_text("Unknown subdivision\n", encoding="utf-8")
    output = tmp_path / ("deck.txt" if case == "suffix" else "deck.apkg")
    country = "unsupported" if case == "country" else "indonesia"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "geo_anki",
            "--country",
            country,
            "--targets",
            str(targets),
            "--data",
            str(dataset),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as error:
        run.main()
    assert error.value.code == 2
    assert message in capsys.readouterr().err
    assert not output.exists()
    assert not output.with_suffix(".json").exists()
    assert not (tmp_path / "deck_maps").exists()


def test_geometry_repair_and_reprojection(dataset):
    """Verify invalid polygons are repaired and projected data returns to WGS84.

    Args:
        dataset: Boundary ZIP fixture to modify.

    Returns:
        None. Asserts repaired polygon validity, CRS, and geographic bounds.
    """
    provinces, districts = data.load_data(dataset)
    districts.loc[0, "geometry"] = Polygon(
        [
            (102, -3),
            (104, -1),
            (102, -1),
            (104, -3),
            (102, -3),
        ]
    )
    with ZipFile(dataset, "w") as archive:
        archive.writestr("indonesia_provinsi.geojson", provinces.to_crs(3857).to_json())
        archive.writestr(
            "indonesia_kabupaten.geojson", districts.to_crs(3857).to_json()
        )
    with pytest.warns(UserWarning, match="Repairing invalid geometries"):
        provinces, districts = data.load_data(dataset)
    assert provinces.crs.to_epsg() == districts.crs.to_epsg() == 4326
    assert districts.is_valid.all()
    assert not districts.is_empty.any()
    assert districts.iloc[0].geometry.geom_type == "MultiPolygon"
    assert districts.iloc[0].geometry.bounds == pytest.approx((102, -3, 104, -1))
