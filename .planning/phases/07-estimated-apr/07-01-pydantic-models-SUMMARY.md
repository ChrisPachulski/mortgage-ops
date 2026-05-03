---
phase: 07-estimated-apr
plan: 01
subsystem: api
tags:
  - phase-07
  - estimated-apr
  - pydantic-models
  - reg-z-appendix-j
  - sc-4-anchor

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "lib/models.Money + lib/models.Loan + Pydantic v2 strict+frozen+forbid convention (D-08 inheritance)"
  - phase: 02-rules-predicates
    provides: "lib/rules/reg_z.within_apr_tolerance + TOLERANCE_REGULAR + TOLERANCE_IRREGULAR (consumed by APRResponse.tolerance_check shape)"
  - phase: 07-estimated-apr (Plan 07-00)
    provides: "tests/test_apr.py 13 xfail-strict stubs + apr_fixture loader (1 stub flipped this plan)"
provides:
  - "lib/apr.py — Pydantic v2 boundary models APRRequest, AdvanceScheduleEntry, PaymentScheduleEntry, APRResponse"
  - "APRResponse SC-4 invariant: literal 'estimated APR' required AND bare 'APR' forbidden, enforced at the Pydantic model boundary (D-05)"
  - "APRRequest cross-field invariants: t=0 advance required (D-06) + payment_schedule periods sum >= 1"
  - "solve_apr(request) -> APRResponse stub raising NotImplementedError (Wave 2 fills body)"
  - "1 Wave-0 stub flipped to PASS: test_apr_solver_module_exists_with_newton_raphson_signature"
affects:
  - 07-02-newton-raphson-engine
  - 07-03-odd-first-period-helpers
  - 07-04-cli
  - 07-05-tests-and-fixtures
  - 07-06-references-doc
  - 07-07-ffiec-fixtures

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 ConfigDict(strict=True, frozen=True, extra='forbid') on every boundary model (Phase 1 D-08; lifted in Phases 3, 4, 5, 6)"
    - "Cross-field @model_validator(mode='after') for regulatory invariants (Reg Z Appendix J §(b)(2) t=0 advance, payment-schedule non-empty)"
    - "Literal-text invariant enforced at model boundary, not just CLI (D-05 — pins ROADMAP SC-4 at the deepest possible surface)"
    - "noqa: TC001 idiom for runtime-resolved Pydantic field annotations (matches lib/models.py noqa: TC003 for date)"

key-files:
  created:
    - lib/apr.py
  modified:
    - tests/test_apr.py

key-decisions:
  - "D-01 honored: all 4 boundary models use ConfigDict(strict=True, frozen=True, extra='forbid')"
  - "D-05 honored: APRResponse.summary literal-text invariant enforced via @model_validator at the Pydantic boundary (not just CLI); allows 'estimated APR' and 'APR tolerance' phrases, forbids bare 'APR' (regex \\bAPR\\b after stripping 'estimated APR')"
  - "D-06 honored: APRRequest cross-field validator enforces at least one t=0 advance with f=0 per Reg Z Appendix J §(b)(2)"
  - "D-07 honored: APRResponse.iterations is Field(ge=1, le=50) — Pydantic enforces ROADMAP SC-3 50-iteration cap at the model layer"
  - "D-08 honored: APRResponse.tolerance_check is dict[str, Any] | None (untyped) for Phase 8/12 extensibility"
  - "Plan ships a wider Literal['30/360', 'actual/365', 'actual/actual'] and an unbounded list[AdvanceScheduleEntry] (per the plan's task code blocks); CONTEXT.md D-03/D-04 propose tightening these to Literal['30/360'] and Field(min_length=1, max_length=1) — that tightening lives in CONTEXT, not in the 07-01 task code, and is appropriately a downstream concern (no field-name change required to apply later, satisfying Plan 07-01's Rule-1 boundary)"

patterns-established:
  - "Pydantic v2 boundary model with regulatory-citation cross-field validators (Phase 7 first iterative-solver boundary in mortgage-ops; mirrors lib/arm.py:107-170 cross-field idiom)"
  - "SC-4 literal-text invariant enforcement at the deepest model boundary; future plans/CLIs/subagents inherit the guarantee for free (cannot construct an APRResponse that violates SC-4)"
  - "Stub-with-NotImplementedError + Wave-N body-fill pattern continues from Phase 4 D-26 / Phase 5 D-09 (lib/apr.solve_apr ships the contract; Wave 2 fills the body)"

requirements-completed: []  # APR-01 is partially closed here (model surface). Full closure when Wave 2 (Plan 07-02) ships the solver body. Per Plan 07-01 frontmatter, requirements: [APR-01], but APR-01 spans model + Newton-Raphson body — leaving Pending in REQUIREMENTS.md until Wave 2 closes it (mirrors Phase 4 multi-plan partial-closure idiom).

# Metrics
duration: 6min 20s
completed: 2026-05-03
---

# Phase 7 Plan 1: Pydantic Models Summary

**Pydantic v2 boundary for the Reg Z Appendix J APR solver — APRRequest with cross-field t=0-advance + non-empty-payment validators, APRResponse with the SC-4 literal-text invariant ('estimated APR' required, bare 'APR' forbidden) enforced at the model boundary, and a NotImplementedError-stubbed solve_apr ready for Wave 2 to fill.**

## Performance

- **Duration:** 6 min 20 s
- **Started:** 2026-05-03T19:50:21Z
- **Completed:** 2026-05-03T19:56:41Z
- **Tasks:** 6 (all atomically committed; no checkpoint, no human action)
- **Files modified:** 1 (tests/test_apr.py)
- **Files created:** 1 (lib/apr.py)

## Accomplishments

- Shipped `lib/apr.py` (379 lines) with module docstring enumerating APR-01..08 + LOCKED DECISIONS D-01..D-08 + Phase-7-consumer back-pointer to `lib/rules/reg_z.py:43-47`
- Defined the four boundary models — `AdvanceScheduleEntry`, `PaymentScheduleEntry`, `APRRequest`, `APRResponse` — all with `ConfigDict(strict=True, frozen=True, extra="forbid")`
- Encoded the **SC-4 anchor** at the Pydantic model boundary: `APRResponse._summary_contains_literal_estimated_apr` enforces both halves of the rule (literal 'estimated APR' required AND bare 'APR' word forbidden, with 'APR tolerance' allow-listed) — so the engine layer cannot emit a response that violates SC-4 even by accident
- Encoded the Reg Z Appendix J §(b)(2) t=0-advance invariant + the payment-schedule non-empty invariant as `@model_validator(mode="after")` cross-field rules on `APRRequest`
- Shipped `solve_apr(request: APRRequest) -> APRResponse` stub raising `NotImplementedError` with a thorough docstring laying out the Wave 2 algorithm (npf.rate seed → Decimal Newton step → D-06 dual-criterion convergence → D-07 50-iteration cap)
- Flipped Wave 0 stub `test_apr_solver_module_exists_with_newton_raphson_signature` to a real signature-contract assertion (passes)
- **Suite count after:** 466 passed (was 465; +1 from the flipped stub) / 4 skipped / 13 xfailed (was 14; -1 from the flipped Phase 7 stub) — zero regression to Phase 5/6/7-Wave-0 baseline

## Task Commits

Each task committed atomically against `main` (sequential executor; no branching per `parallelization=false`; no AI attribution per global + project CLAUDE.md):

1. **Task 1: Create `lib/apr.py` with module docstring + LOCKED DECISIONS** — `49a1c79` (feat)
2. **Task 2: Add `AdvanceScheduleEntry` and `PaymentScheduleEntry` models** — `e05fccc` (feat)
3. **Task 3: Add `APRRequest` with cross-field validators** — `a2a3d0d` (feat)
4. **Task 4: Add `APRResponse` with literal-text invariant (SC-4 anchor)** — `ccfa3e8` (feat)
5. **Task 5: Add `solve_apr` stub raising `NotImplementedError`** — `cde813f` (feat)
6. **Task 6: Flip Wave 0 stub `test_apr_solver_module_exists_with_newton_raphson_signature`** — `bb00f9b` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution (the final docs(07-01) commit).

## Files Created/Modified

- `lib/apr.py` (created, 379 lines) — module docstring + 4 Pydantic boundary models + `solve_apr` stub. Imports trimmed to actually-used names per Wave-0's Rule-3 hygiene precedent.
- `tests/test_apr.py` (modified, +20/-6) — flipped 1 of 13 stubs to real signature-contract assertion.

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|-------------|--------|--------|
| `wc -l lib/apr.py` | >= 250 | 379 | PASS |
| `grep -c 'ConfigDict(strict=True, frozen=True, extra="forbid")' lib/apr.py` | 4 | 4 | PASS |
| `grep -c '@model_validator(mode="after")' lib/apr.py` | >= 3 | 4 | PASS |
| `grep -c "estimated APR" lib/apr.py` | >= 2 | 17 | PASS |
| `pytest tests/test_apr.py::test_apr_solver_module_exists_with_newton_raphson_signature -v` | PASS | PASS | PASS |
| `pytest tests/test_apr.py -v --tb=no \| tail -20` | 1 passed + 12 xfailed | 1 passed + 12 xfailed | PASS |
| `mypy --strict lib/apr.py` | clean | clean | PASS |
| `ruff check lib/apr.py` | clean | clean | PASS |
| `ruff format --check lib/apr.py` | clean | clean | PASS |
| Full-suite `pytest` (regression check) | >= 461 passed (executor floor) | 466 passed / 4 skipped / 13 xfailed / 0 failed / 0 errors | PASS |

## Decisions Made

None novel — followed the plan's 8 LOCKED DECISIONS (D-01..D-08) verbatim from the plan frontmatter and the Goal block. Three smoke-test invariants were validated empirically before each commit:

- After Task 3: confirmed APRRequest happy path + missing-t=0-advance ValidationError + extra='forbid' rejection + frozen-mutation rejection.
- After Task 4: confirmed APRResponse happy path + missing 'estimated APR' literal ValidationError + bare-'APR' regex rejection + 'APR tolerance' phrase allowance + iterations le=50 + iterations ge=1 + tolerance_check dict acceptance.
- After Task 5: confirmed `solve_apr` signature parameters/return-annotation + NotImplementedError raise.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Hygiene] Trimmed imports per task and added `noqa: TC001` for the runtime-resolved Pydantic field annotation**

- **Found during:** Tasks 1, 2 (incremental file build; ruff F401 + TC001 caught the imports)
- **Issue:** (a) ruff F401 flagged unused imports in Task 1 because Tasks 2-5 hadn't yet referenced them; (b) ruff TC001 flagged `from lib.models import Money` as a type-checking-only import, but Pydantic v2 resolves field annotations at runtime so the import must stay at runtime.
- **Fix:** (a) Task 1 ships only `from __future__ import annotations`; Tasks 2-5 add `Decimal`, `Literal`, `Any`, `re`, Pydantic primitives, `Loan`, `Money` as their respective code requires them. (b) Added `# noqa: TC001  # Pydantic resolves field annotations at runtime` to the `from lib.models import` line — matches the established `noqa: TC003` idiom in `lib/models.py:16` for the runtime-resolved `date` import.
- **Files modified:** `lib/apr.py`
- **Verification:** `ruff check lib/apr.py` clean; `ruff format --check lib/apr.py` clean; `mypy --strict lib/apr.py` clean after every task commit.
- **Committed in:** `49a1c79` (Task 1; no-imports baseline) and `e05fccc` (Task 2; noqa added with the first runtime use).
- **Plan deviation rule:** Rule-3 (hygiene only — mypy/ruff fixes that do not change semantics). Plan-spec `## Deviation Rules` line: "Rule-3: hygiene only (mypy/ruff fixes that do not change semantics) — log in SUMMARY." Mirrors Wave-0 Plan 07-00 SUMMARY's "1. [Rule 3 - Hygiene] Trimmed unused imports..." precedent.

---

**Total deviations:** 1 auto-fixed (Rule 3 hygiene)
**Impact on plan:** No semantic change. All four boundary models present with the exact field names + types + validators specified in the plan task code blocks. All five SC-4 model-boundary invariants fire as designed (smoke-tested 7 of them empirically before commits).

## Issues Encountered

None.

## Threat Flags

None — Phase 7 Plan 01 is a model-boundary plan; no new network surface, no auth boundaries, no schema changes at trust boundaries beyond the input-validation surface (which is the entire point of strict + frozen + forbid + cross-field validators). The plan's frontmatter lacks a `<threat_model>` section (correct for a Pydantic-only plan).

## Known Stubs

The following stub is **intentional** per the plan's must_haves and is queued for closure in Wave 2:

- **`lib/apr.py:solve_apr`** — raises `NotImplementedError("Wave 2 (Plan 07-02) implements the Newton-Raphson body; ...")`. The docstring lays out the full Wave 2 algorithm (npf.rate seed → Decimal Newton step → D-06 dual-criterion convergence → D-07 50-iteration cap → APRResponse construction). Plan 07-01 frontmatter explicitly lists this as truth #5: "Wave 0 stub `test_apr_solver_module_exists_with_newton_raphson_signature` flips PARTIALLY (model imports succeed; solver call still raises NotImplementedError until Wave 2)" — exactly the state we're in.

No unintentional stubs introduced. No mock/placeholder data. No "TODO" or "FIXME" comments.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture. All six tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

- **Wave 2 (Plan 07-02 Newton-Raphson engine)** is unblocked: imports `from lib.apr import APRRequest, AdvanceScheduleEntry, PaymentScheduleEntry, APRResponse, solve_apr` will succeed; Wave 2 replaces the `solve_apr` body with the actual Newton-Raphson loop (this plan's stub raises `NotImplementedError` with a forward-pointing message). Wave 2 also flips 3 more stubs: `test_apr_solver_seeded_from_npf_rate`, `test_apr_solver_converges_within_decimal_00001_tolerance`, `test_apr_solver_raises_on_non_convergence`.
- **Wave 4 (Plan 07-04 CLI)** will import `APRRequest` for Pydantic JSON validation at the CLI boundary; the four `ConfigDict(strict=True, frozen=True, extra="forbid")` decorators ensure a malformed JSON payload surfaces a 6-key Pydantic envelope on stderr per Phase 3 WR-02 / Phase 4 D-13 inheritance.
- **Plan-vs-CONTEXT scope-tightening note (informational, NOT a deviation):** CONTEXT.md D-03 + D-04 propose tightening `day_count` to `Literal["30/360"]` and `advance_schedule` to `Field(min_length=1, max_length=1)`. Plan 07-01's task code blocks (the binding execution surface) ship the wider `Literal["30/360", "actual/365", "actual/actual"]` and unbounded `list[AdvanceScheduleEntry]`. The plan's `## Deviation Rules` says "Rule-1: any change to model field NAMES requires plan revision (Wave 2-4 reference these names verbatim)" — neither tightening changes a field NAME, so applying them in a future re-plan or a Wave 2/4 plan revision is allowed without bouncing 07-01.
- **APR-01 status:** REQUIREMENTS.md's APR-01 ("`lib/apr.py` Newton-Raphson solver against Reg Z Appendix J unit-period equation") spans both the model surface (this plan) and the engine body (Wave 2). Per the plan's `requirements-completed: []` decision, I am leaving APR-01 in REQUIREMENTS.md as Pending until Wave 2 closes it — mirrors Phase 4's multi-plan partial-closure idiom (e.g., AFFD-01..09 closed across plans 04-01 to 04-06).

## TDD Gate Compliance

The plan does not declare `type: tdd`; this is a vanilla `type: execute` plan. Per the executor protocol's TDD section, no RED/GREEN/REFACTOR cycle gate enforcement is required. For traceability, however: the Wave 0 stub written in Plan 07-00 (commit `0009ba3`) acted as the de-facto RED gate for this plan; Task 6's flip + the 4 model-boundary smoke tests (Tasks 3, 4, 5) acted as the GREEN gate; no REFACTOR occurred (the file was written task-by-task and never restructured).

## Self-Check: PASSED

Verified at execution end:

- [x] `lib/apr.py` exists at the path declared in plan frontmatter (`files_modified: [lib/apr.py]`)
- [x] `git log --oneline | grep 49a1c79` (Task 1) → present
- [x] `git log --oneline | grep e05fccc` (Task 2) → present
- [x] `git log --oneline | grep a2a3d0d` (Task 3) → present
- [x] `git log --oneline | grep ccfa3e8` (Task 4) → present
- [x] `git log --oneline | grep cde813f` (Task 5) → present
- [x] `git log --oneline | grep bb00f9b` (Task 6) → present
- [x] All six task commits reachable from `main`
- [x] No commit message contains "Co-Authored-By", "claude", or any AI attribution (verified by `git log -6 --format='%B' | grep -ci 'co-authored\|claude\|anthropic\|generated with'` → 0)
- [x] Full suite: 466 passed / 4 skipped / 13 xfailed / 0 failed / 0 errors (zero regression to Wave-0 baseline of 465 passed; +1 net pass from the flipped stub)
- [x] mypy --strict + ruff check + ruff format --check all clean on `lib/apr.py` and `tests/test_apr.py`

---
*Phase: 07-estimated-apr*
*Completed: 2026-05-03*
