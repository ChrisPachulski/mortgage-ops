# Roadmap: mortgage-ops

## Shipped Milestones

- **v1.0** — Deterministic Python mortgage calc engine + Claude skill frontend (12 phases, 87 plans, 644 tests passing; SHIPPED 2026-05-13) → [`.planning/milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md)

## Active Milestone

**v1.1 Property Analysis Mode** — Started 2026-05-14
**Goal:** Feed any Zillow listing URL → get a single-page underwriting workup that runs the full v1.0 calc engine against the property × household, with a GO / WATCH / NO-GO verdict.
**Research:** [`.planning/research/v1.1-property-analysis.md`](research/v1.1-property-analysis.md)
**Requirements:** [`REQUIREMENTS.md`](REQUIREMENTS.md) (16 reqs across 6 phases)

### Granularity

User selected **fine** — 6 phases, bottom-up. Phases 13-18 continue v1.0 numbering.

### Phases

- [x] **Phase 13: Property Ingestion** - WebFetch + `__NEXT_DATA__` extraction + interactive gap-fill + `PropertyListing` Pydantic model + DuckDB `analyzed_listings` table
- [x] **Phase 14: Property Analysis Pipeline** - Multi-program fan-out (Conv 30/15, FHA, VA, Jumbo) × DP sweep (3/5/10/15/20/25%) + auto-stress + breakeven + refi + IRS Pub 936 + GO/WATCH/NO-GO verdict (completed 2026-05-18)
- [x] **Phase 15: `property` Skill Mode + Report Formatter** - `modes/property.md` URL-pin routing + `scripts/property_analyze.py` orchestrator + `lib/property_report.py` markdown emitter to `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md` (completed 2026-05-21)
- [ ] **Phase 16: Reference Data** - `data/reference/property-analysis-heuristics.yml` (PMI tables, FHA county limits, jumbo cutoffs) + `insurance-estimate-defaults.yml` (per-state HOI averages)
- [ ] **Phase 17: Tests + Fixtures** - 5 pinned Zillow HTML fixtures + paired golden-value `expected_report.md` files + citation-coverage meta-test
- [ ] **Phase 18: References + Docs** - `references/property-analysis.md` (≥250 lines, 6-section template + Citation Index) + CLAUDE.md cross-link + SKILL.md references-table extension

## Phase Details

### Phase 13: Property Ingestion

**Goal**: Reliably turn a Zillow URL into a validated `PropertyListing` Pydantic record, persisted to DuckDB. Hybrid pipeline (WebFetch + Haiku-prompted extraction + interactive gap-fill); zero dependency on paid scraper APIs.
**Status**: COMPLETED 2026-05-16 — 7 plans shipped (13-00 scaffolding, 13-01 PropertyListing, 13-02 block detector, 13-03 Sonnet extractor, 13-04 CLI orchestrator, 13-05 DuckDB persistence, 13-06 fixtures + integration test). All 7 requirements closed; 5 D-13 locks proven.
**Depends on**: v1.0 (Phase 10 SKILL.md scaffolding + Phase 9 DuckDB + Phase 12 always-exit-0 envelope contract)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, PROP-01, PROP-02, PERS-08
**Success Criteria** (what must be TRUE):

  1. Given a valid Zillow URL, `scripts/property_fetch.py` returns a populated `PropertyListing` JSON envelope with `provenance` tags on every money field (`scraped | user_provided | estimated`).
  2. Captcha / 403 / non-200 responses produce a structured `{listing: null, error: ...}` envelope on stdout with exit 0 — no Python tracebacks (D-12-LIVE02-01 inherited).
  3. When MUST-HAVE fields (price, zip, property_type) are missing from `__NEXT_DATA__`, the script emits an `awaiting_user_input` envelope listing the missing fields; the skill prompts the user and re-invokes with `--user-provided '{...}'` flag.
  4. ZPID extracted from both URL patterns (`/homedetails/{slug}/{zpid}_zpid/` and `/b/{zpid}_zpid/`); ZPID is the DuckDB primary key for `analyzed_listings`.
  5. Round-trip persistence: write a PropertyListing to DuckDB, read it back, assert byte-equal serialization. Lockfile pattern from Phase 9 reused verbatim.

### Phase 14: Property Analysis Pipeline

**Goal**: Compose v1.0 calc primitives (amortize × affordability × ARM × refi × stress × points × IRS Pub 936) into a single `(listing, household, profile) → AnalysisReport` pipeline. Multi-program × down-payment fan-out + verdict synthesis.
**Depends on**: Phase 13 (needs `PropertyListing` model)
**Requirements**: ANLZ-01, ANLZ-02, ANLZ-03, VERD-01
**Success Criteria**:

  1. `lib/property_analysis.py:analyze(listing, household, profile) → AnalysisReport` runs 4 program-eligibility checks (Conventional 30, Conventional 15, FHA, VA if eligible) + jumbo branch when price > conforming limit per zip.
  2. Down-payment sweep produces a `DownPaymentMatrix` with 6 cells per eligible program (3 / 5 / 10 / 15 / 20 / 25% DP). PMI/MIP/funding-fee correctly applied per program + LTV.
  3. Auto-applied stress tests: rate shock +2%, income shock -30%, ARM reset at peak cap (one entry per program where ARM is offered).
  4. Points breakeven at 1pt and 2pt rate drops; refi opportunity scan at (FRED current rate − 1%) and (FRED current rate × 0.85).
  5. IRS Pub 936 deductibility: first-year interest computed, $750k cap awareness (loan_amount > $750k → partial deduction flagged).
  6. Verdict (`GO | WATCH | NO_GO`) with `reasons: list[str]` — each reason cites a specific predicate + computed value. Tests assert: DTI breach across all eligible programs → NO_GO; eligible-only-via-FHA-with-MIP-burden → WATCH; primary programs eligible at user's preferred DP → GO.
  7. Golden-value fixtures: 3 hand-calculated AnalysisReport cases (SFH conforming, condo with HOA, SFH jumbo) pin every cell of the matrix; full suite green.

### Phase 15: `property` Skill Mode + Report Formatter

**Goal**: Wire the analysis pipeline into the Claude skill via a new `property` mode; emit the report as a single-page markdown file under `reports/`.
**Depends on**: Phase 14 (needs AnalysisReport contract)
**Requirements**: MODE-01, MODE-02, MODE-03, RPRT-01, RPRT-02
**Success Criteria**:

  1. `.claude/skills/mortgage-ops/modes/property.md` ships with URL-pin routing — any user message containing `zillow.com` substring dispatches to `property` mode regardless of other mode-routing keywords. Explicit `analyze listing` phrase also routes here.
  2. SKILL.md routing block cross-references `modes/property.md` per Phase 10 D-09 progressive-disclosure; SKILL.md token budget ≤ 4500 cl100k tokens preserved.
  3. `scripts/property_analyze.py` orchestrator runs end-to-end: ingest → analyze → format → persist → emit markdown path. Always exits 0 with `{report_path, verdict, error: null}` envelope per Phase 12 contract.
  4. `lib/property_report.py` emits markdown to `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md` with sections: Header + `## YOUR FIT` (matrix table) + `## RATE STRESS` + `## POINTS BREAKEVEN` + `## REFI OPPORTUNITY` + `## TAX` + `## VERDICT`.
  5. Every numeric field in the report carries citation footer `Computed by: scripts/{name}.py {args}` per Phase 11 stress-test-agent precedent.
  6. Eval: a new prompt `evals/prompts/property-analysis-01.md` exercises the full property mode against a pinned Zillow HTML fixture; oracle pins the expected verdict + 3 numeric fields. `python -m evals.runner` still exits 0 (route_match + numeric_match ≥ 0.95).

**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 15-01-PLAN.md — Wave 0: test scaffolding + synthetic fixtures + eval oracle stub (RPRT-01, RPRT-02, MODE-01..03)
- [x] 15-02-PLAN.md — Wave 1: `lib/property_report.py` AnalysisReport → markdown formatter (RPRT-01, RPRT-02)
- [x] 15-03-PLAN.md — Wave 1: `scripts/property_analyze.py` orchestrator (always-exit-0; sidecar listing; NNN sequencer) + `config/household.example.yml` extension (MODE-03)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 15-04-PLAN.md — Wave 2: `.claude/skills/mortgage-ops/modes/property.md` + SKILL.md Row 0 routing insertion (MODE-01, MODE-02)
- [x] 15-05-PLAN.md — Wave 2: `evals/prompts/property-analysis-01.md` + oracle reconciliation + evals.runner smoke (SC-6)

### Phase 16: Reference Data

**Goal**: Capture all v1.1 regulatory tables in YAML with citations + effective dates. Annual refresh = YAML edit, never code change.
**Depends on**: Phase 14 (analysis pipeline declares which tables it needs)
**Requirements**: REF-09, REF-10
**Success Criteria**:

  1. `data/reference/property-analysis-heuristics.yml` ships PMI rate tables (PMI by LTV band × FICO band — sourced from major-lender published schedules), FHA MIP defaults (upfront 1.75% + monthly 0.55-0.85% per LTV), VA funding fee defaults (per first-use × DP × veteran-type), jumbo cutoffs by county (2026 FHFA conforming limits — baseline $766k 1-unit, $1.149M high-cost).
  2. `data/reference/insurance-estimate-defaults.yml` ships per-state homeowners insurance avg annual cost (NAIC 2024 published averages) + FEMA flood-zone surcharge + earthquake-zone surcharge for California / Oregon / Washington.
  3. Every YAML row carries `citation`, `source` URL, `effective` date, `notes` per Phase 2 D-02 convention.
  4. Existing `lib/rules/_loader.py:_check_staleness` warns when `effective:` is > 12 months old.
  5. `lib/property_analysis.py` reads these YAMLs via the existing rules-loader; no inline constants for any regulatory threshold.

**Plans:** 4 plans

Plans:
**Wave 0**

- [ ] 16-01-PLAN.md — Wave 0: ship the two new YAMLs (PMI 4x4 + insurance 51-state) + two new lib/rules predicate modules (pmi.py + insurance.py) + 8 hand-calc fixture JSONs + citation-coverage-compliant tests (REF-09, REF-10)

**Wave 1**

- [ ] 16-02-PLAN.md — Wave 1: remove `_CONV_PMI_ANNUAL_RATE` Final constant + wire PMI block at L653 to `lib.rules.pmi.lookup_rate` + extend `_REPORT_WARNING_PREFIXES` aggregator at L1505 with 3 new tag families (REF-09; D-16-WIRE-02, D-16-WIRE-03)

**Wave 2** *(sequential after 16-02; same file `lib/property_analysis.py`, different line ranges)*

- [ ] 16-03-PLAN.md — Wave 2: wire insurance fallback at L702-705 via `lib.rules.insurance.lookup_default` with corrected trigger (branches on wrapper-presence, not unwrapped value; flood_zone hardcoded None per RESEARCH correction #1) (REF-10; D-16-WIRE-01, D-16-INS-04)

**Wave 3** *(blocked on 16-03 completion)*

- [ ] 16-04-PLAN.md — Wave 3: search-and-destroy the retired `PMI-RATE-ESTIMATED-0.0075` literal across 7 sites in `tests/test_property_analysis.py` + 3 Phase 14 fixture JSONs; re-anchor `condo_with_hoa_seattle.json` hand-calc PITI/DTI against the new YAML's MGIC rate (REF-09, REF-10; D-16-PMI-03)

### Phase 17: Tests + Fixtures

**Goal**: Pinned Zillow HTML snapshots for CI determinism + golden-value expected reports + citation-coverage meta-test.
**Depends on**: Phase 15 (needs the report formatter to pin against)
**Requirements**: TEST-01, TEST-02
**Success Criteria**:

  1. 5 pinned HTML fixtures at `tests/fixtures/zillow/` covering SFH-conforming / SFH-jumbo / condo-conforming / condo-with-HOA / multifamily-2-4. Each is a manual-capture from a real Zillow listing (cleaned of PII like agent contact info; URL anonymized).
  2. Each fixture has a paired `expected_report.md` golden file. The fixture HTML + expected report together pin the entire pipeline end-to-end.
  3. `tests/test_property_analysis_coverage.py` ships a citation-coverage meta-test: every numeric field in any `expected_report.md` must trace to either a PropertyListing field OR a script invocation OR a `data/reference/*.yml` row. No orphan numbers.
  4. Synthetic-only-in-CI: live WebFetch NEVER runs in CI per Phase 11 D-02 inheritance. Live-capture recipe documented in `tests/fixtures/zillow/README.md` for nightly regeneration.
  5. Full suite green at end of phase: 644 + N tests passing where N is the new property-analysis test count.

### Phase 18: References + Docs

**Goal**: Long-form documentation of the v1.1 pipeline + CLAUDE.md cross-links so future operators (and future-you) understand how property mode dispatches.
**Depends on**: Phase 15 + Phase 17 (need the report + tests to cite)
**Requirements**: REFS-01, REFS-02
**Success Criteria**:

  1. `.claude/skills/mortgage-ops/references/property-analysis.md` (≥ 250 lines, 6-section template + Citation Index appendix) documents: (a) ingestion pipeline (WebFetch + gap-fill + captcha detection), (b) 4-program × 6-DP fan-out algorithm, (c) verdict-synthesis rules, (d) DuckDB schema, (e) report layout contract, (f) 12 pitfalls from research §10.
  2. CLAUDE.md "Project Skills" section gains a `property` mode bullet referencing the new mode file + reference doc.
  3. SKILL.md references-table extended with `property-analysis.md` row (loaded on-demand per Phase 10 D-09 progressive-disclosure).
  4. `.claude/agents/README.md` updated if any new subagent ships (none expected in v1.1 — `property` is a mode, not a subagent; analysis runs in main context since reports are small).

## Backlog (v1.2+)

- **Comparable-properties analysis** — 5 similar nearby sales pulled from same source; compute median $/sqft and flag this listing as priced above/below median
- **Multi-source ingestion** — Redfin / Realtor.com / FSBO parsers
- **Tax-record + assessor data** — county-by-county pull
- **Watchlist mode** — `list listings`, `compare listings A B C`, `show me listings flagged GO in last 30d`
- **Saved-search alerts** — when a saved Zillow search has new listings under $X with verdict GO, notify (email or push)
- **Apify / scraper-API fallback** — if WebFetch degradation observed in real use, wire Apify Zillow Detail Scraper actor as secondary path
- **School / commute / walkability** — third-party API pulls per zip
- **Multi-property side-by-side** — comparison tables across a shortlist
