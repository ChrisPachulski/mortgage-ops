---
phase: 10-claude-skill
plan: 02
subsystem: claude-skill
tags:
  - phase-10
  - claude-skill
  - skill-md
  - frontmatter
  - routing-skeleton
  - math-discipline
  - run-help-first
  - progressive-disclosure
  - subagent-forward-link
  - skll-01
  - skll-02
  - skll-03
  - skll-04
  - skll-09
  - skll-11
  - skll-12
  - skll-apr-1
  - wave-2

requires:
  - phase: 10-00
    provides: tests/_skill_helpers.count_tokens (cl100k_base) + tests/test_skill.py xfail stubs (Wave 5 will flip to consume this SKILL.md)
  - phase: 10-01
    provides: 7 calc CLIs at .claude/skills/mortgage-ops/scripts/ (SKILL.md routing dispatches to scripts that exist)
provides:
  - .claude/skills/mortgage-ops/SKILL.md (253-line / 3386-token routing skeleton + 4 load-bearing doctrines)
  - .claude/skills/mortgage-ops/LICENSE.txt (21-line MIT, D-04 default)
  - frontmatter spec compliance per agentskills.io (name + description + license + compatibility)
  - first-200-line load-bearing routing zone (## Mode Routing at line 19; 7 modes + precedence table)
  - SKLL-11 always-shell-out doctrine literal substring
  - SKLL-12 run-help-first doctrine literal substring
  - SKLL-09 topic→reference progressive-disclosure table (9 references)
  - D-SUBA-FW-01 ## Subagents (Phase 11) forward-link section (3 agent filenames; no delegation wording)
  - SKLL-APR-1 estimated APR literal-text rule (UI-SPEC §e)
  - Discovery menu code fence (UI-SPEC §Discovery Menu)
  - First-Session Onboarding (User Layer enforcement reminder)
affects:
  - "10-03 (Wave 3 modes/*.md): SKILL.md routing references modes/{evaluate,compare,refinance,affordability,stress,amortize,arm}.md that Wave 3 ships; modes/_shared.md owns Number Formatting templates SKILL.md forward-links to (D-NUM-01..06)"
  - "10-04 (Wave 4 references/*.md): SKILL.md topic→reference table references 9 reference files Wave 4 ships"
  - "10-05 (Wave 5 CI tests): Wave 5 flips 7 xfail stubs (SKLL-01 token + line, SKLL-02 routing, SKLL-03 frontmatter, SKLL-04 LICENSE, SKLL-09 progressive disclosure, SKLL-11 shell-out, SKLL-12 run-help-first) to real assertions consuming this SKILL.md"
  - "11 (Phase 11 subagents): D-SUBA-FW-01 forward-link section already names amortization-agent + refi-npv-agent + stress-test-agent so Phase 11 lands by writing the .claude/agents/*.md files; no SKILL.md edit required"

tech-stack:
  added: []
  patterns:
    - "load-bearing-first-200-lines convention (D-12 / SKLL-02): routing must appear before the Anthropic compaction re-attach budget cuts off, so heading + precedence + 7 modes all live in lines 1-200"
    - "doctrine-as-substring contract: SKILL.md author-time prose decisions become Wave 5 grep-assertions; literal substrings 'ALWAYS shell out to scripts/ for math; NEVER compute numbers inline.' (SKLL-11) and 'run scripts with `--help` first; do not read the source' (SKLL-12) are pinned by Wave 0 stubs and Wave 5 flips"
    - "frontmatter copy-block discipline (D-03): RESEARCH §(k) ships verbatim 4-key frontmatter (name + description + license + compatibility); Plan 10-02 pastes verbatim; Wave 5 yaml.safe_load asserts"
    - "forward-link without delegation (D-SUBA-FW-01): SKILL.md can NAME Phase 11 subagents (amortization-agent, refi-npv-agent, stress-test-agent) without instructing delegation — the existence-check seam lives in modes/stress.md per D-SUBA-FW-02; Round-2 codex MEDIUM 8 enforces 'dispatches to subagent' substring MUST be absent from SKILL.md"
    - "token-budget headroom: ship SKILL.md at ~3386 cl100k tokens (1100 under 4500 cap) so Waves 3-5 additions (modes/_shared.md inline references, references/*.md forward-links) don't push past cap"
    - "no-AI-attribution discipline propagation: SKILL.md Footer reaffirms global CLAUDE.md no Co-Authored-By rule for any commit produced by skill-driven workflows"

key-files:
  created:
    - .claude/skills/mortgage-ops/SKILL.md
    - .claude/skills/mortgage-ops/LICENSE.txt
  modified: []

key-decisions:
  - "D-02 honored: 3386 cl100k tokens vs 4500 effective cap (10% margin under Anthropic 5000 spec); 1114-token headroom for Waves 3-5"
  - "D-03 honored: frontmatter copied verbatim from RESEARCH §(k); name=mortgage-ops + 4 SC-2 keys present"
  - "D-04 honored: LICENSE.txt is plain MIT (no SPDX header, no preamble) per project default; pyproject.toml [project] license block edit deferred (out of scope per plan)"
  - "D-09 honored: topic→reference table inline in SKILL.md (no separate loading.md); 9 reference filenames listed"
  - "D-10 honored: 'Loading Additional Context' instructs Claude to read modes/_shared.md FIRST then modes/{mode}.md"
  - "D-11 honored: Mode dispatch table + ambiguity rules live IN SKILL.md (no routing.md split)"
  - "D-12 honored: '## Mode Routing' heading at line 19 (well under 200-line cap)"
  - "D-NUM-01..06 forward-linked: SKILL.md has a 'Number Formatting' section pointing to modes/_shared.md (Wave 3) for the actual fmt_money / fmt_rate / fmt_ratio / fmt_bps templates"
  - "D-SUBA-FW-01 honored: '## Subagents (Phase 11)' section names 3 agent filenames as forward-link only; explicitly states 'Phase 10 ships ONLY the forward-link. The skill does NOT delegate to these agents at Phase 10.'"
  - "D-SUBA-FW-02 honored at SKILL.md surface: existence-check seam NOT placed in SKILL.md routing precedence (rule 5 reads 'stress / sweep + range → stress' with no dispatch parenthetical); Round-2 codex MEDIUM 8 grep-assertion 'dispatches to subagent' returns 0 occurrences. The seam will live in modes/stress.md when Wave 3 ships it."
  - "SKLL-APR-1 (UI-SPEC §e) embedded as 'Estimated APR Literal Text' section; will bind every APR figure post-Phase-7 (apr_reg_z.py already shipped per Plan 10-01 relocation)"

patterns-established:
  - "SKILL.md template structure (lines 1-7 frontmatter; 8-18 title + intro; 19-55 Mode Routing + precedence; 56-83 Math Discipline; 84-113 Bundled Scripts black-box; 114-141 Loading Additional Context; 142-159 Number Formatting forward-link; 160-178 Estimated APR; 179-191 Subagents (Phase 11); 192-222 Discovery Menu; 223-240 First-Session Onboarding; 241-253 Footer) — Phase 11 subagent skills can copy this skeleton if any subagent needs its own SKILL.md surface"
  - "Doctrine-substring contract: load-bearing prose decisions (math discipline, run-help-first) are author-time strings AND machine-checkable Wave 5 substrings — the same literal text serves both the LLM context and the CI grep"
  - "Forward-link section pattern (D-SUBA-FW-01): a phase that ships before its consumer can DOCUMENT-NAME the consumer's filenames in prose without instructing delegation; the consumer phase activates dispatch by writing the file (existence-check seam) without requiring an edit to the documenting phase's surface"

requirements-completed:
  - SKLL-01
  - SKLL-02
  - SKLL-03
  - SKLL-04
  - SKLL-09
  - SKLL-11
  - SKLL-12

duration: ~10 min
completed: "2026-05-10"
---

# Phase 10 Plan 02: SKILL.md Scaffold Summary

**253-line / 3386-token SKILL.md skeleton + 21-line MIT LICENSE.txt bundled inside `.claude/skills/mortgage-ops/`; ships frontmatter (4 SC-2 keys per agentskills.io spec D-03), load-bearing routing (## Mode Routing + 7-mode dispatch table + 9-line precedence in first 19-55 lines per D-12), the 4 load-bearing doctrines (math-discipline always-shell-out / black-box run-help-first / progressive-disclosure topic→reference table for 9 references / estimated APR literal-text rule), and the D-SUBA-FW-01 `## Subagents (Phase 11)` forward-link section naming all 3 Phase 11 subagent filenames — without runtime delegation wording (Round-2 codex MEDIUM 8 guardrail satisfied). Wave 5 grep-asserts; Wave 1 baseline preserved (550 passed / 4 skipped / 16 xfailed).**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-10T00:43:14Z
- **Completed:** 2026-05-10T00:55:50Z
- **Tasks:** 2 (LICENSE.txt + SKILL.md)
- **Files created:** 2

## Wave Outcome

| Metric | Wave 1 baseline | Wave 2 result | Delta |
|--------|-----------------|---------------|-------|
| `pytest` total passed | 550 | 550 | 0 |
| skipped | 4 | 4 | 0 |
| xfailed | 16 | 16 | 0 |
| failed | 0 | 0 | 0 |
| errored | 0 | 0 | 0 |
| Files at `.claude/skills/mortgage-ops/` (excl. scripts/) | 0 | 2 (SKILL.md + LICENSE.txt) | +2 |

Wave 5 (Plan 10-05) will flip the 7 xfail stubs that Plan 10-02 satisfies (SKLL-01 token + line, SKLL-02 routing, SKLL-03 frontmatter, SKLL-04 LICENSE, SKLL-09 progressive disclosure, SKLL-11 shell-out, SKLL-12 run-help-first) — at that point `xfailed` drops by 7 to 9.

## Accomplishments

- **SKILL.md skeleton (253 lines / 3386 cl100k tokens)** — fits both budgets with substantial margin. Frontmatter at lines 1-7 with all 4 SC-2 keys (`name`, `description`, `license`, `compatibility`); `name == "mortgage-ops"` matches parent dir per agentskills.io spec; `description` is 494 chars (under 1024 cap); `compatibility` is 283 chars (under 500 cap).
- **`## Mode Routing` heading at line 19** — well under the 200-line load-bearing cap (D-12 / SKLL-02). All 7 mode names (`evaluate`, `compare`, `refinance`, `affordability`, `stress`, `amortize`, `arm`) appear in the dispatch table; the 9-line precedence list (UI-SPEC §a verbatim) clarifies routing collisions.
- **Math Discipline doctrine (lines 56-83)** — embeds the verbatim SKLL-11 substring `"ALWAYS shell out to scripts/ for math; NEVER compute numbers inline."` Wave 5 will grep-assert.
- **Bundled Scripts black-box discipline (lines 84-113)** — embeds the verbatim SKLL-12 substring `"run scripts with \`--help\` first; do not read the source until you try running the script first and find that a customized solution is absolutely necessary."` Doctrine lifted from `anthropics/skills/skills/webapp-testing/SKILL.md` per RESEARCH §(b).
- **Topic→reference progressive-disclosure table (SKLL-09 / D-09)** — names all 9 reference filenames (`amortization-formulas`, `apr-reg-z`, `arm-mechanics`, `refi-npv`, `affordability-rules`, `gse-limits`, `mip-pmi`, `tax-deductibility`, `spreadsheet-conventions`) keyed by user trigger phrase. Wave 4 ships the actual reference files; Wave 5 asserts presence.
- **`## Subagents (Phase 11)` forward-link section (D-SUBA-FW-01)** — names all 3 Phase 11 agent filenames (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) WITHOUT instructing delegation. Explicit guard: "Phase 10 ships ONLY the forward-link. The skill does NOT delegate to these agents at Phase 10." Round-2 codex MEDIUM 8 contradiction guardrail satisfied — `grep -c "dispatches to subagent"` returns 0; routing precedence rule 5 reads `"stress / sweep + range → stress"` with no parenthetical.
- **LICENSE.txt (21 lines, plain MIT)** — D-04 default. Copyright 2026 Pachulski Household. No SPDX header, no preamble. Frontmatter `license:` field cross-references it: `"MIT (complete terms in LICENSE.txt)"`.

## Task Commits

Each task committed atomically per CLAUDE.md / global no-attribution rule:

1. **Task 1: LICENSE.txt (MIT terms; D-04)** — `bc99012` (feat)
2. **Task 2: SKILL.md (frontmatter + routing skeleton + doctrines + subagents forward-link)** — `3000004` (feat)

**Plan metadata:** _to be appended_ (this SUMMARY commit)

## Files Created/Modified

- `.claude/skills/mortgage-ops/SKILL.md` (NEW, 253 lines / 3386 cl100k tokens) — Skill router entrypoint: frontmatter + routing skeleton + math-discipline doctrine + black-box script invocation doctrine + progressive-disclosure rules + Subagents (Phase 11) forward-link + estimated APR literal-text rule + discovery menu + first-session onboarding + footer.
- `.claude/skills/mortgage-ops/LICENSE.txt` (NEW, 21 lines) — Standard MIT block. Copyright 2026 Pachulski Household.

## Substring-Presence Audit (matches plan §"CRITICAL CONSTRAINTS" + §"acceptance_criteria")

All Wave 5 grep-assertions will pass against this SKILL.md content:

| Required substring / structure | Plan-cited requirement | Verified |
|--------------------------------|------------------------|----------|
| Frontmatter parses cleanly via `yaml.safe_load` | SKLL-03 / D-03 | ✓ (488-char description, 283-char compat — both under spec) |
| `name: mortgage-ops` (matches parent dir) | SKLL-03 / agentskills.io spec | ✓ |
| Frontmatter has 4 SC-2 keys (`name`, `description`, `license`, `compatibility`) | SKLL-03 / D-03 | ✓ all 4 present |
| File ≤ 500 lines | SKLL-01 | ✓ 253 lines |
| File ≤ 4500 cl100k tokens | SKLL-01 / D-02 | ✓ 3386 tokens (1114-token headroom) |
| `## Mode Routing` heading in first 200 lines | SKLL-02 / D-12 | ✓ line 19 |
| All 7 mode names in first 200 lines (`evaluate`, `compare`, `refinance`, `affordability`, `stress`, `amortize`, `arm`) | SKLL-02 indirect | ✓ all 7 in dispatch table + precedence list |
| Substring `"ALWAYS shell out to scripts/ for math; NEVER compute numbers inline."` | SKLL-11 / UI-SPEC §g | ✓ exact match |
| Substring `` "`--help` first" `` | SKLL-12 / RESEARCH §(b) webapp-testing | ✓ multiple occurrences |
| All 9 reference filenames in topic→reference table | SKLL-09 / D-09 / UI-SPEC §d | ✓ amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions |
| Substring `"estimated APR"` (forward-link to Phase 7 / SKLL-APR-1) | UI-SPEC §e | ✓ 6 occurrences |
| Discovery menu code fence (`/mortgage-ops evaluate`...`arm`) | UI-SPEC §Discovery Menu | ✓ |
| `## Subagents (Phase 11)` heading | D-SUBA-FW-01 | ✓ exact match |
| All 3 subagent filenames (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) under Subagents section | D-SUBA-FW-01 | ✓ all 3 as backtick-wrapped tokens |
| Substring `"dispatches to subagent"` MUST NOT appear | Round-2 codex MEDIUM 8 / D-SUBA-FW-02 | ✓ 0 occurrences |
| `LICENSE.txt` exists with `MIT License` first line | SKLL-04 / D-04 | ✓ |
| `LICENSE.txt` between 18 and 25 lines | task 1 acceptance | ✓ 21 lines |

## Frontmatter Verbatim-vs-Recommended Diff

The frontmatter shipped is verbatim per RESEARCH §(k) recommended copy-block. No deviations:

| Field | Shipped value | RESEARCH §(k) | Match |
|-------|---------------|---------------|-------|
| `name` | `mortgage-ops` | `mortgage-ops` | exact |
| `description` (494c) | "Personal-use mortgage analysis for the Pachulski household. Routes natural-language requests…" | identical | exact |
| `license` | `MIT (complete terms in LICENSE.txt)` | identical | exact |
| `compatibility` (283c) | "Requires Python 3.12+, numpy-financial, pydantic v2 (>=2.13), pyyaml. Designed for Claude Code…" | identical | exact |

## Decisions Made

None beyond the LOCKED DECISIONS already pinned by 10-CONTEXT.md and 10-RESEARCH.md. The plan was executed verbatim:

- D-02 token budget honored (3386 < 4500)
- D-03 frontmatter shape honored (4 SC-2 keys, verbatim from §(k))
- D-04 LICENSE.txt = plain MIT honored
- D-09 progressive-disclosure inline (no separate loading.md)
- D-10 / D-11 routing + ambiguity rules in SKILL.md (no split files)
- D-12 routing in first 200 lines (line 19, 90% margin)
- D-NUM-01..06 forward-linked to modes/_shared.md (Wave 3)
- D-SUBA-FW-01 forward-link section without delegation
- D-SUBA-FW-02 existence-check seam NOT in SKILL.md (will live in modes/stress.md per Wave 3)
- SKLL-APR-1 estimated-APR literal-text rule embedded
- Round-2 codex MEDIUM 8 guardrail satisfied (no "dispatches to subagent" substring)

## Deviations from Plan

None — plan executed exactly as written.

The plan §"CRITICAL CONSTRAINTS" called out a Write-tool escape concern around the discovery menu's nested code fence (`\``` escape vs real ``` fence). In practice the Write tool emits the literal `` ``` `` triple-backtick sequence inside the SKILL.md heredoc verbatim — no Edit fixup was required. `grep -c '/mortgage-ops evaluate'` returns 1 confirming the discovery menu structure rendered correctly.

## Issues Encountered

None.

## Self-Check: PASSED

**Files exist:**
- FOUND: `.claude/skills/mortgage-ops/SKILL.md` (253 lines / 3386 cl100k tokens)
- FOUND: `.claude/skills/mortgage-ops/LICENSE.txt` (21 lines, MIT)

**Commits exist (verified via `git log --oneline`):**
- FOUND: `bc99012` feat(10-02): bundle MIT LICENSE.txt inside skill folder (SKLL-04 / D-04)
- FOUND: `3000004` feat(10-02): ship SKILL.md scaffold (SKLL-01..03, SKLL-09, SKLL-11..12, D-SUBA-FW-01)

**Acceptance gates (Task 1):**
- LICENSE.txt exists at `.claude/skills/mortgage-ops/LICENSE.txt`: PASSED
- Contains `MIT License` (first line): PASSED
- Contains `Copyright (c) 2026 Pachulski Household`: PASSED
- Contains `WITHOUT WARRANTY OF ANY KIND`: PASSED
- Line count between 18 and 25: PASSED (21 lines)

**Acceptance gates (Task 2):**
- SKILL.md exists: PASSED
- ≤ 500 lines: PASSED (253)
- ≤ 4500 cl100k tokens: PASSED (3386)
- Frontmatter parses; 4 SC-2 keys: PASSED
- `name == "mortgage-ops"`: PASSED
- `description` ≤ 1024 chars: PASSED (494)
- `compatibility` ≤ 500 chars: PASSED (283)
- `## Mode Routing` heading in first 200 lines: PASSED (line 19)
- All 7 mode names in first 200 lines: PASSED
- SKLL-11 substring present: PASSED
- SKLL-12 substring present: PASSED
- 9 reference filenames in topic→reference table: PASSED (all 9)
- Substring `"estimated APR"` present: PASSED (6 occurrences)
- Discovery menu code fence present: PASSED
- `## Subagents (Phase 11)` heading present: PASSED
- All 3 subagent filenames present: PASSED
- Substring `"dispatches to subagent"` ABSENT: PASSED (0 occurrences)

**Test suite:**
- 550 passed / 4 skipped / 16 xfailed / 0 failed / 0 errored: PASSED (Wave 1 baseline preserved)

## Next Wave Readiness

Wave 3 (Plan 10-03 modes/*.md) can proceed:

- SKILL.md routing forward-references `modes/_shared.md` (D-10 always-load) and `modes/{mode}.md` for all 7 modes — Wave 3 ships these.
- SKILL.md "Number Formatting" section forward-links to `modes/_shared.md` § "Number Formatting" — Wave 3 owns the actual fmt_money / fmt_rate / fmt_ratio / fmt_bps templates.
- Per D-SUBA-FW-02, `modes/stress.md` (Wave 3) will carry the existence-check seam: `"For sweeps with N > 5 scenarios, defer to .claude/agents/stress-test-agent.md if it exists; otherwise run the stress sweep inline."` SKILL.md does NOT need an edit when Phase 11 lands the agent file.
- Token budget headroom: 1114 tokens remain under 4500 cap. Wave 3 should NOT add to SKILL.md (modes/*.md ship as separate files); Wave 4 references/*.md likewise. Wave 5 may add minor SKILL.md edits if CI assertions require, but no large structural change is anticipated.

Wave 5 (Plan 10-05 CI tests) will flip 7 xfail stubs against this SKILL.md (SKLL-01 ×2, SKLL-02, SKLL-03, SKLL-04, SKLL-09, SKLL-11, SKLL-12) — every Wave 5 grep-assertion has a satisfying substring or structural anchor in the shipped content per the audit table above.

Wave 4 (Plan 10-04 references/*.md) consumes the 9 reference filenames already named in SKILL.md's topic→reference table. The names are pinned; Wave 4 ships the files.

Phase 11 (subagents) can land by writing `.claude/agents/{amortization,refi-npv,stress-test}-agent.md` files; SKILL.md already names them as forward-links and `modes/stress.md` (Wave 3) will carry the existence-check seam — zero SKILL.md edits required when Phase 11 ships.

---
*Phase: 10-claude-skill*
*Plan: 02*
*Completed: 2026-05-10*
