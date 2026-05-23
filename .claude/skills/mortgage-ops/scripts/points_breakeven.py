"""Discount-points breakeven CLI: JSON-in / JSON-out wrapper around lib.points.evaluate.

Mirrors scripts/arm_simulate.py per Phase 5 D-07 inheritance. Single-engine
shape (no --mode arg per Plan 08-04 D-04-04); the JSON's 'mode' discriminator
selects from_savings vs from_loans. Reports BOTH simple_breakeven_months AND
npv_breakeven_months side-by-side per ROADMAP SC-4.

Lazy-imports lib.points + pydantic + numpy_financial AFTER argparse so
--help is fast (D-18 / Phase 4 D-13 inherited). 6-key envelope on stderr
for ValidationError + float-gate hits (Phase 3 WR-02 closure inherited).

discount_rate_annual is REQUIRED (Plan 08-04 D-04-05; Plan 08-03 D-02
deferred-coupling note). Phase 6 will add a project-wide default via a
single-line additive non-breaking edit when its borrower-perspective
convention lands.

Test invocation pattern (tests/test_points.py): subprocess via SCRIPT_PATH
constant, NEVER `from scripts.points_breakeven import main` (Phase 3 D-17
portability — Phase 10 relocates the script).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="points_breakeven",
        description=(
            "Compute discount-points breakeven analysis. Reports BOTH simple "
            "and NPV-based breakeven months side-by-side per ROADMAP SC-4, "
            "plus a buy/skip decision based on cumulative NPV at the hold "
            "horizon. JSON-in / JSON-out per Phase 8 PNTS-03."
        ),
        epilog=(
            "Input JSON shape (D-01 discriminated union by 'mode'):\n"
            "\n"
            "  FROM_SAVINGS MODE (caller pre-computed monthly_savings):\n"
            "    {\n"
            '      "mode": "from_savings",\n'
            '      "points_cost": "8000.00",\n'
            '      "monthly_savings": "65.40",\n'
            '      "hold_period_months": 240,\n'
            '      "discount_rate_annual": "0.070000"  // REQUIRED; see references/points-breakeven.md\n'
            "    }\n"
            "\n"
            "  FROM_LOANS MODE (engine derives savings from two Loans):\n"
            "    {\n"
            '      "mode": "from_loans",\n'
            '      "points_cost": "8000.00",\n'
            '      "loan_with_points": {Phase 1 Loan with bought-down rate},\n'
            '      "loan_without_points": {Phase 1 Loan with original rate},\n'
            '      "hold_period_months": 240,\n'
            '      "discount_rate_annual": "0.070000"\n'
            "    }\n"
            "\n"
            "All money/rate fields MUST be JSON strings (D-19; never JSON floats).\n"
            "discount_rate_annual has NO default — caller chooses opportunity cost.\n"
            "  Recommended starting points (until Phase 6 lands a project-wide default):\n"
            "    - 0.000000 (zero opportunity cost; collapses NPV to simple by D-03-03)\n"
            "    - loan annual rate (paying-down-debt opportunity proxy)\n"
            "    - 0.050000 (rough US 10yr Treasury proxy)\n"
            "\n"
            "Negative monthly_savings (rate-up scenario) is allowed at construction;\n"
            "engine returns simple/npv = None with a NEGATIVE_OR_ZERO_SAVINGS warning\n"
            "and decision = skip_points (D-03-01 + D-03-04 mirrors Phase 4 D-11).\n"
            "\n"
            "See references/points-breakeven.md for formula details, discount-rate\n"
            "guidance, and the SC-4 divergence example.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the points request.",
    )
    args = parser.parse_args()

    # Phase 10 relocation (D-01): script lives at
    # .claude/skills/mortgage-ops/scripts/points_breakeven.py (5 levels deep).
    # Inject BOTH the repo root (so `from lib.points import ...` resolves) AND
    # the skill root (so `from scripts._cli_helpers import ...` resolves to the
    # colocated helper, NOT the project-root scripts/ which no longer hosts it).
    # parents[4] = repo root; parents[1] = skill root. Runs AFTER --help has
    # exited above, so D-18 (--help fast) is unaffected.
    _skill_root = str(Path(__file__).resolve().parents[1])
    _project_root = str(Path(__file__).resolve().parents[4])
    for _p in (_project_root, _skill_root):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    # Lazy-import per D-18 / D-13: heavy deps NOT loaded on the --help fast path.
    from lib.observability import log_event, observe
    from lib.points import PointsRequest, evaluate
    from pydantic import TypeAdapter, ValidationError
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

    with observe(cli="points_breakeven", inputs={"args": vars(args)}) as ctx:
        raw = args.input.read_text()

        # JSON-float pre-validation gate (D-19 + WR-02 closure).
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

        # Pydantic boundary validation (discriminated union).
        try:
            adapter: TypeAdapter[Any] = TypeAdapter(PointsRequest)
            request = adapter.validate_json(raw)
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

        # Happy path.
        response = evaluate(request)
        payload = response.model_dump_json(indent=2)
        ctx.set_output(json.loads(payload))
        log_event(
            ctx,
            "INFO",
            "points evaluated",
            event="points_evaluated",
            mode=request.mode,
        )
        print(payload)
        return 0


if __name__ == "__main__":
    sys.exit(main())
