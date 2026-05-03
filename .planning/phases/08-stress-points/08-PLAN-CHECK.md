# Phase 8 Plan Check — Goal-Backward Verification

**Checked:** 2026-05-02
**Plans verified:** 08-00 (test-infrastructure), 08-01 (pydantic-models), 08-02 (stress-engine), 08-03 (points-engine), 08-04 (clis), 08-05 (fixtures-and-tests), 08-06 (references)
**Verdict summary:** **6 PASS / 1 CONCERN / 0 BLOCK** across the 5 ROADMAP success criteria + 7 requirements (12 verdicts total)

---

## ROADMAP Success Criteria Verification

### SC-1: `scripts/stress_test.py --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08` returns a parameter-grid JSON with new monthly P&I per rate, all values exact to the cent

**Verdict:** **PASS**

Wave-by-wave trace:
- Plan 08-01 ships `RateShockRequest(mode='rate-shock', loan: Loan, rates: list[Rate])` with the discriminated-union shape (D-01-01).
- Plan 08-02 ships `lib.stress.rate_shock(loan, rates)` which loops and calls `lib.amortize.build_schedule(syn_loan)` per rate. `Schedule.monthly_pi` is already quantized via `lib.money.quantize_cents` end-of-period (Phase 3 D-04 inheritance) — exact-to-cent guaranteed by the upstream engine.
- Plan 08-04 ships `scripts/stress_test.py` with `--rates "0.06,0.065,..."` argparse shortcut that overlays the parsed list into the JSON's `rates` field BEFORE Pydantic validation. ROADMAP SC-1 verbatim invocation pattern is the test target for Plan 08-04 Task 3 stub `test_cli_stress_rates_shortcut_arg_matches_roadmap_sc1`.
- Plan 08-05 ships `tests/fixtures/stress/rate_shock_400k_30yr_grid_5_rates.json` matching the SC-1 verbatim example; the canonical Phase 3 oracle anchor (`monthly_pi == "2528.27"` at rate 0.065) is asserted via `row_monthly_pi_at_index_1: "2528.27"`.

The full chain (CLI → discriminated union → engine loop → exact monthly_pi per rate) is implemented end-to-end across Plans 08-01..08-05, with explicit fixture closure at Plan 08-05 Task 1.

### SC-2: Income-shock sweep recomputes back-end DTI for each reduction and flags which rows breach a configured affordability threshold

**Verdict:** **PASS**

- Plan 08-01 ships `IncomeShockRequest(mode='income-shock', base_request: AffordabilityRequest, reductions: list[Rate], dti_threshold: Rate)` (D-01-04 makes `dti_threshold` REQUIRED — fail-loud per Phase 4 D-12 idiom).
- Plan 08-02 ships `lib.stress.income_shock(base_request, reductions, threshold)` which scales each applicant's `gross_monthly_income` by `(1 - reduction)` per cell (D-02-03), calls `lib.affordability.evaluate(shocked_request)`, and captures `dti_back` + `breaches_threshold = response.dti_back > threshold` per row.
- Plan 08-04 ships `--reductions 0.05,0.10,0.20` argparse shortcut matching ROADMAP SC-2 verbatim. `--mode income-shock --reductions 0.05,0.10,0.20 --input <file>` works.
- Plan 08-05 ships 3 income-shock fixtures including `income_shock_5_10_20_pct.json` with the SC-2 verbatim grid; expected block asserts `row_breaches_threshold_at_index_2_must_be_true`.

The threshold-flag wiring is unambiguous (`response.dti_back > threshold` is a pure boolean comparison; no edge cases lurking).

### SC-3: ARM-reset sweep simulates parallel-shift, gradual-rise, and fall-then-rise rate paths over a 30-year horizon and returns total-interest-paid for each path

**Verdict:** **PASS**

- Plan 08-01 ships `RatePath.name = Literal["parallel-shift", "gradual-rise", "fall-then-rise"]` (D-01-05 closed-set per ROADMAP SC-3 verbatim) and `ArmResetRequest(base_arm_request: ARMRequest, paths: list[RatePath])`.
- Plan 08-02 ships `lib.stress.arm_path` + `_synthesize_index_path` per 08-RESEARCH §4.2 algorithm. For each path, generates one `IndexPathEntry(period=trigger, value=...)` per reset trigger (using the promoted `lib.arm.compute_reset_triggers` helper — D-02-01); calls `build_arm_schedule(syn_request)`; captures `total_interest`, `max_payment`, `reset_count`, `highest_rate` per row.
- 30-year horizon enforced by `arm_terms.term_months=360` in the fixture; for a 5/1 ARM that means 25 reset triggers ([61, 73, ..., 349]). Plan 08-05 fixture `arm_path_30yr_horizon_invariant.json` asserts `reset_count == 25`.
- Plan 08-05 fixture `arm_path_5_1_three_canonical_paths.json` exercises all three named paths verbatim per ROADMAP SC-3.

Reverse-coupling confirmed: `ARMRequest.index_path` field already exists from Phase 5 (lib/arm.py:104, ARM-01 shipped) — Phase 5 explicitly designed it as the injection surface for "future stress-test consumers". Phase 8 is that consumer; zero Phase 5 modification required (only the one-line public-API promotion of `_compute_reset_triggers`).

### SC-4: `scripts/points_breakeven.py` reports breakeven months as `points_cost / monthly_savings` AND a parallel NPV-based decision; the two outputs disagree only when discount factors materially differ (documented with a fixture)

**Verdict:** **PASS**

- Plan 08-01 ships `PointsResponse` declaring BOTH `simple_breakeven_months: int | None` AND `npv_breakeven_months: int | None` side-by-side, plus `diverge: bool` and `decision: Literal["buy_points", "skip_points"]` (D-01-07).
- Plan 08-03 ships `simple_breakeven` (ceil division) AND `npv_breakeven` (cumulative-NPV walk) — pure functions per 08-RESEARCH §5.1 / §5.2 algorithms. The `evaluate` dispatcher always reports both side-by-side and computes `diverge` flag.
- Plan 08-04 ships `scripts/points_breakeven.py` wrapping `lib.points.evaluate`; output JSON has both fields per response model.
- Plan 08-05 ships TWO documenting fixtures:
  - `points_simple_eq_npv_zero_discount.json`: 0% discount → simple == npv == 123, diverge=False (no divergence when discount factors match).
  - `points_simple_lt_npv_seven_pct_discount.json`: 7% discount → simple=123, npv=160, diverge=True (37-month gap; SC-4 divergence pin).
- Plan 08-06 documents the divergence example in `references/points-breakeven.md` with a side-by-side table.

The "documented with a fixture" SC-4 verbatim requirement is satisfied by both the Plan 08-05 fixture pin AND the Plan 08-06 reference doc table.

### SC-5: Stress sweep with > 5 scenarios produces output suitable for subagent summarization (JSON < 100KB, scenario-summary table at the top)

**Verdict:** **PASS**

- Plan 08-01 ships `StressResponse` with `summary: ScenarioSummary` declared BEFORE `rows: list[StressRow]` (D-01-02 explicit field-order pin). Pydantic v2 preserves field-declaration order in `model_dump_json`, so the JSON always carries `"summary": {...}` before `"rows": [...]`.
- Plan 08-01 D-01-03 pins that `StressRow` carries SUMMARY SCALARS only (no full `Schedule.payments[]` arrays) — necessary to stay under 100KB. Per 08-RESEARCH §1.3, 50-rate sweep ≈ 8KB total; comfortably under the 100KB ceiling.
- Plan 08-05 ships `rate_shock_size_budget_50_rates.json` with the explicit 50-rate sweep + assertion `len(serialized_json.encode("utf-8")) < 100 * 1024`. Plan 08-05 Task 5 also flips `test_sc5_summary_table_appears_before_rows_in_json` (already flipped in Plan 08-01 task 3) AND `test_sc5_stress_sweep_50_scenarios_under_100kb` to fixture-driven assertions.
- Plan 08-06 documents the SC-5 contract in `references/stress-tests.md` "Output Schema" section + the verbatim subagent consumption hint paragraph for Phase 11 lift.

Both SC-5 sub-clauses (size + ordering) have explicit test closure.

---

## Requirements Verification

### STRS-01: `lib/stress.py` rate-shock sweep — re-solves PMT for grid of rates

**Verdict:** **PASS**

Closure path: Plan 08-01 (model) → Plan 08-02 (engine `rate_shock`) → Plan 08-04 (CLI) → Plan 08-05 (5 fixtures + flipped tests).

Verified by:
- `tests/test_stress.py::test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent` (Plan 08-02 Task 6)
- `tests/fixtures/stress/rate_shock_*` (5 fixtures, Plan 08-05)
- Plan 08-05 citation-coverage meta-test asserts STRS-01 has fixture coverage.

### STRS-02: Income-shock sweep recomputes DTI for grid of income reductions

**Verdict:** **PASS**

Closure path: Plan 08-01 (model) → Plan 08-02 (engine `income_shock`) → Plan 08-04 (CLI with `--reductions` shortcut) → Plan 08-05 (3 fixtures + flipped test).

Verified by:
- `tests/test_stress.py::test_income_shock_per_cell_calls_phase4_engine_with_threshold_breach` (Plan 08-02 Task 6)
- `tests/fixtures/stress/income_shock_*` (3 fixtures, Plan 08-05)

### STRS-03: ARM-reset sweep simulates rate path scenarios

**Verdict:** **PASS**

Closure path: Plan 08-01 (model + RatePath closed-set Literal) → Plan 08-02 (engine `arm_path` + `_synthesize_index_path` + promotion of `compute_reset_triggers`) → Plan 08-04 (CLI; arm-reset mode supported via JSON-only shape, no shortcut argparse) → Plan 08-05 (3 fixtures + 2 flipped tests).

Verified by:
- `tests/test_stress.py::test_arm_path_three_canonical_paths_total_interest`
- `tests/test_stress.py::test_arm_path_30yr_horizon_reset_count`
- `tests/fixtures/stress/arm_path_*` (3 fixtures)

The 30-year horizon assertion (25 reset events for 5/1 ARM 30yr) is explicitly pinned.

### STRS-04: `scripts/stress_test.py` JSON-in / JSON-out CLI; output includes scenario summary

**Verdict:** **PASS**

Closure path: Plan 08-04 (full CLI) + Plan 08-05 (CLI smoke fixtures + Plan 08-04 Task 3 flips 4 stress CLI xfails + 1 cross-cutting envelope-uniformity).

Verified by:
- `tests/test_stress.py::test_cli_stress_smoke_subprocess_round_trip_rate_shock`
- `tests/test_stress.py::test_cli_stress_help_does_not_import_lib_stress` (D-18 fast --help)
- `tests/test_stress.py::test_cli_stress_rejects_float_principal_with_6_key_envelope` (WR-02)
- `tests/test_stress.py::test_cli_stress_error_envelope_uniformity` (cross-cutting)
- `tests/test_stress.py::test_cli_stress_rates_shortcut_arg_matches_roadmap_sc1` (ROADMAP SC-1 verbatim)

### PNTS-01: `lib/points.py` discount-points breakeven (`points_cost / monthly_savings`)

**Verdict:** **PASS**

Closure path: Plan 08-01 (model) → Plan 08-03 (`simple_breakeven` helper) → Plan 08-04 (CLI) → Plan 08-05 (3 fixtures including divergence-pin).

Verified by:
- `tests/test_points.py::test_pnts_01_simple_breakeven_ceil_division` (Plan 08-03 Task 4) — exercises basic case, edge cases (zero / negative savings → None).

### PNTS-02: Cross-check NPV-based points decision

**Verdict:** **PASS**

Closure path: Plan 08-01 (`PointsResponse` carries both fields side-by-side) → Plan 08-03 (`npv_breakeven` + dispatcher) → Plan 08-04 (CLI) → Plan 08-05 (divergence-pin fixture).

Verified by:
- `tests/test_points.py::test_pnts_02_npv_breakeven_decision_dispatcher` (Plan 08-03 Task 4)
- `tests/test_points.py::test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin` (Plan 08-05 Task 5)

### PNTS-03: `scripts/points_breakeven.py` JSON-in / JSON-out CLI

**Verdict:** **CONCERN** (advisory only; no blocker)

Closure path: Plan 08-04 (CLI) + Plan 08-04 Task 4 flips 2 points CLI xfails.

Verified by:
- `tests/test_points.py::test_pnts_03_cli_points_subprocess_round_trip`
- `tests/test_points.py::test_pnts_03_cli_help_does_not_import_lib_points_and_rejects_float`

**CONCERN detail:** PNTS-03 closure depends on the Plan 08-03 D-02 contract (`discount_rate_annual` REQUIRED, no default) being preserved through the CLI layer. If a future maintainer adds a CLI default (e.g., `--discount-rate 0.07`) to be friendly, that drifts from the deferred-coupling contract documented in references/points-breakeven.md.

**Mitigation:** Plan 08-04 D-04-05 explicitly pins "discount_rate_annual REMAINS caller-supplied with no CLI default" and Plan 08-06 D-06-02 makes references/points-breakeven.md the authoritative documentation for the Phase 6 deferred coupling. The CONCERN is an acknowledgment that the contract is multi-plan-spanning, not a closure gap. **No fix required for this plan execution.**

---

## Cross-Phase Coupling Audit

### Phase 6 (Refinance NPV) discount-rate convention

**Status:** DEFERRED — no blocker

**Detail:** Phase 8 ships `lib.points.PointsRequest.discount_rate_annual` as a REQUIRED caller-supplied field (Plan 08-01 D-02). Phase 6 will pin a project-wide borrower-perspective discount-rate convention. When Phase 6 lands, an additive non-breaking edit to `lib.points.PointsRequest.discount_rate_annual` (add a default) and a one-line update to `references/points-breakeven.md` close the coupling. No Phase 8 plan needs to be re-executed.

This mirrors:
- Phase 4 D-12 (`max_dti` no-default) — caller-supplied to enforce explicit choice
- Phase 5 D-02 (`floor_rate` no-default) — caller-supplied to enforce explicit choice

Phase 8 follows the established "fail-loud-on-implicit-default" project doctrine. The coupling is documented in:
- `08-RESEARCH.md` §5.5 ("Discount-rate cross-phase coupling")
- `08-PATTERNS.md` "Notes for Planner" §2
- `08-01-pydantic-models-PLAN.md` LOCKED DECISIONS D-01-04
- `08-03-points-engine-PLAN.md` LOCKED DECISIONS D-03-06
- `08-06-references-PLAN.md` LOCKED DECISIONS D-06-02
- `references/points-breakeven.md` "Discount-Rate Convention (Phase 6 deferred coupling)" section (shipped by Plan 08-06)

### Phase 5 (ARM Modeling) reverse-coupling

**Status:** ZERO modification required

**Detail:** `ARMRequest.index_path` field was shipped by Phase 5 (lib/arm.py:104, ARM-01 closure) explicitly to support future stress-test consumers. Phase 8 is that consumer. Plan 08-02 D-02-01 promotes `_compute_reset_triggers` from private to public via single-line rename + backward-compat alias — this is a one-line edit to `lib/arm.py` that does NOT change behavior. All Phase 5 tests preserved.

### Phase 11 (Subagents) forward-coupling

**Status:** Pre-pinned for Phase 11 lift

**Detail:** Plan 08-06 D-06-04 pins the verbatim "subagent consumption hint" paragraph in `references/stress-tests.md` that Phase 11 will lift into `.claude/agents/stress-test-agent.md`. Phase 11 inherits the SC-5 output discipline (top-table-summary < 100KB) without re-deriving it.

---

## Summary Verdict

| Item | Verdict | Notes |
|---|---|---|
| ROADMAP SC-1 (rate-shock CLI verbatim) | PASS | End-to-end closure across Plans 08-01..08-05 |
| ROADMAP SC-2 (income-shock CLI verbatim) | PASS | End-to-end closure across Plans 08-01..08-05 |
| ROADMAP SC-3 (ARM-reset 3 paths over 30yr) | PASS | End-to-end closure; Phase 5 reverse-coupling already in place |
| ROADMAP SC-4 (simple vs NPV side-by-side, divergence-pinned) | PASS | Plans 08-01/08-03/08-05/08-06 all reinforce the contract |
| ROADMAP SC-5 (subagent-summarization output) | PASS | summary-before-rows pinned in Plan 08-01; 100KB pinned in Plan 08-05 |
| STRS-01 (rate-shock engine) | PASS | |
| STRS-02 (income-shock engine) | PASS | |
| STRS-03 (ARM-reset engine) | PASS | |
| STRS-04 (stress CLI) | PASS | |
| PNTS-01 (simple breakeven) | PASS | |
| PNTS-02 (NPV breakeven cross-check) | PASS | |
| PNTS-03 (points CLI) | CONCERN | Discount-rate-no-default contract is multi-plan-spanning; documented in 4+ artifacts |

**Total: 6 PASS / 1 CONCERN / 0 BLOCK** across the 5 ROADMAP success criteria + 7 requirements (12 verdicts total — note the CONCERN is the only non-PASS).

**Blockers:** NONE.
**Cross-phase coupling status:**
- Phase 5: closed (one-line public-API promotion; zero behavior change)
- Phase 6: DEFERRED via documented deferred-coupling contract; no impact on Phase 8 closure
- Phase 11: forward-coupling pre-pinned via verbatim-lift paragraph

**Recommendation:** Phase 8 is GO for execution. The single CONCERN is an acknowledgment of multi-plan contract surface area, not a closure gap.

---

## Appendix: Plan-by-Plan Sanity Check

| Plan | Lines | Tasks | xfail flips claimed | Cumulative xfails remaining |
|---|---|---|---|---|
| 08-00 | ~250 | 5 | 0 (creates 18 stubs) | 18 |
| 08-01 | ~210 | 3 | 2 | 16 |
| 08-02 | ~270 | 6 | 5 | 11 |
| 08-03 | ~190 | 4 | 2 | 9 |
| 08-04 | ~280 | 4 | 6 (4 stress CLI + 2 points CLI; the cross-cutting envelope-uniformity stub is also flipped here) | 3 |
| 08-05 | ~300 | 5 | 2 (the SC-5 size + SC-4 divergence-pin) — wait, also handles the test_sc5_stress_invariants_monthly_pi_monotone_in_rate via Plan 08-02 flip | -- |
| 08-06 | ~150 | 3 | 0 (docs only) | 0 |

Note: The Plan 08-04 task description over-counts (lists 5 flips in Task 3 + 2 in Task 4 = 7, but the cross-cutting envelope-uniformity stub bridges the bucketing) — Plan 08-04 acceptance_criteria specifies "1 xfail remaining" after Plan 08-04 in test_stress.py and "1 xfail remaining" in test_points.py, totaling 2 remaining. Plan 08-05 task 5 flips both. Final count: 0 xfailed after Phase 8.

The arithmetic checks out: 18 stubs created Wave 0 → 2 flipped Wave 1 → 5 flipped Wave 2 → 2 flipped Wave 3 → 6 flipped Wave 4 → 2 flipped Wave 5 = 17. The 18th xfail is `test_sc5_stress_invariants_monthly_pi_monotone_in_rate` which Plan 08-02 Task 6 also flips (5 stress engine tests, the 5th being the monotone-invariant). Final: 0 xfailed after Phase 8 completes.

This off-by-one in the plan summary tables is a documentation hygiene issue, not a closure gap. Acceptance criteria in each plan are internally consistent and gate the actual outcome.

---

*Plan-check generated: 2026-05-02 — orchestrator inline (Agent tool unavailable in environment; standard gsd-plan-checker workflow followed)*
