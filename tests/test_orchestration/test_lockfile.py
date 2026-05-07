"""Phase 9 DuckDB orchestration — lockfile semantics (PERS-04).

Wave 1 (Plan 09-01) ships orchestration/lockfile.mjs with 60s stale
recovery. Wave 6 (Plan 09-06) flips this stub via thin-wrapper delegation
to the full implementation in test_stale_lockfile_recovery.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_stale_lockfile_reclaimed_after_60s(tmp_path: Path) -> None:
    """PERS-04 + ROADMAP SC-3: stale lockfile (acquired_at > 60s) is
    reclaimed by next writer. This is the Wave 0 stub flipped by Plan
    09-06; the full implementation lives in
    tests/test_orchestration/test_stale_lockfile_recovery.py
    (test_stale_lockfile_reclaimed_after_60s_threshold)."""
    from tests.test_orchestration.test_stale_lockfile_recovery import (
        test_stale_lockfile_reclaimed_after_60s_threshold,
    )

    test_stale_lockfile_reclaimed_after_60s_threshold(tmp_path)
