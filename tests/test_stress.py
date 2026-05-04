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


def test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent() -> None:
    """STRS-01 + ROADMAP SC-1: rate-shock returns monthly_pi exact to cent for each rate.

    Plan 08-02 Task 6 flip — synthesized request (no fixture; Plan 08-05 will
    introduce fixture-driven assertions). Phase 3 oracle anchor: $400k/30yr at
    6.5% returns monthly_pi==2528.27 (CONVENTIONS.md pinned oracle).
    """
    from datetime import date
    from decimal import Decimal

    from lib.models import Loan
    from lib.stress import rate_shock

    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),  # nominal; rate_shock overrides per cell
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="fixed",
    )
    rates = [Decimal("0.060000"), Decimal("0.065000"), Decimal("0.070000")]
    rows, summary = rate_shock(loan, rates)

    assert len(rows) == 3
    # Phase 3 oracle anchor: 0.065 → "2528.27" (CONVENTIONS.md pinned oracle).
    assert rows[1].monthly_pi == Decimal("2528.27")
    # All values quantized to 2 decimal places (Money discipline).
    for r in rows:
        assert r.monthly_pi is not None
        assert r.monthly_pi.as_tuple().exponent == -2
    # Worst case = highest rate.
    assert summary.worst_case_label == "0.070000"
    # Monotone-pi invariant clean for monotone rates.
    assert summary.stress_invariant_violations == []


# =========================================================================
# STRS-02 income-shock engine (1 stub) — flipped Wave 2
# =========================================================================


def test_income_shock_per_cell_calls_phase4_engine_with_threshold_breach() -> None:
    """STRS-02 + ROADMAP SC-2: income-shock recomputes dti_back per reduction; flags threshold breach.

    Plan 08-02 Task 6 flip — synthesized AffordabilityRequest mirroring the
    single_applicant fixture shape. Baseline: $400k loan @ 6.5% / $10k income /
    $0 debts → dti_back ≈ 0.252827 (Phase 4 forward-mode). 50% reduction halves
    income to $5k → dti_back ≈ 0.505654 → breaches 0.43 threshold.
    """
    import json

    from lib.affordability import evaluate as affordability_evaluate
    from lib.stress import IncomeShockRequest, StressRequest, income_shock
    from pydantic import TypeAdapter

    base_payload = {
        "mode": "income-shock",
        "base_request": {
            "household": {
                "location": {
                    "state_fips": "53",
                    "county_fips": "033",
                    "county_name": "King",
                    "state": "WA",
                    "zip": "98101",
                },
                "applicants": [
                    {
                        "name": "A",
                        "gross_monthly_income": "10000.00",
                        "credit_score": 720,
                    },
                ],
                "size": 1,
                "monthly_debts": {
                    "auto": "0.00",
                    "student_loans": "0.00",
                    "credit_cards": "0.00",
                    "other": "0.00",
                },
                "escrow": {
                    "property_tax_monthly": "0.00",
                    "insurance_monthly": "0.00",
                    "hoa_monthly": "0.00",
                },
                "va": None,
                "current_housing_payment": "0.00",
            },
            "max_dti": "0.430000",
            "target_loan_type": "conventional",
            "term_months": 360,
            "annual_rate": "0.065000",
            "apr": None,
            "apor": None,
            "monthly_pmi": None,
            "endorsement_date_override": None,
            "junior_liens": [],
            "mode": "forward",
            "loan_amount": "400000.00",
            "property_value": "500000.00",
        },
        "reductions": ["0.000000", "0.500000"],
        "dti_threshold": "0.430000",
    }
    adapter: TypeAdapter[StressRequest] = TypeAdapter(StressRequest)
    req = adapter.validate_json(json.dumps(base_payload))
    assert isinstance(req, IncomeShockRequest)

    # Baseline reference dti for the 0.0-reduction sanity invariant.
    baseline_response = affordability_evaluate(req.base_request)
    baseline_dti = baseline_response.dti_back

    rows, summary = income_shock(req.base_request, req.reductions, req.dti_threshold)
    assert len(rows) == 2

    # 0% reduction: dti_back exactly matches the baseline forward-mode response.
    assert rows[0].label == "-0%"
    assert rows[0].dti_back == baseline_dti
    assert rows[0].breaches_threshold is False  # ~0.252827 < 0.43

    # 50% reduction: dti_back roughly doubles AND breaches the 0.43 threshold.
    assert rows[1].label == "-50%"
    assert rows[1].dti_back is not None
    assert baseline_dti is not None
    assert rows[1].dti_back > baseline_dti
    assert rows[1].breaches_threshold is True
    # Worst-case label tracks the higher dti.
    assert summary.worst_case_label == "-50%"
    # Per D-02-05, income-shock invariants stay empty in v1.
    assert summary.stress_invariant_violations == []


# =========================================================================
# STRS-03 ARM-reset path engine (2 stubs) — flipped Wave 2
# =========================================================================


def _build_5_1_arm_request_30yr() -> Any:
    """Helper: 5/1 ARM 30yr base ARMRequest used by Task 6 arm-path flips.

    initial=60, reset=12, term=360 → 25 reset triggers ([61, 73, ..., 349]).
    Margin 250bps; floor 3%; 500bps initial cap; 200bps periodic; 500bps lifetime.
    """
    from datetime import date
    from decimal import Decimal

    from lib.arm import ARMRequest, ARMTerms
    from lib.models import Loan

    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="arm",
    )
    arm_terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
        note_rate=None,
    )
    return ARMRequest(
        loan=loan,
        arm_terms=arm_terms,
        assumed_index_rate=Decimal("0.040000"),
        index_path=[],
    )


def test_arm_path_three_canonical_paths_total_interest() -> None:
    """STRS-03 + ROADMAP SC-3: parallel-shift + gradual-rise + fall-then-rise return total_interest_paid.

    Plan 08-02 Task 6 flip — synthesized 5/1 ARM 30yr base + three canonical
    paths. Sanity ordering: parallel-shift's total_interest > fall-then-rise's
    total_interest (the parallel +200bps shock is held forever; fall-then-rise
    drops then rises, accumulating less interest than the dominated path).
    """
    from decimal import Decimal

    from lib.stress import RatePath, arm_path

    base = _build_5_1_arm_request_30yr()
    paths = [
        RatePath(name="parallel-shift", params={"shift_bps": 200}),
        RatePath(name="gradual-rise", params={"step_bps": 25}),
        RatePath(name="fall-then-rise", params={"drop_bps": 100, "rise_bps": 200}),
    ]
    rows, summary = arm_path(base, paths)
    assert len(rows) == 3
    by_label = {r.label: r for r in rows}
    # All three paths produce positive total_interest.
    for name in ("parallel-shift", "gradual-rise", "fall-then-rise"):
        ti = by_label[name].total_interest
        assert ti is not None
        assert ti > Decimal("0")
    # Sanity ordering: parallel-shift dominates fall-then-rise on accumulated interest.
    parallel_ti = by_label["parallel-shift"].total_interest
    fall_rise_ti = by_label["fall-then-rise"].total_interest
    assert parallel_ti is not None
    assert fall_rise_ti is not None
    assert parallel_ti > fall_rise_ti
    # Worst case = highest total_interest.
    assert summary.worst_case_label is not None


def test_arm_path_30yr_horizon_reset_count() -> None:
    """STRS-03 + ROADMAP SC-3: 5/1 ARM 30yr → 25 reset events per path.

    Plan 08-02 Task 6 flip — _synthesize_index_path covers all reset triggers
    for the term (initial=60, reset=12, term=360 → triggers [61, 73, ..., 349],
    25 entries). Each path generates 25 IndexPathEntry rows; build_arm_schedule
    emits 25 ResetEvent rows.
    """
    from lib.stress import RatePath, arm_path

    base = _build_5_1_arm_request_30yr()
    paths = [
        RatePath(name="parallel-shift", params={"shift_bps": 200}),
        RatePath(name="gradual-rise", params={"step_bps": 25}),
        RatePath(name="fall-then-rise", params={"drop_bps": 100, "rise_bps": 200}),
    ]
    rows, _summary = arm_path(base, paths)
    for r in rows:
        assert r.reset_count == 25, f"path {r.label} expected 25 resets, got {r.reset_count}"


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


def test_sc5_stress_invariants_monthly_pi_monotone_in_rate() -> None:
    """ROADMAP SC-5 + RESEARCH §6.4: monthly_pi strictly increases as rate strictly increases.

    Plan 08-02 Task 6 flip — synthesized 4-rate sweep on $400k/30yr. Monotone-
    increasing rates produce monotone-increasing monthly_pi (Phase 3 amortization
    physics); stress_invariant_violations stays empty. Non-empty here would
    signal a Phase 3 engine bug.
    """
    from datetime import date
    from decimal import Decimal

    from lib.models import Loan
    from lib.stress import RateShockRequest, evaluate

    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="fixed",
    )
    req = RateShockRequest(
        loan=loan,
        rates=[
            Decimal("0.060000"),
            Decimal("0.065000"),
            Decimal("0.070000"),
            Decimal("0.075000"),
        ],
    )
    response = evaluate(req)
    assert response.summary.stress_invariant_violations == []
    # Sanity: monthly_pi strictly increases across the row order.
    pis: list[Decimal] = []
    for r in response.rows:
        assert r.monthly_pi is not None
        pis.append(r.monthly_pi)
    for i in range(1, len(pis)):
        assert pis[i] > pis[i - 1], (
            f"non-monotone monthly_pi at index {i}: {pis[i - 1]} -> {pis[i]}"
        )


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
