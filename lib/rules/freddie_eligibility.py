"""Freddie Mac eligibility / Credit Fee Cap matrix lookup.

Citation: Freddie Mac Single-Family Seller/Servicer Guide §4203.4 + Credit Fee Cap matrix.

Source URL: https://sf.freddiemac.com/working-with-us/origination-underwriting/eligibility-criteria
Source URL: https://guide.freddiemac.com/app/guide/section/4203.4
Effective: 2026-01-15 (latest published matrix revision; pinned per CONTEXT.md
Assumption A4 — annual refresh = YAML edit + commit).

Pattern reference: cfpb/jumbo-mortgage one-predicate-per-citation pattern.

What this predicate decides:
  Given borrower credit score, loan LTV %, loan purpose, occupancy, and unit
  count, return Freddie's PUBLISHED eligibility (True/False) and Credit Fee Cap
  in basis points per the Single-Family Seller/Servicer Guide §4203.4 matrix.

Models the PUBLISHED Eligibility Matrix only — does NOT replicate Freddie's
proprietary LPA AUS decision (per CONTEXT.md `<deferred>` line 188).

Per CONTEXT.md D-05: data/reference/freddie-eligibility-matrix.yml is
implementation-detail under RUL-03; NOT a new REF-ID. The two Fannie/Freddie
matrices ship in lockstep so Phase 4 affordability can compose both outcomes
(see RESEARCH §RUL-03 line 810).

Inputs:
    credit_score: int (300-850)
    ltv_pct: Decimal (e.g., Decimal("80.00"))
    loan_purpose: Literal["purchase", "rate_term_refi", "cash_out_refi"]
    occupancy: Literal["primary", "second_home", "investment"]
    unit_count: int (1-4)

Output (FreddieEligibilityResult — frozen Pydantic v2 model):
    eligible: bool — True iff Freddie's matrix permits this loan profile.
    credit_fee_bps: Decimal — Freddie Credit Fee Cap in basis points.

Raises:
    LookupError: if no matrix cell matches the (credit_score_bucket, ltv_bucket)
        combination — never silently returns eligible=False with credit_fee_bps=0
        (CONTEXT.md `<specifics>` fail-loud discipline).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from lib.rules._loader import load_reference

LoanPurpose = Literal["purchase", "rate_term_refi", "cash_out_refi"]
Occupancy = Literal["primary", "second_home", "investment"]


class FreddieEligibilityResult(BaseModel):
    """Frozen Pydantic v2 result type — immutable predicate output.

    Phase 4 affordability composes this with `lib.rules.fannie_eligibility`
    output to derive cross-GSE eligibility.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    eligible: bool
    credit_fee_bps: Decimal


def _credit_score_bucket(credit_score: int) -> str:
    raw = load_reference("freddie-eligibility-matrix")
    for bucket in raw["credit_score_buckets"]:
        lo = int(bucket["min"])
        hi = int(bucket["max"])
        if lo <= credit_score <= hi:
            return str(bucket["id"])
    raise LookupError(
        f"credit_score={credit_score} matches no Freddie bucket (buckets cover 300-850; check YAML)"
    )


def _ltv_bucket(ltv_pct: Decimal) -> str:
    raw = load_reference("freddie-eligibility-matrix")
    for bucket in raw["ltv_buckets"]:
        lo = Decimal(bucket["min"])
        hi = Decimal(bucket["max"])
        if lo <= ltv_pct <= hi:
            return str(bucket["id"])
    raise LookupError(
        f"ltv_pct={ltv_pct} matches no Freddie LTV bucket (buckets cover 0-97; check YAML)"
    )


def evaluate(
    credit_score: int,
    ltv_pct: Decimal,
    loan_purpose: LoanPurpose,
    occupancy: Occupancy,
    unit_count: int,
) -> FreddieEligibilityResult:
    """Return Freddie eligibility + Credit Fee Cap for the given borrower/loan.

    Composes base eligibility cell + loan-purpose / occupancy / unit-count
    add-ons (additive bps applied on top of base credit_fee_bps). All come from
    data/reference/freddie-eligibility-matrix.yml.

    Per CONTEXT.md `<specifics>` fail-loud discipline: raises LookupError when
    no matrix row matches — never silently returns FreddieEligibilityResult(
    eligible=False, credit_fee_bps=Decimal("0")).
    """
    raw = load_reference("freddie-eligibility-matrix")
    cs_bucket = _credit_score_bucket(credit_score)
    ltv_b = _ltv_bucket(ltv_pct)

    try:
        cell = raw["eligibility"][cs_bucket][ltv_b]
    except KeyError as exc:
        raise LookupError(
            f"No Freddie eligibility cell for "
            f"credit_score_bucket={cs_bucket!r}, ltv_bucket={ltv_b!r} "
            f"(CONTEXT.md fail-loud discipline; check YAML)"
        ) from exc

    base_eligible = bool(cell["eligible"])
    base_bps = Decimal(cell["credit_fee_bps"])

    try:
        purpose_addon = Decimal(raw["loan_purpose_addons"][loan_purpose])
    except KeyError as exc:
        raise LookupError(
            f"No Freddie loan_purpose_addon for loan_purpose={loan_purpose!r}"
        ) from exc

    try:
        occ_addon = Decimal(raw["occupancy_addons"][occupancy])
    except KeyError as exc:
        raise LookupError(f"No Freddie occupancy_addon for occupancy={occupancy!r}") from exc

    try:
        unit_addon = Decimal(raw["unit_count_addons"][str(unit_count)])
    except KeyError as exc:
        raise LookupError(f"No Freddie unit_count_addon for unit_count={unit_count!r}") from exc

    total_bps = base_bps + purpose_addon + occ_addon + unit_addon
    return FreddieEligibilityResult(eligible=base_eligible, credit_fee_bps=total_bps)
