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

from datetime import (  # Pydantic resolves annotations at runtime
    UTC,
    datetime,
)
from decimal import Decimal
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from lib.affordability import (
    Applicant,
    EscrowInputs,
    ForwardModeRequest,
    LocationFIPS,
    MonthlyDebts,
    VAInputs,
)
from lib.affordability import (
    Household as AffordabilityHousehold,
)
from lib.affordability import (
    evaluate as affordability_evaluate,
)
from lib.amortize import build_schedule
from lib.arm import ARMTerms
from lib.fred_cache import CACHE_DIR, get_cached_or_fetch, with_cache_lock
from lib.household import Household  # noqa: TC001
from lib.models import Loan, Money, Rate  # Pydantic resolves annotations at runtime
from lib.money import quantize_cents, quantize_rate
from lib.profile import Profile  # noqa: TC001
from lib.property_listing import (  # noqa: TC001  # Pydantic resolves annotations at runtime
    PropertyListing,
    ProvenancedMoney,
)
from lib.rules.fha_mip import compute as fha_mip_compute
from lib.rules.loan_type import MissingCountyDataError
from lib.rules.loan_type import classify as classify_loan_type
from lib.rules.types import County
from lib.rules.va_funding_fee import compute as va_funding_fee_compute

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
# Private composition helpers (Plan 14-02 Task 2)
# ---------------------------------------------------------------------------


def _unwrap_provenanced(
    pm: ProvenancedMoney | None,
    default: Decimal = Decimal("0.00"),
) -> Decimal:
    """Safely unwrap a ProvenancedMoney. Returns ``default`` when ``pm`` is None
    OR ``pm.value`` is None (Phase 13 ProvenancedMoney.value is ``Money | None``
    — a present wrapper with a None value is a legitimate gap-fill envelope
    state). Prevents TypeError from ``None / Decimal("12")`` in escrow division
    paths. Resolves Plan 14-PLAN-CHECK B-4.
    """
    return pm.value if (pm is not None and pm.value is not None) else default


def _todays_rate_per_program(program: str) -> Decimal:
    """Return today's lock rate for ``program`` from FRED cache.

    Per D-14-REFI-02:
      - Conv30, FHA30, VA30, Jumbo30 -> MORTGAGE30US (acceptable v1.0 proxy)
      - Conv15                        -> MORTGAGE15US
      - Conv30-ARM-5-1                -> MORTGAGE30US minus 25bps heuristic

    Every read serializes through ``with_cache_lock`` per Pitfall 9. When
    ``get_cached_or_fetch`` raises NotImplementedError (cache cold, no
    fetcher injected) the call is converted to a ValueError that names the
    CLI invocation that refreshes the cache, so callers can recover.
    """
    series_id: str
    delta: Decimal
    if program == "Conv15":
        series_id = "MORTGAGE15US"
        delta = Decimal("0")
    elif program == "Conv30-ARM-5-1":
        series_id = "MORTGAGE30US"
        delta = Decimal("-0.0025")
    else:
        # Conv30 / FHA30 / VA30 / Jumbo30
        series_id = "MORTGAGE30US"
        delta = Decimal("0")

    with with_cache_lock(CACHE_DIR, reason=f"property-analysis read {series_id}"):
        try:
            entry = get_cached_or_fetch(series_id, fetcher=None)
        except NotImplementedError as exc:
            raise ValueError(
                f"FRED cache cold for {series_id}; run "
                f"scripts/fred_cli.py get {series_id} --latest to refresh"
            ) from exc

    raw = Decimal(str(entry["value"]))
    return quantize_rate(raw + delta)


def _determine_programs(
    listing: PropertyListing,
    household: Household,
    profile: Profile,
) -> tuple[list[str], list[str]]:
    """Return (programs, warnings) for the matrix fan-out.

    Per CONTEXT D-14-MATRIX-03 + Pitfall 5: jumbo trigger uses
    ``County(state_fips, county_fips, name)`` from Household FIPS (NOT zip).
    MissingCountyDataError from classify() degrades gracefully — append a
    "MissingCountyDataError" string to warnings and return base programs.
    """
    programs: list[str] = list(PROGRAMS_BASE)
    warnings: list[str] = []
    if profile.va_eligible:
        programs.append("VA30")
    county = County(
        state_fips=household.state_fips,
        county_fips=household.county_fips,
        name=household.county_name,
    )
    try:
        classification = classify_loan_type(
            quantize_cents(listing.price), county, program="conventional"
        )
        if classification == "jumbo":
            programs.append("Jumbo30")
    except MissingCountyDataError:
        warnings.append("MissingCountyDataError")
    return programs, warnings


def _compute_cash_to_close(
    loan_amount: Decimal,
    down_payment: Decimal,
    ufmip_not_financed: Decimal = Decimal("0"),
) -> Decimal:
    """Per Assumption A7: cash_to_close = down_payment + 3% loan_amount + any
    non-financed UFMIP. In v1.1 UFMIP and VA funding fee are both FINANCED INTO
    principal (Phase 4 D-03; W-3) so ``ufmip_not_financed`` defaults to 0.
    """
    return quantize_cents(down_payment + loan_amount * _CLOSING_COSTS_PCT + ufmip_not_financed)


def _affordability_target_loan_type(
    program: str,
) -> Literal["conventional", "fha", "va", "jumbo"]:
    """Map Plan 14 program literal to affordability's target_loan_type."""
    if program in ("Conv30", "Conv15"):
        return "conventional"
    if program == "Jumbo30":
        return "jumbo"
    if program == "FHA30":
        return "fha"
    if program == "VA30":
        return "va"
    raise ValueError(f"unrecognized program: {program!r}")


def _build_program_result(
    program: str,
    dp_pct: Decimal,
    listing: PropertyListing,
    household: Household,
    profile: Profile,
    annual_rate: Decimal,
) -> ProgramResult:
    """Per-cell composition engine (D-14-MATRIX-01 + D-14-MATRIX-02).

    Mirrors ``lib.affordability.evaluate_forward`` (L805-949) shape but operates
    on Phase 14's Household / Profile / PropertyListing inputs. Delegates
    regulatory math to existing predicates: lib.amortize.build_schedule for
    P&I, lib.rules.fha_mip.compute for FHA UFMIP/MIP, lib.rules.va_funding_fee
    .compute for VA funding fee, lib.affordability.evaluate for eligibility.

    Per D-14-MATRIX-02 every numeric field is populated regardless of
    eligibility, so a downstream Verdict can cite the predicate breach with
    the actual computed value.

    Iteration-2 fixes baked in:
      B-2: VA cells synthesize VAInputs deterministically.
      B-4: ProvenancedMoney unwrap routes through ``_unwrap_provenanced``.
      W-3: VA funding fee FINANCED INTO principal; monthly_mi=0 for VA.
    """
    eligible_reasons: list[str] = []

    # Step 1 — price / down-payment / base loan
    price = quantize_cents(listing.price)
    down_payment = quantize_cents(price * dp_pct)
    base_loan_amount = quantize_cents(price - down_payment)

    # Step 2 — term
    term_months = (
        DEFAULT_CONFORMING_15_TERM_MONTHS if program == "Conv15" else DEFAULT_CONFORMING_TERM_MONTHS
    )

    # Step 3 — initial MI / financed-principal calc per program
    loan_type: Literal["fixed", "fha", "va"]
    financed_principal: Decimal
    monthly_mi: Decimal
    if program in ("Conv30", "Conv15", "Jumbo30"):
        loan_type = "fixed"
        provisional_ltv = base_loan_amount / price
        if provisional_ltv > Decimal("0.80"):
            monthly_mi = quantize_cents(base_loan_amount * _CONV_PMI_ANNUAL_RATE / Decimal("12"))
            eligible_reasons.append("PMI-RATE-ESTIMATED-0.0075")
        else:
            monthly_mi = Decimal("0.00")
        financed_principal = base_loan_amount
    elif program == "FHA30":
        loan_type = "fha"
        pre_loan = Loan(
            principal=base_loan_amount,
            annual_rate=annual_rate,
            term_months=DEFAULT_CONFORMING_TERM_MONTHS,
            loan_type="fha",
        )
        mip = fha_mip_compute(
            loan=pre_loan,
            original_property_value=price,
            endorsement_date=datetime.now(UTC).date(),
        )
        financed_principal = quantize_cents(base_loan_amount + mip.ufmip)
        monthly_mi = quantize_cents(financed_principal * mip.annual_mip_pct / Decimal("12"))
    elif program == "VA30":
        loan_type = "va"
        funding_fee = va_funding_fee_compute(
            loan_amount=base_loan_amount,
            down_payment_pct=dp_pct,
            is_first_use=True,
            loan_purpose="purchase",
            is_exempt_from_funding_fee=False,
        )
        # W-3: finance the funding fee into principal (mirrors Phase 4 D-03
        # financed-UFMIP convention). monthly_mi stays 0 — the amortization
        # captures the funding-fee cost via the larger monthly_pi.
        financed_principal = quantize_cents(base_loan_amount + funding_fee)
        monthly_mi = Decimal("0.00")
        eligible_reasons.append("VA-FUNDING-FEE-FINANCED")
    else:
        raise ValueError(f"unrecognized program: {program!r}")

    # Step 5 — monthly_pi via Phase 3 build_schedule on financed principal
    loan = Loan(
        principal=financed_principal,
        annual_rate=annual_rate,
        term_months=term_months,
        loan_type=loan_type,
    )
    schedule = build_schedule(loan, frequency="monthly")
    monthly_pi = schedule.monthly_pi

    # Step 6 — escrow components (B-4: guarded unwrap)
    monthly_tax = quantize_cents(_unwrap_provenanced(listing.tax_annual) / Decimal("12"))
    monthly_insurance = quantize_cents(
        _unwrap_provenanced(listing.insurance_estimate_annual) / Decimal("12")
    )
    monthly_hoa = quantize_cents(_unwrap_provenanced(listing.hoa_monthly))

    # Step 7 — PITI: quantize ONCE at end (Pitfall 6)
    piti_pre = monthly_pi + monthly_tax + monthly_insurance + monthly_hoa + monthly_mi
    piti = quantize_cents(piti_pre)

    # Step 8 — DTI back-end
    dti_back = quantize_rate((piti + household.monthly_obligations) / household.monthly_income)

    # Step 9 — LTV
    ltv = quantize_rate(financed_principal / price)

    # Step 10 — cash_to_close
    cash_to_close = _compute_cash_to_close(
        base_loan_amount, down_payment, ufmip_not_financed=Decimal("0")
    )

    # Step 11 — affordability eligibility (B-2: VA-aware request construction)
    target_loan_type = _affordability_target_loan_type(program)
    va_inputs: VAInputs | None = None
    if program == "VA30":
        va_inputs = VAInputs(
            region="northeast",
            family_size=2,
            actual_residual_income=quantize_cents(household.monthly_income * Decimal("0.5")),
        )
        eligible_reasons.append("VA-RESIDUAL-SYNTHESIZED-V1")

    # Map the Phase-14 single-applicant snapshot into Phase-4's multi-applicant
    # AffordabilityHousehold shape. Per W-5 the monthly_obligations collapse to
    # the "other" bucket of MonthlyDebts; per the LocationFIPS contract
    # (lib/affordability.py L347-351) state is a 2-char display field — we use
    # household.state_fips (always 2 chars) since Phase 14 Household does not
    # carry a state abbreviation.
    affordability_household = AffordabilityHousehold(
        location=LocationFIPS(
            state_fips=household.state_fips,
            county_fips=household.county_fips,
            county_name=household.county_name,
            state=household.state_fips,
        ),
        applicants=[
            Applicant(
                name="primary",
                gross_monthly_income=household.monthly_income,
                credit_score=household.fico,
            )
        ],
        size=1,
        monthly_debts=MonthlyDebts(other=household.monthly_obligations),
        escrow=EscrowInputs(
            property_tax_monthly=monthly_tax,
            insurance_monthly=monthly_insurance,
            hoa_monthly=monthly_hoa,
        ),
        va=va_inputs,
    )

    # monthly_pmi conditional: Phase 4 _validate_common requires it for
    # conventional + LTV > 0.80 (RESEARCH Open Q#1). Pass the cell's monthly_mi
    # for those cells; None otherwise.
    monthly_pmi_for_request: Money | None = None
    if target_loan_type == "conventional" and ltv > Decimal("0.80"):
        monthly_pmi_for_request = monthly_mi

    forward_request = ForwardModeRequest(
        household=affordability_household,
        max_dti=Decimal("0.500000"),
        target_loan_type=target_loan_type,
        term_months=term_months,
        annual_rate=annual_rate,
        loan_amount=base_loan_amount,
        property_value=price,
        monthly_pmi=monthly_pmi_for_request,
    )
    response = affordability_evaluate(forward_request)

    eligible: bool
    blocker_reasons: list[str]
    if response.blocked:
        eligible = False
        # PATTERNS.md L437-442 — read VERBATIM, never reformat.
        blocker_reasons = [response.blocked_by] if response.blocked_by is not None else []
    else:
        eligible = True
        blocker_reasons = []

    # Step 12 — assemble ProgramResult with all numerics populated
    # regardless of eligibility (D-14-MATRIX-02).
    return ProgramResult(
        program=program,  # type: ignore[arg-type]
        down_payment_pct=quantize_rate(dp_pct),
        loan_amount=financed_principal,
        monthly_pi=monthly_pi,
        monthly_tax=monthly_tax,
        monthly_insurance=monthly_insurance,
        monthly_hoa=monthly_hoa,
        monthly_mi=monthly_mi,
        piti=piti,
        cash_to_close=cash_to_close,
        dti_back=dti_back,
        ltv=ltv,
        eligible=eligible,
        blocker_reasons=blocker_reasons,
        eligible_reasons=eligible_reasons,
    )


def _build_matrix(
    listing: PropertyListing,
    household: Household,
    profile: Profile,
    todays_rates: dict[str, Decimal],
) -> tuple[DownPaymentMatrix, list[str]]:
    """Fan out across programs x DPs to produce the full DownPaymentMatrix
    (D-14-MATRIX-01) plus a list of matrix-assembly warnings.

    ``todays_rates`` is a dict keyed by program name (Conv30, Conv15, FHA30,
    VA30, Jumbo30) — caller obtains via ``_todays_rate_per_program`` per
    D-14-REFI-02. Matrix carries len(programs) * 6 cells (24 in the base
    case, 30 when jumbo triggers).
    """
    programs, warnings = _determine_programs(listing, household, profile)
    cells: list[ProgramResult] = []
    for program in programs:
        rate = todays_rates[program]
        for dp_pct in DOWN_PAYMENT_PCTS:
            cells.append(_build_program_result(program, dp_pct, listing, household, profile, rate))
    matrix = DownPaymentMatrix(
        cells=cells,
        programs_present=programs,
        down_payment_pcts=list(DOWN_PAYMENT_PCTS),
    )
    return matrix, warnings


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
