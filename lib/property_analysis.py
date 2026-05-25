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
  - B-2 (VA-program affordability construction): VA cells are not approved
    without caller-supplied residual-income inputs. Phase 14's public
    Household/Profile models do not carry those fields, so VA30 cells surface
    "VA-RESIDUAL-NOT-SUPPLIED" as an ineligible blocker instead of fabricating
    residual income from gross monthly income.
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

import hashlib
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
)
from lib.affordability import (
    Household as AffordabilityHousehold,
)
from lib.affordability import (
    evaluate as affordability_evaluate,
)
from lib.amortize import build_schedule
from lib.arm import ARMRequest, ARMTerms
from lib.fred_cache import CACHE_DIR, get_cached_or_fetch, with_cache_lock
from lib.household import Household  # noqa: TC001
from lib.models import (  # Pydantic resolves annotations at runtime
    Loan,
    Money,
    NonNegativeRatio,
    Rate,
)
from lib.money import quantize_cents, quantize_rate
from lib.points import PointsRequestFromLoans
from lib.points import evaluate as points_evaluate
from lib.profile import Profile  # noqa: TC001
from lib.property_listing import (  # noqa: TC001  # Pydantic resolves annotations at runtime
    PropertyListing,
    ProvenancedMoney,
)
from lib.refinance import RateAndTermRefiRequest
from lib.refinance import evaluate as refi_evaluate
from lib.rules.fha_mip import compute as fha_mip_compute
from lib.rules.irs_pub936 import qualified_loan_limit as pub936_qualified_loan_limit
from lib.rules.loan_type import MissingCountyDataError
from lib.rules.loan_type import classify as classify_loan_type
from lib.rules.types import County
from lib.rules.va_funding_fee import compute as va_funding_fee_compute
from lib.stress import (
    ArmResetRequest,
    IncomeShockRequest,
    RatePath,
    RateShockRequest,
)
from lib.stress import StressRow as UpstreamStressRow
from lib.stress import evaluate as stress_evaluate

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

# B-5 (Plan 14-03 PLAN-CHECK fix): Per-program DTI ceilings. A hardcoded 0.50
# for all programs is silently wrong for 3 of 5 programs (false-positive WATCH
# on FHA cells, false-negative GO on VA cells). Each entry below carries the
# regulatory source as a comment for grep-discoverability.
_DTI_CEILING_BY_PROGRAM: Final[dict[str, Decimal]] = {
    # Conventional: Fannie / Freddie ATR-QM safe harbor; QM Patch sunset 2021
    # (CFPB General QM Final Rule, 2020-12-29; back-end ratio target 0.43 with
    # APR-APOR-spread test, lender-conservative cap 0.50).
    "Conv30": Decimal("0.50"),
    "Conv15": Decimal("0.50"),
    # FHA: HUD Handbook 4000.1 II.A.5.d max back-end ratio (compensating-factors
    # path; baseline 0.43 + 0.14 cushion for strong residual / reserves).
    "FHA30": Decimal("0.57"),
    # VA: VA Lender Handbook 26-7 Ch. 4 §7 — 41% baseline back-end ratio
    # (residual-income gating supplies the upside cushion separately).
    "VA30": Decimal("0.41"),
    # Jumbo: ATR/QM safe harbor for non-QM jumbo (lender-conservative; most
    # post-QM Patch jumbo programs cap at 43%).
    "Jumbo30": Decimal("0.43"),
}
"""Per-program DTI ceilings used by the stress block (B-5 PLAN-CHECK fix).

The ``IncomeShockRequest.dti_threshold`` field and the ``breaches_dti_ceiling``
flag on every stress kind are evaluated against this per-program ceiling, NOT
a hardcoded 0.50. Citations in the inline comment.
"""

_REFI_CLOSING_COSTS_PCT: Final[Decimal] = Decimal("0.02")
"""Industry rule-of-thumb estimate for rate-and-term refi closing costs (2% of
new loan balance). Plan 14-03 ``_build_refi_block`` uses this scalar; a future
phase may swap in a per-jurisdiction itemized table. Distinct from
``_CLOSING_COSTS_PCT`` (purchase) — refi closing is typically lower because
title insurance is reissue-rated and origination fees are lender-promo
sensitive."""

_REFI_NPV_HORIZON_MONTHS: Final[int] = 60
"""5-year NPV horizon for the refi scan (D-14-REFI-02 + Phase 6 D-11). Matches
the ``RefiRow.npv_60mo`` field semantics on Phase 14's RefiRow."""

_POINTS_CONV_FAMILY: Final[frozenset[str]] = frozenset({"Conv30", "Conv15", "Jumbo30"})
"""Programs for which points-buydown breakeven is modeled (Open Question 1
resolution in RESEARCH). FHA + VA cells get a ``WARNING-NO-POINTS-FOR-FHA-VA``
note instead of a breakeven figure — FHA UFMIP / VA funding fee dominate
deferred-cost economics, and discount points on those programs require
case-by-case loan-officer modeling outside Phase 14's v1.1 scope."""

_POINTS_HOLD_PERIOD_MONTHS: Final[int] = 60
"""5-year hold horizon for the points-buydown NPV walk. Matches the refi NPV
horizon and the standard mortgage-industry 5-year-tenure assumption."""

_RATE_SHOCK_BPS: Final[Decimal] = Decimal("0.02")
"""+200bps rate shock magnitude (D-14-STRESS-01)."""

_INCOME_SHOCK_REDUCTION: Final[Decimal] = Decimal("0.30")
"""-30% income shock magnitude (D-14-STRESS-01)."""

_STRESS_RATE_SHOCK_CODE: Final[str] = "STRESS-RATE-SHOCK-200BPS"
_STRESS_INCOME_SHOCK_CODE: Final[str] = "STRESS-INCOME-SHOCK-30PCT"
_STRESS_ARM_RESET_CODE: Final[str] = "STRESS-ARM-RESET-PEAK-CAP"


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
    dti_back: NonNegativeRatio
    ltv: NonNegativeRatio
    eligible: bool
    blocker_reasons: list[str] = Field(default_factory=list)
    """When ``eligible=False``: the blocked_by citation read VERBATIM from
    ``lib.affordability.AffordabilityResponse.blocked_by`` (PATTERNS.md L437-442).
    """
    eligible_reasons: list[str] = Field(default_factory=list)
    """Soft signals tagged at cell-construction time, e.g.,
    "PMI-RATE-ESTIMATED-0.0075", "VA-FUNDING-FEE-FINANCED"."""
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
    stressed_dti_back: NonNegativeRatio
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

    if entry.get("value") is None:
        raise ValueError(
            f"FRED cache for {series_id} has value=None; run "
            f"scripts/fred_cli.py get {series_id} --latest to refresh"
        )
    raw = Decimal(str(entry["value"]))
    if raw > Decimal("1"):
        raw = raw / Decimal("100")
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


def _build_affordability_forward_request(
    *,
    program: str,
    down_payment_pct: Decimal,
    listing: PropertyListing,
    household: Household,
    annual_rate: Decimal,
    monthly_tax: Decimal,
    monthly_insurance: Decimal,
    monthly_hoa: Decimal,
    monthly_mi: Decimal,
    ltv: Decimal,
) -> ForwardModeRequest:
    price = quantize_cents(listing.price)
    base_loan_amount = quantize_cents(price - quantize_cents(price * down_payment_pct))
    target_loan_type = _affordability_target_loan_type(program)
    term_months = (
        DEFAULT_CONFORMING_15_TERM_MONTHS if program == "Conv15" else DEFAULT_CONFORMING_TERM_MONTHS
    )

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
        va=None,
    )

    monthly_pmi_for_request: Money | None = None
    if target_loan_type == "conventional" and ltv > Decimal("0.80"):
        monthly_pmi_for_request = monthly_mi

    return ForwardModeRequest(
        household=affordability_household,
        max_dti=_DTI_CEILING_BY_PROGRAM[program],
        target_loan_type=target_loan_type,
        term_months=term_months,
        annual_rate=annual_rate,
        loan_amount=base_loan_amount,
        property_value=price,
        monthly_pmi=monthly_pmi_for_request,
    )


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
      B-2: VA cells require explicit residual-income data and are blocked when
      Phase 14's input models do not carry it.
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

    # Step 11 — affordability eligibility (B-2: VA residual data is required)
    eligible: bool
    blocker_reasons: list[str]
    forward_request = _build_affordability_forward_request(
        program=program,
        down_payment_pct=dp_pct,
        listing=listing,
        household=household,
        annual_rate=annual_rate,
        monthly_tax=monthly_tax,
        monthly_insurance=monthly_insurance,
        monthly_hoa=monthly_hoa,
        monthly_mi=monthly_mi,
        ltv=ltv,
    )
    try:
        response = affordability_evaluate(forward_request)
    except NotImplementedError as exc:
        # FHA / VA loan_amount above the county ceiling raises here (per
        # lib/rules/loan_type.py L135). D-14-MATRIX-02 mandates explicit
        # ineligible rows with populated numerics; mark the cell ineligible
        # and surface a stable blocker code rather than propagating the crash.
        eligible = False
        if program == "FHA30":
            blocker_reasons = [f"HUD-LIMIT-CEILING-EXCEEDED: {exc}"]
        elif program == "VA30":
            blocker_reasons = [f"VA-LIMIT-CEILING-EXCEEDED: {exc}"]
        else:
            blocker_reasons = [f"LOAN-TYPE-CLASSIFY-NOT-IMPLEMENTED: {exc}"]
    else:
        if response.blocked:
            eligible = False
            # PATTERNS.md L437-442 — read VERBATIM, never reformat.
            blocker_reasons = [response.blocked_by] if response.blocked_by is not None else []
        elif cash_to_close > household.liquid_reserves:
            eligible = False
            blocker_reasons = ["CASH-TO-CLOSE-RESERVES"]
        else:
            eligible = True
            blocker_reasons = []

    if program == "VA30":
        if dti_back > _DTI_CEILING_BY_PROGRAM[program] and "DTI-CAP-VA" not in blocker_reasons:
            eligible = False
            blocker_reasons.append("DTI-CAP-VA")
        if (
            cash_to_close > household.liquid_reserves
            and "CASH-TO-CLOSE-RESERVES" not in blocker_reasons
        ):
            eligible = False
            blocker_reasons.append("CASH-TO-CLOSE-RESERVES")
        if "VA-RESIDUAL-NOT-SUPPLIED" not in blocker_reasons:
            eligible = False
            blocker_reasons.append("VA-RESIDUAL-NOT-SUPPLIED")

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
    down_payment_pcts = _matrix_down_payment_pcts(household.preferred_down_payment_pct)
    cells: list[ProgramResult] = []
    for program in programs:
        rate = todays_rates[program]
        for dp_pct in down_payment_pcts:
            cells.append(_build_program_result(program, dp_pct, listing, household, profile, rate))
    matrix = DownPaymentMatrix(
        cells=cells,
        programs_present=programs,
        down_payment_pcts=down_payment_pcts,
    )
    return matrix, warnings


def _matrix_down_payment_pcts(preferred_dp: Decimal) -> list[Decimal]:
    """Return the fixed ladder plus the user's preferred DP when absent."""
    target = quantize_rate(preferred_dp)
    values = [quantize_rate(dp) for dp in DOWN_PAYMENT_PCTS]
    if target not in values:
        values.append(target)
        values.sort()
    return values


# ---------------------------------------------------------------------------
# Plan 14-03 auxiliary-block builders (stress / refi / points / tax)
#
# All four blocks run at the user's preferred down-payment (D-14-STRESS-01),
# delegating regulatory math to lib.stress / lib.refinance / lib.points /
# lib.rules.irs_pub936. No new mathematical primitives.
# ---------------------------------------------------------------------------


def _eligible_cells_at_preferred_dp(
    matrix: DownPaymentMatrix,
    preferred_dp: Decimal,
) -> list[ProgramResult]:
    """Return preferred-DP cells eligible for auxiliary stress/refi/points blocks.

    VA rows blocked only by missing residual-income data are included for
    diagnostics while remaining ineligible for verdict synthesis.

    ``preferred_dp`` is compared via numeric equality after quantize_rate; the
    Phase-14 Household ships ``preferred_down_payment_pct`` as a Rate which is
    already quantized, but the matrix cells route through quantize_rate one more
    time, so we normalize both sides to be safe.
    """
    target = quantize_rate(preferred_dp)
    return [
        c
        for c in matrix.cells
        if c.down_payment_pct == target
        and (
            c.eligible
            or (c.program == "VA30" and c.blocker_reasons == ["VA-RESIDUAL-NOT-SUPPLIED"])
        )
    ]


def _construct_affordability_request_for_cell(
    cell: ProgramResult,
    listing: PropertyListing,
    household: Household,
    annual_rate: Decimal,
) -> ForwardModeRequest:
    """Reconstruct the Phase-4 ForwardModeRequest used by lib.affordability.evaluate."""
    return _build_affordability_forward_request(
        program=cell.program,
        down_payment_pct=cell.down_payment_pct,
        listing=listing,
        household=household,
        annual_rate=annual_rate,
        monthly_tax=cell.monthly_tax,
        monthly_insurance=cell.monthly_insurance,
        monthly_hoa=cell.monthly_hoa,
        monthly_mi=cell.monthly_mi,
        ltv=cell.ltv,
    )


def _make_cell_loan(cell: ProgramResult, current_rate: Decimal) -> Loan:
    """Build the synthetic Loan that represents this cell's financed principal
    at the current rate. Used by both the stress block (rate-shock + arm-reset)
    and the refi / points blocks.

    loan_type mapping mirrors Plan 14-02's per-cell engine: FHA30 -> "fha",
    VA30 -> "va", everything else -> "fixed". A fresh-origination convention
    is used (no origination_date so Phase 3 D-12 synthesizes one).
    """
    term_months = (
        DEFAULT_CONFORMING_15_TERM_MONTHS
        if cell.program == "Conv15"
        else DEFAULT_CONFORMING_TERM_MONTHS
    )
    loan_type: Literal["fixed", "fha", "va"]
    if cell.program == "FHA30":
        loan_type = "fha"
    elif cell.program == "VA30":
        loan_type = "va"
    else:
        loan_type = "fixed"
    return Loan(
        principal=cell.loan_amount,
        annual_rate=current_rate,
        term_months=term_months,
        loan_type=loan_type,
    )


def _stress_row_from_rate_shock(
    cell: ProgramResult,
    upstream_row: UpstreamStressRow,
    household: Household,
    ceiling: Decimal,
) -> StressRow:
    """Convert lib.stress.StressRow (rate-shock) into Phase 14 StressRow.

    Recomputes Phase 14's ``stressed_piti`` by adding the unchanged escrow +
    MI components to the upstream ``monthly_pi``; the recomputed
    ``stressed_dti_back`` uses the household's unchanged income + obligations
    (rate shock does NOT change income).
    """
    assert upstream_row.monthly_pi is not None
    stressed_monthly_pi = upstream_row.monthly_pi
    stressed_piti = quantize_cents(
        stressed_monthly_pi
        + cell.monthly_tax
        + cell.monthly_insurance
        + cell.monthly_hoa
        + cell.monthly_mi
    )
    stressed_dti = quantize_rate(
        (stressed_piti + household.monthly_obligations) / household.monthly_income
    )
    breaches = stressed_dti > ceiling
    blocker_reasons = [_STRESS_RATE_SHOCK_CODE] if breaches else []
    return StressRow(
        program=cell.program,
        stress_kind="rate_shock",
        baseline_piti=cell.piti,
        stressed_piti=stressed_piti,
        stressed_dti_back=stressed_dti,
        breaches_dti_ceiling=breaches,
        blocker_reasons=blocker_reasons,
    )


def _stress_row_from_income_shock(
    cell: ProgramResult,
    upstream_row: UpstreamStressRow,
    household: Household,
    ceiling: Decimal,
) -> StressRow:
    """Convert lib.stress.StressRow (income-shock) into Phase 14 StressRow.

    Income shock does NOT change PITI (per lib/stress.py L131 + RESEARCH L322 —
    upstream row has ``monthly_pi=None`` for income-shock). Recompute DTI from
    the matrix cell's own PITI so financed FHA/VA amounts stay aligned with the
    displayed cell economics.
    """
    _ = upstream_row
    shocked_income = household.monthly_income * (Decimal("1") - _INCOME_SHOCK_REDUCTION)
    stressed_dti = quantize_rate((cell.piti + household.monthly_obligations) / shocked_income)
    breaches = stressed_dti > ceiling
    blocker_reasons = [_STRESS_INCOME_SHOCK_CODE] if breaches else []
    return StressRow(
        program=cell.program,
        stress_kind="income_shock",
        baseline_piti=cell.piti,
        stressed_piti=None,
        stressed_dti_back=stressed_dti,
        breaches_dti_ceiling=breaches,
        blocker_reasons=blocker_reasons,
    )


def _stress_row_from_arm_reset(
    cell: ProgramResult,
    upstream_row: UpstreamStressRow,
    household: Household,
    ceiling: Decimal,
) -> StressRow:
    """Convert lib.stress.StressRow (arm-reset) into Phase 14 StressRow.

    Reads ``max_payment`` (peak monthly_pi after the reset) from the upstream
    row (lib/stress.py L138) and treats it as the stressed monthly P&I —
    rebuilds PITI + DTI from the cell's unchanged escrow / MI / income.
    """
    peak_payment = upstream_row.max_payment
    if peak_payment is None:
        # Defensive fallback (upstream arm_path always populates this; keep
        # baseline if missing so we never emit None for stressed_piti on an
        # ARM-reset row).
        peak_payment = cell.monthly_pi
    stressed_piti = quantize_cents(
        peak_payment
        + cell.monthly_tax
        + cell.monthly_insurance
        + cell.monthly_hoa
        + cell.monthly_mi
    )
    stressed_dti = quantize_rate(
        (stressed_piti + household.monthly_obligations) / household.monthly_income
    )
    breaches = stressed_dti > ceiling
    blocker_reasons = [_STRESS_ARM_RESET_CODE] if breaches else []
    return StressRow(
        program=cell.program,
        stress_kind="arm_reset",
        baseline_piti=cell.piti,
        stressed_piti=stressed_piti,
        stressed_dti_back=stressed_dti,
        breaches_dti_ceiling=breaches,
        blocker_reasons=blocker_reasons,
    )


def _build_stress_block(
    matrix: DownPaymentMatrix,
    listing: PropertyListing,
    household: Household,
    profile: Profile,
    todays_rates: dict[str, Decimal],
) -> StressBlock:
    """Fan stress tests out across programs eligible at the preferred DP
    (D-14-STRESS-01..03). Three stress kinds per eligible cell:

      1. rate_shock — current_rate + 200bps (per RateShockRequest)
      2. income_shock — -30% income (per IncomeShockRequest)
      3. arm_reset — Conv30 only; peak-cap parallel shift on the 5/1 ARM

    Programs ineligible at preferred DP are SKIPPED (D-14-STRESS-01). When no
    cells are eligible at preferred DP, rows is empty (Behavior 8).

    Upstream API signatures verified 2026-05-17 against lib/stress.py L160-260:
      - RateShockRequest.rates: list of FULL Rate values (NOT bps offsets)
      - IncomeShockRequest.reductions: shock MAGNITUDE (NOT multiplier)
      - ArmResetRequest.paths: REQUIRED (min_length=1)
    """
    preferred = household.preferred_down_payment_pct
    eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
    rows: list[StressRow] = []

    for cell in eligible_cells:
        current_rate = todays_rates[cell.program]
        cell_loan = _make_cell_loan(cell, current_rate)
        ceiling = _DTI_CEILING_BY_PROGRAM[cell.program]

        # ============================================================
        # 1. Rate shock +200bps — RateShockRequest (verified L177-189)
        # ============================================================
        shocked_rate = quantize_rate(current_rate + _RATE_SHOCK_BPS)
        rate_resp = stress_evaluate(
            RateShockRequest(
                mode="rate-shock",
                loan=cell_loan,
                rates=[current_rate, shocked_rate],  # FULL Rate values, NOT bps
                baseline_label=str(current_rate),
                scenario_label=f"{cell.program}+200bps",
            )
        )
        shocked_rate_label = str(shocked_rate)
        upstream_rate_row = next(
            (r for r in rate_resp.rows if r.label == shocked_rate_label),
            None,
        )
        if upstream_rate_row is None:
            raise ValueError(
                f"rate-shock row {shocked_rate_label!r} missing from upstream rows "
                f"{[r.label for r in rate_resp.rows]!r}"
            )
        rows.append(_stress_row_from_rate_shock(cell, upstream_rate_row, household, ceiling))

        # ============================================================
        # 2. Income shock -30% — IncomeShockRequest (verified L192-205)
        # ============================================================
        base_request = _construct_affordability_request_for_cell(
            cell, listing, household, current_rate
        )
        income_resp = stress_evaluate(
            IncomeShockRequest(
                mode="income-shock",
                base_request=base_request,
                reductions=[_INCOME_SHOCK_REDUCTION],  # shock MAGNITUDE
                dti_threshold=ceiling,  # B-5: per-program ceiling
                scenario_label=f"{cell.program}-30%-income",
            )
        )
        upstream_income_row = income_resp.rows[0]
        rows.append(_stress_row_from_income_shock(cell, upstream_income_row, household, ceiling))

        # ============================================================
        # 3. ARM reset — ArmResetRequest (verified L208-223; Conv30 only)
        # ============================================================
        if cell.program == "Conv30":
            arm_index_rate = todays_rates["Conv30-ARM-5-1"]
            arm_req = ARMRequest(
                loan=cell_loan,  # field is `loan`, NOT `base_loan`
                arm_terms=_CONV_5_1_ARM_TERMS,
                assumed_index_rate=arm_index_rate,
            )
            # paths is REQUIRED (min_length=1). Use a parallel-shift at the
            # lifetime cap to capture the peak-cap reset stress (D-14-STRESS-03).
            peak_cap_path = RatePath(
                name="parallel-shift",
                params={"shift_bps": _CONV_5_1_ARM_TERMS.lifetime_cap_bps},
            )
            arm_resp = stress_evaluate(
                ArmResetRequest(
                    mode="arm-reset",
                    base_arm_request=arm_req,
                    paths=[peak_cap_path],  # REQUIRED
                    scenario_label=f"{cell.program}-arm-peak-cap",
                )
            )
            upstream_arm_row = arm_resp.rows[0]
            rows.append(_stress_row_from_arm_reset(cell, upstream_arm_row, household, ceiling))

    return StressBlock(preferred_down_payment_pct=quantize_rate(preferred), rows=rows)


def _build_refi_block(
    matrix: DownPaymentMatrix,
    household: Household,
    todays_rates: dict[str, Decimal],
) -> RefiBlock:
    """Refi scan at the preferred DP (D-14-REFI-01..03). Exactly 2 rows per
    eligible-at-preferred-DP program: ``FRED_current - 1.00`` AND
    ``FRED_current x 0.85`` target rates.

    Each row carries the SIGNED Phase 14 Decimals (monthly_savings, npv_60mo)
    read verbatim from the upstream ``RefiResponse`` (refi engine returns
    Decimal, NOT Money — Pitfall 3). Negative values are correct for the
    rate-up scenarios that can occur when ``current_rate x 0.85`` exceeds
    ``current_rate - 0.01`` (mathematically impossible at non-trivial rates,
    but the engine sign-tracks regardless).

    Upstream API signature verified 2026-05-17 against lib/refinance.py L288-525:
      - RateAndTermRefiRequest.refi_kind: "rate_and_term" (underscore)
      - .old_remaining_months: int (NOT remaining_months)
      - .discount_rate_annual: REQUIRED (D-05)
      - resp.breakeven.npv_months: int | None (NOT npv_breakeven_months)
    """
    preferred = household.preferred_down_payment_pct
    eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
    rows: list[RefiRow] = []

    for cell in eligible_cells:
        current_rate = todays_rates[cell.program]
        new_term = (
            DEFAULT_CONFORMING_15_TERM_MONTHS
            if cell.program == "Conv15"
            else DEFAULT_CONFORMING_TERM_MONTHS
        )
        closing = quantize_cents(cell.loan_amount * _REFI_CLOSING_COSTS_PCT)

        # Scenario A: target = current_rate - Decimal("0.01") (D-14-REFI-03 FRED-1.00)
        target_a = quantize_rate(current_rate - Decimal("0.01"))
        refi_a = refi_evaluate(
            RateAndTermRefiRequest(
                refi_kind="rate_and_term",  # underscore, not hyphen
                old_loan_balance=cell.loan_amount,
                old_annual_rate=current_rate,
                old_remaining_months=new_term,  # baseline matches new term
                new_annual_rate=target_a,
                new_term_months=new_term,
                closing_costs=closing,
                discount_rate_annual=current_rate,  # REQUIRED (D-05); Phase 6 D-09 convention
                analysis_horizon_months=_REFI_NPV_HORIZON_MONTHS,
            )
        )
        rows.append(
            RefiRow(
                program=cell.program,
                target_rate=target_a,
                scenario_label="minus_100bps",
                monthly_savings=refi_a.monthly_savings,  # signed Decimal
                breakeven_months=refi_a.breakeven.npv_months,
                npv_60mo=refi_a.npv,  # signed Decimal
            )
        )

        # Scenario B: target = current_rate * Decimal("0.85") (D-14-REFI-03 FREDx0.85)
        target_b = quantize_rate(current_rate * Decimal("0.85"))
        refi_b = refi_evaluate(
            RateAndTermRefiRequest(
                refi_kind="rate_and_term",
                old_loan_balance=cell.loan_amount,
                old_annual_rate=current_rate,
                old_remaining_months=new_term,
                new_annual_rate=target_b,
                new_term_months=new_term,
                closing_costs=closing,
                discount_rate_annual=current_rate,
                analysis_horizon_months=_REFI_NPV_HORIZON_MONTHS,
            )
        )
        rows.append(
            RefiRow(
                program=cell.program,
                target_rate=target_b,
                scenario_label="fred_times_0_85",
                monthly_savings=refi_b.monthly_savings,
                breakeven_months=refi_b.breakeven.npv_months,
                npv_60mo=refi_b.npv,
            )
        )

    return RefiBlock(rows=rows)


def _build_points_block(
    matrix: DownPaymentMatrix,
    household: Household,
    todays_rates: dict[str, Decimal],
) -> PointsBlock:
    """Points-buydown breakeven at the preferred DP. Exactly 2 rows per
    eligible-at-preferred-DP program (1pt + 2pt).

    Open Question 1 resolution: Conv-family only (Conv30 / Conv15 / Jumbo30)
    runs the full PointsRequestFromLoans evaluation; FHA + VA emit rows with
    ``simple_breakeven_months=None`` + ``npv_breakeven_months=None`` +
    ``note="WARNING-NO-POINTS-FOR-FHA-VA"``.

    Assumption A3: each discount point drops the rate by 25bps
    (Decimal("0.002500"); industry rule-of-thumb).

    Upstream API signature verified 2026-05-17 against lib/points.py L85-103:
      - mode="from_loans" (underscore)
      - loan_with_points / loan_without_points (NOT discounted_loan / no_points_loan)
      - hold_period_months: int
      - discount_rate_annual: REQUIRED (D-02)
    """
    preferred = household.preferred_down_payment_pct
    eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
    rows: list[PointsRow] = []

    for cell in eligible_cells:
        current_rate = todays_rates[cell.program]
        term_months = (
            DEFAULT_CONFORMING_15_TERM_MONTHS
            if cell.program == "Conv15"
            else DEFAULT_CONFORMING_TERM_MONTHS
        )

        for points in (1, 2):
            rate_drop_raw = Decimal("0.002500") * points  # Assumption A3
            rate_drop = quantize_rate(rate_drop_raw)

            if cell.program in _POINTS_CONV_FAMILY:
                discounted_rate = quantize_rate(current_rate - rate_drop)
                loan_without_points = Loan(
                    principal=cell.loan_amount,
                    annual_rate=current_rate,
                    term_months=term_months,
                    loan_type="fixed",
                )
                loan_with_points = Loan(
                    principal=cell.loan_amount,
                    annual_rate=discounted_rate,
                    term_months=term_months,
                    loan_type="fixed",
                )
                points_cost = quantize_cents(
                    cell.loan_amount * Decimal("0.01") * Decimal(str(points))
                )

                resp = points_evaluate(
                    PointsRequestFromLoans(
                        mode="from_loans",  # underscore form (B-1)
                        points_cost=points_cost,
                        loan_with_points=loan_with_points,  # B-1 — correct field name
                        loan_without_points=loan_without_points,  # B-1 — correct field name
                        hold_period_months=_POINTS_HOLD_PERIOD_MONTHS,
                        discount_rate_annual=current_rate,  # Phase 6 D-09 convention
                    )
                )
                rows.append(
                    PointsRow(
                        program=cell.program,
                        points_purchased=points,
                        rate_drop=rate_drop,
                        simple_breakeven_months=resp.simple_breakeven_months,
                        npv_breakeven_months=resp.npv_breakeven_months,
                        note=None,
                    )
                )
            else:
                # FHA + VA: points not modeled (Open Question 1 resolution).
                rows.append(
                    PointsRow(
                        program=cell.program,
                        points_purchased=points,
                        rate_drop=rate_drop,
                        simple_breakeven_months=None,
                        npv_breakeven_months=None,
                        note="WARNING-NO-POINTS-FOR-FHA-VA",
                    )
                )

    return PointsBlock(rows=rows)


def _build_tax_block(
    matrix: DownPaymentMatrix,
    household: Household,
    profile: Profile,
    todays_rates: dict[str, Decimal],
) -> TaxBlock:
    """IRS Pub 936 first-year interest + $750k-cap awareness per program at the
    preferred DP.

    For each program eligible at the preferred DP:
      - first_year_interest = sum of the first 12 interest components of the
        amortization schedule (Phase 3 build_schedule).
      - over_750k_cap_per_program[program] = (cell.loan_amount > cap), where
        cap comes from lib.rules.irs_pub936.qualified_loan_limit with the
        defaults all False (Pitfall 11 — Phase 14 v1 = post-2017 acquisition;
        future phases can extend Profile with grandfathering booleans).

    B-6: signature pinned to ``(matrix, household, profile, todays_rates)``
    (4 args) matching Plan 14-05 callsite + must_haves.truths line 4.
    """
    preferred = household.preferred_down_payment_pct
    eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
    cap = pub936_qualified_loan_limit(filing_status=profile.filing_status)
    # Defaults: has_grandfathered_debt=False, binding_contract_*=False (Pitfall 11)

    first_year: dict[str, Money] = {}
    over_cap: dict[str, bool] = {}
    for cell in eligible_cells:
        loan = _make_cell_loan(cell, todays_rates[cell.program])
        schedule = build_schedule(loan, frequency="monthly")
        # Sum interest component of first 12 payments — start=Decimal("0") per
        # PATTERNS.md L237 (avoid int 0 contamination).
        first_year[cell.program] = quantize_cents(
            sum(
                (p.interest for p in schedule.payments[:12]),
                start=Decimal("0"),
            )
        )
        over_cap[cell.program] = cell.loan_amount > cap

    return TaxBlock(
        first_year_interest_per_program=first_year,
        over_750k_cap_per_program=over_cap,
        qualified_loan_limit=quantize_cents(cap),
        filing_status=profile.filing_status,
    )


# ---------------------------------------------------------------------------
# Top-level entrypoint (Plan 14-05) — composes the 6-step pipeline
# ---------------------------------------------------------------------------


def analyze(
    listing: PropertyListing,
    household: Household,
    profile: Profile,
    *,
    fred_mortgage_30us: Decimal | None = None,
    fred_mortgage_15us: Decimal | None = None,
) -> AnalysisReport:
    """Top-level Phase 14 entrypoint (D-14-MODELS-04). 6-step pipeline per
    RESEARCH.md L164-235:

      1. Resolve programs + county (via ``_determine_programs``).
      2. Resolve today's rate per program (FRED cache, lock-serialized via
         ``_todays_rate_per_program``); when callers pass explicit
         ``fred_mortgage_30us`` / ``fred_mortgage_15us`` overrides the FRED
         cache is bypassed entirely (test-injection path).
      3. Determine programs (Conv30/Conv15/FHA30 always; VA30 if
         ``profile.va_eligible``; Jumbo30 if classify == "jumbo").
      4. Build matrix (DownPaymentMatrix with 18, 24, or 30 cells).
      5. Build auxiliary blocks at preferred DP (StressBlock, RefiBlock,
         PointsBlock, TaxBlock).
      6. Synthesize verdict (``lib.property_verdict.synthesize``).

    Returns a frozen ``AnalysisReport`` Phase 15's ``lib.property_report`` renders.

    Raises:
        ValueError: when the FRED cache is cold AND no ``fred_mortgage_*us``
            override was supplied (re-raised from
            ``_todays_rate_per_program``; Phase 15 CLI catches at the
            always-exit-0 envelope boundary).
        pydantic.ValidationError: when any input violates the model contract.
    """
    # Local import to avoid the circular dependency with lib.property_verdict
    # (which imports DownPaymentMatrix / StressBlock / Verdict / VerdictReason
    # from this module at top level).
    from lib.property_verdict import synthesize

    warnings: list[str] = []

    # Step 1 + 3 — programs are recomputed inside _build_matrix; here we
    # eagerly call _determine_programs solely to surface its MissingCountyDataError
    # warning into the top-level AnalysisReport.warnings. The matrix carries
    # programs_present, so we discard the program list itself.
    _programs, prog_warnings = _determine_programs(listing, household, profile)
    warnings.extend(prog_warnings)

    # Step 2 — resolve today's rates (FRED-or-override)
    if fred_mortgage_30us is None:
        rate_30 = _todays_rate_per_program("Conv30")
    else:
        rate_30 = quantize_rate(fred_mortgage_30us)

    if fred_mortgage_15us is None:
        rate_15 = _todays_rate_per_program("Conv15")
    else:
        rate_15 = quantize_rate(fred_mortgage_15us)

    # Build the per-program rate dict (D-14-REFI-02 proxies + 25bps ARM heuristic)
    todays_rates: dict[str, Decimal] = {
        "Conv30": rate_30,
        "Conv15": rate_15,
        "FHA30": rate_30,  # D-14-REFI-02 proxy
        "VA30": rate_30,  # D-14-REFI-02 proxy
        "Jumbo30": rate_30,  # D-14-REFI-02 proxy
        "Conv30-ARM-5-1": quantize_rate(rate_30 - Decimal("0.0025")),  # D-14-REFI-02
    }

    # Step 4 — matrix fan-out (24 cells base; +6 if jumbo; -6 if not VA-eligible)
    matrix, matrix_warnings = _build_matrix(listing, household, profile, todays_rates)
    warnings.extend(matrix_warnings)

    # Surface PMI-RATE-ESTIMATED whenever any cell carried the placeholder.
    if any("PMI-RATE-ESTIMATED" in r for c in matrix.cells for r in c.eligible_reasons):
        warnings.append("PMI-RATE-ESTIMATED")

    # Step 5 — auxiliary blocks (all at preferred DP per D-14-STRESS-01)
    stress = _build_stress_block(matrix, listing, household, profile, todays_rates)
    refi = _build_refi_block(matrix, household, todays_rates)
    points = _build_points_block(matrix, household, todays_rates)
    tax = _build_tax_block(matrix, household, profile, todays_rates)

    # Step 6 — verdict synthesis (D-14-VERDICT-01..04 cascade)
    verdict = synthesize(matrix, stress, household, profile)

    # Snapshot hash + audit timestamp (Phase 13 D-13-REANALYSIS-01 pattern)
    snapshot_input = household.model_dump_json() + profile.model_dump_json()
    snapshot_hash = hashlib.sha256(snapshot_input.encode("utf-8")).hexdigest()

    return AnalysisReport(
        listing_snapshot=listing,
        household_snapshot_hash=snapshot_hash,
        fetched_at=datetime.now(UTC),
        fred_mortgage_30us=rate_30,
        fred_mortgage_15us=rate_15,
        matrix=matrix,
        stress=stress,
        refi=refi,
        points=points,
        tax=tax,
        verdict=verdict,
        warnings=list(dict.fromkeys(warnings)),  # dedup preserving order
    )
