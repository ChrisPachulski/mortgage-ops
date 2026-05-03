---
phase: 06
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_refinance.py
  - tests/fixtures/refinance/.gitkeep
autonomous: true
requirements: []
tags:
  - phase-06
  - refinance-npv
  - test-infrastructure
  - nyquist
must_haves:
  truths:
    - "tests/test_refinance.py exists and is collected by pytest"
    - "Every Phase 6 requirement (REFI-01..09) plus every ROADMAP SC-1..SC-5 plus the SC-4 sign-validator coverage has a stub function with @pytest.mark.xfail(strict=True)"
    - "Stubbed file runs (pytest tests/test_refinance.py -v) without ImportError; xfail tests show as XFAIL not ERROR"
    - "tests/conftest.py exposes refinance_fixture pytest fixture loadable by name from any test (mirrors arm_fixture from Phase 5)"
    - "tests/fixtures/refinance/ directory is committed (via .gitkeep)"
    - "Phase 6 test scaffold is additive: no behavior change to Phase 1/3/4/5 production code or existing tests; only adds new xfail-decorated stubs that downstream waves flip"
  artifacts:
    - path: "tests/test_refinance.py"
      provides: "~25 xfail stubs covering REFI-01..09 + SC-1..5 + sign-validator + breakeven-divergence + after-tax + envelope-uniformity"
      min_lines: 200
    - path: "tests/conftest.py"
      provides: "refinance_fixture loader (parallel to arm_fixture / affordability_fixture)"
      contains: "def refinance_fixture"
    - path: "tests/fixtures/refinance/.gitkeep"
      provides: "Empty placeholder to commit hand-calc fixture directory"
  key_links:
    - from: "tests/test_refinance.py"
      to: "tests/conftest.py"
      via: "refinance_fixture parametric injection"
      pattern: "def test_.*\\(.*refinance_fixture"
    - from: "Wave 1..6 plans"
      to: "tests/test_refinance.py xfail decorators"
      via: "incremental flip from xfail → pass as engine slices land"
      pattern: "@pytest.mark.xfail"
---

<objective>
Establish Phase 6 test scaffolding that subsequent waves flip xfail→pass against. Ship the `refinance_fixture` pytest fixture loader, ~25 xfail-decorated stubs covering every REFI-01..09 + SC-1..5 + sign-validator + envelope-uniformity, and the empty `tests/fixtures/refinance/` directory.

Purpose: Nyquist validation gate. Every requirement-closing wave (Plans 06-01..06) flips a specific xfail to a real assertion. Without Wave 0, downstream plans have no test landing pads.

Output: A test file that COLLECTS but xfails everything; a conftest.py extension; one empty fixture directory. Zero engine code, zero fixture content.
</objective>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/06-refinance-npv/06-RESEARCH.md
@.planning/phases/06-refinance-npv/06-PATTERNS.md
@CLAUDE.md
@tests/conftest.py
@tests/test_arm.py
@tests/test_affordability.py
</context>

<test_inventory>
The 25 xfail stubs in tests/test_refinance.py — names locked verbatim:

REFI-01 (rate-and-term NPV) — 3 tests:
- test_refi_rate_and_term_positive_npv         (SC-1; flipped Wave 5)
- test_refi_rate_and_term_negative_npv         (SC-1; flipped Wave 5)
- test_refi_npv_decimal_exact                  (D-04 sign rigor; flipped Wave 5)

REFI-02 (cash-out) — 3 tests:
- test_refi_cash_out_proceeds                  (SC-3; flipped Wave 5)
- test_refi_cash_out_new_monthly_pi            (SC-3; flipped Wave 5)
- test_refi_cash_out_total_interest_delta      (SC-3; flipped Wave 5)

REFI-03 (breakeven dual reporting) — 3 tests:
- test_refi_breakeven_simple_labeled           (SC-2; flipped Wave 5)
- test_refi_breakeven_npv_labeled              (SC-2; flipped Wave 5)
- test_refi_breakeven_divergence_documented    (SC-2 divergence fixture; flipped Wave 5)

REFI-04 (pyxirr deferral) — 1 test:
- test_pyxirr_deferred_to_phase11_documented   (D-07; flipped Wave 6)

REFI-05/06/07 (positive/negative/cash-out fixtures) — covered by REFI-01/02 above.

REFI-08 (CLI) — 6 tests:
- test_cli_smoke_subprocess_round_trip         (Wave 4)
- test_cli_help_does_not_import_lib_refinance  (D-18; Wave 4)
- test_cli_rejects_float_closing_costs         (D-19/WR-02; Wave 4)
- test_cli_rejects_float_discount_rate         (D-19/WR-02; Wave 4)
- test_cli_error_envelope_uniformity           (D-19/WR-02; Wave 4)
- test_cli_help_cites_references_refi_npv      (SC-5 mandate; Wave 4)

REFI-09 (references doc) — 3 tests:
- test_refi_npv_doc_sections_present           (SC-5; Wave 6)
- test_refi_npv_doc_sign_convention_phrase     (SC-5 verbatim "outflows negative, savings positive"; Wave 6)
- test_lib_refinance_module_docstring_cites    (D-16; Wave 2)

SC-4 sign-validator (model-layer) — 4 tests:
- test_refi_cashflow_outflow_positive_rejected (SC-4 verbatim; Wave 1)
- test_refi_cashflow_inflow_negative_rejected  (SC-4 verbatim; Wave 1)
- test_refi_cashflow_zero_accepted_either_dir  (D-14; Wave 1)
- test_refi_cashflow_correctly_signed_passes   (Wave 1)

Cross-cutting — 2 tests:
- test_refi_cashflow_kind_citation_coverage    (D-03 Literal coverage; Wave 5)
- test_after_tax_mode_validator_requires_all   (D-09; Wave 3)

TOTAL: 25 xfail stubs.
</test_inventory>

<tasks>

<task type="auto">
  <name>Task 1: Extend tests/conftest.py with refinance_fixture loader</name>
  <files>tests/conftest.py</files>
  <action>
    Append to tests/conftest.py (after the existing arm_fixture appended in Plan 05-00). Verbatim shape with `arm` → `refinance` swap:

    ```python


    @pytest.fixture
    def refinance_fixture() -> Callable[[str], dict[str, Any]]:
        """Return a callable that loads a single refi fixture by filename stem
        from tests/fixtures/refinance/. Mirrors arm_fixture / affordability_fixture
        / amortize_fixture — one-fixture-per-file shape; loader takes a filename
        stem like "positive_npv_200bps_drop_2k_costs", not an id within an array.

        Per Phase 6 D-15: every Phase 6 fixture lives under tests/fixtures/refinance/
        as one .json per scenario.
        """

        def _load(stem: str) -> dict[str, Any]:
            path = FIXTURE_DIR / "refinance" / f"{stem}.json"
            return json.loads(path.read_text())  # type: ignore[no-any-return]

        return _load
    ```

    Do NOT modify any existing fixture function.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python -c "from tests.conftest import refinance_fixture; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def refinance_fixture' tests/conftest.py` returns 1
    - `grep -c 'def arm_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'def affordability_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'fixtures" / "refinance"' tests/conftest.py` returns 1
    - `pytest tests/test_arm.py tests/test_affordability.py tests/test_amortize.py --collect-only -q` exits 0 (no regression)
  </acceptance_criteria>
  <done>
    refinance_fixture importable from tests.conftest; existing fixtures unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/fixtures/refinance/.gitkeep</name>
  <files>tests/fixtures/refinance/.gitkeep</files>
  <action>
    Create empty file `tests/fixtures/refinance/.gitkeep` (zero bytes) so the directory commits.
  </action>
  <verify>
    <automated>test -f /Users/cujo253/Documents/mortgage-ops/tests/fixtures/refinance/.gitkeep && wc -c /Users/cujo253/Documents/mortgage-ops/tests/fixtures/refinance/.gitkeep</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/fixtures/refinance/.gitkeep` exits 0
    - `wc -c tests/fixtures/refinance/.gitkeep` reports 0
  </acceptance_criteria>
  <done>
    Directory exists, committable.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create tests/test_refinance.py with 25 xfail stubs</name>
  <files>tests/test_refinance.py</files>
  <action>
    Create the file. Module header mirrors tests/test_arm.py (lines 1-300). Every stub uses `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 06-NN ...")`. Stub bodies: `pytest.fail("Wave 0 stub")`. Imports cover json, re, subprocess, sys, Decimal, Path, pytest, TYPE_CHECKING/Callable.

    Module-level constants:
    ```python
    SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "refi_npv.py"
    REFINANCE_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "refinance.py"
    REFI_NPV_DOC_PATH: Path = Path(__file__).resolve().parent.parent / "references" / "refi-npv.md"
    ```

    Each of the 25 names from <test_inventory> above is a separate `def test_…() -> None:` decorated `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 06-XX <slug>")`. Reason field cites the wave that flips it (per the inventory mapping).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_refinance.py -v --tb=no 2>&1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_refinance.py` returns 25
    - `grep -c 'def test_' tests/test_refinance.py` returns 25
    - Every stub name from <test_inventory> appears exactly once (per-name grep)
    - `grep -c 'SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "refi_npv.py"' tests/test_refinance.py` returns 1
    - `pytest tests/test_refinance.py -v --tb=no 2>&1 | grep -c XFAIL` returns 25
    - `pytest tests/test_refinance.py -v --tb=no 2>&1 | grep -E '(FAILED|ERROR)' | wc -l` returns 0
  </acceptance_criteria>
  <done>
    tests/test_refinance.py collected by pytest, runs to 25 XFAIL outcomes, zero passes/failures/errors.
  </done>
</task>

<task type="auto">
  <name>Task 4: Verify zero regression to Phase 5 baseline</name>
  <action>
    Run full pytest + mypy + ruff. Phase 5 baseline = 432 passed + 4 skipped + 1 strict xfail (per ROADMAP.md). After Wave 0 the count should be 432 passed + 4 skipped + 26 xfailed (= 1 inherited + 25 new), zero failures.
    Run: pytest -q; mypy --strict tests/conftest.py tests/test_refinance.py; ruff check tests/conftest.py tests/test_refinance.py; ruff format --check tests/conftest.py tests/test_refinance.py.
  </action>
  <acceptance_criteria>
    - `pytest -q` shows ≥ 432 passed
    - `pytest -q` shows ≥ 25 new xfailed (total ≥ 26 xfailed)
    - 0 failed, 0 errors
    - mypy --strict + ruff clean
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-00 (this plan): Wave 0 ships test scaffold ONLY. No engine code, no fixtures, no references doc. Subsequent waves flip the 25 xfail stubs in their assigned wave per the test_inventory mapping.
</locked_decisions>

<verify_block>
- All 25 expected stub names present in tests/test_refinance.py (per-name grep in acceptance_criteria)
- Full pytest suite: ≥ 432 passed + ≥ 26 xfailed + 0 failed + 0 errored
- mypy --strict + ruff clean across conftest.py + test_refinance.py
- tests/fixtures/refinance/ committed (.gitkeep present, zero bytes)
- refinance_fixture importable; existing fixtures unchanged
</verify_block>

<deviation_rules>
- Rule-1 (test names): the 25 stub names are LOCKED verbatim. If a downstream wave needs a different test name, it MUST flip its assigned xfail (rename inside same plan) AND document a Rule-1 deviation in its SUMMARY.md.
- Rule-2 (xfail strictness): every stub uses `strict=True`. If a stub passes accidentally during a later wave, the xfail decorator MUST be removed in the SAME plan that fixes the test. XPASS is a hard failure.
- Rule-3 (additive only): zero modification to Phase 1/3/4/5 production code or tests. If Wave 0 surfaces a regression in conftest.py, STOP and route through gsd-debug.
</deviation_rules>

<success_criteria>
- tests/test_refinance.py exists, collected by pytest, all 25 stubs report XFAIL
- tests/conftest.py extended with refinance_fixture (existing fixtures untouched)
- tests/fixtures/refinance/ committed via .gitkeep
- Phase 5 baseline preserved (≥ 432 passed)
- mypy --strict + ruff format clean across all touched files
- Waves 1..6 have a clear contract: each downstream plan flips a known xfail name and removes the decorator
</success_criteria>
