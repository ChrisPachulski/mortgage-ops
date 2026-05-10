"""Estimated APR CLI: JSON-in / JSON-out wrapper around lib.apr.solve_apr.

Mirrors scripts/arm_simulate.py per Phase 5 D-07 + Phase 3 D-17/D-18/D-19 +
Phase 4 D-13 inheritance + Phase 7 Plan 07-04 D-19/D-20/D-21/D-22:

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
  Phase 4 D-13 (BLOCKER fix) precedent for non-Pydantic ValueError surfaces
  (D-21: type='value_error', loc=['solver'], ctx={'class':
  'APRConvergenceError', 'iterations', 'last_residual', 'last_i'}).
- Happy path: prints APRResponse.model_dump_json(indent=2) on stdout, exit 0.
- Boundary failure: exit 2 with envelope on stderr.

User-facing strings — every reference to APR uses the literal "estimated APR"
(ROADMAP SC-4 / D-22); enforcement at three layers:
  (a) module-level Pydantic validator on APRResponse.summary (Wave 1 D-05),
  (b) regex test in tests/test_apr.py (Wave 5),
  (c) docstring + epilog contract (this file).

References cited:
- references/apr-reg-z.md (per ROADMAP SC-5 + D-20 — cited in --help epilog;
  Phase 5 ARM CLI does NOT cite references/arm-mechanics.md in --help; Phase 7
  sets the precedent and a future hygiene plan may retroactively add it to ARM).

Test invocation pattern (tests/test_apr.py): subprocess via SCRIPT_PATH constant,
NEVER `from scripts.apr_reg_z import main` (Phase 3 D-17 portability —
Phase 10 relocates the script).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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

    # Phase 10 relocation (D-01): script lives at
    # .claude/skills/mortgage-ops/scripts/apr_reg_z.py (5 levels deep). Inject
    # BOTH the repo root (so `from lib.apr import ...` resolves) AND the
    # skill root (so `from scripts._cli_helpers import ...` resolves to the
    # colocated helper, NOT the project-root scripts/ which no longer hosts it).
    # parents[4] = repo root; parents[1] = skill root. Runs AFTER --help has
    # exited above, so D-18 (--help fast) is unaffected.
    _skill_root = str(Path(__file__).resolve().parents[1])
    _project_root = str(Path(__file__).resolve().parents[4])
    for _p in (_project_root, _skill_root):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    # Lazy-import per D-18 / D-13: heavy deps NOT loaded on the --help fast path.
    from lib.apr import APRConvergenceError, APRRequest, solve_apr
    from pydantic import VERSION as _pydantic_version
    from pydantic import ValidationError
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

    try:
        raw = args.input.read_text()
    except FileNotFoundError as e:
        print(
            json.dumps({"error": f"input file not found: {e.filename}"}),
            file=sys.stderr,
        )
        return 2
    except OSError as e:
        print(
            json.dumps({"error": f"could not read input file: {e}"}),
            file=sys.stderr,
        )
        return 2

    # JSON-float pre-validation gate (D-19 + WR-02 closure).
    # Phase 7 D-19 explicitly extends this to APR money/rate fields:
    # loan.principal, finance_charges, advance_schedule[].amount,
    # payment_schedule[].amount, disclosed_apr, unit_period_fraction, ...
    # The walker is generic — finds the FIRST JSON float anywhere in the tree.
    float_hit = find_json_float_loc(raw)
    if float_hit is not None:
        loc, input_str = float_hit
        envelope = make_decimal_type_envelope(loc, input_str)
        print(json.dumps(envelope), file=sys.stderr)
        return 2

    # Pydantic boundary validation. Catches:
    # - Missing required fields (e.g., advance_schedule)
    # - Cross-field validator failures (e.g., t=0 advance missing per D-06)
    # - Type errors (e.g., string where int expected)
    try:
        request = APRRequest.model_validate_json(raw)
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2

    # APRConvergenceError catch — mirrors scripts/affordability.py
    # MissingCountyDataError pattern (Phase 4 D-13 BLOCKER fix). The solver
    # raises APRConvergenceError after MAX_ITER iterations; without explicit
    # catch this would escape main() as a Python traceback. Surface as 6-key
    # envelope per D-21 (type='value_error', loc=['solver'], ctx carries the
    # APRConvergenceError attributes for caller debugging).
    #
    # Variable name `convergence_envelope` (vs the `envelope` used by the
    # float-gate above) is intentional: it documents the disposition contrast
    # (boundary-rejection vs. solver-divergence) and avoids mypy's
    # name-redefinition error under --strict.
    try:
        response = solve_apr(request)
    except APRConvergenceError as e:
        _major_minor = ".".join(_pydantic_version.split(".")[:2])
        convergence_envelope: list[dict[str, Any]] = [
            {
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
            }
        ]
        print(json.dumps(convergence_envelope), file=sys.stderr)
        return 2

    # Happy path: emit APRResponse JSON to stdout with the literal "estimated
    # APR" phrase already enforced at the model boundary by
    # APRResponse._summary_contains_literal_estimated_apr (D-22).
    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
