# Affordability Rules (Phase 4 DTI/LTV/CLTV/PITI + reverse-affordability)

Loaded on demand from SKILL.md per the topic→reference table. Triggers: "what's DTI", "how is affordability computed", "explain residual income".

## What this doc covers

The metrics and predicates behind `lib/affordability.py` and `.claude/skills/mortgage-ops/scripts/affordability.py`: front-end vs back-end DTI, LTV, CLTV, the PITI breakdown, the reverse-affordability solver, the joint-applicant credit-score rule, and the blocker-precedence hierarchy that produces `BLOCKED_BY_*` citation constants.

## Forward Mode: DTI / LTV / CLTV / PITI

### DTI (debt-to-income)

Two ratios reported, both as decimals (display layer formats as `43.0%` per D-NUM-03):

- **Front-end DTI (housing-only):** `monthly_PITI / gross_monthly_income`
- **Back-end DTI (housing + other monthly debts):** `(monthly_PITI + monthly_debts) / gross_monthly_income`

Where `gross_monthly_income` = sum of applicant gross monthly incomes. Treat the DTI target as a borrower-affordability and program-overlay input, not the General QM legal test. Current General QM is price-based: `lib.rules.atr_qm` compares APR against APOR thresholds, while lender and agency overlays may still impose DTI limits for qualification.

### LTV / CLTV

- **LTV:** `loan_amount / property_value`
- **CLTV:** `(loan_amount + sum(junior_lien_balances)) / property_value`

Reported as decimals (display formats as `97.5%`, etc.). LTV thresholds drive PMI/MIP and conforming/jumbo classification (see `references/gse-limits.md` and `references/mip-pmi.md`).

### PITI breakdown

Monthly housing payment is the sum of:

```
PITI = P&I  +  property_tax/12  +  hazard_insurance/12  +  HOA  +  mortgage_insurance
```

Where:
- **P&I:** from `lib/amortize.py` (level monthly payment; see `references/amortization-formulas.md`).
- **Property tax / hazard insurance:** annual amounts from `EscrowInputs`, divided by 12.
- **HOA:** monthly dollar amount.
- **Mortgage insurance:** PMI for conventional > 80% LTV, FHA MIP per `references/mip-pmi.md`, none for VA/USDA (which carry their own funding fees, modeled separately).

## Reverse Mode (AFFD-05 + Phase 4 D-09)

"What's the largest loan I can carry?" — solve for `max_loan_amount` given a target max P&I and a target LTV.

Steps:
1. From `gross_monthly_income`, `back_end_dti_target`, and `monthly_debts`, derive `max_PITI`.
2. Subtract escrow + HOA + estimated MI to get `max_PI`.
3. Invert PMT via `numpy_financial.pv`:

```python
max_loan_amount = quantize_cents(
    -npf.pv(rate=annual_rate / Decimal("12"),
            nper=term_months,
            pmt=-max_PI,
            fv=0)
)
```

(See `lib/affordability.py` line 65, locked decision D-08.) Round-trip closure (D-09): plug `max_loan_amount` back through forward mode and confirm the resulting P&I equals the input `max_PI` to the cent.

## Joint Applicants (AFFD-06)

For multi-applicant loans, the underwriter uses the **lower of the mid scores** across applicants (Fannie/Freddie convention). For each applicant we sort their three bureau scores ascending and pick the middle (mid) score; then across applicants we take the minimum of those mids. This drives PMI rate buckets and, in some lender overlays, the rate sheet itself.

## Blocker Precedence (Phase 4 D-11)

Affordability checks are NOT independent. They run in a fixed first-binding-rule-wins order; the first failing rule's citation constant is returned in `blocked_by`:

1. **classify** (`lib.rules.loan_type.classify`) — must succeed (loan must be a recognized program: conventional/conforming, conventional/jumbo, FHA, VA, USDA). Failure → `BLOCKED_BY_CLASSIFY`.
2. **USDA income test** (`lib.rules.usda`) — applicant household income must be ≤ 115% area median (USDA Section 502 Direct rule). Only run for USDA candidates.
3. **LTV / CLTV bounds** (`lib.rules.loan_type._max_ltv`) — per program (e.g., FHA min downpayment = 3.5%, conventional ≥ 3% on first-time-buyer programs).
4. **DTI** — back-end DTI vs the caller-supplied affordability/program overlay cap (for example, FHA manual-underwriting overlays can allow higher DTIs with compensating factors).
5. **ATR/QM** (`lib.rules.atr_qm`) — Reg Z 12 CFR §1026.43 ability-to-repay; General QM safe harbor/rebuttable-presumption status is determined by the APR-vs-APOR price thresholds implemented in the rules module.
6. **VA residual income** (`lib.rules.va_residual_income`) — VA-only; minimum residual income table per region + family size (M26-7 Ch 4).

Output schema: `affordable: false`, `blocked_by: "BLOCKED_BY_DTI"`, `citation: "CFPB §1026.43(c)(2)"`, plus the binding rule's pass/fail data for narration.

## Cross-References

- `lib/affordability.py` — `evaluate_forward`, `evaluate_reverse`, blocker chain
- `lib/rules/loan_type.py` — `classify()` dispatcher (`references/gse-limits.md`)
- `lib/rules/conventional_pmi.py`, `lib/rules/fha_mip.py` — MI predicates (`references/mip-pmi.md`)
- `lib/rules/atr_qm.py` — ATR/QM APR-vs-APOR price-threshold logic
- `lib/rules/va_residual_income.py` — VA M26-7 grid
- `lib/rules/usda.py` — USDA Section 502 income test
- `.claude/skills/mortgage-ops/scripts/affordability.py` — JSON-in/JSON-out CLI

**Last reviewed:** 2026-05-08
