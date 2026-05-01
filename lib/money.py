"""Money discipline helpers.

Every Decimal in this project is constructed from strings, quantized end-of-period
with ROUND_HALF_UP, and never mixed with float in the same expression.

This module is the single source of truth for project-wide Decimal discipline (FND-01).
Every other module imports `to_money`, `quantize_cents`, `CENT`, and/or `MONEY_CONTEXT`
from here; nobody constructs `Decimal` from a literal in scattered places.

Why ROUND_HALF_UP instead of Python's default ROUND_HALF_EVEN (banker's rounding)?
Banker's rounding is correct for accounting averages but wrong for US consumer mortgage
math; lender amortization schedules use ROUND_HALF_UP. See pitfall 2 in 01-RESEARCH.md.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Final

CENT: Final[Decimal] = Decimal("0.01")
"""The quantum for end-of-period money rounding."""

MONEY_CONTEXT: Final[Context] = Context(prec=28, rounding=ROUND_HALF_UP)
"""Project-wide Decimal context. prec=28 is Python default; rounding is set
explicitly because Python's default is ROUND_HALF_EVEN (banker's), which is
wrong for US consumer finance."""


def to_money(value: str) -> Decimal:
    """Construct a money Decimal from a string.

    Floats are rejected at the type level by mypy --strict; runtime callers passing
    a non-str will see a TypeError from Decimal's constructor (we don't catch it —
    failing loud is the contract).
    """
    return Decimal(value)


def quantize_cents(value: Decimal) -> Decimal:
    """Round a Decimal to two places using ROUND_HALF_UP.

    Call ONCE at end-of-period; never mid-calculation. Uses `localcontext` so the
    global Decimal context is not mutated (pitfall 9).
    """
    with localcontext(MONEY_CONTEXT):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)


_RATE_QUANTUM: Final[Decimal] = Decimal("0.000001")
"""The quantum for end-of-period rate rounding (matches lib.models.Rate decimal_places=6).

Companion to CENT (the quantum for quantize_cents at 2 decimal places).
Phase 5 D-14 promotes this constant from lib/affordability.py:613 (Phase 4)
to lib/money.py because Phase 5's ARM engine becomes the second consumer.
"""


def quantize_rate(rate: Decimal) -> Decimal:
    """Quantize a fractional rate to 6 decimal places using ROUND_HALF_UP.

    Companion to quantize_cents (2 decimal places for Money). Use for any
    Rate-typed value at end-of-period; never quantize mid-calculation
    (Phase 1 PITFALLS, Phase 3 D-04, Phase 4 D-09 inherited).

    The 6-decimal quantum matches lib.models.Rate's
    Annotated[Decimal, Field(max_digits=7, decimal_places=6)] constraint.

    Promoted from lib/affordability.py._quantize_rate (Phase 4 D-09) to
    lib/money.py per Phase 5 D-14 because Phase 5 lib/arm.py is the
    second consumer.
    """
    with localcontext(MONEY_CONTEXT):
        return rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)
