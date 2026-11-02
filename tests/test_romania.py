"""Romanian county coverage, aliases, whole-country maps and real decks."""

import hashlib
import io
import json
import sqlite3
import sys
import unicodedata
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZipFile

import genanki
import geopandas as gpd
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from PIL import Image
from shapely.geometry import Polygon, box, mapping

from geo_anki.countries.romania import data
from geo_anki.countries.romania.build import build_romania
from geo_anki.countries.romania.maps import MAP_CRS, REFERENCE_CITIES, render_map
from geo_anki.scripts import run


def write_source(path, payload):
    """Store source-format GeoJSON directly in the standard local ZIP."""
    with ZipFile(path, "w") as archive:
        archive.writestr(data.LAYER, json.dumps(payload))


@pytest.fixture
def payload():
    features = []
    for index, (code, name) in enumerate(data.COUNTIES.items()):
        x, y = 20 + index % 7 * 1.5, 44 + index // 7 * 0.7
        geometry = box(x, y, x + 1.1, y + 0.5)
        if code == "B":
            geometry = box(26.02, 44.35, 26.2, 44.55)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "adm0_a3": "ROU",
                    "iso_3166_2": f"RO-{code}",
                    "name": "Bucharest" if code == "B" else name,
                    "type_en": "City" if code == "B" else "County",
                },
                "geometry": mapping(geometry),
            }
        )
    features.append(
        {
            "type": "Feature",
            "properties": {
                "adm0_a3": "HUN",
                "iso_3166_2": "HU-X",
                "name": "Other",
                "type_en": "County",
            },
            "geometry": mapping(box(90, 10, 91, 11)),
        }
    )
    return {"type": "FeatureCollection", "features": features}


@pytest.fixture
def dataset(tmp_path, payload):
    path = tmp_path / "counties.zip"
    write_source(path, payload)
    return path


def test_complete_county_inventory_and_aliases(dataset):
    counties = data.load_data(dataset)
    assert len(counties) == 42
    assert set(counties.county_code) == {f"RO-{code}" for code in data.COUNTIES}
    assert counties.type_en.value_counts().to_dict() == {"County": 41, "City": 1}
    selected = data.select_targets(
        counties, ["  BISTRITA Nasaud  ", "bucharest", "RO-CJ", "tm", "Iaşi"]
    )
    assert selected.county_code.tolist() == ["RO-BN", "RO-B", "RO-CJ", "RO-TM", "RO-IS"]
    assert selected.county_name.tolist() == [
        "Bistrița-Năsăud",
        "București",
        "Cluj",
        "Timiș",
        "Iași",
    ]
    assert data.normalize(unicodedata.normalize("NFD", "Vâlcea")) == "valcea"
    assert data.normalize("Bistriţa–Năsăud") == "bistrita nasaud"
    assert counties.crs.to_epsg() == 4326


@pytest.mark.parametrize(
    "names, message",
    [
        ([], "empty"),
        (["Atlantis"], "Unknown county"),
        (["București", "Bucharest"], "Duplicate"),
        (["Timiș", "RO-TM"], "Duplicate"),
        (["CJ", "Cluj"], "Duplicate"),
    ],
)
def test_invalid_targets(dataset, names, message):
    with pytest.raises(ValueError, match=message):
        data.select_targets(data.load_data(dataset), names)


@pytest.mark.parametrize(
    "problem, message",
    [
        ("field", "required county"),
        ("name", "Missing county"),
        ("blank", "Missing county"),
        ("number", "Missing county"),
        ("duplicate", "Duplicate county"),
        ("unknown", "all 41"),
        ("missing", "all 41"),
        ("no_bucharest", "all 41"),
        ("wrong_type", "municipality"),
        ("null", "nonempty polygon"),
        ("empty", "nonempty polygon"),
        ("line", "nonempty polygon"),
        ("no_romania", "Missing Romanian"),
        ("malformed", "Malformed boundary"),
        ("not_collection", "FeatureCollection"),
    ],
)
def test_bad_boundaries(dataset, payload, problem, message):
    first = payload["features"][0]
    if problem == "field":
        for feature in payload["features"]:
            del feature["properties"]["name"]
    elif problem == "name":
        first["properties"]["name"] = None
    elif problem == "blank":
        first["properties"]["name"] = "  "
    elif problem == "number":
        first["properties"]["name"] = 123
    elif problem == "duplicate":
        first["properties"]["iso_3166_2"] = "RO-AG"
    elif problem == "unknown":
        first["properties"]["iso_3166_2"] = "RO-XX"
    elif problem == "missing":
        del payload["features"][0]
    elif problem == "no_bucharest":
        payload["features"] = [
            f for f in payload["features"] if f["properties"]["iso_3166_2"] != "RO-B"
        ]
    elif problem == "wrong_type":
        first["properties"]["type_en"] = "City"
    elif problem == "null":
        first["geometry"] = None
    elif problem == "empty":
        first["geometry"] = {"type": "Polygon", "coordinates": []}
    elif problem == "line":
        first["geometry"] = {"type": "LineString", "coordinates": [[20, 44], [21, 45]]}
    elif problem == "no_romania":
        for feature in payload["features"]:
            feature["properties"]["adm0_a3"] = "HUN"
    elif problem == "malformed":
        payload["features"][0] = None
    elif problem == "not_collection":
        payload = []
    write_source(dataset, payload)
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_polygon_repair_and_projected_override(dataset, payload):
    payload["features"][0]["geometry"] = mapping(
        Polygon([(20, 44), (21, 45), (20, 45), (21, 44), (20, 44)])
    )
    frame = gpd.GeoDataFrame.from_features(payload["features"], crs=4326)
    write_source(dataset, json.loads(frame.to_crs(3857).to_json()))
    with pytest.warns(UserWarning, match="Repairing invalid"):
        counties = data.load_data(dataset)
    assert counties.crs.to_epsg() == 4326
    assert counties.is_valid.all()
    assert (counties.to_crs(MAP_CRS).area > 0).all()


def test_checksums_and_cached_download(dataset, tmp_path, monkeypatch):
    with ZipFile(dataset) as archive:
        content = archive.read(data.LAYER)
    monkeypatch.setattr(data, "DATA_SHA256", hashlib.sha256(content).hexdigest())
    download = Mock(return_value=io.BytesIO(content))
    monkeypatch.setattr(data, "urlopen", download)
    path = data.download_data(tmp_path / "cache")
    assert data.download_data(tmp_path / "cache") == path
    download.assert_called_once_with(data.DATA_URL, timeout=120)
    with ZipFile(path, "w") as archive:
        archive.writestr(data.LAYER, b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(tmp_path / "cache")
    path.unlink()
    monkeypatch.setattr(data, "urlopen", Mock(return_value=io.BytesIO(b"bad")))
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(tmp_path / "cache")
    assert not path.exists()


def test_bounded_archive_members(dataset, tmp_path, monkeypatch):
    for members in ({"../evil": "bad"}, {data.LAYER: "bad", "extra": "bad"}):
        with ZipFile(dataset, "w") as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        with pytest.raises(ValueError, match="exactly one"):
            data.load_data(dataset)
    with ZipFile(dataset, "w") as archive:
        archive.writestr(data.LAYER, "too long")
    monkeypatch.setattr(data, "MAX_LAYER_BYTES", 1)
    with pytest.raises(ValueError, match="too large"):
        data.load_data(dataset)
    monkeypatch.setattr(data, "urlopen", Mock(return_value=io.BytesIO(b"too long")))
    with pytest.raises(ValueError, match="too large"):
        data.download_data(tmp_path / "cache")
    assert not (tmp_path / "evil").exists()


@pytest.mark.parametrize("name", ["Cluj", "București", "Bistrița-Năsăud"])
def test_whole_country_extent_cities_and_no_pointers(dataset, tmp_path, name):
    counties = data.load_data(dataset)
    context = counties.to_crs(MAP_CRS)
    selected = data.select_targets(counties, [name])
    limits = []
    savefig = Figure.savefig

    def save(figure, *args, **kwargs):
        savefig(figure, *args, **kwargs)
        limits.append((figure.axes[0].get_xlim(), figure.axes[0].get_ylim()))

    with (
        patch.object(Figure, "savefig", autospec=True, side_effect=save),
        patch.object(
            Axes, "annotate", autospec=True, side_effect=Axes.annotate
        ) as labels,
        patch.object(
            Axes, "set_title", autospec=True, side_effect=Axes.set_title
        ) as title,
    ):
        output = tmp_path / "map.png"
        render_map(context, selected, output)
    xmin, ymin, xmax, ymax = context.total_bounds
    (left, right), (bottom, top) = limits[0]
    assert left < xmin < xmax < right and bottom < ymin < ymax < top
    assert right - left < (xmax - xmin) * 2
    assert title.call_args.args[1] == name
    city_names = {call.args[1] for call in labels.call_args_list if call.args[1]}
    assert city_names == {c[0] for c in REFERENCE_CITIES}
    assert all("arrowprops" not in call.kwargs for call in labels.call_args_list)
    with Image.open(output) as image:
        assert image.size == (1600, 1440)


@pytest.mark.parametrize("local", [False, True])
def test_cli_stable_notes_and_embedded_maps(dataset, tmp_path, monkeypatch, local):
    monkeypatch.chdir(tmp_path)
    targets = tmp_path / "targets.txt"
    targets.write_text(
        "\ufeff# Romanian names and aliases\nCluj\n\nBucharest\nBistrita-Nasaud\n",
        encoding="utf-8",
    )
    args = ["geo_anki", "--country", "Romania", "--targets", str(targets)]
    if local:
        args += ["--data", str(dataset)]
    monkeypatch.setattr(sys, "argv", args)
    download = Mock(return_value=dataset)
    monkeypatch.setitem(
        run.COUNTRIES,
        "romania",
        replace(run.COUNTRIES["romania"], download_data=download),
    )
    run.main()
    assert download.call_count == (0 if local else 1)
    output = tmp_path / "outputs/romania.apkg"
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert [c["county_code"] for c in manifest["cards"]] == ["RO-CJ", "RO-B", "RO-BN"]
    with ZipFile(output) as archive:
        media = {
            name: archive.read(key)
            for key, name in json.loads(archive.read("media")).items()
        }
        assert len(media) == 3
        for card in manifest["cards"]:
            image = Path(card["image"])
            assert media[image.name] == image.read_bytes()
        db = tmp_path / "collection.sqlite"
        db.write_bytes(archive.read("collection.anki2"))
    with sqlite3.connect(db) as connection:
        notes = connection.execute(
            "SELECT guid, flds FROM notes ORDER BY id"
        ).fetchall()
        assert [n[0] for n in notes] == [
            genanki.guid_for(f"geo-anki:romania:{code}")
            for code in ("RO-CJ", "RO-B", "RO-BN")
        ]
        assert [n[1].split("\x1f")[:2] for n in notes] == [
            ["Romania: Cluj", "Cluj"],
            ["Romania: București", "București"],
            ["Romania: Bistrița-Năsăud", "Bistrița-Năsăud"],
        ]
        assert connection.execute("SELECT count(*) FROM cards").fetchone()[0] == 3
        decks = json.loads(connection.execute("SELECT decks FROM col").fetchone()[0])
        assert "Geo Anki::Romania" in {d["name"] for d in decks.values()}


def test_invalid_targets_write_no_outputs(dataset, tmp_path):
    targets = tmp_path / "targets.txt"
    targets.write_text("Cluj\nUnknown\n")
    output = tmp_path / "out/romania.apkg"
    with pytest.raises(ValueError, match="Unknown county"):
        build_romania(targets, output, dataset, "Test")
    assert not output.parent.exists()


def test_shipped_target_and_example_lists(dataset):
    root = Path(__file__).resolve().parents[1]
    targets = (root / "targets/romania.txt").read_text().splitlines()
    examples = (root / "examples/romania.txt").read_text().splitlines()
    counties = data.load_data(dataset)
    assert len(targets) == len(set(targets)) == 42
    assert len(examples) == len(set(examples)) == 10
    assert set(examples).issubset(targets)
    assert set(targets) == set(data.COUNTIES.values())
    assert len(data.select_targets(counties, targets)) == 42
    assert data.select_targets(counties, examples).county_name.tolist() == examples
