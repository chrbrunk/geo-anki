import hashlib
import json
from pathlib import Path

from geo_anki.countries.germany.data import (
    DATA_ATTRIBUTION,
    DATA_REVISION,
    DATA_URL,
    DATA_VINTAGE,
    load_data,
    select_targets,
)
from geo_anki.countries.germany.maps import render_map
from geo_anki.utils.anki import write_deck


def build_germany(
    targets: Path, output: Path, data: Path, deck_name: str
) -> list[Path]:
    """Generate German district maps, an Anki deck, and a dataset manifest.

    Args:
        targets: UTF-8 text file containing one district label per line.
        output: Destination .apkg path, also used to name maps and the manifest.
        data: Local ZIP containing German boundary layers.
        deck_name: Display name of the Anki deck.

    Returns:
        Generated PNG paths in target-file order.

    Raises:
        ValueError: Boundary data or requested district names are invalid.
    """
    states, boundaries = load_data(data)
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
        name = str(target.iloc[0].target_name)
        code = str(target.iloc[0].AGS)
        key = f"germany:{code}"
        image = (
            image_dir / f"germany_{hashlib.sha256(key.encode()).hexdigest()[:16]}.png"
        )
        render_map(states, boundaries, target, image)
        row = target.iloc[0]
        district_name = str(row.GEN)
        if row.BEZ in ("Kreisfreie Stadt", "Stadtkreis"):
            full_name = f"Kreisfreie Stadt {district_name}"
        elif district_name.startswith(("Region ", "Städteregion ", "Regionalverband ")):
            full_name = district_name
        else:
            full_name = f"{row.BEZ} {district_name}"
        cards.append((key, f"Germany: {name}", f"{full_name} — {row.state}", image))
        manifest.append(
            {
                "name": name,
                "ags": code,
                "state": str(target.iloc[0].state),
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
                "data_vintage": DATA_VINTAGE,
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
