# Phase 14 Deferred Items

Discovered during plan execution but out-of-scope for the current plan.

## Plan 14-01 (foundation-models, 2026-05-18)

### Pre-existing test failures NOT caused by Plan 14-01

The working tree was running with an uncommitted modification to
`lib/rules/fha_mip.py` (+14/-5) when Plan 14-01 began. That uncommitted change
breaks two tests that pass on a clean stash:

1. `tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring[fha_mip]`
   — docstring lost the literal `"Citation:"` token (now reads `"Citation (operative):"`).
2. `tests/test_rules/test_citation_coverage_mutations.py::test_meta_tests_pass_unmutated_baseline`
   — cascade: this meta-test invokes the citation_coverage test in a subprocess and asserts
   it passes; it inherits failure #1.

Verification that failures are pre-existing (not from Plan 14-01):
- `git stash && pytest tests/test_rules/test_citation_coverage.py -x` → 11/11 PASS.
- `git stash pop && pytest tests/test_rules/test_citation_coverage.py -x` → fha_mip FAIL.
- The two failing tests exercise `lib/rules/fha_mip.py` only; Plan 14-01 touches
  `lib/household.py`, `lib/profile.py`, `tests/test_household.py`, `tests/test_profile.py` only.

Per `<work_in_progress_note>` in the agent prompt: the fha_mip.py change is unrelated
to Phase 14 and was instructed NOT to be touched. The fix belongs in whichever
session originally modified fha_mip.py (likely a citation-format refactor that needs
either an updated `Citation:` literal or an update to the citation_coverage regex).

Plan 14-01 itself ships clean: 22/22 tests in `tests/test_household.py` +
`tests/test_profile.py` pass; the new `lib/household.py` and `lib/profile.py`
modules import without error and don't perturb any other test path.
