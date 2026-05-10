---
phase: 11-subagents
fixed_at: 2026-05-10T00:00:00Z
review_path: .planning/phases/11-subagents/11-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-05-10
**Source review:** `.planning/phases/11-subagents/11-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (3 Critical + 6 Warnings; Info skipped per scope)
- Fixed: 9
- Skipped: 0

**Test suite gate (post-fix):** 600 passed, 5 skipped, 1 xfailed, 0 failed
(matches the pre-fix baseline; no regression).

## Fixed Issues

### CR-01: Broken cross-link to non-existent `references/stress-tests.md`

**Files modified:** `.claude/skills/mortgage-ops/references/stress-tests.md`
(new file)
**Commit:** 43c9b13
**Applied fix:** Copied the canonical Phase 8 reference from
`references/stress-tests.md` (top-level, where it was originally added in
commit c5ff926) into `.claude/skills/mortgage-ops/references/stress-tests.md`
(skill directory, where five Phase 11 artifacts cite it). Phase 8 was supposed
to ship the file alongside the other phase-domain references (`apr-reg-z.md`,
`arm-mechanics.md`, `refi-npv.md`) but only landed it at the top-level path.
This is option (a) from the review (ship the file) — the right fix because
the references are load-bearing. No edits needed to the four citing
locations (`stress-test-agent.md:147`, `subagent-routing.md:5,164`,
`modes/stress.md:146`, `stress_test.py:101`).

### CR-02: Amortization agent column contract does not match fixture/test

**Files modified:**
- `tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl`
- `tests/test_subagents.py`

**Commit:** b49a087
**Applied fix:** Adopted Option A from the review (agent contract is canonical;
fixture and test conform). The agent body at `amortization-agent.md:66`
specifies `period | date | payment | principal | interest | balance` and is
locked first per Wave 1. Updated the fixture's inline-table header to match
verbatim, added synthetic `date` cells (2026-06-01 / 2026-07-01 / 2056-05-01)
in the existing rows, and changed the SUBA-04 amort assertion from
`"| month "` to `"| period "`. The failure message now also names the
canonical six-column header so a future drift surfaces with full context.

### CR-03: refi-npv-agent body instructs "Write the input" with no Write tool available

**Files modified:** `.claude/agents/refi-npv-agent.md`
**Commit:** 36aad43
**Applied fix:** Added parenthetical disambiguation to Workflow Step 3b
mirroring the `amortization-agent.md` Workflow Step 4 pattern. Step 3b now
reads: "Write the input to `/tmp/refi-input-{offer-idx}-{timestamp}.json`
(Bash tool — use a heredoc or `printf` to materialize the tmpfile; the
Write tool is NOT in this agent's toolset per Hard rule #5)." Closes the
internal contradiction between the Workflow body's verb "Write" (which a
literal reading would dispatch to the Write tool) and the frontmatter
`tools: [Read, Bash]` allowlist.

### WR-01: tiktoken dev-dep contradicts the project's tokenizer doctrine

**Files modified:** `pyproject.toml`
**Commit:** 7913c92
**Applied fix:** Added an inline comment in `[dependency-groups] dev`
documenting that tiktoken is used by `tests/_skill_helpers.py` for Phase 10
SKILL.md token-budget tests (cl100k_base encoder per Phase 10 RESEARCH §(i)
+ LOCKED DECISION D-02). The "REJECTED" note in `tests/test_subagents.py`
applies only to the Phase 11 subagent context (SUBA-06 uses
`anthropic.count_tokens` per Plan 11-05 D-01), not to the project as a
whole. This is option (b) from the review (document the actual usage).
The dep is NOT removed — `tests/_skill_helpers.py:18` actively imports it.

### WR-02: SKILL.md "Subagents (Phase 11)" section in future tense

**Files modified:** `.claude/skills/mortgage-ops/SKILL.md`
**Commit:** 1f179b6
**Applied fix:** Converted the section body to present tense:
- "Three subagents provide context isolation" (was "will land")
- "Files live at `.claude/agents/{agent}.md`" (was "will be created at")
- "Dispatch is gated by `modes/stress.md` ... performs an existence check ...
  and falls back to inline execution if the file is absent" (was "When Phase 11
  lands ... will activate the dispatch automatically")

The literal heading `## Subagents (Phase 11)` is preserved verbatim because
`tests/test_skill.py::test_skill_md_subagent_section_present` asserts the
exact string per D-SUBA-FW-01 (Phase 10 forward-link contract). The
`(Phase 11)` suffix names the originating phase, not the future-tense
status; keeping it satisfies the Phase 10 test gate. (The first attempt
at this fix dropped the `(Phase 11)` suffix and was caught by the
test_skill.py failure; the suffix was restored before commit.)

### WR-03: SUBA-05 regex too permissive

**Files modified:** `tests/test_subagents.py`
**Commit:** 2c6f204
**Applied fix:** Replaced the `.* + re.DOTALL` regex with a literal-sentence
assertion against `modes/stress.md:155` verbatim:
`"If \`scenario_count > 5\`, dispatch to \`stress-test-agent\`"`. This is
option (B) from the review (strongest pin, matches canonical phrasing
exactly). Removed the now-orphaned `import re` inside the SUBA-05 test
body (the module-level `import re` is still used by SUBA-04 amort CSV
regex at line 367). The strict `>5` threshold (NOT `>=5`, NOT `>3`) is
preserved per Plan 11-04 LOCKED DECISION D-01 and the orchestrator
constraint.

### WR-04: SUBA-04 refi NPV parser crashes opaquely on `n/a`

**Files modified:** `tests/test_subagents.py`
**Commit:** d840477
**Applied fix:** Wrapped `float(npv_str)` in try/except ValueError +
`pytest.fail()` with a diagnostic message that names the canonical
contract (NPV as LAST column per Plan 11-02 Hard rule #5) and explains
why a non-numeric last cell signals a column-reorder drift. The current
passing case (NPV is numeric) is unchanged; only the failure mode is now
interpretable.

### WR-05: Refi `Computed by:` cite uses ambiguous shell brace expansion

**Files modified:** `tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl`
**Commit:** b35f84d
**Applied fix:** Replaced the brace-expansion form with a parameterized
template:
- Before: `--input /tmp/refi-input-{1,2,3}-1714665600.json (3 invocations)`
- After:  `--input /tmp/refi-input-N-1714665600.json (3 invocations, N=1..3)`

This is the more compact option from the review (vs. listing three
explicit invocation lines), preserves token budget, and makes clear that
the citation is a parameterized template — not a copy-pasteable shell
command. The SUBA-04 refi assertion (`"refi_npv.py" in content`) still
matches.

### WR-06: README.md cross-link target depth wrong

**Files modified:** `.claude/agents/README.md`
**Commit:** 0f9be0e
**Applied fix:** Normalized all `Where to learn more` paths to repo-rooted
bare form (option (a) from the review), matching the established
convention in sibling `.claude/skills/mortgage-ops/references/*.md`
(verified: `apr-reg-z.md:484`, `arm-mechanics.md:25`,
`subagent-routing.md:6,163` all use bare repo-rooted paths). Mappings:
- `../skills/mortgage-ops/...`           -> `.claude/skills/mortgage-ops/...`
- `../../.planning/...`                  -> `.planning/...`
- `../../tests/...`                      -> `tests/...`

Added a one-line preamble naming the convention so future readers match
the established pattern.

## Skipped Issues

None — all 9 in-scope findings (3 Critical + 6 Warnings) were fixed.

The 4 Info findings (IN-01..IN-04) are out of scope per the orchestrator
configuration (`fix_scope: critical_warning`).

## Constraints honored

- No `Co-Authored-By` or AI-attribution markers in any of the 9 commits
  (verified: each commit message ends with the trailing line of the body,
  no Claude/Anthropic byline).
- READ-ONLY user-layer respected: no edits to `config/household.yml`,
  `config/profile.yml`, any `*.duckdb` file, or `data/`.
- SUBA-05 threshold strictly `>5` preserved — verified by grep across
  `modes/stress.md` (3 occurrences, all `> 5`) and `test_subagents.py`
  (5 occurrences, all `>5`).
- SC-3 token budget assertion still strictly `< 1000` — verified at
  `tests/test_subagents.py:477` (`response.input_tokens < 1000`).
- Test suite green: 600 passed / 5 skipped / 1 xfailed / 0 failed
  (matches pre-fix baseline; no regressions).

---

_Fixed: 2026-05-10_
_Fixer: gsd-code-fixer_
_Iteration: 1_
