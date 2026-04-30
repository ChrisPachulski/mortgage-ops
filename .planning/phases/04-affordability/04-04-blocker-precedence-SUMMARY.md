---
phase: 04-affordability
plan: 04
subsystem: affordability

tags: [phase-4, affordability, blockers, precedence, citations, wave-4]

requires:
  - phase: 01-foundation
    provides: lib/models.py Money/Rate aliases (Rate.le=1 constraint surfaces a Plan 04-02 boundary edge case for high-debt requests — see Issues Encountered); lib/money.py quantize_cents single source of truth
  - phase: 02-regulatory-reference-data-rules-predicates
    provides: lib/rules/atr_qm.py general_qm_passes(apr, apor, loan_amount, lien_position) -> bool; lib/rules/usda.py evaluate(...).income_eligible per RESEARCH Open Q#4; lib/rules/va_residual_income.py evaluate(...).binding_rule_citation STABLE format (Phase 2 D-11 read VERBATIM); lib/rules/fannie_eligibility.py compute_llpa(credit_score, ltv_pct AS percentage points, ...) -> Decimal bps; lib/rules/freddie_eligibility.py evaluate(...).eligible bool; lib/rules/conventional_pmi.py LTV_REQUEST_ELIGIBLE statutory constant
  - phase: 03-core-amortization
    provides: response.model_copy(update={...}) frozen-Pydantic mutation idiom (used to layer blocker state on top of math-only response); D-04 PITFALLS pattern (single-quantize end-of-period, never per-component)
  - phase: 04-affordability
    provides: 04-01 type contract (10 frozen-strict Pydantic models + AffordabilityRequest discriminated union + cross-walk constants + _validate_common); 04-02 evaluate_forward 7-step pipeline (math-only response with classify-blocker preserved); 04-03 evaluate_reverse 12-step npf.pv pipeline (math-only response with classify-blocker preserved); 04-04 D-11 precedence pipeline + public evaluate() dispatcher (THIS PLAN)

provides:
  - lib/affordability.py extended with _evaluate_blockers(response, request) D-11 precedence pipeline
  - _append_soft_warnings(response, request) helper — always runs (T-04-04-05); HPA-PMI-REQUIRED + ATR-QM-NOT-EVALUATED + Fannie LLPA + Freddie ineligibility soft warnings
  - Public evaluate(request) -> AffordabilityResponse dispatcher (Plan 04-05 CLI consumes this; in-process Phase 5+ ARM/stress consumers use it directly)
  - LTV_CEILING_BY_TARGET / CLTV_CEILING_BY_TARGET tables (Final[dict[str, Decimal]]; conventional 0.97, jumbo 1.00, fha 0.965, va 1.00, usda 1.00 per RESEARCH)
  - BLOCKED_BY_* citation Final[str] format-string templates: LTV-CEILING-{LOAN_TYPE}, CLTV-CEILING-{LOAN_TYPE}, DTI-CAP-{LOAN_TYPE}, USDA-INCOME-LIMIT-{state_fips}-{county_fips}, ATR-QM-PRICE-FIRST, plus BLOCKED_BY_VA_RESIDUAL_PATTERN regex (predicate-emitted, never constructed)
  - WARNING_* soft-warning Final[str] templates: HPA-PMI-REQUIRED, ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR, FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}, FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}
  - Bucket-label helpers: _ltv_to_percentage_points (RESEARCH §A.4 fractional→percentage-point conversion for Fannie/Freddie predicate consumption), _ltv_bucket_label (7 buckets), _credit_score_bucket_label (9 buckets per Phase 2 RUL-02/03 standard boundaries)
  - 21 new Task 1 + Task 2 tests covering ceilings, citation templates, soft warnings, all 6 D-11 precedence steps, dispatcher routing, soft-warnings-always-evaluated invariant, VA-residual verbatim-citation negative-grep gate via inspect.getsource

affects: [04-05-cli-and-config, 04-06-tests-and-fixtures, 05-arm, 08-stress]

tech-stack:
  added: []  # Pure composition over Phase 1/2/3 + Plan 04-01/04-02/04-03 surface; no new runtime deps
  patterns:
    - "D-11 blocker-precedence-as-short-circuit pipeline: sequential `if new_blocked_by is None and ...` branches in fixed precedence order. First-hard-fail-wins; subsequent steps are skipped at the predicate-call level (NOT just the citation-assignment level — the predicate itself is not invoked once a higher-precedence blocker fired). Soft warnings always evaluated regardless of hard-blocker state (T-04-04-05) via _append_soft_warnings sibling helper that runs unconditionally. Reusable for any future regulatory-blocker pipeline with sum-type semantics + soft-vs-hard signal separation."
    - "Predicate-citation-read-verbatim-with-negative-grep-gate: when a downstream predicate emits a stable citation string (Phase 2 D-11 va_residual_income.binding_rule_citation), the consumer reads it via the `.binding_rule_citation` attribute and never reconstructs the string. The negative-grep gate `f\"VA-RESIDUAL-` (must be 0) is enforced by inspect.getsource introspection in test_evaluate_va_residual_citation_read_verbatim_not_constructed — a runtime assertion that catches future format-shadow regressions. Reusable for any predicate→consumer pair where the citation/error string format is a stable contract."
    - "Soft-warning-always-evaluated discipline (T-04-04-05): _append_soft_warnings runs UNCONDITIONALLY — both at the start of _evaluate_blockers when response.blocked is True from the classify step (early-return path) AND at the end of _evaluate_blockers after hard-blocker assignment. Reusable for any future plan that distinguishes hard-blockers (response.blocked) from advisory-class signals (response.warnings) and must surface BOTH simultaneously."
    - "LookupError-on-out-of-grid-predicate-input as advisory (T-04-04-07 ACCEPTED): Fannie LLPA + Freddie eligibility predicates raise LookupError when the (credit_score_bucket, ltv_bucket) cell does not exist in the YAML matrix (e.g., pre-2026 LLPA matrix bucket misses). Phase 4 catches LookupError + ValueError and treats as advisory (no warning emitted) rather than hard blocker. Documented inline + threat model T-04-04-07 mitigation. Reusable for any future plan composing predicates that raise on out-of-grid inputs."

key-files:
  created: []
  modified:
    - lib/affordability.py (+372 lines net: +12 lines for D-11 citation constants + ceiling tables in Task 1; +360 lines for _evaluate_blockers + _append_soft_warnings + evaluate() public dispatcher + bucket-label helpers + Phase 2 atr_qm/fannie/freddie/usda/va_residual imports in Task 2)
    - tests/test_affordability.py (+417 lines: +149 lines for Task 1 ceiling-table + citation-template + module-level-exposure tests; +268 lines for Task 2 D-11 precedence + dispatcher + verbatim-citation negative-grep tests)

key-decisions:
  - "Two-task plan executed cleanly: Task 1 (D-11 citation constants + ceiling tables; module-level surface for Plan 04-06 citation-coverage meta-test) committed atomically as `89c92ca`; Task 2 (the precedence pipeline + public dispatcher; the actual D-11 enforcement) committed atomically as `22bd64c`. Tests written first per project's TDD discipline; 5 Task 1 tests + 16 Task 2 tests all RED until source landed (verified via stepwise inline python smoke). The single-feat-commit-per-task shape mirrors prior plans (04-01/04-02/04-03) — each task ships green source + tests in one commit because pre-commit hooks (mypy --strict) gate any test that imports a non-existent module."
  - "Comment-block reword for negative grep gate: action body's literal `f\"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}\"` substring in the documentation comments triggered the plan's own negative-grep gate `f\"VA-RESIDUAL- (must be 0)`. Reworded both occurrences to reference the predicate-side citation by line-number citation (`lib/rules/va_residual_income.py L115`) instead of inlining the format-string. Negative grep gate now satisfied (count 0 across the file). Reusable pattern for any future plan whose negative-grep gate would otherwise fire on documentation comments — reword to cite the source location instead of inlining the prohibited substring."
  - "5 ruff hygiene auto-fixes inline: SIM102 nested-if collapses (DTI cap + ATR/QM gates) → use compound `and` conditions; SIM108 ternary collapses (ltv_fraction extraction in _append_soft_warnings; base extraction in evaluate dispatcher); RUF100 unused-noqa removal (S101 not enabled in ruff config — comment kept as plain comment without the directive). All applied in Task 2; no semantic changes. Mirrors 03-04 / 04-00 / 04-02 / 04-03 ruff-hygiene deviation pattern."
  - "Bucket-label helpers introduced for soft-warning citation strings (FANNIE-LLPA-... / FREDDIE-INELIGIBLE-...): _ltv_bucket_label (7 buckets: 60-OR-LESS, 60-75, 75-80, 80-85, 85-90, 90-95, OVER-95) + _credit_score_bucket_label (9 buckets: BELOW-620, 620-639, ..., 760-OR-ABOVE) match Phase 2 RUL-02/03 standard boundaries. The helper labels are for the citation STRING in response.warnings only — they do NOT replace the YAML-driven bucket lookup inside fannie_compute_llpa / freddie_evaluate (those still consult their own bucket tables internally). Reusable for any future Phase 4+ consumer that needs a coarse-grained label of the same RUL-02/03 buckets."

patterns-established:
  - "_evaluate_blockers as a 6-step composition pipeline that wraps a math-only response: (1) short-circuit if response.blocked from classify (still appends soft warnings); (2) USDA income (target=='usda'); (3) LTV/CLTV ceiling; (4) DTI cap (forward only — reverse enforces by construction per D-08); (5) ATR/QM general-QM (when apr+apor present); (6) VA-residual (target=='va', citation read verbatim). All 6 wrapped in `warnings.catch_warnings(record=True)` to propagate StaleReferenceWarning from predicate calls. Pydantic v2 frozen response gets a NEW response via model_copy(update={...}) — never in-place mutation. Reusable for any future Phase 4+ regulatory-blocker pipeline (Phase 5 ARM may compose this for reset-time DTI; Phase 8 stress may invoke per grid cell)."
  - "Public dispatcher pattern: evaluate(request) routes ForwardModeRequest|ReverseModeRequest via the discriminated-union mode field → evaluate_forward / evaluate_reverse → _evaluate_blockers. The script CLI (Plan 04-05) calls evaluate(); in-process consumers (Phase 5 ARM, Phase 8 stress) also call evaluate(). The two intermediate functions (evaluate_forward / evaluate_reverse) remain public for callers that want math-only output without blocker-precedence semantics (e.g., reverse-mode round-trip closure assertion in Plan 04-06's fixture-based test_AFFD_05_reverse_round_trip needs the math-only forward output to compare against the reverse output's max_loan_amount). Reusable for any future Phase 4+ entrypoint composition."
  - "Citation-coverage discoverability via dir() + grep: Plan 04-06's citation-coverage meta-test will introspect `dir(lib.affordability)` to find BLOCKED_BY_* (>= 5 constants) + WARNING_* (>= 4 constants) Final[str] module-level names; for each, verify at least one fixture's blocked_by / warnings entry matches the constant value or template-format-result. Pattern reusable for any future Phase that ships a citation-emitting calc layer."

requirements-completed: [AFFD-07]
# AFFD-07 (binding-rule citation when blocking) is closed at the math layer
# in Plan 04-04. Per project convention (Phase 3 03-01 STATE.md decision:
# "Mark requirements complete only when ALL plans listing the requirement
# in frontmatter have shipped"), AFFD-07 is listed in Plan 04-04 frontmatter
# `requirements_addressed: [AFFD-07]` — Plan 04-06 adds the fixture-based
# test_AFFD_07_blocked_by_va_residual_west_family_4 RED→GREEN flip, but the
# precedence pipeline + verbatim-citation discipline are shipped here. The
# AFFD-07 xfail stub in tests/test_affordability.py remains xfail until
# Plan 04-06 ships the fixture + flip.

duration: 10min
completed: 2026-04-30
---

# Phase 4 Plan 04: Blocker Precedence Summary

**`_evaluate_blockers` D-11 precedence pipeline + `evaluate()` public dispatcher: composes Phase 2 atr_qm + usda + va_residual_income + fannie/freddie eligibility predicates into the regulatory-blocker decision layer per CONTEXT.md D-11; first-hard-fail-wins short-circuit (loan-type-classify → USDA-income → LTV/CLTV ceiling → DTI cap → ATR/QM → VA-residual); soft warnings (HPA-PMI-REQUIRED + ATR-QM-NOT-EVALUATED + Fannie LLPA + Freddie ineligibility) always evaluated even when hard-blocked; VA-residual citation read VERBATIM from predicate's `binding_rule_citation` field (Phase 2 D-11 STABLE format; never format-shadowed in Phase 4); ROADMAP SC-3 anchor verified end-to-end (`blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"` for VA WEST family-4 below M26-7 minimum).**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-30T20:02:07Z
- **Completed:** 2026-04-30T20:12:45Z
- **Tasks:** 2 (Task 1 citation constants + ceiling tables; Task 2 _evaluate_blockers + evaluate() public dispatcher)
- **Files modified/created:** 0 created + 2 modified (lib/affordability.py +372 lines net; tests/test_affordability.py +417 lines)

## Accomplishments

- `_evaluate_blockers(response, request) -> AffordabilityResponse` shipped: D-11 precedence pipeline with first-hard-fail-wins short-circuit. All 6 precedence steps verified end-to-end against realistic-numbers smoke (the canonical example: VA WEST family-4 + actual_residual_income < $1,117 → `blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"` verbatim from `va_residual_evaluate(...).binding_rule_citation`).
- `_append_soft_warnings(response, request) -> AffordabilityResponse` shipped: HPA-PMI-REQUIRED (conv > 0.80 LTV per 12 USC §4902); ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR (both apr/apor None); FANNIE-LLPA-{FICO}-{LTV} (when `fannie_compute_llpa(...)` returns positive bps; LookupError on out-of-grid is treated as advisory per T-04-04-07); FREDDIE-INELIGIBLE-{FICO}-{LTV} (when `freddie_evaluate(...).eligible == False`). Always runs, regardless of hard-blocker state (T-04-04-05).
- `evaluate(request) -> AffordabilityResponse` public dispatcher shipped: routes ForwardModeRequest|ReverseModeRequest via the discriminated-union mode field → evaluate_forward / evaluate_reverse → _evaluate_blockers. This is the function `scripts/affordability.py` (Plan 04-05) consumes.
- D-11 citation constants shipped (Task 1): `LTV_CEILING_BY_TARGET` / `CLTV_CEILING_BY_TARGET` (Final[dict[str, Decimal]]); `BLOCKED_BY_LTV_CEILING_TEMPLATE` / `BLOCKED_BY_CLTV_CEILING_TEMPLATE` / `BLOCKED_BY_DTI_CAP_TEMPLATE` / `BLOCKED_BY_USDA_INCOME_TEMPLATE` (Final[str] format-string templates); `BLOCKED_BY_ATR_QM_PRICE_FIRST` (Final[str] literal); `BLOCKED_BY_VA_RESIDUAL_PATTERN` (Final[str] regex for citation-coverage meta-test); `WARNING_HPA_PMI_REQUIRED` / `WARNING_ATR_QM_NOT_EVALUATED` (Final[str] literals); `WARNING_FANNIE_LLPA_TEMPLATE` / `WARNING_FREDDIE_INELIGIBLE_TEMPLATE` (Final[str] format-string templates).
- Bucket-label helpers shipped: `_ltv_to_percentage_points` (RESEARCH §A.4 — Fannie/Freddie take ltv_pct AS percentage points, NOT fraction); `_ltv_bucket_label` (7 buckets matching Phase 2 RUL-02/03 boundaries: 60-OR-LESS / 60-75 / 75-80 / 80-85 / 85-90 / 90-95 / OVER-95); `_credit_score_bucket_label` (9 buckets: BELOW-620 / 620-639 / 640-659 / 660-679 / 680-699 / 700-719 / 720-739 / 740-759 / 760-OR-ABOVE).
- 21 new tests added (5 Task 1 + 16 Task 2): ceiling-table values; hard-blocker citation templates; soft-warning citation templates; module-level dir() exposure for Plan 04-06 citation-coverage meta-test; clean-conventional no-blocker; VA-residual blocker verbatim (ROADMAP SC-3); DTI-cap blocker; LTV-ceiling blocker; classify-blocker preserved (jumbo); USDA-income blocker; ATR/QM blocker when apr+apor present; ATR/QM advisory when missing; HPA-PMI-REQUIRED warning; blocked-iff-blocked-by invariant; dispatcher routes reverse mode; VA-residual pass-no-blocker; non-VA target skips VA evaluation; VA-residual citation-read-verbatim negative-grep via inspect.getsource; soft-warnings-appended-even-when-blocked.
- Full suite **340 passed + 9 xfailed** (was 320 + 5 Task 1 + 15 net Task 2 = 340; the 9 AFFD-XX Wave 0 xfail stubs preserved verbatim per plan instruction; Plan 04-06 flips them).
- mypy --strict + ruff clean across 51+ source files.
- ROADMAP SC-3 closed at the math layer: `evaluate(VA WEST family-4 with actual_residual_income < $1,117)` → `response.blocked == True`, `response.blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"` exactly, populated VERBATIM via `va_residual_evaluate(...).binding_rule_citation` (`lib/rules/va_residual_income.py:115`).
- BLOCKER 2 fix preserved: USDA branch reads `request.household.size` DIRECTLY; never infers from `len(applicants)` or `va.family_size`. Negative grep gates verified at 0 (`household_size = sum(1 for _ in request.household.applicants)` count: 0; `household_size = request.household.va.family_size` count: 0).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add D-11 blocker citation constants + LTV/CLTV ceiling tables** — `89c92ca` (feat)
2. **Task 2: Implement `_evaluate_blockers` + public `evaluate()` dispatcher** — `22bd64c` (feat)

_Plan metadata commit (this SUMMARY + state updates) follows after self-check._

## Files Created/Modified

- `lib/affordability.py` (MODIFY, +372 lines net):
  - Added 5 new Phase 2 predicate runtime imports: `from lib.rules.atr_qm import general_qm_passes`; `from lib.rules.fannie_eligibility import compute_llpa as fannie_compute_llpa`; `from lib.rules.freddie_eligibility import evaluate as freddie_evaluate`; `from lib.rules.usda import evaluate as usda_evaluate`; `from lib.rules.va_residual_income import evaluate as va_residual_evaluate`. Phase 2 D-08 full-path-import discipline preserved.
  - Task 1: D-11 citation-constants block (`LTV_CEILING_BY_TARGET`, `CLTV_CEILING_BY_TARGET`, 6 `BLOCKED_BY_*`, 4 `WARNING_*` constants) inserted between `_LOAN_TYPE_BLOCKER_PREFIX` and the Pydantic leaf models section.
  - Task 2: `_ltv_to_percentage_points`, `_ltv_bucket_label`, `_credit_score_bucket_label` helpers; `_evaluate_blockers` 6-step pipeline; `_append_soft_warnings` always-runs sibling helper; public `evaluate(request)` dispatcher. All appended at the end of the module after `evaluate_reverse`.
- `tests/test_affordability.py` (MODIFY, +417 lines):
  - Task 1: 5 new tests (test_ltv_ceiling_table_values, test_cltv_ceiling_table_values, test_blocked_by_citation_template_constants, test_warning_citation_constants, test_citation_constants_module_level_exposure).
  - Task 2: 16 new tests (test_evaluate_clean_conventional_no_blocker, test_evaluate_va_residual_blocker_west_family_4_verbatim [ROADMAP SC-3 anchor], test_evaluate_dti_cap_blocker, test_evaluate_ltv_ceiling_blocker_conventional, test_evaluate_classify_blocker_preserved_for_jumbo, test_evaluate_usda_income_blocker, test_evaluate_atr_qm_blocker_when_apr_apor_present, test_evaluate_atr_qm_advisory_when_apr_apor_missing, test_evaluate_hpa_pmi_required_warning_for_conv_above_80_ltv, test_evaluate_invariant_blocked_iff_blocked_by, test_evaluate_dispatcher_routes_reverse_mode, test_evaluate_va_residual_pass_no_blocker, test_evaluate_non_va_target_skips_va_residual, test_evaluate_va_residual_citation_read_verbatim_not_constructed [inspect.getsource negative-grep gate], test_evaluate_blockers_appends_soft_warnings_even_when_blocked [T-04-04-05 mitigation pin]).

## Decisions Made

- **Comment-block reword to satisfy negative grep gate `f"VA-RESIDUAL- (must be 0)`.** The plan's action body included documentation comments referencing the predicate's stable format (`f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"`) twice — once near the regex pattern definition, once at the verbatim-read site. Both inlined the prohibited substring. Reworded both to reference the predicate source location by line citation (`lib/rules/va_residual_income.py:115`) instead of inlining the format-string. Negative grep gate now satisfies. The runtime negative-grep test (`test_evaluate_va_residual_citation_read_verbatim_not_constructed`) uses `inspect.getsource(affordability)` to enforce this discipline at test-runtime, catching future format-shadow regressions.
- **5 ruff hygiene auto-fixes applied inline as Rule-3 deviations.** SIM102 nested-if collapses on DTI-cap and ATR/QM-blocker gates → use compound `and` conditions; SIM108 ternary collapses on ltv_fraction extraction (forward vs reverse mode) and `base` selection in evaluate(); RUF100 unused-noqa removal on `# noqa: S101` (S101 is not enabled in this project's ruff config — the comment is kept without the directive). Mirrors 03-04 / 04-00 / 04-02 / 04-03 ruff-hygiene deviation pattern.
- **2 ruff format auto-formats accepted across the two task commits.** Pre-commit ruff format hook auto-reformatted lib/affordability.py + tests/test_affordability.py on each task commit (Task 1: 2 files reformatted; Task 2: 1 file reformatted). Mirrors 03-01 / 03-02 / 03-04 / 04-00 / 04-02 / 04-03 ruff-format-auto-wrap deviation pattern (now the seventh occurrence in this project).
- **DTI-cap blocker tests use realistic numbers (DTI < 1.0).** Pydantic Rate type has `le=Decimal("1")` constraint; pathological "DTI > 1" cases (where non-housing debts dwarf income) cannot be constructed because the math-only `evaluate_forward` raises a Pydantic ValidationError when populating `dti_back` on the response. Plan 04-04 tests use realistic DTI scenarios (e.g., FHA loan with 0.479 DTI vs 0.380 cap) which exercise the DTI-cap blocker correctly. The DTI > 1 edge case is OUT-OF-SCOPE for Plan 04-04 (Plan 04-01/04-02 surface decision; would require Rate type change rippling through all rate fields). Documented as a deferred edge case under "Issues Encountered" below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Comment-block reword to satisfy negative grep gate `f"VA-RESIDUAL- (must be 0)`**

- **Found during:** Task 2 (post-implementation acceptance-grep verification)
- **Issue:** The plan's action body included documentation comments at TWO locations (one near `BLOCKED_BY_VA_RESIDUAL_PATTERN`, one at the `va_result.binding_rule_citation` verbatim-read site) that inlined the prohibited substring `f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"`. The plan's negative-grep gate `f"VA-RESIDUAL- (must be 0)` would fire because grep operates on file text including comments.
- **Fix:** Reworded both comment-block occurrences to reference the predicate source location (`lib/rules/va_residual_income.py:115`) instead of inlining the format-string. The runtime negative-grep test (`test_evaluate_va_residual_citation_read_verbatim_not_constructed`) uses `inspect.getsource(affordability)` to enforce this discipline at test-runtime as well. Mirrors 02-05 / 03-04 reword-to-satisfy-grep-gate deviation pattern.
- **Files modified:** lib/affordability.py
- **Verification:** `grep -c 'f"VA-RESIDUAL-' lib/affordability.py` → 0 (was 2)
- **Committed in:** 22bd64c (Task 2 commit; reword applied before commit)

**2. [Rule 3 - Blocking] 5 ruff hygiene auto-fixes inline (SIM102, SIM108, RUF100)**

- **Found during:** Task 2 (post-implementation `uv run ruff check`)
- **Issue:** ruff fired 5 hygiene complaints on the action-body-prescribed code:
  - SIM102 (×2): nested `if` statements on DTI-cap and ATR/QM-blocker gates should be collapsed via compound `and`
  - SIM108 (×2): if/else blocks for ltv_fraction extraction (`if response.mode == "forward"`) and `base` selection (`if request.mode == "forward"`) should be ternaries
  - RUF100: unused-noqa for `# noqa: S101` (S101 is not enabled in this project's ruff config — the directive is unused)
- **Fix:** All 5 fixes applied inline, no semantic changes. The compound `and` conditions and ternary expressions preserve the exact branch logic. The S101 noqa is removed (the assert remains a plain assert).
- **Files modified:** lib/affordability.py
- **Verification:** `uv run ruff check lib/affordability.py` → All checks passed!
- **Committed in:** 22bd64c (Task 2 commit; fixes applied before commit)

**3. [Rule 3 - Blocking] 2 ruff format auto-formats across the two task commits**

- **Found during:** Task 1 + Task 2 (pre-commit ruff format hook on the staged files)
- **Issue:** Pre-commit ruff format hook auto-reformatted both files on Task 1's commit (2 files reformatted: line-wrapping in the new constants block + minor whitespace in tests) and lib/affordability.py on Task 2's commit (1 file reformatted: minor line-wrapping in the action-body-prescribed code).
- **Fix:** Re-staged + re-committed after each ruff-format pass. Substance preserved on both reformat passes (only line shape differs from the action-body verbatim quote). Mirrors 03-01 / 03-02 / 03-04 / 04-00 / 04-02 / 04-03 ruff-format-auto-wrap deviation pattern (seventh occurrence in this project).
- **Files modified:** lib/affordability.py + tests/test_affordability.py
- **Verification:** Both task commits land green via the second commit attempt; full suite 340 passed + 9 xfailed.
- **Committed in:** 89c92ca (Task 1 second-attempt commit) + 22bd64c (Task 2 second-attempt commit)

---

**Total deviations:** 3 — all Rule-3 hygiene-class (no semantic changes to the plan's blocker-precedence math contract).

**Impact on plan:** All deviations are tooling/documentation-class. The math contract specified in the plan's `<behavior>` block (Tests 1-17) + `<acceptance_criteria>` literal grep gates (positive + negative) is shipped exactly as written. The Rule-3 deviations adjust the EXPRESSION of the contract to satisfy the project's tooling discipline. The negative grep gate `f"VA-RESIDUAL- (must be 0)` was the primary deviation source — reworded comments preserve the documentation intent while satisfying the literal-substring constraint. No scope creep.

## Issues Encountered

- **Pydantic Rate `le=Decimal("1")` constraint blocks pathological DTI > 1.0 cases.** When constructing test scenarios for the DTI-cap blocker, an initial test case used $5k income + $5,500 monthly debts → DTI 1.82, which crashes `evaluate_forward(...)` at the AffordabilityResponse construction step (Pydantic rejects `dti_back > 1`). The Rate type is defined in `lib/models.py` as `Annotated[Decimal, Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1"))]` — the `le=1` upper bound is correct for rates that semantically can't exceed 100% (LTV, interest rates), but DTI can exceed 1.0 in pathological cases (debts > income). This is a Plan 04-01 / 04-02 surface decision; OUT-OF-SCOPE for Plan 04-04. Plan 04-04 tests use realistic DTI scenarios (e.g., FHA loan with 0.479 DTI vs 0.380 cap) that exercise the DTI-cap blocker without hitting the Pydantic constraint. Resolution for Plan 04-04: documented here for Plan 04-05 (CLI) and Plan 04-06 (fixtures) authors — the CLI must surface a clean error message when callers submit pathological scenarios where math-only-pass ValidationError fires before the blocker pipeline can cite DTI-CAP-{LOAN_TYPE}. A Plan 04-06 follow-up fixture might pin this corner case via a different DTI cap (e.g., a request that exceeds 0.43 but stays below 1.0). Future v2 may relax the Rate type's `le=1` for DTI-class fields specifically — but that requires a new Annotated alias (e.g., `DTI: Annotated[Decimal, Field(..., ge=0, le=Decimal("3"))]`) to preserve type discipline across Money/Rate boundaries.

- **ATR-QM threshold tier auto-passes for very-large loans.** Initial ATR/QM blocker test used a 5pp APR-APOR spread on a $400k loan; the threshold for first-lien tier-1 is 2.25pp, so spread > threshold triggered blocker correctly. Worth noting for Plan 04-06 fixtures: small-loan (< $66k) tier and subordinate-lien tier are out-of-scope for Phase 4 v1 (CONTEXT.md / RESEARCH §"First-lien vs subordinate-lien" — first-lien residential only).

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the plan's `<threat_model>` already enumerated. T-04-04-01..T-04-04-08 mitigations are all preserved by acceptance grep gates + structural reads + the new runtime negative-grep test:

- **T-04-04-01 (VA-residual citation format-drift):** `grep -c 'f"VA-RESIDUAL-' lib/affordability.py` returns 0 (was 2; reworded as Rule-3 deviation #1); `va_result.binding_rule_citation` read verbatim (positive grep returns 1); runtime negative-grep test `test_evaluate_va_residual_citation_read_verbatim_not_constructed` uses `inspect.getsource` to catch future format-shadow regressions; ROADMAP SC-3 anchor (`blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"`) verified end-to-end via `test_evaluate_va_residual_blocker_west_family_4_verbatim`.
- **T-04-04-02 (precedence violation):** Sequential `if new_blocked_by is None and ...` branches enforce precedence in code structure. `test_evaluate_classify_blocker_preserved_for_jumbo` confirms classify-step blocker (Plan 04-02 step 1) takes precedence over LTV-ceiling check. Plan 04-06 will ship additional precedence-pin fixtures (e.g., a request that violates BOTH LTV and DTI must surface LTV citation, not DTI).
- **T-04-04-03 (LTV ceiling silently downgraded for conv 97% FTHB):** ACCEPTED per RESEARCH Assumption A1 — Phase 4 v1 unconditional 97% per HomeReady; FTHB modeling out of v1; documented in `LTV_CEILING_BY_TARGET` source comment.
- **T-04-04-04 (USDA blocker mis-ordering):** Code structure orders USDA at step 2 (after classify, before LTV/CLTV). Plan 04-06 will pin via a USDA loan that has BOTH income-ineligibility AND below-ceiling LTV — must surface USDA-INCOME-LIMIT, not LTV-CEILING.
- **T-04-04-05 (soft warnings silently dropped):** `_append_soft_warnings` runs UNCONDITIONALLY — both at the early-return path when classify-blocked AND at the end of `_evaluate_blockers`. Pinned by `test_evaluate_blockers_appends_soft_warnings_even_when_blocked`.
- **T-04-04-06 (Pydantic frozen response mutated in-place):** All response transitions use `response.model_copy(update={...})` (positive grep returns 4 occurrences; in-place attribute assignment would raise TypeError at runtime per Pydantic v2 frozen semantics). Pinned by Plan 04-01's `test_response_is_frozen`.
- **T-04-04-07 (Fannie LLPA / Freddie LookupError silently swallowed):** ACCEPTED per RESEARCH §"fannie_eligibility.py" + §"freddie_eligibility.py": predicates raise LookupError on out-of-grid inputs (pre-2026 LLPA matrix bucket misses). `_append_soft_warnings` explicitly catches `(LookupError, ValueError)` and skips the soft warning — out-of-grid is informational; no actionable info. Documented in code comment.
- **T-04-04-08 (response.warnings leaks predicate-internal staleness):** ACCEPTED per RESEARCH §"_loader.py + StaleReferenceWarning" + Phase 2 D-12: surfacing stale warnings to caller is by-design (Phase 2 D-12 + D-11). Documented in module docstring; the "loud-by-default" stance is the project-level choice.

## User Setup Required

None — Plan 04-04 ships only internal calc-engine code; no external service configuration, no .env additions, no manual user steps.

## Next Phase Readiness

- **Plan 04-05 (CLI + config) unblocked.** `evaluate(request)` is the public dispatcher; `scripts/affordability.py` (Plan 04-05) needs only to call `AffordabilityRequest.model_validate_json(raw)` (with the Phase 3 D-19 6-key envelope shape preserved on ValidationError) → dispatch to `evaluate(request)` → `print(response.model_dump_json(indent=2))`. Lazy-import discipline preserved: numpy_financial is already imported at module top by Plan 04-03; lib.rules.* predicates are imported eagerly at module load (Phase 2 D-08 full-path imports).
- **Plan 04-06 (tests + fixtures) unblocked.** All 9 AFFD-XX Wave 0 xfail stubs are RED-flippable. Plan 04-06's required fixtures:
  1. `forward_conventional_80_ltv.json` — clean conventional 80% LTV, no blocker (oracle anchor: $400k @ 6.5%/30yr → $2,528.27 monthly P&I; matches Plan 04-02 conforming oracle).
  2. `forward_conventional_85_ltv_with_pmi.json` — conv 85% LTV, monthly_pmi supplied; warnings contains `HPA-PMI-REQUIRED`.
  3. `forward_fha_above_dti_cap.json` — FHA loan with realistic DTI > max_dti; `blocked_by == "DTI-CAP-FHA"`.
  4. `forward_va_residual_fail.json` — VA WEST family-4 below $1,117; `blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"` (ROADMAP SC-3 anchor).
  5. `forward_jumbo_above_county_limit.json` — high-income applicant + $2M loan in King WA; `blocked_by` starts with `FHFA-LIMIT-CONFORMING-` (the classify-step blocker preserved by precedence).
  6. `reverse_conventional_80_ltv_43_dti.json` — SC-2 anchor: max_dti=0.43, joint income=10000, conv 80% LTV, 7%/30yr → max_loan_amount=$646,322.54 (engine-emitted; pinned in fixture; round-trip closure forward(reverse).dti_back == 0.430000 exact).
  7. `joint_applicants_two_incomes.json` — applicants=[A:credit 720, B:credit 680]; uses `min(720,680)=680` for Fannie/Freddie; income summed (SC-5).
  8. `single_applicant.json` — applicants=[only A]; same code path.
  9. `household_example_yml_e2e.json` — manifest pointing at `config/household.example.yml`; subprocess invocation per SC-4.

  The 9 AFFD-XX xfail stubs in tests/test_affordability.py flip RED→GREEN as Plan 04-06 ships the fixture-based assertions (Plan 04-06 also ships the citation-coverage meta-test that introspects `dir(lib.affordability)` via grep on `BLOCKED_BY_*` / `WARNING_*` prefixes — already discoverable at >= 5 / >= 4 constants per `test_citation_constants_module_level_exposure`).

- **Phase 5 (ARM) + Phase 8 (stress) downstream consumers unblocked.** Both consume `evaluate(request)` per the stable contract documented in CONTEXT.md `<code_context>` line 279. ARM-reset DTI re-computation will instantiate a ForwardModeRequest with the post-reset annual_rate and route through `evaluate(...)`. Stress-rate-shock + income-shock sweeps will call `evaluate(...)` per grid cell.

- **No blockers.** Full suite green (340 passed + 9 xfailed = 349 collected); mypy --strict + ruff clean across the project; deviation set is 3 Rule-3 hygiene-class only (no semantic changes); AFFD-07 closes at the math layer (Plan 04-06 fixture-based test_AFFD_07 xfail flip remains).

---
*Phase: 04-affordability*
*Completed: 2026-04-30*

## Self-Check: PASSED

- lib/affordability.py — FOUND
- tests/test_affordability.py — FOUND
- .planning/phases/04-affordability/04-04-blocker-precedence-SUMMARY.md — FOUND
- Commit 89c92ca (Task 1) — FOUND
- Commit 22bd64c (Task 2) — FOUND
