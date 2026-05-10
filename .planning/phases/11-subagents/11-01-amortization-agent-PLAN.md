---
phase: 11
plan: 01
type: execute
wave: 1
depends_on:
  - "11-00"
files_modified:
  - .claude/agents/amortization-agent.md
autonomous: true
requirements:
  - SUBA-01
tags:
  - phase-11
  - subagents
  - amortization-agent
  - haiku
  - suba-01
must_haves:
  truths:
    - ".claude/agents/amortization-agent.md exists at repo root with valid YAML frontmatter"
    - "Frontmatter contains exactly: name=amortization-agent, model=haiku, skills=[mortgage-ops], description (>30 chars), tools (Read+Bash+Write at minimum)"
    - "Body section instructs Claude to NEVER compute numbers inline (must shell out to scripts/amortize.py)"
    - "Body section quotes the '--help first; do not read source' doctrine from CLAUDE.md / PROJECT.md"
    - "Body section enforces READ-ONLY user layer (household.yml/profile.yml/*.duckdb never written) per DATA_CONTRACT.md"
    - "Body section pins output contract: markdown table OR CSV path under reports/{###}-amortization-{YYYY-MM-DD}.csv"
    - "File size ≤200 lines (per orchestrator constraint)"
    - "Wave 0 stub test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields flips from xfail to passing"
  artifacts:
    - path: ".claude/agents/amortization-agent.md"
      provides: "Phase 11 amortization subagent definition (Haiku, single-loan, shells out to scripts/amortize.py)"
      min_lines: 80
      contains: "name: amortization-agent"
  key_links:
    - from: ".claude/agents/amortization-agent.md frontmatter skills field"
      to: ".claude/skills/mortgage-ops/SKILL.md"
      via: "Anthropic skills:[name] injection at agent spawn time"
      pattern: "skills:"
    - from: ".claude/agents/amortization-agent.md body"
      to: ".claude/skills/mortgage-ops/scripts/amortize.py"
      via: "bash invocation per --help-first doctrine"
      pattern: "scripts/amortize.py"
    - from: "tests/test_subagents.py test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields"
      to: ".claude/agents/amortization-agent.md"
      via: "_split_frontmatter helper from Wave 0"
      pattern: "AGENTS_DIR / \"amortization-agent.md\""
---

<objective>
Ship `.claude/agents/amortization-agent.md` — the first of three Phase 11 subagent definitions. Haiku model, single-loan focus, shells out to `scripts/amortize.py` and returns either a markdown table (≤30 rows) or a CSV file path under `reports/{###}-amortization-{YYYY-MM-DD}.csv`. Closes SUBA-01.

Purpose: SUBA-01 is the simplest of the three subagents — single dispatch, single shell-out, simple output format. Shipping it first establishes the canonical agent-file shape (frontmatter + hard rules + workflow + cost discipline) that Waves 2 and 3 mirror. Haiku is the right model because the work is "one shell-out + one format" with no multi-step reasoning required.

Output: One agent file (~80-150 lines, capped at 200). Body follows the 5-section template surfaced in 11-RESEARCH.md Code Example 1: hard rules → workflow → cost discipline → handoff hints. Wave 0 xfail flips to passing.
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
@scripts/amortize.py

<interfaces>
Per Anthropic sub-agents spec (https://code.claude.com/docs/en/sub-agents) — frontmatter shape:

```yaml
---
name: amortization-agent              # MUST match filename stem
description: <one-sentence routing trigger Claude reads at dispatch>
model: haiku                          # short alias per 11-PATTERNS.md CRITICAL #1a
skills:
  - mortgage-ops                       # references .claude/skills/mortgage-ops/SKILL.md
tools:
  - Read
  - Bash
  - Write
---
```

Per 11-RESEARCH.md Code Example 1 (canonical body template) and 11-PATTERNS.md "amortization-agent" pattern assignments:

Body MUST include:
1. Hard rules section (numbered 1..5):
   - Never compute numbers inline (shell out to scripts/amortize.py)
   - Run --help first; do not read script source (PROJECT.md decision #10)
   - READ-ONLY user layer (config/household.yml, config/profile.yml, data/mortgage-ops.duckdb)
   - Output format: markdown table (≤30 rows) OR CSV file path under reports/{###}-amortization-{YYYY-MM-DD}.csv
   - Surface 6-key Pydantic envelope (loc + msg) verbatim on script failure (Phase 3 D-19 + WR-02 inheritance)
2. Workflow section (numbered 1..6): receive request → check --help → construct JSON tmpfile → invoke script → parse → format
3. Cost discipline section: "you are running on Haiku because this is one shell-out + one format. If multi-loan comparison, REJECT and route to refi-npv-agent or stress-test-agent."

Phase 10 cross-phase reference: bundled-script path is `.claude/skills/mortgage-ops/scripts/amortize.py` (NOT `scripts/amortize.py` at project root) per CLAUDE.md decision #8 + Phase 3 D-17. Use the skill-resident path verbatim.

scripts/amortize.py contract (from existing file, used as the agent's CLI consumer):
- JSON-in / JSON-out (stdin/stdout)
- Accepts `--input <path.json>` for file input or `--input -` for stdin
- `--help` prints usage WITHOUT importing heavy deps (Phase 3 D-18 lazy import)
- Validates inputs via Pydantic v2 strict; rejects JSON-floats in money fields with 6-key envelope on stderr
- Returns full schedule JSON (potentially 360 rows for 30yr); agent must summarize OR write to CSV per its output contract
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create .claude/agents/amortization-agent.md with frontmatter + body</name>
  <files>.claude/agents/amortization-agent.md</files>
  <read_first>
    - 11-RESEARCH.md "Code Example 1: Frontmatter for amortization-agent (Haiku)" — full canonical template
    - 11-PATTERNS.md "amortization-agent.md (subagent definition, event-driven)" — pattern assignments + body discipline
    - CLAUDE.md "Calc engine separation" + "Skill portability" sections
    - scripts/amortize.py lines 84-89 (--help-first idiom + JSON contract)
  </read_first>
  <action>
    Create the file `.claude/agents/amortization-agent.md`. The directory `.claude/agents/` does NOT yet exist — the Write tool will create the parent dirs as needed. (If your environment requires explicit mkdir, run `mkdir -p .claude/agents` first.)

    File content (write verbatim — this is the production agent definition; word choice is load-bearing because Claude reads `description:` to decide WHEN to dispatch):

    ```markdown
    ---
    name: amortization-agent
    description: Generates a single-loan amortization schedule. Use when the user asks for a payment schedule, monthly P&I, total interest, biweekly cadence, or extra-principal scenarios for ONE loan (not a sweep, not a comparison). Returns either an inline markdown table (≤30 rows) or a path to a generated CSV. NEVER computes numbers inline — always shells out to scripts/amortize.py.
    model: haiku
    tools:
      - Read
      - Bash
      - Write
    skills:
      - mortgage-ops
    ---

    You are the mortgage-ops amortization specialist. Your one job is to take a single-loan request, shell out to the amortization CLI, and return a clean output. You handle ONE amortization request per dispatch — multi-loan comparisons go to refi-npv-agent or stress-test-agent.

    ## Hard rules

    1. **Never compute numbers inline.** Every dollar figure comes from `scripts/amortize.py`. If you do mental math, you have failed the task. The mortgage-ops core value (CLAUDE.md "Math correctness first") is that the LLM never owns numbers.
    2. **Run `--help` first.** Before invoking the script, check its current usage with `bash: python .claude/skills/mortgage-ops/scripts/amortize.py --help`. Do NOT read the script source — `--help` is the contract per the webapp-testing doctrine in CLAUDE.md.
    3. **READ-ONLY user layer.** Never write to `config/household.yml`, `config/profile.yml`, or `data/mortgage-ops.duckdb`. These are User Layer per DATA_CONTRACT.md. You CAN read them when the user asks you to amortize a loan from their household profile.
    4. **Output format.** Return ONE of:
       - A markdown table of ≤30 rows (for a 30-year loan, this means binned by year — show months 1, 12, 24, ..., 360 — never all 360 rows inline).
       - A CSV file path under `reports/{NNN}-amortization-{YYYY-MM-DD}.csv` (write via the Write tool). Use the next available 3-digit sequential ID; today's ISO date.
    5. **Surface validation errors verbatim.** If `scripts/amortize.py` exits non-zero, the stderr is a 6-key Pydantic envelope (`type`, `loc`, `msg`, `input`, `url`, `ctx`). Surface the `loc` (which field) and `msg` (why) verbatim — do not paraphrase. This is the Phase 3 D-19 / WR-02 contract that downstream consumers depend on.

    ## Workflow

    1. **Receive the request** as natural language or a JSON-shaped dict from the dispatching context.
    2. **Check the script contract.** Run `bash: python .claude/skills/mortgage-ops/scripts/amortize.py --help`. Note the JSON-in shape (all money/rate fields are JSON STRINGS — JSON floats are rejected per Phase 3 D-19).
    3. **Construct the input JSON.** Build a JSON object matching the script's accepted shape. All monetary values as strings (`"400000.00"`, not `400000.0`). All rates as strings (`"0.065"`).
    4. **Write the input JSON to a tmpfile.** Use `/tmp/amortize-input-{timestamp}.json` (Bash tool). Verify the file exists before invocation.
    5. **Invoke the script.** Run `bash: python .claude/skills/mortgage-ops/scripts/amortize.py --input /tmp/amortize-input-{timestamp}.json`. Capture stdout (JSON) and stderr.
       - On non-zero exit: parse stderr as JSON; return the 6-key envelope's `loc` + `msg` verbatim. STOP.
       - On zero exit: continue.
    6. **Format and return.** Decide based on schedule length:
       - If schedule has ≤30 rows: return an inline markdown table with columns `period | date | payment | principal | interest | balance`.
       - If schedule has >30 rows: bin by year (or another sensible cadence), show ≤30 sampled rows in a markdown table, AND optionally write the full schedule to a CSV at `reports/{NNN}-amortization-{YYYY-MM-DD}.csv` (Write tool) and return the path alongside the summary table.
       - Always preface with a 2-3 line summary: "30-year fixed @ 6.5%, $400k principal -> $2,528.27 monthly P&I, $510,178.20 total interest. Schedule below."

    ## Cost discipline

    You are running on Haiku because this work is one shell-out + one format. If a request would require multiple amortization runs (e.g., comparing 3 rate scenarios, stress-testing 50 rate shocks), you are the WRONG agent — return to the dispatcher: "This is a multi-loan comparison. Route to refi-npv-agent (for 2-5 refi offers) or stress-test-agent (for >5 scenarios in a parameter sweep)."

    ## Handoff hints

    - **Single refi quote evaluation** (one current loan vs one new offer): you can handle this — it's two amortization runs you do sequentially. Surface the savings/cost in the summary line.
    - **Multi-offer refi ranking** (≥2 offers): route to refi-npv-agent.
    - **Stress sweep** (parameter grid >5 scenarios): route to stress-test-agent.
    - **ARM amortization**: you can handle this if `scripts/arm_simulate.py` exists in `.claude/skills/mortgage-ops/scripts/` — same shell-out pattern. Run `--help` first.

    ---

    Reference: this agent definition follows the Anthropic sub-agents spec
    (https://code.claude.com/docs/en/sub-agents). Frontmatter `skills: [mortgage-ops]`
    injects the full SKILL.md content into this agent's context at spawn time per
    the documented "Preload skills into subagents" mechanism.
    ```

    Critical details:
    - The `description:` field is the routing signal (per 11-RESEARCH.md Pitfall 2 + Pattern 1). It MUST name (a) specific intent (single-loan amortization), (b) output shape (markdown table or CSV path), (c) trigger keywords (payment schedule, monthly P&I, biweekly, extra-principal). The current draft does this in one paragraph.
    - `model: haiku` — short alias per 11-PATTERNS.md CRITICAL #1a (avoids touching the file when haiku-4-5 → haiku-5).
    - `tools:` is YAML list form (per Anthropic spec, both list and comma-separated string accepted; list is more readable and ruff-yaml-friendly if anyone runs yamllint later).
    - Skill-resident script path used verbatim: `.claude/skills/mortgage-ops/scripts/amortize.py`.
    - Body length target: 80-150 lines (the template above is ~85 lines including blank lines and docstring footer). The 200-line cap is the orchestrator-imposed maximum.
    - No Co-Authored-By in any text or in the commit message (CLAUDE.md global rule).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/agents/amortization-agent.md &amp;&amp; uv run python -c "
import yaml
from pathlib import Path
text = Path('.claude/agents/amortization-agent.md').read_text()
assert text.startswith('---\n'), 'missing opening delimiter'
parts = text.split('---\n', 2)
assert len(parts) >= 3, 'missing closing delimiter'
fm = yaml.safe_load(parts[1])
assert fm['name'] == 'amortization-agent', f'name={fm.get(\"name\")}'
assert fm['model'] == 'haiku', f'model={fm.get(\"model\")}'
assert fm['skills'] == ['mortgage-ops'], f'skills={fm.get(\"skills\")}'
assert isinstance(fm['description'], str) and len(fm['description']) > 30, f'desc={fm.get(\"description\")}'
print('OK frontmatter valid')
"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f .claude/agents/amortization-agent.md` exits 0
    - `wc -l .claude/agents/amortization-agent.md` returns at least 80 and at most 200
    - `head -1 .claude/agents/amortization-agent.md` returns `---`
    - `grep -c '^name: amortization-agent$' .claude/agents/amortization-agent.md` returns 1
    - `grep -c '^model: haiku$' .claude/agents/amortization-agent.md` returns 1
    - `grep -c '^  - mortgage-ops$' .claude/agents/amortization-agent.md` returns 1 (under skills:)
    - `grep -cE '^  - (Read|Bash|Write)$' .claude/agents/amortization-agent.md` returns 3 (all three tools listed)
    - `grep -c 'scripts/amortize.py' .claude/agents/amortization-agent.md` returns at least 2 (--help invocation + actual invocation)
    - `grep -c '\.claude/skills/mortgage-ops/scripts/' .claude/agents/amortization-agent.md` returns at least 2 (skill-resident path used)
    - `grep -ci 'never compute numbers inline' .claude/agents/amortization-agent.md` returns at least 1
    - `grep -ci 'read.only user layer' .claude/agents/amortization-agent.md` returns at least 1
    - `grep -c 'household.yml' .claude/agents/amortization-agent.md` returns at least 1
    - `grep -c '6-key' .claude/agents/amortization-agent.md` returns at least 1 (envelope contract referenced)
    - `grep -ci 'co-authored-by' .claude/agents/amortization-agent.md` returns 0
  </acceptance_criteria>
  <done>
    Agent file exists with valid YAML frontmatter (name, description, model, skills, tools); body contains all 5 hard rules + workflow + cost discipline; file size within budget; no AI attribution.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip Wave 0 SUBA-01 xfail stub to a real assertion</name>
  <files>tests/test_subagents.py</files>
  <read_first>
    - tests/test_subagents.py (current Wave 0 stub for test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields)
    - 11-RESEARCH.md "Code Example 4: SUBA-01 frontmatter parse test" — body template
    - tests/test_subagents.py module-level helpers (_split_frontmatter, AGENTS_DIR, REQUIRED_FRONTMATTER_KEYS, VALID_MODELS) shipped in Wave 0
  </read_first>
  <action>
    Edit tests/test_subagents.py. For the function `test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields`:

    1. REMOVE the `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-01 ships .claude/agents/amortization-agent.md")` decorator.
    2. REPLACE the body `pytest.fail("Wave 0 stub")` with a real assertion using the Wave 0 helpers:

    ```python
    def test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields() -> None:
        """SUBA-01 + ROADMAP SC-1: amortization-agent.md frontmatter has model:, skills: [mortgage-ops], description, name."""
        path = AGENTS_DIR / "amortization-agent.md"
        assert path.exists(), f"SUBA-01: {path} must exist (shipped by Plan 11-01)"
        fm = _split_frontmatter(path)
        missing = REQUIRED_FRONTMATTER_KEYS - fm.keys()
        assert not missing, f"SUBA-01: {path.name} missing frontmatter keys: {missing}"
        assert fm["name"] == "amortization-agent", f"SUBA-01: name={fm['name']!r} must equal 'amortization-agent' (filename stem)"
        assert fm["model"] == "haiku", f"SUBA-01: model={fm['model']!r} must equal 'haiku' (REQUIREMENTS SUBA-01 + 11-RESEARCH model selection)"
        assert fm["skills"] == ["mortgage-ops"], f"SUBA-01: skills={fm['skills']!r} must equal ['mortgage-ops']"
        assert isinstance(fm["description"], str) and len(fm["description"]) > 30, (
            f"SUBA-01: description must be a non-trivial routing trigger, got {fm.get('description')!r}"
        )
    ```

    Do NOT touch any other test or any module-level constant. SUBA-02..06 stubs remain xfail.

    Per 11-RESEARCH.md the strict=True flag means a passing-but-still-xfailed test raises XPASS — that is precisely why we MUST remove the decorator at flip time, not just relax it.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest tests/test_subagents.py::test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields -v 2>&amp;1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/test_subagents.py::test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields -v 2>&1 | grep -c PASSED` returns 1
    - `grep -c 'test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields' tests/test_subagents.py` returns 1
    - `grep -B1 'def test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields' tests/test_subagents.py | grep -c xfail` returns 0 (decorator removed)
    - Other 5 SUBA stubs still xfail/skip (not accidentally flipped): `uv run pytest tests/test_subagents.py -v --tb=no 2>&1 | grep -cE '(XFAIL|SKIP)'` returns 5
    - Full suite still green: `uv run pytest -q 2>&1 | tail -3 | grep -cE '[0-9]+ failed' | grep -v '0 failed'` returns 0
    - `uv run mypy --strict tests/test_subagents.py` exits 0
    - `uv run ruff check tests/test_subagents.py` exits 0
  </acceptance_criteria>
  <done>
    SUBA-01 test passes; the other 5 SUBA stubs remain xfail/skip; suite green; SUBA-01 closed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent file → Claude Code session start | Agent is loaded at session start; mid-session edits require restart per 11-RESEARCH Pitfall 3 |
| description: field → dispatch routing | Vague description risks misroute (refi questions to amortization-agent etc) per 11-RESEARCH Pitfall 2 |
| Body prompt → script invocation | If prompt allows reading script source instead of --help, breaks Anthropic webapp-testing doctrine |
| Tools whitelist → User Layer | Write tool MUST NOT be turned against config/household.yml; defense-in-depth via prompt rule + pre-commit hook (Phase 1 FND-10) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-07 | Tampering (Write tool overwrites household.yml) | tools: [Write] in frontmatter | mitigate | Hard rule #3 in body explicitly forbids it; Phase 1 FND-10 pre-commit hook is belt-and-suspenders; Phase 12 eval can include a negative test ("user asks agent to update household.yml" → agent refuses) |
| T-11-08 | Information Disclosure (agent paraphrases Pydantic envelope, hides loc field) | Hard rule #5 | mitigate | Rule explicitly says "verbatim — do not paraphrase"; Phase 12 eval can assert envelope passthrough |
| T-11-09 | Repudiation (LLM-computed numbers leak past the contract) | Hard rule #1 | mitigate | "Never compute numbers inline" rule + handoff-hints to other agents for multi-loan; Phase 12 number-traceback eval (EVAL-04) catches violations |
| T-11-10 | Tampering (description: drift causes silent dispatch misroute) | description: field text | accept | description is hand-tuned at ship time; Phase 12 routing eval (EVAL-03) is the regression gate. Wave 1 just needs to make a non-trivial description; the calibration loop is Phase 12. |
| T-11-11 | Elevation of Privilege (Bash arbitrary command beyond script invocations) | Bash tool | accept | Vanilla Bash is broad; Phase 11 RESEARCH §Security accepts the risk because agent prompts only ever invoke `python .claude/skills/mortgage-ops/scripts/<name>.py --input ...` and agent files are version-controlled (any change is reviewable). Future hardening: PreToolUse hook validator. |
</threat_model>

<verification>
- File exists with valid YAML frontmatter; required keys (name/description/model/skills/tools) present
- model=haiku, skills=[mortgage-ops], name matches filename stem
- Body contains hard rules, workflow, cost discipline sections
- Body references skill-resident script path `.claude/skills/mortgage-ops/scripts/amortize.py`
- File size 80-200 lines
- Wave 0 SUBA-01 xfail stub flipped to passing assertion
- Full suite still green; mypy + ruff clean
- No Co-Authored-By in commit
</verification>

<success_criteria>
- `.claude/agents/amortization-agent.md` exists with all required frontmatter and body sections
- `tests/test_subagents.py::test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields` passes
- Other 5 SUBA stubs remain xfail/skip (no accidental flip)
- SUBA-01 requirement closed in REQUIREMENTS.md tracking
- No AI attribution in agent file or commit
</success_criteria>

<deviation_rules>
- If `.claude/agents/` directory does not exist: create it via the Write tool (the parent dirs are created automatically); do NOT add a `.gitkeep` (the agent file itself anchors the directory).
- If yaml.safe_load fails on the frontmatter during verify: inspect the file for tabs vs spaces, ensure the closing `---` is on its own line, and confirm no trailing whitespace before delimiters.
- If the description: field's auto-extracted len > 200 chars triggers any future yaml-style linter warning: that is fine — the field is intentionally descriptive; trim only if it crosses a hard limit (Anthropic spec does not document one as of 2026-05).
- If Phase 10 has ALREADY shipped `.claude/skills/mortgage-ops/SKILL.md` by the time this plan runs: nothing changes; the script-path references remain identical. The frontmatter `skills: [mortgage-ops]` resolves at agent-spawn time, not at file-write time.
- If the SUBA-01 test fails after flip with a "missing closing '---' delimiter" error: the agent file likely has a stray triple-dash inside the body (e.g., as a horizontal rule). Replace the body's `---` horizontal rule with `***` or remove it entirely; only the frontmatter delimiters can use `---`.
</deviation_rules>

<dependencies>
**Wave 1 dependencies:**

- **Hard:** Wave 0 (Plan 11-00) must be complete. Wave 0 ships the test stub `test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields` that this plan flips, and the `_split_frontmatter` helper that the flipped test calls.
- **Soft (Phase 10):** This plan can SHIP the agent file even before Phase 10 lands the skill. The frontmatter `skills: [mortgage-ops]` is static text; it only RESOLVES at agent-spawn time, which happens during interactive Claude Code use, not during Wave 1 verification. Wave 5's SUBA-04 + SUBA-05 smoke tests are the gates that require Phase 10 to be live.

**Cross-phase HARD GATE for Phase 11 EXECUTION (not planning):**
The agent file CAN be written and the SUBA-01 frontmatter test CAN pass without Phase 10. But the agent CANNOT be successfully dispatched in a live Claude Code session until Phase 10 ships:
- `.claude/skills/mortgage-ops/SKILL.md` (referenced by `skills: [mortgage-ops]`)
- `.claude/skills/mortgage-ops/scripts/amortize.py` (invoked by agent body)

If the executor tries to manually verify the agent in an interactive session BEFORE Phase 10 lands, the agent will spawn but `bash: python .claude/skills/mortgage-ops/scripts/amortize.py --help` will fail with FileNotFoundError. Document this in the SUMMARY and defer live-dispatch verification to post-Phase-10.

**Downstream:** Wave 5 (Plan 11-05) parametrizes test_SUBA_04 over EXPECTED_AGENTS, which includes amortization-agent. So the SUBA-04 flip in Wave 5 implicitly re-verifies this agent's `skills: [mortgage-ops]` field.
</dependencies>

<output>
After completion, create `.planning/phases/11-subagents/11-01-SUMMARY.md` documenting:
- Path to created agent file: `.claude/agents/amortization-agent.md`
- Frontmatter values: name, model, tools, skills, description (first ~80 chars)
- Line count of agent file
- SUBA-01 stub flip status (xfail → PASSED)
- Other 5 SUBA stubs status (still xfail/skip)
- Full suite status (≥379 + 1 new pass + 5 xfail/skip + 0 fail + 0 error)
- Confirmation: agent file body references `.claude/skills/mortgage-ops/scripts/amortize.py` (NOT project-root scripts/)
- Confirmation: no Co-Authored-By in agent file or commit message
- Note: live dispatch verification deferred to post-Phase-10 (the agent file can be tested for frontmatter validity now, but cannot be interactively dispatched until Phase 10's skill + scripts land)
</output>
