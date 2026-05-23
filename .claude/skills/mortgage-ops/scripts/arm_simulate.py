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

    # Phase 10 relocation (D-01): script lives at
    # .claude/skills/mortgage-ops/scripts/arm_simulate.py (5 levels deep). Inject
    # BOTH the repo root (so `from lib.arm import ...` resolves) AND the
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
    from lib.arm import ARMRequest, build_arm_schedule
    from lib.observability import log_event, observe
    from pydantic import ValidationError
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

    with observe(cli="arm_simulate", inputs={"args": vars(args)}) as ctx:
        raw = args.input.read_text()

        # JSON-float pre-validation gate (D-19 + WR-02 closure).
        # Phase 5 D-07 explicitly extends this to ARM money/rate fields:
        # loan.principal, assumed_index_rate, index_path[].value, arm_terms.floor_rate.
        # The walker is generic — finds the FIRST JSON float anywhere in the tree.
        float_hit = find_json_float_loc(raw)
        if float_hit is not None:
            loc, input_str = float_hit
            envelope = make_decimal_type_envelope(loc, input_str)
            log_event(
                ctx,
                "ERROR",
                "json float in money field",
                event="validation_float_gate",
                exit_status="error_validation",
                loc=loc,
                offending_input=input_str,
            )
            print(json.dumps(envelope), file=sys.stderr)
            return 2

        # Pydantic boundary validation. Catches:
        # - Missing required fields (e.g., floor_rate per D-02)
        # - Misaligned index_path periods (model_validator from Plan 05-02)
        # - Type errors (e.g., string where int expected)
        try:
            request = ARMRequest.model_validate_json(raw)
        except ValidationError as e:
            log_event(
                ctx,
                "ERROR",
                "pydantic validation failed",
                event="validation_pydantic",
                exit_status="error_validation",
                error_count=e.error_count(),
            )
            print(e.json(), file=sys.stderr)
            return 2

        # Happy path: build the ARM schedule and emit JSON to stdout.
        schedule = build_arm_schedule(request)
        payload = schedule.model_dump_json(indent=2)
        ctx.set_output(json.loads(payload))
        log_event(
            ctx,
            "INFO",
            "arm schedule built",
            event="arm_schedule_built",
            payments=len(schedule.payments),
        )
        print(payload)
        return 0


if __name__ == "__main__":
    sys.exit(main())
