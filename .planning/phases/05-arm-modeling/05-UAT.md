---
status: complete
phase: 05-arm-modeling
source:
  - 05-00-SUMMARY.md
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
  - 05-04a-SUMMARY.md
  - 05-04b-SUMMARY.md
  - 05-05-SUMMARY.md
  - 05-06-SUMMARY.md
started: 2026-05-03T01:17:35Z
updated: 2026-05-03T01:25:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Full Test Suite Passes
expected: |
  Run `uv run pytest -q` from the repo root. Suite reports 432 passed,
  4 skipped, 1 xfailed, 0 failed, 0 errors. The single xfail is the
  deferred Bankrate/Vertex42 5/1 cross-source check (ARM-06 partial).
result: pass
observed: "432 passed, 4 skipped, 1 xfailed, 3 warnings in 14.93s. xfail = test_oracle_cross_validation_5_1 (Phase 8+ deferral per T-05-34)."

### 2. ARM CLI End-to-End Round Trip
expected: |
  Run `uv run python scripts/arm_simulate.py --input <fixture.json>` against
  a 5/1 ARM input. Stdout returns valid JSON ARMSchedule with payments=360,
  reset_events=25, first reset at period 61, last reset at period 349,
  final balance == 0.00. Exit code 0.
result: pass
observed: "exit=0; payments=360; reset_events=25; first_reset=61; last_reset=349; final_balance=0.00; final_period=360 (5/1 ARM fixture: 400k @ 5%/30yr, 2/1/5 caps, 0.0525 index)."

### 3. CLI --help Is Fast (Lazy Imports)
expected: |
  Run `uv run python scripts/arm_simulate.py --help`. Help text prints
  promptly (sub-second on a warm shell) and the heavy modules
  (lib.arm, lib.amortize, numpy_financial) are NOT imported during --help.
  This protects D-18 (--help works without loading the engine).
result: pass
observed: "--help completes in 0.063s wall time. python -X importtime confirms lib.arm, lib.amortize, numpy_financial are NOT loaded during --help. exit=0; 16 help lines."

### 4. CLI Rejects Float Inputs With 6-Key Error Envelope
expected: |
  Submit a request JSON containing a float (e.g. `"principal": 400000.0`)
  to scripts/arm_simulate.py. CLI exits 2 and prints a 6-key envelope on
  stderr: type=decimal_type, loc, msg, input, ctx, url. Same envelope
  shape as scripts/amortize.py and scripts/affordability.py (WR-02).
result: pass
observed: "exit=2; stderr envelope keys = {type, loc, msg, input, url, ctx} (6 keys); type=decimal_type; loc=[loan, principal]; ctx.class=Decimal; ctx.field_path=loan.principal."

### 5. CLI Rejects Misaligned index_path Period
expected: |
  Submit an ARMRequest with index_path entry at period 62 on a 5/1 ARM
  (resets are 61, 73, 85, ...). CLI exits 2; stderr envelope reports
  ValueError from ARMRequest._index_path_periods_align_to_reset_triggers.
result: pass
observed: "exit=2; type=value_error; msg='index_path entry at period 62 does not align to a reset trigger period (D-01). Valid triggers for this product: [61, 73, 85, 97, 109]...'."

### 6. Reset Months Match ARM Conventions
expected: |
  For each ARM type, first reset fires at the documented month:
  5/1 → month 61, 7/1 → month 85, 10/1 → month 121, 5/6 → first reset
  at 61, second reset at 67 (every 6 months thereafter). Visible as
  payment-jump tests in tests/test_arm.py and as reset_events list
  on schedule output.
result: pass
observed: "5/1: first=61, second=73, total=25. 7/1: first=85, second=97, total=23. 10/1: first=121, second=133, total=20. 5/6: first=61, second=67, total=50. All match published ARM reset conventions."

### 7. Cap Precedence: Initial → Periodic → Lifetime → Floor
expected: |
  At first reset, only initial_cap_bps applies (not periodic_cap_bps).
  At subsequent resets, periodic_cap_bps applies. Lifetime ceiling
  uses note_rate (or loan.annual_rate when note_rate is None per LM-3).
  When floor lifts the rate above fully-indexed, applied_cap == "floor".
  ResetEvent.applied_cap is one of: initial, periodic, lifetime, floor, none.
result: pass
observed: "initial fixture: applied_cap=initial at period 61, periodic at 73+. lifetime fixture: lifetime binds at every reset. floor fixture: floor binds. modest 5/1: applied_cap=none. All Literal values exercised; test_applied_cap_citation_coverage meta-test passes."

### 8. Schedule Reaches Zero Balance at Maturity
expected: |
  For a 30-year ARM, the final payment row ends with balance == 0.00.
  Cumulative_interest is continuous across reset boundaries (no zeroing
  at non-final epochs). test_cumulative_totals_continuous_across_resets
  and test_non_final_epoch_does_not_zero_balance pin this.
result: pass
observed: "final balance=0.00 at period 360. Period 60 balance=367314.67, period 72=362313.21, period 84=356910.09 (all positive — no non-final epoch zeroing). cumulative_interest monotonic non-decreasing 1666.67 → 561167.66."

### 9. floor_rate Is Required (No Default)
expected: |
  Constructing ARMTerms without floor_rate raises pydantic ValidationError
  with type='missing'. There is no default — D-02 "fail loud, no inference"
  is enforced at the model boundary.
result: pass
observed: "ARMTerms(...) without floor_rate raises ValidationError; missing errors = [(('floor_rate',), 'missing')]."

### 10. references/arm-mechanics.md Reference Doc
expected: |
  File exists at references/arm-mechanics.md with the 7 D-08 [REVISED]
  sections: Reset Month Convention, Cap Precedence, Floor Algebra,
  Quantization, Negative Amortization Out of Scope, index_series_id
  Semantics, Teaser-ARM Lifetime Cap Base. Cites Fannie B2-1.4-02,
  Freddie 6302.7(b), CFPB §1951, ABT Bank 5/6 SOFR (NOT the broken
  legacy B5-3.5-01 / §4404 citations).
result: pass
observed: "196 lines; all 7 sections + Appendix headers present. Citations: B2-1.4-02 x8, 6302.7 x4, §1951 x6, abt.bank x3. Forbidden legacy: B5-3.5-01 x0, §4404 x0."

### 11. ARMTerms Docstring Cites arm-mechanics.md
expected: |
  `help(lib.arm.ARMTerms)` (or grep on lib/arm.py) shows the docstring
  contains a pointer to references/arm-mechanics.md. Provides
  grep-discoverability from Phase 11 amortization-agent context (SC-5).
result: pass
observed: "ARMTerms.__doc__ is 545 chars and contains both 'references/' and 'arm-mechanics.md' tokens. SC-5 verified."

### 12. Oracle Cross-Validation Against ABT Bank 5/6 SOFR
expected: |
  tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.pdf and
  the matching .json transcription exist. test_oracle_cross_validation_5_6
  passes: engine output matches ABT Bank's published worst-case payment
  ($90.54 per $10k at 10.375% over 360 months) under the disclosure's
  full-original-term convention.
result: pass
observed: "PDF + JSON both present. PDF SHA256=891e70b7bc9de8a9804f53f32d1cb05488e381dd9b147bcd76d466555da2d83b (matches Plan 05-06). test_oracle_cross_validation_5_6 PASSED in 0.24s."

### 13. lib.money.quantize_rate Public Helper (D-14 Promotion)
expected: |
  `from lib.money import quantize_rate` succeeds. It quantizes Decimal
  rates to 6 decimals using ROUND_HALF_UP. Golden pin:
  quantize_rate(Decimal("0.0654995")) == Decimal("0.065500").
  lib/affordability.py no longer defines a private _quantize_rate.
result: pass
observed: "quantize_rate(0.0654995)=0.065500 (ROUND_HALF_UP boundary). 0.0654994 -> 0.065499. grep -c _quantize_rate lib/affordability.py = 0 (D-14 migration clean)."

## Summary

total: 13
passed: 13
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
