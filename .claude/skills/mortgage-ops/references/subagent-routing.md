# Subagent routing — when each Phase 11 agent fires

**Loaded:** on-demand only (Phase 10 SKLL-09 progressive disclosure; NOT auto-included in SKILL.md core context).
**Audience:** Claude Code main thread when routing decisions are ambiguous; the user when asking "why did this dispatch go where it did?"; future planners/debuggers reviewing the Phase 11 contract.
**Sibling docs:** `references/arm-mechanics.md` (Phase 5 doctrine), `references/refi-npv.md` (Phase 6 sign convention), `references/stress-tests.md` (Phase 8 input contract — UPSTREAM of stress-test-agent).
**Source plans:** `.planning/phases/11-subagents/11-01..06-*-PLAN.md`.

## The three agents — at a glance

| Agent | Model | Trigger | Output shape | Source plan |
|---|---|---|---|---|
| `amortization-agent` | Haiku | Single-loan amortization request | Markdown table OR CSV path under `reports/{NNN}-amortization-{YYYY-MM-DD}.csv` | Plan 11-01 |
| `refi-npv-agent` | Sonnet | 2-5 refi offers — "rank by NPV" | Ranked markdown table sorted descending by NPV + 2-3 sentence narrative | Plan 11-02 |
| `stress-test-agent` | Haiku | Stress sweep with >5 scenarios | ≤1,000-token summary: top-of-JSON `scenario_summary` table verbatim + 2-3 sentence narrative + ≤3 highlight rows | Plan 11-03 |

## When each agent fires

### amortization-agent (Haiku, single-loan)

Fires when the user asks for ONE loan's payment-by-payment detail with no parameter sweep
and no multi-offer comparison. Trigger keywords: "amortization schedule", "payment schedule",
"monthly P&I", "biweekly cadence", "extra principal", "what's my interest over X years".

Does NOT fire for:
- Multi-loan comparisons → use main thread or `refi-npv-agent` (if comparing refi offers).
- Parameter sweeps (rate shock, income shock, ARM reset path) → use `stress-test-agent`.
- "How much can I qualify for?" → use main thread (calls `scripts/affordability.py` directly).

Why Haiku: one shell-out + one format = no multi-step reasoning. See Plan 11-01 Cost Discipline.

### refi-npv-agent (Sonnet, 2-5 offers)

Fires when the user has 2-5 refinance offers and asks "which is best?", "rank by NPV",
"what's the breakeven on each?". Trigger keywords: "refi", "refinance", "rate-and-term",
"cash-out refi", "compare offers", "rank offers".

Does NOT fire for:
- Single-offer evaluation → use main thread (calls `scripts/refi_npv.py` directly).
- More than 5 offers → still fires here, but the ranking signal degrades past 5; the agent
  will flag in its narrative if the user provides 6+ offers.
- Stress sweeps across rates → use `stress-test-agent` (per the >5-scenario rule).

Why 2-5 range:
- <2 (single offer) is rejected by the agent's Cost Discipline section — Sonnet is overkill
  for a single shell-out.
- >5 is technically accepted but the comparative-ranking signal degrades; if the user has
  6+ offers, they probably want a stress sweep over a parameter grid (route to
  `stress-test-agent`) rather than offer-by-offer NPV ranking.

Why Sonnet: ranking 2-5 offers requires reasoning across tradeoffs (rate vs closing costs
vs cash-out vs points). Haiku-tier table-compression is insufficient. See Plan 11-02 Cost
Discipline + Plan 11-02 Hard rule #5 (the ranked-by-NPV-descending output contract).

Tools whitelist: `[Read, Bash]` — NO Write tool in v1 per RESEARCH Open Question 1 (inline
markdown sufficient for typical 2-5 offer comparisons; future iteration can add Write for
a CSV-output mode if Phase 12 evals demand it).

### stress-test-agent (Haiku, >5 scenarios)

Fires when the user requests a parameter-grid stress sweep with **strictly more than 5**
scenarios (i.e., `scenario_count > 5`). The threshold matches the literal SC-2 / SUBA-05
wording in ROADMAP.md and REQUIREMENTS.md. Trigger keywords: "stress test", "rate shock",
"what if rates go to X", "income shock", "ARM reset path", "rate sweep", "scenario analysis".

Does NOT fire for:
- Single what-if (one scenario) → main thread.
- Sweep with ≤5 scenarios → main thread (the dispatch overhead isn't worth it; output
  fits comfortably in main context).
- Multi-loan amortization comparison → use `refi-npv-agent` (for refi specifically) or
  construct a manual scripts/amortize.py loop on the main thread.

Why >5 strictly: literal SC-2 wording. Career-ops uses ≥3 URLs as its threshold (different
domain, different work shape); mortgage-ops chose >5 because that's what the requirement
says. Plan 11-04 LOCKED DECISION D-01 pinned this; off-by-one risk surfaced in
11-RESEARCH.md Open Question #3.

Why Haiku: Phase 8 owns the math (`scripts/stress_test.py` does all the per-scenario
calculation and emits the top-of-JSON `scenario_summary` table). The agent's only
reasoning load is "compress the pre-computed summary table to ≤1,000 tokens" — Haiku
is the right tier for summarization.

Tools whitelist: `[Read, Bash, Write]` — Write is for the CSV escape hatch (if user
explicitly requests "the full sweep", agent writes the JSON detail to
`reports/{NNN}-stress-{YYYY-MM-DD}.csv` and returns the path, NOT the content). Per
Plan 11-03 Hard rule #5 + Workflow Step 6.

## The 1,000-token budget for stress-test-agent (SC-3 rationale)

Per ROADMAP.md SC-3 (verbatim): "End-to-end test: a 50-scenario rate-shock stress sweep
dispatched through the subagent returns a summary < 1,000 tokens to the main context."

**Why 1,000 specifically:**
- Matches the literal SC-3 wording (no hedging — the threshold is the requirement).
- Haiku-tier summarization output is typically ~5-15 tokens per row × ~5-10 representative
  rows + 50-150 tokens of narrative + ~50 tokens of citation = ~500 tokens for a clean
  summary; 1,000 leaves ~50% headroom for edge-case verbosity (more highlight rows,
  richer narrative for breach scenarios).
- Main context room: returning ≤1,000 tokens leaves ~9× headroom in a typical Sonnet/Opus
  conversation for follow-up Q&A on the summary without compaction.

**How it's enforced:**

Plan 11-05 ships `tests/test_subagents.py::test_SUBA_06_stress_summary_under_1000_tokens`
which calls `anthropic.Anthropic().messages.count_tokens(model="claude-haiku-4-5", ...)`
against the recorded synthetic transcript fixture at
`tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl`. Per Plan 11-05
LOCKED DECISIONS D-01 (anthropic.count_tokens, NOT tiktoken) and D-03 (strict <1000
threshold). Skipif-gated on `ANTHROPIC_API_KEY` for airgapped CI.

**How to diagnose a budget breach:**
1. Run `pytest tests/test_subagents.py::test_SUBA_06_stress_summary_under_1000_tokens -v`.
   Note the reported token count.
2. If the count exceeds 1,000 because the synthetic fixture was edited: trim the fixture
   (drop a highlight row; shorten the narrative). Per Plan 11-05 D-02 the fixture is
   hand-authored to mirror canonical agent output; tightening it is a planning decision,
   not a test bug.
3. If the count exceeds 1,000 because the AGENT's actual output (captured via
   `claude -p`) requires >1,000 tokens: the SC-3 budget is too tight for the chosen output
   shape. Surface as a Phase 12 follow-up: either relax the threshold (requires a roadmap
   amendment) or shrink the output shape in the agent body.

## Capturing replacement transcripts via claude -p

The recorded transcripts at `tests/fixtures/subagent_transcripts/*.transcript.jsonl` are
SYNTHETIC for v1 (per Plan 11-05 LOCKED DECISION D-02 — CI determinism + free + airgap-safe).
They represent the canonical output shape each agent SHOULD produce, hand-authored to mirror
the agent body specs.

Quarterly (or after any agent prompt change), regenerate from a real Claude Code session:
1. See the live-capture recipe at `tests/fixtures/subagent_transcripts/README.md`.
2. The recipe uses `claude -p "<prompt>" --output-format json | jq -c > <name>.NEW`,
   diffs against the committed fixture, promotes if the shape is unchanged.
3. Re-run `uv run pytest tests/test_subagents.py -v -k 'SUBA_04 or SUBA_06'` to confirm
   SC-3 + SC-4 still pass against the fresh transcript.

Live capture costs paid-tier API credits and is non-deterministic — that's the whole reason
CI uses synthetic fixtures. Do NOT add live-capture invocations to CI.

## Loading semantics (Phase 10 progressive disclosure)

This file is in `.claude/skills/mortgage-ops/references/`. Per Phase 10 SKLL-09:
> "References load on demand (progressive disclosure per Anthropic skill convention)."

Concretely: this file is NOT included in the SKILL.md core context (which has the SKLL-01
5,000-token budget). It loads when:
- A mode file (e.g., `modes/stress.md`) explicitly references it.
- The user asks "why did this dispatch go to X?" and SKILL.md routes to the references
  lookup.
- A planner reviewing the Phase 11 contract opens it directly via `Read`.

Do NOT inline this file's content into SKILL.md or any modes/*.md file — that defeats
Phase 10 SKLL-01's compaction discipline. The cross-link from a mode file to here is one
line (`See references/subagent-routing.md for full routing detail`).

## Cross-references

- Agent files: `.claude/agents/amortization-agent.md`, `.claude/agents/refi-npv-agent.md`,
  `.claude/agents/stress-test-agent.md`.
- Browser-friendly summaries: `.claude/agents/README.md` (NOT loaded into agent context;
  for human repo-browsers only — Plan 11-06 D-02).
- SUBA-05 routing seam: `.claude/skills/mortgage-ops/modes/stress.md` (Plan 11-04 wires
  the >5 dispatch rule there; if Phase 10 hasn't shipped at Plan 11-04 time, see
  `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md` for the cross-phase contract).
- Upstream input contract: `references/stress-tests.md` (Phase 8 designed the
  `scenario_summary` top-of-JSON table specifically for stress-test-agent consumption).
- Sign-convention dependency: `references/refi-npv.md` (Phase 6 pinned borrower-perspective
  sign convention; refi-npv-agent enforces it via Hard rule #2).

---

Reference: this doc honors the Phase 5/6/8 `references/*.md` doctrine (one MD file per
domain concern, on-demand-loaded by Phase 10 progressive disclosure). The file is sibling
to `references/arm-mechanics.md` (the originating analog from Phase 5 D-08) and follows
the same section-shape (Overview → Detail → Citations → Cross-references). No AI
attribution per CLAUDE.md global rule.
