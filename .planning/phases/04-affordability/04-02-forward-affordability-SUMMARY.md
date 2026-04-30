---
phase: 04-affordability
plan: 02
subsystem: affordability

tags: [phase-4, affordability, forward, dti, ltv, cltv, piti, wave-2, evaluate-forward]

requires:
  - phase: 01-foundation
    provides: lib/models.py Loan/Money/Rate aliases (condecimal max_digits=14, decimal_places=2 + max_digits=7, decimal_places=6); lib/money.py quantize_cents single source of truth (ROUND_HALF_UP, called once end-of-period)
  - phase: 02-regulatory-reference-data-rules-predicates
    provides: lib/rules/loan_type.py classify(loan_amount, county, program=) with MissingCountyDataError loud-fail; lib/rules/fha_mip.py compute(loan, original_property_value, endorsement_date) -> MIPResult; lib/rules/conventional_pmi.py LTV_REQUEST_ELIGIBLE statutory constant; lib/rules/_loader.py StaleReferenceWarning for staleness propagation; lib/rules/types.py County construction
  - phase: 03-core-amortization
    provides: lib/amortize.py build_schedule(Loan) -> Schedule.monthly_pi (numpy-financial wrapping); D-04 PITFALLS pattern (single quantize at end-of-period, never per-component)
  - phase: 04-affordability
    provides: 04-01 Wave 1 lib/affordability.py Pydantic v2 type contract with TARGET_LOAN_TYPE_CROSSWALK + TARGET_LOAN_TYPE_TO_PROGRAM cross-walks + 18 LOCKED DECISION docstring blocks + cross-plan stubs for evaluate_forward / evaluate_reverse

provides:
  - lib/affordability.py extended with evaluate_forward implementation body (replaces Plan 04-01 NotImplementedError stub)
  - Private helpers _compute_dti / _compute_ltv / _compute_cltv / _classify_target_loan_type / _compute_monthly_mi / _build_loan_for_amortization / _build_county
  - USDA_ANNUAL_FEE_RATE = Decimal("0.0035") statutory constant
  - _LOAN_TYPE_BLOCKER_PREFIX citation prefix table (FHFA-LIMIT-CONFORMING / HUD-LIMIT-FHA / VA-LIMIT / USDA-LIMIT / FHFA-LIMIT-JUMBO)
  - Stable evaluate_forward(req) -> AffordabilityResponse contract for Phase 5 ARM + Phase 8 stress consumers

affects: [04-03-reverse-affordability, 04-04-blocker-precedence, 04-05-cli-and-config, 04-06-tests-and-fixtures, 05-arm, 08-stress]

tech-stack:
  added: []  # Pure composition over Phase 1/2/3 surface; no new runtime deps
  patterns:
    - "Two-step UFMIP financing for FHA: pre-finance fha_mip_compute call to get UFMIP -> financed_loan_amount = loan_amount + UFMIP -> build_schedule on financed_loan -> monthly_pi from financed amount. Inline rather than recursive _compute_monthly_mi for clarity. Reusable for any future plan that auto-finances upfront fees (VA funding fee in v2; USDA upfront guarantee fee if added)."
    - "Single-quantize PITI composition: piti_pre_quantize = monthly_pi + tax + ins + hoa + monthly_mi computed at full Decimal precision, quantize_cents called ONCE at end. Never quantize mid-calculation (Phase 3 D-04 PITFALLS pattern). Reusable for any future composition of money components into a single output."
    - "Predicate signature drift handled at composition boundary: lib/affordability.py reconciles CONTEXT.md D-02 vs RESEARCH §A.1-A.3 corrected signatures. lib.rules.loan_type.classify() called with program= kwarg derived from TARGET_LOAN_TYPE_TO_PROGRAM cross-walk; lib.rules.fha_mip.compute() called with (loan, original_property_value, endorsement_date) tuple; lib.rules.conventional_pmi.LTV_REQUEST_ELIGIBLE statutory constant consumed directly (status() not called for the Phase 4 affordability surface because it returns a TERMINATION enum not a 'needs PMI' boolean). Reusable for any future plan composing predicates whose CONTEXT.md descriptions drift from on-disk signatures: pin the corrected calls at the composition boundary, document with RESEARCH §-citation comments inline."
    - "Replace stub-presence test with positive behavior test when stub body lands: test_evaluate_forward_is_cross_plan_stub asserted NotImplementedError on the Plan 04-01 stub; Plan 04-02 replaces it with test_evaluate_forward_returns_response_for_valid_request that exercises the conforming oracle ($400k @ 6.5%/30yr -> $2528.27 monthly_pi). Mirrors Phase 2 02-02 pattern (REMOVED test_fha_program_raises_not_implemented_until_ref_02_lands and ADDED 4 positive FHA tests) and is the canonical RED->GREEN flip for cross-plan stub tests when the stub body ships."

key-files:
  created: []
  modified:
    - lib/affordability.py (+340 lines: imports + USDA constant + _LOAN_TYPE_BLOCKER_PREFIX + 7 private helpers + full evaluate_forward body)
    - tests/test_affordability.py (+45 / -7 lines: replaced test_evaluate_forward_is_cross_plan_stub with test_evaluate_forward_returns_response_for_valid_request positive behavior test)

key-decisions:
  - "Two-step UFMIP-then-build_schedule sequence for FHA target. Plan author noted the sequencing concern in the action body ('_compute_monthly_mi takes financed_loan_amount; for FHA we need a two-step compute (UFMIP first -> financed_amount -> monthly MIP from financed_amount). Inline the FHA branch here for clarity.'). Implementation: when target_loan_type=='fha', a pre-financing fha_mip_compute call returns ufmip; financed_loan_amount = loan_amount + ufmip; build_schedule runs on the financed amount; THEN _compute_monthly_mi is called with financed_loan_amount to produce monthly_mi (which uses fha_mip_compute again under the hood, but on the financed loan). The pre-MIP call is harmless duplicate work because lib.rules._loader caches via @lru_cache. Reusable pattern for any future scenario where UFMIP/upfront-fee financing changes the principal that downstream amortization needs to consume."
  - "Replace test_evaluate_forward_is_cross_plan_stub with positive behavior test as Rule-1 deviation in Task 2 commit. The Plan 04-01 test asserted that evaluate_forward(None) raises NotImplementedError citing 'Plan 04-02'. Once Plan 04-02 ships the body, that test becomes invalid. Mirrors Phase 2 02-02 pattern of REMOVING the stub-presence test and ADDING positive tests when the stub body lands. The test was renamed to test_evaluate_forward_returns_response_for_valid_request and exercises the $400k @ 6.5%/30yr conforming oracle to verify the monthly_pi=$2528.27 + ltv=0.80 + loan_type='conforming' contract."
  - "Phase 4's evaluate_forward leaves blocked / blocked_by reflecting ONLY the loan-type-classify step-1 blocker. Plan 04-04 wraps evaluate_forward with the rest of the D-11 precedence pipeline (LTV/CLTV ceiling -> DTI cap -> ATR/QM -> VA-residual) and mutates a NEW response via model_copy. This split keeps evaluate_forward focused on math and Plan 04-04 focused on regulatory blocker precedence. The split is documented in the evaluate_forward docstring step 12 + the function body's comment block + the 'Coupling note for Plan 04-04' in the plan's action body."
  - "Re-add imports stripped by ruff in Task 1 commit. Task 1 specified `import warnings`, `from lib.amortize import build_schedule`, `from lib.rules._loader import StaleReferenceWarning` to be added at module top — but they were not used by the helpers committed in Task 1, so ruff F401 fired and removed them. Task 2's body needs all three (warnings.catch_warnings, build_schedule call, StaleReferenceWarning subclass check). Re-added in Task 2 as a Rule-3 deviation. Documented as a project pattern: when a multi-task plan stages imports in an early task whose body doesn't yet use them, ruff F401 will strip them; re-add at the task that uses them, or pre-cite # noqa: F401 with a Plan-NN-YY-needs-this rationale comment."

patterns-established:
  - "evaluate_forward as a 7-step composition pipeline: (1) joint income sum + monthly debts; (2) County construction from FIPS; (3) loan-type classify with corrected signature + cross-walk acceptance check; (4) UFMIP financing (FHA D-03 auto-finance); (5) build_schedule on financed_loan -> monthly_pi; (6) _compute_monthly_mi on financed_loan_amount; (7) PITI single-quantize + LTV/CLTV at financed_loan_amount + DTI front/back at full Decimal precision. Phase 5 ARM, Phase 6 refi, Phase 8 stress all consume this pipeline; the contract is locked at the 17-field AffordabilityResponse output."
  - "Predicate-signature reconciliation at composition boundary: every `lib/rules/*` predicate consumed in lib/affordability.py is called with the on-disk signature (RESEARCH §A.1-A.3) NOT the CONTEXT.md description. Inline RESEARCH §-citation comments document the drift. Negative grep gates (`! grep -E 'conventional_pmi.status(ltv_pct'`, `! grep -E 'fha_mip.compute(loan_amount, ltv_pct, term_months)'`) prevent regression."
  - "Stub-presence test replacement as Rule-1 deviation: when a cross-plan stub's body ships in a later plan, the prior plan's stub-presence test (which asserted NotImplementedError) is invalid and must be replaced with a positive behavior test. Mirrors Phase 2 02-02 pattern. The replacement test should exercise the canonical happy-path against an oracle value if available."

requirements-completed: []  # AFFD-01..04 + AFFD-06 are addressed at the math level in Plan 04-02, but per project convention (Phase 3 03-01: 'Mark requirements complete only when ALL plans listing the requirement in frontmatter have shipped') they stay open until Plan 04-04 wires the precedence pipeline + Plan 04-06 ships the fixture-based tests. AFFD-07 closes at Plan 04-04 (blocker precedence). The 9 AFFD-XX xfail stubs in tests/test_affordability.py remain xfail as the plan instructed.

duration: 8min
completed: 2026-04-30
---

# Phase 4 Plan 02: Forward Affordability Summary

**evaluate_forward(req: ForwardModeRequest) -> AffordabilityResponse implementation: composes Phase 1/2/3 (lib.models + lib.rules predicates + lib.amortize.build_schedule) into a 7-step DTI/LTV/CLTV/PITI pipeline with FHA UFMIP auto-finance, joint-applicant aggregation, predicate-signature reconciliation, and StaleReferenceWarning capture; ships private helpers _compute_dti / _compute_ltv / _compute_cltv / _classify_target_loan_type / _compute_monthly_mi / _build_loan_for_amortization / _build_county.**

## Performance

- **Duration:** 8 min (Task 1 helpers + Task 2 evaluate_forward body)
- **Started:** 2026-04-30T19:20:32Z
- **Completed:** 2026-04-30T19:29:27Z
- **Tasks:** 2
- **Files modified/created:** 2 modified (lib/affordability.py +340 lines; tests/test_affordability.py +45/-7 lines)

## Accomplishments

- `evaluate_forward` body shipped (replaces the Plan 04-01 `raise NotImplementedError("forward evaluation shipped in Plan 04-02")` stub)
- 7 private helpers shipped: `_compute_dti`, `_compute_ltv`, `_compute_cltv`, `_classify_target_loan_type`, `_compute_monthly_mi`, `_build_loan_for_amortization`, `_build_county`
- `USDA_ANNUAL_FEE_RATE = Decimal("0.0035")` statutory constant + `_LOAN_TYPE_BLOCKER_PREFIX` citation prefix table for D-11 step-1 blocker construction
- Conforming oracle parity verified end-to-end: $400k @ 6.5%/30yr conventional 80% LTV produces `monthly_pi=$2528.27` exactly (matches Phase 1 `golden_pmt.json` + Phase 3 `build_schedule`); `financed_loan_amount=$400000.00` (no UFMIP for conventional); `loan_type='conforming'`; `ltv=0.80`; `cltv=0.80`; `monthly_mi=$0.00`; `blocked=False`; `warnings=[]`
- FHA path verified: $400k/$500k FHA produces `financed_loan_amount=$407000.00` (= 400000 + 7000 UFMIP at 1.75%); `monthly_mi=$169.58`; `warnings` contains `'fha-mip-rates ... more than 12 months old'` (StaleReferenceWarning correctly captured via `warnings.catch_warnings(record=True)`)
- VA path verified: `monthly_mi=$0.00`, `financed_loan_amount=$400000.00` (no UFMIP for VA per Plan 04-02)
- Phase 2 predicate-signature drifts (RESEARCH §A.1-A.3) handled at composition boundary: `loan_type.classify(loan_amount, county, program=...)` with corrected signature; `fha_mip.compute(loan, original_property_value, endorsement_date)` with full triple; `conventional_pmi.LTV_REQUEST_ELIGIBLE` consumed directly (`status()` not called)
- Replaced `test_evaluate_forward_is_cross_plan_stub` (which asserted `NotImplementedError` on the stub) with `test_evaluate_forward_returns_response_for_valid_request` (positive behavior test against the conforming oracle)
- Full suite **320 passed + 9 xfailed** (no regression from Plan 04-01 baseline); mypy --strict + ruff clean across both modified files; Phase 1/2/3 surfaces unmodified
- 9 AFFD-XX Wave 0 xfail stubs preserved verbatim (Plan 04-06 flips them per phase plan)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Phase 2 predicate imports + private helpers** — `a841725` (feat)
2. **Task 2: Implement evaluate_forward — replaces stub body; composes helpers + build_schedule + warning capture** — `e21c9df` (feat)

_Plan metadata commit (this SUMMARY + state updates) follows after self-check._

## Files Created/Modified

- `lib/affordability.py` (MODIFY, +340 lines net) — added `import warnings`, `numpy_financial`, `build_schedule`, `quantize_cents`, `StaleReferenceWarning`, `fha_mip_compute`, `loan_type_classify` runtime imports; added `Final` to typing imports; added `USDA_ANNUAL_FEE_RATE` Decimal constant; added `_LOAN_TYPE_BLOCKER_PREFIX` dict; added 7 private helpers; replaced `evaluate_forward` body (177 lines) implementing the full 7-step composition pipeline
- `tests/test_affordability.py` (MODIFY, +45/-7 lines net) — replaced `test_evaluate_forward_is_cross_plan_stub` with `test_evaluate_forward_returns_response_for_valid_request` positive behavior test (exercises the conforming oracle: $400k @ 6.5%/30yr -> $2528.27 monthly_pi)

## Decisions Made

- **Two-step UFMIP-then-build_schedule for FHA target.** When `target_loan_type=='fha'`, the pipeline calls `fha_mip_compute` once before financing to get `ufmip`, computes `financed_loan_amount = loan_amount + ufmip`, then runs `build_schedule(financed_loan)` for `monthly_pi`. The downstream `_compute_monthly_mi` is then called on `financed_loan_amount` (which calls `fha_mip_compute` again under the hood — harmless because `lib.rules._loader.load_reference` is `@lru_cache`d). The plan author flagged this sequencing concern in the action body and the implementation followed the recommended inline two-step shape for clarity.
- **Replace stub-presence test with positive behavior test as Rule-1 deviation.** `test_evaluate_forward_is_cross_plan_stub` (which asserted `NotImplementedError` on the Plan 04-01 stub) became invalid as soon as the Plan 04-02 stub body shipped. Mirrors Phase 2 02-02 pattern (REMOVED `test_fha_program_raises_not_implemented_until_ref_02_lands` + ADDED 4 positive FHA tests when REF-02 landed). The replacement test exercises the canonical $400k @ 6.5%/30yr conforming oracle.
- **Phase 4's evaluate_forward leaves `blocked / blocked_by` reflecting ONLY the loan-type-classify step-1 blocker.** Plan 04-04 wraps `evaluate_forward` with `_evaluate_blockers(...)` that runs the rest of the D-11 precedence pipeline (LTV/CLTV ceiling -> DTI cap -> ATR/QM -> VA-residual) and mutates a NEW response via `model_copy(update={...})`. This split keeps `evaluate_forward` focused on math and Plan 04-04 focused on regulatory blocker precedence. Documented in the evaluate_forward docstring step 12 + the function body's comment block.
- **Re-add `import warnings`, `from lib.amortize import build_schedule`, `from lib.rules._loader import StaleReferenceWarning` in Task 2** because Task 1's commit-time ruff `--fix` stripped them as F401 unused (Task 1 helpers don't reference them). Task 2's `evaluate_forward` body uses all three. Documented as a Rule-3 hygiene deviation; reusable pattern for any future multi-task plan that stages imports in an early task whose body doesn't yet use them.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Re-added imports stripped by ruff F401 in Task 1 commit**

- **Found during:** Task 2 (mypy --strict on lib/affordability.py after writing evaluate_forward body)
- **Issue:** Task 1's action body specified `import warnings`, `from lib.amortize import build_schedule`, `from lib.rules._loader import StaleReferenceWarning` to be added at module top. The Task 1 helpers (_compute_dti / _compute_ltv / _compute_cltv / _classify_target_loan_type / _compute_monthly_mi / _build_loan_for_amortization / _build_county) do not reference any of those three imports — only `quantize_cents`, `Decimal`, `Loan`, `LTV_REQUEST_ELIGIBLE`, `LoanType`, `MissingCountyDataError`, `fha_mip_compute`, `County`, `loan_type_classify`. ruff `--fix` invoked during the Task 1 grooming run stripped the three unused imports as F401. When Task 2's evaluate_forward body was added, mypy --strict surfaced 5 F821 / undefined-name errors at the call sites for `warnings.catch_warnings`, `StaleReferenceWarning`, and `build_schedule`.
- **Fix:** Re-added the three imports at the top of lib/affordability.py in Task 2's edit. ruff was clean after the re-add (the imports are now used). Mirrors Phase 3 03-02 / 03-04 / 04-01 ruff-driven import-management deviation patterns.
- **Files modified:** lib/affordability.py
- **Verification:** `uv run ruff check lib/affordability.py` -> All checks passed!; `uv run mypy --strict lib/affordability.py` -> Success: no issues found in 1 source file
- **Committed in:** e21c9df (Task 2 commit)

**2. [Rule 3 - Blocking] Removed plan-author speculative `# noqa: F841` after ruff RUF100**

- **Found during:** Task 2 (ruff check after writing evaluate_forward body)
- **Issue:** Plan action body specified `_min_credit_score = min(a.credit_score for a in applicants)  # noqa: F841` (F841 = local-variable-assigned-but-never-used). Because the variable is `_`-prefixed, ruff F841 does NOT fire on it (ruff's unused-binding detection respects the underscore convention); ruff RUF100 then fires on the noqa as an unused directive.
- **Fix:** Removed `# noqa: F841`; reworded the explanatory comment block above the assignment to reference the underscore-prefix convention. The variable is correctly bound for D-05 documentation purposes; Plan 04-04 will consume `min(...)` when the blocker pipeline lands. Mirrors 02-07 + 03-04 + 04-00 + 04-01 "no speculative noqa" project convention.
- **Files modified:** lib/affordability.py
- **Verification:** `uv run ruff check lib/affordability.py` -> All checks passed!
- **Committed in:** e21c9df (Task 2 commit)

**3. [Rule 1 - Bug] Replaced invalid stub-presence test (`test_evaluate_forward_is_cross_plan_stub`) with positive behavior test**

- **Found during:** Task 2 (full test suite run after writing evaluate_forward body)
- **Issue:** Plan 04-01's `test_evaluate_forward_is_cross_plan_stub` asserted that `evaluate_forward(None)` raises `NotImplementedError("forward evaluation shipped in Plan 04-02")`. Once Plan 04-02 ships the body, that assertion is invalid — `evaluate_forward(None)` now raises `AttributeError: 'NoneType' object has no attribute 'household'` (because the new body dereferences `request.household.applicants` immediately). The test would FAIL after Plan 04-02 ships the stub body, breaking the suite-stays-green discipline.
- **Fix:** Renamed the test to `test_evaluate_forward_returns_response_for_valid_request` and replaced the body with a positive behavior test that constructs a valid ForwardModeRequest (the conforming oracle: $400k @ 6.5%/30yr) and asserts `response.monthly_pi == Decimal("2528.27")`, `response.ltv == Decimal("0.80")`, `response.loan_type == "conforming"`. Mirrors Phase 2 02-02 pattern (REMOVED `test_fha_program_raises_not_implemented_until_ref_02_lands` + ADDED 4 positive FHA tests when REF-02 landed) — established convention for cross-plan-stub-test handoff.
- **Files modified:** tests/test_affordability.py
- **Verification:** `uv run pytest tests/test_affordability.py -x` -> 19 passed + 9 xfailed; `uv run mypy --strict tests/test_affordability.py` -> Success
- **Committed in:** e21c9df (Task 2 commit)

**4. [Rule 3 - Blocking] Accepted ruff format auto-collapse of `sum_monthly_debts` multi-line expression**

- **Found during:** Task 2 (pre-commit ruff format hook ran on the evaluate_forward body)
- **Issue:** Plan action body wrote `sum_monthly_debts = (\n    debts.auto + debts.student_loans + debts.credit_cards + debts.other\n)` as a 3-line wrapped assignment. ruff format auto-collapsed to a single line because the right-hand side fits at 100 chars (ruff line-length).
- **Fix:** Accepted the ruff format output. Substance preserved (sum is identical; only the line shape differs from the plan's verbatim quote). Mirrors 03-01 / 03-02 / 03-04 / 04-00 ruff-format-auto-wrap deviation pattern.
- **Files modified:** lib/affordability.py (auto-formatted by pre-commit hook)
- **Verification:** Single-line `sum_monthly_debts = debts.auto + debts.student_loans + debts.credit_cards + debts.other` is grep-equivalent to the multi-line form; full suite still 320 passed + 9 xfailed
- **Committed in:** e21c9df (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (1 Rule-1 invalid test removal, 3 Rule-3 hygiene/format)

**Impact on plan:** All four deviations are tooling/test-handoff class. The math contract specified in the plan's `<behavior>` block + `<acceptance_criteria>` is shipped exactly as written; the Rule-3 deviations adjust the EXPRESSION of the contract to satisfy the project's tooling discipline (mirrors prior plans' ruff/mypy hygiene deviation patterns: 02-07 noqa, 03-01 ruff-format auto-wrap, 03-02 multiple ruff format auto-wraps, 03-04 four ruff hygiene fires, 03-06 grep-gate-driven docstring expansion, 04-00/04-01 same pattern). The Rule-1 deviation is a documented project convention (Phase 2 02-02 pattern of replacing stub-presence tests when stub body lands). No scope creep.

## Issues Encountered

- The Plan-author-specified `Test 12: For FHA case, response.warnings contains a "stale" string entry` substring assertion was authored against an older `_loader.py` warning message format. The actual `lib/rules/_loader.py` warning string is `"Reference data 'fha-mip-rates' has effective=2023-03-20, which is more than 12 months old (threshold: 2025-04-30). Annual regulatory refresh may be overdue."` — does NOT contain the lowercase substring `"stale"`. The warning IS captured correctly (single warning string in `response.warnings`); it just uses different wording than the plan author anticipated. Resolution: the spirit of the test (StaleReferenceWarning was correctly captured and propagated) is verified end-to-end via `len(resp.warnings) >= 1` AND `'fha-mip-rates' in resp.warnings[0]` AND `'12 months' in resp.warnings[0]` — those substrings are stable contracts on the warning. Future Plan 04-06 fixture tests should use the substring contract, not the literal `"stale"` substring.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the plan's `<threat_model>` already enumerated. T-04-02-01..T-04-02-07 mitigations are all preserved by acceptance-grep gates + structural reads:

- T-04-02-01 (predicate signature drift): positive grep gates verified `program=program`, `from lib.rules.fha_mip import compute as fha_mip_compute`, `MissingCountyDataError`; negative grep gate verified ZERO occurrences of `conventional_pmi.status(ltv_pct` or `fha_mip.compute(loan_amount, ltv_pct, term_months)`
- T-04-02-02 (PITI mid-calculation quantize): positive grep gate `quantize_cents(piti_pre_quantize)` returns 1; structural read confirms only ONE `quantize_cents` call on the PITI sum (the others are for individual money outputs at end-of-period boundary)
- T-04-02-03 (MissingCountyDataError silent catch): action body explicitly states "MissingCountyDataError propagates as Python exception"; grep verified there is no try/except around `loan_type_classify(...)`; the exception propagates up the call stack to the script boundary (Plan 04-05 will surface it as 6-key envelope)
- T-04-02-04 (StaleReferenceWarning suppression): positive grep gate `warnings.catch_warnings(record=True)` returns 2 (code + docstring); the `warnings.simplefilter("always", StaleReferenceWarning)` line ensures warnings are never suppressed
- T-04-02-05 (float coercion): no `Decimal(0.07)` constructor calls anywhere; all annual_rate values flow through `request.annual_rate` which is Pydantic-strict-True validated
- T-04-02-06 (PII in module docstring): no PII added; King WA is the project's example county
- T-04-02-07 (UFMIP not financed): D-03 + RESEARCH recommendation locked to option (b) auto-finance; verified end-to-end by FHA case test (`financed_loan_amount=$407000.00` for $400k base loan with 1.75% UFMIP)

## User Setup Required

None — Plan 04-02 ships only internal calc-engine code; no external service configuration, no .env additions, no manual user steps.

## Next Phase Readiness

- **Plan 04-03 (reverse affordability) unblocked.** `evaluate_reverse` stub remains; ReverseModeRequest fields are pinned by Plan 04-01; private helpers (`_compute_dti`, `_compute_ltv`, `_compute_cltv`) are reusable for the round-trip closure check (D-09; SC-2). `numpy_financial` is already imported at module top so Plan 04-03 can call `npf.pv` without import surgery.
- **Plan 04-04 (blocker precedence) unblocked.** `evaluate_forward` already surfaces the loan-type-classify step-1 blocker into `response.blocked` / `response.blocked_by`; Plan 04-04 will wrap `evaluate_forward` with `_evaluate_blockers(...)` that runs steps 2-6 of D-11 precedence (LTV/CLTV ceiling -> DTI cap -> ATR/QM -> VA-residual) and mutates a NEW response via `AffordabilityResponse.model_copy(update={...})`. The 7 private helpers (`_compute_ltv`, `_compute_cltv`, `_compute_dti`, etc.) are reusable for the precedence math; `_LOAN_TYPE_BLOCKER_PREFIX` is the citation prefix table.
- **Plans 04-05 (CLI) + 04-06 (tests + fixtures) unblocked.** The 9 AFFD-XX Wave 0 xfail stubs are RED-flippable as soon as Plan 04-06 ships the fixture-based assertions against `evaluate_forward(...)` results. Plan 04-05 only needs to dispatch on `request.mode == "forward"` to call into `evaluate_forward` (which is a stable contract now).
- **No blockers.** Full suite green (320 passed + 9 xfailed = 329 collected); mypy --strict + ruff clean across the project; deviation-set is 1 Rule-1 (test-replacement) + 3 Rule-3 (hygiene/format) — all documented project patterns; no semantic changes to plan's math contract.

---
*Phase: 04-affordability*
*Completed: 2026-04-30*

## Self-Check: PASSED

- lib/affordability.py — FOUND
- tests/test_affordability.py — FOUND
- .planning/phases/04-affordability/04-02-forward-affordability-SUMMARY.md — FOUND
- Commit a841725 (Task 1) — FOUND
- Commit e21c9df (Task 2) — FOUND
