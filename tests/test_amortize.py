"""Tests for lib/amortize.py engine + scripts/amortize.py CLI (Phase 3).

Coverage matrix:
  - AMRT-01: lib/amortize.py wraps numpy-financial PMT/IPMT/PPMT (structural)
  - AMRT-02: fixed-rate monthly schedule generation (4 golden oracles)
  - AMRT-03: biweekly true + half-monthly modes (D-01 + D-04)
  - AMRT-04: extra principal entries (one-shot, recurring, step-up, cap)
  - AMRT-05: final-period principal cleanup (D-09 cents-drift absorption)
  - AMRT-06: scripts/amortize.py CLI surface (Task 3, appended below)
  - AMRT-07: sum(principal+extra) == original_principal exactly
  - AMRT-08: monthly_pi parity against the 4 pinned oracles

Locked-decision coverage (per CONTEXT.md D-01..D-19):
  - D-02: biweekly_mode validity / default (validator + engine default)
  - D-12: origination_date synthesis when None (engine-time, not model)
  - D-13: relativedelta month-end clipping (Jan-31 -> Feb-28)
  - D-15: Schedule.total_interest == payments[-1].cumulative_interest (validator
    ratification on real engine output)

Money discipline (CLAUDE.md):
  - Decimal exact equality everywhere; no fuzzy comparators for money.
  - Decimal constructed from STRINGS (never from Python floats).
  - All JSON fixture values are strings; this module decodes them with Decimal(s).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from lib.amortize import AmortizeRequest, ExtraPrincipalEntry, build_schedule
from lib.models import Loan, Schedule
from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

FOUR_ORACLE_IDS = [
    "wikipedia_200k_30yr",
    "cfpb_le_162k_30yr",
    "computed_400k_30yr",
    "computed_200k_15yr",
]
AMORTIZE_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "amortize.py"
SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "amortize.py"
"""Phase 3 CLI lives at project root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""


def assert_schedule_invariants(schedule: Schedule, original_principal: Decimal) -> None:
    """Asserts AMRT-07 + D-11 + D-15 invariants on every produced schedule.

    - AMRT-07 / D-11: sum(principal + extra_principal) == original_principal exactly.
    - D-09: payments[-1].balance is exactly Decimal("0.00").
    - D-15: Schedule.total_interest == payments[-1].cumulative_interest exactly.
    """
    sum_principal = sum((p.principal for p in schedule.payments), start=Decimal("0.00"))
    sum_extra = sum((p.extra_principal for p in schedule.payments), start=Decimal("0.00"))
    assert sum_principal + sum_extra == original_principal, (
        f"AMRT-07/D-11 violated: sum(principal+extra)={sum_principal + sum_extra} "
        f"!= original_principal={original_principal}"
    )
    assert schedule.payments[-1].balance == Decimal("0.00"), (
        f"D-09 violated: final balance != 0.00: {schedule.payments[-1].balance}"
    )
    assert schedule.total_interest == schedule.payments[-1].cumulative_interest, (
        f"D-15 violated: total_interest={schedule.total_interest} "
        f"!= payments[-1].cumulative_interest={schedule.payments[-1].cumulative_interest}"
    )


# ---------------------------------------------------------------------------
# AMRT-01: structural — lib/amortize.py wraps numpy-financial
# ---------------------------------------------------------------------------


def test_amortize_module_uses_numpy_financial() -> None:
    """AMRT-01: lib/amortize.py wraps numpy-financial; does NOT reimplement.

    Structural check: read the module source and assert the wrapping idiom is
    present. This guards against a future refactor that hand-rolls the PMT
    formula and inadvertently breaks the AMRT-01 contract.
    """
    src = AMORTIZE_MODULE_PATH.read_text()
    assert "import numpy_financial as npf" in src, "AMRT-01: numpy_financial import missing"
    assert "npf.pmt(" in src, "AMRT-01: npf.pmt call missing (engine not wrapping)"
    # Bug-avoidance docstring grep:
    assert "issues/130" in src, "Bug #130 fv-sign avoidance comment missing"
    assert "issues/131" in src, "Bug #131 irr-arch avoidance comment missing"


# ---------------------------------------------------------------------------
# AMRT-02 / AMRT-08: parametrized golden-oracle parity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_id",
    [pytest.param(fid, id=fid) for fid in FOUR_ORACLE_IDS],
)
def test_fixed_rate_oracle(
    fixture_id: str,
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-08: build_schedule's monthly_pi matches each pinned oracle exactly.

    The four oracles in tests/fixtures/golden_pmt.json (Wikipedia, CFPB LE,
    computed $400k, computed $200k/15yr) are anchored by external sources;
    this test pins them as the math-correctness contract.
    """
    fx = golden_fixture(fixture_id)
    # Hand: each oracle's expected_monthly_pi is the regulator/source-published value.
    # Wikipedia: 200k/6.5/30 -> 1264.14; CFPB LE: 162k/3.875/30 -> 761.78;
    # computed 400k/6.5/30 -> 2528.27; computed 200k/7/15 -> 1797.66.
    loan = Loan(
        principal=Decimal(fx["principal"]),
        annual_rate=Decimal(fx["annual_rate"]),
        term_months=fx["term_months"],
        origination_date=date(2026, 5, 1),
    )
    schedule = build_schedule(loan)
    assert schedule.monthly_pi == Decimal(fx["expected_monthly_pi"])
    assert_schedule_invariants(schedule, loan.principal)


# ---------------------------------------------------------------------------
# AMRT-03: biweekly true + half-monthly
# ---------------------------------------------------------------------------


def test_biweekly_true_oracle(
    amortize_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-03 / D-01 / D-04: biweekly-true accelerates to the fixture-pinned period count.

    Wikipedia-oracle scaled to biweekly-true mode. monthly_pi is the IMPLIED
    monthly P&I (rate/12); the per-biweekly cashflow is half of that. Period
    count is engine-empirical (~628 for 200k/6.5/30 per RESEARCH 3.1).
    """
    fx = amortize_fixture("biweekly_true_200k_6_5")
    # Hand: 200k @ 6.5% / 30yr biweekly-true -> 628 periods exactly (engine pinned).
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
        origination_date=date.fromisoformat(fx["loan"]["origination_date"]),
    )
    schedule = build_schedule(loan, frequency="biweekly", biweekly_mode="true")
    summary = fx["expected_schedule_summary"]
    assert len(schedule.payments) == summary["num_payments"]
    assert schedule.monthly_pi == Decimal(summary["monthly_pi"])
    assert schedule.total_interest == Decimal(summary["total_interest"])
    assert schedule.final_payment_adjusted is summary["final_payment_adjusted"]
    # Pin first + last payments to the engine-emitted values verbatim.
    first = schedule.payments[0]
    fp = summary["first_payment"]
    assert first.period == fp["period"]
    assert first.payment_date == date.fromisoformat(fp["payment_date"])
    assert first.payment == Decimal(fp["payment"])
    assert first.principal == Decimal(fp["principal"])
    assert first.interest == Decimal(fp["interest"])
    assert first.extra_principal == Decimal(fp["extra_principal"])
    assert first.balance == Decimal(fp["balance"])
    last = schedule.payments[-1]
    lp = summary["last_payment"]
    assert last.period == lp["period"]
    assert last.balance == Decimal("0.00")
    assert last.cumulative_principal == Decimal(lp["cumulative_principal"])
    assert_schedule_invariants(schedule, loan.principal)


def test_biweekly_half_monthly_oracle(
    amortize_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-03 / D-04 / RESEARCH 3.2: half-monthly biweekly emits 360 monthly rows.

    Half-monthly mode: rate/12 + monthly amortization (interest still booked
    monthly per D-04 / RESEARCH 3.2 Option A); biweekly cashflow is a billing
    decoration consumers handle outside the engine. Wikipedia-oracle parity
    on monthly_pi.
    """
    fx = amortize_fixture("biweekly_half_monthly_200k_6_5")
    # Hand: half-monthly is monthly amortization with biweekly billing decoration.
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
        origination_date=date.fromisoformat(fx["loan"]["origination_date"]),
    )
    schedule = build_schedule(loan, frequency="biweekly", biweekly_mode="half-monthly")
    summary = fx["expected_schedule_summary"]
    assert len(schedule.payments) == 360
    assert schedule.monthly_pi == Decimal("1264.14")
    assert schedule.total_interest == Decimal(summary["total_interest"])
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert_schedule_invariants(schedule, loan.principal)


def test_biweekly_mode_defaults_to_true_when_omitted() -> None:
    """D-02 default: build_schedule(loan, frequency='biweekly') == biweekly_mode='true'.

    The default is applied INSIDE build_schedule (per D-02 in lib/amortize.py
    docstring); the model preserves "what the caller provided".
    """
    # Hand: biweekly-true accelerates to ~628 periods on 200k/6.5/30; defaulting
    # mode=None to "true" should produce the SAME period count as explicit "true".
    loan = Loan(
        principal=Decimal("200000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2026, 5, 1),
    )
    default_schedule = build_schedule(loan, frequency="biweekly")
    explicit_schedule = build_schedule(loan, frequency="biweekly", biweekly_mode="true")
    assert len(default_schedule.payments) == len(explicit_schedule.payments)
    assert default_schedule.monthly_pi == explicit_schedule.monthly_pi
    assert default_schedule.total_interest == explicit_schedule.total_interest
    assert_schedule_invariants(default_schedule, loan.principal)


def test_amortize_request_rejects_biweekly_mode_when_monthly() -> None:
    """D-02 validator: AmortizeRequest rejects frequency=monthly + biweekly_mode='true'.

    The validator (AmortizeRequest._biweekly_mode_consistency) raises at model
    construction time, BEFORE build_schedule is called.
    """
    loan = Loan(
        principal=Decimal("200000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2026, 5, 1),
    )
    # Hand: D-02 requires biweekly_mode is None when frequency='monthly'.
    with pytest.raises(ValidationError) as excinfo:
        AmortizeRequest(loan=loan, frequency="monthly", biweekly_mode="true")
    assert "biweekly_mode must be None" in str(excinfo.value)


# ---------------------------------------------------------------------------
# AMRT-04: extra principal entries (D-05 / D-07 / D-08)
# ---------------------------------------------------------------------------


def test_extra_oneshot_period_60(
    amortize_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-04 / D-05: one-shot extra principal fires only at its period."""
    fx = amortize_fixture("extra_oneshot_5k_period_60")
    # Hand: $5000 extra at period 60; surrounding periods have extra=0.00.
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
        origination_date=date.fromisoformat(fx["loan"]["origination_date"]),
    )
    entries = [
        ExtraPrincipalEntry(
            period=e["period"],
            amount=Decimal(e["amount"]),
            recurring=e["recurring"],
        )
        for e in fx["extra_principal"]
    ]
    schedule = build_schedule(loan, extra_principal=entries)
    summary = fx["expected_schedule_summary"]
    assert len(schedule.payments) == summary["num_payments"]
    # period 60 = index 59 (1-indexed -> 0-indexed)
    assert schedule.payments[59].extra_principal == Decimal(summary["extra_at_period_60"])
    assert schedule.payments[58].extra_principal == Decimal(summary["extra_at_period_59"])
    assert schedule.payments[60].extra_principal == Decimal(summary["extra_at_period_61"])
    assert schedule.final_payment_adjusted is True
    assert_schedule_invariants(schedule, loan.principal)


def test_extra_recurring_200_from_period_1(
    amortize_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-04 / D-05: recurring extra principal fires at every period from start period."""
    fx = amortize_fixture("extra_recurring_200_30yr")
    # Hand: $200/period recurring from period 1 shortens 360-mo schedule meaningfully.
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
        origination_date=date.fromisoformat(fx["loan"]["origination_date"]),
    )
    entries = [
        ExtraPrincipalEntry(
            period=e["period"],
            amount=Decimal(e["amount"]),
            recurring=e["recurring"],
        )
        for e in fx["extra_principal"]
    ]
    schedule = build_schedule(loan, extra_principal=entries)
    summary = fx["expected_schedule_summary"]
    assert len(schedule.payments) == summary["num_payments"]
    assert len(schedule.payments) < 360  # shortened
    assert schedule.payments[0].extra_principal == Decimal(summary["extra_at_period_1"])
    assert schedule.payments[99].extra_principal == Decimal(summary["extra_at_period_100"])
    assert_schedule_invariants(schedule, loan.principal)


def test_extra_step_up_200_to_300_at_period_13(
    amortize_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-04 / D-05 override: later recurring entry overrides earlier from its own period."""
    fx = amortize_fixture("extra_step_up_200_to_300")
    # Hand: $200 from period 1, $300 from period 13. Periods 1-12 see $200, 13+ see $300.
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
        origination_date=date.fromisoformat(fx["loan"]["origination_date"]),
    )
    entries = [
        ExtraPrincipalEntry(
            period=e["period"],
            amount=Decimal(e["amount"]),
            recurring=e["recurring"],
        )
        for e in fx["extra_principal"]
    ]
    schedule = build_schedule(loan, extra_principal=entries)
    summary = fx["expected_schedule_summary"]
    assert len(schedule.payments) == summary["num_payments"]
    assert schedule.payments[0].extra_principal == Decimal(summary["extra_at_period_1"])
    assert schedule.payments[11].extra_principal == Decimal(summary["extra_at_period_12"])
    assert schedule.payments[12].extra_principal == Decimal(summary["extra_at_period_13"])
    assert schedule.payments[49].extra_principal == Decimal(summary["extra_at_period_50"])
    assert_schedule_invariants(schedule, loan.principal)


def test_extra_caps_at_remaining_balance_silently(
    amortize_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-04 / D-08: recurring extra-principal that overshoots remaining balance
    silently caps at the balance and sets final_payment_adjusted=True.
    """
    fx = amortize_fixture("extra_caps_at_balance")
    # Hand: $1000/12mo loan with $50000 recurring extra: cap fires period 1,
    # schedule terminates immediately, flag is True (D-08 surface signal).
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
        origination_date=date.fromisoformat(fx["loan"]["origination_date"]),
    )
    entries = [
        ExtraPrincipalEntry(
            period=e["period"],
            amount=Decimal(e["amount"]),
            recurring=e["recurring"],
        )
        for e in fx["extra_principal"]
    ]
    schedule = build_schedule(loan, extra_principal=entries)
    assert len(schedule.payments) == fx["expected_schedule_summary"]["num_payments"]
    assert schedule.final_payment_adjusted is True
    assert_schedule_invariants(schedule, loan.principal)


# ---------------------------------------------------------------------------
# AMRT-05: final-period principal cleanup (D-09)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_id",
    [pytest.param(fid, id=fid) for fid in FOUR_ORACLE_IDS],
)
def test_final_payment_cleans_to_zero_fixed(
    fixture_id: str,
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-05 / D-09: final-period balance lands at exactly Decimal('0.00') for all 4 oracles.

    Cents-drift values (-$4.58 to +$2.90 per RESEARCH 5) are absorbed by the
    final-period cleanup; the contract is exact zero.
    """
    fx = golden_fixture(fixture_id)
    # Hand: each oracle ends at balance=0.00 exactly after cents-drift cleanup.
    loan = Loan(
        principal=Decimal(fx["principal"]),
        annual_rate=Decimal(fx["annual_rate"]),
        term_months=fx["term_months"],
        origination_date=date(2026, 5, 1),
    )
    schedule = build_schedule(loan)
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert_schedule_invariants(schedule, loan.principal)


@pytest.mark.parametrize(
    "biweekly_mode",
    [pytest.param("true", id="true"), pytest.param("half-monthly", id="half-monthly")],
)
def test_final_payment_cleans_to_zero_biweekly(biweekly_mode: str) -> None:
    """AMRT-05 / D-09: biweekly modes also cleanly terminate at balance=0.00 exactly."""
    # Hand: Wikipedia-oracle parameters in both biweekly modes; both end at 0.00.
    loan = Loan(
        principal=Decimal("200000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2026, 5, 1),
    )
    schedule = build_schedule(loan, frequency="biweekly", biweekly_mode=biweekly_mode)  # type: ignore[arg-type]
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert_schedule_invariants(schedule, loan.principal)


# ---------------------------------------------------------------------------
# D-12: origination_date synthesis when None
# ---------------------------------------------------------------------------


def test_build_schedule_synthesizes_origination_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-12: when Loan.origination_date is None, engine synthesizes from datetime.now(UTC).

    Uses monkeypatch on lib.amortize.datetime to keep the test deterministic
    without adding any time-mocking dep (RESEARCH 8 recommendation).
    """
    from datetime import date as _date

    fake_today = _date(2026, 5, 15)

    class _FakeDateTime:
        @classmethod
        def now(cls, tz: object = None) -> _FakeDateTime:
            return cls()

        def date(self) -> _date:
            return fake_today

    monkeypatch.setattr("lib.amortize.datetime", _FakeDateTime)

    loan = Loan(
        principal=Decimal("200000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=None,
    )
    schedule = build_schedule(loan)
    # Hand: 2026-05-15 + relativedelta(months=1) = 2026-06-15.
    assert schedule.payments[0].payment_date == _date(2026, 6, 15)
    assert_schedule_invariants(schedule, loan.principal)


# ---------------------------------------------------------------------------
# D-13: relativedelta month-end clipping
# ---------------------------------------------------------------------------


def test_month_end_origination_clips_to_feb_28(
    amortize_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """D-13: origination 2026-01-31 -> first payment 2026-02-28 (relativedelta clips)."""
    fx = amortize_fixture("month_end_jan_31")
    # Hand: relativedelta clips Jan-31 + 1mo to Feb-28 (or Feb-29 in leap years).
    # Subsequent dates also clip where the day is unrepresentable in target month.
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
        origination_date=date.fromisoformat(fx["loan"]["origination_date"]),
    )
    schedule = build_schedule(loan)
    summary = fx["expected_schedule_summary"]
    assert schedule.payments[0].payment_date == date.fromisoformat(summary["first_payment_date"])
    assert schedule.payments[1].payment_date == date.fromisoformat(summary["second_payment_date"])
    assert schedule.payments[2].payment_date == date.fromisoformat(summary["third_payment_date"])
    assert_schedule_invariants(schedule, loan.principal)


# ---------------------------------------------------------------------------
# D-15: Schedule.total_interest == payments[-1].cumulative_interest by construction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_id",
    [pytest.param(fid, id=fid) for fid in FOUR_ORACLE_IDS],
)
def test_schedule_d15_invariant_holds_for_all_engine_outputs(
    fixture_id: str,
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """D-15: validator ratification on real engine output for all 4 oracles.

    The Schedule._total_interest_matches_last_cumulative validator (Plan 03-01)
    guards construction; this test confirms the engine's by-construction
    setting (Plan 03-02) actually satisfies the validator on real inputs.
    """
    fx = golden_fixture(fixture_id)
    loan = Loan(
        principal=Decimal(fx["principal"]),
        annual_rate=Decimal(fx["annual_rate"]),
        term_months=fx["term_months"],
        origination_date=date(2026, 5, 1),
    )
    schedule = build_schedule(loan)
    assert schedule.total_interest == schedule.payments[-1].cumulative_interest
    assert_schedule_invariants(schedule, loan.principal)


# ---------------------------------------------------------------------------
# ExtraPrincipalEntry: Pydantic field constraints
# ---------------------------------------------------------------------------


def test_extra_principal_entry_rejects_period_zero() -> None:
    """ExtraPrincipalEntry.period has ge=1; period=0 must raise ValidationError."""
    # Hand: period 0 is not a valid schedule period (1-indexed convention).
    with pytest.raises(ValidationError):
        ExtraPrincipalEntry(period=0, amount=Decimal("100.00"), recurring=False)


def test_extra_principal_entry_rejects_zero_amount() -> None:
    """ExtraPrincipalEntry.amount has gt=0; amount=0.00 must raise ValidationError."""
    # Hand: amount=0 is meaningless for extra-principal; surface as validation error.
    with pytest.raises(ValidationError):
        ExtraPrincipalEntry(period=1, amount=Decimal("0.00"), recurring=False)


# ---------------------------------------------------------------------------
# AMRT-06: scripts/amortize.py CLI subprocess + lazy-import + error surface
# ---------------------------------------------------------------------------


def test_cli_smoke_subprocess_round_trip(tmp_path: Path) -> None:
    """AMRT-06: write input JSON, invoke script via subprocess, parse output JSON.

    End-to-end: validates argparse + Pydantic boundary + engine + JSON output
    in one round-trip.
    """
    input_path = tmp_path / "loan.json"
    # Hand: Wikipedia oracle (200k/6.5/30) -> monthly_pi 1264.14, final balance 0.00.
    input_path.write_text(
        json.dumps(
            {
                "loan": {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                },
            }
        )
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(input_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["monthly_pi"] == "1264.14"
    assert out["payments"][-1]["balance"] == "0.00"


def test_cli_help_does_not_import_lib_amortize() -> None:
    """D-18: --help must not trigger lib.amortize import (lazy-import contract).

    Strategy (CANONICAL PROJECT PATTERN — mirrors tests/test_block_user_layer.py:24-32):

    Spawn a fresh Python subprocess (so lib.amortize is NOT already imported from
    this test module's own ``from lib.amortize import ...`` line) and run an
    inline check that loads scripts/amortize.py via
    ``importlib.util.spec_from_file_location`` with sys.argv patched to
    ``--help``. The subprocess prints whether ``lib.amortize`` ended up in
    sys.modules; this test asserts ``not_imported`` was reported.

    We do NOT use ``import scripts.amortize`` because scripts/ has NO __init__.py
    and is intentionally not a Python package (project convention; loading via
    spec_from_file_location is how tests/test_block_user_layer.py loads
    scripts/hooks/block-user-layer.py too).

    A try/finally restores sys.argv inside the inline harness so the harness
    itself stays isolated; argparse's --help raises SystemExit(0) after printing
    usage, and the harness catches it and asserts exc.code == 0.

    Per RESEARCH 10 Open Question 4: structural import-mock is more deterministic
    than wall-clock timing-based assertions (which are flaky in CI under load).
    """
    # Hand: spawn a fresh Python that has NOT pre-imported lib.amortize
    # (this test module's own top-level import would otherwise pollute sys.modules
    # in the test process and force the assertion into a skip).
    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_amortize', SCRIPT)\n"
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
        "    'lib_amortize_imported': 'lib.amortize' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
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
    # Hand: argparse --help exits with code 0 after printing usage.
    assert payload["help_exit_code"] == 0, (
        f"--help should exit 0, got {payload['help_exit_code']!r}"
    )
    # Hand: D-18 contract: lib.amortize and numpy_financial MUST NOT have been
    # loaded as a consequence of executing scripts/amortize.py's --help path.
    assert payload["lib_amortize_imported"] is False, (
        "D-18 violated: lib.amortize was imported during scripts/amortize.py --help "
        "(must be lazy-imported INSIDE main() AFTER argparse parses --help)."
    )
    assert payload["numpy_financial_imported"] is False, (
        "D-18 violated: numpy_financial was imported during --help "
        "(heavy dep must stay behind the lazy-import gate)."
    )


def test_cli_no_input_returns_argparse_error() -> None:
    """AMRT-06: missing --input flag exits 2 with argparse usage on stderr."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--input" in result.stderr


def test_cli_file_not_found_returns_structured_error(tmp_path: Path) -> None:
    """AMRT-06: nonexistent --input path exits 2 with structured JSON error."""
    bogus = tmp_path / "does_not_exist.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bogus)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    err = json.loads(result.stderr)
    assert "input file not found" in err.get("error", "")


def test_cli_invalid_json_input(tmp_path: Path) -> None:
    """AMRT-06: malformed JSON input exits 2 with Pydantic ValidationError JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text('{"loan":')  # truncated
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    # Pydantic emits a list of error dicts; should parse as JSON.
    parsed = json.loads(result.stderr)
    assert isinstance(parsed, list)
    assert len(parsed) >= 1


def test_cli_rejects_float_principal(tmp_path: Path) -> None:
    """D-19: pre-validation gate rejects JSON-float in any Money field.

    The JSON has ``principal: 400000.00`` as a NUMBER (not a string). Pydantic v2
    model_validate_json permissively coerces JSON numbers into Decimal, so the
    CLI runs a pre-validation walker (_find_json_float_loc) that emits a
    Pydantic-shaped ``decimal_type`` error envelope before model_validate_json.
    """
    bad = tmp_path / "float.json"
    # Hand: JSON number literal 400000.00 deserializes to a Python float;
    # the pre-validation gate rejects it with a structured envelope.
    bad.write_text(
        '{"loan": {"principal": 400000.00, "annual_rate": "0.065000", "term_months": 360}}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    # At least one error should reference 'principal' in its loc OR mention
    # 'decimal_type'/'Input should be'.
    offending = [
        e
        for e in errors
        if (isinstance(e.get("loc"), list) and "principal" in e["loc"])
        or "decimal_type" in str(e.get("type", ""))
        or "Input should be" in str(e.get("msg", ""))
    ]
    assert offending, f"No error referenced principal/decimal_type: {errors}"


def test_cli_d02_violation_at_boundary(tmp_path: Path) -> None:
    """D-02: AmortizeRequest validator rejects frequency=monthly + biweekly_mode='true'.

    The validator runs at model_validate_json time, BEFORE build_schedule is
    called. Surfaces as ValidationError JSON.
    """
    bad = tmp_path / "d02.json"
    bad.write_text(
        json.dumps(
            {
                "loan": {
                    "principal": "400000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                },
                "frequency": "monthly",
                "biweekly_mode": "true",
            }
        )
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    # Stderr should be parseable Pydantic JSON; one of the errors should mention
    # biweekly_mode.
    errors = json.loads(result.stderr)
    flat = json.dumps(errors)
    assert "biweekly_mode" in flat


def test_cli_biweekly_round_trip(tmp_path: Path) -> None:
    """AMRT-03 + AMRT-06: end-to-end biweekly-true round-trip via CLI."""
    input_path = tmp_path / "biweekly.json"
    input_path.write_text(
        json.dumps(
            {
                "loan": {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                },
                "frequency": "biweekly",
                "biweekly_mode": "true",
            }
        )
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(input_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["payments"][-1]["balance"] == "0.00"
    # Hand: biweekly-true accelerates; expect substantially fewer than the
    # 720 formulaic biweekly periods (per RESEARCH 3.1: ~628 for this loan).
    assert 600 < len(out["payments"]) < 700
