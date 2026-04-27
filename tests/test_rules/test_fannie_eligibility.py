"""Tests for lib/rules/fannie_eligibility.py — Fannie LLPA Matrix §B5-1 (RUL-02).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - Pitfall 6: credit-score bucket boundaries at 700, 719, 720, 739, 740
    (independent unit-tests of _credit_score_bucket helper)
  - Full-stack LLPA round-trip at each boundary (credit_score -> bucket -> bps)
  - Cash-out refi loan_purpose add-on (composition: base + addon)
  - Fail-loud LookupError when no matrix cell matches
  - Auto-discovery: citation-coverage meta-test gains [fannie_eligibility] case
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.fannie_eligibility import (
    _credit_score_bucket,
    _ltv_bucket,
    compute_llpa,
)

FIX_DIR: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX_DIR / name).read_text())
    return data


# Pitfall 6: credit-score bucket boundary unit-tests (independent of LLPA lookup).


def test_credit_score_bucket_700_lower_boundary() -> None:
    # Hand: 700 is the lower bound of '700-719' bucket (LOW-INCLUSIVE).
    assert _credit_score_bucket(700) == "700-719"


def test_credit_score_bucket_719_upper_boundary() -> None:
    # Hand: 719 stays in '700-719' (HIGH-INCLUSIVE); does NOT spill into 720-739.
    assert _credit_score_bucket(719) == "700-719"


def test_credit_score_bucket_720_lower_boundary_load_bearing() -> None:
    # Hand: 720 is the lower bound of '720-739' (LOW-INCLUSIVE).
    # This is THE Pitfall 6 test: if 720 accidentally maps to '700-719',
    # customer is overcharged. LOAD-BEARING.
    assert _credit_score_bucket(720) == "720-739"


def test_credit_score_bucket_739_upper_boundary() -> None:
    # Hand: 739 stays in '720-739' (HIGH-INCLUSIVE); does NOT spill into 740-759.
    assert _credit_score_bucket(739) == "720-739"


def test_credit_score_bucket_740_lower_boundary() -> None:
    # Hand: 740 is the lower bound of '740-759-or-better'.
    assert _credit_score_bucket(740) == "740-759-or-better"


# LTV bucket boundary unit-tests (HIGH-INCLUSIVE per YAML).


def test_ltv_bucket_75_belongs_to_lower_bucket() -> None:
    # Hand: 75.00 is the upper bound of '70.01-75' (HIGH-INCLUSIVE).
    assert _ltv_bucket(Decimal("75.00")) == "70.01-75"


def test_ltv_bucket_75_01_belongs_to_higher_bucket() -> None:
    # Hand: 75.01 is the lower bound of '75.01-80'.
    assert _ltv_bucket(Decimal("75.01")) == "75.01-80"


def test_ltv_bucket_80_belongs_to_75_01_to_80() -> None:
    # Hand: 80.00 is the upper bound of '75.01-80' (HIGH-INCLUSIVE).
    assert _ltv_bucket(Decimal("80.00")) == "75.01-80"


# Full-stack LLPA round-trip tests at each Pitfall 6 boundary.


@pytest.mark.parametrize(
    "fixture_name",
    [
        "fannie_eligibility_credit_score_700.json",
        "fannie_eligibility_credit_score_719.json",
        "fannie_eligibility_credit_score_720.json",
        "fannie_eligibility_credit_score_739.json",
        "fannie_eligibility_credit_score_740.json",
    ],
)
def test_compute_llpa_at_credit_score_boundary(fixture_name: str) -> None:
    fx = _load(fixture_name)
    result = compute_llpa(
        credit_score=fx["credit_score"],
        ltv_pct=Decimal(fx["ltv_pct"]),
        loan_purpose=fx["loan_purpose"],
        occupancy=fx["occupancy"],
        unit_count=fx["unit_count"],
    )
    # Hand: see fixture comment for derivation.
    assert result == Decimal(fx["expected_llpa_bps"])


def test_compute_llpa_cash_out_refi_addon() -> None:
    # Hand: cash_out_refi addon at LTV=80, credit=720 = base 50 + addon 275 = 325 bps.
    # Same inputs with loan_purpose="purchase" yield base 50 + 0 = 50 bps.
    fx = _load("fannie_eligibility_cash_out_refi.json")
    cash_out = compute_llpa(
        credit_score=fx["credit_score"],
        ltv_pct=Decimal(fx["ltv_pct"]),
        loan_purpose="cash_out_refi",
        occupancy=fx["occupancy"],
        unit_count=fx["unit_count"],
    )
    purchase = compute_llpa(
        credit_score=fx["credit_score"],
        ltv_pct=Decimal(fx["ltv_pct"]),
        loan_purpose="purchase",
        occupancy=fx["occupancy"],
        unit_count=fx["unit_count"],
    )
    assert cash_out == Decimal(fx["expected_llpa_bps"])
    assert cash_out > purchase  # cash-out is strictly more expensive at this cell.


def test_compute_llpa_below_620_credit_high_ltv() -> None:
    # Hand: credit_score=550 -> 'below-620'; LTV=95 -> '90.01-95'. Base 325 + 0 + 0 + 0 = 325 bps.
    # Confirms the worst-case cell is reachable (no NotImplementedError per D-04).
    result = compute_llpa(
        credit_score=550,
        ltv_pct=Decimal("95.00"),
        loan_purpose="purchase",
        occupancy="primary",
        unit_count=1,
    )
    assert result == Decimal("325")


def test_compute_llpa_missing_cell_raises_lookup_error_via_unknown_purpose() -> None:
    # Hand: pass an invalid loan_purpose at runtime (bypassing Literal narrowing
    # via type:ignore — same fail-loud pattern as tests/test_models.py:42).
    # Predicate must raise LookupError, NEVER silently return Decimal("0").
    with pytest.raises(LookupError):
        compute_llpa(
            credit_score=720,
            ltv_pct=Decimal("80.00"),
            loan_purpose="unknown_purpose",  # type: ignore[arg-type]
            occupancy="primary",
            unit_count=1,
        )


def test_credit_score_300_is_in_below_620() -> None:
    # Hand: 300 is the floor of the 'below-620' bucket (matches Borrower.Field(ge=300)).
    assert _credit_score_bucket(300) == "below-620"


def test_credit_score_850_is_in_top_bucket() -> None:
    # Hand: 850 is the ceiling of the '740-759-or-better' bucket (matches Borrower.Field(le=850)).
    assert _credit_score_bucket(850) == "740-759-or-better"
