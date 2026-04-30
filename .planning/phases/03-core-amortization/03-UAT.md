---
status: complete
phase: 03-core-amortization
source:
  - 03-01-SUMMARY.md
  - 03-02-SUMMARY.md
  - 03-03-SUMMARY.md
  - 03-04-SUMMARY.md
  - 03-VERIFICATION.md
  - 03-REVIEW.md
started: 2026-04-29T23:40:00Z
updated: 2026-04-29T23:50:00Z
---

## Current Test

[testing complete]

## Tests

### 1. CLI smoke test — run scripts/amortize.py end-to-end
expected: Running `uv run python scripts/amortize.py --input tests/fixtures/amortize/extra_oneshot_5k_period_60.json` from the project root prints a JSON object with `monthly_pi: "2528.27"`, a `payments` array, `final_payment_adjusted: true`, and the final-row `balance: "0.00"`. Exit code 0.
result: pass

### 2. CR-01 decision — _resolve_extra duplicate-period non-determinism
expected: Decide between (a) reject duplicate (period, recurring=True) entries at AmortizeRequest validation time, (b) document a deterministic tie-breaker (e.g., last-wins or sum) and pin it with a fixture, or (c) accept the status quo as out-of-scope for personal use. Reproduction case from code review: two `ExtraPrincipalEntry` rows with the same `period` and `recurring=True` produce different schedules depending on input order ([100, 200] → 100.00; [200, 100] → 200.00).
result: issue
reported: "User chose (a) — reject duplicate (period, recurring=True) entries via AmortizeRequest validator."
severity: major
decision: a
fix_summary: "Add a model_validator to AmortizeRequest in lib/amortize.py that rejects any two ExtraPrincipalEntry rows sharing the same `period` when both are `recurring=True`. Surface as Pydantic ValidationError so the CLI emits a structured error envelope. Add a unit test in tests/test_amortize.py pinning the rejection. Update lib/amortize.py module docstring D-05 line to anchor the new constraint."

### 3. WR-02 decision — CLI error envelope inconsistency
expected: Decide between (a) unify the float-gate error envelope to Pydantic's 6-key shape ({type, loc, msg, input, url, ctx}), or (b) accept the 3-key float-gate shape ({type, loc, msg}) and document the asymmetry so Phase 9 Node orchestration / Phase 10 skill knows to handle both shapes.
result: issue
reported: "User chose (a) — unify float-gate error envelope to Pydantic's 6-key shape."
severity: minor
decision: a
fix_summary: "Refactor `_find_json_float_loc` and the surrounding error-emission path in scripts/amortize.py so the float-in-money gate emits the same Pydantic-shaped envelope ({type, loc, msg, input, url, ctx}) as native ValidationError. Populate `input` with the offending JSON value, `url` with Pydantic's decimal_type docs URL, and `ctx` with the field path. Update the existing CLI tests in tests/test_amortize.py asserting envelope shape to lock the 6-key contract."

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Two ExtraPrincipalEntry rows with the same period and recurring=True must not produce order-dependent schedules"
  status: failed
  reason: "User chose option (a): reject duplicate (period, recurring=True) entries via AmortizeRequest validator. Code review CR-01 verified empirically: [100, 200] order returns 100.00; [200, 100] returns 200.00. D-05 spec is silent on tie-breaking; this fix tightens the contract by rejecting the ambiguity at the boundary."
  severity: major
  test: 2
  artifacts:
    - path: "lib/amortize.py"
      provides: "AmortizeRequest model_validator rejecting duplicate (period, recurring=True) entries"
    - path: "tests/test_amortize.py"
      provides: "Unit test pinning rejection of duplicate-period recurring entries"
  missing:
    - "AmortizeRequest validator for ExtraPrincipalEntry uniqueness on (period, recurring=True)"
    - "Pinned test case for duplicate-period rejection"
    - "D-05 docstring update in lib/amortize.py anchoring the new constraint"

- truth: "scripts/amortize.py error envelopes must have a uniform shape across all failure modes"
  status: failed
  reason: "User chose option (a): unify float-gate envelope to Pydantic's 6-key shape ({type, loc, msg, input, url, ctx}). Code review WR-02 verified the float-gate emits 3 keys while Pydantic emits 6 — Phase 9 Node orchestration and Phase 10 SKILL.md narration would need conditional shape handling without this fix."
  severity: minor
  test: 3
  artifacts:
    - path: "scripts/amortize.py"
      provides: "_find_json_float_loc emits Pydantic-shaped 6-key error envelope ({type, loc, msg, input, url, ctx})"
    - path: "tests/test_amortize.py"
      provides: "Updated CLI subprocess test asserting 6-key envelope shape on float-in-money input"
  missing:
    - "input/url/ctx keys populated in float-gate error envelope"
    - "Test asserting 6-key envelope shape (not 3-key) for float-in-money gate"
    - "Docstring note in scripts/amortize.py confirming envelope-shape contract"
