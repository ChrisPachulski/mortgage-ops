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
from typing import Any


def _find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    """Walk parsed JSON and return (loc-path, decimal-string) of the first JSON float.

    Pydantic v2 strict mode accepts JSON numbers for Decimal fields by design
    (https://docs.pydantic.dev/2.13/concepts/json/#json-parsing) — JSON has no
    distinct decimal type, so Pydantic permissively coerces JSON numbers. But
    the project's money-discipline contract (CLAUDE.md FND-01) and D-19 require
    money/rate fields be JSON STRINGS (e.g. "400000.00"). So we pre-parse with
    `parse_float=Decimal` to mark JSON-numbers-with-decimal-points as Decimal
    instances, then walk the parsed tree to find the first Decimal — its
    loc-path identifies the offending field.

    WR-02 closure: returns BOTH the loc-path AND the offending input value
    (as a Decimal-string) so the boundary error envelope can populate the
    Pydantic-shape `input` key without re-walking the JSON. Returns None
    when no JSON floats are present.

    The schema has zero fields that legitimately accept JSON floats:
      - principal / annual_rate / amount: must be JSON strings (Money/Rate)
      - term_months / period: JSON integers
      - origination_date: JSON string (ISO date) or null
      - loan_type / frequency / biweekly_mode: JSON strings or null
      - recurring: JSON boolean
    A blanket "reject any JSON float" check is therefore correct.
    """
    from decimal import Decimal as _Decimal  # local-import: keeps --help fast (D-18)

    try:
        parsed = json.loads(raw, parse_float=_Decimal)
    except json.JSONDecodeError:
        # Invalid JSON — let Pydantic's model_validate_json produce the canonical error.
        return None

    def _walk(node: Any, path: list[str | int]) -> tuple[list[str | int], str] | None:
        if isinstance(node, _Decimal):
            # str(Decimal) preserves the original lexical form (e.g. "400000.00"
            # round-trips exactly when reconstructed via Decimal(str(...))).
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

    # When invoked as a script (`python scripts/amortize.py ...`), Python puts
    # `scripts/` on sys.path, NOT the project root, so `from lib.amortize import ...`
    # fails with ModuleNotFoundError. Insert the project root (parent of this file's
    # directory) at sys.path[0] so the lazy-import below resolves. Cheap (one Path
    # operation + list insert) and runs only AFTER --help has already exited above,
    # so D-18 (--help fast) is unaffected.
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # lazy-import per D-18: heavy deps (numpy_financial, dateutil, lib.amortize)
    # are NOT loaded on the --help fast path. argparse has already parsed by here,
    # so any --help / --version invocation has SystemExit'd above this line.
    from lib.amortize import AmortizeRequest, build_schedule
    from pydantic import ValidationError

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
    float_hit = _find_json_float_loc(raw)
    if float_hit is not None:
        float_loc, float_input = float_hit

        # Lazy-imported pydantic.VERSION here (NOT at module top) to preserve
        # D-18 fast --help. The version segment in the docs URL floats with
        # the runtime Pydantic version so a 2.13 to 2.14 upgrade auto-aligns.
        from pydantic import VERSION as _pydantic_version

        _major_minor = ".".join(_pydantic_version.split(".")[:2])
        envelope = [
            {
                "type": "decimal_type",
                "loc": float_loc,
                "msg": (
                    "Input should be a valid decimal — JSON string required "
                    "for money/rate fields per D-19 (JSON floats are rejected "
                    "at the boundary)"
                ),
                "input": float_input,
                "url": f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type",
                "ctx": {
                    "class": "Decimal",
                    "field_path": ".".join(str(p) for p in float_loc),
                },
            }
        ]
        print(json.dumps(envelope), file=sys.stderr)
        return 2

    # D-19: Pydantic v2 model_validate_json at the boundary handles every other
    # validation surface (shape, type, D-02 cross-field, extra=forbid, etc.) and
    # emits structured JSON-readable errors via e.json().
    try:
        request = AmortizeRequest.model_validate_json(raw)
    except ValidationError as e:
        # Pydantic emits structured JSON-readable errors; pass through as JSON.
        print(e.json(), file=sys.stderr)
        return 2

    schedule = build_schedule(
        request.loan,
        frequency=request.frequency,
        biweekly_mode=request.biweekly_mode,
        extra_principal=request.extra_principal,
    )
    print(schedule.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
