---
phase: 11
plan: 03
type: execute
wave: 3
depends_on:
  - "11-00"
files_modified:
  - .claude/agents/stress-test-agent.md
autonomous: true
requirements:
  - SUBA-03
tags:
  - phase-11
  - subagents
  - stress-test-agent
  - haiku
  - suba-03
must_haves:
  truths:
    - ".claude/agents/stress-test-agent.md exists at repo root with valid YAML frontmatter"
    - "Frontmatter contains exactly: name=stress-test-agent, model=haiku, skills=[mortgage-ops], description (>30 chars, starts with 'Use proactively for stress sweeps with >5 scenarios'), tools (Read+Bash+Write — Write is needed for the optional CSV escape hatch per RESEARCH Code Example 3 line 6)"
    - "Body section instructs Claude to NEVER recompute numbers (must consume Phase 8 scripts/stress_test.py output verbatim — Phase 8 has done the math)"
    - "Body section pins the input contract: top-of-JSON scenario-summary table per Phase 8 contract (08-PATTERNS.md:11,27,261,290)"
    - "Body section enforces ≤1,000-token output budget with explicit self-check guidance"
    - "Body section enforces 'always cite the script invocation' discipline (Phase 12 EVAL-04 traceability)"
    - "Body section enforces READ-ONLY user layer (household.yml/profile.yml/*.duckdb never written) per DATA_CONTRACT.md"
    - "File size ≤200 lines (per orchestrator constraint)"
    - "Wave 0 stub test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku flips from xfail to passing"
  artifacts:
    - path: ".claude/agents/stress-test-agent.md"
      provides: "Phase 11 stress-test subagent definition (Haiku, single-shot summarization, consumes Phase 8 stress_test.py JSON, ≤1k token output)"
      min_lines: 80
      contains: "name: stress-test-agent"
  key_links:
    - from: ".claude/agents/stress-test-agent.md frontmatter skills field"
      to: ".claude/skills/mortgage-ops/SKILL.md"
      via: "Anthropic skills:[name] injection at agent spawn time"
      pattern: "skills:"
    - from: ".claude/agents/stress-test-agent.md body"
      to: ".claude/skills/mortgage-ops/scripts/stress_test.py"
      via: "bash invocation per --help-first doctrine; called ONCE (script handles full grid internally per Phase 8 design)"
      pattern: "scripts/stress_test.py"
    - from: ".claude/agents/stress-test-agent.md body 'top-of-JSON summary table' instruction"
      to: ".planning/phases/08-stress-points/08-PATTERNS.md:11,27,261,290 + Phase 8 references/stress-tests.md"
      via: "documented Phase 8 → Phase 11 contract: scenario-summary table at top of JSON, designed FOR this consumer"
      pattern: "scenario.summary"
    - from: "tests/test_subagents.py test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku"
      to: ".claude/agents/stress-test-agent.md"
      via: "_split_frontmatter helper from Wave 0; assertion fm['model'] == 'haiku'"
      pattern: "model: haiku"
---

<objective>
Ship `.claude/agents/stress-test-agent.md` — the third and final Phase 11 subagent definition. **Haiku** model (resolves the SUBA-03 model-discrepancy surfaced in 11-PATTERNS.md Critical Issue #1a item 2: REQUIREMENTS.md SUBA-03 says "Haiku" but the orchestrator-prompt-era scratch said "TBD"; this plan locks Haiku per the original requirement and per RESEARCH Architectural Responsibility Map). Closes SUBA-03.

Purpose: SUBA-03 is the linchpin of SC-3 (the 1,000-token budget gate) and SC-2 (the >5-scenario routing rule wired in Plan 11-04). It runs on Haiku because the workload is "consume the top-of-JSON summary table that Phase 8 already computed and compress it to ≤1,000 tokens" — that is summarization, not multi-step reasoning. Per 11-RESEARCH.md "Standard Stack" and Augment Code 2026 routing guide ("Haiku for fast summarization, table compression"), Haiku is the right tier; Sonnet would be wasted on reformatting work the upstream script already did. The agent's hard rule is: do NOT recompute numbers, do NOT return raw JSON, ALWAYS cite the bash invocation that produced the numbers.

Output: One agent file (~80-150 lines, capped at 200). Body mirrors the amortization-agent and refi-npv-agent template structure (frontmatter → hard rules → workflow → cost discipline → handoff hints) with stress-specific content. Wave 0 SUBA-03 xfail flips to passing.
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
@.planning/phases/11-subagents/11-02-refi-npv-agent-PLAN.md
@.planning/phases/08-stress-points/08-PATTERNS.md

<interfaces>
Per Anthropic sub-agents spec (https://code.claude.com/docs/en/sub-agents) — frontmatter shape (Haiku variant; Write tool included for the optional CSV escape hatch):

```yaml
---
name: stress-test-agent               # MUST match filename stem
description: <starts with "Use proactively for stress sweeps with >5 scenarios"; per D-04>
model: haiku                          # short alias per 11-PATTERNS.md CRITICAL #1a; LOCKED via D-01 (resolves PATTERNS issue #1a item 2)
skills:
  - mortgage-ops
tools:
  - Read
  - Bash
  - Write
---
```

Per 11-RESEARCH.md Code Example 3 (canonical body template) and 11-PATTERNS.md "stress-test-agent" pattern assignments + cross-phase contract source:

**Phase 8 → Phase 11 input contract (LOCKED via D-02):**

Phase 8's `scripts/stress_test.py` JSON output is designed FOR this subagent to consume. The exact contract is documented in:
- `.planning/phases/08-stress-points/08-PATTERNS.md:11` ("scenario-summary table at the top of JSON for SC-5 subagent consumption")
- `.planning/phases/08-stress-points/08-PATTERNS.md:27` ("subagent consumption contract for Phase 11")
- `.planning/phases/08-stress-points/08-PATTERNS.md:261` ("top-table-summary contract for SC-5")
- `.planning/phases/08-stress-points/08-PATTERNS.md:290` ("Top-of-JSON scenario-summary table + < 100KB total")

The agent reads ONLY the top-of-JSON summary table for the narrative + max-3 highlight rows. The full per-scenario detail array stays in the agent's context but is NEVER returned to the main thread (that defeats context isolation, per RESEARCH Pitfall 5).

**Body MUST include:**

1. Hard rules section (numbered 1..6):
   - Never recompute numbers (Phase 8 has done the math; you summarize)
   - Never return raw JSON (return ONLY the summary; if your output is >1,000 tokens, you have failed the task)
   - Run `--help` first; do not read script source (per CLAUDE.md doctrine)
   - READ-ONLY user layer (CAN read config/household.yml; NEVER writes user-layer files)
   - Output format: top-of-JSON summary table verbatim (the columns Phase 8 emits) + 2-3 sentence narrative + ≤3 highlight rows; cite the exact bash invocation
   - Always cite the script invocation (per Phase 12 EVAL-04 number-traceback discipline; the line `Computed by: bash python .claude/skills/mortgage-ops/scripts/stress_test.py --input <path>` MUST appear at the bottom of every response)

2. Workflow section (numbered 1..6): receive sweep request → check --help → construct ONE input JSON for the full grid → invoke `scripts/stress_test.py --input` ONCE → read top-of-JSON summary table → compose summary table verbatim + narrative + ≤3 highlight rows + invocation cite → return

3. Token budget section: explicit ≤1,000-token target; self-check guidance ("approximate 4 chars/token; if your draft exceeds ~4,000 chars, drop a highlight row or shorten the narrative; SC-3 enforces externally via anthropic.count_tokens against a recorded transcript fixture")

4. CSV escape hatch (per RESEARCH Code Example 3 lines 365-368): if user explicitly requests "give me the full sweep", write the JSON detail to `reports/{###}-stress-{YYYY-MM-DD}.csv` via the Write tool and return the PATH (not the content). This is why `Write` is in the tools list.

5. Cost discipline section: "Haiku because compress-this-table is summarization, not reasoning. Sweeps with ≤5 scenarios → reject (main thread can run scripts/stress_test.py inline; the dispatch overhead isn't worth it; see SUBA-05 routing in Plan 11-04)."

**Phase 8 + Phase 10 dependency context (informational):** scripts/stress_test.py does NOT yet exist (Phase 8 ships it as STRS-04). Phase 10 then relocates it to `.claude/skills/mortgage-ops/scripts/stress_test.py`. The agent file references the future skill-resident path; verification of live dispatch waits for Phase 8 + Phase 10. SHIPPING this agent file does NOT block on Phase 8 or 10 — the YAML frontmatter is static text and the body is a system prompt; the SUBA-03 frontmatter test is filesystem-only.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create .claude/agents/stress-test-agent.md with frontmatter + body</name>
  <files>.claude/agents/stress-test-agent.md</files>
  <read_first>
    - 11-RESEARCH.md "Code Example 3: Frontmatter for stress-test-agent (Haiku)" — full canonical template
    - 11-PATTERNS.md "stress-test-agent.md (subagent definition, event-driven, summarization)" — pattern + Phase 8 cross-phase contract
    - 11-PATTERNS.md CRITICAL ISSUE #1a item 2 (the SUBA-03 model-discrepancy that this plan resolves via LOCKED DECISION D-01)
    - 11-RESEARCH.md Pitfall 5 ("Subagent emits raw JSON instead of summary") — the failure mode this agent's hard rule prevents
    - .planning/phases/08-stress-points/08-PATTERNS.md:11,27,261,290 — the Phase 8 → Phase 11 input contract
    - .claude/agents/amortization-agent.md (Wave 1) and .claude/agents/refi-npv-agent.md (Wave 2) for canonical agent-file shape consistency
  </read_first>
  <action>
    Create the file `.claude/agents/stress-test-agent.md`. The directory `.claude/agents/` already exists (created in Wave 1).

    File content (write verbatim — production agent definition; word choice load-bearing for routing accuracy and SC-3 token-budget compliance):

    ```markdown
    ---
    name: stress-test-agent
    description: Use proactively for stress sweeps with >5 scenarios (rate-shock, income-shock, ARM-reset path). Dispatches scripts/stress_test.py once with the full parameter grid, then summarizes the top-of-JSON scenario-summary table to ≤1,000 tokens (table verbatim + 2-3 sentence narrative + max 3 highlight rows). NEVER returns raw per-scenario JSON to main context; NEVER recomputes numbers (Phase 8 owns the math).
    model: haiku
    tools:
      - Read
      - Bash
      - Write
    skills:
      - mortgage-ops
    ---

    You are the mortgage-ops stress-test specialist. You dispatch one parameter sweep, summarize Phase 8's pre-computed scenario-summary table to ≤1,000 tokens, and return ONLY the summary to the main thread. Sweeps with 5 or fewer scenarios are rejected — they belong on the main thread (see Cost discipline).

    ## Hard rules

    1. **Never recompute numbers.** Phase 8's `scripts/stress_test.py` already computed every dollar figure, every DTI, every rate. Your job is to read its top-of-JSON `scenario_summary` table and present it. If you do mental math (e.g., "approximately $X,XXX"), you have violated the mortgage-ops core value (CLAUDE.md "Math correctness first"). Cite, don't compute.
    2. **Never return raw JSON.** The whole point of dispatching to you is context isolation. The full per-scenario JSON detail (50+ rows) stays in YOUR context; only the summary returns to the main thread. If your final response is >1,000 tokens, you have failed the task — re-summarize coarser.
    3. **Run `--help` first.** Before invoking the script, check current usage with `bash: python .claude/skills/mortgage-ops/scripts/stress_test.py --help`. Do NOT read the script source — `--help` is the contract per CLAUDE.md webapp-testing doctrine.
    4. **READ-ONLY user layer.** You CAN read `config/household.yml` to discover the current loan when the dispatcher hands you parameters. You NEVER write to it, to `config/profile.yml`, or to `data/mortgage-ops.duckdb` — these are User Layer per DATA_CONTRACT.md. The Write tool is in your toolset ONLY for the CSV escape hatch (see Workflow Step 6); never point Write at User-Layer paths.
    5. **Output format.** Three required sections, in this order:
       - **Summary table** (verbatim from the script's top-of-JSON `scenario_summary` field — DO NOT reorder columns, DO NOT round, DO NOT abbreviate the values).
       - **Narrative** (2-3 sentences naming: a) the worst-case scenario, b) which scenarios breach the configured affordability threshold (if applicable), c) the median outcome).
       - **Highlights** (≤3 rows pulled verbatim from the per-scenario detail — pick the worst, the median, and the best; never more than 3).
    6. **Always cite the script invocation.** The final line of every response MUST be: `Computed by: bash python .claude/skills/mortgage-ops/scripts/stress_test.py --input <tmpfile-path>`. Phase 12 EVAL-04 number-traceback regression test asserts this line is present and that every dollar figure in the summary appears in the script's stdout JSON.

    ## Workflow

    1. **Receive the sweep request.** The dispatcher provides `mode` (one of `rate-shock | income-shock | arm-reset`), the parameter grid, and the base loan + household. If `len(parameter_grid) <= 5`, REJECT (see Cost discipline).
    2. **Check the script contract.** Run `bash: python .claude/skills/mortgage-ops/scripts/stress_test.py --help`. Note the JSON-in shape — the discriminated-union `mode` field, the per-mode grid shape (rate_shock_bps array vs income_reduction_pct array vs index_path array), and the response envelope (top-of-JSON `scenario_summary` table + per-scenario `scenarios` array).
    3. **Construct ONE input JSON.** The script handles the full grid internally — you call it ONCE per dispatch, NOT once per scenario. All money fields as JSON STRINGS (`"5000.00"` not `5000.0`); all rates as strings (`"0.065"`); the grid as a JSON array of strings or numbers per `--help`. Write the input to `/tmp/stress-input-{timestamp}.json`.
    4. **Invoke the script.** `bash: python .claude/skills/mortgage-ops/scripts/stress_test.py --input /tmp/stress-input-{timestamp}.json`.
       - On non-zero exit: parse stderr as the 6-key Pydantic envelope; surface `loc` + `msg` verbatim (Phase 3 D-19 / WR-02 contract). STOP and return the error — do not partial-summarize.
       - On zero exit: capture stdout JSON. The full payload (potentially ~100KB for 50-scenario sweeps) stays in YOUR context.
    5. **Compose the summary.** Read ONLY the top-of-JSON `scenario_summary` table. Format it verbatim as a markdown table. Compose the 2-3 sentence narrative. Pick ≤3 highlight rows from the detail array (worst / median / best). Append the `Computed by:` cite.
    6. **CSV escape hatch (only if user explicitly asks for the full sweep).** If — and only if — the dispatcher's prompt contains "full sweep", "all scenarios", "give me the CSV", or equivalent: write the full per-scenario JSON detail to `reports/{NNN}-stress-{YYYY-MM-DD}.csv` via the Write tool (compute NNN by listing existing reports and incrementing). Return ONLY the path string — the CSV content NEVER goes into your response. Include the `Computed by:` cite as usual.

    ## Token budget

    Your output target is **≤1,000 tokens** to the main context. SC-3 enforces this externally via `anthropic.Anthropic().messages.count_tokens(model="claude-haiku-4-5", messages=[{"role": "assistant", "content": <your-output>}])` against a recorded transcript fixture (50-scenario rate-shock sweep). Self-check: 4 chars/token is a workable approximation; if your draft exceeds ~4,000 characters, drop a highlight row or shorten the narrative. Do NOT pad with restating the user's question — straight to the table.

    ## Cost discipline

    You are running on Haiku because this work is one shell-out + one summarization of a pre-computed table. The reasoning load is "compress this table to its essential shape" — Haiku is fine for that, and Sonnet would be wasted (Phase 8 has already done all the multi-step math). If a request would arrive with **5 or fewer scenarios**, you are the WRONG agent — return: "Sweep size {N} ≤ 5: the main thread can run `python .claude/skills/mortgage-ops/scripts/stress_test.py --input <one-grid.json>` directly without subagent dispatch. The output (~5 rows × ~100 tokens = ~500 tokens) fits comfortably in main context. See modes/stress.md SUBA-05 routing rule." (The >5 routing rule is Plan 11-04's responsibility to wire into modes/stress.md.)

    ## Handoff hints

    - **Single-loan amortization** (no sweep at all): route to amortization-agent.
    - **Multi-offer refi ranking** (NPV across 2-5 offers): route to refi-npv-agent.
    - **Sweep with ≤5 scenarios:** main thread (not this agent).
    - **Single what-if** (one scenario): main thread.
    - **Stress sweep across rates with >5 scenarios:** YOU. This is your dispatch surface.

    ---

    Reference: this agent definition follows the Anthropic sub-agents spec
    (https://code.claude.com/docs/en/sub-agents). Frontmatter `skills: [mortgage-ops]`
    injects the full SKILL.md content into this agent's context at spawn time per
    the documented "Preload skills into subagents" mechanism. The Phase 8 → Phase 11
    input contract (top-of-JSON scenario_summary table + ≤100KB total payload) is
    documented in `.planning/phases/08-stress-points/08-PATTERNS.md:11,27,261,290`
    and in Phase 8's `references/stress-tests.md`. The model selection (Haiku) is
    locked by Plan 11-03 LOCKED DECISION D-01, resolving the SUBA-03 model-
    discrepancy surfaced in `.planning/phases/11-subagents/11-PATTERNS.md` Critical
    Issue #1a item 2.
    ```

    Critical details:
    - `description:` is the routing signal — starts literally with "Use proactively for stress sweeps with >5 scenarios" per D-04 (matches Anthropic's "Use proactively for X" recommended prefix for proactive-dispatch agents). Names (a) intent (parameter-grid stress sweeps), (b) trigger threshold (>5 scenarios), (c) output shape (≤1,000-token summary), (d) hard prohibitions (no raw JSON, no recomputation).
    - `model: haiku` — Haiku for summarization per PROJECT.md key decision row + REQUIREMENTS SUBA-03 + LOCKED DECISION D-01 (resolves the discrepancy noted in 11-PATTERNS.md Critical Issue #1a item 2). Rationale: Phase 8 owns the math; this agent's only reasoning load is "which 3 rows are most informative" — Haiku-tier work.
    - `tools: [Read, Bash, Write]` — Write is included ONLY for the CSV escape hatch (Hard rule #5 + Workflow Step 6). Per RESEARCH Code Example 3 line 6 ("CSV escape hatch"). The hard rule + workflow scope Write to the System Layer (`reports/`), never to User Layer (household.yml etc.).
    - Skill-resident script path used verbatim: `.claude/skills/mortgage-ops/scripts/stress_test.py` (NOT project-root `scripts/stress_test.py` — Phase 10 relocates per CLAUDE.md decision #8 + Phase 3 D-17).
    - Body length target: 80-150 lines. 200-line cap is orchestrator-imposed maximum.
    - No Co-Authored-By in any text or in the commit message (CLAUDE.md global rule).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/agents/stress-test-agent.md &amp;&amp; uv run python -c "
import yaml
from pathlib import Path
text = Path('.claude/agents/stress-test-agent.md').read_text()
assert text.startswith('---\n'), 'missing opening delimiter'
parts = text.split('---\n', 2)
assert len(parts) >= 3, 'missing closing delimiter'
fm = yaml.safe_load(parts[1])
assert fm['name'] == 'stress-test-agent', f'name={fm.get(\"name\")}'
assert fm['model'] == 'haiku', f'model={fm.get(\"model\")} — must be haiku per Plan 11-03 D-01'
assert fm['skills'] == ['mortgage-ops'], f'skills={fm.get(\"skills\")}'
assert isinstance(fm['description'], str) and len(fm['description']) > 30, f'desc={fm.get(\"description\")}'
assert fm['description'].lower().startswith('use proactively for stress sweeps with >5 scenarios'), f'desc must start with the D-04 trigger phrase; got: {fm[\"description\"][:80]}'
tools = fm.get('tools') or []
assert 'Bash' in tools and 'Read' in tools and 'Write' in tools, f'tools must include Read+Bash+Write (Write needed for CSV escape hatch); got tools={tools}'
print('OK frontmatter valid')
" &amp;&amp; test $(wc -l &lt; .claude/agents/stress-test-agent.md) -le 200 &amp;&amp; echo "OK ≤200 lines"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f .claude/agents/stress-test-agent.md` exits 0
    - `wc -l .claude/agents/stress-test-agent.md` returns at least 80 and at most 200
    - `head -1 .claude/agents/stress-test-agent.md` returns `---`
    - `grep -c '^name: stress-test-agent$' .claude/agents/stress-test-agent.md` returns 1
    - `grep -c '^model: haiku$' .claude/agents/stress-test-agent.md` returns 1
    - `grep -c '^  - mortgage-ops$' .claude/agents/stress-test-agent.md` returns 1
    - `grep -cE '^  - (Read|Bash|Write)$' .claude/agents/stress-test-agent.md` returns 3
    - `grep -ci 'use proactively for stress sweeps with >5 scenarios' .claude/agents/stress-test-agent.md` returns at least 1 (D-04 trigger phrase)
    - `grep -c 'scripts/stress_test.py' .claude/agents/stress-test-agent.md` returns at least 2
    - `grep -c '\.claude/skills/mortgage-ops/scripts/' .claude/agents/stress-test-agent.md` returns at least 2
    - `grep -ci 'never recompute' .claude/agents/stress-test-agent.md` returns at least 1
    - `grep -ci 'never return raw json' .claude/agents/stress-test-agent.md` returns at least 1
    - `grep -ci '1,000.token' .claude/agents/stress-test-agent.md` returns at least 1 (D-03 budget)
    - `grep -ci 'computed by' .claude/agents/stress-test-agent.md` returns at least 1 (citation discipline)
    - `grep -ci 'scenario_summary' .claude/agents/stress-test-agent.md` returns at least 1 (Phase 8 contract field name per D-02)
    - `grep -ci 'read.only user layer' .claude/agents/stress-test-agent.md` returns at least 1
    - `grep -c 'household.yml' .claude/agents/stress-test-agent.md` returns at least 1
    - `grep -ci 'co-authored-by' .claude/agents/stress-test-agent.md` returns 0
  </acceptance_criteria>
  <done>
    Agent file exists with valid YAML frontmatter (name, description starting with "Use proactively for stress sweeps with >5 scenarios", model=haiku per D-01, skills=[mortgage-ops], tools=[Read,Bash,Write]); body contains all 6 hard rules + workflow + token budget + cost discipline + handoff hints + CSV escape hatch; references Phase 8 `scenario_summary` field by name; pins ≤1,000-token budget; pins citation discipline; file size within budget; no AI attribution.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip Wave 0 SUBA-03 xfail stub to a real assertion</name>
  <files>tests/test_subagents.py</files>
  <read_first>
    - tests/test_subagents.py current Wave 0 SUBA-03 stub
    - 11-RESEARCH.md "Code Example 4: SUBA-01 frontmatter parse test" — pattern to lift
    - .planning/phases/11-subagents/11-01-amortization-agent-PLAN.md Task 2 (the SUBA-01 flip — same shape)
    - .planning/phases/11-subagents/11-02-refi-npv-agent-PLAN.md Task 2 (the SUBA-02 flip — same shape)
  </read_first>
  <action>
    Edit tests/test_subagents.py. For the function `test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku`:

    1. REMOVE the `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-03 ships .claude/agents/stress-test-agent.md")` decorator.
    2. REPLACE the body `pytest.fail("Wave 0 stub")` with a real assertion:

    ```python
    def test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku() -> None:
        """SUBA-03 + ROADMAP SC-1 + SC-3 setup: stress-test-agent.md frontmatter parses AND model=haiku.

        Model selection LOCKED via Plan 11-03 D-01: Haiku, resolving the SUBA-03 model-
        discrepancy surfaced in 11-PATTERNS.md Critical Issue #1a item 2 (REQUIREMENTS.md
        says Haiku; orchestrator scratch said TBD; this plan locks Haiku per the original
        requirement and per RESEARCH Architectural Responsibility Map — Phase 8 owns the
        math, this agent only summarizes).
        """
        path = AGENTS_DIR / "stress-test-agent.md"
        assert path.exists(), f"SUBA-03: {path} must exist (shipped by Plan 11-03)"
        fm = _split_frontmatter(path)
        missing = REQUIRED_FRONTMATTER_KEYS - fm.keys()
        assert not missing, f"SUBA-03: {path.name} missing frontmatter keys: {missing}"
        assert fm["name"] == "stress-test-agent", f"SUBA-03: name={fm['name']!r} must equal 'stress-test-agent' (filename stem)"
        assert fm["model"] == "haiku", (
            f"SUBA-03: model={fm['model']!r} must equal 'haiku' "
            "(REQUIREMENTS SUBA-03 + Plan 11-03 LOCKED DECISION D-01 — Haiku for summarization; "
            "Phase 8 owns the math, no multi-step reasoning required)"
        )
        assert fm["skills"] == ["mortgage-ops"], f"SUBA-03: skills={fm['skills']!r} must equal ['mortgage-ops']"
        assert isinstance(fm["description"], str) and len(fm["description"]) > 30, (
            f"SUBA-03: description must be a non-trivial routing trigger, got {fm.get('description')!r}"
        )
        # D-04 — description MUST start with the proactive-dispatch trigger phrase so
        # Claude Code's auto-delegation routes >5-scenario sweeps here without ambiguity.
        assert fm["description"].lower().startswith("use proactively for stress sweeps with >5 scenarios"), (
            f"SUBA-03: description must start with 'Use proactively for stress sweeps with >5 scenarios' "
            f"per Plan 11-03 D-04; got: {fm['description'][:80]!r}"
        )
        # Write tool MUST be present — needed for the CSV escape hatch (Hard rule #5 +
        # Workflow Step 6 in the agent body); Read+Bash+Write per RESEARCH Code Example 3.
        tools = fm.get("tools") or []
        for required in ("Read", "Bash", "Write"):
            assert required in tools, (
                f"SUBA-03: tools must include {required!r} (Write needed for CSV escape hatch); got tools={tools}"
            )
    ```

    Do NOT touch any other test or any module-level constant. SUBA-01 and SUBA-02 should remain passing (Waves 1 and 2 already flipped them). SUBA-04..06 remain xfail/skip.

    Per 11-RESEARCH.md the strict=True flag means a passing-but-still-xfailed test raises XPASS — that is precisely why we MUST remove the decorator at flip time.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest tests/test_subagents.py::test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku -v 2>&amp;1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/test_subagents.py::test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku -v 2>&1 | grep -c PASSED` returns 1
    - `grep -B1 'def test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku' tests/test_subagents.py | grep -c xfail` returns 0 (decorator removed)
    - `uv run pytest tests/test_subagents.py::test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields -v 2>&1 | grep -c PASSED` returns 1 (Wave 1 flip preserved)
    - `uv run pytest tests/test_subagents.py::test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet -v 2>&1 | grep -c PASSED` returns 1 (Wave 2 flip preserved)
    - SUBA-04..06 still xfail/skip: `uv run pytest tests/test_subagents.py -v --tb=no 2>&1 | grep -cE '(XFAIL|SKIP)'` returns 3
    - Full suite still green: `uv run pytest -q 2>&1 | tail -3 | grep -cE '[0-9]+ failed' | grep -v '0 failed'` returns 0
    - `uv run mypy --strict tests/test_subagents.py` exits 0
    - `uv run ruff check tests/test_subagents.py` exits 0
  </acceptance_criteria>
  <done>
    SUBA-03 test passes; SUBA-01 and SUBA-02 still pass; SUBA-04..06 remain xfail/skip; suite green; SUBA-03 closed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent file → Claude Code session start | Agent loaded at session start; mid-session edits require restart per 11-RESEARCH Pitfall 3 |
| description: field → dispatch routing | Mismatched threshold phrasing risks misroute (≤5-scenario sweeps land here, wasting context isolation) |
| Body prompt → output token budget | Agent could ignore the ≤1,000-token rule and dump raw JSON (RESEARCH Pitfall 5 — the canonical Phase 11 failure mode) |
| Tools whitelist → User Layer | Write tool present (for CSV escape hatch) → MUST be scoped to `reports/` only, never `config/household.yml` etc. |
| Body prompt → Phase 8 numeric output | Agent could rationalize / round / restate Phase 8's numbers, breaking number-traceback (Phase 12 EVAL-04) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-17 | Information Disclosure (raw 50-scenario JSON returned, blowing past 1k token budget) | Body Hard rule #2 + Token budget section | mitigate | Hard rule #2 explicitly forbids returning raw JSON; Token budget section pins ≤1,000-token target with self-check guidance; SC-3 enforces externally via anthropic.count_tokens against transcript fixture (Plan 11-05 ships the test) |
| T-11-18 | Repudiation (agent paraphrases stress numbers as "approximately $X" instead of script output verbatim) | Body Hard rule #1 + Hard rule #5 (table verbatim) | mitigate | Hard rule #1 forbids inline computation; Hard rule #5 requires the table verbatim; Hard rule #6 + bottom-of-response cite enables Phase 12 EVAL-04 number-traceback regression; the cite line is regex-asserted by Plan 11-05 |
| T-11-19 | Tampering (agent invokes scripts/stress_test.py once per scenario instead of once per dispatch — Phase 8's grid handler is bypassed) | Body Workflow Step 3+4 | mitigate | Workflow Step 3 explicitly says "the script handles the full grid internally — you call it ONCE per dispatch, NOT once per scenario"; Phase 8's discriminated-union design (per 08-PATTERNS.md) makes this the natural CLI shape |
| T-11-20 | Privilege Escalation (Write tool, present for CSV escape hatch, gets pointed at config/household.yml or data/mortgage-ops.duckdb) | tools: [Read, Bash, Write] | mitigate | Hard rule #4 (READ-ONLY user layer) + Hard rule #4 explicit clarification that Write is "ONLY for the CSV escape hatch" + Workflow Step 6 scopes Write target to `reports/{NNN}-stress-{YYYY-MM-DD}.csv`; pre-commit hook is belt-and-suspenders defense |
| T-11-21 | Tampering (description: drift causes ≤5-scenario sweeps to land here, defeating the SUBA-05 routing rule) | description: field + Cost discipline section | mitigate | description explicitly says ">5 scenarios" (the literal SC-2 text); Cost discipline section REJECTS ≤5-scenario dispatches with an explicit message + reference to modes/stress.md SUBA-05 routing rule (Plan 11-04 wires the routing) |
| T-11-22 | Tampering (model selection drift — someone changes haiku → sonnet without re-evaluating cost discipline) | model: haiku frontmatter field | mitigate | Plan 11-03 LOCKED DECISION D-01 explicitly pins Haiku with rationale; the SUBA-03 frontmatter test (Task 2) asserts model == "haiku" and will fail if changed; PATTERNS Critical Issue #1a item 2 is documented for future-planner traceability |
</threat_model>

<verification>
- File exists with valid YAML frontmatter; required keys (name/description/model/skills/tools) present
- model=haiku per D-01, skills=[mortgage-ops], name matches filename stem, tools=[Read, Bash, Write]
- description starts with the D-04 trigger phrase ("Use proactively for stress sweeps with >5 scenarios")
- Body contains hard rules, workflow, token budget, cost discipline, handoff hints, CSV escape hatch
- Body references skill-resident script path `.claude/skills/mortgage-ops/scripts/stress_test.py`
- Body references Phase 8 `scenario_summary` field by name (D-02 input contract)
- Body pins ≤1,000-token output budget with self-check guidance (D-03)
- Body pins `Computed by:` citation discipline (Phase 12 EVAL-04 traceability)
- File size 80-200 lines
- Wave 0 SUBA-03 xfail stub flipped to passing assertion
- Wave 1 SUBA-01 and Wave 2 SUBA-02 flips preserved (still passing)
- Full suite green; mypy + ruff clean
- No Co-Authored-By in commit
</verification>

<success_criteria>
- `.claude/agents/stress-test-agent.md` exists with all required frontmatter and body sections
- `tests/test_subagents.py::test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku` passes
- SUBA-01 (Wave 1) and SUBA-02 (Wave 2) still pass; SUBA-04..06 remain xfail/skip
- SUBA-03 requirement closed in REQUIREMENTS.md tracking
- ROADMAP SC-1 (frontmatter parse for stress-test-agent.md) satisfied for this agent
- D-01 model-discrepancy from PATTERNS Critical Issue #1a item 2 resolved (Haiku locked)
- No AI attribution in agent file or commit
</success_criteria>

<locked_decisions>
- **D-01: model = haiku.** Resolves the SUBA-03 model-discrepancy surfaced in 11-PATTERNS.md Critical Issue #1a item 2. Rationale: Phase 8's `scripts/stress_test.py` does the math; this agent's only reasoning load is "compress the pre-computed summary table to ≤1,000 tokens" — that is summarization, not multi-step reasoning. Haiku is the right tier per Augment Code 2026 routing guide ("Haiku for fast summarization, table compression"). Sonnet would be wasted. If runtime evaluation in Phase 12 shows Haiku quality is poor for this workload, switching to Sonnet is a one-line frontmatter change with no other code or test changes required.
- **D-02: input contract = Phase 8 scripts/stress_test.py output schema.** Specifically: top-of-JSON `scenario_summary` table + per-scenario `scenarios` array. Documented in `.planning/phases/08-stress-points/08-PATTERNS.md:11,27,261,290` and Phase 8's `references/stress-tests.md`. The agent reads ONLY the summary table for the markdown output; the detail array stays in the agent's context but never returns to main.
- **D-03: ≤1,000 token output budget enforced via tokenizer harness.** SC-3 gate. Tokenizer = `anthropic.Anthropic().messages.count_tokens(model="claude-haiku-4-5", messages=[...])` per RESEARCH Code Example 5. Plan 11-05 ships the test against a recorded transcript fixture for a canonical 50-scenario rate-shock sweep. The agent body includes self-check guidance (4 chars/token approximation) but the SC-3 gate is the source of truth.
- **D-04: description copy starts with "Use proactively for stress sweeps with >5 scenarios".** This is the literal text Claude Code reads at dispatch time per the Anthropic auto-delegation mechanism (RESEARCH Pitfall 2 — vague descriptions cause routing collisions). The "Use proactively" prefix is Anthropic's recommended pattern for proactive-dispatch agents. The ">5 scenarios" suffix matches the literal SC-2 / SUBA-05 routing threshold (Plan 11-04 wires the corresponding rule into modes/stress.md).
</locked_decisions>

<deviation_rules>
- If runtime evaluation in Phase 12 shows Haiku summary quality is insufficient for 50-scenario sweeps: switching to Sonnet is a one-line frontmatter change. Surface as a separate plan (Phase 12 follow-up); do NOT make the change in this plan.
- If Phase 8's `scripts/stress_test.py` does NOT emit a top-of-JSON `scenario_summary` table at land time: this is a Phase 8 contract violation, NOT a Phase 11 problem. Escalate to Phase 8 to add the field per `.planning/phases/08-stress-points/08-PATTERNS.md:11` (Phase 8 already documented the contract; if missing at ship time, file as a Phase 8 gap).
- If the YAML loader returns `None` for tools (empty list elision): change the assertion to `tools = fm.get("tools") or []` (already in the proposed test body) so a missing or null tools field doesn't crash — it just means "Write tool absent" which the assertion will then catch with a clear error.
- If a strict YAML linter complains about block-list vs flow-list style for tools: the agent file uses block-list (one per line). Both Anthropic-spec accepted and ruff-friendly. Do not switch to flow style.
- If the user requests removing the CSV escape hatch (e.g., "we never want full sweep export"): drop Write from `tools:`, drop Hard rule #5 CSV mention, drop Workflow Step 6, and update the SUBA-03 test assertion to `assert "Write" not in tools`. Surface as a follow-up plan; do NOT make the change in this plan.
</deviation_rules>

<dependencies>
**Wave 3 dependencies:**

- **Hard:** Wave 0 (Plan 11-00) must be complete. Wave 0 ships the SUBA-03 stub + the `_split_frontmatter` helper + `REQUIRED_FRONTMATTER_KEYS` constant + `AGENTS_DIR` constant.
- **Soft:** Waves 1 (Plan 11-01) and 2 (Plan 11-02) need not be complete for THIS plan to ship — the three waves edit different agent files and different test functions. They can run in parallel if the orchestrator allows (Wave 1, 2, 3 are independent of each other; only Wave 0 is the shared dependency). The wave numbering is sequential by convention.
- **Soft (Phase 8):** scripts/stress_test.py does NOT yet exist (Phase 8 ships it as STRS-04). The agent file references the future skill-resident path; live dispatch verification waits for Phase 8 + Phase 10. No blocker for SHIPPING the agent file.
- **Soft (Phase 10):** Same as Waves 1+2 — frontmatter `skills: [mortgage-ops]` is static text; resolution at agent-spawn time waits for Phase 10. The SUBA-04 + SUBA-05 smoke tests in Wave 5 are the gates that require Phase 10 to be live.

**Cross-phase HARD GATE for Phase 11 EXECUTION (not planning):**
The agent file CAN be written and the SUBA-03 frontmatter test CAN pass without Phase 8 or Phase 10. But the agent CANNOT be successfully dispatched in a live Claude Code session until BOTH:
1. Phase 8 ships scripts/stress_test.py with the top-of-JSON `scenario_summary` field per 08-PATTERNS.md.
2. Phase 10 relocates it to `.claude/skills/mortgage-ops/scripts/stress_test.py` and ships SKILL.md + modes/stress.md (the latter is updated by Plan 11-04 to wire the >5 routing rule).

Document this in the SUMMARY.

**Downstream:**
- Wave 4 (Plan 11-04) wires the SUBA-05 routing rule into modes/stress.md, citing this agent by name.
- Wave 5 (Plan 11-05) parametrizes test_SUBA_04 over EXPECTED_AGENTS, which includes stress-test-agent — re-verifies the `skills: [mortgage-ops]` field. Wave 5 SUBA-06 (50-scenario summary <1k tokens) is the SC-3 gate; it consumes a recorded transcript fixture representing what THIS agent returns.
</dependencies>

<output>
After completion, create `.planning/phases/11-subagents/11-03-SUMMARY.md` documenting:
- Path to created agent file: `.claude/agents/stress-test-agent.md`
- Frontmatter values: name, model=haiku (per D-01, resolving PATTERNS Critical Issue #1a item 2), tools (Read+Bash+Write — Write for CSV escape hatch), skills, description (first ~80 chars confirming D-04 trigger phrase)
- Line count of agent file
- SUBA-03 stub flip status (xfail → PASSED)
- Wave 1 SUBA-01 and Wave 2 SUBA-02 status (still PASSED — sanity check no regression)
- Other 3 SUBA stubs status (still xfail/skip)
- Full suite status (≥379 + 3 new passes + 3 xfail/skip + 0 fail + 0 error)
- Confirmation: agent file body references `.claude/skills/mortgage-ops/scripts/stress_test.py` (NOT project-root scripts/)
- Confirmation: body references Phase 8 `scenario_summary` field by name (D-02 input contract)
- Confirmation: body pins ≤1,000-token budget (D-03) + `Computed by:` citation discipline (Phase 12 EVAL-04 traceability)
- Confirmation: body REJECTS ≤5-scenario dispatches with the SUBA-05 routing reference (Plan 11-04 will wire the rule)
- Confirmation: no Co-Authored-By in agent file or commit message
- Note: live dispatch verification deferred to post-Phase-8 + post-Phase-10
</output>
