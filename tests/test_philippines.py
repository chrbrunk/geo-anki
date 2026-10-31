import io
import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZipFile

import geopandas as gpd
import pytest
from matplotlib.axes import Axes
from PIL import Image
from shapely.geometry import MultiPolygon, Point, Polygon, box

from geo_anki.countries.philippines import data
from geo_anki.countries.philippines.build import build_philippines
from geo_anki.countries.philippines.maps import render_map
from geo_anki.countries.philippines.references import REFERENCE_PLACES
from geo_anki.scripts import run


@pytest.fixture
def dataset(tmp_path):
    """Create province and non-province layers in the source archive layout.

    Args:
        tmp_path: Temporary directory for the archive.

    Returns:
        ZIP containing two provinces and a separate context district.
    """
    frame = gpd.GeoDataFrame(
        {
            "adm2_en": ["Batanes", "Cebu", "NCR, First District"],
            "adm2_psgc": [200900000, 702200000, 1303900000],
            "geo_level": ["Prov", "Prov", "Dist"],
        },
        geometry=[
            box(121.8, 20.3, 122, 20.5),
            box(123, 10, 124, 11),
            box(120, 14, 121, 15),
        ],
        crs=4326,
    )
    archive = tmp_path / "boundaries.zip"
    with ZipFile(archive, "w") as z:
        for index in (0, 1, 2):
            z.writestr(
                f"source/latest/geojson/regions/medres/provdists-region-{index}.0.01.json",
                frame.iloc[[index]].to_json(),
            )
        # Other resolutions must not introduce duplicate provinces.
        z.writestr(
            "source/latest/geojson/regions/lowres/provdists-region-0.0.001.json",
            frame.to_json(),
        )
    return archive


def test_loading_and_matching(dataset):
    """Verify context retention, exact resolution selection, and ordered matching.

    Args:
        dataset: Province/district archive fixture.

    Returns:
        None. Asserts names, codes, CRS, and matching behavior.
    """
    boundaries = data.load_data(dataset)
    assert len(boundaries) == 3
    assert boundaries.crs.to_epsg() == 4326
    selected = data.select_targets(boundaries, ["  CEBU  ", "batanes"])
    assert selected.adm2_en.tolist() == ["Cebu", "Batanes"]
    assert selected.adm2_psgc.tolist() == ["702200000", "200900000"]


@pytest.mark.parametrize(
    "names, message",
    [
        ([], "empty"),
        (["Cebu", "CEBU"], "Duplicate"),
        (["Ceb"], "Unknown province.*cebu"),
        (["NCR, First District"], "Unknown province"),
    ],
)
def test_invalid_targets(dataset, names, message):
    """Reject invalid requests and prevent selecting districts as provinces.

    Args:
        dataset: Province/district archive fixture.
        names: Requested province names.
        message: Expected error pattern.

    Returns:
        None. Asserts a useful ValueError.
    """
    with pytest.raises(ValueError, match=message):
        data.select_targets(data.load_data(dataset), names)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("adm2_en", None, "Missing boundary names"),
        ("adm2_en", "  ", "Empty boundary names"),
        ("adm2_psgc", None, "Missing boundary names or codes"),
        ("adm2_psgc", 702200000, "Duplicate boundary codes"),
        ("adm2_en", "Cebu", "Duplicate province names"),
    ],
)
def test_invalid_data(dataset, field, value, message):
    """Reject malformed names, missing codes, and duplicate identities.

    Args:
        dataset: Archive fixture to modify.
        field: Property to replace in the first province.
        value: Invalid replacement value.
        message: Expected error pattern.

    Returns:
        None. Asserts invalid data is rejected before generating maps.
    """
    with ZipFile(dataset) as z:
        layers = {name: z.read(name) for name in z.namelist()}
    name = next(iter(layers))
    layer = json.loads(layers[name])
    layer["features"][0]["properties"][field] = value
    layers[name] = json.dumps(layer).encode()
    with ZipFile(dataset, "w") as z:
        for name, payload in layers.items():
            z.writestr(name, payload)
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_download_cache_and_checksum(tmp_path, monkeypatch):
    """Verify that downloads and cached data are checksum-verified.

    Args:
        tmp_path: Temporary cache directory.
        monkeypatch: Helper for replacing the download and expected hash.

    Returns:
        None. Asserts one download, cache reuse, and corruption rejection.
    """
    payload = b"boundary archive"
    monkeypatch.setattr(data, "DATA_SHA256", data.hashlib.sha256(payload).hexdigest())
    download = Mock(side_effect=lambda *args, **kwargs: io.BytesIO(payload))
    monkeypatch.setattr(data, "urlopen", download)
    path = data.download_data(tmp_path)
    assert data.download_data(tmp_path) == path
    download.assert_called_once_with(data.DATA_URL, timeout=120)
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        data.download_data(tmp_path)


def test_map_uses_whole_country(dataset, tmp_path):
    """Verify the extent includes distant provinces and non-province context.

    Args:
        dataset: Archive with distant provinces and a context district.
        tmp_path: Directory for the rendered PNG.

    Returns:
        None. Asserts the complete extent and a nonempty map image.
    """
    boundaries = data.load_data(dataset)
    target = data.select_targets(boundaries, ["Cebu"])
    output = tmp_path / "map.png"
    with (
        patch.object(
            Axes, "set_xlim", autospec=True, side_effect=Axes.set_xlim
        ) as xlim,
        patch.object(
            Axes, "set_ylim", autospec=True, side_effect=Axes.set_ylim
        ) as ylim,
    ):
        render_map(boundaries, target, output)
    projected = boundaries.to_crs(
        "+proj=merc +lon_0=122 +datum=WGS84 +units=m +no_defs"
    )
    xmin, ymin, xmax, ymax = projected.total_bounds
    assert xlim.call_args.args[1] < xmin
    assert xlim.call_args.args[2] > xmax
    assert ylim.call_args.args[1] < ymin
    assert ylim.call_args.args[2] > ymax
    with Image.open(output) as image:
        assert image.size == (1600, 1440)
        colors = image.convert("RGB").getcolors(image.width * image.height)
        assert colors is not None and len(colors) > 20


@pytest.mark.parametrize("local_data", [True, False])
def test_cli_builds_deck(dataset, tmp_path, monkeypatch, capsys, local_data):
    """Verify country dispatch, downloads, defaults, packaged cards, and media.

    Args:
        dataset: Province/district archive fixture.
        tmp_path: Directory for targets and default output files.
        monkeypatch: Helper for replacing CLI arguments and country download.
        capsys: Captured CLI output.
        local_data: Whether to provide an explicit local archive.

    Returns:
        None. Asserts correct Philippines cards, deck, images, and manifest.
    """
    monkeypatch.chdir(tmp_path)
    targets = tmp_path / "targets.txt"
    targets.write_text("\ufeff# provinces\n  Cebu  \n\nBatanes\n", encoding="utf-8")
    arguments = ["geo_anki", "--country", "Philippines", "--targets", str(targets)]
    if local_data:
        arguments.extend(["--data", str(dataset)])
    monkeypatch.setattr(sys, "argv", arguments)
    download = Mock(return_value=dataset)
    monkeypatch.setitem(
        run.COUNTRIES,
        "philippines",
        replace(run.COUNTRIES["philippines"], download_data=download),
    )
    run.main()
    assert (
        "Created outputs/philippines.apkg: 2 cards and 2 PNG maps"
        in capsys.readouterr().out
    )
    if local_data:
        download.assert_not_called()
    else:
        download.assert_called_once_with(run.Path(".cache/geo-anki"))
    output = tmp_path / "outputs/philippines.apkg"
    with ZipFile(output) as z:
        media = json.loads(z.read("media"))
        assert len(media) == 2
        assert all(z.read(key).startswith(b"\x89PNG") for key in media)
        database = tmp_path / "collection.sqlite"
        database.write_bytes(z.read("collection.anki2"))
    with sqlite3.connect(database) as connection:
        notes = connection.execute("SELECT flds FROM notes ORDER BY id").fetchall()
        assert [note[0].split("\x1f")[:2] for note in notes] == [
            ["Philippines: Cebu", "Cebu"],
            ["Philippines: Batanes", "Batanes"],
        ]
        assert connection.execute("SELECT count(*) FROM cards").fetchone()[0] == 2
        decks = json.loads(connection.execute("SELECT decks FROM col").fetchone()[0])
        assert "Geo Anki::Philippines" in [deck["name"] for deck in decks.values()]
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert manifest["default_revision"] == data.DATA_REVISION
    assert manifest["attribution"] == data.DATA_ATTRIBUTION
    assert [card["name"] for card in manifest["cards"]] == ["Cebu", "Batanes"]


def test_invalid_target_creates_no_deck(dataset, tmp_path):
    """Verify an invalid province is rejected before rendering or packaging.

    Args:
        dataset: Province/district archive fixture.
        tmp_path: Directory for targets and outputs.

    Returns:
        None. Asserts failure leaves no deck or map directory.
    """
    targets = tmp_path / "targets.txt"
    targets.write_text("Unknown province\n")
    output = tmp_path / "deck.apkg"
    with pytest.raises(ValueError, match="Unknown province"):
        build_philippines(targets, output, dataset, "Test deck")
    assert not output.exists()
    assert not output.with_suffix(".json").exists()
    assert not (tmp_path / "deck_maps").exists()


@pytest.mark.parametrize(
    "name",
    [
        "Batanes",
        "Camiguin",
        "Siquijor",
        "Biliran",
        "Guimaras",
        "Marinduque",
        "Dinagat Islands",
        "Basilan",
        "Tawi-Tawi",
        "Rizal",
        "Cebu",
    ],
)
def test_small_province_arrows(dataset, tmp_path, name):
    """Point at small provinces' largest island, leaving larger provinces unmarked.

    Args:
        dataset: Archive fixture providing map context.
        tmp_path: Directory for the rendered map.
        name: Small province or a larger comparison province.

    Returns:
        None. Asserts pointer visibility, color, and an on-land destination.
    """
    boundaries = data.load_data(dataset)
    target = boundaries.iloc[[0]].copy()
    target["adm2_en"] = name
    largest = box(121.8, 20.3, 122, 20.5)
    target.geometry = [MultiPolygon([box(121.7, 20.6, 121.72, 20.62), largest])]
    with patch.object(
        Axes, "annotate", autospec=True, side_effect=Axes.annotate
    ) as arrow:
        render_map(boundaries, target, tmp_path / f"{name}.png")
    if name == "Cebu":
        arrow.assert_not_called()
    else:
        arrow.assert_called_once()
        assert arrow.call_args.kwargs["arrowprops"]["color"] == "#f18d32"
        x, y = arrow.call_args.kwargs["xy"]
        projected = gpd.GeoSeries([largest], crs=4326).to_crs(
            "+proj=merc +lon_0=122 +datum=WGS84 +units=m +no_defs"
        )
        assert projected.iloc[0].contains(Point(x, y))


@pytest.mark.parametrize(
    "problem, message",
    [
        ("missing_fields", "Missing records or required"),
        ("empty_layer", "Missing records or required"),
        ("no_provinces", "no provinces"),
        ("missing_geometry", "nonempty polygon"),
        ("line_geometry", "nonempty polygon"),
        ("no_layers", "Expected unique province/district layers"),
    ],
)
def test_invalid_boundary_layers(dataset, problem, message):
    """Reject incomplete archives and unsuitable geometry before map generation.

    Args:
        dataset: Archive fixture to modify.
        problem: Invalid archive or geometry scenario.
        message: Expected validation error.

    Returns:
        None. Asserts corrupt or incomplete input is rejected.
    """
    with ZipFile(dataset) as z:
        layers = {name: json.loads(z.read(name)) for name in z.namelist()}
    for layer in layers.values():
        if problem == "empty_layer":
            layer["features"] = []
        for feature in layer["features"]:
            if problem == "missing_fields":
                del feature["properties"]["adm2_en"]
            elif problem == "no_provinces":
                feature["properties"]["geo_level"] = "Dist"
            elif problem == "missing_geometry":
                feature["geometry"] = None
            elif problem == "line_geometry":
                feature["geometry"] = {
                    "type": "LineString",
                    "coordinates": [[121, 10], [122, 11]],
                }
    with ZipFile(dataset, "w") as z:
        if problem != "no_layers":
            for name, layer in layers.items():
                z.writestr(name, json.dumps(layer))
    with pytest.raises(ValueError, match=message):
        data.load_data(dataset)


def test_geometry_repair_and_reprojection(dataset):
    """Repair self-intersections and normalize projected coordinates to WGS84.

    Args:
        dataset: Archive fixture to replace with projected boundary layers.

    Returns:
        None. Asserts repaired shapes and correct geographic coordinates.
    """
    boundaries = data.load_data(dataset)
    boundaries.loc[0, "geometry"] = Polygon(
        [(121, 20), (122, 21), (121, 21), (122, 20), (121, 20)]
    )
    with ZipFile(dataset, "w") as z:
        z.writestr(
            "source/latest/geojson/regions/medres/provdists-region-0.0.01.json",
            boundaries.to_crs(3857).to_json(),
        )
    with pytest.warns(UserWarning, match="Repairing invalid geometries"):
        result = data.load_data(dataset)
    assert result.crs.to_epsg() == 4326
    assert result.is_valid.all()
    assert result.iloc[0].geometry.geom_type == "MultiPolygon"
    assert result.iloc[0].geometry.bounds == pytest.approx((121, 20, 122, 21))


def test_reference_places_cover_all_provinces():
    """Keep the curated reference mapping in sync with the full province list.

    Returns:
        None. Asserts every supported province has a named city or town.
    """
    targets = Path(__file__).resolve().parents[1] / "targets/philippines.txt"
    names = {
        line.strip()
        for line in targets.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert len(names) == 82
    assert names == set(REFERENCE_PLACES)
    assert all(place.name.strip() for place in REFERENCE_PLACES.values())
    assert all(place.kind in {"city", "town"} for place in REFERENCE_PLACES.values())


@pytest.mark.parametrize(
    "province, subtitle",
    [("Cebu", "Reference city: Cebu City"), ("Batanes", "Reference town: Basco")],
)
def test_reference_subtitle(dataset, tmp_path, province, subtitle):
    """Use a smaller subtitle and distinguish cities from reference towns.

    Args:
        dataset: Province/district archive fixture.
        tmp_path: Directory for the rendered map.
        province: Province with a city or town reference.
        subtitle: Expected reference-place label.

    Returns:
        None. Asserts correct labeling and a smaller reference font.
    """
    boundaries = data.load_data(dataset)
    target = data.select_targets(boundaries, [province])
    with (
        patch.object(
            Axes, "set_title", autospec=True, side_effect=Axes.set_title
        ) as title,
        patch.object(Axes, "text", autospec=True, side_effect=Axes.text) as text,
    ):
        render_map(boundaries, target, tmp_path / "reference.png")
    assert title.call_args.args[1] == province
    labels = [
        call
        for call in text.call_args_list
        if len(call.args) > 3 and call.args[3] == subtitle
    ]
    assert len(labels) == 1
    assert labels[0].kwargs["fontsize"] < title.call_args.kwargs["fontsize"]
