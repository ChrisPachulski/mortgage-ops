"""Loan-type classification (conforming/jumbo/FHA/VA/USDA).

Citation: 12 USC §1717 (FHFA conforming loan limit authority — established Fannie
Mae and the conforming-loan-limit framework) + NHA §203(b)(2) (FHA loan limits as
a percentage of the conforming limit). Per-county overrides published annually by
FHFA (conventional / VA) and HUD (FHA).
Source URL: https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026
Effective: 2026-01-01

What this predicate decides:
  Given a loan amount, county (or None), program, and unit count, return the
  LoanType enum value identifying which loan program / tier applies.

Adopts the cfpb/jumbo-mortgage 'fail loud on missing county' pattern: when a
county-specific limit is required (loan_amount > baseline, conventional/FHA/VA
program), this predicate raises MissingCountyDataError rather than silently
defaulting to baseline. Loans at or below baseline can be classified without
county data because every county gets at least the baseline limit.

Inputs:
    loan_amount: Decimal (positive)
    county: County | None (from lib.rules.types)
    program: Literal["conventional", "fha", "va", "usda"]
    unit_count: int (1..4; v1 supports unit_count=1 only)

Outputs:
    LoanType (Literal from lib.rules.types)

Edge cases:
  - county=None + loan_amount <= baseline → conforming (no county lookup needed)
  - county=None + loan_amount > baseline → MissingCountyDataError (loud, never
    silent baseline fallback) — Pitfall 7 protection
  - program=fha + loan_amount > floor + county=None → MissingCountyDataError
  - program=fha + loan_amount > county ceiling → NotImplementedError (jumbo FHA
    not in v1)
  - program=va before REF-04 lands → NotImplementedError pointing to plan 02-03
  - unit_count > 1 → NotImplementedError (multi-family deferred to v2)
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from lib.rules._loader import load_reference

if TYPE_CHECKING:
    from lib.rules.types import County, LoanType


class MissingCountyDataError(ValueError):
    """Raised when classification requires county-specific limits but caller
    passed county=None and loan_amount > baseline.

    Adopts cfpb/jumbo-mortgage 'fail loud on missing county' (their `needCounty`
    sentinel becomes our exception). Never silently default to baseline — that
    would misclassify $830k loans in low-cost counties as conforming when they
    are actually jumbo (Pitfall 7).
    """


_UNIT_WORD: dict[int, str] = {1: "one", 2: "two", 3: "three", 4: "four"}


def classify(
    loan_amount: Decimal,
    county: County | None,
    program: Literal["conventional", "fha", "va", "usda"] = "conventional",
    unit_count: int = 1,
) -> LoanType:
    """Classify a loan into one of the LoanType enum values.

    See module docstring for full edge-case behavior.
    """
    if unit_count != 1:
        raise NotImplementedError(
            f"unit_count={unit_count} not yet supported; v1 ships unit_count=1 only "
            f"(multi-family classification deferred — see roadmap)"
        )
    if program == "usda":
        return "usda"
    if program == "conventional":
        return _classify_conventional(loan_amount, county, unit_count)
    if program == "fha":
        return _classify_fha(loan_amount, county, unit_count)
    if program == "va":
        return _classify_va(loan_amount, county, unit_count)
    raise NotImplementedError(f"program={program!r} not recognized")


def _classify_conventional(
    loan_amount: Decimal, county: County | None, unit_count: int
) -> LoanType:
    ref = load_reference("conforming-limits-2026")
    unit_key = f"{_UNIT_WORD[unit_count]}_unit"
    baseline = Decimal(ref["limits"]["baseline"][unit_key])
    if loan_amount <= baseline:
        return "conforming"
    if county is None:
        raise MissingCountyDataError(
            f"loan_amount {loan_amount} exceeds baseline {baseline}; "
            f"county required to classify as high_balance vs jumbo"
        )
    county_limit = _county_limit(ref, county, unit_key, baseline)
    if loan_amount <= county_limit:
        return "high_balance"
    return "jumbo"


def _classify_fha(loan_amount: Decimal, county: County | None, unit_count: int) -> LoanType:
    """FHA classification per HUD ML 2025-23 (REF-02).

    Floor = $541,287 (low-cost areas); ceiling = $1,249,125 (high-cost areas).
    Loans at or below floor → fha_standard. Loans above floor but at or below
    county ceiling → fha_high_balance. Loans above county ceiling → out of FHA
    program (raise NotImplementedError; jumbo FHA is not a v1 product).
    """
    ref = load_reference("fha-limits-2026")
    unit_key = f"{_UNIT_WORD[unit_count]}_unit"
    floor = Decimal(ref["limits"]["floor"][unit_key])
    if loan_amount <= floor:
        return "fha_standard"
    if county is None:
        raise MissingCountyDataError(
            f"FHA loan_amount {loan_amount} exceeds floor {floor}; "
            f"county required to determine high-balance vs out-of-program"
        )
    county_limit = _county_limit_fha(ref, county, unit_key, floor)
    if loan_amount <= county_limit:
        return "fha_high_balance"
    raise NotImplementedError(
        f"loan_amount {loan_amount} exceeds FHA county ceiling {county_limit} "
        f"for {county.name}; loans above the FHA ceiling are not eligible for "
        f"the FHA program (consider conventional jumbo)"
    )


def _classify_va(loan_amount: Decimal, county: County | None, unit_count: int) -> LoanType:
    """VA classification reads REF-04 wiring.

    VA uses the FHFA conforming limits for full-entitlement vets (since 2020).
    Implementation lands when plan 02-03 ships VA infrastructure.
    """
    raise NotImplementedError("VA classify() body shipped in plan 02-03 (RUL-06/RUL-07 wiring)")


def _county_limit(ref: dict[str, Any], county: County, unit_key: str, baseline: Decimal) -> Decimal:
    """Return county-specific limit, falling back to baseline if county is not
    in the high-cost subset."""
    for entry in ref["limits"]["high_cost_counties"]:
        if entry["state_fips"] == county.state_fips and entry["county_fips"] == county.county_fips:
            return Decimal(entry[unit_key])
    return baseline


def _county_limit_fha(
    ref: dict[str, Any], county: County, unit_key: str, floor: Decimal
) -> Decimal:
    """Return county-specific FHA ceiling, falling back to floor for unlisted
    counties (matches HUD's convention: low-cost areas use the floor)."""
    for entry in ref["limits"]["high_cost_counties"]:
        if entry["state_fips"] == county.state_fips and entry["county_fips"] == county.county_fips:
            return Decimal(entry[unit_key])
    return floor
