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

from lib.models import (  # noqa: TC001  # Pydantic resolves field annotations at runtime
    Loan,
    Money,
    Rate,
)
from lib.money import MONEY_CONTEXT


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
    monthly_savings: Money  # may be negative for rate-up scenarios; engine warns
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
    monthly_savings: Money  # echoed; useful when caller used from_loans
    cumulative_npv_at_hold: Money  # cum_npv(hold_period_months); decision driver
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


def evaluate(req: PointsRequest) -> PointsResponse:
    """Dispatch on ``req.mode`` and run the matching breakeven analysis.

    Wave 1 (Plan 08-01 — this file) ships the type contract only. Wave 3
    (Plan 08-03) replaces this body with two branches:
      from_savings: pass (points_cost, monthly_savings, hold, discount_rate)
                    directly to simple_breakeven + npv_breakeven helpers
      from_loans:   call build_schedule on each Loan, derive monthly_savings,
                    route to the same helpers

    Cross-plan stub idiom: Phase 4 D-08 (lib.affordability Wave 1 → Wave 2
    pattern). Stubbing here lets Plan 08-03 fill the body without re-importing
    the surface across the wave boundary.
    """
    raise NotImplementedError("lib.points.evaluate body lives in Plan 08-03")
