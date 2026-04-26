---
phase: 01-foundations-money-discipline
plan: 01
status: complete
requirements:
  - FND-03
  - FND-04
  - FND-05
  - FND-08
completed_date: 2026-04-26
---

# Phase 01 Plan 01: Project Skeleton + Money Discipline Bootstrap — Summary

Stood up the Python project skeleton: pyproject.toml with ruff / mypy --strict / pytest config, uv-managed lockfile, pinned Python 3.12, empty package markers, a shared `golden_fixture` test loader, and the seam directories every later wave depends on. The Wave-1 phase gate (`uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest`) exits 0 on a clean clone.

## Status

**COMPLETE.** All `must_haves.truths` verified. All `success_criteria` met. Both planned tasks executed and committed atomically.

## Files Created

| Path | Purpose | Bytes |
|------|---------|-------|
| `pyproject.toml` | Project deps + ruff / mypy --strict / pytest tool config; pins `numpy-financial==1.0.0`, `>=` ranges for pydantic / dateutil / dev tools (uv.lock pins exact resolutions) | 1195 |
| `uv.lock` | Reproducible install lockfile — 31 packages resolved | ~100 KB |
| `.python-version` | Pinned Python 3.12 (single line) | 5 |
| `lib/__init__.py` | Empty package marker. **Crucial Invariant:** Phase 1 exports nothing from `lib/`. Plan 03+ extends. | 0 |
| `tests/__init__.py` | Empty marker so `mypy --strict` does not warn about implicit namespace packages | 0 |
| `tests/fixtures/__init__.py` | Empty marker (same reason) | 0 |
| `tests/conftest.py` | Shared `golden_fixture` pytest factory — canonical loader for `tests/fixtures/golden_pmt.json`. Plan 05 ships the JSON; Phase 3+ amortization tests consume the same loader. | ~900 |
| `tests/test_smoke.py` | Single green test (`test_python_version_is_modern`) so Plan 06 CI has something to run before Plans 03/04/05 land | ~360 |
| `scripts/.gitkeep` | Reserve dir for Plan 06 `block-user-layer.py` pre-commit hook + Phase 3+ CLIs | 0 |
| `scripts/hooks/.gitkeep` | Reserve dir for git hooks | 0 |
| `config/.gitkeep` | Reserve dir; `config/household.example.yml` lands in Plan 02 | 0 |
| `data/reference/.gitkeep` | Phase 2 seam — regulatory YAMLs land here | 0 |
| `reports/.gitkeep` | Phase 7+ run output dir; `reports/*` gitignored in Plan 06 | 0 |
| `README.md` | One-paragraph stub pointing at `.planning/PROJECT.md` with the four `uv run` quick-start commands | ~590 |

## Files Modified

None — Wave 1 is greenfield scaffolding. The pre-existing `CLAUDE.md` (uncommitted from prior planning) was tracked as a separate scaffold commit (see commits list).

## Commits Made

| SHA | Subject |
|-----|---------|
| `273f705` | `chore(01): track CLAUDE.md conventions doc` |
| `cd48e82` | `feat(01): bootstrap uv project with ruff/mypy --strict/pytest config` |
| `9268e23` | `feat(01): scaffold lib/tests/scripts/config/data/reports skeleton` |

(A fourth commit will land for this SUMMARY.md per `commit_docs: true`.)

## pyproject.toml Highlights (canonical Phase 1 config)

- `[project] requires-python = ">=3.12"` with deps `pydantic>=2.13.3`, `python-dateutil>=2.9.0`, `numpy-financial==1.0.0` (exact pin per supply-chain mitigation T-1-01a)
- `[dependency-groups] dev`: `pytest>=9.0`, `mypy>=1.20`, `ruff>=0.15`, `pre-commit>=4.6`
- `[tool.hatch.build.targets.wheel] packages = ["lib"]` — wheel surface is `lib/` only
- `[tool.ruff] target-version = "py312"`, `line-length = 100`, `src = ["lib", "tests", "scripts"]`
- `[tool.ruff.lint] select = E, F, W, I, UP, B, SIM, RUF, TCH, PT` with `ignore = ["E501"]`
- `[tool.ruff.format] quote-style = "double"`
- `[tool.mypy] strict = true`, `files = ["lib", "tests", "scripts"]`, `plugins = ["pydantic.mypy"]`, plus `warn_unreachable / warn_redundant_casts / warn_unused_ignores = true`
- `[[tool.mypy.overrides]] module = "numpy_financial"` with `ignore_missing_imports = true` — Pitfall 4 mitigation. Phase 1 does not import `numpy_financial`, but Phase 3 will; shipping the override now keeps `mypy --strict` green throughout.
- `[tool.pytest.ini_options] minversion = "9.0"`, `testpaths = ["tests"]`, `addopts = ["-ra", "--strict-markers", "--strict-config"]`

## golden_fixture Loader (canonical fixture entry point)

`tests/conftest.py` exposes a single pytest fixture, `golden_fixture`, that returns a `Callable[[str], dict[str, Any]]` which loads a fixture by `id` from `tests/fixtures/golden_pmt.json`. This is the **canonical fixture-loading entry point** for Plan 05's `test_fixtures.py` (which ships the JSON and validates shape) and every Phase 3+ amortization test (which computes against the pinned values). Phase 3 must not introduce a parallel loader — it must consume this one.

The loader uses a `TYPE_CHECKING` import for `Callable` (with `from __future__ import annotations` in effect), satisfying ruff `UP035` + `TC003` while preserving the same runtime behavior the plan specified.

## Must-Haves Verification

### `must_haves.truths`

| Truth | Result |
|-------|--------|
| `uv sync --locked && uv run pytest` exits 0 on a clean checkout | **PASS** — `uv sync --locked` resolved 31 packages and reported `Checked 30 packages`; `uv run pytest` collected 1 test, reported `1 passed in 0.00s`, exit 0. |
| `uv run mypy --strict .` exits 0 on a clean checkout (with empty lib/) | **PASS** — `Success: no issues found in 5 source files`, exit 0. |
| `uv run ruff check .` exits 0 on a clean checkout | **PASS** — `All checks passed!`, exit 0. |
| Repo skeleton (`lib/`, `tests/`, `tests/fixtures/`, `config/`, `data/reference/`, `scripts/`, `scripts/hooks/`, `reports/`) exists and is tracked in git | **PASS** — every directory has either `__init__.py` or `.gitkeep` committed. |

### `must_haves.artifacts`

| Path | Provides | Verified |
|------|----------|----------|
| `pyproject.toml` | Project deps + ruff/mypy/pytest tool config; contains `[tool.ruff]` | **PASS** |
| `uv.lock` | Reproducible install lockfile | **PASS** |
| `.python-version` | Pinned Python 3.12 | **PASS** |
| `lib/__init__.py` | Empty package marker for `lib/` | **PASS** (0 bytes) |
| `tests/__init__.py` | Empty package marker so `mypy --strict` works | **PASS** (0 bytes) |
| `tests/conftest.py` | Shared `golden_fixture` loader (reusable by Phase 1 + Phase 3) | **PASS** |
| `tests/test_smoke.py` | Trivial green test so CI has something to run before Wave 2 | **PASS** |
| `README.md` | One-paragraph stub pointing at `.planning/PROJECT.md` | **PASS** |

### `must_haves.key_links`

| Link | Verified |
|------|----------|
| `pyproject.toml` → `uv.lock` via `uv sync --locked` | **PASS** — sync exited 0, lockfile is in lockstep with `pyproject.toml` |
| `pyproject.toml` → `lib/`, `tests/`, `scripts/` via `[tool.ruff] src` and `[tool.mypy] files` | **PASS** — both directives include all three dirs verbatim |

### Wave-1 Phase Gate (from `<verification>`)

`uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest` — **all four sub-commands exit 0**, confirmed in a single chained run. This is the Wave-1 merge boundary per PATTERNS.md Convention 9.

## Deviations from Plan

### 1. [Rule 1 — Bug] `tests/conftest.py` literal content failed the plan's own ruff gate

- **Found during:** Task 2 verify
- **Issue:** The plan's specified EXACT content for `tests/conftest.py` imports `Callable` from `typing`, which fails ruff `UP035` (the `UP` rule is in the plan's `[tool.ruff.lint] select`). After auto-fixing UP035 (`from collections.abc import Callable`), ruff then flagged `TC003` (the `TCH` rule, also in `select`) because `Callable` is only used in annotations and `from __future__ import annotations` is in effect — so the import must live in a `TYPE_CHECKING` block.
- **Fix:** Imported `Callable` inside `if TYPE_CHECKING:`, using `from typing import TYPE_CHECKING, Any`. Same runtime behavior, same fixture signature, ruff-clean and mypy-clean.
- **Files modified:** `tests/conftest.py`
- **Commit:** `9268e23`

### 2. [Rule 1 — Bug] `tests/conftest.py` and `tests/test_smoke.py` failed `ruff format --check`

- **Found during:** Wave-1 phase gate verification
- **Issue:** The plan's literal content for both files placed `from __future__ import annotations` immediately after the module docstring with no blank line. `ruff format` requires one blank line between the docstring and the first import.
- **Fix:** `uv run ruff format .` added the blank line; no semantic change.
- **Files modified:** `tests/conftest.py`, `tests/test_smoke.py`
- **Commit:** `9268e23`

Both deviations are minor formatter / linter compliance fixes to the plan's literal content. The plan's intent — "the Wave-1 phase gate exits 0" — is preserved verbatim; the literal byte-content of two test scaffold files differs from the plan by 1-3 lines each.

## Authentication Gates

None.

## Threat Flags

None — no new security-relevant surface introduced beyond what the plan's `<threat_model>` already enumerated. Mitigations T-1-01a (exact pin on `numpy-financial==1.0.0` + lockfile) and T-1-02a (`mypy strict = true` + `numpy_financial` override) shipped in Task 1.

## Follow-ups for Subsequent Plans

- **Plan 02:** Lands `config/household.example.yml` skeleton (the `.gitkeep` placeholder ships now).
- **Plan 03:** First real `lib/` module — must not introduce a parallel fixture loader; consume `tests/conftest.py:golden_fixture`.
- **Plan 05:** Ships `tests/fixtures/golden_pmt.json` (the file `golden_fixture` reads). Until Plan 05 lands, calling `golden_fixture(<id>)` raises `FileNotFoundError`, which is intentional — Plan 05 also adds `tests/test_fixtures.py` to validate the JSON shape.
- **Plan 06:** Lands `.gitignore` (covering `.venv/`, `tests/__pycache__/`, `data/*.duckdb`, `reports/*`, User Layer config files), plus `block-user-layer.py` pre-commit hook and the CI workflow that runs the Wave-1 phase gate. The `tests/__pycache__/` dir generated by pytest in this plan was deliberately left untracked pending Plan 06's `.gitignore`.

## Self-Check: PASSED

- All committed files exist and are tracked:
  - `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`
  - `lib/__init__.py`, `tests/__init__.py`, `tests/fixtures/__init__.py`, `tests/conftest.py`, `tests/test_smoke.py`
  - `scripts/.gitkeep`, `scripts/hooks/.gitkeep`, `config/.gitkeep`, `data/reference/.gitkeep`, `reports/.gitkeep`
  - `CLAUDE.md` (tracked via `273f705`)
- All commits present in `git log`: `273f705`, `cd48e82`, `9268e23`
- Wave-1 phase gate (`ruff check . && ruff format --check . && mypy --strict . && pytest`) exits 0
- Primary truth (`uv sync --locked && uv run pytest`) exits 0
