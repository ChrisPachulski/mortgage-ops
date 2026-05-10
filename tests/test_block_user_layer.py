"""Tests for scripts/hooks/block-user-layer.py — FND-10 enforcement.

Every assertion includes the expected behavior and why.

Coverage:
  - Rejects each USER_LAYER_PATTERN (config/household.yml, profile.yml, modes/_profile.md)
  - Rejects any reports/ path except reports/.gitkeep
  - Rejects any *.duckdb, *.duckdb-wal, *.duckdb-shm
  - Accepts data/reference/.gitkeep, reports/.gitkeep (whitelist)
  - Accepts unrelated System Layer paths (lib/money.py, pyproject.toml, etc.)
  - Accepts config/household.example.yml (committed example)
  - main() exit codes: 0 for clean staging, 1 for any User Layer offender
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the hook script as a module despite the kebab-case filename.
_HOOK_PATH = Path(__file__).resolve().parent.parent / "scripts" / "hooks" / "block-user-layer.py"
_spec = importlib.util.spec_from_file_location("_block_user_layer", _HOOK_PATH)
assert _spec is not None
assert _spec.loader is not None
_block_user_layer = importlib.util.module_from_spec(_spec)
sys.modules["_block_user_layer"] = _block_user_layer
_spec.loader.exec_module(_block_user_layer)

is_user_layer = _block_user_layer.is_user_layer
main = _block_user_layer.main


@pytest.mark.parametrize(
    "path",
    [
        "config/household.yml",
        "config/profile.yml",
        "modes/_profile.md",
        ".claude/skills/mortgage-ops/modes/_profile.md",
    ],
)
def test_user_layer_pattern_paths_are_blocked(path: str) -> None:
    assert is_user_layer(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "reports/2026-04-26-my-loan.md",
        "reports/100-something.md",
    ],
)
def test_reports_directory_is_blocked(path: str) -> None:
    assert is_user_layer(path) is True


def test_reports_gitkeep_is_whitelisted() -> None:
    assert is_user_layer("reports/.gitkeep") is False


def test_data_reference_gitkeep_is_whitelisted() -> None:
    assert is_user_layer("data/reference/.gitkeep") is False


@pytest.mark.parametrize(
    "path",
    [
        "data/mortgage-ops.duckdb",
        "data/mortgage-ops.duckdb-wal",
        "data/mortgage-ops.duckdb-shm",
        "data/anything.duckdb",
    ],
)
def test_duckdb_files_are_blocked(path: str) -> None:
    assert is_user_layer(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "lib/money.py",
        "lib/models.py",
        "tests/test_money.py",
        "pyproject.toml",
        "uv.lock",
        ".gitignore",
        ".github/workflows/ci.yml",
        ".pre-commit-config.yaml",
        "DATA_CONTRACT.md",
        "README.md",
        "config/household.example.yml",
        "config/profile.example.yml",
        "scripts/hooks/block-user-layer.py",
    ],
)
def test_system_layer_paths_are_allowed(path: str) -> None:
    assert is_user_layer(path) is False


def test_main_exits_zero_with_no_offenders() -> None:
    rc = main(["scripts/hooks/block-user-layer.py", "lib/money.py", "pyproject.toml"])
    assert rc == 0


def test_main_exits_one_with_user_layer_offender() -> None:
    rc = main(["scripts/hooks/block-user-layer.py", "config/household.yml"])
    assert rc == 1


def test_main_exits_one_when_offender_mixed_with_clean_paths() -> None:
    rc = main(
        [
            "scripts/hooks/block-user-layer.py",
            "lib/money.py",
            "config/profile.yml",  # offender
            "pyproject.toml",
        ]
    )
    assert rc == 1
