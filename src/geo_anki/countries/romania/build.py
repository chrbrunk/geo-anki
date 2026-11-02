"""Build county cards with stable ISO-based note IDs and embedded maps."""

import hashlib
import json
from pathlib import Path

from geo_anki.countries.romania.data import (
    DATA_ATTRIBUTION,
    DATA_REVISION,
    DATA_URL,
    load_data,
    select_targets,
)
from geo_anki.countries.romania.maps import MAP_CRS, render_map
from geo_anki.utils.anki import write_deck


def build_romania(
    targets: Path, output: Path, data: Path, deck_name: str
) -> list[Path]:
    """Validate every target before rendering whole-country maps and an Anki deck."""
    counties = load_data(data)
    names = [
        line.strip()
        for line in targets.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    selected = select_targets(counties, names)
    context = counties.to_crs(MAP_CRS)
    image_dir = output.parent / f"{output.stem}_maps"
    cards = []
    manifest = []
    for index, row in selected.iterrows():
        key = f"romania:{row.county_code}"
        image = (
            image_dir / f"romania_{hashlib.sha256(key.encode()).hexdigest()[:16]}.png"
        )
        render_map(context, selected.loc[[index]], image)
        name = str(row.county_name)
        cards.append((key, f"Romania: {name}", name, image))
        manifest.append(
            {"name": name, "county_code": str(row.county_code), "image": str(image)}
        )
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
