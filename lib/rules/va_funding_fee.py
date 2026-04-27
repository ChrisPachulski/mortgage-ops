"""VA funding fee computation per 38 USC §3729 + VA Lender Handbook M26-7 Chapter 8.

Citation: 38 USC §3729 (statutory authority for VA funding fee) + VA Lender
Handbook M26-7 Chapter 8 "Borrower Fees, Charges, and the VA Funding Fee" (current
fee table, effective 2023-04-07).
Source URL: https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf
Effective: 2023-04-07

What this predicate decides:
  Given loan_amount, down_payment_pct, is_first_use flag, loan_purpose, and
  is_exempt_from_funding_fee flag, return the VA funding fee dollar amount
  (quantized to cents end-of-period).

Inputs:
    loan_amount: Decimal (positive; loan principal)
    down_payment_pct: Decimal (in [0, 1]; 0.05 = 5%)
    is_first_use: bool (True for borrower's first VA-guaranteed loan; False for
                       subsequent uses — fee tier doubles for purchase < 5% down)
    loan_purpose: Literal["purchase", "cash_out_refi", "irrrl",
                          "manufactured_home_non_permanent", "loan_assumption"]
    is_exempt_from_funding_fee: bool (True for veterans receiving VA disability
                                      compensation — fee is $0 by statute)

Outputs:
    Decimal — funding fee in dollars, quantized to 2 decimal places (ROUND_HALF_UP).

Edge cases:
  - is_exempt=True: returns Decimal("0.00") immediately (no table lookup).
  - down_payment_pct < 0 or > 1: raises ValueError.
  - loan_purpose not in the literal set: raises ValueError.
  - No matching down-payment band for purchase: raises LookupError
    (REF-04 schema gap).

IRRRL note: IRRRL fee is a flat 0.50% regardless of use-count or down-payment;
the predicate ignores is_first_use and down_payment_pct for loan_purpose="irrrl".
Same for manufactured_home_non_permanent (1.00%) and loan_assumption (0.50%).

Cash-out refi note: Per VA M26-7 Chapter 8, cash-out refi fees are FLAT —
first-use 2.15% / subsequent-use 3.30% — and do NOT depend on
down_payment_pct (the very concept is incoherent for a refi). The predicate
ignores down_payment_pct for loan_purpose="cash_out_refi" and looks up
flat_fees.cash_out_{first,subsequent}_use directly. Fix for BL-02
(02-REVIEW.md): pre-fix code routed cash-out through the purchase
down-payment-banded table and could understate the fee by ~$3,600 on a
$400k 10%-down example.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from lib.money import quantize_cents
from lib.rules._loader import load_reference

VAFundingFeePurpose = Literal[
    "purchase",
    "cash_out_refi",
    "irrrl",
    "manufactured_home_non_permanent",
    "loan_assumption",
]


def compute(
    loan_amount: Decimal,
    down_payment_pct: Decimal,
    is_first_use: bool,
    loan_purpose: VAFundingFeePurpose,
    is_exempt_from_funding_fee: bool,
) -> Decimal:
    """Compute VA funding fee per VA M26-7 Chapter 8.

    See module docstring for full edge-case behavior.
    """
    if is_exempt_from_funding_fee:
        # Statutory exemption — no table lookup, no fee.
        return quantize_cents(Decimal("0"))

    if loan_amount <= 0:
        raise ValueError(f"loan_amount must be positive, got {loan_amount}")
    if down_payment_pct < 0 or down_payment_pct > 1:
        raise ValueError(f"down_payment_pct must be in [0, 1], got {down_payment_pct}")

    ref = load_reference("va-funding-fees")

    fee_pct: Decimal
    # Flat-fee branches: IRRRL, manufactured home, assumption, cash-out refi —
    # table lookup not used. Cash-out refi fees are flat per M26-7 Chapter 8
    # (BL-02 02-REVIEW.md): use-count selects the rate; down_payment_pct is
    # ignored.
    if loan_purpose == "irrrl":
        fee_pct = Decimal(ref["flat_fees"]["irrrl"])
    elif loan_purpose == "manufactured_home_non_permanent":
        fee_pct = Decimal(ref["flat_fees"]["manufactured_home_non_permanent"])
    elif loan_purpose == "loan_assumption":
        fee_pct = Decimal(ref["flat_fees"]["loan_assumption"])
    elif loan_purpose == "cash_out_refi":
        key = "cash_out_first_use" if is_first_use else "cash_out_subsequent_use"
        fee_pct = Decimal(ref["flat_fees"][key])
    elif loan_purpose == "purchase":
        fee_pct = _lookup_purchase_pct(
            table=ref["purchase"],
            down_payment_pct=down_payment_pct,
            is_first_use=is_first_use,
        )
    else:
        raise ValueError(f"loan_purpose={loan_purpose!r} not recognized")

    return quantize_cents(loan_amount * fee_pct)


def _lookup_purchase_pct(
    table: list[dict[str, Any]],
    down_payment_pct: Decimal,
    is_first_use: bool,
) -> Decimal:
    """Find the purchase row whose down-payment band brackets the input.

    Bands are inclusive lower / EXCLUSIVE upper for all rows EXCEPT the last
    row in the table, whose upper bound is INCLUSIVE so 100%-down maps cleanly
    (and so any future YAML edit that uses a non-1.00 top-row max — e.g. "1" or
    "1.0001" — still works correctly).

    WR-09 (02-REVIEW.md): pre-fix this last-row inclusivity was conditional on
    a magic literal `dp_max == Decimal("1.00")`. While Decimal("1") == Decimal("1.00")
    is True today, encoding the contract via row position is more robust than
    via a sentinel value: the YAML schema's invariant is "the last row covers
    the top of the range", not "the last row's max happens to equal 1.00".

    Cash-out refi does NOT use this table per M26-7 Ch 8 (see BL-02 fix in
    02-REVIEW.md / module docstring); it is flat-fee and routes through
    `flat_fees.cash_out_*` instead.

    Raises LookupError if no row matches (indicates REF-04 schema regression).
    """
    last_index = len(table) - 1
    for index, row in enumerate(table):
        dp_min = Decimal(row["down_payment_min"])
        dp_max = Decimal(row["down_payment_max"])
        is_last_row = index == last_index
        # Lower bound inclusive; upper bound exclusive on intermediate rows;
        # upper bound INCLUSIVE on the last row (regardless of its literal max).
        if is_last_row:
            in_band = dp_min <= down_payment_pct <= dp_max
        else:
            in_band = dp_min <= down_payment_pct < dp_max
        if in_band:
            key = "first_use_pct" if is_first_use else "subsequent_use_pct"
            return Decimal(row[key])
    raise LookupError(
        f"No purchase row matched down_payment_pct={down_payment_pct}. REF-04 schema gap."
    )
