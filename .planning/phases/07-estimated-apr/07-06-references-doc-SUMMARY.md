---
phase: 07-estimated-apr
plan: 06
subsystem: references-doc
tags:
  - phase-07
  - estimated-apr
  - references
  - documentation
  - apr-08
  - sc-5

# Dependency graph
requires:
  - phase: 05-arm-modeling
    provides: "references/arm-mechanics.md six-section template (D-28 inheritance) + ARMTerms.__doc__ cite-from idiom (D-29 mirror pattern)"
  - phase: 06-refinance-npv
    provides: "references/refi-npv.md sectioned-reference-doc + citation-index-appendix idiom (D-16 belt-and-suspenders surfaces analog)"
  - phase: 07-estimated-apr (Plan 07-01)
    provides: "APRRequest boundary model — Task 2 extends its existing __doc__ to cite the new references doc per D-29"
  - phase: 07-estimated-apr (Plan 07-05)
    provides: "tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json (SC-1 anchor) — references doc §4 Worked Example cites this fixture as the canonical regulatory anchor"
  - phase: 07-estimated-apr (Plan 07-00)
    provides: "13 Wave-0 xfail-strict stubs in tests/test_apr.py — this wave flips the 12th stub (test_references_apr_reg_z_doc_present_with_required_sections / APR-08); only APR-04 (Wave 7) remains xfail"
provides:
  - "references/apr-reg-z.md (523 lines; 6 required sections + Citation Index appendix; D-28 mirror of references/arm-mechanics.md template)"
  - "lib.apr.APRRequest.__doc__ extended with explicit ROADMAP SC-5 / D-29 cite-from contract reference (Phase 5 ARMTerms parallel)"
  - "Wave-0 stub test_references_apr_reg_z_doc_present_with_required_sections flipped to PASS — asserts (a) doc exists; (b) all 6 required section headers present; (c) lib/apr.py contains 'references/apr-reg-z.md' literal string (D-29 cite-from contract)"
  - "APR-08 closed; 12 of 13 Wave-0 stubs flipped (only APR-04 / Wave 7 stays xfail)"
affects:
  - 07-07-ffiec-fixtures (Wave 7 / Plan 07-07 will close APR-04 by capturing 20+ HMDA Platform oracle fixtures; references doc §6 already documents the HMDA Platform sole-oracle decision per D-01 / D-02 from 07-CONTEXT.md, so Wave 7 has no doc edits to do)
  - 10-claude-skill (Phase 10 bundles references/apr-reg-z.md into .claude/skills/mortgage-ops/references/ per project convention; the file ships ready-to-bundle)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-28 LOCKED: Phase 7 references doc mirrors references/arm-mechanics.md six-section template (Phase 5 D-08 precedent). Section headers exact-match-pinned by the test grep — section reordering or header-text changes require plan revision."
    - "D-29 LOCKED: cite-from contract (lib.apr.APRRequest.__doc__ cites references/apr-reg-z.md). Mirrors Phase 5 ARMTerms.__doc__ → references/arm-mechanics.md cite-from idiom + Phase 6 D-16 belt-and-suspenders multi-surface idiom."
    - "D-30 LOCKED: all citation URLs verified against eCFR / CFPB / numpy_financial / GitHub on 2026-05-02 (per 07-RESEARCH §Citations). Annual re-verification cadence (Phase 2 staleness convention inheritance)."
    - "Citation Index appendix table: URL × section-anchor × last-verified-date triplets. Phase 6 references/refi-npv.md §Appendix shape verbatim — gives downstream re-verifiers a single table to walk for annual cadence."
    - "Existing module-docstring + field-description citations (lines 31, 52, 110, 668 of lib/apr.py) preserved unchanged; the new APRRequest docstring text is the authoritative SC-5 cite-from surface, the 4 pre-existing references are non-load-bearing reinforcers."

key-files:
  created:
    - references/apr-reg-z.md
  modified:
    - lib/apr.py
    - tests/test_apr.py

key-decisions:
  - "D-28 honored verbatim: 6-section template Unit-Period Model / Day-Count Conventions / Odd First Period Handling / Worked Example / Newton-Raphson Convergence / Citations Summary; section headers match the Wave-0 stub's required_sections list character-for-character (exact prefix; the test uses 'in' substring search but the prefixes are unambiguous)."
  - "D-29 honored: APRRequest.__doc__ extended from 'See `references/apr-reg-z.md` for the unit-period model + day-count conventions.' → 'See `references/apr-reg-z.md` for the unit-period model, day-count conventions, odd-first-period handling, and Newton-Raphson convergence details with regulatory citations (ROADMAP SC-5 / D-29 cite-from contract).' Names all 4 doc scopes + the SC-5 anchor explicitly (mirrors Phase 5 ARMTerms.__doc__ pattern)."
  - "D-30 honored: 11 URLs cited (eCFR Reg Z Part 1026 Appendix J + §1026.4 / §1026.17 / §1026.18 / §1026.22; CFPB TILA-RESPA Compliance Guide; FFIEC APRWIN; CFPB Rate Spread Calculator; HMDA Platform; numpy_financial.rate docs; numpy_financial issue #131); each tagged 'verified 2026-05-02' in §6 prose AND in the Citation Index appendix table."
  - "Worked example (§4) anchors to the SC-1 fixture tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json (D-25 LOCKED regulatory value 0.120000 from Plan 07-05). Documents the engine-vs-regulatory delta (engine 0.119994; |diff| = 0.000006 < tolerance 0.00001) explicitly, so a future reader sees why the fixture pins the regulatory value not the engine value."
  - "Doc length 523 lines (>= 250 min per plan must_haves.artifacts) — matches refi-npv.md (630 lines) order of magnitude; arm-mechanics.md (196 lines) was the original D-28 template but the Phase 7 doc is necessarily longer because the U-equation algebra + day-count + odd-first-period + Newton convergence each merit a substantive section."
  - "Locked-decision cross-reference table (§6 final subsection) lists 11 D-NN cross-refs from 07-CONTEXT.md + plan 07-06 frontmatter; mirrors Phase 6 references/refi-npv.md §8 D-01..D-16 cross-reference table verbatim (idiom inheritance)."

patterns-established:
  - "Plan 07-06 establishes the Phase 7 references doc as the third sibling in references/*.md (after arm-mechanics.md from Phase 5 and refi-npv.md from Phase 6). Future phases adding reference docs (Phase 8 stress-points may add references/stress-paths.md) follow the same six-section + Citation Index appendix template."
  - "D-29 cite-from contract test: the Wave-0 stub asserts both (a) doc presence with required section headers AND (b) cite-from string presence in lib/apr.py. This is a stronger contract than Phase 5's ARMTerms cite-from (which is documentary only); the test fails loudly if either side of the cite-from contract drifts."
  - "Citation Index appendix table per refi-npv.md §Appendix is now the standard tail of every references/*.md (ARM doc has its own §Appendix; Refi doc has §Appendix; Phase 7 doc has §Appendix). Annual re-verifier walks one table per doc."
  - "Reduced-line-count convention: the doc body uses prose with citation parentheticals AND a final §6 Citations Summary that aggregates URLs by category (regulatory / CFPB / library) + the §Appendix that re-tabulates with last-verified dates. Three layers of citation discipline: inline parenthetical → §6 categorized list → §Appendix verifier table."

requirements-completed:
  - APR-08  # references/apr-reg-z.md unit-period model + day-count conventions documentation shipped + lib.apr cite-from contract + Wave-0 stub flipped to PASS

# Metrics
duration: 4min 51s
completed: 2026-05-03
---

# Phase 7 Plan 6: References Doc Summary

**Phase 7 Wave 6 ships `references/apr-reg-z.md` (523 lines; six required sections per D-28 LOCKED — Unit-Period Model, Day-Count Conventions, Odd First Period Handling, Worked Example, Newton-Raphson Convergence, Citations Summary — plus a Citation Index appendix per D-30 verifier-table idiom inherited from Phase 6 `references/refi-npv.md`); extends `lib.apr.APRRequest.__doc__` with the explicit ROADMAP SC-5 / D-29 cite-from contract (mirrors Phase 5 `ARMTerms.__doc__` → `references/arm-mechanics.md` idiom; names all four doc scopes — unit-period model, day-count, odd-first-period, Newton-Raphson — instead of the prior abbreviated "unit-period model + day-count conventions" only); flips the 12th of 13 Wave-0 xfail stubs (`test_references_apr_reg_z_doc_present_with_required_sections` — APR-08) by replacing the placeholder with assertions that (a) the doc file exists at repo root, (b) all six required section headers are present, (c) `lib/apr.py` contains the literal string `references/apr-reg-z.md` per D-29. Suite 482 passed / 4 skipped / 2 xfailed (was 481/4/3; +1 net pass corresponding to the APR-08 stub flip; -1 xfail; only APR-04 / Wave 7 stub remains xfail). APR-08 closed; SC-5 closed.**

## Performance

- **Duration:** 4 min 51 s
- **Started:** 2026-05-03T21:17:27Z
- **Completed:** 2026-05-03T21:22:18Z
- **Tasks:** 3 atomic commits (1:1 with plan tasks)
- **Files created:** 1 (`references/apr-reg-z.md`, 523 lines)
- **Files modified:** 2 (`lib/apr.py` — APRRequest docstring extension, 8 lines net; `tests/test_apr.py` — Wave-0 stub flip, 31 lines net)

## Accomplishments

- **Shipped `references/apr-reg-z.md`** (523 lines) with the six required sections per D-28 LOCKED template inheritance from `references/arm-mechanics.md`:
  - **§1 Unit-Period Model (12 CFR Part 1026 Appendix J)** — the "U-equation" with full symbol table, collapse-to-PV case for regular monthly mortgages, multi-advance / irregular-schedule generalization note, and `_unit_period_equation` / `_derivative` engine-surface pointers.
  - **§2 Day-Count Conventions** — three v1-supported conventions (`30/360` / `actual/365` / `actual/actual`) with unit-period-days table; v1 cross-validation scope (30/360 only); D-18 "small differences" non-treatment note; cited against §1026.17(c)(4) + Appendix J §(b)(5)(iii).
  - **§3 Odd First Period Handling (§1026.17(c)(4))** — long case `f ∈ [0, 1)` (positive `f`) with day-count-specific formulas; engine surfaces (`_compute_odd_first_period_fraction` helper + `odd_first_period_days` user shortcut per D-15 / D-17); negative-`f` short case (engine accepts; v1 fixtures don't cover); long-long case `f >= 1` rejected at boundary per D-16 with the 45-day negative-path fixture cite.
  - **§4 Worked Example — Reg Z Appendix J Example J(c)(1)** — full SC-1 anchor walkthrough ($5,000 / 36 / $166.07 → 12.00%); Newton iteration table (1 iteration); engine-vs-regulatory delta documented (engine 0.119994; |diff| = 0.000006 < tolerance 0.00001); D-25 LOCKED rationale for pinning the regulatory value not the engine value.
  - **§5 Newton-Raphson Convergence** — algorithm + seed strategy (D-02 / APR-02; `npf.rate` with NaN/out-of-range fallback); tolerance reconciliation (Decimal("0.00001") is 125x tighter than Reg Z §1026.22(a)(2) regular tolerance per RESEARCH §Finding 1); D-06 dual-criterion convergence test (rate tolerance AND dollar residual); D-07 / SC-3 50-iteration cap with `APRConvergenceError`; Decimal-vs-float discipline + `_decimal_pow` helper + sanity guard.
  - **§6 Citations Summary (verified 2026-05-02)** — 11 URLs categorized into Primary regulatory / CFPB explainer + tool oracles / Library + tooling / Cross-phase internal references; Phase 7 LOCKED DECISIONS cross-reference table mapping D-NN to in-doc sections (Phase 6 §8 idiom inheritance).
  - **Appendix — Citation Index** — 11-row URL × section-anchor × last-verified-date table for the annual re-verification cadence (Phase 2 staleness convention; Phase 6 §Appendix idiom inheritance).
- **Extended `lib.apr.APRRequest.__doc__`** to make the D-29 cite-from contract explicit. Before: `"See \`references/apr-reg-z.md\` for the unit-period model + day-count conventions."` After: `"See \`references/apr-reg-z.md\` for the unit-period model, day-count conventions, odd-first-period handling, and Newton-Raphson convergence details with regulatory citations (ROADMAP SC-5 / D-29 cite-from contract)."` — names all 4 doc scopes + the SC-5 anchor explicitly (mirrors Phase 5 ARMTerms pattern).
- **Flipped the 12th of 13 Wave-0 stubs** — `test_references_apr_reg_z_doc_present_with_required_sections` (APR-08) now asserts (a) `references/apr-reg-z.md` exists at repo root, (b) all 6 required section headers are present (`## 1. Unit-Period Model`, `## 2. Day-Count Conventions`, `## 3. Odd First Period Handling`, `## 4. Worked Example`, `## 5. Newton-Raphson Convergence`, `## 6. Citations Summary` — exact-prefix substring match), (c) `lib/apr.py` contains the literal string `"references/apr-reg-z.md"` (D-29 cite-from contract). Only APR-04 / Wave 7 stub remains xfail in `tests/test_apr.py`.
- **Suite count after:** 482 passed (was 481; +1 net pass exactly for the flipped APR-08 stub) / 4 skipped (unchanged) / 2 xfailed (was 3; -1 corresponding to the APR-08 flip) / 0 failed / 0 errors. Zero regression to Plan 07-05 baseline.
- **`tests/test_apr.py` + `lib/apr.py` mypy --strict + ruff check + ruff format --check** all clean post-commit.

## Task Commits

Each task committed atomically against `main` (sequential executor; no branching per `parallelization=false`; no AI attribution per global + project CLAUDE.md):

1. **Task 1: Create `references/apr-reg-z.md`** — `0252f04` (docs)
2. **Task 2: Extend `APRRequest.__doc__` cite-from references doc** — `53bd299` (docs)
3. **Task 3: Flip Wave-0 APR-08 stub** — `a886bea` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `references/apr-reg-z.md` (**created**, 523 lines) — Phase 7 reference doc; 6 required sections + Citation Index appendix; mirrors `references/arm-mechanics.md` template per D-28 LOCKED.
- `lib/apr.py` (**modified**, 5 inserts / 3 deletes around APRRequest docstring) — explicit ROADMAP SC-5 / D-29 cite-from contract reference; names all 4 doc scopes (unit-period model, day-count, odd-first-period, Newton-Raphson).
- `tests/test_apr.py` (**modified**, 34 inserts / 3 deletes around test_references_apr_reg_z_doc_present_with_required_sections) — Wave-0 stub flipped from `pytest.fail("Wave 0 stub")` placeholder to real assertions on doc presence + section headers + cite-from contract.

## Acceptance Gate Verification

| Gate                                                                                          | Plan target                                                | Actual                                              | Status |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------|------------------------------------------------------|--------|
| `ls -la references/apr-reg-z.md`                                                              | file exists                                                | present (25,914 bytes)                              | PASS   |
| `wc -l references/apr-reg-z.md`                                                               | >= 250 lines                                               | 523 lines                                            | PASS   |
| All 6 required section headers present                                                         | 6/6 (## 1. Unit-Period Model ... ## 6. Citations Summary)  | 6/6 (verified via grep)                              | PASS   |
| `grep -c 'references/apr-reg-z.md' lib/apr.py`                                                 | >= 1                                                       | 5 (line 31, 52, 110, 465, 668)                       | PASS   |
| `pytest tests/test_apr.py::test_references_apr_reg_z_doc_present_with_required_sections -v`   | PASS                                                       | PASS                                                 | PASS   |
| `pytest tests/test_apr.py -v --tb=no`                                                         | 17 PASS / 1 xfailed (APR-04 only)                          | 17 PASS / 1 xfailed (APR-04)                         | PASS   |
| Stubs flipped (cumulative)                                                                     | 12 of 13 (APR-04 stays xfail until Wave 7)                 | 12 of 13 (1 xfail in test_apr.py = APR-04 exactly)   | PASS   |
| Full-suite `pytest -q`                                                                         | >= 461 floor + 1 new pass (482 from 481 baseline)          | 482 passed / 4 skipped / 2 xfailed / 0 failed        | PASS   |
| `mypy --strict tests/test_apr.py`                                                              | clean                                                      | clean                                                | PASS   |
| `mypy --strict lib/apr.py`                                                                     | clean                                                      | clean                                                | PASS   |
| `ruff check lib/apr.py tests/test_apr.py`                                                      | clean                                                      | clean                                                | PASS   |
| `ruff format --check lib/apr.py tests/test_apr.py`                                             | clean                                                      | "1 file already formatted" each                       | PASS   |

## Decisions Made

Followed the plan's 3 LOCKED DECISIONS (D-28..D-30) verbatim:

- **D-28 (six-section template inheritance from `references/arm-mechanics.md`):** Honored. The 6 section headers character-for-character match the Wave-0 stub's `required_sections` list (`## 1. Unit-Period Model`, `## 2. Day-Count Conventions`, `## 3. Odd First Period Handling`, `## 4. Worked Example`, `## 5. Newton-Raphson Convergence`, `## 6. Citations Summary`). The test uses substring `in content` matching; the headers are unambiguous prefix-matches against the actual doc lines (which include parenthetical regulation cites: `## 1. Unit-Period Model (12 CFR Part 1026 Appendix J)`, etc.).
- **D-29 (cite-from contract pinned by lib/apr.py grep + APRRequest.__doc__ explicit reference):** Honored. The Wave-0 stub asserts `"references/apr-reg-z.md" in apr_module` (5 hits in current `lib/apr.py`: line 31 module docstring APR-08 entry; line 52 D-04 finance_charges note; line 110 D-18 small-differences note; line 465 — newly extended APRRequest docstring per Task 2; line 668 — `_unit_period_equation` references doc §5). The APRRequest docstring (line 465) is the authoritative SC-5 surface; the others are non-load-bearing reinforcers.
- **D-30 (citation URLs verified 2026-05-02 against eCFR + CFPB):** Honored. All 11 URLs in the Citation Index appendix tagged "2026-05-02"; matches RESEARCH §Citations verification batch. Annual re-verification cadence pointer in the §Appendix tail.

## Deviations from Plan

None — plan executed exactly as written.

The plan's `must_haves.truths` and `must_haves.artifacts` all PASS without inline fixes:

- truth 1: `references/apr-reg-z.md` exists with all 6 sections (cite-from contract, unit-period model, day-count, worked example, Newton convergence, citations) → PASS (note: the plan's truth-list says "cite-from contract" as a section but the actual locked test assertions are §1..§6 unit-period through citations; cite-from contract is a documentary phrase in the doc preface and the reciprocal SC-5 / D-29 layer in `lib.apr.APRRequest.__doc__` — the doc preface mentions it explicitly).
- truth 2: `lib.apr.APRRequest` docstring cites `references/apr-reg-z.md` (mirrors Phase 5 `ARMTerms.__doc__`) → PASS (the docstring already cited the doc per Wave 1; Task 2 explicitly named all 4 scopes + ROADMAP SC-5 anchor for symmetry with the Phase 5 pattern).
- truth 3: Wave 0 stub `test_references_apr_reg_z_doc_present_with_required_sections` flips to PASS → PASS.
- truth 4: All citation URLs verified against eCFR / CFPB on 2026-05-02 per RESEARCH §Citations → PASS (D-30 pinned in §6 prose + Appendix table).
- artifact 1: `references/apr-reg-z.md` ≥ 250 lines → PASS (523 lines).
- artifact 2: `lib/apr.py` modification: `APRRequest` docstring extended with "See `references/apr-reg-z.md` ..." citation → PASS (Task 2 commit `53bd299`).

## Issues Encountered

None — all 3 task commits executed sequentially, no checkpoints, no escalations, no auth gates, no blocking errors.

## Threat Flags

None — Plan 07-06 ships 1 read-only Markdown reference doc + 1 docstring-only edit to `lib/apr.py` + 1 test-file edit. No new code paths, no network surface, no auth boundary, no schema changes at trust boundaries, no new third-party dependencies, no untracked file generation. The references doc is loaded on demand by future Phase 10 skill consumers (progressive disclosure per CLAUDE.md "Skill portability" convention) and by the Wave-0 stub's test grep; both are read-only consumers.

## Known Stubs

None introduced this wave. The pre-existing inline-stub status (3 inline-constructed-input tests carried forward from Plan 07-04 SUMMARY's "Known Stubs" list) is unchanged; those are hygiene-only refactors and were explicitly not in this plan's scope.

The remaining xfail stub in `tests/test_apr.py` is `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` (APR-04 / Plan 07-07 / Wave 7 — HMDA Platform fixture capture). 12 of 13 Wave-0 stubs flipped (only APR-04 stays xfail).

No mock/placeholder data introduced. No `FIXME` comments. No hardcoded empty values.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture, no human-in-the-loop verification. All 3 tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

- **Wave 7 (Plan 07-07 HMDA Platform fixtures)** — unblocked. The references doc §6 Citations Summary already documents the HMDA Platform sole-oracle decision per CONTEXT D-01 and the FFIEC-out-of-scope decision per D-02; Wave 7 has no doc edits to do. APR-04 closes when 20+ HMDA Platform oracle fixtures ship + `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` flips to a parametric over the new fixture corpus.
- **Phase 8 (stress-points)** — `solve_apr` continues to be the integration point for stress wrappers. Phase 8 Newton-iteration consumers may surface debug logging via the doc's §5 reference-section pointer; no doc edits required from Phase 8 unless a new Newton-convergence pathology is discovered.
- **Phase 10 (Claude skill)** — `references/apr-reg-z.md` ships ready-to-bundle into `.claude/skills/mortgage-ops/references/`. The cite-from contract from `lib.apr.APRRequest.__doc__` will continue to point at `references/apr-reg-z.md` (relative-path); the Phase 10 relocation maintains relative-path semantics inside the skill folder. No Phase 10 work required from this plan.
- **Requirement closure status:** Plan 07-06 closes **APR-08** (references/apr-reg-z.md unit-period model + day-count conventions documentation shipped + lib.apr cite-from contract + Wave-0 stub flipped to PASS). Remaining Phase 7 requirement: **APR-04** in Wave 7 (HMDA Platform fixtures).

## TDD Gate Compliance

The plan does not declare `type: tdd`; this is a vanilla `type: execute` plan. Per the executor protocol's TDD section, no RED/GREEN/REFACTOR cycle gate enforcement is required. For traceability: the stub flip in Task 3 is a RED → GREEN transition of the pre-existing Wave-0 xfail stub. The flip removes the `@pytest.mark.xfail(strict=True)` decorator (the RED gate marker per Wave-0's stub-then-flip pattern) and replaces the `pytest.fail("Wave 0 stub")` body with real assertions that PASS against the doc + cite-from surfaces shipped in Tasks 1-2 (the GREEN gate). No REFACTOR pass needed — the test as written is canonical against ruff format.

## Self-Check: PASSED

Verified at execution end:

- [x] `references/apr-reg-z.md` exists at the path declared in plan frontmatter (`files_modified: references/apr-reg-z.md`):
  - `references/apr-reg-z.md` — present (523 lines, 25,914 bytes)
- [x] `lib/apr.py` modified — APRRequest docstring extended (line 465 now says `"See \`references/apr-reg-z.md\` for the unit-period model, day-count conventions, odd-first-period handling, and Newton-Raphson convergence details with regulatory citations (ROADMAP SC-5 / D-29 cite-from contract)."` per `git diff` of commit `53bd299`)
- [x] `tests/test_apr.py` modified — Wave-0 APR-08 stub flipped (no `@pytest.mark.xfail(strict=True)` on `test_references_apr_reg_z_doc_present_with_required_sections`; body replaced with real assertions per `git diff` of commit `a886bea`)
- [x] `git log --oneline | grep 0252f04` (Task 1 references doc) → present
- [x] `git log --oneline | grep 53bd299` (Task 2 APRRequest docstring extension) → present
- [x] `git log --oneline | grep a886bea` (Task 3 Wave-0 stub flip) → present
- [x] All three task commits reachable from `main`
- [x] No commit message contains "Co-Authored-By", "Claude", "Generated with", or any AI attribution (verified by inspection of all 3 messages — solely-authored as repo owner per global + project CLAUDE.md)
- [x] All plan acceptance gates PASS (see Acceptance Gate Verification table above)
- [x] `pytest tests/test_apr.py::test_references_apr_reg_z_doc_present_with_required_sections -v` → PASS
- [x] Full apr suite: 17 passed / 1 xfailed (APR-04 only); was 16/2 pre-Wave-6
- [x] Full project suite: 482 passed / 4 skipped / 2 xfailed / 0 failed / 0 errors (was 481+4+3; +1 net pass / -1 xfail; zero regression to Plan 07-05 baseline of 481)
- [x] mypy --strict + ruff check + ruff format --check all clean on `lib/apr.py` and `tests/test_apr.py`
- [x] APR-08 closes per `requirements-completed` frontmatter (verified via the Wave-0 stub flip end-to-end through doc-presence + section-headers + lib/apr.py cite-from)
- [x] 12 of 13 Wave-0 stubs flipped (verified: only 1 xfail remains in `tests/test_apr.py` — `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` [APR-04 / Wave 7])
- [x] All 11 citation URLs in `references/apr-reg-z.md` Citation Index appendix tagged "2026-05-02" (D-30 honored)

---
*Phase: 07-estimated-apr*
*Completed: 2026-05-03*
