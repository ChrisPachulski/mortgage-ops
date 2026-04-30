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

import numpy_financial as npf  # noqa: F401  # used by Plan 04-03 reverse; preloaded here
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.amortize import build_schedule
from lib.models import Loan, Money, Rate
from lib.money import quantize_cents
from lib.rules._loader import StaleReferenceWarning

# Phase 2 predicate full-path imports per Phase 2 D-08 (one predicate per citation).
# Wave 2 (Plan 04-02) promotes these to runtime imports because evaluate_forward
# calls them at runtime (RESEARCH §A.1-A.3 corrected signatures).
from lib.rules.conventional_pmi import LTV_REQUEST_ELIGIBLE  # Decimal("0.80") — RESEARCH §A.2
from lib.rules.fha_mip import compute as fha_mip_compute
from lib.rules.loan_type import (
    classify as loan_type_classify,
)
from lib.rules.types import County, LoanType, Region  # Pydantic resolves at runtime

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

# USDA annual guarantee fee rate (per lib.rules.usda compute formula
# guarantee_fee_annual = loan_amount * 0.0035; RESEARCH §"lib/rules/usda.py").
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

    - VA-only fields required when target_loan_type=='va' (RESEARCH Open Q#7)
    - apr/apor must be both-or-neither (RESEARCH §"ATR/QM Gating")
    - monthly_pmi required when target_loan_type=='conventional' AND origination
      LTV > LTV_REQUEST_ELIGIBLE (0.80) — RESEARCH Open Q#1; predicate has no rate
    """
    # VA conditional
    if req.target_loan_type == "va" and req.household.va is None:
        raise ValueError(
            "household.va block is required when target_loan_type=='va' "
            "(RESEARCH Open Question #7; D-15 + lib.rules.va_residual_income.evaluate)"
        )
    # apr / apor symmetry
    if (req.apr is None) != (req.apor is None):
        raise ValueError(
            "apr and apor must both be supplied or both be omitted "
            "(RESEARCH §'ATR/QM Gating'; reject half-supplied fabrication)"
        )
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
    dti_front: Rate | None = None
    dti_back: Rate | None = None
    ltv: Rate | None = None
    cltv: Rate | None = None
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
    front = piti / total_gross_monthly_income
    back = (piti + sum_monthly_debts) / total_gross_monthly_income
    return front, back


def _compute_ltv(loan_amount: Decimal, property_value: Decimal) -> Decimal:
    """LTV = loan_amount / property_value (AFFD-02). Decimal precision preserved."""
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
      usda -> quantize_cents((loan_amount * USDA_ANNUAL_FEE_RATE) / 12)
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
        # RESEARCH §"lib/rules/usda.py": guarantee_fee_annual = loan * 0.0035
        return (
            quantize_cents((financed_loan_amount * USDA_ANNUAL_FEE_RATE) / Decimal("12")),
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

    # 9-10. LTV + CLTV (use financed_loan_amount for FHA UFMIP semantics)
    ltv = _compute_ltv(financed_loan_amount, request.property_value)
    cltv = _compute_cltv(
        financed_loan_amount,
        request.junior_liens,
        request.property_value,
    )

    # 11. DTI front + back
    dti_front, dti_back = _compute_dti(
        piti=piti,
        sum_monthly_debts=sum_monthly_debts,
        total_gross_monthly_income=total_gross_monthly_income,
    )

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
    """Reverse-mode affordability: known max_dti + down_payment → max_loan_amount via npf.pv.

    Body shipped in Plan 04-03 (cross-plan stub idiom). Wave 1 / Plan 04-03 will:
      1. compute total_gross_monthly_income + total_monthly_debts
      2. max_PITI = max_dti * income - debts
      3. subtract escrow (tax + ins + HOA) + estimated monthly_mi → max_PI
      4. max_loan_amount = quantize_cents(-npf.pv(rate=annual_rate/12,
         nper=term_months, pmt=-max_PI, fv=0)) (D-08; npf bug #130 avoided
         via fv=0 default)
      5. evaluate blockers (loan-type-classify uses max_loan_amount + implied
         property_value)
      6. round-trip closure within Decimal('0.0001') is verified by
         evaluate_forward(reconstructed_forward_req).dti_back <= max_dti +
         tolerance (D-09; SC-2)
    """
    raise NotImplementedError("reverse evaluation shipped in Plan 04-03")
