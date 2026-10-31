from pathlib import Path

import geopandas as gpd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from geo_anki.countries.germany.data import DATA_ATTRIBUTION
from geo_anki.countries.germany.regions import REFERENCE_CITIES


def render_map(
    states: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    output: Path,
) -> None:
    """Render a district within its entire Bundesland, with reference cities.

    Args:
        states: Validated state boundaries.
        districts: Validated district boundaries.
        target: Single target district row.
        output: Destination PNG path; parent directories are created as needed.

    Returns:
        None. Writes a state-wide map highlighting the selected district.
    """
    row = target.iloc[0]
    state = states[states.AGS == row.state_code].to_crs(3035)
    context = districts[districts.state_code == row.state_code].to_crs(3035)
    selected = target.to_crs(3035)
    figure = Figure(figsize=(10, 9), facecolor="#eaf4f7")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.set_facecolor("#eaf4f7")
    state.plot(ax=ax, color="#e6e8e6", edgecolor="#747d82", linewidth=1.05)
    context.boundary.plot(ax=ax, color="#a9b1b5", linewidth=0.55)
    selected.plot(ax=ax, color="#f18d32", edgecolor="#b65a1b", linewidth=1.0)
    cities = REFERENCE_CITIES[str(row.state_code)]
    points = gpd.GeoSeries(
        gpd.points_from_xy([city[1] for city in cities], [city[2] for city in cities]),
        crs=4326,
    ).to_crs(3035)
    for (name, _, _, dx, dy), point in zip(cities, points, strict=True):
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
    xmin, ymin, xmax, ymax = state.total_bounds
    padding = max(xmax - xmin, ymax - ymin) * 0.06
    ax.set_xlim(xmin - padding, xmax + padding)
    ax.set_ylim(ymin - padding, ymax + padding)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(str(row.target_name), fontsize=14, pad=28)
    ax.text(
        0.5,
        1.015,
        str(row.state),
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
    figure.text(0.5, 0.04, DATA_ATTRIBUTION, ha="center", fontsize=6, color="#59646a")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    figure.clear()
