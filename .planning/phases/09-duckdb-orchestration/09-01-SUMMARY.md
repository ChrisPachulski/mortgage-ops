---
phase: 09-duckdb-orchestration
plan: 01
subsystem: orchestration

tags:
  - phase-09
  - duckdb-orchestration
  - lockfile
  - concurrency
  - cross-process-mutex
  - node-esm
  - pers-04
  - pers-05

# Dependency graph
requires:
  - phase: 09-duckdb-orchestration
    plan: 00
    provides: "tests/test_orchestration/ package + 9 xfail stubs + node_orchestration_run helper"
provides:
  - "orchestration/lockfile.mjs (95 lines) — cross-process mutex via data/.lock with 5 exports: acquireLock, releaseLock, withLock, isStale, readLock"
  - "STALE_THRESHOLD_MS = 60_000 constant exported (PERS-04 + ROADMAP SC-3 contract)"
  - "tests/test_orchestration/test_lockfile_unit.py (221 lines) — 7 unit tests covering acquire/release/stale/race/throw/timeout/null-handling"
  - "Locked precedent for orchestration/ Node ESM modules (path resolution via dirname(dirname(fileURLToPath(import.meta.url))))"
affects:
  - "09-02 init-db (Wave 2) — uses the orchestration/ directory; package.json adds type:module"
  - "09-03 db-write (Wave 3) — imports { withLock } from './lockfile.mjs' to wrap insert-loan/insert-scenario/insert-report transactions"
  - "09-04 render-markdown (Wave 4) — imports { withLock } to wrap render+rewrite of data/loans.md"
  - "09-06 concurrency (Wave 6) — flips test_concurrent_writes_serialize + test_stale_lockfile_reclaimed_after_60s; both exercise this lockfile via db-write.mjs"

# Tech tracking
tech-stack:
  added: []  # No new runtime libraries; uses Node built-ins (fs, path, url) only
  patterns:
    - "Cross-process mutex via JSON-content lockfile with read-back-and-verify (poor-man's compare-and-swap) — direct port of career-ops/scripts/lockfile.mjs"
    - "Stale-lock recovery via acquired_at JSON content (NOT mtime) — deliberately immune to filesystem touch + clock-skew between fs-clock and process-clock"
    - "withLock(fn, opts) wrapper with try/finally — guarantees release even on throw"
    - "releaseLock pid + acquired_at match check — process A cannot delete process B's lock"
    - "Inline `node --input-type=module` ESM scripts in pytest subprocess.run for primitive-layer testing without a .mjs test harness"

key-files:
  created:
    - "orchestration/lockfile.mjs — 95 lines; verbatim port of career-ops/scripts/lockfile.mjs with three renames (CAREER_OPS -> MORTGAGE_OPS in const decl, .career-ops.lock -> .lock filename, header comment block citing mortgage-ops + Phase 9)"
    - "tests/test_orchestration/test_lockfile_unit.py — 221 lines; 7 unit tests with auto-cleanup fixture"
  modified: []  # Wave 1 is purely additive

key-decisions:
  - "D-01-01 LOCKED: writeFileSync(flag:'w') + read-back-and-verify, NOT flag:'wx' (O_EXCL) — career-ops chose flag:'w' deliberately because acquireLock OVERWRITES stale locks; flag:'wx' would crash on every acquire while a stale lock sits on disk"
  - "D-01-02 LOCKED: stale check is acquired_at-based (JSON content), NOT mtime-based — JSON timestamp is set deterministically by writer in same wall-clock domain, immune to `touch` and fs/process clock skew"
  - "D-01-03 LOCKED: lock filename is data/.lock (NOT data/.mortgage-ops.duckdb.lock) — spawn-message constraint + DATA_CONTRACT.md cross-reference; brevity matches mortgage-ops convention vs career-ops's more-specific .career-ops.lock"
  - "D-01-04 LOCKED: lockfile path resolution via dirname(dirname(fileURLToPath(import.meta.url))) — orchestration/ is one dirname up from repo root; identical pattern to be reused by Wave 2 init-db.mjs and Wave 3 db-write.mjs"
  - "D-01-05 LOCKED: STALE_THRESHOLD_MS = 60_000 is non-negotiable (ROADMAP SC-3 contract; PERS-04 binding)"

patterns-established:
  - "orchestration/ Node ESM module path resolution pattern (verbatim career-ops port — Waves 2-4 reuse)"
  - "Inline `node --input-type=module` ESM in pytest subprocess.run — pattern for primitive-layer Node tests that don't need a full DB harness"
  - "Auto-cleanup pytest fixture for filesystem state (data/.lock cleanup before AND after each test)"

requirements-completed: []  # PERS-04 and PERS-05 closure require Wave 6 integration tests; Wave 1 ships the primitive only

# Metrics
duration: 3min
completed: 2026-05-07
---

# Phase 09 Plan 01: Lockfile Summary

**Cross-process mutex primitive shipped: orchestration/lockfile.mjs (95 lines, 5 exports) + 7-test unit suite — every Phase 9 write subcommand can now `import { withLock } from './lockfile.mjs'` to serialize DuckDB writes via data/.lock with 60s stale-lock recovery.**

## Performance

- **Duration:** ~3 min (start 16:41:17Z, end 16:44:00Z; 161s wall-clock; 2 commits)
- **Tasks:** 3 (Task 3 was verification-only — no commit, mirroring Wave 0 precedent)
- **Files created:** 2 (orchestration/lockfile.mjs, tests/test_orchestration/test_lockfile_unit.py)
- **Files modified:** 0

## Accomplishments

- **orchestration/lockfile.mjs (95 lines)** ports career-ops/scripts/lockfile.mjs verbatim with the three planned renames (D-01-01..D-01-05 honored)
- **5 exports** all present and functional: `acquireLock`, `releaseLock`, `withLock`, `isStale`, `readLock`
- **7 unit tests pass** (acquire-release / 60s-threshold / null-defense / stale-reclaim / race-protection / throw-finally / timeout)
- **Phase 5+ baseline preserved + improved**: 521 passed + 4 skipped + 10 xfailed → **528 passed + 4 skipped + 10 xfailed** (+7 net passes from new unit tests; xfail count unchanged because Wave 0's `test_stale_lockfile_reclaimed_after_60s` stays strict-xfail until Wave 6 flips it)
- **mypy --strict + ruff check + ruff format --check all clean** across the new test file and the orchestration directory
- **No leftover data/.lock** after suite completion (auto-cleanup fixture verified)

## Test Counts

- **Pre-Wave-1 baseline (Plan 09-00 final):** 521 passed + 4 skipped + 10 xfailed
- **Post-Wave-1 (Plan 09-01 final):** **528 passed + 4 skipped + 10 xfailed** (+7 passes, 0 xfail delta, 0 regression)
- **Plan acceptance floor:** ≥439 passed (the plan's "432 prior + 7 new = 439" arithmetic was based on a pre-Phase-8 baseline; actual Phase 5+ baseline at Plan 09-00 final was 521, so 528 vastly exceeds the floor)

## Wave-Flip Status

This plan ships PRODUCTION CODE; it does not flip any Wave-0 xfail stub. The single PERS-04 stub (`test_stale_lockfile_reclaimed_after_60s` in `tests/test_orchestration/test_lockfile.py`) stays strict-xfail until **Wave 6 (Plan 09-06)** ships the integration test that pre-creates a stale lock and invokes `db-write.mjs insert-loan` to verify reclaim. Wave 1's contribution to PERS-04/PERS-05 is the primitive that Wave 6 will exercise end-to-end.

## Task Commits

Each task was committed atomically (no Co-Authored-By or AI attribution per global Git Attribution rule):

1. **Task 1: feat(09-01): port orchestration/lockfile.mjs from career-ops** — `337f006`
2. **Task 2: test(09-01): add 7 unit tests for orchestration/lockfile.mjs** — `ed3fe52`
3. **Task 3: Verify zero regression + lint hygiene** — verification-only, no commit (Wave 0 precedent)

## Files Created

- `orchestration/lockfile.mjs` — 95 lines. Three renames from career-ops/scripts/lockfile.mjs:
  - `const CAREER_OPS = ...` → `const MORTGAGE_OPS = ...`
  - `'.career-ops.lock'` filename → `.lock` (per DATA_CONTRACT + spawn-message)
  - Header comment block updated to cite mortgage-ops + Phase 9 PERS-04/PERS-05 + plan locked-decisions D-01-01 + D-01-02
  - Two minor defensive enhancements over career-ops verbatim (still within Rule-2 port scope, also explicitly in the plan's prescribed file content):
    - `isStale` adds `typeof lock.acquired_at !== 'number'` guard (career-ops only checks falsy lock); makes the function defensible against malformed JSON content
    - `readLock` is exported (career-ops keeps it module-private); needed because the unit tests inspect lock state, and the integration test in Wave 6 will likely also inspect

- `tests/test_orchestration/test_lockfile_unit.py` — 221 lines. 7 unit tests with auto-cleanup fixture. All tests use inline `node --input-type=module` ESM scripts via `subprocess.run` with `cwd=REPO_ROOT`. Test runtime ~0.7s for the full file (each spawns a Node subprocess but they're short-lived).

## Decisions Made

All five decisions are LOCKED at the plan level (D-01-01..D-01-05) — the executor honored them verbatim. No new plan-level decisions emerged during execution.

- **D-01-01 LOCKED — writeFileSync(flag:'w') + read-back, NOT flag:'wx':** career-ops/scripts/lockfile.mjs:42 uses flag:'w' deliberately because the acquireLock loop OVERWRITES stale locks (`if (!existing || isStale(existing))`); flag:'wx' would EEXIST-crash on every acquire while a stale lock sits on disk.
- **D-01-02 LOCKED — stale check is acquired_at-based (JSON content), NOT mtime-based:** mtime is vulnerable to filesystem `touch` and clock-skew; JSON timestamp is set deterministically by the writer in the same wall-clock domain that reads it back.
- **D-01-03 LOCKED — lock filename is `.lock` (NOT `.mortgage-ops.duckdb.lock`):** per spawn-message constraint #1 + DATA_CONTRACT.md cross-reference. RESEARCH.md §Recommended Project Structure suggests the longer name but spawn-message + DATA_CONTRACT win (deviation_rules Rule-1 documented this conflict).
- **D-01-04 LOCKED — lockfile path resolution via `dirname(dirname(fileURLToPath(import.meta.url)))`:** Wave 2 init-db.mjs and Wave 3 db-write.mjs will reuse this exact pattern.
- **D-01-05 LOCKED — STALE_THRESHOLD_MS = 60_000 is non-negotiable:** ROADMAP SC-3 + REQUIREMENTS PERS-04 binding contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule-3 Hygiene] Ruff TC003 — `collections.abc.Iterator` moved into TYPE_CHECKING block**
- **Found during:** Task 2 (initial ruff check after writing test file)
- **Issue:** Ruff TC003 fired on `from collections.abc import Iterator` because `Iterator` is only used as a return-type annotation (`-> Iterator[None]`) on the `_cleanup_lock` fixture. With `from __future__ import annotations`, annotations are strings at runtime, so `Iterator` is never imported at runtime.
- **Fix:** Moved `from collections.abc import Iterator` into an `if TYPE_CHECKING:` block; added `from typing import TYPE_CHECKING` import. (Same pattern Wave 0 SUMMARY documented for `pathlib.Path` in test_lockfile.py + test_render_markdown.py.)
- **Plan acknowledgement:** Plan deviation_rules section explicitly authorizes Rule-3 hygiene-only deviations: "If `node --check` surfaces a stylistic warning ... the executor may apply the minimal fix and document it in SUMMARY.md as a Rule-3 deviation. Likewise for ruff format auto-fixes on the Python test file."
- **Files modified:** tests/test_orchestration/test_lockfile_unit.py (only — orchestration/lockfile.mjs was untouched by this fix)
- **Verification:** `uv run ruff check tests/test_orchestration/` → All checks passed; mypy --strict still clean; all 7 tests still pass.
- **Committed in:** `ed3fe52` (Task 2 commit, applied during lint-fix sub-loop before commit)

**2. [Rule-3 Hygiene] Plan verify-block grep counts include comment-mentions; semantics correct**
- **Found during:** Task 1 acceptance-criteria verification
- **Issue:** The plan's verify-block specifies `grep -c "CAREER_OPS" orchestration/lockfile.mjs` MUST return 0 and `grep -c "flag.*'wx'" orchestration/lockfile.mjs` MUST return 0. However, the plan's prescribed file content (which I wrote verbatim per Rule-2) includes these tokens in the **header comment block** explaining the port history and Critical Issue 1 rationale: "Ported verbatim from career-ops/scripts/lockfile.mjs ... with three renames: CAREER_OPS -> MORTGAGE_OPS" and "flag:'wx' (O_EXCL) is INTENTIONALLY NOT USED". A naïve `grep -c` therefore returns 1 + 1 (not 0 + 0) and `flag.*'w'` returns 2 (not 1).
- **Resolution:** Verified via more precise grep that the **code semantics** are correct: zero `const CAREER_OPS` declarations or non-comment usages of CAREER_OPS; zero actual `writeFileSync` calls with `flag:'wx'`; exactly one `writeFileSync` call with `flag:'w'`. The plan's verify-block is grep-naïve about its own prescribed comment text — this is a plan-internal arithmetic glitch, not an implementation defect.
- **Code-level acceptance criteria (semantic, not lexical):**
  - Zero `const CAREER_OPS` declarations: ✓ (only `const MORTGAGE_OPS` exists)
  - Zero non-comment `CAREER_OPS` usages: ✓ (`grep -nv "^//" orchestration/lockfile.mjs | grep CAREER_OPS` exit 1)
  - Exactly one `writeFileSync` call: ✓ (line 60)
  - That one call uses `flag:'w'`, not `'wx'`: ✓
  - All 5 exports present: ✓
  - 95 lines (≥70 minimum): ✓
- **Files modified:** None (the plan's prescribed file content is preserved verbatim — Rule-2 port-verbatim discipline takes priority over Rule-3 cosmetic comment-stripping)
- **Plan acknowledgement:** Rule-2 of plan deviation_rules: "port verbatim, do not refactor ... Even if a reading uncovers what looks like a bug or improvement opportunity, DO NOT refactor — port verbatim." The plan-prescribed content is the canonical content; the plan's grep-based acceptance check is what's drifted.
- **Committed in:** `337f006` (Task 1 commit, file content shipped exactly as plan specified)

---

**Total deviations:** 2 auto-fixed (both Rule-3 hygiene-only; both explicitly anticipated by plan deviation_rules).
**Impact on plan:** Zero functional change. The lockfile primitive is byte-for-byte the prescribed content; the test file matches the prescribed content modulo the TYPE_CHECKING import shuffle. No Rule-1 or Rule-2 deviations occurred.

## Issues Encountered

None — execution was clean. Both Rule-3 hygiene deviations were anticipated by the plan's deviation_rules section.

## Lint + Type Hygiene Status

| Check | Result |
|-------|--------|
| `uv run pytest -q` | **528 passed + 4 skipped + 10 xfailed** (was 521+4+10; +7 net passes; zero regression) |
| `uv run pytest tests/test_orchestration/test_lockfile_unit.py -v` | **7 passed in 0.69s** |
| `node --check orchestration/lockfile.mjs` | syntax OK |
| `uv run mypy --strict tests/test_orchestration/test_lockfile_unit.py` | Success: no issues found in 1 source file |
| `uv run ruff check tests/test_orchestration/` | All checks passed! |
| `uv run ruff format --check tests/test_orchestration/` | 6 files already formatted |
| `test ! -f data/.lock` | exit 0 (no leftover lockfile after suite completes) |

## User Setup Required

None — Wave 1 is additive code + tests; no environment variables, dashboard configuration, or credential setup needed. Wave 2 will add `package.json` with `"type": "module"` (the .mjs extension is currently sufficient for Node to treat the file as ESM regardless of package.json type). Wave 3+ will install `duckdb-async` + `js-yaml` (not needed by the lockfile primitive).

## Self-Check: PASSED

Verified at SUMMARY-write time:
- `orchestration/lockfile.mjs` exists at 95 lines (`wc -l` confirms)
- `node --check orchestration/lockfile.mjs` exits 0
- All 5 exports present (acquireLock, releaseLock, withLock, isStale, readLock — verified via grep)
- `tests/test_orchestration/test_lockfile_unit.py` exists at 221 lines with 7 `def test_` functions
- All 7 required test names verified present
- Commit `337f006` (Task 1: feat(09-01) port lockfile.mjs) found via `git log --oneline`
- Commit `ed3fe52` (Task 2: test(09-01) 7 unit tests) found via `git log --oneline`
- Full pytest suite reports 528 passed + 4 skipped + 10 xfailed (verified)
- mypy --strict + ruff check + ruff format --check all clean (verified)
- No leftover `data/.lock` on disk (verified `test ! -f data/.lock` exits 0)

## Next Phase Readiness

**Wave 2 (Plan 09-02 init-db.mjs) unblocked** — orchestration/ directory exists; init-db.mjs can use the same path-resolution idiom (`dirname(dirname(fileURLToPath(import.meta.url)))`); init-db.mjs does NOT import lockfile (one-shot script, not a write loop).

**Wave 3 (Plan 09-03 db-write.mjs subcommands) unblocked** — `import { withLock } from './lockfile.mjs'` is now valid; insert-loan / insert-scenario / insert-report / drain-queue / update-status / render-markdown subcommands wrap their DuckDB transactions in `withLock(async () => { ... })`.

**Wave 4 (Plan 09-04 render-markdown) unblocked** — render of `data/loans.md` from DuckDB will be wrapped in `withLock` to serialize against concurrent writers.

**Wave 6 (Plan 09-06 concurrency tests) unblocked** — has the lockfile primitive to exercise via end-to-end db-write.mjs invocations:
- `test_concurrent_writes_serialize` will spawn N parallel `db-write.mjs insert-loan` calls and assert serialization
- `test_stale_lockfile_reclaimed_after_60s` will pre-create a stale lock with `acquired_at = Date.now() - 65000` and verify reclaim

**Wave 7 (Plan 09-07 references doc)** — will document this lockfile primitive in the data-layer contract reference.

**Cross-phase contract for Wave 3:** db-write.mjs MUST use `withLock` (not raw acquireLock/releaseLock) to ensure release on throw — the try/finally is the contract surface, not optional sugar.

---
*Phase: 09-duckdb-orchestration*
*Plan: 01 (Wave 1 — lockfile primitive)*
*Completed: 2026-05-07*
