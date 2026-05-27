"""Fannie Mae LLPA matrix lookup (Loan-Level Price Adjustments).

Citation: Fannie Mae LLPA Matrix, Single-Family Selling Guide §B5-1.

Source URL: https://singlefamily.fanniemae.com/media/9391/display
Effective: 2026-01-28 (latest matrix revision; pinned per CONTEXT.md Assumption A4 -
quarterly Fannie republication cadence; annual refresh = YAML edit + commit).

Pattern reference: cfpb/jumbo-mortgage one-predicate-per-citation pattern.

What this predicate decides:
  Given borrower credit score, loan LTV %, loan purpose, occupancy, and unit
  count, return the LLPA in basis points (negative = credit, positive = charge)
  per Fannie's published Single-Family Selling Guide §B5-1 matrix.

The lookup composes:
  - loan_purpose_llpa_bps[loan_purpose][credit_score_bucket][ltv_bucket]
  - occupancy_addons[occupancy]                     (second_home / investment)
  - unit_count_addons[str(unit_count)]              (2-4 unit add-on)

Pitfall 6 (LLPA tier-boundary off-by-one): credit-score 720 belongs to the
"720-739" bucket, NOT "700-719". Bucket helpers `_credit_score_bucket` and
`_ltv_bucket` are unit-tested at every boundary (700, 719, 720, 739, 740,
759, 760, 779, 780).

Per CONTEXT.md D-04: the current official loan-purpose grids are shipped. Cash-out
refinance only has Fannie cells through 80% LTV; higher-LTV cash-out requests
raise LookupError instead of fabricating values.
Per CONTEXT.md D-05: data/reference/fannie-llpa-matrix.yml is implementation-
detail under RUL-02; NOT a new REF-ID.

Inputs:
    credit_score: int (300-850; matches lib.rules.types.Borrower.credit_score)
    ltv_pct: Decimal (e.g., Decimal("80.00") for 80% LTV) — MUST be quantized
        to at most 2 decimal places (WR-03 02-REVIEW.md). The LLPA bucket
        schema is two-decimal-precision (e.g., 60.00 / 60.01-70.00); a value
        on the open fractional interval (60.00, 60.01) matches no bucket.
        compute_llpa raises ValueError on >2-decimal input rather than
        falling through to a generic LookupError.
    loan_purpose: Literal["purchase", "rate_term_refi", "cash_out_refi"]
    occupancy: Literal["primary", "second_home", "investment"]
    unit_count: int (1-4)

Output:
    Decimal LLPA in basis points (negative = credit, positive = charge).

Raises:
    LookupError: if no matrix row matches the (credit_score_bucket, ltv_bucket)
        cell — never silently returns Decimal("0") (CONTEXT.md `<specifics>`
        fail-loud discipline).
    ValueError: if inputs fail range validation (delegated to caller-side
        Pydantic — Borrower.credit_score is Field(ge=300, le=850)).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from lib.rules._loader import load_reference

LoanPurpose = Literal["purchase", "rate_term_refi", "cash_out_refi"]
Occupancy = Literal["primary", "second_home", "investment"]


def _credit_score_bucket(credit_score: int) -> str:
    """Map credit score (300-850) to its Fannie matrix bucket id.

    Bucket boundaries are LOW-INCLUSIVE, HIGH-INCLUSIVE per the YAML.
    Pitfall 6: 720 -> "720-739" (NOT "700-719"); the current official grid
    also separates 740-759, 760-779, and 780+ tiers.
    """
    raw = load_reference("fannie-llpa-matrix")
    buckets = raw["credit_score_buckets"]
    for bucket in buckets:
        lo = int(bucket["min"])
        hi = int(bucket["max"])
        if lo <= credit_score <= hi:
            return str(bucket["id"])
    raise LookupError(
        f"credit_score={credit_score} matches no Fannie LLPA bucket "
        f"(buckets cover 300-850; check YAML)"
    )


def _ltv_bucket(ltv_pct: Decimal) -> str:
    """Map LTV percentage to its Fannie matrix bucket id.

    Bucket boundaries are HIGH-INCLUSIVE per the YAML (e.g., 75.01-80.00
    includes 80.00 but excludes 75.00 which belongs to the lower bucket).

    WR-03 quantization contract (02-REVIEW.md): ltv_pct MUST be quantized to
    at most 2 decimal places. The YAML's bucket schema (...60.00 / 60.01-70.00)
    leaves a fractional gap on the open interval (60.00, 60.01); a 4-decimal
    LTV like Decimal("60.0056") would match no bucket and the predicate would
    fail loud. We surface the contract here as an explicit ValueError so the
    error message guides the caller to quantize, rather than dumping a generic
    LookupError mid-iteration.
    """
    exponent = ltv_pct.as_tuple().exponent
    # exponent is `int` for finite Decimals, `'n' | 'N' | 'F'` for NaN/Infinity.
    if not isinstance(exponent, int):
        raise ValueError(
            f"ltv_pct={ltv_pct} is not a finite Decimal "
            f"(exponent={exponent!r}); LLPA bucket lookup requires a finite, "
            f"two-decimal-quantized Decimal."
        )
    if exponent < -2:
        raise ValueError(
            f"ltv_pct={ltv_pct} must be quantized to <= 2 decimal places "
            f"(LLPA buckets are two-decimal-precision per the YAML schema); "
            f"got exponent={exponent}. Quantize the input "
            f"with .quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) before "
            f"calling compute_llpa()."
        )
    raw = load_reference("fannie-llpa-matrix")
    buckets = raw["ltv_buckets"]
    for bucket in buckets:
        lo = Decimal(bucket["min"])
        hi = Decimal(bucket["max"])
        if lo <= ltv_pct <= hi:
            return str(bucket["id"])
    raise LookupError(
        f"ltv_pct={ltv_pct} matches no Fannie LLPA LTV bucket (buckets cover 0-97; check YAML)"
    )


def compute_llpa(
    credit_score: int,
    ltv_pct: Decimal,
    loan_purpose: LoanPurpose,
    occupancy: Occupancy,
    unit_count: int,
) -> Decimal:
    """Return Fannie LLPA in basis points for the given borrower/loan profile.

    Composes the loan-purpose matrix + occupancy add-on + unit-count add-on.
    All components come from data/reference/fannie-llpa-matrix.yml
    (implementation-detail under RUL-02 per CONTEXT.md D-05).

    Per CONTEXT.md `<specifics>` fail-loud discipline: raises LookupError when
    no matrix row matches the (credit_score_bucket, ltv_bucket) cell — never
    silently returns Decimal("0").
    """
    raw = load_reference("fannie-llpa-matrix")
    cs_bucket = _credit_score_bucket(credit_score)
    ltv_b = _ltv_bucket(ltv_pct)

    try:
        base_bps = Decimal(raw["loan_purpose_llpa_bps"][loan_purpose][cs_bucket][ltv_b])
    except KeyError as exc:
        raise LookupError(
            f"No Fannie LLPA cell for "
            f"loan_purpose={loan_purpose!r}, credit_score_bucket={cs_bucket!r}, "
            f"ltv_bucket={ltv_b!r} "
            f"(CONTEXT.md fail-loud discipline; check YAML)"
        ) from exc

    try:
        occ_addon = Decimal(raw["occupancy_addons"][occupancy])
    except KeyError as exc:
        raise LookupError(f"No Fannie LLPA occupancy_addon for occupancy={occupancy!r}") from exc

    try:
        unit_addon = Decimal(raw["unit_count_addons"][str(unit_count)])
    except KeyError as exc:
        raise LookupError(f"No Fannie LLPA unit_count_addon for unit_count={unit_count!r}") from exc

    return base_bps + occ_addon + unit_addon
