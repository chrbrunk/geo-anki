"""State-wide Indian district maps, with bilingual titles where applicable."""

from pathlib import Path

import geopandas as gpd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch

from geo_anki.countries.bangladesh.maps import BENGALI_FONT
from geo_anki.countries.india.data import DATA_ATTRIBUTION
from geo_anki.countries.india.regions import REFERENCE_CITIES

DEVANAGARI_FONT = Path(__file__).parent / "fonts/NotoSansDevanagari-Regular.ttf"
FONT_LICENSE = Path(__file__).parent / "fonts/OFL-Devanagari.txt"
MAP_CRS = "+proj=lcc +lat_1=12 +lat_2=35 +lat_0=24 +lon_0=80 +datum=WGS84 +units=m"


def prepare_context(boundaries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Project the complete source once per deck, keeping all source geometry."""
    return boundaries.to_crs(MAP_CRS)


def render_map(
    context: gpd.GeoDataFrame, target: gpd.GeoDataFrame, output: Path
) -> None:
    """Frame the complete state/territory and highlight one district.

    Detached territories and islands retain their geographic positions. Extents
    depend only on the state, keeping framing consistent across its cards.
    """
    row = target.iloc[0]
    state = context[context.state_code == row.state_code]
    selected = target.to_crs(context.crs)
    figure = Figure(figsize=(10, 9), facecolor="#eaf4f7")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.set_facecolor("#eaf4f7")
    state.plot(ax=ax, color="#e6e8e6", edgecolor="#a9b1b5", linewidth=0.55)
    selected.plot(ax=ax, color="#f18d32", edgecolor="#b65a1b", linewidth=1.0)
    cities = REFERENCE_CITIES[str(row.state_code)]
    points = gpd.GeoSeries(
        gpd.points_from_xy([c[1] for c in cities], [c[2] for c in cities]), crs=4326
    ).to_crs(context.crs)
    for index, ((name, _, _), point) in enumerate(zip(cities, points, strict=True)):
        ax.scatter(point.x, point.y, s=22, c="#262626", edgecolors="white", zorder=5)
        dx, dy = (6, 6) if index % 2 == 0 else (-6, -7)
        ax.annotate(
            name,
            (point.x, point.y),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=9,
            ha="left" if dx > 0 else "right",
            va="center",
            zorder=6,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1},
        )
    xmin, ymin, xmax, ymax = state.total_bounds
    padding = max(xmax - xmin, ymax - ymin) * 0.07
    ax.set_xlim(xmin - padding, xmax + padding)
    ax.set_ylim(ymin - padding, ymax + padding)
    ax.set_aspect("equal")
    ax.set_axis_off()
    if row.language != "en":
        ax.set_title(
            str(row.name_native),
            fontproperties=FontProperties(
                fname=BENGALI_FONT if row.language == "bn" else DEVANAGARI_FONT
            ),
            language=str(row.language),
            fontsize=18,
            pad=30,
        )
    else:
        ax.set_title(str(row.name_en), fontsize=18, pad=30)
    ax.text(
        0.5,
        1.015,
        str(row.target_name),
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=11,
    )
    ax.legend(
        handles=[Patch(facecolor="#f18d32", label="Selected district")],
        loc="lower left",
        fontsize=8,
    )
    figure.text(0.5, 0.035, DATA_ATTRIBUTION, ha="center", fontsize=6, color="#59646a")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    figure.clear()
