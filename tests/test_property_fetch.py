"""Tests for .claude/skills/mortgage-ops/scripts/property_fetch.py — INGEST-01 + INGEST-03.

Wave 0 xfail scaffold; Wave 4 (Plan 13-04) flips green.
Mirrors tests/test_fred_cli.py SCRIPT_PATH + subprocess.run pattern.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "property_fetch.py"
)


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_property_fetch_help_fast_lazy_imports() -> None:
    """INGEST-01: D-18 inherited: --help <300ms; no anthropic/duckdb import on --help path."""
    assert SCRIPT_PATH.exists(), "Wave 4 creates this script"


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_blocked_captcha_envelope_exit_0() -> None:
    """INGEST-01 + D-13-BLOCK-01: captcha fixture -> exit 0 + envelope.error='captcha_detected'."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_body_too_short_envelope() -> None:
    """INGEST-01 + D-13-BLOCK-01 signal 4: synthetic 1KB body -> error='body_too_short'."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_zpid_extraction_failed_envelope() -> None:
    """INGEST-01: Non-Zillow URL -> error='zpid_extraction_failed', exit 0."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_user_provided_money_strip_dollar_comma() -> None:
    """INGEST-03 + Pitfall 16: --user-provided '{"price":"$625,000"}' -> '625000.00' (strip $ and ,, pad .00)."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_user_provided_tags_provenance() -> None:
    """INGEST-03 + D-13-GAPFILL-01: --user-provided values tagged provenance='user_provided'."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_argparse_error_exit_2() -> None:
    """INGEST-01: The one documented non-zero exit — argparse parse errors get exit 2 (Phase 12 WR-02)."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_unexpected_exception_outer_try_exit_0() -> None:
    """INGEST-01 + Phase 12 CR-02: outer try/except catches; emits envelope; exit 0."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_success_envelope_shape_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """INGEST-01: shape-1 success with mocked Sonnet against sfh_conforming_happy_path.html."""
    assert SCRIPT_PATH.exists()


@pytest.mark.xfail(reason="Phase 13 Wave 4: property_fetch.py not yet built", strict=True)
def test_awaiting_user_input_shape_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """INGEST-03: Mocked Sonnet returns price+property_type only -> shape-2 with missing=['zip']."""
    assert SCRIPT_PATH.exists()
