"""Supported countries and their deck-building entry points."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from geo_anki.countries.bangladesh.build import build_bangladesh
from geo_anki.countries.bangladesh.data import download_data as download_bangladesh
from geo_anki.countries.germany.build import build_germany
from geo_anki.countries.germany.data import download_data as download_germany
from geo_anki.countries.india.build import build_india
from geo_anki.countries.india.data import download_data as download_india
from geo_anki.countries.indonesia.build import build_indonesia
from geo_anki.countries.indonesia.data import download_data as download_indonesia
from geo_anki.countries.japan.build import build_japan
from geo_anki.countries.japan.data import download_data as download_japan
from geo_anki.countries.philippines.build import build_philippines
from geo_anki.countries.philippines.data import download_data as download_philippines
from geo_anki.countries.romania.build import build_romania
from geo_anki.countries.romania.data import download_data as download_romania


@dataclass(frozen=True)
class Country:
    """Country-specific operations used by the shared CLI.

    Attributes:
        name: Display name used for the default Anki deck.
        build: Generate maps and a deck from targets and local boundary data.
        download_data: Download or verify cached boundary data.
    """

    name: str
    build: Callable[[Path, Path, Path, str], list[Path]]
    download_data: Callable[[Path], Path]


COUNTRIES = {
    "bangladesh": Country("Bangladesh", build_bangladesh, download_bangladesh),
    "germany": Country("Germany", build_germany, download_germany),
    "india": Country("India", build_india, download_india),
    "indonesia": Country("Indonesia", build_indonesia, download_indonesia),
    "japan": Country("Japan", build_japan, download_japan),
    "philippines": Country("Philippines", build_philippines, download_philippines),
    "romania": Country("Romania", build_romania, download_romania),
}
