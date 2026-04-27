"""Conventional PMI auto-termination and request-termination rules.

Citation: 12 USC §4901-4910 (Homeowners Protection Act of 1998) — sections 4902(a)
(borrower-requested cancellation at 80% LTV based on original property value),
4902(b) (automatic termination at 78% LTV per amortization schedule), and
4902(g) (high-risk loan midpoint carve-out: PMI terminates no later than the
midpoint of the amortization period regardless of LTV).

Source URL: https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/
Source URL: https://www.fdic.gov/consumer-compliance-examination-manual/v-5-homeowners-protection-act
Effective: 1999-07-29 (HPA original effective date; no material amendment since)

Pattern reference: cfpb/jumbo-mortgage one-predicate-per-citation pattern.

What this predicate decides:
  Given a Loan, current scheduled balance, original property value, a high-risk
  flag, and (for high-risk loans) months elapsed, return whether PMI auto-
  terminates (78% LTV trigger), is request-terminable (80% LTV trigger), is in
  force, or has terminated under the high-risk midpoint carve-out.

LTV is computed against the ORIGINAL appraised property value (HPA-mandated;
re-appraisal-based cancellation is outside the statute and out of scope for v1
per CONTEXT.md `<deferred>` line 187 — refi resets `original_value`, but that
logic lives in Phase 6 refi, not here).

NO YAML lookup — HPA values 0.78 / 0.80 are statutory constants per 12 USC §4902
and are embedded as `Final[Decimal]` module constants per CONTEXT.md D-02.

Edge cases:
  - is_high_risk=True with months_elapsed past midpoint of amortization →
    "high_risk_midpoint_terminated" regardless of LTV (§4902(g)).
  - is_high_risk=True with months_elapsed before midpoint → standard 78%/80%
    rules still apply (caller passes is_high_risk=True only when designating).
  - original_property_value <= 0 → ValueError (loud money-discipline guard).
  - is_high_risk=True with months_elapsed=None → ValueError (loud failure;
    the §4902(g) midpoint check needs months_elapsed).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from lib.models import Loan

PMITerminationStatus = Literal[
    "auto_terminated",
    "request_eligible",
    "in_force",
    "high_risk_midpoint_terminated",
]
"""HPA termination outcome (RUL-05)."""

# Statutory LTV thresholds — embedded as named constants per CONTEXT.md D-02
# (HPA values 0.78 / 0.80 are statutory; no YAML; citation comments load-bearing).
LTV_AUTO_TERMINATE: Final[Decimal] = Decimal("0.78")  # 12 USC §4902(b)
LTV_REQUEST_ELIGIBLE: Final[Decimal] = Decimal("0.80")  # 12 USC §4902(a)


def status(
    loan: Loan,
    scheduled_balance: Decimal,
    original_property_value: Decimal,
    is_high_risk: bool = False,
    months_elapsed: int | None = None,
) -> PMITerminationStatus:
    """Return PMI termination status per HPA 12 USC §4902.

    Args:
        loan: Phase-1 Loan model. term_months drives the §4902(g) midpoint
            calculation (midpoint = loan.term_months // 2).
        scheduled_balance: current scheduled principal balance per amortization
            schedule (NOT current market value of the property).
        original_property_value: appraised value at origination. Required > 0.
        is_high_risk: True iff the loan is HPA-defined high-risk (caller's
            responsibility to determine; HPA §4902(f) defines high-risk).
        months_elapsed: months since first payment. Required when is_high_risk
            is True (the §4902(g) midpoint check needs it). May be None
            otherwise.

    Returns:
        - "high_risk_midpoint_terminated" if is_high_risk=True AND
          months_elapsed >= loan.term_months // 2 (§4902(g)).
        - "auto_terminated" if scheduled_balance / original_property_value
          <= 0.78 (§4902(b)).
        - "request_eligible" if scheduled_balance / original_property_value
          <= 0.80 (§4902(a)).
        - "in_force" otherwise.

    Raises:
        ValueError: if original_property_value <= 0.
        ValueError: if is_high_risk=True and months_elapsed is None.
    """
    if original_property_value <= Decimal("0"):
        raise ValueError(f"original_property_value must be > 0; got {original_property_value!r}")
    if is_high_risk and months_elapsed is None:
        raise ValueError(
            "months_elapsed is required when is_high_risk=True (HPA §4902(g) midpoint check)"
        )

    # §4902(g) high-risk midpoint carve-out — checked BEFORE the LTV thresholds
    # because the carve-out terminates regardless of LTV.
    if is_high_risk:
        midpoint = loan.term_months // 2
        # months_elapsed has been guarded above; mypy knows it is int here.
        assert months_elapsed is not None  # mypy --strict narrowing
        if months_elapsed >= midpoint:
            return "high_risk_midpoint_terminated"

    ltv = scheduled_balance / original_property_value
    if ltv <= LTV_AUTO_TERMINATE:
        return "auto_terminated"
    if ltv <= LTV_REQUEST_ELIGIBLE:
        return "request_eligible"
    return "in_force"
