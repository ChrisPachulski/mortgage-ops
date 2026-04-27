---
phase: 02-regulatory-reference-data-rules-predicates
verified_at: 2026-04-27T05:45:06Z
status: passed
verifier_model: sonnet
test_count: 254/254
---

# Phase 2: Regulatory Reference Data & Rules Predicates — Verification Report

**Phase Goal (ROADMAP.md line 51):** Build the cited regulatory data layer (YAML with `source:` + `effective:`) and the one-predicate-per-citation rules library that every later calc phase composes.

**Verified:** 2026-04-27T05:45:06Z
**Status:** passed
**Score:** 5/5 must_haves verified (with two documented WARNING-class deviations from the original SC wording — neither is a behavior gap; see notes per criterion).
**Test suite:** `uv run pytest -q` → **254 passed, 4 stale-reference warnings, 0 failures** (run at 2026-04-27 05:43Z).

## Goal Verdict

**PASS.** The cited regulatory data layer is in place: 10 YAMLs in `data/reference/` (a documented superset of the original 7 — see deviation note 1), each carrying `source:` URL + `effective:` date, all loaded via the single `lib/rules/_loader.py` source-of-truth loader. The one-predicate-per-citation library ships 11 predicates in `lib/rules/`, each with a `Citation:`/`Source URL:`/`Effective:` docstring header and ≥1 hand-calculated test fixture, audited by parametrized meta-tests (`test_citation_coverage.py`) whose teeth are themselves proven by mutation tests (`test_citation_coverage_mutations.py`, all 7 mutation paths fail loud as expected). All 22 phase requirement IDs (REF-01..09, RUL-01..13) are marked `Done (02-NN)` in REQUIREMENTS.md and trace to real predicate or YAML files. The full code-review-fix pass closed all 14 review findings (5 BLOCKERS + 9 WARNINGS) on main between 19ab9d3 and 8c75e0b, and the test count grew from 224 to 254 to pin those fixes against regression. Two minor deviations from the literal ROADMAP success-criterion wording (YAML count 7→10, function names `compute_mip`→`compute` and `terminates_at`→`status`) are documented in plans, captured by audit tests, and do not change the behavior the success criteria require.

## Per-Must-Have Table

| # | Criterion (verbatim from ROADMAP success criteria) | Status | Live Evidence |
|---|---|---|---|
| 1 | All seven `data/reference/*.yml` files load successfully and each contains `source:` URL + `effective:` date fields (asserted by test) | **VERIFIED** with documented deviation (10 YAMLs ship, not 7) | `data/reference/` contains exactly 10 `.yml` files: `atr-qm-thresholds`, `conforming-limits-2026`, `fannie-llpa-matrix`, `fha-limits-2026`, `fha-mip-rates`, `freddie-eligibility-matrix`, `irs-pub936`, `usda-income-limits`, `va-funding-fees`, `va-residual-income`. Every file has both a `source:` URL (verified by grep — all start with `https://`) and an `effective:` date (parsed as YAML `date` type, not str — enforced by `tests/test_reference/test_schema.py` lines 29-35). The 10-YAML count is pinned by `tests/test_reference/test_yaml_count_audit.py` (`EXPECTED_YAML_COUNT = 10`, `EXPECTED_YAML_STEMS` frozenset), with docstring documenting the 7-vs-10 reconciliation per CONTEXT.md D-05 ("Fannie LLPA + Freddie eligibility + ATR-QM thresholds are implementation-detail YAMLs that ship under RUL-02/03/09, NOT new REF-IDs"). Schema test parametrizes over filesystem and runs 10 cases — all pass. |
| 2 | Importing any `lib/rules/*` predicate when its underlying YAML's `effective:` is >12 months old emits a warning to stderr (staleness check) | **VERIFIED** with WARNING-class wording deviation | `lib/rules/_loader.py:34-38` defines `StaleReferenceWarning(UserWarning)`. `_loader.py:90-101` `_check_staleness()` emits the warning via `warnings.warn(..., category=StaleReferenceWarning, stacklevel=2)` whenever `effective < date.today() - relativedelta(months=12)`. Python's `warnings` module routes UserWarning to `sys.stderr` by default — **manually verified live**: `uv run python -W default -c "from lib.rules._loader import load_reference; load_reference('fha-mip-rates')"` printed the warning to stderr with the exact text `StaleReferenceWarning: Reference data 'fha-mip-rates' has effective=2023-03-20, which is more than 12 months old (threshold: 2025-04-26)`. Test coverage: `tests/test_rules/test_loader.py:41-51` `test_staleness_warning_fires_for_old_yaml` (synthetic 730-day-old YAML triggers `pytest.warns(StaleReferenceWarning)`); line 54-64 `test_no_warning_for_fresh_yaml` (30-day-old YAML, simplefilter=error, asserts no warning). Live test-run output confirms the four shipped stale YAMLs (fha-mip-rates 2023-03-20, irs-pub936 2025-01-01, va-funding-fees 2023-04-07, va-residual-income 2023-04-07) emit `StaleReferenceWarning` at first `load_reference()` call. **Wording deviation:** the criterion says "Importing any `lib/rules/*` predicate ... emits a warning"; the actual implementation is lazy — the warning fires on the first `load_reference()` invocation inside the predicate's `compute()`/`status()` etc., not at module-import time. (Verified via `uv run python -W default -c "import lib.rules.fha_mip"` which prints nothing.) Functionally equivalent in practice (every test that actually USES a stale predicate sees the stderr warning), and `_loader.py:35` docstring claims "Emitted at module-load time" which is technically misleading but harmless given the lazy idiom is universal. |
| 3 | `lib.rules.loan_type.classify(amount, county)` returns correct loan_type enum across high-cost-at-ceiling, low-cost-at-baseline, FHA floor, FHA ceiling — and raises `MissingCountyDataError` (loud) when county is None | **VERIFIED** | `lib/rules/loan_type.py:69-92` `classify(loan_amount, county, program, unit_count)` returns `LoanType` (Literal alias from `lib/rules/types.py`). `MissingCountyDataError` defined at line 55-63. Test coverage in `tests/test_rules/test_loan_type.py` (18 tests, all pass): high-cost-at-ceiling → `test_high_balance_in_high_cost_san_francisco` (line 75: `$1,000,000 in SF → high_balance`) + `test_jumbo_above_san_francisco_ceiling` (line 88: `$1.5M in SF > $1,249,125 ceiling → jumbo`); low-cost-at-baseline → `test_low_cost_county_baseline_loan_treated_as_conforming` (line 101: `$750k < $832,750 baseline in Autauga AL → conforming`) + `test_conforming_baseline_no_county_required` (line 63: `$800k ≤ baseline, county=None tolerated → conforming`); FHA floor → `test_fha_program_classifies_below_floor_as_fha_standard` (line 130: `$400k ≤ $541,287 → fha_standard`); FHA ceiling → `test_fha_program_classifies_above_floor_as_fha_high_balance` (line 144: `$700k in SF, $541,287 < $700k ≤ $1,249,125 → fha_high_balance`); MissingCountyDataError loud-fail → line 117 `test_missing_county_when_above_baseline_raises` (`pytest.raises(MissingCountyDataError, match="county required")`), line 169 `test_fha_program_above_floor_missing_county_raises`, line 175 `test_fha_unlisted_county_above_floor_raises_missing_county_data`, line 232 `test_va_program_above_baseline_missing_county_raises`. Implementation defends against silent baseline-defaulting (Pitfall 7) at `loan_type.py:103-107`, `:127-131`, `:156-160`, `:226-230`. |
| 4 | `lib.rules.fha_mip.compute_mip(...)` produces correct UFMIP + annual MIP for both LTV>90% (life-of-loan) and LTV<=90% (11-year termination) per HUD ML 2023-05; `lib.rules.conventional_pmi.terminates_at(...)` returns 78% LTV (auto) and 80% LTV (request) per HPA | **VERIFIED** with WARNING-class function-name deviation | **Behavior fully verified.** FHA MIP: `lib/rules/fha_mip.py:66-120` exposes `compute(loan, original_property_value, endorsement_date) -> MIPResult`, returning `ufmip: Decimal`, `annual_mip_pct: Decimal`, `terminates_at_period: int \| Literal["life_of_loan"]`. LTV>90% life-of-loan branch verified by `tests/test_rules/test_fha_mip.py:51-65` `test_fha_mip_term30_ltv95_post_2023_returns_life_of_loan` (hand-computed LTV=400000/410000≈0.9756 > 0.90 → terminates_at_period == "life_of_loan"). LTV≤90% 11-year (132mo) branch verified by line 68-81 `test_fha_mip_term30_ltv85_post_2023_terminates_at_132mo` (hand-computed LTV=400000/470000≈0.8511 ≤ 0.90 → terminates_at_period == 132). Pre-2023-03-20 endorsement raises NotImplementedError (line 100-110, fixture `fha_mip_pre_2023_raises.json`). HUD ML 2023-05 cited in module docstring (`lib/rules/fha_mip.py:1-7`). All 10 fha_mip tests pass. Conventional PMI: `lib/rules/conventional_pmi.py:61-126` exposes `status(loan, scheduled_balance, original_property_value, is_high_risk, months_elapsed) -> PMITerminationStatus`. Statutory 0.78 / 0.80 thresholds embedded as `Final[Decimal]` constants (lines 57-58, citing 12 USC §4902(b) and §4902(a)). 78% auto-terminate verified by `test_conventional_pmi.py:52-63` `test_auto_terminates_at_exact_78_ltv` ($156k/$200k = 0.78 exactly → "auto_terminated"). 80% request-eligible verified by line 65-76 `test_request_eligible_at_exact_80_ltv` ($160k/$200k = 0.80 exactly → "request_eligible"). HPA §4902(g) high-risk midpoint carve-out covered by line 91-97 `test_high_risk_terminates_at_midpoint`. All 11 conventional_pmi tests pass. **Wording deviation:** ROADMAP SC says `compute_mip(...)` and `terminates_at(...)`; the implementation ships `compute(...)` and `status(...)`. This rename is documented in plan 02-02 line 26-27 ("`lib.rules.fha_mip.compute(loan, original_property_value, endorsement_date)`") and plan 02-05 line 33-36 ("`lib.rules.conventional_pmi.status(...)`") — plans are authoritative; the SC text in ROADMAP.md was not updated. CONTEXT.md lines 163-164 and 02-07-PLAN.md line 144 still reference the old names — these are stale doc-only references that should be reconciled when Phase 4 (Affordability) and Phase 6 (Refi NPV) actually wire the predicates. No external caller currently uses `compute_mip` or `terminates_at` symbol (verified by `grep -r`). |
| 5 | Every predicate file has a docstring with a regulatory citation, and every citation has at least one passing test fixture (verified by `tests/test_rules/test_citation_coverage.py`) | **VERIFIED** | `tests/test_rules/test_citation_coverage.py:27-48` parametrizes over `_predicate_modules()` (filesystem-introspecting; auto-includes any new predicate). Two parametrized tests per predicate: `test_predicate_has_citation_in_docstring` asserts `"Citation:"`, `"Source URL:"`, `"Effective:"`, and `r"https?://"` all appear in the module docstring; `test_predicate_has_at_least_one_fixture` asserts ≥1 fixture under `tests/fixtures/rules/{stem}_*.json`. Live run: `uv run pytest tests/test_rules/test_citation_coverage.py -v` → **22 passed in 0.02s** (11 predicates × 2 tests each). Predicate roster verified by `tests/test_rules/test_phase2_smoke.py:35-47` `EXPECTED_PREDICATE_MODULES` (11 entries pinned, filesystem-cross-checked). Fixture inventory: 60 JSON files in `tests/fixtures/rules/` distributed across all 11 predicates. **Mutation-tested teeth:** `tests/test_rules/test_citation_coverage_mutations.py` ships 7 tests (RUL-12/RUL-13 audit gate per plan 02-07) that clone the repo to `tmp_path`, mutate one citation line / fixture / YAML field, and run the meta-test as a subprocess to confirm it fails. All 7 mutation tests pass — confirms the meta-tests genuinely catch their regression class. Citation headers spot-checked across all 11 predicates: `Citation:` line present + `Source URL:` ending in real http(s) URL + `Effective:` date present. |

## Requirement Traceability Table

Every phase requirement ID is marked Done in REQUIREMENTS.md (lines 224-245) and points to a real artifact:

| Requirement | Tracked As | Predicate / YAML File | Status | Evidence |
|---|---|---|---|---|
| REF-01 | Done (02-01) | `data/reference/conforming-limits-2026.yml` | SATISFIED | source: FHFA 2026 release, effective: 2026-01-01; loaded by `loan_type._classify_conventional` |
| REF-02 | Done (02-02) | `data/reference/fha-limits-2026.yml` | SATISFIED | source: HUD ML 2025-23, effective: 2026-01-01; loaded by `loan_type._classify_fha` |
| REF-03 | Done (02-02) | `data/reference/fha-mip-rates.yml` | SATISFIED | source: HUD ML 2023-05, effective: 2023-03-20; loaded by `fha_mip.compute` |
| REF-04 | Done (02-03) | `data/reference/va-funding-fees.yml` | SATISFIED | source: VA Lender Handbook M26-7 ch.8, effective: 2023-04-07; loaded by `va_funding_fee` |
| REF-05 | Done (02-03) | `data/reference/va-residual-income.yml` | SATISFIED | source: VA M26-7, effective: 2023-04-07; loaded by `va_residual_income` |
| REF-06 | Done (02-04) | `data/reference/usda-income-limits.yml` | SATISFIED | source: USDA RD eligibility, effective: 2025-10-01; loaded by `usda` |
| REF-07 | Done (02-04) | `data/reference/irs-pub936.yml` | SATISFIED | source: IRS Pub 936, effective: 2025-01-01; loaded by `irs_pub936` |
| REF-08 | Done (02-01) | `lib/rules/_loader.py` `StaleReferenceWarning` | SATISFIED | `_check_staleness()` at `_loader.py:90-101`; tested by `test_loader.py:41-51` |
| REF-09 | Done (02-01) | `tests/test_reference/test_schema.py` | SATISFIED | parametrized over `_ref_files()`, asserts `source` (http URL) + `effective` (date type) on all 10 YAMLs |
| RUL-01 | Done (02-01) | `lib/rules/loan_type.py` | SATISFIED | `classify(...)` + `MissingCountyDataError`; 18 tests pass |
| RUL-02 | Done (02-05) | `lib/rules/fannie_eligibility.py` | SATISFIED | LLPA matrix lookup; 17 tests pass; cites Fannie Mae LLPA Matrix §B5-1 |
| RUL-03 | Done (02-05) | `lib/rules/freddie_eligibility.py` | SATISFIED | LPA-equivalent eligibility; 11 tests pass; cites Freddie SF Seller/Servicer Guide §4203.4 |
| RUL-04 | Done (02-02) | `lib/rules/fha_mip.py` | SATISFIED | UFMIP + annual MIP per HUD ML 2023-05 + termination per HUD ML 2013-04; 10 tests pass |
| RUL-05 | Done (02-05) | `lib/rules/conventional_pmi.py` | SATISFIED | HPA §4902(a)/(b)/(g); 11 tests pass |
| RUL-06 | Done (02-03) | `lib/rules/va_funding_fee.py` | SATISFIED | 38 USC §3729 + VA M26-7; 12 tests pass |
| RUL-07 | Done (02-03) | `lib/rules/va_residual_income.py` | SATISFIED | VA M26-7 Topic 7; 7 tests pass |
| RUL-08 | Done (02-04) | `lib/rules/usda.py` | SATISFIED | 7 CFR Part 3555; 8 tests pass |
| RUL-09 | Done (02-06) | `lib/rules/atr_qm.py` | SATISFIED | 12 CFR §1026.43(e)(2) Mar 2021 final rule; 14 tests pass |
| RUL-10 | Done (02-06) | `lib/rules/reg_z.py` | SATISFIED | 12 CFR §1026.22(a)(2)/(a)(3); 10 tests pass |
| RUL-11 | Done (02-04) | `lib/rules/irs_pub936.py` | SATISFIED | IRC §163(h)(3) post-TCJA $750k cap; 10 tests pass |
| RUL-12 | Done (02-01) | `tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring` | SATISFIED | 11 parametrized cases, all pass; mutation-tested via `test_citation_coverage_mutations.py` |
| RUL-13 | Done (02-01) | `tests/test_rules/test_citation_coverage.py::test_predicate_has_at_least_one_fixture` | SATISFIED | 11 parametrized cases, all pass; 60 fixtures across `tests/fixtures/rules/` |

**Orphaned requirements:** None. Every ID in the phase contract has a SATISFIED entry pointing at a real predicate or YAML.

## Test Runs Executed During Verification

| Command | Result | Purpose |
|---|---|---|
| `uv run pytest -q` | 254 passed, 4 stale-ref warnings, 0 failures, 8.48s | Full test-suite regression — confirms 02-REVIEW-FIX claim of 254/254 |
| `uv run pytest tests/test_reference/test_schema.py tests/test_rules/test_loader.py tests/test_rules/test_loan_type.py tests/test_rules/test_fha_mip.py tests/test_rules/test_conventional_pmi.py -q` | 65 passed, 1 stale-ref warning, 0.17s | Targeted run for must_haves 1-4 |
| `uv run pytest tests/test_rules/test_citation_coverage.py -v` | 22 passed in 0.02s | Per-predicate citation header + fixture audit (must_have 5) |
| `uv run pytest tests/test_rules/test_citation_coverage_mutations.py -v` | 7 passed in 8.14s | Confirms the citation-coverage meta-tests genuinely fail when mutated |
| `uv run pytest --collect-only -q \| tail -5` | 254 tests collected | Pins total test count |
| `uv run python -W default -c "from lib.rules._loader import load_reference; load_reference('fha-mip-rates')" 2>&1` | Prints `StaleReferenceWarning: ... fha-mip-rates ... more than 12 months old ...` to stderr | Live confirmation that staleness emits to stderr (must_have 2) |
| `uv run python -W default -c "import lib.rules.fha_mip" 2>&1` | empty output | Confirms staleness is lazy (fires on `load_reference()`, not on module import) — minor wording deviation noted under must_have 2 |
| `grep -E "^(source\|effective):" data/reference/*.yml` | 10 source: + 10 effective: lines, all source URLs https | Confirms must_have 1 schema across all 10 YAMLs |

## Deviations from ROADMAP Success Criteria (Documented)

Two deviations were identified between the literal ROADMAP success-criterion wording and what shipped. Both are documented in plans/CONTEXT and pinned by audit tests; neither changes any required behavior.

1. **YAML count drift 7 → 10.** ROADMAP SC #1 says "All seven `data/reference/*.yml` files load successfully"; the actual ship is 10 YAMLs. The extra three (`fannie-llpa-matrix`, `freddie-eligibility-matrix`, `atr-qm-thresholds`) are documented in CONTEXT.md D-05 as "implementation-detail YAMLs that ship under RUL-02/03/09, NOT new REF-IDs." Pinned by `tests/test_reference/test_yaml_count_audit.py` (`EXPECTED_YAML_COUNT = 10`). All 10 satisfy the schema (source URL + effective date) per `test_schema.py`. **Behavior intent of SC #1 is satisfied:** every reference YAML loads and carries source/effective.

2. **Function-name drift in must_have 4.** ROADMAP SC #4 says `fha_mip.compute_mip(...)` and `conventional_pmi.terminates_at(...)`; implementation ships `fha_mip.compute(...)` and `conventional_pmi.status(...)`. The plans (02-02 line 26-27, 02-05 lines 33-36) are authoritative and use the new names; the ROADMAP wording was not updated. **Behavior intent is satisfied** — UFMIP + annual MIP for both LTV brackets per HUD ML 2023-05 are correctly computed by `compute()`; 78% / 80% LTV thresholds per HPA §4902(b)/(a) are correctly returned by `status()`. **Stale doc references** in CONTEXT.md lines 163-164 and 02-07-PLAN.md line 144 still call out the old API names — these should be reconciled when Phase 4 (Affordability) wires `fha_mip` and Phase 6 (Refi NPV) wires `conventional_pmi`. No live code currently imports either old name (verified via repo-wide grep).

## Anti-Patterns Scanned

Spot-checked all 11 predicate files and all 10 reference YAMLs for `TODO|FIXME|XXX|HACK|placeholder|coming soon|return None\|return \[\]\|=> {}` patterns. **None found** in production code (`lib/rules/*.py`, `data/reference/*.yml`). Test files contain expected `pytest.raises` and fixture-driven hand calculations — no stub returns or empty dicts that flow into business logic.

The `lib/rules/_loader.py` `lru_cache` clearing pattern (`tests/test_rules/test_loader.py:29-38`, `cache_clear()` before AND after each test) was added in WR-07 of 02-REVIEW.md and prevents synthetic-test contamination — verified clean.

## Behavioral Spot-Checks

| Behavior (from must_haves) | Command | Result | Status |
|---|---|---|---|
| Reference YAMLs all carry source + effective | `for f in data/reference/*.yml; do grep -E "^(source\|effective):" "$f"; done` (10 files × 2 lines) | 20/20 lines present | PASS |
| Stale YAML triggers warning to stderr | `uv run python -W default -c "from lib.rules._loader import load_reference; load_reference('fha-mip-rates')" 2>&1` | Prints exact `StaleReferenceWarning: Reference data 'fha-mip-rates' has effective=2023-03-20, which is more than 12 months old (threshold: 2025-04-26). Annual regulatory refresh may be overdue.` | PASS |
| Pure module import does NOT auto-warn | `uv run python -W default -c "import lib.rules.fha_mip" 2>&1` | empty | PASS-with-deviation-note (lazy warning, not import-time) |
| Loan-type classify is callable + raises MissingCountyDataError | `tests/test_rules/test_loan_type.py::test_missing_county_when_above_baseline_raises` | PASS | PASS |
| FHA MIP compute returns life_of_loan for LTV>90% | `tests/test_rules/test_fha_mip.py::test_fha_mip_term30_ltv95_post_2023_returns_life_of_loan` | PASS | PASS |
| Conventional PMI status returns auto_terminated at 0.78 LTV | `tests/test_rules/test_conventional_pmi.py::test_auto_terminates_at_exact_78_ltv` | PASS | PASS |
| Citation coverage meta-test passes for all 11 predicates | `uv run pytest tests/test_rules/test_citation_coverage.py -v` | 22/22 PASS | PASS |
| Citation coverage meta-test has teeth | `uv run pytest tests/test_rules/test_citation_coverage_mutations.py -v` | 7/7 PASS | PASS |

## Human Verification Items

**None.** Phase 2 is pure backend Python (no UI, no real-time behavior, no external service calls). All success criteria are testable via deterministic Decimal-equality assertions and filesystem audits, all of which run in CI via `uv run pytest`. The 02-REVIEW-FIX pass already closed all 14 review findings (5 BLOCKERS + 9 WARNINGS); no human judgment is required to ratify the fixes — the +30 regression tests (224 → 254) pin them.

## Gaps Section

**No gaps.** All 5 must_haves resolve to VERIFIED. The two wording-vs-implementation deviations (YAML count, function names) are documented in plans, captured by audit tests, and do not change any required behavior. Stale doc references in CONTEXT.md and 02-07-PLAN.md (mentioning `compute_mip` / `terminates_at` rather than `compute` / `status`) should be rewritten when Phase 4 / Phase 6 land their callers — flagged here for the orchestrator but not blocking.

---

_Verified: 2026-04-27T05:45:06Z_
_Verifier: Claude (gsd-verifier, sonnet model)_
