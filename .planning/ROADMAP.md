# Roadmap: mortgage-ops

## Overview

Mortgage-ops delivers a deterministic Python calculation engine fronted by a Claude skill for personal household mortgage analysis. The roadmap is layered bottom-up: lock money discipline (Phase 1), encode regulatory rules as cited predicates (Phase 2), then build calc primitives (amortization → affordability → ARM → refi → APR → stress/points), persist scenarios (Phase 9), wire the skill frontend (Phase 10), add subagent isolation (Phase 11), and finish with live FRED data + an eval harness (Phase 12). Each phase produces a CLI script with golden-value tests; the LLM never owns numbers.

## Granularity

User selected **fine** (8-12 phases). This roadmap is **12 phases** — each calc family is its own phase to keep test discipline tight, and high-risk areas (ARM, refi NPV, APR) get dedicated phases rather than being bundled.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundations & Money Discipline** - Lock Decimal/Pydantic v2 models, CI pipeline, DATA_CONTRACT, golden-value fixtures
- [ ] **Phase 2: Regulatory Reference Data & Rules Predicates** - Cited YAML + one-predicate-per-citation library (2/7 plans complete)
- [ ] **Phase 3: Core Amortization** - Wrap numpy-financial; fixed-rate, biweekly, extra-principal schedules
- [ ] **Phase 4: Affordability** - DTI/LTV/CLTV/PITI + household-aware joint-applicant model
- [ ] **Phase 5: ARM Modeling** - 5/1, 7/1, 10/1, 5/6 with caps/floor/margin/reset and re-amortization
- [ ] **Phase 6: Refinance NPV** - Rate-and-term + cash-out, breakeven, sign-convention discipline
- [ ] **Phase 7: Estimated APR (Reg Z Appendix J)** - Newton-Raphson solver against FFIEC fixtures
- [ ] **Phase 8: Stress Tests & Points Breakeven** - Parameter sweeps + discount-points NPV
- [ ] **Phase 9: DuckDB Persistence & Node Orchestration** - Schema + lockfile + db-write.mjs writer
- [ ] **Phase 10: Claude Skill Frontend** - SKILL.md, modes/, references/, scripts/ bundle
- [ ] **Phase 11: Subagents** - amortization-agent, refi-npv-agent, stress-test-agent for context isolation
- [ ] **Phase 12: FRED MCP Live Rates & Eval Harness** - Live MORTGAGE30US + skill quality regression tests

## Phase Details

### Phase 1: Foundations & Money Discipline
**Goal**: Lock Decimal money discipline, Pydantic v2 domain models, strict CI, and the User/System/Data layer contract before any math touches the codebase
**Depends on**: Nothing (first phase)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-07, FND-08, FND-09, FND-10
**Success Criteria** (what must be TRUE):
  1. `Loan`, `Schedule`, `Payment` Pydantic v2 models reject float inputs to money fields and accept Decimal-from-string with `condecimal(max_digits=14, decimal_places=2)`
  2. `pytest`, `mypy --strict`, and `ruff` all pass on a clean checkout via `uv sync && uv run pytest && uv run mypy --strict . && uv run ruff check .`
  3. GitHub Actions CI workflow runs the full test+typecheck+lint matrix on push and blocks merges on failure
  4. Pre-commit hook rejects any staged change to `config/household.yml`, `config/profile.yml`, or `data/mortgage-ops.duckdb` with a clear "User Layer is read-only" error
  5. `tests/fixtures/` contains pinned golden-value JSON for all four oracles (Wikipedia $200k@6.5%/30yr→$1,264.14, CFPB LE $162k@3.875%/30yr→$761.78, computed $400k@6.5%/30yr→$2,528.27, computed $200k@7%/15yr→$1,797.66)
**Plans:** 6 plans
- [ ] 01-01-PLAN.md — pyproject.toml + uv.lock + repo skeleton (lib/, tests/, scripts/, config/, data/reference/, reports/) — FND-03/04/05/08
- [ ] 01-02-PLAN.md — DATA_CONTRACT.md (User/System/Data/Reference layers) + config/household.example.yml + config/profile.example.yml — FND-07
- [ ] 01-03-PLAN.md — lib/money.py (Decimal helpers: to_money, quantize_cents, MONEY_CONTEXT, CENT) + tests — FND-01
- [ ] 01-04-PLAN.md — lib/models.py (Pydantic v2 Loan/Schedule/Payment + Money/Rate Annotated aliases, strict + frozen + extra=forbid) + tests — FND-02
- [ ] 01-05-PLAN.md — tests/fixtures/golden_pmt.json (4 pinned oracles) + tests/test_fixtures.py — FND-09
- [ ] 01-06-PLAN.md — .gitignore + .github/workflows/ci.yml + .pre-commit-config.yaml + scripts/hooks/block-user-layer.py + branch-protection checkpoint — FND-06/10

### Phase 2: Regulatory Reference Data & Rules Predicates
**Goal**: Build the cited regulatory data layer (YAML with `source:` + `effective:`) and the one-predicate-per-citation rules library that every later calc phase composes
**Depends on**: Phase 1
**Requirements**: REF-01, REF-02, REF-03, REF-04, REF-05, REF-06, REF-07, REF-08, REF-09, RUL-01, RUL-02, RUL-03, RUL-04, RUL-05, RUL-06, RUL-07, RUL-08, RUL-09, RUL-10, RUL-11, RUL-12, RUL-13
**Success Criteria** (what must be TRUE):
  1. All seven `data/reference/*.yml` files load successfully and each contains `source:` URL + `effective:` date fields (asserted by test)
  2. Importing any `lib/rules/*` predicate when its underlying YAML's `effective:` is >12 months old emits a warning to stderr (staleness check)
  3. `lib.rules.loan_type.classify(amount, county)` returns the correct loan_type enum for fixtures across high-cost county at ceiling, low-cost county at baseline, FHA floor, FHA ceiling — and raises `MissingCountyDataError` (loud) when county is None
  4. `lib.rules.fha_mip.compute_mip(...)` produces correct UFMIP + annual MIP for both `LTV>90%` (life-of-loan) and `LTV<=90%` (11-year termination) cases per HUD ML 2023-05; `lib.rules.conventional_pmi.terminates_at(...)` returns 78% LTV (auto) and 80% LTV (request) per HPA
  5. Every predicate file has a docstring with a regulatory citation, and every citation has at least one passing test fixture (verified by `tests/test_rules/test_citation_coverage.py`)
**Plans**: TBD

### Phase 3: Core Amortization
**Goal**: Build the foundational amortization engine wrapping numpy-financial, supporting fixed-rate, biweekly, and arbitrary extra-principal schedules with no float drift
**Depends on**: Phase 1
**Requirements**: AMRT-01, AMRT-02, AMRT-03, AMRT-04, AMRT-05, AMRT-06, AMRT-07, AMRT-08
**Success Criteria** (what must be TRUE):
  1. `scripts/amortize.py --input fixtures/loan_400k_30yr_6_5.json` returns JSON whose `monthly_pi == "2528.27"` (exact Decimal string match) and final-row `balance == "0.00"`
  2. All four golden-fixture tests (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr) pass with exact equality (no `assertAlmostEqual`)
  3. Biweekly schedule (`frequency: biweekly`) produces 26 payments per year via `relativedelta(weeks=2)` with sum of all principal payments exactly equal to original principal
  4. Extra-principal scenario (single, recurring, and per-period inputs) shortens the schedule and final row still balances to `Decimal("0.00")`
  5. `scripts/amortize.py --help` prints usage without importing heavy deps; running with no input prints a clear schema-error message (Pydantic validation surfaces at the script boundary)
**Plans**: TBD

### Phase 4: Affordability
**Goal**: Compose Phase 1 models + Phase 2 rules into household-aware DTI/LTV/CLTV/PITI calculations and reverse-affordability ("what loan amount can I qualify for?")
**Depends on**: Phase 2, Phase 3
**Requirements**: AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-05, AFFD-06, AFFD-07, AFFD-08, AFFD-09
**Success Criteria** (what must be TRUE):
  1. `scripts/affordability.py` accepts a household JSON with joint income + joint applicants + monthly debts and returns front-end DTI, back-end DTI, LTV, CLTV, and PITI as exact Decimal strings
  2. Reverse-affordability mode given (max_dti=0.43, income, debts) returns `max_loan_amount` computed via `npf.pv` from max-affordable PMT, and the result feeds back through forward affordability within `Decimal("0.01")`
  3. When a binding rule blocks qualification (e.g., VA residual income failure), the output JSON includes a `blocked_by` field naming the predicate citation (e.g., `"blocked_by": "VA-RESIDUAL-WEST-FAMILY-4"`) — never silent
  4. `config/household.example.yml` is committed and documents the schema (joint income, applicants with credit scores, monthly debts, location); a fixture-based test loads it and runs through `scripts/affordability.py` end-to-end
  5. Joint-applicant test cases pass for both two-income households and dual-credit-score handling (lower-mid score selected per Fannie/Freddie convention)
**Plans**: TBD

### Phase 5: ARM Modeling
**Goal**: Model 5/1, 7/1, 10/1, 5/6 ARM products with explicit caps/floor/margin/reset semantics and verified handling of both reset-month conventions (60 vs 61)
**Depends on**: Phase 3
**Requirements**: ARM-01, ARM-02, ARM-03, ARM-04, ARM-05, ARM-06, ARM-07, ARM-08, ARM-09
**Success Criteria** (what must be TRUE):
  1. `lib.arm.ARMTerms` Pydantic model has explicit fields `initial_period_months`, `reset_period_months`, `initial_cap_bps`, `periodic_cap_bps`, `lifetime_cap_bps`, `floor_rate`, `margin_bps`, `index_series_id` (no implicit conventions)
  2. `scripts/arm_simulate.py` for a 5/1 ARM (initial_period=60, reset_period=12) produces a payment-jump at month 61 (not 60, not 62) and the new rate equals `min(prior_rate + periodic_cap, max(margin, index + margin))` capped by lifetime cap
  3. ARM tests pass against published MGIC/Bankrate scenarios AND explicitly include both reset-month conventions (60 and 61) as separate fixtures with documented expected outputs
  4. Floor rule enforced: post-reset rate is never below `max(margin, configured_floor)` — verified by a fixture where the index drop would otherwise breach the floor
  5. `references/arm-mechanics.md` documents the chosen reset convention with Freddie/Fannie Selling Guide citations and is referenced from the ARMTerms model docstring
**Plans**: TBD

### Phase 6: Refinance NPV
**Goal**: Calculate refinance NPV (rate-and-term + cash-out) and breakeven months from the borrower's perspective with sign-convention rigor enforced by Pydantic models
**Depends on**: Phase 3
**Requirements**: REFI-01, REFI-02, REFI-03, REFI-04, REFI-05, REFI-06, REFI-07, REFI-08, REFI-09
**Success Criteria** (what must be TRUE):
  1. `scripts/refi_npv.py` on a positive-NPV fixture (rate drops 200bps, $2k closing costs) returns NPV > 0 and on a negative-NPV fixture (same rate, $5k closing costs) returns NPV < 0 — sign convention verified
  2. Breakeven months reported in two forms: simple (`closing_costs / monthly_savings`) and NPV-based (months until cumulative NPV crosses zero); both labeled in the output JSON
  3. Cash-out refi fixture (new principal > old balance) reports correct cash proceeds, new monthly P&I, and total-interest delta vs old loan
  4. `RefiCashflow` Pydantic model has `direction: Literal["outflow", "inflow"]` field; constructing an outflow with positive amount or inflow with negative amount raises a validation error
  5. `references/refi-npv.md` documents the borrower-perspective sign convention explicitly ("outflows negative, savings positive") and is cited in the script's `--help` text
**Plans**: TBD

### Phase 7: Estimated APR (Reg Z Appendix J)
**Goal**: Implement Newton-Raphson APR solver against the Reg Z Appendix J unit-period equation, validated against 20+ FFIEC tool captures within a 10x-tighter tolerance than Reg Z requires
**Depends on**: Phase 3
**Requirements**: APR-01, APR-02, APR-03, APR-04, APR-05, APR-06, APR-07, APR-08
**Success Criteria** (what must be TRUE):
  1. `scripts/apr_reg_z.py` on the Reg Z commentary worked example ($5,000 / 36 × $166.07) returns APR within `Decimal("0.00001")` of 12.00%
  2. All 20+ FFIEC-captured fixtures (varying loan amounts, terms, advance schedules) pass with computed APR within `Decimal("0.00001")` of FFIEC tool output
  3. Newton-Raphson convergence test asserts iterations <= 50 for all fixtures (seeded from `npf.rate(...)` regular-transaction approximation)
  4. User-facing output strings always include the literal text "estimated APR" (never bare "APR") — enforced by a regex test on the JSON output schema
  5. `references/apr-reg-z.md` documents the unit-period model, day-count conventions, and odd-first-period handling with regulatory citations
**Plans**: TBD

### Phase 8: Stress Tests & Points Breakeven
**Goal**: Build parameter-sweep stress tests (rate-shock, income-shock, ARM-reset path) and discount-points breakeven analysis composing prior calc layers
**Depends on**: Phase 3, Phase 4, Phase 5
**Requirements**: STRS-01, STRS-02, STRS-03, STRS-04, PNTS-01, PNTS-02, PNTS-03
**Success Criteria** (what must be TRUE):
  1. `scripts/stress_test.py --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08` returns a parameter-grid JSON with new monthly P&I per rate, all values exact to the cent
  2. Income-shock sweep (`--mode income-shock --reductions 0.05,0.10,0.20`) recomputes back-end DTI for each reduction and flags which rows breach a configured affordability threshold
  3. ARM-reset sweep simulates parallel-shift, gradual-rise, and fall-then-rise rate paths over a 30-year horizon and returns total-interest-paid for each path
  4. `scripts/points_breakeven.py` reports breakeven months as `points_cost / monthly_savings` AND a parallel NPV-based decision; the two outputs disagree only when discount factors materially differ (documented with a fixture)
  5. Stress sweep with > 5 scenarios produces output suitable for subagent summarization (JSON < 100KB, scenario-summary table at the top)
**Plans**: TBD

### Phase 9: DuckDB Persistence & Node Orchestration
**Goal**: Wire DuckDB single-file persistence with the career-ops lockfile pattern and a Node `db-write.mjs` central writer for cross-scenario SQL queries and report storage
**Depends on**: Phase 1
**Requirements**: PERS-01, PERS-02, PERS-03, PERS-04, PERS-05, PERS-06, PERS-07
**Success Criteria** (what must be TRUE):
  1. `node orchestration/init-db.mjs` is idempotent — running it twice on a fresh checkout produces the same schema (loans, scenarios, reports, payments, applicants, properties tables) with no errors
  2. `node orchestration/db-write.mjs --insert-loan --json fixtures/loan.json` writes through `withLock()` and a concurrent second invocation either waits or fails fast (never corrupts) — verified by a parallel-invocation test
  3. Stale lockfile recovery triggers at 60s: a lockfile with `mtime > 60s ago` is reclaimed and the write proceeds (verified by a fixture that pre-creates an old lockfile)
  4. `data/loans.md` and `data/scenarios.md` regenerate from DuckDB via `node orchestration/db-write.mjs --render-markdown` and are byte-identical across runs (no hand-edits possible — file is regenerated from scratch)
  5. `data/known-loans.yml` catalog is committed with at least seven product entries (30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1, FHA 30yr, VA 30yr, jumbo) loadable via a smoke test
**Plans**: TBD

### Phase 10: Claude Skill Frontend
**Goal**: Build the `.claude/skills/mortgage-ops/` skill that routes natural-language requests to the bundled `scripts/`, with progressive-disclosure references and SKILL.md within token budget
**Depends on**: Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, Phase 9
**Requirements**: SKLL-01, SKLL-02, SKLL-03, SKLL-04, SKLL-05, SKLL-06, SKLL-07, SKLL-08, SKLL-09, SKLL-10, SKLL-11, SKLL-12, SKLL-13
**Success Criteria** (what must be TRUE):
  1. `.claude/skills/mortgage-ops/SKILL.md` is ≤ 500 lines and ≤ 5,000 tokens (verified by a CI check that runs a tokenizer); routing logic is in the first 200 lines
  2. SKILL.md frontmatter includes `name`, `description`, `license`, `compatibility` fields; `LICENSE.txt` is bundled inside the skill folder
  3. All seven calc scripts (`amortize.py`, `affordability.py`, `arm_simulate.py`, `refi_npv.py`, `apr_reg_z.py`, `stress_test.py`, `points_breakeven.py`) live INSIDE `.claude/skills/mortgage-ops/scripts/` (NOT at project root) — verified by a structure test
  4. All seven mode files (`evaluate.md`, `compare.md`, `refinance.md`, `affordability.md`, `stress.md`, `amortize.md`, `arm.md`) exist under `modes/`, plus `_shared.md` and `_profile.md`
  5. References folder contains all nine documents (amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions); SKILL.md instructs Claude to ALWAYS shell out to scripts and includes the "run --help first; do not read source" doctrine
**Plans**: TBD
**UI hint**: yes

### Phase 11: Subagents
**Goal**: Add three context-isolated subagents (amortization-agent, refi-npv-agent, stress-test-agent) so calc-heavy parameter sweeps don't pollute the main conversation
**Depends on**: Phase 10
**Requirements**: SUBA-01, SUBA-02, SUBA-03, SUBA-04, SUBA-05, SUBA-06
**Success Criteria** (what must be TRUE):
  1. `.claude/agents/amortization-agent.md`, `refi-npv-agent.md`, and `stress-test-agent.md` exist with valid frontmatter (`model:`, `skills: [mortgage-ops]`, description) — verified by a YAML parse test
  2. Stress mode in SKILL.md routes any sweep with > 5 scenarios to `stress-test-agent` (documented in `modes/stress.md` and tested by an eval prompt)
  3. End-to-end test: a 50-scenario rate-shock stress sweep dispatched through the subagent returns a summary < 1,000 tokens to the main context (token-counted via the eval harness)
  4. `refi-npv-agent` (Sonnet) successfully sweeps three competing refi offers and returns a ranked NPV table; `amortization-agent` (Haiku) returns a CSV path or markdown table for a single-loan amortization request
  5. Each subagent's `skills:` frontmatter resolves to the mortgage-ops skill at spawn time (verified by a smoke test that asserts the subagent has access to bundled scripts)
**Plans**: TBD

### Phase 12: FRED MCP Live Rates & Eval Harness
**Goal**: Wire FRED MCP for live MORTGAGE30US/MORTGAGE15US rate context and ship the eval harness that regression-tests skill quality across all modes
**Depends on**: Phase 10, Phase 11
**Requirements**: LIVE-01, LIVE-02, LIVE-03, LIVE-04, EVAL-01, EVAL-02, EVAL-03, EVAL-04
**Success Criteria** (what must be TRUE):
  1. SKILL.md uses inline `` !`fred-cli get MORTGAGE30US --latest` `` shell injection; running the skill in a fresh session injects the latest weekly rate into context (verified by an eval that asserts the rate appears)
  2. FRED responses cached for 7 days max in a local cache file; an 8-day-old cache entry triggers a refetch (verified by mocking time)
  3. `evals/runner.py evals/prompts/` executes all benchmark prompts and asserts each report's reported numbers trace back to a recorded `scripts/` invocation (Pitfall #2 detection — no LLM-hallucinated numbers)
  4. Eval harness reports `route_match_rate` (% of prompts where the right mode + scripts were invoked) and `numeric_match_rate` (% where reported numbers match expected within tolerance); both ≥ 95% on the v1 prompt set
  5. `evals/expected/` contains expected calc-routes + numeric outputs for at least one prompt per mode (evaluate, compare, refinance, affordability, stress, amortize, arm)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundations & Money Discipline | 6/6 | Complete (PASS-WITH-CAVEATS) | 2026-04-26 |
| 2. Regulatory Reference Data & Rules Predicates | 2/7 | In progress (02-01 + 02-02 green; FHA branch wired) | - |
| 3. Core Amortization | 0/TBD | Not started | - |
| 4. Affordability | 0/TBD | Not started | - |
| 5. ARM Modeling | 0/TBD | Not started | - |
| 6. Refinance NPV | 0/TBD | Not started | - |
| 7. Estimated APR (Reg Z Appendix J) | 0/TBD | Not started | - |
| 8. Stress Tests & Points Breakeven | 0/TBD | Not started | - |
| 9. DuckDB Persistence & Node Orchestration | 0/TBD | Not started | - |
| 10. Claude Skill Frontend | 0/TBD | Not started | - |
| 11. Subagents | 0/TBD | Not started | - |
| 12. FRED MCP Live Rates & Eval Harness | 0/TBD | Not started | - |

---
*Roadmap created: 2026-04-26*
