---
phase: 09-duckdb-orchestration
plan: 03
subsystem: orchestration

tags:
  - phase-09
  - duckdb-orchestration
  - db-write
  - insert-subcommands
  - decimal-discipline
  - withlock-wrap
  - pers-03
  - pers-05

# Dependency graph
requires:
  - phase: 09-duckdb-orchestration
    plan: 00
    provides: "tests/test_orchestration/test_db_lifecycle.py with 4 xfail stubs awaiting flip + node_orchestration_run helper"
  - phase: 09-duckdb-orchestration
    plan: 01
    provides: "orchestration/lockfile.mjs withLock import target"
  - phase: 09-duckdb-orchestration
    plan: 02
    provides: "package.json with duckdb-async@1.4.2 + 6-table schema (loans.annual_rate per D-02-04) for INSERTs to land in"
provides:
  - "orchestration/db-write.mjs (281 lines) — central writer CLI with 5 handlers (4 functional + 1 reserved): cmdInsertLoan, cmdInsertScenario, cmdInsertReport, cmdQuery, cmdRenderMarkdown (placeholder)"
  - "WRITE_COMMANDS Set = {insert-loan, insert-scenario, insert-report, render-markdown} gates withLock acquisition; query bypasses (D-03-01)"
  - "DECIMAL string round-trip discipline VERIFIED at the persistence boundary (D-03-02 + D-03-03)"
  - "PERS-03 closed for ALL THREE insert subcommands at the integration layer; render-markdown closure deferred to Wave 4"
  - "PERS-05 closed at grep level (withLock wrap on WRITE_COMMANDS); concurrency end-to-end test deferred to Wave 6"
affects:
  - "09-04 render-markdown (Wave 4) — REMOVES the 'Not yet implemented (--render-markdown ships in Plan 09-04)' placeholder string from cmdRenderMarkdown; ships byte-identical SELECT + write logic"
  - "09-06 concurrency (Wave 6) — flips test_concurrent_writes_serialize via parallel `db-write.mjs insert-loan` invocations against this writer"

# Tech tracking
tech-stack:
  added: []  # No new runtime libraries; uses duckdb-async (Wave 2) + lockfile.mjs (Wave 1) only
  patterns:
    - "Subcommand dispatcher with HANDLERS map + WRITE_COMMANDS gate Set — career-ops/scripts/db-write.mjs:687-740 idiom"
    - "Argument parser supporting both --key value and --key=value forms (career-ops db-write.mjs:55-83 verbatim port)"
    - "BEGIN TRANSACTION / COMMIT / ROLLBACK try/catch wrap on every INSERT — atomicity discipline (D-03-04)"
    - "DECIMAL VARCHAR round-trip: strings on INSERT, CAST AS VARCHAR on SELECT — closes Critical Issue 2"
    - "BigInt JSON-replacer in cmdQuery — duckdb-async returns INTEGER columns as bigint; replacer collapses to Number for JSON serialization"
    - "withLock(action, { reason: command }) wraps DB lifecycle (Database.create -> handler -> close) inside the cross-process lock"

key-files:
  created:
    - "orchestration/db-write.mjs — 281 lines; 5 subcommand handlers + dispatcher + arg parser + run() error envelope"
  modified:
    - "tests/test_orchestration/test_db_lifecycle.py — flipped 4 xfail stubs to passing (insert_loan, insert_scenario, insert_report, decimal_string_round_trip); 1 xfail remains (test_concurrent_writes_serialize, Wave 6)"

key-decisions:
  - "D-03-01 LOCKED: WRITE_COMMANDS gates lock acquisition; query bypasses — read-only ops don't need cross-process lock (DuckDB MVCC handles concurrent readers); career-ops parallel"
  - "D-03-02 LOCKED: Every DECIMAL column SELECTed via CAST AS VARCHAR — duckdb-async returns DECIMAL as JS bigint; CAST AS VARCHAR forces lossless string round-trip; project-wide invariant per CLAUDE.md"
  - "D-03-03 LOCKED: Every DECIMAL column INSERTed as JSON string — mirrors Phase 1 D-02 / Phase 3 D-19 / Phase 4 D-13 / Phase 5 D-19 boundary discipline"
  - "D-03-04 LOCKED: BEGIN TRANSACTION + COMMIT/ROLLBACK try-catch around every INSERT — atomicity + future-proofing for multi-row inserts"
  - "D-03-05 LOCKED: insert-scenario stores request_json + response_json as JSON columns — avoids schema-migration churn when Phase 4-8 response shapes evolve"
  - "D-03-06 LOCKED: render-markdown is RESERVED but not implemented — Wave 4 owns it end-to-end; placeholder throws 'Not yet implemented (--render-markdown ships in Plan 09-04)'"

patterns-established:
  - "Subcommand-dispatcher Node ESM CLI pattern (HANDLERS map + WRITE_COMMANDS gate Set) — Wave 4 will extend with cmdRenderMarkdown body"
  - "DECIMAL VARCHAR round-trip discipline at the persistence boundary (string in, CAST AS VARCHAR out) — every later wave that SELECTs money columns must honor this"
  - "Reserved-handler-with-clear-error pattern: cmdRenderMarkdown throws 'Not yet implemented' until Wave 4 replaces; gives explicit signal if invoked early"

requirements-completed:
  - PERS-03  # 3 of 4 insert subcommands shipped (insert-loan, insert-scenario, insert-report); render-markdown deferred to Wave 4 (also under PERS-03 umbrella but not blocked here)
  # PERS-05 NOT marked complete — withLock wrap is shipped, but concurrency end-to-end test (test_concurrent_writes_serialize) lands in Wave 6

# Metrics
duration: 4min
completed: 2026-05-07
---

# Phase 09 Plan 03: DB-Write Inserts Summary

**Central writer CLI shipped (orchestration/db-write.mjs, 281 lines, 5 subcommand handlers) with WRITE_COMMANDS-gated withLock + BEGIN TRANSACTION/COMMIT/ROLLBACK discipline + DECIMAL VARCHAR round-trip — 4 xfails flipped (insert-loan + insert-scenario + insert-report + decimal-cents); pass count 529 -> 533 + xfail 9 -> 5; PERS-03 closed for all three insert subcommands.**

## Performance

- **Duration:** ~4 min (start 2026-05-07T16:56:19Z, end 2026-05-07T17:00:08Z; 229s wall-clock; 2 commits)
- **Tasks:** 3 (Task 3 was verification-only — no commit, mirroring Wave 0 / Wave 1 / Wave 2 precedent)
- **Files created:** 1 (orchestration/db-write.mjs)
- **Files modified:** 1 (tests/test_orchestration/test_db_lifecycle.py)

## Subcommand Inventory

| Subcommand | Handler | Lock? | Transaction? | Status |
|------------|---------|-------|--------------|--------|
| insert-loan | cmdInsertLoan | YES (withLock) | BEGIN/COMMIT/ROLLBACK | SHIPPED |
| insert-scenario | cmdInsertScenario | YES (withLock) | BEGIN/COMMIT/ROLLBACK | SHIPPED |
| insert-report | cmdInsertReport | YES (withLock) | BEGIN/COMMIT/ROLLBACK | SHIPPED |
| query | cmdQuery | NO (bypasses) | — (read-only) | SHIPPED |
| render-markdown | cmdRenderMarkdown | YES (withLock) | n/a (placeholder) | RESERVED for Wave 4 |

The render-markdown handler throws `Not yet implemented (--render-markdown ships in Plan 09-04). Per Phase 9 plan sequence, this slot is reserved.` This string will be REMOVED by Plan 09-04, which has a grep gate verifying that.

## WRITE_COMMANDS Set + withLock Wrapping

```javascript
const WRITE_COMMANDS = new Set([
  'insert-loan', 'insert-scenario', 'insert-report', 'render-markdown',
]);

if (WRITE_COMMANDS.has(command)) {
  await withLock(action, { reason: command });
} else {
  await action();  // query bypasses lock per D-03-01
}
```

Verified at grep level:
- `grep -c "WRITE_COMMANDS = new Set" orchestration/db-write.mjs` → 1
- `grep -c "withLock(action" orchestration/db-write.mjs` → 1
- `grep -c "import { withLock } from './lockfile.mjs'" orchestration/db-write.mjs` → 1
- `grep -c "await db.run('BEGIN TRANSACTION')" orchestration/db-write.mjs` → 3 (one per insert)
- `grep -c "await db.run('ROLLBACK')" orchestration/db-write.mjs` → 3 (one per insert)

## DECIMAL String Round-Trip Coverage

The `test_decimal_string_round_trip_preserves_cents` test exercises **4 boundary values** to pin the duckdb-async DECIMAL→bigint coercion bug at every cent of precision:

| Boundary | Value | Rationale |
|----------|-------|-----------|
| Cent precision (load-bearing) | `200000.01` | Wikipedia $200k loan + 1 cent — the canonical case |
| Smallest positive money | `0.01` | One penny — minimum DECIMAL(14,2) granularity |
| Large value (bigint risk zone) | `99999999.99` | Near DECIMAL(14,2) maximum (10^12 - 0.01); bigint coercion would silently truncate |
| Random mid-range | `1234567.89` | Arbitrary value to catch off-by-one in scale handling |

All 4 round-trip byte-exact via `CAST(principal AS VARCHAR)` SELECT discipline.

## Wave-Flip Status

| Stub | File | Pre-Wave-3 | Post-Wave-3 |
|------|------|------------|-------------|
| `test_insert_loan_round_trip` | test_db_lifecycle.py | XFAIL | **PASSED** ✓ |
| `test_insert_scenario_round_trip` | test_db_lifecycle.py | XFAIL | **PASSED** ✓ |
| `test_insert_report_round_trip` | test_db_lifecycle.py | XFAIL | **PASSED** ✓ |
| `test_decimal_string_round_trip_preserves_cents` | test_db_lifecycle.py | XFAIL | **PASSED** ✓ |
| `test_concurrent_writes_serialize` | test_db_lifecycle.py | XFAIL | XFAIL (Wave 6) |
| `test_stale_lockfile_reclaimed_after_60s` | test_lockfile.py | XFAIL | XFAIL (Wave 6) |
| `test_render_markdown_byte_identical` | test_render_markdown.py | XFAIL | XFAIL (Wave 4) |
| `test_known_loans_catalog_complete` | test_known_loans_smoke.py | XFAIL | XFAIL (Wave 5) |

Wave 3 flips exactly 4 xfails (per the 2026-05-04 revised plan; was 2 in v1).

## Test Counts

- **Pre-Wave-3 baseline (Plan 09-02 final):** 529 passed + 4 skipped + 9 xfailed
- **Post-Wave-3 (Plan 09-03 final):** **533 passed + 4 skipped + 5 xfailed** (+4 net passes; -4 net xfails; zero regression)
- **Plan target:** 533 passed + 5 xfailed — **HIT EXACTLY**

The 5 remaining system-wide xfails:
1. `test_oracle_cross_validation_5_1` (Phase 5 ARM oracle deferral — not Phase 9)
2. `test_concurrent_writes_serialize` (Wave 6)
3. `test_stale_lockfile_reclaimed_after_60s` (Wave 6)
4. `test_render_markdown_byte_identical` (Wave 4)
5. `test_known_loans_catalog_complete` (Wave 5)

## Smoke Test (Manual)

```bash
$ rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal
$ MORTGAGE_OPS_DB_PATH=/tmp/smoke.duckdb node orchestration/init-db.mjs
init-db: schema ready
$ cat > /tmp/loan.json <<EOF
{"principal":"200000.01","annual_rate":"0.065000","term_months":360,"origination_date":"2026-05-01","loan_type":"fixed"}
EOF
$ MORTGAGE_OPS_DB_PATH=/tmp/smoke.duckdb node orchestration/db-write.mjs insert-loan --json /tmp/loan.json
{"ok":true,"loan_id":1}
$ MORTGAGE_OPS_DB_PATH=/tmp/smoke.duckdb node orchestration/db-write.mjs query --sql "SELECT id, CAST(principal AS VARCHAR) AS principal, CAST(annual_rate AS VARCHAR) AS annual_rate FROM loans"
[{"id":1,"principal":"200000.01","annual_rate":"0.065000"}]
```

DECIMAL string round-trip: `200000.01` in, `200000.01` out. Annual rate `0.065000` likewise.

## Task Commits

Each task was committed atomically (no Co-Authored-By or AI attribution per global Git Attribution rule):

1. **Task 1: feat(09-03): add orchestration/db-write.mjs with 4 subcommands + dispatcher** — `dc86026`
2. **Task 2: test(09-03): flip 4 xfails to passing in test_db_lifecycle.py** — `b696d91`
3. **Task 3: Verify zero regression + lint hygiene** — verification-only, no commit (Wave 0/1/2 precedent)

## Files Created/Modified

- `orchestration/db-write.mjs` — 281 lines. Imports: Database (duckdb-async), readFileSync/existsSync (fs), join/dirname (path), fileURLToPath (url), withLock (./lockfile.mjs). Top-level constants: ORCH_DIR, MORTGAGE_OPS, DB_PATH (honors MORTGAGE_OPS_DB_PATH env-var seam per D-00-04). parseArgs() handles both --key value and --key=value forms (career-ops verbatim port). 5 handlers: cmdInsertLoan, cmdInsertScenario, cmdInsertReport, cmdQuery, cmdRenderMarkdown. Dispatcher: HANDLERS map + WRITE_COMMANDS gate Set + run() async with top-level catch envelope.
- `tests/test_orchestration/test_db_lifecycle.py` — flipped 4 xfail stubs (removed @pytest.mark.xfail decorators; replaced `pytest.fail("Wave 0 stub")` with real assertions). Each flipped test creates a tmp_path-isolated DB, init-db.mjs bootstraps schema, db-write.mjs inserts a fixture, db-write.mjs query returns the row, assertions verify round-trip exactness. `import json` added at module level (was previously a stub-only file with no JSON parsing).

## Decisions Made

All six decisions are LOCKED at the plan level (D-03-01..D-03-06) — the executor honored them verbatim. No new plan-level decisions emerged during execution.

- **D-03-01 LOCKED — WRITE_COMMANDS gates lock; query bypasses:** career-ops/scripts/db-write.mjs:668 verbatim pattern; RESEARCH §Pattern 2 explicit.
- **D-03-02 LOCKED — DECIMAL VARCHAR on SELECT:** PATTERNS Critical Issue 2 + RESEARCH Pitfall 1; project-wide invariant per CLAUDE.md money discipline.
- **D-03-03 LOCKED — DECIMAL string on INSERT:** Phase 1 D-02 / Phase 3 D-19 / Phase 4 D-13 / Phase 5 D-19 inheritance; cmdInsertLoan validates `typeof === 'string'` for principal + annual_rate; throws on float.
- **D-03-04 LOCKED — BEGIN/COMMIT/ROLLBACK on every INSERT:** RESEARCH §Anti-Patterns "Skipping BEGIN TRANSACTION" + career-ops db-write.mjs:226-252 + 346-368 verbatim pattern.
- **D-03-05 LOCKED — Scenario request_json + response_json as JSON columns:** RESEARCH §c table 3 + PATTERNS Critical Issue 3 schema rationale; avoids schema-migration churn.
- **D-03-06 LOCKED — render-markdown reserved but not implemented here:** clean wave separation; Wave 4 owns the byte-identical contract end-to-end. Placeholder throws explicit error if invoked early.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule-3 Hygiene] Ruff format auto-collapsed long-line assertion message in test_db_lifecycle.py**
- **Found during:** Task 2 (after writing the 4 flipped test bodies)
- **Issue:** `ruff format --check` flagged `tests/test_orchestration/test_db_lifecycle.py` as needing reformat. The trigger was a 110-char line in test_insert_loan_round_trip:
  ```python
  assert row["principal"] == "200000.00", (
      f"DECIMAL string round-trip broke: {row['principal']!r}"
  )
  ```
  vs ruff's preferred single-line form (under 100 chars):
  ```python
  assert row["principal"] == "200000.00", f"DECIMAL string round-trip broke: {row['principal']!r}"
  ```
- **Fix:** Ran `uv run ruff format tests/test_orchestration/test_db_lifecycle.py`; accepted the collapse. Pytest still reports 5 passed + 1 xfailed in this file (no test contract change).
- **Plan acknowledgement:** Plan deviation_rules Rule-3 explicitly authorizes this: "ruff format auto-fix on the Python test changes" → "apply minimal fix and document in SUMMARY as Rule-3."
- **Files modified:** tests/test_orchestration/test_db_lifecycle.py (formatting only — no functional change)
- **Verification:** `uv run ruff format --check tests/test_orchestration/` → 6 files already formatted; pytest still passes all 4 flipped tests.
- **Committed in:** `b696d91` (Task 2 commit, applied during lint sub-loop before commit)

### Documented Plan-Acceptance-Drift (no functional impact)

**2. [Rule-3 Hygiene] Plan grep counts include comment-mentions of BEGIN TRANSACTION + ROLLBACK; semantics correct**
- **Found during:** Task 1 acceptance-criteria verification
- **Issue:** The plan's verify-block specifies `grep -c "BEGIN TRANSACTION" orchestration/db-write.mjs` MUST return 3 and `grep -c "ROLLBACK" orchestration/db-write.mjs` MUST return 3. However, the file's header comment block AND the cmdInsertScenario/cmdInsertReport BEGIN/ROLLBACK code paths together produce 5 hits each (2 in comments + 3 in code). The semantically correct counts (code-level only, via `grep -c "await db.run('BEGIN TRANSACTION')"`) are 3 + 3 as the plan intends.
- **Resolution:** Verified at the semantic level: `grep -c "await db.run('BEGIN TRANSACTION')" orchestration/db-write.mjs` returns 3 (one per insert handler); same for ROLLBACK. The plan's grep is comment-naïve about its own prescribed header text; this is a plan-internal arithmetic glitch consistent with Wave 1 + Wave 2 SUMMARY's documented precedent.
- **Files modified:** None.
- **Plan acknowledgement:** Wave 1 SUMMARY established this precedent: "Plan verify-block grep counts include comment-mentions; semantics correct."

**3. [Rule-3 Hygiene] Plan xfail-decorator-count for test_db_lifecycle.py: expected 2, actual 1 (math reconciles)**
- **Found during:** Task 2 acceptance-criteria verification
- **Issue:** The plan's Task 2 acceptance criterion says `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_db_lifecycle.py` returns 2 (init + concurrent). However, Wave 2 already flipped `test_init_db_idempotent`, leaving only `test_concurrent_writes_serialize` xfail in this file pre-Wave-3 (5 xfails total: init was already gone). After Wave 3 flips 4 more, only 1 xfail remains in this file (test_concurrent_writes_serialize, Wave 6).
- **Resolution:** The substantive criterion is satisfied: exactly 4 xfail decorators removed (one per flipped test); 1 xfail remains in this file (will flip in Wave 6). pytest reports `5 passed, 1 xfailed in this file` — exact +4/-4 delta vs pre-Wave-3 (`1 passed, 5 xfailed in this file`).
- **Verification:** `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_db_lifecycle.py` returns 1; `pytest tests/test_orchestration/test_db_lifecycle.py -v --tb=no` reports `5 passed, 1 xfailed`.
- **Files modified:** None.
- **Plan acknowledgement:** Plan was authored from a pre-Wave-2-completion snapshot; the substantive contract — exactly 4 xfail decorators removed for the 4 named tests, all others preserved — is honored.

---

**Total deviations:** 3 (1 Rule-3 ruff-format auto-fix + 2 documented plan-arithmetic drifts; all hygiene-only).
**Impact on plan:** Zero functional change. The db-write.mjs file structure, all 5 handler signatures, the WRITE_COMMANDS Set contents, the BEGIN/COMMIT/ROLLBACK try-catch discipline, the DECIMAL string round-trip discipline, and the 4 xfail flips are all delivered exactly as specified. No Rule-1 (bug), Rule-2 (missing critical functionality), or Rule-4 (architectural) deviations occurred.

## Issues Encountered

None — execution was clean. All three Rule-3 deviations were anticipated by the plan's deviation_rules section + Wave 1/2 SUMMARY precedent.

## Lint + Type Hygiene Status

| Check | Result |
|-------|--------|
| `uv run pytest -q` | **533 passed + 4 skipped + 5 xfailed** (was 529+4+9; +4 passes, -4 xfails; zero regression) |
| `uv run pytest tests/test_orchestration/test_db_lifecycle.py -v` | 5 passed + 1 xfailed in 1.16s |
| `node --check orchestration/db-write.mjs` | syntax OK |
| `node orchestration/db-write.mjs --help` | exit 0; lists insert-loan/insert-scenario/insert-report/render-markdown/query |
| `uv run mypy --strict tests/test_orchestration/` | Success: no issues found in 6 source files |
| `uv run ruff check tests/test_orchestration/` | All checks passed! |
| `uv run ruff format --check tests/test_orchestration/` | 6 files already formatted |
| End-to-end smoke (init -> insert -> query) | DECIMAL `200000.01` + `0.065000` round-trip byte-exact |

## User Setup Required

None — Wave 3 is additive code (1 new .mjs file) + 1 test-file modification (4 flips). No environment variables, dashboard configuration, credential setup, or schema migrations needed. The MORTGAGE_OPS_DB_PATH env-var seam established in Wave 0 / Wave 2 continues to be honored at the implementation layer.

## Threat Model Coverage

The plan's threat_model section enumerates 5 STRIDE threats (T-09-13..T-09-17). Implementation status:

| Threat ID | Mitigation Implemented | Verified By |
|-----------|------------------------|-------------|
| T-09-13 (SQL injection via JSON payload) | ALL INSERTs use parameterized `?` placeholders; never string-interpolate user values | Code review (cmdInsertLoan/Scenario/Report use `db.all(SQL, val1, val2, ...)` form) |
| T-09-14 (DECIMAL→float silent precision loss) | `typeof === 'string'` guard at boundary; CAST AS VARCHAR for SELECT; round-trip test pins contract | test_decimal_string_round_trip_preserves_cents (4 boundary values) |
| T-09-15 (SQL injection via --sql in cmdQuery) | accepted (developer-only CLI per RESEARCH §Security Domain) | n/a |
| T-09-16 (orphaned DB handle on throw) | try { handler } finally { db.close() } pattern in run() action closure | Code review (action() in run() uses try/finally) |
| T-09-17 (uncommitted partial INSERT survives) | catch ROLLBACK on every subcommand; transaction is atomic | grep verification: 3 BEGIN TRANSACTION + 3 ROLLBACK code-level (one per insert handler) |

## Self-Check: PASSED

Verified at SUMMARY-write time:

**Files exist:**
- `orchestration/db-write.mjs` exists at 281 lines (`wc -l` confirms)
- `tests/test_orchestration/test_db_lifecycle.py` modified (4 flipped tests + 1 remaining xfail; `import json` added)

**Commits exist:**
- `dc86026` (Task 1: feat(09-03) add orchestration/db-write.mjs) — found via `git log --oneline | grep dc86026`
- `b696d91` (Task 2: test(09-03) flip 4 xfails) — found via `git log --oneline | grep b696d91`

**Subcommand inventory:**
- 4 functional handlers (cmdInsertLoan, cmdInsertScenario, cmdInsertReport, cmdQuery) — verified via `grep -c "async function cmd"` returns 5 (4 functional + 1 reserved cmdRenderMarkdown)
- WRITE_COMMANDS Set present — `grep -c "WRITE_COMMANDS = new Set"` returns 1
- withLock import present — `grep -c "import { withLock } from './lockfile.mjs'"` returns 1

**Tests:**
- 4 flipped tests pass — verified via `pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_loan_round_trip ... -v` reports `4 passed`
- Full pytest suite reports 533 passed + 4 skipped + 5 xfailed (verified)
- mypy --strict + ruff check + ruff format --check all clean (verified)

**Render-markdown placeholder:**
- `grep -c "Not yet implemented" orchestration/db-write.mjs` returns 1 (the placeholder string Wave 4 will remove)

**Smoke test:**
- `node orchestration/db-write.mjs --help` exits 0 with all 5 subcommands listed
- End-to-end insert + query against tmp DuckDB confirms `200000.01` and `0.065000` round-trip byte-exact

## Next Phase Readiness

**Wave 4 (Plan 09-04 render-markdown) unblocked** — has the dispatcher slot ready (cmdRenderMarkdown placeholder); has the WRITE_COMMANDS Set with 'render-markdown' already enrolled; has the schema (Wave 2) + insert subcommands (this wave) producing rows for render-markdown to SELECT against. Plan 09-04 will REPLACE the cmdRenderMarkdown body and REMOVE the 'Not yet implemented (--render-markdown ships in Plan 09-04)' string (grep gate verifies removal).

**Wave 5 (Plan 09-05 known-loans.yml) unblocked** — js-yaml is installed (Wave 2); the schema's `loans.known_loan_id` column is the FK target; this wave's insert-loan subcommand is the natural ingestion path for catalog entries.

**Wave 6 (Plan 09-06 concurrency tests) unblocked** — `test_concurrent_writes_serialize` will spawn N parallel `db-write.mjs insert-loan` subprocesses against this writer; the WRITE_COMMANDS-gated withLock + BEGIN/COMMIT/ROLLBACK discipline is the contract under test. `test_stale_lockfile_reclaimed_after_60s` will pre-create a stale lock and verify reclaim.

**Wave 7 (Plan 09-07 references doc)** — will document the db-write.mjs subcommand surface (this wave's deliverable) in the data-layer contract reference alongside the schema (Wave 2) + lockfile (Wave 1).

**Cross-phase contract for Wave 4:**
- Plan 09-04 must REMOVE the literal string `'Not yet implemented (--render-markdown ships in Plan 09-04)'` from cmdRenderMarkdown (Plan 09-04 has a grep gate verifying that).
- Plan 09-04 must SELECT money columns via `CAST(col AS VARCHAR)` per D-03-02 (DECIMAL discipline is project-wide, not per-wave).
- Plan 09-04 must keep cmdRenderMarkdown wrapped in withLock (it is already enrolled in WRITE_COMMANDS) — render-markdown writes data/loans.md + data/scenarios.md, so it counts as a write op.

---
*Phase: 09-duckdb-orchestration*
*Plan: 03 (Wave 3 — db-write subcommand inserts)*
*Completed: 2026-05-07*
