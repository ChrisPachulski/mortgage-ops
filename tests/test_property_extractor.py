"""Tests for lib/property_extractor.py — INGEST-02 (mocked Sonnet).

Wave 0 xfail scaffold; Wave 3 (Plan 13-03) flips green.
Live tests use pytest.importorskip("anthropic") + skipif on ANTHROPIC_API_KEY
(analog: tests/test_subagents.py:432-471).
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.xfail(reason="Phase 13 Wave 3: lib/property_extractor.py not yet built", strict=True)
def test_extract_listing_returns_dict_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """INGEST-02: Mocked Sonnet -> dict with price+zip+property_type fields."""
    from lib.property_extractor import extract_listing  # noqa: F401

    raise AssertionError("Wave 3 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 3: extractor not yet built", strict=True)
def test_extract_listing_returns_none_on_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """INGEST-02: AuthenticationError -> None (never raises; always-exit-0 per D-13-MODEL-01)."""
    from lib.property_extractor import extract_listing  # noqa: F401

    raise AssertionError("Wave 3 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 3: extractor not yet built", strict=True)
def test_extract_listing_strips_prose_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """INGEST-02 + Pitfall 18: 'Here is the data:\\n{...}' -> still parses (regex first-brace)."""
    from lib.property_extractor import extract_listing  # noqa: F401

    raise AssertionError("Wave 3 fills body")


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="Live Sonnet extraction test requires ANTHROPIC_API_KEY. CI must inject as secret or skip.",
)
@pytest.mark.xfail(reason="Phase 13 Wave 3: extractor not yet built", strict=True)
def test_extract_listing_live() -> None:
    """INGEST-02: Optional live smoke test. Requires ANTHROPIC_API_KEY + happy-path HTML fixture."""
    pytest.importorskip("anthropic")
    from lib.property_extractor import extract_listing  # noqa: F401

    raise AssertionError("Wave 3 fills body")
