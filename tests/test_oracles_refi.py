"""Independent oracle tests for the refi-NPV engine (lib.refinance).

Source: mortgagecalculator.org 'Mortgage Refinance Breakeven Calculator'
Example A (substituted for Bankrate/NerdWallet's JS-only calculators; see
tests/fixtures/oracles/README.md).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lib.refinance import RateAndTermRefiRequest, evaluate_rate_and_term

if TYPE_CHECKING:
    from collections.abc import Callable


def test_mortgagecalculator_org_refi_example_a_engine_matches_pi_and_savings(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """mortgagecalculator.org Refinance Example A.

    Inputs: old $200k @ 5%/240mo remaining, new 15yr @ 3.25%, $6k closing.

    Engine must reproduce the oracle's:
      - old_pi = $1,319.91 (exact)
      - new_pi = $1,405.34 (exact)
      - signed monthly savings = -$85.43 (= old - new; payment INCREASES)
      - simple_breakeven_status = 'no_savings' (engine doctrine: no payment-savings
        breakeven exists when new_pi > old_pi)

    The oracle ALSO claims a 'Months to Breakeven = 21' figure, but that
    appears to be a non-standard interest-payoff breakeven (cumulative
    interest-savings vs closing cost), NOT a cashflow-savings breakeven.
    We intentionally do NOT assert that 21-month figure; see fixture _meta.
    """
    fx = oracle_fixture("bankrate-html/mortgagecalculator_org_refinance_breakeven")
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

    expected = fx["expected"]
    assert resp.old_monthly_pi == Decimal(expected["old_monthly_pi"]), (
        f"Engine old_pi {resp.old_monthly_pi} != oracle {expected['old_monthly_pi']}"
    )
    assert resp.new_monthly_pi == Decimal(expected["new_monthly_pi"]), (
        f"Engine new_pi {resp.new_monthly_pi} != oracle {expected['new_monthly_pi']}"
    )
    assert resp.monthly_savings == Decimal(expected["monthly_savings_signed"]), (
        f"Engine monthly_savings {resp.monthly_savings} != oracle "
        f"{expected['monthly_savings_signed']} (signed; refi raises payment "
        f"so savings is negative)"
    )
    assert resp.breakeven.simple_status == expected["simple_breakeven_status"], (
        f"Engine simple_breakeven status {resp.breakeven.simple_status!r} "
        f"!= oracle {expected['simple_breakeven_status']!r}. The oracle's "
        f"separate '21-month' figure measures interest-payoff breakeven, "
        f"not cashflow breakeven — see fixture _meta substitution_note."
    )
