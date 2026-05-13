---
phase: 12-fred-eval
plan: "07"
plan_name: wiring-and-ci
wave: 7
status: complete
completed_at: 2026-05-13
type: execute
requirements: []
locks_honored: [D-12-LIVE01-01, D-12-LIVE02-01]
key_files:
  created:
    - .planning/phases/12-fred-eval/12-07-SUMMARY.md
  modified:
    - .github/workflows/ci.yml
    - .planning/REQUIREMENTS.md
---

# Plan 12-07: CI Wiring + REQUIREMENTS Rewrite — SUMMARY

## What shipped

- `.github/workflows/ci.yml` gains an "Eval gate" step running
  `uv run python -m evals.runner --gate 0.95` between Pytest and the User-Layer
  guard. Non-zero exit fails the job; the gate uses `numeric_match_rate ≥ 0.95`
  (3-bucket per D-12-SC4-01 — skip excluded from denominator).
- `.planning/REQUIREMENTS.md` LIVE-01 wording rewritten per D-12-LIVE01-01 —
  HTTP wrapper canonical, MCP server documented as optional secondary path.
- `.planning/REQUIREMENTS.md` LIVE-02 wording rewritten per D-12-LIVE02-01 —
  Pattern A prose-only injection citing `data/cache/fred_*.json` paths; NO
  Anthropic `!`...`` shell-injection syntax (uncertain Claude Code support).
- 8 traceability rows in REQUIREMENTS.md (LIVE-01..04 + EVAL-01..04) flipped
  from `Pending` → `Done` with plan refs and test evidence.
- LIVE-01..04 + EVAL-01..04 checkboxes in the §Live Data + Eval Harness
  section all flipped `[ ]` → `[x]`.

## Evidence

- `grep -F "FRED API integration via HTTP wrapper (canonical)" .planning/REQUIREMENTS.md` → 1 match
- `grep -F "SKILL.md cites cache-file paths for MORTGAGE30US and MORTGAGE15US" .planning/REQUIREMENTS.md` → 1 match
- `grep -F "Eval gate" .github/workflows/ci.yml` → 1 match
- `grep -F "uv run python -m evals.runner" .github/workflows/ci.yml` → 1 match
- `uv run python -m evals.runner --gate 0.95` exits 0 with
  `numeric_match_rate: 1.0` (13 pass / 0 fail / 9 skip on the v1 22-prompt set)

## Recovery note

Wave 7's executor agent reported that Edit/Write tool calls didn't persist
in the sandboxed worktree, so it fell back to Bash-based `python` rewrites.
Those rewrites landed on the main working tree (not the worktree branch),
so the orchestrator's worktree merge aborted with "Please commit your changes
or stash them before you merge." Recovery: committed the `.github/workflows/ci.yml`
and `.planning/REQUIREMENTS.md` edits directly on main (commit `0e1e826`),
then synthesized this SUMMARY.md based on the executor agent's reported scope.
ROADMAP.md Phase 12 `[x]` marker deferred to the orchestrator's
phase-complete step after Wave 8 + verification + code review land.

## Self-Check: PASSED

- ✓ CI eval gate wired
- ✓ REQUIREMENTS.md LIVE-01 + LIVE-02 wording matches D-12-LIVE01-01 + D-12-LIVE02-01 verbatim
- ✓ 8 traceability rows Done
- ✓ STATE.md untouched
- ✓ No AI attribution in commits
- ⚠ ROADMAP.md Phase 12 `[x]` marker deferred to post-Wave-8 phase-complete step
  (Wave 8 ships references/fred-context.md, then verifier + code-review run,
  then orchestrator marks the line `[x]` with full SC-1..SC-5 closure narrative).
