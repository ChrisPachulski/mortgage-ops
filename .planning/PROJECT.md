# mortgage-ops

## What This Is

Personal-use mortgage analysis tool for the Pachulski household — a sibling to `career-ops` and `card-ops`. Combines a deterministic Python calculation engine (amortization, ARM modeling, refi NPV, affordability, stress tests, points breakeven, estimated APR) with a Claude-skill frontend that routes natural-language requests to the right calc and produces human-readable reports. Built for making real household mortgage decisions, not commercial use.

## Core Value

**Math correctness first.** Every dollar figure that exits this system must be traceable to a tested, deterministic Python function. The LLM frontend is a router and narrator — it never owns numbers.

## Current State

**Shipped:** v1.0 (2026-05-13)
**Status:** Deterministic Python calc engine + Claude skill frontend live. 12 phases, 87 plans, 116 requirements, 644 pytest passing. Eval gate at `route_match=numeric_match=1.0`. See [v1.0 milestone archive](milestones/v1.0-ROADMAP.md) for the full closure receipt.

### Highlights
- Money discipline locked (Decimal-from-strings, ROUND_HALF_UP, condecimal)
- 11 regulatory predicates cited 1:1 (HMDA Platform pattern)
- 7 calc primitives with hand-calc fixtures: amortize, affordability, ARM, refi-NPV, APR (Reg Z App. J), stress, points
- DuckDB persistence + Node orchestration (`db-write.mjs` + `lockfile.mjs`)
- Claude skill frontend with 7 modes + 3 subagents (Haiku/Sonnet split for context isolation)
- Live FRED data + 22-prompt eval harness with 3-bucket gate (pass/fail/skip)

## Current Milestone: v1.1 Property Analysis Mode

**Goal:** Feed any Zillow listing URL → get a single-page underwriting workup that runs the full v1.0 calc engine (amortize × affordability × ARM × refi × stress × points × IRS Pub 936) against the property × household, with a clear GO / WATCH / NO-GO verdict.

**Target features (6 phases, ~14 requirements):**
- Zillow URL ingestion via hybrid pipeline — WebFetch + `__NEXT_DATA__` JSON extraction + interactive gap-fill when fields missing or ambiguous (no paid scraper API in v1.1; deferred to v1.2 if/when WebFetch degrades)
- `PropertyListing` Pydantic v2 model with `ProvenancedMoney` wrapper (every money field tagged `scraped | user_provided | estimated`)
- `lib/property_analysis.py` orchestrator that fans out across 4 loan programs (Conventional 30/15, FHA, VA, Jumbo) × 6 down-payment scenarios (3% / 5% / 10% / 15% / 20% / 25%) — ~24 amortization runs per property
- Auto-applied stress tests + points breakeven + refi opportunity scan + IRS Pub 936 deductibility rollup
- GO / WATCH / NO-GO verdict synthesis with reason list (DTI breach → NO-GO, ARM stress income shock → WATCH, all green → GO)
- DuckDB `analyzed_listings` table — auto-watchlist by accident; mirror Phase 9 lockfile pattern
- `property` mode in SKILL.md — URL-pin routing (substring `zillow.com` → `property` mode)
- Markdown report emitted to `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md` (mirror Phase 11 amortization-agent contract)
- 5 pinned Zillow HTML test fixtures for CI determinism (Phase 11 D-02 inherited — live WebFetch NEVER runs in CI)
- New regulatory YAMLs: `data/reference/property-analysis-heuristics.yml` + `insurance-estimate-defaults.yml` (PMI rate tables, FHA county limits, jumbo cutoffs by zip)

**Out of scope (deferred to v1.2+):**
- Redfin / Realtor.com / FSBO ingestion
- Comparable properties (5 similar nearby sales)
- County assessor / tax-record lookup
- School / commute / walkability
- Multi-property side-by-side
- Saved searches / price-drop alerts
- Paid scraper API integration (Apify / Bright Data / ScrapingBee)

**Research:** `.planning/research/v1.1-property-analysis.md` (997 lines; 9 locked patterns + 12 pitfalls + 8 open questions surfaced for /gsd-discuss-phase)

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Amortization schedules (fixed-rate, biweekly, extra principal payments)
- [ ] ARM modeling (5/1, 7/1, 10/1) with index + margin + caps + floor + reset logic
- [ ] Refinance NPV / breakeven analysis (cash-out and rate-and-term)
- [ ] Affordability ratios (DTI, LTV, CLTV, PITI, front-end / back-end)
- [ ] Affordability rule predicates (Fannie/Freddie/FHA/VA/USDA, one predicate per citation)
- [ ] Stress testing (rate shock, income shock, ARM reset parameter sweeps)
- [ ] Points breakeven analysis
- [ ] Estimated APR per Reg Z Appendix J (Newton-Raphson, labeled "estimated", validated against FFIEC tool)
- [ ] Household-aware data model (joint income, joint applicants, shared decisions)
- [ ] Pydantic v2 + condecimal Loan/Schedule/Payment models
- [ ] DuckDB persistence with lockfile pattern (from career-ops)
- [ ] Claude-skill frontend at `.claude/skills/mortgage-ops/` (modes architecture)
- [ ] `scripts/` bundled inside skill folder, not at project root (portability)
- [ ] `references/` folder for on-demand progressive disclosure
- [ ] Three subagents for context isolation: amortization-agent, refi-npv-agent, stress-test-agent
- [ ] FRED MCP integration (live MORTGAGE30US/MORTGAGE15US rate data)
- [ ] Reference data YAML files with source URLs + effective dates (FHFA, FHA, VA, IRS Pub 936)
- [ ] Test fixtures pinned to known-good golden values (Wikipedia, CFPB LE sample, computed)
- [ ] FFIEC APR Tool capture-as-fixture for Reg Z APR validation
- [ ] Freddie Mac SFLLD sample-quarter integration for statistical sanity checks
- [ ] `evals/` directory with skill quality benchmarks (skill-creator pattern)

### Out of Scope

- MISMO / ULDD XML — wrong layer for personal use; lender-to-GSE protocol
- Loan Estimate / Closing Disclosure PDF parsing — user enters numbers manually as YAML/dict
- Commercial DU / LPA replication — we model the published Eligibility Matrix, not the black-box AUS
- Strict Reg Z compliance — we label our APR "estimated"; not a regulated commercial tool
- Multi-currency support — US-only
- Property valuation models — Zestimate via Zillow MCP if needed later, not built here
- Loan origination workflows — read-only analysis tool, not a LOS

## Context

**Sibling repos (read for patterns, do not depend on):**
- `/Users/cujo253/Documents/career-ops` — DuckDB + lockfile + Python scoring engine pattern, modes architecture, batch runner, data contract (User/System/Data layers), Pydantic models, mode-driven skill routing
- `/Users/cujo253/Documents/card-ops` — household.yml concept, known-products YAML catalog, hand-calculated test assertions, reference docs library, parquet + YAML hybrid persistence

**Architectural decisions made before project init (from 5 prior research agents):**
1. Build on `numpy-financial` for core math (NOT reimplement). Wrap `pmt/ipmt/ppmt` — they support Decimal, vectorize, and use Excel-compatible signatures.
2. `Decimal` for money (construct from strings, quantize end-of-period, ROUND_HALF_UP for cents). Float for IRR/Newton solvers.
3. Pydantic v2 + `condecimal(max_digits=14, decimal_places=2)` for Loan/Schedule/Payment models.
4. `pyxirr` (Rust+PyO3) for batch refi-NPV scenarios when needed.
5. `python-dateutil` `relativedelta` for monthly date arithmetic (handles month-end edges).
6. Encode regulatory rules as **named predicates per citation** (cfpb/hmda-platform pattern): `reg_z.py`, `fannie_eligibility.py`, `fha_mip.py`, `va_funding_fee.py`, `irs_pub936.py`.
7. Reference data as YAML with source URLs + effective dates, refreshed manually annually. No silent scraping.
8. Bundle scripts INSIDE `.claude/skills/mortgage-ops/scripts/` (not at project root) for skill portability — career-ops/card-ops both miss this.
9. SKILL.md ≤ 500 lines / ≤ 5k tokens; load-bearing routing in first 5k tokens (post-compaction re-attach budget).
10. "Run `--help` first; do not read source" doctrine for bundled scripts (Anthropic webapp-testing skill convention).

**Test oracle fixtures (already identified):**
- Wikipedia: $200k @ 6.5% / 30yr → **$1,264.14**
- CFPB Loan Estimate sample: $162k @ 3.875% / 30yr → **$761.78**
- Computed: $400k @ 6.5% / 30yr → **$2,528.27**; $200k @ 7% / 15yr → **$1,797.66**
- Reg Z Appendix J commentary: $5,000 / 36 × $166.07 → 12.00% APR ± 0.005%
- FFIEC APR Tool — capture outputs as fixtures for APR validation
- Freddie Mac SFLLD sample quarter (free, no registration) — statistical sanity checks

**Live data sources (day one):**
- FRED MCP server (`stefanoamorelli/fred-mcp-server`) → `MORTGAGE30US`, `MORTGAGE15US` (mirrors PMMS)

**Regulatory data sources to track (refresh annually):**
- FHFA conforming loan limits (2026: $832,750 baseline / $1,249,125 ceiling)
- HUD/FHA loan limits (2026: $541,287 floor / $1,249,125 ceiling)
- FHA MIP rates (HUD Mortgagee Letter 2023-05)
- VA funding fee + residual income tables (Lender Handbook M26-7)
- USDA RD income limits (115% area median)
- IRS Pub 936 ($750k mortgage interest deduction cap, post-2017)
- CFPB ATR/QM (price-based General QM since 2022; 43% DTI cap is GONE — surface as heuristic only)

## Constraints

- **Tech stack**: Python 3.12+, numpy-financial, pydantic v2, pyxirr, python-dateutil, DuckDB. JS/Node only for skill orchestration scripts (mirror career-ops `db-write.mjs` pattern).
- **Scope**: Personal household use. Not a regulated commercial product. APR is "estimated".
- **Math discipline**: Decimal for money, never float. Construct from strings. Quantize end-of-period.
- **Test discipline**: Every formula has hand-calculated golden-value fixtures with citation in comments (card-ops `test_rewards_grocery_cap.py` pattern).
- **Privacy**: Strict `.gitignore` for household financial data. Personal config layer never auto-updated (career-ops Data Contract pattern).
- **Skill portability**: Skill must be self-contained — `scripts/`, `references/`, `assets/`, `LICENSE.txt` all inside `.claude/skills/mortgage-ops/`.
- **Token budget**: SKILL.md ≤ 500 lines, ≤ 5k tokens. Load-bearing content first.
- **Update cadence**: Regulatory YAML files refreshed annually (Nov-Dec for following year limits).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Wrap numpy-financial; do not reimplement amortization math | Active, BSD-3, Decimal support, vectorizes for parameter sweeps. Re-implementing risks subtle bugs. Identified via prior research. | — Pending |
| Encode rules as one-predicate-per-citation (HMDA Platform pattern) | Each function tied to a single regulatory citation makes annual refreshes safe and auditable. | — Pending |
| Pydantic v2 + condecimal over plain dataclasses | First-class Decimal support, JSON-string serialization (not float), runtime validation at boundaries. | — Pending |
| DuckDB + lockfile from career-ops, not parquet/YAML from card-ops | Mortgage analysis benefits from SQL across scenarios/loans; single-writer model is simpler than card-ops' file-based persistence for cross-scenario queries. | — Pending |
| Subagents (amortization, refi-npv, stress-test) for context isolation | Stress-test parameter sweeps (50+ scenarios) would pollute main conversation; subagents per Anthropic sub-agents docs. Career-ops/card-ops don't use this. | — Pending |
| FRED MCP day-one for live rates | Free, MORTGAGE30US mirrors Freddie PMMS, no auth needed. Bankrate/MND have no public MCP. | — Pending |
| APR labeled "estimated" — not Reg Z compliant | Personal use, not regulated. No public Python Appendix J implementation exists; Newton-Raphson against FFIEC tool fixtures is sufficient for our purposes. | — Pending |
| Skill conventions from anthropics/skills, not just career-ops/card-ops | Career-ops/card-ops both put scripts at project root (not portable). Lift `scripts/` + `references/` inside skill folder + `evals/` from skill-creator. | — Pending |
| Sequential plan execution within phases | User selected sequential; mortgage math has natural dependencies (models → core calcs → orchestration → skill frontend → evals). | — Pending |
| Fine granularity (8-12 phases) | User selected fine; each calc family is its own phase to keep test discipline tight. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-26 after initialization*
