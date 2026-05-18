---
phase: 14
slug: property-analysis-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
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
| 14-XX-XX | XX | X | ANLZ-01 | — | Multi-program fan-out produces ProgramResult per (program, DP); jumbo triggers when price > conforming limit | unit + golden | `pytest tests/test_property_analysis.py::test_matrix_fanout_conforming -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-01 | — | Conforming-limit MissingCountyDataError handled gracefully | unit | `pytest tests/test_property_analysis.py::test_missing_county_graceful -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-01 | — | VA30 included only when profile.va_eligible=True | unit | `pytest tests/test_property_analysis.py::test_va_eligibility_gates_program -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-02 | — | DownPaymentMatrix has 24 cells (no jumbo) or 30 cells (jumbo) | unit + golden | `pytest tests/test_property_analysis.py::test_matrix_cell_count -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-02 | — | Ineligible rows still populate all numerics per D-14-MATRIX-02 | unit | `pytest tests/test_property_analysis.py::test_ineligible_rows_populate_numerics -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-02 | T-14-FLOAT | DP sweep uses exact `Decimal("0.03"), ("0.05"), ("0.10"), ("0.15"), ("0.20"), ("0.25")` | unit | `pytest tests/test_property_analysis.py::test_dp_sweep_uses_decimal_strings -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-03 | — | Stress fan-out: 12-15 rows at preferred DP only | unit + golden | `pytest tests/test_property_analysis.py::test_stress_at_preferred_dp_only -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-03 | — | ARM reset stress fires for Conv30 only (D-14-STRESS-03) | unit | `pytest tests/test_property_analysis.py::test_arm_reset_conv30_only -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-03 | — | Refi scan: 2 scenarios per program (FRED−1.00 AND FRED×0.85) | unit + golden | `pytest tests/test_property_analysis.py::test_refi_two_scenarios_per_program -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-03 | — | Points breakeven: 1pt and 2pt drops per Conv-family program | unit + golden | `pytest tests/test_property_analysis.py::test_points_breakeven_per_program -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | ANLZ-03 | — | IRS Pub 936 first-year interest + over-$750k flag per program | unit + golden | `pytest tests/test_property_analysis.py::test_tax_block_pub936 -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | VERD-01 | — | Verdict cascade: NO_GO if no eligible at any DP | unit | `pytest tests/test_property_verdict.py::test_no_go_no_eligible -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | VERD-01 | — | Verdict cascade: NO_GO if no eligible at preferred DP | unit | `pytest tests/test_property_verdict.py::test_no_go_at_preferred_dp -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | VERD-01 | — | Verdict cascade: WATCH if income-shock stress fails any eligible (D-14-VERDICT-02) | unit | `pytest tests/test_property_verdict.py::test_watch_income_shock -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | VERD-01 | — | Verdict cascade: WATCH if FHA-only eligible AND monthly MIP > $300 (D-14-VERDICT-01) | unit | `pytest tests/test_property_verdict.py::test_watch_fha_mip_burden -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | VERD-01 | — | Verdict cascade: GO when non-FHA eligible AND no stress fail (D-14-VERDICT-03) | unit | `pytest tests/test_property_verdict.py::test_go_non_fha_eligible -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | VERD-01 | T-14-REASON | Each VerdictReason carries both predicate_code AND computed_value (D-14-VERDICT-04) | unit + golden | `pytest tests/test_property_verdict.py::test_reason_format_compliance -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | VERD-01 | — | Every VERDICT_* constant appears in at least one fixture (citation coverage) | meta-test | `pytest tests/test_property_verdict.py::test_verdict_code_citation_coverage -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | (model) | — | Household model rejects extra fields | unit | `pytest tests/test_household.py::test_extra_forbid -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | (model) | — | Profile model defaults va_eligible=False | unit | `pytest tests/test_profile.py::test_va_eligible_default -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | (composition) | T-14-FLOAT | Money fields reject float inputs (strict=True) | unit | `pytest tests/test_property_analysis.py::test_float_rejection -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | (composition) | — | AnalysisReport JSON size < 100KB (Pitfall 10 budget) | invariant | `pytest tests/test_property_analysis.py::test_report_size_budget -x` | ❌ W0 | ⬜ pending |
| 14-XX-XX | XX | X | (composition) | T-14-FRED-RACE | FRED cache reads serialize through with_cache_lock | unit | `pytest tests/test_property_analysis.py::test_fred_lock_serialization -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_property_analysis.py` — stubs for ANLZ-01, ANLZ-02, ANLZ-03
- [ ] `tests/test_property_verdict.py` — stubs for VERD-01 + citation coverage
- [ ] `tests/test_household.py` — stubs for Household model contract
- [ ] `tests/test_profile.py` — stubs for Profile model contract
- [ ] `tests/conftest.py` — extend with `property_analysis_fixture` loader (load-by-stem pattern from `affordability_fixture`)
- [ ] `tests/fixtures/property_analysis/` directory
- [ ] `tests/fixtures/property_analysis/sfh_conforming_king_county.json`
- [ ] `tests/fixtures/property_analysis/condo_with_hoa_seattle.json`
- [ ] `tests/fixtures/property_analysis/sfh_jumbo_bay_area.json`
- [ ] `tests/fixtures/property_analysis/README.md` (synthetic-address policy per Phase 13 D-13)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*All phase behaviors have automated verification — Phase 14 is pure library composition with golden-value pinning.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
