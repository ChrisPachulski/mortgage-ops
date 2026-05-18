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

## Plan 14-04 (verdict-synthesis, 2026-05-18)

### Pre-existing macOS Finder/iCloud duplicates of fha_mip.py

Found during Plan 14-04 full-suite verification: two untracked siblings of
lib/rules/fha_mip.py with Finder/iCloud-style numeric suffixes:

- `lib/rules/fha_mip 2.py` (6938 bytes, mtime 2026-05-18 10:47)
- `lib/rules/fha_mip 3.py` (6938 bytes, mtime 2026-05-18 10:56)

These cause `tests/test_rules/test_citation_coverage.py` to discover them as
additional `[fha_mip 2]` and `[fha_mip 3]` parametrizations (the test
discovers predicate modules by glob), producing 4 additional failures:

- `test_predicate_has_citation_in_docstring[fha_mip 2]` (passes — file has
  the older `"Citation:"` docstring before the in-progress refactor)
- `test_predicate_has_citation_in_docstring[fha_mip 3]` (passes — same)
- `test_predicate_has_at_least_one_fixture[fha_mip 2]` (FAILS — no fixture
  for the duplicate module name)
- `test_predicate_has_at_least_one_fixture[fha_mip 3]` (FAILS — same)

Plus `tests/test_rules/test_phase2_smoke.py::test_filesystem_predicate_count_matches_expected`
fails because the expected predicate count is hard-coded and the duplicates
push the count over the threshold.

These are out-of-scope for Plan 14-04 (the duplicates pre-date the plan; they
were already present when the plan started and are not produced by
Plan 14-04's `lib/property_verdict.py` + `tests/test_property_verdict.py`
work). The user should delete them manually:

```bash
rm "lib/rules/fha_mip 2.py" "lib/rules/fha_mip 3.py"
```

Plan 14-04 itself ships clean: 12/12 tests in `tests/test_property_verdict.py`
pass; the new `lib/property_verdict.py` module imports without error and the
full suite passes (812/812 modulo the 5 pre-existing fha_mip-* failures
documented above).

### Verification that failures are pre-existing (not from Plan 14-04)

```bash
git stash push -m "test-isolation" lib/rules/fha_mip.py
pytest tests/test_rules/test_citation_coverage.py tests/test_rules/test_phase2_smoke.py
# Still produces the same 5 failures (4 fha_mip-2/3 + 1 smoke count)
# because the duplicate `lib/rules/fha_mip 2.py` and `lib/rules/fha_mip 3.py`
# files are not stashable via path arg (untracked).
git stash pop
```

