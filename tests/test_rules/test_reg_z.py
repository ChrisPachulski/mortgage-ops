"""Tests for lib/rules/reg_z.py - RUL-10.

Citation under test: 12 CFR §1026.22(a)(2)-(a)(3) - Reg Z APR tolerance:
1/8 percentage point regular, 1/4 percentage point irregular. Pinned to
fixtures with hand-calc derivations.

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - Regular transaction within +/- 1/8 pp tolerance -> True
  - Regular transaction outside +/- 1/8 pp tolerance -> False
  - Irregular transaction within +/- 1/4 pp tolerance -> True
  - Irregular transaction outside +/- 1/4 pp tolerance -> False
  - Regular exactly at tolerance (`<=` boundary; Pitfall 11 - Decimal exactness)
  - Irregular exactly at tolerance + same diff fails for regular (one diff, two branches)
  - Symmetry (swap disclosed/actual gives same answer - predicate uses abs)
  - Tolerance constants have exact statutory values (locks Decimal('0.00125') and Decimal('0.0025'))
  - Loud failures: negative disclosed_apr, negative actual_apr

LOCKED DECISIONS (per module docstring):
  - D-02: tolerance values live in CODE (no YAML); module-level Final constants.
  - Boundary `<=` per §1026.22(a)(2) "does not exceed".
  - Decimal arithmetic exactness (Pitfall 11): no float operations.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.reg_z import TOLERANCE_IRREGULAR, TOLERANCE_REGULAR, within_apr_tolerance

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def test_tolerance_constants_have_exact_values() -> None:
    # Hand: §1026.22(a)(2) = 1/8 pp = 0.125 percentage points = 0.00125 fractional.
    # Hand: §1026.22(a)(3) = 1/4 pp = 0.25 percentage points = 0.0025 fractional.
    # Locks the values; any module-level edit changing the constants fails this test.
    assert Decimal("0.00125") == TOLERANCE_REGULAR
    assert Decimal("0.0025") == TOLERANCE_IRREGULAR


def test_regular_within_tolerance() -> None:
    # Hand: |0.0700 - 0.0710| = 0.001; 0.001 <= 0.00125 (TOLERANCE_REGULAR) -> True.
    fx = _fx("reg_z_regular_within_tolerance.json")
    result = within_apr_tolerance(
        disclosed_apr=Decimal(fx["disclosed_apr"]),
        actual_apr=Decimal(fx["actual_apr"]),
        is_irregular_transaction=fx["is_irregular_transaction"],
    )
    assert result is fx["expected_within_tolerance"]


def test_regular_outside_tolerance() -> None:
    # Hand: |0.0700 - 0.0715| = 0.0015; 0.0015 > 0.00125 -> False.
    fx = _fx("reg_z_regular_outside_tolerance.json")
    result = within_apr_tolerance(
        disclosed_apr=Decimal(fx["disclosed_apr"]),
        actual_apr=Decimal(fx["actual_apr"]),
        is_irregular_transaction=fx["is_irregular_transaction"],
    )
    assert result is fx["expected_within_tolerance"]


def test_irregular_within_tolerance() -> None:
    # Hand: |0.0700 - 0.0720| = 0.002; 0.002 <= 0.0025 (TOLERANCE_IRREGULAR) -> True.
    # Note: same diff (0.002) FAILS for regular (0.002 > 0.00125) - pins the
    # irregular-gets-more-lenient-tolerance branch.
    fx = _fx("reg_z_irregular_within_tolerance.json")
    result = within_apr_tolerance(
        disclosed_apr=Decimal(fx["disclosed_apr"]),
        actual_apr=Decimal(fx["actual_apr"]),
        is_irregular_transaction=fx["is_irregular_transaction"],
    )
    assert result is fx["expected_within_tolerance"]


def test_irregular_outside_tolerance() -> None:
    # Hand: |0.0700 - 0.0730| = 0.003; 0.003 > 0.0025 -> False.
    fx = _fx("reg_z_irregular_outside_tolerance.json")
    result = within_apr_tolerance(
        disclosed_apr=Decimal(fx["disclosed_apr"]),
        actual_apr=Decimal(fx["actual_apr"]),
        is_irregular_transaction=fx["is_irregular_transaction"],
    )
    assert result is fx["expected_within_tolerance"]


def test_regular_exactly_at_tolerance_passes() -> None:
    # Hand: Decimal('0.0700') - Decimal('0.07125') = Decimal('-0.00125') exactly.
    # abs(-0.00125) = 0.00125 = TOLERANCE_REGULAR exactly. Decimal arithmetic
    # is exact (Pitfall 11), so 0.00125 <= 0.00125 -> True per `<=` boundary.
    fx = _fx("reg_z_regular_exactly_at_tolerance.json")
    disclosed = Decimal(fx["disclosed_apr"])
    actual = Decimal(fx["actual_apr"])
    # Pin the exactness of the Decimal arithmetic before testing the predicate.
    assert abs(disclosed - actual) == Decimal("0.00125")
    result = within_apr_tolerance(
        disclosed_apr=disclosed,
        actual_apr=actual,
        is_irregular_transaction=fx["is_irregular_transaction"],
    )
    assert result is fx["expected_within_tolerance"]


def test_irregular_exactly_at_tolerance_passes_but_regular_fails_same_diff() -> None:
    # Hand: |0.0700 - 0.0725| = 0.0025 exactly.
    # is_irregular_transaction=True -> 0.0025 <= TOLERANCE_IRREGULAR (0.0025) -> True.
    # is_irregular_transaction=False -> 0.0025 > TOLERANCE_REGULAR (0.00125) -> False.
    # One diff, two branches - pins both at once.
    disclosed = Decimal("0.0700")
    actual = Decimal("0.0725")
    assert abs(disclosed - actual) == Decimal("0.0025")
    assert within_apr_tolerance(disclosed, actual, is_irregular_transaction=True) is True
    assert within_apr_tolerance(disclosed, actual, is_irregular_transaction=False) is False


def test_symmetric_under_swap() -> None:
    # Hand: predicate uses abs() so swapping (disclosed, actual) must give the
    # same answer. Pins direction-agnostic semantics.
    a = Decimal("0.0710")
    b = Decimal("0.0700")
    assert within_apr_tolerance(a, b, is_irregular_transaction=False) is True
    assert within_apr_tolerance(b, a, is_irregular_transaction=False) is True


def test_negative_disclosed_apr_raises() -> None:
    # Loud failure: disclosed_apr < 0 -> ValueError.
    with pytest.raises(ValueError, match="disclosed_apr"):
        within_apr_tolerance(
            disclosed_apr=Decimal("-0.01"),
            actual_apr=Decimal("0.0700"),
            is_irregular_transaction=False,
        )


def test_negative_actual_apr_raises() -> None:
    # Loud failure: actual_apr < 0 -> ValueError.
    with pytest.raises(ValueError, match="actual_apr"):
        within_apr_tolerance(
            disclosed_apr=Decimal("0.0700"),
            actual_apr=Decimal("-0.01"),
            is_irregular_transaction=False,
        )
