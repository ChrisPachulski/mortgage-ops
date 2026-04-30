---
phase: 04-affordability
plan: 03
type: execute
wave: 3
depends_on: ["04-00", "04-01", "04-02"]
files_modified:
  - lib/affordability.py
autonomous: true
requirements: [AFFD-05]
requirements_addressed: [AFFD-05]
tags: [phase-4, affordability, reverse, npf-pv, wave-3]

must_haves:
  truths:
    - "evaluate_reverse(req) returns AffordabilityResponse with mode='reverse' (D-14)"
    - "Reverse solver is one-shot npf.pv — no iteration (D-08)"
    - "monthly_rate = annual_rate / Decimal('12') — Phase 3 D-04 convention"
    - "npf.pv is called with rate=monthly_rate, nper=term_months, pmt=-max_pi (negative cash-out), fv=0 (Phase 3 D-09 / numpy-financial issue #130 avoidance)"
    - "max_loan_amount = quantize_cents(-raw_pv) — NEGATE raw return per cash-flow convention; quantize ONCE at end (CLAUDE.md money discipline)"
    - "max_PITI = max_dti * total_gross_monthly_income - sum(monthly_debts) (D-08 step 1)"
    - "max_PI_plus_MI = max_PITI - (escrow.property_tax_monthly + escrow.insurance_monthly + escrow.hoa_monthly) (D-08 step 2)"
    - "assumed_monthly_mi for caller-pinned target_ltv_pct: caller-supplied request.monthly_pmi (conv > 0.80) OR predicate-derived (FHA from estimated property_value AT target LTV) OR Decimal(0) (VA/USDA/conv <= 0.80)"
    - "max_PI = max_PI_plus_MI - assumed_monthly_mi (D-08 step 4)"
    - "Round-trip closure (D-09): for SC-2 fixture (max_dti=0.43, target_ltv=0.80, conventional, 7%/30yr), forward(reverse(req)) yields dti_back <= max_dti + Decimal('0.0001') AND forward.loan_amount == reverse.max_loan_amount exactly"
    - "Reverse mode does NOT call build_schedule (uses npf.pv directly per RESEARCH pseudocode)"
    - "implied_pi = max_PI (the input to npf.pv); surfaced on response for traceability"
  artifacts:
    - path: lib/affordability.py
      provides: "evaluate_reverse implementation; replaces Plan 04-01 stub body"
      contains: "def evaluate_reverse"
      min_lines: 850
  key_links:
    - from: lib/affordability.py
      to: numpy_financial
      via: "npf.pv(rate=monthly_rate, nper=term_months, pmt=-max_pi, fv=0)"
      pattern: "npf\\.pv\\("
    - from: lib/affordability.py
      to: lib/money.py
      via: "quantize_cents on max_loan_amount + intermediate Decimal"
      pattern: "quantize_cents"
---

<objective>
Implement `evaluate_reverse(req: ReverseModeRequest) -> AffordabilityResponse` (AFFD-05). Wraps `numpy_financial.pv` directly per RESEARCH §"numpy-financial npf.pv Conventions". One-shot solve — no iteration (D-08).

Replaces the Plan 04-01 stub `raise NotImplementedError("reverse evaluation shipped in Plan 04-03")` with a full implementation. Reuses `_compute_dti`, `_compute_ltv`, `_compute_cltv`, `_classify_target_loan_type`, `_compute_monthly_mi` helpers from Plan 04-02.

Purpose: ship the npf.pv reverse solver and ensure it round-trips through evaluate_forward within the D-09 tolerance. The round-trip closure is the test in Plan 04-06; this plan ships the math that the round-trip test will exercise.

Output: `lib/affordability.py` extended with `evaluate_reverse` body that calls Phase 2 corrected predicates (RESEARCH §A.1-A.3) for loan_type classification + MI estimation, then computes max_PI_plus_MI → max_PI → max_loan_amount via npf.pv.

Decisions implemented: D-08 (one-shot npf.pv), D-09 (round-trip closure target Decimal('0.0001')), D-10 (request shape locked at Plan 04-01), D-14 (mode discriminator).
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
@.planning/phases/04-affordability/04-01-pydantic-models-PLAN.md
@.planning/phases/04-affordability/04-02-forward-affordability-PLAN.md
@CLAUDE.md
@lib/affordability.py
@lib/amortize.py
@lib/money.py

<interfaces>
<!-- numpy_financial.pv (RESEARCH §"numpy-financial npf.pv Conventions" — verified 2026-04-30) -->

```python
import numpy_financial as npf
# npf.pv(rate, nper, pmt, fv=0, when='end')
#   - rate: per-period rate (monthly = annual/12)
#   - nper: total payments (term_months for monthly cadence)
#   - pmt: NEGATIVE cash outflow (the borrower's monthly P&I)
#   - fv: ALWAYS 0 (Phase 3 D-09 avoidance; numpy-financial issue #130)
#   - when: 'end' (default; standard mortgage convention)
# Returns: NEGATIVE Decimal under cash-flow convention (money received not available today)
#          NEGATE again to express principal as positive: max_loan_amount = -raw_pv
```

<!-- Plan 04-02 helpers (already in lib/affordability.py) -->
```python
def _compute_dti(piti, sum_monthly_debts, total_gross_monthly_income) -> tuple[Decimal, Decimal]
def _compute_ltv(loan_amount, property_value) -> Decimal
def _compute_cltv(loan_amount, junior_liens, property_value) -> Decimal
def _classify_target_loan_type(loan_amount, county, target_loan_type) -> tuple[LoanType, str | None]
def _compute_monthly_mi(target_loan_type, financed_loan_amount, property_value, annual_rate, term_months, monthly_pmi, endorsement_date) -> tuple[Decimal, Decimal]
def _build_county(location: LocationFIPS) -> County
```

<!-- D-09 closure target -->
```
forward(reverse(req)).dti_back <= req.max_dti + Decimal("0.0001")
forward(reverse(req)).loan_amount == reverse(req).max_loan_amount  # exact Decimal equality on dollars
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement evaluate_reverse — npf.pv solve + property_value derivation + MI estimation at target LTV</name>
  <files>lib/affordability.py</files>
  <read_first>
    - lib/affordability.py (Plan 04-02 state — preserve all existing code; helpers in place)
    - .planning/phases/04-affordability/04-RESEARCH.md §"numpy-financial npf.pv Conventions" (full section incl. pseudocode)
    - .planning/phases/04-affordability/04-CONTEXT.md D-08, D-09, D-10
    - .planning/phases/04-affordability/04-PATTERNS.md §"numpy-financial use pattern" (Phase 4 reverse adaptation)
  </read_first>
  <behavior>
    - Test 1: For SC-2 anchor (max_dti=Decimal('0.43'), income=Decimal('10000.00'), no debts, escrow all 0, conv, target_ltv=0.80, 7%/30yr, down_payment=Decimal('100000.00')): max_PITI = 4300, max_PI = 4300 (no MI), max_loan_amount ≈ Decimal('646154.00') (engine-emitted; pin verbatim in fixture)
    - Test 2: response.assumed_ltv_pct == request.target_ltv_pct (Decimal exact)
    - Test 3: response.implied_pi is the max_PI (positive Decimal; quantize_cents applied)
    - Test 4: response.max_loan_amount = quantize_cents(-npf.pv(...)) — single quantize end-of-period
    - Test 5: response.assumed_monthly_mi == Decimal("0.00") for conventional+target_ltv=0.80 (LTV not > 0.80; no PMI)
    - Test 6: For conv+target_ltv=0.85 with caller monthly_pmi=Decimal("145.83"), assumed_monthly_mi == Decimal("145.83") and is subtracted before npf.pv
    - Test 7: response.loan_amount derived: implied property_value = max_loan_amount / target_ltv_pct, BUT response.property_value stays None (reverse mode); we surface assumed_ltv_pct and the derived max_loan_amount instead
    - Test 8: response.mode == "reverse"; response.dti_front + response.dti_back are None (reverse mode does NOT compute forward DTI; round-trip test in Plan 04-06 does this via evaluate_forward)
    - Test 9: Round-trip closure SETUP — forward(req=ForwardModeRequest(loan_amount=resp.max_loan_amount, property_value=resp.max_loan_amount/resp.assumed_ltv_pct, ...)) returns dti_back <= original max_dti + Decimal("0.0001") (D-09); the actual round-trip assertion lands in Plan 04-06's test
    - Test 10: For target_loan_type='fha' reverse: assumed_monthly_mi computed via fha_mip predicate at the ESTIMATED property_value (max_loan_amount / target_ltv_pct); UFMIP NOT financed in reverse mode (the caller-supplied down_payment + target_ltv_pct already pin both sides; financing UFMIP would shift LTV out of the target bucket, breaking D-08's one-shot premise)
    - Test 11: For target_loan_type='va' reverse: assumed_monthly_mi == 0; max_loan_amount unaffected by VA funding fee (financing handled at script boundary; mirrors forward-mode treatment)
    - Test 12: response.warnings populated with StaleReferenceWarning strings if FHA / VA YAMLs are touched (D-11 propagation; same as forward mode)
    - Test 13: Reverse-mode loan-type classification uses the ESTIMATED loan amount BEFORE solving — chicken-and-egg resolved by computing pre-LTV-bucket max_pi-from-income, deriving an initial estimate via npf.pv at zero-MI assumption, then classifying. If classified type is OUTSIDE the target's accepted set, response.blocked=True with the FHFA/HUD/VA/USDA-LIMIT-* citation (mirrors evaluate_forward step 3 output coupling)
  </behavior>
  <action>
    Replace the `evaluate_reverse` stub body (the `raise NotImplementedError("reverse evaluation shipped in Plan 04-03")` line) with the full implementation. Keep the function signature exactly as Plan 04-01 defined it.

    **Implementation skeleton:**

    ```python
    def evaluate_reverse(request: ReverseModeRequest) -> AffordabilityResponse:
        """Reverse-mode affordability: max_loan_amount via npf.pv (D-08).

        Pipeline:
          1. Sum joint income; compute total monthly debts.
          2. max_PITI = max_dti * income - debts.
          3. max_PI_plus_MI = max_PITI - (tax + ins + hoa).
          4. Estimate assumed_monthly_mi via _compute_monthly_mi at the caller-pinned
             target_ltv_pct. For FHA we use a candidate financed_loan_amount derived
             from a zero-MI npf.pv solve, then refine.
          5. max_PI = max_PI_plus_MI - assumed_monthly_mi.
          6. monthly_rate = annual_rate / Decimal("12") (Phase 3 D-04 convention).
          7. raw_pv = npf.pv(rate=monthly_rate, nper=term_months, pmt=-max_PI, fv=0)
             (negative pmt per cash-out convention; fv=0 per Phase 3 D-09 + npf #130).
          8. max_loan_amount = quantize_cents(-raw_pv) — single quantize, end-of-period.
          9. derived_property_value = max_loan_amount / target_ltv_pct (for downstream
             classify call only; NOT surfaced on response — reverse-mode doesn't
             commit to a property_value, just an LTV).
         10. Construct County; classify_target_loan_type with derived_property_value
             check; surface blocker if classified type is outside target's accepted
             set.
         11. Build response with mode="reverse", max_loan_amount, implied_pi=max_PI,
             assumed_ltv_pct=target_ltv_pct, assumed_monthly_mi.

        Round-trip closure target (D-09):
          forward(ForwardModeRequest(loan_amount=resp.max_loan_amount,
                                     property_value=resp.max_loan_amount/target_ltv_pct,
                                     ...)).dti_back <= req.max_dti + Decimal("0.0001")
        """
        # 1. Joint applicant aggregation (D-06 + D-05 + D-07; mirrors evaluate_forward)
        applicants = request.household.applicants
        total_gross_monthly_income = sum(
            (a.gross_monthly_income for a in applicants),
            start=Decimal("0"),
        )
        debts = request.household.monthly_debts
        sum_monthly_debts = (
            debts.auto + debts.student_loans + debts.credit_cards + debts.other
        )

        escrow = request.household.escrow
        endorsement_date = request.endorsement_date_override or date.today()

        # 2. max_PITI (D-08 step 1)
        max_piti = request.max_dti * total_gross_monthly_income - sum_monthly_debts

        # 3. max_PI_plus_MI (D-08 step 2)
        max_pi_plus_mi = max_piti - (
            escrow.property_tax_monthly
            + escrow.insurance_monthly
            + escrow.hoa_monthly
        )

        # 4. Estimate assumed_monthly_mi at caller-pinned target_ltv_pct (D-08 step 3)
        captured_warnings: list[str] = []
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", StaleReferenceWarning)

            # For FHA we need a candidate financed_loan_amount → derived property_value
            # to call fha_mip_compute. Zero-MI seed: solve npf.pv with monthly_mi=0.
            monthly_rate = request.annual_rate / Decimal("12")
            zero_mi_pv = npf.pv(
                rate=monthly_rate,
                nper=request.term_months,
                pmt=-max_pi_plus_mi,
                fv=0,
            )
            zero_mi_loan_amount = quantize_cents(-zero_mi_pv)
            zero_mi_property_value = quantize_cents(
                zero_mi_loan_amount / request.target_ltv_pct
            )

            # Now compute MI for the candidate (FHA branch produces the only
            # non-trivial estimate that depends on financed_loan_amount).
            assumed_monthly_mi, _ = _compute_monthly_mi(
                target_loan_type=request.target_loan_type,
                financed_loan_amount=zero_mi_loan_amount,
                property_value=zero_mi_property_value,
                annual_rate=request.annual_rate,
                term_months=request.term_months,
                monthly_pmi=request.monthly_pmi,
                endorsement_date=endorsement_date,
            )

            # 5. max_PI (D-08 step 4)
            max_pi = max_pi_plus_mi - assumed_monthly_mi

            # 6-8. npf.pv solve (D-08 step 5; RESEARCH §"numpy-financial npf.pv")
            raw_pv = npf.pv(
                rate=monthly_rate,
                nper=request.term_months,
                pmt=-max_pi,
                fv=0,
            )
            max_loan_amount = quantize_cents(-raw_pv)

            # 9. Derive property_value for downstream classify (NOT surfaced on
            #    response — reverse-mode commits to LTV, not a specific property).
            derived_property_value = quantize_cents(
                max_loan_amount / request.target_ltv_pct
            )

            # 10. Loan-type classification (D-11 step 1)
            county = _build_county(request.household.location)
            classified_loan_type, classify_blocker = _classify_target_loan_type(
                loan_amount=max_loan_amount,
                county=county,
                target_loan_type=request.target_loan_type,
            )

            for w in captured:
                if issubclass(w.category, StaleReferenceWarning):
                    captured_warnings.append(str(w.message))

        # 11. Build response
        return AffordabilityResponse(
            mode="reverse",
            loan_type=classified_loan_type,
            blocked=(classify_blocker is not None),
            blocked_by=classify_blocker,
            warnings=captured_warnings,
            total_gross_monthly_income=quantize_cents(total_gross_monthly_income),
            total_monthly_debts=quantize_cents(sum_monthly_debts),
            max_loan_amount=max_loan_amount,
            implied_pi=quantize_cents(max_pi),
            assumed_ltv_pct=request.target_ltv_pct,
            assumed_monthly_mi=quantize_cents(assumed_monthly_mi),
        )
    ```

    **Note on monthly_pi vs implied_pi naming:** `implied_pi` is the reverse-mode counterpart to forward's `monthly_pi` — the monthly principal-and-interest IMPLIED by the npf.pv solve. Naming distinct fields keeps the response shape unambiguous about which mode produced the value (forward = computed via build_schedule; reverse = computed via npf.pv inversion).

    **Note on D-09 round-trip:** This plan does NOT execute the round-trip assertion. Plan 04-06 ships the test fixture `reverse_conventional_80_ltv_43_dti.json` and the test that:
    1. Calls `evaluate_reverse(req)` to get `resp.max_loan_amount`
    2. Calls `evaluate_forward(ForwardModeRequest(loan_amount=resp.max_loan_amount, property_value=resp.max_loan_amount/resp.assumed_ltv_pct, ...))`
    3. Asserts `forward_response.dti_back <= req.max_dti + Decimal("0.0001")` AND `forward_response.loan_amount == resp.max_loan_amount` exactly

    Plan 04-03's task is to make that closure achievable; Plan 04-06's task is to assert it.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "
from decimal import Decimal
from datetime import date
from lib.affordability import (
    evaluate_reverse, evaluate_forward, ReverseModeRequest, ForwardModeRequest,
    Household, LocationFIPS, Applicant, MonthlyDebts, EscrowInputs,
)

household = Household(
    location=LocationFIPS(state='WA', state_fips='53', county_fips='033', county_name='King', zip='98101'),
    applicants=[Applicant(name='A', gross_monthly_income=Decimal('5000.00'), credit_score=720),
                Applicant(name='B', gross_monthly_income=Decimal('5000.00'), credit_score=680)],
    monthly_debts=MonthlyDebts(),
    escrow=EscrowInputs(property_tax_monthly=Decimal('0.00'),
                        insurance_monthly=Decimal('0.00'),
                        hoa_monthly=Decimal('0.00')),
)

# SC-2 anchor: max_dti=0.43, income=10000, debts=0, conv, target_ltv=0.80, 7%/30yr
req = ReverseModeRequest(
    mode='reverse',
    household=household,
    max_dti=Decimal('0.430000'),
    target_loan_type='conventional',
    term_months=360,
    annual_rate=Decimal('0.070000'),
    down_payment=Decimal('100000.00'),
    target_ltv_pct=Decimal('0.800000'),
)
resp = evaluate_reverse(req)

# Test 2: assumed_ltv_pct
assert resp.assumed_ltv_pct == Decimal('0.800000')
# Test 5: no MI for conventional 80%
assert resp.assumed_monthly_mi == Decimal('0.00')
# Test 8: mode + null forward fields
assert resp.mode == 'reverse'
assert resp.dti_front is None
assert resp.dti_back is None
# Round-trip setup (D-09): feed resp.max_loan_amount back through forward; should not blow up
fwd_req = ForwardModeRequest(
    mode='forward',
    household=household,
    max_dti=req.max_dti,
    target_loan_type=req.target_loan_type,
    term_months=req.term_months,
    annual_rate=req.annual_rate,
    loan_amount=resp.max_loan_amount,
    property_value=resp.max_loan_amount / req.target_ltv_pct,
)
fwd_resp = evaluate_forward(fwd_req)
# D-09 closure: dti_back <= max_dti + 0.0001
diff = fwd_resp.dti_back - req.max_dti
assert diff <= Decimal('0.0001'), f'D-09 closure failed: diff={diff}'
# Forward.loan_amount == reverse.max_loan_amount exactly
assert fwd_resp.loan_amount == resp.max_loan_amount

# implied_pi positive
assert resp.implied_pi > Decimal('0.00')
# Reverse always emits None for forward-only fields
assert resp.dti_front is None
assert resp.ltv is None

print(f'OK; max_loan_amount={resp.max_loan_amount}; implied_pi={resp.implied_pi}; round-trip diff={diff}')
"</automated>
  </verify>
  <acceptance_criteria>
    - lib/affordability.py contains literal substring `def evaluate_reverse(request: ReverseModeRequest) -> AffordabilityResponse:`
    - lib/affordability.py does NOT contain literal substring `raise NotImplementedError("reverse evaluation shipped in Plan 04-03")` (stub body replaced)
    - lib/affordability.py contains literal substring `npf.pv(` (numpy-financial direct call)
    - lib/affordability.py contains literal substring `pmt=-max_pi` (negative cash-out convention per RESEARCH §"numpy-financial npf.pv Conventions")
    - lib/affordability.py contains literal substring `fv=0` (Phase 3 D-09 + numpy-financial #130 avoidance)
    - lib/affordability.py contains literal substring `monthly_rate = request.annual_rate / Decimal("12")` (Phase 3 D-04 convention)
    - lib/affordability.py contains literal substring `quantize_cents(-raw_pv)` (negate raw + single quantize per RESEARCH §"reverse pseudocode")
    - lib/affordability.py contains literal substring `request.max_dti * total_gross_monthly_income` (D-08 step 1 max_PITI formula)
    - lib/affordability.py contains literal substring `escrow.property_tax_monthly` (D-01 escrow consumption)
    - lib/affordability.py contains literal substring `_compute_monthly_mi(` (Plan 04-02 helper reuse)
    - lib/affordability.py contains literal substring `assumed_ltv_pct=request.target_ltv_pct` (response shape per Plan 04-01)
    - lib/affordability.py contains literal substring `implied_pi=quantize_cents(max_pi)` (response surfacing for traceability)
    - The verify block above runs successfully (all 8 assertions pass)
    - Round-trip closure verified: `fwd_resp.dti_back - req.max_dti <= Decimal('0.0001')` AND `fwd_resp.loan_amount == resp.max_loan_amount` exactly
    - `uv run pytest -x` still green (no Phase 1/2/3 regressions; Wave 0 stubs still xfail)
    - `uv run mypy --strict lib/affordability.py` exits 0
    - `uv run ruff check lib/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    evaluate_reverse is implemented; npf.pv is called with corrected sign + fv=0 + monthly_rate conventions; round-trip closure (D-09) verified empirically against the SC-2 anchor; mypy + ruff clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| evaluate_reverse → numpy_financial.pv | Sign convention drift is the highest risk; mitigation = pinned grep on `pmt=-max_pi` AND `quantize_cents(-raw_pv)` |
| evaluate_reverse → fv parameter | numpy-financial issue #130 is silent foot-gun if fv != 0; mitigation = `fv=0` literal in code |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-03-01 | Tampering | npf.pv sign convention drift (forgetting to negate pmt OR raw_pv) | mitigate | Grep gates pin BOTH `pmt=-max_pi` AND `quantize_cents(-raw_pv)`; the round-trip closure assertion catches drift empirically (off-by-sign would yield a 2x-off max_loan_amount) |
| T-04-03-02 | Tampering | numpy-financial issue #130 (fv-sign with non-zero fv) | mitigate | Grep gate `fv=0` literal; Phase 3 D-09 already pins this convention |
| T-04-03-03 | Tampering | Decimal/float mixing in monthly_rate computation | mitigate | `request.annual_rate` is Pydantic `Rate` (Decimal); division by `Decimal("12")` keeps result Decimal; npf.pv 1.0.0 returns Decimal for Decimal inputs (verified Phase 3 lib/amortize.py:133 docstring) |
| T-04-03-04 | Tampering | Mid-calc quantize compounds rounding | mitigate | Grep gate confirms ONE `quantize_cents(-raw_pv)` and ONE `quantize_cents(max_pi)` and ONE `quantize_cents(max_loan_amount / request.target_ltv_pct)` — each at distinct end-of-quantity boundaries; intermediate Decimal stays full-precision |
| T-04-03-05 | Repudiation | StaleReferenceWarning suppressed in reverse | mitigate | Same warnings.catch_warnings(record=True) block as evaluate_forward; surfaces in response.warnings |
| T-04-03-06 | Tampering | FHA reverse mode iteration drift (chicken-and-egg loan_amount/property_value/MIP) | accept | One-shot D-08 design intentionally: zero-MI seed → loan estimate → MI estimate → final solve; iteration is OUT of scope per CONTEXT.md Deferred Items "Iterative PMI-LTV reverse solver bisection: out of scope". Documented in module docstring; round-trip tolerance covers compounded rounding (D-09). |
| T-04-03-07 | Tampering | UFMIP financing in reverse mode mismatched with forward auto-finance | accept | Action body explicitly states: reverse mode does NOT auto-finance UFMIP because target_ltv_pct + down_payment pin both sides of the LTV ratio. Forward and reverse share `_compute_monthly_mi`, but reverse passes `financed_loan_amount=zero_mi_loan_amount` (no UFMIP added) — documented and round-trip closure validates the consequence. |
</threat_model>

<verification>
After Task 1 completes:

```bash
# Round-trip closure (D-09) with SC-2 anchor
uv run python -c "from lib.affordability import evaluate_reverse, evaluate_forward; ..." # see verify block

# Phase regressions check
uv run pytest -x

# mypy + ruff clean
uv run mypy --strict lib/affordability.py
uv run ruff check lib/affordability.py
```
</verification>

<success_criteria>
- [ ] `evaluate_reverse(request: ReverseModeRequest) -> AffordabilityResponse` is implemented (no NotImplementedError)
- [ ] `npf.pv(rate=monthly_rate, nper=term_months, pmt=-max_pi, fv=0)` call matches RESEARCH pseudocode
- [ ] `max_loan_amount = quantize_cents(-raw_pv)` — sign-flipped + single quantize
- [ ] D-09 round-trip closure verified: `forward(reverse(req)).dti_back - req.max_dti <= Decimal("0.0001")`
- [ ] D-09 dollar equality verified: `forward(reverse(req)).loan_amount == reverse(req).max_loan_amount` exactly
- [ ] No Phase 1/2/3 regressions; full suite green
- [ ] mypy --strict + ruff clean
</success_criteria>

<output>
After completion, create `.planning/phases/04-affordability/04-03-SUMMARY.md` per the standard template.
</output>
