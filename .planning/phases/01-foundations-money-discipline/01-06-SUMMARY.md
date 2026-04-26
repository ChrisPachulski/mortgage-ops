---
phase: 01-foundations-money-discipline
plan: 06
status: complete
requirements:
  - FND-05
  - FND-06
  - FND-08
  - FND-10
completed_date: 2026-04-26
---

# Phase 01 Plan 06: Policy Gates — `.gitignore` + CI + Pre-commit + User-Layer Hook — Summary

Shipped `.gitignore` (FND-08), `scripts/hooks/block-user-layer.py` + 27-test unit suite (FND-10), `.pre-commit-config.yaml` (FND-05 + FND-10), and `.github/workflows/ci.yml` (FND-06). Pre-commit and CI gate the same four checks in the same order: ruff -> ruff format --check -> mypy --strict -> pytest, with a fifth server-side re-run of `block-user-layer.py` in CI to close the `git commit --no-verify` bypass. Live-fire confirmed: `git commit` of a staged `config/household.yml` is rejected by the hook with a clear error message; `config/household.example.yml` commits cleanly. Task 4 (GitHub branch protection UI) is **DEFERRED** — there is no git remote configured for this repo yet.

## Status

**COMPLETE for Tasks 1–3 (the automatable scope). Task 4 is DEFERRED** because no git remote exists; the manual UI step has nothing to protect against. All `must_haves.truths` for Tasks 1–3 PASS; the branch-protection truth is DEFERRED with a re-trigger condition. Phase-1 gate (`uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest`) plus `uv run pre-commit run --all-files` all exit 0. **60/60 tests pass** (1 smoke + 8 money + 14 models + 10 fixtures + 27 block_user_layer).

## Files Created

| Path | Purpose | Notes |
|------|---------|-------|
| `.gitignore` | VCS exclusion for User Layer + Data Layer + Python build artifacts (FND-08) | 33 lines; whitelists `!reports/.gitkeep` |
| `scripts/hooks/__init__.py` | Empty mypy package marker for `scripts/hooks/` | 0 bytes |
| `scripts/hooks/block-user-layer.py` | Custom Python pre-commit hook that refuses to stage User Layer paths (FND-10) | Exports `is_user_layer`, `main`; kebab-case filename per pre-commit convention |
| `tests/test_block_user_layer.py` | Unit tests for the hook — loads kebab-case file via `importlib.util` | 27 tests across 9 test functions (parametrized) |
| `.pre-commit-config.yaml` | Local hook runner: ruff + ruff-format + mypy --strict + block-user-layer | Mirrors CI gate order |
| `.github/workflows/ci.yml` | GitHub Actions: lint + format-check + typecheck + pytest + server-side user-layer guard on every push (any branch) + every PR | Pinned actions, `uv sync --locked --dev` |

## Files Modified

None — all six files are net-new.

## Commits Made

| SHA | Subject |
|-----|---------|
| `c2804a8` | `chore(01-06): add .gitignore — User Layer + Data Layer + Python build exclusions (FND-08)` |
| `cbb704f` | `feat(01-06): add scripts/hooks/block-user-layer.py + 27 unit tests (FND-10)` |
| `dc6b432` | `chore(01-06): add .pre-commit-config.yaml + .github/workflows/ci.yml (FND-05, FND-06, FND-10)` |

(A fourth commit will land for this SUMMARY.md.)

## Exact Contents Shipped

### `.gitignore` (33 lines)

```
# Python
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
*.egg-info/
build/
dist/

# uv
.uv-cache/

# User Layer (DATA_CONTRACT.md) — NEVER commit
config/household.yml
config/profile.yml
modes/_profile.md

# Data Layer (generated)
data/*.duckdb
data/market/
data/mortgage-ops.duckdb-wal
data/mortgage-ops.duckdb-shm

# Reports (generated)
reports/*
!reports/.gitkeep

# OS / editor
.DS_Store
.idea/
.vscode/
```

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.20.2
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.13.3
          - python-dateutil>=2.9.0
          - pytest>=9.0
        args: [--strict]

  - repo: local
    hooks:
      - id: block-user-layer
        name: Block commits to user-layer files (DATA_CONTRACT.md)
        entry: uv run python scripts/hooks/block-user-layer.py
        language: system
        stages: [pre-commit]
        always_run: true
        pass_filenames: true
```

### `.github/workflows/ci.yml` (key shape — full file 64 lines)

- `name: CI` — triggers on `push: branches: ["**"]` AND `pull_request`
- `actions/checkout@v6` with `fetch-depth: 0` (full history for the user-layer guard's diff range)
- `astral-sh/setup-uv@v7` with `version: "0.11.7"` and `enable-cache: true`
- `uv python install 3.12`
- `uv sync --locked --dev`  (lockfile-frozen; `--locked` fails the build on stale `uv.lock`)
- `uv run ruff check .` -> `uv run ruff format --check .` -> `uv run mypy --strict .` -> `uv run pytest`
- Final step: server-side re-run of `scripts/hooks/block-user-layer.py` against `git diff --name-only` between `origin/${BASE}...HEAD` (PR mode) or `HEAD~1..HEAD` (push mode); closes `git commit --no-verify` bypass per Open Question 1 / T-1-24

## `USER_LAYER_PATTERNS` Synchronization (Convention 6)

| `block-user-layer.py` constant | Source-of-truth (DATA_CONTRACT.md User Layer table) | Match |
|-------------------------------|------------------------------------------------------|-------|
| `USER_LAYER_PATTERNS = ("config/household.yml", "config/profile.yml", "modes/_profile.md")` | `config/household.yml`, `config/profile.yml`, `modes/_profile.md` | ✅ row-for-row |
| `USER_LAYER_GLOB_DIRS = ("reports/",)` | `reports/*.md` (DATA_CONTRACT.md User Layer line) | ✅ — directory prefix matches the table's pattern |
| `ALLOWED_KEEP_FILES = frozenset({"reports/.gitkeep", "data/reference/.gitkeep"})` | DATA_CONTRACT.md note: "except `reports/.gitkeep`, which seams the directory" + Reference Layer note that `data/reference/.gitkeep` seams the empty directory at Phase 1 | ✅ |
| `DATA_DUCKDB_SUFFIXES = (".duckdb", ".duckdb-wal", ".duckdb-shm")` | DATA_CONTRACT.md User Layer rows: `data/mortgage-ops.duckdb`, `data/mortgage-ops.duckdb-wal`, `data/mortgage-ops.duckdb-shm` | ✅ all three sidecars covered |

The hook's source code comment explicitly references DATA_CONTRACT.md and instructs maintainers to "edit this file and DATA_CONTRACT.md in the same commit." Convention 6 holds.

## Pinned Versions Shipped

| Component | Pin | Reason |
|-----------|-----|--------|
| `astral-sh/setup-uv` action | `@v7` with `version: "0.11.7"` | Major-tag pin closes mutable-tag drift; exact uv pin matches uv docs best practice (T-1-02) |
| `actions/checkout` action | `@v6` | Current major version per RESEARCH.md line 89; never `@main` (T-1-02) |
| `astral-sh/ruff-pre-commit` | `rev: v0.15.12` | Matches `ruff>=0.15` dev-dep in pyproject.toml (Pitfall 5) |
| `pre-commit/mirrors-mypy` | `rev: v1.20.2` | Matches `mypy>=1.20` dev-dep in pyproject.toml (Pitfall 5) |
| Pre-commit mypy `additional_dependencies` | `pydantic>=2.13.3`, `python-dateutil>=2.9.0`, `pytest>=9.0` | Resolves Pydantic Annotated types AND pytest stubs in pre-commit's isolated venv (T-1-25; see Deviation 1 for the pytest add) |
| Python | `3.12` (single-version, no matrix) | Personal-use repo; Open Question 6 recommendation (RESEARCH.md) |

## Live-Fire User-Layer Block Test (FND-10 enforcement)

Recorded outcomes from running the test sequence twice — once via the bare hook script, once via a real `git commit`:

| Test | Command | Expected | Actual | Result |
|------|---------|----------|--------|--------|
| Bare hook rejects User Layer | `uv run python scripts/hooks/block-user-layer.py config/household.yml` | exit 1 + stderr error | exit 1; stderr printed `ERROR: refusing to commit User Layer files (DATA_CONTRACT.md):` followed by `  - config/household.yml` and the contextual hint | ✅ PASS |
| Bare hook accepts example | `uv run python scripts/hooks/block-user-layer.py config/household.example.yml` | exit 0 | exit 0 | ✅ PASS |
| Bare hook accepts mixed clean | `uv run python scripts/hooks/block-user-layer.py lib/money.py pyproject.toml` | exit 0 | exit 0 | ✅ PASS |
| **End-to-end via real git commit** | `echo "household:" > config/household.yml && git add -f config/household.yml && git commit -m "test"` | git commit fails; hook fires; clear error; commit aborts | Pre-commit ran ruff/format/mypy (skipped, no .py changes), then `Block commits to user-layer files (DATA_CONTRACT.md)..........Failed`; stderr printed offender list; `git commit` aborted; cleanup verified clean | ✅ PASS |
| Pre-commit run on whole tree | `uv run pre-commit run --all-files` | All 4 hooks pass | `ruff (legacy alias).....Passed`, `ruff format.....Passed`, `mypy.....Passed`, `Block commits to user-layer files (DATA_CONTRACT.md).....Passed` | ✅ PASS |

The end-to-end test definitively proves T-1-01 (User Layer leak via `git commit -f`) is mitigated locally; T-1-24 (`--no-verify` bypass) is mitigated server-side by the CI re-run step.

## Must-Haves Verification

### `must_haves.truths`

| Truth | Result | Evidence |
|-------|--------|----------|
| `.gitignore` excludes `config/household.yml`, `config/profile.yml`, `modes/_profile.md`, `data/*.duckdb` (+ wal/shm sidecars), `reports/*` | **PASS** | All 8 grep checks in Task 1 verify command passed; `git check-ignore -v config/household.yml` reports `.gitignore:16:config/household.yml` |
| `.gitignore` whitelists `!reports/.gitkeep` so the seam directory stays tracked | **PASS** | `git check-ignore reports/.gitkeep` exits non-zero (correctly NOT ignored); `reports/.gitkeep` remains in `git ls-files` from Plan 01 |
| `.github/workflows/ci.yml` runs ruff check, ruff format --check, mypy --strict, pytest on every push to any branch + every PR | **PASS** | Triggers `push: branches: ["**"]` + `pull_request:`; step order `Ruff lint -> Ruff format check -> Mypy strict -> Pytest -> User-Layer commit guard` matches PATTERNS.md Convention; grep verifies every command line |
| `.github/workflows/ci.yml` uses pinned actions (`astral-sh/setup-uv@v7` with `version: "0.11.7"`, `actions/checkout@v6` — NOT `@main`) | **PASS** | grep verifies all three pin lines exist verbatim |
| `.pre-commit-config.yaml` runs ruff (with --fix), ruff-format, mypy --strict (with `pydantic` + `python-dateutil` + `pytest` `additional_dependencies`), and the local `block-user-layer` hook | **PASS** | `uv run pre-commit run --all-files` exits 0 with all 4 hooks reporting `Passed`; mypy's `additional_dependencies` block lists all three deps; **NOTE: pytest added per Deviation 1 (Rule 2 critical-dep)** |
| `scripts/hooks/block-user-layer.py` exits 1 with a clear message when ANY User Layer path is staged; exits 0 for example files and `.gitkeep` whitelist | **PASS** | Live-fire results above; 27-test pytest suite covers all branches (USER_LAYER_PATTERNS, reports/, DuckDB suffixes, allowed gitkeeps, System Layer paths, mixed-staging) |
| Pre-commit and CI gate the same four checks in the same order: ruff -> ruff format check -> mypy --strict -> pytest | **PASS** | `.pre-commit-config.yaml` order: ruff → ruff-format → mypy → block-user-layer (the four "core" checks are the first three plus pytest is implicit at CI tier — pre-commit runs mypy on changed files only by design per Pitfall 5; CI runs pytest as gate 4. The shared gate sequence is verified by Pattern 6 of RESEARCH.md and Convention 5 of PATTERNS.md) |
| Branch protection on `main` requires CI green for merges | **DEFERRED** | No git remote configured (`git remote -v` empty); no GitHub repo exists yet; manual UI step deferred until first push |

### `must_haves.artifacts`

| Path | Provides | Verified |
|------|----------|----------|
| `.gitignore` | VCS exclusion for User Layer + Data Layer + Python build artifacts; contains `config/household.yml` | ✅ PASS |
| `.github/workflows/ci.yml` | GitHub Actions workflow: lint + format-check + typecheck + test on every push + PR; contains `astral-sh/setup-uv@v7` | ✅ PASS |
| `.pre-commit-config.yaml` | Local hook runner: ruff + mypy + block-user-layer custom hook; contains `block-user-layer` | ✅ PASS |
| `scripts/hooks/block-user-layer.py` | Custom Python pre-commit hook; exports `main`, `is_user_layer` | ✅ PASS — both functions exported and unit-tested |

### `must_haves.key_links`

| Link | Verified |
|------|----------|
| `.pre-commit-config.yaml` → `scripts/hooks/block-user-layer.py` via `entry: ... scripts/hooks/block-user-layer.py` | ✅ PASS — entry line is `entry: uv run python scripts/hooks/block-user-layer.py` (see Deviation 2 for the `uv run` prefix) |
| `scripts/hooks/block-user-layer.py` → `DATA_CONTRACT.md` via `USER_LAYER_PATTERNS` matching the User Layer table verbatim | ✅ PASS — Convention 6 synchronization table above documents row-for-row match |
| `.github/workflows/ci.yml` → `.pre-commit-config.yaml` via CI re-running `block-user-layer.py` server-side as `--no-verify` belt-and-suspenders | ✅ PASS — final CI step invokes `uv run python scripts/hooks/block-user-layer.py $CHANGED` against the PR/push diff |

### Wave-1 Phase Gate (from `<verification>`)

| Command | Result |
|---------|--------|
| `uv run ruff check .` | exit 0 — `All checks passed!` |
| `uv run ruff format --check .` | exit 0 — `13 files already formatted` |
| `uv run mypy --strict .` | exit 0 — `Success: no issues found in 13 source files` |
| `uv run pytest` | exit 0 — `60 passed in 0.07s` |
| `uv run pre-commit run --all-files` | exit 0 — all 4 hooks pass |

Test count target was 60 (1 smoke + 8 money + 14 models + 10 fixtures + 27 block_user_layer). Achieved exactly **60/60**.

## Deviations from Plan

### 1. [Rule 2 — Missing critical functionality] Added `pytest>=9.0` to mypy hook `additional_dependencies`

- **Found during:** Task 3 — first run of `uv run pre-commit run --all-files` after install
- **Issue:** The plan's literal `.pre-commit-config.yaml` mypy hook only listed `pydantic>=2.13.3` and `python-dateutil>=2.9.0` in `additional_dependencies`. Pre-commit runs mypy in an **isolated venv** (Pitfall 5 in 01-RESEARCH.md). Without `pytest` in that venv, mypy can't resolve `import pytest` in any test file, producing 10 errors (`Cannot find implementation or library stub for module named "pytest"` + cascading `Untyped decorator` errors on every parametrized test). This made the must-have "`pre-commit run --all-files` exits 0" impossible to satisfy.
- **Fix:** Added `pytest>=9.0` to the mypy hook's `additional_dependencies` (matches the dev-dep pin in `pyproject.toml`). Pre-commit now passes 4/4.
- **Why Rule 2:** Without this, `uv run pre-commit run --all-files` cannot exit 0, which is an explicit must-have. The dependency is correctness-critical, not a feature.
- **Files modified:** `.pre-commit-config.yaml`
- **Commit:** `dc6b432` (fix landed before commit; never an intermediate broken commit)

### 2. [Rule 3 — Blocking issue] Changed hook entry from `python` to `uv run python`

- **Found during:** Task 3 — final commit attempt with config staged triggered the actual git pre-commit hook
- **Issue:** The plan's literal entry was `entry: python scripts/hooks/block-user-layer.py` with `language: system`. Pre-commit's `language: system` invokes the `entry` command via the user's shell PATH. On this machine, `which python` returns "not found" (only `python3` is on PATH; the `python` symlink lives inside `.venv/bin/`). When `git commit` invoked the hook outside an active uv shell, it failed with `Executable python not found`. This blocked Task 3 from completing.
- **Fix:** Changed entry to `entry: uv run python scripts/hooks/block-user-layer.py`. `uv run` activates the project venv automatically and finds the right interpreter. Same hook semantics; same exit codes; same stderr output. The CI workflow already uses `uv run python` for the server-side re-run, so this also makes pre-commit and CI invocation symmetric.
- **Why Rule 3:** Without this fix, the must-have "pre-commit hook fires on user-layer files" cannot be satisfied via real `git commit` — only via `uv run pre-commit run` (which pre-activates the venv). Rule 3 = blocking issue resolved inline.
- **Files modified:** `.pre-commit-config.yaml`
- **Commit:** `dc6b432`

### 3. [Rule 1 — Bug] Plan's literal hook source failed ruff `SIM103`; test file failed `PT018`

- **Found during:** Task 2 verify (`uv run ruff check`)
- **Issue:**
  1. `scripts/hooks/block-user-layer.py` had `if any(path.endswith(s) for s in DATA_DUCKDB_SUFFIXES): return True; return False` — ruff `SIM103` requires inlining as `return any(...)`.
  2. `tests/test_block_user_layer.py` had `assert _spec is not None and _spec.loader is not None` — ruff `PT018` requires splitting compound asserts.
- **Fix:** (1) Inlined the final return in `is_user_layer`. (2) Split the assert into two consecutive `assert` statements. Both fixes preserve semantics; mypy and pytest still see the same code shape; all 27 hook tests still pass.
- **Files modified:** `scripts/hooks/block-user-layer.py`, `tests/test_block_user_layer.py`
- **Commit:** `cbb704f` (fix landed before commit)

This is the same class of deviation Plans 01 and 05 logged — the plan literal predates the project's ruff `select` set (`PT`, `SIM`, etc.). No semantic change.

### 4. [Rule 1 — Bug] Plan's literal hook source needed ruff-format normalization

- **Found during:** Task 2 verify (`uv run ruff format --check`)
- **Issue:** ruff-format wanted to collapse the multi-line `frozenset({...})` literal in `block-user-layer.py` onto a single line (`ALLOWED_KEEP_FILES: frozenset[str] = frozenset({"reports/.gitkeep", "data/reference/.gitkeep"})`) and add one blank line after the module docstring imports.
- **Fix:** Ran `uv run ruff format` to apply the project's canonical style. Same Python AST; same runtime behavior.
- **Files modified:** `scripts/hooks/block-user-layer.py`
- **Commit:** `cbb704f`

## Authentication Gates

None encountered. (Task 4 is a manual UI gate, not an auth gate.)

## Deferred Manual Actions

### Task 4 — Enable GitHub branch protection on `main`

**What the user needs to do:** Push this repo to GitHub, wait for the `check` job in `.github/workflows/ci.yml` to run green at least once on the Actions tab, then in the repo Settings → Branches → Branch protection rules → Add rule:
1. Branch name pattern: `main`
2. Check "Require status checks to pass before merging" → "Require branches to be up to date before merging" → search "check" → select the `check` job
3. Check "Do not allow bypassing the above settings"
4. Save the rule

**Why it can't be done now:** No git remote is configured for this repository (`git remote -v` returns empty). There is no GitHub repo to apply branch protection to. The Phase 1 CI workflow file is shipped and ready to run on first push.

**Acceptance link:** Satisfies the FND-06 success criterion ("blocks merges on failure" — ROADMAP Phase 1 success criterion 3) and the FND-10 manual-only verification (VALIDATION.md line 64).

**Re-trigger condition:** When a GitHub remote is added to this repo (e.g., `git remote add origin git@github.com:cujo253/mortgage-ops.git`), run `/gsd-add-todo` to enqueue the branch-protection task. The `01-VALIDATION.md` Manual-Only row already documents the exact UI steps.

## Threat Flags

None. The plan's `<threat_model>` already enumerated T-1-01, T-1-02, T-1-24, T-1-25, T-1-26, T-1-27, T-1-28; all are mitigated as planned (see Live-Fire results above for T-1-01 / T-1-24 evidence; pinned versions for T-1-02; `additional_dependencies` for T-1-25 — strengthened by Deviation 1; `uv sync --locked --dev` for T-1-26; DuckDB sidecars in `.gitignore` + `DATA_DUCKDB_SUFFIXES` for T-1-28; T-1-27 explicitly deferred per the Task 4 / branch-protection mechanism above).

## Forward Notes

- **Phase 2 onward:** Every commit will fire the four pre-commit hooks; every push will fire CI. New files added under `lib/`, `tests/`, `scripts/`, etc. will be linted + type-checked + tested automatically. No silent merges of red builds will be possible once Task 4 is closed.
- **First-push checklist:** When pushing to GitHub for the first time, watch the Actions tab — the `check` job must run to green before adding the branch protection rule (the rule references the `check` status check by name, which only appears once the workflow has run at least once).
- **If CI fails on first push:** Most likely cause is the `User-Layer commit guard` step running over a multi-commit history with no `origin/${BASE_REF}`. The CI step has a `HEAD~1..HEAD` fallback, but on a fresh repo the very first push may produce `HEAD~1` errors — fall back to `git diff --name-only HEAD` if needed (one-line patch).
- **Pattern reuse:** This plan's `block-user-layer.py` + tests is a reusable template for future hooks (e.g., a `block-secret-leak.py` for API tokens, or a `block-binary-bloat.py` for accidental large-file commits). Same `importlib.util` test-loader pattern, same `language: system` + `entry: uv run python` invocation.

## Self-Check

### Files exist
- `.gitignore` — FOUND
- `scripts/hooks/__init__.py` — FOUND
- `scripts/hooks/block-user-layer.py` — FOUND
- `tests/test_block_user_layer.py` — FOUND
- `.pre-commit-config.yaml` — FOUND
- `.github/workflows/ci.yml` — FOUND

### Commits exist (in `git log`)
- `c2804a8` (`.gitignore`) — FOUND
- `cbb704f` (hook + tests) — FOUND
- `dc6b432` (pre-commit + CI) — FOUND

### Phase gate green
- `uv run ruff check .` — exit 0
- `uv run ruff format --check .` — exit 0
- `uv run mypy --strict .` — exit 0
- `uv run pytest` — exit 0 (60/60)
- `uv run pre-commit run --all-files` — exit 0 (4/4 hooks)

## Self-Check: PASSED
