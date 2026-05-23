"""E2E snapshot test — Scenario A: Conventional 30-year fixed, median market.

Exercises the full CLI journey:
  YAML input fixture -> tempfile JSON request -> subprocess.run on
  ``.claude/skills/mortgage-ops/scripts/affordability.py`` -> parsed stdout
  JSON deep-equality against ``fixtures/snapshots/scenario_a_conv30_median.json``.

Reference scenario: $500k SFH, 20% down, $400k loan @ 6.81% (FRED
MORTGAGE30US 2026-04-24), King WA escrow flavor, two-applicant joint
income. Must classify as ``conforming`` and not be blocked.
"""

from __future__ import annotations

import json

import pytest

from tests.e2e.conftest import assert_snapshot_matches, run_cli

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

SCENARIO = "scenario_a_conv30_median"


def test_scenario_a_conv30_median_snapshot() -> None:
    """The conv-30yr median-market CLI journey is deterministic and matches
    the committed snapshot.

    Asserts:
      1. Subprocess exits 0 (success envelope is exit-0 per Phase 3 D-13).
      2. Stdout parses as JSON.
      3. Parsed JSON (after dynamic-field scrubbing) deep-equals the
         committed snapshot.
      4. The scenario-distinctive engine output is what the user expects —
         specifically ``loan_type == "conforming"`` and
         ``blocked is False`` (sanity guard that survives snapshot-update
         churn).
    """
    proc = run_cli(SCENARIO)
    assert proc.returncode == 0, (
        f"affordability CLI exited {proc.returncode}.\nSTDERR (first 2KB):\n{proc.stderr[:2048]}"
    )
    payload = json.loads(proc.stdout)
    assert payload["loan_type"] == "conforming"
    assert payload["blocked"] is False
    assert_snapshot_matches(SCENARIO, payload)
