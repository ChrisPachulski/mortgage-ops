---
phase: 14
slug: property-analysis-pipeline
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-17
audited: 2026-05-17
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `14-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (already in dev deps; `tests/conftest.py` ships `affordability_fixture`, `amortize_fixture`, `arm_fixture` loaders) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| **Quick run command** | `pytest tests/test_property_analysis.py tests/test_property_verdict.py tests/test_household.py tests/test_profile.py -x` |
| **Full suite command** | `pytest -x` |
| **Estimated runtime** | ~5s quick, ~30s full |

---

## Sampling Rate

- **After every task commit:** Run quick command above (target < 5s)
- **After every plan wave:** Run `pytest -x` (full suite, target < 30s)
- **Before `/gsd:verify-work`:** Full suite must be green; 3 golden-fixture tests pin every preferred-DP cell of every block by exact Decimal equality (D-18 inherited)
- **Max feedback latency:** 30s

---

## Per-Task Verification Map

> Populated by gsd-planner from PLAN.md task IDs. Each row binds a planned task to the requirement and the exact pytest invocation that proves it.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-02-02 | 02 | 2 | ANLZ-01 | — | Multi-program fan-out produces ProgramResult per (program, DP); jumbo triggers when price > conforming limit | unit + golden | `uv run pytest tests/test_property_analysis.py::test_matrix_fanout_conforming -x` | ✅ | ✅ green |
| 14-02-02 | 02 | 2 | ANLZ-01 | — | Conforming-limit MissingCountyDataError handled gracefully | unit | `uv run pytest tests/test_property_analysis.py::test_missing_county_graceful -x` | ✅ | ✅ green |
| 14-02-02 | 02 | 2 | ANLZ-01 | — | VA30 included only when profile.va_eligible=True | unit | `uv run pytest tests/test_property_analysis.py::test_va_eligibility_gates_program -x` | ✅ | ✅ green |
| 14-02-02 | 02 | 2 | ANLZ-02 | — | DownPaymentMatrix has 18 cells base / 24 with VA or Jumbo (programs_present × 6 DPs) per D-14-MATRIX-03 | unit + golden | `uv run pytest tests/test_property_analysis.py::test_matrix_cell_count -x` | ✅ | ✅ green |
| 14-02-02 | 02 | 2 | ANLZ-02 | — | Ineligible rows still populate all numerics per D-14-MATRIX-02 | unit | `uv run pytest tests/test_property_analysis.py::test_ineligible_rows_populate_numerics -x` | ✅ | ✅ green |
| 14-02-01 | 02 | 2 | ANLZ-02 | T-14-FLOAT | DP sweep uses exact `Decimal("0.03"), ("0.05"), ("0.10"), ("0.15"), ("0.20"), ("0.25")` | unit | `uv run pytest tests/test_property_analysis.py::test_dp_sweep_uses_decimal_strings -x` | ✅ | ✅ green |
| 14-03-01 | 03 | 2 | ANLZ-03 | — | Stress fan-out only at preferred DP (rate-shock + income-shock + ARM-reset rows) per D-14-STRESS-01 | unit + golden | `uv run pytest tests/test_property_analysis.py::test_stress_at_preferred_dp_only -x` | ✅ | ✅ green |
| 14-03-01 | 03 | 2 | ANLZ-03 | — | ARM reset stress fires for Conv30 only (D-14-STRESS-03) | unit | `uv run pytest tests/test_property_analysis.py::test_arm_reset_conv30_only -x` | ✅ | ✅ green |
| 14-03-01 | 03 | 2 | ANLZ-03 | — | Refi scan: 2 scenarios per program (FRED−1.00 AND FRED×0.85) | unit + golden | `uv run pytest tests/test_property_analysis.py::test_refi_two_scenarios_per_program -x` | ✅ | ✅ green |
| 14-03-02 | 03 | 2 | ANLZ-03 | — | Points breakeven: 1pt and 2pt drops per Conv-family program | unit + golden | `uv run pytest tests/test_property_analysis.py::test_points_breakeven_per_program -x` | ✅ | ✅ green |
| 14-03-02 | 03 | 2 | ANLZ-03 | — | IRS Pub 936 first-year interest + over-$750k flag per program | unit + golden | `uv run pytest tests/test_property_analysis.py::test_tax_block_pub936 -x` | ✅ | ✅ green |
| 14-04-02 | 04 | 2 | VERD-01 | — | Verdict cascade: NO_GO if no eligible at any DP | unit | `uv run pytest tests/test_property_verdict.py::test_no_go_no_eligible -x` | ✅ | ✅ green |
| 14-04-02 | 04 | 2 | VERD-01 | — | Verdict cascade: NO_GO if no eligible at preferred DP | unit | `uv run pytest tests/test_property_verdict.py::test_no_go_at_preferred_dp -x` | ✅ | ✅ green |
| 14-04-02 | 04 | 2 | VERD-01 | — | Verdict cascade: WATCH if income-shock stress fails any eligible (D-14-VERDICT-02) | unit | `uv run pytest tests/test_property_verdict.py::test_watch_income_shock -x` | ✅ | ✅ green |
| 14-04-02 | 04 | 2 | VERD-01 | — | Verdict cascade: WATCH if FHA-only eligible AND monthly MIP > $300 (D-14-VERDICT-01) | unit | `uv run pytest tests/test_property_verdict.py::test_watch_fha_mip_burden -x` | ✅ | ✅ green |
| 14-04-02 | 04 | 2 | VERD-01 | — | Verdict cascade: GO when non-FHA eligible AND no stress fail (D-14-VERDICT-03) | unit | `uv run pytest tests/test_property_verdict.py::test_go_non_fha_eligible -x` | ✅ | ✅ green |
| 14-04-02 | 04 | 2 | VERD-01 | T-14-REASON | Each VerdictReason carries both predicate_code AND computed_value (D-14-VERDICT-04) | unit + golden | `uv run pytest tests/test_property_verdict.py::test_reason_format_compliance -x` | ✅ | ✅ green |
| 14-04-02 | 04 | 2 | VERD-01 | — | Every VERDICT_* constant appears in at least one fixture (citation coverage) | meta-test | `uv run pytest tests/test_property_verdict.py::test_verdict_code_citation_coverage -x` | ✅ | ✅ green |
| 14-01-01 | 01 | 0 | (model) | — | Household model rejects extra fields | unit | `uv run pytest tests/test_household.py::test_extra_forbid -x` | ✅ | ✅ green |
| 14-01-02 | 01 | 0 | (model) | — | Profile model defaults va_eligible=False | unit | `uv run pytest tests/test_profile.py::test_va_eligible_default -x` | ✅ | ✅ green |
| 14-02-01 | 02 | 2 | (composition) | T-14-FLOAT | Money fields reject float inputs (strict=True) | unit | `uv run pytest tests/test_property_analysis.py::test_float_rejection -x` | ✅ | ✅ green |
| 14-06-03 | 06 | 3 | (composition) | — | AnalysisReport JSON size < 100KB (Pitfall 10 budget) | invariant | `uv run pytest tests/test_property_analysis.py::test_report_size_budget -x` | ✅ | ✅ green |
| 14-02-02 | 02 | 2 | (composition) | T-14-FRED-RACE | FRED cache reads serialize through with_cache_lock | unit | `uv run pytest tests/test_property_analysis.py::test_fred_lock_serialization -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_property_analysis.py` — stubs for ANLZ-01, ANLZ-02, ANLZ-03 (now 49 passing tests; Plan 14-02 `4e33ad3`)
- [x] `tests/test_property_verdict.py` — stubs for VERD-01 + citation coverage (now 13 passing tests; Plan 14-04 `90d1b58`)
- [x] `tests/test_household.py` — stubs for Household model contract (10 passing tests; Plan 14-01 `ddedb57`)
- [x] `tests/test_profile.py` — stubs for Profile model contract (12 passing tests; Plan 14-01 `036ff7a`)
- [x] `tests/conftest.py` — extended with `property_analysis_fixture` loader (Plan 14-02 `4e33ad3`)
- [x] `tests/fixtures/property_analysis/` directory (Plan 14-06 `6793e32`)
- [x] `tests/fixtures/property_analysis/sfh_conforming_king_county.json` (Plan 14-06 `6793e32`)
- [x] `tests/fixtures/property_analysis/condo_with_hoa_seattle.json` (Plan 14-06 `bd5c738`)
- [x] `tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` (Plan 14-06 `bd5c738`)
- [x] `tests/fixtures/property_analysis/README.md` (synthetic-address policy per Phase 13 D-13; Plan 14-06 `6793e32`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*All phase behaviors have automated verification — Phase 14 is pure library composition with golden-value pinning.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s (Phase 14 quick command runs in ~3s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-17

---

## Validation Audit 2026-05-17

| Metric | Count |
|--------|-------|
| Rows in map | 23 |
| COVERED | 23 |
| PARTIAL | 0 |
| MISSING (filled by audit) | 0 |
| Manual-only | 0 |

### Audit Methodology

1. Read all 6 SUMMARY.md files; extracted real task commit hashes per plan.
2. Loaded all 84 Phase-14 test names from `tests/test_property_analysis.py` (49), `tests/test_property_verdict.py` (13), `tests/test_household.py` (10), `tests/test_profile.py` (12).
3. Re-ran every row's `Automated Command` via `uv run pytest <command>` — confirmed 23/23 green in 3.06s with 2 informational stale-reference warnings (out-of-scope per Phase 16).
4. Replaced placeholder task IDs `14-XX-XX` with real plan-num + task-num bindings derived from the SUMMARY commit map.
5. Replaced `❌ W0` with `✅` for every row whose target test exists and passes; replaced `⬜ pending` with `✅ green`.
6. No row required a new test — all 23 planner-suggested test names landed verbatim in the implementation. The planner's matrix-cell-count description was tightened from "24/30 cells" to the actual implemented shape "18 base / 24 with VA or Jumbo" (3 base programs × 6 DPs = 18; +1 program with VA-eligible or Jumbo trigger = 24).

### Task-ID Commit Map

| Task ID | Plan | Commit | Plan-Summary Reference |
|---------|------|--------|------------------------|
| 14-01-01 | 01-foundation-models | `ddedb57` | Household model + 10 contract tests |
| 14-01-02 | 01-foundation-models | `036ff7a` | Profile model + 12 contract tests |
| 14-01-03 | 01-foundation-models | `35c9a33` | deferred-items.md log |
| 14-02-01 | 02-matrix-models | `8d602b1` | 12 Pydantic output models + 5 Final constants |
| 14-02-02 | 02-matrix-models | `8fcfc77` | per-cell composition helpers + matrix builder |
| 14-02-03 | 02-matrix-models | `4e33ad3` | property_analysis_fixture loader + Wave-2+ stub tests |
| 14-03-01 | 03-auxiliary-blocks | `d3bc7f0` | stress + refi helpers + _DTI_CEILING_BY_PROGRAM + 6 tests |
| 14-03-02 | 03-auxiliary-blocks | `ec777a4` | points + tax test assertions |
| 14-03-03 | 03-auxiliary-blocks | `cb7602c` | test_stress_rate_shock_piti_rises |
| 14-04-01 | 04-verdict-synthesis | `ed01b1d` | lib/property_verdict.py synthesize() |
| 14-04-02 | 04-verdict-synthesis | `90d1b58` | 12-test verdict suite |
| 14-05-01 | 05-analyze-composition | `00960b6` | analyze() body GREEN (preceded by `9f4e70f` RED) |
| 14-05-02 | 05-analyze-composition | `e3eeaa1` | flip stub + 7 new integration tests |
| 14-06-01 | 06-golden-fixtures | `6793e32` | SFH conforming fixture + README |
| 14-06-02 | 06-golden-fixtures | `bd5c738` | condo + jumbo fixtures + SFH conforming reformat |
| 14-06-03 | 06-golden-fixtures | `2fe0418` | flip 3 stubs + tighten citation coverage |

### Out-of-Scope Pre-existing Failures (NOT Phase 14's concern)

The following failures were flagged by `<audit_context>` as pre-existing and explicitly ignored per the audit scope:

- 7 pytest collection errors from macOS Finder duplicates: `lib/rules/fha_mip 2.py`, `lib/rules/fha_mip 3.py`, `.planning/config 2.json`, `.planning/config 3.json`.
- 1 uncommitted WIP edit to `lib/rules/fha_mip.py` (+14/-5) altering the docstring citation prefix (`"Citation (operative):"` vs `"Citation:"`) — documented in `deferred-items.md`.

None of these surfaces touch the Phase-14 test set (`tests/test_household.py`, `tests/test_profile.py`, `tests/test_property_analysis.py`, `tests/test_property_verdict.py`). Confirmed by isolated `uv run pytest <four-files>` run: 84 passed, 2 stale-reference warnings, 0 failures.

### Verification Re-run Result

```
$ uv run pytest \
    tests/test_property_analysis.py::test_matrix_fanout_conforming \
    tests/test_property_analysis.py::test_missing_county_graceful \
    tests/test_property_analysis.py::test_va_eligibility_gates_program \
    tests/test_property_analysis.py::test_matrix_cell_count \
    tests/test_property_analysis.py::test_ineligible_rows_populate_numerics \
    tests/test_property_analysis.py::test_dp_sweep_uses_decimal_strings \
    tests/test_property_analysis.py::test_stress_at_preferred_dp_only \
    tests/test_property_analysis.py::test_arm_reset_conv30_only \
    tests/test_property_analysis.py::test_refi_two_scenarios_per_program \
    tests/test_property_analysis.py::test_points_breakeven_per_program \
    tests/test_property_analysis.py::test_tax_block_pub936 \
    tests/test_property_verdict.py::test_no_go_no_eligible \
    tests/test_property_verdict.py::test_no_go_at_preferred_dp \
    tests/test_property_verdict.py::test_watch_income_shock \
    tests/test_property_verdict.py::test_watch_fha_mip_burden \
    tests/test_property_verdict.py::test_go_non_fha_eligible \
    tests/test_property_verdict.py::test_reason_format_compliance \
    tests/test_property_verdict.py::test_verdict_code_citation_coverage \
    tests/test_household.py::test_extra_forbid \
    tests/test_profile.py::test_va_eligible_default \
    tests/test_property_analysis.py::test_float_rejection \
    tests/test_property_analysis.py::test_report_size_budget \
    tests/test_property_analysis.py::test_fred_lock_serialization \
    -v
======================== 23 passed, 2 warnings in 3.06s ========================
```

All 23 mapped rows verified green. No MISSING gaps. No new tests generated. No lib/* modified.
