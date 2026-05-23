"""Independent oracle tests for the discount-points breakeven engine (lib.points).

Source: mortgagecalculator.org 'Should I Pay Points?' worked example
(substituted for Bankrate's points calculator which returned HTTP 404;
see tests/fixtures/oracles/README.md).

IMPORTANT: The captured oracle's no-points payment value of $993.10 is
documented to be INCORRECT (the correct value is $1,013.37, verified via
three independent computations). This test asserts the engine matches the
CORRECT values; the discrepancy is documented in fixture _meta. The
with-points value of $954.83 IS correct and is asserted.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lib.amortize import build_schedule
from lib.models import Loan
from lib.points import PointsRequestFromLoans, evaluate

if TYPE_CHECKING:
    from collections.abc import Callable


def test_mortgagecalculator_org_points_engine_matches_correct_values(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """mortgagecalculator.org Discount Points Example: $200k / 30yr / 4.5%
    no-points vs $200k / 30yr / 4.0% with 2 points ($4,000).

    Engine assertions:
      - No-points P&I = $1,013.37 (engine + oracle's own calculator + textbook formula)
        — the oracle's article text quotes $993.10, which is wrong; we assert
        the engine matches the CORRECT $1,013.37 value.
      - With-points P&I = $954.83 (engine + oracle article both correct here)
      - Monthly savings = $58.54 (= 1013.37 - 954.83)
      - Simple breakeven = ceil(4000 / 58.54) = 69 months
        — the oracle article's '5 years 9 months' is 69 months, consistent
        with this engine value (even though the article quoted a wrong
        no-points P&I, the breakeven line stayed correct).
    """
    fx = oracle_fixture("bankrate-html/mortgagecalculator_org_should_i_pay_points")
    inp = fx["inputs"]

    no_pts_loan = Loan(
        principal=Decimal(inp["loan_no_points"]["principal"]),
        annual_rate=Decimal(inp["loan_no_points"]["annual_rate"]),
        term_months=inp["loan_no_points"]["term_months"],
    )
    with_pts_loan = Loan(
        principal=Decimal(inp["loan_with_points"]["principal"]),
        annual_rate=Decimal(inp["loan_with_points"]["annual_rate"]),
        term_months=inp["loan_with_points"]["term_months"],
    )

    # Direct P&I check first — the engine should reproduce both legs.
    no_pts_pi = build_schedule(no_pts_loan).monthly_pi
    with_pts_pi = build_schedule(with_pts_loan).monthly_pi

    expected_no_pts = Decimal(fx["expected"]["no_points_monthly_pi"])
    expected_with_pts = Decimal(fx["expected"]["with_points_monthly_pi"])
    assert no_pts_pi == expected_no_pts, (
        f"Engine no-points P&I {no_pts_pi} != oracle CORRECT value "
        f"{expected_no_pts} (oracle article text incorrectly states $993.10; "
        f"see fixture _meta substitution_note)."
    )
    assert with_pts_pi == expected_with_pts, (
        f"Engine with-points P&I {with_pts_pi} != oracle {expected_with_pts}"
    )

    # Now the breakeven via the lib.points engine
    req = PointsRequestFromLoans(
        points_cost=Decimal(inp["points_cost"]),
        loan_with_points=with_pts_loan,
        loan_without_points=no_pts_loan,
        hold_period_months=inp["hold_period_months"],
        discount_rate_annual=Decimal(inp["discount_rate_annual"]),
    )
    resp = evaluate(req)
    expected_savings = Decimal(fx["expected"]["monthly_savings"])
    assert resp.monthly_savings == expected_savings, (
        f"Engine monthly_savings {resp.monthly_savings} != hand-derived "
        f"{expected_savings} (= correct no-pts $1,013.37 - with-pts $954.83)"
    )
    expected_breakeven = fx["expected"]["simple_breakeven_months"]
    assert resp.simple_breakeven_months == expected_breakeven, (
        f"Engine simple_breakeven {resp.simple_breakeven_months} != oracle "
        f"{expected_breakeven} months (= ceil($4,000 / $58.54))."
    )
