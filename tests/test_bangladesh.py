import io
import json
import sqlite3
import sys
import unicodedata
import warnings
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZipFile

import geopandas as gpd
import pytest
from matplotlib.axes import Axes
from PIL import Image
from shapely.geometry import Polygon, box

from geo_anki.countries.bangladesh import data
from geo_anki.countries.bangladesh.build import build_bangladesh
from geo_anki.countries.bangladesh.maps import (
    BENGALI_FONT,
    FONT_LICENSE,
    REFERENCE_CITIES,
    render_map,
)
from geo_anki.scripts import run
from geo_anki.utils.anki import stable_id


@pytest.fixture
def dataset(tmp_path):
    """Create bilingual reference tables and synthetic district boundaries.

    Args:
        tmp_path: Directory for the source-format ZIP.

    Returns:
        ZIP with three district polygons, bilingual names, and two divisions.
    """
    frame = gpd.GeoDataFrame(
        {"ADM2_EN": ["Dhaka", "Chittagong", "Comilla"]},
        geometry=[
            box(90, 23, 90.7, 24),
            box(91.4, 21.8, 92, 22.8),
            box(90.8, 23.3, 91.3, 23.9),
        ],
        crs=4326,
    )
    districts = [
        {"id": "13", "name": "Dhaka", "bn_name": "ঢাকা", "division_id": "3"},
        {"id": "8", "name": "Chattogram", "bn_name": "চট্টগ্রাম", "division_id": "1"},
        {"id": "1", "name": "Comilla", "bn_name": "কুমিল্লা", "division_id": "1"},
    ]
    divisions = [{"id": "3", "name": "Dhaka"}, {"id": "1", "name": "Chattogram"}]
    archive = tmp_path / "boundaries.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("source/geojson/districts.geojson", frame.to_json())
        for name, rows in (("districts", districts), ("divisions", divisions)):
            z.writestr(
                f"source/{name}/{name}.json",
                json.dumps(
                    [{"type": "header"}, {"type": "table", "name": name, "data": rows}]
                ),
            )
    return archive


def test_bilingual_matching_and_legacy_names(dataset):
    """Match Bengali, English, and renamed districts while preserving order.

    Args:
        dataset: Bilingual archive fixture.

    Returns:
        None. Asserts canonical spellings, correct joins, and mixed-script input.
    """
    districts = data.load_data(dataset)
    assert districts.crs.to_epsg() == 4326
    selected = data.select_targets(districts, ["  CHITTAGONG  ", "ঢাকা", "Cumilla"])
    assert selected.name_en.tolist() == ["Chattogram", "Dhaka", "Cumilla"]
    assert selected.name_bn.tolist() == ["চট্টগ্রাম", "ঢাকা", "কুমিল্লা"]
    assert selected.district_id.tolist() == ["8", "13", "1"]
    assert selected.division.tolist() == ["Chattogram", "Dhaka", "Chattogram"]
    assert data.normalize("  Brahmanbaria   ") == "brahmanbaria"
    assert data.normalize(unicodedata.normalize("NFD", "বগুড়া")) == data.normalize("বগুড়া")


@pytest.mark.parametrize(
    "names, message",
    [
        ([], "empty"),
        (["Dhaka", "ঢাকা"], "Duplicate"),
        (["Comilla", "Cumilla"], "Duplicate"),
        (["Not a district"], "Unknown district"),
    ],
)
def test_invalid_targets(dataset, names, message):
    """Reject unknown, empty, and cross-script duplicate district selections.

    Args:
        dataset: Bilingual archive fixture.
        names: Requested district names.
        message: Expected error pattern.

    Returns:
        None. Asserts a useful validation error.
    """
    with pytest.raises(ValueError, match=message):
        data.select_targets(data.load_data(dataset), names)


def test_download_cache_and_checksum(tmp_path, monkeypatch):
    """Verify fresh downloads, cache reuse, and corruption detection.

    Args:
        tmp_path: Temporary cache directory.
        monkeypatch: Helper for replacing the expected hash and HTTP response.

    Returns:
        None. Asserts one download and rejection of a corrupted cache.
    """
    payload = b"source archive"
    monkeypatch.setattr(data, "DATA_SHA256", data.hashlib.sha256(payload).hexdigest())
    download = Mock(side_effect=lambda *args, **kwargs: io.BytesIO(payload))
    monkeypatch.setattr(data, "urlopen", download)
    path = data.download_data(tmp_path)
    assert data.download_data(tmp_path) == path
    download.assert_called_once_with(data.DATA_URL, timeout=120)
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(tmp_path)


@pytest.mark.parametrize(
    "problem, message",
    [
        ("missing_bengali", "Missing district IDs or bilingual"),
        ("non_bengali", "Expected a Bengali"),
        ("duplicate_id", "Duplicate district names or IDs"),
        ("duplicate_bengali", "Duplicate district names or IDs"),
        ("unknown_division", "unknown division"),
        ("unmatched_name", "do not match"),
        ("duplicate_boundary", "Duplicate district boundaries"),
        ("missing_boundary_name", "Missing district boundary names"),
        ("missing_fields", "required district boundary fields"),
        ("empty_boundaries", "required district boundary fields"),
        ("missing_division_name", "Missing division names or IDs"),
        ("duplicate_division", "Duplicate division IDs"),
        ("missing_table", "nonempty districts table"),
        ("empty_table", "nonempty districts table"),
        ("duplicate_table", "nonempty districts table"),
        ("bad_export", "Invalid districts table export"),
        ("bad_record", "Invalid records in districts"),
        ("missing_layer", "Expected one reasonably sized"),
        ("line_geometry", "nonempty polygon"),
    ],
)
def test_invalid_source_data(dataset, problem, message):
    """Reject incomplete joins, broken metadata, and unsuitable geometry.

    Args:
        dataset: Archive fixture to modify.
        problem: Invalid source-data scenario.
        message: Expected validation error.

    Returns:
        None. Asserts bad input fails before card generation.
    """
    with ZipFile(dataset) as z:
        layers = {name: json.loads(z.read(name)) for name in z.namelist()}
    districts = layers["source/districts/districts.json"]
    rows = districts[1]["data"]
    divisions = layers["source/divisions/divisions.json"][1]["data"]
    boundaries = layers["source/geojson/districts.geojson"]
    if problem == "missing_bengali":
        rows[0]["bn_name"] = " "
    elif problem == "non_bengali":
        rows[0]["bn_name"] = "Dhaka"
    elif problem == "duplicate_id":
        rows[1]["id"] = rows[0]["id"]
    elif problem == "duplicate_bengali":
        rows[1]["bn_name"] = rows[0]["bn_name"]
    elif problem == "unknown_division":
        rows[0]["division_id"] = "99"
    elif problem == "unmatched_name":
        rows[0]["name"] = "Unknown"
    elif problem == "duplicate_boundary":
        boundaries["features"][1] = boundaries["features"][0]
    elif problem == "missing_boundary_name":
        boundaries["features"][0]["properties"]["ADM2_EN"] = None
    elif problem == "missing_fields":
        for feature in boundaries["features"]:
            feature["properties"] = {}
    elif problem == "empty_boundaries":
        boundaries["features"] = []
    elif problem == "missing_division_name":
        divisions[0]["name"] = " "
    elif problem == "duplicate_division":
        divisions.append(divisions[0])
    elif problem == "missing_table":
        districts.pop()
    elif problem == "empty_table":
        districts[1]["data"] = []
    elif problem == "duplicate_table":
        districts.append(districts[1])
    elif problem == "bad_export":
        layers["source/districts/districts.json"] = {}
    elif problem == "bad_record":
        rows[0] = "invalid"
    elif problem == "missing_layer":
        del layers["source/geojson/districts.geojson"]
    elif problem == "line_geometry":
        boundaries["features"][0]["geometry"] = {
            "type": "LineString",
            "coordinates": [[90, 23], [91, 24]],
        }
    with ZipFile(dataset, "w") as z:
        for name, layer in layers.items():
            z.writestr(name, json.dumps(layer))
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_geometry_repair_and_reprojection(dataset):
    """Repair self-crossing polygons and restore geographic coordinates.

    Args:
        dataset: Archive fixture to update.

    Returns:
        None. Asserts valid repaired geometry and EPSG:4326 output.
    """
    with ZipFile(dataset) as z:
        layers = {name: z.read(name) for name in z.namelist()}
    frame = gpd.read_file(io.BytesIO(layers["source/geojson/districts.geojson"]))
    frame.loc[0, "geometry"] = Polygon(
        [(90, 23), (91, 24), (90, 24), (91, 23), (90, 23)]
    )
    layers["source/geojson/districts.geojson"] = frame.to_crs(3857).to_json().encode()
    with ZipFile(dataset, "w") as z:
        for name, payload in layers.items():
            z.writestr(name, payload)
    with pytest.warns(UserWarning, match="Repairing invalid district"):
        districts = data.load_data(dataset)
    assert districts.crs.to_epsg() == 4326
    assert districts.is_valid.all()
    assert districts.iloc[0].geometry.geom_type == "MultiPolygon"
    assert districts.iloc[0].geometry.bounds == pytest.approx((90, 23, 91, 24))


def test_bilingual_map_and_cities(dataset, tmp_path):
    """Render shaped Bengali titles, English names, and all reference cities.

    Args:
        dataset: Bilingual archive fixture.
        tmp_path: Directory for the map.

    Returns:
        None. Asserts text, fonts, reference cities, full extent, and valid PNG.
    """
    districts = data.load_data(dataset)
    target = data.select_targets(districts, ["ঢাকা"])
    output = tmp_path / "map.png"
    with (
        warnings.catch_warnings(record=True) as emitted,
        patch.object(
            Axes, "set_title", autospec=True, side_effect=Axes.set_title
        ) as title,
        patch.object(Axes, "text", autospec=True, side_effect=Axes.text) as text,
        patch.object(
            Axes, "annotate", autospec=True, side_effect=Axes.annotate
        ) as cities,
        patch.object(
            Axes, "set_ylim", autospec=True, side_effect=Axes.set_ylim
        ) as ylim,
    ):
        render_map(districts, target, output)
    assert title.call_args.args[1] == "ঢাকা"
    assert title.call_args.kwargs["language"] == "bn"
    assert title.call_args.kwargs["fontproperties"].get_file() == str(BENGALI_FONT)
    assert any(len(c.args) > 3 and c.args[3] == "Dhaka" for c in text.call_args_list)
    assert {c.args[1] for c in cities.call_args_list} == {
        c[0] for c in REFERENCE_CITIES
    }
    assert not any("Glyph" in str(w.message) for w in emitted)
    context = districts.to_crs("+proj=merc +lon_0=90 +datum=WGS84 +units=m +no_defs")
    assert ylim.call_args.args[1] < context.total_bounds[1]
    assert ylim.call_args.args[2] > context.total_bounds[3]
    with Image.open(output) as image:
        assert image.size == (1600, 1440)


@pytest.mark.parametrize("local_data", [True, False])
def test_cli_bengali_fronts_and_embedded_font(
    dataset, tmp_path, monkeypatch, local_data
):
    """Build cards with Bengali district names and an embedded Bengali font.

    Args:
        dataset: Bilingual archive fixture.
        tmp_path: Working directory for CLI defaults.
        monkeypatch: Helper for setting CLI arguments and downloader.
        local_data: Whether to supply a local archive instead of downloading.

    Returns:
        None. Asserts card text, embedded font/license, model isolation, and manifest.
    """
    monkeypatch.chdir(tmp_path)
    targets = tmp_path / "targets.txt"
    targets.write_text(
        "\ufeff# Mixed input scripts\nঢাকা\n\nChittagong\n", encoding="utf-8"
    )
    arguments = ["geo_anki", "--country", "Bangladesh", "--targets", str(targets)]
    if local_data:
        arguments.extend(["--data", str(dataset)])
    monkeypatch.setattr(sys, "argv", arguments)
    download = Mock(return_value=dataset)
    monkeypatch.setitem(
        run.COUNTRIES,
        "bangladesh",
        replace(run.COUNTRIES["bangladesh"], download_data=download),
    )
    run.main()
    if local_data:
        download.assert_not_called()
    else:
        download.assert_called_once_with(Path(".cache/geo-anki"))
    output = tmp_path / "outputs/bangladesh.apkg"
    with ZipFile(output) as z:
        media = json.loads(z.read("media"))
        assert len(media) == 4
        assets = {name: z.read(key) for key, name in media.items()}
        assert assets[BENGALI_FONT.name] == BENGALI_FONT.read_bytes()
        assert assets[FONT_LICENSE.name] == FONT_LICENSE.read_bytes()
        assert sum(value.startswith(b"\x89PNG") for value in assets.values()) == 2
        database = tmp_path / "collection.sqlite"
        database.write_bytes(z.read("collection.anki2"))
    with sqlite3.connect(database) as c:
        notes = c.execute("SELECT mid, flds FROM notes ORDER BY id").fetchall()
        fields = [note[1].split("\x1f") for note in notes]
        assert [f[:2] for f in fields] == [
            ["Bangladesh: ঢাকা", "Dhaka"],
            ["Bangladesh: চট্টগ্রাম", "Chattogram"],
        ]
        assert notes[0][0] != stable_id("geo-anki:map-model:v1")
        models = json.loads(c.execute("SELECT models FROM col").fetchone()[0])
        assert "@font-face" in models[str(notes[0][0])]["css"]
        assert BENGALI_FONT.name in models[str(notes[0][0])]["css"]
        assert c.execute("SELECT count(*) FROM cards").fetchone()[0] == 2
        decks = json.loads(c.execute("SELECT decks FROM col").fetchone()[0])
        assert "Geo Anki::Bangladesh" in [d["name"] for d in decks.values()]
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert [card["name_bn"] for card in manifest["cards"]] == ["ঢাকা", "চট্টগ্রাম"]
    assert manifest["default_revision"] == data.DATA_REVISION


def test_bad_target_creates_no_output(dataset, tmp_path):
    """Reject unknown districts without leaving a partial map or package.

    Args:
        dataset: Bilingual archive fixture.
        tmp_path: Directory for input and output.

    Returns:
        None. Asserts no deck, manifest, or map directory was created.
    """
    targets = tmp_path / "targets.txt"
    targets.write_text("Unknown district\n")
    output = tmp_path / "deck.apkg"
    with pytest.raises(ValueError, match="Unknown district"):
        build_bangladesh(targets, output, dataset, "Test deck")
    assert not output.exists()
    assert not output.with_suffix(".json").exists()
    assert not (tmp_path / "deck_maps").exists()
