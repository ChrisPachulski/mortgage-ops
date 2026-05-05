---
status: complete
phase: 08-stress-points
source:
  - 08-00-test-infrastructure-SUMMARY.md
  - 08-01-pydantic-models-SUMMARY.md
  - 08-02-stress-engine-SUMMARY.md
  - 08-03-points-engine-SUMMARY.md
  - 08-04-clis-SUMMARY.md
  - 08-05-fixtures-and-tests-SUMMARY.md
  - 08-06-references-SUMMARY.md
started: 2026-05-05T03:42:57Z
updated: 2026-05-05T03:48:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Stress CLI — Rate Shock Sweep (ROADMAP SC-1)
expected: scripts/stress_test.py --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08 returns scenario_count=5 with row labels matching the rate grid; row at 0.065 produces monthly_pi=2528.27 (Phase 3 oracle anchor).
result: pass

### 2. Stress CLI — Income Shock Sweep (ROADMAP SC-2)
expected: scripts/stress_test.py --mode income-shock --reductions 0.05,0.10,0.20 returns 3 rows with labels ["-5%","-10%","-20%"] and breaches_threshold populated per row (boolean field present, not missing).
result: pass

### 3. Stress CLI — ARM Path Sweep (ROADMAP SC-3)
expected: Submitting an ArmResetRequest with the three canonical paths (parallel-shift, gradual-rise, fall-then-rise) on a 5/1 ARM 30yr base produces 3 rows; each carries reset_count=25 (one per ARM trigger over the 30yr horizon).
result: pass

### 4. Points CLI — Simple vs NPV Divergence (ROADMAP SC-4)
expected: scripts/points_breakeven.py with $8000 points_cost / $65.40 monthly_savings / 240mo hold / 7% discount returns simple_breakeven_months=123, npv_breakeven_months=215, diverge=true, decision="buy_points", gap of +92 months. Both fields reported side-by-side in the response.
result: pass

### 5. Points CLI — Zero Discount Equality
expected: With the same scenario but discount_rate_annual=0.00, simple_breakeven_months equals npv_breakeven_months (both 123) and diverge=false (zero-discount collapses to simple per D-03-03).
result: pass

### 6. Stress Output Field Order (ROADMAP SC-5)
expected: In the JSON output of any stress sweep, the "summary" key appears BEFORE the "rows" key (Pydantic field-declaration order preserved). Verifiable via substring check on indented output: position of '"summary"' < position of '"rows"'.
result: pass

### 7. Float Rejection — 6-Key Envelope
expected: Submitting a JSON input with a float principal (e.g., "principal": 400000.0 instead of "400000.00") to scripts/stress_test.py exits non-zero and emits a 6-key error envelope on stderr: {decimal_type, loc, msg, type, input, ctx} where ctx.class=="Decimal". Same shape from scripts/points_breakeven.py (e.g., "monthly_savings": 65.40 as JSON float rejected).
result: pass

### 8. Reference Doc Discoverability
expected: scripts/stress_test.py --help epilog mentions "references/stress-tests.md"; scripts/points_breakeven.py --help epilog mentions "references/points-breakeven.md". Both reference files exist on disk with regulatory citations (CFPB §1026.43(c)(5), IRS Pub 936, Reg Z §1026.18).
result: pass

### 9. SC-5 Size Budget — 50-Rate Sweep
expected: Loading tests/fixtures/stress/rate_shock_size_budget_50_rates.json through lib.stress.evaluate yields a JSON dump under 100KB (~37,623 bytes per Plan 08-05) AND summary key still precedes rows key in the indented output.
result: pass

### 10. Full Test Suite Pass
expected: pytest -q from the project root reports 521 passed, 4 skipped, 1 xfailed, 0 failed, 0 errored. The single remaining xfail is the inherited Phase 5 ARM oracle Bankrate/Vertex42 deferral — NOT a Phase 8 stub. Zero regression to the Phase 7 baseline of 502/4/1.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all tests passed]
