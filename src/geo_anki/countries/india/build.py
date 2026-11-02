"""Generate India decks, embedded fonts, maps and source manifests."""

import hashlib
import json
from pathlib import Path

from geo_anki.countries.bangladesh.maps import BENGALI_FONT
from geo_anki.countries.bangladesh.maps import FONT_LICENSE as BENGALI_LICENSE
from geo_anki.countries.india.data import (
    DATA_ATTRIBUTION,
    DATA_REVISION,
    DATA_URL,
    DATA_VINTAGE,
    load_data,
    select_targets,
)
from geo_anki.countries.india.maps import (
    DEVANAGARI_FONT,
    FONT_LICENSE,
    prepare_context,
    render_map,
)
from geo_anki.utils.anki import write_deck


def build_india(targets: Path, output: Path, data: Path, deck_name: str) -> list[Path]:
    """Build selected districts in input order, validating before writing outputs."""
    boundaries, districts = load_data(data)
    names = [
        line.strip()
        for line in targets.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    selected = select_targets(districts, names)
    context = prepare_context(boundaries)
    image_dir = output.parent / f"{output.stem}_maps"
    cards = []
    manifest = []
    for _, row in selected.iterrows():
        key = f"india:lgd:{row.district_id}"
        image = image_dir / f"india_{hashlib.sha256(key.encode()).hexdigest()[:16]}.png"
        render_map(context, selected.loc[[row.name]], image)
        cards.append((key, f"India: {row.name_native}", str(row.target_name), image))
        manifest.append(
            {
                "name": str(row.name_en),
                "front_name": str(row.name_native),
                "language": str(row.language),
                "district_id": str(row.district_id),
                "state_code": str(row.state_code),
                "state": str(row.state),
                "image": str(image),
            }
        )
    write_deck(
        cards,
        output,
        deck_name,
        font=DEVANAGARI_FONT,
        fallback_fonts=(BENGALI_FONT,),
        extra_media=(FONT_LICENSE, BENGALI_LICENSE),
    )
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
