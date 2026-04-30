---
phase: 05
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_arm.py
  - tests/fixtures/arm/.gitkeep
  - tests/fixtures/arm/oracle/.gitkeep
autonomous: true
requirements: []
tags:
  - phase-05
  - arm-modeling
  - test-infrastructure
  - nyquist
must_haves:
  truths:
    - "tests/test_arm.py file exists in repo and is collected by pytest"
    - "Every Phase 5 requirement (ARM-01..09) + every cross-cutting test name from 05-VALIDATION.md has a stub function with @pytest.mark.xfail decorator"
    - "Stubbed file runs (pytest tests/test_arm.py -v) without ImportError; xfail tests show as XFAIL not ERROR"
    - "tests/conftest.py exposes arm_fixture pytest fixture loadable by name from any test"
    - "tests/fixtures/arm/ and tests/fixtures/arm/oracle/ directories are committed (via .gitkeep)"
    - "Phase 5 test scaffold is additive: introduces no behavior change to Phase 1/3/4 production code or existing tests; only adds new xfail-decorated stubs that downstream waves flip"
  artifacts:
    - path: "tests/test_arm.py"
      provides: "32 xfail stubs covering ARM-01..09 + cross-cutting + applied_cap citation coverage + envelope-uniformity contract"
      min_lines: 200
    - path: "tests/conftest.py"
      provides: "arm_fixture loader (parallel to amortize_fixture + affordability_fixture)"
      contains: "def arm_fixture"
    - path: "tests/fixtures/arm/.gitkeep"
      provides: "Empty placeholder to commit hand-calc fixture directory"
    - path: "tests/fixtures/arm/oracle/.gitkeep"
      provides: "Empty placeholder to commit oracle capture directory"
  key_links:
    - from: "tests/test_arm.py"
      to: "tests/conftest.py"
      via: "arm_fixture parametric injection"
      pattern: "def test_.*\\(.*arm_fixture"
    - from: "Wave 2/3/4/5/6 plans"
      to: "tests/test_arm.py xfail decorators"
      via: "incremental flip from xfail → pass as engine slices land"
      pattern: "@pytest.mark.xfail"
---

<objective>
Establish the Phase 5 test scaffolding that subsequent waves flip xfail→pass against. Ship the `arm_fixture` pytest fixture loader, ~32 xfail-decorated stub tests covering every ARM-01..09 requirement plus cross-cutting tests (applied_cap citation coverage, envelope uniformity, lazy-import, oracle cross-validation), and the empty `tests/fixtures/arm/` + `tests/fixtures/arm/oracle/` directories.

Purpose: Nyquist validation gate. Every requirement-closing wave (Plans 02..06) flips a specific xfail to a real assertion. Without Wave 0, downstream plans have no test landing pads — they would either (a) ship code with no test or (b) invent test names ad-hoc that fail the citation-coverage meta-check.
Output: A test file that COLLECTS but xfails everything; a conftest.py extension; two empty fixture directories. Zero engine code, zero fixture content.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-arm-modeling/05-CONTEXT.md
@.planning/phases/05-arm-modeling/05-RESEARCH.md
@.planning/phases/05-arm-modeling/05-VALIDATION.md
@.planning/phases/05-arm-modeling/05-PATTERNS.md
@CLAUDE.md
@tests/conftest.py
@tests/test_amortize.py
@tests/test_affordability.py

<interfaces>
<!-- Existing tests/conftest.py (lines 1-71) — Phase 5 EXTENDS, does not modify -->

From tests/conftest.py:
```python
FIXTURE_DIR: Path = Path(__file__).parent / "fixtures"

@pytest.fixture
def amortize_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "amortize" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    return _load

@pytest.fixture
def affordability_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "affordability" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    return _load
```

The arm_fixture appended in this plan MUST mirror this exact shape.
</interfaces>

<test_inventory>
<!-- The 32 xfail stubs to be created in tests/test_arm.py — MUST contain all of these test names verbatim. -->
<!-- Source: 05-VALIDATION.md "Phase Requirements → Test Map" + "ROADMAP Success Criteria" + "applied_cap Literal Coverage". -->

ARM-01 (3 tests):
- test_arm_terms_field_set
- test_arm_terms_missing_floor_rate_raises
- test_note_rate_defaults_to_loan_annual_rate

ARM-02 (4 tests):
- test_arm_5_1_payment_jump_at_61
- test_arm_7_1_payment_jump_at_85
- test_arm_10_1_payment_jump_at_121
- test_arm_5_6_payment_jump_at_61_and_67

ARM-03 (3 tests):
- test_reset_formula_locked
- test_arm_initial_cap_at_first_reset
- test_arm_lifetime_cap_binds

ARM-04 (1 test):
- test_arm_floor_below_margin_blocked

ARM-05 (5 tests):
- test_full_remaining_term_re_amortization
- test_arm_continuous_period_numbering
- test_cumulative_totals_continuous_across_resets
- test_non_final_epoch_does_not_zero_balance
- test_initial_fixed_period_matches_phase1_oracle

ARM-06 (2 tests):
- test_oracle_cross_validation_5_1
- test_oracle_cross_validation_5_6

ARM-07 (1 test):
- test_arm_5_1_off_by_one_negative

ARM-08 (8 tests):
- test_cli_smoke_subprocess_round_trip
- test_cli_help_does_not_import_lib_arm
- test_cli_rejects_float_principal
- test_cli_rejects_float_assumed_index_rate
- test_cli_rejects_float_index_path_value
- test_cli_rejects_float_floor_rate
- test_cli_error_envelope_uniformity
- test_cli_misaligned_index_path_period_rejected

ARM-09 (3 tests):
- test_arm_mechanics_doc_sections_present
- test_arm_terms_docstring_cites_arm_mechanics
- test_arm_mechanics_citations

Cross-cutting (2 tests):
- test_applied_cap_citation_coverage
- test_arm_teaser_rate

TOTAL: 32 xfail stubs.
</test_inventory>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend tests/conftest.py with arm_fixture loader</name>
  <files>tests/conftest.py</files>
  <read_first>
    - tests/conftest.py (full file, 71 lines) — lift the affordability_fixture pattern verbatim
    - 05-PATTERNS.md "tests/conftest.py (extend with arm_fixture loader)" section (line 700+ in patterns doc)
  </read_first>
  <action>
    Append to tests/conftest.py (after the existing affordability_fixture at line 70). The arm_fixture loader is a near-verbatim clone of affordability_fixture with the path component swapped.

    Append exactly this block at end of file:

    ```python


    @pytest.fixture
    def arm_fixture() -> Callable[[str], dict[str, Any]]:
        """Return a callable that loads a single ARM fixture by filename stem
        from tests/fixtures/arm/. Mirrors `amortize_fixture` and
        `affordability_fixture` — one-fixture-per-file shape; loader takes a
        filename stem like "arm_5_1_payment_jump_at_61", not an id within an array.

        Per Phase 5 CONTEXT.md D-09: every Phase 5 fixture lives under
        tests/fixtures/arm/ as one .json per scenario. Oracle capture pairs
        (Bankrate/Vertex42/AmericU per D-04) live under tests/fixtures/arm/oracle/;
        callers pass "oracle/bankrate_5_1_capture_2026" as the stem to load those.
        """

        def _load(stem: str) -> dict[str, Any]:
            path = FIXTURE_DIR / "arm" / f"{stem}.json"
            return json.loads(path.read_text())  # type: ignore[no-any-return]

        return _load
    ```

    Do NOT modify the existing golden_fixture, amortize_fixture, or affordability_fixture functions. Add ONLY the arm_fixture function plus its preceding blank lines.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; python -c "from tests.conftest import arm_fixture; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def arm_fixture' tests/conftest.py` returns 1
    - `grep -c 'def amortize_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'def affordability_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'def golden_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'fixtures" / "arm" / f"{stem}.json"' tests/conftest.py` returns 1 (path is exactly fixtures/arm/<stem>.json)
    - `pytest tests/test_amortize.py tests/test_affordability.py -x --collect-only` exits 0 (no regression to existing test collection)
  </acceptance_criteria>
  <done>
    arm_fixture is importable from tests.conftest; existing fixtures remain unchanged; existing test collection still succeeds.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/fixtures/arm/ + tests/fixtures/arm/oracle/ via .gitkeep</name>
  <files>tests/fixtures/arm/.gitkeep, tests/fixtures/arm/oracle/.gitkeep</files>
  <read_first>
    - tests/fixtures/ directory listing to confirm .gitkeep convention used elsewhere
  </read_first>
  <action>
    Create two empty .gitkeep files (zero bytes each) so the directories are committed:

    1. tests/fixtures/arm/.gitkeep — empty file
    2. tests/fixtures/arm/oracle/.gitkeep — empty file

    Both are needed because Plan 06 ships hand-calc fixture JSON into tests/fixtures/arm/ AND oracle PDF/JSON pairs into tests/fixtures/arm/oracle/. Wave 0 commits the directory structure now so xfail stubs that reference these paths (in Wave 0 stubs only as comments, not as actual reads) can be reasoned about.

    Use the Write tool with empty string content "". Do NOT add any placeholder text — .gitkeep is a zero-byte convention.
  </action>
  <verify>
    <automated>test -f /Users/cujo253/Documents/mortgage-ops/tests/fixtures/arm/.gitkeep &amp;&amp; test -f /Users/cujo253/Documents/mortgage-ops/tests/fixtures/arm/oracle/.gitkeep &amp;&amp; echo OK</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/fixtures/arm/.gitkeep` exits 0
    - `test -f tests/fixtures/arm/oracle/.gitkeep` exits 0
    - `test -d tests/fixtures/arm` exits 0
    - `test -d tests/fixtures/arm/oracle` exits 0
    - `wc -c tests/fixtures/arm/.gitkeep` returns 0 (empty file)
    - `wc -c tests/fixtures/arm/oracle/.gitkeep` returns 0 (empty file)
  </acceptance_criteria>
  <done>
    Both directories exist and are committable.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create tests/test_arm.py with 32 xfail stubs covering ARM-01..09 + cross-cutting</name>
  <files>tests/test_arm.py</files>
  <read_first>
    - tests/test_amortize.py lines 1-60 (module header + SCRIPT_PATH constant + imports pattern)
    - tests/test_affordability.py lines 1-80 (composite header + SCRIPT_PATH + lazy-import test name)
    - 05-VALIDATION.md "Phase Requirements → Test Map" + "applied_cap Literal Coverage" + "ROADMAP Success Criteria → Test Map" sections — these define the exhaustive test name list
    - 05-PATTERNS.md "tests/test_arm.py" section (Patterns 1-6) for header + SCRIPT_PATH + module-level constants
    - 05-CONTEXT.md "Test Inventory" frontmatter section (above) — the 32 names listed
  </read_first>
  <action>
    Create tests/test_arm.py as a brand-new file. The file holds 32 xfail-decorated stub tests + a module header. NO test asserts anything except `pytest.fail("Wave 0 stub")` (the xfail marker absorbs the failure into XFAIL state).

    File structure:

    ```python
    """Phase 5 ARM Modeling — full test surface (ARM-01..09 + cross-cutting).

    Per Phase 3 D-17 portability + Phase 4 D-13 inheritance: subprocess
    invocation only for CLI tests, never `import scripts.arm_simulate`
    directly. SCRIPT_PATH is the single constant edited at Phase 10 when
    scripts/ relocates to .claude/skills/mortgage-ops/scripts/.

    Wave 0 (Plan 05-00) creates ALL 32 tests as xfail stubs. Subsequent waves
    flip the relevant xfail decorators to real assertions:

    - Wave 2 (Plan 05-02 Pydantic models): ARM-01 (3 tests)
    - Wave 3 (Plan 05-03 build_arm_schedule): ARM-02..05 (13 tests)
    - Wave 4 (Plan 05-04 CLI + helper factor): ARM-08 (8 tests)
    - Wave 5 (Plan 05-05 references doc): ARM-09 (3 tests)
    - Wave 6 (Plan 05-06 fixtures + oracle): ARM-06, ARM-07, plus cross-cutting (5 tests)

    Each xfail decorator carries `strict=True` so a passing test in xfail state
    raises XPASS at collection time — the wave that flips it MUST also remove
    the decorator. This prevents accidental "fixed but still marked xfail" drift.
    """

    from __future__ import annotations

    import json
    import re
    import subprocess
    import sys
    from decimal import Decimal
    from pathlib import Path
    from typing import TYPE_CHECKING, Any

    import pytest

    if TYPE_CHECKING:
        from collections.abc import Callable

    SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "arm_simulate.py"
    """Phase 5 CLI lives at project-root scripts/. Phase 10 will relocate to
    .claude/skills/mortgage-ops/scripts/; only this constant updates."""

    ARM_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "arm.py"
    """For lazy-import test (D-18 inherited): assert lib.arm is NOT imported by --help."""


    # =========================================================================
    # ARM-01 (3 stubs) — flipped in Wave 2 (Plan 05-02)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 implements ARMTerms")
    def test_arm_terms_field_set() -> None:
        """ARM-01 + ROADMAP SC-1: ARMTerms has 8 explicit fields + REQUIRED floor_rate + optional note_rate."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 implements ARMTerms")
    def test_arm_terms_missing_floor_rate_raises() -> None:
        """ARM-01 + D-02: ARMTerms rejects missing floor_rate at construction (no default)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-03 implements engine note_rate fallback")
    def test_note_rate_defaults_to_loan_annual_rate() -> None:
        """ARM-01 + D-02: note_rate=None means engine substitutes loan.annual_rate for lifetime base."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-02 (4 stubs) — flipped in Wave 6 (fixtures land)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_1_payment_jump_at_61.json")
    def test_arm_5_1_payment_jump_at_61(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-02 + ROADMAP SC-2: 5/1 ARM produces payment-jump at month 61 (not 60, not 62)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_7_1_payment_jump_at_85.json")
    def test_arm_7_1_payment_jump_at_85(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-02: 7/1 ARM (initial=84, reset=12)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_10_1_payment_jump_at_121.json")
    def test_arm_10_1_payment_jump_at_121(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-02: 10/1 ARM (initial=120, reset=12)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_6_payment_jump_at_61_and_67.json")
    def test_arm_5_6_payment_jump_at_61_and_67(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-02 + D-15: 5/6 ARM (initial=60, reset=6) — first reset 61, second 67."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-03 (3 stubs) — flipped in Wave 6
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-03 + 05-06 implement reset formula")
    def test_reset_formula_locked() -> None:
        """ARM-03 + D-02: clamp(quantize(index+margin), low=floor, high=min(periodic_ceil, lifetime_ceil))."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_initial_cap_at_first_reset.json")
    def test_arm_initial_cap_at_first_reset(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-03 + D-02: First-reset uses initial_cap; subsequent uses periodic_cap."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_lifetime_cap_binds.json")
    def test_arm_lifetime_cap_binds(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-03: Lifetime cap binds when fully-indexed > note_rate + lifetime_cap."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-04 (1 stub) — flipped in Wave 6
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_floor_below_margin_blocked.json")
    def test_arm_floor_below_margin_blocked(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-04 + ROADMAP SC-4: Floor enforcement: new_rate >= max(margin, floor_rate)."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-05 (5 stubs) — flipped in Wave 6
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-03 + 05-06 implement re-amortization")
    def test_full_remaining_term_re_amortization(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-05 + D-05: Re-amortization over FULL remaining term (not just reset window)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_continuous_period_numbering.json")
    def test_arm_continuous_period_numbering(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-05 + D-03: Continuous period numbering 1..N; final balance == 0.00."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-03 implements cumulative-totals stitch")
    def test_cumulative_totals_continuous_across_resets(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-05 + D-05 step 2.4: cumulative_interest + cumulative_principal continuous across epoch boundaries."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-03 + 05-06 lock the slice-stitch invariant")
    def test_non_final_epoch_does_not_zero_balance(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-05 + RESEARCH Q1.2 bear trap: non-final epoch's last sliced row has balance > 0.00."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 reuses Phase 1 oracle anchor")
    def test_initial_fixed_period_matches_phase1_oracle(
        golden_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """ARM-05 + LM-6: First epoch matches Phase 1 oracle ($400k @ 6.5%/30yr → $2528.27 P&I)."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-06 (2 stubs) — flipped in Wave 6 (oracle PDF + JSON ship)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships bankrate + vertex42 5/1 captures")
    def test_oracle_cross_validation_5_1(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-06 + D-04 [REVISED]: Hand-calc + Bankrate + Vertex42 captures AGREE EXACTLY (5/1)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships AmericU 5/6 disclosure capture")
    def test_oracle_cross_validation_5_6(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-06 + D-04 [REVISED]: 5/6 ARM oracle — AmericU disclosure cross-validation."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-07 (1 stub) — flipped in Wave 6
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_1_off_by_one_negative.json")
    def test_arm_5_1_off_by_one_negative(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-07 + ROADMAP SC-3: month 59 still old AND month 61 already new."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-08 (8 stubs) — flipped in Wave 4 (CLI ships)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships scripts/arm_simulate.py")
    def test_cli_smoke_subprocess_round_trip(
        arm_fixture: Callable[[str], dict[str, Any]],
        tmp_path: Path,
    ) -> None:
        """ARM-08: CLI subprocess round-trip — write JSON, invoke, parse stdout."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships lazy-import in scripts/arm_simulate.py")
    def test_cli_help_does_not_import_lib_arm() -> None:
        """ARM-08 + D-18: --help fast (no lib.arm or numpy_financial import before argparse)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate in scripts/arm_simulate.py")
    def test_cli_rejects_float_principal(tmp_path: Path) -> None:
        """ARM-08 + D-19/WR-02: CLI rejects JSON-float in loan.principal with 6-key envelope."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate")
    def test_cli_rejects_float_assumed_index_rate(tmp_path: Path) -> None:
        """ARM-08 + D-19: CLI rejects JSON-float in assumed_index_rate."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate (deep loc)")
    def test_cli_rejects_float_index_path_value(tmp_path: Path) -> None:
        """ARM-08 + D-19: CLI rejects JSON-float in index_path[].value (deep loc through list)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate")
    def test_cli_rejects_float_floor_rate(tmp_path: Path) -> None:
        """ARM-08 + D-19: CLI rejects JSON-float in arm_terms.floor_rate."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships uniform envelope")
    def test_cli_error_envelope_uniformity(tmp_path: Path) -> None:
        """ARM-08 + D-19/WR-02: float-gate + Pydantic ValidationError emit identical 6-key shape."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 ships ARMRequest cross-field validator")
    def test_cli_misaligned_index_path_period_rejected(tmp_path: Path) -> None:
        """ARM-08 + D-01: CLI surfaces ARMRequest._index_path_periods_align_to_reset_triggers as 6-key envelope."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ARM-09 (3 stubs) — flipped in Wave 5 (references/arm-mechanics.md ships)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-05 ships references/arm-mechanics.md")
    def test_arm_mechanics_doc_sections_present() -> None:
        """ARM-09 + D-08: references/arm-mechanics.md exists with all 6 D-08 sections."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 + 05-05 add docstring cite")
    def test_arm_terms_docstring_cites_arm_mechanics() -> None:
        """ARM-09 + ROADMAP SC-5: ARMTerms docstring cites references/arm-mechanics.md."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-05 ships corrected D-08 citations")
    def test_arm_mechanics_citations() -> None:
        """ARM-09 + D-08 [REVISED]: cites B2-1.4-02 + Freddie 6302.7(b) + CFPB §1951 + AmericU 5/6 disclosure."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # Cross-cutting (2 stubs)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships fixtures covering all 5 Literal values")
    def test_applied_cap_citation_coverage() -> None:
        """D-10: every applied_cap Literal value (initial/periodic/lifetime/floor/none) exercised by ≥1 fixture."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_teaser_rate.json")
    def test_arm_teaser_rate(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """D-02 + LM-3: teaser-rate ARM (loan.annual_rate=0.03, note_rate=0.05); lifetime base = note_rate."""
        pytest.fail("Wave 0 stub")
    ```

    Notes:
    - All 32 stubs use `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-XX ...")`. The strict flag means a stub that ACCIDENTALLY passes raises XPASS and fails CI — forcing the wave that fixes the test to also remove the decorator.
    - Imports cover everything subsequent waves need (json, re, subprocess, sys, Decimal, Path, pytest). No imports of lib.arm yet (Wave 2 ships it).
    - Each stub body is just `pytest.fail("Wave 0 stub")`. The xfail decorator catches the failure → reports XFAIL.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_arm.py -v --tb=no 2>&amp;1 | tail -50</automated>
  </verify>
  <acceptance_criteria>
    - File tests/test_arm.py exists with at least 200 lines
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_arm.py` returns 32 (one per stub)
    - `grep -c 'def test_' tests/test_arm.py` returns 32 (one per stub)
    - `grep -c 'def test_arm_terms_field_set' tests/test_arm.py` returns 1
    - `grep -c 'def test_arm_5_1_payment_jump_at_61' tests/test_arm.py` returns 1
    - `grep -c 'def test_arm_5_6_payment_jump_at_61_and_67' tests/test_arm.py` returns 1
    - `grep -c 'def test_arm_floor_below_margin_blocked' tests/test_arm.py` returns 1
    - `grep -c 'def test_oracle_cross_validation_5_1' tests/test_arm.py` returns 1
    - `grep -c 'def test_oracle_cross_validation_5_6' tests/test_arm.py` returns 1
    - `grep -c 'def test_cli_help_does_not_import_lib_arm' tests/test_arm.py` returns 1
    - `grep -c 'def test_applied_cap_citation_coverage' tests/test_arm.py` returns 1
    - `grep -c 'def test_arm_mechanics_citations' tests/test_arm.py` returns 1
    - `grep -c 'def test_initial_fixed_period_matches_phase1_oracle' tests/test_arm.py` returns 1
    - `grep -c 'SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "arm_simulate.py"' tests/test_arm.py` returns 1
    - `pytest tests/test_arm.py --collect-only -q 2>&1 | grep -c 'test_'` returns at least 32
    - `pytest tests/test_arm.py -v --tb=no 2>&1 | grep -c XFAIL` returns 32 (every stub xfails cleanly)
    - `pytest tests/test_arm.py -v --tb=no 2>&1 | grep -E '(FAILED|ERROR)' | wc -l` returns 0 (no errors / collect failures)
  </acceptance_criteria>
  <done>
    tests/test_arm.py is collected by pytest, runs to completion, and produces exactly 32 XFAIL outcomes (zero passes, zero failures, zero errors).
  </done>
</task>

<task type="auto">
  <name>Task 4: Verify zero regression to Phase 4 baseline + commit Wave 0</name>
  <files>(verification only — no file writes)</files>
  <read_first>
    - 05-VALIDATION.md "Phase gate" row (Phase 4 baseline = 379 passed + 4 skipped)
  </read_first>
  <action>
    Run the full pytest suite and confirm:
    1. Phase 4 baseline preserved: 379 passed + 4 skipped (or higher pass count if any prior xfail flipped to pass — that is also acceptable, but the 379 floor must hold)
    2. New ARM-modeling tests show 32 xfails
    3. Zero failures, zero errors

    Run: `pytest -v --tb=short 2>&1 | tail -80`

    If any pre-existing test fails or any unexpected error appears, STOP and investigate. Do NOT proceed until full suite is green-modulo-xfail.

    After verification passes, run mypy + ruff hygiene:
    - `mypy --strict tests/conftest.py tests/test_arm.py`
    - `ruff check tests/conftest.py tests/test_arm.py`
    - `ruff format --check tests/conftest.py tests/test_arm.py`

    All three MUST be clean (zero issues, zero diffs).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest -q 2>&amp;1 | tail -10 &amp;&amp; mypy --strict tests/conftest.py tests/test_arm.py &amp;&amp; ruff check tests/conftest.py tests/test_arm.py &amp;&amp; ruff format --check tests/conftest.py tests/test_arm.py</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows ≥ 379 passed
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ xfailed'` shows exactly 32 xfailed
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ failed'` returns no output OR "0 failed"
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ error'` returns no output OR "0 errors"
    - `mypy --strict tests/conftest.py tests/test_arm.py` exits 0 with "Success: no issues found"
    - `ruff check tests/conftest.py tests/test_arm.py` exits 0 with "All checks passed"
    - `ruff format --check tests/conftest.py tests/test_arm.py` exits 0
  </acceptance_criteria>
  <done>
    Full suite passes with zero regressions; new tests show 32 XFAIL; mypy + ruff clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Wave 0 → Wave 2..6 | Test stubs define the contract that engine implementations must satisfy; mismatch silently leaves a requirement unverified |
| pytest collection → CI signal | XFAIL must be the outcome state; PASS or FAIL or ERROR all leak signal noise |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-09 | Tampering (test contract drift) | tests/test_arm.py stub names | mitigate | Stub names are LISTED VERBATIM in the test_inventory section of this plan; acceptance_criteria grep each one to confirm presence |
| T-05-10 | Information Disclosure (false-pass via skipped xfail) | xfail decorators | mitigate | Every xfail uses `strict=True` → an accidental pass triggers XPASS failure. Wave 2..6 plans MUST remove the decorator when flipping the test |
| T-05-11 | Denial of Service (test-suite slowdown) | new 32 stubs | accept | All stubs are zero-cost `pytest.fail("Wave 0 stub")`; total runtime impact < 0.5s |
| T-05-12 | Repudiation (silent regression to Phase 4 baseline) | conftest.py extension | mitigate | Task 4 acceptance_criteria asserts ≥379 passed; mypy + ruff clean |
</threat_model>

<verification>
- All 32 expected stub names present in tests/test_arm.py (one grep per name in acceptance_criteria)
- Full pytest suite: ≥379 passed + ≥32 xfailed + 0 failed + 0 errored
- mypy --strict + ruff clean across conftest.py + test_arm.py
- Both fixture directories committed (.gitkeep present, zero bytes)
- arm_fixture importable; existing fixtures unchanged
</verification>

<success_criteria>
- tests/test_arm.py exists, collected by pytest, all 32 stubs report XFAIL
- tests/conftest.py extended with arm_fixture (existing fixtures untouched)
- tests/fixtures/arm/ + tests/fixtures/arm/oracle/ committed via .gitkeep
- Phase 4 baseline preserved (≥379 passed + ≥4 skipped)
- mypy --strict + ruff format clean across all touched files
- Wave 2..6 have a clear contract: each downstream plan flips a known xfail name and removes the decorator
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-00-SUMMARY.md` documenting:
- Number of xfail stubs created (must be 32)
- Phase 4 baseline pass count after Wave 0 (must be ≥379)
- mypy + ruff status (must be clean)
- Mapping table: each xfail stub → wave-and-plan responsible for flipping it
</output>
