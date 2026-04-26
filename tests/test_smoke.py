"""Smoke test: Phase 1 Wave 1 must leave the repo in a green-CI state.

This file is allowed to be deleted once Plan 03 / 04 / 05 land their real tests.
For now it ensures `uv run pytest` exits 0 with at least one collected test.
"""

from __future__ import annotations


def test_python_version_is_modern() -> None:
    import sys

    assert sys.version_info >= (3, 12), "mortgage-ops requires Python >= 3.12"
