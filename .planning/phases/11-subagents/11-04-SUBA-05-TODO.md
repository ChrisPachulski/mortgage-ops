# SUBA-05 Cross-Phase Routing Contract

**Owner:** Phase 11 (Subagents) — Plan 11-04
**Consumed by:** Phase 10 (Claude Skill Frontend) — SKLL-01 (SKILL.md routing block) + SKLL-05 (modes/stress.md mode file)
**Status (set by Plan 11-04 executor):** (a) WIRED IN-PLACE
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

1. `grep -E '(scenarios?\s*(>|more than|greater than)\s*5|scenario[_ ]count\s*>\s*5).*(stress-test-agent|subagent)' .claude/skills/mortgage-ops/modes/stress.md` returns a match.
2. `grep -c 'stress-test-agent' .claude/skills/mortgage-ops/SKILL.md` returns ≥ 1.
3. `grep -c 'modes/stress.md' .claude/skills/mortgage-ops/SKILL.md` returns ≥ 1 (cross-link from SKILL.md to the full rule).
4. The Wave 0 stub `tests/test_subagents.py::test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent` passes (the xfail decorator is removed; the regex from RESEARCH Code Example 4 matches).
5. SKILL.md still satisfies SKLL-01 (≤500 lines, ≤5,000 tokens) and SKLL-02 (routing in first 200 lines) after the addition.

Once Phase 10 satisfies all five criteria, mark this TODO file's Status header as **(a) WIRED**
and update Plan 11-04's SUMMARY accordingly.

## Branch — what Plan 11-04 executor actually did

**(a) WIRED IN-PLACE — Phase 10 had shipped at execution time.**

- Phase 10 SKILL.md (253 lines) + modes/stress.md (151 lines) both present at execution time on the
  worktree base `ab8ca7feff2d3aae9f62eba6c73c05a51704af3e` (Wave 3 merge).
- Edited `.claude/skills/mortgage-ops/modes/stress.md` to insert the SUBA-05 routing block above
  containing the literal `scenario_count > 5` + `stress-test-agent` regex-pinning text, appended at
  the end of the file (after RELATED REFERENCES).
- Edited `.claude/skills/mortgage-ops/SKILL.md` to add the routing-block cross-reference into the
  existing "Subagents (Phase 11)" section (which previously gestured at the routing rule without
  pinning the >5 threshold by name). The cross-reference cites both the >5 threshold and
  `modes/stress.md`.
- Wave 0 SUBA-05 test (`test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent`) xfail decorator
  removed; test body replaced with the regex assertion from RESEARCH Code Example 4 (lines
  ~440-452) plus a SKILL.md cross-reference assertion. Test now PASSES.
- This TODO marker remains as the canonical traceability record so Phase 11's planning history
  forever documents the cross-phase contract Plan 11-04 fulfilled.

**(b) AWAITING PHASE 10 — not applicable for this execution.**

(Branch (b) would have been selected if Phase 10 had not shipped SKILL.md + modes/stress.md by the
time Plan 11-04 ran. That branch is now historical for this plan; it remains documented above for
the cross-phase contract template.)
