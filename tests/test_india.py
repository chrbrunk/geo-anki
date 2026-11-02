"""India's language policy, source validation, maps and real Anki packages."""

import hashlib
import io
import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZipFile

import genanki
import py7zr
import pytest
from fontTools.ttLib import TTFont
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from PIL import Image
from shapely.geometry import Polygon, box, mapping

from geo_anki.countries.bangladesh.maps import BENGALI_FONT
from geo_anki.countries.india import data
from geo_anki.countries.india.build import build_india
from geo_anki.countries.india.maps import DEVANAGARI_FONT, prepare_context, render_map
from geo_anki.countries.india.names import FRONT_LANGUAGES, NATIVE_NAMES
from geo_anki.countries.india.regions import REFERENCE_CITIES, STATES
from geo_anki.scripts import run


def write_source(path, features):
    """Write a small compatible ZIP without changing source-format fields."""
    with ZipFile(path, "w") as archive:
        archive.writestr(data.LAYER, "\n".join(json.dumps(f) for f in features))


@pytest.fixture
def features():
    rows = [
        ("490", 27, "PUNE", "MAHARASHTRA", box(73, 18, 75, 20)),
        ("315", 19, "KOLKATA", "WEST BENGAL", box(88, 22, 89, 23)),
        ("27", 3, "AMRITSAR", "PUNJAB", box(74, 31, 75, 32)),
        ("15", 2, "BILASPUR", "HIMACHAL PRADESH", box(76, 31, 77, 32)),
        ("375", 22, "BILASPUR", "CHHATTISGARH", box(82, 22, 83, 23)),
        ("618", 18, "KAMRUP METRO", "ASSAM", box(91, 26, 92, 27)),
        (
            None,
            23,
            "DISPUTED (RATLAM & MANDSAUR)",
            "MADHYA PRADESH",
            box(74, 23, 74.1, 23.1),
        ),
    ]
    return [
        {
            "type": "Feature",
            "properties": {
                "DISTRICT_L": code,
                "State_LGD": state_code,
                "District_C": name,
                "STATE_C": state,
            },
            "geometry": mapping(geometry),
        }
        for code, state_code, name, state, geometry in rows
    ]


@pytest.fixture
def dataset(tmp_path, features):
    path = tmp_path / "districts.zip"
    write_source(path, features)
    return path


def test_scripts_aliases_and_context(dataset):
    context, districts = data.load_data(dataset)
    assert len(context) == 7 and len(districts) == 6
    result = data.select_targets(districts, [" पुणे ", "KOLKATA", "27", "Kamrup Metro"])
    assert result.district_id.tolist() == ["490", "315", "27", "618"]
    assert result.name_native.tolist() == ["पुणे", "কলকাতা", "Amritsar", "Kamrup Metro"]
    assert result.language.tolist() == ["mr", "bn", "en", "en"]
    assert data.select_targets(districts, ["बिलासपुर — Himachal Pradesh"])[
        "district_id"
    ].tolist() == ["15"]
    assert context.crs.to_epsg() == districts.crs.to_epsg() == 4326


@pytest.mark.parametrize(
    "names, message",
    [
        ([], "empty"),
        (["Bilaspur"], "Ambiguous"),
        (["बिलासपुर"], "Ambiguous"),
        (["Pune", "पुणे"], "Duplicate"),
        (["315", "Kolkata"], "Duplicate"),
        (["Atlantis"], "Unknown"),
        (["DISPUTED (RATLAM & MANDSAUR)"], "Unknown"),
    ],
)
def test_bad_targets(dataset, names, message):
    _, districts = data.load_data(dataset)
    with pytest.raises(ValueError, match=message):
        data.select_targets(districts, names)


@pytest.mark.parametrize(
    "problem, message",
    [
        ("field", "required"),
        ("name", "Missing boundary"),
        ("blank", "Missing boundary"),
        ("state", "unknown state"),
        ("state_null", "Missing state"),
        ("duplicate", "Duplicate district"),
        ("missing_id", "Missing district codes"),
        ("bad_id", "Invalid district"),
        ("line", "nonempty polygon"),
        ("empty", "nonempty polygon"),
        ("null_geometry", "nonempty polygon"),
        ("missing_native", "Missing native"),
        ("same_label", "Ambiguous district labels"),
    ],
)
def test_malformed_source(dataset, features, problem, message):
    first = features[0]
    props = first["properties"]
    if problem == "field":
        for feature in features:
            del feature["properties"]["District_C"]
    elif problem == "name":
        props["District_C"] = None
    elif problem == "blank":
        props["District_C"] = "  "
    elif problem == "state":
        props["State_LGD"] = 99
    elif problem == "state_null":
        props["State_LGD"] = None
    elif problem == "duplicate":
        props["DISTRICT_L"] = "315"
    elif problem == "missing_id":
        props["DISTRICT_L"] = None
    elif problem == "bad_id":
        props["DISTRICT_L"] = "0490"
    elif problem == "line":
        first["geometry"] = {"type": "LineString", "coordinates": [[73, 18], [74, 19]]}
    elif problem == "empty":
        first["geometry"] = {"type": "Polygon", "coordinates": []}
    elif problem == "null_geometry":
        first["geometry"] = None
    elif problem == "missing_native":
        props["DISTRICT_L"] = "99999"
    elif problem == "same_label":
        features[1]["properties"].update({"State_LGD": 27, "District_C": "PUNE"})
    write_source(dataset, features)
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_polygon_repair_keeps_area(dataset, features):
    features[0]["geometry"] = mapping(
        Polygon([(73, 18), (75, 20), (73, 20), (75, 18), (73, 18)])
    )
    write_source(dataset, features)
    with pytest.warns(UserWarning, match="Repairing invalid"):
        _, districts = data.load_data(dataset)
    assert districts.is_valid.all() and (districts.to_crs(3857).area > 0).all()


def test_download_verifies_source_layer_and_cache(dataset, tmp_path, monkeypatch):
    with ZipFile(dataset) as archive:
        payload = archive.read(data.LAYER)
    buffer = io.BytesIO()
    with py7zr.SevenZipFile(buffer, "w") as archive:
        archive.writestr(payload, data.LAYER)
    source = buffer.getvalue()
    monkeypatch.setattr(data, "DATA_SHA256", hashlib.sha256(source).hexdigest())
    monkeypatch.setattr(data, "LAYER_SHA256", hashlib.sha256(payload).hexdigest())
    download = Mock(return_value=io.BytesIO(source))
    monkeypatch.setattr(data, "urlopen", download)
    cache = tmp_path / "cache"
    path = data.download_data(cache)
    assert data.download_data(cache) == path
    download.assert_called_once_with(data.DATA_URL, timeout=120)
    with ZipFile(path, "w") as archive:
        archive.writestr(data.LAYER, b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(cache)
    path.unlink()
    monkeypatch.setattr(data, "urlopen", Mock(return_value=io.BytesIO(b"bad")))
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(cache)
    assert not path.exists()


def test_archive_paths_sizes_and_layer_checksum(dataset, tmp_path, monkeypatch):
    for members in ({"../evil": b"bad"}, {data.LAYER: b"bad", "extra": b"bad"}):
        with ZipFile(dataset, "w") as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        with pytest.raises(ValueError, match="exactly one"):
            data.load_data(dataset)
    with ZipFile(dataset, "w") as archive:
        archive.writestr(data.LAYER, b"too long")
    monkeypatch.setattr(data, "MAX_LAYER_BYTES", 1)
    with pytest.raises(ValueError, match="too large"):
        data.load_data(dataset)
    with ZipFile(dataset) as archive:
        with pytest.raises(ValueError, match="too large"):
            data._verified_layer(archive)
    buffer = io.BytesIO()
    with py7zr.SevenZipFile(buffer, "w") as archive:
        archive.writestr(b"bad", "unexpected.geojsonl")
    source = buffer.getvalue()
    monkeypatch.setattr(data, "DATA_SHA256", hashlib.sha256(source).hexdigest())
    monkeypatch.setattr(data, "urlopen", Mock(return_value=io.BytesIO(source)))
    with pytest.raises(ValueError, match="reasonably sized"):
        data.download_data(tmp_path / "cache")
    assert not (tmp_path / "outside").exists()


@pytest.mark.parametrize(
    "name, native", [("Pune", "पुणे"), ("Kolkata", "কলকাতা"), ("Amritsar", "Amritsar")]
)
def test_map_script_state_framing_and_cities(dataset, tmp_path, name, native):
    boundaries, districts = data.load_data(dataset)
    context = prepare_context(boundaries)
    target = data.select_targets(districts, [name])
    output = tmp_path / "map.png"
    limits = []
    savefig = Figure.savefig

    def save(figure, *args, **kwargs):
        savefig(figure, *args, **kwargs)
        limits.append(figure.axes[0].get_xlim())

    with (
        patch.object(
            Axes, "set_title", autospec=True, side_effect=Axes.set_title
        ) as title,
        patch.object(
            Axes, "annotate", autospec=True, side_effect=Axes.annotate
        ) as cities,
        patch.object(Figure, "savefig", autospec=True, side_effect=save),
    ):
        render_map(context, target, output)
    assert title.call_args.args[1] == native
    state_code = target.iloc[0].state_code
    assert {call.args[1] for call in cities.call_args_list} == {
        c[0] for c in REFERENCE_CITIES[state_code]
    }
    xmin, _, xmax, _ = context[context.state_code == state_code].total_bounds
    left, right = limits[0]
    assert left < xmin < xmax < right
    assert right - left < (xmax - xmin) * 2
    with Image.open(output) as image:
        assert image.size == (1600, 1440)


@pytest.mark.parametrize("local", [False, True])
def test_cli_notes_fonts_media_and_guids(dataset, tmp_path, monkeypatch, local):
    monkeypatch.chdir(tmp_path)
    targets = tmp_path / "targets.txt"
    targets.write_text("\ufeff# Three scripts\nPune\n\nকলকাতা\n27\n", encoding="utf-8")
    args = ["geo_anki", "--country", "India", "--targets", str(targets)]
    if local:
        args += ["--data", str(dataset)]
    monkeypatch.setattr(sys, "argv", args)
    download = Mock(return_value=dataset)
    monkeypatch.setitem(
        run.COUNTRIES, "india", replace(run.COUNTRIES["india"], download_data=download)
    )
    run.main()
    assert download.call_count == (0 if local else 1)
    output = tmp_path / "outputs/india.apkg"
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert [c["district_id"] for c in manifest["cards"]] == ["490", "315", "27"]
    assert [c["language"] for c in manifest["cards"]] == ["mr", "bn", "en"]
    with ZipFile(output) as archive:
        media = {
            name: archive.read(key)
            for key, name in json.loads(archive.read("media")).items()
        }
        assert len(media) == 7  # 3 PNGs, two fonts, both licenses.
        for card in manifest["cards"]:
            image = Path(card["image"])
            assert media[image.name] == image.read_bytes()
        assert media[DEVANAGARI_FONT.name] == DEVANAGARI_FONT.read_bytes()
        assert media[BENGALI_FONT.name] == BENGALI_FONT.read_bytes()
        db = tmp_path / "collection.sqlite"
        db.write_bytes(archive.read("collection.anki2"))
    with sqlite3.connect(db) as connection:
        notes = connection.execute(
            "SELECT guid, flds FROM notes ORDER BY id"
        ).fetchall()
        assert [n[0] for n in notes] == [
            genanki.guid_for(f"geo-anki:india:lgd:{code}")
            for code in ("490", "315", "27")
        ]
        assert [n[1].split("\x1f")[:2] for n in notes] == [
            ["India: पुणे", "Pune — Maharashtra"],
            ["India: কলকাতা", "Kolkata — West Bengal"],
            ["India: Amritsar", "Amritsar — Punjab"],
        ]
        models = json.loads(connection.execute("SELECT models FROM col").fetchone()[0])
        css = next(iter(models.values()))["css"]
        assert DEVANAGARI_FONT.name in css and BENGALI_FONT.name in css
        assert "'Geo Anki Custom', 'Geo Anki Fallback 0', sans-serif" in css
        assert connection.execute("SELECT count(*) FROM cards").fetchone()[0] == 3


def test_validation_leaves_no_partial_outputs(dataset, tmp_path):
    targets = tmp_path / "targets.txt"
    targets.write_text("Pune\nUnknown district\n")
    output = tmp_path / "out/india.apkg"
    with pytest.raises(ValueError, match="Unknown"):
        build_india(targets, output, dataset, "Test")
    assert not output.parent.exists()


def test_language_policy_font_coverage_and_shipped_lists():
    assert set(REFERENCE_CITIES) == set(STATES)
    assert FRONT_LANGUAGES["27"] == "mr" and FRONT_LANGUAGES["30"] == "kok"
    assert FRONT_LANGUAGES["11"] == "ne"
    assert {k for k, v in FRONT_LANGUAGES.items() if v == "bn"} == {"16", "19"}
    assert not {"3", "18", "28"}.intersection(FRONT_LANGUAGES)
    for path, low, high in (
        (DEVANAGARI_FONT, 0x900, 0x97F),
        (BENGALI_FONT, 0x980, 0x9FF),
    ):
        with TTFont(path) as font:
            cmap = font.getBestCmap()
        assert cmap is not None
        needed = {
            ord(c)
            for name in NATIVE_NAMES.values()
            for c in name
            if low <= ord(c) <= high
        }
        assert needed.issubset(cmap)
    root = Path(__file__).resolve().parents[1]
    targets = [
        s
        for s in (root / "targets/india.txt").read_text().splitlines()
        if s and not s.startswith("#")
    ]
    assert len(targets) == len(set(targets)) == 731
    assert {s.split(" — ")[1] for s in targets} == set(STATES.values())
    examples = [
        s
        for s in (root / "examples/india.txt").read_text().splitlines()
        if s and not s.startswith("#")
    ]
    assert len(examples) == 10 and set(examples).issubset(targets)
