# Phase 14: Property Analysis Pipeline - Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 14 new files (4 lib modules + 4 test modules + 4 JSON fixtures + 1 fixture README + 1 conftest extension)
**Analogs found:** 14 / 14
**Match quality:** all matches are EXACT or strong role-match — Phase 14 is pure composition over existing primitives, every new file has a direct sibling on disk.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `lib/household.py` | model | request-response | `lib/affordability.py` (Household + LocationFIPS classes, L339-433) | role-match (different field set, same conventions) |
| `lib/profile.py` | model | request-response | `lib/affordability.py` (_CommonRequestFields + VAInputs, L393-405, L441-456) | role-match (no direct profile precedent — analogous "preferences container") |
| `lib/property_analysis.py` | service / composition | request-response | `lib/affordability.py` (`evaluate(req)` + leaf models + private helpers, L1473-1492) + `lib/stress.py` (nested-block response shape, L242-261) | exact (same composition-over-primitives architecture) |
| `lib/property_verdict.py` | service / decision-cascade | request-response | `lib/affordability.py` `_evaluate_blockers` + `BLOCKED_BY_*` constants (L300-331, L1207-1380) | exact (blocker-cascade with predicate-coded reasons) |
| AnalysisReport / DownPaymentMatrix / ProgramResult / StressBlock / RefiBlock / PointsBlock / TaxBlock / Verdict / VerdictReason (location: planner's call — recommend `lib/property_analysis.py` co-location) | model bundle | request-response | `lib/stress.py` (StressRow / ScenarioSummary / StressResponse, L112-261) | exact |
| `tests/test_property_analysis.py` | test | fixture-driven | `tests/test_affordability.py` (fixture-driven blocker-cascade assertions, L838-928) + `tests/test_stress.py` (multi-mode fixture loader pattern, L530-567) | exact |
| `tests/test_property_verdict.py` | test | fixture-driven + citation-coverage meta-test | `tests/test_affordability.py::test_blocked_by_citation_coverage` (L1162-1199) + `tests/test_stress.py::test_phase_08_citation_coverage_meta` (L718-790) | exact |
| `tests/test_household.py` | test | model contract | `tests/test_property_listing.py` (PropertyListing model contract tests, L48-191) + `tests/test_models.py` (Loan/Money/Rate boundary tests, L25-130) | exact |
| `tests/test_profile.py` | test | model contract | same as `test_household.py` | exact |
| `tests/conftest.py` (EXTEND) | fixture loader | filesystem-read | existing `affordability_fixture` / `amortize_fixture` / `arm_fixture` / `stress_fixture` loaders (L40-92, L134-148) | exact (literal copy-paste-rename pattern) |
| `tests/fixtures/property_analysis/sfh_conforming_king_county.json` | fixture | filesystem-read | `tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json` (single-applicant + escrow + monthly_pmi shape) | exact |
| `tests/fixtures/property_analysis/condo_with_hoa_seattle.json` | fixture | filesystem-read | `tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json` (extend with hoa_monthly>0) | exact |
| `tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` | fixture | filesystem-read | `tests/fixtures/affordability/forward_jumbo_above_county_limit.json` (jumbo classify + blocker shape) | exact |
| `tests/fixtures/property_analysis/README.md` | docs | filesystem-read | `tests/fixtures/zillow/README.md` (synthetic-only policy + capture-and-sanitize recipe) | exact |

---

## Pattern Assignments

### `lib/household.py` (model, request-response)

**Analog:** `lib/affordability.py` (Phase 4 Household + LocationFIPS + EscrowInputs + MonthlyDebts at L339-433)

**Imports pattern** (copy from `lib/affordability.py` L174-188):

```python
from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from lib.models import Money, Rate  # noqa: TC001  # Pydantic resolves field annotations at runtime
```

Notes:
- `from __future__ import annotations` is the project-wide first line in every `lib/*.py`.
- The `# noqa: TC001  # Pydantic resolves field annotations at runtime` comment on the `lib.models` import is load-bearing — it's the established idiom that prevents ruff TC001 from moving Money/Rate into a `TYPE_CHECKING:` block where Pydantic v2 cannot resolve them. Verbatim copy from `lib/property_listing.py:23` and `lib/stress.py:79-83`.

**Strict/frozen/extra=forbid Pydantic pattern** (verbatim from `lib/affordability.py` L339-348, the LocationFIPS model — the closest 1:1 analog for Phase 14's NEW Household, which carries state_fips/county_fips/county_name per RESEARCH Pitfall 5):

```python
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
```

**Decimal-default pattern** (verbatim from `lib/affordability.py` L368-375 MonthlyDebts):

```python
class MonthlyDebts(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    auto: Money = Decimal("0.00")
    student_loans: Money = Decimal("0.00")
    credit_cards: Money = Decimal("0.00")
    other: Money = Decimal("0.00")
```

> **Load-bearing convention:** field defaults are constructed via `Decimal("0.00")`, NEVER `Decimal(0)` and NEVER `0.0`. CLAUDE.md money discipline is `Decimal from strings only`.

**Field-with-description pattern** (verbatim from `lib/affordability.py` L420-429, the `size` field on Household — Phase 14's `preferred_down_payment_pct` should mirror this exactly per D-14-STRESS-02):

```python
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
```

> **Phase 14 application:** `preferred_down_payment_pct: Rate = Decimal("0.20")` per D-14-STRESS-02. Use the same multi-line `description=` block to cite D-14-STRESS-02 + default-rationale.

**RESEARCH-pinned field set** (from 14-RESEARCH.md L427-454 — the recommended NEW Household shape):

```python
class Household(BaseModel):
    """Household financial state for property analysis (D-14-MODELS-01).
    DISTINCT from lib.affordability.Household (Phase 4 frozen contract).
    """
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    monthly_income: Money
    monthly_obligations: Money              # auto + student + cc + other aggregated
    fico: int = Field(ge=300, le=850)
    liquid_reserves: Money
    state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
    county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    county_name: str
    preferred_down_payment_pct: Rate = Decimal("0.20")
```

> **Anti-pattern to avoid (RESEARCH Anti-Patterns L482):** do NOT re-use the name `Household` while changing the field set in a different module unless the planner explicitly accepts the ambiguity. RESEARCH recommends keeping the class name `Household` BUT documenting in the docstring that it is "DISTINCT from lib.affordability.Household (Phase 4 frozen contract)". This pattern is already echoed in `lib/property_listing.py` (Phase 13's own `PropertyListing` is distinct from any Phase-4 listing concept and never shadows it).

---

### `lib/profile.py` (model, request-response)

**Analog:** `lib/affordability.py:VAInputs` (L393-405) for "preferences container that gates downstream branching" + `lib/affordability.py:_CommonRequestFields` (L441-456) for the apr/apor optional-fields convention.

**Imports + model pattern** (copy `lib/affordability.py` L393-405 VAInputs as the closest 1:1 analog — "a Pydantic block carrying analysis-time eligibility/program-gating booleans"):

```python
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
```

**Literal + boolean default pattern** (from RESEARCH 14-RESEARCH.md L458-477 + verbatim from `lib/property_listing.py` L25-26 for `Literal` aliasing at module top):

```python
# At module top — copies the Literal-alias pattern from lib/property_listing.py L25:
MilitaryStatus = Literal["active", "veteran", "reserve", "none"]
FilingStatus = Literal["single", "mfj", "mfs", "hoh"]


class Profile(BaseModel):
    """Analysis-time preferences + eligibility metadata (D-14-MODELS-02)."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    va_eligible: bool = False
    first_time_buyer: bool = False
    military_status: MilitaryStatus = "none"

    filing_status: FilingStatus = "mfj"
    marginal_tax_rate: Rate | None = None   # optional; Phase 14 ships Pub 936 boolean only
```

> **Load-bearing convention:** boolean defaults are spelled `False` (capital F, native Python — never `false` or `0`). `Literal` types are aliased at module top (not inlined into fields) so they can be imported by downstream modules without re-defining; mirrors `lib/property_listing.py` L25 (`PropertyType = Literal[...]`) and `lib/affordability.py` L239 (`TargetLoanType = Literal[...]`).

---

### `lib/property_analysis.py` (service / composition, request-response)

**Analog:** `lib/affordability.py:evaluate(...)` (L1473-1492) — the most direct architectural sibling. Phase 4's `evaluate` is a thin dispatcher over `evaluate_forward` + `_evaluate_blockers`; Phase 14's `analyze` will be a similar thin dispatcher over `_build_matrix` + `_build_stress_block` + `_build_refi_block` + `_build_points_block` + `_build_tax_block` + `synthesize_verdict`.

**Top-level composition entrypoint pattern** (verbatim from `lib/affordability.py` L1473-1492):

```python
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
```

> **Phase 14 application** — the `analyze(listing, household, profile)` function should mirror this exact shape: a docstring naming each sub-call by step number, a 1-2 line dispatcher body, with all real work in private `_build_*` helpers. Per Phase 14 RESEARCH §"Architecture" the analyze() body is a 6-step pipeline (resolve county/conforming-limit → fetch FRED rates → determine programs → fan-out matrix → auxiliary blocks → verdict synthesis).

**Per-cell inner-loop pattern** (verbatim from `lib/affordability.py` L805-949 — the `evaluate_forward` body; Phase 14's per-cell `_build_program_result` will mirror this exactly for each (program, dp_pct) tuple):

Key load-bearing excerpts:

```python
# 1. Joint applicant aggregation (D-06 + D-05 + D-07)
applicants = request.household.applicants
total_gross_monthly_income = sum(
    (a.gross_monthly_income for a in applicants),
    start=Decimal("0"),
)
debts = request.household.monthly_debts
sum_monthly_debts = debts.auto + debts.student_loans + debts.credit_cards + debts.other

# 6. Compute monthly P&I via Phase 3 build_schedule on the financed loan
financed_loan = _build_loan_for_amortization(
    principal=financed_loan_amount,
    annual_rate=request.annual_rate,
    term_months=request.term_months,
    origination_date=endorsement_date,
)
schedule = build_schedule(financed_loan)
monthly_pi = schedule.monthly_pi

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
```

> **Load-bearing conventions:**
> 1. **Quantize ONCE at end-of-period** — `quantize_cents(piti_pre_quantize)` is called exactly once per cell. Never per-component. CLAUDE.md money discipline.
> 2. **`start=Decimal("0")` on sum()** — Python's `sum()` defaults to int 0; mixing int 0 with Decimal poisons the result. Always pass `start=Decimal("0")`.
> 3. **MI is in PITI** — RESEARCH Pitfall 6: `piti = monthly_pi + monthly_tax + monthly_insurance + monthly_hoa + monthly_mi`. The "PITI" letters don't include MI, but the industry convention does. Mirror Phase 4 `_compute_piti` signature.

**Module-level constants pattern** (verbatim from `lib/affordability.py` L214-258 — cross-walk dicts and citation prefixes):

```python
# ---------------------------------------------------------------------------
# Module-level cross-walk constants (RESEARCH Open Question #3)
# ---------------------------------------------------------------------------

TARGET_LOAN_TYPE_CROSSWALK: dict[str, frozenset[str]] = {
    "conventional": frozenset({"conforming", "high_balance"}),
    "jumbo": frozenset({"jumbo"}),
    # ...
}
"""Cross-walk: target_loan_type → set of accepted Phase 2 LoanType values.

Used by Plan 04-04's _classify_target_loan_type to detect FHFA-LIMIT-* /
HUD-LIMIT-* blockers when lib.rules.loan_type.classify returns a LoanType
that's outside the requested target_loan_type's accepted set."""
```

> **Phase 14 application** — per RESEARCH Pitfall 2 + Pitfall 8, declare module-level constants for:
> - `DOWN_PAYMENT_PCTS: Final[list[Rate]] = [Decimal("0.03"), Decimal("0.05"), Decimal("0.10"), Decimal("0.15"), Decimal("0.20"), Decimal("0.25")]`
> - `PROGRAMS_BASE: Final[list[str]] = ["Conv30", "Conv15", "FHA30"]`
> - `_CONV_5_1_ARM_TERMS: Final[ARMTerms] = ARMTerms(...)`
> - `_CONV_PMI_ANNUAL_RATE: Final[Decimal] = Decimal("0.0075")` (per Pitfall 1 approach 2)
>
> The `Final` annotation + module-top placement is the established convention in `lib/affordability.py` (L248: `USDA_ANNUAL_FEE_RATE: Final[Decimal] = Decimal("0.0035")`).

**Nested-block response Pydantic shape** (verbatim from `lib/stress.py` L112-261 — StressRow / ScenarioSummary / StressResponse — the closest 1:1 analog for Phase 14's nested AnalysisReport schema):

```python
class StressRow(BaseModel):
    """One scenario row in StressResponse.rows. Summary scalars only (D-03)."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    label: str
    # Mode-specific scalars (only the ones relevant for the row's mode are non-None)
    monthly_pi: Money | None = None  # rate-shock
    total_interest: Money | None = None  # rate-shock + arm-reset
    delta_vs_baseline_monthly: Money | None = None  # rate-shock
    delta_vs_baseline_pct: Rate | None = None  # rate-shock
    dti_back: Rate | None = None  # income-shock
    breaches_threshold: bool | None = None  # income-shock
    blocked_by: str | None = None  # income-shock
    max_payment: Money | None = None  # arm-reset
    reset_count: int | None = None  # arm-reset
    highest_rate: Rate | None = None  # arm-reset


class ScenarioSummary(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    table: list[StressRow]
    baseline_label: str | None = None
    worst_case_label: str | None = None
    stress_invariant_violations: list[str] = Field(default_factory=list)


class StressResponse(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["rate-shock", "income-shock", "arm-reset"]
    scenario_count: int = Field(ge=0)
    summary: ScenarioSummary  # D-02: BEFORE rows
    rows: list[StressRow]
```

> **Load-bearing conventions:**
> 1. **`list[StressRow]` field type** — never `tuple[...]` or `dict[str, StressRow]`. Pydantic JSON serialization is most predictable with `list[...]`.
> 2. **Field declaration order is the JSON serialization order** (Pydantic v2 contract). Phase 8 D-02 pinned `summary: ScenarioSummary` BEFORE `rows: list[StressRow]` so the SC-5 subagent reads the summary table at the top of the JSON envelope. Phase 14 inherits: declare `matrix` before `verdict` so JSON-readers see the numeric data before the verdict letter.
> 3. **Signed Decimal fields drop `ge=0`** — RESEARCH Pitfall 3: `delta_vs_baseline_monthly: Money | None = None` works for stress because deltas can be negative — Phase 8 uses raw `Decimal` (not `Money`) where needed. Phase 14 will need this for `RefiRow.monthly_savings`, `RefiRow.npv_60mo`. Mirror `lib/refinance.py` D-03 RefiCashflow.amount + `lib/points.py` L80 PointsRequestFromSavings.monthly_savings (`Decimal = Field(strict=True, max_digits=14, decimal_places=2)` — no `ge=`).

**Discriminator-by-convention** (Pattern 1 from RESEARCH L264-301):

```python
class ProgramResult(BaseModel):
    """One cell in the DownPaymentMatrix (D-14-MATRIX-01 + D-14-MATRIX-02)."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    program: Literal["Conv30", "Conv15", "FHA30", "VA30", "Jumbo30"]
    down_payment_pct: Rate
    # ... numerics always populated (D-14-MATRIX-02) ...
    eligible: bool
    blocker_reasons: list[str]
    eligible_reasons: list[str]
```

> **Load-bearing convention:** the `program` field is a `Literal` discriminator by NAMING ONLY — there is no Pydantic `Field(discriminator='program')` because all 5 programs share the same shape (no variant fields). This differs from `lib/affordability.py:AffordabilityRequest` (L531-534) which IS a real `Field(discriminator='mode')` union, because Forward and Reverse requests have distinct fields. RESEARCH Pattern 1 spells this out.

---

### `lib/property_verdict.py` (service / decision-cascade, request-response)

**Analog:** `lib/affordability.py:_evaluate_blockers` (L1207-1380) — the closest 1:1 architectural analog. Phase 4's blocker cascade is the proven model for Phase 14's GO/WATCH/NO_GO synthesis (per CONTEXT D-14-VERDICT-04 + RESEARCH Pitfall 7 + 12).

**Predicate-code constants pattern** (verbatim from `lib/affordability.py` L300-331):

```python
# ----- Hard blockers: response.blocked_by candidates -----
# Format-string templates: callers use .format(...) at the call site.
# Plan 04-06 citation-coverage meta-test discovers these via grep on the
# `BLOCKED_BY_` prefix.

BLOCKED_BY_LTV_CEILING_TEMPLATE: Final[str] = "LTV-CEILING-{LOAN_TYPE}"
BLOCKED_BY_CLTV_CEILING_TEMPLATE: Final[str] = "CLTV-CEILING-{LOAN_TYPE}"
BLOCKED_BY_DTI_CAP_TEMPLATE: Final[str] = "DTI-CAP-{LOAN_TYPE}"
BLOCKED_BY_USDA_INCOME_TEMPLATE: Final[str] = "USDA-INCOME-LIMIT-{state_fips}-{county_fips}"
BLOCKED_BY_ATR_QM_PRICE_FIRST: Final[str] = "ATR-QM-PRICE-FIRST"

# ----- Soft warnings (response.warnings candidates) -----
WARNING_HPA_PMI_REQUIRED: Final[str] = "HPA-PMI-REQUIRED"
WARNING_ATR_QM_NOT_EVALUATED: Final[str] = "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR"
WARNING_FANNIE_LLPA_TEMPLATE: Final[str] = "FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}"
WARNING_FREDDIE_INELIGIBLE_TEMPLATE: Final[str] = "FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}"
```

> **Load-bearing conventions** (RESEARCH Pitfall 7):
> 1. **PREFIX discipline:** every hard-blocker constant starts `BLOCKED_BY_`; every soft-warning starts `WARNING_`. Phase 14 should mirror by using `VERDICT_NO_GO_*`, `VERDICT_WATCH_*`, `VERDICT_GO`.
> 2. **Templates vs literals:** when the citation includes runtime values (county FIPS, FICO bucket), declare a template ending in `_TEMPLATE` and `.format(...)` at call site. Plain string constants are used when the citation is fixed (ATR-QM-PRICE-FIRST).
> 3. **`Final[str]`** typing — enables ruff to catch accidental reassignment.

**Phase 14 verdict-code constants** (per RESEARCH Pitfall 7 L606-613 — recommended set):

```python
# lib/property_verdict.py — predicate codes for verdict reasons (D-14-VERDICT-04)
VERDICT_NO_GO_DTI_ALL_PROGRAMS: Final[str] = "DTI-CEILING-ALL-PROGRAMS"
VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP: Final[str] = "NO-ELIGIBLE-AT-PREFERRED-DP"
VERDICT_WATCH_FHA_MIP_BURDEN: Final[str] = "MIP-BURDEN-FHA"
VERDICT_WATCH_STRESS_INCOME_FAIL: Final[str] = "STRESS-INCOME-SHOCK"
VERDICT_WATCH_STRESS_RATE_FAIL: Final[str] = "STRESS-RATE-SHOCK"
VERDICT_WATCH_STRESS_ARM_RESET: Final[str] = "STRESS-ARM-RESET"
VERDICT_GO: Final[str] = "GO-ALL-GREEN"
```

**Blocker-cascade synthesize() body pattern** (verbatim from `lib/affordability.py` L1207-1380 — the precedence pipeline):

```python
def _evaluate_blockers(
    response: AffordabilityResponse,
    request: ForwardModeRequest | ReverseModeRequest,
) -> AffordabilityResponse:
    """Apply D-11 blocker precedence to a math-only response..."""

    # 1. Short-circuit: classify-step blocker already set
    if response.blocked:
        return _append_soft_warnings(response, request)

    new_warnings: list[str] = list(response.warnings)
    new_blocked_by: str | None = None

    # ... extract ltv_fraction, cltv_fraction, dti_back, financed_loan ...

    # 2. USDA income eligibility (RESEARCH Open Q#4)
    if target == "usda" and new_blocked_by is None and financed_loan is not None:
        # ...
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

    # 4. DTI cap
    if new_blocked_by is None and dti_back is not None and dti_back > request.max_dti:
        new_blocked_by = BLOCKED_BY_DTI_CAP_TEMPLATE.format(LOAN_TYPE=loan_type_upper)

    # ... ATR/QM, VA-residual ...

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
```

> **Load-bearing conventions:**
> 1. **First-match-wins precedence cascade** — the `if new_blocked_by is None and ...` guard on every subsequent stage is the cascade idiom. Phase 14's verdict cascade per CONTEXT D-14-VERDICT-01..04 has the same shape:
>    1. No eligible at any DP → NO_GO
>    2. No eligible at preferred DP → NO_GO
>    3. Stress-fail any eligible → WATCH
>    4. FHA-only eligible + MIP > $300 → WATCH
>    5. Otherwise → GO
> 2. **Frozen-model mutation via `model_copy(update={...})`** — Pydantic v2 + `frozen=True` rejects in-place mutation. The pattern is `response.model_copy(update={"field": new_value})` — verbatim from `lib/affordability.py:1371-1377`.
> 3. **VERBATIM citation read** (L1356-1361, the VA-residual block):
>    ```python
>    # READ VERBATIM (Phase 2 D-11 STABLE format; DO NOT format-shadow).
>    # The predicate's stable citation format is documented at
>    # lib/rules/va_residual_income.py L115; Phase 4 reads it through
>    # unchanged via the .binding_rule_citation attribute below — never
>    # constructs the string here.
>    new_blocked_by = va_result.binding_rule_citation
>    ```
>    Phase 14 inherits this discipline: when surfacing a `lib.affordability.AffordabilityResponse.blocked_by` string into a `VerdictReason.predicate_code`, READ IT VERBATIM. Never reformat. Tests must regex-assert the verbatim string makes it through.

**VerdictReason shape with predicate-code + computed-value pair** (per CONTEXT D-14-VERDICT-04 + RESEARCH L378-384):

```python
class VerdictReason(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    predicate_code: str                     # e.g., "DTI-CEILING-CONV", "MIP-BURDEN-FHA"
    computed_value: str                     # numeric value formatted as quoted Decimal string
    program: str | None = None              # which program (or None for cross-program)
    dp_pct: Rate | None = None              # which DP cell (or None for global verdicts)
```

> **Load-bearing convention:** `computed_value` is a STRING (e.g., `"0.51"`, `"325.00"`), not a `Decimal` or `Money`. The reason is that VerdictReason carries DTI rates AND dollar amounts AND raw counts — a polymorphic numeric field. Mirror the Phase 13 `field_serializer('baths')` precedent: serialize Decimal-as-string and store as `str` to keep the model JSON-stable. Tests assert verbatim string matches (e.g., `'"computed_value":"0.510000"'` in JSON output).

---

### AnalysisReport / DownPaymentMatrix / ProgramResult / StressBlock / RefiBlock / PointsBlock / TaxBlock / Verdict / VerdictReason

**Recommended location:** Co-locate all in `lib/property_analysis.py` (the planner's call per CONTEXT "Claude's Discretion", but the precedent in `lib/affordability.py` is to co-locate ALL leaf models + request + response in ONE file; same in `lib/stress.py` for StressRow/ScenarioSummary/StressResponse). Splitting into a separate `lib/property_models.py` introduces a circular-import risk between `property_analysis.py` and `property_verdict.py` if both need to construct Verdict — and breaks the "one composition file, one composition test" Phase 4/5/6/8 convention.

**Analog:** `lib/stress.py` L112-261 (full nested-block shape) + `lib/affordability.py` L547-592 (AffordabilityResponse multi-mode field population).

**Top-level AnalysisReport shape** (from 14-RESEARCH.md L386-410):

```python
class AnalysisReport(BaseModel):
    """Top-level Phase 14 output (D-14-MODELS-04). Phase 15's lib/property_report.py
    consumes this contract for markdown rendering."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    # Inputs echoed (for audit + Phase 15 narration)
    listing_snapshot: PropertyListing
    household_snapshot_hash: str   # SHA256 of household + profile YAML
    fetched_at: datetime

    # FRED rates used (D-14-REFI-02 audit trail)
    fred_mortgage_30us: Rate
    fred_mortgage_15us: Rate

    # The five blocks
    matrix: DownPaymentMatrix
    stress: StressBlock
    refi: RefiBlock
    points: PointsBlock
    tax: TaxBlock
    verdict: Verdict

    # Field declaration order MATTERS (mirrors Phase 8 D-02: summary before rows).
```

> **Load-bearing JSON-size budget** (RESEARCH Pitfall 10): assert `len(report.model_dump_json()) < 100_000` in at least one fixture-driven test. Mirrors `tests/test_stress.py::test_sc5_stress_sweep_50_scenarios_under_100kb` (L528-567):
>
> ```python
> serialized = response.model_dump_json(indent=2)
> size_bytes = len(serialized.encode("utf-8"))
> assert size_bytes < 100 * 1024, f"SC-5 violation: {size_bytes} bytes >= 100KB"
> ```

---

### `tests/test_property_analysis.py` (test, fixture-driven)

**Analog:** `tests/test_affordability.py` (L838-1153 — fixture-driven blocker-cascade assertions on AffordabilityResponse) + `tests/test_stress.py` (L528-567 — fixture-driven SC-5 size-budget test).

**Module docstring + imports pattern** (verbatim from `tests/test_affordability.py` L1-67):

```python
"""Phase 14 Property Analysis — full test surface (ANLZ-01..03 + VERD-01 + cross-cutting).

Plan 14-XX acceptance gate. ...

Per Phase 3 D-17 portability: subprocess invocation only [if/when Phase 15 ships a CLI];
never `import scripts.X` directly. SCRIPT_PATH is the single constant edited at Phase 10
when scripts/ relocates to .claude/skills/mortgage-ops/scripts/.

Per CONTEXT.md D-18: exact Decimal equality, never fuzzy comparators.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from lib.property_analysis import (
    AnalysisReport,
    DownPaymentMatrix,
    ProgramResult,
    analyze,
)
from lib.household import Household
from lib.profile import Profile

if TYPE_CHECKING:
    from collections.abc import Callable
```

**Fixture-driven assertion pattern** (verbatim from `tests/test_affordability.py` L838-928):

```python
def test_evaluate_clean_conventional_no_blocker() -> None:
    """Task 2 Test 1: clean conv 80% LTV → blocked=False, blocked_by=None."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is False
    assert resp.blocked_by is None


def test_evaluate_ltv_ceiling_blocker_conventional() -> None:
    """Task 2 Test 4: conv loan with LTV=0.98 (above 0.97 ceiling) → 'LTV-CEILING-CONVENTIONAL'."""
    req = ForwardModeRequest(...)
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "LTV-CEILING-CONVENTIONAL"
```

> **Load-bearing conventions:**
> 1. **Exact Decimal equality** (CLAUDE.md): `assert rows[1].monthly_pi == Decimal("2528.27")`. Never `pytest.approx` or `assertAlmostEqual` for money. `tests/test_stress.py:114` is the pinned example: `assert rows[1].monthly_pi == Decimal("2528.27")`.
> 2. **One test per blocker code** + **one test per verdict level** (GO/WATCH/NO_GO). Phase 14 has 7 verdict codes per recommended constants block → 7+ specific cascade tests minimum, plus 3 fixture-driven golden tests.
> 3. **Helper builders** for clean state (verbatim from `tests/test_affordability.py` L136-149: `_valid_applicant_kwargs`, `_valid_location_kwargs`, `_make_clean_household`). Phase 14 needs `_make_clean_household()`, `_make_clean_profile()`, `_make_clean_listing()` returning Phase 14 / Phase 13 Pydantic instances.

**Fixture loader call pattern** (verbatim from `tests/test_stress.py` L547-552):

```python
def test_sc5_stress_sweep_50_scenarios_under_100kb(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    fx = stress_fixture("rate_shock_size_budget_50_rates")
    adapter: TypeAdapter[Any] = TypeAdapter(StressRequest)
    request = adapter.validate_json(json.dumps(fx["request"]))
    response = evaluate(request)
```

> **Load-bearing convention:** strict-mode Decimal fields can NOT be validated via `validate_python(dict)` — only `validate_json(json.dumps(dict))` because Pydantic's JSON path coerces "0.065000" → Decimal, while the Python path requires the dict already carry Decimal instances. Phase 14 fixtures MUST use this idiom: load JSON, re-encode, validate.

---

### `tests/test_property_verdict.py` (test, fixture-driven + citation-coverage meta-test)

**Analog:** `tests/test_affordability.py::test_blocked_by_citation_coverage` (L1162-1199) + `tests/test_stress.py::test_phase_08_citation_coverage_meta` (L718-790).

**Citation-coverage meta-test pattern** (verbatim from `tests/test_affordability.py` L1162-1199):

```python
def test_blocked_by_citation_coverage() -> None:
    """RUL-12/13 inheritance: every BLOCKED_BY_* template introduced in
    lib/affordability.py is exercised by at least one fixture."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "affordability"
    all_blocked_by: list[str | None] = []
    for fp in sorted(fixtures_dir.glob("*.json")):
        data = json.loads(fp.read_text())
        if data.get("expected_response") is not None:
            all_blocked_by.append(data["expected_response"].get("blocked_by"))

    # Every non-VA template format must appear in at least one fixture.
    # DTI-CAP-* must be exercised
    dti_prefix = BLOCKED_BY_DTI_CAP_TEMPLATE.split("{")[0]  # "DTI-CAP-"
    assert any(bb is not None and bb.startswith(dti_prefix) for bb in all_blocked_by), (
        "No fixture exercises DTI-CAP-{LOAN_TYPE} citation template"
    )

    # FHFA-LIMIT-* (loan-type-classify mismatch)
    assert any(bb is not None and bb.startswith("FHFA-LIMIT-") for bb in all_blocked_by), (
        "No fixture exercises FHFA-LIMIT-* citation"
    )

    # VA-residual regex
    va_pattern = re.compile(BLOCKED_BY_VA_RESIDUAL_PATTERN)
    assert any(bb is not None and va_pattern.match(bb) for bb in all_blocked_by), (
        "No fixture exercises VA-RESIDUAL-{REGION}-FAMILY-{N} citation pattern"
    )
```

**Phase-wide citation-coverage meta-test pattern** (verbatim from `tests/test_stress.py` L718-790):

```python
def test_phase_08_citation_coverage_meta() -> None:
    """Every Phase 8 requirement (STRS-01..04 + PNTS-01..03) + ROADMAP SC-1..5
    has at least one fixture exercising it."""
    fix_stress = Path(__file__).parent / "fixtures" / "stress"
    fix_points = Path(__file__).parent / "fixtures" / "points"
    all_citations: list[str] = []
    for p in sorted(fix_stress.glob("*.json")) + sorted(fix_points.glob("*.json")):
        data = json.loads(p.read_text())
        meta = data.get("_meta", {})
        citation = meta.get("citation", "")
        all_citations.append(citation)
    # ...
    target_ids = [
        "STRS-01", "STRS-02", "STRS-03", "STRS-04",
        "PNTS-01", "PNTS-02", "PNTS-03",
        "ROADMAP SC-1", "ROADMAP SC-2", "ROADMAP SC-3", "ROADMAP SC-4", "ROADMAP SC-5",
    ]
    for req_id in target_ids:
        id_keys = {req_id, req_id.replace("ROADMAP ", "")}
        in_citation = any(any(k in c for k in id_keys) for c in all_citations)
        # ...
        assert in_citation or in_requirements, ...
```

> **Phase 14 application** — write `test_verdict_code_citation_coverage` that:
> 1. Greps `lib/property_verdict.py` for `VERDICT_*` constants (or imports them and inspects via `dir()`).
> 2. Iterates `tests/fixtures/property_analysis/*.json` and collects every `verdict.reasons[].predicate_code` value.
> 3. Asserts each `VERDICT_*` constant appears in at least one fixture's reasons list.
> 4. Also writes `test_phase_14_requirement_coverage_meta` that asserts each of `ANLZ-01`, `ANLZ-02`, `ANLZ-03`, `VERD-01` appears in at least one fixture's `_meta.citation`.

---

### `tests/test_household.py` and `tests/test_profile.py` (test, model contract)

**Analog:** `tests/test_property_listing.py` (PropertyListing model contract tests, L48-191) + `tests/test_models.py` (Loan/Money/Rate boundary tests, L25-130).

**Model contract test surface** (verbatim from `tests/test_property_listing.py` L30-119):

```python
def _make_min_listing(**overrides: Any) -> PropertyListing:
    """Factory: return a minimum-valid PropertyListing; overrides override any field.
    Defaults are MUST-HAVE-only ..."""
    defaults: dict[str, Any] = {
        "price": Decimal("625000.00"),
        "zip": "94110",
        "property_type": "SFH",
        # ...
    }
    defaults.update(overrides)
    return PropertyListing(**defaults)


def test_must_haves_only_validates() -> None:
    """D-13-MUSTHAVE-01: price + zip + property_type validates; others default None."""
    listing = _make_min_listing()
    assert listing.price == Decimal("625000.00")
    # ...


def test_round_trip_serialization_money_as_string() -> None:
    """PROP-02 baseline: model_dump_json -> Decimal-as-string; full byte-equal round-trip."""
    listing = _make_min_listing(tax_annual=ProvenancedMoney(...))
    s = listing.model_dump_json()
    assert '"price":"625000.00"' in s
    assert PropertyListing.model_validate_json(s) == listing


def test_rejects_float_price_strict_true() -> None:
    """strict=True must reject float for Decimal Money (CLAUDE.md money discipline)."""
    with pytest.raises(ValidationError):
        _make_min_listing(price=625000.0)


def test_extra_field_forbidden() -> None:
    """extra='forbid' rejects unknown fields (Phase 1 D-19 inheritance)."""
    with pytest.raises(ValidationError):
        _make_min_listing(unknown_field="x")


def test_frozen_listing_is_hashable() -> None:
    """frozen=True makes the model hashable (usable as dict key / set member)."""
    listing = _make_min_listing()
    assert hash(listing) is not None
    assert {listing} == {listing}
```

> **Load-bearing required tests per new model** (taxonomy from `tests/test_property_listing.py` + `tests/test_models.py`):
> 1. **Minimum-valid construction** — only required fields populate.
> 2. **strict=True rejects float** — `pytest.raises(ValidationError)` on `Decimal` fields fed a Python `float`.
> 3. **`extra="forbid"` rejects unknown fields** — `pytest.raises(ValidationError)` on `unknown_field="x"`.
> 4. **`frozen=True` makes hashable** — `hash(instance) is not None`; `{instance} == {instance}`.
> 5. **Round-trip serialization** — `model_dump_json()` → `model_validate_json()` returns equal instance.
> 6. **Decimal-as-JSON-string** — `'"field_name":"0.20"' in s` (not `0.20` numeric). CLAUDE.md money discipline.
> 7. **Range validators fire** — `fico=299` and `fico=851` raise; `preferred_down_payment_pct=Decimal("1.5")` raises (Rate ge=0 le=1).
> 8. **Pattern validators fire** — `state_fips="5"` and `state_fips="ABC"` raise.
> 9. **Default values populated correctly** — `preferred_down_payment_pct` defaults to `Decimal("0.20")` when omitted.

---

### `tests/conftest.py` (EXTEND)

**Analog:** existing `affordability_fixture` / `amortize_fixture` / `arm_fixture` / `stress_fixture` / `refinance_fixture` / `apr_fixture` / `points_fixture` loaders (L40-162).

**Loader pattern** (verbatim from `tests/conftest.py` L57-72 — the affordability_fixture loader, the closest 1:1 analog):

```python
@pytest.fixture
def affordability_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single affordability fixture by filename
    stem from tests/fixtures/affordability/. Mirrors `amortize_fixture` —
    one-fixture-per-file shape; loader takes a filename stem like
    "forward_va_residual_fail", not an id within an array.

    Per CONTEXT.md D-17: every Phase 4 fixture lives under
    tests/fixtures/affordability/ as one .json per scenario.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "affordability" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load
```

**Phase 14 application** — append to `tests/conftest.py` (do NOT replace existing fixtures):

```python
@pytest.fixture
def property_analysis_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single property-analysis fixture by filename
    stem from tests/fixtures/property_analysis/. Mirrors affordability_fixture /
    stress_fixture — one-fixture-per-file shape; loader takes a filename stem
    like "sfh_conforming_king_county", not an id within an array.

    Per Phase 14 PLAN-XX: every Phase 14 golden-value fixture lives under
    tests/fixtures/property_analysis/ as one .json per scenario.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "property_analysis" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load
```

> **Load-bearing conventions:**
> 1. **Loader signature `Callable[[str], dict[str, Any]]`** — same return type as all 7 existing fixtures. Tests then bind via parameter type: `def test_foo(property_analysis_fixture: Callable[[str], dict[str, Any]]) -> None:`.
> 2. **One-fixture-per-file** — never wrapped-in-array. Stem-based loading. The first phase to introduce stem-based loading was Phase 3 (`amortize_fixture`) and every subsequent phase has inherited the pattern.
> 3. **`# type: ignore[no-any-return]`** — verbatim. mypy strict-mode rule for the dict return.

---

### `tests/fixtures/property_analysis/sfh_conforming_king_county.json`, `condo_with_hoa_seattle.json`, `sfh_jumbo_bay_area.json`

**Analog:** `tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json` (King WA conforming SFH baseline) and `forward_jumbo_above_county_limit.json` (jumbo-classify blocker — direct analog for Phase 14's sfh_jumbo_bay_area).

**Fixture envelope shape** (verbatim from `tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json`):

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "id": "forward_conventional_85_ltv_with_pmi",
  "source": "Plan 04-06 D-17 fixture list; tests AFFD-04 PITI with monthly_pmi component",
  "rounding": "ROUND_HALF_UP",
  "notes": "Forward conventional 85% LTV: $425k/$500k @ 6.5%/30yr, monthly_pmi=$145.83 ...",
  "request": {
    "household": {
      "location": {
        "state_fips": "53",
        "county_fips": "033",
        "county_name": "King",
        "state": "WA",
        "zip": "98101"
      },
      "applicants": [...],
      "size": 1,
      "monthly_debts": {...},
      "escrow": {...},
      "va": null,
      "current_housing_payment": "0.00"
    },
    "max_dti": "0.430000",
    "target_loan_type": "conventional",
    "term_months": 360,
    "annual_rate": "0.065000",
    "monthly_pmi": "145.83",
    "mode": "forward",
    "loan_amount": "425000.00",
    "property_value": "500000.00"
  },
  "expected_response": {
    "mode": "forward",
    "loan_type": "conforming",
    "blocked": false,
    "blocked_by": null,
    "warnings": ["HPA-PMI-REQUIRED", "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR", "FANNIE-LLPA-720-739-80-85"],
    "total_gross_monthly_income": "12000.00",
    "loan_amount": "425000.00",
    "piti": "2832.12",
    "monthly_pi": "2686.29",
    "monthly_mi": "145.83",
    "ltv": "0.850000"
  }
}
```

**Citation-coverage `_meta` envelope** (verbatim from `tests/fixtures/stress/income_shock_5_10_20_pct.json` L1-6):

```json
{
  "_meta": {
    "citation": "ROADMAP SC-2 verbatim: ...",
    "engine_version": "Phase 8 Plan 08-02",
    "requirements": ["STRS-02", "ROADMAP SC-2"]
  },
  "request": {...},
  "expected": {...},
  "notes": "..."
}
```

> **Load-bearing conventions:**
> 1. **All Decimal values are JSON STRINGS** — `"loan_amount": "425000.00"`, never numeric. CLAUDE.md money discipline + Pydantic v2 `strict=True` rejects float.
> 2. **`_meta` block at fixture top** — every Phase 8+ fixture has this. Phase 14 inherits: each fixture carries `_meta.citation` mentioning ANLZ-01/02/03 + VERD-01 (or ROADMAP wording) and `_meta.requirements: list[str]` for the citation-coverage meta-test to grep.
> 3. **`expected_response` (Phase 4) or `expected` (Phase 8) block** — Phase 14 should use `expected_response: AnalysisReport` (mirror Phase 4's naming since the Phase 14 output IS a Response-style envelope). Inside `expected_response`, every dollar field is a quoted string for exact-equality comparison.
> 4. **Hand-calc citation in `notes`** — explain HOW the expected numbers were derived (e.g., "Phase 3 oracle: $400k @ 6.5%/30yr → monthly_pi=$2528.27"). Reviewers can re-verify by hand.

---

### `tests/fixtures/property_analysis/README.md`

**Analog:** `tests/fixtures/zillow/README.md` (L1-145 — synthetic-only-in-CI policy + capture-and-sanitize + what-not-to-put-here).

**Required sections** (verbatim section headings from `tests/fixtures/zillow/README.md`):

```markdown
# Property Analysis Fixtures (Phase 14)

Pinned, hand-calculated AnalysisReport oracles for deterministic ANLZ-01..03 +
VERD-01 tests. ...

## Files

| File | Tested SC | Covers | ...|
|------|-----------|--------|----|
| `sfh_conforming_king_county.json` | ANLZ-01..03 | Conv30/Conv15/FHA30 conforming SFH; full 4×6 matrix | ... |
| `condo_with_hoa_seattle.json` | ANLZ-01..03 | HOA-fee threads into PITI; PMI applies on Conv30 95% | ... |
| `sfh_jumbo_bay_area.json` | ANLZ-01, VERD-01 | price > conforming limit → Jumbo30 row appears; FHA/Conv blocked | ... |

## Why synthetic, not live (D-02 inherited from Phase 11)

[Standard 4-property block: Determinism / Zero recurring cost / Airgap-safe / Contract-is-shape]

## Capture-and-sanitize recipe (Phase 14-specific)

Each fixture's `expected_response` is HAND-CALCULATED with citation comments
in the `notes` field — never auto-captured from the engine. This is the
Phase 4 / Phase 8 golden-value oracle discipline (CLAUDE.md "Hand-calculated
golden-value fixtures with citation comments").

1. Derive monthly_pi via Phase 3 oracle (e.g., $400k @ 6.5%/30yr → $2528.27;
   the four pinned oracles in `tests/fixtures/golden_pmt.json`).
2. Add escrow + MI + HOA per the fixture's scenario.
3. Cite the hand-calc in `notes`: "Phase 3 oracle: ..., FHA UFMIP per
   lib/rules/fha_mip.py L65, ..."

## When to regenerate

- **After any change to `lib/property_analysis.py` `analyze()` body** that
  changes the AnalysisReport shape — every fixture's `expected_response`
  must be re-hand-calculated.
- **After any `data/reference/*.yml` refresh** (Phase 16 owns the
  refresh — Phase 14 fixtures inherit). Re-derive PITI cells.

## What NOT to put here

- **No real addresses.** Synthetic-only per Phase 11 D-02 inherited. Use
  `123 Synthetic Way, Seattle, WA 98101` style values. ZIP stays real (per
  Phase 13 README precedent: the ZIP is not PII on its own).
- **No AI-attribution markers.** Per the project-wide CLAUDE.md global rule.
- **No raw lender quotes.** Conventional PMI rates are bureau-specific; use
  the RESEARCH Pitfall 1 estimated value `Decimal("0.0075")` annualized.
- **No `config/household.yml` values.** Synthetic financial profiles only.
```

> **Load-bearing conventions:**
> 1. **Synthetic-only-in-CI policy citation** — Phase 11 D-02 is the policy anchor; every fixture README inherits the citation. Verbatim phrase: `synthetic-only per Phase 11 D-02 inherited`.
> 2. **"What NOT to put here" section is mandatory** — `tests/fixtures/{zillow,fred}/README.md` both have it. Specifically: no PII, no real lender quotes (bureau-specific), no AI-attribution markers.
> 3. **Each fixture row in the Files table** carries a `Tested SC` column mapping to the requirement IDs (`ANLZ-01`, etc.) — this becomes the citation-coverage anchor for `test_phase_14_requirement_coverage_meta`.

---

## Shared Patterns

### Strict / frozen / extra=forbid Pydantic model_config

**Source:** Universal across `lib/*.py`. First introduced in `lib/models.py` L39 (Loan).
**Apply to:** Every NEW Pydantic model in Phase 14 (Household, Profile, ProgramResult, DownPaymentMatrix, AnalysisReport, Verdict, VerdictReason, etc.).

```python
model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
```

> Three rules collapsed into one ConfigDict:
> - `strict=True` — rejects float for Decimal-typed fields (CLAUDE.md money discipline).
> - `frozen=True` — instances immutable post-construction; required for hashability + safety in concurrent contexts; mutations use `instance.model_copy(update={...})`.
> - `extra="forbid"` — typos in JSON inputs surface immediately. Reviewers + LLM agents catch field-name drift.

### Money / Rate Annotated aliases

**Source:** `lib/models.py` L23-33.
**Apply to:** Every dollar amount and rate in every NEW model.

```python
from lib.models import Money, Rate  # noqa: TC001  # Pydantic resolves field annotations at runtime
```

Then declare:

```python
field_name: Money              # non-negative dollar amount
rate_field: Rate               # fraction in [0, 1] with 6 decimal places
signed_amount: Decimal = Field(strict=True, max_digits=14, decimal_places=2)   # signed (drops ge=0)
```

> **Critical pitfall** (RESEARCH Pitfall 3 + CLAUDE.md L90):
> - `Money` has `ge=Decimal("0")` — rejects negative values.
> - `Rate` has `ge=Decimal("0"), le=Decimal("1")` — rejects values outside [0, 1] (so 6.5% is `0.065`, NEVER `6.5`).
> - For SIGNED Decimals (RefiRow.monthly_savings, VerdictReason internal computed values that can be negative), drop the `Money` alias and use raw `Decimal = Field(strict=True, max_digits=14, decimal_places=2)`. Precedent: `lib/refinance.py` D-03 + `lib/points.py` L80.

### `quantize_cents` / `quantize_rate` end-of-period rounding

**Source:** `lib/money.py` L1-73 + `lib/affordability.py` L186 import.
**Apply to:** Every computed monetary or rate value at end-of-period boundary.

```python
from lib.money import quantize_cents, quantize_rate

# In analyze() inner loop:
piti = quantize_cents(piti_pre_quantize)
ltv = quantize_rate(_compute_ltv(financed_loan_amount, request.property_value))
```

> **Conventions:**
> - **One quantize per period, at the END** — never quantize intermediates (Phase 3 D-04 PITFALLS).
> - **`quantize_cents` for money** (2 decimal places); **`quantize_rate` for rates** (6 decimal places — `Rate` alias `max_digits=7, decimal_places=6`).
> - **ROUND_HALF_UP** is baked into both helpers; never call `Decimal.quantize` directly.

### Module-level `Final[...]` constants

**Source:** `lib/affordability.py` L248 (`USDA_ANNUAL_FEE_RATE`), L281 (`LTV_CEILING_BY_TARGET`), L305-329 (BLOCKED_BY_* templates).
**Apply to:** Every Phase 14 policy choice (DOWN_PAYMENT_PCTS, PROGRAMS_BASE, _CONV_5_1_ARM_TERMS, _CONV_PMI_ANNUAL_RATE, VERDICT_* codes).

```python
from typing import Final

DOWN_PAYMENT_PCTS: Final[list[Rate]] = [
    Decimal("0.03"), Decimal("0.05"), Decimal("0.10"),
    Decimal("0.15"), Decimal("0.20"), Decimal("0.25"),
]
"""Per CONTEXT D-14-MATRIX-01: 4 programs × 6 DPs = 24 cells (or 5 × 6 = 30 with jumbo)."""

VERDICT_NO_GO_DTI_ALL_PROGRAMS: Final[str] = "DTI-CEILING-ALL-PROGRAMS"
"""Per CONTEXT D-14-VERDICT-04: predicate code cited by Verdict.reasons[].predicate_code."""
```

### `with_cache_lock` for FRED reads

**Source:** `lib/fred_cache.py` L235-356 + RESEARCH Code Example 3 (L785-818).
**Apply to:** Every FRED rate read in `lib/property_analysis.py`.

```python
from lib.fred_cache import CACHE_DIR, get_cached_or_fetch, with_cache_lock

with with_cache_lock(CACHE_DIR, reason=f"property-analysis read {series_id}"):
    entry = get_cached_or_fetch(series_id, fetcher=None)
```

> **Critical** (RESEARCH Pitfall 9): NEVER access `_load_cache()` directly. Phase 14 reads `fetcher=None` (no live-fetch from lib); Phase 15's CLI orchestrator handles cold-cache scenarios by invoking `scripts/fred_cli.py` first.

### Fixture-driven testing with `TypeAdapter.validate_json`

**Source:** `tests/test_affordability.py` L90-104 + `tests/test_stress.py` L547-552.
**Apply to:** Every Phase 14 fixture-driven test.

```python
from pydantic import TypeAdapter
adapter: TypeAdapter[AnalysisRequest] = TypeAdapter(AnalysisRequest)
# Strict-mode Decimal fields require JSON path (Python path rejects "0.065")
request = adapter.validate_json(json.dumps(fx["request"]))
response = analyze(request)
```

> **Critical:** strict-mode Decimal fields can NOT be validated via `validate_python(dict)`. Always re-encode to JSON. This is the load-bearing reason the conftest loaders return raw `dict[str, Any]` rather than pre-validated Pydantic instances — the test owns the validation step.

### Citation-coverage meta-test

**Source:** `tests/test_affordability.py::test_blocked_by_citation_coverage` (L1162-1199) + `tests/test_stress.py::test_phase_08_citation_coverage_meta` (L718-790).
**Apply to:** `tests/test_property_verdict.py` MUST include `test_verdict_code_citation_coverage` (verifies every VERDICT_* constant in lib/property_verdict.py is exercised by at least one fixture's `verdict.reasons[].predicate_code`) AND `test_phase_14_requirement_coverage_meta` (verifies ANLZ-01..03 + VERD-01 each appear in at least one fixture's `_meta.citation`).

### Helper-builder factories for clean test state

**Source:** `tests/test_affordability.py` L136-167 (`_valid_applicant_kwargs`, `_make_clean_household`).
**Apply to:** `tests/test_property_analysis.py` SHOULD ship `_make_clean_household()`, `_make_clean_profile()`, `_make_clean_listing()` returning Pydantic instances. Avoids 50-line setup blocks per test.

### Synthetic-only-in-CI fixture policy

**Source:** `tests/fixtures/zillow/README.md` (L56-79) + `tests/fixtures/fred/README.md` (L14-27).
**Apply to:** `tests/fixtures/property_analysis/README.md` MUST cite "Phase 11 D-02 inherited" and document the four properties: Determinism / Zero recurring cost / Airgap-safe / Contract-is-shape.

---

## No Analog Found

None. Every NEW Phase 14 file has at least one direct sibling already on disk.

---

## Metadata

**Analog search scope:**
- `/Users/cujo253/Documents/mortgage-ops/lib/` — all 16 .py files
- `/Users/cujo253/Documents/mortgage-ops/tests/` — all test_*.py files (28 modules)
- `/Users/cujo253/Documents/mortgage-ops/tests/fixtures/` — all 9 subdirectories (affordability, amortize, apr, arm, fred, points, refinance, skill, stress, subagent_transcripts, zillow)
- `/Users/cujo253/Documents/mortgage-ops/lib/rules/` — Phase 2 predicate library (12 modules)

**Files read (non-overlapping):**
- `lib/models.py` (full — 91 lines)
- `lib/property_listing.py` (full — 105 lines)
- `lib/affordability.py` (L1-200, L200-499, L500-799, L800-1099, L1200-1499 — targeted slices)
- `lib/stress.py` (L1-280, L280-560 — split at function boundary)
- `lib/refinance.py` (L1-150 — module docstring + leaf models)
- `lib/points.py` (L1-140 — module docstring + leaf models)
- `lib/property_persistence.py` (L1-60 — Phase 13 composition seam)
- `tests/conftest.py` (full — 282 lines)
- `tests/test_affordability.py` (L1-150, L820-1199 — citation-coverage focus)
- `tests/test_stress.py` (L1-200, L500-790 — citation-coverage + size-budget focus)
- `tests/test_amortize.py` (L1-120 — fixture-driven test pattern)
- `tests/test_models.py` (L1-130 — model boundary tests)
- `tests/test_property_listing.py` (full — 191 lines)
- `tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json` (full)
- `tests/fixtures/affordability/forward_jumbo_above_county_limit.json` (full)
- `tests/fixtures/stress/income_shock_5_10_20_pct.json` (full)
- `tests/fixtures/zillow/README.md` (full)
- `tests/fixtures/fred/README.md` (full)
- `.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md` (full)
- `.planning/phases/14-property-analysis-pipeline/14-RESEARCH.md` (L1-520 — pattern + pitfall coverage)
- `CLAUDE.md` (full — 154 lines)

**Pattern extraction date:** 2026-05-17

---

## PATTERN MAPPING COMPLETE

**Phase:** 14 - property-analysis-pipeline
**Files classified:** 14
**Analogs found:** 14 / 14 (all exact or strong role-match)

### Coverage
- Files with exact analog: 13
- Files with role-match analog: 1 (lib/profile.py — no Profile precedent, but VAInputs is the closest "eligibility-gating Pydantic block" analog)
- Files with no analog: 0

### Key Patterns Identified
- **Strict/frozen/extra=forbid Pydantic + Money/Rate Annotated aliases** are universal across every new model — sourced from `lib/models.py` L23-33 and `lib/affordability.py` L339-433 (LocationFIPS / MonthlyDebts / EscrowInputs / VAInputs / Household).
- **Blocker-cascade with predicate-coded reasons** is the verdict-synthesis architecture — sourced verbatim from `lib/affordability.py` `_evaluate_blockers` L1207-1380 (first-match-wins precedence + `BLOCKED_BY_*` `Final[str]` constants + `model_copy(update={...})` mutation of frozen models).
- **Composition over primitives, no new math** — `analyze()` mirrors `lib/affordability.py:evaluate()` L1473-1492 (thin dispatcher over private `_build_*` helpers); per-cell PITI follows `evaluate_forward` L805-949 (sum→amortize→escrow→quantize ONCE at end).
- **Nested-block response with field-declaration-order JSON contract** — `lib/stress.py:StressResponse` L242-261 is the analog for AnalysisReport (summary/matrix BEFORE rows/verdict; Pydantic v2 preserves declaration order in `model_dump_json`).
- **Citation-coverage meta-test discipline** — every Phase 4/8 phase ships one; Phase 14 inherits via `test_verdict_code_citation_coverage` (mirrors `tests/test_affordability.py` L1162-1199) AND `test_phase_14_requirement_coverage_meta` (mirrors `tests/test_stress.py` L718-790).
- **Fixture envelope shape** — one-fixture-per-file under `tests/fixtures/property_analysis/`, JSON `_meta.citation` + `_meta.requirements` blocks, `request` + `expected_response` blocks with every Decimal-as-string per CLAUDE.md money discipline.

### File Created
`/Users/cujo253/Documents/mortgage-ops/.planning/phases/14-property-analysis-pipeline/14-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog files + line ranges directly in PLAN.md action sections.
