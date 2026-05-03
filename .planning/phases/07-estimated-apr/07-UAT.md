---
status: complete
phase: 07-estimated-apr
source:
  - 07-00-test-infrastructure-SUMMARY.md
  - 07-01-pydantic-models-SUMMARY.md
  - 07-02-newton-raphson-engine-SUMMARY.md
  - 07-03-odd-first-period-helpers-SUMMARY.md
  - 07-04-cli-SUMMARY.md
  - 07-05-tests-and-fixtures-SUMMARY.md
  - 07-06-references-doc-SUMMARY.md
  - 07-07-ffiec-fixtures-SUMMARY.md
started: 2026-05-03T21:30:00Z
updated: 2026-05-03T21:55:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold-Start Smoke Test
expected: |
  uv sync && .venv/bin/pytest -q | tail -3 → 502 passed / 4 skipped /
  1 xfailed in ~17s. The xfail is the Phase 5 ARM Bankrate/Vertex42
  oracle deferral (test_oracle_cross_validation_5_1), not Phase 7.
result: pass
observed: 502 passed, 4 skipped, 1 xfailed in 16.89s — exact match.

### 2. CLI SC-1 Anchor (Reg Z Appendix J $5000/36/$166.07)
expected: |
  CLI returns estimated_apr ≈ 0.119994, iterations: 1, summary
  contains literal "estimated APR".
result: pass
observed: |
  {
    "estimated_apr": "0.119994",
    "iterations": 1,
    "final_residual": "0.00",
    "summary": "estimated APR: 11.9994% (converged in 1 iterations, residual $0.00)",
    "tolerance_check": null
  }
  |regulatory 0.120000 - engine 0.119994| = 0.000006, within Decimal("0.00001") tolerance.
note: |
  CLI happy-path emits bare APRResponse to stdout (5 keys); error
  paths emit Pydantic-style per-error array to stderr where each
  error dict has 6 keys (type/loc/msg/input/url/ctx). The "6-key
  envelope" terminology in plan 07-04 SUMMARY refers to the
  per-error dict shape, not a top-level wrapper. Confirmed against
  scripts/apr_reg_z.py docstring lines 13-17.

### 3. CLI --help Surfaces "estimated APR" + Reg Z Citation
expected: |
  --help mentions "estimated APR", references "12 CFR Part 1026
  Appendix J", and points readers to references/apr-reg-z.md.
  Exits with code 0.
result: pass
observed: |
  Help text mentions "estimated APR" 4 times, "12 CFR Part 1026
  Appendix J (Reg Z)" in description, "references/apr-reg-z.md"
  for day-count/unit-period/odd-first-period conventions, and
  cites ROADMAP SC-4 for the literal-text invariant.

### 4. CLI Error Envelope on APRConvergenceError
expected: |
  Pathological request that can't converge within 50 iterations
  surfaces as a structured error with exit code 2.
result: pass
observed: |
  Pathological input ($5000 principal repaid by 36 × $0.01) emits
  per-error array with type=value_error, loc=[solver],
  msg="Newton-Raphson did not converge within 1 iterations
  (ROADMAP SC-3 cap=50)", ctx.class=APRConvergenceError,
  ctx.iterations=1, ctx.last_residual=4999.67..., ctx.last_i=0.005.
  Exit code 2. Per-error dict has all 6 expected keys.

### 5. Reference Doc references/apr-reg-z.md
expected: |
  - File exists at references/apr-reg-z.md (~523 lines)
  - Contains 6 required section headers covering unit-period
    model, day-count, odd-first, citations, worked example,
    convergence/limitations
  - lib/apr.py module + APRRequest docstring cite the doc
result: pass
observed: |
  - File: 523 lines (matches expected)
  - Sections (numbered top-level):
    1. Unit-Period Model (12 CFR Part 1026 Appendix J)
    2. Day-Count Conventions
    3. Odd First Period Handling (§1026.17(c)(4))
    4. Worked Example — Reg Z Appendix J Example J(c)(1)
    5. Newton-Raphson Convergence
    6. Citations Summary (verified 2026-05-02)
    + Appendix — Citation Index
  - grep -c 'references/apr-reg-z.md' lib/apr.py = 5 (≥4 PASS)
note: |
  My UAT pre-spec said §5 = "Limitations". The doc instead uses
  "Newton-Raphson Convergence" for §5 and includes
  limitations/coverage notes inline + via Citation Index. The
  Wave-0 stub for APR-08 flips green against the actual doc, so
  the deliverable satisfies plan-checker's contract. My UAT
  expectation was slightly off, doc content is correct.

### 6. Oracle Corpus & Honest Provenance README
expected: |
  - 20 ffiec_*.json files in tests/fixtures/apr/oracle/
  - README.md documents fallback chain + per-fixture provenance
  - No false claims of FFIEC tool / regulatory provenance
  - Partial closure for SC-2/APR-04 honestly disclosed
result: pass
observed: |
  - ls tests/fixtures/apr/oracle/ffiec_*.json | wc -l = 20
  - tests/fixtures/apr/oracle/README.md = 234 lines
  - 12/20 fixtures cross-validated against Wikipedia worked
    example via PV-form algebraic identity (engine APR == nominal
    rate exactly); 8/20 engine-emitted only.
  - Partial closure disclosed in SUMMARY §Partial Closure,
    oracle/README.md, STATE.md narrative, ROADMAP SC-2 entry,
    REQUIREMENTS.md APR-04 row.

### 7. Library Import + Public API Surface
expected: |
  from lib.apr import solve_apr, APRRequest, APRResponse,
  APRConvergenceError succeeds without errors.
result: pass
observed: |
  Print: "OK solve_apr APRRequest APRResponse APRConvergenceError"
  No ImportError, no warnings.

### 8. SC-4 Literal Text Contract — bare "APR" never appears
expected: |
  Search response.summary for bare "APR" (i.e., not preceded by
  "estimated "). Must NOT appear.
result: pass
observed: |
  re.findall(r'(?<!estimated )\bAPR\b',
             "estimated APR: 11.9994% (converged in 1 iterations, residual $0.00)")
  → 0 matches. Literal-text contract enforced end-to-end through
  the model boundary validator (D-05) + CLI surface (D-22) +
  regex test (Wave 5).

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all tests pass]

## Notes

- 2 minor discrepancies between my pre-test UAT specifications
  and reality, both in MY spec not the deliverable:
  1. Test 2 "6-key envelope" was per-error dict shape, not
     top-level wrapper. CLI contract is correct.
  2. Test 5 §5 section name is "Newton-Raphson Convergence" not
     "Limitations". Wave-0 stub for APR-08 still flips green
     against the actual headers.

- Phase 7 SC-2 / APR-04 partial closure (8/20 oracle fixtures
  lack external cross-validation) is honestly disclosed and
  queued for future closure (FFIEC APRWIN under Wine/VM, or HMDA
  Platform Docker).

- All 8 plans, 33 atomic commits, zero AI attribution, zero
  regression to Phase 5 baseline (461 → 502 = +41 net new tests).
