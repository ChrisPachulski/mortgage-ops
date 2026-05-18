---
phase: 14-property-analysis-pipeline
verified: 2026-05-17T00:00:00Z
status: passed
score: 7/7 success criteria verified + 4/4 requirements closed
overrides_applied: 0
re_verification:
  previous_status: null
  notes: "Initial verification; no prior VERIFICATION.md."
---

# Phase 14: Property Analysis Pipeline — Verification Report

**Phase Goal:** Compose v1.0 calc primitives (amortize × affordability × ARM × refi × stress × points × IRS Pub 936) into a single `(listing, household, profile) → AnalysisReport` pipeline. Multi-program × down-payment fan-out + verdict synthesis.

**Verified:** 2026-05-17
**Status:** PASS
**Re-verification:** No — initial verification

## Test Suite Result (Source of Truth)

```
uv run pytest tests/test_household.py tests/test_profile.py \
              tests/test_property_analysis.py tests/test_property_verdict.py
======================== 84 passed, 3 warnings in 5.66s ========================
```

Breakdown (collected):
- `tests/test_household.py` — 10 tests pass
- `tests/test_profile.py` — 12 tests pass
- `tests/test_property_analysis.py` — 49 tests pass
- `tests/test_property_verdict.py` — 13 tests pass

The 3 warnings are stale-reference data warnings (`fha-mip-rates`, `irs-pub936`, `va-funding-fees` all > 12 months from effective date) — informational, not failures, and out of scope for Phase 14 (annual YAML refresh per CLAUDE.md "Reference Data" discipline, due in Phase 16).

Pre-existing failures listed in the verification context (7 fha_mip duplicate-file failures from macOS Finder duplicates + 1 uncommitted edit to `lib/rules/fha_mip.py`) are correctly out of scope and confirmed NOT in the Phase 14 test surface.

## Goal Achievement — Observable Truths (Success Criteria)

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | `lib/property_analysis.py:analyze(listing, household, profile) → AnalysisReport` runs 4 program-eligibility checks (Conv30, Conv15, FHA, VA-if-eligible) + jumbo branch when price > conforming limit | VERIFIED | `analyze()` defined at `lib/property_analysis.py:1433-1534`. Programs gated by `_determine_programs()` at L549-578 (Conv30/Conv15/FHA30 always, VA30 if `profile.va_eligible`, Jumbo30 when `classify_loan_type(...) == "jumbo"`). Tests: `test_matrix_fanout_conforming` (L347), `test_va_eligibility_gates_program` (L358), `test_jumbo_trigger_at_county_limit` (L374), `test_analyze_with_jumbo_listing` (L1008), `test_analyze_with_va_eligible_profile` (L1034) — all pass. |
| 2 | Down-payment sweep produces `DownPaymentMatrix` with 6 cells per eligible program (3/5/10/15/20/25%) with PMI/MIP/funding-fee per program + LTV | VERIFIED | `DOWN_PAYMENT_PCTS` Final[list[Decimal]] at L128-135 with all 6 string-constructed Decimals. `_build_matrix()` at L827-852 iterates programs × DPs. Per-cell composition `_build_program_result()` at L608-824 handles PMI (Conv LTV>0.80, L651-657), FHA MIP (L658-672), VA funding fee (L673-687). Tests: `test_matrix_cell_count` (18 cells base), `test_dp_sweep_uses_decimal_strings` (Pitfall 2 verified), `test_mi_included_in_piti` (PMI in PITI), `test_fha_cell_ufmip_financed_into_principal` — all pass. |
| 3 | Auto-applied stress tests: rate +2%, income −30%, ARM reset at peak cap (Conv30 only) | VERIFIED | `_build_stress_block()` at L1099-1195. Rate-shock at L1130-1145 (`+_RATE_SHOCK_BPS=0.02`), income-shock at L1147-1163 (`-_INCOME_SHOCK_REDUCTION=0.30`), ARM reset gated `if cell.program == "Conv30"` at L1168-1193 using `_CONV_5_1_ARM_TERMS` at L161-170 (lifetime cap 500bps). Tests: `test_stress_at_preferred_dp_only` (L603), `test_arm_reset_conv30_only` (L635), `test_stress_income_shock_dti_recompute` (L683), `test_stress_rate_shock_piti_rises` (L708), `test_dti_ceiling_per_program` (L769) — all pass. |
| 4 | Points breakeven at 1pt/2pt + refi scan at (FRED − 1%) and (FRED × 0.85) | VERIFIED | `_build_points_block()` at L1288-1377 iterates `(1, 2)` points at 25bps/point (Assumption A3). `_build_refi_block()` at L1198-1285 emits exactly 2 RefiRow per program: `minus_100bps` (target = current − 0.01) at L1234-1257, `fred_times_0_85` (target = current × 0.85) at L1259-1283. Tests: `test_refi_two_scenarios_per_program` (L652 — pins labels and target-rate formulas), `test_points_breakeven_per_program` (L824), `test_points_fha_va_warning_note` (L852 — FHA/VA emit `WARNING-NO-POINTS-FOR-FHA-VA`) — all pass. |
| 5 | IRS Pub 936: first-year interest + $750k cap flag | VERIFIED | `_build_tax_block()` at L1380-1425 (B-6 4-arg signature). First-year interest from `schedule.payments[:12]` summed with `start=Decimal("0")` (Pitfall avoided at L1414); `qualified_loan_limit()` from `lib.rules.irs_pub936` called with `filing_status=profile.filing_status`; over-cap flag `cell.loan_amount > cap` at L1418. Tests: `test_tax_block_pub936` (L878), `test_tax_block_mfs_filing_status_halves_cap` (L923 — MFS halves cap to $375k), `test_tax_block_over_cap_flag` (L938) — all pass. |
| 6 | Verdict cascade with predicate + computed value (DTI-breach-all → NO_GO; FHA-only-with-MIP-burden → WATCH; non-FHA-eligible → GO) | VERIFIED | `lib/property_verdict.py:synthesize()` at L111-258 implements 5-level cascade in first-match-wins order. Level 1 (no eligible at any DP, L154-167), Level 2 (no eligible at preferred DP, L172-183), Level 3 (income-shock WATCH, L192-214), Level 4 (FHA-MIP-burden WATCH gated `if not non_fha_eligible`, L223-240), Level 5 (GO default, L247-258). Every reason carries `predicate_code` + `computed_value` per D-14-VERDICT-04. Tests: `test_no_go_no_eligible`, `test_no_go_at_preferred_dp`, `test_watch_income_shock`, `test_watch_fha_mip_burden`, `test_go_non_fha_eligible`, `test_go_wins_over_mip_burden_when_non_fha_eligible`, `test_watch_income_shock_overrides_go`, `test_reason_format_compliance`, `test_verdict_code_citation_coverage` — all pass. |
| 7 | Golden-value fixtures: 3 hand-calculated AnalysisReport cases (SFH conforming, condo with HOA, SFH jumbo) pin every matrix cell | VERIFIED | 3 fixtures at `tests/fixtures/property_analysis/`: `sfh_conforming_king_county.json`, `condo_with_hoa_seattle.json`, `sfh_jumbo_bay_area.json`. Each contains `listing` (with `source_url`, `zpid`, `fetched_at` Phase-13 audit fields), `household`, `profile`, `fred_rates`, `expected_response.matrix.preferred_dp_cells`, `expected_response.verdict`, `expected_response.tax`, hand-calc anchors in `source` + `notes`. Each fixture's `_meta.requirements` lists `[ANLZ-01, ANLZ-02, ANLZ-03, VERD-01]`. Tests: `test_sfh_conforming_king_county_golden` (L1251), `test_condo_with_hoa_seattle_golden` (L1292), `test_sfh_jumbo_bay_area_golden` (L1329), plus `test_phase_14_requirement_coverage_meta` (verdict file L555) all pass. |

**Score: 7/7 success criteria verified.**

## Requirements Coverage

| Requirement | Description | Source Plan(s) | Status | Evidence |
|-------------|-------------|----------------|--------|----------|
| ANLZ-01 | Multi-program fan-out + jumbo branch + ProgramResult shape | 14-01, 14-02, 14-05, 14-06 | SATISFIED | `_determine_programs()` + `_build_program_result()` + `ProgramResult` Pydantic model (`lib/property_analysis.py:259-300`). Closure proven by `test_matrix_fanout_conforming`, `test_va_eligibility_gates_program`, `test_jumbo_trigger_at_county_limit`, `test_ineligible_rows_populate_numerics`, `test_blocker_reason_verbatim`, 3 golden fixtures, `test_phase_14_requirement_coverage_meta`. |
| ANLZ-02 | Down-payment sweep at 6 DPs → DownPaymentMatrix | 14-01, 14-02, 14-05, 14-06 | SATISFIED | `DOWN_PAYMENT_PCTS` + `DownPaymentMatrix` model (L302-314). Pinned by `test_matrix_cell_count` (18 cells base), `test_dp_sweep_uses_decimal_strings`, `test_mi_included_in_piti`, golden fixture cell counts (18, 18, 24). |
| ANLZ-03 | Stress + points + refi + IRS Pub 936 blocks at preferred DP | 14-03, 14-05, 14-06 | SATISFIED | `_build_stress_block` + `_build_refi_block` + `_build_points_block` + `_build_tax_block` (L1099-1425). 12 wave-2 ANLZ-03 unit tests + golden fixtures all pass. |
| VERD-01 | GO/WATCH/NO_GO verdict with predicate-cited reasons | 14-04, 14-05, 14-06 | SATISFIED | `lib/property_verdict.py:synthesize()` 5-level cascade + 5 VERDICT_* Final[str] constants. 13 unit tests in `test_property_verdict.py` exercise all branches + precedence rules + format compliance + fixture citation coverage. |

**No orphaned requirements.** REQUIREMENTS.md checkboxes for ANLZ-01..03 + VERD-01 are all `[x]`. The traceability table at REQUIREMENTS.md:74 still labels `ANLZ-01..03 | Phase 14 | Pending` — this is documentation lag (the checkbox state at L30-32 is the binding signal and shows `[x]`). Not blocking; flagged as a documentation-hygiene follow-up but does NOT affect goal achievement.

## Decision-Lock Honor Check

### D-14-MATRIX (Matrix shape & sparsity)

| Lock | Honored | Evidence |
|------|---------|----------|
| D-14-MATRIX-01 (explicit ineligible rows) | YES | `_build_matrix` (L827-852) iterates ALL programs × ALL DPs; ineligible cells still emit ProgramResult (L808-824). `test_ineligible_rows_populate_numerics` (L413) pins this. |
| D-14-MATRIX-02 (numerics populated on ineligible rows) | YES | `_build_program_result` always populates `piti`, `dti_back`, `ltv`, `cash_to_close`, `monthly_mi`, etc. regardless of `eligible` outcome. NotImplementedError from FHA/VA over-ceiling is caught (L784-797) and translated to stable blocker codes. `test_ineligible_rows_populate_numerics` (L413) + jumbo-fixture Conv30 ineligible row pin this. |
| D-14-MATRIX-03 (jumbo 5th row when triggered) | YES | `_determine_programs` appends `"Jumbo30"` when `classify_loan_type(...) == "jumbo"` (L574-575). `test_jumbo_trigger_at_county_limit` (L374) + `test_analyze_with_jumbo_listing` (L1008 — 4 programs × 6 DPs = 24 cells when jumbo fires) + `sfh_jumbo_bay_area.json` fixture (programs_present=`["Conv30", "Conv15", "FHA30", "Jumbo30"]`) all pin this. |

### D-14-VERDICT (Verdict tie-breaks)

| Lock | Honored | Evidence |
|------|---------|----------|
| D-14-VERDICT-01 (MIP-burden $300 threshold) | YES | `_MIP_BURDEN_THRESHOLD: Final[Decimal] = Decimal("300.00")` at `lib/property_verdict.py:97`. Cascade Level 4 (L223-240) checks `fha_cells[0].monthly_mi > _MIP_BURDEN_THRESHOLD`. `test_watch_fha_mip_burden` (L322) + `test_mip_burden_threshold_pinned_at_300` pin this. |
| D-14-VERDICT-02 (income-shock WATCH) | YES | Cascade Level 3 (`lib/property_verdict.py:192-214`) iterates `stress.rows` for `stress_kind == "income_shock" AND breaches_dti_ceiling`. Per-program DTI ceilings sourced from `_DTI_CEILING_BY_PROGRAM` (Conv 0.50, FHA 0.57, VA 0.41, Jumbo 0.43). `test_watch_income_shock` + `test_watch_income_shock_overrides_go` + `test_dti_ceiling_per_program` pin this. |
| D-14-VERDICT-03 (GO wins over MIP-burden) | YES | Cascade Level 4 guarded by `if not non_fha_eligible:` (`lib/property_verdict.py:223`). When ANY non-FHA program is eligible at preferred DP, the FHA-MIP-burden branch is skipped and verdict falls to Level 5 GO. `test_go_wins_over_mip_burden_when_non_fha_eligible` (L356 in test_property_verdict.py) directly pins this — explicit scenario with Conv30 + FHA30 (monthly_mi=$325) both eligible → asserts level=GO, not WATCH. |
| D-14-VERDICT-04 (predicate + computed citation) | YES | Every `VerdictReason` requires `predicate_code` + `computed_value` (strict Pydantic model at L432-446 of property_analysis.py). `test_reason_format_compliance` (L391) iterates all cascade branches asserting both fields non-empty. `test_verdict_code_citation_coverage` (L432) ensures every VERDICT_* constant is emitted by at least one fixture or in-test scenario. |

### D-14-STRESS (Stress fan-out scope)

| Lock | Honored | Evidence |
|------|---------|----------|
| D-14-STRESS-01 (preferred-DP only) | YES | `_build_stress_block` calls `_eligible_cells_at_preferred_dp(matrix, preferred)` at L1121-1122; only those cells produce stress rows. `test_stress_at_preferred_dp_only` (L603) directly pins this — asserts every row's program is in the eligible-at-preferred set. |
| D-14-STRESS-02 (preferred_dp on Household) | YES | `Household.preferred_down_payment_pct: Rate = Field(default=Decimal("0.20"), ...)` at `lib/household.py:66-75`. `test_preferred_dp_default_decimal_0_20` (L124 of test_household.py) pins the default. |
| D-14-STRESS-03 (ARM reset Conv30 only) | YES | `_build_stress_block` gates the ARM-reset branch with `if cell.program == "Conv30":` at L1168 of property_analysis.py. Uses `_CONV_5_1_ARM_TERMS` (L161-170) with 5/1 ARM disclosures. `test_arm_reset_conv30_only` (L635) pins: exactly one arm_reset row per eligible Conv30 cell, zero rows for any other program. |

### D-14-REFI (Refi baseline & today's rate sourcing)

| Lock | Honored | Evidence |
|------|---------|----------|
| D-14-REFI-01 (matrix-cell baseline) | YES | `_build_refi_block` uses `cell.loan_amount` (current matrix-cell financed principal) as `old_loan_balance` (L1238); existing-mortgage-rate is NOT read from Household (the household model carries no such field — deliberate scope choice). |
| D-14-REFI-02 (FRED sourcing) | YES | `_todays_rate_per_program` (L510-546) routes Conv30/FHA30/VA30/Jumbo30 → MORTGAGE30US, Conv15 → MORTGAGE15US, Conv30-ARM-5-1 → MORTGAGE30US − 25bps. `analyze()` populates `todays_rates` dict at L1491-1498. `with_cache_lock` (Pitfall 9) wraps the read. `test_fred_lock_serialization` + `test_fred_cold_cache_raises_valueerror_with_guidance` pin behavior. |
| D-14-REFI-03 (2-scenario scan: −1.00 AND ×0.85) | YES | `_build_refi_block` (L1198-1285) emits exactly 2 RefiRow per program: `minus_100bps` (target = current − 0.01) and `fred_times_0_85` (target = current × 0.85). `test_refi_two_scenarios_per_program` (L652) directly pins both formulas and exactly-2-rows-per-program. |

### D-14-MODELS (Models & file landings)

| Lock | Honored | Evidence |
|------|---------|----------|
| D-14-MODELS-01 (lib/household.py) | YES | `lib/household.py` (75 lines) defines `Household` Pydantic v2 model with `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`. All required fields present. |
| D-14-MODELS-02 (Profile/Household split) | YES | `lib/profile.py` (61 lines) carries `va_eligible`, `first_time_buyer`, `military_status`, `filing_status`, `marginal_tax_rate`. Household carries financial-state-only fields. Clean separation enforced by `extra="forbid"`. |
| D-14-MODELS-03 (lib/property_verdict.py) | YES | `lib/property_verdict.py` (258 lines) ships `synthesize(matrix, stress, household, profile) → Verdict` per cascade. Plan 14-04 closure. |
| D-14-MODELS-04 (lib/property_analysis.py:analyze()) | YES | `lib/property_analysis.py:analyze()` (L1433-1534) is the top-level entrypoint returning `AnalysisReport` (L464-489). Output model is the Phase-15 contract surface. |

## Golden-Fixture Audit Trail

| Fixture | Phase-13 fields | Hand-calc notes | Programs present | Verdict pinned |
|---------|-----------------|------------------|------------------|----------------|
| `sfh_conforming_king_county.json` | source_url, zpid, fetched_at all present | Decimal-anchored monthly_pi computations cited from `lib.amortize.build_schedule`; UFMIP financing trace; PITI Pitfall-6 quantize-once | Conv30, Conv15, FHA30 | GO, headline_reason="2 non-FHA program(s) eligible at preferred DP 0.200000", reasons[0].predicate_code=GO-ALL-GREEN, computed_value="2" |
| `condo_with_hoa_seattle.json` | source_url, zpid, fetched_at all present | HOA threading into PITI ($450 HOA); PMI rate (95% LTV); cascade Level 3 trace with stressed DTI 0.658032 > 0.50 ceiling | Conv30, Conv15, FHA30 (at 5% preferred DP) | WATCH, predicate_code=STRESS-INCOME-SHOCK, computed_value=0.658032, program=Conv30 |
| `sfh_jumbo_bay_area.json` | source_url, zpid, fetched_at all present | Santa Clara CA $1.85M → $1.48M loan exceeds $1.249M Santa Clara high-cost conforming limit → Jumbo30 row appears, Conv/FHA blocked; cascade Level 3 stressed DTI 0.632038 > 0.43 jumbo ceiling | Conv30 (ineligible, FHFA-LIMIT-CONFORMING-06-085), Conv15 (ineligible), FHA30 (ineligible, HUD-LIMIT-CEILING-EXCEEDED), Jumbo30 (eligible at 20% DP) — 4 programs × 6 DPs = 24 cells | WATCH, predicate_code=STRESS-INCOME-SHOCK, computed_value=0.632038, program=Jumbo30 |

All 3 fixtures include `_meta.requirements: [ANLZ-01, ANLZ-02, ANLZ-03, VERD-01]` and `_meta.citation` documenting full closure path. `test_phase_14_requirement_coverage_meta` (test_property_verdict.py:555) verifies fixture metadata coverage.

## AnalysisReport JSON Size Invariant

`test_report_size_budget` (test_property_analysis.py:990) asserts `model_dump_json(indent=2)` for the canonical SFH-conforming scenario stays under 100 KB. **Passes** in the suite run. Honors Pitfall 10 (no per-cell list[Payment] schedule attached; summary scalars only — confirmed by reading ProgramResult model at L259-300, which contains no schedule field).

## Anti-Pattern Scan

| File | Pattern | Severity | Verdict |
|------|---------|----------|---------|
| `lib/property_analysis.py` | `return None`, empty handlers, stub returns | None found | Clean |
| `lib/property_verdict.py` | TODOs, FIXME, hardcoded empty | None found | Clean (one `del profile` at L144 with explicit forward-compat rationale documented in docstring) |
| `lib/household.py`, `lib/profile.py` | Float on Money/Rate, missing strict/frozen | None found | All `strict=True, frozen=True, extra="forbid"` |
| `tests/fixtures/property_analysis/*.json` | Empty stub fixtures | None found | All 3 contain full listing+household+profile+expected_response payloads with hand-calc traces |

No blocker, warning, or info anti-patterns surfaced.

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full Phase-14 test suite | `uv run pytest tests/test_household.py tests/test_profile.py tests/test_property_analysis.py tests/test_property_verdict.py` | 84 passed, 3 warnings, 5.66s | PASS |
| Module imports cleanly | `python -c "from lib.property_analysis import analyze, AnalysisReport; from lib.property_verdict import synthesize; from lib.household import Household; from lib.profile import Profile"` (implicit via test collection — `84 tests collected in 0.12s`) | PASS | PASS |
| End-to-end `analyze()` produces AnalysisReport | `test_analyze_end_to_end` (L111) | PASS — report.matrix.cells==18, verdict in {GO,WATCH,NO_GO}, snapshot_hash is 64-char hex, fetched_at UTC-aware | PASS |
| JSON size under 100KB | `test_report_size_budget` (L990) | PASS — within the suite run | PASS |

## Deferred Items

None. All 7 success criteria + all 4 requirements close in Phase 14. Phase 15 (property mode + report formatter), Phase 16 (reference data refresh), Phase 17 (Zillow HTML fixtures + citation-coverage meta-test), and Phase 18 (long-form references) are downstream and explicitly out of scope per CONTEXT.

## Human Verification Required

None. All success criteria are programmatically verifiable via the existing pytest suite, fixture pins, and code inspection. There are no UI/UX/external-service concerns at the Phase 14 layer — Phase 15's report formatter will require human visual verification when it lands.

## Gaps Summary

No gaps. The phase deliverables:

1. `lib/property_analysis.py` (1534 lines) ships `analyze()` + 11 Pydantic output models + per-cell composition engine + 4 auxiliary block builders.
2. `lib/property_verdict.py` (258 lines) ships the 5-level GO/WATCH/NO_GO cascade with 5 VERDICT_* citation constants.
3. `lib/household.py` (75 lines) ships the analysis-time Household snapshot with `preferred_down_payment_pct` default Decimal("0.20").
4. `lib/profile.py` (61 lines) ships Profile carrying eligibility booleans + filing-status enum.
5. 3 golden fixtures with hand-calc notes + Phase-13 listing audit fields.
6. 84 passing tests across 4 test files covering every success criterion + every D-14 lock + every cascade branch.

The stale `Pending` entry at REQUIREMENTS.md:74 (the traceability summary table) is a documentation-hygiene issue, not a functional gap — the checkbox state at L30-32 shows `[x]` for ANLZ-01..03 and VERD-01 line 36 is `[x]` already. Updating the table to `Complete` is suggested as a docs-only follow-up but does not block phase closure.

---

## VERIFICATION VERDICT: PASS

_Verified: 2026-05-17_
_Verifier: Claude (gsd-verifier)_
