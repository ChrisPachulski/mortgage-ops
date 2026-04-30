"""Schedule generator wrapping numpy-financial PMT/IPMT/PPMT (AMRT-01).

Per AMRT-01, this module wraps numpy-financial — it does NOT reimplement amortization math.
The scalar per-period iteration is chosen over vectorized npf.ipmt/ppmt because
extra-principal mid-stream (AMRT-04, D-05/D-07/D-08) and biweekly-true acceleration
(AMRT-03, D-01/D-04) both invalidate the vectorized formula's "remaining balance =
principal-amortizing" premise. One code path serves all three frequencies.

Phase 1 frozen surface usage: this module USES `lib.models.Loan/Payment/Schedule` and
`lib.money.quantize_cents`; it MUST NOT mutate Loan or rebind Phase 1 invariants. The
Schedule constructor's D-15 model_validator enforces total_interest agreement at
construction time, so build_schedule sets `total_interest = payments[-1].cumulative_interest`
by construction.

For both biweekly modes, Schedule.monthly_pi is the implied monthly P&I (computed at
rate/12), NOT the biweekly cashflow. Phase 10 SKILL.md narration must reflect this —
biweekly callers see "per-biweekly-debit" amounts on each Payment.payment row, but
Schedule.monthly_pi is the headline rate-and-term metric in monthly units.

LOCKED DECISION - D-01 (both biweekly modes ship; per CONTEXT.md):
  Loan.frequency='biweekly' selects ONE of two algorithms by Loan.biweekly_mode:
    - 'true':         period_rate = annual_rate/26; biweekly cashflow = monthly_pi/2;
                      schedule terminates ~5-7 years early (acceleration). Default
                      mode when frequency='biweekly' and biweekly_mode is None (D-02).
    - 'half-monthly': period_rate = annual_rate/12; schedule has term_months rows
                      (monthly amortization with biweekly billing decoration).
                      Per RESEARCH §3.2 Option A — interest still booked monthly.

LOCKED DECISION - D-02 (biweekly_mode validity / default; per CONTEXT.md):
  AmortizeRequest._biweekly_mode_consistency raises ValidationError when
  frequency='monthly' AND biweekly_mode is not None. Default biweekly_mode='true'
  is applied INSIDE build_schedule (not in the model) so callers can pass
  biweekly_mode=None and get the documented default while the model preserves
  "what was provided" semantics for round-tripping.

LOCKED DECISION - D-03 (date cadence; per CONTEXT.md):
  Monthly + half-monthly biweekly: payment_date = origination + relativedelta(months=period).
  True biweekly:                    payment_date = origination + relativedelta(weeks=2*period).
  First payment is one period AFTER origination (industry standard).

LOCKED DECISION - D-04 (rate-per-period conversion; per CONTEXT.md):
  Monthly:           period_rate = annual_rate / Decimal("12").
  True biweekly:     period_rate = annual_rate / Decimal("26").
  Half-monthly:      period_rate = annual_rate / Decimal("12") (interest still booked
                     monthly per RESEARCH §3.2 Option A); the biweekly cashflow is
                     monthly_pi / Decimal("2") on the lender's billing side, but the
                     schedule itself is monthly.
  All conversions stay in Decimal — never go through float.

LOCKED DECISION - D-05 (extra-principal list-of-entries shape; per CONTEXT.md):
  ExtraPrincipalEntry(period: int>=1, amount: Decimal>0, recurring: bool=False).
  At any period p the active recurring entry is the LATEST entry with
  entry.period <= p AND entry.recurring=True (later recurring overrides earlier
  from its own period onward). One-shot entries (recurring=False) fire only when
  entry.period == p and stack ADDITIVELY on top of the recurring component.

LOCKED DECISION - D-06 (extra-principal period numbering; per CONTEXT.md):
  ExtraPrincipalEntry.period matches the schedule's natural cadence. For monthly
  schedules, period = month number (1..N). For biweekly schedules (true mode),
  period = biweekly period number (1..~780 for 30yr biweekly). When migrating a
  "$200/month extra" scenario to biweekly, the CALLER divides by 2 — the engine
  does NOT internally convert.

LOCKED DECISION - D-07 (composition order within a period; per CONTEXT.md):
  Each period executes EXACTLY in this order:
    1. interest = quantize_cents(period_rate * prior_balance)
    2. principal = quantize_cents(level_pmt - interest)   [or balance, on final period]
    3. extra = _resolve_extra(period, entries, cap = prior_balance - principal)  [D-08]
    4. new_balance = prior_balance - principal - extra
  Extra-principal applies AFTER regular principal. Interest accrues on the prior
  balance untouched by extra (matches numpy-financial's ipmt/ppmt convention).

LOCKED DECISION - D-08 (cap silently at remaining balance; per CONTEXT.md):
  If recurring or one-shot extra would overpay the remaining balance after regular
  principal, cap silently at that remaining-balance value. Do NOT raise — overpaying
  is a legitimate early-payoff scenario. The cap is silent at the row level but is
  surfaced via Schedule.final_payment_adjusted=True (and the schedule terminates
  at that period).

LOCKED DECISION - D-09 (final-period principal cleanup; per CONTEXT.md):
  On the final period (term reached, OR extra-principal zeroed/overshot the balance,
  OR biweekly-true acceleration's last-rung), set principal = remaining_balance so
  Payment.balance lands at exactly Decimal("0.00"). Cents-drift is empirical
  (-$4.58 to +$2.90 across the four golden oracles per RESEARCH §5); this cleanup
  absorbs it cleanly without violating AMRT-07 (sum of principal+extra = original).

LOCKED DECISION - D-10 (final_payment_adjusted detection rule; per CONTEXT.md):
  Schedule.final_payment_adjusted = True iff
    - last.principal != quantize_cents(level_pmt - last.interest)  [drift cleanup]
    - OR any payment has extra_principal > 0                       [extras fired]
  This catches cents-drift, formulaic-acceleration, and extra-principal-induced
  early-payoff in one expression. Default False; engine sets per the rule above.

LOCKED DECISION - D-12 (origination synthesis at engine-time; per CONTEXT.md):
  When Loan.origination_date is None, build_schedule synthesizes from
  datetime.now(UTC).date() at schedule-generation time. Synthesis is INSIDE this
  module (not in lib.models.Loan) so Phase 1's frozen surface keeps
  Loan.origination_date: date | None. Library callers (Phase 5 ARM, Phase 8 stress)
  inherit the same default behavior.

LOCKED DECISION - D-13 (relativedelta month-end clipping trusted; per CONTEXT.md):
  dateutil.relativedelta clips Jan-31 + 1mo to Feb-28/29 automatically. Behavior
  documented stable for >5 years; we pin a fixture exercising the edge in tests.

LOCKED DECISION - D-14 (Payment cumulative-totals tracking; per CONTEXT.md):
  Each Payment row carries cumulative_interest and cumulative_principal Money fields
  (running totals from period 1 through itself). Phase 1 model defaults both to
  Decimal("0.00") for backwards compatibility; this engine populates them per row.

LOCKED DECISION - D-15 (Schedule.total_interest by construction; per CONTEXT.md):
  Schedule.total_interest == payments[-1].cumulative_interest is enforced by a
  Pydantic @model_validator on Schedule (Plan 03-01). build_schedule sets
  total_interest = payments[-1].cumulative_interest by construction so the
  validator passes; mismatch would mean a bug in this engine.

numpy-financial bug avoidance:
  - Bug #130 (npf.pmt fv-sign flipped when fv != 0):
      https://github.com/numpy/numpy-financial/issues/130
      We always pass fv=0 (default). Phase 3 has no balloon-mortgage path.
  - Bug #131 (numpy-financial's irr function is arch-dependent):
      https://github.com/numpy/numpy-financial/issues/131
      We never call that function. Phase 6 / 7 will use pyxirr or our own
      Newton-Raphson per Reg Z Appendix J.

numpy-financial 1.0.0 returns Decimal when fed Decimal (verified empirically
2026-04-29). Sign convention: npf.pmt returns cashflow-out (negative);
we flip with `-` at the boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

import numpy_financial as npf
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.models import Loan, Payment, Schedule
from lib.money import quantize_cents

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date


class ExtraPrincipalEntry(BaseModel):
    """One extra-principal entry (D-05).

    One schema collapses one-shot, recurring, and step-up scenarios:
      - one-shot at period 60: ExtraPrincipalEntry(period=60, amount=Decimal("5000"), recurring=False)
      - recurring $200 from period 1: ExtraPrincipalEntry(period=1, amount=Decimal("200"), recurring=True)
      - step-up at period 13: prior recurring entry from period 1, plus a later
        recurring entry at period 13 — the later entry overrides from period 13 onward.

    `amount` uses `gt=Decimal("0")` (strictly positive); zero is meaningless for
    extra-principal and surfaces immediately as a validation error.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=1)
    amount: Decimal = Field(strict=True, gt=Decimal("0"), max_digits=14, decimal_places=2)
    recurring: bool = False


class AmortizeRequest(BaseModel):
    """Top-level request schema for scripts/amortize.py (D-19 boundary)."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    frequency: Literal["monthly", "biweekly"] = "monthly"
    biweekly_mode: Literal["true", "half-monthly"] | None = None
    extra_principal: list[ExtraPrincipalEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _biweekly_mode_consistency(self) -> AmortizeRequest:
        """D-02: biweekly_mode MUST be None when frequency is monthly.

        The default (biweekly_mode='true' when frequency='biweekly' and
        biweekly_mode is None) is applied inside build_schedule, not here —
        the model preserves "what the caller provided" semantics.
        """
        if self.frequency == "monthly" and self.biweekly_mode is not None:
            raise ValueError("biweekly_mode must be None when frequency='monthly' (D-02)")
        return self


def _resolve_extra(
    period: int,
    entries: Sequence[ExtraPrincipalEntry],
    cap: Decimal,
) -> Decimal:
    """Resolve extra-principal for a single period (D-05, D-07, D-08).

    - Active recurring = latest entry with entry.period <= period and recurring=True.
    - One-shot entries (recurring=False) fire only when entry.period == period
      and stack additively on top of the recurring component.
    - Result is capped at `cap` (the remaining balance after regular principal,
      D-08); cap-application is the engine's responsibility, NOT this helper's
      business — this helper just returns min(raw, cap) quantized.
    """
    active_recurring = max(
        (e for e in entries if e.recurring and e.period <= period),
        key=lambda e: e.period,
        default=None,
    )
    one_shots = [e for e in entries if not e.recurring and e.period == period]

    raw = active_recurring.amount if active_recurring else Decimal("0.00")
    for e in one_shots:
        raw = raw + e.amount

    capped = min(raw, cap) if cap > Decimal("0.00") else Decimal("0.00")
    return quantize_cents(capped)


def build_schedule(
    loan: Loan,
    *,
    frequency: Literal["monthly", "biweekly"] = "monthly",
    biweekly_mode: Literal["true", "half-monthly"] | None = None,
    extra_principal: Sequence[ExtraPrincipalEntry] = (),
) -> Schedule:
    """Generate an amortization schedule (AMRT-02..05).

    Dispatch entrypoint. After D-12 origination synthesis and D-02 defaulting,
    routes to one of three private helpers based on frequency + biweekly_mode:
      - monthly                                -> _build_fixed_monthly
      - biweekly + biweekly_mode='true'        -> _build_biweekly_true
      - biweekly + biweekly_mode='half-monthly' -> _build_biweekly_half_monthly

    All three helpers share the same shape: scalar per-period iteration with
    end-of-period quantize_cents discipline, D-07/D-08 extra-principal composition,
    D-09 final-period cleanup, D-10 final_payment_adjusted detection, D-14
    cumulative-totals tracking, D-15 total_interest set by construction.

    D-12: when loan.origination_date is None, synthesize from datetime.now(UTC).
    """
    # D-12: synthesize origination at engine time (NOT in the Pydantic model)
    origination = loan.origination_date or datetime.now(UTC).date()

    # D-02 default: when frequency=biweekly and biweekly_mode is None, default to "true"
    if frequency == "biweekly" and biweekly_mode is None:
        biweekly_mode = "true"
    if frequency == "monthly" and biweekly_mode is not None:
        raise ValueError("biweekly_mode must be None when frequency='monthly' (D-02)")

    if frequency == "monthly":
        return _build_fixed_monthly(loan, origination, extra_principal)
    if biweekly_mode == "true":
        return _build_biweekly_true(loan, origination, extra_principal)
    # biweekly_mode == "half-monthly"
    assert biweekly_mode == "half-monthly"  # mypy narrowing
    return _build_biweekly_half_monthly(loan, origination, extra_principal)


def _build_fixed_monthly(
    loan: Loan,
    origination: date,
    extra_principal: Sequence[ExtraPrincipalEntry],
) -> Schedule:
    """Fixed-rate monthly path (AMRT-02).

    npf.pmt called ONCE for the level payment at rate/12 (D-04). Per-period
    interest = period_rate * prior_balance, regular principal = pmt - interest,
    extra-principal applied AFTER (D-07) and capped at remaining balance (D-08).
    Final period: principal = prior_balance (D-09); balance = Decimal("0.00").
    """
    period_rate = loan.annual_rate / Decimal("12")  # D-04
    level_pmt = quantize_cents(-npf.pmt(period_rate, loan.term_months, loan.principal))

    balance = loan.principal
    cum_int = Decimal("0.00")
    cum_prin = Decimal("0.00")
    payments: list[Payment] = []

    for period in range(1, loan.term_months + 1):
        interest = quantize_cents(period_rate * balance)

        is_last_term_period = period == loan.term_months
        if is_last_term_period:
            # D-09 final-period cleanup: principal = remaining balance
            principal_paid = balance
            payment_amount = quantize_cents(principal_paid + interest)
        else:
            principal_paid = quantize_cents(level_pmt - interest)
            payment_amount = level_pmt

        # D-07 + D-08: extra-principal AFTER regular principal, capped at remaining balance
        remaining_after_regular = balance - principal_paid
        extra = _resolve_extra(period, extra_principal, cap=remaining_after_regular)
        balance_after = remaining_after_regular - extra

        # D-09 cents-drift cleanup on the formulaic last period: if residual remains,
        # absorb into final principal so balance lands at exactly Decimal("0.00").
        if is_last_term_period and balance_after != Decimal("0.00"):
            principal_paid = principal_paid + balance_after
            payment_amount = quantize_cents(principal_paid + interest + extra)
            balance_after = Decimal("0.00")

        # Final-period detection: term reached OR extra-principal zeroed the balance
        extra_zeroed_balance = balance_after == Decimal("0.00") and extra > Decimal("0.00")
        final_period = is_last_term_period or extra_zeroed_balance

        cum_int = quantize_cents(cum_int + interest)
        cum_prin = quantize_cents(cum_prin + principal_paid)

        payments.append(
            Payment(
                period=period,
                payment_date=origination + relativedelta(months=period),  # D-03
                payment=payment_amount,
                principal=principal_paid,
                interest=interest,
                extra_principal=extra,
                balance=balance_after,
                cumulative_interest=cum_int,  # D-14
                cumulative_principal=cum_prin,  # D-14
            )
        )

        balance = balance_after
        if final_period:
            break

    # D-10 detection rule: drift cleanup OR any extra-principal fired
    last = payments[-1]
    formulaic_last_principal = quantize_cents(level_pmt - last.interest)
    final_payment_adjusted = (last.principal != formulaic_last_principal) or any(
        p.extra_principal > Decimal("0.00") for p in payments
    )

    return Schedule(
        loan=loan,
        monthly_pi=level_pmt,
        total_interest=last.cumulative_interest,  # D-15: matches by construction
        final_payment_adjusted=final_payment_adjusted,
        payments=payments,
    )


def _build_biweekly_true(
    loan: Loan,
    origination: date,
    extra_principal: Sequence[ExtraPrincipalEntry],
) -> Schedule:
    """True biweekly path (AMRT-03 D-01 D-04).

    period_rate = annual_rate / Decimal("26") for interest accrual. Biweekly
    cashflow = quantize_cents(monthly_pi / Decimal("2")) where monthly_pi is the
    IMPLIED monthly P&I computed at rate/12 (per RESEARCH §3.1; this is what
    Schedule.monthly_pi reports — NOT the biweekly cashflow).

    The schedule terminates ~5-7 years early (acceleration). For 30yr at 6.5%
    on $200k, ~628 biweekly periods (vs the formulaic 720). Final-period
    detection: when `balance + interest <= biweekly_payment`, this is the last
    period — D-09 cleanup sets principal = balance.

    Schedule.monthly_pi is the implied monthly P&I, not the biweekly cashflow.
    """
    period_rate = loan.annual_rate / Decimal("26")  # D-04
    monthly_pi = quantize_cents(
        -npf.pmt(loan.annual_rate / Decimal("12"), loan.term_months, loan.principal)
    )
    biweekly_payment = quantize_cents(monthly_pi / Decimal("2"))

    balance = loan.principal
    cum_int = Decimal("0.00")
    cum_prin = Decimal("0.00")
    payments: list[Payment] = []

    # Safety bound: biweekly accelerates payoff but never beyond ~term_months*2 periods.
    max_periods = loan.term_months * 2 + 10
    period = 0
    while balance > Decimal("0.00"):
        period += 1
        if period > max_periods:
            raise ValueError(f"biweekly schedule did not terminate in expected periods: {period}")

        interest = quantize_cents(period_rate * balance)

        # D-09 final-period detection: formulaic biweekly payment would zero/overshoot balance
        formulaic_termination = balance + interest <= biweekly_payment
        if formulaic_termination:
            principal_paid = balance
            payment_amount = quantize_cents(principal_paid + interest)
        else:
            principal_paid = quantize_cents(biweekly_payment - interest)
            payment_amount = biweekly_payment

        # D-07 + D-08: extra-principal AFTER regular principal, capped at remaining balance
        remaining_after_regular = balance - principal_paid
        extra = _resolve_extra(period, extra_principal, cap=remaining_after_regular)
        balance_after = remaining_after_regular - extra

        # Final-period detection: formulaic termination OR extra-principal zeroed balance
        final_period = formulaic_termination or balance_after == Decimal("0.00")

        cum_int = quantize_cents(cum_int + interest)
        cum_prin = quantize_cents(cum_prin + principal_paid)

        payments.append(
            Payment(
                period=period,
                payment_date=origination + relativedelta(weeks=2 * period),  # D-03
                payment=payment_amount,
                principal=principal_paid,
                interest=interest,
                extra_principal=extra,
                balance=balance_after,
                cumulative_interest=cum_int,  # D-14
                cumulative_principal=cum_prin,  # D-14
            )
        )

        balance = balance_after
        if final_period:
            break

    # D-10 detection rule: principal != formulaic biweekly principal OR any extra fired
    last = payments[-1]
    formulaic_last_principal = quantize_cents(biweekly_payment - last.interest)
    final_payment_adjusted = (last.principal != formulaic_last_principal) or any(
        p.extra_principal > Decimal("0.00") for p in payments
    )

    return Schedule(
        loan=loan,
        monthly_pi=monthly_pi,  # IMPLIED monthly P&I (rate/12), per RESEARCH §3.1
        total_interest=last.cumulative_interest,  # D-15: matches by construction
        final_payment_adjusted=final_payment_adjusted,
        payments=payments,
    )


def _build_biweekly_half_monthly(
    loan: Loan,
    origination: date,
    extra_principal: Sequence[ExtraPrincipalEntry],
) -> Schedule:
    """Half-monthly biweekly path (AMRT-03 D-04).

    Per RESEARCH §3.2 Option A and CONTEXT.md D-04 'interest still booked monthly':
    half-monthly biweekly is monthly amortization with biweekly billing. The
    schedule rows match a pure-monthly schedule (term_months rows for term_months
    months). The biweekly cashflow cadence is a billing-frequency decoration that
    consumers (Phase 10 SKILL.md narration) handle outside the engine.

    Math is identical to fixed-rate monthly — period_rate = rate/12 (D-04),
    schedule has term_months rows, payment_date advances by relativedelta(months=1).
    Implementation delegates to _build_fixed_monthly.
    """
    return _build_fixed_monthly(loan, origination, extra_principal)
