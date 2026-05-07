---
phase: 09-duckdb-orchestration
verified: 2026-05-04T00:00:00Z
status: passed
score: 5/5
overrides_applied: 0
---

# Phase 9: DuckDB Persistence & Node Orchestration — Verification Report

**Phase Goal:** Wire DuckDB single-file persistence with the career-ops lockfile pattern and a Node `db-write.mjs` central writer for cross-scenario SQL queries and report storage.
**Verified:** 2026-05-04
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `node orchestration/init-db.mjs` is idempotent — running it twice on a fresh checkout produces the same schema (loans, scenarios, reports, payments, applicants, properties tables) with no errors | VERIFIED | Live run: both invocations exit with "schema ready" and zero errors. All 7 DDL statements use `CREATE TABLE IF NOT EXISTS` + `CREATE SEQUENCE IF NOT EXISTS`. Two dedicated tests pass: `test_init_db_idempotent_across_runs` (SHA256 fingerprint of `pragma_table_info` for all 7 tables matches across runs) and `test_init_db_creates_all_expected_tables`. |
| 2 | `node orchestration/db-write.mjs --insert-loan --json fixtures/loan.json` writes through `withLock()` and a concurrent second invocation either waits or fails fast (never corrupts) | VERIFIED | `db-write.mjs` imports `withLock` from `lockfile.mjs` (line 32); `WRITE_COMMANDS` set (line 295) includes `insert-loan`; dispatcher calls `withLock(action, { reason: command })` for all write subcommands (lines 338-339). `test_parallel_inserts_serialize_via_lockfile` spawns two concurrent Popen processes, asserts at least one succeeds, any failure is lock-shaped (not corruption-shaped), final row count = baseline + successes, lockfile released after both exit. Test passes. |
| 3 | Stale lockfile recovery triggers at 60s: a lockfile with `mtime > 60s ago` is reclaimed and the write proceeds | VERIFIED | `STALE_THRESHOLD_MS = 60_000` (lockfile.mjs line 27); `isStale()` computes `Date.now() - lock.acquired_at > STALE_THRESHOLD_MS` (JSON acquired_at-based, not mtime-based per D-01-02). `test_stale_lockfile_reclaimed_after_60s_threshold` pre-creates a lockfile with `acquired_at` = now - 65s, runs preflight `isStale()` check, then invokes `db-write.mjs insert-loan` and asserts exit 0. `test_fresh_lockfile_under_60s_blocks_or_waits` confirms a 5s-old lock is NOT reclaimed (negative guard). All stale-recovery tests pass. |
| 4 | `data/loans.md` and `data/scenarios.md` regenerate from DuckDB via `node orchestration/db-write.mjs --render-markdown` and are byte-identical across runs | VERIFIED | `render-markdown` subcommand: uses explicit `ORDER BY id ASC` in both render SELECTs (D-04-03), no `NOW()` embedded in output (D-04-04), mandatory `<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->` header (D-04-01), DECIMAL columns cast as VARCHAR (D-04-02). Both `test_render_markdown_byte_identical` and the end-to-end `test_render_markdown_byte_identical_end_to_end` (full init→3 inserts→render→render→SHA256) pass. `render-markdown` is in `WRITE_COMMANDS` and goes through `withLock()`. |
| 5 | `data/known-loans.yml` catalog is committed with at least seven product entries (30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1, FHA 30yr, VA 30yr, jumbo) loadable via a smoke test | VERIFIED | File confirmed at `data/known-loans.yml` with 7 products: `['arm-5-1', 'arm-7-1', 'conv-15yr-fixed', 'conv-30yr-fixed', 'fha-30yr', 'jumbo-30yr-fixed', 'va-30yr']`. All `loan_type` values (`fixed`, `arm`, `fha`, `va`, `jumbo`) are valid `lib.models.Loan.loan_type` Literals. All 7 entries have the full 9-key schema (`id`, `label`, `loan_type`, `principal`, `apr`, `term_months`, `frequency`, `origination_date`, `citation_url`). `principal` and `apr` are quoted strings (Decimal discipline). `test_known_loans_catalog_complete` passes. |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `orchestration/lockfile.mjs` | Cross-process mutex with `withLock()`, `acquireLock()`, `releaseLock()`, `isStale()`, `readLock()`, 60s threshold | VERIFIED | All 5 exports confirmed present. `STALE_THRESHOLD_MS = 60_000`. `node --check` passes. |
| `orchestration/init-db.mjs` | Idempotent DuckDB schema bootstrapper creating 6+1 tables | VERIFIED | 7 `CREATE TABLE IF NOT EXISTS` + 7 `CREATE INDEX IF NOT EXISTS` + `INSERT ... ON CONFLICT DO NOTHING` for idempotency. MORTGAGE_OPS_DB_PATH env-var override present. `node --check` passes. |
| `orchestration/db-write.mjs` | Central writer with insert-loan, insert-scenario, insert-report, render-markdown, query subcommands; all writes through withLock() | VERIFIED | All 5 subcommands in HANDLERS map. WRITE_COMMANDS gates lock acquisition; query bypasses. BEGIN/COMMIT/ROLLBACK wrapping. DECIMAL via CAST AS VARCHAR on reads. `node --check` passes. |
| `data/known-loans.yml` | 7-entry product catalog (30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1, FHA 30yr, VA 30yr, jumbo) | VERIFIED | 7 products confirmed. `source:` + `effective:` Reference Layer keys present. |
| `tests/conftest.py` | `node_orchestration_run` helper with MORTGAGE_OPS_DB_PATH env-var support | VERIFIED | Helper present at `conftest.py` lines 169-207. Sets env var for DB isolation. |
| `tests/test_orchestration/*.py` | 28 tests covering all 5 SCs and PERS-01..07 | VERIFIED | 28 tests, all passing. |
| `references/data-layer.md` | Phase 9 reference document | VERIFIED | File exists at `references/data-layer.md`. |
| `DATA_CONTRACT.md` | Layer contract updated with Phase 9 entries | VERIFIED | File exists at `DATA_CONTRACT.md`. |
| `.gitignore` | Phase 9 artifacts ignored: `data/*.duckdb`, `data/.lock`, `data/loans.md`, `data/scenarios.md` | VERIFIED | All 4 patterns confirmed present. `data/known-loans.yml` NOT ignored (Reference Layer, committed). `test_gitignore_known_loans_NOT_ignored` and `test_gitignore_duckdb_file_IS_ignored` pass. |
| `pyproject.toml` | `pytest-timeout>=2.3` dev dependency | VERIFIED | Present in `[dependency-groups] dev`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `db-write.mjs` | `lockfile.mjs` | `import { withLock } from './lockfile.mjs'` | WIRED | Line 32; used at lines 338-339 for all WRITE_COMMANDS. |
| `db-write.mjs` | DuckDB | `Database.create(DB_PATH)` inside `withLock()` action | WIRED | Lock acquired before DB opens; DB closed in finally; lock released in withLock's finally. |
| `init-db.mjs` | DuckDB | `Database.create(DB_PATH)` → DDL loop | WIRED | Fully substantive DDL executed against real DB handle; DB closed in finally. |
| `db-write.mjs render-markdown` | `data/loans.md` + `data/scenarios.md` | `writeFileSync(LOANS_MD/SCENARIOS_MD, content)` | WIRED | Paths derived from MORTGAGE_OPS root, not env-var-overridable (D-04-07). |
| `test_parallel_invocation.py` | `db-write.mjs insert-loan` | `subprocess.Popen` + `wait(timeout=60)` | WIRED | Two concurrent Popen calls; serialization verified by row count. |
| `test_stale_lockfile_recovery.py` | `lockfile.mjs::isStale()` | preflight `node --input-type=module -e` | WIRED | Preflight check verifies isStale agrees lock is stale before writer runs. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cmdRenderMarkdown` in db-write.mjs | `rows` (loans) | `db.all(SELECT ... FROM loans ORDER BY id ASC)` | Yes — queries live DuckDB loans table, CAST AS VARCHAR for DECIMAL columns | FLOWING |
| `cmdRenderMarkdown` in db-write.mjs | `rows` (scenarios) | `db.all(SELECT ... FROM scenarios ORDER BY id ASC)` | Yes — queries live DuckDB scenarios table, strftime for timestamp | FLOWING |
| `cmdInsertLoan` | `rows[0].id` | `INSERT ... RETURNING id` via DuckDB | Yes — real INSERT with RETURNING | FLOWING |
| `known-loans.yml` | YAML products array | Static Reference Layer file (committed) | Yes — 7 real product entries | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `init-db.mjs` run 1 exits cleanly | `MORTGAGE_OPS_DB_PATH=/tmp/v.duckdb node orchestration/init-db.mjs` | "init-db: schema ready", exit 0 | PASS |
| `init-db.mjs` run 2 (idempotency) exits cleanly | Same command again | "init-db: schema ready", exit 0 (no duplicate CREATE errors) | PASS |
| All 28 orchestration tests pass | `uv run pytest tests/test_orchestration/ -v` | 28 passed in 19.33s | PASS |
| Full suite 549+4+1 maintained | `uv run pytest --timeout=120 -q` | 549 passed, 4 skipped, 1 xfailed | PASS |
| `node --check` on all .mjs files | `node --check orchestration/lockfile.mjs init-db.mjs db-write.mjs` | No errors | PASS |
| `ruff check` on orchestration + tests | `uv run ruff check orchestration/ tests/test_orchestration/` | "All checks passed!" | PASS |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|---------|
| PERS-01 | `data/mortgage-ops.duckdb` schema: loans, scenarios, reports, payments, applicants, properties | SATISFIED | `init-db.mjs` DDL creates all 6 tables + schema_version. `test_init_db_creates_all_expected_tables` asserts all 7 names via `information_schema.tables`. |
| PERS-02 | `orchestration/init-db.mjs` idempotent schema initialization | SATISFIED | All DDL uses `IF NOT EXISTS`; `INSERT INTO schema_version ... ON CONFLICT DO NOTHING`. `test_init_db_idempotent_across_runs` verifies SHA256 schema fingerprint matches across two runs. |
| PERS-03 | `orchestration/db-write.mjs` central writer with subcommands: insert-loan, insert-scenario, insert-report, render-markdown, query | SATISFIED | All 5 subcommands present in HANDLERS map. `test_db_lifecycle.py` round-trip tests cover insert-loan, insert-scenario, insert-report. |
| PERS-04 | `orchestration/lockfile.mjs` provides `withLock()` wrapper, stale recovery at 60s | SATISFIED | `withLock`, `acquireLock`, `releaseLock`, `isStale`, `readLock` all exported. `STALE_THRESHOLD_MS = 60_000`. 7 unit tests in `test_lockfile_unit.py` + stale-recovery integration tests all pass. |
| PERS-05 | All writes wrapped in `withLock()` per career-ops pattern | SATISFIED | `WRITE_COMMANDS` set gates lock acquisition; `query` subcommand bypasses (read-only). `test_parallel_inserts_serialize_via_lockfile` proves serialization under concurrency. |
| PERS-06 | Markdown views (`data/loans.md`, `data/scenarios.md`) regenerated from DB, never edited by hand | SATISFIED | Files are gitignored (`data/loans.md`, `data/scenarios.md`). Render subcommand generates from DB with byte-identical guarantee. Two test files verify this property. |
| PERS-07 | `data/known-loans.yml` catalog: 30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1, FHA 30yr, VA 30yr, jumbo | SATISFIED | All 7 required product IDs present. `test_known_loans_catalog_complete` passes, validating YAML parse, Reference Layer keys, required IDs, 9-key per-entry schema, Decimal-string discipline, and valid `loan_type` Literals. |

All 7 PERS-XX requirements SATISFIED.

---

### Anti-Patterns Found

None. Scan of orchestration/ and tests/test_orchestration/ found no TODOs, FIXMEs, placeholder returns, or stub implementations. All subcommand handlers contain real SQL logic with transactions. No AI attribution found in any Phase 9 files.

---

### Cross-Cutting Checks

| Check | Result |
|-------|--------|
| No AI attribution (Co-Authored-By, Claude, Anthropic) in Phase 9 files | CLEAN — grep across orchestration/, tests/test_orchestration/, data/known-loans.yml returned no matches |
| `node --check` on all .mjs files | PASS (lockfile.mjs, init-db.mjs, db-write.mjs all pass) |
| `ruff check` on orchestration/ + tests/test_orchestration/ | PASS — "All checks passed!" |
| `mypy --strict lib/` | PASS — no errors (mypy does not process .mjs files; Node files pass `node --check`) |
| Decimal-from-string discipline | PRESERVED — `cmdInsertLoan` validates `principal` and `annual_rate` are strings before insert; render uses CAST AS VARCHAR; `known-loans.yml` uses quoted string values; `test_decimal_string_round_trip_preserves_cents` passes |
| Inherited Phase 5 ARM oracle xfail | ACKNOWLEDGED as out-of-scope — `test_oracle_cross_validation_5_1` xfail is pre-existing from Phase 5 ARM deferral; not a Phase 9 gap |
| Full suite pass count | 549 passed + 4 skipped + 1 xfailed — matches claimed count exactly |
| `pytest-timeout>=2.3` in pyproject.toml | PRESENT |

---

### Human Verification Required

None. All success criteria are fully verifiable programmatically and have been verified.

---

## Gaps Summary

No gaps found. All 5 ROADMAP Success Criteria are satisfied, all 7 PERS-XX requirements are closed at the test + implementation layers, and the full suite remains at 549 passed + 4 skipped + 1 xfailed (the Phase 5 ARM oracle deferral outside Phase 9 scope).

---

_Verified: 2026-05-04_
_Verifier: Claude (gsd-verifier)_
