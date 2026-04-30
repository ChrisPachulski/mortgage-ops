---
phase: 05
plan: 03
type: execute
wave: 3
depends_on:
  - "05-00"
  - "05-01"
  - "05-02"
files_modified:
  - lib/arm.py
  - tests/test_arm.py
autonomous: true
requirements:
  - ARM-02
  - ARM-03
  - ARM-04
  - ARM-05
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
must_haves:
  truths:
    - "lib/arm.py exposes a public function build_arm_schedule(req: ARMRequest) -> ARMSchedule that ALWAYS returns a fully-populated ARMSchedule for any valid ARMRequest"
    - "build_arm_schedule re-enters lib.amortize.build_schedule once per epoch with synthetic Loan(principal=remaining_balance, annual_rate=current_rate, term_months=remaining_full_term) per D-05"
    - "Per-epoch slice strategy: take payments[0:reset_period_months] for non-final epochs; take ALL payments for final epoch (preserves Phase 3 D-09 cleanup ONLY at the final epoch per D-05)"
    - "Reset formula at every reset trigger period implements D-02 EXACTLY: fully_indexed = quantize_rate(index + margin/10000); effective_floor = max(margin/10000, floor_rate); ceiling = min(prior_rate + applicable_cap_bps/10000, note_rate + lifetime_cap_bps/10000); new_rate = quantize_rate(clamp(fully_indexed, low=effective_floor, high=ceiling))"
    - "First-reset uses initial_cap_bps; subsequent resets use periodic_cap_bps per D-02"
    - "Lifetime ceiling uses note_rate (or loan.annual_rate when note_rate is None) per D-02"
    - "applied_cap classification covers all 5 Literal values: 'initial', 'periodic', 'lifetime', 'floor', 'none' — every reset emits exactly one classification"
    - "Cumulative totals (cumulative_interest + cumulative_principal) are continuous across epoch boundaries: payments[i].cumulative_interest == payments[i-1].cumulative_interest + payments[i].interest exactly"
    - "Continuous period numbering: payments[0].period == 1, payments[-1].period == loan.term_months, payments[-1].balance == Decimal('0.00')"
    - "ARMSchedule.total_interest == payments[-1].cumulative_interest (Phase 1 D-15 invariant preserved)"
    - "ARMSchedule.final_payment_adjusted reflects ONLY the FINAL epoch's Phase 3 D-09 detection (intermediate epochs always carry forward)"
    - "Wave 0 stubs ARM-02 (4), ARM-03 (3), ARM-04 (1), ARM-05 (5) — total 13 — partially flip in this plan; the 5 stubs that depend on hand-calc fixtures (test_arm_*_payment_jump_*) stay xfail until Wave 6 ships fixtures; the 8 stubs that test invariants (test_full_remaining_term_re_amortization, test_arm_continuous_period_numbering, test_cumulative_totals_continuous_across_resets, test_non_final_epoch_does_not_zero_balance, test_initial_fixed_period_matches_phase1_oracle, test_reset_formula_locked, test_note_rate_defaults_to_loan_annual_rate replacement, test_arm_lifetime_cap_binds — wait, this last one IS fixture-dependent) flip via inline-constructed ARMRequests"
  artifacts:
    - path: "lib/arm.py"
      provides: "build_arm_schedule(req: ARMRequest) -> ARMSchedule + helper(s) for reset formula + applied_cap classification"
      contains: "def build_arm_schedule"
      min_lines: 250
    - path: "tests/test_arm.py"
      provides: "8 invariant tests flipped to passing using inline-constructed ARMRequests (no fixtures yet)"
      contains: "build_arm_schedule"
  key_links:
    - from: "build_arm_schedule"
      to: "lib.amortize.build_schedule"
      via: "per-epoch re-entry with synthetic Loan"
      pattern: "build_schedule\\("
    - from: "build_arm_schedule reset formula"
      to: "lib.money.quantize_rate"
      via: "rate quantize at end of each rate computation"
      pattern: "quantize_rate"
    - from: "ResetEvent.applied_cap"
      to: "Literal classification"
      via: "if/elif chain on (new_rate, effective_floor, periodic_ceiling, lifetime_ceiling)"
      pattern: "applied_cap"
---

<objective>
Ship `build_arm_schedule(req: ARMRequest) -> ARMSchedule` — the per-epoch slice-stitch engine that re-enters Phase 3's `lib.amortize.build_schedule` once per epoch with a synthetic `Loan(principal=remaining_balance, annual_rate=current_rate, term_months=remaining_full_term)`, slices off only the rows for the current epoch window, stitches cumulative totals across boundaries, and emits a `ResetEvent` per reset boundary.

Closes ARM-02, ARM-03, ARM-04, ARM-05 at the engine layer (fixture-based pinning happens in Wave 6).

Purpose: This is the math-correctness core of Phase 5. The slice-stitch design (D-05) is mandatory: it preserves every Phase 3 invariant (D-04 rate-per-period, D-07 composition order, D-09 final-payment cleanup, D-14 cumulative totals) without copying logic. The reset formula (D-02) is the single source of truth for new_rate computation; the `applied_cap` Literal classification enables D-10 citation-coverage testing.

The "non-final epoch shortcut trap" (RESEARCH Q1.2 bear trap) is explicitly forbidden: synthetic_loan.term_months MUST be `remaining_full_term`, NEVER `reset_period_months`. Otherwise Phase 3 D-09 cleanup fires at every epoch's last sliced row, silently zeroing the balance at every reset.

Output: `lib/arm.py` extended ~250 lines with `build_arm_schedule` + helpers; ~8 Wave-0 invariant stubs flipped to passing; the 5 fixture-dependent stubs (test_arm_*_payment_jump_*, test_arm_initial_cap_at_first_reset, test_arm_lifetime_cap_binds, test_arm_floor_below_margin_blocked, test_arm_5_1_off_by_one_negative) stay xfail until Wave 6 ships hand-calc fixtures.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-arm-modeling/05-CONTEXT.md
@.planning/phases/05-arm-modeling/05-RESEARCH.md
@.planning/phases/05-arm-modeling/05-PATTERNS.md
@.planning/phases/05-arm-modeling/05-VALIDATION.md
@CLAUDE.md
@lib/amortize.py
@lib/models.py
@lib/money.py
@lib/arm.py
@tests/fixtures/golden_pmt.json

<interfaces>
Phase 3 build_schedule entry point (lib/amortize.py — DO NOT modify):

```python
def build_schedule(
    loan: Loan,
    frequency: Literal["monthly", "biweekly"] = "monthly",
    biweekly_mode: Literal["true", "half-monthly"] | None = None,
    extra_principal: Sequence[ExtraPrincipalEntry] = (),
) -> Schedule:
    """Returns Schedule with payments: list[Payment], total_interest, monthly_pi,
    final_payment_adjusted (D-10). Each Payment has cumulative_interest +
    cumulative_principal (D-14) populated relative to the call (zeros at period 1).
    """
```

D-02 reset formula (CONTEXT.md lines 70-91; RESEARCH §Q9 + Code Example 2):

```
At each reset trigger period (epoch_idx >= 1):
    index = req.index_path[period].value if period in req.index_path else req.assumed_index_rate
    fully_indexed = quantize_rate(index + (Decimal(margin_bps) / Decimal("10000")))
    effective_floor = max(Decimal(margin_bps) / Decimal("10000"), arm_terms.floor_rate)
    is_first_reset = (epoch_idx == 1)
    applicable_cap_bps = arm_terms.initial_cap_bps if is_first_reset else arm_terms.periodic_cap_bps
    periodic_ceiling = prior_rate + (Decimal(applicable_cap_bps) / Decimal("10000"))
    note_rate_eff = arm_terms.note_rate if arm_terms.note_rate is not None else loan.annual_rate
    lifetime_ceiling = note_rate_eff + (Decimal(arm_terms.lifetime_cap_bps) / Decimal("10000"))
    ceiling = min(periodic_ceiling, lifetime_ceiling)
    new_rate_unquantized = max(effective_floor, min(fully_indexed, ceiling))
    new_rate = quantize_rate(new_rate_unquantized)
```

applied_cap classification (D-10 + LM-5):

```
# Compare new_rate (already quantized) to each constraint (also quantized for consistency).
floor_q = quantize_rate(effective_floor)
periodic_q = quantize_rate(periodic_ceiling)
lifetime_q = quantize_rate(lifetime_ceiling)

if new_rate == floor_q:
    applied_cap = "floor"
elif new_rate == lifetime_q and lifetime_q <= periodic_q:
    # Lifetime binds (more restrictive than periodic OR equal)
    applied_cap = "lifetime"
elif new_rate == periodic_q:
    applied_cap = "initial" if epoch_idx == 1 else "periodic"
else:
    # new_rate strictly between floor and ceiling — fully_indexed itself
    applied_cap = "none"
```

Reset trigger formula (RESEARCH §Q5):

```
triggers = []
period = arm_terms.initial_period_months + 1
while period <= loan.term_months:
    triggers.append(period)
    period += arm_terms.reset_period_months
# 5/1 ARM 30yr: [61, 73, 85, 97, ..., 349]
# 5/6 ARM 30yr: [61, 67, 73, 79, ..., 355]
```

Epoch boundaries (start, end) — half-open intervals:

```
boundaries = [(1, initial_period_months + 1)]
for i, t in enumerate(triggers):
    next_start = triggers[i + 1] if i + 1 < len(triggers) else loan.term_months + 1
    boundaries.append((t, next_start))
# Final epoch ends at loan.term_months + 1 (exclusive); slice takes ALL synthetic rows.
```

Slice-stitch invariant (RESEARCH §Q1):

```
For each epoch:
    remaining_full_term = loan.term_months - start + 1   # e.g., epoch starting at 61 in 30yr -> 300
    synthetic_loan = Loan(principal=remaining_balance, annual_rate=current_rate, term_months=remaining_full_term, ...)
    synthetic = build_schedule(synthetic_loan, frequency='monthly', biweekly_mode=None, extra_principal=())

    epoch_window = end - start
    is_final_epoch = (end == loan.term_months + 1)
    sliced = synthetic.payments[:epoch_window if not is_final_epoch else len(synthetic.payments)]

    for i, p in enumerate(sliced):
        absolute_period = start + i
        cum_int_total = quantize_cents(cum_int_carry + p.cumulative_interest)
        cum_prin_total = quantize_cents(cum_prin_carry + p.cumulative_principal)
        arm_payments.append(ARMPayment(
            period=absolute_period,
            payment_date=loan.origination_date + relativedelta(months=absolute_period),
            payment=p.payment, principal=p.principal, interest=p.interest,
            extra_principal=p.extra_principal, balance=p.balance,
            cumulative_interest=cum_int_total, cumulative_principal=cum_prin_total,
            rate_in_effect=current_rate,
        ))

    # End-of-epoch carry update (only if NOT final epoch)
    cum_int_carry = arm_payments[-1].cumulative_interest
    cum_prin_carry = arm_payments[-1].cumulative_principal
    remaining_balance = arm_payments[-1].balance

    # final_payment_adjusted bubbles up ONLY from the final epoch's synthetic schedule
    if is_final_epoch:
        final_payment_adjusted = synthetic.final_payment_adjusted
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement build_arm_schedule + reset_formula + applied_cap classification helpers in lib/arm.py</name>
  <files>lib/arm.py</files>
  <read_first>
    - lib/arm.py (Wave 2 state — has 6 models, no engine yet)
    - lib/amortize.py:1-100 (imports + module docstring + build_schedule signature) for the entry-point contract
    - lib/amortize.py:295-383 (_build_fixed_monthly per-period loop) — reference for how Phase 3 produces Schedule.payments + cum_int + cum_prin + D-09 cleanup
    - lib/affordability.py:174-187 (imports block) for import order convention
    - 05-CONTEXT.md D-02, D-03, D-05, D-15 — locked engine behavior
    - 05-RESEARCH.md §Q1 (slice-stitch verified by direct lib/amortize.py read), §Q9 (Code Example 2 lines 520-632 — full skeleton)
    - 05-PATTERNS.md "Pattern 4: Per-period iteration with cumulative-totals slice-stitch"
  </read_first>
  <action>
    Append the engine to lib/arm.py AFTER the 6 model classes from Wave 2. The engine consists of:
    1. `_compute_reset_triggers(arm_terms, term_months) -> list[int]` — pure-function helper
    2. `_compute_new_rate(...)` — D-02 reset formula (returns new_rate + applied_cap + index_value_used + ceiling_components for ResetEvent)
    3. `build_arm_schedule(req: ARMRequest) -> ARMSchedule` — main engine

    **Update imports at top of file** — add the new imports needed:

    Append to the existing import block (after `from lib.models import Loan, Money, Payment, Rate`):

    ```
    from datetime import date as _date  # noqa: F401  (unused now; engine uses below)
    from decimal import Decimal
    from typing import Literal as _Literal  # already imported as Literal — alias for clarity if needed; remove if unused

    from dateutil.relativedelta import relativedelta

    from lib.amortize import build_schedule
    from lib.money import quantize_cents, quantize_rate
    ```

    Clean up unused imports (ruff F401 will flag any unused). The actual import additions needed are:
    - `from decimal import Decimal`
    - `from dateutil.relativedelta import relativedelta`
    - `from lib.amortize import build_schedule`
    - `from lib.money import quantize_cents, quantize_rate`

    The existing `Literal` import from `typing` is already there from Wave 2 (used by ResetEvent.applied_cap). The existing `from lib.models import Loan, Money, Payment, Rate` is already there. The `pydantic` imports are already there.

    **Append helper 1: `_compute_reset_triggers`** (private helper, scope-to-file):

    ```
    def _compute_reset_triggers(arm_terms: ARMTerms, term_months: int) -> list[int]:
        """Return the list of reset trigger periods for an ARM.

        Per RESEARCH §Q5: triggers = [initial_period_months + 1, +reset_period_months, ...]
        up to and including term_months. The +1 implements the "rate change applies at
        START of post-fixed-period month" off-by-one (PITFALL 5; ROADMAP SC-2/SC-3).

        5/1 ARM 30yr (initial=60, reset=12, term=360) -> [61, 73, 85, ..., 349].
        5/6 ARM 30yr (initial=60, reset=6,  term=360) -> [61, 67, 73, ..., 355].
        """
        triggers: list[int] = []
        period = arm_terms.initial_period_months + 1
        while period <= term_months:
            triggers.append(period)
            period += arm_terms.reset_period_months
        return triggers
    ```

    **Append helper 2: `_compute_new_rate`** — implements D-02 verbatim:

    ```
    def _compute_new_rate(
        *,
        prior_rate: Rate,
        epoch_idx: int,
        period: int,
        req: ARMRequest,
        loan_annual_rate: Rate,
    ) -> tuple[Rate, _Literal["initial", "periodic", "lifetime", "floor", "none"], Rate]:
        """Compute the new rate at a reset trigger period per D-02.

        Returns (new_rate, applied_cap, index_value_used).

        Formula (D-02 verbatim):
            index = req.index_path[period].value if period in index_path else req.assumed_index_rate
            fully_indexed = quantize_rate(index + margin_bps/10000)
            effective_floor = max(margin_bps/10000, floor_rate)
            applicable_cap_bps = initial_cap_bps if epoch_idx == 1 else periodic_cap_bps
            periodic_ceiling = prior_rate + applicable_cap_bps/10000
            note_rate_eff = note_rate if note_rate is not None else loan.annual_rate
            lifetime_ceiling = note_rate_eff + lifetime_cap_bps/10000
            ceiling = min(periodic_ceiling, lifetime_ceiling)
            new_rate = quantize_rate(clamp(fully_indexed, low=effective_floor, high=ceiling))

        applied_cap classification (D-10):
            "floor"     if new_rate == quantize_rate(effective_floor)
            "lifetime"  if new_rate == quantize_rate(lifetime_ceiling) AND lifetime <= periodic
            "initial"   if epoch_idx == 1 AND new_rate == quantize_rate(periodic_ceiling)
            "periodic"  if epoch_idx >= 2 AND new_rate == quantize_rate(periodic_ceiling)
            "none"      otherwise (fully_indexed itself fell strictly inside the open interval)
        """
        terms = req.arm_terms
        # Step 1: resolve index value for this period (override-wins per D-01)
        index_value = req.assumed_index_rate
        for entry in req.index_path:
            if entry.period == period:
                index_value = entry.value
                break

        # Step 2: compute the candidate rate components (all using Decimal-from-bps, never floats)
        margin_rate = Decimal(terms.margin_bps) / Decimal("10000")
        fully_indexed = quantize_rate(index_value + margin_rate)

        effective_floor = max(margin_rate, terms.floor_rate)

        is_first_reset = epoch_idx == 1
        applicable_cap_bps = terms.initial_cap_bps if is_first_reset else terms.periodic_cap_bps
        periodic_ceiling = prior_rate + (Decimal(applicable_cap_bps) / Decimal("10000"))

        note_rate_eff = terms.note_rate if terms.note_rate is not None else loan_annual_rate
        lifetime_ceiling = note_rate_eff + (Decimal(terms.lifetime_cap_bps) / Decimal("10000"))

        ceiling = min(periodic_ceiling, lifetime_ceiling)

        # Step 3: clamp + final quantize
        # Note: max(low, min(value, high)) implements clamp without an extra Python helper.
        clamped = max(effective_floor, min(fully_indexed, ceiling))
        new_rate = quantize_rate(clamped)

        # Step 4: classify which constraint bound new_rate (for ResetEvent.applied_cap + D-10).
        # Compare quantized values (avoid 1-ULP misses).
        floor_q = quantize_rate(effective_floor)
        periodic_q = quantize_rate(periodic_ceiling)
        lifetime_q = quantize_rate(lifetime_ceiling)

        applied_cap: _Literal["initial", "periodic", "lifetime", "floor", "none"]
        if new_rate == floor_q and new_rate < quantize_rate(fully_indexed):
            # Floor lifted the rate above the unconstrained fully_indexed value.
            applied_cap = "floor"
        elif new_rate == lifetime_q and lifetime_q <= periodic_q and new_rate < quantize_rate(fully_indexed):
            # Lifetime ceiling held below fully_indexed AND was the binding (smaller) ceiling.
            applied_cap = "lifetime"
        elif new_rate == periodic_q and new_rate < quantize_rate(fully_indexed):
            # Periodic ceiling held below fully_indexed.
            applied_cap = "initial" if is_first_reset else "periodic"
        else:
            applied_cap = "none"

        return new_rate, applied_cap, index_value
    ```

    **Append the main engine `build_arm_schedule`** — implements D-05 slice-stitch:

    ```
    def build_arm_schedule(req: ARMRequest) -> ARMSchedule:
        """Build an ARM amortization schedule per D-05 per-epoch slice-stitch (ARM-02..05).

        Algorithm:
            1. Compute reset trigger periods (RESEARCH §Q5 formula).
            2. For each epoch:
                a. Compute current_rate (epoch 0 = loan.annual_rate; epoch >=1 = D-02 reset formula).
                b. Synthesize a Loan with principal=remaining_balance, annual_rate=current_rate,
                   term_months=remaining_full_term (NOT reset_period_months — the bear trap from
                   RESEARCH Q1.2). Re-enter Phase 3's build_schedule.
                c. Slice synthetic.payments[:epoch_window] for non-final epochs;
                   take ALL rows for the final epoch (which is where Phase 3 D-09 cleanup applies).
                d. Stitch each sliced row's cumulative_interest + cumulative_principal by adding
                   the prior epoch's terminal cum totals.
                e. Convert to ARMPayment with rate_in_effect = current_rate.
                f. Carry remaining_balance forward (only for non-final epochs).
            3. Record one ResetEvent per reset trigger period.
            4. Final-epoch only: bubble up final_payment_adjusted from the synthetic schedule.

        D-05 explicitly forbids the "shortcut" of synthetic_loan.term_months=reset_period_months
        because that fires Phase 3's D-09 cleanup at every epoch end — silently zeroing the
        balance at every reset (RESEARCH Q1.2 bear trap).

        Phase 1 D-15 invariant preserved: ARMSchedule.total_interest == payments[-1].cumulative_interest.
        """
        loan = req.loan
        terms = req.arm_terms

        # Compute reset triggers + epoch boundaries.
        triggers = _compute_reset_triggers(terms, loan.term_months)
        # boundaries: list of (start_period, end_period_exclusive) per epoch.
        boundaries: list[tuple[int, int]] = [(1, terms.initial_period_months + 1)]
        for i, t in enumerate(triggers):
            next_start = triggers[i + 1] if i + 1 < len(triggers) else loan.term_months + 1
            boundaries.append((t, next_start))

        # Iteration state
        arm_payments: list[ARMPayment] = []
        reset_events: list[ResetEvent] = []
        remaining_balance: Money = loan.principal
        prior_rate: Rate = loan.annual_rate
        current_rate: Rate = loan.annual_rate
        cum_int_carry: Money = Decimal("0.00")
        cum_prin_carry: Money = Decimal("0.00")
        final_payment_adjusted: bool = False
        old_pmt_for_next_reset: Money = Decimal("0.00")  # populated at end of each non-final epoch

        for epoch_idx, (start, end) in enumerate(boundaries):
            epoch_window = end - start
            is_final_epoch = end == loan.term_months + 1

            # Step 2a: compute current_rate
            applied_cap_for_event: _Literal["initial", "periodic", "lifetime", "floor", "none"] = "none"
            index_value_used: Rate = req.assumed_index_rate  # placeholder for epoch 0 (no reset event)
            if epoch_idx == 0:
                current_rate = loan.annual_rate
            else:
                current_rate, applied_cap_for_event, index_value_used = _compute_new_rate(
                    prior_rate=prior_rate,
                    epoch_idx=epoch_idx,
                    period=start,
                    req=req,
                    loan_annual_rate=loan.annual_rate,
                )

            # Step 2b: synthetic Loan over the FULL remaining term (D-05; never reset_period_months).
            remaining_full_term = loan.term_months - start + 1
            synthetic_loan = Loan(
                principal=remaining_balance,
                annual_rate=current_rate,
                term_months=remaining_full_term,
                origination_date=loan.origination_date,  # date offset applied below per row
                loan_type="arm",
            )
            synthetic = build_schedule(
                synthetic_loan,
                frequency="monthly",
                biweekly_mode=None,
                extra_principal=(),
            )

            # Step 2c: slice
            if is_final_epoch:
                sliced = synthetic.payments
            else:
                sliced = synthetic.payments[:epoch_window]

            # Step 2d + 2e: stitch + convert to ARMPayment
            for i, p in enumerate(sliced):
                absolute_period = start + i
                stitched_cum_int = quantize_cents(cum_int_carry + p.cumulative_interest)
                stitched_cum_prin = quantize_cents(cum_prin_carry + p.cumulative_principal)
                arm_payments.append(
                    ARMPayment(
                        period=absolute_period,
                        payment_date=loan.origination_date + relativedelta(months=absolute_period),
                        payment=p.payment,
                        principal=p.principal,
                        interest=p.interest,
                        extra_principal=p.extra_principal,
                        balance=p.balance,
                        cumulative_interest=stitched_cum_int,
                        cumulative_principal=stitched_cum_prin,
                        rate_in_effect=current_rate,
                    )
                )

            # Step 3: emit ResetEvent (only for epoch >= 1; epoch 0 is the initial fixed period)
            if epoch_idx >= 1:
                # old_pmt is the LAST payment of the prior epoch; new_pmt is the FIRST of this epoch.
                new_pmt = sliced[0].payment
                reset_events.append(
                    ResetEvent(
                        period=start,
                        old_rate=prior_rate,
                        new_rate=current_rate,
                        old_pmt=old_pmt_for_next_reset,
                        new_pmt=new_pmt,
                        index_value_used=index_value_used,
                        applied_cap=applied_cap_for_event,
                    )
                )

            # Step 2f: carry forward (for non-final epochs)
            if not is_final_epoch:
                cum_int_carry = arm_payments[-1].cumulative_interest
                cum_prin_carry = arm_payments[-1].cumulative_principal
                remaining_balance = arm_payments[-1].balance
                old_pmt_for_next_reset = arm_payments[-1].payment
                prior_rate = current_rate
            else:
                # Step 4: final_payment_adjusted bubbles up only from the final epoch's synthetic.
                final_payment_adjusted = synthetic.final_payment_adjusted

        return ARMSchedule(
            loan=loan,
            arm_terms=terms,
            payments=arm_payments,
            reset_events=reset_events,
            total_interest=arm_payments[-1].cumulative_interest,  # Phase 1 D-15 invariant
            final_payment_adjusted=final_payment_adjusted,
        )
    ```

    Notes:
    - Use `_Literal` alias for typing only inside helper signatures (or import `Literal` directly — your call); ensure mypy --strict + ruff F401 happy.
    - The `_compute_new_rate` helper returns the index_value_used so the engine can populate ResetEvent.index_value_used without re-resolving.
    - The `applied_cap == "none"` branch covers (a) modest reset where new_rate == fully_indexed inside open interval AND (b) the rare boundary case where new_rate equals one of the constraints but the constraint did NOT bind (i.e., fully_indexed already equaled the constraint). The strict inequality `new_rate < quantize_rate(fully_indexed)` in the binding branches enforces "constraint actually bound" semantics.
    - LM-5 fixture-construction note: Wave 6 (Plan 05-06) constructs `arm_5_1_payment_jump_at_61.json` numbers explicitly so new_rate falls in the strict open interval (`applied_cap == "none"`).
  </action>
  <verify>
    <automated>python -c "from lib.arm import build_arm_schedule, _compute_reset_triggers, _compute_new_rate, ARMRequest, ARMTerms, ARMPayment, ARMSchedule, ResetEvent, IndexPathEntry; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def build_arm_schedule' lib/arm.py` returns 1
    - `grep -c 'def _compute_reset_triggers' lib/arm.py` returns 1
    - `grep -c 'def _compute_new_rate' lib/arm.py` returns 1
    - `grep -c 'from lib.amortize import build_schedule' lib/arm.py` returns 1
    - `grep -c 'from lib.money import' lib/arm.py` returns 1 (single import line)
    - `grep -c 'quantize_rate' lib/arm.py` returns at least 5 (used in fully_indexed, new_rate, floor_q, periodic_q, lifetime_q)
    - `grep -c 'quantize_cents' lib/arm.py` returns at least 2 (used in stitching cum_int + cum_prin)
    - `grep -c 'remaining_full_term' lib/arm.py` returns at least 1 (D-05 explicitly forbidden shortcut not taken)
    - `grep -c 'reset_period_months' lib/arm.py` returns at least 2 (used in trigger formula + carry; NOT used as synthetic_loan.term_months)
    - `grep -nE 'term_months\s*=\s*[a-zA-Z_.]*reset_period_months' lib/arm.py` returns 0 (the bear-trap shortcut is NOT taken — also rejects qualified forms like `term_months=req.arm_terms.reset_period_months`)
    - `grep -c 'final_payment_adjusted' lib/arm.py` returns at least 2 (mentioned in ARMSchedule field + engine bubble-up)
    - `grep -c 'is_final_epoch' lib/arm.py` returns at least 1
    - `python -c 'from lib.arm import build_arm_schedule; print(build_arm_schedule.__doc__[:50])'` exits 0
    - `mypy --strict lib/arm.py` exits 0
    - `ruff check lib/arm.py` exits 0
    - `ruff format --check lib/arm.py` exits 0
  </acceptance_criteria>
  <done>
    lib/arm.py has build_arm_schedule + 2 helpers; engine importable; mypy + ruff clean; D-05 bear-trap shortcut not taken.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip 8 invariant Wave-0 stubs in tests/test_arm.py to passing tests using inline-constructed ARMRequests</name>
  <files>tests/test_arm.py</files>
  <read_first>
    - tests/test_arm.py (Wave 2 state — 29 xfails after Plan 05-02 flipped 3)
    - tests/fixtures/golden_pmt.json (the $400k @ 6.5%/30yr → $2528.27 anchor)
    - 05-VALIDATION.md "Phase Requirements → Test Map" rows for ARM-05
    - 05-RESEARCH.md §LM-6 "Phase 1 oracle anchor reuse for epoch 0"
    - 05-RESEARCH.md §Q1 "Q1.2 bear trap: non-final epoch's last sliced row has balance > 0.00"
  </read_first>
  <action>
    Flip exactly 8 invariant-style Wave-0 stubs to passing tests. These 8 tests do NOT depend on Wave-6 hand-calc fixtures because they assert engine invariants that hold for any well-formed ARMRequest. Wave 6 (Plan 05-06) flips the remaining 5 fixture-dependent stubs (test_arm_*_payment_jump_*, test_arm_initial_cap_at_first_reset, test_arm_lifetime_cap_binds, test_arm_floor_below_margin_blocked, test_arm_5_1_off_by_one_negative).

    For each flip, REMOVE the `@pytest.mark.xfail(strict=True, reason=...)` decorator and replace the body. Stubs to flip in this plan:

    1. `test_initial_fixed_period_matches_phase1_oracle` (ARM-05; LM-6) — uses Phase 1 golden_pmt.json
    2. `test_arm_continuous_period_numbering` (ARM-05) — invariant
    3. `test_cumulative_totals_continuous_across_resets` (ARM-05) — invariant
    4. `test_non_final_epoch_does_not_zero_balance` (ARM-05; RESEARCH Q1.2 bear-trap test) — invariant
    5. `test_full_remaining_term_re_amortization` (ARM-05) — invariant + comparison against synthetic
    6. `test_reset_formula_locked` (ARM-03) — direct call into `_compute_new_rate` helper
    7. `test_note_rate_defaults_to_loan_annual_rate` (ARM-01; engine half — Wave 2 already flipped the model half; this REPLACES that flip with the full engine assertion)
    8. `test_arm_teaser_rate` (cross-cutting; D-02 + LM-3) — engine substitutes note_rate (not loan.annual_rate) for lifetime base

    Use a shared `_make_5_1_arm_request(...)` helper at the top of the test file to avoid duplicating ARMRequest construction. Define it once after the imports + module constants:

    ```
    def _make_5_1_arm_request(
        principal: str = "400000.00",
        annual_rate: str = "0.065000",
        term_months: int = 360,
        floor_rate: str = "0.030000",
        margin_bps: int = 250,
        initial_cap_bps: int = 500,
        periodic_cap_bps: int = 200,
        lifetime_cap_bps: int = 500,
        assumed_index_rate: str = "0.050000",
        index_path_entries: list[tuple[int, str]] | None = None,
        note_rate: str | None = None,
    ) -> "ARMRequest":  # type: ignore[name-defined]
        """Construct a canonical 5/1 ARM ARMRequest for invariant tests.

        Used across the Wave 3 invariant tests + Wave 6 fixture tests. Defaults match
        the canonical scenario in 05-CONTEXT.md D-09 / RESEARCH LM-5 (modest reset
        whose new_rate falls in the open interval, applied_cap == 'none').
        """
        from datetime import date
        from decimal import Decimal
        from lib.arm import ARMRequest, ARMTerms, IndexPathEntry
        from lib.models import Loan
        loan = Loan(
            principal=Decimal(principal),
            annual_rate=Decimal(annual_rate),
            term_months=term_months,
            origination_date=date(2026, 1, 1),
            loan_type="arm",
        )
        terms = ARMTerms(
            initial_period_months=60,
            reset_period_months=12,
            initial_cap_bps=initial_cap_bps,
            periodic_cap_bps=periodic_cap_bps,
            lifetime_cap_bps=lifetime_cap_bps,
            floor_rate=Decimal(floor_rate),
            margin_bps=margin_bps,
            index_series_id="MORTGAGE30US",
            note_rate=Decimal(note_rate) if note_rate is not None else None,
        )
        index_path = (
            [IndexPathEntry(period=p, value=Decimal(v)) for p, v in (index_path_entries or [])]
        )
        return ARMRequest(
            loan=loan,
            arm_terms=terms,
            assumed_index_rate=Decimal(assumed_index_rate),
            index_path=index_path,
        )
    ```

    Now flip each stub:

    **Flip 1: test_initial_fixed_period_matches_phase1_oracle**

    Remove decorator. Body:

    ```
    """ARM-05 + LM-6: First epoch matches Phase 1 oracle ($400k @ 6.5%/30yr → $2528.27 P&I).

    Direct cross-phase oracle anchor reuse. The initial fixed period (months 1..60)
    must produce identical P&I to Phase 3's _build_fixed_monthly with the same
    Loan(principal=400000, annual_rate=0.065, term_months=360).
    """
    from decimal import Decimal
    from lib.arm import build_arm_schedule
    fx = golden_fixture("computed_400k_30yr")
    req = _make_5_1_arm_request(
        principal=fx["principal"],
        annual_rate=fx["annual_rate"],
        term_months=fx["term_months"],
    )
    schedule = build_arm_schedule(req)
    expected_pi = Decimal(fx["expected_monthly_pi"])
    # Every payment in epoch 0 (months 1..60) must equal the Phase 1 oracle P&I exactly.
    for i in range(60):
        assert schedule.payments[i].payment == expected_pi, (
            f"epoch 0 month {i+1}: got {schedule.payments[i].payment}, expected {expected_pi}"
        )
    # Last month of fixed period:
    assert schedule.payments[59].rate_in_effect == Decimal(fx["annual_rate"]).quantize(Decimal("0.000001"))
    assert schedule.payments[59].period == 60
    ```

    **Flip 2: test_arm_continuous_period_numbering**

    Remove decorator. Body:

    ```
    """ARM-05 + D-03: Continuous period numbering 1..N; final balance == 0.00."""
    from decimal import Decimal
    from lib.arm import build_arm_schedule
    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    # Continuous numbering: payments[i].period == i + 1 for all i
    for i, p in enumerate(schedule.payments):
        assert p.period == i + 1, f"period mismatch at index {i}: got {p.period}"
    # Length matches loan term
    assert len(schedule.payments) == req.loan.term_months
    # Final balance is exactly zero (Phase 3 D-09 cleanup on final epoch)
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert schedule.payments[-1].period == req.loan.term_months
    ```

    **Flip 3: test_cumulative_totals_continuous_across_resets**

    Remove decorator. Body:

    ```
    """ARM-05 + D-05: cumulative_interest + cumulative_principal continuous across epoch boundaries.

    For every i >= 1: payments[i].cumulative_interest == payments[i-1].cumulative_interest + payments[i].interest.
    Particularly important AT the reset boundary (period 61 in 5/1) — Phase 3 build_schedule resets
    its internal cum_int to zero on the synthetic loan, so the engine MUST add cum_int_carry.
    """
    from decimal import Decimal
    from lib.arm import build_arm_schedule
    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    payments = schedule.payments
    # Cumulative interest invariant
    assert payments[0].cumulative_interest == payments[0].interest
    for i in range(1, len(payments)):
        expected_cum_int = payments[i - 1].cumulative_interest + payments[i].interest
        # Use exact Decimal equality (no almostEqual)
        assert payments[i].cumulative_interest == expected_cum_int, (
            f"cumulative_interest discontinuity at period {payments[i].period}: "
            f"prev={payments[i-1].cumulative_interest}, this.interest={payments[i].interest}, "
            f"this.cum_int={payments[i].cumulative_interest}"
        )
    # Final invariant: ARMSchedule.total_interest == payments[-1].cumulative_interest (Phase 1 D-15)
    assert schedule.total_interest == payments[-1].cumulative_interest
    # Continuity at the reset boundary specifically (period 60 → 61)
    period_60 = next(p for p in payments if p.period == 60)
    period_61 = next(p for p in payments if p.period == 61)
    assert period_61.cumulative_interest == period_60.cumulative_interest + period_61.interest
    assert period_61.cumulative_principal == period_60.cumulative_principal + period_61.principal
    ```

    **Flip 4: test_non_final_epoch_does_not_zero_balance**

    Remove decorator. Body:

    ```
    """ARM-05 + RESEARCH Q1.2 bear trap: non-final epoch's last sliced row has balance > 0.00.

    If the engine took the discouraged shortcut (synthetic_loan.term_months=reset_period_months),
    Phase 3 D-09 cleanup would zero the balance at every epoch's last sliced row — silently
    paying off the loan at every reset. This test pins the bear trap.
    """
    from decimal import Decimal
    from lib.arm import build_arm_schedule
    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    # 5/1 ARM 30yr: epoch 0 ends at month 60 (last fixed-period payment).
    payments_by_period = {p.period: p for p in schedule.payments}
    # Period 60 is the last sliced row of epoch 0 — its balance MUST be > 0.
    assert payments_by_period[60].balance > Decimal("0.00"), (
        "epoch 0 final row was zeroed — engine took the D-05 forbidden shortcut"
    )
    # Period 72 is the last sliced row of epoch 1 (months 61..72).
    assert payments_by_period[72].balance > Decimal("0.00"), (
        "epoch 1 final row was zeroed — engine took the D-05 forbidden shortcut"
    )
    # Every NON-final period's balance must be > 0
    for p in schedule.payments[:-1]:
        assert p.balance > Decimal("0.00"), (
            f"period {p.period} balance is zero before final period — engine misbehavior"
        )
    # The FINAL period's balance MUST be exactly zero (Phase 3 D-09 cleanup applies HERE only).
    assert schedule.payments[-1].balance == Decimal("0.00")
    ```

    **Flip 5: test_full_remaining_term_re_amortization**

    Remove decorator. Body:

    ```
    """ARM-05 + D-05: each epoch re-amortizes over the FULL remaining term.

    For epoch 1 (months 61..72), the synthetic Loan must have term_months=300 (loan.term_months - 60),
    not 12 (reset_period_months). Verify by reasoning about the per-payment principal/interest
    split: at month 61 with remaining balance ~$370k and a remaining 300-month term at the new rate,
    the P&I should match a fresh build_schedule of those parameters at month 1.
    """
    from decimal import Decimal
    from lib.arm import build_arm_schedule
    from lib.amortize import build_schedule
    from lib.models import Loan
    from datetime import date
    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    payments_by_period = {p.period: p for p in schedule.payments}

    # Compute what build_schedule would produce for epoch 1 alone.
    epoch_1_balance_in = payments_by_period[60].balance
    epoch_1_rate = payments_by_period[61].rate_in_effect
    synthetic_remaining_term = req.loan.term_months - 60  # 300 for 30yr 5/1
    synthetic = build_schedule(
        Loan(
            principal=epoch_1_balance_in,
            annual_rate=epoch_1_rate,
            term_months=synthetic_remaining_term,
            origination_date=date(2026, 1, 1),
            loan_type="arm",
        ),
        frequency="monthly",
        biweekly_mode=None,
        extra_principal=(),
    )
    # The first 12 rows of this synthetic = the engine's epoch 1 (months 61..72).
    for i in range(12):
        absolute_period = 61 + i
        engine_p = payments_by_period[absolute_period]
        synthetic_p = synthetic.payments[i]
        assert engine_p.payment == synthetic_p.payment, (
            f"period {absolute_period}: engine payment={engine_p.payment}, synthetic={synthetic_p.payment}"
        )
        assert engine_p.principal == synthetic_p.principal
        assert engine_p.interest == synthetic_p.interest
        assert engine_p.balance == synthetic_p.balance
    ```

    **Flip 6: test_reset_formula_locked**

    Remove decorator. Body:

    ```
    """ARM-03 + D-02: clamp(quantize(index+margin), low=floor, high=min(periodic, lifetime)).

    Direct call into the private _compute_new_rate helper to pin the formula. Three scenarios:
    - Modest reset (applied_cap == 'none'): index=0.0525, margin=2.5pp -> fully=0.0775; floor=0.03;
      prior=0.05; periodic_ceiling=0.05+5pp=0.10; note=0.05; lifetime=0.05+5pp=0.10; ceiling=min=0.10.
      new_rate = clamp(0.0775, 0.03, 0.10) = 0.0775 (in the open interval; applied_cap='none').
    - Periodic-bound (applied_cap == 'initial'): make fully_indexed > prior+initial_cap.
      index=0.20 (huge), margin=2.5pp -> fully=0.225; periodic_ceiling=0.05+5pp=0.10;
      lifetime=0.05+5pp=0.10; ceiling=0.10. new_rate=quantize(0.10)=0.10. applied_cap='initial' (epoch_idx==1).
    - Floor-bound (applied_cap == 'floor'): index=0.001, margin=0bps -> fully=0.001; floor=0.03;
      effective_floor=max(0,0.03)=0.03. new_rate=0.03. applied_cap='floor'.
    """
    from decimal import Decimal
    from lib.arm import _compute_new_rate
    req = _make_5_1_arm_request(margin_bps=250, floor_rate="0.030000", initial_cap_bps=500, periodic_cap_bps=200, lifetime_cap_bps=500)

    # Modest reset
    new_rate, applied_cap, idx_used = _compute_new_rate(
        prior_rate=Decimal("0.050000"),
        epoch_idx=1,
        period=61,
        req=_make_5_1_arm_request(assumed_index_rate="0.052500"),
        loan_annual_rate=Decimal("0.050000"),
    )
    assert new_rate == Decimal("0.077500"), f"modest reset: {new_rate}"
    assert applied_cap == "none"

    # Periodic-bound at first reset (initial_cap_bps binds)
    new_rate, applied_cap, _ = _compute_new_rate(
        prior_rate=Decimal("0.050000"),
        epoch_idx=1,
        period=61,
        req=_make_5_1_arm_request(assumed_index_rate="0.200000", margin_bps=250),
        loan_annual_rate=Decimal("0.050000"),
    )
    # prior 0.05 + initial_cap 500bps (5pp) = 0.10; lifetime = 0.05 + 500bps = 0.10; ceiling = 0.10.
    assert new_rate == Decimal("0.100000"), f"periodic-bound: {new_rate}"
    assert applied_cap == "initial"

    # Floor-bound
    new_rate, applied_cap, _ = _compute_new_rate(
        prior_rate=Decimal("0.050000"),
        epoch_idx=1,
        period=61,
        req=_make_5_1_arm_request(assumed_index_rate="0.001000", margin_bps=0, floor_rate="0.030000"),
        loan_annual_rate=Decimal("0.050000"),
    )
    assert new_rate == Decimal("0.030000"), f"floor-bound: {new_rate}"
    assert applied_cap == "floor"
    ```

    **Flip 7: test_note_rate_defaults_to_loan_annual_rate** (REPLACE Wave 2 partial flip with full engine assertion)

    Already-flipped (no xfail decorator from Wave 2). Replace the body with:

    ```
    """ARM-01 + D-02 (engine layer): note_rate=None -> engine treats note_rate=loan.annual_rate
    for lifetime ceiling math.

    Wave 2 (Plan 05-02) verified the model-layer default (note_rate=None). This Wave 3
    test verifies the engine BEHAVIOR: when note_rate is None, lifetime_ceiling is computed
    from loan.annual_rate. We pin this by constructing two requests that differ only in
    note_rate (None vs an explicit value matching loan.annual_rate) and asserting they
    produce identical schedules.
    """
    from decimal import Decimal
    from lib.arm import build_arm_schedule

    req_none = _make_5_1_arm_request(annual_rate="0.050000", note_rate=None)
    req_explicit = _make_5_1_arm_request(annual_rate="0.050000", note_rate="0.050000")
    sched_none = build_arm_schedule(req_none)
    sched_explicit = build_arm_schedule(req_explicit)

    # Schedules must match exactly (note_rate=None collapses to loan.annual_rate)
    assert len(sched_none.payments) == len(sched_explicit.payments)
    for p_none, p_explicit in zip(sched_none.payments, sched_explicit.payments, strict=True):
        assert p_none.payment == p_explicit.payment
        assert p_none.rate_in_effect == p_explicit.rate_in_effect
        assert p_none.balance == p_explicit.balance

    # Reset events also match
    assert len(sched_none.reset_events) == len(sched_explicit.reset_events)
    for re_none, re_explicit in zip(sched_none.reset_events, sched_explicit.reset_events, strict=True):
        assert re_none.new_rate == re_explicit.new_rate
        assert re_none.applied_cap == re_explicit.applied_cap
    ```

    **Flip 8: test_arm_teaser_rate**

    Remove decorator. Body:

    ```
    """D-02 + LM-3 (engine layer): teaser-rate ARM uses note_rate as lifetime base.

    loan.annual_rate=0.030 (teaser); note_rate=0.050 (post-teaser). Lifetime ceiling
    measured against note_rate, not loan.annual_rate. Verify by constructing a scenario
    where the lifetime_cap binds: huge index + initial_cap large enough to NOT bind.
    """
    from decimal import Decimal
    from lib.arm import build_arm_schedule
    # Teaser ARM: 3% initial, 5% post-teaser note rate, 5% lifetime cap → lifetime ceiling = 10%.
    # Without the teaser semantic, lifetime ceiling against loan.annual_rate=0.03 would be 8%.
    req = _make_5_1_arm_request(
        annual_rate="0.030000",          # teaser initial
        note_rate="0.050000",            # post-teaser note rate (lifetime base)
        lifetime_cap_bps=500,            # 5pp
        initial_cap_bps=2000,            # 20pp (large; won't bind)
        periodic_cap_bps=2000,
        floor_rate="0.020000",
        margin_bps=250,
        assumed_index_rate="0.150000",   # huge index → fully_indexed = 0.175 (above lifetime ceiling)
    )
    schedule = build_arm_schedule(req)
    first_reset = schedule.reset_events[0]
    # Lifetime ceiling = note_rate (0.05) + lifetime_cap_bps/10000 (0.05) = 0.10
    # NOT loan.annual_rate (0.03) + 0.05 = 0.08
    assert first_reset.new_rate == Decimal("0.100000"), (
        f"teaser ARM: lifetime ceiling should be note_rate+lifetime_cap=0.10, got new_rate={first_reset.new_rate}"
    )
    assert first_reset.applied_cap == "lifetime"
    ```

    Notes:
    - Each test imports its own dependencies inside the function body (avoid polluting module-level imports for tests that may xfail).
    - The shared `_make_5_1_arm_request(...)` helper is defined ONCE at module top after the imports + module constants.
    - Each test passes verbatim Decimal-string inputs; the engine quantizes appropriately.
  </action>
  <verify>
    <automated>pytest tests/test_arm.py -k "test_initial_fixed_period_matches_phase1_oracle or test_arm_continuous_period_numbering or test_cumulative_totals_continuous_across_resets or test_non_final_epoch_does_not_zero_balance or test_full_remaining_term_re_amortization or test_reset_formula_locked or test_note_rate_defaults_to_loan_annual_rate or test_arm_teaser_rate" -xvs</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_arm.py::test_initial_fixed_period_matches_phase1_oracle -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_arm_continuous_period_numbering -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_cumulative_totals_continuous_across_resets -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_non_final_epoch_does_not_zero_balance -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_full_remaining_term_re_amortization -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_reset_formula_locked -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_note_rate_defaults_to_loan_annual_rate -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_arm_teaser_rate -x` exits 0 with 1 passed
    - `grep -c '@pytest.mark.xfail' tests/test_arm.py` returns 21 (29 - 8 flipped here; the test_note_rate flip was already done in Wave 2 but is REPLACED in this plan, not unflipped)
    - Wait — Wave 2 flipped 3 stubs (29 xfails remaining). This plan flips 8 more. 29 - 8 = 21. Verify by counting. The test_note_rate_defaults_to_loan_annual_rate was flipped in Wave 2 (not currently xfail) — this plan REPLACES the body. So this plan flips 7 actual xfail removals + 1 body replacement = 8 newly-passing engine tests. xfail count after: 29 - 7 = 22.
    - CORRECTED ACCEPTANCE: `grep -c '@pytest.mark.xfail' tests/test_arm.py` returns 22
    - `grep -c 'def _make_5_1_arm_request' tests/test_arm.py` returns 1
    - `mypy --strict tests/test_arm.py` exits 0
    - `ruff check tests/test_arm.py` exits 0
    - `ruff format --check tests/test_arm.py` exits 0
  </acceptance_criteria>
  <done>
    8 engine-invariant tests passing (7 stub flips + 1 body replacement); shared helper present; mypy + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero regression + run full Phase 5 suite</name>
  <files>(verification only)</files>
  <read_first>
    - 05-VALIDATION.md "Phase gate" row
    - Plan 05-02 SUMMARY for prior baseline (385 passed + 4 skipped + 29 xfailed)
  </read_first>
  <action>
    Run the full pytest suite. Expected counts after this plan:
    - Plan 05-02 baseline: 385 passed + 4 skipped + 29 xfailed
    - Plan 05-03 delta: +7 newly-passing tests (8 flips minus the 1 already-passing test_note_rate which is body-replaced) → +7 passed, -7 xfailed
    - Final expected: 392 passed + 4 skipped + 22 xfailed + 0 failed + 0 errored

    Run: `pytest -q`

    Run mypy + ruff on every Phase 5 file:
    - `mypy --strict lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py`
    - `ruff check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py`
    - `ruff format --check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py`

    All MUST be clean.

    Sanity check on the engine itself: invoke a 5/1 ARM construction at the Python REPL and assert basic shape:
    - `python -c 'from datetime import date; from decimal import Decimal; from lib.arm import build_arm_schedule, ARMRequest, ARMTerms; from lib.models import Loan; loan=Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.050000"), term_months=360, origination_date=date(2026,1,1), loan_type="arm"); terms=ARMTerms(initial_period_months=60, reset_period_months=12, initial_cap_bps=500, periodic_cap_bps=200, lifetime_cap_bps=500, floor_rate=Decimal("0.030000"), margin_bps=250, index_series_id="MORTGAGE30US"); req=ARMRequest(loan=loan, arm_terms=terms, assumed_index_rate=Decimal("0.052500")); s=build_arm_schedule(req); print(f"payments={len(s.payments)} resets={len(s.reset_events)} final_bal={s.payments[-1].balance} total_int={s.total_interest}")'`

    The output should show `payments=360 resets=25 final_bal=0.00 total_int=<positive Decimal>` for a 5/1 ARM 30yr (24 reset triggers at periods 61, 73, ..., 349 = 25 entries; wait — 5/1 ARM 30yr triggers are 61, 73, 85, 97, ..., 349 = (349-61)/12 + 1 = 25 entries. ✓).
  </action>
  <verify>
    <automated>pytest -q &amp;&amp; mypy --strict lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py &amp;&amp; ruff check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py &amp;&amp; ruff format --check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q` final summary shows passed >= 392
    - `pytest -q` final summary shows xfailed = 22 (32 - 3 [Wave 2] - 7 [Wave 3] = 22)
    - `pytest -q` final summary shows skipped >= 4
    - `pytest -q` final summary shows failed = 0
    - `pytest -q` final summary shows errors = 0
    - `pytest tests/test_amortize.py -q` shows zero regression vs Phase 3 closure
    - `pytest tests/test_affordability.py -q` shows zero regression vs Phase 4 closure
    - `mypy --strict` across all 6 Phase 5 files exits 0
    - `ruff check` across all 6 Phase 5 files exits 0
    - `ruff format --check` across all 6 Phase 5 files exits 0
    - The Python REPL sanity check produces `payments=360 resets=25 final_bal=0.00 total_int=<positive>` for the 5/1 ARM 30yr scenario
  </acceptance_criteria>
  <done>
    Engine ships; ARM-02..05 closed at the engine layer (fixture pinning in Wave 6); all baselines preserved; mypy + ruff clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| build_arm_schedule entry | Trusted (caller already passed ARMRequest through Pydantic validation); engine assumes validated input |
| Phase 3 build_schedule re-entry | Synthetic Loan crosses Phase 3 boundary; Phase 3 D-09 cleanup MUST fire only at the FINAL epoch (slice strategy) |
| Reset formula → ResetEvent.applied_cap | The Literal classification is consumed by D-10 citation-coverage tests + downstream UI (Phase 11 narration); wrong classification corrupts every downstream reading |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-03 | Tampering (cap precedence error) | _compute_new_rate is_first_reset branch | mitigate | Test test_reset_formula_locked pins applied_cap=='initial' on first reset and applied_cap=='periodic' on subsequent (Wave 6 fixture extension); explicit Decimal arithmetic avoids any float coercion |
| T-05-04 | Tampering (floor breach) | _compute_new_rate effective_floor | mitigate | max(margin_rate, floor_rate) computed BEFORE clamp; test scenarios at index=0.001 verify floor enforcement (test_reset_formula_locked); D-02 spec mandates effective_floor lookup |
| T-05-05 | Tampering (off-by-one reset month) | _compute_reset_triggers period start | mitigate | initial_period_months + 1 explicitly encoded; test_initial_fixed_period_matches_phase1_oracle pins payments[0..59] still at initial rate; Wave 6 ships test_arm_5_1_off_by_one_negative for the negative direction |
| T-05-06 | Tampering (cumulative-totals drift) | build_arm_schedule cum_int_carry stitching | mitigate | test_cumulative_totals_continuous_across_resets explicitly asserts payments[i].cum_int == payments[i-1].cum_int + payments[i].interest at every period; particular focus on the period 60→61 boundary |
| T-05-07 | Elevation of Privilege (silent payoff at every reset) | synthetic_loan.term_months | mitigate | test_non_final_epoch_does_not_zero_balance asserts payments[60].balance > 0 (last sliced row of epoch 0); the bear-trap shortcut is forbidden by D-05 and detected by this test |
| T-05-20 | Tampering (slice off-by-one) | sliced = synthetic.payments[:epoch_window] | mitigate | epoch_window = end - start computed from boundaries (open-end); for 5/1 ARM epoch 0 = (1, 61) = window 60 → payments[0:60] = months 1..60 ✓ |
| T-05-21 | Tampering (index_value_used wrong) | _compute_new_rate index resolution | mitigate | for-loop with explicit period match + break; D-01 override-wins; tested by test_arm_teaser_rate (uses assumed_index_rate fallback) and Wave 6 fixture arm_index_path_overrides.json |
| T-05-22 | Information Disclosure (note_rate leak when None) | _compute_new_rate note_rate_eff fallback | mitigate | test_note_rate_defaults_to_loan_annual_rate asserts that None and explicit loan.annual_rate produce IDENTICAL schedules; test_arm_teaser_rate asserts that explicit note_rate uses the supplied value (LM-3) |
</threat_model>

<verification>
- lib/arm.py has build_arm_schedule + 2 helpers; the D-05 forbidden shortcut (term_months=reset_period_months) is verifiably NOT taken (grep)
- 7 invariant Wave-0 stubs flipped to passing; 1 stub body replaced (test_note_rate_defaults_to_loan_annual_rate) with full engine assertion
- 5 fixture-dependent stubs intentionally remain xfail until Wave 6
- Engine emits exactly 25 ResetEvents for a 5/1 ARM 30yr (verified by REPL sanity check)
- final balance == 0.00 for ANY 5/1 ARM 30yr (Phase 3 D-09 fires at final epoch)
- Phase 1 D-15 invariant preserved (total_interest == payments[-1].cumulative_interest)
- Phase 3 + Phase 4 baselines unchanged
- mypy --strict + ruff clean across all 6 Phase 5 files
</verification>

<success_criteria>
- ARM-02..05 closed at the engine layer (fixture pinning in Wave 6; CLI wrapping in Wave 4)
- D-02 reset formula implemented exactly with applied_cap classification covering all 5 Literal values
- D-05 per-epoch slice-stitch with full-remaining-term synthetic Loan (bear-trap forbidden)
- Phase 3 D-09 final-cleanup fires ONLY at the final epoch (intermediate epochs carry forward)
- Phase 1 oracle anchor preserved at epoch 0 ($400k @ 6.5%/30yr → $2528.27)
- Test count: 392 passed, 22 xfailed, 4 skipped, 0 failed, 0 errors
- mypy --strict + ruff clean
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-03-SUMMARY.md` documenting:
- lib/arm.py line count delta (~+250)
- Engine entry-point + 2 helpers shipped
- 7 invariant tests flipped + 1 test body replaced
- xfail count: 29 → 22
- Pass count: 385 → 392
- 25 ResetEvents per 5/1 ARM 30yr (REPL sanity output)
- Phase 1 oracle anchor verified at epoch 0
- ARM-02..05 closure status (engine layer; awaiting Wave 6 fixture pinning)
</output>
