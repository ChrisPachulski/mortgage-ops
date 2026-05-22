# Mortgage-Ops Literature Acquisition Goal Command

> Reusable operating plan to acquire the literature that optimizes mortgage-ops
> calc accuracy, regulatory rigor, skill design, and decision narration.
> Written 2026-05-15. Re-invokable quarterly (regulatory) / monthly (market).

---

## THE GOAL

**Build a Zotero-hosted literature corpus that makes every mortgage-ops calculation defensible, every recommendation grounded, and every skill iteration informed by the latest practice — with foundational rigor as the floor.**

Bias: **2-3× weight on 2024-2026 sources** (current regulatory state, latest agent-design practice, current rate / macro / climate environment), but the foundational canon (Fabozzi mortgage-backed securities, Campbell-Cocco optimal mortgage choice, Agarwal-Driscoll-Laibson refinance heuristics, Reg Z text) is non-negotiable bedrock.

---

## THE SEVEN PILLARS (each = one Zotero sub-collection)

| # | Pillar | Zotero collection key | Recency weight | Why it matters to mortgage-ops |
|---|---|---|---|---|
| 1 | **Regulatory & Compliance** | `RRLPYLQT` | **Heavy recency (1-3 yr)** | CFPB ATR/QM, Fannie LLPA grid, Reg Z APR — change yearly; stale citations = wrong predicates |
| 2 | **Calc Methods & Models** | `96M9RQKD` | Mixed (50/50) | Amortization, APR, prepay, NPV — math is stable but applied refinements move |
| 3 | **Market & Macro** | `MIB3KGJA` | **Heavy recency (monthly-quarterly)** | Rate trajectory, price indices, regional dynamics — actionable only when current |
| 4 | **AI Agent Design** | `AFI8WHDD` | **Very heavy recency (3-12 mo)** | Claude best practices, skill patterns, eval methods — field moves fast |
| 5 | **Foundational Texts** | `7L4FRRDX` | One-time canonical | Bedrock that doesn't go stale (Fabozzi, Reg Z text, GSE histories) |
| 6 | **Climate & Insurance Risk** | `F2M6UUWS` | **Heavy recency (1-3 yr)** | Insurance crisis literature is post-2022 phenomenon; WA wildfire/flood data evolving |
| 7 | **Personal Purchase Notes** | `8W4ZGH49` | N/A | Pachulski-specific: WA market reports, school districts, neighborhood comps |

Top-level Mortgage collection key: `RK6GZFDS`

---

## SOURCE PRIORITIES (where to look, in order)

### Tier 1 — Authoritative & free (always check first)

**Regulatory:**
- consumerfinance.gov (CFPB) → ATR/QM, Reg Z amendments, mortgage rule pages
- fhfa.gov → Fannie/Freddie LLPA grids, conforming limits
- hud.gov → FHA Mortgagee Letters, MIP factors
- benefits.va.gov → VA funding fee, residual income tables
- 12 CFR text via Cornell Law (law.cornell.edu/cfr/text/12)

**Macro & Market:**
- fred.stlouisfed.org → MORTGAGE30US, MORTGAGE15US, MORTGAGE5US (already integrated)
- freddiemac.com/pmms → Primary Mortgage Market Survey
- fanniemae.com/research → economic & strategic research
- urban.org/housing-finance-policy-center → monthly mortgage chartbook (gold)
- jchs.harvard.edu → annual State of the Nation's Housing
- nahb.org/news-and-economics → builder market data

**Research papers (free / preprint):**
- nber.org/papers → working papers, housing finance section
- ssrn.com → preprints (most academic mortgage papers land here)
- arxiv.org → econ.GN, q-fin, cs.LG (for AI-applied finance)
- federalreserve.gov/econres → FEDS papers
- newyorkfed.org/research → consumer credit panel work

**AI Agent Design:**
- anthropic.com/engineering → blog, prompt engineering guides
- anthropic.com/news → Claude releases
- arxiv.org cs.CL / cs.AI for agent / tool-use papers
- github.com/anthropics/anthropic-cookbook → patterns

### Tier 2 — Worth checking (free, less authoritative)

- mortgagenewsdaily.com → daily rate journalism (useful for trend, not citations)
- hsh.com → rate history
- nar.realtor/research-and-statistics → NAR market data (real estate-broker flavored)
- redfin.com/news/data-center → market data with methodology
- zillow.com/research → tax estimates, ZHVI methodology
- aei.org/housing → Housing Center reports (right-leaning lens)
- brookings.edu/topic/housing → policy work
- bis.org → Bank for International Settlements (occasional mortgage research)

### Tier 3 — Paywalled, fetch abstracts only

- Journal of Finance, Review of Financial Studies, Journal of Urban Economics
- Real Estate Economics, Journal of Housing Economics
- Strategy: pull abstract via SSRN/arxiv preprint search; cite the published version

---

## PRIORITY QUERIES (initial seeding, run on first invocation)

Run these searches across the source tiers above. Quote each search exactly when invoking.

### Pillar 1 — Regulatory (target ~15-20 items)
- "CFPB ATR-QM 2024" OR "CFPB ATR-QM 2025" OR "CFPB ATR-QM 2026"
- "Fannie Mae LLPA matrix" 2024 OR 2025 OR 2026
- "Freddie Mac credit fee structure" 2024+
- "FHA UFMIP" current schedule
- "VA funding fee" current
- "Reg Z APR calculation" updates
- "HMDA reporting threshold" 2024+
- "qualified mortgage" rule amendments
- "FHFA conforming loan limit" 2025 2026
- Washington state mortgage broker disclosure requirements
- King County WA property tax 2026

### Pillar 2 — Calc Methods (target ~12-15 items)
- "mortgage prepayment model" 2022+
- "mortgage NPV refinance decision" recent
- "Newton-Raphson APR Regulation Z"
- "biweekly mortgage payment math"
- "ARM cap structure modeling"
- "FHA UFMIP financing convention"
- "mortgage amortization spreadsheet conventions"
- Foundational: Fabozzi "Handbook of Mortgage-Backed Securities" (citation only — book is paid)

### Pillar 3 — Market & Macro (target ~15-20 items, refresh quarterly)
- Urban Institute Housing Finance Chartbook (latest monthly)
- Freddie Mac PMMS commentary (latest weekly)
- Harvard JCHS State of the Nation's Housing 2025 or 2026
- "mortgage rate forecast 2026"
- "housing affordability index 2026"
- "Case-Shiller home price index" methodology
- "Seattle metro housing market" 2026
- "King County WA real estate market" 2026
- FOMC dot plot effect on mortgage rates 2026

### Pillar 4 — AI Agent Design (target ~15-20 items, refresh quarterly)
- "Anthropic Claude skill" patterns 2025 2026
- "LLM tool use" 2025 2026
- "agent evaluation" 2025 2026
- "prompt caching" Anthropic
- "constitutional AI" 2025 update
- "Claude Code" engineering patterns
- "RAG citation grounding" 2025
- "LLM numeric reasoning" recent (relevant: mortgage-ops never lets LLM do math)
- "deterministic LLM hybrid systems" 2025

### Pillar 5 — Foundational (target ~10-12 canonical items, one-time)
- Fabozzi, Bhattacharya, Fabozzi — "Mortgage-Backed Securities" handbook
- Campbell & Cocco (2003) "Household Risk Management and Optimal Mortgage Choice" QJE
- Agarwal, Driscoll, Laibson (2013) "Optimal Mortgage Refinancing: A Closed-Form Solution"
- Hubbard & Mayer (2008) work on mortgage credit cycles
- Mian & Sufi "House of Debt"
- Reg Z text (12 CFR §1026) — direct ingestion of relevant sections
- HMDA Filing Instructions Guide (FIG) current year
- Selling Guide (Fannie) & Single-Family Seller/Servicer Guide (Freddie)

### Pillar 6 — Climate & Insurance Risk (target ~10-12 items, refresh annually)
- "California insurance crisis" 2022-2026
- "Florida home insurance" 2022-2026
- "wildfire risk pricing" mortgage
- "FEMA flood map" updates
- "First Street Foundation" climate risk methodology
- Washington wildfire risk Cascadia foothills
- King County WA flood zones methodology
- "climate-adjusted mortgage default" 2024+

### Pillar 7 — Personal Purchase Notes (target as-needed, ongoing)
- WA buyer closing cost breakdown (current)
- King/Pierce/Snohomish school district rankings (current)
- Specific listing analyses (when active)
- Lender quote comparisons (when active)
- Inspection report findings (when active)

---

## TAGGING SCHEME

Apply ALL applicable tags per item ingested. Tags drive cross-pillar discovery.

**Vintage tags (mandatory):**
- `vintage:2026` / `vintage:2025` / `vintage:2024` / `vintage:foundational`

**Domain tags:**
- `regulatory` / `calc-methods` / `market-macro` / `agent-design` / `climate-risk` / `personal-purchase`

**Specificity tags:**
- `conventional` / `fha` / `va` / `usda` / `jumbo` / `arm` / `fixed`
- `dti` / `ltv` / `apr` / `pmi` / `mip` / `cltv` / `prepayment`
- `cfpb` / `fhfa` / `hud` / `va-loans` / `gse`

**Geography tags (if applicable):**
- `wa` / `king-county` / `seattle-metro` / `national`

**Authority tags:**
- `primary-source` (rule text, agency publication)
- `peer-reviewed`
- `working-paper`
- `industry-report`
- `journalism`

---

## REFRESH CADENCE

| Pillar | Refresh | Trigger |
|---|---|---|
| Regulatory & Compliance | **Quarterly** | New LLPA matrix release, ATR/QM amendment, conforming limit update |
| Calc Methods & Models | Annually | New foundational paper of note |
| Market & Macro | **Monthly** | New Urban Institute chartbook, fresh PMMS commentary, new market quarter |
| AI Agent Design | **Quarterly** | Claude model release, new Anthropic engineering post |
| Foundational Texts | Once + curation | Add only when canonical-status emerges |
| Climate & Insurance Risk | Annually | After insurance-cycle quarters, after fire seasons |
| Personal Purchase Notes | Continuous | Per active listing / lender / inspection |

---

## INVOCATION PATTERN

To run this command (from any future Claude session):

```
/mortgage-ops … or just paste this filename and say "run the literature goal"
```

Steps the runner should take:
1. Read `.planning/MORTGAGE-OPS-LITERATURE-GOAL.md` (this file).
2. Identify which pillar(s) to refresh per the cadence table above.
3. Run priority queries via WebSearch + WebFetch against Tier 1 → Tier 2 sources.
4. For each item found: capture title, authors, year, URL, abstract, primary source.
5. Apply tagging scheme.
6. Ingest into the matching Zotero sub-collection via `cli-anything-zotero` (use `import` command group; check `--help` first).
7. Update this doc's "Last refresh" entries below at the bottom.
8. Report deltas to user: N new items in [pillars], any rule/regulation that changed since last refresh.

---

## INGESTION COMMAND REFERENCE

```bash
# Activate the CLI venv
source /Users/cujo253/.claude/plugins/marketplaces/cli-anything/zotero/agent-harness/.venv/bin/activate

# View Mortgage collection tree
cli-anything-zotero collection tree

# Sub-collection keys (cache here for fast lookup):
# RK6GZFDS = Mortgage (parent)
# RRLPYLQT = Regulatory and Compliance
# 96M9RQKD = Calc Methods and Models
# MIB3KGJA = Market and Macro
# AFI8WHDD = AI Agent Design
# 7L4FRRDX = Foundational Texts
# F2M6UUWS = Climate and Insurance Risk
# 8W4ZGH49 = Personal Purchase Notes

# Ingest pattern: use the import command group (see --help)
cli-anything-zotero import --help
```

---

## LAST REFRESH LOG

| Date | Pillars refreshed | Items added | Notes |
|---|---|---|---|
| 2026-05-15 | (structure-only) | 0 | Goal command created; sub-collections built; no items seeded yet |
| 2026-05-15 | **All 7 pillars seeded** | **93** | Initial corpus build — 86 items across P1-P6, plus 7 seed items in P7 Personal Purchase (WA REET, WA buyer closing costs, King Co school district locator, WA Form 17 seller disclosure RCW 64.06, WA septic + shared well authorities, NWMLS portal). Total library 216 → 309 items. CITATION-COVERAGE.md generated mapping every `lib/rules/*.py` predicate + `lib/*.py` module to its supporting Zotero entries. Coverage gaps flagged: 12 USC §4901 (HPA), 7 CFR Part 3555 (USDA), IRS Pub 936, USDA Income Limits — to fill in next Regulatory refresh. |
| 2026-05-16 | **Coverage gap fills** | **5** | Closed all 4 gaps flagged in CITATION-COVERAGE.md: 12 USC Ch. 49 / §4902 (HPA, backing conventional_pmi.py), 7 CFR Part 3555 (USDA SFHGLP, backing usda.py), IRS Pub 936 (tax deduction, backing irs_pub936.py), USDA Income Limits lookup tool (backing usda.py income tier). All in RRLPYLQT, tagged `coverage-gap-fill`. Library 520 → 525. Audit also identified 5 weak-provenance items (tenaco.com × 2, financialservicesperspectives.com, seattleagentmagazine.com × 2) — documented in `.planning/ZOTERO-CLEANUP-TODO.md` for manual GUI cleanup (content correct, source mirror suboptimal). |
| 2026-05-16 | **Exponential expansion — 6 of 7 housing pillars** | **211** | 8 parallel research agents ran focused 2021-2026 sweeps. Per-agent results: P1 Regulatory +24 CFPB items (ATR/QM amendments, Section 1071, RESPA Sec 8, redlining enforcement Fairway/Townstone/Trident, AVM rule, Reg X 2024 NPRM, LIBOR transition) + 24 GSE items (FHFA limit history, Fannie LLPA 2023 DTI rescission, FHA MIP/ADU MLs, VA Circular 26-23-06 + VASP, USDA SFH servicing rule, GSE CRT programs, FHFA climate advisory). P2 Calc Methods +31 prepay/refi items (Liebersohn-Rothstein NBER 32781, FEDS 2024-088, FHFA 24-03, Berger NBER 32447, Ringo inframarginal, racial refi gap Gerardi-Willen-Zhang JFE 2023, MBS yield-curve spreads, nonbank/shadow lending, HELOC substitution) + 21 ML/AI items (Fuster Predictably Unequal, Sirignano deep learning, NLP Doc-Q&A, fair lending Hurlin, LLM mortgage audit Bowen-Price-Stein-Yang, AVM accuracy, ZHVI, iBuyer pricing, geospatial flood-LLM, synthetic data). P3 Market & Macro +30 pandemic-era items (Mondragon-Wieland w30041, Ramani-Bloom donut effect, Glaeser-Gyourko w33694/w33876, Auckland upzoning, Minneapolis 2040, Mills-Molloy-Zarutskie SFR, GAO-24-106643, AEI Pinto-Gailes, Buchak-Matvos-Piskorski-Seru iBuyer, CBRE BTR, Gupta-Mittal office apocalypse, Sun Belt migration, Airbnb effects) + 24 affordability/default items (Philly Fed 23-02 forbearance, NY Fed SR 1035, FHFA WP 24-11, Urban Institute Perfect Storm/Affordable Abundance, JCHS State of Nation's Housing 2025, NAR first-time buyer 21% record low, NFHA equity 2025, Ganong-Noel QJE 2023 strategic default, CoreLogic Q4 2024 HER, ICE/Black Knight Mortgage Monitor) + 25 PNW/WA items (WA Commerce 5-yr plan, UW Runstad Q3 2024, PSRC RHNA, HB 1110 middle housing, MHA evaluation, King County 2025 housing needs, WSHFC Covenant Homeownership, condo SB 5258, NWMLS 2024/2025 annuals, HB 1217 rent stabilization, USGS Cascadia, BIAW). P6 Climate +32 items (Fed CSA pilot 2024, SR 23-9, CA FAIR Plan, NFIP H.R.5484, Risk Rating 2.0 GAO/EDF, wildfire default Biswas Phila Fed + Issler Berkeley, hurricane CRE Holtermans-Kahn-Kok, Keys-Mulder w32579, climate securitization Ouazad-Kahn, Gourevitch et al. Nature Climate Change, CBO 2024, Treasury FIO 2025, Fannie/Freddie Green MBS, SEC climate disclosure final rule, climate gentrification, WUI mapping methodology GeoHealth 2025). Total library 309 → 520 items (+68% growth). 6 of 7 mortgage sub-collections grew: Regulatory 16→64 (+48), Calc Methods 15→67 (+52), Market & Macro 15→94 (+79), Climate 11→43 (+32). |
|  |  |  |  |

---

## SUCCESS CRITERIA

- Every dollar figure the mortgage-ops engine emits is traceable to a Zotero-cited authority (Reg Z, Fannie LLPA, FHFA limit, Fed paper).
- Every recommendation Claude makes ("don't buy this house") can be defended with literature on optimal-mortgage-choice / refinance-NPV / household-risk-management.
- Every skill-design choice in `.claude/skills/mortgage-ops/` can be defended with recent Anthropic engineering guidance or published agent-design research.
- The corpus is **never more than 6 months stale** on regulatory / market pillars, **never more than 12 months stale** on AI agent design, and **always intact** on foundational.

---

*This goal command is the operating plan. Re-invoke quarterly minimum. Update the refresh log when items are added.*
