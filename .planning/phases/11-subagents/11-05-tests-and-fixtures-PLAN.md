---
phase: 11
plan: 05
type: execute
wave: 5
depends_on:
  - "11-00"
  - "11-01"
  - "11-02"
  - "11-03"
  - "11-04"
files_modified:
  - tests/test_subagents.py
  - tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl
  - tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl
  - tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl
  - tests/fixtures/subagent_transcripts/README.md
autonomous: true
requirements:
  - SUBA-04
  - SUBA-06
tags:
  - phase-11
  - subagents
  - tests
  - transcript-fixtures
  - tokenizer
  - suba-04
  - suba-06
must_haves:
  truths:
    - "tests/test_subagents.py contains six PASSING test functions covering SC-1..SC-5: test_SUBA_01_..., test_SUBA_02_..., test_SUBA_03_..., test_SUBA_04_skills_field_resolves_for_each_agent (SC-5 smoke), test_SUBA_04_refi_handoff_returns_ranked_table (SC-4 refi via transcript fixture), test_SUBA_04_amort_handoff_returns_csv_or_markdown (SC-4 amort via transcript fixture), test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent (SC-2 — flipped in Plan 11-04), and test_SUBA_06_stress_summary_under_1000_tokens (SC-3 via anthropic.count_tokens against recorded transcript fixture)"
    - "tests/fixtures/subagent_transcripts/ contains three pre-recorded synthetic transcript fixtures (stress_50_scenarios.transcript.jsonl, refi_3_offers.transcript.jsonl, amort_single_loan.transcript.jsonl) — synthetic for CI determinism per D-02"
    - "tests/fixtures/subagent_transcripts/README.md documents the fixture contract + the live-capture recipe (claude -p ... > <name>.transcript.jsonl) for nightly eval regeneration; live capture is NOT run in CI per D-02"
    - "anthropic Python SDK is wired as a test-time dependency (already added in Wave 0); SUBA-06 imports it via pytest.importorskip; SUBA-06 skipif-gates on missing ANTHROPIC_API_KEY"
    - "SC-3 token budget threshold is exactly 1000 (assertion: response.input_tokens < 1000) per D-03 — not 999, not 1001"
    - "SC-5 smoke test (test_SUBA_04_skills_field_resolves_for_each_agent) is parametrized over EXPECTED_AGENTS and asserts (a) fm['skills'] == ['mortgage-ops'], (b) os.path.exists('.claude/skills/mortgage-ops/scripts/amortize.py'), (c) os.path.exists for refi_npv.py and stress_test.py — pytest collection-time pathing per D-04"
    - "All Phase 11 SUBA-01..06 stubs from Wave 0 are now in their final state: passing OR (Plan 11-04 branch (b)) explicitly-deferred-with-pointer; no orphan xfails remain"
    - "Full suite green; mypy --strict + ruff clean for tests/test_subagents.py"
    - "Phase 4 baseline (379 passed + 4 skipped + 0 xfail) preserved exactly modulo Phase 11 additions"
  artifacts:
    - path: "tests/test_subagents.py"
      provides: "Final test surface for Phase 11 SUBA-01..06; flips Wave 0 xfails for SUBA-04 + SUBA-06; imports anthropic for SC-3"
      min_lines: 250
      contains: "def test_SUBA_06_stress_summary_under_1000_tokens"
    - path: "tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl"
      provides: "Synthetic 50-scenario rate-shock summary transcript representing what stress-test-agent returns to main thread; <1000 tokens per anthropic.count_tokens"
      min_lines: 1
    - path: "tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl"
      provides: "Synthetic 3-offer ranked-NPV-table transcript representing what refi-npv-agent returns; markdown table sorted descending by NPV"
      min_lines: 1
    - path: "tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl"
      provides: "Synthetic single-loan amortization transcript representing what amortization-agent returns; markdown table OR CSV path string"
      min_lines: 1
    - path: "tests/fixtures/subagent_transcripts/README.md"
      provides: "Documents the transcript-fixture contract + the live-capture recipe for nightly regeneration; explains why CI uses synthetic-only fixtures"
      min_lines: 50
  key_links:
    - from: "tests/test_subagents.py SUBA-06"
      to: "anthropic.Anthropic().messages.count_tokens"
      via: "pytest.importorskip('anthropic') + skipif on ANTHROPIC_API_KEY; tokenizer per RESEARCH Code Example 5 + D-01"
      pattern: "count_tokens"
    - from: "tests/test_subagents.py SUBA-06 transcript load"
      to: "tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl"
      via: "TRANSCRIPT_DIR module constant from Wave 0"
      pattern: "stress_50_scenarios"
    - from: "tests/test_subagents.py SUBA-04 refi handoff"
      to: "tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl"
      via: "TRANSCRIPT_DIR; assertion that transcript content is a markdown table sorted descending by NPV column"
      pattern: "refi_3_offers"
    - from: "tests/test_subagents.py SUBA-04 amort handoff"
      to: "tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl"
      via: "TRANSCRIPT_DIR; assertion that transcript content is either a markdown table OR a CSV path string"
      pattern: "amort_single_loan"
    - from: "tests/test_subagents.py SC-5 smoke"
      to: ".claude/skills/mortgage-ops/scripts/{amortize,refi_npv,stress_test}.py"
      via: "os.path.exists at pytest collection time per D-04; gated by skipif if Phase 10 has not yet relocated scripts"
      pattern: "\\.claude/skills/mortgage-ops/scripts"
---

<objective>
Pin all Phase 11 SC gates with passing tests + commit synthetic transcript fixtures. This wave is the SUBA-04 + SUBA-06 closure point and the final Wave 0 xfail flip (modulo Plan 11-04 branch (b) which deferred SUBA-05 to Phase 10). Closes SUBA-04 + SUBA-06.

Purpose: Plans 11-01..11-03 shipped the agent files; Plan 11-04 wired the routing seam. Plan 11-05 is where the success criteria become measurable: SC-3 (1000-token budget gate) requires the anthropic.count_tokens call against a recorded transcript; SC-4 (refi 3-offer ranked table + amort CSV/markdown) requires per-agent shape assertions against transcripts; SC-5 (skills field resolves) requires a smoke test that asserts both the YAML skills field AND the bundled-script-path reachability per RESEARCH Pitfall 1 ("skills: is not a script-bundling mechanism — bundled scripts are filesystem files, reached via Bash; SC-5 must check filesystem reachability, not context inclusion").

Output: One major test-file edit (~6 new test functions, 3 xfail flips), three synthetic transcript fixtures (small enough to commit + deterministic for CI), one fixture README documenting the live-capture recipe. anthropic SDK was added to dev-deps in Wave 0; this wave consumes it.
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
@.planning/phases/11-subagents/11-03-stress-test-agent-PLAN.md
@.planning/phases/11-subagents/11-04-skill-routing-update-PLAN.md
@.planning/phases/11-subagents/11-04-SUBA-05-TODO.md
@tests/test_subagents.py
@tests/fixtures/subagent_transcripts/README.md
@pyproject.toml

<interfaces>
**Anthropic count_tokens API surface (per RESEARCH Code Example 5):**

```python
import anthropic
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY env
response = client.messages.count_tokens(
    model="claude-haiku-4-5",
    messages=[{"role": "assistant", "content": "<text>"}],
)
assert response.input_tokens < 1000  # SC-3 gate per D-03
```

`count_tokens` is FREE (separate rate limit, no content billing) but requires ANTHROPIC_API_KEY at runtime — that is why SUBA-06 ships with `@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"))`. RESEARCH Assumption A6 flagged that count_tokens with `role: assistant` (measuring assistant OUTPUT) is the documented use case — Wave 0 verified this; this plan consumes it.

**Transcript fixture format (D-02):**

`.transcript.jsonl` files are one JSON object per line — `{"role": "assistant", "content": "<markdown>"}` — to support future multi-message transcripts (e.g., user question + assistant answer + assistant follow-up). For SUBA-06 / SUBA-04 v1 each fixture has ONE line: the agent's final response to the dispatcher. Synthetic content is hand-authored to (i) match the canonical agent-output shape (per agent body specs in Plans 11-01..11-03) and (ii) fit token budgets where applicable.

**SC-5 / SUBA-04 contract (per RESEARCH Pitfall 1, repeated for emphasis):**

> "skills: is NOT a script-bundling mechanism. The skills: frontmatter field injects SKILL.md *content* into the subagent's context at spawn — but bundled `scripts/*.py` remain filesystem files, reached via the subagent's Bash tool the same way the main thread reaches them. SC-5's smoke test must check filesystem reachability via os.path.exists, NOT context inclusion."

Per D-04, the SC-5 smoke test asserts at pytest collection time:
1. Each agent's frontmatter `skills` field equals `["mortgage-ops"]` (per SUBA-04 / SUBA-01 already-passing assertion — no regression here).
2. Each bundled script exists at the skill-resident path: `os.path.exists('.claude/skills/mortgage-ops/scripts/amortize.py')`, etc.
3. If Phase 10 has NOT yet relocated scripts, gate the assertion with `pytest.mark.skipif(not Path('.claude/skills/mortgage-ops/scripts/amortize.py').exists())` (cross-phase tolerance — same pattern as Plan 11-04 branch (b) tolerates Phase 10 absence).

**Existing Wave 0 stubs to flip (per Plan 11-00 truths):**

- `test_SUBA_04_skills_field_resolves_for_each_agent` (SC-5)
- `test_SUBA_04_refi_handoff_returns_ranked_table` (SC-4 refi)
- `test_SUBA_04_amort_handoff_returns_csv_or_markdown` (SC-4 amort)
- `test_SUBA_06_stress_summary_under_1000_tokens` (SC-3)

Plan 11-04 already flipped SUBA-05 (or deferred it per branch b). Plans 11-01..11-03 already flipped SUBA-01..03. So this plan flips the remaining 4 (or 3 if SUBA-05 deferred).

**Synthetic-fixture content shape (D-02 — hand-authored examples):**

`stress_50_scenarios.transcript.jsonl` (one line; ≤1,000 tokens per anthropic.count_tokens; representative of stress-test-agent's canonical 50-scenario rate-shock output per Plan 11-03 Hard rule #5):

```jsonl
{"role": "assistant", "content": "## 50-scenario rate-shock sweep summary\n\n| rate_bps | rate | monthly_pi | dti_back | breach |\n|---------:|-----:|-----------:|---------:|:-------|\n| -200 | 4.50% | $2,026.74 | 28.1% | no |\n| -100 | 5.50% | $2,271.16 | 30.4% | no |\n|    0 | 6.50% | $2,528.27 | 32.9% | no |\n| +100 | 7.50% | $2,796.86 | 35.5% | no |\n| +200 | 8.50% | $3,076.22 | 38.2% | yes |\n\n... (45 additional scenarios summarized — 5 binned representative rows shown above) ...\n\n**Worst-case:** +500 bps shock breaches at DTI 47.6% (max_dti 43%). **Median outcome:** baseline +50 bps, DTI 33.7%, no breach. **Affordability cliff:** +180 bps (the first scenario where DTI exceeds 36% front-end recommended).\n\nHighlights:\n- Scenario +500: $3,924.18 P&I, DTI 47.6% (BREACH)\n- Scenario   +0: $2,528.27 P&I, DTI 32.9% (baseline)\n- Scenario -200: $2,026.74 P&I, DTI 28.1% (best)\n\nComputed by: bash python .claude/skills/mortgage-ops/scripts/stress_test.py --input /tmp/stress-input-1714665600.json"}
```

`refi_3_offers.transcript.jsonl` (one line; ranked markdown table sorted descending by NPV per Plan 11-02 Hard rule #5):

```jsonl
{"role": "assistant", "content": "## Refi NPV ranking (3 offers, borrower perspective)\n\n| lender | rate | closing_costs | breakeven_months | NPV |\n|:-------|-----:|--------------:|-----------------:|----:|\n| Acme Mortgage | 5.875% | $3,200 | 18 | $14,287 |\n| Bedrock Loans | 5.750% | $5,800 | 31 | $11,944 |\n| ColdStream Federal | 6.000% | $2,400 | n/a | -$842 |\n\n**Winner:** Acme Mortgage. Best NPV ($14,287) AND fastest breakeven (18 months). Bedrock has a lower rate but $2,600 higher closing costs erodes the savings — close second. ColdStream's small closing-cost advantage cannot overcome its higher rate; negative NPV — skip.\n\nComputed by: bash python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi-input-{1,2,3}-1714665600.json (3 invocations)"}
```

`amort_single_loan.transcript.jsonl` (one line; markdown table per Plan 11-01 Hard rule #4 — ≤30 rows so markdown not CSV):

```jsonl
{"role": "assistant", "content": "## Amortization: $400,000 @ 6.50% / 30yr fixed\n\nMonthly P&I: $2,528.27 | Total interest: $510,178.20\n\n| month | payment | principal | interest | balance |\n|------:|--------:|----------:|---------:|--------:|\n|   1 | $2,528.27 |   $361.61 | $2,166.67 | $399,638.39 |\n|   2 | $2,528.27 |   $363.57 | $2,164.71 | $399,274.83 |\n| ... | ... | ... | ... | ... |\n| 360 | $2,528.27 | $2,514.61 |    $13.66 |       $0.00 |\n\nFull schedule (360 rows) exceeds inline display threshold; full table written to: `reports/001-amortization-2026-05-02.csv`\n\nComputed by: bash python .claude/skills/mortgage-ops/scripts/amortize.py --input /tmp/amort-input-1714665600.json"}
```

These synthetic fixtures are deliberately small — well under the 1k token budget for stress (target: ~600 tokens), so SC-3 has headroom and the test isn't on the knife edge.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author the three synthetic transcript fixtures + update the README with the live-capture recipe</name>
  <files>tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl, tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl, tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl, tests/fixtures/subagent_transcripts/README.md</files>
  <read_first>
    - tests/fixtures/subagent_transcripts/README.md (current Wave 0 placeholder — describes the fixture-regeneration ritual to extend)
    - .claude/agents/stress-test-agent.md (Plan 11-03) — the canonical output shape this fixture mirrors
    - .claude/agents/refi-npv-agent.md (Plan 11-02) — the canonical ranked-table shape
    - .claude/agents/amortization-agent.md (Plan 11-01) — the canonical amortization output shape
    - 11-RESEARCH.md Pitfall 5 ("Subagent emits raw JSON instead of summary") — content shape rationale
  </read_first>
  <action>
    Create the three transcript fixtures with the EXACT content blocks from the `<interfaces>` section above (verbatim — they are designed to mirror the canonical agent output shapes from Plans 11-01..11-03 and to fit token budgets where applicable).

    **Fixture 1: tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl** — write the one-line JSONL from `<interfaces>` → stress block.

    **Fixture 2: tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl** — write the one-line JSONL from `<interfaces>` → refi block.

    **Fixture 3: tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl** — write the one-line JSONL from `<interfaces>` → amort block.

    **Update tests/fixtures/subagent_transcripts/README.md** — append (or replace if Wave 0 stub) with sections: (1) "# Subagent transcript fixtures" intro; (2) "## Files" table listing the three fixtures + their tested SC + approx tokens; (3) "## Why synthetic, not live" with D-02 rationale (determinism / free / airgap-safe / contract-is-shape); (4) "## Live-capture recipe (NOT run in CI)" with `claude -p ... --output-format json | jq ... > <name>.transcript.jsonl.NEW` workflow + diff/promote ritual; (5) "## When to regenerate" (quarterly + after agent prompt change + after Phase 10 SKILL.md change); (6) "## Required ANTHROPIC_API_KEY scope" noting count_tokens is free but needs the key, claude -p needs paid tier; (7) "## No AI attribution" reminder per CLAUDE.md global rule.

    Critical details:
    - JSONL format: ONE JSON object per line; the test's TRANSCRIPT_DIR loader reads `path.read_text()` then `json.loads(line)` for each line; v1 fixtures have one line each.
    - Content uses `\n` for newlines (JSON escaping); load via `json.loads(...)["content"]` returns the markdown string with real newlines.
    - The "Approx tokens" column in the README is informational; the actual SC-3 assertion calls anthropic.count_tokens at test time. The synthetic content is hand-tuned to have ~40% headroom under 1000 tokens so future content edits don't push the test onto the knife edge.
    - No Co-Authored-By in any file or in the commit message.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for f in stress_50_scenarios refi_3_offers amort_single_loan; do test -f "tests/fixtures/subagent_transcripts/${f}.transcript.jsonl" || { echo "MISSING: ${f}"; exit 1; }; uv run python -c "
import json
from pathlib import Path
path = Path('tests/fixtures/subagent_transcripts/${f}.transcript.jsonl')
lines = [l for l in path.read_text().splitlines() if l.strip()]
assert len(lines) == 1, f'expected 1 line, got {len(lines)}'
obj = json.loads(lines[0])
assert obj['role'] == 'assistant', f'role={obj[\"role\"]}'
assert isinstance(obj['content'], str) and len(obj['content']) > 100, f'content too short: {len(obj[\"content\"])} chars'
print(f'OK ${f}: {len(obj[\"content\"])} chars')
"; done &amp;&amp; test $(wc -l &lt; tests/fixtures/subagent_transcripts/README.md) -ge 50 &amp;&amp; grep -c 'claude -p' tests/fixtures/subagent_transcripts/README.md &amp;&amp; grep -c 'synthetic' tests/fixtures/subagent_transcripts/README.md</automated>
  </verify>
  <acceptance_criteria>
    - All three `tests/fixtures/subagent_transcripts/*.transcript.jsonl` files exist and parse as valid JSONL with exactly one line, `role: assistant`, non-empty content (>100 chars)
    - Stress fixture content contains "Computed by:" + "stress_test.py" + the 5-row binned table marker (`-200`, `+500`, `breach`)
    - Refi fixture content contains "Computed by:" + "refi_npv.py" + ranked table (lender names) + "Winner:"
    - Amort fixture content contains "Computed by:" + "amortize.py" + "Monthly P&I" + table OR CSV path
    - tests/fixtures/subagent_transcripts/README.md is ≥ 50 lines and contains "claude -p" recipe + "synthetic" rationale + "ANTHROPIC_API_KEY" scope note
    - `grep -ci 'co-authored-by' tests/fixtures/subagent_transcripts/` (recursive) returns 0
  </acceptance_criteria>
  <done>
    Three synthetic transcript fixtures committed; README updated with live-capture recipe + synthetic-vs-live rationale; all fixtures pass JSONL validation; no AI attribution.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip Wave 0 SUBA-04 + SUBA-06 xfails to passing assertions in tests/test_subagents.py</name>
  <files>tests/test_subagents.py</files>
  <read_first>
    - tests/test_subagents.py current Wave 0 stubs for SUBA-04 (3 stubs: skills_field_resolves, refi_handoff, amort_handoff) + SUBA-06 (1 stub)
    - 11-RESEARCH.md Code Example 4 (SUBA-01 frontmatter parse pattern, parametrized over EXPECTED_AGENTS) and Code Example 5 (SUBA-06 token budget pattern with anthropic.count_tokens + skipif)
    - 11-RESEARCH.md Pitfall 1 (skills field is NOT script bundling; SC-5 must check filesystem reachability)
    - .planning/phases/11-subagents/11-04-SUBA-05-TODO.md (to know whether SUBA-05 is in branch a or b — affects how we count remaining xfails)
  </read_first>
  <action>
    Edit tests/test_subagents.py. Make the following four changes (one per Wave 0 stub being flipped):

    **Flip 1 — `test_SUBA_04_skills_field_resolves_for_each_agent` (SC-5 smoke, parametrized):**

    Remove the `@pytest.mark.xfail(...)` decorator. Replace the body with:

    ```python
    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS, ids=lambda n: n)
    def test_SUBA_04_skills_field_resolves_for_each_agent(agent_name: str) -> None:
        """SUBA-04 + SC-5: each agent's skills field is ['mortgage-ops'] AND the bundled
        scripts are reachable on the filesystem at the skill-resident path.

        Per Plan 11-05 D-04: SC-5 smoke is a pytest-collection-time os.path.exists check.
        Per RESEARCH Pitfall 1, skills: is NOT a script-bundling mechanism — bundled
        scripts are filesystem files reached via Bash. So SC-5 verifies (a) the skills
        frontmatter is correct, (b) the named scripts exist on disk at the path the
        agent body references.
        """
        # Part (a): frontmatter skills field
        path = AGENTS_DIR / f"{agent_name}.md"
        assert path.exists(), f"SUBA-04: {path} must exist (Plans 11-01..11-03 dependency)"
        fm = _split_frontmatter(path)
        assert fm["skills"] == ["mortgage-ops"], (
            f"SUBA-04: {agent_name}.md skills={fm['skills']!r} must equal ['mortgage-ops']"
        )

        # Part (b): bundled scripts reachable at skill-resident path
        skill_scripts_dir = SKILLS_DIR / "scripts"
        expected_script_for = {
            "amortization-agent": "amortize.py",
            "refi-npv-agent": "refi_npv.py",
            "stress-test-agent": "stress_test.py",
        }
        expected_script = expected_script_for[agent_name]
        script_path = skill_scripts_dir / expected_script

        if not skill_scripts_dir.exists():
            pytest.skip(
                f"SUBA-04 SC-5 part (b): {skill_scripts_dir} does not exist yet — Phase 10 has not "
                f"relocated scripts to the skill folder (SKLL-10). Test will pass once Phase 10 ships. "
                f"Skip is intentional cross-phase tolerance per Plan 11-05 D-04."
            )
        assert script_path.exists(), (
            f"SUBA-04 SC-5: {agent_name}.md references {expected_script} but {script_path} "
            f"does not exist on the filesystem (Phase 10 SKLL-10 dependency)."
        )
    ```

    **Flip 2 — `test_SUBA_04_refi_handoff_returns_ranked_table` (SC-4 refi via transcript fixture):**

    Remove the `@pytest.mark.xfail(...)` decorator. Replace the body with:

    ```python
    def test_SUBA_04_refi_handoff_returns_ranked_table() -> None:
        """SUBA-04 + SC-4 (refi): refi-npv-agent output is a ranked markdown table sorted
        descending by NPV (per Plan 11-02 Hard rule #5).

        Tested against the recorded synthetic transcript fixture per Plan 11-05 D-02.
        """
        path = TRANSCRIPT_DIR / "refi_3_offers.transcript.jsonl"
        assert path.exists(), f"SUBA-04 refi: transcript fixture {path} must exist (Plan 11-05 Task 1)"
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 1, f"SUBA-04 refi: expected 1-line transcript, got {len(lines)}"
        content = json.loads(lines[0])["content"]

        # Shape assertion 1: markdown table with lender + NPV columns
        assert "| lender " in content and "| NPV " in content, (
            f"SUBA-04 refi: transcript must contain a markdown table with 'lender' and 'NPV' columns; "
            f"got first 200 chars: {content[:200]!r}"
        )
        # Shape assertion 2: at least 3 ranked rows (3-offer fixture; +1 header)
        table_rows = [l for l in content.splitlines() if l.startswith("| ") and "|" in l[2:] and "---" not in l]
        assert len(table_rows) >= 4, (
            f"SUBA-04 refi: expected >=4 table rows (1 header + >=3 data), got {len(table_rows)}"
        )
        # Shape assertion 3: descending-by-NPV ordering — NPV is LAST column per Plan 11-02 Hard rule #5
        npv_values: list[float] = []
        for row in table_rows[1:]:
            cells = [c.strip() for c in row.split("|") if c.strip()]
            npv_str = cells[-1].replace("$", "").replace(",", "")
            npv_values.append(float(npv_str))
        assert npv_values == sorted(npv_values, reverse=True), (
            f"SUBA-04 refi: NPV column must be sorted descending; got {npv_values}"
        )
        # Shape assertion 4: citation discipline (Plans 11-02 + 11-03)
        assert "Computed by:" in content and "refi_npv.py" in content, (
            f"SUBA-04 refi: transcript must contain 'Computed by:' citation referencing refi_npv.py"
        )
    ```

    **Flip 3 — `test_SUBA_04_amort_handoff_returns_csv_or_markdown` (SC-4 amort via transcript fixture):**

    Remove the `@pytest.mark.xfail(...)` decorator. Replace the body with:

    ```python
    def test_SUBA_04_amort_handoff_returns_csv_or_markdown() -> None:
        """SUBA-04 + SC-4 (amort): amortization-agent output is a markdown table OR a CSV path
        string under reports/{NNN}-amortization-{YYYY-MM-DD}.csv (per Plan 11-01 Hard rule #4).
        """
        path = TRANSCRIPT_DIR / "amort_single_loan.transcript.jsonl"
        assert path.exists(), f"SUBA-04 amort: transcript fixture {path} must exist (Plan 11-05 Task 1)"
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 1, f"SUBA-04 amort: expected 1-line transcript, got {len(lines)}"
        content = json.loads(lines[0])["content"]

        has_markdown_table = "| month " in content and "| balance " in content
        has_csv_path = bool(re.search(r"reports/\d{3}-amortization-\d{4}-\d{2}-\d{2}\.csv", content))
        assert has_markdown_table or has_csv_path, (
            f"SUBA-04 amort: transcript must contain EITHER a markdown table (|month|...|balance|) "
            f"OR a CSV path (reports/NNN-amortization-YYYY-MM-DD.csv); got: {content[:200]!r}"
        )
        assert "Computed by:" in content and "amortize.py" in content, (
            f"SUBA-04 amort: transcript must contain 'Computed by:' citation referencing amortize.py"
        )
    ```

    **Flip 4 — `test_SUBA_06_stress_summary_under_1000_tokens` (SC-3 token budget):**

    Remove the `@pytest.mark.xfail(...)` decorator. Replace the body with the canonical pattern from RESEARCH Code Example 5, adjusted for D-01 (anthropic.count_tokens) + D-03 (1000-token threshold exact):

    ```python
    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="SC-3 SUBA-06 token-budget test requires ANTHROPIC_API_KEY for anthropic.count_tokens "
               "(FREE — no content billing per Anthropic docs — but requires network round-trip). "
               "Skip is intentional for local dev without the key; CI must inject the key as a secret.",
    )
    def test_SUBA_06_stress_summary_under_1000_tokens() -> None:
        """SC-3: 50-scenario rate-shock summary fits under 1,000 tokens.

        Per Plan 11-05 D-01: tokenizer = anthropic.Anthropic().messages.count_tokens (the
        official Claude tokenizer; tiktoken explicitly REJECTED per RESEARCH Standard Stack
        because it is OpenAI-specific and ~5-20% drift on the <1k boundary).

        Per Plan 11-05 D-03: budget threshold is exactly 1000 tokens (response.input_tokens
        < 1000) — not 999, not 1001. Matches the literal SC-3 wording.

        Per Plan 11-05 D-02: tested against the synthetic transcript fixture (committed at
        tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl) for CI
        determinism. Live capture for nightly eval is documented in the fixture README but
        NOT run in CI.
        """
        anthropic = pytest.importorskip("anthropic")
        path = TRANSCRIPT_DIR / "stress_50_scenarios.transcript.jsonl"
        assert path.exists(), f"SC-3: transcript fixture {path} must exist (Plan 11-05 Task 1)"
        content = json.loads(path.read_text().strip().splitlines()[0])["content"]

        client = anthropic.Anthropic()
        response = client.messages.count_tokens(
            model="claude-haiku-4-5",
            messages=[{"role": "assistant", "content": content}],
        )
        assert response.input_tokens < 1000, (
            f"SC-3 SUBA-06: stress-test-agent summary returned {response.input_tokens} tokens, "
            f"exceeds 1000-token budget (Plan 11-05 D-03 threshold; ROADMAP SC-3 verbatim). "
            f"To diagnose: drop a highlight row or shorten the narrative in the fixture, OR if "
            f"the agent output legitimately requires >1000 tokens, surface as a Phase 12 follow-up."
        )
    ```

    **At top of file (if not already present from Wave 0):** ensure these imports exist: `import json`, `import os`, `import re`.

    Per RESEARCH Open Question #4 + Pitfall 3: the SC-5 smoke is filesystem-only (no live agent spawn) — that decision is honored here via the parametrized skills+filesystem assertion.

    Do NOT touch any other test or any module-level constant. SUBA-01..03 (Plans 11-01..03 flips) and SUBA-05 (Plan 11-04 flip OR deferred xfail) remain in their current state.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest tests/test_subagents.py -v --tb=short 2>&amp;1 | tail -25 &amp;&amp; uv run mypy --strict tests/test_subagents.py &amp;&amp; uv run ruff check tests/test_subagents.py</automated>
  </verify>
  <acceptance_criteria>
    - SUBA-04 skills_field_resolves test: parametrized 3 cases, all PASS or SKIP (skip iff Phase 10 hasn't relocated scripts) — `uv run pytest tests/test_subagents.py -k 'SUBA_04_skills_field' -v 2>&1 | grep -cE '(PASSED|SKIPPED)'` returns 3
    - SUBA-04 refi handoff test: PASSES — `uv run pytest tests/test_subagents.py::test_SUBA_04_refi_handoff_returns_ranked_table -v 2>&1 | grep -c PASSED` returns 1
    - SUBA-04 amort handoff test: PASSES — `uv run pytest tests/test_subagents.py::test_SUBA_04_amort_handoff_returns_csv_or_markdown -v 2>&1 | grep -c PASSED` returns 1
    - SUBA-06 stress summary test: PASSES if ANTHROPIC_API_KEY set, else SKIPPED — `uv run pytest tests/test_subagents.py::test_SUBA_06_stress_summary_under_1000_tokens -v 2>&1 | grep -cE '(PASSED|SKIPPED)'` returns 1
    - All four functions had xfail decorators removed: `grep -B1 -E 'def test_SUBA_(04|06)_' tests/test_subagents.py | grep -c '@pytest.mark.xfail'` returns 0
    - Wave 1+2+3 still pass: `uv run pytest tests/test_subagents.py -v --tb=no 2>&1 | grep -cE 'test_SUBA_0[123]_.*PASSED'` returns 3
    - SUBA-05 in its expected state per Plan 11-04 branch result (passing or xfail with TODO reason)
    - Full suite green: `uv run pytest -q 2>&1 | tail -3 | grep -cE '[0-9]+ failed' | grep -v '0 failed'` returns 0
    - `uv run mypy --strict tests/test_subagents.py` exits 0
    - `uv run ruff check tests/test_subagents.py` exits 0
    - No orphan xfails remain in tests/test_subagents.py except (possibly) the SUBA-05 deferred xfail with the TODO marker reason
  </acceptance_criteria>
  <done>
    SUBA-04 (3 functions) + SUBA-06 (1 function) xfails flipped to passing/skipping assertions; SUBA-01..03 still pass; SUBA-05 in its Plan-11-04-determined state; full suite green; mypy + ruff clean; SUBA-04 + SUBA-06 requirements closed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Synthetic transcript fixture → SC-3 / SC-4 assertions | Fixture content drift could silently invalidate the SC gates (e.g., NPV column reordered → ranking assertion passes despite bad agent output) |
| Synthetic vs live transcripts | Synthetic content represents what we WANT the agent to produce, not what it actually does; drift between synthetic + live is unmonitored without nightly eval regeneration |
| anthropic.count_tokens network call → CI reliability | SC-3 test requires network + ANTHROPIC_API_KEY at CI time; key absence triggers SKIP not FAIL (acceptable trade-off) |
| SUBA-04 SC-5 filesystem check → Phase 10 dependency | If Phase 10 hasn't shipped, the SC-5 part (b) skips — could mask a real Phase 11 bug if the script paths drift after Phase 10 lands |
| Test imports anthropic at runtime | If anthropic SDK shape changes (response.input_tokens → response.usage.input_tokens), SC-3 silently breaks |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-28 | Tampering (synthetic fixture content drifts from canonical agent output shape; tests still pass but no longer measure the real thing) | tests/fixtures/subagent_transcripts/*.transcript.jsonl | mitigate | README documents the quarterly-regenerate ritual + the live-capture recipe; nightly eval (Phase 12 EVAL-03) re-captures and diffs; the fixture file itself contains a "Computed by:" cite that the test asserts (so the fixture cannot drift to LLM-fabricated numbers without breaking the test) |
| T-11-29 | Information Disclosure (real ANTHROPIC_API_KEY accidentally committed via the live-capture recipe) | tests/fixtures/subagent_transcripts/README.md live-capture recipe | mitigate | README says "CI must inject the key as a secret"; the recipe writes to `.NEW` files and uses `mv` to promote, never embedding the key; CLAUDE.md FND-08 + FND-10 (gitignore + pre-commit hook) catch keys in tests/fixtures via pre-commit even if a developer pastes one accidentally |
| T-11-30 | Denial of Service (SC-3 network call to anthropic.com fails in CI; entire suite turns red) | test_SUBA_06 anthropic.count_tokens call | mitigate | Skipif on missing ANTHROPIC_API_KEY skips cleanly; if key present but network fails, the assertion's `pytest.importorskip("anthropic")` runs but the API call would raise — accept this risk: count_tokens is FREE per Anthropic docs (no rate-limit issues), and the network call is < 1s typical |
| T-11-31 | Tampering (test refactor changes SC-3 budget threshold from < 1000 to <= 1000) | test_SUBA_06 budget assertion | mitigate | D-03 explicitly pins exact threshold (< 1000 not <= 1000); the test docstring repeats the rationale; this plan's acceptance_criteria asserts the literal `< 1000` operator |
| T-11-32 | Tampering (someone replaces synthetic transcripts with live-captured transcripts that vary across CI runs) | tests/fixtures/subagent_transcripts/*.transcript.jsonl | mitigate | D-02 explicitly forbids live-captured fixtures in CI; README documents the rationale; pre-commit hook could be extended (Phase 12 follow-up) to detect non-deterministic content via a hash check, but for v1 the doctrine is a planning + documentation discipline |
| T-11-33 | Repudiation (anthropic SDK response shape changes from .input_tokens to .usage.input_tokens; SC-3 silently fails AttributeError instead of clear assertion message) | test_SUBA_06 .input_tokens attribute access | mitigate | Wave 0 added a smoke test for response shape (per RESEARCH Pitfall 4 mitigation); SDK is pinned tight in pyproject.toml (not >=, == or ~=); deliberate bumps re-run the SDK-shape smoke + this SC-3 test |
| T-11-34 | Tampering (Plan 11-04 branch (b) was taken and the SUBA-05 deferred xfail is silently removed by Plan 11-05 cleanup; SC-2 then has zero test coverage) | Wave 0 SUBA-05 stub state | mitigate | Plan 11-05 action explicitly says "SUBA-05 ... remain in their current state" — the xfail or pass set by Plan 11-04 is preserved, not touched; acceptance criteria asserts SUBA-05 in its Plan-11-04-determined state, so any accidental removal triggers test count mismatch |
</threat_model>

<verification>
- Three synthetic transcript fixtures exist + parse as valid JSONL + match canonical agent output shapes
- README documents live-capture recipe (claude -p) + synthetic-vs-live rationale (D-02)
- SUBA-04 (3 functions: skills, refi, amort) + SUBA-06 xfails removed; assertions PASS or SKIP appropriately
- SUBA-04 refi assertion enforces NPV-descending ordering (4-pass shape check)
- SUBA-04 amort assertion enforces markdown-table OR csv-path shape (per Plan 11-01 Hard rule #4)
- SUBA-04 skills_field_resolves enforces both (a) frontmatter skills field AND (b) filesystem reachability of bundled scripts (per RESEARCH Pitfall 1)
- SUBA-06 enforces the exact <1000 threshold via anthropic.count_tokens against the recorded transcript (D-01 + D-03)
- SUBA-06 skipif on ANTHROPIC_API_KEY (graceful degradation in airgapped CI)
- SUBA-01..03 still pass (no regression)
- SUBA-05 in its Plan-11-04-determined state (passing for branch (a) or xfail-with-TODO for branch (b))
- Full suite green; mypy + ruff clean
- No orphan xfails (every Wave 0 stub now in its final state)
- No Co-Authored-By in any file or commit
</verification>

<success_criteria>
- ROADMAP SC-3 satisfied (50-scenario summary <1000 tokens via anthropic.count_tokens against committed fixture)
- ROADMAP SC-4 satisfied for both refi (3-offer ranked table) AND amort (markdown table OR CSV path)
- ROADMAP SC-5 satisfied for all three agents (skills field + bundled-script filesystem reachability — gracefully skip if Phase 10 hasn't relocated scripts)
- SUBA-04 + SUBA-06 requirements closed in REQUIREMENTS.md tracking
- Phase 11's SC-1..SC-5 are now testable as green-bar regression gates (modulo Phase 10 / 11-04 branch (b) deferrals which have explicit pointer-back contracts)
- No AI attribution in any file or commit
</success_criteria>

<locked_decisions>
- **D-01: tokenizer = anthropic.Anthropic().messages.count_tokens.** Per RESEARCH Standard Stack: tiktoken cl100k_base is REJECTED (OpenAI-specific; ~5-20% drift on the <1k boundary). count_tokens is the official Claude tokenizer; FREE per Anthropic docs (separate rate limit, no content billing); requires ANTHROPIC_API_KEY at runtime (gate via skipif). Wave 0 already pinned the SDK version; this plan consumes it.
- **D-02: transcripts = synthetic, committed for CI determinism; live capture documented in references/subagent-routing.md but NOT run in CI.** Per RESEARCH Pitfall (live LLM calls in CI burn credits, are non-deterministic, break airgapped CI). Synthetic fixtures are hand-authored to match the canonical output shape from Plans 11-01..11-03 + token budget targets. Quarterly regeneration via the live-capture recipe (in fixture README) drift-checks reality against synthetic.
- **D-03: SC-3 budget exact threshold = 1000 tokens (assertion: response.input_tokens < 1000) — not 999, not 1001.** Matches the literal SC-3 wording in ROADMAP.md ("returns a summary < 1,000 tokens"). The synthetic fixture is deliberately at ~600 tokens (40% headroom) so future content edits don't push the test onto the knife edge; if real agent output legitimately requires >1000 tokens, surface as a Phase 12 follow-up rather than relaxing the threshold here.
- **D-04: SC-5 smoke = pytest assertion that os.path.exists('.claude/skills/mortgage-ops/scripts/{amortize,refi_npv,stress_test}.py') at test-collection time.** Per RESEARCH Pitfall 1: skills: is NOT a script-bundling mechanism — bundled scripts are filesystem files reached via Bash. SC-5 verifies (a) skills frontmatter equals ['mortgage-ops'] AND (b) bundled scripts exist on disk at the path the agent body references. If Phase 10 hasn't relocated scripts at test time, the script-existence check skips with an explicit Phase-10-pending reason (cross-phase tolerance, same pattern as Plan 11-04 branch b).
</locked_decisions>

<deviation_rules>
- If anthropic SDK changes the count_tokens response shape (`.input_tokens` → `.usage.input_tokens`): update the assertion to match; bump the SDK pin in pyproject.toml deliberately. Do NOT make the change in this plan unless the SDK shape has actually changed at execution time.
- If a synthetic fixture exceeds the 1000-token budget at hand-authoring time: trim the fixture (drop a highlight row; shorten the narrative). Do NOT relax the SC-3 threshold — D-03 pins it at <1000 strictly.
- If Plan 11-04 took branch (b) (SUBA-05 deferred to Phase 10): SUBA-05 remains xfail-with-TODO-reason after this plan. Do NOT touch the SUBA-05 stub in this plan.
- If a synthetic fixture's NPV-column-descending property is violated (e.g., during a hand-author iteration): the SUBA-04 refi assertion catches this immediately — re-author the fixture. Do NOT relax the assertion.
- If the SUBA-04 skills_field_resolves test fails the script-existence check on a real CI run AFTER Phase 10 has shipped: that is a Phase 10 SKLL-10 violation (scripts not in the skill folder). Surface as a Phase 10 gap, not a Phase 11 fix.
- If the live-capture recipe in the fixture README gets stale (claude -p flag changes; jq filter syntax changes): the recipe is informational only — fix in a docs-only follow-up plan; CI does NOT depend on the recipe being current.
</deviation_rules>

<dependencies>
**Wave 5 dependencies:**

- **Hard:** Wave 0 (Plan 11-00) — ships the four xfail stubs this plan flips + AGENTS_DIR/SKILLS_DIR/TRANSCRIPT_DIR constants + _split_frontmatter helper + the anthropic SDK dev-dep.
- **Hard:** Waves 1, 2, 3 (Plans 11-01..03) — ship the three .claude/agents/*.md files. SUBA-04 skills_field_resolves test reads each agent's frontmatter; the test fails if any agent file is missing.
- **Hard (informational):** Wave 4 (Plan 11-04) — determined whether SUBA-05 is passing (branch a) or deferred (branch b); this plan does NOT touch SUBA-05 but its truth statement about "no orphan xfails" depends on knowing the SUBA-05 state.
- **Soft (Phase 10):** SUBA-04 SC-5 part (b) skips gracefully if Phase 10 hasn't relocated scripts to .claude/skills/mortgage-ops/scripts/; the test passes once Phase 10 ships SKLL-10. SUBA-06 does NOT require Phase 10 — the transcript fixture is committed; only ANTHROPIC_API_KEY is needed.
- **Soft (Phase 8):** Phase 8's STRS-04 (scripts/stress_test.py) is referenced in the synthetic transcript's "Computed by:" line but the fixture content is hand-authored — it does NOT depend on the script existing. The SC-5 part (b) check would skip without it.

**Cross-phase HARD GATE for Phase 11 PHASE-CLOSEOUT:**
This plan is the Phase 11 closeout for SUBA-04 + SUBA-06. After it ships:
- SUBA-01, 02, 03, 04, 06 are CLOSED.
- SUBA-05 is either CLOSED (Plan 11-04 branch a) or DEFERRED-WITH-CONTRACT (Plan 11-04 branch b — Phase 10 honors the SUBA-05 contract on landing).
- ROADMAP SC-1..SC-5 all have measurable test gates.

**Downstream:**
- Wave 6 (Plan 11-06) ships references/subagent-routing.md + .claude/agents/README.md — references the live-capture recipe documented in this plan's fixture README; cross-links the SC-3 budget rationale.
- Phase 12 EVAL-03 / EVAL-04 — extends the eval harness to nightly-regenerate the transcript fixtures via live capture and diff against committed synthetic; if drift detected, Phase 12 surfaces as a regression. The committed fixtures are the v1 source-of-truth contract; Phase 12 evolves them.
</dependencies>

<output>
After completion, create `.planning/phases/11-subagents/11-05-SUMMARY.md` documenting:
- Three transcript fixture paths + their approx token counts (per anthropic.count_tokens — record actual numbers)
- README path + summary of sections added (live-capture recipe; synthetic-vs-live rationale; ANTHROPIC_API_KEY scope)
- Test flips: SUBA-04 (3 functions) + SUBA-06 (1 function) — final state per function (PASSED / SKIPPED with reason)
- SUBA-01..03 status (still PASSED — no regression)
- SUBA-05 status per Plan 11-04 branch (PASSED for branch a, XFAIL-with-TODO for branch b)
- Full suite status (≥379 + 7+ new passes + N skip + 0 fail + 0 error)
- mypy + ruff clean confirmation
- Confirmation: D-01 (anthropic.count_tokens, NOT tiktoken)
- Confirmation: D-02 (synthetic fixtures, NOT live in CI)
- Confirmation: D-03 (<1000 strict)
- Confirmation: D-04 (filesystem-reachability check, gracefully skip on Phase-10-pending)
- Confirmation: no Co-Authored-By in any file or commit
- Phase 11 SC-1..SC-5 measurable-gate status table
- Note: Phase 11 closeout candidate after Wave 6 (references) ships
</output>
