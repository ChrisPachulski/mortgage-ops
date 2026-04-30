---
phase: 04-affordability
plan: 01
type: execute
wave: 1
depends_on: ["04-00"]
files_modified:
  - lib/affordability.py
autonomous: true
requirements: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-06, AFFD-07]
requirements_addressed: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-06, AFFD-07]
tags: [phase-4, affordability, pydantic, models, wave-1, request-response]

must_haves:
  truths:
    - "lib/affordability.py contains a discriminated-union AffordabilityRequest with `mode: Literal['forward', 'reverse']` (D-14)"
    - "AffordabilityResponse is a frozen+strict+extra=forbid Pydantic v2 model (CLAUDE.md money discipline + Phase 1+2+3 idiom)"
    - "Household.location requires explicit state_fips + county_fips (RESEARCH Open Q#2; lib.rules.types.County contract)"
    - "min(applicants[].credit_score) is the documented selector for Fannie LLPA + Freddie eligibility (D-05)"
    - "total_gross_monthly_income = sum(applicant.gross_monthly_income for applicant in applicants) (D-06)"
    - "Single-applicant case is len(applicants)==1; same code path as joint (D-07)"
    - "Household.size: int >= 1 — REQUIRED field representing FULL household size (including non-applicant dependents); drives USDA income-limit lookups via lib.rules.usda.evaluate (RESEARCH §lib/rules/usda.py L198-211); fail-loud, no inference from len(applicants) per CLAUDE.md + CONTEXT.md (BLOCKER 2 fix)"
    - "junior_liens: list[Money] (sum) — v1 simple shape per CONTEXT.md Claude's discretion"
    - "VA-only fields (region, family_size, actual_residual_income) are required-by-validator when target_loan_type == 'va' (RESEARCH Open Q#7)"
    - "monthly_pmi caller-supplied (Decimal | None); REQUIRED when target_loan_type == 'conventional' AND ltv > 0.80 (RESEARCH Open Q#1)"
    - "Loan-type cross-walk literal map exposed: {target → set of accepted Phase 2 LoanType values} (RESEARCH Open Q#3)"
    - "Module docstring lists every D-01..D-18 from CONTEXT.md as `LOCKED DECISION - D-NN` block (mirrors Phase 3 lib/amortize.py docstring template)"
    - "All money fields use Money/Rate aliases from lib.models with condecimal max_digits=14, decimal_places=2"
  artifacts:
    - path: lib/affordability.py
      provides: "Pydantic v2 request/response models + cross-walk + module docstring"
      contains: "class AffordabilityRequest"
      min_lines: 350
  key_links:
    - from: lib/affordability.py
      to: lib/models.py
      via: "import Loan, Money, Rate"
      pattern: "from lib\\.models import"
    - from: lib/affordability.py
      to: lib/rules/types.py
      via: "import County, LoanType, Region"
      pattern: "from lib\\.rules\\.types import"
    - from: lib/affordability.py
      to: tests/test_affordability.py
      via: "AffordabilityRequest / AffordabilityResponse model_validate_json + model_dump_json"
      pattern: "AffordabilityRequest|AffordabilityResponse"
---

<objective>
Land the Phase 4 Pydantic v2 type contract: `AffordabilityRequest` (forward + reverse discriminated union per D-14), `AffordabilityResponse`, plus all leaf models (`Applicant`, `Household`, `EscrowInputs`, `VAInputs`, `ForwardModeRequest`, `ReverseModeRequest`). All models are `ConfigDict(strict=True, frozen=True, extra="forbid")` per Phase 1+2+3 idiom.

Purpose: this plan ships the boundary contract that Plans 04-02 (forward), 04-03 (reverse), and 04-04 (blockers) all consume. By landing the types FIRST, downstream waves implement against a fixed surface and cannot drift.

Output: a single `lib/affordability.py` file containing ONLY models + module docstring + cross-walk constants + the empty function signatures `evaluate_forward(req: AffordabilityRequest) -> AffordabilityResponse: raise NotImplementedError("Plan 04-02")` and `evaluate_reverse(req: AffordabilityRequest) -> AffordabilityResponse: raise NotImplementedError("Plan 04-03")`. Plans 04-02/03/04 add bodies to these stubs (Phase 2 cross-plan stub idiom).

Decisions implemented:
- **D-01** (escrow block: property_tax_monthly / insurance_monthly / hoa_monthly Decimal-strings)
- **D-02** (PMI/MIP from predicates — but with Open Q#1 amendment: caller-supplied monthly_pmi for conventional > 80% LTV)
- **D-03** (UFMIP financing — auto-finance per RESEARCH §"FHA UFMIP Financing Convention" recommendation, surfaced in module docstring; implementation in Plan 04-02)
- **D-04** (property_value per-request, not in household.yml)
- **D-05** (single credit_score: int per applicant; min reduction)
- **D-06** (income aggregation = sum)
- **D-07** (single-applicant len(applicants)==1, same code path)
- **D-08** (one-shot npf.pv reverse with target_ltv_pct)
- **D-10** (reverse-mode JSON request shape verbatim)
- **D-11** (blocked_by: str | None + warnings: list[str] response shape)
- **D-12** (max_dti caller-supplied, no defaults)
- **D-14** (mode: forward | reverse discriminator)
- **RESEARCH Open Q#1** (caller-supplied monthly_pmi field on AffordabilityRequest)
- **RESEARCH Open Q#2** (state_fips + county_fips on Household.location)
- **RESEARCH Open Q#3** (loan-type cross-walk literal map)
- **RESEARCH Open Q#7** (VA-only fields required-by-validator when target_loan_type=='va')
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-affordability/04-CONTEXT.md
@.planning/phases/04-affordability/04-RESEARCH.md
@.planning/phases/04-affordability/04-PATTERNS.md
@CLAUDE.md
@lib/amortize.py
@lib/models.py
@lib/rules/types.py
@lib/rules/conventional_pmi.py
@lib/rules/loan_type.py

<interfaces>
<!-- Existing exports the new models depend on. Use these directly. -->

From lib/models.py:
```python
class Loan(BaseModel):
    principal: Money              # Decimal, condecimal(max_digits=14, decimal_places=2), ge=0
    annual_rate: Rate             # Decimal, condecimal(max_digits=7, decimal_places=6), in [0,1]
    term_months: int              # 1..600
    origination_date: date | None = None
    loan_type: Literal["fixed","arm","fha","va","usda","jumbo"] = "fixed"

# Type aliases (re-import in lib/affordability.py for consistency):
Money = Annotated[Decimal, condecimal(max_digits=14, decimal_places=2)]
Rate = Annotated[Decimal, condecimal(max_digits=7, decimal_places=6)]
```

From lib/rules/types.py:
```python
LoanType = Literal[
    "conforming", "high_balance", "jumbo",
    "fha_standard", "fha_high_balance",
    "va_standard", "va_high_balance",
    "usda",
]  # 8 values; Phase 2 D-08 strict
Region = Literal["northeast", "midwest", "south", "west"]

class County(BaseModel):
    state_fips: str   # 2-digit, regex-validated
    county_fips: str  # 3-digit
    name: str
```

From lib/rules/conventional_pmi.py:
```python
LTV_AUTO_TERMINATE: Final[Decimal] = Decimal("0.78")
LTV_REQUEST_ELIGIBLE: Final[Decimal] = Decimal("0.80")
```

From lib/amortize.py (model+ConfigDict pattern, copy-shape):
```python
class ExtraPrincipalEntry(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=1)
    amount: Decimal = Field(strict=True, gt=Decimal("0"), max_digits=14, decimal_places=2)
    recurring: bool = False
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create lib/affordability.py with module docstring + leaf Pydantic models + cross-walk</name>
  <files>lib/affordability.py</files>
  <read_first>
    - lib/amortize.py (lines 1-200 — module docstring template + Pydantic model patterns)
    - lib/models.py (full file — Loan, Money, Rate, condecimal usage)
    - lib/rules/types.py (full file — LoanType, Region, County)
    - lib/rules/conventional_pmi.py (lines 1-80 — LTV_REQUEST_ELIGIBLE constant import target)
    - .planning/phases/04-affordability/04-PATTERNS.md §"lib/affordability.py" (full section — module docstring shape + Pydantic patterns)
    - .planning/phases/04-affordability/04-CONTEXT.md §<decisions> (D-01 through D-18, full)
    - .planning/phases/04-affordability/04-RESEARCH.md §"Phase 2 Predicate Signature Audit" (drifts) + §"Open Questions for Planner" (1, 2, 3, 7)
  </read_first>
  <behavior>
    - Test 1: `from lib.affordability import AffordabilityRequest, AffordabilityResponse, Applicant, Household, EscrowInputs, VAInputs, evaluate_forward, evaluate_reverse, TARGET_LOAN_TYPE_CROSSWALK, TARGET_LOAN_TYPE_TO_PROGRAM` succeeds
    - Test 2: `Applicant(name="A", gross_monthly_income=Decimal("5000.00"), credit_score=720)` constructs cleanly (Decimal-from-Decimal works)
    - Test 3: `Applicant(name="A", gross_monthly_income=5000.00, credit_score=720)` raises ValidationError (strict=True rejects float)
    - Test 4: `Applicant(name="A", gross_monthly_income="5000.00", credit_score=720)` raises ValidationError (strict=True rejects str — Pydantic dict-validation is strict; only model_validate_json coerces; matches Phase 3 D-19)
    - Test 5: `Household(location={state_fips: "53", county_fips: "033", name: "King"}, applicants=[A], size=1, monthly_debts={...}, escrow={...})` constructs
    - Test 5b: `Household(...)` without `size` field raises ValidationError (size is REQUIRED; BLOCKER 2 fix)
    - Test 5c: `Household(..., size=0)` raises ValidationError (ge=1 constraint)
    - Test 5d: `Household(..., applicants=[A,B], size=5)` constructs successfully (size != len(applicants) is supported; the 2-applicant + 3-children case)
    - Test 6: `Household(...)` with `applicants=[]` raises ValidationError (len &gt;= 1)
    - Test 7: `AffordabilityRequest.model_validate_json('{"mode":"forward",...}')` discriminates on mode field
    - Test 8: `AffordabilityRequest(mode="forward", target_loan_type="va", va=None, ...)` raises ValidationError (model_validator: VA fields required when target_loan_type=='va')
    - Test 9: `AffordabilityRequest(mode="forward", target_loan_type="conventional", target_ltv_pct=Decimal("0.85"), monthly_pmi=None, ...)` raises ValidationError (model_validator: monthly_pmi required when conventional+ltv>0.80)
    - Test 10: `AffordabilityRequest(...)` with extra unknown field raises ValidationError (extra="forbid")
    - Test 11: `TARGET_LOAN_TYPE_CROSSWALK["conventional"] == frozenset({"conforming", "high_balance"})`
    - Test 12: `TARGET_LOAN_TYPE_TO_PROGRAM["conventional"] == "conventional"`, `["jumbo"] == "conventional"`, `["fha"] == "fha"`, `["va"] == "va"`, `["usda"] == "usda"`
    - Test 13: `evaluate_forward(...)` raises `NotImplementedError("forward evaluation shipped in Plan 04-02")` (Wave 1 cross-plan stub idiom; Plan 04-02 replaces body)
    - Test 14: `evaluate_reverse(...)` raises `NotImplementedError("reverse evaluation shipped in Plan 04-03")`
    - Test 15: `AffordabilityResponse` requires `mode: Literal["forward","reverse"]`, `loan_type: LoanType | None`, `blocked: bool`, `blocked_by: str | None`, `warnings: list[str]`, `total_gross_monthly_income: Money`, `total_monthly_debts: Money`, plus mode-specific optional fields (`dti_front, dti_back, ltv, cltv, piti, monthly_pi, monthly_mi, financed_loan_amount` for forward; `max_loan_amount, implied_pi, assumed_ltv_pct, assumed_monthly_mi` for reverse)
    - Test 16: `AffordabilityResponse` is `frozen=True` (assigning to a field after construction raises)
  </behavior>
  <action>
    Create `lib/affordability.py` with the following structure (line counts approximate; final length ~350-450 lines):

    **A. Module docstring (lines 1-~150)** — model after `lib/amortize.py` lines 1-49 template. Required content:

    1. One-line summary: `"""Household-aware affordability composition (AFFD-01..09)."""`
    2. Phase intent paragraph: composes Phase 1 models, Phase 2 predicates, Phase 3 amortization. First consumer of the rule layer.
    3. Architecture map (mirror lib/amortize.py shape):
       - `evaluate_forward(req)` — DTI/LTV/CLTV/PITI + blockers
       - `evaluate_reverse(req)` — npf.pv solver + blockers
       - Helper layer: `_compute_dti`, `_compute_ltv`, `_compute_cltv`, `_compute_piti`, `_classify_target_loan_type`, `_evaluate_blockers`
    4. **LOCKED DECISION blocks for D-01 through D-18** (one block per decision). Format from `lib/amortize.py:33-46`:
       ```
       LOCKED DECISION - D-NN (one-line summary; per CONTEXT.md):
         <2-5 lines of body>
       ```
       Decisions to enumerate (all 18 from CONTEXT.md):
       - D-01: caller-supplied monthly $ for tax/insurance/HOA
       - D-02: PMI/MIP from Phase 2 predicates (with RESEARCH Open Q#1 amendment: monthly_pmi caller-supplied for conventional > 80% LTV — predicate has no rate)
       - D-03: UFMIP auto-financed into principal (option (b)) per RESEARCH §"FHA UFMIP Financing Convention" recommendation
       - D-04: property_value per-request
       - D-05: min(credit_score) across applicants for Fannie LLPA + Freddie
       - D-06: sum(income) across applicants
       - D-07: single-applicant via len(applicants)==1
       - D-08: one-shot npf.pv reverse
       - D-09: round-trip closure within Decimal("0.0001")
       - D-10: reverse-mode JSON request shape (verbatim)
       - D-11: blocked_by + warnings shape; precedence: loan-type-classify → USDA-income (if usda; from RESEARCH Open Q#4) → LTV/CLTV → DTI → ATR/QM → VA-residual
       - D-12: max_dti caller-supplied
       - D-13: CLI mirrors Phase 3 D-17/18/19
       - D-14: mode discriminator
       - D-15: FINAL household.example.yml (with state_fips + county_fips per RESEARCH Open Q#2)
       - D-16: User-Layer pre-commit discipline preserved
       - D-17: hand-calc golden fixtures
       - D-18: exact Decimal equality

    5. **Phase 2 Predicate Signature Corrections block** (mirror RESEARCH §"Phase 2 Predicate Signature Audit"):
       ```
       Phase 2 predicate signature corrections (RESEARCH §"Phase 2 Predicate Signature Audit"):
         - loan_type.classify(loan_amount, county, program=) — NOT positional-only
         - conventional_pmi.status(loan, scheduled_balance, original_property_value, ...) — NOT (ltv_pct, ...); returns termination enum, not rate
         - fha_mip.compute(loan, original_property_value, endorsement_date) — NOT (loan_amount, ltv_pct, term_months); date.today() default
       ```
    6. **Loan-type cross-walk table** (RESEARCH Open Q#3):
       ```
       Loan-type cross-walk (RESEARCH Open Question #3):
         target_loan_type    accepted Phase 2 LoanType values   program=
         conventional        {conforming, high_balance}          "conventional"
         jumbo               {jumbo}                              "conventional"
         fha                 {fha_standard, fha_high_balance}    "fha"
         va                  {va_standard, va_high_balance}      "va"
         usda                {usda}                               "usda"
       ```
    7. **Conventional PMI rate sourcing** (RESEARCH Open Q#1): document that monthly_pmi is caller-supplied (Decimal), required when target_loan_type=='conventional' AND target_ltv_pct > LTV_REQUEST_ELIGIBLE (0.80); module enforces via Pydantic model_validator.
    8. **Stale-warning expected behavior** (RESEARCH §"_loader.py and StaleReferenceWarning"): document that fha-mip-rates.yml + va-residual-income.yml fire StaleReferenceWarning on every load (effective dates > 12mo old); response.warnings surfaces them by design.

    **B. Imports (after docstring)**:
    ```python
    from __future__ import annotations

    from datetime import date
    from decimal import Decimal
    from typing import TYPE_CHECKING, Literal

    from pydantic import BaseModel, ConfigDict, Field, model_validator

    from lib.models import Loan, Money, Rate

    # Phase 2 predicates — full-path imports per Phase 2 D-08 (one predicate per citation).
    # Wave 1 plans 04-02/03/04 use these; this plan only imports the types they need.
    from lib.rules.conventional_pmi import LTV_REQUEST_ELIGIBLE  # Decimal("0.80") — RESEARCH §A.2
    from lib.rules.types import LoanType, Region

    if TYPE_CHECKING:
        # County is constructed at evaluation time, not request validation time;
        # type-only import keeps the model surface decoupled from Phase 2 internals.
        from lib.rules.types import County  # noqa: F401
    ```

    **C. Module-level constants (RESEARCH Open Q#3 cross-walk):**
    ```python
    # Cross-walk: target_loan_type → set of accepted Phase 2 LoanType values
    # (RESEARCH Open Question #3). Used by _classify_target_loan_type to detect
    # FHFA-LIMIT-* / HUD-LIMIT-* blockers in Plan 04-04.
    TARGET_LOAN_TYPE_CROSSWALK: dict[str, frozenset[str]] = {
        "conventional": frozenset({"conforming", "high_balance"}),
        "jumbo": frozenset({"jumbo"}),
        "fha": frozenset({"fha_standard", "fha_high_balance"}),
        "va": frozenset({"va_standard", "va_high_balance"}),
        "usda": frozenset({"usda"}),
    }

    # Cross-walk: target_loan_type → program kwarg passed to lib.rules.loan_type.classify
    # (RESEARCH §A.1). Note jumbo → "conventional" because FHFA limits are the
    # authority that distinguishes conforming vs jumbo within the conventional bucket.
    TARGET_LOAN_TYPE_TO_PROGRAM: dict[str, Literal["conventional", "fha", "va", "usda"]] = {
        "conventional": "conventional",
        "jumbo": "conventional",
        "fha": "fha",
        "va": "va",
        "usda": "usda",
    }

    TargetLoanType = Literal["conventional", "fha", "va", "usda", "jumbo"]
    ```

    **D. Leaf Pydantic models (Applicant, MonthlyDebts, EscrowInputs, VAInputs, LocationFIPS):**

    Use the lib/amortize.py:156-194 ConfigDict pattern verbatim. Money fields use the `Money` type alias from lib.models. Examples:

    ```python
    class LocationFIPS(BaseModel):
        """Household location FIPS codes (RESEARCH Open Question #2; D-15 amendment).

        state_fips + county_fips are REQUIRED for County construction in Phase 2
        predicates. The county_name field is documentation only.
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
        county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
        county_name: str = Field(min_length=1)
        state: str = Field(min_length=2, max_length=2)  # display only
        zip: str | None = None


    class Applicant(BaseModel):
        """One applicant on the loan (D-05, D-06, D-07).

        credit_score is the caller-supplied representative score (mid-of-3 if 3
        scores; lower-of-2 if 2). Phase 4 picks min across applicants for Fannie
        LLPA + Freddie eligibility lookups.
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        name: str = Field(min_length=1)
        gross_monthly_income: Money
        credit_score: int = Field(ge=300, le=850)


    class MonthlyDebts(BaseModel):
        """Back-end DTI inputs (CONTEXT.md household.example.yml schema)."""

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        auto: Money = Field(default=Decimal("0.00"))
        student_loans: Money = Field(default=Decimal("0.00"))
        credit_cards: Money = Field(default=Decimal("0.00"))
        other: Money = Field(default=Decimal("0.00"))


    class EscrowInputs(BaseModel):
        """Caller-supplied PITI components (D-01)."""

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        property_tax_monthly: Money
        insurance_monthly: Money
        hoa_monthly: Money = Field(default=Decimal("0.00"))


    class VAInputs(BaseModel):
        """VA-specific inputs (D-15 optional; required-by-validator when target_loan_type=='va').

        region + family_size produce the stable citation
        f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}" via
        lib.rules.va_residual_income.evaluate (Phase 2 D-11; DO NOT format-drift).
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        region: Region
        family_size: int = Field(ge=1)
        actual_residual_income: Money


    class Household(BaseModel):
        """Household-stable facts (D-04: property_value is per-request, NOT here)."""

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
        current_housing_payment: Money = Field(default=Decimal("0.00"))
    ```

    **E. AffordabilityRequest discriminated union (D-14):**

    Use Pydantic `Field(discriminator="mode")` per PATTERNS.md adaptation note. Two flavors:
    `ForwardModeRequest`, `ReverseModeRequest`. Both share `household: Household`, `max_dti: Rate`, `target_loan_type: TargetLoanType`, `term_months: int`, `annual_rate: Rate`, optional `apr: Rate | None`, `apor: Rate | None`, `monthly_pmi: Money | None`, `endorsement_date_override: date | None`, `junior_liens: list[Money]`. Forward adds `loan_amount: Money`, `property_value: Money`. Reverse adds `down_payment: Money`, `target_ltv_pct: Rate`.

    Use a TWO-MODEL discriminated union (Pydantic v2 idiom):
    ```python
    class _CommonRequestFields(BaseModel):
        """Shared base fields. Not instantiated directly."""
        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        household: Household
        max_dti: Rate                   # caller-supplied per D-12
        target_loan_type: TargetLoanType
        term_months: int = Field(ge=1, le=600)
        annual_rate: Rate
        apr: Rate | None = None
        apor: Rate | None = None
        monthly_pmi: Money | None = None       # RESEARCH Open Q#1
        endorsement_date_override: date | None = None  # RESEARCH Open Q#6
        junior_liens: list[Money] = Field(default_factory=list)


    class ForwardModeRequest(_CommonRequestFields):
        """Forward-mode: known loan_amount + property_value → DTI/LTV/CLTV/PITI."""
        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        mode: Literal["forward"] = "forward"
        loan_amount: Money
        property_value: Money

        @model_validator(mode="after")
        def _validate_forward(self) -> ForwardModeRequest:
            return _validate_common(self)  # see helper below


    class ReverseModeRequest(_CommonRequestFields):
        """Reverse-mode: known max_dti + down_payment + target_ltv_pct → max_loan_amount via npf.pv (D-08, D-10)."""
        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        mode: Literal["reverse"] = "reverse"
        down_payment: Money
        target_ltv_pct: Rate

        @model_validator(mode="after")
        def _validate_reverse(self) -> ReverseModeRequest:
            return _validate_common(self)


    AffordabilityRequest = Annotated[
        ForwardModeRequest | ReverseModeRequest,
        Field(discriminator="mode"),
    ]
    ```

    **F. Conditional-required validator (RESEARCH Open Q#1 + Q#7):**

    ```python
    def _validate_common(req: _CommonRequestFields) -> Any:
        """Cross-field validators applied to both modes:

        - VA-only fields required when target_loan_type=='va' (RESEARCH Open Q#7)
        - apr/apor are both-or-neither (RESEARCH §"ATR/QM Gating")
        - monthly_pmi required when target_loan_type=='conventional' AND
          (forward: loan_amount/property_value > 0.80; reverse: target_ltv_pct > 0.80)
          (RESEARCH Open Q#1)
        """
        # VA conditional
        if req.target_loan_type == "va" and req.household.va is None:
            raise ValueError(
                "household.va block is required when target_loan_type=='va' "
                "(RESEARCH Open Question #7; D-15 + lib.rules.va_residual_income.evaluate)"
            )
        # apr/apor symmetry
        if (req.apr is None) != (req.apor is None):
            raise ValueError(
                "apr and apor must both be supplied or both be omitted "
                "(RESEARCH §'ATR/QM Gating'; reject half-supplied fabrication)"
            )
        # monthly_pmi conditional
        if req.target_loan_type == "conventional":
            if isinstance(req, ForwardModeRequest):
                origination_ltv = req.loan_amount / req.property_value
            else:  # ReverseModeRequest
                origination_ltv = req.target_ltv_pct
            if origination_ltv > LTV_REQUEST_ELIGIBLE and req.monthly_pmi is None:
                raise ValueError(
                    "monthly_pmi is required when target_loan_type=='conventional' "
                    "AND LTV > 0.80 (RESEARCH Open Question #1; conventional_pmi "
                    "predicate returns termination status only, not a rate; caller "
                    "must supply the PMI premium)"
                )
        return req
    ```

    **G. AffordabilityResponse (D-11 shape):**

    ```python
    class AffordabilityResponse(BaseModel):
        """Phase 4 evaluation result (D-11 shape).

        Forward-mode populates: dti_front, dti_back, ltv, cltv, piti, monthly_pi,
        monthly_mi, financed_loan_amount (for FHA UFMIP-financed loans per D-03).
        Reverse-mode populates: max_loan_amount, implied_pi, assumed_ltv_pct,
        assumed_monthly_mi.
        Both modes always populate: mode, loan_type, blocked, blocked_by, warnings,
        total_gross_monthly_income, total_monthly_debts.
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

        # Always populated
        mode: Literal["forward", "reverse"]
        loan_type: LoanType | None  # None if loan-type-classify raised MissingCountyDataError
        blocked: bool
        blocked_by: str | None      # exactly one citation; None when not blocked
        warnings: list[str] = Field(default_factory=list)
        total_gross_monthly_income: Money
        total_monthly_debts: Money

        # Forward-only (None in reverse mode)
        loan_amount: Money | None = None
        property_value: Money | None = None
        financed_loan_amount: Money | None = None  # = loan_amount + UFMIP if FHA per D-03
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
    ```

    **H. Stub function bodies (cross-plan stub idiom, Phase 2 D-08 pattern):**

    ```python
    def evaluate_forward(request: ForwardModeRequest) -> AffordabilityResponse:
        """Forward-mode affordability: known loan + property_value → DTI/LTV/CLTV/PITI.

        Body shipped in Plan 04-02 (cross-plan stub idiom; Phase 2 02-01 precedent).
        """
        raise NotImplementedError("forward evaluation shipped in Plan 04-02")


    def evaluate_reverse(request: ReverseModeRequest) -> AffordabilityResponse:
        """Reverse-mode affordability: known max_dti + down_payment → max_loan via npf.pv.

        Body shipped in Plan 04-03.
        """
        raise NotImplementedError("reverse evaluation shipped in Plan 04-03")
    ```

    Make sure to add `from typing import Annotated` to imports if using `Annotated[...]` for AffordabilityRequest. Also import `Any` for the validator helper return type.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "
from lib.affordability import (
    AffordabilityRequest, AffordabilityResponse,
    Applicant, Household, EscrowInputs, VAInputs, LocationFIPS, MonthlyDebts,
    ForwardModeRequest, ReverseModeRequest,
    evaluate_forward, evaluate_reverse,
    TARGET_LOAN_TYPE_CROSSWALK, TARGET_LOAN_TYPE_TO_PROGRAM,
)
from decimal import Decimal
import pytest
from pydantic import ValidationError

# Test 11: cross-walk table
assert TARGET_LOAN_TYPE_CROSSWALK['conventional'] == frozenset({'conforming', 'high_balance'})
assert TARGET_LOAN_TYPE_CROSSWALK['jumbo'] == frozenset({'jumbo'})
assert TARGET_LOAN_TYPE_CROSSWALK['fha'] == frozenset({'fha_standard', 'fha_high_balance'})
assert TARGET_LOAN_TYPE_CROSSWALK['va'] == frozenset({'va_standard', 'va_high_balance'})
assert TARGET_LOAN_TYPE_CROSSWALK['usda'] == frozenset({'usda'})

# Test 12: program cross-walk
assert TARGET_LOAN_TYPE_TO_PROGRAM['conventional'] == 'conventional'
assert TARGET_LOAN_TYPE_TO_PROGRAM['jumbo'] == 'conventional'
assert TARGET_LOAN_TYPE_TO_PROGRAM['fha'] == 'fha'
assert TARGET_LOAN_TYPE_TO_PROGRAM['va'] == 'va'
assert TARGET_LOAN_TYPE_TO_PROGRAM['usda'] == 'usda'

# Test 13/14: stub idiom
try:
    evaluate_forward(None)  # type: ignore
except NotImplementedError as e:
    assert 'Plan 04-02' in str(e)
try:
    evaluate_reverse(None)  # type: ignore
except NotImplementedError as e:
    assert 'Plan 04-03' in str(e)

print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - lib/affordability.py exists with &gt;= 350 lines
    - lib/affordability.py contains literal substring `class AffordabilityResponse(BaseModel):`
    - lib/affordability.py contains literal substring `class ForwardModeRequest(_CommonRequestFields):`
    - lib/affordability.py contains literal substring `class ReverseModeRequest(_CommonRequestFields):`
    - lib/affordability.py contains literal substring `class Applicant(BaseModel):`
    - lib/affordability.py contains literal substring `class Household(BaseModel):`
    - lib/affordability.py contains literal substring `size: int = Field(` (BLOCKER 2 fix; required full-household-size field)
    - lib/affordability.py Household block contains literal substring `Full household size including non-applicant dependents` (docstring per BLOCKER 2)
    - lib/affordability.py contains literal substring `class EscrowInputs(BaseModel):`
    - lib/affordability.py contains literal substring `class VAInputs(BaseModel):`
    - lib/affordability.py contains literal substring `class LocationFIPS(BaseModel):`
    - lib/affordability.py contains literal substring `Field(discriminator="mode")` (D-14 discriminator)
    - lib/affordability.py contains literal substring `TARGET_LOAN_TYPE_CROSSWALK` (RESEARCH Open Q#3)
    - lib/affordability.py contains literal substring `TARGET_LOAN_TYPE_TO_PROGRAM` (RESEARCH Open Q#3)
    - lib/affordability.py contains literal substring `from lib.rules.conventional_pmi import LTV_REQUEST_ELIGIBLE` (RESEARCH §A.2 statutory constant)
    - lib/affordability.py contains literal substring `from lib.models import Loan, Money, Rate`
    - lib/affordability.py contains literal substring `from lib.rules.types import LoanType, Region` (Phase 2 D-08 full-path imports)
    - lib/affordability.py contains literal substring `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` (frozen+strict+forbid pattern; Phase 1+2+3 idiom)
    - lib/affordability.py contains literal substring `raise NotImplementedError("forward evaluation shipped in Plan 04-02")` (cross-plan stub idiom)
    - lib/affordability.py contains literal substring `raise NotImplementedError("reverse evaluation shipped in Plan 04-03")` (cross-plan stub idiom)
    - lib/affordability.py module docstring contains all 18 LOCKED DECISION blocks: `grep -c "LOCKED DECISION - D-" lib/affordability.py | grep -v '^#'` returns &gt;= 18
    - lib/affordability.py docstring cites RESEARCH Open Questions: `grep -c "RESEARCH Open Question" lib/affordability.py | grep -v '^#'` returns &gt;= 3 (Q#1, Q#2/3, Q#7 minimum)
    - `uv run python -c "from lib.affordability import AffordabilityRequest"` succeeds (collection-clean import)
    - `uv run mypy --strict lib/affordability.py` exits 0 (no type errors on the model file)
    - `uv run ruff check lib/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    Pydantic v2 type contract is shipped; all 16 behavioral tests pass; lib/affordability.py importable cleanly; mypy + ruff clean; cross-walk tables exposed for Plan 04-04; evaluate_forward + evaluate_reverse are documented stubs awaiting Plans 04-02/03 bodies.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| JSON request → AffordabilityRequest.model_validate_json | Untrusted JSON crosses here at the script boundary (Plan 04-05); this plan ships the validator that catches it |
| Pydantic strict mode → Decimal money fields | Float-into-Money is a known foot-gun; strict=True dict-validation rejects, JSON-validation needs Plan 04-05 float-gate |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-01-01 | Tampering | AffordabilityRequest discriminated union | mitigate | `Field(discriminator="mode")` rejects unknown mode values at validation; `extra="forbid"` rejects typo'd field names; pinned by acceptance grep `Field(discriminator="mode")` |
| T-04-01-02 | Tampering | monthly_pmi missing for conventional > 80% LTV | mitigate | `_validate_common` raises ValueError; Pydantic wraps to ValidationError; surfaces in 6-key envelope at script boundary (Plan 04-05). Without this, PITI silently understates by ~$100-300/mo for typical conventional > 80% LTV loans. |
| T-04-01-03 | Tampering | VA fields missing when target_loan_type=='va' | mitigate | Same `_validate_common` raises ValueError; loud-fail per RESEARCH Open Q#7 |
| T-04-01-04 | Tampering | Float-into-Money JSON field | mitigate | Pydantic `strict=True` rejects float at dict-validation; JSON-validation float-gate ships in Plan 04-05 (mirrors Phase 3 D-19 / WR-02 closure) |
| T-04-01-05 | Tampering | apr/apor half-supplied (one but not both) | mitigate | `_validate_common` raises ValueError on `(req.apr is None) != (req.apor is None)` (RESEARCH §"ATR/QM Gating") |
| T-04-01-06 | Repudiation | Pydantic version-prefixed error URL drift across upgrades | accept | Plan 04-05 emits the runtime-pinned URL via `pydantic.VERSION`; Phase 3 03-06 already shipped this idiom; this plan inherits |
| T-04-01-07 | Information Disclosure | Module docstring exposes regulatory citations | accept | All citations are public regulatory sources (HUD, VA, CFPB, Fannie); no PII surface |
</threat_model>

<verification>
Run after Task 1 completes:

```bash
# Module imports cleanly (Wave 1+ depends on this)
uv run python -c "from lib.affordability import AffordabilityRequest, AffordabilityResponse; print('imports OK')"

# 18 D-XX LOCKED DECISION blocks
[ "$(grep -c 'LOCKED DECISION - D-' lib/affordability.py)" -ge 18 ]

# 9 leaf models + 2 stub functions present
grep -c "^class " lib/affordability.py  # expect >= 9 (LocationFIPS, Applicant, MonthlyDebts, EscrowInputs, VAInputs, Household, _CommonRequestFields, ForwardModeRequest, ReverseModeRequest, AffordabilityResponse)

# Cross-walk tables exposed
grep -c "TARGET_LOAN_TYPE_CROSSWALK" lib/affordability.py  # >= 2 (definition + at least one usage in docstring/code)
grep -c "TARGET_LOAN_TYPE_TO_PROGRAM" lib/affordability.py  # >= 2

# strict=True+frozen=True+extra=forbid on every Pydantic model
[ "$(grep -c 'strict=True, frozen=True, extra="forbid"' lib/affordability.py)" -ge 9 ]

# Cross-plan stub idiom
grep -c 'raise NotImplementedError("forward evaluation shipped in Plan 04-02")' lib/affordability.py  # = 1
grep -c 'raise NotImplementedError("reverse evaluation shipped in Plan 04-03")' lib/affordability.py  # = 1

# mypy + ruff clean
uv run mypy --strict lib/affordability.py
uv run ruff check lib/affordability.py

# Full suite still green (Phase 1/2/3 unaffected; Wave 0 stubs still xfail)
uv run pytest -x
```
</verification>

<success_criteria>
- [ ] `lib/affordability.py` exists with module docstring naming all 18 LOCKED DECISIONS (D-01..D-18)
- [ ] All Pydantic models use `ConfigDict(strict=True, frozen=True, extra="forbid")`
- [ ] AffordabilityRequest is a discriminated union by `mode` field per D-14
- [ ] LocationFIPS requires explicit state_fips + county_fips per RESEARCH Open Q#2
- [ ] _validate_common enforces: VA-required-when-va, apr/apor both-or-neither, monthly_pmi required for conventional+LTV>0.80
- [ ] TARGET_LOAN_TYPE_CROSSWALK and TARGET_LOAN_TYPE_TO_PROGRAM exposed for Plan 04-04 consumption
- [ ] evaluate_forward + evaluate_reverse are documented cross-plan stubs (Phase 2 D-08 stub idiom)
- [ ] mypy --strict + ruff clean on the new file
- [ ] All Wave 0 stubs still xfail (no regression to Plan 04-00)
- [ ] Full project suite still green
</success_criteria>

<output>
After completion, create `.planning/phases/04-affordability/04-01-SUMMARY.md` per the standard template. Plan 04-02 (forward), 04-03 (reverse), 04-04 (blockers) consume the contract from this plan in parallel.
</output>
