---
phase: 06
plan: 01
type: execute
wave: 1
depends_on:
  - "06-00"
files_modified:
  - lib/refinance.py
  - tests/test_refinance.py
autonomous: true
requirements:
  - REFI-01
  - REFI-02
tags:
  - phase-06
  - refinance-npv
  - pydantic-models
  - sign-validator
must_haves:
  truths:
    - "lib/refinance.py exists at project root and is importable"
    - "RefiCashflow has direction: Literal['outflow','inflow'] field with @model_validator(mode='after') that rejects positive amount on outflow and negative amount on inflow per SC-4"
    - "RefiCashflow accepts amount=0 in either direction (D-14)"
    - "RefiRequest is a Pydantic v2 discriminated union via Field(discriminator='refi_kind') with RateAndTermRefiRequest + CashOutRefiRequest variants"
    - "RefiResponse Pydantic v2 model with strict+frozen+forbid populated for both refi_kind variants"
    - "All models use ConfigDict(strict=True, frozen=True, extra='forbid')"
    - "Wave 0 stubs test_refi_cashflow_outflow_positive_rejected, test_refi_cashflow_inflow_negative_rejected, test_refi_cashflow_zero_accepted_either_dir, test_refi_cashflow_correctly_signed_passes flip from xfail to PASS"
    - "Phase 5 baseline preserved"
  artifacts:
    - path: "lib/refinance.py"
      provides: "RefiCashflow + _CommonRefiFields + RateAndTermRefiRequest + CashOutRefiRequest + RefiRequest discriminated union + RefiResponse + RefiBreakeven sub-model. NO evaluate() body yet (Wave 2/3 ship engine)."
      min_lines: 200
---

<objective>
Ship the Pydantic v2 model layer of `lib/refinance.py`: 6 strict+frozen+forbid models — RefiCashflow (with the SC-4 sign-validator), RefiBreakeven (sub-model), _CommonRefiFields (base), RateAndTermRefiRequest, CashOutRefiRequest, RefiResponse — plus the RefiRequest discriminated-union alias.

Closes the model-layer half of REFI-01 + REFI-02 + SC-4. Engine bodies arrive in Wave 2 (rate-and-term math) and Wave 3 (cash-out + after-tax). Wave 1 ships ONLY: types + validators + cross-plan stubs for `evaluate_rate_and_term` / `evaluate_cash_out` / `evaluate` (stub bodies raise NotImplementedError with cite to Wave 2/3 plan).
</objective>

<context>
@.planning/phases/06-refinance-npv/06-RESEARCH.md
@.planning/phases/06-refinance-npv/06-PATTERNS.md
@CLAUDE.md
@lib/models.py
@lib/affordability.py
@lib/amortize.py
@tests/test_refinance.py

<interfaces>
Phase 1 imports (lib/models.py:23-46):
```python
Money = Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0"))]
Rate  = Annotated[Decimal, Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1"))]

class Loan(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    principal: Money
    annual_rate: Rate
    term_months: int = Field(ge=1, le=600)
    origination_date: date | None = None
    loan_type: Literal["fixed", "arm", "fha", "va", "usda", "jumbo"] = "fixed"
```

Phase 4 cross-field validator archetype (lib/affordability.py:507-528):
```python
@model_validator(mode="after")
def _validate_forward(self) -> ForwardModeRequest:
    _validate_common(self)
    return self
```

D-03 RefiCashflow shape (RESEARCH §"(e) RefiCashflow" — locked):
```python
class RefiCashflow(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=0)  # t=0 allowed for closing-costs / cash-out
    direction: Literal["outflow", "inflow"]
    amount: Decimal = Field(strict=True, max_digits=14, decimal_places=2)  # NOT Money — Money is ge=0
    kind: Literal["closing_costs", "cash_proceeds", "monthly_savings", "monthly_payment_delta", "tax_shield"]

    @model_validator(mode="after")
    def _direction_sign_consistency(self) -> "RefiCashflow":
        if self.direction == "outflow" and self.amount > Decimal("0"):
            raise ValueError(...)  # cite D-04 + references/refi-npv.md
        if self.direction == "inflow" and self.amount < Decimal("0"):
            raise ValueError(...)
        return self
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create lib/refinance.py with module docstring + imports + 6 Pydantic models</name>
  <files>lib/refinance.py</files>
  <action>
    Create lib/refinance.py at project root. Mirror lib/affordability.py:1-200 shape.

    Module docstring opens with the BORROWER-PERSPECTIVE SIGN CONVENTION verbatim per D-04:
    > "Refinance NPV (rate-and-term + cash-out) from the borrower's perspective.
    > Sign convention: outflows negative, savings positive. See references/refi-npv.md
    > (REFI-09 / SC-5) for full derivation, discount-rate-selection guidance, and
    > breakeven definitions."

    Then a LOCKED DECISION block summarizing D-01..D-16 inline (mirrors lib/affordability.py:22-172).

    Imports (mirror lib/affordability.py:174-205):
    ```python
    from __future__ import annotations
    from datetime import date
    from decimal import Decimal
    from typing import TYPE_CHECKING, Annotated, Final, Literal

    import numpy_financial as npf
    from pydantic import BaseModel, ConfigDict, Field, model_validator

    from lib.amortize import build_schedule
    from lib.models import Loan, Money, Rate
    from lib.money import quantize_cents, quantize_rate

    if TYPE_CHECKING:
        from collections.abc import Sequence
    ```

    Module-level constants (D-04 + D-05 documentation aids):
    ```python
    SIGN_CONVENTION_CITATION: Final[str] = "references/refi-npv.md (D-04)"

    BREAKEVEN_NEVER_SENTINEL: Final[None] = None
    """When NPV-based or simple breakeven never crosses zero within horizon."""
    ```

    Then ship the 6 models verbatim per RESEARCH §"(e) RefiCashflow" + D-02 structure:

    1. **RefiCashflow** (with @model_validator _direction_sign_consistency per D-03/D-04/D-14)
    2. **RefiBreakeven** sub-model:
       ```python
       class RefiBreakeven(BaseModel):
           model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
           simple_months: int | None
           simple_status: Literal["ok", "no_savings", "zero_costs"]
           npv_months: int | None
           npv_status: Literal["ok", "never_breaks_even"]
       ```
    3. **_CommonRefiFields** base (NOT instantiated):
       ```python
       class _CommonRefiFields(BaseModel):
           model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
           old_loan_balance: Money
           old_annual_rate: Rate
           old_remaining_months: int = Field(ge=1, le=600)
           new_annual_rate: Rate
           new_term_months: int = Field(ge=1, le=600)
           closing_costs: Money  # D-15 top-level
           discount_rate_annual: Rate  # D-05 REQUIRED
           analysis_horizon_months: int | None = Field(default=None, ge=1, le=600)  # D-11
           # D-09 after-tax mode (defaults to off)
           after_tax_mode: bool = False
           marginal_tax_rate: Rate | None = None
           filing_status: Literal["single", "mfj", "mfs", "hoh"] | None = None
           has_grandfathered_debt: bool = False
           # D-10 override for cash-out PMI/MIP cases
           new_loan_monthly_pi_override: Money | None = None
       ```

    4. **_validate_common(req)** function (mirrors lib/affordability.py:458-493). Enforces:
       - When `after_tax_mode=True`, `marginal_tax_rate` AND `filing_status` MUST be supplied (D-09)
       - When `after_tax_mode=False`, `marginal_tax_rate` AND `filing_status` SHOULD be None (warn but allow — Plan 06-03)

    5. **RateAndTermRefiRequest(_CommonRefiFields)**:
       ```python
       class RateAndTermRefiRequest(_CommonRefiFields):
           model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
           refi_kind: Literal["rate_and_term"] = "rate_and_term"
           # New principal == old_loan_balance (no equity extraction)

           @model_validator(mode="after")
           def _validate_rate_and_term(self) -> "RateAndTermRefiRequest":
               _validate_common(self)
               return self
       ```

    6. **CashOutRefiRequest(_CommonRefiFields)** with `cash_out_amount: Money` field (Field(gt=Decimal("0"))):
       ```python
       class CashOutRefiRequest(_CommonRefiFields):
           model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
           refi_kind: Literal["cash_out"] = "cash_out"
           cash_out_amount: Money = Field(gt=Decimal("0"))
           # New principal = old_loan_balance + cash_out_amount

           @model_validator(mode="after")
           def _validate_cash_out(self) -> "CashOutRefiRequest":
               _validate_common(self)
               return self
       ```

    7. **RefiRequest** discriminated-union alias:
       ```python
       RefiRequest = Annotated[
           RateAndTermRefiRequest | CashOutRefiRequest,
           Field(discriminator="refi_kind"),
       ]
       ```

    8. **RefiResponse**:
       ```python
       class RefiResponse(BaseModel):
           model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
           refi_kind: Literal["rate_and_term", "cash_out"]
           npv: Decimal = Field(strict=True, max_digits=14, decimal_places=2)  # signed Decimal NOT Money
           breakeven: RefiBreakeven
           old_monthly_pi: Money
           new_monthly_pi: Money
           monthly_savings: Decimal = Field(strict=True, max_digits=14, decimal_places=2)  # signed
           # Cash-out only (None for rate-and-term)
           cash_proceeds: Money | None = None
           monthly_payment_delta: Decimal | None = None
           total_interest_delta: Decimal | None = None
           # After-tax mode only
           after_tax_npv: Decimal | None = None
           # Discount-rate echo (for traceability)
           discount_rate_annual_used: Rate
           analysis_horizon_months_used: int
           # Cashflow audit trail (every period's RefiCashflow for downstream verification)
           cashflows: list[RefiCashflow]
           # Soft warnings
           warnings: list[str] = Field(default_factory=list)
       ```

    9. **Cross-plan stubs** (Phase 2 D-08 idiom — bodies arrive Wave 2/3):
       ```python
       def evaluate_rate_and_term(req: RateAndTermRefiRequest) -> RefiResponse:
           """Wave 2 (Plan 06-02) ships the body."""
           raise NotImplementedError("Plan 06-02 ships rate-and-term engine body")

       def evaluate_cash_out(req: CashOutRefiRequest) -> RefiResponse:
           """Wave 3 (Plan 06-03) ships the body."""
           raise NotImplementedError("Plan 06-03 ships cash-out engine body")

       def evaluate(req: RefiRequest) -> RefiResponse:
           """Wave 4 (Plan 06-04) wires the dispatcher; here as a stub."""
           raise NotImplementedError("Plan 06-04 ships the public dispatcher")
       ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python -c "from lib.refinance import RefiCashflow, RefiBreakeven, RateAndTermRefiRequest, CashOutRefiRequest, RefiRequest, RefiResponse; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'class RefiCashflow' lib/refinance.py` returns 1
    - `grep -c 'class RefiBreakeven' lib/refinance.py` returns 1
    - `grep -c 'class _CommonRefiFields' lib/refinance.py` returns 1
    - `grep -c 'class RateAndTermRefiRequest' lib/refinance.py` returns 1
    - `grep -c 'class CashOutRefiRequest' lib/refinance.py` returns 1
    - `grep -c 'class RefiResponse' lib/refinance.py` returns 1
    - `grep -c 'RefiRequest = Annotated' lib/refinance.py` returns 1
    - `grep -c 'Literal\["outflow", "inflow"\]' lib/refinance.py` returns 1 (RefiCashflow.direction)
    - `grep -c 'def _direction_sign_consistency' lib/refinance.py` returns 1
    - `grep -c 'outflows negative, savings positive' lib/refinance.py` returns ≥ 1 (D-04 cite in module docstring or validator message)
    - `grep -c 'references/refi-npv.md' lib/refinance.py` returns ≥ 2 (module docstring + validator messages per D-16)
    - `grep -c 'ConfigDict(strict=True, frozen=True, extra="forbid")' lib/refinance.py` returns ≥ 6 (one per model)
    - `mypy --strict lib/refinance.py` exits 0
    - `ruff check lib/refinance.py` exits 0
    - `ruff format --check lib/refinance.py` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Flip 4 Wave-0 stubs (SC-4 sign-validator coverage) to passing tests</name>
  <files>tests/test_refinance.py</files>
  <action>
    Remove `@pytest.mark.xfail(strict=True, ...)` from these 4 stubs and ship real bodies:
    - test_refi_cashflow_outflow_positive_rejected
    - test_refi_cashflow_inflow_negative_rejected
    - test_refi_cashflow_zero_accepted_either_dir
    - test_refi_cashflow_correctly_signed_passes
    - test_lib_refinance_module_docstring_cites (D-16 + REFI-09 anchor: assert lib/refinance.py module docstring contains "outflows negative, savings positive" and "references/refi-npv.md")

    Bodies follow RESEARCH §"Oracle 4: SC-4 Sign-Validator Rejection" — use `pytest.raises(ValidationError, match=...)` per Phase 4 idiom.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_refinance.py::test_refi_cashflow_outflow_positive_rejected tests/test_refinance.py::test_refi_cashflow_inflow_negative_rejected tests/test_refinance.py::test_refi_cashflow_zero_accepted_either_dir tests/test_refinance.py::test_refi_cashflow_correctly_signed_passes tests/test_refinance.py::test_lib_refinance_module_docstring_cites -v</automated>
  </verify>
  <acceptance_criteria>
    - All 5 listed tests PASS (no longer XFAIL)
    - Other 20 stubs remain XFAIL
    - Phase 5 baseline preserved (≥ 432 passed; now ≥ 437 with the 5 flipped)
    - mypy + ruff clean
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- **D-01..D-16** inherited from 06-RESEARCH.md verbatim. No re-decision in this plan.
- **Wave 1 scope**: types + validators + stub bodies for evaluate_*. Engine math arrives Wave 2/3.
- **Sign-validator at MODEL LAYER** (not engine): SC-4 rigor demands construction-time rejection per D-03/D-14.
</locked_decisions>

<verify_block>
- All 6 Pydantic models importable from lib.refinance
- 5 Wave-0 stubs flipped (4 SC-4 + 1 module-docstring citation) to PASS
- Remaining 20 stubs still XFAIL
- Phase 5 baseline preserved
- mypy --strict + ruff clean across lib/refinance.py + tests/test_refinance.py
</verify_block>

<deviation_rules>
- Rule-1: model field shapes (RefiCashflow.direction Literal, sign-validator behavior) are LOCKED per D-03/D-04/D-14. Any deviation requires updating 06-RESEARCH.md decisions FIRST.
- Rule-2: NO engine math in this plan. If a Wave-1 task wants to ship `evaluate_rate_and_term` body to "save a wave", STOP — that's a Rule-1 violation against the wave structure.
- Rule-3: hygiene-only (mypy/ruff fixes outside the locked surface) noted as Rule-3 deviations in SUMMARY.md.
</deviation_rules>

<success_criteria>
- lib/refinance.py shipped with 6 models + 1 union alias + 3 cross-plan stubs
- 5 Wave-0 xfail stubs flipped to PASS (SC-4 + D-16 module-docstring)
- 20 stubs remain XFAIL pending Wave 2..6
- Phase 5 baseline (≥ 432 passed) held
- mypy --strict + ruff clean
</success_criteria>
