from pathlib import Path

import geopandas as gpd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from geo_anki.countries.indonesia.regions import Region


def render_map(
    provinces: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    region: Region,
    output: Path,
) -> None:
    province = target.iloc[0].WADMPR
    context = provinces[provinces.PROVINSI.isin(region.provinces)]
    if set(context.PROVINSI) != set(region.provinces):
        raise ValueError(f"Dataset lacks provinces required for {region.name}.")
    # A local Mercator projection keeps shapes and city coordinates aligned.
    longitude = context.geometry.union_all().centroid.x
    crs = f"+proj=merc +lon_0={longitude} +datum=WGS84 +units=m +no_defs"
    context = context.to_crs(crs)
    subdivisions = districts[districts.WADMPR.isin(region.provinces)].to_crs(crs)
    selected = context[context.PROVINSI == province]
    figure = Figure(figsize=(10, 9), facecolor="#eaf4f7")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.set_facecolor("#eaf4f7")
    context.plot(ax=ax, color="#e6e8e6", edgecolor="none")
    selected.plot(ax=ax, color="#f7e9ce", edgecolor="none")
    subdivisions.boundary.plot(ax=ax, color="#a9b1b5", linewidth=0.38)
    context.boundary.plot(ax=ax, color="#747d82", linewidth=1.05)
    target.to_crs(crs).plot(ax=ax, color="#f18d32", edgecolor="#b65a1b", linewidth=1.0)
    selected.boundary.plot(ax=ax, color="#262626", linewidth=2.65)
    if region.cities:
        points = gpd.GeoSeries(
            gpd.points_from_xy(
                [city[1] for city in region.cities],
                [city[2] for city in region.cities],
            ),
            crs=4326,
        ).to_crs(crs)
        for (name, _, _, dx, dy), point in zip(region.cities, points, strict=True):
            ax.scatter(
                point.x, point.y, s=22, c="#262626", edgecolors="white", zorder=5
            )
            ax.annotate(
                name,
                (point.x, point.y),
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=9,
                zorder=6,
                bbox={
                    "facecolor": "white",
                    "alpha": 0.75,
                    "edgecolor": "none",
                    "pad": 1,
                },
            )
    xmin, ymin, xmax, ymax = context.total_bounds
    padding = max(xmax - xmin, ymax - ymin) * 0.06
    ax.set_xlim(xmin - padding, xmax + padding)
    ax.set_ylim(ymin - padding, ymax + padding)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(
        f"{target.iloc[0].WADMKK}\n{province} · {region.name}, Indonesia", fontsize=14
    )
    ax.legend(
        handles=[
            Patch(facecolor="#f18d32", label="Target kabupaten/kota"),
            Patch(facecolor="#f7e9ce", edgecolor="#262626", label="Selected province"),
        ],
        loc="lower left",
        fontsize=8,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    figure.clear()
