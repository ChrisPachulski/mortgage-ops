---
phase: 11
plan: 02
type: execute
wave: 2
depends_on:
  - "11-00"
files_modified:
  - .claude/agents/refi-npv-agent.md
autonomous: true
requirements:
  - SUBA-02
tags:
  - phase-11
  - subagents
  - refi-npv-agent
  - sonnet
  - suba-02
must_haves:
  truths:
    - ".claude/agents/refi-npv-agent.md exists at repo root with valid YAML frontmatter"
    - "Frontmatter contains exactly: name=refi-npv-agent, model=sonnet, skills=[mortgage-ops], description (>30 chars), tools (Read+Bash; NO Write per RESEARCH Open Question 1)"
    - "Body section instructs Claude to NEVER compute NPV inline (must shell out to scripts/refi_npv.py per offer)"
    - "Body section locks borrower-perspective sign convention (outflows negative, savings positive) per Phase 6 references/refi-npv.md"
    - "Body section describes ranked-NPV-table output: lender | rate | closing_costs | breakeven_months | NPV (with sign), sorted descending by NPV"
    - "Body section enforces READ-ONLY user layer (household.yml/profile.yml/*.duckdb never written)"
    - "File size ≤200 lines (per orchestrator constraint)"
    - "Wave 0 stub test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet flips from xfail to passing"
  artifacts:
    - path: ".claude/agents/refi-npv-agent.md"
      provides: "Phase 11 refinance NPV subagent definition (Sonnet, multi-offer ranking, shells out to scripts/refi_npv.py)"
      min_lines: 80
      contains: "name: refi-npv-agent"
  key_links:
    - from: ".claude/agents/refi-npv-agent.md frontmatter skills field"
      to: ".claude/skills/mortgage-ops/SKILL.md"
      via: "Anthropic skills:[name] injection at agent spawn time"
      pattern: "skills:"
    - from: ".claude/agents/refi-npv-agent.md body"
      to: ".claude/skills/mortgage-ops/scripts/refi_npv.py"
      via: "bash invocation per --help-first doctrine; called once per offer"
      pattern: "scripts/refi_npv.py"
    - from: "tests/test_subagents.py test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet"
      to: ".claude/agents/refi-npv-agent.md"
      via: "_split_frontmatter helper from Wave 0; assertion fm['model'] == 'sonnet'"
      pattern: "model: sonnet"
---

<objective>
Ship `.claude/agents/refi-npv-agent.md` — the second of three Phase 11 subagent definitions. **Sonnet** model (the only Sonnet agent in Phase 11; Sonnet because multi-step NPV ranking requires reasoning across offer tradeoffs), tools whitelist deliberately omits Write per RESEARCH.md Open Question 1 v1 decision (returns inline ranked table, no CSV output). Closes SUBA-02.

Purpose: SUBA-02 is the highest-reasoning-load agent in Phase 11 — it composes N invocations of `scripts/refi_npv.py` (one per offer) and ranks results by NPV with a borrower-perspective sign convention. Sonnet is the right tier per PROJECT.md key decision row + 11-RESEARCH.md "Standard Stack" rationale ("Sonnet for complex reasoning, ranking, tradeoffs"). The output contract — ranked markdown table — is deliberately scoped to inline output to keep the v1 attack surface narrow (no Write tool).

Output: One agent file (~80-150 lines, capped at 200). Body mirrors the amortization-agent template structure (hard rules → workflow → cost discipline → handoff hints) with refi-specific content. Wave 0 xfail flips to passing.
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
@.planning/phases/11-subagents/11-00-test-infrastructure-PLAN.md
@.planning/phases/11-subagents/11-01-amortization-agent-PLAN.md

<interfaces>
Per Anthropic sub-agents spec (https://code.claude.com/docs/en/sub-agents) — frontmatter shape (Sonnet variant; no Write tool):

```yaml
---
name: refi-npv-agent                  # MUST match filename stem
description: <one-sentence routing trigger Claude reads at dispatch>
model: sonnet                         # short alias per 11-PATTERNS.md CRITICAL #1a; Sonnet for ranking reasoning
skills:
  - mortgage-ops
tools:
  - Read
  - Bash
---
```

Per 11-RESEARCH.md Code Example 2 (canonical body template) and 11-PATTERNS.md "refi-npv-agent" pattern assignments + cross-phase contract source (Phase 6 06-PATTERNS.md:158 + 06-RESEARCH.md:288 documented that lib.refinance.evaluate is safe to call N times — designed FOR this consumer):

Body MUST include:
1. Hard rules section (numbered 1..5):
   - Never compute NPV inline (shell out to scripts/refi_npv.py once per offer)
   - Sign convention: outflows negative, savings positive (borrower perspective per Phase 6 REFI-09)
   - Run --help first; do not read script source
   - READ-ONLY user layer (CAN read config/household.yml for current loan; NEVER writes)
   - Output format: ranked markdown table sorted by NPV descending; columns: lender | rate | closing_costs | breakeven_months | NPV
2. Workflow section (numbered 1..5): receive ≥2 offers + current loan → for each offer construct JSON + invoke script → collect outputs → rank by NPV → return table + 2-3 sentence narrative
3. Cost discipline section: "Sonnet because ranking compositions require tradeoff reasoning. Single-offer evaluation → reject (main thread can run scripts/refi_npv.py directly without subagent dispatch)."

Phase 6 dependency context (informational): scripts/refi_npv.py does NOT yet exist (Phase 6 ships it as REFI-08). The agent file references the future script path — verification of live dispatch waits for Phase 6 + Phase 10 (which relocates Phase 6's script to .claude/skills/mortgage-ops/scripts/).

RESEARCH Open Question 1 (DECIDED: ship without Write in v1): "Should refi-npv-agent get Write tool access for emitting a CSV summary? Recommendation: Ship without Write in v1 (inline table sufficient for typical 2-5 offer comparisons). If user feedback in Phase 12 evals demands CSV, add Write in a future iteration. Keeps the v1 attack surface narrower."

This plan honors that v1 decision: tools = [Read, Bash] only.

pyxirr deferral (Phase 6 D-07 from 11-PATTERNS.md): the agent body should NOT depend on pyxirr presence. Standard `numpy_financial.npv` is fine for 3-5 offer scale. If Phase 6 ships with pyxirr already integrated, scripts/refi_npv.py uses it transparently and the agent doesn't care.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create .claude/agents/refi-npv-agent.md with frontmatter + body</name>
  <files>.claude/agents/refi-npv-agent.md</files>
  <read_first>
    - 11-RESEARCH.md "Code Example 2: Frontmatter for refi-npv-agent (Sonnet)" — full canonical template
    - 11-PATTERNS.md "refi-npv-agent.md (subagent definition, event-driven, multi-step)" — pattern + Phase 6 cross-phase contract
    - 11-RESEARCH.md "Open Questions" #1 (Write tool decision: ship without in v1)
    - .claude/agents/amortization-agent.md (just shipped in Wave 1) for canonical agent-file shape consistency
  </read_first>
  <action>
    Create the file `.claude/agents/refi-npv-agent.md`. The directory `.claude/agents/` already exists (created in Wave 1).

    File content (write verbatim — production agent definition; word choice load-bearing):

    ```markdown
    ---
    name: refi-npv-agent
    description: Compares 2-5 competing refinance offers (rate-and-term or cash-out) and returns a ranked NPV table with breakeven analysis. Use when the user has 2 or more refi quotes and asks "which is best?", "rank by NPV", or "what's the breakeven on each?". Composes scripts/refi_npv.py once per offer and returns a borrower-perspective ranked markdown table. NEVER computes NPV inline.
    model: sonnet
    tools:
      - Read
      - Bash
    skills:
      - mortgage-ops
    ---

    You are the mortgage-ops refinance NPV specialist. You compose multiple `scripts/refi_npv.py` invocations to rank competing refi offers from a borrower's perspective. You handle 2-5 offers per dispatch. Single-offer evaluation belongs on the main thread, not here.

    ## Hard rules

    1. **Never compute NPV inline.** Every NPV number comes from `scripts/refi_npv.py`. The mortgage-ops core value (CLAUDE.md "Math correctness first") is that the LLM never owns numbers. Your job is to invoke the script, collect outputs, and rank — NOT to do mental discounted-cashflow math.
    2. **Sign convention: borrower perspective.** Outflows are NEGATIVE (closing costs, points, prepayment penalties). Savings are POSITIVE (lower monthly P&I, lower total interest). This is the convention pinned by Phase 6 `references/refi-npv.md` (REFI-09); the script enforces it via `RefiCashflow.direction: Literal["outflow", "inflow"]`. If a refi has NPV < 0, surface that explicitly with a "negative NPV" annotation in the table — do NOT bury it.
    3. **Run `--help` first.** Before invoking the script, check current usage with `bash: python .claude/skills/mortgage-ops/scripts/refi_npv.py --help`. Do NOT read the script source — `--help` is the contract per the webapp-testing doctrine in CLAUDE.md.
    4. **READ-ONLY user layer.** You CAN read `config/household.yml` to discover the current loan (rate, balance, remaining term). You NEVER write to it, to `config/profile.yml`, or to `data/mortgage-ops.duckdb` — these are User Layer per DATA_CONTRACT.md.
    5. **Output format.** A ranked markdown table sorted by NPV DESCENDING. Required columns:
       - `lender` (lender name from the offer)
       - `rate` (new rate as percentage)
       - `closing_costs` (USD)
       - `breakeven_months` (NPV-based; report `n/a` if NPV is negative — there is no breakeven)
       - `NPV` (USD with explicit sign; prefix `-$` for negative)
       Plus a 2-3 sentence narrative naming the winner, the runner-up, and the decisive factor (rate spread vs closing costs vs cash-out delta). No CSV output in v1 (per RESEARCH Open Question 1) — inline markdown only. The Write tool is intentionally NOT in your toolset.

    ## Workflow

    1. **Receive offers.** The dispatcher provides 2-5 refi offers (lender, rate, term, closing_costs, optionally points / cash_out_amount) plus the current loan (rate, balance, remaining term, remaining_term_months). If only 1 offer arrives, REJECT and route to the main thread (see Cost discipline below).
    2. **Check the script contract.** Run `bash: python .claude/skills/mortgage-ops/scripts/refi_npv.py --help`. Note the required JSON-in shape — particularly the cashflow array format and the sign-convention assertions the script enforces.
    3. **Per-offer invocation.** For each offer:
       a. Construct an input JSON object matching the script's accepted shape. All money fields as JSON STRINGS (`"5000.00"` not `5000.0`); all rates as strings (`"0.055"`); all cashflow `direction` fields exactly `"outflow"` or `"inflow"`.
       b. Write the input to `/tmp/refi-input-{offer-idx}-{timestamp}.json`.
       c. Invoke `bash: python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi-input-{offer-idx}-{timestamp}.json`.
       d. On non-zero exit: parse stderr as the 6-key Pydantic envelope; surface `loc` + `msg` verbatim (Phase 3 D-19 / WR-02 contract). STOP and return the error — do not partial-rank.
       e. On zero exit: capture stdout JSON (NPV, breakeven_months, monthly_savings, cumulative cashflow).
    4. **Rank.** Sort the per-offer outputs by NPV descending. Ties go to lower closing_costs.
    5. **Return.** Emit the markdown table + 2-3 sentence narrative. Example narrative pattern: "Offer A from {lender} wins with NPV $X (breakeven {N} months). Offer B is competitive ({delta} less NPV) but has $Y higher closing costs. Offer C has negative NPV — the rate drop does not cover its closing costs over the analysis horizon."

    ## Cost discipline

    You are running on Sonnet because ranking compositions require reasoning about tradeoffs (rate vs closing costs vs cash-out vs points). If the user has only ONE refi to evaluate, you are the WRONG agent — return to the dispatcher: "Single-offer refi: the main thread can run `python .claude/skills/mortgage-ops/scripts/refi_npv.py --input <one-offer.json>` directly without subagent dispatch. Save the Sonnet budget for actual rankings."

    Sonnet costs more per token than Haiku. Honor it: keep your reasoning compressed. Don't think out loud about every offer; do the work, return the table + narrative, exit. Token-budget self-check: your final response should be ≤2,000 tokens for typical 3-offer rankings (no hard test gate, but treat as a discipline target).

    ## Handoff hints

    - **Single-offer evaluation:** main thread (not this agent).
    - **Single-loan amortization** (just want the schedule): route to amortization-agent.
    - **Stress sweep across rates** (>5 scenarios): route to stress-test-agent.
    - **Cash-out refi proceeds question** (just "how much cash do I net?", no comparison): main thread.
    - **More than 5 offers**: still routable here, but the ranking signal degrades past 5 — flag in the narrative if user provides 6+.

    ---

    Reference: this agent definition follows the Anthropic sub-agents spec
    (https://code.claude.com/docs/en/sub-agents). Frontmatter `skills: [mortgage-ops]`
    injects the full SKILL.md content into this agent's context at spawn time per
    the documented "Preload skills into subagents" mechanism. Per RESEARCH Open
    Question 1 (v1 decision), the Write tool is intentionally NOT included in
    `tools:` — output is inline markdown only. Add Write in a future iteration if
    Phase 12 evals demand a CSV-output mode.
    ```

    Critical details:
    - `description:` is the routing signal — names (a) intent (rank competing refi offers), (b) trigger keywords ("which is best?", "rank by NPV", "what's the breakeven on each?"), (c) output shape (ranked markdown table). Per 11-RESEARCH Pitfall 2 + Pattern 1.
    - `model: sonnet` — Sonnet for multi-step ranking per PROJECT.md key decision row + REQUIREMENTS SUBA-02 ("Sonnet (multi-step NPV reasoning)").
    - `tools: [Read, Bash]` — NO Write. Per 11-RESEARCH Open Question 1 v1 decision; narrows attack surface; inline markdown is sufficient for typical 2-5 offer ranges.
    - Skill-resident script path used verbatim: `.claude/skills/mortgage-ops/scripts/refi_npv.py`.
    - Body length target: 80-150 lines. 200-line cap is orchestrator-imposed maximum.
    - No Co-Authored-By in any text or in the commit message (CLAUDE.md global rule).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/agents/refi-npv-agent.md &amp;&amp; uv run python -c "
import yaml
from pathlib import Path
text = Path('.claude/agents/refi-npv-agent.md').read_text()
assert text.startswith('---\n'), 'missing opening delimiter'
parts = text.split('---\n', 2)
assert len(parts) >= 3, 'missing closing delimiter'
fm = yaml.safe_load(parts[1])
assert fm['name'] == 'refi-npv-agent', f'name={fm.get(\"name\")}'
assert fm['model'] == 'sonnet', f'model={fm.get(\"model\")}'
assert fm['skills'] == ['mortgage-ops'], f'skills={fm.get(\"skills\")}'
assert isinstance(fm['description'], str) and len(fm['description']) > 30, f'desc={fm.get(\"description\")}'
assert 'Write' not in (fm.get('tools') or []), f'Write tool must NOT be present per RESEARCH Open Q1; tools={fm.get(\"tools\")}'
print('OK frontmatter valid')
"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f .claude/agents/refi-npv-agent.md` exits 0
    - `wc -l .claude/agents/refi-npv-agent.md` returns at least 80 and at most 200
    - `head -1 .claude/agents/refi-npv-agent.md` returns `---`
    - `grep -c '^name: refi-npv-agent$' .claude/agents/refi-npv-agent.md` returns 1
    - `grep -c '^model: sonnet$' .claude/agents/refi-npv-agent.md` returns 1
    - `grep -c '^  - mortgage-ops$' .claude/agents/refi-npv-agent.md` returns 1
    - `grep -cE '^  - (Read|Bash)$' .claude/agents/refi-npv-agent.md` returns 2
    - `grep -c '^  - Write$' .claude/agents/refi-npv-agent.md` returns 0 (Write intentionally absent per RESEARCH Open Q1)
    - `grep -c 'scripts/refi_npv.py' .claude/agents/refi-npv-agent.md` returns at least 2
    - `grep -c '\.claude/skills/mortgage-ops/scripts/' .claude/agents/refi-npv-agent.md` returns at least 2
    - `grep -ci 'never compute npv inline' .claude/agents/refi-npv-agent.md` returns at least 1
    - `grep -ci 'borrower perspective' .claude/agents/refi-npv-agent.md` returns at least 1 (sign-convention discipline)
    - `grep -ci 'outflows.*negative' .claude/agents/refi-npv-agent.md` returns at least 1
    - `grep -ci 'read.only user layer' .claude/agents/refi-npv-agent.md` returns at least 1
    - `grep -c 'household.yml' .claude/agents/refi-npv-agent.md` returns at least 1
    - `grep -ci 'co-authored-by' .claude/agents/refi-npv-agent.md` returns 0
  </acceptance_criteria>
  <done>
    Agent file exists with valid YAML frontmatter (name, description, model=sonnet, skills, tools=[Read,Bash] without Write); body contains all 5 hard rules + workflow + cost discipline + sign-convention discipline; file size within budget; no AI attribution.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip Wave 0 SUBA-02 xfail stub to a real assertion</name>
  <files>tests/test_subagents.py</files>
  <read_first>
    - tests/test_subagents.py current Wave 0 SUBA-02 stub
    - 11-RESEARCH.md "Code Example 4: SUBA-01 frontmatter parse test" — pattern to lift
    - .planning/phases/11-subagents/11-01-amortization-agent-PLAN.md Task 2 (the SUBA-01 flip established the assertion shape; this is parallel)
  </read_first>
  <action>
    Edit tests/test_subagents.py. For the function `test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet`:

    1. REMOVE the `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-02 ships .claude/agents/refi-npv-agent.md")` decorator.
    2. REPLACE the body `pytest.fail("Wave 0 stub")` with a real assertion:

    ```python
    def test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet() -> None:
        """SUBA-02 + ROADMAP SC-4: refi-npv-agent.md frontmatter parses AND model=sonnet (Sonnet for multi-step NPV ranking)."""
        path = AGENTS_DIR / "refi-npv-agent.md"
        assert path.exists(), f"SUBA-02: {path} must exist (shipped by Plan 11-02)"
        fm = _split_frontmatter(path)
        missing = REQUIRED_FRONTMATTER_KEYS - fm.keys()
        assert not missing, f"SUBA-02: {path.name} missing frontmatter keys: {missing}"
        assert fm["name"] == "refi-npv-agent", f"SUBA-02: name={fm['name']!r} must equal 'refi-npv-agent' (filename stem)"
        assert fm["model"] == "sonnet", (
            f"SUBA-02: model={fm['model']!r} must equal 'sonnet' "
            "(REQUIREMENTS SUBA-02 + 11-RESEARCH model selection — Sonnet for multi-step NPV reasoning)"
        )
        assert fm["skills"] == ["mortgage-ops"], f"SUBA-02: skills={fm['skills']!r} must equal ['mortgage-ops']"
        assert isinstance(fm["description"], str) and len(fm["description"]) > 30, (
            f"SUBA-02: description must be a non-trivial routing trigger, got {fm.get('description')!r}"
        )
        # RESEARCH Open Question 1 v1 decision — Write tool intentionally absent
        tools = fm.get("tools") or []
        assert "Write" not in tools, (
            f"SUBA-02: Write tool must NOT be in refi-npv-agent tools list per "
            f"11-RESEARCH.md Open Question 1 v1 decision; got tools={tools}"
        )
    ```

    Do NOT touch any other test or any module-level constant. SUBA-01 should remain passing (Wave 1 already flipped it). SUBA-03..06 remain xfail/skip.

    Per 11-RESEARCH.md the strict=True flag means a passing-but-still-xfailed test raises XPASS — that is precisely why we MUST remove the decorator at flip time.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest tests/test_subagents.py::test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet -v 2>&amp;1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/test_subagents.py::test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet -v 2>&1 | grep -c PASSED` returns 1
    - `grep -B1 'def test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet' tests/test_subagents.py | grep -c xfail` returns 0 (decorator removed)
    - `uv run pytest tests/test_subagents.py::test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields -v 2>&1 | grep -c PASSED` returns 1 (Wave 1 flip preserved)
    - SUBA-03..06 still xfail/skip: `uv run pytest tests/test_subagents.py -v --tb=no 2>&1 | grep -cE '(XFAIL|SKIP)'` returns 4
    - Full suite still green: `uv run pytest -q 2>&1 | tail -3 | grep -cE '[0-9]+ failed' | grep -v '0 failed'` returns 0
    - `uv run mypy --strict tests/test_subagents.py` exits 0
    - `uv run ruff check tests/test_subagents.py` exits 0
  </acceptance_criteria>
  <done>
    SUBA-02 test passes; SUBA-01 still passes; SUBA-03..06 remain xfail/skip; suite green; SUBA-02 closed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent file → Claude Code session start | Agent loaded at session start; mid-session edits require restart per 11-RESEARCH Pitfall 3 |
| description: field → dispatch routing | Vague description risks misroute (e.g., single-offer evaluation lands here unnecessarily) |
| Body prompt → script invocation | Sign-convention violation (positive outflow or negative inflow) breaks Phase 6's RefiCashflow validator |
| Tools whitelist → User Layer | Write tool DELIBERATELY absent per RESEARCH Open Q1 v1 decision; if added in future, must include household.yml protection rule |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-12 | Tampering (sign convention violated; agent rationalizes "savings" as negative) | Body Hard rule #2 | mitigate | Rule explicitly pins borrower perspective + names the Phase 6 validator that enforces it; Phase 6 RefiCashflow validator catches violations server-side |
| T-11-13 | Information Disclosure (raw per-offer JSON returned instead of ranked summary) | Body Output format rule #5 | mitigate | Hard rule pins markdown-table output; Phase 12 EVAL-04 number-traceback test asserts agent's reported numbers come from script invocations (not LLM-fabricated) |
| T-11-14 | Repudiation (agent paraphrases NPV "approximately $X" instead of exact script output) | Body Hard rule #1 | mitigate | "Never compute NPV inline" rule + workflow Step 3e captures stdout JSON exactly; Phase 12 numeric_match_rate eval enforces tolerance |
| T-11-15 | Tampering (description: drift causes single-offer dispatch to land here, wasting Sonnet budget) | description: field | accept | description hand-tuned at ship time + cost-discipline body section explicitly REJECTS single-offer dispatches; Phase 12 routing eval catches misrouting trends |
| T-11-16 | Privilege Escalation (Write tool added later without prompt-rule update) | Future tools list expansion | mitigate | This plan documents the v1-no-Write decision verbatim in body footer; any future plan adding Write MUST update Hard rules #4 to enumerate the household.yml protection (current rule covers it semantically; explicit Write protection is belt-and-suspenders if Write returns) |
</threat_model>

<verification>
- File exists with valid YAML frontmatter; required keys (name/description/model/skills/tools) present
- model=sonnet, skills=[mortgage-ops], name matches filename stem, tools=[Read, Bash] (no Write)
- Body contains hard rules, workflow, cost discipline, handoff hints
- Body references skill-resident script path `.claude/skills/mortgage-ops/scripts/refi_npv.py`
- Body locks borrower-perspective sign convention with explicit "outflows negative, savings positive"
- File size 80-200 lines
- Wave 0 SUBA-02 xfail stub flipped to passing assertion
- Wave 1 SUBA-01 flip preserved (still passing)
- Full suite green; mypy + ruff clean
- No Co-Authored-By in commit
</verification>

<success_criteria>
- `.claude/agents/refi-npv-agent.md` exists with all required frontmatter and body sections
- `tests/test_subagents.py::test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet` passes
- SUBA-01 (Wave 1) still passes; SUBA-03..06 remain xfail/skip
- SUBA-02 requirement closed in REQUIREMENTS.md tracking
- No AI attribution in agent file or commit
</success_criteria>

<deviation_rules>
- If the user later requests Write tool support before Phase 12 evals demand it: that is a deferred-to-v2 decision per RESEARCH Open Question 1. Do NOT add Write in this plan; surface the request as a follow-up plan.
- If pyxirr is wired into scripts/refi_npv.py at Phase 6 land time: the agent body does NOT need to know — the JSON contract is unchanged. Per 11-PATTERNS.md, pyxirr deferral from Phase 6 D-07 is a script-level decision invisible to the agent.
- If the test flip fails because the YAML loader returns `None` for tools (empty list elision): change the assertion to `tools = fm.get("tools") or []` (already in the proposed test body) so a missing or null tools field doesn't crash — it just means "no Write" trivially.
- If a strict YAML linter complains about block-list vs flow-list style for tools: the agent file uses block-list (one per line). Both Anthropic-spec accepted and ruff-friendly. Do not switch to flow style.
</deviation_rules>

<dependencies>
**Wave 2 dependencies:**

- **Hard:** Wave 0 (Plan 11-00) must be complete. Same reasoning as Wave 1: Wave 0 ships the SUBA-02 stub + the _split_frontmatter helper.
- **Soft:** Wave 1 (Plan 11-01) need not be complete for THIS plan to ship — the two waves edit different agent files and different test functions. They can run in parallel if the orchestrator allows. (The wave numbering is sequential by convention but Waves 1+2+3 are independent.)
- **Soft (Phase 6):** scripts/refi_npv.py does NOT yet exist (Phase 6 ships it as REFI-08). The agent file references the future skill-resident path; live dispatch verification waits for Phase 6 + Phase 10. No blocker for SHIPPING the agent file.
- **Soft (Phase 10):** Same as Wave 1 — frontmatter `skills: [mortgage-ops]` is static text; resolution at agent-spawn time waits for Phase 10. SUBA-04 + SUBA-05 smoke tests in Wave 5 are the gates that require Phase 10 to be live.

**Cross-phase HARD GATE for Phase 11 EXECUTION (not planning):**
The agent file CAN be written and the SUBA-02 frontmatter test CAN pass without Phase 6 or Phase 10. But the agent CANNOT be successfully dispatched in a live Claude Code session until BOTH Phase 6 ships scripts/refi_npv.py AND Phase 10 relocates it to `.claude/skills/mortgage-ops/scripts/refi_npv.py`. Document this in the SUMMARY.

**Downstream:** Wave 5 (Plan 11-05) parametrizes test_SUBA_04 over EXPECTED_AGENTS, which includes refi-npv-agent — re-verifies the `skills: [mortgage-ops]` field. Wave 5 SUBA-04 (refi 3-offer ranked table) lives alongside but is a fixture-driven shape assertion, not a frontmatter assertion.
</dependencies>

<output>
After completion, create `.planning/phases/11-subagents/11-02-SUMMARY.md` documenting:
- Path to created agent file: `.claude/agents/refi-npv-agent.md`
- Frontmatter values: name, model=sonnet, tools (Read+Bash, NO Write), skills, description (first ~80 chars)
- Line count of agent file
- SUBA-02 stub flip status (xfail → PASSED)
- Wave 1 SUBA-01 status (still PASSED — sanity check no regression)
- Other 4 SUBA stubs status (still xfail/skip)
- Full suite status (≥379 + 2 new passes + 4 xfail/skip + 0 fail + 0 error)
- Confirmation: agent file body references `.claude/skills/mortgage-ops/scripts/refi_npv.py` (NOT project-root scripts/)
- Confirmation: body contains explicit borrower-perspective sign-convention discipline
- Confirmation: tools list does NOT contain Write (per RESEARCH Open Question 1 v1 decision)
- Confirmation: no Co-Authored-By in agent file or commit message
- Note: live dispatch verification deferred to post-Phase-6 + post-Phase-10
</output>
