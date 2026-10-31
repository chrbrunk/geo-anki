import io
import json
import sqlite3
import sys
import warnings
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZipFile

import geopandas as gpd
import pytest
from matplotlib.axes import Axes
from PIL import Image
from shapely.geometry import MultiPolygon, Polygon, box

from geo_anki.countries.japan import data
from geo_anki.countries.japan.build import build_japan
from geo_anki.countries.japan.maps import (
    FONT_LICENSE,
    JAPANESE_FONT,
    MAIN_BOUNDS,
    MAP_CRS,
    OKINAWA_BOUNDS,
    REFERENCE_CITIES,
    display_geometry,
    render_map,
)
from geo_anki.countries.japan.prefectures import PREFECTURES
from geo_anki.scripts import run
from geo_anki.utils.anki import stable_id


@pytest.fixture
def dataset(tmp_path):
    """Create a source-format ZIP with mainland, northern, and remote polygons."""
    frame = gpd.GeoDataFrame(
        {"P": ["東京都", "北海道", "沖縄県"]},
        geometry=[box(139, 35, 140, 36), box(140, 42, 144, 45), box(123, 24, 128, 27)],
        crs=4326,
    )
    path = tmp_path / "source.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("source/output/prefectures.geojson", frame.to_json())
    return path


def test_matching(dataset):
    """Resolve both scripts, suffix-free names and JIS codes in request order."""
    frame = data.load_data(dataset)
    assert frame.crs.to_epsg() == 4326
    selected = data.select_targets(frame, ["  HOKKAIDO ", "東京", "47"])
    assert selected.name_en.tolist() == ["Hokkaido", "Tokyo", "Okinawa"]
    assert selected.prefecture_code.tolist() == ["01", "13", "47"]
    assert len(PREFECTURES) == 47


@pytest.mark.parametrize(
    "names,message",
    [
        ([], "empty"),
        (["Tokyo", "東京都"], "Duplicate"),
        (["沖縄", "47"], "Duplicate"),
        (["Atlantis"], "Unknown prefecture"),
    ],
)
def test_invalid_targets(dataset, names, message):
    """Reject empty, unknown and cross-script/code duplicate requests."""
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
    "problem,message",
    [
        ("unknown", "Unknown prefecture"),
        ("null", "Missing prefecture names"),
        ("duplicate", "Duplicate prefecture"),
        ("field", "required names"),
        ("empty", "required names"),
        ("member", "Expected one reasonably sized"),
        ("line", "nonempty polygon"),
    ],
)
def test_invalid_source(dataset, problem, message):
    """Reject malformed archives, names and non-polygon geometry."""
    with ZipFile(dataset) as archive:
        payload = json.loads(archive.read("source/output/prefectures.geojson"))
    features = payload["features"]
    if problem == "unknown":
        features[0]["properties"]["P"] = "unknown"
    elif problem == "null":
        features[0]["properties"]["P"] = None
    elif problem == "duplicate":
        features[1] = features[0]
    elif problem == "field":
        for feature in features:
            feature["properties"] = {}
    elif problem == "empty":
        payload["features"] = []
    elif problem == "line":
        features[0]["geometry"] = {
            "type": "LineString",
            "coordinates": [[139, 35], [140, 36]],
        }
    with ZipFile(dataset, "w") as archive:
        member = (
            "wrong.geojson"
            if problem == "member"
            else "source/output/prefectures.geojson"
        )
        archive.writestr(member, json.dumps(payload))
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_repair_and_reprojection(dataset):
    """Repair a self-crossing polygon and restore geographic coordinates."""
    frame = data.load_data(dataset)
    frame.loc[0, "geometry"] = Polygon(
        [(139, 35), (140, 36), (139, 36), (140, 35), (139, 35)]
    )
    with ZipFile(dataset, "w") as archive:
        archive.writestr(
            "source/output/prefectures.geojson", frame.to_crs(3857).to_json()
        )
    with pytest.warns(UserWarning, match="Repairing invalid prefecture"):
        result = data.load_data(dataset)
    assert result.is_valid.all()
    assert result.crs.to_epsg() == 4326
    assert result.iloc[0].geometry.bounds == pytest.approx((139, 35, 140, 36))


def test_bilingual_map_and_cities(dataset, tmp_path):
    """Render shaped Japanese titles, English names, and all reference cities.

    Args:
        dataset: Bilingual archive fixture.
        tmp_path: Directory for the map.

    Returns:
        None. Asserts bilingual text, city routing, separate extents and valid PNG.
    """
    prefectures = data.load_data(dataset)
    target = data.select_targets(prefectures, ["東京都"])
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
            Axes, "set_xlim", autospec=True, side_effect=Axes.set_xlim
        ) as xlim,
        patch.object(
            Axes, "set_ylim", autospec=True, side_effect=Axes.set_ylim
        ) as ylim,
    ):
        render_map(prefectures, target, output)
    assert title.call_args.args[1] == "東京都"
    assert title.call_args.kwargs["language"] == "ja"
    assert title.call_args.kwargs["fontproperties"].get_file() == str(JAPANESE_FONT)
    assert any(len(c.args) > 3 and c.args[3] == "Tokyo" for c in text.call_args_list)
    assert {c.args[1] for c in cities.call_args_list} == {
        c[0] for c in REFERENCE_CITIES
    }
    assert not any("Glyph" in str(w.message) for w in emitted)
    main_ax = title.call_args.args[0]
    inset_ax = next(
        c.args[0]
        for c in title.call_args_list
        if c.args[1] == "Okinawa · location inset"
    )
    for ax, bounds in ((main_ax, MAIN_BOUNDS), (inset_ax, OKINAWA_BOUNDS)):
        projected = gpd.GeoSeries([box(*bounds)], crs=4326).to_crs(MAP_CRS)
        xmin, ymin, xmax, ymax = projected.total_bounds
        assert any(
            c.args[0] is ax and c.args[1:] == pytest.approx((xmin, xmax))
            for c in xlim.call_args_list
            if len(c.args) == 3
        )
        assert any(
            c.args[0] is ax and c.args[1:] == pytest.approx((ymin, ymax))
            for c in ylim.call_args_list
            if len(c.args) == 3
        )
    for call in cities.call_args_list:
        assert call.args[0] is (inset_ax if call.args[1] == "Naha" else main_ax)
    assert all(spine.get_visible() for spine in inset_ax.spines.values())
    with Image.open(output) as image:
        assert image.size == (1600, 1440)


@pytest.mark.parametrize("local_data", [True, False])
def test_cli_japanese_fronts_and_embedded_font(
    dataset, tmp_path, monkeypatch, local_data
):
    """Build cards with Japanese district names and an embedded Japanese font.

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
        "\ufeff# Mixed input scripts\n東京都\n\nHokkaido\n", encoding="utf-8"
    )
    arguments = ["geo_anki", "--country", "Japan", "--targets", str(targets)]
    if local_data:
        arguments.extend(["--data", str(dataset)])
    monkeypatch.setattr(sys, "argv", arguments)
    download = Mock(return_value=dataset)
    monkeypatch.setitem(
        run.COUNTRIES,
        "japan",
        replace(run.COUNTRIES["japan"], download_data=download),
    )
    run.main()
    if local_data:
        download.assert_not_called()
    else:
        download.assert_called_once_with(Path(".cache/geo-anki"))
    output = tmp_path / "outputs/japan.apkg"
    with ZipFile(output) as z:
        media = json.loads(z.read("media"))
        assert len(media) == 4
        assets = {name: z.read(key) for key, name in media.items()}
        assert assets[JAPANESE_FONT.name] == JAPANESE_FONT.read_bytes()
        assert assets[FONT_LICENSE.name] == FONT_LICENSE.read_bytes()
        assert sum(value.startswith(b"\x89PNG") for value in assets.values()) == 2
        database = tmp_path / "collection.sqlite"
        database.write_bytes(z.read("collection.anki2"))
    with sqlite3.connect(database) as c:
        notes = c.execute("SELECT mid, flds FROM notes ORDER BY id").fetchall()
        fields = [note[1].split("\x1f") for note in notes]
        assert [f[:2] for f in fields] == [
            ["Japan: 東京都", "Tokyo"],
            ["Japan: 北海道", "Hokkaido"],
        ]
        assert notes[0][0] != stable_id("geo-anki:map-model:v1")
        models = json.loads(c.execute("SELECT models FROM col").fetchone()[0])
        assert "@font-face" in models[str(notes[0][0])]["css"]
        assert JAPANESE_FONT.name in models[str(notes[0][0])]["css"]
        assert c.execute("SELECT count(*) FROM cards").fetchone()[0] == 2
        decks = json.loads(c.execute("SELECT decks FROM col").fetchone()[0])
        assert "Geo Anki::Japan" in [d["name"] for d in decks.values()]
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert [card["name_ja"] for card in manifest["cards"]] == ["東京都", "北海道"]
    assert manifest["default_revision"] == data.DATA_REVISION


def test_bad_target_creates_no_output(dataset, tmp_path):
    """Validate targets before creating map and deck files."""
    targets = tmp_path / "targets.txt"
    targets.write_text("Atlantis\n")
    output = tmp_path / "deck.apkg"
    with pytest.raises(ValueError, match="Unknown prefecture"):
        build_japan(targets, output, dataset, "Japan")
    assert not output.exists()
    assert not (tmp_path / "deck_maps").exists()


def test_islands_are_display_only_and_okinawa_is_separate(dataset):
    """Omit remote Tokyo islands and route Okinawa to its inset without data loss."""
    frame = data.load_data(dataset)
    mainland = frame.iloc[0].geometry
    frame.loc[0, "geometry"] = MultiPolygon(
        [mainland, box(139.3, 34.6, 139.5, 34.8), box(153.8, 24.2, 154, 24.4)]
    )
    before = frame.copy(deep=True)
    main = display_geometry(frame, inset=False).to_crs(4326)
    inset = display_geometry(frame, inset=True).to_crs(4326)
    assert set(main.name_en) == {"Tokyo", "Hokkaido"}
    assert inset.name_en.tolist() == ["Okinawa"]
    assert main.loc[main.name_en == "Tokyo"].total_bounds == pytest.approx(
        mainland.bounds
    )
    assert display_geometry(frame.loc[frame.name_en == "Okinawa"], inset=False).empty
    assert display_geometry(frame.loc[frame.name_en == "Tokyo"], inset=True).empty
    assert frame.equals(before)
