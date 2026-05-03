"""Refinance NPV (rate-and-term + cash-out) from the borrower's perspective.

Sign convention: outflows negative, savings positive. See references/refi-npv.md
(REFI-09 / SC-5) for full derivation, discount-rate-selection guidance, and
breakeven definitions.

Phase 6 is the FIRST consumer of `numpy_financial.npv` for refinance net-present-
value evaluation. It composes Phase 1 models (lib.models — Loan/Money/Rate),
Phase 3 amortization (lib.amortize.build_schedule for old-residual + new-loan
schedules), and Phase 5's promoted helper `lib.money.quantize_rate` (D-14) into a
6-model Pydantic v2 surface plus the public `evaluate(req)` discriminated-union
dispatcher.

Architecture map (mirrors lib/affordability.py shape):
  evaluate_rate_and_term(req) — rate-and-term refi NPV (Plan 06-02 body)
  evaluate_cash_out(req)      — cash-out refi NPV + tax-shield (Plan 06-03 body)
  evaluate(req)               — public dispatcher (Plan 06-04 body)
  Helper layer (Plans 06-02..06-04 ship these private functions):
    _compute_npv, _compute_breakeven_simple, _compute_breakeven_npv,
    _build_old_loan_residual, _build_cashflow_stream

This plan (06-01) ships ONLY the Pydantic v2 type contract + the SC-4 sign-
validator on RefiCashflow + cross-plan stub bodies for evaluate_*. Plans 06-02 /
06-03 / 06-04 add bodies to these stubs (Phase 2 D-08 cross-plan stub idiom).

LOCKED DECISION - D-01 (no new external deps; per 06-RESEARCH.md):
  Phase 6 introduces NO new external dependencies. `numpy_financial.npv` is the
  canonical NPV primitive (already pinned at 1.0.0). `pyxirr` is deferred to
  Phase 11 SUBA-02 (refi-npv-agent multi-offer ranking) per REFI-04 ("Optional
  pyxirr integration"). Documented in `evaluate` docstring with `# Phase 11
  migration note`.

LOCKED DECISION - D-02 (module structure mirrors lib/affordability.py):
  Leaf models → _CommonRefiFields base → discriminated union RefiRequest with
  refi_kind discriminator → RefiResponse → private helpers → public evaluate()
  dispatcher. Pattern lifted from lib/affordability.py:436-540.

LOCKED DECISION - D-03 (RefiCashflow shape; per 06-RESEARCH §"(e)"):
  RefiCashflow has: period: int (ge=0), direction: Literal["outflow","inflow"],
  amount: Decimal (max_digits=14, decimal_places=2; NOT Money — Money's ge=0
  would block negative outflows), kind: Literal[5 values] for citation-coverage,
  and an @model_validator(mode="after") `_direction_sign_consistency` that
  rejects sign-mismatched constructions at Pydantic boundary. Zero accepted in
  either direction (D-14 — no sign hazard). The kind Literal lets
  test_refi_cashflow_kind_citation_coverage assert each value appears in ≥1
  fixture (mirrors Phase 5's applied_cap Literal coverage convention).

LOCKED DECISION - D-04 (borrower-perspective sign convention; ROADMAP SC-5):
  outflows negative, savings positive. Documented in (1) RefiCashflow validator
  error messages, (2) lib/refinance.py module docstring (this block + opening
  paragraph), (3) references/refi-npv.md (SC-5), (4) scripts/refi_npv.py --help
  epilog (Plan 06-04). Belt-and-suspenders D-16 surfacing.

LOCKED DECISION - D-05 (discount_rate_annual REQUIRED; no defaults):
  RefiRequest.discount_rate_annual is REQUIRED. No default. Documented in
  references/refi-npv.md with 3 plausible defaults (borrower marginal opportunity
  cost / risk-free rate / OLD loan rate) and the recommended choice (borrower
  after-tax marginal opportunity cost; 5-7% typical). Mirrors Phase 4 D-12 (max_dti
  caller-supplied no-default discipline).

LOCKED DECISION - D-06 (NPV-based breakeven via cumulative-NPV scan, NOT npf.irr):
  numpy_financial.irr is BROKEN (bug #131 — arch-dependent). Phase 6 MUST NOT use
  it. Algorithm: for n in 1..N, compute npv(rate, cashflows[0:n+1]); first n where
  cumulative ≥ 0 wins. If never ≥ 0, return None with status "never_breaks_even".
  Plan 06-02 ships `_compute_breakeven_npv`.

LOCKED DECISION - D-07 (pyxirr deferred to Phase 11 SUBA-02):
  Phase 6 v1 uses numpy_financial.npv exclusively. pyxirr deferral is documented
  in `evaluate` docstring with a `# Phase 11: see pyxirr migration note` marker
  so test_pyxirr_deferred_to_phase11_documented (Plan 06-05 flip) passes.

LOCKED DECISION - D-08 (PMI/MIP recalc OUT of v1 refi scope):
  Caller responsible for `new_loan_monthly_pi_override` if cash-out LTV breaches
  a PMI/MIP threshold. references/refi-npv.md §7 documents the carve-out.

LOCKED DECISION - D-09 (after-tax mode opt-in):
  `after_tax_mode: bool = False`, `marginal_tax_rate: Rate | None = None`,
  `filing_status: Literal["single","mfj","mfs","hoh"] | None = None`. When True,
  all three required (cross-field validator `_validate_common`). Cites
  lib.rules.irs_pub936.qualified_loan_limit (RUL-11) for the $750k post-2017 /
  $1M grandfathered cap. Plan 06-03 ships the engine; Plan 06-01 ships the
  validator.

LOCKED DECISION - D-10 (caller PMI/MIP override field):
  Cash-out scenarios where caller knows the new monthly P&I includes PMI/MIP that
  v1 doesn't recalc: caller passes `new_loan_monthly_pi_override: Money | None
  = None`. Engine uses override when supplied; otherwise computes via
  build_schedule(new_loan).monthly_pi.

LOCKED DECISION - D-11 (analysis_horizon_months optional):
  `analysis_horizon_months: int | None = None`. None = use new_loan.term_months.
  When supplied, cashflow list truncated to t=0..analysis_horizon_months. Used
  by D-13 negative-NPV fixture to overpower 200bps rate drop with $5k closing
  costs (Oracle 2; horizon=12 simulates short borrower tenure).

LOCKED DECISION - D-12 (closing costs paid out-of-pocket in v1):
  No financing into loan. Caller computes new principal accordingly. Documented
  in references/refi-npv.md carve-out section.

LOCKED DECISION - D-13 (negative-NPV fixture uses analysis_horizon_months=12):
  Per Oracle 2: same 200bps rate drop + $5k closing + horizon=12 → NPV ≈ -$741.
  Plan 06-05 ships the fixture.

LOCKED DECISION - D-14 (sign-validator accepts amount=0 in either direction):
  Zero cashflows have no sign hazard; the _direction_sign_consistency validator
  fires only on strict-sign mismatch (outflow with amount > 0 or inflow with
  amount < 0). Pinned by test_refi_cashflow_zero_accepted_either_dir (Plan 06-01
  flip).

LOCKED DECISION - D-15 (closing costs as top-level request field):
  RefiRequest exposes `closing_costs: Money` at the top level. Engine constructs
  the RefiCashflow(period=0, direction="outflow", amount=-closing_costs,
  kind="closing_costs") internally. Caller does NOT pass cashflow list directly —
  cashflows are an OUTPUT (audit trail on RefiResponse), not an input.

LOCKED DECISION - D-16 (sign-convention citation surfaces — belt-and-suspenders):
  (1) RefiCashflow validator messages cite references/refi-npv.md, (2) this
  module docstring opens with "outflows negative, savings positive" + cites the
  doc, (3) references/refi-npv.md headlines the phrase verbatim per SC-5 (Plan
  06-06), (4) scripts/refi_npv.py --help epilog includes the doc cite per SC-5
  (Plan 06-04). Pinned by test_lib_refinance_module_docstring_cites (Plan 06-01
  flip).

Phase 11 migration note: when SUBA-02 ships the refi-npv-agent multi-offer
ranking, evaluate() may grow a sibling `evaluate_batch(reqs: Sequence[RefiRequest])`
that uses pyxirr.npv (Rust+PyO3 backend; 10-50x faster on N≥1000 scenarios) for
batch ranking. Phase 6 v1's single-scenario surface uses numpy_financial.npv
exclusively to preserve Decimal discipline (numpy-financial 1.0.0 returns Decimal
when fed Decimal; pyxirr's f64 backend would lose money-Decimal precision).

Stale-warning expected behavior (inherited from Phase 4):
  data/reference/fha-mip-rates.yml + va-residual-income.yml fire
  StaleReferenceWarning when after-tax-mode invokes lib.rules.irs_pub936.
  Surfaced via warnings.catch_warnings() into RefiResponse.warnings list (Plan
  06-03).
"""

from __future__ import annotations

from datetime import date  # noqa: F401  (reserved for Plan 06-02/06-03 schedule date math)
from decimal import ROUND_CEILING, Decimal
from typing import TYPE_CHECKING, Annotated, Final, Literal

import numpy_financial as npf
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.amortize import build_schedule
from lib.models import (
    Loan,
    Money,
    Rate,
)
from lib.money import quantize_cents, quantize_rate

if TYPE_CHECKING:
    from collections.abc import Sequence  # noqa: F401  (reserved for Plan 06-04 dispatcher hints)


# ---------------------------------------------------------------------------
# Module-level constants (D-04 + D-05 documentation aids)
# ---------------------------------------------------------------------------

SIGN_CONVENTION_CITATION: Final[str] = "references/refi-npv.md (D-04)"
"""Single source of truth for the sign-convention citation string used in
RefiCashflow validator error messages (D-16 belt-and-suspenders surface)."""

BREAKEVEN_NEVER_SENTINEL: Final[None] = None
"""When NPV-based or simple breakeven never crosses zero within horizon.
Plan 06-02's _compute_breakeven_simple / _compute_breakeven_npv return this
sentinel (None) alongside a status Literal that distinguishes the failure mode
("no_savings", "zero_costs", "never_breaks_even"). Mirrors Phase 5's
final_payment_adjusted bool + applied_cap Literal "tagged-status" idiom."""


# ---------------------------------------------------------------------------
# RefiCashflow (D-03) — the SC-4 sign-validator anchor
# ---------------------------------------------------------------------------


class RefiCashflow(BaseModel):
    """A single refi cashflow with sign-direction enforced by Pydantic.

    REFI sign convention (D-04; references/refi-npv.md):
      outflows negative (closing costs, additional payment when new_pi > old_pi)
      inflows positive (savings, cash-out proceeds, tax shield)

    The model rejects mismatches at construction time (SC-4): an outflow with
    a positive amount or an inflow with a negative amount raises ValidationError.
    Zero is accepted in either direction (a zero cashflow has no sign hazard;
    D-14).

    `amount` is raw `Decimal` (NOT lib.models.Money) because Money is ge=0,
    which would reject negative outflow amounts at the type layer BEFORE the
    @model_validator can run. We constrain via Field(strict=True, max_digits=14,
    decimal_places=2) to inherit money discipline without the ge=0 floor.

    The `kind` Literal lets test_refi_cashflow_kind_citation_coverage assert each
    value appears in ≥1 committed fixture (Plan 06-05 flip; mirrors Phase 5's
    applied_cap Literal coverage convention).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    period: int = Field(ge=0)
    """Period index. t=0 allowed for closing-costs at origination AND for cash-out
    proceeds at origination."""

    direction: Literal["outflow", "inflow"]
    """Direction of the cashflow from the borrower's perspective. outflow = money
    leaving the borrower (closing costs, additional payment); inflow = money
    arriving (savings, cash-out proceeds, tax shield)."""

    amount: Decimal = Field(strict=True, max_digits=14, decimal_places=2)
    """Signed Decimal amount. NOT Money (ge=0 would block negatives). The
    @model_validator below enforces sign-direction consistency at construction."""

    kind: Literal[
        "closing_costs",
        "cash_proceeds",
        "monthly_savings",
        "monthly_payment_delta",
        "tax_shield",
    ]
    """Category of the cashflow. tax_shield is after-tax mode only (D-09).
    Phase 6 fixtures collectively cover every value (D-03 citation-coverage)."""

    @model_validator(mode="after")
    def _direction_sign_consistency(self) -> RefiCashflow:
        """Reject sign-mismatched constructions per D-04 (SC-4).

        outflow with amount > 0  → ValueError (outflows must be non-positive)
        inflow with amount < 0   → ValueError (inflows must be non-negative)
        amount == 0              → accepted in either direction (D-14 no sign hazard)
        """
        if self.direction == "outflow" and self.amount > Decimal("0"):
            raise ValueError(
                f"D-04 sign-convention violation: outflow cashflow must have "
                f"non-positive amount (got {self.amount}); outflows negative, "
                f"savings positive (see {SIGN_CONVENTION_CITATION})"
            )
        if self.direction == "inflow" and self.amount < Decimal("0"):
            raise ValueError(
                f"D-04 sign-convention violation: inflow cashflow must have "
                f"non-negative amount (got {self.amount}); outflows negative, "
                f"savings positive (see {SIGN_CONVENTION_CITATION})"
            )
        return self


# ---------------------------------------------------------------------------
# RefiBreakeven sub-model (SC-2 dual-reporting shape)
# ---------------------------------------------------------------------------


class RefiBreakeven(BaseModel):
    """Dual-form breakeven reporting per SC-2 + REFI-03.

    simple_months / npv_months may be None when breakeven never occurs; the
    paired *_status Literal distinguishes the failure mode.

    simple = ceil(closing_costs / monthly_savings); fails when monthly_savings
    <= 0 ("no_savings") or when closing_costs == 0 ("zero_costs").

    npv = first n in 1..N where cumulative NPV ≥ 0 (D-06 cumulative scan, NOT
    npf.irr); fails ("never_breaks_even") when no n satisfies the condition.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    simple_months: int | None
    simple_status: Literal["ok", "no_savings", "zero_costs"]
    npv_months: int | None
    npv_status: Literal["ok", "never_breaks_even"]


# ---------------------------------------------------------------------------
# _CommonRefiFields base (D-02 — not instantiated directly)
# ---------------------------------------------------------------------------


class _CommonRefiFields(BaseModel):
    """Shared base fields for RateAndTermRefiRequest + CashOutRefiRequest. Not
    instantiated directly; the two concrete request models extend this with their
    refi_kind discriminator + variant-specific fields.

    Mirrors lib/affordability.py::_CommonRequestFields shape (Phase 4 D-14).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    old_loan_balance: Money
    """Remaining balance on the OLD (existing) loan as of the refi date."""

    old_annual_rate: Rate
    """Note rate on the OLD loan (used to construct the residual schedule)."""

    old_remaining_months: int = Field(ge=1, le=600)
    """Months remaining on the OLD loan as of the refi date."""

    new_annual_rate: Rate
    """Note rate on the NEW loan (the refi)."""

    new_term_months: int = Field(ge=1, le=600)
    """Term of the NEW loan in months. Common: 360 (30y) or 180 (15y)."""

    closing_costs: Money
    """Closing costs paid out-of-pocket (D-12; v1 does NOT finance into loan).
    Engine constructs RefiCashflow(period=0, direction='outflow',
    amount=-closing_costs, kind='closing_costs') internally per D-15."""

    discount_rate_annual: Rate
    """REQUIRED per D-05. No default. Caller-supplied. See references/refi-npv.md
    for guidance on the three plausible defaults (borrower marginal opportunity
    cost / risk-free rate / OLD loan rate)."""

    analysis_horizon_months: int | None = Field(default=None, ge=1, le=600)
    """Optional cashflow horizon (D-11). None = use new_term_months. When
    supplied, cashflow list truncated to t=0..analysis_horizon_months. D-13
    negative-NPV fixture uses 12 to overpower 200bps rate drop + $5k closing."""

    # D-09 after-tax mode (defaults to off; cross-field validator enforces
    # marginal_tax_rate + filing_status when True)
    after_tax_mode: bool = False
    """Opt-in after-tax NPV mode per D-09. When True, marginal_tax_rate AND
    filing_status MUST be supplied (cross-field validator). Engine adds
    tax_shield cashflows derived from lib.rules.irs_pub936.qualified_loan_limit
    (RUL-11)."""

    marginal_tax_rate: Rate | None = None
    """Borrower's marginal federal tax rate (e.g., 0.24 for the 24% bracket).
    REQUIRED when after_tax_mode=True (D-09)."""

    filing_status: Literal["single", "mfj", "mfs", "hoh"] | None = None
    """IRS filing status. REQUIRED when after_tax_mode=True (D-09); drives the
    qualified-loan-limit lookup ($750k post-2017 / $1M grandfathered)."""

    has_grandfathered_debt: bool = False
    """Whether the borrower has pre-TCJA grandfathered mortgage debt (raises the
    qualified-loan cap from $750k to $1M per IRS Pub 936). Forwarded to
    qualified_loan_limit when after_tax_mode=True."""

    # D-10 override for cash-out PMI/MIP cases v1 doesn't recalc
    new_loan_monthly_pi_override: Money | None = None
    """Optional override for new-loan monthly P&I (D-10). When supplied, engine
    uses this value instead of computing via build_schedule(new_loan).monthly_pi.
    Use this when cash-out LTV breaches a PMI/MIP threshold and the caller has
    externally computed the true monthly payment including MI."""


def _validate_common(req: _CommonRefiFields) -> _CommonRefiFields:
    """Cross-field validators applied to both RateAndTermRefiRequest +
    CashOutRefiRequest.

    - When after_tax_mode=True, marginal_tax_rate AND filing_status MUST be
      supplied (D-09; otherwise the after-tax tax-shield cashflow stream cannot
      be computed).
    - When after_tax_mode=False, marginal_tax_rate AND filing_status SHOULD be
      None — currently not enforced (warn-but-allow handled in Plan 06-03 engine
      body, not at construction time, so callers can carry tax fields across
      mode toggles without re-constructing the request).
    """
    if req.after_tax_mode and (req.marginal_tax_rate is None or req.filing_status is None):
        raise ValueError(
            "after_tax_mode=True requires both marginal_tax_rate and filing_status "
            "(D-09; cites lib.rules.irs_pub936.qualified_loan_limit / RUL-11; "
            "see references/refi-npv.md §'After-Tax Optional Mode')"
        )
    return req


# ---------------------------------------------------------------------------
# RateAndTermRefiRequest (D-02 leaf model — refi_kind="rate_and_term")
# ---------------------------------------------------------------------------


class RateAndTermRefiRequest(_CommonRefiFields):
    """Rate-and-term refi: new principal == old_loan_balance (no equity
    extraction; no cash-out). REFI-01 anchor.

    Plan 06-02 ships evaluate_rate_and_term(req) which consumes this shape and
    returns a RefiResponse with refi_kind='rate_and_term'.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    refi_kind: Literal["rate_and_term"] = "rate_and_term"

    @model_validator(mode="after")
    def _validate_rate_and_term(self) -> RateAndTermRefiRequest:
        _validate_common(self)
        return self


# ---------------------------------------------------------------------------
# CashOutRefiRequest (D-02 leaf model — refi_kind="cash_out")
# ---------------------------------------------------------------------------


class CashOutRefiRequest(_CommonRefiFields):
    """Cash-out refi: new principal = old_loan_balance + cash_out_amount
    (equity extraction). REFI-02 anchor.

    Plan 06-03 ships evaluate_cash_out(req) which consumes this shape and
    returns a RefiResponse with refi_kind='cash_out' populated with
    cash_proceeds + monthly_payment_delta + total_interest_delta (SC-3).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    refi_kind: Literal["cash_out"] = "cash_out"

    cash_out_amount: Money = Field(gt=Decimal("0"))
    """Equity extracted from the property at refi (gt=0 — a cash-out refi by
    definition has positive cash_out_amount; rate-and-term is the zero-cash-out
    sibling). New loan principal = old_loan_balance + cash_out_amount."""

    @model_validator(mode="after")
    def _validate_cash_out(self) -> CashOutRefiRequest:
        _validate_common(self)
        return self


# ---------------------------------------------------------------------------
# RefiRequest discriminated union (D-02; mirrors Phase 4 AffordabilityRequest)
# ---------------------------------------------------------------------------


RefiRequest = Annotated[
    RateAndTermRefiRequest | CashOutRefiRequest,
    Field(discriminator="refi_kind"),
]
"""Pydantic v2 discriminated union by `refi_kind` field (D-02).

Use TypeAdapter(RefiRequest).validate_json(...) at the script boundary; the
discriminator routes the raw payload to RateAndTermRefiRequest or
CashOutRefiRequest based on the `refi_kind` field's literal value. Mirrors
lib/affordability.py::AffordabilityRequest (Phase 4 D-14)."""


# ---------------------------------------------------------------------------
# RefiResponse (SC-1 / SC-2 / SC-3 surface; D-11 cashflow audit trail)
# ---------------------------------------------------------------------------


class RefiResponse(BaseModel):
    """Phase 6 evaluation result.

    Populated for both refi_kind variants. Cash-out-only fields (cash_proceeds,
    monthly_payment_delta, total_interest_delta) are None for rate-and-term.
    after_tax_npv is None unless after_tax_mode=True (D-09).

    `cashflows` is the per-period audit trail (every RefiCashflow constructed by
    the engine). Downstream verifiers (Plan 06-05 fixtures) assert specific
    cashflow_kind values appear in the stream.

    `warnings` carries soft signals (e.g., StaleReferenceWarning surfaces from
    after-tax-mode IRS predicate calls, PMI/MIP carve-out reminders per D-08).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    refi_kind: Literal["rate_and_term", "cash_out"]
    """Echoes the request's refi_kind for downstream consumer routing."""

    npv: Decimal = Field(strict=True, max_digits=14, decimal_places=2)
    """Net present value (signed Decimal — NOT Money because NPV can be negative).
    Quantized to cents at the response boundary (Phase 4 D-18 inheritance)."""

    breakeven: RefiBreakeven
    """Dual-form breakeven (SC-2): simple + NPV-based with paired status fields."""

    old_monthly_pi: Money
    """OLD loan monthly P&I (computed via build_schedule on the residual schedule)."""

    new_monthly_pi: Money
    """NEW loan monthly P&I. When new_loan_monthly_pi_override is set (D-10),
    echoes the override; otherwise from build_schedule(new_loan).monthly_pi."""

    monthly_savings: Decimal = Field(strict=True, max_digits=14, decimal_places=2)
    """Signed: old_monthly_pi - new_monthly_pi. Positive when refi reduces the
    payment (rate-and-term happy path). Negative for most cash-out scenarios
    (larger principal → larger payment)."""

    # Cash-out only (None for rate-and-term)
    cash_proceeds: Money | None = None
    """SC-3: net cash to borrower at t=0 = cash_out_amount - closing_costs."""

    monthly_payment_delta: Decimal | None = None
    """SC-3: signed Decimal; new_monthly_pi - old_monthly_pi. Positive when the
    cash-out larger principal raises the payment."""

    total_interest_delta: Decimal | None = None
    """SC-3: signed Decimal; new_total_remaining_interest - old_total_remaining_interest.
    Positive when the cash-out + extension increases lifetime interest."""

    # After-tax mode only (None unless after_tax_mode=True)
    after_tax_npv: Decimal | None = None
    """D-09: NPV with tax-shield cashflows added. None when after_tax_mode=False."""

    # Discount-rate echo (for traceability)
    discount_rate_annual_used: Rate
    """Echoes the request's discount_rate_annual after quantize_rate (D-05 + Phase 5
    D-14). Surfaces what the engine actually used for downstream auditing."""

    analysis_horizon_months_used: int
    """Echoes the effective horizon (D-11): new_term_months when request omitted
    analysis_horizon_months, else the supplied value. Surfaces what the engine
    actually used for downstream auditing."""

    cashflows: list[RefiCashflow]
    """Per-period audit trail. Every RefiCashflow constructed by the engine.
    Plan 06-05 fixtures assert specific kind values appear in the stream
    (test_refi_cashflow_kind_citation_coverage)."""

    warnings: list[str] = Field(default_factory=list)
    """Soft signals: StaleReferenceWarning surfaces from after-tax-mode IRS
    predicate calls; PMI/MIP carve-out reminders per D-08; etc."""


# ---------------------------------------------------------------------------
# Private helpers (Plan 06-02): Loan-construction + cashflow builder
# ---------------------------------------------------------------------------


def _build_old_loan_residual(
    balance_remaining: Decimal,
    annual_rate: Decimal,
    remaining_months: int,
) -> Loan:
    """Construct a synthetic Loan representing the OLD loan as it stands today
    (the borrower's residual obligation if they don't refi).

    Uses the OLD rate over the REMAINING term — NOT the original term.
    Documented in references/refi-npv.md §"Cashflow Inventory".
    """
    return Loan(
        principal=quantize_cents(balance_remaining),
        annual_rate=quantize_rate(annual_rate),
        term_months=remaining_months,
        origination_date=None,  # synthesized at engine time per Phase 3 D-12
        loan_type="fixed",
    )


def _build_new_loan(
    new_principal: Decimal,
    new_annual_rate: Decimal,
    new_term_months: int,
) -> Loan:
    """Construct the NEW loan post-refi (rate-and-term: new_principal == old_balance;
    cash-out: new_principal == old_balance + cash_out_amount per D-15)."""
    return Loan(
        principal=quantize_cents(new_principal),
        annual_rate=quantize_rate(new_annual_rate),
        term_months=new_term_months,
        origination_date=None,
        loan_type="fixed",
    )


def _build_refi_cashflows(
    *,
    closing_costs: Decimal,
    old_monthly_pi: Decimal,
    new_monthly_pi: Decimal,
    horizon_months: int,
    cash_proceeds_net: Decimal = Decimal("0.00"),  # cash-out only
) -> list[RefiCashflow]:
    """Enumerate the per-period RefiCashflow stream for both refi kinds.

    D-04 sign convention enforced via RefiCashflow validator at construction.
    D-15: closing costs always at t=0 as direction='outflow', amount=-closing_costs.

    For rate-and-term: cash_proceeds_net=0; t=1..horizon emits monthly_savings
    (= old_pi - new_pi) as direction='inflow' (positive when new < old; the
    validator REJECTS the cashflow if savings is negative — engine-side caller
    must classify direction by sign).

    For cash-out: t=0 also gets +cash_proceeds_net inflow; t=1..horizon emits
    monthly_payment_delta. Wave 3 (Plan 06-03) calls this with cash_proceeds_net>0.
    """
    cashflows: list[RefiCashflow] = []

    # t=0: closing costs (always outflow; D-15)
    if closing_costs > Decimal("0"):
        cashflows.append(
            RefiCashflow(
                period=0,
                direction="outflow",
                amount=-quantize_cents(closing_costs),
                kind="closing_costs",
            )
        )

    # t=0: cash proceeds (cash-out only)
    if cash_proceeds_net > Decimal("0"):
        cashflows.append(
            RefiCashflow(
                period=0,
                direction="inflow",
                amount=quantize_cents(cash_proceeds_net),
                kind="cash_proceeds",
            )
        )

    # t=1..horizon: monthly savings or payment delta
    # Sign-classify per D-04: savings > 0 → inflow; savings < 0 (i.e., new_pi > old_pi) → outflow
    per_period_signed = old_monthly_pi - new_monthly_pi  # positive = savings; negative = extra cost
    if per_period_signed != Decimal("0"):
        for t in range(1, horizon_months + 1):
            if per_period_signed > Decimal("0"):
                cashflows.append(
                    RefiCashflow(
                        period=t,
                        direction="inflow",
                        amount=quantize_cents(per_period_signed),
                        kind="monthly_savings",
                    )
                )
            else:
                cashflows.append(
                    RefiCashflow(
                        period=t,
                        direction="outflow",
                        amount=quantize_cents(per_period_signed),  # already negative
                        kind="monthly_payment_delta",
                    )
                )
    return cashflows


# ---------------------------------------------------------------------------
# Private helpers (Plan 06-02 Task 2): NPV + breakeven (per-period flatten,
# numpy_financial.npv wrapper, simple-divide breakeven, cumulative-NPV scan)
# ---------------------------------------------------------------------------


def _flatten_cashflows_to_per_period(
    cashflows: list[RefiCashflow],
    horizon_months: int,
) -> list[Decimal]:
    """Collapse cashflow list into a length-(horizon+1) Decimal array indexed by t.

    npf.npv eats `values` starting at t=0 (RESEARCH §"Watch Out For"). Multiple
    cashflows at the same period (e.g., closing_costs + cash_proceeds at t=0)
    sum together at that index.
    """
    per_period: list[Decimal] = [Decimal("0.00")] * (horizon_months + 1)
    for cf in cashflows:
        if cf.period > horizon_months:
            continue  # truncate per D-11
        per_period[cf.period] = per_period[cf.period] + cf.amount
    return per_period


def _compute_npv(
    discount_rate_annual: Decimal,
    cashflows: list[RefiCashflow],
    horizon_months: int,
) -> Decimal:
    """Wrap numpy_financial.npv (AMRT-01 inheritance: wrap, do not reimplement).

    Per-period rate = discount_rate_annual / 12. quantize_cents AT THE BOUNDARY ONLY
    (Phase 1 PITFALLS; Phase 4 PITI idiom). Intermediate computation stays at
    full Decimal precision via lib.money.MONEY_CONTEXT (28 digits).
    """
    period_rate = discount_rate_annual / Decimal("12")
    values = _flatten_cashflows_to_per_period(cashflows, horizon_months)
    npv = npf.npv(period_rate, values)  # numpy-financial 1.0.0 returns Decimal when fed Decimal
    return quantize_cents(npv)


def _compute_breakeven_simple(
    closing_costs: Decimal,
    monthly_savings: Decimal,
) -> tuple[int | None, Literal["ok", "no_savings", "zero_costs"]]:
    """REFI-03 first formula: ceil(closing_costs / monthly_savings).

    Edge cases per RESEARCH §"(d) Divergence":
      monthly_savings <= 0 → (None, 'no_savings')
      closing_costs == 0  → (0, 'zero_costs')
      else → (ceil(closing/savings), 'ok')
    """
    if closing_costs == Decimal("0"):
        return 0, "zero_costs"
    if monthly_savings <= Decimal("0"):
        return None, "no_savings"
    # Ceiling divide via Decimal
    months_d = (closing_costs / monthly_savings).quantize(Decimal("1"), rounding=ROUND_CEILING)
    return int(months_d), "ok"


def _compute_breakeven_npv(
    discount_rate_annual: Decimal,
    cashflows: list[RefiCashflow],
    horizon_months: int,
) -> tuple[int | None, Literal["ok", "never_breaks_even"]]:
    """REFI-03 second formula: smallest n where cumulative NPV(0..n) >= 0.

    Per D-06: cumulative-NPV scan, NOT npf.irr (bug #131 — arch-dependent).
    """
    period_rate = discount_rate_annual / Decimal("12")
    per_period = _flatten_cashflows_to_per_period(cashflows, horizon_months)
    for n in range(0, horizon_months + 1):
        cumulative = npf.npv(period_rate, per_period[: n + 1])
        if cumulative >= Decimal("0"):
            return n, "ok"
    return None, "never_breaks_even"


# ---------------------------------------------------------------------------
# Private helpers (Plan 06-03 Task 2): after-tax tax-shield cashflow stream
# (D-09; cites lib.rules.irs_pub936.qualified_loan_limit / RUL-11)
# ---------------------------------------------------------------------------


def _compute_tax_shield_cashflows(
    *,
    new_loan: Loan,
    marginal_tax_rate: Decimal,
    filing_status: Literal["single", "mfj", "mfs", "hoh"],
    has_grandfathered_debt: bool,
    horizon_months: int,
) -> list[RefiCashflow]:
    """Per-period tax_shield inflow stream for the after-tax NPV overlay (D-09).

    Per 06-RESEARCH §"(f) Tax Treatment":
      qualified_limit = lib.rules.irs_pub936.qualified_loan_limit(
          filing_status, has_grandfathered_debt=...
      )
      deductible_principal = min(new_principal, qualified_limit)
      deduction_fraction   = deductible_principal / new_principal  (Decimal)
      For each period t in 1..horizon:
          interest_t            = new_schedule.payments[t-1].interest
          deductible_interest_t = interest_t * deduction_fraction
          tax_shield_t          = deductible_interest_t * marginal_tax_rate
          emit RefiCashflow(period=t, direction='inflow',
                            amount=tax_shield_t, kind='tax_shield')

    Tax-shield cashflows with quantized amount == $0.00 are dropped (no sign
    hazard at the validator, but they bloat the audit trail).

    The cashflow stream is appended to the pre-tax cashflow list before NPV
    re-computation; the engine never mutates the pre-tax list.
    """
    # Lazy import: keeps Phase 6 cold path (after_tax_mode=False) free of the
    # IRS predicate's reference-data load cost.
    from lib.rules.irs_pub936 import qualified_loan_limit

    qualified_limit = qualified_loan_limit(
        filing_status=filing_status,
        has_grandfathered_debt=has_grandfathered_debt,
    )
    if new_loan.principal == Decimal("0"):
        return []
    deductible_principal = min(new_loan.principal, qualified_limit)
    deduction_fraction = deductible_principal / new_loan.principal

    new_schedule = build_schedule(new_loan)
    cashflows: list[RefiCashflow] = []
    upper = min(horizon_months, len(new_schedule.payments))
    for t in range(1, upper + 1):
        interest_t = new_schedule.payments[t - 1].interest
        deductible_interest_t = interest_t * deduction_fraction
        tax_shield_t = quantize_cents(deductible_interest_t * marginal_tax_rate)
        if tax_shield_t > Decimal("0.00"):
            cashflows.append(
                RefiCashflow(
                    period=t,
                    direction="inflow",
                    amount=tax_shield_t,
                    kind="tax_shield",
                )
            )
    return cashflows


# ---------------------------------------------------------------------------
# Cross-plan stub bodies (Phase 2 D-08 cross-plan stub idiom)
# ---------------------------------------------------------------------------


# Pinned Oracles (06-RESEARCH.md §"Pinned Oracles" + Plan 06-05 fixtures):
#   Oracle 1 (SC-1 positive): old=$300k@7% 25y residual, new=$300k@5% 25y,
#     closing=$2000, discount=5%, horizon=300 → NPV = Decimal("60705.48")
#     (RESEARCH approximation cited $60,696.32 from analytical PMT formula;
#     engine-derived exact Decimal lands at 60705.48 — Plan 06-05 fixture pins
#     this exact value via Decimal equality per Phase 5 D-04 [REVISED]
#     hand_calc_check witness pattern.)
#   Oracle 2 (SC-1 negative): same parameters BUT closing=$5000 +
#     analysis_horizon_months=12 → NPV = Decimal("-718.01")
#     (RESEARCH approximation cited -$741; engine-derived exact Decimal lands
#     at -718.01 — same Plan 06-05 fixture-pinning discipline.)
# Re-derive at fixture-creation time by running the verification snippets in
# Plan 06-02 Tasks 3-4. These values are the contract Wave 5 fixtures pin
# against via Decimal equality (CLAUDE.md money-discipline; never assertAlmostEqual).
def evaluate_rate_and_term(req: RateAndTermRefiRequest) -> RefiResponse:
    """Rate-and-term refi NPV (REFI-01).

    Pipeline (mirrors lib/affordability.py::evaluate_forward 12-step shape):
      1. Build OLD-loan residual schedule via Phase 3 build_schedule;
         extract old_monthly_pi (= schedule.monthly_pi).
      2. Build NEW loan with new principal == old_balance (rate-and-term
         definition), new_annual_rate, new_term_months.
      3. Extract new_monthly_pi (or use req.new_loan_monthly_pi_override
         per D-10 when supplied).
      4. monthly_savings = old_monthly_pi - new_monthly_pi (signed).
      5. horizon = req.analysis_horizon_months or new_loan.term_months
         (D-11 default = full new term).
      6. Build cashflows via _build_refi_cashflows (closing_costs at t=0
         as outflow per D-15; per-period savings as inflow when positive).
      7. NPV via _compute_npv.
      8. Breakeven (simple + NPV) via _compute_breakeven_*.
      9. Construct RefiResponse with all populated fields.

    After-tax mode (D-09): when req.after_tax_mode=True, Wave 3 (Plan 06-03)
    adds a tax_shield branch. Wave 2 emits a warning if after_tax_mode=True
    (signaling "feature ships in Wave 3"); Wave 3 swaps in the real branch.
    """
    # 1-2: build loans
    old_loan = _build_old_loan_residual(
        balance_remaining=req.old_loan_balance,
        annual_rate=req.old_annual_rate,
        remaining_months=req.old_remaining_months,
    )
    new_loan = _build_new_loan(
        new_principal=req.old_loan_balance,  # rate-and-term: same principal
        new_annual_rate=req.new_annual_rate,
        new_term_months=req.new_term_months,
    )

    # 3: P&I (use override if supplied per D-10)
    old_monthly_pi = build_schedule(old_loan).monthly_pi
    new_monthly_pi = (
        req.new_loan_monthly_pi_override
        if req.new_loan_monthly_pi_override is not None
        else build_schedule(new_loan).monthly_pi
    )

    # 4: signed savings
    monthly_savings = old_monthly_pi - new_monthly_pi

    # 5: horizon
    horizon = req.analysis_horizon_months or new_loan.term_months

    # 6: cashflows
    cashflows = _build_refi_cashflows(
        closing_costs=req.closing_costs,
        old_monthly_pi=old_monthly_pi,
        new_monthly_pi=new_monthly_pi,
        horizon_months=horizon,
        cash_proceeds_net=Decimal("0.00"),  # rate-and-term has no proceeds
    )

    # 7: NPV
    discount_rate = quantize_rate(req.discount_rate_annual)
    npv = _compute_npv(discount_rate, cashflows, horizon)

    # 8: breakeven
    simple_months, simple_status = _compute_breakeven_simple(req.closing_costs, monthly_savings)
    npv_months, npv_status = _compute_breakeven_npv(discount_rate, cashflows, horizon)

    # 9: response
    warnings_list: list[str] = []
    if req.after_tax_mode:
        warnings_list.append(
            "after_tax_mode=True surfaced; Wave 3 (Plan 06-03) will populate after_tax_npv"
        )

    return RefiResponse(
        refi_kind="rate_and_term",
        npv=npv,
        breakeven=RefiBreakeven(
            simple_months=simple_months,
            simple_status=simple_status,
            npv_months=npv_months,
            npv_status=npv_status,
        ),
        old_monthly_pi=old_monthly_pi,
        new_monthly_pi=new_monthly_pi,
        monthly_savings=quantize_cents(monthly_savings),
        cash_proceeds=None,
        monthly_payment_delta=None,
        total_interest_delta=None,
        after_tax_npv=None,
        discount_rate_annual_used=discount_rate,
        analysis_horizon_months_used=horizon,
        cashflows=cashflows,
        warnings=warnings_list,
    )


def evaluate_cash_out(req: CashOutRefiRequest) -> RefiResponse:
    """Evaluate a cash-out refi (Wave 3 / Plan 06-03 ships the body).

    REFI-02 + SC-3 anchor. Computes:
      - new principal = old_loan_balance + cash_out_amount
      - cash_proceeds = cash_out_amount - closing_costs (NET of closing per D-15)
      - monthly_payment_delta = new_monthly_pi - old_monthly_pi
      - total_interest_delta = new_total_interest - old_total_interest
      - cashflows: t=0 cash_proceeds (inflow); t=1..N monthly_payment_delta
        (outflow when new_pi > old_pi, which is typical for cash-out)
      - npv via numpy_financial.npv
      - if after_tax_mode: tax_shield cashflows added per RUL-11
    """
    raise NotImplementedError("Plan 06-03 ships cash-out engine body (Wave 3 of Phase 6)")


def evaluate(req: RefiRequest) -> RefiResponse:
    """Public dispatcher (Wave 4 / Plan 06-04 ships the body).

    Switches on req.refi_kind and routes to evaluate_rate_and_term or
    evaluate_cash_out. Mirrors lib/affordability.py::evaluate dispatcher pattern.

    # Phase 11: see pyxirr migration note in module docstring (D-07).
    # When SUBA-02 ships the refi-npv-agent multi-offer ranking, an
    # evaluate_batch(reqs: Sequence[RefiRequest]) sibling may use pyxirr.npv
    # for batch ranking (10-50x faster on N≥1000 scenarios). Phase 6 v1's
    # single-scenario surface preserves Decimal discipline via numpy_financial.
    """
    raise NotImplementedError("Plan 06-04 ships the public dispatcher (Wave 4 of Phase 6)")
