---
phase: 14
plan: 02
plan_id: 14-02
slug: matrix-models
type: execute
wave: 1
depends_on: []
files_modified:
  - lib/property_analysis.py
  - tests/test_property_analysis.py
  - tests/conftest.py
autonomous: true
requirements:
  - ANLZ-01
  - ANLZ-02
nyquist_compliant: true
tags:
  - pydantic
  - matrix
  - amortize
  - fha-mip
  - va-funding-fee
  - conforming-limit
  - property-analysis

must_haves:
  truths:
    - "lib/property_analysis.py defines the ProgramResult, DownPaymentMatrix, and all auxiliary nested-block Pydantic models (StressRow, StressBlock, RefiRow, RefiBlock, PointsRow, PointsBlock, TaxBlock, Verdict, VerdictReason, AnalysisReport)."
    - "Module-level Final constants exist: DOWN_PAYMENT_PCTS (list of 6 Decimal Rates), PROGRAMS_BASE (['Conv30', 'Conv15', 'FHA30']), _CONV_5_1_ARM_TERMS (ARMTerms instance), _CONV_PMI_ANNUAL_RATE (Decimal('0.0075'))."
    - "Per-cell composition function _build_program_result(program, dp_pct, listing, household, profile, rate) → ProgramResult correctly computes loan_amount, monthly_pi (via lib.amortize.build_schedule), monthly_mi per program (FHA via lib.rules.fha_mip.compute; VA via lib.rules.va_funding_fee.compute; Conv via _CONV_PMI_ANNUAL_RATE when LTV > 0.80; Jumbo treated as Conv-PMI), PITI (P&I + tax + insurance + HOA + MI), DTI back-end, LTV, and eligibility via lib.affordability.evaluate."
    - "Conforming-limit lookup uses lib.rules.loan_type.classify(loan_amount, County(state_fips, county_fips, county_name), program='conventional'); MissingCountyDataError caught gracefully (degrade to conforming-baseline)."
    - "DownPaymentMatrix carries exactly 24 cells (no jumbo) or 30 cells (jumbo triggered) per D-14-MATRIX-03; every cell populates all numerics regardless of eligibility per D-14-MATRIX-02."
    - "ProgramResult JSON contains no list[Payment] (no full schedule); summary scalars only, mirroring Phase 8 D-03."
    - "VA cells synthesize VAInputs deterministically: VAInputs(region='northeast', family_size=2, actual_residual_income=quantize_cents(monthly_income * Decimal('0.5'))); tag eligible_reasons with 'VA-RESIDUAL-SYNTHESIZED-V1' (B-2 fix)."
    - "PropertyListing helper _make_clean_listing defaults all Phase-13 required fields: source_url, zpid, fetched_at (B-3 fix)."
    - "ProvenancedMoney unwrap routes through _unwrap_provenanced(pm, default) — guards both pm is None AND pm.value is None (B-4 fix)."
    - "VA cells finance funding fee into principal (mirrors Phase 4 D-03 financed-UFMIP); monthly_mi=Decimal('0.00') for VA; eligible_reasons += ['VA-FUNDING-FEE-FINANCED'] (W-3 fix)."
  artifacts:
    - path: "lib/property_analysis.py"
      provides: "ProgramResult + DownPaymentMatrix + all output models + per-cell composition helpers + analyze() stub"
      contains: "class ProgramResult(BaseModel)"
    - path: "tests/test_property_analysis.py"
      provides: "ANLZ-01 + ANLZ-02 unit tests + golden assertions on matrix shape"
      contains: "def test_matrix_cell_count"
    - path: "tests/conftest.py"
      provides: "property_analysis_fixture loader (extended)"
      contains: "def property_analysis_fixture"
  key_links:
    - from: "lib/property_analysis.py:_build_program_result"
      to: "lib.amortize.build_schedule"
      via: "P&I computation per cell"
      pattern: "build_schedule\\("
    - from: "lib/property_analysis.py:_build_program_result"
      to: "lib.rules.fha_mip.compute"
      via: "FHA UFMIP + monthly MIP per FHA cell"
      pattern: "fha_mip.*compute\\("
    - from: "lib/property_analysis.py:_build_program_result"
      to: "lib.rules.va_funding_fee.compute"
      via: "VA funding fee per VA cell"
      pattern: "va_funding_fee.*compute\\("
    - from: "lib/property_analysis.py:_determine_programs"
      to: "lib.rules.loan_type.classify"
      via: "Jumbo-trigger classification"
      pattern: "classify\\("
---

<objective>
Ship the core matrix model layer + per-cell composition engine for Phase 14. This plan delivers:

1. **All Pydantic output models** for AnalysisReport (declared up-front in field-declaration order matching Phase 8 D-02). Co-located in `lib/property_analysis.py` per PATTERNS.md L461 rationale (avoid circular-import risk with property_verdict.py).
2. **Module-level Final constants** that downstream plans + tests rely on (DOWN_PAYMENT_PCTS, PROGRAMS_BASE, _CONV_5_1_ARM_TERMS, _CONV_PMI_ANNUAL_RATE per RESEARCH Pitfalls 1 + 2 + 8).
3. **Per-cell composition helper** `_build_program_result(...)` — the heart of D-14-MATRIX-01 + D-14-MATRIX-02 ("numerics computed even on ineligible rows").
4. **Matrix builder** `_build_matrix(...)` — fans out across programs × DPs; handles VA-eligibility gating (D-14-MODELS-02 → Profile.va_eligible) + Jumbo trigger via `lib.rules.loan_type.classify` (Pitfall 5).
5. **Wave-0 test scaffold** `tests/test_property_analysis.py` with ANLZ-01 + ANLZ-02 unit tests (matrix shape, cell count, ineligible-row numeric population, VA gating, Jumbo trigger, float rejection, FRED-lock serialization stub).
6. **`property_analysis_fixture` loader** added to `tests/conftest.py` (load-by-stem pattern per PATTERNS.md L759-775).

This plan deliberately **stops short of** stress/refi/points/tax (Plan 14-03), verdict synthesis (Plan 14-04), top-level `analyze()` composition (Plan 14-05), and golden-value fixtures (Plan 14-06). Those depend on what this plan ships.

Closes ANLZ-01 (multi-program fan-out + jumbo branch) and ANLZ-02 (DP sweep + DownPaymentMatrix).

Purpose: Plans 14-03..14-06 cannot operate without ProgramResult/DownPaymentMatrix/AnalysisReport schemas frozen and the per-cell driver functioning.

Output: ~400 LOC in lib/property_analysis.py + ~250 LOC in tests/test_property_analysis.py + ~20 LOC append in tests/conftest.py.

---

## Iteration-2 Fixes (Check Report)

- **B-2 (VA-program affordability construction):** Resolved via deterministic synthesis policy inside `_build_program_result` (NOT by extending Profile). VA cells construct `VAInputs(region="northeast", family_size=2, actual_residual_income=quantize_cents(household.monthly_income * Decimal("0.5")))` and append `"VA-RESIDUAL-SYNTHESIZED-V1"` to `eligible_reasons`. Tradeoff documented: real VA residual depends on region + family_size + obligations from VA M26-7 tables; the synthesis is conservative (50% of monthly income comfortably exceeds the highest M26-7 minimum residual of ~$1,158 for family_size=5 in the West region) but NOT exact. A follow-on phase may surface region/family_size on Profile if real VA accuracy is required.
- **B-3 (PropertyListing required fields):** `_make_clean_listing` helper defaults `source_url`, `zpid`, `fetched_at` so PropertyListing construction never raises on missing audit fields.
- **B-4 (ProvenancedMoney null-value handling):** Inline `listing.tax_annual.value if listing.tax_annual else 0` patterns replaced with `_unwrap_provenanced(pm, default)` helper. Guards both `pm is None` AND `pm.value is None`.
- **W-3 (VA funding fee monthly treatment):** Mirror Phase 4 D-03 financed-UFMIP convention. VA funding fee is added to principal; `monthly_mi = Decimal("0.00")` for VA cells; `eligible_reasons += ["VA-FUNDING-FEE-FINANCED"]`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md
@.planning/phases/14-property-analysis-pipeline/14-RESEARCH.md
@.planning/phases/14-property-analysis-pipeline/14-PATTERNS.md
@CLAUDE.md
@lib/models.py
@lib/money.py
@lib/amortize.py
@lib/affordability.py
@lib/arm.py
@lib/stress.py
@lib/property_listing.py
@lib/fred_cache.py
@lib/rules/loan_type.py
@lib/rules/types.py
@lib/rules/fha_mip.py
@lib/rules/va_funding_fee.py
@lib/rules/conventional_pmi.py
@tests/conftest.py
@tests/test_affordability.py
@tests/test_stress.py
@tests/test_property_listing.py

<interfaces>
<!-- From lib/amortize.py — the per-cell P&I driver. -->

```python
def build_schedule(loan: Loan, frequency: str = "monthly") -> Schedule: ...
# loan.principal: Decimal (already quantize_cents'd)
# loan.annual_rate: Decimal
# loan.term_months: int
# loan.loan_type: Literal["fixed", "fha", "va", ...]
# Returns Schedule with .monthly_pi: Decimal (already quantize_cents'd per Phase 3 D-15)
```

<!-- From lib/rules/types.py + lib/rules/loan_type.py — Jumbo trigger. -->

```python
class County(BaseModel):
    state_fips: str
    county_fips: str
    name: str

def classify(
    loan_amount: Decimal,
    county: County,
    program: str = "conventional",
    unit_count: int = 1,
) -> Literal["conforming", "high_balance", "jumbo", "fha_floor", ...]: ...
# Raises MissingCountyDataError when county not in high-cost subset AND loan_amount > baseline.
```

<!-- From lib/rules/fha_mip.py — FHA UFMIP + monthly MIP. -->

```python
def compute(loan: Loan, original_property_value: Decimal, endorsement_date: date) -> MIPResult: ...
# MIPResult.ufmip: Decimal (1.75% of base loan)
# MIPResult.annual_mip_pct: Decimal (e.g., 0.0055 for 55bps)
# MIPResult.terminates_at_period: int | None
# Phase 4 D-03: UFMIP is financed INTO principal — call build_schedule on base+ufmip.
```

<!-- From lib/rules/va_funding_fee.py — VA funding fee. -->

```python
def compute(
    loan_amount: Decimal,
    down_payment_pct: Decimal,
    is_first_use: bool,
    loan_purpose: Literal["purchase", "cash_out", "irrrl"] = "purchase",
    is_exempt_from_funding_fee: bool = False,
) -> Decimal: ...
# Returns DOLLAR AMOUNT of funding fee (NOT a rate).
```

<!-- From lib/fred_cache.py — FRED rate sourcing. -->

```python
def with_cache_lock(cache_dir: Path, reason: str): ...  # context manager
def get_cached_or_fetch(series_id: str, fetcher=None) -> dict: ...
CACHE_DIR: Path
# When fetcher=None and cache cold, raises NotImplementedError.
```

<!-- From lib/affordability.py — DTI / blocker cascade (used per cell for eligibility). -->

```python
def evaluate(request: ForwardModeRequest | ReverseModeRequest) -> AffordabilityResponse: ...
# AffordabilityResponse.blocked: bool
# AffordabilityResponse.blocked_by: str | None (the BLOCKED_BY_* citation when blocked)
# AffordabilityResponse.warnings: list[str]
```

<!-- From lib/affordability.py L393-405 — VAInputs (REQUIRED for target_loan_type='va' per _validate_common L467-471). -->

```python
class VAInputs(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    region: Region                          # Literal["northeast","midwest","south","west"]
    family_size: int = Field(ge=1)
    actual_residual_income: Money
```

<!-- From lib/rules/types.py L29 — Region literal. -->

```python
Region = Literal["northeast", "midwest", "south", "west"]
```

<!-- From lib/property_listing.py L44-86 — required audit fields (B-3). -->

```python
class PropertyListing(BaseModel):
    # ...
    source_url: str = Field(min_length=10)       # REQUIRED
    zpid: Annotated[str, Field(pattern=r"^\d+$")] # REQUIRED
    fetched_at: datetime                          # REQUIRED
```

<!-- From lib/property_listing.py L29-42 — ProvenancedMoney (B-4 unwrap target). -->

```python
class ProvenancedMoney(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    value: Money | None                           # value CAN be None even when wrapper is present
    provenance: Provenance
```

<!-- From lib/models.py — Money / Rate aliases (signed Decimals must NOT use Money — see Pitfall 3). -->

```python
Money = Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0"))]
Rate = Annotated[Decimal, Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1"))]
```

<!-- From lib/arm.py L88-105 — ARMTerms shape for _CONV_5_1_ARM_TERMS constant. -->

```python
class ARMTerms(BaseModel):
    initial_period_months: int
    reset_period_months: int
    initial_cap_bps: int
    periodic_cap_bps: int
    lifetime_cap_bps: int
    floor_rate: Decimal  # REQUIRED, no default
    margin_bps: int
    index_series_id: str
```

<!-- From lib/stress.py L242-261 — the response shape AnalysisReport mirrors. -->

```python
class StressResponse(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["rate-shock", "income-shock", "arm-reset"]
    scenario_count: int = Field(ge=0)
    summary: ScenarioSummary  # D-02: BEFORE rows
    rows: list[StressRow]
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create lib/property_analysis.py — all output models + module constants (no analyze() body yet)</name>
  <files>lib/property_analysis.py</files>
  <read_first>
    - lib/models.py (full — Money, Rate, Loan)
    - lib/stress.py L1-280 (StressRow, ScenarioSummary, StressResponse — the closest 1:1 analog for the nested-block shape)
    - lib/affordability.py L214-330 (module-level Final constants + BLOCKED_BY_* templates — the convention to mirror for DOWN_PAYMENT_PCTS / PROGRAMS_BASE / VERDICT_*)
    - lib/affordability.py L1473-1492 (evaluate() dispatcher — the analyze() shape to mirror)
    - lib/refinance.py L190-200 (RefiCashflow.amount precedent — signed Decimal NOT using Money alias)
    - lib/points.py L70-90 (PointsRequestFromSavings.monthly_savings — another signed-Decimal precedent)
    - lib/property_listing.py L1-105 (full — PropertyListing input contract referenced by AnalysisReport.listing_snapshot)
    - lib/arm.py L88-145 (ARMTerms — for _CONV_5_1_ARM_TERMS constant)
    - lib/household.py (created by Plan 14-01)
    - lib/profile.py (created by Plan 14-01)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L264-410 (Pattern 1: ProgramResult; Pattern 2: nested AnalysisReport blocks)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L538-693 (Pitfalls 2, 3, 8, 10 — Decimal-from-strings, signed-Decimal-not-Money, ARMTerms shape, JSON size budget)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L168-455 (lib/property_analysis.py + AnalysisReport co-location)
    - .planning/phases/14-property-analysis-pipeline/14-CONTEXT.md (D-14-MATRIX-01, D-14-MATRIX-02, D-14-MATRIX-03, D-14-STRESS-02, D-14-STRESS-03, D-14-MODELS-04)
  </read_first>
  <behavior>
    This task ships MODEL SHAPES + MODULE CONSTANTS only. No analyze() body. No per-cell helpers yet. Test behaviors are model-contract checks:
    - Behavior 1: `from lib.property_analysis import ProgramResult, DownPaymentMatrix, StressRow, StressBlock, RefiRow, RefiBlock, PointsRow, PointsBlock, TaxBlock, Verdict, VerdictReason, AnalysisReport` succeeds.
    - Behavior 2: `from lib.property_analysis import DOWN_PAYMENT_PCTS, PROGRAMS_BASE, _CONV_5_1_ARM_TERMS, _CONV_PMI_ANNUAL_RATE` succeeds.
    - Behavior 3: `DOWN_PAYMENT_PCTS == [Decimal("0.03"), Decimal("0.05"), Decimal("0.10"), Decimal("0.15"), Decimal("0.20"), Decimal("0.25")]` exactly.
    - Behavior 4: `PROGRAMS_BASE == ["Conv30", "Conv15", "FHA30"]` exactly (VA30 + Jumbo30 added conditionally; not in base).
    - Behavior 5: `_CONV_PMI_ANNUAL_RATE == Decimal("0.0075")` per Pitfall 1 approach 2.
    - Behavior 6: `_CONV_5_1_ARM_TERMS.initial_period_months == 60`, `.reset_period_months == 12`, `.initial_cap_bps == 500`, `.periodic_cap_bps == 200`, `.lifetime_cap_bps == 500`, `.floor_rate == Decimal("0.025")`, `.margin_bps == 250`, `.index_series_id == "MORTGAGE30US"`.
    - Behavior 7: `ProgramResult(program="Conv30", down_payment_pct=Decimal("0.20"), loan_amount=Decimal("500000.00"), monthly_pi=Decimal("3160.34"), monthly_tax=Decimal("500.00"), monthly_insurance=Decimal("100.00"), monthly_hoa=Decimal("0.00"), monthly_mi=Decimal("0.00"), piti=Decimal("3760.34"), cash_to_close=Decimal("125000.00"), dti_back=Decimal("0.350000"), ltv=Decimal("0.800000"), eligible=True, blocker_reasons=[], eligible_reasons=[])` validates.
    - Behavior 8: `ProgramResult(...program="not_a_program"...)` raises ValidationError (Literal enforcement).
    - Behavior 9: `RefiRow(...monthly_savings=Decimal("-150.00"), npv_60mo=Decimal("-2500.00")...)` validates (signed Decimal, NOT Money — Pitfall 3).
    - Behavior 10: `VerdictReason(predicate_code="DTI-CEILING-CONV", computed_value="0.510000", program="Conv30", dp_pct=Decimal("0.20"))` validates.
    - Behavior 11: `Verdict(level="GO", headline_reason="x", reasons=[...])` validates; `level="MAYBE"` raises (Literal enforcement on GO/WATCH/NO_GO).
    - Behavior 12: All models reject extra fields and float input on Decimal-typed fields.
    - Behavior 13: AnalysisReport requires matrix, stress, refi, points, tax, verdict, listing_snapshot, household_snapshot_hash, fetched_at, fred_mortgage_30us, fred_mortgage_15us (field-declaration order: matrix BEFORE verdict per D-02 inheritance from Phase 8).
  </behavior>
  <action>
    Create `lib/property_analysis.py` as a SINGLE module containing ALL Phase 14 output models + module-level constants. NO analyze() implementation in this task — just the static contract surface.

    Required module structure (verbatim header style mirroring lib/affordability.py L174-188 + lib/stress.py L1-90):
    1. `from __future__ import annotations` first line.
    2. Imports:
       - `from datetime import date, datetime`
       - `from decimal import Decimal`
       - `from typing import Annotated, Final, Literal`
       - `from pydantic import BaseModel, ConfigDict, Field`
       - `from lib.models import Money, Rate  # noqa: TC001`
       - `from lib.property_listing import PropertyListing, ProvenancedMoney  # noqa: TC001`
       - `from lib.arm import ARMTerms`
    3. Module docstring citing D-14-MODELS-04 and the public entrypoint (analyze) — note that analyze() body lands in Plan 14-05.

    **Module-level Final constants** (per PATTERNS.md L260-265 + RESEARCH.md Pitfalls 2 + 8):

    ```python
    DOWN_PAYMENT_PCTS: Final[list[Decimal]] = [
        Decimal("0.03"),
        Decimal("0.05"),
        Decimal("0.10"),
        Decimal("0.15"),
        Decimal("0.20"),
        Decimal("0.25"),
    ]
    """Per CONTEXT D-14-MATRIX-01: 4 programs × 6 DPs = 24 cells (or 5 × 6 = 30 with jumbo)."""

    PROGRAMS_BASE: Final[list[str]] = ["Conv30", "Conv15", "FHA30"]
    """Programs always present. VA30 added when profile.va_eligible; Jumbo30 added when price > conforming."""

    _CONV_PMI_ANNUAL_RATE: Final[Decimal] = Decimal("0.0075")
    """Per RESEARCH Pitfall 1 approach 2: 75bps annual PMI estimate. Surface as PMI-RATE-ESTIMATED warning in cells with LTV > 0.80."""

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
    """Per RESEARCH Pitfall 8: conventional 5/1 ARM defaults used in ARM-reset stress (D-14-STRESS-03)."""

    _CLOSING_COSTS_PCT: Final[Decimal] = Decimal("0.03")
    """Per RESEARCH Assumption A7: 3% of loan_amount estimate for cash-to-close. Mark closing_costs_estimated=True on ProgramResult."""

    DEFAULT_CONFORMING_TERM_MONTHS: Final[int] = 360
    DEFAULT_CONFORMING_15_TERM_MONTHS: Final[int] = 180
    ```

    **Pydantic models** (declaration order, all with `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`):

    Required models with exact field sets:
    - **ProgramResult** (per RESEARCH.md L272-302 + PATTERNS.md L312-322):
      - `program: Literal["Conv30", "Conv15", "FHA30", "VA30", "Jumbo30"]`
      - `down_payment_pct: Rate`
      - `loan_amount: Money` (financed amount; FHA includes UFMIP)
      - `monthly_pi: Money`
      - `monthly_tax: Money`
      - `monthly_insurance: Money`
      - `monthly_hoa: Money`
      - `monthly_mi: Money` (PMI/MIP/funding-fee-monthly equivalent; 0 when not applicable)
      - `piti: Money`
      - `cash_to_close: Money`
      - `dti_back: Rate`
      - `ltv: Rate`
      - `eligible: bool`
      - `blocker_reasons: list[str] = Field(default_factory=list)`
      - `eligible_reasons: list[str] = Field(default_factory=list)`
      - `closing_costs_estimated: bool = True` (Assumption A7)

    - **DownPaymentMatrix**:
      - `cells: list[ProgramResult]`
      - `programs_present: list[str]`
      - `down_payment_pcts: list[Rate]`

    - **StressRow** (mirrors RESEARCH.md L317-328):
      - `program: str`
      - `stress_kind: Literal["rate_shock", "income_shock", "arm_reset"]`
      - `baseline_piti: Money`
      - `stressed_piti: Money | None = None`
      - `stressed_dti_back: Rate`
      - `breaches_dti_ceiling: bool`
      - `blocker_reasons: list[str] = Field(default_factory=list)`

    - **StressBlock**:
      - `preferred_down_payment_pct: Rate`
      - `rows: list[StressRow]`

    - **RefiRow** (signed Decimal fields per RESEARCH Pitfall 3 — NOT Money):
      - `program: str`
      - `target_rate: Rate`
      - `scenario_label: Literal["minus_100bps", "fred_times_0_85"]` (note underscore in literal; valid Python identifier)
      - `monthly_savings: Decimal = Field(strict=True, max_digits=14, decimal_places=2)` (signed — drop ge=0)
      - `breakeven_months: int | None = None`
      - `npv_60mo: Decimal = Field(strict=True, max_digits=14, decimal_places=2)` (signed)

    - **RefiBlock**:
      - `rows: list[RefiRow]`

    - **PointsRow**:
      - `program: str`
      - `points_purchased: Literal[1, 2]`
      - `rate_drop: Rate` (e.g., Decimal("0.002500") per point; Assumption A3)
      - `simple_breakeven_months: int | None = None`
      - `npv_breakeven_months: int | None = None`
      - `note: str | None = None` (e.g., "WARNING-NO-POINTS-FOR-FHA-VA" when applicable)

    - **PointsBlock**:
      - `rows: list[PointsRow]`

    - **TaxBlock** (per RESEARCH.md L363-368):
      - `first_year_interest_per_program: dict[str, Money]`
      - `over_750k_cap_per_program: dict[str, bool]`
      - `qualified_loan_limit: Money`
      - `filing_status: Literal["single", "mfj", "mfs", "hoh"]`

    - **VerdictReason** (per RESEARCH.md L378-384 + PATTERNS.md L447-453):
      - `predicate_code: str`
      - `computed_value: str` (string, NOT Decimal — polymorphic numeric per PATTERNS.md L455)
      - `program: str | None = None`
      - `dp_pct: Rate | None = None`

    - **Verdict**:
      - `level: Literal["GO", "WATCH", "NO_GO"]`
      - `headline_reason: str`
      - `reasons: list[VerdictReason]`

    - **AnalysisReport** (per RESEARCH.md L386-410, PATTERNS.md L468-491):
      Field declaration order MATTERS (matrix before verdict per Phase 8 D-02):
      - `listing_snapshot: PropertyListing`
      - `household_snapshot_hash: str`
      - `fetched_at: datetime`
      - `fred_mortgage_30us: Rate`
      - `fred_mortgage_15us: Rate`
      - `matrix: DownPaymentMatrix`
      - `stress: StressBlock`
      - `refi: RefiBlock`
      - `points: PointsBlock`
      - `tax: TaxBlock`
      - `verdict: Verdict`
      - `warnings: list[str] = Field(default_factory=list)` (e.g., "MissingCountyDataError", "PMI-RATE-ESTIMATED")

    Add a placeholder stub function at the bottom:
    ```python
    def analyze(*args, **kwargs) -> AnalysisReport:
        """Top-level Phase 14 entrypoint. Implementation lands in Plan 14-05."""
        raise NotImplementedError("analyze() body lands in Plan 14-05")
    ```

    DO NOT implement `_build_program_result`, `_build_matrix`, `_determine_programs`, `_todays_rate_per_program`, or any composition helpers in this task — those land in Task 2.
    DO NOT define VERDICT_* constants here — those live in lib/property_verdict.py per Plan 14-04.
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py::test_models_importable tests/test_property_analysis.py::test_module_constants -x</automated>
  </verify>
  <acceptance_criteria>
    - `lib/property_analysis.py` exists.
    - `python -c "from lib.property_analysis import ProgramResult, DownPaymentMatrix, StressRow, StressBlock, RefiRow, RefiBlock, PointsRow, PointsBlock, TaxBlock, Verdict, VerdictReason, AnalysisReport, DOWN_PAYMENT_PCTS, PROGRAMS_BASE, _CONV_5_1_ARM_TERMS, _CONV_PMI_ANNUAL_RATE"` exits 0.
    - `python -c "from lib.property_analysis import DOWN_PAYMENT_PCTS; from decimal import Decimal; assert DOWN_PAYMENT_PCTS == [Decimal('0.03'), Decimal('0.05'), Decimal('0.10'), Decimal('0.15'), Decimal('0.20'), Decimal('0.25')]"` exits 0.
    - `python -c "from lib.property_analysis import _CONV_PMI_ANNUAL_RATE; from decimal import Decimal; assert _CONV_PMI_ANNUAL_RATE == Decimal('0.0075')"` exits 0.
    - `python -c "from lib.property_analysis import _CONV_5_1_ARM_TERMS; assert _CONV_5_1_ARM_TERMS.initial_period_months == 60 and _CONV_5_1_ARM_TERMS.lifetime_cap_bps == 500"` exits 0.
    - `python -c "from lib.property_analysis import analyze; analyze()"` raises `NotImplementedError` with the message containing "Plan 14-05".
    - `grep -c 'model_config = ConfigDict(strict=True, frozen=True, extra="forbid")' lib/property_analysis.py` returns at least 12 (one per model; ProgramResult + DownPaymentMatrix + StressRow + StressBlock + RefiRow + RefiBlock + PointsRow + PointsBlock + TaxBlock + VerdictReason + Verdict + AnalysisReport).
    - `grep -v '^#' lib/property_analysis.py | grep -c 'monthly_savings: Decimal = Field(strict=True, max_digits=14, decimal_places=2)'` returns at least 1 (signed-Decimal precedent, not Money).
    - `grep -v '^#' lib/property_analysis.py | grep -c 'npv_60mo: Decimal = Field(strict=True, max_digits=14, decimal_places=2)'` returns at least 1.
    - `grep -c 'Literal\["GO", "WATCH", "NO_GO"\]' lib/property_analysis.py` returns 1.
    - `grep -c 'Literal\["Conv30", "Conv15", "FHA30", "VA30", "Jumbo30"\]' lib/property_analysis.py` returns 1.
    - In the AnalysisReport class definition, the `matrix:` field appears on a line whose line-number is LESS than the line containing `verdict:` (matrix before verdict per D-02). Verified: `awk '/class AnalysisReport/,/^class /' lib/property_analysis.py | grep -n 'matrix:\\|verdict:'` shows matrix first.
  </acceptance_criteria>
  <done>
    All output models + module constants importable; pydantic contract tests pass; ready for Task 2 to add the per-cell composition helpers.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add per-cell composition helpers + matrix builder to lib/property_analysis.py</name>
  <files>lib/property_analysis.py</files>
  <read_first>
    - lib/property_analysis.py (the file from Task 1)
    - lib/amortize.py L255-292 (build_schedule signature)
    - lib/affordability.py L805-949 (evaluate_forward inner loop — the per-cell PITI driver to mirror; load-bearing for "quantize ONCE at end" + "MI is in PITI")
    - lib/affordability.py L36-40 (Phase 4 D-03: UFMIP is financed into principal)
    - lib/affordability.py L393-405 (VAInputs shape — region/family_size/actual_residual_income required)
    - lib/affordability.py L458-493 (_validate_common: enforces household.va presence when target_loan_type='va')
    - lib/rules/types.py L29 (Region = Literal["northeast","midwest","south","west"])
    - lib/rules/fha_mip.py L65-130 (compute signature)
    - lib/rules/va_funding_fee.py L60-110 (compute signature; returns DOLLAR amount, not rate)
    - lib/rules/loan_type.py L55-115 (classify signature; raises MissingCountyDataError)
    - lib/rules/types.py (County model)
    - lib/rules/conventional_pmi.py (TerminationStatus + LTV_REQUEST_ELIGIBLE constant; returns enum, NOT rate — Pitfall 1)
    - lib/money.py L1-73 (quantize_cents, quantize_rate)
    - lib/fred_cache.py L235-356 (get_cached_or_fetch + with_cache_lock contract)
    - lib/affordability.py L407-540 (Phase 4 Household / Applicant / EscrowInputs / MonthlyDebts shapes — needed to construct the affordability request from Phase 14's Household + PropertyListing inputs)
    - lib/property_listing.py L29-105 (full — PropertyListing fields + ProvenancedMoney shape including value can be None)
    - lib/household.py (Phase 14 Household — input to _build_program_result)
    - lib/profile.py (Phase 14 Profile — input to _build_program_result)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L711-878 (Code Examples 1-4 — verbatim composition patterns)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L520-695 (Pitfalls 1, 2, 4, 5, 6, 9 — composition-critical mitigations)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L199-237 (per-cell inner-loop pattern — quantize ONCE; MI in PITI; start=Decimal("0") on sum())
  </read_first>
  <behavior>
    - Behavior 1: `_todays_rate_per_program("Conv30")` returns a Decimal rate from FRED MORTGAGE30US cache (via with_cache_lock).
    - Behavior 2: `_todays_rate_per_program("Conv15")` returns a Decimal from MORTGAGE15US cache.
    - Behavior 3: `_todays_rate_per_program("Conv30-ARM-5-1")` returns `MORTGAGE30US - Decimal("0.0025")` per D-14-REFI-02.
    - Behavior 4: `_todays_rate_per_program(...)` invoked when cache is cold raises a ValueError (NOT NotImplementedError) with guidance to run `scripts/fred_cli.py get MORTGAGE30US --latest`.
    - Behavior 5: `_determine_programs(listing, household, profile)` returns `["Conv30", "Conv15", "FHA30"]` when profile.va_eligible=False AND listing.price below conforming limit for household.county.
    - Behavior 6: `_determine_programs(listing, household, profile)` returns `["Conv30", "Conv15", "FHA30", "VA30"]` when profile.va_eligible=True AND price below conforming.
    - Behavior 7: `_determine_programs(...)` returns `[..., "Jumbo30"]` (jumbo appended) when classify() returns "jumbo".
    - Behavior 8: `_determine_programs(...)` does NOT crash when classify() raises MissingCountyDataError — instead returns the base list and the calling layer surfaces a "MissingCountyDataError" warning into AnalysisReport.warnings (Open Question 4 resolution: graceful degradation).
    - Behavior 9: `_build_program_result(program="Conv30", dp_pct=Decimal("0.20"), listing, household, profile, annual_rate=Decimal("0.065"))` returns a ProgramResult with all numerics populated:
        - loan_amount = price × (1 − 0.20), quantized
        - monthly_pi computed via lib.amortize.build_schedule on a 360-month fixed Loan
        - monthly_mi = Decimal("0.00") at 20% DP (LTV = 0.80 exactly; NO PMI required per HPA)
        - piti = monthly_pi + monthly_tax + monthly_insurance + monthly_hoa + monthly_mi, quantized ONCE at end
        - dti_back = (piti + household.monthly_obligations) / household.monthly_income
        - ltv = loan_amount / price
        - eligible determined by lib.affordability.evaluate (delegated, not re-implemented)
    - Behavior 10: `_build_program_result(program="Conv30", dp_pct=Decimal("0.05"), ...)` returns a result with monthly_mi computed via `quantize_cents(loan_amount × _CONV_PMI_ANNUAL_RATE / 12)` since LTV = 0.95 > 0.80, and `eligible_reasons` contains the literal string "PMI-RATE-ESTIMATED-0.0075" (per Pitfall 1 + PATTERNS.md L533).
    - Behavior 11: `_build_program_result(program="FHA30", dp_pct=Decimal("0.035"))` (or 0.05) — UFMIP is computed via lib.rules.fha_mip.compute and FINANCED INTO principal per Phase 4 D-03; monthly_mi = quantize_cents(financed_principal × mip.annual_mip_pct / 12).
    - Behavior 12 (W-3 — REVISED): `_build_program_result(program="VA30", dp_pct=Decimal("0.00") or 0.05)` — funding_fee = lib.rules.va_funding_fee.compute(...); funding fee FINANCED INTO principal (mirrors Phase 4 D-03 financed-UFMIP convention); monthly_mi = Decimal("0.00") (absorbed by financed principal); eligible_reasons appends "VA-FUNDING-FEE-FINANCED".
    - Behavior 12b (B-2 — NEW): VA30 cells construct a valid `VAInputs(region="northeast", family_size=2, actual_residual_income=quantize_cents(household.monthly_income * Decimal("0.5")))` and pass it into the affordability request so `_validate_common` (lib/affordability.py L467-471) does NOT raise `ValueError("household.va block is required ...")`. eligible_reasons appends "VA-RESIDUAL-SYNTHESIZED-V1".
    - Behavior 13: When a cell would be blocked (e.g., DTI > 0.50 conventional), the ProgramResult has `eligible=False` BUT every numeric field (piti, dti_back, ltv) is still populated per D-14-MATRIX-02; `blocker_reasons` contains the lib.affordability.AffordabilityResponse.blocked_by string verbatim (per PATTERNS.md L437-442 "READ VERBATIM").
    - Behavior 14: `_build_matrix(listing, household, profile, todays_rates_dict)` returns a `DownPaymentMatrix` with exactly len(programs) × 6 cells (24 in default, 30 with jumbo), `programs_present` matches `_determine_programs` output, `down_payment_pcts` equals DOWN_PAYMENT_PCTS.
    - Behavior 15: A cell built via float input (e.g., dp_pct=0.20 not Decimal("0.20")) raises pydantic ValidationError at ProgramResult boundary — strict=True per CLAUDE.md money discipline.
    - Behavior 16 (B-4 — NEW): When a PropertyListing has `tax_annual=ProvenancedMoney(value=None, provenance="unknown")`, `_build_program_result` does NOT raise TypeError; monthly_tax falls back to Decimal("0.00") via `_unwrap_provenanced`. Same for hoa_monthly and insurance_estimate_annual.
  </behavior>
  <action>
    Extend `lib/property_analysis.py` (built in Task 1) with the following private helpers. Place each helper BEFORE the `analyze` stub at the end of the file.

    Add imports at the top of the file (extend existing import block):
    ```python
    from datetime import datetime, timezone
    from lib.amortize import build_schedule
    from lib.money import quantize_cents, quantize_rate
    from lib.models import Loan
    from lib.fred_cache import CACHE_DIR, get_cached_or_fetch, with_cache_lock
    from lib.rules.fha_mip import compute as fha_mip_compute
    from lib.rules.va_funding_fee import compute as va_funding_fee_compute
    from lib.rules.loan_type import classify as classify_loan_type, MissingCountyDataError
    from lib.rules.types import County
    from lib.affordability import (
        evaluate as affordability_evaluate,
        ForwardModeRequest,
        Household as AffordabilityHousehold,
        Applicant,
        LocationFIPS,
        MonthlyDebts,
        EscrowInputs,
        VAInputs,
    )
    from lib.household import Household
    from lib.profile import Profile
    ```
    (Note: `ProvenancedMoney` already imported in Task 1.)

    **Helper 0 (B-4 fix): `_unwrap_provenanced(pm: ProvenancedMoney | None, default: Decimal = Decimal("0.00")) -> Decimal`** — guarded unwrap helper, landed at the TOP of `lib/property_analysis.py` (immediately after the imports, before any other helper).

    ```python
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
    ```

    **Helper 1: `_todays_rate_per_program(program: str) -> Decimal`** — verbatim from RESEARCH.md L791-818 + PATTERNS.md L1005-1009. Use `with_cache_lock(CACHE_DIR, reason=f"property-analysis read {series_id}")`. Branch on program string to pick series_id and delta:
    - Conv15 → MORTGAGE15US, delta=0
    - Conv30-ARM-5-1 → MORTGAGE30US, delta=Decimal("-0.0025")
    - All others (Conv30, FHA30, VA30, Jumbo30) → MORTGAGE30US, delta=0
    Catch `NotImplementedError` from `get_cached_or_fetch(series_id, fetcher=None)` and re-raise as `ValueError(f"FRED cache cold for {series_id}; run scripts/fred_cli.py get {series_id} --latest to refresh")`. Return `quantize_rate(Decimal(str(entry["value"])) + delta)`.

    **Helper 2: `_determine_programs(listing: PropertyListing, household: Household, profile: Profile) -> tuple[list[str], list[str]]`** — returns (programs, warnings). Per RESEARCH.md L843-879:
    ```
    programs = list(PROGRAMS_BASE)
    warnings = []
    if profile.va_eligible:
        programs.append("VA30")
    county = County(state_fips=household.state_fips, county_fips=household.county_fips, name=household.county_name)
    try:
        classification = classify_loan_type(quantize_cents(listing.price), county, program="conventional")
        if classification == "jumbo":
            programs.append("Jumbo30")
    except MissingCountyDataError:
        warnings.append("MissingCountyDataError")
    return programs, warnings
    ```

    **Helper 3: `_compute_cash_to_close(loan_amount: Decimal, down_payment: Decimal, ufmip_not_financed: Decimal = Decimal("0")) -> Decimal`** — returns `quantize_cents(down_payment + loan_amount * _CLOSING_COSTS_PCT + ufmip_not_financed)`. Document closing_costs_estimated=True via Assumption A7.

    **Helper 4 (REVISED for B-2, B-4, W-3): `_build_program_result(program: str, dp_pct: Decimal, listing: PropertyListing, household: Household, profile: Profile, annual_rate: Decimal) -> ProgramResult`** — the core per-cell engine. Mirrors `evaluate_forward` from lib/affordability.py L805-949 + Code Example 2 from RESEARCH.md L741-783.

    Step-by-step body (DO NOT inline-implement amortize/MIP/funding-fee; delegate to existing predicates):

    1. Quantize price + down_payment: `price = quantize_cents(listing.price)`; `down_payment = quantize_cents(price * dp_pct)`; `base_loan_amount = quantize_cents(price - down_payment)`.
    2. Determine term_months: Conv15 → 180, all others → 360 (use DEFAULT_CONFORMING_TERM_MONTHS / DEFAULT_CONFORMING_15_TERM_MONTHS constants).
    3. Initialize per-cell sentinels: `eligible_reasons: list[str] = []`.
    4. Determine loan_type string + compute MI per program:
       - **Conv30 / Conv15 / Jumbo30:** `loan_type="fixed"`. Compute `provisional_ltv = base_loan_amount / price`. If `provisional_ltv > Decimal("0.80")`: `monthly_mi = quantize_cents(base_loan_amount * _CONV_PMI_ANNUAL_RATE / Decimal("12"))` and append `"PMI-RATE-ESTIMATED-0.0075"` to `eligible_reasons`. Else: `monthly_mi = Decimal("0.00")`. `financed_principal = base_loan_amount`.
       - **FHA30:** `loan_type="fha"`. Call `mip = fha_mip_compute(Loan(principal=base_loan_amount, annual_rate=annual_rate, term_months=360, loan_type="fha"), original_property_value=price, endorsement_date=datetime.now(timezone.utc).date())`. `financed_principal = quantize_cents(base_loan_amount + mip.ufmip)`. `monthly_mi = quantize_cents(financed_principal * mip.annual_mip_pct / Decimal("12"))`.
       - **VA30 (W-3 REVISED):** `loan_type="va"`. Call `funding_fee = va_funding_fee_compute(loan_amount=base_loan_amount, down_payment_pct=dp_pct, is_first_use=True, loan_purpose="purchase", is_exempt_from_funding_fee=False)`. `financed_principal = quantize_cents(base_loan_amount + funding_fee)`. `monthly_mi = Decimal("0.00")` (funding fee is absorbed by financed principal; the amortization captures it through higher monthly_pi). Append `"VA-FUNDING-FEE-FINANCED"` to `eligible_reasons`. Document policy: VA funding fee, like FHA UFMIP (Phase 4 D-03), is financed into principal — NOT amortized as a straight-line monthly_mi.
    5. Compute monthly_pi: `loan = Loan(principal=financed_principal, annual_rate=annual_rate, term_months=term_months, loan_type=loan_type)`; `schedule = build_schedule(loan, frequency="monthly")`; `monthly_pi = schedule.monthly_pi`.
    6. Compute escrow components (B-4 — REVISED, use `_unwrap_provenanced` helper, NOT inline guards):
       ```python
       monthly_tax = quantize_cents(_unwrap_provenanced(listing.tax_annual) / Decimal("12"))
       monthly_insurance = quantize_cents(_unwrap_provenanced(listing.insurance_estimate_annual) / Decimal("12"))
       monthly_hoa = quantize_cents(_unwrap_provenanced(listing.hoa_monthly))
       ```
       This guards both `listing.tax_annual is None` AND `listing.tax_annual.value is None` (legitimate Phase 13 gap-fill state).
    7. Compute PITI exactly ONCE at end (Pitfall 6 + PATTERNS.md L223-232):
       `piti_pre = monthly_pi + monthly_tax + monthly_insurance + monthly_hoa + monthly_mi`
       `piti = quantize_cents(piti_pre)`
    8. Compute DTI back-end: `dti_back = quantize_rate((piti + household.monthly_obligations) / household.monthly_income)`.
    9. Compute LTV: `ltv = quantize_rate(financed_principal / price)`.
    10. Compute cash_to_close: `_compute_cash_to_close(base_loan_amount, down_payment, ufmip_not_financed=Decimal("0"))` (FHA UFMIP is financed per Phase 4 D-03; VA funding fee likewise; pass 0 for v1.1).
    11. **Build the affordability request (B-2 — REVISED — VA-aware):**

        Map target_loan_type:
        - Conv30, Conv15 → `"conventional"`
        - Jumbo30 → `"jumbo"`
        - FHA30 → `"fha"`
        - VA30 → `"va"`

        Construct the affordability `Household` (note: this is `AffordabilityHousehold` per the import alias to avoid shadowing the Phase 14 Household — see Plan 14-01 OQ #1 resolution). Build a single Applicant aggregating `gross_monthly_income=household.monthly_income`; pass safe defaults for other applicant fields. MonthlyDebts: place all of `household.monthly_obligations` in the `"other"` bucket (PATTERNS-acknowledged collapse — see W-5 note in 14-PLAN-CHECK.md). LocationFIPS from household.state_fips/county_fips/county_name (state="" placeholder — affordability accepts blank state since LocationFIPS only requires fips for predicate routing). EscrowInputs from the per-cell `monthly_tax`/`monthly_insurance`/`monthly_hoa`.

        **VA branch (B-2 fix):** When `program == "VA30"`, construct:
        ```python
        va_inputs = VAInputs(
            region="northeast",  # Region literal from lib/rules/types.py (Literal["northeast","midwest","south","west"])
            family_size=2,
            actual_residual_income=quantize_cents(household.monthly_income * Decimal("0.5")),
        )
        ```
        Pass `va_inputs` into the AffordabilityHousehold's `va` field (per `lib/affordability.py` L407-433 — AffordabilityHousehold carries an optional `va: VAInputs | None`). For non-VA programs, set `va=None`.

        Rationale for synthesis values:
        - `region="northeast"`: deterministic choice; M26-7 regional residual differences are within ±$200 of average; choosing one keeps the request constructible without surfacing region on Profile in v1.1.
        - `family_size=2`: median household-of-2 maps to a known column in the M26-7 table.
        - `actual_residual_income = monthly_income * 0.5`: 50% of monthly income comfortably exceeds the highest M26-7 minimum residual (~$1,158 for family_size=5, West, loan ≥ $80k) for any monthly_income ≥ $2,400; this ensures the VA-RESIDUAL predicate does NOT block on synthetic residual, which would distort matrix eligibility shape.

        Tradeoff (LOUDLY documented in module docstring + via `eligible_reasons += ["VA-RESIDUAL-SYNTHESIZED-V1"]`): real VA residual income depends on actual region + family_size + actual obligations from VA M26-7 tables; this synthesis is conservative but NOT exact. A follow-on phase may extend Profile with `va_region: Region | None` etc. if user-facing VA-residual accuracy becomes a requirement.

    12. Construct `ForwardModeRequest` with the affordability inputs above; set `monthly_pmi=monthly_mi` when `target_loan_type=="conventional"` AND LTV>0.80 (per Phase 4 RESEARCH Open Q#1 — monthly_pmi REQUIRED for Conv > 80 LTV; otherwise `_validate_common` raises). For other programs set `monthly_pmi=None`.

    13. Call `response = affordability_evaluate(forward_request)`. If `response.blocked`: `eligible=False; blocker_reasons=[response.blocked_by]` (read VERBATIM per PATTERNS.md L437-442). Else: `eligible=True; blocker_reasons=[]`.

    14. Return `ProgramResult(..., eligible_reasons=eligible_reasons, blocker_reasons=blocker_reasons, ...)` with all numerics populated regardless of eligibility (D-14-MATRIX-02).

    **Helper 5: `_build_matrix(listing, household, profile, todays_rates: dict[str, Decimal]) -> tuple[DownPaymentMatrix, list[str]]`** — returns (matrix, warnings):
    ```
    programs, warnings = _determine_programs(listing, household, profile)
    cells = []
    for program in programs:
        rate = todays_rates[program]
        for dp_pct in DOWN_PAYMENT_PCTS:
            cells.append(_build_program_result(program, dp_pct, listing, household, profile, rate))
    matrix = DownPaymentMatrix(cells=cells, programs_present=programs, down_payment_pcts=DOWN_PAYMENT_PCTS)
    return matrix, warnings
    ```

    DO NOT implement stress/refi/points/tax blocks here — those land in Plan 14-03.
    DO NOT implement verdict synthesis here — that lands in Plan 14-04.
    DO NOT implement the top-level `analyze()` body here — that lands in Plan 14-05 (after this task, `analyze()` still raises NotImplementedError).
    DO catch float-input ValidationErrors loudly (let them propagate) — float contamination is Pitfall 2 and must be caught at the model boundary, never silently coerced.
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py -x -k "not stress and not refi and not points and not tax and not verdict and not analyze and not golden"</automated>
  </verify>
  <acceptance_criteria>
    - `lib/property_analysis.py` contains `def _todays_rate_per_program(`, `def _determine_programs(`, `def _build_program_result(`, `def _build_matrix(`, `def _compute_cash_to_close(`, `def _unwrap_provenanced(`.
    - `grep -c '_unwrap_provenanced' lib/property_analysis.py` returns at least 4 (1 def + 3 uses: tax_annual, insurance_estimate_annual, hoa_monthly) (B-4 fix).
    - `grep -c 'with_cache_lock(CACHE_DIR' lib/property_analysis.py` returns at least 1 (FRED reads serialized per Pitfall 9).
    - `grep -c 'County(state_fips=household.state_fips' lib/property_analysis.py` returns at least 1 (Pitfall 5 — County from Household, not zip).
    - `grep -c 'MissingCountyDataError' lib/property_analysis.py` returns at least 1 (graceful handling).
    - `grep -c 'piti_pre = monthly_pi + monthly_tax + monthly_insurance + monthly_hoa + monthly_mi' lib/property_analysis.py` returns 1 (Pitfall 6 — MI in PITI).
    - `grep -c 'piti = quantize_cents(piti_pre)' lib/property_analysis.py` returns 1 (quantize ONCE at end).
    - `grep -c 'fha_mip_compute(' lib/property_analysis.py` returns at least 1.
    - `grep -c 'va_funding_fee_compute(' lib/property_analysis.py` returns at least 1.
    - `grep -c 'affordability_evaluate(' lib/property_analysis.py` returns at least 1.
    - `grep -c '_CONV_PMI_ANNUAL_RATE' lib/property_analysis.py` returns at least 2 (one in constant declaration, one in use).
    - `grep -c 'VA-RESIDUAL-SYNTHESIZED-V1' lib/property_analysis.py` returns at least 1 (B-2 fix marker).
    - `grep -c 'VA-FUNDING-FEE-FINANCED' lib/property_analysis.py` returns at least 1 (W-3 fix marker).
    - `grep -c 'VAInputs(' lib/property_analysis.py` returns at least 1 (B-2 — VAInputs is constructed for VA cells).
    - `grep -c 'region="northeast"' lib/property_analysis.py` returns at least 1 (B-2 — explicit synthesis policy).
    - `grep -c 'monthly_income \* Decimal("0.5")' lib/property_analysis.py` returns at least 1 (B-2 — residual synthesis formula).
    - The unit tests below pass: `pytest tests/test_property_analysis.py::test_dp_sweep_uses_decimal_strings tests/test_property_analysis.py::test_matrix_cell_count tests/test_property_analysis.py::test_va_eligibility_gates_program tests/test_property_analysis.py::test_missing_county_graceful tests/test_property_analysis.py::test_ineligible_rows_populate_numerics tests/test_property_analysis.py::test_float_rejection tests/test_property_analysis.py::test_fred_lock_serialization tests/test_property_analysis.py::test_va_cell_constructs_valid_affordability_request tests/test_property_analysis.py::test_provenanced_value_none_unwraps_to_zero -x` exits 0.
  </acceptance_criteria>
  <done>
    Per-cell composition engine fully functional. Matrix builder produces 24 or 30 cells per D-14-MATRIX-01/03. Eligibility delegated to lib.affordability. VA cells construct valid VAInputs (B-2). PropertyListing escrow unwrap goes through guarded helper (B-4). VA funding fee financed into principal (W-3). Verified by the unit tests called out in acceptance criteria.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create tests/test_property_analysis.py (matrix/cell ANLZ-01 + ANLZ-02 surface) + extend tests/conftest.py with property_analysis_fixture</name>
  <files>tests/test_property_analysis.py, tests/conftest.py</files>
  <read_first>
    - tests/conftest.py (full — pattern for property_analysis_fixture loader; affordability_fixture L57-72 as analog)
    - tests/test_affordability.py L1-200 (test header style + helper builders _make_clean_household etc.)
    - tests/test_affordability.py L800-1000 (fixture-driven assertion pattern + verbatim blocked_by reads)
    - tests/test_stress.py L1-100 + L528-567 (fixture-driven test entrypoint + SC-5 size-budget pattern)
    - tests/test_property_listing.py L1-191 (model-contract testing style — _valid_listing builder includes source_url, zpid, fetched_at)
    - lib/property_analysis.py (Tasks 1 + 2 output)
    - lib/property_listing.py L44-105 (REQUIRED fields: source_url, zpid, fetched_at — B-3)
    - lib/household.py
    - lib/profile.py
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L1095-1218 (Phase Requirements → Test Map; the named tests required)
    - .planning/phases/14-property-analysis-pipeline/14-VALIDATION.md (test catalog rows 43-65; this plan owns rows for ANLZ-01/ANLZ-02/composition)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L504-590 (test_property_analysis.py patterns including fixture-loader call pattern)
  </read_first>
  <behavior>
    The test file must contain these named tests (each one named exactly per VALIDATION.md and RESEARCH.md L1095-1119). Tests in this plan cover ONLY matrix-shape, cell-numeric, eligibility-gating, and basic composition invariants. Stress/refi/points/tax/verdict tests are deferred to later plans.

    Wave-0 (must pass after Task 1 only):
    - `test_models_importable` — All output models + module constants importable.
    - `test_module_constants` — DOWN_PAYMENT_PCTS / PROGRAMS_BASE / _CONV_PMI_ANNUAL_RATE / _CONV_5_1_ARM_TERMS values exact (per Behavior list in Task 1).

    Wave 1 (must pass after Task 2):
    - `test_matrix_cell_count` — A matrix from a non-jumbo synthetic listing has exactly 18 cells (3 programs × 6 DPs, profile.va_eligible=False); jumbo case has 24 cells (4 × 6 incl. Jumbo30) or 30 (5 × 6 with VA + Jumbo).
    - `test_matrix_fanout_conforming` — Verify Conv30 / Conv15 / FHA30 all present in programs_present; verify each program contributes exactly 6 cells.
    - `test_va_eligibility_gates_program` — Profile(va_eligible=False) → "VA30" NOT in matrix.programs_present; Profile(va_eligible=True) → "VA30" IS in matrix.programs_present.
    - `test_jumbo_trigger_at_county_limit` — When listing.price > conforming limit for King County WA (use $1,500,000 to safely exceed baseline $832,750), "Jumbo30" appears in programs_present.
    - `test_missing_county_graceful` — _determine_programs with a county not in the conforming-limits YAML AND a listing.price > baseline returns the base programs + warnings=["MissingCountyDataError"]; no exception escapes.
    - `test_ineligible_rows_populate_numerics` — Construct a household with monthly_income=Decimal("3000.00") + a Conv30 cell at 3% DP on a $1M listing. Assert: result.eligible=False BUT result.piti > 0 AND result.dti_back > 0 AND result.ltv > 0 (per D-14-MATRIX-02).
    - `test_dp_sweep_uses_decimal_strings` — Inspect matrix.cells; assert every cell's down_payment_pct is a Decimal (not float) and matches one of DOWN_PAYMENT_PCTS exactly (Pitfall 2).
    - `test_mi_included_in_piti` — Construct a Conv30 cell at 5% DP (LTV=0.95 > 0.80); assert cell.piti == quantize_cents(cell.monthly_pi + cell.monthly_tax + cell.monthly_insurance + cell.monthly_hoa + cell.monthly_mi) AND cell.monthly_mi > 0 (Pitfall 6).
    - `test_fha_cell_ufmip_financed_into_principal` — Construct an FHA30 cell at 3.5% DP on a $400k listing. Assert cell.loan_amount > price * 0.965 (because UFMIP is added to base loan per Phase 4 D-03 + Code Example 2).
    - `test_conv_pmi_warning_surfaces` — Conv30 cell at 5% DP populates `eligible_reasons` with string containing "PMI-RATE-ESTIMATED-0.0075" (Pitfall 1).
    - `test_float_rejection` — Constructing ProgramResult with a Python float for any Money/Rate field raises ValidationError (strict=True; Pitfall 2).
    - `test_blocker_reason_verbatim` — When a cell is blocked due to DTI, blocker_reasons[0] is the exact string returned by lib.affordability.AffordabilityResponse.blocked_by (e.g., "DTI-CAP-CONVENTIONAL") — verbatim, no reformatting (PATTERNS.md L437-442).
    - `test_fred_lock_serialization` — _todays_rate_per_program invoked twice in a single test does NOT crash; with_cache_lock is invoked (mock or spy on lib.fred_cache.with_cache_lock; assert called with reason containing "property-analysis read").
    - `test_fred_cold_cache_raises_valueerror_with_guidance` — Patch lib.fred_cache.get_cached_or_fetch to raise NotImplementedError; assert _todays_rate_per_program raises ValueError with message containing "scripts/fred_cli.py".
    - `test_va_cell_constructs_valid_affordability_request` (B-2 NEW) — Construct a Profile(va_eligible=True), build a VA30 cell at ANY DP via `_build_program_result(program="VA30", dp_pct=Decimal("0.05"), ...)`. Assert: no `ValueError("household.va block is required when target_loan_type=='va'")` is raised; `cell.eligible_reasons` contains both `"VA-RESIDUAL-SYNTHESIZED-V1"` and `"VA-FUNDING-FEE-FINANCED"`.
    - `test_provenanced_value_none_unwraps_to_zero` (B-4 NEW) — Construct a PropertyListing with `tax_annual=ProvenancedMoney(value=None, provenance="unknown")`, `hoa_monthly=None`, `insurance_estimate_annual=ProvenancedMoney(value=None, provenance="unknown")`. Call `_build_program_result(program="Conv30", dp_pct=Decimal("0.20"), ...)`. Assert: no TypeError; `cell.monthly_tax == Decimal("0.00")` AND `cell.monthly_hoa == Decimal("0.00")` AND `cell.monthly_insurance == Decimal("0.00")`.

    Wave 2+ tests (will appear in later plans; STUB them as `pytest.skip("Plan 14-XX")` so the test file is shape-stable and `pytest --collect-only` shows them up-front):
    - `test_stress_at_preferred_dp_only` (skip → Plan 14-03)
    - `test_arm_reset_conv30_only` (skip → Plan 14-03)
    - `test_refi_two_scenarios_per_program` (skip → Plan 14-03)
    - `test_points_breakeven_per_program` (skip → Plan 14-03)
    - `test_tax_block_pub936` (skip → Plan 14-03)
    - `test_report_size_budget` (skip → Plan 14-06)
    - `test_sfh_conforming_king_county_golden` (skip → Plan 14-06)
    - `test_condo_with_hoa_seattle_golden` (skip → Plan 14-06)
    - `test_sfh_jumbo_bay_area_golden` (skip → Plan 14-06)
  </behavior>
  <action>
    Create `tests/test_property_analysis.py`. Verbatim module header style from tests/test_affordability.py L1-67. Required structure:

    1. Module docstring naming Phase 14 + the covered requirements (ANLZ-01, ANLZ-02, composition invariants; Wave 1 of the test surface).
    2. `from __future__ import annotations` first line.
    3. Imports: `pytest`, `Decimal`, `datetime, timezone` from `datetime`, `ValidationError` from pydantic, `MagicMock, patch` from unittest.mock if used for FRED testing. Import from `lib.property_analysis`: `ProgramResult, DownPaymentMatrix, DOWN_PAYMENT_PCTS, PROGRAMS_BASE, _CONV_PMI_ANNUAL_RATE, _CONV_5_1_ARM_TERMS, _build_program_result, _build_matrix, _determine_programs, _todays_rate_per_program, _unwrap_provenanced`. Import `Household` from `lib.household`, `Profile` from `lib.profile`, `PropertyListing` + `ProvenancedMoney` from `lib.property_listing`.

    4. Helper builders (mirror tests/test_affordability.py L136-167 + tests/test_property_listing.py L30-46):
       - `_make_clean_household(**overrides) -> Household` — returns a Household with sensible defaults (monthly_income="12000.00", monthly_obligations="400.00", fico=740, liquid_reserves="100000.00", state_fips="53", county_fips="033", county_name="King", preferred_down_payment_pct=Decimal("0.20")). Overrides override.
       - `_make_clean_profile(**overrides) -> Profile` — returns Profile() with overrides.
       - `_make_clean_listing(...)` — REVISED per B-3 to default the Phase-13 required audit fields:

         ```python
         def _make_clean_listing(
             price: str = "625000.00",
             zip: str = "98101",
             property_type: str = "SFH",
             source_url: str = "https://www.zillow.com/homedetails/synthetic/1_zpid/",
             zpid: str = "1",
             fetched_at: datetime = datetime(2026, 5, 17, tzinfo=timezone.utc),
             **provenanced_overrides,
         ) -> PropertyListing:
             """Build a Phase-13-valid PropertyListing for use in Phase-14 tests.

             B-3 fix: source_url / zpid / fetched_at are REQUIRED per
             lib/property_listing.py L84-86. Defaulted here so callers don't
             have to enumerate them.

             provenanced_overrides routes to NICE-TO-HAVE money fields (e.g.,
             tax_annual=ProvenancedMoney(value=..., provenance="estimated")).
             """
             return PropertyListing(
                 price=Decimal(price),
                 zip=zip,
                 property_type=property_type,
                 source_url=source_url,
                 zpid=zpid,
                 fetched_at=fetched_at,
                 **provenanced_overrides,
             )
         ```

       - `_make_jumbo_listing()` returns `_make_clean_listing(price="1500000.00")` (above 2026 King County conforming; inherits the B-3 audit-field defaults).

    5. Write each named test from the Behavior list above. Patterns to follow:
       - Use `pytest.raises(ValidationError)` for negative cases (float rejection, extra-forbid).
       - Use exact `==` (CLAUDE.md), never `pytest.approx`.
       - Patch FRED cache reads via `monkeypatch.setattr(lib.property_analysis, "get_cached_or_fetch", ...)` or fixture-injection — DO NOT make real FRED calls in tests.
       - For tests that depend on lib.property_analysis._build_program_result, inject `annual_rate=Decimal("0.065000")` directly (avoid the FRED dependency in unit tests).
       - For `test_fred_lock_serialization`: use `unittest.mock.patch("lib.property_analysis.with_cache_lock")` to spy on the lock acquisition.
       - For Wave-2+ tests: declare them at module bottom; each body is `pytest.skip("Plan 14-XX: <reason>")` so the test name surfaces in `pytest --collect-only`.

    6. **Extend tests/conftest.py** (append; DO NOT replace existing fixtures):
       Add at the bottom of tests/conftest.py:
       ```python
       @pytest.fixture
       def property_analysis_fixture() -> Callable[[str], dict[str, Any]]:
           """Return a callable that loads a single property-analysis fixture by filename
           stem from tests/fixtures/property_analysis/. Mirrors affordability_fixture
           pattern (one-fixture-per-file; stem-based loading).
           Per Plan 14-02 PATTERNS.md L760-775."""

           def _load(stem: str) -> dict[str, Any]:
               path = FIXTURE_DIR / "property_analysis" / f"{stem}.json"
               return json.loads(path.read_text())  # type: ignore[no-any-return]

           return _load
       ```
       The `property_analysis_fixture` returns a loader; actual fixtures are CREATED in Plan 14-06.

    DO NOT add test_property_verdict.py here — that's Plan 14-04.
    DO NOT create fixture JSON files here — those are Plan 14-06.
    DO NOT implement Wave 2+ tests bodies — stub them with pytest.skip().
    DO NOT use `pytest.approx` or `assertAlmostEqual` for any numeric assertion — exact Decimal equality only.
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py -x -k "not stress and not refi and not points and not tax and not verdict and not golden and not report_size_budget"</automated>
  </verify>
  <acceptance_criteria>
    - `tests/test_property_analysis.py` exists.
    - `tests/conftest.py` contains `def property_analysis_fixture(` (grep returns 1 match).
    - `grep -c '^def test_' tests/test_property_analysis.py` returns at least 24 (14 Wave-1 incl. 2 new B-2/B-4 tests + at least 10 stubs).
    - `_make_clean_listing` defaults the 3 Phase-13 required fields (B-3): `grep -c 'source_url' tests/test_property_analysis.py` returns at least 1; `grep -c 'zpid' tests/test_property_analysis.py` returns at least 1; `grep -c 'fetched_at' tests/test_property_analysis.py` returns at least 1.
    - All Wave-1 named tests pass when invoked individually:
      `pytest tests/test_property_analysis.py::test_models_importable tests/test_property_analysis.py::test_module_constants tests/test_property_analysis.py::test_matrix_cell_count tests/test_property_analysis.py::test_matrix_fanout_conforming tests/test_property_analysis.py::test_va_eligibility_gates_program tests/test_property_analysis.py::test_jumbo_trigger_at_county_limit tests/test_property_analysis.py::test_missing_county_graceful tests/test_property_analysis.py::test_ineligible_rows_populate_numerics tests/test_property_analysis.py::test_dp_sweep_uses_decimal_strings tests/test_property_analysis.py::test_mi_included_in_piti tests/test_property_analysis.py::test_fha_cell_ufmip_financed_into_principal tests/test_property_analysis.py::test_conv_pmi_warning_surfaces tests/test_property_analysis.py::test_float_rejection tests/test_property_analysis.py::test_blocker_reason_verbatim tests/test_property_analysis.py::test_fred_lock_serialization tests/test_property_analysis.py::test_fred_cold_cache_raises_valueerror_with_guidance tests/test_property_analysis.py::test_va_cell_constructs_valid_affordability_request tests/test_property_analysis.py::test_provenanced_value_none_unwraps_to_zero -x` exits 0.
    - Wave-2+ tests are collected but SKIPPED: `pytest tests/test_property_analysis.py --collect-only -q | grep -c 'test_stress_at_preferred_dp_only\\|test_arm_reset_conv30_only\\|test_refi_two_scenarios_per_program\\|test_points_breakeven_per_program\\|test_tax_block_pub936\\|test_report_size_budget\\|test_sfh_conforming_king_county_golden\\|test_condo_with_hoa_seattle_golden\\|test_sfh_jumbo_bay_area_golden'` returns 9.
    - `grep -E 'assertAlmostEqual|pytest\.approx' tests/test_property_analysis.py | grep -v '^#' | wc -l` returns 0 (no fuzzy comparators).
    - `pytest -x` (full suite) exits 0 — no regression in other phases.
  </acceptance_criteria>
  <done>
    `pytest tests/test_property_analysis.py -x -k "not stress and not refi and not points and not tax and not verdict and not golden and not report_size_budget"` exits 0; Wave-1 test surface for ANLZ-01 + ANLZ-02 + composition invariants (including B-2 VA-construction + B-4 ProvenancedMoney unwrap) fully green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase 14 lib → FRED cache file | `data/cache/fred_*.json` is shared mutable state; cross-process race possible. Mitigated by `with_cache_lock`. |
| Phase 14 lib → reference YAMLs (conforming-limits-2026.yml, fha-mip-rates.yml, va-funding-fees.yml) | Phase 14 reads via existing predicates (lib.rules.{loan_type, fha_mip, va_funding_fee}); staleness check is inherited from `lib.rules._loader._check_staleness`. |
| User-provided Household/Profile/PropertyListing → ProgramResult | All inputs are Pydantic strict/frozen/extra=forbid; ValidationError on boundary. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-FLOAT | Tampering | ProgramResult, DownPaymentMatrix, all Money/Rate fields | mitigate | `strict=True` on every Money/Rate field; `test_float_rejection` proves rejection; DOWN_PAYMENT_PCTS constructed from strings only (Pitfall 2). |
| T-14-FRED-RACE | Tampering | `_todays_rate_per_program` → `lib.fred_cache.with_cache_lock` | mitigate | Every FRED read wrapped in `with_cache_lock(CACHE_DIR, reason="property-analysis read {series_id}")` per Pitfall 9; `test_fred_lock_serialization` verifies invocation. |
| T-14-STALE-REF | Tampering | conforming-limits-2026.yml, fha-mip-rates.yml, va-funding-fees.yml reads (transitively via lib.rules) | mitigate | Phase 14 reads through existing predicates; `lib.rules._loader._check_staleness` raises StaleReferenceWarning automatically. Phase 14 surfaces warnings via AnalysisReport.warnings (assembled in Plan 14-05). |
| T-14-REASON | Repudiation | n/a in this plan | accept | VerdictReason construction lives in Plan 14-04. |
| T-14-PII | Information Disclosure | tests/test_property_analysis.py | mitigate | Tests use synthetic addresses/fips; no real Zillow data referenced. |
</threat_model>

<verification>
- `pytest tests/test_property_analysis.py -x -k "not stress and not refi and not points and not tax and not verdict and not golden and not report_size_budget"` exits 0.
- `pytest -x` (full suite) exits 0 — no regression.
- `python -c "from lib.property_analysis import analyze; analyze()"` raises NotImplementedError mentioning Plan 14-05 (placeholder still in place).
- `python -c "from lib.property_analysis import _build_matrix, _determine_programs, _build_program_result, _todays_rate_per_program, _unwrap_provenanced"` succeeds (helpers exported / accessible).
- File sizes within budget: `wc -l lib/property_analysis.py` returns < 650 lines (added _unwrap_provenanced + VA-input synthesis); `wc -l tests/test_property_analysis.py` returns < 750 lines (Wave-1 + stubs + 2 new B-2/B-4 tests).
</verification>

<success_criteria>
1. lib/property_analysis.py ships all 12 Pydantic models + 5 module constants + 6 private helpers (_unwrap_provenanced, _todays_rate_per_program, _determine_programs, _compute_cash_to_close, _build_program_result, _build_matrix).
2. Per-cell composition correctly delegates to lib.amortize, lib.rules.fha_mip, lib.rules.va_funding_fee, lib.rules.loan_type, lib.affordability — NO inline regulatory math.
3. PMI rate sourcing uses _CONV_PMI_ANNUAL_RATE constant; cells with LTV>0.80 carry "PMI-RATE-ESTIMATED-0.0075" in eligible_reasons (Pitfall 1).
4. Conforming-limit lookup uses County(state_fips, county_fips, county_name) from Household — never zip (Pitfall 5).
5. FRED reads wrapped in with_cache_lock (Pitfall 9).
6. PITI composition includes monthly_mi; quantize_cents called exactly ONCE at end (Pitfall 6 + Phase 3 D-04).
7. Signed Decimals (RefiRow.monthly_savings, RefiRow.npv_60mo) use raw Decimal, NOT Money alias (Pitfall 3).
8. **B-2 RESOLVED:** VA cells synthesize VAInputs(region="northeast", family_size=2, actual_residual_income=monthly_income*0.5) and tag eligible_reasons with "VA-RESIDUAL-SYNTHESIZED-V1"; `test_va_cell_constructs_valid_affordability_request` proves no `household.va block is required` error.
9. **B-3 RESOLVED:** `_make_clean_listing` defaults source_url, zpid, fetched_at; PropertyListing construction succeeds.
10. **B-4 RESOLVED:** `_unwrap_provenanced` helper guards both `pm is None` AND `pm.value is None`; `test_provenanced_value_none_unwraps_to_zero` proves no TypeError.
11. **W-3 RESOLVED:** VA funding fee financed into principal; monthly_mi=0 for VA; eligible_reasons += "VA-FUNDING-FEE-FINANCED".
12. All Wave-1 unit tests pass (16 base + 2 new B-2/B-4); 9 Wave-2+ tests are stubbed with pytest.skip.
13. tests/conftest.py has the property_analysis_fixture loader appended.
14. ANLZ-01 + ANLZ-02 closed (matrix shape + cell count + program fan-out + jumbo trigger + ineligible-row numeric population all verified).
</success_criteria>

<output>
After completion, create `.planning/phases/14-property-analysis-pipeline/14-02-SUMMARY.md` documenting:
- All 12 Pydantic models shipped (with exact field order in AnalysisReport).
- All 5 module constants (DOWN_PAYMENT_PCTS, PROGRAMS_BASE, _CONV_PMI_ANNUAL_RATE, _CONV_5_1_ARM_TERMS, _CLOSING_COSTS_PCT) with values.
- All 6 private helpers (_unwrap_provenanced, _todays_rate_per_program, _determine_programs, _compute_cash_to_close, _build_program_result, _build_matrix) with signatures.
- Iteration-2 fix summary: B-2 (VA-synthesis), B-3 (PropertyListing defaults in helper), B-4 (_unwrap_provenanced), W-3 (VA funding-fee financed).
- Test counts: 18 Wave-1 tests passing (16 base + 2 new); 9 Wave-2+ tests stubbed.
- Pitfalls mitigated in this plan: 1 (PMI estimate constant), 2 (Decimal-from-strings), 3 (signed Decimal not Money), 4 (delegate to predicates), 5 (County from Household), 6 (MI in PITI; quantize ONCE), 9 (with_cache_lock), 10 (no Schedule.payments on ProgramResult).
- Requirements closed: ANLZ-01, ANLZ-02.
- Interfaces consumed by downstream plans: ProgramResult, DownPaymentMatrix, _build_program_result, _build_matrix, _todays_rate_per_program, _unwrap_provenanced, _CONV_5_1_ARM_TERMS, DOWN_PAYMENT_PCTS, AnalysisReport (frozen schema).
- Note on Phase 14 Household / Affordability Household disambiguation: `from lib.affordability import Household as AffordabilityHousehold` (per Plan 14-01 OQ #1 resolution).
</output>
