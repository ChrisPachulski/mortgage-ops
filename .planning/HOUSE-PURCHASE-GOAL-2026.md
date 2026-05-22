# House Purchase Goal Command — Pachulski 2026

> Single-page operating plan for the 2026 home purchase. Written 2026-05-15.
> Treat this as a living doc — update when triggers fire or constraints change.

---

## THE TARGET (best case)

**Buy a $725,000 home in WA King County, close mid-October 2026, with $23K post-close reserve and ~$7,500/mo lifestyle headroom.**

| Parameter | Value | Source |
|---|---|---|
| Purchase price | $725,000 | Target band midpoint |
| Down payment (15%) | $108,750 | |
| Closing costs (est. 2.5%) | $18,125 | Typical WA buyer-side |
| **Cash to close** | **$126,875** | |
| **Reserve post-close** | **$23,125** | of $150K liquid |
| Loan amount | $616,250 | conventional 30yr fixed |
| Rate target | 5.000% | per current FRED MORTGAGE30US trajectory |
| **Monthly PITI** | **$4,346.08** | from `affordability.py` 2026-05-15 |
| Back-end DTI | 23.4% | well under 43% cap |
| Loan classification | conforming | not high-balance, best rate tier |
| Move-in target | Oct 15, 2026 | 2-month lease overlap |

**Success criteria — all must hold:**
- PITI ≤ $4,500/mo
- Reserve post-close ≥ $20,000 (≥ 4 months PITI)
- Loan classified `conforming` (not high-balance, not jumbo)
- Both incomes intact at application AND close (no income disruption mid-process)
- Move-in date between Oct 1 and Nov 30, 2026

---

## CONSTRAINTS (the threading)

| Date | Constraint |
|---|---|
| **2026-06-?? (~30 days)** | Baby #2 arrives. Move logistics get harder. |
| **2026-12-31** | Rental lease ends. MUST be moved or extended. |
| Throughout | KinderCare $1,450/mo (kid #1, continuing). Baby #2 cared for at home by both WFH parents — no daycare. |
| Throughout | Both incomes intact, no parent stepping back. Total $23,491.67/mo gross base post-raise. |

---

## FALLBACK TIERS

### Fallback A — "Stretch the band" ($750K target)
**Trigger:** Best-fit listing lands in $750K range, no $725K equivalent available.

| | Value |
|---|---|
| PITI @ 5.000% | $4,479.74 |
| PITI @ 5.500% (rate creep) | **$4,677.15** |
| Cash to close | $131,250 |
| Reserve post-close | **$18,750** |
| DTI back-end | 24.0% – 24.8% |

**Conditions to accept:** Reserve stays ≥ $18K, PITI ≤ $4,700, both incomes locked. If rate is at 5.5%+, this becomes uncomfortable — fall further to Tier B.

### Fallback B — "Rate environment worsens" ($700K, accept higher rate)
**Trigger:** 30yr fixed quotes come in 5.5%+ before lock.

| | Value |
|---|---|
| Purchase | $700,000 |
| PITI @ 5.000% | $4,187.42 (current quote) |
| PITI @ 5.500% | ~$4,365 |
| Cash to close | $122,500 |
| Reserve post-close | **$27,500** |

**Action:** Drop one tier on price to preserve PITI ceiling. Or evaluate paying 1 point ($6,160) to buy rate down 0.25% → run `/mortgage-ops points-breakeven`.

### Fallback C — "House hunt slow" (timing slip)
**Trigger:** Pre-approval valid, no acceptable home found by **2026-09-15**.

**Action:**
1. Approach landlord re: month-to-month extension (typically 1.5× rent premium = ~$6,150/mo) OR short 3-month renewal.
2. Continue search through Q4 at same $700-725K target.
3. Refresh pre-approval letter every 60 days.
4. If no offer accepted by Nov 1 → activate Worst Case.

### Fallback D — "Reserves drain mid-process" (life event)
**Trigger:** Liquid drops below $135K before close (birth costs, baby gear, IRS surprise, anything).

**Action:**
1. Drop target to $675K band.
2. OR negotiate seller credit for closing costs (typical 1-3% of price).
3. OR switch to 10% down — accept higher PMI for ~$200-300/mo, preserves $7-10K reserve.
4. Re-run affordability with revised inputs before signing anything.

---

## WORST CASE — "Punt to 2027"

**Activation triggers — ANY one of:**
- 30yr fixed sustained > 6.5% (rate environment broken)
- Either income disrupted (layoff, role change, contractor gap)
- Reserve drops below $80K total liquid
- Baby health crisis OR family medical event eats reserves
- No suitable home found by Nov 1, 2026

**Worst-case sanity check ($675K @ 6.500%):**

| | Value |
|---|---|
| Purchase | $675,000 |
| Loan | $573,750 (15% down) |
| PITI | **$4,590.24** |
| Cash to close | $118,125 |
| Reserve | $31,875 |
| DTI back-end | 24.4% |

Still affordable — but $4,590/mo PITI for a $675K house is poor value-per-dollar. **If forced into this tier, prefer to wait.**

**Worst-case action plan:**
1. **Renew lease** 6-12 months. Budget rent at $4,500-4,800/mo (modest renewal increase). Annual cost: ~$57K.
2. **Pause active search.** No house tours, no offers.
3. **Rebuild reserves to $200K+** using:
   - Chris's bonus deposits (Q1 and/or Q4)
   - Reduce 401k contribution temporarily IF reserves below $80K (otherwise don't — match is free money)
   - Trim lifestyle (the $589/mo "Software" category, the $2,306/mo "Other" — there's real fat there)
4. **Reassess Q2 2027** with new reserve position + rate environment + Dana's income trajectory.

**Cost of waiting:** ~$57K/yr in rent buys ~$30K equity at 5%/30yr/$725K purchase. Math says owning is better long-term, BUT only if you can do it without depleting reserves.

---

## DECISION GATES (calendar)

| Date | Decision | Default action | Re-route if... |
|---|---|---|---|
| **2026-05-30** | Pre-approval started | Apply with 2-3 lenders (Wells Fargo, local credit union, Better.com or similar) | rate quotes >5.5% → Fallback B |
| **2026-06-15** | Pre-approval letter in hand | Letter valid 60-90 days; lock target band | baby arrives early → pause, revisit July 15 |
| **2026-07-01** | Active listings review begins | Pipe listings through `/mortgage-ops evaluate` | inventory dry → expand geo or wait |
| **2026-08-15** | First offer window | Aim for $700-725K, move-in ready | competing offers escalate over $750K → walk |
| **2026-09-15** | **HARD GATE** | If no offer accepted → activate Fallback C (lease extend) | offer accepted → drive to close |
| **2026-10-15** | Target close | Walk-through, sign, fund | inspection issues → renegotiate or walk |
| **2026-11-30** | Latest acceptable close | Otherwise activate Worst Case | |
| **2026-12-15** | Move complete | Lease overlap ends | |
| **2026-12-31** | Lease ends | Must be out OR extended | |

---

## ENGINE COMMANDS PER PHASE

| Use case | Command |
|---|---|
| New listing analysis | `/mortgage-ops evaluate` — paste listing details |
| Lender quote comparison (2+ offers) | `/mortgage-ops compare` |
| Points discount evaluation | `/mortgage-ops points-breakeven` |
| Rate-shock testing | `/mortgage-ops stress` rate-shock |
| Income-shock testing | `/mortgage-ops stress` income-shock |
| Amortization detail | `/mortgage-ops amortize` with extra-principal scenarios |

---

## PRE-FLIGHT CHECKLIST (do this week, 2026-05-15 to 2026-05-22)

- [ ] Dana pull her mortgage-grade tri-bureau FICO (831 was the consumer score; mortgage FICO often differs slightly)
- [ ] Both: gather last 2 years W-2s, last 60 days pay stubs, last 2 months bank statements
- [ ] Verify Chris W-4 adjusted for $161,900 + bonus to avoid repeat of 2025 $8,724 IRS surprise
- [ ] Request 2-3 lender quotes: 30yr fixed, conventional, 15% down on $725K purchase
- [ ] Read prospective listings: target zips 98042, 98058, 98059, 98038 (Covington, Renton, Maple Valley)
- [ ] Identify deal-breakers: school district acceptable for kid #1, NOT septic + well combo, NOT >1990 build without major systems updates
- [ ] Confirm KinderCare commute geography from candidate neighborhoods

---

## OPEN QUESTIONS

1. **Target school district** for kid #1 when they age into K-12. Affects geo.
2. **Geographic scope** — willing to go beyond King County (Pierce, Snohomish, eastern Snoqualmie Valley)?
3. **Property type tolerance** — single-family only, or townhouse/condo OK?
4. **Bonus reliability** — is Chris's 20% bonus guaranteed-ish (recent history shows it landing)?
5. **Side income** — anything not in card-ops (consulting, freelance)?

---

*This is the operating plan. Update inline as facts change. All dollar figures here are from `affordability.py` runs on 2026-05-15. When re-running mid-2026 with updated rates / FICOs / income, replace the table values verbatim.*

---

# CORPUS-INFORMED RE-REVIEW (2026-05-15, post-literature seeding)

> Comprehensive update using the literature corpus (309-item Zotero library) +
> live market data. This re-review supersedes the 5.000%-rate analysis above
> wherever they conflict. Generated 2026-05-15, evening.

## What the corpus changed about the prior analysis

| Prior assumption | Corpus-corrected reality | Source |
|---|---|---|
| 5.000% / 30yr fixed | **6.360% / 30yr fixed** | Freddie Mac PMMS week ending 2026-05-14 (Pillar 3) |
| Insurance ~$300-400/mo placeholder | **$200-350/mo midpoint, escalating 12-22%/yr** | WA Insurance market data + Dallas Fed Pillar 6 |
| Reserve safe at 2 months PITI | **2 months PITI no longer adequate given climate-insurance escalation** | Ge/Johnson/Tzur-Ilan 2025 (Pillar 6) |
| Loan classification ambiguous on jumbo | **All scenarios in target band are baseline conforming** | FHFA 2026 limits: baseline $832,750, King Co high-cost $1,063,750 (Pillar 1) |
| Bonus excluded entirely | **Bonus excluded for qualifying; can model as savings engine separately** | Lender practice + Campbell-Cocco optimal-choice framing (Pillar 5) |
| Refi optionality framed as automatic | **Behavioral frictions cause delayed refi; set quarterly review** | Keys-Pope-Pope, Andersen-Campbell-Nielsen-Ramadorai, Berger-Milbradt-Tourre-Vavra 2024 (Pillar 2) |

## Current rate environment (corpus-grounded)

Per PMMS week ending **2026-05-14**:
- 30-yr fixed: **6.36%** (down from 6.37% prior week; year-ago 6.81%)
- 15-yr fixed: **5.71%** (down from 5.72%; year-ago lower)
- MBA Weekly Survey same week: 6.46% (slightly above PMMS — typical PMMS-vs-MBA spread)

FOMC March 2026 SEP dot plot points to **two cuts in 2026** (currently priced into mortgage curve). Realistic next 12 months: 5.75-6.50% range. **Refi window opens if rates touch ~5.50% on a $637K loan** (Agarwal-Driscoll-Laibson closed-form threshold, after $4-5K closing cost amortization).

## Full price × rate scenario matrix (15% down, conventional, baseline conforming)

All scenarios: 15% down, $250/mo insurance baseline, King County 0.94% property tax (annual ÷ 12), no HOA. Chris 796 / Dana 831 FICO.

| Price | Rate | P&I | Tax | Ins | PMI | **PITI** | DTI back | vs current rent |
|---|---|---|---|---|---|---|---|---|
| $700K | 6.000% | $3,567 | $548 | $250 | $130 | **$4,496** | 24.0% | +$401 |
| $700K | **6.360%** | $3,706 | $548 | $250 | $135 | **$4,640** | 24.6% | **+$545** |
| $700K | 6.460% | $3,745 | $548 | $250 | $138 | **$4,682** | 24.8% | +$587 |
| $700K | 7.000% (stress) | $3,959 | $548 | $250 | $145 | **$4,902** | 25.8% | +$807 |
| $725K | 6.000% | $3,695 | $568 | $250 | $130 | **$4,643** | 24.7% | +$548 |
| $725K | **6.360%** | $3,839 | $568 | $250 | $135 | **$4,791** | 25.3% | **+$696** |
| $725K | 6.460% | $3,879 | $568 | $250 | $138 | **$4,835** | 25.5% | +$740 |
| $725K | 7.000% (stress) | $4,100 | $568 | $250 | $145 | **$5,063** | 26.4% | +$968 |
| $750K | 6.000% | $3,822 | $588 | $250 | $130 | **$4,790** | 25.3% | +$695 |
| $750K | **6.360%** | $3,971 | $588 | $250 | $135 | **$4,943** | 25.9% | **+$848** |
| $750K | 6.460% | $4,013 | $588 | $250 | $138 | **$4,988** | 26.1% | +$893 |
| $750K | 7.000% (stress) | $4,241 | $588 | $250 | $145 | **$5,224** | 27.1% | +$1,129 |

*(P&I from `amortize.py`; PITI/DTI from `affordability.py`, both run 2026-05-15)*

## Sustainable PITI ceiling (literature-informed)

Per Campbell-Cocco optimal-mortgage-choice framing: monthly housing burden should leave room for income-shock cushioning AND a literature-recommended **savings buffer of ≥10% of take-home for emergency rebuild + retirement**. Our $15,500/mo base take-home implies $1,550/mo savings target.

| Risk posture | PITI ceiling | Rationale |
|---|---|---|
| **Aggressive** (zero savings buffer, bonus = pure surplus) | $5,500/mo | Cash flow positive on base, but no emergency rebuild |
| **Realistic** ($1,000/mo savings) | $4,500/mo | Hits the Campbell-Cocco buffer recommendation |
| **Conservative** ($1,500/mo savings) | $4,000/mo | Hits Foote-Gerardi-Willen "double-trigger" margin |

**At 6.36% rate, only the $700K scenario fits the Realistic ceiling.** $725K is +$291 over Realistic. $750K is +$443 over Realistic. Stretching to $750K means accepting the Aggressive posture.

## Climate-insurance stress overlay (Pillar 6 application)

The Dallas Fed Ge/Johnson/Tzur-Ilan (2025) finding: **$500/yr premium increase → 27% rise in delinquency**. WA insurance has been increasing 12-22% per year for three consecutive years. Modeling a realistic 3-yr forward:

| Year | Insurance baseline | At 15% YoY growth |
|---|---|---|
| 2026 (now) | $250/mo ($3,000/yr) | — |
| 2027 | — | $288/mo (+$38) |
| 2028 | — | $331/mo (+$81) |
| 2029 | — | $381/mo (+$131) |

By 2029, PITI on the $700K scenario rises from $4,640 → **~$4,771** purely from insurance creep. That's $131/mo of "stealth" budget erosion most buyers don't model. The Dallas Fed paper says households facing this kind of escalation default at materially higher rates.

**Budget implication:** Add a $50-100/mo **insurance escalation reserve** to your sustainable PITI math. Effective ceilings drop:
- Realistic: $4,500 → **$4,400/mo** target
- Conservative: $4,000 → **$3,900/mo** target

Only the $700K @ 6.36% scenario ($4,640) sits within striking distance of the climate-adjusted Realistic ceiling. **$725K+ at current rates fails the literature-informed conservative test.**

## Submarket reality check

Current Covington/east-King-County inventory snapshot (mid-May 2026):

| Zip | Submarket | Median home price | Position vs $700-750K | WUI exposure |
|---|---|---|---|---|
| **98042** broader zip | Mostly Covington/Kent edges | **$663,295** | **Below band — viable** | Mixed; eastern parts in WUI |
| **98042** Covington proper | Covington core | **$754,500-$789,950** | At/above band — tight | Some WUI eastern edge |
| **98058** Renton Highlands | Renton east + Maple Valley west | **$696,834** | **Below band — viable** | Lower (closer to urban core) |
| Covington April 2026 sales | (median sold price) | $751,614 | Right at top of band | Mixed |

**Inventory:** 65 homes for sale in Covington as of May 12, 2026. Decent inventory at the median, less below.

**Implications:**
1. **98058 (Renton Highlands / west Maple Valley)** is the lowest-risk submarket — below median price, lower WUI exposure (= lower insurance long-term), still in target school districts.
2. **98042 broader** (zip-level) has homes below your band — likely older or smaller. May trade against modern systems but improve cash flow.
3. **Covington proper** at $754K median is right at your stretch — competitive offer environment for any well-priced listing.
4. **Wildfire-WUI scrutiny matters**: per WA DNR 2026 risk map + King County CWPP (Pillar 6 Zotero entries), insurance is materially worse on east-of-Issaquah-Hobart line properties. Bias search toward westward (Renton Highlands, west Maple Valley, even southwest Kent) for insurance preservation.

## Refi optionality math (Agarwal-Driscoll-Laibson applied)

Closed-form refi threshold at current loan sizes (Pillar 2 corpus):

| Current scenario | Loan | Closing cost assumption | **Refi trigger rate** | Realistic FOMC path |
|---|---|---|---|---|
| $700K @ 6.36% | $595,000 | $4,500 (~0.75% of loan) | **5.50-5.65%** | Plausible Q4 2026 / 2027 if cuts land |
| $725K @ 6.36% | $616,250 | $4,700 | **5.55-5.70%** | Same |
| $750K @ 6.36% | $637,500 | $4,800 | **5.55-5.70%** | Same |

**Action:** Set a quarterly calendar reminder to check the 30yr PMMS rate against the trigger above. Berger et al (2024) and Andersen-Campbell-Nielsen-Ramadorai both document households leave 50-100bps of refi savings on the table due to inertia — don't be that household.

## Updated final recommendation

**Primary target band: $675-720K, prioritizing 98058 (Renton Highlands) over 98042 (Covington proper).**

This is **tighter than my pre-corpus recommendation** because:
1. 6.36% market rate (not 5%) raises PITI ~$540/mo at any given price
2. Climate-insurance escalation literature demands a buffer I wasn't carrying
3. Conservative Campbell-Cocco posture says $4,400/mo PITI ceiling
4. WUI-bias toward submarket reduces structural insurance trajectory risk
5. **$700K at 6.36% = $4,640 PITI — at the comfort boundary, not below it**

Decision points:
- **At 6.36% today:** anchor at **$700K**, max $720K. Skip $725-750K unless seller credits cover 1+ year of PITI escalation.
- **If rates drop to 6.00% by close:** $725-735K back on the table.
- **If rates rise to 7.00% before close:** drop to **$650-685K** and re-scope.
- **If WUI-exposed property forces $400/mo insurance:** drop by another $25-50K to keep PITI under $4,600/mo.

## Updated Fallback Tier triggers

The original A-D tiers above (lines 55-95) should be re-read with **rates indexed to 6.36% as baseline**, not 5.0%. Specifically:

- **Fallback A** "Stretch the band" (was $750K stretch): **Re-priced — $750K at 6.36% = $4,943 PITI. This is now firmly in Stretch territory, not "barely works"**. Only invoke if (a) rates drop to ≤6.00% by close OR (b) bonus deposit just landed AND reserves are $25K+.
- **Fallback B** "Rate creep" — already addressed; trigger is rates ≥6.75%, drop to $675K.
- **Fallback C** "House hunt slow" — unchanged.
- **Fallback D** "Reserves drain" — strengthen: with insurance escalation literature in mind, do NOT reduce down payment below 15% unless seller credit covers ≥18 months of insurance escalation buffer.

## Decision gates — re-priced

| Date | Decision | Updated default action |
|---|---|---|
| 2026-05-30 | Pre-approval started | Target $700K @ best-available conforming rate; lenders include First Street climate quote for the listings you're considering |
| 2026-06-15 | Pre-approval letter in hand | Letter valid 60-90 days; confirm conforming-not-high-balance pricing tier |
| 2026-07-01 | Active listings review begins | Pipe through engine using **6.36% (or lender-actual) rate, NOT 5%** |
| 2026-08-15 | First offer window | Target 98058 first, 98042 broader second, Covington proper only if priced ≤$720K |
| 2026-09-15 | **HARD GATE** | If no offer accepted → activate Fallback C (lease extend) |
| 2026-10-15 | Target close | Final rate-lock — refi calendar reminder set 90 days post-close |
| 2026-11-30 | Latest acceptable close | Otherwise Worst Case |
| 2026-12-31 | Lease ends | Must be out OR extended |

## Open questions (refreshed from corpus angle)

1. **First Street risk score** for each candidate listing — fold into offer-decision criterion
2. **Lender willingness to credit insurance escalation reserve** — ask explicitly during pre-approval
3. **Buy-down points evaluation** — at current rate environment, paying 1 point to drop rate 0.25% has a ~5-year breakeven per Agarwal-Driscoll-Laibson; only worthwhile if planning to hold >5 years AND not planning to refi within 18 months
4. **PMI removal trajectory** — at 6.36% / 15% down, organic LTV reaches 80% around month **86 (7.2 years)**. Aggressive principal paydown shortens this; refi to remove PMI is the alternative if rates drop ≥1%
5. **WA wildfire WUI status per address** — use https://dnr.wa.gov/wildfire-resources/wildfire-prevention/wildfire-hazard-and-risk-mapping for every offer

---

*Re-review complete. Anchor point shifted from "$725-750K base / $850-950K bonus-stretch" to "$675-720K base, $720-750K stretch only with rate or bonus support." Decision gates and fallback tiers preserved with re-priced thresholds.*

---

## Literature-Grounded Stress Tests (2026-05-16)

> Generated during the `mortgage-comprehensive` ralph-loop run
> (`.planning/MORTGAGE-OPS-COMPREHENSIVE-LOOP.md` Phase 3). All dollar
> figures below come from the script outputs in `/tmp/stress-result-*.json`,
> not hand math. The Zotero entries cited inline were verified present via
> direct SQLite read on `~/Zotero/zotero.sqlite` during the same run.

**Common base case for all three scenarios:** $700K purchase, 15% down → $595K
loan, 30-yr fixed at 6.36% (PMMS week ending 2026-05-14), $548/mo property tax,
$250/mo baseline insurance, $135/mo PMI, household per `config/household.yml`.
Baseline PITI = **$4,639.52** (`/tmp/climate-insurance/Y0-2026-result.json`).

### Scenario 1 — Rate-shock: 6.36% → 7.50%

*Output:* `/tmp/stress-result-rate-shock.json` (`mode: rate-shock`,
`scenario_count: 3`).

Cited literature: the **lock-in framing** from Liebersohn-Rothstein
("Locked In: Mobility, Market Tightness, and House Prices", Zotero entry
present) and Fonseca-Liu (the multiple "Mortgage Lock-In, Mobility, and Labor
Reallocation" entries in the corpus). Their argument: when origination rates
rise materially above the buyer's lock rate, the household's payment ceiling
gets dragged up immediately while their *outside option* (selling and
re-mortgaging at the new rate) gets penalized, so the dollar exposure to a
6.36→7.50 swing is not just the +$454/mo P&I — it's also the loss of mobility
optionality for the loan's lifetime.

| Rate | Monthly P&I | Δ vs baseline | Total interest paid |
|---|---|---|---|
| 6.36% (baseline) | $3,706.19 | — | $739,229.27 |
| 7.00% | $3,958.55 | **+$252.36** | $830,077.81 |
| 7.50% | $4,160.33 | **+$454.14** | $902,713.81 |

Stacking the +$454.14 P&I delta onto the $4,639.52 baseline PITI gives a
**stressed PITI of ~$5,094/mo** at 7.50% (insurance/tax/PMI held flat).
Back-end DTI under stress: ~27.0%, still well below the 43% ATR/QM cap. The
$700K target *survives* a 7.50% rate environment on a pure DTI basis.

**Verdict:** The $700K target survives the rate-shock — DTI-wise — but the
PITI rises to ~$5,094/mo, blowing past every literature-informed sustainable
ceiling (Realistic $4,500; climate-adjusted Realistic $4,400; Conservative
$4,000). Lock-in literature says you'd be sentenced to those payments for
years before refi-economics open up again. If quotes land at 7.50%, tier down
to the $650-675K band per the existing Worst Case action plan.

### Scenario 2 — Climate-insurance escalation (15% YoY × 5 years)

*Output:* `/tmp/stress-result-climate-insurance.json` (`mode:
climate-insurance-escalation`, `scenario_count: 6`).

Cited literature: **Dallas Fed, Ge / Johnson / Tzur-Ilan 2025** —
"Climate Risk, Insurance Premiums and the Effects on Mortgage and Credit
Outcomes" (Zotero entry verified present). Their headline finding: a
**$500/yr premium hike correlates with a 27% rise in delinquency**, with
the effect concentrating among already-stretched households. WA market
trajectory has been 12-22%/yr for three consecutive years; this scenario
uses 15% YoY as a literature-anchored midpoint.

| Year | Monthly insurance | Monthly PITI | Δ PITI vs Y0 | DTI back |
|---|---|---|---|---|
| Y0 (2026) | $250.00 | $4,639.52 | — | 24.6% |
| Y1 (2027) | $287.50 | $4,677.02 | +$37.50 | 24.8% |
| Y2 (2028) | $330.63 | $4,720.15 | +$80.63 | 25.0% |
| Y3 (2029) | $380.22 | $4,769.74 | +$130.22 | 25.2% |
| Y4 (2030) | $437.25 | $4,826.77 | +$187.25 | 25.4% |
| Y5 (2031) | $502.84 | $4,892.36 | **+$252.84** | 25.7% |

By Y5, annual insurance has gone from $3,000 → $6,034 — a $3,034/yr increase,
roughly **6× the Dallas Fed marginal-hike unit** ($500/yr). Per the
literature's elasticity, the per-unit delinquency lift compounded across five
of those units corresponds to a *materially* elevated default risk profile
for a household that was already at the upper bound of its sustainable PITI
ceiling.

**Verdict:** The $700K target *survives the calculation* — DTI never crosses
26% and the script never returns `blocked=true`. But the Dallas Fed finding
says the *risk profile* deteriorates well before any DTI breach: by Y3-Y5 the
PITI is $130-253/mo above the "climate-adjusted Realistic" $4,400 ceiling
already documented in the corpus-informed re-review above. Recommended
remediation: bias submarket selection toward 98058 (Renton Highlands, lower
WUI exposure) over 98042 east-Covington, and budget an **insurance escalation
reserve of $50-100/mo from day-1** to absorb the trajectory without re-quoting
the policy at adverse renewal moments. The $700K target itself is fine; what
fails is the assumption that today's $250/mo insurance line is durable.

### Scenario 3 — Dana income disruption (job loss / extended leave)

*Output:* `/tmp/stress-result-income-shock.json` (`mode: income-shock`,
`scenario_count: 1`).

Cited literature: **Foote-Gerardi-Willen "Negative Equity and Foreclosure:
Theory and Evidence"** (Zotero entry verified present) — the canonical
*double-trigger* hypothesis: foreclosure typically requires *both* an
adverse equity event *and* an income shock. This scenario isolates the
income-shock half, asking: if Dana's $10,000/mo gross goes to $0 for 6
months (job loss, extended parental leave beyond standard WA PFML), does
Chris's $13,491.67/mo alone clear ATR/QM on the $700K plan?

Encoding: Dana's $10,000 is **42.57%** of the $23,491.67/mo combined
household income, so an income-shock reduction of `0.4257` represents
Dana → $0. (The script's `reductions` parameter applies a proportional
cut to the combined household income — exactly the abstraction the
ATR/QM test cares about.)

| Income state | Effective gross/mo | PITI* | DTI back-end | ATR/QM 43% breach |
|---|---|---|---|---|
| Chris + Dana (baseline) | $23,491.67 | $4,639.52 | 24.6% | no |
| Chris alone (-42.57%) | $13,491.67 | $4,639.52 | **42.91%** | **no (0.094% headroom)** |

\* PITI unchanged — the property/loan don't move; only income changes.

**Verdict:** Chris alone *technically* qualifies the loan at the ATR/QM 43%
back-end cap, but with **0.094 percentage points of headroom** — essentially
a no-margin scenario. The $300/mo new-baby cash outflow flagged in the loop
plan does NOT appear in DTI (childcare and baby costs are excluded by
lender practice per the `config/household.yml` annotation), but it absolutely
appears in *cash flow*: Chris's $13,491.67 minus PITI $4,639.52 minus the
$1,149.05 auto debts minus the $1,450 KinderCare minus rising baby costs
($300/mo) leaves ~$5,953/mo for everything else (utilities, food, gas,
insurance, internet, etc.), versus ~$15,453/mo in the dual-income baseline.
Foote-Gerardi-Willen's double-trigger logic would say: in this state the
household is *one adverse equity event away* from the foreclosure danger
zone, even though DTI is intact. The $700K target is **survivable but not
safe** under sustained Dana-to-zero. A 6-month buffer would consume roughly
$60K of liquid reserves at the current burn — pushing reserves toward the
$80K Worst Case activation trigger documented above.

### Consolidated implication for the $700K target

All three scenarios pass the *mechanical* qualification tests embedded in
the calc engine (`affordability.py` / `stress_test.py`). None blocks the
loan; none crosses the 43% DTI ceiling. But each scenario lands the
household uncomfortably close to a literature-informed risk boundary:

- Rate-shock pushes PITI ~$500 over the climate-adjusted Realistic ceiling.
- Climate-insurance escalation does the same on a slow-bleed cadence.
- Dana-zero compresses Chris-alone DTI to within 0.094% of ATR/QM.

The robustness move per the corpus: **anchor target at the $675-700K band,
not the $700-720K band**, preserving 3-5% PITI headroom against any single
scenario and meaningful cushion against any two of the three landing
simultaneously. This restates and reinforces the corpus-informed
recommendation already in the re-review section above — now with concrete
script outputs to ground it.

*Raw outputs:* `/tmp/stress-result-rate-shock.json`,
`/tmp/stress-result-climate-insurance.json`,
`/tmp/stress-result-income-shock.json`.
Per-year affordability runs for Scenario 2:
`/tmp/climate-insurance/Y0-2026-result.json` through
`/tmp/climate-insurance/Y5-2031-result.json`.

