---
phase: 06
plan: 06
subsystem: references-doc
tags:
  - phase-06
  - refinance-npv
  - references
  - documentation
  - sc-5
  - refi-09
  - d-04
  - d-16
requires:
  - "lib/refinance.py module docstring + RefiCashflow validator messages (Plan 06-01; D-16 surfaces 1 + 2)"
  - "scripts/refi_npv.py --help epilog cite (Plan 06-04; D-16 surface 4)"
  - "tests/test_refinance.py REFI_NPV_DOC_PATH constant + 2 Wave-0 doc stubs (Plan 06-00)"
  - "06-PATTERNS §'references/refi-npv.md' 7-section template lifted from references/arm-mechanics.md (Phase 5 D-16 precedent)"
  - "06-RESEARCH §'Locked Decisions' D-01..D-16 cross-reference + §'(d) Pinned Oracles' Oracle 1/2/3 worked-example body"
provides:
  - "references/refi-npv.md (REFI-09 / SC-5; 630 lines; 8 H2 sections: Sign Convention, Borrower NPV Formula, Discount-Rate Selection, Cashflow Inventory, Simple vs NPV Breakeven, After-Tax Mode, v1 Carve-Outs, Citations)"
  - "SC-5 verbatim phrase 'outflows negative, savings positive' surfaced 3× in §1 (headline + body paragraph + grep-receipt paragraph)"
  - "D-16 belt-and-suspenders surface 3 (the headline reference doc); cited from surfaces 1 (validator messages) + 2 (module docstring) + 4 (--help epilog)"
  - "Citations to Investopedia + Federal Reserve + CFPB + IRS Pub 936 + numpy-financial v1.0.0 + numpy-financial bug #131 + FHFA 2023 housing-finance survey (D-13 horizon-truncation context)"
  - "2 final Wave-0 stubs flipped to PASS: test_refi_npv_doc_sections_present + test_refi_npv_doc_sign_convention_phrase"
  - "Phase 6 Wave-0 closure: all 25 stubs flipped (5 + 0 + 1 + 6 + 11 + 2 = 25 net passing tests across Plans 06-01..06-06)"
affects:
  - "Phase 10 SKILL.md references/ bundle (SKLL-08): references/refi-npv.md is the second references-doc to ship (after arm-mechanics.md); progressive-disclosure pattern is now established for all future calc engines"
  - "Phase 11 SUBA-02 (refi-npv-agent multi-offer ranking): the doc enumerates the v1 carve-outs (PMI/MIP via D-10 override, pyxirr Phase 11 deferral, multi-offer comparison Phase 11 deferral) so the SUBA-02 plan-bank knows exactly which surfaces it inherits clean from Phase 6"
  - "Phase 6 closure: all SC-1..SC-5 + REFI-01..09 satisfied; phase 6/7 of plans complete in roadmap; only Plan 06-06 was outstanding before this execution"
tech-stack:
  added: []
  patterns:
    - "References-doc template inherited from references/arm-mechanics.md (Phase 5 Plan 05-05 / D-16 precedent): section-per-convention discipline + per-section citation block + appendix Citation Index table with 'Last verified' dates"
    - "Belt-and-suspenders sign-convention surfacing (D-16): 4 disjoint code/doc surfaces (validator messages + lib module docstring + references/refi-npv.md headline + --help epilog) ALL cite the same SC-5 verbatim phrase, so a grep across the codebase returns ≥4 hits and any single regression is caught by independent test surfaces"
    - "First-H2-section assertion idiom (Plan 06-06 must_haves.truths): regex-find first '^## ' header, slice text up to second '^## ' header, assert SC-5 phrase falls in that slice. Catches drift where someone moves the headline phrase to a later section and the SC-5 contract subtly weakens."
    - "Numbered-H2 section regex audit (regex `^## (\\d+)\\.\\s` extracts section numbers; assert exact match against ['1','2','3','4','5','6','7','8']) — catches insertion / deletion / re-ordering of required sections at test time"
    - "Annual citation re-validation cadence in §Appendix Citation Index — every URL has a 'Last verified' date; project policy is to re-check each calendar year and update the index if any URL has moved (mirrors arm-mechanics.md precedent)"
key-files:
  created:
    - references/refi-npv.md
    - .planning/phases/06-refinance-npv/06-06-references-doc-SUMMARY.md
  modified:
    - tests/test_refinance.py
key-decisions:
  - "Doc structure mirrors references/arm-mechanics.md exactly (section-per-convention + per-section citation block + appendix Citation Index). 06-PATTERNS §'references/refi-npv.md' specified the 7-section template; the shipped doc adds a Citations §8 + an Appendix §Citation Index for the URL-with-last-verified-date table, exactly matching arm-mechanics.md's 7-section + appendix shape. Total: 8 numbered H2 sections."
  - "SC-5 verbatim phrase 'outflows negative, savings positive' surfaced 3× in §1 (header line + opening paragraph + grep-receipt paragraph documenting all 4 D-16 surfaces). Plan 06-06 must_haves.truths required ≥1 occurrence in the first H2 section; 3 occurrences provide redundancy against accidental edits. The first-H2-section assertion test catches drift if someone moves any of the 3 occurrences to a later section."
  - "D-13 horizon-truncation rationale documented in §5.5 with FHFA 2023 housing-finance survey citation (~13yr median tenure). The departure from ROADMAP SC-1's full-horizon framing (where $5k closing at 200bps drop nets POSITIVE over 25 years) is justified at 3 places per 06-PLAN-CHECK §SC-1 caveat: (1) D-13 itself, (2) negative_npv_short_horizon.json _meta block, (3) THIS doc §5.5. SC-1 still satisfied at borrower-decision use case (12-month tenure)."
  - "D-08 PMI/MIP carve-out + D-10 caller override documented in §7.1. Caller-supplied new_loan_monthly_pi_override pattern matches Phase 4 RESEARCH Open Q#1 inheritance (caller-supplied monthly_pmi). Deferral path explicit: Phase 8 stress sweeps OR a dedicated 06-NN+1 may revisit when LTV varies systematically."
  - "noqa-promotion-on-consume hygiene pattern continued (11th project-wide occurrence): the `import re` line had `noqa: F401  (reserved for Wave 6 doc-section regex assertions)`; Plan 06-06 consumes `re` in both flipped tests via `re.findall` + `re.search`, so the noqa is no longer accurate and was promoted out. Same hygiene Plan 06-05 applied for `Callable` (10th occurrence)."
  - "First-H2-section assertion strengthens Plan 06-06 must_haves.truths beyond the literal frontmatter wording. Frontmatter said 'in the first H2 section'; the test slices text from first '^## ' to second '^## ' (or EOF) and asserts the SC-5 phrase lies in that slice. This catches a subtle drift where someone could move the phrase to §2 (Borrower NPV Formula) or later — the headline-only contract is preserved as a structural property of the doc, not just a substring presence."
requirements-completed:
  - REFI-09  # references/refi-npv.md documents sign convention explicitly (closed via doc body + 2 test flips)

# Metrics
metrics:
  duration: 5m22s
  completed: 2026-05-03
  tests_added: 2
  fixtures_added: 0
  net_files: 2  # 1 created + 1 modified
---

# Phase 6 Plan 06: References Doc Summary

Wave 6 of Phase 6 (Refinance NPV) ships `references/refi-npv.md` — the
borrower-perspective sign-convention doc that closes ROADMAP § Phase 6
SC-5 verbatim, REFI-09, and D-16 belt-and-suspenders surface 3 (the
headline reference). The doc body is what `scripts/refi_npv.py --help`
(Wave 4) and `lib/refinance.py` module docstring (Wave 1) already
pointed at; Wave 6 closes the citation loop. Plan 06-06 also flips the
final 2 Wave-0 doc stubs to PASS, completing Phase 6's Wave-0 closure
(all 25 stubs flipped: 5 + 0 + 1 + 6 + 11 + 2 = 25 net new passing
tests across Plans 06-01..06-06). Final suite: **461 passed + 4 skipped
+ 1 xfailed (inherited Phase 5 strict xfail) + 0 failed + 0 errored**.
Phase 5 baseline preserved (461 ≥ 432). Pre-commit hooks (ruff +
ruff-format + mypy on changed files) all clean.

## What Shipped

### `references/refi-npv.md` — 630 lines, 8 H2 sections + appendix

Mirror of `references/arm-mechanics.md` (Phase 5 D-16 precedent) with
section-per-convention discipline + per-section citation block +
appendix Citation Index table.

| § | Heading | Anchor / Citations |
|---|---|---|
| 1 | Sign Convention — outflows negative, savings positive | SC-5 verbatim (3× in §1); D-04; Investopedia + Federal Reserve |
| 2 | Borrower NPV Formula | Investopedia NPV; numpy-financial v1.0.0 |
| 3 | Discount-Rate Selection (D-05) | 3 plausible defaults; recommends borrower marginal opportunity cost; Investopedia + Fed |
| 4 | Cashflow Inventory: Rate-and-Term vs. Cash-Out | 2 cashflow tables; Federal Reserve + CFPB Closing Disclosure |
| 5 | Simple vs. NPV-Based Breakeven (REFI-03) | breakeven_divergence.json oracle pinned (simple=26mo, npv=28mo); D-06 (no npf.irr per bug #131); D-13 horizon-truncation rationale + FHFA 2023 |
| 6 | After-Tax Optional Mode (D-09) | RUL-11 qualified_loan_limit; IRS Pub 936; \$750k post-2017 / \$1M grandfathered; v1 carve-outs (no AMT, no state tax) |
| 7 | v1 Carve-Outs | D-08 PMI/MIP + D-10 override; D-12 closing-costs OOP; D-07 pyxirr Phase 11; competing-offer comparison Phase 11 |
| 8 | Citations | All 6 primary URLs + cross-phase internal references + D-01..D-16 cross-reference table |
| (App) | Citation Index | URL + last-verified date table for annual re-validation |

**SC-5 verbatim phrase locations** (3 occurrences in §1):
- Line 23: section header `## 1. Sign Convention — outflows negative, savings positive`
- Line 26: opening paragraph
- Line 74: grep-receipt paragraph documenting D-16 surfaces

**D-01..D-16 cross-reference table** in §8 maps every locked decision to
the section that documents it, satisfying Plan 06-06 acceptance criteria
"Cross-references Phase 6 D-01..D-16".

### `tests/test_refinance.py` — 2 stub flips (+77 / -11 lines)

| Test | What it pins |
| --- | --- |
| `test_refi_npv_doc_sections_present` | REFI_NPV_DOC_PATH exists; ≥ 250 lines (got 630); all 8 numbered H2 headers (`^## N\.`) present in order [1, 2, 3, 4, 5, 6, 7, 8] |
| `test_refi_npv_doc_sign_convention_phrase` | Literal 'outflows negative, savings positive' present anywhere AND specifically in the FIRST H2 section (slice from first `^## ` to second `^## `) per Plan 06-06 must_haves.truths |

Side hygiene: promoted `import re` out of `noqa: F401  (reserved for Wave 6
...)` — both flipped tests consume `re.findall` + `re.search` directly. 11th
project-wide noqa-promotion-on-consume occurrence (10th was Plan 06-05's
`Callable` consume).

## Test Outcomes

- **Before** (post-Plan 06-05): 459 passed + 4 skipped + 3 xfailed
- **After** (Plan 06-06): 461 passed + 4 skipped + 1 xfailed
- **Delta**: +2 passed, -2 xfailed (exact match to PLAN expectation)
- **Phase 5 baseline (≥ 432 passed)**: PRESERVED (461 ≥ 432)
- **Phase 6 Wave-0 closure**: ALL 25 STUBS FLIPPED (zero remaining Phase 6 XFAIL)
- **Inherited Phase 5 strict xfail** (test_oracle_cross_validation_5_1; deferred Phase 8+ Bankrate/Vertex42 capture): unchanged
- **Pre-commit hooks** on Task 2 commit: ruff PASSED + ruff-format PASSED + mypy PASSED (all on changed files only)
- **Pre-commit hooks** on Task 1 commit: skipped because no Python files changed in Task 1 (docs-only); ruff/mypy hooks scope to .py only

## SC-5 Closure Receipts

```
$ wc -l references/refi-npv.md
     630 references/refi-npv.md

$ grep -c 'outflows negative, savings positive' references/refi-npv.md
3

$ grep -E '^## [1-9]\.' references/refi-npv.md
## 1. Sign Convention — outflows negative, savings positive
## 2. Borrower NPV Formula
## 3. Discount-Rate Selection (D-05)
## 4. Cashflow Inventory: Rate-and-Term vs. Cash-Out
## 5. Simple vs. NPV-Based Breakeven (REFI-03)
## 6. After-Tax Optional Mode (D-09)
## 7. v1 Carve-Outs
## 8. Citations

$ grep -c 'irs.gov' references/refi-npv.md
3

$ grep -c 'numpy-financial' references/refi-npv.md
13

$ grep -c 'investopedia' references/refi-npv.md
5

$ grep -c 'federalreserve' references/refi-npv.md
6

$ grep -c 'issues/131' references/refi-npv.md
3
```

## D-16 Belt-and-Suspenders Surface Audit

The borrower-perspective sign convention surfaces at four disjoint
locations in the codebase. After Plan 06-06, all four ship live. A
grep for the verbatim SC-5 phrase returns hits at:

| # | Surface | File | Plan |
|---|---|---|---|
| 1 | RefiCashflow validator messages | `lib/refinance.py::RefiCashflow._direction_sign_consistency` (2 ValueError messages) | 06-01 |
| 2 | lib/refinance.py module docstring | `lib/refinance.py` opening paragraph | 06-01 |
| 3 | references/refi-npv.md headline | `references/refi-npv.md §1` (3 occurrences) | 06-06 (THIS PLAN) |
| 4 | scripts/refi_npv.py --help epilog | `scripts/refi_npv.py` argparse epilog | 06-04 |

Independent test surfaces guard each:
- Surface 1: `test_refi_cashflow_outflow_positive_rejected` + `test_refi_cashflow_inflow_negative_rejected` (Plan 06-01) — match validator error message substring
- Surface 2: `test_lib_refinance_module_docstring_cites` (Plan 06-01) — asserts phrase in module text
- Surface 3: `test_refi_npv_doc_sign_convention_phrase` (THIS PLAN) — asserts phrase in doc text + in first H2 section
- Surface 4: `test_cli_help_cites_sign_convention_phrase` (Plan 06-04) — asserts phrase in `--help` stdout

A regression at any single surface is caught by an independent test;
SC-5 verbatim is preserved by 4 disjoint test paths.

## Phase 6 Wave-0 Stub Closure (final scoreboard)

Plan 06-00 created 25 strict-xfail stubs. Subsequent plans flipped them:

| Wave | Plan | Stubs flipped (cumulative) | Notes |
|---|---|---|---|
| 1 | 06-01 | 5 (5 total) | RefiCashflow + sign-validator + module-docstring cite |
| 2 | 06-02 | 0 (5 total) | Empirical engine validation; no stub flips |
| 3 | 06-03 | 1 (6 total) | After-tax mode validator |
| 4 | 06-04 | 6 (12 total) | CLI smoke + envelope + --help cite + lazy import |
| 5 | 06-05 | 11 (23 total) | Fixture-driven flips (REFI-01..03/05..07 + breakeven divergence + D-03 citation coverage + D-07 pyxirr deferral) |
| 6 | 06-06 | 2 (25 total) | Doc body + sign-convention phrase (THIS PLAN) |

**25 / 25 stubs flipped. Zero remaining Phase 6 XFAIL. Phase 6 closes
clean.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Tooling] ruff format auto-applied**

- **Found during:** Task 2 ruff format check (after stub flips)
- **Issue:** ruff format reformatted the new test bodies to match project
  style (long error messages wrapped to fit line length).
- **Fix:** Accepted the auto-format. 14th project-wide occurrence of this
  hygiene-class deviation per STATE.md tracking.
- **Files modified:** tests/test_refinance.py
- **Commit:** 4bd9d6f

**2. [Rule 3 - Hygiene] noqa F401 promotion on `re` consume**

- **Found during:** Task 2 stub flips
- **Issue:** The `import re` line had `noqa: F401  (reserved for Wave 6
  doc-section regex assertions)` — Plan 06-06 IS Wave 6, and both flipped
  tests consume `re.findall` + `re.search` directly. The noqa is no longer
  accurate.
- **Fix:** Promoted `re` out of noqa. Continues the noqa-promotion-on-
  consume hygiene pattern (11th project-wide occurrence; 10th was Plan
  06-05's `Callable` consume).
- **Files modified:** tests/test_refinance.py
- **Commit:** 4bd9d6f

### Plan-Strengthening Deviations

**3. [Plan-strengthen] First-H2-section slice assertion**

- **Found during:** Task 2 acceptance-criteria interpretation
- **Issue:** Plan 06-06 frontmatter must_haves.truths says "Document
  contains literal phrase 'outflows negative, savings positive' in the
  first H2 section (SC-5 verbatim)". A naive substring assertion would
  pass if the phrase appeared ANYWHERE in the doc, missing the structural
  contract that the headline §1 owns the phrase.
- **Fix:** Strengthened `test_refi_npv_doc_sign_convention_phrase` with TWO
  assertions: (a) phrase present anywhere (substring), (b) phrase present
  specifically in the slice from first `^## ` header to second `^## `
  header (or EOF). This catches drift if anyone moves the phrase to §2 or
  later — the headline contract becomes a structural property of the doc.
- **Files modified:** tests/test_refinance.py
- **Commit:** 4bd9d6f

### Hygiene Deviations

None beyond items 1 and 2 above.

## Authentication Gates

None. Plan 06-06 has no external auth dependencies.

## Threat Flags

None. The doc adds no new code, no new endpoints, no new auth surfaces,
no new file-access patterns, and no new schema changes. The 2 test
flips read an on-disk artifact (`references/refi-npv.md`) that the
project owns.

## Deferred Issues

- **Pre-existing mypy --strict 'Source file found twice under different
  module names' baseline** (logged Plan 06-05; verified pre-existing
  before Plan 06-06; out of scope per SCOPE BOUNDARY). Pre-commit mypy
  hook is unaffected (file-level only); ran clean on tests/test_refinance.py
  for Task 2's commit. Resolution candidates remain unchanged: scripts/__init__.py,
  --explicit-package-bases, or mypy_path config. Logged in
  .planning/phases/06-refinance-npv/deferred-items.md.

## TDD Gate Compliance

Plan 06-06 is `type: execute` (not `type: tdd`), so the per-plan TDD
gate sequence (RED → GREEN → REFACTOR) does not apply. The 2 stub flips
follow the GREEN-only pattern: Wave-0 RED tests pre-exist as xfail stubs
from Plan 06-00; Plan 06-06 ships the GREEN that flips them. Phase 6
plan-level TDD discipline is preserved.

## Self-Check: PASSED

- references/refi-npv.md: FOUND (630 lines)
- tests/test_refinance.py: MODIFIED (verified via git status; 2 stubs flipped; ruff + format + mypy all PASSED)
- .planning/phases/06-refinance-npv/06-06-references-doc-SUMMARY.md: FOUND
- Commit 211c882 (Task 1: docs(06-06): add references/refi-npv.md): FOUND in git log
- Commit 4bd9d6f (Task 2: test(06-06): flip last 2 Wave-0 doc stubs): FOUND in git log
- test_refi_npv_doc_sections_present: PASSING (verified via `pytest -v`)
- test_refi_npv_doc_sign_convention_phrase: PASSING (verified via `pytest -v`)
- All 25 Phase 6 Wave-0 stubs PASSING (zero remaining Phase 6 XFAIL)
- Phase 5 baseline preserved (461 ≥ 432)
- Inherited Phase 5 strict xfail unchanged (test_oracle_cross_validation_5_1)
- Final suite: 461 passed + 4 skipped + 1 xfailed + 0 failed + 0 errored
- ruff check + ruff format clean (1 auto-format applied during execution)
- SC-5 verbatim phrase: 3 occurrences in §1 (header line 23 + opening paragraph line 26 + grep-receipt paragraph line 74)
- All 8 H2 sections present in order: [1, 2, 3, 4, 5, 6, 7, 8]
- Citations include: investopedia (5 hits) + federalreserve (6 hits) + irs.gov (3 hits) + numpy-financial bug #131 (3 hits)
- D-01..D-16 cross-reference table in §8
