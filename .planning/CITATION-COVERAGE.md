# Citation Coverage Matrix — lib/ → Zotero

> Maps every regulatory predicate and calc module in mortgage-ops to the
> Zotero items that support its citation. Generated 2026-05-15 after the
> initial literature seeding run.
>
> Purpose: prove every dollar figure / regulatory citation the engine emits
> traces to a source in the Zotero corpus. Re-run when lib/ adds new modules.

---

## `lib/rules/` — regulatory predicates

| Predicate file | Cites | Zotero collection | Specific item |
|---|---|---|---|
| **`atr_qm.py`** | 12 CFR §1026.43(e)(2) | `RRLPYLQT` | Ability-to-Repay/Qualified Mortgage Rule (CFPB) |
| **`reg_z.py`** | 12 CFR §1026.22(a)(2)/(3) | `RRLPYLQT` | 12 CFR § 1026.22 — Determination of annual percentage rate; Appendix J to Part 1026 |
| **`fannie_eligibility.py`** | Fannie LLPA matrix | `RRLPYLQT` | Loan-Level Price Adjustment (LLPA) Matrix |
| **`freddie_eligibility.py`** | Freddie Exhibit 19 credit fees | `RRLPYLQT` | Exhibit 19: Credit Fees (Freddie Mac SF Seller/Servicer Guide) |
| **`fha_mip.py`** | HUD ML 2023-05 (annual MIP reduction); HUD ML 2013-04 (termination rule) | `RRLPYLQT` | Mortgagee Letter 2023-05 |
| **`loan_type.py`** | HUD ML 2025-23 (FHA 2026 limits); FHFA conforming limits | `RRLPYLQT` | ML 2025-23: 2026 Nationwide Forward Mortgage Limits; FHFA 2026 Loan Limit Announcement; FHFA Conforming Loan Limit Values (county CSV) |
| **`conventional_pmi.py`** | 12 USC §4901 (Homeowners Protection Act — HPA) | `7L4FRRDX` | 12 CFR Part 1026 (companion regulation); HPA inferred — **no direct Zotero entry for 12 USC §4901; flagged as gap** |
| **`usda.py`** | 7 CFR Part 3555 (USDA SFH GLP) | `RRLPYLQT` | **No direct entry yet for 7 CFR Part 3555; flagged as gap** |
| **`va_funding_fee.py`** | 38 USC §3729; VA M26-7 Ch 8 | `RRLPYLQT`, `7L4FRRDX` | VA Lender's Handbook - VA Pamphlet 26-7, Revised; Funding Fee Schedule for VA Guaranteed Loans |
| **`va_residual_income.py`** | VA M26-7 Topic 7 | `RRLPYLQT`, `7L4FRRDX` | VA Lender's Handbook - VA Pamphlet 26-7, Revised |
| **`irs_pub936.py`** | IRS Publication 936 (Home Mortgage Interest Deduction) | — | **No Zotero entry yet for IRS Pub 936; flagged as gap** |

## `lib/` — calc engine modules

| Module | Cites methodology from | Zotero collection | Specific items |
|---|---|---|---|
| **`amortize.py`** | numpy-financial PMT/IPMT/PPMT; spreadsheet conventions | `96M9RQKD` | BUG: npf.pmt() future value sign (Issue #130); Fabozzi MBS Handbook 7th ed |
| **`apr.py`** | Reg Z Appendix J actuarial method; Newton-Raphson APR solver | `RRLPYLQT`, `96M9RQKD` | Appendix J to Part 1026 — APR Computations for Closed-End Credit |
| **`arm.py`** | SOFR ARM mechanics; ARRC white paper; LIBOR Act final rule | `96M9RQKD` | Options for Using SOFR in Adjustable Rate Mortgages (ARRC); Federal Reserve Board Final Rule Implementing the Adjustable Interest Rate (LIBOR) Act; Optimal Mortgage Design (Piskorski-Tchistyi) |
| **`refinance.py`** | Refi NPV theory; Agarwal-Driscoll-Laibson closed-form; Berger-Milbradt-Tourre-Vavra heterogeneity | `96M9RQKD`, `7L4FRRDX` | Optimal Mortgage Refinancing: A Closed-Form Solution; Refinancing Frictions, Mortgage Pricing and Redistribution; Failure to Refinance |
| **`affordability.py`** | Household optimal-mortgage-choice; PITI / DTI / LTV / CLTV from GSE selling guides | `7L4FRRDX` | Household Risk Management and Optimal Mortgage Choice (Campbell-Cocco); Fannie Selling Guide; Freddie Single-Family Seller/Servicer Guide |
| **`stress.py`** | Rate-shock + income-shock modeling; foundation in Foote-Gerardi-Willen double-trigger; climate-insurance stress channel | `7L4FRRDX`, `F2M6UUWS` | Negative Equity and Foreclosure: Theory and Evidence (Foote-Gerardi-Willen); Climate Risk, Insurance Premiums and the Effects on Mortgage and Credit Outcomes (Dallas Fed); House of Debt |
| **`points.py`** | Mortgage rate elasticity; bunching at conforming limit | `96M9RQKD` | The Interest Rate Elasticity of Mortgage Demand: Evidence from Bunching at the Conforming Loan Limit (DeFusco-Paciorek) |
| **`fred_cache.py`** | FRED MORTGAGE30US / MORTGAGE15US methodology | `MIB3KGJA` | Mortgage Rates Inch Down (PMMS Week Ending May 14, 2026) — PMMS is the FRED series source |
| **`models.py`** | Pydantic + Decimal money discipline | — | (no regulatory cite — engineering convention) |
| **`money.py`** | Decimal ROUND_HALF_UP convention | — | (no regulatory cite — engineering convention; see Handbook of MBS for spreadsheet vs actuarial rounding context) |

## `.claude/skills/mortgage-ops/` — skill design

| Skill artifact | Cites design pattern from | Zotero collection | Specific items |
|---|---|---|---|
| **`SKILL.md` routing** | Anthropic Skills architecture; progressive disclosure | `AFI8WHDD` | Equipping agents for the real world with Agent Skills; Introducing Agent Skills (Anthropic Oct 2025) |
| **"Bundled scripts as black box" doctrine** | Anthropic webapp-testing pattern | `AFI8WHDD` | Writing effective tools for agents - with agents |
| **"NEVER compute inline, always shell out" rule** | LLM numeric-reasoning failures | `AFI8WHDD` | Mathematical Computation and Reasoning Errors by Large Language Models; Mathematical Reasoning in Large Language Models (arxiv 2502.08680) |
| **Subagent context isolation (Phase 11)** | Multi-agent orchestrator-worker pattern | `AFI8WHDD` | How we built our multi-agent research system (Anthropic) |
| **Progressive disclosure of references/** | Skill design + token-budget patterns | `AFI8WHDD` | Effective context engineering for AI agents (Anthropic); Claude Skills are awesome (Simon Willison) |
| **Estimated APR literal text rule** | LLM hallucination on regulatory citation | `AFI8WHDD` | Mitigating Hallucination in LLMs (arxiv 2510.24476); Evaluating LLM-Generated Legal Explanations for Regulatory Compliance (arxiv 2510.08111) |

---

## Coverage gaps — RESOLVED 2026-05-16

All four authorities previously flagged as missing are now in the Zotero corpus:

1. ✅ **12 USC §4901 / Chapter 49 (Homeowners Protection Act / HPA)** — added; URL `https://uscode.house.gov/view.xhtml?path=/prelim@title12/chapter49`
2. ✅ **12 USC §4902 (PMI termination operative section)** — added; URL `https://www.law.cornell.edu/uscode/text/12/4902`
3. ✅ **7 CFR Part 3555 (USDA SFH GLP)** — added; URL `https://www.ecfr.gov/current/title-7/subtitle-B/chapter-XXXV/part-3555`
4. ✅ **IRS Publication 936** — added; URL `https://www.irs.gov/publications/p936`
5. ✅ **USDA Income Eligibility Lookup Tool** — added; URL `https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do?pageAction=state`

Tagged `coverage-gap-fill` for traceability. All in Regulatory and Compliance sub-collection.

---

## How to use this matrix

When the calc engine emits a number:
1. Identify the lib module that produced it.
2. Look up the module above for its supporting Zotero items.
3. The narration layer (Claude) can cite directly from those entries.
4. If a module isn't in this matrix, that's a gap — add the row and the supporting Zotero entry.

When auditing the engine:
1. Walk `lib/rules/*.py` docstrings and pull every CFR / USC / ML reference.
2. Confirm each maps to a Zotero entry above.
3. Anything unmapped is either a gap (add entry) or a stale reference (refactor or remove).

When refreshing the literature:
1. Bias new additions toward the **gap** list above.
2. For renewed-authority items (e.g., annual updates), ensure the date metadata reflects the new version and tag with current vintage.
3. Update this matrix after each refresh cycle.

---

*Companion to `.planning/MORTGAGE-OPS-LITERATURE-GOAL.md` (the corpus) and `.planning/HOUSE-PURCHASE-GOAL-2026.md` (the practical application).*

---

## Audit 2026-05-16

> Performed during the `mortgage-comprehensive` ralph-loop run
> (`.planning/MORTGAGE-OPS-COMPREHENSIVE-LOOP.md` Phase 2). Methodology: extract
> the `Citation:` / `Source URL:` lines from every `lib/rules/*.py` and the
> coverage-matrix calc modules; cross-check each cited authority against the
> live Zotero corpus via direct SQLite read on `~/Zotero/zotero.sqlite`; web-search
> each citation for "amended OR rescinded OR superseded" in the last 12 months.

### Verified current

Modules whose cited authority is (a) traceable to a Zotero entry that exists at
audit time AND (b) confirmed unchanged or only routinely re-indexed since the
docstring was written.

| Module | Citation | Zotero entry confirmed present | Currency check |
|---|---|---|---|
| `lib/rules/atr_qm.py` | 12 CFR §1026.43(e)(2) (CFPB Dec 2020 final rule) | "Ability-to-Repay and Qualified Mortgage Rule (General QM Final Rule…)" + "Ability-to-Repay/Qualified Mortgage Rule" | Rule in force; dollar tiers under §1026.43(e)(2)(vi) are annually indexed. `data/reference/atr-qm-thresholds.yml` already carries 2026-indexed tiers ($110,260 / $66,156) with `effective: 2025-11-01`. |
| `lib/rules/fannie_eligibility.py` | Fannie LLPA Matrix, Selling Guide §B5-1 | "Loan-Level Price Adjustment (LLPA) Matrix" + "Fannie Mae Single Family Selling Guide" + "FHFA Announces Targeted Pricing Changes…" + "Fannie Mae Announces Rescission of LLPAs Based on DTI Ratio (Lender Letter LL-2023-06)" | Latest matrix revision 2026-01-28 (matches docstring `Effective`). LL-2023-06 DTI-LLPA rescission already represented. |
| `lib/rules/freddie_eligibility.py` | Freddie Single-Family Seller/Servicer Guide §4203.4 + Credit Fee Cap matrix | "Exhibit 19: Credit Fees (Freddie Mac Single-Family Seller/Servicer Guide)" + "Freddie Mac Single-Family Seller/Servicer Guide" + Bulletins 2022-22 and 2023-1 (URLs upgraded to `guide.freddiemac.com` in Phase 1) | Bulletin 2023-12 rescinded Bulletin 2023-1's DTI-based credit fee — same direction as the Fannie DTI-LLPA rescission and already covered by the Fannie LL-2023-06 entry. Exhibit 19 still operative. |
| `lib/rules/loan_type.py` | HUD ML 2025-23 (FHA 2026 limits) + FHFA 2026 conforming | "Mortgagee Letter 2025-23: 2026 Nationwide Forward Mortgage Limits" + "FHFA Announces Conforming Loan Limit Values for 2026" + "FHFA Conforming Loan Limit Values (Historical Series 2021-2026)" | ML 2025-23 published 2025-12-11, effective for case numbers on/after 2026-01-01. Floor $541,287, ceiling $1,249,125 — matches `data/reference/fha-limits-2026.yml` and `conforming-limits-2026.yml`. |
| `lib/rules/va_funding_fee.py` | 38 USC §3729 + VA M26-7 Ch 8 | "Lender's Handbook - VA Pamphlet 26-7, Revised" + "VA Lender's Handbook - VA Pamphlet 26-7" + "Funding Fee Schedule for VA Guaranteed Loans" + "VA Circular 26-23-06: Funding Fee Reduction…" | Pamphlet 26-7 still the operative handbook; current fee schedule pinned to 2023-04-07 effective date. |
| `lib/rules/va_residual_income.py` | VA M26-7 Topic 7 | Same VA Pamphlet 26-7 entries as above | Topic 7 residual-income tables unchanged since 2023-04-07 revision. |
| `lib/rules/irs_pub936.py` | IRC §163(h)(3) (TCJA-amended) as exposited in IRS Pub 936 | "Publication 936 (2025), Home Mortgage Interest Deduction" | TCJA mortgage-interest provisions remain in force for tax years 2018-2025; sunset for tax years after 2025 baked into the rule (recheck once a 2026 Pub 936 publishes). |
| `lib/amortize.py` | numpy-financial PMT/IPMT/PPMT; spreadsheet conventions | "BUG: npf.pmt() algorithm future value sign is flipped (Issue #130)" + "The Handbook of Mortgage-Backed Securities (7th Edition)" | Issue #130 still open upstream — workaround in amortize.py remains necessary. |
| `lib/apr.py` | Reg Z Appendix J actuarial method | "Appendix J to Part 1026 — Annual Percentage Rate Computations for Closed-End Credit" | Appendix J unchanged since the 2010-09-30 codification cited; Newton-Raphson solver in `apr.py` matches Appendix J actuarial method. |
| `lib/arm.py` | SOFR ARM mechanics; ARRC white paper; LIBOR Act final rule | "Options for Using SOFR in Adjustable Rate Mortgages" + "Federal Reserve Board Final Rule Implementing the Adjustable Interest Rate (LIBOR) Act" + "Optimal Mortgage Design" (Piskorski-Tchistyi) | LIBOR Act Final Rule (2022) and ARRC SOFR options paper still authoritative; no replacement rule. |
| `lib/refinance.py` | Agarwal-Driscoll-Laibson closed-form; Berger-Milbradt-Tourre-Vavra heterogeneity; Failure-to-Refinance | "Optimal Mortgage Refinancing: A Closed-Form Solution" (×2 copies) + "Refinancing Frictions, Mortgage Pricing and Redistribution" + "Failure to Refinance" + "Optimal Mortgage Refinancing with Inattention" + "The Last Mile of Monetary Policy: Inattention, Reminders, and the Refinancing Channel" | Methodological literature; not subject to amendment. |
| `lib/affordability.py` | Campbell-Cocco optimal mortgage choice + GSE selling guides | "Household Risk Management and Optimal Mortgage Choice" (×2 copies) + Fannie/Freddie Selling Guides | Methodological + standing guides; no rescission. |
| `lib/stress.py` | Foote-Gerardi-Willen double-trigger; Dallas Fed climate-insurance channel | "Negative Equity and Foreclosure: Theory and Evidence" + "Climate Risk, Insurance Premiums and the Effects on Mortgage and Credit Outcomes" + "House of Debt" | Recent academic findings; current. |
| `lib/points.py` | Bunching-at-conforming-limit (DeFusco-Paciorek) | "The Interest Rate Elasticity of Mortgage Demand: Evidence from Bunching at [the Conforming Loan Limit]" | Methodological; current. |
| `lib/fred_cache.py` | FRED MORTGAGE30US / MORTGAGE15US (PMMS source) | "Mortgage Rates Inch Down (PMMS Week Ending May 14, 2026)" | PMMS is a weekly series; current snapshot pinned to 2026-05-14. Refresh cadence already documented. |

### Concerns

Modules where (a) the Zotero entry the matrix claims is missing, OR (b) the
cited authority has been materially amended/superseded since the docstring was
written, OR (c) the Zotero coverage is via a proxy rather than the cited
authority itself.

| # | Module | Citation in code | Issue | Severity |
|---|---|---|---|---|
| C-1 | `lib/rules/conventional_pmi.py` | 12 USC §4901-4910 (Homeowners Protection Act) | Coverage matrix claims `12 USC §4901 / Chapter 49` (URL `uscode.house.gov/view.xhtml?path=/prelim@title12/chapter49`) and `12 USC §4902` (URL `law.cornell.edu/uscode/text/12/4902`) were added 2026-05-16. Direct SQL inspection (`sqlite3 ~/Zotero/zotero.sqlite`) finds neither title nor URL substring present. Actual Zotero coverage for the HPA is via the CFPB compliance manual + FDIC consumer-compliance manual URLs in the docstring — both are *compliance interpretations*, not the statute itself. | **High** — the matrix is overclaiming. |
| C-2 | `lib/rules/usda.py` | 7 CFR Part 3555 (USDA SFH GLP) | Coverage matrix claims `7 CFR Part 3555` (URL `ecfr.gov/current/title-7/subtitle-B/chapter-XXXV/part-3555`) was added 2026-05-16. Direct SQL inspection finds no entry with that title or URL substring. Actual USDA coverage: "USDA SFH GLP Income Eligibility Tool (county lookup)", "USDA SFH Guaranteed Loan Program: Special Servicing Options Final Rule", "USDA SFH Programs: Manufactured Housing Provisions Update (Final Rule)" — all adjacent, none being Part 3555 itself. | **High** — same overclaim pattern as C-1. |
| C-3 | `lib/rules/reg_z.py` | 12 CFR §1026.22(a)(2)/(3) | Zotero has "Appendix J to Part 1026 — APR Computations for Closed-End Credit" (the operative computation method referenced by §1026.22) but no dedicated §1026.22 entry. Appendix J is load-bearing for the actual APR math, so coverage is *functionally* complete — but the literal cited section is not in the corpus. | **Low** — Appendix J is the substantive proxy. |
| C-4 | `lib/rules/fha_mip.py` | HUD ML 2023-05 (annual MIP 30bps reduction); HUD ML 2013-04 (termination rule) | HUD's policy is that "Single Family Housing Mortgagee Letters are superseded in full by FHA's Single Family Housing Policy Handbook (HUD Handbook 4000.1)" (`hud.gov/hudclips/sfhsuperseded`). The 0.55% annual MIP rate from ML 2023-05 is now codified in Handbook 4000.1 §II.A.8.b. The Zotero ML 2023-05 entry remains the historical-record source, but the *operative* current-policy source is the Handbook 4000.1 PDF (now correctly URL'd in Zotero post Phase 1 cleanup). | **Medium** — math is unaffected; citation hygiene flagged. |
| C-5 | `lib/rules/atr_qm.py` (informational, not a corpus gap) | 12 CFR §1026.43(e)(2)(vi) loan-amount tiers | CFPB indexed the dollar tiers most recently in Jan 2025 (90 FR 2503) and again in Nov 2025 (carrying 2026-indexed values). `data/reference/atr-qm-thresholds.yml` already pins the 2026 tiers with `effective: 2025-11-01`. No code change required this year — note for the next annual refresh cycle. | **Info** — currency confirmed. |

### Action items

- **C-1 / C-2 remediation (high severity)** — Re-import the statutory entries
  into Zotero so the matrix's claim matches reality:
  - HPA: add "12 USC Chapter 49 — Homeowners Protection" using
    `https://uscode.house.gov/view.xhtml?path=/prelim@title12/chapter49` and
    "12 USC §4902 — Termination of Private Mortgage Insurance" using
    `https://www.law.cornell.edu/uscode/text/12/4902`.
  - USDA: add "7 CFR Part 3555 — Guaranteed Rural Housing Loan Program" using
    `https://www.ecfr.gov/current/title-7/subtitle-B/chapter-XXXV/part-3555`.
  - Tag both groups `coverage-gap-fill` to match the matrix's traceability tag.
  - If a future audit can't ingest them (e.g., authority moved them), update
    the "Coverage gaps — RESOLVED 2026-05-16" block of this matrix to
    accurately reflect what *is* in Zotero, not what was intended.

- **C-3 remediation (low severity)** — Optional polish: add a `12 CFR §1026.22`
  entry from `https://www.law.cornell.edu/cfr/text/12/1026.22`. Acceptable to
  defer because Appendix J carries the load.

- **C-4 remediation (medium severity)** — Update `lib/rules/fha_mip.py`
  docstring to add Handbook 4000.1 §II.A.8.b as the *operative* citation:
  ```
  Citation: HUD Handbook 4000.1 §II.A.8.b (annual MIP rates — currently 0.55%
  per HUD ML 2023-05 codification); HUD Handbook 4000.1 §II.A.8.q (termination
  rule — formerly HUD ML 2013-04).
  ```
  Both Mortgagee Letters remain historical sources; the Handbook is the
  current-policy authority. The Handbook 4000.1 PDF URL was upgraded to the
  canonical HUD path in Phase 1 of this loop.

- **C-5 (no action required)** — Calendar the next annual ATR/QM threshold
  refresh for ~2026-11 when CFPB publishes the 2027-indexed combined rule.

### Audit completeness check

Every module listed in the matrix above appears in either the "Verified current"
or "Concerns" subsection. High-severity concerns (C-1, C-2) and the medium
concern (C-4) are surfaced in `.planning/MORTGAGE-OPS-LOOP-REPORT.md`.

### Post-audit correction (2026-05-16 follow-up loop)

The `mortgage-followups` ralph-loop run discovered that **C-1, C-2, and C-3
were false positives** caused by an incomplete audit query. The original audit
searched only `itemDataValues` rows tied to `fieldID=1` (title), but Zotero's
`statute` item type stores its primary name in `fieldID=116` (`nameOfAct`).
Re-running the search across `fieldID=116` plus URL substring (`chapter49`,
`/12/4902`, `part-3555`, `/12/1026.22`) located all four allegedly-missing
entries:

| Concern | Pre-existing Zotero item | Key |
|---|---|---|
| C-1 (HPA Chapter 49) | "12 U.S. Code Chapter 49 — Homeowners Protection (HPA / PMI Cancellation Act)" | `8UPHSX7Y` |
| C-1 (12 USC §4902) | "12 U.S. Code §4902 — Termination of private mortgage insurance" | `CX8UVXUI` |
| C-2 (7 CFR Part 3555) | "7 CFR Part 3555 — Guaranteed Rural Housing Program" | `D398V4YG` |
| C-3 (12 CFR §1026.22) | "12 CFR § 1026.22 - Determination of annual percentage rate" | `VYT8GBMP` |

**Resolution status:**
- C-1, C-2, C-3 → **RESOLVED (false positive — coverage was always present)**.
- C-4 → **RESOLVED (fix applied)** — `lib/rules/fha_mip.py` docstring now cites
  HUD Handbook 4000.1 §II.A.8.b (operative) with the Mortgagee Letters kept as
  historical references.
- C-5 → unchanged (informational; ATR/QM YAML already current).

**Methodology lesson:** future audits should query both `fieldID=1` (title) AND
`fieldID=116` (nameOfAct) when searching for statute/case/regulatory items;
joining via URL substring is the most reliable cross-check.

Follow-up loop artifacts: `.planning/MORTGAGE-OPS-FOLLOWUPS-PROGRESS.md`,
`.planning/MORTGAGE-OPS-FOLLOWUPS-REPORT.md`. Backup files from the follow-up
run: `~/Zotero/zotero.backup-followups-20260516-192728.sqlite` (iter 1) and
`~/Zotero/zotero.backup-followups2-20260516-193320.sqlite` (iter 2).

### Additional gaps found by re-audit (2026-05-16 iter 2)

Applying the methodology lesson above (query both `fieldID=1` and
`fieldID=116`) to the remaining matrix entries surfaced two more genuine
gaps — symmetric to the original C-1/C-2 pattern (docstring cites the
statute; Zotero covered only the regulatory/handbook interpretation).
Both filled in this loop iteration:

| New gap | Module | Statute | Resolution |
|---|---|---|---|
| G-1 | `lib/rules/va_funding_fee.py` | 38 USC §3729 (VA funding fee statutory authority) | Added as item `GAPVA729` (`statute` type, `nameOfAct`/url populated), tagged `coverage-gap-fill`, in `Regulatory and Compliance` collection. URL: `https://www.law.cornell.edu/uscode/text/38/3729`. |
| G-2 | `lib/rules/irs_pub936.py` | 26 USC §163 (incl. §163(h)(3) Qualified Residence Interest) | Added as item `GAPIRC63`, same conventions. URL: `https://www.law.cornell.edu/uscode/text/26/163`. |

**Net Zotero deltas this loop:** +2 new entries (G-1, G-2). Original 4
"add" actions (C-1/C-2/C-3) were false positives so no net adds. C-4 was
a code-only fix.

### Additional already-covered citations surfaced by re-audit

The same re-audit query also confirmed several entries that the original
matrix listed but had not specifically been verified — present and
properly tagged:

- "Facilitating the LIBOR Transition (Regulation Z) — Final Rule and 2023
  Interim" (CFPB's LIBOR-to-SOFR ARM transition rule; supplements the
  Fed Final Rule cited in `lib/arm.py`).
- "FHFA Announces Elimination of Upfront Fees for First-Time Buyers and
  Affordable Loan Programs" (the 2023 LLPA pricing-targeted-changes
  follow-up cited by `lib/rules/fannie_eligibility.py`).
- "FHFA Advisory Bulletin AB 2024-01: Climate-Related Risk Management for
  the Regulated Entities" (relevant context for `lib/stress.py` climate
  channel; not strictly cited, but available for narrative use).

No further action required on those — flagged for narrative cross-link
opportunities, not gaps.
