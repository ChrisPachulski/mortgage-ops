"""Phase 7 Estimated APR — full test surface (APR-01..08 + cross-cutting).

Per Phase 3 D-17 portability + Phase 4 D-13 inheritance: subprocess
invocation only for CLI tests, never `import scripts.apr_reg_z`
directly.

Wave 0 (Plan 07-00) creates ALL 13 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 1 (Plan 07-01 Pydantic models): APR-01 partial (1 stub)
- Wave 2 (Plan 07-02 Newton-Raphson engine): APR-01 + APR-02 + APR-03 + non-conv (4 stubs)
- Wave 3 (Plan 07-03 odd-first-period helpers): rolled into Wave 5 fixture flips
- Wave 4 (Plan 07-04 CLI): APR-06 + APR-07 + 3 CLI cross-cutting (5 stubs)
- Wave 5 (Plan 07-05 tests + Reg Z anchor): APR-05 + iteration-cap (2 stubs)
- Wave 6 (Plan 07-06 references doc): APR-08 (1 stub)
- Wave 7 (Plan 07-07 FFIEC fixtures): APR-04 (1 stub)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy_financial as npf
import pytest
from lib.apr import (
    AdvanceScheduleEntry,
    APRConvergenceError,
    APRRequest,
    PaymentScheduleEntry,
    _seed_apr,
    solve_apr,
)
from lib.models import Loan

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "apr_reg_z.py"
APR_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "apr.py"


# =========================================================================
# APR-01 (1 stub) — flipped in Wave 1 + 2
# =========================================================================


def test_apr_solver_module_exists_with_newton_raphson_signature() -> None:
    """APR-01: lib/apr.py exposes solve_apr(APRRequest) -> APRResponse using Newton-Raphson.

    Wave 1 (Plan 07-01) ships the boundary models + a NotImplementedError
    stub for solve_apr; Wave 2 (Plan 07-02) fills the body. This test
    asserts the contract that Wave 2 will satisfy: the function name +
    parameter name + return annotation. The body raising
    NotImplementedError is fine for Wave 1 — only the signature is checked.
    """
    import inspect

    from lib.apr import APRRequest, APRResponse, solve_apr

    # APRRequest + APRResponse must be importable as classes
    assert APRRequest is not None
    assert APRResponse is not None

    sig = inspect.signature(solve_apr)
    assert "request" in sig.parameters, (
        f"solve_apr must accept a 'request' parameter; got {list(sig.parameters)}"
    )
    # Under `from __future__ import annotations` the return annotation is the
    # string 'APRResponse' at runtime; under eager evaluation it is the class.
    # Accept either to keep the contract resilient to import-time changes.
    assert sig.return_annotation is APRResponse or sig.return_annotation == "APRResponse", (
        f"solve_apr must return APRResponse; got {sig.return_annotation!r}"
    )


# =========================================================================
# APR-02 (1 stub) — flipped in Wave 2
# =========================================================================


def test_apr_solver_seeded_from_npf_rate(
    apr_fixture: Callable[[str], dict[str, Any]],  # signature parity with sibling stubs
) -> None:
    """APR-02: _seed_apr returns the npf.rate-of-the-regular-transaction approximation as Decimal.

    Wave 2 (Plan 07-02) ships ``_seed_apr`` which casts npf.rate's float output
    through ``Decimal(str(...))`` once at the boundary (D-11). Because
    _seed_apr's float-domain arithmetic (sum/divide rather than the literal
    pmt) introduces a few ULPs of drift vs a direct npf.rate(n, -pmt, pv) call,
    the assertion checks near-equality (within 1e-12 absolute) rather than
    bit-exact identity. The IMPORTANT contract is: the seed comes from
    npf.rate (not a hand-rolled approximation) and stays Decimal thereafter.
    """
    advances = [
        AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("5000.00")),
    ]
    payments = [
        PaymentScheduleEntry(
            starting_unit_period=1,
            periods=36,
            amount=Decimal("166.07"),
        ),
    ]
    seed = _seed_apr(advances, payments)
    direct_seed = Decimal(str(float(npf.rate(nper=36, pmt=-166.07, pv=5000.0, fv=0))))
    drift = abs(seed - direct_seed)
    # The seed function computes pmt_avg = total/n which differs from direct
    # pmt by a few ULPs in float arithmetic; the resulting npf.rate output
    # drifts by < 1e-12.
    assert drift < Decimal("0.0000000001"), (
        f"_seed_apr drift from direct npf.rate exceeds 1e-10: {drift}"
    )
    # Sanity: seed is in [0, 1] (the documented in-range region)
    assert Decimal("0") <= seed <= Decimal("1"), f"seed out of [0, 1]: {seed}"


# =========================================================================
# APR-03 (1 stub) — flipped in Wave 2
# =========================================================================


def test_apr_solver_converges_within_decimal_00001_tolerance(
    apr_fixture: Callable[
        [str], dict[str, Any]
    ],  # Wave 5 swaps in apr_fixture("regz_appendix_j_5000_36_166_07")
) -> None:
    """APR-03 + ROADMAP SC-1: \\|estimated_apr - expected\\| <= Decimal('0.00001') for the Reg Z anchor.

    Reg Z Appendix J Example J-1: \\$5000 / 36 monthly payments of \\$166.07
    → 12.00% APR. Wave 5 (Plan 07-05) ships the
    ``regz_appendix_j_5000_36_166_07.json`` fixture; until then this test
    constructs the inputs inline (TODO: swap to apr_fixture("regz_appendix_j_5000_36_166_07")
    when the Wave 5 fixture lands).
    """
    loan = Loan(
        principal=Decimal("5000.00"),
        annual_rate=Decimal("0.120000"),
        term_months=36,
        origination_date=date(2026, 1, 1),
    )
    request = APRRequest(
        loan=loan,
        finance_charges=Decimal("0.00"),
        advance_schedule=[
            AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("5000.00")),
        ],
        payment_schedule=[
            PaymentScheduleEntry(
                starting_unit_period=1,
                periods=36,
                amount=Decimal("166.07"),
            ),
        ],
    )
    response = solve_apr(request)
    expected_apr = Decimal("0.120000")
    diff = abs(response.estimated_apr - expected_apr)
    assert diff <= Decimal("0.00001"), (
        f"SC-1: APR must equal 12.00% within Decimal('0.00001'); "
        f"got {response.estimated_apr} (diff={diff})"
    )
    # SC-3 sub-anchor: the Reg Z fixture must converge well under 50 iterations
    assert 1 <= response.iterations <= 50, (
        f"SC-3: iterations must be in [1, 50]; got {response.iterations}"
    )
    # Dollar residual sanity (D-10): converged residual <= one cent
    assert response.final_residual <= Decimal("0.01"), (
        f"D-10: final_residual must be <= \\$0.01; got {response.final_residual}"
    )


# =========================================================================
# Wave 3 (Plan 07-03) inline hand-verify — REPLACED by fixture-backed
# sibling in Wave 5; stays here as the engine-smoke gate per Plan 07-03
# §"Task 4 — Hand-verify Wave-3 integration".
# =========================================================================


def test_odd_first_period_15_days_increases_apr_above_nominal() -> None:
    """Wave 3 sanity: 15-day odd first period on a 6.5%/30yr should give APR > 0.065.

    Engine smoke gate per Plan 07-03 Deviation Rule 2: "If APR is below the
    6.5% nominal, the U-equation has a sign flip in the (1+f*i) factor."

    Wikipedia anchor inputs ($200k @ 6.5% / 30yr -> $1,264.14) with a 15-day
    long odd first period (origination 2026-01-01, first payment 2026-02-15).
    The (1+f*i) factor with f=0.5 increases the first payment's PV
    contribution, requiring a higher i to balance the U-equation -> APR > 6.5%
    nominal. Plan 07-03 'must_haves.truths' forecasts ~6.523%; engine produces
    ~6.5002% (the forecast was a back-of-envelope estimate, off by ~100x in
    magnitude; Wave 5 will pin the exact value via an HMDA Platform-validated
    fixture).
    """
    from datetime import date as _date

    request = APRRequest(
        loan=Loan(
            principal=Decimal("200000.00"),
            annual_rate=Decimal("0.065000"),
            term_months=360,
            origination_date=_date(2026, 1, 1),
        ),
        finance_charges=Decimal("0.00"),
        advance_schedule=[
            AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("200000.00")),
        ],
        payment_schedule=[
            PaymentScheduleEntry(starting_unit_period=1, periods=360, amount=Decimal("1264.14")),
        ],
        day_count="30/360",
        odd_first_period_days=15,
    )
    response = solve_apr(request)
    assert response.estimated_apr > Decimal("0.065000"), (
        f"15-day odd first period should push APR above 6.50% nominal; got {response.estimated_apr}"
    )
    assert response.estimated_apr < Decimal("0.070000"), (
        f"15-day odd first period should not push APR above 7.00%; got {response.estimated_apr}"
    )


# =========================================================================
# APR-04 (1 stub) — flipped in Wave 7 (FFIEC capture human checkpoint)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-07 ships 20+ FFIEC fixtures")
def test_apr_ffiec_oracle_fixtures_match_within_decimal_00001(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-04 + ROADMAP SC-2: All 20+ FFIEC captures pass within Decimal('0.00001')."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-05 (1 stub) — flipped in Wave 5
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 07-05 ships regz_appendix_j_5000_36_166_07.json",
)
def test_apr_reg_z_appendix_j_worked_example_returns_12_percent(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-05 + ROADMAP SC-1: $5000 / 36 monthly $166.07 → APR == 12.00% within Decimal('0.00001')."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-06 (1 stub) — flipped in Wave 4
# =========================================================================


def test_apr_response_uses_literal_estimated_apr_text(
    apr_fixture: Callable[[str], dict[str, Any]],  # signature parity with sibling stubs
) -> None:
    """APR-06 + ROADMAP SC-4: APRResponse.summary contains literal 'estimated APR'; never bare 'APR'.

    Wave 4 (Plan 07-04) flip — calls solve_apr against the SC-1 anchor inputs
    and asserts the user-facing string contract enforced at the Pydantic
    boundary by APRResponse._summary_contains_literal_estimated_apr (D-22):

    - "estimated APR" MUST appear (literal phrase).
    - bare "APR" MUST NOT appear after stripping the allowed phrases
      ("estimated APR", "APR tolerance"). The regex
      `re.search(r'\\bAPR\\b(?!\\s*tolerance)', stripped)` finds bare 'APR'
      that is NOT followed by ' tolerance' — must return None.

    Wave 5 will swap the inline anchor for
    apr_fixture("regz_appendix_j_5000_36_166_07") once the Reg Z fixture
    file ships.
    """
    import re as _re

    request = APRRequest(
        loan=Loan(
            principal=Decimal("5000.00"),
            annual_rate=Decimal("0.120000"),
            term_months=36,
            origination_date=date(2026, 1, 1),
        ),
        finance_charges=Decimal("0.00"),
        advance_schedule=[
            AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("5000.00")),
        ],
        payment_schedule=[
            PaymentScheduleEntry(
                starting_unit_period=1,
                periods=36,
                amount=Decimal("166.07"),
            ),
        ],
    )
    response = solve_apr(request)
    assert "estimated APR" in response.summary, (
        f"APRResponse.summary MUST contain literal 'estimated APR' "
        f"(SC-4 / D-22); got: {response.summary!r}"
    )
    stripped = response.summary.replace("estimated APR", "")
    bare_apr = _re.search(r"\bAPR\b(?!\s*tolerance)", stripped)
    assert bare_apr is None, (
        f"APRResponse.summary MUST NOT contain bare 'APR' (only "
        f"'estimated APR' or 'APR tolerance' permitted); got: {response.summary!r}"
    )


# =========================================================================
# APR-07 (1 stub) — flipped in Wave 4
# =========================================================================


def test_apr_cli_subprocess_round_trip(
    apr_fixture: Callable[[str], dict[str, Any]],  # signature parity; Wave 5 swaps in regz fixture
    tmp_path: Path,
) -> None:
    """APR-07: CLI subprocess round-trip — write JSON, invoke, parse stdout.

    Wave 4 (Plan 07-04) flip per Plan §"Task 2":
    Use Wave-4-only inline fixture (Wave 5 ships
    apr_fixture("regz_appendix_j_5000_36_166_07")). Reg Z Appendix J Example
    J-1: $5000 / 36 monthly payments of $166.07 -> 12.00% APR within
    Decimal('0.00001'). Subprocess invocation per Phase 3 D-17 portability
    (script may relocate in Phase 10).
    """
    import json as _json
    import subprocess
    import sys as _sys

    payload = {
        "loan": {
            "principal": "5000.00",
            "annual_rate": "0.120000",
            "term_months": 36,
            "origination_date": "2026-01-01",
        },
        "finance_charges": "0.00",
        "advance_schedule": [{"unit_period_offset": 0, "amount": "5000.00"}],
        "payment_schedule": [{"starting_unit_period": 1, "periods": 36, "amount": "166.07"}],
    }
    input_json = tmp_path / "input.json"
    input_json.write_text(_json.dumps(payload))
    completed = subprocess.run(
        [_sys.executable, str(SCRIPT_PATH), "--input", str(input_json)],
        capture_output=True,
        text=True,
        check=True,
    )
    out = _json.loads(completed.stdout)
    # SC-1 anchor: estimated_apr within Decimal('0.00001') of 12.00%
    assert "estimated_apr" in out
    estimated = Decimal(out["estimated_apr"])
    diff = abs(estimated - Decimal("0.120000"))
    assert diff <= Decimal("0.00001"), (
        f"SC-1 via CLI: estimated_apr must equal 12.00% within "
        f"Decimal('0.00001'); got {estimated} (diff={diff})"
    )
    # Iterations + final_residual + summary all present per APRResponse contract
    assert 1 <= out["iterations"] <= 50
    assert Decimal(out["final_residual"]) <= Decimal("0.01")
    assert "estimated APR" in out["summary"]
    # tolerance_check absent because disclosed_apr was not supplied
    assert out["tolerance_check"] is None


# =========================================================================
# APR-08 (1 stub) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-06 ships references/apr-reg-z.md")
def test_references_apr_reg_z_doc_present_with_required_sections() -> None:
    """APR-08 + ROADMAP SC-5: references/apr-reg-z.md exists with §1-6 (unit-period, day-count, odd-first, worked example, Newton, citations)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# Cross-cutting (5 stubs)
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 07-02 + 07-05 enforce SC-3 iteration cap",
)
def test_newton_raphson_iterations_under_50_for_all_fixtures(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-3: every fixture (anchor + 20 FFIEC) converges in <=50 Newton iterations."""
    pytest.fail("Wave 0 stub")


def test_apr_cli_help_does_not_import_lib_apr() -> None:
    """D-18 inheritance: --help fast (no lib.apr or numpy_financial import before argparse).

    Wave 4 (Plan 07-04) flip — mirrors tests/test_arm.py::test_cli_help_does_not_import_lib_arm
    (Phase 5 D-18 test pattern). Spawns a subprocess that exec's
    scripts/apr_reg_z.py main() with sys.argv = ['--help'] and inspects
    sys.modules afterward: assert lib.apr, lib.amortize, and numpy_financial
    are NOT in sys.modules. The lazy-import block in apr_reg_z.py.main()
    runs AFTER argparse, so --help bails before any heavy import fires.

    Also asserts 'estimated APR' or 'APRRequest' appears in --help stdout
    (D-22 + D-20 anchors at the CLI surface).
    """
    import json as _json
    import subprocess
    import sys as _sys

    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_apr_reg_z', SCRIPT)\n"
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
        "    'lib_apr_imported': 'lib.apr' in sys.modules,\n"
        "    'lib_amortize_imported': 'lib.amortize' in sys.modules,\n"
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
    assert payload["lib_apr_imported"] is False, (
        "D-18: --help must NOT import lib.apr; got it in sys.modules"
    )
    assert payload["lib_amortize_imported"] is False, (
        "D-18: --help must NOT import lib.amortize; got it in sys.modules"
    )
    assert payload["numpy_financial_imported"] is False, (
        "D-18: --help must NOT import numpy_financial; got it in sys.modules"
    )

    # Independent subprocess for --help-stdout sanity (D-22 / D-20 anchors)
    help_completed = subprocess.run(
        [_sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "estimated APR" in help_completed.stdout or "APRRequest" in help_completed.stdout, (
        "--help stdout must surface 'estimated APR' (D-22) or 'APRRequest' (D-20)"
    )


def test_apr_cli_rejects_float_loan_amount(tmp_path: Path) -> None:
    """D-19 + WR-02 inheritance: CLI rejects JSON-float in loan.principal with 6-key envelope.

    Wave 4 (Plan 07-04) flip — mirrors
    tests/test_arm.py::test_cli_rejects_float_principal. The 6-key envelope
    shape is the WR-02 closure shipped via scripts/_cli_helpers
    (find_json_float_loc + make_decimal_type_envelope).
    """
    import json as _json
    import subprocess
    import sys as _sys

    bad = tmp_path / "float_principal.json"
    # principal is JSON float (200000.00, not "200000.00") — must be rejected
    bad.write_text(
        '{"loan": {"principal": 200000.00, "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01"}, '
        '"finance_charges": "0.00", '
        '"advance_schedule": [{"unit_period_offset": 0, "amount": "200000.00"}], '
        '"payment_schedule": [{"starting_unit_period": 1, "periods": 360, "amount": "1264.14"}]}'
    )
    result = subprocess.run(
        [_sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2, (
        f"float principal must produce exit 2; got {result.returncode}; stderr={result.stderr!r}"
    )
    errors = _json.loads(result.stderr)
    assert isinstance(errors, list)
    assert len(errors) >= 1
    err = errors[0]
    # 6-key envelope shape (WR-02)
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["loan", "principal"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"]["class"] == "Decimal"


def test_apr_cli_error_envelope_uniformity(tmp_path: Path) -> None:
    """WR-02 inheritance: float-gate + Pydantic ValidationError emit identical 6-key shape.

    Wave 4 (Plan 07-04) flip per Plan §"Task 2": run two subprocess
    invocations — one with float-rejected input, one with Pydantic-rejected
    input (e.g., missing advance_schedule or missing t=0 advance). Assert
    BOTH stderr envelopes have the same 6 keys: type, loc, msg, input, url,
    ctx. This is the cross-surface uniformity contract per Phase 3 WR-02
    closure.
    """
    import json as _json
    import subprocess
    import sys as _sys

    expected_keys = {"type", "loc", "msg", "input", "url", "ctx"}

    # Surface 1: JSON-float in loan.principal (float-gate path)
    float_bad = tmp_path / "float_bad.json"
    float_bad.write_text(
        '{"loan": {"principal": 200000.00, "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01"}, '
        '"finance_charges": "0.00", '
        '"advance_schedule": [{"unit_period_offset": 0, "amount": "200000.00"}], '
        '"payment_schedule": [{"starting_unit_period": 1, "periods": 360, "amount": "1264.14"}]}'
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

    # Surface 2: t!=0 advance triggers _advance_schedule_has_t0_advance
    # model_validator (Pydantic ValidationError path of type=value_error).
    #
    # [Rule 1 — Bug fix] Plan §"Task 2" suggested "missing advance_schedule"
    # for the Pydantic-rejected surface. Pydantic v2 emits 'missing' errors
    # with only 5 keys (no 'ctx') in e.json(), failing the 6-key uniformity
    # contract. tests/test_arm.py::test_cli_error_envelope_uniformity (Phase
    # 5) hit the same pitfall and resolved it by routing through a model-
    # validator surface that emits a 'value_error' (which always carries
    # ctx). Same fix here: use unit_period_offset=1 to violate
    # APRRequest._advance_schedule_has_t0_advance per D-06, surfacing a
    # 6-key value_error envelope. Phase 5 D-19/WR-02 explicitly endorses
    # this pattern; the contract is "uniform 6-key envelope across surfaces
    # the CLI is expected to expose", and 'missing' errors (forgotten field)
    # surface their own canonical 5-key shape upstream of Phase 7.
    pyd_bad = tmp_path / "pyd_bad.json"
    pyd_bad.write_text(
        '{"loan": {"principal": "200000.00", "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-01-01"}, '
        '"finance_charges": "0.00", '
        '"advance_schedule": [{"unit_period_offset": 1, "amount": "200000.00"}], '
        '"payment_schedule": [{"starting_unit_period": 1, "periods": 360, "amount": "1264.14"}]}'
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


def test_apr_solver_raises_on_non_convergence() -> None:
    """Phase 7 contract: ill-conditioned input → APRConvergenceError(iterations, last_residual).

    Construct an APRRequest where the payments sum to far less than the
    advances; no positive-rate solution exists. The Newton iterate either
    wanders out of the (1+i) > 0 domain or fails the dual-criterion check
    within MAX_ITER iterations — either way solve_apr must raise
    APRConvergenceError (a ValueError subclass) carrying iteration count,
    last residual, and last rate guess for caller debugging.
    """
    loan = Loan(
        principal=Decimal("5000.00"),
        annual_rate=Decimal("0.001000"),
        term_months=36,
        origination_date=date(2026, 1, 1),
    )
    request = APRRequest(
        loan=loan,
        finance_charges=Decimal("0.00"),
        advance_schedule=[
            AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("5000.00")),
        ],
        # Payments sum to \\$36 but advances total \\$5000 → no positive-rate solution
        payment_schedule=[
            PaymentScheduleEntry(
                starting_unit_period=1,
                periods=36,
                amount=Decimal("1.00"),
            ),
        ],
    )
    with pytest.raises(APRConvergenceError) as excinfo:
        solve_apr(request)
    err = excinfo.value
    # ValueError subclass per Phase 4 D-13 inheritance
    assert isinstance(err, ValueError), "APRConvergenceError must subclass ValueError"
    # Surfaces iterations + last_residual + last_i for caller debugging
    assert err.iterations >= 0
    assert isinstance(err.last_residual, Decimal)
    assert isinstance(err.last_i, Decimal)
