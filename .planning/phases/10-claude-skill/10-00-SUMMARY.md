---
phase: 10
plan: 00
subsystem: claude-skill
tags:
  - phase-10
  - claude-skill
  - test-infrastructure
  - nyquist
  - wave-0
requires: []
provides:
  - tests/test_skill.py (16 strict-xfail stubs covering SKLL-01..13)
  - tests/_skill_helpers.py (count_tokens, assert_under_budget — cl100k_base)
  - skill_root pytest fixture (.claude/skills/mortgage-ops path constant)
  - repo_root pytest fixture (Path(__file__).resolve().parents[1])
  - tests/fixtures/skill/.gitkeep (Phase 11/12 invocation-capture seam)
  - tiktoken>=0.7,<1.0 in [dependency-groups].dev (alphabetized)
  - .pre-commit-config.yaml mypy additional_dependencies mirrors tiktoken
affects:
  - pyproject.toml (dev deps alphabetized; tiktoken added; pytest-timeout preserved)
  - uv.lock (refreshed via `uv sync --quiet`)
  - tests/conftest.py (appended skill_root + repo_root fixtures; existing 9 fixtures + node_orchestration_run helper untouched)
  - .pre-commit-config.yaml (mypy additional_dependencies += tiktoken — lockstep with pyproject.toml dev deps as the file's own comment instructs)
tech-stack:
  added:
    - tiktoken>=0.7,<1.0 (cl100k_base BPE tokenizer; pinned per D-02 rationale)
  patterns:
    - strict-xfail stub pattern (Phase 5 D-XX inheritance — strict=True forces flipping wave to also remove the decorator)
    - subprocess-only CLI testing (PATTERNS line 803 — survives Phase 10 script relocation)
    - filesystem-introspection meta-tests (PATTERNS line 811)
    - deferred-import F401 hygiene (Round-2 codex HIGH 5 — Wave 5 import-housekeeping step re-adds module-level imports when bodies consume them)
    - parents[1] path-arithmetic seam (Round-2 codex HIGH 1 — repo_root fixture is the single source of truth)
key-files:
  created:
    - tests/_skill_helpers.py
    - tests/test_skill.py
    - tests/fixtures/skill/.gitkeep
  modified:
    - pyproject.toml
    - uv.lock
    - tests/conftest.py
    - .pre-commit-config.yaml
decisions:
  - "Wave 0 ships 16 xfail stubs (≥ 15 floor satisfied; SKLL-13 closure gets 2 dedicated stubs per D-13-05)"
  - "Module-level imports limited to __future__, typing.TYPE_CHECKING, pytest, pathlib.Path under TYPE_CHECKING — F401/TC003 hygiene clean at Wave 0 commit"
  - "repo_root fixture lands in Wave 0 (NOT deferred) so Wave 5/6 plans have the path-arithmetic seam ready when they consume it"
  - "SKLL-13 stub docstrings reference REAL Phase 9 CLI: insert-report --scenario-id <int> --file <path>; fictional --insert-report --json never appears (verified by acceptance grep returning 0)"
metrics:
  duration_minutes: 16
  tasks_completed: 5
  commits: 4
  tests_added: 16
  files_created: 3
  files_modified: 4
  completed_date: "2026-05-10"
---

# Phase 10 Plan 00: Test Infrastructure Summary

Establishes the Phase 10 Nyquist test scaffold — 16 strict-xfail stubs covering SKLL-01..13, the cl100k_base token-counting harness for Phase 10/11/12 reuse, and the `skill_root` + `repo_root` pytest fixtures that downstream waves consume. Zero skill content shipped; downstream Plans 10-01..10-05 flip these stubs to real assertions.

## What Shipped

| Artifact | Purpose | Lines |
|----------|---------|-------|
| `tests/test_skill.py` | 16 strict-xfail stubs (SKLL-01..13 + D-PROF-01) — landing pads for Waves 1-5 | 315 |
| `tests/_skill_helpers.py` | `count_tokens()` + `assert_under_budget()` cl100k_base harness | 49 |
| `tests/conftest.py` (extended) | `skill_root` fixture (Path constant) + `repo_root` fixture (`parents[1]`) | +34 |
| `tests/fixtures/skill/.gitkeep` | Empty placeholder dir for Phase 11/12 invocation captures | 0 |
| `pyproject.toml` (modified) | `tiktoken>=0.7,<1.0` added to dev deps (alphabetized; pytest-timeout preserved) | +5 |
| `uv.lock` (refreshed) | tiktoken 0.x dependency tree resolved | +252 |
| `.pre-commit-config.yaml` (modified) | mypy `additional_dependencies += tiktoken` (lockstep mirroring per the file's own comment) | +1 |

## Commits

| # | Hash | Type | Subject |
|---|------|------|---------|
| 1 | `b6070a7` | chore | add tiktoken>=0.7,<1.0 to dev dependencies |
| 2 | `2f45cef` | feat | add tests/_skill_helpers.py with cl100k token harness |
| 3 | `0ffe25f` | feat | add skill_root + repo_root fixtures + skill fixtures dir |
| 4 | `930a646` | test | add 16 xfail stubs for SKLL-01..13 (Phase 10 test surface) |

## Test Results

**Full suite:** `549 passed, 4 skipped, 17 xfailed, 3 warnings, 0 failed, 0 errored` (295s wall).

**Phase 10 stubs only:** 16 xfailed cleanly (no XPASS, no ERROR).

**Phase 5 baseline preservation:** 549 passed ≫ 432 floor (success criterion satisfied; the +117 delta over the 432 floor reflects every PASS-emitting plan from Phases 5-9 that landed after the Phase 5 SUMMARY metric was recorded).

**xfail accounting:**
- Pre-existing: 1 (Phase 5 ARM oracle Bankrate/Vertex42 cross-source agreement deferral, NOT touched by this wave)
- New from Wave 0: 16 (Phase 10 stubs)
- Total: 17 ✓

## Hygiene Results

| Tool | Files | Result |
|------|-------|--------|
| `mypy --strict` | tests/conftest.py, tests/test_skill.py, tests/_skill_helpers.py | Clean — no issues found in 3 source files |
| `ruff check` | tests/conftest.py, tests/test_skill.py, tests/_skill_helpers.py | All checks passed (NO F401, NO TC003) |
| `ruff format --check` | tests/conftest.py, tests/test_skill.py, tests/_skill_helpers.py | 3 files already formatted |
| pre-commit hooks | every commit | All gates passed (ruff, ruff-format, mypy, block-user-layer) |

## Stub-to-Wave Mapping (16 stubs)

| Stub | Requirement | Flipping Wave/Plan | Notes |
|------|-------------|--------------------|-------|
| `test_skill_md_under_token_budget` | SKLL-01 | Wave 5 / Plan 10-05 | uses `count_tokens` from this wave; threshold 4500 cl100k per D-02 |
| `test_skill_md_under_line_budget` | SKLL-01 | Wave 5 / Plan 10-05 | ≤ 500 lines |
| `test_skill_routing_in_first_200_lines` | SKLL-02 | Wave 5 / Plan 10-05 | per D-12 |
| `test_skill_md_frontmatter_required_fields` | SKLL-03 | Wave 5 / Plan 10-05 | name/description/license/compatibility |
| `test_license_txt_exists_in_skill_folder` | SKLL-04 | Wave 5 / Plan 10-05 | LICENSE.txt MIT default per D-04 |
| `test_modes_exist` | SKLL-05 | Wave 5 / Plan 10-05 | 7 modes (evaluate/compare/refinance/affordability/stress/amortize/arm) |
| `test_shared_mode_has_required_sections` | SKLL-06 | Wave 5 / Plan 10-05 | modes/_shared.md scoring + report structure |
| `test_profile_md_user_layer_gitignored` | SKLL-07 | Wave 5 / Plan 10-05 | per D-07 .example.md committed; .md gitignored |
| `test_profile_example_md_has_exact_four_keys` | D-PROF-01 | Wave 5 / Plan 10-05 | YAML keys: verbosity, citation_density, save_report, disambiguation |
| `test_references_exist` | SKLL-08 | Wave 5 / Plan 10-05 | 9 references files |
| `test_skill_md_documents_progressive_disclosure` | SKLL-09 | Wave 5 / Plan 10-05 | per D-09 topic→reference table |
| `test_seven_scripts_in_skill_folder_only` | SKLL-10 | **Wave 1 / Plan 10-01** | 7 scripts relocated (D-01 + D-06 + D-08) |
| `test_skill_md_shell_out_doctrine` | SKLL-11 | Wave 5 / Plan 10-05 | UI-SPEC §g math-discipline doctrine |
| `test_each_script_has_help_and_doctrine_documented` | SKLL-12 | Wave 5 / Plan 10-05 | webapp-testing exemplar `--help` doctrine |
| `test_report_filename_format` | **SKLL-13 (D-13-02)** | Wave 5 / Plan 10-05 | reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md |
| `test_report_persisted_to_duckdb` | **SKLL-13 (D-13-04)** | Wave 5 / Plan 10-05 | REAL CLI: `node orchestration/db-write.mjs insert-report --scenario-id <int> --file <path>` |

## Round-2 Codex Review Compliance

| Issue | Severity | Resolution |
|-------|----------|------------|
| HIGH-1 (path arithmetic overshoot) | High | `repo_root` fixture shipped in Wave 0; Wave 5/6 plans consume it instead of `skill_root.parent.parent.parent.parent`. Sanity-asserted in conftest by `Path('tests/conftest.py').resolve().parents[1]` resolving to dir containing `pyproject.toml`. |
| HIGH-2 (fictional CLI surface) | High | SKLL-13 stub docstrings reference the REAL `insert-report --scenario-id <int> --file <path>` form. Acceptance grep on fictional `--insert-report --json` returns 0 across `tests/test_skill.py`. |
| HIGH-5 (premature module-level imports) | High | Wave 0 module-level imports limited to `__future__`, `typing.TYPE_CHECKING`, `pytest`, `pathlib.Path` under TYPE_CHECKING. `re`, `subprocess`, `sys`, `yaml`, `count_tokens` all deferred — Plan 10-05 ships an "import housekeeping" step. |
| MEDIUM-6 (SKLL-12 split between waves) | Medium | Single Wave 5 flip covers all 7 relocated scripts uniformly. |
| MEDIUM-10 (uv.lock + dev-dep drift) | Medium | `uv sync --quiet` ran post-edit; uv.lock committed alongside pyproject.toml in the same commit. `pytest-timeout>=2.3` and every other dev dep preserved verbatim. |

## SKLL-13 Closure Stubs (D-13-05)

Per CONTEXT.md D-13-01..05, Phase 10 closes SKLL-13 (it is NOT deferred to Phase 9 or Phase 11). Two dedicated stubs ship in Wave 0:

1. **`test_report_filename_format`** — pins the `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md` filename convention from D-13-02. Wave 5 wires the assertion by parsing `modes/_shared.md` for the convention regex; Plan 10-06 adds the end-to-end smoke that actually writes a file matching the convention.
2. **`test_report_persisted_to_duckdb`** — pins the D-13-04 persistence call: `node orchestration/db-write.mjs insert-report --scenario-id <int> --file <path>`. Docstring explicitly notes that the `reports` table schema (`id, scenario_id, markdown_blob, generated_at`) has NO `filename` column, so the file on disk is the durable filename anchor and the DB row stores `(scenario_id, markdown_blob)`.

Both stubs reference the REAL Phase 9 CLI surface verified against `orchestration/db-write.mjs:296-310` (per Round-2 codex HIGH 2).

## Repo_root Fixture (Round-2 Codex HIGH 1 Resolution)

Wave 0 ships `repo_root` so Wave 5/6 tests have a single, off-by-one-resistant source of truth for the project root. The fixture body is `Path(__file__).resolve().parents[1]` (conftest.py lives in `tests/`, so `parents[0]` = `tests/`, `parents[1]` = repo root). Equivalent for callers that already have `skill_root`: `skill_root.parents[2]` (`.claude/skills/mortgage-ops` is three levels deep, not four). The forbidden form `skill_root.parent.parent.parent.parent` is documented as overshooting the repo root by one level.

Sanity check baked into Task 3 acceptance: `python -c "from pathlib import Path; r=Path('tests/conftest.py').resolve().parents[1]; assert (r / 'pyproject.toml').is_file()"` exits 0 — proving the path arithmetic resolves to the repo root that contains `pyproject.toml`.

## Deferred-Import Hygiene (Round-2 Codex HIGH 5 Resolution)

`tests/test_skill.py` Wave 0 module-level imports:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
import pytest
if TYPE_CHECKING:
    from pathlib import Path
```

Imports the flipped Wave 5 bodies will need (`re`, `subprocess`, `sys`, `yaml`, `from tests._skill_helpers import count_tokens`) are EXPRESSLY DEFERRED. Plan 10-05 (Wave 5) ships an explicit "import housekeeping" step that re-adds them at module level when the assertions consume them. Acceptance grep confirmed all five forbidden imports return 0 occurrences in Wave 0.

## Pyproject.toml + uv.lock Lockstep (Round-2 Codex MEDIUM 10 Resolution)

`tiktoken>=0.7,<1.0` added to `[dependency-groups].dev` alphabetized between `ruff>=0.15` and the (alphabetized) preceding `pytest-timeout>=2.3`. Every pre-existing entry preserved verbatim:

| Before (5 entries) | After (6 entries, alphabetized) |
|--------------------|---------------------------------|
| pytest>=9.0 | mypy>=1.20 |
| pytest-timeout>=2.3 | pre-commit>=4.6 |
| mypy>=1.20 | pytest>=9.0 |
| ruff>=0.15 | pytest-timeout>=2.3 |
| pre-commit>=4.6 | ruff>=0.15 |
| | **tiktoken>=0.7,<1.0** |

`uv sync --quiet` ran immediately after the edit; `uv.lock` regenerated and was committed in the same commit (`b6070a7`) as `pyproject.toml`. `pytest-timeout>=2.3` survives intact (acceptance `grep -c 'pytest-timeout' pyproject.toml` returns 1).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking issue] Pre-commit mypy hook missing tiktoken in additional_dependencies**

- **Found during:** Task 2 commit attempt
- **Issue:** Pre-commit's mypy hook runs in an isolated environment that pulls deps from `additional_dependencies` in `.pre-commit-config.yaml`, NOT from pyproject.toml. The hook failed at commit time with `Cannot find implementation or library stub for module named "tiktoken" [import-not-found]` even though `uv run mypy --strict tests/_skill_helpers.py` was clean.
- **Fix:** Added `- tiktoken>=0.7,<1.0` to the mypy hook's `additional_dependencies` list. The file's own header comment ("Re-run after editing pyproject.toml dev deps; bump `rev:` here in lockstep") explicitly authorizes this kind of mirror update. The newly-added pre-commit dep was committed with Task 2.
- **Files modified:** `.pre-commit-config.yaml`
- **Commit:** `2f45cef` (Task 2)

**2. [Rule 3 — blocking issue] Ruff TC003 fired on `from pathlib import Path`**

- **Found during:** Task 4 hygiene check after writing tests/test_skill.py
- **Issue:** Because `from __future__ import annotations` is in effect, `Path` was used only inside type annotations on test signatures. Ruff's TC003 rule (typing-only stdlib imports) demanded it move under TYPE_CHECKING.
- **Fix:** Replaced top-level `from pathlib import Path` with `from typing import TYPE_CHECKING` + an `if TYPE_CHECKING: from pathlib import Path` block. Functionally identical for callers since the runtime fixture supplies the actual Path object; only the static-typing import location changed.
- **Files modified:** `tests/test_skill.py`
- **Commit:** `930a646` (Task 4 — pre-commit caught and fixed before the commit landed)

Both deviations are pure CI-hygiene fixes — no behavior change to the test surface or production code.

## Self-Check: PASSED

**Files exist:**
- FOUND: tests/test_skill.py
- FOUND: tests/_skill_helpers.py
- FOUND: tests/fixtures/skill/.gitkeep
- FOUND: pyproject.toml (modified)
- FOUND: uv.lock (refreshed)
- FOUND: tests/conftest.py (extended)
- FOUND: .pre-commit-config.yaml (modified)

**Commits exist:**
- FOUND: b6070a7 chore(10-00): add tiktoken>=0.7,<1.0 to dev dependencies
- FOUND: 2f45cef feat(10-00): add tests/_skill_helpers.py with cl100k token harness
- FOUND: 0ffe25f feat(10-00): add skill_root + repo_root fixtures + skill fixtures dir
- FOUND: 930a646 test(10-00): add 16 xfail stubs for SKLL-01..13 (Phase 10 test surface)

**Acceptance gates:**
- 549 passed (≥ 432 floor): PASSED
- 16 new xfailed in tests/test_skill.py (≥ 15 floor): PASSED
- 0 failed, 0 errored: PASSED
- mypy --strict 3 files clean: PASSED
- ruff check 3 files clean (no F401, no TC003): PASSED
- ruff format --check 3 files clean: PASSED
- tiktoken importable: PASSED
- pytest-timeout>=2.3 preserved: PASSED
- repo_root fixture available: PASSED
- SKLL-13 closure stubs (test_report_filename_format + test_report_persisted_to_duckdb) reference REAL CLI: PASSED
- No fictional `--insert-report --json` references: PASSED
- No deferred imports leaked at module level: PASSED
