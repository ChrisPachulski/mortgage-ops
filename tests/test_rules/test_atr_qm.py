"""Tests for lib/rules/atr_qm.py - RUL-09.

Citation under test: 12 CFR §1026.43(e)(2) (General-QM) + §1026.43(b)(4)
(Safe-Harbor). Pinned to fixtures with hand-calc derivations.

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - First-lien high band (>= $110,260): threshold 2.25 pp General-QM, 1.5 pp Safe-Harbor
  - First-lien mid band ($66,156 <= x < $110,260): threshold 3.5 pp
  - First-lien low band (< $66,156): threshold 6.5 pp
  - Subordinate-lien high band (>= $66,156): threshold 3.5 pp
  - Subordinate-lien low band (< $66,156): threshold 6.5 pp
  - Tier boundaries (inclusive lower / exclusive upper): exactly $66,156 -> mid band; exactly $110,260 -> high band
  - APR exactly at threshold (`<=` boundary; Pitfall 11 - Decimal exactness)
  - Safe-Harbor variant reads the second YAML column
  - Loud failures: negative apr, negative apor, zero loan_amount

LOCKED DECISIONS (per module docstring):
  - Threshold-unit convention: YAML in pp; predicate divides by 100.
  - Tier boundary semantics: inclusive lower (`>=`) / exclusive upper (`<`).
  - Comparison boundary: `<=` (exactly-at-threshold counts as passing).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.atr_qm import general_qm_passes, safe_harbor_qm_passes

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def test_first_lien_high_loan_within_general_qm() -> None:
    # Hand: spread = 7.00 - 5.00 = 2.00 pp; first-lien high band threshold = 2.25 pp.
    fx = _fx("atr_qm_first_lien_high_loan_within.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_first_lien_high_loan_outside_general_qm() -> None:
    # Hand: spread = 8.00 - 5.00 = 3.00 pp > 2.25 pp threshold.
    fx = _fx("atr_qm_first_lien_high_loan_outside.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_first_lien_mid_loan_within_general_qm() -> None:
    # Hand: loan $80,000 in $66,156-$110,260 band -> threshold 3.5 pp; spread 3.0 pp.
    fx = _fx("atr_qm_first_lien_mid_loan_within.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_first_lien_low_loan_within_general_qm() -> None:
    # Hand: loan $60,000 < $66,156 -> threshold 6.5 pp; spread 6.0 pp.
    fx = _fx("atr_qm_first_lien_low_loan_within.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_subordinate_lien_high_within_general_qm() -> None:
    # Hand: subordinate, loan >= $66,156 -> threshold 3.5 pp; spread 3.0 pp.
    fx = _fx("atr_qm_subordinate_lien_high_within.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_subordinate_lien_low_within_general_qm() -> None:
    # Hand: subordinate, loan < $66,156 -> threshold 6.5 pp; spread 6.0 pp.
    fx = _fx("atr_qm_subordinate_lien_low_within.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_loan_amount_boundary_66156_uses_mid_band_threshold() -> None:
    # Hand: exactly $66,156 first-lien -> bands {low: <66156, mid: 66156<=x<110260}.
    # Inclusive lower bound on mid band -> mid band threshold (3.5 pp), NOT low band (6.5 pp).
    # spread = 9.00 - 5.00 = 4.00 pp > 3.5 pp -> False.
    fx = _fx("atr_qm_loan_amount_boundary_66156.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_loan_amount_boundary_110260_uses_high_band_threshold() -> None:
    # Hand: exactly $110,260 first-lien -> bands {mid: 66156<=x<110260, high: >=110260}.
    # Inclusive lower bound on high band -> high band threshold (2.25 pp), NOT mid (3.5 pp).
    # spread = 8.00 - 5.00 = 3.00 pp > 2.25 pp -> False.
    fx = _fx("atr_qm_loan_amount_boundary_110260.json")
    result = general_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_apr_exactly_at_general_qm_threshold() -> None:
    # Hand: first-lien high threshold = 2.25 pp = Decimal('0.0225') fractional.
    # apr=0.0725 - apor=0.0500 = Decimal('0.0225') EXACTLY (no float drift).
    # Regulation uses `<=` -> True. Pins Pitfall 11.
    fx = _fx("atr_qm_apr_exactly_at_threshold.json")
    apr = Decimal(fx["apr"])
    apor = Decimal(fx["apor"])
    # Pin the exactness of the Decimal arithmetic before testing the predicate.
    assert apr - apor == Decimal("0.0225")
    result = general_qm_passes(
        apr=apr,
        apor=apor,
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_general_qm_passes"]


def test_safe_harbor_first_lien_high_within() -> None:
    # Hand: first-lien high Safe-Harbor threshold = 1.5 pp (tighter than 2.25 pp General-QM).
    # spread = 6.40 - 5.00 = 1.40 pp <= 1.5 pp -> True.
    fx = _fx("atr_qm_safe_harbor_first_lien_high.json")
    result = safe_harbor_qm_passes(
        apr=Decimal(fx["apr"]),
        apor=Decimal(fx["apor"]),
        loan_amount=Decimal(fx["loan_amount"]),
        lien_position=fx["lien_position"],
    )
    assert result is fx["expected_safe_harbor_qm_passes"]


def test_safe_harbor_first_lien_high_outside_when_general_qm_passes() -> None:
    # Hand: same loan as test_first_lien_high_loan_within (passes General-QM at 2.0 pp <= 2.25 pp)
    # but FAILS Safe-Harbor (2.0 pp > 1.5 pp). Pins that Safe-Harbor is strictly tighter.
    apr = Decimal("0.0700")
    apor = Decimal("0.0500")
    loan_amount = Decimal("250000")
    assert general_qm_passes(apr, apor, loan_amount, "first") is True
    assert safe_harbor_qm_passes(apr, apor, loan_amount, "first") is False


def test_negative_apr_raises() -> None:
    # Loud failure: apr < 0 -> ValueError.
    with pytest.raises(ValueError, match="apr"):
        general_qm_passes(
            apr=Decimal("-0.01"),
            apor=Decimal("0.0500"),
            loan_amount=Decimal("250000"),
            lien_position="first",
        )


def test_negative_apor_raises() -> None:
    # Loud failure: apor < 0 -> ValueError.
    with pytest.raises(ValueError, match="apor"):
        general_qm_passes(
            apr=Decimal("0.0700"),
            apor=Decimal("-0.01"),
            loan_amount=Decimal("250000"),
            lien_position="first",
        )


def test_zero_loan_amount_raises() -> None:
    # Loud failure: loan_amount <= 0 -> ValueError.
    with pytest.raises(ValueError, match="loan_amount"):
        general_qm_passes(
            apr=Decimal("0.0700"),
            apor=Decimal("0.0500"),
            loan_amount=Decimal("0"),
            lien_position="first",
        )
