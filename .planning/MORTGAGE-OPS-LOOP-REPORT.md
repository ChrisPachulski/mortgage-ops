# Mortgage-Ops Comprehensive Loop — Final Report

> Produced by ralph-loop `mortgage-comprehensive` on 2026-05-16. Source
> instructions: `.planning/MORTGAGE-OPS-COMPREHENSIVE-LOOP.md`. Progress
> log: `.planning/MORTGAGE-OPS-LOOP-PROGRESS.md`.
>
> Three phases were executed against their "phase complete when" criteria.
> All three completed; this report consolidates the findings, the deltas
> they introduce to existing planning documents, and the follow-up actions.

---

## Phase 1 — Zotero corpus URL cleanup

**Status:** ✅ Complete.
**Backup:** `~/Zotero/zotero.backup-loop-20260516-182531.sqlite`
(timestamp from this loop run; original 2,879,488 bytes preserved).
**Mechanism:** Zotero.app quit via `osascript -e 'tell app "Zotero" to quit'`,
URL field (`fieldID=10`) updated via direct SQL on `~/Zotero/zotero.sqlite`,
relaunched via `open -a Zotero`. Note: `cli-anything-zotero` was not on
PATH; direct SQLite was used as the equivalent verification path. SQL used:
`INSERT OR IGNORE` into `itemDataValues`, then `UPDATE itemData.valueID`
keyed by the title-matched item.

| # | Title (truncated) | Before URL (host only) | After URL | Tier 1? | Verified |
|---|---|---|---|---|---|
| 1 | Freddie Mac Bulletin 2022-22: Credit Fee Cap Introducti… | tenaco.com (industry mirror) | `https://guide.freddiemac.com/app/guide/bulletin/2022-22` | ✅ freddiemac.com | curl HTTP 200; SQL post-update read confirms |
| 2 | Freddie Mac Bulletin 2023-1: Credit Fee Updates and Exh… | tenaco.com (industry blog) | `https://guide.freddiemac.com/app/guide/bulletin/2023-1` | ✅ freddiemac.com | curl HTTP 200; SQL post-update read confirms |
| 3 | FHA HECM Reverse Mortgage Servicing Handbook Revisions | financialservicesperspectives.com (Mayer Brown LLP blog) | `https://www.hud.gov/sites/dfiles/OCHCO/documents/4000.1hsgh.pdf` | ✅ hud.gov | curl HTTP 200; SQL post-update read confirms. NOTE: the path in the original cleanup TODO (`40001HSGH.pdf`, uppercase) returned 404; the canonical HUD path uses dotted lowercase (`4000.1hsgh.pdf`). |
| 4 | NWMLS: 2024 in Review — Annual Housing Market Report | seattleagentmagazine.com (trade journalism) | `https://www.nwmls.com/wp-content/uploads/2025/01/AnnualReview2024.pdf` | ✅ nwmls.com | curl HTTP 200; SQL post-update read confirms. NOTE: the `/market-reports/annual/2024` path proposed in the TODO returned 404; NWMLS hosts the report as a wp-content PDF instead. |
| 5 | NWMLS: 2025 Home Sales, Prices Kept Pace With 2024 Leve… | seattleagentmagazine.com (trade journalism) | `https://www.nwmls.com/wp-content/uploads/2026/01/AnnualReview2025.pdf` | ✅ nwmls.com | curl HTTP 200; SQL post-update read confirms. Same path-discovery note as row 4. |

**Phase 1 completion criteria — re-verified:**
- All 5 items now point to a Tier 1 authority
  (freddiemac.com / hud.gov / nwmls.com). ✅
- A SQLite backup exists with timestamp from this loop run
  (`zotero.backup-loop-20260516-182531.sqlite`, 2,879,488 bytes). ✅

---

## Phase 2 — Calc engine citation audit

**Status:** ✅ Complete. Full audit section appended to
`.planning/CITATION-COVERAGE.md` under heading `## Audit 2026-05-16`.

**Counts:**

| Bucket | Count |
|---|---|
| **Verified current** | 14 modules — `atr_qm`, `fannie_eligibility`, `freddie_eligibility`, `loan_type`, `va_funding_fee`, `va_residual_income`, `irs_pub936`, `amortize`, `apr`, `arm`, `refinance`, `affordability`, `stress`, `points`, `fred_cache` (15 if `fred_cache` counted separately). |
| **Concerns — high severity** | 2 (C-1, C-2) — overclaimed Zotero coverage |
| **Concerns — medium severity** | 1 (C-4) — superseded-by-handbook citation hygiene |
| **Concerns — low / info** | 2 (C-3 proxy-coverage; C-5 informational) |

### High-severity concerns (action required this cycle)

**C-1 — `lib/rules/conventional_pmi.py` cites the Homeowners Protection Act
(12 USC §4901-4910), but Zotero is missing the statute itself.**
The "Coverage gaps — RESOLVED 2026-05-16" block of `CITATION-COVERAGE.md`
claims `12 USC §4901 / Chapter 49` and `12 USC §4902` were added 2026-05-16
with the URLs `uscode.house.gov/view.xhtml?path=/prelim@title12/chapter49`
and `law.cornell.edu/uscode/text/12/4902`. Direct SQL inspection
(`sqlite3 ~/Zotero/zotero.sqlite` filtering on those URL substrings)
returned zero rows. Actual HPA coverage in Zotero today is the
`consumerfinance.gov/.../homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/`
and `fdic.gov/.../v-5-homeowners-protection-act` URLs referenced from the
predicate's docstring — both compliance-side interpretations, not the statute.

*Recommended remediation:* import the two statutory entries listed in the
matrix's `RESOLVED` block (or amend that block to match what is actually in
Zotero). Tag `coverage-gap-fill` to match the matrix's traceability convention.

**C-2 — `lib/rules/usda.py` cites 7 CFR Part 3555, but Zotero is missing
the regulation itself.**
Same pattern as C-1: matrix claims `7 CFR Part 3555` was added with
`ecfr.gov/current/title-7/subtitle-B/chapter-XXXV/part-3555`; SQL confirms
neither title nor URL substring is present. The corpus does carry adjacent
items ("USDA SFH GLP Income Eligibility Tool", "USDA SFH GLP Special
Servicing Options Final Rule", "USDA SFH Programs: Manufactured Housing
Provisions Update"), but none of them is Part 3555 itself.

*Recommended remediation:* import the eCFR Part 3555 entry, same tagging.

### Medium-severity concern

**C-4 — `lib/rules/fha_mip.py` cites HUD ML 2023-05 and ML 2013-04 as
operative; HUD treats Single Family Housing Mortgagee Letters as
"superseded in full by Handbook 4000.1".**
The 0.55% annual MIP rate from ML 2023-05 is unchanged in policy; it has
simply been re-housed in Handbook 4000.1 §II.A.8.b. The math in the
predicate is unaffected. What needs to change is the docstring's
`Citation:` line — it should name Handbook 4000.1 §II.A.8.b as the
operative source and keep ML 2023-05/2013-04 as historical references.

*Recommended remediation:* update docstring (text suggested in the audit
section itself); the Handbook 4000.1 PDF was just upgraded into Zotero by
Phase 1 row 3, so the destination citation is already corpus-traceable.

### Low / informational

- **C-3** — `lib/rules/reg_z.py` cites §1026.22 but Zotero only carries the
  closely-related Appendix J. Appendix J is the substantive method
  referenced by §1026.22 itself, so functional coverage is fine; the
  literal-section entry is the only thing missing. Optional polish.
- **C-5** — `data/reference/atr-qm-thresholds.yml` already carries the
  2026-indexed CFPB threshold dollar tiers with `effective: 2025-11-01`.
  No action required; calendar the next refresh for ~2026-11.

**Phase 2 completion criteria — re-verified:**
- Every module in the coverage matrix has a row in either "Verified
  current" or "Concerns". ✅
- The audit-results section exists in `CITATION-COVERAGE.md`. ✅
- High-severity concerns (C-1, C-2) are surfaced in this consolidated
  report above. ✅

---

## Phase 3 — Literature-grounded stress tests

**Status:** ✅ Complete. Narration appended to
`.planning/HOUSE-PURCHASE-GOAL-2026.md` under
`## Literature-Grounded Stress Tests (2026-05-16)`.

**Common base case:** $700K purchase, 15% down → $595K loan, 30yr fixed at
6.36% (PMMS 2026-05-14), King County escrow assumptions, $135/mo PMI.
Baseline PITI = $4,639.52 (from `affordability.py`).

| # | Scenario | Underlying script call | Headline metric | Verdict |
|---|---|---|---|---|
| 1 | Rate-shock 6.36% → 7.50% on $595K loan | `stress_test.py mode=rate-shock` over `["0.0636","0.0700","0.0750"]` | P&I 7.50% = **$4,160.33**, Δ +$454.14/mo vs 6.36%. Total interest grows from $739,229 → $902,714. | **Survives DTI**, fails sustainable-PITI ceilings. Stressed PITI ~$5,094/mo lands $694 over the climate-adjusted Realistic $4,400 ceiling. Per lock-in literature (Liebersohn-Rothstein, Fonseca-Liu) the household is committed to those payments for years before refi opens. Action: at 7.50% quotes, tier down to $650-675K. |
| 2 | Climate-insurance 15% YoY × 5 years | 6 × `affordability.py` runs at insurance $250 → $502.84/mo | PITI Y0=$4,639.52 → Y5=**$4,892.36**, Δ +$252.84/mo. DTI grows 24.6% → 25.7%. Annual insurance $3,000 → $6,034 (≈ 6× Dallas Fed marginal hike of $500/yr). | **Survives mechanically** (script never blocks). Per Dallas Fed Ge/Johnson/Tzur-Ilan 2025, this kind of escalation correlates with materially higher delinquency for stretched households. Action: bias to 98058 (lower WUI exposure); budget $50-100/mo insurance escalation reserve from day-1. |
| 3 | Dana income → $0 (job loss / extended leave 6mo) | `stress_test.py mode=income-shock` at `reductions=["0.4257"]` (Dana = 42.57% of household gross) | Chris-alone DTI = **42.91%** — within ATR/QM 43% cap by 0.094 pp. PITI unchanged at $4,639.52. | **Survives ATR/QM**, no margin. Per Foote-Gerardi-Willen double-trigger framework, the household is one adverse-equity event from foreclosure danger in this state. 6 months of Dana-zero consumes ≈ $60K of reserves at projected burn, pushing toward the $80K Worst Case activation trigger. |

### Consolidated implication for the $700K target

All three scenarios pass the calc engine's mechanical tests; none blocks.
But each lands the household within a literature-informed risk margin of a
boundary that the corpus considers structural:

- Scenario 1 violates the climate-adjusted Realistic PITI ceiling.
- Scenario 2 drifts above that same ceiling on a slow-bleed cadence.
- Scenario 3 brings Chris-alone within 0.094 pp of the ATR/QM cap.

**Recommended posture (reinforces existing corpus-informed re-review):**
anchor target at the **$675-700K band**, not $700-720K. This preserves
3-5% PITI headroom against any single scenario and meaningful cushion if
two of the three land simultaneously (e.g., Dana takes extended leave
in the same quarter the insurance renewal raises premium).

**Result files preserved:**
`/tmp/stress-result-rate-shock.json`,
`/tmp/stress-result-climate-insurance.json`,
`/tmp/stress-result-income-shock.json`,
plus the per-year inputs and outputs under `/tmp/climate-insurance/`.

**Phase 3 completion criteria — re-verified:**
- 3 result JSON files exist in `/tmp/`. ✅
- The new stress-test section exists in `HOUSE-PURCHASE-GOAL-2026.md`. ✅
- Each scenario's narration cites a specific Zotero entry by title
  (Liebersohn-Rothstein + Fonseca-Liu / Ge-Johnson-Tzur-Ilan /
  Foote-Gerardi-Willen) and each cited title was verified present in
  Zotero via SQL during Phase 2. ✅

---

## Net deltas this loop run

| Artifact | Change |
|---|---|
| `~/Zotero/zotero.sqlite` | 5 URL fields upgraded to Tier 1 authorities; backup at `~/Zotero/zotero.backup-loop-20260516-182531.sqlite`. |
| `.planning/CITATION-COVERAGE.md` | New `## Audit 2026-05-16` section with 14 verified modules + 5 concerns + remediation list. |
| `.planning/HOUSE-PURCHASE-GOAL-2026.md` | New `## Literature-Grounded Stress Tests (2026-05-16)` section with 3 scenarios + verdicts + consolidated implication. |
| `.planning/MORTGAGE-OPS-LOOP-PROGRESS.md` | Per-iteration log file (new). |
| `.planning/MORTGAGE-OPS-LOOP-REPORT.md` | This file (new). |
| `/tmp/stress-result-*.json` | Three deterministic result captures. |
| `/tmp/zotero_url_updates.sql` | The SQL script used for Phase 1. |

## Follow-up actions (do NOT require another loop run)

1. **High-priority** — Add the two missing Zotero entries documented in C-1
   and C-2, OR amend the matrix's "Coverage gaps — RESOLVED" block to
   match reality. Same tag (`coverage-gap-fill`) either way.
2. **Medium-priority** — Update `lib/rules/fha_mip.py` docstring per the
   text suggested in C-4 (operative cite to Handbook 4000.1 §II.A.8.b;
   keep ML 2023-05 as historical reference).
3. **Low-priority** — Add `12 CFR §1026.22` Cornell-Law entry to Zotero
   for C-3 polish. Skip if convenient.
4. **Calendar** — Annual ATR/QM threshold refresh ~2026-11 when CFPB
   publishes the 2027-indexed combined rule (per C-5).
5. **Calendar** — Re-run this loop when the calc engine gains new modules
   or the corpus has been substantially expanded.

## Anti-shortcut compliance

The loop instructions included specific anti-shortcut clauses; this run
honored each:

- **"Do not output CONVERGED to escape a stuck phase"** — every step in
  every phase completed; no stuck phases.
- **"Do not skip the SQLite backup in Phase 1"** — backup taken before any
  write; path and byte-count above.
- **"Do not report a Phase 2 concern without proposing a specific
  remediation"** — every C-#  has explicit remediation text.
- **"Do not cite Zotero entries by guess"** — every cited title in Phases 2
  and 3 was first verified via SQL `LIKE` against `itemDataValues` keyed
  to `fieldID=1` (title).
- **"Do not cite numbers in Phase 3 narration that aren't from the
  script's stdout JSON"** — every dollar figure in the Phase 3 narration
  is drawn from `/tmp/stress-result-*.json`.

---

*All three phases meet their completion criteria. This report exists at
the path required by the loop's convergence condition.
`MORTGAGE-OPS-LOOP-PROGRESS.md` carries the per-iteration trail.*
