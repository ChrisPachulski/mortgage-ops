# Architecture Research

**Domain:** Personal-use mortgage analysis tool
**Researched:** 2026-04-26
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────┐
│                  USER (terminal / Claude Code)                 │
└───────────────────────────┬────────────────────────────────────┘
                            │ /mortgage-ops [mode] [args]
                            ▼
┌────────────────────────────────────────────────────────────────┐
│            .claude/skills/mortgage-ops/SKILL.md                │
│  Mode router: evaluate | compare | scenario | refinance |      │
│               affordability | stress | amortize                │
│  Loads modes/_shared.md + references/<topic>.md on demand      │
│  Inline `!` shell injection for live rate context              │
└────────┬─────────────────────────────┬─────────────────────────┘
         │                             │
         │ Bash → Python scripts       │ Subagent dispatch
         ▼                             ▼
┌─────────────────────────┐  ┌─────────────────────────────────┐
│  scripts/ (bundled)     │  │  .claude/agents/                │
│  amortize.py            │  │  amortization-agent.md (haiku)  │
│  apr_reg_z.py           │  │  refi-npv-agent.md (sonnet)     │
│  refi_npv.py            │  │  stress-test-agent.md (haiku)   │
│  affordability.py       │  └──────────────┬──────────────────┘
│  stress_test.py         │                 │
│  points_breakeven.py    │                 │
│  arm_simulate.py        │                 │
│  All: --help first;     │                 │
│       JSON in/out       │                 │
└────────────┬────────────┘                 │
             │                              │
             └──────────────┬───────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                       lib/ (Python engine)                     │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ models.py        │  │ amortize.py      │                    │
│  │ Loan/Schedule/   │  │ wraps numpy-     │                    │
│  │ Payment Pydantic │  │ financial        │                    │
│  └──────────────────┘  └──────────────────┘                    │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ apr.py (Newton)  │  │ refinance.py     │                    │
│  └──────────────────┘  └──────────────────┘                    │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ affordability.py │  │ stress.py        │                    │
│  └──────────────────┘  └──────────────────┘                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ rules/                                                   │  │
│  │   reg_z.py | fannie_eligibility.py | fha_mip.py |        │  │
│  │   va_funding_fee.py | usda.py | irs_pub936.py |          │  │
│  │   atr_qm.py                                              │  │
│  │   ONE PREDICATE PER CITATION                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────┬──────────────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                              │
│  ┌──────────────────────┐  ┌──────────────────────────────┐    │
│  │ data/                │  │ data/reference/ (YAML)       │    │
│  │  mortgage-ops.duckdb │  │  conforming-limits-2026.yml  │    │
│  │  (loans, scenarios,  │  │  fha-limits-2026.yml         │    │
│  │   reports tables)    │  │  fha-mip-rates.yml           │    │
│  │                      │  │  va-funding-fees.yml         │    │
│  │  known-loans.yml     │  │  va-residual-income.yml      │    │
│  │  (product catalog)   │  │  usda-income-limits.yml      │    │
│  │                      │  │  irs-pub936.yml              │    │
│  │  data/market/        │  │  All cite source URL +       │    │
│  │   pmms-history.parq  │  │  effective date              │    │
│  └──────────────────────┘  └──────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
              │
              ▼ (live rates only)
┌────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                       │
│  FRED MCP (stefanoamorelli/fred-mcp-server)                    │
│   → MORTGAGE30US, MORTGAGE15US (mirrors PMMS, free)            │
│  [Optional, deferred] confersolutions/mcp-mortgage-server      │
│  [Optional, deferred] sap156/zillow-mcp-server                 │
└────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| SKILL.md | Mode routing; load on-demand references; inject live rate context | Markdown with frontmatter + `!\`...\`` shell blocks |
| modes/*.md | Per-mode instructions for Claude (evaluate, compare, etc.) | Markdown |
| references/*.md | Domain knowledge loaded only when SKILL.md routes there | Markdown (progressive disclosure) |
| scripts/*.py | Black-box CLI helpers, JSON in/out | Python with argparse + Pydantic validation |
| Subagents | Context isolation for calc-heavy sweeps | Markdown with YAML frontmatter |
| lib/models.py | Pydantic Loan/Schedule/Payment with condecimal | Pydantic v2 |
| lib/amortize.py | Wraps numpy-financial, returns Schedule | Pure functions |
| lib/apr.py | Newton-Raphson Reg Z Appendix J | Pure functions |
| lib/refinance.py | Refi NPV, breakeven, cash-out modeling | Pure functions, optionally pyxirr |
| lib/affordability.py | DTI/LTV/PITI/PTI/front-end-back-end | Pure functions |
| lib/stress.py | Rate-shock, income-shock, ARM-reset sweeps | Pure functions returning param-grid results |
| lib/rules/ | One predicate per citation | One file per regulator citation |
| data/mortgage-ops.duckdb | Loans, scenarios, reports, payments | DuckDB single file |
| data/reference/*.yml | Regulatory data with source URL + effective date | YAML, refreshed manually |
| data/known-loans.yml | Product catalog (30yr fixed, 15yr fixed, ARM 5/1, FHA, VA, jumbo) | YAML |
| FRED MCP | Live MORTGAGE30US/MORTGAGE15US rate data | MCP server |

## Recommended Project Structure

```
mortgage-ops/
├── .claude/
│   ├── skills/mortgage-ops/
│   │   ├── SKILL.md                  # ≤500 lines, ≤5k tokens
│   │   ├── LICENSE.txt
│   │   ├── modes/
│   │   │   ├── _shared.md            # scoring + report structure
│   │   │   ├── _profile.md           # user-specific (gitignored)
│   │   │   ├── evaluate.md           # single loan
│   │   │   ├── compare.md            # rank N offers
│   │   │   ├── refinance.md          # is refi worth it
│   │   │   ├── affordability.md      # what can I qualify for
│   │   │   ├── stress.md             # parameter sweeps
│   │   │   ├── amortize.md           # full schedule + extra-payment
│   │   │   └── arm.md                # ARM-specific evaluation
│   │   ├── references/               # on-demand
│   │   │   ├── amortization-formulas.md
│   │   │   ├── apr-reg-z.md
│   │   │   ├── arm-mechanics.md
│   │   │   ├── refi-npv.md
│   │   │   ├── affordability-rules.md
│   │   │   ├── gse-limits.md
│   │   │   ├── mip-pmi.md
│   │   │   ├── tax-deductibility.md
│   │   │   └── spreadsheet-conventions.md  # lifted from xlsx skill
│   │   ├── scripts/                  # bundled black-box helpers
│   │   │   ├── amortize.py
│   │   │   ├── apr_reg_z.py
│   │   │   ├── refi_npv.py
│   │   │   ├── affordability.py
│   │   │   ├── stress_test.py
│   │   │   ├── arm_simulate.py
│   │   │   └── points_breakeven.py
│   │   ├── evals/                    # skill-creator pattern
│   │   │   ├── prompts/
│   │   │   ├── expected/
│   │   │   └── runner.py
│   │   └── assets/
│   └── agents/
│       ├── amortization-agent.md
│       ├── refi-npv-agent.md
│       └── stress-test-agent.md
├── lib/                              # importable, testable without Claude
│   ├── __init__.py
│   ├── models.py
│   ├── amortize.py
│   ├── apr.py
│   ├── refinance.py
│   ├── affordability.py
│   ├── stress.py
│   ├── arm.py
│   ├── points.py
│   └── rules/
│       ├── __init__.py
│       ├── reg_z.py
│       ├── fannie_eligibility.py
│       ├── freddie_eligibility.py
│       ├── fha_mip.py
│       ├── va_funding_fee.py
│       ├── usda.py
│       ├── irs_pub936.py
│       └── atr_qm.py
├── orchestration/                    # JS/Node, mirrors career-ops db-write.mjs
│   ├── db-write.mjs
│   ├── lockfile.mjs
│   ├── init-db.mjs
│   └── render-markdown.mjs
├── data/
│   ├── mortgage-ops.duckdb           # gitignored
│   ├── known-loans.yml               # committed (catalog, not user data)
│   ├── reference/                    # committed (regulatory data)
│   │   ├── conforming-limits-2026.yml
│   │   ├── fha-limits-2026.yml
│   │   ├── fha-mip-rates.yml
│   │   ├── va-funding-fees.yml
│   │   ├── va-residual-income.yml
│   │   ├── usda-income-limits.yml
│   │   └── irs-pub936.yml
│   └── market/
│       └── pmms-history.parquet      # gitignored, regenerated
├── config/
│   ├── household.example.yml
│   └── household.yml                 # gitignored
├── tests/
│   ├── fixtures/
│   │   ├── reg_z_appendix_j.json     # FFIEC capture
│   │   ├── cfpb_le_sample.json       # $162k @ 3.875% / 30yr
│   │   ├── wikipedia_worked.json     # $200k @ 6.5% / 30yr
│   │   └── freddie_sflld_sample/     # free quarter, no registration
│   ├── test_amortize.py
│   ├── test_apr.py
│   ├── test_refinance.py
│   ├── test_affordability.py
│   ├── test_arm.py
│   ├── test_stress.py
│   └── test_rules/
├── reports/                          # gitignored — generated reports
├── pyproject.toml                    # uv + ruff + mypy --strict
├── package.json                      # node side (skill orchestration)
├── .github/workflows/ci.yml          # pytest + mypy + ruff
├── .pre-commit-config.yaml
├── .gitignore                        # strict — household data never committed
├── .envrc                            # direnv venv activation
├── CLAUDE.md
├── DATA_CONTRACT.md                  # User/System/Data layer boundaries
└── README.md
```

### Structure Rationale

- **`.claude/skills/mortgage-ops/scripts/` (not project-root scripts/)**: Anthropic's pdf/xlsx/webapp-testing convention; makes the skill portable on its own. Career-ops/card-ops both miss this.
- **`lib/` is the calc engine, importable without Claude**: Tests run on lib alone — LLM frontend is a separate concern.
- **`lib/rules/` is one file per citation**: HMDA Platform pattern — annual refresh of one rule doesn't risk others.
- **`data/reference/` separate from `data/`**: Regulatory data is committed (auditable refresh history); user data and computed artifacts gitignored.
- **`orchestration/` (Node) mirrors career-ops `scripts/`**: db-write.mjs + lockfile.mjs — DuckDB concurrency pattern.
- **`config/household.yml` not committed**: User layer per career-ops Data Contract; example committed.
- **Subagents in `.claude/agents/` (project-local)**: Context isolation; only spawned for calc-heavy sweeps.

## Architectural Patterns

### Pattern 1: Claude/Python Calc Split

**What:** Claude (in skill modes) extracts loan features from natural language → JSON → Python script computes deterministically → JSON → Claude narrates results.
**When to use:** Every calc operation. The LLM never owns numbers it didn't get from a script.
**Trade-offs:** Pro: Reproducible math, testable without LLM, no hallucinated numbers. Con: One extra hop (negligible).

**Example:**
```python
# scripts/amortize.py
import json, sys, argparse
from decimal import Decimal
from pydantic import BaseModel
from lib.amortize import build_schedule

class AmortInput(BaseModel):
    principal: Decimal
    annual_rate: Decimal
    term_months: int
    extra_principal: Decimal = Decimal("0")

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="path to JSON input")
    args = p.parse_args()
    data = AmortInput.model_validate_json(open(args.input).read())
    schedule = build_schedule(data)
    print(schedule.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
```

### Pattern 2: One Predicate Per Citation (HMDA Platform)

**What:** Each regulatory rule is one named function tied to a specific citation in a docstring.
**When to use:** All `lib/rules/*.py` files.
**Trade-offs:** Pro: Annual regulatory refresh is auditable; tests are 1:1 with citations. Con: More files than a "big-rules-engine" approach.

**Example:**
```python
# lib/rules/reg_z.py
def qm_general_price_test(apr: Decimal, apor: Decimal, loan_amount: Decimal) -> bool:
    """12 CFR §1026.43(e)(2)(vi) — General QM price-based threshold (Mar 2021 final rule).

    Returns True if APR-APOR spread is within the QM threshold for the loan amount tier.
    Replaces the eliminated 43% DTI cap (formerly §1026.43(e)(2)(vi)).
    """
    threshold = _qm_apor_threshold(loan_amount)  # tier lookup
    return (apr - apor) <= threshold
```

### Pattern 3: Reference Data as Cited YAML

**What:** Every regulatory parameter (loan limits, MIP rates, funding fees) lives in a YAML file with `source:` URL and `effective:` date.
**When to use:** All `data/reference/*.yml` files.
**Trade-offs:** Pro: Annual refresh is a YAML edit, not a code change; auditable. Con: Code reads YAML at import time (negligible).

**Example:**
```yaml
# data/reference/conforming-limits-2026.yml
source: "https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026"
effective: 2026-01-01
limits:
  baseline_1_unit: 832750
  ceiling_1_unit: 1249125
  baseline_2_unit: 1066250
  baseline_3_unit: 1289100
```

### Pattern 4: DuckDB + Lockfile (career-ops)

**What:** Single-file ACID database, single-writer; all writes wrapped in `withLock()` with stale-recovery at 60s.
**When to use:** All persistent writes (loans, scenarios, reports tables).
**Trade-offs:** Pro: No transaction-isolation complexity; simple recovery. Con: Single-machine only (fine for personal use).

### Pattern 5: Progressive Disclosure (Anthropic skill convention)

**What:** SKILL.md is a quick-start; per-topic `references/*.md` files load only when the skill routes to them.
**When to use:** All multi-topic skills.
**Trade-offs:** Pro: Token-efficient (idle cost ~100 tokens per skill); reference content effectively unbounded. Con: Discipline required to keep SKILL.md tight.

### Pattern 6: Subagent Context Isolation

**What:** Calc-heavy sweeps (50+ ARM scenarios) run in a forked subagent context; main conversation only sees the final summary.
**When to use:** Any operation that produces > 2k tokens of intermediate output.
**Trade-offs:** Pro: Main conversation stays clean. Con: Subagents have their own model + cost.

## Data Flow

### Single-loan evaluation flow

```
User: "Evaluate this loan: $400k 30yr fixed at 6.5%"
  ↓
SKILL.md → modes/evaluate.md (Claude reads instructions)
  ↓
Claude extracts → JSON: {principal: "400000", rate: "0.065", term: 360}
  ↓
Bash: scripts/amortize.py --input /tmp/loan.json
  ↓
lib/amortize.py → Pydantic Schedule → JSON
  ↓
Bash: scripts/affordability.py --input /tmp/affordability.json
  ↓
lib/affordability.py + lib/rules/* → JSON eligibility
  ↓
Claude composes report.md → reports/{###}-{slug}-{date}.md
  ↓
Node orchestration/db-write.mjs --insert-report → DuckDB
```

### Stress-sweep flow (subagent)

```
User: "What if rates jump 200bps?"
  ↓
SKILL.md → modes/stress.md
  ↓
Spawn stress-test-agent (subagent, isolated context)
  ↓ subagent
  Subagent runs scripts/stress_test.py --rates 0.06,0.065,0.07,0.075,0.08
  ↓ subagent
  Returns summary table to main conversation
  ↓
Claude narrates result in main conversation
```

### Live rate context injection

```
SKILL.md (loaded)
  ↓ inline `!\`fred-cli get MORTGAGE30US --latest\``
  ↓
FRED MCP returns current weekly rate
  ↓
Rate is in Claude's context for the rest of the session
```

## Scaling Considerations

This is a personal-use tool. Scaling is not a concern.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (single household) | Current design |
| 2-5 households (family/friends) | Each clones the repo separately; no sync |
| > 5 households | Out of scope — this is not a SaaS |

Performance concerns:
- 360-row amortization: instantaneous
- 50-scenario stress sweep: < 1s with numpy-financial vectorization
- Newton-Raphson APR: converges in 5-10 iterations, < 100ms
- DuckDB on a few thousand scenario rows: instantaneous

## Anti-Patterns

### Anti-Pattern 1: Math in the LLM context

**What people do:** Have Claude compute amortization inline ("Let me calculate that for you...").
**Why it's wrong:** LLMs hallucinate on multi-step arithmetic; numbers drift; not reproducible.
**Do this instead:** Always shell out to `scripts/amortize.py`. Quote from Anthropic best practices: *"Give Claude a way to verify its work."*

### Anti-Pattern 2: Float for money

**What people do:** `monthly_payment = principal * rate / (1 - (1+rate)**-n)` with floats.
**Why it's wrong:** `0.1 + 0.2 ≠ 0.3` in float; rounding compounds over 360 periods; cents drift.
**Do this instead:** `Decimal` constructed from strings; quantize end-of-period; ROUND_HALF_UP.

### Anti-Pattern 3: Scripts at project root (career-ops/card-ops style)

**What people do:** Put `analyze-patterns.mjs` at the project root, outside `.claude/skills/`.
**Why it's wrong:** Skill is no longer portable; can't share the skill standalone; no clean separation of skill assets vs project orchestration.
**Do this instead:** Bundled scripts inside `.claude/skills/mortgage-ops/scripts/`. Project-wide orchestration (cross-skill) at `orchestration/` if needed.

### Anti-Pattern 4: Big-rules-engine

**What people do:** One `lib/qualification.py` with a 500-line function evaluating all rules.
**Why it's wrong:** Annual regulatory refresh is risky (one citation change → re-test all rules); audit trail is unclear.
**Do this instead:** One file per regulator citation. Predicate function. Docstring with citation. 1:1 test mapping.

### Anti-Pattern 5: Auto-scraping rate data

**What people do:** Cron job hits Bankrate / MND every morning.
**Why it's wrong:** TOS violation; brittle (HTML changes); unnecessary (FRED is official + free + weekly).
**Do this instead:** FRED MCP for `MORTGAGE30US` weekly. Manual annual refresh of regulatory YAML.

### Anti-Pattern 6: Auto-updating user files

**What people do:** Skill updates `config/household.yml` automatically when user changes income.
**Why it's wrong:** Loses user customizations; breaks Data Contract trust.
**Do this instead:** User layer (household.yml, profile.yml) is read-only from system code. System updates can never write to it. Career-ops DATA_CONTRACT.md pattern.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| FRED MCP (`stefanoamorelli/fred-mcp-server`) | MCP server — Claude calls tool with series ID | Free, no API key needed for FRED public series; returns latest observation or range |
| FFIEC APR Tool | None (manual capture-as-fixture) | Closed source; capture outputs once, pin as test fixtures |
| Freddie Mac SFLLD | Manual download (free sample, no registration) | One-time setup; sample quarter is enough for sanity checks |
| FHFA / HUD / IRS data | Manual annual refresh | YAML edit + commit with source URL |
| Confer Solutions MCP | Optional, deferred | Only if LE/CD parsing becomes painful |
| Zillow MCP (`sap156/`) | Optional, deferred | Only if user wants Zestimate context |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| SKILL.md ↔ scripts/*.py | Bash + JSON files (`/tmp/`) | JSON in/out at script boundary; Pydantic validates on read |
| Scripts ↔ lib/ | Direct Python import | Scripts are thin CLI wrappers; lib is the engine |
| lib/ ↔ data/ | Read-only YAML import; DuckDB read-write via duckdb-async | Lockfile wraps writes |
| lib/rules/ ↔ data/reference/ | YAML import at predicate-call time | Cached after first read |
| Skill ↔ subagents | Task() spawn with `agent: stress-test-agent` | Subagent has its own context window; returns summary |

## Sources

- Career-ops repo deep-dive (prior agent, 2026-04-26)
- Card-ops repo deep-dive (prior agent, 2026-04-26)
- Python finance library survey (prior agent, 2026-04-26)
- Claude/MCP ecosystem survey (prior agent, 2026-04-26)
- OSS mortgage projects + regulatory sources (prior agent, 2026-04-26)
- https://github.com/anthropics/skills — pdf, xlsx, webapp-testing, skill-creator patterns
- https://code.claude.com/docs/en/sub-agents — subagent frontmatter, isolation
- https://github.com/cfpb/hmda-platform — predicate-per-citation pattern (Scala)
- https://github.com/stefanoamorelli/fred-mcp-server — FRED MCP

---
*Architecture research for: personal mortgage analysis tool*
*Researched: 2026-04-26*
