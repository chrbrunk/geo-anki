from pathlib import Path

import geopandas as gpd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch

from geo_anki.countries.bangladesh.data import DATA_ATTRIBUTION

BENGALI_FONT = Path(__file__).parent / "fonts/NotoSansBengali-Regular.ttf"
FONT_LICENSE = Path(__file__).parent / "fonts/OFL.txt"

# City name, longitude, latitude, and label offsets in display points.
REFERENCE_CITIES = (
    ("Dhaka", 90.4125, 23.8103, 6, -5),
    ("Chattogram", 91.7832, 22.3569, 6, 5),
    ("Khulna", 89.5403, 22.8456, -6, -5),
    ("Rajshahi", 88.6042, 24.3745, -6, 5),
    ("Rangpur", 89.2752, 25.7439, 6, 5),
    ("Sylhet", 91.8687, 24.8949, 6, 5),
    ("Barishal", 90.3535, 22.7010, 6, -5),
    ("Mymensingh", 90.4203, 24.7471, -6, 5),
)


def render_map(
    districts: gpd.GeoDataFrame, target: gpd.GeoDataFrame, output: Path
) -> None:
    """Save a whole-country map with bilingual titles and reference cities.

    Args:
        districts: District polygons with a defined CRS.
        target: Single district row with name_bn and name_en fields.
        output: Destination PNG path; parent directories are created as needed.

    Returns:
        None. Writes the map to output.
    """
    crs = "+proj=merc +lon_0=90 +datum=WGS84 +units=m +no_defs"
    context = districts.to_crs(crs)
    selected = target.to_crs(crs)
    figure = Figure(figsize=(10, 9), facecolor="#eaf4f7")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.set_facecolor("#eaf4f7")
    context.plot(ax=ax, color="#e6e8e6", edgecolor="#747d82", linewidth=0.55)
    selected.plot(ax=ax, color="#f18d32", edgecolor="#b65a1b", linewidth=1.0)
    points = gpd.GeoSeries(
        gpd.points_from_xy(
            [city[1] for city in REFERENCE_CITIES],
            [city[2] for city in REFERENCE_CITIES],
        ),
        crs=4326,
    ).to_crs(crs)
    for (name, _, _, dx, dy), point in zip(REFERENCE_CITIES, points, strict=True):
        ax.scatter(point.x, point.y, s=22, c="#262626", edgecolors="white", zorder=5)
        ax.annotate(
            name,
            (point.x, point.y),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=9,
            ha="right" if dx < 0 else "left",
            va="center",
            zorder=6,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1},
        )
    xmin, ymin, xmax, ymax = context.total_bounds
    padding = max(xmax - xmin, ymax - ymin) * 0.06
    ax.set_xlim(xmin - padding, xmax + padding)
    ax.set_ylim(ymin - padding, ymax + padding)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(
        str(target.iloc[0].name_bn),
        fontproperties=FontProperties(fname=BENGALI_FONT),
        fontsize=18,
        language="bn",
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
    ax.legend(
        handles=[Patch(facecolor="#f18d32", label="Selected district")],
        loc="lower left",
        fontsize=8,
    )
    figure.text(0.5, 0.04, DATA_ATTRIBUTION, ha="center", fontsize=6, color="#59646a")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    figure.clear()
