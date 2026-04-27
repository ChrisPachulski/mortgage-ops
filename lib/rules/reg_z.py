"""Reg Z APR-tolerance check per 12 CFR §1026.22(a)(2)-(a)(3).

Citation: 12 CFR §1026.22 - Determination of annual percentage rate (APR);
tolerance §1026.22(a)(2) (regular transactions: +/- 1/8 percentage point) and
§1026.22(a)(3) (irregular transactions: +/- 1/4 percentage point).
Source URL: https://www.consumerfinance.gov/rules-policy/regulations/1026/22/
Effective: 2010-09-30

What this predicate decides:
  Given the lender's disclosed APR and the predicate-computed actual APR,
  return whether the disclosure is within the Reg Z tolerance for the
  transaction type (regular or irregular).

Inputs:
    disclosed_apr: Decimal - fractional APR as disclosed on the LE/CD
                   (e.g. Decimal("0.0700") = 7.00%); non-negative.
    actual_apr: Decimal - fractional APR as computed by the predicate
                / oracle / Phase-7 APR solver; non-negative.
    is_irregular_transaction: bool - caller-provided. Per §1026.22(a)(3),
                              "irregular" = multiple advances, irregular
                              payment periods, or irregular payment amounts
                              (other than an irregular first period or
                              first/final payment). Caller is responsible
                              for classification - this predicate does NOT
                              classify the transaction itself.

Outputs:
    bool - True if abs(disclosed - actual) <= applicable tolerance.

LOCKED DECISIONS:
- D-02 (CONTEXT.md): Tolerance values live in CODE (no YAML). The two
  statutory constants (1/8 pp = Decimal("0.00125"); 1/4 pp = Decimal("0.0025"))
  have not changed since the original Reg Z text and are encoded directly
  here as module-level constants with §1026.22(a)(2) / §1026.22(a)(3)
  citation comments.
- Comparison boundary uses `<=` per the regulation's "does not exceed" /
  "does not vary" language: APR difference exactly equal to the tolerance
  COUNTS AS within tolerance (predicate returns True).
- Decimal arithmetic exactness (Pitfall 11): the predicate uses
  `abs(disclosed - actual) <= tolerance` with Decimal-only operands. No
  float arithmetic. Exactly-at-tolerance comparisons are reliable.

Phase-7 consumer note (RESEARCH.md line 898): Phase 7 (Estimated APR)
imports this predicate to verify the estimated APR is within Reg Z
tolerance of the lender's disclosed APR. Phase 7 keeps the "estimated APR"
label because we do not make commercial Reg Z disclosures - this predicate
is the gate, not a disclosure.

Edge cases:
  - disclosed_apr < 0 or actual_apr < 0: raises ValueError (loud).
  - is_irregular_transaction toggles between TOLERANCE_REGULAR and
    TOLERANCE_IRREGULAR; no other distinction is made.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

# 12 CFR §1026.22(a)(2) - regular transaction tolerance: 1/8 percentage point.
# 1/8 pp = 0.125 percentage points = Decimal("0.00125") fractional.
TOLERANCE_REGULAR: Final[Decimal] = Decimal("0.00125")

# 12 CFR §1026.22(a)(3) - irregular transaction tolerance: 1/4 percentage point.
# 1/4 pp = 0.25 percentage points = Decimal("0.0025") fractional.
# "Irregular" = multiple advances, irregular payment periods, or irregular
# payment amounts (other than an irregular first period or first/final payment).
TOLERANCE_IRREGULAR: Final[Decimal] = Decimal("0.0025")


def within_apr_tolerance(
    disclosed_apr: Decimal,
    actual_apr: Decimal,
    is_irregular_transaction: bool,
) -> bool:
    """Return True iff abs(disclosed - actual) is within the applicable Reg Z tolerance.

    See module docstring for full edge-case behavior, including the locked
    no-YAML / Decimal-exactness / `<=`-boundary decisions.
    """
    if disclosed_apr < 0:
        raise ValueError(f"disclosed_apr must be non-negative, got {disclosed_apr}")
    if actual_apr < 0:
        raise ValueError(f"actual_apr must be non-negative, got {actual_apr}")

    tolerance = TOLERANCE_IRREGULAR if is_irregular_transaction else TOLERANCE_REGULAR
    # Decimal abs/subtract - exact arithmetic; no float precision drift (Pitfall 11).
    return abs(disclosed_apr - actual_apr) <= tolerance
