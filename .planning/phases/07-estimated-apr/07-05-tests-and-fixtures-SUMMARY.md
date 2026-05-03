---
phase: 07-estimated-apr
plan: 05
subsystem: tests-and-fixtures
tags:
  - phase-07
  - estimated-apr
  - tests
  - fixtures
  - sc-1-anchor
  - sc-3-anchor
  - reg-z-appendix-j
  - apr-05

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Decimal-from-string discipline + lib/money.MONEY_CONTEXT (for Decimal arithmetic in fixture round-trips)"
  - phase: 07-estimated-apr (Plan 07-01)
    provides: "APRRequest + APRResponse + AdvanceScheduleEntry + PaymentScheduleEntry boundary models"
  - phase: 07-estimated-apr (Plan 07-02)
    provides: "solve_apr Newton-Raphson body + _decimal_pow + APRConvergenceError (Wave 5 hand-calc fixtures exercise the full solver path)"
  - phase: 07-estimated-apr (Plan 07-03)
    provides: "_compute_odd_first_period_fraction + APRRequest.odd_first_period_days wiring (the 15-day and 45-day fixtures exercise this surface)"
  - phase: 07-estimated-apr (Plan 07-04)
    provides: "scripts/apr_reg_z.py CLI (Wave-4 inline-stub tests for round-trip + literal-text are now backed by fixtures shipped this wave; existing inline tests not yet swapped per plan scope — left for Wave 6 or follow-up)"
  - phase: 07-estimated-apr (Plan 07-00)
    provides: "13 Wave-0 xfail-strict stubs in tests/test_apr.py — this wave flips 2 (APR-05 SC-1 + SC-3 iteration cap)"
provides:
  - "tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json (SC-1 anchor fixture: $5000/36/$166.07 → 12.00% APR per D-25 LOCKED regulatory value)"
  - "tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json (Wave 3 odd-period coverage; D-24 engine-emitted 0.065002)"
  - "tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json (D-26 NEGATIVE-path fixture: f=1.5 raises ValueError per D-16)"
  - "tests/fixtures/apr/regz_appendix_j_unit_period_monthly_regular.json (Wikipedia regular monthly sanity; D-24 engine = nominal 0.065000)"
  - "2 Wave-0 stubs flipped to PASS: test_apr_reg_z_appendix_j_worked_example_returns_12_percent (APR-05/SC-1) + test_newton_raphson_iterations_under_50_for_all_fixtures (SC-3 cross-cutting)"
  - "test_apr_hand_calc_fixtures_match_expected (parametric over 2 hand-calc anchors; D-27 reserves Wave 7 expansion to HMDA Platform fixtures)"
  - "test_odd_first_period_too_long_raises (negative-path sibling for the 45-day fixture)"
  - "test_decimal_pow_fractional_exponent_correctness (D-13 sanity guard for the load-bearing _decimal_pow helper)"
affects:
  - 07-06-references-doc (references/apr-reg-z.md §4 worked-example section will cite the SC-1 anchor fixture)
  - 07-07-ffiec-fixtures (Wave 7 will add a parallel parametric test for the 20+ HMDA Platform oracle fixtures per D-27 — D-27 explicitly reserves the parametric expansion to a separate test function)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSON fixture schema {description, citation, request, expected} per D-23 (Phase 4 04-06 fixture idiom verbatim)"
    - "Engine-emitted value pinning per D-24 (Phase 4 04-06 idiom): 15-day + Wikipedia regular fixtures use the engine's exact output as the pinned expected value (avoids hand-calc rounding drift); SC-1 anchor is the EXCEPTION per D-25"
    - "Regulatory-value pinning per D-25 LOCKED: SC-1 anchor expected.estimated_apr is Decimal('0.120000') (the Reg Z Appendix J Example J(c)(1) published value), NOT the engine-emitted value 0.119994 — engine MUST agree within Decimal('0.00001'), and any wider divergence is a P0 release blocker"
    - "Negative-path fixture pattern per D-26: the 45-day fixture documents inputs + expected ValueError shape (raises + message_substring), not solver output; sibling test_odd_first_period_too_long_raises asserts the engine boundary"
    - "JSON-string-typed payload + APRRequest.model_validate_json round-trip (matches scripts/apr_reg_z.py:138 CLI body verbatim) — strict-mode Pydantic validation with Decimal-from-string discipline"
    - "Parametric per-fixture coverage scoped to a single test function (D-27 reserves separate parametric for HMDA Platform fixtures in Wave 7; mirrors Phase 5 oracle vs hand-calc test split)"
    - "pytest.raises with match=re.escape(substring) per ruff PT011 — replaces bare pytest.raises(ValueError) with a documented substring match contract"

key-files:
  created:
    - tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json
    - tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json
    - tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json
    - tests/fixtures/apr/regz_appendix_j_unit_period_monthly_regular.json
  modified:
    - tests/test_apr.py

key-decisions:
  - "D-23 honored: fixture format = {description, citation, request, expected}; mirrors Phase 4 04-06 fixture convention verbatim across all 4 shipped files"
  - "D-24 honored: 15-day odd-period fixture (engine = 0.065002) and Wikipedia regular fixture (engine = 0.065000 = nominal exactly) use engine-emitted values pinned at first compute"
  - "D-25 LOCKED honored: SC-1 anchor uses regulatory value Decimal('0.120000'); engine emits 0.119994 in 1 iteration; |engine - regulatory| = Decimal('0.000006') < Decimal('0.00001') tolerance — within SC-1 contract"
  - "D-26 honored: 45-day odd-period fixture is a NEGATIVE-path fixture (f = 45/30 = 1.5 violates D-16); sibling test asserts ValueError boundary"
  - "D-27 honored: parametric coverage shipped initially with 2 cases (SC-1 anchor + Wikipedia regular); Wave 7 will add a parallel parametric test for the 20+ HMDA Platform oracle fixtures (mirrors Phase 5 oracle vs hand-calc split)"
  - "Auto-fix [Rule 1 — Bug fix in plan spec]: Plan §Task 2 pinned 15-day fixture with min/max range Decimal('0.065100')..Decimal('0.065500'). Plan 07-03 SUMMARY (Rule-1 informational) had ALREADY corrected RESEARCH §Q(e)'s back-of-envelope ~6.523% forecast — the actual engine output is 0.065002, BELOW the plan's 0.065100 floor. Followed plan §Task 2 'NOTE' verbatim (engine-emitted Decimal-string values pinned at first compute and the JSON expected_apr is set to the engine's exact output) per D-24, plus the executor prompt's important_notes guidance ('the fixture's expected.estimated_apr should reflect the ENGINE's emitted value, not 0.06523'). The min/max range was a residual back-of-envelope artifact in the plan code block, superseded by the Wave 3 SUMMARY's empirical correction; D-24 ships the engine value 0.065002 with documentary note explaining the magnitude correction (engine direction is correct: APR > 6.50% nominal; magnitude is +0.0002 pp, not +0.023 pp)."
  - "Auto-fix [Rule 3 — Hygiene] ruff PT011: bare pytest.raises(ValueError) too broad in test_odd_first_period_too_long_raises; added match=re.escape(msg_substring) parameter (uses the fixture's documented expected.message_substring as the regex match pattern); belt-and-suspenders 'in str(excinfo.value)' substring assert preserved"
  - "Auto-fix [Rule 3 — Hygiene] ruff format: 1 mechanical reformat applied to tests/test_apr.py after the Wave-0 stub flips landed (canonical line-wrapping; no semantic change)"

patterns-established:
  - "Plan 07-05 establishes the Phase 7 hand-calc fixture corpus: 3 positive-path (SC-1 anchor + 15-day odd + Wikipedia regular) + 1 negative-path (45-day odd raises ValueError). All 4 use the {description, citation, request, expected} schema per D-23"
  - "D-25 establishes the regulatory-anchor exception to the engine-emitted-value default: SC-1 anchor stays anchored to the regulation, not the engine — any future engine drift > Decimal('0.00001') from 0.120000 is a P0 release blocker pinned by the SC-1 test"
  - "D-26 establishes the negative-path fixture idiom (raises + message_substring) for cases where engine boundary enforcement is the contract under test (rather than a numeric APR output)"
  - "Sibling tests pin engine helpers (test_decimal_pow_fractional_exponent_correctness) AND engine boundary errors (test_odd_first_period_too_long_raises) at the same wave that ships the fixtures that exercise them — keeps the regression surface tight"

requirements-completed:
  - APR-05  # Reg Z Appendix J Example J-1 worked example fixture shipped + SC-1 anchor test asserts engine within Decimal('0.00001') of regulatory 0.120000

# Metrics
duration: 4min 41s
completed: 2026-05-03
---

# Phase 7 Plan 5: Tests and Fixtures Summary

**Phase 7 Wave 5 ships the hand-calc fixture corpus + flips the SC-1 + SC-3 anchor tests: 4 JSON fixtures (SC-1 anchor `regz_appendix_j_5000_36_166_07` per D-25 LOCKED regulatory value `0.120000`; 15-day odd-period engine-emitted `0.065002` per D-24; 45-day NEGATIVE-path raises ValueError per D-26; Wikipedia regular engine = nominal `0.065000` exactly per D-24) + 6 newly-passing tests (2 Wave-0 stub flips: `test_apr_reg_z_appendix_j_worked_example_returns_12_percent` [APR-05/SC-1] + `test_newton_raphson_iterations_under_50_for_all_fixtures` [SC-3 sweep]; 4 new tests: parametric `test_apr_hand_calc_fixtures_match_expected` over 2 anchors, sibling `test_odd_first_period_too_long_raises` for the 45-day fixture, `test_decimal_pow_fractional_exponent_correctness` D-13 helper sanity guard). 11 of 13 Wave-0 stubs now flipped (APR-04 stays xfail until Wave 7; APR-08 stays xfail until Wave 6). Suite 481 passed (was 475; +6 net pass) / 4 skipped / 3 xfailed (was 5; -2 corresponding to the Wave-0 flips); zero regression. APR-05 closed.**

## Performance

- **Duration:** 4 min 41 s
- **Started:** 2026-05-03T21:04:44Z
- **Completed:** 2026-05-03T21:09:25Z
- **Tasks:** 6 atomic commits (Tasks 1-5 mapped 1:1 to commits; Tasks 6-7 + the Task 3 sibling negative-path test bundled into a single commit `d3d3a14` because they all share the same test-file edit)
- **Files created:** 4 (the JSON fixture corpus)
- **Files modified:** 1 (`tests/test_apr.py`, 633 → 753 lines net of ruff format; +6 tests, -2 xfail decorators)

## Accomplishments

- **Shipped the SC-1 anchor fixture** `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` per D-25 LOCKED. Reg Z Appendix J Example J(c)(1) inputs ($5000 / 36 monthly $166.07) with `expected.estimated_apr = "0.120000"` (the regulatory-publication value). Engine emits 0.119994 in 1 iteration; |engine - regulatory| = Decimal('0.000006') (within SC-1 tolerance Decimal('0.00001')).
- **Shipped 3 sibling fixtures** to round out the Phase 7 hand-calc corpus:
  - `regz_appendix_j_odd_first_period_15_days.json` — D-24 engine-emitted 0.065002 (Wave 3 odd-period coverage; corrects RESEARCH ~6.523% back-of-envelope forecast which Plan 07-03 SUMMARY already flagged as ~100x off in magnitude — actual bump is +0.0002 pp, engine math is correct).
  - `regz_appendix_j_odd_first_period_45_days.json` — D-26 NEGATIVE-path fixture (f = 45/30 = 1.5 violates D-16 helper boundary; engine raises ValueError with documented message substring).
  - `regz_appendix_j_unit_period_monthly_regular.json` — D-24 Wikipedia $200k @ 6.5% / 30yr regular monthly; engine emits 0.065000 = nominal exactly in 1 iteration (sanity check that the U-equation collapses to the standard PV form when there is no odd period and no finance charges).
- **Flipped 2 Wave-0 xfail stubs to real assertions:**
  - `test_apr_reg_z_appendix_j_worked_example_returns_12_percent` (APR-05 / SC-1) — loads `regz_appendix_j_5000_36_166_07.json` via `apr_fixture(...)` + `APRRequest.model_validate_json(json.dumps(fix["request"]))` (matches the CLI body); asserts |response.estimated_apr - Decimal('0.120000')| <= Decimal('0.00001').
  - `test_newton_raphson_iterations_under_50_for_all_fixtures` (SC-3 cross-cutting) — sweeps the 3 positive-path fixtures (SC-1 anchor + 15-day odd + Wikipedia regular); asserts each converges in [1, 50] Newton iterations. Wave 7 will add a parallel sweep over the 20+ HMDA Platform fixtures via a separate parametric per D-27.
- **Added 4 new tests:**
  - `test_apr_hand_calc_fixtures_match_expected` (Task 6 parametric coverage) — parametric over 2 cases (SC-1 anchor at Decimal('0.120000') + Wikipedia regular at Decimal('0.065000')); asserts engine output within Decimal('0.00001'). The 15-day fixture is excluded from this parametric because its expected value (0.065002) is engine-emitted (D-24) and exercising it through `_unit_period_equation`'s `(1+f*i)` factor is already pinned by the Wave 3 sign-flip detector test + the iteration-cap sweep.
  - `test_odd_first_period_too_long_raises` (Task 3 sibling) — exercises the 45-day NEGATIVE-path fixture; asserts `pytest.raises(ValueError, match=re.escape(msg_substring))` with the fixture's documented `expected.message_substring`.
  - `test_decimal_pow_fractional_exponent_correctness` (Task 7 — D-13 sanity) — pinned regression guard: `_decimal_pow(2, 0.5)` ≈ sqrt(2) within Decimal('0.0000001'). The Newton body uses `_decimal_pow` for every `(1+i)^(-t-f)` term; pinning sqrt(2) catches order-of-magnitude regressions before the SC-1 anchor test runs (cheaper failure surface).
- **Suite count after:** 481 passed (was 475; +6 net pass exactly per the 6 newly-passing tests) / 4 skipped (unchanged) / 3 xfailed (was 5; -2 corresponding to the Wave-0 stub flips) / 0 failed / 0 errors. Zero regression to Plan 07-04 baseline.
- **`tests/test_apr.py` mypy --strict + ruff check + ruff format --check all clean** post-commit.

## Task Commits

Each task committed atomically against `main` (sequential executor; no branching per `parallelization=false`; no AI attribution per global + project CLAUDE.md):

1. **Task 1: Ship SC-1 anchor fixture** — `25750a2` (feat)
2. **Task 2: Ship 15-day odd-period fixture** — `9a4e746` (feat)
3. **Task 3: Ship 45-day NEGATIVE-path fixture** — `0690903` (feat)
4. **Task 4: Ship Wikipedia regular sanity fixture** — `27f35cf` (feat)
5. **Task 5: Flip 2 Wave-0 stubs (SC-1 + SC-3)** — `3cce166` (test)
6. **Tasks 6+7+sibling: parametric coverage + 45-day sibling + _decimal_pow sanity** — `d3d3a14` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` (**created**, 29 lines) — SC-1 anchor; expected.estimated_apr = "0.120000" per D-25 LOCKED regulatory value
- `tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json` (**created**, 29 lines) — D-24 engine-emitted 0.065002 (corrects RESEARCH back-of-envelope forecast)
- `tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json` (**created**, 28 lines) — D-26 NEGATIVE-path; expected.raises = "ValueError"
- `tests/fixtures/apr/regz_appendix_j_unit_period_monthly_regular.json` (**created**, 29 lines) — D-24 Wikipedia regular sanity; engine = nominal 0.065000 exactly
- `tests/test_apr.py` (**modified**) — 2 Wave-0 stubs flipped + 4 new tests appended (parametric, 45-day sibling, decimal_pow sanity)

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|-------------|--------|--------|
| `ls tests/fixtures/apr/*.json` | 4 files | 4 files (regz_appendix_j_*: 5000_36_166_07, odd_first_period_15_days, odd_first_period_45_days, unit_period_monthly_regular) | PASS |
| `pytest tests/test_apr.py::test_apr_reg_z_appendix_j_worked_example_returns_12_percent -v` | PASS | PASS | PASS |
| `pytest tests/test_apr.py::test_newton_raphson_iterations_under_50_for_all_fixtures -v` | PASS | PASS | PASS |
| `pytest tests/test_apr.py::test_apr_hand_calc_fixtures_match_expected -v` (2 cases) | 2 PASS | 2 PASS | PASS |
| `pytest tests/test_apr.py::test_decimal_pow_fractional_exponent_correctness -v` | PASS | PASS | PASS |
| `pytest tests/test_apr.py::test_odd_first_period_too_long_raises -v` | PASS | PASS | PASS |
| `mypy --strict tests/test_apr.py` | clean | clean | PASS |
| `ruff check tests/test_apr.py` | clean | clean | PASS |
| `ruff format --check tests/test_apr.py` | clean | "1 file already formatted" | PASS |
| Stubs flipped (cumulative) | 11 of 13 (APR-04 + APR-08 stay xfail) | 11 of 13 (xfail count: 2 in test_apr.py = APR-04 + APR-08 exactly) | PASS |
| Full-suite `pytest -q` | >=432 + 11 + 2 xfailed (and >=461 executor floor) | 481 passed / 4 skipped / 3 xfailed / 0 failed / 0 errors | PASS |
| SC-1 anchor: \|response.estimated_apr - Decimal('0.120000')\| <= Decimal('0.00001') | within 0.00001 | engine 0.119994; diff 0.000006 (within tolerance) | PASS |

## Decisions Made

Followed the plan's 5 LOCKED DECISIONS (D-23..D-27) verbatim. Smoke-test invariants validated empirically before each commit:

- **After Task 1 (SC-1 anchor fixture):** `APRRequest.model_validate_json(json.dumps(fix["request"]))` succeeds; `solve_apr` returns 0.119994 in 1 iteration; |engine - Decimal('0.120000')| = Decimal('0.000006') (within Decimal('0.00001')); iterations=1 within `iterations_max=5`.
- **After Task 2 (15-day odd):** engine emits 0.065002 in 2 iterations; matches `expected.estimated_apr` exactly (D-24 engine-emitted pinning).
- **After Task 3 (45-day negative-path):** `solve_apr` raises `ValueError` with message containing `"odd_first_period_days (45) >= 1 unit period"` (the documented `expected.message_substring`).
- **After Task 4 (Wikipedia regular):** engine emits 0.065000 = nominal exactly in 1 iteration; sanity check that no-odd-period + no-finance-charges case collapses to the standard PV form.
- **After Task 5 (stub flips):** SC-1 stub passes (engine within tolerance of regulatory anchor); SC-3 sweep passes (3 fixtures all within [1, 50] iterations).
- **After Tasks 6+7+sibling:** parametric coverage passes (2 cases); 45-day sibling raises ValueError with match pattern; `_decimal_pow(2, 0.5)` = 1.4142135... within Decimal('0.0000001') of 1.41421356.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug fix in plan spec] Plan §Task 2 min/max range for 15-day fixture is wrong (~100x magnitude error)**

- **Found during:** Task 2 (writing the fixture file from the plan's JSON template)
- **Issue:** Plan §Task 2 JSON template specifies:
  ```json
  "expected": {
    "estimated_apr_min": "0.065100",
    "estimated_apr_max": "0.065500",
    ...
  }
  ```
  This range comes from RESEARCH §Q(e) Example 2 ("APR ≈ 6.523%"). Plan 07-03 SUMMARY (Rule-1 informational) had **already** corrected this back-of-envelope forecast — the actual engine output is `0.065002` (≈6.5002%), which is **below** the plan's `0.065100` floor. Pinning the fixture with that min/max range would have produced a fixture that the engine's correct output FAILS, blocking SC-3 sweep + parametric tests until either the fixture or the engine were "fixed" (the engine is correct).
- **Fix:** Followed Plan §Task 2's NOTE verbatim (which immediately follows the JSON template in the plan body): *"per Phase 4 04-06 idiom — engine-emitted Decimal-string values are pinned at first compute and the JSON `expected_apr` is set to the engine's exact output. Plan execution captures `solve_apr` output and writes it back into the fixture as `expected.estimated_apr` to seal."* Plus the executor prompt's important_notes guidance: *"the fixture's expected.estimated_apr should reflect the ENGINE's emitted value (cross-validated against HMDA Platform per CONTEXT D-09), not 0.06523."* So I shipped `expected.estimated_apr = "0.065002"` per D-24 with a fixture `note` documenting the magnitude correction. The min/max range from the plan code block was a residual artifact superseded by the plan's own NOTE + the executor prompt's important_notes + Plan 07-03 SUMMARY's empirical correction.
- **Files modified:** `tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json` (Task 2 commit `9a4e746`)
- **Verification:** Engine emits 0.065002; fixture's pinned value 0.065002; SC-3 sweep + (future Wave-7) HMDA cross-validation will catch any drift.
- **Plan deviation rule:** Rule-1 (bug fix in plan spec — the min/max range was arithmetically incorrect; the plan's NOTE + Plan 07-03's correction + the executor prompt all converge on D-24 engine-emitted pinning). Wave 7 HMDA Platform cross-validation (per CONTEXT D-09) is the definitive check — divergence > Decimal('0.00001') means the engine is wrong, and we'd revisit then. Until then, engine-emitted is the contract per D-24.

**2. [Rule 3 — Hygiene] ruff PT011 — bare `pytest.raises(ValueError)` too broad in `test_odd_first_period_too_long_raises`**

- **Found during:** Tasks 6+7 commit prep (`uv run ruff check tests/test_apr.py`)
- **Issue:** ruff PT011 flags `with pytest.raises(ValueError) as excinfo:` as too broad — the rule wants a `match=...` parameter or a more specific exception subclass. Without a match, a different ValueError (e.g., from a Pydantic validation downstream) could falsely satisfy the test.
- **Fix:** Added `match=re.escape(msg_substring)` parameter where `msg_substring` is loaded from the fixture's `expected.message_substring` (`"odd_first_period_days (45) >= 1 unit period"`). Kept the belt-and-suspenders `assert msg_substring in str(excinfo.value)` substring assert as documentation; the `match=` parameter is the regex-search contract, the substring assert is the literal-substring contract.
- **Files modified:** `tests/test_apr.py` (Tasks 6+7 commit `d3d3a14`)
- **Verification:** `ruff check tests/test_apr.py` → "All checks passed!"; `pytest tests/test_apr.py::test_odd_first_period_too_long_raises -v` → PASS.
- **Plan deviation rule:** Rule-3 (hygiene only — adds a more precise contract; no semantic change to the test's purpose).

**3. [Rule 3 — Hygiene] ruff format auto-applied 1 reformat after Wave-0 stub flips landed**

- **Found during:** Task 5 commit prep (`uv run ruff format --check tests/test_apr.py` flagged "1 file would be reformatted" after the two stub flips' inline assertion bodies landed)
- **Issue:** Hand-written code had minor whitespace / line-wrap differences from ruff's canonical output (the stub flips replaced `pytest.fail("Wave 0 stub")` 1-liners with multi-line assertion bodies; ruff format wanted to canonicalize one f-string line wrap).
- **Fix:** `uv run ruff format tests/test_apr.py` (mechanical; no semantic change).
- **Files modified:** `tests/test_apr.py` (Task 5 commit `3cce166`)
- **Verification:** `ruff format --check tests/test_apr.py` → "1 file already formatted" post-fix.
- **Plan deviation rule:** Rule-3 (hygiene; mechanical reformat).

---

**Total deviations:** 3 (1 Rule-1 bug fix in plan spec — 15-day min/max range was ~100x magnitude error; followed plan's own NOTE + executor important_notes to ship D-24 engine-emitted value; 2 Rule-3 hygiene — ruff PT011 + ruff format).

**Impact on plan:** All plan acceptance gates PASS. The Rule-1 finding is a continuation of Plan 07-03 SUMMARY's Rule-1 informational deviation (which Plan 07-03 had explicitly forecast as "Wave 5 will pin via HMDA Platform oracle") — Wave 5 follows the explicitly-flagged Wave-3-to-Wave-5 baton handoff to ship the engine-emitted value with documentary correction notes. Wave 7 HMDA Platform cross-validation per CONTEXT D-09 is the definitive precision check.

## Issues Encountered

None — all 6 task commits executed sequentially, all 3 deviations resolved inline, no checkpoints, no escalations.

## Threat Flags

None — Plan 07-05 ships 4 read-only JSON fixture files (data; no code paths, no network surface, no auth boundary, no schema changes at trust boundaries) plus 1 test-file edit (no production code changes). The fixtures live under `tests/fixtures/apr/` and are loaded by the existing `apr_fixture` fixture factory shipped in Plan 07-00 (no `conftest.py` modification). The new test functions consume the existing `solve_apr` and `_decimal_pow` surfaces from `lib/apr.py` (no new imports beyond what was already in the file). No new third-party dependencies. No schema changes at boundaries.

## Known Stubs

The following pre-existing inline stubs in `tests/test_apr.py` are NOT swapped to fixture-backed sibling tests in this wave (they continue to construct inputs inline):

- **`test_apr_solver_converges_within_decimal_00001_tolerance`** (Plan 07-02 Wave-2 inline) — still uses inline-constructed APRRequest. Wave 5 ships the SC-1 fixture but the new fixture-backed test `test_apr_reg_z_appendix_j_worked_example_returns_12_percent` (flipped this wave) is the more comprehensive APR-05/SC-1 anchor test; the Wave-2 inline test serves as a redundant SC-1 + SC-3 + D-10 dollar-residual sanity guard with slightly different assertion shape (it checks `final_residual <= Decimal('0.01')` which the new fixture-backed flip does not). Both PASS; the Wave-2 inline could be deleted as redundant in a future hygiene pass, but is not in scope for this plan.
- **`test_apr_response_uses_literal_estimated_apr_text`** (Plan 07-04 Wave-4 inline) — still uses inline-constructed APRRequest. The literal-text contract is enforced at the Pydantic boundary (D-05) on every solver response, so the inline-anchor variant pins the contract correctly; swapping to `apr_fixture(...)` is a hygiene-only refactor not in this plan's scope.
- **`test_apr_cli_subprocess_round_trip`** (Plan 07-04 Wave-4 inline) — still writes the inline-constructed JSON payload to `tmp_path/input.json`. Same reasoning: the CLI round-trip contract is exercised correctly with the inline payload; swapping is hygiene-only.

The Wave 4 SUMMARY explicitly anticipated these swaps; this plan's `must_haves` did NOT require them, so they were left for a follow-up hygiene pass. Their presence does not affect any acceptance gate or requirement closure.

No unintentional stubs introduced. No mock/placeholder data. No `FIXME` comments.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture, no human-in-the-loop verification. All 6 tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

- **Wave 6 (Plan 07-06 references doc)** — unblocked. `references/apr-reg-z.md` will be created with §1-6 (per CONTEXT.md "Specific Ideas" §3 mirror of `references/refi-npv.md` structure); §4 ("Worked example") will cite `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` as the canonical SC-1 anchor reference (the regulatory inputs + engine-output trace). APR-08 closes when `references/apr-reg-z.md` ships and `test_references_apr_reg_z_doc_present_with_required_sections` is flipped.
- **Wave 7 (Plan 07-07 HMDA Platform fixtures)** — unblocked. The 20+ HMDA Platform captures will exercise multi-fixture cross-validation against the engine; per CONTEXT.md D-09 ("HMDA delta policy — engine is wrong"), any divergence > `Decimal("0.00001")` will fail `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` (the historical name; per CONTEXT D-01 it now points at HMDA Platform fixtures with `oracle_commit_sha` provenance pinning). Wave 7 will also add a parallel parametric test for the HMDA fixtures per D-27 (separate test function, mirrors Phase 5 oracle vs hand-calc test split). The 15-day fixture's engine-emitted `0.065002` will be definitively cross-validated then.
- **Phase 8 (stress-points)** — `solve_apr` continues to be the integration point for stress wrappers. The Wave 5 fixtures + sibling tests are now part of the regression baseline; Phase 8 stress-test parameter sweeps will indirectly exercise these fixtures via `solve_apr` per grid cell.
- **Phase 10 (Claude skill)** — fixtures will move with the test suite if the Phase 10 relocation includes them; otherwise the existing `apr_fixture` factory + relative-path lookup in `tests/conftest.py` keeps them addressable from the same stems. No Phase 10 work required.
- **Requirement closure status:** Plan 07-05 closes **APR-05** (Reg Z Appendix J Example J-1 worked example fixture shipped + SC-1 anchor test flipped to PASS asserting engine within Decimal('0.00001') of regulatory `0.120000`). Remaining Phase 7 requirements: APR-04 in Wave 7 (HMDA Platform fixtures), APR-08 in Wave 6 (references doc).

## TDD Gate Compliance

The plan does not declare `type: tdd`; this is a vanilla `type: execute` plan. Per the executor protocol's TDD section, no RED/GREEN/REFACTOR cycle gate enforcement is required. For traceability, however: the 2 stub flips in Task 5 are RED → GREEN transitions of pre-existing Wave-0 xfail stubs. Each flip removes the `@pytest.mark.xfail(strict=True)` decorator (the RED gate marker per Wave-0's stub-then-flip pattern) and replaces the body with a real test that PASSES against the Wave 5 fixtures shipped in Tasks 1-4 (the GREEN gate). The 4 new tests in Task 6+7+sibling are not TDD-flow (they ship as PASSING tests against pre-existing engine code from Plans 07-02 + 07-03; not RED→GREEN). No REFACTOR pass needed.

## Self-Check: PASSED

Verified at execution end:

- [x] All 4 fixture files exist at the paths declared in plan frontmatter (`files_modified: tests/fixtures/apr/*.json`):
  - `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` — present (29 lines)
  - `tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json` — present (29 lines)
  - `tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json` — present (28 lines)
  - `tests/fixtures/apr/regz_appendix_j_unit_period_monthly_regular.json` — present (29 lines)
- [x] `tests/test_apr.py` modified — `wc -l` = 753 (was 633; +120 net of ruff format)
- [x] `git log --oneline | grep 25750a2` (Task 1 SC-1 anchor) → present
- [x] `git log --oneline | grep 9a4e746` (Task 2 15-day odd-period) → present
- [x] `git log --oneline | grep 0690903` (Task 3 45-day negative-path) → present
- [x] `git log --oneline | grep 27f35cf` (Task 4 Wikipedia regular sanity) → present
- [x] `git log --oneline | grep 3cce166` (Task 5 Wave-0 stub flips) → present
- [x] `git log --oneline | grep d3d3a14` (Tasks 6+7+sibling parametric + decimal_pow + 45-day sibling) → present
- [x] All six task commits reachable from `main`
- [x] No commit message contains "Co-Authored-By", "Claude", or any AI attribution (verified by inspection of all 6 messages — solely-authored as repo owner per global + project CLAUDE.md)
- [x] All plan acceptance gates PASS (see Acceptance Gate Verification table above)
- [x] `pytest tests/test_apr.py::test_apr_reg_z_appendix_j_worked_example_returns_12_percent -v` → PASS
- [x] `pytest tests/test_apr.py::test_newton_raphson_iterations_under_50_for_all_fixtures -v` → PASS
- [x] `pytest tests/test_apr.py::test_apr_hand_calc_fixtures_match_expected -v` → 2 PASS
- [x] `pytest tests/test_apr.py::test_decimal_pow_fractional_exponent_correctness -v` → PASS
- [x] `pytest tests/test_apr.py::test_odd_first_period_too_long_raises -v` → PASS
- [x] Full suite: 481 passed / 4 skipped / 3 xfailed / 0 failed / 0 errors (was 475+4+5; +6 net pass / -2 xfail; zero regression to Plan 07-04 baseline of 475)
- [x] `pytest tests/test_apr.py -v`: 16 passed / 2 xfailed (was 10/4 pre-Wave-5; +6 net pass / -2 xfail)
- [x] mypy --strict + ruff check + ruff format --check all clean on `tests/test_apr.py`
- [x] APR-05 closes per `requirements-completed` frontmatter (verified via the SC-1 anchor test flip end-to-end through the fixture surface; engine within Decimal('0.00001') of regulatory Decimal('0.120000'))
- [x] 11 of 13 Wave-0 stubs flipped (verified: only 2 xfail remain in `tests/test_apr.py` — `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` [APR-04 / Wave 7] and `test_references_apr_reg_z_doc_present_with_required_sections` [APR-08 / Wave 6])

---
*Phase: 07-estimated-apr*
*Completed: 2026-05-03*
