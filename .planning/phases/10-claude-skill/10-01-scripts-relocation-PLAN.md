---
phase: 10
plan: 01
type: execute
wave: 1
depends_on:
  - "10-00"
files_modified:
  - .claude/skills/mortgage-ops/scripts/amortize.py
  - .claude/skills/mortgage-ops/scripts/affordability.py
  - .claude/skills/mortgage-ops/scripts/arm_simulate.py
  - .claude/skills/mortgage-ops/scripts/refi_npv.py
  - .claude/skills/mortgage-ops/scripts/apr_reg_z.py
  - .claude/skills/mortgage-ops/scripts/stress_test.py
  - .claude/skills/mortgage-ops/scripts/points_breakeven.py
  - .claude/skills/mortgage-ops/scripts/_cli_helpers.py
  - tests/test_amortize.py
  - tests/test_affordability.py
  - tests/test_arm.py
  - tests/test_apr.py
  - tests/test_refinance.py
  - tests/test_stress.py
  - tests/test_points.py
  - tests/test_cli_helpers.py
  - pyproject.toml
  - tests/test_skill.py
autonomous: true
requirements:
  - SKLL-10
tags:
  - phase-10
  - claude-skill
  - relocation
  - skll-10
  - high-risk
must_haves:
  truths:
    - "All 7 user-facing calc CLIs (amortize.py, affordability.py, arm_simulate.py, refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py) PLUS _cli_helpers.py live ONLY at .claude/skills/mortgage-ops/scripts/, NOT at scripts/ project root"
    - "scripts/_generate_arm_fixtures.py + scripts/_generate_apr_oracle_fixtures.py + scripts/hooks/* STAY at project root per LOCKED DECISION D-06 (dev tooling, not user-facing CLIs)"
    - "Full pre-existing test suite (≥ 549 passed Phase 9 baseline) remains green AFTER relocation — zero regression"
    - "test_seven_scripts_in_skill_folder_only xfail flips to PASS in this wave (asserts all 7 calc scripts inside skill folder, fully closing SC-3 / SKLL-10), and resolves the repo root via the `repo_root` fixture (Round-2 codex HIGH 1: NOT `skill_root.parent.parent.parent.parent` which overshoots by one level)"
    - "git mv was used (not rm + cp) so file history is preserved per Phase 3 D-17 / Phase 7 D-17 / Phase 8 D-XX portability comment expectation"
    - "pyproject.toml [tool.ruff].src + [tool.mypy].files include both 'scripts' AND '.claude/skills/mortgage-ops/scripts' so the surviving scripts/ tooling AND the relocated CLIs are both linted"
    - "Cross-phase contract D-08 (RETIRED at Phase 10 ship): all 7 scripts now physically reside in skill folder. Phase 11/12 may reference relative paths inside skill folder; no future-script-to-root pattern remains"
  artifacts:
    - path: ".claude/skills/mortgage-ops/scripts/amortize.py"
      provides: "Phase 3 CLI relocated (was scripts/amortize.py); behavior unchanged; sys.path injection updated for new depth"
      contains: "def main"
    - path: ".claude/skills/mortgage-ops/scripts/affordability.py"
      provides: "Phase 4 CLI relocated; behavior unchanged"
      contains: "def main"
    - path: ".claude/skills/mortgage-ops/scripts/arm_simulate.py"
      provides: "Phase 5 CLI relocated; behavior unchanged"
      contains: "def main"
    - path: ".claude/skills/mortgage-ops/scripts/refi_npv.py"
      provides: "Phase 6 CLI relocated; behavior unchanged"
      contains: "def main"
    - path: ".claude/skills/mortgage-ops/scripts/apr_reg_z.py"
      provides: "Phase 7 CLI relocated; behavior unchanged"
      contains: "def main"
    - path: ".claude/skills/mortgage-ops/scripts/stress_test.py"
      provides: "Phase 8 CLI relocated; behavior unchanged"
      contains: "def main"
    - path: ".claude/skills/mortgage-ops/scripts/points_breakeven.py"
      provides: "Phase 8 CLI relocated; behavior unchanged"
      contains: "def main"
    - path: ".claude/skills/mortgage-ops/scripts/_cli_helpers.py"
      provides: "Shared CLI helpers (find_json_float_loc, make_decimal_type_envelope) relocated alongside callers"
      contains: "def find_json_float_loc"
  key_links:
    - from: "tests/test_amortize.py SCRIPT_PATH"
      to: ".claude/skills/mortgage-ops/scripts/amortize.py"
      via: "single-constant edit (Phase 3 D-17 portability seam)"
      pattern: "SCRIPT_PATH.*amortize.py"
    - from: ".claude/skills/mortgage-ops/scripts/*.py"
      to: "lib.* + scripts._cli_helpers"
      via: "sys.path injection at main() entry — repo root for lib.*, skill root for scripts.*"
      pattern: "sys.path.insert"
    - from: "test_seven_scripts_in_skill_folder_only"
      to: "Plan 10-01 file moves"
      via: "Wave 0 stub flip — first test to retire its xfail decorator; asserts ALL 7 scripts present; consumes repo_root fixture (Round-2 codex HIGH 1)"
      pattern: "@pytest.mark.xfail"
---

<objective>
Execute LOCKED DECISION D-01 + D-08 cross-phase contract closure: physically relocate ALL SEVEN user-facing CLI scripts (`amortize.py`, `affordability.py`, `arm_simulate.py`, `refi_npv.py`, `apr_reg_z.py`, `stress_test.py`, `points_breakeven.py`) plus `_cli_helpers.py` from project-root `scripts/` into `.claude/skills/mortgage-ops/scripts/` via `git mv` (history preservation). Update each relocated script's `sys.path` injection block to point 4 levels up to the repo root + 1 level up to the skill root. Update `SCRIPT_PATH` constants in 7 test files. Update `pyproject.toml` ruff/mypy/pytest config. Flip the SKLL-10 xfail stub to PASS — and assert ALL SEVEN scripts present (full SC-3 closure, not partial), using the `repo_root` fixture from Plan 10-00 Task 3 (Round-2 codex HIGH 1: do NOT use `skill_root.parent.parent.parent.parent` which overshoots the repo root).

This is the HIGHEST-RISK plan in Phase 10: it relocates already-shipped + already-tested code that 549+ tests depend on (per STATE.md Phase 9 baseline). The full pre-existing test suite MUST remain green AFTER relocation. Phase 11 SUBA-05 hard-depends on the skill-folder scripts existing. SKLL-10 / SC-3 close FULLY at Phase 10 ship.

**STATE.md confirms Phase 6/7/8 COMPLETE.** All 7 calc scripts exist at project-root `scripts/` and are testable today. Earlier draft of this plan moved only 4 scripts and left 3 deferred to "Phase 6/7/8 will ship them later" — that scaffolding is now obsolete and would falsely close SKLL-10/SC-3 at "4 of 7". This revision updates the plan to relocate all 7 scripts in one atomic git mv, fully closing SC-3.

Closes SKLL-10 ("All 7 calc scripts INSIDE `.claude/skills/mortgage-ops/scripts/`, NOT at project root") + flips ONE xfail stub from Wave 0.

Purpose: Without this wave the skill folder cannot host its bundled scripts; SKILL.md routing in Wave 2 would have nothing to dispatch to. Per D-01 rationale, MOVE is the only option that survives Phase 11 contract — symlink breaks portability, shim doubles indirection cost.

Output: 8 files (7 calc scripts + 1 helper) in their new location with updated sys.path; 7 test files with updated SCRIPT_PATH constants; pyproject.toml with extended ruff/mypy/pytest `src`/`files`/`pythonpath` lists; Wave 0 stub `test_seven_scripts_in_skill_folder_only` flipped to PASS asserting all 7 (using `repo_root` fixture; no `parent.parent.parent.parent` overshoot).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/10-claude-skill/10-CONTEXT.md
@.planning/phases/10-claude-skill/10-PATTERNS.md
@.planning/phases/10-claude-skill/10-RESEARCH.md
@.planning/phases/10-claude-skill/10-UI-SPEC.md
@CLAUDE.md
@DATA_CONTRACT.md
@pyproject.toml
@scripts/amortize.py
@scripts/affordability.py
@scripts/arm_simulate.py
@scripts/refi_npv.py
@scripts/apr_reg_z.py
@scripts/stress_test.py
@scripts/points_breakeven.py
@scripts/_cli_helpers.py
@tests/test_amortize.py
@tests/test_affordability.py
@tests/test_arm.py
@tests/test_apr.py
@tests/test_refinance.py
@tests/test_stress.py
@tests/test_points.py
@tests/test_cli_helpers.py

<interfaces>
LOCKED DECISIONS in scope this wave:
- D-01 = MOVE (physical relocation via git mv) — see 10-RESEARCH §(f) for full rationale
- D-05 = `_cli_helpers.py` location SUPERSEDED by 10-PATTERNS CRITICAL #2: keep `_cli_helpers.py` next to the relocated scripts in `.claude/skills/mortgage-ops/scripts/_cli_helpers.py` (NOT in `lib/`). Rationale: `_cli_helpers.py` IS a CLI implementation detail; placing it in `lib/` blurs the lib/scripts boundary.
- D-06 = `_generate_arm_fixtures.py` + `_generate_apr_oracle_fixtures.py` + `scripts/hooks/` STAY at project root
- D-08 = CROSS-PHASE CONTRACT (RETIRED at Phase 10 ship). Originally drafted to allow Phase 6/7/8 to ship NEW scripts directly into the skill folder OR into the root then later relocate. With Phase 6/7/8 already COMPLETE and their scripts shipped to root, this plan relocates all together. No further "ship to root then Phase 10 relocates" pattern remains active.

STATE.md baseline (Phase 9 close): 549 passed + 4 skipped + 1 xfailed. Wave 0 added ≥ 15 stubs; pre-Plan-10-01 baseline is 549 passed + ≥ 15 xfailed.

Phase 3 D-17 + Phase 6 D-17 + Phase 7 D-17 + Phase 8 D-XX portability seams: every existing user-facing CLI carries a docstring noting "Phase 10 will physically relocate". This plan satisfies that contract.

**Round-2 codex HIGH 1 — repo_root path arithmetic:** Plan 10-00 Task 3 ships a `repo_root` pytest fixture returning `Path(__file__).resolve().parents[1]` (from `tests/conftest.py` → repo root). The flipped SKLL-10 test in Task 6 below MUST consume this fixture. Equivalent inline form: `skill_root.parents[2]`. The literal `skill_root.parent.parent.parent.parent` (4 chained `.parent` calls) goes ONE LEVEL TOO FAR (`.claude/skills/mortgage-ops/.parent[3]` lands above the repo root) and is forbidden.

Current sys.path injection block (lift verbatim from scripts/amortize.py:92-100; Phase 6/7/8 scripts use the same idiom):
```python
# When invoked as a script (`python scripts/amortize.py ...`), Python puts
# `scripts/` on sys.path, NOT the project root, so `from lib.amortize import ...`
# fails with ModuleNotFoundError. Insert the project root (parent of this file's
# directory) at sys.path[0] so the lazy-import below resolves.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
```

After-relocation block (per 10-PATTERNS CRITICAL #3 Category B):
```python
# Phase 10: relocated to .claude/skills/mortgage-ops/scripts/{name}.py.
# Inject BOTH the repo root (so `from lib.{module} import ...` resolves) AND
# the skill root (so `from scripts._cli_helpers import ...` resolves —
# scripts/ here means the skill-local scripts/, not project-root scripts/).
# parents[4] = repo root (skipping scripts/, mortgage-ops/, skills/, .claude/).
# parents[1] = skill root (.claude/skills/mortgage-ops).
_skill_root = str(Path(__file__).resolve().parents[1])
_project_root = str(Path(__file__).resolve().parents[4])
for _p in (_project_root, _skill_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

Note that `parents[4]` is correct **for a file at `.claude/skills/mortgage-ops/scripts/<name>.py`** (5 levels deep: scripts/ → mortgage-ops/ → skills/ → .claude/ → repo). For tests living at `tests/<test>.py` (2 levels deep), the equivalent is `parents[1]`, which is what Plan 10-00 Task 3's `repo_root` fixture computes. The Wave 5/6 plans use the test-file form.

Test SCRIPT_PATH constant edits — 7 test files (verify exact line numbers when reading each file, the precise positions vary by phase):
- tests/test_amortize.py — `parent.parent / "scripts" / "amortize.py"` → `parent.parent / ".claude" / "skills" / "mortgage-ops" / "scripts" / "amortize.py"`
- tests/test_affordability.py — same pattern with affordability.py
- tests/test_arm.py — same pattern with arm_simulate.py
- tests/test_apr.py — same pattern with apr_reg_z.py (Phase 7)
- tests/test_refinance.py — same pattern with refi_npv.py (Phase 6)
- tests/test_stress.py — same pattern with stress_test.py (Phase 8)
- tests/test_points.py — same pattern with points_breakeven.py (Phase 8)

(If any of those test files do NOT carry a SCRIPT_PATH constant, run `grep -rn 'SCRIPT_PATH' tests/` first to enumerate the exact constants and adjust.)

pyproject.toml edits (CRITICAL #3 Category C):
- ruff: `src = ["lib", "tests", "scripts"]` → `src = ["lib", "tests", "scripts", ".claude/skills/mortgage-ops/scripts"]`
- mypy: `files = ["lib", "tests", "scripts"]` → `files = ["lib", "tests", "scripts", ".claude/skills/mortgage-ops/scripts"]`
- pytest: add `pythonpath = [".", ".claude/skills/mortgage-ops"]`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pre-flight — record baseline test count + verify all 7 scripts present + git tree clean</name>
  <files>(verification only — no file writes)</files>
  <read_first>
    Phase 9 SUMMARY 09-07 — last-known baseline (≥ 549 passed)
  </read_first>
  <action>
PRE-FLIGHT CHECKS — bail out early if anything is amiss BEFORE touching files.

1. Verify git working tree is clean: `git status --short` should be empty (or contain only Wave 0 changes if Wave 0 hasn't been committed yet — investigate).
2. Record baseline: `pytest -q 2>&1 | tail -3` — capture the exact "N passed, M xfailed" line. Save to `_baseline.txt` in scratch (don't commit).
3. Confirm ALL 7 calc scripts + helper exist at project root:
```
test -f scripts/amortize.py
test -f scripts/affordability.py
test -f scripts/arm_simulate.py
test -f scripts/refi_npv.py
test -f scripts/apr_reg_z.py
test -f scripts/stress_test.py
test -f scripts/points_breakeven.py
test -f scripts/_cli_helpers.py
```
4. Confirm 3 stay-at-root files exist: `test -f scripts/_generate_arm_fixtures.py && test -f scripts/_generate_apr_oracle_fixtures.py && test -f scripts/hooks/block-user-layer.py`.
5. Confirm skill folder does NOT yet have these scripts: `test ! -e .claude/skills/mortgage-ops/scripts/amortize.py`.
6. Enumerate SCRIPT_PATH constants in test files:
```
grep -rn 'SCRIPT_PATH' tests/ | grep -v '__pycache__'
```
   Expect to find 7 distinct test files referencing the 7 calc scripts. If any test file uses a different idiom (e.g., constructs the path inline), note it for Task 4.

If ANY of the above fails, STOP and surface the issue. Do NOT proceed to Task 2.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; git status --short &amp;&amp; pytest -q 2&gt;&amp;1 | tail -3 &amp;&amp; for f in amortize affordability arm_simulate refi_npv apr_reg_z stress_test points_breakeven _cli_helpers; do test -f scripts/$f.py || { echo "MISSING scripts/$f.py"; exit 1; }; done &amp;&amp; test -f scripts/_generate_arm_fixtures.py &amp;&amp; test -f scripts/hooks/block-user-layer.py &amp;&amp; test ! -e .claude/skills/mortgage-ops/scripts/amortize.py</automated>
  </verify>
  <acceptance_criteria>
- Baseline pass count captured (≥ 549 per Phase 9 close)
- All 7 calc scripts (amortize, affordability, arm_simulate, refi_npv, apr_reg_z, stress_test, points_breakeven) + _cli_helpers.py exist at project-root scripts/
- Stay-at-root files present: `_generate_arm_fixtures.py`, `_generate_apr_oracle_fixtures.py` (if it exists; verify), `hooks/block-user-layer.py`
- Skill folder does not yet contain the to-be-moved files
- Working tree clean OR contains only Wave 0 staged changes
- SCRIPT_PATH enumeration captured (≥ 7 references across test files)
  </acceptance_criteria>
  <done>
    Baseline established; preconditions confirmed; ready for relocation.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create skill folder structure + git mv 8 files atomically (7 calc scripts + _cli_helpers)</name>
  <files>.claude/skills/mortgage-ops/scripts/amortize.py, .claude/skills/mortgage-ops/scripts/affordability.py, .claude/skills/mortgage-ops/scripts/arm_simulate.py, .claude/skills/mortgage-ops/scripts/refi_npv.py, .claude/skills/mortgage-ops/scripts/apr_reg_z.py, .claude/skills/mortgage-ops/scripts/stress_test.py, .claude/skills/mortgage-ops/scripts/points_breakeven.py, .claude/skills/mortgage-ops/scripts/_cli_helpers.py</files>
  <read_first>
    10-PATTERNS CRITICAL #2 step-by-step;
    10-RESEARCH §(f) D-01 migration steps
  </read_first>
  <action>
Execute the relocation. Use `git mv` (preserves history) — NOT `cp + rm`, NOT plain `mv`.

Step 1 — Create skill directory structure (if not already present from a partial prior attempt):
```
mkdir -p .claude/skills/mortgage-ops/scripts
mkdir -p .claude/skills/mortgage-ops/modes
mkdir -p .claude/skills/mortgage-ops/references
mkdir -p .claude/skills/mortgage-ops/assets
```

Step 2 — git-mv the 8 files (one per command, in this order — `_cli_helpers.py` LAST so the importers don't have a transient "missing import" window if anything reads them between moves):
```
git mv scripts/amortize.py          .claude/skills/mortgage-ops/scripts/amortize.py
git mv scripts/affordability.py     .claude/skills/mortgage-ops/scripts/affordability.py
git mv scripts/arm_simulate.py      .claude/skills/mortgage-ops/scripts/arm_simulate.py
git mv scripts/refi_npv.py          .claude/skills/mortgage-ops/scripts/refi_npv.py
git mv scripts/apr_reg_z.py         .claude/skills/mortgage-ops/scripts/apr_reg_z.py
git mv scripts/stress_test.py       .claude/skills/mortgage-ops/scripts/stress_test.py
git mv scripts/points_breakeven.py  .claude/skills/mortgage-ops/scripts/points_breakeven.py
git mv scripts/_cli_helpers.py      .claude/skills/mortgage-ops/scripts/_cli_helpers.py
```

Step 3 — Verify D-06 stay-at-root files were NOT touched:
```
test -f scripts/_generate_arm_fixtures.py
test -f scripts/_generate_apr_oracle_fixtures.py 2>/dev/null || true  # may not exist; only assert if present pre-flight
test -f scripts/hooks/block-user-layer.py
test -f scripts/hooks/__init__.py
```

Step 4 — Verify the relocated files now exist at the new location AND are gone from the old:
```
for f in amortize affordability arm_simulate refi_npv apr_reg_z stress_test points_breakeven _cli_helpers; do
  test -f .claude/skills/mortgage-ops/scripts/$f.py || { echo "MISSING in skill: $f.py"; exit 1; }
  test ! -e scripts/$f.py || { echo "STILL AT ROOT: scripts/$f.py"; exit 1; }
done
```

DO NOT yet edit the sys.path blocks (Task 3) or test SCRIPT_PATH constants (Task 4) or pyproject.toml (Task 5). The test suite WILL be red between Task 2 and Task 5 — that is expected and acceptable, BUT each subsequent task must minimize the red window.

DO NOT delete the empty `scripts/` directory — it still contains `__pycache__/`, `_generate_arm_fixtures.py` (and possibly `_generate_apr_oracle_fixtures.py`), and `hooks/`. The directory STAYS.

DO NOT commit yet — Task 6 commits the whole wave atomically.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for f in amortize affordability arm_simulate refi_npv apr_reg_z stress_test points_breakeven _cli_helpers; do test -f .claude/skills/mortgage-ops/scripts/$f.py &amp;&amp; test ! -e scripts/$f.py; done &amp;&amp; test -f scripts/_generate_arm_fixtures.py &amp;&amp; test -f scripts/hooks/block-user-layer.py</automated>
  </verify>
  <acceptance_criteria>
- All 8 files (7 calc scripts + _cli_helpers.py) present in `.claude/skills/mortgage-ops/scripts/`
- All 8 files ABSENT from `scripts/`
- D-06 stay-at-root files unchanged: `scripts/_generate_arm_fixtures.py` + `scripts/hooks/block-user-layer.py` + `scripts/hooks/__init__.py` (and `scripts/_generate_apr_oracle_fixtures.py` if it exists pre-flight)
- `git status --short` shows the rename entries — `git status --short` typically reports ONE `R` line per renamed file (the renamed-from + renamed-to is encoded on a single line). Expected: 8 lines starting with `R` (one per renamed file). Inspect the output and confirm 8 R lines exist; do NOT enforce an "exactly 16" or "exactly 8 R + 8 add" count — git's representation depends on rename detection thresholds.
- Skill subdirectories `modes/`, `references/`, `assets/` exist (empty)
  </acceptance_criteria>
  <done>
    8 files (7 calc scripts + helper) physically relocated via git mv; D-06 stay-at-root files unchanged; skill subdirectories scaffolded.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update sys.path injection in 7 relocated scripts (all 7 calc CLIs)</name>
  <files>.claude/skills/mortgage-ops/scripts/amortize.py, .claude/skills/mortgage-ops/scripts/affordability.py, .claude/skills/mortgage-ops/scripts/arm_simulate.py, .claude/skills/mortgage-ops/scripts/refi_npv.py, .claude/skills/mortgage-ops/scripts/apr_reg_z.py, .claude/skills/mortgage-ops/scripts/stress_test.py, .claude/skills/mortgage-ops/scripts/points_breakeven.py</files>
  <read_first>
    .claude/skills/mortgage-ops/scripts/amortize.py lines 80-110 (current sys.path block);
    Same range in each of: affordability.py, arm_simulate.py, refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py;
    10-PATTERNS CRITICAL #3 Category B "Recommended sys.path injection idiom for relocated scripts"
  </read_first>
  <action>
For each of the 7 relocated calc scripts — `_cli_helpers.py` has NO sys.path block to update — REPLACE the existing `_project_root` block with the dual-injection idiom from 10-PATTERNS CRITICAL #3.

The depth changes: previously `parent.parent` resolved to repo root (script was 2 levels deep). Now scripts live at `.claude/skills/mortgage-ops/scripts/*.py` which is 5 levels deep:
- `parents[0]` = `.claude/skills/mortgage-ops/scripts/`
- `parents[1]` = `.claude/skills/mortgage-ops/` (SKILL ROOT — needed so `from scripts._cli_helpers import ...` resolves to the colocated helper)
- `parents[2]` = `.claude/skills/`
- `parents[3]` = `.claude/`
- `parents[4]` = repo root (REPO ROOT — needed so `from lib.* import ...` resolves)

For EACH of the 7 calc scripts, find the existing block (typically the comment block beginning "When invoked as a script ..." plus the 3-line `_project_root = ... ; if _project_root not in sys.path: sys.path.insert(0, _project_root)`).

REPLACE with (substitute the actual lib module name in the comment per script):
```python
# Phase 10 relocation (D-01): script lives at
# .claude/skills/mortgage-ops/scripts/{this script}.py (5 levels deep). Inject
# BOTH the repo root (so `from lib.{module} import ...` resolves) AND the
# skill root (so `from scripts._cli_helpers import ...` resolves to the
# colocated helper, NOT the project-root scripts/ which no longer hosts it).
# parents[4] = repo root; parents[1] = skill root. Runs AFTER --help has
# exited above, so D-18 (--help fast) is unaffected.
_skill_root = str(Path(__file__).resolve().parents[1])
_project_root = str(Path(__file__).resolve().parents[4])
for _p in (_project_root, _skill_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

Mapping of `from lib.*` lazy-imports per script (keep these UNCHANGED — only the sys.path bootstrap changes):
- amortize.py — `from lib.amortize import ...`
- affordability.py — `from lib.affordability import ...`
- arm_simulate.py — `from lib.arm import ...`
- refi_npv.py — `from lib.refinance import ...`
- apr_reg_z.py — `from lib.apr import ...`
- stress_test.py — `from lib.stress import ...`
- points_breakeven.py — `from lib.points import ...`

DO NOT modify the `from scripts._cli_helpers import ...` lines themselves — the import path stays exactly `from scripts._cli_helpers import ...` because once `_skill_root` is on sys.path, `scripts` resolves to `.claude/skills/mortgage-ops/scripts/` (the colocated helper).

DO NOT modify the docstring of each script (the Phase 3 D-17 / Phase 6 D-17 / Phase 7 D-17 / Phase 8 D-XX explanatory comments). Update those in a follow-up doc-cleanup pass IF needed (NOT this wave) — they were drafted to anticipate this relocation.

After editing all 7, smoke-test each script can run `--help`:
```
for s in amortize affordability arm_simulate refi_npv apr_reg_z stress_test points_breakeven; do
  python .claude/skills/mortgage-ops/scripts/$s.py --help > /dev/null || { echo "FAIL: $s --help"; exit 1; }
done
```

Each MUST exit 0 in < 200ms (D-18 fast --help preserved across all phases).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for s in amortize affordability arm_simulate refi_npv apr_reg_z stress_test points_breakeven; do grep -c 'parents\[4\]' .claude/skills/mortgage-ops/scripts/$s.py | grep -q '^[1-9]' &amp;&amp; python .claude/skills/mortgage-ops/scripts/$s.py --help &gt; /dev/null; done</automated>
  </verify>
  <acceptance_criteria>
- All 7 scripts contain `parents[4]` (repo root injection)
- All 7 scripts contain `parents[1]` (skill root injection)
- All 7 scripts STILL contain `from scripts._cli_helpers import ...` (UNCHANGED — only sys.path bootstrap changed)
- All 7 scripts' `--help` exit 0
- All 7 `--help` runs complete in < 500ms (D-18 fast --help; allow 500ms tolerance for cold cache)
  </acceptance_criteria>
  <done>
    sys.path injection updated in 7 scripts; --help works for all 7; relocated scripts can resolve both `lib.*` AND `scripts._cli_helpers` imports.
  </done>
</task>

<task type="auto">
  <name>Task 4: Update SCRIPT_PATH constants in 7 test files + fix tests/test_cli_helpers.py import</name>
  <files>tests/test_amortize.py, tests/test_affordability.py, tests/test_arm.py, tests/test_apr.py, tests/test_refinance.py, tests/test_stress.py, tests/test_points.py, tests/test_cli_helpers.py</files>
  <read_first>
    Each test file's existing SCRIPT_PATH definition (use `grep -n 'SCRIPT_PATH' tests/test_*.py` from Task 1's enumeration to find exact lines);
    tests/test_cli_helpers.py lines 16-21 (current sys.path inject + import);
    10-PATTERNS CRITICAL #3 Categories A + B (verbatim before/after table)
  </read_first>
  <action>
PART A — Update 7 SCRIPT_PATH constants. Single-line edit per file. The exact pattern in every test file is:
```python
SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "{script_name}.py"
```

Replace with:
```python
SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude" / "skills" / "mortgage-ops" / "scripts" / "{script_name}.py"
)
```

(Single-line form is also acceptable if it fits ruff's line-length cap; use whichever the file's existing style prefers.)

Apply per file:
- tests/test_amortize.py — amortize.py
- tests/test_affordability.py — affordability.py
- tests/test_arm.py — arm_simulate.py
- tests/test_apr.py — apr_reg_z.py
- tests/test_refinance.py — refi_npv.py
- tests/test_stress.py — stress_test.py
- tests/test_points.py — points_breakeven.py

Update each file's pre-SCRIPT_PATH explanatory comment to past-tense ("Phase X CLI WAS at project-root scripts/; Phase 10 (Plan 10-01) RELOCATED ..."). If a test file references SCRIPT_PATH in multiple places, update only the constant; usage sites consume the constant transparently.

PART B — Fix tests/test_cli_helpers.py sys.path injection + import (CRITICAL #3 Category B).

Current lines 16-21 (verify at edit time):
```python
import sys
from pathlib import Path

# Make scripts/ importable as a package
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope
```

Replace with:
```python
import sys
from pathlib import Path

# Phase 10 relocation: scripts/_cli_helpers.py moved to
# .claude/skills/mortgage-ops/scripts/_cli_helpers.py per Plan 10-01.
# Inject the SKILL ROOT (parent of the colocated scripts/) so
# `from scripts._cli_helpers import ...` resolves to the relocated module.
_project_root = Path(__file__).resolve().parent.parent
_skill_root = _project_root / ".claude" / "skills" / "mortgage-ops"
for _p in (_project_root, _skill_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope
```

The `from scripts._cli_helpers import ...` line itself does NOT change.

PART C — Smoke test each affected test file collects:
```
pytest tests/test_amortize.py tests/test_affordability.py tests/test_arm.py tests/test_apr.py tests/test_refinance.py tests/test_stress.py tests/test_points.py tests/test_cli_helpers.py --collect-only -q
```

ALL must exit 0 with no collection errors.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for f in test_amortize test_affordability test_arm test_apr test_refinance test_stress test_points; do grep -c '\.claude' tests/$f.py | grep -q '^[1-9]' || { echo "MISSING .claude in tests/$f.py"; exit 1; }; done &amp;&amp; grep -c '_skill_root' tests/test_cli_helpers.py &amp;&amp; pytest tests/test_amortize.py tests/test_affordability.py tests/test_arm.py tests/test_apr.py tests/test_refinance.py tests/test_stress.py tests/test_points.py tests/test_cli_helpers.py --collect-only -q</automated>
  </verify>
  <acceptance_criteria>
- All 7 test files contain `.claude` in their SCRIPT_PATH (skill-folder path baked in)
- `grep -c '_skill_root' tests/test_cli_helpers.py` returns ≥ 1
- `grep -c 'from scripts._cli_helpers' tests/test_cli_helpers.py` returns 1 (UNCHANGED)
- 8 affected test files all collect without error
- No stale present-tense "project root scripts" comment remaining (all updated to past-tense)
  </acceptance_criteria>
  <done>
    7 SCRIPT_PATH constants + 1 sys.path bootstrap updated; collection green; ready for full-suite verification in Task 6.
  </done>
</task>

<task type="auto">
  <name>Task 5: Update pyproject.toml ruff/mypy/pytest config for new skill-folder paths</name>
  <files>pyproject.toml</files>
  <read_first>
    pyproject.toml lines 28-32 (ruff src);
    pyproject.toml lines 49-54 (mypy files);
    pyproject.toml lines 70-73 (pytest config);
    10-PATTERNS CRITICAL #3 Category C (verbatim before/after)
  </read_first>
  <action>
Three edits in pyproject.toml. Use Edit tool (not Write) — preserve all other lines.

Edit 1 — ruff `src`:
```
src = ["lib", "tests", "scripts"]
```
After:
```
src = ["lib", "tests", "scripts", ".claude/skills/mortgage-ops/scripts"]
```

Edit 2 — mypy `files`:
```
files = ["lib", "tests", "scripts"]
```
After:
```
files = ["lib", "tests", "scripts", ".claude/skills/mortgage-ops/scripts"]
```

Edit 3 — pytest `[tool.pytest.ini_options]`. Add `pythonpath`:
```
[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
pythonpath = [".", ".claude/skills/mortgage-ops"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
```

Rationale: keep `"scripts"` because `scripts/_generate_arm_fixtures.py` and `scripts/hooks/*.py` still live there (D-06) and need ruff/mypy coverage. Add the skill path so the relocated CLIs are linted too. `pythonpath` makes pytest add both the repo root AND the skill root at collection time.

After all three edits, run:
```
mypy --strict .claude/skills/mortgage-ops/scripts/
ruff check .claude/skills/mortgage-ops/scripts/
ruff format --check .claude/skills/mortgage-ops/scripts/
```

ALL three MUST exit 0 (relocated scripts must pass strict typecheck + lint immediately, since their behavior is unchanged).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; grep -c '\.claude/skills/mortgage-ops/scripts' pyproject.toml &amp;&amp; grep -c 'pythonpath' pyproject.toml &amp;&amp; mypy --strict .claude/skills/mortgage-ops/scripts/ &amp;&amp; ruff check .claude/skills/mortgage-ops/scripts/ &amp;&amp; ruff format --check .claude/skills/mortgage-ops/scripts/</automated>
  </verify>
  <acceptance_criteria>
- `grep -c '\.claude/skills/mortgage-ops/scripts' pyproject.toml` returns ≥ 2 (ruff src + mypy files)
- `grep -c 'pythonpath' pyproject.toml` returns 1 (new pytest line)
- `grep -c '"lib", "tests", "scripts"' pyproject.toml` returns 2 (ruff src + mypy files BOTH still include "scripts" alongside the skill path)
- mypy --strict on relocated scripts exits 0
- ruff check on relocated scripts exits 0
- ruff format --check on relocated scripts exits 0
  </acceptance_criteria>
  <done>
    pyproject.toml extended; relocated scripts pass mypy + ruff under new config.
  </done>
</task>

<task type="auto">
  <name>Task 6: Run full test suite + flip SKLL-10 xfail (asserts ALL 7; uses repo_root fixture per Round-2 codex HIGH 1) + commit relocation atomically</name>
  <files>tests/test_skill.py</files>
  <read_first>
    tests/test_skill.py — find `def test_seven_scripts_in_skill_folder_only` (Wave 0 stub from Plan 10-00 Task 4);
    tests/conftest.py — confirm `repo_root` fixture exists (Plan 10-00 Task 3 ships it)
  </read_first>
  <action>
PART A — Full suite verification (the moment of truth for relocation safety):
```
pytest -q 2>&1 | tail -10
```

REQUIRED outcome: ≥ 549 passed (Phase 9 baseline), ≥ 15 xfailed (Wave 0 stubs), 0 failed, 0 errored.

If ANY pre-existing test fails or any unexpected error appears, STOP. The relocation has broken something. Investigate (likely sys.path depth wrong — verify `parents[4]` resolves to repo root by `python -c "from pathlib import Path; print(Path('.claude/skills/mortgage-ops/scripts/amortize.py').resolve().parents[4])"`). Do NOT proceed until full suite is green-modulo-xfail.

PART B — Flip the SKLL-10 xfail stub to a real assertion. In tests/test_skill.py, find:

```python
@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-01 relocates 7 calc scripts ...")
def test_seven_scripts_in_skill_folder_only(skill_root: Path) -> None:
    """SKLL-10 + ROADMAP SC-3 + D-01 + D-06 + D-08: ..."""
    pytest.fail("Wave 0 stub")
```

REPLACE with the real assertion. Note the function signature now consumes BOTH the `skill_root` AND the new `repo_root` fixture (Round-2 codex HIGH 1 — `skill_root.parent.parent.parent.parent` overshoots by one level; use `repo_root` instead). REMOVE the @pytest.mark.xfail decorator entirely:

```python
def test_seven_scripts_in_skill_folder_only(skill_root: Path, repo_root: Path) -> None:
    """SKLL-10 + ROADMAP SC-3 + D-01 + D-06 + D-08: ALL SEVEN calc CLIs —
    amortize.py, affordability.py, arm_simulate.py, refi_npv.py, apr_reg_z.py,
    stress_test.py, points_breakeven.py — live ONLY in
    .claude/skills/mortgage-ops/scripts/, NOT at project-root scripts/.
    _cli_helpers.py also lives in skill folder.

    Stay-at-root files (D-06): _generate_arm_fixtures.py +
    _generate_apr_oracle_fixtures.py + scripts/hooks/*.

    SC-3 / SKLL-10 close FULLY in Phase 10 (all 7 scripts relocated together;
    Phase 6/7/8 COMPLETE per STATE.md so all 7 scripts existed at root pre-move).

    Round-2 codex HIGH 1: this test consumes the `repo_root` fixture from
    Plan 10-00 Task 3. The literal `skill_root.parent.parent.parent.parent`
    (4 chained .parent calls) overshoots the repo root by one level —
    .claude/skills/mortgage-ops is only 3 levels deep, so .parents[3] lands
    above the repo. The correct equivalents are `repo_root` (this fixture)
    or `skill_root.parents[2]`.
    """
    project_scripts = repo_root / "scripts"
    skill_scripts = skill_root / "scripts"

    # Sanity: confirm repo_root fixture resolves correctly. If it doesn't,
    # everything below produces meaningless "missing file" errors instead of
    # surfacing the real bug.
    assert (repo_root / "pyproject.toml").is_file(), (
        f"repo_root fixture broken: pyproject.toml not at {repo_root}; "
        f"path arithmetic in tests/conftest.py needs review"
    )

    relocated = [
        "amortize.py",
        "affordability.py",
        "arm_simulate.py",
        "refi_npv.py",
        "apr_reg_z.py",
        "stress_test.py",
        "points_breakeven.py",
        "_cli_helpers.py",
    ]
    for name in relocated:
        assert (skill_scripts / name).is_file(), (
            f"SKLL-10 violation: {name} missing from skill folder "
            f"(expected at {skill_scripts / name})"
        )
        assert not (project_scripts / name).is_file(), (
            f"SKLL-10 + D-01 violation: {name} STILL at project root scripts/ "
            f"(should have been relocated). Re-run Plan 10-01 Task 2."
        )

    # D-06: stay-at-root files MUST still exist at project root
    stay_at_root = ["_generate_arm_fixtures.py", "hooks/block-user-layer.py"]
    for name in stay_at_root:
        assert (project_scripts / name).is_file(), (
            f"D-06 violation: {name} should remain at project-root scripts/ "
            f"(it is dev tooling, not a user-facing CLI)"
        )

    # D-06: stay-at-root files MUST NOT have been duplicated to skill folder
    for name in stay_at_root:
        assert not (skill_scripts / name).exists(), (
            f"D-06 violation: {name} should NOT exist in skill folder"
        )
```

PART C — Re-run pytest:
```
pytest tests/test_skill.py::test_seven_scripts_in_skill_folder_only -v
pytest -q 2>&1 | tail -5
```

The flipped test MUST PASS. Total xfailed count DROPS by 1.

PART D — Commit the wave atomically. Per CLAUDE.md global rule: NO Co-Authored-By, NO AI attribution.

```
git add .claude/skills/mortgage-ops/scripts/
git add tests/test_amortize.py tests/test_affordability.py tests/test_arm.py
git add tests/test_apr.py tests/test_refinance.py tests/test_stress.py tests/test_points.py
git add tests/test_cli_helpers.py
git add pyproject.toml uv.lock
git add tests/test_skill.py
git commit -m "$(cat <<'EOF'
phase 10/wave 1: relocate 7 calc CLIs into .claude/skills/mortgage-ops/scripts/ (SKLL-10 / SC-3 full closure)

Per LOCKED DECISION D-01 + D-08 retirement:
- git mv 7 user-facing calc CLIs (amortize.py, affordability.py, arm_simulate.py,
  refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py) plus
  _cli_helpers.py from scripts/ -> .claude/skills/mortgage-ops/scripts/
- D-06: scripts/_generate_arm_fixtures.py + scripts/hooks/* stay at project
  root (dev tooling, not user-facing CLIs)
- Updated sys.path injection in 7 scripts: parents[4] = repo root,
  parents[1] = skill root, so both `from lib.*` AND `from scripts._cli_helpers`
  resolve correctly
- Updated SCRIPT_PATH constants in 7 test files (Phase 3/6/7/8 D-17 portability seam)
- Updated tests/test_cli_helpers.py sys.path inject for the relocated helper
- Extended pyproject.toml ruff src + mypy files + pytest pythonpath
- Flipped Wave 0 xfail test_seven_scripts_in_skill_folder_only to PASS asserting
  all 7 scripts present (full SC-3 closure, not partial). Test consumes the
  `repo_root` pytest fixture (Plan 10-00 Task 3) — NOT
  `skill_root.parent.parent.parent.parent` which overshoots repo root.

Phase 6/7/8/9 are COMPLETE per STATE.md, so all 7 calc scripts existed at root
pre-move and are relocated together in one atomic git mv. The earlier "ship to
root then Phase 10 relocates 4 of 7" pattern (D-08 cross-phase contract) is
RETIRED — no further deferred relocation pattern remains.

Phase 9 baseline (>= 549 passed) preserved end-to-end; mypy --strict + ruff
clean across all touched files.

Closes: SKLL-10, ROADMAP Phase 10 SC-3 (full).
EOF
)"
```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest -q 2&gt;&amp;1 | tail -5 &amp;&amp; pytest tests/test_skill.py::test_seven_scripts_in_skill_folder_only -v 2&gt;&amp;1 | tail -5 &amp;&amp; git log -1 --oneline</automated>
  </verify>
  <acceptance_criteria>
- `pytest -q` shows ≥ 549 passed (Phase 9 baseline preserved)
- `pytest -q` shows ≥ 14 xfailed (Wave 0 ≥ 15 minus the 1 flipped)
- `pytest -q` shows 0 failed, 0 errored
- `pytest tests/test_skill.py::test_seven_scripts_in_skill_folder_only` exits 0 PASS
- Test signature consumes BOTH `skill_root` AND `repo_root` fixtures (Round-2 codex HIGH 1)
- `grep -c 'skill_root.parent.parent.parent.parent' tests/test_skill.py` returns 0 in this test (the overshoot pattern is forbidden)
- Test docstring asserts all 7 calc scripts (not "4 of 7")
- Commit exists with subject "phase 10/wave 1: relocate 7 calc CLIs ..."
- Commit body contains "D-01", "D-06", "SKLL-10", "all 7"
- Commit body has NO "Co-Authored-By" line and NO "Claude" / "AI" / "Anthropic" attribution
- `git log -1 --stat` shows ≥ 16 files changed (8 renames + ≥ 7 test files + pyproject + test_skill)
  </acceptance_criteria>
  <done>
    Full suite green; SKLL-10 / SC-3 fully closed (all 7 scripts asserted in skill folder); flipped test consumes `repo_root` fixture (no `parent.parent.parent.parent` overshoot); relocation committed atomically without AI attribution.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Project-root scripts/ → skill-folder scripts/ | Physical move via git mv must preserve history; lose history = lose Phase 3/4/5/6/7/8 D-XX commit-message context |
| sys.path injection block → import resolution | If parents[4] is wrong (off by 1 level), `from lib.*` fails silently at runtime |
| pyproject.toml pythonpath → pytest collection | If skill root not on pytest pythonpath, test_cli_helpers.py import fails at COLLECTION time (ERROR not FAIL) |
| Phase 9 baseline (549 tests) → relocated codebase | If any test breaks, the wave is invalid; entire test surface depends on the relocated scripts behaving identically |
| 7-script atomicity | Splitting the relocation into multiple commits leaves a window where SKILL.md routing can dispatch to scripts that don't yet live where SKILL.md says they do |
| Path arithmetic from tests (Round-2 codex HIGH 1) | `skill_root.parent.parent.parent.parent` overshoots repo root by one level; flipped test uses `repo_root` fixture from Plan 10-00 Task 3 instead |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-06 | Tampering (history loss) | git mv vs cp+rm | mitigate | Task 2 explicitly mandates `git mv`; the action body refuses `cp` or plain `mv` alternatives |
| T-10-07 | Repudiation (silent test breakage) | sys.path depth wrong | mitigate | Task 6 PART A asserts ≥ 549 passed BEFORE flipping any xfail; bail-on-fail discipline |
| T-10-08 | Tampering (D-06 violation — fixture generator accidentally moved) | scripts/_generate_arm_fixtures.py | mitigate | Task 1 + Task 2 + Task 6 explicitly verify D-06 stay-at-root files unchanged |
| T-10-09 | Information Disclosure (CLAUDE.md global rule violation in commit) | commit message | mitigate | Task 6 PART D HEREDOC explicitly omits Co-Authored-By; acceptance criteria asserts no AI attribution |
| T-10-10 | DoS (--help slowdown after sys.path edit) | D-18 fast --help | mitigate | Task 3 verify runs --help on all 7 scripts; acceptance criteria allows < 500ms tolerance for cold-cache run |
| T-10-37 | Tampering (false partial closure of SC-3) | SKLL-10 test docstring | mitigate | Task 6 PART B asserts ALL 7 scripts; no "4 of 7" loophole. Wave 0 stub revised to anticipate the full assertion. |
| T-10-49 | Tampering (path arithmetic overshoot) | flipped SKLL-10 test | mitigate | Task 6 PART B uses `repo_root` fixture from Plan 10-00; acceptance forbids `skill_root.parent.parent.parent.parent` substring (Round-2 codex HIGH 1) |
</threat_model>

<verification>
- 8 files (7 calc scripts + helper) physically present in `.claude/skills/mortgage-ops/scripts/`
- 8 files ABSENT from `scripts/`
- D-06 stay-at-root files (`_generate_arm_fixtures.py`, `hooks/block-user-layer.py`) untouched
- 7 calc scripts have updated `parents[4]` + `parents[1]` sys.path injection
- 8 test files have updated SCRIPT_PATH or sys.path injection (7 SCRIPT_PATH + 1 sys.path)
- pyproject.toml `src` + `files` extended; pytest `pythonpath` added
- mypy --strict + ruff + pytest --collect-only ALL clean across relocated files
- Full pytest: ≥ 549 passed + ≥ 14 xfailed + 0 failed + 0 errored
- SKLL-10 xfail flipped to PASS asserting all 7 scripts (using `repo_root` fixture; no `parent.parent.parent.parent` overshoot per Round-2 codex HIGH 1)
- Atomic commit with no AI attribution
</verification>

<success_criteria>
- All 7 user-CLI scripts + helper physically relocated via git mv (history preserved)
- All 8 affected test files (7 SCRIPT_PATH + 1 sys.path) updated
- pyproject.toml extended for ruff/mypy/pytest
- Phase 9 baseline (≥ 549 passed) preserved end-to-end
- SKLL-10 closed FULLY (all 7 scripts asserted; SC-3 closes without "partial" qualifier; uses `repo_root` fixture per Round-2 codex HIGH 1)
- mypy --strict + ruff format clean across all touched files
- Atomic commit with no AI attribution
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-01-SUMMARY.md` documenting:
- 8 files relocated via git mv (with old path + new path table)
- Phase 9 baseline pass count BEFORE relocation vs AFTER (must be equal or higher)
- xfail count BEFORE (≥ 15) vs AFTER (≥ 14 — one less because SKLL-10 flipped)
- mypy + ruff status (must be clean across `.claude/skills/mortgage-ops/scripts/` + 8 modified test files)
- D-08 retirement note: with all 7 scripts now in skill folder, the "ship to root then relocate" pattern carries no further work
- Confirmation that flipped test uses `repo_root` fixture (Round-2 codex HIGH 1)
- Any deviation from the plan, rationale, and code-review touchpoint
</output>
</content>
</invoke>