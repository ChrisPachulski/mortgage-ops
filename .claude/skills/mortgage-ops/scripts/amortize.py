#!/usr/bin/env python3
"""scripts/amortize.py — JSON-in / JSON-out CLI for the amortization engine.

Per AMRT-06 + D-17/D-18/D-19:
  - File-based input only: --input <path> (no stdin in v1, per D-18)
  - JSON output to stdout (pipe-friendly)
  - --help works without importing heavy deps (lazy-import of lib.amortize,
    numpy_financial, dateutil per D-18)
  - Pydantic v2 strict-mode validation at the boundary (D-19): float in any
    Money/Rate field is rejected immediately with a structured JSON error.

Default biweekly_mode = "true" when frequency is "biweekly" without an explicit
mode (D-02). The model preserves "what the caller provided"; the engine applies
the default at schedule-generation time.

D-17: Phase 3 keeps this script at project root. Phase 10 physically relocates
it to .claude/skills/mortgage-ops/scripts/amortize.py — only the path moves;
test SCRIPT_PATH constants and SKILL.md routing absorb the change.

Input JSON shape (full):
  {
    "loan": {
      "principal": "400000.00",          // string; Pydantic strict mode rejects floats
      "annual_rate": "0.065000",         // string
      "term_months": 360,                // int
      "origination_date": "2026-05-01",  // ISO date OR omit (engine synthesizes today)
      "loan_type": "fixed"               // optional; defaults to "fixed"
    },
    "frequency": "monthly" | "biweekly", // optional; defaults to "monthly"
    "biweekly_mode": "true" | "half-monthly" | null,  // optional; null when frequency=monthly
    "extra_principal": [                 // optional; defaults to []
      {"period": 60, "amount": "5000.00", "recurring": false}
    ]
  }

Envelope Shape Contract (WR-02 closure):
  All ValidationError-class boundary surfaces emit a uniform 6-key Pydantic v2
  e.json() envelope on stderr:
    [{"type": "<error_type>", "loc": [<JSON-pointer>],
      "msg": "<message>",     "input": "<offending_value>",
      "url": "<docs_url>",    "ctx": {"class": "<...>", ...}}]
  Canonical URL pattern: https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type}
  with the version segment computed at runtime from `pydantic.VERSION` so that
  a Pydantic minor upgrade (e.g. 2.13 -> 2.14) auto-aligns without code change.
  This applies BOTH to native Pydantic ValidationError (the e.json() pass-through
  path) AND to the pre-validation float-gate (which constructs an equivalent
  envelope manually using `pydantic.VERSION` to populate the docs URL).

  Downstream consumers parse stderr as a JSON list of 6-key error dicts:
    - Phase 9 (Node orchestration / DuckDB persistence) — db-write.mjs ingests
      the envelope as the canonical error record.
    - Phase 10 (Claude SKILL.md narration) — modes/_shared.md narrates the
      rejection by reading `loc` (which field) + `msg` (why) + `input` (the
      rejected value). No conditional shape detection needed across the
      ValidationError-class surfaces.

  Out of scope for the 6-key contract: file-not-found and OSError surfaces use
  the simpler `{"error": "<message>"}` shape (predates the envelope contract;
  not Pydantic ValidationError surfaces). Argparse usage errors use argparse's
  stderr formatting, also out of scope.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="amortize",
        description="Generate an amortization schedule from a JSON loan input.",
        epilog=(
            "Input JSON shape: a Loan object plus optional 'frequency' "
            '("monthly"|"biweekly"; default "monthly"), "biweekly_mode" '
            '("true"|"half-monthly"; default "true" when frequency=biweekly), '
            'and "extra_principal" (list of {period, amount, recurring} entries). '
            'All money/rate fields MUST be JSON strings (e.g. "400000.00"); '
            "Pydantic v2 strict mode rejects JSON floats at the boundary."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the loan input.",
    )
    args = parser.parse_args()

    # Phase 10 relocation (D-01): script lives at
    # .claude/skills/mortgage-ops/scripts/amortize.py (5 levels deep). Inject
    # BOTH the repo root (so `from lib.amortize import ...` resolves) AND the
    # skill root (so `from scripts._cli_helpers import ...` resolves to the
    # colocated helper, NOT the project-root scripts/ which no longer hosts it).
    # parents[4] = repo root; parents[1] = skill root. Runs AFTER --help has
    # exited above, so D-18 (--help fast) is unaffected.
    _skill_root = str(Path(__file__).resolve().parents[1])
    _project_root = str(Path(__file__).resolve().parents[4])
    for _p in (_project_root, _skill_root):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    # Lazy-import per D-18: heavy deps (numpy_financial, dateutil, lib.amortize)
    # are NOT loaded on the --help fast path. argparse has already parsed by here,
    # so any --help / --version invocation has SystemExit'd above this line.
    # scripts._cli_helpers is the Phase 5 factor-extract: single source of truth
    # for the JSON-float pre-validation gate + 6-key WR-02 envelope shape.
    from lib.amortize import AmortizeRequest, build_schedule
    from lib.observability import log_event, observe
    from pydantic import ValidationError
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

    # Observability wraps the entire body so a failure anywhere still emits a
    # final run_complete / run_error event. The wrapped block returns the exit
    # code; the outer ``with`` re-yields it via ``rc`` so SystemExit pulls the
    # right value. ``inputs={"args": vars(args)}`` is the canonical input
    # snapshot per the project standard.
    with observe(cli="amortize", inputs={"args": vars(args)}) as ctx:
        try:
            raw = args.input.read_text()
        except FileNotFoundError as e:
            log_event(
                ctx,
                "ERROR",
                "input file not found",
                event="input_file_missing",
                exit_status="error_validation",
                input_path=str(args.input),
                filename=e.filename,
            )
            print(
                json.dumps({"error": f"input file not found: {e.filename}"}),
                file=sys.stderr,
            )
            return 2
        except OSError as e:
            log_event(
                ctx,
                "ERROR",
                "input file unreadable",
                event="input_file_unreadable",
                exit_status="error_validation",
                input_path=str(args.input),
                error=str(e),
            )
            print(
                json.dumps({"error": f"could not read input file: {e}"}),
                file=sys.stderr,
            )
            return 2

        # D-19 + WR-02: pre-validation gate — reject JSON-numbers-with-decimal-points
        # in money fields BEFORE handing to Pydantic. Pydantic v2 model_validate_json
        # permissively coerces JSON floats into Decimal (documented behavior per
        # Pydantic 2.13 JSON concepts); the project's CLAUDE.md FND-01 + CONTEXT.md
        # D-19 require money/rate fields be JSON strings.
        #
        # Envelope shape: 6-key Pydantic v2 e.json() shape uniformly across ALL
        # ValidationError-class boundary failure modes (WR-02 closure). Phase 9
        # Node orchestration and Phase 10 SKILL.md narration parse stderr as a
        # single uniform contract.
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

        # D-19: Pydantic v2 model_validate_json at the boundary handles every other
        # validation surface (shape, type, D-02 cross-field, extra=forbid, etc.) and
        # emits structured JSON-readable errors via e.json().
        try:
            request = AmortizeRequest.model_validate_json(raw)
        except ValidationError as e:
            log_event(
                ctx,
                "ERROR",
                "pydantic validation failed",
                event="validation_pydantic",
                exit_status="error_validation",
                error_count=e.error_count(),
            )
            # Pydantic emits structured JSON-readable errors; pass through as JSON.
            print(e.json(), file=sys.stderr)
            return 2

        schedule = build_schedule(
            request.loan,
            frequency=request.frequency,
            biweekly_mode=request.biweekly_mode,
            extra_principal=request.extra_principal,
        )
        payload = schedule.model_dump_json(indent=2)
        ctx.set_output(json.loads(payload))
        log_event(
            ctx,
            "INFO",
            "schedule built",
            event="schedule_built",
            payments=len(schedule.payments),
        )
        print(payload)
        return 0


if __name__ == "__main__":
    sys.exit(main())
