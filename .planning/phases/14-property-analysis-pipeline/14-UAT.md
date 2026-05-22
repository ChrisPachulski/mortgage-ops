---
status: testing
phase: 14-property-analysis-pipeline
source: [14-01-foundation-models-SUMMARY.md, 14-02-matrix-models-SUMMARY.md, 14-03-auxiliary-blocks-SUMMARY.md, 14-04-verdict-synthesis-SUMMARY.md, 14-05-analyze-composition-SUMMARY.md, 14-06-golden-fixtures-SUMMARY.md]
started: 2026-05-19T03:52:13Z
updated: 2026-05-19T03:52:13Z
---

## Current Test

number: 1
name: Cold-Start Import Smoke
expected: |
  Running `uv run python -c "from lib.property_analysis import analyze; from lib.property_verdict import synthesize; from lib.household import Household; from lib.profile import Profile; print('imports OK')"` from /Users/cujo253/Documents/mortgage-ops prints "imports OK" with no traceback and no warnings beyond StaleReferenceWarning for the reference YAMLs.
awaiting: user response

## Tests

### 1. Cold-Start Import Smoke
expected: Running `uv run python -c "from lib.property_analysis import analyze; from lib.property_verdict import synthesize; from lib.household import Household; from lib.profile import Profile; print('imports OK')"` from /Users/cujo253/Documents/mortgage-ops prints "imports OK" with no traceback and no warnings beyond StaleReferenceWarning for the reference YAMLs.
result: [pending]

### 2. End-to-End analyze() Demo Run
expected: Running `uv run pytest tests/test_property_analysis.py::test_sfh_conforming_king_county_golden -v -s` exits 0. Inspect the test output — the analyze() call against the SFH conforming King County synthetic listing returns an AnalysisReport with all 6 blocks populated (matrix, stress, refi, points, tax, verdict), and the test's exact-Decimal cell assertions match the hand-calc fixture.
result: [pending]

### 3. Verdict Reason Readability
expected: |
  Open tests/fixtures/property_analysis/sfh_conforming_king_county.json and inspect `expected_response.verdict.reasons[]`. Each reason should be a short, falsifiable string of the form `"<PREDICATE-CODE>: <computed-value> (program=X, dp=Y)"` (e.g., "GO-ALL-GREEN: ... (program=Conv30, dp=0.20)"). Reads like something you'd be comfortable showing a CPA — no marketing copy, no hand-waving. Per D-14-VERDICT-04 + CONTEXT.md "Verdict copy is short and falsifiable."
result: [pending]

### 4. AnalysisReport Schema Frozen for Phase 15
expected: |
  Open lib/property_analysis.py and skim the AnalysisReport model definition (search for `class AnalysisReport`). The top-level fields should be: listing_snapshot, household_snapshot_hash, fetched_at, fred_mortgage_30us, fred_mortgage_15us, matrix, stress, refi, points, tax, verdict, warnings. This is the schema Phase 15's markdown formatter will consume — confirm the field names + ordering match what you'd want a `lib/property_report.py` to receive as input.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
