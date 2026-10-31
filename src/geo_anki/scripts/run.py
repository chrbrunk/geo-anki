import argparse
from pathlib import Path
from urllib.error import URLError
from zipfile import BadZipFile

from geo_anki.countries import COUNTRIES


def main() -> None:
    """Parse command-line options and generate a geography deck.

    Returns:
        None. Writes output files and prints their locations.

    Raises:
        SystemExit: Help is requested or arguments or input data are invalid.
    """
    parser = argparse.ArgumentParser(description="Generate map-based Anki decks.")
    parser.add_argument(
        "--country", required=True, type=str.lower, choices=sorted(COUNTRIES)
    )
    parser.add_argument(
        "--targets", type=Path, required=True, help="One subdivision name per line"
    )
    parser.add_argument("--output", type=Path, help="Destination .apkg path")
    parser.add_argument(
        "--data", type=Path, help="Local boundary ZIP; otherwise downloaded"
    )
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/geo-anki"))
    parser.add_argument("--deck-name", help="Anki deck name")
    args = parser.parse_args()
    country = COUNTRIES[args.country]
    output = (
        args.output if args.output is not None else Path(f"outputs/{args.country}.apkg")
    )
    deck_name = (
        args.deck_name if args.deck_name is not None else f"Geo Anki::{country.name}"
    )
    if output.suffix.lower() != ".apkg":
        parser.error("--output must end in .apkg")
    try:
        data = (
            args.data
            if args.data is not None
            else country.download_data(args.cache_dir)
        )
        images = country.build(args.targets, output, data, deck_name)
    except (ValueError, OSError, URLError, BadZipFile) as error:
        parser.error(str(error))
    print(f"Created {output}: {len(images)} cards and {len(images)} PNG maps.")
    print(f"Manifest: {output.with_suffix('.json')}")


if __name__ == "__main__":
    main()
