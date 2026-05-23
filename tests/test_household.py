"""Tests for lib/household.py — Phase 14 Household model contract.

Phase 14 Plan 14-01 (Task 1 RED gate). Pins the contract per PATTERNS.md L104-117
and CONTEXT D-14-MODELS-01 + D-14-STRESS-02. Each test independently constructs
a Household instance and asserts a single behavior; negative cases use the
pytest.raises(ValidationError) idiom from tests/test_property_listing.py.

DISTINCT from lib.affordability.Household (Phase 4 frozen contract) — Plan 14-02
disambiguates downstream consumers via `from lib.affordability import Household
as AffordabilityHousehold`. These tests target lib.household.Household only.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from lib.household import Household
from pydantic import ValidationError


def _make_clean_household_kwargs(**overrides: Any) -> dict[str, Any]:
    """Factory: return a minimum-required-fields-only Household kwargs dict.

    Mirrors `_valid_applicant_kwargs` from tests/test_affordability.py. Defaults
    are: monthly_income="12000.00", monthly_obligations="400.00", fico=740,
    liquid_reserves="50000.00", state_fips="53", county_fips="033",
    county_name="King". preferred_down_payment_pct is intentionally omitted so
    callers can assert the Decimal("0.20") default.
    """
    defaults: dict[str, Any] = {
        "monthly_income": Decimal("12000.00"),
        "monthly_obligations": Decimal("400.00"),
        "fico": 740,
        "liquid_reserves": Decimal("50000.00"),
        "state_fips": "53",
        "county_fips": "033",
        "county_name": "King",
    }
    defaults.update(overrides)
    return defaults


# --- D-14-MODELS-01 baseline + D-14-STRESS-02 default ------------------------


def test_clean_household_validates() -> None:
    """Minimum-required-fields-only construction succeeds; default DP = 0.20."""
    h = Household(**_make_clean_household_kwargs())
    assert h.monthly_income == Decimal("12000.00")
    assert h.monthly_obligations == Decimal("400.00")
    assert h.fico == 740
    assert h.liquid_reserves == Decimal("50000.00")
    assert h.state_fips == "53"
    assert h.county_fips == "033"
    assert h.county_name == "King"
    # D-14-STRESS-02 default
    assert h.preferred_down_payment_pct == Decimal("0.20")


# --- extra="forbid" ----------------------------------------------------------


def test_extra_forbid() -> None:
    """extra='forbid' rejects unknown fields (lib/models.py convention)."""
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(unknown_field="x"))


# --- strict=True money discipline --------------------------------------------


def test_rejects_float_monthly_income_strict_true() -> None:
    """Money strict=True rejects float for monthly_income (CLAUDE.md money discipline)."""
    with pytest.raises(ValidationError):
        # Intentional type-system bypass via factory dict — strict=True is the runtime gate.
        Household(**_make_clean_household_kwargs(monthly_income=12000.0))


def test_rejects_zero_monthly_income() -> None:
    """monthly_income=0 must raise — Money alias allows ge=0 for other uses,
    but a household's monthly_income=0 would explode downstream DTI denominators
    in lib/property_analysis.py. Boundary type rejects strictly."""
    with pytest.raises(ValidationError) as exc_info:
        Household(**_make_clean_household_kwargs(monthly_income=Decimal("0")))
    # Validator emits a clear message naming the field and value.
    assert "Monthly income must be > 0" in str(exc_info.value)


# --- fico bounds -------------------------------------------------------------


def test_fico_range_rejects_below_300_and_above_850() -> None:
    """Field(ge=300, le=850) rejects 299 and 851."""
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(fico=299))
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(fico=851))


# --- state_fips / county_fips pattern enforcement ----------------------------


def test_state_fips_pattern_enforced() -> None:
    """state_fips must match ^\\d{2}$ (LocationFIPS pattern from lib/affordability.py L347)."""
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(state_fips="5"))
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(state_fips="ABC"))


def test_county_fips_pattern_enforced() -> None:
    """county_fips must match ^\\d{3}$ (3 digits exactly)."""
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(county_fips="33"))
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(county_fips="ABCD"))


# --- frozen=True hashability -------------------------------------------------


def test_frozen_household_is_hashable() -> None:
    """frozen=True makes Household hashable (usable as dict key / set member)."""
    h = Household(**_make_clean_household_kwargs())
    assert hash(h) is not None
    assert {h} == {h}


# --- D-14-STRESS-02 preferred_down_payment_pct -------------------------------


def test_preferred_dp_default_decimal_0_20() -> None:
    """preferred_down_payment_pct defaults to Decimal('0.20') per D-14-STRESS-02."""
    h = Household(**_make_clean_household_kwargs())
    assert h.preferred_down_payment_pct == Decimal("0.20")


def test_preferred_dp_rate_ge_0_le_1() -> None:
    """preferred_down_payment_pct uses Rate alias (le=1); 1.5 raises."""
    with pytest.raises(ValidationError):
        Household(**_make_clean_household_kwargs(preferred_down_payment_pct=Decimal("1.5")))


# --- round-trip serialization (money discipline) -----------------------------


def test_round_trip_serialization_money_as_string() -> None:
    """Decimal -> JSON STRING; round-trip equality preserved (frozen __eq__)."""
    h = Household(**_make_clean_household_kwargs())
    s = h.model_dump_json()
    # CLAUDE.md money discipline: Decimal serialized as JSON STRING
    assert '"monthly_income":"12000.00"' in s
    # Round-trip equality
    assert Household.model_validate_json(s) == h
