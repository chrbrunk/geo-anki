import hashlib
import io
import json
import sqlite3
import sys
import unicodedata
from dataclasses import replace
from unittest.mock import Mock, patch
from zipfile import ZipFile

import brotli
import geopandas as gpd
import pytest
from matplotlib.axes import Axes
from PIL import Image
from shapely.geometry import Polygon, box

from geo_anki.countries.germany import data
from geo_anki.countries.germany.maps import render_map
from geo_anki.countries.germany.regions import REFERENCE_CITIES
from geo_anki.scripts import run


@pytest.fixture
def dataset(tmp_path):
    """Create source-format layers with a city/county name pair and water duplicates.

    Args:
        tmp_path: Directory for the archive.

    Returns:
        ZIP containing synthetic Bayern/Sachsen-Anhalt state and district polygons.
    """
    states = gpd.GeoDataFrame(
        {
            "AGS": ["09", "15", "09"],
            "GEN": ["Bayern", "Sachsen-Anhalt", "Bayern"],
            "BEZ": ["Freistaat", "Land", "Freistaat"],
            "GF": [4, 4, 2],
        },
        geometry=[box(9, 47, 14, 50), box(10, 52, 13, 54), box(9, 47, 14, 50)],
        crs=4326,
    )
    districts = gpd.GeoDataFrame(
        {
            "AGS": ["09184", "09162", "15090", "09184"],
            "GEN": ["München", "München", "Stendal", "München"],
            "BEZ": ["Landkreis", "Kreisfreie Stadt", "Landkreis", "Landkreis"],
            "GF": [4, 4, 4, 2],
        },
        geometry=[
            box(11, 48, 12, 49),
            box(11.4, 48.1, 11.7, 48.3),
            box(11, 52.5, 12, 53.5),
            box(11, 48, 12, 49),
        ],
        crs=4326,
    )
    archive = tmp_path / "boundaries.zip"
    with ZipFile(archive, "w") as z:
        z.writestr(
            "1_bundeslaender.geojson.br", brotli.compress(states.to_json().encode())
        )
        z.writestr("3_kreise.geojson.br", brotli.compress(districts.to_json().encode()))
    return archive


def test_city_county_names_and_water_filter(dataset):
    """Select the Landkreis by default and distinguish the same-named city.

    Args:
        dataset: Source-format boundary archive.

    Returns:
        None. Asserts water duplicates are removed and official IDs remain intact.
    """
    states, districts = data.load_data(dataset)
    assert len(states) == 2 and len(districts) == 3
    assert districts.crs.to_epsg() == 4326
    selected = data.select_targets(
        districts, ["  MÜNCHEN  ", "München (kreisfreie Stadt)", "15090"]
    )
    assert selected.AGS.tolist() == ["09184", "09162", "15090"]
    assert selected.state.tolist() == ["Bayern", "Bayern", "Sachsen-Anhalt"]
    assert data.normalize(unicodedata.normalize("NFD", "München")) == "münchen"
    assert set(REFERENCE_CITIES) == {f"{i:02}" for i in range(1, 17)}


@pytest.mark.parametrize(
    "names, message",
    [
        ([], "empty"),
        (["München", "09184"], "Duplicate"),
        (["Missing county"], "Unknown district"),
    ],
)
def test_invalid_targets(dataset, names, message):
    """Reject empty, duplicate, and unknown target selections.

    Args:
        dataset: Source-format boundary archive.
        names: Invalid requested names.
        message: Expected error pattern.

    Returns:
        None. Asserts a useful validation error.
    """
    _, districts = data.load_data(dataset)
    with pytest.raises(ValueError, match=message):
        data.select_targets(districts, names)


def test_download_and_cache_checksums(dataset, tmp_path, monkeypatch):
    """Verify both source files before caching and detect later cache corruption.

    Args:
        dataset: Archive whose compressed members act as HTTP responses.
        tmp_path: Temporary cache directory.
        monkeypatch: Helper for replacing checksums and HTTP requests.

    Returns:
        None. Asserts two downloads, cache reuse, and corruption rejection.
    """
    with ZipFile(dataset) as z:
        members = {name: z.read(name) for name in z.namelist()}
    monkeypatch.setattr(
        data,
        "DATA_FILES",
        {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in members.items()
        },
    )
    download = Mock(
        side_effect=lambda url, timeout: io.BytesIO(members[url.rsplit("/", 1)[1]])
    )
    monkeypatch.setattr(data, "urlopen", download)
    cached = data.download_data(tmp_path / "cache")
    assert data.download_data(tmp_path / "cache") == cached
    assert download.call_count == 2
    with ZipFile(cached, "w") as z:
        for name in members:
            z.writestr(name, b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(tmp_path / "cache")
    with ZipFile(cached, "w") as z:
        z.writestr("unexpected", b"data")
    with pytest.raises(ValueError, match="exactly the pinned"):
        data.download_data(tmp_path / "cache")


@pytest.mark.parametrize(
    "problem, message",
    [
        ("missing_layer", "Expected one reasonably sized"),
        ("bad_compression", "Invalid compressed"),
        ("missing_fields", "Missing required boundary fields"),
        ("no_land", "Missing land-area records"),
        ("missing_name", "Missing boundary names"),
        ("empty_name", "Empty boundary names"),
        ("bad_code", "Invalid official boundary codes"),
        ("duplicate_code", "Duplicate boundary codes"),
        ("unknown_state", "unknown Bundesland"),
        ("bad_type", "Unsupported district type"),
        ("duplicate_label", "Ambiguous district target"),
        ("line_geometry", "nonempty polygon"),
    ],
)
def test_invalid_data(dataset, problem, message):
    """Reject malformed source layers and broken state/district identities.

    Args:
        dataset: Archive fixture to modify.
        problem: Invalid data scenario.
        message: Expected error pattern.

    Returns:
        None. Asserts bad input is rejected before rendering.
    """
    with ZipFile(dataset) as z:
        members = {name: z.read(name) for name in z.namelist()}
    name = "3_kreise.geojson.br"
    layer = json.loads(brotli.decompress(members[name]))
    first, second = layer["features"][:2]
    if problem == "missing_fields":
        for f in layer["features"]:
            del f["properties"]["AGS"]
    elif problem == "no_land":
        for f in layer["features"]:
            f["properties"]["GF"] = 2
    elif problem == "missing_name":
        first["properties"]["GEN"] = None
    elif problem == "empty_name":
        first["properties"]["GEN"] = " "
    elif problem == "bad_code":
        first["properties"]["AGS"] = "9184"
    elif problem == "duplicate_code":
        second["properties"]["AGS"] = first["properties"]["AGS"]
    elif problem == "unknown_state":
        first["properties"]["AGS"] = "99184"
    elif problem == "bad_type":
        first["properties"]["BEZ"] = "Unknown"
    elif problem == "duplicate_label":
        second["properties"]["BEZ"] = "Landkreis"
    elif problem == "line_geometry":
        first["geometry"] = {"type": "LineString", "coordinates": [[11, 48], [12, 49]]}
    members[name] = brotli.compress(json.dumps(layer).encode())
    if problem == "missing_layer":
        del members[name]
    elif problem == "bad_compression":
        members[name] = b"not brotli"
    with ZipFile(dataset, "w") as z:
        for name, payload in members.items():
            z.writestr(name, payload)
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_geometry_repair_and_reprojection(dataset):
    """Repair self-intersecting polygons and normalize projected source data.

    Args:
        dataset: Archive fixture to modify.

    Returns:
        None. Asserts valid repaired geometry in EPSG:4326.
    """
    with ZipFile(dataset) as z:
        members = {name: z.read(name) for name in z.namelist()}
    name = "3_kreise.geojson.br"
    frame = gpd.read_file(io.BytesIO(brotli.decompress(members[name])))
    frame.loc[0, "geometry"] = Polygon(
        [(11, 48), (12, 49), (11, 49), (12, 48), (11, 48)]
    )
    members[name] = brotli.compress(frame.to_crs(3857).to_json().encode())
    with ZipFile(dataset, "w") as z:
        for name, payload in members.items():
            z.writestr(name, payload)
    with pytest.warns(UserWarning, match="Repairing invalid"):
        _, districts = data.load_data(dataset)
    assert districts.crs.to_epsg() == 4326
    assert districts.is_valid.all()
    assert districts.iloc[0].geometry.geom_type == "MultiPolygon"


def test_state_extent_and_reference_cities(dataset, tmp_path):
    """Show the entire target state rather than the district or whole country.

    Args:
        dataset: Two-state boundary archive.
        tmp_path: Directory for the rendered map.

    Returns:
        None. Asserts state framing, state-specific city labels, and valid PNG.
    """
    states, districts = data.load_data(dataset)
    target = data.select_targets(districts, ["München (kreisfreie Stadt)"])
    output = tmp_path / "map.png"
    with (
        patch.object(
            Axes, "set_ylim", autospec=True, side_effect=Axes.set_ylim
        ) as ylim,
        patch.object(
            Axes, "annotate", autospec=True, side_effect=Axes.annotate
        ) as cities,
        patch.object(
            Axes, "set_title", autospec=True, side_effect=Axes.set_title
        ) as title,
    ):
        render_map(states, districts, target, output)
    bayern = states[states.AGS == "09"].to_crs(3035).total_bounds
    other = states[states.AGS == "15"].to_crs(3035).total_bounds
    assert ylim.call_args.args[1] < bayern[1]
    assert bayern[3] < ylim.call_args.args[2] < other[1]
    assert {c.args[1] for c in cities.call_args_list} == {
        c[0] for c in REFERENCE_CITIES["09"]
    }
    assert title.call_args.args[1] == "München (kreisfreie Stadt)"
    with Image.open(output) as image:
        assert image.size == (1600, 1440)


@pytest.mark.parametrize("local_data", [True, False])
def test_cli_state_answers_and_embedded_maps(
    dataset, tmp_path, monkeypatch, local_data
):
    """Build real packages with county/city distinctions and Bundesland answers.

    Args:
        dataset: Two-state boundary archive.
        tmp_path: Working directory for CLI defaults.
        monkeypatch: Helper for the downloader and CLI arguments.
        local_data: Whether to use an explicit local archive.

    Returns:
        None. Asserts front/back text, media, stable codes, and manifest contents.
    """
    monkeypatch.chdir(tmp_path)
    targets = tmp_path / "targets.txt"
    targets.write_text(
        "\ufeff# Kreis and city\nMünchen\nMünchen (kreisfreie Stadt)\nStendal\n",
        encoding="utf-8",
    )
    arguments = ["geo_anki", "--country", "Germany", "--targets", str(targets)]
    if local_data:
        arguments.extend(["--data", str(dataset)])
    monkeypatch.setattr(sys, "argv", arguments)
    download = Mock(return_value=dataset)
    monkeypatch.setitem(
        run.COUNTRIES,
        "germany",
        replace(run.COUNTRIES["germany"], download_data=download),
    )
    run.main()
    if local_data:
        download.assert_not_called()
    else:
        download.assert_called_once_with(run.Path(".cache/geo-anki"))
    output = tmp_path / "outputs/germany.apkg"
    with ZipFile(output) as z:
        media = json.loads(z.read("media"))
        assert len(media) == 3
        assert all(z.read(key).startswith(b"\x89PNG") for key in media)
        db = tmp_path / "c.sqlite"
        db.write_bytes(z.read("collection.anki2"))
    with sqlite3.connect(db) as c:
        notes = c.execute("SELECT guid, flds FROM notes ORDER BY id").fetchall()
        assert [row[1].split("\x1f")[:2] for row in notes] == [
            ["Germany: München", "Bayern"],
            ["Germany: München (kreisfreie Stadt)", "Bayern"],
            ["Germany: Stendal", "Sachsen-Anhalt"],
        ]
        assert len({row[0] for row in notes}) == 3
        assert c.execute("SELECT count(*) FROM cards").fetchone()[0] == 3
        decks = json.loads(c.execute("SELECT decks FROM col").fetchone()[0])
        assert "Geo Anki::Germany" in [d["name"] for d in decks.values()]
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert [card["ags"] for card in manifest["cards"]] == ["09184", "09162", "15090"]
    assert [card["state"] for card in manifest["cards"]] == [
        "Bayern",
        "Bayern",
        "Sachsen-Anhalt",
    ]
