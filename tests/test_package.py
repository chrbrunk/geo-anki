"""Smoke tests for the installed package."""

import geo_anki


def test_package_imports():
    assert geo_anki.__name__ == "geo_anki"
