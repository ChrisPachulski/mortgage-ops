"""Phase 8 Points Breakeven — full test surface (PNTS-01..03 + ROADMAP SC-4).

Wave 0 (Plan 08-00) creates ALL 5 stubs as xfail. Subsequent waves flip:
- Wave 3 (Plan 08-03 lib/points.py): PNTS-01/02 engine (2 stubs)
- Wave 4 (Plan 08-04 scripts/points_breakeven.py): PNTS-03 CLI (2 stubs)
- Wave 5 (Plan 08-05 fixtures): SC-4 divergence-pin (1 stub)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "points_breakeven.py"


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-03 ships simple_breakeven",
)
def test_pnts_01_simple_breakeven_ceil_division(
    points_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """PNTS-01: months_to_breakeven == ceil(points_cost / monthly_savings)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-03 ships npv_breakeven",
)
def test_pnts_02_npv_breakeven_decision_dispatcher(
    points_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """PNTS-02: NPV-based breakeven side-by-side with simple; decision = buy_points|skip_points."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-04 ships scripts/points_breakeven.py",
)
def test_pnts_03_cli_points_subprocess_round_trip(
    points_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """PNTS-03: CLI subprocess round-trip — write JSON, invoke, parse stdout."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-04 ships D-18 lazy-import + float-gate",
)
def test_pnts_03_cli_help_does_not_import_lib_points_and_rejects_float() -> None:
    """PNTS-03 + D-18 + WR-02: --help fast; CLI rejects JSON-float with 6-key envelope."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-05 ships points_simple_lt_npv_seven_pct_discount.json",
)
def test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin(
    points_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-4: simple==123, npv==160 at 7% discount; diverge=true; gap=37 months."""
    pytest.fail("Wave 0 stub")
