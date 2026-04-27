"""Tests for lib/rules/usda.py — RUL-08.

Citation under test: 7 CFR Part 3555 + USDA SFH GLP eligibility worksheet.
Pinned to fixtures with hand-calc derivations.

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - Default county, family-4, at the limit -> income_eligible=True (boundary)
  - Default county, family-4, $150 over the limit -> income_eligible=False
  - Family-7 uses persons_5_to_8 limit with NO uplift (band boundary)
  - San Francisco county override resolves to higher limit
  - Guarantee fees quantized to 2 decimals (money discipline)
  - Negative / zero inputs raise ValueError (loud failure)
  - LOCKED DECISION (D-PHASE2-Q5): unlisted county silently falls back to
    default limits — does NOT raise MissingCountyDataError. This is correct
    USDA semantics; see module docstring for rationale.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.types import County
from lib.rules.usda import USDAEligibilityResult, evaluate

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def _county(d: dict[str, Any]) -> County:
    return County(
        state_fips=d["state_fips"],
        county_fips=d["county_fips"],
        name=d["name"],
    )


def test_default_county_family4_at_limit_is_eligible() -> None:
    # Hand: 119850 <= 119850 -> True. Boundary test: equality counts as eligible
    # per USDA published "115% of AMI or below."
    fx = _fx("usda_income_eligible_default_county.json")
    result = evaluate(
        household_income=Decimal(fx["household_income"]),
        household_size=fx["household_size"],
        county=_county(fx["county"]),
        loan_amount=Decimal(fx["loan_amount"]),
    )
    assert isinstance(result, USDAEligibilityResult)
    assert result.income_eligible is fx["expected_income_eligible"]
    assert result.applicable_income_limit == Decimal(fx["expected_applicable_income_limit"])
    assert result.guarantee_fee_upfront == Decimal(fx["expected_guarantee_fee_upfront"])
    assert result.guarantee_fee_annual == Decimal(fx["expected_guarantee_fee_annual"])


def test_default_county_family4_over_limit_is_ineligible() -> None:
    # Hand: 120000 > 119850 -> False. Note guarantee fees STILL computed —
    # downstream consumer decides what to do with them.
    fx = _fx("usda_income_over_limit_default_county.json")
    result = evaluate(
        household_income=Decimal(fx["household_income"]),
        household_size=fx["household_size"],
        county=_county(fx["county"]),
        loan_amount=Decimal(fx["loan_amount"]),
    )
    assert result.income_eligible is False
    assert result.applicable_income_limit == Decimal(fx["expected_applicable_income_limit"])
    assert result.guarantee_fee_upfront == Decimal(fx["expected_guarantee_fee_upfront"])
    assert result.guarantee_fee_annual == Decimal(fx["expected_guarantee_fee_annual"])


def test_family_seven_uses_5_8_person_limit_with_uplift() -> None:
    # Hand: family-7 falls in the 5-8 band (NOT > 8) -> applicable_income_limit
    # = persons_5_to_8 = $158,250 with NO per-extra-member uplift. Boundary
    # protection: ensure uplift is NOT erroneously applied at sizes 5..8.
    fx = _fx("usda_family_seven_extra_member_uplift.json")
    result = evaluate(
        household_income=Decimal(fx["household_income"]),
        household_size=fx["household_size"],
        county=_county(fx["county"]),
        loan_amount=Decimal(fx["loan_amount"]),
    )
    assert result.applicable_income_limit == Decimal(fx["expected_applicable_income_limit"])
    assert result.income_eligible is False  # 165000 > 158250


def test_san_francisco_county_override_higher_limit() -> None:
    # Hand: by_county lookup finds (state_fips=06, county_fips=075) -> override
    # applicable_income_limit = $211,800. 200000 <= 211800 -> eligible.
    fx = _fx("usda_county_override_san_francisco.json")
    result = evaluate(
        household_income=Decimal(fx["household_income"]),
        household_size=fx["household_size"],
        county=_county(fx["county"]),
        loan_amount=Decimal(fx["loan_amount"]),
    )
    assert result.income_eligible is True
    assert result.applicable_income_limit == Decimal(fx["expected_applicable_income_limit"])
    assert result.guarantee_fee_upfront == Decimal(fx["expected_guarantee_fee_upfront"])
    assert result.guarantee_fee_annual == Decimal(fx["expected_guarantee_fee_annual"])


def test_guarantee_fees_quantized_two_places() -> None:
    # Money discipline: $123,456.78 * 0.0100 = 1234.5678 -> ROUND_HALF_UP -> 1234.57.
    # $123,456.78 * 0.0035 = 432.0987... -> ROUND_HALF_UP -> 432.10.
    result = evaluate(
        household_income=Decimal("100000"),
        household_size=4,
        county=County(state_fips="01", county_fips="001", name="Autauga"),
        loan_amount=Decimal("123456.78"),
    )
    assert result.guarantee_fee_upfront == Decimal("1234.57")
    assert result.guarantee_fee_upfront.as_tuple().exponent == -2
    assert result.guarantee_fee_annual == Decimal("432.10")
    assert result.guarantee_fee_annual.as_tuple().exponent == -2


def test_negative_loan_amount_raises() -> None:
    # Loud failure: invalid input.
    with pytest.raises(ValueError, match="loan_amount"):
        evaluate(
            household_income=Decimal("100000"),
            household_size=4,
            county=County(state_fips="01", county_fips="001", name="Autauga"),
            loan_amount=Decimal("-100"),
        )


def test_zero_household_size_raises() -> None:
    # Loud failure: invalid input.
    with pytest.raises(ValueError, match="household_size"):
        evaluate(
            household_income=Decimal("100000"),
            household_size=0,
            county=County(state_fips="01", county_fips="001", name="Autauga"),
            loan_amount=Decimal("200000"),
        )


def test_unlisted_county_silently_uses_default_per_locked_decision() -> None:
    # LOCKED DECISION (D-PHASE2-Q5): unlisted county -> silent fallback to
    # default. NOT a MissingCountyDataError. This is correct USDA semantics.
    # Future "fix" attempts to raise MUST be rejected — see module docstring.
    result = evaluate(
        household_income=Decimal("100000"),
        household_size=4,
        county=County(state_fips="99", county_fips="999", name="DefinitelyNotInOverrideList"),
        loan_amount=Decimal("200000"),
    )
    # Hand: county not in by_county -> fall back to default 1-4-person = $119,850.
    assert result.applicable_income_limit == Decimal("119850")
    assert result.income_eligible is True  # 100000 <= 119850
