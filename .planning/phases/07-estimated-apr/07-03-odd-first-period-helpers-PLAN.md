---
phase: 07
plan: 03
type: execute
wave: 3
depends_on: ["07-02"]
files_modified:
  - lib/apr.py
autonomous: true
requirements: [APR-08]
tags:
  - phase-07
  - estimated-apr
  - day-count
  - odd-first-period
must_haves:
  truths:
    - "lib/apr.py exposes _compute_odd_first_period_fraction(origination, first_payment, day_count) -> Decimal"
    - "Helper handles 30/360, actual/365, actual/actual conventions per RESEARCH §Q(e)"
    - "Helper raises ValueError if first_payment < origination"
    - "solve_apr() optionally consumes APRRequest.odd_first_period_days and rewrites the first PaymentScheduleEntry's unit_period_fraction accordingly"
    - "Hand-calc fixture (15-day odd first period, US 30/360) gives APR ≈ 6.523% on the Wikipedia anchor (verified by Wave 5)"
  artifacts:
    - path: "lib/apr.py"
      provides: "Day-count helpers + odd-first-period integration into solve_apr"
      contains: "def _compute_odd_first_period_fraction"
      min_lines: 550
---

## Goal

Add the day-count + odd-first-period helpers required by Reg Z Appendix J
§(b)(5)(iii) + §1026.17(c)(4). Wire `APRRequest.odd_first_period_days`
into `solve_apr` so the first `PaymentScheduleEntry` carries the
correct `unit_period_fraction`. NO new public surface beyond the helper;
the helper is `lib/apr` private (underscore-prefixed).

## Tasks

### Task 1 — `_compute_odd_first_period_fraction` helper

```python
def _compute_odd_first_period_fraction(
    origination: date,
    first_payment: date,
    day_count: Literal["30/360", "actual/365", "actual/actual"],
) -> Decimal:
    """Return f in [0, 1) per Reg Z §1026.17(c)(4) + Appendix J §(b)(5)(iii).

    For a "long" first period (first_payment more than one unit period after
    origination), the fractional component is the days-beyond-standard
    expressed as a fraction of one unit period in the chosen day-count.

    Raises ValueError if first_payment < origination (negative odd period
    not supported in Phase 7 — RESEARCH OPEN Q1).
    """
    if first_payment < origination:
        raise ValueError(
            f"first_payment ({first_payment}) must be >= origination ({origination}); "
            f"negative odd first period not supported in Phase 7"
        )
    days = (first_payment - origination).days
    if day_count == "30/360":
        unit_days = Decimal("30")
        f = (Decimal(days) - unit_days) / unit_days
    elif day_count == "actual/365":
        unit_days = Decimal("365") / Decimal("12")  # ~30.4167
        f = (Decimal(days) - unit_days) / unit_days
    elif day_count == "actual/actual":
        # Days from origination to one-unit-period-later via relativedelta(months=1)
        actual_unit_end = origination + relativedelta(months=1)
        actual_unit_days = Decimal((actual_unit_end - origination).days)
        f = (Decimal(days) - actual_unit_days) / actual_unit_days
    else:
        raise ValueError(f"unsupported day_count: {day_count!r}")

    # Per §1026.17(c)(4) "small differences" (< 7 days for monthly) are
    # disregarded; we surface the exact fraction and let the U-equation
    # use it. Caller may zero it out if desired.
    if f < Decimal("0"):
        # Short first period (< standard unit). Reg Z math still works for
        # f in (-1, 0); we return as-is.
        return f
    if f >= Decimal("1"):
        raise ValueError(
            f"odd first period >= 1 unit period (days={days}); caller should "
            f"insert an extra t=1 advance instead of stretching the first period"
        )
    return f
```

### Task 2 — Wire into `solve_apr` via `APRRequest.odd_first_period_days`

The Wave 1 `APRRequest.odd_first_period_days: int` field is consumed in
Wave 3. Modify `solve_apr` (Wave 2 body) to apply the fraction to the
first `PaymentScheduleEntry`:

```python
# In solve_apr, BEFORE the Newton seed:
payments_with_odd = list(request.payment_schedule)
if request.odd_first_period_days > 0:
    # Compute fraction relative to the standard unit period
    if request.day_count == "30/360":
        unit_days_dec = Decimal("30")
    elif request.day_count == "actual/365":
        unit_days_dec = Decimal("365") / Decimal("12")
    else:  # actual/actual — caller must supply origination/first_payment via Loan
        # Phase 7 Wave 3 simplification: use 30 days as proxy
        unit_days_dec = Decimal("30")
    f_odd = Decimal(request.odd_first_period_days) / unit_days_dec
    if f_odd >= Decimal("1"):
        raise ValueError(
            f"odd_first_period_days ({request.odd_first_period_days}) >= 1 unit period; "
            f"insert an extra advance entry instead"
        )
    first = payments_with_odd[0]
    payments_with_odd[0] = first.model_copy(update={"unit_period_fraction": f_odd})

# Then use payments_with_odd in place of request.payment_schedule for the
# rest of the function body.
```

### Task 3 — Document day-count conventions in module docstring

Extend the `lib/apr.py` module docstring with a "Day-count conventions"
section listing the three supported values + their formulas. Also note
that the heavy `_compute_odd_first_period_fraction` helper is exported
for advanced callers (e.g., Phase 8 stress) who need to compute fractions
from explicit dates rather than the `odd_first_period_days` integer
shortcut on `APRRequest`.

### Task 4 — Hand-verify Wave-3 integration

Add a one-shot inline test (NO new fixture file yet — Wave 5 ships those):

```python
def test_odd_first_period_15_days_increases_apr_above_nominal() -> None:
    """Wave 3 sanity: 15-day odd first period on a 6.5%/30yr should give APR > 0.065."""
    from lib.apr import solve_apr, APRRequest, AdvanceScheduleEntry, PaymentScheduleEntry
    from lib.models import Loan
    request = APRRequest(
        loan=Loan(principal=Decimal("200000.00"), annual_rate=Decimal("0.065000"), term_months=360),
        finance_charges=Decimal("0.00"),
        advance_schedule=[AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("200000.00"))],
        payment_schedule=[PaymentScheduleEntry(starting_unit_period=1, periods=360, amount=Decimal("1264.14"))],
        day_count="30/360",
        odd_first_period_days=15,
    )
    response = solve_apr(request)
    assert response.estimated_apr > Decimal("0.065000"), \
        f"15-day odd first period should push APR above 6.50% nominal; got {response.estimated_apr}"
    assert response.estimated_apr < Decimal("0.070000"), \
        f"15-day odd first period should not push APR above 7.00%; got {response.estimated_apr}"
```

This test is REPLACED by a fixture-backed sibling in Wave 5; it stays in
Wave 3 as the "engine smoke" gate.

## Acceptance

- `grep -c 'def _compute_odd_first_period_fraction' lib/apr.py` returns 1
- `grep -c 'odd_first_period_days' lib/apr.py` returns ≥3 (model field + solve_apr + helper)
- `grep -c '"30/360"\|"actual/365"\|"actual/actual"' lib/apr.py` returns ≥4 (model literal + helper branches)
- `pytest tests/test_apr.py::test_odd_first_period_15_days_increases_apr_above_nominal -v` PASSES
- mypy --strict lib/apr.py clean
- ruff check + format clean
- `pytest -q 2>&1 | tail -5` shows ≥432 + ≥3 passed (Phase 5 baseline + Wave 1+2+3 flips)

## LOCKED DECISIONS

- **D-15:** Day-count conventions supported are `Literal["30/360", "actual/365", "actual/actual"]`. Default `"30/360"` (Wave 1 D-02).
- **D-16:** `_compute_odd_first_period_fraction` returns Decimal in [-1, 1) — short first periods (negative f) are mathematically valid per Reg Z; long first periods >= 1 unit period are rejected (caller must insert an extra advance).
- **D-17:** `APRRequest.odd_first_period_days` is the user-friendly shortcut; the engine internally rewrites the first `PaymentScheduleEntry.unit_period_fraction`. Advanced callers can bypass by setting `unit_period_fraction` directly on `PaymentScheduleEntry` and leaving `odd_first_period_days=0`.
- **D-18:** "Small differences" (< 7 days) per §1026.17(c)(4) are NOT auto-zeroed by the engine — the engine reports the exact fraction. Caller (or future Phase 8 stress wrapper) may zero them; documented in `references/apr-reg-z.md` §3.

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
pytest tests/test_apr.py::test_odd_first_period_15_days_increases_apr_above_nominal -v
mypy --strict lib/apr.py
ruff check lib/apr.py
ruff format --check lib/apr.py
pytest -q 2>&1 | tail -5
```

## Deviation Rules

- Rule-1: changes to the `Literal[...]` set require plan + Wave 1 model revision.
- Rule-2: hand-verify the 15-day example before declaring done. If APR is
  below the 6.5% nominal, the U-equation has a sign flip in the (1+f·i)
  factor.
- Rule-3: hygiene only.

## Cross-wave Dependency Notes

- **Upstream:** Wave 2 (solve_apr body must exist).
- **Downstream:** Wave 5 ships `regz_appendix_j_odd_first_period_15_days.json`
  + `_45_days.json` fixtures that exercise this helper end-to-end.
- This wave does NOT close any APR-XX requirement directly; APR-08
  (references doc) cites the helper in Wave 6.
