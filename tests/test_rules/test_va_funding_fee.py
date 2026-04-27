"""Tests for lib/rules/va_funding_fee.py — RUL-06.

Citation under test: 38 USC §3729 + VA Lender Handbook M26-7 Chapter 8. Pinned
to fixtures with hand-calc derivations.

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - Purchase first-use, 0% down: 2.15% (highest tier)
  - Purchase subsequent-use, 0% down: 3.30% (highest subsequent-use tier; Pitfall 7)
  - Purchase first-use, 5..<10% down: 1.50%
  - Purchase first-use, >=10% down: 1.25% (boundary at exactly 10%)
  - IRRRL streamline: flat 0.50% (ignores use-count + down-payment)
  - Cash-out refi subsequent-use, 0% down: 3.30% (shares purchase table)
  - Exempt (VA disability comp): $0.00 by statute (short-circuits)
  - Money discipline: result quantized to 2 decimal places exactly
  - Negative down-payment: raises ValueError (loud failure on invalid input)
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.va_funding_fee import compute

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def test_purchase_first_use_zero_down_215_pct() -> None:
    # Hand: $400k * 0.0215 = $8,600.00 (highest first-use tier).
    fx = _fx("va_funding_fee_purchase_first_use_zero_down.json")
    result = compute(
        loan_amount=Decimal(fx["loan_amount"]),
        down_payment_pct=Decimal(fx["down_payment_pct"]),
        is_first_use=fx["is_first_use"],
        loan_purpose=fx["loan_purpose"],
        is_exempt_from_funding_fee=fx["is_exempt_from_funding_fee"],
    )
    assert result == Decimal(fx["expected_fee"])


def test_purchase_subsequent_zero_down_330_pct() -> None:
    # Hand: $400k * 0.0330 = $13,200.00. Pitfall 7: subsequent-use is the
    # higher tier; predicate must NOT silently apply first-use rate.
    fx = _fx("va_funding_fee_purchase_subsequent_zero_down.json")
    result = compute(
        loan_amount=Decimal(fx["loan_amount"]),
        down_payment_pct=Decimal(fx["down_payment_pct"]),
        is_first_use=fx["is_first_use"],
        loan_purpose=fx["loan_purpose"],
        is_exempt_from_funding_fee=fx["is_exempt_from_funding_fee"],
    )
    assert result == Decimal(fx["expected_fee"])


def test_purchase_first_use_5pct_down_150_pct() -> None:
    # Hand: 6% down → in 5..<10 band → 0.0150. $400k * 0.0150 = $6,000.00.
    fx = _fx("va_funding_fee_purchase_first_use_5pct_down.json")
    result = compute(
        loan_amount=Decimal(fx["loan_amount"]),
        down_payment_pct=Decimal(fx["down_payment_pct"]),
        is_first_use=fx["is_first_use"],
        loan_purpose=fx["loan_purpose"],
        is_exempt_from_funding_fee=fx["is_exempt_from_funding_fee"],
    )
    assert result == Decimal(fx["expected_fee"])


def test_purchase_first_use_10pct_down_125_pct() -> None:
    # Hand: 10% down → in >=10 band (lower bound INCLUSIVE at 0.10) → 0.0125.
    # $400k * 0.0125 = $5,000.00. Boundary test: 0.10 must NOT fall in 5..<10.
    fx = _fx("va_funding_fee_purchase_first_use_10pct_down.json")
    result = compute(
        loan_amount=Decimal(fx["loan_amount"]),
        down_payment_pct=Decimal(fx["down_payment_pct"]),
        is_first_use=fx["is_first_use"],
        loan_purpose=fx["loan_purpose"],
        is_exempt_from_funding_fee=fx["is_exempt_from_funding_fee"],
    )
    assert result == Decimal(fx["expected_fee"])


def test_irrrl_streamline_50_bps_regardless_of_use_or_down() -> None:
    # Hand: IRRRL is flat 0.50% per M26-7. Predicate MUST ignore is_first_use
    # and down_payment_pct. $400k * 0.0050 = $2,000.00.
    fx = _fx("va_funding_fee_irrrl_streamline.json")
    result = compute(
        loan_amount=Decimal(fx["loan_amount"]),
        down_payment_pct=Decimal(fx["down_payment_pct"]),
        is_first_use=fx["is_first_use"],
        loan_purpose=fx["loan_purpose"],
        is_exempt_from_funding_fee=fx["is_exempt_from_funding_fee"],
    )
    assert result == Decimal(fx["expected_fee"])


def test_cash_out_subsequent_use_330_pct() -> None:
    # Hand: cash-out shares purchase table; subsequent-use 0% down → 0.0330.
    # $400k * 0.0330 = $13,200.00.
    fx = _fx("va_funding_fee_cash_out_subsequent.json")
    result = compute(
        loan_amount=Decimal(fx["loan_amount"]),
        down_payment_pct=Decimal(fx["down_payment_pct"]),
        is_first_use=fx["is_first_use"],
        loan_purpose=fx["loan_purpose"],
        is_exempt_from_funding_fee=fx["is_exempt_from_funding_fee"],
    )
    assert result == Decimal(fx["expected_fee"])


def test_exempt_returns_zero() -> None:
    # Hand: 38 USC §3729(c) — VA disability comp recipients are exempt.
    # Predicate must short-circuit BEFORE any table lookup. Money discipline:
    # returned $0 has 2-decimal exponent.
    fx = _fx("va_funding_fee_exempt_disability.json")
    result = compute(
        loan_amount=Decimal(fx["loan_amount"]),
        down_payment_pct=Decimal(fx["down_payment_pct"]),
        is_first_use=fx["is_first_use"],
        loan_purpose=fx["loan_purpose"],
        is_exempt_from_funding_fee=fx["is_exempt_from_funding_fee"],
    )
    assert result == Decimal(fx["expected_fee"]) == Decimal("0.00")
    assert result.as_tuple().exponent == -2


def test_funding_fee_returns_quantized_two_places() -> None:
    # Money discipline: $123,456.78 * 0.0215 = 2654.32077... → ROUND_HALF_UP → 2654.32.
    result = compute(
        loan_amount=Decimal("123456.78"),
        down_payment_pct=Decimal("0.00"),
        is_first_use=True,
        loan_purpose="purchase",
        is_exempt_from_funding_fee=False,
    )
    # Hand: 123456.78 * 0.0215 = 2654.320770 → ROUND_HALF_UP → 2654.32.
    assert result == Decimal("2654.32")
    assert result.as_tuple().exponent == -2


def test_negative_down_payment_pct_raises() -> None:
    # Loud failure: down_payment_pct < 0 is invalid input.
    with pytest.raises(ValueError, match="down_payment_pct"):
        compute(
            loan_amount=Decimal("400000.00"),
            down_payment_pct=Decimal("-0.05"),
            is_first_use=True,
            loan_purpose="purchase",
            is_exempt_from_funding_fee=False,
        )
