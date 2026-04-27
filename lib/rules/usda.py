"""USDA SFH Guaranteed Loan Program eligibility per 7 CFR Part 3555.

Citation: 7 CFR Part 3555 — USDA Rural Development Single Family Housing
Guaranteed Loan Program (SFH GLP). Income limit = 115% of area median income
(AMI), with separate caps for 1-4-person and 5-8-person households. Per-household
8% uplift for each person above 8. Guarantee fee per 7 CFR §3555.107: 1.0%
upfront + 0.35% annual on average outstanding balance.
Source URL: https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do
Effective: 2025-10-01

What this predicate decides:
  Given household_income, household_size, county, and loan_amount, return:
    income_eligible: bool — household_income <= applicable USDA income limit
    applicable_income_limit: Decimal — the income cap that was applied
    guarantee_fee_upfront: Decimal — 1.0% of loan_amount, quantized to cents
    guarantee_fee_annual: Decimal — 0.35% of loan_amount, quantized to cents

Inputs:
    household_income: Decimal (annual household income, positive)
    household_size: int (positive; 1+; bands: 1-4 vs 5-8 vs 8+ with uplift)
    county: County (Pydantic v2 model from lib.rules.types — state_fips +
                    county_fips + name; required, never None)
    loan_amount: Decimal (positive loan principal in dollars)

Outputs:
    USDAEligibilityResult (Pydantic v2 frozen+strict+extra=forbid).

LOCKED DECISION — Missing-county handling (per Phase 2 D-PHASE2-Q5 + Pitfall 4):
  When `county` is NOT in REF-06's by_county list, this predicate FALLS BACK
  to the default income limits (does NOT raise MissingCountyDataError). This is
  intentionally DIFFERENT from lib.rules.loan_type.classify, which raises on
  unlisted counties. The asymmetry is correct because:
    - loan_type.classify asks "is this county high-cost?" (silent fallback would
      misclassify a high-cost county as conforming).
    - usda.evaluate asks "what is this county's USDA income limit?" — and per
      USDA published policy, unlisted counties USE THE DEFAULT. Falling back to
      the default IS the correct USDA semantic, not a silent failure.
  Do not "fix" this to raise. The fall-back behavior is regulatory-correct.

Edge cases:
  - household_size > 8: applicable_income_limit = persons_5_to_8 +
    (household_size - 8) * persons_5_to_8 * per_extra_member_pct (USDA's 8%
    per-person uplift above 8).
  - household_income <= 0, household_size <= 0, loan_amount <= 0: raises
    ValueError (loud failure on invalid input).
  - Even when income_eligible=False, guarantee fees are still returned —
    consumer decides what to do (some downstream flows want the "what would
    the fee be if you DID qualify" number).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from lib.money import quantize_cents
from lib.rules._loader import load_reference

if TYPE_CHECKING:
    from lib.rules.types import County


class USDAEligibilityResult(BaseModel):
    """Output of usda.evaluate. Frozen + strict + extra=forbid per Phase 1 conventions."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    income_eligible: bool
    applicable_income_limit: Decimal = Field(strict=True, ge=Decimal("0"))
    guarantee_fee_upfront: Decimal = Field(strict=True, ge=Decimal("0"))
    guarantee_fee_annual: Decimal = Field(strict=True, ge=Decimal("0"))


def evaluate(
    household_income: Decimal,
    household_size: int,
    county: County,
    loan_amount: Decimal,
) -> USDAEligibilityResult:
    """Evaluate USDA SFH GLP eligibility + compute guarantee fees per 7 CFR Part 3555.

    See module docstring for full edge-case behavior, including the locked
    silent-fallback decision for unlisted counties.
    """
    if household_income <= 0:
        raise ValueError(f"household_income must be positive, got {household_income}")
    if household_size <= 0:
        raise ValueError(f"household_size must be positive, got {household_size}")
    if loan_amount <= 0:
        raise ValueError(f"loan_amount must be positive, got {loan_amount}")

    ref = load_reference("usda-income-limits")
    applicable_limit = _income_limit_for(ref, county, household_size)

    upfront_pct = Decimal(ref["guarantee_fee"]["upfront_pct"])
    annual_pct = Decimal(ref["guarantee_fee"]["annual_pct"])

    return USDAEligibilityResult(
        income_eligible=household_income <= applicable_limit,
        applicable_income_limit=applicable_limit,
        guarantee_fee_upfront=quantize_cents(loan_amount * upfront_pct),
        guarantee_fee_annual=quantize_cents(loan_amount * annual_pct),
    )


def _income_limit_for(
    ref: dict[str, Any],
    county: County,
    household_size: int,
) -> Decimal:
    """Resolve applicable USDA income limit for (county, household_size).

    LOCKED DECISION (D-PHASE2-Q5): If county is NOT in by_county overrides,
    fall back to default limits silently — this is correct USDA semantics, NOT
    a missing-data error. See module docstring for rationale.
    """
    # Look for a county-specific override; if none, fall back to default.
    matched_override: dict[str, Any] | None = None
    for row in ref["income_limits"]["by_county"]:
        if row["state_fips"] == county.state_fips and row["county_fips"] == county.county_fips:
            matched_override = row
            break

    if matched_override is not None:
        persons_1_to_4 = Decimal(matched_override["persons_1_to_4"])
        persons_5_to_8 = Decimal(matched_override["persons_5_to_8"])
    else:
        # Silent fallback — correct USDA semantics per D-PHASE2-Q5.
        default = ref["income_limits"]["default"]
        persons_1_to_4 = Decimal(default["persons_1_to_4"])
        persons_5_to_8 = Decimal(default["persons_5_to_8"])

    if household_size <= 4:
        return persons_1_to_4
    if household_size <= 8:
        return persons_5_to_8
    # household_size > 8 — apply USDA's 8%-per-extra-person uplift above 8.
    per_extra_pct = Decimal(ref["income_limits"]["default"]["per_extra_member_pct"])
    extra_members = household_size - 8
    uplift = persons_5_to_8 * per_extra_pct * Decimal(extra_members)
    return persons_5_to_8 + uplift
