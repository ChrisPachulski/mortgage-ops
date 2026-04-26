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
