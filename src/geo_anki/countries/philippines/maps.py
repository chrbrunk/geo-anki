from pathlib import Path

import geopandas as gpd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from geo_anki.countries.philippines.data import DATA_ATTRIBUTION
from geo_anki.countries.philippines.references import REFERENCE_PLACES

HIGHLIGHT_COLOR = "#f18d32"

# Small provinces need a pointer at the fixed whole-country scale.
# Arrow-tail offsets from the province, in display points.
SMALL_PROVINCE_ARROWS = {
    "Batanes": (85, 15),
    "Camiguin": (85, 25),
    "Siquijor": (85, -25),
    "Biliran": (85, 25),
    "Guimaras": (85, -30),
    "Marinduque": (85, 15),
    "Dinagat Islands": (85, 25),
    "Basilan": (85, -25),
    "Tawi-Tawi": (85, -25),
    "Rizal": (85, 15),
}


def render_map(
    boundaries: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    output: Path,
) -> None:
    """Save a whole-country map highlighting one Philippine province.

    Args:
        boundaries: Province and non-province context polygons in a defined CRS.
        target: Single province row with an adm2_en name.
        output: Destination PNG path; parent directories are created as needed.

    Returns:
        None. Writes the map to output.
    """
    crs = "+proj=merc +lon_0=122 +datum=WGS84 +units=m +no_defs"
    context = boundaries.to_crs(crs)
    selected = target.to_crs(crs)
    figure = Figure(figsize=(10, 9), facecolor="#eaf4f7")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.set_facecolor("#eaf4f7")
    context.plot(ax=ax, color="#e6e8e6", edgecolor="#747d82", linewidth=0.55)
    selected.plot(ax=ax, color=HIGHLIGHT_COLOR, edgecolor="#b65a1b", linewidth=1.0)
    name = str(target.iloc[0].adm2_en)
    if name in SMALL_PROVINCE_ARROWS:
        # Aim inside the largest island, rather than an offshore centroid.
        polygon = max(
            selected.geometry.explode(index_parts=False), key=lambda g: g.area
        )
        point = polygon.representative_point()
        ax.annotate(
            "",
            xy=(point.x, point.y),
            xytext=SMALL_PROVINCE_ARROWS[name],
            textcoords="offset points",
            arrowprops={
                "arrowstyle": "->",
                "color": HIGHLIGHT_COLOR,
                "linewidth": 2.6,
                "mutation_scale": 28,
                "shrinkA": 0,
                "shrinkB": 10,
            },
            zorder=7,
        )
    xmin, ymin, xmax, ymax = context.total_bounds
    padding = max(xmax - xmin, ymax - ymin) * 0.06
    ax.set_xlim(xmin - padding, xmax + padding)
    ax.set_ylim(ymin - padding, ymax + padding)
    ax.set_aspect("equal")
    ax.set_axis_off()
    reference = REFERENCE_PLACES[name]
    ax.set_title(name, fontsize=14, pad=28)
    ax.text(
        0.5,
        1.015,
        f"Reference {reference.kind}: {reference.name}",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=10,
    )
    ax.legend(
        handles=[Patch(facecolor=HIGHLIGHT_COLOR, label="Selected province")],
        loc="lower left",
        fontsize=8,
    )
    figure.text(0.5, 0.04, DATA_ATTRIBUTION, ha="center", fontsize=6, color="#59646a")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    figure.clear()
