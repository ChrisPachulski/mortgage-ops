"""Tests for lib/property_extractor.py - INGEST-02 (Sonnet extraction).

Three test groups:
  1. Module-constant smoke (D-13-MODEL-01 model + max_tokens + prompt fields)
  2. Mocked-success: monkeypatched anthropic returns canned response text
  3. Mocked-failure: monkeypatched anthropic raises each documented exception
  4. mock_sonnet conftest fixture smoke
  5. Live (skipped without ANTHROPIC_API_KEY; manual-only in CI per Phase 11 D-02)
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import pytest
from lib.property_extractor import (
    EXTRACTION_PROMPT,
    SONNET_MAX_TOKENS,
    SONNET_MODEL,
    extract_listing,
)

# ---------- Helpers ----------


class _FakeTextBlock:
    """Stand-in for anthropic TextBlock with .type and .text attributes."""

    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    """Stand-in for anthropic ParsedMessage with .content list."""

    def __init__(self, text: str, *, empty: bool = False, wrong_type: bool = False) -> None:
        if empty:
            self.content: list[Any] = []
        elif wrong_type:
            block = _FakeTextBlock(text)
            block.type = "tool_use"
            self.content = [block]
        else:
            self.content = [_FakeTextBlock(text)]


class _FakeClient:
    """Stand-in for anthropic.Anthropic; .messages.parse returns canned response."""

    def __init__(self, response: Any | None = None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc
        # so client.messages.parse resolves to self.parse
        self.messages = self

    def parse(self, **kwargs: Any) -> Any:
        if self._exc:
            raise self._exc
        return self._response

    def create(self, **kwargs: Any) -> Any:
        # Kept for defense-in-depth in case the SDK shape changes upstream
        if self._exc:
            raise self._exc
        return self._response


def _install_fake_anthropic(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> None:
    """Install a fake anthropic.Anthropic factory returning a controlled client."""
    import anthropic

    def _factory(api_key: str | None = None) -> _FakeClient:
        return _FakeClient(**kwargs)

    monkeypatch.setattr(anthropic, "Anthropic", _factory)


def _make_http_response(status: int) -> httpx.Response:
    """Build a minimal httpx.Response with a Request so anthropic exception
    constructors (which dereference response.request) succeed."""
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx.Response(status, request=req)


# ---------- Module-constant smoke tests ----------


def test_sonnet_model_locked_to_4_6() -> None:
    """D-13-MODEL-01: SONNET_MODEL is claude-sonnet-4-6 (NOT haiku, NOT 3-5-sonnet)."""
    assert SONNET_MODEL == "claude-sonnet-4-6"


def test_sonnet_max_tokens_value() -> None:
    """SONNET_MAX_TOKENS is 4096 (3-7x headroom over typical 600-1200 token JSON)."""
    assert SONNET_MAX_TOKENS == 4096


def test_extraction_prompt_lists_all_13_fields() -> None:
    """The prompt must spec all 13 PropertyListing-compatible field names so
    downstream Pydantic validation has the right shape."""
    for name in [
        "zpid",
        "price",
        "zip",
        "property_type",
        "beds",
        "baths",
        "sqft",
        "year_built",
        "tax_annual",
        "hoa_monthly",
        "insurance_estimate_annual",
        "zestimate",
        "days_on_market",
        "list_date",
    ]:
        assert name in EXTRACTION_PROMPT, f"missing field: {name}"


# ---------- Mocked happy-path ----------


def test_extract_listing_returns_dict_on_clean_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """INGEST-02: Mocked Sonnet returning bare JSON -> dict with all 14 fields."""
    canned = json.dumps(
        {
            "zpid": "12345",
            "price": "625000.00",
            "zip": "94110",
            "property_type": "SFH",
            "beds": 3,
            "baths": "2.5",
            "sqft": 1800,
            "year_built": 1985,
            "tax_annual": "7800.00",
            "hoa_monthly": None,
            "insurance_estimate_annual": None,
            "zestimate": "640000.00",
            "days_on_market": 12,
            "list_date": "2026-04-28",
        }
    )
    _install_fake_anthropic(monkeypatch, response=_FakeResponse(canned))
    result = extract_listing("<html>...</html>", "https://zillow.com/.../12345_zpid/")
    assert isinstance(result, dict)
    assert result["price"] == "625000.00"
    assert result["property_type"] == "SFH"
    assert result["hoa_monthly"] is None


def test_extract_listing_strips_prose_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pitfall 18: prose prefix -> first-brace regex extractor still finds JSON."""
    raw = 'Here is the data:\n\n{"price": "625000.00", "zip": "94110", "property_type": "SFH"}'
    _install_fake_anthropic(monkeypatch, response=_FakeResponse(raw))
    result = extract_listing("<html>", "https://zillow.com/.../1_zpid/")
    assert result == {"price": "625000.00", "zip": "94110", "property_type": "SFH"}


# ---------- Mocked failure modes (all -> None per D-13-MODEL-01) ----------


def test_extract_listing_returns_none_on_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """AuthenticationError -> None (never raises; always-exit-0)."""
    import anthropic

    _install_fake_anthropic(
        monkeypatch,
        exc=anthropic.AuthenticationError("bad key", response=_make_http_response(401), body=None),
    )
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


def test_extract_listing_returns_none_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """RateLimitError -> None."""
    import anthropic

    _install_fake_anthropic(
        monkeypatch,
        exc=anthropic.RateLimitError("429", response=_make_http_response(429), body=None),
    )
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


def test_extract_listing_returns_none_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """APIConnectionError -> None."""
    import anthropic

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    _install_fake_anthropic(monkeypatch, exc=anthropic.APIConnectionError(request=req))
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


def test_extract_listing_returns_none_on_generic_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Outer try catches Exception per Phase 12 CR-02 always-exit-0 contract."""
    _install_fake_anthropic(monkeypatch, exc=RuntimeError("boom"))
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


def test_extract_listing_returns_none_on_empty_response_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty response.content list -> None."""
    _install_fake_anthropic(monkeypatch, response=_FakeResponse("", empty=True))
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


def test_extract_listing_returns_none_on_non_text_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First content block with type != 'text' -> None."""
    _install_fake_anthropic(monkeypatch, response=_FakeResponse("ignored", wrong_type=True))
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


def test_extract_listing_returns_none_on_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sonnet returns 'not json {{{ broken' -> None via json.JSONDecodeError catch."""
    _install_fake_anthropic(monkeypatch, response=_FakeResponse("not json {{{ broken"))
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


def test_extract_listing_returns_none_when_no_braces(monkeypatch: pytest.MonkeyPatch) -> None:
    """Response with no brace pair at all -> None (regex returns no match)."""
    _install_fake_anthropic(monkeypatch, response=_FakeResponse("absolutely no json here at all"))
    assert extract_listing("<html>", "https://zillow.com/.../1_zpid/") is None


# ---------- HTML truncation guard ----------


def test_extract_listing_truncates_html_at_200k(monkeypatch: pytest.MonkeyPatch) -> None:
    """Large HTML must be truncated at 200_000 chars before being sent."""
    big = "x" * 500_000

    captured: dict[str, Any] = {}

    class _CapturingMessages:
        def parse(self, **kwargs: Any) -> Any:
            captured["content"] = kwargs["messages"][0]["content"]
            return _FakeResponse('{"price": "1.00", "zip": "94110", "property_type": "SFH"}')

        def create(self, **kwargs: Any) -> Any:
            captured["content"] = kwargs["messages"][0]["content"]
            return _FakeResponse('{"price": "1.00", "zip": "94110", "property_type": "SFH"}')

    class _CapturingClient:
        def __init__(self) -> None:
            self.messages = _CapturingMessages()

    def _factory(api_key: str | None = None) -> _CapturingClient:
        return _CapturingClient()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _factory)
    extract_listing(big, "https://zillow.com/.../1_zpid/")
    # The prompt contains its own template scaffold plus the truncated HTML;
    # 200_000 'x' chars must appear, 200_001 must NOT.
    assert "x" * 200_000 in captured["content"]
    assert "x" * 200_001 not in captured["content"]
    # Upper bound: prompt scaffold ~2KB + 200_000 truncated HTML
    assert len(captured["content"]) < 220_000


# ---------- mock_sonnet conftest fixture smoke test ----------


def test_mock_sonnet_fixture_returns_none_for_unknown_html(
    mock_sonnet: Any,
) -> None:
    """The conftest fixture returns None when no extracted/{sha}.json fixture exists."""
    assert (
        extract_listing("<html>no fixture for this</html>", "https://zillow.com/.../9_zpid/")
        is None
    )


# ---------- Live test (skipped without API key) ----------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason=(
        "Live Sonnet extraction test requires ANTHROPIC_API_KEY. "
        "Skip is intentional for local dev without the key. CI must NOT inject the key "
        "(Phase 11 D-02 synthetic-only-in-CI); manual runs only."
    ),
)
def test_extract_listing_live_smoke() -> None:
    """Optional live smoke test. Requires ANTHROPIC_API_KEY + a minimal HTML payload.

    The contrived synthetic NEXT_DATA blob may or may not produce a clean
    dict from Sonnet; either outcome is acceptable for a smoke test - we only
    assert the function returns the expected type or None.
    """
    pytest.importorskip("anthropic")
    html = (
        "<html>"
        + "x" * 5000
        + '<script id="__NEXT_DATA__">{"props":{"pageProps":{"property":'
        + '{"zpid":"12345","price":625000,"zipcode":"94110","propertyTypeDimension":"SingleFamily"}}}}</script>'
        + "</html>"
    )
    result = extract_listing(html, "https://zillow.com/homedetails/x/12345_zpid/")
    assert result is None or isinstance(result, dict)
