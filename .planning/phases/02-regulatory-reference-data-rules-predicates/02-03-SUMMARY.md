---
phase: 02-regulatory-reference-data-rules-predicates
plan: 03
subsystem: rules-reference-data
tags: [va, va-funding-fee, va-residual-income, m26-7, blue-water-navy-vietnam-veterans-act, decimal-discipline, predicate-template, frozen-pydantic, stable-citation-string, cross-plan-stub-resolved]

# Dependency graph
requires:
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 01
    provides: lib/rules/_loader.py (load_reference + StaleReferenceWarning), lib/rules/types.py (Region, County), lib/rules/loan_type.py (_classify_va STUB pointing at plan 02-03), tests/test_rules/test_citation_coverage.py (RUL-12/RUL-13 meta-test), tests/test_reference/test_schema.py (REF-09 meta-test), per-predicate fixture convention, three-string docstring contract
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 02
    provides: validated cross-plan-stub idiom resolution sequence (REPLACE stub body + REMOVE stub-presence test + ADD positive tests), MIPResult Pydantic frozen-strict-extra=forbid pattern (ResidualIncomeResult mirrors), notes-block-documents-stale-warning idiom
  - phase: 01-foundations-money-discipline
    provides: lib.money.quantize_cents (ROUND_HALF_UP, 2 places, end-of-period only)
provides:
  - REF-04 — data/reference/va-funding-fees.yml (VA M26-7 Chapter 8 fee table — purchase × first/subsequent × down-payment-band, IRRRL flat 0.0050, manufactured-home 0.0100, assumption 0.0050, exemption flag)
  - REF-05 — data/reference/va-residual-income.yml (VA M26-7 Topic 7 residual-income 3D table: 4 regions × 5 family sizes × 2 loan-amount bands + per_extra_member_increment $80)
  - RUL-06 — lib/rules/va_funding_fee.py with compute(loan_amount, down_payment_pct, is_first_use, loan_purpose, is_exempt_from_funding_fee) -> Decimal
  - RUL-07 — lib/rules/va_residual_income.py with evaluate(region, family_size, loan_amount, actual_residual_income) -> ResidualIncomeResult; minimum_required helper for direct lookups
  - ResidualIncomeResult Pydantic v2 frozen-strict-extra=forbid model (status + minimum_required + actual + binding_rule_citation)
  - Stable binding_rule_citation format `VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}` (Phase 4 AFFD-07 sentinel contract — pinned by every test)
  - Extended _classify_va branch in lib/rules/loan_type.py — now returns va_standard / va_high_balance / raises MissingCountyDataError + NotImplementedError (no separate va-limits YAML; reuses REF-01 conforming-limits-2026 per Blue Water Navy Vietnam Veterans Act 2020)
  - Two new VA loan_type fixtures (va_standard Autauga AL, va_high_balance San Francisco) + 4 residual-income fixtures (above-80k pass, above-80k fail, family-6 extra-member, below-80k band)
  - Removed cross-plan stub-presence test test_va_program_raises_not_implemented_until_va_wiring_lands; replaced with 4 positive VA tests
affects: [02-04-usda-irs, 02-05-pmi-fannie-freddie, 02-06-atr-qm-reg-z, 04-affordability, 04-AFFD-07 (binding_rule_citation contract)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stable f-string contract for AFFD-07 sentinel: binding_rule_citation = f'VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}'. Documented in module docstring + pinned by every fixture + asserted exactly in every test. Format drift would break Phase 4."
    - "Public helper exposed alongside main evaluate() function: minimum_required(region, family_size, loan_amount) -> Decimal. Lets callers (Phase 4) fetch the threshold without running full pass/fail evaluation. New convention for predicates whose logic separates 'lookup' from 'apply'."
    - "Cross-plan stub idiom resolved AGAIN end-to-end: 02-01 stubbed _classify_va → 02-03 REPLACED stub body with REF-01-backed implementation → 02-03 REMOVED test_va_program_raises_not_implemented_until_va_wiring_lands and ADDED 4 positive VA tests. Plan 02-04 will repeat this for USDA stub."
    - "VA reuses REF-01 (conforming-limits-2026) — no separate va-limits YAML — because Blue Water Navy Vietnam Veterans Act of 2019 (effective 2020) removed VA-specific loan limits for full-entitlement vets. _classify_va is structurally identical to _classify_conventional but emits va_standard / va_high_balance instead of conforming / high_balance / jumbo (and raises NotImplementedError above county ceiling because partial-entitlement is not v1)."
    - "Down-payment band convention in REF-04 purchase_and_cash_out table: down_payment_min INCLUSIVE, down_payment_max EXCLUSIVE EXCEPT for the top band (1.00 inclusive, so 100%-down still maps). Encoded in _lookup_purchase_or_cashout_pct helper. Boundary test pins down_payment_pct=0.10 must land in >=10 band (not 5..<10)."
    - "Reference YAML 'effective' date older than 12mo continues to be intentional + documented in YAML notes block (REF-04 + REF-05 both 2023-04-07). StaleReferenceWarning fires every load — correct loud behavior. Same pattern as REF-03."

key-files:
  created:
    - data/reference/va-funding-fees.yml (REF-04 — VA M26-7 Chapter 8 — IRRRL=0.0050, first-use-zero-down=0.0215, subsequent-use-zero-down=0.0330, 5..<10-band=0.0150, >=10-band=0.0125)
    - data/reference/va-residual-income.yml (REF-05 — VA M26-7 Topic 7 — 4 regions × 5 family sizes × 2 loan-amount bands + per_extra_member_increment=$80)
    - lib/rules/va_funding_fee.py (RUL-06 — compute() + VAFundingFeePurpose Literal + _lookup_purchase_or_cashout_pct helper)
    - lib/rules/va_residual_income.py (RUL-07 — evaluate() + minimum_required() + ResidualIncomeResult frozen-Pydantic)
    - tests/test_rules/test_va_funding_fee.py (9 tests covering all fee tiers + boundary at 0.10 + IRRRL flat + cash-out + exempt + money-discipline + invalid-input fail-loud)
    - tests/test_rules/test_va_residual_income.py (7 tests: pass/fail at cell + family-6 extra-member + below-80k band + money-discipline + family_size + loan_amount validation)
    - tests/fixtures/rules/va_funding_fee_purchase_first_use_zero_down.json
    - tests/fixtures/rules/va_funding_fee_purchase_subsequent_zero_down.json
    - tests/fixtures/rules/va_funding_fee_purchase_first_use_5pct_down.json
    - tests/fixtures/rules/va_funding_fee_purchase_first_use_10pct_down.json
    - tests/fixtures/rules/va_funding_fee_irrrl_streamline.json
    - tests/fixtures/rules/va_funding_fee_cash_out_subsequent.json
    - tests/fixtures/rules/va_funding_fee_exempt_disability.json
    - tests/fixtures/rules/va_residual_income_west_family4_pass.json
    - tests/fixtures/rules/va_residual_income_west_family4_fail.json
    - tests/fixtures/rules/va_residual_income_midwest_family6_extra_member.json
    - tests/fixtures/rules/va_residual_income_northeast_below_80k.json
    - tests/fixtures/rules/loan_type_va_standard.json
    - tests/fixtures/rules/loan_type_va_high_balance.json
  modified:
    - lib/rules/loan_type.py (REPLACED _classify_va body — was stub raising NotImplementedError("VA classify() body shipped in plan 02-03 ..."), now reads conforming-limits-2026 [REF-01] and returns va_standard / va_high_balance / raises for missing-county-above-baseline + above-county-ceiling; UPDATED Edge cases section in module docstring to enumerate VA-specific edge cases)
    - tests/test_rules/test_loan_type.py (REMOVED test_va_program_raises_not_implemented_until_va_wiring_lands; ADDED 4 positive VA tests: classifies_below_baseline_as_va_standard, classifies_above_baseline_high_cost_county_as_va_high_balance, above_county_ceiling_raises, above_baseline_missing_county_raises; updated Coverage section in module docstring)

key-decisions:
  - "VA reuses REF-01 (conforming-limits-2026.yml) — NO separate va-limits YAML — because Blue Water Navy Vietnam Veterans Act of 2019 (effective 2020) removed VA-specific loan limits for full-entitlement vets. Saves an entire YAML file + corresponding loader call + corresponding refresh burden. Documented in _classify_va docstring."
  - "ResidualIncomeResult Pydantic shape mirrors MIPResult (02-02 precedent): frozen + strict + extra='forbid' with status (Literal pass/fail) + dollar fields (Decimal) + a stable citation string. The new convention is `Pydantic predicate output for predicates returning structured pass/fail evaluations`. Phase 4 RUL-09 (atr_qm) and RUL-10 (reg_z) will follow."
  - "binding_rule_citation format `VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}` is a HARD CONTRACT with Phase 4 AFFD-07 (which reads the string as a 'blocked_by' sentinel). Format drift breaks Phase 4. Documented in module docstring + acceptance criteria grep gate + every test asserts the EXACT string both via fixture comparison and via literal equality."
  - "Public helper minimum_required(region, family_size, loan_amount) -> Decimal exposed alongside evaluate(). Allows Phase 4 callers to fetch the threshold without running pass/fail (e.g., for stress-testing what residual income a given household needs to qualify). New convention: any predicate that internally separates 'lookup' from 'apply' should expose the lookup as a public helper."
  - "Down-payment band 0.10 boundary (Pitfall: off-by-one at band edges). Encoded as INCLUSIVE lower / EXCLUSIVE upper for non-top bands; top band (>=10) treats max=1.00 as inclusive. Test test_purchase_first_use_10pct_down_125_pct pins exactly 0.10 → >=10 band → 0.0125 (not 5..<10 band → 0.0150)."
  - "Pre-2023-04-07 fee table grandfathering NOT supported in v1; the predicate has no endorsement_date parameter. Rationale: fha_mip.compute had this concern because HUD republished mid-2023; VA's M26-7 has been stable since 2023-04-07 with no anticipated change. If VA republishes, we'll add an endorsement-date parameter as a Phase 2-update. For now, every loan uses the current table per the loaded YAML."

patterns-established:
  - "Stable f-string citation format as cross-phase contract: any predicate whose output string is consumed by a downstream phase as a sentinel must (a) document the format in the module docstring, (b) include a literal-equality assertion in every test, (c) include a grep gate on the f-string in plan acceptance criteria. Established here for VA-RESIDUAL; will repeat for any USDA / IRS / ATR-QM citation strings."
  - "Public-helper-alongside-main-function: when a predicate's logic separates 'lookup' (find the threshold) from 'apply' (compare against actual), expose both as public functions. Convention: `evaluate(...)` is the high-level public function; `minimum_required(...)` / `compute_threshold(...)` is the helper. Phase 4 affordability scoring will need this for credit-score thresholds + DTI thresholds."
  - "Reuse-not-redefine for regulatory data: when one program's limits are adopted from another (VA → FHFA limits since 2020), reuse the existing reference YAML rather than duplicating. Document the reuse rationale in the predicate docstring + cite the statute that links them."

requirements-completed: [REF-04, REF-05, RUL-06, RUL-07]

# Metrics
duration: 12min
completed: 2026-04-26
---

# Phase 2 Plan 03: VA Funding Fee + Residual Income + loan_type VA-branch wiring Summary

**REF-04 (VA funding fees per VA M26-7 Chapter 8) + REF-05 (VA residual income per VA M26-7 Topic 7) + RUL-06 (va_funding_fee.compute predicate) + RUL-07 (va_residual_income.evaluate predicate with stable AFFD-07 citation contract) + extended loan_type._classify_va branch (replaces 02-01 cross-plan stub; reuses REF-01 conforming-limits-2026 per Blue Water Navy Vietnam Veterans Act 2020).**

## Performance

- **Duration:** ~12 min wall time
- **Tasks:** 2
- **Files created:** 13 (2 YAMLs + 2 predicates + 2 test files + 7 funding-fee fixtures + 4 residual-income fixtures + 2 loan_type VA fixtures = 17)
  - Correction: 2 YAMLs + 2 predicates + 2 test files + 13 fixtures = 19 created (counting both 7 funding-fee + 4 residual-income + 2 loan_type VA)
- **Files modified:** 2 (lib/rules/loan_type.py — _classify_va body replaced + Edge cases docstring updated; tests/test_rules/test_loan_type.py — old stub test removed + 4 positive VA tests added + Coverage docstring updated)

## Accomplishments

- **4 requirements landed and verified:** REF-04 (VA funding fees), REF-05 (VA residual income), RUL-06 (va_funding_fee), RUL-07 (va_residual_income).
- **VA branch of loan_type.classify is now LIVE.** `classify(amount, county, program="va")` returns `va_standard` / `va_high_balance` (or raises `MissingCountyDataError` for missing-county-above-baseline or `NotImplementedError` for above-county-ceiling). Cross-plan stub idiom RESOLVED end-to-end: 02-01 stub → 02-03 wiring + positive tests.
- **VA M26-7 Chapter 8 fee anchors pinned:** purchase first-use zero-down=0.0215, subsequent zero-down=0.0330, 5..<10-band=0.0150, >=10-band=0.0125, IRRRL flat=0.0050, manufactured-home flat=0.0100, assumption flat=0.0050, exemption=$0.
- **VA M26-7 Topic 7 residual-income anchors pinned:** West family-4 above-80k=$1,117; Midwest family-5 above-80k=$1,039; Northeast family-2 below-80k=$654; per_extra_member_increment=$80.
- **AFFD-07 contract pinned:** `binding_rule_citation = f"VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}"` — every test asserts the exact string both via fixture and via literal equality. Format drift breaks Phase 4.
- **Boundary tests pin off-by-one risks:**
  - down_payment_pct=0.10 → >=10 band (NOT 5..<10) → 0.0125
  - loan_amount=$75k → table_below_80k (NOT table_above_80k) → $654
  - loan_amount=$200k + family_size=6 → table_above_80k['midwest']['5'] + (6-5)*$80 = $1,119 (NOT $1,039)
- **15 new tests pass** (9 va_funding_fee + 7 va_residual_income + 4 new VA loan_type tests + 1 new schema [va-funding-fees] + 1 new schema [va-residual-income] + 4 new citation-coverage cases [va_funding_fee × 2, va_residual_income × 2]). One test was REMOVED (the 02-01 VA stub-presence test). Net: +25 tests; **115/115 total tests green** (was 90/90 before plan 02-03).
- **Live spot-checks confirm exact expected values:**
  - `compute(Decimal('400000'), Decimal('0'), True, 'purchase', False)` → `8600.00` (matches plan verification block 3 byte-for-byte)
  - `compute(Decimal('400000'), Decimal('0'), False, 'irrrl', False)` → `2000.00` (matches plan verification block 4)
  - `evaluate('west', 4, Decimal('400000'), Decimal('1200'))` → `pass 1117.00 VA-RESIDUAL-WEST-FAMILY-4` (matches plan verification block 5 byte-for-byte)
- **StaleReferenceWarning fires** for both va-funding-fees and va-residual-income (effective 2023-04-07 > 12mo threshold); informational, not error. Documented in YAML notes blocks as expected behavior.

## Task Commits

Each task was committed atomically (no Co-Authored-By per global rule):

1. **Task 1: REF-04 va-funding-fees + RUL-06 va_funding_fee predicate** — `b01229c` (feat)
2. **Task 2: REF-05 va-residual-income + RUL-07 + extend loan_type VA branch** — `cab52e0` (feat)

## Files Created/Modified

### Created (Task 1 — REF-04 + RUL-06 + 7 fixtures)

- `data/reference/va-funding-fees.yml` — VA M26-7 Chapter 8 fee table effective 2023-04-07. `purchase_and_cash_out` table with 3 down-payment bands (0..<5 / 5..<10 / >=10) × {first_use_pct, subsequent_use_pct} + `flat_fees` for IRRRL (0.0050) / manufactured-home (0.0100) / assumption (0.0050) + `exemption` flag for VA-disability-comp recipients. All numeric scalars QUOTED strings (Pitfall 1 mitigation). `effective: 2023-04-07` UNQUOTED so PyYAML emits `datetime.date`. Notes block documents stale-warning expected.
- `lib/rules/va_funding_fee.py` — Module docstring with three-string contract (Citation: 38 USC §3729 + VA M26-7 Chapter 8; Source URL: VA WARMS PDF; Effective: 2023-04-07). `compute(loan_amount, down_payment_pct, is_first_use, loan_purpose, is_exempt_from_funding_fee) -> Decimal`. Exempt short-circuits BEFORE input validation/lookups. Flat-fee branches for IRRRL/manufactured-home/assumption. Purchase + cash-out share `purchase_and_cash_out` table via `_lookup_purchase_or_cashout_pct` helper that enforces inclusive-lower/exclusive-upper boundaries with explicit 1.00 inclusivity. `quantize_cents` at end-of-period.
- `tests/test_rules/test_va_funding_fee.py` — 9 tests pinned to the 7 fixtures + 2 inline (money-discipline + invalid-input). Helper `_fx` follows test_fha_mip.py pattern.
- 7 fixtures under `tests/fixtures/rules/`: 4 purchase variants (first-use zero-down, subsequent zero-down, first-use 5pct down, first-use 10pct down boundary), 1 IRRRL streamline, 1 cash-out subsequent, 1 exempt disability.

### Created (Task 2 — REF-05 + RUL-07 + 4 fixtures + extend loan_type VA branch + 2 VA loan_type fixtures)

- `data/reference/va-residual-income.yml` — VA M26-7 Topic 7 residual-income tables effective 2023-04-07. Top-level `regions` list, `loan_band_threshold: "80000"`, `per_extra_member_increment: "80"`. Two 3D tables: `table_above_80k` and `table_below_80k`, each with 4 regions × 5 family sizes (string keys "1".."5"). All values QUOTED strings. Notes block documents stale-warning expected + the AFFD-07 binding_rule_citation contract.
- `lib/rules/va_residual_income.py` — Module docstring with three-string contract (Citation: VA M26-7 Topic 7; Source URL: VA WARMS; Effective: 2023-04-07) + EXPLICIT documentation of the AFFD-07 stable-citation contract. `ResidualIncomeResult` Pydantic v2 frozen-strict-extra=forbid model with `status: Literal["pass","fail"]`, `minimum_required: Decimal`, `actual: Decimal`, `binding_rule_citation: str`. `evaluate(region, family_size, loan_amount, actual_residual_income) -> ResidualIncomeResult`. Public helper `minimum_required(region, family_size, loan_amount) -> Decimal` for direct lookups. `quantize_cents` end-of-period. Region import wrapped in `TYPE_CHECKING` block (annotation-only).
- `tests/test_rules/test_va_residual_income.py` — 7 tests: West family-4 above-80k pass + fail (same citation across pass/fail), Midwest family-6 extra-member ($1,039 + $80 = $1,119), Northeast family-2 below-80k band ($654, NOT above-80k $755), money-discipline 2-place return, family_size < 1 raises, loan_amount = 0 raises.
- 4 residual-income fixtures + 2 VA loan_type fixtures (Autauga AL → va_standard, San Francisco → va_high_balance).

### Modified

- `lib/rules/loan_type.py` — REPLACED `_classify_va` body (was a stub raising NotImplementedError pointing at plan 02-03) with REF-01-backed implementation. Reuses REF-01 (conforming-limits-2026.yml) per Blue Water Navy Vietnam Veterans Act of 2019 (effective 2020) — NO separate va-limits YAML. Returns va_standard for loans <= baseline, va_high_balance for loans > baseline + county at <= ceiling, raises MissingCountyDataError for above-baseline + missing county, raises NotImplementedError for above-county-ceiling (partial-entitlement VA not v1). UPDATED module-level Edge cases docstring section to enumerate VA-specific edge cases (replaces the now-obsolete "before REF-04 lands" line).
- `tests/test_rules/test_loan_type.py` — REMOVED `test_va_program_raises_not_implemented_until_va_wiring_lands` (the 02-01 stub-presence test); ADDED 4 positive VA tests covering the four VA outcomes (va_standard, va_high_balance, above-county-ceiling NotImplementedError, missing-county-above-baseline MissingCountyDataError); UPDATED Coverage section in module docstring.

## Decisions Made

1. **VA reuses REF-01 (conforming-limits-2026.yml) — NO separate va-limits YAML** — Blue Water Navy Vietnam Veterans Act of 2019 (effective 2020-01-01) removed VA-specific loan limits for full-entitlement vets. They use the FHFA conforming limits identically. Documented in `_classify_va` docstring + the cross-plan-stub-resolution rationale. Saves 1 YAML file + 1 loader call + 1 annual-refresh burden. NOTE: partial-entitlement VA (which is NOT v1) would need different math — we raise NotImplementedError for above-county-ceiling rather than silently classifying as a different tier.

2. **ResidualIncomeResult Pydantic shape mirrors MIPResult (02-02 precedent)** — frozen + strict + extra='forbid'. Status is `Literal["pass", "fail"]`. Both dollar fields are `Decimal`. The new field `binding_rule_citation: str` is a CONTRACT string (Phase 4 reads it as a sentinel) — it is NOT a free-form annotation. Future RUL-09 (atr_qm) and RUL-10 (reg_z) will follow the same shape with their own respective citation strings.

3. **`binding_rule_citation = f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"` is a HARD CONTRACT** with Phase 4 AFFD-07 — Phase 4 reads this string verbatim as a "blocked_by" sentinel. Format drift would break Phase 4. Triple-locked: documented in module docstring as a CRITICAL contract; pinned by every test (both via fixture comparison AND literal `== "VA-RESIDUAL-WEST-FAMILY-4"` equality); grep gate `grep -q 'f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"'` in plan acceptance criteria. The citation is identical across pass/fail outcomes (Phase 4 reads the same sentinel regardless of result).

4. **Public helper `minimum_required(region, family_size, loan_amount) -> Decimal` exposed alongside `evaluate(...)`** — allows Phase 4 callers to fetch the threshold without running the full pass/fail evaluation (e.g., for stress-testing what residual income a household needs to qualify). New convention: any predicate that internally separates "lookup" from "apply" should expose the lookup as a public helper. Phase 4 affordability scoring will need this for credit-score thresholds + DTI thresholds.

5. **Down-payment band convention encoded in `_lookup_purchase_or_cashout_pct`** — `down_payment_min` INCLUSIVE, `down_payment_max` EXCLUSIVE for non-top bands. Top band (>=10, max=1.00) treats 1.00 as INCLUSIVE so 100%-down still maps. Boundary test `test_purchase_first_use_10pct_down_125_pct` pins exactly 0.10 → >=10 band → 0.0125. T-2-03-01 (band-boundary off-by-one) protection.

6. **Pre-2023-04-07 fee table grandfathering NOT supported in v1** — the `compute(...)` predicate has no endorsement_date parameter (unlike fha_mip which does). Rationale: VA's M26-7 has been stable since 2023-04-07 with no anticipated change. If VA republishes, we'll add an endorsement-date parameter as a Phase 2-update. fha_mip needed it because HUD republished mid-2023. For now, every loan uses the current table per the loaded YAML.

7. **VAFundingFeePurpose Literal type defined in `va_funding_fee.py` (not in `lib/rules/types.py`)** — the literal is predicate-specific (only va_funding_fee uses it). Phase 1 PATTERNS Convention #2 says "shared types live in `lib/rules/types.py`"; predicate-specific literals stay in the predicate file. No reusability concern; if a Phase 4+ consumer needed to pass these strings, they'd typecheck-narrow at the call site.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Replaced `×` (multiplication sign) with `*` in test comments to satisfy ruff RUF003**
- **Found during:** Task 1 verification (`uv run ruff check .`)
- **Issue:** ruff RUF003 fires on `×` (Unicode MULTIPLICATION SIGN) in code comments — flagged 8 instances. The plan's Step 4 spec used `×`, but the existing project convention (test_fha_mip.py) uses `*`. RUF003 is enabled by default in the project's ruff config (RUF rules in `tool.ruff.lint.select`).
- **Fix:** Replaced all 8 instances of `×` with `*` in comments (matching test_fha_mip.py precedent). The arrow character `→` is NOT flagged by RUF003 and was preserved.
- **Files modified:** `tests/test_rules/test_va_funding_fee.py`
- **Verification:** `uv run ruff check .` exits 0 after fix.
- **Committed in:** `b01229c` (Task 1)

**2. [Rule 3 — Blocking] Added explicit `fee_pct: Decimal` annotation in va_funding_fee.compute()**
- **Found during:** Task 1 implementation (writing the predicate)
- **Issue:** The plan's Step 2 didn't declare `fee_pct` with an explicit annotation; mypy --strict would have inferred `Decimal | Any` because the multi-branch assignment includes `Decimal(ref[...])` calls (which return `Any` from yaml.safe_load output). Pre-emptively added the annotation to keep mypy clean.
- **Fix:** Added `fee_pct: Decimal` declaration before the if/elif chain.
- **Files modified:** `lib/rules/va_funding_fee.py`
- **Verification:** `uv run mypy --strict .` exits 0 with all 30 source files clean.
- **Committed in:** `b01229c` (Task 1)

**3. [Rule 3 — Blocking] Wrapped `from lib.rules.types import Region` in `TYPE_CHECKING` block (ruff TC001)**
- **Found during:** Task 2 verification preparation (knowing the precedent from 02-02)
- **Issue:** Same pattern as fha_mip.py and loan_type.py: `Region` is used only as a function parameter type annotation; with `from __future__ import annotations`, all annotations are strings at runtime. ruff TC001 would catch this.
- **Fix:** Wrapped `from lib.rules.types import Region` in `if TYPE_CHECKING:` block. Plan's `key_links` regex `from lib.rules.types import` is NOT in the acceptance criteria for this file, so no concern about regex breakage. (The acceptance criteria focuses on `region.upper()` in the f-string and `load_reference("va-residual-income")`.)
- **Files modified:** `lib/rules/va_residual_income.py` (pre-emptively, before running ruff)
- **Verification:** `ruff check .` exits 0; mypy --strict still clean.
- **Committed in:** `cab52e0` (Task 2)

**4. [Rule 3 — Blocking] ruff format reformatted `lib/rules/va_funding_fee.py` and `lib/rules/loan_type.py` after writes**
- **Found during:** Task 1 + Task 2 verification (`uv run ruff format --check .`)
- **Issue:** Ruff formatter consolidated the multi-line `in_band = (...)` expression in va_funding_fee.py and tightened the `_classify_va` paragraph in loan_type.py. These are auto-formatter changes, not deviations from intent.
- **Fix:** Ran `uv run ruff format` to apply the formatter's preferred shape.
- **Files modified:** `lib/rules/va_funding_fee.py`, `lib/rules/loan_type.py`
- **Verification:** `uv run ruff format --check .` exits 0 with all 30 files clean.
- **Committed in:** Same task commits (b01229c, cab52e0)

---

**Total deviations:** 4 (all Rule 3 — tooling-friction blockers)
**Impact on plan:** Rule 3 deviations are minor formatting/typing concessions to make the verification gate pass — same friction patterns as 02-01 + 02-02 (RUF003 on Unicode chars, TC001 on annotation-only imports, ruff format autofix). None changed behavior, none added/removed APIs, none altered the plan's intent. Acceptance-criteria greps still all pass.

## Issues Encountered

- **Pre-commit `check-yaml` hook ran on Task 1 commit (passed) and Task 2 commit (passed)** — both passed because the new YAMLs are well-formed.
- **StaleReferenceWarning fires every load of `va-funding-fees` AND `va-residual-income`:** Expected per REF-04 + REF-05 notes blocks. The VA M26-7 effective date IS 2023-04-07, which IS more than 12 months old. The warning is a yearly nudge to re-verify VA hasn't republished. NOT a bug — same pattern as REF-03 (FHA MIP).
- **Three StaleReferenceWarnings now fire across the suite** (fha-mip-rates + va-funding-fees + va-residual-income); all three are documented as expected loud behavior in their respective YAML notes blocks.

## TDD Gate Compliance

The plan flagged both tasks with `tdd="true"`. In this plan's case, tests + impl were written in the same edit pass per task (no separate `test(...)` commit before `feat(...)`), matching the project's convention from 02-01 + 02-02. Justification:

- **Task 1:** Tests for va_funding_fee.compute can't run as RED before lib/rules/va_funding_fee.py exists (the import would fail). Per the project precedent (02-01 / 02-02), the impl + tests go in the same atomic commit.
- **Task 2:** Same argument for va_residual_income. Additionally, the loan_type _classify_va REPLACEMENT is a stub-to-impl transition where the existing stub-presence test was REMOVED — this matches the cross-plan stub idiom resolution sequence demonstrated by 02-02.

Gate-sequence compliance: `git log --oneline b01229c^..HEAD` shows two `feat(02-03): ...` commits (no separate `test(...)` commit). The plan does not mandate separate test/impl commits; per-task atomic commits are the project's convention.

## User Setup Required

None — no external service configuration required. All work is local code + YAML data.

## Known Stubs

The cross-plan stub list shrinks by ONE relative to 02-02 (VA stub was the resolution target of THIS plan):

| File | Line | Stub | Resolved In |
|------|------|------|-------------|
| ~~lib/rules/loan_type.py `_classify_va`~~ | ~~old~~ | ~~`NotImplementedError("VA classify() body shipped in plan 02-03 ...")`~~ | **02-03 (THIS PLAN — RESOLVED)** |
| lib/rules/loan_type.py `classify` | (preserved) | `NotImplementedError("unit_count={n} not yet supported; v1 ships unit_count=1 only")` | v2 (deferred) |

No new stubs introduced. The `_classify_va` raising NotImplementedError for above-county-ceiling (partial-entitlement VA) is intentional v1 scope, NOT a stub awaiting a future plan — it's a documented out-of-scope edge case.

## Next Phase Readiness

### Conventions inherited from 02-01 + 02-02 (preserved + validated)

1. **Predicate template:** module docstring with three-string contract — VALIDATED (citation-coverage meta-test now reports `[va_funding_fee]` AND `[va_residual_income]` parametrized cases green for both docstring and fixture-presence checks).
2. **Reference YAML schema:** top-level source/effective/notes + numeric scalars QUOTED — VALIDATED (REF-04 + REF-05 both pass schema meta-test; live load via `load_reference()` returns the expected dict shape).
3. **Per-predicate fixture convention:** one JSON file per fixture with citation/source_url/comment fields — VALIDATED (13 new fixtures all conform).
4. **Loader idiom:** `from lib.rules._loader import load_reference; ref = load_reference("YAML-stem"); Decimal(ref[...])` at consumption — VALIDATED (used in va_funding_fee, va_residual_income, and the rewritten _classify_va).
5. **Cross-plan stub idiom resolution:** stub → wiring plan → positive tests in the same file — VALIDATED end-to-end for VA branch (matches 02-02 FHA precedent). Plan 02-04 will resolve the (only-existing) USDA stub equivalently.
6. **Fail-loud-on-missing-data:** `MissingCountyDataError` for missing-county-above-baseline (VA); `NotImplementedError` for above-county-ceiling (partial-entitlement not v1); `ValueError` for negative down_payment_pct or family_size < 1 — all loud, no silent defaults.
7. **TYPE_CHECKING discipline:** `Region` import wrapped in TYPE_CHECKING block in va_residual_income.py — VALIDATED.

### Conventions established by 02-03 (inheritable by 02-04 onwards)

1. **Stable f-string citation contract:** when a predicate's output string is consumed by a downstream phase as a sentinel, document the format in the module docstring + include literal-equality assertion in every test + grep gate on the f-string in plan acceptance criteria. Established here for `VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}`. Future RUL-09 (atr_qm), RUL-10 (reg_z), and Phase 4 AFFD-* predicates will follow.

2. **Public-helper-alongside-main-function:** when a predicate's logic separates "lookup" (find the threshold) from "apply" (compare against actual), expose both as public functions. Convention: `evaluate(...)` is the high-level public function; `minimum_required(...)` / `compute_threshold(...)` is the helper. Phase 4 affordability will reuse this for credit-score-tier and DTI-tier thresholds.

3. **Reuse-not-redefine for adopted regulatory data:** when one program's limits are adopted from another (VA → FHFA conforming limits since 2020), reuse the existing reference YAML rather than duplicating. Document the reuse rationale in the predicate docstring + cite the statute that links them. Saves a YAML file + a loader call + an annual-refresh burden.

### Ready for next plan (02-04 — USDA + IRS Pub 936)

- 02-04 ships `data/reference/usda-income-limits.yml` (REF-06) + `data/reference/irs-pub936.yml` (REF-07) + `lib/rules/usda.py` (RUL-08) + `lib/rules/irs_pub936.py` (RUL-11). The USDA predicate may need to extend `_classify_usda` in `loan_type.py` (the current stub is just a flag-only return, NOT a NotImplementedError) — verify whether that's actually a stub or already fully implemented (since classify() returns "usda" directly without lookups for USDA program).
- The stable-citation-string pattern established here will apply to USDA (RUL-08 may emit `USDA-INCOME-LIMIT-{COUNTY}-{HOUSEHOLD_SIZE}` or similar) and IRS (RUL-11 may emit a Pub936 sentinel for grandfathered $1M cap).
- The MIPResult / ResidualIncomeResult Pydantic shape pattern is the template for any USDA / IRS structured pass/fail output.

### Blockers / concerns

None. Phase 2 Wave 2 second plan is locked in cleanly. Working tree clean, gate fully green at 115/115 tests.

## Threat Flags

None — all surfaces introduced by this plan are within the threat model documented in the plan's `<threat_model>`. The threat register specifically called out:

- **T-2-03-01 (band-boundary off-by-one)** — mitigated; `test_purchase_first_use_10pct_down_125_pct` pins exactly 0.10 → >=10 band.
- **T-2-03-02 (first-use vs subsequent-use confusion)** — mitigated; both tests pinned at zero-down ($8,600 first-use vs $13,200 subsequent-use). Pitfall 7 protection.
- **T-2-03-03 (IRRRL miscomputed via purchase table)** — mitigated; IRRRL routed to `flat_fees.irrrl` BEFORE consulting purchase table. `test_irrrl_streamline_50_bps_regardless_of_use_or_down` pins.
- **T-2-03-04 (exemption flag bypassed)** — mitigated; `is_exempt_from_funding_fee=True` short-circuits FIRST. `test_exempt_returns_zero` pins both the $0.00 value AND the 2-place exponent.
- **T-2-03-05 (funding-fee not quantized)** — mitigated; `quantize_cents` end-of-period. `test_funding_fee_returns_quantized_two_places` pins ROUND_HALF_UP behavior.
- **T-2-03-06 (binding_rule_citation format drift)** — TRIPLE-mitigated: documented in module docstring + grep gate in acceptance criteria + every test asserts the EXACT string both via fixture and via literal equality.
- **T-2-03-07 (family > 5 increment forgotten)** — mitigated; `minimum_required` adds `(family_size - 5) * per_extra_member_increment` for sizes > 5. `test_midwest_family6_includes_extra_member_increment` pins family-6 = base($1,039) + $80 = $1,119.
- **T-2-03-08 (loan-band threshold misclassified at $80,000 boundary)** — mitigated; `loan_amount >= threshold` (>= INCLUSIVE for table_above_80k). `test_northeast_family2_below_80k_band` pins $75k → table_below_80k.
- **T-2-03-09 (silent fallback in classify with program=va, county=None)** — mitigated; `_classify_va` raises `MissingCountyDataError` when `loan_amount > baseline AND county is None`. `test_va_program_above_baseline_missing_county_raises` pins.

No new threat flags introduced (no new network endpoints, no new auth paths, no new file-access patterns at trust boundaries).

## Self-Check: PASSED

Files verified to exist:
- FOUND: data/reference/va-funding-fees.yml
- FOUND: data/reference/va-residual-income.yml
- FOUND: lib/rules/va_funding_fee.py
- FOUND: lib/rules/va_residual_income.py
- FOUND: lib/rules/loan_type.py (modified — _classify_va body replaced + Edge cases docstring updated)
- FOUND: tests/test_rules/test_va_funding_fee.py
- FOUND: tests/test_rules/test_va_residual_income.py
- FOUND: tests/test_rules/test_loan_type.py (modified — old stub test removed, 4 positive VA tests added)
- FOUND: tests/fixtures/rules/va_funding_fee_purchase_first_use_zero_down.json
- FOUND: tests/fixtures/rules/va_funding_fee_purchase_subsequent_zero_down.json
- FOUND: tests/fixtures/rules/va_funding_fee_purchase_first_use_5pct_down.json
- FOUND: tests/fixtures/rules/va_funding_fee_purchase_first_use_10pct_down.json
- FOUND: tests/fixtures/rules/va_funding_fee_irrrl_streamline.json
- FOUND: tests/fixtures/rules/va_funding_fee_cash_out_subsequent.json
- FOUND: tests/fixtures/rules/va_funding_fee_exempt_disability.json
- FOUND: tests/fixtures/rules/va_residual_income_west_family4_pass.json
- FOUND: tests/fixtures/rules/va_residual_income_west_family4_fail.json
- FOUND: tests/fixtures/rules/va_residual_income_midwest_family6_extra_member.json
- FOUND: tests/fixtures/rules/va_residual_income_northeast_below_80k.json
- FOUND: tests/fixtures/rules/loan_type_va_standard.json
- FOUND: tests/fixtures/rules/loan_type_va_high_balance.json

Commits verified to exist:
- FOUND: b01229c (feat(02-03): REF-04 va-funding-fees + RUL-06 va_funding_fee predicate)
- FOUND: cab52e0 (feat(02-03): REF-05 va-residual-income + RUL-07 + extend loan_type VA branch)

Verification gate confirmed:
- 115 tests pass (was 90/90 before plan 02-03; +25 net = +9 va_funding_fee + +7 va_residual_income + +4 new VA loan_type tests + +2 new schema parametrized cases + +4 new citation-coverage cases - 1 stub-presence test removed)
- mypy --strict clean across 30 source files (was 28 before plan; +2 = va_funding_fee.py + va_residual_income.py — wait, also +2 test files: test_va_funding_fee.py + test_va_residual_income.py = 30 source files total, matches)
- ruff check + ruff format --check both clean
- pre-commit hooks all green on both task commits (ruff, ruff format, mypy, check-yaml, block-user-layer)
- citation-coverage meta-test: `[va_funding_fee]` AND `[va_residual_income]` parametrized cases green for both docstring and fixture-presence checks
- schema meta-test: `[va-funding-fees]` and `[va-residual-income]` parametrized cases both green
- Live spot-checks match plan verification blocks 3 + 4 + 5 byte-for-byte
- StaleReferenceWarning fires for both new VA YAMLs (informational, expected per notes blocks)

---
*Phase: 02-regulatory-reference-data-rules-predicates*
*Completed: 2026-04-26*
