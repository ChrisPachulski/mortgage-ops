# Phase 14: Property Analysis Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 14-property-analysis-pipeline
**Areas discussed:** DP matrix sparsity, Verdict tie-breaks, Stress fan-out scope, Refi baseline

---

## DP matrix sparsity

### Q1: Matrix shape — how should ineligible cells appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit ineligible rows | Every cell is a ProgramResult with eligible=False + blocker_reasons populated. 24 cells (or 30 w/ jumbo). Best for golden-fixture diffs. | ✓ |
| Sparse — skip ineligible | Matrix only contains eligible cells. Smaller payload but less explainable in report. | |
| Per-program collapsed | Top-level `programs: dict[str, ProgramOutcome]`; whole program collapses when blocked at program level. | |

**User's choice:** Explicit ineligible rows
**Notes:** Locked as D-14-MATRIX-01.

### Q2: For ineligible rows, what should the numeric fields carry?

| Option | Description | Selected |
|--------|-------------|----------|
| Computed anyway | Fill all fields with the value they WOULD have if rules were waived. Easier to show 'what blocked you'. | ✓ |
| None / null | Numeric fields are None for ineligible cells. Smallest payload. | |
| Hybrid: stop at first blocker | Compute only as far as the first failed predicate, then short-circuit. | |

**User's choice:** Computed anyway
**Notes:** Locked as D-14-MATRIX-02. Mirrors affordability.py blocker-cascade convention with full numerics.

### Q3: Where does the jumbo branch appear in the matrix?

| Option | Description | Selected |
|--------|-------------|----------|
| 5th program row when triggered | When price > zip-specific conforming limit, append `Jumbo30` as a 5th row with its own 6-DP sweep. | ✓ |
| Always present, eligible=False when below limit | Schema-stable across listings; PRICE-BELOW-JUMBO-FLOOR blocker when below. | |
| Replace conventional when triggered | Conv30/Conv15 removed and replaced by Jumbo30 when triggered. | |

**User's choice:** 5th program row when triggered
**Notes:** Locked as D-14-MATRIX-03. Final matrix = 30 cells when jumbo applies.

---

## Verdict tie-breaks

### Q1: How should 'FHA-only-with-MIP-burden → WATCH' be quantified?

| Option | Description | Selected |
|--------|-------------|----------|
| FHA monthly MIP > $300/mo | Fixed dollar threshold. Falsifiable, easy to test. | ✓ |
| FHA PITI > Conv PITI × 1.10 | Comparative against hypothetical Conv. Requires computing both even when Conv blocked. | |
| FHA MIP > 25% of monthly PITI | Ratio-based. Falsifiable per-listing without baseline computation. | |
| Defer to planner / research | Researcher pulls HUD/MBA heuristic before planner codes the threshold. | |

**User's choice:** FHA monthly MIP > $300/mo
**Notes:** Locked as D-14-VERDICT-01. Researcher may swap if a credible published heuristic is found (this is the only verdict threshold that's data-driven, per Claude's Discretion list).

### Q2: How should 'stress-fails-income-shock → WATCH' fire?

| Option | Description | Selected |
|--------|-------------|----------|
| Any eligible program fails income-shock | Conservative — fire WATCH if income drops 30% and any eligible cell breaches DTI ceiling. | ✓ |
| All eligible programs fail income-shock | Only fire WATCH if every eligible-at-preferred-DP program breaks. Less noisy. | |
| Majority (>50%) fail | Mid-ground. | |

**User's choice:** Any eligible program fails income-shock
**Notes:** Locked as D-14-VERDICT-02. Most protective verdict; conservative bias.

### Q3: When BOTH WATCH conditions and a GO condition fire — which wins?

| Option | Description | Selected |
|--------|-------------|----------|
| GO wins when any non-FHA eligible at preferred DP | MIP-only path is informational, not the user's actual recommendation. | ✓ |
| WATCH always wins over GO when ANY WATCH cond fires | Most conservative — any stress fail or MIP-only fragility downgrades to WATCH. | |
| Verdict.reasons captures both — verdict = highest severity | Severity order NO_GO > WATCH > GO; surface all triggered reasons. | |

**User's choice:** GO wins when any non-FHA eligible at preferred DP
**Notes:** Locked as D-14-VERDICT-03. Stress-fail WATCH still downgrades GO; the MIP-burden specifically does not when a non-FHA path exists.

---

## Stress fan-out scope

### Q1: Where in the matrix do stress tests run?

| Option | Description | Selected |
|--------|-------------|----------|
| User's preferred DP only | One stress block per program at user's `preferred_down_payment_pct`. ~12–15 stress rows. | ✓ |
| Every DP cell | Fan stresses across the full matrix: ~72–90 stress rows. | |
| Preferred + 20% benchmark | Two columns: user's preferred DP + 20%. ~24–30 stress rows. | |

**User's choice:** User's preferred DP only
**Notes:** Locked as D-14-STRESS-01. Report-bloat with no decision-relevant signal at every cell.

### Q2: Where does `preferred_down_payment_pct` live?

| Option | Description | Selected |
|--------|-------------|----------|
| Household model field | Add `preferred_down_payment_pct: Decimal` to `lib/household.py`. Default 0.20. | ✓ |
| Profile model field | Lives on separate Profile model (analysis-time preferences). | |
| Analyze() positional arg | Pass `preferred_dp_pct` as a top-level arg per call. | |

**User's choice:** Household model field
**Notes:** Locked as D-14-STRESS-02. Phase 14 ships `lib/household.py` as a new module.

### Q3: Which v1.0 programs offer ARM (for ARM peak-cap reset stress)?

| Option | Description | Selected |
|--------|-------------|----------|
| Conv 30 only (5/1 ARM variant) | Only Conv30 ships an ARM variant. Matches `lib/arm.py` Phase 5 scope. | ✓ |
| Conv 30 + Jumbo 30 | Both Conv30 and Jumbo30 offer 5/1 ARM. | |
| Defer to planner | Researcher reads lib/arm.py + Phase 5 plan to determine ARM coverage. | |

**User's choice:** Conv 30 only (5/1 ARM variant)
**Notes:** Locked as D-14-STRESS-03.

---

## Refi baseline

### Q1: The rate the user is being scanned AGAINST — which is it?

| Option | Description | Selected |
|--------|-------------|----------|
| User's matrix cell rate | Baseline = the rate they'd lock in TODAY for the (program, preferred_DP) cell. Forward-looking purchase + refi planning. | ✓ |
| User's existing-loan rate from Household | Baseline = `household.existing_mortgage_rate`. Refinance-from-existing scan. | |
| Both — dual scan | Two refi blocks: forward + backward. | |

**User's choice:** User's matrix cell rate
**Notes:** Locked as D-14-REFI-01. Refinance-from-existing is out of scope for v1.1.

### Q2: Where does today's rate come from for each (program, DP) matrix cell?

| Option | Description | Selected |
|--------|-------------|----------|
| FRED MORTGAGE30US for all 30yr programs | Conv30=MORTGAGE30US, Conv15=MORTGAGE15US, FHA/VA≈MORTGAGE30US, ARM=MORTGAGE30US-0.25. Single source-of-truth. | ✓ |
| Profile rate overrides | Default to FRED but allow per-program overrides from lender quotes. | |
| Pure profile-supplied | Always require profile.rates. No FRED in Phase 14. | |

**User's choice:** FRED MORTGAGE30US for all 30yr programs
**Notes:** Locked as D-14-REFI-02. Lender-quote overrides deferred to a future v1.2 "compare to lender quote" flow.

### Q3: Refi scan triggers — applied to FRED current or user's matrix lock rate?

| Option | Description | Selected |
|--------|-------------|----------|
| Both scan rates from FRED current | Faithful to ROADMAP wording. For non-30yr (Conv15, ARM) the scan diverges. | ✓ |
| Both scan rates from user's lock rate | Internally consistent with baseline lock-in; matches user intuition. Requires deviating from ROADMAP literal wording. | |
| Defer to planner | Researcher pulls a refi-trigger reference (Freddie Mac PMMS or similar). | |

**User's choice:** Both scan rates from FRED current
**Notes:** Locked as D-14-REFI-03.

---

## Claude's Discretion

- **Profile vs Household field allocation** (D-14-MODELS-02): researcher/planner decides whether `va_eligible`, `first_time_buyer`, `military_status` live on Household or on a separate Profile model.
- **AnalysisReport schema depth**: top-level holds matrix + stress + refi + tax + verdict; internal block structure is planner's call.
- **$300/mo MIP-burden swap**: if researcher finds a credible HUD/MBA citation, planner may swap with annotation in PLAN.md.
- **IRS Pub 936 over-cap formatting**: partial-deduction dollars vs "see CPA" callout — Phase 15 formatter problem; Phase 14 ships flag + first-year interest only.

## Deferred Ideas

- Refinance-from-existing-mortgage scan (`household.existing_mortgage_rate` based).
- Stress fan-out at every DP cell (72–90 stress rows).
- Lender-quote rate overrides (`profile.rate_overrides`).
- Comparative MIP-burden thresholds (FHA PITI > Conv × 1.10).
- Partial-deduction dollar computation for over-$750k loans (belongs in Phase 15 formatter).
