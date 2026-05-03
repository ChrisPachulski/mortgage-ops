#!/usr/bin/env python3
"""JSON-in / JSON-out CLI for refinance NPV (REFI-08).

Mirrors scripts/affordability.py per Phase 4 D-13 (CLI conventions). Same
argparse skeleton, same --input <path> only, same lazy-import-AFTER-parse
pattern (D-18 fast --help), same 6-key Pydantic envelope on validation
errors (Phase 3 D-19 + WR-02 closure shape; Phase 5 _cli_helpers reuse).

Sign convention (D-04 + ROADMAP SC-5): outflows negative, savings positive.
See references/refi-npv.md for the borrower-perspective NPV formula,
discount-rate-selection guidance, breakeven definitions (simple +
NPV-based), and the after-tax optional mode (IRS Pub 936 / RUL-11
inheritance).

Modes (D-02 discriminator `refi_kind`):
  rate_and_term — same principal, new rate/term; classic refi-to-save
                  (REFI-01 anchor; SC-1 sign-convention anchor)
  cash_out      — new principal > old balance; equity extraction
                  (REFI-02 anchor; SC-3 cash_proceeds + new_monthly_pi
                  + total_interest_delta surfaces)

Conventions documented in --help epilog:
  - All money/rate fields are JSON STRINGS (Pydantic v2 strict; JSON
    floats rejected at the boundary; same as Phase 3 D-19).
  - discount_rate_annual is REQUIRED (D-05; no default; mirrors Phase 4
    D-12 max_dti caller-supplied discipline). references/refi-npv.md
    documents three plausible defaults and recommends borrower
    after-tax marginal opportunity cost (5-7% typical).
  - closing_costs are paid out-of-pocket in v1 (D-12); not financed
    into the new loan.
  - Cash-out new principal = old_loan_balance + cash_out_amount; engine
    nets closing_costs from cash_proceeds at t=0 per industry CFPB
    Closing Disclosure convention.
  - PMI/MIP recalc on cash-out LTV change is OUT of v1 scope (D-08);
    callers can supply new_loan_monthly_pi_override (D-10) when they
    have externally computed the new monthly P&I including MI.
  - After-tax mode is opt-in (D-09); requires marginal_tax_rate AND
    filing_status when after_tax_mode=true. Cites
    lib.rules.irs_pub936.qualified_loan_limit (RUL-11) for the $750k
    post-2017 / $1M grandfathered cap.

Envelope Shape Contract (WR-02 closure inheritance from Phase 3):
  All ValidationError-class boundary surfaces emit a uniform 6-key
  Pydantic v2 e.json() envelope on stderr:
    [{"type": "<error_type>", "loc": [<JSON-pointer>],
      "msg": "<message>",     "input": "<offending_value>",
      "url": "<docs_url>",    "ctx": {"class": "<...>", ...}}]
  Canonical URL pattern: https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type}
  where MAJOR.MINOR is computed at runtime from pydantic.VERSION (Phase 3
  03-06 idiom; Pydantic 2.13→2.14 auto-aligns without code change).

  This applies to BOTH the pre-validation float-gate (which constructs
  an equivalent envelope manually via scripts._cli_helpers.make_decimal_type_envelope)
  AND native Pydantic ValidationError surfaces (e.json() pass-through).
  In particular: RefiCashflow's @model_validator _direction_sign_consistency
  (Plan 06-01; SC-4 anchor) raises a Pydantic ValidationError that
  TypeAdapter(RefiRequest).validate_json surfaces via e.json() — the
  same 6-key envelope shape downstream consumers parse uniformly.

  Out of scope for the 6-key contract: file-not-found and OSError surfaces
  use the simpler `{"error": "<message>"}` shape (predates the envelope
  contract; not Pydantic ValidationError surfaces). Argparse usage errors
  use argparse's stderr formatting, also out of scope.

Phase 9 / Phase 10 consumers parse stderr as one uniform JSON contract.

D-17 inheritance: Phase 6 keeps this script at project root. Phase 10
physically relocates it to .claude/skills/mortgage-ops/scripts/refi_npv.py
— only the path moves; test SCRIPT_PATH constants and SKILL.md routing
absorb the change.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="refi_npv",
        description=(
            "Compute refinance NPV (rate-and-term or cash-out) from the borrower's "
            "perspective with sign-convention rigor. See references/refi-npv.md."
        ),
        epilog=(
            "Input JSON shape (D-02 discriminator field 'refi_kind'):\n"
            "\n"
            "  RATE-AND-TERM REFI — same principal, new rate/term:\n"
            "    {\n"
            '      "refi_kind": "rate_and_term",\n'
            '      "old_loan_balance": "300000.00",\n'
            '      "old_annual_rate": "0.07",\n'
            '      "old_remaining_months": 300,\n'
            '      "new_annual_rate": "0.05",\n'
            '      "new_term_months": 300,\n'
            '      "closing_costs": "2000.00",\n'
            '      "discount_rate_annual": "0.05",\n'
            '      "analysis_horizon_months": null,        // optional; null = full new term\n'
            '      "after_tax_mode": false,                // opt-in (D-09)\n'
            '      "marginal_tax_rate": null,              // REQUIRED if after_tax_mode=true\n'
            '      "filing_status": null,                  // REQUIRED if after_tax_mode=true\n'
            '      "has_grandfathered_debt": false,        // pre-TCJA $1M cap if true\n'
            '      "new_loan_monthly_pi_override": null    // D-10 override\n'
            "    }\n"
            "\n"
            "  CASH-OUT REFI — new principal > old balance:\n"
            "    {\n"
            '      "refi_kind": "cash_out",\n'
            '      "old_loan_balance": "200000.00",\n'
            '      "old_annual_rate": "0.06",\n'
            '      "old_remaining_months": 240,\n'
            '      "new_annual_rate": "0.06",\n'
            '      "new_term_months": 360,\n'
            '      "closing_costs": "3000.00",\n'
            '      "cash_out_amount": "50000.00",\n'
            '      "discount_rate_annual": "0.05",\n'
            '      "analysis_horizon_months": 240,\n'
            '      "after_tax_mode": false,\n'
            '      "marginal_tax_rate": null,\n'
            '      "filing_status": null\n'
            "    }\n"
            "\n"
            "Sign convention: outflows negative, savings positive\n"
            "(see references/refi-npv.md for the borrower-perspective NPV formula,\n"
            "discount-rate-selection guidance, breakeven definitions, and the\n"
            "after-tax optional mode -- IRS Pub 936 / RUL-11 inheritance).\n"
            "\n"
            "Conventions:\n"
            '  - All money/rate fields MUST be JSON strings (e.g. "300000.00");\n'
            "    Pydantic v2 strict mode rejects JSON floats at the boundary\n"
            "    (D-19 / WR-02 6-key envelope on stderr).\n"
            "  - discount_rate_annual is REQUIRED (D-05; no default); see\n"
            "    references/refi-npv.md for guidance on the three plausible\n"
            "    defaults (borrower marginal opportunity cost / risk-free rate\n"
            "    / OLD loan rate; recommended: borrower after-tax marginal\n"
            "    opportunity cost, 5-7% typical).\n"
            "  - closing_costs paid out-of-pocket only in v1 (D-12); not\n"
            "    financed into the new loan principal.\n"
            "  - cash-out: new_principal = old_loan_balance + cash_out_amount;\n"
            "    closing_costs netted from cash_proceeds at t=0 per CFPB\n"
            "    Closing Disclosure convention.\n"
            "  - PMI/MIP recalc on LTV change OUT of v1 scope (D-08); use\n"
            "    new_loan_monthly_pi_override (D-10) when the cash-out LTV\n"
            "    breach requires externally-computed monthly P&I + MI.\n"
            "  - after_tax_mode opt-in (D-09); requires marginal_tax_rate AND\n"
            "    filing_status when true. Cites IRS Pub 936 / RUL-11 for the\n"
            "    qualified loan limit ($750k post-2017 / $1M grandfathered).\n"
            "\n"
            "Output:\n"
            "  Pretty-printed JSON RefiResponse to stdout on success;\n"
            "  6-key Pydantic envelope on stderr for validation errors\n"
            "  (including SC-4 RefiCashflow sign-validator violations);\n"
            '  {"error": "..."} on file errors.\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the refi request.",
    )
    args = parser.parse_args()

    # When invoked as a script (`python scripts/refi_npv.py ...`), Python puts
    # `scripts/` on sys.path, NOT the project root, so `from lib.refinance import ...`
    # fails with ModuleNotFoundError. Insert the project root (parent of this file's
    # directory) at sys.path[0] so the lazy-import below resolves. Cheap (one Path
    # operation + list insert) and runs only AFTER --help has already exited above,
    # so D-18 (--help fast) is unaffected.
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # Lazy-import per D-18 / D-13: heavy deps (numpy_financial, pydantic,
    # lib.refinance) are NOT loaded on the --help fast path. argparse has
    # already parsed by here, so any --help / --version invocation has
    # SystemExit'd above this line.
    #
    # scripts._cli_helpers is the Phase 5 factor-extract: single source of
    # truth for the JSON-float pre-validation gate + 6-key WR-02 envelope
    # shape. DO NOT duplicate find_json_float_loc / make_decimal_type_envelope
    # here — reuse the shipped helpers per Plan 06-04 deviation_rule Rule-1.
    from lib.refinance import RefiRequest, evaluate
    from pydantic import TypeAdapter, ValidationError
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

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
    # Pydantic 2.13 JSON concepts); the project's CLAUDE.md FND-01 + Phase 3
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
        print(json.dumps(envelope), file=sys.stderr)
        return 2

    # Pydantic validation via TypeAdapter (RefiRequest is an Annotated
    # discriminated union via Field(discriminator="refi_kind"), not a BaseModel
    # subclass; TypeAdapter is the v2 idiom for validating non-class types).
    # Pydantic emits structured JSON-readable errors via e.json(); pass through
    # as JSON.
    #
    # Note on SC-4 (RefiCashflow sign-validator): the engine constructs
    # RefiCashflow instances internally; if a downstream caller bypasses this
    # CLI and passes malformed cashflows directly to lib.refinance, the
    # @model_validator _direction_sign_consistency raises ValidationError —
    # surfaced here as the same 6-key envelope shape via e.json().
    try:
        adapter: TypeAdapter[Any] = TypeAdapter(RefiRequest)
        request = adapter.validate_json(raw)
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2

    # Happy path: dispatch through public evaluate() (D-02 discriminated-union
    # dispatcher; routes by refi_kind to evaluate_rate_and_term / evaluate_cash_out).
    response = evaluate(request)
    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
