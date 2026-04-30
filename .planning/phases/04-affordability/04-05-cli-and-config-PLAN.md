---
phase: 04-affordability
plan: 05
type: execute
wave: 5
depends_on: ["04-00", "04-01", "04-02", "04-03", "04-04"]
files_modified:
  - scripts/affordability.py
  - config/household.example.yml
autonomous: true
requirements: [AFFD-08, AFFD-09]
requirements_addressed: [AFFD-08, AFFD-09]
tags: [phase-4, affordability, cli, config, household-example, wave-5]

must_haves:
  truths:
    - "scripts/affordability.py exists at project root (D-13; Phase 3 D-17 — Phase 10 relocates to .claude/skills/mortgage-ops/scripts/)"
    - "scripts/affordability.py uses --input <path> only (Phase 3 D-18; no stdin input)"
    - "scripts/affordability.py lazy-imports lib.affordability + numpy_financial inside main() AFTER args=parser.parse_args() AND AFTER file-read gates (Phase 3 D-18 fast --help)"
    - "scripts/affordability.py emits the 6-key Pydantic envelope on ValidationError per Phase 3 D-19 / WR-02 closure shape: {type, loc, msg, input, url, ctx}"
    - "scripts/affordability.py URL field uses runtime-pinned pydantic.VERSION → https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type} (Phase 3 03-06 idiom)"
    - "scripts/affordability.py pre-validation float-gate via _find_json_float_loc; no fields legitimately accept JSON floats (D-13 inherits Phase 3 D-19)"
    - "scripts/affordability.py file-error envelope uses simpler {error: ...} shape per Phase 3 contract (file errors NOT 6-key)"
    - "scripts/affordability.py --help text documents BOTH forward and reverse mode JSON shape (per CONTEXT.md D-10)"
    - "scripts/affordability.py --help text documents UFMIP auto-financing convention (D-03 + RESEARCH recommendation)"
    - "scripts/affordability.py --help text documents monthly_pmi caller-supplied requirement for conventional > 80% LTV (RESEARCH Open Q#1)"
    - "scripts/affordability.py --help text documents state_fips + county_fips requirement on household.location (RESEARCH Open Q#2)"
    - "scripts/affordability.py --help text documents VA-only fields required when target_loan_type=='va' (RESEARCH Open Q#7)"
    - "scripts/affordability.py exit code: 0 on success; 2 on ValidationError, file-not-found, or MissingCountyDataError"
    - "scripts/affordability.py main() catches lib.rules.loan_type.MissingCountyDataError (a ValueError subclass raised by lib.rules.loan_type.classify; NOT a Pydantic ValidationError) AFTER ValidationError catch and emits a 6-key envelope with type='value_error', loc=['household','location'], ctx={'class':'MissingCountyDataError'} per Phase 3 D-19 (BLOCKER fix; AFFD-08 contract; threat T-04-02-03 mitigation)"
    - "config/household.example.yml extended in place per D-15 (NOT replaced)"
    - "config/household.example.yml header comment updated to remove the 'Phase 1 ships only this redacted example' hedge (Phase 4 is FINAL per AFFD-09)"
    - "config/household.example.yml location block adds state_fips: '53', county_fips: '033' (King WA defaults; RESEARCH Open Q#2)"
    - "config/household.example.yml household block adds size: 1 with docstring per D-15 (BLOCKER 2 fix; FULL household size including non-applicant dependents; drives USDA income-limit lookups; NOT inferred from len(applicants))"
    - "config/household.example.yml adds new top-level escrow block with property_tax_monthly, insurance_monthly, hoa_monthly Decimal-string defaults (D-01)"
    - "config/household.example.yml adds optional va block with region, family_size, actual_residual_income (D-15 + RESEARCH Open Q#7 — only required when target_loan_type=='va')"
    - "config/household.example.yml has field-level comments per D-15 (units, constraints, citation each field feeds)"
    - "config/household.example.yml is committed (System Layer; FND-04 hook does NOT match *.example.yml)"
    - "scripts/affordability.py preserves Phase 3 D-18 fast --help: lib.affordability and numpy_financial NOT in sys.modules after --help exits (verified by lazy-import test in Plan 04-06)"
  artifacts:
    - path: scripts/affordability.py
      provides: "JSON-in/JSON-out CLI with argparse + lazy-import + 6-key envelope"
      contains: "def main"
      min_lines: 220
    - path: config/household.example.yml
      provides: "FINAL Phase 4 schema (AFFD-09)"
      contains: "escrow:"
      min_lines: 70
  key_links:
    - from: scripts/affordability.py
      to: lib/affordability.py
      via: "lazy-import: from lib.affordability import AffordabilityRequest, evaluate"
      pattern: "from lib\\.affordability import"
    - from: scripts/affordability.py
      to: config/household.example.yml
      via: "user reads --help, copies example.yml to household.yml, fills values, JSON request points at it"
      pattern: "household\\.example\\.yml|household\\.yml"
---

<objective>
Ship the Phase 4 CLI surface (`scripts/affordability.py`) and FINAL `config/household.example.yml` schema (AFFD-09).

The CLI mirrors `scripts/amortize.py` exactly per CONTEXT.md D-13 (which says "Mirror Phase 3's CLI conventions"). Same argparse skeleton, same `--input <path>` only, same lazy-import-AFTER-parse pattern, same 6-key Pydantic envelope on stderr (Phase 3 D-19 + WR-02 closure), same pre-validation float-gate.

`config/household.example.yml` is extended in place per D-15: keeps Phase 1's existing block, adds `escrow:` (D-01) + optional `va:` (D-15 + RESEARCH Open Q#7) + state_fips + county_fips on location (RESEARCH Open Q#2 — required for County construction in Phase 2 predicates). Header comment updated to remove the "Phase 1 ships only this redacted example" hedge — Phase 4 is FINAL.

Purpose: ship the user-facing surface. The CLI is what `scripts/affordability.py` presents to a Phase 10 SKILL.md routing call; household.example.yml is what the user copies to household.yml and fills in.

Output:
- `scripts/affordability.py` (~220 lines; mirrors `scripts/amortize.py` 187 lines + adds dual-mode --help)
- `config/household.example.yml` (extended — keeps existing 36-line skeleton, adds ~35 lines of new fields + comments)

Decisions implemented: D-13 (CLI mirrors Phase 3), D-15 (household.example.yml FINAL), D-16 (User-Layer pre-commit discipline preserved — no changes to hook), D-03 (UFMIP auto-finance documented in --help), D-10 (request shape documented in --help), AFFD-08 + AFFD-09.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-affordability/04-CONTEXT.md
@.planning/phases/04-affordability/04-RESEARCH.md
@.planning/phases/04-affordability/04-PATTERNS.md
@.planning/phases/04-affordability/04-01-pydantic-models-PLAN.md
@.planning/phases/04-affordability/04-04-blocker-precedence-PLAN.md
@CLAUDE.md
@scripts/amortize.py
@config/household.example.yml
@lib/affordability.py
@DATA_CONTRACT.md

<interfaces>
<!-- scripts/amortize.py — exact mirror per D-13 -->

From scripts/amortize.py (Phase 3 03-06 final state):
```python
"""Envelope Shape Contract (WR-02 closure):
  All ValidationError-class boundary surfaces emit a uniform 6-key Pydantic v2
  e.json() envelope on stderr:
    [{"type": "<error_type>", "loc": [<JSON-pointer>],
      "msg": "<message>",     "input": "<offending_value>",
      "url": "<docs_url>",    "ctx": {"class": "<...>", ...}}]
"""

def _find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    # Walks parsed JSON and returns (loc-path, decimal-string) of first JSON float.
    # Used to emit pre-validation 6-key envelope BEFORE Pydantic permissively
    # coerces JSON numbers to Decimal.

def main() -> int:
    parser = argparse.ArgumentParser(prog="amortize", ...)
    parser.add_argument("--input", required=True, type=Path, ...)
    args = parser.parse_args()

    # Inject project root onto sys.path (script-mode invocation)
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # Lazy-import (D-18 fast --help)
    from lib.amortize import AmortizeRequest, build_schedule
    from pydantic import ValidationError

    # File error → simple {"error": ...} envelope
    try:
        raw = args.input.read_text()
    except FileNotFoundError as e:
        print(json.dumps({"error": f"input file not found: {e.filename}"}), file=sys.stderr)
        return 2

    # Pre-validation float gate → 6-key envelope
    float_hit = _find_json_float_loc(raw)
    if float_hit is not None:
        ...  # emit 6-key envelope
        return 2

    # Pydantic validation → 6-key envelope via e.json()
    try:
        request = AmortizeRequest.model_validate_json(raw)
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2

    # Happy path
    schedule = build_schedule(...)
    print(json.dumps({...}, indent=2))
    return 0
```

<!-- lib/affordability.py public surface (Plan 04-04 final state) -->

```python
def evaluate(request: ForwardModeRequest | ReverseModeRequest) -> AffordabilityResponse
# Public dispatcher. Plan 04-05 calls this AFTER AffordabilityRequest.model_validate_json.

# Note: AffordabilityRequest is the Annotated discriminated-union TYPE.
# At validation time use the standalone AffordabilityRequest discriminator OR
# pydantic.TypeAdapter(AffordabilityRequest).validate_json(raw).
```

<!-- config/household.example.yml — Phase 1 skeleton (current state, 36 lines) -->

```yaml
# config/household.example.yml
#
# COMMITTED SKELETON — copy to config/household.yml and fill in your real values.
# config/household.yml is in the User Layer (per DATA_CONTRACT.md): gitignored
# and never auto-updated by any system process.
#
# Phase 4 (Affordability) consumes this schema. Phase 1 ships only this redacted
# example so DATA_CONTRACT.md can cite a real path. Fields here are placeholders;
# Phase 4 (AFFD-09) will document the full schema with units and constraints.

household:
  location:
    state: "WA"
    county: "King"
    zip: "00000"

  applicants:
    - name: "Applicant A"
      gross_monthly_income: "0.00"
      credit_score: 0
    - name: "Applicant B"
      gross_monthly_income: "0.00"
      credit_score: 0

  monthly_debts:
    auto: "0.00"
    student_loans: "0.00"
    credit_cards: "0.00"
    other: "0.00"

  current_housing_payment: "0.00"
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create scripts/affordability.py — mirror scripts/amortize.py with dual-mode --help + AffordabilityRequest validator</name>
  <files>scripts/affordability.py</files>
  <read_first>
    - scripts/amortize.py (full file — exact-mirror analog per D-13)
    - lib/affordability.py (Plan 04-04 final state — confirm public `evaluate(request)` dispatcher exists)
    - .planning/phases/04-affordability/04-PATTERNS.md §"scripts/affordability.py"
    - .planning/phases/04-affordability/04-CONTEXT.md D-13 (CLI mirror), D-10 (request shape)
    - .planning/phases/04-affordability/04-RESEARCH.md §"FHA UFMIP Financing Convention" (D-03 recommendation to document in --help)
  </read_first>
  <action>
    Create `scripts/affordability.py`. Use `scripts/amortize.py` as a near-verbatim template; adapt only the script-specific bits (prog name, epilog, lazy-imported names, dispatcher call). Preserve EVERY pattern (envelope contract docstring, sys.path injection, float-gate, file-error envelope, lazy-import scope discipline).

    **Key adaptations from scripts/amortize.py:**

    1. **Module docstring (top of file):**
       ```python
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
         - target_loan_type=="va" requires household.va block (RESEARCH Open Q#7).
         - target_loan_type=="conventional" with LTV > 0.80 requires
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

       Phase 9 / Phase 10 consumers parse stderr as one uniform JSON contract.
       """
       ```

    2. **Imports (verbatim from scripts/amortize.py):**
       ```python
       from __future__ import annotations

       import argparse
       import json
       import sys
       from pathlib import Path
       from typing import Any
       ```

    3. **`_find_json_float_loc` function** — copy-paste verbatim from `scripts/amortize.py:72-122` (it's domain-agnostic; works on any JSON tree).

    4. **`main()` function** — adapt from `scripts/amortize.py:125-215`:

       ```python
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
                   "  - All money/rate fields MUST be JSON strings (e.g. \"400000.00\");\n"
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
                   "  {\"error\": \"...\"} on file errors.\n"
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

           # Inject project root onto sys.path for script-mode invocation
           # (Phase 3 03-03 idiom; preserves D-18 fast --help — runs only after parse).
           _project_root = str(Path(__file__).resolve().parent.parent)
           if _project_root not in sys.path:
               sys.path.insert(0, _project_root)

           # Lazy-import per D-18 / D-13: heavy deps (numpy_financial, lib.affordability)
           # are NOT loaded on the --help fast path.
           from pydantic import TypeAdapter, ValidationError

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

           # File error → simple {"error": ...} envelope (Phase 3 contract)
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

           # Pre-validation float gate (D-19 + WR-02 inheritance)
           float_hit = _find_json_float_loc(raw)
           if float_hit is not None:
               float_loc, float_input = float_hit
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
           # is the v2 idiom for validating non-class types).
           try:
               adapter = TypeAdapter(AffordabilityRequest)
               request = adapter.validate_json(raw)
           except ValidationError as e:
               print(e.json(), file=sys.stderr)
               return 2

           # Happy path: dispatch through public evaluate()
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
       ```

    Important notes:
    - `TypeAdapter(AffordabilityRequest)` is the Pydantic v2 idiom for validating
      `Annotated[A | B, Field(discriminator="mode")]`. The Plan 04-01 `AffordabilityRequest`
      is a TypeAlias, NOT a BaseModel. If Plan 04-01's `AffordabilityRequest` is named
      slightly differently (e.g., the executor refactored it into a BaseModel wrapper), the executor MUST update this section to call `AffordabilityRequest.model_validate_json(raw)` directly.
    - Use `argparse.RawDescriptionHelpFormatter` to preserve the multi-line epilog formatting (the Phase 3 amortize.py uses default formatter; Phase 4 epilog is multi-line and benefits from raw formatting).
    - The lazy-import of `pydantic.VERSION` lives INSIDE the float_hit branch (deepest possible scope; Phase 3 03-06 lazy-import-scope-minimization idiom).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python scripts/affordability.py --help &gt; /tmp/aff-help.txt 2&gt;&amp;1 &amp;&amp; grep -q "FORWARD MODE" /tmp/aff-help.txt &amp;&amp; grep -q "REVERSE MODE" /tmp/aff-help.txt &amp;&amp; grep -q "state_fips" /tmp/aff-help.txt &amp;&amp; grep -q "monthly_pmi" /tmp/aff-help.txt &amp;&amp; grep -q "UFMIP" /tmp/aff-help.txt &amp;&amp; echo OK</automated>
  </verify>
  <acceptance_criteria>
    - scripts/affordability.py exists with &gt;= 220 lines
    - scripts/affordability.py contains literal substring `prog="affordability"`
    - scripts/affordability.py contains literal substring `def _find_json_float_loc(`
    - scripts/affordability.py contains literal substring `from lib.affordability import`
    - scripts/affordability.py contains literal substring `evaluate(request)` (public dispatcher call)
    - scripts/affordability.py contains literal substring `TypeAdapter(AffordabilityRequest)` OR `AffordabilityRequest.model_validate_json(`
    - scripts/affordability.py contains literal substring `--input` (argparse flag per Phase 3 D-18)
    - scripts/affordability.py contains literal substring `https://errors.pydantic.dev/` (URL pattern)
    - scripts/affordability.py contains literal substring `_major_minor = ".".join(_pydantic_version.split(".")[:2])` (runtime-pinned URL version segment per Phase 3 03-06)
    - scripts/affordability.py contains literal substring `"type": "decimal_type"` (float-gate envelope)
    - scripts/affordability.py contains literal substring `"FORWARD MODE` AND `"REVERSE MODE` (D-10 dual-mode docs in epilog)
    - scripts/affordability.py contains literal substring `state_fips` (RESEARCH Open Q#2 documented in --help)
    - scripts/affordability.py contains literal substring `monthly_pmi` (RESEARCH Open Q#1 documented in --help)
    - scripts/affordability.py contains literal substring `UFMIP` (D-03 documented in --help)
    - scripts/affordability.py contains literal substring `target_loan_type=='va' requires household.va` OR equivalent text (RESEARCH Open Q#7)
    - scripts/affordability.py contains literal substring `_project_root not in sys.path` (sys.path injection per Phase 3 03-03)
    - `uv run python scripts/affordability.py --help` exits 0 (fast --help; no heavy imports)
    - `uv run python scripts/affordability.py --help` output contains both "FORWARD MODE" and "REVERSE MODE" sections
    - `uv run python scripts/affordability.py` (no args) exits 2 with argparse "required argument --input" error
    - `uv run python scripts/affordability.py --input /nonexistent` exits 2 with stderr containing `"error":`
    - scripts/affordability.py contains literal substring `from lib.rules.loan_type import MissingCountyDataError` (BLOCKER 1 fix)
    - scripts/affordability.py contains literal substring `except MissingCountyDataError as e:` (BLOCKER 1 fix)
    - scripts/affordability.py contains literal substring `"class": "MissingCountyDataError"` (envelope ctx field per Phase 3 D-19)
    - When invoked with a fixture whose `household.location.county_fips` is not in `data/reference/conforming-limits-2026.yml` AND `loan_amount > baseline`, `python scripts/affordability.py --input <fixture> 2>&1 >/dev/null | jq -r '.[0].ctx.class'` outputs `MissingCountyDataError` and exit code is 2 (BLOCKER 1 acceptance; pinned by Plan 04-06 fixture `forward_missing_county_data.json`)
    - `uv run mypy --strict scripts/affordability.py` exits 0
    - `uv run ruff check scripts/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    CLI scaffold mirrors Phase 3 amortize.py exactly; --help text documents both modes + all RESEARCH-amended fields (state_fips, monthly_pmi, VA-required, UFMIP financing); 6-key envelope on validation errors; file-error envelope simpler shape; mypy + ruff clean; D-18 fast --help preserved.
  </done>
</task>

<task type="auto">
  <name>Task 2: Extend config/household.example.yml in place per D-15 (FINAL Phase 4 schema; AFFD-09)</name>
  <files>config/household.example.yml</files>
  <read_first>
    - config/household.example.yml (current state — Phase 1 36-line skeleton)
    - .planning/phases/04-affordability/04-CONTEXT.md D-15 + D-16 (User-Layer protections)
    - .planning/phases/04-affordability/04-RESEARCH.md §"Open Questions" #2 (FIPS), #7 (VA required)
    - .planning/phases/04-affordability/04-PATTERNS.md §"config/household.example.yml" (full Phase 4 adaptation)
    - DATA_CONTRACT.md (User Layer / System Layer / Reference Layer separation; *.example.yml is System Layer)
  </read_first>
  <action>
    Edit `config/household.example.yml` IN PLACE (D-15: extend, don't replace). Keep ALL existing fields; modify per the following:

    **A. Update header comment block** (replace the Phase 1 hedge "Phase 1 ships only this redacted example so DATA_CONTRACT.md can cite a real path. Fields here are placeholders; Phase 4 (AFFD-09) will document the full schema with units and constraints." with Phase 4 final language):

    ```yaml
    # config/household.example.yml
    #
    # FINAL Phase 4 schema (AFFD-09). Copy to config/household.yml and fill in
    # your real values. config/household.yml is in the User Layer (per
    # DATA_CONTRACT.md): gitignored and never auto-updated by any system process;
    # protected by Phase 1's pre-commit hook scripts/hooks/block-user-layer.py
    # (FND-04). The hook's allowlist already permits *.example.yml, so this file
    # commits cleanly.
    #
    # Phase 4 (Affordability) consumes this schema to produce DTI / LTV / CLTV /
    # PITI calculations and reverse-affordability ("what loan amount can I
    # qualify for?"). All money fields are Decimal strings (CLAUDE.md money
    # discipline; ROUND_HALF_UP). Phase 2 predicates are invoked by full path
    # per Phase 2 D-08.
    ```

    **B. Update `location:` block** (add state_fips + county_fips per RESEARCH Open Q#2; preserve existing state, county, zip):

    ```yaml
    household:
      # Location — used by Phase 2 rules predicates (loan_type.classify and
      # usda.evaluate require a County(state_fips, county_fips, name) per
      # lib.rules.types.County). state_fips + county_fips are REQUIRED keys
      # per RESEARCH §"Open Questions for Planner" #2.
      location:
        state: "WA"                        # 2-letter state code (display only; not a regulatory key)
        state_fips: "53"                   # 2-digit FIPS (REQUIRED for County construction;
                                            # WA = 53; lookup at https://www.census.gov/library/reference/code-lists/ansi.html)
        county_fips: "033"                 # 3-digit FIPS (REQUIRED; King WA = 033;
                                            # consumed by lib.rules.loan_type.classify + lib.rules.usda.evaluate)
        county_name: "King"                # Display name (matches data/reference/conforming-limits-2026.yml entries; documentation only)
        zip: "00000"                       # ZIP code (display only; v2 PROP-02 may use for property-tax / insurance lookup)
    ```

    Note: existing `county: "King"` is RENAMED to `county_name: "King"` so the YAML matches the LocationFIPS Pydantic model in Plan 04-01. This is a breaking change for any existing User-Layer config/household.yml — but per CONTEXT.md the user has not actually filled in real values yet (Phase 4 is the first consumer); the example is the schema-of-record.

    **C. Update `applicants:` block** (add field-level docstrings per D-15; preserve existing structure):

    ```yaml
      # FULL household size — including non-applicant dependents (BLOCKER 2 fix; D-15).
      # int >= 1; drives USDA income-eligibility lookups via lib.rules.usda.evaluate
      # (which reads household_size to pick the right column of
      # data/reference/usda-income-limits.yml). NOT inferred from len(applicants) —
      # fail-loud, no inference (CLAUDE.md, CONTEXT.md).
      # Example: 2-applicant + 3-children household sets size: 5 even though
      # len(applicants) == 2. For a single-person household: size: 1.
      size: 1

      # Joint applicants — Phase 4 supports two-income households (D-06 + D-07).
      # Single-applicant case is supported via a list of length 1 (no special-cased
      # code path). For multi-applicant: income is summed (D-06); credit_score uses
      # min across applicants for Fannie LLPA + Freddie eligibility lookups (D-05).
      applicants:
        - name: "Applicant A"              # Display name only, not a legal identifier
          gross_monthly_income: "0.00"     # Decimal string; D-06 sums across applicants
          credit_score: 0                  # FICO 300-850; D-05 picks min across applicants for
                                            # Fannie LLPA + Freddie eligibility (caller supplies their
                                            # representative middle-of-three; mid-of-3 modeling out
                                            # of v1 scope per CONTEXT.md D-05)
        - name: "Applicant B"
          gross_monthly_income: "0.00"
          credit_score: 0
    ```

    **D. Preserve `monthly_debts:` block** (no schema change; just add the docstring header):

    ```yaml
      # Monthly debts that count toward back-end DTI (excluded from front-end DTI per
      # standard mortgage convention). Sum is added to PITI for back-end DTI ratio.
      monthly_debts:
        auto: "0.00"
        student_loans: "0.00"
        credit_cards: "0.00"
        other: "0.00"
    ```

    **E. Preserve current_housing_payment:**

    ```yaml
      # Optional: existing housing payment (rent or own) for affordability comparison.
      # Not consumed by Phase 4 math; reserved for Phase 8 stress-test "what-if-I-keep-renting"
      # comparisons.
      current_housing_payment: "0.00"
    ```

    **F. ADD new top-level `escrow:` block (D-01):**

    ```yaml
      # Phase 4 escrow inputs (D-01) — caller-supplied PITI components.
      # Caller enters monthly $ directly; ZIP / county-keyed % rates deferred to v2
      # per CONTEXT.md Deferred Items "% rate-based PITI inputs". User reads the
      # Loan Estimate (LE) for these values. Quantize via Decimal-string per
      # CLAUDE.md money discipline.
      escrow:
        property_tax_monthly: "0.00"       # Decimal string; consumed by AFFD-04 PITI composition
        insurance_monthly: "0.00"          # Decimal string; consumed by AFFD-04 PITI composition
        hoa_monthly: "0.00"                # Decimal string; default "0.00" when no HOA
    ```

    **G. ADD optional `va:` block (D-15 + RESEARCH Open Q#7):**

    ```yaml
      # Phase 4 VA-only inputs (D-15 optional; REQUIRED at request boundary when
      # target_loan_type=="va" per RESEARCH Open Question #7).
      # AffordabilityRequest's @model_validator(mode="after") raises ValidationError
      # if target_loan_type=="va" and this block is absent.
      #
      # When using this template for a non-VA loan, DELETE this block (Pydantic
      # extra="forbid" accepts the absence).
      va:
        region: "west"                     # Literal["northeast","midwest","south","west"] —
                                            # consumed by lib.rules.va_residual_income.evaluate;
                                            # produces the stable citation
                                            # f"VA-RESIDUAL-{REGION_UPPER}-FAMILY-{family_size}"
                                            # per Phase 2 D-11 (DO NOT format-drift; ROADMAP SC-3
                                            # uses "VA-RESIDUAL-WEST-FAMILY-4" verbatim).
        family_size: 4                     # int (>=1; sizes >5 add per_extra_member_increment
                                            # per data/reference/va-residual-income.yml)
        actual_residual_income: "0.00"     # Decimal string; current household residual income
                                            # to compare against the VA M26-7 table minimum.
                                            # Below the minimum → blocked_by="VA-RESIDUAL-{REGION}-FAMILY-{N}".
    ```

    The full result should be ~75-90 lines. Do NOT modify the User-Layer pre-commit hook (D-16; FND-04). The file is committed per System Layer convention (DATA_CONTRACT.md).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "
import yaml
with open('config/household.example.yml') as f:
    data = yaml.safe_load(f)
hh = data['household']
# Existing fields preserved
assert 'location' in hh
assert 'applicants' in hh
assert 'monthly_debts' in hh
# New fields per D-15
assert 'escrow' in hh, 'escrow block missing (D-01)'
assert 'property_tax_monthly' in hh['escrow']
assert 'insurance_monthly' in hh['escrow']
assert 'hoa_monthly' in hh['escrow']
# FIPS per RESEARCH Open Q#2
assert 'state_fips' in hh['location'], 'state_fips missing (RESEARCH Open Q#2)'
assert 'county_fips' in hh['location'], 'county_fips missing'
assert hh['location']['state_fips'] == '53'
assert hh['location']['county_fips'] == '033'
# BLOCKER 2 fix: household.size required
assert 'size' in hh, 'household.size missing (BLOCKER 2)'
assert isinstance(hh['size'], int) and hh['size'] >= 1, 'household.size must be int >= 1'
# Optional VA block present per D-15
assert 'va' in hh, 'va block missing (D-15 + RESEARCH Open Q#7 optional)'
assert hh['va']['region'] == 'west'
assert hh['va']['family_size'] == 4
print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - config/household.example.yml is &gt;= 70 lines
    - config/household.example.yml contains literal substring `state_fips:` (RESEARCH Open Q#2)
    - config/household.example.yml contains literal substring `size: 1` (BLOCKER 2 fix; full-household-size field)
    - config/household.example.yml contains literal substring `FULL household size` (docstring per BLOCKER 2)
    - config/household.example.yml contains literal substring `county_fips:` (RESEARCH Open Q#2)
    - config/household.example.yml contains literal substring `state_fips: "53"` (King WA default)
    - config/household.example.yml contains literal substring `county_fips: "033"` (King WA)
    - config/household.example.yml contains literal substring `escrow:` (D-01 new block)
    - config/household.example.yml contains literal substring `property_tax_monthly:`
    - config/household.example.yml contains literal substring `insurance_monthly:`
    - config/household.example.yml contains literal substring `hoa_monthly:`
    - config/household.example.yml contains literal substring `va:` (D-15 optional VA block)
    - config/household.example.yml contains literal substring `region: "west"`
    - config/household.example.yml contains literal substring `family_size: 4`
    - config/household.example.yml contains literal substring `actual_residual_income:`
    - config/household.example.yml contains literal substring `gross_monthly_income:` (preserved Phase 1 field)
    - config/household.example.yml contains literal substring `credit_score:` (preserved Phase 1 field)
    - config/household.example.yml contains literal substring `monthly_debts:` (preserved Phase 1 field)
    - config/household.example.yml does NOT contain literal substring `Phase 1 ships only this redacted` (Phase 4 hedge removed per AFFD-09)
    - config/household.example.yml contains literal substring `FINAL Phase 4 schema` (AFFD-09 final-state header)
    - YAML parses cleanly via `uv run python -c "import yaml; yaml.safe_load(open('config/household.example.yml'))"`
    - Pre-commit hook scripts/hooks/block-user-layer.py does NOT match config/household.example.yml — verifiable: `git add config/household.example.yml &amp;&amp; pre-commit run --files config/household.example.yml` exits 0 (User-Layer hook does not fire on .example. files per D-16)
  </acceptance_criteria>
  <done>
    config/household.example.yml is the FINAL Phase 4 schema; existing Phase 1 fields preserved; D-15 new fields (escrow, va) added with field-level comments; FIPS codes added per RESEARCH Open Q#2; YAML parses cleanly; User-Layer hook unaffected (only *.example.yml allowlisted).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| JSON file → AffordabilityRequest.model_validate_json | Untrusted JSON file from caller crosses here; Pydantic + float-gate enforce shape |
| --help text → user reading | Documentation IS the contract — drift between --help and actual schema is a real bug surface |
| User Layer config/household.yml → System Layer scripts/affordability.py | Read-only; pre-commit hook FND-04 enforces no system-process writes |
| *.example.yml committable surface | Pre-commit hook MUST allowlist this file (D-16); modification hardens the contract Phase 5+ ARM/refi will rely on |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-05-01 | Tampering | JSON float coerced to Decimal silently (Pydantic permissive JSON) | mitigate | _find_json_float_loc pre-validation gate emits 6-key envelope BEFORE Pydantic; lifted verbatim from Phase 3 03-03 + 03-06; all Phase 4 money/rate fields are JSON strings (no field legitimately accepts JSON float) |
| T-04-05-02 | Tampering | --help text drift from actual schema | mitigate | Acceptance criteria pin substrings: "FORWARD MODE", "REVERSE MODE", state_fips, monthly_pmi, UFMIP, VA-required documentation in epilog; Plan 04-06 ships test that asserts subprocess --help output contains these substrings |
| T-04-05-03 | Tampering | UFMIP financing convention silently changed (D-03 drift between code and --help) | mitigate | --help epilog explicitly states "FHA UFMIP is auto-financed into principal" matching D-03 code path in Plan 04-02; Plan 04-06 fixture for FHA case asserts response.financed_loan_amount == loan_amount + UFMIP exactly |
| T-04-05-04 | Tampering | Lazy-import scope leak (D-18 fast --help broken) | mitigate | Inherits Phase 3 D-18 structural verifier; Plan 04-06 ships subprocess test that asserts lib.affordability and numpy_financial NOT in sys.modules after --help (mirrors test_cli_help_does_not_import_lib_amortize from Phase 3 03-04) |
| T-04-05-05 | Tampering | Pre-commit hook accidentally fires on *.example.yml | mitigate | scripts/hooks/block-user-layer.py allowlist already permits *.example.yml (CONTEXT.md D-16); no hook change needed; verifiable: git status + pre-commit run --files config/household.example.yml exits 0 |
| T-04-05-06 | Tampering | User-Layer write (a system process accidentally writes config/household.yml) | mitigate | This plan does NOT touch config/household.yml; only config/household.example.yml; FND-04 hook still in place |
| T-04-05-07 | Information Disclosure | --help text leaks regulatory citations | accept | All citations are public regulatory sources (HUD ML 2023-05, VA M26-7, CFPB QM); no PII surface |
| T-04-05-08 | Tampering | TypeAdapter(AffordabilityRequest) doesn't exist if Plan 04-01 named the union differently | mitigate | Action body explicitly documents the fallback (`AffordabilityRequest.model_validate_json(raw)` direct call if Plan 04-01 made it a class); executor verifies which form Plan 04-01 produced before committing the import line |
</threat_model>

<verification>
After both tasks complete:

```bash
# CLI: --help works fast (D-18)
time uv run python scripts/affordability.py --help

# CLI: --help text covers both modes + all RESEARCH amendments
uv run python scripts/affordability.py --help | grep -c "FORWARD MODE"  # >= 1
uv run python scripts/affordability.py --help | grep -c "REVERSE MODE"  # >= 1
uv run python scripts/affordability.py --help | grep -c "state_fips"    # >= 1
uv run python scripts/affordability.py --help | grep -c "monthly_pmi"   # >= 1
uv run python scripts/affordability.py --help | grep -c "UFMIP"         # >= 1

# CLI: file-not-found envelope shape
uv run python scripts/affordability.py --input /nonexistent 2>&1 >/dev/null | grep -q '"error":'

# YAML schema parses
uv run python -c "import yaml; yaml.safe_load(open('config/household.example.yml'))"

# YAML extension complete
grep -c "escrow:" config/household.example.yml      # >= 1
grep -c "state_fips" config/household.example.yml   # >= 1
grep -c "va:" config/household.example.yml          # >= 1

# mypy + ruff clean
uv run mypy --strict scripts/affordability.py
uv run ruff check scripts/affordability.py

# Pre-commit hook does NOT fire on *.example.yml (D-16)
git add config/household.example.yml
pre-commit run --files config/household.example.yml

# Full suite still green; Phase 4 stubs still xfail; CLI happy-path validated end-to-end in Plan 04-06
uv run pytest -x
```
</verification>

<success_criteria>
- [ ] `scripts/affordability.py` exists at project root, mirrors `scripts/amortize.py` (Phase 3 D-13 inheritance)
- [ ] `--help` exits 0 and is fast (D-18: lib.affordability + numpy_financial NOT loaded; verified in Plan 04-06)
- [ ] `--help` text documents BOTH forward and reverse modes (D-10)
- [ ] `--help` text documents UFMIP auto-finance (D-03), monthly_pmi caller-supplied (Open Q#1), state_fips/county_fips (Open Q#2), VA-required (Open Q#7)
- [ ] 6-key Pydantic envelope on validation errors (Phase 3 D-19 / WR-02 closure)
- [ ] `{"error": ...}` envelope on file errors (Phase 3 contract)
- [ ] Pre-validation float-gate via _find_json_float_loc (Phase 3 D-19 inheritance)
- [ ] Public `evaluate()` dispatcher consumed via `from lib.affordability import evaluate`
- [ ] `config/household.example.yml` extended in place per D-15 (FINAL schema; AFFD-09)
- [ ] state_fips + county_fips added to location block (RESEARCH Open Q#2)
- [ ] New escrow + optional va blocks added with field-level comments (D-01 + D-15)
- [ ] Header hedge "Phase 1 ships only this redacted example" removed (Phase 4 final per AFFD-09)
- [ ] FND-04 pre-commit hook does NOT fire on the modified *.example.yml (D-16)
- [ ] mypy --strict + ruff clean
- [ ] Phase 1/2/3 regressions: zero
</success_criteria>

<output>
After completion, create `.planning/phases/04-affordability/04-05-SUMMARY.md` per the standard template. Plan 04-06 (tests + fixtures) consumes the CLI surface for subprocess invocation.

## Breaking Change

Phase 1's `config/household.example.yml` field `location.county` is renamed to
`location.county_name` to align with `lib.rules.types.County`'s field name and
the new `LocationFIPS` Pydantic model in Plan 04-01. This is a breaking change
for any User-Layer `config/household.yml` that already exists. However, Phase 4
is the first phase that ships a non-redacted `config/household.example.yml`
(per D-15: Phase 4 is FINAL); the Phase 1 skeleton was a redacted placeholder
with all-zero values, so no real `config/household.yml` should exist yet.
Downstream phases (5+ ARM, 6 refi, 8 stress) inheriting this schema should be
aware that `location.county_name` (not `location.county`) is the canonical key.
(W4 fix.)
</output>
