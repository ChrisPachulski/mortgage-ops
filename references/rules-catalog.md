# Rules Catalog

This catalog is the human-facing inventory for `lib/rules/`. The rule layer is
the underwriting-workbench moat: each predicate turns a cited public rule or
documented heuristic into a deterministic decision surface that downstream
affordability, property analysis, and reports can cite.

`tests/test_rules/test_citation_coverage.py` enforces the mechanical floor:
every predicate module must have a module docstring with `Citation:`,
`Source URL:`, `Effective:`, and at least one fixture under
`tests/fixtures/rules/{predicate}_*.json`. This catalog adds the operator-facing
summary: what each predicate decides, which source/version it was checked
against, and whether the rule is regulatory or heuristic.

## Scope Rule

Treat `lib/rules/` as decision infrastructure, not generic calculator code.
New predicates are appropriate when they support an underwriting verdict,
eligibility/blocker explanation, reference-data refresh, or report citation.
Generic math that does not feed a GO / WATCH / NO-GO decision belongs outside
the rules layer.

## Current Roster

| Module | Kind | Decides | Source / citation | Effective / checked | Fixture prefix |
|---|---|---|---|---|---|
| `loan_type.py` | Regulatory limit classifier | Conventional conforming / high-balance / jumbo, FHA standard / high-balance, VA high-balance, USDA marker | FHFA conforming limits under 12 USC §1717; HUD FHA loan limits under NHA §203(b)(2) | 2026-01-01 | `loan_type_` |
| `fha_mip.py` | Regulatory fee predicate | FHA UFMIP, annual MIP rate, MIP termination period | HUD Handbook 4000.1 §II.A.8.b and §II.A.8.q; historical HUD ML 2023-05 and ML 2013-04 | 2023-03-20 rate; Handbook 4000.1 Update 15 checked 2024-05 | `fha_mip_` |
| `va_funding_fee.py` | Regulatory fee predicate | VA funding fee dollars by purpose, use count, down payment, and exemption | 38 USC §3729; VA Lender Handbook M26-7 Chapter 8 | 2023-04-07 | `va_funding_fee_` |
| `va_residual_income.py` | Regulatory underwriting predicate | VA residual-income pass/fail and minimum required income | VA Lender Handbook M26-7 Topic 7 residual income tables | 2023-04-07 | `va_residual_income_` |
| `usda.py` | Regulatory eligibility/fee predicate | USDA income eligibility, applicable income cap, upfront guarantee fee, annual guarantee fee | 7 CFR Part 3555; USDA RD income-limit lookup | 2025-10-01 | `usda_` |
| `irs_pub936.py` | Tax-rule predicate | Qualified-loan-limit cap for mortgage interest deduction | IRC §163(h)(3) as amended by TCJA; IRS Publication 936 Table 1 | 2025-01-01 | `irs_pub936_` |
| `conventional_pmi.py` | Statutory servicing predicate | HPA PMI auto-termination, request-eligible, in-force, high-risk midpoint statuses | 12 USC §4901-4910 Homeowners Protection Act | 1999-07-29; no material amendment since | `conventional_pmi_` |
| `fannie_eligibility.py` | GSE pricing predicate | Fannie Mae LLPA bps by credit, LTV, purpose, occupancy, unit count | Fannie Mae LLPA Matrix, Single-Family Selling Guide §B5-1 | 2026-01-28 | `fannie_eligibility_` |
| `freddie_eligibility.py` | GSE eligibility/pricing predicate | Freddie published matrix eligibility and Credit Fee Cap bps | Freddie Mac Seller/Servicer Guide §4203.4 and Credit Fee Cap matrix | 2026-01-15 | `freddie_eligibility_` |
| `atr_qm.py` | Regulatory compliance predicate | General QM and Safe-Harbor price-based APR/APOR spread tests | 12 CFR §1026.43(e)(2), CFPB Dec 2020 General QM final rule | Mandatory compliance 2022-10-01 | `atr_qm_` |
| `reg_z.py` | Regulatory tolerance predicate | APR disclosure tolerance pass/fail for regular vs irregular transactions | 12 CFR §1026.22(a)(2)-(a)(3) | 2010-09-30 | `reg_z_` |
| `pmi.py` | Industry heuristic predicate | Conventional monthly borrower-paid PMI annual rate estimate and reason tag | Arch MI Borrower-Paid Monthly Non-Refundable Annualized BPMI Rate Card; cross-checked against major MI filed rates | 2026-02-09 | `pmi_` |
| `insurance.py` | Industry heuristic predicate | Homeowners-insurance fallback estimate by state, flood-zone multiplier, earthquake add-on | NAIC Homeowners Insurance Report, III CA/TX state averages, private-market flood/quake heuristics | Re-checked 2026-05-23 | `insurance_` |

## Non-Predicate Files

`_loader.py` and `types.py` are infrastructure. They are intentionally excluded
from predicate-count tests:

- `_loader.py` loads committed YAML reference data and emits stale-reference
  warnings when `effective:` is more than 12 months old.
- `types.py` holds shared Pydantic/Literal types used by multiple predicates.
- `__init__.py` is only the package marker.

## Update Protocol

When adding or materially changing a predicate:

1. Add or update the module docstring with `Citation:`, `Source URL:`, and
   `Effective:` lines.
2. Put mutable rates, thresholds, and tables in `data/reference/*.yml` unless
   the value is a stable statutory constant.
3. Add at least one hand-checkable fixture under `tests/fixtures/rules/`.
4. Update `tests/test_rules/test_phase2_smoke.py` if the predicate roster
   changes.
5. Update this catalog in the same change.
6. If the predicate feeds property reports, verify the report reason tag and
   citation footer still explain the exact computed value.

## Strategic Boundary

Predicates are the part that turns a mortgage calculator into an underwriting
workbench. A commodity library can produce payment schedules; it generally will
not say which public rule was applied, which data vintage was used, why a loan
is blocked, or which estimate was a heuristic. Protect that boundary.
