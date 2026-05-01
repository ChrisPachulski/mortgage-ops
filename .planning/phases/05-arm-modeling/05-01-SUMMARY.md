---
phase: 05
plan: 01
subsystem: arm-modeling
tags:
  - phase-05
  - arm-modeling
  - quantize-rate
  - d-14-promotion
  - hygiene-factor
dependency_graph:
  requires:
    - "05-00"  # Wave 0 test infrastructure
    - "lib/money.py existed with quantize_cents + MONEY_CONTEXT (Phase 1 D-08)"
    - "lib/affordability.py existed with private _quantize_rate (Phase 4 D-09)"
  provides:
    - "lib.money.quantize_rate(Decimal) -> Decimal — public 6-decimal ROUND_HALF_UP helper"
    - "lib.money._RATE_QUANTUM = Decimal('0.000001') — companion constant to CENT"
    - "Golden-pin test fixing ROUND_HALF_UP behavior at the 0.0654995 boundary"
  affects:
    - "lib/affordability.py — internal-only refactor; public evaluate() API unchanged"
    - "Phase 5 Wave 2 (Plan 05-02) — lib/arm.py can import quantize_rate from lib.money"
tech_stack:
  added: []
  patterns:
    - "D-14 promotion path: helper graduates from private (Phase 4 D-09) to public (Phase 5 D-14) on second-consumer rule"
key_files:
  created: []
  modified:
    - "lib/money.py — +27 lines (quantize_rate def + _RATE_QUANTUM Final constant + docstrings)"
    - "lib/affordability.py — −21 lines (drop _quantize_rate def + _RATE_QUANTUM constant + 3 unused imports; rename 4 call sites; add quantize_rate to lib.money import)"
    - "tests/test_money.py — +24 lines (test_quantize_rate_round_half_up with 7 assertions)"
decisions:
  - "Place quantize_rate AFTER quantize_cents in lib/money.py for read-order parity (CENT then 2-place fn, _RATE_QUANTUM then 6-place fn)"
  - "Remove ROUND_HALF_UP, localcontext, MONEY_CONTEXT imports from lib/affordability.py once they were stranded by the migration (Rule 3 ruff F401 hygiene)"
  - "Keep Final import in lib/affordability.py — 13 other Final-typed module constants still use it"
metrics:
  duration_minutes: 8
  completed: 2026-04-30
  tasks_completed: 4
  commits_created: 4  # 3 task commits + 1 docs commit
  test_count_before: 379_passed_4_skipped_32_xfailed
  test_count_after: 380_passed_4_skipped_32_xfailed
---

# Phase 5 Plan 01: Quantize Rate Promotion Summary

D-14 promoted Phase 4's private `_quantize_rate` helper from `lib/affordability.py` to a public `lib.money.quantize_rate(Decimal) -> Decimal`, pinned by a golden ROUND_HALF_UP boundary test, with zero regression to the Phase 4 (379+4) and Phase 3 (42) baselines.

## Tasks Completed

| # | Task                                                                 | Commit    | Outcome |
|---|----------------------------------------------------------------------|-----------|---------|
| 1 | Add quantize_rate + _RATE_QUANTUM to lib/money.py                    | `2c42a1f` | Public symbol exposed; mypy + ruff clean |
| 2 | Migrate lib/affordability.py — drop local def + rename 4 call sites  | `da315c9` | Pure-internal refactor; public API unchanged |
| 3 | Add golden-pin test for quantize_rate to tests/test_money.py         | `92eeb11` | 7 assertions, exact Decimal equality |
| 4 | Verify zero regression to Phase 4 + Phase 3 baselines                | (no code; verification only) | All gates green |

## Acceptance Gate Results

### Must-haves (from PLAN.md frontmatter)

| Gate | Expected | Actual | Status |
|------|----------|--------|--------|
| `lib.money` exposes public `quantize_rate(Decimal) -> Decimal` at 6 places, ROUND_HALF_UP, MONEY_CONTEXT | yes | yes | PASS |
| `lib/affordability.py` no longer defines `_quantize_rate` | def removed | `grep -c _quantize_rate` = 0 | PASS |
| All 4 prior call sites resolve to `lib.money.quantize_rate` via import | 4 call sites + 1 import = 5 matches | `grep -c quantize_rate` = 5 | PASS |
| Phase 4 suite (`tests/test_affordability.py`) passes 379 + 4 (zero regression) at file level | 78 passed + 4 skipped (file-level slice) | 78 passed + 4 skipped | PASS |
| Phase 3 suite (`tests/test_amortize.py`) still passes | 42 passed | 42 passed | PASS |
| `tests/test_money.py` has half-up boundary golden pin | 1 new test + 0.0654995 → 0.065500 | present + asserted | PASS |
| Wave 2/3 can import `quantize_rate` from `lib.money` without touching `lib.affordability` | public symbol | confirmed via `python -c 'from lib.money import quantize_rate'` | PASS |

### Verification commands (from PLAN.md `<verification>`)

```
pytest -q                 # 380 passed, 4 skipped, 32 xfailed, 0 failed, 0 errored
mypy --strict lib/money.py lib/affordability.py tests/test_money.py   # clean
ruff check lib/money.py lib/affordability.py tests/test_money.py      # clean
ruff format --check lib/money.py lib/affordability.py tests/test_money.py  # 3 files already formatted
```

## Test Counts

| Suite                          | Before (post-Wave 0) | After (Wave 1)        |
|--------------------------------|----------------------|-----------------------|
| `pytest -q` (full)             | 379 passed, 4 skipped, 32 xfailed | **380** passed, 4 skipped, 32 xfailed |
| `tests/test_money.py`          | 8 passed             | 9 passed              |
| `tests/test_affordability.py`  | 78 passed, 4 skipped | 78 passed, 4 skipped (unchanged) |
| `tests/test_amortize.py`       | 42 passed            | 42 passed (unchanged) |
| Wave 0 xfail count             | 32                   | 32 (no XPASS leak)    |

Net delta: **+1 passed, 0 failed, 0 errored, 0 XPASS leak** — exactly the plan's expected curve.

## File Line Deltas

| File                 | Before | After | Delta | Plan estimate | Notes |
|----------------------|-------:|------:|------:|--------------:|-------|
| `lib/money.py`       |     46 |    73 |   +27 | +18           | Extra +9 vs. estimate is the full docstrings on `_RATE_QUANTUM` + `quantize_rate`; symbol/behavior matches plan exactly |
| `lib/affordability.py` | 1513 | 1492  |   −21 | −15 to −19    | Beyond the 15-line `_quantize_rate` block, also removed 3 stranded imports (`ROUND_HALF_UP`, `localcontext`, `MONEY_CONTEXT`); see Deviations |
| `tests/test_money.py` |   70 |    94 |   +24 | +1 test       | 7 assertions + module docstring updates |

## Deviations

### Auto-fixed Issues

**1. [Rule 3 — Hygiene] Removed three stranded imports from `lib/affordability.py`**

- **Found during:** Task 2 (post-edit `ruff check`)
- **Issue:** Once the local `_quantize_rate` def was deleted, `from decimal import ROUND_HALF_UP, ..., localcontext` and `from lib.money import MONEY_CONTEXT, ...` left F401 unused-import errors. The plan called these out as a possibility ("also remove `from typing import Final` if it is now unused"); the actual stranded imports were `ROUND_HALF_UP`, `localcontext`, and `MONEY_CONTEXT` (the `Final` import remains used by 13 other constants).
- **Fix:** Edited `from decimal import ROUND_HALF_UP, Decimal, localcontext` → `from decimal import Decimal`; edited `from lib.money import MONEY_CONTEXT, quantize_cents, quantize_rate` → `from lib.money import quantize_cents, quantize_rate`.
- **Files modified:** `lib/affordability.py`
- **Commit:** `da315c9`
- **Verification:** Subsequent `mypy --strict` + `ruff check` clean; pre-commit hook passed.

No Rule 1 bugs. No Rule 2 missing-functionality. No Rule 4 architectural questions.

## Threat Mitigation Verification

| Threat | Mitigation in plan | Status |
|--------|--------------------|--------|
| T-05-08 Tampering (Phase 4 regression) | Full pytest must hold 379+4 byte-equivalent | PASS — `tests/test_affordability.py` 78+4 unchanged; full suite +1 new test only |
| T-05-13 Tampering (silent rounding-mode change) | Golden pin at 0.0654995 → 0.065500 | PASS — assertion present and passing |
| T-05-14 Information Disclosure (private import leak) | `_quantize_rate` symbol GONE | PASS — `grep -c '_quantize_rate' lib/affordability.py` = 0 |
| T-05-15 Repudiation (mypy --strict regression) | `mypy --strict` clean on all 3 files | PASS |

No new threat surface introduced by Wave 1 (pure-internal refactor; no new endpoints, auth paths, file access, or schema changes).

## Wave 2 Handoff

Plan `05-02` (ARMRequest model + ARM engine skeleton) can now `from lib.money import quantize_rate` directly. No further work in `lib/affordability.py` required for ARM consumption — the helper is the canonical money-discipline path.

## Self-Check: PASSED

- `lib/money.py` exists; `quantize_rate` exported (verified via `python -c 'from lib.money import quantize_rate'`)
- `lib/affordability.py` exists; no `_quantize_rate` remaining (verified via grep)
- `tests/test_money.py` exists; `test_quantize_rate_round_half_up` present and passing
- Commits `2c42a1f`, `da315c9`, `92eeb11` all present in `git log`
- Full suite: 380 passed + 4 skipped + 32 xfailed + 0 failed + 0 errored
- mypy + ruff + ruff-format clean across all 3 touched files
