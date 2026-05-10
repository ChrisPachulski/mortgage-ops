---
phase: 11
plan: 06
type: execute
wave: 6
depends_on:
  - "11-01"
  - "11-02"
  - "11-03"
  - "11-04"
  - "11-05"
files_modified:
  - .claude/skills/mortgage-ops/references/subagent-routing.md
  - .claude/agents/README.md
  - CLAUDE.md
autonomous: true
requirements: []
tags:
  - phase-11
  - subagents
  - references
  - documentation
  - phase-closeout
must_haves:
  truths:
    - ".claude/skills/mortgage-ops/references/subagent-routing.md exists and documents (a) when each of the 3 agents fires (with the >5 stress threshold + the 2-5-offer refi range + the single-loan amort case), (b) the SC-3 1000-token budget rationale, (c) the live-transcript capture recipe pointer to the fixture README, (d) Phase 10 progressive-disclosure on-demand load contract"
    - ".claude/agents/README.md exists and contains a one-paragraph summary per agent + frontmatter notes (model selection, tools whitelist, skills field) for repo-browsers (NOT loaded into agent context per D-02)"
    - "CLAUDE.md is cross-linked: the 'Project Skills' section (or equivalent) references the new agents and points at .claude/agents/README.md for browser-friendly summaries"
    - "subagent-routing.md is loaded on-demand by Phase 10 progressive-disclosure (NOT auto-loaded into SKILL.md context) per D-01 — file lives under .claude/skills/mortgage-ops/references/ alongside Phase 6 refi-npv.md and Phase 8 stress-tests.md"
    - "Both files are committed and contain expected sections; verified via grep + heading checks"
    - "No new tests added by this plan — Plan 11-05 already pinned all SC gates; this plan is documentation-only"
    - "Full suite still green (no regression — pure docs additions); mypy + ruff still clean"
  artifacts:
    - path: ".claude/skills/mortgage-ops/references/subagent-routing.md"
      provides: "Phase 10-progressive-disclosure-loaded reference doc; documents WHEN each Phase 11 agent fires + WHY the SC-3 token budget exists + HOW to capture replacement transcripts via claude -p for nightly eval; the canonical user-facing routing-decision documentation"
      min_lines: 100
      contains: "stress-test-agent"
    - path: ".claude/agents/README.md"
      provides: "Browser-friendly per-agent summary; one paragraph per agent + frontmatter highlights; for humans reading the repo on GitHub, NOT for agent context (D-02)"
      min_lines: 50
      contains: "amortization-agent"
  key_links:
    - from: ".claude/skills/mortgage-ops/references/subagent-routing.md"
      to: ".claude/skills/mortgage-ops/SKILL.md"
      via: "Phase 10 progressive-disclosure references-list (per SKLL-08 pattern: references/ folder loaded on demand only)"
      pattern: "references/subagent-routing.md"
    - from: ".claude/skills/mortgage-ops/references/subagent-routing.md"
      to: "tests/fixtures/subagent_transcripts/README.md"
      via: "cross-link to live-capture recipe documented in Plan 11-05 Task 1 fixture README"
      pattern: "tests/fixtures/subagent_transcripts/README.md"
    - from: ".claude/agents/README.md"
      to: ".claude/agents/{amortization-agent,refi-npv-agent,stress-test-agent}.md"
      via: "per-agent summary paragraph; markdown links to each agent file"
      pattern: "amortization-agent.md"
    - from: "CLAUDE.md"
      to: ".claude/agents/README.md"
      via: "GSD:project-skills (or equivalent) section references the new agents"
      pattern: "\\.claude/agents/"
---

<objective>
Ship the Phase 11 documentation surface: a Phase 10-progressive-disclosure-loaded reference doc (`.claude/skills/mortgage-ops/references/subagent-routing.md`) that documents when each agent fires + why the budgets exist + how to regenerate transcripts; a browser-friendly README at `.claude/agents/README.md` for repo-visitors; and a CLAUDE.md cross-link so the project's top-level entry point points at the new agents. Documentation-only plan — Plan 11-05 already pinned all SC gates, so this wave introduces no new tests and no behavioral changes.

Purpose: Phase 11 closeout. Without the references doc, the routing decisions encoded in Plans 11-03 (>5-scenario threshold) + 11-02 (2-5-offer refi range) + 11-01 (single-loan amort) live ONLY in agent body prose + tests — there's no canonical "here is how the Phase 11 routing decisions work, all in one place" reference for a future planner / debugger / reviewer. Without `.claude/agents/README.md`, GitHub repo-browsers see three opaque YAML-frontmatter MD files with no entry-point summary. Without CLAUDE.md cross-link, a fresh Claude session starting in the project doesn't immediately know the agents exist.

Per D-01, `subagent-routing.md` is on-demand-loaded by Phase 10 progressive disclosure (matches SKLL-08 + SKLL-09 references-folder doctrine; mirrors Phase 6 refi-npv.md + Phase 8 stress-tests.md placement). It does NOT auto-load into SKILL.md context — Phase 10's SKLL-09 enforces the on-demand contract. Per D-02, `.claude/agents/README.md` is for repo browsers, NOT for agent context (Anthropic agent-spec doesn't load README.md from the agents directory; it loads only the *-agent.md files).

Output: Two new MD files (~100 lines for subagent-routing.md, ~50-80 lines for README.md), one CLAUDE.md cross-link edit. Phase 11 then closes; Wave 7+ (if any) is a phase-closeout SUMMARY consolidation.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/11-subagents/11-PATTERNS.md
@.planning/phases/11-subagents/11-RESEARCH.md
@CLAUDE.md
@.planning/phases/11-subagents/11-01-amortization-agent-PLAN.md
@.planning/phases/11-subagents/11-02-refi-npv-agent-PLAN.md
@.planning/phases/11-subagents/11-03-stress-test-agent-PLAN.md
@.planning/phases/11-subagents/11-04-skill-routing-update-PLAN.md
@.planning/phases/11-subagents/11-04-SUBA-05-TODO.md
@.planning/phases/11-subagents/11-05-tests-and-fixtures-PLAN.md

<interfaces>
**References-folder doctrine (per RESEARCH "Recommended Project Structure" + Phase 8 references/stress-tests.md analog):**

`.claude/skills/mortgage-ops/references/*.md` files are loaded ON DEMAND by Phase 10's progressive-disclosure mechanism (SKLL-09). They are NOT auto-included in the SKILL.md core context (which has a 5k-token budget per SKLL-01); they are pulled in only when a mode file or the user explicitly references them. This keeps SKILL.md tight while making detailed reference content available when needed.

Existing references analogs (target patterns to mirror):
- Phase 5 ships `references/arm-mechanics.md` (the Phase-5-D-08 analog — first references doc).
- Phase 6 ships `references/refi-npv.md` (sign-convention discipline).
- Phase 8 ships `references/stress-tests.md` + `references/points-breakeven.md`.

Phase 11's `references/subagent-routing.md` SHOULD be discoverable from:
- The agent body files themselves (they reference this doc by relative path for "see also" context).
- The Phase 10 SKILL.md references-list (Phase 10 SKLL-08 / SKLL-09 enforces the loading contract; Phase 11 just provides the file).
- Phase 8 references/stress-tests.md "Subagent consumption hint" section (per 08-PATTERNS.md:261).

**`.claude/agents/README.md` non-loading note (D-02):**

Per the Anthropic sub-agents spec (https://code.claude.com/docs/en/sub-agents — verified by Plan 11-RESEARCH.md), the agents directory loader scans for `*-agent.md` files (or matches the documented pattern). It does NOT load `README.md`, `LICENSE.md`, etc. So `.claude/agents/README.md` is purely for human repo-browsers (e.g., GitHub) — it does not affect agent dispatch or context. This is intentional: it lets us write browser-friendly per-agent summaries without polluting the LLM's context budget.

**CLAUDE.md cross-link target (D-03):**

CLAUDE.md currently has a `<!-- GSD:skills-start source:skills/ -->` block (lines ~98-102) that says "No project skills found yet. Will populate as Phase 10 (Claude Skill Frontend) implements .claude/skills/mortgage-ops/SKILL.md." Phase 11 adds agents — these are sibling artifacts to skills, also under .claude/. The cross-link extends (or adds a sibling block to) this section to point at .claude/agents/README.md for browser-friendly per-agent summaries. The exact location/wording can adapt to whatever Phase 10 has done with the GSD:skills block by the time Plan 11-06 ships; if Phase 10 hasn't touched it, Plan 11-06 leaves the GSD:skills block alone and adds a separate "Project Subagents" subsection.

**Required content map for `.claude/skills/mortgage-ops/references/subagent-routing.md`:**

1. **Header + Purpose** — what this doc is, who reads it, when it's loaded (on-demand).
2. **The three agents — at a glance** — one-row-per-agent table: name | model | trigger | output shape | citation.
3. **When each agent fires (in detail):**
   - amortization-agent: single-loan amortization request; the "single-loan" qualifier matters because multi-loan comparisons route to refi-npv-agent (rate-and-term comparison) or stress-test-agent (parameter sweep); reference the trigger phrasing from Plan 11-01.
   - refi-npv-agent: 2-5 refi offers (range chosen because <2 = main thread; >5 = ranking signal degrades, surface in narrative); reference Plan 11-02 D-01 if applicable + the "Single-offer refi" Cost Discipline rejection.
   - stress-test-agent: >5-scenario sweeps; reference Plan 11-03 D-04 trigger phrase + the SUBA-05 routing rule + Plan 11-04 cross-phase TODO.
4. **The SC-3 1000-token budget rationale** — why 1000 specifically (matches the literal SC-3 wording; Haiku-tier output budget; ~10x headroom for follow-up questions in main context); how it's enforced (Plan 11-05 anthropic.count_tokens against synthetic transcript); how to diagnose breaches.
5. **Capturing replacement transcripts via claude -p** — a pointer to `tests/fixtures/subagent_transcripts/README.md` for the full live-capture recipe; the WHY (quarterly drift check, post-prompt-change verification); the WARNING (live capture costs paid-tier API credits and is non-deterministic).
6. **Phase 10 progressive-disclosure loading note** — this file is loaded on-demand only; it does NOT auto-load with SKILL.md; it's pulled in when a mode file references it or when a user explicitly asks about subagent routing.
7. **Cross-references** — links to the three agent files, to modes/stress.md (where SUBA-05 lives), to references/stress-tests.md (Phase 8 input contract), to references/refi-npv.md (Phase 6 sign convention), to .claude/agents/README.md (browser-friendly summaries).

**Required content map for `.claude/agents/README.md`:**

1. **Header** — what this directory contains.
2. **NOT loaded into agent context** — explicit note that this README is for human repo-browsers only.
3. **Per-agent summary** — one paragraph per agent (amortization, refi-npv, stress-test) covering: name, model tier (Haiku/Sonnet) + rationale, trigger summary, output format, single-line tool whitelist note, link to the *-agent.md file.
4. **Where to learn more** — pointer to `.claude/skills/mortgage-ops/references/subagent-routing.md` (for routing-decision detail), to ROADMAP.md Phase 11 (for SC traceability), to REQUIREMENTS.md SUBA-01..06 (for requirement traceability).
5. **No AI attribution reminder.**

**Edit target for CLAUDE.md (D-03):**

Locate either the `<!-- GSD:skills-start -->` block OR add a sibling block. Insert (or amend) so a fresh Claude session reading CLAUDE.md sees: "Project subagents: 3 agents under .claude/agents/ (amortization, refi-npv, stress-test). Browser-friendly summaries at .claude/agents/README.md; routing-decision detail at .claude/skills/mortgage-ops/references/subagent-routing.md (loaded on-demand)."
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create .claude/skills/mortgage-ops/references/subagent-routing.md (the on-demand-loaded routing-decision reference)</name>
  <files>.claude/skills/mortgage-ops/references/subagent-routing.md</files>
  <read_first>
    - .planning/phases/11-subagents/11-01-amortization-agent-PLAN.md (for the canonical amortization-agent trigger phrasing + output shape)
    - .planning/phases/11-subagents/11-02-refi-npv-agent-PLAN.md (for the canonical refi-npv-agent trigger phrasing + 2-5 offer range rationale)
    - .planning/phases/11-subagents/11-03-stress-test-agent-PLAN.md (for the canonical stress-test-agent trigger phrasing + >5 threshold rationale + SC-3 budget)
    - .planning/phases/11-subagents/11-04-SUBA-05-TODO.md (for the SUBA-05 cross-phase contract status)
    - .planning/phases/11-subagents/11-05-tests-and-fixtures-PLAN.md (for the SC-3 enforcement detail + the fixture README cross-reference)
    - .planning/phases/06-refinance-npv/06-PATTERNS.md (or equivalent — for the references/refi-npv.md analog file shape)
    - .planning/phases/08-stress-points/08-PATTERNS.md (for the references/stress-tests.md analog file shape)
    - .planning/phases/05-arm-modeling/05-PATTERNS.md (for the references/arm-mechanics.md analog — the FIRST references file, sets the doctrine)
  </read_first>
  <action>
    Create the file `.claude/skills/mortgage-ops/references/subagent-routing.md`. The directory `.claude/skills/mortgage-ops/references/` is created by Phase 10 (SKLL-08); if it does not exist at execution time, create it (single mkdir; no Phase 10 design depends on it being absent).

    File content (write verbatim — production reference doc; mirrors Phase 5/6/8 references/*.md doctrine):

    ```markdown
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
    scenarios. The threshold matches the literal SC-2 / SUBA-05 wording in ROADMAP.md and
    REQUIREMENTS.md. Trigger keywords: "stress test", "rate shock", "what if rates go to X",
    "income shock", "ARM reset path", "rate sweep", "scenario analysis".

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
    ```

    Critical details:
    - File length target: ~120-180 lines. Do not over-pad with restating individual agent body specs — those live in the agent files; this doc is the meta-routing reference.
    - Cross-references use relative paths from the file's location (`references/stress-tests.md` not `.claude/skills/mortgage-ops/references/stress-tests.md`) — matches Phase 5 + 8 sibling-references convention.
    - No Co-Authored-By in any text or in the commit message (CLAUDE.md global rule).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; mkdir -p .claude/skills/mortgage-ops/references &amp;&amp; test -f .claude/skills/mortgage-ops/references/subagent-routing.md &amp;&amp; test $(wc -l &lt; .claude/skills/mortgage-ops/references/subagent-routing.md) -ge 100 &amp;&amp; for kw in 'amortization-agent' 'refi-npv-agent' 'stress-test-agent' 'scenario_count > 5\|scenarios.*5\|>5' '1,000.token\|1000.token' 'progressive disclosure\|on.demand' 'claude -p'; do grep -ciE "$kw" .claude/skills/mortgage-ops/references/subagent-routing.md || { echo "MISSING keyword: $kw"; exit 1; }; done</automated>
  </verify>
  <acceptance_criteria>
    - `test -f .claude/skills/mortgage-ops/references/subagent-routing.md` exits 0
    - `wc -l .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 100
    - `grep -c '^# Subagent routing' .claude/skills/mortgage-ops/references/subagent-routing.md` returns 1 (top header)
    - `grep -c 'amortization-agent' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 3
    - `grep -c 'refi-npv-agent' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 3
    - `grep -c 'stress-test-agent' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 4
    - `grep -ciE '(scenario_count > 5|scenarios.*more than 5|>5 scenarios)' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (>5 threshold appears)
    - `grep -ciE '(1,000.token|1000.token|<.?1000)' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (SC-3 budget)
    - `grep -ciE '(progressive disclosure|on.demand)' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (D-01)
    - `grep -c 'claude -p' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (live-capture pointer)
    - `grep -c 'tests/fixtures/subagent_transcripts/README.md' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (cross-link to Plan 11-05 fixture README)
    - `grep -c 'modes/stress.md' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (SUBA-05 cross-ref)
    - `grep -c 'references/stress-tests.md' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (Phase 8 cross-ref)
    - `grep -c 'references/refi-npv.md' .claude/skills/mortgage-ops/references/subagent-routing.md` returns at least 1 (Phase 6 cross-ref)
    - `grep -ci 'co-authored-by' .claude/skills/mortgage-ops/references/subagent-routing.md` returns 0
  </acceptance_criteria>
  <done>
    references/subagent-routing.md exists with ≥100 lines, all required sections, all required cross-references, the >5 threshold + 1000-token budget rationale documented, the live-capture recipe pointer present, the on-demand-load semantics documented per D-01. No AI attribution.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create .claude/agents/README.md (browser-friendly per-agent summary; NOT loaded into agent context per D-02)</name>
  <files>.claude/agents/README.md</files>
  <read_first>
    - .claude/agents/amortization-agent.md (the canonical Haiku-agent file shape from Plan 11-01)
    - .claude/agents/refi-npv-agent.md (Sonnet-agent shape from Plan 11-02)
    - .claude/agents/stress-test-agent.md (Haiku-agent + CSV-escape-hatch shape from Plan 11-03)
    - .planning/phases/11-subagents/11-RESEARCH.md (frontmatter spec citation per Anthropic sub-agents docs — confirms README.md is NOT loaded by the agents directory loader)
  </read_first>
  <action>
    Create the file `.claude/agents/README.md`. The directory `.claude/agents/` exists from Wave 1.

    File content (write verbatim — browser-facing documentation; word choice less load-bearing than agent files but still production):

    ```markdown
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
    - Single refi offer evaluation: main thread (calls `scripts/refi_npv.py` directly).
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

    Per project CLAUDE.md global rule: do NOT include Co-Authored-By in any commit message
    that touches the agents directory. All agent files + this README are owned solely by the
    repo owner.
    ```

    Critical details:
    - File length target: ~70-100 lines. Do not pad — this is a browser-facing summary, not a tutorial.
    - Cross-references use relative paths from `.claude/agents/` (e.g., `../skills/mortgage-ops/references/subagent-routing.md`, `../../.planning/ROADMAP.md`) — matches GitHub markdown link convention.
    - Per D-02: this file is NOT in any agent's context. The "NOT loaded into agent context" section is the second heading specifically so a casual repo-browser sees it before the per-agent summaries (no confusion about whether they're editing the agent context).
    - No Co-Authored-By in the file or in the commit message.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/agents/README.md &amp;&amp; test $(wc -l &lt; .claude/agents/README.md) -ge 50 &amp;&amp; for kw in 'amortization-agent' 'refi-npv-agent' 'stress-test-agent' 'NOT loaded\|not loaded' 'Haiku' 'Sonnet'; do grep -ci "$kw" .claude/agents/README.md || { echo "MISSING keyword: $kw"; exit 1; }; done</automated>
  </verify>
  <acceptance_criteria>
    - `test -f .claude/agents/README.md` exits 0
    - `wc -l .claude/agents/README.md` returns at least 50
    - `grep -c '^# mortgage-ops subagents' .claude/agents/README.md` returns 1 (top header)
    - `grep -c 'amortization-agent' .claude/agents/README.md` returns at least 2
    - `grep -c 'refi-npv-agent' .claude/agents/README.md` returns at least 2
    - `grep -c 'stress-test-agent' .claude/agents/README.md` returns at least 2
    - `grep -ciE '(NOT loaded|not loaded into agent context)' .claude/agents/README.md` returns at least 1 (D-02 disclaimer)
    - `grep -c 'Haiku' .claude/agents/README.md` returns at least 2 (amortization + stress agents)
    - `grep -c 'Sonnet' .claude/agents/README.md` returns at least 1 (refi agent)
    - `grep -c 'subagent-routing.md' .claude/agents/README.md` returns at least 1 (cross-link to Task 1's reference doc)
    - `grep -c 'CLAUDE.md' .claude/agents/README.md` returns at least 1 (no-AI-attribution reminder)
    - `grep -ci 'co-authored-by' .claude/agents/README.md` returns 0 (file itself does not contain the prohibited string except in the negation context — verify the only occurrence is in "do NOT include Co-Authored-By")
  </acceptance_criteria>
  <done>
    .claude/agents/README.md exists with ≥50 lines, all three agent summaries, frontmatter shared-fields section, "when NOT to dispatch" guidance, cross-references to subagent-routing.md and ROADMAP/REQUIREMENTS, the D-02 "NOT loaded into agent context" disclaimer, and the no-AI-attribution reminder. No AI attribution in commit.
  </done>
</task>

<task type="auto">
  <name>Task 3: Cross-link from CLAUDE.md to .claude/agents/README.md (per D-03)</name>
  <files>CLAUDE.md</files>
  <read_first>
    - CLAUDE.md current `<!-- GSD:skills-start source:skills/ -->` block (lines ~98-102) and surrounding sections to identify the right insertion point
  </read_first>
  <action>
    Edit `/Users/cujo253/Documents/mortgage-ops/CLAUDE.md`. Locate the existing `<!-- GSD:skills-start -->` ... `<!-- GSD:skills-end -->` block (currently around lines 98-102 — verify at edit time since Phase 10 may have modified it).

    **If the GSD:skills block currently says "No project skills found yet" (Phase 10 has NOT yet shipped):** Add a NEW sibling section AFTER the GSD:skills-end marker (and before GSD:workflow-start). Use this content:

    ```markdown
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
    ```

    **If the GSD:skills block has been populated by Phase 10 (says something other than "No project skills found yet"):** Add the same `<!-- GSD:subagents-start ... GSD:subagents-end -->` block as a sibling AFTER the GSD:skills-end marker. Do NOT modify the GSD:skills block (Phase 10 owns it).

    Do NOT remove or modify any other GSD-managed block (project, stack, conventions, architecture, workflow, profile). Insert the new block in alphabetical proximity (between skills and workflow per the existing ordering).

    No Co-Authored-By in the commit. CLAUDE.md global rule.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f CLAUDE.md &amp;&amp; grep -c '<!-- GSD:subagents-start' CLAUDE.md &amp;&amp; grep -c '<!-- GSD:subagents-end' CLAUDE.md &amp;&amp; grep -c 'amortization-agent' CLAUDE.md &amp;&amp; grep -c 'refi-npv-agent' CLAUDE.md &amp;&amp; grep -c 'stress-test-agent' CLAUDE.md &amp;&amp; grep -c '\.claude/agents/README.md' CLAUDE.md &amp;&amp; grep -c '\.claude/skills/mortgage-ops/references/subagent-routing.md' CLAUDE.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '<!-- GSD:subagents-start' CLAUDE.md` returns 1
    - `grep -c '<!-- GSD:subagents-end' CLAUDE.md` returns 1
    - `grep -c '## Project Subagents' CLAUDE.md` returns 1
    - `grep -c 'amortization-agent' CLAUDE.md` returns at least 1
    - `grep -c 'refi-npv-agent' CLAUDE.md` returns at least 1
    - `grep -c 'stress-test-agent' CLAUDE.md` returns at least 1
    - `grep -c '\.claude/agents/README.md' CLAUDE.md` returns at least 1
    - `grep -c '\.claude/skills/mortgage-ops/references/subagent-routing.md' CLAUDE.md` returns at least 1
    - The pre-existing GSD blocks (`GSD:project-start`, `GSD:stack-start`, `GSD:conventions-start`, `GSD:architecture-start`, `GSD:skills-start`, `GSD:workflow-start`, `GSD:profile-start`) all still exist and are unmodified — `grep -cE '<!-- GSD:(project|stack|conventions|architecture|skills|workflow|profile)-(start|end)' CLAUDE.md` returns 14 (7 sections × 2 markers each)
    - `grep -ci 'co-authored-by' CLAUDE.md` should return whatever it returned BEFORE this task (Plan 11-06 introduces no Co-Authored-By language)
  </acceptance_criteria>
  <done>
    CLAUDE.md contains a new GSD:subagents block referencing all three agents + the README + the routing-detail reference doc. Pre-existing GSD blocks untouched. No AI attribution.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| references/subagent-routing.md → Phase 10 progressive disclosure | If Phase 10 mis-classifies the file as auto-load (not on-demand), it pollutes the SKILL.md 5k-token budget |
| .claude/agents/README.md → Anthropic agents directory loader | If the loader changes its scan pattern to include README.md (currently only `*-agent.md`), the README would unexpectedly enter agent context, polluting it |
| CLAUDE.md GSD:subagents block → automated GSD tooling | If a future GSD command rewrites the GSD:subagents block from a template, custom content here could be lost |
| Cross-references to other plan files (11-04-SUBA-05-TODO.md, ROADMAP.md, REQUIREMENTS.md) → file-system stability | If those files are renamed/moved, the cross-references rot |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-35 | Information Disclosure (subagent-routing.md gets auto-loaded into SKILL.md context, blowing past SKLL-01 5k-token budget) | references/subagent-routing.md classification | mitigate | Doc itself documents (in "Loading semantics" section) that it MUST be on-demand-loaded; Phase 10 SKLL-09 enforces the references/ progressive-disclosure contract; Phase 10 PLAN-CHECK should grep for any auto-include of references/ files in SKILL.md |
| T-11-36 | Tampering (Anthropic agents directory loader changes to include README.md, polluting agent context) | .claude/agents/README.md | accept | This is Anthropic spec stability risk, not under mortgage-ops control. The README explicitly says "NOT loaded into agent context" so a future loader change would surface as obvious behavior change; mitigate by tracking Anthropic spec updates per RESEARCH "Valid until: 2026-06-02" cadence |
| T-11-37 | Tampering (a future GSD command rewrites the GSD:subagents block from a generic template, dropping the per-agent content) | CLAUDE.md GSD:subagents block | mitigate | Block uses standard `<!-- GSD:* -->` delimiter convention so GSD tooling recognizes it as managed; if a future GSD command supports custom content (per the GSD:profile-start "managed by generate-claude-profile — do not edit manually" precedent), follow that pattern; for v1 the block is hand-authored and re-runnable |
| T-11-38 | Repudiation (cross-reference to .planning/phases/11-subagents/11-04-SUBA-05-TODO.md becomes stale if Phase 10 lands and the TODO marker Status is updated to "WIRED") | references/subagent-routing.md SUBA-05 cross-ref | accept | The TODO marker file persists per Plan 11-04 ("Do not delete this file at any later wave"); the cross-link remains valid even after Status update; if Phase 10 ships AND someone deletes the TODO marker, that is a Plan 11-04 contract violation |
| T-11-39 | Information Disclosure (live-capture recipe in references/subagent-routing.md inadvertently embeds a real ANTHROPIC_API_KEY example) | live-capture-recipe pointer in subagent-routing.md | mitigate | Doc only POINTS at tests/fixtures/subagent_transcripts/README.md for the recipe; does NOT inline the recipe; the actual recipe in the fixture README itself avoids embedding keys per Plan 11-05 T-11-29 mitigation |
| T-11-40 | Tampering (someone deletes references/subagent-routing.md to "shrink the references folder", thinking it's redundant with the agent body files) | references/subagent-routing.md persistence | mitigate | The file's "Loading semantics" section explicitly explains its role (meta-routing reference for cases where a planner / debugger needs the cross-cutting view); Phase 11 SUMMARY notes its persistence in the closeout record |
</threat_model>

<verification>
- references/subagent-routing.md exists with ≥100 lines covering all three agents + the >5 threshold + the 1000-token budget rationale + the live-capture recipe pointer + the on-demand-load semantics + cross-references to Phase 5/6/8 references
- .claude/agents/README.md exists with ≥50 lines containing all three agent summaries + the D-02 "NOT loaded into agent context" disclaimer + the cross-link to subagent-routing.md
- CLAUDE.md contains a new GSD:subagents block with all three agent names + the cross-references; no pre-existing GSD blocks modified
- Full suite still green (no regression — pure docs additions)
- mypy + ruff still clean
- No Co-Authored-By in any file or commit
</verification>

<success_criteria>
- references/subagent-routing.md and .claude/agents/README.md committed
- CLAUDE.md cross-link wired
- Phase 11 documentation surface complete: future planners / debuggers / repo-browsers can find the routing-decision rationale, the agent summaries, and the test gates from any of three entry points (CLAUDE.md, .claude/agents/README.md, references/subagent-routing.md)
- D-01 (on-demand load) honored — references/subagent-routing.md is in the references/ folder where Phase 10 SKLL-09 enforces progressive disclosure
- D-02 (README.md not in agent context) honored + documented in the README itself
- D-03 (CLAUDE.md cross-link) honored
- No new tests required (Plan 11-05 already pinned all SC gates; this is a docs-only plan)
- Phase 11 ready for closeout SUMMARY consolidation
- No AI attribution in any file or commit
</success_criteria>

<locked_decisions>
- **D-01: references/subagent-routing.md is loaded on-demand by Phase 10 progressive-disclosure mechanism (NOT auto-loaded into SKILL.md context).** Per Phase 10 SKLL-09 + the references/ folder doctrine established by Phase 5 references/arm-mechanics.md (Phase 5 D-08 originating analog) and continued by Phase 6 references/refi-npv.md + Phase 8 references/stress-tests.md. The doc itself documents this loading semantics in its "Loading semantics" section so a future planner or auto-include refactor doesn't accidentally pull it into the SKLL-01 5k-token budget.
- **D-02: .claude/agents/README.md is for human repo-browsers (e.g., GitHub UI), NOT loaded into agent context.** Per the Anthropic sub-agents spec (https://code.claude.com/docs/en/sub-agents — RESEARCH-verified) the agents directory loader scans for `*-agent.md` files matching the documented frontmatter pattern; it does NOT load README.md, LICENSE.md, or other auxiliary files. The README is intentionally non-load-bearing — it summarizes per-agent content for humans without polluting LLM context. The README itself states this disclaimer prominently (second heading) so a casual reader doesn't get confused.
- **D-03: CLAUDE.md cross-link via a new `<!-- GSD:subagents-start ... GSD:subagents-end -->` sibling block.** Mirrors the existing GSD-managed-block convention in CLAUDE.md (project, stack, conventions, architecture, skills, workflow, profile). New block sits between GSD:skills (Phase 10's territory) and GSD:workflow. If future GSD tooling rewrites managed blocks from templates, this block follows the convention and either survives (if tooling preserves custom content per the GSD:profile-start "managed by generate-claude-profile" precedent) or gets re-added by a follow-up plan.
</locked_decisions>

<deviation_rules>
- If Phase 10 ships SKILL.md with an auto-include of `references/subagent-routing.md` (violating SKLL-09 progressive disclosure for this file): that is a Phase 10 contract violation. Surface as a Phase 10 gap, not a Plan 11-06 fix.
- If Anthropic updates the agents directory loader to include README.md in agent context: update D-02 + the README's disclaimer, AND review the README content for context-budget impact. Do NOT make the change in this plan — surface as a follow-up if/when the spec changes.
- If CLAUDE.md's existing GSD:skills block has been populated by Phase 10 with content that already references the agents directory: detect this at edit time and SKIP adding the GSD:subagents block (avoid duplication). Update the SUMMARY to note the consolidation.
- If `.claude/skills/mortgage-ops/references/` does NOT exist at task time (Phase 10 not yet shipped): create the directory (single mkdir) — this is a docs-only directory creation, NOT a layering violation. Do NOT create SKILL.md, modes/, scripts/, or any other Phase 10-owned content.
- If a synthetic-fixture cross-link in subagent-routing.md gets stale (e.g., fixture renamed in a future plan): update via a docs-only follow-up plan; the cross-link rot is non-fatal (the link target moved but the routing-decision content remains correct).
</deviation_rules>

<dependencies>
**Wave 6 dependencies:**

- **Hard:** Waves 1, 2, 3 (Plans 11-01..03) — the three agent files MUST exist before this plan documents them. References to specific agent body content (Hard rules, Cost Discipline) require the agent files to be authored.
- **Hard:** Wave 4 (Plan 11-04) — the SUBA-05 routing seam (or its TODO marker) MUST be in place before subagent-routing.md cross-references it. The TODO marker file (`11-04-SUBA-05-TODO.md`) is referenced by name in subagent-routing.md and the README.
- **Hard:** Wave 5 (Plan 11-05) — the synthetic transcript fixtures + their README MUST exist before subagent-routing.md points readers at them for the live-capture recipe.
- **Soft (Phase 10):** the references/ directory is owned by Phase 10 (SKLL-08). If Phase 10 has not yet shipped, this plan creates the directory (single mkdir) for the file landing — does not block on full Phase 10 completion. The on-demand-load semantics (D-01) require Phase 10 SKLL-09 to be honored at runtime; this plan ships the file in the right location and documents the contract; Phase 10 enforces the loading.
- **Soft (Phase 5/6/8):** the references/arm-mechanics.md, references/refi-npv.md, references/stress-tests.md sibling files are referenced as cross-links. If those files don't exist at task time, the cross-references are forward-pointers (they'll resolve when those phases land). subagent-routing.md is shippable independently.

**Cross-phase HARD GATE for Phase 11 PHASE-CLOSEOUT:**

After Wave 6 ships:
- All Phase 11 deliverables exist (Plans 11-00..11-06).
- All Phase 11 SC-1..SC-5 have measurable test gates (modulo Plan 11-04 branch (b) cross-phase deferral).
- All SUBA-01..06 requirements are CLOSED (modulo SUBA-05 in Plan 11-04 branch (b) → DEFERRED-WITH-CONTRACT).
- Documentation surface complete: routing-decision detail (subagent-routing.md), browser-friendly summaries (.claude/agents/README.md), top-level cross-link (CLAUDE.md GSD:subagents block).

Phase 11 is ready for `/gsd-verify-work` and the Phase 11 closeout SUMMARY.

**Downstream:**
- Phase 12 (FRED MCP + Eval Harness) consumes this documentation surface — EVAL-03 / EVAL-04 reference the routing-decision detail when authoring cross-agent eval prompts; the live-capture recipe in tests/fixtures/subagent_transcripts/README.md feeds nightly eval regeneration.
- Future planners landing in the project read CLAUDE.md → see the GSD:subagents block → follow the cross-link to .claude/agents/README.md → drill into specific agent files OR the routing-decision reference. Three-tier discoverability mirrors the references/ progressive-disclosure model at the agents level.
</dependencies>

<output>
After completion, create `.planning/phases/11-subagents/11-06-SUMMARY.md` documenting:
- Path to created reference doc: `.claude/skills/mortgage-ops/references/subagent-routing.md` (line count + sections shipped)
- Path to created README: `.claude/agents/README.md` (line count + sections shipped)
- CLAUDE.md edit: line range of the new GSD:subagents block; confirmation that pre-existing GSD blocks are unmodified (`grep -cE '<!-- GSD:(project|stack|conventions|architecture|skills|workflow|profile)-(start|end)' CLAUDE.md` returns 14)
- D-01 (on-demand load) honored: file lives in references/ folder where Phase 10 SKLL-09 enforces progressive disclosure
- D-02 (README.md not in agent context) honored: disclaimer present in README; Anthropic spec citation included
- D-03 (CLAUDE.md cross-link) honored: GSD:subagents block added as sibling to GSD:skills
- Full suite still green (no regression — pure docs additions): pytest output summary
- mypy + ruff still clean (no test/code changes; should be no-op): confirmation
- Confirmation: no Co-Authored-By in any file or commit message
- Phase 11 closeout candidate status: Plans 11-00..11-06 all shipped; SC-1..SC-5 measurable; SUBA-01..04+06 CLOSED; SUBA-05 in Plan-11-04-determined state (CLOSED for branch a, DEFERRED-WITH-CONTRACT for branch b)
- Recommendation: ready for `/gsd-verify-work` Phase 11 audit pass and Phase 11 SUMMARY consolidation
</output>
