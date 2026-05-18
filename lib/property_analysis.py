"""Phase 14 property analysis composition surface — output models + constants.

D-14-MODELS-04: this module ships the top-level ``analyze(listing, household,
profile) -> AnalysisReport`` entrypoint that Phase 15 markdown report formatter
consumes. The Phase-14 plan ships in 6 sub-plans:

  - Plan 14-01 (foundation models) — lib/household.py + lib/profile.py.
  - Plan 14-02 (matrix-models, THIS PLAN) — All Pydantic output models +
    module constants + per-cell composition helpers; ``analyze()`` is a stub.
  - Plan 14-03 (auxiliary-blocks) — stress / refi / points / tax block builders.
  - Plan 14-04 (verdict-synthesis) — lib/property_verdict.py + Verdict reasons.
  - Plan 14-05 (analyze-composition) — wires ``analyze()`` body.
  - Plan 14-06 (golden-fixtures) — hand-calculated AnalysisReport fixtures.

Co-location rationale (PATTERNS.md L461): every output model lives in this
single module to avoid circular-import risk with the planned
``lib/property_verdict.py`` (Plan 14-04 will import ``ProgramResult`` +
``Verdict`` from here without forming a cycle).

Pitfalls mitigated in this plan (RESEARCH.md §"Pitfalls"):
  - Pitfall 1 — conventional PMI estimate sourced from
    ``_CONV_PMI_ANNUAL_RATE`` Final constant (0.0075 / 75bps annual). Cells
    with LTV > 0.80 tag ``eligible_reasons`` with "PMI-RATE-ESTIMATED-0.0075".
  - Pitfall 2 — every Decimal constructed from a string; module-level
    ``DOWN_PAYMENT_PCTS`` uses ``Decimal("0.03")`` etc.
  - Pitfall 3 — signed Decimals (RefiRow.monthly_savings, RefiRow.npv_60mo)
    use raw ``Decimal = Field(strict=True, max_digits=14, decimal_places=2)``
    WITHOUT the Money alias (Money has ``ge=Decimal("0")``).
  - Pitfall 5 — Plan 14-02 Helper 2 constructs ``County(state_fips=...,
    county_fips=..., name=...)`` from Household FIPS triplet (NOT from zip).
  - Pitfall 6 — PITI composition includes ``monthly_mi`` and quantizes ONCE
    at the end (see ``_build_program_result`` Step 7).
  - Pitfall 8 — full ``ARMTerms`` shape supplied for ``_CONV_5_1_ARM_TERMS``
    (Phase 5 D-02 requires floor_rate explicitly; no default).
  - Pitfall 9 — every FRED read serializes through
    ``lib.fred_cache.with_cache_lock`` (Helper 1).
  - Pitfall 10 — ProgramResult carries summary scalars only; no
    ``list[Payment]`` schedule attached (mirrors Phase 8 D-03).

Iteration-2 (PLAN-CHECK) fixes baked in:
  - B-2 (VA-program affordability construction): ``_build_program_result``
    synthesizes a deterministic ``VAInputs(region="northeast", family_size=2,
    actual_residual_income=quantize_cents(monthly_income * Decimal("0.5")))``
    when ``program == "VA30"`` and tags ``eligible_reasons`` with
    "VA-RESIDUAL-SYNTHESIZED-V1". This is a CONSERVATIVE estimate (50% of
    monthly income comfortably exceeds the highest M26-7 minimum residual
    of ~$1,158 for family_size=5 in the West region); a follow-on phase
    may surface region / family_size on Profile if higher VA accuracy is
    required.
  - B-3 (PropertyListing required fields): NOT in this module — test
    helper ``_make_clean_listing`` defaults source_url / zpid / fetched_at
    so Phase-13 audit fields are populated. See tests/test_property_analysis.py.
  - B-4 (ProvenancedMoney null-value handling): ``_unwrap_provenanced``
    helper guards both ``pm is None`` AND ``pm.value is None`` (Phase 13
    ``ProvenancedMoney.value`` is ``Money | None``, so a present wrapper
    with a None value is a legitimate gap-fill envelope state).
  - W-3 (VA funding-fee treatment): VA funding fee is FINANCED INTO
    PRINCIPAL (mirrors Phase 4 D-03 financed-UFMIP convention);
    ``monthly_mi = Decimal("0.00")`` for VA cells; eligible_reasons appends
    "VA-FUNDING-FEE-FINANCED".

DISTINCT from ``lib.affordability.Household`` — Plan 14-01 ships
``lib.household.Household`` (financial-state-only snapshot) and Plan 14-02
imports the affordability symbol as ``AffordabilityHousehold`` to keep both
visible without name collision (OQ #1 resolution).
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003  # Pydantic resolves annotations at runtime
from decimal import Decimal
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from lib.arm import ARMTerms
from lib.models import Money, Rate  # noqa: TC001  # Pydantic resolves annotations at runtime
from lib.property_listing import (  # noqa: TC001  # Pydantic resolves annotations at runtime
    PropertyListing,
)

# ---------------------------------------------------------------------------
# Module-level Final constants (PATTERNS.md L260-265 + RESEARCH Pitfalls 1 + 2 + 8)
# ---------------------------------------------------------------------------

DOWN_PAYMENT_PCTS: Final[list[Decimal]] = [
    Decimal("0.03"),
    Decimal("0.05"),
    Decimal("0.10"),
    Decimal("0.15"),
    Decimal("0.20"),
    Decimal("0.25"),
]
"""Per CONTEXT D-14-MATRIX-01: 4 programs x 6 DPs = 24 cells (or 5 x 6 = 30 with jumbo).

All constructed from strings (Pitfall 2: never construct Decimal from a Python
float — Decimal(0.03) yields 0.0299999...). Downstream Plan 14-02 helpers
iterate this list verbatim; the strings are normative.
"""

PROGRAMS_BASE: Final[list[str]] = ["Conv30", "Conv15", "FHA30"]
"""Programs always present in the down-payment matrix.

VA30 is appended when ``profile.va_eligible`` (gated by Plan 14-02 Helper 2);
Jumbo30 is appended when ``listing.price`` exceeds the conforming limit for the
household's county (gated by ``lib.rules.loan_type.classify`` returning "jumbo").
"""

_CONV_PMI_ANNUAL_RATE: Final[Decimal] = Decimal("0.0075")
"""Per RESEARCH Pitfall 1 approach 2: 75bps annual conventional PMI estimate.

Surfaced as ``PMI-RATE-ESTIMATED-0.0075`` in ``eligible_reasons`` for cells
with LTV > 0.80, so the report copy can flag that the PMI figure is a
v1.1 estimate (real PMI is bureau-specific — MGIC / Genworth / Radian
all differ; industry rule-of-thumb is 50bps to 125bps depending on
credit score / LTV bucket).
"""

_CONV_5_1_ARM_TERMS: Final[ARMTerms] = ARMTerms(
    initial_period_months=60,
    reset_period_months=12,
    initial_cap_bps=500,
    periodic_cap_bps=200,
    lifetime_cap_bps=500,
    floor_rate=Decimal("0.025"),
    margin_bps=250,
    index_series_id="MORTGAGE30US",
)
"""Per RESEARCH Pitfall 8: conventional 5/1 ARM defaults used in the ARM-reset
stress (D-14-STRESS-03 — ARM-reset stress fires for Conv30 only).

Full ARMTerms shape supplied: Phase 5 D-02 requires ``floor_rate`` explicitly
(no default) — defaulting matches the AmericU 5/6 SOFR ARM disclosure cited in
references/arm-mechanics.md. Plan 14-03 consumes this constant in its
stress block builder.
"""

_CLOSING_COSTS_PCT: Final[Decimal] = Decimal("0.03")
"""Per RESEARCH Assumption A7: 3% of loan_amount estimate for cash-to-close.

ProgramResult.closing_costs_estimated defaults to True to flag that this is a
v1.1 estimate rather than a per-jurisdiction itemized closing-cost table.
"""

DEFAULT_CONFORMING_TERM_MONTHS: Final[int] = 360
"""360-month default term for Conv30 / FHA30 / VA30 / Jumbo30."""

DEFAULT_CONFORMING_15_TERM_MONTHS: Final[int] = 180
"""180-month term for Conv15."""


# ---------------------------------------------------------------------------
# Per-cell + matrix output models
# ---------------------------------------------------------------------------


class ProgramResult(BaseModel):
    """One cell of the DownPaymentMatrix (per RESEARCH §"Pattern 1: ProgramResult").

    Per D-14-MATRIX-02: every numeric field is populated regardless of
    eligibility, so the Verdict (Plan 14-04) can cite the specific predicate
    breach with the actual computed value (e.g., "DTI=51% — DTI-CAP-CONV").

    Per Phase 8 D-03 + RESEARCH Pitfall 10: summary scalars only — no
    ``list[Payment]`` schedule attached. The full schedule is recomputable from
    program x dp_pct x today's rate; the AnalysisReport surface stays under
    Phase 11's SC-5 30k-token budget.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    program: Literal["Conv30", "Conv15", "FHA30", "VA30", "Jumbo30"]
    down_payment_pct: Rate
    loan_amount: Money
    """Financed amount. For FHA, includes UFMIP per Phase 4 D-03; for VA,
    includes funding fee per W-3."""
    monthly_pi: Money
    monthly_tax: Money
    monthly_insurance: Money
    monthly_hoa: Money
    monthly_mi: Money
    """PMI / MIP / funding-fee-monthly equivalent; Decimal("0.00") when N/A."""
    piti: Money
    cash_to_close: Money
    dti_back: Rate
    ltv: Rate
    eligible: bool
    blocker_reasons: list[str] = Field(default_factory=list)
    """When ``eligible=False``: the blocked_by citation read VERBATIM from
    ``lib.affordability.AffordabilityResponse.blocked_by`` (PATTERNS.md L437-442).
    """
    eligible_reasons: list[str] = Field(default_factory=list)
    """Soft signals tagged at cell-construction time, e.g.,
    "PMI-RATE-ESTIMATED-0.0075", "VA-RESIDUAL-SYNTHESIZED-V1",
    "VA-FUNDING-FEE-FINANCED"."""
    closing_costs_estimated: bool = True
    """Per Assumption A7: 3% of loan_amount estimate; flagged for the report."""


class DownPaymentMatrix(BaseModel):
    """The full program x DP fan-out (D-14-MATRIX-01).

    cell count = len(programs_present) x len(down_payment_pcts) = 24 in the
    non-jumbo case (3 base programs + VA optional, 6 DPs) or 30 when jumbo
    triggers (D-14-MATRIX-03).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    cells: list[ProgramResult]
    programs_present: list[str]
    down_payment_pcts: list[Rate]


# ---------------------------------------------------------------------------
# Stress block (D-14-STRESS-01: preferred-DP only — fan-out lands in Plan 14-03)
# ---------------------------------------------------------------------------


class StressRow(BaseModel):
    """One stress-test row at preferred DP (mirrors RESEARCH.md L317-328)."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    program: str
    stress_kind: Literal["rate_shock", "income_shock", "arm_reset"]
    baseline_piti: Money
    stressed_piti: Money | None = None
    stressed_dti_back: Rate
    breaches_dti_ceiling: bool
    blocker_reasons: list[str] = Field(default_factory=list)


class StressBlock(BaseModel):
    """Stress fan-out across eligible programs at preferred DP (D-14-STRESS-01)."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    preferred_down_payment_pct: Rate
    rows: list[StressRow]


# ---------------------------------------------------------------------------
# Refi block (D-14-REFI-02: two scenarios per program from FRED current)
# ---------------------------------------------------------------------------


class RefiRow(BaseModel):
    """Per-program refi scenario row (per RESEARCH Pitfall 3 — signed fields
    use raw Decimal, NOT the Money alias which has ``ge=Decimal("0")``).

    monthly_savings can be negative when the target rate is HIGHER than the
    lock rate (refi-from-Conv15 to a Conv30-at-FRED scenario is the obvious
    case). npv_60mo can be negative when monthly savings x 60 do not exceed
    estimated closing costs.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    program: str
    target_rate: Rate
    scenario_label: Literal["minus_100bps", "fred_times_0_85"]
    monthly_savings: Decimal = Field(strict=True, max_digits=14, decimal_places=2)
    breakeven_months: int | None = None
    npv_60mo: Decimal = Field(strict=True, max_digits=14, decimal_places=2)


class RefiBlock(BaseModel):
    """Refi scan at preferred DP (D-14-REFI-03: two scenarios per eligible program)."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    rows: list[RefiRow]


# ---------------------------------------------------------------------------
# Points block (1pt + 2pt buydown per eligible program at preferred DP)
# ---------------------------------------------------------------------------


class PointsRow(BaseModel):
    """Per-program points-buydown row."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    program: str
    points_purchased: Literal[1, 2]
    rate_drop: Rate
    """e.g., Decimal("0.002500") per point (Assumption A3 default)."""
    simple_breakeven_months: int | None = None
    npv_breakeven_months: int | None = None
    note: str | None = None
    """e.g., "WARNING-NO-POINTS-FOR-FHA-VA" when applicable."""


class PointsBlock(BaseModel):
    """Points fan-out at preferred DP."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    rows: list[PointsRow]


# ---------------------------------------------------------------------------
# Tax block (IRS Pub 936 — first-year interest + $750k cap awareness)
# ---------------------------------------------------------------------------


class TaxBlock(BaseModel):
    """IRS Pub 936 first-year deductibility (per RESEARCH.md L363-368).

    Phase 14 ships the structured numbers + the over-cap boolean; Phase 15
    decides whether to format the partial-deduction dollar amount or surface
    a "see CPA" callout (CONTEXT §"Claude's Discretion": over-cap formatting).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    first_year_interest_per_program: dict[str, Money]
    over_750k_cap_per_program: dict[str, bool]
    qualified_loan_limit: Money
    filing_status: Literal["single", "mfj", "mfs", "hoh"]


# ---------------------------------------------------------------------------
# Verdict (Plan 14-04 ships verdict synthesis; this module ships the shape)
# ---------------------------------------------------------------------------


class VerdictReason(BaseModel):
    """One falsifiable reason in a Verdict (per RESEARCH.md L378-384 +
    PATTERNS.md L447-453 + CONTEXT D-14-VERDICT-04).

    ``computed_value`` is a string (NOT Decimal) so the field can carry
    polymorphic numeric formats — dollars, rates, integer counts — at the
    schema boundary; Phase 15 picks the display format.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    predicate_code: str
    computed_value: str
    program: str | None = None
    dp_pct: Rate | None = None


class Verdict(BaseModel):
    """The GO / WATCH / NO_GO outcome with falsifiable reasons."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    level: Literal["GO", "WATCH", "NO_GO"]
    headline_reason: str
    reasons: list[VerdictReason]


# ---------------------------------------------------------------------------
# AnalysisReport — the top-level Phase 14 contract (D-14-MODELS-04)
# ---------------------------------------------------------------------------


class AnalysisReport(BaseModel):
    """The top-level contract Phase 15's ``lib/property_report.py`` consumes.

    Field declaration order is LOAD-BEARING: matrix appears BEFORE verdict per
    Phase 8 D-02 inheritance — the matrix is the math substrate the verdict
    cites, so the schema reads naturally top-to-bottom in the formatter.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    listing_snapshot: PropertyListing
    household_snapshot_hash: str
    """SHA256(household.model_dump_json()) — pins which Household generated
    the report (mirrors Phase 13's content-SHA256 audit pattern)."""
    fetched_at: datetime
    fred_mortgage_30us: Rate
    fred_mortgage_15us: Rate
    matrix: DownPaymentMatrix
    stress: StressBlock
    refi: RefiBlock
    points: PointsBlock
    tax: TaxBlock
    verdict: Verdict
    warnings: list[str] = Field(default_factory=list)
    """e.g., "MissingCountyDataError", "PMI-RATE-ESTIMATED" — aggregated from
    cell-construction + matrix-assembly time."""


# ---------------------------------------------------------------------------
# Top-level entrypoint stub — body lands in Plan 14-05
# ---------------------------------------------------------------------------


def analyze(*args: object, **kwargs: object) -> AnalysisReport:
    """Top-level Phase 14 entrypoint. Implementation lands in Plan 14-05.

    Signature (final): ``analyze(listing: PropertyListing, household: Household,
    profile: Profile) -> AnalysisReport``. The body composes
    ``_build_matrix`` (Plan 14-02, Helper 5) + stress/refi/points/tax blocks
    (Plan 14-03) + ``synthesize_verdict`` (Plan 14-04) into the AnalysisReport.
    """
    raise NotImplementedError("analyze() body lands in Plan 14-05")
