# Feature Research

**Domain:** Personal-use mortgage analysis tool
**Researched:** 2026-04-26
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

These are non-negotiable for a household to make real mortgage decisions.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Amortization schedule (fixed-rate) | The single most-asked mortgage question | LOW | Wrap `npf.pmt/ipmt/ppmt`. Test against Wikipedia + CFPB LE samples |
| Total interest paid over life of loan | Standard headline number | LOW | `sum(ipmt(...))` |
| Monthly P&I calculation | Standard headline number | LOW | `npf.pmt(...)` |
| Property tax + homeowners insurance + HOA + PMI/MIP layered (PITI) | What you actually pay each month | MEDIUM | Lookup MIP/PMI from rules predicates |
| Down payment / LTV calculation | Required to determine PMI, jumbo status | LOW | `loan_amount / property_value` |
| Conforming vs jumbo classification | Affects rates, MIP/PMI rules | LOW | County-level limits from FHFA YAML |
| FHA / VA / USDA / conventional loan-type modeling | Each has different rules + fees | MEDIUM | One predicate file per loan type |
| Refinance breakeven (months to recover closing costs) | Most common refi question | MEDIUM | `closing_costs / monthly_savings` |
| Refinance NPV (rate-and-term) | Quantifies actual lifetime benefit | HIGH | Discount future cashflows; pyxirr |
| Extra principal payment scenarios | "What if I pay $200 extra per month?" | LOW | Generator with `addl_principal` (pbpython pattern) |
| Biweekly payment scenarios | Common interview-question feature | LOW | `relativedelta(weeks=2)` schedule |
| ARM 5/1, 7/1, 10/1 modeling | Half of new mortgages today | HIGH | Index + margin + caps + floor + reset logic |
| ARM rate-shock projection | "What's my payment if SOFR goes to X?" | HIGH | Sweep over index path |
| DTI ratio (front-end / back-end) | Determines qualification | LOW | `monthly_debt / monthly_gross_income` |
| Affordability "what loan amount can I qualify for?" | Reverse-direction calc | MEDIUM | DTI cap → max payment → max principal via `npf.pv` |
| Stress test: rate shock | "What if rates jump 200bps before close?" | MEDIUM | Re-solve PMT for new rate |
| Stress test: income shock | "What if one earner loses job?" | MEDIUM | Recompute DTI with reduced income |
| Points breakeven | "Are these discount points worth it?" | LOW | `points_cost / monthly_savings` |
| Cash-out refi modeling | Common life-event scenario | MEDIUM | Same as refi but with new principal > old balance |
| Loan comparison side-by-side | "30yr vs 15yr; FHA vs conventional" | MEDIUM | Multi-scenario report generator |
| Live current rate context | What do today's rates look like? | LOW | FRED MCP `MORTGAGE30US`, `MORTGAGE15US` |
| Household-aware applicant modeling | Joint income, joint applicants — most US mortgages are joint | MEDIUM | `household.yml` with both applicants' income/credit/assets |

### Differentiators (Competitive Advantage)

These set this tool apart from Bankrate/NerdWallet calculators.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Estimated APR per Reg Z Appendix J | No public Python implementation exists; lenders' APR is auditable | HIGH | Newton-Raphson against unit-period equation; validated vs FFIEC tool fixtures |
| Rules-as-predicates audit trail | Every rule cites its regulation (12 CFR §X, HUD ML Y) | MEDIUM | One predicate per citation (HMDA Platform pattern) |
| Subagent-driven stress sweeps | Sweep 50+ ARM scenarios without polluting main context | MEDIUM | Three subagents: amortization, refi-npv, stress-test |
| Reference data with source URLs + effective dates | YAML files cite their HUD/IRS/FHFA source — auditable refresh | LOW | One YAML per regulator |
| Hand-calculated golden-value tests | Every formula has expected value pinned with comment | LOW | Card-ops pattern (test_rewards_grocery_cap.py) |
| Skill-portable architecture | scripts/ + references/ inside skill folder, not at project root | LOW | Anthropic pdf/xlsx skill pattern; career-ops/card-ops both miss this |
| Live FRED rate context at invocation | Current 30yr rate injected via `!\`...\`` shell at skill load | LOW | FRED MCP server |
| Eval harness for skill quality | Benchmark prompts → expected calc routes | MEDIUM | skill-creator pattern |
| Household joint optimization | Should we both be on the loan? Joint vs single-applicant comparison | MEDIUM | Many couples optimize wrong here; non-trivial |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-submit loan applications | Convenience | Real consequences, regulatory exposure, no review | Generate filled-out forms; user submits |
| Real-time rate scraping (Bankrate, MND) | "Always-current rates" | TOS violations; brittle; cache-invalidation hell | FRED MCP (free, official, weekly = sufficient) |
| LE/CD PDF auto-parsing | "Skip data entry" | Fragile; layouts change; no standard | User enters numbers manually as YAML — they need to read the LE anyway |
| Black-box AUS (DU/LPA) replication | "Will I qualify?" | Lenders' AUS is proprietary; we'd be wrong | Model the published Eligibility Matrix (LLPA matrix → YAML lookup) |
| Strict Reg Z compliance | "Real APR" | We'd need legal review, audits, etc. | Label our APR "estimated"; validate against FFIEC tool |
| MISMO/ULDD XML support | "Industry standard" | Lender-to-GSE protocol; consumers never see it | Skip |
| Property valuation models | "What's the house worth?" | Out of scope; Zestimate is a separate problem | Optional Zillow MCP if user demands it later |
| Browser UI / web app | "Pretty UI" | Skill = CLI; web app is a different project | Markdown reports + matplotlib for charts |
| Multi-currency | "International support" | US-only design; muddles money model | Skip |
| Real-time household sync | "My partner can update too" | Single-user, single-machine; sync-conflict hell | One household.yml, manual git sync if needed |

## Feature Dependencies

```
[Loan model (Pydantic)]
    └──requires──> [Decimal money discipline]
                       └──requires──> [Test fixtures pinned]

[Amortization schedule]
    └──requires──> [Loan model]
    └──requires──> [numpy-financial wrapper]

[ARM modeling]
    └──requires──> [Amortization schedule]
    └──requires──> [Index history (FRED MCP)]
    └──requires──> [Caps/floor/margin model]

[Refinance NPV]
    └──requires──> [Amortization schedule]
    └──requires──> [pyxirr or npf.npv]
    └──requires──> [Closing cost model]

[Affordability / DTI / LTV]
    └──requires──> [Loan model]
    └──requires──> [Household income model]
    └──requires──> [Rules predicates per loan type]

[Stress tests]
    └──requires──> [Amortization schedule]
    └──requires──> [ARM modeling]
    └──requires──> [Subagent infrastructure for parameter sweeps]

[Estimated APR (Reg Z Appendix J)]
    └──requires──> [Newton-Raphson solver]
    └──requires──> [FFIEC capture-as-fixture corpus]

[Skill frontend]
    └──requires──> [All Python scripts JSON in/out]
    └──requires──> [Modes architecture]
    └──requires──> [References/ progressive disclosure]

[Subagents]
    └──requires──> [Skill scripts]
    └──enhances──> [Stress tests]
    └──enhances──> [Refi NPV across many offers]

[Reports / artifacts]
    └──requires──> [DuckDB persistence]
    └──requires──> [Lockfile pattern]
```

### Dependency Notes

- **Money discipline (Decimal) is foundational.** Cannot defer — affects every downstream model.
- **numpy-financial wrapper is the math foundation.** All calc layers depend on it.
- **Rules predicates are independent per citation.** Can be added incrementally as needed.
- **Skill frontend depends on all scripts existing.** Build calc layer first, then orchestration, then skill.

## MVP Definition

### Launch With (v1)

User selected "all" scope — every Active requirement is v1. Per dependency graph, build order:

- [x] Loan/Schedule/Payment Pydantic models
- [x] Decimal money discipline + test fixtures
- [x] Amortization schedule (fixed-rate, biweekly, extra payments)
- [x] DTI / LTV / PITI / front-end-back-end ratios
- [x] Rules predicates (Fannie eligibility, FHA MIP, VA funding fee, USDA, Reg Z, IRS Pub 936)
- [x] Reference data YAML files (FHFA limits, FHA limits, MIP rates, VA fees, IRS caps)
- [x] ARM 5/1/7/1/10/1 with caps/floor/margin/reset logic
- [x] Refinance NPV / breakeven / cash-out
- [x] Points breakeven
- [x] Stress test sweeps (rate shock, income shock, ARM reset)
- [x] Estimated APR (Reg Z Appendix J Newton-Raphson, validated vs FFIEC)
- [x] DuckDB persistence with lockfile
- [x] Claude skill at `.claude/skills/mortgage-ops/`
- [x] Three subagents for context isolation
- [x] FRED MCP integration
- [x] Household joint-applicant model
- [x] Eval harness (skill-creator pattern)

### Add After Validation (v1.x)

- [ ] Annual regulatory data refresh script (Playwright + FHFA/HUD/IRS pages) — manual refresh sufficient initially
- [ ] Confer Solutions MCP for LE/CD parsing — only if user gets LE/CD PDFs and tires of manual entry
- [ ] Zillow MCP for property valuation — only if user wants Zestimate context
- [ ] Multi-property portfolio modeling — single primary residence first
- [ ] Tax basis tracking (cost basis, depreciation for rentals) — out of scope for v1

### Future Consideration (v2+)

- [ ] Web UI (matplotlib dashboards or static HTML) — markdown reports first
- [ ] Multi-user household sync — single-user assumption fine
- [ ] Prepayment penalty modeling (declining %, yield-maintenance) — uncommon in residential
- [ ] Real-time rate alerts — FRED weekly cadence sufficient

## Feature Prioritization Matrix

User selected ALL features for v1. Prioritization here informs phase ordering, not inclusion.

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Pydantic models + Decimal discipline | HIGH (foundation) | LOW | P1 |
| Amortization (fixed) | HIGH | LOW | P1 |
| Affordability ratios + rules predicates | HIGH | MEDIUM | P1 |
| Reference data YAML (regulatory) | HIGH | LOW | P1 |
| Refinance NPV / breakeven | HIGH | MEDIUM | P1 |
| Stress tests | HIGH | MEDIUM | P1 |
| ARM modeling | MEDIUM (we don't have an ARM today) | HIGH | P2 (but in v1) |
| Estimated APR (Reg Z) | MEDIUM (sanity-check tool) | HIGH | P2 (but in v1) |
| DuckDB persistence | MEDIUM | LOW | P1 |
| Skill frontend + modes | HIGH (UX) | MEDIUM | P1 |
| Subagents | MEDIUM | LOW | P2 |
| FRED MCP integration | MEDIUM | LOW | P2 |
| Eval harness | LOW (initially) | LOW | P3 |

## Competitor Feature Analysis

| Feature | Bankrate / NerdWallet | Maybe Finance (OSS) | Our Approach |
|---------|----------------------|---------------------|--------------|
| Amortization | Yes (web form) | Yes (Ruby/Rails) | Python + Decimal + JSON in/out |
| Refi NPV | Approximate / breakeven only | No | True NPV via pyxirr |
| Affordability | Yes | No | Rules predicates per loan type with citations |
| Stress test | No | No | Yes (parameter sweeps via subagent) |
| ARM modeling | Surface-level | No | Full caps/floor/margin/reset |
| APR | Vendor's APR (no methodology shown) | No | Estimated APR with Reg Z Appendix J methodology |
| Open source | No | Yes (AGPL) | Yes (MIT or similar) |
| LLM frontend | No | No | Yes (Claude skill) |
| Live rate context | Static rate widgets | No | FRED MCP |

## Sources

- https://github.com/maybe-finance/maybe — OSS personal finance reference
- https://github.com/firefly-iii/firefly-iii — OSS personal finance reference
- https://www.consumerfinance.gov/owning-a-home/ — CFPB consumer toolkit (decommissioned API; static guidance)
- Career-ops repo: `/Users/cujo253/Documents/career-ops/modes/_shared.md` — modes architecture
- Card-ops repo: `/Users/cujo253/Documents/card-ops/lib/rewards.py` — leak-detection pattern (analog: refinance-leak)
- https://github.com/anthropics/skills/tree/main/skills/pdf — progressive disclosure, scripts/, references/

---
*Feature research for: personal mortgage analysis tool*
*Researched: 2026-04-26*
