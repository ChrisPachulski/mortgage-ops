---
phase: 05
plan: 04a
subsystem: arm-modeling
tags:
  - phase-05
  - arm-modeling
  - cli
  - shared-helper
  - factor-extract
  - hygiene
dependency_graph:
  requires:
    - "05-00"  # Wave 0 test infrastructure (no test changes here, but conventions inherited)
    - "05-01"  # quantize_rate (unrelated, but Wave-0/1 baseline frozen for byte-equivalence)
    - "scripts/amortize.py — Phase 3 source-of-truth for the float-gate + envelope (now a consumer)"
    - "scripts/affordability.py — Phase 4 mirror (now a consumer)"
  provides:
    - "scripts._cli_helpers.find_json_float_loc(raw) — shared JSON-float pre-validation gate (D-19)"
    - "scripts._cli_helpers.make_decimal_type_envelope(loc, input_str) — shared 6-key Pydantic-shape envelope builder (WR-02)"
  affects:
    - "Plan 05-04b — scripts/arm_simulate.py CLI (Wave 4 ARM-08 closure) imports both helpers from scripts._cli_helpers"
    - "Phase 6/7/8 future CLIs (refi NPV, APR, stress) — same shared module, no further duplication"
tech_stack:
  added: []
  patterns:
    - "Shared CLI helper module under scripts/ at project root (no __init__.py — scripts/ remains a non-package; consumers sys.path-inject the project root inside main() and import from scripts._cli_helpers)"
    - "Both helpers use lazy imports for decimal/pydantic so D-18 (--help fast) is preserved when consumers import them inside main()"
    - "Single source of truth for the 6-key WR-02 envelope shape across all JSON-in/JSON-out CLIs; lifetime version segment computed at call time from pydantic.VERSION"
key_files:
  created:
    - "scripts/_cli_helpers.py — 104 lines (find_json_float_loc + make_decimal_type_envelope)"
    - "tests/test_cli_helpers.py — 148 lines (8 + 10 + 1 = 19 parametric tests)"
  modified:
    - "scripts/amortize.py — net -71 lines (239 -> 168): removed inline _find_json_float_loc def + inline envelope dict; added helper import; dropped unused 'from typing import Any'"
    - "scripts/affordability.py — net -76 lines (321 -> 245): removed inline _find_json_float_loc def + inline envelope dict; added helper import; kept 'from typing import Any' (still used by TypeAdapter[Any])"
decisions:
  - "Helpers expose public names (find_json_float_loc, make_decimal_type_envelope) — leading underscore dropped vs. the inline _find_json_float_loc; intentional, this is now a cross-script API"
  - "scripts/_cli_helpers.py docstring URL pattern paraphrased to satisfy the 'errors.pydantic.dev appears once' grep gate while keeping documentation accurate (the live URL is constructed inside the function body)"
  - "Helper imports placed in a single sorted block inside main() (lib.X + pydantic + scripts._cli_helpers grouped together) to satisfy ruff I001; the plan's 'before lib.X' positional spec was not load-bearing — all three import groups run at the same call site"
  - "scripts/amortize.py drops 'from typing import Any' (no longer used after the inline helper was removed); scripts/affordability.py keeps it (TypeAdapter[Any] still references it)"
metrics:
  duration_minutes: 5
  completed: 2026-04-30
  tasks_completed: 3
  commits_created: 4  # 3 task commits + 1 docs commit (this summary)
  test_count_before: 392_passed_4_skipped_22_xfailed
  test_count_after: 411_passed_4_skipped_22_xfailed
  new_tests_added: 19  # tests/test_cli_helpers.py (>= 18 parametric required)
  lines_added_cli_helpers: 104
  lines_added_test_cli_helpers: 148
  lines_removed_amortize: 71
  lines_removed_affordability: 76
---

# Phase 5 Plan 04a: scripts/_cli_helpers Factor-Extract Summary

Hygiene/factor-extract: lifted the byte-identical `_find_json_float_loc` def and the byte-identical 6-key envelope construction out of `scripts/amortize.py` + `scripts/affordability.py` into a new shared module `scripts/_cli_helpers.py`, replaced the inline copies with imports, and pinned both helpers behind 19 parametric tests in `tests/test_cli_helpers.py`. Phase 3 and Phase 4 test suites pass byte-equivalent (120 passed, 4 skipped — same counts as Phase 5 Plan 03 closure baseline). No ARM-N requirement is closed in this plan; ARM-08 closure ships in Plan 05-04b which now imports `find_json_float_loc` + `make_decimal_type_envelope` from this shared module.

## Tasks Completed

| # | Task                                                                                  | Commit    | Outcome |
|---|---------------------------------------------------------------------------------------|-----------|---------|
| 1 | Create scripts/_cli_helpers.py with find_json_float_loc + make_decimal_type_envelope  | `031300d` | 104 lines; both helpers exported; mypy --strict + ruff clean; importable when project root is on sys.path |
| 2 | Add tests/test_cli_helpers.py with parametric coverage of both helpers                | `dee1b2c` | 148 lines; 19 tests (8 find_json_float_loc + 10 make_decimal_type_envelope + 1 round-trip); all green |
| 3 | Refactor scripts/amortize.py + scripts/affordability.py to import shared helpers      | `c7f0b1b` | Both inline _find_json_float_loc defs deleted; both inline 6-key envelopes deleted; imports added; -147 net LOC across the two scripts; Phase 3 + Phase 4 byte-equivalent (120 passed, 4 skipped) |

## Acceptance Gate Results

### Plan-level acceptance (`<must_haves>`)

| Gate                                                                                                                                                  | Result |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| `scripts/_cli_helpers.py` exists at project root and exports `find_json_float_loc` + `make_decimal_type_envelope`                                     | PASS   |
| `scripts/amortize.py` imports both helpers from `scripts._cli_helpers`; inline `_find_json_float_loc` def + inline envelope construction REMOVED      | PASS   |
| `scripts/affordability.py` imports both helpers from `scripts._cli_helpers`; inline `_find_json_float_loc` def + inline envelope construction REMOVED | PASS   |
| Phase 3 + Phase 4 test suites still pass byte-equivalent                                                                                              | PASS — 120 passed, 4 skipped (identical to baseline) |
| `tests/test_cli_helpers.py` covers both helpers with >= 18 parametric tests                                                                           | PASS — 19 tests |

### Task 1 grep gates (scripts/_cli_helpers.py)

| Gate                                                                                                       | Expected | Actual |
|------------------------------------------------------------------------------------------------------------|----------|--------|
| `wc -l scripts/_cli_helpers.py`                                                                            | >= 70    | 104 |
| `grep -c 'def find_json_float_loc' scripts/_cli_helpers.py`                                                | 1        | 1   |
| `grep -c 'def make_decimal_type_envelope' scripts/_cli_helpers.py`                                         | 1        | 1   |
| `grep -v '^#' scripts/_cli_helpers.py \| grep -c 'parse_float=_Decimal'`                                   | 1        | 1   |
| `grep -v '^#' scripts/_cli_helpers.py \| grep -c '"type": "decimal_type"'`                                 | 1        | 1   |
| `grep -v '^#' scripts/_cli_helpers.py \| grep -c 'errors.pydantic.dev'`                                    | 1        | 1   |
| `grep -v '^#' scripts/_cli_helpers.py \| grep -c 'from pydantic import VERSION'`                           | 1        | 1   |
| `test ! -e scripts/__init__.py`                                                                            | exit 0   | exit 0 (no __init__.py) |
| `mypy --strict scripts/_cli_helpers.py`                                                                    | exit 0   | exit 0 |
| `ruff check scripts/_cli_helpers.py`                                                                       | exit 0   | exit 0 |
| `ruff format --check scripts/_cli_helpers.py`                                                              | exit 0   | exit 0 |

### Task 2 grep gates (tests/test_cli_helpers.py)

| Gate                                                              | Expected | Actual |
|-------------------------------------------------------------------|----------|--------|
| `pytest tests/test_cli_helpers.py -x`                             | exit 0   | 19 passed |
| `grep -c 'def test_' tests/test_cli_helpers.py`                   | >= 18    | 19 |
| `mypy --strict tests/test_cli_helpers.py`                         | exit 0   | exit 0 |
| `ruff check tests/test_cli_helpers.py`                            | exit 0   | exit 0 |
| `ruff format --check tests/test_cli_helpers.py`                   | exit 0   | exit 0 |

### Task 3 grep gates (refactor)

| Gate                                                                                          | Expected | Actual |
|-----------------------------------------------------------------------------------------------|----------|--------|
| `grep -c 'def _find_json_float_loc' scripts/amortize.py`                                      | 0        | 0      |
| `grep -c 'def _find_json_float_loc' scripts/affordability.py`                                 | 0        | 0      |
| `grep -c 'from scripts._cli_helpers import' scripts/amortize.py`                              | 1        | 1      |
| `grep -c 'from scripts._cli_helpers import' scripts/affordability.py`                         | 1        | 1      |
| `grep -v '^#' scripts/amortize.py \| grep -c 'find_json_float_loc(raw)'`                      | 1        | 1      |
| `grep -v '^#' scripts/affordability.py \| grep -c 'find_json_float_loc(raw)'`                 | 1        | 1      |
| `grep -v '^#' scripts/amortize.py \| grep -c 'make_decimal_type_envelope('`                   | 1        | 1      |
| `grep -v '^#' scripts/affordability.py \| grep -c 'make_decimal_type_envelope('`              | 1        | 1      |
| `pytest tests/test_amortize.py -q` baseline preserved                                         | yes      | 42 passed (== baseline) |
| `pytest tests/test_affordability.py -q` baseline preserved                                    | yes      | 78 passed, 4 skipped (Phase 4 closure baseline; combined Phase3+4 = 120 passed, 4 skipped) |
| `mypy --strict scripts/amortize.py scripts/affordability.py`                                  | exit 0   | exit 0 |
| `ruff check scripts/amortize.py scripts/affordability.py`                                     | exit 0   | exit 0 |
| `ruff format --check scripts/amortize.py scripts/affordability.py`                            | exit 0   | exit 0 |

## Byte-Equivalent Envelope Verification (Headline Acceptance Gate)

Both CLIs invoked with the same float-bearing JSON before/after refactor; envelopes match byte-for-byte:

**scripts/amortize.py** (input: `{"loan": {"principal": 400000.50, ...}}` → stderr):
```
[{"type": "decimal_type", "loc": ["loan", "principal"], "msg": "Input should be a valid decimal — JSON string required for money/rate fields per D-19 (JSON floats are rejected at the boundary)", "input": "400000.50", "url": "https://errors.pydantic.dev/2.13/v/decimal_type", "ctx": {"class": "Decimal", "field_path": "loan.principal"}}]
```
exit code: 2 (unchanged).

**scripts/affordability.py** (input: forward-mode payload with `"loan_amount": 400000.50` → stderr):
```
[{"type": "decimal_type", "loc": ["loan_amount"], "msg": "Input should be a valid decimal — JSON string required for money/rate fields per D-19 (JSON floats are rejected at the boundary)", "input": "400000.50", "url": "https://errors.pydantic.dev/2.13/v/decimal_type", "ctx": {"class": "Decimal", "field_path": "loan_amount"}}]
```
exit code: 2 (unchanged).

Same 6 keys, same shape, same loc semantics, same Pydantic version segment computed at runtime — confirming the factor-extract is semantically null.

## Test Suite Status

| Stage         | Passed | Skipped | xfailed | xpassed | Failed | Errors |
|---------------|--------|---------|---------|---------|--------|--------|
| Baseline      | 392    | 4       | 22      | 0       | 0      | 0      |
| After 05-04a  | 411    | 4       | 22      | 0       | 0      | 0      |
| Delta         | +19    | 0       | 0       | 0       | 0      | 0      |

The +19 delta is exactly the new `tests/test_cli_helpers.py` count. Phase 3 (`tests/test_amortize.py`) and Phase 4 (`tests/test_affordability.py`) suites pass with the identical pre-refactor counts — byte-equivalent verified.

## Threat Mitigations

| Threat ID | Mitigation Status | Evidence |
|-----------|-------------------|----------|
| T-05-01 (helper layer) — JSON-float coercion bypass at the shared helper | Mitigated | `tests/test_cli_helpers.py::TestFindJsonFloatLoc` (8 tests) covers no-floats, top-level float, multiple floats (depth-first), nested list-in-dict, top-level list, invalid JSON, empty object, empty array. Phase 3 + Phase 4 float-gate tests still pass byte-equivalent. |
| T-05-23 — Envelope shape divergence across CLIs | Mitigated | Single source of truth at `scripts._cli_helpers.make_decimal_type_envelope`; `tests/test_cli_helpers.py::TestMakeDecimalTypeEnvelope` (10 tests) pins the exact 6-key shape, dot-joined field_path, runtime-Pydantic version segment, and ctx.class=Decimal. |
| T-05-25 — Phase 3/4 regression after factor | Mitigated | Task 3 acceptance gate ran both pre-existing suites; identical pass counts (120 passed, 4 skipped); byte-equivalent envelope confirmed by smoke-testing both CLIs on float-bearing JSON. |

## Deviations from Plan

### [Rule 3 — Blocking lint] ruff I001 import-organization in tests/test_cli_helpers.py

**Found during:** Task 2 ruff verification.

**Issue:** `from scripts._cli_helpers import ...` placed after a `sys.path.insert(...)` block triggered ruff `I001` (`Import block is un-sorted or un-formatted`). The plan-supplied content used `# noqa: E402` for the late import but that does not silence `I001`.

**Fix:** Extended the `noqa` directive to `# noqa: E402, I001`. The pattern is otherwise identical to what the plan specified.

**Files modified:** `tests/test_cli_helpers.py` (one-line change).

**Commit:** included in Task 2 commit `dee1b2c`.

### [Rule 3 — Blocking lint] ruff I001 import-organization in scripts/amortize.py + scripts/affordability.py

**Found during:** Task 3 ruff verification.

**Issue:** The plan specified the `from scripts._cli_helpers import ...` line be inserted "AFTER `sys.path.insert(0, _project_root)`, BEFORE the `lib.X` import block" — but ruff `I001` flags any deviation from a single sorted import block.

**Fix:** Merged the helper import into the existing `lib.X + pydantic` import block (sorted alphabetically: `lib.affordability`/`lib.amortize` → `lib.rules.loan_type` → `pydantic` → `scripts._cli_helpers`). Functionally identical: all imports execute in `main()` after the sys.path injection and before any helper call. The plan's positional ordering was a guideline, not load-bearing.

**Files modified:** `scripts/amortize.py`, `scripts/affordability.py` — both moved the helper import into the consolidated lazy-import block.

**Commit:** included in Task 3 commit `c7f0b1b`.

### [Rule 3 — Acceptance-gate alignment] scripts/_cli_helpers.py docstring URL paraphrase

**Found during:** Task 1 acceptance grep.

**Issue:** First-pass docstring on `make_decimal_type_envelope` contained the literal URL pattern `https://errors.pydantic.dev/{MAJOR.MINOR}/v/decimal_type`. This bumped the `grep -v '^#' | grep -c 'errors.pydantic.dev'` count to 2 (docstring + live URL), violating the gate which expects 1.

**Fix:** Paraphrased the docstring to "the canonical Pydantic docs URL with MAJOR.MINOR computed at call time" — preserves the documentation intent without including the literal URL token. The live URL construction in the function body is the only `errors.pydantic.dev` occurrence after the fix.

**Files modified:** `scripts/_cli_helpers.py` (3-line docstring tweak).

**Commit:** included in Task 1 commit `031300d`.

### [Rule 1 — Dead import] dropped `from typing import Any` from scripts/amortize.py

**Found during:** Task 3 (after deleting the inline `_find_json_float_loc` def).

**Issue:** `Any` was previously used only inside the inline `_find_json_float_loc` body (`def _walk(node: Any, path: list[str | int]) -> ...`). With that body removed, the import becomes unused and ruff's `F401` would flag it.

**Fix:** Removed `from typing import Any` from `scripts/amortize.py`. Did NOT remove it from `scripts/affordability.py` because that file still uses it (`adapter: TypeAdapter[Any] = TypeAdapter(AffordabilityRequest)` at line 226).

**Files modified:** `scripts/amortize.py`.

**Commit:** included in Task 3 commit `c7f0b1b`.

## Plan 05-04b Unblocked

`scripts/_cli_helpers.py` is now the single source of truth for:
- `find_json_float_loc(raw) -> tuple[list[str | int], str] | None`
- `make_decimal_type_envelope(loc, input_str) -> list[dict[str, Any]]`

Plan 05-04b (Wave 4 ARM-08 closure shipping `scripts/arm_simulate.py`) can now wire its float-gate + envelope to these shared helpers without re-introducing a third inline copy. The depends_on edge `05-04b -> 05-04a` is satisfied.

## Self-Check: PASSED

Verified post-write:

| Artifact                                                           | Check               | Status |
|--------------------------------------------------------------------|---------------------|--------|
| `scripts/_cli_helpers.py`                                          | file exists, 104 LOC | FOUND  |
| `tests/test_cli_helpers.py`                                        | file exists, 148 LOC | FOUND  |
| `scripts/amortize.py` (modified)                                   | git log shows c7f0b1b touched it | FOUND |
| `scripts/affordability.py` (modified)                              | git log shows c7f0b1b touched it | FOUND |
| Commit `031300d` (Task 1)                                          | in `git log --oneline` | FOUND |
| Commit `dee1b2c` (Task 2)                                          | in `git log --oneline` | FOUND |
| Commit `c7f0b1b` (Task 3)                                          | in `git log --oneline` | FOUND |
| `tests/test_cli_helpers.py` runs 19 passed                         | pytest output       | PASS   |
| Phase 3 + Phase 4 byte-equivalent (`tests/test_amortize.py + tests/test_affordability.py`) | pytest 120 passed 4 skipped (== baseline) | PASS |
| Full-suite pass count                                              | 411 passed, 4 skipped, 22 xfailed | PASS |
| mypy --strict on 4 affected files                                  | exit 0              | PASS   |
| ruff check + ruff format --check on 4 affected files               | exit 0              | PASS   |
| Byte-equivalent envelope smoke-test (both CLIs)                    | identical 6-key envelope, exit code 2 | PASS |
