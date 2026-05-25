"""Household-aware affordability composition (AFFD-01..09).

Phase 4 is the FIRST consumer of the Phase 2 rule predicate library. It composes
Phase 1 models (lib.models — Loan/Money/Rate), Phase 2 predicates (lib.rules.* —
loan_type/conventional_pmi/fha_mip/va_residual_income/usda/atr_qm/fannie/freddie),
and the Phase 3 amortization engine (lib.amortize.build_schedule → Schedule.monthly_pi)
into the household-aware DTI/LTV/CLTV/PITI surface plus a one-shot reverse-affordability
solver via numpy-financial's pv function.

Architecture map (mirrors lib/amortize.py shape):
  evaluate_forward(req)  — forward-mode DTI/LTV/CLTV/PITI + blockers (Plan 04-02 body)
  evaluate_reverse(req)  — reverse-mode npf.pv solver + blockers (Plan 04-03 body)
  Helper layer (Plans 04-02..04-04 ship these private functions):
    _compute_dti, _compute_ltv, _compute_cltv, _compute_piti,
    _classify_target_loan_type (cross-walk per RESEARCH Open Q#3),
    _evaluate_blockers (precedence pipeline per D-11)

This plan (04-01) ships ONLY the Pydantic v2 type contract + cross-walk constants
+ documented stubs for evaluate_forward / evaluate_reverse. Plans 04-02 / 04-03 /
04-04 add bodies to these stubs (Phase 2 D-08 cross-plan stub idiom).

LOCKED DECISION - D-01 (caller-supplied monthly $ for tax/insurance/HOA; per CONTEXT.md):
  EscrowInputs carries property_tax_monthly, insurance_monthly, hoa_monthly as
  Money (Decimal max_digits=14, decimal_places=2). No county-keyed % inferences in
  v1 — caller enters monthly $ directly. PMI/MIP are NOT in this block (D-02
  derives them from predicates and a caller-supplied monthly_pmi for conventional).

LOCKED DECISION - D-02 (PMI/MIP from Phase 2 predicates; per CONTEXT.md + RESEARCH Open Q#1):
  Conventional + LTV > 0.80: caller MUST supply monthly_pmi (Money) on the request
  because lib.rules.conventional_pmi.status returns a TERMINATION enum, not a rate
  (RESEARCH §A.2). VA / USDA / conventional <= 0.80 LTV: no monthly MI added.
  FHA: derived from lib.rules.fha_mip.compute (returns annual_mip_pct as fractional
  Decimal). Phase 4 enforces caller-supplied monthly_pmi via _validate_common.

LOCKED DECISION - D-03 (UFMIP auto-financed into principal; per RESEARCH §"FHA UFMIP Financing Convention"):
  When target_loan_type == "fha", the request's loan_amount is the BASE loan amount;
  Plan 04-02 will compute MIPResult.ufmip and add it to the principal that flows into
  lib.amortize.build_schedule (option (b) per CONTEXT.md D-03). Surfaced in the
  AffordabilityResponse as financed_loan_amount when FHA. Documented in CLI --help
  in Plan 04-05 to match the financed schedule.

LOCKED DECISION - D-04 (property_value per-request, not in household.yml; per CONTEXT.md):
  ForwardModeRequest.property_value is supplied per scenario; ReverseModeRequest
  computes the implied property_value from down_payment + max_loan_amount. Household
  carries household-stable facts only (income, debts, escrow, location).

LOCKED DECISION - D-05 (single credit_score: int per applicant; min reduction; per CONTEXT.md):
  Applicant.credit_score is the caller-supplied representative score (caller picks
  mid-of-three or whatever). Plan 04-04 reduces via min(applicants[].credit_score)
  for Fannie LLPA + Freddie eligibility lookups. Three-bureau dict modeling is OUT
  of v1 scope.

LOCKED DECISION - D-06 (income aggregation = sum across applicants; per CONTEXT.md):
  total_gross_monthly_income = sum(applicant.gross_monthly_income for applicant in
  applicants). No income-type modeling (W-2 vs self-employed vs 1099). v1 personal-
  use scope.

LOCKED DECISION - D-07 (single-applicant via len(applicants)==1; per CONTEXT.md):
  No special-cased single-applicant code path. min(...) reduces to the single
  applicant's score; sum(...) reduces to the single applicant's income.

LOCKED DECISION - D-08 (one-shot npf.pv reverse with target_ltv_pct; per CONTEXT.md):
  ReverseModeRequest pins LTV via target_ltv_pct. Plan 04-03's evaluate_reverse
  algorithm: max_PITI = max_dti * income - monthly_debts; subtract escrow + MI;
  max_PI = remainder; max_loan_amount = quantize_cents(-npf.pv(rate=annual_rate/12,
  nper=term_months, pmt=-max_PI, fv=0)). NEVER iterate; one-shot solve.

LOCKED DECISION - D-09 (round-trip closure within Decimal('0.0001'); per CONTEXT.md):
  Reverse → forward parity (SC-2): feed evaluate_reverse output back through
  evaluate_forward and assert dti_back <= max_dti + Decimal('0.0001'). Tolerance
  applies ONLY to the rate value, not to dollar amounts (which compare with strict
  Decimal equality per D-18).

LOCKED DECISION - D-10 (reverse-mode JSON request shape verbatim; per CONTEXT.md):
  ReverseModeRequest fields: mode='reverse', household, max_dti, down_payment,
  target_loan_type, target_ltv_pct, term_months, annual_rate. Plus shared common
  fields (apr/apor optional, monthly_pmi optional, junior_liens default empty).

LOCKED DECISION - D-11 (blocked_by + warnings shape with precedence; per CONTEXT.md):
  AffordabilityResponse.blocked_by: str | None — first hard-fail citation in fixed
  precedence: (1) loan-type-classify (FHFA-LIMIT-* / HUD-LIMIT-*), (2) USDA-income
  (when target_loan_type=='usda'; per RESEARCH Open Q#4), (3) LTV/CLTV ceiling,
  (4) DTI cap, (5) ATR/QM, (6) VA-residual. Soft signals go to warnings: list[str].

LOCKED DECISION - D-12 (max_dti caller-supplied, no defaults; per CONTEXT.md):
  AffordabilityRequest.max_dti is Required (Rate). No per-loan-type default YAML
  in v1; explicit choice every call (matches "fail loud" discipline). ROADMAP SC-2
  example uses 0.43.

LOCKED DECISION - D-13 (CLI mirrors Phase 3 D-17/18/19; per CONTEXT.md):
  scripts/affordability.py uses --input <path> only (no stdin); lazy-imports
  lib.affordability after argparse; emits 6-key Pydantic envelope on stderr per
  Phase 3 D-19; pretty-prints JSON to stdout. Phase 10 relocates to
  .claude/skills/mortgage-ops/scripts/ via SCRIPT_PATH single-constant edit.

LOCKED DECISION - D-14 (mode discriminator; per CONTEXT.md):
  AffordabilityRequest is a Pydantic v2 discriminated union via Field(discriminator=
  "mode"). ForwardModeRequest carries loan_amount + property_value; ReverseModeRequest
  carries down_payment + target_ltv_pct. Both extend a shared _CommonRequestFields
  base (household, max_dti, target_loan_type, term_months, annual_rate, optional
  apr/apor/monthly_pmi/endorsement_date_override/junior_liens).

LOCKED DECISION - D-15 (FINAL household.example.yml with state_fips + county_fips; per RESEARCH Open Q#2):
  Household.location is a LocationFIPS Pydantic model REQUIRING state_fips +
  county_fips (2-digit + 3-digit regex-validated strings). county_name and state
  are documentation-only display fields. Phase 4 constructs lib.rules.types.County
  at evaluation time from these FIPS codes (TYPE_CHECKING import; County is not
  on the request surface). config/household.example.yml ships as FINAL after
  Plan 04-06 (D-15 + Plan 04-05 ship the schema; this plan ships the model that
  validates it).

LOCKED DECISION - D-16 (User-Layer pre-commit discipline preserved; per CONTEXT.md):
  config/household.yml stays gitignored + protected by Phase 1's
  scripts/hooks/block-user-layer.py. Phase 4 only modifies
  config/household.example.yml — the hook's allowlist already permits *.example.yml.

LOCKED DECISION - D-17 (hand-calc golden fixtures; per CONTEXT.md):
  Plan 04-06 ships tests/fixtures/affordability/*.json with citation comments.
  This plan ships only the model surface that those fixtures will exercise via
  AffordabilityRequest.model_validate_json + model_dump_json.

LOCKED DECISION - D-18 (exact Decimal equality; per CONTEXT.md):
  All money fields in fixture expected blocks are quoted Decimal strings; tests
  compare using == against Decimal(...) parsed values. The Decimal('0.0001')
  tolerance in D-09 applies ONLY to the round-trip DTI rate, not to dollar amounts.
  Money/Rate fields use lib.models aliases (condecimal max_digits=14,
  decimal_places=2 for Money; max_digits=7, decimal_places=6 for Rate).

Phase 2 predicate signature corrections (RESEARCH §"Phase 2 Predicate Signature Audit"):
  - loan_type.classify(loan_amount, county, program=, unit_count=) — program kwarg
    is REQUIRED (defaults to 'conventional'); CONTEXT.md D-11 step 1's positional
    call shape is wrong. Plans 04-02/04-04 derive program from target_loan_type via
    TARGET_LOAN_TYPE_TO_PROGRAM cross-walk below.
  - conventional_pmi.status(loan, scheduled_balance, original_property_value,
    is_high_risk=, months_elapsed=) — does NOT take ltv_pct. CONTEXT.md D-02's call
    shape is wrong. Phase 4 affordability uses LTV_REQUEST_ELIGIBLE constant
    directly (RESEARCH §A.2) instead of calling .status() because the predicate
    returns a TERMINATION enum, not a "needs PMI" boolean and not a PMI rate.
  - fha_mip.compute(loan, original_property_value, endorsement_date) — needs a
    Loan object + property_value + date. CONTEXT.md D-02's signature is wrong.
    Returns MIPResult.ufmip + annual_mip_pct (fractional Decimal); Plan 04-02
    derives monthly_mip = quantize_cents((loan.principal * annual_mip_pct) /
    Decimal('12')).

Loan-type cross-walk (RESEARCH Open Question #3):
  target_loan_type    accepted Phase 2 LoanType values     program=
  conventional        {conforming, high_balance}            "conventional"
  jumbo               {jumbo}                                "conventional"
  fha                 {fha_standard, fha_high_balance}      "fha"
  va                  {va_standard, va_high_balance}        "va"
  usda                {usda}                                 "usda"
Note jumbo → "conventional" because FHFA limits are the authority that
distinguishes conforming from jumbo within the conventional bucket; USDA / FHA /
VA use HUD/USDA/VA's own per-program limit tables.

Conventional PMI rate sourcing (RESEARCH Open Question #1):
  monthly_pmi is a caller-supplied Money | None field on AffordabilityRequest.
  REQUIRED when target_loan_type=='conventional' AND origination LTV > 0.80
  (LTV_REQUEST_ELIGIBLE per HPA 12 USC §4902). Module enforces via
  _validate_common. data/reference/ has no pmi-rates.yml because conventional PMI
  rate is bureau-specific (MGIC / Genworth / Radian etc. all differ); industry
  rule-of-thumb is ~0.0050-0.0125 annualized depending on credit-score / LTV
  bucket. Caller fetches their own quote and supplies the monthly $ amount.

Stale-warning expected behavior (RESEARCH §"_loader.py and StaleReferenceWarning"):
  data/reference/fha-mip-rates.yml (effective 2023-03-20) and
  data/reference/va-residual-income.yml (effective 2023-04-07) BOTH currently fire
  StaleReferenceWarning on every YAML load (effective dates > 12 months old).
  Plan 04-02 + Plan 04-03 surface these via warnings.catch_warnings() into the
  AffordabilityResponse.warnings list per D-11. NOT a bug — by design loud-by-
  default per Phase 2 D-12.
"""

from __future__ import annotations

import warnings
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

import numpy_financial as npf
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.amortize import build_schedule
from lib.models import Loan, Money, NonNegativeRatio, Rate
from lib.money import quantize_cents, quantize_rate
from lib.rules._loader import StaleReferenceWarning

# Phase 2 predicate full-path imports per Phase 2 D-08 (one predicate per citation).
# Wave 2 (Plan 04-02) promotes these to runtime imports because evaluate_forward
# calls them at runtime (RESEARCH §A.1-A.3 corrected signatures).
# Wave 4 (Plan 04-04) adds atr_qm + fannie_eligibility + freddie_eligibility +
# usda + va_residual_income for the D-11 blocker-precedence pipeline.
from lib.rules.atr_qm import general_qm_passes
from lib.rules.conventional_pmi import LTV_REQUEST_ELIGIBLE  # Decimal("0.80") — RESEARCH §A.2
from lib.rules.fannie_eligibility import compute_llpa as fannie_compute_llpa
from lib.rules.fha_mip import compute as fha_mip_compute
from lib.rules.freddie_eligibility import evaluate as freddie_evaluate
from lib.rules.loan_type import (
    classify as loan_type_classify,
)
from lib.rules.types import County, LoanType, Region  # Pydantic resolves at runtime
from lib.rules.usda import average_scheduled_annual_balance
from lib.rules.usda import evaluate as usda_evaluate
from lib.rules.va_residual_income import evaluate as va_residual_evaluate

if TYPE_CHECKING:
    from collections.abc import Sequence


# ---------------------------------------------------------------------------
# Module-level cross-walk constants (RESEARCH Open Question #3)
# ---------------------------------------------------------------------------

TARGET_LOAN_TYPE_CROSSWALK: dict[str, frozenset[str]] = {
    "conventional": frozenset({"conforming", "high_balance"}),
    "jumbo": frozenset({"jumbo"}),
    "fha": frozenset({"fha_standard", "fha_high_balance"}),
    "va": frozenset({"va_standard", "va_high_balance"}),
    "usda": frozenset({"usda"}),
}
"""Cross-walk: target_loan_type → set of accepted Phase 2 LoanType values.

Used by Plan 04-04's _classify_target_loan_type to detect FHFA-LIMIT-* /
HUD-LIMIT-* blockers when lib.rules.loan_type.classify returns a LoanType
that's outside the requested target_loan_type's accepted set."""

TARGET_LOAN_TYPE_TO_PROGRAM: dict[str, Literal["conventional", "fha", "va", "usda"]] = {
    "conventional": "conventional",
    "jumbo": "conventional",
    "fha": "fha",
    "va": "va",
    "usda": "usda",
}
"""Cross-walk: target_loan_type → program kwarg passed to lib.rules.loan_type.classify
(RESEARCH §A.1). Note jumbo → 'conventional' because FHFA limits are the
authority that distinguishes conforming vs jumbo within the conventional
bucket."""

TargetLoanType = Literal["conventional", "fha", "va", "usda", "jumbo"]
"""Caller-facing loan-type literal — distinct from the 8-value
lib.rules.types.LoanType which is the predicate-side return type."""

# USDA annual guarantee fee rate (per lib.rules.usda compute basis
# guarantee_fee_annual = average scheduled balance * 0.0035; RESEARCH §"lib/rules/usda.py").
# Sourced directly here (not via predicate call) for Phase 4 PITI composition,
# because USDA predicate's evaluate(...) is consulted by Plan 04-04 for blocker
# precedence; the rate scalar is statutory/contractual and stable.
USDA_ANNUAL_FEE_RATE: Final[Decimal] = Decimal("0.0035")

# Citation prefix per target_loan_type (used when classified type is OUTSIDE
# the target's accepted set — D-11 step 1 LTV-classification block).
_LOAN_TYPE_BLOCKER_PREFIX: dict[str, str] = {
    "conventional": "FHFA-LIMIT-CONFORMING",
    "jumbo": "FHFA-LIMIT-JUMBO",
    "fha": "HUD-LIMIT-FHA",
    "va": "VA-LIMIT",
    "usda": "USDA-LIMIT",
}


# =============================================================================
# D-11 Blocker Precedence — Citation Constants + Ceiling Tables (Plan 04-04)
# =============================================================================
# Citation strings emitted by _evaluate_blockers (Plan 04-04). Plan 04-06 ships
# the citation-coverage meta-test that introspects these via grep on the
# `BLOCKED_BY_` / `WARNING_` prefixes and asserts each appears in at least one
# fixture (RUL-12/13 inheritance per RESEARCH §"Citation-Coverage Meta-Test").
#
# Authoritative sources for the per-loan-type LTV ceilings (RESEARCH §"LTV /
# CLTV Ceiling Authority"):
#   conventional 0.97  — Fannie 97% LTV (HomeReady or first-time-buyer; v1
#                        unconditional per Assumption A1 — FTHB modeling out
#                        of v1 scope; T-04-04-03 accepted)
#   jumbo        0.90  — Common jumbo lender norm for owner-occupied SFH.
#                        Phase 17 polish (2026-05-23): tightened from the
#                        v1 sentinel ceiling of 1.00 (which provided no
#                        enforcement) to 0.90 (the conservative end of the
#                        80-90% range major lenders post for primary-residence
#                        jumbos). Above 0.90 LTV jumbo is a niche product
#                        with materially different pricing and underwriting
#                        and out of scope for personal-use modeling.
#   fha          0.965 — HUD Handbook 4000.1; credit_score >= 580
#   va           1.00  — Full-entitlement vets per VA Pamphlet 26-7 Chapter 3
#   usda         1.00  — USDA SFH GLP per 7 CFR Part 3555

# LTV ceiling per target_loan_type (RESEARCH §"LTV / CLTV Ceiling Authority").
LTV_CEILING_BY_TARGET: Final[dict[str, Decimal]] = {
    "conventional": Decimal("0.97"),
    "jumbo": Decimal("0.90"),
    "fha": Decimal("0.965"),
    "va": Decimal("1.00"),
    "usda": Decimal("1.00"),
}

# CLTV ceiling per target_loan_type (RESEARCH §"CLTV ceilings"; mirrors LTV by
# default — junior-lien semantics push CLTV but ceilings track the senior-lien
# program's ceiling for v1 personal-use scope).
CLTV_CEILING_BY_TARGET: Final[dict[str, Decimal]] = {
    "conventional": Decimal("0.97"),
    "jumbo": Decimal("0.90"),
    "fha": Decimal("0.965"),
    "va": Decimal("1.00"),
    "usda": Decimal("1.00"),
}

# ----- Hard blockers: response.blocked_by candidates -----
# Format-string templates: callers use .format(...) at the call site.
# Plan 04-06 citation-coverage meta-test discovers these via grep on the
# `BLOCKED_BY_` prefix.

BLOCKED_BY_LTV_CEILING_TEMPLATE: Final[str] = "LTV-CEILING-{LOAN_TYPE}"
BLOCKED_BY_CLTV_CEILING_TEMPLATE: Final[str] = "CLTV-CEILING-{LOAN_TYPE}"
BLOCKED_BY_DTI_CAP_TEMPLATE: Final[str] = "DTI-CAP-{LOAN_TYPE}"
BLOCKED_BY_USDA_INCOME_TEMPLATE: Final[str] = "USDA-INCOME-LIMIT-{state_fips}-{county_fips}"
BLOCKED_BY_ATR_QM_PRICE_FIRST: Final[str] = "ATR-QM-PRICE-FIRST"
# ATR-QM-PRICE-SUBORDINATE: out-of-scope for v1 (first-lien residential only;
# CONTEXT.md / RESEARCH §"First-lien vs subordinate-lien").

# The VA-residual citation is NOT a constant here — it's read VERBATIM from
# the predicate's `result.binding_rule_citation` field per Phase 2 D-11.
# The stable predicate-side format is documented at
# lib/rules/va_residual_income.py L115 — Phase 4 never constructs it.
# DO NOT re-construct or format-shadow the predicate's citation string in
# this module — drift between predicate and consumer breaks ROADMAP SC-3
# + Phase 2 D-11 contract.
# The regex pattern below is for the citation-coverage meta-test only —
# Plan 04-06 meta-test asserts at least one fixture's blocked_by matches
# this pattern.
BLOCKED_BY_VA_RESIDUAL_PATTERN: Final[str] = (
    r"^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$"
)

# ----- Soft warnings (response.warnings candidates) -----
WARNING_HPA_PMI_REQUIRED: Final[str] = "HPA-PMI-REQUIRED"
WARNING_ATR_QM_NOT_EVALUATED: Final[str] = "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR"
WARNING_FANNIE_LLPA_TEMPLATE: Final[str] = "FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}"
WARNING_FREDDIE_INELIGIBLE_TEMPLATE: Final[str] = "FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}"


# ---------------------------------------------------------------------------
# Leaf Pydantic models (D-01, D-05, D-06, D-15)
# ---------------------------------------------------------------------------


class LocationFIPS(BaseModel):
    """Household location FIPS codes (RESEARCH Open Question #2; D-15 amendment).

    state_fips + county_fips are REQUIRED for County construction in Phase 2
    predicates. county_name and state are documentation-only display fields.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
    county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    county_name: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    zip: str | None = None


class Applicant(BaseModel):
    """One applicant on the loan (D-05, D-06, D-07).

    credit_score is the caller-supplied representative score (mid-of-3 if 3
    scores; lower-of-2 if 2). Plan 04-04 picks min across applicants for Fannie
    LLPA + Freddie eligibility lookups (D-05).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    name: str = Field(min_length=1)
    gross_monthly_income: Money
    credit_score: int = Field(ge=300, le=850)


class MonthlyDebts(BaseModel):
    """Back-end DTI inputs (CONTEXT.md household.example.yml schema)."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    auto: Money = Decimal("0.00")
    student_loans: Money = Decimal("0.00")
    credit_cards: Money = Decimal("0.00")
    other: Money = Decimal("0.00")


class EscrowInputs(BaseModel):
    """Caller-supplied PITI components (D-01).

    property_tax_monthly + insurance_monthly are REQUIRED. hoa_monthly defaults
    to Decimal('0.00') when no HOA. PMI/MIP are NOT in this block — they are
    derived from predicates (D-02) or caller-supplied via the request's
    monthly_pmi field for conventional > 80% LTV (RESEARCH Open Q#1).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    property_tax_monthly: Money
    insurance_monthly: Money
    hoa_monthly: Money = Decimal("0.00")


class VAInputs(BaseModel):
    """VA-specific inputs (D-15 optional; required-by-validator when target_loan_type=='va').

    region + family_size produce the stable citation
    f'VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}' via
    lib.rules.va_residual_income.evaluate (Phase 2 D-11; DO NOT format-drift).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    region: Region
    family_size: int = Field(ge=1)
    actual_residual_income: Money


class Household(BaseModel):
    """Household-stable facts (D-04: property_value is per-request, NOT here).

    size is REQUIRED and represents the FULL household size including
    non-applicant dependents (BLOCKER 2 fix per CLAUDE.md + CONTEXT.md). Drives
    USDA income-limit lookups via lib.rules.usda.evaluate (RESEARCH §lib/rules/
    usda.py L198-211). Fail-loud, no inference from len(applicants) — for a
    2-applicant + 3-children household, size=5 even though len(applicants)==2.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    location: LocationFIPS
    applicants: list[Applicant] = Field(min_length=1)
    size: int = Field(
        ge=1,
        description=(
            "Full household size including non-applicant dependents — drives "
            "USDA income-limit lookups (RESEARCH §lib/rules/usda.py L198-211); "
            "fail-loud, no inference from applicants count (BLOCKER 2 fix; "
            "CLAUDE.md + CONTEXT.md). For a 2-applicant + 3-children household "
            "size=5 even though len(applicants)==2."
        ),
    )
    monthly_debts: MonthlyDebts
    escrow: EscrowInputs
    va: VAInputs | None = None
    current_housing_payment: Money = Decimal("0.00")

    @model_validator(mode="after")
    def _applicant_income_strictly_positive(self) -> Household:
        total_income = sum(
            (applicant.gross_monthly_income for applicant in self.applicants),
            start=Decimal("0.00"),
        )
        if total_income <= Decimal("0.00"):
            raise ValueError("sum(applicants.gross_monthly_income) must be > 0")
        return self


# ---------------------------------------------------------------------------
# AffordabilityRequest discriminated union (D-14)
# ---------------------------------------------------------------------------


class _CommonRequestFields(BaseModel):
    """Shared base fields for ForwardModeRequest + ReverseModeRequest. Not
    instantiated directly."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    household: Household
    max_dti: Rate  # caller-supplied per D-12 — no defaults
    target_loan_type: TargetLoanType
    term_months: int = Field(ge=1, le=600)
    annual_rate: Rate
    apr: Rate | None = None  # both-or-neither with apor (RESEARCH §"ATR/QM Gating")
    apor: Rate | None = None
    monthly_pmi: Money | None = None  # RESEARCH Open Q#1 — required for conventional > 80 LTV
    endorsement_date_override: date | None = None  # RESEARCH Open Q#6
    junior_liens: list[Money] = Field(default_factory=list)


def _validate_common(req: _CommonRequestFields) -> Any:
    """Cross-field validators applied to both ForwardModeRequest + ReverseModeRequest.

    - VA residual fields are evaluated when supplied; missing residual inputs
      become a hard blocker after ordinary affordability diagnostics run.
    - apr/apor must be both-or-neither (RESEARCH §"ATR/QM Gating")
    - monthly_pmi required when target_loan_type=='conventional' AND origination
      LTV > LTV_REQUEST_ELIGIBLE (0.80) — RESEARCH Open Q#1; predicate has no rate
    """
    # apr / apor symmetry
    if (req.apr is None) != (req.apor is None):
        raise ValueError(
            "apr and apor must both be supplied or both be omitted "
            "(RESEARCH §'ATR/QM Gating'; reject half-supplied fabrication)"
        )
    if isinstance(req, ForwardModeRequest) and req.property_value <= Decimal("0"):
        raise ValueError("property_value must be > 0")
    if isinstance(req, ReverseModeRequest) and req.target_ltv_pct <= Decimal("0"):
        raise ValueError("target_ltv_pct must be > 0")
    # monthly_pmi conditional (conventional + LTV > 0.80)
    if req.target_loan_type == "conventional":
        if isinstance(req, ForwardModeRequest):
            origination_ltv = req.loan_amount / req.property_value
        elif isinstance(req, ReverseModeRequest):
            origination_ltv = req.target_ltv_pct
        else:  # pragma: no cover — defensive; req must be one of the two subtypes
            return req
        if origination_ltv > LTV_REQUEST_ELIGIBLE and req.monthly_pmi is None:
            raise ValueError(
                "monthly_pmi is required when target_loan_type=='conventional' "
                "AND origination LTV > 0.80 (RESEARCH Open Question #1; "
                "lib.rules.conventional_pmi.status returns termination status only, "
                "not a rate; caller must supply the PMI premium)"
            )
    return req


class ForwardModeRequest(_CommonRequestFields):
    """Forward-mode request: known loan_amount + property_value → DTI/LTV/CLTV/PITI.

    Plan 04-02 ships evaluate_forward(req) which consumes this shape.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["forward"] = "forward"
    loan_amount: Money
    property_value: Money

    @model_validator(mode="after")
    def _validate_forward(self) -> ForwardModeRequest:
        _validate_common(self)
        return self


class ReverseModeRequest(_CommonRequestFields):
    """Reverse-mode request: known max_dti + down_payment + target_ltv_pct →
    max_loan_amount via npf.pv (D-08, D-10).

    Plan 04-03 ships evaluate_reverse(req) which consumes this shape.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["reverse"] = "reverse"
    down_payment: Money
    target_ltv_pct: Rate

    @model_validator(mode="after")
    def _validate_reverse(self) -> ReverseModeRequest:
        _validate_common(self)
        return self


AffordabilityRequest = Annotated[
    ForwardModeRequest | ReverseModeRequest,
    Field(discriminator="mode"),
]
"""Pydantic v2 discriminated union by `mode` field (D-14).

Use TypeAdapter(AffordabilityRequest).validate_json(...) at the script
boundary; the discriminator routes the raw payload to ForwardModeRequest or
ReverseModeRequest based on the `mode` field's literal value."""


# ---------------------------------------------------------------------------
# AffordabilityResponse (D-11 shape)
# ---------------------------------------------------------------------------


class AffordabilityResponse(BaseModel):
    """Phase 4 evaluation result (D-11 shape).

    Forward-mode populates: loan_amount, property_value, financed_loan_amount
    (= loan_amount + UFMIP if FHA per D-03), dti_front, dti_back, ltv, cltv,
    piti, monthly_pi, monthly_mi.

    Reverse-mode populates: max_loan_amount, implied_pi, assumed_ltv_pct,
    assumed_monthly_mi.

    Both modes always populate: mode, loan_type, blocked, blocked_by, warnings,
    total_gross_monthly_income, total_monthly_debts.

    blocked_by is the FIRST hard-fail citation in fixed precedence (D-11):
    loan-type-classify (FHFA-LIMIT-* / HUD-LIMIT-*) → USDA-income (when usda) →
    LTV/CLTV → DTI → ATR/QM → VA-residual. Soft signals go to warnings.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    # Always populated
    mode: Literal["forward", "reverse"]
    loan_type: LoanType | None  # None when loan-type-classify raised MissingCountyDataError
    blocked: bool
    blocked_by: str | None  # exactly one citation; None when not blocked
    warnings: list[str] = Field(default_factory=list)
    total_gross_monthly_income: Money
    total_monthly_debts: Money

    # Forward-only (None in reverse mode)
    loan_amount: Money | None = None
    property_value: Money | None = None
    financed_loan_amount: Money | None = None  # loan_amount + UFMIP for FHA per D-03
    dti_front: NonNegativeRatio | None = None
    dti_back: NonNegativeRatio | None = None
    ltv: NonNegativeRatio | None = None
    cltv: NonNegativeRatio | None = None
    piti: Money | None = None
    monthly_pi: Money | None = None
    monthly_mi: Money | None = None

    # Reverse-only (None in forward mode)
    max_loan_amount: Money | None = None
    implied_pi: Money | None = None
    assumed_ltv_pct: Rate | None = None
    assumed_monthly_mi: Money | None = None


# ---------------------------------------------------------------------------
# Private helpers (Plan 04-02 — Wave 2 forward-affordability composition)
# ---------------------------------------------------------------------------


def _build_county(location: LocationFIPS) -> County:
    """Construct a Phase 2 County from Household.location FIPS codes (RESEARCH Open Q#2)."""
    return County(
        state_fips=location.state_fips,
        county_fips=location.county_fips,
        name=location.county_name,
    )


def _build_loan_for_amortization(
    principal: Decimal,
    annual_rate: Decimal,
    term_months: int,
    origination_date: date | None = None,
) -> Loan:
    """Build a Phase 1 Loan for build_schedule consumption.

    loan_type='fixed' is the amortization-mode tag (NOT regulatory classification).
    Phase 2's 8-value LoanType is the regulatory result and lives on
    AffordabilityResponse.loan_type, not on this internal Loan.
    """
    return Loan(
        principal=quantize_cents(principal),
        annual_rate=annual_rate,
        term_months=term_months,
        origination_date=origination_date or date.today(),
        loan_type="fixed",
    )


def _compute_dti(
    piti: Decimal,
    sum_monthly_debts: Decimal,
    total_gross_monthly_income: Decimal,
) -> tuple[Decimal, Decimal]:
    """Compute (front_end_dti, back_end_dti) per AFFD-01 + RESEARCH §"DTI Convention".

    front_end = piti / income (housing-only ratio)
    back_end  = (piti + non-housing-debts) / income (total-debt ratio)

    Returns ratios as Decimal (NOT quantize_cents — DTI is a rate, not money;
    ratios stay at full Decimal precision for the round-trip closure tolerance
    in D-09).
    """
    if total_gross_monthly_income <= Decimal("0"):
        raise ValueError("total_gross_monthly_income must be > 0")
    front = piti / total_gross_monthly_income
    back = (piti + sum_monthly_debts) / total_gross_monthly_income
    return front, back


def _compute_ltv(loan_amount: Decimal, property_value: Decimal) -> Decimal:
    """LTV = loan_amount / property_value (AFFD-02). Decimal precision preserved."""
    if property_value <= Decimal("0"):
        raise ValueError("property_value must be > 0")
    return loan_amount / property_value


def _compute_cltv(
    loan_amount: Decimal,
    junior_liens: Sequence[Decimal],
    property_value: Decimal,
) -> Decimal:
    """CLTV = (loan_amount + sum(junior_liens)) / property_value (AFFD-03).

    v1 uses list[Money] (sum) per CONTEXT.md Claude's discretion. Empty junior_liens
    reduces CLTV to LTV.
    """
    if property_value <= Decimal("0"):
        raise ValueError("property_value must be > 0")
    total = loan_amount + sum(junior_liens, start=Decimal("0"))
    return total / property_value


def _classify_target_loan_type(
    loan_amount: Decimal,
    county: County,
    target_loan_type: TargetLoanType,
) -> tuple[LoanType, str | None]:
    """Run lib.rules.loan_type.classify with the corrected signature
    (RESEARCH §A.1) and check the result against TARGET_LOAN_TYPE_CROSSWALK.

    Returns (classified_type, blocker_citation):
      - classified_type: the Phase 2 8-value LoanType returned by classify
      - blocker_citation: None if classified_type is in the accepted set for
        target_loan_type; otherwise a citation string formatted as:
          FHFA-LIMIT-CONFORMING-{state_fips}-{county_fips}  (target=conventional, classified=jumbo)
          FHFA-LIMIT-JUMBO-{state_fips}-{county_fips}        (target=jumbo, classified=conforming/high_balance)
          HUD-LIMIT-FHA-{state_fips}-{county_fips}           (target=fha, classified=fha_high_balance excluded by HUD ceiling)
          VA-LIMIT-{state_fips}-{county_fips}                (target=va, classified outside)
          USDA-LIMIT-{state_fips}-{county_fips}              (target=usda, classified outside)

    MissingCountyDataError raised by classify is propagated to caller — D-11
    step 1 says it's a HARD ERROR (Pydantic-shaped envelope on stderr per
    Phase 3 D-19), NOT a blocked_by string.
    """
    program = TARGET_LOAN_TYPE_TO_PROGRAM[target_loan_type]
    classified: LoanType = loan_type_classify(
        loan_amount=loan_amount,
        county=county,
        program=program,
    )
    accepted = TARGET_LOAN_TYPE_CROSSWALK[target_loan_type]
    if classified in accepted:
        return classified, None
    citation_prefix = _LOAN_TYPE_BLOCKER_PREFIX[target_loan_type]
    return classified, f"{citation_prefix}-{county.state_fips}-{county.county_fips}"


def _compute_monthly_mi(
    target_loan_type: TargetLoanType,
    financed_loan_amount: Decimal,
    property_value: Decimal,
    annual_rate: Decimal,
    term_months: int,
    monthly_pmi: Decimal | None,
    endorsement_date: date,
    fha_annual_mip_pct: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """Compute (monthly_mi, ufmip_or_zero) for the given target_loan_type.

    Returns:
      - monthly_mi: monthly mortgage-insurance / MIP / USDA annual fee component of PITI
      - ufmip_or_zero: UFMIP dollar amount (FHA only; D-03 auto-finance) or 0 for others

    Branches:
      conventional + LTV>0.80 -> caller-supplied request.monthly_pmi (RESEARCH Open Q#1)
      conventional + LTV<=0.80 -> Decimal("0.00")
      fha -> fha_mip_compute(loan, property_value, endorsement_date); convert annual to monthly
      va -> Decimal("0.00") (funding fee financed into principal at script boundary; not in PITI)
      usda -> quantize_cents((average scheduled balance * USDA_ANNUAL_FEE_RATE) / 12)
      jumbo -> Decimal("0.00") (caller responsible for jumbo-side MI if any)

    Per RESEARCH §A.2/A.3 + Open Q#1.
    """
    if target_loan_type == "conventional":
        origination_ltv = financed_loan_amount / property_value
        if origination_ltv > LTV_REQUEST_ELIGIBLE:
            # Plan 04-01 _validate_common already enforced monthly_pmi is not None here.
            assert monthly_pmi is not None
            return monthly_pmi, Decimal("0")
        return Decimal("0.00"), Decimal("0")

    if target_loan_type == "fha":
        if fha_annual_mip_pct is not None:
            monthly_mip = quantize_cents(
                (financed_loan_amount * fha_annual_mip_pct) / Decimal("12")
            )
            return monthly_mip, Decimal("0")
        # RESEARCH §A.3: fha_mip.compute(loan, property_value, endorsement_date)
        # NOT the CONTEXT.md D-02 (loan_amount, ltv_pct, term_months) signature.
        loan = _build_loan_for_amortization(
            principal=financed_loan_amount,
            annual_rate=annual_rate,
            term_months=term_months,
            origination_date=endorsement_date,
        )
        mip = fha_mip_compute(
            loan=loan,
            original_property_value=property_value,
            endorsement_date=endorsement_date,
        )
        monthly_mip = quantize_cents((financed_loan_amount * mip.annual_mip_pct) / Decimal("12"))
        return monthly_mip, mip.ufmip

    if target_loan_type == "va":
        return Decimal("0.00"), Decimal("0")

    if target_loan_type == "usda":
        annual_fee_basis = average_scheduled_annual_balance(
            loan_amount=financed_loan_amount,
            annual_rate=annual_rate,
            term_months=term_months,
        )
        return (
            quantize_cents((annual_fee_basis * USDA_ANNUAL_FEE_RATE) / Decimal("12")),
            Decimal("0"),
        )

    if target_loan_type == "jumbo":
        return Decimal("0.00"), Decimal("0")

    # Defensive — Pydantic should already have rejected at request boundary
    raise ValueError(f"Unknown target_loan_type: {target_loan_type}")


# ---------------------------------------------------------------------------
# Cross-plan stub functions (Phase 2 D-08 stub idiom)
# ---------------------------------------------------------------------------


def evaluate_forward(request: ForwardModeRequest) -> AffordabilityResponse:
    """Forward-mode affordability composition (AFFD-01..04, AFFD-06).

    Pipeline:
      1. Sum joint income; compute total monthly debts.
      2. Build County from household.location FIPS.
      3. Classify loan_type via Phase 2 RUL-01 with corrected signature
         (RESEARCH §A.1) — uses TARGET_LOAN_TYPE_CROSSWALK to detect
         FHFA-LIMIT-* / HUD-LIMIT-* blockers when the predicate's returned
         LoanType is outside the requested target.
         (MissingCountyDataError propagates as Python exception; D-11 step 1
         hard error, NOT blocked_by — script boundary surfaces 6-key envelope.)
      4. Capture StaleReferenceWarning across predicate calls (D-11 propagation).
      5. For FHA target with D-03 auto-finance: financed_loan_amount =
         loan_amount + ufmip. For other targets: financed_loan_amount = loan_amount.
      6. Call build_schedule on the financed Loan to get monthly_pi.
      7. Compute monthly_mi via _compute_monthly_mi (handles all 5 target loan types).
      8. PITI = quantize_cents(monthly_pi + tax + ins + hoa + monthly_mi). ONE quantize.
      9. LTV = financed_loan_amount / property_value (ratio).
     10. CLTV = (financed_loan_amount + sum(junior_liens)) / property_value.
     11. DTI front = piti / income; DTI back = (piti + non_housing_debts) / income.
     12. Surface the loan-type-classify blocker (if any) into blocked_by so Plan
         04-04's _evaluate_blockers precedence pipeline can find it; the rest of
         D-11 precedence (LTV/CLTV ceiling -> DTI cap -> ATR/QM -> VA-residual)
         is wired in Plan 04-04.

    Note on warnings capture: every predicate call site is wrapped in a single
    warnings.catch_warnings(record=True) block; the captured StaleReferenceWarning
    instances are stringified via str(w.message) and appended to response.warnings.
    """
    # 1. Joint applicant aggregation (D-06 + D-05 + D-07)
    applicants = request.household.applicants
    total_gross_monthly_income = sum(
        (a.gross_monthly_income for a in applicants),
        start=Decimal("0"),
    )
    debts = request.household.monthly_debts
    sum_monthly_debts = debts.auto + debts.student_loans + debts.credit_cards + debts.other
    # min_credit_score is the documented selector for Fannie LLPA + Freddie
    # eligibility lookups in Plan 04-04 — not consumed in evaluate_forward math
    # itself, but bound here per D-05 so the documented selector is visible at
    # the call site (underscore-prefixed name signals "intentionally unused
    # within this function" to ruff; Plan 04-04 wraps and consumes via the
    # blocker pipeline).
    _min_credit_score = min(a.credit_score for a in applicants)

    # 2. County construction
    county = _build_county(request.household.location)

    # Endorsement date (RESEARCH Open Q#6: default to today; allow override)
    endorsement_date = request.endorsement_date_override or date.today()

    # 3-12: capture staleness warnings across the pipeline (D-11)
    captured_warnings: list[str] = []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", StaleReferenceWarning)

        # 3. Loan-type classification (corrected signature per RESEARCH §A.1)
        classified_loan_type, classify_blocker = _classify_target_loan_type(
            loan_amount=request.loan_amount,
            county=county,
            target_loan_type=request.target_loan_type,
        )

        # 5. UFMIP financing (D-03 auto-finance per RESEARCH recommendation)
        #    Compute MI and UFMIP together; financed_loan_amount derives from UFMIP.
        #    Note: _compute_monthly_mi takes financed_loan_amount; for FHA we need
        #    a two-step compute (UFMIP first -> financed_amount -> monthly MIP from
        #    financed_amount). Inline the FHA branch here for clarity.
        ufmip_to_finance = Decimal("0.00")
        if request.target_loan_type == "fha":
            # First MIP call to get UFMIP
            pre_finance_loan = _build_loan_for_amortization(
                principal=request.loan_amount,
                annual_rate=request.annual_rate,
                term_months=request.term_months,
                origination_date=endorsement_date,
            )
            pre_mip = fha_mip_compute(
                loan=pre_finance_loan,
                original_property_value=request.property_value,
                endorsement_date=endorsement_date,
            )
            ufmip_to_finance = pre_mip.ufmip

        financed_loan_amount = quantize_cents(request.loan_amount + ufmip_to_finance)

        # 6. Compute monthly P&I via Phase 3 build_schedule on the financed loan
        financed_loan = _build_loan_for_amortization(
            principal=financed_loan_amount,
            annual_rate=request.annual_rate,
            term_months=request.term_months,
            origination_date=endorsement_date,
        )
        schedule = build_schedule(financed_loan)
        monthly_pi = schedule.monthly_pi

        # 7. Compute monthly_mi (predicate-derived for FHA; caller-supplied for
        #    conventional > 80%; predicate-derived for USDA; 0 for VA / jumbo /
        #    conventional <= 80%)
        monthly_mi, _ = _compute_monthly_mi(
            target_loan_type=request.target_loan_type,
            financed_loan_amount=financed_loan_amount,
            property_value=request.property_value,
            annual_rate=request.annual_rate,
            term_months=request.term_months,
            monthly_pmi=request.monthly_pmi,
            endorsement_date=endorsement_date,
            fha_annual_mip_pct=(
                pre_mip.annual_mip_pct if request.target_loan_type == "fha" else None
            ),
        )

        # Collect StaleReferenceWarning strings (D-11 propagation)
        for w in captured:
            if issubclass(w.category, StaleReferenceWarning):
                captured_warnings.append(str(w.message))

    # 8. PITI — quantize ONCE at end (Phase 3 D-04 PITFALLS pattern; D-01)
    escrow = request.household.escrow
    piti_pre_quantize = (
        monthly_pi
        + escrow.property_tax_monthly
        + escrow.insurance_monthly
        + escrow.hoa_monthly
        + monthly_mi
    )
    piti = quantize_cents(piti_pre_quantize)

    # 9-10. LTV + CLTV (use financed_loan_amount for FHA UFMIP semantics).
    #       Quantize to 6 decimal places at the response boundary so blocker
    #       comparisons see stable ratios while still allowing over-100% values.
    ltv = quantize_rate(_compute_ltv(financed_loan_amount, request.property_value))
    cltv = quantize_rate(
        _compute_cltv(
            financed_loan_amount,
            request.junior_liens,
            request.property_value,
        )
    )

    # 11. DTI front + back (also quantized to 6 places for Rate validation).
    dti_front_raw, dti_back_raw = _compute_dti(
        piti=piti,
        sum_monthly_debts=sum_monthly_debts,
        total_gross_monthly_income=total_gross_monthly_income,
    )
    dti_front = quantize_rate(dti_front_raw)
    dti_back = quantize_rate(dti_back_raw)

    # 12. Build response — blocked / blocked_by reflect ONLY the loan-type-classify
    # blocker (D-11 step 1). Plan 04-04 wraps evaluate_forward with the rest of the
    # precedence pipeline (LTV/CLTV ceiling -> DTI cap -> ATR/QM -> VA-residual) and
    # mutates a NEW response (frozen models — model_copy(update={...})).
    return AffordabilityResponse(
        mode="forward",
        loan_type=classified_loan_type,
        blocked=(classify_blocker is not None),
        blocked_by=classify_blocker,
        warnings=captured_warnings,
        total_gross_monthly_income=quantize_cents(total_gross_monthly_income),
        total_monthly_debts=quantize_cents(sum_monthly_debts),
        loan_amount=request.loan_amount,
        property_value=request.property_value,
        financed_loan_amount=financed_loan_amount,
        dti_front=dti_front,
        dti_back=dti_back,
        ltv=ltv,
        cltv=cltv,
        piti=piti,
        monthly_pi=monthly_pi,
        monthly_mi=quantize_cents(monthly_mi),
    )


def evaluate_reverse(request: ReverseModeRequest) -> AffordabilityResponse:
    """Reverse-mode affordability: max_loan_amount via npf.pv (AFFD-05; D-08).

    One-shot solve — no iteration. Wraps numpy-financial's pv directly per
    RESEARCH §"numpy-financial npf.pv Conventions". The caller pins LTV via
    target_ltv_pct + down_payment, so chicken-and-egg between MI and
    loan_amount is resolved by a zero-MI seed npf.pv solve, then refining
    MI from the seed-implied financed_loan_amount before the final solve.

    Pipeline (D-08 steps):
      1. Sum joint income; compute total monthly debts.
      2. max_PITI = max_dti * income - debts                       (step 1)
      3. max_PI_plus_MI = max_PITI - (tax + ins + hoa)              (step 2)
      4. monthly_rate = annual_rate / Decimal("12")     (Phase 3 D-04 convention)
      5. Zero-MI seed npf.pv solve to get a candidate financed_loan_amount;
         derive a candidate property_value via target_ltv_pct.
      6. Estimate assumed_monthly_mi via _compute_monthly_mi at the candidate
         financed_loan_amount + property_value (FHA branch needs a Loan to
         call fha_mip_compute; conventional branch uses caller-supplied
         monthly_pmi; VA / USDA / jumbo follow predicate-derived rules).
      7. max_PI = max_PI_plus_MI - assumed_monthly_mi               (step 4)
      8. raw_pv = npf.pv(rate=monthly_rate, nper=term_months,
                          pmt=-max_PI, fv=0)                        (step 5)
         — NEGATIVE pmt per cash-flow convention (RESEARCH §"Sign conventions");
         — fv=0 ALWAYS per Phase 3 D-09 + numpy-financial #130 avoidance.
      9. max_loan_amount = quantize_cents(-raw_pv) — NEGATE raw return per
         standard cash-flow convention; quantize ONCE at end (CLAUDE.md money
         discipline).
     10. derived_property_value = max_loan_amount / target_ltv_pct (used for
         downstream classify call only; NOT surfaced on response — reverse
         mode commits to LTV, not a specific property).
     11. Build County; classify_target_loan_type with derived_property_value
         to surface FHFA-LIMIT-* / HUD-LIMIT-* / VA-LIMIT / USDA-LIMIT
         blockers if classified type is outside target's accepted set.
     12. Build response with mode="reverse"; populate max_loan_amount,
         implied_pi=max_PI (positive Decimal — the input to npf.pv),
         assumed_ltv_pct=target_ltv_pct (echoed for traceability),
         assumed_monthly_mi.

    Round-trip closure target (D-09; SC-2) — actual assertion ships in Plan 04-06:
      forward(ForwardModeRequest(loan_amount=resp.max_loan_amount,
                                  property_value=resp.max_loan_amount/target_ltv_pct,
                                  ...)).dti_back <= req.max_dti + Decimal("0.0001")
      AND forward.loan_amount == reverse.max_loan_amount  (exact Decimal equality)

    Note on monthly_pi vs implied_pi naming:
      implied_pi is the reverse-mode counterpart to forward's monthly_pi —
      the monthly principal-and-interest IMPLIED by the npf.pv solve. Naming
      distinct fields keeps the response shape unambiguous about which mode
      produced the value (forward = computed via build_schedule;
      reverse = computed via npf.pv inversion).

    Note on UFMIP financing:
      Reverse mode does NOT auto-finance UFMIP because target_ltv_pct +
      down_payment pin both sides of the LTV ratio; financing UFMIP would
      shift LTV out of the target bucket, breaking D-08's one-shot premise
      (T-04-03-07 in plan threat model). The forward-mode round-trip caller
      reconstructs property_value from max_loan_amount / target_ltv_pct
      (no UFMIP add-on) so the closure is exact.
    """
    # 1. Joint applicant aggregation (D-06 + D-05 + D-07; mirrors evaluate_forward)
    applicants = request.household.applicants
    total_gross_monthly_income = sum(
        (a.gross_monthly_income for a in applicants),
        start=Decimal("0"),
    )
    debts = request.household.monthly_debts
    sum_monthly_debts = debts.auto + debts.student_loans + debts.credit_cards + debts.other

    escrow = request.household.escrow
    endorsement_date = request.endorsement_date_override or date.today()

    # 2. max_PITI (D-08 step 1)
    max_piti = request.max_dti * total_gross_monthly_income - sum_monthly_debts

    # 3. max_PI_plus_MI (D-08 step 2)
    max_pi_plus_mi = max_piti - (
        escrow.property_tax_monthly + escrow.insurance_monthly + escrow.hoa_monthly
    )
    no_budget_blocker = BLOCKED_BY_DTI_CAP_TEMPLATE.format(
        LOAN_TYPE=request.target_loan_type.upper()
    )
    if max_pi_plus_mi <= Decimal("0"):
        return AffordabilityResponse(
            mode="reverse",
            loan_type=None,
            blocked=True,
            blocked_by=no_budget_blocker,
            warnings=[],
            total_gross_monthly_income=quantize_cents(total_gross_monthly_income),
            total_monthly_debts=quantize_cents(sum_monthly_debts),
            max_loan_amount=Decimal("0.00"),
            implied_pi=Decimal("0.00"),
            assumed_ltv_pct=request.target_ltv_pct,
            assumed_monthly_mi=Decimal("0.00"),
        )

    # 4-11: capture staleness warnings across the predicate pipeline (D-11)
    captured_warnings: list[str] = []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", StaleReferenceWarning)

        # 4. monthly_rate (Phase 3 D-04)
        monthly_rate = request.annual_rate / Decimal("12")

        # 5. Zero-MI seed solve (resolves FHA chicken-and-egg between
        #    financed_loan_amount and MI estimate). Same sign-convention as
        #    the final solve (step 8): npf.pv(pmt=NEGATIVE, fv=0) returns a
        #    POSITIVE Decimal directly under numpy_financial 1.0.0; no
        #    second negation. See sign-convention note at the final solve.
        zero_mi_pv = npf.pv(
            rate=monthly_rate,
            nper=request.term_months,
            pmt=-max_pi_plus_mi,
            fv=0,
        )
        zero_mi_loan_amount = quantize_cents(zero_mi_pv)
        zero_mi_property_value = quantize_cents(zero_mi_loan_amount / request.target_ltv_pct)

        # 6. Estimate assumed_monthly_mi at the candidate financed_loan_amount.
        #    For FHA the call uses zero_mi_loan_amount as the seed; the result
        #    feeds back into the FINAL npf.pv solve (one refinement pass; D-08
        #    one-shot premise — no iteration loop).
        assumed_monthly_mi, _ = _compute_monthly_mi(
            target_loan_type=request.target_loan_type,
            financed_loan_amount=zero_mi_loan_amount,
            property_value=zero_mi_property_value,
            annual_rate=request.annual_rate,
            term_months=request.term_months,
            monthly_pmi=request.monthly_pmi,
            endorsement_date=endorsement_date,
        )

        # 7. max_PI (D-08 step 4)
        max_pi = max_pi_plus_mi - assumed_monthly_mi
        if max_pi <= Decimal("0"):
            for w in captured:
                if issubclass(w.category, StaleReferenceWarning):
                    captured_warnings.append(str(w.message))
            return AffordabilityResponse(
                mode="reverse",
                loan_type=None,
                blocked=True,
                blocked_by=no_budget_blocker,
                warnings=captured_warnings,
                total_gross_monthly_income=quantize_cents(total_gross_monthly_income),
                total_monthly_debts=quantize_cents(sum_monthly_debts),
                max_loan_amount=Decimal("0.00"),
                implied_pi=Decimal("0.00"),
                assumed_ltv_pct=request.target_ltv_pct,
                assumed_monthly_mi=quantize_cents(assumed_monthly_mi),
            )

        # 8. Final npf.pv solve (D-08 step 5; RESEARCH §"numpy-financial npf.pv
        #    Conventions"). pmt=-max_pi per cash-flow convention; fv=0 per
        #    Phase 3 D-09 + numpy-financial #130.
        raw_pv = npf.pv(
            rate=monthly_rate,
            nper=request.term_months,
            pmt=-max_pi,
            fv=0,
        )

        # 9. Quantize ONCE at end (CLAUDE.md money discipline).
        #
        # Sign-convention note: RESEARCH §"Sign conventions" + §"reverse pseudocode"
        # prescribe `max_loan_amount = quantize_cents(-raw_pv)` based on the
        # theoretical cash-flow convention (pv NEGATIVE under standard sign
        # rules; negate to express principal received as positive).
        # Empirically numpy_financial 1.0.0 returns POSITIVE pv when pmt is
        # NEGATIVE — the library already inverts internally — so the
        # additional negation prescribed by RESEARCH would yield a NEGATIVE
        # max_loan_amount that fails Pydantic's Money ge=0 constraint
        # (verified via direct npf.pv test 2026-04-30: pmt=-1500 returns
        # +225461.35; pmt=+1500 returns -225461.35). The deviation from
        # RESEARCH pseudocode is pinned by the round-trip closure assertion
        # (D-09; SC-2: forward(reverse(req)).loan_amount == reverse.max_loan_amount
        # exactly).
        dti_limited_loan_amount = quantize_cents(raw_pv)
        max_loan_amount = dti_limited_loan_amount
        down_payment_cap_bound = False
        if request.target_ltv_pct < Decimal("1"):
            down_payment_limited_loan_amount = quantize_cents(
                request.down_payment
                * request.target_ltv_pct
                / (Decimal("1") - request.target_ltv_pct)
            )
            if down_payment_limited_loan_amount < max_loan_amount:
                max_loan_amount = down_payment_limited_loan_amount
                max_pi = quantize_cents(
                    max_pi * max_loan_amount / dti_limited_loan_amount
                    if dti_limited_loan_amount > Decimal("0")
                    else Decimal("0")
                )
                captured_warnings.append("DOWN-PAYMENT-CASH-BINDING")
                down_payment_cap_bound = True

        # 10. Derive property_value for downstream classify call (NOT surfaced
        #     on response — reverse mode commits to LTV, not a specific property).
        derived_property_value = quantize_cents(max_loan_amount / request.target_ltv_pct)
        if down_payment_cap_bound:
            assumed_monthly_mi, _ = _compute_monthly_mi(
                target_loan_type=request.target_loan_type,
                financed_loan_amount=max_loan_amount,
                property_value=derived_property_value,
                annual_rate=request.annual_rate,
                term_months=request.term_months,
                monthly_pmi=request.monthly_pmi,
                endorsement_date=endorsement_date,
            )

        # 11. Loan-type classification (D-11 step 1)
        county = _build_county(request.household.location)
        classified_loan_type, classify_blocker = _classify_target_loan_type(
            loan_amount=max_loan_amount,
            county=county,
            target_loan_type=request.target_loan_type,
        )

        # Collect StaleReferenceWarning strings (D-11 propagation; mirrors
        # evaluate_forward warnings capture).
        for w in captured:
            if issubclass(w.category, StaleReferenceWarning):
                captured_warnings.append(str(w.message))

    # derived_property_value is NOT surfaced on the response (reverse mode
    # commits to assumed_ltv_pct, not a specific property_value). It exists
    # solely to feed the classify call above. Underscore-prefixed-binding
    # convention not used here because the value is referenced one line
    # earlier (in classify); ruff F841 does not fire because the binding is
    # used by the classify call site.
    _ = derived_property_value  # documentation: intentional non-export

    # 12. Build response — blocked / blocked_by reflect ONLY the loan-type-classify
    # blocker (D-11 step 1). Plan 04-04 wraps evaluate_reverse with the rest of the
    # precedence pipeline (LTV/CLTV ceiling -> DTI cap -> ATR/QM -> VA-residual)
    # and mutates a NEW response (frozen models — model_copy(update={...})).
    return AffordabilityResponse(
        mode="reverse",
        loan_type=classified_loan_type,
        blocked=(classify_blocker is not None),
        blocked_by=classify_blocker,
        warnings=captured_warnings,
        total_gross_monthly_income=quantize_cents(total_gross_monthly_income),
        total_monthly_debts=quantize_cents(sum_monthly_debts),
        max_loan_amount=max_loan_amount,
        implied_pi=quantize_cents(max_pi),
        assumed_ltv_pct=request.target_ltv_pct,
        assumed_monthly_mi=quantize_cents(assumed_monthly_mi),
    )


# ---------------------------------------------------------------------------
# Plan 04-04: D-11 blocker-precedence pipeline + public evaluate() dispatcher
# ---------------------------------------------------------------------------


def _ltv_to_percentage_points(ltv_fraction: Decimal) -> Decimal:
    """Convert fractional LTV (Decimal('0.80')) to percentage points
    (Decimal('80.00')) for Fannie/Freddie predicate consumption.

    Fannie/Freddie predicates take ltv_pct AS PERCENTAGE POINTS (RESEARCH
    §"fannie_eligibility.py" line 246), NOT as a fraction. Quantizes to 2
    decimal places; the predicates raise ValueError on higher-precision
    input.
    """
    return (ltv_fraction * Decimal("100")).quantize(Decimal("0.01"))


def _ltv_bucket_label(ltv_pct_points: Decimal) -> str:
    """Coarse LTV bucket label for soft-warning citation strings
    (FANNIE-LLPA-... + FREDDIE-INELIGIBLE-...). Buckets:
    '60-OR-LESS', '60-75', '75-80', '80-85', '85-90', '90-95', 'OVER-95'.

    Note: this label is for the citation STRING; it does NOT replace the
    YAML-driven bucket lookup inside fannie_compute_llpa / freddie_evaluate
    (those still consult their own bucket tables).
    """
    if ltv_pct_points <= Decimal("60.00"):
        return "60-OR-LESS"
    if ltv_pct_points <= Decimal("75.00"):
        return "60-75"
    if ltv_pct_points <= Decimal("80.00"):
        return "75-80"
    if ltv_pct_points <= Decimal("85.00"):
        return "80-85"
    if ltv_pct_points <= Decimal("90.00"):
        return "85-90"
    if ltv_pct_points <= Decimal("95.00"):
        return "90-95"
    return "OVER-95"


def _credit_score_bucket_label(score: int) -> str:
    """Coarse credit-score bucket label for soft-warning citation strings.
    Phase 2 RUL-02 / RUL-03 use the standard 8-bucket boundaries
    (620, 640, 660, 680, 700, 720, 740, 760)."""
    if score < 620:
        return "BELOW-620"
    if score < 640:
        return "620-639"
    if score < 660:
        return "640-659"
    if score < 680:
        return "660-679"
    if score < 700:
        return "680-699"
    if score < 720:
        return "700-719"
    if score < 740:
        return "720-739"
    if score < 760:
        return "740-759"
    return "760-OR-ABOVE"


def _evaluate_blockers(
    response: AffordabilityResponse,
    request: ForwardModeRequest | ReverseModeRequest,
) -> AffordabilityResponse:
    """Apply D-11 blocker precedence to a math-only response from
    evaluate_forward / evaluate_reverse.

    Precedence (D-11 + RESEARCH Open Q#4):
      1. Loan-type classification — already wired in evaluate_forward /
         evaluate_reverse; short-circuits the rest of D-11 if the math-only
         pass already set response.blocked from the classify step.
      2. USDA income eligibility (when target_loan_type=='usda'; per
         RESEARCH Open Q#4 — placed AFTER classify, BEFORE LTV/CLTV ceiling).
      3. LTV / CLTV ceiling per target_loan_type (RESEARCH §"LTV / CLTV
         Ceiling Authority").
      4. DTI cap exceeded (forward mode only — reverse mode's solver
         enforces by construction per D-08; reverse mode never blocks here).
      5. ATR/QM general-QM (when first-lien residential AND apr+apor
         present; advisory if missing — RESEARCH §"Missing apr/apor").
      6. VA residual income (when target_loan_type=='va'). Citation read
         VERBATIM from result.binding_rule_citation per Phase 2 D-11.

    Soft warnings (always evaluated, never block):
      - Fannie LLPA hit (FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET})
      - Freddie ineligibility (FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET})
      - HPA-PMI-REQUIRED (when conventional + LTV > 0.80)
      - ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR (when one or both missing)

    Loan-amount convention: FHA LTV/CLTV ceilings use the base loan amount
    supplied by the request because collateral coverage is measured before
    financed UFMIP. ATR/QM and USDA affordability checks use the financed loan
    amount because payment cost and price thresholds include financed UFMIP.

    Returns a new AffordabilityResponse with updated blocked / blocked_by /
    warnings (Pydantic frozen — uses model_copy(update=...)).
    """
    # 1. Short-circuit: classify-step blocker already set in evaluate_forward
    #    / evaluate_reverse — but ALWAYS append soft warnings regardless of
    #    blocker state (T-04-04-05 mitigation: soft warnings must not be
    #    silently dropped when blocked).
    if response.blocked:
        return _append_soft_warnings(response, request)

    new_warnings: list[str] = list(response.warnings)
    new_blocked_by: str | None = None

    # Compute the LTV used for downstream checks (fraction; NOT percentage points).
    if isinstance(request, ForwardModeRequest):
        base_loan_amount = request.loan_amount
        ltv_fraction = response.ltv  # already computed in evaluate_forward
        cltv_fraction = response.cltv
        dti_back = response.dti_back
        financed_loan = response.financed_loan_amount or response.loan_amount
        if request.target_loan_type == "fha":
            ltv_fraction = quantize_rate(_compute_ltv(base_loan_amount, request.property_value))
            cltv_fraction = quantize_rate(
                _compute_cltv(
                    base_loan_amount,
                    request.junior_liens,
                    request.property_value,
                )
            )
    else:  # reverse
        ltv_fraction = response.assumed_ltv_pct
        # Reverse mode does NOT compute CLTV (no junior-lien semantics with no
        # surfaced property_value); treat CLTV-ceiling as not-applicable here.
        cltv_fraction = None
        # Reverse mode never blocks on DTI — enforced by construction (D-08);
        # consumers needing DTI-cap check must round-trip through forward mode.
        dti_back = None
        financed_loan = response.max_loan_amount

    target = request.target_loan_type
    loan_type_upper = target.upper()
    location = request.household.location

    # Capture warnings emitted by the predicates we call here (D-11 propagation
    # of StaleReferenceWarning emitted by lib.rules._loader).
    captured_warnings: list[str] = []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", StaleReferenceWarning)

        # 2. USDA income eligibility (RESEARCH Open Q#4 + BLOCKER 2 fix)
        if target == "usda" and new_blocked_by is None and financed_loan is not None:
            county = _build_county(location)
            # BLOCKER 2 fix: use request.household.size DIRECTLY (the FULL
            # household size including non-applicant dependents). Do NOT
            # infer from len(applicants) or va.family_size — silent
            # approximation produces wrong USDA decisions for households
            # with non-applicant dependents (e.g. 2-applicant + 3-children
            # case: applicants=2 but actual household_size=5). Plan 04-01
            # added the required `size` field; the validator pre-condition
            # guarantees it is present and >= 1. Per CLAUDE.md +
            # CONTEXT.md "fail loud, no inference".
            household_size = request.household.size
            household_income = response.total_gross_monthly_income * Decimal("12")
            usda_result = usda_evaluate(
                household_income=household_income,
                household_size=household_size,
                county=county,
                loan_amount=financed_loan,
                annual_rate=request.annual_rate,
                term_months=request.term_months,
            )
            if not usda_result.income_eligible:
                new_blocked_by = BLOCKED_BY_USDA_INCOME_TEMPLATE.format(
                    state_fips=location.state_fips,
                    county_fips=location.county_fips,
                )

        # 3. LTV / CLTV ceiling
        if new_blocked_by is None and ltv_fraction is not None:
            ltv_ceiling = LTV_CEILING_BY_TARGET[target]
            if ltv_fraction > ltv_ceiling:
                new_blocked_by = BLOCKED_BY_LTV_CEILING_TEMPLATE.format(
                    LOAN_TYPE=loan_type_upper,
                )

        if new_blocked_by is None and cltv_fraction is not None:
            cltv_ceiling = CLTV_CEILING_BY_TARGET[target]
            if cltv_fraction > cltv_ceiling:
                new_blocked_by = BLOCKED_BY_CLTV_CEILING_TEMPLATE.format(
                    LOAN_TYPE=loan_type_upper,
                )

        # 4. DTI cap (forward only; reverse enforces by construction).
        # Reverse mode never blocks on DTI — enforced by construction (D-08);
        # consumers needing DTI-cap check must round-trip through forward mode.
        if new_blocked_by is None and dti_back is not None and dti_back > request.max_dti:
            new_blocked_by = BLOCKED_BY_DTI_CAP_TEMPLATE.format(
                LOAN_TYPE=loan_type_upper,
            )

        # 5. ATR/QM general-QM (first-lien residential)
        #    Phase 4 v1 scope: all evaluations are first-lien residential
        #    (CONTEXT.md / RESEARCH §"Residential vs non-residential").
        #    Half-supplied apr/apor case is rejected at request boundary by
        #    _validate_common (Plan 04-01); both-None case falls through to
        #    the warning emitted by _append_soft_warnings.
        if (
            new_blocked_by is None
            and financed_loan is not None
            and request.apr is not None
            and request.apor is not None
        ):
            qm_passes = general_qm_passes(
                apr=request.apr,
                apor=request.apor,
                loan_amount=financed_loan,
                lien_position="first",
            )
            if not qm_passes:
                new_blocked_by = BLOCKED_BY_ATR_QM_PRICE_FIRST

        # 6. VA residual income (target=='va' only)
        if new_blocked_by is None and target == "va" and financed_loan is not None:
            va = request.household.va
            if va is None:
                new_blocked_by = "VA-RESIDUAL-NOT-SUPPLIED"
            else:
                va_result = va_residual_evaluate(
                    region=va.region,
                    family_size=va.family_size,
                    loan_amount=financed_loan,
                    actual_residual_income=va.actual_residual_income,
                )
                if va_result.status == "fail":
                    # READ VERBATIM (Phase 2 D-11 STABLE format; DO NOT
                    # format-shadow). The predicate's stable citation format is
                    # documented at lib/rules/va_residual_income.py L115; Phase 4
                    # reads it through unchanged via the .binding_rule_citation
                    # attribute below — never constructs the string here.
                    new_blocked_by = va_result.binding_rule_citation

        # Capture stale warnings emitted by all the predicate calls above.
        for w in captured:
            if issubclass(w.category, StaleReferenceWarning):
                captured_warnings.append(str(w.message))

    new_warnings.extend(captured_warnings)

    # Build intermediate response with hard blocker (if any) applied.
    intermediate = response.model_copy(
        update={
            "blocked": new_blocked_by is not None,
            "blocked_by": new_blocked_by,
            "warnings": new_warnings,
        }
    )

    # Always append soft warnings (T-04-04-05).
    return _append_soft_warnings(intermediate, request)


def _append_soft_warnings(
    response: AffordabilityResponse,
    request: ForwardModeRequest | ReverseModeRequest,
) -> AffordabilityResponse:
    """Append soft (non-blocking) warnings to response.warnings.

    Always-evaluated, regardless of hard-blocker state (T-04-04-05):
      - HPA-PMI-REQUIRED (when conventional + LTV > 0.80)
      - ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR (when both apr/apor None)
      - FANNIE-LLPA-{FICO}-{LTV} (when compute_llpa returns positive bps)
      - FREDDIE-INELIGIBLE-{FICO}-{LTV} (when freddie_evaluate.eligible == False)
    """
    soft: list[str] = []

    ltv_fraction = response.ltv if response.mode == "forward" else response.assumed_ltv_pct

    # HPA-PMI-REQUIRED — conventional + origination LTV > 0.80 (12 USC §4902).
    if (
        request.target_loan_type == "conventional"
        and ltv_fraction is not None
        and ltv_fraction > LTV_REQUEST_ELIGIBLE
    ):
        soft.append(WARNING_HPA_PMI_REQUIRED)

    # ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR — both missing case
    # (half-supplied is rejected at request boundary by _validate_common).
    if request.apr is None and request.apor is None:
        soft.append(WARNING_ATR_QM_NOT_EVALUATED)

    # Fannie LLPA + Freddie eligibility (only for conventional / jumbo
    # targets; FHA/VA/USDA are out of GSE scope).
    if request.target_loan_type in {"conventional", "jumbo"} and ltv_fraction is not None:
        min_credit_score = min(a.credit_score for a in request.household.applicants)
        ltv_pp = _ltv_to_percentage_points(ltv_fraction)
        ltv_bucket = _ltv_bucket_label(ltv_pp)
        fico_bucket = _credit_score_bucket_label(min_credit_score)

        with warnings.catch_warnings(record=True) as cw:
            warnings.simplefilter("always", StaleReferenceWarning)
            try:
                llpa_bps = fannie_compute_llpa(
                    credit_score=min_credit_score,
                    ltv_pct=ltv_pp,
                    loan_purpose="purchase",
                    occupancy="primary",
                    unit_count=1,
                )
                if llpa_bps > Decimal("0"):
                    soft.append(
                        WARNING_FANNIE_LLPA_TEMPLATE.format(
                            FICO_BUCKET=fico_bucket,
                            LTV_BUCKET=ltv_bucket,
                        )
                    )
            except (LookupError, ValueError):
                # T-04-04-07 ACCEPTED: Phase 2 predicates raise LookupError
                # on out-of-grid inputs (e.g., pre-2026 LLPA matrix bucket
                # misses). Treat as advisory (no warning) rather than
                # blocker — out-of-grid is informational; no actionable info.
                pass

            try:
                freddie_result = freddie_evaluate(
                    credit_score=min_credit_score,
                    ltv_pct=ltv_pp,
                    loan_purpose="purchase",
                    occupancy="primary",
                    unit_count=1,
                )
                if not freddie_result.eligible:
                    soft.append(
                        WARNING_FREDDIE_INELIGIBLE_TEMPLATE.format(
                            FICO_BUCKET=fico_bucket,
                            LTV_BUCKET=ltv_bucket,
                        )
                    )
            except (LookupError, ValueError):
                # Same T-04-04-07 rationale.
                pass

            for w in cw:
                if issubclass(w.category, StaleReferenceWarning):
                    soft.append(str(w.message))

    if not soft:
        return response

    return response.model_copy(update={"warnings": [*response.warnings, *soft]})


def evaluate(
    request: ForwardModeRequest | ReverseModeRequest,
) -> AffordabilityResponse:
    """Public Phase 4 entrypoint. Dispatches by request.mode and post-processes
    via the D-11 blocker-precedence pipeline.

    This is the function `scripts/affordability.py` (Plan 04-05) calls AFTER
    AffordabilityRequest.model_validate_json. AffordabilityRequest is the
    Annotated[ForwardModeRequest | ReverseModeRequest, Field(discriminator="mode")]
    union from Plan 04-01; Pydantic narrows the type at validation time so the
    callsite passes a concrete request (ForwardModeRequest or ReverseModeRequest)
    to this function.

    Pipeline:
      1. evaluate_forward / evaluate_reverse — pure math + classify blocker only.
      2. _evaluate_blockers — D-11 precedence (USDA-income → LTV/CLTV → DTI →
         ATR/QM → VA-residual) + soft warnings.
    """
    base = evaluate_forward(request) if request.mode == "forward" else evaluate_reverse(request)
    return _evaluate_blockers(base, request)
