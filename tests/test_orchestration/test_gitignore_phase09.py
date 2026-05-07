"""Phase 9 .gitignore regression test (Plan 09-07).

Two complementary mechanisms:

1. Line-presence: assert specific Phase 9 entries appear in .gitignore.
   Catches accidental deletion.
2. Behavioral: invoke `git check-ignore` on representative paths; assert
   each path's ignore status matches its DATA_CONTRACT layer rule.
   Catches over-broad-wildcard regressions (e.g., someone replaces
   explicit per-file lines with `data/*` which would silently un-track
   data/known-loans.yml — Plan 09-05 D-05-01 violation).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from tests.conftest import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

GITIGNORE: Path = REPO_ROOT / ".gitignore"

# Line-presence assertions (Phase 9 additions per Plan 09-07 D-02)
REQUIRED_GITIGNORE_LINES: tuple[str, ...] = (
    "data/.mortgage-ops.duckdb.lock",
    "data/.lock",
)


def _git_check_ignore(path: str) -> int:
    """Invoke `git check-ignore` from REPO_ROOT; return the exit code.
    Exit 0 = path IS ignored. Exit 1 = path is NOT ignored.
    """
    result = subprocess.run(
        ["git", "check-ignore", path],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode


def test_gitignore_phase09_entries_present() -> None:
    """Plan 09-07 D-02: explicit per-file lockfile entries appear in
    .gitignore. Catches accidental deletion."""
    assert GITIGNORE.exists(), f".gitignore not found at {GITIGNORE}"
    content = GITIGNORE.read_text()

    for line in REQUIRED_GITIGNORE_LINES:
        assert line in content, (
            f"Plan 09-07 violation: .gitignore is missing required Phase 9 "
            f"entry {line!r}; ephemeral lockfile would leak into git status. "
            f"See RESEARCH Pitfall 5."
        )


def test_gitignore_known_loans_NOT_ignored() -> None:
    """Plan 09-05 D-05-01 + DATA_CONTRACT.md line 67: data/known-loans.yml
    is Reference Layer and MUST be committed. An over-broad `data/*`
    wildcard in .gitignore would silently un-track it, breaking Phase 10
    and Phase 12 product routing.
    """
    rc = _git_check_ignore("data/known-loans.yml")
    assert rc == 1, (
        f"Plan 09-05 D-05-01 violation: data/known-loans.yml is being "
        f"ignored by git (check-ignore exit {rc}). Likely cause: an "
        f"over-broad `data/*` wildcard in .gitignore. Fix: replace with "
        f"explicit per-file lines OR add `!data/known-loans.yml` whitelist."
    )


def test_gitignore_duckdb_file_IS_ignored() -> None:
    """DATA_CONTRACT.md line 50: data/mortgage-ops.duckdb is Data Layer
    (gitignored). Existing Phase 1 rule `data/*.duckdb` covers this."""
    rc = _git_check_ignore("data/mortgage-ops.duckdb")
    assert rc == 0, (
        f"data/mortgage-ops.duckdb is NOT ignored (check-ignore exit {rc}); "
        f"Data Layer file is at risk of accidental commit. Likely cause: "
        f"the Phase 1 `data/*.duckdb` line was removed from .gitignore."
    )


def test_gitignore_lockfile_IS_ignored() -> None:
    """Plan 09-07 D-02 + RESEARCH Pitfall 5: data/.mortgage-ops.duckdb.lock
    is ephemeral writer state and MUST be ignored to prevent stale locks
    being committed (which would block CI for 60s on every clone)."""
    rc = _git_check_ignore("data/.mortgage-ops.duckdb.lock")
    assert rc == 0, (
        f"data/.mortgage-ops.duckdb.lock is NOT ignored "
        f"(check-ignore exit {rc}); ephemeral lockfile is at risk of "
        f"being committed. Plan 09-07 Task 2 missed adding this entry."
    )


def test_gitignore_reports_seam_preserved() -> None:
    """Phase 1 invariant: reports/.gitkeep MUST be tracked (it preserves
    the empty reports/ directory in git); reports/*.md MUST be ignored
    (generated artifacts)."""
    rc_keeper = _git_check_ignore("reports/.gitkeep")
    assert rc_keeper == 1, (
        f"reports/.gitkeep is being ignored (check-ignore exit {rc_keeper}); "
        f"the seam file would be lost on next clone. Likely cause: the "
        f"`!reports/.gitkeep` whitelist line was removed from .gitignore."
    )

    rc_report = _git_check_ignore("reports/sample-report.md")
    assert rc_report == 0, (
        f"reports/sample-report.md is NOT ignored "
        f"(check-ignore exit {rc_report}); generated user reports could "
        f"leak into git. Likely cause: the `reports/*` Phase 1 line was "
        f"removed from .gitignore."
    )


def test_gitignore_no_bare_data_wildcard() -> None:
    """Defensive guard: a bare `data/*` line would un-track
    data/known-loans.yml. Plan 09-07 D-02 explicitly forbids this pattern.
    Reading .gitignore as text and grepping for the exact pattern.
    """
    content = GITIGNORE.read_text()
    # Match a line that is exactly `data/*` (with optional surrounding whitespace)
    # but NOT `data/*.duckdb` or `data/*.parquet` (which are scoped).
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "data/*":
            raise AssertionError(
                "Plan 09-07 D-02 violation: .gitignore contains a bare "
                "`data/*` wildcard line. This silently un-tracks "
                "data/known-loans.yml (Reference Layer). Use explicit "
                "per-file lines instead, or add `!data/known-loans.yml` "
                "whitelist."
            )
