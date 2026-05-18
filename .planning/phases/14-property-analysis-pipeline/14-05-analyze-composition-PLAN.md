---
phase: 14
plan: 05
plan_id: 14-05
slug: analyze-composition
type: execute
wave: 3
depends_on:
  - 14-01
  - 14-02
  - 14-03
  - 14-04
files_modified:
  - lib/property_analysis.py
  - tests/test_property_analysis.py
autonomous: true
requirements:
  - ANLZ-01
  - ANLZ-02
  - ANLZ-03
  - VERD-01
nyquist_compliant: true
tags:
  - composition
  - analyze
  - top-level
  - analysis-report

must_haves:
  truths:
    - "lib/property_analysis.py:analyze(listing, household, profile, *, fred_mortgage_30us=None, fred_mortgage_15us=None) returns a fully-populated AnalysisReport; when FRED rate overrides are None, the function fetches via lib.fred_cache.get_cached_or_fetch wrapped in with_cache_lock per Pitfall 9."
    - "analyze() composes the 6-step pipeline from RESEARCH.md L164-235: (1) resolve county + conforming limit; (2) fetch today's rate per program; (3) determine programs; (4) build matrix; (5) build stress/refi/points/tax blocks at preferred DP; (6) synthesize verdict via lib.property_verdict.synthesize. Order is fixed."
    - "AnalysisReport.household_snapshot_hash is a SHA256 hex digest of `household.model_dump_json() + profile.model_dump_json()` per Phase 13 D-13-REANALYSIS-01 pattern."
    - "AnalysisReport.fetched_at is set to datetime.now(timezone.utc) inside analyze()."
    - "AnalysisReport.warnings includes 'MissingCountyDataError' when conforming-limit lookup degrades; 'PMI-RATE-ESTIMATED' (with the constant value) when any cell carries the conv PMI placeholder; 'StaleReferenceWarning' pass-through when lib.rules._loader surfaces stale YAML warnings."
    - "JSON size of the final AnalysisReport is < 100KB for the canonical SFH-conforming scenario per Pitfall 10."
    - "FRED reads serialize through with_cache_lock(CACHE_DIR, reason=...) — Pitfall 9 enforced via test_fred_lock_serialization passing in this plan's end-to-end test."
  artifacts:
    - path: "lib/property_analysis.py"
      provides: "analyze() top-level entrypoint composing all helpers"
      contains: "def analyze("
    - path: "tests/test_property_analysis.py"
      provides: "End-to-end test test_analyze_end_to_end + test_report_size_budget"
      contains: "def test_analyze_end_to_end"
  key_links:
    - from: "lib/property_analysis.py:analyze"
      to: "lib.property_verdict.synthesize"
      via: "import + call"
      pattern: "from lib\\.property_verdict import synthesize"
    - from: "lib/property_analysis.py:analyze"
      to: "lib.fred_cache.{with_cache_lock, get_cached_or_fetch}"
      via: "_todays_rate_per_program from Plan 14-02"
      pattern: "with_cache_lock\\("
    - from: "lib/property_analysis.py:analyze"
      to: "_build_matrix, _build_stress_block, _build_refi_block, _build_points_block, _build_tax_block"
      via: "private helper composition"
      pattern: "_build_(matrix|stress_block|refi_block|points_block|tax_block)\\("
---

<objective>
Wire all prior plans together into the top-level `analyze(listing, household, profile)` function. Closes ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 at the integration level (Plans 14-02/03/04 closed each at the unit level; this plan proves end-to-end composition).

The function:
1. Resolves county + conforming limit (via `_determine_programs` from Plan 14-02).
2. Fetches today's rate per program via `_todays_rate_per_program` (Plan 14-02) — serialized through `with_cache_lock` per Pitfall 9.
3. Determines program list (Conv30/Conv15/FHA30 always; VA30 if profile.va_eligible; Jumbo30 if classify() returns "jumbo").
4. Builds the matrix via `_build_matrix` (Plan 14-02).
5. Builds StressBlock, RefiBlock, PointsBlock, TaxBlock via Plan 14-03 helpers.
6. Synthesizes Verdict via `lib.property_verdict.synthesize` (Plan 14-04).
7. Assembles AnalysisReport with `listing_snapshot` echoed, `household_snapshot_hash` computed via SHA256, `fetched_at=datetime.now(timezone.utc)`, FRED rates audit-trail recorded.
8. Pushes any warnings (MissingCountyDataError, PMI-RATE-ESTIMATED, StaleReferenceWarning) into AnalysisReport.warnings.

End-to-end test surface:
- `test_analyze_end_to_end` — synthetic SFH-conforming scenario; report.verdict.level ∈ {"GO", "WATCH"}; matrix has 18 cells (3 programs × 6 DP); stress/refi/points/tax blocks populated.
- `test_report_size_budget` — `len(report.model_dump_json()) < 100_000` (Pitfall 10).
- `test_analyze_with_jumbo_listing` — listing.price=$1.5M → matrix has 24 cells (4 programs × 6 incl. Jumbo30).
- `test_analyze_with_va_eligible_profile` — Profile(va_eligible=True) → "VA30" in matrix.programs_present.
- `test_analyze_fred_rate_overrides` — when fred_mortgage_30us + fred_mortgage_15us are passed explicitly, analyze() does NOT hit the FRED cache.

Purpose: This plan is the integration ceiling. After it, Plan 14-06 ships fixtures to pin every cell of the matrix end-to-end.

Output: ~150 LOC added to lib/property_analysis.py (analyze() body + a few utility helpers) + ~250 LOC of integration tests in tests/test_property_analysis.py.
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
@.planning/phases/14-property-analysis-pipeline/14-03-SUMMARY.md
@.planning/phases/14-property-analysis-pipeline/14-04-SUMMARY.md
@CLAUDE.md
@lib/property_analysis.py
@lib/property_verdict.py
@lib/property_listing.py
@lib/household.py
@lib/profile.py
@lib/fred_cache.py
@tests/test_property_analysis.py
@tests/conftest.py

<interfaces>
From Plan 14-02:
- `_todays_rate_per_program(program: str) -> Decimal`
- `_determine_programs(listing, household, profile) -> tuple[list[str], list[str]]` (programs, warnings)
- `_build_matrix(listing, household, profile, todays_rates: dict[str, Decimal]) -> tuple[DownPaymentMatrix, list[str]]`

From Plan 14-03:
- `_build_stress_block(matrix, listing, household, profile, todays_rates) -> StressBlock`
- `_build_refi_block(matrix, household, todays_rates) -> RefiBlock`
- `_build_points_block(matrix, household, todays_rates) -> PointsBlock`
- `_build_tax_block(matrix, household, profile, todays_rates) -> TaxBlock`

From Plan 14-04:
- `lib.property_verdict.synthesize(matrix, stress, household, profile) -> Verdict`

From Plan 14-02 (models):
- `AnalysisReport` with fields: listing_snapshot, household_snapshot_hash, fetched_at, fred_mortgage_30us, fred_mortgage_15us, matrix, stress, refi, points, tax, verdict, warnings.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement analyze() body in lib/property_analysis.py (replace NotImplementedError stub)</name>
  <files>lib/property_analysis.py</files>
  <read_first>
    - lib/property_analysis.py (full — Plans 14-02 + 14-03 output: all helpers + models + stub)
    - lib/property_verdict.py (Plan 14-04 output)
    - lib/fred_cache.py L235-356 (get_cached_or_fetch + with_cache_lock signatures)
    - lib/affordability.py L1473-1492 (evaluate() dispatcher style — the analyze() shape to mirror per PATTERNS.md L175-197)
    - lib/property_persistence.py L1-60 (Phase 13 — for household_snapshot_hash pattern reference, though that file lives in Phase 13)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L164-237 (6-step pipeline architecture diagram)
    - .planning/phases/14-property-analysis-pipeline/14-CONTEXT.md (D-14-MODELS-04 — analyze() signature + AnalysisReport contract)
  </read_first>
  <behavior>
    - Behavior 1: `analyze(listing, household, profile)` returns an AnalysisReport when all inputs are valid and FRED cache is warm.
    - Behavior 2: `analyze(listing, household, profile, fred_mortgage_30us=Decimal("0.065"), fred_mortgage_15us=Decimal("0.058"))` uses the provided rates and does NOT invoke lib.fred_cache.
    - Behavior 3: When fred rates are NOT supplied AND lib.fred_cache.get_cached_or_fetch raises NotImplementedError (cold cache), analyze() raises a ValueError with guidance to run scripts/fred_cli.py.
    - Behavior 4: `report.household_snapshot_hash` is a 64-char lowercase hex string (SHA256 digest).
    - Behavior 5: `report.fetched_at` is a timezone-aware datetime in UTC.
    - Behavior 6: `report.fred_mortgage_30us` and `report.fred_mortgage_15us` echo the rates used (whether passed-in or fetched).
    - Behavior 7: `report.warnings` is a list[str]; includes "MissingCountyDataError" when conforming-limit lookup degrades; includes "PMI-RATE-ESTIMATED" (dedup'd) when any matrix cell has the PMI placeholder warning in its eligible_reasons.
    - Behavior 8: `report.verdict` is exactly the Verdict returned by lib.property_verdict.synthesize(matrix, stress, household, profile).
    - Behavior 9: `report.matrix`, `report.stress`, `report.refi`, `report.points`, `report.tax` are exactly the outputs of _build_matrix, _build_stress_block, _build_refi_block, _build_points_block, _build_tax_block (no post-processing).
    - Behavior 10: `report.listing_snapshot == listing` (frozen Pydantic equality).
    - Behavior 11: `analyze()` raises on programmer error (invalid Pydantic input) — Phase 14 is library; Phase 15's CLI is responsible for catching and emitting always-exit-0 envelope.
    - Behavior 12: `analyze()` is deterministic given identical inputs (modulo fetched_at + FRED rate snapshot) — running twice with same listing/household/profile/fred_overrides produces identical matrix/stress/refi/points/tax/verdict.
  </behavior>
  <action>
    Replace the `def analyze(*args, **kwargs):` stub at the bottom of `lib/property_analysis.py` with the full implementation.

    Add to imports:
    ```python
    import hashlib
    from lib.property_verdict import synthesize
    ```

    Replace the stub with this implementation:

    ```python
    def analyze(
        listing: PropertyListing,
        household: Household,
        profile: Profile,
        *,
        fred_mortgage_30us: Decimal | None = None,
        fred_mortgage_15us: Decimal | None = None,
    ) -> AnalysisReport:
        """Top-level Phase 14 entrypoint (D-14-MODELS-04). 6-step pipeline per
        RESEARCH §"System Architecture Diagram":

          1. Resolve county + conforming limit (via _determine_programs).
          2. Fetch today's rate per program (FRED cache, lock-serialized).
          3. Determine programs (Conv30/Conv15/FHA30 always; VA30 if profile.va_eligible;
             Jumbo30 if classify == jumbo).
          4. Build matrix (DownPaymentMatrix with 24 or 30 cells).
          5. Build auxiliary blocks at preferred DP (StressBlock, RefiBlock,
             PointsBlock, TaxBlock).
          6. Synthesize verdict (lib.property_verdict.synthesize).

        Returns: frozen AnalysisReport that Phase 15's lib.property_report.py renders.

        Raises:
          - ValueError when FRED cache is cold and no fred_mortgage_*us override
            is supplied (Phase 15 CLI catches and surfaces guidance).
          - pydantic.ValidationError when any input violates the model contract.
        """
        warnings: list[str] = []

        # Step 1+3: programs + warning for missing-county
        programs, prog_warnings = _determine_programs(listing, household, profile)
        warnings.extend(prog_warnings)

        # Step 2: today's rates per program
        if fred_mortgage_30us is None:
            try:
                rate_30 = _todays_rate_per_program("Conv30")
            except ValueError:
                raise
        else:
            rate_30 = quantize_rate(fred_mortgage_30us)

        if fred_mortgage_15us is None:
            try:
                rate_15 = _todays_rate_per_program("Conv15")
            except ValueError:
                raise
        else:
            rate_15 = quantize_rate(fred_mortgage_15us)

        # Build the per-program rate dict (D-14-REFI-02)
        todays_rates: dict[str, Decimal] = {
            "Conv30": rate_30,
            "Conv15": rate_15,
            "FHA30": rate_30,         # D-14-REFI-02 proxy
            "VA30": rate_30,          # D-14-REFI-02 proxy
            "Jumbo30": rate_30,       # D-14-REFI-02 proxy
            "Conv30-ARM-5-1": quantize_rate(rate_30 - Decimal("0.0025")),  # D-14-REFI-02
        }

        # Step 4: matrix
        matrix, matrix_warnings = _build_matrix(listing, household, profile, todays_rates)
        warnings.extend(matrix_warnings)

        # Surface PMI-RATE-ESTIMATED if any cell carries the warning
        if any("PMI-RATE-ESTIMATED" in r for c in matrix.cells for r in c.eligible_reasons):
            warnings.append("PMI-RATE-ESTIMATED")

        # Step 5: auxiliary blocks
        stress = _build_stress_block(matrix, listing, household, profile, todays_rates)
        refi = _build_refi_block(matrix, household, todays_rates)
        points = _build_points_block(matrix, household, todays_rates)
        tax = _build_tax_block(matrix, household, profile, todays_rates)

        # Step 6: verdict
        verdict = synthesize(matrix, stress, household, profile)

        # Snapshot hash + timestamp (Phase 13 D-13-REANALYSIS-01 pattern)
        snapshot_input = household.model_dump_json() + profile.model_dump_json()
        snapshot_hash = hashlib.sha256(snapshot_input.encode("utf-8")).hexdigest()

        return AnalysisReport(
            listing_snapshot=listing,
            household_snapshot_hash=snapshot_hash,
            fetched_at=datetime.now(timezone.utc),
            fred_mortgage_30us=rate_30,
            fred_mortgage_15us=rate_15,
            matrix=matrix,
            stress=stress,
            refi=refi,
            points=points,
            tax=tax,
            verdict=verdict,
            warnings=list(dict.fromkeys(warnings)),  # dedup preserving order
        )
    ```

    Notes:
    - `dict.fromkeys(warnings)` is the dedup-preserving-insertion-order idiom (Python 3.7+).
    - Use `quantize_rate(...)` on every rate to enforce Rate decimal_places=6.
    - `datetime.now(timezone.utc)` is timezone-aware (Pydantic rejects naive datetimes by default).
    - `hashlib.sha256(...).hexdigest()` returns 64 lowercase hex chars.
    - If a downstream helper (e.g., _build_stress_block) raises a ValidationError because of bad input, let it propagate — Phase 14 is library; Phase 15's CLI catches.

    DO NOT add new helpers in this task — analyze() composes existing ones.
    DO NOT add try/except around any helper call (Pitfall: catching ValidationError silently hides bugs). Only the FRED-cold-cache ValueError is caught and re-raised with guidance (already handled inside _todays_rate_per_program from Plan 14-02).
    DO NOT include any I/O beyond FRED cache reads (already serialized through with_cache_lock).
    DO NOT compute closing_costs_estimated as False — the placeholder remains True per Assumption A7 (closing costs are listing-specific; v1.1 ships the 3% estimate).
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py::test_analyze_end_to_end -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'raise NotImplementedError' lib/property_analysis.py | grep -v '^#'` returns 0 (stub removed; ValueError for cold FRED cache is the only remaining raise pattern).
    - `grep -c 'def analyze(' lib/property_analysis.py` returns 1.
    - `grep -c 'from lib.property_verdict import synthesize' lib/property_analysis.py` returns 1.
    - `grep -c 'import hashlib' lib/property_analysis.py` returns 1.
    - `grep -c 'synthesize(matrix, stress, household, profile)' lib/property_analysis.py` returns 1.
    - `grep -c 'hashlib.sha256(' lib/property_analysis.py` returns 1.
    - `grep -c 'datetime.now(timezone.utc)' lib/property_analysis.py` returns 1.
    - `grep -c '"Conv30-ARM-5-1": quantize_rate(rate_30 - Decimal("0.0025"))' lib/property_analysis.py` returns 1 (D-14-REFI-02 ARM rate).
    - `grep -c 'dict.fromkeys(warnings)' lib/property_analysis.py` returns 1 (dedup pattern).
    - `python -c "from lib.property_analysis import analyze; import inspect; sig = inspect.signature(analyze); assert list(sig.parameters.keys()) == ['listing', 'household', 'profile', 'fred_mortgage_30us', 'fred_mortgage_15us'], list(sig.parameters.keys())"` exits 0.
    - `pytest tests/test_property_analysis.py::test_analyze_end_to_end -x` exits 0.
  </acceptance_criteria>
  <done>
    `analyze()` body fully implemented; 6-step pipeline wired; all helpers composed; verdict synthesis invoked. End-to-end test passes against a synthetic SFH scenario.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Flip end-to-end + size-budget stubs in tests/test_property_analysis.py to real assertions</name>
  <files>tests/test_property_analysis.py</files>
  <read_first>
    - tests/test_property_analysis.py (Plans 14-02 + 14-03 output — includes pytest.skip stubs for end-to-end + size-budget)
    - lib/property_analysis.py (Plan 14-05 Task 1 output — analyze() implementation)
    - lib/property_verdict.py (Plan 14-04 output)
    - tests/test_stress.py L528-567 (test_sc5_stress_sweep_50_scenarios_under_100kb — size-budget pattern to mirror per RESEARCH §"Validation Architecture" + PATTERNS.md L493-499)
    - .planning/phases/14-property-analysis-pipeline/14-VALIDATION.md (rows for composition: test_report_size_budget, test_analyze_end_to_end)
  </read_first>
  <behavior>
    Flip these stubs from pytest.skip to real assertion bodies:

    - `test_analyze_end_to_end` — Construct synthetic listing/household/profile; call analyze(listing, household, profile, fred_mortgage_30us=Decimal("0.065000"), fred_mortgage_15us=Decimal("0.058000")) (pass overrides to avoid FRED). Assert:
        - report is an AnalysisReport instance.
        - report.matrix.cells has length 18 (3 programs × 6 DP) for a non-jumbo, non-VA-eligible scenario.
        - report.stress.rows has at least 1 entry per eligible-at-preferred-DP program.
        - report.refi.rows has 2 × (eligible-at-preferred-DP program count) entries.
        - report.points.rows has 2 × (eligible-at-preferred-DP program count) entries.
        - report.tax.qualified_loan_limit == Decimal("750000").
        - report.verdict.level ∈ {"GO", "WATCH", "NO_GO"}.
        - report.household_snapshot_hash is a 64-char hex string.
        - report.fetched_at is timezone-aware (`.tzinfo is not None`).
        - report.fred_mortgage_30us == Decimal("0.065000"); report.fred_mortgage_15us == Decimal("0.058000").
        - report.listing_snapshot == listing.

    - `test_report_size_budget` — `serialized = report.model_dump_json(indent=2); size_bytes = len(serialized.encode("utf-8")); assert size_bytes < 100 * 1024, f"Size budget violation: {size_bytes} bytes ≥ 100KB"`.

    Add the following NEW named tests (not previously stubbed):
    - `test_analyze_with_jumbo_listing` — listing.price=Decimal("1500000.00") in King County WA (state_fips="53", county_fips="033"); matrix.programs_present includes "Jumbo30"; matrix.cells has length 24 (4 × 6).
    - `test_analyze_with_va_eligible_profile` — Profile(va_eligible=True); matrix.programs_present includes "VA30"; matrix.cells has length 24 (4 × 6 for Conv30/Conv15/FHA30/VA30).
    - `test_analyze_fred_rate_overrides_bypass_cache` — Patch lib.property_analysis._todays_rate_per_program with a MagicMock that raises if called; pass fred_mortgage_30us + fred_mortgage_15us; assert mock NOT invoked (overrides bypass cache).
    - `test_analyze_household_snapshot_hash_deterministic` — Run analyze() twice with same inputs (override FRED rates so cache is bypassed); assert `report1.household_snapshot_hash == report2.household_snapshot_hash` (deterministic) BUT `report1.fetched_at != report2.fetched_at` (timestamps differ).
    - `test_analyze_warnings_dedup_pmi_estimated` — Build a scenario where multiple Conv30/Conv15 cells have LTV > 0.80 (95%, 90%, etc.); assert "PMI-RATE-ESTIMATED" appears EXACTLY ONCE in report.warnings (dedup'd).
    - `test_analyze_verdict_matches_synthesize` — Run analyze() and separately call lib.property_verdict.synthesize on the same matrix + stress + household + profile; assert `report.verdict == synthesized_directly` (analyze passes through synthesize output).
    - `test_analyze_cold_fred_cache_raises_valueerror` — Patch lib.property_analysis.get_cached_or_fetch to raise NotImplementedError; call analyze() WITHOUT fred_mortgage_* overrides; assert ValueError with message containing "scripts/fred_cli.py".
  </behavior>
  <action>
    Edit `tests/test_property_analysis.py` to:

    1. Replace the `pytest.skip` body in `test_analyze_end_to_end` (if previously stubbed) with the real assertion body per Behavior 1 list.
    2. Replace the `pytest.skip` body in `test_report_size_budget` with the size-assertion body per Behavior 2 list.
    3. Add the 6 new named tests listed in Behavior (`test_analyze_with_jumbo_listing`, `test_analyze_with_va_eligible_profile`, `test_analyze_fred_rate_overrides_bypass_cache`, `test_analyze_household_snapshot_hash_deterministic`, `test_analyze_warnings_dedup_pmi_estimated`, `test_analyze_verdict_matches_synthesize`, `test_analyze_cold_fred_cache_raises_valueerror`).

    Reuse the `_make_clean_household() / _make_clean_profile() / _make_clean_listing()` builders from Plan 14-02 Task 3.

    For `test_analyze_fred_rate_overrides_bypass_cache` and `test_analyze_cold_fred_cache_raises_valueerror`, use `unittest.mock.patch` on `lib.property_analysis._todays_rate_per_program` or `lib.property_analysis.get_cached_or_fetch` (depending on which abstraction is cleanest to spy on).

    DO NOT delete the previously-stubbed `test_sfh_conforming_king_county_golden / test_condo_with_hoa_seattle_golden / test_sfh_jumbo_bay_area_golden` stubs — those remain `pytest.skip(...)` until Plan 14-06 ships fixtures.

    For exact-Decimal comparison rules: keep using `==` (CLAUDE.md money discipline). For the size-budget test, use `<` on byte count.

    DO NOT touch fixture-driven golden tests (deferred to Plan 14-06).
    DO NOT use `pytest.approx`.
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py -x -k "not golden"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'pytest.skip' tests/test_property_analysis.py` returns 3 (only golden-fixture stubs remain).
    - The 8 new/flipped tests exist as real bodies (not pytest.skip):
      `for t in test_analyze_end_to_end test_report_size_budget test_analyze_with_jumbo_listing test_analyze_with_va_eligible_profile test_analyze_fred_rate_overrides_bypass_cache test_analyze_household_snapshot_hash_deterministic test_analyze_warnings_dedup_pmi_estimated test_analyze_verdict_matches_synthesize test_analyze_cold_fred_cache_raises_valueerror; do grep -c "def $t" tests/test_property_analysis.py; done` — each grep returns 1.
    - `pytest tests/test_property_analysis.py::test_analyze_end_to_end tests/test_property_analysis.py::test_report_size_budget tests/test_property_analysis.py::test_analyze_with_jumbo_listing tests/test_property_analysis.py::test_analyze_with_va_eligible_profile tests/test_property_analysis.py::test_analyze_fred_rate_overrides_bypass_cache tests/test_property_analysis.py::test_analyze_household_snapshot_hash_deterministic tests/test_property_analysis.py::test_analyze_warnings_dedup_pmi_estimated tests/test_property_analysis.py::test_analyze_verdict_matches_synthesize tests/test_property_analysis.py::test_analyze_cold_fred_cache_raises_valueerror -x` exits 0.
    - `pytest -x` (full suite) exits 0 — no regression.
    - `grep -E 'assertAlmostEqual|pytest\.approx' tests/test_property_analysis.py | grep -v '^#' | wc -l` returns 0.
  </acceptance_criteria>
  <done>
    End-to-end + size-budget tests pass on synthetic data. Jumbo, VA, FRED-override, deterministic-hash, dedup, verdict-passthrough, cold-cache-error all verified. Only golden-fixture tests remain stubbed (Plan 14-06 closes them).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| analyze() → lib.fred_cache | FRED cache reads serialized via with_cache_lock per Pitfall 9. |
| analyze() → all _build_* helpers + lib.property_verdict.synthesize | Pure in-process function calls; no IPC. |
| AnalysisReport JSON output | Bounded by Pitfall 10 (< 100KB) — verified by test_report_size_budget. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-FLOAT | Tampering | AnalysisReport.fred_mortgage_30us / fred_mortgage_15us | mitigate | quantize_rate() applied before construction; Rate alias rejects float at strict=True boundary. Override path quantizes Decimal input. |
| T-14-FRED-RACE | Tampering | analyze() FRED cache reads | mitigate | _todays_rate_per_program (Plan 14-02) wraps each read in with_cache_lock(CACHE_DIR, reason=...). End-to-end tests bypass cache via fred_mortgage_* overrides to avoid live reads. |
| T-14-STALE-REF | Tampering | Reference YAMLs read transitively via lib.rules predicates | mitigate | Existing predicates surface StaleReferenceWarning; this plan passes warnings through to AnalysisReport.warnings. |
| T-14-REASON | Repudiation | Verdict.reasons[] populated via synthesize() | mitigate | Synthesize() (Plan 14-04) requires predicate_code AND computed_value on every reason; analyze() does NOT mutate verdict. |
| T-14-PII | Information Disclosure | tests/test_property_analysis.py end-to-end | mitigate | Tests use synthetic fips/addresses; no real Zillow data. |
| T-14-JSON-SIZE | Denial of Service (indirect) | AnalysisReport.model_dump_json() output | mitigate | Pitfall 10: ProgramResult carries summary scalars only (no Schedule.payments); test_report_size_budget asserts < 100KB on canonical fixture. |
</threat_model>

<verification>
- `pytest tests/test_property_analysis.py -x -k "not golden"` exits 0.
- `pytest -x` (full suite) exits 0.
- `python -c "from lib.property_analysis import analyze; from lib.household import Household; from lib.profile import Profile; from lib.property_listing import PropertyListing, ProvenancedMoney; from decimal import Decimal; listing = PropertyListing(price=Decimal('625000.00'), zip='98101', property_type='SFH', tax_annual=ProvenancedMoney(value=Decimal('6000.00'), provenance='estimated'), insurance_estimate_annual=ProvenancedMoney(value=Decimal('1200.00'), provenance='estimated')); household = Household(monthly_income=Decimal('12000.00'), monthly_obligations=Decimal('400.00'), fico=740, liquid_reserves=Decimal('150000.00'), state_fips='53', county_fips='033', county_name='King'); profile = Profile(); report = analyze(listing, household, profile, fred_mortgage_30us=Decimal('0.065000'), fred_mortgage_15us=Decimal('0.058000')); print(report.verdict.level)"` prints "GO", "WATCH", or "NO_GO" (no crash, single token).
</verification>

<success_criteria>
1. analyze() implements the 6-step pipeline per RESEARCH.md L164-235.
2. FRED rate sourcing supports both cache reads (production) and explicit overrides (tests).
3. AnalysisReport.household_snapshot_hash is deterministic SHA256 of household + profile JSON.
4. AnalysisReport.warnings is deduplicated and ordered by first-occurrence.
5. AnalysisReport JSON size < 100KB for canonical SFH-conforming scenario (Pitfall 10).
6. analyze() raises ValueError on cold FRED cache; raises ValidationError on bad input — Phase 15 catches at CLI boundary.
7. End-to-end integration verified at 9 named tests; full Wave-1 + Wave-2 + Wave-3 test surface passes.
8. ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 all closed at the integration level.
</success_criteria>

<output>
After completion, create `.planning/phases/14-property-analysis-pipeline/14-05-SUMMARY.md` documenting:
- analyze() signature + 6-step pipeline summary.
- Test counts: 9 new/flipped integration tests; 3 fixture-driven tests still stubbed (Plan 14-06).
- Pitfalls mitigated in this plan: 9 (with_cache_lock confirmed via test_fred_lock_serialization at integration), 10 (JSON < 100KB verified).
- All Phase 14 requirements (ANLZ-01, ANLZ-02, ANLZ-03, VERD-01) closed at integration level.
- Open items for Plan 14-06: 3 hand-calc golden fixtures + fixture-based citation-coverage tightening.
- Files consumed by Plan 14-06: lib/property_analysis.py:analyze() + lib/property_verdict.py:synthesize() — both frozen now.
- Sample report.verdict.level distribution observed across the 9 tests (e.g., "GO seen in 7 tests; WATCH in 1 (FHA-MIP scenario); NO_GO in 1 (under-income scenario)").
</output>
