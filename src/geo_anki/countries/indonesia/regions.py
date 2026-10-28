from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    """Geographic context and reference cities for a map.

    Attributes:
        name: Display name of the island or province.
        provinces: Dataset province names included in the map extent.
        cities: Tuples of name, longitude, latitude, and x/y label offsets in points.
    """

    name: str
    provinces: tuple[str, ...]
    # City name, longitude, latitude, label offset in points.
    cities: tuple[tuple[str, float, float, int, int], ...] = ()


REGIONS = (
    Region(
        "Java",
        (
            "Banten",
            "DKI Jakarta",
            "Jawa Barat",
            "Jawa Tengah",
            "Daerah Istimewa Yogyakarta",
            "Jawa Timur",
        ),
        (
            ("Jakarta", 106.8456, -6.2088, 5, 8),
            ("Bandung", 107.6191, -6.9175, 5, -12),
            ("Semarang", 110.4203, -6.9667, 5, 8),
            ("Yogyakarta", 110.3695, -7.7956, -65, -12),
            ("Surakarta", 110.8167, -7.5667, 5, -12),
            ("Surabaya", 112.7508, -7.2575, 5, 8),
            ("Malang", 112.6304, -7.9666, 5, -12),
        ),
    ),
    Region(
        "Sulawesi",
        (
            "Sulawesi Utara",
            "Gorontalo",
            "Sulawesi Tengah",
            "Sulawesi Barat",
            "Sulawesi Selatan",
            "Sulawesi Tenggara",
        ),
        (
            ("Manado", 124.8455, 1.4748, 5, 8),
            ("Gorontalo", 123.0595, 0.5435, 5, -12),
            ("Palu", 119.8707, -0.8917, -25, 8),
            ("Mamuju", 118.9009, -2.6797, -48, 5),
            ("Makassar", 119.4327, -5.1477, -55, -12),
            ("Kendari", 122.5120, -3.9985, 5, 5),
        ),
    ),
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
    """Choose island-wide context, falling back to the province itself.

    Args:
        province: Exact province name from the boundary dataset.

    Returns:
        Configured island region or a province-only region without cities.
    """
    return next(
        (region for region in REGIONS if province in region.provinces),
        Region(province, (province,)),
    )
