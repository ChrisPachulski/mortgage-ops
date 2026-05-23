# Reference Data & Rule Predicate Refresh Ledger

**Last full review:** 2026-05-23
**Maintainer:** household maintainer (single-person project, v1)

This ledger is the single canonical map of every regulatory data file
(`data/reference/*.yml`) and every rule predicate (`lib/rules/*.py`) that the
mortgage-ops calc engine relies on. For each entry it records what is pinned,
the source (preferably a primary government URL), the effective date, the
refresh process, the validation oracle, known limitations, and the last review
date.

The ledger is **informational**. No CI step enforces it. It exists so that the
single maintainer can answer "where did this number come from and when do I
re-check it?" in one place.

## Cadence

- Reference YAMLs are reviewed annually (next sweep: **2027-05-23**) or
  whenever a `StaleReferenceWarning` fires on `uv run pytest`
  (>12 months since `effective:`, per `lib/rules/_loader.py:90`).
- Rule predicates change only when their underlying regulatory citation
  changes. The YAML refresh path is preferred — predicates are designed so
  annual updates touch only the YAML (`source:` + `effective:` + body),
  not Python code.
- See `docs/dependency-review.md` for the separate dependency-audit cadence.

## How to refresh a YAML

1. Open `data/reference/<name>.yml`.
2. Replace the body with the new published values from the `source:` URL.
3. Bump the `effective:` field to the publication date (unquoted YAML date,
   `YYYY-MM-DD`).
4. Commit. The next `uv run pytest` run will go quiet for that file because
   `_check_staleness` (`lib/rules/_loader.py:90`) compares `effective:`
   against `date.today() - relativedelta(months=12)`.

## Reference YAMLs (12)

### `data/reference/conforming-limits-2026.yml`
- **Pins:** 2026 FHFA conforming-loan baseline ($832,750 1-unit) + ceiling
  ($1,249,125) and the high-cost-county subset that gets the ceiling.
- **Source:** https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026
- **Effective:** 2026-01-01
- **Refresh command:** edit `data/reference/conforming-limits-2026.yml`,
  replace per-county block from FHFA county XLSX, bump `effective:`, commit.
- **Validation oracle:** `tests/test_reference/test_schema.py`,
  `tests/test_reference/test_yaml_count_audit.py`,
  `tests/test_rules/test_loan_type.py` (consumer-side oracles); external:
  FHFA news release.
- **Limitations:** Ships a SUBSET of high-cost counties (CA / NY / DC / FL /
  WA / MA / VA / NJ / CT / HI / AK metros — ~232 high-cost counties nationally
  per FHFA, only the highest-volume subset shipped per D-PHASE2-Q2). Counties
  not listed get the baseline; if `loan_amount > baseline` and county is not
  in the subset, `lib.rules.loan_type.classify` raises
  `MissingCountyDataError`. Multi-unit fields populated only at the baseline /
  ceiling level — per-county multi-unit data not shipped because v1 only
  supports `unit_count=1`.
- **Last reviewed:** 2026-05-23

### `data/reference/fha-limits-2026.yml`
- **Pins:** 2026 HUD FHA forward-mortgage floor ($541,287 1-unit) + ceiling
  ($1,249,125) + the high-cost-county subset.
- **Source:** https://www.hud.gov/sites/dfiles/hudclips/documents/2025-23hsgml.pdf
  (HUD Mortgagee Letter 2025-23)
- **Effective:** 2026-01-01
- **Refresh command:** edit `data/reference/fha-limits-2026.yml`, replace
  per-county block from HUD's per-county tables, bump `effective:`, commit.
- **Validation oracle:** `tests/test_reference/test_schema.py`,
  `tests/test_reference/test_yaml_count_audit.py`,
  `tests/test_rules/test_loan_type.py` (consumer-side oracles); external:
  HUD ML 2025-23.
- **Limitations:** Same county-subset semantic as conforming — unlisted
  high-cost counties raise `MissingCountyDataError` rather than silently
  returning the floor. Multi-unit data shipped only at floor/ceiling level
  (v1 supports `unit_count=1` only).
- **Last reviewed:** 2026-05-23

### `data/reference/fha-mip-rates.yml`
- **Pins:** FHA annual MIP rate table (post-HUD ML 2023-05 30-bps reduction)
  + UFMIP rate (1.75%) + termination rules (life-of-loan vs 132 months).
- **Source:** https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf
  (HUD Mortgagee Letter 2023-05). Predicate docstring also cites the operative
  HUD Handbook 4000.1 §II.A.8.b URL where the ML was re-housed.
- **Effective:** 2023-03-20
- **Refresh command:** verify against the current HUD Handbook 4000.1
  publication; edit the table if HUD publishes a superseding ML, then bump
  `effective:`, commit.
- **Validation oracle:** `tests/test_rules/test_fha_mip.py` (golden fixtures);
  external: HUD ML 2023-05 PDF.
- **Limitations:** Effective date is older than the 12-month staleness
  threshold (StaleReferenceWarning WILL fire); this is intentional per the
  YAML notes because HUD has not republished. Pre-2023-03-20 endorsement
  dates raise `NotImplementedError` (grandfathering deferred to v2).
- **Last reviewed:** 2026-05-23

### `data/reference/va-funding-fees.yml`
- **Pins:** VA funding-fee table per 38 USC §3729 + VA Lender Handbook M26-7
  Chapter 8: purchase (banded by down-payment + first-vs-subsequent use),
  cash-out refi (flat), IRRRL (0.50%), manufactured-home-non-permanent,
  loan-assumption fees.
- **Source:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf
- **Effective:** 2023-04-07
- **Refresh command:** verify against the current M26-7 Chapter 8 PDF / latest
  VA Circular; edit the per-row fees, bump `effective:`, commit.
- **Validation oracle:** `tests/test_rules/test_va_funding_fee.py` (golden
  fixtures); external: VA M26-7 Chapter 8 PDF.
- **Limitations:** Effective date older than 12 months — `StaleReferenceWarning`
  WILL fire (intentional; VA has not republished). Down-payment bands are
  exclusive of upper bound (`0..<5`, `5..<10`, `>=10`). Veterans receiving VA
  disability compensation are EXEMPT (fee = $0); that flag is a caller
  responsibility.
- **Last reviewed:** 2026-05-23

### `data/reference/va-residual-income.yml`
- **Pins:** VA residual-income minimum thresholds by region
  (northeast / midwest / south / west), family size 1-5, and loan-amount
  band (< $80k vs >= $80k), with $80 per extra family member above 5.
- **Source:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/
  (VA Lender Handbook M26-7 Topic 7)
- **Effective:** 2023-04-07
- **Refresh command:** verify against M26-7 Topic 7; edit the per-region
  table, bump `effective:`, commit.
- **Validation oracle:** `tests/test_rules/test_va_residual_income.py`
  (golden fixtures); external: VA M26-7 Topic 7.
- **Limitations:** Effective date older than 12 months —
  `StaleReferenceWarning` WILL fire (intentional). Below-$80k tier values
  documented as ~10-12% lower than the >=$80k tier per published M26-7.
  Predicate emits a stable `VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}` citation
  string that Phase 4 affordability `blocked_by` reporting depends on —
  format drift breaks Phase 4.
- **Last reviewed:** 2026-05-23

### `data/reference/usda-income-limits.yml`
- **Pins:** USDA SFH GLP income limits (115% AMI) for 1-4-person and
  5-8-person households (default + per-county overrides) + 8% per extra
  member above 8 + guarantee-fee structure (1.00% upfront, 0.35% annual)
  per 7 CFR §3555.107.
- **Source:** https://www.rd.usda.gov/files/rd-grhlimitmap.pdf
  (predicate docstring also cites
  https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do)
- **Effective:** 2025-10-01 (USDA fiscal-year start; within 12mo window)
- **Refresh command:** verify against the current USDA SFH GLP eligibility
  worksheet; edit the per-county overrides and default limits, bump
  `effective:`, commit.
- **Validation oracle:** `tests/test_rules/test_usda.py` (golden fixtures);
  external: USDA eligibility worksheet.
- **Limitations:** Per Phase 2 D-PHASE2-Q5, unlisted counties FALL BACK to
  the default income limits (this is the USDA-published behavior, NOT a
  silent failure — intentionally asymmetric with FHFA/FHA missing-county
  semantics).
- **Last reviewed:** 2026-05-23

### `data/reference/irs-pub936.yml`
- **Pins:** Qualified-loan-limit caps under IRC §163(h)(3) /
  IRS Pub 936: post-2017 cap ($750k single/MFJ/HoH; $375k MFS), pre-2017
  grandfathered cap ($1M single/MFJ/HoH; $500k MFS), and the TCJA
  binding-contract grace-period date triggers (2017-12-15 / 2018-04-01).
- **Source:** https://www.irs.gov/pub/irs-pdf/p936.pdf
- **Effective:** 2025-01-01
- **Refresh command:** verify against the current-tax-year IRS Pub 936
  publication; edit caps if Congress amends §163(h)(3), bump `effective:`,
  commit.
- **Validation oracle:** `tests/test_rules/test_irs_pub936.py` (golden
  fixtures); external: IRS Pub 936 (Table 1 worksheet).
- **Limitations:** Effective date currently >12mo — StaleReferenceWarning
  WILL fire (refresh against tax-year-2026 publication when IRS posts it).
  Points deductibility (Pub 936 §3) explicitly OUT OF SCOPE for v1: that
  requires settlement-statement facts the predicate does not receive.
- **Last reviewed:** 2026-05-23

### `data/reference/fannie-llpa-matrix.yml`
- **Pins:** Fannie Mae LLPA matrix (Single-Family Selling Guide §B5-1):
  base credit-score x LTV bps table + loan-purpose / occupancy / unit-count
  add-ons + explicit credit-score / LTV bucket boundaries.
- **Source:** https://singlefamily.fanniemae.com/media/9391/display
- **Effective:** 2026-01-28
- **Refresh command:** re-extract matrix from Fannie's published PDF
  (quarterly cadence per Assumption A4), edit YAML body, bump `effective:`,
  commit. Per CONTEXT.md D-05, this YAML is implementation-detail under
  RUL-02 — NOT a new REF-ID.
- **Validation oracle:** `tests/test_rules/test_fannie_eligibility.py`
  (golden fixtures + boundary tests at 700/719/720/739/740);
  external: Fannie LLPA PDF.
- **Limitations:** Credit-score buckets are LOW-INCLUSIVE / HIGH-INCLUSIVE
  (e.g. 720-739 includes both 720 and 739); LTV buckets are HIGH-INCLUSIVE
  (e.g. 75.01-80.00 includes 80.00, excludes 75.00). LTV inputs must be
  quantized to at most 2 decimal places (predicate raises `ValueError`
  on >2-dp input).
- **Last reviewed:** 2026-05-23

### `data/reference/freddie-eligibility-matrix.yml`
- **Pins:** Freddie Mac eligibility + Credit Fee Cap matrix per Single-Family
  Seller/Servicer Guide §4203.4: eligibility flags per credit-score x LTV
  bucket + loan-purpose / occupancy / unit-count add-ons.
- **Source:** https://sf.freddiemac.com/working-with-us/origination-underwriting/eligibility-criteria
  (predicate docstring also cites https://guide.freddiemac.com/app/guide/section/4203.4)
- **Effective:** 2026-01-15
- **Refresh command:** re-extract matrix from Freddie's published source,
  edit YAML body, bump `effective:`, commit. Per CONTEXT.md D-05,
  implementation-detail under RUL-03 — NOT a new REF-ID.
- **Validation oracle:** `tests/test_rules/test_freddie_eligibility.py`
  (golden fixtures, including the deliberate overlay-diff cells at 620-639
  LTV>90 and entire below-620 row); external: Freddie SSG §4203.4.
- **Limitations:** Models PUBLISHED matrix only — does NOT replicate Freddie's
  proprietary LPA AUS decision. Same 2-decimal-place LTV quantization
  requirement as the Fannie matrix.
- **Last reviewed:** 2026-05-23

### `data/reference/atr-qm-thresholds.yml`
- **Pins:** ATR/QM General-QM + Safe-Harbor APR-APOR spread thresholds
  per 12 CFR §1026.43(e)(2) / §1026.43(b)(4): per (lien_position * loan-amount
  band) row carrying the 2026-indexed loan-amount tiers
  ($110,260 first-lien high; $66,156 first-lien mid / subordinate high) +
  threshold percentage points (2.25/3.5/6.5 General-QM; 1.5/3.5/6.5
  Safe-Harbor).
- **Source:** https://files.consumerfinance.gov/f/documents/cfpb_combined-reg-z-thresholds-adjustment-rule_2025-11.pdf
- **Effective:** 2025-11-01
- **Refresh command:** verify against the latest CFPB combined Reg Z
  thresholds adjustment publication (typically Q4 each year for the upcoming
  calendar year's tiers), edit the per-row loan-amount bounds, bump
  `effective:`, commit.
- **Validation oracle:** `tests/test_rules/test_atr_qm.py` (golden fixtures);
  external: CFPB combined Reg Z thresholds adjustment rule PDF.
- **Limitations:** YAML stores thresholds as PERCENTAGE POINTS; predicate
  divides by 100 at consumption to compare against fractional `apr - apor`.
  Loan-amount tier boundaries are inclusive-lower (`>=`) / exclusive-upper
  (`<`). Predicate does NOT enforce all-other ATR factors (income docs,
  reserves, etc.) — only the price-based test.
- **Last reviewed:** 2026-05-23

### `data/reference/insurance-estimate-defaults.yml`
- **Pins:** Composite homeowners-insurance fallback: 51-row state base
  premium (50 + DC), 5-row flood-zone multiplier (multiplicative), 3-row
  earthquake state add-on (additive flat $; CA, OR, WA).
- **Source:** https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022
  (state base; CA + TX from III state averages because NAIC excludes
  them — separately documented in per-row notes; flood multipliers from
  representative private-market carrier filings; CA quake from
  California Earthquake Authority; OR / WA from PNW private-market carrier
  surveys.)
- **Effective:** 2025-05-21 (NAIC report publication date)
- **Refresh command:** verify against the NEXT NAIC Homeowners Insurance
  Report republication; edit per-state base premium rows + per-row notes;
  bump `effective:`, commit.
- **Validation oracle:** `tests/test_rules/test_insurance.py` (golden
  fixtures including WA Pachulski baseline of $1,619.65/year); external:
  NAIC homeowners-insurance report.
- **Limitations:** NOT a regulatory predicate — heuristic. Every estimated
  value is flagged in reports via
  `INSURANCE-ESTIMATED-NAIC-{state}-{zone}` tags. Earthquake add-ons are
  flat $ approximating ~$500-700k coverage; high- or low-value homes will
  be systematically mispriced (D-16-INS-03 tradeoff). States outside
  CA/OR/WA silently get $0 quake. Effective >12mo — `StaleReferenceWarning`
  WILL fire (intentional).
- **Last reviewed:** 2026-05-23

### `data/reference/property-analysis-heuristics.yml`
- **Pins:** Abridged 4x4 MGIC Standard MI (BPMI) annual rate schedule —
  FICO bands {700-719, 720-739, 740-759, 760+} x LTV bands {80-85, 85-90,
  90-95, 95-97}, 16 cells.
- **Source:** https://www.mgic.com/rates/rate-cards
- **Effective:** 2024-03-04 (MGIC Rate Card "Standard MI" published bulletin)
- **Refresh command:** verify against the next MGIC bulletin republication;
  edit the per-cell `annual_rate` values, bump `effective:`, commit.
- **Validation oracle:** `tests/test_rules/test_pmi.py` (golden fixtures
  including worked example FICO=745 / LTV=0.92 → annual_rate 0.0035 and
  capped-fallback boundaries); external: MGIC Rate Card published bulletin
  (form 71-43345 series).
- **Limitations:** NOT a regulatory predicate — industry rate card. Reports
  flag every value via `PMI-RATE-ESTIMATED-MGIC-...` tags. Bucket convention
  is EXCLUSIVE-LOWER / INCLUSIVE-UPPER (no `ltv_min == 0.00` special-case,
  unlike `fha-mip-rates.yml`); LTV exactly 0.80 hits the capped-fallback
  row by design. Out-of-band combos (FICO<700, LTV>97, LTV<=80) return the
  worst cell with `PMI-RATE-CAPPED-MGIC-ABRIDGED-...` tag. Full MGIC 8x7
  schedule deferred to v2. Effective >12mo — `StaleReferenceWarning` WILL
  fire (intentional).
- **Last reviewed:** 2026-05-23

## Rule Predicates (13)

### `lib/rules/loan_type.py`
- **What it decides:** Given loan amount, county, program, and unit count,
  returns the `LoanType` enum identifying which loan tier applies
  (conforming / high-balance / jumbo / fha-floor / fha-ceiling / va / usda).
- **Citation:** 12 USC §1717 (FHFA conforming loan limit authority);
  NHA §203(b)(2) (FHA loan limits).
- **Source URL:** https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026
- **Effective:** 2026-01-01 (mirrors `conforming-limits-2026.yml`)
- **Validation oracle:** `tests/test_rules/test_loan_type.py` golden
  fixtures (including the `MissingCountyDataError` loud-fail path); external:
  FHFA news release.
- **Limitations:** Raises `MissingCountyDataError` if county data is
  required but missing (loud-fail per cfpb/jumbo-mortgage pattern).
  Raises `NotImplementedError` for unit_count > 1 (v1 supports 1-unit only),
  partial-entitlement VA, and FHA jumbo.
- **Last reviewed:** 2026-05-23

### `lib/rules/fha_mip.py`
- **What it decides:** Given a `Loan`, original property value, and FHA
  endorsement date, returns `MIPResult(ufmip, annual_mip_pct,
  terminates_at_period)`.
- **Citation:** HUD Handbook 4000.1 §II.A.8.b (annual MIP rate, ~0.55% post
  HUD ML 2023-05) + §II.A.8.q (termination rules — life-of-loan if LTV > 90%,
  132 months otherwise; codifies HUD ML 2013-04). Historical: HUD ML 2023-05,
  HUD ML 2013-04.
- **Source URL (operative):** https://www.hud.gov/sites/dfiles/OCHCO/documents/4000.1hsgh.pdf
  (Handbook 4000.1, Update 15, 2024-05)
- **Source URL (historical):** https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf
- **Effective:** 2023-03-20
- **Validation oracle:** `tests/test_rules/test_fha_mip.py` golden fixtures;
  external: HUD Handbook 4000.1 + HUD ML 2023-05 PDFs.
- **Limitations:** Endorsement dates before 2023-03-20 raise
  `NotImplementedError` (pre-HUD-ML-2023-05 rates deferred to v2). LTV > 1.00
  or `original_property_value <= 0` raise `ValueError`.
- **Last reviewed:** 2026-05-23

### `lib/rules/va_funding_fee.py`
- **What it decides:** Given loan amount, down-payment %, first-use flag,
  loan purpose, and exemption flag, returns the VA funding fee Decimal
  amount (quantized to cents).
- **Citation:** 38 USC §3729 (statutory authority); VA Lender Handbook M26-7
  Chapter 8 (current fee table).
- **Source URL:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf
- **Effective:** 2023-04-07
- **Validation oracle:** `tests/test_rules/test_va_funding_fee.py` golden
  fixtures; external: VA M26-7 Chapter 8 PDF.
- **Limitations:** `is_exempt=True` returns `Decimal("0.00")` without table
  lookup. Cash-out refi fees are flat (do NOT depend on down-payment;
  fixed by BL-02 02-REVIEW.md). IRRRL, manufactured-home-non-permanent,
  and loan-assumption are flat regardless of use-count / down-payment.
- **Last reviewed:** 2026-05-23

### `lib/rules/va_residual_income.py`
- **What it decides:** Given region, family size, loan amount, and actual
  residual income, returns `ResidualIncomeResult(status, minimum_required,
  actual, binding_rule_citation)`.
- **Citation:** VA Lender Handbook M26-7 Topic 7 (Residual Income).
- **Source URL:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/
- **Effective:** 2023-04-07
- **Validation oracle:** `tests/test_rules/test_va_residual_income.py`
  golden fixtures + binding-rule-citation format pin; external: VA M26-7
  Topic 7.
- **Limitations:** `family_size < 1` raises `ValueError`. Predicate emits a
  STABLE citation string format `VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}`
  that Phase 4 `blocked_by` reporting consumes — format drift breaks Phase 4.
- **Last reviewed:** 2026-05-23

### `lib/rules/usda.py`
- **What it decides:** Given household income, household size, county, and
  loan amount, returns `USDAEligibilityResult(income_eligible,
  applicable_income_limit, guarantee_fee_upfront, guarantee_fee_annual)`.
- **Citation:** 7 CFR Part 3555 (USDA RD SFH GLP) + 7 CFR §3555.107
  (guarantee fee).
- **Source URL:** https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do
- **Effective:** 2025-10-01
- **Validation oracle:** `tests/test_rules/test_usda.py` golden fixtures;
  external: USDA eligibility worksheet + 7 CFR §3555.
- **Limitations:** Per locked decision D-PHASE2-Q5, unlisted counties FALL
  BACK to default limits (does NOT raise `MissingCountyDataError`).
  Asymmetric with `loan_type.classify` by design — `usda.evaluate` asks
  "what is this county's limit?" where the default IS the answer for most
  counties.
- **Last reviewed:** 2026-05-23

### `lib/rules/irs_pub936.py`
- **What it decides:** Given filing status and grandfathering / binding-contract
  grace-period flags, returns the Decimal qualified loan limit cap.
- **Citation:** IRC §163(h)(3) as amended by TCJA 2017; IRS Pub 936 Table 1
  worksheet.
- **Source URL:** https://www.irs.gov/pub/irs-pdf/p936.pdf
- **Effective:** 2025-01-01
- **Validation oracle:** `tests/test_rules/test_irs_pub936.py` golden
  fixtures; external: IRS Pub 936 Table 1.
- **Limitations:** Predicate does NOT do date arithmetic — caller must
  supply the TWO booleans (`binding_contract_signed_before_2017_12_15` AND
  `_closed_before_2018_04_01`) because the TCJA grace period requires both
  dates and a single origination_date cannot capture them. Points
  deductibility (Pub 936 §3) explicitly OUT OF SCOPE for v1.
- **Last reviewed:** 2026-05-23

### `lib/rules/conventional_pmi.py`
- **What it decides:** Given a `Loan`, current scheduled balance, original
  property value, a high-risk flag, and (for high-risk) months elapsed,
  returns PMI status: `in_force` / `request_terminable` / `auto_terminated`
  / `high_risk_midpoint_terminated`.
- **Citation:** 12 USC §4901-4910 (Homeowners Protection Act of 1998),
  specifically §4902(a) (80% LTV borrower request), §4902(b) (78% LTV
  auto-termination), §4902(g) (high-risk midpoint carve-out).
- **Source URL:** https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/
  (also https://www.fdic.gov/consumer-compliance-examination-manual/v-5-homeowners-protection-act)
- **Effective:** 1999-07-29 (HPA original effective date; no material
  amendment since)
- **Validation oracle:** `tests/test_rules/test_conventional_pmi.py` golden
  fixtures (smoke covers LTV=0.78 → auto_terminated); external: HPA statute.
- **Limitations:** NO YAML — statutory constants 0.78 / 0.80 are
  `Final[Decimal]` module constants per D-02. LTV computed against
  ORIGINAL appraised value (HPA-mandated); re-appraisal-based cancellation
  out of scope for v1. `is_high_risk=True` with `months_elapsed=None`
  raises `ValueError` (loud).
- **Last reviewed:** 2026-05-23

### `lib/rules/fannie_eligibility.py`
- **What it decides:** Given credit score, LTV %, loan purpose, occupancy,
  and unit count, returns LLPA in basis points (negative = credit, positive
  = charge).
- **Citation:** Fannie Mae LLPA Matrix, Single-Family Selling Guide §B5-1.
- **Source URL:** https://singlefamily.fanniemae.com/media/9391/display
- **Effective:** 2026-01-28
- **Validation oracle:** `tests/test_rules/test_fannie_eligibility.py`
  golden fixtures + boundary tests; external: Fannie LLPA Matrix PDF.
- **Limitations:** Per CONTEXT.md D-04 full matrix shipped (no
  `NotImplementedError` branches). LTV input must be quantized to at most
  2 decimal places (predicate raises `ValueError` on >2-dp input — WR-03
  02-REVIEW.md).
- **Last reviewed:** 2026-05-23

### `lib/rules/freddie_eligibility.py`
- **What it decides:** Given credit score, LTV %, loan purpose, occupancy,
  and unit count, returns `FreddieEligibilityResult(eligible, credit_fee_bps)`.
- **Citation:** Freddie Mac Single-Family Seller/Servicer Guide §4203.4 +
  Credit Fee Cap matrix.
- **Source URL:** https://sf.freddiemac.com/working-with-us/origination-underwriting/eligibility-criteria
  (also https://guide.freddiemac.com/app/guide/section/4203.4)
- **Effective:** 2026-01-15
- **Validation oracle:** `tests/test_rules/test_freddie_eligibility.py`
  golden fixtures + the deliberate Freddie-vs-Fannie overlay-diff cells
  (620-639 LTV>90 and the entire below-620 row); external: Freddie SSG.
- **Limitations:** Models PUBLISHED matrix only — does NOT replicate
  Freddie's proprietary LPA AUS decision. Same 2-decimal-place LTV
  quantization requirement as Fannie.
- **Last reviewed:** 2026-05-23

### `lib/rules/atr_qm.py`
- **What it decides:** Given APR, APOR, loan amount, and lien position,
  returns True iff the loan passes the General-QM (or Safe-Harbor) price
  test. Two entry points: `general_qm_passes` and `safe_harbor_qm_passes`.
- **Citation:** 12 CFR §1026.43(e)(2) (General-QM) + §1026.43(b)(4)
  (Safe-Harbor) as amended by CFPB Dec 2020 final rule (mandatory
  compliance 2022-10-01).
- **Source URL:** https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition
- **Effective:** 2022-10-01
- **Validation oracle:** `tests/test_rules/test_atr_qm.py` golden fixtures
  (including loan-amount-tier boundary tests at $66,156 and $110,260);
  external: CFPB final rule + 12 CFR §1026.43.
- **Limitations:** Only the price-based test — predicate does NOT enforce
  other ATR factors (income, employment, debt obligations, reserves).
  Threshold-unit convention: YAML stores percentage points; predicate
  divides by 100 at consumption. Boundary comparison uses `<=` per Reg Z
  "does not exceed" language.
- **Last reviewed:** 2026-05-23

### `lib/rules/reg_z.py`
- **What it decides:** Given disclosed APR, actual APR, and an
  `is_irregular_transaction` flag, returns True iff
  `abs(disclosed - actual) <= applicable tolerance` (1/8 pp regular,
  1/4 pp irregular).
- **Citation:** 12 CFR §1026.22(a)(2) (regular) + §1026.22(a)(3) (irregular).
- **Source URL:** https://www.consumerfinance.gov/rules-policy/regulations/1026/22/
- **Effective:** 2010-09-30 (Reg Z text; no material amendment since)
- **Validation oracle:** `tests/test_rules/test_reg_z.py` golden fixtures +
  the `test_phase2_smoke.py::test_reg_z_within_tolerance_happy_path` boundary
  smoke; external: 12 CFR §1026.22.
- **Limitations:** NO YAML — statutory constants 0.00125 / 0.0025 are
  module-level `Final[Decimal]` per D-02. Predicate does NOT classify the
  transaction itself; caller must supply `is_irregular_transaction`.
  Decimal-only arithmetic; no float coercion (Pitfall 11).
- **Last reviewed:** 2026-05-23

### `lib/rules/pmi.py`
- **What it decides:** Given a representative FICO score and an LTV ratio,
  returns `PMILookupResult(annual_rate, reason_tag)` using the abridged 4x4
  MGIC schedule with worst-cell capped fallback for out-of-band combos.
- **Citation:** MGIC Rate Card "Standard MI" (industry-published rate card;
  NOT a regulatory predicate).
- **Source URL:** https://www.mgic.com/rates/rate-cards
- **Effective:** 2024-03-04
- **Validation oracle:** `tests/test_rules/test_pmi.py` golden fixtures
  (worked example FICO=745 / LTV=0.92 → 0.0035, plus boundary + capped-
  fallback cells); external: MGIC Rate Card published bulletin.
- **Limitations:** Industry heuristic — reports flag every value with
  `PMI-RATE-ESTIMATED-MGIC-...` or `PMI-RATE-CAPPED-MGIC-ABRIDGED-...`.
  Bucket convention EXCLUSIVE-LOWER / INCLUSIVE-UPPER; LTV exactly 0.80
  hits the capped fallback by design (consistent with the Phase 14 trigger
  `provisional_ltv > Decimal("0.80")`). Full MGIC 8x7 schedule deferred
  to v2.
- **Last reviewed:** 2026-05-23

### `lib/rules/insurance.py`
- **What it decides:** Given a USPS state code and an optional FEMA flood
  zone, returns the estimated annual homeowners insurance premium (Money)
  using `state_base * flood_zone_multiplier + earthquake_state_addon`.
- **Citation:** Composite — NAIC Homeowners Insurance Report (Data for
  2022, published 2025-05-21) for 49 covered states + DC; III state averages
  for CA + TX; private-market homeowners-policy flood-uplift heuristic
  (NOT FEMA NFIP — Risk Rating 2.0 decoupled NFIP from FIRM zone);
  CEA + PNW private-market averages for CA / OR / WA quake add-ons.
- **Source URL:** https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022
- **Effective:** 2025-05-21
- **Validation oracle:** `tests/test_rules/test_insurance.py` golden fixtures
  (WA Pachulski baseline $1,619.65/year worked example); external: NAIC
  homeowners-insurance report.
- **Limitations:** NOT a regulatory predicate — heuristic. Reports flag every
  estimated value via `INSURANCE-ESTIMATED-NAIC-{state}-{zone}`. In v1.1
  the caller always passes `flood_zone=None` (PropertyListing has no
  flood_zone field) so only the "unknown" multiplier row (1.15) ever fires.
  States outside CA/OR/WA silently receive $0 quake add-on. Earthquake
  flat-$ approximates ~$500-700k coverage; non-baseline home values are
  systematically mispriced (D-16-INS-03 tradeoff).
- **Last reviewed:** 2026-05-23

## Stale-warning current state

Snapshot of `data/reference/*.yml` files currently triggering
`StaleReferenceWarning` as of **2026-05-23** (12-month threshold:
**2025-05-23**). The pytest-default warning dedup hides some entries; the
authoritative scan is `uv run python` directly invoking `load_reference`
for each YAML.

`uv run pytest --timeout=60 -q 2>&1 | grep StaleReferenceWarning | sort -u`
output (pytest dedups; misses fha-mip-rates):

```
/Users/cujo253/Documents/mortgage-ops/lib/rules/_loader.py:86: StaleReferenceWarning: Reference data 'insurance-estimate-defaults' has effective=2025-05-21, which is more than 12 months old (threshold: 2025-05-23). Annual regulatory refresh may be overdue.
/Users/cujo253/Documents/mortgage-ops/lib/rules/_loader.py:86: StaleReferenceWarning: Reference data 'irs-pub936' has effective=2025-01-01, which is more than 12 months old (threshold: 2025-05-23). Annual regulatory refresh may be overdue.
/Users/cujo253/Documents/mortgage-ops/lib/rules/_loader.py:86: StaleReferenceWarning: Reference data 'property-analysis-heuristics' has effective=2024-03-04, which is more than 12 months old (threshold: 2025-05-23). Annual regulatory refresh may be overdue.
/Users/cujo253/Documents/mortgage-ops/lib/rules/_loader.py:86: StaleReferenceWarning: Reference data 'va-funding-fees' has effective=2023-04-07, which is more than 12 months old (threshold: 2025-05-23). Annual regulatory refresh may be overdue.
/Users/cujo253/Documents/mortgage-ops/lib/rules/_loader.py:86: StaleReferenceWarning: Reference data 'va-residual-income' has effective=2023-04-07, which is more than 12 months old (threshold: 2025-05-23). Annual regulatory refresh may be overdue.
```

Direct loader scan (every YAML, no dedup):

| YAML stem                       | effective    | stale (>12mo)? |
| ------------------------------- | ------------ | -------------- |
| conforming-limits-2026          | 2026-01-01   | no             |
| fha-limits-2026                 | 2026-01-01   | no             |
| fha-mip-rates                   | 2023-03-20   | **yes**        |
| va-funding-fees                 | 2023-04-07   | **yes**        |
| va-residual-income              | 2023-04-07   | **yes**        |
| usda-income-limits              | 2025-10-01   | no             |
| irs-pub936                      | 2025-01-01   | **yes**        |
| fannie-llpa-matrix              | 2026-01-28   | no             |
| freddie-eligibility-matrix      | 2026-01-15   | no             |
| atr-qm-thresholds               | 2025-11-01   | no             |
| insurance-estimate-defaults     | 2025-05-21   | **yes**        |
| property-analysis-heuristics    | 2024-03-04   | **yes**        |

Six YAMLs are currently stale: `fha-mip-rates`, `va-funding-fees`,
`va-residual-income`, `irs-pub936`, `insurance-estimate-defaults`,
`property-analysis-heuristics`. Per the YAML headers, the four
`va-*` / `fha-mip-rates` / `property-analysis-heuristics` /
`insurance-estimate-defaults` warnings are EXPECTED (the underlying source
has not republished) — re-verification, not necessarily content change, is
the refresh action. `irs-pub936` is the most likely candidate for a true
content refresh because IRS Pub 936 is republished annually. This ledger
DOCUMENTS state; a separate task (Phase 17 / #1) will FIX the stale YAMLs.
