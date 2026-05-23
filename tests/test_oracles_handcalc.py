"""Independent hand-calc oracle tests for the four core calc families.

Each fixture under tests/fixtures/oracles/handcalc/ ships a worked
arithmetic derivation in its `derivation:` block, a citation_url to the
formula source, and a reviewer signature (household maintainer /
2026-05-23). The tests load each fixture, run the corresponding engine
entry-point, and assert exact Decimal equality on the final outputs.

These complement the third-party oracles (CFPB LE / CHARM / Bankrate-HTML)
because hand-calc fixtures are derived from first-principles arithmetic
that does NOT touch the engine — so a systematic engine bug cannot shift
both sides of the assertion in lockstep.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lib.amortize import build_schedule
from lib.apr import (
    AdvanceScheduleEntry,
    APRRequest,
    PaymentScheduleEntry,
    solve_apr,
)
from lib.arm import ARMRequest, ARMTerms, build_arm_schedule
from lib.models import Loan
from lib.refinance import RateAndTermRefiRequest, evaluate_rate_and_term

if TYPE_CHECKING:
    from collections.abc import Callable


def test_handcalc_amortize_engine_exact_decimal_match(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Hand-calc: $100k @ 12.000% / 360 months -> PMT $1,028.61, period-1
    interest $1,000.00 (= P*r exactly), period-1 principal $28.61.

    Exact Decimal equality on every output."""
    fx = oracle_fixture("handcalc/amortize")
    inp = fx["inputs"]["loan"]
    loan = Loan(
        principal=Decimal(inp["principal"]),
        annual_rate=Decimal(inp["annual_rate"]),
        term_months=inp["term_months"],
    )
    schedule = build_schedule(loan)
    exp = fx["expected"]

    assert schedule.monthly_pi == Decimal(exp["monthly_pi"])
    p1 = schedule.payments[0]
    assert p1.interest == Decimal(exp["first_period_interest"])
    assert p1.principal == Decimal(exp["first_period_principal"])
    assert p1.balance == Decimal(exp["first_period_balance"])


def test_handcalc_apr_engine_exact_decimal_match(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Hand-calc: zero-finance-charges identity case (APR == nominal rate exactly).

    Algebraic identity: if finance_charges=0 and the cashflows are a level
    annuity, the Reg Z Appendix J unit-period equation reduces to the PMT
    equation, so the unique solver root is i = annual_rate / 12. Engine
    must return APR = 0.120000 exactly."""
    fx = oracle_fixture("handcalc/apr")
    inp = fx["inputs"]
    loan_d = inp["loan"]
    loan = Loan(
        principal=Decimal(loan_d["principal"]),
        annual_rate=Decimal(loan_d["annual_rate"]),
        term_months=loan_d["term_months"],
        origination_date=date.fromisoformat(loan_d["origination_date"]),
    )
    req = APRRequest(
        loan=loan,
        finance_charges=Decimal(inp["finance_charges"]),
        advance_schedule=[
            AdvanceScheduleEntry(
                unit_period_offset=a["unit_period_offset"],
                amount=Decimal(a["amount"]),
            )
            for a in inp["advance_schedule"]
        ],
        payment_schedule=[
            PaymentScheduleEntry(
                starting_unit_period=p["starting_unit_period"],
                periods=p["periods"],
                amount=Decimal(p["amount"]),
            )
            for p in inp["payment_schedule"]
        ],
    )
    response = solve_apr(req)
    assert response.estimated_apr == Decimal(fx["expected"]["estimated_apr"]), (
        f"Hand-calc APR identity case: engine {response.estimated_apr} != "
        f"hand-derived {fx['expected']['estimated_apr']} — algebraic identity "
        f"violation (finance_charges=0 + level annuity should yield APR == r)."
    )


def test_handcalc_arm_engine_exact_decimal_match(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Hand-calc: 5/1 ARM 200k @ 4% initial / 250bps margin / 2.5% assumed
    index -> fully-indexed 5.00% at first reset; no cap binds (rate sits
    strictly inside all ceilings)."""
    fx = oracle_fixture("handcalc/arm")
    loan_d = fx["inputs"]["loan"]
    terms_d = fx["inputs"]["arm_terms"]
    loan = Loan(
        principal=Decimal(loan_d["principal"]),
        annual_rate=Decimal(loan_d["annual_rate"]),
        term_months=loan_d["term_months"],
        origination_date=date.fromisoformat(loan_d["origination_date"]),
        loan_type=loan_d.get("loan_type", "arm"),
    )
    terms = ARMTerms(
        initial_period_months=terms_d["initial_period_months"],
        reset_period_months=terms_d["reset_period_months"],
        initial_cap_bps=terms_d["initial_cap_bps"],
        periodic_cap_bps=terms_d["periodic_cap_bps"],
        lifetime_cap_bps=terms_d["lifetime_cap_bps"],
        floor_rate=Decimal(terms_d["floor_rate"]),
        margin_bps=terms_d["margin_bps"],
        index_series_id=terms_d["index_series_id"],
    )
    req = ARMRequest(
        loan=loan,
        arm_terms=terms,
        assumed_index_rate=Decimal(fx["inputs"]["assumed_index_rate"]),
    )
    schedule = build_arm_schedule(req)
    exp = fx["expected"]

    # Initial-period (year 1 - 5) P&I and rate
    assert schedule.payments[0].payment == Decimal(exp["year1_p_and_i"])
    assert schedule.payments[0].rate_in_effect == Decimal(exp["year1_rate"])

    # End of year-5 balance (just before first reset)
    assert schedule.payments[59].balance == Decimal(exp["year5_ending_balance"])

    # Year-6 P&I + rate after first reset (period 61)
    assert schedule.payments[60].payment == Decimal(exp["year6_p_and_i"])
    assert schedule.payments[60].rate_in_effect == Decimal(exp["year6_rate"])

    # No cap binds
    assert schedule.reset_events[0].applied_cap == exp["first_reset_applied_cap"]


def test_handcalc_refi_npv_engine_exact_decimal_match(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Hand-calc: zero-discount-rate identity case for refi NPV.

    When discount_rate_annual = 0, the NPV collapses to the unweighted sum of
    cashflows. Closing costs = 0, monthly savings $93.00 over 60 months
    -> NPV = 60 * 93.00 = $5,580.00 exactly."""
    fx = oracle_fixture("handcalc/refi_npv")
    inp = fx["inputs"]
    req = RateAndTermRefiRequest(
        old_loan_balance=Decimal(inp["old_loan_balance"]),
        old_annual_rate=Decimal(inp["old_annual_rate"]),
        old_remaining_months=inp["old_remaining_months"],
        new_annual_rate=Decimal(inp["new_annual_rate"]),
        new_term_months=inp["new_term_months"],
        closing_costs=Decimal(inp["closing_costs"]),
        discount_rate_annual=Decimal(inp["discount_rate_annual"]),
    )
    resp = evaluate_rate_and_term(req)
    exp = fx["expected"]

    assert resp.npv == Decimal(exp["npv"]), (
        f"Hand-calc refi NPV identity: engine {resp.npv} != hand-derived "
        f"{exp['npv']} (= 60 mo x $93.00 monthly savings at zero discount)."
    )
    assert resp.old_monthly_pi == Decimal(exp["old_monthly_pi"])
    assert resp.new_monthly_pi == Decimal(exp["new_monthly_pi"])
    assert resp.monthly_savings == Decimal(exp["monthly_savings_signed"])
    assert resp.breakeven.simple_months == exp["simple_breakeven_months"]
    assert resp.breakeven.simple_status == exp["simple_breakeven_status"]
    assert resp.breakeven.npv_months == exp["npv_breakeven_months"]
    assert resp.breakeven.npv_status == exp["npv_breakeven_status"]
