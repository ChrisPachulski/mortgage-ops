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
  - program=fha + loan_amount > floor + county not in high-cost subset →
    MissingCountyDataError (mirrors conventional path; matches YAML notes)
  - program=fha + loan_amount > county ceiling → NotImplementedError (jumbo FHA
    not in v1)
  - program=va + loan_amount > baseline + county=None → MissingCountyDataError
  - program=va + loan_amount > county ceiling → NotImplementedError (partial-
    entitlement VA, which requires a gap-down-payment, is not a v1 product)
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
    """VA classification — full-entitlement vets use FHFA conforming limits since
    the 2020 Blue Water Navy Vietnam Veterans Act removed VA-specific loan limits.

    Loans <= conforming baseline → va_standard. Loans above baseline but at or
    below county ceiling → va_high_balance. Loans above county ceiling → out of
    VA full-entitlement (raise NotImplementedError; partial-entitlement is not a
    v1 product).
    """
    ref = load_reference("conforming-limits-2026")
    unit_key = f"{_UNIT_WORD[unit_count]}_unit"
    baseline = Decimal(ref["limits"]["baseline"][unit_key])
    if loan_amount <= baseline:
        return "va_standard"
    if county is None:
        raise MissingCountyDataError(
            f"VA loan_amount {loan_amount} exceeds baseline {baseline}; "
            f"county required to determine va_high_balance vs out-of-program"
        )
    county_limit = _county_limit(ref, county, unit_key, baseline)
    if loan_amount <= county_limit:
        return "va_high_balance"
    raise NotImplementedError(
        f"VA loan_amount {loan_amount} exceeds county ceiling {county_limit} "
        f"for {county.name}; partial-entitlement VA loans (which require down "
        f"payment to cover the gap) are not a v1 product"
    )


def _county_limit(ref: dict[str, Any], county: County, unit_key: str, baseline: Decimal) -> Decimal:
    """Return county-specific limit, falling back to baseline if county is not
    in the high-cost subset.

    BL-04 contract (02-REVIEW.md): the conforming-limits-2026.yml
    high_cost_counties entries currently ship only `one_unit` keys. The runtime
    `classify` guard (unit_count != 1 -> NotImplementedError) prevents this
    helper from being called with non-one_unit keys today, but defend in depth
    here so any future drop of that guard surfaces a documented gap rather
    than a confusing KeyError.
    """
    if unit_key != "one_unit":
        raise NotImplementedError(
            f"county-level multi-unit limits not yet shipped in "
            f"data/reference/conforming-limits-2026.yml; got unit_key={unit_key!r}. "
            f"Per Phase 2 decision D-PHASE2-Q2 only one_unit county data is shipped; "
            f"add per-unit columns from FHFA county XLSX before relaxing the "
            f"unit_count guard in classify()."
        )
    for entry in ref["limits"]["high_cost_counties"]:
        if entry["state_fips"] == county.state_fips and entry["county_fips"] == county.county_fips:
            return Decimal(entry[unit_key])
    return baseline


def _county_limit_fha(
    ref: dict[str, Any], county: County, unit_key: str, floor: Decimal
) -> Decimal:
    """Return county-specific FHA ceiling for an above-floor loan.

    Per data/reference/fha-limits-2026.yml notes (Phase 2 decision D-PHASE2-Q2):
    we ship a SUBSET of high-cost counties; unlisted counties whose loan exceeds
    the FHA floor must raise MissingCountyDataError so the caller can tell the
    difference between "really exceeds the FHA ceiling" and "your county is not
    in our shipped table." This mirrors `_county_limit` (conventional) which
    fails loud rather than silently defaulting.

    Note: callers MUST only invoke this helper when loan_amount > floor; loans
    at or below floor are classified as fha_standard without any county lookup.

    BL-04 contract (02-REVIEW.md): fha-limits-2026.yml high_cost_counties
    entries currently ship only `one_unit` keys. Defend in depth in case the
    `unit_count != 1` guard in classify() is ever relaxed.
    """
    if unit_key != "one_unit":
        raise NotImplementedError(
            f"county-level multi-unit FHA limits not yet shipped in "
            f"data/reference/fha-limits-2026.yml; got unit_key={unit_key!r}. "
            f"Per Phase 2 decision D-PHASE2-Q2 only one_unit county data is shipped; "
            f"add per-unit columns from HUD county tables before relaxing the "
            f"unit_count guard in classify()."
        )
    for entry in ref["limits"]["high_cost_counties"]:
        if entry["state_fips"] == county.state_fips and entry["county_fips"] == county.county_fips:
            return Decimal(entry[unit_key])
    raise MissingCountyDataError(
        f"FHA county ({county.state_fips}/{county.county_fips} {county.name!r}) not "
        f"in shipped high-cost subset; cannot determine ceiling. Add the county "
        f"to data/reference/fha-limits-2026.yml or pass a smaller loan amount."
    )
