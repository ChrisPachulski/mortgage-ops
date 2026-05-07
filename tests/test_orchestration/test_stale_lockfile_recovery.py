"""Phase 9 stale-lockfile recovery test (PERS-04 + ROADMAP SC-3).

SC-3: stale lockfile recovery triggers at 60s. The test pre-creates a
lockfile with `acquired_at` = now - 65000 ms (5s margin past the 60s
threshold to avoid clock-skew flakes), then invokes db-write.mjs and
asserts the write succeeds (the writer reclaimed the stale lock).

Per Plan 09-01 D-01-01: the lockfile lives at the FIXED path
`data/.lock` under repo root, NOT a sibling of the DB.
Per Plan 09-01 D-01-02: stale recovery is acquired_at-based (JSON
content), NOT mtime-based. The test sets BOTH the JSON acquired_at
field and the file mtime as belt-and-suspenders, but only the JSON
field is LOAD-BEARING per the lockfile.mjs::isStale() implementation.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import TYPE_CHECKING

import pytest

from tests.conftest import REPO_ROOT, node_orchestration_run

if TYPE_CHECKING:
    from pathlib import Path

# Stale threshold per Plan 09-01 D-02 / RESEARCH line 17 + 584
STALE_THRESHOLD_SECONDS = 60
# Margin past threshold to avoid clock-skew flakes (RESEARCH line 602: 65s)
STALE_AGE_SECONDS = 65

# Fixed lockfile path (Plan 09-01 D-01-01: data/.lock under repo root)
LOCKFILE: Path = REPO_ROOT / "data" / ".lock"


@pytest.mark.timeout(
    60
)  # Warning #4 / D-06-09: 1.5x worst-case (30s db-write + 10s pre-flight + margin)
def test_stale_lockfile_reclaimed_after_60s_threshold(tmp_path: Path) -> None:
    """PERS-04 + ROADMAP SC-3: a pre-existing lockfile with acquired_at > 60s
    is reclaimed by a fresh db-write.mjs invocation; the write proceeds
    normally and the lockfile is released after."""
    db_path = tmp_path / "test_stale.duckdb"

    # Cleanup: ensure no leftover lockfile from prior tests (defensive)
    if LOCKFILE.exists():
        LOCKFILE.unlink()

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
    LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    LOCKFILE.write_text(
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
    os.utime(LOCKFILE, (sixty_five_s_ago, sixty_five_s_ago))

    # Sanity: lockfile is in place before the writer runs
    assert LOCKFILE.exists(), f"failed to pre-create stale lockfile at {LOCKFILE}"

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
        check=False,
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
    assert not LOCKFILE.exists(), (
        f"Lockfile leaked after stale-recovery: {LOCKFILE} still exists. "
        f"Indicates releaseLock was skipped after the reclaim."
    )


@pytest.mark.timeout(30)  # Warning #4 / D-06-09: 2x subprocess timeout=15
def test_fresh_lockfile_under_60s_blocks_or_waits(tmp_path: Path) -> None:
    """Negative companion: a FRESH lockfile (acquired_at < 60s) MUST NOT be
    reclaimed — it represents an active writer. The new writer must
    wait, fail-fast with a lock-busy error, or otherwise refuse to
    proceed within a short timeout window. This guards the SC-3 threshold
    from regressing to '0s' (which would silently break SC-2)."""
    db_path = tmp_path / "test_fresh.duckdb"

    # Cleanup: any leftover lockfile from prior tests
    if LOCKFILE.exists():
        LOCKFILE.unlink()

    init = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert init.returncode == 0, f"init failed: {init.stderr}"

    # Pre-create a FRESH lockfile (acquired_at = 5s ago, well under 60s)
    fresh_ms = int((time.time() - 5) * 1000)
    LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    LOCKFILE.write_text(
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
    os.utime(LOCKFILE, (five_s_ago, five_s_ago))

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
    try:
        result = node_orchestration_run(
            "orchestration/db-write.mjs",
            "insert-loan",
            "--json",
            str(fx),
            db_path=db_path,
            timeout=15,
        )
        # The fresh lock must NOT be silently reclaimed (that would break SC-2).
        # Acceptable: writer fails fast (returncode != 0) OR writer times out
        # (caught by the except below). NOT acceptable: writer succeeds
        # (returncode == 0) — that proves the threshold collapsed below 60s.
        assert result.returncode != 0, (
            f"PERS-04 violation: writer reclaimed a 5s-old lockfile — the "
            f"60s threshold has degraded. This silently breaks SC-2 (parallel "
            f"writers no longer serialize). stderr={result.stderr}"
        )
    except subprocess.TimeoutExpired:
        # Acceptable: writer is waiting for the lock to release (polling).
        # That is the expected behavior in the polling-with-timeout pattern.
        pass
    finally:
        # Cleanup — remove the fresh lockfile we planted (writer didn't release
        # it because it never owned it).
        if LOCKFILE.exists():
            LOCKFILE.unlink()
