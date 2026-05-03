---
phase: 06
plan: 03
type: execute
wave: 3
depends_on:
  - "06-00"
  - "06-01"
  - "06-02"
files_modified:
  - lib/refinance.py
  - tests/test_refinance.py
autonomous: true
requirements:
  - REFI-02
  - REFI-07
tags:
  - phase-06
  - refinance-npv
  - cash-out
  - after-tax
  - irs-pub936
must_haves:
  truths:
    - "evaluate_cash_out body composes Wave 2 helpers + cash-out-specific logic per RESEARCH §'(c) Cash-Out Mechanics' + Oracle 3"
    - "cash_proceeds_net = cash_out_amount - closing_costs surfaced as RefiResponse.cash_proceeds (NEVER negative — D-12 disallows financing into loan in v1)"
    - "total_interest_delta = new_loan.total_interest - old_loan_residual.total_interest (signed; positive when new costs more interest)"
    - "After-tax mode (D-09) wired: when after_tax_mode=True, _compute_tax_shield_cashflows builds period-by-period tax_shield inflow stream from IRS Pub 936 qualified_loan_limit (RUL-11)"
    - "Cross-field validator _validate_after_tax_inputs (D-09) enforces marginal_tax_rate + filing_status both supplied when after_tax_mode=True"
    - "Public evaluate(req: RefiRequest) -> RefiResponse dispatcher routes by refi_kind discriminator"
    - "Oracle 3 (cash-out) reproduces exact Decimal values"
  artifacts:
    - path: "lib/refinance.py"
      provides: "evaluate_cash_out body + _compute_tax_shield_cashflows helper + _validate_after_tax_inputs (Wave-1 stub fully wired) + public evaluate() dispatcher"
---

<objective>
Ship the cash-out engine + the optional after-tax savings overlay + the public `evaluate()` dispatcher. Closes REFI-02 (cash-out NPV) + REFI-07 (cash-out fixture math). After-tax mode (D-09) becomes operational; previously-emitted Wave-2 warning is replaced with real tax_shield cashflows.
</objective>

<context>
@.planning/phases/06-refinance-npv/06-RESEARCH.md
@.planning/phases/06-refinance-npv/06-PATTERNS.md
@lib/refinance.py
@lib/rules/irs_pub936.py
@tests/test_refinance.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire _validate_after_tax_inputs (Wave 1 left this conditional logic incomplete)</name>
  <files>lib/refinance.py</files>
  <action>
    Update `_validate_common` to enforce D-09 verbatim:
    ```python
    if req.after_tax_mode:
        if req.marginal_tax_rate is None or req.filing_status is None:
            raise ValueError(
                "after_tax_mode=True requires both marginal_tax_rate and filing_status "
                "(D-09; cites lib.rules.irs_pub936.qualified_loan_limit / RUL-11; "
                "see references/refi-npv.md §'After-Tax Optional Mode')"
            )
    ```
    Flip Wave-0 stub `test_after_tax_mode_validator_requires_all` to a real test exercising both rejection cases (missing marginal_tax_rate / missing filing_status) AND the happy-path (all three supplied).
  </action>
  <acceptance_criteria>
    - test_after_tax_mode_validator_requires_all passes
    - mypy + ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Implement _compute_tax_shield_cashflows helper</name>
  <files>lib/refinance.py</files>
  <action>
    Add the after-tax helper:
    ```python
    def _compute_tax_shield_cashflows(
        *,
        new_loan: Loan,
        marginal_tax_rate: Decimal,
        filing_status: Literal["single", "mfj", "mfs", "hoh"],
        has_grandfathered_debt: bool,
        horizon_months: int,
    ) -> list[RefiCashflow]:
        """Per-period tax_shield inflow stream (D-09).

        Per RESEARCH §'(f) Tax Treatment':
          qualified_limit = lib.rules.irs_pub936.qualified_loan_limit(filing_status, ...)
          deductible_principal = min(new_principal, qualified_limit)
          deduction_fraction = deductible_principal / new_principal  (Decimal)
          For each period t in 1..horizon:
              interest_t = new_schedule.payments[t-1].interest
              deductible_interest_t = interest_t * deduction_fraction
              tax_shield_t = deductible_interest_t * marginal_tax_rate
              emit RefiCashflow(period=t, direction='inflow', amount=tax_shield_t, kind='tax_shield')
        """
        from lib.rules.irs_pub936 import qualified_loan_limit
        qualified_limit = qualified_loan_limit(
            filing_status=filing_status,
            has_grandfathered_debt=has_grandfathered_debt,
        )
        deductible_principal = min(new_loan.principal, qualified_limit)
        if new_loan.principal == Decimal("0"):
            return []
        deduction_fraction = deductible_principal / new_loan.principal

        new_schedule = build_schedule(new_loan)
        cashflows: list[RefiCashflow] = []
        upper = min(horizon_months, len(new_schedule.payments))
        for t in range(1, upper + 1):
            interest_t = new_schedule.payments[t - 1].interest
            deductible_interest_t = interest_t * deduction_fraction
            tax_shield_t = quantize_cents(deductible_interest_t * marginal_tax_rate)
            if tax_shield_t > Decimal("0.00"):
                cashflows.append(
                    RefiCashflow(
                        period=t,
                        direction="inflow",
                        amount=tax_shield_t,
                        kind="tax_shield",
                    )
                )
        return cashflows
    ```
  </action>
  <acceptance_criteria>
    - Helper importable; returns list[RefiCashflow]
    - mypy + ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Wire evaluate_cash_out body</name>
  <files>lib/refinance.py</files>
  <action>
    Replace Wave-1 NotImplementedError stub with full body following Oracle 3:
    ```python
    def evaluate_cash_out(req: CashOutRefiRequest) -> RefiResponse:
        """Cash-out refi NPV (REFI-02; SC-3).

        New principal = old_balance + cash_out_amount (D-15 NO closing-costs financing in v1).
        Cash proceeds at t=0 = cash_out_amount - closing_costs (NET; D-12 cash-out
        convention; can be negative if costs > cash, but D-12 documents this is
        unusual in practice and surfaces in the JSON without flag).

        Total interest delta = new_schedule.total_interest - old_residual.total_interest.
        """
        # 1: build loans
        old_loan = _build_old_loan_residual(
            balance_remaining=req.old_loan_balance,
            annual_rate=req.old_annual_rate,
            remaining_months=req.old_remaining_months,
        )
        new_principal = req.old_loan_balance + req.cash_out_amount
        new_loan = _build_new_loan(
            new_principal=new_principal,
            new_annual_rate=req.new_annual_rate,
            new_term_months=req.new_term_months,
        )

        # 2: P&I (override per D-10 if supplied — important for cash-out PMI/MIP cases)
        old_schedule = build_schedule(old_loan)
        new_schedule = build_schedule(new_loan)
        old_monthly_pi = old_schedule.monthly_pi
        new_monthly_pi = (
            req.new_loan_monthly_pi_override
            if req.new_loan_monthly_pi_override is not None
            else new_schedule.monthly_pi
        )

        # 3: signed deltas
        monthly_payment_delta = new_monthly_pi - old_monthly_pi  # signed; positive = pay more
        monthly_savings = old_monthly_pi - new_monthly_pi        # signed; mirror of above
        cash_proceeds_net = quantize_cents(req.cash_out_amount - req.closing_costs)
        total_interest_delta = quantize_cents(
            new_schedule.total_interest - old_schedule.total_interest
        )

        # 4: horizon (D-11)
        horizon = req.analysis_horizon_months or new_loan.term_months

        # 5: cashflows — closing costs NOT a separate t=0 outflow (already netted into cash_proceeds_net per D-12)
        cashflows = _build_refi_cashflows(
            closing_costs=Decimal("0.00"),  # netted into cash_proceeds_net
            old_monthly_pi=old_monthly_pi,
            new_monthly_pi=new_monthly_pi,
            horizon_months=horizon,
            cash_proceeds_net=cash_proceeds_net,
        )

        # 6: after-tax overlay (D-09)
        after_tax_npv: Decimal | None = None
        if req.after_tax_mode:
            assert req.marginal_tax_rate is not None and req.filing_status is not None  # validator
            tax_shield_cashflows = _compute_tax_shield_cashflows(
                new_loan=new_loan,
                marginal_tax_rate=req.marginal_tax_rate,
                filing_status=req.filing_status,
                has_grandfathered_debt=req.has_grandfathered_debt,
                horizon_months=horizon,
            )
            cashflows_with_shield = cashflows + tax_shield_cashflows
            after_tax_npv = _compute_npv(
                quantize_rate(req.discount_rate_annual),
                cashflows_with_shield,
                horizon,
            )

        # 7: NPV (pre-tax)
        discount_rate = quantize_rate(req.discount_rate_annual)
        npv = _compute_npv(discount_rate, cashflows, horizon)

        # 8: breakeven (cash-out: simple is "no_savings"; NPV-breakeven typically 0 if cash > 0)
        simple_months, simple_status = _compute_breakeven_simple(req.closing_costs, monthly_savings)
        npv_months, npv_status = _compute_breakeven_npv(discount_rate, cashflows, horizon)

        return RefiResponse(
            refi_kind="cash_out",
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
            cash_proceeds=cash_proceeds_net if cash_proceeds_net >= Decimal("0") else None,
            monthly_payment_delta=quantize_cents(monthly_payment_delta),
            total_interest_delta=total_interest_delta,
            after_tax_npv=after_tax_npv,
            discount_rate_annual_used=discount_rate,
            analysis_horizon_months_used=horizon,
            cashflows=cashflows,
            warnings=[],
        )
    ```
  </action>
  <acceptance_criteria>
    - evaluate_cash_out callable; Oracle 3 reproduces cash_proceeds=$47000.00, new_monthly_pi=$1498.88, total_interest_delta near $145,711 (Wave 5 fixture pins exact)
    - mypy + ruff clean
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Wire public evaluate() dispatcher + after-tax for rate-and-term path</name>
  <files>lib/refinance.py</files>
  <action>
    Replace `evaluate` stub:
    ```python
    def evaluate(req: RefiRequest) -> RefiResponse:
        """Public dispatcher; routes by refi_kind discriminator (D-02)."""
        if isinstance(req, RateAndTermRefiRequest):
            return evaluate_rate_and_term(req)
        if isinstance(req, CashOutRefiRequest):
            return evaluate_cash_out(req)
        raise ValueError(f"Unknown refi_kind: {req!r}")  # defensive; discriminator should have caught
    ```

    Also extend `evaluate_rate_and_term` to compute after_tax_npv when after_tax_mode=True (replaces Wave-2 warning):
    ```python
    if req.after_tax_mode:
        assert req.marginal_tax_rate is not None and req.filing_status is not None
        tax_shield_cashflows = _compute_tax_shield_cashflows(
            new_loan=new_loan,
            marginal_tax_rate=req.marginal_tax_rate,
            filing_status=req.filing_status,
            has_grandfathered_debt=req.has_grandfathered_debt,
            horizon_months=horizon,
        )
        after_tax_npv = _compute_npv(
            discount_rate, cashflows + tax_shield_cashflows, horizon
        )
        # populate after_tax_npv in response (replace warning emission from Wave 2)
    ```

    Remove the Wave-2 placeholder warning ("after_tax_mode=True surfaced; Wave 3 will populate"); replace with real after_tax_npv value.
  </action>
  <acceptance_criteria>
    - `evaluate(rate_and_term_req)` returns RefiResponse with refi_kind='rate_and_term'
    - `evaluate(cash_out_req)` returns RefiResponse with refi_kind='cash_out'
    - When after_tax_mode=True: response.after_tax_npv != None
    - Wave-2 warning string no longer present
    - mypy + ruff clean
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-09 wired: after-tax mode opt-in; cross-field validator enforces marginal_tax_rate + filing_status when on
- D-12 cash-out closing-costs convention: NETTED into cash_proceeds (NOT a separate t=0 outflow)
- D-15 cash-out new_principal computation: old_balance + cash_out_amount (no closing-costs financing in v1)
- RUL-11 (lib.rules.irs_pub936.qualified_loan_limit) consumed for after-tax deductibility cap
</locked_decisions>

<verify_block>
- evaluate(req) dispatcher routes correctly
- Oracle 3 cash-out values match expected (cash_proceeds=$47k, monthly_payment_delta≈+$66.02)
- After-tax mode populates after_tax_npv when on
- All Wave 1 + Wave 2 tests still pass
- Phase 5 baseline preserved
- mypy --strict + ruff clean
</verify_block>

<deviation_rules>
- Rule-1: cash-out cash_proceeds may be negative if closing_costs > cash_out_amount; D-12 documents this is unusual but legal. RefiResponse.cash_proceeds set to None in that pathological case (consumer-friendly: "no positive proceeds"). Document in evaluate_cash_out docstring.
- Rule-2: if after-tax NPV would require an index path or APR Phase 7 has not yet shipped, abort and flag — Phase 6 must NOT depend on Phase 7.
</deviation_rules>

<success_criteria>
- Oracle 3 cash-out reproduces; SC-3 fields populated
- After-tax mode operational (D-09) for both rate-and-term + cash-out
- Phase 5 baseline held; Wave 1+2 tests still PASS
- mypy --strict + ruff clean
</success_criteria>
