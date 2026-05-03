---
phase: 08
plan: 04
type: execute
wave: 4
depends_on: ["08-00", "08-01", "08-02", "08-03"]
files_added:
  - scripts/stress_test.py
  - scripts/points_breakeven.py
files_modified: []
autonomous: true
requirements: ["STRS-04", "PNTS-03"]
tags:
  - phase-08
  - stress-points
  - cli
must_haves:
  truths:
    - "scripts/stress_test.py exists, runs JSON-in / JSON-out via lib.stress.evaluate, supports --mode {rate-shock|income-shock|arm-reset} as advisory hint, supports --rates and --reductions list-shortcuts that synthesize the rates / reductions JSON fields"
    - "scripts/points_breakeven.py exists, runs JSON-in / JSON-out via lib.points.evaluate"
    - "Both CLIs use lazy-import after argparse (D-18 fast --help)"
    - "Both CLIs reuse scripts._cli_helpers.find_json_float_loc + make_decimal_type_envelope (no helper extension needed)"
    - "Both CLIs emit 6-key Pydantic envelope on stderr for ValidationError + float-gate hits (Phase 3 WR-02 closure)"
    - "ROADMAP SC-1 verbatim invocation: scripts/stress_test.py --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08 --input <file> works"
    - "ROADMAP SC-2 verbatim invocation: scripts/stress_test.py --mode income-shock --reductions 0.05,0.10,0.20 --input <file> works"
    - "STRS-04 + PNTS-03 closed at the CLI layer (fixture-driven assertions in Plan 08-05)"
    - "6 Wave 0 xfails flipped: 4 stress CLI + 2 points CLI"
---

<objective>
Ship the two Phase 8 CLIs as JSON-in / JSON-out wrappers around the Wave 2 / Wave 3 engines. Mirror scripts/arm_simulate.py exactly (lazy-import + float-gate + 6-key envelope) — the only innovations are:

1. `--mode` advisory hint in `scripts/stress_test.py` (the discriminator is in JSON; argparse just helps users construct the right shape)
2. `--rates 0.06,0.065,...` and `--reductions 0.05,0.10,...` argparse shortcuts that overlay the parsed list into the JSON's `rates` / `reductions` fields BEFORE Pydantic validation. ROADMAP SC-1 + SC-2 verbatim invocation pattern.

This plan closes STRS-04 and PNTS-03 at the CLI layer. Fixture-driven assertion closure happens in Plan 08-05.
</objective>

<context>
@.planning/phases/08-stress-points/08-PATTERNS.md (§Pattern 6, 7)
@scripts/arm_simulate.py (canonical Phase 5 CLI shape; lift verbatim)
@scripts/affordability.py (mode-discriminator CLI shape; lift --help epilog discipline)
@scripts/_cli_helpers.py (find_json_float_loc + make_decimal_type_envelope; reuse AS-IS)
@lib/stress.py (Wave 2 evaluate dispatcher)
@lib/points.py (Wave 3 evaluate dispatcher)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create scripts/stress_test.py</name>
  <files>scripts/stress_test.py</files>
  <action>
    Create scripts/stress_test.py mirroring scripts/arm_simulate.py with mode-aware argparse + list-shortcut overlays. Full file:

    ```python
    """Stress-test CLI: JSON-in / JSON-out wrapper around lib.stress.evaluate.

    Mirrors scripts/arm_simulate.py + scripts/affordability.py per Phase 5 D-07
    inheritance. JSON discriminator field 'mode' selects the sweep variant
    (rate-shock | income-shock | arm-reset); argparse --mode is an advisory hint
    that helps users construct the right JSON shape but does NOT override the
    discriminator (Pydantic v2 validates the JSON's mode field against the
    discriminated union).

    Two convenience shortcuts overlay parsed CLI lists into the JSON BEFORE
    Pydantic validation, so users can invoke the canonical ROADMAP SC-1 / SC-2
    forms without hand-editing JSON:

      --rates 0.06,0.065,0.07,0.075,0.08    overlays into request.rates (rate-shock mode)
      --reductions 0.05,0.10,0.20           overlays into request.reductions (income-shock mode)

    These shortcuts are FORBIDDEN for arm-reset mode (paths are too structured
    for a flat list-shortcut; users supply paths via JSON).

    Lazy-imports lib.stress + pydantic + numpy_financial AFTER argparse so
    --help is fast (D-18 / Phase 4 D-13 inherited). 6-key envelope on stderr
    for ValidationError + float-gate hits (Phase 3 WR-02 closure inherited).
    """

    from __future__ import annotations

    import argparse
    import json
    import sys
    from pathlib import Path


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
                '      "dti_threshold": "0.43"  // ATR/QM heuristic per RESEARCH §3.2\n'
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
                "All money/rate fields MUST be JSON strings (D-19; never JSON floats).\n"
                "ATR/QM threshold default (income-shock) is 0.43 — caller must specify.\n"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--input", required=True, type=Path,
                            help="Path to JSON file containing the stress request.")
        parser.add_argument("--mode", required=False,
                            choices=["rate-shock", "income-shock", "arm-reset"],
                            help="Advisory hint; the JSON's 'mode' field is authoritative.")
        parser.add_argument("--rates", required=False, type=_parse_decimal_list,
                            help="Comma-separated rates (overlays request.rates for rate-shock).")
        parser.add_argument("--reductions", required=False, type=_parse_decimal_list,
                            help="Comma-separated reductions (overlays request.reductions for income-shock).")
        args = parser.parse_args()

        _project_root = str(Path(__file__).resolve().parent.parent)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)

        from pydantic import TypeAdapter, ValidationError

        from lib.stress import StressRequest, evaluate
        from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

        raw = args.input.read_text()

        # Apply CLI shortcuts BEFORE the float-gate so the float-gate sees the final JSON.
        if args.rates is not None or args.reductions is not None:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                if args.rates is not None:
                    parsed["rates"] = args.rates
                if args.reductions is not None:
                    parsed["reductions"] = args.reductions
                raw = json.dumps(parsed)

        # JSON-float gate (D-19 + WR-02 closure).
        float_hit = find_json_float_loc(raw)
        if float_hit is not None:
            loc, input_str = float_hit
            envelope = make_decimal_type_envelope(loc, input_str)
            print(json.dumps(envelope), file=sys.stderr)
            return 2

        # Pydantic boundary validation. Discriminated union: TypeAdapter validates JSON
        # against StressRequest = Annotated[Rate|Income|Arm, Field(discriminator='mode')].
        try:
            request = TypeAdapter(StressRequest).validate_json(raw)
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
  <acceptance_criteria>
    - File scripts/stress_test.py exists with at least 100 lines
    - `python scripts/stress_test.py --help` exits 0 and prints usage including "rate-shock", "income-shock", "arm-reset"
    - `python -c "import sys; sys.path.insert(0, 'scripts'); import stress_test; print('OK')"` exits 0
    - mypy --strict scripts/stress_test.py exits 0
    - ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Create scripts/points_breakeven.py</name>
  <files>scripts/points_breakeven.py</files>
  <action>
    Create scripts/points_breakeven.py mirroring scripts/arm_simulate.py shape exactly (single-engine, no mode shortcuts):

    ```python
    """Discount-points breakeven CLI: JSON-in / JSON-out wrapper around lib.points.evaluate.

    Mirrors scripts/arm_simulate.py per Phase 5 D-07 inheritance. Single mode
    (no --mode arg); the JSON's 'mode' discriminator selects from_savings vs
    from_loans. Reports BOTH simple_breakeven_months AND npv_breakeven_months
    side-by-side per ROADMAP SC-4.

    Lazy-imports lib.points + pydantic + numpy_financial AFTER argparse (D-18).
    6-key envelope on stderr for ValidationError + float-gate (Phase 3 WR-02
    closure). discount_rate_annual is REQUIRED (no default — Phase 6 will pin
    project-wide convention; Plan 08-03 D-02 deferred coupling note).
    """

    from __future__ import annotations

    import argparse
    import json
    import sys
    from pathlib import Path


    def main() -> int:
        parser = argparse.ArgumentParser(
            prog="points_breakeven",
            description=(
                "Compute discount-points breakeven analysis. Reports BOTH simple "
                "and NPV-based breakeven months side-by-side, plus a buy/skip "
                "decision based on cumulative NPV at the hold horizon."
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
                '      "discount_rate_annual": "0.070000"  // REQUIRED; see references/points-breakeven.md for guidance\n'
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
                "All money/rate fields MUST be JSON strings (D-19).\n"
                "discount_rate_annual has NO default — caller chooses opportunity cost.\n"
                "  Recommended starting points (until Phase 6 lands):\n"
                "    - 0.000000 (zero opportunity cost; collapses NPV to simple)\n"
                "    - loan annual rate (paying-down-debt opportunity proxy)\n"
                "    - 0.050000 (rough US 10yr Treasury proxy)\n"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--input", required=True, type=Path,
                            help="Path to JSON file containing the points request.")
        args = parser.parse_args()

        _project_root = str(Path(__file__).resolve().parent.parent)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)

        from pydantic import TypeAdapter, ValidationError

        from lib.points import PointsRequest, evaluate
        from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope

        raw = args.input.read_text()

        float_hit = find_json_float_loc(raw)
        if float_hit is not None:
            loc, input_str = float_hit
            envelope = make_decimal_type_envelope(loc, input_str)
            print(json.dumps(envelope), file=sys.stderr)
            return 2

        try:
            request = TypeAdapter(PointsRequest).validate_json(raw)
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
  <acceptance_criteria>
    - File scripts/points_breakeven.py exists
    - `python scripts/points_breakeven.py --help` exits 0
    - mypy --strict scripts/points_breakeven.py exits 0
    - ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Flip 4 Wave 0 stress CLI xfails</name>
  <files>tests/test_stress.py</files>
  <action>
    Flip these 4 tests, removing their @pytest.mark.xfail decorators:

    1. `test_cli_stress_smoke_subprocess_round_trip_rate_shock` — write a minimal rate-shock JSON to tmp_path, invoke `subprocess.run([sys.executable, str(SCRIPT_PATH), "--input", str(json_path)], capture_output=True, text=True)`, assert `result.returncode == 0` and `json.loads(result.stdout)["mode"] == "rate-shock"` and `result.stdout.find("summary") < result.stdout.find("rows")` (SC-5 byte-order check on indented JSON).

    2. `test_cli_stress_rates_shortcut_arg_matches_roadmap_sc1` — write a minimal rate-shock JSON with `rates: []` to tmp_path, invoke with `--rates "0.06,0.065,0.07,0.075,0.08"`, assert response has 5 rows and `summary.table[0].label == "0.06"`.

    3. `test_cli_stress_help_does_not_import_lib_stress` — invoke `subprocess.run([sys.executable, str(SCRIPT_PATH), "--help"], ...)`, then verify (via `subprocess.run([sys.executable, "-c", "import sys; sys.modules.pop('lib.stress', None); sys.argv=[..., '--help']; import scripts.stress_test as m; m.main(); print('lib.stress' in sys.modules)"]`) that lib.stress is NOT imported during --help. Pattern from tests/test_arm.py::test_cli_help_does_not_import_lib_arm.

    4. `test_cli_stress_rejects_float_principal_with_6_key_envelope` — write a rate-shock JSON with `loan.principal: 400000.00` (JSON float, not string), invoke, assert returncode==2 and parse stderr as a JSON list whose [0] dict has all 6 keys: type, loc, msg, input, url, ctx.

    5. `test_cli_stress_error_envelope_uniformity` — write a rate-shock JSON missing the required `rates` field, invoke, assert returncode==2 and stderr is parseable as a JSON list whose [0] dict has all 6 keys identical-shape to the float-gate envelope.

    (Task lists 5 tests but Wave 0 stub count for "STRS-04 CLI" is 4 — the envelope-uniformity test is in the cross-cutting bucket. So flips total = 4 STRS-04 + 1 cross-cutting = 5. Adjust acceptance criteria accordingly.)
  </action>
  <acceptance_criteria>
    - `grep -c '@pytest.mark.xfail' tests/test_stress.py` returns 1 (was 6 after Plan 08-02; 5 more flipped here — including the cross-cutting envelope-uniformity stub)
    - `pytest tests/test_stress.py -v --tb=short` shows ≥12 passed, ≤1 xfailed
    - Full suite: ≥425 passed
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Flip 2 Wave 0 points CLI xfails</name>
  <files>tests/test_points.py</files>
  <action>
    Flip these 2 tests, removing their @pytest.mark.xfail decorators:

    1. `test_pnts_03_cli_points_subprocess_round_trip` — write a minimal from_savings JSON (points_cost=8000, monthly_savings=65.40, hold_period_months=240, discount_rate_annual=0.07) to tmp_path, invoke `scripts/points_breakeven.py --input <path>`, assert returncode==0 and parse stdout JSON has simple_breakeven_months==123 + npv_breakeven_months==160 + diverge==True.

    2. `test_pnts_03_cli_help_does_not_import_lib_points_and_rejects_float` — invoke `--help` (verify lib.points NOT in sys.modules); also write a from_savings JSON with monthly_savings as JSON float (e.g., 65.40), invoke, assert returncode==2 and stderr is a 6-key envelope.
  </action>
  <acceptance_criteria>
    - `grep -c '@pytest.mark.xfail' tests/test_points.py` returns 1 (was 3 after Plan 08-03; 2 more flipped)
    - `pytest tests/test_points.py -v --tb=short` shows ≥4 passed, 1 xfailed (the SC-4 fixture-pin test, flipped in Plan 08-05)
    - Full suite: ≥427 passed
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-04-01: --mode is an ADVISORY hint; the JSON's mode field is authoritative. Pydantic discriminated-union validation is the single source of truth. Avoids dual-discriminator drift.
- D-04-02: --rates and --reductions shortcuts overlay into JSON BEFORE Pydantic validation (and BEFORE the float-gate). Comma-split parser preserves strings (no float coercion at the argparse layer) so the float-gate semantics are unchanged.
- D-04-03: --rates and --reductions are ONLY meaningful for rate-shock and income-shock modes respectively. Misuse (e.g., --rates with arm-reset mode) silently overlays into a JSON field that doesn't exist in arm-reset's shape — Pydantic will reject with a clear extra=forbid violation. Documented in --help epilog.
- D-04-04: scripts/points_breakeven.py has NO --mode arg (single-engine; the JSON's mode discriminates from_savings vs from_loans). Simpler shape; mirrors scripts/amortize.py.
- D-04-05: discount_rate_annual REMAINS caller-supplied with no CLI default. The --help epilog text documents the recommended starting points (per 08-RESEARCH §5.5). Phase 6 will add a project-wide default via additive non-breaking edit to lib.points.
- D-04-06: TypeAdapter(StressRequest).validate_json(raw) is the canonical Pydantic v2 idiom for discriminated unions over JSON strings. Verified by Phase 4 affordability CLI which uses the same pattern.
- D-04-07: subprocess invocation only for tests (D-17 portability inheritance). Phase 10 relocates both scripts to .claude/skills/mortgage-ops/scripts/; only SCRIPT_PATH constants in tests update.
</locked_decisions>

<verify_block>
- Both CLIs exit 0 on --help; both fast (no lib.stress / lib.points imported during --help)
- Both CLIs round-trip a valid JSON request → JSON response on stdout
- Both CLIs emit 6-key envelope on stderr for float-gate hit + ValidationError
- ROADMAP SC-1 verbatim invocation works: `--mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08 --input <minimal.json>` returns 5 rows
- ROADMAP SC-2 verbatim invocation works: `--mode income-shock --reductions 0.05,0.10,0.20 --input <minimal.json>` returns 3 rows with breach flags
- 6 Wave 0 xfails flipped (4 stress CLI + 2 points CLI; the cross-cutting envelope-uniformity test is also flipped)
- mypy + ruff clean
</verify_block>

<deviation_rules>
- Rule 1: If TypeAdapter discriminated-union behavior produces a confusing error message for `--mode bogus`, document the workaround in SUMMARY.md (likely a custom argparse choices= validation runs first, but the JSON validation path is what matters).
- Rule 2: If --rates / --reductions shortcuts cause field-name conflicts when the source JSON ALREADY has the field, current behavior (last-write-wins from CLI) is intentional. Document in --help.
- Rule 3: If subprocess test latency is high (each CLI invocation is ~1 sec for cold imports), accept it — Phase 10's skill bundle will pre-warm. Tests are not on a hot path.
</deviation_rules>

<success_criteria>
- STRS-04 + PNTS-03 closed at the CLI layer (fixture-driven assertions live in Plan 08-05)
- 6 of 11 remaining Wave 0 xfails flipped after this plan (1 stress + 1 points + 4 fixture-driven left for Plan 08-05)
- mypy + ruff clean across both new scripts
- ROADMAP SC-1 + SC-2 verbatim invocation patterns work
- Phase 6 discount-rate coupling DEFERRED (caller-supplied; no CLI default)
</success_criteria>
