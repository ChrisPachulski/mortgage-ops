"""Phase 9 parallel-writer concurrency test (PERS-05 + ROADMAP SC-2).

SC-2: `node orchestration/db-write.mjs --insert-loan --json fixtures/loan.json`
writes through withLock() and a concurrent second invocation either waits
or fails fast (no DB corruption).

Test strategy: spawn two `subprocess.Popen` calls back-to-back; wait for
both; assert (a) the lockfile race did not corrupt the DB (final SELECT
count = baseline + successes with both inserts persisted), (b) the lockfile
is released after both processes complete (no leak).

Race window per RESEARCH Pitfall 2: the read-then-write lockfile pattern
has a small race window. Either outcome is valid: both succeed (typical
case — DuckDB's OS file lock is the second line of defense), or one fails
fast with a lock-timeout error and exits non-zero. The test tolerates
both as long as the FINAL STATE is correct.

Note on lockfile path: orchestration/lockfile.mjs uses a FIXED
`data/.lock` path (Plan 09-01 — NOT sibling-of-DB). All test invocations
target the same lockfile under data/.lock regardless of MORTGAGE_OPS_DB_PATH.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.conftest import REPO_ROOT, node_orchestration_run

if TYPE_CHECKING:
    from pathlib import Path

# Lockfile path is fixed by orchestration/lockfile.mjs: data/.lock under
# the repo root, NOT a sibling of the DB. Wave-1 D-01-01.
LOCKFILE: Path = REPO_ROOT / "data" / ".lock"


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


@pytest.mark.timeout(
    90
)  # Warning #4 / D-06-09: 1.5x subprocess wait(timeout=60); pytest-timeout safety net
def test_parallel_inserts_serialize_via_lockfile(tmp_path: Path) -> None:
    """PERS-05 + ROADMAP SC-2: two parallel `node db-write.mjs insert-loan`
    invocations either both succeed (one waits) or exactly one fails fast
    with a lock-timeout error. Either way, the DB is not corrupted: final
    loan count equals baseline + (number of successful inserts), and the
    lockfile is released after the dust settles."""
    db_path = tmp_path / "test_parallel.duckdb"

    # Pre-cleanup: any leftover lockfile from a prior crashed test run
    if LOCKFILE.exists():
        LOCKFILE.unlink()

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
    assert not LOCKFILE.exists(), (
        f"Lockfile leaked: {LOCKFILE} still exists after both writers exited. "
        f"Indicates releaseLock was skipped (likely a finally-block bug in lockfile.mjs)."
    )
