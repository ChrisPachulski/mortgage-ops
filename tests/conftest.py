"""Shared pytest fixtures for the mortgage-ops test suite.

The `golden_fixture` factory loads pinned monthly P&I oracles from
`tests/fixtures/golden_pmt.json` (committed in Plan 05). Phase 1 only validates
shape; Phase 3+ uses the same loader to compute and assert against the values.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURE_DIR: Path = Path(__file__).parent / "fixtures"


@pytest.fixture
def golden_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single named fixture by `id` from
    tests/fixtures/golden_pmt.json. Raises KeyError if the id is not present."""

    def _load(fixture_id: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "golden_pmt.json"
        data = json.loads(path.read_text())
        for fx in data["fixtures"]:
            if fx["id"] == fixture_id:
                return fx  # type: ignore[no-any-return]
        raise KeyError(f"fixture id not found in golden_pmt.json: {fixture_id}")

    return _load
