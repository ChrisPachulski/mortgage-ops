---
phase: 03-core-amortization
reviewed: 2026-04-29T23:30:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - lib/models.py
  - lib/amortize.py
  - scripts/amortize.py
  - tests/test_models.py
  - tests/test_amortize.py
  - tests/conftest.py
  - tests/fixtures/amortize/biweekly_half_monthly_200k_6_5.json
  - tests/fixtures/amortize/biweekly_true_200k_6_5.json
  - tests/fixtures/amortize/extra_caps_at_balance.json
  - tests/fixtures/amortize/extra_oneshot_5k_period_60.json
  - tests/fixtures/amortize/extra_recurring_200_30yr.json
  - tests/fixtures/amortize/extra_step_up_200_to_300.json
  - tests/fixtures/amortize/month_end_jan_31.json
findings:
  critical: 1
  warning: 8
  info: 4
  total: 13
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-04-29T23:30:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 3 ships a deterministic Decimal-only amortization engine with three frequency paths (monthly, biweekly-true, biweekly-half-monthly), file-based JSON CLI, and 35 parametrized test cases. The core math primitives are sound: no float literals appear anywhere in `lib/amortize.py`, `lib/models.py`, or `scripts/amortize.py` (verified via AST scan); `numpy_financial.pmt` returns `Decimal` when fed `Decimal` (verified empirically); `quantize_cents` is correctly applied at end-of-period only; the `parse_float=Decimal` pre-validation gate effectively blocks JSON-float inputs to money fields; and the four golden oracles (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr) all match `monthly_pi` exactly.

That said, adversarial review surfaced one BLOCKER (order-dependent behavior when two recurring `ExtraPrincipalEntry` rows share a `period`) and several WARNINGs covering coverage gaps (no biweekly+extras test, no one-shot+recurring stacking test, no rate=0 / term=1 edge-case tests), an inconsistent error-shape between two CLI failure gates, a `Schedule` validator that silently accepts absurd `total_interest` values when `payments=[]`, and a few maintainability concerns (load-bearing `assert` for type narrowing, redundant cross-cutting validation in two places, biweekly-half-monthly outputs that are byte-identical to monthly outputs without any frequency hint on `Schedule`).

## Critical Issues

### CR-01: `_resolve_extra` is order-dependent when two recurring entries share the same `period`

**File:** `lib/amortize.py:203-207`
**Issue:** `_resolve_extra` selects the active recurring entry with `max(... key=lambda e: e.period, default=None)`. When two `ExtraPrincipalEntry` rows have the same `period` and both are `recurring=True`, Python's `max` returns whichever appears LAST in the input sequence (no tie-breaker on `amount`). The contract in CONTEXT.md D-05 says "the LATEST entry with `entry.period <= p` AND `entry.recurring=True`" — that wording is order-of-list-ambiguous when periods tie. Empirically verified:

```
[ExtraPrincipalEntry(period=1, amount=100, recurring=True),
 ExtraPrincipalEntry(period=1, amount=200, recurring=True)]
  -> _resolve_extra(period=5, ...) returns 100.00

[ExtraPrincipalEntry(period=1, amount=200, recurring=True),
 ExtraPrincipalEntry(period=1, amount=100, recurring=True)]
  -> _resolve_extra(period=5, ...) returns 200.00
```

Two semantically equivalent inputs (sets of entries) produce different schedules — and therefore different `total_interest`, different `num_payments`, different `final_payment_adjusted`. This is a determinism violation in a calc engine whose stated value is "Math correctness first. Every dollar figure that exits this system must be traceable to a tested, deterministic Python function."

**Fix:** Either (a) add a `model_validator` on `AmortizeRequest` rejecting duplicate `(period, recurring)` pairs, or (b) define an explicit tie-breaker (e.g., later in list overrides) AND add a fixture/test pinning the documented behavior. Preferred (a):

```python
@model_validator(mode="after")
def _no_duplicate_recurring_periods(self) -> AmortizeRequest:
    seen: set[int] = set()
    for e in self.extra_principal:
        if e.recurring:
            if e.period in seen:
                raise ValueError(
                    f"duplicate recurring extra_principal at period {e.period}; "
                    "use one entry per period (D-05)"
                )
            seen.add(e.period)
    return self
```

## Warnings

### WR-01: `Schedule` D-15 validator silently accepts absurd `total_interest` when `payments=[]`

**File:** `lib/models.py:76-91`, exercised by `tests/test_models.py:233-248`
**Issue:** The empty-payments branch returns early without validating `total_interest`. Tests/library callers can construct `Schedule(payments=[], total_interest=Decimal("999.99"))` and the model accepts it. The engine never produces empty payments today, but the model is the contract — Phase 5 ARM, Phase 8 stress, and any downstream consumer can construct stub `Schedule`s with internally-inconsistent values. The "constructor convenience for in-progress scaffolds" justification is for Phase 1 — by Phase 3, no engine produces an empty schedule.
**Fix:** When `payments` is empty, require `total_interest == Decimal("0.00")`:

```python
if not self.payments:
    if self.total_interest != Decimal("0.00"):
        raise ValueError(
            f"D-15 invariant: empty schedule must have total_interest=0.00, "
            f"got {self.total_interest}"
        )
    return self
```

### WR-02: CLI emits two different error envelope shapes for two adjacent failure modes

**File:** `scripts/amortize.py:151-163` vs `scripts/amortize.py:169-174`
**Issue:** When the float pre-validation gate fires, the CLI emits a hand-built envelope with keys `{"type", "loc", "msg"}`. When Pydantic's `model_validate_json` fires, the CLI passes through `e.json()` which emits keys `{"type", "loc", "msg", "input", "url"}` (and sometimes `"ctx"`). Two failure paths for closely related errors produce two different shapes on stderr. Phase 9 Node consumer parsing both will need conditional logic; STACK.md says the calc engine returns "JSON; Claude narrates" — heterogeneous shapes break that contract.
**Fix:** Build the float-gate envelope to match Pydantic's full shape (include `"input": null, "url": null`), or alternatively raise a Pydantic `PydanticCustomError` so the same `e.json()` path emits both. The first option is simpler:

```python
envelope = [
    {
        "type": "decimal_type",
        "loc": float_loc,
        "msg": "Input should be a JSON string for money/rate fields ...",
        "input": None,
        "url": "https://docs.pydantic.dev/2.13/concepts/json/",
    }
]
```

### WR-03: Float pre-validation gate fires before `extra="forbid"`, giving misleading errors for unrelated typos

**File:** `scripts/amortize.py:151-164`
**Issue:** `_find_json_float_loc` walks the entire parsed JSON tree and reports the FIRST JSON-float-with-decimal-point or scientific notation it finds. If a user submits `{"loan": {...}, "metadata": {"version": 1.5}}` (an unrecognized top-level key with a float value), the pre-validation gate fires on `metadata.version` and emits `decimal_type` pointing to a field that is not in the schema at all. The actual problem is `extra="forbid"` (the field shouldn't exist), but the user sees a misleading "money field needs a string" error. Future schema additions that introduce any float-accepting field anywhere break this gate's "blanket reject" assumption (documented at line 64-65 as fragile).
**Fix:** Limit the walker to known money/rate JSON paths (`loan.principal`, `loan.annual_rate`, `extra_principal[*].amount`) instead of "anything that smells like a JSON number with a decimal point." This eliminates both the misleading-error case and the future-fragility note in the docstring.

### WR-04: No test exercises one-shot + recurring stacking on the same period (D-05 contract)

**File:** `tests/test_amortize.py` (entire AMRT-04 section)
**Issue:** `_resolve_extra` line 211-212 stacks recurring + one-shot ADDITIVELY when both target the same period. CONTEXT.md D-05 explicitly specifies this: "One-shot entries (recurring=False) fire only when entry.period == p and stack ADDITIVELY on top of the recurring component." The four AMRT-04 fixtures cover:
- one-shot only (`extra_oneshot_5k_period_60.json`)
- recurring only (`extra_recurring_200_30yr.json`)
- two recurring (step-up, `extra_step_up_200_to_300.json`)
- recurring with cap (`extra_caps_at_balance.json`)

None cover one-shot + recurring on the same period. A regression that broke the additive `raw = raw + e.amount` line into `raw = e.amount` would silently pass the entire test suite.
**Fix:** Add a fixture `extra_oneshot_plus_recurring_period_60.json` pinning a recurring `$200` from `period=1` plus a one-shot `$5000` at `period=60`, with the expected row at `period=60` having `extra_principal == "5200.00"`.

### WR-05: No test exercises biweekly + extra_principal (D-06 contract)

**File:** `tests/test_amortize.py` (AMRT-04 section)
**Issue:** All four extras fixtures use `frequency="monthly"`. CONTEXT.md D-06 explicitly defines biweekly extras semantics ("the CALLER divides by 2 — the engine does NOT internally convert"), but no test pins the engine's biweekly extras path. `_build_biweekly_true` line 400 calls `_resolve_extra(period, extra_principal, ...)`. A bug that confused biweekly periods with monthly periods (e.g., always dividing by 2 inside the engine instead of expecting caller-side conversion) would not be caught.
**Fix:** Add a fixture `extra_recurring_biweekly_100.json`: 200k/6.5/30 biweekly-true with `[ExtraPrincipalEntry(period=1, amount=Decimal("100"), recurring=True)]` (the biweekly equivalent of the monthly $200 fixture), and pin engine output verbatim.

### WR-06: No test for rate=0 or term_months=1 / 2 edge cases

**File:** `tests/test_amortize.py`
**Issue:** `Loan` allows `annual_rate=Decimal("0")` (interest-free, non-amortizing) and `term_months=1`. The engine handles these in principle (numpy-financial's `pmt(0, 1, P)` returns `-P`), but neither is exercised. A `term_months=1` schedule has exactly one row and exposes the final-period drift cleanup with no preceding rows to absorb compounding error. A `rate=0` biweekly-true schedule could come close to the `max_periods = term_months*2 + 10` safety bound (line 380).
**Fix:** Add two parametrized cases:

```python
@pytest.mark.parametrize("term_months", [1, 2])
def test_short_term_loan_terminates_correctly(term_months: int) -> None: ...

def test_zero_rate_loan_amortizes_linearly() -> None: ...
```

### WR-07: Load-bearing `assert` for mypy narrowing on `biweekly_mode` strips under `python -O`

**File:** `lib/amortize.py:254`
**Issue:** `assert biweekly_mode == "half-monthly"  # mypy narrowing` runs in dev/test but is COMPLETELY ELIDED when Python is invoked with `-O`. Today the post-assert call to `_build_biweekly_half_monthly` ignores `biweekly_mode` so the missing assertion has no functional impact — but a future refactor that makes `_build_biweekly_half_monthly` consult `biweekly_mode` would crash silently in `-O` mode. Project STACK.md mandates `mypy --strict`; an explicit `if/elif/else` is both narrowing-safe and runtime-safe.
**Fix:**

```python
if biweekly_mode == "half-monthly":
    return _build_biweekly_half_monthly(loan, origination, extra_principal)
raise AssertionError(f"unreachable biweekly_mode: {biweekly_mode!r}")
```

### WR-08: Two failure modes for the same logical D-02 violation (lib vs CLI)

**File:** `lib/amortize.py:246-247` vs `lib/amortize.py:184-186`
**Issue:** `AmortizeRequest._biweekly_mode_consistency` raises a Pydantic `ValidationError`; `build_schedule` raises a plain Python `ValueError` for the same condition. Library callers calling `build_schedule(loan, frequency="monthly", biweekly_mode="true")` directly (Phase 5 ARM, Phase 8 stress will do this) get a `ValueError`; CLI callers get a Pydantic `ValidationError`. Two different exception types for one logical contract violation surfaces as inconsistent error handling at every call site.
**Fix:** Pick one. Recommended: have `build_schedule` re-raise the engine-side check as a `ValidationError` by routing through `AmortizeRequest.model_validate` internally, OR document explicitly that `build_schedule` may raise `ValueError` and update callers' contract. The simpler change is to align both:

```python
# Replace the ValueError on line 247 with:
from pydantic import TypeAdapter
TypeAdapter(AmortizeRequest).validate_python({
    "loan": loan,
    "frequency": frequency,
    "biweekly_mode": biweekly_mode,
})  # raises ValidationError
```

## Info

### IN-01: Schedule output is byte-identical for monthly and biweekly+half-monthly

**File:** `lib/amortize.py:443-460`, fixtures `month_end_jan_31.json` vs `biweekly_half_monthly_200k_6_5.json`
**Issue:** `_build_biweekly_half_monthly` delegates directly to `_build_fixed_monthly`. The resulting `Schedule` has no `frequency` or `biweekly_mode` field — `Schedule.loan` carries only `loan_type`, not `frequency`. CLI consumers JSON-dumping a half-monthly schedule see exactly the same shape as a monthly schedule (and indeed the half-monthly fixture's `expected_schedule_summary` is byte-identical to the corresponding monthly schedule, modulo `final_payment_adjusted=true` which is the same in both for 200k/6.5/30). Phase 10 SKILL.md narration relies on the docstring claim "biweekly cashflow is a billing decoration consumers handle outside the engine," but Phase 10 has no in-band signal on `Schedule` to know which mode produced the rows.
**Fix:** Add an optional `frequency: Literal["monthly", "biweekly"] = "monthly"` and `biweekly_mode: Literal["true", "half-monthly"] | None = None` to `Schedule` so the JSON output preserves what the caller requested. (Defer to Phase 10 if narration doesn't actually need it; raise to WARNING if it does.)

### IN-02: `parse_float=Decimal` also catches scientific-notation integers (e.g., `5e2`)

**File:** `scripts/amortize.py:67-90`
**Issue:** The walker docstring at lines 56-58 says it flags "JSON-numbers-with-decimal-points" but `json.loads(parse_float=Decimal)` also routes scientific-notation literals (`1e2`, `5E+3`) through the float parser, so they too become `Decimal` instances and trigger the gate. Behaviorally OK (such literals violate money discipline equally), but the docstring is slightly wrong.
**Fix:** Update the docstring on lines 56-58 to read: "JSON numbers that are not pure integer literals (i.e., contain a decimal point OR scientific-notation 'e'/'E')."

### IN-03: `ExtraPrincipalEntry.amount` re-declares Money-shaped constraints rather than reusing `Money`

**File:** `lib/amortize.py:163`
**Issue:** `amount: Decimal = Field(strict=True, gt=Decimal("0"), max_digits=14, decimal_places=2)`. This is `Money` minus `ge=0` plus `gt=0`. If `Money`'s shape evolves (e.g., adds rounding context, adds a future serializer config), `amount` won't follow. Project conventions in CLAUDE.md treat `condecimal(max_digits=14, decimal_places=2)` as a single contract; multiple declarations dilute that.
**Fix:** Either define a `PositiveMoney` alias in `lib/models.py` and reuse it here, or add a comment documenting why this isn't `Money` (gt vs ge):

```python
# In lib/models.py:
PositiveMoney = Annotated[
    Decimal,
    Field(strict=True, max_digits=14, decimal_places=2, gt=Decimal("0")),
]
# In lib/amortize.py:
amount: PositiveMoney
```

### IN-04: `ExtraPrincipalEntry.period` has `ge=1` but no upper bound

**File:** `lib/amortize.py:162`
**Issue:** A user can submit `ExtraPrincipalEntry(period=99999, amount=Decimal("100"))` and it validates. The engine never reaches that period for any reasonable schedule; the entry is silently a no-op. No diagnostic. Mortgage UX best-practice is to surface "your entry was ignored because the schedule terminated at period N." This is a Phase 10 narration concern more than a Phase 3 engine concern, but worth pinning.
**Fix:** Either accept silent no-op (current) and document it explicitly in the docstring, or add a cross-field validator on `AmortizeRequest` warning when `entry.period > loan.term_months * 2` (rough biweekly upper bound). Defer to Phase 10 if narration handles it.

---

_Reviewed: 2026-04-29T23:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
