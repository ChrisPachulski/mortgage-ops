"""Tests for lib/rules/pmi.py — REF-09 (Phase 16 Wave 0).

Citation under test: Arch MI Borrower-Paid Monthly Non-Refundable Annualized
BPMI Rate Card (MCUS-B0283B-AMI, effective 2026-02-09); cross-verified
against Enact MI / Essent / National MI. Pinned to hand-calc anchored
fixtures under `tests/fixtures/rules/pmi_*.json`.

Vendor history: this fixture set originally pinned MGIC's "Standard MI"
BPMI rates (2024-03-04). MGIC's public BPMI PDF moved behind MiQ
authentication during 2025; the 2026-05-23 polish refresh re-pinned the
abridged 4x4 subset against Arch MI's currently-public rate card after
filed-rate convergence verified against Enact / Essent / National MI (0bps
drift across all 16 cells). The reason-tag literal `PMI-RATE-ESTIMATED-MGIC-*`
is preserved across the vendor switch for citation stability.

Coverage:
  - YAML metadata + 16-row table + capped-fallback row load via load_reference
  - In-band high-quality corner (FICO 760+ x LTV 80-85): annual_rate=0.0019
  - In-band middle (FICO 740-759 x LTV 90-95): annual_rate=0.0048 (Pachulski
    baseline; +13bps vs the prior 2024-03-04 pin)
  - In-band low-quality corner (FICO 700-719 x LTV 95-97): annual_rate=0.0079
    (rate coincides with capped-fallback but reason tag is the IN-band marker)
  - Out-of-band low FICO (680 x 0.96): cap at 0.0079, capped reason tag
  - Boundary LTV exactly 0.80: falls THROUGH to cap per RESEARCH Pitfall 10 /
    PATTERNS Boundary Convention Divergence (verifies the divergence from
    lib/rules/fha_mip.py's ltv_min == 0.00 special-case is enforced)
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from lib.rules.pmi import PMILookupResult, lookup_rate

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data


def test_yaml_loads_with_metadata() -> None:
    """property-analysis-heuristics.yml carries source/effective and the
    16-row table + capped-fallback row required by D-16-PMI-01/02."""
    from lib.rules._loader import load_reference

    ref = load_reference("property-analysis-heuristics")
    assert "source" in ref
    assert "effective" in ref
    assert "pmi_annual_rate_table" in ref
    assert len(ref["pmi_annual_rate_table"]) == 16
    assert "pmi_capped_fallback" in ref
    assert ref["pmi_capped_fallback"]["annual_rate"] == "0.0079"


def test_pmi_lookup_in_band_corner_high_quality_760_80() -> None:
    """High-quality corner: FICO 760+ x LTV 80-85 -> 0.0019."""
    fx = _fx("pmi_in_band_corner_high_quality_760_80.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert isinstance(result, PMILookupResult)
    assert result.annual_rate == Decimal(fx["expected_annual_rate"])
    assert result.reason_tag == fx["expected_reason_tag"]


def test_pmi_lookup_in_band_middle_740_90() -> None:
    """Pachulski-baseline middle case: FICO 740-759 x LTV 90-95 -> 0.0048."""
    fx = _fx("pmi_in_band_middle_740_90.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert isinstance(result, PMILookupResult)
    assert result.annual_rate == Decimal(fx["expected_annual_rate"])
    assert result.reason_tag == fx["expected_reason_tag"]


def test_pmi_lookup_in_band_corner_low_quality_700_95() -> None:
    """Low-quality in-band corner: FICO 700-719 x LTV 95-97 -> 0.0079.
    The annual_rate value coincides with pmi_capped_fallback.annual_rate,
    but the reason tag is the IN-band marker because (fico, ltv) IS inside
    the table — proves the reason-tag branching is keyed on the lookup
    path (in-band vs fallback), not on the rate value."""
    fx = _fx("pmi_in_band_corner_low_quality_700_95.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert result.annual_rate == Decimal(fx["expected_annual_rate"])
    assert result.reason_tag == fx["expected_reason_tag"]
    assert result.reason_tag.startswith("PMI-RATE-ESTIMATED-MGIC-")


def test_pmi_lookup_out_of_band_caps_low_fico_680_96() -> None:
    """FICO 680 is below the 700-719 floor -> capped fallback per D-16-PMI-02.
    No raise; the eligible_reasons tag carries the capped-suffix marker."""
    fx = _fx("pmi_capped_low_fico_680_96.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert result.annual_rate == Decimal(fx["expected_annual_rate"])
    assert result.reason_tag == fx["expected_reason_tag"]
    assert result.reason_tag.startswith("PMI-RATE-CAPPED-MGIC-ABRIDGED-")


def test_pmi_lookup_ltv_exactly_080_caps() -> None:
    """LTV exactly 0.80 is OUT-of-band per the EXCLUSIVE-LOWER boundary
    convention (RESEARCH Pitfall 10 / PATTERNS Boundary Convention Divergence).
    Verifies alignment with Phase 14 trigger `provisional_ltv > Decimal('0.80')`
    at lib/property_analysis.py:652 — a loan at LTV exactly 0.80 should NOT
    trigger PMI in the first place; if it ever does (via stale data path),
    the predicate falls through to cap rather than silently matching a row."""
    fx = _fx("pmi_capped_boundary_ltv_080.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert result.annual_rate == Decimal(fx["expected_annual_rate"])
    assert result.reason_tag == fx["expected_reason_tag"]
    assert result.reason_tag.startswith("PMI-RATE-CAPPED-MGIC-ABRIDGED-")


def test_pmi_lookup_result_is_frozen() -> None:
    """PMILookupResult must reject mutation post-construction (frozen=True)."""
    from pydantic import ValidationError

    result = lookup_rate(fico=760, ltv=Decimal("0.83"))
    try:
        result.annual_rate = Decimal("0.0099")  # type: ignore[misc]
    except ValidationError:
        return
    raise AssertionError("PMILookupResult should be frozen but mutation succeeded")


def test_pmi_lookup_reason_tag_pattern_for_inner_cell() -> None:
    """Spot-check that the 760+ x 90-95 cell emits the exact parameterized tag."""
    result = lookup_rate(fico=760, ltv=Decimal("0.95"))
    assert result.annual_rate == Decimal("0.0034")
    assert result.reason_tag == "PMI-RATE-ESTIMATED-MGIC-90-95-760+"
