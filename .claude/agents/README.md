# mortgage-ops subagents

Three project-scoped Claude Code subagents that provide context-isolated dispatch for
calc-heavy mortgage operations. Each agent is a Markdown file with YAML frontmatter
(`name`, `description`, `model`, `tools`, `skills`); the body is a focused system prompt.

## NOT loaded into agent context

Per the Anthropic sub-agents spec (https://code.claude.com/docs/en/sub-agents) the agents
directory loader scans for `*-agent.md` files (matching the documented frontmatter pattern)
and loads them at session start. It does **not** load `README.md`, `LICENSE.md`, or any
other auxiliary file in this directory. This README exists for **human repo-browsers**
(e.g., GitHub) and is intentionally NOT in the agents' context window.

Routing-decision detail (when each agent fires; budget rationale; live-capture recipe) lives
in `../skills/mortgage-ops/references/subagent-routing.md` — that file IS available to the
agents (loaded on-demand by Phase 10 progressive disclosure).

## The three agents

### `amortization-agent.md`

Single-loan amortization specialist. **Model: Haiku** (one shell-out + one format = no
multi-step reasoning). Fires when the user asks for ONE loan's payment-by-payment detail
(no parameter sweep, no multi-offer comparison). Output: a markdown table (≤30 rows) OR a
CSV path under `reports/{NNN}-amortization-{YYYY-MM-DD}.csv`. Tools: `Read, Bash, Write`
(Write is for CSV output when the schedule exceeds the inline display threshold). Shells
out to `.claude/skills/mortgage-ops/scripts/amortize.py`. Closes REQUIREMENTS.md SUBA-01
(Plan 11-01).

### `refi-npv-agent.md`

Refinance NPV ranking specialist. **Model: Sonnet** (multi-step reasoning across 2-5
offers — rate vs closing costs vs cash-out vs points tradeoffs require Sonnet-tier
reasoning, not Haiku-tier table compression). Fires when the user has 2-5 refi offers and
asks "which is best?", "rank by NPV", "what's the breakeven on each?". Output: a ranked
markdown table sorted descending by NPV (columns: lender | rate | closing_costs |
breakeven_months | NPV) + 2-3 sentence narrative naming the winner and decisive factor.
Tools: `Read, Bash` — **no Write** in v1 per RESEARCH Open Question 1 (inline markdown
sufficient for typical 2-5 offer comparisons; CSV-output mode is a future iteration if
Phase 12 evals demand it). Shells out to `.claude/skills/mortgage-ops/scripts/refi_npv.py`
once per offer; ranks the outputs by NPV. Closes REQUIREMENTS.md SUBA-02 (Plan 11-02).

### `stress-test-agent.md`

Parameter-grid stress sweep specialist. **Model: Haiku** (Phase 8 owns the math; this
agent's only reasoning load is "compress the pre-computed `scenario_summary` table to
≤1,000 tokens" — summarization, not multi-step reasoning). Fires when the user requests
a stress sweep with **strictly more than 5 scenarios** (the SUBA-05 / SC-2 routing rule
in `../skills/mortgage-ops/modes/stress.md`). Output: a ≤1,000-token summary — top-of-JSON
`scenario_summary` table verbatim + 2-3 sentence narrative + ≤3 highlight rows + a
`Computed by:` citation line. Tools: `Read, Bash, Write` (Write is for the CSV escape
hatch — if the user explicitly requests "the full sweep", agent writes the JSON detail to
`reports/{NNN}-stress-{YYYY-MM-DD}.csv` and returns the path, NOT the content). Shells
out to `.claude/skills/mortgage-ops/scripts/stress_test.py` ONCE with the full grid (the
script handles the per-scenario loop). Closes REQUIREMENTS.md SUBA-03 (Plan 11-03).

## Frontmatter summary

All three agents share these frontmatter fields:
- `name:` — kebab-case, MUST match the filename stem.
- `description:` — the routing trigger Claude Code reads at dispatch time; >30 chars;
  starts with a clear intent statement (stress-test-agent's starts with the literal
  "Use proactively for stress sweeps with >5 scenarios" per Plan 11-03 D-04).
- `model:` — short alias (`haiku` or `sonnet`); not version-pinned so model upgrades don't
  require touching three agent files.
- `skills:` — `[mortgage-ops]` for all three; injects the Phase 10 SKILL.md content into
  the agent's context at spawn time.
- `tools:` — explicit allowlist (Read, Bash, optionally Write) per Anthropic-spec tool
  whitelist convention. NEVER includes `Edit` (subagents don't edit files; they shell out
  to scripts).

## When NOT to dispatch a subagent

- Single-loan amortization is fine on the main thread if context is uncluttered — the
  amortization-agent shines when the main thread is already heavy and dispatch saves
  compaction.
- Single refi offer evaluation: main thread (calls `scripts/refi_npv.py` directly) — the
  refi-npv-agent's Cost Discipline rejects single-offer dispatches outright.
- Stress sweep with ≤5 scenarios: main thread (the dispatch overhead isn't worth it for
  ~500-token output).

The Cost Discipline section in each agent's body REJECTS misrouted dispatches with an
explicit "wrong agent — route to X instead" message, so an accidental misroute is
self-correcting (the agent returns immediately without doing the work).

## Where to learn more

- Routing decisions in detail: `../skills/mortgage-ops/references/subagent-routing.md`
  (loaded on-demand by Phase 10 progressive disclosure).
- SUBA-05 routing seam (>5 scenarios → stress-test-agent): `../skills/mortgage-ops/modes/stress.md`
  (Plan 11-04 wires the rule there; cross-phase contract at
  `../../.planning/phases/11-subagents/11-04-SUBA-05-TODO.md`).
- Phase 11 success criteria: `../../.planning/ROADMAP.md` Phase 11 section (SC-1..SC-5).
- Per-requirement traceability: `../../.planning/REQUIREMENTS.md` SUBA-01..SUBA-06.
- Test gates: `../../tests/test_subagents.py` + the synthetic transcripts at
  `../../tests/fixtures/subagent_transcripts/` (live-capture recipe in that directory's
  README).

## No AI attribution

Per project CLAUDE.md global rule: do NOT include any AI attribution in any commit message
that touches the agents directory. All agent files + this README are owned solely by the
repo owner.
