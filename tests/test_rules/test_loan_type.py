"""Tests for lib/rules/loan_type.py — RUL-01.

Citation under test: 12 USC §1717 (FHFA conforming-limit authority) + NHA §203(b)(2)
(FHA limits as % of conforming). Per-county subset shipped in
data/reference/conforming-limits-2026.yml.

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - conforming at baseline: county=None tolerated when loan_amount <= baseline
  - high_balance: high-cost county (San Francisco) at <= ceiling
  - jumbo: above county ceiling
  - low-cost-county Pitfall 7: sub-baseline loan in non-high-cost county is conforming
  - missing-county fail-loud (cfpb/jumbo-mortgage pattern) when loan > baseline
  - USDA flag-only branch (no amount-based classification)
  - FHA fha_standard: loan <= floor in low-cost county (REF-02 wired in plan 02-02)
  - FHA fha_high_balance: loan > floor + listed high-cost county at <= ceiling
  - FHA above-county-ceiling: NotImplementedError (jumbo FHA not in v1)
  - FHA missing-county above floor: MissingCountyDataError (loud)
  - VA branch stubbed with NotImplementedError until 02-03 wires it
  - unit_count > 1 stubbed with NotImplementedError (multi-family deferred)
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.loan_type import MissingCountyDataError, classify
from lib.rules.types import County

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def _county_from_fx(fx_county: dict[str, str]) -> County:
    return County(
        state_fips=fx_county["state_fips"],
        county_fips=fx_county["county_fips"],
        name=fx_county["name"],
    )


def test_conforming_baseline_no_county_required() -> None:
    # Hand: $800,000 <= $832,750 baseline -> conforming. county=None tolerated.
    fx = _fx("loan_type_conforming_baseline.json")
    result = classify(
        Decimal(fx["loan_amount"]),
        county=None,
        program=fx["program"],
        unit_count=fx["unit_count"],
    )
    assert result == fx["expected_loan_type"] == "conforming"


def test_high_balance_in_high_cost_san_francisco() -> None:
    # Hand: $1,000,000 in SF (06/075). $832,750 < $1M <= $1,249,125 -> high_balance.
    fx = _fx("loan_type_high_balance_san_francisco.json")
    county = _county_from_fx(fx["county"])
    result = classify(
        Decimal(fx["loan_amount"]),
        county=county,
        program=fx["program"],
        unit_count=fx["unit_count"],
    )
    assert result == fx["expected_loan_type"] == "high_balance"


def test_jumbo_above_san_francisco_ceiling() -> None:
    # Hand: $1,500,000 in SF > $1,249,125 ceiling -> jumbo.
    fx = _fx("loan_type_jumbo_above_san_francisco_ceiling.json")
    county = _county_from_fx(fx["county"])
    result = classify(
        Decimal(fx["loan_amount"]),
        county=county,
        program=fx["program"],
        unit_count=fx["unit_count"],
    )
    assert result == fx["expected_loan_type"] == "jumbo"


def test_low_cost_county_baseline_loan_treated_as_conforming() -> None:
    # Hand: Pitfall 7 case. $750k < $832,750 baseline -> conforming even though
    # Autauga AL is a low-cost county whose limit IS the baseline. The classify
    # function must handle this without trying to look up Autauga (which isn't
    # in the high_cost_counties subset).
    fx = _fx("loan_type_low_cost_county_baseline.json")
    county = _county_from_fx(fx["county"])
    result = classify(
        Decimal(fx["loan_amount"]),
        county=county,
        program=fx["program"],
        unit_count=fx["unit_count"],
    )
    assert result == fx["expected_loan_type"] == "conforming"


def test_missing_county_when_above_baseline_raises() -> None:
    # Hand: $900,000 > $832,750 baseline; without county we cannot tell whether
    # this is high_balance (in high-cost county) or jumbo (in low-cost county).
    # Fail loud per cfpb/jumbo-mortgage pattern (Pitfall 7).
    with pytest.raises(MissingCountyDataError, match="county required"):
        classify(Decimal("900000.00"), county=None, program="conventional")


def test_usda_program_flag_only() -> None:
    # USDA does not classify by loan amount — predicate just returns the flag.
    assert classify(Decimal("100000.00"), county=None, program="usda") == "usda"


def test_fha_program_classifies_below_floor_as_fha_standard() -> None:
    # Hand: $400,000 loan in Autauga AL (NOT in high_cost_counties; FHA limit IS
    # the floor=$541,287). $400k <= $541,287 → fha_standard.
    fx = _fx("loan_type_fha_standard.json")
    county = _county_from_fx(fx["county"])
    result = classify(
        Decimal(fx["loan_amount"]),
        county=county,
        program=fx["program"],
        unit_count=fx["unit_count"],
    )
    assert result == fx["expected_loan_type"] == "fha_standard"


def test_fha_program_classifies_above_floor_as_fha_high_balance() -> None:
    # Hand: $700,000 loan in San Francisco (FHA ceiling=$1,249,125).
    # $541,287 < $700k <= $1,249,125 → fha_high_balance.
    fx = _fx("loan_type_fha_high_balance.json")
    county = _county_from_fx(fx["county"])
    result = classify(
        Decimal(fx["loan_amount"]),
        county=county,
        program=fx["program"],
        unit_count=fx["unit_count"],
    )
    assert result == fx["expected_loan_type"] == "fha_high_balance"


def test_fha_program_above_county_ceiling_raises() -> None:
    # Hand: $1,500,000 loan in San Francisco (ceiling=$1,249,125). Above ceiling
    # → not eligible for FHA. Loud error per fail-loud-on-edge-case discipline.
    with pytest.raises(NotImplementedError, match="exceeds FHA county ceiling"):
        classify(
            Decimal("1500000.00"),
            county=County(state_fips="06", county_fips="075", name="San Francisco CA"),
            program="fha",
        )


def test_fha_program_above_floor_missing_county_raises() -> None:
    # Hand: $700k > $541,287 floor; without county we cannot classify. Fail loud.
    with pytest.raises(MissingCountyDataError, match="FHA loan_amount"):
        classify(Decimal("700000.00"), county=None, program="fha")


def test_va_program_raises_not_implemented_until_va_wiring_lands() -> None:
    # Plan 02-03 wires VA branches. Until then this confirms the stub is in place.
    with pytest.raises(NotImplementedError, match="02-03"):
        classify(
            Decimal("400000.00"),
            county=None,
            program="va",
        )


def test_unit_count_above_one_raises_not_implemented() -> None:
    # Multi-family classification is deferred to v2.
    with pytest.raises(NotImplementedError, match="unit_count"):
        classify(Decimal("400000.00"), county=None, program="conventional", unit_count=2)
