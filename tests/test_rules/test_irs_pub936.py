"""Tests for lib/rules/irs_pub936.py — RUL-11.

Citation under test: IRC §163(h)(3) + IRS Publication 936 Table 1. Pinned to
fixtures with hand-calc derivations.

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - Post-2017 single -> $750,000 (TCJA-reduced cap)
  - Post-2017 MFJ -> $750,000 (same as single per TCJA)
  - Post-2017 HoH -> $750,000 (same as single)
  - Post-2017 MFS -> $375,000 (exactly half)
  - Pre-2017 grandfathered single -> $1,000,000 (pre-TCJA cap preserved)
  - Pre-2017 grandfathered MFS -> $500,000 (exactly half of $1M)
  - Binding-contract grace period (BOTH flags True) -> $1,000,000 (treated
    as grandfathered)
  - Binding-contract: only one flag True -> does NOT qualify; falls back to
    post-2017 cap ($750,000)
  - Invalid filing_status -> ValueError (loud failure)

LOCKED DECISION (per RESEARCH.md line 912): the binding-contract grace period
requires TWO booleans (signed-before AND closed-before), NOT a single
origination_date — see module docstring for rationale.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.irs_pub936 import qualified_loan_limit

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def test_post_2017_single_returns_750k_cap() -> None:
    # Hand: post-2017 single cap = $750,000 (TCJA-reduced from $1M pre-TCJA).
    fx = _fx("irs_pub936_post_2017_single_at_cap.json")
    result = qualified_loan_limit(
        filing_status=fx["filing_status"],
        has_grandfathered_debt=fx["has_grandfathered_debt"],
        binding_contract_signed_before_2017_12_15=fx["binding_contract_signed_before_2017_12_15"],
        binding_contract_closed_before_2018_04_01=fx["binding_contract_closed_before_2018_04_01"],
    )
    assert result == Decimal(fx["expected_qualified_loan_limit"])


def test_post_2017_mfj_returns_750k_cap() -> None:
    # Hand: post-2017 MFJ cap = $750,000 (same as single per TCJA).
    result = qualified_loan_limit(filing_status="mfj")
    assert result == Decimal("750000")


def test_post_2017_hoh_returns_750k_cap() -> None:
    # Hand: post-2017 HoH cap = $750,000 (same as single per TCJA).
    result = qualified_loan_limit(filing_status="hoh")
    assert result == Decimal("750000")


def test_grandfathered_pre_2017_single_returns_1m_cap() -> None:
    # Hand: has_grandfathered_debt=True -> pre-2017 cap = $1,000,000.
    fx = _fx("irs_pub936_grandfathered_pre_2017_single.json")
    result = qualified_loan_limit(
        filing_status=fx["filing_status"],
        has_grandfathered_debt=fx["has_grandfathered_debt"],
        binding_contract_signed_before_2017_12_15=fx["binding_contract_signed_before_2017_12_15"],
        binding_contract_closed_before_2018_04_01=fx["binding_contract_closed_before_2018_04_01"],
    )
    assert result == Decimal(fx["expected_qualified_loan_limit"])


def test_post_2017_mfs_returns_375k_cap() -> None:
    # Hand: post-2017 MFS cap = $750k / 2 = $375,000 (encoded directly in YAML).
    fx = _fx("irs_pub936_post_2017_mfs_half_cap.json")
    result = qualified_loan_limit(
        filing_status=fx["filing_status"],
        has_grandfathered_debt=fx["has_grandfathered_debt"],
        binding_contract_signed_before_2017_12_15=fx["binding_contract_signed_before_2017_12_15"],
        binding_contract_closed_before_2018_04_01=fx["binding_contract_closed_before_2018_04_01"],
    )
    assert result == Decimal(fx["expected_qualified_loan_limit"])


def test_grandfathered_mfs_returns_500k_cap() -> None:
    # Hand: pre-2017 grandfathered MFS cap = $1M / 2 = $500,000.
    result = qualified_loan_limit(filing_status="mfs", has_grandfathered_debt=True)
    assert result == Decimal("500000")


def test_binding_contract_grace_period_treated_as_grandfathered() -> None:
    # Hand: BOTH grace flags True (signed before 2017-12-15 AND closed before
    # 2018-04-01) -> debt is treated as grandfathered -> cap = $1,000,000.
    # LOCKED DECISION: the grace period requires BOTH dates; a single
    # origination_date cannot capture this.
    fx = _fx("irs_pub936_binding_contract_grace_period.json")
    result = qualified_loan_limit(
        filing_status=fx["filing_status"],
        has_grandfathered_debt=fx["has_grandfathered_debt"],
        binding_contract_signed_before_2017_12_15=fx["binding_contract_signed_before_2017_12_15"],
        binding_contract_closed_before_2018_04_01=fx["binding_contract_closed_before_2018_04_01"],
    )
    assert result == Decimal(fx["expected_qualified_loan_limit"])


def test_binding_contract_only_signed_flag_does_not_qualify() -> None:
    # Hand: only signed-before flag True (closed-before flag False) -> does NOT
    # qualify for grace period -> falls back to post-2017 cap = $750,000.
    # Pins the AND-semantics: BOTH flags required, not OR.
    result = qualified_loan_limit(
        filing_status="single",
        has_grandfathered_debt=False,
        binding_contract_signed_before_2017_12_15=True,
        binding_contract_closed_before_2018_04_01=False,
    )
    assert result == Decimal("750000")


def test_binding_contract_only_closed_flag_does_not_qualify() -> None:
    # Hand: only closed-before flag True (signed-before flag False) -> does NOT
    # qualify -> post-2017 cap = $750,000. Pins AND-semantics symmetrically.
    result = qualified_loan_limit(
        filing_status="single",
        has_grandfathered_debt=False,
        binding_contract_signed_before_2017_12_15=False,
        binding_contract_closed_before_2018_04_01=True,
    )
    assert result == Decimal("750000")


def test_invalid_filing_status_raises() -> None:
    # Loud failure: filing_status not in literal set -> ValueError.
    # The `# type: ignore[arg-type]` documents that mypy --strict catches this
    # at compile time; the runtime test verifies the ValueError raises too.
    with pytest.raises(ValueError, match="filing_status"):
        qualified_loan_limit(filing_status="invalid")  # type: ignore[arg-type]
