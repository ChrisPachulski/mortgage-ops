---
phase: 10
plan: 01
subsystem: claude-skill
tags: [phase-10, claude-skill, relocation, skll-10, high-risk]
requires:
  - "10-00 (Wave 0 stubs + repo_root fixture)"
  - "Phase 6 COMPLETE (refi_npv.py exists at root)"
  - "Phase 7 COMPLETE (apr_reg_z.py exists at root)"
  - "Phase 8 COMPLETE (stress_test.py + points_breakeven.py exist at root)"
  - "Phase 9 baseline (549 passed, 4 skipped, 17 xfailed)"
provides:
  - "All 7 user-facing calc CLIs physically located at .claude/skills/mortgage-ops/scripts/"
  - "_cli_helpers.py colocated with the CLIs that import it"
  - "SKLL-10 / SC-3 full closure (test_seven_scripts_in_skill_folder_only PASS)"
  - "D-08 cross-phase contract retired"
  - "pyproject.toml with mypy_path + namespace_packages so `from scripts._cli_helpers` resolves under strict typecheck"
affects:
  - "Wave 2 (10-02 SKILL.md scaffold) — routing dispatches to scripts that now exist where SKILL.md will say"
  - "Wave 5 (10-05 CI tests) — SKLL-12 test target paths confirmed"
  - "Phase 11 SUBA-05 — subagents reference relative paths inside skill folder"
tech-stack:
  added: []
  patterns:
    - "git mv preserves rename history (84-100% similarity)"
    - "parents[4] = repo root, parents[1] = skill root for 5-level-deep scripts"
    - "pyproject.toml mypy_path enables namespace-package resolution across moved files"
    - "ruff format auto-applied to multi-line Path constants in test files"
key-files:
  created: []
  modified:
    - ".claude/skills/mortgage-ops/scripts/amortize.py (was scripts/amortize.py)"
    - ".claude/skills/mortgage-ops/scripts/affordability.py (was scripts/affordability.py)"
    - ".claude/skills/mortgage-ops/scripts/arm_simulate.py (was scripts/arm_simulate.py)"
    - ".claude/skills/mortgage-ops/scripts/refi_npv.py (was scripts/refi_npv.py)"
    - ".claude/skills/mortgage-ops/scripts/apr_reg_z.py (was scripts/apr_reg_z.py)"
    - ".claude/skills/mortgage-ops/scripts/stress_test.py (was scripts/stress_test.py)"
    - ".claude/skills/mortgage-ops/scripts/points_breakeven.py (was scripts/points_breakeven.py)"
    - ".claude/skills/mortgage-ops/scripts/_cli_helpers.py (was scripts/_cli_helpers.py)"
    - "tests/test_amortize.py (SCRIPT_PATH constant retargeted)"
    - "tests/test_affordability.py (SCRIPT_PATH constant retargeted)"
    - "tests/test_arm.py (SCRIPT_PATH constant retargeted)"
    - "tests/test_apr.py (SCRIPT_PATH constant retargeted)"
    - "tests/test_refinance.py (SCRIPT_PATH constant retargeted)"
    - "tests/test_stress.py (SCRIPT_PATH constant retargeted)"
    - "tests/test_points.py (SCRIPT_PATH constant retargeted)"
    - "tests/test_cli_helpers.py (sys.path injection extended to skill root)"
    - "tests/test_skill.py (SKLL-10 xfail flipped to PASS)"
    - "pyproject.toml (ruff src + mypy files + mypy_path + pytest pythonpath)"
decisions:
  - "D-01 honored: physical relocation via `git mv` (not symlink, not shim)"
  - "D-06 honored: scripts/_generate_arm_fixtures.py + scripts/_generate_apr_oracle_fixtures.py + scripts/hooks/* stay at project root"
  - "D-08 RETIRED: with all 7 scripts in skill folder, no further 'ship to root then relocate' pattern remains"
  - "Round-2 codex HIGH 1 honored: flipped SKLL-10 test consumes `repo_root` fixture; forbidden pattern (4 chained .parent calls) absent from test_skill.py executable code AND docstring"
  - "Rule 3 (auto-fix blocking issues): added mypy_path + namespace_packages + explicit_package_bases to pyproject.toml so mypy --strict can resolve `from scripts._cli_helpers import ...` after relocation"
metrics:
  duration: ~25 minutes
  completed: 2026-05-08
---

# Phase 10 Plan 01: Scripts Relocation Summary

**One-liner:** Physically relocated all 7 user-facing calc CLIs plus `_cli_helpers.py` from `scripts/` to `.claude/skills/mortgage-ops/scripts/` via `git mv`, retargeted 7 SCRIPT_PATH constants and 1 sys.path injection in tests, extended pyproject.toml with `mypy_path` so strict typecheck resolves the colocated helper import, and flipped the SKLL-10 xfail to PASS asserting all 7 scripts present (full SC-3 closure, no "4 of 7" partial qualifier).

## Wave Outcome

- **Phase 9 baseline preserved end-to-end:** 549 passed → 550 passed (one xfail flipped). 17 xfailed → 16 xfailed. 0 failed, 0 errored.
- **Lint + typecheck clean:** mypy --strict on 85 source files PASS; ruff check + ruff format clean on every touched file.
- **`git mv` similarity scores (history preserved):** _cli_helpers.py 100%, refi_npv.py 94%, affordability.py 93%, refi_npv 94%, apr_reg_z.py 91%, stress_test.py 91%, amortize.py 90%, points_breakeven.py 88%, arm_simulate.py 84%.

## File Relocation Table (8 files, all via `git mv`)

| Old path                          | New path                                                    | Sys.path block | Similarity |
| --------------------------------- | ----------------------------------------------------------- | -------------- | ---------- |
| `scripts/amortize.py`             | `.claude/skills/mortgage-ops/scripts/amortize.py`           | UPDATED        | 90%        |
| `scripts/affordability.py`        | `.claude/skills/mortgage-ops/scripts/affordability.py`      | UPDATED        | 93%        |
| `scripts/arm_simulate.py`         | `.claude/skills/mortgage-ops/scripts/arm_simulate.py`       | UPDATED        | 84%        |
| `scripts/refi_npv.py`             | `.claude/skills/mortgage-ops/scripts/refi_npv.py`           | UPDATED        | 94%        |
| `scripts/apr_reg_z.py`            | `.claude/skills/mortgage-ops/scripts/apr_reg_z.py`          | UPDATED        | 91%        |
| `scripts/stress_test.py`          | `.claude/skills/mortgage-ops/scripts/stress_test.py`        | UPDATED        | 91%        |
| `scripts/points_breakeven.py`     | `.claude/skills/mortgage-ops/scripts/points_breakeven.py`   | UPDATED        | 88%        |
| `scripts/_cli_helpers.py`         | `.claude/skills/mortgage-ops/scripts/_cli_helpers.py`       | n/a (no main)  | 100%       |

## Sys.path Injection Pattern (applied to 7 calc CLIs)

```python
# parents[4] = repo root  (so `from lib.* import ...` resolves)
# parents[1] = skill root (so `from scripts._cli_helpers import ...` resolves)
_skill_root = str(Path(__file__).resolve().parents[1])
_project_root = str(Path(__file__).resolve().parents[4])
for _p in (_project_root, _skill_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

## Test Path Updates

| Test file                | Constant updated         | New target                                                   |
| ------------------------ | ------------------------ | ------------------------------------------------------------ |
| `tests/test_amortize.py`     | `SCRIPT_PATH`           | `.claude/skills/mortgage-ops/scripts/amortize.py`           |
| `tests/test_affordability.py`| `SCRIPT_PATH`           | `.claude/skills/mortgage-ops/scripts/affordability.py`      |
| `tests/test_arm.py`          | `SCRIPT_PATH`           | `.claude/skills/mortgage-ops/scripts/arm_simulate.py`       |
| `tests/test_apr.py`          | `SCRIPT_PATH`           | `.claude/skills/mortgage-ops/scripts/apr_reg_z.py`          |
| `tests/test_refinance.py`    | `SCRIPT_PATH`           | `.claude/skills/mortgage-ops/scripts/refi_npv.py`           |
| `tests/test_stress.py`       | `SCRIPT_PATH`           | `.claude/skills/mortgage-ops/scripts/stress_test.py`        |
| `tests/test_points.py`       | `SCRIPT_PATH`           | `.claude/skills/mortgage-ops/scripts/points_breakeven.py`   |
| `tests/test_cli_helpers.py`  | sys.path inject         | adds `.claude/skills/mortgage-ops` for `from scripts._cli_helpers` |

## pyproject.toml Changes

- `[tool.ruff].src` — added `.claude/skills/mortgage-ops/scripts`
- `[tool.mypy].files` — added `.claude/skills/mortgage-ops/scripts`
- `[tool.mypy].mypy_path = [".", ".claude/skills/mortgage-ops"]` — NEW (deviation Rule 3)
- `[tool.mypy].namespace_packages = true` — NEW (deviation Rule 3)
- `[tool.mypy].explicit_package_bases = true` — NEW (deviation Rule 3)
- `[tool.pytest.ini_options].pythonpath = [".", ".claude/skills/mortgage-ops"]` — NEW

## SKLL-10 Closure (full SC-3, not partial)

`tests/test_skill.py::test_seven_scripts_in_skill_folder_only` was flipped from a Wave 0 strict-xfail stub to a real assertion that:

1. Asserts ALL 8 relocated files (7 calc CLIs + `_cli_helpers.py`) are present at `.claude/skills/mortgage-ops/scripts/`
2. Asserts the same 8 files are ABSENT from `scripts/` at the project root
3. Asserts the D-06 stay-at-root files (`_generate_arm_fixtures.py`, `hooks/block-user-layer.py`) ARE present at `scripts/`
4. Asserts the same D-06 files are NOT duplicated into the skill folder
5. Sanity-checks that `repo_root / "pyproject.toml"` is a file (catches a broken `repo_root` fixture before producing meaningless missing-file errors)

The test consumes the `repo_root` fixture from `tests/conftest.py` (Plan 10-00 Task 3) per Round-2 codex HIGH 1. The forbidden 4-chained-`.parent` overshoot pattern is absent from the entire test_skill.py file (`grep -c 'skill_root.parent.parent.parent.parent' tests/test_skill.py` returns 0).

## D-08 Cross-Phase Contract — RETIRED

D-08 was originally drafted to allow Phase 6/7/8 to ship NEW scripts directly into the skill folder, OR ship them to the project root for later relocation by Phase 10. Phase 6/7/8 elected the latter (per STATE.md, all three phases COMPLETE with their CLIs at project root). With this wave moving all 7 scripts together in one `git mv`, the "ship to root then relocate" pattern carries no further work.

No future-script-to-root pattern remains active. Future skill-related scripts ship directly into `.claude/skills/mortgage-ops/scripts/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Added mypy `mypy_path` + `namespace_packages` + `explicit_package_bases`**

- **Found during:** Task 5 — running `mypy --strict .claude/skills/mortgage-ops/scripts/` after extending `[tool.mypy].files` produced 7 errors of the form `Cannot find implementation or library stub for module named "scripts._cli_helpers"`.
- **Issue:** The plan specified extending `[tool.mypy].files` to include the skill scripts path, but `files` only tells mypy WHAT to typecheck — it doesn't add the path to mypy's module-resolution search list. With `_cli_helpers.py` now at `.claude/skills/mortgage-ops/scripts/_cli_helpers.py` and seven CLIs importing it via `from scripts._cli_helpers import ...`, mypy needs to know that `scripts/` (a namespace package) lives under `.claude/skills/mortgage-ops/`.
- **Fix:** Added `mypy_path = [".", ".claude/skills/mortgage-ops"]` to `[tool.mypy]`. Mypy also requires `namespace_packages = true` and `explicit_package_bases = true` to handle scripts/ as a namespace package across two filesystem roots (project root for tests/ + lib/, skill root for the relocated scripts/).
- **Files modified:** `pyproject.toml`
- **Commit:** included in `91e30ac` (single atomic commit per plan).
- **Result:** `mypy --strict` exits 0 across 85 source files.

**2. [Rule 3 - Blocking issue] Removed forbidden-pattern literal from docstring**

- **Found during:** Task 6 verification — `grep -c 'skill_root.parent.parent.parent.parent' tests/test_skill.py` returned 1 (not 0) because the explanatory docstring quoted the forbidden pattern verbatim using backticks to demonstrate why it was wrong.
- **Issue:** The plan's acceptance criterion "`grep -c '...' tests/test_skill.py returns 0` (the overshoot pattern is forbidden)" is a stricter requirement than "the test's executable code does not use the pattern" — a verbatim-grep guard is part of the acceptance gate.
- **Fix:** Reworded the docstring to describe the forbidden pattern in prose ("Four chained .parent attribute accesses overshoot the repo root by one level") instead of quoting the literal token. The pedagogical content is preserved; only the literal substring is gone.
- **Files modified:** `tests/test_skill.py` (docstring of `test_seven_scripts_in_skill_folder_only`)
- **Commit:** included in `91e30ac`.
- **Result:** `grep -c 'skill_root.parent.parent.parent.parent' tests/test_skill.py` returns 0.

### Linter-driven reformatting

`ruff format` reformatted the SCRIPT_PATH multi-line Path constants in 4 of the 7 retargeted test files (`tests/test_cli_helpers.py`, `tests/test_points.py`, `tests/test_refinance.py`, `tests/test_stress.py`) into a one-Path-component-per-line layout. This is a stylistic transformation only; the constants still resolve to the same path. The other 3 files were already in the linter-preferred shape after my edit.

### Authentication gates

None occurred.

## Verification Commands (replayable)

```
# 1. Confirm baseline
.venv/bin/pytest -q | tail -3
# expected: 550 passed, 4 skipped, 16 xfailed

# 2. Confirm mypy + ruff clean
.venv/bin/mypy --strict | tail -3
# expected: Success: no issues found in 85 source files
.venv/bin/ruff check && .venv/bin/ruff format --check
# expected: All checks passed!  85 files already formatted (or similar)

# 3. Confirm SKLL-10 PASSES (no longer xfail)
.venv/bin/pytest tests/test_skill.py::test_seven_scripts_in_skill_folder_only -v | tail -3
# expected: tests/test_skill.py::test_seven_scripts_in_skill_folder_only PASSED

# 4. Confirm forbidden pattern absent
grep -c 'skill_root.parent.parent.parent.parent' tests/test_skill.py
# expected: 0

# 5. Confirm relocation
ls .claude/skills/mortgage-ops/scripts/
# expected: 8 files (7 CLIs + _cli_helpers.py)
ls scripts/
# expected: _generate_arm_fixtures.py + _generate_apr_oracle_fixtures.py + hooks/ (D-06 stay-at-root)

# 6. Confirm git history preserved
git log --follow --oneline .claude/skills/mortgage-ops/scripts/amortize.py | head -3
# expected: original Phase 3 commits visible
```

## Self-Check: PASSED

- All 8 relocated files present at `.claude/skills/mortgage-ops/scripts/` and absent from `scripts/`: VERIFIED
- All 8 files passed through `git mv` (rename detected, similarity ≥ 84%): VERIFIED
- D-06 stay-at-root files present at project root and not duplicated to skill folder: VERIFIED
- 7 sys.path injection blocks updated to dual-injection idiom (parents[4] + parents[1]): VERIFIED
- 7 test SCRIPT_PATH constants + 1 test sys.path inject updated: VERIFIED
- pyproject.toml extended with ruff src, mypy files, mypy_path, namespace_packages, explicit_package_bases, pytest pythonpath: VERIFIED
- mypy --strict clean across 85 source files: VERIFIED
- ruff check + ruff format clean across all touched files: VERIFIED
- Full pytest: 550 passed (was 549) + 4 skipped + 16 xfailed (was 17) + 0 failed + 0 errored: VERIFIED
- SKLL-10 xfail flipped to PASS asserting all 7 scripts (full SC-3 closure, not partial): VERIFIED
- Test consumes `repo_root` fixture (no four-chained-.parent overshoot): VERIFIED
- Forbidden pattern absent from test_skill.py (grep returns 0): VERIFIED
- Atomic commit `91e30ac` made by ChrisPachulski (no Co-Authored-By, no AI attribution): VERIFIED
