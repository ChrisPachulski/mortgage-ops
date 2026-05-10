# Mortgage Insurance (FHA MIP + Conventional PMI)

Loaded on demand from SKILL.md per the topic→reference table. Triggers: "what are MIP rules", "when does PMI drop off", "FHA insurance".

## What this doc covers

The two mortgage-insurance regimes — FHA Mortgage Insurance Premium (MIP, both up-front and annual) and conventional Private Mortgage Insurance (PMI) — and the rules that govern when each terminates. Numeric rates are authoritative in `data/reference/fha-mip-rates.yml`; this doc explains the mechanism.

## FHA MIP

Source: HUD Mortgagee Letter 2023-05 (effective 2023-03-20). Predicate: `lib/rules/fha_mip.py` (RUL-04).

### UFMIP (Up-Front MIP)

- **Rate:** `1.75%` of the base loan amount (`ufmip_rate: "0.0175"` in YAML).
- **Mechanism:** charged at closing, **financed into the principal by default** (Phase 4 D-03). The borrower's note amount becomes `base_loan + UFMIP`, and amortization runs against the financed principal. This is why the FHA loan principal exceeds the property purchase loan amount on the closing disclosure.
- **Refundability:** partial refund available if the loan terminates within the first 36 months (sliding scale per HUD); not modeled in v1.

### Annual MIP (paid monthly)

Tabular rate per `(term_months_band, LTV_band, loan_amount_tier)`. Two tiers:
- **Standard tier:** `loan_amount ≤ $726,200` (the 2023 conforming baseline; HUD anchors here, not the current-year FHFA baseline).
- **High-balance tier:** `loan_amount > $726,200`.

Long-term loans (`term > 15yr`, i.e., months 181-360):
- LTV > 95% → **0.55%** (standard) / **0.75%** (high-balance)
- LTV 90-95% → **0.50%** / **0.70%**
- LTV ≤ 90% → **0.50%** / **0.70%**

Short-term loans (`term ≤ 15yr`, i.e., months 1-180): rates ~0.40% standard / 0.40% high-balance regardless of LTV (with a low-LTV reduction to 0.15% for standard at LTV ≤ 90%).

The annual MIP is divided by 12 and added to the monthly housing payment.

### Termination (HUD ML 2013-04, unchanged in 2023-05)

- **Origination LTV > 90%:** MIP runs for the **life of the loan**. The borrower cannot drop FHA MIP by paying down to 78% — the only escape is to refinance into a conventional loan once equity supports it.
- **Origination LTV ≤ 90%:** MIP **terminates at 132 months** (= 11 years × 12). After month 132, the monthly MIP component drops off the housing payment.

This life-of-loan provision is the single biggest reason borrowers refinance from FHA to conventional once they cross 78% LTV.

## Conventional PMI

Source: Homeowners Protection Act of 1998 (HPA) — 12 USC §4901-4910 + 12 CFR §1024 implementing Reg X. Predicate: `lib/rules/conventional_pmi.py` (RUL-05).

### When required

- Conventional loans with origination LTV > 80% require PMI (Fannie/Freddie convention; some lender overlays may waive at LTV ≤ 85% for very strong files).
- Rate varies by LTV bucket (95-97%, 90-95%, 85-90%, 80-85%) and credit-score bucket. Industry rates roughly 0.20% to 1.50% annually; v1 uses a simple LTV-only tier model in `lib/rules/conventional_pmi.py`.

### Termination — HPA's two thresholds

The HPA gives borrowers two escape valves:

1. **Automatic termination at 78% LTV** (based on **original** amortization schedule, NOT current home value): the servicer MUST cancel PMI once the scheduled balance reaches 78% of the original property value. Triggered automatically; no borrower request needed.
2. **Borrower-requested cancellation at 80% LTV**: the borrower may request cancellation once the scheduled balance reaches 80% of original property value, subject to good payment history. Requires a request — does not happen automatically.

Both thresholds use the original amortization schedule; appraisal-based equity claims (e.g., "my house is now worth more, so my LTV is 75% via current value") are NOT covered by HPA — those require a separate value-based cancellation request which the servicer may grant under its own policy.

### Final-termination at midpoint (HPA §4902(b))

Independent of the 78% trigger, PMI MUST terminate at the loan's amortization midpoint regardless of LTV. For a 30-year loan that's month 180; for a 15-year loan that's month 90. This is rarely the binding rule (most loans hit 78% LTV before midpoint).

## LPMI (Lender-Paid PMI) — Not Modeled

Some loans bake the PMI premium into a higher interest rate (lender pays MI; borrower pays a higher coupon). The PMI is therefore non-cancellable (you can't terminate something you're not paying as a separate line). Tradeoff: lower monthly housing payment vs. permanently higher rate. v1 does NOT model LPMI; if a user has an LPMI loan, treat the rate as the all-in rate and skip the MI line.

## Cross-References

- `data/reference/fha-mip-rates.yml` — REF-03, UFMIP + annual MIP table + termination rules
- `lib/rules/fha_mip.py` — RUL-04, `compute_fha_mip(...)`, life-of-loan vs 132-month termination
- `lib/rules/conventional_pmi.py` — RUL-05, `requires_pmi`, `pmi_terminates_at`, HPA logic
- `references/affordability-rules.md` — PITI breakdown (MI is the "I" line for high-LTV loans)
- `references/gse-limits.md` — LTV thresholds for classification

**Last reviewed:** 2026-05-08
