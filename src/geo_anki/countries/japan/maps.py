from pathlib import Path

import geopandas as gpd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch
from shapely.geometry import box

from geo_anki.countries.japan.data import DATA_ATTRIBUTION

JAPANESE_FONT = Path(__file__).parent / "fonts/GeoAnkiJapanese.otf"
FONT_LICENSE = Path(__file__).parent / "fonts/GeoAnkiJapanese-LICENSE.txt"

# City name, longitude, latitude, and label offsets in display points.
REFERENCE_CITIES = (
    ("Sapporo", 141.3544, 43.0621, -6, -5),
    ("Hakodate", 140.7290, 41.7687, -6, -5),
    ("Kushiro", 144.3840, 42.9850, 6, -5),
    ("Aomori", 140.7474, 40.8222, 6, 5),
    ("Morioka", 141.1545, 39.7021, 6, 5),
    ("Sendai", 140.8719, 38.2682, 6, -5),
    ("Niigata", 139.0232, 37.9162, -6, 5),
    ("Kanazawa", 136.6562, 36.5613, -6, 5),
    ("Tokyo", 139.6917, 35.6895, 6, -5),
    ("Shizuoka", 138.3828, 34.9756, 6, -5),
    ("Nagoya", 136.9066, 35.1815, 6, 6),
    ("Osaka", 135.5023, 34.6937, 6, -5),
    ("Hiroshima", 132.4553, 34.3853, -6, 8),
    ("Takamatsu", 134.0433, 34.3428, 6, -10),
    ("Kochi", 133.5311, 33.5597, 6, -10),
    ("Fukuoka", 130.4017, 33.5902, -6, 10),
    ("Nagasaki", 129.8777, 32.7503, -6, -5),
    ("Kumamoto", 130.7079, 32.8031, 6, -8),
    ("Kagoshima", 130.5571, 31.5966, 6, -5),
    ("Naha", 127.6809, 26.2124, 6, -5),
)


MAP_CRS = "+proj=merc +lon_0=138 +datum=WGS84 +units=m +no_defs"
MAIN_BOUNDS = (128.0, 30.9, 146.5, 46.2)
OKINAWA_BOUNDS = (122.5, 23.5, 132.0, 28.5)


def display_geometry(frame: gpd.GeoDataFrame, *, inset: bool) -> gpd.GeoDataFrame:
    """Prepare display polygons without changing the source boundary data.

    Args:
        frame: Prefecture boundaries with Japanese names and a defined CRS.
        inset: Select Okinawa for the inset instead of the main islands.

    Returns:
        Clipped, projected polygons; remote southern/eastern islands are omitted.
    """
    geographic = frame.to_crs(4326)
    okinawa = geographic.name_ja == "沖縄県"
    visible = geographic.loc[okinawa if inset else ~okinawa].copy()
    if not inset:
        tokyo = visible.name_ja == "東京都"
        visible.loc[tokyo, "geometry"] = visible.loc[tokyo].geometry.intersection(
            box(138, 35, 142, 37)
        )
    bounds = OKINAWA_BOUNDS if inset else MAIN_BOUNDS
    visible.geometry = visible.geometry.intersection(box(*bounds))
    visible = visible.loc[~visible.geometry.is_empty].copy()
    visible = visible.to_crs(MAP_CRS)
    visible.geometry = visible.geometry.simplify(200, preserve_topology=True)
    return visible


def _draw_panel(ax, context, selected, *, inset: bool) -> None:
    """Draw prefectures, relevant cities and a fixed geographic panel extent."""
    ax.set_facecolor("#eaf4f7")
    if not context.empty:
        context.plot(ax=ax, color="#e6e8e6", edgecolor="#747d82", linewidth=0.55)
    if not selected.empty:
        selected.plot(ax=ax, color="#f18d32", edgecolor="#b65a1b", linewidth=1.0)
    cities = [city for city in REFERENCE_CITIES if (city[0] == "Naha") == inset]
    points = gpd.GeoSeries(
        gpd.points_from_xy([c[1] for c in cities], [c[2] for c in cities]), crs=4326
    ).to_crs(MAP_CRS)
    for (name, _, _, dx, dy), point in zip(cities, points, strict=True):
        ax.scatter(point.x, point.y, s=22, c="#262626", edgecolors="white", zorder=5)
        ax.annotate(
            name,
            (point.x, point.y),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=8,
            ha="right" if dx < 0 else "left",
            va="center",
            zorder=6,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1},
        )
    bounds = OKINAWA_BOUNDS if inset else MAIN_BOUNDS
    xmin, ymin, xmax, ymax = (
        gpd.GeoSeries([box(*bounds)], crs=4326).to_crs(MAP_CRS).total_bounds
    )
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_yticks([])


def render_map(
    prefectures: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    output: Path,
    *,
    context: tuple[gpd.GeoDataFrame, gpd.GeoDataFrame] | None = None,
) -> None:
    """Save a bilingual main-island map with a separately boxed Okinawa inset.

    Args:
        prefectures: Prefecture polygons with a defined CRS.
        target: Single prefecture row with name_ja and name_en fields.
        output: Destination PNG path; parent directories are created as needed.
        context: Optional prepared main/inset polygons shared across deck cards.

    Returns:
        None. Writes the map to output.
    """
    if context is None:
        context = (
            display_geometry(prefectures, inset=False),
            display_geometry(prefectures, inset=True),
        )
    figure = Figure(figsize=(10, 9), facecolor="#eaf4f7")
    FigureCanvasAgg(figure)
    ax = figure.add_axes((0.07, 0.12, 0.86, 0.72))
    _draw_panel(
        ax,
        context[0],
        display_geometry(target, inset=False),
        inset=False,
    )
    ax.set_axis_off()
    inset_ax = ax.inset_axes((0.76, -0.045, 0.29, 0.20))
    _draw_panel(
        inset_ax,
        context[1],
        display_geometry(target, inset=True),
        inset=True,
    )
    for spine in inset_ax.spines.values():
        spine.set_color("#747d82")
        spine.set_linewidth(0.8)
    inset_ax.set_title("Okinawa · location inset", fontsize=8, pad=7)
    ax.set_title(
        str(target.iloc[0].name_ja),
        fontproperties=FontProperties(fname=JAPANESE_FONT),
        fontsize=18,
        language="ja",
        pad=28,
    )
    ax.text(
        0.5,
        1.015,
        str(target.iloc[0].name_en),
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=12,
    )
    figure.legend(
        handles=[Patch(facecolor="#f18d32", label="Selected prefecture")],
        loc="lower left",
        bbox_to_anchor=(0.08, 0.065),
        fontsize=8,
    )
    figure.text(0.5, 0.04, DATA_ATTRIBUTION, ha="center", fontsize=6, color="#59646a")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    figure.clear()
