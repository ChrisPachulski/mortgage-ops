"""ARM (adjustable-rate mortgage) models + engine for Phase 5.

This file is the entry point for ARM modeling per CONTEXT.md D-03:
parallel ARMSchedule + ARMPayment in lib/arm.py; Phase 1 Payment / Schedule
UNCHANGED. Models live here (D-discretion scope-to-file) until a second
consumer needs them — current consumers: lib.arm, scripts.arm_simulate.

Wave 2 (Plan 05-02) ships the model layer (this file).
Wave 3 (Plan 05-03) adds build_arm_schedule(...) per-epoch slice-stitch.
Wave 5 (Plan 05-05) adds the references/arm-mechanics.md docstring citation
on ARMTerms (ROADMAP SC-5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.amortize import build_schedule
from lib.models import Loan, Money, Payment, Rate
from lib.money import quantize_cents, quantize_rate


class ARMTerms(BaseModel):
    """ARM contractual terms (8 explicit fields per ARM-01 + optional note_rate per D-02).

    See references/arm-mechanics.md for reset/cap/floor convention, including
    Selling Guide citations (Fannie B2-1.4-02, Freddie 6302.7(b)), CFPB §1951,
    and the AmericU 5/6 SOFR ARM disclosure (Phase 5 ARM-09 + ROADMAP SC-5).

    Field schema locked in CONTEXT.md D-06. Every field is REQUIRED except
    note_rate; floor_rate has NO default per D-02 (forces explicit caller
    choice; matches mortgage-ops 'fail loud, no inference' discipline).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    initial_period_months: int = Field(ge=1, le=600)
    """Months at the initial fixed rate. 5/1 ARM = 60; 7/1 = 84; 10/1 = 120; 5/6 = 60."""

    reset_period_months: int = Field(ge=1, le=600)
    """Months between resets after the initial period. 5/1, 7/1, 10/1 = 12; 5/6 = 6."""

    initial_cap_bps: int = Field(ge=0, le=2000)
    """First-reset cap in basis points; common: 500 (5pp). 2000 (20pp) sanity rail."""

    periodic_cap_bps: int = Field(ge=0, le=2000)
    """Cap for resets after the first; common: 200 (2pp)."""

    lifetime_cap_bps: int = Field(ge=0, le=2000)
    """Lifetime cap measured against note_rate (D-02); common: 500 (5pp)."""

    floor_rate: Rate
    """REQUIRED per D-02. No default. Effective floor = max(margin_bps/10000, floor_rate)."""

    margin_bps: int = Field(ge=0, le=2000)
    """Spread over index in basis points; common: 250 (2.5pp)."""

    index_series_id: str = Field(min_length=1, max_length=64)
    """Metadata only in v1 (e.g., 'MORTGAGE30US', 'SOFR1Y'). Phase 12 maps to FRED MCP."""

    note_rate: Rate | None = None
    """Optional per D-02. None = use loan.annual_rate as lifetime base. Provide for teaser-rate ARMs."""


class IndexPathEntry(BaseModel):
    """One entry in ARMRequest.index_path: an index value applied at a specific reset period.

    Scoped to lib/arm.py per D-discretion (scope-to-file until second consumer).
    Pattern mirrors Phase 3's ExtraPrincipalEntry (lib/amortize.py).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    period: int = Field(ge=1)
    """The reset trigger period this index value applies to (e.g., 61, 73 for a 5/1 ARM).
    Validated against the reset cadence by ARMRequest._index_path_periods_align_to_reset_triggers."""

    value: Rate
    """The index value at this period (e.g., 0.0525 = 5.25%)."""


class ARMRequest(BaseModel):
    """Top-level request schema for build_arm_schedule + scripts/arm_simulate.py.

    Locked structure per D-01: assumed_index_rate REQUIRED + optional index_path overrides.
    Override-wins semantics: at a reset trigger period, index_path[period] wins over assumed_index_rate.
    Misaligned index_path periods (not a reset trigger) raise ValueError at construction.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    """Phase 1 Loan; loan.annual_rate is the INITIAL fixed-period rate. loan.loan_type='arm' is conventional but not validated here."""

    arm_terms: ARMTerms
    assumed_index_rate: Rate
    """REQUIRED per D-01. Engine fallback when index_path does not cover a reset period."""

    index_path: list[IndexPathEntry] = Field(default_factory=list)
    """Optional per-reset overrides. Empty list = use assumed_index_rate at every reset."""

    @model_validator(mode="after")
    def _index_path_periods_align_to_reset_triggers(self) -> ARMRequest:
        """D-01: every index_path entry's period MUST match a reset trigger.

        Reset triggers (per RESEARCH §Q5):
            triggers = [initial_period_months + 1 + k * reset_period_months for k in 0..]
            up to and including loan.term_months.

        For a 5/1 ARM (initial=60, reset=12, term=360): triggers = {61, 73, 85, ..., 349}.
        An index_path entry at period 62 raises ValueError — caller must align.
        """
        initial = self.arm_terms.initial_period_months
        cadence = self.arm_terms.reset_period_months
        term = self.loan.term_months
        triggers: set[int] = set()
        period = initial + 1
        while period <= term:
            triggers.add(period)
            period += cadence
        seen_periods: set[int] = set()
        for entry in self.index_path:
            if entry.period not in triggers:
                sample = sorted(triggers)[:5]
                suffix = "..." if len(triggers) > 5 else ""
                raise ValueError(
                    f"index_path entry at period {entry.period} does not align to a "
                    f"reset trigger period (D-01). Valid triggers for this product: "
                    f"{sample}{suffix}"
                )
            # WR-02: reject duplicates so override-wins semantics are deterministic;
            # silent first-wins violates the project's "fail loud, no inference" doctrine
            # (CLAUDE.md money discipline + CONTEXT.md D-01).
            if entry.period in seen_periods:
                raise ValueError(
                    f"index_path contains duplicate entries for period {entry.period} "
                    f"(D-01: each reset trigger may appear at most once)"
                )
            seen_periods.add(entry.period)
        return self

    @model_validator(mode="after")
    def _floor_does_not_exceed_lifetime_ceiling(self) -> ARMRequest:
        """WR-03 + D-02: reject configurations where the effective floor exceeds the
        lifetime ceiling. Otherwise every reset's clamp would force new_rate above the
        lifetime cap (D-02 invariant violation), and the classifier could not signal it
        downstream (applied_cap reports "floor" without the lifetime breach being visible).

        note_rate is optional (collapses to loan.annual_rate per D-02), so this check
        runs at the ARMRequest layer where loan.annual_rate is available.
        """
        terms = self.arm_terms
        note_rate_eff = terms.note_rate if terms.note_rate is not None else self.loan.annual_rate
        lifetime_ceiling = note_rate_eff + Decimal(terms.lifetime_cap_bps) / Decimal("10000")
        margin_rate = Decimal(terms.margin_bps) / Decimal("10000")
        effective_floor = max(margin_rate, terms.floor_rate)
        if effective_floor > lifetime_ceiling:
            raise ValueError(
                f"effective_floor ({effective_floor}) exceeds lifetime_ceiling "
                f"({lifetime_ceiling}); this would force every reset to violate "
                f"the lifetime cap (D-02 invariant)."
            )
        return self


class ARMPayment(Payment):
    """Payment row in an ARM schedule; subclass of Phase 1 Payment per D-03.

    Adds rate_in_effect to capture the per-period annualized rate. Pydantic v2
    model_config IS auto-inherited from Payment per RESEARCH LM-4, but we
    re-specify here for defense-in-depth + grep-discoverability.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    rate_in_effect: Rate
    """The annualized rate active during this period. Equals loan.annual_rate during epoch 0
    (initial fixed period); equals new_rate after each reset (D-02 formula)."""


class ResetEvent(BaseModel):
    """One ARM reset boundary (per D-03).

    Records old/new rate, old/new payment, the index value used, and the cap
    kind that bound the new rate (Literal value enables D-10 citation-coverage).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    period: int = Field(ge=1)
    """Absolute period (continuous numbering) where the new rate first applies. 5/1: 61, 73, ..."""

    old_rate: Rate
    new_rate: Rate
    old_pmt: Money
    """P&I in effect immediately before the reset (last payment of the prior epoch)."""

    new_pmt: Money
    """P&I that takes effect at this period (first payment of the new epoch)."""

    index_value_used: Rate
    """The index value used to compute new_rate. Equals index_path[period].value if supplied,
    else assumed_index_rate (D-01 override-wins)."""

    applied_cap: Literal["initial", "periodic", "lifetime", "floor", "none"]
    """Which constraint bound new_rate. D-10 citation-coverage requires every value exercised."""


class ARMSchedule(BaseModel):
    """ARM-aware schedule. Parallel to Phase 1 Schedule; NOT a subclass per D-03.

    Continuous period numbering 1..N across epochs. final_payment_adjusted reflects
    ONLY the final epoch's Phase 3 D-09 cleanup (intermediate epochs always carry
    forward — see Plan 05-03 D-05 algorithm).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    arm_terms: ARMTerms
    payments: list[ARMPayment]
    """Continuous 1..N. payments[0].period == 1; payments[-1].period == loan.term_months."""

    reset_events: list[ResetEvent]
    """One entry per reset boundary (period >= initial_period_months + 1)."""

    total_interest: Money
    """Sum of all interest paid; preserves Phase 1 D-15 invariant: total_interest == payments[-1].cumulative_interest."""

    final_payment_adjusted: bool = False
    """Only the FINAL epoch sets True (per Phase 3 D-09 / D-10 cleanup); intermediate epochs always False."""


# =========================================================================
# Engine — build_arm_schedule + private helpers (Wave 3 / Plan 05-03)
# =========================================================================


def compute_reset_triggers(arm_terms: ARMTerms, term_months: int) -> list[int]:
    """Return the list of reset trigger periods for an ARM.

    Public per Phase 8 D-02-01 (08-02 plan): lib/stress.py imports this for
    ARM-reset path synthesis. Was private until Phase 8.

    Per RESEARCH §Q5: triggers = [initial_period_months + 1, +reset_period_months, ...]
    up to and including term_months. The +1 implements the "rate change applies at
    START of post-fixed-period month" off-by-one (PITFALL 5; ROADMAP SC-2/SC-3).

    5/1 ARM 30yr (initial=60, reset=12, term=360) -> [61, 73, 85, ..., 349].
    5/6 ARM 30yr (initial=60, reset=6,  term=360) -> [61, 67, 73, ..., 355].
    """
    triggers: list[int] = []
    period = arm_terms.initial_period_months + 1
    while period <= term_months:
        triggers.append(period)
        period += arm_terms.reset_period_months
    return triggers


# Backward compat: keep the underscore-prefixed name as an alias for in-module callers.
_compute_reset_triggers = compute_reset_triggers


def _compute_new_rate(
    *,
    prior_rate: Rate,
    epoch_idx: int,
    period: int,
    req: ARMRequest,
    loan_annual_rate: Rate,
) -> tuple[Rate, Literal["initial", "periodic", "lifetime", "floor", "none"], Rate]:
    """Compute the new rate at a reset trigger period per D-02.

    Returns (new_rate, applied_cap, index_value_used).

    Formula (D-02 verbatim):
        index = req.index_path[period].value if period in index_path else req.assumed_index_rate
        fully_indexed = quantize_rate(index + margin_bps/10000)
        effective_floor = max(margin_bps/10000, floor_rate)
        applicable_cap_bps = initial_cap_bps if epoch_idx == 1 else periodic_cap_bps
        periodic_ceiling = prior_rate + applicable_cap_bps/10000
        note_rate_eff = note_rate if note_rate is not None else loan.annual_rate
        lifetime_ceiling = note_rate_eff + lifetime_cap_bps/10000
        ceiling = min(periodic_ceiling, lifetime_ceiling)
        new_rate = quantize_rate(clamp(fully_indexed, low=effective_floor, high=ceiling))

    applied_cap classification (D-10):
        "floor"     if new_rate == quantize_rate(effective_floor) AND lifted above fully_indexed
        "lifetime"  if new_rate == quantize_rate(lifetime_ceiling) AND lifetime <= periodic AND held below fully_indexed
        "initial"   if epoch_idx == 1 AND new_rate == quantize_rate(periodic_ceiling) AND held below fully_indexed
        "periodic"  if epoch_idx >= 2 AND new_rate == quantize_rate(periodic_ceiling) AND held below fully_indexed
        "none"      otherwise (fully_indexed itself fell strictly inside the open interval)
    """
    terms = req.arm_terms
    # Step 1: resolve index value for this period (override-wins per D-01)
    index_value: Rate = req.assumed_index_rate
    for entry in req.index_path:
        if entry.period == period:
            index_value = entry.value
            break

    # Step 2: compute the candidate rate components (all using Decimal-from-bps, never floats)
    margin_rate = Decimal(terms.margin_bps) / Decimal("10000")
    fully_indexed = quantize_rate(index_value + margin_rate)

    effective_floor = max(margin_rate, terms.floor_rate)

    is_first_reset = epoch_idx == 1
    applicable_cap_bps = terms.initial_cap_bps if is_first_reset else terms.periodic_cap_bps
    periodic_ceiling = prior_rate + (Decimal(applicable_cap_bps) / Decimal("10000"))

    note_rate_eff = terms.note_rate if terms.note_rate is not None else loan_annual_rate
    lifetime_ceiling = note_rate_eff + (Decimal(terms.lifetime_cap_bps) / Decimal("10000"))

    ceiling = min(periodic_ceiling, lifetime_ceiling)

    # Step 3: clamp + final quantize
    # Note: max(low, min(value, high)) implements clamp without an extra Python helper.
    clamped = max(effective_floor, min(fully_indexed, ceiling))
    new_rate = quantize_rate(clamped)

    # Step 4: classify which constraint bound new_rate (for ResetEvent.applied_cap + D-10).
    # Compare quantized values (avoid 1-ULP misses).
    floor_q = quantize_rate(effective_floor)
    periodic_q = quantize_rate(periodic_ceiling)
    lifetime_q = quantize_rate(lifetime_ceiling)
    fully_indexed_q = quantize_rate(fully_indexed)

    applied_cap: Literal["initial", "periodic", "lifetime", "floor", "none"]
    if new_rate == floor_q and new_rate > fully_indexed_q:
        # Floor lifted the rate above the unconstrained fully_indexed value.
        applied_cap = "floor"
    elif new_rate == lifetime_q and lifetime_q <= periodic_q and new_rate < fully_indexed_q:
        # Lifetime ceiling held below fully_indexed AND was the binding (smaller) ceiling.
        applied_cap = "lifetime"
    elif new_rate == periodic_q and new_rate < fully_indexed_q:
        # Periodic ceiling held below fully_indexed.
        applied_cap = "initial" if is_first_reset else "periodic"
    else:
        applied_cap = "none"

    return new_rate, applied_cap, index_value


def build_arm_schedule(req: ARMRequest) -> ARMSchedule:
    """Build an ARM amortization schedule per D-05 per-epoch slice-stitch (ARM-02..05).

    Algorithm:
        1. Compute reset trigger periods (RESEARCH §Q5 formula).
        2. For each epoch:
            a. Compute current_rate (epoch 0 = loan.annual_rate; epoch >=1 = D-02 reset formula).
            b. Synthesize a Loan with principal=remaining_balance, annual_rate=current_rate,
               term_months=remaining_full_term (NOT reset_period_months — the bear trap from
               RESEARCH Q1.2). Re-enter Phase 3's build_schedule.
            c. Slice synthetic.payments[:epoch_window] for non-final epochs;
               take ALL rows for the final epoch (which is where Phase 3 D-09 cleanup applies).
            d. Stitch each sliced row's cumulative_interest + cumulative_principal by adding
               the prior epoch's terminal cum totals.
            e. Convert to ARMPayment with rate_in_effect = current_rate.
            f. Carry remaining_balance forward (only for non-final epochs).
        3. Record one ResetEvent per reset trigger period.
        4. Final-epoch only: bubble up final_payment_adjusted from the synthetic schedule.

    D-05 explicitly forbids the "shortcut" of synthesizing the per-epoch Loan with
    term_months equal to the reset cadence (reset_period_months) because that fires
    Phase 3's D-09 cleanup at every epoch end — silently zeroing the balance at every
    reset (RESEARCH Q1.2 bear trap).

    Phase 1 D-15 invariant preserved: ARMSchedule.total_interest == payments[-1].cumulative_interest.
    """
    loan = req.loan
    terms = req.arm_terms

    # WR-01: Synthesize the origination anchor ONCE per build_arm_schedule call so every
    # per-epoch row's payment_date offsets from the same date. Mirrors lib.amortize._build_fixed_monthly's
    # `datetime.now(UTC).date()` fallback (D-12 idiom). Without this single anchor, each per-epoch
    # synthetic Loan would call datetime.now(UTC).date() independently — producing duplicate /
    # non-monotonic payment_date values across epochs and cross-midnight drift between epochs.
    origination_anchor = loan.origination_date or datetime.now(UTC).date()

    # Compute reset triggers + epoch boundaries.
    triggers = compute_reset_triggers(terms, loan.term_months)
    # boundaries: list of (start_period, end_period_exclusive) per epoch.
    boundaries: list[tuple[int, int]] = [(1, terms.initial_period_months + 1)]
    for i, t in enumerate(triggers):
        next_start = triggers[i + 1] if i + 1 < len(triggers) else loan.term_months + 1
        boundaries.append((t, next_start))

    # Iteration state
    arm_payments: list[ARMPayment] = []
    reset_events: list[ResetEvent] = []
    remaining_balance: Money = loan.principal
    prior_rate: Rate = loan.annual_rate
    current_rate: Rate = loan.annual_rate
    cum_int_carry: Money = Decimal("0.00")
    cum_prin_carry: Money = Decimal("0.00")
    final_payment_adjusted: bool = False
    old_pmt_for_next_reset: Money = Decimal("0.00")  # populated at end of each non-final epoch

    for epoch_idx, (start, end) in enumerate(boundaries):
        epoch_window = end - start
        is_final_epoch = end == loan.term_months + 1

        # Step 2a: compute current_rate
        applied_cap_for_event: Literal["initial", "periodic", "lifetime", "floor", "none"] = "none"
        index_value_used: Rate = req.assumed_index_rate  # placeholder for epoch 0 (no reset event)
        if epoch_idx == 0:
            current_rate = loan.annual_rate
        else:
            current_rate, applied_cap_for_event, index_value_used = _compute_new_rate(
                prior_rate=prior_rate,
                epoch_idx=epoch_idx,
                period=start,
                req=req,
                loan_annual_rate=loan.annual_rate,
            )

        # Step 2b: synthetic Loan over the FULL remaining term (D-05; never reset_period_months).
        remaining_full_term = loan.term_months - start + 1
        synthetic_loan = Loan(
            principal=remaining_balance,
            annual_rate=current_rate,
            term_months=remaining_full_term,
            origination_date=loan.origination_date,  # date offset applied below per row
            loan_type="arm",
        )
        synthetic = build_schedule(
            synthetic_loan,
            frequency="monthly",
            biweekly_mode=None,
            extra_principal=(),
        )

        # Step 2c: slice
        sliced = synthetic.payments if is_final_epoch else synthetic.payments[:epoch_window]

        # Step 2d + 2e: stitch + convert to ARMPayment
        for i, p in enumerate(sliced):
            absolute_period = start + i
            stitched_cum_int = quantize_cents(cum_int_carry + p.cumulative_interest)
            stitched_cum_prin = quantize_cents(cum_prin_carry + p.cumulative_principal)
            arm_payments.append(
                ARMPayment(
                    period=absolute_period,
                    payment_date=origination_anchor + relativedelta(months=absolute_period),
                    payment=p.payment,
                    principal=p.principal,
                    interest=p.interest,
                    extra_principal=p.extra_principal,
                    balance=p.balance,
                    cumulative_interest=stitched_cum_int,
                    cumulative_principal=stitched_cum_prin,
                    rate_in_effect=current_rate,
                )
            )

        # Step 3: emit ResetEvent (only for epoch >= 1; epoch 0 is the initial fixed period)
        if epoch_idx >= 1:
            # old_pmt is the LAST payment of the prior epoch; new_pmt is the FIRST of this epoch.
            new_pmt = sliced[0].payment
            reset_events.append(
                ResetEvent(
                    period=start,
                    old_rate=prior_rate,
                    new_rate=current_rate,
                    old_pmt=old_pmt_for_next_reset,
                    new_pmt=new_pmt,
                    index_value_used=index_value_used,
                    applied_cap=applied_cap_for_event,
                )
            )

        # Step 2f: carry forward (for non-final epochs)
        if not is_final_epoch:
            cum_int_carry = arm_payments[-1].cumulative_interest
            cum_prin_carry = arm_payments[-1].cumulative_principal
            remaining_balance = arm_payments[-1].balance
            old_pmt_for_next_reset = arm_payments[-1].payment
            prior_rate = current_rate
        else:
            # Step 4: final_payment_adjusted bubbles up only from the final epoch's synthetic.
            final_payment_adjusted = synthetic.final_payment_adjusted

    return ARMSchedule(
        loan=loan,
        arm_terms=terms,
        payments=arm_payments,
        reset_events=reset_events,
        total_interest=arm_payments[-1].cumulative_interest,  # Phase 1 D-15 invariant
        final_payment_adjusted=final_payment_adjusted,
    )
