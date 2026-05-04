---
phase: 08-stress-points
plan: 02
subsystem: stress-points
tags:
  - phase-08
  - stress-points
  - stress-engine
  - rate-shock
  - income-shock
  - arm-reset
  - phase-3-composition
  - phase-4-composition
  - phase-5-composition

# Dependency graph
requires:
  - phase: 03-amortization
    provides: "lib.amortize.build_schedule (Phase 3 D-09 cleanup; exact-to-cent monthly_pi via lib.money.quantize_cents) — re-entered per rate cell in rate_shock"
  - phase: 04-affordability
    provides: "lib.affordability.evaluate dispatcher (Phase 4 D-11 blocker precedence + AffordabilityResponse.dti_back/blocked_by) — re-entered per reduction cell in income_shock"
  - phase: 05-arm-modeling
    provides: "lib.arm.build_arm_schedule + ARMRequest.index_path injection surface (lib/arm.py:104, ARM-01) — re-entered per path cell in arm_path; _compute_reset_triggers private helper promoted to public compute_reset_triggers via single rename + backward-compat alias (D-02-01 mirrors Phase 5 D-14 quantize_rate promotion)"
  - phase: 08-stress-points/08-01
    provides: "lib.stress type contract (RateShockRequest|IncomeShockRequest|ArmResetRequest discriminated union; StressResponse summary-before-rows field order; ScenarioSummary + StressRow + RatePath leaf models; evaluate() cross-plan stub raising NotImplementedError) — Plan 08-02 fills evaluate() body and adds three per-mode helpers"
provides:
  - "lib.stress.rate_shock(loan, rates, baseline_label) — per-cell loop over Phase 3 build_schedule with monthly_pi/total_interest capture + delta_vs_baseline_monthly + delta_vs_baseline_pct + RATE_SHOCK_MONOTONE_PI invariant check"
  - "lib.stress.income_shock(base_request, reductions, dti_threshold) — per-cell loop applying per-applicant gross_monthly_income reduction and re-running Phase 4 evaluate; returns dti_back/breaches_threshold/blocked_by"
  - "lib.stress._synthesize_index_path + lib.stress.arm_path — for each named RatePath, generate one IndexPathEntry per reset trigger and re-run Phase 5 build_arm_schedule; capture total_interest/max_payment/reset_count/highest_rate"
  - "lib.stress.evaluate(req) — isinstance-dispatch over the discriminated union; assembles StressResponse with summary-before-rows field order"
  - "lib.arm.compute_reset_triggers — promoted public name (was _compute_reset_triggers); backward-compat alias preserves Phase 5 internal callsites; D-02-01 mirrors Phase 5 D-14 quantize_rate promotion"
  - "5 Wave-0 xfails flipped at the engine layer: rate_shock + income_shock + arm_path canonical + arm_path 30yr horizon + monthly_pi monotone invariant; 6 xfails remain (4 CLI for Plan 08-04, 1 SC-5 size-budget fixture for Plan 08-05, 1 envelope-uniformity for Plan 08-04)"
affects:
  - 08-03-points-engine
  - 08-04-clis
  - 08-05-fixtures-and-tests
  - 08-06-references

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase 3/4/5 composition-not-reimplementation idiom (08-PATTERNS.md Pattern 1-4): each per-mode helper is a 5-15 line loop over an existing engine; no new mathematical primitive shipped in Phase 8"
    - "Pydantic v2 model_copy(update={...}) on frozen Loan/AffordabilityRequest/Household/Applicant/ARMRequest models for per-cell synthesis (D-02-02, D-02-03, D-02-04 all rely on this idiom; verified empirically against Phase 4 reverse-mode flow)"
    - "Worst-case-row total ordering via key function returning Decimal('0') for None — keeps max() over StressRow.monthly_pi/dti_back/total_interest total in the presence of mode-specific Optional fields"
    - "TYPE_CHECKING-guarded Sequence import (only used as type annotation at runtime) — avoids ruff TC003 while keeping the runtime import set minimal"
    - "Public-API promotion via single-line rename + backward-compat alias (D-02-01 mirrors Phase 5 D-14): compute_reset_triggers; _compute_reset_triggers = compute_reset_triggers"

key-files:
  created: []
  modified:
    - lib/stress.py
    - lib/arm.py
    - tests/test_stress.py

key-decisions:
  - "D-02-01 (LOCKED, honored): Promote lib.arm._compute_reset_triggers to public compute_reset_triggers via single-line rename + backward-compat alias `_compute_reset_triggers = compute_reset_triggers`. Mirrors Phase 5 D-14 quantize_rate promotion. Avoids Phase 8 importing a private name. All Phase 5 in-module callers preserved via the alias; the canonical caller in build_arm_schedule was updated to use the public name for hygiene."
  - "D-02-02 (LOCKED, honored): rate_shock uses loan.model_copy(update={'annual_rate': rate}) — Pydantic v2 frozen-model update idiom. Verified by Phase 4 reverse-mode flow."
  - "D-02-03 (LOCKED, honored): income_shock applies the reduction PER-APPLICANT (each applicant's gross_monthly_income is scaled). Phase 4 D-06 sum aggregation means proportional cuts produce a proportionally-cut total."
  - "D-02-04 (LOCKED, honored): arm_path._synthesize_index_path generates one IndexPathEntry per reset trigger — every trigger is covered (alignment-validator on ARMRequest enforces this; a misalignment would be a Plan-08-02 bug, not a runtime issue)."
  - "D-02-05 (LOCKED, honored): stress_invariant_violations is populated ONLY for the rate-shock monotone-pi check in v1. Income-shock dti monotone and arm-reset parallel-shift dominance invariants are NOTED in 08-RESEARCH §6.4 for Phase 11+ expansion; income-shock and arm-reset paths intentionally ship empty lists."
  - "D-02-06 (LOCKED, honored): model_copy on AffordabilityRequest preserves the discriminated-union runtime type (Pydantic v2 preserves the runtime type of the source object). Verified empirically by income_shock smoke test passing through the Phase 4 forward-mode pipeline."

patterns-established:
  - "Phase 8 Wave 2 stress-engine surface — three per-mode helpers (rate_shock / income_shock / arm_path) each a 5-15 line loop over the matching Phase 3/4/5 engine, plus _synthesize_index_path internal helper for the closed-set RatePath dispatch (parallel-shift / gradual-rise / fall-then-rise per D-01-05). Engine surface is purely additive on top of Plan 08-01's type contract; the cross-plan evaluate() stub becomes the dispatcher."
  - "Worst-case key-function pattern for mixed-Optional StressRow fields: `def _row_pi(r: StressRow) -> Money: assert r.monthly_pi is not None; return r.monthly_pi` for already-narrowed cases; `lambda r: r.dti_back if r.dti_back is not None else Decimal('0')` for cases that may legitimately produce None (income_shock when the reduction crosses a hard blocker)."
  - "Per-task incremental imports at the boundary module: only the imports the current task uses are added to lib/stress.py per task commit; subsequent tasks promote (Task 2: amortize.build_schedule + quantize_cents/quantize_rate + Decimal + TYPE_CHECKING Sequence; Task 3: affordability.evaluate as affordability_evaluate; Task 4: ARMTerms + IndexPathEntry + build_arm_schedule + compute_reset_triggers + ARMRequest moved out of TC001). Keeps each commit's diff isolated to the surface it actually adds; mirrors Phase 7 Plan 07-01 incremental-import idiom."
  - "Backward-compat alias preserves all in-module + downstream callers when promoting a private helper to public — single-line rename + `_old = new` after the def. Pattern reusable for any future private→public promotion (Phase 5 D-14 quantize_rate was the precedent; Plan 08-02 D-02-01 is the second occurrence)."

requirements-completed:
  - STRS-01
  - STRS-02
  - STRS-03

# Metrics
duration: ~10min
completed: 2026-05-04
---

# Phase 8 Plan 02: Stress Engine Summary

**Three per-mode stress-sweep helpers (rate_shock / income_shock / arm_path) plus an evaluate() dispatcher composed over Phase 3 build_schedule, Phase 4 affordability.evaluate, and Phase 5 build_arm_schedule, with one-line public-API promotion of compute_reset_triggers in lib/arm.py and 5 Wave-0 xfails flipped to in-process assertions.**

## Performance

- **Duration:** ~10 minutes
- **Started:** 2026-05-04T00:06:49Z
- **Completed:** 2026-05-04T00:16:22Z
- **Tasks:** 6 (all atomic, all committed; per-task incremental imports per Phase 7 idiom)
- **Files modified:** 3 (lib/stress.py +245/-15, lib/arm.py +9/-2, tests/test_stress.py +257/-43; 571 insertions / 62 deletions; final line counts 549/496/446)
- **Files created:** 0

## Accomplishments

- Promoted `lib.arm._compute_reset_triggers` → `lib.arm.compute_reset_triggers` (D-02-01) via single-line rename + backward-compat alias `_compute_reset_triggers = compute_reset_triggers`. Phase 5 baseline preserved verbatim: `tests/test_arm.py` 36 passed + 1 xfailed (the inherited Phase 5 ARM oracle Bankrate/Vertex42 deferral). Mirrors Phase 5 D-14 quantize_rate promotion exactly.
- Added `lib.stress.rate_shock(loan, rates, baseline_label)` — per-cell loop over `lib.amortize.build_schedule` with `monthly_pi` + `total_interest` capture, delta-vs-baseline computation in 2dp Money / 6dp Rate quanta, and the `RATE_SHOCK_MONOTONE_PI` invariant check (08-RESEARCH §6.4). Smoke: $400k/30yr at {0.06, 0.065, 0.07} returns [2398.20, 2528.27, 2661.21] — pinning the Phase 3 oracle (CONVENTIONS.md $400k @ 6.5%/30yr → 2528.27) end-to-end through the rate-shock path.
- Added `lib.stress.income_shock(base_request, reductions, dti_threshold)` — per-cell loop scaling each applicant's `gross_monthly_income` by `(1 - reduction)` (D-02-03 per-applicant scaling per Phase 4 D-06 sum aggregation) and re-running `lib.affordability.evaluate(shocked_request)`. Captures `dti_back` + `breaches_threshold` + `blocked_by` per row. Worst-case label = highest `dti_back` (None treated as 0 for total ordering).
- Added `lib.stress._synthesize_index_path(arm_terms, term_months, base_index, path)` for the three named paths (parallel-shift / gradual-rise / fall-then-rise per D-01-05 closed set per ROADMAP SC-3 verbatim) generating one `IndexPathEntry` per reset trigger; and `lib.stress.arm_path(base_arm_request, paths)` per-cell loop over `lib.arm.build_arm_schedule` capturing `total_interest`, `max_payment`, `reset_count`, `highest_rate` per row. For a 5/1 ARM 30yr base (initial=60, reset=12, term=360), every path produces `reset_count == 25` (one per trigger in [61, 73, ..., 349]).
- Wired `lib.stress.evaluate(req)` dispatcher to isinstance-narrow over `RateShockRequest|IncomeShockRequest|ArmResetRequest` and assemble `StressResponse` with the SC-5 summary-before-rows field order (D-01-02; the Pydantic field declaration order does the heavy lifting). Smoke: `evaluate(RateShockRequest(loan, rates=[0.06, 0.07]))` returns `scenario_count=2, summary.worst_case_label='0.07'` exactly per plan-spec acceptance smoke.
- Flipped 5 of 11 Wave-0 xfails in `tests/test_stress.py` with synthesized in-process assertions (no fixtures yet — Plan 08-05 ships the 14 fixtures): `test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent`, `test_income_shock_per_cell_calls_phase4_engine_with_threshold_breach`, `test_arm_path_three_canonical_paths_total_interest`, `test_arm_path_30yr_horizon_reset_count`, `test_sc5_stress_invariants_monthly_pi_monotone_in_rate`. Suite count: 509 passed + 4 skipped + 12 xfailed (was 504/4/17; +5 net pass exactly per the 5 stub flips, −5 xfailed exactly corresponding to the flipped stubs; 0 failed; 0 errored; Phase 5 baseline preserved at 36/1).

## Task Commits

Each task committed atomically against `main` (sequential executor; `parallelization=false`; `branching_strategy=none`; commits authored solely by repo owner per global + project CLAUDE.md):

1. **Task 1: Promote `_compute_reset_triggers` to public API in lib/arm.py** — `a6f4c2b` (refactor)
2. **Task 2: Implement lib.stress.rate_shock** — `97ea690` (feat)
3. **Task 3: Implement lib.stress.income_shock** — `3a8a482` (feat)
4. **Task 4: Implement lib.stress.arm_path + _synthesize_index_path** — `753b8c1` (feat)
5. **Task 5: Implement lib.stress.evaluate dispatcher** — `bbdabd8` (feat)
6. **Task 6: Flip 5 Wave 0 xfails (engine smoke tests)** — `0592216` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `lib/arm.py` — promoted `_compute_reset_triggers` to public `compute_reset_triggers` via single-line rename; added backward-compat alias `_compute_reset_triggers = compute_reset_triggers`; updated the in-module callsite in `build_arm_schedule` to use the public name for hygiene; +9/−2 lines net (496 lines total).
- `lib/stress.py` — added per-task imports for the helpers + 4 public + 1 private function bodies + dispatcher (Decimal, TYPE_CHECKING Sequence, build_schedule, ARMTerms/IndexPathEntry/build_arm_schedule/compute_reset_triggers, affordability_evaluate, quantize_cents/quantize_rate); +245/−15 lines net (549 lines total). Wave-1 type contract preserved verbatim — only the engine bodies replace the Wave-1 NotImplementedError stub at evaluate() and add five new top-level definitions (rate_shock, income_shock, _synthesize_index_path, arm_path) + augmented imports.
- `tests/test_stress.py` — 5 xfail decorators removed and bodies replaced with synthesized in-process assertions; 1 new helper `_build_5_1_arm_request_30yr()` factored across the two arm_path tests; +257/−43 lines net (446 lines total). 6 xfail decorators remaining (was 11; 5 flipped exactly per Plan 08-02 acceptance criterion `grep -c '@pytest.mark.xfail' tests/test_stress.py == 6`). Remaining xfails: 4 CLI stubs + 1 SC-5 size-budget + 1 envelope-uniformity (all to be flipped by Plans 08-04 and 08-05).

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|-------------|--------|--------|
| `grep -c 'def compute_reset_triggers' lib/arm.py` | 1 | 1 | PASS |
| `grep -c '_compute_reset_triggers = compute_reset_triggers' lib/arm.py` | 1 | 1 | PASS |
| `python -c "from lib.arm import compute_reset_triggers; print(compute_reset_triggers.__doc__[:50])"` | exit 0 | "Return the list of reset trigger periods for an ARM..." | PASS |
| `pytest tests/test_arm.py -q` | exit 0 | 36 passed + 1 xfailed (Phase 5 baseline preserved) | PASS |
| `grep -c 'def rate_shock' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'def income_shock' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'def arm_path' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'def _synthesize_index_path' lib/stress.py` | 1 | 1 | PASS |
| `grep -c '^def evaluate' lib/stress.py` | 1 (the real dispatcher) | 1 | PASS |
| `grep -c 'NotImplementedError' lib/stress.py` | 0 | 0 | PASS |
| `mypy --strict lib/stress.py lib/arm.py` | clean | Success: no issues found in 2 source files | PASS |
| `ruff check lib/stress.py lib/arm.py` | clean | All checks passed! | PASS |
| `ruff format --check lib/stress.py lib/arm.py` | clean | 2 files already formatted | PASS |
| `grep -c '@pytest.mark.xfail' tests/test_stress.py` | 6 (was 11; 5 flipped) | 6 | PASS |
| `pytest tests/test_stress.py -v --tb=short` | 7 passed, 6 xfailed | 7 passed, 6 xfailed | PASS |
| Full-suite passed count | ≥ 418 (plan target floor) / ≥ 502 (Phase 5 baseline) | 509 | PASS |
| Full-suite xfailed count | ≥ 11 (16 from Plan 08-01 minus 5 flipped) | 12 (the +1 above 11 is the inherited Phase 5 ARM oracle xfail, NOT Phase 8) | PASS |
| Full-suite failed count | 0 | 0 | PASS |
| Full-suite errored count | 0 | 0 | PASS |
| Smoke: rate_shock $400k/30yr at {0.06, 0.065, 0.07} | monotone monthly_pi values | [2398.20, 2528.27, 2661.21] (Phase 3 oracle pinned at 0.065) | PASS |
| Smoke: evaluate(RateShockRequest(rates=[0.06, 0.07])).summary.worst_case_label | "0.07" | "0.07" | PASS |
| Plan-spec acceptance smoke (`scenario_count, worst_case_label`) | "2 0.07" | "2 0.07" | PASS |

## SC-5 Field-Order Self-Verification (regression-checked across the new evaluate path)

Plan 08-01 already pinned `summary: ScenarioSummary` BEFORE `rows: list[StressRow]` at the model declaration; Plan 08-02's evaluate() dispatcher always assembles via `StressResponse(mode=..., scenario_count=..., summary=summary, rows=rows)` keyword args, so the Pydantic v2 declaration-order serialization holds end-to-end. The Plan 08-01 flipped test `test_sc5_summary_table_appears_before_rows_in_json` continues to pass post-Plan-08-02 (full suite 509/4/12; that test is in the 509-passed set, regression-free).

## Phase 5 Baseline Preservation

`pytest tests/test_arm.py -q` post-rename: 36 passed + 1 xfailed (the 1 xfailed is the inherited Phase 5 ARM oracle Bankrate/Vertex42 deferral pinned in Plan 05-06 SUMMARY's deferred-items contract — NOT a Plan-08-02 regression). The backward-compat alias `_compute_reset_triggers = compute_reset_triggers` ensures every Phase 5 in-module callsite resolves identically to the pre-rename binding; the only Phase 5 in-module caller (`build_arm_schedule`) was also updated to the public name for hygiene, but the alias would have made that update optional. No behavioral change at the rename surface — verified empirically.

## Decisions Made

None novel — followed locked decisions D-02-01..D-02-06 verbatim from plan frontmatter. The 6 (LOCKED) decisions were honored without interpretation:

- D-02-01: `_compute_reset_triggers` → `compute_reset_triggers` public via single rename + alias (mirrors Phase 5 D-14 quantize_rate promotion)
- D-02-02: `loan.model_copy(update={'annual_rate': rate})` for per-cell synthesis in rate_shock
- D-02-03: per-applicant `gross_monthly_income` scaling by `(1 - reduction)` in income_shock
- D-02-04: `_synthesize_index_path` covers ALL reset triggers per term (alignment-validator on ARMRequest catches misalignment as a Plan-08-02 bug not a runtime issue)
- D-02-05: stress_invariant_violations populated ONLY for rate-shock monotone-pi check in v1; income-shock + arm-reset paths ship empty lists intentionally
- D-02-06: `model_copy` on `AffordabilityRequest` preserves discriminated-union runtime type (Pydantic v2 preserves the runtime type of the source object)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan-spec helper sketch had subtle issues fixed inline against project's mypy --strict + ruff config**

- **Found during:** Tasks 2, 3, 4 (writing the helper bodies from the plan-spec sketch and observing the project's lint + type-check outputs)
- **Issue:** Three small adjustments to the plan-spec helper sketches were needed to land clean against the project's discipline:
  - **Per-task incremental imports** — the plan-spec listed all helpers' imports at once, which would have made Tasks 2 / 3 / 4 / 5 each fire ruff F401 unused-import errors against future-task imports. Adopted Phase 7 Plan 07-01's per-task incremental-import idiom: each task's commit imports only what its body uses, with `Sequence` placed in a `TYPE_CHECKING` guard since it's used only as a type annotation in the rate_shock signature (Task 2). Subsequent tasks promoted imports as bodies needed them: Task 3 added `affordability_evaluate`; Task 4 added `ARMTerms` / `IndexPathEntry` / `build_arm_schedule` / `compute_reset_triggers` and moved `ARMRequest` out of `noqa: TC001` because it's now also used at runtime as the arm_path arg type.
  - **PT018 compound-assert split** — `assert parallel_ti is not None and fall_rise_ti is not None` in `test_arm_path_three_canonical_paths_total_interest` (Task 6) tripped ruff PT018 ("assertion should be broken down into multiple parts"). Split into two single-condition asserts. Same hygiene class as Phase 4 04-04 deviation #2 split-compound-assert.
  - **Mypy narrowing for max() over StressRow with Optional fields** — `max(rows, key=lambda r: r.monthly_pi or Decimal("0"))` from the plan-spec sketch trips mypy --strict on Money|None ordering. Two patterns chosen depending on whether the field is provably non-None at the callsite: (a) for rate_shock's worst-case computation, the rows were just constructed with non-None `monthly_pi` so the key uses `assert r.monthly_pi is not None; return r.monthly_pi` to give mypy a narrow path; (b) for income_shock's `dti_back` (which can legitimately be None when the affordability call hits a hard blocker like USDA-income-limit before computing DTI), the key uses `r.dti_back if r.dti_back is not None else Decimal('0')` for total ordering; same pattern for arm_path's `total_interest`.
- **Fix:** Applied the three adjustments inline as each task hit them. Each adjustment preserves the plan-spec's substantive intent (Task 2-5 ship the four documented helpers with the documented behaviors; Task 6 ships the five flipped tests with the documented assertions).
- **Files modified:** `lib/stress.py` (Tasks 2-5; per-task incremental imports), `tests/test_stress.py` (Task 6; PT018 split).
- **Verification:** `mypy --strict lib/stress.py lib/arm.py` clean; `ruff check + format --check` clean; full suite 509/4/12 zero-regression to Plan 08-01 baseline of 504/4/17 (+5 net pass / −5 xfailed exactly per plan).
- **Committed in:** `97ea690` (Task 2 imports + rate_shock), `3a8a482` (Task 3 imports + income_shock), `753b8c1` (Task 4 imports + arm_path + _synthesize_index_path), `0592216` (Task 6 PT018 split).
- **Plan deviation rule:** Rule-1 / Rule-3 hygiene blend — lint and mypy strict-mode ergonomics that don't change the engines' substantive behavior; the helpers ship the exact contracts the plan specified.

**2. [Rule 1 - Bug] Plan-spec test used `loan_type='conventional'` for the rate-shock smoke; not in Loan.loan_type Literal**

- **Found during:** Task 6 (writing `test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent`)
- **Issue:** The plan spec's `<acceptance_criteria>` for Task 2 inlines `Loan(... loan_type='conventional')`. But `lib/models.py:45` defines `loan_type: Literal['fixed', 'arm', 'fha', 'va', 'usda', 'jumbo'] = 'fixed'` — `'conventional'` is NOT in the closed set (Phase 4's `target_loan_type` discriminated-union enum DOES include it, but `Loan.loan_type` does not — Phase 4 maps the coarse `target_loan_type` to the narrower `Loan.loan_type` Literal via `TARGET_LOAN_TYPE_CROSSWALK`). Constructing the Loan with `loan_type='conventional'` raises `ValidationError` at construction time. Plan 08-01 SUMMARY documented the same bug-class for `test_stress_request_discriminated_union_by_mode` (deviation #4 there).
- **Fix:** Changed `loan_type='conventional'` to `loan_type='fixed'` in both the rate_shock and the SC-5 monotone tests (the most natural choice for a 30-year fixed-rate scenario).
- **Files modified:** `tests/test_stress.py` (Task 6).
- **Verification:** Both flipped tests pass; full suite zero-regression.
- **Committed in:** `0592216`.
- **Plan deviation rule:** Rule-1 bug — the plan-spec values would have made the tests fail at the wrong layer (Loan construction, not the rate-shock / monotone behavior). Same root cause as Plan 08-01 deviation #4. Documented inline in the test docstrings so future planners don't reintroduce.

**3. [Rule 3 - Hygiene] Removed unused `noqa: TC001` on AffordabilityRequest after Task 3**

- **Found during:** Task 3 (after adding `from lib.affordability import evaluate as affordability_evaluate`, ruff RUF100 fired on the existing `noqa: TC001` on `AffordabilityRequest` because the module now imports it again at runtime via the helper signature `income_shock(base_request: AffordabilityRequest, ...)` under `from __future__ import annotations` — but ruff's TC001 detector now sees a runtime callsite and considers the noqa unused).
- **Fix:** Dropped the `noqa: TC001` directive from the `AffordabilityRequest` import. The Pydantic field annotation runtime-resolution semantics are preserved by the second import statement (`from lib.affordability import evaluate as affordability_evaluate`) which forces the module to load; `AffordabilityRequest` resolves the same way it did before.
- **Files modified:** `lib/stress.py` (Task 3).
- **Verification:** `ruff check + format --check lib/stress.py` clean; `mypy --strict lib/stress.py` clean; smoke import `from lib.stress import IncomeShockRequest, income_shock` succeeds.
- **Committed in:** `3a8a482`.
- **Plan deviation rule:** Rule-3 hygiene — formatting/lint fix that doesn't change behavior. Twentieth occurrence of ruff hygiene-class deviations in the project (running tally per recent plan SUMMARYs).

---

**Total deviations:** 3 auto-fixed (1 Rule-1 plan-spec helper-sketch issues that are mostly hygiene-class but fix-time falls under Rule-1; 1 Rule-1 plan-spec Loan.loan_type='conventional' bug carried over from Plan 08-01; 1 Rule-3 hygiene noqa removal after import-promotion)
**Impact on plan:** No semantic change. All 4 helpers + dispatcher ship with the exact contracts the plan specified; all 5 Wave-0 xfails flipped exactly as specified; both LOCKED-DECISION smoke tests (rate_shock $400k/30yr at 0.065 = 2528.27 Phase 3 oracle pin; arm_path 5/1 ARM 30yr produces reset_count==25 across all 3 paths) verified empirically. The only inline adjustments were incremental-import hygiene + Loan.loan_type='conventional'→'fixed' (same bug-class as Plan 08-01 deviation #4) + a single PT018 compound-assert split. The plan-spec acceptance grep `pytest tests/test_stress.py -v --tb=short` showed `7 passed, 6 xfailed` exactly per plan acceptance.

## Issues Encountered

None blocking. All 3 deviations resolved inline within the same task they were discovered. Pre-commit hooks (ruff legacy + ruff format + mypy + check yaml + block-user-layer) passed on every task commit.

## Threat Flags

None — Plan 08-02 is a pure-engine plan composing existing Phase 3/4/5 surfaces. No new network endpoints, no new auth/file-access surface, no schema changes. The plan frontmatter has no `<threat_model>` section, which is correct for a composition-only plan.

## Known Stubs

None ship in this plan. Plan 08-01's two cross-plan `evaluate()` stubs:

| Stub | File | Status |
|------|------|--------|
| `lib.stress.evaluate()` raised NotImplementedError | `lib/stress.py` | RESOLVED in this plan (Task 5) — body is now the isinstance-dispatch over the discriminated union |
| `lib.points.evaluate()` raised NotImplementedError | `lib/points.py` | Still pending — Plan 08-03 (Wave 3) ships the body |

## User Setup Required

None — no external service configuration, no environment variables, no manual capture. All six tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

- **Plan 08-04 (CLIs, Wave 4)** is unblocked at the engine surface: `scripts/stress_test.py` calls `lib.stress.evaluate(req)` after `TypeAdapter(StressRequest).validate_json(...)`; the engine layer is fully operational. The 4 CLI xfails + 1 envelope-uniformity xfail in `tests/test_stress.py` remain Wave 0 stubs awaiting Plan 08-04.
- **Plan 08-05 (fixtures + tests, Wave 5)** is unblocked at the engine surface: the 14 fixtures (5 rate-shock + 3 income-shock + 3 arm-path + 3 points) call into the same engine entrypoints these helpers ship. The SC-5 size-budget xfail (`test_sc5_stress_sweep_50_scenarios_under_100kb`) awaits the 50-rate `rate_shock_size_budget_50_rates.json` fixture.
- **Phase 5 reverse-coupling** is permanently closed: the public-API promotion of `compute_reset_triggers` is complete; the backward-compat alias preserves all internal Phase 5 callsites; the in-module call in `build_arm_schedule` was updated to the public name for hygiene. No further Phase 5 modification is required by Plan 08-04 / 08-05 / 08-06.
- **Phase 11 forward-coupling** is pre-pinned: `references/stress-tests.md` (Plan 08-06) will lift the SC-5 subagent-consumption-hint paragraph verbatim into `.claude/agents/stress-test-agent.md`. The model layer's summary-before-rows + size-budget contracts (D-01-02 + D-01-03) and the engine layer's `stress_invariant_violations` (D-01-06 + D-02-05) are stable.

## Next Phase Readiness

- **Plan 08-03 (points engine, Wave 3)** is unblocked: `lib.points.evaluate()` body lands next, replacing the Plan 08-01 NotImplementedError stub at `lib/points.py:138`. Plan 08-03 is independent of 08-02 (different Pydantic surface, different math layer); they could have shipped in parallel under a different branching strategy.
- **Plan 08-04..08-06** unchanged from Plan 08-01 SUMMARY's forward-coupling notes — all engine surfaces stable.
- REQUIREMENTS.md STRS-01..STRS-03 transitioned from Pending → Done at the math layer; STRS-04 (CLI) remains Pending pending Plan 08-04. PNTS-01..03 unchanged (Plan 08-03 will close PNTS-01 + PNTS-02 at the math layer).

## Self-Check: PASSED

Verified at execution end:

- [x] `lib/arm.py` modified (`git log --oneline | grep a6f4c2b` → present)
- [x] `lib/stress.py` modified across 4 task commits (`git log --oneline | grep -E '97ea690|3a8a482|753b8c1|bbdabd8'` → all four present)
- [x] `tests/test_stress.py` modified (`git log --oneline | grep 0592216` → present)
- [x] All six task commits (a6f4c2b, 97ea690, 3a8a482, 753b8c1, bbdabd8, 0592216) reachable from `main`
- [x] Phase 5 baseline preserved: `pytest tests/test_arm.py -q` returns 36 passed + 1 xfailed (the 1 xfailed is the inherited Phase 5 ARM oracle Bankrate/Vertex42 deferral, NOT Phase 8)
- [x] Full suite: 509 passed / 4 skipped / 12 xfailed / 0 failed / 0 errored (+5 / −5 vs Plan 08-01 baseline of 504/4/17)
- [x] mypy --strict clean on lib/stress.py + lib/arm.py
- [x] ruff check + ruff format --check clean on lib/stress.py + lib/arm.py
- [x] `compute_reset_triggers` is public + `_compute_reset_triggers = compute_reset_triggers` alias is present + Phase 5 in-module call updated to public name
- [x] No `NotImplementedError` remaining in `lib/stress.py`
- [x] 5 Wave-0 xfails flipped exactly per plan-spec acceptance (`grep -c '@pytest.mark.xfail' tests/test_stress.py == 6`); 6 remain (4 CLI for Plan 08-04; 1 SC-5 size-budget for Plan 08-05; 1 envelope-uniformity for Plan 08-04)

---
*Phase: 08-stress-points*
*Completed: 2026-05-04*
