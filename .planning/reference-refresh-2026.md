# Reference Data Refresh Audit — 2026

**Audit date:** 2026-05-23
**Auditor:** Claude (research-only; no YAML/code edits made)
**Scope:** 5 stale `data/reference/*.yml` files flagged by `StaleReferenceWarning`

## Headline summary

| File | Materiality | New effective date proposed |
|---|---|---|
| `irs-pub936.yml` | MATERIAL (legislative) — caps numerically unchanged, but cap structure is now PERMANENT per OBBBA + PMI deductibility restored for TY2026 | 2025-01-01 (Pub 936 2025 ed.) or 2026 on publication |
| `va-funding-fees.yml` | NO-CHANGE — schedule unchanged since 2023-04-07 by statute | 2023-04-07 (refresh `notes:` only; cosmetic re-verify) |
| `va-residual-income.yml` | NO-CHANGE — table unchanged; flag pre-existing per-extra-member bug (below-$80k tier should be $75, not $80) | 2023-04-07 (refresh `notes:` only; cosmetic re-verify) |
| `insurance-estimate-defaults.yml` | NO-CHANGE — NAIC 2022-data report (published 2025-05-21) is still the latest; no newer NAIC report exists | 2025-05-21 (cosmetic re-verify; no NAIC republication) |
| `property-analysis-heuristics.yml` | NEEDS-MANUAL-RESEARCH — MGIC's public rate-card PDF page is broken/404; current rates require authenticated MiQ access | 2024-03-04 (until MGIC bulletin obtained) |

---

## data/reference/irs-pub936.yml

**Current state:**
- `effective: 2025-01-01`
- `source: https://www.irs.gov/pub/irs-pdf/p936.pdf`
- Pinned values:
  - `caps.post_2017.single/mfj/hoh: "750000"` ; `mfs: "375000"` ; `effective_for_debt_after: 2017-12-15`
  - `caps.pre_2017_grandfathered.single/mfj/hoh: "1000000"` ; `mfs: "500000"` ; `effective_for_debt_on_or_before: 2017-12-15`
  - `binding_contract_grace_period.contract_signed_before: 2017-12-15` ; `close_before: 2018-04-01`

**Proposed update:**
- `effective: 2025-01-01` (Pub 936 for tax year 2025 — the most recent published edition; IRS Pub 936 for TY2026 will not publish until early 2027)
- `source:` unchanged — `https://www.irs.gov/pub/irs-pdf/p936.pdf` still resolves to the 2025 edition
- Pinned numeric values: **ALL UNCHANGED** (still $750k post-2017 / $1M pre-2017 / $375k & $500k MFS)
- **Notes section needs material update** to reflect:
  - **OBBBA Section 70108 (One Big Beautiful Bill Act, 2025)** permanently extended the IRC §163(h)(3) $750,000 acquisition-debt cap. Previously, the cap was scheduled to revert to $1,000,000 for tax years beginning after 2025-12-31 under the TCJA sunset. OBBBA removed the sunset.
  - **PMI premium deductibility** is restored for tax year 2026 onward, with AGI phase-out beginning at $100,000 ($50,000 MFS). This is OUT OF SCOPE for RUL-11 (same scope-deferral logic as points deductibility), but the `points_deductibility:` notes block should be updated to mention PMI deductibility alongside points as another deferred item.
  - Update the existing comment `"current edition is for tax year 2025"` to remain accurate and note that the OBBBA changes the policy framing without changing pinned values.

**Materiality:** MATERIAL (legislative framing change; numeric values unchanged)
**Source quality:** PRIMARY (IRS.gov)
**Risk flags:**
- IRS has NOT yet published a 2026-edition Pub 936; the 2025 edition remains the current authoritative document as of 2026-05-23. Last review/update timestamp on `https://www.irs.gov/forms-pubs/about-publication-936` is 2026-03-30.
- A correction notice dated 2025-12-05 affects Worksheet line 2 for TY2020-2024 (not the cap table) — out of scope for this YAML.
- Once IRS publishes the 2026 edition (typically Jan-Mar 2027), re-verify whether any acquisition-debt-cap language changed. OBBBA-permanence framing means the cap is now statutory rather than sunset-pending — expect Pub 936 (2026) to drop the "post-2025 reversion" caveats.

**Verification recipe:**
```
curl -sI https://www.irs.gov/pub/irs-pdf/p936.pdf | grep -i 'last-modified'
# Confirm Pub 936 edition by fetching first page; look for "For use in preparing 2025 Returns"
```
Compare cap dollar values against `legalclarity.org` and Tax Foundation summaries for sanity.

**Sources consulted:**
- https://www.irs.gov/publications/p936 (HTML, 2025 edition)
- https://www.irs.gov/forms-pubs/about-publication-936 (last reviewed 2026-03-30)
- https://www.tgccpa.com/interest-expense-updates-from-the-one-big-beautiful-bill-act/ (OBBBA §70108 permanent extension)
- https://www.hrblock.com/tax-center/irs/tax-law-and-policy/one-big-beautiful-bill-salt-deduction/ (PMI deductibility restoration)

---

## data/reference/va-funding-fees.yml

**Current state:**
- `effective: 2023-04-07`
- `source: https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf`
- Pinned values:
  - `purchase`: 0..<5 → first-use 2.15% / subsequent 3.30%; 5..<10 → 1.50% / 1.50%; >=10 → 1.25% / 1.25%
  - `flat_fees.irrrl: 0.50%` ; `manufactured_home_non_permanent: 1.00%` ; `loan_assumption: 0.50%` ; `cash_out_first_use: 2.15%` ; `cash_out_subsequent_use: 3.30%`
  - `exemption.va_disability_compensation_recipient: true`

**Proposed update:**
- `effective: 2023-04-07` — **UNCHANGED.** The Blue Water Navy Vietnam Veterans Act schedule that took effect 2023-04-07 explicitly governs through 2026. Verified at va.gov: "The current rates took effect April 7, 2023, and remain unchanged for 2026."
- `source:` unchanged. The VA.gov "Funding fee and closing costs" landing page (`https://www.va.gov/housing-assistance/home-loans/funding-fee-and-closing-costs/`) shows the same fee table with a page last-updated 2026-01-15 but the schedule still references the 2023-04-07 effective date.
- Pinned numeric values: **ALL UNCHANGED.**
- Refresh the `notes:` block to extend the "Re-verify annually that no new VA Circular has changed these rates" comment with a dated audit stamp: "Re-verified 2026-05-23 against va.gov (last updated 2026-01-15) — no change."

**Materiality:** NO-CHANGE (cosmetic refresh of `notes:` re-verification timestamp only; an `effective:` field bump to 2026-05-23 would be **semantically wrong** because the underlying VA rule has not been re-enacted on that date)
**Source quality:** PRIMARY (va.gov + WARMS)
**Risk flags:**
- The WARMS PDF URLs now redirect to a JavaScript-gated KnowVA portal (`knowva.ebenefits.va.gov`), which blocks WebFetch. The PDF itself still exists; the static legacy URL is what's cited. If automated fetching is added later, expect the redirect.
- The VA.gov funding fee page does NOT publish a separate 5-9.99% band — it uses ">= 5%" — but the YAML's exclusive-upper-bound convention `5..<10` is consistent with M26-7 Chapter 8 internal table semantics.
- **Statutory reset risk:** §3729 fee rates are written into statute by Congress. Watch for any new VA Circular or legislative change (e.g., a successor to the Blue Water Navy Vietnam Veterans Act) that re-tables these. As of 2026-05-23 none exists.

**Verification recipe:**
```
# Direct VA.gov page (works without JS)
WebFetch https://www.va.gov/housing-assistance/home-loans/funding-fee-and-closing-costs/
# Cross-check with veteransunited or valoannetwork tertiary summary for sanity
```

**Sources consulted:**
- https://www.va.gov/housing-assistance/home-loans/funding-fee-and-closing-costs/ (PRIMARY — page last updated 2026-01-15; schedule effective 2023-04-07)
- https://valoannetwork.com/va-funding-fee-changes-2026/ ("rates took effect April 7, 2023, and remain unchanged for 2026")
- https://www.veteransunited.com/valoans/va-funding-fee/ (corroborates same table)

---

## data/reference/va-residual-income.yml

**Current state:**
- `effective: 2023-04-07`
- `source: https://benefits.va.gov/WARMS/docs/admin26/m26-07/`
- Pinned values:
  - `regions: [northeast, midwest, south, west]`
  - `loan_band_threshold: "80000"`
  - `per_extra_member_increment: "80"` (single field, applies to both tiers)
  - `table_above_80k`: 4 regions × family sizes 1-5 (e.g., NE-4 = 1025, S-4 = 1003, W-4 = 1117)
  - `table_below_80k`: 4 regions × family sizes 1-5 (e.g., NE-4 = 888, S-4 = 868, W-4 = 967)

**Proposed update:**
- `effective: 2023-04-07` — **UNCHANGED.** Chapter 4 was revised 2023-11-21 (effective 2024-01-01) but the revision was scoped to medical-collections handling (see Topic 7 / TENA notice); the residual income table itself was NOT changed. The 2026 third-party charts (veteran.com, veteransunited.com, valoannetwork.com) all reproduce the EXACT same numeric table as the YAML.
- `source:` unchanged.
- Pinned numeric values in `table_above_80k` and `table_below_80k`: **ALL UNCHANGED** — verified row-by-row against veteran.com 2026 chart:
  - NE: 450 / 755 / 909 / 1025 / 1062 (matches)
  - MW: 441 / 738 / 889 / 1003 / 1039 (matches)
  - S: 441 / 738 / 889 / 1003 / 1039 (matches)
  - W: 491 / 823 / 990 / 1117 / 1158 (matches)
  - Below-$80k tier numbers also match exactly.

**PRE-EXISTING BUG TO FLAG (not a 2026 source change):**
- The YAML defines a single `per_extra_member_increment: "80"`. Authoritative VA M26-7 publishes TWO increments: **$75 for loans below $80,000** and **$80 for loans at $80,000 and above** (confirmed by veteran.com 2026 chart and veteransunited.com). The single-value YAML schema silently overstates the requirement for below-$80k loans by $5 per additional family member beyond 5.
- This is a Phase 2/Phase 4 modeling defect — NOT a 2026 source change. Flagging here so it can be triaged separately (probably a new rule like `per_extra_member_increment_below_80k: "75"` / `per_extra_member_increment_above_80k: "80"`). Predicate AFFD-07 in Phase 4 would need a schema bump; the citation-stable `binding_rule_citation` format probably does not need to change.

**Materiality:** NO-CHANGE for the 2026 refresh itself (cosmetic re-verify only). **Pre-existing schema defect** flagged separately as MATERIAL but out of scope for an annual refresh.
**Source quality:** PRIMARY (VA M26-7 Chapter 4, Topic 7) for the table values; SECONDARY (third-party VA-lender sites) for the 2026 confirmation since the primary WARMS PDFs are now JS-gated.
**Risk flags:**
- Verify the $75 vs $80 increment defect by reading M26-7 Chapter 4 Topic 7 directly once a non-JS PDF mirror is found, before changing schema.
- VA's KnowVA portal is JS-gated; consider archiving a static copy of M26-7 Chapter 4 to `references/` so future audits can re-verify without depending on third parties.
- Veteran.com claims "Add $80 per person" for above-$80k tier and "Add $75 per person" for below-$80k tier; veteransunited.com agrees.

**Verification recipe:**
```
# 2026 third-party chart confirms unchanged
WebFetch https://veteran.com/va-residual-income/
WebFetch https://www.veteransunited.com/valoans/explaining-the-vas-standard-for-residual-income/
# To verify the $75 vs $80 increment defect, look for an archived M26-7 Ch 4 PDF
```

**Sources consulted:**
- https://veteran.com/va-residual-income/ (full 2026 chart, both tiers, both increments)
- https://valoannetwork.com/va-residual-income-chart/ (2026 chart — confirms above-$80k tier; uses $80 increment + a single all-regions row for below-$80k that uses $75)
- https://www.tenaco.com/va-revises-chapter-4-of-lenders-handbook-m26-7/ (2023-11-21 Ch 4 revision; medical collections only; residual income unchanged)

---

## data/reference/insurance-estimate-defaults.yml

**Current state:**
- `effective: 2025-05-21`
- `source: https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022`
- Pinned values:
  - `state_base_annual_premium`: 51 rows (49 NAIC 2022 + CA $1480 III + TX $2641 III)
  - `flood_zone_multipliers`: 5 rows (X=1.00, A=1.30, AE=1.30, V=1.80, unknown=1.15)
  - `earthquake_state_addons`: 3 rows (CA=$850, OR=$200, WA=$250)

**Proposed update:**
- `effective: 2025-05-21` — **UNCHANGED.** Verified at content.naic.org: the most recently published NAIC report is still "Dwelling Fire, Homeowners Owner-Occupied, and Homeowners Tenant and Condominium/Cooperative Unit Owner's Insurance Report: **Data for 2022**, published **2025-05-21**". The 2026 Homeowners Market Data Call (per NAIC publications page) has a submission deadline of 2026-06-15 covering policy years 2018-2025; the resulting report will not be published until 2027 at the earliest.
- `source:` unchanged.
- Pinned numeric values: **ALL UNCHANGED from NAIC source** (same 2022-data underlying the existing YAML).
- Re-verify the III-sourced CA + TX values once III republishes its state-by-state breakdown. As of 2026-05-23 III's current page (`iii.org/fact-statistic/facts-statistics-homeowners-and-renters-insurance`) still cites NAIC 2022 data and shows CA=$1,492 and TX=$2,397. These differ slightly from the YAML's CA=$1,480 and TX=$2,641 — the deltas are likely:
  - CA: $1,480 (YAML) vs $1,492 (III current) — $12 difference, probably a different policy-form mix or rounding. **COSMETIC; ≤1% drift.**
  - TX: $2,641 (YAML) vs $2,397 (III current) — $244 difference, ~9%. **POTENTIALLY MATERIAL** — investigate whether the original YAML used a Texas Department of Insurance figure rather than the III table.

**Refresh the `notes:` re-verification timestamp** to record the 2026-05-23 audit and document that NAIC has not republished.

**Materiality:** NO-CHANGE for NAIC primary data. **POTENTIAL MATERIAL drift** on TX (III secondary) — flagged for manual review, may be a source-of-record question (TDI vs III).
**Source quality:** PRIMARY (NAIC) for 49 states; SECONDARY (III state-DOI table) for CA + TX.
**Risk flags:**
- The flood-zone multipliers and earthquake-state addons are explicitly heuristic (per YAML notes — RESEARCH Pitfall 6/7); they are not citable to a single primary source and do not need annual refresh.
- If the TX figure was originally sourced from a TDI publication rather than III, the citation note `"III state-DOI table — NAIC 2022 excludes TX"` is misleading. Spot-check the original Phase 16-01 PR for the source.
- Florida insurance market is volatile; the YAML's FL=$2,625 may already be conservative. Insurify's 2026 estimate-engine number is $5,796 (for $300k dwelling) — but that's a different methodology and not directly comparable to NAIC HO-3 average.

**Verification recipe:**
```
WebFetch https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022
# Confirm: report title still references "Data for 2022, published 2025-05-21"
WebFetch https://www.iii.org/fact-statistic/facts-statistics-homeowners-and-renters-insurance
# Spot-check CA + TX state averages
```

**Sources consulted:**
- https://content.naic.org/article/naic-releases-homeowners-insurance-report-2022 (PRIMARY — title confirms "Data for 2022, published 2025-05-21"; same as YAML)
- https://www.iii.org/fact-statistic/facts-statistics-homeowners-and-renters-insurance (III — CA=$1,492, TX=$2,397, FL=$2,677 per NAIC 2022 data)
- https://content.naic.org/publications (no newer report posted; 2026 Market Data Call due 2026-06-15)

---

## data/reference/property-analysis-heuristics.yml

(File name is misleading — this is actually the MGIC PMI rate-card YAML used by `lib/rules/pmi.py`.)

**Current state:**
- `effective: 2024-03-04`
- `source: https://www.mgic.com/rates/rate-cards`
- Pinned values:
  - `pmi_annual_rate_table`: 16-row 4×4 abridged subset (FICO 760+, 740-759, 720-739, 700-719) × (LTV 80-85, 85-90, 90-95, 95-97)
  - `pmi_capped_fallback.annual_rate: "0.0078"` (FICO 700-719 × LTV 95-97)

**Proposed update:**
- `effective: 2024-03-04` — **UNVERIFIED.** MGIC's public rates page (`https://www.mgic.com/rates/rate-cards`) no longer publishes a static "Standard MI" rate card PDF for direct download. The page redirects users to the authenticated MiQ rate-quote platform (`https://miq.mgic.com/miq/`) for current pricing. The legacy PDF (`71-61284-rate-card-pdf-bpmi-monthly-july-2018.pdf`) is archived but unreachable (404).
- `source:` may need to change to either (a) the MiQ login page with a stated 2025-or-later snapshot date, or (b) an MGIC Bulletin URL once obtained.
- Pinned numeric values: **CANNOT BE VERIFIED FROM PUBLIC WEB.**

**Materiality:** **NEEDS-MANUAL-RESEARCH.** Cannot confidently confirm or update the 4×4 rate matrix without one of:
  1. Direct authenticated MiQ access (user has lender credentials), OR
  2. A current MGIC Bulletin PDF URL (recent ones found in search but not directly accessible):
     - **MGIC Bulletin #04-2025** — 2026 Agency loan-limit alignment, effective 2025-11-26
     - **MGIC Bulletin #05-2025** — Underwriting Guideline update, effective 2026-01-22
     - **MGIC Bulletin #01-2025** — Underwriting Guideline update, effective 2025-06-25
     - None of the above bulletins are confirmed to change PMI rates — they may be underwriting-only.
  3. A current Enact/Radian/Arch/Essent/National MI rate-card cross-check for sanity.

**Source quality:** PRIMARY (MGIC bulletin) target, but currently inaccessible from public web in 2026; SECONDARY would require a third-party rate-quote engine snapshot.
**Risk flags:**
- The current YAML values are 2024-03-04 vintage. MGIC has issued at least three bulletins in 2025; whether any of them changed BPMI monthly rates is unknown. If MGIC re-priced post-LLPA-Matrix-2023 or in response to 2025 reinsurance cost shifts, the 4×4 subset could be materially stale.
- Phase 16-01 explicitly designed this YAML to be a "industry-published rate card; NOT a regulatory predicate" and the predicate emits `PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}` reason tags. So a stale rate card produces estimates flagged as estimates — limited blast radius, but **users will see numbers that look authoritative**.
- **Recommend: do not refresh `effective:` without obtaining a current MGIC bulletin.** Bumping the date without a source change creates false confidence.

**Verification recipe:**
```
# Option A: User logs into MiQ and runs a representative quote
# Option B: Fetch MGIC bulletin PDFs once URLs are known
# Option C: Cross-check against Enact Rate360 (https://enactmi.com/Rate360) for same FICO/LTV cells
```

**Sources consulted (largely unsuccessful):**
- https://www.mgic.com/rates/rate-cards (PRIMARY landing page; no public PDF download for Standard MI)
- https://www.mgic.com/rates/mi-premium-plans (lists premium plans; no rates)
- https://www.mgic.com/-/media/mi/rates/rate-cards/71-61284-rate-card-pdf-bpmi-monthly-july-2018.pdf (404)
- https://www.mgic.com/underwriting/underwriting-and-rate-changes (lists bulletins but does not show rate content publicly)

---

## Cross-cutting observations

1. **VA WARMS legacy PDF URLs all redirect to a JavaScript-gated KnowVA portal.** Three of the five files (`va-funding-fees`, `va-residual-income`, plus any other future VA citations) will fail automated re-verification through the `source:` URLs as currently pinned. Recommend either:
   - Mirroring the source PDFs into `references/` and pinning a local-path note, OR
   - Updating `source:` to the public-facing `va.gov` consumer page (which is JS-light and WebFetch-friendly) and keeping the WARMS PDF as a secondary reference.

2. **No 2026 IRS Pub 936 yet.** IRS Pub 936 is published Jan-Mar of the year following the tax year (so the TY2026 edition will land ~Q1 2027). Until then, the 2025 edition + OBBBA legislative notes are the authoritative pairing.

3. **NAIC Homeowners Insurance Report cadence is roughly annual but lags ~3 years.** The 2022-data report was published 2025-05-21; the 2026 Market Data Call (covering 2018-2025 policy years) is due 2026-06-15, which means a 2026 publication is plausible but not guaranteed. Re-check NAIC publications quarterly.

4. **MGIC rate cards are no longer publicly downloadable as PDFs.** Phase 16-01's "industry-published rate card" assumption is now load-bearing on either MGIC bulletin access or MiQ login. The portability of `data/reference/property-analysis-heuristics.yml` (which is really a PMI rate card) is degraded.

5. **`per_extra_member_increment` bug in `va-residual-income.yml`** is real and pre-existing; needs schema split into below-$80k ($75) and above-$80k ($80) increments. Flagging here for separate triage.

---

## data/reference/property-analysis-heuristics.yml — Manual research follow-up

**Follow-up date:** 2026-05-23
**Trigger:** Prior research pass flagged this file as `NEEDS-MANUAL-RESEARCH` because MGIC's abridged BPMI rate-card PDF subset moved behind MiQ authentication. This section documents a public-source substitute analysis using Arch MI, Enact MI, and Essent Guaranty rate cards.

### 1. Current YAML state (verbatim summary)

- `source: https://www.mgic.com/rates/rate-cards`
- `effective: 2024-03-04`
- Schema: `pmi_annual_rate_table` (16 rows = 4 FICO bands × 4 LTV bands) + `pmi_capped_fallback` (single worst-cell row)
- Boundary convention: EXCLUSIVE-LOWER / INCLUSIVE-UPPER on both FICO and LTV
- All scalars QUOTED strings (Decimal-from-string at boundary)
- Pinned values (annual rate as decimal):

  | FICO band | LTV 80-85 | LTV 85-90 | LTV 90-95 | LTV 95-97 |
  |---|---|---|---|---|
  | 760+ | 0.0019 | 0.0023 | 0.0028 | 0.0034 |
  | 740-759 | 0.0023 | 0.0028 | 0.0035 | 0.0046 |
  | 720-739 | 0.0028 | 0.0037 | 0.0048 | 0.0061 |
  | 700-719 | 0.0033 | 0.0046 | 0.0059 | **0.0078** (capped fallback) |

### 2. Sources consulted

| Vendor | URL | Rate-card revision date | Accessibility |
|---|---|---|---|
| **Arch MI** (PRIMARY) | https://mortgage.archgroup.com/wp-content/uploads/sites/4/MCUS-B0283B-AMI-BP-Monthly-FICO-Rate-Card.pdf | **Effective Feb. 9, 2026** | PUBLIC PDF (downloaded + pdftotext-extracted) |
| **Enact MI** (PRIMARY) | https://content.enactmi.com/documents/rate-cards/2025/00460.NationalMonthly.FIXED.0725.pdf | **Effective June 22, 2023; updated July 17, 2025** | PUBLIC PDF (downloaded + pdftotext-extracted) |
| **Essent Guaranty** (SECONDARY — stale) | https://www.essent.us/sites/default/files/bpmi-lpmi-monthly-premium-rate-card-02-11-19.pdf | Effective Feb. 11, 2019 (Essent's archive library publishes no card newer than 2019; current pricing is via `ratefinder.essent.us` login-only) | PUBLIC PDF but stale; useful as a historical pin showing identical filed rates back to 2019 |
| **National MI** (SECONDARY) | https://www.nationalmi.com/wp-content/uploads/2022/02/MA.MN_.BP_.2022-03.pdf | Effective Mar. 1, 2022 | PUBLIC PDF (extracted; matches Enact/Arch standard-coverage rows) |
| **MGIC** (TARGET — inaccessible) | https://www.mgic.com/rates/rate-cards | Page redirects to MiQ (login wall); no public BPMI Monthly PDF | LOGIN WALL — only the Credit Union archive PDF (Effective Dec. 4, 2017) is still publicly reachable for reference |
| **MGIC bulletin index** (CROSS-CHECK) | https://www.mgic.com/underwriting/underwriting-and-rate-changes | n/a | PUBLIC LISTING — no 2025 bulletin announces a BPMI rate change (all 5 are underwriting/loan-limit only). Strong signal MGIC's filed BPMI schedule has not moved since 2024-03-04. |
| **Freddie Mac LLPA matrix** (cross-check) | https://sf.freddiemac.com/docs/pdf/exhibit/19/exhibit_19.pdf | n/a | 404 — exhibit URL is dead (LLPAs were repealed/restructured by FHFA in 2023). Cross-check via LLPA cell rates is not viable. |

### 3. Cross-source comparison table

PMI rate-card industry-standard mapping: standard Fannie/Freddie coverage requirements are:
- LTV 80.01-85% → 12% coverage
- LTV 85.01-90% → 25% coverage
- LTV 90.01-95% → 25% coverage
- LTV 95.01-97% → 25% coverage

For each FICO band the cross-source FIXED-RATE / Amortization > 20 years / Standard Fannie Mae/Freddie Mac Coverage cells are **identical across Arch MI (eff. 2026-02-09), Enact MI (eff. 2023-06-22 updated 2025-07-17), Essent (eff. 2019-02-11), and National MI (eff. 2022-03-01)**. This is filed-rate convergence — the four major MIs file effectively the same posted schedule with state-by-state regulatory approval, and the structure has been stable across 7 years.

**2026 INDUSTRY-STANDARD cells (Arch/Enact/Essent/National MI all agree on these annualized BPMI percentages):**

| FICO band | LTV 80.01-85 (12% cov) | LTV 85.01-90 (25% cov) | LTV 90.01-95 (25% cov) | LTV 95.01-97 (25% cov) |
|---|---|---|---|---|
| 760+ | **0.19%** | **0.28%** | **0.34%** | **0.46%** |
| 740-759 | **0.20%** | **0.38%** | **0.48%** | **0.58%** |
| 720-739 | **0.23%** | **0.46%** | **0.59%** | **0.70%** |
| 700-719 | **0.25%** | **0.55%** | **0.68%** | **0.79%** |

**Vendor disagreement check:** All four vendors publish IDENTICAL cells (≤ 0bps drift) for every cell in the 4×4 grid above. Confidence is HIGH.

**Comparison vs. current YAML:**

| Cell | YAML (2024-03-04) | 2026 industry-standard cross-source | Δ (bps) |
|---|---|---|---|
| 760+ × 80-85 | 0.0019 | 0.0019 | 0 (match) |
| 760+ × 85-90 | 0.0023 | 0.0028 | **+5** |
| 760+ × 90-95 | 0.0028 | 0.0034 | **+6** |
| 760+ × 95-97 | 0.0034 | 0.0046 | **+12** ⚠ |
| 740-759 × 80-85 | 0.0023 | 0.0020 | -3 |
| 740-759 × 85-90 | 0.0028 | 0.0038 | **+10** ⚠ |
| 740-759 × 90-95 | 0.0035 | 0.0048 | **+13** ⚠ |
| 740-759 × 95-97 | 0.0046 | 0.0058 | **+12** ⚠ |
| 720-739 × 80-85 | 0.0028 | 0.0023 | -5 |
| 720-739 × 85-90 | 0.0037 | 0.0046 | **+9** |
| 720-739 × 90-95 | 0.0048 | 0.0059 | **+11** ⚠ |
| 720-739 × 95-97 | 0.0061 | 0.0070 | **+9** |
| 700-719 × 80-85 | 0.0033 | 0.0025 | **-8** |
| 700-719 × 85-90 | 0.0046 | 0.0055 | **+9** |
| 700-719 × 90-95 | 0.0059 | 0.0068 | **+9** |
| 700-719 × 95-97 (worst-cell / capped fallback) | 0.0078 | 0.0079 | +1 (effectively match) |

**Pattern observation:** The current YAML's 80-85 column (12% coverage) and the worst-cell value (700-719 × 95-97 = 0.0078) are effectively correct (within 1bps) against 2026 cards — but the **interior 85-90, 90-95, and 95-97 columns are systematically UNDER-stated by 9-13bps** relative to current 25%-coverage filed rates. This is too large to be rounding; it suggests the original 2024 YAML may have used a **mix of coverage levels** (e.g., 25% for 85-90 but 18% for 90-95 / 95-97) rather than the strict Fannie/Freddie standard 25% coverage requirement. The mismatch is NOT explained by a rate-card revision between 2024 and 2026 — Arch's 2026-02-09 standard-coverage cells are pixel-identical to Essent's 2019-02-11 standard-coverage cells. The four-MI filed schedule has been stable, so the current YAML appears to have been **mis-sourced** rather than stale.

### 4. Proposed YAML diff

Below is the proposed patch (NOT APPLIED — research-only). The diff replaces the under-stated interior cells with the 2026 industry-standard 25%-coverage cells while keeping the capped-fallback worst-cell anchor and the boundary convention unchanged.

```diff
--- a/data/reference/property-analysis-heuristics.yml
+++ b/data/reference/property-analysis-heuristics.yml
@@
-source: "https://www.mgic.com/rates/rate-cards"
-effective: 2024-03-04
+source: "https://mortgage.archgroup.com/wp-content/uploads/sites/4/MCUS-B0283B-AMI-BP-Monthly-FICO-Rate-Card.pdf"
+# Cross-verified against:
+#   - https://content.enactmi.com/documents/rate-cards/2025/00460.NationalMonthly.FIXED.0725.pdf (eff. 2023-06-22, updated 2025-07-17)
+#   - https://www.essent.us/sites/default/files/bpmi-lpmi-monthly-premium-rate-card-02-11-19.pdf (eff. 2019-02-11; stable filed-rate match)
+#   - https://www.nationalmi.com/wp-content/uploads/2022/02/MA.MN_.BP_.2022-03.pdf (eff. 2022-03-01)
+# Substitute for MGIC's no-longer-public BPMI Monthly PDF (page now redirects to MiQ auth).
+# Filed-rate convergence: all four MIs publish IDENTICAL standard-coverage BPMI cells.
+effective: 2026-02-09
 notes: |
-  MGIC Rate Card "Standard MI" (Borrower-Paid Monthly Premium) — abridged 4x4
-  BPMI rate schedule per CONTEXT D-16-PMI-01. Industry-published rate card;
+  Arch MI Borrower-Paid Monthly Non-Refundable Annualized BPMI Rate Card —
+  abridged 4x4 BPMI subset per CONTEXT D-16-PMI-01. Industry-published rate card;
   NOT a regulatory predicate. Reports flag every PMI value as estimate via
-  `PMI-RATE-ESTIMATED-MGIC-{ltv_band}-{fico_band}` in `eligible_reasons`.
+  `PMI-RATE-ESTIMATED-MI-{ltv_band}-{fico_band}` in `eligible_reasons`.
   ...
+  Source pinning: Arch MI Rate Card (MCUS-B0283B-AMI), Effective Feb. 9, 2026,
+  "Borrower-Paid Monthly, Non-Refundable Annualized BPMI Rates, Amortization
+  Term > 20 Years, Fixed". Cells correspond to standard Fannie/Freddie coverage
+  (12% for LTV 85.00 & below; 25% for LTV 85.01-97.00). Cross-verified vendors
+  publish identical filed rates back to Essent 2019-02-11.
 pmi_annual_rate_table:
   # FICO 760+ row
-  - {fico_min: "760", fico_max: "850", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0019", fico_band_label: "760+", ltv_band_label: "80-85"}
-  - {fico_min: "760", fico_max: "850", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0023", fico_band_label: "760+", ltv_band_label: "85-90"}
-  - {fico_min: "760", fico_max: "850", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0028", fico_band_label: "760+", ltv_band_label: "90-95"}
-  - {fico_min: "760", fico_max: "850", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0034", fico_band_label: "760+", ltv_band_label: "95-97"}
+  - {fico_min: "760", fico_max: "850", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0019", fico_band_label: "760+", ltv_band_label: "80-85"}
+  - {fico_min: "760", fico_max: "850", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0028", fico_band_label: "760+", ltv_band_label: "85-90"}
+  - {fico_min: "760", fico_max: "850", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0034", fico_band_label: "760+", ltv_band_label: "90-95"}
+  - {fico_min: "760", fico_max: "850", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0046", fico_band_label: "760+", ltv_band_label: "95-97"}
   # FICO 740-759 row
-  - {fico_min: "740", fico_max: "759", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0023", fico_band_label: "740-759", ltv_band_label: "80-85"}
-  - {fico_min: "740", fico_max: "759", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0028", fico_band_label: "740-759", ltv_band_label: "85-90"}
-  - {fico_min: "740", fico_max: "759", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0035", fico_band_label: "740-759", ltv_band_label: "90-95"}
-  - {fico_min: "740", fico_max: "759", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0046", fico_band_label: "740-759", ltv_band_label: "95-97"}
+  - {fico_min: "740", fico_max: "759", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0020", fico_band_label: "740-759", ltv_band_label: "80-85"}
+  - {fico_min: "740", fico_max: "759", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0038", fico_band_label: "740-759", ltv_band_label: "85-90"}
+  - {fico_min: "740", fico_max: "759", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0048", fico_band_label: "740-759", ltv_band_label: "90-95"}
+  - {fico_min: "740", fico_max: "759", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0058", fico_band_label: "740-759", ltv_band_label: "95-97"}
   # FICO 720-739 row
-  - {fico_min: "720", fico_max: "739", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0028", fico_band_label: "720-739", ltv_band_label: "80-85"}
-  - {fico_min: "720", fico_max: "739", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0037", fico_band_label: "720-739", ltv_band_label: "85-90"}
-  - {fico_min: "720", fico_max: "739", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0048", fico_band_label: "720-739", ltv_band_label: "90-95"}
-  - {fico_min: "720", fico_max: "739", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0061", fico_band_label: "720-739", ltv_band_label: "95-97"}
+  - {fico_min: "720", fico_max: "739", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0023", fico_band_label: "720-739", ltv_band_label: "80-85"}
+  - {fico_min: "720", fico_max: "739", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0046", fico_band_label: "720-739", ltv_band_label: "85-90"}
+  - {fico_min: "720", fico_max: "739", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0059", fico_band_label: "720-739", ltv_band_label: "90-95"}
+  - {fico_min: "720", fico_max: "739", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0070", fico_band_label: "720-739", ltv_band_label: "95-97"}
   # FICO 700-719 row
-  - {fico_min: "700", fico_max: "719", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0033", fico_band_label: "700-719", ltv_band_label: "80-85"}
-  - {fico_min: "700", fico_max: "719", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0046", fico_band_label: "700-719", ltv_band_label: "85-90"}
-  - {fico_min: "700", fico_max: "719", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0059", fico_band_label: "700-719", ltv_band_label: "90-95"}
-  - {fico_min: "700", fico_max: "719", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0078", fico_band_label: "700-719", ltv_band_label: "95-97"}
+  - {fico_min: "700", fico_max: "719", ltv_min: "0.80", ltv_max: "0.85", annual_rate: "0.0025", fico_band_label: "700-719", ltv_band_label: "80-85"}
+  - {fico_min: "700", fico_max: "719", ltv_min: "0.85", ltv_max: "0.90", annual_rate: "0.0055", fico_band_label: "700-719", ltv_band_label: "85-90"}
+  - {fico_min: "700", fico_max: "719", ltv_min: "0.90", ltv_max: "0.95", annual_rate: "0.0068", fico_band_label: "700-719", ltv_band_label: "90-95"}
+  - {fico_min: "700", fico_max: "719", ltv_min: "0.95", ltv_max: "0.97", annual_rate: "0.0079", fico_band_label: "700-719", ltv_band_label: "95-97"}
 pmi_capped_fallback:
-  annual_rate: "0.0078"
+  annual_rate: "0.0079"
   fico_band_label: "700-719"
   ltv_band_label: "95-97"
```

**Notes on the proposed diff:**
- Reason-tag prefix change from `MGIC` to `MI` (vendor-agnostic) is OPTIONAL — leaving `MGIC` in place preserves the lib/rules/pmi.py format string and citation-stable test surface. **NEEDS-DECISION** for the user: keep `MGIC` tag (cosmetic citation drift) or rename to `MI` (touch tests too). If reading lib/rules/pmi.py line 88, the tag literal is `PMI-RATE-ESTIMATED-MGIC-{ltv_band_label}-{fico_band_label}` — any vendor rename triggers a test update.
- The capped-fallback bump from 0.0078 → 0.0079 is +1bps (within rounding noise). All capped-fallback reason tags downstream (`PMI-RATE-CAPPED-MGIC-ABRIDGED-{fico}-{ltv}`) unchanged.
- 80-85 column changes are SMALL (-8 to +0 bps) but 740-759 × 80-85 drops 3bps (0.0023 → 0.0020) — verified by Arch + Enact + Essent + NatMI all agreeing on 0.20% there.

### 5. Confidence verdict

**HIGH** for the proposed 4×4 grid. Four independent public-source rate cards (Arch MI 2026-02-09, Enact MI 2025-07-25, Essent 2019-02-11, National MI 2022-03-01) publish IDENTICAL standard-coverage cells across every FICO/LTV combination in the YAML's bucketing. Disagreement between vendors at any cell is 0bps. The cells have been stable across at least 7 years of published filings.

Caveat: the underlying MGIC rate card (the YAML's original primary source) cannot be re-verified directly without MiQ login. However:
1. The MGIC bulletin index publicly lists ALL 2025 bulletins, NONE of which touched BPMI rates.
2. The 2017 MGIC Credit Union archive PDF still publicly accessible publishes the same standard-coverage cells (760+ × 95-97 25% = 0.44 vs Arch 2026 = 0.46 — 2bps drift over 8 years).
3. Filed-rate convergence across the four major MIs means switching the YAML's primary source from MGIC to Arch MI is **substantively equivalent** for the abridged 4×4 subset.

The new `effective: 2026-02-09` is the date of the Arch MI rate card. This is the most defensible currently-published date.

### 6. Risk note — VALUES MAY HAVE MOVED

**MATERIAL FINDING:** The current YAML's interior cells (85-90, 90-95, 95-97 columns) are systematically **UNDER-STATED by 9-13bps** vs current 2026 industry-standard 25%-coverage filed rates. The under-statement is consistent across multiple cells and FICO bands, suggesting the original 2024 YAML may have inadvertently used **18%-or-mixed coverage cells** rather than the Fannie/Freddie-standard 25% coverage rows.

**Material cells (>15bps shift) — call out to the user:**
- None of the proposed deltas exceed 15bps (the largest is +13bps at 740-759 × 90-95).

**Cells worth attention (10-15bps shift, just under the materiality threshold):**
- 740-759 × 85-90: +10bps (0.0028 → 0.0038)
- 740-759 × 90-95: **+13bps** (0.0035 → 0.0048)
- 740-759 × 95-97: +12bps (0.0046 → 0.0058)
- 720-739 × 90-95: +11bps (0.0048 → 0.0059)
- 760+ × 95-97: +12bps (0.0034 → 0.0046)

**Why this matters for the Pachulski household:**
The Phase 16-01 design notes call out 740-759 as the "Pachulski-household representative band". The 740-759 × 90-95 cell shifts +13bps (0.0035 → 0.0048), which on a $400k loan adds ~$52/yr or ~$4.30/mo to estimated PMI in `lib/rules/pmi.py` lookups. **This is the most relevant cell for household scenarios and is materially closest to the 15bps materiality threshold.**

**Recommended next step:** Before applying the diff, the user should decide whether the original 2024 YAML's interior cells were intentional (representing some non-standard coverage mix used by MGIC's "Standard MI" product) or were a sourcing error. Two paths:
1. **If MiQ login available:** Run an MGIC rate quote for FICO 745 × LTV 0.92 × 30yr Conv Purchase Primary Res — if the MGIC quote returns ~0.48% (matching cross-source) then the YAML was mis-sourced; if it returns ~0.35% then MGIC has a genuinely lower filed rate than Arch/Enact/Essent and the YAML was correct.
2. **If MiQ login unavailable:** Apply the Arch MI 2026-02-09 cells as the new pinned values; document the vendor switch explicitly in the YAML notes block.

**Confidence in the "values may have moved" framing:** HIGH that the YAML disagrees with current Arch/Enact/Essent/NatMI public cards; MEDIUM-HIGH that the disagreement was a 2024 sourcing artifact rather than MGIC's filed rates having moved materially since then.
