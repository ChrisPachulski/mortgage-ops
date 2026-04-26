# Project Research Summary

**Project:** mortgage-ops
**Domain:** Personal-use mortgage analysis tool (Python calc engine + Claude skill frontend)
**Researched:** 2026-04-26
**Confidence:** HIGH

## Executive Summary

Mortgage-ops is a sibling repo to career-ops and card-ops, dedicated to mortgage analysis for the household. The pattern that works for this domain — and that the prior research strongly supports — is a **deterministic Python calc engine** (built on numpy-financial + Pydantic v2 + Decimal money discipline + DuckDB persistence) **fronted by a Claude skill** that routes natural-language requests to bundled scripts. The LLM is a router and narrator; it never owns numbers.

The 5-agent research effort surfaced three large-scale findings: (1) **numpy-financial is the right foundation** (active again in 2025, BSD-3, supports Decimal, vectorizes for parameter sweeps) — wrap it, don't reimplement; (2) the **Claude skills ecosystem has stronger conventions** than career-ops/card-ops yet adopt (`scripts/` inside the skill folder, `references/` for progressive disclosure, "run --help first" doctrine, evals harness) — we should lift those; (3) **regulatory data sources are stable but require manual annual refresh** — encode as cited YAML files, refresh once a year. There is no public Reg Z Appendix J APR implementation in any language, so we'll write Newton-Raphson against FFIEC tool fixtures and label our output "estimated".

Critical risks: (1) float-vs-Decimal money discipline — must lock in Phase 1; (2) ARM reset off-by-one and PMI/MIP termination rules — high-error-rate areas requiring dedicated phases; (3) regulatory drift — annual YAML refresh discipline plus startup-time staleness check.

## Key Findings

### Recommended Stack

Python 3.12+ calc engine with Pydantic v2 models, numpy-financial wrapped (not reimplemented), pyxirr for batch NPV, python-dateutil for date arithmetic, DuckDB single-file persistence with lockfile. Node side mirrors career-ops `db-write.mjs` pattern for skill orchestration.

**Core technologies:**
- **Python 3.12+ + Pydantic v2 condecimal** — Loan/Schedule/Payment models with first-class Decimal, JSON-string serialization (correct for finance APIs), runtime validation at script boundaries
- **numpy-financial** — Wrap PMT/IPMT/PPMT; supports Decimal; vectorizes for parameter sweeps. **Do not reimplement.** Watch bug #130 (fv-sign) and #131 (irr arch-dependent)
- **DuckDB + lockfile** (career-ops pattern) — Single-file ACID persistence; cross-scenario SQL queries; better than parquet+YAML (card-ops style) for scenario comparison
- **uv + ruff + mypy --strict + pytest** — Dev tooling. Career-ops/card-ops lack these; we adopt them day one
- **FRED MCP** (`stefanoamorelli/fred-mcp-server`) — Live MORTGAGE30US/MORTGAGE15US (mirrors PMMS); free; no key needed
- **Pyxirr** — Optional, for batch refi-NPV across 100+ scenarios (Rust+PyO3)

### Expected Features

User scoped "all" — every feature is in v1.

**Must have (table stakes):**
- Amortization schedule (fixed, biweekly, extra payments) — users expect this
- DTI / LTV / PITI / front-end-back-end ratios — qualification math
- Refinance NPV / breakeven — most-asked refi question
- Conforming vs jumbo classification — affects rates
- FHA / VA / USDA / conventional product modeling — household needs these comparable
- Live current rate context (FRED MCP)
- Household-aware applicant model — most US mortgages are joint
- Stress test (rate-shock, income-shock, ARM-reset)
- ARM 5/1, 7/1, 10/1 with caps/floor/margin/reset
- Points breakeven
- Estimated APR (Reg Z Appendix J)

**Should have (competitive):**
- Rules-as-predicates audit trail (one citation per predicate file — HMDA Platform pattern)
- Subagent-driven stress sweeps (context isolation)
- Reference data with cited source URLs + effective dates
- Hand-calculated golden-value tests (card-ops pattern)
- Skill-portable architecture (`scripts/` + `references/` inside skill folder)
- Eval harness (skill-creator pattern)

**Defer (v1.x or v2):**
- LE/CD PDF parsing — user enters numbers manually as YAML
- Annual regulatory data refresh script — manual refresh sufficient initially
- Zillow MCP for property valuation — only if user wants Zestimate context
- Web UI — markdown reports first
- Multi-property portfolio modeling — single primary residence first

### Architecture Approach

Three-layer architecture: (1) Claude skill at `.claude/skills/mortgage-ops/` routes natural-language requests to bundled `scripts/`; (2) Python `lib/` calc engine implements Pydantic-typed math, with `lib/rules/` predicates encoding regulations one-per-citation; (3) data layer combines DuckDB for scenarios/reports and YAML for regulatory reference data. Three subagents (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) provide context isolation for calc-heavy operations.

**Major components:**
1. **Claude skill (`.claude/skills/mortgage-ops/`)** — SKILL.md ≤ 500 lines with progressive disclosure to `references/`; bundled `scripts/` are black-box CLI helpers; `evals/` harness for skill quality
2. **Python lib (`lib/`)** — `models.py` (Pydantic), `amortize.py` (numpy-financial wrapper), `apr.py` (Newton-Raphson Reg Z), `refinance.py`, `affordability.py`, `stress.py`, `arm.py`, `rules/*.py` (one predicate per citation)
3. **Data layer (`data/`)** — `mortgage-ops.duckdb` (loans/scenarios/reports), `known-loans.yml` (catalog), `reference/*.yml` (regulatory data with source URL + effective date)
4. **Orchestration (`orchestration/`)** — Node scripts mirroring career-ops `db-write.mjs` for DuckDB writes
5. **Subagents (`.claude/agents/`)** — Three specialized agents for context-isolated calc sweeps

### Critical Pitfalls

1. **Float-based money math** — Cents drift over 360 periods; Decimal from strings, quantize end-of-period. Lock in Phase 1.
2. **Math inside the LLM (hallucinated numbers)** — Every dollar figure traces to a `scripts/` invocation. Hard rule in SKILL.md.
3. **Stale regulatory data** — All limits/fees in `data/reference/*.yml` with `source:` and `effective:`; startup-time staleness check.
4. **Reg Z Appendix J APR drift vs FFIEC** — Capture 20+ FFIEC fixtures; Newton-Raphson tolerance 10x tighter than ±0.005% requirement; label "estimated".
5. **ARM cap/floor/margin/reset off-by-one errors** — Document conventions in `references/arm-mechanics.md`; Pydantic model with explicit field names; test both reset-month conventions.
6. **PMI / MIP termination rules conflated** — Separate predicate files for HPA (conventional) vs HUD ML (FHA); origination_date parameter for FHA grandfathering.
7. **User layer auto-update** — DATA_CONTRACT.md enforces read-only User Layer; pre-commit hook prevents writes to `config/`.

## Implications for Roadmap

User selected **fine granularity (8-12 phases)** and **sequential** plan execution within phases. Suggested phase structure (12 phases, dependency-ordered):

### Phase 1: Foundations (models + money discipline)
**Rationale:** Decimal money discipline and Pydantic v2 condecimal models are the foundation. Every later phase depends on these. Locking them in early prevents Pitfall #1 (float drift) cascading.
**Delivers:** `lib/models.py` (Loan, Schedule, Payment), Decimal helpers, pyproject.toml + uv setup, CI pipeline (pytest + mypy --strict + ruff), DATA_CONTRACT.md, `config/household.example.yml`, golden-value test fixtures.
**Addresses:** Foundation for all features.
**Avoids:** Pitfall #1 (float math), Pitfall #10 (User Layer violation).

### Phase 2: Regulatory data + rules predicates
**Rationale:** Rules predicates with cited sources are independent of calc math. Building them next means downstream calc phases can compose them. Annual refresh discipline locked in.
**Delivers:** `data/reference/*.yml` (FHFA, FHA, VA, USDA, IRS), `lib/rules/*.py` (one predicate per citation), startup staleness check, `lib/rules/loan_type.py` with cfpb/jumbo-mortgage's "fail loud on missing county" pattern.
**Addresses:** Conforming/jumbo classification, FHA/VA/USDA fees, IRS Pub 936 deduction limits, ATR/QM (price-based test).
**Avoids:** Pitfall #3 (stale data), Pitfall #6 (PMI/MIP confusion), Pitfall #7 (loan-type confusion).

### Phase 3: Core amortization (fixed-rate + extra payments + biweekly)
**Rationale:** Simplest calc; everything else depends on it. Wrap numpy-financial; pin golden-value fixtures.
**Delivers:** `lib/amortize.py`, `scripts/amortize.py`, tests against Wikipedia + CFPB LE + computed fixtures.
**Uses:** numpy-financial PMT/IPMT/PPMT, Pydantic Schedule model.
**Avoids:** Pitfall #2 (LLM math), Pitfall #1 (float drift) propagating from Phase 1.

### Phase 4: Affordability (DTI/LTV/PITI + household model)
**Rationale:** Composes Phase 1 models + Phase 2 rules. Household-aware (joint income, joint applicants).
**Delivers:** `lib/affordability.py`, `scripts/affordability.py`, household.yml schema, tests for joint vs single applicant.
**Avoids:** Pitfall #6 (PMI/MIP), Pitfall #7 (loan-type), Pitfall #10 (User Layer).

### Phase 5: ARM modeling (5/1, 7/1, 10/1 with caps/floor/margin/reset)
**Rationale:** Highest off-by-one risk. Dedicated phase. Builds on Phase 3 amortization.
**Delivers:** `lib/arm.py`, `scripts/arm_simulate.py`, ARM Pydantic model, tests against published ARM scenarios + both reset-month conventions.
**Avoids:** Pitfall #5 (ARM off-by-one).

### Phase 6: Refinance NPV / breakeven / cash-out
**Rationale:** Composes amortization (Phase 3). Sign-convention errors are common; dedicated phase + subagent boundary.
**Delivers:** `lib/refinance.py`, `scripts/refi_npv.py`, both positive- and negative-NPV fixtures, optional pyxirr integration.
**Avoids:** Pitfall #8 (refi sign errors).

### Phase 7: Estimated APR (Reg Z Appendix J Newton-Raphson)
**Rationale:** No public Python implementation exists. High complexity. Single-issue dedicated phase.
**Delivers:** `lib/apr.py` (Newton-Raphson), 20+ FFIEC capture fixtures, tolerance tests, `references/apr-reg-z.md` documenting unit-period model.
**Avoids:** Pitfall #4 (APR drift).

### Phase 8: Points breakeven + stress tests
**Rationale:** Both compose amortization (Phase 3) + ARM (Phase 5). Stress tests benefit from subagent context isolation.
**Delivers:** `lib/points.py`, `lib/stress.py`, `scripts/points_breakeven.py`, `scripts/stress_test.py`, parameter-grid sweep tests.

### Phase 9: DuckDB persistence + Node orchestration
**Rationale:** Builds the data layer for storing scenarios/reports across sessions. Lockfile pattern prevents concurrency bugs.
**Delivers:** `orchestration/init-db.mjs`, `orchestration/db-write.mjs`, `orchestration/lockfile.mjs`, `data/mortgage-ops.duckdb` schema, render-markdown script.
**Avoids:** Concurrency bugs (career-ops lockfile pattern proven).

### Phase 10: Claude skill frontend (SKILL.md + modes/ + references/)
**Rationale:** Composes all prior phases. SKILL.md routes to scripts/. Progressive disclosure via references/.
**Delivers:** `.claude/skills/mortgage-ops/SKILL.md` (≤ 500 lines), `modes/*.md`, `references/*.md` (lifted patterns from anthropic xlsx skill), `LICENSE.txt`, frontmatter compatibility/license fields.
**Avoids:** Pitfall #2 (LLM math), Pitfall #9 (skill content overflow).

### Phase 11: Subagents (amortization-agent, refi-npv-agent, stress-test-agent)
**Rationale:** Context isolation for calc-heavy sweeps. Builds on Phase 10 skill scripts.
**Delivers:** Three subagent definitions in `.claude/agents/`, integration with stress mode, end-to-end test of a 50-scenario sweep returning summary < 1k tokens.

### Phase 12: FRED MCP integration + eval harness
**Rationale:** Final polish. Live rate context day-one (per user requirement); eval harness validates skill quality (skill-creator pattern, missing from career-ops/card-ops).
**Delivers:** FRED MCP wired in SKILL.md (`!\`fred-cli get MORTGAGE30US --latest\``), `evals/prompts/`, `evals/expected/`, `evals/runner.py`, README.md, ROADMAP for v1.x.

### Phase Ordering Rationale

- **Phase 1 first** — Decimal discipline cascades. Lock it before any math touches Pydantic.
- **Phase 2 before any calc** — Rules predicates are independent and used by every later phase. Refreshing them once is cheaper than refactoring 5 places.
- **Phase 3 (amortization) before Phase 5 (ARM)** — ARM composes amortization.
- **Phase 4 (affordability) before Phase 6 (refi)** — Refi NPV uses affordability checks for "should we refi?" eligibility.
- **Phase 7 (APR) standalone** — Doesn't gate other phases; can slot anywhere after Phase 3. Placed mid-roadmap for risk-balancing.
- **Phase 9 (persistence) before Phase 10 (skill)** — Skill writes reports to DuckDB; needs the schema.
- **Phase 10 (skill) before Phase 11 (subagents)** — Subagents are skill consumers.
- **Phase 12 (FRED + evals) last** — Polish; eval harness validates earlier phases retroactively.

### Research Flags

Phases likely needing deeper per-phase research during planning:
- **Phase 5 (ARM modeling):** Cap/floor/margin/reset conventions vary — Freddie/Fannie Selling Guides need direct citation. Hour-long Selling Guide read recommended.
- **Phase 7 (APR):** Reg Z Appendix J unit-period model + day-count conventions are subtle. Read Appendix J commentary worked examples + capture FFIEC fixtures before coding.
- **Phase 11 (subagents):** Anthropic sub-agent docs around context: fork, agent: Explore — patterns evolve; verify current frontmatter fields.

Phases with standard patterns (skip per-phase research):
- **Phase 1 (foundations):** Pydantic v2 + Decimal patterns are well-documented.
- **Phase 3 (amortization):** numpy-financial wrap is straightforward.
- **Phase 8 (points / stress):** Both are simple given Phase 3 + 5.
- **Phase 9 (persistence):** Career-ops `db-write.mjs` is direct prior art.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | numpy-financial / Pydantic v2 / DuckDB all verified against active repos |
| Features | HIGH | User scoped explicitly; mortgage feature set is well-defined |
| Architecture | HIGH | Career-ops/card-ops provide proven sibling pattern; Anthropic skills add missing portability conventions |
| Pitfalls | HIGH | All pitfalls have known recovery; APR + ARM are the two genuine risks but bounded |

**Overall confidence:** HIGH

### Gaps to Address

- **Reg Z Appendix J implementation reference**: No public Python implementation exists. Approach: Newton-Raphson against captured FFIEC tool fixtures; tolerance 10x tighter than ±0.005%. Document unit-period model and day-count conventions in `references/apr-reg-z.md`. Address during Phase 7.
- **ARM convention disambiguation**: "5/1 ARM" reset month varies (60 vs 61) by lender doc. Approach: Pydantic model with explicit `initial_period_months` and `reset_period_months`; document our convention; test both. Address during Phase 5.
- **Joint-applicant DTI handling**: Spousal income inclusion rules vary by loan type (FHA vs VA vs conventional). Approach: Per-loan-type predicate (one citation each). Address during Phase 4.
- **Annual regulatory refresh cadence**: First refresh after Nov 2026 (FHFA 2027 limits). Approach: Manual YAML edit + commit; defer automation to v1.x.

## Sources

### Primary (HIGH confidence)
- Career-ops repo deep-dive — `/Users/cujo253/Documents/career-ops` (DATA_CONTRACT.md, db-write.mjs, scoring/, lockfile.mjs)
- Card-ops repo deep-dive — `/Users/cujo253/Documents/card-ops` (test_rewards_grocery_cap.py, household.yml, lib/rules/)
- https://github.com/numpy/numpy-financial — main branch active 2025; bug tracker
- https://docs.pydantic.dev/2.x/api/types/ — condecimal, JSON-string Decimal serialization
- https://github.com/anthropics/skills — pdf, xlsx, webapp-testing, skill-creator conventions
- https://code.claude.com/docs/en/skills — frontmatter, progressive disclosure, compaction
- https://code.claude.com/docs/en/sub-agents — subagent isolation patterns
- https://www.consumerfinance.gov/rules-policy/regulations/1026/ — Reg Z Appendix J
- https://www.fhfa.gov/data/conforming-loan-limit — 2026 limits
- https://github.com/cfpb/hmda-platform — predicate-per-citation pattern (Scala)
- https://github.com/cfpb/jumbo-mortgage — fail-loud on missing county data
- https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset — SFLLD sample quarter
- https://www.ffiec.gov/resources/computational-tools/apr — APR Tool oracle (closed source)

### Secondary (MEDIUM confidence)
- https://pbpython.com/amortization-model-revised.html — pandas amortization pattern (port to Decimal)
- https://github.com/Anexen/pyxirr — pyxirr (active Nov 2025)
- https://github.com/austinmcconnell/mortgage — split_payment closed-form idiom (vendor only)
- https://github.com/jlumbroso/mortgage — Decimal patterns (read only)
- https://github.com/stefanoamorelli/fred-mcp-server — FRED MCP server
- HUD Mortgagee Letter 2023-05 — current FHA MIP rules
- VA Lender Handbook M26-7 — funding fee + residual income tables
- IRS Publication 936 — mortgage interest deduction ($750k cap post-2017)

### Tertiary (LOW confidence)
- https://github.com/maybe-finance/maybe — OSS personal finance reference (Ruby)
- https://github.com/firefly-iii/firefly-iii — OSS personal finance reference (PHP)
- https://blog.rittmananalytics.com/from-prompts-to-skills-automating-financial-and-kpi-analysis-in-looker-with-claude-skills-and-mcp-f5ed78380cc2 — case study: skill + MCP pairing

---
*Research completed: 2026-04-26*
*Ready for roadmap: yes*
