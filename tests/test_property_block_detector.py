"""Tests for lib/property_block_detector.py — INGEST-04 + D-13-BLOCK-01.

Wave 0 xfail scaffold; Wave 2 (Plan 13-02) flips green.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(
    reason="Phase 13 Wave 2: lib/property_block_detector.py not yet built", strict=True
)
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (403, "http_403"),
        (429, "http_429"),
        (503, "http_503"),
        (500, "http_other"),
        (200, None),
    ],
)
def test_detect_block_status_codes(status: int, expected: str | None) -> None:
    """D-13-BLOCK-01 signal 1: HTTP status codes map to specific block errors."""
    from lib.property_block_detector import detect_block  # noqa: F401

    raise AssertionError("Wave 2 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 2: detect_block not yet built", strict=True)
def test_detect_block_body_too_short() -> None:
    """body < 5000 bytes -> 'body_too_short' (D-13-BLOCK-01 signal 4)."""
    from lib.property_block_detector import detect_block  # noqa: F401

    raise AssertionError("Wave 2 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 2: detect_block not yet built", strict=True)
@pytest.mark.parametrize(
    "phrase",
    [
        "press & hold",
        "human verification",
        "px-captcha",
        "are you a robot",
        "unusual traffic",
        "recaptcha",
    ],
)
def test_detect_block_captcha_phrases(phrase: str) -> None:
    """Each phrase fires 'captcha_detected' (case-insensitive). D-13-BLOCK-01 signal 3."""
    from lib.property_block_detector import detect_block  # noqa: F401

    raise AssertionError("Wave 2 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 2: detect_block not yet built", strict=True)
def test_detect_block_missing_next_data() -> None:
    """200-status, large body, no captcha, no <script id="__NEXT_DATA__"> -> 'missing_next_data'."""
    from lib.property_block_detector import detect_block  # noqa: F401

    raise AssertionError("Wave 2 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 2: extract_zpid not yet built", strict=True)
@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.zillow.com/homedetails/123-Main-SF-CA-94110/12345678_zpid/", "12345678"),
        ("https://zillow.com/b/87654321_zpid/", "87654321"),
        ("https://zillow.com/.../12345_zpid", "12345"),
        ("https://zillow.com/.../12345_zpid/?source=email", "12345"),
        ("https://zillow.com/.../12345_zpid/#photos", "12345"),
        ("http://www.zillow.com/.../12345_zpid/", "12345"),
        ("https://redfin.com/property/12345", None),
        ("https://zillow.com/homedetails/foo/", None),
        ("", None),
    ],
)
def test_extract_zpid(url: str, expected: str | None) -> None:
    """INGEST-04: ZPID extraction from both URL patterns + edge cases."""
    from lib.property_block_detector import extract_zpid  # noqa: F401

    raise AssertionError("Wave 2 fills body")
