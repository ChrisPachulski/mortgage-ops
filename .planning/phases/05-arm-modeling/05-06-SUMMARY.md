---
phase: 05-arm-modeling
plan: 06
subsystem: testing
tags:
  - phase-05
  - arm-modeling
  - fixtures
  - oracle-cross-validation
  - decimal-discipline
  - hand-calc-witness
  - sofr-arm
  - rule-4-deviation
  - oracle-url-rot

# Dependency graph
requires:
  - phase: 05-arm-modeling/05-00
    provides: arm_fixture loader, tests/fixtures/arm/oracle/ directory scaffold
  - phase: 05-arm-modeling/05-02
    provides: lib/arm.py model layer (ARMRequest/ARMTerms/IndexPathEntry)
  - phase: 05-arm-modeling/05-03
    provides: lib/arm.py engine (build_arm_schedule with slice-stitch architecture)
  - phase: 05-arm-modeling/05-04a
    provides: scripts/_cli_helpers.py
  - phase: 05-arm-modeling/05-04b
    provides: scripts/arm_simulate.py CLI
  - phase: 05-arm-modeling/05-05
    provides: references/arm-mechanics.md
provides:
  - 11 hand-calc ARM fixtures pinning ARM-02..05 + ARM-07 with engine-emitted Decimal-string expected values
  - 1 oracle capture pair (ABT Bank 5/6 SOFR ARM Disclosure 2022 PDF + JSON transcription)
  - 10 of 11 remaining Wave-0 stubs flipped to passing tests
  - test_oracle_cross_validation_5_6 reworked to consume the ABT Bank disclosure (substituted for AmericU after URL rot)
  - applied_cap citation-coverage meta-test (D-10) wired against the directory of fixtures
  - I-010 _request_from_fixture helper + I-004 _assert_hand_calc_check helper (test infrastructure for future ARM fixtures)
affects:
  - phase-08-stress (ARM stress paths will reuse the same fixture/oracle conventions)
  - phase-11-amortization-agent (will narrate engine output that is now fixture-pinned)
  - phase-12-fred-integration (will populate assumed_index_rate from MORTGAGE30US/SOFR feeds)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Engine-emitted hand-calc fixtures (Phase 4 D-09 idiom): fixture expected values are produced by the engine itself; the cross-source agreement test against an external oracle (ABT Bank, etc.) is the credibility anchor that makes the engine-pinned fixture honest"
    - "Hand-calc Decimal witness for cap-bound fixtures (I-004): when no external oracle covers the cap-bound path, embed a pure-Decimal hand-derivation in expected.reset_events[0].hand_calc_check that the test asserts engine output matches"
    - "_request_from_fixture(fx) helper deduplicates Loan/ARMTerms/IndexPathEntry reconstruction across fixture-based stub flips (I-010)"
    - "Oracle-substitution Rule-4 deviation pattern: when a plan-mandated source 404s, prefer a functionally equivalent published lender disclosure over deferring; document the substitution rationale in both the oracle JSON's source field and references/arm-mechanics.md"
    - "Disclosure-convention vs cash-flow-convention reconciliation: lender disclosures' 'Maximum Monthly Payment' is a regulatory worst-case computed at full original term; the engine's actual worst-case under D-05 full-remaining-term re-amortization is lower. Cross-source tests honour both conventions explicitly."

key-files:
  created:
    - tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.pdf
    - tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.json
  modified:
    - tests/test_arm.py
    - references/arm-mechanics.md

key-decisions:
  - "Rule-4-A: AmericU 5/6 SOFR ARM Disclosure URL (the plan-mandated source) returns HTTP 404 and the apex domain americu.com is parked. Substitute with ABT Bank's '5/6, 7/6 & 10/6 SOFR ARM Disclosure' — same SOFR index (30-day Average SOFR offered by FRBNY), same first-change-date (month 61), same every-6-months reset cadence, same 2/1/5 cap structure for the 5/6 product, same rounding (up to nearest 1/8 of 1%), same floor-cannot-decrease-below-margin convention. ABT URL verified live 2026-04-30 (HTTP 200, 112 KB, valid PDF). SHA256 of committed PDF: 891e70b7bc9de8a9804f53f32d1cb05488e381dd9b147bcd76d466555da2d83b. AmericU's published worked example was a 2/1/5-cap 5/6 SOFR ARM with month-61 first reset; ABT's is functionally identical."
  - "Rule-4-B: 4 browser/spreadsheet captures (Bankrate 5/1, 7/1, 10/1, Vertex42 5/1) deferred to Phase 8+. Bankrate's ARM Calculator is JavaScript-driven and Vertex42 ships an Excel template; both require human-only browser/Excel interaction not available in this session. test_oracle_cross_validation_5_1 stays xfailed with strict=True and an updated reason citing the deferral. ARM-06 closure is therefore PARTIAL at the cross-source layer — fully closed for 5/6 (ABT) and at the math/oracle layer."
  - "Disclosure-convention discovery: ABT's published 'Maximum Monthly Payment $90.54' (per $10,000 loan) is computed as the payment for a fresh $10,000 loan at the lifetime-cap rate (10.375%) over the FULL 360-month term — i.e., a regulatory worst-case showing the highest payment a borrower could theoretically face. Our engine instead re-amortizes the then-current balance over the remaining term per Phase 5 D-05, so its actual cash-flow payment at month 79 ($85.87) is lower than the disclosure figure. Cross-source agreement honours both conventions: engine matches ABT exactly under the disclosure's full-original-term convention via lib.amortize.build_schedule on a fresh fixed-rate $10k/10.375%/360mo loan."
  - "Test for the test (test_arm_mechanics_citations) updated to require a fragment present in the ABT URL (abt.bank/.../Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf) instead of the AmericU fragment (5_6-SOFR-ARM-Program-Disclosure). The forbidden-legacy guard fragments (B5-3.5-01, §4404) are unchanged — D-08 [REVISED 2026-04-30] regression guard preserved."

patterns-established:
  - "Pattern: Oracle URL rot recovery — when a plan-mandated lender disclosure URL 404s, prefer functionally equivalent substitution over deferral. Record the swap rationale in BOTH the oracle JSON's source field AND references/arm-mechanics.md. Document via Rule-4 deviation in the plan's SUMMARY."
  - "Pattern: Cross-source agreement under different conventions — when a lender disclosure publishes a regulatory worst-case (computed at full original term) but the engine produces an actual cash-flow path (re-amortized over remaining term per D-05), the cross-source test honours both conventions explicitly: assert engine matches disclosure under the disclosure's stated convention (e.g., a fresh fixed-rate loan at the cap rate) rather than forcing a single equality assertion that would silently lose information."
  - "Pattern: Browser-only captures are deferral-eligible, not implementation gaps. When automation infeasibility (JS-driven UI, spreadsheet-only template) prevents capture, queue as Phase 8+ deferred work and keep the dependent test xfailed with strict=True + a reason explicitly citing the deferral. The strict=True ensures the test doesn't silently leak XPASS if the engine path stops requiring the capture."

requirements-completed:
  - ARM-02
  - ARM-03
  - ARM-04
  - ARM-05
  - ARM-07
# ARM-06 NOTE: math/oracle layer closed (5/6 via ABT). Cross-source layer partial — Bankrate
# (5/1, 7/1, 10/1) and Vertex42 (5/1) captures deferred to Phase 8+. The cross-source 5/1
# test stays xfailed with strict=True. ARM-06 is intentionally NOT listed in
# requirements-completed because the cross-source-3-tool agreement clause is unfulfilled;
# closing it requires a future human capture session.

# Metrics
duration: 16min
completed: 2026-05-02
---

# Phase 5 Plan 06: Fixtures & Oracle Cross-Validation Summary

**11 hand-calc ARM fixtures plus ABT Bank 5/6 SOFR oracle pair land; 10 of 11 remaining Wave-0 stubs flip to passing; AmericU URL rot triggers a Rule-4 substitution; Bankrate + Vertex42 browser captures deferred to Phase 8+.**

## Performance

- **Duration:** ~16 min (resume session; Task 1 fixtures from b24e8e3 already on main)
- **Tasks completed in this resume:** 4 (ABT PDF capture, references update, ABT JSON transcription, stub flips)
- **Files modified in this resume:** 4 (2 created in tests/fixtures/arm/oracle/, 2 edited)
- **Plus Task 1 (b24e8e3, prior session):** 11 fixture JSONs + scripts/_generate_arm_fixtures.py

## Accomplishments

- 11 hand-calc fixtures shipped (engine-emitted Decimal-string expected values, with Decimal hand_calc_check witnesses on the 3 cap-bound fixtures per I-004)
- 1 oracle capture pair shipped: ABT Bank "5/6, 7/6 & 10/6 SOFR ARM Disclosure" PDF (112 KB, SHA256 891e70b7…) + JSON transcription
- 10 of 11 remaining Wave-0 xfailed stubs flipped to passing (1 stays xfailed, deferred to Phase 8+)
- test_oracle_cross_validation_5_6 reworked: uses ABT instead of AmericU; honours disclosure-convention worst-case via lib.amortize.build_schedule
- applied_cap citation-coverage meta-test (D-10) wired against tests/fixtures/arm/*.json directory walk
- _request_from_fixture, _assert_engine_matches_fixture_at_period, _assert_hand_calc_check helpers added at module top of tests/test_arm.py
- references/arm-mechanics.md AmericU citation replaced with ABT citation (Section 1 + Appendix); test_arm_mechanics_citations updated to require ABT URL fragment

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate the 11 hand-calc fixtures** - `b24e8e3` (test) — _shipped in prior session_
2. **Task 2 substitution: Capture ABT Bank PDF** - `4e87163` (chore) — _AmericU URL 404 → ABT Bank substitute curl-fetched_
3. **Task 2-followup: Update references/arm-mechanics.md AmericU → ABT** - `2870e9b` (docs)
4. **Task 3: Transcribe ABT disclosure to JSON oracle** - `0ace60f` (test)
5. **Task 4: Flip 10 of 11 Wave-0 stubs (1 deferred)** - `22f02de` (test)
6. **Task 5/Plan metadata: this SUMMARY** - _final commit_

## Files Created / Modified

### Created
- `tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.pdf` — frozen ABT Bank lender disclosure (curl-fetched 2026-04-30; SHA256 891e70b7bc9de8a9804f53f32d1cb05488e381dd9b147bcd76d466555da2d83b)
- `tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.json` — JSON transcription of disclosure's 5/6 ARM C30 column with 2 anchor rows (period 1 initial @ 5.375%/$56.00, period 79 max @ 10.375%/$90.54)
- `.planning/phases/05-arm-modeling/05-06-SUMMARY.md` — this file

### Modified
- `tests/test_arm.py` — added _request_from_fixture, _assert_engine_matches_fixture_at_period, _assert_hand_calc_check module-level helpers; flipped 10 stubs (4 ARM-02, 2 ARM-03, 1 ARM-04, 1 ARM-06 5/6, 1 ARM-07, 1 cross-cutting D-10 meta-test); kept 1 ARM-06 5/1 stub xfailed with updated Phase 8+ deferral reason; updated test_arm_mechanics_citations to require the new ABT URL fragment + docstring annotated with the Plan 05-06 substitution rationale.
- `references/arm-mechanics.md` — Section 1 "Reset Month Convention" citation block updated (AmericU URL → ABT URL); Appendix Citation Index row swapped (AmericU → ABT) with "replaced AmericU URL after 404 confirmed" note. Preserved citations: Fannie B2-1.4-02, Freddie 6302.7(b), Freddie SOFR-Indexed ARMs, CFPB §1951. Forbidden-legacy guard fragments (B5-3.5-01, §4404) unchanged.

## Decisions Made

See frontmatter `key-decisions`. Summary:

1. AmericU 5/6 SOFR oracle swapped to ABT Bank (Rule-4-A) — URL rot.
2. 4 browser/spreadsheet captures deferred to Phase 8+ (Rule-4-B) — automation infeasibility.
3. Cross-source test honours disclosure-convention worst-case explicitly (separate `lib.amortize.build_schedule` call against the lifetime-cap rate over full original term) — engine's actual D-05 cash-flow path is lower.
4. test_arm_mechanics_citations URL fragment updated to ABT-aware substring (`abt.bank/wp-content/uploads/2022/09/Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf`).

## Deviations from Plan

### Rule-4-A: AmericU 5/6 SOFR Disclosure URL Rot → ABT Bank Substitution

- **Found during:** Task 2 (oracle PDF capture)
- **Issue:** Plan 05-06's user_setup.americu.com block instructs `curl -o tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf`. The URL returns HTTP 404 (confirmed: `curl -sk -o /dev/null -w "%{http_code}\n" <url>` → 404, response size 870 bytes which is the 404 page, not a PDF). The apex domain americu.com is reachable but the WordPress upload tree no longer hosts that asset.
- **Fix:** Substituted ABT Bank's "5/6, 7/6 & 10/6 SOFR ARM Disclosure" (https://www.abt.bank/wp-content/uploads/2022/09/Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf), verified live 2026-04-30 (HTTP 200, 112 KB, valid PDF v1.6, text-extractable via pdftotext). The ABT disclosure documents a SOFR-indexed 5/6 ARM with the SAME 2/1/5 cap structure, SAME first change date (month 61), SAME every-6-months reset cadence, SAME 30-day Average SOFR index offered by FRBNY, SAME rounding (up to nearest 1/8 of 1%), and SAME floor-cannot-decrease-below-margin convention as the AmericU disclosure was being used to anchor. The substitute is functionally equivalent for the math invariant (`fully_indexed = quantize(index + margin)`, then clamp to caps + floor) that the test was meant to pin.
- **Files modified:** `tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.pdf` (new); `tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.json` (new); `references/arm-mechanics.md` (Section 1 + Appendix citation rows); `tests/test_arm.py` (test_arm_mechanics_citations URL fragment + docstring; test_oracle_cross_validation_5_6 reworked).
- **SHA256 of committed ABT PDF:** 891e70b7bc9de8a9804f53f32d1cb05488e381dd9b147bcd76d466555da2d83b
- **Verification:**
  - `file tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.pdf` → "PDF document, version 1.6 (zip deflate encoded)"
  - `pdftotext -layout` extracts the disclosure text cleanly; the 5/6 ARM C30 column has Initial Rate 5.375% / Initial Payment $56.00, Margin 3.000%, Index 1.287%, Initial Cap 2.000% / Periodic Cap 1.000% / Lifetime Cap 5.000%, Maximum Rate 10.375% / Maximum Payment $90.54, Loan Year Max Reached 7th.
  - `test_arm_mechanics_citations`, `test_arm_mechanics_doc_sections_present`, `test_arm_terms_docstring_cites_arm_mechanics` all pass.
  - `grep -c "americu" references/arm-mechanics.md` → 0; `grep -c "abt.bank" references/arm-mechanics.md` → 2.
- **Committed in:** `4e87163` (PDF fetch), `2870e9b` (doc + test edit), `0ace60f` (oracle JSON), `22f02de` (test flip).

### Rule-4-B: Bankrate + Vertex42 Browser/Spreadsheet Captures Deferred to Phase 8+

- **Found during:** Task 2 (oracle PDF capture)
- **Issue:** Plan 05-06's user_setup.bankrate.com block instructs the executor to "Browser-print 5/1 ARM scenario from https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/" (and 7/1, 10/1 variants), and user_setup.vertex42.com instructs "Download https://www.vertex42.com/ExcelTemplates/arm-calculator.html ... populate the same canonical 5/1 scenario, browser-print to PDF". Bankrate's calculator is JavaScript-driven (the per-period table is rendered client-side after the user populates the form and clicks Calculate); Vertex42 ships an Excel template that the user must download, open in Excel/LibreOffice/Numbers, populate, and re-print. Neither is automatable from this session — both are explicit `checkpoint:human-action` Type tasks per the plan's autonomy declaration.
- **Decision:** Per Phase 5 threat T-05-34 ("if URLs 404 in the future, swap-in replacement oracle is a Phase 8+ concern"), generalized to "automation-infeasible captures are also a Phase 8+ concern". The cross-source test for 5/1 (test_oracle_cross_validation_5_1, depends on Bankrate 5/1 + Vertex42 5/1) stays xfailed with `strict=True` and an updated reason explicitly citing this deferral. The 7/1 and 10/1 captures had no dedicated Wave-0 stub (the 7/1/10/1 hand-calc fixture tests are now passing without an oracle witness — they pin engine output via the engine-emitted fixture only); deferring those captures does not change the xfail count for 7/1/10/1.
- **ARM-06 closure status:** PARTIAL.
  - Closed at the math/oracle layer for 5/6 via ABT (test_oracle_cross_validation_5_6 passing).
  - Unclosed at the cross-source layer for 5/1 (test_oracle_cross_validation_5_1 still xfailed).
  - Phase 8+ backlog item (must be added to phase 8 ROADMAP / RESEARCH): "Capture 4 ARM oracle PDFs via browser/Excel and flip cross-source agreement stubs (Bankrate 5/1 + Vertex42 5/1 + Bankrate 7/1 + Bankrate 10/1)."
- **Files modified:** `tests/test_arm.py` (test_oracle_cross_validation_5_1 xfail reason updated).
- **Verification:** `pytest tests/test_arm.py::test_oracle_cross_validation_5_1 -v` reports XFAIL with the deferral reason. `grep -c "@pytest.mark.xfail" tests/test_arm.py` returns 1 (was 11 before this plan; the 1 remaining is the deferred 5/1 cross-source).
- **Committed in:** `22f02de` (test flip commit, which also reworded the 5/1 xfail reason).

### Rule-1: Disclosure-Convention vs Cash-Flow-Convention Reconciliation in 5/6 Oracle Test

- **Found during:** Task 4 (test_oracle_cross_validation_5_6 first run)
- **Issue:** Initial draft of the 5/6 cross-source test naively asserted `engine.payments[78].payment == Decimal("90.54")`, which failed because the engine produces $85.87 at month 79 under the worst-case cap-binding path. Investigation: ABT's "Maximum Monthly Payment $90.54" is computed as the payment for a fresh $10,000 loan at the lifetime-cap rate (10.375%) over the FULL 360-month term — verified independently via `numpy_financial.pmt(0.103750/12, 360, 10000)` returning -90.5388 (rounds to $90.54). The engine's $85.87 at month 79 is correct under Phase 5 D-05 (full-remaining-term re-amortization): by month 79 the loan has paid down ~$952, and re-amortizing $9047.66 over the remaining 282 months at 10.375% yields $85.87. The disclosure documents a regulatory worst-case (highest payment a borrower could theoretically face); the engine documents the actual cash-flow path. Both are correct under their respective conventions.
- **Fix:** Reworked the test to honour BOTH conventions explicitly:
  - Anchor 1: ABT's lifetime cap = ABT max rate − ABT initial rate = 5.0pp (matches our engine's 500-bps lifetime_cap_bps).
  - Anchor 2: Engine matches ABT's initial payment exactly when run with ABT's exact scenario inputs.
  - Anchor 3: Engine's worst-case rate path hits the disclosure's max rate at the disclosure-stated change date (month 79 = 4th change date, within the 7th loan year).
  - Anchor 4: Under the disclosure's full-original-term convention (a fresh fixed-rate loan at the lifetime-cap rate), `lib.amortize.build_schedule` produces exactly $90.54 — matching the disclosure exactly.
- **Files modified:** `tests/test_arm.py` (test_oracle_cross_validation_5_6 body); `tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.json` (notes field expanded with the convention reconciliation).
- **Verification:** `pytest tests/test_arm.py::test_oracle_cross_validation_5_6 -v` passes.
- **Committed in:** `22f02de`.

---

**Total deviations:** 3 (2 Rule-4 architectural + 1 Rule-1 bug discovery during test authoring).
**Impact on plan:** Both Rule-4 deviations were anticipated by Phase 5 threat T-05-34 (oracle URL/automation gaps). The Rule-1 fix tightened the cross-source test rather than weakening it (matching ABT's $90.54 EXACTLY under the disclosure's stated convention is stronger than asserting an unreachable equality at month 79). No scope creep.

## Issues Encountered

- AmericU URL 404 (resolved via Rule-4-A above)
- Bankrate + Vertex42 captures not feasible in this session (resolved via Rule-4-B deferral)
- Disclosure-convention semantic gap (resolved via Rule-1 reconciliation)

## User Setup Required

None — the AmericU `curl` step in user_setup.americu.com is now obsolete (URL 404'd); the ABT substitute is committed in-tree. The 4 deferred Bankrate/Vertex42 captures will require a human capture session in Phase 8+.

## D-10 applied_cap Coverage Matrix

| Literal value | Pinning fixture(s) |
|---|---|
| `none` | arm_5_1_payment_jump_at_61, arm_7_1_payment_jump_at_85, arm_10_1_payment_jump_at_121, arm_5_1_off_by_one_negative, arm_continuous_period_numbering, arm_5_6 (second reset), arm_index_path_overrides |
| `initial` | arm_initial_cap_at_first_reset (period 61), arm_5_6_payment_jump_at_61_and_67 (period 61) |
| `periodic` | arm_initial_cap_at_first_reset (period 73 onwards) |
| `lifetime` | arm_lifetime_cap_binds, arm_teaser_rate (engine-tested via `_make_5_1_arm_request` not fixture) |
| `floor` | arm_floor_below_margin_blocked |

`test_applied_cap_citation_coverage` walks `tests/fixtures/arm/*.json` and asserts the union of `applied_cap` values across fixture reset events covers `{"initial", "periodic", "lifetime", "floor", "none"}`. Test passes.

## ROADMAP SC Verification Matrix (Phase 5)

| SC | Pinned by | Status |
|---|---|---|
| SC-1: ARMTerms has 8 explicit fields | test_arm_terms_field_set | PASS |
| SC-2: 5/1 ARM payment-jump at month 61 | test_arm_5_1_payment_jump_at_61 | PASS |
| SC-3: Both reset-month conventions (60/61) | test_arm_5_1_payment_jump_at_61 + test_arm_5_1_off_by_one_negative | PASS |
| SC-4: Floor enforced | test_arm_floor_below_margin_blocked | PASS |
| SC-5: arm-mechanics.md cites Selling Guides + cited from ARMTerms docstring | test_arm_mechanics_doc_sections_present + test_arm_terms_docstring_cites_arm_mechanics + test_arm_mechanics_citations | PASS |

## ARM-N Requirements Closure

| Requirement | Status | Notes |
|---|---|---|
| ARM-01 | Closed (Plan 05-02) | model layer |
| ARM-02 | Closed (this plan) | 4 product fixtures (5/1, 7/1, 10/1, 5/6) |
| ARM-03 | Closed (this plan) | initial / periodic / lifetime cap fixtures |
| ARM-04 | Closed (this plan) | floor fixture |
| ARM-05 | Closed (Plan 05-03 invariants + this plan continuous-numbering fixture) | engine-tested |
| ARM-06 | **PARTIAL** (this plan) | 5/6 cross-source closed via ABT; 5/1 cross-source deferred to Phase 8+ |
| ARM-07 | Closed (this plan) | off-by-one negative fixture |
| ARM-08 | Closed (Plan 05-04b) | CLI |
| ARM-09 | Closed (Plan 05-05) | references doc |

8 of 9 requirements fully closed; ARM-06 partial (cross-source 5/1 only) pending a Phase 8+ human capture session.

## Test Counts (Plan 05-06 delta)

| | Before (after Task 1 / commit b24e8e3) | After (this resume) |
|---|---|---|
| passed | 422 | **432** |
| skipped | 4 | 4 |
| xfailed | 11 | **1** |
| failed | 0 | 0 |
| errors | 0 | 0 |

Net delta: +10 passed, −10 xfailed (1 stub remains xfailed under explicit Phase 8+ deferral).

## Phase 3 + Phase 4 Baselines

- `pytest tests/test_amortize.py -q` → **42 passed** (unchanged from Phase 3 closure)
- `pytest tests/test_affordability.py -q` → **78 passed, 4 skipped** (unchanged from Phase 4 closure)

Zero regression.

## mypy + ruff Status

- `mypy --strict tests/test_arm.py` → 0 errors
- `mypy --strict lib/arm.py` → 0 errors
- `mypy --strict scripts/_generate_arm_fixtures.py` → 0 errors
- `ruff check tests/test_arm.py references/arm-mechanics.md` → "All checks passed!"
- `ruff format --check tests/test_arm.py` → "1 file already formatted"
- Pre-commit hook ran on every commit (4e87163, 2870e9b, 0ace60f, 22f02de) — all passed.

## Phase 8+ Deferred Backlog (must propagate to Phase 8 plan)

- **Capture 4 ARM oracle PDFs via browser/Excel and flip cross-source agreement stubs:**
  - Bankrate 5/1 ARM Calculator → `tests/fixtures/arm/oracle/bankrate_5_1_capture_<year>.{pdf,json}`
  - Bankrate 7/1 ARM Calculator → `tests/fixtures/arm/oracle/bankrate_7_1_capture_<year>.{pdf,json}`
  - Bankrate 10/1 ARM Calculator → `tests/fixtures/arm/oracle/bankrate_10_1_capture_<year>.{pdf,json}`
  - Vertex42 Excel template (5/1) → `tests/fixtures/arm/oracle/vertex42_5_1_capture_<year>.{pdf,json}`
  - Flip `test_oracle_cross_validation_5_1` from xfail to passing once captures exist.
  - Add equivalent cross-source agreement tests for 7/1 and 10/1 (currently passing on engine-emitted fixture only).

## Self-Check

- File `tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.pdf`: FOUND (112 KB, PDF v1.6).
- File `tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.json`: FOUND (valid JSON, 5 required keys, 2 expected_per_period rows).
- File `references/arm-mechanics.md`: FOUND (AmericU URL replaced; ABT URL present in Section 1 + Appendix; required citation fragments preserved).
- File `tests/test_arm.py`: FOUND (1 xfail decorator remaining, was 11; _request_from_fixture defined once, used 8 times).
- Commit `4e87163`: FOUND.
- Commit `2870e9b`: FOUND.
- Commit `0ace60f`: FOUND.
- Commit `22f02de`: FOUND.

## Self-Check: PASSED

## Next Phase Readiness

- Phase 5 is **conditionally closed**: 8 of 9 ARM-N requirements fully closed; ARM-06 is partial pending Phase 8+ cross-source captures.
- ROADMAP SC-1..SC-5 all verified by passing tests.
- Phase 3 + Phase 4 baselines preserved byte-for-byte.
- Final state: 432 passed, 4 skipped, 1 xfailed (under explicit Phase 8+ deferral; strict=True ensures any future XPASS will fail loudly).
- Orchestrator may proceed to `/gsd-verify-work` for Phase 5 verification. The verifier should treat the single xfailed test as the expected residual under T-05-34 + the documented Rule-4-B deferral; the corresponding Phase 8+ backlog item is queued in this SUMMARY.

---
*Phase: 05-arm-modeling*
*Completed: 2026-05-02*
