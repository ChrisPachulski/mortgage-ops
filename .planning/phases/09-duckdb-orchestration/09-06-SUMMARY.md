---
phase: 09-duckdb-orchestration
plan: 06
subsystem: testing
tags: [phase-09, duckdb-orchestration, integration-tests, concurrency, pers-01, pers-02, pers-04, pers-05, pers-06, pytest-timeout]

# Dependency graph
requires:
  - phase: 09-00
    provides: Wave 0 stub names + node_orchestration_run conftest helper + REPO_ROOT export
  - phase: 09-01
    provides: orchestration/lockfile.mjs withLock + isStale + readLock + STALE_THRESHOLD_MS=60_000
  - phase: 09-02
    provides: orchestration/init-db.mjs idempotent CREATE TABLE IF NOT EXISTS DDL (7 tables)
  - phase: 09-03
    provides: orchestration/db-write.mjs cmdInsertLoan + cmdQuery + WRITE_COMMANDS Set
  - phase: 09-04
    provides: orchestration/db-write.mjs cmdRenderMarkdown with deterministic header + ORDER BY
  - phase: 09-05
    provides: data/known-loans.yml committed (proves catalog is in place before integration)
provides:
  - 4 new integration test files pinning ROADMAP SC-1..SC-4 end-to-end
  - test_init_db_idempotent.py — schema fingerprint via SHA256 of pragma_table_info
  - test_parallel_invocation.py — Popen-based concurrent insert-loan with race-window tolerance
  - test_stale_lockfile_recovery.py — acquired_at JSON aging + pre-flight isStale Node check
  - test_render_markdown_byte_identical.py — full pipeline init -> insert -> render -> SHA256 compare
  - 2 Wave 0 xfail stubs flipped via thin-wrapper delegation (PERS-04, PERS-05 traceability preserved)
  - pytest-timeout dev dependency for hung-process safety nets
affects: [phase-09-07, phase-10-claude-skill, gsd-verify-work]

# Tech tracking
tech-stack:
  added: [pytest-timeout>=2.3]
  patterns:
    - "Schema fingerprinting: SHA256 of sorted pragma_table_info JSON dump"
    - "Concurrent subprocess.Popen with race-window-tolerant assertions (final-state check)"
    - "Pre-flight Node ESM one-liner via --input-type=module for isStale verification"
    - "Thin-wrapper test delegation for Wave 0 stub name preservation"

key-files:
  created:
    - tests/test_orchestration/test_init_db_idempotent.py
    - tests/test_orchestration/test_parallel_invocation.py
    - tests/test_orchestration/test_stale_lockfile_recovery.py
    - tests/test_orchestration/test_render_markdown_byte_identical.py
  modified:
    - tests/test_orchestration/test_db_lifecycle.py (flipped test_concurrent_writes_serialize xfail)
    - tests/test_orchestration/test_lockfile.py (flipped test_stale_lockfile_reclaimed_after_60s xfail)
    - pyproject.toml (added pytest-timeout dev dependency)
    - uv.lock (resolved pytest-timeout==2.4.0)

key-decisions:
  - "D-06-09 enforced: @pytest.mark.timeout markers (90/60/30s) layered on top of subprocess timeout kwargs"
  - "Lockfile path is FIXED at data/.lock per Plan 09-01 D-01-01 (NOT sibling-of-DB) — tests target this path explicitly"
  - "Stale-lock test uses acquired_at JSON aging as load-bearing per D-01-02; os.utime is belt-and-suspenders only"
  - "Pre-flight isStale(readLock()) Node check runs BEFORE db-write to fail fast on seam regression (Blocker #3)"
  - "Race-window assertion is final-state (count + lockfile-released), not which process won (D-06-01)"
  - "test_init_db_idempotent was already flipped in earlier wave — left untouched per Task 5 conditional"

patterns-established:
  - "Schema fingerprint via SHA256 of pragma_table_info JSON dump (deterministic across DuckDB minor versions)"
  - "Race-window-tolerant concurrency assertions: successes >= 1 + failures must be lock-shaped + final count = baseline + successes"
  - "Pre-flight ESM Node one-liner pattern for cross-language seam verification"
  - "try/finally cleanup for fixed-path render artifacts (D-04-07 + D-06-06)"

requirements-completed: [PERS-01, PERS-02, PERS-04, PERS-05, PERS-06]

# Metrics
duration: 18min
completed: 2026-05-07
---

# Phase 09 Plan 06: integration-tests Summary

**End-to-end integration tests pin ROADMAP SC-1..SC-4 (idempotent init, parallel-writer serialization, stale-lock recovery, byte-identical render) with race-window-tolerant assertions, schema fingerprinting via SHA256 of pragma_table_info, and pre-flight isStale Node seam checks.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-07T17:12:00Z (approx)
- **Completed:** 2026-05-07T17:30:07Z
- **Tasks:** 6 (all completed)
- **Files modified:** 6 (4 created + 2 stub-flips), plus pyproject.toml + uv.lock

## Accomplishments

- 4 new integration test files (~673 lines total) pinning Phase 9's load-bearing concurrency, idempotency, and byte-equality contracts.
- 2 Wave 0 xfail stubs flipped via thin-wrapper delegation (PERS-04 + PERS-05 traceability preserved per D-06-05).
- Pass count delta: 535 → 543 (+8 net: 4 new test files contributing 6 test functions, 2 stub flips). 0 failed, 0 phase-9 xfailed (1 inherited Phase 5 ARM oracle xfail remains, unchanged).
- pytest-timeout==2.4.0 installed; @pytest.mark.timeout markers active per D-06-09 (90s parallel / 60s stale-reclaim / 30s fresh-blocks).
- Concurrency timing measured: parallel-invocation 0.33s wall (lockfile serialized cleanly), stale-reclaim ~0.5s, fresh-blocks ~15s (full timeout, expected polling pattern).
- mypy --strict + ruff check + ruff format all green across tests/test_orchestration/ (10 files).
- node --check passes on all .mjs files (no Node code touched per Rule-7).
- No leaked artifacts after suite: data/loans.md, data/scenarios.md, data/.lock all absent.

## Task Commits

Each task was committed atomically (no AI attribution per global rule + project rule):

1. **Task 1: test_init_db_idempotent.py** — `121e113` (test)
2. **Chore: pytest-timeout dependency** — `ad65715` (chore)
3. **Task 2: test_parallel_invocation.py** — `b9a4c09` (test)
4. **Task 3: test_stale_lockfile_recovery.py** — `214b2ef` (test)
5. **Task 4: test_render_markdown_byte_identical.py** — `81c77de` (test)
6. **Task 5: flip Wave 0 xfail stubs** — `cd6dae8` (test)

## Files Created/Modified

- `tests/test_orchestration/test_init_db_idempotent.py` (117 lines) — schema fingerprint test + 7-table existence guard
- `tests/test_orchestration/test_parallel_invocation.py` (167 lines) — concurrent Popen-based insert-loan
- `tests/test_orchestration/test_stale_lockfile_recovery.py` (236 lines) — positive 65s reclaim + negative 5s block + pre-flight isStale Node check
- `tests/test_orchestration/test_render_markdown_byte_identical.py` (153 lines) — full pipeline SHA256 byte-equality
- `tests/test_orchestration/test_db_lifecycle.py` (modified) — flipped test_concurrent_writes_serialize xfail to thin-wrapper delegation; removed now-unused pytest import
- `tests/test_orchestration/test_lockfile.py` (modified) — flipped test_stale_lockfile_reclaimed_after_60s xfail to thin-wrapper delegation; removed pytest import
- `pyproject.toml` — added pytest-timeout>=2.3 to dev dependency-group
- `uv.lock` — resolved pytest-timeout==2.4.0

## SC Pinning Matrix

| SC   | Requirement | End-to-end test                                                                        | Status |
|------|-------------|----------------------------------------------------------------------------------------|--------|
| SC-1 | PERS-01/02  | `test_init_db_idempotent_across_runs` + `test_init_db_creates_all_expected_tables`     | PINNED |
| SC-2 | PERS-05     | `test_parallel_inserts_serialize_via_lockfile`                                         | PINNED |
| SC-3 | PERS-04     | `test_stale_lockfile_reclaimed_after_60s_threshold` + `test_fresh_lockfile_under_60s_blocks_or_waits` | PINNED |
| SC-4 | PERS-06     | `test_render_markdown_byte_identical_end_to_end` (Wave 6) + Wave 4 unit-style test (D-06-08 dual-coverage)     | PINNED |
| SC-5 | PERS-07     | `test_known_loans_catalog_complete` (Wave 5)                                           | PINNED upstream |

## Pass Count Delta

| Marker             | Before Wave 6 | After Wave 6 | Delta |
|--------------------|---------------|--------------|-------|
| passed             | 535           | 543          | +8    |
| failed             | 0             | 0            | 0     |
| skipped            | 4             | 4            | 0     |
| xfailed (phase-9)  | 2             | 0            | -2    |
| xfailed (inherited Phase 5 ARM oracle) | 1 | 1 | 0 |

Net: +8 passed (4 new test files + 6 new test functions; 2 wrapper flips advance Wave 0 stubs from xfailed to passed; pre-existing tests unchanged). Phase 9 xfail count = 0; only the inherited Phase 5 `test_oracle_cross_validation_5_1` remains xfailed (deferred per Plan 05-06 Rule-4 — out of Phase 9 scope).

## Concurrency Test Results

- **test_parallel_inserts_serialize_via_lockfile** — 0.33s wall time. Both writers succeeded (lockfile correctly serialized them; the second waited the ~100ms POLL_INTERVAL + acquired). Outcome: `successes=2, failures=0`. Final loan count: baseline (0) + 2 = 2. Lockfile (data/.lock) released after both processes exited.
- **test_stale_lockfile_reclaimed_after_60s_threshold** — ~0.5s wall time. Pre-flight Node `isStale(readLock())` returned 0 (stale, as expected). db-write reclaimed the 65s-old lockfile and inserted successfully. Lockfile released after.
- **test_fresh_lockfile_under_60s_blocks_or_waits** — ~15.0s wall time (full subprocess timeout=15). Writer correctly polled-with-timeout against the 5s-fresh fixture lockfile; never reclaimed. Caught via `subprocess.TimeoutExpired` (acceptable per polling-with-timeout pattern; passes the negative assertion). Cleanup unlinked the fresh fixture lockfile after.

## pytest-timeout Confirmation

```toml
# pyproject.toml [dependency-groups] dev
dev = [
    "pytest>=9.0",
    "pytest-timeout>=2.3",
    ...
]
```

`uv.lock` resolved `pytest-timeout==2.4.0`. Plugin auto-registers the `timeout` marker (no `markers = [...]` ini-options entry needed for `--strict-markers` compatibility — the plugin's auto-registration satisfies it).

## Stale-Lock Test JSON Aging Confirmation

```python
stale_acquired_at_ms = int((time.time() - STALE_AGE_SECONDS) * 1000)
LOCKFILE.write_text(
    json.dumps(
        {
            "pid": 99999,
            "acquired_at": stale_acquired_at_ms,  # LOAD-BEARING per D-01-02
            "reason": "stale-test-fixture",
        },
        ...
    )
)
```

The `acquired_at` JSON field aging is load-bearing (per Plan 09-01 D-01-02: lockfile.mjs::isStale() reads `lock.acquired_at` and compares to `Date.now()` against `STALE_THRESHOLD_MS=60_000`). `os.utime(LOCKFILE, ...)` runs after as belt-and-suspenders for any defense-in-depth path. The pre-flight Node one-liner (`import {isStale, readLock} ...; process.exit(isStale(readLock()) ? 0 : 1)`) confirms the seam at runtime BEFORE db-write executes.

## Decisions Made

- **Used existing fixed lockfile path `data/.lock` instead of plan's sibling-path expectation.** The plan example showed `_lockfile_for(db_path)` returning `db_path.parent / f".{db_path.name}.lock"`, but `orchestration/lockfile.mjs` uses a hard-coded `LOCK_PATH = join(MORTGAGE_OPS, 'data', '.lock')` regardless of `MORTGAGE_OPS_DB_PATH`. Tests now correctly target this fixed path. Documented in test docstrings + module-level `LOCKFILE` constant.
- **Path imports moved into TYPE_CHECKING blocks for ruff TC003 compliance** in test_init_db_idempotent.py, test_parallel_invocation.py, test_stale_lockfile_recovery.py, test_render_markdown_byte_identical.py. The existing test_db_lifecycle.py keeps Path at runtime because it uses `Path(__file__).resolve()` for REPO_ROOT.
- **Left `test_init_db_idempotent` (test_db_lifecycle.py) untouched.** Plan Task 5 conditioned the flip on "IF the stub is still xfail-decorated"; this stub was already flipped in Wave 2 with a real implementation, so the conditional applied. Only the 2 actually-xfail-decorated stubs (`test_concurrent_writes_serialize`, `test_stale_lockfile_reclaimed_after_60s`) were re-pointed via thin-wrapper delegation.
- **Negative companion test catches `subprocess.TimeoutExpired`** to allow either fail-fast or polling-with-timeout outcomes per the plan's footnote on lockfile.mjs implementation flexibility. Both shapes satisfy the assertion that fresh locks aren't reclaimed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lockfile path mismatch between plan example and Wave 1 implementation**
- **Found during:** Task 2 (test_parallel_invocation.py)
- **Issue:** Plan example used `_lockfile_for(db_path)` with sibling-of-DB convention, but `orchestration/lockfile.mjs` ships with `LOCK_PATH = join(MORTGAGE_OPS, 'data', '.lock')` — a fixed repo-relative path. Tests using sibling-path would never see lockfile contention because real db-write uses a different path.
- **Fix:** Replaced helper function with module-level `LOCKFILE: Path = REPO_ROOT / "data" / ".lock"` constant. Used in test_parallel_invocation.py + test_stale_lockfile_recovery.py.
- **Files modified:** test_parallel_invocation.py, test_stale_lockfile_recovery.py
- **Verification:** All concurrency tests passed; lockfile is created at `data/.lock` and verified absent after suite.
- **Committed in:** `b9a4c09`, `214b2ef`

**2. [Rule 3 - Blocking] Plan Task 5 expected 3 xfail flips; only 2 xfails remain**
- **Found during:** Task 5
- **Issue:** Plan said to flip 3 stubs (`test_init_db_idempotent`, `test_concurrent_writes_serialize`, `test_stale_lockfile_reclaimed_after_60s`). Inspection showed only 2 are xfail-decorated; `test_init_db_idempotent` was already flipped to a real implementation in Wave 2. Plan's own conditional ("Do NOT modify ... IF they have ALREADY been flipped") covered this case.
- **Fix:** Flipped only the 2 actually-xfail-decorated stubs. Per Rule-1 (test contract names pinned) the existing real `test_init_db_idempotent` was left untouched.
- **Files modified:** test_db_lifecycle.py, test_lockfile.py
- **Verification:** `grep -c "@pytest.mark.xfail"` returns 0 in both files; `pytest tests/test_orchestration/ -v` shows 0 XFAIL, 0 FAILED.
- **Committed in:** `cd6dae8`

**3. [Rule 6 - Lint hygiene] ruff TC003 / UP037 / formatting**
- **Found during:** Tasks 1-4 (every new test file)
- **Issue:** ruff `TC003` flagged `from pathlib import Path` as type-only import; `UP037` flagged quoted module-level type annotation; `ruff format` reflowed long pytest decorator argument.
- **Fix:** Moved Path imports into `if TYPE_CHECKING:` blocks (since they were only used in annotations). Removed the quoted annotation from the LOCKFILE constant. Accepted ruff's formatter line-break decisions for `@pytest.mark.timeout(N)` decorators.
- **Files modified:** test_init_db_idempotent.py, test_parallel_invocation.py, test_stale_lockfile_recovery.py, test_render_markdown_byte_identical.py
- **Verification:** mypy --strict + ruff check + ruff format --check all green.
- **Committed in:** part of Tasks 1-4 commits

**4. [Rule 3 - Blocking] STALE_THRESHOLD_SECONDS / STALE_AGE_SECONDS literal annotation**
- **Found during:** Task 3 acceptance grep
- **Issue:** I initially typed `STALE_THRESHOLD_SECONDS: int = 60` but the plan's `grep -c "STALE_THRESHOLD_SECONDS = 60"` acceptance check fails on the typed form.
- **Fix:** Removed `: int` annotation (constants are inferred as int anyway).
- **Files modified:** test_stale_lockfile_recovery.py
- **Verification:** Both grep counts return 1 as required; mypy still clean.
- **Committed in:** part of `214b2ef`

---

**Total deviations:** 4 auto-fixed (3 blocking, 1 lint hygiene)
**Impact on plan:** All deviations were minor adapter fixes between plan example code and real-world Wave 1-5 ship state. No scope changes; no Node code touched (Rule-7 honored). Plan intent preserved.

## Issues Encountered

None — all 6 tasks executed cleanly. The pre-flight isStale Node check (Blocker #3 fix in iter-2) ran exactly once and confirmed the seam works end-to-end without surprises.

## User Setup Required

None — Phase 9 is fully internal (orchestration scripts + tests). No external services, no credentials, no environment variables.

## Next Phase Readiness

**Phase 9 ready for /gsd-verify-work and Plan 09-07 (references docs).**

- All 7 PERS requirements (PERS-01..07) closed.
- All 5 ROADMAP SC- success criteria pinned by passing tests.
- xfail count = 0 across phase-9 (1 unrelated Phase 5 ARM oracle xfail still queued for Phase 8+).
- Pitfall coverage: Pitfall 2 (race window) regression-protected via `test_parallel_inserts_serialize_via_lockfile`; Pitfall 3 (render determinism) double-protected via Wave 4 + Wave 6.
- Lint clean: mypy --strict + ruff check + ruff format all green on 10 source files in tests/test_orchestration/.
- No leaked artifacts.

Phase 10 (Claude Skill Frontend) can begin once verifier confirms.

## Self-Check: PASSED

- All 4 created test files exist on disk (verified via `ls`).
- All 6 commits exist in `git log` (verified): `121e113`, `ad65715`, `b9a4c09`, `214b2ef`, `81c77de`, `cd6dae8`.
- Full suite: 543 passed, 4 skipped, 1 xfailed (inherited Phase 5), 0 failed.
- Phase 9 only: 22 passed, 0 xfailed, 0 failed.
- mypy --strict clean (10 source files).
- ruff check + ruff format --check clean.
- node --check clean on all 3 .mjs files (no Node code touched).
- Cleanup absent: data/loans.md, data/scenarios.md, data/.lock all unlinked after suite.

---
*Phase: 09-duckdb-orchestration*
*Plan: 06 (integration-tests)*
*Completed: 2026-05-07*
