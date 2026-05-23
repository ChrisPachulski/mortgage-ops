"""E2E snapshot test — Scenario D: ARM 5/1 refi NPV.

Exercises the full CLI journey:
  YAML input fixture -> tempfile JSON request -> subprocess.run on
  ``.claude/skills/mortgage-ops/scripts/refi_npv.py`` -> parsed stdout JSON
  deep-equality against ``fixtures/snapshots/scenario_d_arm51_refi.json``.

Scenario distinctive path: an existing 30yr fixed at 7.5% with 300 months
remaining and a $377,920 balance is refinanced into a 5/1 ARM at 6.25%
initial fixed rate (data/known-loans.yml arm-5-1). The refi_npv CLI uses
the INITIAL fixed rate as ``new_annual_rate`` (Phase 6 v1 scope — ARM
payment-path modeling beyond the initial fixed period is owned by
arm_simulate.py). 5% discount rate, $3,500 closing costs.

Asserts the borrower-perspective NPV is positive, the breakeven months
are deterministic (simple + NPV-based per Phase 6), and the full
RefiResponse (including the 301-element cashflows array) matches the
committed snapshot byte-for-byte after scrub.

This is the largest snapshot in the suite (~36KB stdout) — the full
300-month savings cashflow stream is part of the contract per Phase 6
SC-1 sign-convention rigor; truncating to summary fields would lose the
sign-rigor coverage.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from tests.e2e.conftest import assert_snapshot_matches, run_cli

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

SCENARIO = "scenario_d_arm51_refi"


def test_scenario_d_arm51_refi_snapshot() -> None:
    """The 5/1 ARM refi NPV CLI journey is deterministic and matches the
    committed snapshot.

    Asserts:
      1. Subprocess exits 0.
      2. Stdout parses as JSON.
      3. ``refi_kind == "rate_and_term"`` (mode discriminator preserved).
      4. ``Decimal(npv) > 0`` (a rate drop of 125bps with $3.5k closing
         costs on a $378k balance must yield positive NPV at 5% discount).
      5. ``Decimal(monthly_savings) > 0`` (sign-rigor — savings are positive
         inflows per D-04 + SC-1).
      6. The first cashflow is the closing-costs outflow at period 0;
         the rest are monthly_savings inflows (SC-1 / RefiCashflow sign
         validator).
      7. Parsed JSON (after dynamic-field scrubbing) deep-equals the snapshot.
    """
    proc = run_cli(SCENARIO)
    assert proc.returncode == 0, (
        f"refi_npv CLI exited {proc.returncode}.\nSTDERR (first 2KB):\n{proc.stderr[:2048]}"
    )
    payload = json.loads(proc.stdout)
    assert payload["refi_kind"] == "rate_and_term"
    assert Decimal(payload["npv"]) > Decimal("0")
    assert Decimal(payload["monthly_savings"]) > Decimal("0")
    # SC-1 cashflow sign-rigor anchors
    cashflows = payload["cashflows"]
    assert cashflows[0]["kind"] == "closing_costs"
    assert cashflows[0]["direction"] == "outflow"
    assert Decimal(cashflows[0]["amount"]) < Decimal("0")
    assert cashflows[1]["kind"] == "monthly_savings"
    assert cashflows[1]["direction"] == "inflow"
    assert Decimal(cashflows[1]["amount"]) > Decimal("0")
    assert_snapshot_matches(SCENARIO, payload)
