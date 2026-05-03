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

- [x] **REF-01**: `data/reference/conforming-limits-2026.yml` with FHFA baseline + ceiling + per-county lookup, source URL, effective date
- [x] **REF-02**: `data/reference/fha-limits-2026.yml` with FHA floor/ceiling + per-county lookup
- [x] **REF-03**: `data/reference/fha-mip-rates.yml` with FHA UFMIP + annual MIP rates per term/LTV/loan-amount tier
- [x] **REF-04**: `data/reference/va-funding-fees.yml` with first-use/subsequent-use/IRRRL/cash-out funding fee tables
- [x] **REF-05**: `data/reference/va-residual-income.yml` with geographic × family-size × loan-amount residual income table
- [x] **REF-06**: `data/reference/usda-income-limits.yml` with 115%-of-area-median income thresholds
- [x] **REF-07**: `data/reference/irs-pub936.yml` with $750k cap (post-2017), $1M cap (grandfathered), points deductibility rules
- [x] **REF-08**: Startup-time staleness check warns when any reference YAML's `effective:` date is > 12 months old
- [x] **REF-09**: Tests assert every reference YAML has `source:` URL and `effective:` date fields

### Rules Predicates (one predicate per citation)

- [x] **RUL-01**: `lib/rules/loan_type.py` classifies conforming / high-balance / jumbo / FHA / FHA-HB / VA / VA-HB / USDA based on county data; fails loud when county missing (cfpb/jumbo-mortgage pattern)
- [x] **RUL-02**: `lib/rules/fannie_eligibility.py` implements LLPA matrix lookup (credit-score × LTV × loan-purpose tiers)
- [x] **RUL-03**: `lib/rules/freddie_eligibility.py` implements equivalent LPA-published eligibility checks
- [x] **RUL-04**: `lib/rules/fha_mip.py` implements MIP UFMIP + annual MIP per HUD ML 2023-05, with origination-date grandfathering
- [x] **RUL-05**: `lib/rules/conventional_pmi.py` implements HPA auto-termination (78% LTV) and request-termination (80% LTV) rules
- [x] **RUL-06**: `lib/rules/va_funding_fee.py` calculates VA funding fee per Lender Handbook M26-7
- [x] **RUL-07**: `lib/rules/va_residual_income.py` evaluates residual income vs geographic × family-size × loan-amount table
- [x] **RUL-08**: `lib/rules/usda.py` evaluates USDA income limits (115% area median) and guarantee fees
- [x] **RUL-09**: `lib/rules/atr_qm.py` implements General QM price-based test (Mar 2021 final rule, replaces 43% DTI cap)
- [x] **RUL-10**: `lib/rules/reg_z.py` implements Reg Z disclosures and tolerances (1/8 percentage point regular, 1/4 percentage point irregular)
- [x] **RUL-11**: `lib/rules/irs_pub936.py` implements qualified loan limit worksheet ($750k post-2017 cap)
- [x] **RUL-12**: Every rules predicate has docstring with regulatory citation
- [x] **RUL-13**: 1:1 test-to-citation mapping: every predicate has at least one test fixture per citation

### Amortization

- [x] **AMRT-01**: `lib/amortize.py` wraps numpy-financial PMT/IPMT/PPMT (does NOT reimplement)
- [x] **AMRT-02**: Schedule generator handles fixed-rate loans (any term, any rate)
- [x] **AMRT-03**: Schedule generator handles biweekly payment frequency (`relativedelta(weeks=2)`)
- [x] **AMRT-04**: Schedule generator handles arbitrary extra principal payments (single, recurring, or per-period)
- [x] **AMRT-05**: Final payment cleanup ensures balance reaches exactly $0.00 (no float drift)
- [x] **AMRT-06**: `scripts/amortize.py` provides JSON-in / JSON-out CLI for skill use
- [x] **AMRT-07**: Tests assert `sum(principal_payments) == original_principal` exactly
- [x] **AMRT-08**: Tests pass against all four golden fixtures (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr)

### Affordability

- [x] **AFFD-01**: `lib/affordability.py` calculates DTI (front-end and back-end) given household income + monthly debts
- [x] **AFFD-02**: LTV calculation given loan amount + property value
- [x] **AFFD-03**: CLTV calculation given loan amount + junior liens + property value
- [x] **AFFD-04**: PITI calculation (P&I + property tax + insurance + HOA + PMI/MIP)
- [x] **AFFD-05**: Reverse direction: "what loan amount can I qualify for given income X?" via `npf.pv` from max-affordable PMT
- [x] **AFFD-06**: Household-aware: joint income, joint applicants, dual-credit-score handling
- [x] **AFFD-07**: Affordability output cites the binding rule when blocking (e.g., "blocked by VA-RESIDUAL-WEST-FAMILY-4")
- [x] **AFFD-08**: `scripts/affordability.py` provides JSON-in / JSON-out CLI
- [x] **AFFD-09**: `config/household.example.yml` documents schema (joint income, applicants, monthly debts, location)

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

- [x] **REFI-01**: `lib/refinance.py` calculates rate-and-term refi NPV (borrower perspective: outflows negative, savings positive)
- [x] **REFI-02**: Cash-out refi modeling (new principal > old balance)
- [x] **REFI-03**: Breakeven months: `closing_costs / monthly_savings` (simple) and NPV-based (proper)
- [ ] **REFI-04**: Optional `pyxirr` integration for batch NPV across many refi offers
- [x] **REFI-05**: Tests with positive-NPV fixture (rate drop, low closing costs)
- [x] **REFI-06**: Tests with negative-NPV fixture (same rate, high closing costs)
- [x] **REFI-07**: Tests with cash-out fixture (proceeds, new balance, total interest comparison)
- [x] **REFI-08**: `scripts/refi_npv.py` provides JSON-in / JSON-out CLI
- [x] **REFI-09**: `references/refi-npv.md` documents sign convention explicitly

### Estimated APR (Reg Z Appendix J)

- [x] **APR-01**: `lib/apr.py` Newton-Raphson solver against Reg Z Appendix J unit-period equation
- [x] **APR-02**: Newton-Raphson seeded from `npf.rate(...)` (regular-transaction approximation)
- [x] **APR-03**: Tolerance Decimal("0.00001") (10x tighter than Reg Z's ±0.005% requirement)
- [ ] **APR-04**: 20+ FFIEC APR Tool capture-as-fixture tests (varying loans, terms, advances)
- [x] **APR-05**: Reg Z commentary worked example as fixture: $5,000 / 36 × $166.07 → 12.00% APR
- [x] **APR-06**: User-facing output labeled "estimated APR" (not "APR")
- [x] **APR-07**: `scripts/apr_reg_z.py` provides JSON-in / JSON-out CLI
- [ ] **APR-08**: `references/apr-reg-z.md` documents unit-period model + day-count conventions

### Stress Testing & Points

- [ ] **STRS-01**: `lib/stress.py` rate-shock sweep: re-solves PMT for grid of rates
- [ ] **STRS-02**: Income-shock sweep: recomputes DTI for grid of income reductions
- [ ] **STRS-03**: ARM-reset sweep: simulates rate path scenarios (parallel-shift, gradual-rise, fall-then-rise)
- [ ] **STRS-04**: `scripts/stress_test.py` provides JSON-in / JSON-out CLI; output includes scenario summary; tests for stress sweeps include parameter-grid expected outputs
- [ ] **PNTS-01**: `lib/points.py` calculates discount-points breakeven (`points_cost / monthly_savings = months`)
- [ ] **PNTS-02**: Cross-check NPV-based points decision (positive NPV ⇔ keep points; negative ⇔ skip)
- [ ] **PNTS-03**: `scripts/points_breakeven.py` provides JSON-in / JSON-out CLI

> **Note:** STRS-04 was duplicated in the original requirements (one for the script CLI, one for sweep-test fixtures); the two have been merged into a single requirement above. Coverage count treats this as **one** requirement.

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

Mapped 2026-04-26 by gsd-roadmapper. Every v1 requirement is assigned to exactly one phase. See `.planning/ROADMAP.md` for phase goals + success criteria.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Pending |
| FND-02 | Phase 1 | Pending |
| FND-03 | Phase 1 | Pending |
| FND-04 | Phase 1 | Pending |
| FND-05 | Phase 1 | Pending |
| FND-06 | Phase 1 | Pending |
| FND-07 | Phase 1 | Pending |
| FND-08 | Phase 1 | Pending |
| FND-09 | Phase 1 | Pending |
| FND-10 | Phase 1 | Pending |
| REF-01 | Phase 2 | Done (02-01) |
| REF-02 | Phase 2 | Done (02-02) |
| REF-03 | Phase 2 | Done (02-02) |
| REF-04 | Phase 2 | Done (02-03) |
| REF-05 | Phase 2 | Done (02-03) |
| REF-06 | Phase 2 | Done (02-04) |
| REF-07 | Phase 2 | Done (02-04) |
| REF-08 | Phase 2 | Done (02-01) |
| REF-09 | Phase 2 | Done (02-01) |
| RUL-01 | Phase 2 | Done (02-01) |
| RUL-02 | Phase 2 | Done (02-05) |
| RUL-03 | Phase 2 | Done (02-05) |
| RUL-04 | Phase 2 | Done (02-02) |
| RUL-05 | Phase 2 | Done (02-05) |
| RUL-06 | Phase 2 | Done (02-03) |
| RUL-07 | Phase 2 | Done (02-03) |
| RUL-08 | Phase 2 | Done (02-04) |
| RUL-09 | Phase 2 | Done (02-06) |
| RUL-10 | Phase 2 | Done (02-06) |
| RUL-11 | Phase 2 | Done (02-04) |
| RUL-12 | Phase 2 | Done (02-01) |
| RUL-13 | Phase 2 | Done (02-01) |
| AMRT-01 | Phase 3 | Done (03-02) |
| AMRT-02 | Phase 3 | Done (03-02) |
| AMRT-03 | Phase 3 | Done (03-02) |
| AMRT-04 | Phase 3 | Done (03-02) |
| AMRT-05 | Phase 3 | Done (03-02) |
| AMRT-06 | Phase 3 | Done (03-03) |
| AMRT-07 | Phase 3 | Done (03-04) |
| AMRT-08 | Phase 3 | Done (03-04) |
| AFFD-01 | Phase 4 | Done (04-06) |
| AFFD-02 | Phase 4 | Done (04-06) |
| AFFD-03 | Phase 4 | Done (04-06) |
| AFFD-04 | Phase 4 | Done (04-06) |
| AFFD-05 | Phase 4 | Done (04-06) |
| AFFD-06 | Phase 4 | Done (04-06) |
| AFFD-07 | Phase 4 | Complete |
| AFFD-08 | Phase 4 | Complete |
| AFFD-09 | Phase 4 | Complete |
| ARM-01 | Phase 5 | Pending |
| ARM-02 | Phase 5 | Pending |
| ARM-03 | Phase 5 | Pending |
| ARM-04 | Phase 5 | Pending |
| ARM-05 | Phase 5 | Pending |
| ARM-06 | Phase 5 | Pending |
| ARM-07 | Phase 5 | Pending |
| ARM-08 | Phase 5 | Pending |
| ARM-09 | Phase 5 | Pending |
| REFI-01 | Phase 6 | Implemented (Plan 06-02 + 06-05 — engine layer + 3 fixture-driven test flips: test_refi_rate_and_term_positive_npv + test_refi_rate_and_term_negative_npv + test_refi_npv_decimal_exact all PASS) |
| REFI-02 | Phase 6 | Implemented (Plan 06-03 + 06-05 — engine layer + 3 fixture-driven test flips: test_refi_cash_out_proceeds + test_refi_cash_out_new_monthly_pi + test_refi_cash_out_total_interest_delta all PASS) |
| REFI-03 | Phase 6 | Implemented (Plan 06-02 + 06-05 — _compute_breakeven_simple + _compute_breakeven_npv helpers + 3 fixture-driven test flips: test_refi_breakeven_simple_labeled + test_refi_breakeven_npv_labeled + test_refi_breakeven_divergence_documented all PASS; D-06 cumulative-NPV scan correctly returns 'never_breaks_even' when horizon truncation prevents cumulative >= 0) |
| REFI-04 | Phase 6 | Pending (Phase 11 SUBA-02 deferral per D-07; REFI-04 says "Optional pyxirr integration" — Phase 6 ships docstring deferral + lib/refinance.py module-docstring "Phase 11 migration note" marker; Plan 06-05 ships test_pyxirr_deferred_to_phase11_documented PASS asserting the docstring deferral) |
| REFI-05 | Phase 6 | Implemented (Plan 06-05 — tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json shipped with engine-derived expected values pinned via Decimal equality; Oracle 1 NPV=60705.48; test_refi_rate_and_term_positive_npv PASS) |
| REFI-06 | Phase 6 | Implemented (Plan 06-05 — tests/fixtures/refinance/negative_npv_short_horizon.json shipped with engine-derived expected values pinned via Decimal equality; Oracle 2 NPV=-718.01 via D-13 horizon=12 truncation; test_refi_rate_and_term_negative_npv PASS) |
| REFI-07 | Phase 6 | Implemented (Plan 06-03 + 06-05 — Oracle 3 cash-out engine-derived values pinned end-to-end + tests/fixtures/refinance/cash_out_proceeds_50k.json shipped with cash_proceeds=47000.00, npv=36996.30, total_interest_delta=145706.07 pinned via Decimal equality; 3 SC-3 surface tests PASS) |
| REFI-08 | Phase 6 | Implemented (Plan 06-04 + 06-05 — scripts/refi_npv.py CLI shipped 253 lines + sign_validator_outflow_positive.json fixture exercises CLI round-trip rejection via discount_rate_annual='1.5' above Pydantic Rate le=1 → exit 2 + 6-key WR-02 envelope; 6 Wave-4 CLI stub flips + 1 Wave-5 fixture-side coverage PASS) |
| REFI-09 | Phase 6 | Implemented (Plan 06-06 — references/refi-npv.md 630-line sign-convention doc shipped at project root with SC-5 verbatim phrase 'outflows negative, savings positive' surfaced 3× in §1 headline section + 8 numbered H2 sections [Sign Convention + Borrower NPV Formula + Discount-Rate Selection + Cashflow Inventory + Simple vs NPV Breakeven + After-Tax Mode + v1 Carve-Outs + Citations] + appendix Citation Index; cites Investopedia + Federal Reserve + CFPB + IRS Pub 936 + numpy-financial v1.0.0 + numpy-financial bug #131 + FHFA 2023; D-13 horizon-truncation rationale + D-08 PMI/MIP carve-out + D-07 pyxirr Phase 11 deferral all documented; D-01..D-16 cross-reference table; mirrors references/arm-mechanics.md template; D-16 belt-and-suspenders surface 3 closed; 2 Wave-0 doc stub flips PASS; closes SC-5 + REFI-09; PHASE 6 CLOSES CLEAN) |
| APR-01 | Phase 7 | Done (07-01 + 07-02 — Pydantic v2 boundary models in Plan 07-01 + Newton-Raphson body in Plan 07-02 against Reg Z Appendix J unit-period equation) |
| APR-02 | Phase 7 | Done (07-02 — _seed_apr via npf.rate with NaN/inf/range fallback to nominal-rate-of-return then 0.005 last-resort per D-11) |
| APR-03 | Phase 7 | Done (07-02 — TOLERANCE = Decimal("0.00001") + DOLLAR_RESIDUAL = Decimal("0.01") D-10 dual-criterion convergence; 125x tighter than Reg Z's regular-transaction ±1/8 pp = Decimal("0.00125")) |
| APR-04 | Phase 7 | Pending |
| APR-05 | Phase 7 | Done (07-05 — tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json shipped per D-25 LOCKED regulatory value Decimal('0.120000'); test_apr_reg_z_appendix_j_worked_example_returns_12_percent flipped to PASS asserting engine within Decimal('0.00001') of regulatory anchor; engine emits 0.119994 in 1 iteration, diff 0.000006 within tolerance) |
| APR-06 | Phase 7 | Done (07-04 — literal 'estimated APR' contract enforced end-to-end through the CLI surface: D-22 three-layer enforcement combining (a) Pydantic @model_validator on APRResponse.summary [Wave 1 D-05] + (b) literal phrase 4x in scripts/apr_reg_z.py module docstring + epilog body x3 [Wave 4 D-22] + (c) regex test test_apr_response_uses_literal_estimated_apr_text via re.search r'\\bAPR\\b(?!\\s*tolerance)' [Wave 4 flip]) |
| APR-07 | Phase 7 | Done (07-04 — scripts/apr_reg_z.py 184 lines mirroring scripts/arm_simulate.py byte-for-byte: argparse + --input + sys.path injection + lazy-import block (D-18) + JSON-float gate via scripts._cli_helpers + Pydantic ValidationError + APRConvergenceError 6-key envelope per D-21 + happy-path APRResponse.model_dump_json on stdout exit 0; test_apr_cli_subprocess_round_trip on SC-1 anchor inputs returns estimated_apr=0.119994 within Decimal('0.00001') of 0.120000 in 1 Newton iter) |
| APR-08 | Phase 7 | Pending |
| STRS-01 | Phase 8 | Pending |
| STRS-02 | Phase 8 | Pending |
| STRS-03 | Phase 8 | Pending |
| STRS-04 | Phase 8 | Pending |
| PNTS-01 | Phase 8 | Pending |
| PNTS-02 | Phase 8 | Pending |
| PNTS-03 | Phase 8 | Pending |
| PERS-01 | Phase 9 | Pending |
| PERS-02 | Phase 9 | Pending |
| PERS-03 | Phase 9 | Pending |
| PERS-04 | Phase 9 | Pending |
| PERS-05 | Phase 9 | Pending |
| PERS-06 | Phase 9 | Pending |
| PERS-07 | Phase 9 | Pending |
| SKLL-01 | Phase 10 | Pending |
| SKLL-02 | Phase 10 | Pending |
| SKLL-03 | Phase 10 | Pending |
| SKLL-04 | Phase 10 | Pending |
| SKLL-05 | Phase 10 | Pending |
| SKLL-06 | Phase 10 | Pending |
| SKLL-07 | Phase 10 | Pending |
| SKLL-08 | Phase 10 | Pending |
| SKLL-09 | Phase 10 | Pending |
| SKLL-10 | Phase 10 | Pending |
| SKLL-11 | Phase 10 | Pending |
| SKLL-12 | Phase 10 | Pending |
| SKLL-13 | Phase 10 | Pending |
| SUBA-01 | Phase 11 | Pending |
| SUBA-02 | Phase 11 | Pending |
| SUBA-03 | Phase 11 | Pending |
| SUBA-04 | Phase 11 | Pending |
| SUBA-05 | Phase 11 | Pending |
| SUBA-06 | Phase 11 | Pending |
| LIVE-01 | Phase 12 | Pending |
| LIVE-02 | Phase 12 | Pending |
| LIVE-03 | Phase 12 | Pending |
| LIVE-04 | Phase 12 | Pending |
| EVAL-01 | Phase 12 | Pending |
| EVAL-02 | Phase 12 | Pending |
| EVAL-03 | Phase 12 | Pending |
| EVAL-04 | Phase 12 | Pending |

**Coverage:**

| Phase | Requirements Mapped | Count |
|-------|---------------------|-------|
| Phase 1: Foundations & Money Discipline | FND-01..10 | 10 |
| Phase 2: Regulatory Reference Data & Rules Predicates | REF-01..09, RUL-01..13 | 22 |
| Phase 3: Core Amortization | AMRT-01..08 | 8 |
| Phase 4: Affordability | AFFD-01..09 | 9 |
| Phase 5: ARM Modeling | ARM-01..09 | 9 |
| Phase 6: Refinance NPV | REFI-01..09 | 9 |
| Phase 7: Estimated APR | APR-01..08 | 8 |
| Phase 8: Stress Tests & Points Breakeven | STRS-01..04, PNTS-01..03 | 7 |
| Phase 9: DuckDB Persistence & Node Orchestration | PERS-01..07 | 7 |
| Phase 10: Claude Skill Frontend | SKLL-01..13 | 13 |
| Phase 11: Subagents | SUBA-01..06 | 6 |
| Phase 12: FRED MCP Live Rates & Eval Harness | LIVE-01..04, EVAL-01..04 | 8 |
| **Total** | | **116** |

- v1 requirements: 116 unique IDs across 13 categories (note: original draft said 110 — recount shows 116 once REF/RUL/SKLL fully enumerated; one duplicate STRS-04 in source merged into a single requirement)
- Mapped to phases: 116 ✓
- Unmapped: 0 ✓
- Phases without requirements: 0 ✓

---
*Requirements defined: 2026-04-26*
*Last updated: 2026-04-26 — traceability populated by gsd-roadmapper*
