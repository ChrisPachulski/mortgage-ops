---
phase: 07
plan: 04
type: execute
wave: 4
depends_on: ["07-03"]
files_modified:
  - scripts/apr_reg_z.py
autonomous: true
requirements: [APR-06, APR-07]
tags:
  - phase-07
  - estimated-apr
  - cli
must_haves:
  truths:
    - "scripts/apr_reg_z.py exists at project root mirroring scripts/arm_simulate.py shape"
    - "argparse + --input <path> only; lazy-import lib.apr + numpy_financial AFTER argparse (D-18)"
    - "JSON-float pre-validation gate via scripts._cli_helpers.find_json_float_loc (Phase 5 factor reuse)"
    - "6-key Pydantic envelope on stderr (WR-02 + Phase 4 D-13 inheritance)"
    - "APRConvergenceError caught explicitly and surfaced as 6-key envelope"
    - "Happy path: APRResponse.model_dump_json(indent=2) on stdout, exit 0"
    - "--help epilog includes the literal 'estimated APR' phrase + cites references/apr-reg-z.md"
  artifacts:
    - path: "scripts/apr_reg_z.py"
      provides: "JSON-in/JSON-out CLI for the APR solver"
      contains: "def main"
      min_lines: 180
---

## Goal

Ship `scripts/apr_reg_z.py` mirroring `scripts/arm_simulate.py` (the
canonical Phase 5 CLI shape). Same argparse skeleton, same lazy-import,
same 6-key Pydantic envelope, same `_cli_helpers` reuse. New responsibilities:
(1) catch `APRConvergenceError` and surface via 6-key envelope; (2) cite
`references/apr-reg-z.md` in --help epilog (ROADMAP SC-5 cite-from-script
contract); (3) ensure all user-facing strings respect "estimated APR"
literal (SC-4) — relies on `APRResponse._summary_contains_literal_estimated_apr`
already enforced at the model boundary.

## Tasks

### Task 1 — Create `scripts/apr_reg_z.py` skeleton

Lift `scripts/arm_simulate.py:1-103` (already concise — 103 lines).

```python
"""Estimated APR CLI: JSON-in / JSON-out wrapper around lib.apr.solve_apr.

Mirrors scripts/arm_simulate.py per Phase 5 D-07 + Phase 3 D-17/D-18/D-19 +
Phase 4 D-13 inheritance:

- Lives at project root (Phase 7); Phase 10 relocates to
  .claude/skills/mortgage-ops/scripts/apr_reg_z.py per PROJECT.md decision #8.
- `--input <path>` only (no stdin in v1).
- Lazy-imports lib.apr + numpy_financial AFTER argparse so `--help` is fast (D-18).
- JSON-float pre-validation gate covers loan.principal, finance_charges,
  advance_schedule[].amount, payment_schedule[].amount, disclosed_apr,
  unit_period_fraction (any other money/rate field). Float gate emits
  6-key Pydantic envelope on stderr (Phase 3 WR-02 closure). Helper sourced
  from scripts._cli_helpers (factored Phase 5 Plan 05-04a).
- Pydantic ValidationError surfaces e.json() on stderr — also 6-key shape.
- APRConvergenceError caught explicitly and surfaced as 6-key envelope per
  Phase 4 D-13 (BLOCKER fix) precedent for non-Pydantic ValueError surfaces.
- Happy path: prints APRResponse.model_dump_json(indent=2) on stdout, exit 0.
- Boundary failure: exit 2 with envelope on stderr.

User-facing strings — every reference to APR uses the literal 'estimated APR'
(ROADMAP SC-4); enforced at the model boundary by APRResponse._summary_contains_literal_estimated_apr.

References cited:
- references/apr-reg-z.md (per ROADMAP SC-5 — cited in --help epilog)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apr_reg_z",
        description=(
            "Compute the estimated APR for a closed-end mortgage per "
            "12 CFR Part 1026 Appendix J (Reg Z). JSON-in / JSON-out."
        ),
        epilog=(
            "Input JSON shape (APRRequest):\n"
            "  {\n"
            '    "loan": {Phase 1 Loan: principal/annual_rate/term_months/origination_date/loan_type},\n'
            '    "finance_charges": "2500.00",\n'
            '    "advance_schedule": [{"unit_period_offset": 0, "amount": "200000.00"}],\n'
            '    "payment_schedule": [{"starting_unit_period": 1, "periods": 360, "amount": "1264.14"}],\n'
            '    "day_count": "30/360",         // 30/360|actual/365|actual/actual\n'
            '    "unit_periods_per_year": 12,   // 12 = monthly\n'
            '    "odd_first_period_days": 0,    // days beyond standard unit period from origination to first payment\n'
            '    "disclosed_apr": "0.072000"    // optional; populates tolerance_check\n'
            "  }\n"
            "All money/rate fields MUST be JSON strings (Phase 3 D-19; never JSON floats).\n"
            "\n"
            "Output JSON shape (APRResponse):\n"
            "  {\n"
            '    "estimated_apr": "0.072345",\n'
            '    "iterations": 5,\n'
            '    "final_residual": "0.00",\n'
            '    "summary": "estimated APR: 7.2345% (converged in 5 iterations, residual $0.00)",\n'
            '    "tolerance_check": null | {within_tolerance: bool, ...}\n'
            "  }\n"
            "\n"
            "User-facing strings always use the literal 'estimated APR' (never bare 'APR'),\n"
            "per ROADMAP SC-4. See references/apr-reg-z.md for the unit-period model,\n"
            "day-count conventions, and odd-first-period handling with regulatory citations.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the APRRequest.",
    )
    args = parser.parse_args()

    # sys.path injection (mirrors scripts/affordability.py:140-143)
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # Lazy-import per D-18 / D-13: heavy deps NOT loaded on the --help fast path.
    from lib.apr import APRRequest, APRConvergenceError, solve_apr
    from pydantic import ValidationError, VERSION as _pydantic_version
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

    try:
        raw = args.input.read_text()
    except FileNotFoundError as e:
        print(json.dumps({"error": f"input file not found: {e.filename}"}), file=sys.stderr)
        return 2
    except OSError as e:
        print(json.dumps({"error": f"could not read input file: {e}"}), file=sys.stderr)
        return 2

    # JSON-float pre-validation gate (D-19 + WR-02)
    float_hit = find_json_float_loc(raw)
    if float_hit is not None:
        loc, input_str = float_hit
        envelope = make_decimal_type_envelope(loc, input_str)
        print(json.dumps(envelope), file=sys.stderr)
        return 2

    try:
        request = APRRequest.model_validate_json(raw)
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2

    # APRConvergenceError catch — mirrors scripts/affordability.py:221-238
    # MissingCountyDataError pattern (Phase 4 D-13 BLOCKER fix). The solver
    # raises APRConvergenceError after 50 iterations; without explicit catch
    # this would escape main() as a Python traceback.
    try:
        response = solve_apr(request)
    except APRConvergenceError as e:
        _major_minor = ".".join(_pydantic_version.split(".")[:2])
        envelope = [{
            "type": "value_error",
            "loc": ["solver"],
            "msg": str(e),
            "input": request.model_dump(mode="json"),
            "url": f"https://errors.pydantic.dev/{_major_minor}/v/value_error",
            "ctx": {
                "class": "APRConvergenceError",
                "iterations": e.iterations,
                "last_residual": str(e.last_residual),
                "last_i": str(e.last_i),
            },
        }]
        print(json.dumps(envelope), file=sys.stderr)
        return 2

    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Task 2 — Flip Wave 0 stubs

Remove `@pytest.mark.xfail` and replace bodies with real assertions for:

- **`test_apr_response_uses_literal_estimated_apr_text`** — call solver
  on a temp APRRequest; assert `"estimated APR" in response.summary` and
  `re.search(r'\bAPR\b(?!\s*tolerance)', response.summary.replace("estimated APR", ""))` is None.

- **`test_apr_cli_subprocess_round_trip`** — write apr_fixture("regz_appendix_j_5000_36_166_07")
  to tmp_path/input.json (or a Wave-4-only inline fixture if Wave 5 not
  shipped), run `subprocess.run([sys.executable, str(SCRIPT_PATH),
  "--input", str(input_json)], capture_output=True, text=True, check=True)`,
  parse stdout, assert estimated_apr value.

- **`test_apr_cli_help_does_not_import_lib_apr`** — run `subprocess.run(
  [sys.executable, str(SCRIPT_PATH), "--help"], ...)`, assert exit 0,
  assert "estimated APR" or "APRRequest" in stdout, then run a separate
  subprocess that inspects `sys.modules` after import-but-no-args (mirror
  Phase 5 D-18 test pattern in `tests/test_arm.py`).

- **`test_apr_cli_rejects_float_loan_amount`** — write JSON with
  `"principal": 200000.00` (not a string), run subprocess, assert exit 2,
  parse stderr, assert envelope shape `[{"type": "decimal_type", "loc": [...],
  "msg": ..., "input": ..., "url": ..., "ctx": {...}}]`.

- **`test_apr_cli_error_envelope_uniformity`** — run two subprocess
  invocations: one with float-rejected input, one with Pydantic-rejected
  input (e.g., missing `advance_schedule`); assert both stderr envelopes
  have the same 6 keys.

## Acceptance

- `scripts/apr_reg_z.py` exists, ≥180 lines
- `grep -c 'from lib.apr import' scripts/apr_reg_z.py` returns 1 (lazy import inside main)
- `grep -c 'from scripts._cli_helpers import' scripts/apr_reg_z.py` returns 1
- `grep -c 'estimated APR' scripts/apr_reg_z.py` returns ≥2 (epilog + module docstring)
- `grep -c 'references/apr-reg-z.md' scripts/apr_reg_z.py` returns ≥1 (epilog citation)
- `grep -c 'APRConvergenceError' scripts/apr_reg_z.py` returns ≥2 (catch + envelope ctx)
- `python scripts/apr_reg_z.py --help` exits 0 with epilog visible
- `pytest tests/test_apr.py::test_apr_response_uses_literal_estimated_apr_text -v` PASSES
- `pytest tests/test_apr.py::test_apr_cli_subprocess_round_trip -v` PASSES
- `pytest tests/test_apr.py::test_apr_cli_help_does_not_import_lib_apr -v` PASSES
- `pytest tests/test_apr.py::test_apr_cli_rejects_float_loan_amount -v` PASSES
- `pytest tests/test_apr.py::test_apr_cli_error_envelope_uniformity -v` PASSES
- mypy --strict scripts/apr_reg_z.py clean
- ruff check + format clean

## LOCKED DECISIONS

- **D-19:** CLI shape is byte-for-byte (modulo argument names + epilog text) the same as `scripts/arm_simulate.py`. Phase 7 inherits Phase 5 D-07 inheritance chain.
- **D-20:** `--help` epilog cites `references/apr-reg-z.md` per ROADMAP SC-5. Phase 5 ARM CLI does NOT cite `references/arm-mechanics.md` in --help; Phase 7 sets the precedent (and we may retroactively add it to ARM in a Phase 7+ hygiene plan).
- **D-21:** APRConvergenceError envelope shape: `type="value_error"`, `loc=["solver"]`, `ctx={"class": "APRConvergenceError", "iterations": int, "last_residual": str, "last_i": str}`. Mirrors `scripts/affordability.py:221-238` MissingCountyDataError envelope.
- **D-22:** All user-facing string surfaces (epilog, summary) use the literal "estimated APR". Enforcement at three layers: (a) module-level Pydantic validator on `APRResponse.summary` (Wave 1 D-05); (b) regex test (Wave 5); (c) docstring contract.

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
python scripts/apr_reg_z.py --help | head -40
pytest tests/test_apr.py -v --tb=short 2>&1 | tail -30
mypy --strict scripts/apr_reg_z.py
ruff check scripts/apr_reg_z.py
ruff format --check scripts/apr_reg_z.py
pytest -q 2>&1 | tail -5
```

## Deviation Rules

- Rule-1: any deviation from the `scripts/arm_simulate.py` shape requires
  plan revision (Phase 5 D-07 + Phase 3 D-17 inheritance chain).
- Rule-3: hygiene only.

## Cross-wave Dependency Notes

- **Upstream:** Waves 1-3 (models + solver + odd-first-period). Wave 5
  ships the Reg Z anchor fixture used by `test_apr_cli_subprocess_round_trip`;
  Wave 4 may use a temp inline fixture and link to the Wave 5 fixture
  with a TODO.
- **Downstream:** Wave 5 (regression tests) extends the CLI tests with
  per-fixture parametric coverage; Wave 7 (FFIEC fixtures) drives the
  CLI through the 20+ oracle corpus.
- APR-06 + APR-07 fully closed by this wave.
