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
  - No matching down-payment band for purchase/cash_out: raises LookupError
    (REF-04 schema gap).

IRRRL note: IRRRL fee is a flat 0.50% regardless of use-count or down-payment;
the predicate ignores is_first_use and down_payment_pct for loan_purpose="irrrl".
Same for manufactured_home_non_permanent (1.00%) and loan_assumption (0.50%).
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
    # Flat-fee branches: IRRRL, manufactured home, assumption — table lookup not used.
    if loan_purpose == "irrrl":
        fee_pct = Decimal(ref["flat_fees"]["irrrl"])
    elif loan_purpose == "manufactured_home_non_permanent":
        fee_pct = Decimal(ref["flat_fees"]["manufactured_home_non_permanent"])
    elif loan_purpose == "loan_assumption":
        fee_pct = Decimal(ref["flat_fees"]["loan_assumption"])
    elif loan_purpose in ("purchase", "cash_out_refi"):
        fee_pct = _lookup_purchase_or_cashout_pct(
            table=ref["purchase_and_cash_out"],
            down_payment_pct=down_payment_pct,
            is_first_use=is_first_use,
        )
    else:
        raise ValueError(f"loan_purpose={loan_purpose!r} not recognized")

    return quantize_cents(loan_amount * fee_pct)


def _lookup_purchase_or_cashout_pct(
    table: list[dict[str, Any]],
    down_payment_pct: Decimal,
    is_first_use: bool,
) -> Decimal:
    """Find the purchase/cash-out row whose down-payment band brackets the input.

    Bands are inclusive lower / EXCLUSIVE upper: 0..<5, 5..<10, >=10. The >=10 row
    has down_payment_max=1.00 which we treat as inclusive (1.00 = 100% down).

    Raises LookupError if no row matches (indicates REF-04 schema regression).
    """
    for row in table:
        dp_min = Decimal(row["down_payment_min"])
        dp_max = Decimal(row["down_payment_max"])
        # Lower bound inclusive; upper bound exclusive EXCEPT for the top band
        # whose max is 1.00 (which we treat as inclusive so 100%-down still maps).
        in_band = dp_min <= down_payment_pct < dp_max or (
            dp_max == Decimal("1.00") and down_payment_pct == Decimal("1.00")
        )
        if in_band:
            key = "first_use_pct" if is_first_use else "subsequent_use_pct"
            return Decimal(row[key])
    raise LookupError(
        f"No purchase_and_cash_out row matched down_payment_pct={down_payment_pct}. "
        f"REF-04 schema gap."
    )
