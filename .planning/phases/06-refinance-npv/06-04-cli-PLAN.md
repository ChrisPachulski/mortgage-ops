---
phase: 06
plan: 04
type: execute
wave: 4
depends_on:
  - "06-00"
  - "06-01"
  - "06-02"
  - "06-03"
files_modified:
  - scripts/refi_npv.py
  - tests/test_refinance.py
autonomous: true
requirements:
  - REFI-08
tags:
  - phase-06
  - refinance-npv
  - cli
  - 6-key-envelope
must_haves:
  truths:
    - "scripts/refi_npv.py exists at project root, is executable as `python scripts/refi_npv.py --input <path>`"
    - "--help is fast (< 200ms) — no lib.refinance / numpy_financial / pydantic import on the help path (D-18 inheritance from Phase 3)"
    - "--help epilog cites references/refi-npv.md verbatim per SC-5 (string 'see references/refi-npv.md' must appear)"
    - "JSON-float pre-validation gate emits 6-key Pydantic envelope on stderr (D-19/WR-02 inheritance)"
    - "ValidationError from RefiCashflow sign-validator surfaces via TypeAdapter as 6-key envelope (path: cashflows[N].direction or amount)"
    - "Reuses scripts/_cli_helpers.py find_json_float_loc + make_decimal_type_envelope (Phase 5 factor — DO NOT duplicate)"
    - "Wave 0 stubs test_cli_smoke_subprocess_round_trip + test_cli_help_does_not_import_lib_refinance + test_cli_rejects_float_closing_costs + test_cli_rejects_float_discount_rate + test_cli_error_envelope_uniformity + test_cli_help_cites_references_refi_npv flip from xfail to PASS"
  artifacts:
    - path: "scripts/refi_npv.py"
      provides: "JSON-in/JSON-out CLI with WR-02 6-key envelope discipline; mirrors scripts/affordability.py shape verbatim"
      min_lines: 200
---

<objective>
Build `scripts/refi_npv.py` CLI mirroring `scripts/affordability.py` (Phase 4 Plan 04-05) verbatim. JSON-in/JSON-out, --input <path> only, lazy-import after argparse (D-18), 6-key Pydantic envelope on validation failure (WR-02), reuses Phase 5's `scripts/_cli_helpers.py`. Closes REFI-08.

The --help epilog (REFI-09 / SC-5 mandate) MUST cite `references/refi-npv.md` so a borrower running `python scripts/refi_npv.py --help` sees where to read the sign convention.
</objective>

<context>
@.planning/phases/06-refinance-npv/06-RESEARCH.md
@.planning/phases/06-refinance-npv/06-PATTERNS.md
@scripts/affordability.py
@scripts/amortize.py
@scripts/_cli_helpers.py
@lib/refinance.py
@tests/test_refinance.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create scripts/refi_npv.py</name>
  <files>scripts/refi_npv.py</files>
  <action>
    Create scripts/refi_npv.py — copy scripts/affordability.py verbatim and substitute:
    - prog name: "refi_npv"
    - description: "Compute refinance NPV (rate-and-term or cash-out) from the borrower's perspective with sign-convention rigor."
    - imports: `from lib.refinance import RefiRequest, evaluate` (replace AffordabilityRequest)
    - --help epilog: BOTH refi_kind shapes (rate_and_term + cash_out) per RESEARCH §"Pinned Oracles" examples; INCLUDE the SC-5-mandated citation:
      ```
      "Sign convention: outflows negative, savings positive."
      "See references/refi-npv.md for the borrower-perspective NPV formula,"
      "discount-rate-selection guidance, breakeven definitions, and the"
      "after-tax optional mode (IRS Pub 936 / RUL-11 inheritance)."
      ```
    - Module docstring: cite D-04 sign convention + WR-02 envelope contract identical to scripts/affordability.py:1-59 with AFFD → REFI substitution.
    - Skip the MissingCountyDataError special-case from scripts/affordability.py:148-238 — Phase 6 has no county dependency. Replace with simple ValidationError catch path.

    Final shape:
    ```python
    #!/usr/bin/env python3
    """JSON-in / JSON-out CLI for refinance NPV (REFI-08).

    Mirrors scripts/affordability.py per Phase 4 D-13. Same argparse skeleton,
    same --input <path> only, same lazy-import-AFTER-parse pattern (D-18 fast
    --help), same 6-key Pydantic envelope on validation errors (WR-02 inheritance).

    Sign convention (D-04 + SC-5): outflows negative, savings positive.
    See references/refi-npv.md.
    """
    from __future__ import annotations
    import argparse
    import json
    import sys
    from pathlib import Path

    def main() -> int:
        parser = argparse.ArgumentParser(
            prog="refi_npv",
            description=(
                "Compute refinance NPV (rate-and-term or cash-out) from the borrower's "
                "perspective with sign-convention rigor. See references/refi-npv.md."
            ),
            epilog=(
                # ... see acceptance_criteria for required strings ...
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--input", required=True, type=Path,
                            help="Path to JSON file containing the refi request.")
        args = parser.parse_args()

        # sys.path shim
        _project_root = str(Path(__file__).resolve().parent.parent)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)

        # Lazy import (D-18)
        from lib.refinance import RefiRequest, evaluate
        from pydantic import TypeAdapter, ValidationError
        from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

        try:
            raw = args.input.read_text()
        except FileNotFoundError as e:
            print(json.dumps({"error": f"input file not found: {e.filename}"}), file=sys.stderr)
            return 2
        except OSError as e:
            print(json.dumps({"error": f"could not read input file: {e}"}), file=sys.stderr)
            return 2

        # WR-02 float-gate
        float_hit = find_json_float_loc(raw)
        if float_hit is not None:
            loc, input_str = float_hit
            envelope = make_decimal_type_envelope(loc, input_str)
            print(json.dumps(envelope), file=sys.stderr)
            return 2

        try:
            adapter = TypeAdapter(RefiRequest)
            request = adapter.validate_json(raw)
        except ValidationError as e:
            print(e.json(), file=sys.stderr)
            return 2

        response = evaluate(request)
        print(response.model_dump_json(indent=2))
        return 0

    if __name__ == "__main__":
        sys.exit(main())
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python scripts/refi_npv.py --help | head -40 && grep -c 'references/refi-npv.md' scripts/refi_npv.py</automated>
  </verify>
  <acceptance_criteria>
    - `python scripts/refi_npv.py --help` exits 0 in < 200ms (D-18 fast)
    - `--help` output contains literal string `see references/refi-npv.md` (SC-5)
    - `--help` output contains literal phrase `outflows negative, savings positive` (SC-5)
    - `python scripts/refi_npv.py --help` does NOT output any error or import-time warning
    - `python -c "import ast; tree = ast.parse(open('scripts/refi_npv.py').read()); imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]; assert all(not (isinstance(i, ast.ImportFrom) and i.module and ('refinance' in i.module or 'numpy' in i.module or 'pydantic' in i.module)) for i in tree.body); print('D-18 OK')"` passes (no top-level lazy-target imports — they are inside main())
    - `grep -c 'from scripts._cli_helpers' scripts/refi_npv.py` returns 1
    - mypy + ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Flip 6 Wave-0 CLI stubs</name>
  <files>tests/test_refinance.py</files>
  <action>
    Replace xfail decorators with real bodies for these 6 tests:
    - test_cli_smoke_subprocess_round_trip — write a fixture JSON to tmp_path, invoke `subprocess.run([sys.executable, str(SCRIPT_PATH), "--input", str(p)])`, parse stdout JSON, assert refi_kind, npv, breakeven keys present.
    - test_cli_help_does_not_import_lib_refinance — invoke `subprocess.run(..., "--help")`, assert exit 0, assert no `lib.refinance` import via inspecting `sys.modules` post-run is impossible across processes; instead use the AST-static check from Task 1 acceptance.
    - test_cli_rejects_float_closing_costs — write JSON with `"closing_costs": 2000.00` (raw JSON float), invoke, assert exit 2, parse stderr as JSON, assert 6-key envelope shape with type=='decimal_type', loc=['closing_costs'].
    - test_cli_rejects_float_discount_rate — same shape with `"discount_rate_annual": 0.05`.
    - test_cli_error_envelope_uniformity — invoke twice (once float-gate triggered, once Pydantic ValidationError triggered via missing field), assert BOTH stderr outputs are JSON, both have the same 6-key set: {type, loc, msg, input, url, ctx}.
    - test_cli_help_cites_references_refi_npv — invoke --help, grep stdout for 'references/refi-npv.md' literal AND 'outflows negative, savings positive' literal.
  </action>
  <acceptance_criteria>
    - All 6 listed tests PASS
    - Earlier 5 Wave-1 tests still PASS
    - Other Wave-0 stubs (Wave 5/6) still XFAIL
    - Phase 5 baseline preserved (≥ 432 passed)
    - mypy + ruff clean
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-13 (Phase 4 inheritance): CLI uses --input <path> only; no stdin
- D-17 (Phase 3 inheritance): SCRIPT_PATH at project-root scripts/; Phase 10 relocates to .claude/skills/mortgage-ops/scripts/ via single SCRIPT_PATH-constant edit
- D-18 (Phase 3 inheritance): --help fast — lazy-import lib.refinance / numpy_financial AFTER argparse
- D-19 / WR-02 (Phase 3 inheritance): 6-key Pydantic envelope on stderr for ALL ValidationError-class boundary failures
- SC-5 mandate: --help cites references/refi-npv.md literally
- Reuse-not-duplicate: imports find_json_float_loc + make_decimal_type_envelope from scripts._cli_helpers (Phase 5 D-19 factor-extract)
</locked_decisions>

<verify_block>
- scripts/refi_npv.py executable; --help < 200ms; --help cites references/refi-npv.md
- 6 CLI Wave-0 stubs flipped to PASS
- 5 Wave-1 + Wave-3 model tests still PASS
- Phase 5 baseline preserved; ≥ 437 + 6 = 443 passed
- mypy --strict + ruff clean
</verify_block>

<deviation_rules>
- Rule-1: must reuse Phase 5 scripts/_cli_helpers.py (not re-implement). If the helper signatures don't fit Phase 6 needs, FIX the helper (Plan 06-04 may MODIFY scripts/_cli_helpers.py — but the modification is additive only, never breaks Phase 3/4/5 contract).
- Rule-2: SC-5 string literals ("see references/refi-npv.md", "outflows negative, savings positive") are LOAD-BEARING and asserted by tests. Do NOT paraphrase.
- Rule-3: hygiene-only deviations noted in SUMMARY.md.
</deviation_rules>

<success_criteria>
- scripts/refi_npv.py shipped, --help fast + cites references/refi-npv.md
- 6 CLI Wave-0 stubs flipped to PASS
- WR-02 envelope discipline preserved
- Phase 5 baseline held + Wave 1 + Wave 3 tests still PASS
- mypy --strict + ruff clean
</success_criteria>
