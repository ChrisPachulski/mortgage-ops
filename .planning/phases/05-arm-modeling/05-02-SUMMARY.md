---
phase: 05
plan: 02
subsystem: arm-modeling
tags:
  - phase-05
  - arm-modeling
  - pydantic-models
  - arm-01
dependency_graph:
  requires:
    - "05-00"  # Wave 0 test infrastructure (32 xfail stubs + arm_fixture loader)
    - "05-01"  # lib.money.quantize_rate public (consumed by Wave 3 engine)
    - "lib/models.py — Phase 1 Loan, Payment, Money, Rate (imported)"
  provides:
    - "lib.arm.ARMTerms — 8 explicit fields + optional note_rate (ARM-01 / SC-1)"
    - "lib.arm.IndexPathEntry — period + value sub-model (D-discretion scope-to-file)"
    - "lib.arm.ARMRequest — top-level request schema with _index_path_periods_align_to_reset_triggers validator (D-01)"
    - "lib.arm.ARMPayment — Phase 1 Payment subclass + rate_in_effect (D-03)"
    - "lib.arm.ResetEvent — applied_cap Literal[initial|periodic|lifetime|floor|none] (D-10)"
    - "lib.arm.ARMSchedule — parallel BaseModel (NOT subclass) for ARM-aware schedules (D-03)"
  affects:
    - "Wave 3 (Plan 05-03) — build_arm_schedule consumes ARMRequest + emits ARMSchedule"
    - "Wave 4 (Plan 05-04) — scripts/arm_simulate.py consumes ARMRequest at the model_validate_json boundary"
    - "Wave 5 (Plan 05-05) — appends references/arm-mechanics.md citation to ARMTerms docstring (SC-5)"
tech_stack:
  added: []
  patterns:
    - "Pydantic v2 strict+frozen+forbid on every model (defense-in-depth re-spec on ARMPayment subclass per RESEARCH LM-4)"
    - "D-01 cross-field validator: model_validator(mode='after') raises ValueError when index_path period not in reset trigger set"
    - "D-discretion scope-to-file: IndexPathEntry lives in lib/arm.py until a second consumer needs it (mirrors Phase 3 ExtraPrincipalEntry)"
    - "ARMPayment(Payment) Pydantic v2 inheritance: subclass adds rate_in_effect; Phase 1 fields auto-included"
key_files:
  created:
    - "lib/arm.py — 197 lines: 6 model classes + cross-field validator (no engine code; Wave 3 ships build_arm_schedule)"
  modified:
    - "tests/test_arm.py — +190 lines / -9 lines: 3 ARM-01 stubs flipped + 2 NEW ARMRequest validator tests (xfail count 32 → 29)"
decisions:
  - "Re-specify model_config on ARMPayment for grep-discoverability (RESEARCH LM-4: Pydantic v2 auto-inherits, but defense-in-depth re-spec is harmless)"
  - "Skip ARMTerms _initial_period_aligns_with_reset cross-field validator per CONTEXT.md A4 (not strictly required by ARM-01)"
  - "test_note_rate_defaults_to_loan_annual_rate flipped as PARTIAL — model-layer assertion only; Wave 3 (Plan 05-03) replaces with full engine assertion"
  - "test_cli_misaligned_index_path_period_rejected stays xfail in Wave 2 (CLI ships Wave 4); the model-layer half is pinned by NEW test_arm_request_misaligned_index_path_raises"
metrics:
  duration_minutes: 4
  completed: 2026-04-30
  tasks_completed: 3
  commits_created: 3  # 2 task commits + 1 docs commit
  test_count_before: 380_passed_4_skipped_32_xfailed
  test_count_after: 385_passed_4_skipped_29_xfailed
---

# Phase 5 Plan 02: Pydantic Models Summary

Shipped the 6-class Pydantic v2 model layer of `lib/arm.py` (197 lines), including ARMTerms with 8 explicit ARM-01 fields + REQUIRED floor_rate + optional note_rate, the D-01 ARMRequest cross-field validator that aligns index_path entries to reset trigger periods, the D-03 ARMPayment(Payment) subclass with rate_in_effect, the parallel ARMSchedule BaseModel, and ResetEvent with the 5-value applied_cap Literal. Flipped 3 Wave-0 ARM-01 xfail stubs (xfail count 32 → 29) and added 2 NEW model-layer tests pinning the cross-field validator. Phase 3 + Phase 4 baselines preserved.

## Tasks Completed

| # | Task                                                            | Commit    | Outcome |
|---|-----------------------------------------------------------------|-----------|---------|
| 1 | Create lib/arm.py with 6 Pydantic v2 models + ARMRequest validator | `fc1002d` | 197 lines; mypy --strict + ruff clean; all 6 model_config greps pass |
| 2 | Flip ARM-01 Wave 0 stubs in tests/test_arm.py + add 2 NEW tests | `ed49c86` | 5 tests passing; xfail 32 → 29; mypy + ruff clean |
| 3 | Verify zero regression to Phase 3 + Phase 4 + Wave 0/1 baselines | (no code) | 385 passed, 4 skipped, 29 xfailed, 0 failed |

## Acceptance Gate Results

### Plan-level acceptance (`<must_haves>`)

| Gate                                                                              | Result   |
|-----------------------------------------------------------------------------------|----------|
| `lib/arm.py` importable: 6 model classes                                          | PASS     |
| ARMTerms 8 explicit fields + optional note_rate (9 total)                         | PASS     |
| floor_rate REQUIRED (no default; missing raises ValidationError)                  | PASS     |
| ARMRequest._index_path_periods_align_to_reset_triggers model_validator(mode=after) | PASS     |
| ARMPayment subclasses Phase 1 Payment + rate_in_effect; re-specifies model_config | PASS     |
| ARMSchedule parallel BaseModel (NOT subclass) with payments + reset_events        | PASS     |
| ResetEvent.applied_cap Literal[initial, periodic, lifetime, floor, none]          | PASS     |
| IndexPathEntry inline in lib/arm.py (D-discretion scope-to-file)                  | PASS     |
| 3 Wave-0 stubs flipped (test_arm_terms_field_set, _missing_floor_rate_raises, _note_rate_defaults_to_loan_annual_rate) | PASS |
| Phase 4 baseline preserved (test_amortize.py + test_affordability.py unchanged)   | PASS     |

### Task-level grep gates (Task 1, lib/arm.py)

| Grep                                                                              | Expected | Actual |
|-----------------------------------------------------------------------------------|----------|--------|
| `class ARMTerms(BaseModel)`                                                       | 1        | 1      |
| `class IndexPathEntry(BaseModel)`                                                 | 1        | 1      |
| `class ARMRequest(BaseModel)`                                                     | 1        | 1      |
| `class ARMPayment(Payment)`                                                       | 1        | 1      |
| `class ResetEvent(BaseModel)`                                                     | 1        | 1      |
| `class ARMSchedule(BaseModel)`                                                    | 1        | 1      |
| `floor_rate: Rate$`                                                               | >=1      | 1      |
| `floor_rate: Rate \| None`                                                        | 0        | 0      |
| `note_rate: Rate \| None = None`                                                  | 1        | 1      |
| `applied_cap: Literal`                                                            | 1        | 1      |
| `Literal["initial", "periodic", "lifetime", "floor", "none"]`                     | 1        | 1      |
| `_index_path_periods_align_to_reset_triggers`                                     | >=1      | 2      |
| `@model_validator(mode="after")`                                                  | 1        | 1      |
| `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`             | 6        | 6      |
| `rate_in_effect: Rate`                                                            | 1        | 1      |
| `index_series_id: str`                                                            | 1        | 1      |
| `index_path: list[IndexPathEntry]`                                                | 1        | 1      |
| `def build_arm_schedule`                                                          | 0        | 0      |

### Task-level grep gates (Task 2, tests/test_arm.py)

| Grep                                                       | Expected | Actual |
|------------------------------------------------------------|----------|--------|
| `@pytest.mark.xfail`                                       | 29       | 29     |
| `def test_arm_request_misaligned_index_path_raises`        | 1        | 1      |
| `def test_arm_request_aligned_index_path_succeeds`         | 1        | 1      |

### Test results

| Suite               | Before          | After            | Delta                                  |
|---------------------|-----------------|------------------|----------------------------------------|
| Full suite (`-q`)   | 380p / 4s / 32x | 385p / 4s / 29x  | +5 passed, -3 xfailed (3 flips + 2 new) |
| `test_amortize.py`  | 42 passed       | 42 passed        | no change (Phase 3 zero regression)    |
| `test_affordability.py` | 78p / 4s    | 78p / 4s         | no change (Phase 4 zero regression)    |

### Lint/type results

`mypy --strict` + `ruff check` + `ruff format --check` all clean across:
`lib/arm.py`, `lib/money.py`, `lib/affordability.py`, `tests/test_arm.py`, `tests/test_money.py`, `tests/conftest.py`.

## Models inventory (lib/arm.py)

| Class           | Lines    | Fields                                                                                          | Notes                                              |
|-----------------|----------|-------------------------------------------------------------------------------------------------|----------------------------------------------------|
| ARMTerms        | 23-60    | 8 explicit + optional note_rate                                                                 | floor_rate REQUIRED; index_series_id min/max len   |
| IndexPathEntry  | 64-78    | period (>=1), value (Rate)                                                                      | Mirrors Phase 3 ExtraPrincipalEntry                |
| ARMRequest      | 81-130   | loan, arm_terms, assumed_index_rate, index_path                                                 | Has _index_path_periods_align_to_reset_triggers    |
| ARMPayment      | 133-145  | Phase 1 Payment fields + rate_in_effect                                                         | Subclass; re-specifies model_config (RESEARCH LM-4)|
| ResetEvent      | 148-173  | period, old_rate, new_rate, old_pmt, new_pmt, index_value_used, applied_cap                     | applied_cap Literal[5 values] (D-10 coverage)      |
| ARMSchedule     | 176-197  | loan, arm_terms, payments, reset_events, total_interest, final_payment_adjusted                 | Parallel BaseModel (NOT subclass) per D-03         |

## Stubs flipped + tests added

| Test                                                  | Status                | Plan-driven action                                                |
|-------------------------------------------------------|-----------------------|-------------------------------------------------------------------|
| `test_arm_terms_field_set`                            | xfail → PASS          | Full assertion on 9 fields + model_config + I-007 extra_forbidden |
| `test_arm_terms_missing_floor_rate_raises`            | xfail → PASS          | ValidationError(type='missing') on omitted floor_rate             |
| `test_note_rate_defaults_to_loan_annual_rate`         | xfail → PASS (partial) | Model-layer half only; Wave 3 replaces with engine assertion      |
| `test_arm_request_misaligned_index_path_raises`       | NEW (Plan 05-02)      | Period 62 on 5/1 ARM raises ValidationError                       |
| `test_arm_request_aligned_index_path_succeeds`        | NEW (Plan 05-02)      | Triggers 61 + 73 accepted on 5/1 ARM                              |
| `test_cli_misaligned_index_path_period_rejected`      | still xfail           | Stays xfail; Wave 4 (Plan 05-04) flips when CLI ships             |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Linter] Ruff I001 import-order auto-fix**
- **Found during:** Task 2 (tests/test_arm.py lint)
- **Issue:** Inline imports inside test functions (third-party + local mixed) tripped ruff's I001 import-block sort rule (3 occurrences: test_arm_terms_field_set, test_arm_terms_missing_floor_rate_raises, test_arm_request_misaligned_index_path_raises).
- **Fix:** `ruff check --fix tests/test_arm.py` reordered each import block alphabetically. No semantic change.
- **Files modified:** `tests/test_arm.py`
- **Commit:** Folded into `ed49c86` (single Task 2 commit; auto-fix happened pre-commit, not as a separate commit)

No other deviations. Plan executed exactly as written.

## Auth Gates

None encountered.

## Threat Model Coverage

All Plan 05-02 mitigations from `<threat_model>` landed:

| Threat ID | Mitigation                                                                              | Test Pin                                                  |
|-----------|-----------------------------------------------------------------------------------------|-----------------------------------------------------------|
| T-05-02   | model_validator raises ValueError on misaligned index_path period                       | `test_arm_request_misaligned_index_path_raises`           |
| T-05-16   | floor_rate has no default; ValidationError(type='missing') on omission                  | `test_arm_terms_missing_floor_rate_raises`                |
| T-05-17   | extra='forbid' on every model rejects unknown fields                                    | `test_arm_terms_field_set` (I-007 behavioral assertion)   |
| T-05-18   | ARMPayment(Payment) Pydantic v2 inheritance preserves Phase 1 Payment field shape       | `test_arm_terms_field_set` covers ARMTerms; ARMPayment shape exercised in Wave 3 |
| T-05-19   | model_config re-specified on ARMPayment for grep-discoverability + Pydantic v3 forward-compat | `grep -c 'model_config = ConfigDict(...)' lib/arm.py == 6` |

## ARM-01 closure status

ARM-01 is CLOSED at the model layer:
- 8 explicit fields + optional note_rate verified by `test_arm_terms_field_set`
- REQUIRED floor_rate verified by `test_arm_terms_missing_floor_rate_raises`
- ROADMAP SC-1 ("ARMTerms has 8 explicit fields, no implicit conventions") VERIFIED.

Engine-behavior closure (note_rate fallback to loan.annual_rate at lifetime ceiling math) lands in Wave 3 (Plan 05-03) when `build_arm_schedule` ships. The current `test_note_rate_defaults_to_loan_annual_rate` is a PARTIAL flip (model-layer assertion); Wave 3 will replace its body with the full engine assertion per its plan.

## Self-Check: PASSED

**Files created:**
- `/Users/cujo253/Documents/mortgage-ops/lib/arm.py` — FOUND (197 lines)
- `/Users/cujo253/Documents/mortgage-ops/.planning/phases/05-arm-modeling/05-02-SUMMARY.md` — FOUND (this file)

**Files modified:**
- `/Users/cujo253/Documents/mortgage-ops/tests/test_arm.py` — confirmed via `git log --oneline tests/test_arm.py`

**Commits:**
- `fc1002d` — `feat(05-02): add lib/arm.py Pydantic v2 model layer (ARM-01)` — FOUND
- `ed49c86` — `test(05-02): flip ARM-01 stubs and add ARMRequest validator tests` — FOUND

**Test counts:** Full suite final: `385 passed, 4 skipped, 29 xfailed, 0 failed, 0 errors` — matches plan expectation exactly.
