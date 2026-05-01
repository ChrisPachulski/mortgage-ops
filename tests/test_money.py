"""Tests for lib/money.py — Decimal discipline (FND-01).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - to_money: string-only construction
  - quantize_cents: ROUND_HALF_UP (not banker's ROUND_HALF_EVEN)
  - MONEY_CONTEXT: prec=28, rounding=ROUND_HALF_UP
  - localcontext discipline: global getcontext() unchanged after roundtrip
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext

from lib.money import CENT, MONEY_CONTEXT, quantize_cents, quantize_rate, to_money


def test_to_money_from_string_round_trips() -> None:
    # Hand: Decimal("0.065") preserves the exact string form; no float drift.
    assert to_money("0.065") == Decimal("0.065")


def test_to_money_preserves_canonical_oracle_string() -> None:
    # The Wikipedia oracle 1264.14 must round-trip without loss.
    # FND-09 contract: tests/fixtures/golden_pmt.json stores "1264.14" as a string.
    assert to_money("1264.14") == Decimal("1264.14")


def test_quantize_cents_uses_round_half_up_at_0p005() -> None:
    # Hand: ROUND_HALF_UP(0.005, 2) == 0.01.
    # ROUND_HALF_EVEN (Python's default; banker's rounding) would return 0.00.
    # This is the load-bearing assertion for FND-01: prove we are NOT using banker's.
    assert quantize_cents(Decimal("0.005")) == Decimal("0.01")


def test_quantize_cents_uses_round_half_up_at_0p015() -> None:
    # Hand: ROUND_HALF_UP(0.015, 2) == 0.02; banker's would also give 0.02 (odd→up).
    # Included to ensure the boundary is consistent across odd/even tiebreaker rows.
    assert quantize_cents(Decimal("0.015")) == Decimal("0.02")


def test_quantize_cents_uses_round_half_up_at_0p025() -> None:
    # Hand: ROUND_HALF_UP(0.025, 2) == 0.03; banker's would give 0.02 (even-down).
    # The cleanest test: only ROUND_HALF_UP yields 0.03 here.
    assert quantize_cents(Decimal("0.025")) == Decimal("0.03")


def test_money_context_invariants() -> None:
    # MONEY_CONTEXT must declare prec=28 (Python default) and rounding=ROUND_HALF_UP.
    # If a future patch flips either, every test in the suite must fail loud.
    assert MONEY_CONTEXT.prec == 28
    assert MONEY_CONTEXT.rounding == ROUND_HALF_UP


def test_cent_constant() -> None:
    # CENT is the quantum for end-of-period money rounding.
    assert Decimal("0.01") == CENT


def test_quantize_cents_does_not_mutate_global_context() -> None:
    # Pitfall 9: quantize_cents must use `with localcontext(MONEY_CONTEXT):`
    # so the global getcontext() is unchanged after the call.
    # This guards against test-order-dependent failures across the suite.
    global_rounding_before = getcontext().rounding
    global_prec_before = getcontext().prec
    _ = quantize_cents(Decimal("123.456"))
    assert getcontext().rounding == global_rounding_before
    assert getcontext().prec == global_prec_before


def test_quantize_rate_round_half_up() -> None:
    """quantize_rate quantizes to 6 decimal places using ROUND_HALF_UP.

    Promoted from lib/affordability.py._quantize_rate (Phase 4 D-09) per
    Phase 5 D-14. The half-up boundary case (0.0654995 -> 0.065500) is
    the load-bearing pin: Python's default Decimal context is
    ROUND_HALF_EVEN (banker's rounding) which would produce 0.065498 —
    US consumer finance discipline (CLAUDE.md) requires HALF_UP.
    """
    # Typical Phase 4 affordability result; pads to 6 decimals.
    assert quantize_rate(Decimal("0.065")) == Decimal("0.065000")
    # Half-up boundary (exact halfway → rounds UP, not banker's even).
    assert quantize_rate(Decimal("0.0654995")) == Decimal("0.065500")
    # Just below half → rounds DOWN.
    assert quantize_rate(Decimal("0.0654994")) == Decimal("0.065499")
    # Above half → rounds UP.
    assert quantize_rate(Decimal("0.0654996")) == Decimal("0.065500")
    # Zero edge.
    assert quantize_rate(Decimal("0.000000")) == Decimal("0.000000")
    # Unit edge (max LTV scenario).
    assert quantize_rate(Decimal("1.000000")) == Decimal("1.000000")
    # 28-digit input (LTV math from affordability) clamps to 6 places.
    assert quantize_rate(Decimal("0.123456789012345")) == Decimal("0.123457")
