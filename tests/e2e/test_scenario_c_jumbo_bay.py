"""E2E snapshot test — Scenario C: Jumbo Bay Area.

Exercises the full CLI journey:
  YAML input fixture -> tempfile JSON request -> subprocess.run on
  ``.claude/skills/mortgage-ops/scripts/affordability.py`` -> parsed stdout
  JSON deep-equality against ``fixtures/snapshots/scenario_c_jumbo_bay.json``.

Scenario distinctive path: $1.2M property, 25% down, $900k loan in Solano
County CA (06/095). Solano sits at the baseline conforming limit ($832,750
per data/reference/conforming-limits-2026.yml), so a $900k loan classifies
as ``jumbo`` (NOT ``conforming``). DTI back lands ~0.40, under the 0.43
ceiling — must STAY eligible (``blocked is False``).
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from tests.e2e.conftest import assert_snapshot_matches, run_cli

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

SCENARIO = "scenario_c_jumbo_bay"


def test_scenario_c_jumbo_bay_snapshot() -> None:
    """The jumbo Bay Area CLI journey is deterministic and matches the
    committed snapshot.

    Asserts:
      1. Subprocess exits 0.
      2. Stdout parses as JSON.
      3. ``loan_type == "jumbo"`` (must FORCE jumbo classification — proves
         the Solano county_fips choice is honored).
      4. ``blocked is False`` (the Phase 17 review anchor: jumbo with
         dti_back < 0.43 and LTV 0.75 must STAY eligible).
      5. ``Decimal(dti_back) < Decimal("0.43")`` (ceiling guard).
      6. Parsed JSON (after dynamic-field scrubbing) deep-equals the snapshot.
    """
    proc = run_cli(SCENARIO)
    assert proc.returncode == 0, (
        f"affordability CLI exited {proc.returncode}.\nSTDERR (first 2KB):\n{proc.stderr[:2048]}"
    )
    payload = json.loads(proc.stdout)
    assert payload["loan_type"] == "jumbo"
    assert payload["blocked"] is False
    assert Decimal(payload["dti_back"]) < Decimal("0.43")
    assert_snapshot_matches(SCENARIO, payload)
