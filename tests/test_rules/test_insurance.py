"""Tests for lib/rules/insurance.py — REF-10 (Phase 16 Wave 0).

Citation under test: NAIC Homeowners Insurance Report (Data for 2022, published
2025-05-21) + III state averages for CA/TX + private-market flood-uplift
heuristic + CEA/PNW earthquake add-ons. Pinned to hand-calc anchored fixtures
under `tests/fixtures/rules/insurance_*.json`.

Coverage:
  - YAML metadata + 51 state rows + 5 flood multiplier rows + 3 earthquake rows
  - lookup_default WA + None flood_zone -> base * 1.15 + WA quake addon
  - lookup_default CA + 'AE' flood_zone -> base * 1.30 + CA quake addon
    (tests forward-compat flood path; v1.1 callers always pass None per
    RESEARCH correction #1)
  - lookup_default TX + None flood_zone -> base * 1.15 + 0 (silent zero;
    TX is not in {CA, OR, WA} so earthquake_state_addons has no row)
  - lookup_default for unknown state raises LookupError ('REF-10 schema gap')
  - fips_to_usps('53') == 'WA' and fips_to_usps('06') == 'CA'
  - fips_to_usps unknown FIPS raises KeyError with descriptive message
  - _FIPS_TO_USPS has 51 entries (50 states + DC)
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.money import quantize_cents
from lib.rules.insurance import _FIPS_TO_USPS, fips_to_usps, lookup_default

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def test_yaml_loads_with_metadata() -> None:
    """insurance-estimate-defaults.yml carries source/effective + 51 + 5 + 3
    rows required by D-16-INS-01..03."""
    from lib.rules._loader import load_reference

    ref = load_reference("insurance-estimate-defaults")
    assert all(
        k in ref
        for k in (
            "source",
            "effective",
            "state_base_annual_premium",
            "flood_zone_multipliers",
            "earthquake_state_addons",
        )
    )
    assert len(ref["state_base_annual_premium"]) == 51
    assert len(ref["flood_zone_multipliers"]) == 5
    assert len(ref["earthquake_state_addons"]) == 3
    # Only CA / OR / WA appear in earthquake_state_addons per D-16-INS-03.
    assert {r["state"] for r in ref["earthquake_state_addons"]} == {"CA", "OR", "WA"}


def test_lookup_state_base_wa() -> None:
    """Pachulski-baseline: state=WA, flood_zone=None -> base * 1.15 + WA quake."""
    fx = _fx("insurance_wa_no_flood.json")
    result = lookup_default(state=fx["state"], flood_zone=fx["flood_zone"])
    assert isinstance(result, Decimal)
    assert result == Decimal(fx["expected_annual"])


def test_composition_ca_zone_ae() -> None:
    """Forward-compat flood path: state=CA, flood_zone='AE' -> base * 1.30 + CA quake.
    v1.1 callers ALWAYS pass flood_zone=None (RESEARCH correction #1); this
    fixture exercises the X/A/AE/V scaffolding rows for v1.2 future-proofing."""
    fx = _fx("insurance_ca_zone_ae.json")
    result = lookup_default(state=fx["state"], flood_zone=fx["flood_zone"])
    assert result == Decimal(fx["expected_annual"])


def test_earthquake_silent_zero_for_other_state() -> None:
    """Non-quake state: state=TX, flood_zone=None -> base * 1.15 + 0.00.
    Proves D-16-INS-03 silent-zero (no reason tag, no raise) for states
    outside {CA, OR, WA}."""
    fx = _fx("insurance_tx_no_quake.json")
    result = lookup_default(state=fx["state"], flood_zone=None)
    assert result == Decimal(fx["expected_annual"])


def test_missing_state_raises_lookup_error() -> None:
    """Unknown state -> LookupError with REF-10 schema-gap message."""
    with pytest.raises(LookupError, match="REF-10 schema gap"):
        lookup_default(state="XX", flood_zone=None)


def test_fips_to_usps_known_code() -> None:
    """Spot-check key FIPS->USPS mappings used by the Phase 14 wire-in."""
    assert fips_to_usps("53") == "WA"
    assert fips_to_usps("06") == "CA"
    assert fips_to_usps("48") == "TX"
    assert fips_to_usps("36") == "NY"
    assert fips_to_usps("11") == "DC"


def test_fips_to_usps_unknown_raises() -> None:
    """Unknown FIPS -> KeyError with descriptive message."""
    with pytest.raises(KeyError, match="Unknown state FIPS"):
        fips_to_usps("99")


def test_fips_to_usps_dict_has_51_entries() -> None:
    """50 states + DC = 51 entries."""
    assert len(_FIPS_TO_USPS) == 51


def test_silent_zero_quantization_matches_hand_calc() -> None:
    """Cross-check: TX hand-calc value equals quantize_cents(base * 1.15)."""
    tx_result = lookup_default("TX", None)
    expected = quantize_cents(Decimal("2641.00") * Decimal("1.15"))
    assert tx_result == expected


def test_wa_composition_full_formula() -> None:
    """Cross-check: WA hand-calc value equals quantize_cents(base * 1.15 + 250.00)."""
    wa_result = lookup_default("WA", None)
    expected = quantize_cents(Decimal("1191.00") * Decimal("1.15") + Decimal("250.00"))
    assert wa_result == expected


def test_oregon_quake_addon_fires() -> None:
    """OR is in {CA, OR, WA} so the earthquake row fires (Decimal('200.00'))."""
    or_result = lookup_default("OR", None)
    expected = quantize_cents(Decimal("1031.00") * Decimal("1.15") + Decimal("200.00"))
    assert or_result == expected
