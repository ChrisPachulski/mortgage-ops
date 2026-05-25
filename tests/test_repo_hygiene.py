"""Repo-hygiene guards.

Phase 17 post-review: macOS Finder's drag-copy creates duplicates like
``foo 2.py``, ``.lock 3``, etc. When the duplicate is a source or test file,
pytest collects it as a real test module and breaks the suite. The
.gitignore catches most cases proactively; this test is the defensive
belt-and-suspenders, scoped to the directories pytest actually collects from
(source + tests).

Generated/ephemeral directories (``.codex-loop/``, ``data/cache/``,
``data/logs/``, ``reports/``, ``__pycache__/``, etc.) are intentionally
excluded — duplicates there are filesystem noise, not a correctness risk, and
shouldn't fail CI.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Matches "<base> <digit>.<ext>" anywhere in the path — the exact pattern
# Finder produces. Also matches " copy.<ext>" which is the alternative form.
_FINDER_DUP_RE = re.compile(r" (?:\d+|copy)\.[A-Za-z0-9]+$")

# Directory names anywhere in a path that disqualify it from the scan.
# Includes (a) tool caches, (b) virtualenvs / node_modules, (c) generated
# data layers (DATA_CONTRACT.md), and (d) report/log/eval output trees.
_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".codex-loop",
        ".git",
        ".venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "__pycache__",
        # Generated data layer (DATA_CONTRACT.md) — ephemeral artifacts.
        "cache",  # data/cache/ — fetcher caches (HTML, JSON sidecars)
        "logs",  # data/logs/ — per-run observability JSONL
        "property-listings",  # data/property-listings/ — Phase 15 sidecars
        "market",  # data/market/ — generated parquet
        # Report + eval output trees.
        "reports",
        "runs",  # evals/runs/
    }
)


def _is_in_skipped_tree(path: Path) -> bool:
    """True if any path component is a skipped directory name."""
    return any(part in _SKIP_DIR_NAMES for part in path.parts)


def test_no_finder_style_duplicates_in_source_or_tests() -> None:
    """Scan source + test trees for Finder-style drag-copy duplicates.

    Scope is intentionally narrow: only directories pytest collects from or
    that ship as source. Generated/ephemeral trees (data/cache, data/logs,
    reports/, __pycache__, etc.) are excluded — duplicates there are
    filesystem noise, not a pytest-collection hazard.
    """
    offenders: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if _is_in_skipped_tree(path):
            continue
        if _FINDER_DUP_RE.search(path.name):
            offenders.append(path.relative_to(PROJECT_ROOT))

    assert not offenders, (
        "Finder-style drag-copy duplicates found in a source or test tree. "
        "When pytest collects a duplicated test_*.py it can break the suite. "
        "Delete them manually:\n  " + "\n  ".join(str(p) for p in offenders)
    )
