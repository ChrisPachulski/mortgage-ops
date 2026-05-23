"""Default homeowners-insurance annual estimate (state base + flood + earthquake).

Citation: Composite — NAIC Homeowners Insurance Report (Data for 2022,
  published 2025-05-21) for 49 covered states + DC; III state averages for
  CA + TX (NAIC excludes these via separate channel — see Pitfall 5);
  private-market homeowners-policy flood-uplift heuristic (NOT FEMA NFIP —
  Risk Rating 2.0 decoupled NFIP premium from FIRM zone in 2021-04;
  see Pitfall 6); CEA + PNW private-market averages for CA/OR/WA
  earthquake add-ons (Pitfall 7: flat-$ approximates ~$500-700k coverage).

  This is NOT a regulatory predicate — it is a per-state heuristic estimate
  that fires only when listing.insurance_estimate_annual is None (or its
  .value is None). Reports flag every estimated value via
  "INSURANCE-ESTIMATED-NAIC-{state}-{zone}" in eligible_reasons per
  CONTEXT D-16-INS-04. The wire-in lives at lib/property_analysis.py:703-705
  (added in Plan 16-03), NOT in lib/property_listing.py (Phase 13 frozen).
Source URL: https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022
  (additional URLs documented in YAML notes block — III for CA/TX,
   representative private-market carrier filings for flood multipliers,
   CEA + PNW carrier surveys for quake add-ons)
Effective: 2025-05-21 (NAIC report publication date)

What this predicate decides:
  Given a USPS state code and an optional FEMA flood zone, return the
  estimated annual homeowners insurance premium (Money). Composition:
    annual = state_base * flood_zone_multiplier + earthquake_state_addon

  Quantization happens ONCE at the boundary (Pitfall 6 — quantize_cents
  after the full multiplication + addition).

  For state not in {CA, OR, WA}: earthquake_addon = Decimal("0.00") silently
  (no row, no reason tag — per D-16-INS-03 Claude's Discretion).
  For flood_zone not in {X, A, AE, V} (including None): use "unknown" row.
  In v1.1 the caller (lib/property_analysis.py) ALWAYS passes flood_zone=None
  because PropertyListing has no flood_zone field (RESEARCH correction #1) —
  only the "unknown" multiplier row ever fires in v1.1.

Worked example (WA, Pachulski baseline):
  >>> from decimal import Decimal
  >>> r = lookup_default("WA", flood_zone=None)
  >>> # WA base 1191.00 * unknown multiplier 1.15 + WA quake addon 250.00
  >>> # = 1369.65 + 250.00 = 1619.65
  >>> r
  Decimal('1619.65')

Inputs:
    state: str (2-char USPS code; use fips_to_usps() to convert household.state_fips)
    flood_zone: str | None (FEMA FIRM zone; None always in v1.1)

Outputs:
    Money (Decimal; annual premium, quantize_cents-applied at boundary)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from lib.models import Money  # noqa: TC001  # Pydantic resolves annotations at runtime
from lib.money import quantize_cents
from lib.rules._loader import load_reference

# Census Bureau immutable metadata; no refresh cadence; constant dict per
# CONTEXT D-16-FILE-02 ("small constant dict in lib/rules/insurance.py").
# 50 states + DC = 51 entries. Note FIPS codes skip 03, 07, 14, 43, 52
# (those are reserved / formerly-assigned codes per the Census Bureau).
_FIPS_TO_USPS: Final[dict[str, str]] = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
}


def fips_to_usps(state_fips: str) -> str:
    """Lookup USPS code from 2-digit FIPS. Raises KeyError on unknown FIPS.

    Used by the Phase 14 wire-in (Plan 16-03) to convert household.state_fips
    (2-digit FIPS code) into the USPS code that `lookup_default(state, ...)`
    expects.
    """
    if state_fips not in _FIPS_TO_USPS:
        raise KeyError(
            f"Unknown state FIPS {state_fips!r}; expected one of {sorted(_FIPS_TO_USPS)!r}"
        )
    return _FIPS_TO_USPS[state_fips]


def lookup_default(state: str, flood_zone: str | None) -> Money:
    """Look up the default annual homeowners-insurance premium for `state` +
    optional `flood_zone`. Returns the quantized annual premium per the
    composition formula `state_base * flood_zone_multiplier + eq_addon`.

    See module docstring for full behavior including silent-zero quake and
    forward-compat flood path.
    """
    ref = load_reference("insurance-estimate-defaults")

    # 1. State base (exact-match USPS lookup). Missing-state raises LookupError
    # (loud — REF-10 schema gap; every USPS code must be covered).
    base_row = next(
        (r for r in ref["state_base_annual_premium"] if r["state"] == state),
        None,
    )
    if base_row is None:
        raise LookupError(
            f"No state_base_annual_premium row for state={state!r}. "
            f"REF-10 schema gap — every USPS code must be covered."
        )
    base = Decimal(base_row["base_annual"])

    # 2. Flood multiplier (exact-match zone; default to "unknown" row for
    # None / unrecognized zones). Defensive Decimal("1.00") fallback against
    # YAML drift — never silently scale by a wrong factor.
    zone_key = flood_zone if flood_zone in {"X", "A", "AE", "V"} else "unknown"
    mult_row = next(
        (r for r in ref["flood_zone_multipliers"] if r["zone"] == zone_key),
        None,
    )
    multiplier = Decimal(mult_row["multiplier"]) if mult_row else Decimal("1.00")

    # 3. Earthquake add-on (CA/OR/WA only; silent Decimal("0.00") otherwise
    # per CONTEXT D-16-INS-03 Claude's-Discretion — no reason tag fires for
    # non-{CA, OR, WA} states).
    eq_row = next(
        (r for r in ref["earthquake_state_addons"] if r["state"] == state),
        None,
    )
    eq_addon = Decimal(eq_row["flat_addon_annual"]) if eq_row else Decimal("0.00")

    # 4. Composition + end-of-period quantization (Pitfall 6 — single
    # quantize call at the predicate boundary).
    return quantize_cents(base * multiplier + eq_addon)
