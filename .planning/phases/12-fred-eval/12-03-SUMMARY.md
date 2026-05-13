---
phase: 12-fred-eval
plan: 03
subsystem: skill-md
tags: [phase-12, wave-3, skill-md, prose-only-injection, pattern-a, fred, live-rates, live-02]

# Dependency graph
requires:
  - phase: 10-claude-skill
    provides: "SKILL.md ≤500 lines / ≤4500 cl100k tokens budget; `## Math Discipline` anchor section"
  - phase: 12-fred-eval (Plan 12-02)
    provides: "scripts/fred_cli.py HTTP wrapper + data/cache/fred_*.json 7-day cache"
provides:
  - "SKILL.md `## Live Mortgage Rates` section per D-12-LIVE02-01 verbatim (Pattern A prose-only injection)"
  - "Cache-miss recovery prose: routes Claude to fred_cli.py on stale/missing cache; envelope `error` field is the recovery contract per Pitfall 1"
  - "3 LIVE-02 acceptance tests flipped green (heading, citations, no-shell-injection)"
  - "3 supplementary tests: token budget post-insert, line budget post-insert, positional ordering"
affects: [12-04-eval-metrics, 12-05-eval-prompts, 12-06-eval-oracles, 12-07-ci-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern A prose-only skill injection: cache-file references via Read tool, NOT `!`...`` shell-injection (Open Q1 unresolved per 12-RESEARCH.md)"
    - "Cache-miss recovery via envelope `error` field (script always exits 0; non-zero exits NOT expected)"
    - "TDD RED/GREEN gate sequence: test() commit precedes feat() commit (Phase 12 wave-3 closure)"

key-files:
  created: []
  modified:
    - ".claude/skills/mortgage-ops/SKILL.md (added 19-line `## Live Mortgage Rates` section between `## Mode Routing` and `## Math Discipline`)"
    - "tests/test_skill_md_fred.py (flipped 3 xfails to green; added 3 supplementary tests)"

key-decisions:
  - "Use Pattern A (prose-only injection) per D-12-LIVE02-01 — `!`...`` shell-injection syntax forbidden because Anthropic Claude Code support is unverified (Open Q1)."
  - "Insert the section BEFORE `## Math Discipline` (per PATTERNS line 174) and AFTER `## Mode Routing` end — keeps the first-200-line routing budget intact (SKLL-02 inheritance)."
  - "Cache-miss recovery prose explicitly documents the envelope `error` field as the recovery contract (Pitfall 1) — narrate the error and ask user manually if FRED_API_KEY missing."
  - "Use the existing `tests._skill_helpers.count_tokens` helper (not the plan-referenced `count_cl100k_tokens`, which doesn't exist) — Rule 3 blocking fix."

patterns-established:
  - "Pattern A prose-only injection: SKILL.md cites cache-file paths (`data/cache/fred_*.json`) so Claude loads rates via the Read tool when the borrower asks current-rate questions; no shell-execution at skill load time."
  - "Cache recovery prose adjacency: every cache-citing section in SKILL.md should be followed by a recovery paragraph documenting the refresh command + envelope-error narration contract."

requirements-completed: [LIVE-02]

# Metrics
duration: ~10min
completed: 2026-05-13
---

# Phase 12 Plan 03: SKILL.md FRED Live Rate Section Summary

**Inserted D-12-LIVE02-01 verbatim `## Live Mortgage Rates` section into SKILL.md using Pattern A (prose-only injection with cache-file references), closing LIVE-02 at the skill layer with grep-verifiable contract.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-13T18:14:00Z
- **Completed:** 2026-05-13T18:16:21Z
- **Tasks:** 1 (single TDD task with RED + GREEN commits)
- **Files modified:** 2 (`.claude/skills/mortgage-ops/SKILL.md`, `tests/test_skill_md_fred.py`)

## Accomplishments

- SKILL.md gains the verbatim D-12-LIVE02-01 `## Live Mortgage Rates` section between `## Mode Routing` and `## Math Discipline`.
- All four required tokens present in SKILL.md: `MORTGAGE30US`, `MORTGAGE15US`, `data/cache/fred_MORTGAGE30US.json`, `scripts/fred_cli.py` (plus `data/cache/fred_MORTGAGE15US.json`).
- Pattern A enforced: forbidden grep `!\`[^\`]*fred[^\`]*\`` returns zero matches.
- SKILL.md budgets preserved: 276 lines (≤500), 3677 cl100k tokens (≤4500 — D-02 10% margin under 5000 Anthropic spec).
- 3 LIVE-02 Wave-0 xfails flipped green: heading, citations, no-shell-injection.
- 3 supplementary tests added: token-budget-post-insert, line-budget-post-insert, positional-ordering.
- Phase 10 `test_skill_md_under_token_budget` + `test_skill_md_under_line_budget` still pass (no regression).
- Full test suite green: 617 passed, 5 skipped, 18 xfailed (all expected future-wave stubs).

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): flip Wave-0 xfails + add 3 supplementary tests** — `df8d08c` (test)
2. **Task 1 (GREEN): insert `## Live Mortgage Rates` section into SKILL.md** — `00b4ac7` (feat)

No REFACTOR commit needed — the inserted prose is the verbatim D-12-LIVE02-01 text plus the plan-specified cache-miss recovery paragraph; no cleanup applicable.

## Files Created/Modified

- `.claude/skills/mortgage-ops/SKILL.md` — inserted 19-line section (heading + 8-line verbatim D-12-LIVE02-01 block + 8-line cache-miss recovery paragraph). Section appears at lines 54-72; `## Math Discipline` now starts at line 73.
- `tests/test_skill_md_fred.py` — module docstring updated to Wave-3 closure narrative; 3 xfail decorators removed; 3 supplementary tests added (token budget, line budget, positional ordering); `pytest` import removed (no longer needed since no xfails remain).

## Verbatim Inserted Text (for future-you audit)

```markdown
## Live Mortgage Rates

Latest weekly rates (refreshed via `scripts/fred_cli.py` on weekly cron;
cached 7 days max in `data/cache/fred_MORTGAGE30US.json`):

- 30-yr fixed (MORTGAGE30US): see cache file `data/cache/fred_MORTGAGE30US.json`
  field `value`
- 15-yr fixed (MORTGAGE15US): see cache file `data/cache/fred_MORTGAGE15US.json`

Skill loads these via Read tool when borrower asks 'what's the current rate?'

If the cache file is absent or stale (>7 days old), invoke
`python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE30US --latest`
yourself to refresh; the script writes the cache and emits the value to stdout.
The script ALWAYS exits 0 — if the envelope's `error` field is non-null
(e.g., FRED_API_KEY missing), narrate the error and ask the user for the
current rate manually. Per D-12-LIVE02-01 + Pitfall 1, the envelope `error`
field is the recovery contract; non-zero exit codes are NOT expected here.
```

Lines 1-9 are verbatim from CONTEXT.md D-12-LIVE02-01 (lines 38-48); lines 11-18 are the plan-specified cache-miss recovery paragraph (CONTEXT.md lines 50-51 expanded with envelope-error narration contract per Pitfall 1).

## Token + Line Budget Audit

| Metric         | Phase 10 ship | Phase 12 Plan 03 ship | Headroom (target ≤) |
| -------------- | ------------- | --------------------- | ------------------- |
| Lines          | 257           | 276 (+19)             | 500                 |
| cl100k tokens  | 3419          | 3677 (+258)           | 4500                |

Section adds 19 lines and ~258 cl100k tokens — well within both budgets.

(Note: the plan's section-size estimate was ~12 lines / ~80 tokens. The realized delta is ~19 lines / ~258 tokens because the cache-miss recovery paragraph is more substantial than the bare 2-line snippet sketched in CONTEXT.md — the executor expanded it to include the envelope-error narration contract from Pitfall 1, which buys explicit recovery guidance for Claude at the cost of a small budget delta. Both budgets still hold with substantial headroom.)

## Pattern A vs B Decision Rationale

**Selected: Pattern A (prose-only injection)** per D-12-LIVE02-01.

Pattern A:
- SKILL.md cites cache-file paths in prose; Claude reads them via the Read tool when borrowers ask current-rate questions.
- Forbidden: `!`...`` shell-injection syntax (Anthropic-documented but Claude Code support unverified per 12-RESEARCH.md Open Question 1).
- Grep contract is deterministic: 4 required tokens must appear; forbidden regex must not match.

Pattern B (rejected for v1):
- Would inline `!`python scripts/fred_cli.py ...`` shell-injection at skill load time.
- Unverified Claude Code support → high risk of "skill loads but rate not injected, silently fails open."
- Defer to v2 if/when Anthropic publishes Claude Code shell-injection support guarantees.

The grep-based test contract enforces this decision permanently: regression to Pattern B would fail `test_skill_md_does_not_use_shell_injection_syntax`.

## Decisions Made

- **Helper symbol fix (Rule 3 blocking):** plan referenced `tests._skill_helpers.count_cl100k_tokens` which doesn't exist; the actual helper is `tests._skill_helpers.count_tokens`. Used the correct symbol in the new test.
- **Budget threshold (Rule 2 alignment):** plan's `test_skill_md_token_budget_after_phase12_insert` sketched a soft 4500 check and a hard 5000 check. The existing Phase 10 `test_skill_md_under_token_budget` enforces ≤4500 (D-02 10% margin under 5000 Anthropic spec). Aligned the new test to the same 4500 threshold to avoid contract drift — one canonical budget enforced in two places.
- **Removed `pytest` import (cleanup):** with all xfails removed, `pytest` was an unused import. Removed it to keep the test module clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wrong helper symbol in plan's test sketch**
- **Found during:** Task 1 RED phase (writing supplementary tests)
- **Issue:** Plan referenced `from tests._skill_helpers import count_cl100k_tokens`, but the actual helper exported by that module is `count_tokens`. Importing a non-existent symbol would cause an `ImportError` at test collection, blocking the entire test suite.
- **Fix:** Used `from tests._skill_helpers import count_tokens` in `test_skill_md_token_budget_after_phase12_insert`.
- **Files modified:** `tests/test_skill_md_fred.py`
- **Verification:** `uv run pytest tests/test_skill_md_fred.py -v` collects and runs all tests successfully.
- **Committed in:** `df8d08c` (RED commit)

**2. [Rule 2 - Missing Critical] Aligned token budget threshold with Phase 10 canon**
- **Found during:** Task 1 RED phase (writing supplementary tests)
- **Issue:** Plan sketched a dual-threshold test (hard 5000, soft 4500). The existing Phase 10 `test_skill_md_under_token_budget` already enforces ≤4500 (D-02 10% margin under 5000 Anthropic spec). Two tests with different thresholds for the same budget would drift over time.
- **Fix:** Aligned the new test to enforce only ≤4500 cl100k tokens, matching Phase 10 canon. Single canonical budget enforced consistently.
- **Files modified:** `tests/test_skill_md_fred.py`
- **Verification:** Both Phase 10 and Phase 12 budget tests pass with the same 4500 cap.
- **Committed in:** `df8d08c` (RED commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking, 1 Rule 2 missing critical)
**Impact on plan:** Both auto-fixes essential for correctness; no scope creep. The plan's test sketch contained one symbol error and one budget-drift risk; both were corrected inline.

## Issues Encountered

None — TDD RED + GREEN cycle completed cleanly. RED phase confirmed 4 of 6 tests failed (the 4 section-presence tests); the 2 budget tests passed in RED because current-state SKILL.md was already under budget. GREEN phase made all 6 tests pass with no further iteration.

## TDD Gate Compliance

Plan type is `execute` (not `tdd`), but Task 1 has `tdd="true"`. RED/GREEN gate sequence satisfied:

- RED gate: `df8d08c` (`test(12-03): flip Wave-0 xfails + add token/line/positioning tests for FRED section`)
- GREEN gate: `00b4ac7` (`feat(12-03): insert Live Mortgage Rates section into SKILL.md (Pattern A prose-only)`)
- REFACTOR gate: not needed (verbatim D-12-LIVE02-01 + plan-specified prose; no cleanup applicable)

## User Setup Required

None — no external service configuration required. (FRED_API_KEY env var setup is documented separately in Plan 12-01/12-02 USER-SETUP context; this plan only touches SKILL.md prose.)

## Next Phase Readiness

- LIVE-02 closed at the SKILL.md layer per D-12-LIVE02-01. The skill now cites both FRED series + cache paths + the refresh script + the envelope-error recovery contract.
- Plan 12-04 (eval-runner metrics) can safely depend on the SKILL.md `## Live Mortgage Rates` section being present — eval prompts that ask "what's the current 30-year fixed rate?" can credit the Read invocation against the cache fixture.
- Plan 12-05 (live-rate-injection-01 prompt per D-12-SC1-01) has the SKILL.md anchor it needs.
- No blockers for downstream Phase 12 plans.

## Self-Check: PASSED

- **Files modified verified:**
  - `.claude/skills/mortgage-ops/SKILL.md` — FOUND, contains `## Live Mortgage Rates` heading
  - `tests/test_skill_md_fred.py` — FOUND, 6 tests defined, 0 xfail decorators remaining
- **Commits verified:**
  - `df8d08c` (RED) — FOUND in `git log`
  - `00b4ac7` (GREEN) — FOUND in `git log`
- **Smoke greps verified:** all 6 required tokens present, forbidden shell-injection grep returns zero.
- **Budgets verified:** 276 lines (≤500), 3677 cl100k tokens (≤4500).
- **Full suite verified:** 617 passed, 5 skipped, 18 xfailed (all expected); no regressions.

---
*Phase: 12-fred-eval*
*Completed: 2026-05-13*
