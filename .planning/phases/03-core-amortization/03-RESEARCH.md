# Phase 3: Core Amortization - Research

**Researched:** 2026-04-29
**Domain:** Deterministic amortization-schedule generator (numpy-financial wrapper) + JSON-in/JSON-out CLI
**Confidence:** HIGH — every claim either pinned by a CONTEXT.md decision (D-01..D-19), verified empirically against the project's installed `numpy-financial==1.0.0` in this session, or cited from external docs/regulator URLs already in CONTEXT.md.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Biweekly semantics (D-01..D-04)**
- D-01: Ship BOTH biweekly modes. `Loan.biweekly_mode: Literal["true", "half-monthly"] | None`. Two algorithms, two golden-fixture sets.
- D-02: Default `biweekly_mode = "true"` when `frequency: biweekly` is set without explicit mode. When `frequency: monthly`, `biweekly_mode` MUST be None (validation error otherwise).
- D-03: Date cadence — biweekly steps via `relativedelta(weeks=2)`; monthly via `relativedelta(months=1)`. First payment is one period after origination.
- D-04: True biweekly: `period_rate = annual_rate / Decimal("26")`. Half-monthly: monthly P&I at `annual_rate / Decimal("12")`, split in half for biweekly cashflow (interest still booked monthly). Monthly: `annual_rate / Decimal("12")`. All Decimal — never through float.

**Extra-principal input shape (D-05..D-08)**
- D-05: `extra_principal: list[ExtraPrincipalEntry]` with `period: int (>=1)`, `amount: Money (>0)`, `recurring: bool = False`. One-shot, recurring, step-up scenarios all collapse here. Later recurring entry overrides earlier from its period onward.
- D-06: `period` is period-indexed in schedule's natural cadence. Caller converts "$200/month" → "$100/biweekly" themselves.
- D-07: Order of operations per period: (1) `interest = period_rate * prior_balance`; (2) `principal = pmt - interest`; (3) apply `extra_principal_for_period`; (4) `new_balance = prior_balance - principal - extra_principal_for_period`.
- D-08: Cap extra-principal at remaining balance silently (sets `final_payment_adjusted=True`); do not raise.

**Final-payment cleanup (D-09..D-11)**
- D-09: Adjust ONLY the final period's principal. `principal = prior_balance`; `interest = period_rate * prior_balance`; `payment = principal + interest`; `balance = Decimal("0.00")`.
- D-10: Top-level `Schedule.final_payment_adjusted: bool` flag. Default False; True when adjustment is non-zero (cents drift OR extra-principal early payoff).
- D-11: Hard invariant test: `sum(principal_payments) + sum(extra_principal_payments) == original_principal` exactly. No `assertAlmostEqual`.

**Date handling (D-12..D-13)**
- D-12: When `origination_date` is None, synthesize from today's run date (UTC). Synthesis happens in `lib/amortize.py` at schedule-generation time, NOT in the Pydantic model. `Loan.origination_date: date | None` stays per Phase 1 frozen surface.
- D-13: Month-end edge handling delegated to `relativedelta`. Origination 2026-01-31 → first monthly payment 2026-02-28 (clipping). Pin a fixture exercising the edge.

**Schedule output schema (D-14..D-16)**
- D-14: Extend Phase 1's `Payment` with `cumulative_interest: Money` and `cumulative_principal: Money` (default `Decimal("0.00")`, backwards-compatible).
- D-15: `Schedule.total_interest == payments[-1].cumulative_interest` enforced by validator OR test.
- D-16: Schedule order = ascending by period; dense (every 1..N has a row); period numbering starts at 1.

**CLI surface (D-17..D-19)**
- D-17: `scripts/amortize.py` lives at `<repo>/scripts/amortize.py` for Phase 3. Phase 10 migrates to `.claude/skills/...`.
- D-18: `--input <path>` only. No stdin. Lazy-import `lib.amortize` after argparse (fast `--help`). Schema-error on no input via Pydantic.
- D-19: CLI uses `Loan.model_validate_json` at boundary. Pydantic v2 strict-mode rejects floats in money fields.

### Claude's Discretion

- numpy-financial wrapper internals: scalar per-period vs vectorized — planner picks.
- Decimal/float boundary inside numpy-financial calls — isolate float regions with explicit `Decimal(str(...))` reconstruction; document inline.
- `ExtraPrincipalEntry` Pydantic model placement: `lib/amortize.py` (scoped, preferred) vs `lib/models.py` (frozen surface).
- Test-fixture filenames + structure under `tests/fixtures/amortize/` — JSON shape mirrors `golden_pmt.json` but planner names files.
- Whether to add `freezegun` to dev deps for date-determinism in tests where fixtures don't already pass explicit `origination_date`.
- mypy --strict / ruff continue clean; no new lint rules.

### Deferred Ideas (OUT OF SCOPE)

- Vectorized schedule generation (Phase 8 may revisit if profiling shows scalar paths slow).
- `pyxirr` integration (Phase 6 refi NPV is first consumer).
- DuckDB persistence of computed schedules (Phase 9).
- Skill physical relocation of `scripts/amortize.py` (Phase 10).
- `freezegun` (add only if needed for fixtures without explicit `origination_date`).
- Stdin-based CLI input (v2 if needed).
- Schema migrations for `Payment` cumulative fields if persisted (Phase 9).
- Validation of "extra-principal would overpay" as a structured warning (v2; v1 silently caps).
- ARM re-amortization mid-schedule (Phase 5; Phase 3 wrapper must accept arbitrary `principal/annual_rate/term_months` so Phase 5 can call into it at each reset boundary).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AMRT-01 | `lib/amortize.py` wraps numpy-financial PMT/IPMT/PPMT (does NOT reimplement) | §2 (wrapper strategy); empirical verification npf 1.0.0 supports Decimal end-to-end |
| AMRT-02 | Schedule generator handles fixed-rate loans (any term, any rate) | §2, §5, §10 (validation) |
| AMRT-03 | Schedule generator handles biweekly payment frequency (`relativedelta(weeks=2)`) | §3 (both algorithms in Decimal pseudocode); §10 |
| AMRT-04 | Schedule generator handles arbitrary extra principal payments (single, recurring, or per-period) | §4 (composition order + recurring-override semantics); §10 |
| AMRT-05 | Final payment cleanup ensures balance reaches exactly $0.00 (no float drift) | §5 (algorithm + drift quantification: empirical –$4.58 to +$2.90 on the four oracles) |
| AMRT-06 | `scripts/amortize.py` provides JSON-in / JSON-out CLI for skill use | §7 (argparse skeleton + lazy-import pattern) |
| AMRT-07 | Tests assert `sum(principal_payments) == original_principal` exactly | §5; §10 (Nyquist: per-test invariant assertion) |
| AMRT-08 | Tests pass against all four golden fixtures (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr) | §10; empirically verified all four match `quantize_cents(-npf.pmt(rate/12, n, principal))` exactly in this session |
</phase_requirements>

---

## 1. Executive Summary

Phase 3 is a thin, deterministic wrapper around `numpy-financial.pmt/ipmt/ppmt` that produces a `Schedule` (per Phase 1's frozen Pydantic models) for fixed-rate, biweekly (true + half-monthly), and extra-principal scenarios. The math is settled — `numpy-financial==1.0.0` (already pinned in `pyproject.toml`) accepts and returns `Decimal` end-to-end (empirically verified this session); all four golden oracles (Wikipedia $1,264.14, CFPB LE $761.78, $400k/$2,528.27, $200k-15yr/$1,797.66) match `quantize_cents(-npf.pmt(rate/12, n, principal))` exactly. The interesting design surface is **iteration shape**: `npf.pmt` once + per-period scalar `interest = period_rate * balance` / `principal = pmt - interest`, with end-of-period `quantize_cents`. Vectorized `npf.ipmt`/`npf.ppmt` over a periods array are equivalent for the fixed-rate case but cannot survive extra-principal mid-stream (which mutates remaining balance every period). **Recommendation: scalar per-period iteration**, with `npf.pmt` called once for the level payment and `npf.ipmt(rate, 1, n, balance)` available as an oracle for sanity-check tests. CLI is argparse + lazy-import + `Loan.model_validate_json`. Drift over 360 periods on the four oracles ranges $-4.58 to +$2.90 (single-digit dollars, both signs); D-09's "set final principal = remaining balance" cleanup absorbs it cleanly. The test surface has 7 distinct behaviors to cover (fixed, biweekly-true, biweekly-half-monthly, extra-one-shot, extra-recurring, extra-step-up, final-cleanup) plus 4 oracle equality tests = 11 baseline test classes + AMRT-07 invariant assertion bolted onto every schedule-producing test. No new lint rules, no new dev deps unless the planner picks `freezegun`. Phase 1's `Payment` model gets two fields added (D-14: `cumulative_interest`, `cumulative_principal`); existing tests untouched.

**Primary recommendation:** Scalar per-period iteration with `npf.pmt` for the level payment + manual interest/principal split + end-of-period `quantize_cents`; `npf.ipmt`/`npf.ppmt` reserved as test-only oracles for the fixed-rate path (cross-check that our scalar iteration matches numpy's vectorized values to within the cents-drift band).

---

## 2. numpy-financial Wrapper Strategy

### Empirical baseline (verified this session)

```
npf version: 1.0.0
pmt(Decimal, int, Decimal) -> Decimal              # negative (cashflow-out convention)
ipmt(Decimal, int, int, Decimal) -> ndarray[Decimal]  # 0-d ndarray with one Decimal element
ppmt(Decimal, int, int, Decimal) -> Decimal        # negative
ipmt(Decimal, np.arange(1,N), int, Decimal) -> ndarray[Decimal]  # vectorized, all Decimal
```

Sign convention: `npf.pmt` returns negative values (Excel cashflow-out); we flip with `-` at the boundary.

### The two candidate paths

| Path | Shape | When it works | When it breaks |
|------|-------|--------------|----------------|
| **A — scalar per-period iteration** | Call `npf.pmt(rate, n, principal)` once for level payment; per period: `interest = quantize_cents(rate * balance)`, `principal = quantize_cents(pmt - interest)`, `balance -= principal` | Always — works for fixed, biweekly, AND extra-principal | — |
| **B — vectorized npf.ipmt/npf.ppmt** | Call `npf.ipmt(rate, np.arange(1,n+1), n, principal)` once → array of all period interests; same for principal; cumsum for balances | Fixed-rate only | Breaks for extra-principal: vectorized formula assumes the original principal/balance schedule, but extra-principal mid-stream changes the remaining balance, invalidating later periods' values |

### Recommendation: Path A (scalar)

Rationale, in order of weight:
1. **Survives extra-principal mid-stream.** AMRT-04 is non-negotiable. With Path B you'd have to re-vectorize from each extra-principal event onward, which is just Path A wearing a costume.
2. **Survives biweekly-true acceleration.** When `biweekly_mode="true"` and the payment is `monthly_pi / 2`, the schedule terminates *early* (~628 periods for a 200k/6.5%/30yr loan, vs the formulaic 780 — empirically verified this session). The scalar loop naturally exits when balance → 0; the vectorized path would over-allocate.
3. **One code path for all three scenarios** (fixed, biweekly, extra-principal). Maintainability + test-coverage clarity.
4. **Performance is a non-issue.** 30yr biweekly = ~780 iterations; even for Phase 8's 100-scenario stress sweeps, that's ~78k iterations of trivial Decimal arithmetic — well under 1s. (Deferred-decisions table in CONTEXT.md notes vectorization may be revisited in Phase 8 if profiling shows otherwise.)

### Wrapper module shape (recommended)

```python
# lib/amortize.py
"""Schedule generator wrapping numpy-financial PMT/IPMT/PPMT.

Per AMRT-01, this module wraps numpy-financial — it does NOT reimplement amortization
math. The scalar per-period iteration is chosen over vectorized npf.ipmt/ppmt because
extra-principal mid-stream (AMRT-04) and biweekly-true acceleration (AMRT-03 D-01/D-04)
both invalidate the vectorized formula's "remaining balance assumed = principal-amortizing"
premise.

numpy-financial 1.0.0 returns Decimals when fed Decimals (verified). Sign convention:
npf.pmt returns negative cashflow-out; we flip at the boundary with `-`.

Bug avoidance (per CONTEXT.md):
- Always pass fv=0 (default). Bug #130 (pmt fv-sign flipped) does not affect us.
- Never use npf.irr. Bug #131 (irr arch-dependent). Phase 6 will use pyxirr.

Default biweekly_mode = "true" when frequency=biweekly without explicit mode (D-02).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy_financial as npf  # type: ignore[import-untyped]
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field

from lib.models import Loan, Payment, Schedule
from lib.money import CENT, quantize_cents

if TYPE_CHECKING:
    from collections.abc import Sequence


class ExtraPrincipalEntry(BaseModel):
    """One extra-principal entry. D-05 collapses one-shot/recurring/step-up to one schema."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=1)
    amount: Decimal = Field(strict=True, gt=Decimal("0"), max_digits=14, decimal_places=2)
    recurring: bool = False


def build_schedule(
    loan: Loan,
    *,
    frequency: str = "monthly",                       # "monthly" | "biweekly"
    biweekly_mode: str | None = None,                 # "true" | "half-monthly" | None
    extra_principal: Sequence[ExtraPrincipalEntry] = (),
) -> Schedule: ...
```

### Decimal/float boundary

numpy-financial 1.0.0 accepts Decimal end-to-end with no float coercion (verified). The `Decimal(str(...))` reconstruction pattern from CONTEXT.md "Claude's Discretion" is **not needed** for any path Phase 3 hits. Document this verification inline in the module docstring; flag clearly if future numpy-financial versions regress.

[VERIFIED: empirical execution 2026-04-29 in project's `.venv`]

---

## 3. Biweekly Algorithms (Full Decimal Pseudocode)

Both algorithms produce a `Schedule` with the same Pydantic shape. The DIFFERENCE is the period count, payment amount, and interest-accrual cadence.

### 3.1 True biweekly (D-01, D-02 default, D-04)

**Definition:** Pay half the monthly P&I every 14 days. 26 half-payments/yr = 13 monthly equivalents/yr (vs 12). Extra payment/yr accelerates payoff. Period rate `= annual_rate / 26` for interest accrual.

**Empirical: 200k/6.5%/30yr → ~628 biweekly periods (24.2 yrs), saving ~5.8 yrs vs 30yr monthly.**

```python
# True biweekly pseudocode (D-04)
period_rate = annual_rate / Decimal("26")
monthly_pi = quantize_cents(-npf.pmt(annual_rate / Decimal("12"), term_months, principal))
biweekly_payment = quantize_cents(monthly_pi / Decimal("2"))    # half of monthly P&I

balance = principal
period = 0
payments = []
cum_int = Decimal("0.00")
cum_prin = Decimal("0.00")

while balance > Decimal("0.00"):
    period += 1
    interest = quantize_cents(period_rate * balance)

    # Final-period cleanup detection: if formulaic principal would zero/overshoot the balance,
    # this IS the final period (D-09).
    if balance + interest <= biweekly_payment:
        # Final period: principal = balance (clear it)
        principal_paid = balance
        payment = quantize_cents(principal_paid + interest)
        balance_after = Decimal("0.00")
        final_adjusted = True
    else:
        principal_paid = quantize_cents(biweekly_payment - interest)
        payment = biweekly_payment
        balance_after = balance - principal_paid

    # Apply extra-principal AFTER regular principal (D-07) — see §4 for details
    extra = _extra_for_period(period, extra_principal_entries, cap=balance_after)
    balance_after -= extra

    cum_int += interest
    cum_prin += principal_paid
    payments.append(Payment(
        period=period,
        payment_date=origination_date + relativedelta(weeks=2 * period),  # D-03
        payment=payment,
        principal=principal_paid,
        interest=interest,
        extra_principal=extra,
        balance=balance_after,
        cumulative_interest=cum_int,           # D-14
        cumulative_principal=cum_prin,         # D-14
    ))

    balance = balance_after
```

**Notes:**
- Term limit: in practice biweekly-true terminates ~5-7 yrs early; loop exits when `balance == 0`. Optionally hard-cap at `term_months * 2` periods as a safety bound (paranoia; not strictly needed since the formulaic biweekly payment guarantees termination).
- The `monthly_pi` field on `Schedule` (already in Phase 1) = the *implied monthly* P&I (computed at rate/12), NOT the biweekly cashflow. Document this in `lib/amortize.py` docstring + `--help` text. Alternative: introduce `Schedule.period_payment` as a convention; out of scope per Phase 1 frozen surface — stick with the docstring approach.
- `final_payment_adjusted` is True for true-biweekly schedules whenever the formulaic biweekly payment would overshoot in the last period (almost always; biweekly accelerates and the last period rarely lines up to zero exactly).

### 3.2 Half-monthly biweekly (D-01, D-04)

**Definition:** Compute monthly P&I at rate/12. Debit half every 14 days as a *cashflow*. Interest is **booked monthly** (not biweekly) — this preserves the same total interest as a vanilla monthly schedule. The schedule has 360 monthly rows (or 24N rows? see below) and the biweekly cadence is purely a billing-frequency decoration.

**Critical design choice — what does the schedule output look like?** Two reasonable interpretations:

| Option | Schedule rows | Pro | Con |
|--------|---------------|-----|-----|
| **A** | One row per **monthly** period (360 rows for 30yr); `payment_date` is the second-half debit date; total interest matches monthly | Simplest; schedule shape identical to fixed-rate | Loses the biweekly cashflow visibility |
| **B** | One row per **biweekly** debit (720 rows for 30yr); each row's `interest` is half the *monthly* interest accrual booked at the second debit only (first debit row has interest=0) | Faithful to cashflow; visible biweekly debits | Awkward semantics; consumer must understand |

**Recommendation: Option A.** The "half-monthly" mode is a billing-frequency convenience; the underlying amortization mathematics is monthly. Schedule emits 360 monthly rows; `payment_date` advances `relativedelta(months=1)`; `payment = monthly_pi`. The fact that the lender debits in two halves is a `Schedule.notes` matter, not a per-row matter. **Document this prominently** in the module docstring — failure to clarify is a known calculator-tool mistake (per CONTEXT.md spec rationale).

```python
# Half-monthly biweekly pseudocode (D-04, Option A)
# Cashflow is biweekly; interest accrual + schedule rows are monthly.
period_rate = annual_rate / Decimal("12")
monthly_pi = quantize_cents(-npf.pmt(period_rate, term_months, principal))

balance = principal
payments = []
cum_int = Decimal("0.00")
cum_prin = Decimal("0.00")

for period in range(1, term_months + 1):
    interest = quantize_cents(period_rate * balance)

    # D-09 final-period cleanup applied at last formulaic period
    if period == term_months:
        principal_paid = balance
        payment = quantize_cents(principal_paid + interest)
    else:
        principal_paid = quantize_cents(monthly_pi - interest)
        payment = monthly_pi
    balance_after = balance - principal_paid

    # Extra-principal (D-07)
    extra = _extra_for_period(period, extra_principal_entries, cap=balance_after)
    balance_after -= extra

    cum_int += interest
    cum_prin += principal_paid
    payments.append(Payment(
        period=period,
        payment_date=origination_date + relativedelta(months=period),  # D-03 (monthly cadence)
        payment=payment,
        principal=principal_paid,
        interest=interest,
        extra_principal=extra,
        balance=balance_after,
        cumulative_interest=cum_int,
        cumulative_principal=cum_prin,
    ))
    balance = balance_after
    if balance == Decimal("0.00") and extra_principal_entries:
        break  # extra-principal accelerated payoff
```

**`monthly_pi` on Schedule:** the actual monthly P&I (consumers see it; matches monthly oracle).

**Open planner question:** does the JSON output need to surface "biweekly debits cadence: $X per 14 days"? Recommendation: include in a future `Schedule.notes: list[str]` field (deferred per CONTEXT.md Deferred Ideas — out of v1) OR as an inline comment in the report writer (Phase 10). For Phase 3, the biweekly-half-monthly schedule is simply a monthly schedule with a label.

[ASSUMED] Half-monthly mode emits a monthly schedule, not a biweekly one. **Confirm with planner / user** if biweekly debit-cashflow visibility is required for v1. If yes, switch to Option B and re-pin biweekly-half-monthly fixtures accordingly. *Per CONTEXT.md "specifics" line 180: "interest still booked monthly"* — strongly supports Option A.

---

## 4. Extra-Principal Composition

### Order of operations (D-07 — locked)

For each period:
1. `interest = quantize_cents(period_rate * prior_balance)` — interest accrues on prior balance, untouched by extra
2. `principal = quantize_cents(pmt - interest)` — regular principal portion
3. `extra_principal_for_period = _resolve_extra(period, entries, cap=prior_balance - principal)` — D-08 cap at remaining balance
4. `new_balance = prior_balance - principal - extra_principal_for_period`

This ordering matches `npf.ipmt`/`npf.ppmt` convention (interest computed at start of period on outstanding balance) and is what consumer reports expect.

### Recurring-then-override semantics (D-05)

Resolution rule: at each period `p`, the *active* recurring entry is the **latest entry** (highest `period` value) that satisfies `entry.period <= p AND entry.recurring == True`. One-shot entries (`recurring=False`) fire only on the named period and are additive to the recurring component.

```python
def _resolve_extra(
    period: int,
    entries: Sequence[ExtraPrincipalEntry],
    cap: Decimal,
) -> Decimal:
    """Resolve extra-principal for a single period.

    - Active recurring = latest entry with entry.period <= period and recurring=True.
    - One-shot entries fire only on the named period (additive to recurring).
    - Result is capped at remaining balance (D-08); cap-application sets
      final_payment_adjusted at the schedule level.
    """
    active_recurring = max(
        (e for e in entries if e.recurring and e.period <= period),
        key=lambda e: e.period,
        default=None,
    )
    one_shots = [e for e in entries if not e.recurring and e.period == period]

    raw = (active_recurring.amount if active_recurring else Decimal("0.00"))
    raw += sum((e.amount for e in one_shots), start=Decimal("0.00"))

    capped = min(raw, cap)
    return quantize_cents(capped)
```

**Test cases the planner must pin (per CONTEXT.md "Specific Ideas"):**
- One-shot at period 60: `[{period: 60, amount: "5000", recurring: false}]` — only period 60 has extra.
- Recurring $200 from period 1: `[{period: 1, amount: "200", recurring: true}]` — every period has $200.
- Step-up at period 13: `[{period: 1, amount: "200", recurring: true}, {period: 13, amount: "300", recurring: true}]` — periods 1-12 have $200, period 13 onward has $300.
- Cap-at-balance: recurring $50,000/period on a small loan — caps silently, sets `final_payment_adjusted = True`.

### Biweekly + extra-principal (D-06)

`period` field counts biweekly periods (1..~780 for 30yr biweekly true). Caller is responsible for converting "$200/month" → "$100/biweekly". Document in `--help`. One rule: `period` matches the schedule's emitted period numbers, no internal conversion.

[VERIFIED: D-06 in CONTEXT.md, line 49]

---

## 5. Final-Payment Cleanup

### Algorithm (D-09 — locked)

On the **final period** (whichever one terminates the schedule — formulaic last period for fixed/half-monthly, or first period where `balance + interest <= payment` for biweekly-true / extra-principal accelerated):

```python
interest_final = quantize_cents(period_rate * prior_balance)
principal_final = prior_balance                   # clear remaining balance
payment_final = quantize_cents(principal_final + interest_final)
balance_after_final = Decimal("0.00")
# Set Schedule.final_payment_adjusted = True if principal_final != formulaic_principal
final_payment_adjusted = (principal_final != quantize_cents(level_pmt - interest_final))
```

### Cents-drift quantification (empirical, this session)

Naive iteration without cleanup, per oracle (200k/6.5/30yr Wikipedia, 162k/3.875/30yr CFPB, 400k/6.5/30yr, 200k/7/15yr):

| Oracle | n periods | naive final balance (overshoot/undershoot) |
|--------|-----------|---------------------------------------------|
| Wikipedia 200k/6.5/30yr | 360 | **−$4.58** (overpaid by $4.58 across the schedule) |
| CFPB 162k/3.875/30yr | 360 | **+$2.90** (underpaid; $2.90 left on the table) |
| Computed 400k/6.5/30yr | 360 | **+$2.61** (underpaid) |
| Computed 200k/7/15yr | 180 | **−$0.96** (overpaid) |

**Magnitude:** single-digit dollars across all four oracles. **Sign:** can be negative or positive — the cleanup must handle both directions.

D-09's cleanup absorbs both directions cleanly: `principal = balance` clears whatever remains. Verified: Wikipedia oracle final-period cleanup yields `principal=$1252.77, interest=$6.79, balance=$0.00, sum_principal=$200000.00 exactly`.

[VERIFIED: empirical execution 2026-04-29]

### `final_payment_adjusted` semantics (D-10)

| Trigger | Flag value |
|---------|-----------|
| Default (no adjustment) | False |
| Cents drift cleanup at last period | True |
| Extra-principal accelerated payoff (schedule terminates before formulaic last period) | True |
| Recurring extra-principal capped at remaining balance | True |

Default False; set True whenever the final period's principal differs from the formulaic value. Consumers (Phase 6 refi for early-payoff detection; Phase 8 stress for shortened schedules) consume this flag.

**Detection rule** (recommended):
```python
final_payment_adjusted = (principal_final != quantize_cents(level_pmt - interest_final))
```
This catches both cents-drift and extra-principal-induced acceleration in one expression.

**Edge case to pin in tests:** "by-luck-zero-drift" — if the schedule's drift happens to be exactly $0.00 (rare, but possible for contrived rates/principals), `final_payment_adjusted` should be False. Verify by constructing a fixture where formulaic last-period principal exactly equals remaining balance.

---

## 6. Cumulative-Totals Invariant (D-15)

### Decision: validator vs test

**Recommendation: model-level Pydantic validator on `Schedule`.**

Rationale:
- Phase 1's existing model conventions already use `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` for all domain models. Adding a `@model_validator(mode="after")` is consistent with that surface and locks the invariant at the type-system layer (every consumer of `Schedule` — Phase 6 refi, Phase 8 stress — gets the guarantee for free).
- The alternative ("test-level assertion") leaves the invariant unenforced for any Schedule constructed outside the test suite (e.g., a Phase 6 caller building a synthetic Schedule for a what-if scenario).
- Validator is enforced exactly once at construction time; no runtime cost during iteration.

```python
# lib/models.py (extension)
from pydantic import model_validator

class Schedule(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    monthly_pi: Money
    total_interest: Money
    final_payment_adjusted: bool = False     # D-10
    payments: list[Payment]

    @model_validator(mode="after")
    def _total_interest_matches_last_cumulative(self) -> "Schedule":
        """D-15: Schedule.total_interest == payments[-1].cumulative_interest exactly.

        Guards against silent disagreement between summary and per-row totals.
        Skipped when payments is empty (constructor convenience; tests still cover
        non-empty schedules).
        """
        if not self.payments:
            return self
        last = self.payments[-1].cumulative_interest
        if self.total_interest != last:
            raise ValueError(
                f"Schedule.total_interest ({self.total_interest}) != "
                f"payments[-1].cumulative_interest ({last}); D-15 invariant violated"
            )
        return self
```

**Note for the planner:** This is the ONE part of Phase 1's frozen surface that needs more than a "two field additions" extension. The `Schedule` model gains a validator AND a new `final_payment_adjusted: bool = False` field (D-10). Both are backwards-compatible additions (default values; existing Phase 1 tests on `Schedule` pass without modification — verified by `test_schedule_aggregates_loan_and_payments` which uses one-row payments where `total_interest=$510178.27` won't match the one-row `cumulative_interest=Decimal("0.00")`... wait — see Open Question below).

### ⚠️ Open question for the planner

Phase 1's `test_schedule_aggregates_loan_and_payments` constructs a Schedule with `total_interest=Decimal("510178.27")` and a single Payment whose `cumulative_interest` defaults to `Decimal("0.00")`. **Adding the D-15 validator will break this test.** Options:
1. Update the Phase 1 test to pass a Payment with `cumulative_interest=Decimal("510178.27")` (preferred — minor adjustment).
2. Loosen the validator to skip when `len(payments) <= 1` (loses some safety).
3. Move D-15 enforcement to a test-only assertion in Phase 3 (loses the type-system guarantee).

**Recommendation: Option 1.** It's a one-line test change, preserves the strongest invariant, and the test is in the "Phase 1 frozen surface" only loosely — it documents shape rather than locking values. Plan should explicitly call out updating `tests/test_models.py::test_schedule_aggregates_loan_and_payments`.

---

## 7. CLI Design (`scripts/amortize.py`)

### argparse skeleton with lazy-import (D-17, D-18, D-19)

```python
#!/usr/bin/env python3
"""scripts/amortize.py — JSON-in / JSON-out CLI for the amortization engine.

Per AMRT-06 + D-17/D-18/D-19:
- File-based input only: --input <path> (no stdin in v1, per D-18)
- JSON output to stdout (pipe-friendly)
- --help works without importing heavy deps (lazy-import per D-18)
- Pydantic v2 strict-mode validation at the boundary (D-19)
- Errors surface as JSON-readable Pydantic validation messages

Default biweekly_mode = "true" when frequency is "biweekly" without explicit mode (D-02).
Phase 10 will physically relocate this script to .claude/skills/mortgage-ops/scripts/amortize.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="amortize",
        description="Generate an amortization schedule from a JSON loan input.",
        epilog=(
            "Input JSON shape: a Loan object plus optional 'frequency' "
            '("monthly"|"biweekly"), "biweekly_mode" ("true"|"half-monthly"; default '
            '"true" when frequency=biweekly), and "extra_principal" '
            "(list of {period, amount, recurring} entries). See lib/amortize.py docstring."
        ),
    )
    parser.add_argument(
        "--input", required=True, type=Path,
        help="Path to JSON file containing the loan input.",
    )
    args = parser.parse_args()

    # Lazy-import after argparse (D-18: --help is fast)
    from pydantic import ValidationError
    from lib.amortize import build_schedule, ExtraPrincipalEntry, AmortizeRequest
    from lib.models import Loan

    try:
        raw = args.input.read_text()
    except FileNotFoundError as e:
        print(json.dumps({"error": f"input file not found: {e.filename}"}), file=sys.stderr)
        return 2

    try:
        request = AmortizeRequest.model_validate_json(raw)  # D-19
    except ValidationError as e:
        # Pydantic emits structured JSON-readable errors; pass through as JSON
        print(e.json(), file=sys.stderr)
        return 2

    schedule = build_schedule(
        request.loan,
        frequency=request.frequency,
        biweekly_mode=request.biweekly_mode,
        extra_principal=request.extra_principal,
    )
    print(schedule.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `AmortizeRequest` Pydantic model (recommended placement: `lib/amortize.py`)

```python
# lib/amortize.py
class AmortizeRequest(BaseModel):
    """Top-level request schema for scripts/amortize.py."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    frequency: Literal["monthly", "biweekly"] = "monthly"
    biweekly_mode: Literal["true", "half-monthly"] | None = None
    extra_principal: list[ExtraPrincipalEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _biweekly_mode_consistency(self) -> "AmortizeRequest":
        """D-02: biweekly_mode MUST be None when frequency is monthly."""
        if self.frequency == "monthly" and self.biweekly_mode is not None:
            raise ValueError(
                "biweekly_mode must be None when frequency='monthly' (D-02)"
            )
        # D-02 default: when biweekly and mode unset, default to "true" — applied at engine time
        return self
```

The default `biweekly_mode = "true"` is applied inside `build_schedule`, not in the model (so callers can pass `None` and get the documented default — keeps the model's "what was provided" semantics distinct from the engine's "what was applied").

### Error surface examples

| Input | Stderr | Exit |
|-------|--------|------|
| Missing `--input` | argparse usage message | 2 |
| `--input nonexistent.json` | `{"error": "input file not found: nonexistent.json"}` | 2 |
| Invalid JSON | Pydantic ValidationError JSON (parsing error) | 2 |
| Float in `principal` | Pydantic ValidationError JSON (decimal_type error) | 2 |
| `frequency=monthly` with `biweekly_mode=true` | Pydantic ValidationError JSON (D-02 violation) | 2 |
| Valid input | JSON Schedule on stdout | 0 |

### `--help` performance

Lazy-import means `argparse` parses + emits help text *before* any `numpy_financial`, `dateutil`, or `lib.*` import. Smoke-test with `time python scripts/amortize.py --help` should be < 100ms; the heavy imports happen only on a real run.

---

## 8. Date Handling

### Origination synthesis (D-12)

When `origination_date` is None at the engine entry point, synthesize at schedule-generation time (NOT in the Pydantic model — Phase 1 frozen surface keeps `Loan.origination_date: date | None`):

```python
# lib/amortize.py
from datetime import UTC, datetime

def build_schedule(loan: Loan, ...) -> Schedule:
    origination_date = loan.origination_date or datetime.now(UTC).date()
    ...
```

Synthesizing inside the engine (vs. inside the script CLI) means library callers (Phase 5 ARM, Phase 8 stress) get the same default behavior.

### Month-end edge (D-13)

`relativedelta` clips Jan 31 + 1mo → Feb 28 (or Feb 29 in leap years). Trust dateutil's behavior; pin a fixture exercising the edge to lock it in.

**Pin a fixture:** `tests/fixtures/amortize/month_end_origination_jan31.json` with `origination_date: "2026-01-31"`, monthly schedule, expected first `payment_date: "2026-02-28"`. Add explicit assertions in the test that the next several `payment_date`s are also clipped (`2026-03-31`, `2026-04-30`, `2026-05-31`, `2026-06-30`).

[VERIFIED: dateutil 2.9.x relativedelta month-end clipping behavior is documented stable for >5 years; project already imports dateutil per pyproject.toml + Phase 1 RESEARCH.md]

### Test determinism approach

CONTEXT.md "Claude's Discretion" leaves this open. Recommended approach (preferred path): **explicit `origination_date` in every fixture**. No `freezegun` dependency added.

| Approach | Pro | Con |
|----------|-----|-----|
| **Explicit `origination_date` in fixtures** | No new dep; deterministic; visible in JSON | Slightly more boilerplate per fixture |
| `freezegun` + `@pytest.fixture(autouse=True)` | One test-level decorator handles all "origination=None" cases | New dev dep; magic; hides date-flow |

**Recommendation: explicit dates in all amortize-test fixtures.** Add ONE small unit test for the synthesis path that uses `freezegun` (or simpler: `monkeypatch` the `datetime.now` import). This isolates the only "date is None" test to a single deterministic case without polluting all golden fixtures with frozen-time decorators. Avoids adding `freezegun` as a project-level dep entirely (use `monkeypatch` since pytest provides it stdlib-style).

```python
# tests/test_amortize.py
def test_build_schedule_synthesizes_origination_when_none(monkeypatch) -> None:
    """D-12: when Loan.origination_date is None, engine synthesizes from datetime.now(UTC)."""
    from datetime import date as _date
    fake_today = _date(2026, 5, 15)

    class _FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            class _D:
                @staticmethod
                def date(): return fake_today
            return _D()

    monkeypatch.setattr("lib.amortize.datetime", _FakeDateTime)
    loan = Loan(principal=Decimal("200000.00"), annual_rate=Decimal("0.065000"), term_months=360)
    schedule = build_schedule(loan)
    # First payment date = 2026-05-15 + relativedelta(months=1) = 2026-06-15
    assert schedule.payments[0].payment_date == _date(2026, 6, 15)
```

---

## 9. Test Fixture Structure

### Directory layout (recommended)

```
tests/
├── fixtures/
│   ├── golden_pmt.json                   # Phase 1 — 4 oracles, used by AMRT-08
│   └── amortize/                         # Phase 3 — new directory
│       ├── fixed_30yr_400k_6_5.json      # full schedule fixture (loan + expected_summary)
│       ├── fixed_30yr_200k_6_5.json
│       ├── fixed_30yr_162k_3_875.json
│       ├── fixed_15yr_200k_7.json
│       ├── biweekly_true_200k_6_5.json
│       ├── biweekly_half_monthly_200k_6_5.json
│       ├── extra_oneshot_5k_period_60_200k_6_5.json
│       ├── extra_recurring_200_30yr_400k_6_5.json
│       ├── extra_step_up_200_to_300_30yr_200k_6_5.json
│       ├── extra_overpay_caps_at_balance.json
│       └── month_end_origination_jan31.json
├── test_amortize.py                      # new test file
└── conftest.py                           # may extend with amortize_fixture loader
```

**Naming convention:** `{scenario}_{principal_short}_{rate_short}.json` for fixed; `{mode}_{principal_short}_{rate_short}.json` for biweekly; `{kind}_{terms}_{principal_short}_{rate_short}.json` for extra-principal.

### Fixture schema (mirrors `golden_pmt.json` shape, extended)

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "id": "fixed_30yr_400k_6_5",
  "source": "computed in-tree with Decimal + ROUND_HALF_UP; cross-verified against Wikipedia oracle scaling",
  "rounding": "ROUND_HALF_UP",
  "notes": "Stress-test scale of Wikipedia oracle (2x principal, same rate/term).",
  "loan": {
    "principal": "400000.00",
    "annual_rate": "0.065000",
    "term_months": 360,
    "origination_date": "2026-05-01",
    "loan_type": "fixed"
  },
  "frequency": "monthly",
  "biweekly_mode": null,
  "extra_principal": [],
  "expected_schedule_summary": {
    "monthly_pi": "2528.27",
    "total_interest": "510176.86",
    "final_payment_adjusted": true,
    "num_payments": 360,
    "first_payment": {
      "period": 1,
      "payment_date": "2026-06-01",
      "payment": "2528.27",
      "principal": "361.60",
      "interest": "2166.67",
      "extra_principal": "0.00",
      "balance": "399638.40",
      "cumulative_interest": "2166.67",
      "cumulative_principal": "361.60"
    },
    "last_payment": {
      "period": 360,
      "payment_date": "2056-05-01",
      "payment": "...",
      "principal": "...",
      "interest": "...",
      "extra_principal": "0.00",
      "balance": "0.00",
      "cumulative_interest": "510176.86",
      "cumulative_principal": "400000.00"
    }
  }
}
```

**Pin only first/last rows + summary** — pinning all 360 rows in JSON is brittle and makes diffs huge. The AMRT-07 invariant assertion (sum of principal_payments == original_principal) protects the middle rows; the first/last pin protects the boundary calculations.

### Fixture loader (conftest extension)

```python
# tests/conftest.py (extension)
@pytest.fixture
def amortize_fixture() -> Callable[[str], dict[str, Any]]:
    """Load a single amortize fixture by filename stem from tests/fixtures/amortize/."""
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "amortize" / f"{stem}.json"
        return json.loads(path.read_text())
    return _load
```

### Extra-principal pinned numbers

Each extra-principal fixture's `expected_schedule_summary` must include the **acceleration impact** explicitly:

```json
"expected_schedule_summary": {
  "num_payments": 287,                         // (vs 360 formulaic — schedule shortened)
  "interest_savings_vs_baseline": "73142.18",  // computed against the no-extra fixture
  "final_payment_adjusted": true,
  ...
}
```

This makes test failures readable: "expected num_payments=287, got 290" tells the reader exactly what drifted.

---

## 10. Validation Architecture

> Per `.planning/config.json` `workflow.nyquist_validation: true`. Section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ (per `pyproject.toml [dependency-groups].dev`) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_amortize.py -x` |
| Full suite command | `uv run pytest` |
| Strict markers | `--strict-markers --strict-config` (already enabled) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AMRT-01 | `lib/amortize.py` wraps numpy-financial (does NOT reimplement) | structural | `uv run pytest tests/test_amortize.py::test_amortize_module_uses_numpy_financial -x` (asserts `numpy_financial` import in module + presence of `npf.pmt` call via AST or import-graph check) | ❌ Wave 0 |
| AMRT-02 | Fixed-rate schedule: 4 golden oracles | unit | `uv run pytest tests/test_amortize.py::test_fixed_rate_oracle -x` (parametrized over the 4 oracles) | ❌ Wave 0 |
| AMRT-03 | Biweekly true mode + half-monthly mode (separate algorithms) | unit | `uv run pytest tests/test_amortize.py::test_biweekly_true_oracle tests/test_amortize.py::test_biweekly_half_monthly_oracle -x` | ❌ Wave 0 |
| AMRT-04 | Extra-principal: one-shot + recurring + step-up + cap-at-balance | unit | `uv run pytest tests/test_amortize.py -k "extra_principal" -x` | ❌ Wave 0 |
| AMRT-05 | Final-payment cleanup (balance == Decimal("0.00") exactly) | invariant | `uv run pytest tests/test_amortize.py -k "final_payment" -x` | ❌ Wave 0 |
| AMRT-06 | CLI smoke: JSON-in/out, lazy --help, error surface | integration (subprocess) | `uv run pytest tests/test_amortize.py -k "cli" -x` | ❌ Wave 0 |
| AMRT-07 | `sum(principal) + sum(extra_principal) == original_principal` exactly | invariant (asserted on EVERY schedule-producing test) | covered by every test that calls `build_schedule` via shared `assert_schedule_invariants` helper | ❌ Wave 0 |
| AMRT-08 | All 4 golden oracles pass with exact Decimal equality | unit | `uv run pytest tests/test_amortize.py::test_fixed_rate_oracle -x` (parametrized; uses Phase 1's `golden_fixture`) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_amortize.py -x` (~12-20 tests; should run in < 5s including 360-period iterations)
- **Per wave merge:** `uv run pytest` (full suite — Phase 1 + Phase 2 + new Phase 3 tests = 224+ tests; < 30s)
- **Phase gate:** Full suite green + ruff + mypy --strict before `/gsd-verify-work`

### Nyquist Coverage Matrix

| Branch / Behavior | Test | Sampling Rationale |
|-------------------|------|-------------------|
| Fixed monthly, no extras | `test_fixed_rate_oracle[wikipedia]` | Wikipedia oracle: simplest baseline, locks the fundamental math |
| Fixed monthly, no extras (different rate/term) | `test_fixed_rate_oracle[cfpb_le]` | Lower rate; pins regulator-published example |
| Fixed monthly, scale-up | `test_fixed_rate_oracle[400k]` | 2x principal — proves no scale-dependent bugs |
| Fixed monthly, shorter term | `test_fixed_rate_oracle[200k_15yr]` | 15yr term; proves term-independence |
| Biweekly true | `test_biweekly_true_oracle` | rate/26 + half-of-monthly-pmt + acceleration to ~628 periods |
| Biweekly half-monthly | `test_biweekly_half_monthly_oracle` | rate/12 + monthly schedule + biweekly cashflow label only |
| Extra one-shot | `test_extra_oneshot_period_60` | period 60 only, $5000; shortens term by ~3-4 periods |
| Extra recurring | `test_extra_recurring_200_from_period_1` | $200/period from period 1; shortens schedule meaningfully |
| Extra step-up | `test_extra_step_up_200_to_300_at_period_13` | proves later-recurring-overrides-earlier (D-05) |
| Extra cap-at-balance | `test_extra_caps_at_remaining_balance_silently` | recurring $50k/period on small loan; D-08 cap; final_payment_adjusted=True |
| Final cleanup, fixed | `test_final_payment_cleans_to_zero_fixed` | drift absorption; balance == Decimal("0.00") |
| Final cleanup, biweekly-true | `test_final_payment_cleans_to_zero_biweekly` | accelerated payoff; flag fires |
| AMRT-07 invariant | `assert_schedule_invariants` helper invoked by EVERY schedule-test | sum(principal+extra_principal) == original_principal exact; one assert per test |
| D-15 model invariant | `test_schedule_total_interest_matches_last_cumulative` | direct construction tests with mismatched values raise ValidationError |
| Month-end edge | `test_month_end_origination_clips_to_feb_28` | Jan 31 + 1mo → Feb 28; locks dateutil behavior |
| Date synthesis | `test_build_schedule_synthesizes_origination_when_none` | D-12 path with monkeypatch on datetime.now |
| CLI happy path | `test_cli_smoke_subprocess_round_trip` | subprocess: write input JSON, run script, parse output JSON |
| CLI fast --help | `test_cli_help_does_not_import_lib_amortize` | timing-sensitive OR import-mock check |
| CLI missing input | `test_cli_no_input_returns_pydantic_error` | exit 2 + Pydantic JSON on stderr |
| CLI invalid JSON | `test_cli_invalid_json_input` | exit 2 + structured error |
| CLI float in money field | `test_cli_rejects_float_principal` | Pydantic strict-mode rejection at boundary |
| AMRT-08 oracle parity | `test_fixed_rate_oracle` parametrized over `golden_pmt.json` | 4 fixtures × exact `==` comparison; AMRT-08 contract |

### Wave 0 Gaps

- [ ] `tests/test_amortize.py` — new file; 20-25 test functions covering AMRT-01..08 + D-15 + month-end + CLI
- [ ] `tests/conftest.py` — extend with `amortize_fixture` loader (small change to existing file)
- [ ] `tests/fixtures/amortize/` — new directory; 11 JSON fixtures listed in §9
- [ ] `lib/amortize.py` — production code (engine + ExtraPrincipalEntry + AmortizeRequest)
- [ ] `lib/models.py` — extend Payment with `cumulative_interest` + `cumulative_principal`; extend Schedule with `final_payment_adjusted` + D-15 validator; UPDATE `tests/test_models.py::test_schedule_aggregates_loan_and_payments` to satisfy new validator
- [ ] `scripts/amortize.py` — new file; argparse + lazy-import + Pydantic boundary
- [ ] `pyproject.toml` — `numpy-financial` already pinned (==1.0.0); no change needed unless planner adds optional dev dep (NOT recommended — see §8)

### Helper to define once

```python
# tests/test_amortize.py (recommended top-of-file helper)
from decimal import Decimal
from lib.models import Schedule

def assert_schedule_invariants(schedule: Schedule, original_principal: Decimal) -> None:
    """Asserts AMRT-07 + D-11 + D-15 invariants on every produced schedule."""
    sum_principal = sum((p.principal for p in schedule.payments), start=Decimal("0.00"))
    sum_extra = sum((p.extra_principal for p in schedule.payments), start=Decimal("0.00"))
    assert sum_principal + sum_extra == original_principal, (
        f"AMRT-07/D-11 violated: sum(principal+extra)={sum_principal + sum_extra} != "
        f"original_principal={original_principal}"
    )
    assert schedule.payments[-1].balance == Decimal("0.00"), \
        f"final balance != 0.00: {schedule.payments[-1].balance}"
    # D-15 already enforced by validator; redundant assertion as a defense-in-depth tripwire
    assert schedule.total_interest == schedule.payments[-1].cumulative_interest
```

Every schedule-producing test ends with `assert_schedule_invariants(sched, loan.principal)`. This is the project's "trust but verify" idiom for the AMRT-07 contract.

---

## 11. numpy-financial Bug Avoidance

### Inline-comment template for `lib/amortize.py` module docstring

```python
"""Schedule generator wrapping numpy-financial PMT/IPMT/PPMT.

...

numpy-financial bug avoidance (per CONTEXT.md "Specific Ideas" + STACK.md verdict matrix):
  - Bug #130 (npf.pmt fv-sign flipped when fv != 0):
      https://github.com/numpy/numpy-financial/issues/130
      We always pass fv=0 (default). Phase 3 has no balloon-mortgage path.
      Phase 5 ARM (re-amortizes mid-stream with new principal/rate) ALSO uses fv=0.
      If a future phase needs fv != 0, audit this bug FIRST.
  - Bug #131 (npf.irr arch-dependent):
      https://github.com/numpy/numpy-financial/issues/131
      We never use npf.irr. Phase 6 refi NPV / Phase 7 estimated APR will use pyxirr
      and/or our own Newton-Raphson per Reg Z Appendix J.

numpy-financial 1.0.0 returns Decimal when fed Decimal (verified empirically 2026-04-29).
Sign convention: npf.pmt/ipmt/ppmt return cashflow-out (negative); we flip with `-` at
the boundary. Never go through float — see CLAUDE.md money discipline.
"""
```

### Phase 3 confirmed safe-paths

| Operation | npf call | fv used? | irr used? | Safe? |
|-----------|----------|----------|-----------|-------|
| Level monthly P&I | `npf.pmt(rate, n, principal)` | No (default 0) | No | ✓ |
| Per-period interest (oracle/test only) | `npf.ipmt(rate, period, n, principal)` | No (default 0) | No | ✓ |
| Per-period principal (oracle/test only) | `npf.ppmt(rate, period, n, principal)` | No (default 0) | No | ✓ |

[VERIFIED: bugs catalogued in `.planning/research/STACK.md` and `.planning/research/PITFALLS.md`; both confirmed in CONTEXT.md "Specific Ideas" line 186]

[CITED: https://github.com/numpy/numpy-financial/issues/130, https://github.com/numpy/numpy-financial/issues/131]

---

## 12. Vectorization Decision

**Decision: scalar per-period iteration. Phase 8 may revisit.**

| Path | Recommended for | Why |
|------|-----------------|-----|
| Scalar per-period iteration | Phase 3 default | Survives extra-principal mid-stream and biweekly-true acceleration; one code path for all 7 scenarios; performance is non-issue at < 800 periods |
| Vectorized `npf.ipmt(rate, np.arange(1, n+1), n, principal)` | Phase 8 stress sweeps if profiling shows it | Faster for fixed-rate parameter grids (no extra-principal); 100x speedup possible per scenario but only when iteration count × scenario count crosses ~50k periods |

**Performance ceiling for Phase 3 scope:**

| Scenario | Periods | Decimal arithmetic ops | Wall time (estimate) |
|----------|---------|------------------------|----------------------|
| 30yr monthly fixed | 360 | ~2,000 | < 5 ms |
| 30yr biweekly true | ~628 | ~3,500 | < 10 ms |
| 30yr biweekly true + extra-principal | ~580 | ~3,500 | < 10 ms |
| 50-scenario stress sweep (Phase 8) | 18,000-31,000 | ~175,000 | < 500 ms |

Even Phase 8's worst-case stress sweep stays under a second on scalar iteration. Vectorization is a future optimization that should be backed by profiler output, not premature.

[VERIFIED: empirical execution shows ~628 biweekly-true periods complete in well under 1 second on the host machine this session]

**Note for Phase 8 planner:** if a stress sweep wants to vectorize, it should call `build_schedule` repeatedly (for the fixed-rate, no-extra-principal subset of scenarios) and compute the parameter grid in numpy outside the schedule generator. Don't add a vector path inside `build_schedule` itself — the branching cost would slow down the common (single-loan) case.

---

## 13. Risk Register

| Risk | Severity | Mitigation | Verification |
|------|----------|------------|--------------|
| **Float drift via numpy-financial intermediate** | HIGH | numpy-financial 1.0.0 is end-to-end Decimal (verified). Module-level test asserts return type of `npf.pmt(Decimal,...,Decimal)` IS `Decimal`. | `test_npf_returns_decimal_when_fed_decimal` (canary) |
| **Quantizing mid-calculation** | HIGH | One `quantize_cents` call per period at end. PITFALLS.md flags this; CLAUDE.md money discipline reinforces. Code review check: every `quantize_cents` call is at the assignment to `interest`, `principal_paid`, `payment`, or `extra_principal` — never mid-expression. | Manual code review + ruff custom rule (deferred); planner can use a grep gate `! grep -E 'quantize_cents.*[+\-*/].*quantize_cents' lib/amortize.py` |
| **`assertAlmostEqual` for money** | MEDIUM | CLAUDE.md forbids; tests use `==`. Linter doesn't catch this; rely on code review + grep gate. | Plan acceptance: `! grep -rE 'assertAlmostEqual' tests/test_amortize.py` |
| **Cents drift NOT absorbed by D-09** | HIGH | Empirical drift is ±$5 across all four oracles; D-09's `principal = balance` cleanup is mathematically exhaustive (it sets the residual to whatever it needs to be). Can't fail unless D-09 is mis-implemented. | `test_final_balance_is_exactly_zero` parametrized over all fixtures |
| **AMRT-07 invariant lies** (computed wrong but test passes) | HIGH | Hand-calculated golden values from external oracles (Wikipedia, CFPB) — not computed in-tree. The 4 oracles serve as anchor points; AMRT-07 invariant adds the mid-period coverage. | AMRT-08's exact-equality assertion against external oracles |
| **`relativedelta` month-end behavior changes** | LOW | dateutil is stable; behavior documented for >5 yrs. Pin a fixture exercising Jan 31 → Feb 28 to lock it. | `test_month_end_origination_clips_to_feb_28` |
| **D-15 validator breaks Phase 1 test** | LOW | Update `tests/test_models.py::test_schedule_aggregates_loan_and_payments` to pass a Payment with matching `cumulative_interest`. One-line change. | Ratified by green Phase 1 + Phase 3 test suites |
| **`Schedule.monthly_pi` semantics drift in biweekly modes** | MEDIUM | `monthly_pi` always equals the implied monthly P&I (`-npf.pmt(rate/12, term_months, principal)` quantized), regardless of frequency or biweekly_mode. Biweekly cashflow visibility is a `notes`-level concern (deferred). Document prominently in `lib/amortize.py` docstring + `--help`. | `test_biweekly_schedule_monthly_pi_equals_monthly_oracle` |
| **CLI lazy-import broken** (heavy imports leak into `--help`) | LOW | `--help` benchmark (< 100ms) + import-mock test that fails if `lib.amortize` is imported during argparse. | `test_cli_help_skips_lib_amortize_import` |
| **`extra_principal` cap silently underpays a real legitimate scenario** | LOW | D-08 documented behavior; `final_payment_adjusted=True` is the surface signal. Test pins this explicitly. | `test_extra_caps_at_remaining_balance_silently` |
| **By-luck-zero-drift schedule** sets `final_payment_adjusted=False` accidentally when extra-principal triggered the schedule shortening | LOW | Detection rule (§5) compares formulaic vs actual final principal — handles all paths uniformly. Edge-case test pins this. | `test_final_payment_adjusted_fires_on_extra_principal_acceleration_even_when_zero_drift` |
| **Half-monthly mode emits biweekly rows instead of monthly** | MEDIUM | Recommendation §3.2 chooses Option A (monthly rows). Document in module docstring. PIN with a fixture asserting `len(payments) == 360` for 30yr half-monthly. | `test_biweekly_half_monthly_emits_360_rows_for_30yr` + Open Question §3.2 awaiting user confirmation |
| **`monthly_pi` field name vs payment frequency confusion in JSON output** | MEDIUM | Phase 1 frozen surface uses `monthly_pi`. For biweekly outputs, the field is named `monthly_pi` but represents the implied-monthly P&I (not the biweekly debit). Document this in the docstring and the `Schedule.notes`-deferred placeholder. Phase 10 SKILL.md must not narrate `monthly_pi` as the actual payment for biweekly schedules. | Documentation in module docstring + Phase 10 dependency note |
| **`numpy_financial` import marked `type: ignore[import-untyped]`** | LOW | Already established by Phase 1 mypy override (line 60-61 of pyproject.toml). Reuse pattern. | mypy --strict green |

---

## 14. Open Questions for the Planner

1. **Half-monthly biweekly schedule shape (Option A vs B)** [§3.2]
   - What we know: D-04 says "interest still booked monthly"; CONTEXT.md "specifics" line 180 reinforces "total interest matches monthly equivalent"; recommendation is Option A (monthly rows).
   - What's unclear: is biweekly cashflow visibility required in the JSON output for v1?
   - Recommendation: planner adopts Option A; if user feedback later requests biweekly cashflow visibility, add via `Schedule.notes` (currently deferred per CONTEXT.md Deferred Ideas).

2. **D-15 validator vs test enforcement** [§6]
   - What we know: validator catches the invariant for ALL Schedule constructions; test catches only test-suite cases.
   - What's unclear: does the `test_schedule_aggregates_loan_and_payments` Phase 1 test get updated, or do we use a test-only approach?
   - Recommendation: model-level validator + update Phase 1 test (one-line change).

3. **`Schedule.monthly_pi` field semantics in biweekly mode** [Risk Register]
   - What we know: Phase 1 frozen surface uses `monthly_pi`; the field is the implied-monthly P&I, not the biweekly cashflow.
   - What's unclear: should biweekly schedules surface a per-period payment field separately?
   - Recommendation: stick with Phase 1 surface; document the semantic in `lib/amortize.py` module docstring; defer per-period-payment surfacing to Phase 10 (where SKILL.md narrates).

4. **CLI fast-`--help` benchmark technique** [§7]
   - What we know: lazy-import is the standard pattern; the recommended skeleton imports `lib.amortize` only after `parser.parse_args()`.
   - What's unclear: is the test for "fast --help" timing-based (`time python scripts/amortize.py --help < 100ms`) or import-mock (assert `sys.modules['lib.amortize']` is absent before parse_args)?
   - Recommendation: import-mock approach. Timing-based tests are flaky; mocking `sys.modules` and asserting absence of the heavy modules at parse-args time is deterministic.

5. **Property-based testing (Hypothesis) for AMRT-07** [§10]
   - What we know: Phase 1 + Phase 2 didn't use Hypothesis. AMRT-07 is a perfect candidate (any valid Loan should satisfy `sum(principal_payments) + sum(extra_principal_payments) == original_principal`).
   - What's unclear: scope creep risk — adding `hypothesis` to dev deps for this single phase.
   - Recommendation: defer Hypothesis; stick with parametrized fixture-based tests in Phase 3. Add `hypothesis` in Phase 8 stress when parameter grids justify it.

6. **`ExtraPrincipalEntry` placement: `lib/amortize.py` vs `lib/models.py`** [§7]
   - What we know: CONTEXT.md "Claude's Discretion" prefers `lib/amortize.py` (scoped) until a second consumer needs it. Phase 4 affordability + Phase 5 ARM + Phase 8 stress could all eventually consume this shape.
   - What's unclear: if Phase 5 (ARM re-amortization) wants to compose `extra_principal` mid-stream, does it import from `lib.amortize` or expect it in `lib.models`?
   - Recommendation: keep in `lib/amortize.py` for Phase 3 (scoped); promote to `lib/models.py` when Phase 5 plan-checker flags the import. Mirrors Phase 2's `FilingStatus` / `LoanPurpose` scoping pattern.

---

## RESEARCH COMPLETE

Confidence: **HIGH** — math, library behavior, and oracle parity are empirically verified this session against the project's installed `numpy-financial==1.0.0`; all design choices are anchored either to CONTEXT.md decisions D-01..D-19 (locked) or to research/PITFALLS.md (verified). Six open questions remain for the planner; none are blockers — all have a recommended default. Phase 3 is unambiguous and ready to plan.
