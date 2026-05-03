---
phase: 07-estimated-apr
plan: 00
subsystem: testing
tags:
  - phase-07
  - estimated-apr
  - test-infrastructure
  - nyquist
  - pytest
  - xfail-strict

# Dependency graph
requires:
  - phase: 05-arm-modeling
    provides: "tests/test_arm.py xfail-stub-then-flip pattern + tests/conftest.py arm_fixture loader template"
  - phase: 06-refinance-npv
    provides: "tests/test_refinance.py + refinance_fixture loader (immediately preceding sibling)"
provides:
  - "tests/test_apr.py — 13 xfail-strict stubs (8 requirement-mapped APR-01..08 + 5 cross-cutting)"
  - "apr_fixture pytest loader at tests/conftest.py (mirrors arm_fixture / refinance_fixture)"
  - "tests/fixtures/apr/ + tests/fixtures/apr/oracle/ committed empty placeholder dirs"
  - "Phase 7 Nyquist gate: every Phase 7 requirement (APR-01..08) has at least one named test"
affects:
  - 07-01-pydantic-models
  - 07-02-newton-raphson-engine
  - 07-03-odd-first-period-helpers
  - 07-04-cli
  - 07-05-fixtures-and-reg-z-anchor
  - 07-06-references-doc
  - 07-07-ffiec-fixtures

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "xfail(strict=True) Wave-0 stub → wave-N flip pattern (inherited from Phase 5 D-09; Phase 7 D-00-02)"
    - "Per-phase pytest fixture loader at tests/conftest.py (one-fixture-per-file JSON)"
    - "SCRIPT_PATH + APR_MODULE_PATH module-level constants for subprocess-only CLI tests (Phase 3 D-17)"

key-files:
  created:
    - tests/test_apr.py
    - tests/fixtures/apr/.gitkeep
    - tests/fixtures/apr/oracle/.gitkeep
  modified:
    - tests/conftest.py

key-decisions:
  - "D-00-01 (LOCKED): Test inventory pinned at 13 stubs (8 requirement + 5 cross-cutting). Mirrors Phase 5 D-09."
  - "D-00-02 (LOCKED): All 13 xfail decorators use strict=True so accidental pass raises XPASS."
  - "D-00-03 (LOCKED): apr_fixture loader is FIXTURE_DIR / 'apr' / f'{stem}.json' with no shape transform."

patterns-established:
  - "Phase 7 Nyquist gate via tests/test_apr.py: every requirement has a named, xfail-strict stub before any engine code lands"
  - "Loader naming convention extended: golden_fixture, amortize_fixture, affordability_fixture, arm_fixture, refinance_fixture, apr_fixture"
  - "Wave-0 imports trimmed to actually-used names (Path, TYPE_CHECKING, Any, Callable, pytest); future waves re-add json/re/subprocess/sys/Decimal as they flip stubs"

requirements-completed: []

# Metrics
duration: 3min 21s
completed: 2026-05-03
---

# Phase 7 Plan 0: Test Infrastructure Summary

**Phase 7 Nyquist gate shipped: 13 xfail-strict APR stubs + apr_fixture loader + empty fixtures dirs, with full suite preserved at 465 passed.**

## Performance

- **Duration:** 3 min 21 s
- **Started:** 2026-05-03T19:42:05Z
- **Completed:** 2026-05-03T19:45:26Z
- **Tasks:** 4 (Task 4 was the verification gate)
- **Files modified:** 1 (tests/conftest.py)
- **Files created:** 3 (tests/test_apr.py + 2 .gitkeep)

## Accomplishments

- Extended `tests/conftest.py` with `apr_fixture` pytest fixture (parallel to `arm_fixture` / `refinance_fixture`)
- Created `tests/test_apr.py` with all 13 Phase 7 xfail-strict stubs covering APR-01..08 + 5 cross-cutting contracts
- Committed empty `tests/fixtures/apr/` and `tests/fixtures/apr/oracle/` directories (Wave 5 + Wave 7 destinations)
- Suite count after: 465 passed, 4 skipped, 14 xfailed (13 new + 1 inherited Phase 5 ARM oracle); zero regression to Phase 5 / Phase 6 baseline

## Task Commits

Each task committed atomically against `main` (sequential executor; no branching per `parallelization=false`):

1. **Task 1: Extend tests/conftest.py with apr_fixture loader** — `5713247` (feat)
2. **Task 2: Create tests/fixtures/apr/.gitkeep + oracle/.gitkeep** — `a1f31fb` (chore)
3. **Task 3: Create tests/test_apr.py with 13 xfail stubs** — `0009ba3` (feat)
4. **Task 4: Verify zero regression + hygiene gates** — verification only; no code changes; rolled into Task 3 commit

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `tests/conftest.py` — appended `apr_fixture` (21 insertions; mirrors `refinance_fixture` shape; cites Phase 7 D-00-03)
- `tests/test_apr.py` — 182 lines; 13 xfail-strict stubs; module docstring lays out the wave-by-wave flip plan
- `tests/fixtures/apr/.gitkeep` — empty (Wave 5 lands `regz_appendix_j_5000_36_166_07.json` here)
- `tests/fixtures/apr/oracle/.gitkeep` — empty (Wave 7 lands HMDA Platform / FFIEC captures here)

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|------|--------|--------|
| `grep -c '@pytest.mark.xfail(' tests/test_apr.py` | 13 | 13 | PASS |
| `grep -c 'def test_' tests/test_apr.py` | 13 | 13 | PASS |
| `grep -c 'strict=True' tests/test_apr.py` | 13 | 13 | PASS (1 per decorator) |
| `pytest tests/test_apr.py -v` | 13 XFAIL, 0 ERROR, 0 FAIL | 13 xfailed | PASS |
| Full-suite passed count | ≥ 432 (plan) / ≥ 461 (executor floor) | 465 passed | PASS |
| `mypy --strict tests/conftest.py tests/test_apr.py` | clean | clean | PASS |
| `ruff check tests/conftest.py tests/test_apr.py` | clean | clean | PASS |
| `ruff format --check tests/conftest.py tests/test_apr.py` | clean | clean | PASS |

Note on the plan-spec acceptance gate `grep -c '@pytest.mark.xfail(strict=True'`: this returns 8 (not 13) because `ruff format` auto-broke 5 long-line decorators across multiple lines, putting `strict=True` on the line below `@pytest.mark.xfail(`. All 13 stubs have `strict=True` (verified via `grep -c 'strict=True' tests/test_apr.py` → 13 and the runtime XFAIL semantics — pytest treats each decorator as strict). See deviation #1 below.

## Decisions Made

None novel — followed locked decisions D-00-01, D-00-02, D-00-03 verbatim from plan frontmatter. The three (LOCKED) decisions were honored without interpretation:

- 13 stubs (no more, no fewer)
- All `strict=True`
- Loader path `FIXTURE_DIR / "apr" / f"{stem}.json"` (no shape transformation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Hygiene] Trimmed unused imports from tests/test_apr.py and accepted ruff-format multi-line decorator layout**

- **Found during:** Task 3 (immediately after writing the file verbatim from the plan spec)
- **Issue:** The plan-spec import block lists `json`, `re`, `subprocess`, `sys`, `decimal.Decimal` for downstream use in waves 2/4/5; ruff F401 flags them as unused at Wave 0 since none of the 13 `pytest.fail("Wave 0 stub")` bodies reference them. Separately, ruff-format auto-broke the 5 longest `@pytest.mark.xfail(...)` decorators across three lines (so `strict=True` lives on the line below `@pytest.mark.xfail(`), which makes the plan-spec acceptance grep `'@pytest.mark.xfail(strict=True'` return 8 rather than 13.
- **Fix:** Removed the 5 unused imports (Wave 2/4/5 can re-add them when flipping stubs; this is the standard incremental pattern). Accepted ruff-format's multi-line decorator layout — all 13 decorators still carry `strict=True` (verified via `grep -c 'strict=True'` → 13 and via 13 XFAIL outcomes at runtime, which require strict semantics to fail on accidental XPASS).
- **Files modified:** `tests/test_apr.py`
- **Verification:** `mypy --strict tests/conftest.py tests/test_apr.py` clean; `ruff check` clean; `ruff format --check` clean; `pytest tests/test_apr.py -v --tb=no` → 13 xfailed, 0 errors, 0 fails.
- **Committed in:** `0009ba3` (Task 3 commit; the imports were never committed to git in their unused form)
- **Plan deviation rule:** Rule-3 hygiene-only — formatting/lint fixes that do not change tests are explicitly permitted by the plan's "Deviation Rules" section (line 288-289 of `07-00-test-infrastructure-PLAN.md`).

---

**Total deviations:** 1 auto-fixed (Rule 3 hygiene)
**Impact on plan:** No semantic change. All 13 named stubs present; all carry `strict=True`; all collect as XFAIL at runtime; full suite zero-regression. The plan-spec acceptance grep wording is the only artifact that needs updating in subsequent wave plans (`'@pytest.mark.xfail(' && grep -c 'strict=True'` is the equivalent two-grep gate).

## Issues Encountered

None.

## Threat Flags

None — Phase 7 Plan 00 is a test-scaffold-only plan. No production code modified; no new network surface; no auth boundaries; no schema changes. The `<threat_model>` section is absent from the plan frontmatter, which is correct for a Wave-0 stubs plan.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture. All four tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

The 13 stubs are now load-bearing for Waves 1–7 of Phase 7. Each downstream wave plan must (a) reference the test names verbatim and (b) remove the `@pytest.mark.xfail(strict=True, ...)` decorator when flipping the stub to a real assertion (failure to remove → XPASS → suite breaks).

| Wave | Plan | Stubs flipped (count) | Stub names |
|------|------|--------------------:|-----------|
| 1 | 07-01-pydantic-models | 1 (partial) | test_apr_solver_module_exists_with_newton_raphson_signature |
| 2 | 07-02-newton-raphson-engine | 4 | test_apr_solver_module_exists_..., test_apr_solver_seeded_from_npf_rate, test_apr_solver_converges_..., test_apr_solver_raises_on_non_convergence |
| 3 | 07-03-odd-first-period-helpers | 0 | (rolled into Wave 5 fixture flips) |
| 4 | 07-04-cli | 5 | test_apr_response_uses_literal_estimated_apr_text, test_apr_cli_subprocess_round_trip, test_apr_cli_help_does_not_import_lib_apr, test_apr_cli_rejects_float_loan_amount, test_apr_cli_error_envelope_uniformity |
| 5 | 07-05-fixtures-and-reg-z-anchor | 2 | test_apr_reg_z_appendix_j_worked_example_returns_12_percent, test_newton_raphson_iterations_under_50_for_all_fixtures |
| 6 | 07-06-references-doc | 1 | test_references_apr_reg_z_doc_present_with_required_sections |
| 7 | 07-07-ffiec-fixtures (or HMDA Platform per CONTEXT D-01) | 1 | test_apr_ffiec_oracle_fixtures_match_within_decimal_00001 |

Total: 14 flips across 7 waves (Wave 2 flips one Wave-1 partial stub plus 3 net new). All 13 stubs end Phase 7 either flipped to PASS or documented as deferred (CONTEXT.md notes APR-04 as the partial-closure candidate if Wave 7 cannot capture).

## Next Phase Readiness

- Phase 7 Wave 1 (Plan 07-01 Pydantic models) is unblocked: imports `lib.apr` will produce `ImportError` until the wave ships, and the corresponding stub is xfail-strict so collection succeeds without false-positive failure.
- The renaming of "FFIEC" → "HMDA Platform" per CONTEXT D-01 (oracle pivot) does NOT affect this plan's artifacts — `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` keeps its FFIEC-named test ID for traceability with the original requirement APR-04 and the existing ROADMAP language; Wave 7's plan revision is responsible for the rename in fixture filenames + reason strings.
- No requirements are completed by this plan (per plan frontmatter `requirements: []`); REQUIREMENTS.md APR-01..08 stay Pending.

## Self-Check: PASSED

Verified at execution end:

- [x] `tests/test_apr.py` exists (`git log --oneline | grep 0009ba3` → present)
- [x] `tests/conftest.py` modified (`git log --oneline | grep 5713247` → present)
- [x] `tests/fixtures/apr/.gitkeep` exists (`git log --oneline | grep a1f31fb` → present)
- [x] `tests/fixtures/apr/oracle/.gitkeep` exists (same commit)
- [x] All three task commits (5713247, a1f31fb, 0009ba3) reachable from `main`
- [x] Full suite: 465 passed / 4 skipped / 14 xfailed / 0 failed / 0 errors
- [x] mypy --strict + ruff check + ruff format --check all clean on the two touched test files

---
*Phase: 07-estimated-apr*
*Completed: 2026-05-03*
