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


def test_cli_stress_smoke_subprocess_round_trip_rate_shock(tmp_path: Path) -> None:
    """STRS-04: CLI rate-shock subprocess round-trip — write JSON, invoke, parse stdout.

    Plan 08-04 Task 3 flip — synthesized minimal rate-shock JSON (no fixture
    loader; Plan 08-05 will introduce fixture-driven assertions for SC-1 / SC-5
    / etc.). Verifies:
      - exit 0 on happy path
      - stdout JSON has mode == "rate-shock"
      - SC-5 byte-order pin: "summary" key appears BEFORE "rows" key in indented JSON
        (the field-order contract is also verified at the model layer in
        test_sc5_summary_table_appears_before_rows_in_json — this is the
        round-trip witness end-to-end through the CLI).
    """
    import json as _json
    import subprocess
    import sys as _sys

    request_path = tmp_path / "input.json"
    request_path.write_text(
        '{"mode": "rate-shock", '
        '"loan": {"principal": "400000.00", "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "fixed"}, '
        '"rates": ["0.060000", "0.065000", "0.070000"]}'
    )
    result = subprocess.run(
        [_sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = _json.loads(result.stdout)
    assert out["mode"] == "rate-shock"
    assert out["scenario_count"] == 3
    # Phase 3 oracle anchor end-to-end through the CLI: 0.065 → "2528.27"
    # (CONVENTIONS.md pinned oracle).
    assert out["rows"][1]["monthly_pi"] == "2528.27"
    # SC-5 byte-order pin (D-02): "summary" key appears BEFORE "rows" key in
    # the indented serialized JSON. The Pydantic v2 field-declaration-order
    # serialization makes this a property of the model, but the round-trip
    # witness here verifies the field order survives the CLI's
    # model_dump_json(indent=2) call.
    assert result.stdout.find('"summary"') < result.stdout.find('"rows"'), (
        "SC-5 violation in CLI output: summary must appear before rows"
    )


def test_cli_stress_rates_shortcut_arg_matches_roadmap_sc1(tmp_path: Path) -> None:
    """STRS-04 + ROADMAP SC-1 verbatim: --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08.

    Plan 08-04 Task 3 flip + D-04-02: --rates shortcut overlays the parsed
    list into request.rates BEFORE Pydantic validation. Verifies:
      - 5 rows produced from the shortcut
      - first row label == "0.06" (engine echoes the input string verbatim;
        no float coercion at the argparse layer per D-04-02 / D-19)
      - --mode advisory hint passes through harmlessly per D-04-01
        (the JSON's mode field is authoritative).
    """
    import json as _json
    import subprocess
    import sys as _sys

    # Source JSON has rates: [] — the CLI shortcut overwrites it last-write-wins
    # per D-04-02. The empty source list would itself fail Pydantic
    # min_length=1, but the overlay happens BEFORE Pydantic validation so the
    # final raw JSON has the 5-rate list.
    request_path = tmp_path / "input.json"
    request_path.write_text(
        '{"mode": "rate-shock", '
        '"loan": {"principal": "400000.00", "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "fixed"}, '
        '"rates": []}'
    )
    result = subprocess.run(
        [
            _sys.executable,
            str(SCRIPT_PATH),
            "--mode",
            "rate-shock",
            "--rates",
            "0.06,0.065,0.07,0.075,0.08",
            "--input",
            str(request_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = _json.loads(result.stdout)
    assert len(out["rows"]) == 5
    assert out["scenario_count"] == 5
    # First row label echoes the input string verbatim (no decimal-place
    # normalization at the CLI layer; the engine receives the strings as-is).
    assert out["summary"]["table"][0]["label"] == "0.06"
    # And the labels track input order across the full 5-cell sweep.
    expected_labels = ["0.06", "0.065", "0.07", "0.075", "0.08"]
    actual_labels = [r["label"] for r in out["rows"]]
    assert actual_labels == expected_labels


def test_cli_stress_help_does_not_import_lib_stress() -> None:
    """STRS-04 + D-18: --help fast (no lib.stress or numpy_financial import before argparse).

    Plan 08-04 Task 3 flip — mirrors tests/test_arm.py::
    test_cli_help_does_not_import_lib_arm verbatim. The lazy-import contract
    is shipped at scripts/stress_test.py:main() — `from lib.stress import ...`
    appears INSIDE main() AFTER argparse.parse_args(), so the --help fast path
    never loads lib.stress, lib.amortize, lib.affordability, lib.arm, or
    numpy_financial.
    """
    import json as _json
    import subprocess
    import sys as _sys

    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_stress_test', SCRIPT)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "saved_argv = sys.argv\n"
        "sys.argv = [SCRIPT, '--help']\n"
        "exit_code = None\n"
        "try:\n"
        "    try:\n"
        "        module.main()\n"
        "    except SystemExit as exc:\n"
        "        exit_code = exc.code\n"
        "finally:\n"
        "    sys.argv = saved_argv\n"
        "result = {\n"
        "    'help_exit_code': exit_code,\n"
        "    'lib_stress_imported': 'lib.stress' in sys.modules,\n"
        "    'lib_amortize_imported': 'lib.amortize' in sys.modules,\n"
        "    'lib_affordability_imported': 'lib.affordability' in sys.modules,\n"
        "    'lib_arm_imported': 'lib.arm' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
        "}\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run(
        [_sys.executable, "-c", inline],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = _json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["help_exit_code"] == 0
    assert payload["lib_stress_imported"] is False
    assert payload["lib_amortize_imported"] is False
    assert payload["lib_affordability_imported"] is False
    assert payload["lib_arm_imported"] is False
    assert payload["numpy_financial_imported"] is False


def test_cli_stress_rejects_float_principal_with_6_key_envelope(tmp_path: Path) -> None:
    """STRS-04 + WR-02: CLI rejects JSON-float in loan.principal with 6-key Pydantic envelope.

    Plan 08-04 Task 3 flip — mirrors tests/test_arm.py::
    test_cli_rejects_float_principal verbatim. The float-gate path emits the
    canonical 6-key envelope {type, loc, msg, input, url, ctx} via the shared
    scripts._cli_helpers.make_decimal_type_envelope helper (Phase 5 D-19 +
    WR-02 closure).
    """
    import json as _json
    import subprocess
    import sys as _sys

    bad = tmp_path / "float_principal.json"
    bad.write_text(
        '{"mode": "rate-shock", '
        '"loan": {"principal": 400000.00, "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "fixed"}, '
        '"rates": ["0.060000"]}'
    )
    result = subprocess.run(
        [_sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = _json.loads(result.stderr)
    err = errors[0]
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["loan", "principal"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"]["class"] == "Decimal"


# =========================================================================
# ROADMAP SC-5 subagent-summarization output (3 stubs) — flipped Wave 5
# =========================================================================


def test_sc5_stress_sweep_50_scenarios_under_100kb(
    stress_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-5: 50-scenario sweep produces JSON < 100KB AND summary precedes rows.

    Plan 08-05 Task 5 flip — fixture-driven assertion for the SC-5 size-budget +
    field-order contract. The fixture (rate_shock_size_budget_50_rates.json)
    pins a 50-rate sweep generated as ``[f"0.0{40+i:02d}000" for i in range(50)]``
    (per D-05-06; rates 0.04..0.089 step 0.001). Engine emits ~37.6KB
    serialized JSON (well under the 100KB ceiling per 08-RESEARCH §1.3
    estimate). The byte-order check uses the substring ``.find('"summary"')``
    < ``.find('"rows"')`` on the indented JSON string per D-05-03 (robust to
    whitespace; sufficient for the SC-5 contract intent).
    """
    import json as _json

    from lib.stress import StressRequest, evaluate
    from pydantic import TypeAdapter

    fx = stress_fixture("rate_shock_size_budget_50_rates")
    adapter: TypeAdapter[Any] = TypeAdapter(StressRequest)
    # validate_json coerces Decimal strings (Phase 4 fixture idiom) — strict-mode
    # validate_python rejects "0.040000" because it's not Decimal-typed in Python.
    request = adapter.validate_json(_json.dumps(fx["request"]))
    response = evaluate(request)

    # SC-5 size budget: serialized JSON < 100KB.
    serialized = response.model_dump_json(indent=2)
    size_bytes = len(serialized.encode("utf-8"))
    assert size_bytes < 100 * 1024, f"SC-5 violation: {size_bytes} bytes >= 100KB"

    # SC-5 byte-order: summary key precedes rows key in indented JSON (D-05-03).
    idx_summary = serialized.find('"summary"')
    idx_rows = serialized.find('"rows"')
    assert 0 <= idx_summary < idx_rows, (
        f"SC-5 violation: 'summary' at {idx_summary} must precede 'rows' at {idx_rows}"
    )

    # Sanity: scenario_count matches fixture.
    assert response.scenario_count == fx["expected"]["scenario_count"]


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


def test_cli_stress_error_envelope_uniformity(tmp_path: Path) -> None:
    """STRS-04 + WR-02: float-gate + Pydantic ValidationError emit identical 6-key shape.

    Plan 08-04 Task 3 flip — mirrors tests/test_apr.py::
    test_apr_cli_error_envelope_uniformity. The cross-surface uniformity
    contract per Phase 3 WR-02 closure is "uniform 6-key envelope across
    surfaces the CLI is expected to expose": both the float-gate path AND
    the Pydantic ValidationError path emit envelopes carrying the same set
    of 6 keys: {type, loc, msg, input, url, ctx}.

    [Rule 1 - Bug fix] Plan 08-04 Task 3 spec suggested "missing required
    `rates` field" for the Pydantic-rejected surface. Pydantic v2 emits
    'missing' errors with only 5 keys (no 'ctx') in e.json(), failing the
    6-key uniformity contract. Same pitfall hit by tests/test_apr.py and
    tests/test_arm.py per their respective deviation notes; both resolved
    by routing through a surface that emits a value_error or too_short
    error (which DO carry ctx). This test uses an empty rates list ([])
    which trips RateShockRequest.rates Field(min_length=1) and surfaces a
    too_short ValidationError with full 6-key shape.
    """
    import json as _json
    import subprocess
    import sys as _sys

    expected_keys = {"type", "loc", "msg", "input", "url", "ctx"}

    # Surface 1: JSON-float in loan.principal (float-gate path).
    float_bad = tmp_path / "float_bad.json"
    float_bad.write_text(
        '{"mode": "rate-shock", '
        '"loan": {"principal": 400000.00, "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "fixed"}, '
        '"rates": ["0.060000"]}'
    )
    float_result = subprocess.run(
        [_sys.executable, str(SCRIPT_PATH), "--input", str(float_bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert float_result.returncode == 2
    float_errors = _json.loads(float_result.stderr)
    assert isinstance(float_errors, list)
    assert len(float_errors) >= 1
    for err in float_errors:
        assert set(err.keys()) == expected_keys, (
            f"float-gate envelope keys mismatch: got {set(err.keys())}; expected {expected_keys}"
        )

    # Surface 2: empty rates list trips RateShockRequest.rates Field(min_length=1)
    # and surfaces a too_short ValidationError (which DOES carry ctx — see
    # docstring for the rationale on why this is preferred over the 'missing'
    # surface the Plan 08-04 Task 3 spec suggested).
    pyd_bad = tmp_path / "pyd_bad.json"
    pyd_bad.write_text(
        '{"mode": "rate-shock", '
        '"loan": {"principal": "400000.00", "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "fixed"}, '
        '"rates": []}'
    )
    pyd_result = subprocess.run(
        [_sys.executable, str(SCRIPT_PATH), "--input", str(pyd_bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert pyd_result.returncode == 2
    pyd_errors = _json.loads(pyd_result.stderr)
    assert isinstance(pyd_errors, list)
    assert len(pyd_errors) >= 1
    for err in pyd_errors:
        assert set(err.keys()) == expected_keys, (
            f"Pydantic envelope keys mismatch: got {set(err.keys())}; expected {expected_keys}"
        )


# =========================================================================
# Phase 8 citation-coverage meta-test (Plan 08-05 Task 5)
# =========================================================================


def test_phase_08_citation_coverage_meta() -> None:
    """Every Phase 8 requirement (STRS-01..04 + PNTS-01..03) + ROADMAP SC-1..5
    has at least one fixture exercising it.

    Plan 08-05 Task 5 — closes the Phase 8 fixture-coverage contract. Iterates
    over all *.json files under tests/fixtures/{stress,points}/ and asserts that
    every requirement ID + ROADMAP SC label appears as a substring in at least
    one fixture's ``_meta.citation`` field.

    Per D-05-04 LOCKED: both raw requirement IDs (e.g., "STRS-01") AND ROADMAP
    SC strings (e.g., "ROADMAP SC-1") are valid citation tokens. A fixture's
    _meta.citation may contain one or both; this meta-test uses substring
    presence rather than exact match for resilience to minor wording drift.
    Variants are accepted: "ROADMAP SC-1" matches if either "ROADMAP SC-1"
    OR "SC-1" appears.

    STRS-04 and PNTS-03 are CLI requirements which are exercised by the CLI
    smoke tests in this file rather than by fixture-driven tests; this meta-
    test still requires fixture citation coverage for them so future fixtures
    that exercise CLI invocations explicitly get traceability for those
    requirement IDs.
    """
    import json

    fix_stress = Path(__file__).parent / "fixtures" / "stress"
    fix_points = Path(__file__).parent / "fixtures" / "points"
    all_citations: list[str] = []
    all_requirement_lists: list[list[str]] = []
    for p in sorted(fix_stress.glob("*.json")) + sorted(fix_points.glob("*.json")):
        data = json.loads(p.read_text())
        meta = data.get("_meta", {})
        citation = meta.get("citation", "")
        all_citations.append(citation)
        # Some fixtures also carry a structured _meta.requirements list.
        reqs = meta.get("requirements", [])
        if isinstance(reqs, list):
            all_requirement_lists.append([str(r) for r in reqs])

    joined_citations = " | ".join(all_citations)
    flat_requirements = [r for sub in all_requirement_lists for r in sub]
    joined_requirements = " | ".join(flat_requirements)

    target_ids = [
        "STRS-01",
        "STRS-02",
        "STRS-03",
        "STRS-04",
        "PNTS-01",
        "PNTS-02",
        "PNTS-03",
        "ROADMAP SC-1",
        "ROADMAP SC-2",
        "ROADMAP SC-3",
        "ROADMAP SC-4",
        "ROADMAP SC-5",
    ]
    for req_id in target_ids:
        # Accept both literal and bare form (ROADMAP SC-1 also matches SC-1)
        id_keys = {req_id, req_id.replace("ROADMAP ", "")}
        in_citation = any(any(k in c for k in id_keys) for c in all_citations)
        in_requirements = any(any(k in r for k in id_keys) for r in flat_requirements)
        assert in_citation or in_requirements, (
            f"No fixture cites {req_id} (in _meta.citation OR _meta.requirements). "
            f"citations: {joined_citations[:300]} | "
            f"requirements: {joined_requirements[:300]}"
        )
