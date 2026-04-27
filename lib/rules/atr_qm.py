"""ATR/QM General-QM + Safe-Harbor price-based test per 12 CFR §1026.43(e)(2).

Citation: 12 CFR §1026.43(e)(2) - General Qualified Mortgage Loan Definition,
as amended by the CFPB Dec 2020 final rule (mandatory compliance 2022-10-01),
which replaced the legacy 43% DTI cap with a price-based test on the spread
between APR and the Average Prime Offer Rate (APOR). Safe-Harbor variant
in §1026.43(b)(4) uses tighter spread thresholds.
Source URL: https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition
Effective: 2022-10-01

What this predicate decides:
  Given APR, APOR, loan amount, and lien position, return whether the loan
  passes the General-QM price-based test (or, via safe_harbor_qm_passes, the
  tighter Safe-Harbor variant). The threshold table (loan-amount-tier *
  lien-position -> APR-APOR threshold percentage points) is loaded from
  data/reference/atr-qm-thresholds.yml; CFPB indexes the loan-amount tiers
  annually so the YAML is the single source of truth.

Inputs:
    apr: Decimal - fractional APR (e.g. Decimal("0.0700") = 7.00%)
    apor: Decimal - fractional Average Prime Offer Rate (e.g. Decimal("0.0500"))
    loan_amount: Decimal - principal loan amount in dollars (positive)
    lien_position: Literal["first", "subordinate"] - lien priority

Outputs:
    bool - True if the loan passes the test (i.e. APR-APOR spread is within
    the applicable threshold).

LOCKED DECISION - Threshold-unit convention (per CONTEXT.md D-02):
  YAML stores threshold as PERCENTAGE POINTS (e.g. "2.25" = 2.25 pp).
  Predicate divides by 100 at consumption time to compare against the
  fractional spread `apr - apor`. Stays human-readable against CFPB's
  published table while keeping all arithmetic in Decimal.

LOCKED DECISION - Boundary semantics (per RESEARCH.md lines 877-887):
  Loan-amount tier boundaries are INCLUSIVE on the lower bound (`>=`) and
  EXCLUSIVE on the upper bound (`<`). Exactly $66,156 first-lien is in the
  mid band; exactly $110,260 first-lien is in the high band.

LOCKED DECISION - Comparison boundary (per RESEARCH.md line 886):
  The regulation uses `<=`, so APR-APOR spread exactly at the threshold
  COUNTS AS within threshold (predicate returns True).

Edge cases:
  - apr < 0 or apor < 0: raises ValueError (loud invalid-input guard).
  - loan_amount <= 0: raises ValueError.
  - No matrix row matches (lien_position, loan_amount): raises LookupError
    (loud - never silently returns False; would mask a YAML body bug).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Final, Literal

from lib.rules._loader import load_reference

LienPosition = Literal["first", "subordinate"]

_HUNDRED: Final[Decimal] = Decimal("100")


def general_qm_passes(
    apr: Decimal,
    apor: Decimal,
    loan_amount: Decimal,
    lien_position: LienPosition,
) -> bool:
    """Return True if the (apr - apor) spread passes the General-QM test.

    See module docstring for full edge-case behavior, including the locked
    threshold-unit convention and boundary semantics.
    """
    return _spread_passes(apr, apor, loan_amount, lien_position, "general_qm_threshold_pp")


def safe_harbor_qm_passes(
    apr: Decimal,
    apor: Decimal,
    loan_amount: Decimal,
    lien_position: LienPosition,
) -> bool:
    """Return True if the (apr - apor) spread passes the tighter Safe-Harbor test."""
    return _spread_passes(apr, apor, loan_amount, lien_position, "safe_harbor_threshold_pp")


def _spread_passes(
    apr: Decimal,
    apor: Decimal,
    loan_amount: Decimal,
    lien_position: LienPosition,
    column: str,
) -> bool:
    if apr < 0:
        raise ValueError(f"apr must be non-negative, got {apr}")
    if apor < 0:
        raise ValueError(f"apor must be non-negative, got {apor}")
    if loan_amount <= 0:
        raise ValueError(f"loan_amount must be positive, got {loan_amount}")

    ref = load_reference("atr-qm-thresholds")
    threshold_pp = _threshold_pp(ref, lien_position, loan_amount, column)
    threshold_fractional = threshold_pp / _HUNDRED
    spread = apr - apor
    # `<=` per 12 CFR §1026.43(e)(2): exactly-at-threshold counts as passing.
    return spread <= threshold_fractional


def _threshold_pp(
    ref: dict[str, Any],
    lien_position: LienPosition,
    loan_amount: Decimal,
    column: str,
) -> Decimal:
    """Look up threshold (in percentage points) for (lien_position, loan_amount)."""
    for row in ref["thresholds"]:
        if row["lien_position"] != lien_position:
            continue
        lo = Decimal(row["loan_amount_min"])
        hi_raw = row["loan_amount_max"]
        in_low = loan_amount >= lo
        in_high = hi_raw is None or loan_amount < Decimal(str(hi_raw))
        if in_low and in_high:
            return Decimal(row[column])
    raise LookupError(
        f"No ATR/QM threshold row matched (lien_position={lien_position!r}, "
        f"loan_amount={loan_amount}). Check data/reference/atr-qm-thresholds.yml."
    )
