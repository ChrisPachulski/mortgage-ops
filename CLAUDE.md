<!-- GSD:project-start source:PROJECT.md -->
## Project

**mortgage-ops** — Personal-use mortgage analysis tool for the Pachulski household. Sibling to `career-ops` and `card-ops`. Combines a deterministic Python calculation engine (amortization, ARM modeling, refi NPV, affordability, stress tests, points breakeven, estimated APR) with a Claude-skill frontend that routes natural-language requests to the right calc and produces human-readable reports.

**Core Value:** Math correctness first. Every dollar figure that exits this system must be traceable to a tested, deterministic Python function. The LLM frontend is a router and narrator — it never owns numbers.

See `.planning/PROJECT.md` for full context, requirements, and key decisions.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

**Python calc engine (3.12+):**
- `numpy-financial` — Wraps Excel-style PMT/IPMT/PPMT/NPV/IRR. **Wrap, do not reimplement.** Beware bugs #130 (pmt fv-sign) and #131 (irr arch-dependent).
- `pydantic` ≥2.6 — Loan/Schedule/Payment models with `condecimal(max_digits=14, decimal_places=2)`.
- `python-dateutil` — `relativedelta` for monthly payment scheduling.
- `pandas` — Schedule output, statistical sanity checks against Freddie SFLLD samples.
- `pyxirr` — Rust+PyO3 XIRR/XNPV for batch refi-NPV scenarios.
- `duckdb` — Single-file ACID persistence (loans, scenarios, reports tables).
- `pytest`, `mypy --strict`, `ruff`, `uv` — Dev tooling.

**Node skill orchestration:**
- `duckdb-async`, `js-yaml` — Mirror `career-ops/scripts/db-write.mjs` and `lockfile.mjs` patterns.

**External integrations:**
- FRED MCP (`stefanoamorelli/fred-mcp-server`) — Live `MORTGAGE30US`/`MORTGAGE15US` rate data (mirrors PMMS).

**What NOT to use:**
- `mortgage` PyPI / `mortgage` (jbmohler) / `amortization` PyPI — abandoned, float-based, or no license.
- QuantLib, FinancePy, rateslib, absbox — wrong scope or licensing.
- Float for money — use `Decimal` constructed from strings, quantize with `ROUND_HALF_UP`.

See `.planning/research/STACK.md` for full verdict matrix.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

**Money discipline (non-negotiable):**
- `Decimal` for all dollar amounts and rates. Construct from strings: `Decimal("0.065")` not `Decimal(0.065)`.
- `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` end-of-period only.
- Never mix `float` and `Decimal` in the same expression.
- Pydantic v2 `condecimal` at all script boundaries.

**Calc engine separation:**
- Every dollar figure is computed by Python in `lib/`. Claude never owns numbers.
- SKILL.md routes to `scripts/*.py` for math; scripts return JSON; Claude narrates.
- Bundled scripts: run `--help` first; do not read source unless customization needed (Anthropic webapp-testing doctrine).

**Rules-as-predicates (HMDA Platform pattern):**
- One file per regulatory citation in `lib/rules/`.
- Docstring includes citation (12 CFR §X.Y, HUD ML Z, etc.).
- 1:1 test-to-citation mapping.

**Reference data discipline:**
- All regulatory parameters in `data/reference/*.yml` with `source:` URL and `effective:` date.
- Annual refresh = YAML edit + commit, never code change.
- Startup-time staleness check warns when `effective:` is > 12 months old.

**Skill portability (lifted from anthropics/skills):**
- `scripts/`, `references/`, `assets/`, `LICENSE.txt` all INSIDE `.claude/skills/mortgage-ops/`.
- SKILL.md ≤ 500 lines, ≤ 5k tokens. Load-bearing routing in first 200 lines.
- `references/*.md` loaded on demand only (progressive disclosure).

**Data Contract (career-ops pattern):**
- **User Layer** (READ-ONLY from system code): `config/household.yml`, `config/profile.yml`, `modes/_profile.md`. Never auto-updated. Always gitignored.
- **System Layer**: `lib/`, `scripts/`, `modes/`, `references/`, `orchestration/`. Auto-updatable.
- **Data Layer**: `data/mortgage-ops.duckdb`, `data/market/*.parquet`, `reports/`. Generated; gitignored.
- **Reference Layer**: `data/reference/*.yml`, `data/known-loans.yml`. Committed; manually refreshed.

**Testing:**
- Hand-calculated golden-value fixtures with citation comments (card-ops pattern).
- Exact Decimal equality, never `assertAlmostEqual` for money.
- Pinned oracles: Wikipedia $200k @ 6.5%/30yr → $1,264.14; CFPB LE $162k @ 3.875%/30yr → $761.78; computed $400k @ 6.5%/30yr → $2,528.27; computed $200k @ 7%/15yr → $1,797.66.

**Commits:** No Co-Authored-By or AI attribution (per global rule).

See `.planning/research/PITFALLS.md` for "looks done but isn't" checklist and recovery strategies.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

**Three-layer architecture:**

1. **Claude skill** at `.claude/skills/mortgage-ops/` — routes natural-language requests to bundled `scripts/`. Modes: `evaluate`, `compare`, `refinance`, `affordability`, `stress`, `amortize`, `arm`. Three subagents (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) provide context isolation for calc-heavy operations.

2. **Python lib** at `lib/` — `models.py` (Pydantic), `amortize.py` (numpy-financial wrapper), `apr.py` (Newton-Raphson Reg Z), `refinance.py`, `affordability.py`, `stress.py`, `arm.py`, `points.py`, `rules/*.py` (one predicate per citation).

3. **Data layer** at `data/` — `mortgage-ops.duckdb` (loans/scenarios/reports), `known-loans.yml` (catalog), `reference/*.yml` (regulatory data with source URL + effective date).

**Orchestration** at `orchestration/` (Node) — `db-write.mjs` + `lockfile.mjs` mirroring career-ops pattern. All DuckDB writes wrapped in `withLock()`.

See `.planning/research/ARCHITECTURE.md` for ASCII diagram, project structure, data flows, and integration points.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found yet. Will populate as Phase 10 (Claude Skill Frontend) implements `.claude/skills/mortgage-ops/SKILL.md`.
<!-- GSD:skills-end -->

<!-- GSD:subagents-start source:agents/ -->
## Project Subagents

Three context-isolated Claude Code subagents under `.claude/agents/`:

- **`amortization-agent`** (Haiku) — single-loan amortization schedules. Returns markdown
  table or CSV path. Closes REQUIREMENTS SUBA-01.
- **`refi-npv-agent`** (Sonnet) — ranks 2-5 competing refi offers by NPV (borrower
  perspective). Returns ranked markdown table. Closes SUBA-02.
- **`stress-test-agent`** (Haiku) — parameter-grid stress sweeps with >5 scenarios.
  Returns ≤1,000-token summary. Closes SUBA-03.

Browser-friendly per-agent summaries: `.claude/agents/README.md` (NOT loaded into agent
context — for human repo-browsers).

Routing-decision detail (when each agent fires, budget rationale, live-transcript capture
recipe): `.claude/skills/mortgage-ops/references/subagent-routing.md` (loaded on-demand by
Phase 10 progressive disclosure).

See `.planning/phases/11-subagents/` for source plans (Plans 11-00..11-06).
<!-- GSD:subagents-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work
- `/gsd-discuss-phase N` to gather context before planning a phase
- `/gsd-plan-phase N` to plan a phase's work
- `/gsd-progress` to see project status and routing

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.

**This project is configured with:**
- Granularity: fine (12 phases)
- Execution: sequential within phases
- Mode: yolo (auto-approve gates)
- Workflow agents: research + plan-check + verifier all enabled
- Models: quality profile (opus for research/roadmap)
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` — do not edit manually.
<!-- GSD:profile-end -->
