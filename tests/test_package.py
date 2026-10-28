"""Smoke tests for the installed package."""

import geo_anki


def test_package_imports():
    """Verify the installed package can be imported.

    Returns:
        None. Asserts the expected package name.
    """
    assert geo_anki.__name__ == "geo_anki"
