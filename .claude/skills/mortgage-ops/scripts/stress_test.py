"""Stress-test CLI: JSON-in / JSON-out wrapper around lib.stress.evaluate.

Mirrors scripts/arm_simulate.py + scripts/affordability.py per Phase 5 D-07
inheritance. JSON discriminator field 'mode' selects the sweep variant
(rate-shock | income-shock | arm-reset); argparse --mode is an advisory hint
that helps users construct the right JSON shape but does NOT override the
discriminator (Pydantic v2 validates the JSON's mode field against the
discriminated union per Plan 08-04 D-04-01).

Two convenience shortcuts overlay parsed CLI lists into the JSON BEFORE
Pydantic validation, so users can invoke the canonical ROADMAP SC-1 / SC-2
forms without hand-editing JSON (Plan 08-04 D-04-02):

  --rates 0.06,0.065,0.07,0.075,0.08    overlays into request.rates (rate-shock mode)
  --reductions 0.05,0.10,0.20           overlays into request.reductions (income-shock mode)

These shortcuts only make sense for rate-shock and income-shock modes
respectively. Misuse (e.g., --rates with arm-reset) silently overlays into a
JSON field that does not exist in the target shape; Pydantic will reject with
the canonical extra=forbid violation envelope on stderr (D-04-03).

Lazy-imports lib.stress + pydantic + numpy_financial AFTER argparse so
--help is fast (D-18 / Phase 4 D-13 inherited). 6-key envelope on stderr
for ValidationError + float-gate hits (Phase 3 WR-02 closure inherited).

Test invocation pattern (tests/test_stress.py): subprocess via SCRIPT_PATH
constant, NEVER `from scripts.stress_test import main` (Phase 3 D-17
portability — Phase 10 relocates the script).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _parse_decimal_list(s: str) -> list[str]:
    """Parse a comma-separated list of decimal strings; preserve as strings.

    Caller is responsible for Decimal coercion (we keep them as strings so
    Pydantic v2 strict mode validates them as Money/Rate per D-19 contract;
    if we converted to float here, the JSON would carry floats and the
    float-gate would (correctly) reject them).
    """
    return [item.strip() for item in s.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="stress_test",
        description=(
            "Run a stress sweep (rate-shock | income-shock | arm-reset) over a "
            "parameter grid. JSON-in / JSON-out per Phase 8 STRS-04. Output "
            "carries a top-of-JSON scenario-summary table for SC-5 subagent "
            "consumption (< 100KB total)."
        ),
        epilog=(
            "Input JSON shape (D-01 discriminated union by 'mode'):\n"
            "\n"
            "  RATE-SHOCK MODE (STRS-01 + ROADMAP SC-1):\n"
            "    {\n"
            '      "mode": "rate-shock",\n'
            '      "loan": {Phase 1 Loan: principal/annual_rate/term_months/...},\n'
            '      "rates": ["0.06", "0.065", "0.07", "0.075", "0.08"],\n'
            '      "baseline_label": "0.065"  // optional; defaults to rates[0]\n'
            "    }\n"
            "\n"
            "  INCOME-SHOCK MODE (STRS-02 + ROADMAP SC-2):\n"
            "    {\n"
            '      "mode": "income-shock",\n'
            '      "base_request": { ... full AffordabilityRequest ... },\n'
            '      "reductions": ["0.05", "0.10", "0.20"],\n'
            '      "dti_threshold": "0.43"  // ATR/QM heuristic per RESEARCH section 3.2\n'
            "    }\n"
            "\n"
            "  ARM-RESET MODE (STRS-03 + ROADMAP SC-3):\n"
            "    {\n"
            '      "mode": "arm-reset",\n'
            '      "base_arm_request": { ... full ARMRequest ... },\n'
            '      "paths": [\n'
            '        {"name": "parallel-shift", "params": {"shift_bps": 200}},\n'
            '        {"name": "gradual-rise", "params": {"step_bps": 25}},\n'
            '        {"name": "fall-then-rise", "params": {"drop_bps": 100, "rise_bps": 200}}\n'
            "      ]\n"
            "    }\n"
            "\n"
            "Convenience CLI shortcuts (rate-shock + income-shock only):\n"
            "  --rates 0.06,0.065,...      overlays into request.rates\n"
            "  --reductions 0.05,0.10,...  overlays into request.reductions\n"
            "\n"
            "Last-write-wins: if the JSON already has rates/reductions, the CLI\n"
            "shortcut overrides them (intentional per Plan 08-04 D-04-02).\n"
            "\n"
            "All money/rate fields MUST be JSON strings (D-19; never JSON floats).\n"
            "ATR/QM threshold default (income-shock) is 0.43 — caller must specify\n"
            "in JSON; no module-level default (Phase 4 D-12 max_dti discipline).\n"
            "\n"
            "See references/stress-tests.md for sweep mechanics, output-schema\n"
            "details, and Phase 11 subagent consumption contract.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the stress request.",
    )
    parser.add_argument(
        "--mode",
        required=False,
        choices=["rate-shock", "income-shock", "arm-reset"],
        help="Advisory hint; the JSON's 'mode' field is authoritative (D-04-01).",
    )
    parser.add_argument(
        "--rates",
        required=False,
        type=_parse_decimal_list,
        help="Comma-separated rates (overlays request.rates for rate-shock).",
    )
    parser.add_argument(
        "--reductions",
        required=False,
        type=_parse_decimal_list,
        help="Comma-separated reductions (overlays request.reductions for income-shock).",
    )
    args = parser.parse_args()

    # Phase 10 relocation (D-01): script lives at
    # .claude/skills/mortgage-ops/scripts/stress_test.py (5 levels deep). Inject
    # BOTH the repo root (so `from lib.stress import ...` resolves) AND the
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
    from lib.observability import log_event, observe
    from lib.stress import StressRequest, evaluate
    from pydantic import TypeAdapter, ValidationError
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

    with observe(cli="stress_test", inputs={"args": vars(args)}) as ctx:
        raw = args.input.read_text()

        # Apply CLI shortcuts BEFORE the float-gate so the float-gate sees the
        # final JSON (D-04-02 verbatim). The parsed list values are strings (per
        # _parse_decimal_list), so the overlay introduces no JSON floats — the
        # float-gate semantics are unchanged. Last-write-wins per D-04-02.
        if args.rates is not None or args.reductions is not None:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                # Let downstream gates surface the JSON parse error with their
                # canonical envelopes; do not swallow it here.
                parsed = None
            if isinstance(parsed, dict):
                if args.rates is not None:
                    parsed["rates"] = args.rates
                if args.reductions is not None:
                    parsed["reductions"] = args.reductions
                raw = json.dumps(parsed)
                log_event(
                    ctx,
                    "INFO",
                    "cli overlay applied",
                    event="cli_overlay_applied",
                    rates_overlay=args.rates,
                    reductions_overlay=args.reductions,
                )

        # JSON-float pre-validation gate (D-19 + WR-02 closure).
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

        # Pydantic boundary validation (discriminated union).
        try:
            adapter: TypeAdapter[Any] = TypeAdapter(StressRequest)
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

        # Happy path: dispatch + emit StressResponse JSON to stdout.
        response = evaluate(request)
        payload = response.model_dump_json(indent=2)
        ctx.set_output(json.loads(payload))
        log_event(
            ctx,
            "INFO",
            "stress evaluated",
            event="stress_evaluated",
            mode=request.mode,
        )
        print(payload)
        return 0


if __name__ == "__main__":
    sys.exit(main())
