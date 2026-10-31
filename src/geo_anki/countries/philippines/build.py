import hashlib
import json
from pathlib import Path

from geo_anki.countries.philippines.data import (
    DATA_ATTRIBUTION,
    DATA_REVISION,
    DATA_URL,
    load_data,
    select_targets,
)
from geo_anki.countries.philippines.maps import render_map
from geo_anki.utils.anki import write_deck


def build_philippines(
    targets: Path, output: Path, data: Path, deck_name: str
) -> list[Path]:
    """Generate Philippine province maps, an Anki deck, and a dataset manifest.

    Args:
        targets: UTF-8 text file containing one province name per line.
        output: Destination .apkg path, also used to name maps and the manifest.
        data: Local ZIP containing Philippine boundary layers.
        deck_name: Display name of the Anki deck.

    Returns:
        Generated PNG paths in target-file order.

    Raises:
        ValueError: Boundary data or requested province names are invalid.
    """
    boundaries = load_data(data)
    names = [
        line.strip()
        for line in targets.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    selected = select_targets(boundaries, names)
    image_dir = output.parent / f"{output.stem}_maps"
    cards = []
    manifest = []
    for index in selected.index:
        target = selected.loc[[index]]
        name = str(target.iloc[0].adm2_en)
        code = str(target.iloc[0].adm2_psgc)
        key = f"philippines:{code}"
        image = (
            image_dir
            / f"philippines_{hashlib.sha256(key.encode()).hexdigest()[:16]}.png"
        )
        render_map(boundaries, target, image)
        cards.append((key, f"Philippines: {name}", name, image))
        manifest.append({"name": name, "psgc": code, "image": str(image)})
    write_deck(cards, output, deck_name)
    output.with_suffix(".json").write_text(
        json.dumps(
            {
                "dataset": str(data),
                "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
                "default_source": DATA_URL,
                "default_revision": DATA_REVISION,
                "attribution": DATA_ATTRIBUTION,
                "cards": manifest,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return [card[3] for card in cards]
