"""Optional MortgageModeler comparative oracle tests.

MortgageModeler overlaps with this repo's commodity mortgage math surface:
fixed amortization, ARM paths, refinance breakeven, APR-ish analytics, HELOC,
and fee modeling. It is intentionally NOT a runtime dependency. These tests
skip unless the package is installed in the test environment, then compare only
the conventions that are compatible enough to provide signal.

Source checked 2026-05-24:
  - PyPI package `mortgagemodeler==0.4.3`
  - GitHub repo `arunkpe/mortgagemodeler`

Important convention boundary:
  MortgageModeler's `effective_apr()` returns an effective annual yield
  percentage via IRR compounding. `lib.apr.solve_apr()` returns the Reg Z-style
  estimated APR fractional rate. The APR test below is therefore a convention
  guard, not a parity assertion.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import os
import tempfile
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from lib.amortize import build_schedule
from lib.apr import AdvanceScheduleEntry, APRRequest, PaymentScheduleEntry, solve_apr
from lib.arm import ARMRequest, ARMTerms, build_arm_schedule
from lib.models import Loan as MortgageOpsLoan
from lib.refinance import RateAndTermRefiRequest, evaluate_rate_and_term

CENT = Decimal("0.01")
RATE_PCT_QUANTUM = Decimal("0.0001")


def _load_mortgagemodeler() -> tuple[Any, Any, Any, Any]:
    """Load MortgageModeler lazily so the default suite has no optional dep."""
    os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
    try:
        module = importlib.import_module("mortgagemodeler")
        breakeven_module = importlib.import_module("mortgagemodeler.utils.breakeven")
        apr_module = importlib.import_module("mortgagemodeler.utils.effective_apr")
    except Exception as exc:
        pytest.skip(f"optional MortgageModeler oracle unavailable: {type(exc).__name__}: {exc}")

    return (
        module.Loan,
        module.LoanAmortizer,
        breakeven_module.breakeven_analysis,
        apr_module.effective_apr,
    )


def _mm_dataframe(amortizer_cls: Any, loan: Any) -> Any:
    """Build a MortgageModeler schedule while suppressing optional import noise."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        return amortizer_cls(loan).to_dataframe()


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(CENT)


def _percent(value: object) -> Decimal:
    return Decimal(str(value)).quantize(RATE_PCT_QUANTUM)


def _assert_money_close(actual: Decimal, expected: Decimal, tolerance: Decimal = CENT) -> None:
    assert abs(actual - expected) <= tolerance, (
        f"{actual} differs from expected {expected} by more than {tolerance}"
    )


def test_mortgagemodeler_fixed_amortization_matches_monthly_pi_and_first_row() -> None:
    """Fixed-rate monthly amortization conventions match to the cent."""
    mm_loan_cls, mm_amortizer_cls, _, _ = _load_mortgagemodeler()

    mm_loan = mm_loan_cls(
        principal=200000,
        rate=6.5,
        term_months=360,
        origination_date=date(2026, 1, 1),
    )
    mm_df = _mm_dataframe(mm_amortizer_cls, mm_loan)

    ours = build_schedule(
        MortgageOpsLoan(
            principal=Decimal("200000.00"),
            annual_rate=Decimal("0.065000"),
            term_months=360,
            origination_date=date(2026, 1, 1),
        )
    )
    first = mm_df.iloc[0]

    assert _money(first["Payment"]) == ours.monthly_pi
    assert _money(first["Interest"]) == ours.payments[0].interest
    assert _money(first["Principal"]) == ours.payments[0].principal
    assert _money(first["Ending Balance"]) == ours.payments[0].balance


def test_mortgagemodeler_arm_path_matches_no_cap_first_reset_with_cent_tolerance() -> None:
    """ARM reset payment is close when no cap binds and the index path is aligned."""
    mm_loan_cls, mm_amortizer_cls, _, _ = _load_mortgagemodeler()

    mm_arm = mm_loan_cls.from_arm(
        principal=200000,
        term=360,
        arm_type="5/1",
        index="SOFR",
        margin=2.5,
        origination_date=date(2026, 1, 1),
        rate=4.0,
        caps=(2, 1, 5),
        floors=(0, 0, 0),
        forward_curve={"2031-02-01": 2.5},
    )
    mm_df = _mm_dataframe(mm_amortizer_cls, mm_arm)

    ours = build_arm_schedule(
        ARMRequest(
            loan=MortgageOpsLoan(
                principal=Decimal("200000.00"),
                annual_rate=Decimal("0.040000"),
                term_months=360,
                origination_date=date(2026, 1, 1),
                loan_type="arm",
            ),
            arm_terms=ARMTerms(
                initial_period_months=60,
                reset_period_months=12,
                initial_cap_bps=200,
                periodic_cap_bps=100,
                lifetime_cap_bps=500,
                floor_rate=Decimal("0.000000"),
                margin_bps=250,
                index_series_id="SOFR",
            ),
            assumed_index_rate=Decimal("0.025000"),
        )
    )
    month_60 = mm_df.iloc[59]
    month_61 = mm_df.iloc[60]

    _assert_money_close(_money(month_60["Ending Balance"]), ours.payments[59].balance)
    _assert_money_close(_money(month_61["Payment"]), ours.payments[60].payment)
    assert _percent(month_61["Effective Rate"]) == Decimal("5.0000")
    assert ours.reset_events[0].applied_cap == "none"


def test_mortgagemodeler_refi_breakeven_matches_rate_and_term_simple_case() -> None:
    """Rate-and-term refi breakeven agrees for a simple positive-savings case."""
    mm_loan_cls, mm_amortizer_cls, mm_breakeven, _ = _load_mortgagemodeler()

    old_df = _mm_dataframe(
        mm_amortizer_cls,
        mm_loan_cls(
            principal=400000,
            rate=7.0,
            term_months=360,
            origination_date=date(2026, 1, 1),
        ),
    )
    new_df = _mm_dataframe(
        mm_amortizer_cls,
        mm_loan_cls(
            principal=400000,
            rate=6.0,
            term_months=360,
            origination_date=date(2026, 1, 1),
        ),
    )
    mm_result = mm_breakeven(new_df, old_df, refi_costs=5000)

    ours = evaluate_rate_and_term(
        RateAndTermRefiRequest(
            old_loan_balance=Decimal("400000.00"),
            old_annual_rate=Decimal("0.070000"),
            old_remaining_months=360,
            new_annual_rate=Decimal("0.060000"),
            new_term_months=360,
            closing_costs=Decimal("5000.00"),
            discount_rate_annual=Decimal("0.000000"),
            analysis_horizon_months=360,
        )
    )

    assert _money(old_df.iloc[0]["Payment"]) == ours.old_monthly_pi
    assert _money(new_df.iloc[0]["Payment"]) == ours.new_monthly_pi
    assert mm_result["breakeven_month"] == ours.breakeven.simple_months
    assert ours.breakeven.simple_status == "ok"


def test_mortgagemodeler_apr_helper_is_effective_yield_not_reg_z_parity() -> None:
    """MortgageModeler's APR helper is not a Reg Z parity oracle."""
    _, _, _, mm_effective_apr = _load_mortgagemodeler()

    loan = MortgageOpsLoan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2026, 1, 1),
    )
    schedule = build_schedule(loan)
    ours = solve_apr(
        APRRequest(
            loan=loan,
            finance_charges=Decimal("0.00"),
            advance_schedule=[
                AdvanceScheduleEntry(
                    unit_period_offset=0,
                    amount=Decimal("400000.00"),
                )
            ],
            payment_schedule=[
                PaymentScheduleEntry(
                    starting_unit_period=1,
                    periods=360,
                    amount=schedule.monthly_pi,
                )
            ],
        )
    )
    mm_apr_percent = Decimal(str(mm_effective_apr(400000, 6.5, 360, points=0.0, fees=0.0)))

    assert ours.estimated_apr == Decimal("0.065000")
    assert mm_apr_percent > Decimal("6.5")
    assert mm_apr_percent == Decimal("6.697")
