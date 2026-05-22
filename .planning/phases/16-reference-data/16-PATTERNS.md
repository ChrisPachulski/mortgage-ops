# Phase 16: Reference Data - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 8 new + 1 modified (`lib/property_analysis.py`) + 3 fixture JSONs (modified)
**Analogs found:** 8 / 8 (every Phase 16 deliverable maps cleanly to a Phase 2 in-repo analog)

## CONTEXT corrections propagated to PATTERNS

The pattern assignments below honor three RESEARCH-verified corrections to CONTEXT (do NOT re-introduce these inaccuracies during planning):

1. **No `flood_zone` field on PropertyListing** (CONTEXT D-16-WIRE-01 incorrectly says it exists). `lib/rules/insurance.py:lookup_default(state, flood_zone)` accepts `flood_zone: str | None`; the call site at `lib/property_analysis.py:703-705` ALWAYS passes `None` in v1.1. The `flood_zone_multipliers` block in the insurance YAML is forward-compatible scaffolding; only the `"unknown"` row fires from Phase 14 in v1.1.
2. **`_unwrap_provenanced` returns `Decimal("0.00")` not `None`** (CONTEXT D-16-WIRE-01 incorrectly says it returns None). The fallback trigger must branch on `listing.insurance_estimate_annual is None or listing.insurance_estimate_annual.value is None` BEFORE calling `_unwrap_provenanced`. Do not branch on `monthly_insurance == Decimal("0.00")` (false fires on legitimate $0 listings).
3. **`_ALLOWED_REASONS` does NOT exist as a Python constant** (CONTEXT D-16-WIRE-03 misidentifies `lib/property_analysis.py:296` — that line is inside a docstring). The actual "allow-list" surface is the substring-match aggregator at **line 1505** (`if any("PMI-RATE-ESTIMATED" in r ...)`) plus literal-string assertions in `tests/test_property_analysis.py` (7 hit sites) and 3 fixture JSON files. Plan tasks edit those surfaces, NOT a phantom constant.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `data/reference/property-analysis-heuristics.yml` | reference-YAML | static-lookup (range buckets) | `data/reference/fha-mip-rates.yml` | exact |
| `data/reference/insurance-estimate-defaults.yml` | reference-YAML (multi-section) | static-lookup (3 sections: exact-match + multiplier + flat-add) | `data/reference/va-funding-fees.yml` | exact (multi-section structure) |
| `lib/rules/pmi.py` | lib-rules-module | YAML-read → range-match → return Pydantic | `lib/rules/fha_mip.py` | exact (range-lookup pattern) |
| `lib/rules/insurance.py` | lib-rules-module | YAML-read → exact-match + composition → return Money | `lib/rules/fha_mip.py` (skeleton) + `lib/rules/va_funding_fee.py` (multi-section consumer) | role-match (no in-repo composer with state lookup; FHA MIP is the closest range-lookup analog) |
| `tests/test_rules/test_pmi.py` | unit-test | fixture-JSON-driven assertions | `tests/test_rules/test_fha_mip.py` | exact |
| `tests/test_rules/test_insurance.py` | unit-test | fixture-JSON-driven assertions + composition checks | `tests/test_rules/test_fha_mip.py` | exact |
| `tests/fixtures/rules/pmi_*.json` (≥5) | hand-calc-fixture | static JSON with citation + inputs + expected outputs | `tests/fixtures/rules/fha_mip_term30_ltv95_post_2023.json` | exact |
| `tests/fixtures/rules/insurance_*.json` (≥3) | hand-calc-fixture | static JSON with citation + inputs + expected outputs | `tests/fixtures/rules/fha_mip_term30_ltv85_post_2023.json` | exact |
| `lib/property_analysis.py` (modify L21-23, L151, L653-654, L703-705, L1505) | lib-edits | swap inline constant → YAML-driven call + add fallback branch | `lib/property_analysis.py:666-672` (existing `fha_mip_compute` call site shows the wire-in pattern) | exact (mirror existing FHA wire-in) |

## Boundary Convention Divergence (CRITICAL — RESEARCH Pitfall 10)

**FHA MIP** (`lib/rules/fha_mip.py:155-160`) special-cases the lowest LTV bucket — `ltv_min == Decimal("0.00")` is treated INCLUSIVE-on-both-ends. This is the BL-03 fix (low-LTV catch-all added when FHA loans below 78% LTV previously raised LookupError).

```python
# Source: lib/rules/fha_mip.py L155-160
if ltv_min == Decimal("0.00"):
    if not (ltv <= ltv_max):
        continue
else:
    if not (ltv_min < ltv <= ltv_max):
        continue
```

**PMI MUST INVERT THIS**: every PMI bucket is EXCLUSIVE-LOWER / INCLUSIVE-UPPER, with NO `ltv_min == 0.00` branch. Reason: Phase 14's strict trigger at `lib/property_analysis.py:652` reads `provisional_ltv > Decimal("0.80")` — a loan at LTV exactly 0.80 does NOT trigger PMI, so the PMI table's first row (`ltv_min=0.80, ltv_max=0.85`) must cover `0.80 < ltv <= 0.85`. The `pmi.py:lookup_rate` helper drops the `if ltv_min == Decimal("0.00")` branch entirely. Out-of-band cases (including `ltv <= 0.80`) fall through to the capped-fallback per D-16-PMI-02.

```python
# pmi.py lookup helper — STRICT exclusive-lower / inclusive-upper for ALL buckets
ltv_min = Decimal(row["ltv_min"])
ltv_max = Decimal(row["ltv_max"])
# No ltv_min == 0.00 branch — PMI table has no zero-bucket row.
if fico_min <= fico <= fico_max and ltv_min < ltv <= ltv_max:
    return PMILookupResult(...)
```

Document this divergence in `lib/rules/pmi.py` module docstring AND in the YAML header notes block.

## Pattern Assignments

### `data/reference/property-analysis-heuristics.yml` (reference-YAML, static-lookup)

**Analog:** `data/reference/fha-mip-rates.yml`

**Required headers** (lines 1-3 of analog):
```yaml
# data/reference/property-analysis-heuristics.yml
source: "<MGIC Rate Card 'Standard MI' BPMI bulletin URL — planner pins exact PDF + revision>"
effective: 2026-XX-XX  # UNQUOTED YAML date — _loader.py:80-85 rejects quoted strings
notes: |
  <multi-line block with: rationale, schema description, boundary convention,
  refresh discipline, staleness-warning expectation>
```

**Top-level keys** (mirror `fha-mip-rates.yml` structure):
- `source:` (quoted str) — single bulletin URL
- `effective:` (UNQUOTED YAML date) — bulletin publication date
- `notes:` (`|` block) — narrative + schema + boundary doc
- `pmi_annual_rate_table:` (list of 16 row dicts) — primary lookup surface
- `pmi_capped_fallback:` (single dict) — worst-cell rate for out-of-band combos per D-16-PMI-02

**Row shape** (mirrors `fha-mip-rates.yml:22-27` row shape, every numeric quoted per Pitfall 1):
```yaml
pmi_annual_rate_table:
  - {fico_min: "760", fico_max: "850", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "<TODO>", fico_band_label: "760+", ltv_band_label: "80-85"}
  # ... 15 more rows ...

pmi_capped_fallback:
  fico_band_label: "700-719"
  ltv_band_label: "95-97"
  annual_rate: "<TODO matches the worst row above>"
```

**Quoted-Decimal rule** (CLAUDE.md money discipline + Phase 2 Pitfall 1):
- Every numeric scalar MUST be a quoted string (`"0.0050"`, `"760"`, `"0.80"`).
- `effective:` is the SOLE unquoted scalar (must remain `datetime.date` for `_check_staleness`).
- Consumers wrap in `Decimal(str)` at boundary (see `lib/rules/fha_mip.py:153` for the pattern).

---

### `data/reference/insurance-estimate-defaults.yml` (reference-YAML, multi-section)

**Analog:** `data/reference/va-funding-fees.yml` (the only existing multi-section YAML in the repo — verified Sources)

**Top-level structure** mirrors VA's 3-section layout (`purchase`, `flat_fees`, `exemption` per `va-funding-fees.yml:32-46`):
```yaml
# data/reference/insurance-estimate-defaults.yml
source: "<NAIC report URL OR composite-source statement>"
effective: 2025-05-21  # NAIC 2022-data report publication date — will fire StaleReferenceWarning (CORRECT per Phase 2 D-12 precedent)
notes: |
  Three independent lookup surfaces in one file:
    1. state_base_annual_premium: 51 rows (50 states + DC)
    2. flood_zone_multipliers: 4 rows (X, A/AE, V, unknown) — MULTIPLICATIVE
    3. earthquake_state_addons: 3 rows (CA, OR, WA) — ADDITIVE flat $

  Composition: annual = state_base * flood_zone_multiplier + earthquake_addon
  Quantization happens at the predicate boundary (quantize_cents end-of-period).

  IMPORTANT (Pitfall 5): NAIC's 2022-data report (published 2025-05-21)
  EXCLUDES California and Texas (separate submission channel). Use III or
  state-DOI averages for CA + TX; document per-row source mix in row `notes:`.

  IMPORTANT (Pitfall 6): FEMA Risk Rating 2.0 (effective 2021-04-01) decoupled
  NFIP premium from FIRM zone. The multipliers below are a private-market
  homeowners-policy uplift heuristic, NOT a citable FEMA NFIP rate.

  IMPORTANT (Pitfall 7): CEA publishes earthquake premium per $1000 coverage,
  not as a flat $. The flat values below approximate a $500-700k home;
  high-value or low-value homes will be systematically mispriced. v1.1 design
  tradeoff (CONTEXT D-16-INS-03).

  IMPORTANT (Pitfall 3): PropertyListing has NO flood_zone field as of v1.1;
  the call site at lib/property_analysis.py always passes flood_zone=None,
  so only the "unknown" row in flood_zone_multipliers ever fires. The X/A/AE/V
  rows are forward-compatible scaffolding for v1.2.

state_base_annual_premium:
  - {state: "AL", base_annual: "<TODO>", notes: "NAIC 2022"}
  # ... 49 NAIC rows + 2 III rows for CA, TX ...

flood_zone_multipliers:
  - {zone: "X",       multiplier: "1.00", notes: "Minimal risk; no uplift"}
  - {zone: "A",       multiplier: "1.30", notes: "100-year floodplain"}
  - {zone: "AE",      multiplier: "1.30", notes: "100-year floodplain w/ BFE"}
  - {zone: "V",       multiplier: "1.80", notes: "Coastal high-velocity zone"}
  - {zone: "unknown", multiplier: "1.15", notes: "Missing data default (v1.1 default — always fires)"}

earthquake_state_addons:
  - {state: "CA", flat_addon_annual: "<TODO>", notes: "CEA + private market avg @ ~$500-700k coverage baseline"}
  - {state: "OR", flat_addon_annual: "<TODO>", notes: "Cascadia subduction zone; non-CEA private market"}
  - {state: "WA", flat_addon_annual: "<TODO>", notes: "Cascadia subduction zone; non-CEA private market"}
```

**Quoted-Decimal rule:** every numeric quoted; `effective:` unquoted YAML date.

---

### `lib/rules/pmi.py` (lib-rules-module, YAML-read → range-match → Pydantic)

**Analog:** `lib/rules/fha_mip.py` (verbatim template — citation-coverage meta-test enforces this shape)

**Docstring header** (REQUIRED by `tests/test_rules/test_citation_coverage.py:28-39` — must contain `Citation:`, `Source URL:`, `Effective:`, and at least one `http(s)://` URL):

```python
"""Conventional PMI annual rate lookup (4x4 LTV x FICO MGIC abridged schedule).

Citation: MGIC Rate Card "Standard MI" (Borrower-Paid Monthly Premium) —
  industry-published rate schedule, NOT a regulatory predicate. Phase 16
  ships an abridged 4x4 subset (16 cells); the full MGIC 8x7 schedule is
  deferred to v2 per CONTEXT D-16-PMI-01. Out-of-band combos return the
  worst-cell rate per D-16-PMI-02 (no raise, no interpolation).
Source URL: https://www.mgic.com/rates/rate-cards
  [BULLETIN-SPECIFIC URL: planner pins exact PDF + revision number;
   landing page is not stable across MGIC site refactors.]
Effective: <planner pins to bulletin publication date>

What this predicate decides:
  Given a representative FICO score and an LTV ratio at origination,
  return the annual PMI rate (Decimal) + a reason tag for the
  eligible_reasons soft-signal surface.

  In-band: tag = "PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}"
  Out-of-band: cap at worst cell,
    tag = "PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}"

  Bucket convention: ALL buckets are EXCLUSIVE-LOWER / INCLUSIVE-UPPER.
  No ltv_min == 0.00 special-case (unlike fha_mip.py). LTV exactly 0.80 is
  OUT-of-band (consistent with Phase 14 trigger `provisional_ltv > 0.80`
  at lib/property_analysis.py:652) and hits the capped fallback.

Inputs:
    fico: int (300..850; lib/household.py L61 constrains)
    ltv: Decimal (financed_principal / appraised_value at origination)

Outputs:
    PMILookupResult — frozen Pydantic:
        annual_rate: Rate
        reason_tag: str
"""
```

**Imports + class** (mirror `fha_mip.py:48-72`):
```python
from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from lib.models import Rate
from lib.rules._loader import load_reference


class PMILookupResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    annual_rate: Rate
    reason_tag: str
```

**Range-lookup core pattern** (mirror `fha_mip.py:132-167`):
```python
def lookup_rate(fico: int, ltv: Decimal) -> PMILookupResult:
    ref = load_reference("property-analysis-heuristics")
    for row in ref["pmi_annual_rate_table"]:
        fico_min = int(row["fico_min"])
        fico_max = int(row["fico_max"])
        ltv_min = Decimal(row["ltv_min"])
        ltv_max = Decimal(row["ltv_max"])
        # EXCLUSIVE-LOWER / INCLUSIVE-UPPER for all buckets (NO 0.00 branch).
        if fico_min <= fico <= fico_max and ltv_min < ltv <= ltv_max:
            return PMILookupResult(
                annual_rate=Decimal(row["annual_rate"]),
                reason_tag=(
                    f"PMI-RATE-ESTIMATED-MGIC-"
                    f"{row['ltv_band_label']}-{row['fico_band_label']}"
                ),
            )
    # D-16-PMI-02: cap at worst row (FICO 700-719 x LTV 95.01-97).
    worst = ref["pmi_capped_fallback"]
    return PMILookupResult(
        annual_rate=Decimal(worst["annual_rate"]),
        reason_tag=f"PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}",
    )
```

**Error handling:** No raise on out-of-band — fallback always returns. (Distinct from `fha_mip.py:164-167` which raises LookupError.) If `pmi_capped_fallback` key is missing, the implicit `KeyError` is the schema-gap signal (acceptable; the citation-coverage meta-test will fail on YAML schema drift).

---

### `lib/rules/insurance.py` (lib-rules-module, multi-section composition)

**Analog:** `lib/rules/fha_mip.py` (docstring skeleton + Pydantic discipline) + multi-section consumer pattern (only `fha_mip.py` consumes its YAML's `annual_mip_table` AND `termination` sections — `insurance.py` extends this to 3 sections)

**Docstring header** (citation-coverage meta-test gate):
```python
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
  CONTEXT D-16-INS-04.

Source URL: https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022
  (additional URLs documented in YAML notes block)
Effective: 2025-05-21 (NAIC report publication date)

What this predicate decides:
  Given a USPS state code and an optional FEMA flood zone, return the
  estimated annual homeowners insurance premium (Money). Composition:
    annual = state_base * flood_zone_multiplier + earthquake_state_addon

  For state not in {CA, OR, WA}, earthquake_addon = Decimal("0.00") silently.
  For flood_zone not in {X, A, AE, V} (including None), use "unknown" row.
  In v1.1 the caller (lib/property_analysis.py) always passes flood_zone=None
  because PropertyListing has no flood_zone field (Pitfall 3) — only the
  "unknown" multiplier row ever fires in v1.1.

Inputs:
    state: str (2-char USPS code; use fips_to_usps() to convert household.state_fips)
    flood_zone: str | None (FEMA FIRM zone; None always in v1.1)

Outputs:
    Money (Decimal; annual premium, quantize_cents-applied at boundary)
"""
```

**Imports + constants** (FIPS→USPS dict per CONTEXT D-16-FILE-02):
```python
from __future__ import annotations
from decimal import Decimal
from typing import Final
from lib.models import Money
from lib.money import quantize_cents
from lib.rules._loader import load_reference

# Census Bureau immutable metadata; no refresh cadence; constant dict per
# CONTEXT D-16-FILE-02 ("small constant dict in lib/rules/insurance.py").
_FIPS_TO_USPS: Final[dict[str, str]] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY",
}


def fips_to_usps(state_fips: str) -> str:
    """Lookup USPS code from 2-digit FIPS. Raises KeyError on unknown FIPS."""
    if state_fips not in _FIPS_TO_USPS:
        raise KeyError(
            f"Unknown state FIPS {state_fips!r}; expected one of "
            f"{sorted(_FIPS_TO_USPS)!r}"
        )
    return _FIPS_TO_USPS[state_fips]
```

**Core composition pattern:**
```python
def lookup_default(state: str, flood_zone: str | None) -> Money:
    ref = load_reference("insurance-estimate-defaults")

    # 1. State base (exact-match USPS lookup)
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

    # 2. Flood multiplier (exact-match zone; default to "unknown" row)
    zone_key = flood_zone if flood_zone in {"X", "A", "AE", "V"} else "unknown"
    mult_row = next(
        (r for r in ref["flood_zone_multipliers"] if r["zone"] == zone_key),
        None,
    )
    multiplier = Decimal(mult_row["multiplier"]) if mult_row else Decimal("1.00")

    # 3. Earthquake add-on (CA/OR/WA only; silent 0 otherwise per CONTEXT)
    eq_row = next(
        (r for r in ref["earthquake_state_addons"] if r["state"] == state),
        None,
    )
    eq_addon = Decimal(eq_row["flat_addon_annual"]) if eq_row else Decimal("0.00")

    # 4. Composition + end-of-period quantization (Pitfall 6 — single quantize)
    return quantize_cents(base * multiplier + eq_addon)
```

**Error handling:**
- Missing state row → `LookupError` (loud; YAML schema gap; the YAML must cover all 51 USPS codes).
- Missing flood row → defensive `Decimal("1.00")` fallback (YAML drift safety; never silently scales by wrong factor).
- Missing earthquake row → silent `Decimal("0.00")` (CORRECT per CONTEXT D-16-INS-03; non-CA/OR/WA states never get tagged).

---

### `tests/test_rules/test_pmi.py` (unit-test, fixture-JSON-driven)

**Analog:** `tests/test_rules/test_fha_mip.py` (verbatim template)

**Imports + fixture loader** (mirror `test_fha_mip.py:20-38`):
```python
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.rules.pmi import PMILookupResult, lookup_rate

FIX: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIX / name).read_text())
    return data
```

**Per-fixture test pattern** (mirror `test_fha_mip.py:51-65`):
```python
def test_pmi_lookup_in_band_760_95() -> None:
    # Hand: FICO=760, LTV=Decimal("0.95") -> row [FICO 760+ x LTV 90-95] -> rate=<YAML value>
    # Reason tag: "PMI-RATE-ESTIMATED-MGIC-90-95-760+"
    fx = _fx("pmi_in_band_760_95.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert isinstance(result, PMILookupResult)
    assert result.annual_rate == Decimal(fx["expected_annual_rate"])
    assert result.reason_tag == fx["expected_reason_tag"]


def test_pmi_lookup_out_of_band_caps_low_fico() -> None:
    # Hand: FICO=680, LTV=0.96 -> no in-band row -> capped at worst cell.
    # Reason tag: "PMI-RATE-CAPPED-MGIC-ABRIDGED-680-0.96"
    fx = _fx("pmi_capped_low_fico_680_96.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert result.annual_rate == Decimal(fx["expected_annual_rate"])
    assert result.reason_tag == fx["expected_reason_tag"]


def test_pmi_lookup_ltv_exactly_080_caps() -> None:
    # Boundary convention: LTV exactly 0.80 is OUT-of-band (Pitfall 10).
    # Phase 14 trigger uses `> 0.80`; PMI table starts at `ltv_min < ltv <= ltv_max`
    # with ltv_min=0.80 EXCLUSIVE, so LTV=0.80 hits the cap fallback.
    fx = _fx("pmi_boundary_ltv_080_caps.json")
    result = lookup_rate(fico=fx["fico"], ltv=Decimal(fx["ltv"]))
    assert result.reason_tag.startswith("PMI-RATE-CAPPED-MGIC-ABRIDGED-")
```

**Minimum 5 fixtures per RESEARCH Open Q5:**
- `pmi_in_band_corner_high_quality_760_80.json` (FICO 760+ × LTV 80-85)
- `pmi_in_band_corner_low_quality_700_95.json` (FICO 700-719 × LTV 95-97)
- `pmi_in_band_middle_740_90.json` (FICO 740-759 × LTV 90-95 — Pachulski-baseline)
- `pmi_capped_low_fico_680_96.json` (out-of-band, hits cap)
- `pmi_capped_boundary_ltv_080.json` (LTV exactly 0.80 — boundary convention guard)

---

### `tests/test_rules/test_insurance.py` (unit-test, fixture-JSON-driven)

**Analog:** `tests/test_rules/test_fha_mip.py` (verbatim shape)

**Test surface:**
```python
def test_insurance_lookup_state_base_wa() -> None:
    # Hand: WA state -> NAIC 2022 base = $<YAML value>
    # No flood zone (v1.1 always None) -> "unknown" multiplier (1.15)
    # WA in earthquake list -> add-on = $<YAML value>
    # Composition: base * 1.15 + eq_addon
    fx = _fx("insurance_wa_no_flood.json")
    result = lookup_default(state=fx["state"], flood_zone=fx.get("flood_zone"))
    assert result == Decimal(fx["expected_annual"])


def test_insurance_earthquake_silent_zero_for_non_quake_state() -> None:
    # Hand: TX state -> NAIC base, "unknown" multiplier, NO earthquake row -> +$0
    # Critical: NO reason-tag fires; result is just the base * multiplier.
    fx = _fx("insurance_tx_no_quake.json")
    result = lookup_default(state=fx["state"], flood_zone=None)
    assert result == Decimal(fx["expected_annual"])


def test_fips_to_usps_known_code() -> None:
    from lib.rules.insurance import fips_to_usps
    assert fips_to_usps("53") == "WA"
    assert fips_to_usps("06") == "CA"


def test_fips_to_usps_unknown_raises() -> None:
    from lib.rules.insurance import fips_to_usps
    with pytest.raises(KeyError, match="Unknown state FIPS"):
        fips_to_usps("99")
```

**Minimum 3 fixtures per RESEARCH Wave 0:**
- `insurance_wa_no_flood.json` (Pachulski baseline — WA + None flood_zone + earthquake add-on)
- `insurance_ca_zone_ae.json` (high-flood high-quake — CA + AE zone + earthquake add-on; tests forward-compat path)
- `insurance_tx_no_quake.json` (non-quake state, missing flood data — TX + None + no earthquake)

---

### `tests/fixtures/rules/pmi_*.json` and `insurance_*.json` (hand-calc-fixture)

**Analog:** `tests/fixtures/rules/fha_mip_term30_ltv95_post_2023.json` (verbatim shape)

**Fixture JSON shape** (mirror analog 1:1):
```json
{
  "citation": "MGIC Rate Card 'Standard MI' BPMI <bulletin id>, row FICO 760+ x LTV 80.01-85",
  "source_url": "https://www.mgic.com/rates/rate-cards/<bulletin-pdf>",
  "comment": "Hand-calc: fico=760, ltv=Decimal('0.83') -> row [fico_min=760, fico_max=850, ltv_min=0.80, ltv_max=0.85] -> annual_rate=<YAML value>. Reason tag: PMI-RATE-ESTIMATED-MGIC-80-85-760+.",
  "fico": 760,
  "ltv": "0.83",
  "expected_annual_rate": "0.0050",
  "expected_reason_tag": "PMI-RATE-ESTIMATED-MGIC-80-85-760+"
}
```

**Required fields per fixture** (citation-coverage meta-test will glob `pmi_*.json` and `insurance_*.json` matching the predicate stem):
- `citation` (str) — specific table cell / row identifier
- `source_url` (str) — pinned bulletin/report URL
- `comment` (str) — hand-calc derivation showing inputs → expected output
- input fields (`fico`, `ltv` as string; `state`, `flood_zone` for insurance)
- `expected_*` fields (Decimal-as-string for money/rate; literal strings for reason tags)

**Citation-coverage gate** (`tests/test_rules/test_citation_coverage.py:42-48`):
```python
@pytest.mark.parametrize("path", _predicate_modules(), ids=lambda p: p.stem)
def test_predicate_has_at_least_one_fixture(path: Path) -> None:
    matches = list(FIX_DIR.glob(f"{path.stem}_*.json"))
    assert len(matches) >= 1, (...)
```
→ Every `lib/rules/*.py` (including new `pmi.py` and `insurance.py`) gets auto-discovered; the meta-test fails until at least one fixture matching `pmi_*.json` and at least one matching `insurance_*.json` exists.

---

### `lib/property_analysis.py` (lib-edits — 5 surgical edit sites)

**Edit Site 1: L21-23 (docstring)**
**Action:** Remove the Pitfall 1 reference to `_CONV_PMI_ANNUAL_RATE`. Replace with reference to `lib.rules.pmi.lookup_rate`.

Current (per RESEARCH-verified file read 2026-05-22):
```python
# L20-23
Pitfalls mitigated in this plan (RESEARCH.md §"Pitfalls"):
  - Pitfall 1 — conventional PMI estimate sourced from
    ``_CONV_PMI_ANNUAL_RATE`` Final constant (0.0075 / 75bps annual). Cells
    with LTV > 0.80 tag ``eligible_reasons`` with "PMI-RATE-ESTIMATED-0.0075".
```

Replace with:
```python
  - Pitfall 1 — conventional PMI rate sourced from
    ``lib.rules.pmi.lookup_rate(fico, ltv)`` (YAML-driven 4x4 MGIC abridged
    schedule). Cells with LTV > 0.80 tag ``eligible_reasons`` with either
    "PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}" (in-band) or
    "PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}" (out-of-band capped fallback).
```

**Edit Site 2: L151-159 (the Final constant)**
**Action:** REMOVE the `_CONV_PMI_ANNUAL_RATE: Final[Decimal] = Decimal("0.0075")` constant AND its docstring entirely.

**Edit Site 3: L653-654 (PMI computation site)**
Current:
```python
if provisional_ltv > Decimal("0.80"):
    monthly_mi = quantize_cents(base_loan_amount * _CONV_PMI_ANNUAL_RATE / Decimal("12"))
    eligible_reasons.append("PMI-RATE-ESTIMATED-0.0075")
```

Replace with (mirror Example 3 from RESEARCH):
```python
if provisional_ltv > Decimal("0.80"):
    from lib.rules.pmi import lookup_rate as pmi_lookup_rate  # at module top, recommended
    pmi_result = pmi_lookup_rate(household.fico, provisional_ltv)
    monthly_mi = quantize_cents(
        base_loan_amount * pmi_result.annual_rate / Decimal("12")
    )
    eligible_reasons.append(pmi_result.reason_tag)
```

**Edit Site 4: L703-705 (insurance computation site) — CRITICAL: honor RESEARCH correction #2**

DO NOT branch on `_unwrap_provenanced(...) is None` — that helper returns `Decimal("0.00")`, never `None` (verified `lib/property_analysis.py:497-507`).

Current:
```python
monthly_insurance = quantize_cents(
    _unwrap_provenanced(listing.insurance_estimate_annual) / Decimal("12")
)
```

Replace with (mirror Example 4 from RESEARCH):
```python
pm = listing.insurance_estimate_annual
if pm is not None and pm.value is not None:
    annual_insurance = pm.value
else:
    from lib.rules.insurance import lookup_default, fips_to_usps
    state_usps = fips_to_usps(household.state_fips)
    # Pitfall 3: PropertyListing has NO flood_zone field in v1.1. Always pass None.
    # Only the "unknown" multiplier row in flood_zone_multipliers ever fires here.
    annual_insurance = lookup_default(state_usps, flood_zone=None)
    eligible_reasons.append(
        f"INSURANCE-ESTIMATED-NAIC-{state_usps}-unknown"
    )
monthly_insurance = quantize_cents(annual_insurance / Decimal("12"))
```

**Edit Site 5: L1505 (substring aggregator — NOT a constant per RESEARCH correction #3)**

Current (verified L1504-1506):
```python
# Surface PMI-RATE-ESTIMATED whenever any cell carried the placeholder.
if any("PMI-RATE-ESTIMATED" in r for c in matrix.cells for r in c.eligible_reasons):
    warnings.append("PMI-RATE-ESTIMATED")
```

Replace with (mirror Example 5 from RESEARCH — add a Final constant for grep-discoverability):
```python
# Top-level warning surfacing: any cell that carried a soft-signal reason
# matching one of these prefixes contributes a single deduped warning string.
# Recommend defining this constant near other module-level _STRESS_*_CODE
# constants (~line 249-251) for grep-discoverability.
_REPORT_WARNING_PREFIXES: Final[dict[str, str]] = {
    "PMI-RATE-ESTIMATED-MGIC": "PMI-RATE-ESTIMATED-MGIC",
    "PMI-RATE-CAPPED-MGIC": "PMI-RATE-CAPPED-MGIC",
    "INSURANCE-ESTIMATED-NAIC": "INSURANCE-ESTIMATED-NAIC",
}

# (Inside analyze(), replacing the existing L1504-1506 block:)
for prefix, warning_label in _REPORT_WARNING_PREFIXES.items():
    if any(prefix in r for c in matrix.cells for r in c.eligible_reasons):
        warnings.append(warning_label)
```

**Edit Site 6: Reason-tag literal references in 3 fixture JSONs** (RESEARCH Pitfall 8 + Runtime State Inventory)

Files (per RESEARCH grep 2026-05-22):
- `tests/fixtures/property_analysis/condo_with_hoa_seattle.json` — 4 occurrences (notes L6, _meta citation L8, eligible_reasons L80 and L96 — all carry literal `"PMI-RATE-ESTIMATED-0.0075"`)
- `tests/fixtures/property_analysis/sfh_conforming_king_county.json` — 1 occurrence (warnings array L130 carries `"PMI-RATE-ESTIMATED"` substring — leave UNCHANGED because top-level warning string changes to `"PMI-RATE-ESTIMATED-MGIC"`)
- `tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` — 1 occurrence (warnings array L142 — same as above)

**Action per fixture:**
- `condo_with_hoa_seattle.json`: re-anchor with hand-calc using the new YAML's MGIC rate; replace literal `"PMI-RATE-ESTIMATED-0.0075"` strings with the new parameterized tag (e.g., `"PMI-RATE-ESTIMATED-MGIC-90-95-740"`); note that downstream PITI/DTI values change — full re-anchoring required, NOT just string find/replace.
- `sfh_conforming_king_county.json`: update the `"warnings"` array entry from `"PMI-RATE-ESTIMATED"` to `"PMI-RATE-ESTIMATED-MGIC"` (matching the new aggregator label).
- `sfh_jumbo_bay_area.json`: same as above.

**Edit Site 7: `tests/test_property_analysis.py` assertions** (RESEARCH Pitfall 8)

Per RESEARCH grep, 7 hit sites at lines 481, 1101-1102, 1116, 1120, 1299, 1319, 1326 use `assert "PMI-RATE-ESTIMATED-0.0075" in cell.eligible_reasons` style. Rewrite each to substring/prefix match:
```python
# Before:
assert "PMI-RATE-ESTIMATED-0.0075" in cell.eligible_reasons
# After:
assert any(r.startswith("PMI-RATE-ESTIMATED-MGIC-") for r in cell.eligible_reasons)
```

---

## Shared Patterns

### Loader entry point
**Source:** `lib/rules/_loader.py:46-87` (`load_reference(name)`)
**Apply to:** Both new `lib/rules/pmi.py` and `lib/rules/insurance.py`

```python
# Source: lib/rules/fha_mip.py:91 — the canonical call shape
ref = load_reference("property-analysis-heuristics")  # filename stem; no .yml
# ref is dict[str, Any] — top-level keys per YAML; numeric values are quoted strings
# requiring Decimal(str) boundary coercion.
```

Return shape:
- `dict[str, Any]` with `source: str`, `effective: datetime.date`, plus all top-level keys from the YAML (e.g., `pmi_annual_rate_table: list[dict]`, `state_base_annual_premium: list[dict]`, etc.).
- The loader is `lru_cache(maxsize=None)`-decorated; multiple lookups within a process share parsed YAML.
- The loader runs `_check_staleness` on first call → fires `StaleReferenceWarning` if `effective` is > 12 months old (CORRECT behavior for NAIC 2022 report; expected to fire — see RESEARCH Pitfall 5).
- Filename regex `^[a-z0-9][a-z0-9-]*$` per `_loader.py:31` — new YAML stems `property-analysis-heuristics` and `insurance-estimate-defaults` both comply.

### Pydantic output discipline
**Source:** `lib/rules/fha_mip.py:65-72` (MIPResult)
**Apply to:** `lib/rules/pmi.py:PMILookupResult` (already specified above)

```python
class PMILookupResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    annual_rate: Rate
    reason_tag: str
```

- `strict=True` — rejects float-to-Decimal coercion at boundary
- `frozen=True` — immutable after construction
- `extra="forbid"` — schema gaps surface as Pydantic ValidationError, not silent attribute drops

`lib/rules/insurance.py:lookup_default` returns raw `Money` (Decimal alias from `lib.models`), NOT a wrapper class — no result wrapper needed when output is a single scalar.

### Money discipline at YAML boundary
**Source:** `lib/rules/fha_mip.py:94, 153-154, 163` (Decimal-from-string at every YAML scalar consumption)
**Apply to:** Every `Decimal(...)` call in `lib/rules/pmi.py` and `lib/rules/insurance.py`

```python
ufmip_rate = Decimal(ref["ufmip_rate"])           # YAML scalar is "0.0175" str
ltv_min = Decimal(row["ltv_min"])                 # YAML scalar is "0.80" str
return Decimal(row["annual_mip_rate"])            # YAML scalar is "0.0055" str
```

Never `Decimal(float_value)`; never compare float and Decimal; quantize ONLY at end-of-period via `quantize_cents` (`lib/money.py`). The `quantize_cents(base * multiplier + eq_addon)` call in `insurance.py:lookup_default` is the ONLY quantization in the predicate path — Phase 14's call site divides by 12 + re-quantizes for monthly display, mirroring the FHA MIP wire-in convention at `lib/property_analysis.py:672`.

### Citation-coverage meta-test contract
**Source:** `tests/test_rules/test_citation_coverage.py:28-48`
**Apply to:** Both new predicate modules and at least one fixture per predicate

Two parametrized tests auto-discover any new `lib/rules/*.py`:
1. `test_predicate_has_citation_in_docstring[<stem>]` — requires `Citation:`, `Source URL:`, `Effective:`, and at least one `http(s)://` URL in the module docstring.
2. `test_predicate_has_at_least_one_fixture[<stem>]` — requires at least one `<stem>_*.json` in `tests/fixtures/rules/`.

Plan tasks MUST satisfy both BEFORE the meta-test runs (it's a pre-existing gate that turns red on any new predicate lacking these artifacts).

### Reason-tag emission discipline
**Source:** `lib/property_analysis.py:654, 687` (existing tag-append pattern at the PMI + VA wire-in)
**Apply to:** Both new wire-in sites (PMI block L653-654, insurance fallback L703-705)

Pattern: `eligible_reasons.append("<TAG-LITERAL>")` immediately adjacent to the rate-application line. Tags surface in `report.warnings` via the substring aggregator at L1505 (which Phase 16 extends).

Test-side: `assert any(r.startswith("<PREFIX>-") for r in cell.eligible_reasons)` (substring/prefix match, NEVER exact-string equality — Pitfall 8).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All 8 Phase 16 deliverables have direct in-repo analogs (`fha_mip.py`, `fha-mip-rates.yml`, `va-funding-fees.yml`, `test_fha_mip.py`, `fha_mip_*.json`). No greenfield patterns. |

## Metadata

**Analog search scope:** `lib/rules/*.py`, `data/reference/*.yml`, `tests/test_rules/*.py`, `tests/fixtures/rules/*.json`, `lib/property_analysis.py` (target of edits)

**Files read (verbatim):**
- `lib/rules/fha_mip.py` (full file, 168 lines) — primary analog for both new predicate modules
- `lib/rules/_loader.py` (full file, 102 lines) — loader contract + return shape
- `data/reference/fha-mip-rates.yml` (full file, 50 lines) — YAML schema + quoted-Decimal convention + range-bucket rows
- `data/reference/va-funding-fees.yml` (full file, 46 lines) — multi-section YAML precedent
- `tests/test_rules/test_fha_mip.py` (first 120 lines) — test shape + fixture loader pattern
- `tests/test_rules/test_citation_coverage.py` (full file, 49 lines) — meta-test contract
- `tests/fixtures/rules/fha_mip_term30_ltv95_post_2023.json` (full) — fixture JSON shape
- `tests/fixtures/rules/fha_mip_term30_ltv85_post_2023.json` (full) — second-fixture reference
- `lib/property_analysis.py` (5 targeted ranges: L1-50, L145-164, L485-507, L640-714, L1495-1514) — edit-site contexts

**Pattern extraction date:** 2026-05-22

## PATTERN MAPPING COMPLETE
