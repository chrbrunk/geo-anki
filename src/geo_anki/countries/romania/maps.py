"""Consistent whole-country county maps with Romanian reference-city labels."""

from pathlib import Path

import geopandas as gpd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from geo_anki.countries.romania.data import DATA_ATTRIBUTION

MAP_CRS = "+proj=lcc +lat_1=43 +lat_2=48 +lat_0=46 +lon_0=25 +datum=WGS84 +units=m"
REFERENCE_CITIES = (
    ("București", 26.1025, 44.4268, 7, -10),
    ("Cluj-Napoca", 23.6236, 46.7712, 6, 7),
    ("Iași", 27.6014, 47.1585, 6, 7),
    ("Timișoara", 21.2257, 45.7489, -6, -8),
    ("Constanța", 28.6348, 44.1598, 6, -7),
    ("Craiova", 23.7949, 44.3302, -6, -8),
    ("Brașov", 25.6012, 45.6579, 6, 7),
    ("Oradea", 21.9189, 47.0465, -6, 6),
    ("Suceava", 26.2556, 47.6635, 6, 7),
    ("Galați", 28.0425, 45.4353, 6, 7),
    ("Sibiu", 24.1256, 45.7983, -6, -8),
    ("Baia Mare", 23.5681, 47.6567, -6, 7),
    ("Bacău", 26.9146, 46.5670, 6, 7),
    ("Pitești", 24.8692, 44.8565, -6, -8),
    ("Tulcea", 28.7928, 45.1716, 6, -8),
)


def render_map(
    context: gpd.GeoDataFrame, target: gpd.GeoDataFrame, output: Path
) -> None:
    """Show the entire country with the selected county or municipality filled."""
    selected = target.to_crs(context.crs)
    row = selected.iloc[0]
    figure = Figure(figsize=(10, 9), facecolor="#eaf4f7")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.set_facecolor("#eaf4f7")
    context.plot(ax=ax, color="#e6e8e6", edgecolor="#747d82", linewidth=0.65)
    selected.plot(ax=ax, color="#f18d32", edgecolor="#b65a1b", linewidth=1.0)
    points = gpd.GeoSeries(
        gpd.points_from_xy(
            [c[1] for c in REFERENCE_CITIES], [c[2] for c in REFERENCE_CITIES]
        ),
        crs=4326,
    ).to_crs(context.crs)
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
    padding = max(xmax - xmin, ymax - ymin) * 0.08
    ax.set_xlim(xmin - padding, xmax + padding)
    ax.set_ylim(ymin - padding, ymax + padding)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(str(row.county_name), fontsize=18, pad=16)
    ax.legend(
        handles=[Patch(facecolor="#f18d32", label="Selected county / municipality")],
        loc="lower left",
        fontsize=8,
    )
    figure.text(0.5, 0.04, DATA_ATTRIBUTION, ha="center", fontsize=7, color="#59646a")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    figure.clear()
