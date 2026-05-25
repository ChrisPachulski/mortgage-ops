"""Block-signal detection + ZPID extraction.

Phase 13 D-13-BLOCK-01 + INGEST-04. Pure stdlib (re only); no third-party deps.

`detect_block(status_code, body)` returns the first matching BlockError or None.
Detection order is cheap-first to minimize work on the happy path:
    1. HTTP status != 200 -> http_403 / http_429 / http_503 / http_other
    2. Body length < 5000 bytes -> body_too_short
    3. Body contains any captcha phrase (case-insensitive) -> captcha_detected
    4. Body has no <script id="__NEXT_DATA__"> -> missing_next_data

Runs BEFORE the Sonnet extraction call in scripts/property_fetch.py - saves
~$0.16/blocked-page (50k input tokens never sent).

`extract_zpid(url)` parses ZPID from BOTH supported URL patterns:
    /homedetails/{slug}/{zpid}_zpid/   (the common pattern)
    /b/{zpid}_zpid/                    (the shortlink pattern)
Returns None for non-Zillow URLs, malformed URLs, or empty strings.
"""

from __future__ import annotations

import re
from typing import Final, Literal
from urllib.parse import urlparse

BlockError = Literal[
    "http_403",
    "http_429",
    "http_503",
    "http_other",
    "missing_next_data",
    "captcha_detected",
    "body_too_short",
]

CAPTCHA_PHRASES: Final[tuple[str, ...]] = (
    "press & hold",
    "human verification",
    "px-captcha",
    "are you a robot",
    "unusual traffic",
    "recaptcha",
)
MIN_BODY_BYTES: Final[int] = 5000

# Pitfall 19: attribute order varies (id=... type=... vs type=... id=...).
# Match any <script ...> that contains id="__NEXT_DATA__" anywhere in its attrs.
NEXT_DATA_RE: Final[re.Pattern[str]] = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>',
    re.IGNORECASE,
)

# INGEST-04: both URL patterns. ZPID is digits-only; slug is anything non-/.
ZPID_RE: Final[re.Pattern[str]] = re.compile(
    r"/(?:homedetails/[^/]+/|b/)(\d+)_zpid/?",
    re.IGNORECASE,
)


def detect_block(status_code: int, body: str) -> BlockError | None:
    """Return first matching block error or None. See module docstring for order."""
    if status_code == 403:
        return "http_403"
    if status_code == 429:
        return "http_429"
    if status_code == 503:
        return "http_503"
    if status_code != 200:
        return "http_other"
    if len(body) < MIN_BODY_BYTES:
        return "body_too_short"
    lowered = body.lower()
    if any(phrase in lowered for phrase in CAPTCHA_PHRASES):
        return "captcha_detected"
    if NEXT_DATA_RE.search(body) is None:
        return "missing_next_data"
    return None


def extract_zpid(url: str) -> str | None:
    """Extract ZPID from Zillow URL. Returns None for non-Zillow / malformed URLs.

    INGEST-04 supports BOTH:
        zillow.com/homedetails/{slug}/{zpid}_zpid/
        zillow.com/b/{zpid}_zpid/
    Trailing slash, query string, fragment, and http/https scheme variants all work.
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname.lower().rstrip(".") if parsed.hostname else ""
    except ValueError:
        return None
    if host != "zillow.com" and not host.endswith(".zillow.com"):
        return None
    match = ZPID_RE.search(parsed.path)
    return match.group(1) if match else None
