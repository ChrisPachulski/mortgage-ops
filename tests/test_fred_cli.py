"""Phase 12 Wave-1 live tests for .claude/skills/mortgage-ops/scripts/fred_cli.py.

LIVE-01 + LIVE-04 closed: HTTP wrapper canonical path per D-12-LIVE01-01.
Always-exit-0 envelope per Pitfall 1 + D-12-LIVE02-01 recovery contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "fred_cli.py"
)
"""Phase 12 ships fred_cli.py directly into .claude/skills/mortgage-ops/scripts/
(no project-root -> skill-folder relocation pass — D-12-LIVE01-01 + RESEARCH
§Architectural Responsibility Map). Mirrors Phase 10-relocated SCRIPT_PATH
pattern in tests/test_amortize.py."""

ALL_SERIES = ("MORTGAGE30US", "MORTGAGE15US")
"""Allowlist per RESEARCH §Security Domain V5 - reject other series_id values
to defend against URL parameter injection."""


def test_fred_cli_script_exists() -> None:
    """LIVE-01: scripts/fred_cli.py must exist at .claude/skills/mortgage-ops/scripts/."""
    assert SCRIPT_PATH.is_file(), f"missing {SCRIPT_PATH}"


def test_fred_cli_help_fast_lazy_imports() -> None:
    """LIVE-01: --help must complete in <300ms (lazy-import of urllib + lib.fred_cache
    after argparse)."""
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert elapsed < 0.3, f"--help took {elapsed:.3f}s; D-18 lazy-import discipline violated"


def test_fred_cli_missing_api_key_returns_exit_0_with_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LIVE-01 + Pitfall 1: missing FRED_API_KEY -> exit 0 + JSON envelope with `error` field.

    Diverges from amortize.py exit-2 pattern: SKILL.md prose-only injection per
    D-12-LIVE02-01 requires the recovery contract to be the envelope's `error` field,
    not a non-zero exit.
    """
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "MORTGAGE30US", "--latest"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0  # NOT 2 — see D-12-LIVE02-01 recovery contract
    envelope = json.loads(result.stdout)
    assert envelope["value"] is None
    assert envelope["error"] is not None
    assert "FRED_API_KEY" in envelope["error"]


@pytest.mark.parametrize("series_id", ALL_SERIES)
def test_fred_cli_supports_both_series(series_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """LIVE-04: MORTGAGE15US must be accepted alongside MORTGAGE30US (allowlist of 2)."""
    monkeypatch.delenv("FRED_API_KEY", raising=False)  # don't actually hit FRED
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), series_id, "--latest"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    envelope = json.loads(result.stdout)
    assert envelope["series_id"] == series_id
