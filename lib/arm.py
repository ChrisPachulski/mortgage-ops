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

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.models import Loan, Money, Payment, Rate


class ARMTerms(BaseModel):
    """ARM contractual terms (8 explicit fields per ARM-01 + optional note_rate per D-02).

    Field schema locked in CONTEXT.md D-06. Every field is REQUIRED except
    note_rate; floor_rate has NO default per D-02 (forces explicit caller
    choice; matches mortgage-ops 'fail loud, no inference' discipline).

    Wave 5 (Plan 05-05) appends a docstring citation:
        See references/arm-mechanics.md for reset/cap/floor convention.
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
        for entry in self.index_path:
            if entry.period not in triggers:
                sample = sorted(triggers)[:5]
                suffix = "..." if len(triggers) > 5 else ""
                raise ValueError(
                    f"index_path entry at period {entry.period} does not align to a "
                    f"reset trigger period (D-01). Valid triggers for this product: "
                    f"{sample}{suffix}"
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
