import hashlib
import json
from pathlib import Path

from geo_anki.countries.bangladesh.data import (
    DATA_ATTRIBUTION,
    DATA_REVISION,
    DATA_URL,
    load_data,
    select_targets,
)
from geo_anki.countries.bangladesh.maps import BENGALI_FONT, FONT_LICENSE, render_map
from geo_anki.utils.anki import write_deck


def build_bangladesh(
    targets: Path, output: Path, data: Path, deck_name: str
) -> list[Path]:
    """Generate Bengali-front district cards, bilingual maps, and a manifest.

    Args:
        targets: UTF-8 text file containing Bengali or English district names.
        output: Destination .apkg path, also used to name maps and the manifest.
        data: Local ZIP containing district boundaries and bilingual name tables.
        deck_name: Display name of the Anki deck.

    Returns:
        Generated PNG paths in target-file order.

    Raises:
        ValueError: Boundary data or requested district names are invalid.
    """
    districts = load_data(data)
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
        row = target.iloc[0]
        name_en, name_bn = str(row.name_en), str(row.name_bn)
        key = f"bangladesh:{row.district_id}"
        image = (
            image_dir
            / f"bangladesh_{hashlib.sha256(key.encode()).hexdigest()[:16]}.png"
        )
        render_map(districts, target, image)
        cards.append((key, f"Bangladesh: {name_bn}", name_en, image))
        manifest.append(
            {
                "name": name_en,
                "name_bn": name_bn,
                "district_id": str(row.district_id),
                "division": str(row.division),
                "image": str(image),
            }
        )
    write_deck(cards, output, deck_name, font=BENGALI_FONT, extra_media=(FONT_LICENSE,))
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
