"""Mortgage interest deduction qualified loan limit per IRC §163(h)(3) + IRS Pub 936.

Citation: IRC §163(h)(3) (mortgage interest deduction) as amended by the Tax
Cuts and Jobs Act of 2017 (TCJA). Computational worksheet in IRS Publication 936
Table 1. Post-2017 acquisition debt cap = $750,000 (single / MFJ / HoH) or
$375,000 (MFS). Pre-2017 grandfathered acquisition debt cap = $1,000,000 or
$500,000 (MFS).
Source URL: https://www.irs.gov/pub/irs-pdf/p936.pdf
Effective: 2025-01-01

What this predicate decides:
  Given filing_status and grandfathering / binding-contract grace-period flags,
  return the applicable qualified loan limit Decimal cap.

Inputs:
    filing_status: Literal["single", "mfj", "mfs", "hoh"]
    has_grandfathered_debt: bool — True if the acquisition debt was incurred
                                   ON or BEFORE 2017-12-15 (caller responsible
                                   for evaluating origination dates).
    binding_contract_signed_before_2017_12_15: bool — TCJA transition rule
                                   flag (a). Default False.
    binding_contract_closed_before_2018_04_01: bool — TCJA transition rule
                                   flag (b). Default False.

Outputs:
    Decimal — qualified loan limit cap in dollars.

LOCKED DECISION — Grace-period encoding (per RESEARCH.md line 912 + line 1369):
  The TCJA binding-contract grace period requires BOTH dates (signed ≤ 2017-12-15
  AND closed < 2018-04-01); a single origination_date field cannot capture this.
  This predicate takes TWO booleans; when BOTH are True, treats the debt as
  grandfathered (applies pre-2017 cap). The predicate does NOT do calendar
  arithmetic on dates — caller is responsible for providing the booleans based
  on the actual contract / closing dates.

OUT OF SCOPE — Points deductibility (Pub 936 §3):
  Deductibility of mortgage points hinges on settlement-statement facts (loan
  secured by primary residence, points paid as fee, computed as % of loan,
  shown on settlement statement) that this predicate does not have. RUL-11
  returns the qualified-loan-limit cap only. Deferred to a future plan.

Edge cases:
  - filing_status not in the literal set: raises ValueError.
  - MFS filing status: cap is HALF of the corresponding single/MFJ/HoH cap
    (per IRS Pub 936; encoded directly in REF-07 YAML, not divided here).
  - Grace-period flags only matter when has_grandfathered_debt=False; if
    has_grandfathered_debt=True the predicate already applies grandfathered cap.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from lib.rules._loader import load_reference

FilingStatus = Literal["single", "mfj", "mfs", "hoh"]


def qualified_loan_limit(
    filing_status: FilingStatus,
    has_grandfathered_debt: bool = False,
    binding_contract_signed_before_2017_12_15: bool = False,
    binding_contract_closed_before_2018_04_01: bool = False,
) -> Decimal:
    """Return the IRS Pub 936 qualified loan limit cap for this filing status.

    See module docstring for full edge-case behavior, including the locked
    grace-period-as-two-booleans decision.
    """
    if filing_status not in ("single", "mfj", "mfs", "hoh"):
        raise ValueError(
            f"filing_status must be 'single' | 'mfj' | 'mfs' | 'hoh', got {filing_status!r}"
        )

    ref = load_reference("irs-pub936")

    # Grace period: BOTH flags required (per RESEARCH.md line 912 locked decision).
    grace_qualifies = (
        binding_contract_signed_before_2017_12_15 and binding_contract_closed_before_2018_04_01
    )

    if has_grandfathered_debt or grace_qualifies:
        cap_str = ref["caps"]["pre_2017_grandfathered"][filing_status]
    else:
        cap_str = ref["caps"]["post_2017"][filing_status]

    return Decimal(cap_str)
