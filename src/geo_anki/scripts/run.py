import argparse
import hashlib
import json
from pathlib import Path
from urllib.error import URLError
from zipfile import BadZipFile

from geo_anki.countries.indonesia.data import (
    DATA_REVISION,
    DATA_URL,
    download_data,
    load_data,
    normalize,
    select_targets,
)
from geo_anki.countries.indonesia.maps import render_map
from geo_anki.countries.indonesia.regions import region_for
from geo_anki.utils.anki import write_deck


def build_indonesia(
    targets: Path, output: Path, data: Path, deck_name: str
) -> list[Path]:
    """Generate Indonesian maps, an Anki deck, and a dataset manifest.

    Args:
        targets: UTF-8 text file containing one subdivision name per line.
        output: Destination .apkg path, also used to name maps and the manifest.
        data: Local ZIP containing Indonesian boundary layers.
        deck_name: Display name of the Anki deck.

    Returns:
        Generated PNG paths in target-file order.

    Raises:
        ValueError: Boundary data or requested subdivision names are invalid.
    """
    provinces, districts = load_data(data)
    names = [
        line.strip()
        for line in targets.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    selected = select_targets(districts, names)
    image_dir = output.parent / f"{output.stem}_maps"
    cards = []
    manifest = []
    for index in selected.index:
        target = selected.loc[[index]]
        name, province = str(target.iloc[0].WADMKK), str(target.iloc[0].WADMPR)
        key = f"indonesia:{normalize(province)}:{normalize(name)}"
        image = (
            image_dir / f"indonesia_{hashlib.sha256(key.encode()).hexdigest()[:16]}.png"
        )
        region = region_for(province)
        render_map(provinces, districts, target, region, image)
        full_name = (
            name
            if normalize(name).startswith(("kota ", "kabupaten "))
            else f"Kabupaten {name}"
        )
        cards.append(
            (key, f"Indonesia: {name}", f"{full_name} — {province}, Indonesia", image)
        )
        manifest.append(
            {
                "name": name,
                "province": province,
                "region": region.name,
                "image": str(image),
            }
        )
    write_deck(cards, output, deck_name)
    output.with_suffix(".json").write_text(
        json.dumps(
            {
                "dataset": str(data),
                "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
                "default_source": DATA_URL,
                "default_revision": DATA_REVISION,
                "cards": manifest,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return [card[3] for card in cards]


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
