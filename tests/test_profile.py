"""Tests for lib/profile.py — Phase 14 Profile model contract.

Phase 14 Plan 14-01 (Task 2). Pins the contract per PATTERNS.md L156-161 and
CONTEXT D-14-MODELS-02 (Claude's Discretion resolution): Profile carries
va_eligible + first_time_buyer + military_status + filing_status +
marginal_tax_rate. These are analysis-time eligibility booleans + preferences,
NOT financial state; financial state lives on lib.household.Household.

Each test independently constructs a Profile instance and asserts a single
behavior; negative cases use pytest.raises(ValidationError).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from lib.profile import FilingStatus, MilitaryStatus, Profile  # noqa: F401
from pydantic import ValidationError

# --- defaults (D-14-MODELS-02 locked) ----------------------------------------


def test_va_eligible_default() -> None:
    """va_eligible defaults to False (PATTERNS.md L157)."""
    p = Profile()
    assert p.va_eligible is False


def test_first_time_buyer_default() -> None:
    """first_time_buyer defaults to False."""
    p = Profile()
    assert p.first_time_buyer is False


def test_military_status_default_none() -> None:
    """military_status defaults to 'none' (PATTERNS.md L159)."""
    p = Profile()
    assert p.military_status == "none"


def test_filing_status_default_mfj() -> None:
    """filing_status defaults to 'mfj' (PATTERNS.md L160)."""
    p = Profile()
    assert p.filing_status == "mfj"


def test_marginal_tax_rate_optional_default_none() -> None:
    """marginal_tax_rate is optional; default None (only consumed by TaxBlock when set)."""
    p = Profile()
    assert p.marginal_tax_rate is None


# --- overrides round-trip -----------------------------------------------------


def test_overrides_validate() -> None:
    """va_eligible=True + military_status='veteran' overrides intact."""
    p = Profile(va_eligible=True, military_status="veteran")
    assert p.va_eligible is True
    assert p.military_status == "veteran"


# --- Literal enforcement ------------------------------------------------------


def test_invalid_military_status_rejected() -> None:
    """MilitaryStatus Literal rejects unknown values."""
    with pytest.raises(ValidationError):
        Profile(military_status="invalid")  # type: ignore[arg-type]


def test_invalid_filing_status_rejected() -> None:
    """FilingStatus Literal rejects unknown values."""
    with pytest.raises(ValidationError):
        Profile(filing_status="invalid")  # type: ignore[arg-type]


# --- extra="forbid" ----------------------------------------------------------


def test_extra_forbid() -> None:
    """extra='forbid' rejects unknown fields."""
    with pytest.raises(ValidationError):
        Profile(unknown_field="x")  # type: ignore[call-arg]


# --- Rate bounds on marginal_tax_rate ----------------------------------------


def test_marginal_tax_rate_range() -> None:
    """marginal_tax_rate uses Rate alias (le=1); Decimal('1.5') raises."""
    # Valid case
    p = Profile(marginal_tax_rate=Decimal("0.32"))
    assert p.marginal_tax_rate == Decimal("0.32")
    # Invalid case (over 1.0)
    with pytest.raises(ValidationError):
        Profile(marginal_tax_rate=Decimal("1.5"))


# --- frozen=True hashability -------------------------------------------------


def test_frozen_profile_is_hashable() -> None:
    """frozen=True makes Profile hashable (set/dict-key usable)."""
    p = Profile()
    assert hash(p) is not None
    assert {p} == {p}


# --- round-trip JSON --------------------------------------------------------


def test_round_trip_serialization() -> None:
    """model_validate_json(model_dump_json()) == original (frozen __eq__)."""
    p = Profile(
        va_eligible=True,
        first_time_buyer=True,
        military_status="veteran",
        filing_status="single",
        marginal_tax_rate=Decimal("0.24"),
    )
    s = p.model_dump_json()
    assert Profile.model_validate_json(s) == p
