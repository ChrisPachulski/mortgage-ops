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
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.freddie_eligibility import (
    FreddieEligibilityResult,
    _ltv_bucket,
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


def test_ltv_bucket_rejects_more_than_two_decimal_places() -> None:
    # Regression for WR-03 (02-REVIEW.md): the LTV bucket schema is
    # two-decimal-precision (60.00 / 60.01-70.00). A 4-decimal LTV like
    # Decimal("60.0056") falls in the open fractional gap and matches no
    # bucket. Post-fix, _ltv_bucket fails fast with an explicit ValueError.
    with pytest.raises(ValueError, match="must be quantized to <= 2 decimal places"):
        _ltv_bucket(Decimal("60.0056"))


def test_ltv_bucket_accepts_exactly_two_decimal_places() -> None:
    # Regression for WR-03: ensure the >2-decimal guard does not over-trigger.
    assert _ltv_bucket(Decimal("60.00")) == "0-60"


def test_freddie_eligibility_yaml_every_eligible_field_is_python_bool() -> None:
    # Regression for WR-04 (02-REVIEW.md): a future YAML edit that quotes
    # the eligibility flag (e.g., 'false' instead of unquoted false) would
    # be silently truthy under bool(). Pin the YAML's actual cell types so
    # such an edit fails this schema test.
    import yaml as _yaml

    yaml_path = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "reference"
        / "freddie-eligibility-matrix.yml"
    )
    raw = _yaml.safe_load(yaml_path.read_text())
    for cs_bucket, by_ltv in raw["eligibility"].items():
        for ltv_bucket, cell in by_ltv.items():
            value = cell["eligible"]
            assert isinstance(value, bool), (
                f"freddie-eligibility-matrix.yml eligibility[{cs_bucket!r}]"
                f"[{ltv_bucket!r}].eligible must be a YAML bool (true/false "
                f"unquoted); got {type(value).__name__} with value {value!r}"
            )


def test_freddie_evaluate_raises_typeerror_on_quoted_eligibility_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression for WR-04 (02-REVIEW.md): if a future YAML accidentally
    # quoted the eligibility flag, the predicate must fail loud rather than
    # silently flip every 'ineligible' cell to 'eligible' via bool('false')==True.

    from lib.rules._loader import load_reference

    # Build a minimal but schema-valid Freddie YAML with a QUOTED 'false' flag.
    today = date.today().isoformat()
    fake_yaml = (
        f"source: 'https://example.test/'\n"
        f"effective: {today}\n"
        f"credit_score_buckets:\n"
        f"  - {{id: '740-or-better', min: '740', max: '850'}}\n"
        f"ltv_buckets:\n"
        f"  - {{id: '0-60', min: '0', max: '60.00'}}\n"
        f"eligibility:\n"
        f"  '740-or-better':\n"
        f"    '0-60':\n"
        f"      eligible: 'false'   # QUOTED — pre-fix this would have been truthy\n"
        f"      credit_fee_bps: '0'\n"
        f"loan_purpose_addons:\n"
        f"  purchase: '0'\n"
        f"occupancy_addons:\n"
        f"  primary: '0'\n"
        f"unit_count_addons:\n"
        f"  '1': '0'\n"
    )
    fake_path = tmp_path / "freddie-eligibility-matrix.yml"
    fake_path.write_text(fake_yaml)
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()

    with pytest.raises(TypeError, match="must be a YAML bool"):
        evaluate(
            credit_score=750,
            ltv_pct=Decimal("60.00"),
            loan_purpose="purchase",
            occupancy="primary",
            unit_count=1,
        )

    # Reset the cache so other tests in this session see the real YAML.
    load_reference.cache_clear()
