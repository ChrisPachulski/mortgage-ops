"""Tests for lib/rules/fha_mip.py — RUL-04.

Citation under test: HUD ML 2023-05 (annual MIP rates) + HUD ML 2013-04
(termination rules). Pinned to fixtures with hand-calc derivations.

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - LTV > 90% (term 30): annual_mip=0.0055; terminates life_of_loan
  - LTV <= 90% (term 30): annual_mip=0.0050; terminates at 132mo
  - Short term (term 15) at low LTV: annual_mip=0.0015
  - Pre-2023-03-20 endorsement: NotImplementedError (Pitfall 5 protection)
  - UFMIP returned with exact two-decimal-place quantization (money discipline)
  - LTV > 1.00 raises ValueError (loud failure on invalid input)
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.models import Loan
from lib.rules.fha_mip import MIPResult, compute

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def _loan_from_fx(fx_loan: dict[str, Any]) -> Loan:
    return Loan(
        principal=Decimal(fx_loan["principal"]),
        annual_rate=Decimal(fx_loan["annual_rate"]),
        term_months=fx_loan["term_months"],
        origination_date=date.fromisoformat(fx_loan["origination_date"]),
        loan_type=fx_loan["loan_type"],
    )


def test_fha_mip_term30_ltv95_post_2023_returns_life_of_loan() -> None:
    # Hand: LTV = $400k / $410k ~= 0.9756 > 0.90 -> life_of_loan.
    # Annual MIP table row [0.95<LTV<=1.00, term<=360, <=$726k] -> 0.0055.
    # UFMIP = $400k * 0.0175 = $7,000.00.
    fx = _fx("fha_mip_term30_ltv95_post_2023.json")
    loan = _loan_from_fx(fx["loan"])
    result = compute(
        loan=loan,
        original_property_value=Decimal(fx["original_property_value"]),
        endorsement_date=date.fromisoformat(fx["endorsement_date"]),
    )
    assert isinstance(result, MIPResult)
    assert result.ufmip == Decimal(fx["expected_ufmip"])
    assert result.annual_mip_pct == Decimal(fx["expected_annual_mip_pct"])
    assert result.terminates_at_period == fx["expected_terminates_at_period"]


def test_fha_mip_term30_ltv85_post_2023_terminates_at_132mo() -> None:
    # Hand: LTV = $400k / $470k ~= 0.8511 <= 0.90 -> 132mo termination (11 years).
    # Annual MIP row [0.00<LTV<=0.90, term<=360, <=$726k] -> 0.0050.
    # UFMIP unchanged at $7,000.00.
    fx = _fx("fha_mip_term30_ltv85_post_2023.json")
    loan = _loan_from_fx(fx["loan"])
    result = compute(
        loan=loan,
        original_property_value=Decimal(fx["original_property_value"]),
        endorsement_date=date.fromisoformat(fx["endorsement_date"]),
    )
    assert result.ufmip == Decimal(fx["expected_ufmip"])
    assert result.annual_mip_pct == Decimal(fx["expected_annual_mip_pct"])
    assert result.terminates_at_period == fx["expected_terminates_at_period"]


def test_fha_mip_term15_ltv75_post_2023_short_term_low_rate() -> None:
    # Hand: LTV = $300k / $400k = 0.75 -> short-term low-LTV row -> 0.0015.
    # UFMIP = $300k * 0.0175 = $5,250.00. Terminates at 132mo (LTV <= 0.90).
    fx = _fx("fha_mip_term15_ltv90_post_2023.json")
    loan = _loan_from_fx(fx["loan"])
    result = compute(
        loan=loan,
        original_property_value=Decimal(fx["original_property_value"]),
        endorsement_date=date.fromisoformat(fx["endorsement_date"]),
    )
    assert result.ufmip == Decimal(fx["expected_ufmip"])
    assert result.annual_mip_pct == Decimal(fx["expected_annual_mip_pct"])
    assert result.terminates_at_period == fx["expected_terminates_at_period"]


def test_fha_mip_pre_2023_endorsement_raises() -> None:
    # Hand: endorsement_date 2014-08-01 < 2023-03-20 -> NotImplementedError.
    # Pitfall 5: silent grandfathering would understate user's MIP burden.
    fx = _fx("fha_mip_pre_2023_raises.json")
    loan = _loan_from_fx(fx["loan"])
    with pytest.raises(NotImplementedError, match=fx["expected_match"]):
        compute(
            loan=loan,
            original_property_value=Decimal(fx["original_property_value"]),
            endorsement_date=date.fromisoformat(fx["endorsement_date"]),
        )


def test_fha_mip_ufmip_returns_quantized_two_places() -> None:
    # Money discipline: UFMIP must be quantized to exactly 2 decimal places.
    # $123,456.78 * 0.0175 = $2,160.4936650 -- must round to $2,160.49.
    loan = Loan(
        principal=Decimal("123456.78"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2024, 6, 15),
        loan_type="fha",
    )
    result = compute(
        loan=loan,
        original_property_value=Decimal("150000.00"),
        endorsement_date=date(2024, 6, 15),
    )
    # Hand: 123456.78 * 0.0175 = 2160.493650 -> ROUND_HALF_UP -> 2160.49.
    assert result.ufmip == Decimal("2160.49")
    # Sanity: exactly 2 decimal places (Decimal exponent = -2).
    assert result.ufmip.as_tuple().exponent == -2


def test_fha_mip_ltv_above_one_raises() -> None:
    # Loud failure: principal > property_value is invalid input.
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2024, 6, 15),
        loan_type="fha",
    )
    with pytest.raises(ValueError, match=r"LTV.*exceeds 1\.00"):
        compute(
            loan=loan,
            original_property_value=Decimal("350000.00"),
            endorsement_date=date(2024, 6, 15),
        )
