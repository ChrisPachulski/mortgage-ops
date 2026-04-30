---
phase: 05
plan: 04b
type: execute
wave: 4
depends_on:
  - "05-00"
  - "05-01"
  - "05-02"
  - "05-03"
  - "05-04a"
files_modified:
  - scripts/arm_simulate.py
  - tests/test_arm.py
autonomous: true
requirements:
  - ARM-08
tags:
  - phase-05
  - arm-modeling
  - cli
  - arm-08
must_haves:
  truths:
    - "scripts/arm_simulate.py exists at project root mirroring scripts/affordability.py + scripts/amortize.py exactly per D-07"
    - "scripts/arm_simulate.py uses --input <path> (no stdin) per D-07 / Phase 3 D-18 / Phase 4 D-13"
    - "scripts/arm_simulate.py lazy-imports lib.arm + lib.amortize + numpy_financial AFTER argparse (verified by test_cli_help_does_not_import_lib_arm)"
    - "scripts/arm_simulate.py JSON-float pre-validation gate covers loan.principal, assumed_index_rate, index_path[].value, and arm_terms.floor_rate per D-07; emits 6-key envelope on stderr (consumed from scripts._cli_helpers shipped by Plan 05-04a)"
    - "scripts/arm_simulate.py emits ARMSchedule.model_dump_json(indent=2) on stdout for happy path; returns exit code 0"
    - "scripts/arm_simulate.py emits Pydantic ValidationError envelope on stderr (e.json()) for boundary failures; returns exit code 2"
    - "Phase 3 + Phase 4 + Plan 05-04a test suites still pass byte-equivalent"
    - "All 8 ARM-08 Wave 0 stubs flip from xfail to passing (test_cli_smoke_subprocess_round_trip, test_cli_help_does_not_import_lib_arm, 4x test_cli_rejects_float_*, test_cli_error_envelope_uniformity, test_cli_misaligned_index_path_period_rejected)"
  artifacts:
    - path: "scripts/arm_simulate.py"
      provides: "ARM CLI mirroring scripts/affordability.py per D-07"
      contains: "def main"
      min_lines: 70
  key_links:
    - from: "scripts/arm_simulate.py"
      to: "lib.arm.build_arm_schedule"
      via: "lazy-import after argparse + sys.path injection"
      pattern: "from lib.arm import"
    - from: "scripts/arm_simulate.py"
      to: "scripts._cli_helpers.find_json_float_loc"
      via: "JSON-float pre-validation gate"
      pattern: "from scripts._cli_helpers import"
    - from: "tests/test_arm.py 8 ARM-08 flips"
      to: "scripts/arm_simulate.py"
      via: "subprocess invocation via SCRIPT_PATH (D-17 portability)"
      pattern: "subprocess.run.*SCRIPT_PATH"
---

<objective>
Plan 05-04b (split half 2 of 2 per checker BLOCKER I-003): ship `scripts/arm_simulate.py` (ARM CLI per D-07/ARM-08) consuming the shared `scripts._cli_helpers` module that Plan 05-04a factored out. Flip 8 ARM-08 Wave-0 stubs in tests/test_arm.py to passing tests via subprocess invocation.

Closes ARM-08 ("`scripts/arm_simulate.py` JSON-in/JSON-out CLI"). Plan-checker note from RESEARCH §"Recommended Plan Structure" line 480: this plan MUST verify Phase 3 + Phase 4 + Plan 05-04a test suites pass byte-equivalent.

Owns threat T-05-01 (CLI invocation of the gate — see threat_model below) and T-05-24 (lib.arm not imported on --help path) and T-05-26 (sys.path injection ordering).

Purpose: Two deliverables in one plan because they are tightly coupled:
1. **scripts/arm_simulate.py** — new CLI consuming scripts._cli_helpers (shipped by Plan 05-04a)
2. **8 ARM-08 stub flips in tests/test_arm.py** — subprocess-invocation tests pinning CLI behavior

Splitting these across separate plans would force the second plan to test a not-yet-shipped CLI — they belong together.

Output: 1 new file (scripts/arm_simulate.py) + 1 file modified (tests/test_arm.py); 8 ARM-08 stubs flipped to passing.
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
@scripts/_cli_helpers.py
@lib/arm.py

<interfaces>
Phase 3/4 CLI shape (scripts/affordability.py shape after Plan 05-04a refactor — Phase 5 mirrors per D-07):

```python
def main() -> int:
    parser = argparse.ArgumentParser(prog="...", description="...", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()

    # Inject project root into sys.path so `from lib.X import ...` works
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # Lazy-import after argparse (D-18 fast --help)
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope
    from lib.X import Y, Z
    from pydantic import ValidationError

    raw = args.input.read_text()

    # JSON-float pre-validation gate
    float_hit = find_json_float_loc(raw)
    if float_hit is not None:
        loc, input_str = float_hit
        envelope = make_decimal_type_envelope(loc, input_str)
        print(json.dumps(envelope), file=sys.stderr)
        return 2

    # Pydantic validation
    try:
        request = X.model_validate_json(raw)
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2

    # Happy path
    response = Y(request)
    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Phase 5 entry surface (lib/arm.py after Wave 3 — for the import statements):

```python
from lib.arm import ARMRequest, build_arm_schedule
# ARMRequest carries: loan, arm_terms, assumed_index_rate, index_path
# build_arm_schedule(req: ARMRequest) -> ARMSchedule
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create scripts/arm_simulate.py mirroring scripts/affordability.py per D-07</name>
  <files>scripts/arm_simulate.py</files>
  <read_first>
    - scripts/affordability.py (full file after Plan 05-04a refactor) — exact mirror template
    - scripts/amortize.py (full file after Plan 05-04a refactor) — second pattern source
    - scripts/_cli_helpers.py (shipped by Plan 05-04a) — for the import statement
    - 05-CONTEXT.md D-07 — locked CLI behavior (--input only, lazy-import, 6-key envelope, JSON-float gate, subprocess-invocation in tests)
    - 05-PATTERNS.md "scripts/arm_simulate.py" section (lines 233-355) — full Pattern 1, 2, 3 application
    - lib/arm.py (after Wave 3) — for the ARMRequest + build_arm_schedule + ARMSchedule entry surface
  </read_first>
  <action>
    Create scripts/arm_simulate.py at project root. Mirror scripts/affordability.py SHAPE EXACTLY per D-07 — the only changes are (a) prog name + description text, (b) the lib import (`lib.arm` instead of `lib.affordability`), (c) the request type (`ARMRequest`), (d) the engine entry-point (`build_arm_schedule`), (e) the response type (`ARMSchedule`).

    File content (literal Python):

    ```
    """ARM simulator CLI: JSON-in / JSON-out wrapper around lib.arm.build_arm_schedule.

    Mirrors scripts/amortize.py + scripts/affordability.py per CONTEXT.md D-07
    inheritance from Phase 3 D-17/D-18/D-19 + Phase 4 D-13:

    - Lives at project root (Phase 5); Phase 10 relocates to
      .claude/skills/mortgage-ops/scripts/arm_simulate.py per PROJECT.md decision #8.
    - `--input <path>` only (no stdin in v1).
    - Lazy-imports lib.arm + lib.amortize + numpy_financial AFTER argparse so
      `--help` is fast (D-18 / Phase 4 D-13 inherited).
    - JSON-float pre-validation gate covers loan.principal, assumed_index_rate,
      index_path[].value, arm_terms.floor_rate (and any other money/rate field).
      Float gate emits 6-key Pydantic envelope on stderr (Phase 3 WR-02 closure).
      Helper sourced from scripts._cli_helpers (factored out by Plan 05-04a).
    - Pydantic ValidationError surfaces e.json() on stderr — also 6-key shape.
    - Happy path: prints ARMSchedule.model_dump_json(indent=2) on stdout, exit 0.
    - Boundary failure: exit 2 with envelope on stderr.

    Test invocation pattern (tests/test_arm.py): subprocess via SCRIPT_PATH constant,
    NEVER `from scripts.arm_simulate import main` (Phase 3 D-17 portability —
    Phase 10 relocates the script).
    """

    from __future__ import annotations

    import argparse
    import json
    import sys
    from pathlib import Path


    def main() -> int:
        parser = argparse.ArgumentParser(
            prog="arm_simulate",
            description=(
                "Build an ARM amortization schedule (5/1, 7/1, 10/1, 5/6, "
                "or any (initial_period_months, reset_period_months) combo). "
                "JSON-in / JSON-out per Phase 5 D-07."
            ),
            epilog=(
                "Input JSON shape (D-01 + D-06):\n"
                "  {\n"
                '    "loan": {Phase 1 Loan: principal/annual_rate/term_months/'
                "origination_date/loan_type='arm'},\n"
                '    "arm_terms": {ARMTerms: 8 fields + optional note_rate},\n'
                '    "assumed_index_rate": "0.0500",\n'
                '    "index_path": [{"period": 61, "value": "0.0525"}, ...]\n'
                "  }\n"
                "All money/rate fields MUST be JSON strings (D-19; never JSON floats).\n"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--input",
            required=True,
            type=Path,
            help="Path to JSON file containing the ARM request.",
        )
        args = parser.parse_args()

        # When invoked as `python scripts/arm_simulate.py ...`, Python puts
        # `scripts/` on sys.path, NOT the project root, so `from lib.arm
        # import ...` fails with ModuleNotFoundError. Insert the project root.
        _project_root = str(Path(__file__).resolve().parent.parent)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)

        # Lazy-import per D-18 / D-13: heavy deps NOT loaded on the --help fast path.
        from scripts._cli_helpers import (  # noqa: E402
            find_json_float_loc,
            make_decimal_type_envelope,
        )
        from lib.arm import ARMRequest, build_arm_schedule  # noqa: E402
        from pydantic import ValidationError  # noqa: E402

        raw = args.input.read_text()

        # JSON-float pre-validation gate (D-19 + WR-02 closure).
        # Phase 5 D-07 explicitly extends this to ARM money/rate fields:
        # loan.principal, assumed_index_rate, index_path[].value, arm_terms.floor_rate.
        # The walker is generic — finds the FIRST JSON float anywhere in the tree.
        float_hit = find_json_float_loc(raw)
        if float_hit is not None:
            loc, input_str = float_hit
            envelope = make_decimal_type_envelope(loc, input_str)
            print(json.dumps(envelope), file=sys.stderr)
            return 2

        # Pydantic boundary validation. Catches:
        # - Missing required fields (e.g., floor_rate per D-02)
        # - Misaligned index_path periods (model_validator from Plan 05-02)
        # - Type errors (e.g., string where int expected)
        try:
            request = ARMRequest.model_validate_json(raw)
        except ValidationError as e:
            print(e.json(), file=sys.stderr)
            return 2

        # Happy path: build the ARM schedule and emit JSON to stdout.
        schedule = build_arm_schedule(request)
        print(schedule.model_dump_json(indent=2))
        return 0


    if __name__ == "__main__":
        sys.exit(main())
    ```

    Notes:
    - The script has NO MissingCountyDataError-class handling (Phase 5 has no domain-specific exception classes; only Pydantic + the float-gate produce 6-key envelopes).
    - The `--help` fast path is preserved by lazy-importing EVERYTHING heavyweight (lib.arm pulls in lib.amortize + numpy_financial transitively) AFTER argparse.parse_args().
    - The `noqa: E402` markers on the lazy imports tell ruff "yes, these imports are intentionally not at the top of the file."
  </action>
  <verify>
    <automated>python scripts/arm_simulate.py --help</automated>
  </verify>
  <acceptance_criteria>
    - File scripts/arm_simulate.py exists with at least 70 lines
    - `grep -c 'def main' scripts/arm_simulate.py` returns 1
    - `grep -c 'argparse.ArgumentParser' scripts/arm_simulate.py` returns 1
    - `grep -c 'prog="arm_simulate"' scripts/arm_simulate.py` returns 1
    - `grep -c 'required=True' scripts/arm_simulate.py` returns 1 (--input required per D-07)
    - `grep -c 'sys.path.insert(0, _project_root)' scripts/arm_simulate.py` returns 1
    - `grep -c 'from scripts._cli_helpers import' scripts/arm_simulate.py` returns 1 (lazy-imported)
    - `grep -c 'from lib.arm import' scripts/arm_simulate.py` returns 1 (lazy-imported AFTER argparse)
    - `grep -v '^#' scripts/arm_simulate.py | grep -c 'find_json_float_loc(raw)'` returns 1 (comment-stripped)
    - `grep -v '^#' scripts/arm_simulate.py | grep -c 'make_decimal_type_envelope('` returns 1
    - `grep -v '^#' scripts/arm_simulate.py | grep -c 'ARMRequest.model_validate_json'` returns 1
    - `grep -v '^#' scripts/arm_simulate.py | grep -c 'build_arm_schedule(request)'` returns 1
    - `grep -v '^#' scripts/arm_simulate.py | grep -c 'schedule.model_dump_json(indent=2)'` returns 1
    - `grep -v '^#' scripts/arm_simulate.py | grep -c 'return 2'` returns at least 2 (float gate + ValidationError)
    - `grep -v '^#' scripts/arm_simulate.py | grep -c 'return 0'` returns 1
    - `python scripts/arm_simulate.py --help` exits 0 and prints help text including "arm_simulate"
    - `mypy --strict scripts/arm_simulate.py` exits 0
    - `ruff check scripts/arm_simulate.py` exits 0
    - `ruff format --check scripts/arm_simulate.py` exits 0
  </acceptance_criteria>
  <done>
    scripts/arm_simulate.py exists with the D-07 mirror shape; --help works; mypy + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip 8 ARM-08 CLI Wave-0 stubs in tests/test_arm.py</name>
  <files>tests/test_arm.py</files>
  <read_first>
    - tests/test_arm.py (Wave 3 state: 22 xfails)
    - tests/test_amortize.py:722-1067 (CLI test patterns for subprocess + envelope + lazy-import) — full reference for all 8 patterns
    - tests/test_affordability.py:685-1280 (same patterns; in particular test_AFFD_08_cli_smoke + test_cli_help_does_not_import_lib_affordability + test_cli_rejects_float_*)
    - 05-PATTERNS.md "tests/test_arm.py" Patterns 1, 2, 3, 4 (lines 433-602) — full skeletons for each test type
    - 05-VALIDATION.md ARM-08 rows
  </read_first>
  <action>
    Flip exactly 8 ARM-08 stubs to passing tests. Each test invokes scripts/arm_simulate.py via subprocess (NEVER direct import per D-17 portability).

    Stubs to flip:
    1. test_cli_smoke_subprocess_round_trip
    2. test_cli_help_does_not_import_lib_arm
    3. test_cli_rejects_float_principal
    4. test_cli_rejects_float_assumed_index_rate
    5. test_cli_rejects_float_index_path_value
    6. test_cli_rejects_float_floor_rate
    7. test_cli_error_envelope_uniformity
    8. test_cli_misaligned_index_path_period_rejected

    For each, REMOVE the `@pytest.mark.xfail(...)` decorator AND replace the body. Note that `test_cli_smoke_subprocess_round_trip` requires a fixture that ships in Wave 6 (Plan 05-06) — for now, have this test build its request inline using the `_make_5_1_arm_request(...)` helper from Wave 3, dump it to JSON, invoke the CLI, parse stdout, and assert the response is a valid ARMSchedule (don't assert specific dollar values yet — Wave 6 fixture flips will pin those).

    **Flip 1: test_cli_smoke_subprocess_round_trip**

    Remove decorator. Body:

    ```
    """ARM-08: CLI subprocess round-trip — write JSON, invoke, parse stdout.

    Wave 4 ships the basic round-trip (request/response shape correct).
    Wave 6 (Plan 05-06) replaces this with a fixture-based assertion that
    pins specific dollar values (arm_5_1_payment_jump_at_61.json).
    """
    import subprocess
    from decimal import Decimal
    req = _make_5_1_arm_request()
    request_path = tmp_path / "input.json"
    # ARMRequest.model_dump_json gives JSON-strings for Decimal fields (CLAUDE.md money discipline).
    request_path.write_text(req.model_dump_json())
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    # Smoke shape assertions
    assert "loan" in out
    assert "arm_terms" in out
    assert "payments" in out
    assert "reset_events" in out
    assert "total_interest" in out
    assert "final_payment_adjusted" in out
    assert len(out["payments"]) == 360  # 30yr 5/1 ARM
    # Continuous numbering invariant
    assert out["payments"][0]["period"] == 1
    assert out["payments"][-1]["period"] == 360
    assert out["payments"][-1]["balance"] == "0.00"
    # 5/1 ARM 30yr produces 25 reset events
    assert len(out["reset_events"]) == 25
    assert out["reset_events"][0]["period"] == 61
    # I-005: pin the LAST reset trigger as well (catches off-by-one in the
    # reset-trigger generator at the END of the schedule).
    assert out["reset_events"][-1]["period"] == 349, (
        f"expected last reset trigger at period 349, got {out['reset_events'][-1]['period']}"
    )
    ```

    **Flip 2: test_cli_help_does_not_import_lib_arm**

    Remove decorator. Body (lift the inline harness pattern from tests/test_affordability.py:1194-1242 with name swaps):

    ```
    """ARM-08 + D-18: --help fast path. Must NOT trigger lib.arm or lib.amortize
    or numpy_financial imports.
    """
    import subprocess
    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_arm_simulate', SCRIPT)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "saved_argv = sys.argv\n"
        "sys.argv = [SCRIPT, '--help']\n"
        "exit_code = None\n"
        "try:\n"
        "    try:\n"
        "        module.main()\n"
        "    except SystemExit as exc:\n"
        "        exit_code = exc.code\n"
        "finally:\n"
        "    sys.argv = saved_argv\n"
        "result = {\n"
        "    'help_exit_code': exit_code,\n"
        "    'lib_arm_imported': 'lib.arm' in sys.modules,\n"
        "    'lib_amortize_imported': 'lib.amortize' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
        "}\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", inline],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["help_exit_code"] == 0
    assert payload["lib_arm_imported"] is False
    assert payload["lib_amortize_imported"] is False
    assert payload["numpy_financial_imported"] is False
    ```

    **Flip 3: test_cli_rejects_float_principal**

    Remove decorator. Body:

    ```
    """ARM-08 + D-19/WR-02: JSON-float in loan.principal rejected with 6-key envelope."""
    import subprocess
    bad = tmp_path / "float_principal.json"
    bad.write_text(
        '{"loan": {"principal": 400000.00, "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", "index_path": []}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["loan", "principal"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"]["class"] == "Decimal"
    ```

    **Flip 4: test_cli_rejects_float_assumed_index_rate**

    Remove decorator. Body:

    ```
    """ARM-08 + D-19: JSON-float in assumed_index_rate rejected with 6-key envelope."""
    import subprocess
    bad = tmp_path / "float_index.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": 0.050000, "index_path": []}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert err["loc"] == ["assumed_index_rate"]
    assert err["type"] == "decimal_type"
    ```

    **Flip 5: test_cli_rejects_float_index_path_value**

    Remove decorator. Body:

    ```
    """ARM-08 + D-19: JSON-float deep in index_path[0].value rejected with correct loc."""
    import subprocess
    bad = tmp_path / "float_index_path.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", '
        '"index_path": [{"period": 61, "value": 0.052500}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert err["loc"] == ["index_path", 0, "value"]
    assert err["ctx"]["field_path"] == "index_path.0.value"
    ```

    **Flip 6: test_cli_rejects_float_floor_rate**

    Remove decorator. Body:

    ```
    """ARM-08 + D-19: JSON-float in arm_terms.floor_rate rejected."""
    import subprocess
    bad = tmp_path / "float_floor.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": 0.030000, "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", "index_path": []}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert err["loc"] == ["arm_terms", "floor_rate"]
    ```

    **Flip 7: test_cli_error_envelope_uniformity**

    Remove decorator. Body:

    ```
    """ARM-08 + D-19/WR-02: float-gate envelope + Pydantic ValidationError envelope
    have IDENTICAL 6-key shape (mirror tests/test_amortize.py:996+).
    """
    import subprocess
    # Case 1: float-gate envelope (loan.principal as a JSON float)
    bad_float = tmp_path / "float.json"
    bad_float.write_text(
        '{"loan": {"principal": 400000.00, "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", "index_path": []}'
    )
    res1 = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad_float)],
        capture_output=True, text=True, check=False,
    )
    err1 = json.loads(res1.stderr)[0]

    # Case 2: Pydantic ValidationError envelope (missing floor_rate)
    bad_pydantic = tmp_path / "missing_floor.json"
    bad_pydantic.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", "index_path": []}'
    )
    res2 = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad_pydantic)],
        capture_output=True, text=True, check=False,
    )
    err2 = json.loads(res2.stderr)[0]

    # Both must have the same 6 top-level keys
    assert set(err1.keys()) == set(err2.keys())
    assert {"type", "loc", "msg", "input", "url", "ctx"} <= set(err1.keys())
    # Both URLs are Pydantic-format
    assert err1["url"].startswith("https://errors.pydantic.dev/")
    assert err2["url"].startswith("https://errors.pydantic.dev/")
    # Same exit code
    assert res1.returncode == 2
    assert res2.returncode == 2
    ```

    **Flip 8: test_cli_misaligned_index_path_period_rejected**

    Remove decorator. Body:

    ```
    """ARM-08 + D-01: misaligned index_path period surfaces ARMRequest model_validator
    error as the 6-key Pydantic ValidationError envelope.
    """
    import subprocess
    bad = tmp_path / "misaligned.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", '
        '"index_path": [{"period": 62, "value": "0.052500"}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    # Pydantic surfaces the model_validator ValueError; one of the errors mentions period 62
    assert any("62" in str(e.get("msg", "")) for e in errors)
    # Each error has the 6-key shape
    for e in errors:
        assert {"type", "loc", "msg", "input", "url", "ctx"} <= set(e.keys())
    ```

    Notes:
    - All 8 tests use subprocess invocation via SCRIPT_PATH (the constant defined at module top in Wave 0).
    - The malformed-JSON fixtures are embedded inline rather than living in tests/fixtures/arm/. Fixture-based tests (Wave 6) ship the canonical fixtures.
    - `test_cli_smoke_subprocess_round_trip` uses `_make_5_1_arm_request(...)` from Wave 3 to construct a valid request inline; Wave 6 replaces the body with a fixture-loader-based assertion.
  </action>
  <verify>
    <automated>pytest tests/test_arm.py -k "test_cli_smoke_subprocess_round_trip or test_cli_help_does_not_import_lib_arm or test_cli_rejects_float_principal or test_cli_rejects_float_assumed_index_rate or test_cli_rejects_float_index_path_value or test_cli_rejects_float_floor_rate or test_cli_error_envelope_uniformity or test_cli_misaligned_index_path_period_rejected" -xvs</automated>
  </verify>
  <acceptance_criteria>
    - All 8 ARM-08 tests pass via the verify command (8 passed, 0 xfailed in that filter)
    - `grep -c '@pytest.mark.xfail' tests/test_arm.py` returns 14 (22 - 8 = 14)
    - test_cli_smoke_subprocess_round_trip body asserts `out['reset_events'][-1]['period'] == 349` (I-005: pin the LAST trigger as well as the FIRST)
    - `mypy --strict tests/test_arm.py` exits 0
    - `ruff check tests/test_arm.py` exits 0
    - `ruff format --check tests/test_arm.py` exits 0
  </acceptance_criteria>
  <done>
    All 8 ARM-08 stubs flipped to passing; xfail count drops from 22 to 14.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero regression to Phase 3 + Phase 4 + Plan 05-04a + Phase 5 baselines</name>
  <files>(verification only)</files>
  <read_first>
    - 05-VALIDATION.md "Phase gate" row
    - Plan 05-03 SUMMARY for prior baseline (392 passed + 4 skipped + 22 xfailed)
    - Plan 05-04a SUMMARY for the +18 new test_cli_helpers tests
  </read_first>
  <action>
    Run the full pytest suite. Expected counts after this plan:
    - Plan 05-03 baseline: 392 passed + 4 skipped + 22 xfailed
    - Plan 05-04a delta: +18 NEW tests in tests/test_cli_helpers.py → 410 passed
    - Plan 05-04b delta: +8 ARM-08 stubs flipped → 418 passed, 14 xfailed
    - Phase 3 + Phase 4 baselines preserved byte-equivalent
    - Final expected: 418 passed + 4 skipped + 14 xfailed + 0 failed + 0 errored

    Run: `pytest -q`

    Run mypy + ruff on every Phase 5 file Wave 0..4 has touched:
    - `mypy --strict lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py`
    - `ruff check ...` (same file list)
    - `ruff format --check ...` (same file list)

    All MUST be clean. PARTICULAR FOCUS on Phase 3/4 byte-equivalence: tests/test_amortize.py + tests/test_affordability.py pass counts MUST equal their pre-factor baseline exactly.

    Sanity check: the `--help` fast path on the new CLI:
    - `python scripts/arm_simulate.py --help` exits 0 in well under 1 second (lazy imports work)

    And a quick happy-path subprocess invocation using the canonical 5/1 ARM ARMRequest from Wave 3 helper:
    - `python -c "import json; from datetime import date; from decimal import Decimal; from lib.arm import ARMRequest, ARMTerms; from lib.models import Loan; req=ARMRequest(loan=Loan(principal=Decimal('400000.00'), annual_rate=Decimal('0.050000'), term_months=360, origination_date=date(2026,1,1), loan_type='arm'), arm_terms=ARMTerms(initial_period_months=60, reset_period_months=12, initial_cap_bps=500, periodic_cap_bps=200, lifetime_cap_bps=500, floor_rate=Decimal('0.030000'), margin_bps=250, index_series_id='MORTGAGE30US'), assumed_index_rate=Decimal('0.050000')); open('/tmp/arm_test.json','w').write(req.model_dump_json())"` → write request
    - `python scripts/arm_simulate.py --input /tmp/arm_test.json | python -c "import sys, json; d=json.load(sys.stdin); print(f\"payments={len(d['payments'])} resets={len(d['reset_events'])} final_bal={d['payments'][-1]['balance']}\")"` → assert output `payments=360 resets=25 final_bal=0.00`
  </action>
  <verify>
    <automated>pytest -q &amp;&amp; mypy --strict lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py &amp;&amp; ruff check lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q` final summary shows passed >= 418
    - `pytest -q` final summary shows xfailed = 14
    - `pytest -q` final summary shows skipped >= 4
    - `pytest -q` final summary shows failed = 0
    - `pytest -q` final summary shows errors = 0
    - `pytest tests/test_amortize.py -q` shows BYTE-EQUIVALENT pass count to Phase 3 closure
    - `pytest tests/test_affordability.py -q` shows BYTE-EQUIVALENT pass count to Phase 4 closure (379 + 4)
    - `mypy --strict` across all 11 files exits 0
    - `ruff check` across all 11 files exits 0
    - `ruff format --check` across all 11 files exits 0
    - `python scripts/arm_simulate.py --help` exits 0
    - The subprocess happy-path sanity check produces `payments=360 resets=25 final_bal=0.00`
  </acceptance_criteria>
  <done>
    Phase 3 + Phase 4 + Plan 05-04a byte-equivalent; ARM-08 closed; all CLI tests passing; mypy + ruff clean across 11 files.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User-supplied JSON → scripts/arm_simulate.py | Untrusted input crosses here; float-gate + Pydantic validation are the two-layer defense |
| --help fast path | D-18 contract: lib.arm + numpy_financial NOT loaded on help path |
| sys.path injection in main() | Must precede every `from scripts._cli_helpers import` and `from lib.arm import` line |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-01 (CLI layer) | Tampering (JSON-float coercion bypass via ARM CLI) | scripts/arm_simulate.py float-gate invocation | mitigate | The 4 test_cli_rejects_float_* tests (loan.principal, assumed_index_rate, index_path[].value, arm_terms.floor_rate) verify gate fires for all four ARM money/rate fields. Helper itself is tested independently in Plan 05-04a |
| T-05-24 | Information Disclosure (lib.arm imported on --help path) | scripts/arm_simulate.py main() lazy imports | mitigate | test_cli_help_does_not_import_lib_arm asserts lib_arm + lib_amortize + numpy_financial NOT in sys.modules after --help completes |
| T-05-26 | Tampering (sys.path injection ordering) | scripts/arm_simulate.py main() | mitigate | The pattern `_project_root` insert MUST come BEFORE `from scripts._cli_helpers import` AND `from lib.arm import`. Test test_cli_smoke_subprocess_round_trip exercises the full path; failure surfaces as ModuleNotFoundError |
</threat_model>

<verification>
- scripts/arm_simulate.py exists mirroring affordability.py per D-07
- 8 ARM-08 stubs flipped to passing (test_cli_smoke + lazy-import + 4x float-rejects + envelope-uniformity + misaligned-period)
- Phase 3 + Phase 4 + Plan 05-04a test suites BYTE-EQUIVALENT (zero regression)
- --help fast path preserved (lib.arm + lib.amortize + numpy_financial not imported)
- 6-key envelope uniformity verified across float-gate + Pydantic ValidationError sources
- 410 → 418 passed; 22 → 14 xfailed
- mypy + ruff clean across 11 Phase 5 files
</verification>

<success_criteria>
- ARM-08 closed (CLI ships with all 4 boundary checks: float-gate, Pydantic, model_validator, happy-path)
- Phase 3 + Phase 4 + Plan 05-04a test suites byte-equivalent (no regression from 05-04b)
- Test count: 418 passed, 14 xfailed, 4 skipped, 0 failed, 0 errors
- mypy --strict + ruff clean across 11 files
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-04b-SUMMARY.md` documenting:
- scripts/arm_simulate.py shipped at project root mirroring scripts/affordability.py
- 8 ARM-08 stubs flipped (full list)
- xfail count: 22 → 14
- Pass count: 410 → 418
- Phase 3 + Phase 4 + Plan 05-04a byte-equivalent verification
- ARM-08 closure status
- mypy + ruff status across 11 files
</output>
