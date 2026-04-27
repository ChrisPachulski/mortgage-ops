"""Tests for lib/rules/conventional_pmi.py — HPA 12 USC §4901-4910 (RUL-05).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - §4902(b): auto-termination at exactly 0.78 LTV
  - §4902(a): request-eligible at exactly 0.80 LTV
  - in_force above 0.80 LTV (negative case)
  - §4902(g): high-risk midpoint carve-out — terminates past midpoint regardless of LTV
  - high-risk before midpoint: standard 78%/80% rules still apply
  - fail-loud: ValueError for original_property_value <= 0
  - fail-loud: ValueError for is_high_risk=True with months_elapsed=None
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.models import Loan
from lib.rules.conventional_pmi import (
    LTV_AUTO_TERMINATE,
    LTV_REQUEST_ELIGIBLE,
    status,
)

FIX_DIR: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX_DIR / name).read_text())
    return data


def _loan_from_fixture(fx: dict[str, Any]) -> Loan:
    return Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
    )


def test_statutory_constants_match_hpa() -> None:
    # Hand: §4902(b) auto = 0.78; §4902(a) request = 0.80. Pin to exact Decimal strings.
    assert Decimal("0.78") == LTV_AUTO_TERMINATE
    assert Decimal("0.80") == LTV_REQUEST_ELIGIBLE


def test_auto_terminates_at_exact_78_ltv() -> None:
    fx = _load("conventional_pmi_auto_terminate_78ltv.json")
    # Hand: $156k / $200k = 0.78 exactly -> auto_terminated per §4902(b).
    result = status(
        loan=_loan_from_fixture(fx),
        scheduled_balance=Decimal(fx["scheduled_balance"]),
        original_property_value=Decimal(fx["original_property_value"]),
        is_high_risk=fx["is_high_risk"],
        months_elapsed=fx["months_elapsed"],
    )
    assert result == fx["expected_status"] == "auto_terminated"


def test_request_eligible_at_exact_80_ltv() -> None:
    fx = _load("conventional_pmi_request_eligible_80ltv.json")
    # Hand: $160k / $200k = 0.80 exactly -> request_eligible per §4902(a).
    result = status(
        loan=_loan_from_fixture(fx),
        scheduled_balance=Decimal(fx["scheduled_balance"]),
        original_property_value=Decimal(fx["original_property_value"]),
        is_high_risk=fx["is_high_risk"],
        months_elapsed=fx["months_elapsed"],
    )
    assert result == fx["expected_status"] == "request_eligible"


def test_in_force_at_81_ltv() -> None:
    fx = _load("conventional_pmi_in_force_81ltv.json")
    # Hand: $162k / $200k = 0.81 -> in_force (above the 0.80 request threshold).
    result = status(
        loan=_loan_from_fixture(fx),
        scheduled_balance=Decimal(fx["scheduled_balance"]),
        original_property_value=Decimal(fx["original_property_value"]),
        is_high_risk=fx["is_high_risk"],
        months_elapsed=fx["months_elapsed"],
    )
    assert result == fx["expected_status"] == "in_force"


def test_high_risk_terminates_at_midpoint() -> None:
    fx = _load("conventional_pmi_high_risk_midpoint.json")
    # Hand: 360-month term -> midpoint=180. months_elapsed=181 >= 180 -> terminates
    # per §4902(g) regardless of LTV (here LTV=0.95 would otherwise be in_force).
    result = status(
        loan=_loan_from_fixture(fx),
        scheduled_balance=Decimal(fx["scheduled_balance"]),
        original_property_value=Decimal(fx["original_property_value"]),
        is_high_risk=fx["is_high_risk"],
        months_elapsed=fx["months_elapsed"],
    )
    assert result == fx["expected_status"] == "high_risk_midpoint_terminated"


def test_high_risk_before_midpoint_in_force() -> None:
    # Same high-risk fixture but months_elapsed=179 (one month before midpoint=180).
    # Hand: 179 < 180 -> §4902(g) does NOT trigger; standard rules apply; LTV=0.95
    # -> in_force.
    fx = _load("conventional_pmi_high_risk_midpoint.json")
    result = status(
        loan=_loan_from_fixture(fx),
        scheduled_balance=Decimal(fx["scheduled_balance"]),
        original_property_value=Decimal(fx["original_property_value"]),
        is_high_risk=True,
        months_elapsed=179,
    )
    assert result == "in_force"


def test_zero_original_value_raises_loud() -> None:
    # Hand: division-by-zero guard; HPA LTV is undefined when original value is 0.
    loan = Loan(
        principal=Decimal("200000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    with pytest.raises(ValueError, match="original_property_value"):
        status(
            loan=loan,
            scheduled_balance=Decimal("100000"),
            original_property_value=Decimal("0"),
        )


def test_negative_original_value_raises_loud() -> None:
    loan = Loan(
        principal=Decimal("200000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    with pytest.raises(ValueError, match="original_property_value"):
        status(
            loan=loan,
            scheduled_balance=Decimal("100000"),
            original_property_value=Decimal("-1"),
        )


def test_high_risk_without_months_elapsed_raises_loud() -> None:
    # Hand: §4902(g) midpoint check needs months_elapsed; missing input is a
    # caller bug, not a silent default.
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.085000"),
        term_months=360,
    )
    with pytest.raises(ValueError, match="months_elapsed"):
        status(
            loan=loan,
            scheduled_balance=Decimal("380000"),
            original_property_value=Decimal("400000"),
            is_high_risk=True,
            months_elapsed=None,
        )
