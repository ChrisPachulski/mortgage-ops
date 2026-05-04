"""Phase 8 Points Breakeven — full test surface (PNTS-01..03 + ROADMAP SC-4).

Wave 0 (Plan 08-00) creates ALL 5 stubs as xfail. Subsequent waves flip:
- Wave 3 (Plan 08-03 lib/points.py): PNTS-01/02 engine (2 stubs)
- Wave 4 (Plan 08-04 scripts/points_breakeven.py): PNTS-03 CLI (2 stubs)
- Wave 5 (Plan 08-05 fixtures): SC-4 divergence-pin (1 stub)
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "points_breakeven.py"


def test_pnts_01_simple_breakeven_ceil_division() -> None:
    """PNTS-01: ``months_to_breakeven == ceil(points_cost / monthly_savings)``.

    Pinned cases:
      8000 / 65.40 = 122.3242... -> ceil = 123 (NOT 122)
      8000 / 80.00 = 100.0       -> ceil = 100 (exact division)
    Edge cases (D-03-01: return None instead of raising; dispatcher surfaces
    the warning at the response layer per Phase 4 D-11 idiom):
      monthly_savings == 0    -> None
      monthly_savings <  0    -> None (rate-up scenario; points cost more)
    """
    from lib.points import simple_breakeven

    assert simple_breakeven(Decimal("8000.00"), Decimal("65.40")) == 123
    assert simple_breakeven(Decimal("8000.00"), Decimal("80.00")) == 100
    assert simple_breakeven(Decimal("8000.00"), Decimal("0.00")) is None
    assert simple_breakeven(Decimal("8000.00"), Decimal("-1.00")) is None


def test_pnts_02_npv_breakeven_decision_dispatcher() -> None:
    """PNTS-02: NPV-based breakeven side-by-side with simple; decision dispatcher.

    Two scenarios pinned at the engine layer:

    1. Zero-discount (D-03-03 mathematical identity): cum_npv collapses to
       undiscounted accumulation, so npv_breakeven == simple_breakeven == 123;
       diverge=False; decision=buy_points (cum_npv at 240mo is positive).

    2. 7%-discount divergence (08-RESEARCH §5.4 narrative pinned 160 months,
       but the documented §5.2 formula and numpy_financial.nper both yield
       ~215 months; engine ships the correct math). The §5.4 RESEARCH narrative
       cum_npv values (Year 14 ≈ +$430) are inconsistent with the §5.2
       cumulative-NPV formula. Cross-validated:
         numpy_financial.nper(0.07/12, 65.40, -8000) -> 214.9476 (ceil = 215)
         closed-form n = -ln(1 - 8000*r/65.40) / ln(1+r) where r=0.07/12 -> 214.95
       Engine ships the §5.2 formula correctly and pins 215 here. Decision
       remains buy_points because hold_period_months=240 > 215 so cum_npv at
       hold is strictly positive ($435.46).
    """
    from lib.points import PointsRequestFromSavings, evaluate

    # Scenario 1: zero discount; simple == npv (no divergence)
    r0 = evaluate(
        PointsRequestFromSavings(
            points_cost=Decimal("8000.00"),
            monthly_savings=Decimal("65.40"),
            hold_period_months=240,
            discount_rate_annual=Decimal("0.000000"),
        )
    )
    assert r0.simple_breakeven_months == 123
    assert r0.npv_breakeven_months == 123
    assert r0.diverge is False
    assert r0.diverge_explanation is None
    assert r0.decision == "buy_points"
    assert r0.warnings == []

    # Scenario 2: 7% discount; simple=123, npv=215 (engine-actual; cross-
    # validated against numpy_financial.nper). diverge=True; gap=+92 months.
    r1 = evaluate(
        PointsRequestFromSavings(
            points_cost=Decimal("8000.00"),
            monthly_savings=Decimal("65.40"),
            hold_period_months=240,
            discount_rate_annual=Decimal("0.070000"),
        )
    )
    assert r1.simple_breakeven_months == 123
    assert r1.npv_breakeven_months == 215
    assert r1.diverge is True
    assert r1.diverge_explanation is not None
    assert "0.070000" in r1.diverge_explanation
    assert r1.decision == "buy_points"  # 240 > 215; cum_npv at hold is positive
    assert r1.cumulative_npv_at_hold > Decimal("0")


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
    """ROADMAP SC-4: simple==123, npv==215 at 7% discount; diverge=true; gap=92 months."""
    pytest.fail("Wave 0 stub")
