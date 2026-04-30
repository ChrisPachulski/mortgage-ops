---
phase: 04-affordability
plan: 06
type: execute
wave: 6
depends_on: ["04-00", "04-01", "04-02", "04-03", "04-04", "04-05"]
files_modified:
  - tests/test_affordability.py
  - tests/fixtures/affordability/forward_conventional_80_ltv.json
  - tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json
  - tests/fixtures/affordability/forward_fha_above_dti_cap.json
  - tests/fixtures/affordability/forward_va_residual_fail.json
  - tests/fixtures/affordability/forward_jumbo_above_county_limit.json
  - tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json
  - tests/fixtures/affordability/joint_applicants_two_incomes.json
  - tests/fixtures/affordability/single_applicant.json
  - tests/fixtures/affordability/household_example_yml_e2e.json
autonomous: true
requirements: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-05, AFFD-06, AFFD-07, AFFD-08, AFFD-09]
requirements_addressed: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-05, AFFD-06, AFFD-07, AFFD-08, AFFD-09]
tags: [phase-4, affordability, tests, fixtures, golden-values, citation-coverage, wave-6]

must_haves:
  truths:
    - "All 9 Wave 0 xfail stubs replaced with real assertions; xpass count == 9 (or xfail markers removed entirely)"
    - "Each AFFD-XX requirement has at least one test that exercises it end-to-end through evaluate() OR scripts/affordability.py subprocess"
    - "9+ JSON fixtures committed under tests/fixtures/affordability/ (D-17 list)"
    - "All fixture money fields are quoted Decimal strings (D-18 — exact equality, no assertAlmostEqual)"
    - "ROADMAP SC-3 verbatim: forward_va_residual_fail.json fixture asserts response.blocked_by == 'VA-RESIDUAL-WEST-FAMILY-4' exactly"
    - "ROADMAP SC-2 verbatim: reverse_conventional_80_ltv_43_dti.json round-trips through forward; dti_back closure within Decimal('0.0001'); dollar amounts equal exactly (D-09)"
    - "ROADMAP SC-4 verbatim: household_example_yml_e2e.json invokes scripts/affordability.py via subprocess against config/household.example.yml — full pipeline"
    - "ROADMAP SC-5 verbatim: joint_applicants_two_incomes.json + single_applicant.json both pass; same code path"
    - "Citation-coverage meta-test: every BLOCKED_BY_* constant in lib/affordability.py has at least one fixture with response.blocked_by matching it"
    - "VA-residual citation regex match: at least one fixture has blocked_by matching r'^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\\d+$'"
    - "CLI subprocess pattern (Phase 3 D-17): tests use subprocess.run([sys.executable, str(SCRIPT_PATH), '--input', tmp_path/'x.json']); never `import scripts.affordability` directly"
    - "D-18 fast --help test: subprocess --help exits 0 with lib.affordability and numpy_financial NOT in sys.modules (Phase 3 03-04 idiom; same fresh-Python subprocess inline harness)"
    - "6-key Pydantic envelope test: float-in-money rejected with 6-key shape on stderr (Phase 3 03-06 idiom)"
    - "Round-trip closure test: evaluate_forward(reverse(req).max_loan_amount, max_loan_amount/target_ltv_pct, ...) yields dti_back <= max_dti + Decimal('0.0001') AND loan_amount == max_loan_amount exactly"
  artifacts:
    - path: tests/test_affordability.py
      provides: "Full Phase 4 test surface: 9 AFFD-XX tests + citation coverage + lazy-import + float-gate + round-trip + CLI subprocess + fixture loaders"
      contains: "def test_AFFD_07_blocked_by_va_residual_west_family_4"
      min_lines: 600
    - path: tests/fixtures/affordability/forward_va_residual_fail.json
      provides: "ROADMAP SC-3 verbatim fixture"
      contains: "VA-RESIDUAL-WEST-FAMILY-4"
    - path: tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json
      provides: "ROADMAP SC-2 round-trip anchor"
      contains: "reverse"
    - path: tests/fixtures/affordability/household_example_yml_e2e.json
      provides: "ROADMAP SC-4 e2e invocation manifest"
  key_links:
    - from: tests/test_affordability.py
      to: tests/fixtures/affordability/*.json
      via: "affordability_fixture loader (Plan 04-00 conftest extension)"
      pattern: "affordability_fixture\\("
    - from: tests/test_affordability.py
      to: scripts/affordability.py
      via: "subprocess invocation (NEVER direct import per Phase 3 D-17)"
      pattern: "subprocess\\.run.*SCRIPT_PATH"
    - from: tests/test_affordability.py
      to: lib/affordability.py
      via: "evaluate() public dispatcher + helper imports"
      pattern: "from lib\\.affordability import"
---

<objective>
Replace the Wave 0 xfail stubs with real assertions; ship the 9 fixtures from D-17; run citation-coverage + lazy-import + 6-key envelope + round-trip closure tests. This plan is the Phase 4 acceptance gate — when this plan ships, AFFD-01..09 are all closed and the 5 ROADMAP success criteria (SC-1..SC-5) are pinned by tests.

Purpose: this is the test surface that makes Phase 4 verifiable. Per Phase 3's amortize_fixture / test_amortize.py shape, every fixture is hand-calculated (or engine-emitted-and-verbatim-pinned per Phase 3 D-04 idiom) with money fields as Decimal-strings; comparisons are exact `==` (D-18 — never assertAlmostEqual or pytest.approx).

Output:
- `tests/test_affordability.py` ~600 lines: 9 AFFD-XX flag-flips (xfail → real) + 5 cross-cutting tests (citation-coverage meta-test, lazy-import D-18, float-gate 6-key, round-trip D-09, joint vs single-applicant equivalence)
- 9 JSON fixtures per D-17 list

Per RESEARCH §"Validation Architecture": this plan ships ALL fixtures from the D-17 named list. Per VALIDATION.md: pytest 7.x, quick run is `pytest tests/test_affordability.py -x --tb=short` (~10s).

Decisions implemented: D-17 (fixture list), D-18 (exact Decimal equality), AFFD-01..09 (every requirement has a passing test), ROADMAP SC-1..SC-5 (verbatim).
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
@.planning/phases/04-affordability/04-VALIDATION.md
@.planning/phases/04-affordability/04-00-test-infrastructure-PLAN.md
@.planning/phases/04-affordability/04-04-blocker-precedence-PLAN.md
@.planning/phases/04-affordability/04-05-cli-and-config-PLAN.md
@CLAUDE.md
@tests/test_amortize.py
@tests/conftest.py
@tests/fixtures/amortize/biweekly_true_200k_6_5.json
@tests/fixtures/golden_pmt.json
@lib/affordability.py
@scripts/affordability.py
@config/household.example.yml

<interfaces>
<!-- Wave 0 stubs (Plan 04-00, currently xfail) — replace bodies with real tests. -->

```python
@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-01 implementation pending (Plan 04-02)")
def test_AFFD_01_dti_calculations() -> None: ...
# ... 9 stubs total
```

<!-- Plan 04-04 public surface -->
```python
def evaluate(request: ForwardModeRequest | ReverseModeRequest) -> AffordabilityResponse
# Plus all BLOCKED_BY_* / WARNING_* constants and TARGET_LOAN_TYPE_CROSSWALK exported
```

<!-- Plan 04-05 CLI surface -->
```python
SCRIPT_PATH = .../scripts/affordability.py
# Subprocess invocation: subprocess.run([sys.executable, str(SCRIPT_PATH), "--input", tmp_path / "x.json"], ...)
```

<!-- Phase 3 reference patterns -->
```python
# tests/test_amortize.py:50-53 — SCRIPT_PATH constant
# tests/test_amortize.py:722-751 — subprocess invocation
# tests/test_amortize.py:754-827 — lazy-import D-18 fresh-Python harness
# tests/test_amortize.py:873-928 — 6-key envelope test for float rejection
# tests/test_amortize.py:56-75 — assert_schedule_invariants helper
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Generate engine-emitted golden values and write the 9 fixture JSON files</name>
  <files>
    tests/fixtures/affordability/forward_conventional_80_ltv.json,
    tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json,
    tests/fixtures/affordability/forward_fha_above_dti_cap.json,
    tests/fixtures/affordability/forward_va_residual_fail.json,
    tests/fixtures/affordability/forward_jumbo_above_county_limit.json,
    tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json,
    tests/fixtures/affordability/joint_applicants_two_incomes.json,
    tests/fixtures/affordability/single_applicant.json,
    tests/fixtures/affordability/household_example_yml_e2e.json
  </files>
  <read_first>
    - tests/fixtures/amortize/biweekly_true_200k_6_5.json (Phase 3 fixture skeleton — use as a starting shape)
    - .planning/phases/04-affordability/04-PATTERNS.md §"tests/fixtures/affordability/*.json" (full per-fixture quick-spec table)
    - .planning/phases/04-affordability/04-CONTEXT.md D-17 (fixture list)
    - .planning/phases/04-affordability/04-RESEARCH.md §"numpy-financial npf.pv Conventions" (worked example for reverse fixture)
    - data/reference/va-residual-income.yml (M26-7 minimum for WEST family-4 — used to set actual_residual_income BELOW the threshold for the va-fail fixture)
    - data/reference/conforming-limits-2026.yml (King WA baseline — used to pick a loan amount > limit for jumbo fixture)
    - data/reference/fha-mip-rates.yml (FHA MIP table — confirm UFMIP + annual rate the fixture will trigger)
  </read_first>
  <action>
    For each fixture:

    1. **Use the engine-as-source-of-truth idiom** (Phase 3 D-04 / 03-04 inheritance): write a temporary Python script that constructs the AffordabilityRequest, calls `evaluate(req)`, prints the response as JSON. Paste the engine-emitted Decimal strings VERBATIM into the fixture's `expected_response` block. Never hand-compute money fields.

    2. **Fixture file shape** (mirrors `tests/fixtures/amortize/biweekly_true_200k_6_5.json`):
       ```json
       {
         "$schema": "https://json-schema.org/draft-07/schema#",
         "id": "<filename_stem>",
         "source": "<ROADMAP SC-N citation OR 'engine-emitted; computed from <D-XX>'>",
         "rounding": "ROUND_HALF_UP",
         "notes": "<hand-calc citation references; what this fixture pins>",
         "request": { ... AffordabilityRequest.model_dump() shape with mode-discriminator ... },
         "expected_response": { ... AffordabilityResponse.model_dump() shape, money as quoted strings ... }
       }
       ```

    3. **Per-fixture spec** (for each, write a temporary generator script, run `evaluate(req)`, paste result):

       **forward_conventional_80_ltv.json** (anchor: matches Phase 1 oracle `computed_400k_30yr` from `golden_pmt.json` for monthly_pi=2528.27):
       - request: forward mode, conventional, $400k loan / $500k property (LTV=0.80), 6.5%/30yr, joint applicants A=720+$5k/B=680+$5k, no debts, escrow all 0, max_dti=0.43
       - expected_response: blocked=False, blocked_by=null, monthly_pi="2528.27", ltv="0.80", cltv="0.80", monthly_mi="0.00", piti="2528.27", warnings=[] (no FHA/VA → no stale warnings)

       **forward_conventional_85_ltv_with_pmi.json**:
       - request: forward conventional, $425k / $500k (LTV=0.85), 6.5%/30yr, monthly_pmi="145.83", same household
       - expected_response: blocked=False (LTV 0.85 < 0.97 ceiling); piti = quantize_cents(monthly_pi + 0 + 0 + 0 + 145.83); warnings contains "HPA-PMI-REQUIRED"

       **forward_fha_above_dti_cap.json**:
       - request: forward FHA, $400k / $415000 (LTV ~0.964 just under 0.965 ceiling), low income to push DTI back > max_dti, max_dti="0.30" (tight)
       - expected_response: blocked=True, blocked_by="DTI-CAP-FHA"; warnings contains stale-warning string from fha-mip-rates.yml + "HPA-PMI-REQUIRED" NOT present (FHA, not conventional)

       **forward_va_residual_fail.json** (ROADMAP SC-3 anchor):
       - request: forward VA, $400k loan, household.va.region="west", family_size=4, actual_residual_income BELOW M26-7 minimum for WEST family-4 (likely $1,117 per data/reference/va-residual-income.yml `table_above_80k.west["4"]: "1117"`); set actual_residual_income="1100.00" (below threshold)
       - expected_response: blocked=True, blocked_by="VA-RESIDUAL-WEST-FAMILY-4" (verbatim from predicate); warnings contains stale-warning string from va-residual-income.yml

       **forward_jumbo_above_county_limit.json**:
       - request: forward conventional in King WA (state_fips="53", county_fips="033"); King WA baseline limit is ~$832,750 per RESEARCH §"data/reference/conforming-limits-2026.yml". Pinned values: `loan_amount="1500000.00"`, `property_value="2000000.00"` (LTV = 1500000/2000000 = 0.75), `monthly_pmi=null`, `target_loan_type="conventional"`. classify returns "jumbo" → cross-walk rejects → blocked_by="FHFA-LIMIT-CONFORMING-53-033"
       - notes block: `"LTV = 1500000/2000000 = 0.75; monthly_pmi=null is valid because LTV ≤ 0.80 falls outside _validate_common's PMI-required band (BLOCKER 3 buildability anchor — fixture must reach evaluate() to exercise the cross-walk blocker, not be rejected at the Pydantic boundary)."`
       - expected_response: blocked=True, blocked_by="FHFA-LIMIT-CONFORMING-53-033"

       **reverse_conventional_80_ltv_43_dti.json** (ROADMAP SC-2 anchor):
       - request: reverse mode, conventional, max_dti="0.430000", down_payment="100000.00", target_ltv_pct="0.800000", 7%/30yr, joint income $10k, no debts, escrow all 0
       - expected_response: blocked=False, mode="reverse", max_loan_amount=<engine-emitted>, implied_pi=<engine-emitted>, assumed_ltv_pct="0.800000", assumed_monthly_mi="0.00"
       - Test side: round-trip closure (forward(reverse(req)).dti_back <= 0.43 + 0.0001; loan_amount == max_loan_amount exactly)

       **joint_applicants_two_incomes.json** (SC-5 anchor + BLOCKER 2 divergence demonstration):
       - request: forward conv 80% with applicants=[A:credit 720+$6000, B:credit 680+$4000]; total income $10k, min credit 680. Pinned `household.size=4` (a household of 4: 2 applicants + 2 non-applicant dependents). This intentionally exercises `size != len(applicants)` per BLOCKER 2 fix — `lib.rules.usda.evaluate` and any future household-size-keyed rules MUST read `request.household.size` directly and never infer from `len(applicants)`.
       - expected_response: total_gross_monthly_income="10000.00", any soft warning related to credit_score uses fico_bucket="660-679" or "680-699" (depending on min_credit_score=680 → bucket "680-699")

       **single_applicant.json** (SC-5 anchor; len==1 case):
       - request: forward conv 80% with applicants=[A:credit 720+$10000]; total income $10k, min credit 720
       - expected_response: same code path; total_gross_monthly_income="10000.00"

       **household_example_yml_e2e.json** (SC-4 anchor):
       - This fixture is an "invocation manifest" — Plan 04-06 generates a request JSON from config/household.example.yml at TEST-TIME (loads YAML, fills in non-zero example values, writes JSON to tmp_path); the fixture itself contains the EXPECTED response shape (after non-zero values fill in). To keep this stable, the fixture instead contains a "synthetic request" derived from household.example.yml's example values plus testing-friendly placeholder values for the 0.00 fields (e.g., gross_monthly_income="5000.00" instead of "0.00").
       - Specifically: the fixture's `request` field is a complete forward-mode JSON request that uses the example.yml's location.state_fips ("53"), county_fips ("033"), but fills `gross_monthly_income`, `credit_score`, `monthly_debts`, `escrow.property_tax_monthly`, `escrow.insurance_monthly`, `escrow.hoa_monthly` with non-zero example values; target_loan_type="conventional" (so the va: block is unused); loan_amount + property_value pinned for a clean pass.
       - expected_response: blocked=False; full Pydantic schema match.

    4. **Fixture money discipline**: ALL Decimal-typed fields are quoted JSON strings. Phase 4's request schema fields (loan_amount, property_value, monthly_pmi, gross_monthly_income, max_dti, target_ltv_pct, annual_rate, escrow.{property_tax_monthly, insurance_monthly, hoa_monthly}, va.actual_residual_income, junior_liens elements, monthly_debts.* fields, current_housing_payment) are STRINGS. term_months, family_size, credit_score, applicants[].... are integers.

    5. **Generator pseudocode (executor uses this pattern):**
       ```python
       # /tmp/gen-fixture-XX.py
       from decimal import Decimal
       from lib.affordability import (
           evaluate, ForwardModeRequest, Household, LocationFIPS,
           Applicant, MonthlyDebts, EscrowInputs, VAInputs,
       )
       req = ForwardModeRequest(...)
       resp = evaluate(req)
       print(resp.model_dump_json(indent=2))
       # paste output verbatim into fixture's "expected_response" block.
       ```

    Save the generator scripts to /tmp/ during execution; do NOT commit them.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for f in forward_conventional_80_ltv forward_conventional_85_ltv_with_pmi forward_fha_above_dti_cap forward_va_residual_fail forward_jumbo_above_county_limit forward_missing_county_data reverse_conventional_80_ltv_43_dti joint_applicants_two_incomes single_applicant household_example_yml_e2e; do test -f "tests/fixtures/affordability/${f}.json" || { echo "MISSING: $f"; exit 1; }; done &amp;&amp; uv run python -c "
import json
from pathlib import Path
fixtures_dir = Path('tests/fixtures/affordability')
for fp in sorted(fixtures_dir.glob('*.json')):
    data = json.loads(fp.read_text())
    assert 'request' in data, f'{fp}: missing request'
    assert 'expected_response' in data, f'{fp}: missing expected_response'
    assert 'rounding' in data and data['rounding'] == 'ROUND_HALF_UP'
    assert 'source' in data
    print(f'OK: {fp.name}')
print('all fixtures parse')
"</automated>
  </verify>
  <acceptance_criteria>
    - All 10 fixture files exist under tests/fixtures/affordability/ (9 from D-17 + forward_missing_county_data.json from BLOCKER 1)
    - Every fixture has top-level `\$schema`, `id`, `source`, `rounding: "ROUND_HALF_UP"`, `notes`, `request`, `expected_response` keys
    - tests/fixtures/affordability/forward_va_residual_fail.json contains literal substring `"VA-RESIDUAL-WEST-FAMILY-4"` (ROADMAP SC-3 verbatim)
    - tests/fixtures/affordability/forward_va_residual_fail.json `request.target_loan_type == "va"` AND `request.household.va.region == "west"` AND `request.household.va.family_size == 4`
    - tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json `request.mode == "reverse"` AND `request.target_ltv_pct == "0.800000"` AND `request.max_dti == "0.430000"`
    - tests/fixtures/affordability/forward_conventional_80_ltv.json `expected_response.monthly_pi == "2528.27"` (Phase 1 / Phase 3 oracle anchor)
    - tests/fixtures/affordability/forward_fha_above_dti_cap.json `expected_response.blocked_by` matches regex `^DTI-CAP-FHA$`
    - tests/fixtures/affordability/forward_jumbo_above_county_limit.json `expected_response.blocked_by` starts with `"FHFA-LIMIT-"`
    - tests/fixtures/affordability/joint_applicants_two_incomes.json `request.household.applicants` has length 2; tests/fixtures/affordability/single_applicant.json has length 1
    - All fixture money fields are quoted strings (not bare numbers): grep `'-?\d+\.\d{2}[^"]\|^-?\d+\.\d{2}'` returns 0 matches across the 10 files (except line numbers / array indices)
    - Every fixture's `request.household` contains a `size` integer field >= 1 (BLOCKER 2 acceptance): inline-Python check iterates fixtures and asserts `data["request"]["household"]["size"] >= 1` for all 10 fixtures
    - tests/fixtures/affordability/forward_missing_county_data.json contains literal substring `"county_fips": "999"` (BLOCKER 1 fixture; nonexistent FIPS triggers MissingCountyDataError)
    - tests/fixtures/affordability/forward_jumbo_above_county_limit.json contains literal substring `"property_value": "2000000.00"` (BLOCKER 3 LTV-pinning anchor)
    - tests/fixtures/affordability/forward_jumbo_above_county_limit.json contains literal substring `"loan_amount": "1500000.00"` (BLOCKER 3 LTV-pinning anchor)
    - tests/fixtures/affordability/forward_jumbo_above_county_limit.json `request.monthly_pmi` is null (BLOCKER 3 buildability anchor: LTV=0.75 ≤ 0.80 outside _validate_common's PMI-required band; documented in fixture `notes` block)
    - tests/fixtures/affordability/joint_applicants_two_incomes.json `request.household.size > len(request.household.applicants)` (BLOCKER 2 divergence demonstration: size=4, len(applicants)=2)
    - All 9 fixtures parse via json.load + match the inline-Python schema check (no missing required keys)
    - YAML schema parses cleanly: `uv run python -c "import json; [json.loads(open(f'tests/fixtures/affordability/{f}.json').read()) for f in ['forward_conventional_80_ltv', ...]]"` exits 0
  </acceptance_criteria>
  <done>
    9 fixtures committed; ROADMAP SC-2/SC-3/SC-4/SC-5 anchors pinned; all money fields quoted Decimal strings; engine-emitted values pasted verbatim per Phase 3 D-04 idiom.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace Wave 0 xfail stubs with real tests + add cross-cutting tests (citation coverage, lazy-import, float-gate, round-trip)</name>
  <files>tests/test_affordability.py</files>
  <read_first>
    - tests/test_affordability.py (Plan 04-00 state — 9 xfail stubs with structured reasons)
    - tests/test_amortize.py (full file — analog patterns: lazy-import, 6-key envelope, subprocess, fixture loader)
    - lib/affordability.py (Plan 04-04 final — public surface)
    - .planning/phases/04-affordability/04-PATTERNS.md §"tests/test_affordability.py" (test patterns + verbatim assertions)
    - .planning/phases/04-affordability/04-RESEARCH.md §"Validation Architecture" (test dimensions + sampling rate)
    - .planning/phases/04-affordability/04-CONTEXT.md D-17 (fixture list) + D-18 (exact equality)
  </read_first>
  <behavior>
    - Test 1 (AFFD-01 DTI): For forward_conventional_80_ltv fixture, evaluate(req).dti_front and dti_back match expected_response exactly via Decimal equality
    - Test 2 (AFFD-02 LTV): Same fixture, evaluate(req).ltv == Decimal("0.80") exactly
    - Test 3 (AFFD-03 CLTV): Construct request with junior_liens=["50000.00"]; evaluate(req).cltv > evaluate_no_juniors(req).ltv
    - Test 4 (AFFD-04 PITI): For forward_conventional_85_ltv_with_pmi, piti = quantize_cents(monthly_pi + tax + ins + hoa + monthly_pmi) verified by reading expected_response
    - Test 5 (AFFD-05 reverse + round-trip): reverse_conventional_80_ltv_43_dti round-trips: forward(ForwardModeRequest(loan_amount=resp.max_loan_amount, property_value=resp.max_loan_amount/req.target_ltv_pct, ...)).dti_back <= req.max_dti + Decimal("0.0001"); forward.loan_amount == resp.max_loan_amount exactly (D-09)
    - Test 6 (AFFD-06 joint applicants): joint_applicants_two_incomes: total_gross_monthly_income == sum; min_credit_score selected
    - Test 7 (AFFD-07 VA-residual blocked_by VERBATIM): forward_va_residual_fail: response.blocked_by == "VA-RESIDUAL-WEST-FAMILY-4" (verbatim per ROADMAP SC-3)
    - Test 8 (AFFD-08 CLI smoke): subprocess invocation of scripts/affordability.py with each fixture's request as input; subprocess.run check=True; output JSON matches expected_response shape
    - Test 9 (AFFD-09 household.example.yml e2e): household_example_yml_e2e fixture invokes subprocess against the example.yml-derived request; full round-trip
    - Test 10 (single-applicant code path equivalence): single_applicant fixture passes the same code path as joint (both go through evaluate_forward + same helper layer)
    - Test 11 (citation coverage): introspect lib/affordability.py for all `BLOCKED_BY_*` Final[str] constants; assert each appears in at least one fixture's `expected_response.blocked_by` (or, for templates with `{LOAN_TYPE}` placeholders, regex match against fixtures)
    - Test 12 (VA citation regex coverage): at least one fixture's blocked_by matches r"^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$"
    - Test 13 (D-18 lazy --help; Phase 3 03-04 idiom): subprocess fresh-Python harness verifies lib.affordability NOT in sys.modules AND numpy_financial NOT in sys.modules after `--help`
    - Test 14 (6-key envelope; Phase 3 03-06 idiom): subprocess invocation with a JSON containing `"loan_amount": 400000.00` (JSON float, not string) → returncode 2; stderr is JSON list with 6-key envelope (type, loc, msg, input, url, ctx); url starts with "https://errors.pydantic.dev/" and ends with "/v/decimal_type"
    - Test 15 (file-not-found envelope): subprocess with `--input /nonexistent` → returncode 2; stderr contains `"error":` (simpler shape per Phase 3)
    - Test 16 (--help fast): time-bounded test (subprocess --help completes in < 2 seconds — generous bound; Phase 3 03-04's harness used 150ms; Phase 4 should be similar but allow margin for CI)
    - Test 17 (Pydantic ValidationError 6-key envelope): subprocess invocation with valid JSON shape but invalid data (e.g., target_loan_type="va" without va: block) → returncode 2; stderr is JSON list with 6 keys; type=value_error; msg contains "household.va block is required when target_loan_type=='va'"
    - Test 18 (round-trip dollar equality): for the SC-2 fixture, after round-trip closure, forward.loan_amount == reverse.max_loan_amount exactly (no tolerance — D-09 says dollars are exact, only DTI rate has 0.0001 tolerance)
    - Test 19 (BLOCKER 1 — MissingCountyDataError envelope): subprocess invocation with `forward_missing_county_data.json` returns exit code 2; stderr is JSON list with one 6-key envelope; envelope[0]["ctx"]["class"] == "MissingCountyDataError"; envelope[0]["type"] == "value_error"; envelope[0]["loc"] == ["household", "location"]
    - Test 20 (BLOCKER 4 — VA region × family_size grid): @pytest.mark.parametrize over 12 cells (4 regions × {1, 4, 5}); for each (region, family_size), construct a forward VA request that fails residual (actual_residual_income below the M26-7 minimum for that cell), call evaluate(req), and assert response.blocked_by == f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}" verbatim (Phase 2 D-11 stable format; VALIDATION.md §1 boundary coverage)
    - Test 21 (BLOCKER 4 — FHA MIP table grid): @pytest.mark.parametrize over 4 cells (loan_amount ∈ {"400000.00", "800000.00"} × ltv_pct ∈ {"0.95", "0.965"}); for each (loan, ltv), construct a forward FHA request and assert response.monthly_mi is non-None + > 0; per VALIDATION.md §1 each table cell produces a monthly_mi
    - Test 22 (BLOCKER 4 — LTV ceiling boundary grid): @pytest.mark.parametrize over 6 loan_types {conventional, conventional_ftb (alias for conventional v1 — see Note A1), fha, va, usda, jumbo} × {at-ceiling, ceiling+0.0001}; for each, construct a forward request at the exact ceiling LTV and at ceiling+0.0001; assert at-ceiling case is NOT blocked by LTV-CEILING; ceiling+0.0001 case IS blocked with `LTV-CEILING-{LOAN_TYPE_UPPER}` citation. Note: jumbo ceiling is 1.00 (no v1 enforcement) so ceiling+0.0001 case for jumbo is skipped via pytest.skip (or parametrize id includes "jumbo-skipped"); conventional_ftb collapses to conventional in v1 per RESEARCH Assumption A1 — duplicate test cell is acceptable.
  </behavior>
  <action>
    Edit `tests/test_affordability.py`. Replace the 9 xfail stubs with real test bodies; add 9 new cross-cutting tests. Final structure:

    **A. Update imports** (replace Wave 0 imports — add real imports now that lib/affordability + scripts/affordability exist):
    ```python
    from __future__ import annotations

    import importlib.util
    import json
    import re
    import subprocess
    import sys
    from decimal import Decimal
    from pathlib import Path
    from typing import TYPE_CHECKING, Any

    import pytest
    from pydantic import TypeAdapter

    from lib.affordability import (
        AffordabilityRequest,
        AffordabilityResponse,
        ForwardModeRequest,
        ReverseModeRequest,
        Household,
        LocationFIPS,
        Applicant,
        MonthlyDebts,
        EscrowInputs,
        VAInputs,
        evaluate,
        evaluate_forward,
        evaluate_reverse,
        BLOCKED_BY_ATR_QM_PRICE_FIRST,
        BLOCKED_BY_CLTV_CEILING_TEMPLATE,
        BLOCKED_BY_DTI_CAP_TEMPLATE,
        BLOCKED_BY_LTV_CEILING_TEMPLATE,
        BLOCKED_BY_USDA_INCOME_TEMPLATE,
        BLOCKED_BY_VA_RESIDUAL_PATTERN,
        WARNING_HPA_PMI_REQUIRED,
    )

    if TYPE_CHECKING:
        from collections.abc import Callable
    ```

    **B. SCRIPT_PATH + AFFORDABILITY_MODULE_PATH constants** preserved from Wave 0 (no change).

    **C. Helper to construct a request from a fixture's `request` block:**
    ```python
    def _build_request_from_fixture(fixture_request: dict[str, Any]) -> AffordabilityRequest:
        """Validate a fixture's request block via the Phase 4 discriminated union.

        Per Plan 04-05: AffordabilityRequest is Annotated[ForwardModeRequest |
        ReverseModeRequest, Field(discriminator="mode")]. TypeAdapter is the
        Pydantic v2 idiom for non-class types.
        """
        adapter = TypeAdapter(AffordabilityRequest)
        return adapter.validate_python(fixture_request)
    ```

    **D. Replace each Wave 0 stub** — remove `@pytest.mark.xfail` and `raise NotImplementedError`; insert real assertions.

    Example Test 7 (the SC-3 VA-residual verbatim test):
    ```python
    def test_AFFD_07_blocked_by_va_residual_west_family_4(
        affordability_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """AFFD-07 + ROADMAP SC-3: VA WEST family-4 residual fail emits the
        Phase 2 D-11 stable citation VERBATIM."""
        fx = affordability_fixture("forward_va_residual_fail")
        req = _build_request_from_fixture(fx["request"])
        resp = evaluate(req)
        # ROADMAP SC-3 verbatim
        assert resp.blocked is True
        assert resp.blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"
        # Citation matches the regex pattern (Phase 2 D-11 format)
        assert re.match(BLOCKED_BY_VA_RESIDUAL_PATTERN, resp.blocked_by) is not None
        # Decimal-equality check on expected_response keys
        expected = fx["expected_response"]
        assert resp.blocked_by == expected["blocked_by"]
    ```

    Example Test 5 (the SC-2 round-trip closure test):
    ```python
    def test_AFFD_05_reverse_round_trip(
        affordability_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """AFFD-05 + ROADMAP SC-2: reverse → forward closure within Decimal('0.0001')
        DTI tolerance (D-09); dollar amounts equal exactly (D-18)."""
        fx = affordability_fixture("reverse_conventional_80_ltv_43_dti")
        rev_req = _build_request_from_fixture(fx["request"])
        assert isinstance(rev_req, ReverseModeRequest)
        rev_resp = evaluate(rev_req)
        assert rev_resp.mode == "reverse"
        assert rev_resp.max_loan_amount is not None
        assert rev_resp.assumed_ltv_pct == rev_req.target_ltv_pct
        # Round-trip: build forward request from reverse output
        derived_property_value = rev_resp.max_loan_amount / rev_req.target_ltv_pct
        fwd_req = ForwardModeRequest(
            mode="forward",
            household=rev_req.household,
            max_dti=rev_req.max_dti,
            target_loan_type=rev_req.target_loan_type,
            term_months=rev_req.term_months,
            annual_rate=rev_req.annual_rate,
            apr=rev_req.apr,
            apor=rev_req.apor,
            monthly_pmi=rev_req.monthly_pmi,
            endorsement_date_override=rev_req.endorsement_date_override,
            junior_liens=rev_req.junior_liens,
            loan_amount=rev_resp.max_loan_amount,
            property_value=derived_property_value,
        )
        fwd_resp = evaluate(fwd_req)
        # D-09 closure: dti_back <= max_dti + Decimal('0.0001')
        assert fwd_resp.dti_back is not None
        assert fwd_resp.dti_back - rev_req.max_dti <= Decimal("0.0001")
        # D-18 dollar exact equality
        assert fwd_resp.loan_amount == rev_resp.max_loan_amount
    ```

    Example Test 13 (D-18 lazy-import; mirror tests/test_amortize.py:754-827):
    ```python
    def test_cli_help_does_not_import_lib_affordability() -> None:
        """D-18 (Phase 3 03-04 idiom): --help must not trigger lib.affordability
        or numpy_financial import.

        Spawn a fresh Python subprocess (so neither is already imported via this
        test module's top-level imports) and run an inline check that loads
        scripts/affordability.py via importlib.util.spec_from_file_location with
        sys.argv patched to --help.
        """
        project_root = Path(__file__).resolve().parent.parent
        inline = (
            "import importlib.util, sys, json\n"
            f"sys.path.insert(0, {str(project_root)!r})\n"
            f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
            "spec = importlib.util.spec_from_file_location('scripts_affordability', SCRIPT)\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "sys.modules['scripts_affordability'] = module\n"
            "spec.loader.exec_module(module)\n"
            "sys.argv = ['affordability', '--help']\n"
            "try:\n"
            "    module.main()\n"
            "except SystemExit as e:\n"
            "    exit_code = e.code\n"
            "else:\n"
            "    exit_code = 0\n"
            "result = {\n"
            "    'help_exit_code': exit_code,\n"
            "    'lib_affordability_imported': 'lib.affordability' in sys.modules,\n"
            "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
            "}\n"
            "print(json.dumps(result))\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", inline],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        assert payload["help_exit_code"] == 0
        assert payload["lib_affordability_imported"] is False
        assert payload["numpy_financial_imported"] is False
    ```

    Example Test 14 (6-key envelope; mirror tests/test_amortize.py:873-928):
    ```python
    def test_cli_rejects_float_in_loan_amount(tmp_path: Path) -> None:
        """D-19 + WR-02 inheritance: pre-validation gate emits 6-key envelope."""
        bad = tmp_path / "float.json"
        bad.write_text(
            '{"mode": "forward",'
            '"household": {"location": {"state": "WA", "state_fips": "53", '
            '"county_fips": "033", "county_name": "King", "zip": "98101"}, '
            '"applicants": [{"name":"A","gross_monthly_income":"5000.00","credit_score":720}], '
            '"monthly_debts": {}, '
            '"escrow": {"property_tax_monthly":"0.00","insurance_monthly":"0.00","hoa_monthly":"0.00"}}, '
            '"max_dti":"0.43","target_loan_type":"conventional","term_months":360,'
            '"annual_rate":"0.065","loan_amount": 400000.00,'  # JSON float — should reject
            '"property_value":"500000.00"}'
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2
        errors = json.loads(result.stderr)
        err = errors[0]
        assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
        assert err["type"] == "decimal_type"
        assert err["loc"] == ["loan_amount"]
        assert err["url"].startswith("https://errors.pydantic.dev/")
        assert err["url"].endswith("/v/decimal_type")
        assert err["ctx"].get("class") == "Decimal"
    ```

    Example Test 11 (citation coverage):
    ```python
    def test_blocked_by_citation_coverage() -> None:
        """RUL-12/13 inheritance: every BLOCKED_BY_* template introduced in
        lib/affordability.py is exercised by at least one fixture."""
        fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "affordability"
        all_blocked_by: list[str | None] = []
        for fp in sorted(fixtures_dir.glob("*.json")):
            data = json.loads(fp.read_text())
            all_blocked_by.append(data["expected_response"].get("blocked_by"))

        # Every non-VA template format must appear in at least one fixture.
        # Templates use {LOAN_TYPE} placeholder; we strip and substring-match.
        templates_to_check = [
            BLOCKED_BY_LTV_CEILING_TEMPLATE,   # LTV-CEILING-{LOAN_TYPE}
            BLOCKED_BY_DTI_CAP_TEMPLATE,       # DTI-CAP-{LOAN_TYPE}
            # CLTV-CEILING is optional; skip if no junior-lien fixture exercises it
        ]
        for tpl in templates_to_check:
            prefix = tpl.split("{")[0]  # "LTV-CEILING-" or "DTI-CAP-"
            assert any(
                bb is not None and bb.startswith(prefix)
                for bb in all_blocked_by
            ), f"No fixture exercises citation template: {tpl}"

        # FHFA-LIMIT-* (loan-type-classify mismatch) — substring "FHFA-LIMIT-"
        assert any(bb is not None and bb.startswith("FHFA-LIMIT-") for bb in all_blocked_by), \
            "No fixture exercises FHFA-LIMIT-* citation"

        # VA-residual regex
        va_pattern = re.compile(BLOCKED_BY_VA_RESIDUAL_PATTERN)
        assert any(bb is not None and va_pattern.match(bb) for bb in all_blocked_by), \
            "No fixture exercises VA-RESIDUAL-{REGION}-FAMILY-{N} citation pattern"
    ```

    All other test bodies follow the same pattern: load fixture → build request → call evaluate() OR subprocess → assert response shape + Decimal equality.

    **E. BLOCKER 4 boundary-parametrize tests** (VALIDATION.md §1 coverage):

    ```python
    # BLOCKER 4 fix — VA region × family_size coverage (12 cells)
    @pytest.mark.parametrize("region,family_size", [
        ("northeast", 1), ("northeast", 4), ("northeast", 5),
        ("midwest", 1),   ("midwest", 4),   ("midwest", 5),
        ("south", 1),     ("south", 4),     ("south", 5),
        ("west", 1),      ("west", 4),      ("west", 5),
    ])
    def test_va_residual_citation_format(region: str, family_size: int) -> None:
        """BLOCKER 4 — Asserts VA-residual binding citation = f'VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}' verbatim (Phase 2 D-11 stable format).

        Each test constructs a forward VA request with actual_residual_income
        BELOW the M26-7 minimum for the (region, family_size) cell — pulling
        the threshold from data/reference/va-residual-income.yml at test-time.
        Asserts response.blocked_by matches the verbatim format (no string
        formatting drift from Phase 2 predicate).
        """
        # 1) Load M26-7 minimum for cell from reference YAML
        import yaml as _yaml
        ref_path = Path(__file__).resolve().parent.parent / "data" / "reference" / "va-residual-income.yml"
        ref = _yaml.safe_load(ref_path.read_text())
        # The reference structure is documented in lib/rules/va_residual_income.py;
        # executor must match the exact key path used by the predicate.
        # Below is illustrative — executor pins to actual YAML structure at test-time.
        threshold = _lookup_va_threshold(ref, region, family_size, loan_amount=Decimal("400000.00"))
        actual = threshold - Decimal("100.00")  # below threshold → fail

        # 2) Build a passing-otherwise request (target=va, all other gates clean)
        household = Household(
            location=LocationFIPS(state="WA", state_fips="53", county_fips="033",
                                  county_name="King", zip="98101"),
            applicants=[Applicant(name="A", gross_monthly_income=Decimal("12000.00"), credit_score=720)],
            size=max(family_size, 1),
            monthly_debts=MonthlyDebts(),
            escrow=EscrowInputs(property_tax_monthly=Decimal("0.00"),
                                insurance_monthly=Decimal("0.00"),
                                hoa_monthly=Decimal("0.00")),
            va=VAInputs(region=region, family_size=family_size, actual_residual_income=actual),
        )
        req = ForwardModeRequest(
            mode="forward", household=household,
            max_dti=Decimal("0.430000"), target_loan_type="va",
            term_months=360, annual_rate=Decimal("0.070000"),
            loan_amount=Decimal("400000.00"), property_value=Decimal("500000.00"),
        )
        resp = evaluate(req)
        # VERBATIM Phase 2 D-11 citation
        expected = f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"
        assert resp.blocked is True, f"expected blocked for {expected}; got blocked_by={resp.blocked_by}"
        assert resp.blocked_by == expected, f"format drift: got {resp.blocked_by} expected {expected}"


    # BLOCKER 4 fix — FHA MIP table coverage (4 cells)
    @pytest.mark.parametrize("loan_amount,property_value,ltv_label", [
        ("400000.00", "421000.00", "<=726200/<=95"),    # ≤ $726,200 / ≤95% LTV (LTV ~0.95)
        ("400000.00", "414500.00", "<=726200/>95"),     # ≤ $726,200 / >95% LTV (LTV ~0.965)
        ("800000.00", "842000.00", ">726200/<=95"),     # > $726,200 / ≤95% LTV (LTV ~0.95)
        ("800000.00", "829000.00", ">726200/>95"),      # > $726,200 / >95% LTV (LTV ~0.965)
    ])
    def test_fha_mip_compute_per_table_row(loan_amount: str, property_value: str, ltv_label: str) -> None:
        """BLOCKER 4 — confirms each FHA MIP table cell produces a non-None monthly_mi in PITI.

        VALIDATION.md §1 requires coverage of all 4 cells of the FHA MIP table
        (HUD ML 2023-05). Per RESEARCH §A.3, fha_mip.compute returns ufmip + annual_mip.
        Phase 4 derives monthly_mi = quantize_cents((financed_principal × annual_mip_pct) / 12).
        Cell-specific values are pinned by Plan 04-06 fixtures or computed at test-time.
        """
        household = Household(
            location=LocationFIPS(state="WA", state_fips="53", county_fips="033",
                                  county_name="King", zip="98101"),
            applicants=[Applicant(name="A", gross_monthly_income=Decimal("15000.00"), credit_score=720)],
            size=2,
            monthly_debts=MonthlyDebts(),
            escrow=EscrowInputs(property_tax_monthly=Decimal("0.00"),
                                insurance_monthly=Decimal("0.00"),
                                hoa_monthly=Decimal("0.00")),
        )
        req = ForwardModeRequest(
            mode="forward", household=household,
            max_dti=Decimal("0.430000"), target_loan_type="fha",
            term_months=360, annual_rate=Decimal("0.070000"),
            loan_amount=Decimal(loan_amount), property_value=Decimal(property_value),
        )
        resp = evaluate(req)
        assert resp.monthly_mi is not None, f"FHA MIP cell {ltv_label}: monthly_mi must be non-None per HUD ML 2023-05"
        assert resp.monthly_mi > Decimal("0"), f"FHA MIP cell {ltv_label}: monthly_mi must be > 0"


    # BLOCKER 4 fix — LTV ceiling boundary coverage (6 loan_types × 2 boundary cases)
    @pytest.mark.parametrize("target_loan_type,ceiling", [
        ("conventional", Decimal("0.97")),
        ("fha",          Decimal("0.965")),
        ("va",           Decimal("1.00")),
        ("usda",         Decimal("1.00")),
        ("jumbo",        Decimal("1.00")),
    ])
    @pytest.mark.parametrize("offset,blocked_expected", [
        (Decimal("0"),       False),    # at-ceiling — NOT blocked
        (Decimal("0.0001"),  True),     # ceiling + 0.0001 — IS blocked (except jumbo, see skip below)
    ])
    def test_ltv_ceiling_boundary(
        target_loan_type: str, ceiling: Decimal, offset: Decimal, blocked_expected: bool,
    ) -> None:
        """BLOCKER 4 — LTV ceiling boundary per loan_type.

        Per RESEARCH §"LTV / CLTV Ceiling Authority" + Plan 04-04 LTV_CEILING_BY_TARGET.
        For target=jumbo, ceiling=1.00 has no v1 enforcement — skip the over-ceiling case
        (RESEARCH Assumption A1).
        """
        if target_loan_type == "jumbo" and offset > Decimal("0"):
            pytest.skip("jumbo ceiling 1.00 has no v1 enforcement (RESEARCH A1)")

        ltv_target = ceiling + offset
        # Build request with property_value = loan_amount / ltv_target
        loan_amount = Decimal("400000.00")
        property_value = (loan_amount / ltv_target).quantize(Decimal("0.01"))

        # Build household + (va block if required)
        location = LocationFIPS(state="WA", state_fips="53", county_fips="033",
                                county_name="King", zip="98101")
        applicants = [Applicant(name="A", gross_monthly_income=Decimal("15000.00"), credit_score=720)]
        kwargs: dict[str, Any] = dict(
            location=location, applicants=applicants, size=2,
            monthly_debts=MonthlyDebts(),
            escrow=EscrowInputs(property_tax_monthly=Decimal("0.00"),
                                insurance_monthly=Decimal("0.00"),
                                hoa_monthly=Decimal("0.00")),
        )
        if target_loan_type == "va":
            kwargs["va"] = VAInputs(region="west", family_size=2,
                                    actual_residual_income=Decimal("9999.00"))  # high enough to pass

        household = Household(**kwargs)
        # monthly_pmi required when conventional + LTV > 0.80
        monthly_pmi: Decimal | None = (
            Decimal("250.00") if target_loan_type == "conventional" and ltv_target > Decimal("0.80") else None
        )
        req = ForwardModeRequest(
            mode="forward", household=household,
            max_dti=Decimal("0.99"),  # generous so DTI doesn't fire first
            target_loan_type=target_loan_type, term_months=360,
            annual_rate=Decimal("0.070000"), monthly_pmi=monthly_pmi,
            loan_amount=loan_amount, property_value=property_value,
        )
        resp = evaluate(req)
        if blocked_expected:
            assert resp.blocked is True
            assert resp.blocked_by == f"LTV-CEILING-{target_loan_type.upper()}", (
                f"target={target_loan_type} offset={offset}: expected LTV-CEILING-{target_loan_type.upper()}, got {resp.blocked_by}"
            )
        else:
            # At-ceiling case — must NOT be blocked by LTV-CEILING (other gates may still fire,
            # so check the specific citation, not just `not blocked`).
            if resp.blocked_by is not None:
                assert not resp.blocked_by.startswith("LTV-CEILING-"), (
                    f"target={target_loan_type} at ceiling {ceiling}: should not block on LTV-CEILING; got {resp.blocked_by}"
                )
    ```

    **F. BLOCKER 1 Test 19 — MissingCountyDataError envelope subprocess test:**

    ```python
    def test_cli_missing_county_data_emits_six_key_envelope(
        affordability_fixture: Callable[[str], dict[str, Any]],
        tmp_path: Path,
    ) -> None:
        """BLOCKER 1 fix — when household.location.county_fips is not in
        data/reference/conforming-limits-2026.yml AND loan_amount > baseline,
        scripts/affordability.py main() catches MissingCountyDataError and emits
        the Phase 3 D-19 6-key envelope (instead of a Python traceback).
        """
        fx = affordability_fixture("forward_missing_county_data")
        request_path = tmp_path / "missing_county.json"
        request_path.write_text(json.dumps(fx["request"]))
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 2, f"expected exit 2, got {result.returncode}; stderr={result.stderr}"
        errors = json.loads(result.stderr)
        assert isinstance(errors, list) and len(errors) == 1
        err = errors[0]
        assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}, f"keys={set(err.keys())}"
        assert err["type"] == "value_error"
        assert err["loc"] == ["household", "location"]
        assert err["ctx"]["class"] == "MissingCountyDataError"
        # Per fixture's expected_stderr_envelope contract
        for k, v in fx["expected_stderr_envelope"][0].items():
            if k == "ctx":
                for ck, cv in v.items():
                    assert err["ctx"][ck] == cv
            else:
                assert err[k] == v
    ```

    **G. W5 — test_cli_rejects_float_in_loan_amount docstring update:**

    The existing Test 14 example (`test_cli_rejects_float_in_loan_amount`) uses
    `property_value=500000.00` so LTV = 400000/500000 = 0.80 exactly (NOT > 0.80),
    which means `monthly_pmi=None` passes `_validate_common`. Add a docstring
    comment noting this:

    ```python
    def test_cli_rejects_float_in_loan_amount(tmp_path: Path) -> None:
        """D-19 + WR-02 inheritance: pre-validation gate emits 6-key envelope.

        # W5 fix: property_value=500000 makes LTV=0.80 exactly (NOT >0.80) so
        # monthly_pmi=None passes _validate_common — the test exercises the
        # float-gate, not the conditional monthly_pmi validator. For the
        # complementary case where LTV>0.80 with monthly_pmi=null raises
        # ValidationError, see test_cli_rejects_missing_monthly_pmi_when_required
        # (added below).
        """
        # ... existing body ...


    def test_cli_rejects_missing_monthly_pmi_when_required(tmp_path: Path) -> None:
        """W5 fix — companion to Test 14: LTV=0.81 + conventional + monthly_pmi=null
        triggers the conditional monthly_pmi validator from Plan 04-01 _validate_common.
        Asserts the 6-key envelope on stderr (Pydantic ValidationError path)."""
        bad = tmp_path / "missing_pmi.json"
        bad.write_text(
            '{"mode":"forward",'
            '"household":{"location":{"state":"WA","state_fips":"53","county_fips":"033",'
            '"county_name":"King","zip":"98101"},'
            '"applicants":[{"name":"A","gross_monthly_income":"5000.00","credit_score":720}],'
            '"size":1,'
            '"monthly_debts":{"auto":"0.00","student_loans":"0.00","credit_cards":"0.00","other":"0.00"},'
            '"escrow":{"property_tax_monthly":"0.00","insurance_monthly":"0.00","hoa_monthly":"0.00"}},'
            '"max_dti":"0.43","target_loan_type":"conventional","term_months":360,'
            '"annual_rate":"0.065","loan_amount":"405000.00","property_value":"500000.00",'
            '"monthly_pmi":null}'
        )  # LTV = 405000/500000 = 0.81 > 0.80 — conditional validator must fire
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 2
        errors = json.loads(result.stderr)
        assert any(
            "monthly_pmi" in (e.get("msg") or "") or "monthly_pmi" in str(e.get("loc"))
            for e in errors
        ), f"expected monthly_pmi-related ValidationError; got {errors}"
    ```

    **Note on Test 19 / Test 20-22 placement**: insert the BLOCKER 4 parametrize tests + Test 19 + W5 companion AFTER the existing AFFD-XX tests but BEFORE the citation-coverage meta-test, so the citation-coverage test sees all citations after they've been exercised.

    **Helper for Test 20 (_lookup_va_threshold)**: implement as a small private helper at the top of test_affordability.py that walks data/reference/va-residual-income.yml's nested structure (regions × loan-amount-tier × family_size). Pin the YAML key path to whatever lib.rules.va_residual_income.evaluate uses internally — read the predicate source as part of the implementation.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest tests/test_affordability.py -x --tb=short 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - tests/test_affordability.py exists with >= 600 lines
    - tests/test_affordability.py contains literal substring `def test_AFFD_07_blocked_by_va_residual_west_family_4`
    - tests/test_affordability.py contains literal substring `"VA-RESIDUAL-WEST-FAMILY-4"` (ROADMAP SC-3 verbatim)
    - tests/test_affordability.py contains literal substring `def test_AFFD_05_reverse_round_trip` AND substring `Decimal("0.0001")` (D-09 closure)
    - tests/test_affordability.py contains literal substring `def test_blocked_by_citation_coverage` (RUL-12/13 inheritance)
    - tests/test_affordability.py contains literal substring `def test_cli_help_does_not_import_lib_affordability` (D-18 lazy-import)
    - tests/test_affordability.py contains literal substring `def test_cli_rejects_float_in_loan_amount` (6-key envelope)
    - tests/test_affordability.py contains literal substring `def test_cli_missing_county_data_emits_six_key_envelope` (BLOCKER 1 Test 19)
    - tests/test_affordability.py contains literal substring `def test_va_residual_citation_format` (BLOCKER 4 — VA region × family_size grid)
    - tests/test_affordability.py contains literal substring `def test_fha_mip_compute_per_table_row` (BLOCKER 4 — FHA MIP table grid)
    - tests/test_affordability.py contains literal substring `def test_ltv_ceiling_boundary` (BLOCKER 4 — LTV ceiling boundary)
    - tests/test_affordability.py contains literal substring `def test_cli_rejects_missing_monthly_pmi_when_required` (W5 companion test)
    - `pytest tests/test_affordability.py::test_va_residual_citation_format -x` collects 12 cells (4 regions × 3 family_size values per BLOCKER 4)
    - `pytest tests/test_affordability.py::test_fha_mip_compute_per_table_row -x` collects 4 cells per HUD ML 2023-05 (BLOCKER 4)
    - `pytest tests/test_affordability.py::test_ltv_ceiling_boundary -x` collects 12 cases (6 loan_types × 2 boundary offsets) with 1+ skipped for jumbo (BLOCKER 4)
    - tests/test_affordability.py contains literal substring `subprocess.run([sys.executable, str(SCRIPT_PATH)` (Phase 3 D-17 portability)
    - tests/test_affordability.py contains literal substring `TypeAdapter(AffordabilityRequest)` (Pydantic v2 discriminated union validation)
    - tests/test_affordability.py does NOT contain literal substring `assertAlmostEqual` (D-18 enforcement)
    - tests/test_affordability.py does NOT contain literal substring `pytest.approx` (D-18 enforcement)
    - tests/test_affordability.py does NOT contain literal substring `@pytest.mark.xfail(strict=False, reason="Wave` (Wave 0 stubs replaced; xfail decorators removed)
    - `uv run pytest tests/test_affordability.py -x --tb=short` exits 0 (all tests pass — no xfail, no skip, no fail)
    - `uv run pytest tests/test_affordability.py --collect-only -q | grep -c "::test_"` returns >= 40 (9 AFFD-XX + cross-cutting tests + BLOCKER 4 parametrize cells: 12 VA + 4 FHA-MIP + 11 LTV-ceiling + 1 BLOCKER 1 + W5 companion ≈ 40+)
    - `uv run pytest -x` (full suite) exits 0
    - `uv run mypy --strict lib/affordability.py scripts/affordability.py tests/test_affordability.py tests/conftest.py` exits 0
    - `uv run ruff check lib/affordability.py scripts/affordability.py tests/test_affordability.py tests/conftest.py` exits 0
  </acceptance_criteria>
  <done>
    9 Wave 0 stubs replaced with real tests; 9 cross-cutting tests added (citation coverage, lazy-import, float-gate, file-error, --help-fast, ValidationError 6-key, round-trip closure, single-applicant equivalence, ATR/QM advisory); all 9 fixtures exercised; full Phase 4 acceptance gate passes; ROADMAP SC-1..SC-5 verified by tests; AFFD-01..09 closed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test fixtures → Decimal-string discipline | Fixture money fields MUST be quoted JSON strings; bare numbers (JSON floats) would silently coerce and pass tests for wrong reasons |
| Subprocess invocation → CLI surface | Tests use subprocess.run, not direct import (Phase 3 D-17 portability for Phase 10 relocation) |
| Citation strings → Phase 2 D-11 stable contract | VA-residual citation MUST be verbatim from predicate; format-drift breaks contract |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-06-01 | Tampering | Decimal/float silent coercion in fixtures | mitigate | Acceptance grep on negative pattern (no bare-number money fields); JSON validation pass via pre-validation float-gate test (Test 14) catches drift |
| T-04-06-02 | Tampering | VA-residual citation format-drift | mitigate | Test 7 asserts `resp.blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"` exactly; ROADMAP SC-3 verbatim; redundant assertion via regex pattern |
| T-04-06-03 | Tampering | xfail markers left in place silencing real failures | mitigate | Negative grep gate `@pytest.mark.xfail(strict=False, reason="Wave` returns 0 occurrences (all Wave 0 stubs flipped) |
| T-04-06-04 | Tampering | Direct `import scripts.affordability` would break Phase 10 relocation | mitigate | Subprocess invocation via SCRIPT_PATH constant (Phase 3 D-17 idiom); negative grep gate `from scripts` returns 0 outside the SCRIPT_PATH constant definition |
| T-04-06-05 | Tampering | Pre-commit hook accidentally fires on tests/fixtures/affordability/ contents | accept | The hook only matches User-Layer files; tests/fixtures/affordability/*.json is System Layer (per DATA_CONTRACT.md); confirmed by Plan 04-00 .gitkeep commit |
| T-04-06-06 | Repudiation | StaleReferenceWarning silently dropped from response.warnings | mitigate | FHA + VA fixtures explicitly assert their `warnings` arrays contain stale-warning strings (FHA mip-rates and VA residual income YAMLs both currently fire warnings per RESEARCH §_loader.py) |
| T-04-06-07 | Tampering | Round-trip closure tolerance loosened (allowing Decimal('0.01') instead of 0.0001) | mitigate | Test 5 hard-codes `Decimal("0.0001")` per D-09; acceptance grep gate pins the literal |
| T-04-06-08 | Information Disclosure | Subprocess test leaks fixture data on stderr | accept | Test fixtures contain example values only (no PII); subprocess output captured via subprocess.run, not logged |
</threat_model>

<verification>
After both tasks complete (full Phase 4 acceptance gate):

```bash
# Phase 4 quick-test (VALIDATION.md sampling rate per task)
uv run pytest tests/test_affordability.py -x --tb=short

# Full project suite green
uv run pytest -x

# mypy + ruff clean across all Phase 4 files
uv run mypy --strict lib/affordability.py scripts/affordability.py tests/test_affordability.py tests/conftest.py
uv run ruff check lib/affordability.py scripts/affordability.py tests/test_affordability.py tests/conftest.py

# 9 fixtures present
ls tests/fixtures/affordability/*.json | wc -l  # >= 9 (excluding .gitkeep)

# 9 AFFD-XX tests + cross-cutting all collect
uv run pytest tests/test_affordability.py --collect-only -q | grep -c "::test_"  # >= 18

# ROADMAP SC-1..SC-5 verbatim coverage
grep -q "VA-RESIDUAL-WEST-FAMILY-4" tests/test_affordability.py     # SC-3
grep -q "round_trip\|round-trip" tests/test_affordability.py        # SC-2
grep -q "household.example.yml\|household_example_yml" tests/test_affordability.py  # SC-4
grep -q "joint_applicants\|single_applicant" tests/test_affordability.py  # SC-5

# ROADMAP SC-1: scripts/affordability.py works end-to-end (subprocess test for any forward fixture)
# Implicit: Test 8 + Test 9 cover this.
```
</verification>

<success_criteria>
- [ ] All 9 Wave 0 xfail stubs replaced with real test bodies (no xfail, no skip)
- [ ] 9 fixtures committed under tests/fixtures/affordability/ (D-17 list complete)
- [ ] All money fields in fixtures are quoted Decimal strings (D-18 — exact equality)
- [ ] ROADMAP SC-1 verified: forward_conventional_80_ltv subprocess test passes; monthly_pi == "2528.27" exactly
- [ ] ROADMAP SC-2 verified: reverse_conventional_80_ltv_43_dti round-trips; D-09 tolerance honored; dollar amounts equal exactly
- [ ] ROADMAP SC-3 verified: forward_va_residual_fail; blocked_by == "VA-RESIDUAL-WEST-FAMILY-4" verbatim
- [ ] ROADMAP SC-4 verified: household_example_yml_e2e; subprocess invocation against config/household.example.yml succeeds
- [ ] ROADMAP SC-5 verified: joint_applicants_two_incomes + single_applicant; same code path
- [ ] Citation-coverage meta-test: every BLOCKED_BY_* template / constant has at least one fixture
- [ ] D-18 lazy-import test: --help fast; lib.affordability + numpy_financial NOT in sys.modules after --help (Phase 3 03-04 idiom)
- [ ] 6-key Pydantic envelope test: float-in-money rejected with 6-key shape (Phase 3 03-06 idiom)
- [ ] file-not-found envelope test: simpler {error: ...} shape (Phase 3 contract)
- [ ] Subprocess pattern: SCRIPT_PATH constant; never `import scripts.affordability` directly
- [ ] No D-18 violations: zero `assertAlmostEqual` and zero `pytest.approx`
- [ ] Full project suite green; AFFD-01..09 all closed
- [ ] mypy --strict + ruff clean across all Phase 4 files
</success_criteria>

<output>
After completion, create `.planning/phases/04-affordability/04-06-SUMMARY.md` per the standard template.

Phase 4 acceptance: when this plan completes green, run `/gsd-verify-work` to verify the 5 ROADMAP SC and the 9 AFFD-XX requirements all close. Then `/gsd-transition` to Phase 5 (ARM Modeling).
</output>
