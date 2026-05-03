---
phase: 08
plan: 03
type: execute
wave: 3
depends_on: ["08-00", "08-01"]
files_modified:
  - lib/points.py
autonomous: true
requirements: ["PNTS-01", "PNTS-02"]
tags:
  - phase-08
  - stress-points
  - engine
must_haves:
  truths:
    - "lib.points.simple_breakeven(points_cost, monthly_savings) returns int (months) via math.ceil(points_cost / monthly_savings); returns None when monthly_savings <= 0"
    - "lib.points.npv_breakeven(points_cost, monthly_savings, hold_months, discount_rate_annual) returns (cum_npv_at_hold, months_to_npv_zero | None) via cumulative discounted-sum walk"
    - "lib.points.evaluate(req) dispatches on req.mode; both from_savings and from_loans modes return PointsResponse with simple AND npv side-by-side, diverge flag, decision dispatcher"
    - "PNTS-01 + PNTS-02 closed at the math layer (CLI in Plan 08-04; fixture-driven divergence pin in Plan 08-05)"
    - "2 Wave 0 xfails flipped: simple_breakeven + npv_breakeven engine smoke"
---

<objective>
Implement the discount-points breakeven engine: two pure-function helpers (`simple_breakeven`, `npv_breakeven`) plus the `evaluate()` dispatcher. Math is straightforward — simple is one ceil-division, NPV is a cumulative discounted-sum walk over months. Phase 6 cross-phase coupling (project-wide discount-rate convention) is DEFERRED via caller-supplied discount_rate_annual (Plan 08-01 D-02 contract).
</objective>

<context>
@.planning/phases/08-stress-points/08-PATTERNS.md (§Pattern 5)
@.planning/phases/08-stress-points/08-RESEARCH.md (§5)
@lib/points.py (Plan 08-01 type contract; this plan adds bodies)
@lib/amortize.py (build_schedule for from_loans mode; Schedule.monthly_pi)
@lib/money.py (CENT, quantize_cents)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement lib.points.simple_breakeven</name>
  <files>lib/points.py</files>
  <action>
    Add to lib/points.py:

    ```python
    import math


    def simple_breakeven(points_cost: Money, monthly_savings: Money) -> int | None:
        """PNTS-01: months_to_breakeven = ceil(points_cost / monthly_savings).

        Returns None when monthly_savings <= 0 (rate-up scenario; points cost MORE
        than they save). Caller surfaces a warning in PointsResponse.warnings.

        Both inputs are Money (Decimal). Division is Decimal-safe; we use
        math.ceil with explicit Decimal-to-int conversion via the // 1 pattern
        that produces an integer Decimal, then int() at the boundary.
        """
        if monthly_savings <= Decimal("0"):
            return None
        # Decimal-safe ceil: (a / b).to_integral_value(rounding=ROUND_CEILING)
        from decimal import ROUND_CEILING, localcontext
        from lib.money import MONEY_CONTEXT
        with localcontext(MONEY_CONTEXT):
            quotient = points_cost / monthly_savings
            ceiled = quotient.to_integral_value(rounding=ROUND_CEILING)
        return int(ceiled)
    ```
  </action>
  <acceptance_criteria>
    - `grep -c 'def simple_breakeven' lib/points.py` returns 1
    - Smoke: `python -c "from decimal import Decimal; from lib.points import simple_breakeven; print(simple_breakeven(Decimal('8000.00'), Decimal('65.40')))"` prints `123`
    - Edge: `python -c "from decimal import Decimal; from lib.points import simple_breakeven; print(simple_breakeven(Decimal('8000.00'), Decimal('-10.00')))"` prints `None`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Implement lib.points.npv_breakeven</name>
  <files>lib/points.py</files>
  <action>
    Add to lib/points.py:

    ```python
    def npv_breakeven(
        points_cost: Money,
        monthly_savings: Money,
        hold_months: int,
        discount_rate_annual: Rate,
    ) -> tuple[Money, int | None]:
        """PNTS-02 + ROADMAP SC-4: cumulative-NPV walk; returns (cum_npv_at_hold, months_to_zero | None).

        Per 08-RESEARCH §5.2:
            r_monthly = discount_rate_annual / 12
            cum_npv(m) = sum_{k=1..m} (monthly_savings / (1 + r_monthly)^k) - points_cost

        Walks month-by-month from 1 to hold_months; returns the first m where
        cum_npv >= 0 as months_to_zero, or None if it never crosses within hold.

        Discount rate of ZERO collapses NPV to simple breakeven (no time-value
        adjustment). Negative monthly_savings → cum_npv strictly decreases →
        returns (cum_npv_at_hold, None) and discount-rate has no effect on the
        break-detection (caller's simple_breakeven also returns None; warning
        gets surfaced at the response level).

        Returns the final cum_npv_at_hold so the dispatcher can compute the
        decision (buy_points iff cum_npv_at_hold >= 0).
        """
        from lib.money import quantize_cents, MONEY_CONTEXT
        from decimal import localcontext

        r_monthly = discount_rate_annual / Decimal("12")
        months_to_zero: int | None = None
        with localcontext(MONEY_CONTEXT):
            cum_npv = -Decimal(points_cost)
            discount_factor = Decimal("1")
            multiplier = Decimal("1") / (Decimal("1") + r_monthly) if r_monthly > Decimal("0") else Decimal("1")
            for m in range(1, hold_months + 1):
                discount_factor = discount_factor * multiplier if r_monthly > Decimal("0") else Decimal("1")
                cum_npv = cum_npv + monthly_savings * discount_factor
                if months_to_zero is None and cum_npv >= Decimal("0"):
                    months_to_zero = m
        return quantize_cents(cum_npv), months_to_zero
    ```
  </action>
  <acceptance_criteria>
    - `grep -c 'def npv_breakeven' lib/points.py` returns 1
    - Smoke (zero discount): `python -c "from decimal import Decimal; from lib.points import npv_breakeven; cum, m = npv_breakeven(Decimal('8000.00'), Decimal('65.40'), 240, Decimal('0.000000')); print(m)"` prints `123` (matches simple)
    - Smoke (7% discount): `python -c "from decimal import Decimal; from lib.points import npv_breakeven; cum, m = npv_breakeven(Decimal('8000.00'), Decimal('65.40'), 240, Decimal('0.070000')); print(m)"` prints `160` (matches 08-RESEARCH §5.4 divergence pin)
    - Edge (negative savings): `python -c "from decimal import Decimal; from lib.points import npv_breakeven; cum, m = npv_breakeven(Decimal('8000.00'), Decimal('-10.00'), 120, Decimal('0.07')); print(m)"` prints `None`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Implement lib.points.evaluate dispatcher</name>
  <files>lib/points.py</files>
  <action>
    Replace the NotImplementedError stub from Plan 08-01 with the real dispatcher:

    ```python
    from lib.amortize import build_schedule


    def _derive_monthly_savings(loan_with_points: Loan, loan_without_points: Loan) -> Money:
        """For from_loans mode: run two build_schedule calls and diff monthly_pi."""
        s_with = build_schedule(loan_with_points, frequency="monthly")
        s_without = build_schedule(loan_without_points, frequency="monthly")
        return quantize_cents(s_without.monthly_pi - s_with.monthly_pi)


    def evaluate(req: PointsRequest) -> PointsResponse:
        """PNTS-01 + PNTS-02 + ROADMAP SC-4: report simple AND npv side-by-side; decide buy/skip."""
        from lib.money import quantize_cents
        warnings: list[str] = []

        if isinstance(req, PointsRequestFromLoans):
            monthly_savings = _derive_monthly_savings(req.loan_with_points, req.loan_without_points)
        else:
            monthly_savings = req.monthly_savings

        if monthly_savings <= Decimal("0"):
            warnings.append(f"NEGATIVE_OR_ZERO_SAVINGS_{monthly_savings}")

        simple_m = simple_breakeven(req.points_cost, monthly_savings)
        cum_npv, npv_m = npv_breakeven(
            req.points_cost, monthly_savings, req.hold_period_months, req.discount_rate_annual
        )

        diverge = (simple_m is not None and npv_m is not None and simple_m != npv_m)
        diverge_explanation: str | None = None
        if diverge:
            assert simple_m is not None and npv_m is not None  # mypy narrow
            gap = npv_m - simple_m
            diverge_explanation = (
                f"NPV breakeven {gap:+d} months relative to simple due to "
                f"{req.discount_rate_annual} annual discount rate eroding present value of late savings"
            )

        decision: Literal["buy_points", "skip_points"] = (
            "buy_points" if cum_npv >= Decimal("0") else "skip_points"
        )
        if simple_m is None:
            decision = "skip_points"

        return PointsResponse(
            simple_breakeven_months=simple_m,
            npv_breakeven_months=npv_m,
            diverge=diverge,
            diverge_explanation=diverge_explanation,
            decision=decision,
            discount_rate_used=req.discount_rate_annual,
            hold_period_months=req.hold_period_months,
            monthly_savings=quantize_cents(monthly_savings),
            cumulative_npv_at_hold=cum_npv,
            warnings=warnings,
        )
    ```
  </action>
  <acceptance_criteria>
    - `grep -c 'def evaluate' lib/points.py` returns 1 (real dispatcher; stub gone)
    - `grep -c 'NotImplementedError' lib/points.py` returns 0
    - Smoke from_savings: `python -c "from decimal import Decimal; from lib.points import evaluate, PointsRequestFromSavings; r = evaluate(PointsRequestFromSavings(points_cost=Decimal('8000.00'), monthly_savings=Decimal('65.40'), hold_period_months=240, discount_rate_annual=Decimal('0.070000'))); print(r.simple_breakeven_months, r.npv_breakeven_months, r.diverge, r.decision)"` prints `123 160 True buy_points`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Flip 2 Wave 0 xfails (points engine smoke)</name>
  <files>tests/test_points.py</files>
  <action>
    Flip these 2 tests from xfail to in-process assertions:

    1. `test_pnts_01_simple_breakeven_ceil_division`:
    ```python
    def test_pnts_01_simple_breakeven_ceil_division() -> None:
        from decimal import Decimal
        from lib.points import simple_breakeven
        assert simple_breakeven(Decimal("8000.00"), Decimal("65.40")) == 123
        assert simple_breakeven(Decimal("8000.00"), Decimal("80.00")) == 100
        # 8000 / 65.40 = 122.3242 → ceil = 123 (NOT 122)
        # Edge: zero / negative savings
        assert simple_breakeven(Decimal("8000.00"), Decimal("0.00")) is None
        assert simple_breakeven(Decimal("8000.00"), Decimal("-1.00")) is None
    ```

    2. `test_pnts_02_npv_breakeven_decision_dispatcher`:
    ```python
    def test_pnts_02_npv_breakeven_decision_dispatcher() -> None:
        from decimal import Decimal
        from lib.points import evaluate, PointsRequestFromSavings
        # Zero discount: simple == npv (no divergence)
        r = evaluate(PointsRequestFromSavings(
            points_cost=Decimal("8000.00"), monthly_savings=Decimal("65.40"),
            hold_period_months=240, discount_rate_annual=Decimal("0.000000")))
        assert r.simple_breakeven_months == 123
        assert r.npv_breakeven_months == 123
        assert r.diverge is False
        assert r.decision == "buy_points"
        # 7% discount: simple==123, npv==160 (08-RESEARCH §5.4 pin)
        r2 = evaluate(PointsRequestFromSavings(
            points_cost=Decimal("8000.00"), monthly_savings=Decimal("65.40"),
            hold_period_months=240, discount_rate_annual=Decimal("0.070000")))
        assert r2.simple_breakeven_months == 123
        assert r2.npv_breakeven_months == 160
        assert r2.diverge is True
        assert r2.diverge_explanation is not None
        assert r2.decision == "buy_points"  # 240 months > 160; cum_npv positive at hold
    ```

    Remove the @pytest.mark.xfail decorator on both.
  </action>
  <acceptance_criteria>
    - `grep -c '@pytest.mark.xfail' tests/test_points.py` returns 3 (was 5; 2 flipped)
    - `pytest tests/test_points.py -v --tb=short` shows 2 passed and 3 xfailed
    - Full suite: ≥420 passed, ≥9 xfailed, 0 failed, 0 errored
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-03-01: simple_breakeven returns None for monthly_savings <= 0 (instead of raising) so the response dispatcher can surface a structured warning rather than an unhandled exception. Mirrors Phase 4 D-11 blocked_by-via-field-not-raise convention.
- D-03-02: npv_breakeven uses month-by-month cumulative walk (NOT closed-form annuity formula). Reasons: (a) easier to verify hand-calc fixture math; (b) matches discrete monthly-payment cadence; (c) supports the "first m where cum_npv >= 0" question naturally. Closed-form would require iterating anyway to find m.
- D-03-03: Discount rate of 0 collapses to simple breakeven (no divergence). Mathematical identity verified by Plan 08-05 fixture `points_simple_eq_npv_zero_discount.json`.
- D-03-04: Decision dispatcher uses `cum_npv_at_hold >= 0` as the buy/skip oracle. If simple_breakeven is None (negative savings), decision is forced to "skip_points" regardless of cum_npv (negative-savings cum_npv is dominated by the points_cost subtraction and stays negative anyway, but the explicit force is defensive).
- D-03-05: from_loans mode runs build_schedule TWICE (once per Loan). Plan 08-04 CLI may add a `--rates "no_points,with_points"` shortcut that synthesizes both Loans in argparse before invoking lib.points.evaluate — pinned in Plan 08-04 LOCKED DECISIONS.
- D-03-06: Phase 6 cross-phase coupling on discount_rate_annual remains DEFERRED. Plan 08-06 references/points-breakeven.md documents starting points (loan rate, 10yr Treasury proxy, zero). When Phase 6 lands, the coupling is closed via a single non-breaking additive edit to lib.points.PointsRequest (default = Phase 6 project-wide convention).
</locked_decisions>

<verify_block>
- simple_breakeven + npv_breakeven + evaluate all importable
- All four Phase 8 §5 fixture-pinned numerical values verified via inline smoke (123 simple, 160 npv at 7%, 123 npv at 0%)
- 2 Wave 0 xfails flipped
- mypy --strict lib/points.py exits 0
- ruff clean
- Phase 6 coupling DEFERRED — no blocker on this plan
</verify_block>

<deviation_rules>
- Rule 1: If Decimal localcontext(MONEY_CONTEXT) precision (28 digits) loses precision in long-horizon NPV walks (240+ months at 7%), increase precision context per-call OR document the known cents-drift in the decision threshold. The Plan 08-05 fixture pins 160-month NPV at 7% — if the engine returns 159 or 161, that's a precision regression.
- Rule 2: If `Loan.model_copy(update={"annual_rate": rate})` triggers re-validation surprises in from_loans mode (e.g., loan_type changes downstream), pin the workaround in SUMMARY.md.
- Rule 3: Documentation-only fix to references/points-breakeven.md (Phase 6 coupling note, discount-rate guidance) lives in Plan 08-06.
</deviation_rules>

<success_criteria>
- PNTS-01 + PNTS-02 closed at the math layer (PNTS-03 CLI in Plan 08-04; SC-4 fixture in Plan 08-05)
- 2 of 5 Wave 0 points xfails flipped
- mypy + ruff clean across lib/points.py
- 7%-discount divergence numerical pin (123 → 160 months) verified by inline smoke
- Phase 6 discount-rate coupling DEFERRED (caller-supplied; non-breaking when Phase 6 lands) — no blocker
</success_criteria>
