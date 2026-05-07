"""Phase 9 DuckDB orchestration — lockfile semantics (PERS-04).

Wave 1 (Plan 09-01) ships orchestration/lockfile.mjs with 60s stale
recovery. Wave 6 (Plan 09-06) flips this stub to a real fixture-based
assertion that pre-creates a synthetic stale lock and verifies reclaim.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub - Plan 09-06 ships stale-lockfile-recovery test"
)
def test_stale_lockfile_reclaimed_after_60s(tmp_path: Path) -> None:
    """PERS-04 + ROADMAP SC-3: a pre-existing lockfile with acquired_at
    more than 60s ago is reclaimed by a fresh writer. Test pre-creates
    data/.lock with acquired_at=Date.now()-65000, then invokes
    `db-write.mjs insert-loan` and asserts:
    1. exit code 0 (write succeeded; stale lock was reclaimed)
    2. lockfile released after the write completes (no leak)
    Per PATTERNS Critical Issue 1: stale check is acquired_at-based, NOT
    mtime-based; test still sets mtime as belt-and-suspenders.
    """
    pytest.fail("Wave 0 stub")
