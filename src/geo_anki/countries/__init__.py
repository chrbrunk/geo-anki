"""Supported countries and their deck-building entry points."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from geo_anki.countries.indonesia.build import build_indonesia
from geo_anki.countries.indonesia.data import download_data as download_indonesia
from geo_anki.countries.philippines.build import build_philippines
from geo_anki.countries.philippines.data import download_data as download_philippines


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
    "indonesia": Country("Indonesia", build_indonesia, download_indonesia),
    "philippines": Country("Philippines", build_philippines, download_philippines),
}
