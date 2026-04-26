# Requirements: mortgage-ops

**Defined:** 2026-04-26
**Core Value:** Math correctness first — every dollar figure that exits this system must be traceable to a tested, deterministic Python function. The LLM frontend is a router and narrator; it never owns numbers.

## v1 Requirements

User selected "all" scope; everything below is in v1.

### Foundations

- [ ] **FND-01**: Project uses Decimal for all monetary fields, constructed from strings, with ROUND_HALF_UP cent quantization at end-of-period
- [ ] **FND-02**: Pydantic v2 models with `condecimal(max_digits=14, decimal_places=2)` for Loan, Schedule, Payment domain types
- [ ] **FND-03**: Strict typing enforced via `mypy --strict` in CI (no untyped code merges)
- [ ] **FND-04**: `pyproject.toml` with `uv` lockfile and reproducible installs
- [ ] **FND-05**: Linting via `ruff` enforced via pre-commit hook + CI
- [ ] **FND-06**: GitHub Actions CI runs pytest + mypy + ruff on every push (career-ops/card-ops both lack this)
- [ ] **FND-07**: `DATA_CONTRACT.md` defines User Layer / System Layer / Data Layer with read-only User Layer enforcement
- [ ] **FND-08**: `.gitignore` excludes household.yml, profile.yml, mortgage-ops.duckdb, reports/, and any user PII paths
- [ ] **FND-09**: Golden-value test fixtures pinned: Wikipedia ($200k @ 6.5%/30yr → $1,264.14), CFPB LE ($162k @ 3.875%/30yr → $761.78), computed ($400k @ 6.5%/30yr → $2,528.27; $200k @ 7%/15yr → $1,797.66)
- [ ] **FND-10**: Pre-commit hook prevents committing user-layer files (household.yml, profile.yml)

### Regulatory Reference Data

- [ ] **REF-01**: `data/reference/conforming-limits-2026.yml` with FHFA baseline + ceiling + per-county lookup, source URL, effective date
- [ ] **REF-02**: `data/reference/fha-limits-2026.yml` with FHA floor/ceiling + per-county lookup
- [ ] **REF-03**: `data/reference/fha-mip-rates.yml` with FHA UFMIP + annual MIP rates per term/LTV/loan-amount tier
- [ ] **REF-04**: `data/reference/va-funding-fees.yml` with first-use/subsequent-use/IRRRL/cash-out funding fee tables
- [ ] **REF-05**: `data/reference/va-residual-income.yml` with geographic × family-size × loan-amount residual income table
- [ ] **REF-06**: `data/reference/usda-income-limits.yml` with 115%-of-area-median income thresholds
- [ ] **REF-07**: `data/reference/irs-pub936.yml` with $750k cap (post-2017), $1M cap (grandfathered), points deductibility rules
- [ ] **REF-08**: Startup-time staleness check warns when any reference YAML's `effective:` date is > 12 months old
- [ ] **REF-09**: Tests assert every reference YAML has `source:` URL and `effective:` date fields

### Rules Predicates (one predicate per citation)

- [ ] **RUL-01**: `lib/rules/loan_type.py` classifies conforming / high-balance / jumbo / FHA / FHA-HB / VA / VA-HB / USDA based on county data; fails loud when county missing (cfpb/jumbo-mortgage pattern)
- [ ] **RUL-02**: `lib/rules/fannie_eligibility.py` implements LLPA matrix lookup (credit-score × LTV × loan-purpose tiers)
- [ ] **RUL-03**: `lib/rules/freddie_eligibility.py` implements equivalent LPA-published eligibility checks
- [ ] **RUL-04**: `lib/rules/fha_mip.py` implements MIP UFMIP + annual MIP per HUD ML 2023-05, with origination-date grandfathering
- [ ] **RUL-05**: `lib/rules/conventional_pmi.py` implements HPA auto-termination (78% LTV) and request-termination (80% LTV) rules
- [ ] **RUL-06**: `lib/rules/va_funding_fee.py` calculates VA funding fee per Lender Handbook M26-7
- [ ] **RUL-07**: `lib/rules/va_residual_income.py` evaluates residual income vs geographic × family-size × loan-amount table
- [ ] **RUL-08**: `lib/rules/usda.py` evaluates USDA income limits (115% area median) and guarantee fees
- [ ] **RUL-09**: `lib/rules/atr_qm.py` implements General QM price-based test (Mar 2021 final rule, replaces 43% DTI cap)
- [ ] **RUL-10**: `lib/rules/reg_z.py` implements Reg Z disclosures and tolerances (1/8 percentage point regular, 1/4 percentage point irregular)
- [ ] **RUL-11**: `lib/rules/irs_pub936.py` implements qualified loan limit worksheet ($750k post-2017 cap)
- [ ] **RUL-12**: Every rules predicate has docstring with regulatory citation
- [ ] **RUL-13**: 1:1 test-to-citation mapping: every predicate has at least one test fixture per citation

### Amortization

- [ ] **AMRT-01**: `lib/amortize.py` wraps numpy-financial PMT/IPMT/PPMT (does NOT reimplement)
- [ ] **AMRT-02**: Schedule generator handles fixed-rate loans (any term, any rate)
- [ ] **AMRT-03**: Schedule generator handles biweekly payment frequency (`relativedelta(weeks=2)`)
- [ ] **AMRT-04**: Schedule generator handles arbitrary extra principal payments (single, recurring, or per-period)
- [ ] **AMRT-05**: Final payment cleanup ensures balance reaches exactly $0.00 (no float drift)
- [ ] **AMRT-06**: `scripts/amortize.py` provides JSON-in / JSON-out CLI for skill use
- [ ] **AMRT-07**: Tests assert `sum(principal_payments) == original_principal` exactly
- [ ] **AMRT-08**: Tests pass against all four golden fixtures (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr)

### Affordability

- [ ] **AFFD-01**: `lib/affordability.py` calculates DTI (front-end and back-end) given household income + monthly debts
- [ ] **AFFD-02**: LTV calculation given loan amount + property value
- [ ] **AFFD-03**: CLTV calculation given loan amount + junior liens + property value
- [ ] **AFFD-04**: PITI calculation (P&I + property tax + insurance + HOA + PMI/MIP)
- [ ] **AFFD-05**: Reverse direction: "what loan amount can I qualify for given income X?" via `npf.pv` from max-affordable PMT
- [ ] **AFFD-06**: Household-aware: joint income, joint applicants, dual-credit-score handling
- [ ] **AFFD-07**: Affordability output cites the binding rule when blocking (e.g., "blocked by VA-RESIDUAL-WEST-FAMILY-4")
- [ ] **AFFD-08**: `scripts/affordability.py` provides JSON-in / JSON-out CLI
- [ ] **AFFD-09**: `config/household.example.yml` documents schema (joint income, applicants, monthly debts, location)

### ARM Modeling

- [ ] **ARM-01**: `lib/arm.py` Pydantic model with explicit `initial_period_months`, `reset_period_months`, `initial_cap_bps`, `periodic_cap_bps`, `lifetime_cap_bps`, `floor_rate`, `margin_bps`, `index_series_id`
- [ ] **ARM-02**: Supports 5/1, 7/1, 10/1, 5/6 (six-month) ARM products
- [ ] **ARM-03**: Reset logic: at month N+1 (start of next period), new rate = `min(prior_rate + periodic_cap, max(margin, index + margin))`, capped by lifetime cap
- [ ] **ARM-04**: Floor handling: new_rate >= max(margin, configured floor)
- [ ] **ARM-05**: Re-amortization at reset: remaining balance recasts over remaining term at new rate
- [ ] **ARM-06**: Tests against published ARM scenarios from MGIC or Bankrate calculators
- [ ] **ARM-07**: Tests verify both reset-month conventions (60 vs 61 for 5/1)
- [ ] **ARM-08**: `scripts/arm_simulate.py` provides JSON-in / JSON-out CLI
- [ ] **ARM-09**: `references/arm-mechanics.md` documents conventions with Freddie/Fannie Selling Guide citations

### Refinance

- [ ] **REFI-01**: `lib/refinance.py` calculates rate-and-term refi NPV (borrower perspective: outflows negative, savings positive)
- [ ] **REFI-02**: Cash-out refi modeling (new principal > old balance)
- [ ] **REFI-03**: Breakeven months: `closing_costs / monthly_savings` (simple) and NPV-based (proper)
- [ ] **REFI-04**: Optional `pyxirr` integration for batch NPV across many refi offers
- [ ] **REFI-05**: Tests with positive-NPV fixture (rate drop, low closing costs)
- [ ] **REFI-06**: Tests with negative-NPV fixture (same rate, high closing costs)
- [ ] **REFI-07**: Tests with cash-out fixture (proceeds, new balance, total interest comparison)
- [ ] **REFI-08**: `scripts/refi_npv.py` provides JSON-in / JSON-out CLI
- [ ] **REFI-09**: `references/refi-npv.md` documents sign convention explicitly

### Estimated APR (Reg Z Appendix J)

- [ ] **APR-01**: `lib/apr.py` Newton-Raphson solver against Reg Z Appendix J unit-period equation
- [ ] **APR-02**: Newton-Raphson seeded from `npf.rate(...)` (regular-transaction approximation)
- [ ] **APR-03**: Tolerance Decimal("0.00001") (10x tighter than Reg Z's ±0.005% requirement)
- [ ] **APR-04**: 20+ FFIEC APR Tool capture-as-fixture tests (varying loans, terms, advances)
- [ ] **APR-05**: Reg Z commentary worked example as fixture: $5,000 / 36 × $166.07 → 12.00% APR
- [ ] **APR-06**: User-facing output labeled "estimated APR" (not "APR")
- [ ] **APR-07**: `scripts/apr_reg_z.py` provides JSON-in / JSON-out CLI
- [ ] **APR-08**: `references/apr-reg-z.md` documents unit-period model + day-count conventions

### Stress Testing & Points

- [ ] **STRS-01**: `lib/stress.py` rate-shock sweep: re-solves PMT for grid of rates
- [ ] **STRS-02**: Income-shock sweep: recomputes DTI for grid of income reductions
- [ ] **STRS-03**: ARM-reset sweep: simulates rate path scenarios (parallel-shift, gradual-rise, fall-then-rise)
- [ ] **STRS-04**: `scripts/stress_test.py` provides JSON-in / JSON-out CLI; output includes scenario summary
- [ ] **PNTS-01**: `lib/points.py` calculates discount-points breakeven (`points_cost / monthly_savings = months`)
- [ ] **PNTS-02**: Cross-check NPV-based points decision (positive NPV ⇔ keep points; negative ⇔ skip)
- [ ] **PNTS-03**: `scripts/points_breakeven.py` provides JSON-in / JSON-out CLI
- [ ] **STRS-04**: Tests for stress sweeps include parameter-grid expected outputs

### Persistence (DuckDB)

- [ ] **PERS-01**: `data/mortgage-ops.duckdb` schema: loans, scenarios, reports, payments, applicants, properties tables
- [ ] **PERS-02**: `orchestration/init-db.mjs` idempotent schema initialization (career-ops pattern)
- [ ] **PERS-03**: `orchestration/db-write.mjs` central writer with subcommands: insert-loan, insert-scenario, insert-report, render-markdown, query
- [ ] **PERS-04**: `orchestration/lockfile.mjs` provides `withLock()` wrapper, stale recovery at 60s
- [ ] **PERS-05**: All writes wrapped in `withLock()` per career-ops pattern
- [ ] **PERS-06**: Markdown views (`data/loans.md`, `data/scenarios.md`) regenerated from DB, never edited by hand
- [ ] **PERS-07**: `data/known-loans.yml` catalog: 30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1, FHA 30yr, VA 30yr, jumbo

### Claude Skill Frontend

- [ ] **SKLL-01**: `.claude/skills/mortgage-ops/SKILL.md` ≤ 500 lines, ≤ 5k tokens
- [ ] **SKLL-02**: SKILL.md routing logic in first 200 lines (compaction re-attach budget)
- [ ] **SKLL-03**: SKILL.md frontmatter includes `name`, `description`, `license`, `compatibility`
- [ ] **SKLL-04**: `LICENSE.txt` bundled inside skill folder
- [ ] **SKLL-05**: Modes: evaluate, compare, refinance, affordability, stress, amortize, arm
- [ ] **SKLL-06**: `modes/_shared.md` defines scoring + report structure (career-ops pattern)
- [ ] **SKLL-07**: `modes/_profile.md` for user-specific overrides (gitignored)
- [ ] **SKLL-08**: `references/` folder with: amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions
- [ ] **SKLL-09**: References load on demand (progressive disclosure per Anthropic skill convention)
- [ ] **SKLL-10**: All `scripts/` bundled INSIDE `.claude/skills/mortgage-ops/scripts/` (NOT at project root)
- [ ] **SKLL-11**: SKILL.md instructs Claude to ALWAYS shell out to scripts for math; never compute inline
- [ ] **SKLL-12**: Scripts include `--help` first; "do not read source" doctrine documented (webapp-testing pattern)
- [ ] **SKLL-13**: Reports written to `reports/{###}-{slug}-{YYYY-MM-DD}.md` and ingested into DuckDB

### Subagents

- [ ] **SUBA-01**: `.claude/agents/amortization-agent.md` — Haiku, runs amortize/scripts; returns markdown table or CSV path
- [ ] **SUBA-02**: `.claude/agents/refi-npv-agent.md` — Sonnet (multi-step NPV reasoning), can sweep multiple offers
- [ ] **SUBA-03**: `.claude/agents/stress-test-agent.md` — Haiku, runs parameter-grid sweeps; returns < 1k token summary
- [ ] **SUBA-04**: Each subagent has `skills: [mortgage-ops]` frontmatter to preload skill content
- [ ] **SUBA-05**: Stress mode invokes stress-test-agent for sweeps > 5 scenarios
- [ ] **SUBA-06**: End-to-end test: 50-scenario stress sweep returns summary < 1k tokens to main context

### Live Data + Eval Harness

- [ ] **LIVE-01**: FRED MCP integration via `stefanoamorelli/fred-mcp-server` for MORTGAGE30US weekly rate
- [ ] **LIVE-02**: SKILL.md uses inline `!\`...\`` shell injection for current rate context at invocation
- [ ] **LIVE-03**: Cache FRED responses for 7 days max (FRED publishes weekly)
- [ ] **LIVE-04**: Optional FRED MORTGAGE15US for 15-year context
- [ ] **EVAL-01**: `evals/prompts/` with benchmark queries (one per mode minimum)
- [ ] **EVAL-02**: `evals/expected/` with expected calc routes + numeric outputs
- [ ] **EVAL-03**: `evals/runner.py` executes prompts against the skill, asserts route + output match
- [ ] **EVAL-04**: Eval harness regression-tests: every reported number traces back to a `scripts/` invocation (Pitfall #2 detection)

## v2 Requirements

Deferred to future releases. Tracked but not in current roadmap.

### Annual Refresh Automation

- **AUTO-01**: Playwright script that scrapes FHFA / HUD / IRS pages each November to draft updated YAMLs (manual review required)
- **AUTO-02**: Annual run notification reminding user to refresh `data/reference/`

### Document Parsing

- **PARSE-01**: Optional integration with `confersolutions/mcp-mortgage-server` for LE/CD PDF parsing
- **PARSE-02**: TRID compliance check (LE-vs-CD comparison)

### Property Valuation

- **PROP-01**: Optional integration with `sap156/zillow-mcp-server` for Zestimate context
- **PROP-02**: Property tax + insurance lookup by ZIP

### Portfolio

- **PORT-01**: Multi-property portfolio modeling (primary + investment)
- **PORT-02**: Tax basis tracking (cost basis, depreciation for rentals)

## Out of Scope

| Feature | Reason |
|---------|--------|
| MISMO / ULDD XML support | Lender-to-GSE protocol; consumers never see it; wrong layer for personal use |
| Loan Estimate / Closing Disclosure auto-parsing | Fragile; layouts change; user enters numbers manually as YAML — they need to read the LE anyway. Optional v2 if painful |
| Commercial DU / LPA replication | Lenders' AUS is proprietary black-box; we model the published Eligibility Matrix instead |
| Strict Reg Z compliance | We label our APR "estimated"; not a regulated commercial tool — would require legal review |
| Multi-currency support | US-only design; muddles money model |
| Real-time rate scraping (Bankrate, MND) | TOS violations; brittle; FRED MCP gives free official PMMS-mirror weekly |
| Auto-submit loan applications | Real consequences; no review opportunity; ethically prohibited |
| Web UI / web app | Skill = CLI; markdown reports + matplotlib for charts |
| Real-time household sync | Single-user, single-machine; sync-conflict hell |
| Prepayment penalty modeling | Uncommon in residential post-2014 (CFPB QM rules limit them) |
| Rate alerts / notifications | FRED weekly cadence sufficient |
| LOS workflows / origination | Read-only analysis tool, not a Loan Origination System |

## Traceability

Empty until `gsd-roadmapper` runs in the next step.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | TBD | Pending |
| ... | TBD | Pending |

**Coverage:**
- v1 requirements: 110 total (across 12 categories)
- Mapped to phases: 0 (pending roadmapper)
- Unmapped: 110 ⚠️

---
*Requirements defined: 2026-04-26*
*Last updated: 2026-04-26 after initial definition*
