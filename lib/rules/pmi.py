"""Conventional PMI annual rate lookup (4x4 LTV x FICO MGIC abridged schedule).

Citation: MGIC Rate Card "Standard MI" (Borrower-Paid Monthly Premium) —
  industry-published rate schedule, NOT a regulatory predicate. Phase 16
  ships an abridged 4x4 subset (16 cells); the full MGIC 8x7 schedule is
  deferred to v2 per CONTEXT D-16-PMI-01. Out-of-band combos return the
  worst-cell rate per D-16-PMI-02 (no raise, no interpolation).
Source URL: https://www.mgic.com/rates/rate-cards
  (additional bulletin form-number pinning lives in the YAML notes block)
Effective: 2024-03-04 (MGIC Rate Card "Standard MI" published bulletin date)

What this predicate decides:
  Given a representative FICO score and an LTV ratio at origination,
  return the annual PMI rate (Rate) + a reason tag for the
  eligible_reasons soft-signal surface.

  In-band: tag = "PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}"
  Out-of-band: cap at worst cell,
    tag = "PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}"

  Bucket convention: ALL buckets are EXCLUSIVE-LOWER / INCLUSIVE-UPPER.
  No ltv_min == 0.00 special-case (unlike lib/rules/fha_mip.py — see PATTERNS
  Boundary Convention Divergence). LTV exactly 0.80 is OUT-of-band (consistent
  with the Phase 14 trigger `provisional_ltv > Decimal("0.80")` at
  lib/property_analysis.py:652) and hits the capped fallback.

Worked example:
  >>> from decimal import Decimal
  >>> r = lookup_rate(fico=745, ltv=Decimal("0.92"))
  >>> r.annual_rate
  Decimal('0.0035')
  >>> r.reason_tag
  'PMI-RATE-ESTIMATED-MGIC-90-95-740-759'

Inputs:
    fico: int (300..850; lib/household.py constrains via Pydantic Field)
    ltv: Decimal (financed_principal / appraised_value at origination)

Outputs:
    PMILookupResult — frozen Pydantic:
        annual_rate: Rate (Decimal-from-string at YAML boundary)
        reason_tag: str (parameterized per CONTEXT D-16-PMI-03)
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from lib.models import Rate  # noqa: TC001  # Pydantic resolves annotations at runtime
from lib.rules._loader import load_reference


class PMILookupResult(BaseModel):
    """PMI lookup result. Frozen + strict per project Pydantic discipline."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    annual_rate: Rate
    reason_tag: str


def lookup_rate(fico: int, ltv: Decimal) -> PMILookupResult:
    """Look up the annual PMI rate for a (fico, ltv) pair against the MGIC
    abridged 4x4 schedule. Returns the in-band rate + per-cell reason tag when
    the inputs fall inside the table; returns the capped-fallback rate +
    capped-suffix reason tag when out-of-band (D-16-PMI-02).

    See module docstring for full behavior including the boundary convention.
    """
    ref = load_reference("property-analysis-heuristics")
    for row in ref["pmi_annual_rate_table"]:
        # WR-02 pattern: YAML scalars are quoted strings; coerce to int/Decimal
        # at the boundary (CLAUDE.md money discipline + Phase 2 Pitfall 1).
        fico_min = int(row["fico_min"])
        fico_max = int(row["fico_max"])
        ltv_min = Decimal(row["ltv_min"])
        ltv_max = Decimal(row["ltv_max"])
        # EXCLUSIVE-LOWER / INCLUSIVE-UPPER for ALL buckets — NO ltv_min == 0.00
        # special-case (RESEARCH Pitfall 10 / PATTERNS Boundary Convention
        # Divergence). LTV exactly 0.80 falls THROUGH to capped-fallback to
        # match Phase 14 trigger `provisional_ltv > Decimal("0.80")`.
        if fico_min <= fico <= fico_max and ltv_min < ltv <= ltv_max:
            return PMILookupResult(
                annual_rate=Decimal(row["annual_rate"]),
                reason_tag=(
                    f"PMI-RATE-ESTIMATED-MGIC-{row['ltv_band_label']}-{row['fico_band_label']}"
                ),
            )
    # D-16-PMI-02: out-of-band combos cap at worst-cell rate (no raise; the
    # eligible_reasons tag carries the capped-suffix marker for downstream
    # report aggregation). Out-of-band includes: FICO < 700, LTV > 0.97,
    # LTV <= 0.80 (boundary convention divergence from fha_mip.py).
    worst = ref["pmi_capped_fallback"]
    return PMILookupResult(
        annual_rate=Decimal(worst["annual_rate"]),
        reason_tag=f"PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}",
    )
