---
phase: 08-stress-points
plan: 01
subsystem: stress-points
tags:
  - phase-08
  - stress-points
  - pydantic-models
  - discriminated-union
  - sc-5-field-order

# Dependency graph
requires:
  - phase: 04-affordability
    provides: "AffordabilityRequest discriminated-union pattern (lib/affordability.py:441-534) — verbatim model for Phase 8 StressRequest mode-discriminated union"
  - phase: 05-arm-modeling
    provides: "ARMRequest with index_path injection surface (lib/arm.py:104) — explicitly designed for the stress-test consumer; ArmResetRequest reuses ARMRequest as-is"
  - phase: 08-stress-points/08-00
    provides: "tests/test_stress.py 13 strict-xfail stubs (Wave 0 Nyquist gate) — this plan flips 2 of them"
provides:
  - "lib/stress.py — Pydantic v2 type contract for stress sweeps (RateShockRequest|IncomeShockRequest|ArmResetRequest discriminated by 'mode'; StressResponse with summary-before-rows field order pinning ROADMAP SC-5; ScenarioSummary + StressRow + RatePath leaf models; evaluate() cross-plan stub raising NotImplementedError)"
  - "lib/points.py — Pydantic v2 type contract for discount-points breakeven (PointsRequestFromSavings|PointsRequestFromLoans discriminated by 'mode'; PointsResponse carrying both simple_breakeven_months AND npv_breakeven_months side-by-side per ROADMAP SC-4; evaluate() cross-plan stub raising NotImplementedError)"
  - "ROADMAP SC-5 contract baked into the Pydantic model layer — StressResponse field declaration places summary BEFORE rows; Pydantic v2 preserves field order in model_dump_json"
  - "Phase 6 deferred-coupling marker — PointsRequest.discount_rate_annual REQUIRED with no default; additive non-breaking change when Phase 6 lands"
affects:
  - 08-02-stress-engine
  - 08-03-points-engine
  - 08-04-clis
  - 08-05-fixtures-and-tests

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 discriminated union via Annotated[A | B | C, Field(discriminator='mode')] — third use after Phase 4 AffordabilityRequest + Phase 7 internal union; now standard project idiom"
    - "Field-declaration-order as serialization-order contract — StressResponse pins summary-before-rows at the model layer (D-01-02), enforced by Pydantic v2's model_dump_json preserving declaration order"
    - "Cross-plan stub idiom — evaluate() raises NotImplementedError so Wave 2/3 plans fill body without re-importing the surface (Phase 4 D-08 lib.affordability Wave 1 -> Wave 2 pattern)"
    - "Runtime-required Pydantic-field imports flagged with `noqa: TC001` (Phase 7 D-19 inheritance) so ruff TCH lint doesn't push them into TYPE_CHECKING blocks"

key-files:
  created:
    - lib/stress.py
    - lib/points.py
  modified:
    - tests/test_stress.py
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
    - .planning/phases/08-stress-points/08-01-pydantic-models-SUMMARY.md

key-decisions:
  - "D-01-01 (LOCKED): StressRequest discriminated by 'mode' over 3 subclasses (RateShockRequest, IncomeShockRequest, ArmResetRequest) mirroring Phase 4 AffordabilityRequest pattern"
  - "D-01-02 (LOCKED): StressResponse field order is `summary: ScenarioSummary` BEFORE `rows: list[StressRow]` — ROADMAP SC-5 contract baked into the model declaration; NEVER reorder"
  - "D-01-03 (LOCKED): StressRow carries summary scalars only; no full Schedule.payments[] arrays (D-03 in stress.py docstring; SC-5 100KB size budget)"
  - "D-01-04 (LOCKED): PointsRequest.discount_rate_annual REQUIRED with no default; Phase 6 cross-phase coupling deferred via additive non-breaking change"
  - "D-01-05 (LOCKED): RatePath.name is closed-set Literal[parallel-shift, gradual-rise, fall-then-rise] per ROADMAP SC-3 verbatim"
  - "D-01-06 (LOCKED): ScenarioSummary.stress_invariant_violations is list[str], not a raise — engine appends citations; empty = happy path"
  - "D-01-07 (LOCKED): PointsResponse always reports BOTH simple_breakeven_months AND npv_breakeven_months side-by-side; diverge=True iff unequal AND both non-None"

patterns-established:
  - "Phase 8 model layer uses ConfigDict(strict=True, frozen=True, extra='forbid') uniformly across all 8 BaseModel subclasses (RatePath, StressRow, ScenarioSummary, _CommonStressFields, RateShockRequest, IncomeShockRequest, ArmResetRequest, StressResponse) and 3 in lib/points.py (PointsRequestFromSavings, PointsRequestFromLoans, PointsResponse) — 11 models total at the Phase 8 boundary"
  - "Phase 4 AffordabilityRequest discriminator-union pattern is now the standard project idiom for any 'pick-one-of-N-shapes-via-string-discriminator' surface; Phase 8 ships 2 more (StressRequest 3-way + PointsRequest 2-way)"
  - "Cross-plan stub for engine `evaluate()` functions: `def evaluate(req) -> Response: raise NotImplementedError(\"...lives in Plan 08-XX\")` — surface stable, body deferred to next wave"

requirements-completed: []

# Metrics
duration: ~5min
completed: 2026-05-03
---

# Phase 8 Plan 01: Pydantic Models Summary

**Phase 8 Wave 1 type-contract shipped: lib/stress.py + lib/points.py with discriminated-union request models, ROADMAP SC-5 summary-before-rows pinned at the model layer, ROADMAP SC-4 simple-vs-NPV-side-by-side response pinned at the model layer, and 2 of 18 Wave 0 xfails flipped to passing.**

## Performance

- **Duration:** ~5 minutes
- **Started:** 2026-05-03T23:48:28Z
- **Completed:** 2026-05-03T23:54Z (approx)
- **Tasks:** 3 (all atomic, all committed)
- **Files created:** 2 (lib/stress.py + lib/points.py)
- **Files modified:** 1 (tests/test_stress.py — 2 xfail decorators removed, real assertions added)

## Accomplishments

- Created `lib/stress.py` (257 lines) with the Phase 8 stress-test type contract:
  - 4 leaf models (`RatePath`, `StressRow`, `ScenarioSummary`, `_CommonStressFields`)
  - 3 request subclasses (`RateShockRequest`, `IncomeShockRequest`, `ArmResetRequest`) discriminated by `mode`
  - `StressRequest` Annotated discriminated union mirroring Phase 4 AffordabilityRequest
  - `StressResponse` with `summary: ScenarioSummary` declared BEFORE `rows: list[StressRow]` (ROADMAP SC-5 verbatim closure)
  - `evaluate(req: StressRequest) -> StressResponse` cross-plan stub raising `NotImplementedError("lib.stress.evaluate body lives in Plan 08-02")`
  - All 8 Pydantic models carry `ConfigDict(strict=True, frozen=True, extra='forbid')`
- Created `lib/points.py` (140 lines) with the Phase 8 points-breakeven type contract:
  - 2 request subclasses (`PointsRequestFromSavings`, `PointsRequestFromLoans`) discriminated by `mode`
  - `PointsRequest` Annotated discriminated union
  - `PointsResponse` carrying both `simple_breakeven_months` AND `npv_breakeven_months` side-by-side per ROADMAP SC-4 (D-04)
  - `discount_rate_annual: Rate` REQUIRED on every request — Phase 6 deferred-coupling per project fail-loud-on-implicit-default doctrine (D-02)
  - Both breakeven fields are `int | None` (D-03; None = never crosses zero within hold)
  - `evaluate(req: PointsRequest) -> PointsResponse` cross-plan stub raising `NotImplementedError("lib.points.evaluate body lives in Plan 08-03")`
- Flipped 2 of 18 Wave 0 xfails in `tests/test_stress.py`:
  - `test_stress_request_discriminated_union_by_mode` — validates `TypeAdapter(StressRequest).validate_json(...)` routes `mode='rate-shock'` to `RateShockRequest` and rejects `mode='bogus-mode'` with `ValidationError`
  - `test_sc5_summary_table_appears_before_rows_in_json` — asserts `model_dump_json` preserves field-declaration order so the `summary` key precedes the `rows` key in dict ordering
- Suite count after: **504 passed, 4 skipped, 17 xfailed** (was 502/4/19 at Plan 08-00 close; +2 net pass exactly per the 2 stub flips, -2 xfailed exactly corresponding to the flipped stubs)

## Task Commits

Each task committed atomically against `main` (sequential executor; `parallelization=false`; `branching_strategy=none`; commits authored solely by repo owner per global + project CLAUDE.md):

1. **Task 1: Create lib/stress.py** — `292de13` (feat)
2. **Task 2: Create lib/points.py** — `947e5c0` (feat)
3. **Task 3: Flip 2 Wave 0 xfails** — `4eebe55` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `lib/stress.py` — 257 lines; 8 Pydantic models + `StressRequest` Annotated discriminated union + `evaluate()` cross-plan stub; module docstring carries the 6 LOCKED DECISIONS verbatim from the plan frontmatter
- `lib/points.py` — 140 lines; 3 Pydantic models + `PointsRequest` Annotated discriminated union + `evaluate()` cross-plan stub; module docstring carries the 4 LOCKED DECISIONS verbatim from the plan frontmatter
- `tests/test_stress.py` — 2 xfail decorators removed and bodies replaced with real assertions; +49 / -11 lines net; 11 xfail decorators remaining (was 13)

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|------|--------|--------|
| `wc -l lib/stress.py` | >= 250 | 257 | PASS |
| `grep -c 'class RateShockRequest' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'class IncomeShockRequest' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'class ArmResetRequest' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'StressRequest = Annotated' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'discriminator="mode"' lib/stress.py` | 1 | 1 | PASS |
| `grep -c 'class StressResponse' lib/stress.py` | 1 | 1 | PASS |
| Field-order: `summary: ScenarioSummary` line < `rows: list[StressRow]` line | line 235 < line 236 | line 235 < line 236 | PASS |
| `python -c "from lib.stress import StressRequest, StressResponse, RateShockRequest, IncomeShockRequest, ArmResetRequest, RatePath, StressRow, ScenarioSummary, evaluate; print('OK')"` | exit 0 | OK | PASS |
| `mypy --strict lib/stress.py` | clean | Success: no issues | PASS |
| `ruff check + format --check lib/stress.py` | clean | All checks passed; 1 file already formatted | PASS |
| `wc -l lib/points.py` | >= 120 | 140 | PASS |
| `grep -c 'class PointsRequestFromSavings' lib/points.py` | 1 | 1 | PASS |
| `grep -c 'class PointsRequestFromLoans' lib/points.py` | 1 | 1 | PASS |
| `grep -c 'PointsRequest = Annotated' lib/points.py` | 1 | 1 | PASS |
| `grep -c 'discriminator="mode"' lib/points.py` | 1 | 1 | PASS |
| `grep -c 'class PointsResponse' lib/points.py` | 1 | 1 | PASS |
| `python -c "from lib.points import PointsRequest, PointsResponse, PointsRequestFromSavings, PointsRequestFromLoans, evaluate; print('OK')"` | exit 0 | OK | PASS |
| `mypy --strict lib/points.py` | clean | Success: no issues | PASS |
| `ruff check + format --check lib/points.py` | clean | All checks passed; 1 file already formatted | PASS |
| `grep -c '@pytest.mark.xfail' tests/test_stress.py` | 11 (was 13; 2 flipped) | 11 | PASS |
| `pytest tests/test_stress.py::test_stress_request_discriminated_union_by_mode -v` | exit 0 (passes) | PASSED | PASS |
| `pytest tests/test_stress.py::test_sc5_summary_table_appears_before_rows_in_json -v` | exit 0 (passes) | PASSED | PASS |
| Full-suite passed count | >= 413 | 504 | PASS (well above target) |
| Full-suite xfailed count | >= 16 | 17 | PASS |
| Full-suite failed count | 0 | 0 | PASS |
| Full-suite errored count | 0 | 0 | PASS |

## SC-5 Field-Order Self-Verification

The plan frontmatter pins the SC-5 field-order contract: in `StressResponse`, `summary` MUST be declared BEFORE `rows`. Verified twice:

```
$ grep -n "summary: ScenarioSummary\|rows: list\[StressRow\]" lib/stress.py
19:  StressResponse declares ``summary: ScenarioSummary`` BEFORE
20:  ``rows: list[StressRow]``. Pydantic v2 preserves field-declaration order in
235:    summary: ScenarioSummary  # D-02: BEFORE rows
236:    rows: list[StressRow]
```

Line 235 (`summary`) precedes line 236 (`rows`) — D-01-02 locked decision honored. Runtime test `test_sc5_summary_table_appears_before_rows_in_json` confirms `model_dump_json` produces the same ordering at the JSON-key level.

## Decisions Made

None novel — followed locked decisions D-01-01..D-01-07 verbatim from plan frontmatter. The 7 (LOCKED) decisions were honored without interpretation:

- 3 stress request subclasses unioned via `mode` discriminator (D-01-01)
- StressResponse field declaration order: summary before rows (D-01-02)
- StressRow carries summary scalars only; no full Schedule.payments[] (D-01-03)
- PointsRequest.discount_rate_annual REQUIRED with no default (D-01-04)
- RatePath.name closed-set Literal (D-01-05)
- ScenarioSummary.stress_invariant_violations list[str] (D-01-06)
- PointsResponse always reports both breakevens side-by-side (D-01-07)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Hygiene] Removed unnecessary `# type: ignore[empty-body]` on evaluate() stub**

- **Found during:** Task 1 (mypy --strict failed with `error: Unused "type: ignore" comment [unused-ignore]`)
- **Issue:** The plan-spec body for `lib/stress.py` includes `def evaluate(req: StressRequest) -> StressResponse:  # type: ignore[empty-body]` and `lib/points.py` includes the same. mypy's `warn_unused_ignores = true` (set in pyproject.toml line 53) reports the ignore as unused because the function body raises `NotImplementedError("...")` rather than being empty — mypy never flags raise-only function bodies as `empty-body`. The ignore comment is dead.
- **Fix:** Removed the `# type: ignore[empty-body]` suffix from both `evaluate()` signatures. Function bodies remain `raise NotImplementedError("...")` per the cross-plan stub idiom.
- **Files modified:** `lib/stress.py` (Task 1) — `lib/points.py` was written with the fix already applied (Task 2 saw Task 1's failure).
- **Verification:** `mypy --strict lib/stress.py lib/points.py` -> clean.
- **Committed in:** `292de13` (lib/stress.py) — the ignore-stripped form was the first committed shape.
- **Plan deviation rule:** Rule-3 hygiene-only — formatting/lint fixes that do not change behavior. No plan-spec promise was broken; `evaluate()` still stubs `NotImplementedError` for Plan 08-02/08-03 to fill.

**2. [Rule 3 - Hygiene] Replaced `×` (MULTIPLICATION SIGN) with `x` in module docstring (RUF002)**

- **Found during:** Task 1 ruff check.
- **Issue:** The plan-spec D-03 docstring contains `50-rate sweep × 360 rows × 200 bytes per row would be 3.6MB, blowing the 100KB SC-5 budget by 36×`. Ruff RUF002 flags `×` (U+00D7) and similar non-ASCII look-alikes in docstrings as ambiguous. The project's ruff config selects RUF rules.
- **Fix:** Replaced three instances of `×` with plain ASCII `x` in the D-03 LOCKED-DECISION docstring of `lib/stress.py`.
- **Files modified:** `lib/stress.py` only.
- **Verification:** `ruff check lib/stress.py` -> All checks passed.
- **Committed in:** `292de13` — first committed shape.
- **Plan deviation rule:** Rule-3 hygiene-only.

**3. [Rule 3 - Hygiene] Added `noqa: TC001` to runtime-required Pydantic-field imports**

- **Found during:** Task 1 ruff check (TC001 errors on `lib.affordability.AffordabilityRequest`, `lib.arm.ARMRequest`, `lib.models.Loan/Money/Rate`).
- **Issue:** Ruff's TCH (typing-imports) lint pushed the type-only imports into a `TYPE_CHECKING:` block. But these are NOT type-only imports — Pydantic v2 resolves field annotations at runtime when constructing the model class, so the symbols must be importable at module-import time. Phase 7's `lib/apr.py:163` uses the exact same `noqa: TC001  # Pydantic resolves field annotations at runtime` comment for `Loan, Money` imports.
- **Fix:** Added `noqa: TC001` to all three `from lib.* import ...` lines in `lib/stress.py` and `lib/points.py`. Then `ruff check --fix` re-organized the multi-line imports with the noqa preserved on the parent `from ... import (` line. Cleared.
- **Files modified:** `lib/stress.py`, `lib/points.py` (both, on first write per Task 1/2 fix iteration).
- **Verification:** `ruff check lib/stress.py lib/points.py` -> All checks passed; `python -c "from lib.stress import *; print('OK')"` -> OK (runtime importable confirmed).
- **Committed in:** `292de13` (stress.py first), `947e5c0` (points.py).
- **Plan deviation rule:** Rule-3 hygiene-only — followed the established Phase 7 pattern verbatim.

**4. [Rule 1 - Bug] Plan-spec test used `loan_type="conventional"` which is not in the Loan Literal**

- **Found during:** Task 3 (running the flipped test the first time).
- **Issue:** The plan spec (line 365) for `test_stress_request_discriminated_union_by_mode` constructs `Loan(... loan_type="conventional")`. But `lib/models.py:45` defines `loan_type: Literal["fixed", "arm", "fha", "va", "usda", "jumbo"] = "fixed"` — `"conventional"` is NOT in the closed set. This is a planner over-extrapolation (Phase 4's `target_loan_type` enum DOES include `"conventional"`, but `Loan.loan_type` does not). Constructing the Loan with `loan_type="conventional"` raises `ValidationError` at construction time, before the StressRequest discriminator is even exercised.
- **Fix:** Changed `loan_type="conventional"` to `loan_type="fixed"` (the most natural choice for a 30-year fixed-rate scenario). Added an inline comment explaining the Literal mismatch so future maintainers don't reintroduce the planner's value.
- **Files modified:** `tests/test_stress.py`.
- **Verification:** Test passes; full suite zero regression.
- **Committed in:** `4eebe55` — first committed shape of the flipped test.
- **Plan deviation rule:** Rule-1 bug — the plan-spec value would have made the test fail at the wrong layer (Loan construction, not StressRequest discrimination). The fix preserves the substantive intent of the test.

**5. [Rule 1 - Bug] Plan-spec test used `validate_python(...)` but strict-mode rejects string -> Decimal in Python path**

- **Found during:** Task 3 (running the flipped test the first time).
- **Issue:** The plan-spec body for `test_stress_request_discriminated_union_by_mode` calls `adapter.validate_python({...})` after `loan.model_dump(mode="json")` — but `model_dump(mode="json")` returns Decimals as STRINGS (`"400000.00"`) and Dates as STRINGS (`"2026-01-01"`). Pydantic v2 strict-mode (which all Phase 1+ models use via `ConfigDict(strict=True, ...)`) REJECTS string -> Decimal coercion in the Python validation path; only the JSON validation path (`validate_json(...)`) accepts strings as Decimal/Date inputs. The plan-spec test failed with 4 ValidationErrors at the leaf Loan fields.
- **Fix:** Switched to `adapter.validate_json(json.dumps(payload))` per the established Phase 4 idiom (`tests/test_affordability.py:_request_from_fixture` lines 89-96 explicitly document this exact constraint). Result: validate_json -> strict-mode-Decimal-coercion path -> happy path passes; bogus-mode rejected with ValidationError as expected.
- **Files modified:** `tests/test_stress.py`.
- **Verification:** Both flipped tests pass; full suite 504 passed.
- **Committed in:** `4eebe55` — the JSON-path final shape.
- **Plan deviation rule:** Rule-1 bug — the plan-spec test would never pass with the project's strict-mode Pydantic discipline. The fix follows the established Phase 4 idiom verbatim and is documented in the test's docstring so future planners don't repeat the mistake.

---

**Total deviations:** 5 auto-fixed (3 Rule-3 hygiene + 2 Rule-1 bug; no Rule-2 or Rule-4 cases triggered)
**Impact on plan:** No semantic change. All 8 + 3 = 11 Pydantic models present with the exact field shapes specified in the plan. SC-5 field-order pinned. SC-4 simple-vs-NPV-side-by-side response model pinned. Phase 6 deferred-coupling marker present. The plan-spec test bodies for Task 3 had two mistakes (Loan.loan_type="conventional" + validate_python with json-dumped strict-mode Decimals); both were caught and fixed inline against the actual project's models, and the fixed shapes are documented in the test docstrings so the planner's mistakes don't propagate to Plan 08-02 / 08-04 / 08-05 fixture authors.

## Issues Encountered

None blocking. All 5 deviations resolved inline within the same task they were discovered.

## Threat Flags

None — Phase 8 Plan 01 is a model-layer-only plan. No new network surface, no auth boundaries, no schema persistence (DuckDB lands Phase 9), no file I/O. The plan frontmatter has no `<threat_model>` block, which is correct for a type-contract-only plan.

## Known Stubs

Plan 08-01 ships TWO intentional stubs by design (cross-plan stub idiom per Phase 4 D-08):

| Stub | File | Line | Reason | Resolved by |
|------|------|------|--------|-------------|
| `lib.stress.evaluate()` raises NotImplementedError | `lib/stress.py` | line 256 | Wave 1 ships type contract only; Plan 08-02 ships engine body | Plan 08-02 (08-02-stress-engine) |
| `lib.points.evaluate()` raises NotImplementedError | `lib/points.py` | line 138 | Wave 1 ships type contract only; Plan 08-03 ships engine body | Plan 08-03 (08-03-points-engine) |

Both stubs are SURFACED-AS-STUB per the plan's `must_haves.truths`: "Public engine functions exist as cross-plan stubs (lib.stress.evaluate, lib.points.evaluate) raising NotImplementedError — Plans 08-02 and 08-03 fill bodies". This is the documented intent, not a regression. The xfail-strict stubs in `tests/test_stress.py` and `tests/test_points.py` for the engine-layer behaviors (e.g., `test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent`) remain xfail-decorated until Plan 08-02 / 08-03 flip them.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture. All three tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

- Plan 08-02 (stress-engine, Wave 2) imports from `lib.stress`: `RateShockRequest, IncomeShockRequest, ArmResetRequest, StressRequest, StressResponse, StressRow, ScenarioSummary, RatePath` — all surfaces stable. The `evaluate()` body replaces the `raise NotImplementedError` line; the type signature is unchanged.
- Plan 08-03 (points-engine, Wave 3) imports from `lib.points`: `PointsRequestFromSavings, PointsRequestFromLoans, PointsRequest, PointsResponse` — all surfaces stable. The `evaluate()` body replaces the `raise NotImplementedError` line; the type signature is unchanged.
- Plan 08-04 (CLIs, Wave 4) imports from both `lib.stress` (StressRequest + evaluate) and `lib.points` (PointsRequest + evaluate). Surface is stable.
- Plan 08-05 (fixtures + tests, Wave 5) consumes `StressResponse.model_dump_json()` for the SC-5 size-budget assertion; the summary-before-rows ordering is already pinned in this plan's flipped test.
- Plan 08-06 (references, Wave 6) cites `references/points-breakeven.md` "Phase 6 deferred coupling" — D-01-04 in this plan establishes the pattern; Plan 08-06 lifts it into the reference doc.

The 11 remaining xfail-strict stubs in `tests/test_stress.py` (4 engine + 4 CLI + 3 SC-5) are now load-bearing for Plans 08-02, 08-04, 08-05.

## Next Phase Readiness

- Phase 8 Wave 2 (Plan 08-02 stress engine) is unblocked: `from lib.stress import ...` resolves; the `evaluate()` stub is the single line Plan 08-02 replaces.
- Phase 8 Wave 3 (Plan 08-03 points engine) is unblocked: `from lib.points import ...` resolves; the `evaluate()` stub is the single line Plan 08-03 replaces.
- Phase 5 ARM `index_path` injection surface (lib/arm.py:104) confirmed as the integration point for Plan 08-02's `arm_path` engine — this plan's `ArmResetRequest.base_arm_request: ARMRequest` reuses Phase 5's ARMRequest as-is, no Phase 5 modification.
- Phase 4 AffordabilityRequest reused as-is by `IncomeShockRequest.base_request: AffordabilityRequest` — no Phase 4 modification.
- Phase 6 discount-rate convention deferred-coupling pinned at the model layer via `PointsRequest.discount_rate_annual` REQUIRED with no default. When Phase 6 lands, a single-line additive non-breaking change in `lib/points.py` adds the default; no Phase 8 plan needs to be re-executed.
- No requirements are completed by this plan (per plan frontmatter `requirements: []`); REQUIREMENTS.md STRS-01..04 + PNTS-01..03 stay Pending.

## Self-Check: PASSED

Verified at execution end:

- [x] `lib/stress.py` exists (`git log --oneline | grep 292de13` -> present)
- [x] `lib/points.py` exists (`git log --oneline | grep 947e5c0` -> present)
- [x] `tests/test_stress.py` modified (`git log --oneline | grep 4eebe55` -> present)
- [x] All three task commits (292de13, 947e5c0, 4eebe55) reachable from `main`
- [x] Full suite: 504 passed / 4 skipped / 17 xfailed / 0 failed / 0 errors (+2 / -2 vs Plan 08-00 baseline of 502/4/19)
- [x] mypy --strict clean on lib/stress.py + lib/points.py
- [x] ruff check + ruff format --check clean on lib/stress.py + lib/points.py
- [x] SC-5 field-order verified at the source level: line 235 `summary: ScenarioSummary` < line 236 `rows: list[StressRow]`
- [x] SC-5 field-order verified at runtime: `test_sc5_summary_table_appears_before_rows_in_json` PASSED via `model_dump_json` -> `json.loads` -> `keys.index("summary") < keys.index("rows")`

---
*Phase: 08-stress-points*
*Completed: 2026-05-03*
