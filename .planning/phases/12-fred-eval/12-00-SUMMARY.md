---
phase: 12-fred-eval
plan: 00
subsystem: testing
tags: [phase-12, wave-0, test-infrastructure, fred, eval-harness, strict-xfail, freezegun, python-frontmatter]

# Dependency graph
requires:
  - phase: 11-subagents
    provides: synthetic-fixture-only-in-CI policy (D-02) mirrored into tests/fixtures/fred/README.md
  - phase: 10-claude-skill
    provides: .claude/skills/mortgage-ops/SKILL.md routing structure that Plan 12-03 extends
  - phase: 09-persistence
    provides: orchestration/lockfile.mjs withLock pattern to port into lib/fred_cache.with_cache_lock
provides:
  - 5 strict-xfail test files covering every Phase 12 requirement (LIVE-01..04 + EVAL-01..04)
  - evals/ package skeleton with explicit __init__.py + prompts/, expected/, runs/ subdirs
  - tests/fixtures/fred/ scaffold with README documenting synthetic-only-in-CI rationale
  - freezegun (TTL boundary mocking) + python-frontmatter (eval prompt parsing) dev-deps
  - .gitignore entries for data/cache/fred_*.json + data/cache/.fred-cache.lock + evals/runs/*
affects: [12-fred-eval, plans 12-01 through 12-08, fred-cli, fred-cache, evals-runner, evals-metrics, skill-md-fred]

# Tech tracking
tech-stack:
  added:
    - freezegun==1.5.5 (TTL boundary mocking for 7-day cache tests)
    - python-frontmatter==1.1.0 (eval prompt frontmatter parsing)
  patterns:
    - Wave-0-strict-xfail-then-flip discipline (inherited from Phases 4/5/7/9/11)
    - Anchored xfail stubs (assertions force fail until later wave ships the target)
    - Per-line type-ignore on imports of not-yet-existing modules
    - evals/ as explicit Python package (not namespace) for unambiguous mypy discovery

key-files:
  created:
    - tests/test_fred_cli.py
    - tests/test_fred_cache.py
    - tests/test_evals_runner.py
    - tests/test_evals_metrics.py
    - tests/test_skill_md_fred.py
    - tests/fixtures/fred/README.md
    - tests/fixtures/fred/.gitkeep
    - evals/__init__.py
    - evals/prompts/.gitkeep
    - evals/expected/.gitkeep
    - evals/runs/.gitkeep
  modified:
    - pyproject.toml (added freezegun + python-frontmatter to dev-deps)
    - uv.lock (refreshed)
    - .gitignore (added Phase 12 FRED cache + evals/runs entries)

key-decisions:
  - "Promoted evals/.gitkeep to evals/__init__.py (explicit package, not namespace) per executor success_criteria"
  - "Anchored test_every_prompt_has_paired_oracle to non-empty prompts dir to prevent XPASS-strict via vacuous truth"
  - "Anchored test_skill_md_does_not_use_shell_injection_syntax to presence of '## Live Mortgage Rates' heading so the absence-check is not load-bearing until Plan 12-03 ships the section"
  - "Per-line `# type: ignore[import-not-found]` on first import of evals.metrics / evals.runner / lib.fred_cache; duplicate imports in later tests need no ignore (mypy reports import-not-found once per module per file)"
  - "Used `freezegun` as top-level module-level import (not inline) for ruff I001 compliance"

patterns-established:
  - "Strict-xfail stubs MUST include assertions that fail until the target ships — empty-loop / absence-check tests need anchors to avoid XPASS-strict"
  - "Cache fixture schema pins JSON value field as STRING (D-19 money discipline carries forward to all FRED cache artifacts)"
  - "SCRIPT_PATH constant for scripts/fred_cli.py points directly into .claude/skills/mortgage-ops/scripts/ — no project-root → skill-folder relocation pass (diverges from Phase 3/8 pattern per D-12-LIVE01-01)"

requirements-completed: []

# Metrics
duration: ~30min
completed: 2026-05-13
---

# Phase 12 Plan 00: test-infrastructure Summary

**Wave-0 strict-xfail stubs covering all 8 Phase 12 requirements (LIVE-01..04 + EVAL-01..04) + evals/ package scaffold + tests/fixtures/fred/ + freezegun/python-frontmatter dev-deps**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-13T17:23:00Z (approximate)
- **Completed:** 2026-05-13T17:52:53Z
- **Tasks:** 2 (plus 1 follow-up correction commit)
- **Files modified:** 14

## Accomplishments

- **5 test files with 22 base + 7 parametric xfail-decorated stubs** anchoring every Phase 12 requirement (LIVE-01..04 + EVAL-01..04) so Waves 1-7 land into a fail-then-flip safety net.
- **evals/ package** with explicit `__init__.py` + `prompts/`, `expected/`, `runs/` subdir seams — Plans 12-04 (runner + metrics), 12-05 (prompts), 12-06 (oracles) have their landing targets.
- **tests/fixtures/fred/** + README documenting the synthetic-only-in-CI policy (Phase 11 D-02 inheritance) and the FRED live-capture promotion recipe.
- **Phase 12 dev-deps pinned**: freezegun>=1.5 (resolved 1.5.5) for TTL boundary mocking, python-frontmatter>=1.1 (resolved 1.1.0) for eval prompt parsing. `uv sync --locked --dev` succeeds.
- **`.gitignore` extended** for Data Layer (cache JSON + lockfile) and System Layer write target (evals/runs/) per DATA_CONTRACT.md.
- **600 passed / 5 skipped / 30 xfailed** — no regressions to Phases 1-11 tests; all 29 new xfails surface as XFAIL (not XPASS, not ERROR).

## Task Commits

1. **Task 1: Scaffold evals/ tree, tests/fixtures/fred/, gitignore + pyproject.toml dev-deps** — `9e2de90` (chore)
2. **Task 2: Create 5 Wave-0 strict-xfail test stubs covering all 8 Phase 12 requirements** — `ec6363e` (test)
3. **Follow-up correction: Promote evals/.gitkeep to evals/__init__.py** — `22f91c4` (chore)

_All commits used `--no-verify` per parallel-executor protocol. No Co-Authored-By or AI-attribution trailers per global CLAUDE.md rule + project CLAUDE.md._

## Files Created/Modified

### Created
- `tests/test_fred_cli.py` — 4 xfail stubs (5 with MORTGAGE15US parametrize). LIVE-01 (SCRIPT_PATH existence + --help <300ms lazy-import + always-exit-0 envelope on missing FRED_API_KEY) + LIVE-04 (MORTGAGE15US support).
- `tests/test_fred_cache.py` — 4 xfail stubs using `freezegun.freeze_time` for 6d23h59m/7d0h/8d boundary cases (D-12-LIVE02-01 strict-`<` 7-day TTL) plus `with_cache_lock` port-of-`withLock` contract.
- `tests/test_evals_runner.py` — 6 xfail stubs (12 with mode parametrize). EVAL-01 (22-prompt set per D-12-SC1-01), SC-5 (every mode has ≥1 prompt), EVAL-02 (paired oracles), EVAL-03 + D-12-SC4-01 (three-bucket gate denominator excludes skip).
- `tests/test_evals_metrics.py` — 5 xfail stubs. EVAL-04 + D-12-SC3-01 STDOUT-only sourcing (prose-only fails, cmd-arg-only fails, stdout-sourced passes, `provenance: static` exempt) + D-12-SC4-01 NumericScore enum shape.
- `tests/test_skill_md_fred.py` — 3 xfail stubs. LIVE-02 + D-12-LIVE02-01 (`## Live Mortgage Rates` heading + four required token references + shell-injection-syntax absence).
- `tests/fixtures/fred/README.md` — synthetic-only-in-CI rationale + live-capture recipe + "what NOT to put here" guardrails (no API keys, no live transcripts, no AI-attribution).
- `tests/fixtures/fred/.gitkeep` — dir-preservation seam for the fixtures landing target.
- `evals/__init__.py` — explicit package init with docstring pointing at later waves' landing targets.
- `evals/prompts/.gitkeep` — Wave-5 fill target (22 prompt MDs).
- `evals/expected/.gitkeep` — Wave-6 fill target (paired oracle JSONs).
- `evals/runs/.gitkeep` — eval-runner output target (System Layer per DATA_CONTRACT.md; gitignored except this seam).

### Modified
- `pyproject.toml` — added `freezegun>=1.5` + `python-frontmatter>=1.1` to `[dependency-groups].dev` (alphabetical order preserved).
- `uv.lock` — refreshed after `uv sync --dev`.
- `.gitignore` — appended Phase 12 section: `data/cache/fred_*.json`, `data/cache/.fred-cache.lock` (Data Layer), `evals/runs/*` with `!evals/runs/.gitkeep` exception (System Layer write target).

## Decisions Made

- **Promoted `evals/.gitkeep` → `evals/__init__.py`.** The plan's `files_modified` originally listed `evals/.gitkeep`, but the executor success_criteria explicitly required `evals/__init__.py`. The `__init__.py` makes `evals/` an explicit package (vs namespace), preserves the dir, and is the clearer artifact for mypy package discovery when Plans 12-04 ship `evals/runner.py` + `evals/metrics.py`. Net: one fewer file, same dir-preservation semantics.
- **Anchored XPASS-strict failures with positive assertions.** Two stubs initially passed under strict-xfail because of vacuous truth: `test_every_prompt_has_paired_oracle` looped over an empty `evals/prompts/*.md` glob, and `test_skill_md_does_not_use_shell_injection_syntax` ran an absence-grep against a SKILL.md that has no FRED section yet. Both now lead with an anchor assertion (prompts dir non-empty / heading present) that forces the xfail until the target wave lands.
- **Used module-level `import freezegun`** in `tests/test_fred_cache.py` to satisfy ruff I001 (consistent import block ordering) and TC003 (move standard-library imports into a TYPE_CHECKING block — `Path` is only used as an annotation in that file since `tmp_path` is already typed at the framework level).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] XPASS-strict failures on two empty-loop / no-target-yet stubs**
- **Found during:** Task 2 (test stub verification)
- **Issue:** Two strict-xfail stubs vacuously passed — `test_every_prompt_has_paired_oracle` had no prompts to iterate over (empty `evals/prompts/`), and `test_skill_md_does_not_use_shell_injection_syntax` ran an absence-grep against a SKILL.md without the FRED section, so the `re.findall` returned `[]` and the assertion succeeded.
- **Fix:** Added a leading anchor assertion to each test that fails until the target lands: prompts dir non-empty (Plan 12-05 trigger) and `## Live Mortgage Rates` heading present (Plan 12-03 trigger). Strict-xfail discipline now holds — both surface as XFAIL, not XPASS.
- **Files modified:** `tests/test_evals_runner.py`, `tests/test_skill_md_fred.py`
- **Verification:** `uv run pytest tests/test_fred_*.py tests/test_evals_*.py tests/test_skill_md_fred.py` reports `29 xfailed` (zero XPASS, zero errors).
- **Committed in:** `ec6363e` (Task 2 commit — anchors were added as part of the same task, not a separate fix commit, since they're part of the test-stub design)

**2. [Rule 1 - Bug] Ruff TC003 + I001 + PT018 violations on first draft of `tests/test_fred_cache.py`**
- **Found during:** Task 2 (lint pass)
- **Issue:** Inline `import freezegun` inside each test body triggered I001 (import sorting); standalone `from pathlib import Path` triggered TC003 (annotation-only use should go in `TYPE_CHECKING` block); compound `assert "pid" in data and "acquired_at" in data` triggered PT018 (break into separate asserts).
- **Fix:** Moved `import freezegun` to module top; moved `Path` import into `TYPE_CHECKING` block; split the compound lock-content assertion into two individual asserts.
- **Files modified:** `tests/test_fred_cache.py`
- **Verification:** `uv run ruff check tests/test_fred_*.py tests/test_evals_*.py tests/test_skill_md_fred.py` → "All checks passed!"
- **Committed in:** `ec6363e` (Task 2 commit)

**3. [Rule 1 - Bug] mypy `dict` generic missing type args + `import-not-found` on not-yet-existing modules**
- **Found during:** Task 2 (mypy --strict pass)
- **Issue:** `sub_calls: list[dict]` triggered `type-arg` strict-mode error; imports of `evals.metrics`, `evals.runner`, `lib.fred_cache`, and `frontmatter` all triggered `import-not-found` / `import-untyped` because the modules either don't exist yet (filled by Plans 12-02..04) or have no py.typed marker.
- **Fix:** Annotated all helper lists as `list[dict[str, object]]`. Added `# type: ignore[import-not-found]` on the FIRST import of each future module per test file; subsequent imports in the same file need no ignore (mypy reports each missing module once). Added `# type: ignore[import-untyped]` on the `frontmatter` import (the package has no type stubs and we don't want to add it to `[[tool.mypy.overrides]]` for a single test-file import).
- **Files modified:** `tests/test_evals_metrics.py`, `tests/test_evals_runner.py`, `tests/test_fred_cache.py`
- **Verification:** `uv run mypy tests/test_fred_*.py tests/test_evals_*.py tests/test_skill_md_fred.py` → "Success: no issues found in 5 source files".
- **Committed in:** `ec6363e` (Task 2 commit)

**4. [Rule 2 - Missing Critical] `evals/__init__.py` over `evals/.gitkeep`**
- **Found during:** Post-Task-1 reconciliation against executor success_criteria
- **Issue:** Plan's `files_modified` listed `evals/.gitkeep`, but executor invocation success_criteria explicitly required `evals/__init__.py`. The explicit init module is necessary so mypy treats `evals/` as a defined package (vs namespace) when Plans 12-04 land `evals/runner.py` + `evals/metrics.py`.
- **Fix:** `git rm evals/.gitkeep` + write `evals/__init__.py` with a module docstring pointing at later-wave landing targets.
- **Files modified:** `evals/__init__.py` (created), `evals/.gitkeep` (removed)
- **Verification:** `uv run pytest` still reports 600 passed; the new file is committed as a separate atomic chore commit.
- **Committed in:** `22f91c4` (separate chore commit because the change spanned a removal + addition and the original Task 1 commit had already shipped)

---

**Total deviations:** 4 auto-fixed (3 Rule 1 bugs caught during verification, 1 Rule 2 missing-critical reconciliation against success_criteria).
**Impact on plan:** All four were strictly necessary for the success criteria (pytest xfail discipline, mypy --strict + ruff clean, explicit package shape). No scope creep — every fix served the plan's stated done criteria.

## Issues Encountered

- **`uv sync --locked --dev` cache replay needed a follow-up plain `uv sync --dev`** to install the new dev-deps into the local venv (the lock entry was added but `--locked` mode doesn't install when the lock had no resolution diff in the cache yet). Resolved by running `uv sync --dev` once, then `uv sync --locked --dev` to confirm the lock is fully resolved.
- **`freezegun` shows `__version__` but `frontmatter` does not** (`python-frontmatter` exposes `frontmatter.load` but no version attr). Substituted `hasattr(frontmatter, "load")` for the import-verification probe — both packages load and the API surface that the later tests need is present.

## TDD Gate Compliance

Plan 12-00 frontmatter type is `execute`, not `tdd`. Task 2 carried `tdd="true"` in the plan, but in the Wave-0 strict-xfail context the "RED" phase is the xfail itself — there is no GREEN gate in this plan because Plans 12-01..06 hold the GREEN-flip responsibility. The test commit `ec6363e` (`test(12-00):`) is the RED gate; the corresponding GREEN commits are deferred to the wave plans that flip each xfail.

No TDD gate-sequence violations.

## User Setup Required

None — no external service configuration. The `FRED_API_KEY` env var that Plans 12-01..02 will need is documented in `tests/fixtures/fred/README.md` (live-capture recipe) but is NOT required by any Wave-0 test.

## Next Phase Readiness

- **Plan 12-01 (LIVE-01 + LIVE-04 — `scripts/fred_cli.py`):** All test stubs in place; flipping requires shipping the script + lazy-import discipline + always-exit-0 envelope + MORTGAGE15US support.
- **Plan 12-02 (LIVE-03 — `lib/fred_cache.py`):** All boundary tests in place with `freezegun`; flipping requires `is_fresh`, `StaleCacheWarning`, `warn_if_stale`, `with_cache_lock`.
- **Plan 12-03 (LIVE-02 — SKILL.md FRED section):** Shell-injection guard test is anchored to heading presence; flipping requires shipping the verbatim `## Live Mortgage Rates` section per D-12-LIVE02-01 + 4 required token references.
- **Plan 12-04 (EVAL-03 + EVAL-04 — `evals/runner.py` + `evals/metrics.py`):** `evals/__init__.py` already in place; runner needs `HarnessReport` dataclass with three-bucket aggregator; metrics needs `NumericScore` enum + `score_numeric_match` + `score_route_match` + STDOUT-only `detect_hallucinations`.
- **Plan 12-05 (EVAL-01 + D-12-SC1-01 — 22 prompts):** `evals/prompts/.gitkeep` is the landing target.
- **Plan 12-06 (EVAL-02 — 22 oracles):** `evals/expected/.gitkeep` is the landing target.
- **No blockers** — every Phase 12 wave has a deterministic flip target.

## Self-Check: PASSED

Verified each created file exists and each commit is in `git log`:

- FOUND: `tests/test_fred_cli.py`
- FOUND: `tests/test_fred_cache.py`
- FOUND: `tests/test_evals_runner.py`
- FOUND: `tests/test_evals_metrics.py`
- FOUND: `tests/test_skill_md_fred.py`
- FOUND: `tests/fixtures/fred/.gitkeep`
- FOUND: `tests/fixtures/fred/README.md`
- FOUND: `evals/__init__.py`
- FOUND: `evals/prompts/.gitkeep`
- FOUND: `evals/expected/.gitkeep`
- FOUND: `evals/runs/.gitkeep`
- FOUND commit: `9e2de90` (Task 1)
- FOUND commit: `ec6363e` (Task 2)
- FOUND commit: `22f91c4` (post-task __init__.py promotion)

Verification commands ran successfully:
- `uv run pytest` → 600 passed, 5 skipped, 30 xfailed
- `uv run pytest tests/test_fred_*.py tests/test_evals_*.py tests/test_skill_md_fred.py` → 29 xfailed
- `uv run ruff check tests/test_fred_*.py tests/test_evals_*.py tests/test_skill_md_fred.py` → All checks passed
- `uv run mypy tests/test_fred_*.py tests/test_evals_*.py tests/test_skill_md_fred.py` → Success: no issues found in 5 source files
- `uv sync --locked --dev` → Resolved 50 packages in 4ms (lock in sync)

---
*Phase: 12-fred-eval*
*Completed: 2026-05-13*
