"""Discount-points breakeven engine for Phase 8 (PNTS-01..03 + ROADMAP SC-4).

Two modes:
  from_savings — caller already computed monthly_savings (single Decimal in)
  from_loans   — caller supplies two Loans (with-points + without-points);
                 engine derives monthly_savings via two build_schedule calls.

Wave 1 (this plan, 08-01) ships only the type contract + cross-plan stub.
Wave 3 (Plan 08-03) ships simple_breakeven, npv_breakeven, and the body of
evaluate().

LOCKED DECISION - D-01 (mode discriminator):
  PointsRequest is a Pydantic v2 discriminated union over PointsRequestFromSavings
  (mode='from_savings') and PointsRequestFromLoans (mode='from_loans'). Mirrors
  Phase 4 AffordabilityRequest + Phase 8 StressRequest pattern.

LOCKED DECISION - D-02 (caller-supplied discount_rate; no module default):
  PointsRequest.discount_rate_annual is REQUIRED (Rate). Phase 6 (Refinance NPV)
  will pin the project-wide borrower-perspective convention; Phase 8 punts to
  caller. Single-line additive non-breaking change when Phase 6 lands. Documented
  in references/points-breakeven.md (Plan 08-06). Matches Phase 4 D-12 max_dti
  discipline + Phase 5 D-02 floor_rate discipline (fail-loud-on-implicit-default
  project doctrine). Cross-phase coupling note pinned in 08-RESEARCH §5.5.

LOCKED DECISION - D-03 (None for never-breakeven):
  Both simple_breakeven_months and npv_breakeven_months are int | None. None
  means "never crosses zero within hold_period_months". Negative-savings
  scenarios (rate-up; PNTS-01 edge case) return None for both with a warning
  in PointsResponse.warnings.

LOCKED DECISION - D-04 (decision dispatcher reports BOTH outputs):
  ROADMAP SC-4 verbatim: "reports breakeven months as points_cost / monthly_savings
  AND a parallel NPV-based decision". PointsResponse always carries both
  simple_breakeven_months AND npv_breakeven_months side-by-side; diverge=True
  iff they're not equal (and both non-None). decision = "buy_points" iff
  cum_npv(hold_period_months) >= 0; "skip_points" otherwise.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal, localcontext
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from lib.amortize import build_schedule
from lib.models import (  # noqa: TC001  # Pydantic resolves field annotations at runtime
    Loan,
    Money,
    Rate,
)
from lib.money import MONEY_CONTEXT, quantize_cents


class PointsRequestFromSavings(BaseModel):
    """PNTS-01 mode where caller already computed monthly_savings.

    Plan 08-03 ``simple_breakeven(points_cost, monthly_savings)`` consumes the
    pair directly; ``npv_breakeven`` walks ``cum_npv(m) -= points_cost`` for
    m in 1..hold_period_months. Negative ``monthly_savings`` (rate-up scenario;
    PNTS-01 edge case) is ALLOWED at construction — engine returns None for both
    breakevens with a warning.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["from_savings"] = "from_savings"
    points_cost: Money = Field(strict=True, gt=Decimal("0"))
    # Signed Decimal (NOT Money — Money's ge=0 would block rate-up scenarios per
    # the docstring above). Mirrors Phase 6 D-03 RefiCashflow.amount precedent.
    monthly_savings: Decimal = Field(strict=True, max_digits=14, decimal_places=2)
    hold_period_months: int = Field(ge=1, le=600)
    discount_rate_annual: Rate  # D-02: REQUIRED; no module default


class PointsRequestFromLoans(BaseModel):
    """PNTS-01 mode where engine derives monthly_savings from two Loan schedules.

    Plan 08-03 calls ``build_schedule(loan_without_points)`` and
    ``build_schedule(loan_with_points)``, computes
    ``monthly_savings = no_pts.monthly_pi - with_pts.monthly_pi``, then routes
    to the same simple_breakeven / npv_breakeven helpers as the from_savings
    mode. Plan 08-05 SC-4 divergence-pin fixture uses this mode for hand-calc
    traceability.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["from_loans"] = "from_loans"
    points_cost: Money = Field(strict=True, gt=Decimal("0"))
    loan_with_points: Loan
    loan_without_points: Loan
    hold_period_months: int = Field(ge=1, le=600)
    discount_rate_annual: Rate  # D-02: REQUIRED; no module default


PointsRequest = Annotated[
    PointsRequestFromSavings | PointsRequestFromLoans,
    Field(discriminator="mode"),
]
"""Pydantic v2 discriminated union by ``mode`` (D-01).

Use ``TypeAdapter(PointsRequest).validate_json(...)`` at the script boundary;
the discriminator routes the raw payload to PointsRequestFromSavings or
PointsRequestFromLoans based on the ``mode`` field's literal value."""


class PointsResponse(BaseModel):
    """Top-level response carrying BOTH simple_breakeven AND npv_breakeven side-by-side.

    Per ROADMAP SC-4 (D-04): both fields are always populated and reported
    together. ``diverge=True`` iff the two outputs are unequal AND both are
    non-None; the divergence-pin fixture (Plan 08-05
    points_simple_lt_npv_seven_pct_discount.json) documents the 37-month gap
    at 7% discount. ``decision`` is the buy/skip recommendation derived from
    ``cumulative_npv_at_hold >= 0``.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    simple_breakeven_months: int | None  # D-03: None = never
    npv_breakeven_months: int | None  # D-03: None = never (within hold)
    diverge: bool
    diverge_explanation: str | None = None
    decision: Literal["buy_points", "skip_points"]
    discount_rate_used: Rate
    hold_period_months: int
    # Signed Decimals (NOT Money) — both can legitimately be negative:
    # - monthly_savings: rate-up scenario in from_loans mode (with-points rate
    #   is HIGHER than without-points rate; negative savings = points cost more).
    # - cumulative_npv_at_hold: the walk strictly decreases for negative savings;
    #   non-crossing happy-path scenarios at high discount rates also stay
    #   negative through hold_period_months. Mirrors Phase 6 D-03 RefiCashflow.amount.
    monthly_savings: Decimal = Field(strict=True, max_digits=14, decimal_places=2)
    cumulative_npv_at_hold: Decimal = Field(strict=True, max_digits=14, decimal_places=2)
    warnings: list[str] = Field(default_factory=list)


def simple_breakeven(points_cost: Money, monthly_savings: Money) -> int | None:
    """PNTS-01: ``months_to_breakeven = ceil(points_cost / monthly_savings)``.

    Returns ``None`` when ``monthly_savings <= 0`` (rate-up scenario; points cost
    MORE than they save). The caller surfaces a structured warning in
    ``PointsResponse.warnings`` rather than raising — D-03-01 mirrors Phase 4
    D-11 blocked_by-via-field-not-raise convention.

    Both inputs are ``Money`` (Decimal). Decimal-safe ceil is performed under
    ``localcontext(MONEY_CONTEXT)`` so the project-wide ROUND_HALF_UP context
    is not mutated; the quotient is rounded toward +inf via
    ``to_integral_value(rounding=ROUND_CEILING)`` and converted to ``int`` at
    the boundary.
    """
    if monthly_savings <= Decimal("0"):
        return None
    with localcontext(MONEY_CONTEXT):
        quotient = points_cost / monthly_savings
        ceiled = quotient.to_integral_value(rounding=ROUND_CEILING)
    return int(ceiled)


def npv_breakeven(
    points_cost: Money,
    monthly_savings: Decimal,
    hold_months: int,
    discount_rate_annual: Rate,
) -> tuple[Decimal, int | None]:
    """PNTS-02 + ROADMAP SC-4: cumulative-NPV walk over months 1..hold_months.

    Per 08-RESEARCH §5.2::

        r_monthly = discount_rate_annual / 12
        cum_npv(m) = sum_{k=1..m} (monthly_savings / (1 + r_monthly)^k) - points_cost

    Walks month-by-month from 1 to ``hold_months`` and returns
    ``(cum_npv_at_hold, months_to_zero)`` where ``months_to_zero`` is the FIRST
    month ``m`` such that ``cum_npv(m) >= 0`` (or ``None`` if it never crosses
    within ``hold_months``).

    Discount rate of ZERO collapses to simple breakeven (no time-value
    adjustment): every discount factor stays at 1, so the walk is just an
    accumulation of ``monthly_savings`` against ``-points_cost`` and crosses
    zero at the same month as ``simple_breakeven``. Mathematical identity
    verified by Plan 08-05 fixture ``points_simple_eq_npv_zero_discount.json``.

    Negative ``monthly_savings`` -> ``cum_npv`` strictly decreases ->
    ``months_to_zero = None``; the discount-rate has no effect on the
    break-detection in this branch (the caller's ``simple_breakeven`` also
    returns ``None`` and the dispatcher surfaces the warning at the response
    level — D-03-04).

    The final ``cum_npv_at_hold`` is returned (quantized to cents) so the
    dispatcher can drive the buy/skip decision (``buy_points`` iff
    ``cum_npv_at_hold >= 0``; D-03-04). Note this is the **unquantized**
    accumulator's value rounded once at the boundary — never quantize
    mid-walk.
    """
    r_monthly = discount_rate_annual / Decimal("12")
    months_to_zero: int | None = None
    with localcontext(MONEY_CONTEXT):
        cum_npv = -points_cost
        if r_monthly > Decimal("0"):
            multiplier = Decimal("1") / (Decimal("1") + r_monthly)
            discount_factor = Decimal("1")
            for m in range(1, hold_months + 1):
                discount_factor = discount_factor * multiplier
                cum_npv = cum_npv + monthly_savings * discount_factor
                if months_to_zero is None and cum_npv >= Decimal("0"):
                    months_to_zero = m
        else:
            # Zero discount: collapses to undiscounted accumulation
            for m in range(1, hold_months + 1):
                cum_npv = cum_npv + monthly_savings
                if months_to_zero is None and cum_npv >= Decimal("0"):
                    months_to_zero = m
    return quantize_cents(cum_npv), months_to_zero


def _derive_monthly_savings(loan_with_points: Loan, loan_without_points: Loan) -> Money:
    """Run two ``build_schedule`` calls and diff ``monthly_pi`` (D-03-05).

    Used by the from_loans branch of ``evaluate``. Returns the difference
    ``no_points.monthly_pi - with_points.monthly_pi`` quantized to cents.
    Phase 3 ``Schedule.monthly_pi`` is already quantized, so the subtraction
    is exact-to-cent; the explicit ``quantize_cents`` is defensive.
    """
    s_with = build_schedule(loan_with_points, frequency="monthly")
    s_without = build_schedule(loan_without_points, frequency="monthly")
    return quantize_cents(s_without.monthly_pi - s_with.monthly_pi)


def evaluate(req: PointsRequest) -> PointsResponse:
    """PNTS-01 + PNTS-02 + ROADMAP SC-4: report simple AND npv side-by-side.

    Dispatch on ``req.mode``:
      ``from_savings`` -> use the caller-supplied ``monthly_savings`` directly.
      ``from_loans``   -> derive ``monthly_savings`` via two ``build_schedule``
                          calls (one per Loan) and diff ``monthly_pi``.

    Always reports BOTH ``simple_breakeven_months`` AND ``npv_breakeven_months``
    side-by-side (D-04 LOCKED). ``diverge`` is True iff both are non-None and
    unequal (D-01-07 + D-04). Decision = ``buy_points`` iff
    ``cumulative_npv_at_hold >= 0``; forced to ``skip_points`` when
    ``simple_breakeven`` is None (negative savings — D-03-04 defensive force).
    Negative or zero monthly_savings emits a structured warning rather than
    raising (D-03-01 mirrors Phase 4 D-11).
    """
    if isinstance(req, PointsRequestFromLoans):
        monthly_savings = _derive_monthly_savings(req.loan_with_points, req.loan_without_points)
    else:
        monthly_savings = req.monthly_savings

    warnings: list[str] = []
    if monthly_savings <= Decimal("0"):
        warnings.append(f"NEGATIVE_OR_ZERO_SAVINGS_{monthly_savings}")

    simple_m = simple_breakeven(req.points_cost, monthly_savings)
    cum_npv, npv_m = npv_breakeven(
        req.points_cost,
        monthly_savings,
        req.hold_period_months,
        req.discount_rate_annual,
    )

    diverge = simple_m is not None and npv_m is not None and simple_m != npv_m
    diverge_explanation: str | None = None
    if diverge:
        # Split assertions for ruff PT018 + mypy narrowing
        assert simple_m is not None
        assert npv_m is not None
        gap = npv_m - simple_m
        diverge_explanation = (
            f"NPV breakeven {gap:+d} months relative to simple due to "
            f"{req.discount_rate_annual} annual discount rate eroding present "
            f"value of late savings"
        )

    decision: Literal["buy_points", "skip_points"] = (
        "buy_points" if cum_npv >= Decimal("0") else "skip_points"
    )
    if simple_m is None:
        decision = "skip_points"

    return PointsResponse(
        simple_breakeven_months=simple_m,
        npv_breakeven_months=npv_m,
        diverge=diverge,
        diverge_explanation=diverge_explanation,
        decision=decision,
        discount_rate_used=req.discount_rate_annual,
        hold_period_months=req.hold_period_months,
        monthly_savings=quantize_cents(monthly_savings),
        cumulative_npv_at_hold=cum_npv,
        warnings=warnings,
    )
