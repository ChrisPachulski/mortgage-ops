"""Repo-hygiene guards. Catches accumulated workspace cruft before it ships.

Phase 17 post-review: macOS Finder's drag-copy creates duplicates like
``foo 2.py``, ``.lock 3``, etc. These pollute pytest collection (the new
``foo 2.py`` is treated as a real test module) and broke the suite in
review. The .gitignore catches most of these proactively; this test is the
defensive belt-and-suspenders.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Matches "<base> <digit>.<ext>" anywhere in the path — the exact pattern
# Finder produces. Also matches " copy.<ext>" which is the alternative form.
_FINDER_DUP_RE = re.compile(r" (?:\d+|copy)\.[A-Za-z0-9]+$")

# Directories that legitimately contain space-separated names (none right now,
# but the allow-list is here for future use).
_ALLOW_DIRS: frozenset[Path] = frozenset()


def _is_ignored(path: Path) -> bool:
    """Skip directories that are not part of the working tree we care about."""
    parts = path.parts
    skip = {".venv", "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git"}
    return any(p in skip for p in parts)


def test_no_finder_style_duplicates_in_working_tree() -> None:
    offenders: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if _is_ignored(path):
            continue
        if path in _ALLOW_DIRS:
            continue
        if _FINDER_DUP_RE.search(path.name):
            offenders.append(path.relative_to(PROJECT_ROOT))

    assert not offenders, (
        "Finder-style drag-copy duplicates found in working tree. "
        "These accidentally get collected by pytest and break the suite. "
        "Delete them manually:\n  " + "\n  ".join(str(p) for p in offenders)
    )
