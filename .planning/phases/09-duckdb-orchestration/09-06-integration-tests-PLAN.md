---
phase: 09
plan: 06
type: execute
wave: 6
depends_on:
  - "09-00"
  - "09-01"
  - "09-02"
  - "09-03"
  - "09-04"
  - "09-05"
files_modified:
  - tests/test_orchestration/test_db_lifecycle.py
  - tests/test_orchestration/test_lockfile.py
  - tests/test_orchestration/test_init_db_idempotent.py
  - tests/test_orchestration/test_parallel_invocation.py
  - tests/test_orchestration/test_stale_lockfile_recovery.py
  - tests/test_orchestration/test_render_markdown_byte_identical.py
must_haves:
  truths:
    - "test_db_lifecycle.py::test_init_db_idempotent xfail flips to passing (PERS-01 + PERS-02 + ROADMAP SC-1 closure — revision 2026-05-04: PERS-01 added per checker Blocker #1; the test_init_db_creates_all_expected_tables companion in test_init_db_idempotent.py asserts the 6-table schema PERS-01 mandates)"
    - "test_init_db_idempotent.py::test_init_db_creates_all_expected_tables verifies PERS-01 (6-table schema: loans, scenarios, reports, payments, applicants, properties; revision 2026-05-04: PERS-01 closure traceability added per Blocker #1)"
    - "test_db_lifecycle.py::test_concurrent_writes_serialize xfail flips to passing (PERS-05 + ROADMAP SC-2 closure)"
    - "test_lockfile.py::test_stale_lockfile_reclaimed_after_60s xfail flips to passing (PERS-04 + ROADMAP SC-3 closure)"
    - "tests/test_orchestration/test_init_db_idempotent.py end-to-end test exists (invokes node init-db.mjs twice, asserts schema unchanged via SHA256 of pragma_table_info dumps)"
    - "tests/test_orchestration/test_parallel_invocation.py end-to-end test exists (subprocess.Popen two `node db-write.mjs insert-loan` simultaneously; asserts both exit 0 OR exactly-one fails fast with lock-timeout error; final SELECT count = baseline + 2; lockfile released)"
    - "tests/test_orchestration/test_stale_lockfile_recovery.py end-to-end test exists (pre-creates data/.mortgage-ops.duckdb.lock with mtime=now-65s, invokes db-write, asserts success and lock released)"
    - "tests/test_orchestration/test_render_markdown_byte_identical.py end-to-end test exists (full pipeline: init -> insert 2 loans -> render twice -> hashlib.sha256 compare; supplements Wave-4 unit-level coverage with end-to-end pinning of SC-4)"
    - "All Phase 9 tests pass: pytest tests/test_orchestration/ -v shows 0 xfailed, 0 failed; mypy + ruff clean"
    - "ROADMAP SC-1, SC-2, SC-3, SC-4 all pinned by passing integration tests (SC-5 was pinned in Wave 5)"
  artifacts:
    - path: "tests/test_orchestration/test_init_db_idempotent.py"
      provides: "PERS-02 + ROADMAP SC-1 end-to-end: idempotent schema initialization across consecutive invocations"
      contains: "def test_init_db_idempotent_across_runs"
    - path: "tests/test_orchestration/test_parallel_invocation.py"
      provides: "PERS-05 + ROADMAP SC-2 end-to-end: two simultaneous writers serialize via withLock; no corruption"
      contains: "def test_parallel_inserts_serialize_via_lockfile"
    - path: "tests/test_orchestration/test_stale_lockfile_recovery.py"
      provides: "PERS-04 + ROADMAP SC-3 end-to-end: 60s+ old lockfile is reclaimed by next writer"
      contains: "def test_stale_lockfile_reclaimed_after_60s_threshold"
    - path: "tests/test_orchestration/test_render_markdown_byte_identical.py"
      provides: "ROADMAP SC-4 end-to-end byte-identical regeneration (supplements Wave-4 unit test)"
      contains: "def test_render_markdown_byte_identical_end_to_end"
  key_links:
    - from: "tests/test_orchestration/test_parallel_invocation.py"
      to: "orchestration/db-write.mjs + orchestration/lockfile.mjs"
      via: "subprocess.Popen(['node', 'orchestration/db-write.mjs', 'insert-loan', '--json', ...])"
      pattern: "subprocess\\.Popen.*db-write\\.mjs.*insert-loan"
    - from: "tests/test_orchestration/test_stale_lockfile_recovery.py"
      to: "data/.mortgage-ops.duckdb.lock"
      via: "os.utime(lock_path, (mtime, mtime)) where mtime = time.time() - 65"
      pattern: "os\\.utime.*\\.lock"
    - from: "tests/test_orchestration/test_render_markdown_byte_identical.py"
      to: "data/loans.md, data/scenarios.md"
      via: "hashlib.sha256(file.read_bytes()).hexdigest() x2 -> assert equal"
      pattern: "hashlib\\.sha256"
autonomous: true
requirements:
  - PERS-01
  - PERS-02
  - PERS-04
  - PERS-05
  - PERS-06
tags:
  - phase-09
  - duckdb-orchestration
  - integration-tests
  - concurrency
  - pers-01
  - pers-02
  - pers-04
  - pers-05
  - pers-06
---

<objective>
**Goal:** Ship the four end-to-end integration tests that pin Phase 9's load-bearing concurrency + idempotency + byte-equality contracts, AND flip the three remaining Wave 0 xfail stubs (`test_init_db_idempotent`, `test_concurrent_writes_serialize`, `test_stale_lockfile_reclaimed_after_60s`). After this plan ships, ROADMAP SC-1, SC-2, SC-3, SC-4 are all pinned by passing tests (SC-5 was pinned in Wave 5; SC-4 was unit-pinned in Wave 4 and is now also end-to-end pinned).

**Purpose:** PERS-02 + PERS-04 + PERS-05 closure. The Wave 0 stubs reserve the test names; Waves 1-4 ship the orchestration code; this wave is the contract enforcement layer. Without these tests, the lockfile race window (Pitfall 2), stale-lock-recovery (60s threshold), and idempotent-init (`CREATE TABLE IF NOT EXISTS`) guarantees would be hand-eyeballed instead of regression-pinned. The parallel-invocation test in particular is the only guard against the lockfile race window degrading silently under future refactors.

**Output:** 4 new test files under `tests/test_orchestration/` (~400 lines total); 3 Wave 0 xfail decorators removed (3 stubs flip to passing); pass count delta +3 from xfail-flips + 4 net new tests = +7 minimum (assuming each new test contributes at least one passing assertion); xfail count drops to 0.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/09-duckdb-orchestration/09-PATTERNS.md
@.planning/phases/09-duckdb-orchestration/09-RESEARCH.md
@CLAUDE.md
@DATA_CONTRACT.md
@orchestration/init-db.mjs
@orchestration/db-write.mjs
@orchestration/lockfile.mjs
@tests/conftest.py
@tests/test_orchestration/test_db_lifecycle.py
@tests/test_orchestration/test_lockfile.py

<interfaces>
**Wave 0 stubs being flipped (NAMES PINNED — DO NOT RENAME per Wave 0 D-00 Rule-1):**

| Stub Path | Closes | SC |
|-----------|--------|-----|
| `tests/test_orchestration/test_db_lifecycle.py::test_init_db_idempotent` | PERS-02 | SC-1 |
| `tests/test_orchestration/test_db_lifecycle.py::test_concurrent_writes_serialize` | PERS-05 | SC-2 |
| `tests/test_orchestration/test_lockfile.py::test_stale_lockfile_reclaimed_after_60s` | PERS-04 | SC-3 |

**Note on Wave 4 SC-4 coverage:** Plan 09-04 already flipped `tests/test_orchestration/test_render_markdown.py::test_render_markdown_byte_identical` (unit-style: render twice, byte-compare). This plan ADDS an end-to-end variant `test_render_markdown_byte_identical.py::test_render_markdown_byte_identical_end_to_end` that runs the full init -> insert -> render -> byte-compare pipeline; both tests coexist as belt-and-suspenders.

**conftest helper (already shipped Wave 0):**
```python
def node_orchestration_run(
    *args: str,
    db_path: Path | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Shells out to `node` from REPO_ROOT; sets MORTGAGE_OPS_DB_PATH env var
    if db_path provided. Returns CompletedProcess (stdout/stderr captured)."""
```

Import via: `from tests.conftest import node_orchestration_run, REPO_ROOT`.

**pytest-timeout dependency (revision 2026-05-04 per Warning #4 + D-06-09):**
Tests in this plan use `@pytest.mark.timeout(N)` markers; the `pytest-timeout`
package must be available in the dev dependency set. If `pytest -m timeout`
collect-only reports "marker not found", add `pytest-timeout` to
`pyproject.toml`'s dev dependency list before running the suite. The marker
is a hung-process safety net layered on top of the explicit `subprocess.run`
/ `subprocess.Popen` `timeout=` kwargs.

**For Popen-based parallelism (test_parallel_invocation.py): build the command list manually rather than going through node_orchestration_run (which uses subprocess.run, blocking). Pattern:**
```python
import subprocess
from tests.conftest import REPO_ROOT

def _spawn_insert(fixture_path: Path, db_path: Path) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env["MORTGAGE_OPS_DB_PATH"] = str(db_path)
    return subprocess.Popen(
        ["node", "orchestration/db-write.mjs", "insert-loan",
         "--json", str(fixture_path)],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
```

**Lockfile path (D-01 lockfile-PLAN inheritance):** `data/.mortgage-ops.duckdb.lock` (when DB_PATH is the default); for tmp_path-isolated tests, the lockfile is `<dirname(db_path)>/.<basename(db_path)>.lock`. Verify the actual sibling-path convention from `orchestration/lockfile.mjs` before writing tests.

**Stale-lockfile JSON shape (RESEARCH lines 604-608):**
```json
{
  "pid": <integer>,
  "acquired_at": <unix_ms>,
  "reason": <string>
}
```

**Stale threshold:** 60 seconds (D-02 lockfile-PLAN inheritance; RESEARCH line 17, line 584). Test uses 65s margin to avoid clock-skew flakes.

**Render determinism contract (D-03 inheritance from Plan 09-04):**
- Explicit `ORDER BY id ASC` in SELECTs
- No `generated_at` timestamp embedded in markdown body
- Mandatory `<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->` header at line 1
- Wave-4 D-04-01 through D-04-07 all carry forward

**Test fixture loan shapes (RESEARCH precedent + Wave 3 schema):**
```json
{"principal":"200000.00","apr":"0.0650","term_months":360,"origination_date":"2026-05-01","loan_type":"fixed"}
```
(Note RESEARCH uses `apr` field naming; verify Plan 09-03 dispatcher accepts `annual_rate` vs `apr` — match what Plan 09-03's cmdInsertLoan expects. If 09-03 ships with `annual_rate`, use that.)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write tests/test_orchestration/test_init_db_idempotent.py (SC-1 end-to-end)</name>
  <files>tests/test_orchestration/test_init_db_idempotent.py</files>
  <read_first>
    - orchestration/init-db.mjs (the schema bootstrapper from Plan 09-02)
    - tests/conftest.py (node_orchestration_run helper)
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md §"Pinned schema DDL" + §Pattern 1 (`CREATE TABLE IF NOT EXISTS`)
    - tests/test_orchestration/test_db_lifecycle.py (the Wave 0 stub for test_init_db_idempotent)
  </read_first>
  <action>
    Write a NEW file `tests/test_orchestration/test_init_db_idempotent.py` that pins ROADMAP SC-1 ("`node orchestration/init-db.mjs` is idempotent") via end-to-end invocation + schema-fingerprint comparison.

    **Strategy:** invoke `init-db.mjs` twice against the same tmp_path-isolated DuckDB file; SELECT each table's column metadata via `pragma_table_info('<table>')` ordered by cid; SHA256-hash the concatenated dump; assert the two hashes are identical.

    Why fingerprinting over `==` of raw rows: pragma_table_info row order may shift across DuckDB minor versions, but the concatenated-then-hashed dump is robust to that as long as the underlying schema is unchanged.

    File content:

    ```python
    """Phase 9 init-db.mjs idempotency end-to-end test (PERS-02 + ROADMAP SC-1).

    SC-1: `node orchestration/init-db.mjs` is idempotent. Running it twice
    against the same DB file produces an identical schema (no DROP, no
    duplicate CREATE error, no schema drift).

    Test strategy: invoke init twice; SHA256-hash a deterministic dump of
    pragma_table_info() for every table; assert the two hashes match.
    """

    from __future__ import annotations

    import hashlib
    import json
    from pathlib import Path

    from tests.conftest import node_orchestration_run

    # Tables defined by Plan 09-02 init-db.mjs (RESEARCH §"Pinned schema DDL").
    # Add to this list if Plan 09-02 ships additional tables.
    EXPECTED_TABLES: tuple[str, ...] = (
        "loans",
        "scenarios",
        "reports",
        "payments",
        "applicants",
        "properties",
    )


    def _schema_fingerprint(db_path: Path) -> str:
        """Compute a deterministic SHA256 of the full schema by querying
        pragma_table_info for every table and SHA256-hashing the JSON dump."""
        dump_parts: list[str] = []
        for table in EXPECTED_TABLES:
            result = node_orchestration_run(
                "orchestration/db-write.mjs",
                "query",
                "--sql",
                f"SELECT cid, name, type, \"notnull\", dflt_value, pk "
                f"FROM pragma_table_info('{table}') ORDER BY cid ASC",
                db_path=db_path,
            )
            assert result.returncode == 0, (
                f"pragma_table_info({table}) failed: {result.stderr}"
            )
            # The query subcommand emits JSON to stdout (per Plan 09-03).
            rows = json.loads(result.stdout)
            dump_parts.append(f"{table}:{json.dumps(rows, sort_keys=True)}")

        dump = "\n".join(dump_parts).encode("utf-8")
        return hashlib.sha256(dump).hexdigest()


    def test_init_db_idempotent_across_runs(tmp_path: Path) -> None:
        """PERS-02 + ROADMAP SC-1: two consecutive invocations of
        `node orchestration/init-db.mjs` produce a byte-identical schema
        fingerprint. The CREATE TABLE IF NOT EXISTS pattern (RESEARCH §Pattern 1)
        is the load-bearing mechanism."""
        db_path = tmp_path / "test_idempotent.duckdb"

        # First init: builds the schema from scratch
        run1 = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert run1.returncode == 0, f"init run 1 failed: {run1.stderr}"
        assert db_path.exists(), f"DB file not created at {db_path}"

        fingerprint_1 = _schema_fingerprint(db_path)

        # Second init: must NOT drop or recreate; CREATE IF NOT EXISTS is no-op
        run2 = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert run2.returncode == 0, (
            f"init run 2 (idempotency) failed: {run2.stderr}\n"
            f"This is the SC-1 violation: init is NOT idempotent. Likely cause: "
            f"missing IF NOT EXISTS on a CREATE TABLE statement (RESEARCH Pattern 1)."
        )

        fingerprint_2 = _schema_fingerprint(db_path)

        assert fingerprint_1 == fingerprint_2, (
            f"PERS-02 + SC-1 violation: schema fingerprint drifted between "
            f"consecutive init runs.\n"
            f"  Run 1 SHA256: {fingerprint_1}\n"
            f"  Run 2 SHA256: {fingerprint_2}\n"
            f"Likely cause: a CREATE TABLE without IF NOT EXISTS, or an ALTER "
            f"that runs unconditionally."
        )


    def test_init_db_creates_all_expected_tables(tmp_path: Path) -> None:
        """Companion guard: SC-1 idempotency is meaningless if init silently
        skips creating a required table. Verify all 6 PERS-01 tables exist
        after a single init."""
        db_path = tmp_path / "test_tables.duckdb"

        run1 = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert run1.returncode == 0, f"init failed: {run1.stderr}"

        # Query for table existence via information_schema
        result = node_orchestration_run(
            "orchestration/db-write.mjs",
            "query",
            "--sql",
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name",
            db_path=db_path,
        )
        assert result.returncode == 0, f"information_schema query failed: {result.stderr}"
        rows = json.loads(result.stdout)
        actual_tables = {r["table_name"] for r in rows}

        missing = set(EXPECTED_TABLES) - actual_tables
        assert not missing, (
            f"PERS-01 violation: init-db.mjs failed to create tables: "
            f"{sorted(missing)}; have: {sorted(actual_tables)}"
        )
    ```

    **Failure mode pre-check:** If Plan 09-02 ships with fewer than 6 tables (e.g., only loans/scenarios/reports), update `EXPECTED_TABLES` to match what 09-02 actually delivers. The DDL in RESEARCH §"Pinned schema DDL" lists 6 tables; cross-reference Plan 09-02's `must_haves` before writing.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_init_db_idempotent.py -v --tb=short 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_orchestration/test_init_db_idempotent.py` exits 0
    - `pytest tests/test_orchestration/test_init_db_idempotent.py -v 2>&1 | grep -c PASSED` returns at least 2 (idempotent + creates_all_tables)
    - `pytest tests/test_orchestration/test_init_db_idempotent.py -v 2>&1 | grep -c FAILED` returns 0
    - `grep -c "hashlib.sha256" tests/test_orchestration/test_init_db_idempotent.py` returns at least 1
    - `grep -c "_schema_fingerprint" tests/test_orchestration/test_init_db_idempotent.py` returns at least 3
    - `grep -c "EXPECTED_TABLES" tests/test_orchestration/test_init_db_idempotent.py` returns at least 3
    - `grep -c "from tests.conftest import node_orchestration_run" tests/test_orchestration/test_init_db_idempotent.py` returns 1
    - `mypy --strict tests/test_orchestration/test_init_db_idempotent.py` exits 0
    - `ruff check tests/test_orchestration/test_init_db_idempotent.py` exits 0
  </acceptance_criteria>
  <done>
    SC-1 pinned by deterministic schema-fingerprint test; PERS-02 closed at the integration layer.
  </done>
</task>

<task type="auto">
  <name>Task 2: Write tests/test_orchestration/test_parallel_invocation.py (SC-2 end-to-end)</name>
  <files>tests/test_orchestration/test_parallel_invocation.py</files>
  <read_first>
    - orchestration/db-write.mjs (Wave 3 cmdInsertLoan + Wave 1 withLock wrapper)
    - orchestration/lockfile.mjs (Wave 1 acquireLock/releaseLock contract)
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md §"Parallel-Invocation Test (SC-2)" lines 507-580 (test design + race-window note)
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md §"Pitfall 2: Lockfile Race Window" lines 648-665 (acceptance criteria — final state matters, not which process wins)
  </read_first>
  <action>
    Write a NEW file `tests/test_orchestration/test_parallel_invocation.py` lifted from RESEARCH §"Parallel-Invocation Test (SC-2)" lines 511-578, adapted to use `tests.conftest.REPO_ROOT` and `MORTGAGE_OPS_DB_PATH` env-var isolation.

    **Critical design rule (RESEARCH line 580 + Pitfall 2):** assertion is on the FINAL STATE (count == baseline + 2; lockfile released), NOT on which process won the race. Tolerate either "both succeed" or "exactly-one fails-fast with lock-timeout error" outcomes — both are valid per career-ops design.

    File content:

    ```python
    """Phase 9 parallel-writer concurrency test (PERS-05 + ROADMAP SC-2).

    SC-2: `node orchestration/db-write.mjs --insert-loan --json fixtures/loan.json`
    writes through withLock() and a concurrent second invocation either waits
    or fails fast (no DB corruption).

    Test strategy: spawn two `subprocess.Popen` calls back-to-back; wait for
    both; assert (a) the lockfile race did not corrupt the DB (final SELECT
    count = baseline + 2 with both inserts persisted), (b) the lockfile is
    released after both processes complete (no leak).

    Race window per RESEARCH Pitfall 2: the read-then-write lockfile pattern
    has a small race window. Either outcome is valid: both succeed (typical
    case — DuckDB's OS file lock is the second line of defense), or one fails
    fast with a lock-timeout error and exits non-zero. The test tolerates
    both as long as the FINAL STATE is correct.
    """

    from __future__ import annotations

    import json
    import os
    import subprocess
    from pathlib import Path

    import pytest

    from tests.conftest import REPO_ROOT, node_orchestration_run


    def _spawn_insert(fixture_path: Path, db_path: Path) -> subprocess.Popen[bytes]:
        """Spawn a non-blocking `node db-write.mjs insert-loan` process."""
        env = os.environ.copy()
        env["MORTGAGE_OPS_DB_PATH"] = str(db_path)
        return subprocess.Popen(
            [
                "node",
                "orchestration/db-write.mjs",
                "insert-loan",
                "--json",
                str(fixture_path),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


    def _lockfile_for(db_path: Path) -> Path:
        """Lockfile sibling-path convention from Plan 09-01 lockfile.mjs:
        the lockfile lives in the same directory as the DB, named
        `.<dbname>.lock`."""
        return db_path.parent / f".{db_path.name}.lock"


    def _count_loans(db_path: Path) -> int:
        result = node_orchestration_run(
            "orchestration/db-write.mjs",
            "query",
            "--sql",
            "SELECT count(*) AS n FROM loans",
            db_path=db_path,
        )
        assert result.returncode == 0, f"count query failed: {result.stderr}"
        rows = json.loads(result.stdout)
        return int(rows[0]["n"])


    @pytest.mark.timeout(90)  # Warning #4 / D-06-09: 1.5x subprocess wait(timeout=60); pytest-timeout safety net
    def test_parallel_inserts_serialize_via_lockfile(tmp_path: Path) -> None:
        """PERS-05 + ROADMAP SC-2: two parallel `node db-write.mjs insert-loan`
        invocations either both succeed (one waits) or exactly one fails fast
        with a lock-timeout error. Either way, the DB is not corrupted: final
        loan count equals baseline + (number of successful inserts), and the
        lockfile is released after the dust settles."""
        db_path = tmp_path / "test_parallel.duckdb"

        # 1. Pre-init the DB
        init = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert init.returncode == 0, f"init failed: {init.stderr}"

        baseline = _count_loans(db_path)

        # 2. Two distinct fixture loans (different principals so we can verify both landed)
        fx_a = tmp_path / "loan_a.json"
        fx_b = tmp_path / "loan_b.json"
        fx_a.write_text(
            json.dumps(
                {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                    "loan_type": "fixed",
                }
            )
        )
        fx_b.write_text(
            json.dumps(
                {
                    "principal": "300000.00",
                    "annual_rate": "0.067500",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                    "loan_type": "fixed",
                }
            )
        )

        # 3. Spawn both simultaneously
        p1 = _spawn_insert(fx_a, db_path)
        p2 = _spawn_insert(fx_b, db_path)
        rc1 = p1.wait(timeout=60)
        rc2 = p2.wait(timeout=60)

        stderr_1 = p1.stderr.read().decode() if p1.stderr else ""
        stderr_2 = p2.stderr.read().decode() if p2.stderr else ""

        # 4. Outcome classification (per RESEARCH line 580 + Pitfall 2):
        # Acceptable outcomes: (a) both succeed; (b) exactly one fails fast with
        # a lock-timeout-shaped error message. NOT acceptable: any DB corruption
        # error, both fail, or one succeeds + one hangs forever.
        successes = [rc for rc in (rc1, rc2) if rc == 0]
        failures = [(rc, stderr) for rc, stderr in [(rc1, stderr_1), (rc2, stderr_2)] if rc != 0]

        assert len(successes) >= 1, (
            f"At least one writer must succeed.\n"
            f"  rc1={rc1} stderr={stderr_1}\n"
            f"  rc2={rc2} stderr={stderr_2}"
        )

        # If any failed, the failure must be a lock-timeout shape, not a
        # DB-corruption shape. Lock-timeout error messages contain "lock" or
        # "LOCK" or "timeout"; DuckDB corruption errors mention "IO Error" or
        # "Catalog Error" without "lock" context.
        for rc, stderr in failures:
            stderr_lower = stderr.lower()
            assert "lock" in stderr_lower or "timeout" in stderr_lower or "busy" in stderr_lower, (
                f"A writer failed with a non-lock-related error (suggests DB corruption "
                f"rather than lock contention): rc={rc} stderr={stderr}"
            )

        # 5. Atomicity: final count = baseline + (successful inserts). Each
        # successful insert added exactly one row.
        final = _count_loans(db_path)
        expected = baseline + len(successes)
        assert final == expected, (
            f"PERS-05 violation: insert atomicity broken. "
            f"baseline={baseline} successes={len(successes)} expected={expected} final={final}"
        )

        # 6. Lockfile released (no leak). RESEARCH line 577.
        lockfile = _lockfile_for(db_path)
        assert not lockfile.exists(), (
            f"Lockfile leaked: {lockfile} still exists after both writers exited. "
            f"Indicates releaseLock was skipped (likely a finally-block bug in lockfile.mjs)."
        )
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_parallel_invocation.py -v --tb=short 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_orchestration/test_parallel_invocation.py` exits 0
    - `pytest tests/test_orchestration/test_parallel_invocation.py -v 2>&1 | grep -c PASSED` returns at least 1
    - `pytest tests/test_orchestration/test_parallel_invocation.py -v 2>&1 | grep -c FAILED` returns 0
    - `grep -c "subprocess.Popen" tests/test_orchestration/test_parallel_invocation.py` returns at least 1
    - `grep -c "_spawn_insert" tests/test_orchestration/test_parallel_invocation.py` returns at least 3
    - `grep -c "MORTGAGE_OPS_DB_PATH" tests/test_orchestration/test_parallel_invocation.py` returns 1
    - `grep -c "lockfile.exists" tests/test_orchestration/test_parallel_invocation.py` returns 1
    - `grep -c "@pytest.mark.timeout" tests/test_orchestration/test_parallel_invocation.py` returns 1 (Warning #4 / D-06-09: hung-process safety net)
    - `mypy --strict tests/test_orchestration/test_parallel_invocation.py` exits 0
    - `ruff check tests/test_orchestration/test_parallel_invocation.py` exits 0
  </acceptance_criteria>
  <done>
    SC-2 pinned end-to-end; PERS-05 closed; lockfile race-window discipline regression-protected.
  </done>
</task>

<task type="auto">
  <name>Task 3: Write tests/test_orchestration/test_stale_lockfile_recovery.py (SC-3 end-to-end)</name>
  <files>tests/test_orchestration/test_stale_lockfile_recovery.py</files>
  <read_first>
    - orchestration/lockfile.mjs (Wave 1 stale-detection logic; verify 60s threshold)
    - orchestration/db-write.mjs (insert-loan path that exercises withLock)
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md §"Stale-Lockfile-Recovery Test (SC-3)" lines 582-628
  </read_first>
  <action>
    Write a NEW file `tests/test_orchestration/test_stale_lockfile_recovery.py` lifted from RESEARCH §"Stale-Lockfile-Recovery Test (SC-3)" lines 586-628, adapted to use the conftest helper + tmp_path-isolated DB.

    File content:

    ```python
    """Phase 9 stale-lockfile recovery test (PERS-04 + ROADMAP SC-3).

    SC-3: stale lockfile recovery triggers at 60s. The test pre-creates a
    lockfile with mtime = now - 65s (5s margin past the 60s threshold to
    avoid clock-skew flakes), then invokes db-write.mjs and asserts the
    write succeeds (the writer reclaimed the stale lock).

    Per Plan 09-01 D-02: stale threshold = 60s (RESEARCH line 17, line 584).
    Per Plan 09-01 D-01: lockfile state lives in JSON shape with `pid`,
    `acquired_at` (unix ms), `reason`. Some implementations key off the JSON
    `acquired_at` field; others key off file mtime. Belt-and-suspenders, the
    test sets BOTH to 65s ago.
    """

    from __future__ import annotations

    import json
    import os
    import subprocess
    import time
    from pathlib import Path

    import pytest

    from tests.conftest import REPO_ROOT, node_orchestration_run

    # Stale threshold per Plan 09-01 D-02 / RESEARCH line 17 + 584
    STALE_THRESHOLD_SECONDS: int = 60
    # Margin past threshold to avoid clock-skew flakes (RESEARCH line 602: 65s)
    STALE_AGE_SECONDS: int = 65


    def _lockfile_for(db_path: Path) -> Path:
        """Lockfile sibling-path convention (Plan 09-01)."""
        return db_path.parent / f".{db_path.name}.lock"


    @pytest.mark.timeout(60)  # Warning #4 / D-06-09: 1.5x worst-case (30s db-write + 10s pre-flight + margin)
    def test_stale_lockfile_reclaimed_after_60s_threshold(tmp_path: Path) -> None:
        """PERS-04 + ROADMAP SC-3: a pre-existing lockfile with mtime > 60s
        is reclaimed by a fresh db-write.mjs invocation; the write proceeds
        normally and the lockfile is released after."""
        db_path = tmp_path / "test_stale.duckdb"
        lock = _lockfile_for(db_path)

        # 1. Pre-init the DB so insert-loan has a target schema
        init = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert init.returncode == 0, f"init failed: {init.stderr}"

        # 2. Pre-create a stale lockfile. Per Plan 09-01 D-01-02, the
        # LOAD-BEARING aging mechanism is the JSON `acquired_at` field
        # (Date.now() in milliseconds), NOT the file mtime. Without this
        # field aged in the JSON content, lockfile.mjs::isStale() returns
        # false and the new writer waits the full 30s acquireLock timeout
        # before erroring out — silently failing the test against a hung
        # process. (Revision 2026-05-04 per checker Blocker #3 fix-hint:
        # explicit LOAD-BEARING comment + pre-flight isStale check below.)
        stale_acquired_at_ms = int((time.time() - STALE_AGE_SECONDS) * 1000)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(
            json.dumps(
                {
                    "pid": 99999,  # bogus PID — process does not exist
                    "acquired_at": stale_acquired_at_ms,  # LOAD-BEARING per D-01-02
                    "reason": "stale-test-fixture",
                },
                indent=2,
            )
        )

        # 3. Belt-and-suspenders: also set the file's mtime to 65s ago. This
        # is NOT the load-bearing aging mechanism (per Plan 09-01 D-01-02 the
        # JSON acquired_at field is); kept only because some future
        # implementation MIGHT cross-check mtime as a defense-in-depth signal.
        sixty_five_s_ago = time.time() - STALE_AGE_SECONDS
        os.utime(lock, (sixty_five_s_ago, sixty_five_s_ago))

        # Sanity: lockfile is in place before the writer runs
        assert lock.exists(), f"failed to pre-create stale lockfile at {lock}"

        # 3a. PRE-FLIGHT (revision 2026-05-04 per Blocker #3): assert that
        # lockfile.mjs::isStale() agrees the fixture is stale BEFORE we hand
        # it to the writer. If isStale() returns false, the test would hang
        # for ~30s on the acquireLock timeout and fail with a confusing
        # error; we want a fast, specific failure pointing at the seam.
        # The Node one-liner uses --input-type=module to allow top-level
        # await + ESM import. Exit code 0 if stale; 1 otherwise.
        preflight = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                (
                    "import {isStale, readLock} from './orchestration/lockfile.mjs';"
                    "process.exit(isStale(readLock()) ? 0 : 1);"
                ),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert preflight.returncode == 0, (
            f"PRE-FLIGHT FAILURE (Blocker #3 seam): lockfile.mjs::isStale() "
            f"did NOT classify the fixture lock as stale.\n"
            f"  acquired_at_ms = {stale_acquired_at_ms}\n"
            f"  current Date.now() ms = {int(time.time() * 1000)}\n"
            f"  age_ms = {int(time.time() * 1000) - stale_acquired_at_ms}\n"
            f"  STALE_THRESHOLD_MS in lockfile.mjs = 60000\n"
            f"  preflight stderr = {preflight.stderr}\n"
            f"This means the fixture's JSON content is malformed OR the "
            f"lockfile path is wrong OR Plan 09-01 D-01-02 (acquired_at-based "
            f"stale check) has regressed to mtime-based. The downstream "
            f"db-write call would hang for 30s on acquireLock timeout — fix "
            f"the seam before retrying."
        )

        # 4. Run the writer — it should reclaim the stale lock and succeed
        fx = tmp_path / "loan.json"
        fx.write_text(
            json.dumps(
                {
                    "principal": "150000.00",
                    "annual_rate": "0.070000",
                    "term_months": 180,
                    "origination_date": "2026-05-01",
                    "loan_type": "fixed",
                }
            )
        )

        result = node_orchestration_run(
            "orchestration/db-write.mjs",
            "insert-loan",
            "--json",
            str(fx),
            db_path=db_path,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"PERS-04 + SC-3 violation: db-write failed to reclaim a {STALE_AGE_SECONDS}s-old "
            f"lockfile (threshold = {STALE_THRESHOLD_SECONDS}s). stderr={result.stderr}\n"
            f"Likely cause: lockfile.mjs stale-detection threshold is not 60s, OR the "
            f"detection logic checks neither JSON acquired_at nor file mtime correctly."
        )

        # 5. Lockfile released after the writer completes
        assert not lock.exists(), (
            f"Lockfile leaked after stale-recovery: {lock} still exists. "
            f"Indicates releaseLock was skipped after the reclaim."
        )


    @pytest.mark.timeout(30)  # Warning #4 / D-06-09: 2x subprocess timeout=15
    def test_fresh_lockfile_under_60s_blocks_or_waits(tmp_path: Path) -> None:
        """Negative companion: a FRESH lockfile (mtime < 60s) MUST NOT be
        reclaimed — it represents an active writer. The new writer must
        wait, fail-fast with a lock-busy error, or otherwise refuse to
        proceed within a short timeout window. This guards the SC-3 threshold
        from regressing to '0s' (which would silently break SC-2)."""
        db_path = tmp_path / "test_fresh.duckdb"
        lock = _lockfile_for(db_path)

        init = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert init.returncode == 0, f"init failed: {init.stderr}"

        # Pre-create a FRESH lockfile (acquired_at = 5s ago, well under 60s)
        fresh_ms = int((time.time() - 5) * 1000)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),  # use OUR pid — looks plausibly live
                    "acquired_at": fresh_ms,
                    "reason": "fresh-test-fixture",
                },
                indent=2,
            )
        )
        five_s_ago = time.time() - 5
        os.utime(lock, (five_s_ago, five_s_ago))

        fx = tmp_path / "loan.json"
        fx.write_text(
            json.dumps(
                {
                    "principal": "100000.00",
                    "annual_rate": "0.060000",
                    "term_months": 180,
                    "origination_date": "2026-05-01",
                    "loan_type": "fixed",
                }
            )
        )

        # Use a short timeout — the writer should either fail fast (lock busy)
        # or hit the timeout polling for the lock to release. Either way, the
        # exit code should be non-zero (because we never release the fresh lock).
        result = node_orchestration_run(
            "orchestration/db-write.mjs",
            "insert-loan",
            "--json",
            str(fx),
            db_path=db_path,
            timeout=15,
        )

        # The fresh lock must NOT be silently reclaimed (that would break SC-2).
        # Acceptable: writer fails fast (returncode != 0) OR writer times out.
        # NOT acceptable: writer succeeds (returncode == 0) — that proves the
        # threshold collapsed below 60s.
        assert result.returncode != 0, (
            f"PERS-04 violation: writer reclaimed a 5s-old lockfile — the "
            f"60s threshold has degraded. This silently breaks SC-2 (parallel "
            f"writers no longer serialize). stderr={result.stderr}"
        )

        # Cleanup — remove the fresh lockfile we planted (writer didn't release it
        # because it never owned it).
        if lock.exists():
            lock.unlink()
    ```

    **Note on the negative-companion test:** if Plan 09-01's lockfile.mjs uses a polling-with-timeout pattern, the fresh-lockfile test may take up to 15s to complete. That is intended. If lockfile.mjs uses a fail-fast pattern, the test completes in milliseconds. Both shapes are acceptable per Plan 09-01 D-XX (which the executor should cross-reference).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_stale_lockfile_recovery.py -v --tb=short 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_orchestration/test_stale_lockfile_recovery.py` exits 0
    - `pytest tests/test_orchestration/test_stale_lockfile_recovery.py -v 2>&1 | grep -c PASSED` returns at least 2 (stale-reclaimed + fresh-blocks)
    - `pytest tests/test_orchestration/test_stale_lockfile_recovery.py -v 2>&1 | grep -c FAILED` returns 0
    - `grep -c "STALE_THRESHOLD_SECONDS = 60" tests/test_orchestration/test_stale_lockfile_recovery.py` returns 1
    - `grep -c "STALE_AGE_SECONDS = 65" tests/test_orchestration/test_stale_lockfile_recovery.py` returns 1
    - `grep -c "os.utime" tests/test_orchestration/test_stale_lockfile_recovery.py` returns at least 2 (stale + fresh setups)
    - `grep -c "lock.exists" tests/test_orchestration/test_stale_lockfile_recovery.py` returns at least 2
    - `grep -c "@pytest.mark.timeout" tests/test_orchestration/test_stale_lockfile_recovery.py` returns 2 (Warning #4 / D-06-09: stale-reclaim + fresh-blocks each get a marker)
    - `grep -c "isStale(readLock())" tests/test_orchestration/test_stale_lockfile_recovery.py` returns 1 (Blocker #3 fix: pre-flight Node check asserts the fixture is classified stale BEFORE the db-write invocation; without this seam check the test would hang for 30s on acquireLock timeout)
    - `grep -c "PRE-FLIGHT FAILURE" tests/test_orchestration/test_stale_lockfile_recovery.py` returns 1 (the assertion message points at the Blocker #3 seam if it ever regresses)
    - `mypy --strict tests/test_orchestration/test_stale_lockfile_recovery.py` exits 0
    - `ruff check tests/test_orchestration/test_stale_lockfile_recovery.py` exits 0
  </acceptance_criteria>
  <done>
    SC-3 pinned end-to-end with positive (reclaim 65s-old) + negative (block 5s-old) companions; PERS-04 closed.
  </done>
</task>

<task type="auto">
  <name>Task 4: Write tests/test_orchestration/test_render_markdown_byte_identical.py (SC-4 end-to-end supplement)</name>
  <files>tests/test_orchestration/test_render_markdown_byte_identical.py</files>
  <read_first>
    - tests/test_orchestration/test_render_markdown.py (Wave-4-flipped unit-style byte-identical test — already passing)
    - orchestration/db-write.mjs (cmdRenderMarkdown + insert-loan from Wave 4 + Wave 3)
    - .planning/phases/09-duckdb-orchestration/09-04-render-markdown-PLAN.md (D-04-01 through D-04-07; SHA256-via-bytes pattern)
  </read_first>
  <action>
    Write a NEW file `tests/test_orchestration/test_render_markdown_byte_identical.py` that supplements Wave-4's `test_render_markdown.py::test_render_markdown_byte_identical` (which already passes) with an end-to-end pipeline test using `hashlib.sha256` of file bytes (more explicit than the byte-equality assertion in Wave 4).

    Why both tests coexist: Wave 4 unit test is the minimal byte-equality contract (`bytes_a == bytes_b`); this Wave 6 end-to-end test exercises the full init -> insert -> render -> render -> SHA256-compare pipeline AND adds explicit cleanup of `data/loans.md` + `data/scenarios.md` so the test is hermetic. Belt-and-suspenders; both should pass after this plan ships.

    File content:

    ```python
    """Phase 9 render-markdown byte-identical end-to-end test (ROADMAP SC-4).

    SC-4: data/loans.md and data/scenarios.md regenerate via --render-markdown
    byte-identical.

    This is the END-TO-END companion to Wave 4's
    test_render_markdown.py::test_render_markdown_byte_identical (which is
    the minimal unit-style assertion). The end-to-end variant runs the full
    init -> insert -> render -> render -> hashlib.sha256 compare pipeline,
    making the byte-identical contract regression-safe.

    Per Wave 4 D-04 inheritance: the byte-equality property depends on
    (a) explicit ORDER BY id ASC in render SELECTs, (b) NO generated_at
    timestamp embedded in markdown body, (c) the mandatory <!-- Generated
    from data/mortgage-ops.duckdb - edit via scripts, not directly --> header
    at line 1.
    """

    from __future__ import annotations

    import hashlib
    import json
    from pathlib import Path

    from tests.conftest import REPO_ROOT, node_orchestration_run

    # The render-markdown subcommand writes to FIXED paths under data/
    # (Plan 09-04 D-04-07: paths NOT env-var-overridable in v1).
    LOANS_MD: Path = REPO_ROOT / "data" / "loans.md"
    SCENARIOS_MD: Path = REPO_ROOT / "data" / "scenarios.md"
    GENERATED_HEADER: str = "<!-- Generated from data/mortgage-ops.duckdb"


    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


    def test_render_markdown_byte_identical_end_to_end(tmp_path: Path) -> None:
        """ROADMAP SC-4 end-to-end: full pipeline init -> 3 inserts ->
        render -> render -> SHA256-compare. Both files (loans.md +
        scenarios.md) must hash identically across consecutive runs."""
        db_path = tmp_path / "test_render_e2e.duckdb"

        # Cleanup any leftover render artifacts (Plan 09-04 D-04-07: render
        # writes to fixed paths under data/, regardless of DB location).
        for f in (LOANS_MD, SCENARIOS_MD):
            if f.exists():
                f.unlink()

        try:
            # 1. Init schema
            init = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
            assert init.returncode == 0, f"init failed: {init.stderr}"

            # 2. Insert 3 loans (varying types, principals, terms — non-trivial render)
            fixtures = [
                {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                    "loan_type": "fixed",
                },
                {
                    "principal": "350000.00",
                    "annual_rate": "0.070000",
                    "term_months": 180,
                    "origination_date": "2026-05-15",
                    "loan_type": "jumbo",
                },
                {
                    "principal": "1000000.00",
                    "annual_rate": "0.069500",
                    "term_months": 360,
                    "origination_date": "2026-06-01",
                    "loan_type": "jumbo",
                },
            ]
            for i, loan in enumerate(fixtures):
                fx = tmp_path / f"loan_{i}.json"
                fx.write_text(json.dumps(loan))
                ins = node_orchestration_run(
                    "orchestration/db-write.mjs",
                    "insert-loan",
                    "--json",
                    str(fx),
                    db_path=db_path,
                )
                assert ins.returncode == 0, f"insert {i} failed: {ins.stderr}"

            # 3. First render
            r1 = node_orchestration_run(
                "orchestration/db-write.mjs", "render-markdown", db_path=db_path
            )
            assert r1.returncode == 0, f"render run 1 failed: {r1.stderr}"
            assert LOANS_MD.exists(), f"loans.md not created at {LOANS_MD}"
            assert SCENARIOS_MD.exists(), f"scenarios.md not created at {SCENARIOS_MD}"

            hash_loans_1 = _sha256(LOANS_MD)
            hash_scenarios_1 = _sha256(SCENARIOS_MD)

            # 4. Second render against same DB state — must produce identical bytes
            r2 = node_orchestration_run(
                "orchestration/db-write.mjs", "render-markdown", db_path=db_path
            )
            assert r2.returncode == 0, f"render run 2 failed: {r2.stderr}"

            hash_loans_2 = _sha256(LOANS_MD)
            hash_scenarios_2 = _sha256(SCENARIOS_MD)

            # 5. Byte-identical contract (load-bearing)
            assert hash_loans_1 == hash_loans_2, (
                f"ROADMAP SC-4 violation: loans.md drifted between consecutive renders.\n"
                f"  Run 1 SHA256: {hash_loans_1}\n"
                f"  Run 2 SHA256: {hash_loans_2}\n"
                f"Likely cause (per Wave 4 D-04-03/04): missing ORDER BY id ASC, OR "
                f"a generated_at timestamp embedded in render output."
            )
            assert hash_scenarios_1 == hash_scenarios_2, (
                f"ROADMAP SC-4 violation: scenarios.md drifted between consecutive renders.\n"
                f"  Run 1 SHA256: {hash_scenarios_1}\n"
                f"  Run 2 SHA256: {hash_scenarios_2}"
            )

            # 6. Mandatory <!-- Generated from ... --> header at line 1 of both
            # (Wave 4 D-04-01 — load-bearing per Plan 09-PATTERNS.md)
            loans_text = LOANS_MD.read_text()
            scenarios_text = SCENARIOS_MD.read_text()
            assert loans_text.startswith(GENERATED_HEADER), (
                f"loans.md missing 'Generated from' header at line 1; "
                f"first 80 chars: {loans_text[:80]!r}"
            )
            assert scenarios_text.startswith(GENERATED_HEADER), (
                f"scenarios.md missing 'Generated from' header at line 1; "
                f"first 80 chars: {scenarios_text[:80]!r}"
            )

            # 7. All three principals appear in the rendered loans body (Decimal-string
            # discipline preserved through render layer per Wave 4 D-04-02)
            for principal in ("200000.00", "350000.00", "1000000.00"):
                assert principal in loans_text, (
                    f"principal {principal!r} missing from rendered loans.md; "
                    f"likely cause: CAST AS VARCHAR not applied (D-04-02)."
                )

        finally:
            # Cleanup generated artifacts (gitignored but tidy)
            for f in (LOANS_MD, SCENARIOS_MD):
                if f.exists():
                    f.unlink()
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_render_markdown_byte_identical.py -v --tb=short 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_orchestration/test_render_markdown_byte_identical.py` exits 0
    - `pytest tests/test_orchestration/test_render_markdown_byte_identical.py -v 2>&1 | grep -c PASSED` returns 1
    - `pytest tests/test_orchestration/test_render_markdown_byte_identical.py -v 2>&1 | grep -c FAILED` returns 0
    - `grep -c "hashlib.sha256" tests/test_orchestration/test_render_markdown_byte_identical.py` returns at least 1
    - `grep -c "_sha256" tests/test_orchestration/test_render_markdown_byte_identical.py` returns at least 5 (helper + 4 call sites)
    - `grep -c "GENERATED_HEADER" tests/test_orchestration/test_render_markdown_byte_identical.py` returns at least 3
    - After test, `test ! -f data/loans.md` exits 0 (cleanup ran)
    - After test, `test ! -f data/scenarios.md` exits 0 (cleanup ran)
    - `mypy --strict tests/test_orchestration/test_render_markdown_byte_identical.py` exits 0
    - `ruff check tests/test_orchestration/test_render_markdown_byte_identical.py` exits 0
  </acceptance_criteria>
  <done>
    SC-4 pinned end-to-end with hashlib.sha256 explicit comparison; supplements Wave 4 unit-style coverage.
  </done>
</task>

<task type="auto">
  <name>Task 5: Flip the 3 remaining Wave 0 xfail stubs in test_db_lifecycle.py + test_lockfile.py</name>
  <files>tests/test_orchestration/test_db_lifecycle.py, tests/test_orchestration/test_lockfile.py</files>
  <read_first>
    - tests/test_orchestration/test_db_lifecycle.py (Wave 0 stubs: test_init_db_idempotent, test_insert_loan_round_trip, test_concurrent_writes_serialize, test_decimal_string_round_trip_preserves_cents)
    - tests/test_orchestration/test_lockfile.py (Wave 0 stub: test_stale_lockfile_reclaimed_after_60s)
    - tests/test_orchestration/test_init_db_idempotent.py (Task 1 of THIS plan)
    - tests/test_orchestration/test_parallel_invocation.py (Task 2 of THIS plan)
    - tests/test_orchestration/test_stale_lockfile_recovery.py (Task 3 of THIS plan)
  </read_first>
  <action>
    The Wave 0 stubs reserved test names that other waves were supposed to flip. Wave 3 already flipped `test_insert_loan_round_trip` and `test_decimal_string_round_trip_preserves_cents` per the Plan 09-00 wave-flip table. This task flips the 3 remaining stubs by re-pointing them at the Task 1-3 implementations.

    **Strategy: thin re-export pattern.** Rather than duplicate the test bodies, re-implement each Wave 0 stub as a thin wrapper that delegates to the Task 1-3 functions. This keeps the Wave 0 test name (PERS-XX traceability) AND the Task 1-3 implementation (full body) coexistent.

    **File 1 — tests/test_orchestration/test_db_lifecycle.py:**

    Find the `test_init_db_idempotent` stub (decorated with `@pytest.mark.xfail(strict=True, ...)` and a `pytest.fail("Wave 0 stub")` body). Replace ENTIRELY with:

    ```python
    def test_init_db_idempotent(tmp_path: Path) -> None:
        """PERS-02 + ROADMAP SC-1: init-db.mjs is idempotent. This is the
        Wave 0 stub flipped by Plan 09-06; the full implementation lives in
        tests/test_orchestration/test_init_db_idempotent.py
        (test_init_db_idempotent_across_runs)."""
        from tests.test_orchestration.test_init_db_idempotent import (
            test_init_db_idempotent_across_runs,
        )

        test_init_db_idempotent_across_runs(tmp_path)
    ```

    Remove the `@pytest.mark.xfail(strict=True, ...)` decorator above this function.

    Find the `test_concurrent_writes_serialize` stub. Replace with:

    ```python
    def test_concurrent_writes_serialize(tmp_path: Path) -> None:
        """PERS-05 + ROADMAP SC-2: parallel writers serialize via lockfile.
        This is the Wave 0 stub flipped by Plan 09-06; the full implementation
        lives in tests/test_orchestration/test_parallel_invocation.py
        (test_parallel_inserts_serialize_via_lockfile)."""
        from tests.test_orchestration.test_parallel_invocation import (
            test_parallel_inserts_serialize_via_lockfile,
        )

        test_parallel_inserts_serialize_via_lockfile(tmp_path)
    ```

    Remove the `@pytest.mark.xfail(strict=True, ...)` decorator above this function.

    Do NOT modify `test_init_db_idempotent` or `test_concurrent_writes_serialize` IF they have ALREADY been flipped to passing implementations by an earlier wave (cross-reference Wave 3's behavior — Plan 09-03 may or may not have flipped them; Wave 0 D-00 says Wave 6 flips them, so this is the expected flip point).

    Do NOT touch `test_insert_loan_round_trip` or `test_decimal_string_round_trip_preserves_cents` — those were flipped by Wave 3 per Plan 09-00 line 252-253. If they are still xfail-decorated, that is a Wave 3 bug, not this plan's concern; surface as a blocker comment and proceed.

    **File 2 — tests/test_orchestration/test_lockfile.py:**

    Find the `test_stale_lockfile_reclaimed_after_60s` stub. Replace with:

    ```python
    def test_stale_lockfile_reclaimed_after_60s(tmp_path: Path) -> None:
        """PERS-04 + ROADMAP SC-3: stale lockfile (mtime > 60s) is reclaimed
        by next writer. This is the Wave 0 stub flipped by Plan 09-06; the
        full implementation lives in
        tests/test_orchestration/test_stale_lockfile_recovery.py
        (test_stale_lockfile_reclaimed_after_60s_threshold)."""
        from tests.test_orchestration.test_stale_lockfile_recovery import (
            test_stale_lockfile_reclaimed_after_60s_threshold,
        )

        test_stale_lockfile_reclaimed_after_60s_threshold(tmp_path)
    ```

    Remove the `@pytest.mark.xfail(strict=True, ...)` decorator above this function.

    **Why the thin-wrapper pattern:** preserves Wave 0 test names (which appear in REQUIREMENTS.md PERS-XX traceability) without duplicating ~150 lines of test body. Both names appear in pytest collection (one wrapper + one implementation), giving 2 PASSED rows per closed PERS — the wrapper proves the Wave 0 reservation was honored; the implementation proves the contract is pinned.

    **Sanity step:** after editing, run pytest on both modified files and confirm 0 xfailed.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_db_lifecycle.py tests/test_orchestration/test_lockfile.py -v --tb=short 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_orchestration/test_db_lifecycle.py tests/test_orchestration/test_lockfile.py -v 2>&1 | grep -c XFAIL` returns 0
    - `pytest tests/test_orchestration/test_db_lifecycle.py tests/test_orchestration/test_lockfile.py -v 2>&1 | grep -c FAILED` returns 0
    - `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_db_lifecycle.py` returns 0
    - `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_lockfile.py` returns 0
    - `grep -c "Wave 0 stub" tests/test_orchestration/test_db_lifecycle.py` returns 0
    - `grep -c "Wave 0 stub" tests/test_orchestration/test_lockfile.py` returns 0
    - `grep -c "def test_init_db_idempotent" tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c "def test_concurrent_writes_serialize" tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c "def test_stale_lockfile_reclaimed_after_60s" tests/test_orchestration/test_lockfile.py` returns 1
    - `mypy --strict tests/test_orchestration/test_db_lifecycle.py tests/test_orchestration/test_lockfile.py` exits 0
    - `ruff check tests/test_orchestration/test_db_lifecycle.py tests/test_orchestration/test_lockfile.py` exits 0
  </acceptance_criteria>
  <done>
    All 3 remaining Wave 0 xfails flipped to passing via thin-wrapper delegation; PERS-02, PERS-04, PERS-05 closed at the Wave 0 reservation layer + at the integration layer.
  </done>
</task>

<task type="auto">
  <name>Task 6: Verify zero regression + lint hygiene + xfail count = 0</name>
  <files>(verification only)</files>
  <action>
    Final verification. The Phase 9 success state: all 7 PERS requirements closed; all 5 ROADMAP SC- success criteria pinned by tests; xfail count = 0 (down from 7 at Wave 0 baseline); pass count up by ~10-12 (4 new tests in this plan + 3 wrapper flips + 2-3 helper tests like negative-companion + tables-exist).

    1. Full pytest suite: `pytest -q 2>&1 | tail -3` — assert 0 failed, 0 xfailed.
    2. Phase 9-only: `pytest tests/test_orchestration/ -v 2>&1 | tail -30` — assert all PASSED, none XFAIL.
    3. mypy --strict on tests/test_orchestration/.
    4. ruff check + ruff format --check on tests/test_orchestration/.
    5. Sanity: data/loans.md + data/scenarios.md NOT present after suite (cleanup ran in tests).
    6. Sanity: data/.mortgage-ops.duckdb.lock NOT present (no leaks).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest -q 2>&1 | tail -3 && pytest tests/test_orchestration/ -v 2>&1 | tail -30 && mypy --strict tests/test_orchestration/ && ruff check tests/test_orchestration/ && ruff format --check tests/test_orchestration/ && test ! -f data/loans.md && test ! -f data/scenarios.md && test ! -f data/.mortgage-ops.duckdb.lock && echo "ALL GREEN"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows >= 450 (Wave 5 baseline 444 + ~6 net new from Wave 6)
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ xfailed'` shows 0 (or absent — pytest omits the count when zero)
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ failed'` returns no match (zero failures)
    - `pytest tests/test_orchestration/ -v 2>&1 | grep -c XFAIL` returns 0
    - `pytest tests/test_orchestration/ -v 2>&1 | grep -c FAILED` returns 0
    - `mypy --strict tests/test_orchestration/` exits 0
    - `ruff check tests/test_orchestration/` exits 0
    - `ruff format --check tests/test_orchestration/` exits 0
    - `test ! -f data/loans.md` exits 0
    - `test ! -f data/scenarios.md` exits 0
    - `test ! -f data/.mortgage-ops.duckdb.lock` exits 0
  </acceptance_criteria>
  <done>
    Phase 9 test layer fully green: PERS-01..07 all closed; ROADMAP SC-1..SC-5 all pinned; xfail count = 0; lint clean; no leaked artifacts.
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS:**

- **D-06-09 (revision 2026-05-04 per Warning #4): Concurrency + stale-lock tests have explicit per-test timeout markers + per-subprocess timeouts.** — rationale: a flaky Node process hanging at the lockfile.mjs 30s acquireLock deadline could silently stall the suite. Belt-and-suspenders: (a) every `subprocess.run` / `subprocess.Popen.wait` call passes an explicit `timeout=` kwarg matching the test's wall-time budget; (b) each test function carries `@pytest.mark.timeout(N)` with N = 1.5-2x the underlying subprocess timeout (so the marker fires only if the kwarg ALSO fails to fire, e.g. the marker catches a hung pytest fixture itself or a Popen that never fires its own timeout). CI wall-time impact: parallel-invocation worst-case ~60s; stale-lockfile-recovery worst-case ~30s + ~10s pre-flight (Blocker #3) = ~40s; fresh-lockfile-blocks worst-case ~15s. Total Phase 9 concurrency-test wall-time budget: ~115s (was ~85s pre-revision; +30s comes from worst-case stale-lock retries plus the Blocker #3 pre-flight). Rule-of-three citation: pytest-timeout is the de facto idiom for hung-subprocess defense in test suites with subprocess invocations; career-ops uses analogous timeouts for its DB-write tests; Phase 5 ARM tests use timeouts on long-running fixtures.

- **D-06-01: Lockfile race-window mitigation = read-back-and-verify (NOT O_EXCL)** — rationale: career-ops pattern explicitly chose `writeFileSync` flag `'w'` over `'wx'` (O_EXCL) because O_EXCL is broken on NFS (RESEARCH lines 651-652 + [CITED: https://lwn.net/Articles/251004/]). Plan 09-01 inherits this verbatim. Plan 09-06 tests must therefore tolerate the documented race window: assertion is on FINAL STATE (count == baseline + N successful), not on which process won. Rule-of-three citation: career-ops/scripts/lockfile.mjs:42 uses `'w'`; RESEARCH §Pitfall 2 lines 648-665; RESEARCH line 580 ("The test must tolerate either ordering — the assertion is on the final state").

- **D-06-02: Stale-lockfile threshold = 60 seconds (5s margin → 65s in tests)** — rationale: career-ops lockfile.mjs uses 60s; RESEARCH line 17 + 584; tests use 65s margin to absorb clock skew + filesystem mtime resolution variance (some FSes round mtime to 1s; others to 0.001s; the 5s margin is safe across both). Rule-of-three citation: career-ops lockfile.mjs STALE_THRESHOLD_MS = 60_000; RESEARCH line 602 (test uses 65s); Plan 09-01 D-XX inheritance.

- **D-06-03: Render-markdown determinism via explicit ORDER BY + omit generated_at + fixed header** — rationale: inheritance from Wave 4 D-04-03 + D-04-04 + D-04-01. Test re-asserts these contracts at the integration layer (full pipeline) as belt-and-suspenders against future refactors that might subtly break Wave 4's unit-style guard. Rule-of-three citation: Plan 09-04 D-04-01..04; RESEARCH §Pitfall 3 lines 666-682; PATTERNS Pattern Assignments line 303.

- **D-06-04: Test-side parallel invocation uses subprocess.Popen (NOT node_orchestration_run which uses subprocess.run)** — rationale: subprocess.run blocks; we need both `node` processes spawned simultaneously. Popen returns immediately so the test can launch p1, then p2, then `.wait()` on each. Rule-of-three citation: RESEARCH lines 522-529 (test design uses Popen); subprocess docs (Popen non-blocking, run blocking); the conftest helper signature returns CompletedProcess (already-completed shape).

- **D-06-05: Wave 0 stub names preserved via thin-wrapper delegation (NOT renamed, NOT deleted)** — rationale: Wave 0 D-00 Rule-1 ("test contract is source of truth") locks the stub names to PERS-XX traceability; renaming would break the requirement-mapping table. The Task 5 wrappers preserve the stub name + delegate to the Task 1-3 implementations; both appear in pytest collection (2 PASSED per closed PERS) which is fine — duplicate execution is cheap (~1-3s per stub per duplicate run) and the traceability win outweighs the cost. Rule-of-three citation: Wave 0 D-00 Rule-1; REQUIREMENTS.md PERS-02/04/05 reference the stub names; PHASE 9 ROADMAP SC-1/2/3 cite the stub names verbatim.

- **D-06-06: data/loans.md + data/scenarios.md cleanup happens in `try/finally` blocks** — rationale: render writes to fixed paths under `data/` (Plan 09-04 D-04-07: NOT env-var-overridable in v1); without cleanup, suite leaves stray files in the working tree. The try/finally pattern guarantees cleanup even when an assertion fails. Rule-of-three citation: Plan 09-04 D-04-07 + Plan 09-04 Task 2 (Wave 4 already uses try/finally); pytest standard fixture cleanup pattern; tmp_path cannot help here because the paths are NOT under tmp_path.

- **D-06-07: Test fixture loan field naming uses `annual_rate` (NOT `apr`)** — rationale: cross-reference Plan 09-03's cmdInsertLoan signature; the loans schema column is `annual_rate` (RESEARCH §Pinned schema DDL — verify this against actual Plan 09-03 implementation). RESEARCH §test designs (lines 547-552) used `apr` because that snippet pre-dated the schema lock; the actual schema uses `annual_rate`. If Plan 09-03 ships with `apr`, swap accordingly — but the test must match the schema column exactly. Rule-of-three citation: 09-RESEARCH §Pinned schema DDL; Plan 09-03 PLAN.md cmdInsertLoan field validation; the schema column name is the source of truth.

- **D-06-08: SC-4 has TWO byte-identical tests (Wave 4 unit + Wave 6 end-to-end), both pass** — rationale: belt-and-suspenders for the load-bearing byte-equality contract. Wave 4 is the minimal unit guard (`bytes_a == bytes_b`); Wave 6 is the end-to-end pipeline guard (full init -> insert -> render -> SHA256). They cover different failure surfaces: a Wave-4 regression catches a render-only break; a Wave-6 regression catches an upstream insert-side break that propagates to render. Rule-of-three citation: Wave 4 Task 2 (the original test); RESEARCH §Pitfall 3 (the failure-mode taxonomy); ROADMAP SC-4 emphasis on "byte-identical".
</locked_decisions>

<verify_block>
**Verify Block:**

```bash
# 1. All 4 new test files exist
test -f tests/test_orchestration/test_init_db_idempotent.py
test -f tests/test_orchestration/test_parallel_invocation.py
test -f tests/test_orchestration/test_stale_lockfile_recovery.py
test -f tests/test_orchestration/test_render_markdown_byte_identical.py

# 2. Each test file passes individually
pytest tests/test_orchestration/test_init_db_idempotent.py -v --tb=short
pytest tests/test_orchestration/test_parallel_invocation.py -v --tb=short
pytest tests/test_orchestration/test_stale_lockfile_recovery.py -v --tb=short
pytest tests/test_orchestration/test_render_markdown_byte_identical.py -v --tb=short

# 3. Wave 0 stubs flipped (test_db_lifecycle.py + test_lockfile.py)
pytest tests/test_orchestration/test_db_lifecycle.py tests/test_orchestration/test_lockfile.py -v --tb=short
grep -c "@pytest.mark.xfail" tests/test_orchestration/test_db_lifecycle.py    # expect 0
grep -c "@pytest.mark.xfail" tests/test_orchestration/test_lockfile.py        # expect 0

# 4. Full Phase 9 suite green; xfail count = 0
pytest tests/test_orchestration/ -v 2>&1 | tail -30
pytest tests/test_orchestration/ -v 2>&1 | grep -c XFAIL  # expect 0
pytest tests/test_orchestration/ -v 2>&1 | grep -c FAILED # expect 0

# 5. Full project suite green; xfail count = 0 (was 7 at Phase 9 start)
pytest -q 2>&1 | tail -3

# 6. Lint + type clean
mypy --strict tests/test_orchestration/
ruff check tests/test_orchestration/
ruff format --check tests/test_orchestration/

# 7. No leaked artifacts after suite
test ! -f data/loans.md
test ! -f data/scenarios.md
test ! -f data/.mortgage-ops.duckdb.lock

# 8. SC verification matrix:
#    SC-1 (idempotent init):       test_init_db_idempotent_across_runs PASSED
#    SC-2 (parallel writers):      test_parallel_inserts_serialize_via_lockfile PASSED
#    SC-3 (stale-lock recovery):   test_stale_lockfile_reclaimed_after_60s_threshold PASSED
#    SC-4 (byte-identical render): test_render_markdown_byte_identical (Wave 4) +
#                                  test_render_markdown_byte_identical_end_to_end (Wave 6) BOTH PASSED
#    SC-5 (known-loans 7 entries): test_known_loans_catalog_complete (Wave 5) PASSED
echo "Phase 9 ready for /gsd-verify-work"
```
</verify_block>

<deviation_rules>
**Deviation Rules:**

- **Rule-1 (test contract names are pinned):** D-06-05 locks the Wave 0 stub names. If the executor finds a stub name that mismatches a requirement (e.g., `test_concurrent_writes_serialize` looks redundant with `test_parallel_inserts_serialize_via_lockfile`), DO NOT silently rename or delete. The thin-wrapper pattern is the answer; surface naming-cleanup proposals as a future-phase comment.

- **Rule-2 (race-window assertion = final state):** D-06-01 locks "tolerate either ordering". If the executor writes `assert rc1 == 0 and rc2 == 0` as a hard equality (not allowing for fail-fast lock-busy), STOP — that may flake under the documented race window. Use the "successes >= 1 + failures must be lock-shaped + final count = baseline + len(successes)" pattern.

- **Rule-3 (loan field naming match Plan 09-03):** D-06-07 says use `annual_rate`. Before writing tests, GREP `orchestration/db-write.mjs` for the actual field name validated by `cmdInsertLoan` and use whatever 09-03 ships. If 09-03 actually validates `apr`, swap (but commit the rename in the test reference too). The test must match the schema column exactly.

- **Rule-4 (cleanup is non-negotiable):** D-06-06 mandates try/finally cleanup of `data/loans.md` + `data/scenarios.md`. If the executor writes a test without try/finally, STOP — failed assertions will leave stray files in the working tree, which contaminates the next test run AND the developer's git status.

- **Rule-5 (timeouts):** parallel-invocation uses `wait(timeout=60)` + `@pytest.mark.timeout(90)`; stale-lockfile-recovery uses `timeout=30` + `@pytest.mark.timeout(60)`; fresh-lockfile-blocks uses `timeout=15` + `@pytest.mark.timeout(30)`. Per D-06-09 (revision 2026-05-04 per Warning #4), the pytest-timeout marker is 1.5-2x the subprocess timeout to act as a hung-process safety net. These are not arbitrary — they account for the Plan 09-01 polling interval (typically 100ms) + DuckDB warmup time (~200-500ms) + Blocker #3 pre-flight overhead + safety margin. Do NOT shrink them without verifying against the actual 09-01 implementation; flakiness will result. Total CI wall-time impact: ~115s for the three concurrency tests (was ~85s pre-revision).

- **Rule-6 (lint hygiene as Rule-3 deviation):** ruff format may apply to the long string literals; apply minimal fixes. mypy --strict may flag missing annotations on inner functions; add explicit `-> None` return types as needed.

- **Rule-7 (no Node code modifications):** Plan 09-06 is TEST-LAYER ONLY. Do NOT modify orchestration/*.mjs files in this plan. If a test reveals a bug in init-db.mjs or db-write.mjs or lockfile.mjs, STOP and surface as a blocker comment — bug-fixes belong in a follow-up wave or in Plan 09-XX revisions, not silently in this plan.
</deviation_rules>

<dependencies>
**Dependencies:**

- **Depends on:** Plan 09-00 (Wave 0 stubs in test_db_lifecycle.py + test_lockfile.py; node_orchestration_run helper); Plan 09-01 (orchestration/lockfile.mjs withLock contract; STALE_THRESHOLD_MS = 60_000); Plan 09-02 (orchestration/init-db.mjs idempotent schema); Plan 09-03 (orchestration/db-write.mjs cmdInsertLoan + cmdQuery + WRITE_COMMANDS Set); Plan 09-04 (orchestration/db-write.mjs cmdRenderMarkdown + LOANS_MD/SCENARIOS_MD output); Plan 09-05 (data/known-loans.yml — not directly required by these tests but proves the catalog is committed before integration tests run).
- **Blocks:** Plan 09-07 (references doc may cite the test names for "see also"; references doc cannot describe Plan 09-06's coverage shape until this plan ships).
- **Inheritance:** D-04-01..07 (render determinism contract from Wave 4); Wave 0 D-00 Rule-1 (test contract is source of truth); Wave 1 D-01-XX (lockfile.mjs contract); Wave 2 D-02-XX (init-db.mjs idempotency).
- **Forward dependencies:** `/gsd-verify-work` runs after this plan ships and reads PERS-XX closure status from the test results; the suite-green state is the gate to Phase 10.
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Two parallel `node` processes -> single DuckDB file | withLock + DuckDB OS lock are the two layers of mutual exclusion |
| Pre-existing lockfile (untrusted state) -> next writer | Stale-detection logic decides: reclaim if mtime > 60s, wait/fail otherwise |
| Render-markdown -> data/loans.md, data/scenarios.md | Byte-equality contract is the load-bearing user-facing guarantee |
| Test-spawned subprocess.Popen -> parent test process | env var passing (MORTGAGE_OPS_DB_PATH) isolates test DBs from production data |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-27 | Tampering (parallel writers cause partial-insert state) | db-write.mjs cmdInsertLoan + lockfile.mjs withLock | mitigate | test_parallel_inserts_serialize_via_lockfile asserts final count = baseline + successes (no partials, no doubles) |
| T-09-28 | Denial of Service (lockfile leak permanently blocks all writers) | lockfile.mjs releaseLock skipped path | mitigate | Both parallel + stale tests assert lockfile does NOT exist after the test; would catch a finally-block bug |
| T-09-29 | Repudiation (init-db silently mutates schema across runs) | init-db.mjs DDL with missing IF NOT EXISTS | mitigate | _schema_fingerprint via SHA256 of pragma_table_info dump catches any drift; test_init_db_idempotent_across_runs |
| T-09-30 | Spoofing (stale lockfile from crashed prior writer never reclaimed) | lockfile.mjs stale-detection threshold | mitigate | Positive: test_stale_lockfile_reclaimed_after_60s_threshold (65s reclaimed); Negative: test_fresh_lockfile_under_60s_blocks_or_waits (5s NOT reclaimed) |
| T-09-31 | Tampering (render output drifts due to non-deterministic SELECT order or embedded timestamp) | db-write.mjs cmdRenderMarkdown SELECTs | mitigate | hashlib.sha256 comparison of rendered file bytes (Wave 6) + Wave 4 byte-equality unit test; both PASSED required for Phase 9 closure |
| T-09-32 | Information Disclosure (test fixtures contain real PII or credentials) | tests/test_orchestration/*.py fixtures | accept | All test fixtures use synthetic data ($150k/$200k/$300k principals; bogus PIDs); no PII; no credentials |
| T-09-33 | Elevation of Privilege (test sets MORTGAGE_OPS_DB_PATH to a path outside tmp_path, contaminating production data/mortgage-ops.duckdb) | env var passing in _spawn_insert | mitigate | All test invocations pass `db_path=tmp_path / "...duckdb"`; explicit path containment; no production data at risk |
</threat_model>

<verification>
- 4 new integration test files exist under tests/test_orchestration/
- 3 Wave 0 xfail stubs flipped via thin-wrapper delegation
- ROADMAP SC-1, SC-2, SC-3 pinned by passing end-to-end tests
- ROADMAP SC-4 pinned by both Wave 4 unit + Wave 6 end-to-end tests
- ROADMAP SC-5 pinned by Wave 5 catalog test (separate plan; verified upstream)
- xfail count drops from 4 (Wave 5 baseline) to 0 (post-Wave 6)
- Full project suite green; mypy + ruff clean
- No leaked artifacts: data/loans.md, data/scenarios.md, data/.mortgage-ops.duckdb.lock all absent post-suite
- PERS-02, PERS-04, PERS-05 closed at the integration layer
</verification>

<success_criteria>
- All 5 ROADMAP SC- success criteria pinned by passing tests (SC-1 through SC-5)
- All 7 PERS-01..07 requirements closed (PERS-01/02/03 from Wave 2-3, PERS-04/05 from Wave 6, PERS-06 from Wave 4 + Wave 6, PERS-07 from Wave 5)
- xfail count = 0 across the entire project (was 7 at Phase 9 start)
- Phase 9 test layer regression-protected against the four documented failure modes: lockfile race window, stale-lock-detection drift, init-DDL non-idempotency, render-markdown byte-equality break
- Phase 9 ready for /gsd-verify-work followed by Phase 10
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-06-SUMMARY.md` documenting:
- 4 new test files + line counts + SC pinning matrix
- 3 Wave 0 stubs flipped (thin-wrapper delegation pattern)
- Pass count delta (Wave 5 baseline 444 -> Wave 6 baseline ~454-456 depending on companion-test counts)
- xfail count delta (4 -> 0)
- PERS-02, PERS-04, PERS-05 closure status (now closed)
- Cumulative phase status: PERS-01..07 ALL closed; SC-1..SC-5 ALL pinned
- Pitfall coverage: Pitfall 2 (race window) regression-protected via test_parallel_inserts_serialize_via_lockfile; Pitfall 3 (render determinism) double-protected via Wave 4 + Wave 6
- Note: Phase 9 ready for /gsd-verify-work and references doc (Plan 09-07)
</output>
