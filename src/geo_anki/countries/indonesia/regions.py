from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    name: str
    provinces: tuple[str, ...]
    # City name, longitude, latitude, label offset in points.
    cities: tuple[tuple[str, float, float, int, int], ...] = ()


REGIONS = (
    Region(
        "Kalimantan",
        (
            "Kalimantan Barat",
            "Kalimantan Tengah",
            "Kalimantan Selatan",
            "Kalimantan Timur",
            "Kalimantan Utara",
        ),
        (
            ("Pontianak", 109.3425, -0.0263, 5, 5),
            ("Palangka Raya", 113.9213, -2.2096, 5, 5),
            ("Banjarmasin", 114.5910, -3.3194, 5, -12),
            ("Samarinda", 117.1537, -0.5022, 6, 0),
            ("Balikpapan", 116.8529, -1.2379, 6, -10),
            ("Bontang", 117.5000, 0.1333, 6, 8),
        ),
    ),
    Region(
        "Sumatra",
        (
            "Aceh",
            "Sumatera Utara",
            "Sumatera Barat",
            "Riau",
            "Jambi",
            "Sumatera Selatan",
            "Bengkulu",
            "Lampung",
            "Kepulauan Bangka Belitung",
        ),
        (
            ("Banda Aceh", 95.3238, 5.5483, 5, 5),
            ("Medan", 98.6722, 3.5952, 5, 5),
            ("Padang", 100.3543, -0.9471, -42, -10),
            ("Pekanbaru", 101.4478, 0.5071, 5, 5),
            ("Jambi", 103.6131, -1.6101, 5, 5),
            ("Palembang", 104.7754, -2.9761, 5, 5),
            ("Bandar Lampung", 105.2668, -5.3971, 5, -12),
        ),
    ),
)


def region_for(province: str) -> Region:
    return next(
        (region for region in REGIONS if province in region.provinces),
        Region(province, (province,)),
    )
