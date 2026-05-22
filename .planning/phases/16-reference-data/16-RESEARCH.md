# Phase 16: Reference Data - Research

**Researched:** 2026-05-22
**Domain:** Regulatory + actuarial reference data (PMI rate lookup; homeowners-insurance defaults with flood + earthquake overlays) + Phase 14 wire-in
**Confidence:** HIGH for in-repo patterns; MEDIUM for external data sources (NAIC / MGIC / CEA / private flood) — every external dollar value is `[ASSUMED]` and must be sourced by the planner at YAML-write time

## Summary

Phase 16 is a tightly-scoped YAML + predicate-module addition with one Phase 14 wire-in. It does not introduce new infrastructure: the loader (`lib/rules/_loader.py`), the citation-coverage meta-test, the YAML schema convention (quoted-Decimal scalars + per-file `source` / `effective`), and the predicate-module shape (module docstring with `Citation:` / `Source URL:` / `Effective:` + pure-function lookup) are all Phase 2 frozen surfaces. The two new files (`lib/rules/pmi.py`, `lib/rules/insurance.py`) mirror `lib/rules/fha_mip.py` 1:1; the two new YAMLs (`data/reference/property-analysis-heuristics.yml`, `data/reference/insurance-estimate-defaults.yml`) mirror `data/reference/fha-mip-rates.yml` 1:1. The Phase 14 wire-in deletes one inline constant (`_CONV_PMI_ANNUAL_RATE` at `lib/property_analysis.py:151`), swaps two call sites (PMI block lines 651-657, insurance block lines 703-705), and updates test/fixture assertions that pin the retired `PMI-RATE-ESTIMATED-0.0075` literal.

The single non-trivial research finding is that **three of the four external sources cited in CONTEXT need adjustment**: (1) MGIC does not publish its rate cards publicly — current PDFs are 404 or gated behind MiQ login, so the planner must capture a specific bulletin version manually and pin its filename/effective date; (2) the latest publicly-released NAIC Homeowners Insurance Report covers **2022 data, published 2025-05-21**, NOT "NAIC 2024"; California and Texas are NOT included in the NAIC dataset (CONTEXT D-16-INS-01 says "50 states + DC = 51 rows," but the planner will need a secondary source for CA + TX, e.g., the III/Bankrate state tables or each state's department of insurance); (3) **FEMA Risk Rating 2.0 (effective 2021-04) abandoned zone-based pricing**, so the X/+0 / A,AE/+30 / V/+80 / unknown/+15 schema in CONTEXT D-16-INS-02 cannot cite FEMA NFIP as the source — the planner must either cite private-carrier proxies (Neptune, Wright Flood) or restructure the multiplier table around something other than FEMA zone codes.

**Primary recommendation:** Treat the two new YAMLs as documenting the schema + the cell *positions* with placeholder strings tagged `# TODO: populate from <source>` at planner time, and ship the predicate modules + their hand-calc tests against a deliberately-frozen synthetic test YAML (per the Phase 2 RUL fixture pattern). The `data/reference/*.yml` files themselves get their final numbers in a single dedicated plan task that the user reviews — same shape as Phase 2's D-04 "ship the full matrix" workflow, but with the table values flagged as planner-sourced data rather than regulator-published numbers.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PMI rate lookup (FICO × LTV → annual rate) | Reference Layer + `lib/rules/` | — | Phase 2 "rules-as-predicates" pattern: each `lib/rules/*.py` owns one citation; data lives in `data/reference/*.yml`; loader is shared. Same tier as FHA MIP (`lib/rules/fha_mip.py`) and Fannie LLPA (`lib/rules/fannie_eligibility.py`). |
| Insurance default lookup (state + flood + earthquake → annual $) | Reference Layer + `lib/rules/` | — | Same as PMI. Distinct module per "one predicate per citation" — even though insurance is not a regulatory predicate, the citation-coverage test gate treats every `lib/rules/*.py` uniformly. |
| YAML staleness warning | `lib/rules/_loader.py` (frozen Phase 2 surface) | — | `_check_staleness()` is the single source of truth for the 12-month warning; new YAMLs inherit it automatically because they go through `load_reference()`. |
| State FIPS → USPS code mapping | `lib/rules/insurance.py` (small constant dict) | — | CONTEXT D-16-FILE-02 specifies "small constant dict in lib/rules/insurance.py." No new YAML needed — the 51 FIPS→USPS pairs are immutable Census Bureau metadata, not regulatory data with a refresh cadence. |
| Phase 14 PMI block wire-in | `lib/property_analysis.py` (calc-engine composition surface) | `lib/rules/pmi.py` | Phase 14's composition layer holds the call site; the predicate provides the rate. Same separation as Phase 14's existing FHA MIP call (`fha_mip_compute()` at line 666). |
| Phase 14 insurance fallback wire-in | `lib/property_analysis.py` (escrow block) | `lib/rules/insurance.py` | Fallback fires inside `_build_program_result`, NOT in `lib/property_listing.py` — Phase 13's PropertyListing model is frozen per CONTEXT D-13-FIELDS. |
| Reason-tag aggregation + dedup | `lib/property_analysis.py:analyze()` (lines 1504-1506) | — | Existing substring-match dedup `dict.fromkeys` pattern already aggregates PMI tags; Phase 16 extends the same aggregator to surface the new `PMI-RATE-CAPPED-MGIC-ABRIDGED-*` and `INSURANCE-ESTIMATED-NAIC-*` tags. |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**PMI table granularity + source (REF-09):**
- D-16-PMI-01 (4×4 MGIC abridged): 16-row PMI table. FICO bands: `760+`, `740-759`, `720-739`, `700-719`. LTV bands: `80.01-85`, `85.01-90`, `90.01-95`, `95.01-97`. Citation: MGIC Rate Card "Standard MI" abridged. Reason tag pattern: `PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}` (replaces today's `PMI-RATE-ESTIMATED-0.0075`).
- D-16-PMI-02 (Cap-at-worst-row fallback): out-of-band combos (FICO<700, LTV>97%) return the worst-cell rate (FICO `700-719` × LTV `95.01-97`) and tag `PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}`. No raise, no interpolation.
- D-16-PMI-03 (Reason-code retirement): retire `PMI-RATE-ESTIMATED-0.0075` literal; add the two new patterns above.

**Insurance defaults (REF-10):**
- D-16-INS-01 (50 states + DC, NAIC 2024 averages): 51 rows. Schema: `{state, base_annual, notes}`.
- D-16-INS-02 (Flood: per-FEMA-zone % uplift): 4 rows. X→+0%, A/AE→+30%, V→+80%, unknown→+15%. Multiplicative on state base.
- D-16-INS-03 (Earthquake: CA/OR/WA flat $ add-ons): 3 rows. Other states get no surcharge and no tag.
- D-16-INS-04 (Estimate tag on fallback): tag `INSURANCE-ESTIMATED-NAIC-{state}-{zone}` appended to `eligible_reasons`.

**File shape + module API (D-16-FILE family):**
- D-16-FILE-01 (Two separate single-purpose YAMLs, no aggregator manifest): `data/reference/property-analysis-heuristics.yml` (PMI only) + `data/reference/insurance-estimate-defaults.yml` (state base + flood multipliers + earthquake add-ons). Existing Phase 2 reference YAMLs stay as-is.
- D-16-FILE-02 (Two new lib/rules modules): `lib/rules/pmi.py` exports `lookup_rate(fico: int, ltv: Rate) -> Rate`; `lib/rules/insurance.py` exports `lookup_default(state: str, flood_zone: str | None) -> Money`. Both use existing `lib/rules/_loader.py:load_reference()`.
- D-16-FILE-03 (Loader unchanged): No changes to `_loader.py`. New YAMLs carry `effective:` dates and inherit `_check_staleness` automatically.

**Phase 14 wire-in:**
- D-16-WIRE-01 (Insurance fallback in property_analysis.py Step 6): Edit `lib/property_analysis.py:703-705`. When `_unwrap_provenanced(listing.insurance_estimate_annual)` returns the `default` of `Decimal("0.00")` (the current None-handler), call `lib.rules.insurance.lookup_default(household.state_fips, listing.flood_zone)` and append the INSURANCE-ESTIMATED-NAIC-{state}-{zone} reason.
- D-16-WIRE-02 (PMI lookup in property_analysis.py PMI block): Edit `lib/property_analysis.py:651-657`. Replace `_CONV_PMI_ANNUAL_RATE` reference with `lib.rules.pmi.lookup_rate(household.fico, ltv)`. Remove the Final constant at line 151 AND its module-docstring mention at lines 21-23.
- D-16-WIRE-03 (Allow-list update for new reason codes): Update the substring-match aggregator at `lib/property_analysis.py:1504-1506` to also surface the new tag families.

### Claude's Discretion

- **Exact MGIC PMI rate values** — planner sources from MGIC Rate Card "Standard MI" publication; effective date matches publication date. Recommend pinning the latest bulletin and citing the bulletin number.
- **Exact NAIC state averages** — planner sources from the latest NAIC Homeowners Insurance Report (2024 data ideally).
- **Exact flood-zone uplift percentages** — refine starting design (X/+0, A/AE/+30, V/+80, unknown/+15) to whatever the source publishes.
- **Exact CA/OR/WA earthquake $ values** — planner sources from CEA + PNW carrier averages.
- **YAML row schema details** — quoted Decimal strings per Phase 2 D-02. Flat `{state, base_annual, notes}` rows for insurance; `{fico_min, fico_max, ltv_min, ltv_max, rate}` rows for PMI matching the FHA-MIP-table shape.
- **Test fixture set** — golden hand-calc anchors: FICO 760 × LTV 95 (in-band), FICO 680 × LTV 96 (capped); insurance for WA × flood-zone X (Pachulski-household baseline).
- **Earthquake "unknown state" behavior** — when `state` is not in {CA, OR, WA}, the earthquake lookup returns Decimal("0.00") silently (no tag).

### Deferred Ideas (OUT OF SCOPE)

- Metro-level insurance overlay (v1.2).
- Per-USGS-seismic-zone earthquake granularity (v1.2).
- Multi-lender consensus PMI averaging (v1.2).
- Full MGIC 8×7 PMI schedule (v2).
- PMI variation by occupancy / unit count / loan purpose (v2).
- Annual refresh automation (Playwright scrape — Phase 2 D-08 AUTO-01).
- Edits to `lib/property_listing.py` (Phase 13 frozen).
- Edits to `.claude/skills/mortgage-ops/modes/property.md` (Phase 15 mode body owns extraction).
- New REF requirements beyond REF-09 / REF-10.
- Earthquake state coverage beyond CA/OR/WA.
- True NFIP-policy cost separate from homeowners uplift.
- PropertyListing model_validator auto-population (rejected — keep the fallback in property_analysis.py).
- Cross-table aggregator manifest with `includes:` block.

## Project Constraints (from CLAUDE.md)

The following directives in `./CLAUDE.md` constrain every Phase 16 task. They have the same authority as locked CONTEXT decisions.

| Directive | Source | Enforcement in Phase 16 |
|-----------|--------|-------------------------|
| **Decimal from strings only** (no `Decimal(0.0075)`; always `Decimal("0.0075")`) | Conventions §Money discipline | Every YAML scalar quoted; every test fixture constructs Decimal from a string; PMI / insurance rate values quoted in YAML. |
| **`quantize(Decimal("0.01"), ROUND_HALF_UP)` end-of-period only** | Conventions §Money discipline | Insurance lookup returns annual Money; caller quantizes; predicate does NOT pre-quantize the per-month-divided value. |
| **No float-Decimal mixing in same expression** | Conventions §Money discipline | YAML loader returns string; predicate wraps in Decimal at boundary; never `Decimal(yaml_value)` where yaml_value is a float. |
| **Pydantic v2 `condecimal` at script boundaries** | Conventions §Money discipline | If a CLI or DuckDB write surface accepts predicate output, Money/Rate aliases handle it (no new types needed Phase 16). |
| **Reference data in `data/reference/*.yml` with `source:` URL + `effective:` date** | Conventions §Reference data discipline | Both new YAMLs MUST have `source:` and `effective:` at top level; loader raises `MissingReferenceFieldError` otherwise. |
| **Annual refresh = YAML edit + commit, never code change** | Conventions §Reference data discipline | Predicates never have hard-coded rates; everything routes through `load_reference()`. |
| **Startup-time staleness check at 12 months** | Conventions §Reference data discipline | `_loader.py:_check_staleness()` is the gate; Phase 16 does not touch it. NAIC 2022 data will fire `StaleReferenceWarning` (correct — see "Common Pitfalls" below). |
| **One file per regulatory citation in `lib/rules/`** | Conventions §Rules-as-predicates | `lib/rules/pmi.py` and `lib/rules/insurance.py` are distinct modules; each carries one docstring with one Citation line; the citation-coverage meta-test gates this. |
| **Docstring includes citation (12 CFR §X.Y, HUD ML Z, etc.)** | Conventions §Rules-as-predicates | PMI cites MGIC bulletin; insurance cites NAIC report + CEA averages + private-carrier flood survey. NOT statute (industry-published, not regulatory) — explicit acknowledgment in docstring per CONTEXT precedent. |
| **1:1 test-to-citation mapping** | Conventions §Rules-as-predicates | Every YAML row has at least one hand-calc test anchor; every test asserts the YAML-published value verbatim. |
| **Hand-calculated golden-value fixtures with citation comments** | Conventions §Testing | `tests/fixtures/rules/pmi_*.json` + `tests/fixtures/rules/insurance_*.json` with `citation` + `source_url` + `comment` fields per Phase 2 RUL pattern. |
| **Exact Decimal equality, never `assertAlmostEqual` for money** | Conventions §Testing | Test assertions use `assert result == Decimal("0.0090")` style; never tolerance comparisons. |
| **No Co-Authored-By or AI attribution in commits** | Conventions §Commits + global rule | All Phase 16 commits authored solely by the repo owner. |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REF-09 | `data/reference/property-analysis-heuristics.yml` ships PMI rate tables. Annual refresh = YAML edit. | "Standard Stack" §1 (PyYAML 6+ already shipped); "Architecture Patterns" §Pattern 1 (fha_mip.py analog); "Code Examples" §1 (PMI module skeleton); D-16-PMI-01..03 covered in CONTEXT. |
| REF-10 | `data/reference/insurance-estimate-defaults.yml` ships per-state HOI avg + flood + earthquake. | "Standard Stack" §1; "Architecture Patterns" §Pattern 1 (multi-section YAML precedent: va-funding-fees.yml); "Code Examples" §2 (insurance module skeleton); "Common Pitfalls" §3 (FEMA Risk Rating 2.0 decoupled zone-from-premium). D-16-INS-01..04 covered in CONTEXT, but external sources flagged HIGH-uncertainty — see "Open Questions" §1, §2, §3, §4. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pyyaml` | `>=6.0.2` | YAML parsing for `data/reference/*.yml` | Already declared in `pyproject.toml` line 12 [VERIFIED: pyproject.toml]; used by Phase 2 `_loader.py` line 20. `safe_load` enforced per CLAUDE.md (Phase 2 D-... ASVS V10 mitigation). |
| `pydantic` | `>=2.13.3` | Strict/frozen output models if any new types ship | Already declared [VERIFIED: pyproject.toml line 9]. `Rate` / `Money` aliases from `lib/models.py` cover the predicate output surface; no new types expected. |
| `pytest` | `>=9.0` | Hand-calc anchored predicate tests | Already declared [VERIFIED: pyproject.toml line 20]. New tests land in `tests/test_rules/test_pmi.py` + `tests/test_rules/test_insurance.py`. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dateutil` | `>=2.9.0` | `relativedelta(months=12)` for staleness check | Already declared [VERIFIED: pyproject.toml line 10]; Phase 16 uses `_loader.py` unchanged so no direct dateutil usage in new modules. |
| `decimal` (stdlib) | — | Money-from-strings boundary coercion | Standard Python stdlib. Every predicate wraps YAML strings in `Decimal(...)` at consumption. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline `_CONV_PMI_ANNUAL_RATE` Final constant | YAML-driven lookup (current path) | Inline is simpler but violates CLAUDE.md "annual refresh = YAML edit, never code change" — locked out by ROADMAP SC #5. |
| One unified `property-analysis-heuristics.yml` with PMI + insurance + future tables | Two separate YAMLs (current path) | Unified is more discoverable but mixes two regulatory domains; CONTEXT D-16-FILE-01 explicitly rejects this. |
| `state-fips-usps.yml` separate file for FIPS→USPS mapping | Constant dict in `lib/rules/insurance.py` (current path) | YAML is consistent with reference-layer discipline but FIPS→USPS is Census Bureau metadata, not regulatory; no refresh cadence; CONTEXT D-16-FILE-02 locks the constant-dict approach. |
| MGIC 8×7 full schedule (56 cells) | MGIC 4×4 abridged (16 cells, current path) | Full matrix is closer to real-world quote accuracy; abridged keeps refresh burden tractable; CONTEXT D-16-PMI-01 locks 4×4. |
| Two-tier lookup (metro then state) for insurance | State-only 51-row table (current path) | Metro is more accurate; requires ZIP→MSA mapping out of v1 scope; CONTEXT defers to v1.2. |

**Installation:** No new dependencies — all required libraries are already pinned in `pyproject.toml`. Phase 16 is a pure-data + pure-Python addition.

**Version verification:** All declared versions verified against `pyproject.toml` 2026-05-22.

## Architecture Patterns

### System Architecture Diagram

```
                      Phase 14 analyze(listing, household, profile)
                                          │
                                          ▼
                          ┌──────────────────────────────────┐
                          │ _build_program_result()          │
                          │ lib/property_analysis.py L611+   │
                          └────────────┬─────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │ PMI block        │    │ FHA MIP block    │    │ Insurance block  │
   │ L651-657 (edit)  │    │ L658-672 (no chg)│    │ L702-705 (edit)  │
   └────────┬─────────┘    └──────────────────┘    └────────┬─────────┘
            │                                                │
            ▼                                                ▼
   ┌──────────────────┐                          ┌──────────────────┐
   │ lib/rules/pmi.py │                          │ lib/rules/        │
   │ lookup_rate()    │                          │ insurance.py      │
   │ NEW              │                          │ lookup_default()  │
   └────────┬─────────┘                          │ NEW               │
            │                                    └────────┬─────────┘
            ▼                                             │
   ┌──────────────────┐                                   ▼
   │ load_reference   │◄─────────────────────────────────┘
   │ lib/rules/       │
   │ _loader.py       │  (existing; lru_cache + staleness check)
   └────────┬─────────┘
            │
   ┌────────┴──────────────────────────────────────┐
   │                                                │
   ▼                                                ▼
data/reference/                              data/reference/
property-analysis-                           insurance-estimate-
heuristics.yml (NEW)                         defaults.yml (NEW)

   [16 PMI rows]                             [51 state rows +
                                              4 flood multipliers +
                                              3 earthquake add-ons]


   reasons aggregation:
   ┌──────────────────────────────────────────────┐
   │ analyze() L1504-1506 (substring-match dedup) │
   │                                              │
   │ "PMI-RATE-ESTIMATED-MGIC-*"  ──┐             │
   │ "PMI-RATE-CAPPED-MGIC-*"     ──┼──> warnings │
   │ "INSURANCE-ESTIMATED-NAIC-*" ──┘             │
   └──────────────────────────────────────────────┘
```

The diagram traces the data flow: Phase 14's `analyze()` calls `_build_program_result()` per cell; the PMI and insurance blocks each route through the new `lib/rules/*.py` predicate; both predicates load their YAML via the existing `_loader.py`. The reason aggregator at the top of `analyze()` (lines 1504-1506) dedups any tag matching the registered prefixes via `dict.fromkeys`.

### Recommended Project Structure

```
data/reference/
├── property-analysis-heuristics.yml    # NEW (Phase 16, REF-09)
├── insurance-estimate-defaults.yml     # NEW (Phase 16, REF-10)
├── fha-mip-rates.yml                   # existing (Phase 2)
├── conforming-limits-2026.yml          # existing (Phase 2)
├── va-funding-fees.yml                 # existing (Phase 2)
├── fha-limits-2026.yml                 # existing (Phase 2)
├── fannie-llpa-matrix.yml              # existing (Phase 2)
├── freddie-eligibility-matrix.yml      # existing (Phase 2)
├── usda-income-limits.yml              # existing (Phase 2)
├── irs-pub936.yml                      # existing (Phase 2)
├── va-residual-income.yml              # existing (Phase 2)
└── atr-qm-thresholds.yml               # existing (Phase 2)

lib/rules/
├── pmi.py                              # NEW (Phase 16, REF-09)
├── insurance.py                        # NEW (Phase 16, REF-10)
├── _loader.py                          # existing (Phase 2; no edits)
├── conventional_pmi.py                 # existing (Phase 2; HPA cancellation — UNRELATED to rate lookup)
├── fha_mip.py                          # existing (Phase 2; analog for pmi.py)
├── fannie_eligibility.py               # existing (Phase 2)
├── freddie_eligibility.py              # existing (Phase 2)
├── va_funding_fee.py                   # existing (Phase 2)
├── va_residual_income.py               # existing (Phase 2)
├── usda.py                             # existing (Phase 2)
├── atr_qm.py                           # existing (Phase 2)
├── reg_z.py                            # existing (Phase 2)
├── irs_pub936.py                       # existing (Phase 2)
├── loan_type.py                        # existing (Phase 2)
└── types.py                            # existing (Phase 2)

tests/test_rules/
├── test_pmi.py                         # NEW (Phase 16)
├── test_insurance.py                   # NEW (Phase 16)
├── test_citation_coverage.py           # existing (Phase 2; auto-discovers pmi.py + insurance.py)
└── (existing per-predicate tests)

tests/fixtures/rules/
├── pmi_*.json                          # NEW (Phase 16; ≥16 fixtures, 1:1 to cells)
├── insurance_*.json                    # NEW (Phase 16; ≥3 fixtures)
└── (existing per-predicate fixtures)

lib/property_analysis.py                # MODIFIED (Phase 16; ~6 line edits + 1 import)
tests/test_property_analysis.py         # MODIFIED (Phase 16; 4 assertions updated)
tests/fixtures/property_analysis/*.json # MODIFIED (Phase 16; 3 fixtures — update "warnings" array)
```

### Pattern 1: One-predicate-per-citation YAML lookup module

**What:** Each `lib/rules/*.py` predicate file owns a single citation, loads one YAML via `load_reference()`, exposes a single lookup function, and has a `Citation:` / `Source URL:` / `Effective:` block in the module docstring.

**When to use:** Every Phase 16 new module. Mandatory — the citation-coverage meta-test at `tests/test_rules/test_citation_coverage.py:28-39` fails any predicate without these three docstring lines.

**Example (PMI module skeleton):**

```python
# Source: tests/test_rules/test_citation_coverage.py (the meta-test enforces this shape)
# Source: lib/rules/fha_mip.py L1-46 (analog module docstring)
"""Conventional PMI annual rate lookup (4x4 LTV x FICO MGIC abridged schedule).

Citation: MGIC Rate Card "Standard MI" (Borrower-Paid Monthly Premium)
  — industry-published rate schedule, NOT a regulatory predicate. Phase 16
  ships an abridged 4x4 subset (16 cells); the full MGIC 8x7 schedule is
  deferred to v2 per CONTEXT D-16-PMI-01.
Source URL: https://www.mgic.com/rates/rate-cards
  [BULLETIN-SPECIFIC URL: planner pins the exact bulletin PDF + revision
   number; the landing page above is not stable across MGIC site refactors.]
Effective: <planner pins to bulletin publication date>

What this predicate decides:
  Given a FICO score and an LTV ratio, return the annual PMI rate
  (decimal, e.g., 0.0050 = 50bps). Tags the call site with either:
    PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}  (in-band)
    PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}     (out-of-band)
  per CONTEXT D-16-PMI-03.

  Out-of-band fallback (D-16-PMI-02): when (fico, ltv) falls outside the
  4x4 grid, return the rate from the WORST cell (FICO 700-719 x LTV
  95.01-97). No raise, no interpolation.

Inputs:
    fico: int (representative score, 300..850 per lib/household.py L61)
    ltv:  Rate (financed_principal / appraised_value at origination)

Outputs:
    LookupResult — frozen Pydantic model with:
        annual_rate: Rate (Decimal; e.g., Decimal("0.0050"))
        reason_tag:  str (the tag to append to eligible_reasons)
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict
from lib.models import Rate
from lib.rules._loader import load_reference


class PMILookupResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    annual_rate: Rate
    reason_tag: str


def lookup_rate(fico: int, ltv: Decimal) -> PMILookupResult:
    """Return PMI annual rate (Decimal) + reason tag per D-16-PMI-02/03."""
    ref = load_reference("property-analysis-heuristics")
    table = ref["pmi_annual_rate_table"]
    for row in table:
        fico_min = int(row["fico_min"])
        fico_max = int(row["fico_max"])
        ltv_min = Decimal(row["ltv_min"])
        ltv_max = Decimal(row["ltv_max"])
        if fico_min <= fico <= fico_max and ltv_min < ltv <= ltv_max:
            return PMILookupResult(
                annual_rate=Decimal(row["annual_rate"]),
                reason_tag=(
                    f"PMI-RATE-ESTIMATED-MGIC-"
                    f"{row['ltv_band_label']}-{row['fico_band_label']}"
                ),
            )
    # D-16-PMI-02: cap at worst row (FICO 700-719 x LTV 95.01-97)
    worst = ref["pmi_capped_fallback"]
    return PMILookupResult(
        annual_rate=Decimal(worst["annual_rate"]),
        reason_tag=f"PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}",
    )
```

### Pattern 2: Quoted-Decimal YAML scalars (Phase 2 D-02 Pitfall 1 defense)

**What:** Every numeric scalar in `data/reference/*.yml` MUST be a quoted string. The loader returns strings; consumers wrap in `Decimal(...)` at the boundary.

**When to use:** Every YAML row in the two new files. Non-negotiable per CLAUDE.md money discipline and per the on-import schema validation in `_loader.py:80-85` (the `effective:` field, conversely, MUST be unquoted to remain a `datetime.date`).

**Example (PMI YAML skeleton):**

```yaml
# Source: data/reference/fha-mip-rates.yml (analog file shape)
# data/reference/property-analysis-heuristics.yml
source: "<MGIC Rate Card 'Standard MI' bulletin URL — planner pins exact PDF>"
effective: 2026-XX-XX  # UNQUOTED YAML date; loader rejects quoted strings
notes: |
  MGIC Rate Card "Standard MI" Borrower-Paid Monthly Premium (BPMI),
  abridged 4x4 subset per CONTEXT D-16-PMI-01. Full 8x7 schedule deferred
  to v2.

  Schema:
    - fico_min / fico_max: representative-FICO range (inclusive both ends)
    - ltv_min / ltv_max:   LTV range (exclusive min, inclusive max except
                           when min==0.80 where it is inclusive — matches
                           FHA-MIP-table bucket convention in fha_mip.py)
    - annual_rate:         Decimal-as-string; e.g., "0.0050" = 50bps
    - fico_band_label:     human label for reason-tag composition
    - ltv_band_label:      human label for reason-tag composition

  Annual refresh = MGIC bulletin re-extraction + YAML edit. No code change.
  Staleness check fires at 12 months from `effective:`.

pmi_annual_rate_table:
  # FICO 760+ row
  - {fico_min: "760", fico_max: "850", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "<TODO>", fico_band_label: "760+", ltv_band_label: "80-85"}
  - {fico_min: "760", fico_max: "850", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "<TODO>", fico_band_label: "760+", ltv_band_label: "85-90"}
  - {fico_min: "760", fico_max: "850", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "<TODO>", fico_band_label: "760+", ltv_band_label: "90-95"}
  - {fico_min: "760", fico_max: "850", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "<TODO>", fico_band_label: "760+", ltv_band_label: "95-97"}
  # FICO 740-759 row (3 more cells)
  # FICO 720-739 row (4 more cells)
  # FICO 700-719 row (4 more cells)  -- the 4th cell here is also the capped-fallback target
  # ... 16 cells total

pmi_capped_fallback:
  # The "worst cell" — FICO 700-719 x LTV 95.01-97 — per D-16-PMI-02.
  # Referenced by lib.rules.pmi.lookup_rate when (fico, ltv) is out-of-band.
  fico_band_label: "700-719"
  ltv_band_label: "95-97"
  annual_rate: "<TODO matches the row above>"
```

### Pattern 3: Multi-section YAML (insurance with state base + flood multipliers + earthquake add-ons)

**What:** When one YAML carries multiple distinct lookup surfaces, use top-level keyed blocks (NOT a single flat list). Mirrors `data/reference/va-funding-fees.yml` which carries `purchase`, `flat_fees`, and `exemption` sections [VERIFIED: file contents read 2026-05-22].

**When to use:** `data/reference/insurance-estimate-defaults.yml` — 3 distinct surfaces (state base, flood multipliers, earthquake add-ons).

**Example:**

```yaml
# Source: data/reference/va-funding-fees.yml (analog file shape — multi-section)
# data/reference/insurance-estimate-defaults.yml
source: "<NAIC report URL OR composite-source statement per Open Q1>"
effective: 2025-05-21  # NAIC 2022 data report publication date; will fire StaleReferenceWarning (CORRECT per Phase 2 D-12 precedent)
notes: |
  Three independent lookup surfaces in one file:
    1. state_base_annual_premium: 51 rows (50 states + DC); state base
       homeowners insurance premium per CONTEXT D-16-INS-01.
    2. flood_zone_multipliers: 4 rows (X, A/AE, V, unknown); MULTIPLICATIVE
       on top of state base per CONTEXT D-16-INS-02.
    3. earthquake_state_addons: 3 rows (CA, OR, WA); ADDITIVE flat $
       per CONTEXT D-16-INS-03.

  Composition for state=WA, flood_zone="X":
    base = lookup state_base_annual_premium where state == "WA"
    multiplier = lookup flood_zone_multipliers where zone == "X" (= 1.00)
    eq_addon = lookup earthquake_state_addons where state == "WA" (Money)
    annual_premium = quantize_cents(base * multiplier + eq_addon)

  Composition for state=TX, flood_zone=None:
    base = lookup state_base_annual_premium where state == "TX"
    multiplier = lookup flood_zone_multipliers where zone == "unknown"
    eq_addon = Decimal("0.00")  (TX not in {CA, OR, WA}; no tag)

state_base_annual_premium:
  - {state: "AL", base_annual: "<TODO>", notes: "<source citation per state if differs from header>"}
  - {state: "AK", base_annual: "<TODO>", notes: "<...>"}
  # ... 51 rows total

flood_zone_multipliers:
  # CONTEXT D-16-INS-02 starting design (planner may refine):
  - {zone: "X",       multiplier: "1.00", notes: "Minimal risk; no uplift"}
  - {zone: "A",       multiplier: "1.30", notes: "100-year floodplain"}
  - {zone: "AE",      multiplier: "1.30", notes: "100-year floodplain, base flood elevations established"}
  - {zone: "V",       multiplier: "1.80", notes: "Coastal high-velocity zone"}
  - {zone: "unknown", multiplier: "1.15", notes: "Missing data default (mid-band)"}

earthquake_state_addons:
  - {state: "CA", flat_addon_annual: "<TODO>", notes: "CEA + private market avg"}
  - {state: "OR", flat_addon_annual: "<TODO>", notes: "Cascadia subduction zone exposure; non-CEA"}
  - {state: "WA", flat_addon_annual: "<TODO>", notes: "Cascadia subduction zone exposure; non-CEA"}
```

### Pattern 4: Range-based row matching (FHA-MIP-table convention)

**What:** When a YAML row carries a numeric range (e.g., `fico_min`/`fico_max` or `ltv_min`/`ltv_max`), the lookup helper coerces strings to Decimal/int at consumption, applies inclusive/exclusive bucket conventions consistently, and raises (or falls back) when no row matches.

**When to use:** `lib/rules/pmi.py:lookup_rate()` (PMI 4×4 grid). Insurance state lookup is exact-match (USPS code), not range-based.

**Example:** See `lib/rules/fha_mip.py:132-167` (`_lookup_annual_mip` helper) — the exact pattern PMI mirrors. Note the bucket convention: `ltv_min == Decimal("0.00")` treats `ltv_min` as inclusive; otherwise exclusive. PMI cells with `ltv_min == Decimal("0.80")` should follow Phase 14's existing convention at `lib/property_analysis.py:652` where `provisional_ltv > Decimal("0.80")` triggers PMI — so `ltv_min == Decimal("0.80")` is EXCLUSIVE in `pmi.py` (a cell at LTV 0.80 exactly does NOT trigger PMI; only > 0.80 does).

### Anti-Patterns to Avoid

- **Float-Decimal mixing at the YAML boundary** — `Decimal(row["annual_rate"])` where `row["annual_rate"]` is an unquoted YAML scalar (PyYAML emits a float). Defense: every numeric scalar quoted in YAML; consumers always `Decimal(str)` at boundary. Phase 14 verifies this via the existing test pattern at `tests/test_property_analysis.py:484-501` (the `test_float_rejection` precedent).
- **Hand-rolling the staleness warning** — Don't reimplement `_check_staleness` in `pmi.py` or `insurance.py`. The loader does this once; predicates don't repeat it.
- **Embedding state names instead of USPS codes** — Use 2-char USPS codes (`WA`, not `Washington`); FIPS→USPS happens in `lib/rules/insurance.py` constant dict, NOT in the YAML row keys.
- **Returning Money from `lookup_default()` with the wrong type wrapping** — `lib/models.py:Money` is `Annotated[Decimal, ...]`; returning a raw `Decimal` works because Money is just an alias, but tests should assert on `Decimal` equality, not on `Money(Decimal(...))` instantiation.
- **Auto-fixing `eligible_reasons` allow-list mid-phase** — there is no `_ALLOWED_REASONS` constant (CONTEXT D-16-WIRE-03 misnames this surface; see "Common Pitfalls" §1). The "allow-list" is the substring-match aggregator at line 1505 plus the literal-string assertions in `tests/test_property_analysis.py`. Phase 16 updates those assertions, NOT a non-existent constant.
- **Pre-quantizing predicate output to monthly** — Insurance predicate returns annual Money; the call site at `lib/property_analysis.py:702-705` quantizes monthly via `/Decimal("12")` end-of-period. Predicate quantizing first then dividing creates two rounding events (Pitfall 6 violation per Phase 14 module docstring).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML loading + 12-month staleness | Custom loader per module | `lib/rules/_loader.py:load_reference()` | Already shipped (Phase 2); handles `safe_load`, schema validation, `lru_cache`, `_check_staleness` warning. Re-implementing creates loader drift. |
| Citation hygiene check | Per-predicate ad-hoc docstring check | `tests/test_rules/test_citation_coverage.py` | Filesystem-introspecting parametrized test (lines 23-48) auto-discovers any new `lib/rules/*.py` and asserts Citation: / Source URL: / Effective: lines + at least one matching fixture file. Zero config — both new modules are picked up automatically. |
| Reason-tag uniqueness in `analyze()` warnings | Manual dedup loop | Existing pattern at `lib/property_analysis.py:1533` (`list(dict.fromkeys(warnings))`) | Already dedups by first-occurrence order; new tag families inherit dedup if the aggregator pattern at L1504-1506 is extended (3 lines added). |
| FIPS → USPS state code mapping | Pull from a `data/reference/state-fips-usps.yml` | Constant dict in `lib/rules/insurance.py` per CONTEXT D-16-FILE-02 | Immutable Census Bureau metadata; no refresh cadence; YAML-ifying creates pointless 12-month warnings on a never-changing dataset. |
| Test fixture pattern for reference-data predicates | Custom JSON shape | `tests/fixtures/rules/*.json` Phase 2 RUL pattern | Already established: each fixture has `citation`, `source_url`, `comment`, and hand-calc inputs + expected outputs. See `tests/fixtures/rules/fha_mip_term30_ltv95_post_2023.json` for shape. |
| Pydantic output models | New domain types in `lib/rules/types.py` | Reuse `lib.models.Money` + `lib.models.Rate` | The predicate outputs are scalars (one Decimal rate, one Money annual); a single `LookupResult` Pydantic per predicate is appropriate but DON'T add new "PMICell" / "InsuranceState" record types unless tests demand them. |

**Key insight:** Phase 16 is a thin extension of Phase 2's frozen infrastructure. The entire scope reduces to: 2 YAMLs that mirror existing YAMLs, 2 predicate modules that mirror `lib/rules/fha_mip.py`, 2 test files that mirror `tests/test_rules/test_fha_mip.py`, and 4-6 line edits in `lib/property_analysis.py`. Custom infrastructure is forbidden by the architectural responsibility map.

## Common Pitfalls

### Pitfall 1: `_ALLOWED_REASONS` does not exist as a constant

**What goes wrong:** CONTEXT D-16-WIRE-03 references "the `_ALLOWED_REASONS` constant in `lib/property_analysis.py:296`" and instructs the planner to "replace with regex/prefix pattern matching." But the verbatim file at line 296 is a docstring comment, not a constant [VERIFIED: read 2026-05-22]. There is no Python-level allow-list constant anywhere in `lib/property_analysis.py` or `lib/property_verdict.py`. A planner who searches for the constant and edits a phantom won't catch the real allow-list surface.

**Why it happens:** Confusion between three distinct surfaces:
1. `VERDICT_*` Final[str] constants in `lib/property_verdict.py:60-88` — these are VERDICT predicate codes (`"DTI-CEILING-ALL-PROGRAMS"`, `"GO-ALL-GREEN"`, etc.), NOT the soft-signal `eligible_reasons` tags.
2. The substring-match aggregator at `lib/property_analysis.py:1504-1506`: `if any("PMI-RATE-ESTIMATED" in r for c in matrix.cells for r in c.eligible_reasons): warnings.append("PMI-RATE-ESTIMATED")` — this is the implicit allow-list for the top-level `report.warnings` field.
3. Test assertions in `tests/test_property_analysis.py` at lines 481, 1101-1102, 1116, 1120, 1299, 1319, 1326 — these are literal-string assertions that pin the retired tag `"PMI-RATE-ESTIMATED-0.0075"`.

**How to avoid:**
- The Phase 16 "allow-list update" actually means: (a) change line 1505 substring from `"PMI-RATE-ESTIMATED"` to handle both new tag families (`PMI-RATE-ESTIMATED-MGIC` and `PMI-RATE-CAPPED-MGIC` map to `"PMI-RATE-ESTIMATED"` and `"PMI-RATE-CAPPED"` top-level warnings); (b) update the 7 test assertion sites in `tests/test_property_analysis.py` (grep for `"PMI-RATE-ESTIMATED-0.0075"` — there are 4 in `tests/test_property_analysis.py`, 0 in `tests/test_property_verdict.py`); (c) update the 3 fixture JSON files (`tests/fixtures/property_analysis/sfh_conforming_king_county.json`, `condo_with_hoa_seattle.json`, `sfh_jumbo_bay_area.json`) — all 3 carry `"warnings": ["PMI-RATE-ESTIMATED"]`. Plus update the `condo_with_hoa_seattle.json` notes + eligible_reasons array (4 spots).
- Add an explicit `_PMI_REASON_PREFIXES: Final[frozenset[str]] = frozenset({"PMI-RATE-ESTIMATED-MGIC", "PMI-RATE-CAPPED-MGIC"})` constant at module-load time in `lib/property_analysis.py` (near line 249-251 with the other `_STRESS_*_CODE` constants) so the aggregator pattern is grep-discoverable and not buried in a literal.

**Warning signs:** Grep results showing 7 hits for `PMI-RATE-ESTIMATED-0.0075` in `tests/test_property_analysis.py` and 0 hits for a constant by that name anywhere; the Phase 14 verifier explicitly notes "the 3 warnings are stale-reference data warnings (`fha-mip-rates`, `irs-pub936`, `va-funding-fees` all > 12 months)" and DOES NOT mention any reasons-allow-list test failure — because no such test exists. [VERIFIED: read of `lib/property_analysis.py` 2026-05-22; `tests/test_property_analysis.py` grep output 2026-05-22]

### Pitfall 2: `_unwrap_provenanced` returns Decimal("0.00") not None — the fallback trigger condition needs care

**What goes wrong:** CONTEXT D-16-WIRE-01 says "when `_unwrap_provenanced(listing.insurance_estimate_annual)` returns None, call `lib.rules.insurance.lookup_default(...)`." But the helper at `lib/property_analysis.py:497-507` NEVER returns None — it returns the `default` argument (`Decimal("0.00")` by default) when `pm` is None or `pm.value` is None [VERIFIED: read 2026-05-22]. Conditionally branching on `is None` will never fire.

**Why it happens:** B-4 fix in Plan 14-02 changed the return contract from `Money | None` to `Money` (defaulted to 0.00) to "prevent TypeError from `None / Decimal('12')` in escrow division paths" [VERIFIED: docstring at L497-506]. The fix shadows the gap-fill state.

**How to avoid:** The Phase 16 fallback trigger must check `listing.insurance_estimate_annual is None` OR `(listing.insurance_estimate_annual is not None and listing.insurance_estimate_annual.value is None)` at the call site, BEFORE the `_unwrap_provenanced` call. Recommended new helper:

```python
# Source: lib/property_analysis.py L497-507 (existing _unwrap_provenanced)
def _insurance_annual(
    listing: PropertyListing,
    household: Household,
) -> tuple[Decimal, str | None]:
    """Return (annual_insurance_money, optional_reason_tag).

    If the listing carries a non-None insurance_estimate_annual.value, use it
    and return tag=None. Otherwise call lib.rules.insurance.lookup_default and
    return tag="INSURANCE-ESTIMATED-NAIC-{state}-{zone}".
    """
    pm = listing.insurance_estimate_annual
    if pm is not None and pm.value is not None:
        return pm.value, None
    from lib.rules.insurance import lookup_default
    state_usps = _fips_to_usps(household.state_fips)
    zone = listing.flood_zone if hasattr(listing, "flood_zone") else None
    annual = lookup_default(state_usps, zone)
    return annual, f"INSURANCE-ESTIMATED-NAIC-{state_usps}-{zone or 'unknown'}"
```

**Warning signs:** `if monthly_insurance == Decimal("0.00")` style branching — will misfire when the listing legitimately has $0 insurance. Always branch on the wrapper presence, not the unwrapped scalar value.

### Pitfall 3: PropertyListing has NO `flood_zone` field

**What goes wrong:** CONTEXT D-16-WIRE-01 says "Phase 13 `PropertyListing` already exposes `flood_zone: str | None` per Phase 13 D-13-FIELDS" and the input pin (`files_to_read`) reiterates "PropertyListing has flood_zone field." Verification of `lib/property_listing.py` 2026-05-22 shows **no such field exists**. The full field list is: `price`, `zip`, `property_type`, `tax_annual`, `hoa_monthly`, `insurance_estimate_annual`, `zestimate`, `beds`, `baths`, `sqft`, `year_built`, `days_on_market`, `list_date` (+ their `*_provenance` siblings), `source_url`, `zpid`, `fetched_at` [VERIFIED: read of `lib/property_listing.py` 2026-05-22]. No `flood_zone`.

**Why it happens:** Likely a CONTEXT-stage confusion with a planned-but-not-shipped Phase 13 field. The CONTEXT also locks "Phase 13 PropertyListing model stays frozen" (`<domain>` section line 29), so adding `flood_zone` to PropertyListing in Phase 16 is explicitly out of scope.

**How to avoid:** Phase 16's `lib.rules.insurance.lookup_default(state, flood_zone)` MUST accept `flood_zone: str | None` and the call site MUST always pass `None`. Insurance YAML's `flood_zone_multipliers` block becomes effectively a single-row lookup (the `"unknown"` row, multiplier=1.15) for every Phase 16 invocation. The PMI work doesn't need flood_zone. Two options:

  **Option A (CONTEXT-conforming):** Accept that `flood_zone` is always None in v1.1; ship the multiplier table for forward compatibility; the only multiplier that fires in practice is `"unknown"` → 1.15. Document this in `lib/rules/insurance.py` docstring. v1.2 phase adds `flood_zone` to PropertyListing.

  **Option B (planner escalation):** Plan an addition to Phase 13's PropertyListing model — but this violates "PropertyListing model stays frozen" lock and creates a Phase-16-scope-creep issue. Not recommended without an explicit user override.

Recommendation: Option A. Default `flood_zone=None` always; multiplier table is forward-compatible scaffolding.

**Warning signs:** A planner task that says "edit `lib/property_listing.py` to add flood_zone" — that violates D-16-WIRE-01's "PropertyListing model (Phase 13) is NOT modified" lock.

### Pitfall 4: macOS Finder-duplicate files in `lib/rules/`

**What goes wrong:** `ls lib/rules/` shows `fha_mip 2.py` and `fha_mip 3.py` alongside `fha_mip.py` [VERIFIED: ls output 2026-05-22]. The Phase 14 verification report explicitly calls these out as "7 fha_mip duplicate-file failures from macOS Finder duplicates" that are "correctly out of scope" for Phase 14. The citation-coverage meta-test at `tests/test_rules/test_citation_coverage.py:23` globs `RULES_DIR.glob("*.py")` — so any new `pmi 2.py` or `insurance 2.py` accidentally created by Finder will be auto-discovered and fail the meta-test.

**Why it happens:** macOS Finder appends `" 2"`, `" 3"`, etc. when copy-paste duplicates occur (often during inspection or backups).

**How to avoid:** (a) Verify post-write that `lib/rules/` contains only intended files — `ls lib/rules/ | grep -E "^[a-z_]+\.py$"` should match the intended file set; (b) Plan task should include explicit guard: "delete any macOS Finder duplicates before commit"; (c) Add a `.gitignore` rule `lib/rules/*[0-9].py` if not already present (or pre-commit hook). Note that Phase 14's verifier acknowledged the existing fha_mip duplicates pre-existed and went out of scope — Phase 16 should NOT delete them unless explicitly tasked (could be intentional artifacts).

**Warning signs:** New test failures with names like `test_predicate_has_citation_in_docstring[pmi 2]` or `test_predicate_has_at_least_one_fixture[insurance 2]`.

### Pitfall 5: NAIC report is 2022 data, not 2024; California and Texas are excluded

**What goes wrong:** CONTEXT D-16-INS-01 says "NAIC 2024 averages" for 50 states + DC = 51 rows. The most recent publicly-released NAIC Homeowners Insurance Report is "**Data for 2022**", published **2025-05-21** [VERIFIED: WebFetch of content.naic.org news release 2026-05-22]. NAIC's 2018 report (the prior cycle) was published 2021-01-13 — i.e., NAIC has a multi-year publication lag. Additionally, **California and Texas are NOT covered** by NAIC's statistical-agent data feed (they submit data directly to NAIC by a different process and are typically excluded from the published averages tables) [VERIFIED: NAIC news release wording 2026-05-22]. A 51-row YAML claiming "NAIC 2024" averages will be both temporally and structurally inaccurate.

**Why it happens:** Industry parlance often says "NAIC averages" generically, but the specific tabular product has a real release cadence and known coverage gaps.

**How to avoid:**
- Pin `effective: 2025-05-21` (NAIC report publication date) — the YAML will fire `StaleReferenceWarning` IF the planner's research date is > 12 months past that; the warning is correct (Phase 2 D-12 precedent: warnings firing on still-current data is expected behavior).
- For California + Texas state rows, use a clearly-cited secondary source — III, Bankrate state tables, or each state's department of insurance. Add a per-row `notes:` field documenting which rows came from which source (mixed-source provenance per row).
- Cite the actual NAIC report title in the YAML header: "Dwelling Fire, Homeowners Owner-Occupied, and Homeowners Tenant and Condominium/Cooperative Unit Owner's Insurance Report: Data for 2022."
- If the planner wants a single-source-per-file YAML, use III's "Facts + Statistics: Homeowners and renters insurance" averages instead — but cite it explicitly.

**Warning signs:** A YAML with `source: "https://content.naic.org/..."` and a CA row with a "NAIC" `notes:` field — CA data is NOT NAIC-published.

### Pitfall 6: FEMA Risk Rating 2.0 decoupled NFIP premium from flood zone

**What goes wrong:** CONTEXT D-16-INS-02 cites "FEMA NFIP flood-zone definitions + private-market actuarial averages" as the source for X/+0%, A/AE/+30%, V/+80%, unknown/+15%. As of **2021-04-01**, FEMA's Risk Rating 2.0 abandoned zone-based pricing — NFIP premiums are now calculated based on property-specific features (elevation, distance to water body, prior claims, etc.), NOT on the FIRM zone designation [VERIFIED: WebSearch summary 2026-05-22; congress.gov/crs-product/IN11777]. Citing "FEMA NFIP" as the source for zone-based multipliers is no longer factually accurate.

**Why it happens:** Pre-2021 NFIP pricing WAS zone-based, and most lender training material + industry rules-of-thumb still use zone-based heuristics. The private flood market (Neptune, Wright, etc.) still uses zone proxies, but each carrier is proprietary.

**How to avoid:**
- Reframe the YAML's `notes:` and `Citation:` to say "**Private-market homeowners-insurance flood-uplift heuristic; NOT a direct NFIP rate citation.** FEMA Risk Rating 2.0 (effective 2021-04-01) decoupled NFIP premium from flood zone. The multipliers below are a representative private-market private-carrier proxy for an end-user-facing v1.1 estimate."
- Cite a concrete proxy source for the multipliers: either a published Neptune Flood market overview, an III "Spotlight on: Flood insurance" page, or an actuarial-society survey. WebSearch found a Neptune Flood "market overview" referencing zone-based private-rate adjustments (Zone X: 0.60, Zone AE: 0.85, Zone VE: 1.05) — but those are private-flood-vs-NFIP comparisons, NOT homeowners-policy uplifts, so they're not a direct citation either.
- Adjust the multipliers if the chosen source publishes different ratios. The CONTEXT's X/+0, A,AE/+30, V/+80, unknown/+15 split is reasonable as a first-pass design; without a single-citable source the planner should keep the values conservative and clearly tag them as "v1.1 representative estimate."

**Warning signs:** Any YAML citation reading "FEMA NFIP zone-based rates" or "NFIP rate increase by zone" — these are no longer accurate post-2021.

### Pitfall 7: CEA premium-per-$1000-coverage doesn't map cleanly to a flat add-on

**What goes wrong:** CONTEXT D-16-INS-03 prescribes "flat $ add-ons" for CA / OR / WA earthquake. But CEA's published premium structure is per-$1000 of dwelling coverage (e.g., $3.54/$1000) — a flat $ add-on with no reference to dwelling value will systematically understate premiums for high-value homes and overstate for low-value homes [VERIFIED: WebSearch CEA premium calculator 2026-05-22]. The CEA-reported average premium of ~$1,770 (for a $500k home) is itself coverage-dependent.

**Why it happens:** Flat-$ is simpler to publish + verify; coverage-percentage requires the listing's dwelling-value estimate (zestimate or list-price) to be in scope at the lookup call site. The simpler model trades accuracy for testability.

**How to avoid:**
- Acknowledge the simplification in the YAML `notes:` field: "Flat $ add-on per state. Real-world earthquake premiums are coverage-dependent (CEA: $3-4/$1000); the flat values below approximate a $500k-$700k single-family home and are tagged as estimates."
- Cite CEA's published $/$1000 rate alongside the flat number to allow future v1.2 upgrade to coverage-percentage.
- Set CA's flat value to roughly $1,800 (the WebSearch-reported CEA average for $500k coverage; planner refines); OR/WA lower, e.g., $400-$800 (lower seismic, mostly private-market).

**Warning signs:** A test that asserts a $5M property gets the same earthquake add-on as a $400k property — that's the v1.1 design (flag in fixture comments) but should not be hidden.

### Pitfall 8: Phase 14's existing PMI test assertion at `tests/test_property_analysis.py:481` is a STRING equality, not a prefix match

**What goes wrong:** The test `test_conv_pmi_warning_surfaces` asserts `"PMI-RATE-ESTIMATED-0.0075" in cell.eligible_reasons` (exact-string membership). Phase 16 retires the `0.0075` tag in favor of `PMI-RATE-ESTIMATED-MGIC-{ltv}-{fico}` (variable). A simple find-replace from `PMI-RATE-ESTIMATED-0.0075` to `PMI-RATE-ESTIMATED-MGIC` will break the assertion (the cell now contains, e.g., `"PMI-RATE-ESTIMATED-MGIC-95-740"`, not `"PMI-RATE-ESTIMATED-MGIC"`).

**Why it happens:** The assertion uses exact-string membership; the new tag is parameterized.

**How to avoid:** Rewrite the assertion to use a substring or prefix match: `assert any(r.startswith("PMI-RATE-ESTIMATED-MGIC-") for r in cell.eligible_reasons)`. Same fix at the other 6 hit sites in `tests/test_property_analysis.py` (lines 1101, 1116, 1120, 1299, 1319, 1326). Don't forget the 3 golden fixtures: the `eligible_reasons` arrays in `tests/fixtures/property_analysis/condo_with_hoa_seattle.json` (lines 80, 96) hard-code `"PMI-RATE-ESTIMATED-0.0075"` — those fixtures must be regenerated with the new tag values, hand-calc-anchored to the FICO 740 × LTV 95 cell in the new YAML.

**Warning signs:** Test failures of the form `assert "PMI-RATE-ESTIMATED-0.0075" in [..., "PMI-RATE-ESTIMATED-MGIC-95-740"]` — exact-match against parameterized tag.

### Pitfall 9: `data/reference/property-analysis-heuristics.yml` filename collision risk with ROADMAP SC #1

**What goes wrong:** ROADMAP SC #1 says "`data/reference/property-analysis-heuristics.yml` ships PMI rate tables (PMI by LTV band × FICO band — sourced from major-lender published schedules), FHA MIP defaults (upfront 1.75% + monthly 0.55-0.85% per LTV), VA funding fee defaults (per first-use × DP × veteran-type), jumbo cutoffs by county (2026 FHFA conforming limits — baseline $766k 1-unit, $1.149M high-cost)." A planner who reads SC #1 literally might think Phase 16 ALSO ships FHA MIP / VA funding fee / jumbo cutoffs in this single YAML — but those are ALREADY shipped in Phase 2 as separate files. CONTEXT D-16-FILE-01 clarifies: "Existing `data/reference/fha-mip-rates.yml`, `va-funding-fees.yml`, `conforming-limits-2026.yml` stay as-is — Phase 2's structure already covers FHA / VA / jumbo per ROADMAP SC #1's 'FHA MIP defaults, VA funding fee defaults, jumbo cutoffs' (those are already shipped). Phase 16 only ADDS the PMI + insurance tables."

**Why it happens:** ROADMAP was written before Phase 2's plan-packaging fully crystallized; SC #1 describes the end-state contents of the YAMLs but doesn't specify which phase ships what.

**How to avoid:** `data/reference/property-analysis-heuristics.yml` ships **PMI table ONLY**. Do NOT merge FHA MIP / VA / jumbo content into it. The 5 ROADMAP SCs are descriptive of the overall reference-data state, not Phase 16-only deliverables.

**Warning signs:** A Phase 16 plan task that says "extract FHA MIP rates from `fha-mip-rates.yml` into `property-analysis-heuristics.yml`" — that's a violation of D-16-FILE-01.

### Pitfall 10: Decimal coercion edge — `Decimal("0.80")` exactly at the PMI threshold

**What goes wrong:** Phase 14's PMI trigger at `lib/property_analysis.py:652` uses `provisional_ltv > Decimal("0.80")` — strictly greater. A cell at LTV exactly 0.80 does NOT trigger PMI. The Phase 16 PMI YAML's first row has `ltv_min: "0.80"` — and the lookup helper's bucket convention (per `lib/rules/fha_mip.py:155-160`) treats `ltv_min != 0.00` as EXCLUSIVE lower bound. Both halves agree: LTV > 0.80 triggers PMI; PMI table cell `ltv_min=0.80, ltv_max=0.85` covers `0.80 < ltv <= 0.85`. Good — but a planner who copies the FHA-MIP convention without verifying could introduce an off-by-one bug.

**Why it happens:** FHA MIP's lowest LTV bucket (`ltv_min: "0.00"`) special-cases as INCLUSIVE; PMI doesn't have a 0.00 bucket (PMI doesn't apply below 80%). The planner must explicitly NOT enable that special-case in `pmi.py`.

**How to avoid:** The `lib/rules/pmi.py:lookup_rate()` helper drops the `if ltv_min == Decimal("0.00"):` branch entirely (or asserts `ltv_min > Decimal("0.00")`). All buckets are exclusive-lower / inclusive-upper. Test fixture at LTV exactly 0.80 should produce a cap-fallback (out of grid → worst row), NOT a 760+ × 80-85 cell hit.

**Warning signs:** A test that passes `Decimal("0.80")` for `ltv` and expects the first row to match — that's a misread of the bucket convention.

## Runtime State Inventory

> Phase 16 is a YAML-addition + small-module + Phase 14 wire-in. It does involve renaming/retiring one tag (`PMI-RATE-ESTIMATED-0.0075`) and one Final constant (`_CONV_PMI_ANNUAL_RATE`). The inventory below addresses what survives a code edit.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | `tests/fixtures/property_analysis/sfh_conforming_king_county.json`, `condo_with_hoa_seattle.json`, `sfh_jumbo_bay_area.json` each contain a `"warnings": ["PMI-RATE-ESTIMATED"]` array, and `condo_with_hoa_seattle.json` carries `"PMI-RATE-ESTIMATED-0.0075"` strings in `eligible_reasons` (lines 80, 96) AND in the prose `notes` field (line 6). DuckDB `analyzed_listings` table (Phase 13 PERS-08) may have persisted real analyzed listings with the old `eligible_reasons` JSON strings — these are user-data not test fixtures. | Data migration: update the 3 golden-fixture JSON files (hand-edit; values are hand-calc anchors so new MGIC rates change the numeric PITI/DTI calculations downstream — full re-anchoring required, not just tag rename). DuckDB rows ARE persisted user analysis records — new analyses get the new tags; old rows keep the old tags. CONTEXT explicitly does not call for a DuckDB migration here; the snapshot_hash + analyzed_at timestamp differentiate vintages already (Phase 13 D-13-REANALYSIS-01). |
| **Live service config** | None. mortgage-ops has no live SaaS dashboards / n8n workflows / external service that references `PMI-RATE-ESTIMATED-0.0075` by name. | None — verified by inspection of project structure. |
| **OS-registered state** | None. No Task Scheduler / cron / launchd / pm2 entries reference Phase 14 reason codes. | None — verified by inspection. |
| **Secrets / env vars** | None. mortgage-ops keeps no secrets that reference reason codes by name. FRED API key is the only secret (per Phase 12) and is unaffected. | None. |
| **Build artifacts** | Python `__pycache__` directories under `lib/property_analysis.py` and `lib/rules/` carry compiled `.pyc` files referencing the old constant name `_CONV_PMI_ANNUAL_RATE`. Stale across the rename. | Automatically cleared by `pytest` next run; no manual action. (uv-managed venv recompiles on import.) |

**Search-and-destroy targets for tag retirement** (grep `"PMI-RATE-ESTIMATED-0.0075"`):
- `lib/property_analysis.py` — 5 occurrences (lines 23, 154, 296 inside docstrings; line 654 the actual `eligible_reasons.append`; line 1505 the warning aggregator substring — substring stays unchanged since it's `PMI-RATE-ESTIMATED` not the full literal)
- `tests/test_property_analysis.py` — 4 literal assertions (lines 481, 1101-1102, 1116, 1120, 1299, 1319, 1326 — collapsed by grep to 7 distinct positions; planner counts each)
- `tests/fixtures/property_analysis/condo_with_hoa_seattle.json` — 4 occurrences (notes line 6, _meta citation line 8, eligible_reasons lines 80 and 96)
- `tests/fixtures/property_analysis/sfh_conforming_king_county.json` — 1 occurrence (warnings array line 130 — `"PMI-RATE-ESTIMATED"` substring only, no `-0.0075`)
- `tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` — 1 occurrence (warnings array line 142)
- `lib/property_analysis.py` line 1505 — `"PMI-RATE-ESTIMATED" in r` — leave the SUBSTRING check intact (it matches both old `-0.0075` and new `-MGIC-*` tags); add a parallel substring for `"PMI-RATE-CAPPED"` so capped cells also surface as a top-level warning. The top-level warning string in `report.warnings` should become `"PMI-RATE-ESTIMATED-MGIC"` (not `PMI-RATE-ESTIMATED-0.0075`) to preserve the "1 type per warning entry" dedup discipline.

## Common Pitfalls (continued)

(See main Common Pitfalls section above — Pitfalls 1-10 documented.)

## Code Examples

### Example 1: `lib/rules/pmi.py` skeleton (verified-pattern from `lib/rules/fha_mip.py`)

```python
# Source: lib/rules/fha_mip.py L48-167 (analog module structure)
"""Conventional PMI annual rate lookup (4x4 LTV x FICO MGIC abridged schedule).

Citation: MGIC Rate Card "Standard MI" (Borrower-Paid Monthly Premium)
  — industry-published rate schedule, NOT a regulatory predicate. Phase 16
  ships an abridged 4x4 subset (16 cells); the full MGIC 8x7 schedule is
  deferred to v2 per CONTEXT D-16-PMI-01. Out-of-band combos return the
  worst-cell rate per D-16-PMI-02 (no raise, no interpolation).
Source URL: <planner pins exact MGIC bulletin PDF + revision number>
Effective: <planner pins to bulletin publication date>

What this predicate decides:
  Given a representative FICO score and an LTV ratio at origination,
  return the annual PMI rate (Decimal) + a reason tag for the
  eligible_reasons soft-signal surface in lib.property_analysis.

  In-band: tag = "PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}"
  Out-of-band (FICO < 700 OR LTV > 97 OR LTV <= 80): cap at worst cell,
    tag = "PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}"

Inputs:
    fico: int (300..850; lib/household.py L61 constrains this)
    ltv:  Decimal (financed_principal / appraised_value at origination)

Outputs:
    PMILookupResult — frozen Pydantic:
        annual_rate: Rate
        reason_tag: str
"""

from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from lib.models import Rate
from lib.rules._loader import load_reference


class PMILookupResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    annual_rate: Rate
    reason_tag: str


def lookup_rate(fico: int, ltv: Decimal) -> PMILookupResult:
    ref = load_reference("property-analysis-heuristics")
    table = ref["pmi_annual_rate_table"]
    for row in table:
        fico_min = int(row["fico_min"])
        fico_max = int(row["fico_max"])
        ltv_min = Decimal(row["ltv_min"])
        ltv_max = Decimal(row["ltv_max"])
        # All buckets exclusive-lower / inclusive-upper (Pitfall 10).
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

### Example 2: `lib/rules/insurance.py` skeleton

```python
# Source: lib/rules/fha_mip.py L48-167 (analog) + lib/rules/va_funding_fee.py (multi-section consumer)
"""Default homeowners-insurance annual estimate (state base + flood + earthquake).

Citation: Composite — NAIC Homeowners Insurance Report (Data for 2022,
  published 2025-05-21) for 48 states + DC; III state averages for CA + TX
  (which NAIC does not publish via statistical agents); private-market
  homeowners-policy flood uplift heuristic (NOT FEMA NFIP — Risk Rating 2.0
  decoupled NFIP premium from FIRM zone in 2021); CEA + PNW private-market
  averages for CA/OR/WA earthquake add-ons.

  This is NOT a regulatory predicate — it is a per-state heuristic estimate
  that fires only when listing.insurance_estimate_annual is None. Reports
  flag every estimated value via "INSURANCE-ESTIMATED-NAIC-{state}-{zone}"
  in eligible_reasons per CONTEXT D-16-INS-04.

Source URL: https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022
  (additional URLs documented in data/reference/insurance-estimate-defaults.yml notes)
Effective: 2025-05-21 (NAIC report publication date)

What this predicate decides:
  Given a USPS state code and an optional FEMA flood zone, return the
  estimated annual homeowners insurance premium (Money). Composition:
    annual = state_base * flood_zone_multiplier + earthquake_state_addon

  For state not in {CA, OR, WA}, earthquake_state_addon = Decimal("0.00").
  For flood_zone is None or not in {X, A, AE, V}, uses "unknown" multiplier.

Inputs:
    state: str (2-char USPS code; lib.rules.insurance maps household.state_fips -> USPS)
    flood_zone: str | None (FEMA FIRM zone; None for missing data)

Outputs:
    Money (Decimal; annual premium quantized to cents at the boundary)
"""

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


def lookup_default(state: str, flood_zone: str | None) -> Money:
    """Return estimated annual homeowners-insurance premium.

    state: 2-char USPS code.
    flood_zone: FEMA FIRM zone; None/unknown -> "unknown" multiplier (1.15).
    """
    ref = load_reference("insurance-estimate-defaults")
    # State base
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

    # Flood multiplier
    zone_key = flood_zone if flood_zone in {"X", "A", "AE", "V"} else "unknown"
    mult_row = next(
        (r for r in ref["flood_zone_multipliers"] if r["zone"] == zone_key),
        None,
    )
    multiplier = Decimal(mult_row["multiplier"]) if mult_row else Decimal("1.00")

    # Earthquake add-on (CA/OR/WA only; silent 0 otherwise)
    eq_row = next(
        (r for r in ref["earthquake_state_addons"] if r["state"] == state),
        None,
    )
    eq_addon = Decimal(eq_row["flat_addon_annual"]) if eq_row else Decimal("0.00")

    return quantize_cents(base * multiplier + eq_addon)
```

### Example 3: Phase 14 wire-in diff (PMI block)

```python
# Source: lib/property_analysis.py L645-657 (current state) — EDIT shown as diff comments
# Step 3 — initial MI / financed-principal calc per program
loan_type: Literal["fixed", "fha", "va"]
financed_principal: Decimal
monthly_mi: Decimal
if program in ("Conv30", "Conv15", "Jumbo30"):
    loan_type = "fixed"
    provisional_ltv = base_loan_amount / price
    if provisional_ltv > Decimal("0.80"):
        # BEFORE (line 653):
        # monthly_mi = quantize_cents(base_loan_amount * _CONV_PMI_ANNUAL_RATE / Decimal("12"))
        # eligible_reasons.append("PMI-RATE-ESTIMATED-0.0075")
        # AFTER (Phase 16 wire-in per D-16-WIRE-02):
        from lib.rules.pmi import lookup_rate  # at module top, not inside function
        pmi_result = lookup_rate(household.fico, provisional_ltv)
        monthly_mi = quantize_cents(base_loan_amount * pmi_result.annual_rate / Decimal("12"))
        eligible_reasons.append(pmi_result.reason_tag)
    else:
        monthly_mi = Decimal("0.00")
    financed_principal = base_loan_amount
```

### Example 4: Phase 14 wire-in diff (insurance block) — handles Pitfall 2 + Pitfall 3

```python
# Source: lib/property_analysis.py L701-705 (current state)
# Step 6 — escrow components (B-4: guarded unwrap)
monthly_tax = quantize_cents(_unwrap_provenanced(listing.tax_annual) / Decimal("12"))

# BEFORE (lines 703-705):
# monthly_insurance = quantize_cents(
#     _unwrap_provenanced(listing.insurance_estimate_annual) / Decimal("12")
# )

# AFTER (Phase 16 wire-in per D-16-WIRE-01):
pm = listing.insurance_estimate_annual
if pm is not None and pm.value is not None:
    annual_insurance = pm.value
else:
    from lib.rules.insurance import lookup_default, fips_to_usps
    state_usps = fips_to_usps(household.state_fips)
    # Pitfall 3: PropertyListing has NO flood_zone field as of v1.1; pass None.
    # Future v1.2 may add the field; fallback uses "unknown" multiplier.
    flood_zone = None
    annual_insurance = lookup_default(state_usps, flood_zone)
    eligible_reasons.append(
        f"INSURANCE-ESTIMATED-NAIC-{state_usps}-{flood_zone or 'unknown'}"
    )
monthly_insurance = quantize_cents(annual_insurance / Decimal("12"))

monthly_hoa = quantize_cents(_unwrap_provenanced(listing.hoa_monthly))
```

### Example 5: Phase 14 wire-in diff (warnings aggregator)

```python
# Source: lib/property_analysis.py L1504-1506 (current state)
# BEFORE:
# if any("PMI-RATE-ESTIMATED" in r for c in matrix.cells for r in c.eligible_reasons):
#     warnings.append("PMI-RATE-ESTIMATED")

# AFTER (Phase 16 update per D-16-WIRE-03; recommend a Final constant for grep-discoverability):
_PMI_WARNING_PREFIXES: Final[dict[str, str]] = {
    "PMI-RATE-ESTIMATED-MGIC": "PMI-RATE-ESTIMATED-MGIC",
    "PMI-RATE-CAPPED-MGIC": "PMI-RATE-CAPPED-MGIC",
    "INSURANCE-ESTIMATED-NAIC": "INSURANCE-ESTIMATED-NAIC",
}

# In analyze():
for prefix, warning_label in _PMI_WARNING_PREFIXES.items():
    if any(
        prefix in r
        for c in matrix.cells
        for r in c.eligible_reasons
    ):
        warnings.append(warning_label)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline Final constant for v1.1 estimated values (e.g., `_CONV_PMI_ANNUAL_RATE`) | YAML-driven lookup via `lib/rules/*.py` predicate + `data/reference/*.yml` | Phase 16 (this phase) | ROADMAP SC #5 closed: "no inline constants for any regulatory threshold." Annual refresh = YAML edit. |
| FEMA NFIP zone-based premium pricing (X→cheap, AE→middle, V→expensive) | FEMA Risk Rating 2.0 property-specific pricing (elevation, distance to water, claims history) | 2021-04-01 (FEMA Risk Rating 2.0 effective) | Phase 16's flood-multiplier YAML is a **private-market homeowners-uplift heuristic, NOT a citable FEMA NFIP rate**. Documented in YAML notes + module docstring. |
| NAIC Homeowners Insurance Report 2018 data (published 2021-01-13) | NAIC Homeowners Insurance Report 2022 data (published 2025-05-21) | NAIC release of 2022 data on 2025-05-21 | Phase 16 cites 2022-data report. California + Texas still excluded from NAIC dataset; secondary source (III, Bankrate, state DOI) needed for those 2 rows. |
| Float-based YAML scalars (PyYAML default) | Quoted-Decimal scalars (Phase 2 Pitfall 1 defense) | Phase 2 D-02 | Phase 16 inherits — every numeric scalar in both new YAMLs MUST be quoted. |
| Hand-rolled YAML loader per predicate | Shared `lib/rules/_loader.py:load_reference()` with `lru_cache` + `_check_staleness` | Phase 2 D-02 | Phase 16 reuses; no new loader code. |
| Single-source-per-row YAML | Composite-source-per-row with `notes:` field per row | Phase 16 (for insurance) | NAIC + III + state DOI mixed-provenance unavoidable for the insurance YAML. |

**Deprecated / outdated:**
- "MGIC abridged rate card" as a stable URL — MGIC's site refactored multiple times; the planner must pin the exact bulletin PDF + revision number, not the landing page.
- "NAIC 2024" verbiage in CONTEXT — the most recent report is "Data for 2022, published 2025-05-21." Adjust YAML notes accordingly.
- "FEMA NFIP flood-zone uplift" — Risk Rating 2.0 deprecated zone-based pricing in 2021.
- `_CONV_PMI_ANNUAL_RATE: Final[Decimal] = Decimal("0.0075")` — retired by this phase; reference removed from module docstring (lines 21-23) and constant declaration (line 151).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MGIC publishes a "Standard MI" abridged 4-FICO-band × 4-LTV-band rate card. The 4 FICO bands are exactly `760+`, `740-759`, `720-739`, `700-719` and the 4 LTV bands are exactly `80.01-85`, `85.01-90`, `90.01-95`, `95.01-97`. | Standard Stack, D-16-PMI-01 | If MGIC's actual published bands differ (e.g., breakpoint at 760 vs 780, or 7 LTV columns vs 4), the YAML's band labels and reason-tag pattern require adjustment. Plan task should "verify exact MGIC band labels at YAML-write time and update reason-tag templates accordingly." | [ASSUMED] — MGIC's website (mgic.com/rates/rate-cards) returned 404 on the cached BPMI PDF URL in WebFetch 2026-05-22; current bulletin shape inferred from industry-standard MGIC schedules. The planner MUST verify directly against a fetched bulletin PDF before pinning band labels. |
| A2 | NAIC's "Data for 2022" Homeowners Insurance Report is the most recent publication and is the appropriate source for 48 states + DC. California and Texas are systematically excluded from this dataset and require III or state-DOI substitution. | Common Pitfalls §5, Open Questions §1 | If NAIC publishes a 2023 or 2024 report before Phase 16 ships, the planner should use that newer report. If CA + TX exclusion is wrong (NAIC's 2022 release did include them via a different channel), the YAML can avoid the multi-source per-row notes. | [VERIFIED: WebFetch of content.naic.org news release 2026-05-22 confirmed 2022 data, published 2025-05-21, CA+TX excluded]. |
| A3 | FEMA's Risk Rating 2.0 (effective 2021-04-01) abandoned zone-based NFIP premium pricing, meaning a citation reading "FEMA NFIP flood zone X → +0%, A/AE → +30%, V → +80%" is no longer factually accurate. | Common Pitfalls §6, Open Questions §3 | If Risk Rating 2.0 is later revoked, or if FEMA reintroduces zone-based pricing, the YAML's `Citation:` can re-cite FEMA directly. v1.1's documented disclaimer is correct as of 2026-05-22. | [VERIFIED: WebSearch 2026-05-22 — multiple sources including congress.gov/crs-product/IN11777 confirm zone abandonment]. |
| A4 | CEA (California Earthquake Authority) publishes earthquake premium as $/$1000 coverage (~$3.54/$1000), making a flat-$ add-on a v1.1 simplification that systematically misprices high/low-value homes. | Common Pitfalls §7 | If CEA also publishes flat-$ averages by home-value tier, the YAML can carry per-tier flat values. v1.1 design ships single flat value approximating $500-700k home; document the simplification. | [VERIFIED: WebSearch CEA premium calculator 2026-05-22]. |
| A5 | Oregon and Washington earthquake premiums are non-CEA (private-market) with no single canonical source. The planner will need to use NW Insurance Council data, Oregon DFR resources, or representative private-carrier surveys. | Architecture Patterns §Pattern 3, Open Questions §4 | If a canonical OR/WA earthquake source is found, citation tightens. Without one, the YAML cites a composite "NW Insurance Council survey + Oregon DFR + Washington OIC" footprint. | [ASSUMED — partial verification via WebSearch 2026-05-22]. |
| A6 | The exact values for the flood multipliers (X→+0%, A/AE→+30%, V→+80%, unknown→+15%) in CONTEXT are "starting design assumptions"; CONTEXT explicitly says planner may refine to "whatever the source publishes." | Architecture Patterns §Pattern 3 | Numbers chosen affect downstream PITI cell values; test fixtures hand-calc-anchored to these multipliers must be recomputed if planner changes them. | [VERIFIED: CONTEXT D-16-INS-02 explicitly calls these "a starting design assumption"]. |
| A7 | `PropertyListing` does NOT carry a `flood_zone` field; CONTEXT's claim "PropertyListing has flood_zone field" is incorrect for the current Phase 13 model. | Common Pitfalls §3 | If user wants to ADD `flood_zone` to PropertyListing as part of Phase 16, that violates Phase 13's frozen-model lock and CONTEXT D-16-WIRE-01's "PropertyListing model (Phase 13) is NOT modified" rule. Planner should escalate to user, not silently add. | [VERIFIED: `lib/property_listing.py` read 2026-05-22 — full field list confirms no flood_zone]. |
| A8 | The `_ALLOWED_REASONS` constant CONTEXT D-16-WIRE-03 references at `lib/property_analysis.py:296` does NOT exist as a Python constant; line 296 is a docstring. The actual "allow-list" surface is the substring-match aggregator at line 1505 + 7 literal-string test assertions in `tests/test_property_analysis.py` + 3 golden-fixture JSON files. | Common Pitfalls §1, D-16-WIRE-03 | If planner edits a phantom `_ALLOWED_REASONS` constant, the edits go nowhere and tests still fail. Planner must update the actual surfaces enumerated in Pitfall 1. | [VERIFIED: grep across `lib/property_analysis.py` + `lib/property_verdict.py` + `tests/test_property_*.py` 2026-05-22]. |
| A9 | The reasons-allow-list test (Phase 14 verification) referenced in input pin `files_to_read` and CONTEXT specifics does not exist as a dedicated test file. The closest analogue is `test_conv_pmi_warning_surfaces` at `tests/test_property_analysis.py:475-481` (literal-string assertion). | Common Pitfalls §1 + §8 | A planner who searches for `test_reasons_allow_list` or similar finds nothing; the actual gate is multiple inline assertions. | [VERIFIED: grep for `ALLOW\|allow_list\|allowed_reasons\|reasons_allow` across `tests/` 2026-05-22 returned no matches in test files]. |
| A10 | macOS Finder-duplicate files `fha_mip 2.py` + `fha_mip 3.py` already exist in `lib/rules/`; the citation-coverage meta-test globs `*.py` and would also pick up a `pmi 2.py` or `insurance 2.py` if accidentally created. | Common Pitfalls §4 | Planner who runs the meta-test pre-commit will see existing fha_mip duplicate failures (out of Phase 16 scope per Phase 14 verifier); must be careful NOT to delete the fha_mip duplicates as a side-effect. | [VERIFIED: `ls lib/rules/` 2026-05-22]. |

**Risk summary:** A1, A5 require live PDF capture by the planner before YAML pinning. A2, A3, A4, A6, A7, A8, A9, A10 are verified.

## Open Questions

1. **Which NAIC report version to cite, given CA + TX exclusions and 3-year publication lag?**
   - What we know: NAIC Homeowners Insurance Report "Data for 2022" published 2025-05-21; CA + TX use a separate submission channel and are typically excluded from the published averages tables.
   - What's unclear: Whether the planner should cite a unified NAIC-derived 49-row dataset + 2-row III-derived (CA, TX) supplement, OR ship an all-rows III-derived table for consistency (single citable source).
   - Recommendation: Use NAIC for the 49 covered states + DC; use III "Facts + Statistics: Homeowners and renters insurance" averages for CA + TX. Document the per-row source mix in the `notes:` field per row. Single canonical source URL in YAML header.

2. **Which MGIC bulletin / rate card revision to pin?**
   - What we know: MGIC publishes rate cards under `https://www.mgic.com/rates/rate-cards`; the BPMI Monthly rate card has a known PDF naming convention (`71-61284-rate-card-pdf-bpmi-monthly-{month}-{year}.pdf` based on 2018 sample URL); current PDFs require direct MGIC site download or MiQ login.
   - What's unclear: Whether the planner can obtain the current bulletin without MGIC representative contact; the exact form-number / publication-date of the current "Standard MI" abridged rate card.
   - Recommendation: Plan task should include manual download step ("download current MGIC BPMI Standard Borrower-Paid Monthly rate card from mgic.com/rates/rate-cards and archive at `data/reference/sources/mgic-bpmi-monthly-{date}.pdf` for audit"). Verify the 4-FICO-band × 4-LTV-band structure matches Assumption A1 before YAML pinning.

3. **Source for flood-zone uplift multipliers given Risk Rating 2.0?**
   - What we know: FEMA Risk Rating 2.0 (2021-04) decoupled NFIP pricing from FIRM zones. Private-market homeowners insurance often still uses zone-derived rate factors but is carrier-specific. III's "Spotlight on: Flood insurance" provides directional commentary but not a tabular set of homeowners-policy uplifts.
   - What's unclear: Whether to cite a private-carrier filing (e.g., Neptune Flood market overview), a research paper, or a composite "v1.1 representative estimate" with no single citation.
   - Recommendation: Document the multipliers as "v1.1 representative private-market estimate; NOT a direct NFIP/FEMA rate citation" in YAML notes. Keep multipliers conservative (X→+0%, A→+25%, AE→+30%, V→+60-80%, unknown→+15%) — these are insurance-uplift estimates, not flood-policy quotes. Cite a "composite of III + Neptune Flood market overview + Insurance Information Institute spotlight" if the planner wants a defensible-but-acknowledged-approximation citation.

4. **Earthquake add-on dollar values for CA / OR / WA?**
   - What we know: CEA average for a $500k home is ~$1,770/year (2024 data; 6.8% rate increase in January 2025). Oregon: ~$200-$300/year for $300k coverage (2009 survey, likely outdated); Washington: ~$1,200/year for $600k coverage at $2/$1000. National average $800/year.
   - What's unclear: Authoritative 2024-2025 source for OR/WA averages; whether to use $-per-$1000 (more accurate) or flat-$ (simpler) per CONTEXT D-16-INS-03.
   - Recommendation: Use flat-$ per CONTEXT; assume $500-700k home baseline. CA ≈ $1,500-$1,800; OR ≈ $400-$600; WA ≈ $700-$1,000. Document the implied home-value baseline in YAML notes. v1.2 could move to coverage-percentage.

5. **Test fixture hand-calc anchors — which MGIC cells get fixtures?**
   - What we know: Phase 2 RUL pattern is "≥1 fixture per row when feasible; ≥1 fixture per logical edge case always." 16 cells + 1 capped-fallback = 17 distinct test paths.
   - What's unclear: Whether to ship 17 fixtures (one per cell + capped) or 6-8 representative fixtures (corners + capped + 2-3 middle cells).
   - Recommendation: Ship at least 5 fixtures: (a) corner-high-quality: FICO 760+ × LTV 80-85 (lowest rate); (b) corner-low-quality: FICO 700-719 × LTV 95-97 (highest in-band rate); (c) middle: FICO 740-759 × LTV 90-95 (Pachulski-baseline); (d) capped-low-FICO: FICO 680 × LTV 96 (out-of-band, hits cap); (e) capped-high-LTV: FICO 760 × LTV 98 (out-of-band, hits cap). 1:1-to-cell fixtures (16 + 1) preferred if test runtime allows.

6. **Do we expand `lib.rules.insurance.lookup_default` to handle `flood_zone is None`, or assume the caller always passes a non-None value?**
   - What we know: PropertyListing doesn't carry `flood_zone` (Pitfall 3), so the caller always passes None in v1.1. Future v1.2 might add flood_zone to PropertyListing.
   - What's unclear: Whether to ship the multiplier branch for None handling NOW (forward-compat) or defer.
   - Recommendation: Ship the None handling NOW — the "unknown" multiplier row in the YAML is forward-compatible scaffolding. v1.2 only needs to add the flood_zone field to PropertyListing and pass it through; the predicate API is stable.

7. **Verdict-allow-list interaction — does adding a new soft-signal reason to `eligible_reasons` affect the verdict cascade?**
   - What we know: `lib/property_verdict.py:synthesize()` reads `matrix.cells[*].blocker_reasons` and `stress.rows[*].breaches_dti_ceiling` to make verdict decisions. Soft signals in `eligible_reasons` are NOT consumed by the verdict cascade (verified by reading `lib/property_verdict.py` 2026-05-22).
   - What's unclear: Nothing — soft signals are display-only.
   - Recommendation: No verdict-cascade changes required for Phase 16. Verdict stays stable; only the report's "warnings" surface and `eligible_reasons` per-cell carry the new tags.

## Environment Availability

> Phase 16 is pure-code + pure-data; no live external services.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Predicate modules + tests | ✓ | 3.14.3 (system default) | — |
| `uv` package manager | Project tooling | ✓ | 0.11.7 | direct `pip install` |
| `pyproject.toml` declared deps (`pyyaml`, `pydantic`, `pytest`, `python-dateutil`) | Already pinned | ✓ | per `pyproject.toml` | — |
| MGIC rate card PDF (current bulletin) | YAML population | ⚠ | unknown — requires manual download | Use latest archived MGIC bulletin found via search; document in YAML `notes:` |
| NAIC Homeowners Insurance Report 2022 PDF | YAML population (state base premiums) | ⚠ | content.naic.org publication 2025-05-21 | III state averages or state-DOI publications |
| CEA Public Annual Report or Premium Calculator | YAML population (CA earthquake add-on) | ✓ | accessible at earthquakeauthority.com | None needed |
| FEMA Risk Rating 2.0 documentation | Module docstring citation for "NOT FEMA zone-based" disclaimer | ✓ | fema.gov/flood-insurance/risk-rating | — |

**Missing dependencies with no fallback:** None blocking.

**Missing dependencies with fallback:** MGIC rate card requires manual download — planner task includes the download step.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0 [VERIFIED: pyproject.toml line 20] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths, pythonpath, addopts) |
| Quick run command | `uv run pytest tests/test_rules/test_pmi.py tests/test_rules/test_insurance.py -x` |
| Full suite command | `uv run pytest tests/` |
| Citation coverage gate | `uv run pytest tests/test_rules/test_citation_coverage.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REF-09 | `property-analysis-heuristics.yml` loads with `source:` + `effective:` | unit | `uv run pytest tests/test_rules/test_pmi.py::test_yaml_loads_with_metadata -x` | ❌ Wave 0 |
| REF-09 | PMI lookup returns correct rate for FICO 760 × LTV 95 in-band | unit | `uv run pytest tests/test_rules/test_pmi.py::test_lookup_in_band_760_95 -x` | ❌ Wave 0 |
| REF-09 | PMI lookup returns capped rate + correct tag for FICO 680 × LTV 96 out-of-band | unit | `uv run pytest tests/test_rules/test_pmi.py::test_lookup_out_of_band_caps -x` | ❌ Wave 0 |
| REF-09 | PMI predicate has Citation: / Source URL: / Effective: in docstring | meta | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring[pmi] -x` | ✅ (auto-discovers via filesystem glob) |
| REF-09 | PMI predicate has at least one fixture file | meta | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_at_least_one_fixture[pmi] -x` | ✅ (auto-discovers; needs ≥1 `pmi_*.json` fixture) |
| REF-10 | `insurance-estimate-defaults.yml` loads with `source:` + `effective:` | unit | `uv run pytest tests/test_rules/test_insurance.py::test_yaml_loads_with_metadata -x` | ❌ Wave 0 |
| REF-10 | State base lookup returns correct value for WA | unit | `uv run pytest tests/test_rules/test_insurance.py::test_lookup_state_base_wa -x` | ❌ Wave 0 |
| REF-10 | Composition: state + flood multiplier + earthquake for WA × zone-X | unit | `uv run pytest tests/test_rules/test_insurance.py::test_composition_wa_zone_x -x` | ❌ Wave 0 |
| REF-10 | Earthquake silent-zero for non-CA/OR/WA state | unit | `uv run pytest tests/test_rules/test_insurance.py::test_earthquake_silent_zero_for_other_state -x` | ❌ Wave 0 |
| REF-10 | Insurance predicate citation hygiene | meta | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring[insurance] -x` | ✅ (auto-discovers) |
| REF-09+10 (regression) | Phase 14 full suite green after wire-in | integration | `uv run pytest tests/test_property_analysis.py tests/test_property_verdict.py -x` | ✅ (needs fixture re-anchoring) |
| REF-09+10 (regression) | `test_conv_pmi_warning_surfaces` passes with new MGIC tag pattern | unit | `uv run pytest tests/test_property_analysis.py::test_conv_pmi_warning_surfaces -x` | ✅ (assertion must be rewritten to `startswith("PMI-RATE-ESTIMATED-MGIC-")`) |
| REF-09+10 (regression) | `test_analyze_warnings_dedup_pmi_estimated` passes with new warning aggregator | unit | `uv run pytest tests/test_property_analysis.py::test_analyze_warnings_dedup_pmi_estimated -x` | ✅ (warning label update + dedup logic still valid) |
| Smoke | Full module import surface intact | smoke | `uv run python -c "from lib.rules.pmi import lookup_rate; from lib.rules.insurance import lookup_default, fips_to_usps"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_rules/test_pmi.py tests/test_rules/test_insurance.py -x` (~1s expected)
- **Per wave merge:** `uv run pytest tests/test_rules/ tests/test_property_analysis.py tests/test_property_verdict.py -x` (~6-10s expected)
- **Phase gate:** Full suite green via `uv run pytest tests/` (645+ tests) before `/gsd-verify-work` runs

### Wave 0 Gaps

- [ ] `tests/test_rules/test_pmi.py` — covers REF-09 (PMI lookup + capping + citation hygiene). Must include hand-calc fixtures for the 5 representative cells from Open Question §5.
- [ ] `tests/test_rules/test_insurance.py` — covers REF-10 (state base + flood multiplier + earthquake add-on + FIPS→USPS + silent-zero-non-quake-state).
- [ ] `tests/fixtures/rules/pmi_*.json` — at least 5 fixture files matching the citation-coverage meta-test's `pmi_*.json` glob; ideally 16+1 = 17 (one per cell + capped fallback).
- [ ] `tests/fixtures/rules/insurance_*.json` — at least 3 fixture files: WA+X (Pachulski baseline), CA+AE (high-flood high-quake), TX+unknown (non-quake state, missing flood data).
- [ ] `data/reference/property-analysis-heuristics.yml` — PMI 4×4 + capped-fallback schema. Frozen as test-only YAML at Wave 0 with placeholder values; real values populated in a dedicated planner-sourced task post-Wave 0.
- [ ] `data/reference/insurance-estimate-defaults.yml` — state base + flood multipliers + earthquake add-ons schema; same placeholder-to-real workflow.
- [ ] `lib/rules/pmi.py` — predicate module with required docstring header + `lookup_rate()`.
- [ ] `lib/rules/insurance.py` — predicate module with required docstring header + `lookup_default()` + `fips_to_usps()` + `_FIPS_TO_USPS` constant.

## Security Domain

> `security_enforcement: true` in `.planning/config.json`; ASVS Level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user auth surface in Phase 16. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Read-only library functions; no privilege-affecting changes. |
| V5 Input Validation | yes | Pydantic v2 strict mode for any output model (Money/Rate aliases reject floats); range checks on FICO (300..850 inherited from `lib/household.py`); state-FIPS pattern check via `_FIPS_TO_USPS` lookup (KeyError on unknown); state-USPS exact-match. The `_loader.py` already validates the YAML filename pattern (`^[a-z0-9][a-z0-9-]*$`) at L31 to defend against path-traversal payloads. |
| V6 Cryptography | no | No crypto. |
| V10 Malicious Code | yes | `yaml.safe_load` only (Phase 2 D-... ASVS V10 mitigation; `_loader.py:70` already enforces). Phase 16 inherits — no additional surface. |
| V11 Business Logic | yes | One-predicate-per-citation discipline + hand-calc-anchored test fixtures + citation-coverage meta-test gate prevent silent introduction of unsourced regulatory values. Phase 2 RUL precedent. |

### Known Threat Patterns for {python + pyyaml + pydantic}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PyYAML float-coercion of unquoted numeric scalars (Pitfall 1) | Tampering | Quoted-Decimal YAML scalars + `Decimal(str)` boundary coercion in every consumer. |
| PyYAML arbitrary-object deserialization via `yaml.load` | Tampering / Execution | `yaml.safe_load` only — enforced at `_loader.py:70`. |
| Path traversal in `load_reference(name)` (e.g., `name="../../etc/passwd"`) | Information Disclosure | Name regex `^[a-z0-9][a-z0-9-]*$` enforced at `_loader.py:63-68`. New YAMLs use lowercase-hyphen-only stems (`property-analysis-heuristics`, `insurance-estimate-defaults`). |
| Stale regulatory data silently used as current | Repudiation | `StaleReferenceWarning` at 12 months on `effective:` field — loud-by-default. NAIC 2022-data report (published 2025-05-21) will fire the warning in 2026-05-21+. |
| Decimal vs float mixing introducing precision error in PMI/insurance | Tampering | Money discipline non-negotiable per CLAUDE.md; Pydantic strict-mode rejects floats on Money/Rate fields. |
| Unverified citation in predicate docstring (claim without URL) | Repudiation | Citation-coverage meta-test asserts `Citation:` + `Source URL:` + `Effective:` + at least one http(s) URL in every predicate module docstring. |

## Sources

### Primary (HIGH confidence — VERIFIED in this session)

- **`lib/rules/_loader.py`** — Phase 2 frozen loader; lru_cache + safe_load + `_check_staleness`. Read 2026-05-22.
- **`lib/rules/fha_mip.py`** — Direct analog for `lib/rules/pmi.py` module shape (citation header, range-based lookup, Decimal-from-string boundary). Read 2026-05-22.
- **`data/reference/fha-mip-rates.yml`** — Direct analog for `property-analysis-heuristics.yml` shape (quoted-Decimal scalars, per-file source/effective/notes, range-bucket rows). Read 2026-05-22.
- **`data/reference/va-funding-fees.yml`** — Multi-section YAML precedent (`purchase`, `flat_fees`, `exemption` blocks) — analog for `insurance-estimate-defaults.yml`'s 3-section layout. Read 2026-05-22.
- **`data/reference/conforming-limits-2026.yml`** — Subset-shipping with `notes:` documentation precedent (Phase 2 D-04 / D-06). Read 2026-05-22.
- **`tests/test_rules/test_fha_mip.py`** — Direct analog for `tests/test_rules/test_pmi.py` test shape (hand-calc anchored fixtures, 1:1 citation mapping). Read 2026-05-22 (first 100 lines).
- **`tests/test_rules/test_citation_coverage.py`** — Meta-test that gates citation hygiene + fixture-existence for every `lib/rules/*.py` file. Read 2026-05-22.
- **`lib/property_analysis.py`** — Read full Phase 14 surface 2026-05-22; verified absence of `_ALLOWED_REASONS` constant; confirmed `_unwrap_provenanced` semantics; located all 5 retired-tag occurrences.
- **`lib/property_listing.py`** — Read 2026-05-22; verified absence of `flood_zone` field.
- **`lib/household.py`** — Read 2026-05-22; verified `state_fips`, `county_fips`, `county_name`, `fico` fields.
- **`lib/rules/conventional_pmi.py`** — Sibling naming reference (HPA cancellation predicate — distinct from rate lookup). Read 2026-05-22 (first 80 lines).
- **`.planning/phases/16-reference-data/16-CONTEXT.md`** — Phase 16 context document; locked decisions D-16-PMI-01..03, D-16-INS-01..04, D-16-FILE-01..03, D-16-WIRE-01..03. Read 2026-05-22.
- **`.planning/phases/14-property-analysis-pipeline/14-VERIFICATION.md`** — Confirms Phase 14 PASS status, frozen surfaces, stale-warning-on-import behavior. Read 2026-05-22.
- **`pyproject.toml`** — Dependency versions verified 2026-05-22.

### Secondary (MEDIUM confidence — verified by cross-reference)

- **NAIC Homeowners Insurance Report — Data for 2022, published 2025-05-21**, https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022 — WebFetch 2026-05-22 confirmed publication date, report title, and CA+TX exclusion.
- **NAIC publications hub** — https://content.naic.org/publications — referenced for general report cadence.
- **California Earthquake Authority — Premium Calculator + 2025 Rate Changes** — https://www.earthquakeauthority.com/california-earthquake-insurance-policies/earthquake-insurance-premium-calculator + https://portal.earthquakeauthority.com/earthquake-policies/2025-rate-policy-changes — WebSearch 2026-05-22 confirmed $3.54/$1000 average rate and 6.8% Jan 2025 increase.
- **FEMA NFIP Risk Rating 2.0** — https://www.fema.gov/flood-insurance/risk-rating + https://www.congress.gov/crs-product/IN11777 — WebSearch 2026-05-22 confirmed zone-based pricing decoupling effective 2021-04-01.
- **III Spotlight on Flood Insurance** — https://www.iii.org/article/spotlight-on-flood-insurance — secondary source for private-market flood context.
- **Insurance Information Institute Facts + Statistics** — https://www.iii.org/fact-statistic/facts-statistics-homeowners-and-renters-insurance — secondary source for state averages where NAIC excludes (CA, TX).
- **NW Insurance Council Earthquake** — https://www.nwinsurance.org/earthquake — secondary source for OR/WA earthquake context (composite citation).
- **Oregon DFR Earthquake Insurance Tips** — https://dfr.oregon.gov/insure/home/storm/pages/earthquake.aspx — secondary source for OR.

### Tertiary (LOW confidence — single source or unverified, flagged for planner validation)

- **MGIC Rate Cards landing page** — https://www.mgic.com/rates/rate-cards — landing page; specific bulletin PDF requires direct download (current archived PDFs from 2018 return 404). Planner must capture a current bulletin manually before YAML pinning. [LOW — A1]
- **Specific flood-zone uplift percentages (X→+0, A/AE→+30, V→+80, unknown→+15)** — CONTEXT D-16-INS-02 "starting design assumption." No single citable source post-Risk-Rating-2.0. [LOW — A6]
- **OR/WA earthquake flat $ values** — composite "NW Insurance Council + Oregon DFR + Washington OIC + private-carrier survey" — no single canonical publication. [LOW — A5]
- **MGIC 4×4 abridged band labels (FICO 760+, 740-759, 720-739, 700-719; LTV 80.01-85, 85.01-90, 90.01-95, 95.01-97)** — inferred from CONTEXT and industry-standard MGIC schedules; not verified against a current MGIC bulletin. [LOW — A1]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps already in `pyproject.toml`, Phase 2 patterns frozen and verified in-repo.
- Architecture: HIGH — direct file-level analog (`lib/rules/fha_mip.py` for pmi, multi-section YAML for insurance) verified by read.
- Pitfalls: HIGH — every pitfall verified against the current codebase (line-numbers + grep output captured 2026-05-22).
- External data sources (MGIC, NAIC, CEA, FEMA, private flood): MEDIUM — verified that the CONTEXT-claimed sources are partially-inaccurate (NAIC 2024 → actual 2022; FEMA zone-based → Risk Rating 2.0 decoupled); planner needs to source exact values manually.
- Phase 14 wire-in: HIGH — exact line numbers + grep-verified file contents.
- CONTEXT discrepancies: HIGH — Pitfalls 1, 2, 3 document misalignments between CONTEXT text and the verified codebase; planner must address.

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (NAIC report cadence is annual; MGIC bulletins are quarterly; FEMA Risk Rating 2.0 documentation stable; external sources may shift faster than internal patterns)
