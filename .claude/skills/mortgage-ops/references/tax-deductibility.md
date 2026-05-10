# Tax Deductibility — IRS Pub 936 Mortgage Interest

Loaded on demand from SKILL.md per the topic→reference table. Triggers: "is mortgage interest deductible", "tax implications", "Pub 936".

## What this doc covers

The qualified-loan-limit cap structure under IRS Publication 936 (Phase 2 portion: REF-07 + RUL-11), and a cross-link to the Phase 6 after-tax refi-NPV mode (`references/refi-npv.md`) for the discounted-cashflow side of tax-aware refinance analysis.

## Qualified Loan Limit

Statutory authority: IRC §163(h)(3) (mortgage interest deduction) as amended by the Tax Cuts and Jobs Act of 2017 (TCJA). Source-of-truth values live in `data/reference/irs-pub936.yml`.

- **Post-2017 (TCJA):** `$750,000` cap on combined acquisition indebtedness for primary + secondary residence (single, MFJ, HoH); `$375,000` for MFS (Married Filing Separately, half). Interest on debt above the cap is not deductible.
- **Pre-2017 (grandfathered):** `$1,000,000` cap (single / MFJ / HoH); `$500,000` MFS. Applies to acquisition indebtedness incurred on or before 2017-12-15.

Source: IRS Publication 936 §"Limits on Home Mortgage Interest Deduction"; <https://www.irs.gov/pub/irs-pdf/p936.pdf>.

### Binding-Contract Grace Period (TCJA transition rule)

Debt qualifies as grandfathered (and gets the higher $1M cap) if BOTH:
1. The binding written contract was signed BEFORE 2017-12-15, AND
2. The loan closed BEFORE 2018-04-01.

Both conditions must be met. RUL-11 encodes these as TWO booleans (`binding_contract_signed_before_2017_12_15`, `binding_contract_closed_before_2018_04_01`) because a single origination_date cannot capture the two-date requirement.

## Qualified-Loan-Limit Predicate (RUL-11)

`lib.rules.irs_pub936.qualified_loan_limit(...)` implements the Pub 936 cap predicate. Function name verified against `lib/rules/irs_pub936.py` line 60 — Round-2 review (codex LOW 12) caught a draft that referenced a non-existent `..._worksheet(...)` symbol; the actual public name is `qualified_loan_limit` (no `_worksheet` suffix).

Signature:

```python
def qualified_loan_limit(
    filing_status: FilingStatus,                          # "single" | "mfj" | "mfs" | "hoh"
    has_grandfathered_debt: bool = False,
    binding_contract_signed_before_2017_12_15: bool = False,
    binding_contract_closed_before_2018_04_01: bool = False,
) -> Decimal:
```

Returns the deductible-interest cap (a `Decimal` dollar amount) for this filing status. The predicate dispatches on:
- `has_grandfathered_debt OR (both grace-period booleans True)` → pre-2017 caps
- otherwise → post-2017 caps

Loaded values come from `data/reference/irs-pub936.yml` via the standard `load_reference()` shim (so annual republication of Pub 936 is a YAML edit + commit, never a code change).

## Points Deductibility (Pub 936 §3) — OUT OF SCOPE for v1

Points-deductibility hinges on settlement-statement facts that the predicate does not have:

- **Loan origination points on a primary-residence purchase loan:** deductible in the year paid if itemized + meets the safe-harbor tests (not refinanced from elsewhere; computed as a percent of loan; etc.).
- **Refinance points:** amortized over the loan term, UNLESS proceeds funded improvements to the secured residence.

RUL-11 returns the qualified-loan-limit cap only; points-deductibility is documented in `data/reference/irs-pub936.yml` for completeness but not computed.

## Phase 6 After-Tax Refi NPV (cross-link)

Per STATE.md, Phase 6 (refinance NPV) is COMPLETE. The after-tax mode is the canonical place where IRS Pub 936 limits intersect with discounted-cashflow analysis: when a refinance changes the interest portion of the housing payment (and therefore the deductible interest), the NPV calculation must net out the marginal-tax-rate effect to reflect the borrower's true after-tax savings.

The high-level rule:

- Marginal tax rate enters the calc as a per-call parameter (or via `modes/_profile.md` if a future skill-level override is added).
- After-tax interest savings = pre-tax interest savings × (1 − marginal_rate)
- After-tax NPV = Σ (after-tax savings discounted at after-tax discount rate)

For the AUTHORITATIVE description of the after-tax mode (cashflow construction, discount-rate selection, qualified-loan-limit interaction when refinancing across the $750k threshold), load `references/refi-npv.md` — Phase 6 authored that doc as the source-of-truth for refi NPV conventions, and Plan 10-04 Task 2 byte-lifted it into the skill folder (drift-protected by Wave 5 byte-equality test).

## Cross-References

- `data/reference/irs-pub936.yml` — REF-07; Phase 2 source-of-truth (caps + grace-period rules)
- `lib/rules/irs_pub936.py` — RUL-11; `qualified_loan_limit(filing_status, ...)` (Phase 2)
- `lib/refinance.py` + `.claude/skills/mortgage-ops/scripts/refi_npv.py` — Phase 6 SHIPPED; relocated by Plan 10-01
- `.claude/skills/mortgage-ops/references/refi-npv.md` — Phase 6 reference, byte-lifted by Plan 10-04 Task 2 (after-tax mode authoritative)
- `references/affordability-rules.md` — DTI uses pre-tax income (deductibility does NOT enter affordability; it enters NPV)

**Last reviewed:** 2026-05-08
