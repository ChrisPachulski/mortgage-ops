"""Independent oracle tests for the ARM engine (lib.arm).

Sources captured 2026-05-23:
  - mortgagecalculator.org 5/1 ARM article worked example
    (substituted for Bankrate's JS-rendered calculator; see
    tests/fixtures/oracles/README.md).

Asserts engine matches published year-1 P&I and end-of-year-5 balance
within tolerance documented in the fixture _meta.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lib.amortize import build_schedule
from lib.models import Loan

if TYPE_CHECKING:
    from collections.abc import Callable


def test_mortgagecalculator_org_5_1_arm_year1_pi_and_year5_balance(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """mortgagecalculator.org 5/1 ARM: $240k / 3.37% / 30yr.

    Engine year-1 P&I must equal $1,060.37 exactly (cent equality —
    `numpy_financial.pmt` wrap is deterministic). Engine year-5 ending
    balance is asserted within $1 because the oracle's balance numbers
    derive from a rounded payment value; the cent-of-drift documented
    in the fixture is consistent with that rounding.

    Year-1 P&I match is the harder test: a systematic bug in the
    `numpy_financial.pmt` wrap or the period-rate conversion would
    fail this immediately.
    """
    fx = oracle_fixture("bankrate-html/mortgagecalculator_org_5_1_arm")
    inp = fx["inputs"]["loan"]
    loan = Loan(
        principal=Decimal(inp["principal"]),
        annual_rate=Decimal(inp["annual_rate"]),
        term_months=inp["term_months"],
        loan_type=inp.get("loan_type", "fixed"),
    )
    schedule = build_schedule(loan)

    expected_y1_pi = Decimal(fx["expected"]["year1_monthly_pi"])
    assert schedule.monthly_pi == expected_y1_pi, (
        f"mortgagecalculator.org 5/1 ARM oracle: engine year-1 P&I "
        f"{schedule.monthly_pi} != oracle {expected_y1_pi}. "
        f"Indicates a level-payment PMT regression — see fixture _meta."
    )

    expected_y5_balance = Decimal(fx["expected"]["year5_ending_balance_approx"])
    balance_tol = Decimal(fx["expected"]["year5_balance_tolerance"])
    actual_y5_balance = schedule.payments[59].balance
    drift = abs(actual_y5_balance - expected_y5_balance)
    assert drift <= balance_tol, (
        f"Engine year-5 ending balance {actual_y5_balance} deviates from "
        f"oracle {expected_y5_balance} by {drift}, exceeding documented "
        f"tolerance {balance_tol}. This would indicate an amortization "
        f"drift bug — engine-emitted goldens cannot catch this."
    )
