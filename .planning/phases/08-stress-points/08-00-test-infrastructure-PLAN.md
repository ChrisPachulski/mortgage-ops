---
phase: 08
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_stress.py
  - tests/test_points.py
  - tests/fixtures/stress/.gitkeep
  - tests/fixtures/stress/oracle/.gitkeep
  - tests/fixtures/points/.gitkeep
autonomous: true
requirements: []
tags:
  - phase-08
  - stress-points
  - test-infrastructure
  - nyquist
must_haves:
  truths:
    - "tests/test_stress.py and tests/test_points.py exist and are collected by pytest"
    - "Every Phase 8 requirement (STRS-01..04, PNTS-01..03) plus every ROADMAP SC-1..SC-5 has at least one xfail-decorated stub function"
    - "All xfail decorators use strict=True so an accidental pass triggers XPASS at CI"
    - "tests/conftest.py exposes stress_fixture and points_fixture pytest fixtures"
    - "tests/fixtures/stress/, tests/fixtures/stress/oracle/, tests/fixtures/points/ directories committed via .gitkeep"
    - "Phase 8 test scaffold is additive: Phase 5 baseline (411 passed + 4 skipped per Phase 5 06 SUMMARY) preserved"
  artifacts:
    - path: "tests/test_stress.py"
      provides: "13 xfail stubs covering STRS-01..04 + ROADMAP SC-1/SC-2/SC-3/SC-5 + cross-cutting (envelope, lazy-import, invariants)"
      min_lines: 200
    - path: "tests/test_points.py"
      provides: "5 xfail stubs covering PNTS-01..03 + ROADMAP SC-4 (divergence)"
      min_lines: 100
    - path: "tests/conftest.py"
      provides: "stress_fixture + points_fixture loaders (parallel to arm_fixture)"
      contains: "def stress_fixture"
---

<objective>
Establish the Phase 8 test scaffolding that subsequent waves flip xfail→pass against. Ship the `stress_fixture` + `points_fixture` pytest fixtures, ~13 xfail-decorated stubs in `tests/test_stress.py` covering STRS-01..04 + SC-1/2/3/5, ~5 xfail stubs in `tests/test_points.py` covering PNTS-01..03 + SC-4 divergence, plus the empty `tests/fixtures/stress/`, `tests/fixtures/stress/oracle/`, and `tests/fixtures/points/` directories.

Purpose: Nyquist validation gate. Every requirement-closing wave (Plans 02..05) flips a specific xfail to a real assertion. Without Wave 0, downstream plans have no test landing pads.

Output: Two test files that COLLECT but xfail everything; conftest.py extension; three empty fixture directories. Zero engine code, zero fixture content.
</objective>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/08-stress-points/08-PATTERNS.md
@.planning/phases/08-stress-points/08-RESEARCH.md
@CLAUDE.md
@tests/conftest.py
@tests/test_arm.py
@tests/test_amortize.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend tests/conftest.py with stress_fixture + points_fixture loaders</name>
  <files>tests/conftest.py</files>
  <action>
    Append to tests/conftest.py (after the existing `arm_fixture` at line 91). Two new factories, near-verbatim clones of `arm_fixture` with the path component swapped.

    ```python


    @pytest.fixture
    def stress_fixture() -> Callable[[str], dict[str, Any]]:
        """Return a callable that loads a single stress fixture by filename stem
        from tests/fixtures/stress/. Mirrors arm_fixture / affordability_fixture.

        Per Phase 8 Plan 08-05: every Phase 8 stress fixture lives under
        tests/fixtures/stress/ as one .json per scenario. Oracle pairs (if any
        v2 capture-as-fixture lands) live under tests/fixtures/stress/oracle/.
        """

        def _load(stem: str) -> dict[str, Any]:
            path = FIXTURE_DIR / "stress" / f"{stem}.json"
            return json.loads(path.read_text())  # type: ignore[no-any-return]

        return _load


    @pytest.fixture
    def points_fixture() -> Callable[[str], dict[str, Any]]:
        """Return a callable that loads a single points-breakeven fixture by
        filename stem from tests/fixtures/points/. Mirrors arm_fixture /
        affordability_fixture / stress_fixture. Plan 08-05 ships fixtures here.
        """

        def _load(stem: str) -> dict[str, Any]:
            path = FIXTURE_DIR / "points" / f"{stem}.json"
            return json.loads(path.read_text())  # type: ignore[no-any-return]

        return _load
    ```

    Do NOT modify the existing golden_fixture, amortize_fixture, affordability_fixture, or arm_fixture functions.
  </action>
  <acceptance_criteria>
    - `grep -c 'def stress_fixture' tests/conftest.py` returns 1
    - `grep -c 'def points_fixture' tests/conftest.py` returns 1
    - `grep -c 'def arm_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'def affordability_fixture' tests/conftest.py` returns 1 (existing)
    - `grep -c 'def amortize_fixture' tests/conftest.py` returns 1 (existing)
    - `grep -c 'fixtures" / "stress" / f"{stem}.json"' tests/conftest.py` returns 1
    - `grep -c 'fixtures" / "points" / f"{stem}.json"' tests/conftest.py` returns 1
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Create three .gitkeep placeholders</name>
  <files>tests/fixtures/stress/.gitkeep, tests/fixtures/stress/oracle/.gitkeep, tests/fixtures/points/.gitkeep</files>
  <action>
    Create three empty (zero-byte) .gitkeep files via Write tool with empty string content:
    1. tests/fixtures/stress/.gitkeep
    2. tests/fixtures/stress/oracle/.gitkeep
    3. tests/fixtures/points/.gitkeep
  </action>
  <acceptance_criteria>
    - `test -f tests/fixtures/stress/.gitkeep && test -f tests/fixtures/stress/oracle/.gitkeep && test -f tests/fixtures/points/.gitkeep` exits 0
    - `wc -c tests/fixtures/stress/.gitkeep` returns 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Create tests/test_stress.py with 13 xfail stubs</name>
  <files>tests/test_stress.py</files>
  <action>
    Create tests/test_stress.py with these exact stubs, all `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-XX implements ...")`:

    Module header:
    ```python
    """Phase 8 Stress Tests — full test surface (STRS-01..04 + ROADMAP SC-1/2/3/5 + cross-cutting).

    Per Phase 3 D-17 portability + Phase 5 Wave 0 idiom: subprocess invocation only
    for CLI tests, never `import scripts.stress_test` directly. SCRIPT_PATH is the
    single constant edited at Phase 10 when scripts/ relocates to .claude/skills/.

    Wave 0 (Plan 08-00) creates ALL 13 stubs as xfail. Subsequent waves flip:
    - Wave 1 (Plan 08-01 Pydantic models): STRS-04 model contract (1 stub)
    - Wave 2 (Plan 08-02 lib/stress.py): STRS-01/02/03 engine (4 stubs)
    - Wave 4 (Plan 08-04 scripts/stress_test.py): STRS-04 CLI (4 stubs)
    - Wave 5 (Plan 08-05 fixtures + tests): SC-1/2/3/5 fixture-driven (4 stubs)

    Each xfail uses strict=True so accidental pass raises XPASS — the wave that
    flips it MUST also remove the decorator.
    """

    from __future__ import annotations

    from pathlib import Path
    from typing import TYPE_CHECKING, Any

    import pytest

    if TYPE_CHECKING:
        from collections.abc import Callable

    SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "stress_test.py"
    """Phase 8 CLI lives at project-root scripts/. Phase 10 relocates."""

    STRESS_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "stress.py"
    """For lazy-import test (D-18 inherited): assert lib.stress is NOT imported by --help."""
    ```

    The 13 stubs (verbatim names + decorators + minimal bodies):

    ```python
    # =========================================================================
    # STRS-04 model contract (1 stub) — flipped Wave 1 (Plan 08-01)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-01 ships StressRequest discriminated union")
    def test_stress_request_discriminated_union_by_mode() -> None:
        """STRS-04 + Plan 08-01: StressRequest = RateShock|IncomeShock|ArmReset discriminated by 'mode'."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # STRS-01 rate-shock engine (1 stub) — flipped Wave 2
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-02 ships lib.stress.rate_shock")
    def test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent(
        stress_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """STRS-01 + ROADMAP SC-1: rate-shock returns monthly_pi exact to cent for each rate."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # STRS-02 income-shock engine (1 stub) — flipped Wave 2
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-02 ships lib.stress.income_shock")
    def test_income_shock_per_cell_calls_phase4_engine_with_threshold_breach(
        stress_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """STRS-02 + ROADMAP SC-2: income-shock recomputes dti_back per reduction; flags threshold breach."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # STRS-03 ARM-reset path engine (2 stubs) — flipped Wave 2
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-02 ships lib.stress.arm_path")
    def test_arm_path_three_canonical_paths_total_interest(
        stress_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """STRS-03 + ROADMAP SC-3: parallel-shift + gradual-rise + fall-then-rise return total_interest_paid."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-02 synthesizes index_path per reset trigger")
    def test_arm_path_30yr_horizon_reset_count(
        stress_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """STRS-03 + ROADMAP SC-3: 5/1 ARM 30yr → 25 reset events per path."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # STRS-04 CLI (4 stubs) — flipped Wave 4 (Plan 08-04)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-04 ships scripts/stress_test.py")
    def test_cli_stress_smoke_subprocess_round_trip_rate_shock(
        stress_fixture: Callable[[str], dict[str, Any]],
        tmp_path: Path,
    ) -> None:
        """STRS-04: CLI rate-shock subprocess round-trip — write JSON, invoke, parse stdout."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-04 ships --rates 0.06,0.065,... shortcut")
    def test_cli_stress_rates_shortcut_arg_matches_roadmap_sc1(tmp_path: Path) -> None:
        """STRS-04 + ROADMAP SC-1 verbatim: --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-04 ships D-18 lazy-import")
    def test_cli_stress_help_does_not_import_lib_stress() -> None:
        """STRS-04 + D-18: --help fast (no lib.stress or numpy_financial import before argparse)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-04 ships float-gate + 6-key envelope")
    def test_cli_stress_rejects_float_principal_with_6_key_envelope(tmp_path: Path) -> None:
        """STRS-04 + WR-02: CLI rejects JSON-float in loan.principal with 6-key Pydantic envelope."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # ROADMAP SC-5 subagent-summarization output (3 stubs) — flipped Wave 5
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-05 ships rate_shock_size_budget_50_rates.json")
    def test_sc5_stress_sweep_50_scenarios_under_100kb(
        stress_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """ROADMAP SC-5: 50-scenario sweep produces JSON < 100KB."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-01 declares summary BEFORE rows")
    def test_sc5_summary_table_appears_before_rows_in_json() -> None:
        """ROADMAP SC-5: scenario-summary table at the top — summary key appears before rows key."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-02 emits stress_invariant_violations")
    def test_sc5_stress_invariants_monthly_pi_monotone_in_rate(
        stress_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """ROADMAP SC-5 + RESEARCH §6.4: monthly_pi strictly increases as rate strictly increases."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # Cross-cutting (1 stub)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-04 ships envelope-uniformity")
    def test_cli_stress_error_envelope_uniformity(tmp_path: Path) -> None:
        """STRS-04 + WR-02: float-gate + Pydantic ValidationError emit identical 6-key shape."""
        pytest.fail("Wave 0 stub")
    ```

    Total: 13 xfail stubs (1 model + 4 engine + 4 CLI + 3 SC-5 + 1 cross-cutting).
  </action>
  <acceptance_criteria>
    - File tests/test_stress.py exists with at least 200 lines
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_stress.py` returns 13
    - `grep -c 'def test_' tests/test_stress.py` returns 13
    - `grep -c 'def test_stress_request_discriminated_union_by_mode' tests/test_stress.py` returns 1
    - `grep -c 'def test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent' tests/test_stress.py` returns 1
    - `grep -c 'def test_income_shock_per_cell_calls_phase4_engine_with_threshold_breach' tests/test_stress.py` returns 1
    - `grep -c 'def test_arm_path_three_canonical_paths_total_interest' tests/test_stress.py` returns 1
    - `grep -c 'def test_sc5_stress_sweep_50_scenarios_under_100kb' tests/test_stress.py` returns 1
    - `grep -c 'def test_sc5_summary_table_appears_before_rows_in_json' tests/test_stress.py` returns 1
    - `pytest tests/test_stress.py -v --tb=no 2>&1 | grep -c XFAIL` returns 13
    - `pytest tests/test_stress.py -v --tb=no 2>&1 | grep -E '(FAILED|ERROR)' | wc -l` returns 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Create tests/test_points.py with 5 xfail stubs</name>
  <files>tests/test_points.py</files>
  <action>
    Create tests/test_points.py mirroring test_stress.py header but with these 5 stubs:

    ```python
    """Phase 8 Points Breakeven — full test surface (PNTS-01..03 + ROADMAP SC-4).

    Wave 0 (Plan 08-00) creates ALL 5 stubs as xfail. Subsequent waves flip:
    - Wave 3 (Plan 08-03 lib/points.py): PNTS-01/02 engine (2 stubs)
    - Wave 4 (Plan 08-04 scripts/points_breakeven.py): PNTS-03 CLI (2 stubs)
    - Wave 5 (Plan 08-05 fixtures): SC-4 divergence-pin (1 stub)
    """
    from __future__ import annotations

    from pathlib import Path
    from typing import TYPE_CHECKING, Any

    import pytest

    if TYPE_CHECKING:
        from collections.abc import Callable

    SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "points_breakeven.py"


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-03 ships simple_breakeven")
    def test_pnts_01_simple_breakeven_ceil_division(
        points_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """PNTS-01: months_to_breakeven == ceil(points_cost / monthly_savings)."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-03 ships npv_breakeven")
    def test_pnts_02_npv_breakeven_decision_dispatcher(
        points_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """PNTS-02: NPV-based breakeven side-by-side with simple; decision = buy_points|skip_points."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-04 ships scripts/points_breakeven.py")
    def test_pnts_03_cli_points_subprocess_round_trip(
        points_fixture: Callable[[str], dict[str, Any]],
        tmp_path: Path,
    ) -> None:
        """PNTS-03: CLI subprocess round-trip — write JSON, invoke, parse stdout."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-04 ships D-18 lazy-import + float-gate")
    def test_pnts_03_cli_help_does_not_import_lib_points_and_rejects_float() -> None:
        """PNTS-03 + D-18 + WR-02: --help fast; CLI rejects JSON-float with 6-key envelope."""
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 08-05 ships points_simple_lt_npv_seven_pct_discount.json")
    def test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin(
        points_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """ROADMAP SC-4: simple==123, npv==160 at 7% discount; diverge=true; gap=37 months."""
        pytest.fail("Wave 0 stub")
    ```
  </action>
  <acceptance_criteria>
    - File tests/test_points.py exists with at least 100 lines
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_points.py` returns 5
    - `grep -c 'def test_' tests/test_points.py` returns 5
    - `grep -c 'def test_pnts_01_simple_breakeven_ceil_division' tests/test_points.py` returns 1
    - `grep -c 'def test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin' tests/test_points.py` returns 1
    - `pytest tests/test_points.py -v --tb=no 2>&1 | grep -c XFAIL` returns 5
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 5: Verify zero regression to Phase 5 baseline</name>
  <files>(verification only)</files>
  <action>
    Run full pytest suite. Baseline expected: ≥411 passed + ≥4 skipped (Phase 5 06 SUMMARY metric). New: 18 xfailed (13 stress + 5 points). Zero failures, zero errors.

    Then mypy + ruff hygiene:
    - `mypy --strict tests/conftest.py tests/test_stress.py tests/test_points.py`
    - `ruff check tests/conftest.py tests/test_stress.py tests/test_points.py`
    - `ruff format --check tests/conftest.py tests/test_stress.py tests/test_points.py`
  </action>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows ≥ 411 passed
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ xfailed'` shows ≥ 18 xfailed
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ failed'` returns "0 failed" or no output
    - `mypy --strict tests/conftest.py tests/test_stress.py tests/test_points.py` exits 0
    - `ruff check tests/conftest.py tests/test_stress.py tests/test_points.py` exits 0
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-00-01: Wave 0 stub count = 18 total (13 stress + 5 points). Mirrors Phase 5 Wave 0 32-stub Nyquist pattern with smaller surface (Phase 8 has 7 requirements vs Phase 5's 9).
- D-00-02: All xfail decorators use `strict=True` to gate against accidental XPASS. Wave 2-5 plans MUST remove the decorator when flipping a test (T-08-10 mitigation, mirrors Phase 5 T-05-10).
- D-00-03: SCRIPT_PATH constant per CLI test file (one in test_stress.py, one in test_points.py). Phase 10 relocation = single-line edit per file.
- D-00-04: stress_fixture and points_fixture loaders are byte-equivalent clones of arm_fixture with the path component swapped — DO NOT generalize into a parametric loader (RESEARCH Q9 / LM-3 from Phase 5: explicit-per-subsystem loaders survive grep-discovery; generic loaders create indirection).
</locked_decisions>

<verify_block>
- All 13 stress + 5 points stub names present (one grep per name in acceptance_criteria)
- Full pytest suite: ≥411 passed + ≥18 xfailed + 0 failed + 0 errored
- mypy --strict + ruff clean across conftest.py + test_stress.py + test_points.py
- Three fixture directories committed (.gitkeep present, zero bytes)
- stress_fixture + points_fixture importable; existing fixtures unchanged
</verify_block>

<deviation_rules>
- Rule 1: If a stub name needs to change (e.g., to satisfy a downstream wave's clearer naming), document the rename in the SUMMARY.md and update this PLAN.md's acceptance_criteria simultaneously.
- Rule 2: If pytest discovers >18 xfails, that means some Phase 5 test got accidentally introduced by Wave 0 — STOP and audit; do NOT commit until baseline drift is explained.
- Rule 3: Hygiene-only deviations (ruff format auto-collapse of multi-line decorator strings, mypy unused-type:ignore removal after explicit None-check) are accepted without amending this plan. Pin in SUMMARY.md.
</deviation_rules>

<success_criteria>
- tests/test_stress.py + tests/test_points.py exist, both collected by pytest, all 18 stubs report XFAIL
- tests/conftest.py extended with stress_fixture + points_fixture (existing fixtures untouched)
- Three fixture directories committed via .gitkeep
- Phase 5 baseline preserved (≥411 passed + ≥4 skipped)
- mypy --strict + ruff clean across all touched files
- Waves 1-5 have a clear contract: each downstream plan flips a known xfail name and removes the decorator
</success_criteria>
