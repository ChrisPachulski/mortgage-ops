# Requirements: mortgage-ops v1.1 Property Analysis Mode

**Milestone:** v1.1
**Goal:** Feed a Zillow URL → get a one-page underwriting workup using the full v1.0 calc engine.
**Defined:** 2026-05-14
**Status:** Active

## Scope

Feed a Zillow listing URL into the mortgage-ops skill and have it run the entire v1.0 calc engine (amortize × affordability × ARM × refi-NPV × stress × points × IRS Pub 936) against `(listing, household, profile)`, producing a single-page markdown report with a GO / WATCH / NO-GO verdict and reason list.

The math layer is complete. v1.1 is **composition + ingestion + a new report formatter**, not new primitives.

## Requirements

### Property Ingestion (Hybrid: WebFetch + interactive gap-fill)

- [x] **INGEST-01**: WebFetch fetches the Zillow listing URL and extracts the `<script id="__NEXT_DATA__">` JSON blob. Captcha / 403 / non-200 responses are detected and surface a structured error envelope (not a Python traceback).
- [x] **INGEST-02**: Haiku-prompted extraction pulls the canonical PropertyListing fields from `__NEXT_DATA__`: price, tax_annual, hoa_monthly, insurance_estimate_annual, beds, baths, sqft, zip, property_type, year_built, zestimate, days_on_market, list_date.
- [x] **INGEST-03**: Interactive gap-fill — when any MUST-HAVE field (price, zip, property_type) is missing or null, Claude prompts the user; each user-provided value is recorded with `provenance: user_provided` in the PropertyListing record.
- [x] **INGEST-04**: ZPID extraction from URL — supports both `zillow.com/homedetails/{slug}/{zpid}_zpid/` and `zillow.com/b/{zpid}_zpid/` URL patterns; ZPID is the durable primary key for `analyzed_listings`.

### PropertyListing Domain Model

- [x] **PROP-01**: `lib/property_listing.py` ships a Pydantic v2 `PropertyListing` model with all canonical fields, `condecimal` for money, `Literal` for `property_type` (SFH / condo / townhouse / multifamily-2-4), `field_validator` for zip (5-digit string), all money fields wrapped in `ProvenancedMoney` (value + provenance: `scraped | user_provided | estimated`).
- [x] **PROP-02**: Round-trip serialization to DuckDB via `orchestration/db-write.mjs` pattern from Phase 9; analyzed_listings table schema documented in references/property-analysis.md.

### Analysis Pipeline (`lib/property_analysis.py`)

- [x] **ANLZ-01**: Multi-program comparison fans out across 4 loan programs (Conventional 30yr, Conventional 15yr, FHA 30yr, VA 30yr if profile.va_eligible) + jumbo branch when price exceeds zip-specific conforming limit; each program produces a Pydantic `ProgramResult` (eligible, monthly_PITI, cash_to_close, DTI, LTV, PMI/MIP/funding-fee, eligible_reasons, blocker_reasons).
- [x] **ANLZ-02**: Down-payment scenario sweep at 3% / 5% / 10% / 15% / 20% / 25% per program — produces a `DownPaymentMatrix` (~24 cells for 4 programs × 6 DPs, fewer when programs are ineligible).
- [x] **ANLZ-03**: Auto-applied stress tests (rate shock +2%, income shock -30%, ARM reset at peak cap) + points breakeven (1pt and 2pt drops) + refi opportunity scan (against current FRED rate × 0.85 historical-avg-drop heuristic) + IRS Pub 936 deductibility rollup (first-year interest, $750k cap awareness).

### Verdict Synthesis

- [x] **VERD-01**: `lib/property_verdict.py` returns GO / WATCH / NO-GO + reason list. Rules: any DTI breach across all eligible programs → NO-GO; any program eligible at user's preferred DP → GO; eligible-only-via-FHA-with-MIP-burden or stress-fails-income-shock → WATCH. Verdict copy is short and falsifiable (each reason cites a specific predicate + computed number).

### `property` Skill Mode

- [x] **MODE-01**: `.claude/skills/mortgage-ops/modes/property.md` ships with routing rule: if user message contains a `zillow.com` substring OR explicit `analyze listing` phrase → dispatch to `property` mode. URL-pin overrides any mode-routing keyword collision (the URL is load-bearing).
- [x] **MODE-02**: SKILL.md routing block cross-references `modes/property.md` per Phase 10 D-09 progressive-disclosure convention; SKILL.md token budget preserved (≤ 4500 cl100k tokens).
- [x] **MODE-03**: `property` mode invokes `scripts/property_analyze.py` (new) which orchestrates the full pipeline; never computes inline; always exits 0 with structured envelope per Phase 12 D-12-LIVE02-01 recovery contract.

### Persistence

- [x] **PERS-08**: DuckDB `analyzed_listings` table created in Wave 0 via migration; schema includes zpid PK, source_url, all PropertyListing fields, analysis_report TEXT (markdown), analysis_verdict ENUM (GO/WATCH/NO-GO), analyzed_at TIMESTAMP, household_snapshot_hash (so re-analyses after household.yml changes don't silently overwrite). Lockfile pattern from Phase 9 reused verbatim.

### Report Formatter

- [x] **RPRT-01**: `lib/property_report.py` emits markdown to `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md` mirroring Phase 11 amortization-agent's "markdown table OR CSV path" contract. Markdown layout matches the mockup: header (address / price / Zestimate delta / tax-HOA-insurance escrow), `## YOUR FIT` section with program × DP matrix, `## RATE STRESS` + `## POINTS BREAKEVEN` + `## REFI OPPORTUNITY` + `## TAX` sections, `## VERDICT` synthesis at bottom.
- [x] **RPRT-02**: Every numeric field in the report carries citation footer `Computed by: scripts/{name}.py {args}` per Phase 11 stress-test-agent precedent + Phase 12 D-12-SC3-01 stdout-only sourcing.

### Reference Data

- [ ] **REF-09**: `data/reference/property-analysis-heuristics.yml` ships PMI rate tables (PMI by LTV band and FICO band), FHA MIP defaults, VA funding fee defaults, jumbo cutoffs by zip-county (use 2026 FHFA conforming limits). Annual refresh = YAML edit, not code change.
- [ ] **REF-10**: `data/reference/insurance-estimate-defaults.yml` ships per-state homeowners insurance avg annual cost (used when listing has no insurance estimate) + earthquake/flood add-ons by FEMA zone.

### Testing

- [ ] **TEST-01**: 5 pinned Zillow HTML fixtures at `tests/fixtures/zillow/` covering: SFH-conforming, SFH-jumbo, condo-conforming, condo-with-HOA, multifamily-2-4. Each has a paired golden-value `expected_report.md` so the formatter is regression-tested. Synthetic-only-in-CI per Phase 11 D-02 inheritance; live WebFetch never runs in CI.
- [ ] **TEST-02**: Citation-coverage meta-test mirrors Phase 8 / Phase 12 — every PropertyListing field used in the report must trace to either the listing record or a scripts/ invocation; every regulatory threshold (PMI cap, FHA limit, jumbo cutoff) must trace to a `data/reference/*.yml` row with citation.

### References Documentation

- [ ] **REFS-01**: `.claude/skills/mortgage-ops/references/property-analysis.md` (≥250 lines, 6-section template per arm-mechanics.md idiom + Citation Index) documents the ingestion pipeline (WebFetch + gap-fill), the 4-program × 6-DP fan-out algorithm, the verdict-synthesis rules, the DuckDB schema, the report layout contract, and 12 pitfalls from research §10.
- [ ] **REFS-02**: CLAUDE.md "Project Skills" section gains a `property` mode bullet; SKILL.md references-table extended with `property-analysis.md` row.

## v1 → v1.1 Traceability

| Requirement | Assigned Phase | Status |
|-------------|----------------|--------|
| INGEST-01..04 | Phase 13 (property-ingestion) | Closed (Plan 13-04 + integration coverage in Plan 13-06) |
| PROP-01..02 | Phase 13 (property-ingestion) | Closed (PROP-01 Plan 13-01; PROP-02 Plan 13-05) |
| ANLZ-01..03 | Phase 14 (property-analysis-pipeline) | Pending |
| VERD-01 | Phase 14 | Complete |
| MODE-01..03 | Phase 15 (property-mode) | Pending |
| PERS-08 | Phase 13 | Closed (Plan 13-05) |
| RPRT-01..02 | Phase 15 | Pending |
| REF-09..10 | Phase 16 (reference-data) | Pending |
| TEST-01..02 | Phase 17 (tests-and-fixtures) | Pending |
| REFS-01..02 | Phase 18 (references) | Pending |

**Coverage:** 16 requirements across 6 phases. Every requirement maps to exactly one phase; every phase has at least one requirement.

## Open Questions (locked by /gsd-discuss-phase before each phase)

1. **Personal vs generic baseline:** does the report use YOUR household scenarios (profile.yml + household.yml) or generic 20%-down baselines? (Default: personal — read profile.yml at runtime; fall back to generic if absent.)
2. **Verdict thresholds:** what DTI / LTV / cash-to-close ratios flip GO → WATCH → NO-GO? (Default: hard codes from regulatory predicates — DTI > 43% conventional → NO-GO; FHA-only eligible → WATCH with reason; all primary programs eligible → GO.)
3. **Default stress scenarios:** which run automatically vs opt-in? (Default: rate +2%, income -30%, ARM reset at peak cap — auto. Job loss / death-of-spouse / property tax reassessment — opt-in.)
4. **Refi opportunity heuristic:** rates fall 1%, or FRED current × 0.85 historical avg, or both? (Default: both, side by side.)
5. **Down-payment scenario set:** 3/5/10/15/20/25, or include 0% (VA) and 30%+? (Default: 0% only if VA-eligible; 30%+ deferred to v1.2.)
6. **Watchlist mode:** should `property` mode also expose `list listings` / `compare listings A B C` commands? (Default: NO — single-listing flow only in v1.1; multi-listing comparison deferred to v1.2.)
7. **PMI cutoff:** auto-removable at 78% LTV (HPA) or 80% LTV (lender request)? Both? (Default: both — show 80% borrower-request line and 78% auto-removal line.)
8. **Apify fallback timing:** ship paid-scraper integration in v1.1 (belt-and-suspenders) or strict v1.2-only (WebFetch + gap-fill must prove insufficient first)? (Default: STRICT v1.2-only — ship hybrid first, watch for degradation in real use, then add Apify if needed.)
