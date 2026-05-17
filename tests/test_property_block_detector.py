"""Tests for lib/property_block_detector.py — INGEST-04 + D-13-BLOCK-01."""

from __future__ import annotations

import pytest
from lib.property_block_detector import (
    CAPTCHA_PHRASES,
    MIN_BODY_BYTES,
    detect_block,
    extract_zpid,
)

# A canned happy-path body: above MIN_BODY_BYTES, no captcha, has NEXT_DATA tag.
_HAPPY_BODY = (
    "<html>"
    + "x" * (MIN_BODY_BYTES + 200)
    + '<script id="__NEXT_DATA__">{"props":{}}</script>'
    + "</html>"
)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (403, "http_403"),
        (429, "http_429"),
        (503, "http_503"),
        (500, "http_other"),
        (502, "http_other"),
        (200, None),
    ],
)
def test_detect_block_status_codes(status: int, expected: str | None) -> None:
    """D-13-BLOCK-01 signal 1: HTTP status codes map to specific block errors."""
    assert detect_block(status, _HAPPY_BODY) == expected


def test_detect_block_body_too_short() -> None:
    """body length strictly less than MIN_BODY_BYTES -> 'body_too_short' (signal 4)."""
    body = "x" * (MIN_BODY_BYTES - 1)
    assert detect_block(200, body) == "body_too_short"


def test_detect_block_body_at_exactly_min_bytes_is_not_too_short() -> None:
    """Boundary: exactly MIN_BODY_BYTES is OK (strict-<); falls through to NEXT_DATA check."""
    body = "x" * MIN_BODY_BYTES
    assert detect_block(200, body) == "missing_next_data"


@pytest.mark.parametrize("phrase", list(CAPTCHA_PHRASES))
def test_detect_block_captcha_phrases(phrase: str) -> None:
    """Each phrase fires 'captcha_detected' (signal 3) with a big-enough body."""
    body = phrase + " " + "x" * (MIN_BODY_BYTES + 200)
    assert detect_block(200, body) == "captcha_detected"


def test_detect_block_captcha_case_insensitive() -> None:
    """Captcha phrase match is case-insensitive across all 6 phrases."""
    body = "PRESS & HOLD to continue" + ("x" * MIN_BODY_BYTES)
    assert detect_block(200, body) == "captcha_detected"


def test_detect_block_missing_next_data() -> None:
    """200-status, large body, no captcha, no <script id="__NEXT_DATA__"> -> 'missing_next_data'."""
    body = "<html>" + "x" * (MIN_BODY_BYTES + 200) + "</html>"
    assert detect_block(200, body) == "missing_next_data"


def test_detect_block_happy_path_returns_none() -> None:
    """Happy path: 200 + big body + no captcha + NEXT_DATA tag present -> None."""
    assert detect_block(200, _HAPPY_BODY) is None


def test_detect_block_next_data_attribute_order_variant() -> None:
    """Pitfall 19: id="__NEXT_DATA__" preceded by type= attribute still matches."""
    body = (
        "<html>"
        + "x" * (MIN_BODY_BYTES + 200)
        + '<script type="application/json" id="__NEXT_DATA__">{}</script>'
        + "</html>"
    )
    assert detect_block(200, body) is None


def test_detect_block_status_wins_over_short_body() -> None:
    """Order check: 403 with 1KB body -> http_403, not body_too_short."""
    assert detect_block(403, "x" * 1000) == "http_403"


def test_detect_block_short_body_wins_over_captcha() -> None:
    """Order check: 200 + 1KB body containing 'recaptcha' -> body_too_short."""
    body = "recaptcha " + ("x" * 100)
    assert detect_block(200, body) == "body_too_short"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.zillow.com/homedetails/123-Main-SF-CA-94110/12345678_zpid/", "12345678"),
        ("https://zillow.com/b/87654321_zpid/", "87654321"),
        ("https://zillow.com/homedetails/foo/12345_zpid", "12345"),
        ("https://zillow.com/homedetails/foo/12345_zpid/?source=email", "12345"),
        ("https://zillow.com/homedetails/foo/12345_zpid/#photos", "12345"),
        ("http://www.zillow.com/homedetails/foo/12345_zpid/", "12345"),
        ("https://www.zillow.com/HOMEDETAILS/x/55_ZPID/", "55"),
        ("https://redfin.com/property/12345", None),
        ("https://zillow.com/homedetails/foo/", None),
        ("https://zillow.com/no-zpid-here/", None),
        ("", None),
    ],
)
def test_extract_zpid(url: str, expected: str | None) -> None:
    """INGEST-04: ZPID extraction from both URL patterns + edge cases."""
    assert extract_zpid(url) == expected
