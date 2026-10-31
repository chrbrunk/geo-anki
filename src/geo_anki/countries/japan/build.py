import hashlib
import json
from pathlib import Path

from geo_anki.countries.japan.data import (
    DATA_ATTRIBUTION,
    DATA_REVISION,
    DATA_URL,
    load_data,
    select_targets,
)
from geo_anki.countries.japan.maps import (
    FONT_LICENSE,
    JAPANESE_FONT,
    display_geometry,
    render_map,
)
from geo_anki.utils.anki import write_deck


def build_japan(targets: Path, output: Path, data: Path, deck_name: str) -> list[Path]:
    """Generate Japanese-front prefecture cards, bilingual maps, and a manifest.

    Args:
        targets: UTF-8 text file containing Japanese or English prefecture names.
        output: Destination .apkg path, also used to name maps and the manifest.
        data: Local ZIP containing Japanese prefecture boundaries.
        deck_name: Display name of the Anki deck.

    Returns:
        Generated PNG paths in target-file order.

    Raises:
        ValueError: Boundary data or requested prefecture names are invalid.
    """
    prefectures = load_data(data)
    names = [
        line.strip()
        for line in targets.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    selected = select_targets(prefectures, names)
    image_dir = output.parent / f"{output.stem}_maps"
    context = (
        display_geometry(prefectures, inset=False),
        display_geometry(prefectures, inset=True),
    )
    cards = []
    manifest = []
    for index in selected.index:
        target = selected.loc[[index]]
        row = target.iloc[0]
        name_en, name_ja = str(row.name_en), str(row.name_ja)
        key = f"japan:{row.prefecture_code}"
        image = image_dir / f"japan_{hashlib.sha256(key.encode()).hexdigest()[:16]}.png"
        render_map(prefectures, target, image, context=context)
        cards.append((key, f"Japan: {name_ja}", name_en, image))
        manifest.append(
            {
                "name": name_en,
                "name_ja": name_ja,
                "prefecture_code": str(row.prefecture_code),
                "image": str(image),
            }
        )
    write_deck(
        cards, output, deck_name, font=JAPANESE_FONT, extra_media=(FONT_LICENSE,)
    )
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
