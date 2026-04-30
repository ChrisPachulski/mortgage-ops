---
phase: 03-core-amortization
plan: 01
subsystem: amortization-models
tags: [amortization, pydantic, models, validator, d-10, d-14, d-15]
requires:
  - lib/models.py (Phase 1 frozen Loan/Payment/Schedule + Money/Rate aliases)
  - lib/money.py (CENT, quantize_cents, MONEY_CONTEXT)
provides:
  - lib/models.py::Payment.cumulative_interest (D-14)
  - lib/models.py::Payment.cumulative_principal (D-14)
  - lib/models.py::Schedule.final_payment_adjusted (D-10)
  - lib/models.py::Schedule._total_interest_matches_last_cumulative (D-15 model_validator)
affects:
  - tests/test_models.py (5 new tests + 1 updated; no deletions)
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 @model_validator(mode='after') for cross-field invariants (Phase 3 first use)"
    - "Empty-list early-return guard inside model_validator for constructor convenience"
    - "Inline `# D-XX:` decision-citation comments next to each new field/validator"
key-files:
  created: []
  modified:
    - lib/models.py
    - tests/test_models.py
decisions:
  - D-10 implemented as Schedule.final_payment_adjusted: bool = False (default keeps Phase 1 callers green)
  - D-14 implemented as Payment.cumulative_interest + Payment.cumulative_principal each defaulting to Decimal("0.00")
  - D-15 implemented as Schedule @model_validator(mode='after') raising ValueError with "D-15 invariant:" message prefix when total_interest != payments[-1].cumulative_interest; empty payments list skipped per CONTEXT.md guidance
  - Validator return-type annotation kept unquoted as `Schedule` (not `"Schedule"`) because `from __future__ import annotations` already postpones evaluation; ruff UP037 enforces unquoting
metrics:
  duration_seconds: 242
  duration_minutes: 4
  completed_date: "2026-04-30"
  tasks_completed: 2
  tests_added: 5
  tests_updated: 1
  tests_total_in_test_models: 19
  full_suite_tests_passing: 259
---

# Phase 03 Plan 01: Amortization Models Extension Summary

Locked the Phase 3 amortization data shape on Phase 1's frozen Pydantic surface so Plan 03-02's `lib/amortize.py` engine can construct `Schedule` and `Payment` instances with cumulative-totals tracking, end-of-schedule adjustment flagging, and a model-level invariant guarding summary-vs-row consistency.

## What Shipped

**`lib/models.py`** — three additive changes (no Phase 1 field renamed/removed):

1. **Import** — `model_validator` added to the `pydantic` import line (alongside the existing `BaseModel, ConfigDict, Field`).
2. **`Payment` extension (D-14)** — two new `Money` fields appended after `balance`:
   - `cumulative_interest: Money = Decimal("0.00")` — running interest total through this period.
   - `cumulative_principal: Money = Decimal("0.00")` — running principal total through this period.
   - Both defaulted; existing Phase 1 `Payment` callers (test_payment_constructs_with_phase_3_shape, etc.) construct unchanged.
3. **`Schedule` extension (D-10 + D-15)**:
   - New field inserted before `payments`: `final_payment_adjusted: bool = False` (D-10 — engine sets True when final-period principal differs from formulaic value).
   - New `@model_validator(mode="after")` named `_total_interest_matches_last_cumulative` enforcing `Schedule.total_interest == payments[-1].cumulative_interest`. Empty-payments path is guarded (`if not self.payments: return self`) per CONTEXT.md "constructor convenience" allowance. Mismatched values raise `ValueError` (surfaced as `pydantic.ValidationError`) with message prefix `D-15 invariant:` and both actual values formatted in.

**`tests/test_models.py`** — one update + five new tests (no deletions):

| Test | Status | Pins |
|------|--------|------|
| `test_schedule_aggregates_loan_and_payments` | UPDATED | Phase 1 test now passes Payment with `cumulative_interest=Decimal("2166.67")` and Schedule with `total_interest=Decimal("2166.67")` so D-15 validator is satisfied. Existing assertions (`sched.loan.principal`, `len(sched.payments)`) preserved. |
| `test_payment_carries_cumulative_totals` | NEW | D-14 — Payment exposes both cumulative fields when supplied. |
| `test_payment_cumulative_totals_default_to_zero` | NEW | D-14 backwards-compat — both fields default to `Decimal("0.00")` when omitted. |
| `test_schedule_total_interest_must_match_last_cumulative` | NEW | D-15 — Schedule with mismatched values raises `ValidationError` whose `str(exc.value)` contains `"D-15"` or `"total_interest"`. |
| `test_schedule_with_empty_payments_skips_d15_validator` | NEW | D-15 guard — empty `payments=[]` constructs successfully (validator early-returns). Also confirms D-10 default. |
| `test_schedule_final_payment_adjusted_defaults_false` | NEW | D-10 — `Schedule.final_payment_adjusted` defaults to `False` when omitted. |

Final test_models.py count: 19 tests (was 14 at HEAD~2; gained 5).

## Decision Implementation Map

| CONTEXT.md decision | Implementation in lib/models.py | Test that pins it |
|---------------------|-------------------------------|-------------------|
| **D-10** Schedule.final_payment_adjusted bool flag, default False | `final_payment_adjusted: bool = False` field on Schedule | `test_schedule_final_payment_adjusted_defaults_false`, `test_schedule_with_empty_payments_skips_d15_validator` (asserts default in passing branch) |
| **D-14** Payment cumulative_interest + cumulative_principal Money fields with Decimal("0.00") defaults | Two Money fields appended after `balance` | `test_payment_carries_cumulative_totals` (positive), `test_payment_cumulative_totals_default_to_zero` (default) |
| **D-15** Schedule.total_interest == payments[-1].cumulative_interest invariant | `@model_validator(mode="after")` named `_total_interest_matches_last_cumulative`; empty-payments early-return; ValueError with `D-15 invariant:` prefix | `test_schedule_total_interest_must_match_last_cumulative` (raises), `test_schedule_aggregates_loan_and_payments` (passes), `test_schedule_with_empty_payments_skips_d15_validator` (skip path) |

## Verification Results

- `uv run pytest tests/test_models.py` — 19 passed
- `uv run pytest` (full suite) — 259 passed, 0 failed (4 pre-existing StaleReferenceWarning entries unrelated to this plan)
- `uv run mypy --strict .` — Success: no issues found in 47 source files
- `uv run ruff check .` — All checks passed
- `uv run ruff format --check .` — clean
- All grep gates from `<acceptance_criteria>` pass:
  - `cumulative_interest: Money = Decimal("0.00")` — present
  - `cumulative_principal: Money = Decimal("0.00")` — present
  - `final_payment_adjusted: bool = False` — present
  - `@model_validator(mode="after")` — present
  - `D-15 invariant:` — present in ValueError message
  - `from pydantic import.*model_validator` — present
  - `def test_payment_carries_cumulative_totals(` — 1 match
  - `def test_payment_cumulative_totals_default_to_zero(` — 1 match
  - `def test_schedule_total_interest_must_match_last_cumulative(` — 1 match
  - `def test_schedule_with_empty_payments_skips_d15_validator(` — 1 match
  - `def test_schedule_final_payment_adjusted_defaults_false(` — 1 match
  - `total_interest=Decimal("2166.67")` — 2 matches (updated test + final_payment_adjusted-default test)
  - No `assertAlmostEqual` in tests/test_models.py
- Manual sanity per plan: `python -c "from lib.models import Payment; p = Payment(...); print(p.cumulative_interest, p.cumulative_principal)"` prints `0.00 0.00` (verified).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Ruff UP037 forbids quoted `"Schedule"` return-type annotation**
- **Found during:** Task 1 — `uv run ruff check lib/models.py` failed with `UP037 [*] Remove quotes from type annotation` on the validator's `-> "Schedule":` annotation.
- **Cause:** The plan's verbatim text used `"Schedule"` in quotes, but the project enables `from __future__ import annotations` which already postpones evaluation of every annotation; ruff's UP037 rule flags the redundant string literal.
- **Fix:** Changed the validator return type from `-> "Schedule":` to `-> Schedule:` (unquoted). Behaviorally identical (Pydantic v2 + PEP 563 both resolve forward references at runtime). The plan's `<acceptance_criteria>` does not lock the quoted form; only `@model_validator(mode="after")` and `D-15 invariant:` are grep-anchored.
- **Files modified:** lib/models.py
- **Commit:** 9821d77

**2. [Rule 3 - Blocker] Pre-commit ruff format wrapped `final_payment_adjusted: bool = False  # ...` line because the inline comment pushed it past 100 chars**
- **Found during:** Task 1 commit — pre-commit `ruff format` reformatted the assignment into a parenthesized `final_payment_adjusted: bool = (False  # comment)` shape, which broke the grep gate `final_payment_adjusted: bool = False`.
- **Fix:** Moved the D-10 explanatory comment to the line above (`# D-10: True when final period principal != formulaic value` then `final_payment_adjusted: bool = False`). Kept the D-10 citation inline-adjacent. Grep gate now passes.
- **Files modified:** lib/models.py
- **Commit:** 9821d77

**3. [Rule 3 - Blocker] Pre-commit ruff format wanted to wrap a long inline comment in `test_schedule_aggregates_loan_and_payments`**
- **Found during:** Task 2 — `uv run ruff format --check tests/test_models.py` flagged a 104-char line: `cumulative_interest=Decimal("2166.67"),  # D-14 + D-15: must match Schedule.total_interest below`.
- **Fix:** Hoisted the long explanatory comment to the line above (`# D-14 + D-15: cumulative_interest must match Schedule.total_interest below`). Same approach applied to the analogous `total_interest=Decimal("2166.67")  # D-15: matches p.cumulative_interest above` line. Grep gate `total_interest=Decimal("2166.67")` still matches twice as required.
- **Files modified:** tests/test_models.py
- **Commit:** 81beaca

### Plan Spec Discrepancies (no behavior change)

- **Test count drift in plan body.** The plan stated "11 existing + 4 new = 15 tests" in `<done>` block of Task 2, but the file actually had 14 existing tests at HEAD~2 and the plan's `<action>` Change-2 listed **5** new tests (`test_payment_carries_cumulative_totals`, `test_payment_cumulative_totals_default_to_zero`, `test_schedule_total_interest_must_match_last_cumulative`, `test_schedule_with_empty_payments_skips_d15_validator`, `test_schedule_final_payment_adjusted_defaults_false`) plus 1 updated. Final reality: 14 + 5 = 19 tests. The plan's `<acceptance_criteria>` correctly grep-anchors all 5 new test names; only the prose count was off. Implemented per the artifact spec, not the prose count. Phase 3 baseline for Plans 02-04: **259 tests in full suite, 19 in test_models.py**.

## Phase 3 Plan 02-04 Baseline

Future Phase 3 plans (engine, fixtures, CLI) should baseline against:
- **Full suite:** 259 tests passing
- **`lib/models.py` shape:** Loan unchanged; Payment has 9 fields (was 7); Schedule has 5 fields (was 4) + 1 `@model_validator`
- **Forward contract for 03-02:** `lib/amortize.py::build_schedule` MUST construct each `Payment` with `cumulative_interest` + `cumulative_principal` set, AND construct `Schedule` with `total_interest=payments[-1].cumulative_interest` (else the validator raises). Empty-payments schedules remain legal but are not the engine's product.
- **Forward contract for 03-03 (fixtures):** JSON fixtures' `expected_schedule_summary` blocks should include `cumulative_interest` and `cumulative_principal` on first/last payment rows (per RESEARCH §9 schema).

## Threat Flags

None — plan stayed inside the threat model documented in the PLAN frontmatter (T-03-01-01..04 all addressed). No new endpoints, no new file access, no new schema at trust boundaries beyond what the plan already enumerated.

## Self-Check: PASSED

- lib/models.py — FOUND
- tests/test_models.py — FOUND
- commit 9821d77 (Task 1) — FOUND in git log
- commit 81beaca (Task 2) — FOUND in git log
- All grep gates verified above
- Full pytest suite 259/259 green
- mypy --strict + ruff check + ruff format --check all clean
