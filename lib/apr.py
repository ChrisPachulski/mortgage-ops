"""Phase 7 Estimated APR — Reg Z Appendix J Newton-Raphson solver (Pydantic boundary).

Phase 7 builds an "estimated APR" engine on top of Phase 3 amortization. Wave 1
(Plan 07-01) shipped the Pydantic v2 boundary models (APRRequest,
AdvanceScheduleEntry, PaymentScheduleEntry, APRResponse). Wave 2 (Plan 07-02 —
this commit set) ships the Newton-Raphson body: ``_decimal_pow``,
``_unit_period_equation`` (f(i)), ``_derivative`` (f'(i)), ``_seed_apr``
(npf.rate-with-fallback), the ``APRConvergenceError`` exception class, and
the full ``solve_apr`` Decimal-arithmetic iteration. Wave 4 (Plan 07-04)
ships the JSON-in / JSON-out CLI at scripts/apr_reg_z.py.

Phase-7 consumer note: lib/rules/reg_z.py:43-47 already references this
module — `within_apr_tolerance(disclosed, actual, is_irregular)` is the
predicate Phase 7 calls when APRRequest.disclosed_apr is supplied (see
APRResponse.tolerance_check). Phase 7 keeps the "estimated APR" label
because mortgage-ops does not make commercial Reg Z disclosures (ROADMAP
SC-4); the solver is a calc, not a disclosure.

Requirements covered (Plans 07-01 + 07-02; remaining closure across Waves 4-7):
  APR-01: lib/apr.py Newton-Raphson solver against Reg Z Appendix J
          unit-period equation (Plans 07-01 + 07-02 together: model
          surface + body + convergence + helpers).
  APR-02: Newton-Raphson seeded from npf.rate (Plan 07-02 _seed_apr).
  APR-03: Convergence tolerance Decimal("0.00001") (Plan 07-02 TOLERANCE
          + DOLLAR_RESIDUAL dual criterion D-10).
  APR-04: 20+ HMDA Platform capture-as-fixture cross-validation (Wave 7).
  APR-05: Reg Z Appendix J Example J-1 worked example fixture (Wave 5).
  APR-06: User-facing output uses literal "estimated APR" (this plan
          enforces at the Pydantic boundary via D-05).
  APR-07: scripts/apr_reg_z.py JSON-in / JSON-out CLI (Wave 4).
  APR-08: references/apr-reg-z.md unit-period model + day-count
          conventions documentation (Wave 6).

LOCKED DECISIONS (carried from .planning/phases/07-estimated-apr/07-CONTEXT.md):

- D-01: All four boundary models use ConfigDict(strict=True, frozen=True,
        extra="forbid"). Phase 1 D-08 inheritance — every Pydantic boundary
        in mortgage-ops uses the same trio.

- D-02: APRRequest.day_count defaults to "30/360" per FFIEC tool default
        + RESEARCH §Q(b). The Literal accepts {"30/360", "actual/365",
        "actual/actual"}; v1 cross-validation only covers 30/360 (Wave 7
        captures), but the type surface accepts all three so future ARM /
        treasury phases can extend without a model bump.

- D-03: APRRequest.unit_periods_per_year defaults to 12 (monthly
        mortgage). Settable in [1, 365] for non-monthly products. Phase 8+
        stress-paths may use 26 for biweekly.

- D-04: APRRequest.finance_charges is REQUIRED and CALLER-SUPPLIED
        (orchestrator-locked decision; documented in
        references/apr-reg-z.md §3). The engine subtracts finance_charges
        from loan.principal to form amount_financed per Reg Z §1026.18(b).
        It does NOT classify which closing costs qualify as §1026.4
        finance charges — that determination belongs to the caller.

- D-05: APRResponse.summary literal-text invariant is enforced at the
        Pydantic model boundary via @model_validator(mode="after"), NOT
        only at the CLI. Constructing APRResponse(summary="APR is 7%")
        raises ValidationError. The validator (a) requires the literal
        substring "estimated APR" to appear and (b) forbids any bare
        "APR" word (regex \\bAPR\\b) outside the allowed phrases
        "estimated APR" and "APR tolerance". This pins ROADMAP SC-4 at
        the deepest possible boundary.

- D-06: APRRequest.advance_schedule MUST contain at least one advance at
        unit_period_offset=0 with unit_period_fraction=0 (the t=0
        advance — Reg Z Appendix J §(b)(2)). Reverse-mode "amount-financed
        only" callers pass a single entry
        AdvanceScheduleEntry(unit_period_offset=0,
                             amount=loan.principal - finance_charges).
        Cross-field invariant enforced via
        APRRequest._advance_schedule_has_t0_advance.

- D-07: APRResponse.iterations is Field(ge=1, le=50). Pydantic enforces
        ROADMAP SC-3's 50-iteration cap at the model layer; the solver
        MUST raise APRConvergenceError BEFORE constructing the response
        when the cap is exceeded (so a malformed response with iterations
        > 50 cannot be emitted by the engine — defense in depth against a
        future bug).

- D-08: APRResponse.tolerance_check is dict[str, Any] | None (NOT a typed
        Pydantic submodel). Rationale: keep the schema flexible for
        Phase 8 / Phase 12 extensions (e.g., adding "computed_at" or
        "regulation_subsection" without a model bump). Documented field-by-
        field in the APRResponse.tolerance_check docstring; Wave 4 (CLI)
        documents the canonical shape in scripts/apr_reg_z.py --help.

- D-15: _compute_odd_first_period_fraction(origination, first_payment,
        day_count) accepts the same Literal as APRRequest.day_count
        ({"30/360", "actual/365", "actual/actual"}) and returns Decimal in
        [-1, 1) per Reg Z §1026.17(c)(4). Plan 07-03 (Wave 3).

- D-16: Short first periods (negative f) are mathematically valid per Reg Z
        and engine accepts them; v1 cross-validates only long cases (f in
        [0, 1)). f >= 1 raises ValueError — caller should insert an extra
        t=1 advance instead. Plan 07-03 (Wave 3).

- D-17: APRRequest.odd_first_period_days is the user-friendly INTEGER
        shortcut consumed in Wave 3 — solve_apr internally rewrites the
        first PaymentScheduleEntry.unit_period_fraction. Advanced callers
        bypass by setting unit_period_fraction directly on the
        PaymentScheduleEntry and leaving odd_first_period_days=0 (e.g.,
        Phase 8 stress callers using _compute_odd_first_period_fraction
        with explicit dates). Plan 07-03 (Wave 3).

- D-18: "Small differences" (< 7 days for monthly) per §1026.17(c)(4) are
        NOT auto-zeroed by the engine — the engine reports the exact
        fraction. Caller (or future Phase 8 stress wrapper) may zero them.
        Documented in references/apr-reg-z.md §3 (Wave 6).

Day-count conventions (Wave 3 / Plan 07-03; D-15..D-18):

  The Reg Z Appendix J §(b)(5)(iii) odd-first-period fraction f depends on
  the day-count convention the creditor used to compute the finance charge
  (12 CFR §1026.17(c)(4)). _compute_odd_first_period_fraction(origination,
  first_payment, day_count) implements the three v1-supported conventions:

  - "30/360" (US default; FFIEC tool default per RESEARCH §Q(b)):
        f = (days - 30) / 30
    Every month is 30 days, year is 360. Standard for closed-end mortgages.

  - "actual/365":
        f = (days - 365/12) / (365/12)              # 365/12 ~= 30.4167
    Actual day counts, year is 365. Used by some adjustable-rate products.

  - "actual/actual":
        f = (days - actual_unit_days) / actual_unit_days
    Where actual_unit_days = (origination + relativedelta(months=1) -
    origination).days. Real day counts, real month length (handles month-
    end edges per the project-wide python-dateutil idiom). Used by
    treasuries; rare for mortgages.

  The helper is exported (underscore-prefixed but importable) for advanced
  callers who need to compute fractions from explicit dates rather than
  the APRRequest.odd_first_period_days integer shortcut. Phase 8 stress
  wrappers (parameter sweeps over rate paths x loan amounts x points) use
  this directly when an origination date varies across grid cells.

References (canonical URLs verified 2026-05-02 in 07-RESEARCH.md):
- 12 CFR Part 1026 Appendix J (Reg Z APR computation):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026
- 12 CFR §1026.17(c)(4) (basis of disclosures + odd first period)
- 12 CFR §1026.18(b) and (e) (amount-financed + APR disclosure label)
- 12 CFR §1026.22(a)(2)-(a)(3) (APR tolerance — consumed by tolerance_check)
- HMDA Platform (sole oracle per CONTEXT D-01):
  https://github.com/cfpb/hmda-platform
"""

from __future__ import annotations

import math
import re
import warnings
from datetime import date  # noqa: TC003  # used at runtime by _compute_odd_first_period_fraction
from decimal import Decimal, localcontext
from typing import Any, Literal

import numpy_financial as npf
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.models import Loan, Money  # noqa: TC001  # Pydantic resolves field annotations at runtime
from lib.money import MONEY_CONTEXT, quantize_cents, quantize_rate


def _decimal_pow(base: Decimal, exponent: Decimal) -> Decimal:
    """Compute base ** exponent via Decimal.exp(Decimal.ln(base) * exponent).

    Native Decimal.__pow__ requires integer exponents; we route through
    ln/exp for fractional exponents (the (1+i)^(-t-f) terms in the Reg Z
    Appendix J unit-period equation), preserving MONEY_CONTEXT.prec=28.

    D-13 (locked): negative-base inputs raise ValueError (mathematically
    undefined for fractional exponents in the reals). Pinned by sibling
    test ``test_decimal_pow_fractional_exponent_correctness`` (Wave 5).
    """
    if base <= Decimal("0"):
        raise ValueError(f"_decimal_pow requires positive base; got {base}")
    with localcontext(MONEY_CONTEXT):
        return (base.ln() * exponent).exp()


def _compute_odd_first_period_fraction(
    origination: date,
    first_payment: date,
    day_count: Literal["30/360", "actual/365", "actual/actual"],
) -> Decimal:
    """Return f per Reg Z §1026.17(c)(4) + Appendix J §(b)(5)(iii).

    For a "long" first period (first_payment more than one unit period after
    origination), the fractional component is the days-beyond-standard
    expressed as a fraction of one unit period in the chosen day-count.

    Day-count formulas (RESEARCH §Q(e)):
      - "30/360":         f = (days - 30) / 30
      - "actual/365":     f = (days - 365/12) / (365/12)        # ~30.4167-day month
      - "actual/actual":  f = (days - actual_unit_days) / actual_unit_days
                          where actual_unit_days = days from origination to
                          origination + relativedelta(months=1) (handles
                          month-end edges per project-wide D-07 dateutil idiom).

    Returns:
      Decimal in [-1, 1):
        - f = 0 when first_payment is exactly one unit period after origination
        - f > 0 (long first period) is the LONG case — the only one
          cross-validated in v1
        - f < 0 (short first period) is mathematically valid (Reg Z math
          supports it via the (1 + f*i) factor) but NOT cross-validated
          in v1 — engine accepts; caller is responsible for understanding

    Raises:
      ValueError: if first_payment < origination (negative odd period —
                  RESEARCH OPEN Q1 deferred to v2 per Phase 7 scope)
      ValueError: if f >= 1 (the odd period is one full unit period or
                  longer — caller should insert an extra t=1 advance
                  instead of stretching the first period into the
                  fractional-period model)
      ValueError: if day_count is not one of the three supported values

    D-15 (locked): Literal accepts {"30/360", "actual/365", "actual/actual"}
    matching APRRequest.day_count.
    D-16 (locked): return value in [-1, 1); short cases (negative f) accepted
    by the engine but not cross-validated in v1.
    D-18 (locked): "small differences" (< 7 days for monthly) per
    §1026.17(c)(4) are NOT auto-zeroed by the engine — the engine reports
    the exact fraction and lets the U-equation use it.
    """
    if first_payment < origination:
        raise ValueError(
            f"first_payment ({first_payment}) must be >= origination ({origination}); "
            f"negative odd first period not supported in Phase 7"
        )
    days = (first_payment - origination).days
    with localcontext(MONEY_CONTEXT):
        if day_count == "30/360":
            unit_days = Decimal("30")
            f = (Decimal(days) - unit_days) / unit_days
        elif day_count == "actual/365":
            unit_days = Decimal("365") / Decimal("12")  # ~30.4167-day month
            f = (Decimal(days) - unit_days) / unit_days
        elif day_count == "actual/actual":
            # Use python-dateutil relativedelta(months=1) to compute the actual
            # number of days in the unit period anchored at origination
            # (handles month-end edges per project-wide D-07 dateutil idiom).
            actual_unit_end = origination + relativedelta(months=1)
            actual_unit_days = Decimal((actual_unit_end - origination).days)
            f = (Decimal(days) - actual_unit_days) / actual_unit_days
        else:
            raise ValueError(f"unsupported day_count: {day_count!r}")

        if f >= Decimal("1"):
            raise ValueError(
                f"odd first period >= 1 unit period (days={days}, day_count={day_count!r}); "
                f"caller should insert an extra t=1 advance instead of stretching the "
                f"first period into the fractional-period model"
            )
        return f


def _unit_period_equation(
    advances: list[AdvanceScheduleEntry],
    payments: list[PaymentScheduleEntry],
    i: Decimal,
) -> Decimal:
    """Reg Z Appendix J §(b): f(i) = sum_advances - sum_payments (PV at rate i).

    Each advance/payment uses the (1 + f·i)·(1+i)^(-t) form (simple interest
    within the fractional period; compound between full periods). Returns
    f(i) — zero at the converged APR.

    Each payment-schedule block expands to its constituent k=0..periods-1
    payments at unit-period offsets ``starting_unit_period + k``. The
    block's ``unit_period_fraction`` (long odd first period per Reg Z
    §1026.17(c)(4)) applies ONLY to the first payment in the block (k=0);
    subsequent payments are regular (g=0).

    Pure Decimal arithmetic under MONEY_CONTEXT (D-09); never mixes float.
    """
    with localcontext(MONEY_CONTEXT):
        one = Decimal("1")
        adv_sum = Decimal("0")
        for a in advances:
            t = Decimal(a.unit_period_offset)
            f = a.unit_period_fraction
            adv_sum += a.amount * (one + f * i) * _decimal_pow(one + i, -t)
        pmt_sum = Decimal("0")
        for p in payments:
            for k in range(p.periods):
                s = Decimal(p.starting_unit_period + k)
                g = p.unit_period_fraction if k == 0 else Decimal("0")
                pmt_sum += p.amount * (one + g * i) * _decimal_pow(one + i, -s)
        return adv_sum - pmt_sum


def _derivative(
    advances: list[AdvanceScheduleEntry],
    payments: list[PaymentScheduleEntry],
    i: Decimal,
) -> Decimal:
    """Closed-form f'(i) for the Reg Z Appendix J unit-period equation.

    Per RESEARCH §Q(c), differentiating
        f(i) = sum A*(1+f*i)*(1+i)^(-t) - sum P*(1+g*i)*(1+i)^(-s)
    yields
        f'(i) = sum A*[f*(1+i)^(-t) - (1+f*i)*t*(1+i)^(-t-1)]
              - sum P*[g*(1+i)^(-s) - (1+g*i)*s*(1+i)^(-s-1)]

    Pure Decimal arithmetic under MONEY_CONTEXT (D-09); never mixes float.
    """
    with localcontext(MONEY_CONTEXT):
        one = Decimal("1")
        adv_d = Decimal("0")
        for a in advances:
            t = Decimal(a.unit_period_offset)
            f = a.unit_period_fraction
            term1 = a.amount * f * _decimal_pow(one + i, -t)
            term2 = a.amount * (one + f * i) * t * _decimal_pow(one + i, -t - one)
            adv_d += term1 - term2
        pmt_d = Decimal("0")
        for p in payments:
            for k in range(p.periods):
                s = Decimal(p.starting_unit_period + k)
                g = p.unit_period_fraction if k == 0 else Decimal("0")
                term1 = p.amount * g * _decimal_pow(one + i, -s)
                term2 = p.amount * (one + g * i) * s * _decimal_pow(one + i, -s - one)
                pmt_d += term1 - term2
        return adv_d - pmt_d


class APRConvergenceError(ValueError):
    """Newton-Raphson failed to converge within the 50-iteration cap (SC-3).

    Surfaced via scripts/apr_reg_z.py 6-key envelope as type='value_error',
    loc=['solver'], ctx={'class': 'APRConvergenceError', 'iterations': 50,
    'last_residual': str(...)} - Phase 4 D-13 inheritance.

    Attributes:
        iterations: How many Newton iterations ran before bailing (== MAX_ITER
                    when the cap is exceeded; smaller when f'(i) hit zero).
        last_residual: abs(f(i)) at the final iteration (Decimal dollars).
        last_i: The last periodic-rate guess before bailing.
    """

    def __init__(self, iterations: int, last_residual: Decimal, last_i: Decimal) -> None:
        self.iterations = iterations
        self.last_residual = last_residual
        self.last_i = last_i
        super().__init__(
            f"Newton-Raphson did not converge within {iterations} iterations "
            f"(ROADMAP SC-3 cap=50); last_residual={last_residual}, last_i={last_i}"
        )


def _seed_apr(
    advance_schedule: list[AdvanceScheduleEntry],
    payment_schedule: list[PaymentScheduleEntry],
) -> Decimal:
    """Seed Newton-Raphson via npf.rate treating loan as a regular transaction.

    Per APR-02: treat as if every advance were a single t=0 net principal
    and every payment were the average. ``numpy_financial.rate`` returns a
    float; cast through ``Decimal(str(...))`` exactly ONCE at the boundary
    (D-11). The Newton iteration is pure Decimal thereafter.

    Fallback chain (RESEARCH §Q(c)):
      1. If npf.rate returns NaN, +/-inf, negative, or > 1, treat as
         out-of-range and fall through.
      2. Nominal rate-of-return: total_interest / pv / n_total
         (assumes payments > advances; gives a positive seed proportional
         to the average per-period interest accrual).
      3. Last-resort 0.005 (~6% annualized) when pv <= 0 or n_total <= 0
         (degenerate inputs that the cross-field validators should already
         have rejected, but defense-in-depth).
    """
    pv_float = float(sum(a.amount for a in advance_schedule))
    total_pmt_float = float(sum(p.amount * p.periods for p in payment_schedule))
    n_total = sum(p.periods for p in payment_schedule)
    if pv_float <= 0 or n_total <= 0:
        return Decimal("0.005")
    pmt_avg_float = total_pmt_float / n_total
    try:
        seed_float = float(
            npf.rate(nper=n_total, pmt=-pmt_avg_float, pv=pv_float, fv=0),
        )
        if math.isnan(seed_float) or math.isinf(seed_float) or seed_float < 0 or seed_float > 1:
            raise ValueError("npf.rate seed out of range")
        return Decimal(str(seed_float))
    except (ValueError, ZeroDivisionError):
        # Fallback: nominal rate-of-return from total interest paid
        total_interest = total_pmt_float - pv_float
        if total_interest <= 0:
            return Decimal("0.005")
        return Decimal(str(total_interest / pv_float / n_total))


class AdvanceScheduleEntry(BaseModel):
    """One advance in the loan disbursement schedule (Reg Z Appendix J §(b)(2)).

    The unit-period equation models each advance Aⱼ as occurring at
    `unit_period_offset + unit_period_fraction` whole-plus-fractional
    unit periods after t=0. For the standard single-disbursement mortgage
    every advance has unit_period_offset=0 and unit_period_fraction=0
    (the t=0 advance — see APRRequest D-06 invariant).

    Construction loans / draw-down HELOCs may emit multiple entries with
    increasing offsets. Phase 7 v1 oracle (HMDA Platform) covers
    single-advance only; multi-advance is on the v2 backlog
    (07-CONTEXT.md "Deferred Ideas").
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    unit_period_offset: int = Field(
        ge=0,
        description="Whole unit periods between t=0 and the advance",
    )
    unit_period_fraction: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        lt=Decimal("1"),
        description="Fractional unit period in [0, 1) for advances mid-period",
    )
    amount: Money


class PaymentScheduleEntry(BaseModel):
    """One regular-payment block in the schedule.

    A 30-year monthly mortgage with one payment level is a single entry
    with periods=360. Construction loans with payment changes mid-term
    use multiple entries (e.g., interest-only draw period followed by a
    fully-amortizing block).

    The unit-period equation evaluates each payment Pₖ at
    `starting_unit_period + (k-1) + unit_period_fraction` for
    k = 1..periods. unit_period_fraction handles long odd first periods
    per Reg Z §1026.17(c)(4); v1 cross-validates only f ∈ [0, 1) (long
    cases), but the type surface accepts f=0 (regular case) which is the
    default.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    starting_unit_period: int = Field(
        ge=1,
        description="The unit-period index of the first payment in this block (1-indexed)",
    )
    periods: int = Field(
        ge=1,
        description="Number of unit periods this block spans (e.g., 360 for 30yr monthly)",
    )
    amount: Money
    unit_period_fraction: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        lt=Decimal("1"),
        description="Fractional unit period in [0, 1) for odd first period (long case only in v1)",
    )


class APRRequest(BaseModel):
    """Reg Z Appendix J APR-solve request (boundary model).

    See `references/apr-reg-z.md` for the unit-period model + day-count
    conventions. Pydantic v2 strict + frozen + forbid per Phase 1 D-08
    (mortgage-ops project-wide convention; D-01 above).

    Cross-field invariants (LOCKED, see D-06):
      - advance_schedule MUST contain at least one entry with
        unit_period_offset=0 AND unit_period_fraction=Decimal("0") (the
        t=0 advance — Reg Z Appendix J §(b)(2)).
      - payment_schedule.periods summed over all entries MUST be >= 1
        (otherwise the U-equation has no payment side).

    Reverse-mode "amount-financed only" callers (the standard
    single-disbursement mortgage) pass:

        AdvanceScheduleEntry(
            unit_period_offset=0,
            amount=loan.principal - finance_charges,
        )

    The engine subtracts finance_charges from loan.principal to form
    amount_financed per Reg Z §1026.18(b); D-04 makes finance_charges
    caller-supplied (no §1026.4 classifier in v1).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    finance_charges: Money = Field(
        description=(
            "Sum of §1026.4 finance charges; subtracted from loan.principal "
            "per §1026.18(b). CALLER-SUPPLIED (D-04) — engine does not "
            "classify which closing costs qualify under §1026.4."
        ),
    )
    advance_schedule: list[AdvanceScheduleEntry]
    payment_schedule: list[PaymentScheduleEntry]
    day_count: Literal["30/360", "actual/365", "actual/actual"] = "30/360"
    unit_periods_per_year: int = Field(
        default=12,
        ge=1,
        le=365,
        description="Unit periods per year (D-03; default 12 = monthly mortgage)",
    )
    odd_first_period_days: int = Field(
        default=0,
        ge=0,
        le=365,
        description=(
            "Days beyond standard unit period from origination to first payment; "
            "0 = no odd period (Reg Z §1026.17(c)(4); long case only in v1)."
        ),
    )
    disclosed_apr: Money | None = Field(
        default=None,
        description=(
            "Optional lender-disclosed APR; when set, APRResponse.tolerance_check "
            "is populated against lib.rules.reg_z.within_apr_tolerance per "
            "12 CFR §1026.22(a)(2)-(a)(3)."
        ),
    )

    @model_validator(mode="after")
    def _advance_schedule_has_t0_advance(self) -> APRRequest:
        """D-06: advance_schedule MUST have at least one entry at t=0 with f=0."""
        if not any(
            a.unit_period_offset == 0 and a.unit_period_fraction == Decimal("0")
            for a in self.advance_schedule
        ):
            raise ValueError(
                "advance_schedule MUST contain at least one advance at "
                "unit_period_offset=0 (Reg Z Appendix J §(b)(2))"
            )
        return self

    @model_validator(mode="after")
    def _payment_schedule_non_empty(self) -> APRRequest:
        """payment_schedule must sum to >= 1 unit period."""
        total_periods = sum(p.periods for p in self.payment_schedule)
        if total_periods == 0:
            raise ValueError("payment_schedule MUST sum to at least 1 period")
        return self


class APRResponse(BaseModel):
    """Result of solve_apr() (boundary model).

    summary always contains the literal text "estimated APR" (ROADMAP
    SC-4) AND must NOT contain a bare "APR" word outside the allowed
    phrases ("estimated APR", "APR tolerance"). Both halves are enforced
    at the Pydantic boundary by D-05's @model_validator —
    constructing APRResponse(summary="APR is 7%") raises ValidationError
    even from the engine, not just from the CLI surface.

    Surfaced fields (D-05):
      estimated_apr   — fractional APR in [0, 1] quantized to 6 decimal
                        places (matches Phase 5 D-14 Rate quantization).
      iterations      — Newton iterations to converge; ROADMAP SC-3 caps
                        at 50 (D-07: enforced at this boundary).
      final_residual  — abs(f(i_final)) in dollars at convergence; the
                        D-06 dual-criterion residual sanity-check value
                        (informational; convergence test is internal to
                        solve_apr).
      summary         — user-facing string with the literal "estimated
                        APR" phrase (D-05 / SC-4).
      tolerance_check — populated only when APRRequest.disclosed_apr was
                        supplied; dict shape (D-08, kept loose for Phase
                        8/12 extensibility):
                          {
                            "within_tolerance": bool,
                            "tolerance_used": Decimal,    # 0.00125 regular
                                                          # 0.0025 irregular
                            "regulation": "12 CFR §1026.22(a)(2)",
                          }
                        Wave 4 (CLI) will mirror this docstring shape in
                        scripts/apr_reg_z.py --help.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    estimated_apr: Decimal = Field(
        strict=True,
        max_digits=7,
        decimal_places=6,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Fractional APR in [0, 1] quantized to 6 decimal places (Phase 5 D-14)",
    )
    iterations: int = Field(
        ge=1,
        le=50,
        description="Newton iterations to converge (ROADMAP SC-3 cap; D-07)",
    )
    final_residual: Money = Field(
        description="abs(f(i_final)) — dollar residual at convergence (D-06 dual criterion)",
    )
    summary: str = Field(
        min_length=10,
        description=(
            "User-facing summary; MUST contain literal 'estimated APR' (ROADMAP SC-4) "
            "and MUST NOT contain bare 'APR' (only 'estimated APR' or 'APR tolerance' allowed)."
        ),
    )
    tolerance_check: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Populated when APRRequest.disclosed_apr supplied; cites "
            "12 CFR §1026.22(a)(2)-(a)(3). dict shape kept loose (D-08) for "
            "Phase 8/12 extensibility."
        ),
    )

    @model_validator(mode="after")
    def _summary_contains_literal_estimated_apr(self) -> APRResponse:
        """ROADMAP SC-4 / APR-06 / D-05: literal 'estimated APR' MUST appear; bare 'APR' MUST NOT.

        Strips the allowed phrases ('estimated APR') and then scans for any
        bare 'APR' word; allows 'APR tolerance' (the regulatory phrase
        used in lib.rules.reg_z.within_apr_tolerance docstrings).
        """
        if "estimated APR" not in self.summary:
            raise ValueError(
                f"APRResponse.summary MUST contain literal 'estimated APR' per "
                f"ROADMAP SC-4; got: {self.summary!r}"
            )
        # Strip the allowed literal then check for any bare 'APR' word
        stripped = self.summary.replace("estimated APR", "")
        # Allow 'APR tolerance' (regulatory phrase) but not bare 'APR'
        bare_apr = re.search(r"\bAPR\b(?!\s*tolerance)", stripped)
        if bare_apr is not None:
            raise ValueError(
                f"APRResponse.summary MUST NOT contain bare 'APR' (only "
                f"'estimated APR' or 'APR tolerance' permitted); got: {self.summary!r}"
            )
        return self


TOLERANCE: Decimal = Decimal("0.00001")
"""D-09/D-10 (locked): convergence tolerance on the rate step.

125x tighter than Reg Z regular-transaction tolerance (Decimal("0.00125") =
1/8 pp) per RESEARCH §Finding 1; satisfies the ROADMAP "10x tighter than
Reg Z" goal trivially.
"""

DOLLAR_RESIDUAL: Decimal = Decimal("0.01")
"""D-10 (locked): dollar-residual sanity check (one cent).

Defense-in-depth alongside the rate tolerance: f(i) at convergence must be
within one cent of zero, otherwise we treat the rate as "stalled, residual
huge" and continue iterating.
"""

MAX_ITER: int = 50
"""D-12 (locked): hard cap on Newton iterations per ROADMAP SC-3.

Breach raises APRConvergenceError; caller never sees an APRResponse with
iterations > 50 (D-07 defense in depth at the model boundary).
"""


def solve_apr(request: APRRequest) -> APRResponse:
    """Solve for the estimated APR via Newton-Raphson per Reg Z Appendix J.

    See references/apr-reg-z.md §5 for the algorithm:

      1. Seed via _seed_apr (npf.rate of regular-transaction approximation).
      2. Newton iteration in MONEY_CONTEXT (prec=28 Decimal):
            i_{n+1} = i_n - f(i_n)/f'(i_n)
      3. Convergence: abs(i_{n+1} - i_n) <= TOLERANCE
                  AND abs(f(i_{n+1})) <= DOLLAR_RESIDUAL  (D-10 dual criterion).
      4. Hard cap MAX_ITER iterations; APRConvergenceError if exceeded
         (D-12) or if f'(i) hits zero (avoids divide-by-zero).
      5. APR = quantize_rate(i_final * unit_periods_per_year)  (D-14).
      6. tolerance_check populated when request.disclosed_apr is supplied.

    Args:
        request: The APRRequest boundary model. Pre-validated by Pydantic
                 (strict + frozen + extra=forbid + cross-field invariants
                 D-06 + non-empty payment schedule).

    Returns:
        APRResponse with estimated_apr quantized to 6 decimal places,
        iterations count, final_residual (in dollars), summary string
        containing the literal 'estimated APR' (SC-4), and optional
        tolerance_check when request.disclosed_apr was supplied.

    Raises:
        APRConvergenceError: when Newton-Raphson exceeds MAX_ITER iterations
                             or when f'(i) hits exactly zero. ValueError
                             subclass; surfaced by scripts/apr_reg_z.py
                             via the Phase 4 D-13 6-key envelope.
    """
    # warnings.catch_warnings is the Phase 4 evaluate_reverse idiom (lib/affordability.py:1033);
    # Phase 7 currently emits no custom warnings, but capturing keeps the surface ready
    # for downstream phases to add warning-bearing branches without an API bump.
    f_val = Decimal("0")
    iterations = 0

    # D-17 (locked): APRRequest.odd_first_period_days is the user-friendly shortcut;
    # the engine internally rewrites the first PaymentScheduleEntry.unit_period_fraction
    # so the U-equation's (1 + g*i) factor on the first payment carries the long
    # odd first period per Reg Z §1026.17(c)(4) + Appendix J §(b)(5)(iii).
    # Advanced callers can bypass by setting unit_period_fraction directly on the
    # PaymentScheduleEntry and leaving odd_first_period_days=0 (Phase 8 stress
    # wrapper may use _compute_odd_first_period_fraction with explicit dates instead).
    payments_with_odd = list(request.payment_schedule)
    if request.odd_first_period_days > 0:
        # Wave 3 simplification: convert odd_first_period_days into a unit-period
        # fraction relative to the standard unit period. For 30/360 the standard
        # unit is 30 days; for actual/365 it is 365/12 ~= 30.4167 days; for
        # actual/actual the request lacks origination/first_payment dates here, so
        # we use 30 days as a proxy (callers needing exact actual/actual fractions
        # use _compute_odd_first_period_fraction with explicit dates and set
        # PaymentScheduleEntry.unit_period_fraction directly, leaving
        # odd_first_period_days=0).
        if request.day_count == "30/360":
            unit_days_dec = Decimal("30")
        elif request.day_count == "actual/365":
            unit_days_dec = Decimal("365") / Decimal("12")
        else:  # actual/actual — Wave 3 simplification: use 30 as proxy
            unit_days_dec = Decimal("30")
        with localcontext(MONEY_CONTEXT):
            f_odd = Decimal(request.odd_first_period_days) / unit_days_dec
        if f_odd >= Decimal("1"):
            raise ValueError(
                f"odd_first_period_days ({request.odd_first_period_days}) >= 1 unit "
                f"period (day_count={request.day_count!r}, unit_days={unit_days_dec}); "
                f"insert an extra advance entry instead of stretching the first period"
            )
        first = payments_with_odd[0]
        payments_with_odd[0] = first.model_copy(update={"unit_period_fraction": f_odd})

    with warnings.catch_warnings():
        warnings.simplefilter("always")
        with localcontext(MONEY_CONTEXT):
            i = _seed_apr(request.advance_schedule, payments_with_odd)
            # Guard against a degenerate seed that already places (1+i) <= 0 (would
            # blow up the very first _decimal_pow call). Treat as immediate
            # non-convergence rather than letting ValueError propagate raw.
            if i <= Decimal("-1"):
                raise APRConvergenceError(iterations=0, last_residual=Decimal("0"), last_i=i)
            for n in range(1, MAX_ITER + 1):
                iterations = n
                try:
                    f_val = _unit_period_equation(request.advance_schedule, payments_with_odd, i)
                    fprime = _derivative(request.advance_schedule, payments_with_odd, i)
                except ValueError as exc:
                    # _decimal_pow rejected a non-positive (1+i) base; the
                    # iterate has wandered out of the equation's domain — this
                    # is a non-convergence signal, not a programmer bug.
                    raise APRConvergenceError(
                        iterations=n, last_residual=abs(f_val), last_i=i
                    ) from exc
                if fprime == Decimal("0"):
                    raise APRConvergenceError(iterations=n, last_residual=abs(f_val), last_i=i)
                i_next = i - f_val / fprime
                if abs(i_next - i) <= TOLERANCE and abs(f_val) <= DOLLAR_RESIDUAL:
                    i = i_next
                    break
                # If the next iterate would put (1+i) at or below zero, the
                # subsequent _decimal_pow would raise; bail with APRConvergenceError
                # so callers get a clean signal rather than a raw ValueError.
                if i_next <= Decimal("-1"):
                    raise APRConvergenceError(iterations=n, last_residual=abs(f_val), last_i=i)
                i = i_next
            else:
                raise APRConvergenceError(iterations=MAX_ITER, last_residual=abs(f_val), last_i=i)

            estimated_apr = quantize_rate(i * Decimal(request.unit_periods_per_year))
            final_residual_quantized = quantize_cents(abs(f_val))

    apr_pct_str = f"{estimated_apr * Decimal('100'):.4f}"
    summary = (
        f"estimated APR: {apr_pct_str}% "
        f"(converged in {iterations} iterations, residual ${final_residual_quantized})"
    )

    tolerance_check: dict[str, Any] | None = None
    if request.disclosed_apr is not None:
        from lib.rules.reg_z import TOLERANCE_REGULAR, within_apr_tolerance

        is_within = within_apr_tolerance(
            disclosed_apr=request.disclosed_apr,
            actual_apr=estimated_apr,
            is_irregular_transaction=False,
        )
        tolerance_check = {
            "disclosed_apr": str(request.disclosed_apr),
            "estimated_apr": str(estimated_apr),
            "within_tolerance": is_within,
            "tolerance_used": str(TOLERANCE_REGULAR),
            "regulation": "12 CFR §1026.22(a)(2)",
        }

    return APRResponse(
        estimated_apr=estimated_apr,
        iterations=iterations,
        final_residual=final_residual_quantized,
        summary=summary,
        tolerance_check=tolerance_check,
    )
