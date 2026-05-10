#!/usr/bin/env python3
"""Pre-commit hook: refuse to commit any User Layer file.

User Layer is defined in DATA_CONTRACT.md and contains the user's PII / customizations.
This hook is the enforcement mechanism for FND-10. .gitignore (FND-08) is the first
layer; this hook catches `git add -f` bypasses of .gitignore as the second layer.

The USER_LAYER_PATTERNS, USER_LAYER_GLOB_DIRS, and ALLOWED_KEEP_FILES tuples must
match the User Layer table in DATA_CONTRACT.md exactly. Both lists are kept in sync
by editing this file and DATA_CONTRACT.md in the same commit.
"""

from __future__ import annotations

import sys

# Exact paths that are NEVER allowed in a commit.
USER_LAYER_PATTERNS: tuple[str, ...] = (
    "config/household.yml",
    "config/profile.yml",
    "modes/_profile.md",
    ".claude/skills/mortgage-ops/modes/_profile.md",
    # DuckDB and reports are gitignored, but block them as belt-and-suspenders
    # in case .gitignore is ever bypassed with `git add -f`.
)
# Path-prefix matches (any file under these directories is User Layer).
USER_LAYER_GLOB_DIRS: tuple[str, ...] = (
    "reports/",  # any file under reports/ except entries in ALLOWED_KEEP_FILES
)
# Whitelist: these specific paths under glob dirs ARE allowed.
ALLOWED_KEEP_FILES: frozenset[str] = frozenset({"reports/.gitkeep", "data/reference/.gitkeep"})
# Suffix block (DuckDB main + sidecars).
DATA_DUCKDB_SUFFIXES: tuple[str, ...] = (".duckdb", ".duckdb-wal", ".duckdb-shm")


def is_user_layer(path: str) -> bool:
    """Return True if `path` is a User Layer file that must not be committed."""
    if path in ALLOWED_KEEP_FILES:
        return False
    if path in USER_LAYER_PATTERNS:
        return True
    if any(path.startswith(d) for d in USER_LAYER_GLOB_DIRS):
        return True
    return any(path.endswith(s) for s in DATA_DUCKDB_SUFFIXES)


def main(argv: list[str]) -> int:
    """Pre-commit invokes this with `argv[0] == script` and `argv[1:]` = staged paths."""
    offenders = [a for a in argv[1:] if is_user_layer(a)]
    if not offenders:
        return 0
    print(
        "ERROR: refusing to commit User Layer files (DATA_CONTRACT.md):",
        file=sys.stderr,
    )
    for o in offenders:
        print(f"  - {o}", file=sys.stderr)
    print(
        "\nThese paths are User Layer per DATA_CONTRACT.md and must never be committed.\n"
        "If this is a mistake (e.g. you intended to commit `config/household.example.yml`),\n"
        "double-check the path. The example file is committable; the live file is not.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
