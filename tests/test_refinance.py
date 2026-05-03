"""Phase 6 Refinance NPV — full test surface (REFI-01..09 + SC-1..SC-5 + cross-cutting).

Per Phase 3 D-17 portability + Phase 4 D-13 inheritance + Phase 5 inheritance:
subprocess invocation only for CLI tests, never `import scripts.refi_npv`
directly. SCRIPT_PATH is the single constant edited at Phase 10 when scripts/
relocates to .claude/skills/mortgage-ops/scripts/.

Wave 0 (Plan 06-00) creates ALL 25 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 1 (Plan 06-01 RefiCashflow + sign-validator + module docstring cite):
  4 sign-validator tests + 1 module-docstring cite (5 flips)
- Wave 2 (Plan 06-02 rate-and-term engine + breakeven helpers):
  empirical engine validation; no test flips (0 flips)
- Wave 3 (Plan 06-03 cash-out + after-tax mode):
  1 after-tax validator (1 flip)
- Wave 4 (Plan 06-04 CLI scripts/refi_npv.py + 6-key envelope):
  6 CLI tests (6 flips)
- Wave 5 (Plan 06-05 fixtures + REFI-01..03/05..07 + SC-1..3 + breakeven divergence):
  11 fixture-driven flips (rate-and-term + cash-out + breakeven + cashflow-kind
  citation coverage + pyxirr-deferral docstring assertion)
- Wave 6 (Plan 06-06 references/refi-npv.md doc):
  2 doc tests (sections + sign-convention phrase)

Each xfail decorator carries `strict=True` so a passing test in xfail state
raises XPASS at collection time — the wave that flips it MUST also remove
the decorator. This prevents accidental "fixed but still marked xfail" drift.

Phase 6 stub names are LOCKED verbatim by Plan 06-00 <test_inventory>; downstream
waves rename only via documented Rule-1 deviations in their SUMMARY.md.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from lib.refinance import CashOutRefiRequest, RateAndTermRefiRequest, RefiCashflow
from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "refi_npv.py"
"""Phase 6 CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""

REFINANCE_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "refinance.py"
"""For lazy-import test (D-18 inherited): assert lib.refinance is NOT imported by --help."""

REFI_NPV_DOC_PATH: Path = Path(__file__).resolve().parent.parent / "references" / "refi-npv.md"
"""For SC-5 doc-presence + sign-convention-phrase tests (Wave 6 / Plan 06-06)."""


# =========================================================================
# REFI-01 (rate-and-term NPV) — 3 stubs, flipped Wave 5 (Plan 06-05)
# =========================================================================


def test_refi_rate_and_term_positive_npv(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-1 anchor: rate-and-term refi at 200bps drop + $2k closing → NPV > 0 (Oracle 1).

    Loads tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json,
    runs evaluate(req), asserts engine_output Decimal-equals expected.npv per
    Phase 5 D-04 [REVISED] hand_calc_check witness pattern.
    """
    fx = refinance_fixture("positive_npv_200bps_drop_2k_costs")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]
    # SC-1 anchor: NPV strictly positive
    assert Decimal(resp.npv) > Decimal("0"), (
        f"SC-1 violated: positive-NPV fixture must yield npv > 0; got {resp.npv}"
    )
    # Phase 5 D-04 [REVISED]: strict Decimal equality vs engine-derived pin
    assert Decimal(resp.npv) == Decimal(expected["npv"]), (
        f"engine drift: npv={resp.npv} != expected={expected['npv']}"
    )
    # Sanity surface fields
    assert str(resp.old_monthly_pi) == expected["old_monthly_pi"]
    assert str(resp.new_monthly_pi) == expected["new_monthly_pi"]
    assert str(resp.monthly_savings) == expected["monthly_savings"]
    assert resp.refi_kind == expected["refi_kind"]


def test_refi_rate_and_term_negative_npv(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-1 anchor: same rate drop + $5k closing + analysis_horizon_months=12 → NPV < 0 (Oracle 2).

    D-13 horizon-truncation: full-horizon NPV at 200bps drop + $5k closing is
    still positive (~$60k savings); horizon=12 simulates short borrower tenure
    (FHFA median ~13y) and yields the negative-NPV anchor for SC-1.
    """
    fx = refinance_fixture("negative_npv_short_horizon")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]
    # SC-1 anchor: NPV strictly negative
    assert Decimal(resp.npv) < Decimal("0"), (
        f"SC-1 violated: negative-NPV fixture must yield npv < 0; got {resp.npv}"
    )
    # Phase 5 D-04 [REVISED]: strict Decimal equality vs engine-derived pin
    assert Decimal(resp.npv) == Decimal(expected["npv"]), (
        f"engine drift: npv={resp.npv} != expected={expected['npv']}"
    )
    assert resp.analysis_horizon_months_used == 12  # D-13


def test_refi_npv_decimal_exact(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """D-04: NPV asserted with strict Decimal equality (no assertAlmostEqual; CLAUDE.md money discipline).

    Exercises the Decimal-equals discipline via the positive-NPV fixture: every
    money/rate field on the response equals the fixture's pinned Decimal-string
    via Decimal(==), never pytest.approx.
    """
    fx = refinance_fixture("positive_npv_200bps_drop_2k_costs")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]
    # Strict Decimal equality discipline (Phase 4 D-18 idiom, Phase 5 D-04 [REVISED])
    assert Decimal(resp.npv) == Decimal(expected["npv"])
    assert Decimal(resp.old_monthly_pi) == Decimal(expected["old_monthly_pi"])
    assert Decimal(resp.new_monthly_pi) == Decimal(expected["new_monthly_pi"])
    assert Decimal(resp.monthly_savings) == Decimal(expected["monthly_savings"])
    assert Decimal(resp.discount_rate_annual_used) == Decimal(expected["discount_rate_annual_used"])
    # CLAUDE.md money discipline: never use approx for money
    # (this test would fail if any quantize_cents drift snuck in)


# =========================================================================
# REFI-02 (cash-out) — 3 stubs, flipped Wave 5 (Plan 06-05)
# =========================================================================


def test_refi_cash_out_proceeds(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-3 anchor: cash_proceeds surfaced as labeled top-level JSON field (Oracle 3)."""
    fx = refinance_fixture("cash_out_proceeds_50k")
    req = CashOutRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]
    # SC-3: cash_proceeds is a labeled top-level field on the response
    assert resp.cash_proceeds is not None, "SC-3 violated: cash_proceeds must be populated"
    assert Decimal(resp.cash_proceeds) == Decimal(expected["cash_proceeds"])
    # Surface the labeled key in serialized JSON (downstream contract)
    out = json.loads(resp.model_dump_json())
    assert "cash_proceeds" in out
    assert out["cash_proceeds"] == expected["cash_proceeds"]


def test_refi_cash_out_new_monthly_pi(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-3 anchor: new_monthly_pi surfaced as labeled top-level JSON field (Oracle 3)."""
    fx = refinance_fixture("cash_out_proceeds_50k")
    req = CashOutRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]
    # SC-3: new_monthly_pi is a labeled top-level field
    assert Decimal(resp.new_monthly_pi) == Decimal(expected["new_monthly_pi"])
    out = json.loads(resp.model_dump_json())
    assert "new_monthly_pi" in out
    assert out["new_monthly_pi"] == expected["new_monthly_pi"]


def test_refi_cash_out_closing_exceeds_cash_audit_trail(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """CR-01 (REVIEW.md fix): on the pathological cash-out path where
    closing_costs >= cash_out_amount, the engine MUST emit BOTH gross t=0
    legs (closing_costs outflow + cash_out_amount inflow) so the audit
    trail and NPV math agree on what actually moved.

    Pre-fix bug: the negative-net branch passed cash_proceeds_net=0 to
    _build_refi_cashflows, which (per `if cash_proceeds_net > 0`) suppressed
    the cash_proceeds emission entirely. The audit trail surfaced ONLY the
    closing_costs outflow — the borrower's actual cash_out_amount inflow
    disappeared, breaking SC-3's "labeled top-level + audit-trail" contract.

    This fixture pins the post-fix invariant: sum(t=0 cashflows.amount) ==
    cash_out_amount - closing_costs (signed). cash_proceeds remains None
    per the D-12 / Rule-1 consumer-friendly surface (we don't report a
    non-positive Money), but the audit trail loses no transactions.
    """
    fx = refinance_fixture("cash_out_closing_exceeds_cash")
    req = CashOutRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]

    # Audit-trail integrity: both gross legs surfaced at t=0
    t0_cashflows = [cf for cf in resp.cashflows if cf.period == 0]
    kinds_at_t0 = {cf.kind for cf in t0_cashflows}
    assert "closing_costs" in kinds_at_t0, (
        f"CR-01 violated: closing_costs outflow missing from t=0 audit trail; "
        f"got kinds={kinds_at_t0}"
    )
    assert "cash_proceeds" in kinds_at_t0, (
        f"CR-01 violated: cash_proceeds inflow missing from t=0 audit trail "
        f"(this WAS the bug: dropped on the negative-net path); got kinds={kinds_at_t0}"
    )

    # CR-01 invariant: sum of t=0 amounts == cash_out_amount - closing_costs
    t0_sum = sum((cf.amount for cf in t0_cashflows), Decimal("0"))
    assert t0_sum == Decimal(expected["t0_net_signed"]), (
        f"CR-01 audit-trail vs. NPV math drift: sum(t=0 cashflows)={t0_sum}, "
        f"expected={expected['t0_net_signed']} (= cash_out - closing)"
    )

    # D-12 / Rule-1 consumer-friendly surface preserved: cash_proceeds is None
    # when net is non-positive (we do NOT surface a non-positive Money value).
    assert resp.cash_proceeds is expected["cash_proceeds"]


def test_refi_cash_out_total_interest_delta(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-3 anchor: total_interest_delta surfaced as labeled top-level JSON field (Oracle 3)."""
    fx = refinance_fixture("cash_out_proceeds_50k")
    req = CashOutRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]
    assert resp.total_interest_delta is not None, (
        "SC-3 violated: total_interest_delta must be populated for cash-out"
    )
    assert Decimal(resp.total_interest_delta) == Decimal(expected["total_interest_delta"])
    # SC-3 sign rigor: cash-out + extension causes MORE lifetime interest, so signed positive
    assert Decimal(resp.total_interest_delta) > Decimal("0"), (
        f"SC-3: cash-out total_interest_delta should be positive (more interest); "
        f"got {resp.total_interest_delta}"
    )
    out = json.loads(resp.model_dump_json())
    assert "total_interest_delta" in out
    assert out["total_interest_delta"] == expected["total_interest_delta"]


# =========================================================================
# REFI-03 (breakeven dual reporting) — 3 stubs, flipped Wave 5 (Plan 06-05)
# =========================================================================


def test_refi_breakeven_simple_labeled(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-2 anchor: simple_months + simple_status labeled in output JSON."""
    fx = refinance_fixture("positive_npv_200bps_drop_2k_costs")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]["breakeven"]
    out = json.loads(resp.model_dump_json())
    # SC-2 surface: breakeven sub-object labeled at top-level with both forms
    assert "breakeven" in out
    assert "simple_months" in out["breakeven"]
    assert "simple_status" in out["breakeven"]
    assert out["breakeven"]["simple_months"] == expected["simple_months"]
    assert out["breakeven"]["simple_status"] == expected["simple_status"]


def test_refi_breakeven_npv_labeled(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-2 anchor: npv_months + npv_status labeled in output JSON (D-06 cumulative scan)."""
    fx = refinance_fixture("positive_npv_200bps_drop_2k_costs")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]["breakeven"]
    out = json.loads(resp.model_dump_json())
    # SC-2 surface: NPV-based breakeven labeled at top-level (D-06 cumulative scan)
    assert "breakeven" in out
    assert "npv_months" in out["breakeven"]
    assert "npv_status" in out["breakeven"]
    assert out["breakeven"]["npv_months"] == expected["npv_months"]
    assert out["breakeven"]["npv_status"] == expected["npv_status"]


def test_refi_breakeven_divergence_documented(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """SC-2 anchor: breakeven_divergence.json exercises high-discount-rate divergence (simple ≠ NPV by ≥1 month)."""
    fx = refinance_fixture("breakeven_divergence")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]["breakeven"]
    # SC-2 divergence anchor: simple ≠ NPV by ≥ 1 month at 8% discount
    assert resp.breakeven.simple_months is not None
    assert resp.breakeven.npv_months is not None
    assert resp.breakeven.simple_months == expected["simple_months"]
    assert resp.breakeven.npv_months == expected["npv_months"]
    divergence = abs(resp.breakeven.npv_months - resp.breakeven.simple_months)
    assert divergence >= 1, (
        f"SC-2 divergence anchor: simple ({resp.breakeven.simple_months}) and "
        f"npv ({resp.breakeven.npv_months}) must differ by ≥ 1 month"
    )


# =========================================================================
# REFI-04 (pyxirr deferral) — 1 stub, flipped Wave 6 (Plan 06-05/06-06 docstring assertion)
# =========================================================================


def test_pyxirr_deferred_to_phase11_documented() -> None:
    """D-07: lib/refinance.py docstring cites Phase 11 + pyxirr deferral (REFI-04 OPTIONAL closure).

    Per Plan 06-05 Task 7 spec: assert lib/refinance.py docstring contains
    "Phase 11" AND "pyxirr" — explicit deferral documentation, not silent
    omission. Pinned by reading the on-disk artifact (not __doc__) so future
    PRs that rip the docstring out fail this test even if behavior is unchanged.
    """
    source = REFINANCE_MODULE_PATH.read_text()
    assert "Phase 11" in source, (
        "D-07 violated: lib/refinance.py must cite 'Phase 11' for pyxirr deferral"
    )
    assert "pyxirr" in source, (
        "D-07 violated: lib/refinance.py must mention 'pyxirr' (REFI-04 OPTIONAL deferral)"
    )


# =========================================================================
# REFI-08 (CLI scripts/refi_npv.py) — 6 stubs, flipped Wave 4 (Plan 06-04)
# =========================================================================


def test_cli_smoke_subprocess_round_trip(tmp_path: Path) -> None:
    """REFI-08: scripts/refi_npv.py JSON-in/JSON-out round-trip via subprocess.

    Per Phase 3 D-17 + Phase 4 D-13: subprocess invocation only, never `import
    scripts.refi_npv` directly. Writes Oracle 1 (RESEARCH §"Pinned Oracles":
    rate-and-term, 200bps drop, $2k closing, 25y horizon) to a tmp_path JSON,
    invokes the CLI, parses stdout JSON, and asserts the response shape +
    refi_kind discriminator + the SC-1 / SC-2 / SC-3 surface keys are all
    present and correctly typed.

    Decimal-equality on npv is asserted against the engine-derived Oracle 1
    pin from STATE.md / lib/refinance.py module comment block ("60705.48").
    Plan 06-05 ships fixture-driven oracle parity tests; this Wave-4 smoke
    is the CLI surface contract: subprocess round-trip works end-to-end.
    """
    request_path = tmp_path / "oracle1.json"
    request_path.write_text(
        json.dumps(
            {
                "refi_kind": "rate_and_term",
                "old_loan_balance": "300000.00",
                "old_annual_rate": "0.07",
                "old_remaining_months": 300,
                "new_annual_rate": "0.05",
                "new_term_months": 300,
                "closing_costs": "2000.00",
                "discount_rate_annual": "0.05",
            }
        )
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)

    # refi_kind discriminator echoed
    assert out["refi_kind"] == "rate_and_term"

    # SC-1 anchor: positive NPV (rate-drop benefit). Decimal-string equality
    # against the engine-derived Oracle 1 pin (lib/refinance.py oracle comment).
    assert out["npv"] == "60705.48"

    # SC-2 anchor: breakeven dual-form (simple + NPV) labeled in output JSON.
    assert "breakeven" in out
    assert set(out["breakeven"].keys()) == {
        "simple_months",
        "simple_status",
        "npv_months",
        "npv_status",
    }
    assert out["breakeven"]["simple_status"] == "ok"
    assert out["breakeven"]["npv_status"] == "ok"
    assert out["breakeven"]["simple_months"] == 6  # ceil(2000/366.57)
    assert out["breakeven"]["npv_months"] == 6  # cumulative NPV crosses zero quickly

    # SC-3 anchors: cash-out-only fields are None for rate-and-term.
    assert out["cash_proceeds"] is None
    assert out["monthly_payment_delta"] is None
    assert out["total_interest_delta"] is None

    # D-04 sign convention preserved end-to-end.
    assert out["old_monthly_pi"] == "2120.34"
    assert out["new_monthly_pi"] == "1753.77"
    assert out["monthly_savings"] == "366.57"

    # Audit trail: cashflows list always present (D-15 closing_costs at t=0)
    assert isinstance(out["cashflows"], list)
    assert len(out["cashflows"]) > 0
    first_cf = out["cashflows"][0]
    assert first_cf["period"] == 0
    assert first_cf["direction"] == "outflow"
    assert first_cf["kind"] == "closing_costs"
    assert first_cf["amount"] == "-2000.00"  # SC-4 sign rigor end-to-end


def test_cli_help_does_not_import_lib_refinance() -> None:
    """D-18 (Phase 3 03-04 idiom): --help must not trigger lib.refinance,
    numpy_financial, or pydantic import.

    Spawn a fresh Python subprocess (so none are already imported via this
    test module's top-level imports — this module imports lib.refinance +
    pydantic at module scope, which would otherwise mask the laziness check)
    and run an inline check that loads scripts/refi_npv.py via
    importlib.util.spec_from_file_location with sys.argv patched to --help.

    Mirrors tests/test_affordability.py::test_cli_help_does_not_import_lib_affordability
    verbatim, with the affordability/refinance path swap.
    """
    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_refi_npv', SCRIPT)\n"
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
        "    'lib_refinance_imported': 'lib.refinance' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
        "    'pydantic_imported': 'pydantic' in sys.modules,\n"
        "}\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", inline],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["help_exit_code"] == 0
    assert payload["lib_refinance_imported"] is False, (
        "D-18 violated: lib.refinance was imported during --help (must be lazy)"
    )
    assert payload["numpy_financial_imported"] is False, (
        "D-18 violated: numpy_financial was imported during --help"
    )
    assert payload["pydantic_imported"] is False, (
        "D-18 violated: pydantic was imported during --help"
    )


def test_cli_rejects_float_closing_costs(tmp_path: Path) -> None:
    """D-19 + WR-02 inheritance: pre-validation gate emits 6-key envelope.

    closing_costs is the canonical Phase 6 money field; passing it as a raw
    JSON float (2000.00 — no quotes) must trigger the float-gate at
    scripts/refi_npv.py and emit the 6-key Pydantic envelope on stderr,
    NOT silently coerce to Decimal (Pydantic v2's permissive default).

    Mirrors tests/test_affordability.py::test_cli_rejects_float_in_loan_amount
    + tests/test_amortize.py::test_cli_rejects_float_principal — same shape,
    same envelope, different field. Reuses the Phase 5 _cli_helpers factor
    (find_json_float_loc + make_decimal_type_envelope) per Plan 06-04 Rule-1.
    """
    bad = tmp_path / "float_closing.json"
    bad.write_text(
        '{"refi_kind": "rate_and_term",'
        '"old_loan_balance": "300000.00",'
        '"old_annual_rate": "0.07",'
        '"old_remaining_months": 300,'
        '"new_annual_rate": "0.05",'
        '"new_term_months": 300,'
        '"closing_costs": 2000.00,'  # raw JSON float — should be rejected
        '"discount_rate_annual": "0.05"}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    # 6-key envelope contract (WR-02 closure)
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["closing_costs"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"].get("class") == "Decimal"
    assert err["input"] == "2000.00"  # the offending value, as Decimal-string


def test_cli_rejects_float_discount_rate(tmp_path: Path) -> None:
    """D-19 + WR-02 inheritance: float-gate fires on Rate fields too.

    discount_rate_annual is the SC-5-flagged Rate field unique to Phase 6
    (D-05 caller-supplied; no default); the float-gate must fire on it the
    same as on Money fields. Sibling-test of test_cli_rejects_float_closing_costs
    that pins the gate's coverage of BOTH Money AND Rate fields per
    CLAUDE.md FND-01 ("Decimal for all dollar amounts AND rates").
    """
    bad = tmp_path / "float_rate.json"
    bad.write_text(
        '{"refi_kind": "rate_and_term",'
        '"old_loan_balance": "300000.00",'
        '"old_annual_rate": "0.07",'
        '"old_remaining_months": 300,'
        '"new_annual_rate": "0.05",'
        '"new_term_months": 300,'
        '"closing_costs": "2000.00",'
        '"discount_rate_annual": 0.05}'  # raw JSON float — should be rejected
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    # 6-key envelope contract (WR-02 closure)
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["discount_rate_annual"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"].get("class") == "Decimal"
    assert err["input"] == "0.05"


def test_cli_error_envelope_uniformity(tmp_path: Path) -> None:
    """D-19 + WR-02 closure: float-gate AND ValidationError emit identical 6-key shape.

    The WR-02 closure contract (Phase 3 03-06) mandates that ALL
    ValidationError-class boundary surfaces emit the SAME 6-key Pydantic v2
    envelope shape on stderr. Phase 9 / Phase 10 downstream consumers parse
    stderr as one uniform JSON contract regardless of WHICH validator fired.

    This test exercises both arms of the contract:
      (a) JSON-float-gate path: closing_costs as raw float → manually-built
          envelope via scripts._cli_helpers.make_decimal_type_envelope.
      (b) Pydantic ValidationError path: cross-field _validate_common
          validator (D-09 — after_tax_mode=True without marginal_tax_rate
          + filing_status) → e.json() pass-through.

    Both must produce a JSON list whose first element has the SAME 6-key set:
    {type, loc, msg, input, url, ctx}. If a future PR drifts one path's
    envelope shape (e.g., adds a 'severity' key, drops 'ctx'), this test
    fails before the contract drift reaches Phase 9 consumers.

    Mirrors tests/test_amortize.py::test_cli_error_envelope_uniformity (Phase 3
    03-06 anchor).
    """
    expected_keys = {"type", "loc", "msg", "input", "url", "ctx"}

    # (a) Float-gate path: closing_costs as raw JSON float → manually-built
    # envelope via scripts._cli_helpers.make_decimal_type_envelope.
    float_path = tmp_path / "float_gate.json"
    float_path.write_text(
        '{"refi_kind": "rate_and_term",'
        '"old_loan_balance": "300000.00",'
        '"old_annual_rate": "0.07",'
        '"old_remaining_months": 300,'
        '"new_annual_rate": "0.05",'
        '"new_term_months": 300,'
        '"closing_costs": 2000.00,'
        '"discount_rate_annual": "0.05"}'
    )
    float_result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(float_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert float_result.returncode == 2
    float_errors = json.loads(float_result.stderr)
    assert isinstance(float_errors, list)
    assert len(float_errors) >= 1
    float_err = float_errors[0]
    assert set(float_err.keys()) == expected_keys, (
        f"float-gate envelope drift: keys={set(float_err.keys())}; expected {expected_keys}"
    )

    # (b) Pydantic ValidationError path: trigger _validate_common cross-field
    # validator (D-09 — after_tax_mode=True without marginal_tax_rate +
    # filing_status). This path produces a value_error with ctx populated by
    # Pydantic's @model_validator surface — known-good 6-key shape that
    # mirrors the cross-shape contract pinned by tests/test_amortize.py
    # (Phase 3 03-06 idiom).
    #
    # Note: a "missing required field" ValidationError surface would emit
    # only 5 of the 6 keys (Pydantic's `missing` error type omits ctx); the
    # WR-02 closure contract is satisfied by the validator-error surface
    # which is the cross-field path Phase 9/10 consumers actually narrate.
    validator_path = tmp_path / "validator_error.json"
    validator_path.write_text(
        '{"refi_kind": "rate_and_term",'
        '"old_loan_balance": "300000.00",'
        '"old_annual_rate": "0.07",'
        '"old_remaining_months": 300,'
        '"new_annual_rate": "0.05",'
        '"new_term_months": 300,'
        '"closing_costs": "2000.00",'
        '"discount_rate_annual": "0.05",'
        '"after_tax_mode": true}'  # missing marginal_tax_rate + filing_status
    )
    validator_result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(validator_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validator_result.returncode == 2
    validator_errors = json.loads(validator_result.stderr)
    assert isinstance(validator_errors, list)
    assert len(validator_errors) >= 1
    validator_err = validator_errors[0]
    assert set(validator_err.keys()) == expected_keys, (
        f"ValidationError envelope drift: keys={set(validator_err.keys())}; "
        f"expected {expected_keys}"
    )

    # Symmetric contract: both errors share the SAME key-set (the WR-02 closure
    # promise — Phase 9 / Phase 10 narration parses one shape uniformly).
    assert set(float_err.keys()) == set(validator_err.keys()), (
        "WR-02 violated: float-gate and ValidationError emit different envelope shapes"
    )


def test_cli_help_cites_references_refi_npv() -> None:
    """SC-5 verbatim: scripts/refi_npv.py --help epilog cites references/refi-npv.md
    AND the canonical sign-convention phrase.

    ROADMAP Phase 6 SC-5 mandates: 'references/refi-npv.md documents the
    borrower-perspective sign convention explicitly ("outflows negative,
    savings positive") AND is cited in the script's --help text.'

    This test pins BOTH literal strings in the --help output:
      (1) 'see references/refi-npv.md' — the documentation cite (D-16
          belt-and-suspenders surface 4 of 4)
      (2) 'outflows negative, savings positive' — the verbatim D-04 sign
          convention phrase (D-16 belt-and-suspenders surface)

    Pinning the literal strings (not paraphrases) guards against future PRs
    silently dropping the SC-5 mandate; the test fails immediately if either
    citation is reworded out of the epilog. Per Plan 06-04 deviation_rule
    Rule-2: SC-5 string literals are LOAD-BEARING.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    # SC-5 surface 1: documentation cite (literal phrase)
    assert "see references/refi-npv.md" in result.stdout, (
        "SC-5 violated: --help epilog must cite 'see references/refi-npv.md'"
    )
    # SC-5 surface 2: verbatim sign-convention phrase (D-04)
    assert "outflows negative, savings positive" in result.stdout, (
        "SC-5 violated: --help epilog must contain literal 'outflows negative, savings positive'"
    )


# =========================================================================
# REFI-09 (references/refi-npv.md) — 3 stubs
# - 2 flipped Wave 6 (Plan 06-06: doc body)
# - 1 flipped Wave 2 (Plan 06-01: lib/refinance.py module docstring cite)
# =========================================================================


def test_refi_npv_doc_sections_present() -> None:
    """SC-5: references/refi-npv.md ships ≥ 250 lines with required sections.

    Per Plan 06-06 acceptance criteria + 06-PATTERNS §"references/refi-npv.md",
    the document must mirror references/arm-mechanics.md's section-per-
    convention discipline with these 7 numbered sections + Citations:

      §1 Sign Convention (SC-5 verbatim phrase headline)
      §2 Borrower NPV Formula
      §3 Discount-Rate Selection (D-05)
      §4 Cashflow Inventory: Rate-and-Term vs. Cash-Out
      §5 Simple vs. NPV-Based Breakeven (REFI-03)
      §6 After-Tax Optional Mode (D-09)
      §7 v1 Carve-Outs (D-08 PMI/MIP + D-12 closing-costs OOP + D-07 pyxirr)
      §8 Citations (Investopedia + Federal Reserve + IRS Pub 936 + numpy-financial)

    The min_lines: 250 contract is Plan 06-06 frontmatter must_haves.artifacts.
    """
    assert REFI_NPV_DOC_PATH.exists(), (
        f"references/refi-npv.md must exist at {REFI_NPV_DOC_PATH} (REFI-09 / SC-5)"
    )
    text = REFI_NPV_DOC_PATH.read_text()

    # ≥ 250 lines per Plan 06-06 frontmatter min_lines contract.
    line_count = len(text.splitlines())
    assert line_count >= 250, (
        f"references/refi-npv.md must be ≥ 250 lines (got {line_count}); "
        "Plan 06-06 must_haves.artifacts contract"
    )

    # All 8 numbered H2 section headers present (regex matches '## N. ...').
    section_headers = re.findall(r"^## (\d+)\.\s", text, flags=re.MULTILINE)
    expected_section_numbers = ["1", "2", "3", "4", "5", "6", "7", "8"]
    assert section_headers == expected_section_numbers, (
        f"references/refi-npv.md must have 8 numbered H2 sections in order "
        f"(1..8); got {section_headers}. Per Plan 06-06 §1-7 + Citations §8."
    )


def test_refi_npv_doc_sign_convention_phrase() -> None:
    """SC-5 verbatim: doc contains literal 'outflows negative, savings positive'.

    Per ROADMAP § Phase 6 SC-5 + Plan 06-06 frontmatter must_haves.truths,
    the LITERAL phrase 'outflows negative, savings positive' MUST appear in
    the first H2 section of references/refi-npv.md. This is the load-bearing
    sign-convention contract — the engine's RefiCashflow validator messages,
    lib/refinance.py module docstring, and scripts/refi_npv.py --help epilog
    all cite this doc as the canonical source for the convention (D-16
    belt-and-suspenders surfaces 1, 2, 4 cite this surface 3).
    """
    assert REFI_NPV_DOC_PATH.exists(), (
        f"references/refi-npv.md must exist at {REFI_NPV_DOC_PATH} (REFI-09 / SC-5)"
    )
    text = REFI_NPV_DOC_PATH.read_text()

    # SC-5 verbatim presence anywhere in the doc.
    assert "outflows negative, savings positive" in text, (
        "SC-5 violated: references/refi-npv.md must contain literal phrase "
        "'outflows negative, savings positive' (D-04 borrower-perspective "
        "sign convention; D-16 belt-and-suspenders surface 3)"
    )

    # Plan 06-06 must_haves.truths: phrase must appear in the FIRST H2 section.
    # Slice the doc from the first '## ' header to the second '## ' header
    # (or end-of-file if only one) and assert the phrase falls inside.
    first_h2_match = re.search(r"^## ", text, flags=re.MULTILINE)
    assert first_h2_match is not None, (
        "references/refi-npv.md must have at least one H2 section header (no '## ' found)"
    )
    first_h2_start = first_h2_match.start()
    second_h2_match = re.search(r"^## ", text[first_h2_start + 3 :], flags=re.MULTILINE)
    first_section_end = (
        first_h2_start + 3 + second_h2_match.start() if second_h2_match is not None else len(text)
    )
    first_section = text[first_h2_start:first_section_end]
    assert "outflows negative, savings positive" in first_section, (
        "SC-5 violated: literal phrase 'outflows negative, savings positive' "
        "must appear in the FIRST H2 section of references/refi-npv.md "
        "(Plan 06-06 must_haves.truths). The headline section IS the contract."
    )


def test_lib_refinance_module_docstring_cites() -> None:
    """D-16: lib/refinance.py module docstring cites references/refi-npv.md.

    Belt-and-suspenders sign-convention surface (D-16):
      (1) RefiCashflow validator messages cite the doc
      (2) lib/refinance.py module docstring cites the doc (THIS test)
      (3) references/refi-npv.md headlines the phrase verbatim per SC-5 (Plan 06-06)
      (4) scripts/refi_npv.py --help epilog includes the doc cite per SC-5 (Plan 06-04)

    REFI-09 anchor + SC-5 verbatim phrase ("outflows negative, savings positive")
    must also appear in the module docstring so the contract is documented
    immediately at the import boundary, not only at the doc layer.
    """
    # Read the module file directly (not via __doc__) so we exercise the
    # on-disk artifact that future readers see and that grep gates target.
    source = REFINANCE_MODULE_PATH.read_text()
    assert REFINANCE_MODULE_PATH.exists(), (
        f"lib/refinance.py must exist at {REFINANCE_MODULE_PATH} (D-16 anchor)"
    )
    # D-16 belt-and-suspenders surface (2): module docstring cites the doc.
    assert "references/refi-npv.md" in source, (
        "lib/refinance.py module docstring must cite references/refi-npv.md (D-16)"
    )
    # SC-5 verbatim sign-convention phrase must surface in the module too.
    assert "outflows negative, savings positive" in source, (
        "lib/refinance.py module docstring must contain SC-5 verbatim phrase "
        "'outflows negative, savings positive' (D-04 + D-16)"
    )


# =========================================================================
# SC-4 sign-validator (model-layer) — 4 stubs, flipped Wave 1 (Plan 06-01)
# =========================================================================


def test_refi_cashflow_outflow_positive_rejected() -> None:
    """SC-4 verbatim: RefiCashflow(direction='outflow', amount=positive) raises ValidationError.

    Per D-04 borrower-perspective sign convention (outflows negative, savings
    positive), constructing an outflow with a positive amount is an immediate
    sign-direction violation that the @model_validator _direction_sign_consistency
    rejects at construction time. Match the predicate's error-message substring
    cited in 06-RESEARCH §"Oracle 4" to defend against silent message drift.
    """
    with pytest.raises(ValidationError, match="outflow cashflow must have non-positive amount"):
        RefiCashflow(
            period=0,
            direction="outflow",
            amount=Decimal("2000.00"),
            kind="closing_costs",
        )


def test_refi_cashflow_inflow_negative_rejected() -> None:
    """SC-4 verbatim: RefiCashflow(direction='inflow', amount=negative) raises ValidationError.

    Mirror sign-direction violation: an inflow with a negative amount is the
    opposite-side construction error and is rejected by the same validator
    (D-04 + 06-RESEARCH §"Oracle 4").
    """
    with pytest.raises(ValidationError, match="inflow cashflow must have non-negative amount"):
        RefiCashflow(
            period=1,
            direction="inflow",
            amount=Decimal("-100.00"),
            kind="monthly_savings",
        )


def test_refi_cashflow_zero_accepted_either_dir() -> None:
    """D-14: RefiCashflow with amount=Decimal('0.00') in either direction is valid.

    Zero cashflows have no sign hazard (the validator fires only on strict-sign
    mismatch: outflow with amount > 0 OR inflow with amount < 0). This test
    pins the explicit D-14 carve-out so a future "tighten the validator" PR
    cannot silently start rejecting zero amounts.
    """
    # Both should construct without raising — Pydantic returns the validated instance.
    outflow_zero = RefiCashflow(
        period=0,
        direction="outflow",
        amount=Decimal("0.00"),
        kind="closing_costs",
    )
    inflow_zero = RefiCashflow(
        period=0,
        direction="inflow",
        amount=Decimal("0.00"),
        kind="cash_proceeds",
    )
    assert outflow_zero.amount == Decimal("0.00")
    assert inflow_zero.amount == Decimal("0.00")
    assert outflow_zero.direction == "outflow"
    assert inflow_zero.direction == "inflow"


def test_refi_cashflow_correctly_signed_passes() -> None:
    """SC-4 happy path: outflow with negative amount + inflow with positive amount construct cleanly.

    Verifies the full SC-4 contract is symmetric: rejecting wrong-sign
    constructions does not also reject right-sign constructions. Pins the
    happy-path so the validator's logic remains a strict matched-pair check
    (not an over-broad reject).
    """
    closing_costs = RefiCashflow(
        period=0,
        direction="outflow",
        amount=Decimal("-2000.00"),
        kind="closing_costs",
    )
    monthly_savings = RefiCashflow(
        period=1,
        direction="inflow",
        amount=Decimal("366.57"),
        kind="monthly_savings",
    )
    assert closing_costs.amount == Decimal("-2000.00")
    assert closing_costs.direction == "outflow"
    assert closing_costs.kind == "closing_costs"
    assert monthly_savings.amount == Decimal("366.57")
    assert monthly_savings.direction == "inflow"
    assert monthly_savings.kind == "monthly_savings"


# =========================================================================
# Cross-cutting — 2 stubs
# - test_refi_cashflow_kind_citation_coverage flipped Wave 5 (Plan 06-05) — every Literal kind appears in ≥1 fixture
# - test_after_tax_mode_validator_requires_all flipped Wave 3 (Plan 06-03) — D-09 cross-field validator
# =========================================================================


def test_refi_cashflow_kind_citation_coverage() -> None:
    """D-03: every value of RefiCashflow.kind Literal appears in ≥1 committed fixture (mirrors Phase 5 applied_cap).

    Per Plan 06-05 Task 7 spec: iterate fixtures in tests/fixtures/refinance/,
    collect every RefiCashflow.kind Literal value across all expected.cashflows_kinds
    lists, assert each of {closing_costs, cash_proceeds, monthly_savings,
    monthly_payment_delta, tax_shield} appears in ≥1 fixture. Mirrors Phase 5's
    applied_cap Literal coverage convention.
    """
    fixture_dir = Path(__file__).resolve().parent / "fixtures" / "refinance"
    required_kinds = {
        "closing_costs",
        "cash_proceeds",
        "monthly_savings",
        "monthly_payment_delta",
        "tax_shield",
    }
    seen: set[str] = set()
    fixtures_scanned = 0
    for fpath in sorted(fixture_dir.glob("*.json")):
        fx = json.loads(fpath.read_text())
        kinds = fx.get("expected", {}).get("cashflows_kinds", [])
        seen.update(kinds)
        fixtures_scanned += 1
    assert fixtures_scanned >= 6, (
        f"D-03: at least 6 refinance fixtures expected; found {fixtures_scanned}"
    )
    missing = required_kinds - seen
    assert not missing, (
        f"D-03 citation coverage violated: kinds {missing} missing from any "
        f"fixture's expected.cashflows_kinds. Seen: {sorted(seen)}; "
        f"required: {sorted(required_kinds)}"
    )


def test_refi_after_tax_mode_engine(
    refinance_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """WR-01 (REVIEW.md fix): exercise the after_tax_mode_smoke.json fixture's
    pinned engine outputs at the engine layer (not just the kind-citation
    coverage scan).

    Pre-fix: the only test that touched after_tax_mode_smoke.json was
    test_refi_cashflow_kind_citation_coverage, which globs *.json and asserts
    expected.cashflows_kinds contains the required Literals — it does NOT call
    evaluate(). The pinned numerical contract (npv='60705.48',
    after_tax_npv='96584.52', tax_shield_sample.amount='300.00') was therefore
    unprotected at engine-output level. A regression in
    _compute_tax_shield_cashflows (wrong period indexing, wrong
    qualified_loan_limit branch, wrong marginal_tax_rate multiplication) would
    not be caught.

    This test invokes evaluate() on the fixture and asserts strict Decimal
    equality on npv, after_tax_npv, and the first-period tax_shield cashflow
    (D-04 money-discipline: never pytest.approx for money).
    """
    fx = refinance_fixture("after_tax_mode_smoke")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate

    resp = evaluate(req)
    expected = fx["expected"]

    # Pre-tax NPV pinned (cross-check against Oracle 1; same scenario)
    assert Decimal(resp.npv) == Decimal(expected["npv"]), (
        f"after-tax-mode pre-tax NPV drift: got {resp.npv} != expected {expected['npv']}"
    )

    # After-tax NPV: D-09 contract — tax_shield cashflows added before NPV recompute
    assert resp.after_tax_npv is not None, (
        "D-09 violated: after_tax_npv must be populated when after_tax_mode=True"
    )
    assert Decimal(resp.after_tax_npv) == Decimal(expected["after_tax_npv"]), (
        f"after_tax_npv drift: got {resp.after_tax_npv} != expected {expected['after_tax_npv']}"
    )
    # Tax shield strictly improves PV (more money in borrower's pocket)
    assert Decimal(resp.after_tax_npv) > Decimal(resp.npv), (
        "after_tax_npv should exceed pre-tax npv (tax shield is an inflow stream)"
    )

    # First-period tax_shield cashflow pinned (D-03 kind coverage anchor)
    sample = expected["tax_shield_sample"]
    tax_shield_cashflows = [cf for cf in resp.cashflows if cf.kind == "tax_shield"]
    assert len(tax_shield_cashflows) > 0, (
        "WR-01: after_tax_mode=True must emit tax_shield cashflows into the audit trail"
    )
    first_shield = next(cf for cf in tax_shield_cashflows if cf.period == sample["period"])
    assert first_shield.direction == sample["direction"]
    assert Decimal(first_shield.amount) == Decimal(sample["amount"]), (
        f"first tax_shield amount drift: got {first_shield.amount} != expected "
        f"{sample['amount']} (would catch _compute_tax_shield_cashflows regressions)"
    )
    assert first_shield.kind == sample["kind"]


def test_after_tax_mode_validator_requires_all() -> None:
    """D-09: when after_tax_mode=True, both marginal_tax_rate AND filing_status are required (else ValidationError).

    The cross-field validator `_validate_common` (Wave 1) is exercised through both
    request leaf models (RateAndTermRefiRequest + CashOutRefiRequest). When
    after_tax_mode=True, omitting EITHER marginal_tax_rate OR filing_status raises
    ValidationError with a message that cites D-09 + RUL-11 (lib.rules.irs_pub936
    qualified_loan_limit). The happy path (all three supplied) constructs cleanly.

    Wave 3 / Plan 06-03 anchor — the validator was shipped at Wave 1 (Plan 06-01)
    but only exercised at the engine-consumer level here, where the after-tax
    tax_shield branch lights up (lib.refinance._compute_tax_shield_cashflows).
    """
    base_kwargs: dict[str, Any] = {
        "old_loan_balance": Decimal("300000.00"),
        "old_annual_rate": Decimal("0.07"),
        "old_remaining_months": 300,
        "new_annual_rate": Decimal("0.05"),
        "new_term_months": 300,
        "closing_costs": Decimal("2000.00"),
        "discount_rate_annual": Decimal("0.05"),
    }

    # Rejection 1: missing marginal_tax_rate (filing_status supplied)
    with pytest.raises(
        ValidationError,
        match="after_tax_mode=True requires both marginal_tax_rate and filing_status",
    ):
        RateAndTermRefiRequest(
            **base_kwargs,
            after_tax_mode=True,
            marginal_tax_rate=None,
            filing_status="single",
        )

    # Rejection 2: missing filing_status (marginal_tax_rate supplied)
    with pytest.raises(
        ValidationError,
        match="after_tax_mode=True requires both marginal_tax_rate and filing_status",
    ):
        RateAndTermRefiRequest(
            **base_kwargs,
            after_tax_mode=True,
            marginal_tax_rate=Decimal("0.24"),
            filing_status=None,
        )

    # Rejection 3: both missing (after_tax_mode=True with neither)
    with pytest.raises(
        ValidationError,
        match="after_tax_mode=True requires both marginal_tax_rate and filing_status",
    ):
        CashOutRefiRequest(
            **base_kwargs,
            cash_out_amount=Decimal("50000.00"),
            after_tax_mode=True,
            marginal_tax_rate=None,
            filing_status=None,
        )

    # Happy path: all three supplied → constructs cleanly (rate-and-term)
    rate_and_term_ok = RateAndTermRefiRequest(
        **base_kwargs,
        after_tax_mode=True,
        marginal_tax_rate=Decimal("0.24"),
        filing_status="mfj",
    )
    assert rate_and_term_ok.after_tax_mode is True
    assert rate_and_term_ok.marginal_tax_rate == Decimal("0.24")
    assert rate_and_term_ok.filing_status == "mfj"
    assert rate_and_term_ok.refi_kind == "rate_and_term"

    # Happy path: all three supplied → constructs cleanly (cash-out)
    cash_out_ok = CashOutRefiRequest(
        **base_kwargs,
        cash_out_amount=Decimal("50000.00"),
        after_tax_mode=True,
        marginal_tax_rate=Decimal("0.32"),
        filing_status="single",
    )
    assert cash_out_ok.after_tax_mode is True
    assert cash_out_ok.marginal_tax_rate == Decimal("0.32")
    assert cash_out_ok.filing_status == "single"
    assert cash_out_ok.refi_kind == "cash_out"

    # Happy path: after_tax_mode=False → tax fields can be None (default carry-through)
    rate_and_term_off = RateAndTermRefiRequest(**base_kwargs)
    assert rate_and_term_off.after_tax_mode is False
    assert rate_and_term_off.marginal_tax_rate is None
    assert rate_and_term_off.filing_status is None
