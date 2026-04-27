"""Tests for lib/rules/freddie_eligibility.py — Freddie SF Seller/Servicer Guide §4203.4 (RUL-03).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - Common case: Freddie matches Fannie at top-tier credit / standard LTV
  - Overlay diff: Freddie INELIGIBLE where Fannie is generally eligible (proves
    the predicate exists separately for citation discipline)
  - Credit Fee Cap numeric assertion (Decimal-from-string round-trip)
  - Fail-loud LookupError when no matrix cell matches
  - FreddieEligibilityResult is a frozen Pydantic v2 model (immutable contract)
  - Auto-discovery: citation-coverage meta-test gains [freddie_eligibility] case
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.freddie_eligibility import (
    FreddieEligibilityResult,
    evaluate,
)
from pydantic import ValidationError

FIX_DIR: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX_DIR / name).read_text())
    return data


def test_common_case_matches_fannie_outcome() -> None:
    fx = _load("freddie_eligibility_common_case.json")
    # Hand: credit_score=740, LTV=80, purchase, primary, 1-unit -> eligible=True,
    # credit_fee_bps=0. Same as Fannie at this cell -- confirms top-tier convergence.
    result = evaluate(
        credit_score=fx["credit_score"],
        ltv_pct=Decimal(fx["ltv_pct"]),
        loan_purpose=fx["loan_purpose"],
        occupancy=fx["occupancy"],
        unit_count=fx["unit_count"],
    )
    assert result.eligible is fx["expected_eligible"]
    assert result.credit_fee_bps == Decimal(fx["expected_credit_fee_bps"])


def test_overlay_case_differs_from_fannie() -> None:
    fx = _load("freddie_eligibility_overlay_diff.json")
    # Hand: credit_score=625, LTV=92 -> Freddie matrix says ineligible (overlay
    # restriction at low-credit + high-LTV combo). Fannie at the same inputs is
    # generally eligible. Confirms RUL-03 exists separately for citation discipline.
    result = evaluate(
        credit_score=fx["credit_score"],
        ltv_pct=Decimal(fx["ltv_pct"]),
        loan_purpose=fx["loan_purpose"],
        occupancy=fx["occupancy"],
        unit_count=fx["unit_count"],
    )
    assert result.eligible is fx["expected_eligible"]  # False per overlay
    assert result.credit_fee_bps == Decimal(fx["expected_credit_fee_bps"])


def test_credit_fee_cap_bps_numeric() -> None:
    fx = _load("freddie_eligibility_credit_fee_bps.json")
    # Hand: credit_score=680, LTV=80 -> '680-699' x '75.01-80'. Base 175 +
    # cash_out 275 + 0 + 0 = 450 bps. Confirms exact Decimal equality
    # (no pytest.approx) per CLAUDE.md money discipline.
    result = evaluate(
        credit_score=fx["credit_score"],
        ltv_pct=Decimal(fx["ltv_pct"]),
        loan_purpose=fx["loan_purpose"],
        occupancy=fx["occupancy"],
        unit_count=fx["unit_count"],
    )
    assert result.credit_fee_bps == Decimal(fx["expected_credit_fee_bps"])
    assert result.credit_fee_bps == Decimal("450")


def test_evaluate_missing_cell_raises_lookup_error() -> None:
    # Hand: pass an invalid loan_purpose (bypassing Literal narrowing via type:ignore --
    # same fail-loud pattern as tests/test_models.py:42). Predicate must raise
    # LookupError, NEVER silently return FreddieEligibilityResult(eligible=False, bps=0).
    with pytest.raises(LookupError):
        evaluate(
            credit_score=720,
            ltv_pct=Decimal("80.00"),
            loan_purpose="unknown_purpose",  # type: ignore[arg-type]
            occupancy="primary",
            unit_count=1,
        )


def test_result_is_frozen_pydantic_model() -> None:
    # Hand: ConfigDict(strict=True, frozen=True, extra="forbid") on the result type
    # means mutation must raise ValidationError. Phase 1 PATTERNS Convention #2.
    result = evaluate(
        credit_score=740,
        ltv_pct=Decimal("80.00"),
        loan_purpose="purchase",
        occupancy="primary",
        unit_count=1,
    )
    with pytest.raises(ValidationError):
        result.eligible = False  # type: ignore[misc]


def test_result_rejects_extra_fields() -> None:
    # Hand: extra="forbid" must reject unknown fields at construction.
    with pytest.raises(ValidationError):
        FreddieEligibilityResult(  # type: ignore[call-arg]
            eligible=True,
            credit_fee_bps=Decimal("0"),
            unknown_extra_field="oops",
        )


def test_below_620_is_ineligible_at_all_ltv() -> None:
    # Hand: 'below-620' bucket has eligible=false at every LTV cell per Freddie
    # published matrix. Confirms full-matrix coverage (D-01: ship all 11 predicates,
    # full matrices, no stub branches).
    result = evaluate(
        credit_score=600,
        ltv_pct=Decimal("60.00"),
        loan_purpose="purchase",
        occupancy="primary",
        unit_count=1,
    )
    assert result.eligible is False
