"""Phase 14 property-analysis pipeline — Wave 1 tests (ANLZ-01, ANLZ-02).

Wave 1 (Plan 14-02) covers ONLY matrix-shape, cell-numeric, eligibility-gating,
and basic composition invariants. Stress / refi / points / tax / verdict
tests are stubbed and deferred to Plans 14-03..14-06.

Per CLAUDE.md money discipline: exact Decimal equality only; never
``pytest.approx`` or ``assertAlmostEqual``. Per RESEARCH Pitfall 2:
every Decimal in this file is constructed from a string literal.

Test taxonomy:
  - Wave-0 (Task 1 of Plan 14-02): model + module-constant contract tests.
  - Wave-1 (Task 2 of Plan 14-02): per-cell composition + matrix builder
    + iteration-2 fixes (B-2 VA-construction, B-3 PropertyListing
    defaults, B-4 ProvenancedMoney unwrap, W-3 VA financed funding fee).
  - Wave-2+ (Plan 14-03..14-06): stress / refi / points / tax / verdict
    / golden fixtures — stubbed below with ``pytest.skip``.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from lib.property_analysis import (
    _CONV_5_1_ARM_TERMS,
    _CONV_PMI_ANNUAL_RATE,
    DOWN_PAYMENT_PCTS,
    PROGRAMS_BASE,
    AnalysisReport,
    DownPaymentMatrix,
    PointsBlock,
    PointsRow,
    ProgramResult,
    RefiBlock,
    RefiRow,
    StressBlock,
    StressRow,
    TaxBlock,
    Verdict,
    VerdictReason,
    analyze,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Wave-0 — model + module-constant contract tests (Task 1 deliverable)
# ---------------------------------------------------------------------------


def test_models_importable() -> None:
    """All 12 output models + 5 module constants + analyze stub import."""
    assert ProgramResult is not None
    assert DownPaymentMatrix is not None
    assert StressRow is not None
    assert StressBlock is not None
    assert RefiRow is not None
    assert RefiBlock is not None
    assert PointsRow is not None
    assert PointsBlock is not None
    assert TaxBlock is not None
    assert Verdict is not None
    assert VerdictReason is not None
    assert AnalysisReport is not None
    assert analyze is not None


def test_module_constants() -> None:
    """DOWN_PAYMENT_PCTS / PROGRAMS_BASE / _CONV_PMI_ANNUAL_RATE / _CONV_5_1_ARM_TERMS values exact."""
    assert [
        Decimal("0.03"),
        Decimal("0.05"),
        Decimal("0.10"),
        Decimal("0.15"),
        Decimal("0.20"),
        Decimal("0.25"),
    ] == DOWN_PAYMENT_PCTS
    assert PROGRAMS_BASE == ["Conv30", "Conv15", "FHA30"]
    assert Decimal("0.0075") == _CONV_PMI_ANNUAL_RATE
    assert _CONV_5_1_ARM_TERMS.initial_period_months == 60
    assert _CONV_5_1_ARM_TERMS.reset_period_months == 12
    assert _CONV_5_1_ARM_TERMS.initial_cap_bps == 500
    assert _CONV_5_1_ARM_TERMS.periodic_cap_bps == 200
    assert _CONV_5_1_ARM_TERMS.lifetime_cap_bps == 500
    assert _CONV_5_1_ARM_TERMS.floor_rate == Decimal("0.025")
    assert _CONV_5_1_ARM_TERMS.margin_bps == 250
    assert _CONV_5_1_ARM_TERMS.index_series_id == "MORTGAGE30US"


def test_analyze_stub_raises_not_implemented_with_plan_14_05_reference() -> None:
    """analyze() raises NotImplementedError; message cites Plan 14-05."""
    with pytest.raises(NotImplementedError) as exc:
        analyze()
    assert "Plan 14-05" in str(exc.value)


def test_program_result_validates_with_clean_inputs() -> None:
    """ProgramResult accepts a clean Conv30-at-20%-DP inputs (Behavior 7)."""
    pr = ProgramResult(
        program="Conv30",
        down_payment_pct=Decimal("0.200000"),
        loan_amount=Decimal("500000.00"),
        monthly_pi=Decimal("3160.34"),
        monthly_tax=Decimal("500.00"),
        monthly_insurance=Decimal("100.00"),
        monthly_hoa=Decimal("0.00"),
        monthly_mi=Decimal("0.00"),
        piti=Decimal("3760.34"),
        cash_to_close=Decimal("125000.00"),
        dti_back=Decimal("0.350000"),
        ltv=Decimal("0.800000"),
        eligible=True,
    )
    assert pr.program == "Conv30"
    assert pr.eligible is True
    assert pr.blocker_reasons == []
    assert pr.eligible_reasons == []
    assert pr.closing_costs_estimated is True


def test_program_result_rejects_unknown_program_literal() -> None:
    """ProgramResult enforces program Literal (Behavior 8)."""
    with pytest.raises(ValidationError):
        ProgramResult(
            program="not_a_program",  # type: ignore[arg-type]
            down_payment_pct=Decimal("0.200000"),
            loan_amount=Decimal("500000.00"),
            monthly_pi=Decimal("3160.34"),
            monthly_tax=Decimal("500.00"),
            monthly_insurance=Decimal("100.00"),
            monthly_hoa=Decimal("0.00"),
            monthly_mi=Decimal("0.00"),
            piti=Decimal("3760.34"),
            cash_to_close=Decimal("125000.00"),
            dti_back=Decimal("0.350000"),
            ltv=Decimal("0.800000"),
            eligible=True,
        )


def test_refi_row_accepts_signed_decimal_savings() -> None:
    """RefiRow.monthly_savings and .npv_60mo are signed Decimals (Pitfall 3)."""
    row = RefiRow(
        program="Conv30",
        target_rate=Decimal("0.055000"),
        scenario_label="minus_100bps",
        monthly_savings=Decimal("-150.00"),
        npv_60mo=Decimal("-2500.00"),
    )
    assert row.monthly_savings == Decimal("-150.00")
    assert row.npv_60mo == Decimal("-2500.00")


def test_verdict_reason_accepts_string_computed_value() -> None:
    """VerdictReason.computed_value is a string (polymorphic numeric)."""
    vr = VerdictReason(
        predicate_code="DTI-CAP-CONVENTIONAL",
        computed_value="0.510000",
        program="Conv30",
        dp_pct=Decimal("0.200000"),
    )
    assert vr.predicate_code == "DTI-CAP-CONVENTIONAL"
    assert vr.computed_value == "0.510000"


def test_verdict_rejects_unknown_level_literal() -> None:
    """Verdict.level enforces Literal["GO", "WATCH", "NO_GO"] (Behavior 11)."""
    Verdict(level="GO", headline_reason="x", reasons=[])  # accepted
    with pytest.raises(ValidationError):
        Verdict(level="MAYBE", headline_reason="x", reasons=[])  # type: ignore[arg-type]


def test_program_result_rejects_float_on_money_field() -> None:
    """strict=True rejects Python float on Money/Rate fields (Pitfall 2)."""
    with pytest.raises(ValidationError):
        ProgramResult(
            program="Conv30",
            down_payment_pct=0.2,  # type: ignore[arg-type]
            loan_amount=Decimal("500000.00"),
            monthly_pi=Decimal("3160.34"),
            monthly_tax=Decimal("500.00"),
            monthly_insurance=Decimal("100.00"),
            monthly_hoa=Decimal("0.00"),
            monthly_mi=Decimal("0.00"),
            piti=Decimal("3760.34"),
            cash_to_close=Decimal("125000.00"),
            dti_back=Decimal("0.350000"),
            ltv=Decimal("0.800000"),
            eligible=True,
        )
