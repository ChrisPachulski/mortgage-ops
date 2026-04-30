---
phase: 04-affordability
plan: 04
type: execute
wave: 4
depends_on: ["04-00", "04-01", "04-02", "04-03"]
files_modified:
  - lib/affordability.py
autonomous: true
requirements: [AFFD-07]
requirements_addressed: [AFFD-07]
tags: [phase-4, affordability, blockers, precedence, citations, wave-4]

must_haves:
  truths:
    - "Blocker precedence (D-11): loan-type-classify (already wired in 04-02/04-03) → USDA-income (when target=='usda'; RESEARCH Open Q#4) → LTV/CLTV ceiling → DTI cap → ATR/QM (when first-lien residential AND apr+apor present; advisory if missing) → VA-residual (when target=='va')"
    - "Single blocked_by string + warnings: list[str] response shape (D-11)"
    - "First hard-fail wins (short-circuit precedence) — subsequent fails go to warnings or are skipped"
    - "VA-residual citation read VERBATIM from result.binding_rule_citation (Phase 2 D-11; STABLE format VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}; format-drift = contract violation)"
    - "USDA branch reads household_size DIRECTLY from request.household.size — the BLOCKER 2 required field added in Plan 04-01; NEVER infers from len(applicants) or va.family_size (CLAUDE.md + CONTEXT.md fail-loud, no inference)"
    - "Citation string formats (planner-finalized — pinned by tests in Plan 04-06):"
    - "  - FHFA-LIMIT-CONFORMING-{state_fips}-{county_fips} / FHFA-LIMIT-JUMBO-{state_fips}-{county_fips} (already wired in 04-02 helper)"
    - "  - HUD-LIMIT-FHA-{state_fips}-{county_fips} (target=fha mismatch)"
    - "  - VA-LIMIT-{state_fips}-{county_fips} (target=va mismatch)"
    - "  - USDA-LIMIT-{state_fips}-{county_fips} (target=usda mismatch)"
    - "  - USDA-INCOME-LIMIT-{state_fips}-{county_fips} (when usda.income_eligible == False; RESEARCH Open Q#4)"
    - "  - LTV-CEILING-{LOAN_TYPE_UPPER} (e.g., LTV-CEILING-CONVENTIONAL, LTV-CEILING-FHA)"
    - "  - CLTV-CEILING-{LOAN_TYPE_UPPER}"
    - "  - DTI-CAP-{LOAN_TYPE_UPPER} (e.g., DTI-CAP-FHA)"
    - "  - ATR-QM-PRICE-FIRST (Phase 2 RUL-09 stable citation; advisory if apr/apor missing)"
    - "  - VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N} (verbatim from predicate; ROADMAP SC-3 example)"
    - "Soft warnings: HPA-PMI-REQUIRED, FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}, FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}, ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR"
    - "Per-loan-type LTV ceilings (RESEARCH §'LTV / CLTV Ceiling Authority'): conventional 0.97, jumbo 1.00 (no enforcement v1), fha 0.965, va 1.00, usda 1.00"
    - "Block citation strings exposed as Final[str] module constants for citation-coverage meta-test (RUL-12/13 inheritance per RESEARCH §'Citation-Coverage Meta-Test')"
  artifacts:
    - path: lib/affordability.py
      provides: "_evaluate_blockers wrapper; LTV ceiling table; blocked_by citation constants; module-level evaluate() entrypoint"
      contains: "def _evaluate_blockers"
      min_lines: 1100
  key_links:
    - from: lib/affordability.py (evaluate)
      to: lib/affordability.py (evaluate_forward / evaluate_reverse)
      via: "dispatch by request.mode + post-process via _evaluate_blockers"
      pattern: "_evaluate_blockers\\("
    - from: lib/affordability.py
      to: lib/rules/va_residual_income.py
      via: "evaluate(region, family_size, loan_amount, actual_residual_income).binding_rule_citation"
      pattern: "binding_rule_citation"
    - from: lib/affordability.py
      to: lib/rules/usda.py
      via: "evaluate(...).income_eligible (RESEARCH Open Q#4)"
      pattern: "usda_evaluate|usda\\.evaluate"
    - from: lib/affordability.py
      to: lib/rules/atr_qm.py
      via: "general_qm_passes(apr, apor, loan_amount, lien_position='first')"
      pattern: "general_qm_passes"
---

<objective>
Implement the blocker-precedence pipeline (`_evaluate_blockers`) that wraps the math-only outputs from Plan 04-02 (`evaluate_forward`) and Plan 04-03 (`evaluate_reverse`) and applies the D-11 precedence rules. Plus a public `evaluate(request)` entrypoint that dispatches by `request.mode` and post-processes via `_evaluate_blockers`.

Replaces the loan-type-classify-only blocker behavior (where Plans 04-02/04-03 surfaced `response.blocked` based on classify result alone) with the FULL D-11 precedence: classify → USDA-income (when usda) → LTV/CLTV → DTI → ATR/QM → VA-residual.

Purpose: ship the regulatory-blocker decision layer. Per ROADMAP SC-3 the canonical example is a VA loan blocked by `"VA-RESIDUAL-WEST-FAMILY-4"`; this plan ships the path that produces that exact string verbatim. Per RESEARCH Open Q#4, USDA income-eligibility is added as a blocker step at planner discretion (this plan locks it in).

Output:
- `lib/affordability.py` extended with `_evaluate_blockers(response, request)` helper
- Public `evaluate(request: AffordabilityRequest) -> AffordabilityResponse` dispatcher
- LTV ceiling table per loan_type
- `BLOCKED_BY_*` Final[str] / format-string constants for citation-coverage meta-test
- Soft-warning citation strings for HPA-PMI-REQUIRED, ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR, FANNIE-LLPA-..., FREDDIE-INELIGIBLE-...

Decisions implemented: D-11 (blocked_by + warnings + precedence), D-12 (max_dti caller-supplied — DTI cap blocker uses request.max_dti), AFFD-07 (binding-rule citation when blocking).
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
@.planning/phases/04-affordability/04-01-pydantic-models-PLAN.md
@.planning/phases/04-affordability/04-02-forward-affordability-PLAN.md
@.planning/phases/04-affordability/04-03-reverse-affordability-PLAN.md
@CLAUDE.md
@lib/affordability.py
@lib/rules/va_residual_income.py
@lib/rules/usda.py
@lib/rules/atr_qm.py
@lib/rules/fannie_eligibility.py
@lib/rules/freddie_eligibility.py
@lib/rules/conventional_pmi.py

<interfaces>
<!-- Phase 2 predicates Plan 04-04 calls. SIGNATURES VERIFIED. -->

From lib/rules/va_residual_income.py (CONTEXT.md exact match):
```python
def evaluate(
    region: Region,
    family_size: int,
    loan_amount: Decimal,
    actual_residual_income: Decimal,
) -> ResidualIncomeResult
# ResidualIncomeResult.status: Literal["pass", "fail"]
# ResidualIncomeResult.binding_rule_citation: str  # f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}" — VERBATIM per Phase 2 D-11
```

From lib/rules/usda.py:
```python
def evaluate(
    household_income: Decimal,
    household_size: int,
    county: County,
    loan_amount: Decimal,
) -> USDAEligibilityResult
# USDAEligibilityResult.income_eligible: bool
# USDAEligibilityResult.applicable_income_limit: Decimal
# USDAEligibilityResult.guarantee_fee_upfront: Decimal
# USDAEligibilityResult.guarantee_fee_annual: Decimal
```

From lib/rules/atr_qm.py:
```python
def general_qm_passes(
    apr: Decimal,
    apor: Decimal,
    loan_amount: Decimal,
    lien_position: LienPosition,  # Literal["first", "subordinate"]; Phase 4 v1 = "first" only
) -> bool
# Returns True if loan PASSES general QM (APR-APOR spread <= threshold for loan-amount tier)
```

From lib/rules/fannie_eligibility.py:
```python
def compute_llpa(
    credit_score: int,
    ltv_pct: Decimal,           # IMPORTANT: percentage points, not fraction; Decimal("80.00") for 80%
    loan_purpose: LoanPurpose,  # Literal["purchase","rate_term_refi","cash_out_refi"]
    occupancy: Occupancy,       # Literal["primary","second_home","investment"]
    unit_count: int,
) -> Decimal  # LLPA basis points; negative=credit, positive=charge
# RESEARCH §'fannie_eligibility.py' line 246: ltv_pct MUST be quantized to <= 2 decimal places
```

From lib/rules/freddie_eligibility.py:
```python
def evaluate(
    credit_score: int,
    ltv_pct: Decimal,            # SAME percentage-point convention
    loan_purpose: LoanPurpose,
    occupancy: Occupancy,
    unit_count: int,
) -> FreddieEligibilityResult  # eligible: bool, credit_fee_bps: Decimal
```

From lib/rules/conventional_pmi.py:
```python
LTV_REQUEST_ELIGIBLE: Final[Decimal] = Decimal("0.80")  # statutory threshold; 12 USC §4902
```

<!-- Plan 04-02 / 04-03 outputs (already on lib/affordability.py) -->
```python
def evaluate_forward(req: ForwardModeRequest) -> AffordabilityResponse
def evaluate_reverse(req: ReverseModeRequest) -> AffordabilityResponse
# Both return responses with blocked + blocked_by potentially set for the loan-type-classify
# step ONLY (D-11 step 1). _evaluate_blockers must NOT short-circuit on that pre-set state
# without doing the rest of D-11 if classify_blocker is None.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add LTV ceiling table + blocked_by citation constants + soft-warning constants</name>
  <files>lib/affordability.py</files>
  <read_first>
    - lib/affordability.py (Plan 04-03 state — preserve all existing code)
    - .planning/phases/04-affordability/04-RESEARCH.md §"LTV / CLTV Ceiling Authority"
    - .planning/phases/04-affordability/04-RESEARCH.md §"Validation Architecture / Citation-coverage meta-test"
  </read_first>
  <behavior>
    - Test 1: `LTV_CEILING_BY_TARGET["conventional"] == Decimal("0.97")` (RESEARCH unconditional 97% per A1)
    - Test 2: `LTV_CEILING_BY_TARGET["fha"] == Decimal("0.965")` (RESEARCH HUD 4000.1)
    - Test 3: `LTV_CEILING_BY_TARGET["va"] == Decimal("1.00")` (RESEARCH VA Pamphlet 26-7)
    - Test 4: `LTV_CEILING_BY_TARGET["usda"] == Decimal("1.00")` (RESEARCH 7 CFR Part 3555)
    - Test 5: `LTV_CEILING_BY_TARGET["jumbo"] == Decimal("1.00")` (no v1 enforcement; pin sentinel)
    - Test 6: `BLOCKED_BY_DTI_CAP_TEMPLATE == "DTI-CAP-{LOAN_TYPE}"` (format string constant)
    - Test 7: `BLOCKED_BY_LTV_CEILING_TEMPLATE == "LTV-CEILING-{LOAN_TYPE}"` (format string constant)
    - Test 8: `BLOCKED_BY_CLTV_CEILING_TEMPLATE == "CLTV-CEILING-{LOAN_TYPE}"`
    - Test 9: `BLOCKED_BY_USDA_INCOME_TEMPLATE == "USDA-INCOME-LIMIT-{state_fips}-{county_fips}"`
    - Test 10: `BLOCKED_BY_ATR_QM_PRICE_FIRST == "ATR-QM-PRICE-FIRST"` (Phase 2 RUL-09 stable citation)
    - Test 11: `WARNING_HPA_PMI_REQUIRED == "HPA-PMI-REQUIRED"` (soft warning; Plan 04-04 wires)
    - Test 12: `WARNING_ATR_QM_NOT_EVALUATED == "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR"` (soft warning)
    - Test 13: `WARNING_FANNIE_LLPA_TEMPLATE == "FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}"` (soft warning template)
    - Test 14: `WARNING_FREDDIE_INELIGIBLE_TEMPLATE == "FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}"` (soft warning template)
    - Test 15: All citation constants are exposed in `__all__` OR are accessible via `from lib.affordability import BLOCKED_BY_*` (citation-coverage meta-test in Plan 04-06 introspects these)
  </behavior>
  <action>
    Edit `lib/affordability.py`. Add a constants block AFTER the existing `_LOAN_TYPE_BLOCKER_PREFIX` table (Plan 04-02) and BEFORE the helper functions:

    ```python
    # =============================================================================
    # D-11 Blocker Precedence — Citation Constants + Ceiling Tables
    # =============================================================================
    # Citation strings emitted by _evaluate_blockers. Plan 04-06 ships the
    # citation-coverage meta-test that introspects these via `dir(lib.affordability)`
    # and asserts each appears in at least one fixture (RUL-12/13 inheritance).

    # LTV ceiling per target_loan_type (RESEARCH §"LTV / CLTV Ceiling Authority").
    # Authoritative sources cited in module docstring D-11 block.
    LTV_CEILING_BY_TARGET: Final[dict[str, Decimal]] = {
        "conventional": Decimal("0.97"),  # Fannie 97% LTV (HomeReady or first-time-buyer; v1 unconditional per Assumption A1)
        "jumbo": Decimal("1.00"),         # No v1 enforcement; non-agency LTV varies 80-90% in practice (RESEARCH §"LTV / CLTV Ceiling Authority")
        "fha": Decimal("0.965"),          # HUD Handbook 4000.1; credit_score >= 580
        "va": Decimal("1.00"),            # Full-entitlement vets per VA Pamphlet 26-7 Chapter 3
        "usda": Decimal("1.00"),          # USDA SFH GLP per 7 CFR Part 3555
    }

    # CLTV ceiling per target_loan_type (RESEARCH §"CLTV ceilings"; mirrors LTV by default).
    CLTV_CEILING_BY_TARGET: Final[dict[str, Decimal]] = {
        "conventional": Decimal("0.97"),
        "jumbo": Decimal("1.00"),
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
    # the predicate's `result.binding_rule_citation` field per Phase 2 D-11
    # (format f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"). DO NOT
    # re-construct or format-shadow that string in Phase 4 — drift between
    # predicate and consumer breaks ROADMAP SC-3 + Phase 2 D-11 contract.
    # The pattern below is for the citation-coverage meta-test only (regex match
    # — meta-test asserts at least one fixture's blocked_by matches this).
    BLOCKED_BY_VA_RESIDUAL_PATTERN: Final[str] = r"^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$"

    # ----- Soft warnings (response.warnings) -----
    WARNING_HPA_PMI_REQUIRED: Final[str] = "HPA-PMI-REQUIRED"
    WARNING_ATR_QM_NOT_EVALUATED: Final[str] = "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR"
    WARNING_FANNIE_LLPA_TEMPLATE: Final[str] = "FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}"
    WARNING_FREDDIE_INELIGIBLE_TEMPLATE: Final[str] = "FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}"
    ```

    Verify `Final` is imported from typing.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "
from decimal import Decimal
from lib.affordability import (
    LTV_CEILING_BY_TARGET, CLTV_CEILING_BY_TARGET,
    BLOCKED_BY_LTV_CEILING_TEMPLATE, BLOCKED_BY_CLTV_CEILING_TEMPLATE,
    BLOCKED_BY_DTI_CAP_TEMPLATE, BLOCKED_BY_USDA_INCOME_TEMPLATE,
    BLOCKED_BY_ATR_QM_PRICE_FIRST, BLOCKED_BY_VA_RESIDUAL_PATTERN,
    WARNING_HPA_PMI_REQUIRED, WARNING_ATR_QM_NOT_EVALUATED,
    WARNING_FANNIE_LLPA_TEMPLATE, WARNING_FREDDIE_INELIGIBLE_TEMPLATE,
)

assert LTV_CEILING_BY_TARGET['conventional'] == Decimal('0.97')
assert LTV_CEILING_BY_TARGET['fha'] == Decimal('0.965')
assert LTV_CEILING_BY_TARGET['va'] == Decimal('1.00')
assert LTV_CEILING_BY_TARGET['usda'] == Decimal('1.00')
assert LTV_CEILING_BY_TARGET['jumbo'] == Decimal('1.00')

assert BLOCKED_BY_DTI_CAP_TEMPLATE == 'DTI-CAP-{LOAN_TYPE}'
assert BLOCKED_BY_LTV_CEILING_TEMPLATE == 'LTV-CEILING-{LOAN_TYPE}'
assert BLOCKED_BY_USDA_INCOME_TEMPLATE == 'USDA-INCOME-LIMIT-{state_fips}-{county_fips}'
assert BLOCKED_BY_ATR_QM_PRICE_FIRST == 'ATR-QM-PRICE-FIRST'
assert BLOCKED_BY_VA_RESIDUAL_PATTERN == r'^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$'

assert WARNING_HPA_PMI_REQUIRED == 'HPA-PMI-REQUIRED'
assert WARNING_ATR_QM_NOT_EVALUATED == 'ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR'

print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - lib/affordability.py contains literal substring `LTV_CEILING_BY_TARGET: Final[dict[str, Decimal]] = {`
    - lib/affordability.py contains literal substring `"conventional": Decimal("0.97")`
    - lib/affordability.py contains literal substring `"fha": Decimal("0.965")`
    - lib/affordability.py contains literal substring `BLOCKED_BY_LTV_CEILING_TEMPLATE: Final[str] = "LTV-CEILING-{LOAN_TYPE}"`
    - lib/affordability.py contains literal substring `BLOCKED_BY_DTI_CAP_TEMPLATE: Final[str] = "DTI-CAP-{LOAN_TYPE}"`
    - lib/affordability.py contains literal substring `BLOCKED_BY_USDA_INCOME_TEMPLATE: Final[str] = "USDA-INCOME-LIMIT-{state_fips}-{county_fips}"`
    - lib/affordability.py contains literal substring `BLOCKED_BY_ATR_QM_PRICE_FIRST: Final[str] = "ATR-QM-PRICE-FIRST"`
    - lib/affordability.py contains literal substring `BLOCKED_BY_VA_RESIDUAL_PATTERN: Final[str] = r"^VA-RESIDUAL`
    - lib/affordability.py contains literal substring `WARNING_HPA_PMI_REQUIRED`
    - lib/affordability.py contains literal substring `WARNING_ATR_QM_NOT_EVALUATED`
    - All 15 behavioral tests pass via inline python verification
    - `grep -c "BLOCKED_BY_" lib/affordability.py | grep -v '^#'` returns &gt;= 5 (citation-coverage discoverability for Plan 04-06)
    - `uv run mypy --strict lib/affordability.py` exits 0
    - `uv run ruff check lib/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    Citation constants + ceiling tables shipped; citation-coverage meta-test in Plan 04-06 can discover them via grep introspection; mypy + ruff clean.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement _evaluate_blockers + public evaluate() dispatcher</name>
  <files>lib/affordability.py</files>
  <read_first>
    - lib/affordability.py (Task 1 state — citation constants + ceilings in place)
    - .planning/phases/04-affordability/04-CONTEXT.md D-11 (full block — precedence rules)
    - .planning/phases/04-affordability/04-RESEARCH.md §"Blocker Precedence — Domain Validation"
    - .planning/phases/04-affordability/04-RESEARCH.md §"Open Questions" #4 (USDA), #5 (VA fee), #7 (VA required)
    - lib/rules/va_residual_income.py (verify result.binding_rule_citation field name)
    - lib/rules/atr_qm.py (verify general_qm_passes signature)
    - lib/rules/usda.py (verify evaluate signature + USDAEligibilityResult fields)
    - lib/rules/fannie_eligibility.py + freddie_eligibility.py (LLPA / eligible field names)
  </read_first>
  <behavior>
    - Test 1: `evaluate(req)` for clean conventional 80% LTV (King WA, $400k loan, $500k value, joint income $10k, no debts, max_dti=0.43) returns blocked=False, blocked_by=None
    - Test 2: `evaluate(req)` for VA loan with WEST region + family_size=4 + actual_residual_income BELOW M26-7 minimum returns blocked=True, blocked_by="VA-RESIDUAL-WEST-FAMILY-4" (verbatim from predicate; ROADMAP SC-3)
    - Test 3: `evaluate(req)` for FHA loan with DTI back > max_dti returns blocked=True, blocked_by="DTI-CAP-FHA"
    - Test 4: `evaluate(req)` for conv loan with LTV=0.98 (above 0.97 ceiling) returns blocked=True, blocked_by="LTV-CEILING-CONVENTIONAL"
    - Test 5: `evaluate(req)` for jumbo loan with $2M loan + King WA county returns blocked=True, blocked_by="FHFA-LIMIT-CONFORMING-53-033" (loan-type-classify step 1; pre-existing from Plan 04-02 path; precedence preserved)
    - Test 6: USDA loan with usda.evaluate.income_eligible=False returns blocked=True, blocked_by="USDA-INCOME-LIMIT-{state_fips}-{county_fips}" (RESEARCH Open Q#4; placed AFTER classify in precedence)
    - Test 7: For first-lien residential with apr+apor present and general_qm_passes=False: blocked=True, blocked_by="ATR-QM-PRICE-FIRST"
    - Test 8: For first-lien residential with apr=None AND apor=None: NO blocker; warnings contains "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR" (advisory per CONTEXT.md D-11 + RESEARCH §"Missing apr/apor")
    - Test 9: Conv 85% LTV (above 0.80) with caller monthly_pmi: warnings contains "HPA-PMI-REQUIRED" (PMI required advisory per D-11 soft-blocker)
    - Test 10: First hard-fail wins: classify-fail short-circuits; subsequent steps don't run; only the FIRST citation appears in blocked_by
    - Test 11: Fannie LLPA hit (compute_llpa returns positive bps): warnings contains a "FANNIE-LLPA-..." entry; LLPA is NOT a blocker (matches CONTEXT.md D-11 soft-blocker design)
    - Test 12: Freddie ineligible: warnings contains a "FREDDIE-INELIGIBLE-..." entry; NOT a blocker
    - Test 13: VA-residual citation read VERBATIM via `result.binding_rule_citation` — no Phase 4-side reformatting; pinned by code grep that the source string never appears in lib/affordability.py outside of the comment naming the predicate's stable contract
    - Test 14: `evaluate(req)` is the public dispatcher: ForwardModeRequest → evaluate_forward + _evaluate_blockers; ReverseModeRequest → evaluate_reverse + _evaluate_blockers; mode discriminator dispatch matches Pydantic union
    - Test 15: response.blocked is True iff response.blocked_by is not None (invariant)
    - Test 16: For non-VA target loan_type with VA inputs absent: no VA-residual evaluation (skipped step)
    - Test 17: For VA target with VA inputs present and residual passes: blocked=False, no VA citation in blocked_by
  </behavior>
  <action>
    Edit `lib/affordability.py`. Steps:

    **A. Add Phase 2 predicate imports** (after Plan 04-02's existing imports):
    ```python
    from lib.rules.atr_qm import general_qm_passes
    from lib.rules.fannie_eligibility import compute_llpa as fannie_compute_llpa
    from lib.rules.freddie_eligibility import evaluate as freddie_evaluate
    from lib.rules.usda import evaluate as usda_evaluate
    from lib.rules.va_residual_income import evaluate as va_residual_evaluate
    ```

    **B. Add helper for percentage-point LTV** (RESEARCH §"fannie_eligibility.py" — Fannie/Freddie take ltv as percentage points, NOT fraction):
    ```python
    def _ltv_to_percentage_points(ltv_fraction: Decimal) -> Decimal:
        """Convert fractional LTV (Decimal('0.80')) to percentage points
        (Decimal('80.00')) for Fannie/Freddie predicate consumption.
        Quantizes to 2 decimal places; the predicates raise ValueError on
        higher-precision input (RESEARCH §A.4 line 245)."""
        return (ltv_fraction * Decimal("100")).quantize(Decimal("0.01"))


    def _ltv_bucket_label(ltv_pct_points: Decimal) -> str:
        """Coarse LTV bucket label for soft-warning citation strings
        (FANNIE-LLPA-... + FREDDIE-INELIGIBLE-...). Buckets:
        '60-OR-LESS', '60-75', '75-80', '80-85', '85-90', '90-95', 'OVER-95'."""
        if ltv_pct_points <= Decimal("60.00"): return "60-OR-LESS"
        if ltv_pct_points <= Decimal("75.00"): return "60-75"
        if ltv_pct_points <= Decimal("80.00"): return "75-80"
        if ltv_pct_points <= Decimal("85.00"): return "80-85"
        if ltv_pct_points <= Decimal("90.00"): return "85-90"
        if ltv_pct_points <= Decimal("95.00"): return "90-95"
        return "OVER-95"


    def _credit_score_bucket_label(score: int) -> str:
        """Coarse credit-score bucket label for soft-warning citation strings.
        Phase 2 RUL-02 / RUL-03 use the standard 8-bucket boundaries
        (620, 640, 660, 680, 700, 720, 740, 760)."""
        if score < 620: return "BELOW-620"
        if score < 640: return "620-639"
        if score < 660: return "640-659"
        if score < 680: return "660-679"
        if score < 700: return "680-699"
        if score < 720: return "700-719"
        if score < 740: return "720-739"
        if score < 760: return "740-759"
        return "760-OR-ABOVE"
    ```

    **C. Implement `_evaluate_blockers` (the precedence pipeline):**

    Important: Pydantic models are `frozen=True`, so we cannot mutate `response.blocked` in place. Use `response.model_copy(update={...})` per Pydantic v2 idiom.

    ```python
    def _evaluate_blockers(
        response: AffordabilityResponse,
        request: ForwardModeRequest | ReverseModeRequest,
    ) -> AffordabilityResponse:
        """Apply D-11 blocker precedence to a math-only response from
        evaluate_forward / evaluate_reverse.

        Precedence (D-11 + RESEARCH Open Q#4):
          1. Loan-type classification (already wired in evaluate_forward/reverse;
             short-circuits if response.blocked already True from classify step).
          2. USDA income eligibility (when target_loan_type=='usda'; RESEARCH Open Q#4).
          3. LTV / CLTV ceiling per target_loan_type (RESEARCH §"LTV / CLTV Ceiling Authority").
          4. DTI cap exceeded (forward only; reverse mode's solver enforces by construction).
          5. ATR/QM general-QM (when first-lien residential AND apr+apor present;
             advisory if missing — RESEARCH §"Missing apr/apor").
          6. VA residual income (when target_loan_type=='va').

        Soft warnings (always evaluated, never block):
          - Fannie LLPA hit
          - Freddie ineligibility
          - HPA-PMI-REQUIRED (when conventional + LTV > 0.80)
          - ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR (when one or both missing)

        Returns a new AffordabilityResponse with updated blocked / blocked_by /
        warnings (Pydantic frozen — uses model_copy(update=...)).
        """
        # 1. Short-circuit: classify-step blocker already set in evaluate_forward/reverse
        if response.blocked:
            # Append soft warnings even when classify-blocked, for diagnostic richness
            return _append_soft_warnings(response, request)

        new_warnings: list[str] = list(response.warnings)
        new_blocked_by: str | None = None

        # Compute the LTV used for downstream checks (fraction; NOT percentage points)
        if response.mode == "forward":
            ltv_fraction = response.ltv  # already computed in evaluate_forward
            cltv_fraction = response.cltv
            dti_back = response.dti_back
            financed_loan = response.financed_loan_amount or response.loan_amount
        else:  # reverse
            ltv_fraction = response.assumed_ltv_pct
            # Reverse mode does NOT compute CLTV (no junior-lien semantic with no property);
            # treat CLTV-ceiling as not-applicable here.
            cltv_fraction = None
            dti_back = None  # reverse-mode dti is enforced by construction (D-08)
            financed_loan = response.max_loan_amount

        target = request.target_loan_type
        loan_type_upper = target.upper()
        location = request.household.location

        # Capture warnings emitted by the predicates we call here
        captured_warnings: list[str] = []
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", StaleReferenceWarning)

            # 2. USDA income eligibility (RESEARCH Open Q#4 + BLOCKER 2 fix)
            if target == "usda" and new_blocked_by is None:
                county = _build_county(location)
                # BLOCKER 2 fix: use request.household.size directly (the FULL household
                # size including non-applicant dependents). Do NOT infer from
                # len(applicants) or va.family_size — that silently approximates USDA
                # household income limits using mortgage-applicant count instead of
                # the regulator-defined household size, producing wrong USDA decisions
                # (e.g., 2-applicant + 3-children case: applicants=2 but actual size=5).
                # Plan 04-01 added the required `size` field; the validator pre-condition
                # guarantees it is present and >= 1. Per CLAUDE.md + CONTEXT.md "fail
                # loud, no inference".
                household_size = request.household.size
                # We need household income for usda.evaluate
                household_income = response.total_gross_monthly_income * Decimal("12")
                usda_result = usda_evaluate(
                    household_income=household_income,
                    household_size=household_size,
                    county=county,
                    loan_amount=financed_loan,
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

            # 4. DTI cap (forward only; reverse enforces by construction)
            # Reverse mode never blocks on DTI — enforced by construction (D-08);
            # consumers needing DTI-cap check must round-trip through forward mode (W1 fix).
            if new_blocked_by is None and dti_back is not None:
                if dti_back > request.max_dti:
                    new_blocked_by = BLOCKED_BY_DTI_CAP_TEMPLATE.format(
                        LOAN_TYPE=loan_type_upper,
                    )

            # 5. ATR/QM general-QM (first-lien residential)
            #    Phase 4 v1 scope: all evaluations are first-lien residential
            #    (CONTEXT.md / RESEARCH §"Residential vs non-residential").
            if new_blocked_by is None:
                if request.apr is not None and request.apor is not None:
                    qm_passes = general_qm_passes(
                        apr=request.apr,
                        apor=request.apor,
                        loan_amount=financed_loan,
                        lien_position="first",
                    )
                    if not qm_passes:
                        new_blocked_by = BLOCKED_BY_ATR_QM_PRICE_FIRST
                # else: half-supplied case is rejected at request boundary by
                # _validate_common (Plan 04-01); both-None case falls through
                # to the warning below.

            # 6. VA residual income (target=='va' only)
            if new_blocked_by is None and target == "va":
                # Pydantic _validate_common already enforced va is not None when target=='va'
                va = request.household.va
                assert va is not None  # noqa: S101 — validator pre-condition
                va_result = va_residual_evaluate(
                    region=va.region,
                    family_size=va.family_size,
                    loan_amount=financed_loan,
                    actual_residual_income=va.actual_residual_income,
                )
                if va_result.status == "fail":
                    # READ VERBATIM (Phase 2 D-11 STABLE format; DO NOT format-shadow).
                    new_blocked_by = va_result.binding_rule_citation

            # Capture stale warnings emitted by all the predicate calls above
            for w in captured:
                if issubclass(w.category, StaleReferenceWarning):
                    captured_warnings.append(str(w.message))

        new_warnings.extend(captured_warnings)

        # Build intermediate response with hard blocker (if any) applied
        intermediate = response.model_copy(
            update={
                "blocked": new_blocked_by is not None,
                "blocked_by": new_blocked_by,
                "warnings": new_warnings,
            }
        )

        # Always append soft warnings (HPA-PMI-REQUIRED, Fannie LLPA, Freddie, ATR/QM-not-evaluated)
        return _append_soft_warnings(intermediate, request)


    def _append_soft_warnings(
        response: AffordabilityResponse,
        request: ForwardModeRequest | ReverseModeRequest,
    ) -> AffordabilityResponse:
        """Append soft (non-blocking) warnings to response.warnings.

        Always-evaluated, regardless of hard-blocker state:
          - HPA-PMI-REQUIRED (when conventional + LTV > 0.80)
          - ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR (when both apr/apor None)
          - FANNIE-LLPA-{FICO}-{LTV} (when compute_llpa returns positive bps)
          - FREDDIE-INELIGIBLE-{FICO}-{LTV} (when freddie_evaluate.eligible == False)
        """
        soft: list[str] = []

        if response.mode == "forward":
            ltv_fraction = response.ltv
        else:
            ltv_fraction = response.assumed_ltv_pct

        # HPA-PMI-REQUIRED
        if (
            request.target_loan_type == "conventional"
            and ltv_fraction is not None
            and ltv_fraction > LTV_REQUEST_ELIGIBLE
        ):
            soft.append(WARNING_HPA_PMI_REQUIRED)

        # ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR
        if request.apr is None and request.apor is None:
            soft.append(WARNING_ATR_QM_NOT_EVALUATED)

        # Fannie LLPA + Freddie eligibility (only for conventional / jumbo targets;
        # FHA/VA/USDA are out of GSE scope).
        if (
            request.target_loan_type in {"conventional", "jumbo"}
            and ltv_fraction is not None
        ):
            min_credit_score = min(
                a.credit_score for a in request.household.applicants
            )
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
                        soft.append(WARNING_FANNIE_LLPA_TEMPLATE.format(
                            FICO_BUCKET=fico_bucket,
                            LTV_BUCKET=ltv_bucket,
                        ))
                except (LookupError, ValueError):
                    # Phase 2 predicates raise LookupError on out-of-grid inputs;
                    # treat as advisory (no warning) rather than blocker.
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
                        soft.append(WARNING_FREDDIE_INELIGIBLE_TEMPLATE.format(
                            FICO_BUCKET=fico_bucket,
                            LTV_BUCKET=ltv_bucket,
                        ))
                except (LookupError, ValueError):
                    pass

                for w in cw:
                    if issubclass(w.category, StaleReferenceWarning):
                        soft.append(str(w.message))

        if not soft:
            return response

        return response.model_copy(
            update={"warnings": [*response.warnings, *soft]}
        )
    ```

    **D. Implement public `evaluate()` dispatcher:**
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
        callsite passes a concrete request to this function.
        """
        if request.mode == "forward":
            base = evaluate_forward(request)
        else:
            base = evaluate_reverse(request)
        return _evaluate_blockers(base, request)
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "
from decimal import Decimal
from lib.affordability import (
    evaluate, ForwardModeRequest, Household, LocationFIPS,
    Applicant, MonthlyDebts, EscrowInputs, VAInputs,
    BLOCKED_BY_DTI_CAP_TEMPLATE, BLOCKED_BY_LTV_CEILING_TEMPLATE,
    WARNING_HPA_PMI_REQUIRED,
)

household = Household(
    location=LocationFIPS(state='WA', state_fips='53', county_fips='033', county_name='King', zip='98101'),
    applicants=[Applicant(name='A', gross_monthly_income=Decimal('5000.00'), credit_score=720),
                Applicant(name='B', gross_monthly_income=Decimal('5000.00'), credit_score=680)],
    monthly_debts=MonthlyDebts(),
    escrow=EscrowInputs(property_tax_monthly=Decimal('0.00'),
                        insurance_monthly=Decimal('0.00'),
                        hoa_monthly=Decimal('0.00')),
)

# Test 1: clean conv 80% — no blocker
req_clean = ForwardModeRequest(
    mode='forward', household=household, max_dti=Decimal('0.430000'),
    target_loan_type='conventional', term_months=360, annual_rate=Decimal('0.065000'),
    loan_amount=Decimal('400000.00'), property_value=Decimal('500000.00'),
)
resp = evaluate(req_clean)
assert not resp.blocked, f'expected not blocked, got blocked_by={resp.blocked_by}'
assert resp.blocked_by is None

# Test 4: LTV ceiling violation — conv 0.98 > 0.97
req_ltv = ForwardModeRequest(
    mode='forward', household=household, max_dti=Decimal('0.430000'),
    target_loan_type='conventional', term_months=360, annual_rate=Decimal('0.065000'),
    monthly_pmi=Decimal('250.00'),  # required when conv > 0.80
    loan_amount=Decimal('490000.00'), property_value=Decimal('500000.00'),  # LTV=0.98
)
resp_ltv = evaluate(req_ltv)
assert resp_ltv.blocked, 'expected blocked'
assert resp_ltv.blocked_by == 'LTV-CEILING-CONVENTIONAL', f'got {resp_ltv.blocked_by}'

# Test 9: HPA-PMI-REQUIRED warning for conv 85%
req_pmi = ForwardModeRequest(
    mode='forward', household=household, max_dti=Decimal('0.430000'),
    target_loan_type='conventional', term_months=360, annual_rate=Decimal('0.065000'),
    monthly_pmi=Decimal('150.00'),
    loan_amount=Decimal('425000.00'), property_value=Decimal('500000.00'),  # LTV=0.85
)
resp_pmi = evaluate(req_pmi)
assert WARNING_HPA_PMI_REQUIRED in resp_pmi.warnings, f'warnings={resp_pmi.warnings}'

# Test 15: invariant blocked iff blocked_by
for r in [resp, resp_ltv, resp_pmi]:
    assert (r.blocked) == (r.blocked_by is not None), f'invariant violated: blocked={r.blocked}, blocked_by={r.blocked_by}'

print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - lib/affordability.py contains literal substring `def _evaluate_blockers(`
    - lib/affordability.py contains literal substring `household_size = request.household.size` (BLOCKER 2 fix; full-household-size used directly)
    - lib/affordability.py does NOT contain literal substring `household_size = sum(1 for _ in request.household.applicants)` (BLOCKER 2: stale len(applicants) inference removed)
    - lib/affordability.py does NOT contain literal substring `household_size = request.household.va.family_size` (BLOCKER 2: stale va.family_size fallback removed)
    - lib/affordability.py contains literal substring `Reverse mode never blocks on DTI` (W1 comment)
    - lib/affordability.py contains literal substring `def evaluate(` (public dispatcher)
    - lib/affordability.py contains literal substring `def _append_soft_warnings(`
    - lib/affordability.py contains literal substring `va_result.binding_rule_citation` (VA verbatim per Phase 2 D-11)
    - lib/affordability.py contains literal substring `from lib.rules.va_residual_income import evaluate as va_residual_evaluate`
    - lib/affordability.py contains literal substring `from lib.rules.atr_qm import general_qm_passes`
    - lib/affordability.py contains literal substring `from lib.rules.usda import evaluate as usda_evaluate`
    - lib/affordability.py contains literal substring `from lib.rules.fannie_eligibility import compute_llpa as fannie_compute_llpa`
    - lib/affordability.py contains literal substring `from lib.rules.freddie_eligibility import evaluate as freddie_evaluate`
    - lib/affordability.py contains literal substring `BLOCKED_BY_LTV_CEILING_TEMPLATE.format(`
    - lib/affordability.py contains literal substring `BLOCKED_BY_DTI_CAP_TEMPLATE.format(`
    - lib/affordability.py contains literal substring `BLOCKED_BY_USDA_INCOME_TEMPLATE.format(`
    - lib/affordability.py contains literal substring `BLOCKED_BY_ATR_QM_PRICE_FIRST` (used as RHS, not template)
    - lib/affordability.py contains literal substring `WARNING_HPA_PMI_REQUIRED` (soft warning emission)
    - lib/affordability.py contains literal substring `lien_position="first"` (Phase 4 v1 scope per RESEARCH)
    - lib/affordability.py contains literal substring `response.model_copy(update=` (frozen Pydantic mutation idiom)
    - lib/affordability.py does NOT contain literal substring `f"VA-RESIDUAL-` (Phase 4 must NOT construct the VA citation; reads from predicate)
    - lib/affordability.py does NOT contain literal substring `binding_rule_citation = ` (Phase 4 reads, never writes)
    - All 17 behavioral tests pass via inline python verification + the verify block above
    - `uv run pytest -x` still green (no Phase 1/2/3 regressions; Wave 0 stubs still xfail)
    - `uv run mypy --strict lib/affordability.py` exits 0
    - `uv run ruff check lib/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    Blocker precedence pipeline is shipped per D-11; VA-residual citation is read VERBATIM from predicate (no format drift); USDA-income blocker added per RESEARCH Open Q#4; soft warnings (HPA-PMI-REQUIRED, Fannie LLPA, Freddie ineligible, ATR/QM not evaluated) populate response.warnings; public `evaluate()` dispatcher exposed for Plan 04-05 CLI consumption; mypy + ruff clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| _evaluate_blockers → predicate result.binding_rule_citation | Format-drift between predicate and consumer breaks Phase 2 D-11 + ROADMAP SC-3 contract |
| Phase 4 citation strings → fixtures | Citation-coverage meta-test (Plan 04-06) detects missing test coverage; planner-finalized formats are pinned by tests |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-04-01 | Tampering | VA-residual citation format-drift | mitigate | Acceptance criteria: lib/affordability.py does NOT contain `f"VA-RESIDUAL-` (negative grep gate); `va_result.binding_rule_citation` read verbatim; ROADMAP SC-3 fixture `forward_va_residual_fail.json` (Plan 04-06) asserts the exact "VA-RESIDUAL-WEST-FAMILY-4" string |
| T-04-04-02 | Tampering | First hard-fail wins precedence violation (e.g., DTI fires before LTV) | mitigate | Action body specifies the precedence in code structure (sequential `if new_blocked_by is None and ...`); Plan 04-06 ships precedence-pin fixtures (e.g., a request that violates BOTH LTV and DTI must surface LTV citation, not DTI) |
| T-04-04-03 | Tampering | LTV ceiling silently downgraded for conventional 97% (FTHB nuance) | accept | RESEARCH Assumption A1: Phase 4 v1 unconditional 97% per HomeReady; FTHB modeling out of v1; documented in module docstring; low-risk for personal-use |
| T-04-04-04 | Tampering | USDA blocker placed AFTER LTV (mis-ordering RESEARCH Open Q#4) | mitigate | Action body explicitly orders USDA at step 2 (after classify, before LTV/CLTV); Plan 04-06 fixture pins this with a USDA loan that has BOTH income-ineligibility AND below-ceiling LTV — must surface USDA-INCOME-LIMIT, not LTV-CEILING |
| T-04-04-05 | Repudiation | Soft warnings silently dropped | mitigate | _append_soft_warnings runs UNCONDITIONALLY (even when blocked); Plan 04-06 fixture asserts both blocked_by AND warnings populated |
| T-04-04-06 | Tampering | Pydantic frozen response mutated in-place | mitigate | Action body uses `response.model_copy(update={...})` per Pydantic v2 idiom; acceptance criteria: grep confirms presence; trying to assign to a frozen field would raise TypeError at runtime |
| T-04-04-07 | Tampering | Fannie LLPA / Freddie LookupError silently swallowed | accept | RESEARCH §"fannie_eligibility.py" + §"freddie_eligibility.py": predicates raise LookupError on out-of-grid inputs (pre-2026 LLPA matrix bucket misses). Action body explicitly catches these and skips the soft warning (out-of-grid is informational; no actionable info). Documented in code comment. |
| T-04-04-08 | Information Disclosure | response.warnings leaks predicate-internal staleness messages | accept | RESEARCH §"_loader.py + StaleReferenceWarning": surfacing stale warnings to caller is by-design (Phase 2 D-12 + D-11). Documented in module docstring; the "loud-by-default" stance is the project-level choice. |
</threat_model>

<verification>
After both tasks complete:

```bash
# All citations introspectable
uv run python -c "from lib.affordability import (BLOCKED_BY_LTV_CEILING_TEMPLATE, BLOCKED_BY_CLTV_CEILING_TEMPLATE, BLOCKED_BY_DTI_CAP_TEMPLATE, BLOCKED_BY_USDA_INCOME_TEMPLATE, BLOCKED_BY_ATR_QM_PRICE_FIRST, BLOCKED_BY_VA_RESIDUAL_PATTERN); print('citations OK')"

# Public entrypoint works
uv run python -c "from lib.affordability import evaluate; print('evaluate OK')"

# Phase regressions check
uv run pytest -x

# mypy + ruff clean
uv run mypy --strict lib/affordability.py
uv run ruff check lib/affordability.py
```
</verification>

<success_criteria>
- [ ] D-11 precedence implemented in code structure: classify (preserved from 04-02/03) → USDA-income (when usda) → LTV/CLTV → DTI → ATR/QM → VA-residual
- [ ] First-hard-fail-wins short-circuit (subsequent steps skipped when blocked_by already set)
- [ ] VA-residual citation read VERBATIM from `result.binding_rule_citation` (no Phase 4 format-shadow)
- [ ] USDA income blocker added per RESEARCH Open Q#4
- [ ] Soft warnings always evaluated: HPA-PMI-REQUIRED, ATR-QM-NOT-EVALUATED, FANNIE-LLPA-..., FREDDIE-INELIGIBLE-...
- [ ] Public `evaluate(request)` dispatcher works for both ForwardModeRequest + ReverseModeRequest
- [ ] All citation constants exposed at module level for citation-coverage meta-test (Plan 04-06)
- [ ] No Phase 1/2/3 regressions; full suite green
- [ ] mypy --strict + ruff clean
</success_criteria>

<output>
After completion, create `.planning/phases/04-affordability/04-04-SUMMARY.md` per the standard template. Plan 04-05 (CLI + config) consumes the public `evaluate()` entrypoint.
</output>
