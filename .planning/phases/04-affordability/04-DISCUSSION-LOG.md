# Phase 4: Affordability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 04-affordability
**Areas discussed:** PITI component sourcing, Joint-applicant credit-score model, Reverse-affordability solver shape, Binding-rule blocker precedence

---

## PITI component sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| Caller-supplied monthly $ (Recommended) | household.yml grows: property_tax_monthly, insurance_monthly, hoa_monthly (Decimal strings). PMI from conventional_pmi predicate; MIP from fha_mip predicate. Simplest. Matches "user enters numbers manually as YAML" principle. v2 can add ZIP-based lookup. | ✓ |
| Annual % of property value | household.yml grows property_tax_rate_pct, insurance_rate_pct (annual %). System computes monthly = property_value × rate / 12. Cleaner for what-if scenarios; user has to estimate rates per county (vary widely). | |
| Hybrid (monthly $ OR annual %) | Pydantic discriminated union per field: caller passes EITHER monthly_$ OR annual_rate_pct. Most flexible; validation/test surface roughly doubles. | |
| Monthly $ for tax/ins/HOA, predicate for PMI/MIP only | Same as option 1 but explicit that v1 will NOT support % rates and v2 may. Document explicitly in AFFD-09. Functionally identical to option 1. | |

**User's choice:** Caller-supplied monthly $ (Recommended)
**Notes:** Captured as D-01 (escrow block in household.yml), D-02 (PMI/MIP from predicates), D-03 (UFMIP financing → planner discretion), D-04 (property_value as per-request input).

---

## Joint-applicant credit-score model

| Option | Description | Selected |
|--------|-------------|----------|
| Single int per applicant; pick lower across applicants (Recommended) | Keep Phase 1 shape: applicants[].credit_score: int. Treat single value AS applicant's representative score. Phase 4 picks min across applicants for Fannie LLPA / Freddie eligibility. Aligns with "fail loud, no inference" + "user enters numbers manually". | ✓ |
| Three bureau scores per applicant; pick lower-of-mids | Extend schema: applicants[].credit_scores: {equifax, experian, transunion}. Phase 4 computes mid-of-three per applicant, then min across. Most faithful to GSE underwriting; more YAML to fill out; redundant if user only knows one number. | |
| Accept either shape (single int OR three-key dict) | Pydantic discriminated union on credit_score. Most flexible; validation surface and tests roughly double. | |
| Optional middle score field with int fallback | applicants[].credit_score: int + optional bureau_scores: {...} for record/audit only. Phase 4 always reads credit_score for picks; bureau_scores is metadata. | |

**User's choice:** Single int per applicant; pick lower across applicants (Recommended)
**Notes:** Captured as D-05 (single int, lower across applicants), D-06 (income aggregation = sum), D-07 (single-applicant via list of length 1).

---

## Reverse-affordability solver shape

| Option | Description | Selected |
|--------|-------------|----------|
| Caller-supplied down_payment + target LTV pinned (Recommended) | Reverse request: { max_dti, gross_monthly_income, monthly_debts, down_payment, target_loan_type, term_months, annual_rate, monthly_tax, monthly_insurance, monthly_hoa }. LTV is pinnable; one-shot solve via npf.pv. SC-2 trivially passes. | ✓ |
| Bisection over loan amount (PMI/MIP recomputed each step) | Solver iterates on loan_amount; recompute LTV → PMI status → PITI → check vs DTI cap. More "correct" when LTV crosses 80%. Bisection loop, convergence test, ~50-row test surface. Likely overkill for personal-use. | |
| Caller-supplied target LTV bucket directly | Reverse request includes target_ltv_pct: "0.80". Simplest. Trades user-facing clarity for solver simplicity. | |
| Two-pass (assume no PMI, then check) | Pass 1: solve max_loan ignoring PMI. Pass 2: compute LTV; if > 80%, recompute with PMI; iterate at most twice. Compromise. | |

**User's choice:** Caller-supplied down_payment + target LTV pinned (Recommended)
**Notes:** Captured as D-08 (one-shot npf.pv with pinned LTV), D-09 (round-trip closure within Decimal("0.0001") rate-of-rounding tolerance), D-10 (reverse-mode JSON request shape locked).

---

## Binding-rule blocker precedence

| Option | Description | Selected |
|--------|-------------|----------|
| Single blocked_by + warnings list (Recommended) | { blocked: bool, blocked_by: str \| None, warnings: list[str] }. blocked_by = FIRST hard-fail in fixed priority order: loan-type → LTV/CLTV → DTI → ATR/QM → VA residual. Soft signals (LLPA, PMI required) → warnings. Matches SC-3's "never silent" language and example syntax. | ✓ |
| All blockers in a list (no priority) | { blocked: bool, blockers: list[str] }. Every failing predicate fires its citation. Cost: ROADMAP SC-3 example shows singular "blocked_by" — would deviate from example wording. | |
| Single blocked_by only (no warnings) | { blocked: bool, blocked_by: str \| None }. Strict to ROADMAP example. No soft warnings in output. | |
| Structured: blocked_by + soft_blockers + advisories | Three-tier. Most informative. Most schema. Probably overkill for v1. | |

**User's choice:** Single blocked_by + warnings list (Recommended)
**Notes:** Captured as D-11 (precedence order + soft-warning citation list), D-12 (DTI cap source = caller-supplied max_dti, no defaults). Stale-reference warnings from Phase 2 D-12 propagate through warnings field via warnings.catch_warnings().

---

## Claude's Discretion

The following items were intentionally left to planner / executor discretion (recorded in CONTEXT.md `<decisions>` "Claude's Discretion" subsection):

- AffordabilityRequest / AffordabilityResponse Pydantic shape (single class with optional fields vs discriminated union by `mode`)
- Final string formats for non-VA-residual `blocked_by` citations (FHFA-LIMIT-..., LTV-CEILING-..., DTI-CAP-..., ATR-QM-PRICE-FIRST). VA residual format is HARD-LOCKED at `VA-RESIDUAL-{REGION}-FAMILY-{N}` per Phase 2 D-11.
- UFMIP financing convention (caller pre-finances vs lib.affordability auto-finances)
- PMI auto-termination period (`pmi_terminates_at_period`) advisory in warnings — add only when first downstream consumer needs it.
- CLTV junior-lien input shape (simple `list[Money]` vs structured)
- ATR/QM apr+apor request fields (gating: missing → advisory only, not blocker)
- Test runner pattern (extend existing tests/conftest.py with affordability_fixture loader mirroring Phase 3)

## Deferred Ideas

- % rate-based PITI inputs → v2
- ZIP / county-keyed tax+insurance lookup → v2 (PROP-02)
- Three-bureau credit-score dict per applicant → out of v1 scope
- Income-type modeling (W-2 vs self-employed averaging) → out of v1 scope
- Per-loan-type DTI cap YAML in data/reference/ → v2 if bare max_dti UX becomes painful
- PMI auto-termination period advisory → add when first consumer needs it
- CLTV junior-lien structured shape → v2
- Iterative PMI-LTV reverse solver (bisection) → out of scope; caller pins LTV
- AffordabilityResponse advisory tier (soft_blockers separate from warnings) → v2 if needed
- Stdin-based CLI input → v2 (inherits Phase 3 D-18)
