"""Tests for lib/rules/va_residual_income.py — RUL-07.

Citation under test: VA Lender Handbook M26-7 Topic 7 — geographic-regional
residual-income tables. Pinned to fixtures.

Every assertion includes the hand-calculated expected value and why.

CRITICAL: binding_rule_citation must be exactly "VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}".
Phase 4 AFFD-07 reads this string verbatim as a "blocked_by" sentinel; format
drift here breaks Phase 4. Tests pin the format on every fixture.

Coverage:
  - West family-4 above-80k pass: $1,117 minimum, $1,200 actual → pass
  - West family-4 above-80k fail: $1,117 minimum, $500 actual → fail (same citation)
  - Midwest family-6 above-80k extra-member: ($1,039 + $80) = $1,119 minimum
  - Northeast family-2 below-80k band: uses table_below_80k → $654
  - Family size validation: family_size < 1 raises ValueError
  - Loan amount validation: loan_amount <= 0 raises ValueError
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.va_residual_income import ResidualIncomeResult, evaluate, minimum_required

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def test_west_family4_above_80k_pass() -> None:
    # Hand: West family-4, $400k loan -> table_above_80k['west']['4']=$1,117.
    # Actual $1,200 >= $1,117 -> pass.
    fx = _fx("va_residual_income_west_family4_pass.json")
    result = evaluate(
        region=fx["region"],
        family_size=fx["family_size"],
        loan_amount=Decimal(fx["loan_amount"]),
        actual_residual_income=Decimal(fx["actual_residual_income"]),
    )
    assert isinstance(result, ResidualIncomeResult)
    assert result.status == fx["expected_status"] == "pass"
    assert result.minimum_required == Decimal(fx["expected_minimum_required"])
    assert result.binding_rule_citation == fx["expected_binding_rule_citation"]
    assert result.binding_rule_citation == "VA-RESIDUAL-WEST-FAMILY-4"


def test_west_family4_above_80k_fail() -> None:
    # Hand: same minimum $1,117; actual $500 < $1,117 -> fail. Citation MUST be
    # identical to pass-case (AFFD-07 sentinel stability).
    fx = _fx("va_residual_income_west_family4_fail.json")
    result = evaluate(
        region=fx["region"],
        family_size=fx["family_size"],
        loan_amount=Decimal(fx["loan_amount"]),
        actual_residual_income=Decimal(fx["actual_residual_income"]),
    )
    assert result.status == fx["expected_status"] == "fail"
    assert result.minimum_required == Decimal(fx["expected_minimum_required"])
    assert result.binding_rule_citation == "VA-RESIDUAL-WEST-FAMILY-4"


def test_midwest_family6_includes_extra_member_increment() -> None:
    # Hand: Midwest family-6 above-80k. Base $1,039 (family-5 row) + 1 * $80
    # extra-member increment = $1,119. Actual $1,500 >= $1,119 -> pass.
    fx = _fx("va_residual_income_midwest_family6_extra_member.json")
    result = evaluate(
        region=fx["region"],
        family_size=fx["family_size"],
        loan_amount=Decimal(fx["loan_amount"]),
        actual_residual_income=Decimal(fx["actual_residual_income"]),
    )
    assert result.status == "pass"
    assert result.minimum_required == Decimal("1119.00")
    assert result.binding_rule_citation == "VA-RESIDUAL-MIDWEST-FAMILY-6"


def test_northeast_family2_below_80k_band() -> None:
    # Hand: Northeast family-2, $75k loan (< $80k threshold) -> uses table_below_80k.
    # Cell value $654; actual $700 >= $654 -> pass.
    fx = _fx("va_residual_income_northeast_below_80k.json")
    result = evaluate(
        region=fx["region"],
        family_size=fx["family_size"],
        loan_amount=Decimal(fx["loan_amount"]),
        actual_residual_income=Decimal(fx["actual_residual_income"]),
    )
    assert result.status == "pass"
    assert result.minimum_required == Decimal("654.00")
    assert result.binding_rule_citation == "VA-RESIDUAL-NORTHEAST-FAMILY-2"


def test_minimum_required_helper_returns_quantized_two_places() -> None:
    # Money discipline: helper output is quantized to 2 decimal places.
    result = minimum_required(region="west", family_size=4, loan_amount=Decimal("400000.00"))
    assert result == Decimal("1117.00")
    assert result.as_tuple().exponent == -2


def test_family_size_below_one_raises() -> None:
    # Loud failure on invalid input.
    with pytest.raises(ValueError, match="family_size"):
        evaluate(
            region="west",
            family_size=0,
            loan_amount=Decimal("400000.00"),
            actual_residual_income=Decimal("1500.00"),
        )


def test_loan_amount_zero_raises() -> None:
    with pytest.raises(ValueError, match="loan_amount"):
        evaluate(
            region="west",
            family_size=4,
            loan_amount=Decimal("0"),
            actual_residual_income=Decimal("1500.00"),
        )
