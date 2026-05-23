"""E2E snapshot test — Scenario B: FHA first-time buyer.

Exercises the full CLI journey:
  YAML input fixture -> tempfile JSON request -> subprocess.run on
  ``.claude/skills/mortgage-ops/scripts/affordability.py`` -> parsed stdout
  JSON deep-equality against ``fixtures/snapshots/scenario_b_fha_ftb.json``.

Scenario distinctive path: ``target_loan_type=fha`` triggers UFMIP auto-finance
into principal (D-03 + RESEARCH §"FHA UFMIP Financing Convention") and annual
MIP composition into PITI. Property value sized so financed LTV stays UNDER
the 0.965 FHA HUD-Handbook-4000.1 ceiling — exercises the MIP code path
without tripping ``LTV-CEILING-FHA``.

The StaleReferenceWarning for ``fha-mip-rates`` (effective 2023-03-20, more
than 12 months old) is part of the snapshot; the embedded
``threshold: YYYY-MM-DD`` substring is scrubbed via the conftest's
``_THRESHOLD_RE`` regex so the test is clock-stable.
"""

from __future__ import annotations

import json

import pytest

from tests.e2e.conftest import assert_snapshot_matches, run_cli

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

SCENARIO = "scenario_b_fha_ftb"


def test_scenario_b_fha_ftb_snapshot() -> None:
    """The FHA FTB CLI journey is deterministic and matches the committed
    snapshot.

    Asserts:
      1. Subprocess exits 0.
      2. Stdout parses as JSON.
      3. ``loan_type == "fha_standard"`` (no high-balance escalation at $337,750).
      4. ``financed_loan_amount > loan_amount`` (UFMIP financed).
      5. ``monthly_mi > 0`` (annual MIP active).
      6. Parsed JSON (after dynamic-field scrubbing) deep-equals the snapshot.
    """
    proc = run_cli(SCENARIO)
    assert proc.returncode == 0, (
        f"affordability CLI exited {proc.returncode}.\nSTDERR (first 2KB):\n{proc.stderr[:2048]}"
    )
    payload = json.loads(proc.stdout)
    assert payload["loan_type"] == "fha_standard"
    # UFMIP financed into principal (D-03)
    assert payload["financed_loan_amount"] != payload["loan_amount"]
    # Annual MIP active
    assert payload["monthly_mi"] != "0.00"
    assert_snapshot_matches(SCENARIO, payload)
