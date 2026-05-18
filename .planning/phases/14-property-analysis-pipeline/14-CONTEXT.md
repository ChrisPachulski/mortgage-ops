# Phase 14: Property Analysis Pipeline - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Compose v1.0 calc primitives (`lib/{affordability,amortize,arm,points,refinance,stress}.py` + IRS Pub 936 deductibility) into a single `analyze(listing, household, profile) → AnalysisReport` pipeline that:

- Fans out across 4 base programs (Conv30, Conv15, FHA30, VA30 when `profile.va_eligible`) plus a Jumbo30 5th row when `listing.price` exceeds the zip-specific conforming limit.
- Sweeps 6 down-payment scenarios (3 / 5 / 10 / 15 / 20 / 25%) per program — producing an explicit 4×6 (or 5×6 with jumbo) `DownPaymentMatrix`.
- Applies 3 stress tests (rate shock +2%, income shock −30%, ARM peak-cap reset) at the user's preferred-DP cell only.
- Scans points breakeven (1pt, 2pt drops) and refi opportunity (FRED current − 1% AND FRED current × 0.85).
- Computes IRS Pub 936 deductibility (first-year interest + $750k cap flag).
- Synthesizes a `GO | WATCH | NO_GO` verdict with falsifiable, predicate-cited reasons.

**In scope:** the pipeline + verdict logic + `lib/household.py` + `lib/property_verdict.py` + the AnalysisReport Pydantic contract + 3 golden-value hand-calculated fixtures.

**Out of scope:** the property-mode skill wiring (Phase 15), the markdown report formatter (Phase 15), PMI/MIP rate tables + FHA limits + jumbo cutoffs as YAML data (Phase 16 — Phase 14 reads from already-shipped `data/reference/*.yml`).

</domain>

<decisions>
## Implementation Decisions

### DownPaymentMatrix shape & sparsity

- **D-14-MATRIX-01:** **Explicit ineligible rows.** Every (program, DP%) cell is a `ProgramResult` with `eligible: bool` + `blocker_reasons: list[str]` populated. Total cells = 4 programs × 6 DPs = 24 (or 5 × 6 = 30 when jumbo triggers). Schema-stable for golden-fixture diffs across listings.
- **D-14-MATRIX-02:** **Numeric fields computed anyway on ineligible rows.** PITI, cash_to_close, DTI, LTV, PMI/MIP/funding_fee are all populated with the value they WOULD have if rules were waived. Lets the report cite the specific predicate breach with the actual number (e.g., "DTI=51% — DTI-CEILING-CONV"). Slight compute overhead per cell, but maximally explainable.
- **D-14-MATRIX-03:** **Jumbo as a 5th program row when triggered.** When `listing.price > conforming_limit_for_zip`, append `Jumbo30` as row 5 with its own 6-DP sweep (final matrix = 30 cells). Below the limit, Jumbo30 is omitted entirely (not present-but-ineligible). Conv30/Conv15 remain present regardless.

### Verdict tie-breaks (verdict synthesis)

- **D-14-VERDICT-01 (MIP-burden WATCH):** Fire WATCH when only FHA is eligible at preferred DP AND `FHA monthly MIP > $300/mo`. Fixed dollar threshold — falsifiable, no comparative baseline required.
- **D-14-VERDICT-02 (Stress-fail WATCH):** Fire WATCH when **ANY** eligible-at-preferred-DP program fails the income-shock stress (DTI breaches ceiling at income × 0.70). Conservative; most-protective verdict.
- **D-14-VERDICT-03 (Severity precedence):** **GO wins when any non-FHA program is eligible at preferred DP**, regardless of FHA MIP burden. The MIP-only path is surfaced as an informational reason but does not downgrade the verdict when a non-FHA eligible path exists. Stress-fail WATCH still downgrades a GO (so GO requires: non-FHA eligible at preferred DP AND no stress-fail across eligible programs).
- **D-14-VERDICT-04 (Reason citations):** Every verdict reason MUST cite both the predicate identifier (matching the existing `lib/rules/*` blocker code style — e.g., `DTI-CEILING-CONV`) and the computed numeric value that triggered it. Mirrors Phase 4 affordability blocker-cascade convention.

### Stress fan-out scope

- **D-14-STRESS-01:** **Stress tests run at user's preferred DP only**, not the full matrix. Output: 4–5 programs × 3 stresses = 12–15 stress rows per analysis. The full DP sweep stays purely program-level (eligibility + PITI per cell); stress fan-out at every cell was rejected as report-bloat with no decision-relevant signal (user only buys at one DP).
- **D-14-STRESS-02:** `preferred_down_payment_pct: Decimal` lives on the **Household Pydantic model** (`lib/household.py`, new this phase). User sets it once in their `household.yml`. Default = `Decimal("0.20")` when absent.
- **D-14-STRESS-03:** **ARM peak-cap reset stress fires for Conv30 only** (the 5/1 ARM variant per Phase 5 `lib/arm.py` scope). FHA/VA/Conv15/Jumbo30 do not produce an ARM-reset stress row.

### Refi baseline & today's-rate sourcing

- **D-14-REFI-01:** **Baseline lock rate = user's matrix cell rate** (the rate they'd lock in TODAY for the given program × DP). The analysis is forward-looking purchase + refi planning; the household's existing mortgage rate is NOT the baseline (a refinance-from-existing scan is out of scope for Phase 14).
- **D-14-REFI-02:** **Today's rate per program sourced from FRED via `lib/fred_cache.py`:**
  - Conv30 = `MORTGAGE30US`
  - Conv15 = `MORTGAGE15US`
  - FHA30, VA30 = `MORTGAGE30US` (acceptable v1.0 proxy)
  - Conv30 ARM 5/1 = `MORTGAGE30US − 0.25` heuristic
  - Jumbo30 = `MORTGAGE30US` (acceptable v1.0 proxy)
- **D-14-REFI-03:** **Refi scan triggers both come from FRED current** per ROADMAP literal wording — scan at `(FRED_current − 1.00)` AND `(FRED_current × 0.85)`. For 30yr programs these equal the user's lock; for Conv15 / ARM they diverge (a defensible projection downstream from "this is what the broader market would have to do for a refi to be worth it").

### Models & file landings

- **D-14-MODELS-01:** Phase 14 ships **`lib/household.py`** (new) — Pydantic v2 Household model. Strict/frozen/extra=forbid, mirroring `lib.models` conventions. Fields needed for analysis: income, monthly_obligations, fico, liquid_reserves, `preferred_down_payment_pct`, va_eligible (or this lives on Profile — see D-14-MODELS-02).
- **D-14-MODELS-02 (Profile/Household split):** Marked **Claude's Discretion** — researcher/planner decides whether `va_eligible`, `first_time_buyer`, `military_status` live on Household (financial-state) or on a separate `Profile` (analysis-time preferences) model. CONTEXT does not lock this.
- **D-14-MODELS-03:** Phase 14 ships **`lib/property_verdict.py`** (new) — verdict synthesis module that consumes the populated DownPaymentMatrix + stress block + refi block + Pub 936 block and returns the `Verdict` Pydantic model (GO/WATCH/NO_GO + reasons[]).
- **D-14-MODELS-04:** Phase 14 ships **`lib/property_analysis.py`** (new) — top-level `analyze(listing, household, profile) → AnalysisReport` composition module. AnalysisReport is the Pydantic contract Phase 15 consumes for the markdown report formatter.

### Claude's Discretion (planner/researcher decides)

- **AnalysisReport schema depth:** flat top-level fields vs nested per-program blocks. Locked: top level contains matrix + stress + refi + tax + verdict; internal structure of those blocks is planner's call.
- **Profile vs Household field allocation** (D-14-MODELS-02 above).
- **MIP-burden $300/mo threshold sensitivity:** if researcher finds a credible HUD / MBA citation that differs, planner may swap the threshold WITH explicit annotation in PLAN.md (this is the only verdict threshold that's data-driven; the others are policy choices).
- **IRS Pub 936 over-cap formatting:** the criterion says "$750k cap awareness flagged". Whether the report shows partial-deduction dollars or a "see CPA" flag — Phase 15's formatter problem. Phase 14 ships the boolean flag + first-year interest only.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 14 planning artifacts (this milestone)
- `.planning/REQUIREMENTS.md` — ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 (pending → must close in Phase 14)
- `.planning/ROADMAP.md` §"Phase 14: Property Analysis Pipeline" — 7 success criteria
- `.planning/PROJECT.md` — core value, math-correctness-first principle, evolution rules

### Prior-phase decisions (carry forward)
- `.planning/phases/13-property-ingestion/13-CONTEXT.md` — PropertyListing Pydantic conventions
- `.planning/phases/12-fred-eval/12-CONTEXT.md` — FRED cache + always-exit-0 envelope contract
- `.planning/phases/10-claude-skill/10-CONTEXT.md` — D-09 progressive disclosure (mode/SKILL.md budget)
- `.planning/phases/05-arm-modeling/05-CONTEXT.md` — ARM scope = 5/1 only (D-14-STRESS-03 depends on this)
- `.planning/research/v1.1-property-analysis.md` — milestone research, 9 patterns + 12 pitfalls + 8 open questions

### Existing reference data (already shipped, Phase 14 READS these)
- `data/reference/conforming-limits-2026.yml` — jumbo trigger thresholds per county/zip (D-14-MATRIX-03)
- `data/reference/fha-mip-rates.yml` — FHA upfront 1.75% + monthly MIP per LTV
- `data/reference/va-funding-fees.yml` — VA funding fee per first-use × DP × veteran-type
- `data/reference/irs-pub936.yml` — IRS Pub 936 caps + deductibility rules
- `data/reference/fannie-llpa-matrix.yml` — Fannie LLPAs (price-by-FICO × LTV adjustments, if needed for Conv30)
- `data/reference/freddie-eligibility-matrix.yml` — Freddie eligibility rules
- `data/reference/atr-qm-thresholds.yml` — ATR/QM thresholds (used by `lib/affordability.py` already)

### Reusable v1.0 calc primitives (already shipped)
- `lib/affordability.py` — DTI-CEILING-* blocker codes, blocker-cascade pattern (model for D-14-VERDICT-04)
- `lib/amortize.py` — `amortize(loan_amount, rate, term) → AmortizationSchedule` (per-program PITI driver)
- `lib/arm.py` — 5/1 ARM peak-cap reset (D-14-STRESS-03)
- `lib/points.py` — points-buydown breakeven math (criterion #4)
- `lib/refinance.py` — refinance NPV (criterion #4 refi scan)
- `lib/stress.py` — stress test composition (criterion #3)
- `lib/fred_cache.py` — FRED MORTGAGE30US / MORTGAGE15US accessor (D-14-REFI-02)
- `lib/models.py` — Money / Rate Annotated aliases + strict/frozen/extra=forbid conventions
- `lib/property_listing.py` — Phase 13 PropertyListing model (input contract)

### External docs (for research)
- IRS Publication 936 (2025 edition) — Home Mortgage Interest Deduction; $750k cap; first-year interest treatment
- FHFA 2026 Conforming Loan Limits — baseline $766,550 / high-cost $1,149,825 (1-unit)
- HUD Handbook 4000.1 §II.A.8 — FHA MIP rates by LTV / loan term

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib/affordability.py` — already implements DTI ceiling blockers per program. D-14-MATRIX-02 ("computed anyway") reuses its blocker-cascade pattern: each blocker code is a stable enum value + computed-value pair.
- `lib/amortize.py` — drives PITI computation per cell. Pass program-specific rate (D-14-REFI-02) + loan_amount + term.
- `lib/stress.py` — already composes rate / income / ARM-reset stresses. Phase 14 calls it per-program at preferred DP only (D-14-STRESS-01).
- `lib/refinance.py` — Phase 6 refi NPV. Phase 14 invokes it twice per program at preferred DP: once with target rate = (FRED − 1.00), once with target rate = (FRED × 0.85).
- `lib/points.py` — Phase 8 points buydown. Phase 14 invokes at 1pt and 2pt drops, computes breakeven in months.
- `data/reference/conforming-limits-2026.yml` — D-14-MATRIX-03 reads this to trigger the jumbo 5th row.
- `data/reference/irs-pub936.yml` — Pub 936 caps + rules. Phase 14 lib loads this for D-14-VERDICT-04's tax block.

### Established Patterns
- **Strict/frozen/extra=forbid Pydantic** (from `lib/models.py` + Phase 13's PropertyListing): new models in this phase MUST follow the same pattern. `Household`, `Profile` (if landed), `AnalysisReport`, `Verdict`, `ProgramResult`, `DownPaymentMatrix`, `StressBlock`, `RefiBlock`, `TaxBlock` all use Annotated Money / Rate aliases.
- **Blocker-code citation** (from `lib/affordability.py`): each `reason` in `Verdict.reasons` is shaped `"<BLOCKER-CODE>: <computed-value> (program=<program>, dp=<dp_pct>)"`. Phase 14 reuses this convention.
- **Always-exit-0 envelope** (Phase 12 contract): if `analyze()` is exposed via a CLI in Phase 15, the CLI must catch and emit shape-2 / shape-3 envelopes. Phase 14's library function itself raises normally on programmer error (e.g., invalid household) — that's the planner's call.
- **FRED cache lockfile reuse** (Phase 9 D-LOCK + Phase 12 Python port): Phase 14's FRED reads serialize through `lib.fred_cache.with_cache_lock` exactly like Phase 13 persistence did. No new locks.

### Integration Points
- **Phase 13 contract input:** `analyze(listing: PropertyListing, ...)` — PropertyListing.price is the listing price driver; PropertyListing.zip drives the conforming-limit lookup for D-14-MATRIX-03.
- **Phase 15 contract output:** AnalysisReport is the schema Phase 15's `lib/property_report.py` consumes. Phase 14 freezes this schema before Phase 15 lands.
- **Phase 12 FRED cache:** Phase 14 calls `lib.fred_cache.get_series("MORTGAGE30US")` and `get_series("MORTGAGE15US")` — both already cached by Phase 12.
- **Phase 16 dependency direction:** Phase 14 reads `data/reference/*.yml` files via the existing rules loader pattern. Phase 16 only refreshes the YAMLs; Phase 14 does NOT depend on Phase 16's outputs (the YAMLs already exist).

</code_context>

<specifics>
## Specific Ideas

- **Falsifiable verdict copy:** D-14-VERDICT-04 explicitly requires every reason cite both a predicate code AND a computed value. This is the user's strong preference (carries forward from Phase 4 / Phase 8 stress test agent conventions): "Verdict copy is short and falsifiable."
- **The $300/mo MIP-burden number** (D-14-VERDICT-01) is a policy choice, not a researched threshold. If researcher finds a published heuristic (HUD or MBA) it can be swapped, but the default stands.
- **Golden-value fixtures (criterion #7):** 3 hand-calculated AnalysisReport cases:
  1. SFH conforming (Conv30 eligible, FHA eligible, VA dependent on profile)
  2. Condo with HOA (HOA fee threads into PITI; PMI applies)
  3. SFH jumbo (price > conforming limit; Jumbo30 row appears; FHA/Conv ineligible)

</specifics>

<deferred>
## Deferred Ideas

- **Refinance-from-existing-mortgage scan** (compare new lock vs `household.existing_mortgage_rate`). Rejected from Phase 14 scope (D-14-REFI-01 baseline is forward-only). Belongs in a future "refi mode" phase if user later wants it.
- **Stress fan-out at every DP cell** (full 24×3 or 30×3 stress matrix). Rejected from Phase 14 (D-14-STRESS-01). Could re-enter scope if Phase 15 report shows users want it, but report-bloat is the main objection.
- **Rate overrides from lender quotes** (`profile.rate_overrides: dict[program, Decimal]`). Rejected from Phase 14 (D-14-REFI-02 is FRED-only). Could enter scope when v1.2 ships "compare to lender quote" flow.
- **MIP-burden comparative thresholds** (FHA PITI > Conv × 1.10 style). Rejected for v1.1 (D-14-VERDICT-01 uses the fixed $300/mo). Researcher may surface a published heuristic; if so, swap is in-scope under "Claude's Discretion".
- **Partial-deduction dollar amount for over-$750k loans** in the IRS Pub 936 block. Phase 14 ships the flag only; Phase 15 formatter decides whether to compute the partial dollars or surface a "see CPA" callout.

</deferred>

---

*Phase: 14-property-analysis-pipeline*
*Context gathered: 2026-05-17*
