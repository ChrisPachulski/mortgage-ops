# GSE Loan Limits (FHFA conforming + FHA + VA + USDA)

Loaded on demand from SKILL.md per the topic→reference table. Triggers: "what's the conforming limit", "what's a jumbo", "what's the FHA ceiling here".

## What this doc covers

The classification thresholds behind `lib/rules/loan_type.py::classify(...)`: the FHFA conforming baseline + ceiling, the FHA floor + ceiling, the VA entitlement model, and the USDA rural/income test. Numeric values authoritative in `data/reference/conforming-limits-2026.yml` and `data/reference/fha-limits-2026.yml`; this doc explains the mechanism.

## FHFA Conforming Limits (2026)

Source: FHFA news release 2025-12-04, effective for loans with pool issue dates on or after 2026-01-01.

- **Baseline 1-unit:** `$832,750`
- **Ceiling 1-unit (high-cost areas):** `$1,249,125` (= 150% × baseline)

Per-county data (which counties get the ceiling vs the baseline) is shipped in `data/reference/conforming-limits-2026.yml` under `limits.high_cost_counties`. We ship a high-volume subset covering CA / NY / DC / FL / WA / MA / VA / NJ / CT / HI / AK metros — the rest of the ~232 nationwide high-cost counties are NOT shipped. Counties not present:
- Get the baseline limit if loan ≤ baseline,
- Raise `MissingCountyDataError` if loan > baseline (so the user knows to extend the table).

Multi-unit limits (2/3/4-unit) live in the YAML but `lib/rules/loan_type.classify` rejects `unit_count > 1` for v1.

## Jumbo Classification

A loan is **jumbo** if `loan_amount > applicable_county_limit`. Jumbos are non-agency (not eligible for Fannie/Freddie purchase) and follow lender-overlay underwriting (typically tighter DTI + reserve requirements). v1 classifies jumbo but does NOT model jumbo-specific overlays — those are out of scope.

## FHA Limits (2026)

Source: HUD Mortgagee Letter 2025-23, effective for FHA case numbers assigned on or after 2026-01-01.

- **Floor 1-unit:** `$541,287` (= 65% × FHFA baseline)
- **Ceiling 1-unit:** `$1,249,125` (matches conforming ceiling)

Per-county FHA limits are computed per MSA, but HUD publishes per-county tables that we ship in `data/reference/fha-limits-2026.yml`. Same subset semantics as conforming: unlisted high-cost counties → `MissingCountyDataError`. The `lib.rules.loan_type._county_limit_fha` helper enforces this (BL-01 / BL-05 fix).

## VA Loans

Source: 38 USC §3703(a)(1)(C) + VA Circular 26-19-30 (no county limits since 2020 for veterans with full entitlement).

- **No statutory cap** for veterans with full entitlement (per the Blue Water Navy Vietnam Veterans Act of 2019).
- VA uses an **entitlement model**: each veteran has a basic entitlement ($36,000 base, 25% of the conforming limit available beyond) which guarantees a portion of the loan.
- Veterans with prior VA loans not yet paid off use partial entitlement; in that case county limits re-engage.
- v1 models the no-statutory-cap default; partial-entitlement scenarios are out of scope.

## USDA Section 502

Source: USDA Rural Development Guaranteed Loan program (RD Instruction 1980-D, 7 CFR §3555).

- **Property eligibility:** rural area per USDA's per-address GIS lookup. We do NOT ship the GIS data; the user supplies an `is_rural` boolean (caller verifies via the USDA online tool).
- **Income limit:** household income ≤ 115% of area median income, varies by household size. Encoded per state/county in (future) `data/reference/usda-income-limits.yml` (currently inline in `lib/rules/usda.py`).
- **No down-payment requirement:** 100% LTV permitted (financed funding fee).

## classify() Decision Tree (RUL-01)

`lib.rules.loan_type.classify(loan_amount, location, va_eligible, usda_inputs)` runs in this order:

1. If `va_eligible` and full entitlement → `va`
2. If `usda_inputs.is_rural` and income test passes → `usda`
3. If `loan_amount ≤ FHA_county_limit` and FHA borrower → `fha`
4. If `loan_amount ≤ conforming_county_limit` → `conventional/conforming`
5. Else → `conventional/jumbo`

Borrower may opt out of FHA even if eligible (cost tradeoff: FHA MIP is life-of-loan above 90% LTV; conventional PMI terminates at 78% LTV per HPA — see `references/mip-pmi.md`).

## Cross-References

- `data/reference/conforming-limits-2026.yml` — REF-01, FHFA baseline + ceiling + per-county subset
- `data/reference/fha-limits-2026.yml` — REF-02, FHA floor + ceiling + per-county subset
- `lib/rules/loan_type.py` — `classify()`, `_county_limit`, `_county_limit_fha`, `MissingCountyDataError`
- `references/mip-pmi.md` — MI rules per program
- `references/affordability-rules.md` — blocker precedence (classify() runs first)

**Last reviewed:** 2026-05-08
