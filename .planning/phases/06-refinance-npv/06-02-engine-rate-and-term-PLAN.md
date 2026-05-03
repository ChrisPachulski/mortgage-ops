---
phase: 06
plan: 02
type: execute
wave: 2
depends_on:
  - "06-00"
  - "06-01"
files_modified:
  - lib/refinance.py
  - tests/test_refinance.py
autonomous: true
requirements:
  - REFI-01
  - REFI-03
tags:
  - phase-06
  - refinance-npv
  - engine
  - npv
  - breakeven
must_haves:
  truths:
    - "lib/refinance.py defines build_refi_cashflows + compute_npv + compute_breakeven_simple + compute_breakeven_npv as private helpers"
    - "evaluate_rate_and_term body composes the helpers and returns a fully-populated RefiResponse with sign convention preserved (D-04: closing costs negative, savings positive)"
    - "compute_npv wraps numpy_financial.npv (AMRT-01 wrap-not-reimplement inheritance), Decimal-typed, quantize_cents at boundary only"
    - "compute_breakeven_simple returns (None, 'no_savings') when monthly_savings <= 0; (0, 'zero_costs') when closing_costs == 0; (ceil(closing/savings), 'ok') otherwise"
    - "compute_breakeven_npv runs cumulative-NPV scan per D-06 (numpy_financial.irr is broken per bug #131; do NOT use)"
    - "Pinned oracles 1 + 2 (positive-NPV + negative-NPV from RESEARCH §'Pinned Oracles') reproduced exactly via Decimal equality"
  artifacts:
    - path: "lib/refinance.py"
      provides: "evaluate_rate_and_term body + 4 private helpers + module-internal _build_old_loan_residual + _build_new_loan helpers; ~250 net new lines"
      contains: "def evaluate_rate_and_term"
---

<objective>
Build the rate-and-term refi engine: 4 private helpers (`_build_refi_cashflows`, `_compute_npv`, `_compute_breakeven_simple`, `_compute_breakeven_npv`) plus 2 Loan-construction helpers (`_build_old_loan_residual`, `_build_new_loan`), composed into `evaluate_rate_and_term(req: RateAndTermRefiRequest) -> RefiResponse`. The body wraps `numpy_financial.npv` per AMRT-01 wrap-not-reimplement discipline.

Closes the engine layer of REFI-01 + REFI-03 (rate-and-term + dual breakeven). Cash-out (REFI-02) ships in Wave 3 but reuses the same primitives.

Output: ~250 net new lines in lib/refinance.py; pinned oracles 1 + 2 reproduce exactly.
</objective>

<context>
@.planning/phases/06-refinance-npv/06-RESEARCH.md
@.planning/phases/06-refinance-npv/06-PATTERNS.md
@lib/refinance.py
@lib/amortize.py
@lib/affordability.py
@lib/money.py
@tests/test_refinance.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement Loan-construction helpers + cashflow builder</name>
  <files>lib/refinance.py</files>
  <action>
    Add private helpers below the cross-plan stubs:

    ```python
    def _build_old_loan_residual(
        balance_remaining: Decimal,
        annual_rate: Decimal,
        remaining_months: int,
    ) -> Loan:
        """Construct a synthetic Loan representing the OLD loan as it stands today
        (the borrower's residual obligation if they don't refi).

        Uses the OLD rate over the REMAINING term — NOT the original term.
        Documented in references/refi-npv.md §'Cashflow Inventory'.
        """
        return Loan(
            principal=quantize_cents(balance_remaining),
            annual_rate=quantize_rate(annual_rate),
            term_months=remaining_months,
            origination_date=None,  # synthesized at engine time per Phase 3 D-12
            loan_type="fixed",
        )

    def _build_new_loan(
        new_principal: Decimal,
        new_annual_rate: Decimal,
        new_term_months: int,
    ) -> Loan:
        """Construct the NEW loan post-refi (rate-and-term: new_principal == old_balance;
        cash-out: new_principal == old_balance + cash_out_amount per D-15)."""
        return Loan(
            principal=quantize_cents(new_principal),
            annual_rate=quantize_rate(new_annual_rate),
            term_months=new_term_months,
            origination_date=None,
            loan_type="fixed",
        )

    def _build_refi_cashflows(
        *,
        closing_costs: Decimal,
        old_monthly_pi: Decimal,
        new_monthly_pi: Decimal,
        horizon_months: int,
        cash_proceeds_net: Decimal = Decimal("0.00"),  # cash-out only
    ) -> list[RefiCashflow]:
        """Enumerate the per-period RefiCashflow stream for both refi kinds.

        D-04 sign convention enforced via RefiCashflow validator at construction.
        D-15: closing costs always at t=0 as direction='outflow', amount=-closing_costs.

        For rate-and-term: cash_proceeds_net=0; t=1..horizon emits monthly_savings
        (= old_pi - new_pi) as direction='inflow' (positive when new < old; the
        validator REJECTS the cashflow if savings is negative — engine-side caller
        must classify direction by sign).

        For cash-out: t=0 also gets +cash_proceeds_net inflow; t=1..horizon emits
        monthly_payment_delta. Wave 3 (Plan 06-03) calls this with cash_proceeds_net>0.
        """
        cashflows: list[RefiCashflow] = []

        # t=0: closing costs (always outflow; D-15)
        if closing_costs > Decimal("0"):
            cashflows.append(
                RefiCashflow(
                    period=0,
                    direction="outflow",
                    amount=-quantize_cents(closing_costs),
                    kind="closing_costs",
                )
            )

        # t=0: cash proceeds (cash-out only)
        if cash_proceeds_net > Decimal("0"):
            cashflows.append(
                RefiCashflow(
                    period=0,
                    direction="inflow",
                    amount=quantize_cents(cash_proceeds_net),
                    kind="cash_proceeds",
                )
            )

        # t=1..horizon: monthly savings or payment delta
        # Sign-classify per D-04: savings > 0 → inflow; savings < 0 (i.e., new_pi > old_pi) → outflow
        per_period_signed = old_monthly_pi - new_monthly_pi  # positive = savings; negative = extra cost
        if per_period_signed != Decimal("0"):
            for t in range(1, horizon_months + 1):
                if per_period_signed > Decimal("0"):
                    cashflows.append(
                        RefiCashflow(
                            period=t,
                            direction="inflow",
                            amount=quantize_cents(per_period_signed),
                            kind="monthly_savings",
                        )
                    )
                else:
                    cashflows.append(
                        RefiCashflow(
                            period=t,
                            direction="outflow",
                            amount=quantize_cents(per_period_signed),  # already negative
                            kind="monthly_payment_delta",
                        )
                    )
        return cashflows
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python -c "from lib.refinance import _build_old_loan_residual, _build_new_loan, _build_refi_cashflows; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - All 3 helpers defined and importable
    - mypy + ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Implement _compute_npv + breakeven helpers</name>
  <files>lib/refinance.py</files>
  <action>
    Add NPV + breakeven helpers below the cashflow builder:

    ```python
    def _flatten_cashflows_to_per_period(
        cashflows: list[RefiCashflow],
        horizon_months: int,
    ) -> list[Decimal]:
        """Collapse cashflow list into a length-(horizon+1) Decimal array indexed by t.

        npf.npv eats `values` starting at t=0 (RESEARCH §'Watch Out For'). Multiple
        cashflows at the same period (e.g., closing_costs + cash_proceeds at t=0)
        sum together at that index.
        """
        per_period: list[Decimal] = [Decimal("0.00")] * (horizon_months + 1)
        for cf in cashflows:
            if cf.period > horizon_months:
                continue  # truncate per D-11
            per_period[cf.period] = per_period[cf.period] + cf.amount
        return per_period

    def _compute_npv(
        discount_rate_annual: Decimal,
        cashflows: list[RefiCashflow],
        horizon_months: int,
    ) -> Decimal:
        """Wrap numpy_financial.npv (AMRT-01 inheritance: wrap, do not reimplement).

        Per-period rate = discount_rate_annual / 12. quantize_cents AT THE BOUNDARY ONLY
        (Phase 1 PITFALLS; Phase 4 PITI idiom). Intermediate computation stays at
        full Decimal precision via lib.money.MONEY_CONTEXT (28 digits).
        """
        period_rate = discount_rate_annual / Decimal("12")
        values = _flatten_cashflows_to_per_period(cashflows, horizon_months)
        npv = npf.npv(period_rate, values)  # numpy-financial 1.0.0 returns Decimal when fed Decimal
        return quantize_cents(npv)

    def _compute_breakeven_simple(
        closing_costs: Decimal,
        monthly_savings: Decimal,
    ) -> tuple[int | None, Literal["ok", "no_savings", "zero_costs"]]:
        """REFI-03 first formula: ceil(closing_costs / monthly_savings).

        Edge cases per RESEARCH §'(d) Divergence':
          monthly_savings <= 0 → (None, 'no_savings')
          closing_costs == 0  → (0, 'zero_costs')
          else → (ceil(closing/savings), 'ok')
        """
        if closing_costs == Decimal("0"):
            return 0, "zero_costs"
        if monthly_savings <= Decimal("0"):
            return None, "no_savings"
        # Ceiling divide via Decimal
        from decimal import ROUND_CEILING
        months_d = (closing_costs / monthly_savings).quantize(Decimal("1"), rounding=ROUND_CEILING)
        return int(months_d), "ok"

    def _compute_breakeven_npv(
        discount_rate_annual: Decimal,
        cashflows: list[RefiCashflow],
        horizon_months: int,
    ) -> tuple[int | None, Literal["ok", "never_breaks_even"]]:
        """REFI-03 second formula: smallest n where cumulative NPV(0..n) >= 0.

        Per D-06: cumulative-NPV scan, NOT npf.irr (bug #131 — arch-dependent).
        """
        period_rate = discount_rate_annual / Decimal("12")
        per_period = _flatten_cashflows_to_per_period(cashflows, horizon_months)
        for n in range(0, horizon_months + 1):
            cumulative = npf.npv(period_rate, per_period[:n + 1])
            if cumulative >= Decimal("0"):
                return n, "ok"
        return None, "never_breaks_even"
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python -c "from lib.refinance import _compute_npv, _compute_breakeven_simple, _compute_breakeven_npv; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - All 4 helpers defined; importable
    - mypy + ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Wire evaluate_rate_and_term body</name>
  <files>lib/refinance.py</files>
  <action>
    Replace the Wave-1 NotImplementedError stub with the full body:

    ```python
    def evaluate_rate_and_term(req: RateAndTermRefiRequest) -> RefiResponse:
        """Rate-and-term refi NPV (REFI-01).

        Pipeline (mirrors lib/affordability.py::evaluate_forward 12-step shape):
          1. Build OLD-loan residual schedule via Phase 3 build_schedule;
             extract old_monthly_pi (= schedule.monthly_pi).
          2. Build NEW loan with new principal == old_balance (rate-and-term
             definition), new_annual_rate, new_term_months.
          3. Extract new_monthly_pi (or use req.new_loan_monthly_pi_override
             per D-10 when supplied).
          4. monthly_savings = old_monthly_pi - new_monthly_pi (signed).
          5. horizon = req.analysis_horizon_months or new_loan.term_months
             (D-11 default = full new term).
          6. Build cashflows via _build_refi_cashflows (closing_costs at t=0
             as outflow per D-15; per-period savings as inflow when positive).
          7. NPV via _compute_npv.
          8. Breakeven (simple + NPV) via _compute_breakeven_*.
          9. Construct RefiResponse with all populated fields.

        After-tax mode (D-09): when req.after_tax_mode=True, Wave 3 (Plan 06-03)
        adds a tax_shield branch. Wave 2 emits a warning if after_tax_mode=True
        (signaling "feature ships in Wave 3"); Wave 3 swaps in the real branch.
        """
        # 1-2: build loans
        old_loan = _build_old_loan_residual(
            balance_remaining=req.old_loan_balance,
            annual_rate=req.old_annual_rate,
            remaining_months=req.old_remaining_months,
        )
        new_loan = _build_new_loan(
            new_principal=req.old_loan_balance,  # rate-and-term: same principal
            new_annual_rate=req.new_annual_rate,
            new_term_months=req.new_term_months,
        )

        # 3: P&I (use override if supplied per D-10)
        old_monthly_pi = build_schedule(old_loan).monthly_pi
        new_monthly_pi = (
            req.new_loan_monthly_pi_override
            if req.new_loan_monthly_pi_override is not None
            else build_schedule(new_loan).monthly_pi
        )

        # 4: signed savings
        monthly_savings = old_monthly_pi - new_monthly_pi

        # 5: horizon
        horizon = req.analysis_horizon_months or new_loan.term_months

        # 6: cashflows
        cashflows = _build_refi_cashflows(
            closing_costs=req.closing_costs,
            old_monthly_pi=old_monthly_pi,
            new_monthly_pi=new_monthly_pi,
            horizon_months=horizon,
            cash_proceeds_net=Decimal("0.00"),  # rate-and-term has no proceeds
        )

        # 7: NPV
        discount_rate = quantize_rate(req.discount_rate_annual)
        npv = _compute_npv(discount_rate, cashflows, horizon)

        # 8: breakeven
        simple_months, simple_status = _compute_breakeven_simple(req.closing_costs, monthly_savings)
        npv_months, npv_status = _compute_breakeven_npv(discount_rate, cashflows, horizon)

        # 9: response
        warnings_list: list[str] = []
        if req.after_tax_mode:
            warnings_list.append(
                "after_tax_mode=True surfaced; Wave 3 (Plan 06-03) will populate after_tax_npv"
            )

        return RefiResponse(
            refi_kind="rate_and_term",
            npv=npv,
            breakeven=RefiBreakeven(
                simple_months=simple_months,
                simple_status=simple_status,
                npv_months=npv_months,
                npv_status=npv_status,
            ),
            old_monthly_pi=old_monthly_pi,
            new_monthly_pi=new_monthly_pi,
            monthly_savings=quantize_cents(monthly_savings),
            cash_proceeds=None,
            monthly_payment_delta=None,
            total_interest_delta=None,
            after_tax_npv=None,
            discount_rate_annual_used=discount_rate,
            analysis_horizon_months_used=horizon,
            cashflows=cashflows,
            warnings=warnings_list,
        )
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python -c "
from decimal import Decimal
from lib.refinance import RateAndTermRefiRequest, evaluate_rate_and_term
req = RateAndTermRefiRequest(
    old_loan_balance=Decimal('300000.00'), old_annual_rate=Decimal('0.070000'), old_remaining_months=300,
    new_annual_rate=Decimal('0.050000'), new_term_months=300,
    closing_costs=Decimal('2000.00'), discount_rate_annual=Decimal('0.050000'),
)
resp = evaluate_rate_and_term(req)
print('npv', resp.npv)
print('savings', resp.monthly_savings)
print('simple_be', resp.breakeven.simple_months)
print('npv_be', resp.breakeven.npv_months)
assert resp.npv > Decimal('0'), f'SC-1 positive: NPV not positive: {resp.npv}'
print('SC-1 positive PASS')
"</automated>
  </verify>
  <acceptance_criteria>
    - Oracle 1 (positive-NPV) returns NPV > 0
    - Oracle 2 (negative-NPV at horizon=12) returns NPV < 0 (verify via second python -c invocation)
    - Cashflow list non-empty; first entry is closing_costs at period=0 with negative amount
    - mypy + ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Empirically derive exact Decimal NPV values for Oracles 1 + 2; document in docstring</name>
  <files>lib/refinance.py</files>
  <action>
    Run the engine on Oracle 1 + Oracle 2 setups (RESEARCH §"Pinned Oracles"); capture the EXACT Decimal NPV values returned. Add a `# Pinned Oracle` comment block at the top of evaluate_rate_and_term:

    ```python
    # Pinned Oracles (06-RESEARCH.md §"Pinned Oracles" + Plan 06-05 fixtures):
    #   Oracle 1 (SC-1 positive): old=$300k@7% 25y residual, new=$300k@5% 25y,
    #     closing=$2000, discount=5%, horizon=300 → NPV = <DERIVED_VALUE>
    #   Oracle 2 (SC-1 negative): same but horizon=12 → NPV = <DERIVED_VALUE>
    # These values are the contract Wave 5 fixtures pin against via Decimal equality.
    ```

    Replace <DERIVED_VALUE> with the actual values from the verify step. Plan 06-05 (fixtures) consumes these.
  </action>
  <acceptance_criteria>
    - Comment block present with both derived values pinned
    - Both values reproduce exactly when re-running the verify python -c snippet
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-04 sign convention enforced at cashflow construction (RefiCashflow validator from Wave 1) — engine code never bypasses.
- D-06 breakeven uses cumulative-NPV scan (NOT npf.irr).
- D-11 horizon defaulting (None → new_loan.term_months) preserved verbatim.
- D-15 closing costs at t=0 only.
- AMRT-01 inheritance: npf.npv wrapped, not reimplemented.
</locked_decisions>

<verify_block>
- evaluate_rate_and_term importable + callable
- Oracle 1 → NPV > 0; Oracle 2 → NPV < 0
- Pinned Decimal values documented in evaluate_rate_and_term docstring
- mypy --strict + ruff clean
- Phase 5 baseline preserved
</verify_block>

<deviation_rules>
- Rule-1 (math): if numpy-financial returns float (not Decimal) for any input shape, STOP and route through gsd-debug. Do NOT silently convert via Decimal(str(npv_result)) — that masks Phase 3 D-04's verified Decimal-in-Decimal-out behavior.
- Rule-2 (sign): if a cashflow construction would violate D-04 sign convention (e.g., trying to construct an inflow with negative savings), the RefiCashflow validator MUST raise. Engine-side caller classifies direction by sign per Task 1.
- Rule-3: hygiene-only deviations noted in SUMMARY.md.
</deviation_rules>

<success_criteria>
- evaluate_rate_and_term ships, returns RefiResponse with all required fields
- Oracle 1 + Oracle 2 reproduce expected sign (>0 / <0)
- Decimal exact values pinned in docstring for Wave 5 fixture consumption
- Phase 5 baseline (≥ 432 passed) held; 5 Wave 1 flips still PASS
- mypy --strict + ruff clean
</success_criteria>
