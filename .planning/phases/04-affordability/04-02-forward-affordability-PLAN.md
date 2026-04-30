---
phase: 04-affordability
plan: 02
type: execute
wave: 2
depends_on: ["04-00", "04-01"]
files_modified:
  - lib/affordability.py
autonomous: true
requirements: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-06]
requirements_addressed: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-06]
tags: [phase-4, affordability, forward, dti, ltv, cltv, piti, wave-2]

must_haves:
  truths:
    - "evaluate_forward(req) returns AffordabilityResponse with mode='forward' (D-14)"
    - "DTI front-end = quantize_cents-eligible Decimal: piti / total_gross_monthly_income"
    - "DTI back-end = (piti + sum(monthly_debts)) / total_gross_monthly_income (per RESEARCH §'DTI Convention')"
    - "total_gross_monthly_income = sum(applicant.gross_monthly_income for applicant in applicants) (D-06)"
    - "min_credit_score = min(applicant.credit_score for applicant in applicants) (D-05)"
    - "ltv = loan_amount / property_value (AFFD-02)"
    - "cltv = (loan_amount + sum(junior_liens)) / property_value (AFFD-03; D-discretion: list[Money] sum)"
    - "PITI = quantize_cents(monthly_pi + property_tax_monthly + insurance_monthly + hoa_monthly + monthly_mi) — single quantize at end-of-period (Phase 3 D-04 PITFALLS pattern; D-01)"
    - "monthly_pi = build_schedule(loan).monthly_pi where loan.principal = financed_loan_amount (D-03 auto-finance UFMIP for FHA)"
    - "monthly_mi for FHA = quantize_cents((financed_principal * MIPResult.annual_mip_pct) / Decimal('12')) (RESEARCH §A.3)"
    - "monthly_mi for conventional+LTV>0.80 = caller-supplied request.monthly_pmi (RESEARCH Open Q#1)"
    - "monthly_mi for conventional+LTV<=0.80, VA, USDA, jumbo = Decimal('0.00') (D-02)"
    - "FHA UFMIP financed: financed_loan_amount = request.loan_amount + MIPResult.ufmip; surfaced on response (D-03 option (b); RESEARCH recommendation)"
    - "fha_mip.compute is called with (Loan, original_property_value, endorsement_date=request.endorsement_date_override or date.today()) — RESEARCH §A.3 corrected signature"
    - "loan_type.classify is called with (loan_amount, county, program=TARGET_LOAN_TYPE_TO_PROGRAM[target]) — RESEARCH §A.1 corrected signature"
    - "MissingCountyDataError raised by classify is propagated as Python exception (NOT blocked_by) — Phase 3 D-19 envelope on stderr; D-11 step 1 hard error"
    - "StaleReferenceWarning captured via warnings.catch_warnings(record=True) and surfaced as str(w.message) in response.warnings (D-11)"
  artifacts:
    - path: lib/affordability.py
      provides: "evaluate_forward implementation; private helpers _compute_dti, _compute_ltv, _compute_cltv, _compute_piti, _classify_target_loan_type, _compute_monthly_mi"
      contains: "def evaluate_forward"
      min_lines: 700
  key_links:
    - from: lib/affordability.py
      to: lib/amortize.py
      via: "build_schedule(Loan(...)) call for monthly_pi"
      pattern: "build_schedule\\("
    - from: lib/affordability.py
      to: lib/money.py
      via: "quantize_cents on every Money output"
      pattern: "quantize_cents"
    - from: lib/affordability.py
      to: lib/rules/loan_type.py
      via: "classify(loan_amount, county, program=...)"
      pattern: "loan_type_classify\\(|classify\\("
    - from: lib/affordability.py
      to: lib/rules/fha_mip.py
      via: "compute(loan, original_property_value, endorsement_date)"
      pattern: "fha_mip_compute|fha_mip\\.compute"
---

<objective>
Implement `evaluate_forward(req: ForwardModeRequest) -> AffordabilityResponse` (AFFD-01, AFFD-02, AFFD-03, AFFD-04) and the joint-applicant aggregation helpers (AFFD-06). Composes Phase 1 (`Loan`, `Money`, `Rate`), Phase 2 (`fha_mip.compute`, `loan_type.classify`, `LTV_REQUEST_ELIGIBLE`), and Phase 3 (`build_schedule`, `Schedule.monthly_pi`).

Replaces the Plan 04-01 stub `raise NotImplementedError("forward evaluation shipped in Plan 04-02")` with a full implementation. This plan does NOT implement blocker precedence (Plan 04-04) — it computes the math and lets the response.blocked default to False; Plan 04-04 wires the precedence pipeline that mutates response.blocked / blocked_by.

Purpose: ship the load-bearing forward-mode math. Every dollar figure flows through `quantize_cents`. PITI is summed THEN quantized (Phase 3 D-04 PITFALLS pattern), never per-component-quantized.

Output: `lib/affordability.py` extended with `evaluate_forward` body + private helpers + the `_classify_target_loan_type` cross-walk applier + `_compute_monthly_mi` PMI/MIP composition (handling D-02 + D-03 + RESEARCH §A.2/A.3 corrections + RESEARCH Open Q#1 caller-supplied conventional PMI).

Decisions implemented: D-01 (caller-supplied escrow), D-02 (predicate-derived MI with Open Q#1 amendment), D-03 (auto-finance UFMIP per RESEARCH recommendation), D-04 (property_value per-request), D-05 (min credit_score), D-06 (sum income), D-07 (single-applicant via len==1).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-affordability/04-CONTEXT.md
@.planning/phases/04-affordability/04-RESEARCH.md
@.planning/phases/04-affordability/04-PATTERNS.md
@.planning/phases/04-affordability/04-VALIDATION.md
@.planning/phases/04-affordability/04-01-pydantic-models-PLAN.md
@CLAUDE.md
@lib/affordability.py
@lib/amortize.py
@lib/money.py
@lib/models.py
@lib/rules/loan_type.py
@lib/rules/fha_mip.py
@lib/rules/conventional_pmi.py
@lib/rules/_loader.py

<interfaces>
<!-- Phase 2 predicates Plan 04-02 calls. SIGNATURES VERIFIED (RESEARCH §"Phase 2 Predicate Signature Audit"). -->

From lib/rules/loan_type.py:
```python
def classify(
    loan_amount: Decimal,
    county: County | None,
    program: Literal["conventional", "fha", "va", "usda"] = "conventional",
    unit_count: int = 1,
) -> LoanType  # 8-value Literal: conforming|high_balance|jumbo|fha_standard|fha_high_balance|va_standard|va_high_balance|usda
# Raises MissingCountyDataError(ValueError) when county is None and loan_amount > baseline
```

From lib/rules/fha_mip.py:
```python
def compute(
    loan: Loan,
    original_property_value: Decimal,
    endorsement_date: date,
) -> MIPResult
# MIPResult.ufmip: Decimal (dollar amount; e.g. 0.0175 * principal)
# MIPResult.annual_mip_pct: Decimal (fractional; e.g. 0.0055 = 55 bps)
# MIPResult.terminates_at_period: int | Literal["life_of_loan"]
# Raises NotImplementedError for endorsement_date < 2023-03-20 ("pre-2023-03-20" substring)
```

From lib/rules/conventional_pmi.py:
```python
LTV_REQUEST_ELIGIBLE: Final[Decimal] = Decimal("0.80")  # used directly per RESEARCH §A.2 — not status()
```

From lib/amortize.py:
```python
def build_schedule(
    loan: Loan,
    *,
    frequency: Literal["monthly", "biweekly"] = "monthly",
    biweekly_mode: Literal["true", "half-monthly"] | None = None,
    extra_principal: Sequence[ExtraPrincipalEntry] = (),
) -> Schedule
# Schedule.monthly_pi: Money
```

From lib/money.py:
```python
def quantize_cents(value: Decimal) -> Decimal  # ROUND_HALF_UP, project-wide single source
```

From lib/rules/_loader.py:
```python
class StaleReferenceWarning(UserWarning): ...  # captured via warnings.catch_warnings(record=True)
```

From lib/affordability.py (Plan 04-01):
```python
TARGET_LOAN_TYPE_CROSSWALK: dict[str, frozenset[str]]  # target → accepted Phase 2 LoanType values
TARGET_LOAN_TYPE_TO_PROGRAM: dict[str, Literal["conventional", "fha", "va", "usda"]]
LTV_REQUEST_ELIGIBLE: Decimal("0.80")  # re-exported from conventional_pmi
class ForwardModeRequest, AffordabilityResponse: ...  # see Plan 04-01
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add Phase 2 predicate imports + private helpers (_compute_dti, _compute_ltv, _compute_cltv, _classify_target_loan_type, _compute_monthly_mi, _build_loan_for_amortization)</name>
  <files>lib/affordability.py</files>
  <read_first>
    - lib/affordability.py (Plan 04-01 state — preserve all existing code)
    - lib/amortize.py (lines 138-200 imports + helper organization)
    - lib/rules/loan_type.py (lines 1-100 — classify signature + MissingCountyDataError)
    - lib/rules/fha_mip.py (lines 1-130 — compute signature + MIPResult shape)
    - lib/rules/types.py (full file — County construction)
    - lib/money.py (full file — quantize_cents)
    - .planning/phases/04-affordability/04-PATTERNS.md §"Watch Out For" (RESEARCH §A.1-A.3 corrections)
  </read_first>
  <behavior>
    - Test 1: `_compute_dti(Decimal("3000.00"), Decimal("500.00"), Decimal("10000.00"))` returns `(Decimal("0.30"), Decimal("0.35"))` exactly (front_dti = 3000/10000 = 0.30; back_dti = (3000+500)/10000 = 0.35)
    - Test 2: `_compute_ltv(Decimal("400000.00"), Decimal("500000.00"))` returns Decimal("0.80") exactly
    - Test 3: `_compute_cltv(Decimal("400000.00"), [Decimal("50000.00"), Decimal("25000.00")], Decimal("500000.00"))` returns Decimal("0.95") exactly (= 475000/500000)
    - Test 4: `_compute_cltv(Decimal("400000.00"), [], Decimal("500000.00"))` returns Decimal("0.80") (empty junior_liens reduces to LTV)
    - Test 5: `_classify_target_loan_type(loan_amount=Decimal("400000"), county=King_WA_County, target="conventional")` returns ("conforming", None) — accepted, no blocker
    - Test 6: `_classify_target_loan_type(loan_amount=Decimal("2000000"), county=King_WA_County, target="conventional")` returns ("jumbo", "FHFA-LIMIT-CONFORMING-WA-033") — outside cross-walk acceptance set
    - Test 7: `_classify_target_loan_type(loan_amount=Decimal("2000000"), county=None, target="conventional")` raises `MissingCountyDataError` (propagates Phase 2 RUL-01 loud-fail; D-11 step 1 hard error, NOT blocked_by)
    - Test 8: `_compute_monthly_mi(target_loan_type="conventional", loan_amount=Decimal("400000"), property_value=Decimal("500000"), monthly_pmi=None, ...)` returns Decimal("0.00") (LTV=0.80 not > 0.80; no PMI)
    - Test 9: `_compute_monthly_mi(target_loan_type="conventional", loan_amount=Decimal("425000"), property_value=Decimal("500000"), monthly_pmi=Decimal("145.83"), ...)` returns Decimal("145.83") (LTV=0.85 > 0.80; caller-supplied per RESEARCH Open Q#1)
    - Test 10: `_compute_monthly_mi(target_loan_type="fha", loan_amount=Decimal("400000"), ...)` returns the predicate-derived monthly value: `quantize_cents((financed_principal * MIPResult.annual_mip_pct) / Decimal("12"))`
    - Test 11: `_compute_monthly_mi(target_loan_type="va", ...)` returns Decimal("0.00")
    - Test 12: `_compute_monthly_mi(target_loan_type="usda", loan_amount, ...)` returns USDA annual fee converted to monthly: `quantize_cents((loan_amount * Decimal("0.0035")) / Decimal("12"))` (RESEARCH §"lib/rules/usda.py" — guarantee_fee_annual / 12)
    - Test 13: `_build_loan_for_amortization(principal=Decimal("407000"), annual_rate=Decimal("0.0700"), term_months=360)` returns a `Loan(principal=407000, annual_rate=0.0700, term_months=360, origination_date=date.today(), loan_type="fixed")`
  </behavior>
  <action>
    Edit `lib/affordability.py` (preserving Plan 04-01 content). Add the following AFTER the cross-walk constants but BEFORE the `evaluate_forward` stub:

    **A. Extend imports block (immediately after existing imports):**
    ```python
    import warnings
    from datetime import date

    import numpy_financial as npf  # used by Plan 04-03 reverse; lazy-import-friendly here

    from lib.amortize import build_schedule
    from lib.money import quantize_cents

    # Phase 2 predicates — full-path imports per Phase 2 D-08 (one predicate per citation).
    # Imported here (not under TYPE_CHECKING) because evaluate_forward calls them at runtime.
    from lib.rules.loan_type import (
        MissingCountyDataError,
        classify as loan_type_classify,
    )
    from lib.rules.fha_mip import compute as fha_mip_compute
    from lib.rules._loader import StaleReferenceWarning
    from lib.rules.types import County
    ```

    Note: `npf` is imported at module top, mirroring `lib/amortize.py`. Plan 04-05 lazy-imports `lib.affordability` inside `main()` (D-13 / Phase 3 D-18), so `numpy_financial` does NOT load on `--help` fast path.

    **B. Add USDA annual fee constant:**
    ```python
    # USDA annual guarantee fee rate (per lib.rules.usda compute formula
    # guarantee_fee_annual = loan_amount * 0.0035; RESEARCH §"lib/rules/usda.py").
    # Sourced directly here (not via predicate call) for Phase 4 PITI composition,
    # because USDA predicate's evaluate(...) is consulted by Plan 04-04 for blocker
    # precedence; the rate scalar is statutory/contractual and stable.
    USDA_ANNUAL_FEE_RATE: Final[Decimal] = Decimal("0.0035")
    ```
    Add `from typing import Final` to imports if not already present.

    **C. Add private helpers (after constants):**

    ```python
    def _build_county(location: LocationFIPS) -> County:
        """Construct a Phase 2 County from Household.location FIPS codes (RESEARCH Open Q#2)."""
        return County(
            state_fips=location.state_fips,
            county_fips=location.county_fips,
            name=location.county_name,
        )


    def _build_loan_for_amortization(
        principal: Decimal,
        annual_rate: Decimal,
        term_months: int,
        origination_date: date | None = None,
    ) -> Loan:
        """Build a Phase 1 Loan for build_schedule consumption.

        loan_type='fixed' is the amortization-mode tag (NOT regulatory classification).
        Phase 2's 8-value LoanType is the regulatory result and lives on
        AffordabilityResponse.loan_type, not on this internal Loan.
        """
        return Loan(
            principal=quantize_cents(principal),
            annual_rate=annual_rate,
            term_months=term_months,
            origination_date=origination_date or date.today(),
            loan_type="fixed",
        )


    def _compute_dti(
        piti: Decimal,
        sum_monthly_debts: Decimal,
        total_gross_monthly_income: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """Compute (front_end_dti, back_end_dti) per AFFD-01 + RESEARCH §"DTI Convention".

        front_end = piti / income (housing-only ratio)
        back_end  = (piti + non-housing-debts) / income (total-debt ratio)

        Returns ratios as Decimal (NOT quantize_cents — DTI is a rate, not money;
        ratios stay at full Decimal precision for the round-trip closure tolerance
        in D-09).
        """
        front = piti / total_gross_monthly_income
        back = (piti + sum_monthly_debts) / total_gross_monthly_income
        return front, back


    def _compute_ltv(loan_amount: Decimal, property_value: Decimal) -> Decimal:
        """LTV = loan_amount / property_value (AFFD-02). Decimal precision preserved."""
        return loan_amount / property_value


    def _compute_cltv(
        loan_amount: Decimal,
        junior_liens: Sequence[Decimal],
        property_value: Decimal,
    ) -> Decimal:
        """CLTV = (loan_amount + sum(junior_liens)) / property_value (AFFD-03).

        v1 uses list[Money] (sum) per CONTEXT.md Claude's discretion. Empty junior_liens
        reduces CLTV to LTV.
        """
        total = loan_amount + sum(junior_liens, start=Decimal("0"))
        return total / property_value


    def _classify_target_loan_type(
        loan_amount: Decimal,
        county: County,
        target_loan_type: TargetLoanType,
    ) -> tuple[LoanType, str | None]:
        """Run lib.rules.loan_type.classify with the corrected signature
        (RESEARCH §A.1) and check the result against TARGET_LOAN_TYPE_CROSSWALK.

        Returns (classified_type, blocker_citation):
          - classified_type: the Phase 2 8-value LoanType returned by classify
          - blocker_citation: None if classified_type is in the accepted set for
            target_loan_type; otherwise a citation string formatted as:
              FHFA-LIMIT-CONFORMING-{state_fips}-{county_fips}  (target=conventional, classified=jumbo)
              FHFA-LIMIT-JUMBO-{state_fips}-{county_fips}        (target=jumbo, classified=conforming/high_balance)
              HUD-LIMIT-FHA-{state_fips}-{county_fips}           (target=fha, classified=fha_high_balance excluded by HUD ceiling)
              VA-LIMIT-{state_fips}-{county_fips}                (target=va, classified outside)
              USDA-LIMIT-{state_fips}-{county_fips}              (target=usda, classified outside)

        MissingCountyDataError propagates to caller — D-11 step 1 says it's a
        HARD ERROR (Pydantic-shaped envelope on stderr per Phase 3 D-19), NOT a
        blocked_by string.
        """
        program = TARGET_LOAN_TYPE_TO_PROGRAM[target_loan_type]
        classified: LoanType = loan_type_classify(
            loan_amount=loan_amount,
            county=county,
            program=program,
        )
        accepted = TARGET_LOAN_TYPE_CROSSWALK[target_loan_type]
        if classified in accepted:
            return classified, None
        # Determine the citation prefix per target/classified mismatch
        citation_prefix = _LOAN_TYPE_BLOCKER_PREFIX[target_loan_type]
        return classified, f"{citation_prefix}-{county.state_fips}-{county.county_fips}"


    # Citation prefix per target_loan_type (used when classified type is OUTSIDE
    # the target's accepted set — D-11 step 1 LTV-classification block).
    _LOAN_TYPE_BLOCKER_PREFIX: dict[str, str] = {
        "conventional": "FHFA-LIMIT-CONFORMING",
        "jumbo": "FHFA-LIMIT-JUMBO",
        "fha": "HUD-LIMIT-FHA",
        "va": "VA-LIMIT",
        "usda": "USDA-LIMIT",
    }


    def _compute_monthly_mi(
        target_loan_type: TargetLoanType,
        financed_loan_amount: Decimal,
        property_value: Decimal,
        annual_rate: Decimal,
        term_months: int,
        monthly_pmi: Decimal | None,
        endorsement_date: date,
    ) -> tuple[Decimal, Decimal]:
        """Compute (monthly_mi, ufmip_or_zero) for the given target_loan_type.

        Returns:
          - monthly_mi: monthly mortgage-insurance / MIP / USDA annual fee component of PITI
          - ufmip_or_zero: UFMIP dollar amount (FHA only; D-03 auto-finance) or 0 for others

        Branches:
          conventional + LTV>0.80 → caller-supplied request.monthly_pmi (RESEARCH Open Q#1)
          conventional + LTV<=0.80 → Decimal("0.00")
          fha → fha_mip_compute(loan, property_value, endorsement_date); convert annual to monthly
          va → Decimal("0.00") (funding fee financed into principal at script boundary; not in PITI)
          usda → quantize_cents((loan_amount * USDA_ANNUAL_FEE_RATE) / 12)
          jumbo → Decimal("0.00") (caller responsible for jumbo-side MI if any)

        Per RESEARCH §A.2/A.3 + Open Q#1.
        """
        if target_loan_type == "conventional":
            origination_ltv = financed_loan_amount / property_value
            if origination_ltv > LTV_REQUEST_ELIGIBLE:
                # Plan 04-01 _validate_common already enforced monthly_pmi is not None here.
                assert monthly_pmi is not None  # noqa: S101 — validator pre-condition
                return monthly_pmi, Decimal("0")
            return Decimal("0.00"), Decimal("0")

        if target_loan_type == "fha":
            # RESEARCH §A.3: fha_mip.compute(loan, property_value, endorsement_date)
            # NOT the CONTEXT.md D-02 (loan_amount, ltv_pct, term_months) signature.
            loan = _build_loan_for_amortization(
                principal=financed_loan_amount,
                annual_rate=annual_rate,
                term_months=term_months,
                origination_date=endorsement_date,
            )
            mip = fha_mip_compute(
                loan=loan,
                original_property_value=property_value,
                endorsement_date=endorsement_date,
            )
            monthly_mip = quantize_cents(
                (financed_loan_amount * mip.annual_mip_pct) / Decimal("12")
            )
            return monthly_mip, mip.ufmip

        if target_loan_type == "va":
            return Decimal("0.00"), Decimal("0")

        if target_loan_type == "usda":
            # RESEARCH §"lib/rules/usda.py": guarantee_fee_annual = loan * 0.0035
            return (
                quantize_cents((financed_loan_amount * USDA_ANNUAL_FEE_RATE) / Decimal("12")),
                Decimal("0"),
            )

        if target_loan_type == "jumbo":
            return Decimal("0.00"), Decimal("0")

        # Defensive — Pydantic should already have rejected at request boundary
        raise ValueError(f"Unknown target_loan_type: {target_loan_type}")
    ```

    Add `from collections.abc import Sequence` to TYPE_CHECKING block; promote `from datetime import date` to runtime (already added above).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "
from decimal import Decimal
from datetime import date
from lib.affordability import (
    _compute_dti, _compute_ltv, _compute_cltv,
    _compute_monthly_mi, _build_loan_for_amortization,
    _classify_target_loan_type, USDA_ANNUAL_FEE_RATE,
)
from lib.rules.types import County

# Test 1: DTI
front, back = _compute_dti(Decimal('3000.00'), Decimal('500.00'), Decimal('10000.00'))
assert front == Decimal('0.30'), f'expected 0.30, got {front}'
assert back == Decimal('0.35'), f'expected 0.35, got {back}'

# Test 2: LTV
ltv = _compute_ltv(Decimal('400000.00'), Decimal('500000.00'))
assert ltv == Decimal('0.80'), f'expected 0.80, got {ltv}'

# Test 3: CLTV with juniors
cltv = _compute_cltv(Decimal('400000.00'), [Decimal('50000.00'), Decimal('25000.00')], Decimal('500000.00'))
assert cltv == Decimal('0.95'), f'expected 0.95, got {cltv}'

# Test 4: CLTV empty
cltv_empty = _compute_cltv(Decimal('400000.00'), [], Decimal('500000.00'))
assert cltv_empty == Decimal('0.80'), f'expected 0.80, got {cltv_empty}'

# Test 8: conventional <= 80% LTV
mi, ufmip = _compute_monthly_mi('conventional', Decimal('400000'), Decimal('500000'), Decimal('0.07'), 360, None, date(2026, 5, 1))
assert mi == Decimal('0.00')
assert ufmip == Decimal('0')

# Test 9: conventional > 80% LTV with caller-supplied
mi2, _ = _compute_monthly_mi('conventional', Decimal('425000'), Decimal('500000'), Decimal('0.07'), 360, Decimal('145.83'), date(2026, 5, 1))
assert mi2 == Decimal('145.83'), f'expected 145.83, got {mi2}'

# Test 11: VA — no MI
mi_va, _ = _compute_monthly_mi('va', Decimal('400000'), Decimal('500000'), Decimal('0.07'), 360, None, date(2026, 5, 1))
assert mi_va == Decimal('0.00')

# Test 12: USDA monthly fee
mi_usda, _ = _compute_monthly_mi('usda', Decimal('400000'), Decimal('500000'), Decimal('0.07'), 360, None, date(2026, 5, 1))
expected_usda = (Decimal('400000') * Decimal('0.0035')) / Decimal('12')
from lib.money import quantize_cents
assert mi_usda == quantize_cents(expected_usda), f'expected {quantize_cents(expected_usda)}, got {mi_usda}'

# Test 13: Loan construction
loan = _build_loan_for_amortization(Decimal('407000'), Decimal('0.0700'), 360, date(2026, 5, 1))
assert loan.principal == Decimal('407000.00')
assert loan.annual_rate == Decimal('0.0700')
assert loan.term_months == 360
assert loan.loan_type == 'fixed'

print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - lib/affordability.py contains literal substring `def _compute_dti(`
    - lib/affordability.py contains literal substring `def _compute_ltv(`
    - lib/affordability.py contains literal substring `def _compute_cltv(`
    - lib/affordability.py contains literal substring `def _classify_target_loan_type(`
    - lib/affordability.py contains literal substring `def _compute_monthly_mi(`
    - lib/affordability.py contains literal substring `def _build_loan_for_amortization(`
    - lib/affordability.py contains literal substring `def _build_county(`
    - lib/affordability.py contains literal substring `from lib.rules.loan_type import` (corrected import per RESEARCH §A.1)
    - lib/affordability.py contains literal substring `program=program` (or `program=TARGET_LOAN_TYPE_TO_PROGRAM`) — Phase 2 D-08 corrected signature
    - lib/affordability.py contains literal substring `from lib.rules.fha_mip import compute as fha_mip_compute` (full-path import per Phase 2 D-08)
    - lib/affordability.py contains literal substring `MissingCountyDataError` (RUL-01 hard-fail import — propagated, not caught)
    - lib/affordability.py contains literal substring `USDA_ANNUAL_FEE_RATE: Final[Decimal] = Decimal("0.0035")` (RESEARCH §USDA monthly fee derivation)
    - lib/affordability.py contains literal substring `_LOAN_TYPE_BLOCKER_PREFIX` (citation-prefix table)
    - lib/affordability.py contains literal substring `"FHFA-LIMIT-CONFORMING"` (cross-walk citation prefix per RESEARCH §A.1 + D-11)
    - lib/affordability.py contains literal substring `"HUD-LIMIT-FHA"`, `"VA-LIMIT"`, `"USDA-LIMIT"`
    - lib/affordability.py does NOT contain literal substring `conventional_pmi.status(ltv_pct` (RESEARCH §A.2 drift correction — the predicate is NOT consumed for monthly rate)
    - lib/affordability.py does NOT contain literal substring `fha_mip.compute(loan_amount, ltv_pct, term_months)` (RESEARCH §A.3 drift correction)
    - `uv run mypy --strict lib/affordability.py` exits 0
    - `uv run ruff check lib/affordability.py` exits 0
    - All 13 behavioral tests in &lt;behavior&gt; pass via inline python verification above
  </acceptance_criteria>
  <done>
    Helper layer is shipped; all corrected Phase 2 predicate signatures are honored; cross-walk citation prefixes pin the format Plan 04-04 will assemble; mypy + ruff clean.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement evaluate_forward — replaces stub body; composes helpers + build_schedule + warning capture</name>
  <files>lib/affordability.py</files>
  <read_first>
    - lib/affordability.py (Task 1 state — preserve all helpers)
    - .planning/phases/04-affordability/04-PATTERNS.md §"Warning capture pattern (RESEARCH §_loader.py)"
    - lib/amortize.py (lines 255-292 — build_schedule signature + return shape)
    - .planning/phases/04-affordability/04-CONTEXT.md D-01 through D-07 + D-11 (precedence shape, even though Plan 04-04 wires the bypass)
  </read_first>
  <behavior>
    - Test 1: `evaluate_forward(req)` for `forward_conventional_80_ltv` (loan=$400k, property=$500k, income joint=$10k, 6.5%/30yr, no debts, max_dti=0.43) returns `monthly_pi=Decimal("2528.27")` (matches golden_pmt.json computed_400k_30yr oracle)
    - Test 2: response.dti_front + response.dti_back computed; both Decimal; back >= front
    - Test 3: response.ltv == Decimal("0.80") exact; response.cltv == Decimal("0.80") exact (no junior_liens)
    - Test 4: response.piti = quantize_cents(2528.27 + tax + ins + hoa + 0) — verify single-quantize discipline
    - Test 5: response.monthly_mi == Decimal("0.00") (LTV not > 0.80)
    - Test 6: response.financed_loan_amount == Decimal("400000.00") (no FHA UFMIP financing for conventional)
    - Test 7: response.loan_type == "conforming" (Phase 2 classified value)
    - Test 8: response.total_gross_monthly_income = sum across applicants (D-06)
    - Test 9: response.total_monthly_debts = sum of MonthlyDebts fields
    - Test 10: response.warnings is empty for a clean conventional 80% case (no FHA/VA YAML touched → no StaleReferenceWarning)
    - Test 11: For FHA case (target_loan_type='fha'), response.financed_loan_amount = loan_amount + UFMIP; build_schedule is called with the FINANCED principal (D-03 auto-finance per RESEARCH recommendation)
    - Test 12: For FHA case, response.warnings contains a "stale" string entry (because fha-mip-rates.yml effective 2023-03-20 is > 12 months old; expected per RESEARCH §_loader.py)
    - Test 13: For target_loan_type='va' with VA inputs, monthly_mi == 0; financed_loan_amount == loan_amount (no UFMIP for VA — VA funding fee handled at script boundary per RESEARCH recommendation, mirrors D-03 but Plan 04-02 does NOT auto-finance VA funding fee here; a future amendment can add it)
    - Test 14: blocked=False, blocked_by=None for the clean conventional case (Plan 04-04 wires the precedence pipeline that mutates these — Plan 04-02 leaves them at default-False)
    - Test 15: Wave 0 stub `test_AFFD_01_dti_calculations` can be turned from xfail to a real assertion against `evaluate_forward(...)` results — but Plan 04-02 leaves it xfail; Plan 04-06 (tests + fixtures) flips it
  </behavior>
  <action>
    Replace the `evaluate_forward` stub body (the `raise NotImplementedError("forward evaluation shipped in Plan 04-02")` line) with the full implementation. Keep the function signature exactly as Plan 04-01 defined it.

    **Implementation skeleton:**

    ```python
    def evaluate_forward(request: ForwardModeRequest) -> AffordabilityResponse:
        """Forward-mode affordability composition.

        Pipeline:
          1. Sum joint income; compute total monthly debts.
          2. Build County from household.location FIPS.
          3. Classify loan_type via Phase 2 RUL-01 with corrected signature.
             (MissingCountyDataError propagates as Python exception; D-11 step 1
             hard error, NOT blocked_by — script boundary surfaces 6-key envelope.)
          4. Capture StaleReferenceWarning across predicate calls (D-11 propagation).
          5. For FHA target with D-03 auto-finance: financed_loan_amount = loan_amount + ufmip
             For other targets: financed_loan_amount = loan_amount.
          6. Call build_schedule on the financed Loan to get monthly_pi.
          7. Compute monthly_mi via _compute_monthly_mi (handles all 5 target loan types).
          8. PITI = quantize_cents(monthly_pi + tax + ins + hoa + monthly_mi). ONE quantize.
          9. LTV = financed_loan_amount / property_value (ratio).
         10. CLTV = (financed_loan_amount + sum(junior_liens)) / property_value.
         11. DTI front = piti / income; DTI back = (piti + non_housing_debts) / income.
         12. Default response.blocked=False, blocked_by=None — Plan 04-04 wires
             the precedence pipeline that mutates these.

        Note on warnings capture: every predicate call site is wrapped in a
        single warnings.catch_warnings(record=True) block; the captured
        StaleReferenceWarning instances are stringified via str(w.message) and
        appended to response.warnings.
        """
        # 1. Joint applicant aggregation (D-06 + D-05 + D-07)
        applicants = request.household.applicants
        total_gross_monthly_income = sum(
            (a.gross_monthly_income for a in applicants),
            start=Decimal("0"),
        )
        debts = request.household.monthly_debts
        sum_monthly_debts = (
            debts.auto + debts.student_loans + debts.credit_cards + debts.other
        )
        # min_credit_score is the documented selector for Fannie LLPA + Freddie
        # eligibility lookups in Plan 04-04 — not consumed in evaluate_forward
        # math, but documented here per D-05.
        _min_credit_score = min(a.credit_score for a in applicants)  # noqa: F841

        # 2. County construction
        county = _build_county(request.household.location)

        # Endorsement date (RESEARCH Open Q#6: default to today; allow override)
        endorsement_date = request.endorsement_date_override or date.today()

        # 3-12: capture staleness warnings across the pipeline (D-11)
        captured_warnings: list[str] = []
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", StaleReferenceWarning)

            # 3. Loan-type classification (corrected signature per RESEARCH §A.1)
            classified_loan_type, classify_blocker = _classify_target_loan_type(
                loan_amount=request.loan_amount,
                county=county,
                target_loan_type=request.target_loan_type,
            )

            # 5. UFMIP financing (D-03 auto-finance per RESEARCH recommendation)
            #    Compute MI and UFMIP together; financed_loan_amount derives from UFMIP.
            #    Note: _compute_monthly_mi takes financed_loan_amount; for FHA we need
            #    a two-step compute (UFMIP first → financed_amount → monthly MIP from
            #    financed_amount). Inline the FHA branch here for clarity.
            ufmip_to_finance = Decimal("0.00")
            if request.target_loan_type == "fha":
                # First MIP call to get UFMIP
                pre_finance_loan = _build_loan_for_amortization(
                    principal=request.loan_amount,
                    annual_rate=request.annual_rate,
                    term_months=request.term_months,
                    origination_date=endorsement_date,
                )
                pre_mip = fha_mip_compute(
                    loan=pre_finance_loan,
                    original_property_value=request.property_value,
                    endorsement_date=endorsement_date,
                )
                ufmip_to_finance = pre_mip.ufmip

            financed_loan_amount = quantize_cents(request.loan_amount + ufmip_to_finance)

            # 6. Compute monthly P&I via Phase 3 build_schedule on the financed loan
            financed_loan = _build_loan_for_amortization(
                principal=financed_loan_amount,
                annual_rate=request.annual_rate,
                term_months=request.term_months,
                origination_date=endorsement_date,
            )
            schedule = build_schedule(financed_loan)
            monthly_pi = schedule.monthly_pi

            # 7. Compute monthly_mi (predicate-derived for FHA; caller-supplied for
            #    conventional > 80%; predicate-derived for USDA; 0 for VA / jumbo /
            #    conventional <= 80%)
            monthly_mi, _ = _compute_monthly_mi(
                target_loan_type=request.target_loan_type,
                financed_loan_amount=financed_loan_amount,
                property_value=request.property_value,
                annual_rate=request.annual_rate,
                term_months=request.term_months,
                monthly_pmi=request.monthly_pmi,
                endorsement_date=endorsement_date,
            )

            # Collect StaleReferenceWarning strings (D-11 propagation)
            for w in captured:
                if issubclass(w.category, StaleReferenceWarning):
                    captured_warnings.append(str(w.message))

        # 8. PITI — quantize ONCE at end (Phase 3 D-04 PITFALLS pattern; D-01)
        escrow = request.household.escrow
        piti_pre_quantize = (
            monthly_pi
            + escrow.property_tax_monthly
            + escrow.insurance_monthly
            + escrow.hoa_monthly
            + monthly_mi
        )
        piti = quantize_cents(piti_pre_quantize)

        # 9-10. LTV + CLTV (use financed_loan_amount for FHA UFMIP semantics)
        ltv = _compute_ltv(financed_loan_amount, request.property_value)
        cltv = _compute_cltv(
            financed_loan_amount,
            request.junior_liens,
            request.property_value,
        )

        # 11. DTI front + back
        dti_front, dti_back = _compute_dti(
            piti=piti,
            sum_monthly_debts=sum_monthly_debts,
            total_gross_monthly_income=total_gross_monthly_income,
        )

        # 12. Build response — blocked / blocked_by stay at default-False; Plan 04-04
        # mutates these via the precedence pipeline AFTER this function returns.
        # For now, surface the loan-type-classify blocker (if any) into blocked_by
        # so Plan 04-04 can find it; this is a documented coupling point.
        return AffordabilityResponse(
            mode="forward",
            loan_type=classified_loan_type,
            blocked=(classify_blocker is not None),
            blocked_by=classify_blocker,
            warnings=captured_warnings,
            total_gross_monthly_income=quantize_cents(total_gross_monthly_income),
            total_monthly_debts=quantize_cents(sum_monthly_debts),
            loan_amount=request.loan_amount,
            property_value=request.property_value,
            financed_loan_amount=financed_loan_amount,
            dti_front=dti_front,
            dti_back=dti_back,
            ltv=ltv,
            cltv=cltv,
            piti=piti,
            monthly_pi=monthly_pi,
            monthly_mi=quantize_cents(monthly_mi),
        )
    ```

    **Coupling note for Plan 04-04:** evaluate_forward returns with `blocked` + `blocked_by` set ONLY for the loan-type-classify blocker (D-11 step 1). Plan 04-04 wraps `evaluate_forward` with `_evaluate_blockers` that:
    1. Calls evaluate_forward
    2. If response.blocked is already True (classify hit), short-circuits return
    3. Otherwise iterates the rest of D-11 precedence (LTV ceiling → DTI cap → ATR/QM → VA-residual) and mutates a NEW response (frozen models — uses model_copy with update={"blocked": ..., "blocked_by": ..., "warnings": [...]})

    This split keeps evaluate_forward focused on math and Plan 04-04 focused on regulatory blocker precedence.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "
from decimal import Decimal
from datetime import date
from lib.affordability import (
    evaluate_forward, ForwardModeRequest, Household, LocationFIPS,
    Applicant, MonthlyDebts, EscrowInputs,
)

req = ForwardModeRequest(
    mode='forward',
    household=Household(
        location=LocationFIPS(state='WA', state_fips='53', county_fips='033', county_name='King', zip='98101'),
        applicants=[Applicant(name='A', gross_monthly_income=Decimal('5000.00'), credit_score=720),
                    Applicant(name='B', gross_monthly_income=Decimal('5000.00'), credit_score=680)],
        monthly_debts=MonthlyDebts(auto=Decimal('0.00'), student_loans=Decimal('0.00'),
                                   credit_cards=Decimal('0.00'), other=Decimal('0.00')),
        escrow=EscrowInputs(property_tax_monthly=Decimal('0.00'),
                            insurance_monthly=Decimal('0.00'),
                            hoa_monthly=Decimal('0.00')),
    ),
    max_dti=Decimal('0.430000'),
    target_loan_type='conventional',
    term_months=360,
    annual_rate=Decimal('0.065000'),
    loan_amount=Decimal('400000.00'),
    property_value=Decimal('500000.00'),
)
resp = evaluate_forward(req)
# Test 1: monthly_pi matches Phase 1/3 oracle
assert resp.monthly_pi == Decimal('2528.27'), f'expected 2528.27, got {resp.monthly_pi}'
# Test 3: LTV
assert resp.ltv == Decimal('0.80'), f'expected 0.80, got {resp.ltv}'
# Test 5: no PMI
assert resp.monthly_mi == Decimal('0.00'), f'expected 0.00, got {resp.monthly_mi}'
# Test 6: financed amount = loan amount (no UFMIP for conventional)
assert resp.financed_loan_amount == Decimal('400000.00')
# Test 7: classified
assert resp.loan_type == 'conforming'
# Test 8: joint income
assert resp.total_gross_monthly_income == Decimal('10000.00')
# Test 14: not blocked (no classify blocker for King WA $400k conventional)
assert resp.blocked is False
assert resp.blocked_by is None
print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - lib/affordability.py contains literal substring `def evaluate_forward(request: ForwardModeRequest) -> AffordabilityResponse:`
    - lib/affordability.py does NOT contain literal substring `raise NotImplementedError("forward evaluation shipped in Plan 04-02")` (stub body replaced)
    - lib/affordability.py contains literal substring `build_schedule(financed_loan)` (Phase 3 call site)
    - lib/affordability.py contains literal substring `quantize_cents(piti_pre_quantize)` (single end-of-period quantize per Phase 3 D-04 PITFALLS)
    - lib/affordability.py contains literal substring `warnings.catch_warnings(record=True)` (D-11 stale-warning propagation)
    - lib/affordability.py contains literal substring `_min_credit_score = min(a.credit_score for a in applicants)` (D-05 documented selector)
    - lib/affordability.py contains literal substring `sum((a.gross_monthly_income for a in applicants)` (D-06 sum)
    - lib/affordability.py contains literal substring `total_gross_monthly_income / income` is NOT present — DTI uses Decimal division `/ total_gross_monthly_income` only
    - lib/affordability.py contains literal substring `request.loan_amount + ufmip_to_finance` (D-03 auto-finance per RESEARCH recommendation)
    - lib/affordability.py contains literal substring `endorsement_date_override or date.today()` (RESEARCH Open Q#6 default)
    - All 15 behavioral tests pass via inline python verification above + a follow-up FHA case verification (test 11/12) executable
    - `uv run pytest tests/test_amortize.py -x` still green (no Phase 3 regression)
    - `uv run pytest tests/test_affordability.py -x` still green (Plan 04-00 stubs still xfail; no production-side regression)
    - `uv run mypy --strict lib/affordability.py lib/amortize.py` exits 0
    - `uv run ruff check lib/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    evaluate_forward composes Phase 1/2/3 surfaces correctly; matches the $2528.27 conforming-loan oracle exactly; FHA path auto-finances UFMIP and emits the financed amount on the response; PITI single-quantize discipline preserved; mypy + ruff clean; no Phase 3 regressions.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| evaluate_forward → Phase 2 predicates | Predicate signature drift (RESEARCH §A.1-A.3) is the highest-risk surface; mitigation = corrected signatures pinned by acceptance grep |
| evaluate_forward → quantize_cents | PITI single-quantize discipline is load-bearing; mid-calc quantize would compound rounding errors |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-02-01 | Tampering | Phase 2 predicate signature drift (CONTEXT.md D-02 vs RESEARCH §A.1-A.3) | mitigate | Acceptance grep gates pin the corrected call shapes (`program=program`, `fha_mip_compute(loan=..., original_property_value=..., endorsement_date=...)`); negative grep gate on `conventional_pmi.status(ltv_pct` |
| T-04-02-02 | Tampering | PITI mid-calculation quantize compounds rounding | mitigate | Acceptance grep on `quantize_cents(piti_pre_quantize)` AND structural read of action body confirms only ONE quantize call on the PITI sum |
| T-04-02-03 | Tampering | MissingCountyDataError silently caught & converted to blocked_by | mitigate | Negative-direction: action body explicitly states "MissingCountyDataError propagates as Python exception"; no try/except around `loan_type_classify(...)`; surfaces as 6-key envelope at script boundary in Plan 04-05 |
| T-04-02-04 | Repudiation | StaleReferenceWarning silently suppressed | mitigate | `warnings.catch_warnings(record=True)` + `warnings.simplefilter("always", StaleReferenceWarning)` ensures warnings ARE captured; appended to response.warnings unsuppressed |
| T-04-02-05 | Tampering | Float coercion via Decimal(0.07) (constructor with float arg) | accept | Pydantic v2 strict=True at request boundary rejects float; lib/affordability internal math uses only `request.annual_rate` and Decimal-from-Decimal arithmetic; no float surface |
| T-04-02-06 | Information Disclosure | Module docstring mentions Pachulski household location (King WA) | accept | Public location data; no PII; King WA is the example county across the project |
| T-04-02-07 | Tampering | UFMIP not financed when caller expected pre-financing | mitigate | D-03 + RESEARCH recommendation locked to option (b) auto-finance; documented in module docstring (Plan 04-01) and CLI --help (Plan 04-05); mismatched expectation is loud (response.financed_loan_amount field surfaces the addition) |
</threat_model>

<verification>
After both tasks complete:

```bash
# Conformance to Phase 1+3 oracle
uv run python -c "
from decimal import Decimal
from lib.affordability import evaluate_forward, ForwardModeRequest, Household, LocationFIPS, Applicant, MonthlyDebts, EscrowInputs
# build minimal req — see Task 2 verify
req = ForwardModeRequest(mode='forward', household=Household(...), max_dti=Decimal('0.43'), target_loan_type='conventional', term_months=360, annual_rate=Decimal('0.065'), loan_amount=Decimal('400000.00'), property_value=Decimal('500000.00'))
assert evaluate_forward(req).monthly_pi == Decimal('2528.27')
"

# All Wave 0 stubs still xfail (Plan 04-06 flips them)
uv run pytest tests/test_affordability.py -x

# Phase 1+2+3 regressions check
uv run pytest -x

# mypy + ruff clean across changed files
uv run mypy --strict lib/affordability.py
uv run ruff check lib/affordability.py
```
</verification>

<success_criteria>
- [ ] `evaluate_forward(request: ForwardModeRequest) -> AffordabilityResponse` is implemented (no NotImplementedError)
- [ ] `monthly_pi == Decimal("2528.27")` for $400k @ 6.5% / 30yr (matches Phase 1 oracle + Phase 3 build_schedule)
- [ ] PITI is single-quantized at end (one `quantize_cents(...)` call on the sum)
- [ ] LTV + CLTV use `financed_loan_amount` (not raw `request.loan_amount`) for the FHA UFMIP-auto-financed semantics
- [ ] DTI front + back use Decimal precision (no quantize)
- [ ] StaleReferenceWarning captured and surfaced in `response.warnings`
- [ ] All Phase 2 predicate calls use corrected signatures (RESEARCH §A.1-A.3)
- [ ] Joint-applicant aggregation: sum income + min credit_score (D-05, D-06, D-07)
- [ ] FHA UFMIP auto-finance (D-03 option (b)): `financed_loan_amount = loan_amount + UFMIP`
- [ ] No Phase 1/2/3 regressions; all existing tests still green
- [ ] mypy --strict + ruff clean
</success_criteria>

<output>
After completion, create `.planning/phases/04-affordability/04-02-SUMMARY.md` per the standard template.
</output>
