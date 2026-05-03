---
phase: 08
plan: 05
type: execute
wave: 5
depends_on: ["08-00", "08-01", "08-02", "08-03", "08-04"]
files_added:
  - tests/fixtures/stress/rate_shock_400k_30yr_grid_5_rates.json
  - tests/fixtures/stress/rate_shock_200k_30yr_grid_3_rates.json
  - tests/fixtures/stress/rate_shock_baseline_label_override.json
  - tests/fixtures/stress/rate_shock_size_budget_50_rates.json
  - tests/fixtures/stress/rate_shock_invariant_check.json
  - tests/fixtures/stress/income_shock_5_10_20_pct.json
  - tests/fixtures/stress/income_shock_threshold_0_50.json
  - tests/fixtures/stress/income_shock_zero_reduction_baseline_match.json
  - tests/fixtures/stress/arm_path_5_1_three_canonical_paths.json
  - tests/fixtures/stress/arm_path_floor_binding.json
  - tests/fixtures/stress/arm_path_30yr_horizon_invariant.json
  - tests/fixtures/points/points_simple_eq_npv_zero_discount.json
  - tests/fixtures/points/points_simple_lt_npv_seven_pct_discount.json
  - tests/fixtures/points/points_negative_savings_warning.json
files_modified:
  - tests/test_stress.py
  - tests/test_points.py
autonomous: true
requirements: ["STRS-01", "STRS-02", "STRS-03", "STRS-04", "PNTS-01", "PNTS-02", "PNTS-03"]
tags:
  - phase-08
  - stress-points
  - fixtures
  - tests
must_haves:
  truths:
    - "11 stress fixtures + 3 points fixtures shipped under tests/fixtures/stress/ and tests/fixtures/points/"
    - "Every fixture file is valid JSON, loadable via stress_fixture / points_fixture loaders"
    - "Every fixture file carries a _meta.citation field documenting the hand-calc oracle source"
    - "All remaining Wave 0 xfails flipped to fixture-driven assertions (count = previous remaining 2 → 0)"
    - "ROADMAP SC-5 size assertion: rate_shock_size_budget_50_rates produces serialized JSON < 100KB AND summary.table appears before rows when serialized via model_dump_json(indent=2)"
    - "ROADMAP SC-4 divergence pin: points_simple_lt_npv_seven_pct_discount produces simple_breakeven=123 + npv_breakeven=160 + diverge=True"
    - "Citation-coverage meta-test asserts every Phase 8 requirement (STRS-01..04 + PNTS-01..03) has at least one fixture exercising it"
---

<objective>
Ship the 14 hand-calc fixtures pinned in 08-RESEARCH §10, flip the remaining Wave 0 xfails to fixture-driven assertions, and add the citation-coverage meta-test that asserts every Phase 8 requirement is exercised by at least one fixture.

This plan is the FINAL closure plan for STRS-01..04 + PNTS-01..03. All ROADMAP SC-1 through SC-5 should be verifiable verbatim by tests after this plan completes.
</objective>

<context>
@.planning/phases/08-stress-points/08-RESEARCH.md (§10 fixture catalog)
@tests/fixtures/golden_pmt.json (Phase 1 fixture format reference)
@tests/fixtures/affordability/*.json (Phase 4 one-fixture-per-file format)
@tests/fixtures/arm/*.json (Phase 5 one-fixture-per-file format)
@lib/stress.py (Wave 2 engine)
@lib/points.py (Wave 3 engine)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Generate 5 rate-shock fixtures</name>
  <files>tests/fixtures/stress/rate_shock_*.json (5 files)</files>
  <action>
    For each fixture, run lib.stress.evaluate(req) in a small Python script to produce the engine-emitted Decimal-string values, then commit the captured request + expected response with a `_meta.citation` field. Do NOT hand-derive monthly_pi values from formulas — let the engine emit them so fixtures are exact-equality (Phase 3 D-04 idiom inherited).

    Fixture 1 — `rate_shock_400k_30yr_grid_5_rates.json` (ROADMAP SC-1 verbatim):
    ```json
    {
      "_meta": {
        "citation": "ROADMAP SC-1 verbatim example: $400k @ 30yr; rates 0.06..0.08 step 0.005; baseline default (rates[0]=0.06)",
        "engine_version": "Phase 8 Plan 08-02"
      },
      "request": {
        "mode": "rate-shock",
        "loan": {
          "principal": "400000.00",
          "annual_rate": "0.060000",
          "term_months": 360,
          "origination_date": "2026-01-01",
          "loan_type": "conventional"
        },
        "rates": ["0.060000", "0.065000", "0.070000", "0.075000", "0.080000"]
      },
      "expected": {
        "mode": "rate-shock",
        "scenario_count": 5,
        "summary_baseline_label": "0.060000",
        "summary_worst_case_label": "0.080000",
        "row_monthly_pi_at_index_1": "2528.27",
        "row_monthly_pi_at_index_3": "2796.86",
        "stress_invariant_violations": []
      }
    }
    ```

    Fixture 2 — `rate_shock_200k_30yr_grid_3_rates.json` (Wikipedia oracle anchor at rate=0.065):
    ```json
    {
      "_meta": {
        "citation": "Phase 1 Wikipedia oracle: $200k @ 6.5%/30yr → $1264.14 monthly_pi (FND-09); pinned as rate-shock cell"
      },
      "request": {
        "mode": "rate-shock",
        "loan": {"principal": "200000.00", "annual_rate": "0.050000", "term_months": 360, "origination_date": "2026-01-01", "loan_type": "conventional"},
        "rates": ["0.050000", "0.065000", "0.080000"]
      },
      "expected": {
        "row_monthly_pi_at_label_0_065000": "1264.14"
      }
    }
    ```

    Fixture 3 — `rate_shock_baseline_label_override.json` (explicit baseline override):
    ```json
    {
      "_meta": {"citation": "08-RESEARCH §2.4 #3: explicit baseline_label='0.05' on a 0.04/0.05/0.06 grid"},
      "request": {
        "mode": "rate-shock",
        "loan": {"principal": "300000.00", "annual_rate": "0.040000", "term_months": 180, "origination_date": "2026-01-01", "loan_type": "conventional"},
        "rates": ["0.040000", "0.050000", "0.060000"],
        "baseline_label": "0.050000"
      },
      "expected": {
        "summary_baseline_label": "0.050000",
        "row_delta_vs_baseline_monthly_at_index_1": "0.00"
      }
    }
    ```

    Fixture 4 — `rate_shock_size_budget_50_rates.json` (SC-5 size pin):
    ```json
    {
      "_meta": {"citation": "ROADMAP SC-5: 50-scenario sweep MUST serialize under 100KB"},
      "request": {
        "mode": "rate-shock",
        "loan": {"principal": "400000.00", "annual_rate": "0.040000", "term_months": 360, "origination_date": "2026-01-01", "loan_type": "conventional"},
        "rates": ["0.040000", "0.041000", "0.042000", ... 50 entries through "0.089000"]
      },
      "expected": {
        "scenario_count": 50,
        "max_serialized_bytes": 102400
      }
    }
    ```
    (Generate the 50-rate list by `[f"0.0{40+i:02d}000" for i in range(50)]` per the script; commit the resulting list verbatim.)

    Fixture 5 — `rate_shock_invariant_check.json` (AMRT-07 carry-through):
    ```json
    {
      "_meta": {"citation": "AMRT-07 invariant: sum of payments per cell == loan.principal exactly"},
      "request": {
        "mode": "rate-shock",
        "loan": {"principal": "400000.00", "annual_rate": "0.050000", "term_months": 360, "origination_date": "2026-01-01", "loan_type": "conventional"},
        "rates": ["0.050000", "0.065000", "0.080000"]
      },
      "expected": {
        "invariant_amrt_07": true
      }
    }
    ```
  </action>
  <acceptance_criteria>
    - 5 files exist under tests/fixtures/stress/ matching the names above
    - Each loads as valid JSON
    - Each has a _meta.citation field
    - Fixture 4's request.rates list has exactly 50 entries
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Generate 3 income-shock fixtures</name>
  <files>tests/fixtures/stress/income_shock_*.json (3 files)</files>
  <action>
    Fixture 6 — `income_shock_5_10_20_pct.json` (ROADMAP SC-2 verbatim):
    ```json
    {
      "_meta": {"citation": "ROADMAP SC-2 verbatim: --reductions 0.05,0.10,0.20 over a baseline AffordabilityRequest"},
      "request": {
        "mode": "income-shock",
        "base_request": { /* full forward-mode AffordabilityRequest with $10k joint income, $400k loan @ 6.5%, 30yr conventional */ },
        "reductions": ["0.050000", "0.100000", "0.200000"],
        "dti_threshold": "0.430000"
      },
      "expected": {
        "scenario_count": 3,
        "row_dti_back_at_index_0_must_be_lt_0_43": true,
        "row_breaches_threshold_at_index_2_must_be_true": true
      }
    }
    ```

    Fixture 7 — `income_shock_threshold_0_50.json` (caller-supplied higher threshold):
    ```json
    {
      "_meta": {"citation": "08-RESEARCH §3.4 #2: same baseline + reductions, threshold=0.50 → none breach"},
      "request": {
        "mode": "income-shock",
        "base_request": { /* same as fixture 6 */ },
        "reductions": ["0.050000", "0.100000", "0.200000"],
        "dti_threshold": "0.500000"
      },
      "expected": {
        "all_breaches_false": true
      }
    }
    ```

    Fixture 8 — `income_shock_zero_reduction_baseline_match.json` (sanity invariant):
    ```json
    {
      "_meta": {"citation": "08-RESEARCH §3.4 #3: reduction=0.0 row's dti_back EXACTLY matches evaluate(base_request).dti_back"},
      "request": {
        "mode": "income-shock",
        "base_request": { /* same baseline */ },
        "reductions": ["0.000000"],
        "dti_threshold": "0.430000"
      },
      "expected": {
        "row_0_dti_back_equals_baseline": true
      }
    }
    ```

    The `base_request` block in fixtures 6-8 should be a fully-valid forward-mode AffordabilityRequest matching Phase 4's schema (household + max_dti + target_loan_type + term_months + annual_rate + loan_amount + property_value). Reuse a known-good AffordabilityRequest from tests/fixtures/affordability/ as the seed.
  </action>
  <acceptance_criteria>
    - 3 files exist under tests/fixtures/stress/
    - Each loads as valid JSON
    - Each has a _meta.citation field
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Generate 3 ARM-path fixtures</name>
  <files>tests/fixtures/stress/arm_path_*.json (3 files)</files>
  <action>
    Fixture 9 — `arm_path_5_1_three_canonical_paths.json` (ROADMAP SC-3 verbatim):
    ```json
    {
      "_meta": {"citation": "ROADMAP SC-3 verbatim: parallel-shift, gradual-rise, fall-then-rise on 5/1 ARM 30yr"},
      "request": {
        "mode": "arm-reset",
        "base_arm_request": {
          "loan": {"principal": "400000.00", "annual_rate": "0.060000", "term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"},
          "arm_terms": {
            "initial_period_months": 60, "reset_period_months": 12,
            "initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500,
            "floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"
          },
          "assumed_index_rate": "0.050000"
        },
        "paths": [
          {"name": "parallel-shift", "params": {"shift_bps": 200}},
          {"name": "gradual-rise", "params": {"step_bps": 25}},
          {"name": "fall-then-rise", "params": {"drop_bps": 100, "rise_bps": 200}}
        ]
      },
      "expected": {
        "scenario_count": 3,
        "all_total_interest_positive": true,
        "ordering_parallel_shift_total_interest_gt_fall_then_rise": true
      }
    }
    ```

    Fixture 10 — `arm_path_floor_binding.json` (D-10 applied_cap=='floor' citation coverage):
    Same shape but with `floor_rate: "0.040000"` and `fall-then-rise` with `drop_bps: 400` so the floor binds in the fall window. Expected: at least one ResetEvent in the fall-then-rise schedule has applied_cap=="floor".

    Fixture 11 — `arm_path_30yr_horizon_invariant.json`:
    Same shape (any single canonical path will do); expected reset_count == 25 (5/1 ARM 30yr triggers: 61, 73, ..., 349 = 25 resets).
  </action>
  <acceptance_criteria>
    - 3 files exist under tests/fixtures/stress/
    - Each loads as valid JSON
    - Each has a _meta.citation field
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Generate 3 points fixtures</name>
  <files>tests/fixtures/points/points_*.json (3 files)</files>
  <action>
    Fixture 12 — `points_simple_eq_npv_zero_discount.json`:
    ```json
    {
      "_meta": {"citation": "08-RESEARCH §5.4: zero discount → NPV breakeven == simple breakeven; diverge=False"},
      "request": {
        "mode": "from_savings",
        "points_cost": "8000.00",
        "monthly_savings": "65.40",
        "hold_period_months": 240,
        "discount_rate_annual": "0.000000"
      },
      "expected": {
        "simple_breakeven_months": 123,
        "npv_breakeven_months": 123,
        "diverge": false,
        "decision": "buy_points"
      }
    }
    ```

    Fixture 13 — `points_simple_lt_npv_seven_pct_discount.json` (ROADMAP SC-4 divergence pin):
    ```json
    {
      "_meta": {"citation": "ROADMAP SC-4 + 08-RESEARCH §5.4: 7% discount → simple=123, npv=160, diverge=True (37-month gap)"},
      "request": {
        "mode": "from_savings",
        "points_cost": "8000.00",
        "monthly_savings": "65.40",
        "hold_period_months": 240,
        "discount_rate_annual": "0.070000"
      },
      "expected": {
        "simple_breakeven_months": 123,
        "npv_breakeven_months": 160,
        "diverge": true,
        "decision": "buy_points"
      }
    }
    ```

    Fixture 14 — `points_negative_savings_warning.json`:
    ```json
    {
      "_meta": {"citation": "PNTS-01 edge case: negative monthly_savings → both outputs None + warning"},
      "request": {
        "mode": "from_savings",
        "points_cost": "8000.00",
        "monthly_savings": "-10.00",
        "hold_period_months": 120,
        "discount_rate_annual": "0.070000"
      },
      "expected": {
        "simple_breakeven_months": null,
        "npv_breakeven_months": null,
        "decision": "skip_points",
        "warnings_contains_negative_savings": true
      }
    }
    ```
  </action>
  <acceptance_criteria>
    - 3 files exist under tests/fixtures/points/
    - Each loads as valid JSON
    - Each has a _meta.citation field
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 5: Flip remaining xfails to fixture-driven assertions + add citation-coverage meta-test</name>
  <files>tests/test_stress.py, tests/test_points.py</files>
  <action>
    Flip the 1 remaining stress xfail (`test_sc5_stress_sweep_50_scenarios_under_100kb`) and the 1 remaining points xfail (`test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin`):

    `test_sc5_stress_sweep_50_scenarios_under_100kb`:
    ```python
    def test_sc5_stress_sweep_50_scenarios_under_100kb(
        stress_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        from pydantic import TypeAdapter
        from lib.stress import StressRequest, evaluate
        fx = stress_fixture("rate_shock_size_budget_50_rates")
        request = TypeAdapter(StressRequest).validate_python(fx["request"])
        response = evaluate(request)
        serialized = response.model_dump_json(indent=2)
        size_bytes = len(serialized.encode("utf-8"))
        assert size_bytes < 100 * 1024, f"SC-5 violation: {size_bytes} bytes >= 100KB"
        # SC-5 byte-order check
        idx_summary = serialized.find('"summary"')
        idx_rows = serialized.find('"rows"')
        assert 0 <= idx_summary < idx_rows
    ```

    `test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin`:
    ```python
    def test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin(
        points_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        from pydantic import TypeAdapter
        from lib.points import PointsRequest, evaluate
        fx = points_fixture("points_simple_lt_npv_seven_pct_discount")
        request = TypeAdapter(PointsRequest).validate_python(fx["request"])
        response = evaluate(request)
        assert response.simple_breakeven_months == 123
        assert response.npv_breakeven_months == 160
        assert response.diverge is True
        assert response.decision == "buy_points"
    ```

    Add citation-coverage meta-test (new test, not flipping any xfail) — append to tests/test_stress.py:
    ```python
    def test_phase_08_citation_coverage_meta() -> None:
        """Every Phase 8 requirement (STRS-01..04 + PNTS-01..03) has at least one fixture exercising it."""
        import json
        from pathlib import Path
        FIX_STRESS = Path(__file__).parent / "fixtures" / "stress"
        FIX_POINTS = Path(__file__).parent / "fixtures" / "points"
        all_citations: list[str] = []
        for p in list(FIX_STRESS.glob("*.json")) + list(FIX_POINTS.glob("*.json")):
            data = json.loads(p.read_text())
            citation = data.get("_meta", {}).get("citation", "")
            all_citations.append(citation)
        joined = " | ".join(all_citations)
        for req_id in ["STRS-01", "STRS-02", "STRS-03", "STRS-04",
                       "PNTS-01", "PNTS-02", "PNTS-03",
                       "ROADMAP SC-1", "ROADMAP SC-2", "ROADMAP SC-3",
                       "ROADMAP SC-4", "ROADMAP SC-5"]:
            # ROADMAP SC variants accepted: literal + descriptive substrings
            id_keys = {req_id, req_id.replace("ROADMAP ", "")}
            assert any(any(k in c for k in id_keys) for c in all_citations), \
                f"No fixture cites {req_id}: {joined[:200]}"
    ```
  </action>
  <acceptance_criteria>
    - `grep -c '@pytest.mark.xfail' tests/test_stress.py` returns 0
    - `grep -c '@pytest.mark.xfail' tests/test_points.py` returns 0
    - `pytest tests/test_stress.py tests/test_points.py -v --tb=short` shows ALL tests passing (zero xfailed)
    - Full suite: ≥429 passed, 0 xfailed (was 18 from Phase 8 stubs), 0 failed, 0 errored
    - `pytest tests/test_stress.py::test_phase_08_citation_coverage_meta -v` passes
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-05-01: Engine-emitted fixture values (NOT hand-derived). Per Phase 3 D-04 / Phase 4 D-17 idiom. The fixture script runs lib.stress.evaluate / lib.points.evaluate to capture the Decimal-string values, then commits them. Hand-calc citations live in the _meta.citation field for traceability.
- D-05-02: One fixture per file. Mirrors Phase 4 / Phase 5 conventions; diffs stay readable.
- D-05-03: SC-5 byte-order check uses substring `.find('"summary"')` < `.find('"rows"')` on the indented JSON string. Robust to whitespace; sufficient for the SC-5 contract intent.
- D-05-04: Citation-coverage meta-test treats both raw requirement IDs (STRS-01) AND ROADMAP SC strings (ROADMAP SC-1) as valid citation tokens. A fixture's _meta.citation may contain one or both; the meta-test uses substring presence rather than exact match for resilience.
- D-05-05: SC-4 numerical pins (123 / 160) are HARD pins. If a future Phase 6 discount-rate convention change shifts these by 1 month, that's a breaking change requiring an explicit Plan in Phase 6 to retire/update Fixture 13.
- D-05-06: Fixture 4 (50-rate sweep) generates rates as `[f"0.0{40+i:02d}000" for i in range(50)]` for stable byte counts. Plan must commit the literal list (not the generation expression).
- D-05-07: Fixtures 6-8 (income-shock) require a fully-valid forward-mode AffordabilityRequest in `request.base_request`. Reuse the seed from one of Plan 04-06's existing fixtures (e.g., `tests/fixtures/affordability/forward_conventional_above_dti_cap.json` or analog) — DO NOT hand-construct.
</locked_decisions>

<verify_block>
- 14 fixture files exist (11 stress + 3 points) and load as JSON
- All 18 Wave 0 xfails flipped (count of @pytest.mark.xfail in test_stress.py + test_points.py == 0)
- Citation-coverage meta-test passes (every Phase 8 requirement + SC has fixture coverage)
- ROADMAP SC-1 + SC-2 + SC-3 + SC-4 + SC-5 all verifiable verbatim by tests
- Full suite: ≥429 passed (411 baseline + 18 flipped Phase 8 xfails), 0 xfailed
- mypy + ruff clean
</verify_block>

<deviation_rules>
- Rule 1: If the fixture-emitted JSON for the 50-rate sweep crosses the 100KB ceiling (extremely unlikely given §1.3 estimate: ~8KB), SHRINK the per-row representation by removing optional None fields from StressRow's serialization (e.g., add `model_config exclude_none=True`). Document in SUMMARY.md.
- Rule 2: If income-shock seed AffordabilityRequest from Phase 4 doesn't produce a marginally-failing DTI scenario, hand-tune household income or loan amount to land near the threshold. Document in fixture's _meta.
- Rule 3: If 7%-discount NPV breakeven returns 159 or 161 instead of the pinned 160 (Decimal precision drift), update Plan 08-03 D-03-02 with the precision-context fix BEFORE adjusting the fixture. The 160-month value is the canonical hand-calc per 08-RESEARCH §5.4 — the engine adapts to the math, not the other way around.
- Rule 4: Hygiene-only deviations (ruff format, mypy unused-type:ignore) accepted without amending this plan.
</deviation_rules>

<success_criteria>
- 14 hand-calc fixtures shipped + citation-coverage meta-test
- All 18 Wave 0 xfails flipped; every Phase 8 requirement (STRS-01..04 + PNTS-01..03) closed at the test layer
- ROADMAP SC-1 through SC-5 verifiable verbatim by tests after this plan
- Phase 5 baseline preserved (no regressions to existing tests)
- mypy + ruff clean
</success_criteria>
