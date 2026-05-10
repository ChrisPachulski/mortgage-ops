---
phase: 11-subagents
plan: 02
subsystem: subagents
tags: [phase-11, subagents, refi-npv-agent, sonnet, suba-02]

# Dependency graph
requires:
  - phase: 11
    provides: Wave 0 scaffold (xfail SUBA-02 stub, _split_frontmatter helper, AGENTS_DIR/REQUIRED_FRONTMATTER_KEYS constants, anthropic==0.100.0 dev pin)
  - phase: 11
    provides: Wave 1 5-section body template + skill-resident path discipline + spec-citation footer pattern (mirrored here for refi-npv-agent shape consistency)
  - phase: 6
    provides: (soft, downstream) scripts/refi_npv.py + RefiCashflow sign-convention validator — Phase 11 references the future skill-resident path; live dispatch verification deferred to post-Phase-6 + post-Phase-10
  - phase: 10
    provides: (soft, downstream) skills:[mortgage-ops] frontmatter resolves at agent-spawn time; live dispatch verification deferred to post-Phase-10
provides:
  - .claude/agents/refi-npv-agent.md (124 lines, frontmatter + 5-section body, Sonnet model, tools=[Read, Bash] WITHOUT Write per RESEARCH Open Question 1 v1)
  - SUBA-02 closed (frontmatter parses + name + model=sonnet + skills + description shape + Write-tool-absent assertion, was Wave 0 xfail)
affects: [11-03-stress-test-agent, 11-05-tests-and-fixtures]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subagent frontmatter for Sonnet variant: name + description (>30 chars routing trigger) + model=sonnet + tools (YAML list, NO Write) + skills=[mortgage-ops]"
    - "Tools whitelist exclusion: Write deliberately omitted to keep v1 attack surface narrow per 11-RESEARCH Open Question 1 — output is inline markdown only"
    - "Sign-convention discipline encoded in agent body (Hard rule #2): outflows negative, savings positive — borrower perspective per Phase 6 references/refi-npv.md"
    - "Body horizontal rule uses *** not --- (carried over from Wave 1) so yaml.safe_load is unambiguous about where frontmatter ends"
    - "5-section body template mirrored from Wave 1: hard rules (numbered) -> workflow (numbered) -> cost discipline -> handoff hints -> spec citation footer"
    - "Skill-resident script path .claude/skills/mortgage-ops/scripts/refi_npv.py used verbatim per CLAUDE.md decision #8 + Phase 3 D-17"

key-files:
  created:
    - .claude/agents/refi-npv-agent.md (124 lines, Phase 11 refinance NPV subagent: Sonnet, multi-offer ranking, shells out to scripts/refi_npv.py, returns ranked markdown table sorted by NPV descending)
  modified:
    - tests/test_subagents.py (test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet flipped from xfail stub to real assertion; xfail decorator removed; body uses _split_frontmatter helper from Wave 0 + adds Write-absent assertion per RESEARCH Open Q1)

key-decisions:
  - "Tools list deliberately excludes Write per 11-RESEARCH.md Open Question 1 v1 decision: ship without Write in v1 (inline markdown table sufficient for typical 2-5 offer comparisons; narrows attack surface). Test asserts 'Write' not in tools so any future addition requires an explicit plan + threat-model update."
  - "Use *** instead of --- for the body horizontal rule (carried over from Wave 1). Three-dash horizontal rules anywhere after the frontmatter block can confuse yaml.safe_load on the closing-delimiter scan."
  - "Use ruff PT018-compatible assertion split for description-shape check (separate isinstance + len assertions, with description = fm.get('description') binding). Pattern carried over from Wave 1 — single combined assertion is more concise but PT018 forbids it; the test's intent is unchanged."
  - "Tools list block-style (one per line) rather than flow-style ([Read, Bash]). Both Anthropic-spec accepted; block-style matches Wave 1 shape so all three Phase 11 agent files have consistent visual structure."

patterns-established:
  - "Wave-2+ stub-flip pattern (continuation of Wave 1): drop @pytest.mark.xfail(strict=True) decorator AND replace pytest.fail('Wave 0 stub') body. Skipping either step would emit XPASS (decorator stays) or false-pass (body unchanged). Both must happen in the same edit."
  - "Tools-whitelist exclusion-test pattern: when an agent file deliberately omits a tool (Write here per RESEARCH Open Q1), the SUBA-X test MUST assert the absence ('Write' not in tools) so future plans cannot silently re-add the tool without updating both the agent file AND the threat model."

requirements-completed:
  - SUBA-02

# Metrics
duration: 3.0 min
completed: 2026-05-10
---

# Phase 11 Plan 02: Refi NPV Agent Summary

**Shipped `.claude/agents/refi-npv-agent.md` (Sonnet, multi-offer NPV ranking, shells out to `scripts/refi_npv.py` once per offer, tools=[Read, Bash] WITHOUT Write per RESEARCH Open Q1 v1); flipped Wave 0 SUBA-02 xfail stub to a passing assertion. SUBA-02 closed.**

## Performance

- **Duration:** ~3.0 min
- **Started:** 2026-05-10T16:39:17Z
- **Completed:** 2026-05-10T16:42:18Z
- **Tasks:** 2
- **Files created:** 1 (`.claude/agents/refi-npv-agent.md`)
- **Files modified:** 1 (`tests/test_subagents.py`)

## Accomplishments

- `.claude/agents/refi-npv-agent.md` exists at repo root with valid YAML frontmatter (parses cleanly via `yaml.safe_load`).
- Frontmatter pinned: `name=refi-npv-agent`, `model=sonnet`, `skills=[mortgage-ops]`, `tools=[Read, Bash]` (Write intentionally absent), `description` (374 chars, ~80-char preview: `"Compares 2-5 competing refinance offers (rate-and-term or cash-out) and returns "`).
- Body has all 5 hard rules: never compute NPV inline / borrower-perspective sign convention (outflows negative, savings positive) / `--help` first / READ-ONLY user layer / output format = ranked markdown table sorted by NPV descending with required columns lender + rate + closing_costs + breakeven_months + NPV.
- Body workflow section enumerates 5 steps (receive offers -> check `--help` -> per-offer JSON construction + script invocation + error handling -> rank -> return table + narrative).
- Body cost-discipline section explicitly tells Claude to reject single-offer evaluation and route it back to the main thread; treats Sonnet budget as a discipline target with a ≤2,000-token soft self-check.
- Body handoff-hints section covers single-offer / single-loan amortization / stress sweep / cash-out proceeds / >5 offers branches.
- Skill-resident script path `.claude/skills/mortgage-ops/scripts/refi_npv.py` referenced 4 times in the body (NOT the project-root `scripts/refi_npv.py` — per CLAUDE.md decision #8 + Phase 3 D-17).
- File size: 124 lines (within the 80-200 min/max envelope).
- No `Co-Authored-By` / AI-attribution markers in the agent file or any commit message (CLAUDE.md global rule + project local rule).
- Wave 0 stub `test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet` flipped: xfail decorator removed, body replaced with real assertions using `_split_frontmatter` helper from Wave 0, plus a Write-tool-absent assertion to lock in the RESEARCH Open Q1 v1 decision.
- SUBA-02 test PASSED. Wave 1 SUBA-01 still PASSED (no regression). The other 4 SUBA stubs (SUBA-03/04/05/06) remain xfail/skip exactly as Wave 0 set them.
- Full suite still green: **593 passed, 5 skipped, 4 xfailed, 0 failed, 0 errored** (Wave 1 baseline was 592 passed + 5 skipped + 5 xfailed; Wave 2 delta is +1 passed / -1 xfailed, exactly the SUBA-02 flip).
- mypy `--strict` clean on `tests/test_subagents.py`.
- ruff `check` clean on `tests/test_subagents.py`.
- ruff `format --check` clean on `tests/test_subagents.py`.

## Task Commits

Each task was committed atomically with `--no-verify` (parallel-executor convention):

1. **Task 1: Create `.claude/agents/refi-npv-agent.md` with frontmatter + body** — `e53a27a` (feat)
2. **Task 2: Flip Wave 0 SUBA-02 xfail stub to real assertion** — `7c4062c` (test)

## Files Created/Modified

### Created

- `.claude/agents/refi-npv-agent.md` — 124 lines. Phase 11 refinance NPV subagent definition. Frontmatter (`name=refi-npv-agent` / `description` (374 chars) / `model: sonnet` / `tools: [Read, Bash]` (block-style YAML list, NO Write) / `skills: [mortgage-ops]`) + 5-section body (hard rules -> workflow -> cost discipline -> handoff hints -> Anthropic spec footer). Body references skill-resident path `.claude/skills/mortgage-ops/scripts/refi_npv.py` (4 occurrences); never points at project-root `scripts/refi_npv.py` for the script path. Body footer documents the v1-no-Write decision verbatim per RESEARCH Open Question 1 — any future plan adding Write must explicitly update Hard rule #4 to enumerate household.yml protection (currently the rule covers it semantically; explicit Write protection is belt-and-suspenders if Write returns).

### Modified

- `tests/test_subagents.py` — `test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet` body replaced with real assertions:
  - Asserts `path.exists()` for the agent file
  - Calls `_split_frontmatter(path)` (Wave 0 helper)
  - Asserts no missing keys vs `REQUIRED_FRONTMATTER_KEYS` (`name`, `description`, `model`, `skills`)
  - Asserts `name == "refi-npv-agent"` (filename stem)
  - Asserts `model == "sonnet"` (REQUIREMENTS SUBA-02 pin — Sonnet for multi-step NPV ranking)
  - Asserts `skills == ["mortgage-ops"]`
  - Asserts `description` is a string with `len > 30` (split into two assertions to satisfy ruff PT018 — pattern carried over from Wave 1)
  - **NEW for SUBA-02:** asserts `"Write" not in tools` (locking in RESEARCH Open Q1 v1 decision; the assertion uses `tools = fm.get("tools") or []` so a missing/null tools field doesn't crash — it just means "no Write" trivially)
  - The `@pytest.mark.xfail(strict=True, reason="Wave 0 stub …")` decorator was removed in the same edit (per RESEARCH: a passing-but-still-xfailed test raises XPASS under `strict=True`; flipping requires both body change AND decorator removal).

## Decisions Made

- **Tools list deliberately excludes Write.** Per 11-RESEARCH.md Open Question 1 v1 decision: ship without Write in v1; inline markdown table is sufficient for typical 2-5 offer comparisons; narrows the attack surface. Documented verbatim in the agent body footer + locked in by the SUBA-02 test's `"Write" not in tools` assertion. Any future plan adding Write must update both the agent file AND the test AND the threat-model `<threat_model>` block.
- **Use `***` instead of `---` for the body horizontal rule.** Carried over from Wave 1 — three-dash horizontal rules anywhere after the frontmatter block can confuse `yaml.safe_load` on the closing-delimiter scan.
- **Split the description-shape assertion into two `assert` statements.** ruff's PT018 rule rejects compound `isinstance(x) and len(x) > N`. Splitting into separate `assert isinstance(...)` + `assert len(...) > 30` keeps the test intent unchanged and satisfies the lint gate. Pattern carried over from Wave 1.
- **Block-style YAML tools list.** `tools:\n  - Read\n  - Bash` (one per line) rather than flow-style `tools: [Read, Bash]`. Matches Wave 1's amortization-agent.md visual shape so all three Phase 11 agent files have consistent structure; ruff-friendly; both styles are Anthropic-spec accepted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Split description-shape assertion to satisfy ruff PT018**

- **Found during:** Task 2 verification (`uv run ruff check tests/test_subagents.py`)
- **Issue:** The plan's verbatim Task 2 source used `assert isinstance(fm["description"], str) and len(fm["description"]) > 30, "..."`. ruff's PT018 (in this project's lint set under `PT`) flags compound assertions with `and` as an error: "Assertion should be broken down into multiple parts". This violates the project's lint gate even though the assertion is functionally correct — same issue Wave 1 hit on the SUBA-01 flip.
- **Fix:** Bound `description = fm.get("description")` to a local, then split into two assertions: (a) `assert isinstance(description, str)` with a "must be a string, got {type}" message, (b) `assert len(description) > 30` with a ">30 chars" message. Test intent unchanged: a non-string `description` (or a missing one) fails the first assertion with a precise type-of-actual-value error; a too-short description fails the second with the actual content for traceability. mypy is also happy because the second assertion follows a successful `isinstance` narrowing.
- **Files modified:** `tests/test_subagents.py`
- **Verification:** `uv run ruff check tests/test_subagents.py` -> "All checks passed!"; `uv run mypy --strict tests/test_subagents.py` -> "Success: no issues found"; the SUBA-02 test still PASSED.
- **Committed in:** `7c4062c` (Task 2 commit — fix happened pre-commit, the committed file is the PT018-clean version)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — bug-class).

**Impact on plan:** Single textual fix to the plan's verbatim test source so the test survives the project's ruff lint gate. Zero scope creep, zero behavior change. The frontmatter assertions, the tools-list `Write`-absent assertion, the `_split_frontmatter` helper call, the decorator removal, and all 16 agent-file acceptance criteria all landed exactly as the plan specified.

## Authentication Gates

None encountered. SUBA-02 is filesystem-only; no API keys, no live LLM dispatch, no external network calls.

## Issues Encountered

- The plan's verbatim Task 2 source carried the same compound `isinstance() and len() > N` assertion that Wave 1 hit on SUBA-01. Easy Rule-1 split into two assertions; test intent preserved. Future flip waves (Plan 11-03 for SUBA-03) should use the same split pattern from the start.
- No other surprises — the Wave 0 helper `_split_frontmatter` and the constants `AGENTS_DIR` / `REQUIRED_FRONTMATTER_KEYS` worked as advertised, and Wave 1's body-template + horizontal-rule + line-wrap discipline applied cleanly to refi-npv-agent (124 lines, within 80-200 budget on first write — no rewrap needed unlike Wave 1).

## TDD Gate Compliance

This plan is `type: execute`, not `type: tdd` — the RED/GREEN/REFACTOR gate sequence does not apply. The Wave 0 scaffold pre-shipped the SUBA-02 test stub as `xfail(strict=True)`; this plan's job is the GREEN-equivalent: ship the agent file, then flip the stub to a real assertion. The git history (`feat(11-02): …` immediately followed by `test(11-02): flip SUBA-02 xfail stub …`) reflects the implementation-then-test-flip ordering called out in the plan's Tasks 1 and 2.

## Threat Flags

None. No new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries beyond what the plan's `<threat_model>` already enumerated. The agent file's `tools: [Read, Bash]` whitelist is the in-scope mitigation for T-11-16 (Privilege Escalation via future Write-tool addition), and the SUBA-02 test's `"Write" not in tools` assertion is the test-level lock. T-11-12 (sign-convention tampering) is mitigated by Hard rule #2 + Phase 6's `RefiCashflow` validator. T-11-13 (raw JSON returned) and T-11-14 (NPV paraphrased) are mitigated by Hard rule #1 + Hard rule #5 (output format pin).

## Phase 6 + Phase 10 Live-Dispatch Note

Per the plan's `<dependencies>` section: this agent file CAN be created and the SUBA-02 frontmatter test CAN pass without Phase 6 or Phase 10 — both happened in this plan with no Phase 6 or Phase 10 surface present. However, the agent CANNOT be successfully dispatched in a live Claude Code session until BOTH:

- Phase 6 ships `scripts/refi_npv.py` (REFI-08) — currently does NOT exist; the agent body references the future skill-resident path
- Phase 10 ships `.claude/skills/mortgage-ops/SKILL.md` AND relocates the script to `.claude/skills/mortgage-ops/scripts/refi_npv.py`

Live-dispatch verification (running an actual 3-offer ranking through the agent and asserting the markdown table + narrative shape) is deferred to post-Phase-6 + post-Phase-10. Wave 5 (Plan 11-05) parametrizes `test_SUBA_04` over `EXPECTED_AGENTS` (which includes `refi-npv-agent`), and that test does require Phase 10's skill folder to exist on disk for the smoke check. Wave 5's optional refi-3-offer transcript fixture is a fixture-shape assertion, not a live dispatch.

## Self-Check

Verifying all created files exist and all task commits are reachable in git history:

- `[FOUND]` `.claude/agents/refi-npv-agent.md` (124 lines)
- `[FOUND]` `tests/test_subagents.py` (modified — SUBA-02 stub flipped)
- `[FOUND]` commit `e53a27a` (Task 1: refi-npv-agent.md created)
- `[FOUND]` commit `7c4062c` (Task 2: SUBA-02 xfail flipped)
- `[FOUND]` SUBA-02 test PASSED in pytest output (`tests/test_subagents.py::test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet PASSED`)
- `[FOUND]` Wave 1 SUBA-01 still PASSED (no regression)
- `[FOUND]` Other 4 SUBA stubs still xfail/skip (3 XFAIL on SUBA-03/04/05, 1 SKIPPED on SUBA-06 due to missing `ANTHROPIC_API_KEY`)
- `[FOUND]` Full suite green: 593 passed, 5 skipped, 4 xfailed, 0 failed, 0 errored
- `[FOUND]` mypy `--strict` clean on `tests/test_subagents.py`
- `[FOUND]` ruff `check` clean on `tests/test_subagents.py`
- `[FOUND]` ruff `format --check` clean on `tests/test_subagents.py`
- `[VERIFIED]` Zero `Co-Authored-By` / AI-attribution in agent file or commit messages
- `[VERIFIED]` Body references `.claude/skills/mortgage-ops/scripts/refi_npv.py` (skill-resident path), NOT `scripts/refi_npv.py` (project root)
- `[VERIFIED]` Body contains explicit borrower-perspective sign-convention discipline (Hard rule #2: outflows NEGATIVE, savings POSITIVE)
- `[VERIFIED]` Tools list does NOT contain Write (per RESEARCH Open Question 1 v1 decision)

## Self-Check: PASSED

## Next Plan Readiness

- **Wave 3 (Plan 11-03) unblocked:** SUBA-03 stub `test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku` exists and reports XFAIL; Plan 11-03 ships `.claude/agents/stress-test-agent.md` (Haiku) and flips the stub. Plan 11-03 should mirror the Wave 1 + Wave 2 pattern: 5-section body, `***` not `---` horizontal rule, block-style YAML tools list, `description = fm.get("description")` PT018-compatible split assertion in the test flip.
- **Wave 5 (Plan 11-05) parametrize over `EXPECTED_AGENTS`:** when Wave 5 lands, the parametrized SUBA-04 test will iterate over `("amortization-agent", "refi-npv-agent", "stress-test-agent")` — `amortization-agent` (Wave 1) and now `refi-npv-agent` (Wave 2) are both ready for that re-verification.
- **The 5-section body template + skill-resident path discipline + spec-citation footer pattern is now established across two distinct agents** (Haiku amortization, Sonnet refi-NPV) with structurally identical YAML and body shape. Plan 11-03 should mirror it for stress-test-agent (Haiku, with Write tool re-enabled per its CSV-output mode).

---
*Phase: 11-subagents*
*Plan: 02-refi-npv-agent*
*Completed: 2026-05-10*
