# Phase 16: Reference Data - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace Phase 14's inline `_CONV_PMI_ANNUAL_RATE = Decimal("0.0075")` constant in `lib/property_analysis.py:151` with a YAML-driven PMI rate lookup (4×4 LTV × FICO bands), AND ship a new insurance-defaults YAML that fires as a fallback when `listing.insurance_estimate_annual` is None. Closes REF-09, REF-10. Honors ROADMAP SC #5: "no inline constants for any regulatory threshold."

**In scope:**
- `data/reference/property-analysis-heuristics.yml` — new YAML; 4×4 PMI table only (16 rows: 4 LTV bands × 4 FICO bands).
- `data/reference/insurance-estimate-defaults.yml` — new YAML; 51 state rows (NAIC 2024 averages) + 4-row FEMA flood-zone uplift table + 3-row CA/OR/WA earthquake flat add-on table.
- `lib/rules/pmi.py` — new predicate module exporting `lookup_rate(fico: int, ltv: Decimal) -> Rate`. Uses existing `lib/rules/_loader.py` for YAML read + 12-month staleness check.
- `lib/rules/insurance.py` — new predicate module exporting `lookup_default(state: str, flood_zone: str | None) -> Money`. Same loader.
- `lib/property_analysis.py` edits:
  1. Remove `_CONV_PMI_ANNUAL_RATE: Final[Decimal] = Decimal("0.0075")` (line 151) and its reasons-tag.
  2. PMI block (`lib/property_analysis.py:653`): replace `_CONV_PMI_ANNUAL_RATE` reference with `lib.rules.pmi.lookup_rate(fico, ltv)` call.
  3. Insurance block (`lib/property_analysis.py:703`): add fallback — when `_unwrap_provenanced(listing.insurance_estimate_annual)` is None, call `lib.rules.insurance.lookup_default(state, flood_zone)` and tag `INSURANCE-ESTIMATED-NAIC-{state}-{zone}` in `eligible_reasons`.
- Tests: `tests/test_rules/test_pmi.py` + `tests/test_rules/test_insurance.py` with hand-calc anchored fixtures (Phase 2 RUL pattern).

**Out of scope:**
- Metro-level insurance overlay (v1.2).
- Per-USGS-seismic-zone earthquake granularity (v1.2 if v1.1 CA/OR/WA blanket proves insufficient).
- Multi-lender consensus PMI averaging (v1.2 if MGIC-only proves inadequate).
- Full MGIC 8×7 schedule (only ship if 4×4 hits frequent "capped" tags in real usage — v2 reconsideration).
- PMI variation by occupancy / unit count / loan purpose (v2 — current scope is owner-occupied SFH).
- Annual refresh automation (Playwright scrape per Phase 2 D-08 deferred AUTO-01).
- Edits to `lib/property_listing.py` (Phase 13 PropertyListing model stays frozen — the fallback lives in `property_analysis.py`, not in the model validator).
- Edits to `.claude/skills/mortgage-ops/modes/property.md` (Phase 15 mode body owns extraction; not gap-filling from YAML at extraction time).
- New REF requirements beyond REF-09 / REF-10 — adding new tables (Fannie LLPA additions, USDA refresh, etc.) belongs in their own phase.

</domain>

<decisions>
## Implementation Decisions

### PMI table granularity + source (REF-09)

- **D-16-PMI-01 (4×4 MGIC abridged schedule):** Ship a 16-row PMI table. FICO bands: `760+`, `740-759`, `720-739`, `700-719` (4 rows). LTV bands: `80.01-85`, `85.01-90`, `90.01-95`, `95.01-97` (4 cols). 16 cells total. Citation source: MGIC Rate Card "Standard MI" abridged published bulletin (single source URL per file per Phase 2 D-02 convention). Reports flag every PMI value as estimate via `PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}` in `eligible_reasons` (replaces today's `PMI-RATE-ESTIMATED-0.0075` tag).
- **D-16-PMI-02 (Cap-at-worst-row fallback for out-of-band combos):** When `(fico, ltv)` falls outside the 4×4 grid — FICO < 700, LTV > 97%, etc. — `lib.rules.pmi.lookup_rate()` returns the rate from the WORST cell in the table (FICO `700-719` × LTV `95.01-97`) and tags `eligible_reasons` with `PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}`. No raise, no Final-constant fallback, no interpolation. Report copy must flag capped cells distinctly from in-band estimates (different reason code makes this trivial).
- **D-16-PMI-03 (Reason-code surface vs current state):** Phase 14's existing `PMI-RATE-ESTIMATED-0.0075` tag is RETIRED. New reason codes: `PMI-RATE-ESTIMATED-MGIC-{ltv}-{fico}` (in-band lookup) and `PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}` (out-of-band fallback). Phase 14's existing `PMI-RATE-ESTIMATED-0.0075` allow-list constant (`lib/property_analysis.py:296`) must be updated; remove old tag, add the two new patterns.

### Insurance defaults (REF-10)

- **D-16-INS-01 (All 50 states + DC, NAIC 2024 averages):** 51 rows in `insurance-estimate-defaults.yml`, one per state. Each row: `state` (2-char USPS code), `base_annual` (NAIC 2024 published avg annual homeowners premium, quoted Decimal string), `notes` (optional context). Mirrors Phase 2 `conforming-limits-2026.yml` "ship the full table, accept annual refresh burden" precedent (D-04 lineage). Annual refresh = 51 YAML edits when NAIC publishes its new report; `lib/rules/_loader.py:_check_staleness` warns at 12 months.
- **D-16-INS-02 (Flood: per-FEMA-zone % uplift):** Separate `flood_zone_multipliers` block in the same YAML. 4 rows: `X` zone → `+0%`, `A`/`AE` zones → `+30%`, `V` zone → `+80%`, `unknown` → `+15%` (mid-band default for missing flood-zone data; planner can adjust to MGIC/CFPB-published value). Multiplicative on top of state base. Citation: FEMA NFIP flood-zone definitions + private-market actuarial averages (planner sources the exact uplift % values).
- **D-16-INS-03 (Earthquake: CA/OR/WA flat $ add-ons):** Separate `earthquake_state_addons` block in the same YAML. 3 rows for CA / OR / WA only. CA carries the highest add-on (CEA + private-market avg); OR + WA lower (lower seismic risk + private market). Other states get no earthquake surcharge (and no tag). Citation: California Earthquake Authority published averages + private-market PNW carrier averages (planner sources exact $ values).
- **D-16-INS-04 (Estimate tag on fallback fire):** When `lib.rules.insurance.lookup_default()` fires from `property_analysis.py`, append `INSURANCE-ESTIMATED-NAIC-{state}-{zone}` (e.g., `INSURANCE-ESTIMATED-NAIC-WA-X`) to `eligible_reasons`. Mirrors PMI tag pattern. Report copy flags every cell with this reason as an estimate.

### File shape + module API (D-15-FILE family)

- **D-16-FILE-01 (Two separate single-purpose YAMLs, no aggregator manifest):** Ship the two YAMLs at the exact paths ROADMAP specifies — `data/reference/property-analysis-heuristics.yml` (PMI only) and `data/reference/insurance-estimate-defaults.yml` (state base + flood multipliers + earthquake add-ons). Existing `data/reference/fha-mip-rates.yml`, `va-funding-fees.yml`, `conforming-limits-2026.yml` stay as-is — Phase 2's structure already covers FHA / VA / jumbo per ROADMAP SC #1's "FHA MIP defaults, VA funding fee defaults, jumbo cutoffs" (those are already shipped). Phase 16 only ADDS the PMI + insurance tables. No aggregator file; no `includes:` block; no unified entry-point module.
- **D-16-FILE-02 (Two new lib/rules modules):** `lib/rules/pmi.py` exports `lookup_rate(fico: int, ltv: Rate) -> Rate` + raises nothing (always returns a Rate per D-16-PMI-02). `lib/rules/insurance.py` exports `lookup_default(state: str, flood_zone: str | None) -> Money`. Both modules use the existing `lib/rules/_loader.py:load_yaml_table()` pattern from Phase 2 D-04; both add a one-per-predicate test file under `tests/test_rules/`.
- **D-16-FILE-03 (Existing _loader.py staleness check honors new YAMLs unchanged):** No changes to `lib/rules/_loader.py`. The new YAMLs carry `effective:` dates per Phase 2 D-02; `_check_staleness` warns at 12 months automatically.

### Phase 14 wire-in

- **D-16-WIRE-01 (Insurance fallback in property_analysis.py Step 6):** Edit `lib/property_analysis.py:703-705` (the `monthly_insurance = quantize_cents(...)` block). When `_unwrap_provenanced(listing.insurance_estimate_annual)` returns None, call `lib.rules.insurance.lookup_default(household.state_fips, listing.flood_zone)` (Phase 13 `PropertyListing` already exposes `flood_zone: str | None` per Phase 13 D-13-FIELDS) and append the `INSURANCE-ESTIMATED-NAIC-{state}-{zone}` reason. PropertyListing model (Phase 13) is NOT modified.
- **D-16-WIRE-02 (PMI lookup in property_analysis.py PMI block):** Edit `lib/property_analysis.py:653-654`. Replace `_CONV_PMI_ANNUAL_RATE` reference with `lib.rules.pmi.lookup_rate(household.fico, ltv)` call. Append the new reason tag per D-16-PMI-03. Remove the `_CONV_PMI_ANNUAL_RATE: Final[Decimal]` constant (line 151) AND its module-docstring mention (lines 21-23).
- **D-16-WIRE-03 (Allow-list update for new reason codes):** The `_ALLOWED_REASONS` constant in `lib/property_analysis.py:296` currently allows the literal string `"PMI-RATE-ESTIMATED-0.0075"`. Replace with regex/prefix pattern matching `PMI-RATE-ESTIMATED-MGIC-*` and `PMI-RATE-CAPPED-MGIC-ABRIDGED-*` and `INSURANCE-ESTIMATED-NAIC-*`. Reason-allow-list test (Phase 14 verification test) must continue passing.

### Claude's Discretion

- **Exact MGIC PMI rate values** — planner sources from MGIC Rate Card "Standard MI" publication; effective date matches publication date. Recommend pinning the latest bulletin and citing the bulletin number.
- **Exact NAIC state averages** — planner sources from the latest NAIC Homeowners Insurance Report. Recommend 2024 data; report's publication date becomes the YAML's `effective` date.
- **Exact flood-zone uplift percentages** — planner sources from NFIP actuarial averages or a representative private-market carrier filing. The X/+0, A/AE/+30, V/+80, unknown/+15 split above is a starting design assumption; refine to whatever the source publishes.
- **Exact CA/OR/WA earthquake $ values** — planner sources from CEA (California Earthquake Authority) published averages + private-market PNW carrier surveys (OR/WA earthquake is non-CEA).
- **YAML row schema details** — quoted Decimal strings per Phase 2 D-02 (Pitfall 1: never let PyYAML emit float). Flat `{state, base_annual, notes}` rows for insurance; `{fico_min, fico_max, ltv_min, ltv_max, rate}` rows for PMI matching the FHA-MIP-table shape. Effective date precision: one date per file (matches the source publication date, not per row).
- **Test fixture set** — golden hand-calc anchors for PMI lookup at FICO 760 × LTV 95 (Conv30 at 5% DP, an in-band case) + a capped case (FICO 680 × LTV 96) + insurance lookup for WA × flood-zone X (Pachulski-household baseline). Phase 2 RUL pattern: 1:1 test-to-citation mapping per row.
- **Earthquake "unknown state" behavior** — when `state` is not in {CA, OR, WA} the earthquake lookup returns Decimal("0.00") silently (no tag). Documented in `lib/rules/insurance.py` docstring.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 16 planning artifacts (this phase)
- `.planning/REQUIREMENTS.md` — REF-09, REF-10 (pending → must close in Phase 16)
- `.planning/ROADMAP.md` §"Phase 16: Reference Data" — 5 success criteria, Depends on Phase 14
- `.planning/PROJECT.md` — math-correctness-first principle; reference-data discipline ("all regulatory parameters in `data/reference/*.yml` with `source:` URL and `effective:` date")
- `CLAUDE.md` — Money discipline (Decimal-from-strings only; YAML scalars MUST be quoted); reference data discipline

### Prior-phase decisions (carry forward)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-CONTEXT.md` — D-02 (quoted-string YAML convention; per-file `source` / `effective` / `notes`); D-04 (full-matrix precedent — accept refresh burden); D-05 (reference data YAMLs ship under their RUL/REF parents, not as new REF-IDs)
- `.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md` — D-14-MATRIX-02 (ineligible rows still compute their numbers — PMI fallback applies to LTV>0.80 cells regardless of program eligibility); reason-code surface convention
- `.planning/phases/14-property-analysis-pipeline/14-VERIFICATION.md` — confirms AnalysisReport schema frozen; reason-code allow-list test (test_phase14_reasons_allow_listed) currently passes with `PMI-RATE-ESTIMATED-0.0075` — Phase 16 must update allow-list AND keep test green
- `.planning/phases/13-property-ingestion/13-CONTEXT.md` — PropertyListing model (insurance_estimate_annual optional; flood_zone optional)

### Existing reference YAMLs Phase 16 PRESERVES (no edits)
- `data/reference/fha-mip-rates.yml` — FHA MIP defaults already shipped (ROADMAP SC #1 says "FHA MIP defaults"; this file already provides them)
- `data/reference/va-funding-fees.yml` — VA funding fee defaults already shipped
- `data/reference/conforming-limits-2026.yml` — Jumbo cutoffs already shipped (2026 FHFA limits)
- `data/reference/fha-limits-2026.yml` — FHA county limits already shipped
- `data/reference/fannie-llpa-matrix.yml`, `freddie-eligibility-matrix.yml` — referenced for the "full matrix" precedent (D-04)

### Existing code Phase 16 EXTENDS or READS
- `lib/rules/_loader.py` — `load_yaml_table()` + `_check_staleness()` (12-month warning); new `pmi.py` + `insurance.py` modules call this entrypoint
- `lib/property_analysis.py:151` — `_CONV_PMI_ANNUAL_RATE` Final constant to REMOVE
- `lib/property_analysis.py:653-654` — PMI computation site to rewire to `lib.rules.pmi.lookup_rate()`
- `lib/property_analysis.py:703-705` — insurance computation site to add `lib.rules.insurance.lookup_default()` fallback
- `lib/property_analysis.py:296` — `_ALLOWED_REASONS` constant to update with new reason patterns
- `lib/property_analysis.py:21-23` — module docstring mention of `_CONV_PMI_ANNUAL_RATE` to remove
- `lib/property_listing.py` — Phase 13 PropertyListing model: READ-ONLY this phase; expose `flood_zone: str | None` for the insurance lookup call site
- `lib/household.py` — Phase 14 Household: provides `state_fips` (2-digit FIPS) and `fico`; insurance lookup needs 2-char USPS code (need state_fips → USPS mapping in `lib/rules/insurance.py` — small constant dict)
- `lib/rules/conventional_pmi.py` — Phase 2 PMI auto-termination predicate (UNCHANGED — different concern; cancellation logic, not rate lookup)
- `tests/test_rules/conftest.py` — Phase 2 fixture factory pattern; new test files follow same shape

### External references (research domain — planner verifies + cites)
- MGIC Rate Card "Standard MI" published bulletin — source for PMI rate values
- NAIC Homeowners Insurance Report (latest published) — source for state base premiums
- FEMA NFIP flood-zone definitions — source for X/A/AE/V zone classifications
- California Earthquake Authority published averages — source for CA earthquake add-on
- Private-market PNW carrier surveys (OR/WA) — source for non-CEA earthquake add-ons
- 12 USC §4901-4910 (HPA) — already cited by `lib/rules/conventional_pmi.py`; NOT relevant to Phase 16 rate-lookup work

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`lib/rules/_loader.py:load_yaml_table()`** — Phase 2's YAML reader; takes filename + expected schema, returns parsed dict with quoted-Decimal handling. `_check_staleness()` warns at 12 months. Phase 16's two new modules call this verbatim.
- **`lib/rules/fha_mip.py`** — closest existing analog for `lib/rules/pmi.py`. Same shape: docstring with `Citation:` / `Source URL:` / `Effective:` lines, YAML-driven table lookup, range-based row matching. Phase 16 PMI module mirrors this file structure 1:1.
- **`lib/rules/conventional_pmi.py`** — closest existing analog for naming convention (`conventional_pmi.py` for cancellation; `pmi.py` for rate lookup is the natural sibling).
- **`tests/test_rules/test_fha_mip.py`** — analog test structure for `tests/test_rules/test_pmi.py` + `tests/test_rules/test_insurance.py`. Per Phase 2 RUL pattern: 1:1 test-to-citation mapping.

### Established Patterns
- **Money discipline (CLAUDE.md non-negotiable):** Decimal constructed from strings; YAML scalars quoted; loader returns strings, caller wraps in `Decimal(...)` at boundary; `quantize(Decimal("0.01"), ROUND_HALF_UP)` end-of-period only.
- **One-predicate-per-citation (Phase 2):** each `lib/rules/*.py` cites its operative statute / publication / handbook. PMI rate lookup is NOT a regulatory predicate (no statutory citation) — it's an industry-published heuristic. Plan acknowledges this: PMI module's `Citation:` line names the MGIC bulletin; `Source URL:` points to the rate card.
- **Reason-code allow-list (Phase 14):** `_ALLOWED_REASONS` in `lib/property_analysis.py:296` gates the strings that may appear in `eligible_reasons`. Phase 16 updates this constant; the allow-list test must continue passing.
- **YAML row schema (Phase 2 D-02):** quoted Decimal strings; per-file `source` / `effective` / `notes`; numeric scalars NEVER unquoted (Pitfall 1: PyYAML float coercion).
- **Reference data subset shipping (Phase 2):** ship the high-volume subset, document via `notes:` field, MissingDataError or capped-fallback for out-of-coverage. Phase 16 PMI uses capped-fallback per D-16-PMI-02; insurance ships full 50+DC so no out-of-coverage handler needed.

### Integration Points
- **`lib/property_analysis.py:653-654`** — PMI computation site. Currently uses `_CONV_PMI_ANNUAL_RATE`; Phase 16 replaces with `lib.rules.pmi.lookup_rate(fico, ltv)`.
- **`lib/property_analysis.py:703-705`** — Insurance computation site. Currently requires `listing.insurance_estimate_annual` to be non-None (no fallback); Phase 16 adds the YAML fallback.
- **`lib/property_analysis.py:296`** — `_ALLOWED_REASONS` constant. Phase 16 updates with new reason patterns.
- **`tests/test_rules/`** — new test files added under existing test directory; no test infrastructure changes.
- **`evals/fixtures/property/sfh_conforming_001.json`** (Phase 15) — synthetic fixture; planner verifies the fixture's insurance_estimate_annual + fico + ltv combo still works with the new lookup (or updates if Phase 16 changes the value).

</code_context>

<specifics>
## Specific Ideas

- **Phase 2 D-04 precedent governs PMI granularity philosophy** — D-04 chose the full Fannie LLPA matrix over a simplified version because "annual refresh will be a meaningful YAML edit — accept the maintenance burden." Phase 16 explicitly DEPARTS from this for PMI: the 4×4 simplified table is the v1.1 choice with a documented capped-fallback. If real-world usage shows frequent capped cells, v2 reconsiders the full MGIC 8×7 schedule (deferred below).
- **Phase 14 `PMI-RATE-ESTIMATED-0.0075` retirement** — search-and-destroy the literal string in Phase 14 source + the `_ALLOWED_REASONS` allow-list + any test that asserts this exact tag. Replace with the two new reason patterns.
- **Mirror Phase 14 verification test** — Phase 14 ships a reasons-allow-list test that catches drift. Phase 16 MUST update it, not bypass it. The test stays green by listing both the new patterns; planner verifies via grep.
- **NAIC report timing** — NAIC publishes the Homeowners report on a roughly annual cadence; the 2024 report is the latest published as of Phase 16 work. Planner pins `effective: 2024-XX-XX` to the report's publication date; the 12-month staleness warning will fire on import (CORRECT behavior — Phase 2 D-02 precedent: warnings firing on still-current data is expected when the source hasn't republished).
- **Worked-example planner task** — like Phase 15 `modes/property.md` included a worked example, Phase 16's `lib/rules/pmi.py` + `lib/rules/insurance.py` docstrings should each include a worked example showing the lookup call + expected return value + the resulting reason tag, citing real numbers from the shipped YAML.

</specifics>

<deferred>
## Deferred Ideas

- **Metro-level insurance overlay** — overlay 25 high-volume MSAs on top of the 51 state-level rows (two-tier lookup: metro first, state fallback). Listed as v1.2 watchlist-mode enrichment; requires a ZIP→MSA mapping that's out of v1.1 scope.
- **USGS seismic-zone-by-county earthquake granularity** — currently CA/OR/WA flat add-ons; v1.2 could ship a 4-row USGS-seismic-zone table (zones 1-4) with county-level lookups.
- **Multi-lender consensus PMI averaging** — composite of MGIC + Radian + Genworth + National MI per-cell. Closer to real-world quote spread; defer to v1.2 if MGIC-only feedback shows systematic bias.
- **Full MGIC 8×7 PMI schedule** — 56 rows instead of 16. Reconsider for v2 if v1.1 frequently fires the capped-fallback tag in real usage.
- **PMI variation by occupancy / unit count / loan purpose** — investment / second-home / multi-unit / cash-out refi LLPA-style PMI variations. Out of v1 scope (current scope is owner-occupied SFH; Phase 2 D-12 also defers multi-unit and investment cases).
- **Cross-table aggregator manifest** — `data/reference/property-analysis-heuristics.yml` could later evolve into an aggregator with `includes:` referencing all reference YAMLs. v1.2+ if more reference YAMLs accrue and a single import surface becomes valuable.
- **Annual refresh automation** — Playwright scrape of FHFA / HUD / IRS / NAIC pages (Phase 2 D-08 lineage; AUTO-01). v2.
- **Per-FEMA-flood-zone cost-of-flood-insurance separate from homeowners uplift** — current model multiplies homeowners by a flood uplift %, but real NFIP flood is a separate policy. Defer the "true NFIP-policy cost" model to v1.2; v1.1's combined-multiplier is an estimate (tagged as such via `INSURANCE-ESTIMATED-NAIC-*`).
- **PropertyListing model_validator auto-population** — Phase 13 PropertyListing could gain a model_validator that auto-fills insurance_estimate_annual from YAML at validation time. Considered + REJECTED for Phase 16: Phase 13 is frozen and the fallback in `property_analysis.py` is the cleaner separation (Phase 13 = data-shape; Phase 16 = wiring).
- **Earthquake state coverage beyond CA/OR/WA** — Alaska + Hawaii + Utah (Wasatch) + the New Madrid zone (MO/AR/TN). v1.2 if needed.

</deferred>

---

*Phase: 16-reference-data*
*Context gathered: 2026-05-22*
