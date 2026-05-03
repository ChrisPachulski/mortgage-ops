"""Phase 7 Estimated APR — Reg Z Appendix J Newton-Raphson solver (Pydantic boundary).

Phase 7 builds an "estimated APR" engine on top of Phase 3 amortization. Wave 1
(this plan) ships ONLY the Pydantic v2 boundary models (APRRequest,
AdvanceScheduleEntry, PaymentScheduleEntry, APRResponse) plus a `solve_apr`
stub that raises NotImplementedError. Wave 2 (Plan 07-02) fills the
Newton-Raphson body. Wave 4 (Plan 07-04) ships the JSON-in / JSON-out CLI
at scripts/apr_reg_z.py.

Phase-7 consumer note: lib/rules/reg_z.py:43-47 already references this
module — `within_apr_tolerance(disclosed, actual, is_irregular)` is the
predicate Phase 7 calls when APRRequest.disclosed_apr is supplied (see
APRResponse.tolerance_check). Phase 7 keeps the "estimated APR" label
because mortgage-ops does not make commercial Reg Z disclosures (ROADMAP
SC-4); the solver is a calc, not a disclosure.

Requirements covered (Plan 07-01 partial; full closure across Waves 2-7):
  APR-01: lib/apr.py Newton-Raphson solver against Reg Z Appendix J
          unit-period equation (this plan: model surface + stub; Wave 2 body).
  APR-02: Newton-Raphson seeded from npf.rate (Wave 2).
  APR-03: Convergence tolerance Decimal("0.00001") (Wave 2).
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
from decimal import Decimal, localcontext
from typing import Any, Literal

import numpy_financial as npf
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.models import Loan, Money  # noqa: TC001  # Pydantic resolves field annotations at runtime
from lib.money import MONEY_CONTEXT


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


def solve_apr(request: APRRequest) -> APRResponse:
    """Solve for the estimated APR via Newton-Raphson (Wave 2 implements body).

    See references/apr-reg-z.md §5 for the algorithm: seed from
    `numpy_financial.rate(...)` (regular-transaction approximation), then
    iterate `i_{n+1} = i_n - f(i_n) / f'(i_n)` against the Reg Z Appendix
    J unit-period equation in pure Decimal arithmetic until BOTH
    `abs(i_{n+1} - i_n) <= Decimal("0.00001")` AND
    `abs(f(i_{n+1})) <= Decimal("0.01")` (D-06 dual criterion). Cap at
    50 iterations (ROADMAP SC-3) — raise APRConvergenceError before
    constructing APRResponse if cap exceeded (D-07 defense in depth).

    Args:
        request: The APRRequest boundary model. Pre-validated by Pydantic
                 (strict + frozen + extra=forbid + cross-field invariants
                 D-06 + non-empty payment schedule).

    Returns:
        APRResponse with estimated_apr quantized to 6 decimal places,
        iterations count, final_residual, summary string containing the
        literal 'estimated APR' (SC-4), and optional tolerance_check
        when request.disclosed_apr was supplied.

    Raises:
        NotImplementedError: Wave 2 (Plan 07-02) ships the implementation.
    """
    raise NotImplementedError(
        "Wave 2 (Plan 07-02) implements the Newton-Raphson body; "
        "Wave 1 (Plan 07-01) ships only the boundary models."
    )
