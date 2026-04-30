---
phase: 05
plan: 04a
type: execute
wave: 4
depends_on:
  - "05-00"
  - "05-01"
files_modified:
  - scripts/_cli_helpers.py
  - scripts/amortize.py
  - scripts/affordability.py
  - tests/test_cli_helpers.py
autonomous: true
requirements: []
tags:
  - phase-05
  - arm-modeling
  - cli
  - shared-helper
  - factor-extract
  - hygiene
must_haves:
  truths:
    - "scripts/_cli_helpers.py exists at project root and exports two public functions: find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None AND make_decimal_type_envelope(loc: list[str | int], input_str: str) -> list[dict[str, Any]]"
    - "scripts/amortize.py imports find_json_float_loc + make_decimal_type_envelope from scripts._cli_helpers; the inline _find_json_float_loc def + inline envelope construction are REMOVED"
    - "scripts/affordability.py imports find_json_float_loc + make_decimal_type_envelope from scripts._cli_helpers; the inline _find_json_float_loc def + inline envelope construction are REMOVED"
    - "Phase 3 + Phase 4 test suites still pass byte-equivalent (PLAN-CHECKER NOTE: factor-extract MUST not regress existing CLIs)"
    - "tests/test_cli_helpers.py covers both helpers with >= 18 parametric tests"
  artifacts:
    - path: "scripts/_cli_helpers.py"
      provides: "Shared helpers for JSON-in/JSON-out scripts: find_json_float_loc + make_decimal_type_envelope"
      contains: "def find_json_float_loc"
      min_lines: 70
    - path: "tests/test_cli_helpers.py"
      provides: "Parametric tests for find_json_float_loc + make_decimal_type_envelope"
      contains: "def test_"
    - path: "scripts/amortize.py"
      provides: "Refactored to import from scripts._cli_helpers; inline _find_json_float_loc removed"
      contains: "from scripts._cli_helpers import"
    - path: "scripts/affordability.py"
      provides: "Refactored to import from scripts._cli_helpers; inline _find_json_float_loc removed"
      contains: "from scripts._cli_helpers import"
  key_links:
    - from: "scripts/amortize.py + scripts/affordability.py"
      to: "scripts._cli_helpers"
      via: "factored shared helper"
      pattern: "from scripts._cli_helpers import"
---

<objective>
Plan 05-04a (split half 1 of 2 per checker BLOCKER I-003): factor the JSON-float pre-validation gate (`_find_json_float_loc`) and the 6-key envelope construction out of `scripts/amortize.py` + `scripts/affordability.py` into a new shared module `scripts/_cli_helpers.py`. Phase 5 IS the third consumer of this helper; Phase 6 (refi NPV), Phase 7 (APR), Phase 8 (stress) will be the 4th, 5th, 6th — factoring NOW prevents 5 future copies of the same 50 lines (RESEARCH §Q8 explicit recommendation; CONTEXT.md D-discretion approves).

This plan is a HYGIENE FACTOR — no ARM-N requirement closure. The actual ARM-08 closure ships in Plan 05-04b which depends on this plan. Splitting is required because the original 05-04 had 6 tasks across 6 files, exceeding the 5-task threshold (BLOCKER I-003).

Owns threat T-05-01 (the JSON-float gate helper itself — see threat_model below) and T-05-23 (envelope shape divergence prevention) and T-05-25 (Phase 3/4 byte-equivalent regression prevention).

Purpose: Three deliverables in one plan because they are tightly coupled:
1. **scripts/_cli_helpers.py** — new shared module (single source of truth for the JSON-float gate + envelope)
2. **scripts/amortize.py + scripts/affordability.py refactor** — replace inline copies with imports (zero behavior change)
3. **tests/test_cli_helpers.py** — parametric tests pinning both helpers' behavior independently

Splitting these across separate plans would force the second plan to either (a) duplicate the helper (defeats the point) or (b) wait on a not-yet-shipped factor — they belong together as a single hygiene unit.

Output: 4 file mods + 1 new test file; Phase 3 + Phase 4 test suites byte-equivalent. No ARM-08 closure here (that ships in Plan 05-04b).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-arm-modeling/05-CONTEXT.md
@.planning/phases/05-arm-modeling/05-RESEARCH.md
@.planning/phases/05-arm-modeling/05-PATTERNS.md
@.planning/phases/05-arm-modeling/05-VALIDATION.md
@CLAUDE.md
@scripts/amortize.py
@scripts/affordability.py

<interfaces>
Existing _find_json_float_loc helper (currently in scripts/amortize.py:72-122 AND scripts/affordability.py:70-123 — verified BYTE-IDENTICAL by RESEARCH §Q8 grep on 2026-04-30):

```python
def _find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    """Walk parsed JSON and return (loc-path, decimal-string) of the first JSON float.
    [...50 lines of body...]
    """
    from decimal import Decimal as _Decimal
    try:
        parsed = json.loads(raw, parse_float=_Decimal)
    except json.JSONDecodeError:
        return None
    def _walk(node: Any, path: list[str | int]) -> tuple[list[str | int], str] | None:
        if isinstance(node, _Decimal):
            return (path, str(node))
        if isinstance(node, dict):
            for k, v in node.items():
                hit = _walk(v, [*path, k])
                if hit is not None:
                    return hit
        elif isinstance(node, list):
            for i, v in enumerate(node):
                hit = _walk(v, [*path, i])
                if hit is not None:
                    return hit
        return None
    return _walk(parsed, [])
```

Existing 6-key envelope construction (currently inline in scripts/amortize.py:196-213 + scripts/affordability.py:236-274 — also byte-equivalent):

```python
from pydantic import VERSION as _pydantic_version
_major_minor = ".".join(_pydantic_version.split(".")[:2])
envelope = [{
    "type": "decimal_type",
    "loc": float_loc,
    "msg": "Input should be a valid decimal — JSON string required for money/rate fields per D-19 (JSON floats are rejected at the boundary)",
    "input": float_input,
    "url": f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type",
    "ctx": {
        "class": "Decimal",
        "field_path": ".".join(str(p) for p in float_loc),
    },
}]
print(json.dumps(envelope), file=sys.stderr)
return 2
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create scripts/_cli_helpers.py with find_json_float_loc + make_decimal_type_envelope</name>
  <files>scripts/_cli_helpers.py</files>
  <read_first>
    - scripts/amortize.py:70-123 (the _find_json_float_loc def — lift verbatim, rename to drop leading underscore)
    - scripts/amortize.py:196-213 OR scripts/affordability.py:236-274 (the inline envelope construction — lift the 6-key shape)
    - 05-RESEARCH.md §Q8 (lines 218-292) — file shape + factor recipe
    - 05-PATTERNS.md "scripts/_cli_helpers.py" section (lines 358-405) — full skeleton
  </read_first>
  <action>
    Create scripts/_cli_helpers.py at project root. The file MUST:
    1. Lift `_find_json_float_loc` verbatim from scripts/amortize.py:70-123 (or affordability.py:70-123 — they are byte-identical). Rename to `find_json_float_loc` (drop leading underscore — public).
    2. Add a sibling `make_decimal_type_envelope(loc, input_str) -> list[dict[str, Any]]` that constructs the 6-key envelope with runtime-computed Pydantic version segment.

    File content (literal Python):

    ```
    """Shared CLI helpers for JSON-in/JSON-out scripts (Phase 3 D-19 / WR-02 closure inheritance).

    Phase 5 introduced this module when factoring _find_json_float_loc out of
    scripts/amortize.py + scripts/affordability.py to a single source of truth
    (RESEARCH Q8 + Plan-Checker note line 480).

    Phase 10 may relocate to .claude/skills/mortgage-ops/scripts/_cli_helpers.py
    following the script-relocation pattern; Phase 5 keeps it at project root
    per D-17 portability.

    Note: scripts/ is NOT a Python package by project convention (no __init__.py);
    consumers import from scripts._cli_helpers AFTER inserting project root into
    sys.path inside their main() body (Phase 3 / Phase 4 sys.path-injection idiom).
    """

    from __future__ import annotations

    import json
    from typing import Any


    def find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
        """Walk parsed JSON and return (loc-path, decimal-string) of the first JSON float.

        Pydantic v2 strict mode accepts JSON numbers for Decimal fields by design
        (https://docs.pydantic.dev/2.13/concepts/json/#json-parsing) — JSON has no
        distinct decimal type, so Pydantic permissively coerces JSON numbers. But
        the project's money-discipline contract (CLAUDE.md FND-01) and D-19 require
        money/rate fields to be JSON STRINGS (e.g. "400000.00"). So we pre-parse
        with `parse_float=Decimal` to mark JSON-numbers-with-decimal-points as
        Decimal instances, then walk the parsed tree to find the first Decimal —
        its loc-path identifies the offending field.

        Returns None if the input has no JSON floats or fails JSON parsing
        (in the latter case, Pydantic surfaces its canonical error downstream).

        Lifted verbatim from scripts/amortize.py:70-123 + scripts/affordability.py:70-123
        (byte-identical) on 2026-04-30 per Phase 5 D-discretion factor-extract.
        """
        from decimal import Decimal as _Decimal  # local-import: keeps --help fast (D-18)

        try:
            parsed = json.loads(raw, parse_float=_Decimal)
        except json.JSONDecodeError:
            return None

        def _walk(node: Any, path: list[str | int]) -> tuple[list[str | int], str] | None:
            if isinstance(node, _Decimal):
                return (path, str(node))
            if isinstance(node, dict):
                for k, v in node.items():
                    hit = _walk(v, [*path, k])
                    if hit is not None:
                        return hit
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    hit = _walk(v, [*path, i])
                    if hit is not None:
                        return hit
            return None

        return _walk(parsed, [])


    def make_decimal_type_envelope(
        loc: list[str | int],
        input_str: str,
    ) -> list[dict[str, Any]]:
        """Construct the 6-key Pydantic-shape envelope for a JSON-float rejection.

        Single source of truth for the WR-02 envelope shape. Mirrors the inline
        construction at scripts/amortize.py:196-213 + scripts/affordability.py:236-273
        (byte-identical) lifted on 2026-04-30 per Phase 5 D-discretion factor-extract.

        URL pattern: https://errors.pydantic.dev/{MAJOR.MINOR}/v/decimal_type
        with version computed at call time via lazy pydantic.VERSION import (preserves
        D-18 fast --help — pydantic must NOT load on the help path).

        Pinned by tests at:
        - tests/test_amortize.py::test_cli_rejects_float_principal
        - tests/test_affordability.py::test_cli_rejects_float_in_loan_amount
        - tests/test_arm.py::test_cli_rejects_float_principal (and 3 siblings) — Plan 05-04b
        - tests/test_cli_helpers.py (parametric coverage of this helper itself)
        """
        from pydantic import VERSION as _pydantic_version  # local-import: D-18

        _major_minor = ".".join(_pydantic_version.split(".")[:2])
        return [
            {
                "type": "decimal_type",
                "loc": loc,
                "msg": (
                    "Input should be a valid decimal — JSON string required "
                    "for money/rate fields per D-19 (JSON floats are rejected "
                    "at the boundary)"
                ),
                "input": input_str,
                "url": f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type",
                "ctx": {
                    "class": "Decimal",
                    "field_path": ".".join(str(p) for p in loc),
                },
            }
        ]
    ```

    Important: do NOT add `__init__.py` to scripts/. Project convention is that scripts/ is intentionally not a Python package (verified by tests/test_amortize.py:766-768 comment); consumers do `sys.path.insert(0, project_root)` in their `main()` body THEN `from scripts._cli_helpers import ...`.
  </action>
  <verify>
    <automated>python -c "import sys; sys.path.insert(0, '.'); from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File scripts/_cli_helpers.py exists with at least 70 lines
    - `grep -c 'def find_json_float_loc' scripts/_cli_helpers.py` returns 1
    - `grep -c 'def make_decimal_type_envelope' scripts/_cli_helpers.py` returns 1
    - `grep -v '^#' scripts/_cli_helpers.py | grep -c 'parse_float=_Decimal'` returns 1 (the JSON-float gate behavior; comment-stripped to avoid self-invalidating grep gate)
    - `grep -v '^#' scripts/_cli_helpers.py | grep -c '"type": "decimal_type"'` returns 1
    - `grep -v '^#' scripts/_cli_helpers.py | grep -c 'errors.pydantic.dev'` returns 1
    - `grep -v '^#' scripts/_cli_helpers.py | grep -c 'from pydantic import VERSION'` returns 1 (lazy import inside function body — verifies D-18 fast --help)
    - `test ! -e scripts/__init__.py` exits 0 (no __init__.py — scripts/ is NOT a package)
    - `mypy --strict scripts/_cli_helpers.py` exits 0
    - `ruff check scripts/_cli_helpers.py` exits 0
    - `ruff format --check scripts/_cli_helpers.py` exits 0
  </acceptance_criteria>
  <done>
    scripts/_cli_helpers.py exists with both helpers; mypy + ruff clean; importable when project root is on sys.path.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add tests/test_cli_helpers.py with parametric coverage of both helpers</name>
  <files>tests/test_cli_helpers.py</files>
  <read_first>
    - scripts/_cli_helpers.py (just created)
    - 05-RESEARCH.md §Q8 (lines 282-289) — test impact bullet list
    - tests/test_amortize.py (search for `_find_json_float_loc` direct usage if any)
  </read_first>
  <action>
    Create tests/test_cli_helpers.py with parametric coverage of both shared helpers. Cover:

    For `find_json_float_loc`:
    - Valid JSON with no floats → returns None
    - Single nested float → returns (loc, decimal-string)
    - Multiple floats → returns first (depth-first walk)
    - JSON arrays + nested objects → correct integer indices in loc
    - Invalid JSON (malformed) → returns None
    - JSON with float inside list inside dict → correct deep loc

    For `make_decimal_type_envelope`:
    - Returns list of length 1
    - Envelope has exactly the 6 keys: type, loc, msg, input, url, ctx
    - URL contains "errors.pydantic.dev" and ends with "/v/decimal_type"
    - URL version segment is MAJOR.MINOR (matches runtime pydantic.VERSION)
    - ctx contains class="Decimal" and field_path joined by dots
    - Round-trip with find_json_float_loc: feed JSON with float → call envelope → assert canonical shape

    File content:

    ```
    """Tests for scripts/_cli_helpers.py (Phase 5 D-discretion factor-extract).

    These tests pin the shared JSON-float gate + 6-key envelope shape that
    scripts/amortize.py, scripts/affordability.py, and scripts/arm_simulate.py
    all consume. The byte-identical pre-existing inline implementations at
    scripts/amortize.py:70-123 + scripts/affordability.py:70-123 are removed
    in Plan 05-04a Task 3 once these tests are passing.
    """

    from __future__ import annotations

    import json
    import sys
    from pathlib import Path

    import pytest


    # scripts/ is intentionally not a Python package; inject project root for imports.
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope  # noqa: E402


    # =========================================================================
    # find_json_float_loc
    # =========================================================================

    class TestFindJsonFloatLoc:
        def test_no_floats_returns_none(self) -> None:
            raw = json.dumps({"a": 1, "b": "0.05", "c": [1, 2, 3]})
            assert find_json_float_loc(raw) is None

        def test_single_float_at_top_level(self) -> None:
            raw = '{"principal": 400000.50}'
            hit = find_json_float_loc(raw)
            assert hit is not None
            loc, val = hit
            assert loc == ["principal"]
            assert val == "400000.5"

        def test_multiple_floats_returns_first_depth_first(self) -> None:
            # Dict iteration order is insertion-preserving (Python 3.7+);
            # the walk visits keys in order — "a" first, then "b".
            raw = '{"a": 1.5, "b": 2.5}'
            hit = find_json_float_loc(raw)
            assert hit is not None
            loc, _ = hit
            assert loc == ["a"]

        def test_float_in_nested_list_inside_dict(self) -> None:
            raw = '{"index_path": [{"period": 61, "value": 0.0525}]}'
            hit = find_json_float_loc(raw)
            assert hit is not None
            loc, val = hit
            assert loc == ["index_path", 0, "value"]
            assert val == "0.0525"

        def test_float_in_top_level_list(self) -> None:
            raw = "[1, 2.5, 3]"
            hit = find_json_float_loc(raw)
            assert hit is not None
            loc, val = hit
            assert loc == [1]
            assert val == "2.5"

        def test_invalid_json_returns_none(self) -> None:
            raw = '{"a": 1, "b":'  # truncated, malformed
            assert find_json_float_loc(raw) is None

        def test_empty_object_returns_none(self) -> None:
            assert find_json_float_loc("{}") is None

        def test_empty_array_returns_none(self) -> None:
            assert find_json_float_loc("[]") is None


    # =========================================================================
    # make_decimal_type_envelope
    # =========================================================================

    class TestMakeDecimalTypeEnvelope:
        def test_returns_list_of_one(self) -> None:
            env = make_decimal_type_envelope(["loan", "principal"], "400000.5")
            assert isinstance(env, list)
            assert len(env) == 1

        def test_envelope_has_exactly_six_keys(self) -> None:
            env = make_decimal_type_envelope(["loan", "principal"], "400000.5")
            err = env[0]
            assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}

        def test_envelope_type_is_decimal_type(self) -> None:
            env = make_decimal_type_envelope(["loan", "principal"], "400000.5")
            assert env[0]["type"] == "decimal_type"

        def test_envelope_loc_round_trips(self) -> None:
            loc = ["index_path", 0, "value"]
            env = make_decimal_type_envelope(loc, "0.0525")
            assert env[0]["loc"] == loc

        def test_envelope_input_round_trips(self) -> None:
            env = make_decimal_type_envelope(["principal"], "12345.67")
            assert env[0]["input"] == "12345.67"

        def test_envelope_url_pattern(self) -> None:
            env = make_decimal_type_envelope(["principal"], "1.5")
            url = env[0]["url"]
            assert url.startswith("https://errors.pydantic.dev/")
            assert url.endswith("/v/decimal_type")

        def test_envelope_url_version_matches_runtime_pydantic(self) -> None:
            from pydantic import VERSION as pv
            major_minor = ".".join(pv.split(".")[:2])
            env = make_decimal_type_envelope(["x"], "1.5")
            assert f"errors.pydantic.dev/{major_minor}/" in env[0]["url"]

        def test_envelope_ctx_class_decimal(self) -> None:
            env = make_decimal_type_envelope(["x"], "1.5")
            assert env[0]["ctx"]["class"] == "Decimal"

        def test_envelope_ctx_field_path_dot_joined(self) -> None:
            env = make_decimal_type_envelope(["loan", "principal"], "1.5")
            assert env[0]["ctx"]["field_path"] == "loan.principal"

        def test_envelope_ctx_field_path_with_int_index(self) -> None:
            env = make_decimal_type_envelope(["index_path", 0, "value"], "0.05")
            assert env[0]["ctx"]["field_path"] == "index_path.0.value"


    # =========================================================================
    # Round-trip
    # =========================================================================

    def test_round_trip_finds_float_then_emits_envelope() -> None:
        """Integration: parse JSON with a float, locate it, emit canonical envelope."""
        raw = '{"loan": {"principal": 400000.5}, "rate": "0.05"}'
        hit = find_json_float_loc(raw)
        assert hit is not None
        loc, val = hit
        env = make_decimal_type_envelope(loc, val)
        err = env[0]
        assert err["loc"] == ["loan", "principal"]
        assert err["input"] == "400000.5"
        assert err["ctx"]["field_path"] == "loan.principal"
    ```

    Notes:
    - Tests are class-grouped for clarity but each is also a free function test (`test_round_trip_finds_float_then_emits_envelope`).
    - The sys.path injection at module top mirrors the pattern in tests/test_amortize.py + tests/test_affordability.py for subprocess-invoked CLI tests.
  </action>
  <verify>
    <automated>pytest tests/test_cli_helpers.py -xvs</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_cli_helpers.py -x` exits 0 with all tests passed
    - `grep -c 'def test_' tests/test_cli_helpers.py` returns at least 18 (8 find_json_float_loc + 10 make_decimal_type_envelope)
    - `mypy --strict tests/test_cli_helpers.py` exits 0
    - `ruff check tests/test_cli_helpers.py` exits 0
    - `ruff format --check tests/test_cli_helpers.py` exits 0
  </acceptance_criteria>
  <done>
    tests/test_cli_helpers.py runs green; both helpers covered parametrically.
  </done>
</task>

<task type="auto">
  <name>Task 3: Refactor scripts/amortize.py + scripts/affordability.py to import from scripts._cli_helpers; verify Phase 3 + Phase 4 byte-equivalent</name>
  <files>scripts/amortize.py, scripts/affordability.py</files>
  <read_first>
    - scripts/amortize.py:70-123 (inline _find_json_float_loc) — DELETE
    - scripts/amortize.py:196-213 (inline envelope construction) — REPLACE with helper call
    - scripts/affordability.py:70-123 (inline _find_json_float_loc) — DELETE
    - scripts/affordability.py:236-274 (inline envelope construction) — REPLACE with helper call
    - 05-RESEARCH.md §Q8 "Phase 4 + Phase 3 update" subsection (line 281) — both files swap to imports
  </read_first>
  <action>
    Refactor BOTH existing CLIs to use the shared helpers. The behavior is byte-equivalent — only the location of the helper code changes. Plan-checker note from RESEARCH §Recommended Plan Structure line 480 makes this verification mandatory.

    **For each of scripts/amortize.py and scripts/affordability.py, perform exactly two edits:**

    **Edit A: Delete the inline `_find_json_float_loc` def.** Locate the function (around lines 70-123 in both files; ~50 lines including the docstring + nested `_walk` helper). Use the Edit tool to remove the entire function definition. After this edit, the file no longer contains `def _find_json_float_loc`.

    **Edit B: Replace the inline envelope construction with helper calls.** Locate the block in `main()` that:
    1. Calls `_find_json_float_loc(raw)` to detect a float
    2. Lazy-imports `from pydantic import VERSION as _pydantic_version`
    3. Constructs the 6-key envelope dict inline
    4. Prints it to stderr and returns 2

    Replace this entire block with:

    ```
    float_hit = find_json_float_loc(raw)
    if float_hit is not None:
        loc, input_str = float_hit
        envelope = make_decimal_type_envelope(loc, input_str)
        print(json.dumps(envelope), file=sys.stderr)
        return 2
    ```

    **Then add the helper imports.** Inside `main()` (AFTER the sys.path injection block, BEFORE the existing lazy-import block from `lib.X`), add:

    ```
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope
    ```

    The position MATTERS: must be AFTER `sys.path.insert(0, _project_root)` so the import resolves; must be BEFORE the `lib.X` import block so the helper is available when the gate runs.

    **Specifically for scripts/affordability.py:** the existing `MissingCountyDataError` exception handler may use a separate manual envelope-construction pattern (the Pydantic `MissingCountyDataError` is NOT a ValidationError; it gets a custom envelope via the same shape). Reuse `make_decimal_type_envelope` IF its loc/input semantics fit; if NOT (the MissingCountyDataError envelope uses `type="value_error"` not `"decimal_type"`), keep that block inline. Only the JSON-float gate + envelope block is being factored — the catch-all envelope for MissingCountyDataError stays put unless trivially refactorable. Inspect lib/affordability.py + scripts/affordability.py to determine.

    **Verify zero regression.** After each edit pair, run:
    - `pytest tests/test_amortize.py -x` (must show same pass count as Phase 3 closure)
    - `pytest tests/test_affordability.py -x` (must show 379 + 4)

    If ANY pre-existing test fails, STOP, revert, and investigate. The whole point of factoring out byte-identical code is zero behavior change.
  </action>
  <verify>
    <automated>pytest tests/test_amortize.py tests/test_affordability.py tests/test_cli_helpers.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def _find_json_float_loc' scripts/amortize.py` returns 0 (function removed)
    - `grep -c 'def _find_json_float_loc' scripts/affordability.py` returns 0 (function removed)
    - `grep -c 'from scripts._cli_helpers import' scripts/amortize.py` returns 1
    - `grep -c 'from scripts._cli_helpers import' scripts/affordability.py` returns 1
    - `grep -v '^#' scripts/amortize.py | grep -c 'find_json_float_loc(raw)'` returns 1 (the call site, not the def; comment-stripped)
    - `grep -v '^#' scripts/affordability.py | grep -c 'find_json_float_loc(raw)'` returns 1
    - `grep -v '^#' scripts/amortize.py | grep -c 'make_decimal_type_envelope('` returns 1
    - `grep -v '^#' scripts/affordability.py | grep -c 'make_decimal_type_envelope('` returns 1
    - `pytest tests/test_amortize.py -q` shows same pass count as Phase 3 closure (no regression)
    - `pytest tests/test_affordability.py -q` shows passed >= 379 (Phase 4 baseline preserved)
    - `mypy --strict scripts/amortize.py scripts/affordability.py` exits 0
    - `ruff check scripts/amortize.py scripts/affordability.py` exits 0
    - `ruff format --check scripts/amortize.py scripts/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    Both Phase 3 + Phase 4 CLIs refactored to use shared helpers; zero regression to existing test suites; mypy + ruff clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User-supplied JSON → scripts/amortize.py + scripts/affordability.py float-gate | Existing untrusted input crosses here; refactor must preserve gate semantics byte-identical |
| scripts._cli_helpers shared module | Two CLIs (Phase 3, Phase 4) consume the same helper; semantic drift would corrupt both. Plan 05-04b adds a third consumer (arm_simulate.py) |
| Phase 3 + Phase 4 test suite baseline | Refactor MUST preserve byte-equivalent pass counts |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-01 (helper layer) | Tampering (JSON-float coercion bypass) | scripts/_cli_helpers.find_json_float_loc | mitigate | tests/test_cli_helpers.py covers the helper independently with >= 18 parametric tests; existing tests/test_amortize.py + tests/test_affordability.py float-gate tests pass byte-equivalent after Task 3 |
| T-05-23 | Tampering (envelope shape divergence across CLIs) | scripts/_cli_helpers.make_decimal_type_envelope | mitigate | Single source of truth; tests/test_cli_helpers.py pins the 6-key shape; Plan 05-04b will add tests/test_arm.py assertions |
| T-05-25 | Repudiation (Phase 3/4 regression after factor) | scripts/amortize.py + scripts/affordability.py refactor | mitigate | Task 3 mandates BYTE-EQUIVALENT pass count for both pre-existing CLIs; verify command runs both suites and exits non-zero on regression |
</threat_model>

<verification>
- scripts/_cli_helpers.py exists with both helpers
- scripts/amortize.py + scripts/affordability.py both refactored (inline helpers removed; imports added)
- 18 NEW tests in tests/test_cli_helpers.py all pass
- Phase 3 + Phase 4 test suites BYTE-EQUIVALENT (factor-extract verified semantically null)
- mypy + ruff clean across 4 files (scripts/_cli_helpers.py + scripts/amortize.py + scripts/affordability.py + tests/test_cli_helpers.py)
</verification>

<success_criteria>
- scripts/_cli_helpers.py shipped with 2 helpers + 18 parametric tests
- scripts/amortize.py + scripts/affordability.py refactored to import shared helpers; zero regression
- Plan 05-04b can now build scripts/arm_simulate.py against scripts._cli_helpers (its dependency in depends_on)
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-04a-SUMMARY.md` documenting:
- scripts/_cli_helpers.py shipped with 2 helpers + 18 tests
- scripts/amortize.py + scripts/affordability.py refactored (helpers removed, imports added)
- Phase 3 + Phase 4 byte-equivalent verification
- mypy + ruff status across 4 files
- Plan 05-04b unblocked (can now consume scripts._cli_helpers for scripts/arm_simulate.py)
</output>
