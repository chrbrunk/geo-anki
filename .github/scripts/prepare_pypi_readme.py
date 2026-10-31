"""Convert relative README links to absolute URLs for the package's release tag."""

import re
import tomllib
from pathlib import Path


def with_release_links(text: str, version: str) -> str:
    """Resolve relative repository links for the PyPI package description.

    Args:
        text: README Markdown containing branch-relative repository links.
        version: Package version from pyproject.toml.

    Returns:
        Markdown whose repository links point to the matching release tag.
    """
    repo = "https://github.com/chrbrunk/geo-anki"
    raw = "https://raw.githubusercontent.com/chrbrunk/geo-anki"
    tag = f"v{version}"

    def absolute(target: str) -> str:
        if target.startswith(("https://", "http://", "mailto:", "#")):
            return target
        if target.endswith("/"):
            return f"{repo}/tree/{tag}/{target}"
        if target.endswith((".png", ".apkg")):
            return f"{raw}/{tag}/{target}"
        return f"{repo}/blob/{tag}/{target}"

    text = re.sub(
        r"(\[[^\]]*\])\(([^)]+)\)",
        lambda match: f"{match[1]}({absolute(match[2])})",
        text,
    )
    return re.sub(
        r'src="([^"]+)"',
        lambda match: f'src="{absolute(match[1])}"',
        text,
    )


if __name__ == "__main__":
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    readme = Path("README.md")
    readme.write_text(
        with_release_links(
            readme.read_text(encoding="utf-8"), project["project"]["version"]
        ),
        encoding="utf-8",
    )
