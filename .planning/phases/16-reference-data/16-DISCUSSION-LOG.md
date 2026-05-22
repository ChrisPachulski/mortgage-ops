# Phase 16: Reference Data - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 16-reference-data
**Areas discussed:** PMI table granularity + source, PMI fallback when no row matches, Insurance state coverage, Insurance surcharge model, property-analysis-heuristics.yml shape, Insurance fallback wire-in

---

## PMI table granularity + source

| Option | Description | Selected |
|--------|-------------|----------|
| Simplified 4×4 (MGIC abridged) | 4 LTV bands × 4 FICO bands = 16 rows. MGIC Rate Card "Standard MI" abridged. Coarsest fidelity for low FICO; cheapest refresh. | ✓ |
| Full MGIC schedule (8×7) | 8 LTV × 7 FICO = 56 rows. Mirrors Phase 2 D-04 full-matrix precedent. Annual refresh = meaningful YAML edit. | |
| Multi-lender consensus (4×4 averaged) | 4×4 grid with each cell averaging MGIC + Radian + Genworth + National MI. 4 source URLs. | |
| MGIC 8×7 + low-FICO safety-net carve-out | 8×7 for FICO ≥ 640; below 640 a single high-risk band row. 57 rows; captures wider real distribution. | |

**User's choice:** Simplified 4×4 (MGIC abridged)
**Notes:** Recommended balance for v1.1 personal-use scope. Capped-fallback (D-16-PMI-02) handles out-of-band cases without raising. Full 8×7 deferred for reconsideration if v1.1 hits frequent capped tags.

---

## PMI fallback when no row matches

| Option | Description | Selected |
|--------|-------------|----------|
| Use highest-rate row + estimate flag | Return worst-cell rate (FICO 700-719 × LTV 95.01-97) + tag `PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}`. Conservative; no silent failures. | ✓ |
| Raise MissingPMIBandError (loud) | lib.rules.pmi raises; property_analysis catches → cell ineligible + BLOCKER-PMI-DATA-GAP. Forces table extension. | |
| Linear-interpolate between bands | Smoothest output; complex code; hard to cite (interpolated value isn't published). | |
| Fall back to 0.0075 Final constant | Preserves Phase 14 backwards-compat; documented exception to SC #5. | |

**User's choice:** Use highest-rate row + estimate flag
**Notes:** Conservative estimate + visible tag in `eligible_reasons` lets the report copy distinguish in-band estimates from capped fallbacks. Aligns with Phase 14's "M-14-MATRIX-02" philosophy (compute the number, surface the caveat in reasons).

---

## Insurance state coverage

| Option | Description | Selected |
|--------|-------------|----------|
| All 50 states + DC (NAIC 2024 averages) | 51 rows; covers any US listing; one NAIC report read per refresh; matches Phase 2 D-04 full-table precedent. | ✓ |
| Target metros only (~10 rows) | WA/OR/CA + 5-7 high-volume markets; smallest YAML; out-of-coverage → MissingInsuranceDataError. | |
| All 50 states + metro overlay top 25 MSAs | 51 state + 25 MSA = ~75 rows; ZIP→MSA mapping problem. | |
| All 50 states; defer metro granularity to v1.2 | 51 rows now; metro overlay deferred to watchlist mode. | |

**User's choice:** All 50 states + DC (NAIC 2024 averages)
**Notes:** Choosing full coverage now is consistent with Phase 2's full-Fannie-LLPA-matrix precedent and avoids out-of-coverage errors for any random Zillow URL the user pastes. Annual refresh = one NAIC report read.

---

## Insurance surcharge model

| Option | Description | Selected |
|--------|-------------|----------|
| FEMA flood zone uplift % + CA/OR/WA earthquake flat $ add-on | Flood: X +0%, A/AE +30%, V +80%. Earthquake: CEA + private-market flat $ for CA/OR/WA only. | ✓ |
| Flood by FEMA zone + earthquake by USGS seismic zone | Flood same; earthquake by 4 USGS zones with county lookup. More defensible; costlier source. | |
| Flood only; earthquake deferred to v1.2 | Conservative scope; most listings don't carry earthquake. | |
| Flat uplift table by (flood_zone, state) combo | 4 × 51 = 204 cells; single combined add-on; hard to cite. | |

**User's choice:** FEMA flood zone uplift % + CA/OR/WA earthquake flat add-on
**Notes:** Combines a published-source flood model (FEMA zones, NFIP actuarial averages) with a focused earthquake model for the three high-seismic states. Other states get no earthquake surcharge. USGS-seismic-zone refinement and OR/WA private-market sourcing are noted for v1.2.

---

## property-analysis-heuristics.yml shape

| Option | Description | Selected |
|--------|-------------|----------|
| PMI table only (single-purpose) | New file = 4×4 PMI table only. Existing fha-mip / va-funding / conforming-limits stay as-is. lib/rules/pmi.py exports lookup_rate(). | ✓ |
| PMI + aggregator manifest | PMI table + `includes:` block referencing FHA/VA/conforming for single Phase 14 entry-point. | |
| PMI + aggregator + insurance | Merge PMI + insurance into one file; reduces 2 new files to 1; mixed citations per file. | |
| Two separate new files, no aggregator | Match ROADMAP filenames exactly; cleanest separation; smallest API change. | |

**User's choice:** PMI table only (single-purpose)
**Notes:** Functionally equivalent to "Two separate new files, no aggregator" — the user's pick names the new file's contents (PMI only) while implicitly preserving the second file (`insurance-estimate-defaults.yml`) as its own single-purpose file. Decisions D-16-FILE-01 captures both YAMLs at the exact paths ROADMAP names.

---

## Insurance fallback wire-in

| Option | Description | Selected |
|--------|-------------|----------|
| In property_analysis.py (analyze step) | Step 6 escrow block: if listing.insurance_estimate_annual is None → call lib.rules.insurance.lookup_default(). PropertyListing (Phase 13) untouched. | ✓ |
| In PropertyExtractor (Claude mode body) | Mode body gap-fills at extraction time before validation. Requires modes/property.md edit (Phase 15 file). | |
| In PropertyListing model_validator | Auto-fill at validation time; touches Phase 13 (which was implicitly frozen). | |
| Hybrid: PropertyListing fills if state+zone present, else analyze() retries | Two code paths; explicit failure modes; more moving parts. | |

**User's choice:** In property_analysis.py (analyze step)
**Notes:** Keeps Phase 13 PropertyListing frozen and Phase 15 mode body untouched. The fallback is a pure addition to Phase 14's existing computation site (lib/property_analysis.py:703-705), cleanly tagged via `INSURANCE-ESTIMATED-NAIC-{state}-{zone}` in eligible_reasons.

---

## Claude's Discretion

- Exact MGIC PMI rate values (planner sources from MGIC Rate Card bulletin)
- Exact NAIC 2024 state average homeowners premium values (planner sources from NAIC report)
- Exact FEMA flood-zone uplift percentages (planner sources from NFIP actuarial averages or representative carrier filing)
- Exact CA/OR/WA earthquake $ add-on values (planner sources from CEA + PNW carrier averages)
- YAML row schema details (quoted Decimal strings per Phase 2 D-02; flat `{state, base_annual, notes}` rows for insurance; `{fico_min, fico_max, ltv_min, ltv_max, rate}` rows for PMI matching the FHA-MIP-table shape; one effective date per file)
- Test fixture set (golden hand-calc anchors for PMI in-band + capped cases + insurance WA × flood-zone X baseline)
- Earthquake "unknown state" behavior (state ∉ {CA, OR, WA} → silent zero, no tag; documented in `lib/rules/insurance.py` docstring)

## Deferred Ideas

- Metro-level insurance overlay (v1.2)
- USGS seismic-zone-by-county earthquake granularity (v1.2)
- Multi-lender consensus PMI averaging (v1.2)
- Full MGIC 8×7 PMI schedule (v2 reconsideration if v1.1 hits frequent capped tags)
- PMI variation by occupancy / unit count / loan purpose (v2 — current scope is owner-occupied SFH)
- Cross-table aggregator manifest at `property-analysis-heuristics.yml` (v1.2+ if more YAMLs accrue)
- Annual refresh automation — Playwright scrape (v2 AUTO-01)
- Per-FEMA-flood-zone separate NFIP-policy cost model (v1.2)
- PropertyListing model_validator auto-population (rejected — Phase 13 stays frozen)
- Earthquake state coverage beyond CA/OR/WA — AK / HI / UT / New Madrid (v1.2)
