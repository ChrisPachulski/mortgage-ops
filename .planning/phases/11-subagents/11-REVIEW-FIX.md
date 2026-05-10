---
phase: 11-subagents
fixed_at: 2026-05-10T00:00:00Z
review_path: .planning/phases/11-subagents/11-REVIEW.md
iteration: 2
findings_in_scope: 13
fixed: 13
skipped: 0
status: all_fixed
iteration_1_fixed: 9
iteration_2_fixed: 4
total_fixed: 13
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-05-10
**Source review:** `.planning/phases/11-subagents/11-REVIEW.md`
**Iteration:** 2 (cumulative across iterations 1 + 2)

**Summary:**
- Findings in scope: 13 (3 Critical + 6 Warnings + 4 Info)
- Fixed: 13
- Skipped: 0
- Iteration 1: 9/9 (3 Critical + 6 Warnings)
- Iteration 2: 4/4 (4 Info)

**Test suite gate (post-iteration-2 fix):** 600 passed, 5 skipped, 1 xfailed,
0 failed — matches the pre-fix baseline; no regression across either
iteration.

## Iteration 2 — Info findings (4 new fixes)

### IN-01: Future-tense roadmap prose in test_subagents.py docstring

**Files modified:** `tests/test_subagents.py`
**Commit:** 5fcca60
**Applied fix:** Replaced the wave-by-wave "Wave 0 creates all 6 tests
as xfail stubs; subsequent waves flip..." narrative with a final-state
description. The new docstring records the locked outcome ("All
SUBA-01..06 tests are live (no xfail decorators remain)") followed by
a wave-provenance ledger that preserves historical traceability:
SUBA-01 (Plan 11-01), SUBA-02 (Plan 11-02), SUBA-03 (Plan 11-03),
SUBA-04+SUBA-06 (Plan 11-05), SUBA-05 (Plan 11-04). Also dropped the
duplicative "Subsequent waves should NOT redefine any of the above"
paragraph that became redundant with the new Module-structure intro.
The `(constants are imported by sibling test files when present)`
bullet captures the operative guidance in one line.

### IN-02: TRANSCRIPT_DIR docstring references non-existent filename

**Files modified:** `tests/test_subagents.py`
**Commit:** f4ae83b
**Applied fix:** Updated the `TRANSCRIPT_DIR` constant docstring to
name the real fixture: `stress_50_scenarios.transcript.jsonl` (the
file that actually lives at `tests/fixtures/subagent_transcripts/`)
instead of `stress_50_scenario_summary.md` (which never landed). Also
clarified that `anthropic.count_tokens` is called against the
JSONL **content**, not the path, to remove a second reader-trap.

### IN-03: `.gitkeep` is redundant once real fixtures landed

**Files modified:**
- `tests/fixtures/subagent_transcripts/.gitkeep` (deleted via `git rm`)
- `tests/fixtures/subagent_transcripts/README.md` (updated narrative)

**Commit:** 5114d5f
**Applied fix:** Removed the 0-byte `.gitkeep` seam. The directory is
now tracked through the real content files (`README.md` + three
`*.transcript.jsonl` fixtures) that Wave 5 landed in the same
directory, so the Wave 0 seam file is residue. Updated the directory
README's Wave-history paragraph to record the cleanup ("The `.gitkeep`
was removed in the Phase 11 code-review cleanup pass (IN-03) once the
real fixtures landed alongside the README — git tracks the directory
via those files now") so future readers don't look for a missing file.

Safety checks performed:
- `scripts/hooks/block-user-layer.py:31` ALLOWED_KEEP_FILES enumerates
  only `reports/.gitkeep` and `data/reference/.gitkeep` — this
  `.gitkeep` was NOT on the whitelist, so removal does not touch the
  User-Layer seam contract or `tests/test_block_user_layer.py`.
- `tests/test_orchestration/test_gitignore_phase09.py:100` asserts
  only on `reports/.gitkeep`, not the transcripts seam.
- `TRANSCRIPT_DIR` is a module-level `Path` constant evaluated at
  import time (not at directory-emptiness check time); the SUBA-04
  smoke test (`tests/test_subagents.py::test_transcript_dir_exists`
  equivalent) reads the directory and the three real `.jsonl`
  fixtures, all of which are still present.

Post-removal directory listing: 4 files (README.md + 3 transcripts),
all preserved.

### IN-04: Fixture path date drifts from system date

**Files modified:** `tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl`
**Commit:** b20565e
**Applied fix:** Single-character literal swap: `reports/001-amortization-2026-05-02.csv`
-> `reports/001-amortization-2026-05-10.csv`. Today's date per
`CLAUDE.md` is 2026-05-10 and the `amortization-agent` Hard rule #4
specifies "today's ISO date" for the CSV path.

Safety checks performed:
- `grep -rn "2026-05-02"` confirmed no test asserts against the
  literal date string. Other `2026-05-02` occurrences are unrelated
  "verified 2026-05-02" citation timestamps in
  `references/apr-reg-z.md` and `references/refi-npv.md` (both
  Phase 7 / Phase 6 deliverables, untouched).
- SUBA-04 amort assertion uses the regex
  `reports/\d{3}-amortization-\d{4}-\d{2}-\d{2}\.csv`, which matches
  both before and after the change.
- The fixture's JSONL still parses (verified via `json.loads`).

## Iteration 1 — Critical and Warning findings (9 fixes)

[Preserved verbatim from iteration 1 report for cross-reference.]

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

None — all 13 findings (3 Critical + 6 Warnings + 4 Info) across both
iterations were fixed.

## Constraints honored

- No `Co-Authored-By` or AI-attribution markers in any of the 13 fix
  commits (verified across iterations 1 + 2; each commit message ends
  with the trailing line of the body, no Claude/Anthropic byline).
- READ-ONLY user-layer respected: no edits to `config/household.yml`,
  `config/profile.yml`, any `*.duckdb` file, or `data/`.
- SUBA-05 threshold strictly `>5` preserved across both iterations
  (no Info finding touched modes/stress.md routing prose).
- SC-3 token budget assertion still strictly `< 1000` — verified at
  `tests/test_subagents.py:471` (`response.input_tokens < 1000`;
  line number shifted -1 in iteration 2 from docstring trimming, but
  the assertion is unchanged).
- Test suite green: 600 passed / 5 skipped / 1 xfailed / 0 failed
  (matches pre-fix baseline across both iterations; no regressions
  introduced by any of the 13 fixes).
- Iteration 2 commits used `--no-verify` per orchestrator instruction
  (avoids hook contention on main; the global no-Claude-attribution
  rule was still honored manually in every commit message).

## Iteration-2 commit ledger (chronological)

| Commit  | Finding | Title                                                                        |
|---------|---------|------------------------------------------------------------------------------|
| 5fcca60 | IN-01   | collapse stale wave-by-wave narrative in test_subagents docstring             |
| f4ae83b | IN-02   | correct TRANSCRIPT_DIR docstring filename reference                           |
| 5114d5f | IN-03   | remove redundant subagent_transcripts/.gitkeep seam                           |
| b20565e | IN-04   | align amort fixture CSV-path date with system date                            |

---

_Fixed: 2026-05-10_
_Fixer: gsd-code-fixer_
_Iteration: 2 (covering Info findings; iteration 1 covered Critical + Warning)_
