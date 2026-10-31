import argparse
from pathlib import Path
from urllib.error import URLError
from zipfile import BadZipFile

from geo_anki.countries.indonesia.build import build_indonesia
from geo_anki.countries.indonesia.data import download_data


def main() -> None:
    """Parse command-line options and generate a geography deck.

    Returns:
        None. Writes output files and prints their locations.

    Raises:
        SystemExit: Help is requested or arguments or input data are invalid.
    """
    parser = argparse.ArgumentParser(description="Generate map-based Anki decks.")
    parser.add_argument(
        "--country", required=True, type=str.lower, choices=["indonesia"]
    )
    parser.add_argument(
        "--targets", type=Path, required=True, help="One kabupaten/kota per line"
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/indonesia.apkg"))
    parser.add_argument(
        "--data", type=Path, help="Local boundary ZIP; otherwise downloaded"
    )
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/geo-anki"))
    parser.add_argument("--deck-name", default="Geo Anki::Indonesia")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".apkg":
        parser.error("--output must end in .apkg")
    try:
        data = args.data if args.data is not None else download_data(args.cache_dir)
        images = build_indonesia(args.targets, args.output, data, args.deck_name)
    except (ValueError, OSError, URLError, BadZipFile) as error:
        parser.error(str(error))
    print(f"Created {args.output}: {len(images)} cards and {len(images)} PNG maps.")
    print(f"Manifest: {args.output.with_suffix('.json')}")


if __name__ == "__main__":
    main()
