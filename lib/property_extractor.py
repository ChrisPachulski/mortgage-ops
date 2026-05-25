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
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from lib.property_block_detector import NEXT_DATA_RE, extract_zpid

SONNET_MODEL: Final[str] = "claude-sonnet-4-6"
SONNET_MAX_TOKENS: Final[int] = 4096
HTML_PROMPT_WINDOW_CHARS: Final[int] = 200_000
NEXT_DATA_PREFIX_CONTEXT_CHARS: Final[int] = 10_000
MONEY_CENTS: Final[Decimal] = Decimal("0.01")
FREE_TEXT_KEY_PARTS: Final[tuple[str, ...]] = (
    "agent",
    "attribution",
    "broker",
    "description",
    "disclaimer",
    "marketing",
    "provider",
    "remarks",
    "seller",
)

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
    deterministic = _extract_listing_from_next_data(html)
    if not _zpid_matches_source_url(deterministic, source_url):
        return None
    if deterministic is not None and _has_required_fields(deterministic):
        return deterministic

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
                    "content": EXTRACTION_PROMPT.format(html=_model_prompt_window(html)),
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

    result = _parse_json_with_prose_tolerance(raw)
    if result is None:
        return None
    if not _model_output_matches_deterministic(result, deterministic, source_url):
        return None
    return result


def _extract_listing_from_next_data(html: str) -> dict[str, object] | None:
    data = _parse_next_data(html)
    if data is None:
        return None
    record = _find_property_record(data)
    if record is None:
        return None

    price = _money_string(_first_present(record, "price", "unformattedPrice"))
    zipcode = _string_value(
        _first_present(record, "zipcode", "zipCode", "postalCode")
        or _first_present(_dict_value(record.get("address")), "zipcode", "zipCode", "postalCode")
    )
    property_type = _property_type_value(
        _first_present(record, "propertyTypeDimension", "homeType", "propertyType")
    )

    result: dict[str, object] = {
        "zpid": _string_value(record.get("zpid")),
        "price": price,
        "zip": zipcode,
        "property_type": property_type,
        "beds": _int_value(_first_present(record, "bedrooms", "beds")),
        "baths": _decimal_string(_first_present(record, "bathrooms", "baths")),
        "sqft": _int_value(_first_present(record, "livingArea", "livingAreaValue", "sqft")),
        "year_built": _int_value(_first_present(record, "yearBuilt")),
        "tax_annual": _money_string(_first_present(record, "taxAnnualAmount", "annualTaxAmount")),
        "hoa_monthly": _money_string(_first_present(record, "hoaFee", "monthlyHoaFee")),
        "insurance_estimate_annual": _money_string(
            _first_present(record, "insuranceEstimateAnnual", "annualHomeInsurance")
        ),
        "zestimate": _money_string(_first_present(record, "zestimate")),
        "days_on_market": _int_value(_first_present(record, "daysOnZillow", "daysOnMarket")),
        "list_date": _string_value(_first_present(record, "datePostedString", "listingDate")),
    }
    return result if any(v is not None for v in result.values()) else None


def _parse_next_data(html: str) -> Any | None:
    import html as html_lib
    import json

    raw = _next_data_text(html)
    if raw is None:
        return None
    try:
        return json.loads(html_lib.unescape(raw).strip())
    except json.JSONDecodeError:
        return None


def _next_data_text(html: str) -> str | None:
    match = NEXT_DATA_RE.search(html)
    if match is None:
        return None
    end = html.find("</script>", match.end())
    if end < 0:
        return None
    return html[match.end() : end]


def _find_property_record(node: Any) -> dict[str, Any] | None:
    if isinstance(node, dict):
        if "zpid" in node and any(k in node for k in ("price", "zipcode", "propertyTypeDimension")):
            return node
        for value in node.values():
            found = _find_property_record(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_property_record(value)
            if found is not None:
                return found
    return None


def _model_prompt_window(html: str) -> str:
    data = _parse_next_data(html)
    if data is None:
        return _html_prompt_window(html)

    import json

    sanitized = _strip_free_text_fields(data)
    raw = json.dumps(sanitized, separators=(",", ":"), ensure_ascii=False)
    return raw[:HTML_PROMPT_WINDOW_CHARS]


def _strip_free_text_fields(value: Any, key: str = "") -> Any:
    lowered_key = key.lower()
    if any(part in lowered_key for part in FREE_TEXT_KEY_PARTS):
        return None
    if isinstance(value, dict):
        return {k: _strip_free_text_fields(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_free_text_fields(v, key) for v in value]
    return value


def _has_required_fields(result: dict[str, object]) -> bool:
    return all(result.get(k) is not None for k in ("zpid", "price", "zip", "property_type"))


def _zpid_matches_source_url(result: dict[str, object] | None, source_url: str) -> bool:
    if result is None or result.get("zpid") is None:
        return True
    source_zpid = extract_zpid(source_url)
    return source_zpid is None or str(result["zpid"]) == source_zpid


def _model_output_matches_deterministic(
    result: dict[str, object],
    deterministic: dict[str, object] | None,
    source_url: str,
) -> bool:
    source_zpid = extract_zpid(source_url)
    if (
        source_zpid is not None
        and result.get("zpid") is not None
        and str(result["zpid"]) != source_zpid
    ):
        return False
    if deterministic is None:
        return _has_required_fields(result)
    for key in ("zpid", "price", "zip", "property_type"):
        expected = deterministic.get(key)
        actual = result.get(key)
        if (
            expected is not None
            and actual is not None
            and not _same_extracted_value(key, actual, expected)
        ):
            return False
    return True


def _same_extracted_value(key: str, actual: object, expected: object) -> bool:
    if key == "price":
        actual_decimal = _decimal_value(actual)
        expected_decimal = _decimal_value(expected)
        return (
            actual_decimal is not None
            and expected_decimal is not None
            and actual_decimal == expected_decimal
        )
    return str(actual) == str(expected)


def _first_present(record: dict[str, Any] | None, *keys: str) -> Any | None:
    if record is None:
        return None
    for key in keys:
        value = record.get(key)
        if value is not None:
            return value
    return None


def _dict_value(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(Decimal(str(value).replace(",", "")))
    except (InvalidOperation, ValueError):
        return None


def _decimal_value(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).replace("$", "").replace(",", "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _decimal_string(value: Any) -> str | None:
    decimal = _decimal_value(value)
    return str(decimal.normalize()) if decimal is not None else None


def _money_string(value: Any) -> str | None:
    decimal = _decimal_value(value)
    return str(decimal.quantize(MONEY_CENTS)) if decimal is not None else None


def _property_type_value(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None
    normalized = text.replace("_", "").replace("-", "").replace(" ", "").lower()
    if normalized in {"singlefamily", "singlefamilyresidence", "detached"}:
        return "SFH"
    if normalized in {"condo", "condominium"}:
        return "condo"
    if normalized in {"townhouse", "townhome"}:
        return "townhouse"
    if normalized in {"multifamily", "duplex", "triplex", "fourplex"}:
        return "multifamily-2-4"
    return None


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
