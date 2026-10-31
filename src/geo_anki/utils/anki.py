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
    cards: list[tuple[str, str, str, Path]],
    output: Path,
    deck_name: str,
    *,
    font: Path | None = None,
    extra_media: tuple[Path, ...] = (),
) -> None:
    """Write map-backed notes and embedded images to an Anki package.

    Args:
        cards: Tuples of stable note key, front text, back text, and PNG path.
        output: Destination .apkg path; parent directories are created as needed.
        deck_name: Display name used to derive the stable deck ID.
        font: Optional bundled font for card text, using a separate Anki model.
        extra_media: Additional assets, such as the bundled font's license.

    Returns:
        None. Writes the package to output.
    """
    model_key = "geo-anki:map-model:v1"
    model_name = "Geo Anki Map"
    css = ".card { font-family: sans-serif; text-align: center; font-size: 22px; } "
    css += "img { max-width: 100%; height: auto; }"
    if font is not None:
        model_key = f"geo-anki:map-model:{font.name}:v1"
        model_name = f"Geo Anki Map ({font.stem})"
        css = (
            "@font-face { font-family: 'Geo Anki Custom'; "
            f"src: url('{font.name}'); }} "
            + css.replace(
                "font-family: sans-serif", "font-family: 'Geo Anki Custom', sans-serif"
            )
        )
    model = genanki.Model(
        stable_id(model_key),
        model_name,
        fields=[{"name": name} for name in ("Front", "Back", "Map")],
        templates=[
            {
                "name": "Location",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}<br>{{Map}}',
            }
        ],
        css=css,
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
    package.media_files.extend(str(path) for path in extra_media)
    if font is not None:
        package.media_files.append(str(font))
    output.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output))
