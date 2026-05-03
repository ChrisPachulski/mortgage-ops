"""Phase 8 Stress Tests — full test surface (STRS-01..04 + ROADMAP SC-1/2/3/5 + cross-cutting).

Per Phase 3 D-17 portability + Phase 5 Wave 0 idiom: subprocess invocation only
for CLI tests, never `import scripts.stress_test` directly. SCRIPT_PATH is the
single constant edited at Phase 10 when scripts/ relocates to .claude/skills/.

Wave 0 (Plan 08-00) creates ALL 13 stubs as xfail. Subsequent waves flip:
- Wave 1 (Plan 08-01 Pydantic models): STRS-04 model contract (1 stub)
- Wave 2 (Plan 08-02 lib/stress.py): STRS-01/02/03 engine (4 stubs)
- Wave 4 (Plan 08-04 scripts/stress_test.py): STRS-04 CLI (4 stubs)
- Wave 5 (Plan 08-05 fixtures + tests): SC-1/2/3/5 fixture-driven (4 stubs)

Each xfail uses strict=True so accidental pass raises XPASS — the wave that
flips it MUST also remove the decorator.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "stress_test.py"
"""Phase 8 CLI lives at project-root scripts/. Phase 10 relocates."""

STRESS_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "stress.py"
"""For lazy-import test (D-18 inherited): assert lib.stress is NOT imported by --help."""


# =========================================================================
# STRS-04 model contract (1 stub) — flipped Wave 1 (Plan 08-01)
# =========================================================================


def test_stress_request_discriminated_union_by_mode() -> None:
    """STRS-04 + Plan 08-01: StressRequest = RateShock|IncomeShock|ArmReset discriminated by 'mode'.

    Per Phase 4 idiom (tests/test_affordability.py:_request_from_fixture): strict-mode
    Decimal fields require the JSON validation path to coerce strings, so we
    re-encode the dict to JSON and validate via validate_json. This mirrors how
    scripts/* will exercise the boundary.
    """
    import json
    from datetime import date
    from decimal import Decimal

    from lib.models import Loan
    from lib.stress import RateShockRequest, StressRequest
    from pydantic import TypeAdapter, ValidationError

    adapter: TypeAdapter[StressRequest] = TypeAdapter(StressRequest)
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="fixed",  # Loan.loan_type Literal does not include "conventional"
    )
    happy_payload = {
        "mode": "rate-shock",
        "loan": loan.model_dump(mode="json"),
        "rates": ["0.06"],
    }
    rs = adapter.validate_json(json.dumps(happy_payload))
    assert isinstance(rs, RateShockRequest)

    bogus_payload = {**happy_payload, "mode": "bogus-mode"}
    with pytest.raises(ValidationError):
        adapter.validate_json(json.dumps(bogus_payload))


# =========================================================================
# STRS-01 rate-shock engine (1 stub) — flipped Wave 2
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-02 ships lib.stress.rate_shock",
)
def test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """STRS-01 + ROADMAP SC-1: rate-shock returns monthly_pi exact to cent for each rate."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# STRS-02 income-shock engine (1 stub) — flipped Wave 2
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-02 ships lib.stress.income_shock",
)
def test_income_shock_per_cell_calls_phase4_engine_with_threshold_breach(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """STRS-02 + ROADMAP SC-2: income-shock recomputes dti_back per reduction; flags threshold breach."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# STRS-03 ARM-reset path engine (2 stubs) — flipped Wave 2
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-02 ships lib.stress.arm_path",
)
def test_arm_path_three_canonical_paths_total_interest(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """STRS-03 + ROADMAP SC-3: parallel-shift + gradual-rise + fall-then-rise return total_interest_paid."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-02 synthesizes index_path per reset trigger",
)
def test_arm_path_30yr_horizon_reset_count(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """STRS-03 + ROADMAP SC-3: 5/1 ARM 30yr → 25 reset events per path."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# STRS-04 CLI (4 stubs) — flipped Wave 4 (Plan 08-04)
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-04 ships scripts/stress_test.py",
)
def test_cli_stress_smoke_subprocess_round_trip_rate_shock(
    stress_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """STRS-04: CLI rate-shock subprocess round-trip — write JSON, invoke, parse stdout."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-04 ships --rates 0.06,0.065,... shortcut",
)
def test_cli_stress_rates_shortcut_arg_matches_roadmap_sc1(tmp_path: Path) -> None:
    """STRS-04 + ROADMAP SC-1 verbatim: --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-04 ships D-18 lazy-import",
)
def test_cli_stress_help_does_not_import_lib_stress() -> None:
    """STRS-04 + D-18: --help fast (no lib.stress or numpy_financial import before argparse)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-04 ships float-gate + 6-key envelope",
)
def test_cli_stress_rejects_float_principal_with_6_key_envelope(tmp_path: Path) -> None:
    """STRS-04 + WR-02: CLI rejects JSON-float in loan.principal with 6-key Pydantic envelope."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ROADMAP SC-5 subagent-summarization output (3 stubs) — flipped Wave 5
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-05 ships rate_shock_size_budget_50_rates.json",
)
def test_sc5_stress_sweep_50_scenarios_under_100kb(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-5: 50-scenario sweep produces JSON < 100KB."""
    pytest.fail("Wave 0 stub")


def test_sc5_summary_table_appears_before_rows_in_json() -> None:
    """ROADMAP SC-5: scenario-summary table at the top — summary key appears before rows key."""
    import json

    from lib.stress import ScenarioSummary, StressResponse

    resp = StressResponse(
        mode="rate-shock",
        scenario_count=0,
        summary=ScenarioSummary(table=[]),
        rows=[],
    )
    out = resp.model_dump_json()
    keys = list(json.loads(out).keys())
    assert keys.index("summary") < keys.index("rows"), (
        f"SC-5 violation: summary must appear before rows; got order {keys}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-02 emits stress_invariant_violations",
)
def test_sc5_stress_invariants_monthly_pi_monotone_in_rate(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-5 + RESEARCH §6.4: monthly_pi strictly increases as rate strictly increases."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# Cross-cutting (1 stub)
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 08-04 ships envelope-uniformity",
)
def test_cli_stress_error_envelope_uniformity(tmp_path: Path) -> None:
    """STRS-04 + WR-02: float-gate + Pydantic ValidationError emit identical 6-key shape."""
    pytest.fail("Wave 0 stub")
