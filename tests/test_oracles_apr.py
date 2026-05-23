"""Independent oracle tests for the APR engine (lib.apr).

Source: CFPB H-24(B) Mortgage Loan Estimate sample (Feb 7, 2014). See
tests/fixtures/oracles/cfpb-le/h24b_fixed_rate_162k_3_875.json for the
captured inputs and the disclosed APR (4.274%).

Tolerance per Reg Z §1026.22(a)(2): +/- 0.125 percentage points
(Decimal("0.00125") as a fractional rate) for regular transactions.
The engine ships its own internal convergence tolerance of Decimal("0.00001")
which is 125x tighter; the +/- 0.125% here is the REGULATORY tolerance the
oracle is measured against, not the engine's internal tolerance.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lib.apr import (
    AdvanceScheduleEntry,
    APRRequest,
    PaymentScheduleEntry,
    solve_apr,
)
from lib.models import Loan

if TYPE_CHECKING:
    from collections.abc import Callable


REG_Z_REGULAR_TOLERANCE = Decimal("0.00125")
"""12 CFR §1026.22(a)(2): regular-transaction APR tolerance is 1/8 percentage
point = 0.00125 as a fractional rate."""


def _request_from_oracle(fixture: dict[str, Any]) -> APRRequest:
    """Reconstruct an APRRequest from an oracle fixture dict."""
    inp = fixture["inputs"]
    loan_d = inp["loan"]
    loan = Loan(
        principal=Decimal(loan_d["principal"]),
        annual_rate=Decimal(loan_d["annual_rate"]),
        term_months=loan_d["term_months"],
        origination_date=date.fromisoformat(loan_d["origination_date"]),
        loan_type=loan_d.get("loan_type", "fixed"),
    )
    return APRRequest(
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
        day_count=inp.get("day_count", "30/360"),
        unit_periods_per_year=inp.get("unit_periods_per_year", 12),
        odd_first_period_days=inp.get("odd_first_period_days", 0),
    )


def test_cfpb_h24b_fixed_rate_162k_apr_within_reg_z_tolerance(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """CFPB H-24(B) Loan Estimate: $162k @ 3.875%/30yr -> disclosed APR 4.274%.

    Engine APR must agree with the disclosed APR within +/- 0.125 percentage
    points per 12 CFR §1026.22(a)(2). This is the SINGLE highest-credibility
    independent APR oracle this project has access to without standing up
    HMDA Platform or running FFIEC APRWIN on a Windows VM. A failure here
    is exactly the systematic-bug class that engine-emitted golden fixtures
    cannot detect.
    """
    fx = oracle_fixture("cfpb-le/h24b_fixed_rate_162k_3_875")
    req = _request_from_oracle(fx)
    response = solve_apr(req)

    disclosed = Decimal(fx["expected"]["disclosed_apr"])
    diff = abs(response.estimated_apr - disclosed)

    assert diff <= REG_Z_REGULAR_TOLERANCE, (
        f"CFPB H-24(B) oracle: engine APR {response.estimated_apr} "
        f"deviates from disclosed APR {disclosed} by {diff} — exceeds Reg Z "
        f"regular-transaction tolerance {REG_Z_REGULAR_TOLERANCE} "
        f"(12 CFR §1026.22(a)(2)). This is a systematic engine bug or a "
        f"finance-charges miscoding — see fixture _meta for capture details."
    )
