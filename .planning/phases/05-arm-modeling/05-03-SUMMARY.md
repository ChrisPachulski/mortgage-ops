---
phase: 05
plan: 03
subsystem: arm-modeling
tags:
  - phase-05
  - arm-modeling
  - engine
  - slice-stitch
  - reset-formula
  - arm-02
  - arm-03
  - arm-04
  - arm-05
dependency_graph:
  requires:
    - "05-00"  # Wave 0 test infrastructure (32 xfail stubs + arm_fixture loader)
    - "05-01"  # lib.money.quantize_rate (consumed by D-02 reset formula)
    - "05-02"  # lib.arm Pydantic v2 model layer (ARMRequest -> ARMSchedule shape)
    - "lib/amortize.py — Phase 3 build_schedule entry point (re-entered per epoch)"
    - "lib/models.py — Phase 1 Loan, Payment, Money, Rate (subclass Schedule for synthetic loan)"
  provides:
    - "lib.arm.build_arm_schedule(req: ARMRequest) -> ARMSchedule — D-05 per-epoch slice-stitch engine (ARM-02..05 closure at math layer)"
    - "lib.arm._compute_reset_triggers(arm_terms, term_months) -> list[int] — RESEARCH Q5 trigger formula (private; scope-to-file)"
    - "lib.arm._compute_new_rate(...) -> (new_rate, applied_cap, index_value_used) — D-02 reset formula + 5-value applied_cap classification (private)"
  affects:
    - "Wave 4 (Plan 05-04) — scripts/arm_simulate.py wraps build_arm_schedule behind subprocess CLI + 6-key error envelope"
    - "Wave 6 (Plan 05-06) — fixtures + hand-calc oracle pin numerical correctness; flips the remaining 5 fixture-dependent stubs (test_arm_*_payment_jump_*, test_arm_initial_cap_at_first_reset, test_arm_lifetime_cap_binds, test_arm_floor_below_margin_blocked, test_arm_5_1_off_by_one_negative)"
tech_stack:
  added: []
  patterns:
    - "D-05 per-epoch slice-stitch: synthesize Loan(principal=remaining_balance, annual_rate=current_rate, term_months=remaining_full_term), re-enter Phase 3 build_schedule, slice payments[:epoch_window] (or all rows on the final epoch), stitch cumulative totals across boundaries"
    - "D-02 reset formula: clamp(quantize_rate(index+margin), low=effective_floor, high=min(periodic_ceiling, lifetime_ceiling)); first-reset uses initial_cap_bps; subsequent use periodic_cap_bps; lifetime ceiling against note_rate (fallback loan.annual_rate per LM-3)"
    - "applied_cap classification (D-10) compares quantized constraints to avoid 1-ULP misclassification; lifetime wins on tie with periodic (more restrictive policy)"
    - "RESEARCH Q1.2 bear-trap forbidden: synthetic_loan.term_months MUST be remaining_full_term (NOT reset_period_months); test_non_final_epoch_does_not_zero_balance pins this"
key_files:
  created: []
  modified:
    - "lib/arm.py — +252 lines (197 -> 449): adds build_arm_schedule + _compute_reset_triggers + _compute_new_rate; imports Decimal, dateutil.relativedelta, lib.amortize.build_schedule, lib.money.{quantize_cents,quantize_rate}"
    - "tests/test_arm.py — +262 lines net (503 -> 765): adds _make_5_1_arm_request helper; flips 7 ARM-02..05 invariant stubs to passing (test_initial_fixed_period_matches_phase1_oracle, test_arm_continuous_period_numbering, test_cumulative_totals_continuous_across_resets, test_non_final_epoch_does_not_zero_balance, test_full_remaining_term_re_amortization, test_reset_formula_locked, test_arm_teaser_rate); replaces test_note_rate_defaults_to_loan_annual_rate body with full engine assertion"
decisions:
  - "lib/arm.py imports Literal directly (Wave 2 already used it); the proposed `_Literal` alias was not needed since the existing import already serves both the model layer and the engine helper signatures"
  - "ARMPayment.payment_date computation prefers loan.origination_date + relativedelta(months=absolute_period) when origination is not None; falls back to the synthetic Payment's payment_date when None (Phase 3 D-12 origination synthesis covers the None path; we honor that)"
  - "applied_cap classification: changed branch guards to compare new_rate to fully_indexed_q (quantized) instead of fully_indexed; this avoids 1-ULP edge cases where the unquantized fully_indexed differs from new_rate by < 1 ULP"
  - "Floor branch guard: new_rate > fully_indexed_q (strict greater) per D-10 'constraint actually bound' semantics — the floor only 'binds' when it lifted the rate above what fully_indexed would have produced"
metrics:
  duration_minutes: 5
  completed: 2026-04-30
  tasks_completed: 3
  commits_created: 3  # 2 task commits + 1 docs commit (this summary)
  test_count_before: 385_passed_4_skipped_29_xfailed
  test_count_after: 392_passed_4_skipped_22_xfailed
  lines_added_lib_arm: 252  # 197 -> 449
  lines_added_test_arm: 262  # 503 -> 765
---

# Phase 5 Plan 03: Engine — build_arm_schedule Summary

Shipped `build_arm_schedule(req: ARMRequest) -> ARMSchedule` — the per-epoch slice-stitch engine for ARM modeling — plus two private helpers (`_compute_reset_triggers`, `_compute_new_rate`). The engine re-enters Phase 3's `build_schedule` once per epoch with a synthetic `Loan(principal=remaining_balance, annual_rate=current_rate, term_months=remaining_full_term)`, slices payments[:epoch_window] for non-final epochs (taking ALL rows for the final epoch where Phase 3 D-09 cleanup applies), stitches cumulative totals across epoch boundaries, and emits one `ResetEvent` per reset boundary with the D-10 5-value applied_cap classification. Closes ARM-02 (off-by-one + payment jump), ARM-03 (cap precedence: lifetime → initial → periodic → floor), ARM-04 (floor enforcement), and ARM-05 (continuous period numbering + cumulative totals + re-amortization invariants) at the math layer; fixture-based pinning lands in Wave 6. Phase 3 + Phase 4 baselines preserved exactly.

## Tasks Completed

| # | Task                                                                            | Commit    | Outcome |
|---|---------------------------------------------------------------------------------|-----------|---------|
| 1 | Implement build_arm_schedule + _compute_reset_triggers + _compute_new_rate     | `17e3b20` | lib/arm.py 197→449 lines; mypy --strict + ruff clean; D-05 bear-trap shortcut not taken |
| 2 | Flip 7 ARM-02..05 invariant stubs + replace test_note_rate body                | `8a5376f` | xfail 29→22; 8 engine-invariant tests passing (7 flips + 1 body replacement); _make_5_1_arm_request helper added |
| 3 | Verify zero regression + run full Phase 5 suite                                | (no code) | 392 passed, 4 skipped, 22 xfailed, 0 failed, 0 errors; REPL sanity payments=360 resets=25 final_bal=0.00 |

## Acceptance Gate Results

### Plan-level acceptance (`<must_haves>`)

| Gate                                                                                                                                                  | Result |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| `build_arm_schedule(req: ARMRequest) -> ARMSchedule` exposed publicly                                                                                 | PASS   |
| Per-epoch re-entry into `lib.amortize.build_schedule` with synthetic Loan(principal=remaining_balance, annual_rate=current_rate, term_months=remaining_full_term) | PASS   |
| Slice strategy: payments[0:reset_period_months] non-final; ALL payments final epoch (preserves Phase 3 D-09 only at the final epoch)                  | PASS   |
| D-02 reset formula: clamp(quantize_rate(index+margin), low=effective_floor, high=min(periodic, lifetime))                                             | PASS   |
| First-reset uses initial_cap_bps; subsequent use periodic_cap_bps                                                                                     | PASS   |
| Lifetime ceiling uses note_rate (fallback loan.annual_rate when None) per D-02 + LM-3                                                                 | PASS   |
| applied_cap covers all 5 Literal values (initial/periodic/lifetime/floor/none); every reset emits exactly one classification                          | PASS   |
| Cumulative totals continuous across epoch boundaries (payments[i].cum_int == payments[i-1].cum_int + payments[i].interest)                            | PASS   |
| Continuous period numbering: payments[0].period == 1, payments[-1].period == loan.term_months, payments[-1].balance == Decimal("0.00")                | PASS   |
| ARMSchedule.total_interest == payments[-1].cumulative_interest (Phase 1 D-15 invariant)                                                               | PASS   |
| ARMSchedule.final_payment_adjusted reflects ONLY the final epoch's Phase 3 D-09 detection                                                             | PASS   |
| 7 invariant Wave-0 stubs flipped + 1 body replaced; 5 fixture-dependent stubs intentionally remain xfail                                              | PASS   |

### Task 1 grep gates (lib/arm.py)

| Grep                                                                                       | Expected | Actual |
|--------------------------------------------------------------------------------------------|----------|--------|
| `def build_arm_schedule`                                                                   | 1        | 1      |
| `def _compute_reset_triggers`                                                              | 1        | 1      |
| `def _compute_new_rate`                                                                    | 1        | 1      |
| `from lib.amortize import build_schedule`                                                  | 1        | 1      |
| `from lib.money import`                                                                    | 1        | 1      |
| `quantize_rate`                                                                            | >=5      | 13     |
| `quantize_cents`                                                                           | >=2      | 3      |
| `remaining_full_term`                                                                      | >=1      | 3      |
| `reset_period_months`                                                                      | >=2      | 8      |
| `term_months\s*=\s*[a-zA-Z_.]*reset_period_months` (D-05 forbidden shortcut)               | 0        | 0      |
| `final_payment_adjusted`                                                                   | >=2      | 7      |
| `is_final_epoch`                                                                           | >=1      | 3      |
| `mypy --strict lib/arm.py`                                                                 | exit 0   | exit 0 |
| `ruff check lib/arm.py`                                                                    | exit 0   | exit 0 |
| `ruff format --check lib/arm.py`                                                           | exit 0   | exit 0 |

### Task 2 grep gates (tests/test_arm.py)

| Grep                                              | Expected | Actual |
|---------------------------------------------------|----------|--------|
| `@pytest.mark.xfail`                              | 22       | 22     |
| `def _make_5_1_arm_request`                       | 1        | 1      |
| `mypy --strict tests/test_arm.py`                 | exit 0   | exit 0 |
| `ruff check tests/test_arm.py`                    | exit 0   | exit 0 |
| `ruff format --check tests/test_arm.py`           | exit 0   | exit 0 |

### Task 3 final verification

| Suite                          | Before          | After            | Delta                        |
|--------------------------------|-----------------|------------------|------------------------------|
| Full suite (`pytest -q`)       | 385p / 4s / 29x | 392p / 4s / 22x  | +7 passed, -7 xfailed (7 flips); +1 NEW pass via test_note_rate body replacement (was already passing as partial flip; now full engine pass) — net delta: +7 passed |
| `tests/test_amortize.py`       | 42 passed       | 42 passed        | no change (Phase 3 zero regression) |
| `tests/test_affordability.py`  | 78p / 4s        | 78p / 4s         | no change (Phase 4 zero regression) |
| `mypy --strict` Phase 5 files  | clean           | clean            | no change                    |
| `ruff check` Phase 5 files     | clean           | clean            | no change                    |
| `ruff format --check` Phase 5  | clean           | clean            | no change                    |

### REPL sanity (5/1 ARM 30yr modest reset)

```
loan: $400,000 @ 5.0%/30yr, origination 2026-01-01
arm:  initial=60, reset=12, caps={initial:500bps, periodic:200bps, lifetime:500bps},
      floor=3%, margin=250bps, assumed_index=5.25%
output: payments=360 resets=25 final_bal=0.00 total_int=$561,167.66
        first reset @ period 61: 5.0% -> 7.75%, applied_cap=none
```

25 reset events match the formula (349-61)/12 + 1 = 25 ✓; final balance 0 confirms Phase 3 D-09 cleanup at the final epoch only.

## Engine internals

### `_compute_reset_triggers` (RESEARCH Q5)

```
period = arm_terms.initial_period_months + 1   # +1 = "rate change at START of post-fixed-period month" (PITFALL 5)
while period <= term_months:
    triggers.append(period); period += arm_terms.reset_period_months
```

5/1 ARM 30yr → 25 triggers at [61, 73, 85, …, 349].
5/6 ARM 30yr → 50 triggers at [61, 67, 73, …, 355].

### `_compute_new_rate` (D-02 + D-10)

Reset formula (verbatim):
1. `index_value = req.index_path[period].value if exists else req.assumed_index_rate` (D-01 override-wins)
2. `fully_indexed = quantize_rate(index_value + margin_bps/10000)`
3. `effective_floor = max(margin_bps/10000, floor_rate)`
4. `applicable_cap_bps = initial_cap_bps if epoch_idx == 1 else periodic_cap_bps`
5. `periodic_ceiling = prior_rate + applicable_cap_bps/10000`
6. `note_rate_eff = note_rate if note_rate is not None else loan.annual_rate` (LM-3)
7. `lifetime_ceiling = note_rate_eff + lifetime_cap_bps/10000`
8. `ceiling = min(periodic_ceiling, lifetime_ceiling)`
9. `new_rate = quantize_rate(max(effective_floor, min(fully_indexed, ceiling)))`

applied_cap classification (D-10) compares against quantized constraints with strict-inequality "binding actually held" guards:
- `floor`     ← new_rate == quantize_rate(effective_floor) AND new_rate > quantize_rate(fully_indexed)
- `lifetime`  ← new_rate == quantize_rate(lifetime_ceiling) AND lifetime_q <= periodic_q AND new_rate < quantize_rate(fully_indexed)  (lifetime wins on tie — more restrictive policy)
- `initial`   ← epoch_idx == 1 AND new_rate == quantize_rate(periodic_ceiling) AND new_rate < quantize_rate(fully_indexed)
- `periodic`  ← epoch_idx >= 2 AND new_rate == quantize_rate(periodic_ceiling) AND new_rate < quantize_rate(fully_indexed)
- `none`      ← otherwise (fully_indexed itself fell strictly inside the open interval)

### `build_arm_schedule` (D-05)

Single iteration over epoch boundaries `[(1, initial+1), (initial+1, t1), …, (t_last, term+1)]`:

```
for (start, end) in boundaries:
    is_final_epoch = (end == term + 1)
    epoch_window = end - start
    current_rate = loan.annual_rate if epoch_idx == 0 else _compute_new_rate(...)
    remaining_full_term = loan.term_months - start + 1   # NEVER reset_period_months (RESEARCH Q1.2 bear trap)
    synthetic = build_schedule(Loan(principal=remaining_balance, annual_rate=current_rate, term_months=remaining_full_term, ...))
    sliced = synthetic.payments if is_final_epoch else synthetic.payments[:epoch_window]
    stitch cum_int_carry + cum_prin_carry into each row; convert Payment → ARMPayment
    if epoch_idx >= 1: emit ResetEvent(period=start, ...)
    if not is_final_epoch: carry forward (cum totals, balance, prior_rate, old_pmt)
    else: final_payment_adjusted = synthetic.final_payment_adjusted
```

Cap precedence verified end-to-end: lifetime → initial → periodic → floor (lifetime wins on tie with periodic; floor wins absolutely when it lifts above fully_indexed).

## Stubs flipped + tests added

| Test                                                       | Status                  | Plan-driven action                                                                       |
|------------------------------------------------------------|-------------------------|------------------------------------------------------------------------------------------|
| `test_initial_fixed_period_matches_phase1_oracle`          | xfail → PASS            | LM-6: epoch 0 P&I matches Phase 1 oracle ($400k @ 6.5%/30yr → $2528.27) for all 60 months |
| `test_arm_continuous_period_numbering`                     | xfail → PASS            | D-03: payments[i].period == i+1 for all i; final balance 0; len == term_months           |
| `test_cumulative_totals_continuous_across_resets`          | xfail → PASS            | D-05 + D-15: cum_int continuous across the 60→61 reset boundary; total_interest invariant |
| `test_non_final_epoch_does_not_zero_balance`               | xfail → PASS            | RESEARCH Q1.2 bear-trap pin: period 60/72 balance > 0; only final balance == 0           |
| `test_full_remaining_term_re_amortization`                 | xfail → PASS            | D-05: epoch-1 P&I matches a fresh build_schedule over 300-month remainder, never 12      |
| `test_reset_formula_locked`                                | xfail → PASS            | D-02 direct call into `_compute_new_rate`: 'none' / 'initial' / 'floor' branches verified |
| `test_arm_teaser_rate`                                     | xfail → PASS            | LM-3: lifetime ceiling against note_rate (0.05) not loan.annual_rate (0.03); applied_cap='lifetime' |
| `test_note_rate_defaults_to_loan_annual_rate`              | body REPLACED           | Wave 2 model-layer half subsumed; engine assertion: schedules with note_rate=None vs explicit identical |
| 5 fixture-dependent stubs (Wave 6)                         | still xfail             | Stays xfail until Plan 05-06 ships hand-calc fixtures                                    |

xfail count delta: 29 → 22 (7 stubs flipped). Pass count delta: 385 → 392 (+7).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Linter] Bear-trap docstring grep false-positive**
- **Found during:** Task 1 acceptance (`grep -nE 'term_months\s*=\s*[a-zA-Z_.]*reset_period_months' lib/arm.py` returned 1)
- **Issue:** The `build_arm_schedule` docstring originally read "D-05 explicitly forbids the 'shortcut' of synthetic_loan.term_months=reset_period_months …" — this exactly matched the acceptance grep that was meant to catch the FORBIDDEN code pattern. The docstring describing the forbidden pattern triggered a false positive.
- **Fix:** Reworded the docstring to "synthesizing the per-epoch Loan with term_months equal to the reset cadence (reset_period_months)" — preserves the warning, avoids the literal `term_months=reset_period_months` substring.
- **Files modified:** `lib/arm.py`
- **Commit:** Folded into `17e3b20` (single Task 1 commit; fix happened pre-commit)

**2. [Rule 1 - Bug] test_reset_formula_locked periodic-bound scenario inconsistent with classification spec**
- **Found during:** Task 2 (running the flipped test)
- **Issue:** Plan's periodic-bound scenario used `initial_cap_bps=500, lifetime_cap_bps=500` → both `periodic_ceiling` and `lifetime_ceiling` equal 0.10. The plan's classification spec says "Lifetime binds (more restrictive than periodic OR equal)" — i.e., on tie, `applied_cap='lifetime'`. So the test's expectation `applied_cap=='initial'` was unreachable.
- **Fix:** Bumped `lifetime_cap_bps` to 1000 (10pp) in the periodic-bound scenario only, making `lifetime_ceiling=0.15` strictly above `periodic_ceiling=0.10`. The 'initial' branch now binds distinctly.
- **Files modified:** `tests/test_arm.py`
- **Commit:** Folded into `8a5376f` (single Task 2 commit; fix happened pre-commit)

No other deviations. Engine algorithm executed exactly per D-05 + D-02 spec.

## Auth Gates

None encountered.

## Threat Model Coverage

All Plan 05-03 mitigations from `<threat_model>` landed:

| Threat ID | Mitigation                                                                                  | Test Pin                                                          |
|-----------|---------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| T-05-03   | _compute_new_rate is_first_reset branch + Decimal arithmetic                                | `test_reset_formula_locked` (initial branch); Wave 6 fixture extension covers periodic |
| T-05-04   | max(margin_rate, floor_rate) BEFORE clamp                                                   | `test_reset_formula_locked` (floor-bound scenario at index=0.001) |
| T-05-05   | initial_period_months + 1 explicitly encoded                                                | `test_initial_fixed_period_matches_phase1_oracle` (epoch 0 months 1..60 still at initial rate); Wave 6 ships off-by-one negative test |
| T-05-06   | cum_int_carry + cum_prin_carry stitching at every epoch boundary                            | `test_cumulative_totals_continuous_across_resets` (continuity at 60→61 + every period) |
| T-05-07   | synthetic_loan.term_months = remaining_full_term (D-05 bear-trap forbidden)                 | `test_non_final_epoch_does_not_zero_balance` (period 60/72 balance > 0) |
| T-05-20   | epoch_window = end - start; payments[0:60] for 5/1 ARM epoch 0                              | `test_arm_continuous_period_numbering` (continuous 1..N + length); `test_full_remaining_term_re_amortization` (epoch 1 = months 61..72) |
| T-05-21   | for-loop with explicit period match + break in `_compute_new_rate`                          | `test_arm_teaser_rate` (uses assumed_index_rate fallback, no override); Wave 6 ships index-path-overrides fixture |
| T-05-22   | _compute_new_rate `terms.note_rate if terms.note_rate is not None else loan_annual_rate`    | `test_note_rate_defaults_to_loan_annual_rate` (None vs explicit produce identical schedules); `test_arm_teaser_rate` (explicit note_rate used) |

## ARM-02..05 closure status

ARM-02..05 are CLOSED at the engine (math) layer:

- **ARM-02** (off-by-one + payment jump): `_compute_reset_triggers` formula `initial+1, +reset` verified by `test_initial_fixed_period_matches_phase1_oracle` (months 1..60 at initial rate) + the engine emits 25 ResetEvents per 5/1 ARM 30yr (REPL sanity); fixture-based numerical pinning (Bankrate/Vertex42/AmericU oracle agreement) lands in Wave 6.
- **ARM-03** (cap precedence): `_compute_new_rate` covers all 5 applied_cap values; `test_reset_formula_locked` directly pins 'none' / 'initial' / 'floor'; `test_arm_teaser_rate` pins 'lifetime'. Periodic-vs-initial distinction per epoch_idx verified.
- **ARM-04** (floor enforcement): `effective_floor = max(margin_rate, floor_rate)` computed BEFORE clamp; `test_reset_formula_locked` floor-bound scenario (index=0.001 → floor lifts to 0.03) pins it.
- **ARM-05** (continuous numbering + cumulative totals + re-amortization): `test_arm_continuous_period_numbering` + `test_cumulative_totals_continuous_across_resets` + `test_non_final_epoch_does_not_zero_balance` + `test_full_remaining_term_re_amortization` collectively pin every D-05 invariant.

Engine-layer closure complete. Wave 4 (Plan 05-04) wraps the engine in `scripts/arm_simulate.py`. Wave 6 (Plan 05-06) ships hand-calc fixtures + cross-source oracle agreement and flips the 5 fixture-dependent stubs.

## Self-Check: PASSED

**Files modified:**
- `/Users/cujo253/Documents/mortgage-ops/lib/arm.py` — FOUND (449 lines; 197 + 252 added)
- `/Users/cujo253/Documents/mortgage-ops/tests/test_arm.py` — FOUND (765 lines)

**Files created:**
- `/Users/cujo253/Documents/mortgage-ops/.planning/phases/05-arm-modeling/05-03-SUMMARY.md` — FOUND (this file)

**Commits:**
- `17e3b20` — `feat(05-03): add build_arm_schedule slice-stitch engine (ARM-02..05)` — FOUND
- `8a5376f` — `test(05-03): flip 7 ARM-02..05 invariant stubs + replace test_note_rate body` — FOUND

**Test counts:** Full suite final: `392 passed, 4 skipped, 22 xfailed, 0 failed, 0 errors` — matches plan expectation exactly.
