"""Sonnet-driven __NEXT_DATA__ extraction. Phase 13 INGEST-02 + D-13-MODEL-01.

Never raises; ALL failure modes return None so the caller emits shape-2
awaiting_user_input per the always-exit-0 contract (Phase 12 CR-02).

Cost: ~$0.16/call (Sonnet 4.6: $3/$15 per 1M tokens; 50k input + 800 output).
Block detection (lib/property_block_detector.detect_block) runs BEFORE this
function to avoid wasted $0.10-$0.16 on captcha pages.

API path: Wave-0 Probe A confirmed `anthropic.messages.parse` is available
on the runtime SDK (0.100.0). This module uses `client.messages.parse(...)`
for the call; `output_format` is intentionally omitted because the prompt
instructs Sonnet to emit the JSON dict directly and downstream Pydantic
(PropertyListing) requires audit fields (source_url, zpid, fetched_at) that
the CLI layer adds AFTER this call. The first-brace regex fallback (Pitfall
18) is retained defensively for any prose-prefixed responses.
"""

from __future__ import annotations

import os
from typing import Any, Final

from lib.property_block_detector import NEXT_DATA_RE

SONNET_MODEL: Final[str] = "claude-sonnet-4-6"
SONNET_MAX_TOKENS: Final[int] = 4096
HTML_PROMPT_WINDOW_CHARS: Final[int] = 200_000
NEXT_DATA_PREFIX_CONTEXT_CHARS: Final[int] = 10_000

# Module-level injection seam for the Anthropic client constructor.
# Tests monkeypatch this attribute directly (e.g.,
# `monkeypatch.setattr("lib.property_extractor.Anthropic", _factory)`) so the
# real anthropic SDK is never imported during mocked tests. Production runs
# resolve the real class lazily inside `extract_listing` to keep module import
# cheap (the SDK pulls in heavy submodules like anthropic.lib.vertex).
Anthropic: Any = None

EXTRACTION_PROMPT: Final[str] = """\
You are extracting structured property data from a Zillow listing's HTML.
The HTML contains a <script id="__NEXT_DATA__"> tag holding the full property
record as JSON. Find that JSON. Then output a SINGLE JSON object with exactly
these fields:

  zpid               (string, required)
  price              (string, required - Decimal-safe, e.g. "625000.00")
  zip                (string, required - 5 digits)
  property_type      (one of: "SFH", "condo", "townhouse", "multifamily-2-4")
  beds               (integer or null)
  baths              (string Decimal or null - e.g. "2.5")
  sqft               (integer or null)
  year_built         (integer or null)
  tax_annual         (string Decimal or null - annual)
  hoa_monthly        (string Decimal or null - null if no HOA)
  insurance_estimate_annual  (string Decimal or null)
  zestimate          (string Decimal or null)
  days_on_market     (integer or null)
  list_date          (string YYYY-MM-DD or null)

Rules:
  1. Output JSON ONLY. No prose, no fences, no preamble.
  2. Use null for fields you cannot extract. Null is better than wrong.
  3. Money/decimal fields are JSON STRINGS, never numbers (Pydantic strict
     rejects floats for Decimal).
  4. Do not infer or guess. If the page does not state it, the field is null.
  5. property_type maps: SingleFamily/Detached -> "SFH"; Condo -> "condo";
     Townhouse -> "townhouse"; Multifamily/Duplex/Triplex/Fourplex -> "multifamily-2-4".
     Anything else (Manufactured, Cooperative) -> null (gap-fill required).

The HTML follows:

{html}
"""


def extract_listing(html: str, source_url: str) -> dict[str, object] | None:
    """Call Sonnet to extract PropertyListing-compatible fields.

    Returns a dict of field values on success or None on ANY failure
    (auth error, rate limit, network error, malformed JSON, empty content,
    non-text block, etc.). Caller (scripts/property_fetch.py) emits a
    shape-2 awaiting_user_input envelope when this returns None.

    No auto-retry per D-13-MODEL-01 - single attempt; failure falls through
    to the gap-fill CLI conversation layer.
    """
    try:
        global Anthropic
        if Anthropic is None:
            import anthropic

            Anthropic = anthropic.Anthropic

        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.parse(
            model=SONNET_MODEL,
            max_tokens=SONNET_MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(html=_html_prompt_window(html)),
                }
            ],
            # output_format omitted intentionally: the prompt instructs Sonnet
            # to emit the JSON dict directly. PropertyListing requires audit
            # fields (source_url, zpid, fetched_at) that the CLI adds AFTER
            # this call, so we cannot pass it as output_format here.
        )
        if not response.content or response.content[0].type != "text":
            return None
        raw = response.content[0].text
    except Exception:  # load-bearing always-exit-0 contract (Phase 12 CR-02)
        return None

    return _parse_json_with_prose_tolerance(raw)


def _html_prompt_window(html: str) -> str:
    if len(html) <= HTML_PROMPT_WINDOW_CHARS:
        return html
    match = NEXT_DATA_RE.search(html)
    if match is None:
        return html[:HTML_PROMPT_WINDOW_CHARS]
    start = max(0, match.start() - NEXT_DATA_PREFIX_CONTEXT_CHARS)
    end = start + HTML_PROMPT_WINDOW_CHARS
    if end > len(html):
        end = len(html)
        start = max(0, end - HTML_PROMPT_WINDOW_CHARS)
    return html[start:end]


def _parse_json_with_prose_tolerance(raw: str) -> dict[str, object] | None:
    """Strip any prose prefix and return the first brace-balanced JSON object.

    Pitfall 18: Sonnet occasionally prepends prose ("Here is the data:...")
    despite the "JSON ONLY" rule in the prompt. Decode from the first opening
    brace and let JSONDecoder stop at the end of that object.
    """
    import json

    first_brace = raw.find("{")
    if first_brace < 0:
        return None
    try:
        result, _ = json.JSONDecoder().raw_decode(raw[first_brace:])
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None
