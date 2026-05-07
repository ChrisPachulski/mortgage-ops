---
phase: 09
plan: 01
type: execute
wave: 1
depends_on:
  - "09-00"
files_modified:
  - orchestration/lockfile.mjs
  - tests/test_orchestration/test_lockfile_unit.py
autonomous: true
requirements:
  - PERS-04
  - PERS-05
tags:
  - phase-09
  - duckdb-orchestration
  - lockfile
  - concurrency
must_haves:
  truths:
    - "orchestration/lockfile.mjs exists and exports acquireLock, releaseLock, withLock, isStale, readLock"
    - "Lockfile content is JSON {pid, acquired_at, reason} written to data/.lock at repo root"
    - "STALE_THRESHOLD_MS = 60_000 is exported as a constant; isStale(lock) returns true iff Date.now() - lock.acquired_at > 60000"
    - "acquireLock uses writeFileSync with flag 'w' followed by read-back-and-verify (poor-man's compare-and-swap per PATTERNS Critical Issue 1)"
    - "releaseLock checks pid + acquired_at match before unlinkSync (prevents race where process A deletes process B's lock)"
    - "withLock(fn, opts) wrapper acquires before fn(), releases in finally even on throw"
    - "tests/test_orchestration/test_lockfile_unit.py has at least 6 unit tests exercising the lockfile API directly via Node subprocess + lock file inspection"
    - "All Phase 5 baseline tests still pass (>=432 passed + >=4 skipped)"
  artifacts:
    - path: "orchestration/lockfile.mjs"
      provides: "Cross-process mutex primitive with 60s stale recovery (port of career-ops/scripts/lockfile.mjs)"
      contains: "export async function withLock"
      min_lines: 70
    - path: "tests/test_orchestration/test_lockfile_unit.py"
      provides: "Unit tests for lockfile mechanics (separate from PERS-04 stale-recovery integration test in test_lockfile.py)"
      contains: "def test_"
      min_lines: 80
  key_links:
    - from: "orchestration/db-write.mjs (Wave 3)"
      to: "orchestration/lockfile.mjs"
      via: "import { withLock } from './lockfile.mjs'"
      pattern: "import.*withLock.*from.*lockfile.mjs"
    - from: "data/.lock"
      to: "process.pid + Date.now()"
      via: "JSON serialization in acquireLock"
      pattern: "JSON.stringify.*pid.*acquired_at"
---

<objective>
**Goal:** Ship the cross-process mutex primitive (`orchestration/lockfile.mjs`) that all Phase 9 write subcommands wrap their DuckDB transactions in. Port career-ops/scripts/lockfile.mjs verbatim, change three constants (path constant rename + lock filename `.lock` per DATA_CONTRACT.md), and add a unit-test surface that exercises acquire / release / stale-recovery / read-back-verification mechanics directly without touching DuckDB.

**Purpose:** PERS-04 + PERS-05 require a working `withLock()` BEFORE Wave 2 (init-db.mjs) and Wave 3 (db-write.mjs --insert-loan) can land. Lockfile is the foundation; its correctness gates every subsequent write.

**Output:** orchestration/lockfile.mjs (~80 lines, mirrors career-ops/scripts/lockfile.mjs exactly with 3 renames); tests/test_orchestration/test_lockfile_unit.py (~120 lines, 6+ unit tests exercising the API via Node subprocess + filesystem inspection). NO touching of init-db.mjs or db-write.mjs (those land in later waves).
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
@tests/conftest.py
@tests/test_orchestration/test_lockfile.py

<interfaces>
**career-ops/scripts/lockfile.mjs** is the line-for-line port target (78 lines). The full file lives at `/Users/cujo253/Documents/career-ops/scripts/lockfile.mjs` — read it as the canonical reference.

Public API (preserve verbatim, rename three constants only):
```javascript
export const STALE_THRESHOLD_MS = 60_000;
export const DEFAULT_TIMEOUT_MS = 30_000;
export const POLL_INTERVAL_MS = 100;

export function readLock(): { pid: number, acquired_at: number, reason: string } | null;
export function isStale(lock): boolean;  // Date.now() - lock.acquired_at > STALE_THRESHOLD_MS
export async function acquireLock({ timeoutMs?, reason? }): Promise<{ pid, acquired_at, reason }>;
export function releaseLock(myLock): void;
export async function withLock(fn, opts): Promise<ReturnType<typeof fn>>;
```

**Renames from career-ops -> mortgage-ops:**
1. `CAREER_OPS` constant -> `MORTGAGE_OPS`
2. Lock filename `.career-ops.lock` -> `.lock` (per DATA_CONTRACT.md line 22 + RESEARCH §Recommended Project Structure shows `data/.mortgage-ops.duckdb.lock` BUT spawn message mandates `data/.lock` — use `.lock` per spawn)
3. Module-level path resolution: `dirname(dirname(fileURLToPath(import.meta.url)))` (lockfile.mjs is at `orchestration/`, repo root is one `dirname` up)

**Lock file path:** `MORTGAGE_OPS / 'data' / '.lock'` (per spawn message constraint and DATA_CONTRACT.md cross-reference).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create orchestration/ directory and port lockfile.mjs from career-ops</name>
  <files>orchestration/lockfile.mjs</files>
  <read_first>
    - /Users/cujo253/Documents/career-ops/scripts/lockfile.mjs (full file, 78 lines) — line-for-line port target
    - 09-PATTERNS.md "orchestration/lockfile.mjs (concurrency primitive)" section — confirms verbatim port + 3 renames
    - 09-PATTERNS.md "Critical Issue 1" — explains why writeFileSync(flag:'w') + read-back is correct (NOT 'wx'/O_EXCL)
  </read_first>
  <action>
    Create `orchestration/` directory (mkdir -p). Then create `orchestration/lockfile.mjs` as a near-verbatim port of `career-ops/scripts/lockfile.mjs` with exactly three renames:

    1. `CAREER_OPS` constant -> `MORTGAGE_OPS`
    2. `.career-ops.lock` filename -> `.lock`
    3. Header comment block updated to cite mortgage-ops and Phase 9 PERS-04/PERS-05

    Full file content (write exactly this):

    ```javascript
    // orchestration/lockfile.mjs
    // Cross-process mutex for serializing DuckDB writes via data/.lock.
    // Ported verbatim from career-ops/scripts/lockfile.mjs (Phase 9 PATTERNS.md
    // Critical Issue 1) with three renames: CAREER_OPS -> MORTGAGE_OPS,
    // .career-ops.lock -> .lock, header citation block.
    //
    // PERS-04 + PERS-05 + ROADMAP SC-3: 60s stale-lock recovery.
    // Plan 09-01 D-01-01: writeFileSync(flag:'w') + read-back-and-verify is the
    // poor-man's compare-and-swap (PATTERNS Critical Issue 1). flag:'wx' (O_EXCL)
    // is INTENTIONALLY NOT USED — it would crash on every acquire because the
    // existing stale lock would still be on disk; the existing code intentionally
    // OVERWRITES stale locks at lines acquireLock:if(!existing||isStale(existing)).
    //
    // Plan 09-01 D-01-02: stale recovery is acquired_at-based (JSON content),
    // NOT mtime-based. Deliberate: mtime is vulnerable to filesystem `touch`
    // and clock-skew between fs-clock and process-clock. The JSON-content
    // timestamp is set deterministically by the writer in the same wall-clock
    // domain that reads it back.

    import { writeFileSync, readFileSync, unlinkSync, existsSync } from 'fs';
    import { join, dirname } from 'path';
    import { fileURLToPath } from 'url';

    const MORTGAGE_OPS = dirname(dirname(fileURLToPath(import.meta.url)));
    const LOCK_PATH = join(MORTGAGE_OPS, 'data', '.lock');

    export const STALE_THRESHOLD_MS = 60_000;
    export const DEFAULT_TIMEOUT_MS = 30_000;
    export const POLL_INTERVAL_MS = 100;

    function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    export function readLock() {
      if (!existsSync(LOCK_PATH)) return null;
      try {
        return JSON.parse(readFileSync(LOCK_PATH, 'utf-8'));
      } catch (e) {
        // Corrupt or partially-written lock — treat as absent so caller overwrites.
        return null;
      }
    }

    export function isStale(lock) {
      if (!lock || typeof lock.acquired_at !== 'number') return true;
      const age = Date.now() - lock.acquired_at;
      return age > STALE_THRESHOLD_MS;
    }

    export async function acquireLock({ timeoutMs = DEFAULT_TIMEOUT_MS, reason = '' } = {}) {
      const deadline = Date.now() + timeoutMs;
      const myLock = { pid: process.pid, acquired_at: Date.now(), reason };

      while (Date.now() < deadline) {
        const existing = readLock();
        if (!existing || isStale(existing)) {
          try {
            // flag:'w' = O_TRUNC | O_CREAT | O_WRONLY (NOT O_EXCL — see header comment).
            writeFileSync(LOCK_PATH, JSON.stringify(myLock, null, 2), { flag: 'w' });
            // Read-back-and-verify: poor-man's compare-and-swap.
            const readBack = readLock();
            if (readBack && readBack.pid === process.pid && readBack.acquired_at === myLock.acquired_at) {
              return myLock;
            }
          } catch (e) {
            // Race: another process wrote between our read and write. Retry.
          }
        }
        await sleep(POLL_INTERVAL_MS);
      }
      const blocker = readLock();
      throw new Error(`Lock acquire timeout after ${timeoutMs}ms. Blocker: ${JSON.stringify(blocker)}`);
    }

    export function releaseLock(myLock) {
      const existing = readLock();
      if (existing && existing.pid === myLock.pid && existing.acquired_at === myLock.acquired_at) {
        try {
          unlinkSync(LOCK_PATH);
        } catch (e) {
          // Already gone — fine.
        }
      }
      // If existing.pid != myLock.pid, another process owns the lock now. Do not unlink.
    }

    export async function withLock(fn, opts = {}) {
      const lock = await acquireLock(opts);
      try {
        return await fn();
      } finally {
        releaseLock(lock);
      }
    }
    ```

    Verify the file is at exactly the path `orchestration/lockfile.mjs`. Do NOT create `package.json` (that lands in Wave 2). The file uses ESM imports (`import { ... } from 'fs'`) which Node treats correctly when invoked as `.mjs` regardless of package.json type. Wave 2's package.json adds `"type": "module"` for completeness.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && test -f orchestration/lockfile.mjs && node --check orchestration/lockfile.mjs && echo "syntax OK"</automated>
  </verify>
  <acceptance_criteria>
    - `test -d orchestration` exits 0
    - `test -f orchestration/lockfile.mjs` exits 0
    - `node --check orchestration/lockfile.mjs` exits 0 (parses without syntax error)
    - `grep -c "export async function withLock" orchestration/lockfile.mjs` returns 1
    - `grep -c "export async function acquireLock" orchestration/lockfile.mjs` returns 1
    - `grep -c "export function releaseLock" orchestration/lockfile.mjs` returns 1
    - `grep -c "export function isStale" orchestration/lockfile.mjs` returns 1
    - `grep -c "export function readLock" orchestration/lockfile.mjs` returns 1
    - `grep -c "STALE_THRESHOLD_MS = 60_000" orchestration/lockfile.mjs` returns 1
    - `grep -c "MORTGAGE_OPS" orchestration/lockfile.mjs` returns at least 2 (constant def + LOCK_PATH usage)
    - `grep -c "CAREER_OPS" orchestration/lockfile.mjs` returns 0 (rename complete)
    - `grep -c "'.lock'" orchestration/lockfile.mjs` returns 1 (lock filename rename)
    - `grep -c "writeFileSync.*flag.*'w'" orchestration/lockfile.mjs` returns 1 (NOT 'wx' — Critical Issue 1 discipline preserved)
    - `wc -l orchestration/lockfile.mjs` returns at least 70 lines
  </acceptance_criteria>
  <done>
    orchestration/lockfile.mjs exists; node --check parses cleanly; all 5 exports present; CAREER_OPS rename complete; flag:'w' discipline preserved.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/test_orchestration/test_lockfile_unit.py with 6+ mechanics tests</name>
  <files>tests/test_orchestration/test_lockfile_unit.py</files>
  <read_first>
    - tests/conftest.py — node_orchestration_run helper signature
    - 09-PATTERNS.md "Critical Issue 1" — three findings the unit tests must exercise
    - 09-RESEARCH.md "Stale-Lockfile-Recovery Test" — pre-create-lock pattern
  </read_first>
  <action>
    Create tests/test_orchestration/test_lockfile_unit.py with unit tests that exercise lockfile mechanics WITHOUT touching DuckDB. Each test uses an inline Node one-liner via `subprocess.run(["node", "-e", "..."])` to invoke the lockfile API directly.

    These are UNIT tests for the lockfile primitive. The integration test (test_stale_lockfile_reclaimed_after_60s in test_lockfile.py from Wave 0) stays xfail until Wave 6 ships the integration with init-db + db-write.

    File content:

    ```python
    """Phase 9 lockfile.mjs unit tests — exercises the lockfile API directly
    without touching DuckDB or db-write.mjs.

    Plan 09-01 ships orchestration/lockfile.mjs; this test surface validates
    PERS-04 mechanics at the primitive layer. The full integration test
    (test_stale_lockfile_reclaimed_after_60s in test_lockfile.py) flips in
    Wave 6 once init-db.mjs (Wave 2) and db-write.mjs (Wave 3) exist.

    All tests use inline `node -e "..."` invocations; the orchestration script
    is imported as a relative ESM module via dynamic import. cwd=REPO_ROOT so
    the relative path 'orchestration/lockfile.mjs' resolves correctly.
    """

    from __future__ import annotations

    import json
    import subprocess
    import time
    from pathlib import Path

    import pytest

    REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    LOCK_PATH: Path = REPO_ROOT / "data" / ".lock"


    def _node_run(script: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
        """Run an inline Node ESM script via `node --input-type=module`."""
        return subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )


    @pytest.fixture(autouse=True)
    def _cleanup_lock() -> None:
        """Remove any stale data/.lock from prior test runs before AND after."""
        if LOCK_PATH.exists():
            LOCK_PATH.unlink()
        yield
        if LOCK_PATH.exists():
            LOCK_PATH.unlink()


    def test_acquire_then_release_cycles_cleanly() -> None:
        """acquireLock writes data/.lock with {pid, acquired_at, reason}; releaseLock removes it."""
        script = """
        import { acquireLock, releaseLock, readLock } from './orchestration/lockfile.mjs';
        const lock = await acquireLock({ reason: 'unit-test' });
        const onDisk = readLock();
        console.log(JSON.stringify({
          got_pid: lock.pid === process.pid,
          got_reason: lock.reason === 'unit-test',
          on_disk_pid: onDisk.pid === process.pid,
          on_disk_acquired_at: typeof onDisk.acquired_at === 'number',
        }));
        releaseLock(lock);
        const after = readLock();
        console.log(JSON.stringify({ released: after === null }));
        """
        result = _node_run(script)
        assert result.returncode == 0, f"stderr={result.stderr}"
        lines = result.stdout.strip().split("\n")
        before = json.loads(lines[0])
        after = json.loads(lines[1])
        assert before["got_pid"] is True
        assert before["got_reason"] is True
        assert before["on_disk_pid"] is True
        assert before["on_disk_acquired_at"] is True
        assert after["released"] is True
        assert not LOCK_PATH.exists(), "lockfile should be deleted after releaseLock"


    def test_isstale_returns_true_for_lock_older_than_60s() -> None:
        """isStale(lock) is true iff Date.now() - lock.acquired_at > STALE_THRESHOLD_MS (60000)."""
        script = """
        import { isStale, STALE_THRESHOLD_MS } from './orchestration/lockfile.mjs';
        const fresh = { pid: 1, acquired_at: Date.now(), reason: '' };
        const stale = { pid: 2, acquired_at: Date.now() - 65000, reason: '' };
        const at_boundary_minus = { pid: 3, acquired_at: Date.now() - 59000, reason: '' };
        console.log(JSON.stringify({
          threshold: STALE_THRESHOLD_MS,
          fresh_stale: isStale(fresh),
          stale_stale: isStale(stale),
          boundary_stale: isStale(at_boundary_minus),
        }));
        """
        result = _node_run(script)
        assert result.returncode == 0, f"stderr={result.stderr}"
        out = json.loads(result.stdout.strip())
        assert out["threshold"] == 60000
        assert out["fresh_stale"] is False
        assert out["stale_stale"] is True
        assert out["boundary_stale"] is False  # 59s < 60s threshold


    def test_isstale_returns_true_for_null_or_corrupt_lock() -> None:
        """Defense in depth: isStale(null) == true; isStale(missing acquired_at) == true."""
        script = """
        import { isStale } from './orchestration/lockfile.mjs';
        console.log(JSON.stringify({
          null_lock: isStale(null),
          undefined_lock: isStale(undefined),
          missing_acquired_at: isStale({ pid: 1, reason: 'x' }),
          string_acquired_at: isStale({ pid: 1, acquired_at: 'not-a-number', reason: '' }),
        }));
        """
        result = _node_run(script)
        assert result.returncode == 0, f"stderr={result.stderr}"
        out = json.loads(result.stdout.strip())
        assert all(out.values()), f"all four should be stale: {out}"


    def test_acquirelock_overwrites_stale_lock() -> None:
        """acquireLock claims a stale (>60s old) lock from another PID."""
        # Pre-create a stale lock under a bogus PID
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        stale_acquired_at = int((time.time() - 65) * 1000)
        LOCK_PATH.write_text(
            json.dumps({"pid": 99999, "acquired_at": stale_acquired_at, "reason": "stale-fixture"}, indent=2)
        )
        script = """
        import { acquireLock, releaseLock, readLock } from './orchestration/lockfile.mjs';
        const lock = await acquireLock({ timeoutMs: 5000, reason: 'reclaim-test' });
        const onDisk = readLock();
        console.log(JSON.stringify({
          claimed: lock.pid === process.pid,
          on_disk_pid: onDisk.pid === process.pid,
          on_disk_reason: onDisk.reason === 'reclaim-test',
        }));
        releaseLock(lock);
        """
        result = _node_run(script)
        assert result.returncode == 0, f"stderr={result.stderr}"
        out = json.loads(result.stdout.strip())
        assert out["claimed"] is True
        assert out["on_disk_pid"] is True
        assert out["on_disk_reason"] is True


    def test_releaselock_does_not_delete_other_process_lock() -> None:
        """releaseLock checks pid + acquired_at match before unlink (race protection)."""
        # Pre-create a lock owned by a different PID/timestamp
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        other_lock = {"pid": 99999, "acquired_at": int(time.time() * 1000), "reason": "other-process"}
        LOCK_PATH.write_text(json.dumps(other_lock, indent=2))
        script = """
        import { releaseLock, readLock } from './orchestration/lockfile.mjs';
        // Construct a fake lock with current PID but DIFFERENT acquired_at
        const fake = { pid: process.pid, acquired_at: 1, reason: 'fake' };
        releaseLock(fake);
        const after = readLock();
        console.log(JSON.stringify({
          still_present: after !== null,
          still_other_pid: after && after.pid === 99999,
        }));
        """
        result = _node_run(script)
        assert result.returncode == 0, f"stderr={result.stderr}"
        out = json.loads(result.stdout.strip())
        assert out["still_present"] is True, "releaseLock must NOT delete other process's lock"
        assert out["still_other_pid"] is True


    def test_withlock_releases_on_throw() -> None:
        """withLock(fn) releases the lock even if fn() throws."""
        script = """
        import { withLock, readLock } from './orchestration/lockfile.mjs';
        try {
          await withLock(async () => { throw new Error('intentional'); }, { reason: 'throw-test' });
        } catch (e) {
          // Expected
        }
        const after = readLock();
        console.log(JSON.stringify({ released: after === null }));
        """
        result = _node_run(script)
        assert result.returncode == 0, f"stderr={result.stderr}"
        out = json.loads(result.stdout.strip())
        assert out["released"] is True, "withLock MUST release lock on throw (finally clause)"


    def test_acquirelock_times_out_against_fresh_lock() -> None:
        """acquireLock with short timeout fails fast against a fresh (non-stale) lock."""
        # Pre-create a FRESH lock (acquired_at = now)
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fresh = {"pid": 99999, "acquired_at": int(time.time() * 1000), "reason": "blocker"}
        LOCK_PATH.write_text(json.dumps(fresh, indent=2))
        script = """
        import { acquireLock } from './orchestration/lockfile.mjs';
        try {
          await acquireLock({ timeoutMs: 500, reason: 'should-timeout' });
          console.log(JSON.stringify({ ok: false, err: null }));
        } catch (e) {
          console.log(JSON.stringify({ ok: true, err: String(e.message).slice(0, 50) }));
        }
        """
        result = _node_run(script)
        assert result.returncode == 0, f"stderr={result.stderr}"
        out = json.loads(result.stdout.strip())
        assert out["ok"] is True
        assert "Lock acquire timeout" in out["err"]
    ```

    All tests use the auto-cleanup fixture so a leftover `data/.lock` from a previous test does NOT pollute the next. Tests run in `~5-10s` total (each spawns a Node subprocess).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_lockfile_unit.py -v --tb=short 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_orchestration/test_lockfile_unit.py` exits 0
    - `grep -c "def test_" tests/test_orchestration/test_lockfile_unit.py` returns at least 6
    - `grep -c "def test_acquire_then_release_cycles_cleanly" tests/test_orchestration/test_lockfile_unit.py` returns 1
    - `grep -c "def test_isstale_returns_true_for_lock_older_than_60s" tests/test_orchestration/test_lockfile_unit.py` returns 1
    - `grep -c "def test_isstale_returns_true_for_null_or_corrupt_lock" tests/test_orchestration/test_lockfile_unit.py` returns 1
    - `grep -c "def test_acquirelock_overwrites_stale_lock" tests/test_orchestration/test_lockfile_unit.py` returns 1
    - `grep -c "def test_releaselock_does_not_delete_other_process_lock" tests/test_orchestration/test_lockfile_unit.py` returns 1
    - `grep -c "def test_withlock_releases_on_throw" tests/test_orchestration/test_lockfile_unit.py` returns 1
    - `grep -c "def test_acquirelock_times_out_against_fresh_lock" tests/test_orchestration/test_lockfile_unit.py` returns 1
    - `pytest tests/test_orchestration/test_lockfile_unit.py -v 2>&1 | grep -E '(passed|failed|error)' | tail -1` shows "7 passed" (or whatever the actual count, but zero failed and zero errors)
  </acceptance_criteria>
  <done>
    All 7+ unit tests pass; lockfile mechanics fully exercised (acquire/release/stale/race/throw/timeout); zero failures.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero regression + lint hygiene</name>
  <files>(verification only)</files>
  <action>
    1. Full pytest suite: at least 432 + 7 (Wave 1 unit tests) = 439 passed; xfailed unchanged at >=8 (Wave 0's 7 stubs + Phase 5's 1 strict xfail).
    2. mypy --strict on tests/test_orchestration/test_lockfile_unit.py.
    3. ruff check + ruff format --check on tests/test_orchestration/.
    4. Manual sanity check: leave NO data/.lock on disk after all tests run.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest -q 2>&1 | tail -3 && mypy --strict tests/test_orchestration/test_lockfile_unit.py && ruff check tests/test_orchestration/ && ruff format --check tests/test_orchestration/ && test ! -f data/.lock && echo "no leftover lock"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows >= 439 (432 prior + 7 new lockfile tests)
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ failed' | head -1` returns no output OR "0 failed"
    - `mypy --strict tests/test_orchestration/test_lockfile_unit.py` exits 0
    - `ruff check tests/test_orchestration/` exits 0
    - `ruff format --check tests/test_orchestration/` exits 0
    - `test ! -f data/.lock` exits 0 (no leftover lockfile after suite completes)
  </acceptance_criteria>
  <done>
    Full suite green; lint clean; no lockfile leak.
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS:**

- **D-01-01: writeFileSync(flag:'w') + read-back, NOT flag:'wx' (O_EXCL)** — rationale: per PATTERNS Critical Issue 1, the existing stale lock would be on disk and 'wx' would crash on every acquire. Career-ops chose flag:'w' deliberately because the code intentionally OVERWRITES stale locks (`if (!existing || isStale(existing))`). Rule-of-three citation: career-ops/scripts/lockfile.mjs:42 uses flag:'w'; PATTERNS Critical Issue 1 says "keep the flag:'w' + read-back idiom"; RESEARCH §Pitfall 2 confirms flag:'w' is the v1 acceptable choice.

- **D-01-02: Stale check is acquired_at-based (JSON content), NOT mtime-based** — rationale: per PATTERNS Critical Issue 1, mtime is vulnerable to filesystem `touch` and clock-skew between fs-clock and process-clock. JSON-content timestamp is set deterministically by the writer. Rule-of-three citation: career-ops/scripts/lockfile.mjs:28-32 uses `Date.now() - lock.acquired_at`; PATTERNS Critical Issue 1 finding 3 confirms; RESEARCH §c locks the threshold at 60_000.

- **D-01-03: Lock filename is `.lock` (NOT `.mortgage-ops.duckdb.lock`)** — rationale: spawn message mandates `data/.lock`; PATTERNS line 100-103 cites DATA_CONTRACT.md line 22 implying `.lock` filename; brevity matches mortgage-ops convention (career-ops uses `.career-ops.lock` because it has multiple lock-targets in the future). Rule-of-three citation: spawn-message constraint #1 of "Important constraints" section; PATTERNS Pattern Assignments lockfile section line 59 ("`.career-ops.lock`" -> "`.lock`"); RESEARCH §Recommended Project Structure line 165 (note the conflict: RESEARCH suggests `.mortgage-ops.duckdb.lock` but DATA_CONTRACT and spawn message win — see Rule-1 below).

- **D-01-04: Lockfile path resolution via `dirname(dirname(fileURLToPath(import.meta.url)))`** — rationale: lockfile.mjs lives at `orchestration/`, repo root is one dirname up; pattern lifted verbatim from career-ops where scripts/ is one dirname up from career-ops root. Rule-of-three citation: career-ops/scripts/lockfile.mjs:7-8 uses identical pattern; init-db.mjs (Wave 2) will use identical pattern; db-write.mjs (Wave 3) will use identical pattern.

- **D-01-05: STALE_THRESHOLD_MS = 60_000 is non-negotiable** — rationale: ROADMAP SC-3 explicitly says "Stale lockfile recovery triggers at 60s"; this is a contract with downstream tests. Rule-of-three citation: ROADMAP.md:182 (SC-3); REQUIREMENTS.md PERS-04; PATTERNS line 59.
</locked_decisions>

<verify_block>
**Verify Block:**

```bash
# 1. lockfile.mjs exists and parses
test -f orchestration/lockfile.mjs && node --check orchestration/lockfile.mjs && echo "syntax OK"

# 2. All 5 exports present
for sym in withLock acquireLock releaseLock isStale readLock; do
  count=$(grep -c "export.*$sym" orchestration/lockfile.mjs)
  [ "$count" -eq 1 ] && echo "$sym: exported" || echo "$sym: MISSING"
done

# 3. Critical Issue 1 discipline preserved
grep -c "writeFileSync.*flag.*'w'" orchestration/lockfile.mjs  # MUST return 1
grep -c "flag.*'wx'" orchestration/lockfile.mjs                # MUST return 0

# 4. Rename complete
grep -c "CAREER_OPS" orchestration/lockfile.mjs   # MUST return 0
grep -c "MORTGAGE_OPS" orchestration/lockfile.mjs # MUST return >=2

# 5. Lock filename
grep -c "'.lock'" orchestration/lockfile.mjs  # MUST return 1

# 6. Stale threshold pinned
grep -c "STALE_THRESHOLD_MS = 60_000" orchestration/lockfile.mjs  # MUST return 1

# 7. Unit tests all pass
pytest tests/test_orchestration/test_lockfile_unit.py -v --tb=short 2>&1 | tail -3

# 8. Full suite green
pytest -q 2>&1 | tail -3

# 9. Lint hygiene
mypy --strict tests/test_orchestration/test_lockfile_unit.py
ruff check tests/test_orchestration/
ruff format --check tests/test_orchestration/

# 10. No leftover lockfile after suite
test ! -f data/.lock && echo "no leftover lock"
```
</verify_block>

<deviation_rules>
**Deviation Rules:**

- **Rule-1 (RESEARCH vs spawn-message conflict on lock filename):** RESEARCH.md line 165 suggests `data/.mortgage-ops.duckdb.lock`; spawn message + DATA_CONTRACT.md cross-reference imply `data/.lock`. The locked decision (D-01-03) is `.lock` per spawn message. If the executor sees evidence that this is wrong (e.g., a future Phase introduces multiple .lock files needing namespace), STOP and surface as a CONTEXT-level revision, not an executor-level rename.

- **Rule-2 (port verbatim, do not refactor):** career-ops/scripts/lockfile.mjs is the canonical reference. Even if a reading uncovers what looks like a bug or improvement opportunity (e.g., "we should use `flock(2)` instead"), DO NOT refactor — port verbatim. Improvements are PATTERNS-level decisions for a future phase. The race window is documented and accepted (PATTERNS Critical Issue 1 finding 1).

- **Rule-3 (hygiene-only deviations are OK):** If `node --check` surfaces a stylistic warning (e.g., trailing semicolons), the executor may apply the minimal fix and document it in SUMMARY.md as a Rule-3 deviation. Likewise for ruff format auto-fixes on the Python test file.
</deviation_rules>

<dependencies>
**Dependencies:**

- **Depends on:** Plan 09-00 (test infrastructure) — uses tests/test_orchestration/ package marker.
- **Blocks:** Plan 09-02 (init-db.mjs uses the orchestration/ directory created here, but does not import lockfile.mjs directly — init-db is a one-shot script). Plan 09-03 (db-write.mjs imports `withLock` from this file). Plan 09-06 (concurrency tests exercise lockfile via db-write.mjs).
- **No external dependencies:** This plan does NOT install npm packages; it uses only Node built-ins (fs, path, url). Wave 2 ships package.json + duckdb-async install.
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Two concurrent Node processes -> data/.lock | Race window between read and write per Critical Issue 1; mitigated by read-back-and-verify |
| Stale lock from crashed prior run -> next acquireLock | Mitigated by 60s acquired_at-based stale recovery |
| Other process's lock -> releaseLock | Mitigated by pid + acquired_at match check before unlinkSync |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-05 | Tampering (race window in acquireLock) | writeFileSync without O_EXCL | accept | Documented in PATTERNS Critical Issue 1; DuckDB's own OS file lock is the second line of defense; SC-2 verifies end-state correctness, not which writer wins |
| T-09-06 | Denial of Service (stale lock blocks all writes forever) | LOCK_PATH on disk after crash | mitigate | 60s STALE_THRESHOLD_MS; isStale check on every acquireLock loop iteration |
| T-09-07 | Tampering (process A unlinks process B's lock) | releaseLock | mitigate | pid + acquired_at match check before unlinkSync |
| T-09-08 | Information Disclosure (lockfile content reveals PIDs of other processes) | data/.lock contents | accept | Single-user desktop tool; data/ is User Layer per DATA_CONTRACT.md; no privilege boundary |
</threat_model>

<verification>
- orchestration/lockfile.mjs ports career-ops verbatim with 3 renames (CAREER_OPS, .career-ops.lock, header)
- node --check parses cleanly
- All 5 exports present (withLock, acquireLock, releaseLock, isStale, readLock)
- writeFileSync flag:'w' discipline preserved (NOT 'wx'); STALE_THRESHOLD_MS = 60_000
- 7+ unit tests pass; cover acquire/release/stale/race/throw/timeout/null-handling
- Full pytest suite >= 439 passed; zero regression to Phase 5 baseline
- mypy + ruff clean; no leftover data/.lock after suite
</verification>

<success_criteria>
- orchestration/lockfile.mjs exists at ~80 lines, ports career-ops verbatim
- 7+ unit tests in tests/test_orchestration/test_lockfile_unit.py all pass
- Phase 5 baseline preserved (>=432 passed); new total >=439 passed
- mypy --strict + ruff format clean
- Wave 2 (init-db.mjs) and Wave 3 (db-write.mjs) can import withLock from this file
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-01-SUMMARY.md` documenting:
- orchestration/lockfile.mjs line count and the three renames applied
- Unit test count (must be >= 7) and coverage (acquire/release/stale/race/throw/timeout)
- Pass count delta (Phase 5 baseline 432 -> Phase 9 Wave 1 baseline >= 439)
- mypy + ruff status
- Confirmation that withLock is ready for Wave 3 db-write.mjs to import
</output>
</content>
</invoke>