# Phase 14: Property Analysis Pipeline - Research

**Researched:** 2026-05-17
**Domain:** Composition of v1.0 calc primitives into a (listing, household, profile) → AnalysisReport pipeline with multi-program × DP fan-out and falsifiable verdict synthesis.
**Confidence:** HIGH (composition only; every underlying primitive is already test-pinned, every regulatory YAML already shipped, every Pydantic pattern already established)

## Summary

Phase 14 invents **zero new math.** It composes seven already-shipped primitives (`lib/{amortize, affordability, arm, points, refinance, stress}.py` + `lib/rules/irs_pub936`) into a single `analyze(listing, household, profile) → AnalysisReport` function plus a verdict synthesizer. The work is (a) shaping ~12 new Pydantic models, (b) wiring the 4-or-5 program × 6 DP fan-out loop, (c) the 3-stress / 2-points / 2-refi auxiliary blocks at preferred-DP only, and (d) the GO/WATCH/NO_GO verdict cascade with blocker-code citations.

The hardest design decisions are already locked in CONTEXT.md (D-14-MATRIX-01..03, D-14-VERDICT-01..04, D-14-STRESS-01..03, D-14-REFI-01..03, D-14-MODELS-01..04). The two genuine open questions are: (1) how deep to nest the AnalysisReport schema, and (2) whether `va_eligible / first_time_buyer / military_status` live on Household or on a separate Profile. Both are recommended below with concrete shapes.

**Primary recommendation:** Mirror `lib/stress.py`'s nested-block + discriminated-union architecture exactly. Land Phase 14 as four new files (`lib/household.py`, `lib/profile.py`, `lib/property_verdict.py`, `lib/property_analysis.py`). Put `va_eligible / first_time_buyer / military_status` on a NEW `Profile` model (not Household), because Phase 4's `lib.affordability.Household` is locked-frozen and these are analysis-time preferences, not financial-state facts. Ship three golden-value fixtures as one-fixture-per-file (matching Phase 4/5/8 convention) plus a citation-coverage meta-test for the verdict blocker codes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**DownPaymentMatrix shape & sparsity**
- **D-14-MATRIX-01:** Explicit ineligible rows. Every (program, DP%) cell is a `ProgramResult` with `eligible: bool` + `blocker_reasons: list[str]` populated. Total cells = 4 programs × 6 DPs = 24 (or 5 × 6 = 30 when jumbo triggers). Schema-stable for golden-fixture diffs across listings.
- **D-14-MATRIX-02:** Numeric fields computed anyway on ineligible rows. PITI, cash_to_close, DTI, LTV, PMI/MIP/funding_fee are all populated with the value they WOULD have if rules were waived. Lets the report cite the specific predicate breach with the actual number (e.g., "DTI=51% — DTI-CEILING-CONV"). Slight compute overhead per cell, but maximally explainable.
- **D-14-MATRIX-03:** Jumbo as a 5th program row when triggered. When `listing.price > conforming_limit_for_zip`, append `Jumbo30` as row 5 with its own 6-DP sweep (final matrix = 30 cells). Below the limit, Jumbo30 is omitted entirely (not present-but-ineligible). Conv30/Conv15 remain present regardless.

**Verdict tie-breaks (verdict synthesis)**
- **D-14-VERDICT-01 (MIP-burden WATCH):** Fire WATCH when only FHA is eligible at preferred DP AND `FHA monthly MIP > $300/mo`. Fixed dollar threshold — falsifiable, no comparative baseline required.
- **D-14-VERDICT-02 (Stress-fail WATCH):** Fire WATCH when **ANY** eligible-at-preferred-DP program fails the income-shock stress (DTI breaches ceiling at income × 0.70). Conservative; most-protective verdict.
- **D-14-VERDICT-03 (Severity precedence):** **GO wins when any non-FHA program is eligible at preferred DP**, regardless of FHA MIP burden. The MIP-only path is surfaced as an informational reason but does not downgrade the verdict when a non-FHA eligible path exists. Stress-fail WATCH still downgrades a GO (so GO requires: non-FHA eligible at preferred DP AND no stress-fail across eligible programs).
- **D-14-VERDICT-04 (Reason citations):** Every verdict reason MUST cite both the predicate identifier (matching the existing `lib/rules/*` blocker code style — e.g., `DTI-CEILING-CONV`) and the computed numeric value that triggered it. Mirrors Phase 4 affordability blocker-cascade convention.

**Stress fan-out scope**
- **D-14-STRESS-01:** Stress tests run at user's preferred DP only, not the full matrix. Output: 4–5 programs × 3 stresses = 12–15 stress rows per analysis. The full DP sweep stays purely program-level (eligibility + PITI per cell).
- **D-14-STRESS-02:** `preferred_down_payment_pct: Decimal` lives on the Household Pydantic model (`lib/household.py`, new this phase). User sets it once in their `household.yml`. Default = `Decimal("0.20")` when absent.
- **D-14-STRESS-03:** ARM peak-cap reset stress fires for Conv30 only (the 5/1 ARM variant per Phase 5 `lib/arm.py` scope). FHA/VA/Conv15/Jumbo30 do not produce an ARM-reset stress row.

**Refi baseline & today's-rate sourcing**
- **D-14-REFI-01:** Baseline lock rate = user's matrix cell rate (the rate they'd lock in TODAY for the given program × DP). The analysis is forward-looking purchase + refi planning; the household's existing mortgage rate is NOT the baseline.
- **D-14-REFI-02:** Today's rate per program sourced from FRED via `lib/fred_cache.py`:
  - Conv30 = `MORTGAGE30US`
  - Conv15 = `MORTGAGE15US`
  - FHA30, VA30 = `MORTGAGE30US` (acceptable v1.0 proxy)
  - Conv30 ARM 5/1 = `MORTGAGE30US − 0.25` heuristic
  - Jumbo30 = `MORTGAGE30US` (acceptable v1.0 proxy)
- **D-14-REFI-03:** Refi scan triggers both come from FRED current — scan at `(FRED_current − 1.00)` AND `(FRED_current × 0.85)`. For 30yr programs these equal the user's lock; for Conv15 / ARM they diverge (a defensible projection downstream from "this is what the broader market would have to do for a refi to be worth it").

**Models & file landings**
- **D-14-MODELS-01:** Phase 14 ships `lib/household.py` (new) — Pydantic v2 Household model. Strict/frozen/extra=forbid, mirroring `lib.models` conventions. Fields needed for analysis: income, monthly_obligations, fico, liquid_reserves, `preferred_down_payment_pct`, va_eligible (or this lives on Profile — see D-14-MODELS-02).
- **D-14-MODELS-02 (Profile/Household split):** Marked **Claude's Discretion** — researcher/planner decides whether `va_eligible`, `first_time_buyer`, `military_status` live on Household (financial-state) or on a separate `Profile` (analysis-time preferences) model. CONTEXT does not lock this.
- **D-14-MODELS-03:** Phase 14 ships `lib/property_verdict.py` (new) — verdict synthesis module that consumes the populated DownPaymentMatrix + stress block + refi block + Pub 936 block and returns the `Verdict` Pydantic model (GO/WATCH/NO_GO + reasons[]).
- **D-14-MODELS-04:** Phase 14 ships `lib/property_analysis.py` (new) — top-level `analyze(listing, household, profile) → AnalysisReport` composition module. AnalysisReport is the Pydantic contract Phase 15 consumes for the markdown report formatter.

### Claude's Discretion

- **AnalysisReport schema depth:** flat top-level fields vs nested per-program blocks. Locked: top level contains matrix + stress + refi + tax + verdict; internal structure of those blocks is planner's call.
- **Profile vs Household field allocation** (D-14-MODELS-02 above).
- **MIP-burden $300/mo threshold sensitivity:** if researcher finds a credible HUD / MBA citation that differs, planner may swap the threshold WITH explicit annotation in PLAN.md.
- **IRS Pub 936 over-cap formatting:** Phase 14 ships the boolean flag + first-year interest only.

### Deferred Ideas (OUT OF SCOPE)

- **Refinance-from-existing-mortgage scan** (compare new lock vs `household.existing_mortgage_rate`). Rejected from Phase 14 scope (D-14-REFI-01 baseline is forward-only). Belongs in a future "refi mode" phase if user later wants it.
- **Stress fan-out at every DP cell** (full 24×3 or 30×3 stress matrix). Rejected from Phase 14 (D-14-STRESS-01).
- **Rate overrides from lender quotes** (`profile.rate_overrides: dict[program, Decimal]`). Rejected from Phase 14 (D-14-REFI-02 is FRED-only).
- **MIP-burden comparative thresholds** (FHA PITI > Conv × 1.10 style). Rejected for v1.1 (D-14-VERDICT-01 uses the fixed $300/mo).
- **Partial-deduction dollar amount for over-$750k loans** in the IRS Pub 936 block. Phase 14 ships the flag only; Phase 15 formatter decides whether to compute the partial dollars or surface a "see CPA" callout.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANLZ-01 | Multi-program comparison fans out across 4 loan programs (Conv30, Conv15, FHA30, VA30 if profile.va_eligible) + jumbo branch when price exceeds zip-specific conforming limit; each program produces a Pydantic `ProgramResult` (eligible, monthly_PITI, cash_to_close, DTI, LTV, PMI/MIP/funding-fee, eligible_reasons, blocker_reasons). | Standard Stack §"Composition", Architecture §"ProgramResult shape", Code Examples §"Per-cell composition" |
| ANLZ-02 | Down-payment scenario sweep at 3% / 5% / 10% / 15% / 20% / 25% per program — produces a `DownPaymentMatrix` (~24 cells for 4 programs × 6 DPs, fewer when programs are ineligible). | Architecture §"DownPaymentMatrix structure", Pitfall 4 §"PMI/MIP table lookup by LTV", Code Examples §"DP fan-out loop" |
| ANLZ-03 | Auto-applied stress tests (rate shock +2%, income shock -30%, ARM reset at peak cap) + points breakeven (1pt and 2pt drops) + refi opportunity scan (against FRED current - 1% AND FRED current × 0.85) + IRS Pub 936 deductibility rollup (first-year interest, $750k cap awareness). | Architecture §"Auxiliary blocks", Code Examples §"Stress invocation", §"Refi scan", §"IRS Pub 936 block" |
| VERD-01 | `lib/property_verdict.py` returns GO/WATCH/NO_GO + reason list. Any DTI breach across all eligible programs → NO_GO; any program eligible at user's preferred DP → GO; eligible-only-via-FHA-with-MIP-burden or stress-fails-income-shock → WATCH. Verdict copy is short and falsifiable (each reason cites a specific predicate + computed number). | Architecture §"Verdict cascade", Code Examples §"Verdict synthesis", Pitfall 7 §"Verdict reason format drift" |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

These directives govern every line of code Phase 14 ships:

- **Money discipline (non-negotiable):** `Decimal` only — never float. Construct from strings: `Decimal("0.065")`, never `Decimal(0.065)`. `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` end-of-period only. Pydantic v2 `condecimal` (or `Money`/`Rate` Annotated aliases from `lib/models.py`) at every script boundary.
- **Calc engine separation:** every dollar figure computed by Python in `lib/`; Claude never owns numbers. Phase 14 ships library code only — the script boundary (Phase 12 always-exit-0 envelope) is wired in Phase 15.
- **Rules-as-predicates:** one file per regulatory citation in `lib/rules/`. Phase 14 CONSUMES `lib/rules/{loan_type, fha_mip, va_funding_fee, irs_pub936, conventional_pmi, fannie_eligibility, atr_qm, ...}.py`. It does NOT add new rule predicates.
- **Reference data discipline:** all regulatory parameters in `data/reference/*.yml` with `source:` URL + `effective:` date. Phase 14 reads `conforming-limits-2026.yml`, `fha-mip-rates.yml`, `va-funding-fees.yml`, `irs-pub936.yml`, `fannie-llpa-matrix.yml`. It does NOT inline-constant any regulatory threshold.
- **Testing:** hand-calculated golden-value fixtures with citation comments. Exact Decimal equality, never `assertAlmostEqual` for money.
- **Commits:** No Co-Authored-By or AI attribution (per global rule).
- **User-Layer pre-commit hook:** `scripts/hooks/block-user-layer.py` blocks edits to `config/household.yml` / `config/profile.yml`. Phase 14 may modify `config/household.example.yml` and `config/profile.example.yml` only (allowlist already permits `*.example.yml`).
- **`Money` alias:** `Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0"))]`. **CAUTION:** `ge=Decimal("0")` blocks negative values — for signed Decimals (e.g., `delta_vs_baseline_monthly`), use raw `Decimal = Field(strict=True, max_digits=14, decimal_places=2)` instead, matching the Phase 6 `RefiCashflow.amount` precedent.
- **`Rate` alias:** `Annotated[Decimal, Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1"))]`. Note the `le=Decimal("1")` ceiling — all rates are fractional (0.065 = 6.5%), never percentages.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AnalysisReport schema (Pydantic contract) | Python lib (`lib/property_analysis.py`) | — | Frozen contract Phase 15's report formatter consumes; lives at the math layer because it carries Decimal-discipline. |
| Multi-program × DP fan-out (compose primitives) | Python lib (`lib/property_analysis.py`) | — | Pure composition over `lib.{amortize, affordability, arm, points, refinance, stress}` + `lib.rules.*`; matches Phase 4-8 separation (math in lib/, skill narration in modes/). |
| Verdict synthesis (GO/WATCH/NO_GO cascade) | Python lib (`lib/property_verdict.py`) | — | Same separation; verdict is a derived field carrying blocker citations. |
| Household + Profile Pydantic models | Python lib (`lib/household.py`, `lib/profile.py`) | YAML User Layer (`config/household.yml`, `config/profile.yml`) | Models live in lib/; user values live in gitignored User Layer per DATA_CONTRACT.md. Phase 14 may modify only `*.example.yml`. |
| FRED rate sourcing (today's rate per program) | Python lib (consumes `lib.fred_cache.get_cached_or_fetch`) | — | Cache layer already exists (Phase 12); Phase 14 reads through it via `with_cache_lock` serialization. |
| Regulatory-data YAML reads (PMI/MIP/funding-fee/conforming-limit/Pub 936) | Python lib (`lib/rules/*.py` → `lib.rules._loader.load_reference`) | YAML reference (`data/reference/*.yml`) | All regulatory tables already shipped (Phase 2+); Phase 14 consumes via existing predicates. |
| Markdown report formatting | NOT Phase 14 | Phase 15 (`lib/property_report.py`) | Phase 14 freezes AnalysisReport schema; Phase 15 renders. |
| Skill mode routing (URL pin, narration) | NOT Phase 14 | Phase 15 (`.claude/skills/mortgage-ops/modes/property.md`) | Phase 14 is library-only. |
| CLI orchestrator (always-exit-0 envelope) | NOT Phase 14 | Phase 15 (`scripts/property_analyze.py`) | Phase 14 raises on programmer error; Phase 15's CLI catches and emits envelope. |

## Standard Stack

### Core (already in pyproject.toml — Phase 14 adds nothing new)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | ≥2.6 | All new models (Household, Profile, ProgramResult, DownPaymentMatrix, StressBlock, RefiBlock, TaxBlock, Verdict, AnalysisReport) | Strict/frozen/extra=forbid is universal in `lib/` per CLAUDE.md. **[VERIFIED: pyproject.toml at repo root + every lib/ file]** |
| `numpy-financial` | 1.0.0 | Transitively via `lib.amortize.build_schedule` (per-cell PITI driver) | Already pinned at 1.0.0 (Phase 1 D-FND-02); returns Decimal when fed Decimal. **[VERIFIED: lib/amortize.py L124-135 docstring]** |
| `python-dateutil` | (installed) | Transitively via amortize date math | Used by Phase 3 D-13 for month-end clipping. **[VERIFIED: lib/amortize.py L145]** |
| `PyYAML` | (installed) | Transitively via `lib.rules._loader.load_reference` | All reference YAMLs loaded through this seam. **[VERIFIED: existing pattern]** |

**No new dependencies in Phase 14.** Every primitive Phase 14 composes is already shipped + test-pinned. **[VERIFIED: `ls /Users/cujo253/Documents/mortgage-ops/lib/`]**

### Supporting (existing lib/ primitives — Phase 14 composes these)

| Module | Function/Class | Purpose in Phase 14 |
|--------|----------------|---------------------|
| `lib.amortize` | `build_schedule(loan, frequency='monthly') → Schedule` | Per-cell PITI driver. Returns `Schedule.monthly_pi` (the P&I number Phase 14 adds escrow + MI to for PITI). **[VERIFIED: lib/amortize.py L255-292]** |
| `lib.affordability` | `evaluate(req) → AffordabilityResponse`; `Household, Applicant, MonthlyDebts, EscrowInputs, LocationFIPS, VAInputs` | DTI/LTV/CLTV/blocker cascade per cell. **WARNING:** This `Household` model is a Phase 4 lock — Phase 14's NEW `Household` model in `lib/household.py` is a DIFFERENT contract (analysis-time vs affordability-time). See Architecture §"Profile/Household split" below for the resolution. **[VERIFIED: lib/affordability.py L407-433 (Phase 4 Household), CONTEXT D-14-MODELS-01]** |
| `lib.arm` | `build_arm_schedule(req) → ARMSchedule`; `ARMTerms, ARMRequest, IndexPathEntry` | 5/1 ARM peak-cap reset stress at preferred-DP Conv30 only (D-14-STRESS-03). **[VERIFIED: lib/arm.py L88-145, Phase 5 D-06]** |
| `lib.stress` | `RateShockRequest, IncomeShockRequest, ArmResetRequest, evaluate(req) → StressResponse` | All three stress modes (rate shock, income shock, ARM reset) at preferred DP only. **[VERIFIED: lib/stress.py L162-262]** |
| `lib.points` | `PointsRequestFromLoans, evaluate(req) → PointsResponse` | Points breakeven at 1pt and 2pt drops at preferred-DP cell. **[VERIFIED: lib/points.py L85-135]** |
| `lib.refinance` | `evaluate(req) → RefiResponse`; `RefiRequest` (rate-and-term mode) | Refi scan at `(FRED_current - 1.00)` AND `(FRED_current × 0.85)` per program at preferred DP. **[VERIFIED: lib/refinance.py L1-160]** |
| `lib.fred_cache` | `get_cached_or_fetch(series_id, fetcher=...)`; `with_cache_lock(cache_dir, reason=...)` | Today's rate sourcing per program (D-14-REFI-02). All reads serialize through `with_cache_lock`. **[VERIFIED: lib/fred_cache.py L235-356]** |
| `lib.models` | `Loan, Schedule, Payment, Money, Rate` | Phase 1 frozen surface — every new model imports `Money` and `Rate` Annotated aliases from here. **[VERIFIED: lib/models.py L1-92]** |
| `lib.money` | `quantize_cents(d) → Decimal`; `quantize_rate(d) → Decimal` | End-of-period rounding helpers (ROUND_HALF_UP). **[VERIFIED: lib/affordability.py L186 import]** |
| `lib.property_listing` | `PropertyListing` (Phase 13 input contract) | The `listing` arg to `analyze()`. Fields used: `price`, `zip` (will need state_fips/county_fips derivation per Pitfall 5), `property_type`, `tax_annual`, `hoa_monthly`, `insurance_estimate_annual`. **[VERIFIED: lib/property_listing.py L44-87]** |
| `lib.rules.loan_type` | `classify(loan_amount, county, program=, unit_count=) → LoanType`; `MissingCountyDataError` | Drives D-14-MATRIX-03 (jumbo trigger). Note: takes a `County(state_fips, county_fips, name)`, NOT a zip — see Pitfall 5. **[VERIFIED: lib/rules/loan_type.py L55-111]** |
| `lib.rules.fha_mip` | `compute(loan, original_property_value, endorsement_date) → MIPResult(ufmip, annual_mip_pct, terminates_at_period)` | FHA UFMIP + monthly MIP per LTV. UFMIP auto-financed into principal per Phase 4 D-03. **[VERIFIED: lib/rules/fha_mip.py L65-130]** |
| `lib.rules.va_funding_fee` | `compute(loan_amount, down_payment_pct, is_first_use, loan_purpose='purchase', is_exempt_from_funding_fee) → Decimal` | VA funding fee. Note: returns dollar amount, not a rate. **[VERIFIED: lib/rules/va_funding_fee.py L65-110]** |
| `lib.rules.irs_pub936` | `qualified_loan_limit(filing_status, has_grandfathered_debt=, binding_contract_signed_before_2017_12_15=, binding_contract_closed_before_2018_04_01=) → Decimal` | $750k cap awareness flag. Phase 14 calls with default booleans (no grandfathering) since household acquisition is post-2017 by definition for v1.1 scope (Pitfall 11). **[VERIFIED: lib/rules/irs_pub936.py L66-90]** |
| `lib.rules.conventional_pmi` | `LTV_REQUEST_ELIGIBLE: Decimal("0.80")` constant; `status(loan, scheduled_balance, original_property_value, ...) → TerminationStatus` enum | **CRITICAL:** Returns a termination enum, NOT a PMI rate. Caller MUST supply `monthly_pmi: Money` when conventional + LTV > 0.80 (Phase 4 RESEARCH Open Q#1). See Pitfall 1 below. **[VERIFIED: lib/affordability.py L195 + L478-492]** |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-process composition (`lib/property_analysis.py:analyze(...)`) | Subprocess fan-out (one `subprocess.run` per cell) | 24-30 subprocesses × ~500ms argparse cold-start = 12-15s wall-clock vs ~1s in-process. **[CITED: research/v1.1-property-analysis.md §Pattern 3, "wall-clock well under one second"]** Reject subprocess. |
| Nested per-program blocks (recommended) | Flat top-level fields (one field per program × DP × metric = 30+ top-level fields) | Flat is unreadable, breaks `extra="forbid"` ergonomics for jumbo-conditional fields. Nest. |
| Profile + Household split (recommended) | All fields on Household | Household is already a Phase 4 LOCKED frozen contract for affordability (`lib/affordability.py:Household`) — re-using the name with new fields would silently shadow it across the codebase. Use a separate `Profile` model. |
| Recompute conforming-limit via direct YAML read | Call `lib.rules.loan_type.classify()` | `classify()` already handles the high-cost-county subset + raises `MissingCountyDataError` for unknown counties. Don't bypass — see Pitfall 5. |

**Installation:**

```bash
# No new packages — Phase 14 adds zero dependencies.
# Verify existing deps:
python -c "import pydantic; print(pydantic.VERSION)"
# Expected: 2.6+
```

**Version verification:** Verified against `pyproject.toml` and existing lib/ imports as of 2026-05-17. No new versions to confirm.

## Architecture Patterns

### System Architecture Diagram

```
                          analyze(listing, household, profile)
                                       │
                                       ▼
              ┌───────────────────────────────────────────────────┐
              │ Step 1: Resolve county + conforming limit         │
              │ (listing.zip + profile.state_fips/county_fips →   │
              │  lib.rules.loan_type.classify per program)        │
              └───────────────────────────────────────────────────┘
                                       │
                                       ▼
              ┌───────────────────────────────────────────────────┐
              │ Step 2: Fetch today's rate per program            │
              │ lib.fred_cache.get_cached_or_fetch                │
              │   MORTGAGE30US → Conv30, FHA30, VA30, Jumbo30     │
              │   MORTGAGE15US → Conv15                           │
              │   MORTGAGE30US - 0.25 → Conv30 ARM (D-14-REFI-02) │
              └───────────────────────────────────────────────────┘
                                       │
                                       ▼
              ┌───────────────────────────────────────────────────┐
              │ Step 3: Determine programs                        │
              │   base = [Conv30, Conv15, FHA30]                  │
              │   if profile.va_eligible: base += [VA30]          │
              │   if listing.price > conforming_limit:            │
              │       base += [Jumbo30]                           │
              └───────────────────────────────────────────────────┘
                                       │
                                       ▼
              ┌───────────────────────────────────────────────────┐
              │ Step 4: Fan-out — for each (program, DP):         │
              │   • compute loan_amount = price × (1 - dp_pct)    │
              │   • compute PMI/MIP/funding-fee per program       │
              │   • call lib.amortize.build_schedule → monthly_pi │
              │   • compose PITI (P&I + tax + insurance + HOA     │
              │       + MI/funding-fee monthly)                   │
              │   • compute DTI back-end (PITI + obligations) /   │
              │       income                                       │
              │   • emit ProgramResult(eligible, blockers, all    │
              │       numerics populated per D-14-MATRIX-02)      │
              │   → DownPaymentMatrix(cells: list[ProgramResult]) │
              └───────────────────────────────────────────────────┘
                                       │
                                       ▼
              ┌───────────────────────────────────────────────────┐
              │ Step 5: Auxiliary blocks at preferred DP only     │
              │   • StressBlock: per-program × 3 stresses         │
              │     (rate +2%, income -30%, ARM reset for Conv30) │
              │   • RefiBlock: per-program × 2 refi scans         │
              │     ((FRED-1.00) and (FRED×0.85))                 │
              │   • PointsBlock: per-program × 2 point drops      │
              │     (1pt, 2pt) — Conv30/Conv15/Jumbo30 only?      │
              │     (planner decision; see Open Question 1)       │
              │   • TaxBlock: IRS Pub 936 first-year interest +   │
              │     $750k cap boolean                             │
              └───────────────────────────────────────────────────┘
                                       │
                                       ▼
              ┌───────────────────────────────────────────────────┐
              │ Step 6: lib.property_verdict.synthesize(...)      │
              │   → Verdict(level='GO'|'WATCH'|'NO_GO',           │
              │     reasons: list[VerdictReason])                 │
              │   Cascade per D-14-VERDICT-01..04:                │
              │   1. No eligible at any DP → NO_GO                │
              │   2. No eligible at preferred DP → NO_GO          │
              │   3. Stress-fail any eligible → WATCH             │
              │   4. FHA-only eligible + MIP > $300 → WATCH       │
              │   5. Otherwise → GO                               │
              └───────────────────────────────────────────────────┘
                                       │
                                       ▼
                              AnalysisReport(...)
                              (frozen Pydantic; Phase 15 renders)
```

### Recommended Project Structure

```
lib/
├── household.py              # NEW — Household model (analysis-time)
├── profile.py                # NEW — Profile model (eligibility/preferences)
├── property_analysis.py      # NEW — analyze() composition + all output models
│                               (ProgramResult, DownPaymentMatrix, StressBlock,
│                                RefiBlock, PointsBlock, TaxBlock, AnalysisReport)
└── property_verdict.py       # NEW — synthesize() + Verdict + VerdictReason models

tests/
├── test_household.py         # NEW — model validation tests
├── test_profile.py           # NEW — model validation tests
├── test_property_analysis.py # NEW — pipeline tests + 3 golden fixtures
├── test_property_verdict.py  # NEW — verdict cascade tests + citation coverage
└── fixtures/
    └── property_analysis/    # NEW dir
        ├── sfh_conforming_king_county.json
        ├── condo_with_hoa_seattle.json
        └── sfh_jumbo_bay_area.json
```

> **NOTE (out of Phase 14 scope per Specifics):** the exact file split (e.g., whether `ProgramResult` lands in `lib/property_analysis.py` vs its own `lib/program_result.py`) is the planner's call. The above is a recommendation, not a lock.

### Pattern 1: Discriminated-union-by-program for cell engines

**What:** Each program's `ProgramResult` is structurally identical (same fields), but the *helpers* that compute MI/funding-fee branch by program. Keep ProgramResult flat (one shape for all 5 programs) with `program: Literal["Conv30","Conv15","FHA30","VA30","Jumbo30"]` as a discriminator-by-convention (no Pydantic discriminated union — fields don't differ).

**When to use:** When the OUTPUT shape is uniform but the INPUT compute path branches.

**Example shape:**

```python
# lib/property_analysis.py
class ProgramResult(BaseModel):
    """One cell in the DownPaymentMatrix (D-14-MATRIX-01 + D-14-MATRIX-02).

    Numerics populated on ineligible rows too (D-14-MATRIX-02) so the report
    can cite the predicate breach with the actual number.
    """
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    program: Literal["Conv30", "Conv15", "FHA30", "VA30", "Jumbo30"]
    down_payment_pct: Rate

    # Numerics (always populated — D-14-MATRIX-02)
    loan_amount: Money
    monthly_pi: Money
    monthly_tax: Money
    monthly_insurance: Money
    monthly_hoa: Money
    monthly_mi: Money              # PMI / MIP / funding-fee-monthly equivalent
    piti: Money                    # P&I + tax + insurance + HOA + MI
    cash_to_close: Money           # down_payment + ufmip-if-not-financed + estimated closing
    dti_back: Rate                 # (piti + monthly_obligations) / monthly_income
    ltv: Rate                      # loan_amount / property_value

    # Eligibility (D-14-MATRIX-01)
    eligible: bool
    blocker_reasons: list[str]     # blocker-code-style strings (D-14-VERDICT-04)
    eligible_reasons: list[str]    # for symmetry — programs that passed get an empty list
                                   # or a "verified-against" trail
```

### Pattern 2: AnalysisReport — nested-block recommendation (resolves Claude's Discretion)

**Recommendation: nested blocks, mirroring `lib/stress.py:StressResponse` shape exactly.**

```python
# lib/property_analysis.py
class DownPaymentMatrix(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    cells: list[ProgramResult]              # 24 (no jumbo) or 30 (jumbo)
    programs_present: list[str]             # ["Conv30","Conv15","FHA30","VA30","Jumbo30"]
    down_payment_pcts: list[Rate]           # [0.03, 0.05, 0.10, 0.15, 0.20, 0.25]


class StressRow(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    program: str                            # which program this row applies to
    stress_kind: Literal["rate_shock", "income_shock", "arm_reset"]
    baseline_piti: Money
    stressed_piti: Money | None             # None for income_shock (income doesn't change PITI)
    stressed_dti_back: Rate
    breaches_dti_ceiling: bool
    blocker_reasons: list[str]              # populated on breach


class StressBlock(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    preferred_down_payment_pct: Rate        # echo from Household
    rows: list[StressRow]                   # 12-15 rows (4-5 programs × 3 stresses minus ARM-for-non-Conv30)


class RefiRow(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    program: str
    target_rate: Rate                       # FRED_current - 1.00 OR FRED_current × 0.85
    scenario_label: Literal["minus_100bps", "fred_times_0.85"]
    monthly_savings: Decimal                # signed (rate-up scenarios)
    breakeven_months: int | None
    npv_60mo: Decimal                       # signed


class RefiBlock(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    rows: list[RefiRow]                     # 4-5 programs × 2 scenarios = 8-10 rows


class PointsRow(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    program: str
    points_purchased: Literal[1, 2]
    rate_drop: Rate                         # 0.0025 per point (industry convention; planner confirms)
    simple_breakeven_months: int | None
    npv_breakeven_months: int | None


class PointsBlock(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    rows: list[PointsRow]


class TaxBlock(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    first_year_interest_per_program: dict[str, Money]   # keyed by program label
    over_750k_cap_per_program: dict[str, bool]
    qualified_loan_limit: Money                          # Decimal("750000") for post-2017
    filing_status: Literal["single","mfj","mfs","hoh"]   # echoed from Profile


class Verdict(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    level: Literal["GO", "WATCH", "NO_GO"]
    headline_reason: str                    # one-line verdict copy
    reasons: list[VerdictReason]            # falsifiable cascade per D-14-VERDICT-04


class VerdictReason(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    predicate_code: str                     # e.g., "DTI-CEILING-CONV", "MIP-BURDEN", "STRESS-INCOME"
    computed_value: str                     # numeric value formatted as quoted Decimal string
    program: str | None = None              # which program this applies to (or None for cross-program)
    dp_pct: Rate | None = None              # which DP cell (or None for global verdicts)


class AnalysisReport(BaseModel):
    """Top-level Phase 14 output (D-14-MODELS-04). Phase 15's lib/property_report.py
    consumes this contract for markdown rendering."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    # Inputs echoed (for audit + Phase 15 narration)
    listing_snapshot: PropertyListing
    household_snapshot_hash: str           # SHA256 of household + profile YAML (Phase 13 D-13-REANALYSIS-01)
    fetched_at: datetime

    # FRED rates used (D-14-REFI-02 audit trail)
    fred_mortgage_30us: Rate
    fred_mortgage_15us: Rate

    # The five blocks
    matrix: DownPaymentMatrix
    stress: StressBlock
    refi: RefiBlock
    points: PointsBlock
    tax: TaxBlock
    verdict: Verdict

    # Field declaration order MATTERS: matrix before verdict so JSON-readers see numerics first.
    # Mirrors Phase 8 D-02 (summary before rows).
```

**Why nested over flat:** flat-with-per-program fields would balloon the top-level model to ~50 fields and make jumbo-conditional fields awkward (Pydantic v2 + `extra="forbid"` doesn't gracefully handle "field exists only when jumbo triggers"). Nested blocks let each block contain its own list of rows; jumbo conditionality lives in `DownPaymentMatrix.cells` being length 24 vs 30.

### Pattern 3: Profile vs Household split (resolves Claude's Discretion D-14-MODELS-02)

**Recommendation: separate `lib/profile.py` Profile model. Put `va_eligible`, `first_time_buyer`, `military_status` there.**

Rationale:
1. **Name collision with Phase 4 lock.** `lib.affordability.Household` is a Phase 4 FROZEN contract (`extra="forbid"`). Adding fields to that exact class breaks Phase 4 fixtures + test surface. A NEW `lib.household.Household` with different fields would silently shadow it across files — confusing.
2. **Semantic split is real.** Household = financial-state (income, debts, FICO, reserves, preferred DP). Profile = analysis-time preferences + eligibility metadata (va_eligible, first_time_buyer, filing_status, marginal_tax_rate, display preferences). The existing `config/profile.example.yml` already separates these concerns.
3. **Sibling-project precedent.** PROJECT.md L93-96 cites card-ops + career-ops as inspirations. **[VERIFIED: card-ops uses `household.yml` for household-stable facts]**; the `config/profile.example.yml` in this repo already has display + defaults + modes blocks — a natural place to add `va_eligible`.

**Concrete shapes:**

```python
# lib/household.py (NEW — Phase 14)
class Household(BaseModel):
    """Household financial state for property analysis (D-14-MODELS-01).

    DISTINCT from lib.affordability.Household (Phase 4 frozen contract).
    This is the simpler analysis-time view; the affordability engine consumes
    a parallel structure derived from this one.
    """
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    # Income + debts (analysis-time aggregates; affordability evaluate(...) gets the
    # detailed Phase 4 Household constructed from these + Profile fields)
    monthly_income: Money
    monthly_obligations: Money              # auto + student + cc + other (aggregated)
    fico: int = Field(ge=300, le=850)
    liquid_reserves: Money                  # cash available for cash-to-close

    # Location (needed for conforming-limit lookup via County construction)
    state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
    county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    county_name: str

    # Phase 14 preferred-DP knob (D-14-STRESS-02)
    preferred_down_payment_pct: Rate = Decimal("0.20")

    # Phase 4 escrow inputs reused as-is
    monthly_property_tax: Money | None = None     # if None, use listing's
    monthly_insurance: Money | None = None        # if None, use listing's
    monthly_hoa: Money | None = None              # if None, use listing's


# lib/profile.py (NEW — Phase 14)
class Profile(BaseModel):
    """Analysis-time preferences + eligibility metadata (D-14-MODELS-02).

    Split from Household because these are user preferences and program-eligibility
    booleans, NOT financial state.
    """
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    # Eligibility booleans (drive program fan-out in property_analysis.analyze)
    va_eligible: bool = False
    first_time_buyer: bool = False
    military_status: Literal["active","veteran","reserve","none"] = "none"

    # Tax (drives IRS Pub 936 block)
    filing_status: Literal["single","mfj","mfs","hoh"] = "mfj"
    marginal_tax_rate: Rate | None = None   # optional; Phase 14 ships Pub 936 boolean only

    # Display preferences (echoed for Phase 15 rendering)
    display_money_format: str = "USD"
    display_rate_format: Literal["percent","decimal"] = "percent"
```

### Anti-Patterns to Avoid

- **Re-using `lib.affordability.Household` name in `lib/household.py`.** Different module path, same class name → import-time confusion + test surface drift. Use the same NAME only if shipping the EXACT Phase 4 model; otherwise a different name or different module is required.
- **Computing PMI/MIP/funding-fee inline (with hardcoded rates) instead of via predicates.** All three are already YAML-backed via `lib.rules.{fha_mip, va_funding_fee}`. Inline rates silently drift.
- **Calling `lib.rules.loan_type.classify` once per (program, DP) cell.** Classification depends only on (loan_amount, county, program); it's invariant across DP. Cache the classification per (program, loan_amount) tuple.
- **Skipping `with_cache_lock` around FRED reads.** Phase 12 contract requires every cache read serializes through `with_cache_lock(reason=...)`. Direct `_load_cache()` calls bypass the lock and race with the SKILL.md weekly cron.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-program PITI computation | Custom PMT formula | `lib.amortize.build_schedule(loan, frequency='monthly').monthly_pi` | Already wraps `numpy_financial.pmt`; respects all Phase 3 invariants (D-04 rate-per-period, D-07 composition order, D-15 total_interest by construction). |
| DTI / LTV blocker cascade per cell | Inline DTI math | `lib.affordability.evaluate(req)` returning `AffordabilityResponse.blocked_by` | Phase 4's blocker-code precedence is exactly what D-14-VERDICT-04 needs to cite. |
| Conforming-limit lookup | Direct YAML read of conforming-limits-2026.yml | `lib.rules.loan_type.classify(loan_amount, county, program='conventional')` | Predicate handles high-cost-county subset + `MissingCountyDataError`. |
| FHA monthly MIP | Hardcoded 0.55% × loan_amount / 12 | `lib.rules.fha_mip.compute(loan, original_property_value, endorsement_date).annual_mip_pct` → `monthly = quantize_cents(loan_amount × annual_mip_pct / 12)` | YAML table is LTV-band × term-band × loan-amount-band conditional; hardcoding silently mis-rates high-balance loans. |
| VA funding fee | Hardcoded 2.15% × loan_amount | `lib.rules.va_funding_fee.compute(loan_amount, dp_pct, is_first_use, 'purchase', is_exempt)` | Band lookup with cash-out exclusions + IRRRL/manufactured-home flat fees. Hardcoding mis-rates non-purchase. |
| Conventional PMI | Hardcoded 0.005-0.0125 range | **Caller-supplied `monthly_pmi: Money` per Phase 4 RESEARCH Open Q#1** — bureau-specific, no public YAML | Conventional PMI rates are NOT in any reference YAML because they're MGIC/Genworth/Radian-specific. Caller (Phase 14 has to figure this out — see Open Question 2). |
| IRS Pub 936 cap | Hardcoded $750,000 | `lib.rules.irs_pub936.qualified_loan_limit(filing_status=...)` | Predicate handles MFS-half ($375k) + pre-2017 grandfathering ($1M) + binding-contract grace period. |
| FRED rate fetch | Direct `urllib.request` | `lib.fred_cache.get_cached_or_fetch(series_id, fetcher=...)` | Already implements 7-day TTL + `with_cache_lock` + schema_version + StaleCacheWarning + always-exit-0 envelope shape. |
| Stress test composition | Custom rate/income/ARM-reset loop | `lib.stress.evaluate(StressRequest)` discriminated union (`RateShockRequest`, `IncomeShockRequest`, `ArmResetRequest`) | Already returns `StressResponse(summary, rows)` with stress_invariant_violations check. |
| Refi NPV breakeven | Custom NPV walk | `lib.refinance.evaluate(RefiRequest)` | Already returns `RefiResponse` with simple-AND-NPV breakeven side-by-side; D-06 cumulative-NPV walk in lib already passes the bug-#131-avoidance test. |
| Points breakeven | Custom point/savings math | `lib.points.evaluate(PointsRequestFromLoans(...))` | Returns simple AND NPV breakeven; D-04 reports both per ROADMAP. |
| Money quantization | `round()` or `Decimal(x).quantize(Decimal('0.01'))` | `lib.money.quantize_cents(d)` | Pins ROUND_HALF_UP consistently across the codebase. |

**Key insight:** Phase 14 should be ~600-800 lines of composition glue + Pydantic model declarations. If your plan is showing >1500 lines of new code, you're reimplementing something the v1.0 engine already ships. Halt and ask "what existing function does this?"

## Runtime State Inventory

This is a **greenfield phase** (composition-only; no rename/refactor). The Runtime State Inventory categories are answered explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 14 produces in-memory `AnalysisReport` objects only. DuckDB persistence of these reports is wired via `lib.property_persistence` (already shipped Phase 13) — but Phase 13's writer takes the JSON envelope, so Phase 14 just calls `model_dump_json()` and hands off. **No new schema, no migration.** | None |
| Live service config | None — Phase 14 has no live external services. FRED reads go through the existing cache (Phase 12 SC-2 + `with_cache_lock`). No n8n/Datadog/external-API state to update. | None |
| OS-registered state | None — no schedulers, no daemons. Phase 14 is library code only. | None |
| Secrets/env vars | None — Phase 14 reads no env vars. FRED_API_KEY is consumed by `scripts/fred_cli.py` (Phase 12) not by lib.fred_cache directly. | None |
| Build artifacts | None — Phase 14 adds 4 new .py files to lib/; no compiled artifacts, no egg-info, no pyproject.toml change. **Verify after planning** that no plan introduces a new top-level package that would need `pip install -e .` refresh. | None expected |

**Nothing found in any category:** State explicitly — verified by direct inspection of `lib/`, `data/cache/`, `data/`, `orchestration/`, `scripts/`, `pyproject.toml`, and the CONTEXT.md "Out of scope" + "Existing Code Insights" sections.

## Common Pitfalls

### Pitfall 1: Conventional PMI rate is NOT in any reference YAML

**What goes wrong:** Plan assumes `lib.rules.conventional_pmi.status()` returns a PMI rate; assigns `monthly_mi = principal × pmi_rate / 12` per cell. Engine fails at runtime — predicate returns a `TerminationStatus` enum, not a rate. Or worse: plan hardcodes "0.5% / year" for PMI and silently mis-rates the analysis for FICO < 720 borrowers.

**Why it happens:** Phase 4 D-02 + RESEARCH Open Q#1 documented this carve-out, but it's easy to miss when composing primitives.

**How to avoid:** Phase 14 has to source conventional PMI somehow. Three viable approaches (planner picks):
  1. **Caller-supplied at request boundary** (Phase 4 idiom): `Household.monthly_pmi_for_conventional: Money | None`. Forces the user to enter their MGIC/Genworth quote in `household.yml`. Honest about "no public table exists."
  2. **Industry-rule-of-thumb constant** in `lib/property_analysis.py`: `_CONV_PMI_ANNUAL_RATE: Final[Decimal] = Decimal("0.0075")` (mid-range estimate). Document loudly that this is a placeholder; surface a `WARNING: PMI rate estimated` reason on every Conv30/Conv15 row with LTV > 0.80.
  3. **New `data/reference/property-analysis-heuristics.yml`** (planned for Phase 16) carrying a PMI-by-FICO-by-LTV grid sourced from a published lender schedule. Phase 14 reads this; surfaces `WARNING: PMI rate estimated from published schedule, your quote may differ`.

**Recommendation (researcher's call):** Approach 2 for Phase 14 (matches v1.0 "fail loud, ship something" doctrine), with Phase 16 swapping in approach 3 via the YAML refresh path. Mark both Conv30 and Conv15 rows with `eligible_reasons += ["PMI-RATE-ESTIMATED-0.0075"]` so the verdict reason cascade can cite the estimate.

**Warning signs:** Plan mentions `pmi_rate` without citing a reference YAML or a caller-input field; Phase 14 fixture assertions on Conv30 PITI fail.

### Pitfall 2: Float contamination in DP fan-out

**What goes wrong:** Loop writes `for dp_pct in [0.03, 0.05, 0.10, 0.15, 0.20, 0.25]:` → `loan_amount = price × (1 - dp_pct)` → pydantic raises `ValidationError: input is a float, not Decimal` at the AmortizeRequest boundary.

**Why it happens:** Python literal `0.03` is a float; Phase 14's models all require `Decimal` via `strict=True`.

**How to avoid:** Module-level constant:
```python
DOWN_PAYMENT_PCTS: Final[list[Rate]] = [
    Decimal("0.03"),
    Decimal("0.05"),
    Decimal("0.10"),
    Decimal("0.15"),
    Decimal("0.20"),
    Decimal("0.25"),
]
```
Pattern mirrors Phase 3 D-04 rate conversions and `lib/stress.py` rate lists.

**Warning signs:** `mypy --strict` complains about `Decimal` × `float` ops; pydantic ValidationError mentions "input_type=float".

### Pitfall 3: Mixing `Money` (ge=0) and signed Decimals

**What goes wrong:** Refi block needs `monthly_savings` and `npv_60mo` which can be NEGATIVE (rate-up scenarios). Plan declares them as `Money` → pydantic rejects negative values at boundary.

**Why it happens:** `lib.models.Money` is `Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0"))]`. The `ge=Decimal("0")` blocks signed values.

**How to avoid:** Follow the Phase 6 `RefiCashflow.amount` precedent (lib/refinance.py L196-198): use raw `Decimal = Field(strict=True, max_digits=14, decimal_places=2)` — drop the `ge=0` but keep the digit constraints. Document in the field's docstring: "signed Decimal (NOT Money) because rate-up scenarios produce negative savings".

**Warning signs:** Plan declares `monthly_savings: Money` or `delta_vs_baseline_monthly: Money`.

### Pitfall 4: PMI/MIP/funding-fee LTV table lookup off-by-one (high-LTV band confusion)

**What goes wrong:** FHA MIP table has rows with `ltv_max: "1.00"` and `ltv_max: "0.95"`. A loan with LTV=0.96 falls in the 0.95-1.00 band, but a naive lookup that uses `<=` on both sides finds either no row or the wrong row. Worse: BL-03 fix in `data/reference/fha-mip-rates.yml` shows a HIGH-balance LTV<=0.78 row was missing pre-fix — any caller that reused that pattern silently raises LookupError.

**Why it happens:** Inclusivity convention (low-inclusive, high-inclusive vs low-inclusive, high-exclusive) varies across YAMLs. `data/reference/va-funding-fees.yml` is exclusive-upper (per its notes "0..<5 means less than 5%"). `data/reference/fha-mip-rates.yml` uses inclusive-both. **[CITED: fha-mip-rates.yml L22 + va-funding-fees.yml L31]**

**How to avoid:** Don't roll your own lookup — call the existing predicates (`lib.rules.fha_mip.compute(...)`, `lib.rules.va_funding_fee.compute(...)`) which encode the inclusivity correctly. If you must do your own range check, write a fixture asserting the boundary case (e.g., LTV=0.78 exactly, LTV=0.90 exactly).

**Warning signs:** Plan has `if ltv > 0.78 and ltv <= 0.90:` or similar inline range checks; missing fixture for boundary LTV.

### Pitfall 5: Conforming-limit lookup needs `County(state_fips, county_fips, name)`, NOT zip

**What goes wrong:** Plan writes `if listing.price > conforming_limit_for_zip(listing.zip):` and tries to thread zip → conforming-limit directly.

**Why it happens:** `PropertyListing.zip` is a 5-digit string, but `lib.rules.loan_type.classify(loan_amount, county, program)` takes a `County` Pydantic model with `state_fips: "53"`, `county_fips: "033"`, `name: "King"`. **[VERIFIED: lib/rules/loan_type.py L69 + lib/rules/types.py]** The YAML `conforming-limits-2026.yml` is keyed by (state_fips, county_fips), NOT zip. No zip→county lookup table ships in v1.

**How to avoid:** `state_fips + county_fips + county_name` live on **Household** (per `config/household.example.yml` L21-31 — "state_fips + county_fips are REQUIRED keys"). Pass these from `household` arg, NOT from listing. Recommended Household field shape (see Pattern 3 above) already includes them. Phase 14's `analyze()` constructs the `County` from `household.{state_fips, county_fips, county_name}` once and reuses it across cells.

**Warning signs:** Plan tries to extract county from `listing.zip`; no `lib.rules.types.County` import.

### Pitfall 6: PMI/MIP NOT in DTI calculation, vs IS in PITI

**What goes wrong:** Cell computes `dti_back = (P&I + tax + insurance + HOA + obligations) / income` but FORGETS to add monthly MI. Industry convention (and Phase 4's `_compute_piti` per affordability docstring) includes MI in PITI, hence in DTI.

**Why it happens:** "PITI" abbreviation is P+I+T+I — MI is the silent fifth letter.

**How to avoid:** Compose PITI explicitly as `piti = monthly_pi + monthly_tax + monthly_insurance + monthly_hoa + monthly_mi` (mirror Phase 4 `_compute_piti` signature). Fixture assertion: hand-calc a Conv30 95% LTV cell and pin the PITI dollar amount to include the PMI component.

**Warning signs:** Test fixture's PITI is suspiciously close to (P&I + escrow) without PMI/MIP added.

### Pitfall 7: Verdict reason format drift across blocker codes

**What goes wrong:** D-14-VERDICT-04 requires "every reason cites both predicate identifier AND computed numeric value." Plan emits free-form strings like "DTI too high (52%)" — these don't match `lib/rules/*` blocker codes (`DTI-CAP-CONVENTIONAL`, `LTV-CEILING-FHA`, etc.) and can't be regex-asserted by a citation-coverage meta-test.

**Why it happens:** Phase 4 + Phase 6 blocker codes are PREFIXED constants (`BLOCKED_BY_*` in `lib/affordability.py` L305-325). Phase 14's NEW blocker codes (MIP-BURDEN, STRESS-INCOME, etc.) need the same prefix discipline.

**How to avoid:** Ship a constants block at the top of `lib/property_verdict.py`:
```python
# lib/property_verdict.py — predicate codes for verdict reasons (D-14-VERDICT-04)
VERDICT_NO_GO_DTI_ALL_PROGRAMS: Final[str] = "DTI-CEILING-ALL-PROGRAMS"
VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP: Final[str] = "NO-ELIGIBLE-AT-PREFERRED-DP"
VERDICT_WATCH_FHA_MIP_BURDEN: Final[str] = "MIP-BURDEN-FHA"
VERDICT_WATCH_STRESS_INCOME_FAIL: Final[str] = "STRESS-INCOME-SHOCK"
VERDICT_WATCH_STRESS_RATE_FAIL: Final[str] = "STRESS-RATE-SHOCK"        # if planner chooses to fire
VERDICT_WATCH_STRESS_ARM_RESET: Final[str] = "STRESS-ARM-RESET"
VERDICT_GO: Final[str] = "GO-ALL-GREEN"
```
Then mirror Phase 4 + Phase 8's citation-coverage meta-test:
```python
# tests/test_property_verdict.py
def test_verdict_code_citation_coverage(...):
    """Every VERDICT_* constant must appear in at least one fixture's verdict.reasons[].predicate_code."""
```

**Warning signs:** Plan has free-form verdict reason strings; no module-level constants for predicate codes.

### Pitfall 8: ARM 5/1 stress requires the FULL ARMRequest shape, not just a rate

**What goes wrong:** Plan calls `lib.stress.evaluate(ArmResetRequest(loan=conv30_loan, paths=[...]))` but `ArmResetRequest.base_arm_request` is an `ARMRequest`, not a `Loan`. The plan crashes at pydantic validation.

**Why it happens:** `ARMRequest` requires `arm_terms: ARMTerms` (8+ required fields: initial_period_months, reset_period_months, initial_cap_bps, periodic_cap_bps, lifetime_cap_bps, floor_rate, margin_bps, index_series_id) + `assumed_index_rate: Rate`. **[VERIFIED: lib/arm.py L87-105]** Phase 5 D-02 locked `floor_rate` as REQUIRED (no default).

**How to avoid:** Hardcode the conventional 5/1 ARM terms as a module-level constant in `lib/property_analysis.py`:
```python
_CONV_5_1_ARM_TERMS: Final[ARMTerms] = ARMTerms(
    initial_period_months=60,
    reset_period_months=12,
    initial_cap_bps=500,           # 5pp first-reset cap (industry standard)
    periodic_cap_bps=200,           # 2pp subsequent-reset cap
    lifetime_cap_bps=500,           # 5pp lifetime cap vs note_rate
    floor_rate=Decimal("0.025"),    # 2.5% floor (industry standard)
    margin_bps=250,                 # 2.5pp margin over index
    index_series_id="MORTGAGE30US", # v1.0 placeholder per Phase 5 D-06
)
```
Surface these constants in references docs (Phase 18) so future-you knows they're policy choices, not regulatory.

**Warning signs:** Plan passes a Loan directly to `ArmResetRequest`; no `ARMTerms` instantiation.

### Pitfall 9: FRED cache reads not serialized through `with_cache_lock`

**What goes wrong:** Plan does `entry = lib.fred_cache._load_cache("MORTGAGE30US")` directly. Two parallel `analyze()` invocations (e.g., user analyzes two listings in quick succession) race on the cache file.

**Why it happens:** `_load_cache` is a private helper exposed for inspection only. The public path is `get_cached_or_fetch(series_id, fetcher=...)` which internally uses `_save_cache` which wraps `with_cache_lock`.

**How to avoid:** Always call through `get_cached_or_fetch`. If you only need to READ (no fetch), you still want the lock for read-after-write consistency. Pattern:
```python
from lib.fred_cache import get_cached_or_fetch, with_cache_lock, CACHE_DIR

def _todays_rate(series_id: str) -> Rate:
    """Read today's rate from FRED cache; raise if stale and no live fetcher available."""
    with with_cache_lock(CACHE_DIR, reason=f"property-analysis read {series_id}"):
        entry = get_cached_or_fetch(
            series_id,
            fetcher=None,   # Phase 14 lib does NOT live-fetch; raises if cold
        )
    return quantize_rate(Decimal(entry["value"]))
```
If `fetcher=None` and cache is cold, `get_cached_or_fetch` raises `NotImplementedError`. Phase 14 catches and converts to a ValueError with guidance ("Run `scripts/fred_cli.py get MORTGAGE30US --latest` to refresh cache").

**Warning signs:** Plan imports `_load_cache` or accesses `_cache_path` directly; no `with_cache_lock` usage.

### Pitfall 10: AnalysisReport JSON > 100KB blows the Phase 8 D-02 budget pattern

**What goes wrong:** Plan ships a full `Schedule.payments[]` for every (program, DP) cell. 30 cells × 360 monthly payments × ~200 bytes = 2.16MB JSON. Phase 8 D-02 pinned 100KB as the upper bound for stress responses.

**Why it happens:** Easy to absent-mindedly include the full Schedule when ProgramResult only needs scalars.

**How to avoid:** Mirror Phase 8 D-03 explicitly: `ProgramResult` carries SUMMARY SCALARS only. No `payments: list[Payment]`. If a downstream consumer needs the full schedule, they re-derive it via `lib.amortize.build_schedule(loan)` from the ProgramResult's `loan_amount + annual_rate + term_months`. Phase 14 fixture: assert `len(report.model_dump_json()) < 100_000`.

**Warning signs:** Plan has `payments: list[Payment]` on ProgramResult; fixture JSON size unbounded.

### Pitfall 11: IRS Pub 936 grandfathering booleans default-FALSE is correct for v1.1 scope

**What goes wrong:** Plan worries about pre-2017 vs post-2017 acquisition-debt rules and over-engineers the TaxBlock with `has_grandfathered_debt` + `binding_contract_signed_before_2017_12_15` + `binding_contract_closed_before_2018_04_01` fields propagated through the Profile.

**Why it happens:** `lib.rules.irs_pub936.qualified_loan_limit(...)` exposes 3 boolean knobs. **[VERIFIED: lib/rules/irs_pub936.py L66-90]** It's tempting to surface them all.

**How to avoid:** Phase 14's listings are all "user is considering buying THIS Zillow property TODAY" — by definition post-2017 acquisition. Default all three booleans to `False` (no grandfathering, no grace period). Call:
```python
cap = irs_pub936.qualified_loan_limit(filing_status=profile.filing_status)
# Defaults: has_grandfathered_debt=False, binding_contract_*=False
```
Returns $750,000 (single/MFJ/HoH) or $375,000 (MFS) for 2026 listings. The 4th-degree edge case ("user is refi'ing an existing pre-2017 mortgage into this property") is out of scope per D-14-REFI-01 (forward-only refi baseline). Document this assumption in the TaxBlock docstring.

**Warning signs:** Profile model has 3 IRS booleans; TaxBlock has a `grandfathered: bool` field.

### Pitfall 12: Citation-coverage meta-test missing → Phase 14 ships without traceability

**What goes wrong:** Phase 14 doesn't include a `test_property_verdict_citation_coverage` meta-test. Future verdict-code additions silently fail to appear in any fixture. The verdict reason cascade drifts over time without surfacing.

**Why it happens:** Phase 4 + Phase 8's citation-coverage tests are the existing convention but they live in separate test files; easy to forget to mirror.

**How to avoid:** Plan must include `tests/test_property_verdict.py::test_verdict_code_citation_coverage` that introspects `lib.property_verdict` for `VERDICT_*` constants via `grep` and asserts each appears in at least one fixture file. Mirrors `tests/test_affordability.py:test_blocker_code_citation_coverage` pattern.

**Warning signs:** Plan lists 3 fixture files but no meta-test asserting all verdict codes are exercised.

## Code Examples

> **Sources:** All code patterns below are verified against actual files in `/Users/cujo253/Documents/mortgage-ops/lib/` as of 2026-05-17. Every import + signature confirmed by direct read of the source.

### Example 1: Per-cell P&I computation via `lib.amortize.build_schedule`

```python
# Source: lib/amortize.py L255-292 (build_schedule signature)
from decimal import Decimal
from lib.amortize import build_schedule
from lib.models import Loan
from lib.money import quantize_cents

def _compute_cell_pi(
    loan_amount: Decimal,
    annual_rate: Decimal,
    term_months: int,
) -> Decimal:
    """Return monthly P&I for one matrix cell.

    Per Phase 3 D-04: period_rate = annual_rate / 12. Phase 3 D-09 final-period
    cleanup ensures monthly_pi cleanly amortizes to balance=0.00 at term.
    """
    loan = Loan(
        principal=quantize_cents(loan_amount),
        annual_rate=annual_rate,
        term_months=term_months,
        loan_type="fixed",
        # origination_date=None → Phase 3 D-12 synthesizes datetime.now(UTC).date()
    )
    schedule = build_schedule(loan, frequency="monthly")
    return schedule.monthly_pi  # already quantize_cents'd per Phase 3 D-15
```

### Example 2: FHA UFMIP financing into principal (Phase 4 D-03)

```python
# Source: lib/affordability.py L36-40 D-03 + lib/rules/fha_mip.py L65-130
from datetime import date
from decimal import Decimal
from lib.amortize import build_schedule
from lib.models import Loan
from lib.money import quantize_cents
from lib.rules.fha_mip import compute as fha_mip_compute

def _compute_fha_cell(
    listing_price: Decimal,
    down_payment_pct: Decimal,
    term_months: int,
    annual_rate: Decimal,
    endorsement_date: date,
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (monthly_pi_with_financed_ufmip, monthly_mip, ufmip_dollar).

    Phase 4 D-03 lock: UFMIP is auto-financed into the loan principal (NOT cash).
    Pre-quantization needed at UFMIP composition so end-state respects Money decimal_places.
    """
    base_loan = quantize_cents(listing_price * (Decimal("1") - down_payment_pct))
    property_value = quantize_cents(listing_price)
    # Use a sentinel Loan for the predicate (the predicate only uses .principal).
    sentinel_loan = Loan(
        principal=base_loan,
        annual_rate=annual_rate,
        term_months=term_months,
        loan_type="fha",
    )
    mip = fha_mip_compute(sentinel_loan, property_value, endorsement_date)

    financed_principal = quantize_cents(base_loan + mip.ufmip)
    financed_loan = Loan(
        principal=financed_principal,
        annual_rate=annual_rate,
        term_months=term_months,
        loan_type="fha",
    )
    pi = build_schedule(financed_loan, frequency="monthly").monthly_pi
    monthly_mip = quantize_cents(financed_principal * mip.annual_mip_pct / Decimal("12"))
    return pi, monthly_mip, mip.ufmip
```

### Example 3: FRED rate fetch through `with_cache_lock`

```python
# Source: lib/fred_cache.py L235-356 + Phase 12 D-12-LIVE02-01
from decimal import Decimal
from lib.fred_cache import CACHE_DIR, get_cached_or_fetch, with_cache_lock
from lib.money import quantize_rate

def _todays_rate_per_program(program: str) -> Decimal:
    """Return today's rate for the given program. D-14-REFI-02.

    Conv30/FHA30/VA30/Jumbo30 → MORTGAGE30US
    Conv15                    → MORTGAGE15US
    Conv30 ARM 5/1            → MORTGAGE30US - 0.0025 (25bps below)
    """
    if program == "Conv15":
        series_id = "MORTGAGE15US"
        delta = Decimal("0")
    elif program == "Conv30-ARM-5-1":
        series_id = "MORTGAGE30US"
        delta = Decimal("-0.0025")
    else:
        series_id = "MORTGAGE30US"
        delta = Decimal("0")

    with with_cache_lock(CACHE_DIR, reason=f"property-analysis read {series_id}"):
        entry = get_cached_or_fetch(series_id, fetcher=None)
        # Note: fetcher=None means raise NotImplementedError if cache cold.
        # Phase 14 lib does NOT live-fetch; Phase 15 CLI orchestrator handles
        # the cold-cache path by invoking scripts/fred_cli.py first.

    raw = Decimal(str(entry["value"]))  # FRED returns numeric strings already
    return quantize_rate(raw + delta)
```

### Example 4: DP fan-out loop with explicit ineligible-row population

```python
# Source: pattern derived from lib/affordability.py D-11 blocker cascade +
#         CONTEXT.md D-14-MATRIX-02 ("numeric fields computed anyway")
from decimal import Decimal
from typing import Final
from lib.affordability import evaluate as affordability_evaluate
from lib.models import Money, Rate
from lib.money import quantize_cents, quantize_rate

DOWN_PAYMENT_PCTS: Final[list[Rate]] = [
    Decimal("0.03"),
    Decimal("0.05"),
    Decimal("0.10"),
    Decimal("0.15"),
    Decimal("0.20"),
    Decimal("0.25"),
]

PROGRAMS_BASE: Final[list[str]] = ["Conv30", "Conv15", "FHA30"]  # VA30 + Jumbo30 added conditionally

def _build_matrix(
    listing,           # PropertyListing
    household,         # Household (NEW Phase 14)
    profile,           # Profile (NEW Phase 14)
    todays_rates,      # dict[str, Rate]
) -> list:             # list[ProgramResult]
    programs = list(PROGRAMS_BASE)
    if profile.va_eligible:
        programs.append("VA30")

    # Conforming-limit lookup (D-14-MATRIX-03) — see Pitfall 5 for County construction
    from lib.rules.types import County
    from lib.rules.loan_type import classify, MissingCountyDataError
    county = County(
        state_fips=household.state_fips,
        county_fips=household.county_fips,
        name=household.county_name,
    )
    try:
        classification = classify(listing.price, county, program="conventional")
        if classification == "jumbo":
            programs.append("Jumbo30")
    except MissingCountyDataError:
        # County not in high-cost subset AND price > baseline → can't classify.
        # Phase 14 surfaces this as a top-level AnalysisReport warning; per cell
        # we treat as conforming-baseline (best-effort).
        pass

    cells: list = []
    for program in programs:
        for dp_pct in DOWN_PAYMENT_PCTS:
            loan_amount = quantize_cents(listing.price * (Decimal("1") - dp_pct))
            # ... compute P&I, MI, PITI, DTI, LTV per program ...
            # On blocker (e.g., DTI > ceiling), eligible=False but ALL numerics populated.
            # On pass, eligible=True with empty blocker_reasons.
            cells.append(...)  # ProgramResult(...)
    return cells
```

### Example 5: Verdict synthesis with falsifiable reason citations

```python
# Source: lib/property_verdict.py (NEW Phase 14) — pattern from
#         lib/affordability.py D-11 blocker cascade + D-14-VERDICT-01..04
from decimal import Decimal
from typing import Final, Literal

VERDICT_NO_GO_DTI_ALL_PROGRAMS: Final[str] = "DTI-CEILING-ALL-PROGRAMS"
VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP: Final[str] = "NO-ELIGIBLE-AT-PREFERRED-DP"
VERDICT_WATCH_FHA_MIP_BURDEN: Final[str] = "MIP-BURDEN-FHA"
VERDICT_WATCH_STRESS_INCOME_FAIL: Final[str] = "STRESS-INCOME-SHOCK"
VERDICT_GO: Final[str] = "GO-ALL-GREEN"

# D-14-VERDICT-01: $300/mo MIP burden threshold (policy choice, see Sources)
_MIP_BURDEN_THRESHOLD: Final[Decimal] = Decimal("300.00")

def synthesize(matrix, stress, household, profile):
    """D-14-VERDICT-01..04 cascade. Returns Verdict(level, headline_reason, reasons[])."""
    preferred = household.preferred_down_payment_pct
    cells_at_preferred = [c for c in matrix.cells if c.down_payment_pct == preferred]
    eligible_at_preferred = [c for c in cells_at_preferred if c.eligible]
    non_fha_eligible = [c for c in eligible_at_preferred if c.program != "FHA30"]

    # Level 1: NO_GO if no eligible at any DP across any program
    if not any(c.eligible for c in matrix.cells):
        return Verdict(
            level="NO_GO",
            headline_reason="No program qualifies at any DP scenario",
            reasons=[VerdictReason(
                predicate_code=VERDICT_NO_GO_DTI_ALL_PROGRAMS,
                computed_value=str(min(c.dti_back for c in matrix.cells)),
            )],
        )

    # Level 2: NO_GO if no eligible at preferred DP
    if not eligible_at_preferred:
        return Verdict(
            level="NO_GO",
            headline_reason=f"No program qualifies at preferred DP {preferred}",
            reasons=[VerdictReason(
                predicate_code=VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP,
                computed_value=str(preferred),
                dp_pct=preferred,
            )],
        )

    # Level 3 (D-14-VERDICT-02): WATCH if ANY eligible-at-preferred fails income shock
    income_stress_fails = [
        s for s in stress.rows
        if s.stress_kind == "income_shock" and s.breaches_dti_ceiling
        and any(c.program == s.program and c.eligible for c in cells_at_preferred)
    ]
    if income_stress_fails:
        return Verdict(
            level="WATCH",
            headline_reason="Income-shock stress breaches DTI ceiling for at least one eligible program",
            reasons=[VerdictReason(
                predicate_code=VERDICT_WATCH_STRESS_INCOME_FAIL,
                computed_value=str(f.stressed_dti_back),
                program=f.program,
            ) for f in income_stress_fails],
        )

    # Level 4 (D-14-VERDICT-01 + D-14-VERDICT-03): WATCH if FHA-only eligible AND MIP > $300
    if not non_fha_eligible:  # all eligible-at-preferred are FHA
        fha_cells = [c for c in eligible_at_preferred if c.program == "FHA30"]
        if fha_cells and fha_cells[0].monthly_mi > _MIP_BURDEN_THRESHOLD:
            return Verdict(
                level="WATCH",
                headline_reason=f"FHA-only path with monthly MIP {fha_cells[0].monthly_mi} > ${_MIP_BURDEN_THRESHOLD}",
                reasons=[VerdictReason(
                    predicate_code=VERDICT_WATCH_FHA_MIP_BURDEN,
                    computed_value=str(fha_cells[0].monthly_mi),
                    program="FHA30",
                    dp_pct=preferred,
                )],
            )

    # Level 5: GO
    return Verdict(
        level="GO",
        headline_reason=f"{len(non_fha_eligible)} non-FHA program(s) eligible at preferred DP",
        reasons=[VerdictReason(
            predicate_code=VERDICT_GO,
            computed_value=str(len(non_fha_eligible)),
        )],
    )
```

### Example 6: Three golden-value fixture organization (mirrors Phase 4 convention)

```
tests/fixtures/property_analysis/
  sfh_conforming_king_county.json
  condo_with_hoa_seattle.json
  sfh_jumbo_bay_area.json
```

```json
// tests/fixtures/property_analysis/sfh_conforming_king_county.json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "id": "sfh_conforming_king_county",
  "source": "Hand-computed; King County WA conforming limit $1,027,000 (2026); Conv30/Conv15/FHA30 all eligible at 20% DP",
  "rounding": "ROUND_HALF_UP",
  "notes": "SFH @ $625,000 in King County WA; household income $12k/mo, debts $400/mo, FICO 740, 20% DP preferred; Conv30 PITI = $X (hand-calc anchor)",
  "listing": { ... PropertyListing fields ... },
  "household": { ... Household (lib/household.py) fields ... },
  "profile": { ... Profile (lib/profile.py) fields ... },
  "fred_rates": {
    "MORTGAGE30US": "0.065000",
    "MORTGAGE15US": "0.058000"
  },
  "expected": {
    "matrix": {
      "cells_count": 24,
      "programs_present": ["Conv30", "Conv15", "FHA30"],
      "preferred_dp_cells": [
        {"program": "Conv30", "dp_pct": "0.20", "monthly_pi": "...", "piti": "...", "eligible": true, "blocker_reasons": []},
        ...
      ]
    },
    "stress": { ... },
    "refi": { ... },
    "points": { ... },
    "tax": { ... },
    "verdict": {
      "level": "GO",
      "headline_reason": "...",
      "reasons": [{"predicate_code": "GO-ALL-GREEN", "computed_value": "2"}]
    }
  }
}
```

**One-fixture-per-file convention** lifted from Phase 4 (`tests/fixtures/affordability/`). Diffs stay readable; pytest parametrization picks fixture by stem.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `numpy_financial.irr` for breakeven | Cumulative-NPV scan via `numpy_financial.npv` | Phase 6 D-06 (2026-04) | Avoids known bug #131 (arch-dependent results). Phase 14's refi block inherits the bug-avoidance free. |
| Phase 4 affordability hardcoded blocker codes | `BLOCKED_BY_*: Final[str]` module-level constants + citation-coverage meta-test | Phase 4 + Phase 6 D-11 | Phase 14's `VERDICT_*` constants follow the same pattern; meta-test asserts coverage. |
| `lib.fred_cache._load_cache` direct reads | `get_cached_or_fetch(series_id, fetcher=...)` + `with_cache_lock` | Phase 12 CR-01 (2026-05) | Phase 14 inherits the always-exit-0 envelope contract; cold-cache no longer crashes downstream. |
| Manual cap-precedence in ARM | `applied_cap: Literal["initial","periodic","lifetime","floor","none"]` on `ResetEvent` | Phase 5 D-03 (2026-04) | Phase 14's ARM-reset stress automatically gets the cap-classifier for free. |

**Deprecated/outdated:**
- 43% DTI hard cap (ATR/QM pre-2021): **GONE** per CFPB price-based General QM Final Rule. PROJECT.md L127 marks it as "heuristic only." Phase 14's verdict cascade should NOT treat 43% as a regulatory line; defer to user's `max_dti` (already on Phase 4 Household).
- Subprocess-per-cell composition: rejected in favor of in-process import (research §Pattern 3, "wall-clock under one second").

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The $300/mo MIP-burden threshold (D-14-VERDICT-01) has no published HUD/MBA equivalent. Confirmed by web search 2026-05-17: no $300 figure surfaces in HUD Mortgagee Letters, FHA Handbook 4000.1, or MBA published guidance. | Pitfall §"MIP-burden $300" + Sources | LOW — CONTEXT.md already marks this as policy choice; Phase 14 ships the threshold as-is. Tagged `[ASSUMED]` here so future-you knows it's not data-driven. |
| A2 | The conventional 5/1 ARM defaults (initial_cap=500bps, periodic_cap=200bps, lifetime_cap=500bps, floor_rate=Decimal("0.025"), margin_bps=250) are industry-standard for D-14-STRESS-03. | Pitfall §"ARM 5/1 stress" + Code Example 8 | MEDIUM — these are the Phase 5 D-06 documented common values, but ARM terms vary by lender. If wrong, the ARM-reset stress row over- or under-states the peak rate by ~50-100bps. Surface as a module constant Phase 18 documents. |
| A3 | The 1pt and 2pt rate-drop convention is "0.0025 rate drop per point" (25bps per discount point). | Architecture §"PointsBlock" + Code Example | MEDIUM — common industry rule-of-thumb, but actual drops vary by lender and rate environment (sometimes 12.5bps, sometimes 50bps). If wrong, breakeven months are mis-stated. Document loudly as a policy choice. |
| A4 | Phase 14 fixtures should treat all loans as POST-2017 acquisition (no grandfathering for IRS Pub 936). | Pitfall 11 | LOW — by definition the user is buying a Zillow listing TODAY, so post-2017 is correct for the listing itself. Edge case (user owns a pre-2017 mortgage on a different property) is out of scope per D-14-REFI-01. |
| A5 | Conventional PMI for D-14-MATRIX-02's "computed anyway" cells uses an estimated 0.0075 annual rate (75bps) as a placeholder until Phase 16 ships the property-analysis-heuristics.yml table. | Pitfall 1 | MEDIUM — real PMI rates range 0.50-1.25% depending on FICO + LTV. If a user's actual FICO is 660, our PMI estimate may be 30-50% low. Surface a `PMI-RATE-ESTIMATED` warning on every conventional row with LTV > 0.80 so the user knows. |
| A6 | Phase 14 does NOT need a Pydantic v2 discriminated union on ProgramResult (one shape works for all 5 programs). | Pattern 1 + Architecture | LOW — fields are identical; `program: Literal[...]` works as a non-union discriminator. If a future program (e.g., USDA-30) introduces program-specific fields, planner refactors. |
| A7 | Cash-to-close computation = `down_payment + estimated_closing_costs + (UFMIP-if-not-financed)`. For Phase 14 the closing-costs estimate is a placeholder constant (~3% of loan_amount); real closing costs come from a Loan Estimate the user doesn't have yet. | Pattern 1 (ProgramResult.cash_to_close) | MEDIUM — closing costs are listing-specific. If the report's cash-to-close is 30% off, the verdict's "Cash-to-close consumes >80% of liquid reserves" trigger (mentioned in research §Pattern 4) may fire wrong. Mark `closing_costs_estimated: bool` on ProgramResult so Phase 15 surfaces a warning. |

## Open Questions

1. **Points breakeven applies to which programs?**
   - What we know: D-14-STRESS-03 limits ARM-reset stress to Conv30 only. Points buydown is a separate mechanism not constrained by the CONTEXT.md decisions.
   - What's unclear: should the PointsBlock fan out across Conv30, Conv15, FHA30, VA30, Jumbo30 — or only Conv30/Conv15/Jumbo30 (since FHA + VA already carry MIP/funding-fee burdens that distort breakeven economics)?
   - Recommendation: Conv30 + Conv15 + Jumbo30 only. Mark FHA + VA as "points not modeled" with a `WARNING-NO-POINTS-FOR-FHA-VA` reason in the PointsBlock. Planner confirms; this is policy.

2. **How does Phase 14 resolve conventional PMI rate for the matrix?** (See Pitfall 1.)
   - What we know: Phase 4 RESEARCH Open Q#1 documented the carve-out (no public YAML; bureau-specific quotes).
   - What's unclear: which of approach 1 (caller-supplied), 2 (constant estimate), or 3 (deferred Phase 16 YAML) should Phase 14 ship?
   - Recommendation: approach 2 with a `WARNING-PMI-RATE-ESTIMATED` blocker-code-style warning per cell. Swap to approach 3 in Phase 16.

3. **Should the closing-costs estimate (Assumption A7) be configurable on Profile?**
   - What we know: cash-to-close calculation needs SOME closing-cost number. Industry rule-of-thumb is 2-5% of loan amount.
   - What's unclear: whether to surface as `profile.closing_costs_pct_estimate: Rate = Decimal("0.03")` or hardcode in `lib/property_analysis.py`.
   - Recommendation: hardcoded constant in `lib/property_analysis.py` for v1.1; if users want override, Profile gets the field in v1.2.

4. **Pre-flight County construction failure semantics.**
   - What we know: `lib.rules.loan_type.classify` raises `MissingCountyDataError` when `loan_amount > baseline AND county is None or county not in high-cost subset`.
   - What's unclear: should Phase 14's `analyze()` (a) fail loud and raise out (matching Phase 3 D-19 fail-loud doctrine), or (b) emit a top-level `AnalysisReport.warnings: list[str] += ["MissingCountyDataError"]` and continue with the conforming-baseline best-effort?
   - Recommendation: (b) — graceful degradation, since Phase 14 is library-level. Phase 15's CLI orchestrator decides whether to wrap in an always-exit-0 envelope. The user benefit (still get a partial report for an unknown-county listing) outweighs the strictness cost.

## Environment Availability

> Phase 14 is library-only code; no external CLI/runtime dependencies beyond Python + already-installed packages.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All lib/ code | ✓ (assumed; v1.0 ships at 3.12+) | 3.12+ | — |
| pydantic | All new models | ✓ | ≥2.6 | — |
| numpy-financial | lib.amortize (transitively) | ✓ | 1.0.0 | — |
| python-dateutil | lib.amortize (transitively) | ✓ | (installed) | — |
| FRED cache files | D-14-REFI-02 today's-rate | depends on whether `data/cache/fred_MORTGAGE30US.json` + `fred_MORTGAGE15US.json` exist + are fresh | — | Phase 14 lib raises NotImplementedError if cold; Phase 15 CLI orchestrator invokes `scripts/fred_cli.py` to refresh |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Cold FRED cache — handled at the Phase 15 orchestrator layer per the Phase 12 contract.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` (already in dev deps; `tests/conftest.py` ships `affordability_fixture`, `amortize_fixture`, `arm_fixture` loaders) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| Quick run command | `pytest tests/test_property_analysis.py tests/test_property_verdict.py tests/test_household.py tests/test_profile.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLZ-01 | Multi-program fan-out produces ProgramResult per (program, DP); jumbo triggers when price > conforming limit | unit + golden fixture | `pytest tests/test_property_analysis.py::test_matrix_fanout_conforming -x` | ❌ Wave 0 |
| ANLZ-01 | Conforming-limit MissingCountyDataError handled gracefully | unit | `pytest tests/test_property_analysis.py::test_missing_county_graceful -x` | ❌ Wave 0 |
| ANLZ-01 | VA30 included only when profile.va_eligible=True | unit | `pytest tests/test_property_analysis.py::test_va_eligibility_gates_program -x` | ❌ Wave 0 |
| ANLZ-02 | DownPaymentMatrix has 24 cells (no jumbo) or 30 cells (jumbo) | unit + golden | `pytest tests/test_property_analysis.py::test_matrix_cell_count -x` | ❌ Wave 0 |
| ANLZ-02 | Ineligible rows still populate all numerics per D-14-MATRIX-02 | unit | `pytest tests/test_property_analysis.py::test_ineligible_rows_populate_numerics -x` | ❌ Wave 0 |
| ANLZ-02 | DP sweep uses exact `Decimal("0.03"), ("0.05"), ("0.10"), ("0.15"), ("0.20"), ("0.25")` | unit | `pytest tests/test_property_analysis.py::test_dp_sweep_uses_decimal_strings -x` | ❌ Wave 0 |
| ANLZ-03 | Stress fan-out: 12-15 rows at preferred DP only (4-5 programs × 3 stresses minus ARM-non-Conv30) | unit + golden | `pytest tests/test_property_analysis.py::test_stress_at_preferred_dp_only -x` | ❌ Wave 0 |
| ANLZ-03 | ARM reset stress fires for Conv30 only (D-14-STRESS-03) | unit | `pytest tests/test_property_analysis.py::test_arm_reset_conv30_only -x` | ❌ Wave 0 |
| ANLZ-03 | Refi scan: 2 scenarios per program (FRED−1.00 AND FRED×0.85) | unit + golden | `pytest tests/test_property_analysis.py::test_refi_two_scenarios_per_program -x` | ❌ Wave 0 |
| ANLZ-03 | Points breakeven: 1pt and 2pt drops per Conv-family program (Open Question 1) | unit + golden | `pytest tests/test_property_analysis.py::test_points_breakeven_per_program -x` | ❌ Wave 0 |
| ANLZ-03 | IRS Pub 936 first-year interest + over-$750k flag per program | unit + golden | `pytest tests/test_property_analysis.py::test_tax_block_pub936 -x` | ❌ Wave 0 |
| VERD-01 | Verdict cascade: NO_GO if no eligible at any DP | unit | `pytest tests/test_property_verdict.py::test_no_go_no_eligible -x` | ❌ Wave 0 |
| VERD-01 | Verdict cascade: NO_GO if no eligible at preferred DP | unit | `pytest tests/test_property_verdict.py::test_no_go_at_preferred_dp -x` | ❌ Wave 0 |
| VERD-01 | Verdict cascade: WATCH if income-shock stress fails any eligible (D-14-VERDICT-02) | unit | `pytest tests/test_property_verdict.py::test_watch_income_shock -x` | ❌ Wave 0 |
| VERD-01 | Verdict cascade: WATCH if FHA-only eligible AND monthly MIP > $300 (D-14-VERDICT-01) | unit | `pytest tests/test_property_verdict.py::test_watch_fha_mip_burden -x` | ❌ Wave 0 |
| VERD-01 | Verdict cascade: GO when non-FHA eligible AND no stress fail (D-14-VERDICT-03) | unit | `pytest tests/test_property_verdict.py::test_go_non_fha_eligible -x` | ❌ Wave 0 |
| VERD-01 | Every VERDICT_* constant appears in at least one fixture (citation coverage) | meta-test | `pytest tests/test_property_verdict.py::test_verdict_code_citation_coverage -x` | ❌ Wave 0 |
| VERD-01 | Each VerdictReason carries both predicate_code AND computed_value (D-14-VERDICT-04) | unit + golden | `pytest tests/test_property_verdict.py::test_reason_format_compliance -x` | ❌ Wave 0 |
| (model) | Household model rejects extra fields | unit | `pytest tests/test_household.py::test_extra_forbid -x` | ❌ Wave 0 |
| (model) | Profile model defaults va_eligible=False | unit | `pytest tests/test_profile.py::test_va_eligible_default -x` | ❌ Wave 0 |
| (composition) | Money fields reject float inputs (strict=True) | unit | `pytest tests/test_property_analysis.py::test_float_rejection -x` | ❌ Wave 0 |
| (composition) | AnalysisReport JSON size < 100KB (Pitfall 10 budget) | invariant | `pytest tests/test_property_analysis.py::test_report_size_budget -x` | ❌ Wave 0 |
| (composition) | FRED cache reads serialize through with_cache_lock | unit | `pytest tests/test_property_analysis.py::test_fred_lock_serialization -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_property_analysis.py tests/test_property_verdict.py tests/test_household.py tests/test_profile.py -x` (target < 5s)
- **Per wave merge:** `pytest -x` (full suite, target < 30s)
- **Phase gate:** Full suite green before `/gsd-verify-work`; 3 golden-fixture tests pin every cell of every block by exact Decimal equality (D-18 inherited).

### Fixture Organization

**Recommendation: one fixture file per case (matches Phase 4 `affordability/`, Phase 5 `arm/`, Phase 8 `stress/` conventions).**

```
tests/fixtures/property_analysis/
  sfh_conforming_king_county.json     # SFH @ $625k in King WA; Conv30/Conv15/FHA30 eligible at 20% DP; verdict=GO
  condo_with_hoa_seattle.json         # Condo @ $475k in Seattle; HOA $450/mo; PMI applies at 95% LTV; verdict=GO or WATCH
  sfh_jumbo_bay_area.json             # SFH @ $1.85M in Santa Clara CA; Jumbo30 row appears; FHA + Conv30/15 ineligible; verdict=? (planner pins)
```

**Rationale (one-fixture-per-file vs one-file-three-cases):**
- One-fixture-per-file is the EXISTING repo convention. `tests/conftest.py:property_analysis_fixture` (NEW) follows `affordability_fixture` shape (load by stem).
- Diff readability: when a single cell's expected PITI changes, the PR diff touches one file, not a 3-case mega-fixture.
- Pytest parametrization: `@pytest.mark.parametrize("stem", ["sfh_conforming_king_county", "condo_with_hoa_seattle", "sfh_jumbo_bay_area"])` enumerates cases cleanly.

**Assertion patterns (matches CLAUDE.md "exact Decimal equality" rule):**

```python
# tests/test_property_analysis.py
import json
from decimal import Decimal
from pathlib import Path

from lib.property_analysis import analyze
from lib.property_listing import PropertyListing
from lib.household import Household
from lib.profile import Profile

def test_sfh_conforming_king_county_golden(property_analysis_fixture):
    fx = property_analysis_fixture("sfh_conforming_king_county")
    listing = PropertyListing(**fx["listing"])
    household = Household(**fx["household"])
    profile = Profile(**fx["profile"])

    # Pin FRED rates (no live fetch in tests)
    report = analyze(
        listing, household, profile,
        fred_mortgage_30us=Decimal(fx["fred_rates"]["MORTGAGE30US"]),
        fred_mortgage_15us=Decimal(fx["fred_rates"]["MORTGAGE15US"]),
    )

    # Cell count assertion
    assert len(report.matrix.cells) == fx["expected"]["matrix"]["cells_count"]

    # Exact Decimal equality per CLAUDE.md money discipline
    for expected_cell in fx["expected"]["matrix"]["preferred_dp_cells"]:
        actual = next(
            c for c in report.matrix.cells
            if c.program == expected_cell["program"]
            and c.down_payment_pct == Decimal(expected_cell["dp_pct"])
        )
        assert actual.monthly_pi == Decimal(expected_cell["monthly_pi"])
        assert actual.piti == Decimal(expected_cell["piti"])
        assert actual.eligible == expected_cell["eligible"]
        assert actual.blocker_reasons == expected_cell["blocker_reasons"]

    # Verdict assertion (D-14-VERDICT-04 format compliance)
    assert report.verdict.level == fx["expected"]["verdict"]["level"]
    for expected_reason in fx["expected"]["verdict"]["reasons"]:
        # Each reason must cite predicate_code AND computed_value
        assert any(
            r.predicate_code == expected_reason["predicate_code"]
            and r.computed_value == expected_reason["computed_value"]
            for r in report.verdict.reasons
        )
```

**Test counts per primitive composition:**

| Primitive Composed | Unit Tests | Golden Fixture Touches |
|--------------------|------------|-----------------------|
| `lib.amortize.build_schedule` (PITI driver) | 1 test (`test_cell_pi_computation_matches_amortize`) | All 3 fixtures (every preferred-DP cell) |
| `lib.affordability.evaluate` (DTI/blocker) | 2 tests (forward eligible + forward blocked) | All 3 fixtures |
| `lib.arm.build_arm_schedule` (5/1 ARM stress) | 1 test (`test_arm_reset_stress_conv30_only`) | sfh_conforming + sfh_jumbo (Conv30 paths only) |
| `lib.stress.evaluate` (3 stress modes) | 3 tests (one per mode) | All 3 fixtures |
| `lib.points.evaluate` (breakeven) | 1 test (`test_points_per_program`) | All 3 fixtures (Conv-family rows only) |
| `lib.refinance.evaluate` (refi NPV) | 1 test (`test_refi_two_scenarios`) | All 3 fixtures |
| `lib.rules.fha_mip.compute` (MIP block) | 1 test (`test_fha_mip_per_cell`) | sfh_conforming + condo_with_hoa |
| `lib.rules.va_funding_fee.compute` (VA fee) | 1 test (`test_va_funding_fee_per_cell`) | sfh_conforming (if va_eligible=True) |
| `lib.rules.irs_pub936.qualified_loan_limit` | 1 test (`test_tax_block_pub936`) | All 3 fixtures (sfh_jumbo specifically asserts over-cap flag=True) |
| `lib.rules.loan_type.classify` (jumbo trigger) | 1 test (`test_jumbo_trigger_at_county_limit`) | sfh_jumbo specifically |
| `lib.fred_cache.with_cache_lock` (rate sourcing) | 1 test (`test_fred_lock_serialization`) | All 3 fixtures (via pinned rates) |

**Total estimated test surface for Phase 14:** ~30 unit tests + 3 golden-fixture tests + 1 citation-coverage meta-test + 1 size-budget invariant. Aligns with Phase 4's ~40-test surface and Phase 8's ~25-test surface.

### Wave 0 Gaps

- [ ] `tests/test_property_analysis.py` — covers ANLZ-01, ANLZ-02, ANLZ-03 (does not exist)
- [ ] `tests/test_property_verdict.py` — covers VERD-01 + citation coverage (does not exist)
- [ ] `tests/test_household.py` — covers Household model contract (does not exist)
- [ ] `tests/test_profile.py` — covers Profile model contract (does not exist)
- [ ] `tests/conftest.py` — extend with `property_analysis_fixture` loader (new fixture function)
- [ ] `tests/fixtures/property_analysis/` directory — does not exist
- [ ] 3 fixture files (sfh_conforming_king_county.json, condo_with_hoa_seattle.json, sfh_jumbo_bay_area.json) — do not exist
- [ ] Framework install: none — pytest already configured

## Security Domain

> `security_enforcement: true` in .planning/config.json with `security_asvs_level: 1`. Phase 14 is library composition code with no network I/O, no untrusted input parsing, no auth, no cryptography. ASVS coverage is minimal but verified.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 14 has no users or auth surface. |
| V3 Session Management | no | Phase 14 has no sessions. |
| V4 Access Control | no | Phase 14 reads only library inputs (already validated by Phase 13 PropertyListing pydantic boundary). |
| V5 Input Validation | yes | All inputs (PropertyListing, Household, Profile) are Pydantic v2 strict/frozen/extra=forbid models — boundary validation is built-in. |
| V6 Cryptography | no | No cryptographic operations. (Note: household_snapshot_hash uses SHA256 from `hashlib`; that's a hash function for data deduplication, not a security primitive, and the input is already non-secret.) |

### Known Threat Patterns for `lib/property_analysis.py`

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Decimal precision loss (silent float-to-Decimal coercion) | Tampering | `strict=True` on every Money/Rate field rejects float at validation boundary (CLAUDE.md money discipline + lib/models.py L23-33). |
| Cross-process race on FRED cache | Tampering | `with_cache_lock` (Phase 12 D-LOCK + Python port from `orchestration/lockfile.mjs`) — read-back-verify CAS pattern with 60s stale recovery. |
| Stale regulatory data masquerading as current | Tampering | `lib.rules._loader._check_staleness` raises `StaleReferenceWarning` when `effective:` is > 12 months old. Phase 14 inherits this loud-by-default behavior; warnings surface into `AnalysisReport.warnings`. |
| Verdict reason missing computed_value (lets the user trust a verdict without falsifiable basis) | Repudiation | D-14-VERDICT-04 + Pitfall 7 — `VerdictReason` Pydantic model REQUIRES `predicate_code AND computed_value`; pydantic ValidationError on construction without both. Citation-coverage meta-test enforces that every code appears in fixtures. |
| PII in fixtures (real Zillow listings carry agent contact info, full addresses) | Information Disclosure | Phase 13 D-13 + Phase 11 D-02 fixture-sanitization policy: synthetic addresses preserve zip but strip PII. Phase 14 fixtures inherit; document in `tests/fixtures/property_analysis/README.md`. |

## Sources

### Primary (HIGH confidence)

- **`.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md`** — Locked decisions D-14-MATRIX-01..03, D-14-VERDICT-01..04, D-14-STRESS-01..03, D-14-REFI-01..03, D-14-MODELS-01..04. The authority for every "this is locked" claim in this research.
- **`.planning/REQUIREMENTS.md`** — ANLZ-01..03, VERD-01 wording.
- **`.planning/ROADMAP.md`** — Phase 14 success criteria 1-7, Phase 15 dependency direction.
- **`.planning/PROJECT.md`** — Core value (math correctness first), CLAUDE.md (money discipline + test discipline + reference data discipline).
- **`.planning/research/v1.1-property-analysis.md`** — 9 milestone patterns + 12 pitfalls + 8 open questions; Phase 14 inherits Patterns 3-5 + Pitfalls 4-7.
- **`.planning/phases/13-property-ingestion/13-CONTEXT.md`** — PropertyListing field shape (price + zip + property_type MUST-HAVE; everything else NICE-TO-HAVE); analyzed_listings schema (Phase 13 ships table; Phase 14 just appends analysis_json).
- **`.planning/phases/12-fred-eval/12-CONTEXT.md`** — D-12-LIVE02-01 cache-file SKILL.md injection pattern; FRED reads serialize through `with_cache_lock`.
- **`.planning/phases/05-arm-modeling/05-CONTEXT.md`** — ARM 5/1 = (initial=60, reset=12); D-02 floor_rate REQUIRED; D-06 ARMTerms field schema; constrains D-14-STRESS-03.
- **`lib/affordability.py`** L1-540 — Phase 4 Household / Applicant / EscrowInputs / blocker-code constants pattern; the model for D-14-VERDICT-04 reason format.
- **`lib/amortize.py`** L1-292 — `build_schedule` signature + D-04 rate-per-period + D-09 final-period cleanup + D-12 origination synthesis.
- **`lib/arm.py`** L1-200 — ARMTerms + ARMRequest + IndexPathEntry shapes for ARM-reset stress.
- **`lib/stress.py`** L1-300 — Discriminated union + StressResponse(summary, rows) shape; D-02 field-order convention applied to AnalysisReport.
- **`lib/refinance.py`** L1-200 — D-04 sign convention (outflows negative); D-06 NPV-based breakeven without `npf.irr`.
- **`lib/points.py`** L1-145 — Discriminated union over from_savings/from_loans; D-04 both-outputs convention.
- **`lib/fred_cache.py`** L1-356 — `with_cache_lock` lifecycle; `get_cached_or_fetch` contract; StaleCacheWarning.
- **`lib/models.py`** L1-92 — Money / Rate Annotated aliases; strict=True; ge=0 caveat for Money.
- **`lib/property_listing.py`** L1-105 — PropertyListing field shape (Phase 13 contract).
- **`lib/rules/loan_type.py`** L1-115 — classify(loan_amount, county, program=, unit_count=) signature; MissingCountyDataError.
- **`lib/rules/fha_mip.py`** L1-130 — compute(loan, original_property_value, endorsement_date) → MIPResult.
- **`lib/rules/va_funding_fee.py`** L60-110 — compute(loan_amount, dp_pct, is_first_use, loan_purpose, is_exempt) → Decimal.
- **`lib/rules/irs_pub936.py`** L1-95 — qualified_loan_limit(filing_status, has_grandfathered_debt=, binding_contract_*=) → Decimal; Phase 14 calls with defaults.
- **`data/reference/conforming-limits-2026.yml`** — 2026 baseline $832,750 + ceiling $1,249,125 + WA King County $1,027,000.
- **`data/reference/fha-mip-rates.yml`** — UFMIP 1.75%; annual MIP LTV-band table + life-of-loan termination rule.
- **`data/reference/va-funding-fees.yml`** — Purchase fee band table + cash-out-flat rates + exemption flag.
- **`data/reference/irs-pub936.yml`** — Post-2017 $750k / Pre-2017 $1M caps + MFS halving + binding-contract grace period.
- **`data/reference/fannie-llpa-matrix.yml`** — LLPA bps grid by credit_score × LTV bucket (referenced by Phase 4 affordability; Phase 14 inherits via affordability_evaluate).
- **`config/household.example.yml`** — Existing Household.location requires state_fips + county_fips + county_name (Pitfall 5 confirmation).
- **`config/profile.example.yml`** — Existing Profile shape (display + defaults + modes blocks) → natural home for `va_eligible` field.
- **`tests/conftest.py`** L24-72 — affordability_fixture / amortize_fixture / arm_fixture loader pattern (one-fixture-per-file convention).
- **`tests/fixtures/affordability/forward_conventional_80_ltv.json`** — Fixture-shape exemplar (request + expected + source citation + rounding mode + notes).

### Secondary (MEDIUM confidence)

- **`/Users/cujo253/Documents/mortgage-ops/.planning/config.json`** — Confirmed nyquist_validation=true, security_enforcement=true, granularity=fine.
- **WebSearch 2026-05-17, query "FHA monthly MIP burden $300 threshold heuristic HUD MBA published guidance":** No published HUD or MBA $300 threshold exists. The CONTEXT.md $300/mo number is a policy choice (Assumption A1). Sources reviewed: amerisave.com, multifamily.loans, federalregister.gov, lower.com, mortgage-info.com, answers.hud.gov, bayoumortgage.com, hud.gov/hud-partners, legalclarity.org — none reference a $300 monthly MIP burden threshold heuristic.

### Tertiary (LOW confidence — none used in this research)

None. All claims trace to Primary or Secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primitive verified against actual `lib/` source as of 2026-05-17; no new dependencies.
- Architecture: HIGH — patterns mirror Phase 4/5/8 conventions; AnalysisReport shape recommendation is direct extrapolation from `lib/stress.py:StressResponse`.
- Pitfalls: HIGH (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12), MEDIUM (11) — Pitfall 11 requires planner confirmation that v1.1 scope is purely post-2017 acquisition.
- Open Questions: MEDIUM — 4 questions surface real planner decisions; none are blockers for plan creation.
- Validation Architecture: HIGH — fixture convention + assertion pattern + test count all mirror Phase 4/5/8 exactly.

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (30 days; stable composition over locked v1.0 surface)

## RESEARCH COMPLETE

- **Phase 14 ships ZERO new math primitives.** It composes seven already-shipped + test-pinned modules (`amortize, affordability, arm, points, refinance, stress, fred_cache`) plus three reference predicates (`fha_mip, va_funding_fee, irs_pub936`) into a fan-out pipeline + verdict cascade. Total new code estimate: 600-800 lines across 4 new `lib/` files.
- **Profile/Household split (Claude's Discretion resolved):** ship a NEW `lib/profile.py` Profile model (carries `va_eligible, first_time_buyer, military_status, filing_status, marginal_tax_rate`) separate from a NEW `lib/household.py` Household (carries `monthly_income, monthly_obligations, fico, liquid_reserves, state_fips, county_fips, county_name, preferred_down_payment_pct`). Two reasons: (1) `lib.affordability.Household` is a Phase 4 frozen name; (2) the existing `config/profile.example.yml` already separates these concerns.
- **AnalysisReport schema (Claude's Discretion resolved):** nested blocks (DownPaymentMatrix, StressBlock, RefiBlock, PointsBlock, TaxBlock, Verdict), matching `lib/stress.py:StressResponse` shape. Field-declaration order: matrix → stress → refi → points → tax → verdict (matrix first so the JSON-reader sees numerics before narrative).
- **Five concrete pitfalls planner MUST address in plan tasks:** (1) conventional PMI rate has no public YAML — pick approach 2 (estimated constant + WARNING reason); (2) conforming-limit lookup requires County(state_fips, county_fips, name), NOT zip — derive from Household; (3) signed Decimals (refi_savings, points_savings) cannot use the Money alias (ge=0); use raw Decimal per Phase 6 RefiCashflow precedent; (4) ARM 5/1 stress requires the full ARMRequest with ARMTerms — hardcode conventional ARM defaults as module constant; (5) every VerdictReason MUST cite both predicate_code AND computed_value — ship `VERDICT_*` constants + citation-coverage meta-test mirroring Phase 4 + Phase 8.
- **Validation architecture: 3 golden-value fixtures (sfh_conforming_king_county, condo_with_hoa_seattle, sfh_jumbo_bay_area) as one-file-per-case in `tests/fixtures/property_analysis/`; ~30 unit tests + 3 golden tests + 1 citation-coverage meta-test + 1 100KB-size-budget invariant; exact Decimal equality per CLAUDE.md (never assertAlmostEqual for money). Wave 0 ships test stubs as xfail; later waves flip to green. Full suite gate before `/gsd-verify-work`.
