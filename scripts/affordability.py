#!/usr/bin/env python3
"""JSON-in / JSON-out CLI for affordability (AFFD-08).

Mirrors scripts/amortize.py per CONTEXT.md D-13 (CLI conventions). Same
argparse skeleton, same --input <path> only, same lazy-import-AFTER-parse
pattern (D-18 fast --help), same 6-key Pydantic envelope on validation
errors (Phase 3 D-19 + WR-02 closure shape).

Modes (D-14 discriminator):
  forward — known loan_amount + property_value → DTI / LTV / CLTV / PITI
  reverse — known max_dti + down_payment + target_ltv_pct → max_loan_amount
            via numpy_financial.pv

Conventions documented in --help epilog:
  - All money/rate fields are JSON STRINGS (Pydantic v2 strict; JSON
    floats rejected at the boundary; same as Phase 3 D-19).
  - household.location.state_fips + county_fips required (RESEARCH Open
    Question #2; lib.rules.types.County contract).
  - target_loan_type=='va' requires household.va block (RESEARCH Open Q#7).
  - target_loan_type=='conventional' with LTV > 0.80 requires
    monthly_pmi (RESEARCH Open Q#1; conventional_pmi predicate has no
    rate; caller supplies the PMI premium).
  - FHA UFMIP is auto-financed into principal per D-03 + RESEARCH §"FHA
    UFMIP Financing Convention"; response.financed_loan_amount surfaces
    the addition.

Envelope Shape Contract (WR-02 closure inheritance from Phase 3):
  All ValidationError-class boundary surfaces emit a uniform 6-key
  Pydantic v2 e.json() envelope on stderr:
    [{"type": "<error_type>", "loc": [<JSON-pointer>],
      "msg": "<message>",     "input": "<offending_value>",
      "url": "<docs_url>",    "ctx": {"class": "<...>", ...}}]
  Canonical URL pattern: https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type}
  where MAJOR.MINOR is computed at runtime from pydantic.VERSION (Phase 3
  03-06 idiom; Pydantic 2.13→2.14 auto-aligns without code change).

  In addition to native Pydantic ValidationError surfaces, the CLI catches
  lib.rules.loan_type.MissingCountyDataError (a ValueError subclass raised
  by lib.rules.loan_type.classify when the household location county_fips
  is not present in data/reference/conforming-limits-2026.yml AND the loan
  amount exceeds the baseline ceiling). It is NOT a Pydantic
  ValidationError; without an explicit catch the exception escapes main()
  as a Python traceback on stderr — violating the Phase 3 D-19 6-key
  envelope contract. We emit a 6-key envelope with type='value_error',
  loc=['household','location'], ctx={'class':'MissingCountyDataError'}
  per Phase 3 D-19 (BLOCKER fix; AFFD-08 contract; T-04-02-03 mitigation).

  Out of scope for the 6-key contract: file-not-found and OSError surfaces
  use the simpler `{"error": "<message>"}` shape (predates the envelope
  contract; not Pydantic ValidationError surfaces). Argparse usage errors
  use argparse's stderr formatting, also out of scope.

Phase 9 / Phase 10 consumers parse stderr as one uniform JSON contract.

D-17 inheritance: Phase 4 keeps this script at project root. Phase 10
physically relocates it to .claude/skills/mortgage-ops/scripts/affordability.py
— only the path moves; test SCRIPT_PATH constants and SKILL.md routing
absorb the change.
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

    Phase 4 schema has zero fields that legitimately accept JSON floats:
      - loan_amount / property_value / down_payment / annual_rate /
        max_dti / target_ltv_pct / monthly_pmi / apr / apor / junior_liens[*] /
        gross_monthly_income / monthly_debts.* / escrow.{property_tax_monthly,
        insurance_monthly, hoa_monthly} / va.actual_residual_income:
          must be JSON strings (Money/Rate)
      - term_months / family_size / credit_score / household.size: JSON ints
      - mode / target_loan_type / location.* / va.region / applicant.name:
        JSON strings
    A blanket "reject any JSON float" check is therefore correct.
    """
    from decimal import Decimal as _Decimal  # local-import: keeps --help fast (D-18)

    try:
        parsed = json.loads(raw, parse_float=_Decimal)
    except json.JSONDecodeError:
        # Invalid JSON — let Pydantic's TypeAdapter.validate_json produce the canonical error.
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
        prog="affordability",
        description="Compute household affordability (forward) or max loan amount (reverse).",
        epilog=(
            "Input JSON shape (D-14 discriminator field 'mode'):\n"
            "\n"
            "  FORWARD MODE — known loan + property:\n"
            "    {\n"
            '      "mode": "forward",\n'
            '      "household": { ... see config/household.example.yml ... },\n'
            '      "max_dti": "0.430000",\n'
            '      "target_loan_type": "conventional"|"fha"|"va"|"usda"|"jumbo",\n'
            '      "term_months": 360,\n'
            '      "annual_rate": "0.065000",\n'
            '      "loan_amount": "400000.00",\n'
            '      "property_value": "500000.00",\n'
            '      "monthly_pmi": "150.00" | null,    // REQUIRED if conventional + LTV > 0.80\n'
            '      "junior_liens": ["50000.00", ...], // optional, default []\n'
            '      "apr": "0.072000" | null,          // optional; ATR/QM advisory if null\n'
            '      "apor": "0.060000" | null          // both-or-neither\n'
            "    }\n"
            "\n"
            "  REVERSE MODE — known max_dti + LTV target:\n"
            "    {\n"
            '      "mode": "reverse",\n'
            '      "household": { ... same shape ... },\n'
            '      "max_dti": "0.430000",\n'
            '      "target_loan_type": "conventional",\n'
            '      "term_months": 360,\n'
            '      "annual_rate": "0.070000",\n'
            '      "down_payment": "100000.00",\n'
            '      "target_ltv_pct": "0.800000"\n'
            "    }\n"
            "\n"
            "Conventions:\n"
            '  - All money/rate fields MUST be JSON strings (e.g. "400000.00");\n'
            "    Pydantic v2 strict mode rejects JSON floats at the boundary.\n"
            "  - household.location.state_fips (2 digits) + county_fips (3 digits)\n"
            "    are REQUIRED for Phase 2 County lookup (e.g. King WA = 53/033).\n"
            "  - target_loan_type=='va' requires household.va block (region,\n"
            "    family_size, actual_residual_income).\n"
            "  - target_loan_type=='conventional' with LTV > 0.80 requires\n"
            "    monthly_pmi (conventional_pmi predicate has no rate; caller\n"
            "    supplies the PMI premium per RESEARCH Open Question #1).\n"
            "  - FHA UFMIP is auto-financed into principal (D-03 + RESEARCH\n"
            "    §'FHA UFMIP Financing Convention'); response.financed_loan_amount\n"
            "    surfaces the financed total.\n"
            "\n"
            "Output:\n"
            "  Pretty-printed JSON AffordabilityResponse to stdout on success;\n"
            "  6-key Pydantic envelope on stderr for validation errors;\n"
            '  {"error": "..."} on file errors.\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the affordability request.",
    )
    args = parser.parse_args()

    # When invoked as a script (`python scripts/affordability.py ...`), Python puts
    # `scripts/` on sys.path, NOT the project root, so `from lib.affordability import ...`
    # fails with ModuleNotFoundError. Insert the project root (parent of this file's
    # directory) at sys.path[0] so the lazy-import below resolves. Cheap (one Path
    # operation + list insert) and runs only AFTER --help has already exited above,
    # so D-18 (--help fast) is unaffected.
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # Lazy-import per D-18 / D-13: heavy deps (numpy_financial, lib.affordability)
    # are NOT loaded on the --help fast path. argparse has already parsed by here,
    # so any --help / --version invocation has SystemExit'd above this line.
    from lib.affordability import (
        AffordabilityRequest,
        evaluate,
    )

    # MissingCountyDataError is raised by lib.rules.loan_type.classify when the
    # household location county_fips is not present in data/reference/conforming-limits-2026.yml
    # AND the loan amount exceeds the baseline ceiling. This is NOT a Pydantic
    # ValidationError — it propagates from inside evaluate() through evaluate_forward
    # / evaluate_reverse. We catch it explicitly to emit the Phase 3 D-19 6-key envelope
    # rather than letting Python emit a stack trace (BLOCKER fix; AFFD-08 contract;
    # T-04-02-03 mitigation).
    from lib.rules.loan_type import MissingCountyDataError
    from pydantic import TypeAdapter, ValidationError

    # File error → simple {"error": ...} envelope (Phase 3 contract; intentionally
    # not the 6-key shape — file-not-found / OSError surfaces predate the envelope
    # contract and are scoped out of WR-02 closure).
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

    # Pydantic validation via TypeAdapter (AffordabilityRequest is an
    # Annotated discriminated union, not a BaseModel subclass; TypeAdapter
    # is the v2 idiom for validating non-class types). Pydantic emits
    # structured JSON-readable errors via e.json(); pass through as JSON.
    try:
        adapter: TypeAdapter[Any] = TypeAdapter(AffordabilityRequest)
        request = adapter.validate_json(raw)
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2

    # Happy path: dispatch through public evaluate().
    #
    # MissingCountyDataError catch (BLOCKER fix; AFFD-08; T-04-02-03 mitigation):
    # lib.rules.loan_type.classify raises MissingCountyDataError (a ValueError
    # subclass) when household.location.county_fips is not present in
    # data/reference/conforming-limits-2026.yml AND loan_amount exceeds baseline.
    # This is NOT a Pydantic ValidationError; without an explicit catch the
    # exception escapes main() as a Python traceback on stderr — violating the
    # Phase 3 D-19 6-key envelope contract. Emit the standard envelope instead.
    try:
        response = evaluate(request)
    except MissingCountyDataError as e:
        from pydantic import VERSION as _pydantic_version

        _major_minor = ".".join(_pydantic_version.split(".")[:2])
        envelope = [
            {
                "type": "value_error",
                "loc": ["household", "location"],
                "msg": str(e),
                "input": request.household.location.model_dump(mode="json"),
                "url": f"https://errors.pydantic.dev/{_major_minor}/v/value_error",
                "ctx": {"class": "MissingCountyDataError"},
            }
        ]
        print(json.dumps(envelope), file=sys.stderr)
        return 2

    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
