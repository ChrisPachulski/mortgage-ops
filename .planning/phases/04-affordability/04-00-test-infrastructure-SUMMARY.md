---
phase: 04-affordability
plan: 00
subsystem: testing

tags: [phase-4, affordability, test-infrastructure, wave-0, pytest, xfail, fixture-loader]

requires:
  - phase: 01-foundation
    provides: tests/conftest.py FIXTURE_DIR + golden_fixture loader pattern; tests/fixtures/ tree convention
  - phase: 03-core-amortization
    provides: tests/conftest.py amortize_fixture sibling-loader pattern (mirror); tests/test_amortize.py SCRIPT_PATH constant idiom (mirror)

provides:
  - tests/conftest.py extended with affordability_fixture pytest fixture (mirror of amortize_fixture)
  - tests/fixtures/affordability/ directory committed via .gitkeep sentinel (Wave 3 fixture-population scaffold)
  - tests/test_affordability.py skeleton with 9 xfail stubs (one per AFFD-01..09 requirement)
  - AFFORDABILITY_MODULE_PATH + SCRIPT_PATH constants pin Phase 10 relocation seam
  - Nyquist-compliant per-task verify gate enabled for Plans 04-01..04-06 (each Wave 1+ task can express `pytest tests/test_affordability.py::test_AFFD_NN_xxx -x`)

affects: [04-01-pydantic-models, 04-02-forward-affordability, 04-03-reverse-affordability, 04-04-blocker-precedence, 04-05-cli-and-config, 04-06-tests-and-fixtures]

tech-stack:
  added: []  # Wave 0 scaffold only; no new runtime deps. pytest already configured Phase 1.
  patterns:
    - "Wave-0 xfail-stub seeding: each requirement gets a `@pytest.mark.xfail(strict=False, reason='Wave N: AFFD-XX implementation pending (Plan 04-NN)')` stub with `raise NotImplementedError(...)` body so pytest collects the function but xfail catches the not-implemented signal at execution time. Reusable for any future phase that wants per-requirement test surface in place BEFORE production code lands."
    - "Sibling-loader convention extended: each new phase appends a `{phase}_fixture` factory to tests/conftest.py mirroring the established amortize_fixture shape (filename-stem loader from `FIXTURE_DIR / phase / f'{stem}.json'`). Fixture-shape consistency across phases enables a future RUL-13-style citation-coverage meta-test if Phase 4+ ships one."

key-files:
  created:
    - tests/test_affordability.py
    - tests/fixtures/affordability/.gitkeep
  modified:
    - tests/conftest.py

key-decisions:
  - "Wave 0 xfail-stub raises NotImplementedError inside the function body (not at import time) so xfail catches it at test-execution time, not collection time. Without this, `from lib.affordability import ...` at module top would break collection because lib.affordability does not exist yet."
  - "Stub xfail reason strings encode the wave + target plan (e.g., 'Wave 1: AFFD-01 implementation pending (Plan 04-02)') for grep audit per threat-model T-04-00-02 — a silently-dropped stub in Wave 1+ is detectable by `grep -c 'Wave .: AFFD' tests/test_affordability.py` dropping by exactly 1 per RED→GREEN flip."
  - "Removed plan-specified speculative imports (json, subprocess, sys, decimal.Decimal, typing.Any, collections.abc.Callable) that Wave 0 stubs do not yet use; ruff F401 flagged them. Wave 1+ plans (04-02..04-06) will add each import back when their implementation needs it. Mirrors 02-07/03-04 pattern: don't carry speculative imports."

patterns-established:
  - "Wave-0 stub seeding pattern: collect-only-at-Wave-0 + RED→GREEN flip-per-requirement at Wave 1+ — Plans 04-02..04-06 each replace one or more stub bodies with real assertions; the xfail flips to xpass and the planner removes the @pytest.mark.xfail decorator in the same commit."
  - "SCRIPT_PATH single-constant Phase-10 relocation seam: tests/test_affordability.py's `SCRIPT_PATH = .../scripts/affordability.py` is the ONLY constant edited at Phase 10 when scripts/ relocates to .claude/skills/mortgage-ops/scripts/. Phase 4 callers MUST use subprocess invocation (NEVER `import scripts.affordability`) so the relocation stays a one-line change. Mirrors Phase 3 D-17 + tests/test_amortize.py:50-53 idiom."

requirements-completed: []  # Wave 0 scaffold only; no AFFD-XX requirement is closed by this plan. AFFD-01..09 close at Wave 1-3 (Plans 04-02..04-06).

duration: 3min
completed: 2026-04-30
---

# Phase 4 Plan 00: Test Infrastructure Summary

**Wave 0 test scaffold for AFFD-01..09: tests/conftest.py extended with affordability_fixture loader; tests/fixtures/affordability/ committed; tests/test_affordability.py skeleton with 9 xfail stubs enables Nyquist-compliant per-task verify gates for Plans 04-01..04-06.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-30T18:54:34Z
- **Completed:** 2026-04-30T18:58:15Z
- **Tasks:** 3
- **Files modified/created:** 3 (1 modified, 2 created)

## Accomplishments

- `tests/conftest.py` extended with `affordability_fixture` factory that mirrors Phase 3's `amortize_fixture` (D-17 fixture loader pattern; one-fixture-per-file under `tests/fixtures/affordability/`; loader takes a filename stem)
- `tests/fixtures/affordability/` committed as a directory via `.gitkeep` 0-byte sentinel (Wave 3 / Plan 04-06 populates with the 9+ fixture JSONs)
- `tests/test_affordability.py` skeleton: 9 xfail stubs (one per AFFD-01..09), `AFFORDABILITY_MODULE_PATH` + `SCRIPT_PATH` constants, structured xfail reason strings for grep audit
- 301 prior tests still green; 9 new tests xfail by design — full suite stays green per VALIDATION.md Wave-0 requirement
- Nyquist-compliant per-task verify gate enabled: every Wave 1+ task in Plans 04-01..04-06 can express `<verify><automated>pytest tests/test_affordability.py::test_AFFD_NN_xxx -x</automated></verify>` against a real test stub

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend tests/conftest.py with affordability_fixture factory** — `d55b989` (feat)
2. **Task 2: Create tests/fixtures/affordability/ with .gitkeep** — `81df1a0` (chore)
3. **Task 3: Create tests/test_affordability.py skeleton with AFFD-01..09 stubs** — `28504cf` (test)

_Plan metadata commit (this SUMMARY + state updates) follows after self-check._

## Files Created/Modified

- `tests/conftest.py` (MODIFY) — appended `affordability_fixture` factory after the existing `amortize_fixture`; preserves Phase 1 + Phase 3 ordering; FIXTURE_DIR shared with prior loaders
- `tests/fixtures/affordability/.gitkeep` (CREATE) — 0-byte sentinel committing the empty fixtures directory so the loader does not raise FileNotFoundError on the parent path before Wave 3 fixtures land
- `tests/test_affordability.py` (CREATE, 92 lines) — module docstring + AFFORDABILITY_MODULE_PATH + SCRIPT_PATH constants + 9 xfail stubs (AFFD-01..09) raising `NotImplementedError("Wave 0 stub — implementation comes in Plan 04-NN")` inside each function body

## Decisions Made

- **Stub function bodies raise `NotImplementedError`, not bare `pass`** — xfail with `pass` would xpass on every collection (function returns successfully), incorrectly flagging the stub as "passing" before any implementation lands. Raising `NotImplementedError` ensures xfail catches the stub at test-execution time and surfaces a structured reason on the next plan's RED→GREEN flip. Selected over alternative `pytest.skip(...)` because xfail integrates with the suite-stays-green discipline (xfailed != skipped in pytest summary).
- **Drop plan-specified speculative imports (json, subprocess, sys, decimal.Decimal, typing.Any, collections.abc.Callable)** — ruff F401 flagged all 6 as unused at Wave 0 (stub bodies don't use them). Removing now keeps tests/test_affordability.py mypy-strict + ruff clean; Wave 1+ plans (04-02..04-06) will add each import back when their implementation needs it. Mirrors 02-07 + 03-04 "no speculative noqa, no speculative imports" convention.
- **Accept ruff format auto-collapse of SCRIPT_PATH** — pre-commit ruff format auto-collapsed `SCRIPT_PATH: Path = (\n    Path(__file__)...\n)` to a single line because the assignment fits at 100 chars after the right-hand side concatenation. Substance is preserved (the constant points at the same path); only the line shape differs from the plan's verbatim quote. Mirrors 03-01 + 03-02 ruff-format-auto-wrap deviation pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed plan-specified speculative imports**

- **Found during:** Task 3 (tests/test_affordability.py creation)
- **Issue:** Plan task body specified imports `json`, `subprocess`, `sys`, `decimal.Decimal`, `typing.Any`, `collections.abc.Callable` to mirror tests/test_amortize.py:26-42 verbatim. ruff F401 flagged all 6 as unused because Wave 0 stub bodies (each `raise NotImplementedError(...)`) do not reference any of them — the imports were authored for the Wave 1+ test bodies that do not yet exist.
- **Fix:** Trimmed the import block to `from __future__ import annotations`, `from pathlib import Path`, `import pytest` — the only imports the Wave 0 module uses (Path for the two MODULE_PATH constants, pytest for the @pytest.mark.xfail decorator). Wave 1+ plans (04-02..04-06) will add `json` / `subprocess` / `sys` / `Decimal` / `Any` / `Callable` back as each test body needs them.
- **Files modified:** tests/test_affordability.py
- **Verification:** `uv run ruff check tests/test_affordability.py` → All checks passed!; `uv run mypy --strict tests/test_affordability.py` → Success: no issues found in 1 source file
- **Committed in:** 28504cf (Task 3 commit)

**2. [Rule 3 - Blocking] Accepted ruff format auto-collapse of SCRIPT_PATH multi-line assignment**

- **Found during:** Task 3 (pre-commit hook ran ruff format)
- **Issue:** Plan Task 3 action body specified `SCRIPT_PATH: Path = (\n    Path(__file__).resolve().parent.parent / "scripts" / "affordability.py"\n)` as a 3-line wrapped assignment. ruff format auto-collapsed it to `SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "affordability.py"` because the line fits at 100 chars (ruff line-length). The plan acceptance criterion `grep -c "SCRIPT_PATH: Path = (" tests/test_affordability.py` therefore returns 0 instead of >=1 against the literal substring.
- **Fix:** Accepted the ruff format output. Substance preserved (constant points at the same path; constant is exported with the same type annotation; the docstring referencing Phase 10 relocation seam is intact directly below). The acceptance criterion was a line-shape proxy for "constant exists and is wired correctly" — both still true when verified via the more general grep `grep -E "SCRIPT_PATH: Path = " tests/test_affordability.py` which returns 1.
- **Files modified:** tests/test_affordability.py (auto-formatted by pre-commit hook)
- **Verification:** `grep "SCRIPT_PATH" tests/test_affordability.py` shows the constant present with correct path; `uv run pytest tests/test_affordability.py --collect-only -q | grep -c '::test_AFFD_0'` → 9 (collection unaffected); `AFFORDABILITY_MODULE_PATH: Path = (` multi-line form preserved (it doesn't fit on one line at 100 chars).
- **Committed in:** 28504cf (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - Blocking, both ruff hygiene)
**Impact on plan:** Both deviations are formatting-class only (no semantic change); the plan's intent (Wave 0 scaffold collects 9 stubs, fixture loader registered, fixtures dir committed) is fully achieved. Mirrors the established 03-01..03-06 ruff-auto-wrap deviation pattern. No scope creep.

## Issues Encountered

None — plan executed smoothly. Wave 0 scaffold pattern is now established for any future phase that wants pre-populated test stubs before production code lands.

## Known Stubs

The following 9 xfail stubs are intentional Wave 0 placeholders, NOT scope-shrink stubs. Each is protected by `@pytest.mark.xfail(strict=False, reason="Wave N: AFFD-XX implementation pending (Plan 04-NN)")` so pytest collects but does not fail the suite:

| Stub | File | Line | Wave | Target Plan |
|------|------|------|------|-------------|
| test_AFFD_01_dti_calculations | tests/test_affordability.py | 38 | 1 | 04-02 |
| test_AFFD_02_ltv_calculation | tests/test_affordability.py | 48 | 1 | 04-02 |
| test_AFFD_03_cltv_with_junior_liens | tests/test_affordability.py | 54 | 1 | 04-02 |
| test_AFFD_04_piti_composition | tests/test_affordability.py | 60 | 1 | 04-02 |
| test_AFFD_05_reverse_round_trip | tests/test_affordability.py | 66 | 1 | 04-03 |
| test_AFFD_06_joint_applicants | tests/test_affordability.py | 72 | 1 | 04-02 |
| test_AFFD_07_blocked_by_va_residual_west_family_4 | tests/test_affordability.py | 78 | 1 | 04-04 |
| test_AFFD_08_cli_smoke | tests/test_affordability.py | 84 | 2 | 04-05 |
| test_AFFD_09_household_example_yml_e2e | tests/test_affordability.py | 90 | 3 | 04-06 |

**Resolution path:** Each stub flips RED→GREEN at its target plan; the @pytest.mark.xfail decorator is removed in the same commit as the body replacement. Stub-presence count `grep -c 'Wave .: AFFD' tests/test_affordability.py` should drop by exactly 1 per Wave-N task per threat-model T-04-00-02 grep audit.

## User Setup Required

None — Wave 0 scaffold is purely internal test infrastructure; no external service configuration, no .env additions, no manual user steps.

## Next Phase Readiness

- **Plans 04-01..04-06 unblocked.** Each can express `<verify><automated>pytest tests/test_affordability.py::test_AFFD_NN_xxx -x</automated></verify>` against a real test stub. Per VALIDATION.md, the Nyquist-compliant per-task feedback gate (max latency 20s) is now achievable for every Wave 1+ task.
- **Wave 1 (Plans 04-01..04-04) is the natural next batch:** AFFD-01..04 + AFFD-06 + AFFD-07 stubs are RED-flippable as soon as `lib/affordability.py` lands (Plan 04-01 ships the Pydantic request/response models; Plan 04-02 ships the forward DTI/LTV/CLTV/PITI body). AFFD-05 follows in Plan 04-03 (reverse `npf.pv` solver).
- **No blockers.** Full suite green (301 passed + 9 xfailed); mypy --strict clean across the 2 modified test files; ruff clean; deviation-set is 2 Rule-3 hygiene only.

---
*Phase: 04-affordability*
*Completed: 2026-04-30*

## Self-Check: PASSED

- tests/conftest.py — FOUND
- tests/fixtures/affordability/.gitkeep — FOUND
- tests/test_affordability.py — FOUND
- .planning/phases/04-affordability/04-00-test-infrastructure-SUMMARY.md — FOUND
- Commit d55b989 (Task 1) — FOUND
- Commit 81df1a0 (Task 2) — FOUND
- Commit 28504cf (Task 3) — FOUND
