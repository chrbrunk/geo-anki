import hashlib
from html import escape
from pathlib import Path

import genanki


def stable_id(value: str) -> int:
    """Derive a repeatable numeric identifier for an Anki model or deck.

    Args:
        value: Stable identifying string.

    Returns:
        Nonnegative 31-bit integer derived from the string's SHA-256 hash.
    """
    return (
        int.from_bytes(hashlib.sha256(value.encode()).digest()[:4], "big") & 0x7FFFFFFF
    )


def write_deck(
    cards: list[tuple[str, str, str, Path]], output: Path, deck_name: str
) -> None:
    """Write map-backed notes and embedded images to an Anki package.

    Args:
        cards: Tuples of stable note key, front text, back text, and PNG path.
        output: Destination .apkg path; parent directories are created as needed.
        deck_name: Display name used to derive the stable deck ID.

    Returns:
        None. Writes the package to output.
    """
    model = genanki.Model(
        stable_id("geo-anki:map-model:v1"),
        "Geo Anki Map",
        fields=[{"name": name} for name in ("Front", "Back", "Map")],
        templates=[
            {
                "name": "Location",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}<br>{{Map}}',
            }
        ],
        css=".card { font-family: sans-serif; text-align: center; font-size: 22px; } "
        "img { max-width: 100%; height: auto; }",
    )
    deck = genanki.Deck(stable_id(f"geo-anki:deck:{deck_name}"), deck_name)
    for key, front, back, image in cards:
        deck.add_note(
            genanki.Note(
                model=model,
                guid=genanki.guid_for(f"geo-anki:{key}"),
                fields=[
                    escape(front),
                    escape(back),
                    f'<img src="{escape(image.name)}">',
                ],
            )
        )
    package = genanki.Package(deck)
    package.media_files = [str(card[3]) for card in cards]
    output.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output))
