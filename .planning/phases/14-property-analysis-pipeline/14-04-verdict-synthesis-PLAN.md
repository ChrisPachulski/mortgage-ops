---
phase: 14
plan: 04
plan_id: 14-04
slug: verdict-synthesis
type: execute
wave: 2
depends_on:
  - 14-01
  - 14-02
files_modified:
  - lib/property_verdict.py
  - tests/test_property_verdict.py
autonomous: true
requirements:
  - VERD-01
nyquist_compliant: true
tags:
  - verdict
  - blocker-cascade
  - citation-coverage

must_haves:
  truths:
    - "lib/property_verdict.py ships VERDICT_* Final[str] constants per RESEARCH Pitfall 7 prefix discipline: VERDICT_NO_GO_DTI_ALL_PROGRAMS, VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP, VERDICT_WATCH_FHA_MIP_BURDEN, VERDICT_WATCH_STRESS_INCOME_FAIL, VERDICT_GO."
    - "synthesize(matrix, stress, household, profile) returns a Verdict implementing the D-14-VERDICT-01..04 cascade in first-match-wins order: NO_GO if no eligible at any DP, NO_GO if no eligible at preferred DP, WATCH if income-shock fails any eligible (D-14-VERDICT-02), WATCH if FHA-only AND MIP > $300 (D-14-VERDICT-01), GO otherwise (D-14-VERDICT-03)."
    - "Every Verdict.reasons[].predicate_code is one of the VERDICT_* constants OR a verbatim cell blocker_reasons string; every reason carries a computed_value string (D-14-VERDICT-04)."
    - "tests/test_property_verdict.py contains test_verdict_code_citation_coverage that introspects lib.property_verdict for VERDICT_* constants and asserts every constant is emitted by at least one cascade-level unit test in this same file (fixture-based coverage tightens in Plan 14-06)."
  artifacts:
    - path: "lib/property_verdict.py"
      provides: "synthesize() + VERDICT_* constants + _MIP_BURDEN_THRESHOLD"
      contains: "def synthesize"
    - path: "tests/test_property_verdict.py"
      provides: "VERD-01 cascade tests + citation-coverage meta-test"
      contains: "def test_verdict_code_citation_coverage"
  key_links:
    - from: "lib/property_verdict.py:synthesize"
      to: "lib.property_analysis.Verdict, VerdictReason"
      via: "import Verdict + VerdictReason from lib.property_analysis"
      pattern: "from lib\\.property_analysis import.*Verdict"
    - from: "tests/test_property_verdict.py:test_verdict_code_citation_coverage"
      to: "lib.property_verdict (VERDICT_* constants)"
      via: "grep-style introspection mirrors tests/test_affordability.py:test_blocked_by_citation_coverage"
      pattern: "VERDICT_"
---

<objective>
Ship the verdict synthesis module. Closes VERD-01.

The module:
1. Declares VERDICT_* Final[str] constants per Pitfall 7 prefix discipline.
2. Implements `synthesize(matrix, stress, household, profile) -> Verdict` using the 5-level cascade per D-14-VERDICT-01..04.
3. Ships the falsifiable-reason discipline: every VerdictReason carries both predicate_code (one of the VERDICT_* constants OR a verbatim cell-level blocker code) AND computed_value (string).
4. Mirrors lib.affordability._evaluate_blockers first-match-wins cascade (PATTERNS.md L374-422).

Companion tests cover every cascade level (5 named tests), reason format compliance (1 named test), and the citation-coverage meta-test (1 named test) — total ~10 named tests in tests/test_property_verdict.py.

Output: ~250 LOC in lib/property_verdict.py + ~350 LOC in tests/test_property_verdict.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md
@.planning/phases/14-property-analysis-pipeline/14-RESEARCH.md
@.planning/phases/14-property-analysis-pipeline/14-PATTERNS.md
@.planning/phases/14-property-analysis-pipeline/14-01-SUMMARY.md
@.planning/phases/14-property-analysis-pipeline/14-02-SUMMARY.md
@CLAUDE.md
@lib/property_analysis.py
@lib/affordability.py
@lib/household.py
@lib/profile.py
@tests/test_affordability.py

<interfaces>
From lib/property_analysis.py (Plan 14-02):
- class ProgramResult — fields: program, down_payment_pct, monthly_mi, piti, dti_back, ltv, eligible, blocker_reasons, eligible_reasons.
- class DownPaymentMatrix — cells, programs_present, down_payment_pcts.
- class StressBlock — preferred_down_payment_pct, rows.
- class StressRow — program, stress_kind ("rate_shock" | "income_shock" | "arm_reset"), baseline_piti, stressed_piti, stressed_dti_back, breaches_dti_ceiling, blocker_reasons.
- class Verdict — level ("GO" | "WATCH" | "NO_GO"), headline_reason, reasons[].
- class VerdictReason — predicate_code, computed_value, program, dp_pct.

From lib/affordability.py L300-331 — BLOCKED_BY_* Final[str] constants idiom.
From lib/affordability.py L1207-1380 — _evaluate_blockers cascade pattern (first-match-wins, model_copy on frozen models).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create lib/property_verdict.py with VERDICT_* constants + synthesize() cascade</name>
  <files>lib/property_verdict.py</files>
  <read_first>
    - lib/property_analysis.py (Plan 14-02 output — imports Verdict, VerdictReason, ProgramResult, DownPaymentMatrix, StressBlock, StressRow)
    - lib/affordability.py L300-331 (BLOCKED_BY_* constants idiom — Final[str] + prefix discipline)
    - lib/affordability.py L1207-1380 (_evaluate_blockers cascade pattern)
    - lib/household.py
    - lib/profile.py
    - .planning/phases/14-property-analysis-pipeline/14-CONTEXT.md (D-14-VERDICT-01..04 locked decisions)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L880-968 (Code Example 5 — verbatim synthesize() body)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L598-622 (Pitfall 7 — VERDICT_* constants discipline)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L328-455 (lib/property_verdict.py pattern with verbatim cascade idioms)
  </read_first>
  <behavior>
    - Behavior 1: All 5 VERDICT_* constants importable plus _MIP_BURDEN_THRESHOLD. Exact string values:
        - VERDICT_NO_GO_DTI_ALL_PROGRAMS == "DTI-CEILING-ALL-PROGRAMS"
        - VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP == "NO-ELIGIBLE-AT-PREFERRED-DP"
        - VERDICT_WATCH_FHA_MIP_BURDEN == "MIP-BURDEN-FHA"
        - VERDICT_WATCH_STRESS_INCOME_FAIL == "STRESS-INCOME-SHOCK"
        - VERDICT_GO == "GO-ALL-GREEN"
        - _MIP_BURDEN_THRESHOLD == Decimal("300.00")
    - Behavior 2: Cascade level 1 — when no cell in matrix.cells has eligible=True, returns Verdict(level="NO_GO", reasons=[VerdictReason(predicate_code=VERDICT_NO_GO_DTI_ALL_PROGRAMS, computed_value=str(min_dti_across_cells))]).
    - Behavior 3: Cascade level 2 — when there is at least one eligible cell at SOME DP but none at preferred DP, returns Verdict(level="NO_GO", reasons=[VerdictReason(predicate_code=VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP, computed_value=str(preferred), dp_pct=preferred)]).
    - Behavior 4: Cascade level 3 (D-14-VERDICT-02) — when at least one eligible-at-preferred-DP program has a stress row with stress_kind="income_shock" and breaches_dti_ceiling=True, returns Verdict(level="WATCH", reasons=[VerdictReason(predicate_code=VERDICT_WATCH_STRESS_INCOME_FAIL, computed_value=str(stressed_dti_back), program=row.program) for each failing row]).
    - Behavior 5: Cascade level 4 (D-14-VERDICT-01 + D-14-VERDICT-03) — when ALL eligible-at-preferred-DP cells are FHA30 AND fha_cell.monthly_mi > Decimal("300.00"), returns Verdict(level="WATCH", reasons=[VerdictReason(predicate_code=VERDICT_WATCH_FHA_MIP_BURDEN, computed_value=str(fha_cell.monthly_mi), program="FHA30", dp_pct=preferred)]).
    - Behavior 6: Cascade level 5 (D-14-VERDICT-03 GO-wins) — when at least one non-FHA program is eligible at preferred DP AND no income-shock failures occurred, returns Verdict(level="GO", reasons=[VerdictReason(predicate_code=VERDICT_GO, computed_value=str(count_of_non_fha_eligible))]).
    - Behavior 7: GO-wins-over-MIP-burden (D-14-VERDICT-03) — when a non-FHA program is eligible at preferred DP, FHA MIP burden does NOT downgrade to WATCH; verdict is GO.
    - Behavior 8: Inputs are NEVER mutated; all returned Pydantic instances are fresh constructions.
    - Behavior 9: Empty matrix.cells (degenerate) returns NO_GO with VERDICT_NO_GO_DTI_ALL_PROGRAMS; min(...) over empty iterable uses default=Decimal("0").
    - Behavior 10: synthesize() is a pure function — no I/O, no global state reads, no time.now() calls.
  </behavior>
  <action>
    Create `lib/property_verdict.py` mirroring lib/affordability.py module-header style and the L1207-1380 cascade idiom.

    Required module structure:

    1. `from __future__ import annotations` first line.
    2. Imports:
       - `from decimal import Decimal`
       - `from typing import Final`
       - `from lib.property_analysis import DownPaymentMatrix, ProgramResult, StressBlock, StressRow, Verdict, VerdictReason`
       - `from lib.household import Household`
       - `from lib.profile import Profile`
    3. Module docstring citing D-14-VERDICT-01..04 + D-14-MODELS-03 + Pitfall 7 prefix discipline (no AI-attribution markers per CLAUDE.md global rule).

    4. Module-level Final constants block — Pitfall 7 prefix discipline:
       - `VERDICT_NO_GO_DTI_ALL_PROGRAMS: Final[str] = "DTI-CEILING-ALL-PROGRAMS"`
       - `VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP: Final[str] = "NO-ELIGIBLE-AT-PREFERRED-DP"`
       - `VERDICT_WATCH_FHA_MIP_BURDEN: Final[str] = "MIP-BURDEN-FHA"`
       - `VERDICT_WATCH_STRESS_INCOME_FAIL: Final[str] = "STRESS-INCOME-SHOCK"`
       - `VERDICT_GO: Final[str] = "GO-ALL-GREEN"`
       - `_MIP_BURDEN_THRESHOLD: Final[Decimal] = Decimal("300.00")` (D-14-VERDICT-01 policy choice; Assumption A1)

    5. `synthesize(matrix, stress, household, profile) -> Verdict` function implementing the cascade exactly per RESEARCH Code Example 5 (L898-968). Each cascade level uses `if <condition>: return Verdict(...)` with early-return — first-match-wins precedence (PATTERNS.md L426-432).

       Cascade implementation:
       - Compute `preferred = household.preferred_down_payment_pct`.
       - Compute `cells_at_preferred = [c for c in matrix.cells if c.down_payment_pct == preferred]`.
       - Compute `eligible_at_preferred = [c for c in cells_at_preferred if c.eligible]`.
       - Compute `non_fha_eligible = [c for c in eligible_at_preferred if c.program != "FHA30"]`.
       - **Level 1**: `if not any(c.eligible for c in matrix.cells):` → emit NO_GO with VERDICT_NO_GO_DTI_ALL_PROGRAMS; computed_value = str(min((c.dti_back for c in matrix.cells), default=Decimal("0"))).
       - **Level 2**: `if not eligible_at_preferred:` → emit NO_GO with VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP; computed_value = str(preferred); dp_pct = preferred.
       - **Level 3 (D-14-VERDICT-02)**: compute `income_stress_fails = [s for s in stress.rows if s.stress_kind == "income_shock" and s.breaches_dti_ceiling and any(c.program == s.program for c in eligible_at_preferred)]`. If non-empty → emit WATCH with one VerdictReason(predicate_code=VERDICT_WATCH_STRESS_INCOME_FAIL, computed_value=str(f.stressed_dti_back), program=f.program) per failing row.
       - **Level 4 (D-14-VERDICT-01 + D-14-VERDICT-03)**: `if not non_fha_eligible:` (i.e., all eligible-at-preferred are FHA): pull `fha_cells = [c for c in eligible_at_preferred if c.program == "FHA30"]`. If `fha_cells and fha_cells[0].monthly_mi > _MIP_BURDEN_THRESHOLD`: emit WATCH with VERDICT_WATCH_FHA_MIP_BURDEN; computed_value = str(fha_cells[0].monthly_mi); program="FHA30"; dp_pct=preferred.
       - **Level 5 (D-14-VERDICT-03)**: GO; computed_value = str(len(non_fha_eligible)).

    6. Place the `_MIP_BURDEN_THRESHOLD` constant ABOVE the function (module-level). Document the policy choice + Assumption A1 in the constant's docstring.

    DO NOT declare VERDICT_WATCH_STRESS_RATE_FAIL or VERDICT_WATCH_STRESS_ARM_RESET constants — D-14-VERDICT-02 explicitly locks income-shock only as the WATCH trigger; declaring unused codes would fail the citation-coverage meta-test in Task 2.
    DO NOT import lib.property_analysis._build_* helpers — synthesize() is a pure function over already-built block inputs.
    DO NOT mutate any input arguments; frozen=True on Pydantic models prohibits this anyway.
    DO NOT use model_copy(update=...) — synthesize() constructs a fresh Verdict, never copies an input.
  </action>
  <verify>
    <automated>pytest tests/test_property_verdict.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `lib/property_verdict.py` exists.
    - `grep -c 'VERDICT_NO_GO_DTI_ALL_PROGRAMS: Final\[str\] = "DTI-CEILING-ALL-PROGRAMS"' lib/property_verdict.py` returns 1.
    - `grep -c 'VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP: Final\[str\] = "NO-ELIGIBLE-AT-PREFERRED-DP"' lib/property_verdict.py` returns 1.
    - `grep -c 'VERDICT_WATCH_FHA_MIP_BURDEN: Final\[str\] = "MIP-BURDEN-FHA"' lib/property_verdict.py` returns 1.
    - `grep -c 'VERDICT_WATCH_STRESS_INCOME_FAIL: Final\[str\] = "STRESS-INCOME-SHOCK"' lib/property_verdict.py` returns 1.
    - `grep -c 'VERDICT_GO: Final\[str\] = "GO-ALL-GREEN"' lib/property_verdict.py` returns 1.
    - `grep -c '_MIP_BURDEN_THRESHOLD: Final\[Decimal\] = Decimal("300.00")' lib/property_verdict.py` returns 1.
    - `grep -c 'def synthesize(' lib/property_verdict.py` returns 1.
    - `grep -c 'VERDICT_WATCH_STRESS_RATE_FAIL\|VERDICT_WATCH_STRESS_ARM_RESET' lib/property_verdict.py | grep -v '^#' | wc -l` returns 0 (no unused constants).
    - `python -c "from lib.property_verdict import VERDICT_NO_GO_DTI_ALL_PROGRAMS, VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP, VERDICT_WATCH_FHA_MIP_BURDEN, VERDICT_WATCH_STRESS_INCOME_FAIL, VERDICT_GO, _MIP_BURDEN_THRESHOLD, synthesize; from decimal import Decimal; assert _MIP_BURDEN_THRESHOLD == Decimal('300.00')"` exits 0.
    - `python -c "from lib.property_verdict import synthesize; import inspect; sig = inspect.signature(synthesize); assert list(sig.parameters.keys()) == ['matrix', 'stress', 'household', 'profile']"` exits 0 (signature pinned).
  </acceptance_criteria>
  <done>
    `lib/property_verdict.py` ships the 5 VERDICT_* constants + _MIP_BURDEN_THRESHOLD + synthesize() implementing the 5-level cascade. Importable and signature-pinned. Behavior verified in Task 2's test suite.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create tests/test_property_verdict.py with full cascade coverage + citation-coverage meta-test</name>
  <files>tests/test_property_verdict.py</files>
  <read_first>
    - lib/property_verdict.py (Task 1 output)
    - lib/property_analysis.py (Plan 14-02 — for constructing ProgramResult / DownPaymentMatrix / StressBlock / StressRow inputs)
    - lib/household.py, lib/profile.py
    - tests/test_affordability.py L1162-1199 (test_blocked_by_citation_coverage — the meta-test pattern to mirror)
    - tests/test_stress.py L718-790 (test_phase_08_citation_coverage_meta — phase-wide requirement coverage pattern)
    - .planning/phases/14-property-analysis-pipeline/14-VALIDATION.md (rows for VERD-01 — required named tests)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L1108-1114 (VERD-01 test-to-requirement map)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L594-662 (test_property_verdict.py pattern)
  </read_first>
  <behavior>
    The test file must contain exactly these named tests, each invoking synthesize() with a hand-constructed (matrix, stress, household, profile) tuple:

    Cascade tests (one per cascade level):
    - `test_no_go_no_eligible` — Matrix with all cells eligible=False → Verdict(level="NO_GO", reasons[0].predicate_code == VERDICT_NO_GO_DTI_ALL_PROGRAMS, computed_value is a Decimal-string).
    - `test_no_go_at_preferred_dp` — Matrix where some cells eligible at DP=0.25 BUT no cell eligible at preferred DP=0.20 → Verdict(level="NO_GO", reasons[0].predicate_code == VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP, reasons[0].dp_pct == Decimal("0.20")).
    - `test_watch_income_shock` — Eligible-at-preferred matrix + a StressBlock with at least one StressRow where stress_kind="income_shock" and breaches_dti_ceiling=True → Verdict(level="WATCH", reasons[0].predicate_code == VERDICT_WATCH_STRESS_INCOME_FAIL, reasons[0].program is set).
    - `test_watch_fha_mip_burden` — Eligible-at-preferred contains ONLY FHA30 cells (no Conv/VA/Jumbo eligible) AND fha_cell.monthly_mi == Decimal("325.00") (> $300 threshold) AND no income-shock failures → Verdict(level="WATCH", reasons[0].predicate_code == VERDICT_WATCH_FHA_MIP_BURDEN, reasons[0].computed_value == "325.00").
    - `test_go_non_fha_eligible` — Eligible-at-preferred contains at least one non-FHA program (Conv30) AND no income-shock failures → Verdict(level="GO", reasons[0].predicate_code == VERDICT_GO).

    Cascade-precedence tests (D-14-VERDICT-03):
    - `test_go_wins_over_mip_burden_when_non_fha_eligible` — Eligible-at-preferred contains BOTH Conv30 AND FHA30 (where FHA monthly_mi > $300) → Verdict(level="GO"), not WATCH. MIP-burden does NOT downgrade when non-FHA is eligible.
    - `test_watch_income_shock_overrides_go` — Same eligible-at-preferred as test_go_non_fha_eligible BUT with an income-shock failure → Verdict(level="WATCH") not GO. Income-shock precedes GO in cascade.

    Format-compliance test (D-14-VERDICT-04):
    - `test_reason_format_compliance` — For each cascade level (run synthesize() and inspect each output's reasons[]), assert every VerdictReason has non-empty predicate_code AND non-empty computed_value (both required by Pydantic frozen+strict, but assert explicitly via `assert len(reason.predicate_code) > 0` and `assert len(reason.computed_value) > 0`).

    Edge-case test:
    - `test_empty_matrix_returns_no_go` — synthesize(matrix=DownPaymentMatrix(cells=[], programs_present=[], down_payment_pcts=[]), stress=StressBlock(preferred_down_payment_pct=Decimal("0.20"), rows=[]), household, profile) → Verdict(level="NO_GO") without crashing (Behavior 9).

    Citation-coverage meta-test (Pitfall 7 + 12):
    - `test_verdict_code_citation_coverage` — Mirrors tests/test_affordability.py:test_blocked_by_citation_coverage. Procedure:
        1. Import lib.property_verdict.
        2. Inspect module globals (or grep the source file) for `VERDICT_` prefixed string constants.
        3. Run each of the 5 cascade-level unit tests INSIDE this test (call synthesize() with a known scenario for each cascade) and collect all `reason.predicate_code` values emitted across all scenarios.
        4. Assert every `VERDICT_` constant value appears in the collected set.
        5. Plan 14-06 will tighten this to fixture-based coverage when fixture files exist. For now, in-test coverage is the gate.

    Phase requirement-coverage meta-test:
    - `test_phase_14_verdict_requirement_coverage` — Asserts the docstrings / comments of synthesize() AND each cascade-level test reference D-14-VERDICT-01..04 + VERD-01. Pattern from tests/test_stress.py:test_phase_08_citation_coverage_meta.

    Total named test count: 10.
  </behavior>
  <action>
    Create `tests/test_property_verdict.py` with verbatim module-header style from tests/test_affordability.py.

    Required structure:
    1. Module docstring naming Phase 14 + VERD-01 + D-14-VERDICT-01..04 coverage.
    2. `from __future__ import annotations` first line.
    3. Imports:
       - `import pytest`
       - `from decimal import Decimal`
       - `from datetime import datetime, timezone`
       - `from lib.property_verdict import (synthesize, VERDICT_NO_GO_DTI_ALL_PROGRAMS, VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP, VERDICT_WATCH_FHA_MIP_BURDEN, VERDICT_WATCH_STRESS_INCOME_FAIL, VERDICT_GO, _MIP_BURDEN_THRESHOLD)`
       - `from lib.property_analysis import (ProgramResult, DownPaymentMatrix, StressRow, StressBlock, Verdict, VerdictReason)`
       - `from lib.household import Household`
       - `from lib.profile import Profile`

    4. Helper-builder functions (mirror tests/test_affordability.py L136-167 idiom):
       - `_make_eligible_cell(program, dp_pct, *, piti, monthly_mi=Decimal("0"), dti_back=Decimal("0.35"), ltv=Decimal("0.80")) -> ProgramResult` — returns an eligible ProgramResult with sensible defaults for non-domain fields.
       - `_make_ineligible_cell(program, dp_pct, *, blocker_reasons, **kwargs) -> ProgramResult` — returns an ineligible ProgramResult with the given blocker_reasons list.
       - `_make_matrix(cells: list[ProgramResult]) -> DownPaymentMatrix` — wraps cells in a DownPaymentMatrix with derived programs_present + down_payment_pcts.
       - `_make_stress_row(program, stress_kind, breaches=False, dti=Decimal("0.40")) -> StressRow` — returns a StressRow with sensible defaults.
       - `_make_stress_block(rows: list[StressRow], preferred_dp=Decimal("0.20")) -> StressBlock`.
       - `_make_clean_household(preferred_dp=Decimal("0.20")) -> Household` — returns a Household with preferred_down_payment_pct=preferred_dp.
       - `_make_clean_profile(**overrides) -> Profile`.

    5. Each named test from the Behavior list with the exact name. Use builders to construct minimal inputs.

    6. `test_verdict_code_citation_coverage` body:
       ```python
       def test_verdict_code_citation_coverage() -> None:
           """Pitfall 12 + RESEARCH §"Validation Architecture": every VERDICT_*
           constant in lib/property_verdict.py must be emitted by at least one
           cascade-level test in this file. Plan 14-06 will tighten this to
           fixture-based coverage."""
           import lib.property_verdict as v
           constants = {name: val for name, val in vars(v).items()
                        if isinstance(name, str) and name.startswith("VERDICT_") and isinstance(val, str)}
           assert constants, "No VERDICT_* constants found in lib.property_verdict"

           # Run each cascade level and collect emitted predicate_codes
           emitted: set[str] = set()
           # Level 1
           v1 = synthesize(_matrix_no_eligible(), _empty_stress(), _make_clean_household(), _make_clean_profile())
           emitted.update(r.predicate_code for r in v1.reasons)
           # Level 2
           v2 = synthesize(_matrix_eligible_at_non_preferred_only(), _empty_stress(), _make_clean_household(), _make_clean_profile())
           emitted.update(r.predicate_code for r in v2.reasons)
           # Level 3
           v3 = synthesize(_matrix_eligible_at_preferred(), _stress_with_income_shock_fail(), _make_clean_household(), _make_clean_profile())
           emitted.update(r.predicate_code for r in v3.reasons)
           # Level 4
           v4 = synthesize(_matrix_fha_only_eligible_with_high_mip(), _empty_stress(), _make_clean_household(), _make_clean_profile())
           emitted.update(r.predicate_code for r in v4.reasons)
           # Level 5
           v5 = synthesize(_matrix_eligible_at_preferred(), _empty_stress(), _make_clean_household(), _make_clean_profile())
           emitted.update(r.predicate_code for r in v5.reasons)

           # Every VERDICT_* constant must appear
           for name, code in constants.items():
               assert code in emitted, f"{name}={code!r} not exercised by any cascade level in this test file"
       ```
       Implement the helper matrix-builder functions (`_matrix_no_eligible`, `_matrix_eligible_at_non_preferred_only`, `_matrix_eligible_at_preferred`, `_matrix_fha_only_eligible_with_high_mip`, `_empty_stress`, `_stress_with_income_shock_fail`) as small wrappers on top of the basic builders above.

    7. `test_phase_14_verdict_requirement_coverage`:
       ```python
       def test_phase_14_verdict_requirement_coverage() -> None:
           """Every D-14-VERDICT-XX decision is referenced by at least one test
           docstring in this file. Pattern from tests/test_stress.py:
           test_phase_08_citation_coverage_meta."""
           import inspect
           from pathlib import Path

           source = Path(__file__).read_text()
           required_refs = ["D-14-VERDICT-01", "D-14-VERDICT-02", "D-14-VERDICT-03", "D-14-VERDICT-04", "VERD-01"]
           for ref in required_refs:
               assert ref in source, f"No test references {ref} in tests/test_property_verdict.py"
       ```

    DO NOT mock lib.property_verdict.synthesize — call it directly.
    DO NOT skip any test in this file. All 10 must pass on first run.
    DO NOT use `pytest.approx` or `assertAlmostEqual` for any numeric assertion.
    DO NOT reference fixture files — those don't exist yet. Synthesize inputs in-test using the builders.
    DO ensure docstrings on each cascade-level test reference the relevant D-14-VERDICT-XX decision (so test_phase_14_verdict_requirement_coverage finds them via source grep).
  </action>
  <verify>
    <automated>pytest tests/test_property_verdict.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `tests/test_property_verdict.py` exists.
    - `grep -c '^def test_' tests/test_property_verdict.py` returns at least 10.
    - Each named test from Behavior list exists: `for t in test_no_go_no_eligible test_no_go_at_preferred_dp test_watch_income_shock test_watch_fha_mip_burden test_go_non_fha_eligible test_go_wins_over_mip_burden_when_non_fha_eligible test_watch_income_shock_overrides_go test_reason_format_compliance test_empty_matrix_returns_no_go test_verdict_code_citation_coverage test_phase_14_verdict_requirement_coverage; do grep -c "def $t" tests/test_property_verdict.py; done` — every grep returns >= 1.
    - `pytest tests/test_property_verdict.py -x` exits 0 (all 10+ tests pass).
    - `grep -E 'assertAlmostEqual|pytest\.approx' tests/test_property_verdict.py | grep -v '^#' | wc -l` returns 0 (no fuzzy comparators).
    - `grep -c 'D-14-VERDICT-01\|D-14-VERDICT-02\|D-14-VERDICT-03\|D-14-VERDICT-04' tests/test_property_verdict.py` returns at least 4 (each decision referenced).
    - `grep -c 'VERD-01' tests/test_property_verdict.py` returns at least 1.
    - `pytest -x` (full suite) exits 0 — no regression in other phases.
  </acceptance_criteria>
  <done>
    All 10 named tests pass. Citation-coverage meta-test asserts every VERDICT_* constant is emitted by at least one cascade scenario. Phase-14 requirement-coverage meta-test asserts every D-14-VERDICT-XX is referenced. VERD-01 fully covered at the unit level.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase 14 lib → lib.property_verdict.synthesize() | Pure-function call over already-constructed Pydantic blocks. No external I/O, no time-of-call dependencies. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-FLOAT | Tampering | VerdictReason.computed_value (string, not Decimal) | mitigate | computed_value is intentionally a string per PATTERNS.md L455 — polymorphic numeric serialization. Tests assert exact string equality. |
| T-14-FRED-RACE | Tampering | n/a | accept | synthesize() does not read FRED. |
| T-14-STALE-REF | Tampering | n/a | accept | synthesize() does not read reference YAMLs. |
| T-14-REASON | Repudiation | VerdictReason.predicate_code, computed_value | mitigate | D-14-VERDICT-04 + Pitfall 7 — VerdictReason Pydantic model REQUIRES predicate_code AND computed_value (strict mode rejects empty/None for required str fields). Test_reason_format_compliance verifies both fields are populated on every emitted reason. Citation-coverage meta-test verifies every VERDICT_* constant is exercised. |
| T-14-PII | Information Disclosure | tests/test_property_verdict.py | mitigate | Tests use synthetic Household / Profile / ProgramResult instances; no real data. |
</threat_model>

<verification>
- `pytest tests/test_property_verdict.py -x` exits 0.
- `pytest -x` (full suite) exits 0 — no regression.
- `python -c "from lib.property_verdict import synthesize"` succeeds.
- `python -c "from lib.property_verdict import VERDICT_NO_GO_DTI_ALL_PROGRAMS; assert VERDICT_NO_GO_DTI_ALL_PROGRAMS == 'DTI-CEILING-ALL-PROGRAMS'"` exits 0.
- Citation-coverage meta-test asserts all 5 VERDICT_* constants are emitted by at least one cascade-level test scenario.
</verification>

<success_criteria>
1. lib/property_verdict.py ships 5 VERDICT_* Final[str] constants + _MIP_BURDEN_THRESHOLD + synthesize().
2. synthesize() implements the 5-level cascade per D-14-VERDICT-01..04 (NO_GO_no_eligible_any_DP → NO_GO_no_eligible_at_preferred → WATCH_income_shock → WATCH_FHA_MIP_burden → GO).
3. D-14-VERDICT-03 precedence: GO wins over MIP-burden when non-FHA eligible; income-shock WATCH still downgrades GO.
4. Every VerdictReason carries predicate_code AND computed_value (D-14-VERDICT-04).
5. tests/test_property_verdict.py contains 10+ named tests; citation-coverage meta-test asserts every VERDICT_* constant is exercised.
6. Pitfall 7 (prefix discipline) mitigated; Pitfall 12 (citation-coverage meta-test missing) mitigated.
7. VERD-01 closed at unit-test level; Plan 14-06 tightens to fixture-coverage.
</success_criteria>

<output>
After completion, create `.planning/phases/14-property-analysis-pipeline/14-04-SUMMARY.md` documenting:
- 5 VERDICT_* constants with exact string values.
- _MIP_BURDEN_THRESHOLD value + Assumption A1 reference.
- synthesize() signature + 5-level cascade summary.
- 10 named tests + which D-14-VERDICT-XX each covers.
- Citation-coverage meta-test behavior (in-test coverage now; fixture-coverage in Plan 14-06).
- Pitfalls mitigated: 7 (prefix discipline), 12 (citation-coverage meta-test).
- Requirements closed: VERD-01.
- Interfaces consumed by Plan 14-05: synthesize() (called from analyze()); Plan 14-06 fixtures reference the 5 VERDICT_* constants.
</output>
