---
phase: 05-arm-modeling
fixed_at: 2026-05-03T02:49:10Z
iteration: 1
fix_scope: critical_warning
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 5: ARM Modeling — Code Review Fix Report

**Fixed at:** 2026-05-03T02:49:10Z
**Source review:** `.planning/phases/05-arm-modeling/05-REVIEW.md`
**Iteration:** 1
**Scope:** critical + warning (5 of 12 findings — 7 INFO findings deferred)

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0
- Test baseline (full suite): 432 passed -> 436 passed; +4 net new regression tests (WR-02, WR-03, WR-04 fixture-binding net +1, WR-05 deep-nesting); 0 failures, 0 unexpected skips.

## Fixed Issues

### WR-01: Per-epoch payment_date is wrong when loan.origination_date is None

**Files modified:** `lib/arm.py`
**Commit:** `305d794`
**Applied fix:**
- Added `from datetime import UTC, datetime` import.
- At the top of `build_arm_schedule`, synthesize a single anchor: `origination_anchor = loan.origination_date or datetime.now(UTC).date()`. This mirrors `lib.amortize._build_fixed_monthly`'s D-12 idiom.
- Replaced the per-row conditional `loan.origination_date + relativedelta(...) if not None else p.payment_date` with the unconditional `origination_anchor + relativedelta(months=absolute_period)`. Every per-epoch row now offsets from the same anchor, eliminating the cross-epoch duplicated/non-monotonic `payment_date` defect and the cross-midnight drift between independent synthetic builds.

**Test result:** 52 passed, 1 xfailed (test_arm.py + test_cli_helpers.py); full suite: 432 passed unchanged at this stage.

---

### WR-02: ARMRequest does not reject duplicate index_path periods

**Files modified:** `lib/arm.py`, `tests/test_arm.py`
**Commit:** `a52235b`
**Applied fix:**
- Extended `ARMRequest._index_path_periods_align_to_reset_triggers` with a `seen_periods: set[int]` and a duplicate check raising `ValueError("index_path contains duplicate entries for period {n} ...")` so silent first-wins iteration is no longer accepted at construction.
- Added regression test `test_arm_request_duplicate_index_path_period_raises` mirroring `test_arm_request_misaligned_index_path_raises` — constructs a request with two entries at period 61 and asserts a `ValidationError` containing the word "duplicate".

**Test result:** 53 passed, 1 xfailed (test_arm.py + test_cli_helpers.py); full suite: 433 passed.

---

### WR-03: ARMTerms accepts floor_rate > lifetime ceiling without cross-field validation

**Files modified:** `lib/arm.py`, `tests/test_arm.py`
**Commit:** `ec8ac4f`
**Applied fix:**
- Added a second `ARMRequest` `model_validator(mode="after")` named `_floor_does_not_exceed_lifetime_ceiling`. It computes `note_rate_eff = arm_terms.note_rate or loan.annual_rate` (D-02 collapse), then `lifetime_ceiling = note_rate_eff + lifetime_cap_bps/10000` and `effective_floor = max(margin_bps/10000, floor_rate)`. Raises `ValueError(f"effective_floor ({...}) exceeds lifetime_ceiling ({...}); ...")` when the floor would silently force every reset to violate the lifetime cap.
- Added regression test `test_arm_request_floor_exceeds_lifetime_ceiling_raises` exercising `floor_rate=0.20` with `loan.annual_rate=0.05` + `lifetime_cap_bps=500` (lifetime_ceiling=0.10) — asserts `ValidationError` containing "lifetime_ceiling".
- Verified the cross-field check does NOT reject the existing `arm_floor_below_margin_blocked.json` fixture (effective_floor=0.04 vs lifetime_ceiling=0.10) — that fixture continues to pass.

**Test result:** 54 passed, 1 xfailed (test_arm.py + test_cli_helpers.py); full suite: 434 passed.

---

### WR-04: Three ARM fixtures are not bound to a named test

**Files modified:** `tests/test_arm.py`
**Commit:** `a0e8926`
**Applied fix (option a — wire each fixture into a test, per review's preferred path):**
- `arm_continuous_period_numbering.json`: rewrote `test_arm_continuous_period_numbering` to load via the `arm_fixture` callable and `_request_from_fixture(fx)`. Preserves the structural invariants (continuous numbering, length matches term, final balance==0) and adds spot-check `_assert_engine_matches_fixture_at_period` calls at periods 1, 60, 61, and the last period — wiring the fixture's hand-calc rows into actual assertions.
- `arm_teaser_rate.json`: rewrote `test_arm_teaser_rate` to load via the fixture loader. Preserves the load-bearing teaser-rate assertion (`first_reset.new_rate == 0.10` and `applied_cap == "lifetime"`) and adds explicit fixture-cross-validation against `expected.reset_events[0]` (new_rate, applied_cap, index_value_used) plus three per-payment spot-checks.
- `arm_index_path_overrides.json`: added new `test_arm_index_path_overrides` test. Asserts override-wins at periods 61 (0.06) and 73 (0.045), and fallback to `assumed_index_rate` (0.05) at period 85 — pinning D-01 override semantics. Cross-validates new_rate + applied_cap against the fixture's `expected.reset_events`.

**Test result:** 36 passed, 1 xfailed in test_arm.py (was 33 before this iteration → +3 tests rewritten/added); full suite: 435 passed.

---

### WR-05: find_json_float_loc has unbounded recursion on deeply nested JSON

**Files modified:** `scripts/_cli_helpers.py`, `tests/test_cli_helpers.py`
**Commits:** `3803828` (engine fix), `dd6e3f3` (regression test)
**Note on split:** the local `mypy --strict` pre-commit hook errors when the changed-file batch includes both `scripts/_cli_helpers.py` and `tests/test_cli_helpers.py` simultaneously (mypy resolves `_cli_helpers` under two module paths via `sys.path` injection in the test). To satisfy the hook, the engine fix and the new regression test were committed back-to-back as two atomic commits — both still belong to WR-05.
**Applied fix:**
- Replaced the recursive `_walk` inner function with an iterative LIFO stack walker. Children pushed in REVERSED order (`reversed(list(node.items()))` for dicts, `range(len(node)-1, -1, -1)` for lists) so LIFO pop visits keys/indices in original insertion / positional order — preserving the "first depth-first" semantic pinned by `test_multiple_floats_returns_first_depth_first`.
- Added regression test `test_deeply_nested_does_not_recurse` exercising 5000 levels of nested `[`...`]` (well past Python's default `sys.getrecursionlimit() ≈ 1000`). Previously this raised `RecursionError`; now returns `(loc=[0]*5000, val="1.5")`.

**Test result:** 20 passed in test_cli_helpers.py (was 19, +1 deep-nesting test); full suite: 436 passed.

## Skipped Issues

None — all 5 in-scope warnings were applied cleanly and verified with the project's pytest suite. The 7 INFO-level findings (IN-01 through IN-07) are out of scope for this iteration per the `critical_warning` `fix_scope` configuration.

---

_Fixed: 2026-05-03T02:49:10Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
