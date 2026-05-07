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
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

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
        check=False,
    )


@pytest.fixture(autouse=True)
def _cleanup_lock() -> Iterator[None]:
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
        json.dumps(
            {"pid": 99999, "acquired_at": stale_acquired_at, "reason": "stale-fixture"},
            indent=2,
        )
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
    other_lock = {
        "pid": 99999,
        "acquired_at": int(time.time() * 1000),
        "reason": "other-process",
    }
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
    fresh = {
        "pid": 99999,
        "acquired_at": int(time.time() * 1000),
        "reason": "blocker",
    }
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
