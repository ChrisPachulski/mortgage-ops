---
phase: 11
plan: 04
type: execute
wave: 4
depends_on:
  - "11-03"
files_modified:
  - .claude/skills/mortgage-ops/modes/stress.md
  - .claude/skills/mortgage-ops/SKILL.md
  - .planning/phases/11-subagents/11-04-SUBA-05-TODO.md
files_modified_conditional:
  - description: "If Phase 10 has NOT yet shipped .claude/skills/mortgage-ops/{SKILL.md,modes/stress.md}: Plan 11-04 ships ONLY the TODO marker file and DOES NOT create the skill files (that is Phase 10's responsibility per CLAUDE.md decision #8 / Phase 3 D-17 / 11-RESEARCH Pitfall 1). The TODO marker tells Phase 10 the exact lines/content to insert when SKILL.md + modes/stress.md are first authored."
autonomous: true
requirements:
  - SUBA-05
tags:
  - phase-11
  - subagents
  - skill-routing
  - cross-phase-update
  - suba-05
must_haves:
  truths:
    - "Either: (a) .claude/skills/mortgage-ops/modes/stress.md contains the literal SUBA-05 routing rule 'If scenario_count > 5, dispatch to stress-test-agent (see .claude/agents/stress-test-agent.md)' AND .claude/skills/mortgage-ops/SKILL.md cross-references the rule in its routing block, OR (b) Phase 10 has NOT yet shipped — in which case .planning/phases/11-subagents/11-04-SUBA-05-TODO.md exists and documents the exact insertion contract for Phase 10 to honor"
    - "The threshold is strictly >5 (D-01) — NOT ≥5, NOT ≥3, NOT >3 — to match the literal SC-2 / SUBA-05 wording in ROADMAP.md and REQUIREMENTS.md verbatim"
    - "The trigger phrasing 'Use proactively for stress sweeps with >5 scenarios' (Plan 11-03 D-04) is documented as the canonical agent-routing copy that Claude Code's auto-delegation reads at dispatch time"
    - "modes/stress.md (or the TODO marker) explicitly names .claude/agents/stress-test-agent.md by file path so the routing decision is unambiguous"
    - "Phase 10's planning notes are updated (or a planner-note added) to acknowledge the SUBA-05 contract Phase 11 imposes on Phase 10's modes/stress.md"
    - "Wave 0 stub test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent flips from xfail to passing (filesystem regex check against modes/stress.md OR — if branch (b) — remains xfail-skipped with a documented reason pointing at the TODO marker)"
  artifacts:
    - path: ".claude/skills/mortgage-ops/modes/stress.md"
      provides: "Phase 10-owned mode file extended by Phase 11 with the SUBA-05 >5 routing rule"
      condition: "ONLY if Phase 10 has shipped this file (branch (a)); otherwise see TODO marker artifact"
      contains: "scenario_count > 5"
    - path: ".claude/skills/mortgage-ops/SKILL.md"
      provides: "Phase 10-owned skill file with a routing-block cross-reference to modes/stress.md SUBA-05 rule"
      condition: "ONLY if Phase 10 has shipped this file (branch (a))"
      contains: "stress-test-agent"
    - path: ".planning/phases/11-subagents/11-04-SUBA-05-TODO.md"
      provides: "Cross-phase contract: exact text Phase 10 must insert into modes/stress.md + SKILL.md when those files are first authored. Always shipped (regardless of branch); branch (a) cites this file as the source-of-truth, branch (b) ships ONLY this file."
      min_lines: 50
  key_links:
    - from: ".claude/skills/mortgage-ops/modes/stress.md SUBA-05 routing block"
      to: ".claude/agents/stress-test-agent.md (Plan 11-03)"
      via: "explicit file-path reference; auto-delegation by Claude Code reads stress-test-agent.md description field"
      pattern: "stress-test-agent"
    - from: ".claude/skills/mortgage-ops/SKILL.md routing block"
      to: ".claude/skills/mortgage-ops/modes/stress.md SUBA-05 rule"
      via: "Phase 10 progressive-disclosure mode-file load on stress-mode dispatch"
      pattern: "modes/stress.md"
    - from: ".planning/phases/11-subagents/11-04-SUBA-05-TODO.md"
      to: "Phase 10 SKLL-05 (modes file authoring) + SKLL-01 (SKILL.md routing block authoring)"
      via: "cross-phase contract document — Phase 10 reads this at planning time"
      pattern: "SUBA-05"
    - from: "tests/test_subagents.py test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent"
      to: ".claude/skills/mortgage-ops/modes/stress.md OR TODO marker"
      via: "regex check from Wave 0 (per RESEARCH Code Example 4 line ~440); pattern matches '(scenarios? (>|more than|greater than) 5|scenario_count > 5).*(stress-test-agent|subagent)'"
      pattern: "scenario_count > 5"
---

<objective>
Wire the SUBA-05 routing rule (>5-scenario stress sweeps dispatch to stress-test-agent) into the Phase 10 SKILL.md / modes/stress.md surface. **This is a cross-phase update** — Phase 11 plans the contract; Phase 10 ships the underlying skill files. If Phase 10 has already shipped the relevant files, Plan 11-04 EXTENDS them in-place. If Phase 10 has NOT yet shipped, Plan 11-04 ships a planner TODO marker (`11-04-SUBA-05-TODO.md`) that Phase 10 honors when authoring SKILL.md + modes/stress.md. Closes SUBA-05.

Purpose: SUBA-05 is the routing seam that makes SC-2 ("Stress mode in SKILL.md routes any sweep with >5 scenarios to stress-test-agent") testable. Without this rule wired into modes/stress.md, the stress-test-agent (Plan 11-03) is dead code — Claude Code's auto-delegation would never dispatch to it. The rule lives at the skill layer (Phase 10 territory) but is contractually owned by Phase 11 because (a) the threshold (>5) is a SUBA-05 requirement, (b) the agent name (`stress-test-agent`) is a Phase 11 deliverable, and (c) the routing pattern is the entire reason Phase 11 exists. Per 11-PATTERNS.md Critical Issue #1c + threshold-routing pattern from career-ops/.claude/skills/career-ops/SKILL.md:84-93 (the only in-tree analog for threshold-based delegation, even though career-ops uses a different dispatch mechanism).

Output: Either (a) two file edits (modes/stress.md + SKILL.md) plus the TODO marker for traceability, OR (b) just the TODO marker if Phase 10 hasn't shipped yet. The Wave 0 SUBA-05 test either passes (branch a) or remains xfail-skipped with a documented Phase-10-pending reason (branch b).
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
@.planning/phases/11-subagents/11-03-stress-test-agent-PLAN.md
@.planning/phases/10-claude-skill/10-PATTERNS.md
@.planning/phases/10-claude-skill/10-RESEARCH.md

<interfaces>
**SUBA-05 / SC-2 contract (verbatim from ROADMAP.md:206 + REQUIREMENTS.md:153):**

> "Stress mode in SKILL.md routes any sweep with > 5 scenarios to `stress-test-agent` (documented in modes/stress.md and tested by an eval prompt)" — ROADMAP SC-2

> "SUBA-05: Stress mode invokes stress-test-agent for sweeps > 5 scenarios" — REQUIREMENTS.md:153

The threshold is **strictly > 5** (per Plan 11-04 LOCKED DECISION D-01; matches the literal text of both source documents). Sweeps with exactly 5 scenarios stay on the main thread. This deliberately differs from career-ops's threshold-based delegation precedent at `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md:84-93` which uses a "≥3 URLs" threshold for its `pipeline` mode — mortgage-ops chooses ">5" because that is the literal SC-2 wording, not because we believe 5 is the right cutoff per se. The career-ops pattern is the structural precedent for threshold-based delegation; the specific number is mortgage-ops's call.

**Cross-phase update protocol (LOCKED via D-02):**

This plan touches Phase 10's deliverables (SKILL.md + modes/stress.md) which Phase 10 has NOT yet implemented (`.planning/phases/10-claude-skill/` contains only PATTERNS, RESEARCH, UI-SPEC; no PLAN files yet). Two execution branches:

- **Branch (a) — Phase 10 has shipped at execution time:** Edit modes/stress.md and SKILL.md in-place. Insert the literal SUBA-05 routing rule into modes/stress.md and a one-line cross-reference into SKILL.md's routing block. The Wave 0 SUBA-05 test passes via the regex check from RESEARCH Code Example 4 (lines ~440-452). Always also ship the TODO marker file as a traceability record of the cross-phase contract.

- **Branch (b) — Phase 10 has NOT shipped at execution time:** Ship ONLY the TODO marker file (`.planning/phases/11-subagents/11-04-SUBA-05-TODO.md`). The TODO marker contains the EXACT insertion contract Phase 10 must honor when authoring SKILL.md + modes/stress.md. The Wave 0 SUBA-05 test remains xfail-skipped with a docstring reason pointing at the TODO marker. Phase 10's planner reads the TODO marker and bakes the SUBA-05 rule into modes/stress.md + SKILL.md at SKLL-01 / SKLL-05 time. After Phase 10 ships, a follow-up plan (Phase 10 closeout or a Phase 11 cleanup plan) flips the xfail to passing.

The executor decides which branch by running `test -d .claude/skills/mortgage-ops/modes/` at task start.

**Insertion contract for branch (a) — exact text:**

For `.claude/skills/mortgage-ops/modes/stress.md` — append the following block at the end of the existing routing/dispatch section (or the end of the file if no routing section exists):

```markdown
## Subagent dispatch (SUBA-05)

If `scenario_count > 5`, dispatch to `stress-test-agent` (see `.claude/agents/stress-test-agent.md`).
The agent receives the sweep request, invokes `scripts/stress_test.py` once with the full grid,
and returns a ≤1,000-token summary to the main context (Phase 11 SC-2 + SC-3 contract).

Sweeps with 5 or fewer scenarios stay on the main thread — the dispatch overhead is not worth
it for outputs that fit in main context (≤500 tokens for typical 5-scenario sweeps).

The exact routing trigger Claude Code reads at dispatch time is the `description:` field of
`.claude/agents/stress-test-agent.md`, which begins: "Use proactively for stress sweeps with
>5 scenarios..." (Plan 11-03 LOCKED DECISION D-04). Do not duplicate the trigger phrasing
here — describe the routing decision in plain prose so this mode file stays a routing map,
not a copy of the agent file.
```

For `.claude/skills/mortgage-ops/SKILL.md` — within the routing decision table or routing block (whatever shape Phase 10 lands on per their SKLL-01 / SKLL-02 design), add a row or one-line reference equivalent to:

```markdown
| stress | parameter sweeps | If scenario_count > 5 → dispatch to `stress-test-agent` (see `modes/stress.md`); else inline |
```

OR (if Phase 10 uses a prose routing block instead of a table):

```markdown
- **stress mode**: Routes parameter-grid sweeps. Sweeps with >5 scenarios dispatch to
  `stress-test-agent` per the SUBA-05 rule (full text in `modes/stress.md`); sweeps with
  ≤5 scenarios run inline.
```

The exact wording can be adapted to Phase 10's chosen routing-block style — the load-bearing requirements are: (i) names the >5 threshold, (ii) names `stress-test-agent` by exact agent-file name, (iii) cross-links to `modes/stress.md` for the full rule.

**Insertion contract for branch (b):** the TODO marker file (`11-04-SUBA-05-TODO.md`) contains both blocks above verbatim, plus a "Phase 10 acceptance criteria" section: when Phase 10 ships modes/stress.md + SKILL.md, the SUBA-05 regex test must pass against modes/stress.md (per Wave 0 SUBA-05 stub).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create the SUBA-05 cross-phase TODO marker (always — branch a or b)</name>
  <files>.planning/phases/11-subagents/11-04-SUBA-05-TODO.md</files>
  <read_first>
    - 11-PATTERNS.md "Threshold-based dispatch" pattern (career-ops/.claude/skills/career-ops/SKILL.md:84-93 precedent)
    - 11-RESEARCH.md Open Question #2 (where exactly the >5 routing rule lives — both SKILL.md and modes/stress.md)
    - 11-RESEARCH.md Open Question #3 (off-by-one risk — strictly >5 not ≥5)
    - .planning/phases/10-claude-skill/10-PATTERNS.md (Phase 10's planned mode-file structure)
    - .planning/phases/10-claude-skill/10-RESEARCH.md (Phase 10's SKILL.md routing-block design)
  </read_first>
  <action>
    Create the file `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md`. This file is **always** shipped (regardless of branch) so the cross-phase contract is documented in Phase 11's planning record forever, not just inferable from a one-off SKILL.md edit.

    File content (write verbatim):

    ```markdown
    # SUBA-05 Cross-Phase Routing Contract

    **Owner:** Phase 11 (Subagents) — Plan 11-04
    **Consumed by:** Phase 10 (Claude Skill Frontend) — SKLL-01 (SKILL.md routing block) + SKLL-05 (modes/stress.md mode file)
    **Status (set by Plan 11-04 executor):** [TODO: executor sets to (a) WIRED IN-PLACE | (b) AWAITING PHASE 10]
    **Threshold:** strictly `> 5` (LOCKED DECISION D-01 — see Plan 11-04 LOCKED DECISIONS section)

    ## What this contract requires

    When Phase 10 authors `.claude/skills/mortgage-ops/SKILL.md` and `.claude/skills/mortgage-ops/modes/stress.md`,
    those files MUST contain the SUBA-05 routing rule wiring stress mode to `stress-test-agent`
    (`.claude/agents/stress-test-agent.md`, shipped by Plan 11-03) for sweeps with >5 scenarios.

    This is the seam that makes SC-2 / SUBA-05 testable. Without it, `stress-test-agent` is dead code:
    Claude Code's auto-delegation reads agent `description:` fields, but the SKILL.md routing layer is
    where mode-level dispatch decisions live (per 11-RESEARCH.md Open Question #2 — both SKILL.md and
    modes/stress.md document the rule, with modes/stress.md as the canonical full-text location).

    ## Insertion text — modes/stress.md

    Append the following block at the end of the existing routing/dispatch section of `modes/stress.md`
    (or the end of the file if no routing section exists yet):

    ```markdown
    ## Subagent dispatch (SUBA-05)

    If `scenario_count > 5`, dispatch to `stress-test-agent` (see `.claude/agents/stress-test-agent.md`).
    The agent receives the sweep request, invokes `scripts/stress_test.py` once with the full grid,
    and returns a ≤1,000-token summary to the main context (Phase 11 SC-2 + SC-3 contract).

    Sweeps with 5 or fewer scenarios stay on the main thread — the dispatch overhead is not worth
    it for outputs that fit in main context (≤500 tokens for typical 5-scenario sweeps).

    The exact routing trigger Claude Code reads at dispatch time is the `description:` field of
    `.claude/agents/stress-test-agent.md`, which begins: "Use proactively for stress sweeps with
    >5 scenarios..." (Plan 11-03 LOCKED DECISION D-04). Do not duplicate the trigger phrasing
    here — describe the routing decision in plain prose so this mode file stays a routing map,
    not a copy of the agent file.
    ```

    ## Insertion text — SKILL.md routing block

    Within Phase 10's chosen routing-block shape (per SKLL-01 / SKLL-02 design — table-form or
    prose-form), add a row or one-line reference for stress mode that names the >5 threshold and
    the agent file. Example for table-form routing block:

    ```markdown
    | stress | parameter sweeps | If scenario_count > 5 → dispatch to `stress-test-agent` (see `modes/stress.md`); else inline |
    ```

    Example for prose-form routing block:

    ```markdown
    - **stress mode**: Routes parameter-grid sweeps. Sweeps with >5 scenarios dispatch to
      `stress-test-agent` per the SUBA-05 rule (full text in `modes/stress.md`); sweeps with
      ≤5 scenarios run inline.
    ```

    The load-bearing requirements (whichever shape is used):

    1. Names the **strictly >5** threshold (NOT ≥5, NOT >3, NOT ≥3 — these are wrong per D-01).
    2. Names **`stress-test-agent`** by exact agent-file basename (matches `.claude/agents/stress-test-agent.md`).
    3. Cross-links to **`modes/stress.md`** so a reader following the routing breadcrumb finds the full rule.
    4. Stays within Phase 10's SKLL-02 routing-first-200-lines budget — this addition is one row or one bullet, ~30 tokens.

    ## Why this is a Phase 11 contract owned by Plan 11-04 (not authored directly by Phase 10)

    Phase 11 is the source of truth for:
    - The threshold value (>5 — pinned by SC-2 / SUBA-05 / Plan 11-04 D-01).
    - The agent file name (`stress-test-agent` — Plan 11-03 ships the file).
    - The trigger phrasing (`Use proactively for stress sweeps with >5 scenarios` — Plan 11-03 D-04).
    - The output budget (≤1,000 tokens — Plan 11-03 D-03 enforced by Plan 11-05's SC-3 test).

    Phase 10 is the authoring surface for SKILL.md + modes/stress.md. Phase 11 cannot author Phase 10's
    files directly without committing a layering violation (Phase 11 would have to invent the SKILL.md
    routing-block shape Phase 10 hasn't designed yet). Hence: Phase 11 ships the contract; Phase 10
    honors it.

    ## Phase 10 acceptance criteria for honoring this contract

    When Phase 10 has shipped SKILL.md + modes/stress.md with the SUBA-05 wiring:

    1. `grep -E '(scenarios?\\s*(>|more than|greater than)\\s*5|scenario[_ ]count\\s*>\\s*5).*(stress-test-agent|subagent)' .claude/skills/mortgage-ops/modes/stress.md` returns a match.
    2. `grep -c 'stress-test-agent' .claude/skills/mortgage-ops/SKILL.md` returns ≥ 1.
    3. `grep -c 'modes/stress.md' .claude/skills/mortgage-ops/SKILL.md` returns ≥ 1 (cross-link from SKILL.md to the full rule).
    4. The Wave 0 stub `tests/test_subagents.py::test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent` passes (the xfail decorator is removed; the regex from RESEARCH Code Example 4 matches).
    5. SKILL.md still satisfies SKLL-01 (≤500 lines, ≤5,000 tokens) and SKLL-02 (routing in first 200 lines) after the addition.

    Once Phase 10 satisfies all five criteria, mark this TODO file's Status header as **(a) WIRED**
    and update Plan 11-04's SUMMARY accordingly.

    ## Branch — what Plan 11-04 executor actually did

    [TODO: executor fills this in at task time. Two valid outcomes:]

    **(a) WIRED IN-PLACE — Phase 10 had shipped at execution time.**
    - Edited `.claude/skills/mortgage-ops/modes/stress.md` to insert the SUBA-05 routing block above.
    - Edited `.claude/skills/mortgage-ops/SKILL.md` to add the routing-block cross-reference.
    - Wave 0 SUBA-05 test xfail decorator removed; test passes.
    - This TODO marker remains as the canonical traceability record.

    **(b) AWAITING PHASE 10 — Phase 10 had not yet shipped at execution time.**
    - This TODO marker file is the only deliverable. modes/stress.md and SKILL.md edits deferred to Phase 10.
    - Wave 0 SUBA-05 test xfail decorator updated with a docstring reason pointing at this TODO marker.
    - Phase 10 planner is responsible for reading this file and baking the contract into SKILL.md + modes/stress.md.
    - A Phase 10 closeout plan (or a follow-up Phase 11 cleanup plan) flips the SUBA-05 xfail when Phase 10 lands.
    ```

    Critical details:
    - File is the cross-phase contract — it is the **canonical record** even after Phase 10 ships and the SKILL.md edits are in-place. Do not delete this file at any later wave.
    - The "what Plan 11-04 executor actually did" section MUST be filled in at execution time per branch (a) or (b).
    - No Co-Authored-By in the file or in the commit message.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .planning/phases/11-subagents/11-04-SUBA-05-TODO.md &amp;&amp; test $(wc -l &lt; .planning/phases/11-subagents/11-04-SUBA-05-TODO.md) -ge 50 &amp;&amp; grep -c 'scenario_count > 5' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md &amp;&amp; grep -c 'stress-test-agent' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md &amp;&amp; grep -c 'modes/stress.md' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md</automated>
  </verify>
  <acceptance_criteria>
    - `test -f .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` exits 0
    - `wc -l .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns at least 50
    - `grep -c 'scenario_count > 5' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns at least 2 (insertion text for modes/stress.md + acceptance criteria)
    - `grep -c 'stress-test-agent' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns at least 4
    - `grep -c 'modes/stress.md' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns at least 3
    - `grep -ci 'co-authored-by' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns 0
    - `grep -c 'SUBA-05' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns at least 5 (heavy ID-cross-referencing for traceability)
  </acceptance_criteria>
  <done>
    Cross-phase TODO marker exists with the verbatim insertion text for both modes/stress.md and SKILL.md, the load-bearing requirements list, the Phase 10 acceptance criteria, and the branch-(a)-or-(b) field for the executor to fill in. No AI attribution.
  </done>
</task>

<task type="auto">
  <name>Task 2: Conditionally wire SUBA-05 into modes/stress.md + SKILL.md (branch a only — gated by Phase 10 file existence)</name>
  <files>.claude/skills/mortgage-ops/modes/stress.md, .claude/skills/mortgage-ops/SKILL.md</files>
  <read_first>
    - .planning/phases/11-subagents/11-04-SUBA-05-TODO.md (just created in Task 1) — the canonical insertion text
    - .claude/skills/mortgage-ops/modes/stress.md (if it exists — Phase 10's mode file shape determines exact insertion location)
    - .claude/skills/mortgage-ops/SKILL.md (if it exists — Phase 10's routing-block shape determines table-form vs prose-form choice)
  </read_first>
  <action>
    **First decide branch (a) vs (b)** by running:

    ```bash
    test -f .claude/skills/mortgage-ops/modes/stress.md && test -f .claude/skills/mortgage-ops/SKILL.md && echo "branch-a" || echo "branch-b"
    ```

    **If branch-b ("Phase 10 not shipped"):** STOP this task. Mark Task 2 as deferred. Edit `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md` to set the Status header to `(b) AWAITING PHASE 10` and fill in the "Branch (b)" section. ALSO edit `tests/test_subagents.py` SUBA-05 stub: keep the xfail decorator but UPDATE its `reason=` string to point at the TODO marker:

    ```python
    @pytest.mark.xfail(strict=True, reason="Plan 11-04 deferred SUBA-05 wiring to Phase 10 — see .planning/phases/11-subagents/11-04-SUBA-05-TODO.md for the cross-phase contract; flip this xfail when Phase 10 ships SKILL.md + modes/stress.md with the SUBA-05 rule")
    ```

    **If branch-a ("Phase 10 has shipped"):** proceed with the edits below.

    **Edit 1 — append SUBA-05 block to .claude/skills/mortgage-ops/modes/stress.md:**

    Locate the end of the existing routing/dispatch section (or the end of the file if no routing section exists). Append the following block VERBATIM (this matches the insertion text in the TODO marker):

    ```markdown

    ## Subagent dispatch (SUBA-05)

    If `scenario_count > 5`, dispatch to `stress-test-agent` (see `.claude/agents/stress-test-agent.md`).
    The agent receives the sweep request, invokes `scripts/stress_test.py` once with the full grid,
    and returns a ≤1,000-token summary to the main context (Phase 11 SC-2 + SC-3 contract).

    Sweeps with 5 or fewer scenarios stay on the main thread — the dispatch overhead is not worth
    it for outputs that fit in main context (≤500 tokens for typical 5-scenario sweeps).

    The exact routing trigger Claude Code reads at dispatch time is the `description:` field of
    `.claude/agents/stress-test-agent.md`, which begins: "Use proactively for stress sweeps with
    >5 scenarios..." (Plan 11-03 LOCKED DECISION D-04). Do not duplicate the trigger phrasing
    here — describe the routing decision in plain prose so this mode file stays a routing map,
    not a copy of the agent file.
    ```

    **Edit 2 — add routing-block cross-reference to .claude/skills/mortgage-ops/SKILL.md:**

    Read the existing SKILL.md routing block to determine its shape (table-form or prose-form).

    - If table-form (markdown table with mode | description | dispatch columns): add a new row OR amend the existing `stress` row to include the SUBA-05 dispatch column. Use the exact text:
      `If scenario_count > 5 → dispatch to \`stress-test-agent\` (see \`modes/stress.md\`); else inline`

    - If prose-form (bulleted list): add a sub-bullet (or amend the existing stress-mode bullet) to include:
      `Sweeps with >5 scenarios dispatch to \`stress-test-agent\` per the SUBA-05 rule (full text in \`modes/stress.md\`)`

    Critical constraint: SKILL.md MUST still satisfy SKLL-01 (≤500 lines, ≤5,000 tokens) and SKLL-02 (routing logic in first 200 lines) after this edit. The addition is ~30 tokens; it should land within the routing block (already in the first 200 lines per Phase 10 design).

    **Edit 3 — flip the Wave 0 SUBA-05 xfail to a passing assertion in tests/test_subagents.py:**

    Remove the `@pytest.mark.xfail(...)` decorator. Replace the body with the regex check from RESEARCH Code Example 4 lines ~440-452 (which the Wave 0 stub already mirrors structurally):

    ```python
    def test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent() -> None:
        """SUBA-05 + ROADMAP SC-2: modes/stress.md documents the >5 scenario dispatch rule.

        Per Plan 11-04 LOCKED DECISION D-01: threshold is strictly >5 (matches the literal SC-2
        text); D-02: cross-phase update protocol (this branch executed because Phase 10 had
        shipped at task time).
        """
        stress_md_path = SKILLS_DIR / "modes" / "stress.md"
        assert stress_md_path.exists(), (
            f"SUBA-05: {stress_md_path} must exist (Phase 10 SKLL-05 dependency); "
            "if Phase 10 has not yet shipped, see .planning/phases/11-subagents/11-04-SUBA-05-TODO.md"
        )
        stress_md = stress_md_path.read_text()
        # Regex matches phrasings: "scenarios > 5", "more than 5 scenarios",
        # "scenario_count > 5" — pinned by an explicit positive assertion.
        pattern = re.compile(
            r"(scenarios?\s*(>|more than|greater than)\s*5|scenario[_ ]count\s*>\s*5).*"
            r"(stress-test-agent|subagent)",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(stress_md), (
            "SUBA-05: modes/stress.md must document 'sweeps with > 5 scenarios route to stress-test-agent' "
            "per the insertion contract in .planning/phases/11-subagents/11-04-SUBA-05-TODO.md"
        )
        # SKILL.md cross-reference assertion — Phase 10 surface MUST cite the agent name
        # so the routing breadcrumb is followable from SKILL.md → modes/stress.md → agent file.
        skill_md = (SKILLS_DIR / "SKILL.md").read_text()
        assert "stress-test-agent" in skill_md, (
            "SUBA-05: SKILL.md must cross-reference stress-test-agent in its routing block "
            "(per Plan 11-04 SKILL.md insertion contract)"
        )
    ```

    **Final step (both branches):** Update `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md` "Branch — what Plan 11-04 executor actually did" section to set the Status header and fill in the (a) or (b) checklist.

    No Co-Authored-By in any commit. CLAUDE.md global rule.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; (if test -f .claude/skills/mortgage-ops/modes/stress.md &amp;&amp; test -f .claude/skills/mortgage-ops/SKILL.md; then \
      grep -E '(scenarios?[[:space:]]*(>|more than|greater than)[[:space:]]*5|scenario_count[[:space:]]*>[[:space:]]*5).*stress-test-agent' .claude/skills/mortgage-ops/modes/stress.md &amp;&amp; \
      grep -c 'stress-test-agent' .claude/skills/mortgage-ops/SKILL.md &amp;&amp; \
      uv run pytest tests/test_subagents.py::test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent -v 2>&amp;1 | tail -5; \
    else \
      echo "branch-b: Phase 10 not shipped — verifying TODO marker is updated and SUBA-05 xfail remains" &amp;&amp; \
      grep -c '11-04-SUBA-05-TODO.md' tests/test_subagents.py &amp;&amp; \
      grep -c 'AWAITING PHASE 10\|WIRED IN-PLACE' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md; \
    fi)</automated>
  </verify>
  <acceptance_criteria>
    - **Branch (a) — Phase 10 shipped:**
      - `grep -E '(scenarios?[[:space:]]*(>|more than|greater than)[[:space:]]*5|scenario_count[[:space:]]*>[[:space:]]*5).*stress-test-agent' .claude/skills/mortgage-ops/modes/stress.md` returns a match
      - `grep -c 'stress-test-agent' .claude/skills/mortgage-ops/SKILL.md` returns ≥ 1
      - `grep -c 'modes/stress.md' .claude/skills/mortgage-ops/SKILL.md` returns ≥ 1
      - `wc -l .claude/skills/mortgage-ops/SKILL.md` returns ≤ 500 (SKLL-01 still satisfied)
      - `uv run pytest tests/test_subagents.py::test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent -v 2>&1 | grep -c PASSED` returns 1
      - `grep -B1 'def test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent' tests/test_subagents.py | grep -c xfail` returns 0
      - `grep -c 'WIRED IN-PLACE' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns ≥ 1
    - **Branch (b) — Phase 10 not shipped:**
      - `test -f .claude/skills/mortgage-ops/modes/stress.md` exits non-zero (file genuinely absent)
      - `grep -c '11-04-SUBA-05-TODO.md' tests/test_subagents.py` returns ≥ 1 (xfail reason updated to point at TODO marker)
      - `uv run pytest tests/test_subagents.py::test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent -v 2>&1 | grep -c XFAIL` returns 1
      - `grep -c 'AWAITING PHASE 10' .planning/phases/11-subagents/11-04-SUBA-05-TODO.md` returns ≥ 1
    - **Both branches:**
      - SUBA-01, SUBA-02, SUBA-03 still pass: `uv run pytest tests/test_subagents.py -v --tb=no 2>&1 | grep -cE '(test_SUBA_0[123]_).*PASSED'` returns 3
      - SUBA-04 + SUBA-06 still xfail/skip
      - Full suite still green: `uv run pytest -q 2>&1 | tail -3 | grep -cE '[0-9]+ failed' | grep -v '0 failed'` returns 0
      - `uv run mypy --strict tests/test_subagents.py` exits 0 (branch a only — branch b makes no test changes beyond xfail-reason update)
      - `uv run ruff check tests/test_subagents.py` exits 0
  </acceptance_criteria>
  <done>
    Either (a) modes/stress.md + SKILL.md edited in-place with the SUBA-05 routing rule, the SUBA-05 test flipped from xfail to passing, and the TODO marker Status set to "WIRED IN-PLACE"; OR (b) the TODO marker Status set to "AWAITING PHASE 10", the SUBA-05 test xfail-reason updated to point at the TODO marker, and the file edits explicitly deferred to Phase 10 with a clear executor-recorded reason. SUBA-01, SUBA-02, SUBA-03 all still pass; full suite green; no AI attribution.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Plan 11-04 → Phase 10 deliverables | Plan 11-04 modifies (or contracts to modify) Phase 10's owned files; layering violation risk if Phase 11 invents Phase 10's design |
| modes/stress.md SUBA-05 block → routing semantics | Off-by-one threshold drift (≥5 vs >5) silently breaks SC-2 |
| SKILL.md routing-block edit → SKLL-01 budget | Phase 11 addition could push SKILL.md past 500 lines / 5k tokens, breaking Phase 10 SC-1 |
| TODO marker → Phase 10 planner | If Phase 10 planner doesn't read the marker, the SUBA-05 rule never lands and SC-2 fails |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-23 | Tampering (threshold drift — someone changes >5 to ≥5 or >3) | modes/stress.md SUBA-05 block | mitigate | Plan 11-04 D-01 explicitly pins strictly >5; the SUBA-05 regex test asserts the literal pattern; the TODO marker documents the rationale (matches literal SC-2 wording) |
| T-11-24 | Information Disclosure (Phase 10 planner doesn't read the TODO marker, ships modes/stress.md without SUBA-05 wiring) | TODO marker file → Phase 10 planning workflow | mitigate | Marker filename starts with `11-04-SUBA-05-` so it's discoverable via standard glob `.planning/phases/*/`-prefix scans; Phase 10 PLAN-CHECK should grep for "SUBA-05" cross-references; the Wave 0 SUBA-05 xfail remains the failing-loud regression gate |
| T-11-25 | Tampering (SKILL.md insertion blows past SKLL-01 500-line / 5k-token budget) | SKILL.md routing block edit | mitigate | Insertion is ≤30 tokens (one row or one bullet); branch (a) verify includes `wc -l ≤ 500` check; if Phase 10's SKILL.md is already at the limit, the edit fails the budget check and the executor falls back to branch (b) (defer to Phase 10) |
| T-11-26 | Repudiation (modes/stress.md insertion drifts from the TODO marker text) | modes/stress.md insertion content | mitigate | TODO marker contains the verbatim insertion text; branch (a) action explicitly references the TODO marker as the source of truth; the SUBA-05 regex test catches semantic drift but not character-level diff (acceptable trade-off — semantic correctness is what SC-2 measures) |
| T-11-27 | Tampering (executor picks branch (a) when files exist but are placeholder/stub Phase-10-WIP files, polluting Phase 10's WIP) | branch detection logic | accept | Branch detection is a simple `test -f` — if Phase 10 has shipped WIP placeholders, that is Phase 10's problem to clean up. The TODO marker remains as the canonical contract regardless. |
</threat_model>

<verification>
- `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md` always exists with the verbatim cross-phase insertion contract (Task 1)
- Either (branch a) modes/stress.md contains `scenario_count > 5` + `stress-test-agent` per the regex pattern, OR (branch b) the TODO marker Status header is `AWAITING PHASE 10` and the SUBA-05 xfail-reason points at the TODO marker
- Either (branch a) SKILL.md contains `stress-test-agent` and `modes/stress.md` cross-references AND SKILL.md is ≤ 500 lines (SKLL-01 preserved), OR (branch b) no SKILL.md edit
- SUBA-01, SUBA-02, SUBA-03 still pass; SUBA-04 + SUBA-06 still xfail/skip
- Full suite green; mypy + ruff clean
- D-01 (>5 strictly) honored in all wired text
- D-02 (cross-phase update protocol) executed correctly per the branch detected at task time
- No Co-Authored-By in any file or commit
</verification>

<success_criteria>
- ROADMAP SC-2 satisfied via either branch (a) live regex match against modes/stress.md OR branch (b) documented Phase 10 contract that will satisfy SC-2 once Phase 10 ships
- SUBA-05 requirement closed (branch a) OR contractually-deferred-with-tracking (branch b)
- Cross-phase TODO marker is the single source of truth for the SUBA-05 contract; survives forever as a planning record
- Plan 11-03's stress-test-agent is no longer dead code (branch a) OR has a documented activation path (branch b)
- No AI attribution in any file or commit
</success_criteria>

<locked_decisions>
- **D-01: trigger threshold = strictly > 5.** Career-ops uses ≥3 URLs as its threshold (per `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md:84-93` — the only in-tree threshold-routing precedent). Mortgage-ops chooses >5 because that is the literal SC-2 / SUBA-05 text in ROADMAP.md and REQUIREMENTS.md, not because we believe 5 is the "right" cutoff. Sweeps with exactly 5 scenarios stay on the main thread. Off-by-one risk surfaced in 11-RESEARCH.md Open Question #3 — pinned here.
- **D-02: cross-phase update protocol.** When Phase 11 plans modify Phase 10 deliverables, the executor checks Phase 10 file existence at task time. If files exist (branch a): edit in-place + ship the TODO marker as canonical record. If files do NOT exist (branch b): ship ONLY the TODO marker; defer file edits to Phase 10's authoring workflow; update the relevant Wave 0 xfail's `reason=` string to point at the TODO marker. This protocol is generic and reusable for any future cross-phase update plan.
</locked_decisions>

<deviation_rules>
- If Phase 10 has shipped modes/stress.md but with a routing structure that would conflict with the SUBA-05 block (e.g., a different routing rule for `scenarios > 3`): do NOT silently override. STOP and surface as a follow-up plan that aligns Phase 10's existing routing with the SUBA-05 contract. The TODO marker Status becomes "(c) CONFLICT — see follow-up plan".
- If SKILL.md is already at the 500-line limit per SKLL-01: branch (a) edit fails the wc -l check; fall back to branch (b) and add to the TODO marker a "Phase 10 must compress SKILL.md by 1+ line before adding the SUBA-05 reference" note.
- If Phase 10 ships modes/stress.md WITH the SUBA-05 rule already inserted (anticipating Plan 11-04): branch (a) Edit 1 should detect the existing rule via grep and skip insertion (idempotency); the SUBA-05 regex test already passes; mark the TODO marker as "(a) WIRED — by Phase 10 directly".
- If a strict YAML/markdown linter complains about the inserted block formatting: the insertion is plain markdown (## heading + paragraphs + code-fence-free prose); should not trip standard mortgage-ops linting. If it does, normalize whitespace but do NOT change the load-bearing tokens (`scenario_count > 5`, `stress-test-agent`, `modes/stress.md`).
</deviation_rules>

<dependencies>
**Wave 4 dependencies:**

- **Hard:** Wave 3 (Plan 11-03) must be complete. Plan 11-03 ships `.claude/agents/stress-test-agent.md` and the D-04 trigger phrase (`Use proactively for stress sweeps with >5 scenarios`). The TODO marker references both by exact name; the modes/stress.md insertion block references `.claude/agents/stress-test-agent.md` by file path.
- **Hard:** Wave 0 (Plan 11-00) must be complete. Wave 0 ships the SUBA-05 stub + `SKILLS_DIR` constant.
- **Conditional Hard (Phase 10):** Branch (a) execution requires Phase 10 to have shipped `.claude/skills/mortgage-ops/SKILL.md` + `.claude/skills/mortgage-ops/modes/stress.md`. Branch (b) execution explicitly does NOT require Phase 10. The branch detection at task time (`test -f`) selects the correct path.
- **Soft (Phase 8):** Indirectly — the modes/stress.md insertion mentions `scripts/stress_test.py`, which Phase 8 ships. The reference is descriptive (the agent will invoke this script) and does not require the script to exist for Plan 11-04 to ship.

**Cross-phase HARD GATE for ROADMAP SC-2 satisfaction:**
SC-2 (verbatim: "Stress mode in SKILL.md routes any sweep with > 5 scenarios to stress-test-agent") is satisfied when branch (a) executes — modes/stress.md contains the regex-matchable rule AND SKILL.md cross-references it. If branch (b) executes, SC-2 is contractually-deferred-pending-Phase-10. Phase 11's verification phase must check this distinction explicitly.

**Downstream:**
- Wave 5 (Plan 11-05) ships the broader SUBA-04..06 test suite + transcript fixtures. The SUBA-05 regex test from this plan (Task 2 branch a) is preserved and parametrized further; SUBA-06 (50-scenario summary <1k tokens) consumes a recorded transcript fixture for the agent dispatched by THIS plan's routing rule.
- Wave 6 (Plan 11-06) ships `references/subagent-routing.md` which documents the >5 threshold rationale + the cross-phase TODO marker workflow as a pattern.
- Phase 10 itself: once Phase 10 ships modes/stress.md + SKILL.md (regardless of which Wave 4 branch executed), Phase 10's planner reads the TODO marker and either (i) confirms the rule is already wired (branch a) or (ii) bakes it in at SKLL-01 / SKLL-05 time (branch b). The TODO marker Status header is updated accordingly.
</dependencies>

<output>
After completion, create `.planning/phases/11-subagents/11-04-SUMMARY.md` documenting:
- Path to TODO marker: `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md` (always shipped)
- Branch executed: (a) WIRED IN-PLACE | (b) AWAITING PHASE 10 — with explicit reason
- If branch (a):
  - modes/stress.md edit: line-count delta + the inserted block's first/last lines for verification
  - SKILL.md edit: line-count delta + the inserted line/row for verification
  - SKILL.md still satisfies SKLL-01 (≤500 lines, ≤5k tokens) post-edit
  - SUBA-05 test xfail flip: PASSED status confirmation
- If branch (b):
  - Confirmation that no edits to Phase 10 files were made
  - Confirmation that SUBA-05 xfail reason was updated to point at the TODO marker
  - Forward-pointer: when Phase 10 ships, what closes this loop (SUBA-05 xfail flip in a follow-up plan)
- Wave 1 SUBA-01, Wave 2 SUBA-02, Wave 3 SUBA-03 all still PASSED (no regression)
- SUBA-04 + SUBA-06 still xfail/skip
- Full suite status (≥379 + N new passes + M xfail/skip + 0 fail + 0 error)
- D-01 (>5 strictly) honored in inserted text (branch a) or TODO marker text (branch b)
- D-02 (cross-phase update protocol) execution record
- Confirmation: no Co-Authored-By in any file or commit message
</output>
