---
phase: 14
plan: 03
plan_id: 14-03
slug: auxiliary-blocks
type: execute
wave: 2
depends_on:
  - 14-01
  - 14-02
files_modified:
  - lib/property_analysis.py
  - tests/test_property_analysis.py
autonomous: true
requirements:
  - ANLZ-03
nyquist_compliant: true
tags:
  - stress
  - refi
  - points
  - irs-pub936
  - arm

must_haves:
  truths:
    - "_build_stress_block(matrix, listing, household, profile, todays_rates) → StressBlock fans out 3 stresses (rate +2%, income -30%, ARM-reset for Conv30 only) across each eligible-at-preferred-DP program, producing 12-15 StressRow entries."
    - "_build_refi_block(matrix, household, todays_rates) → RefiBlock produces exactly 2 RefiRow per program at preferred DP (target_rate = FRED_current − 1.00 AND FRED_current × 0.85)."
    - "_build_points_block(matrix, household, todays_rates) → PointsBlock produces exactly 2 PointsRow per Conv-family program (Conv30, Conv15, Jumbo30) — FHA + VA carry a WARNING-NO-POINTS-FOR-FHA-VA note per Open Question 1 resolution."
    - "_build_tax_block(matrix, household, profile, todays_rates) → TaxBlock computes first-year interest per program AND over_750k_cap flag via lib.rules.irs_pub936.qualified_loan_limit(filing_status=profile.filing_status) with default grandfathering booleans (Pitfall 11) (B-6 — signature pinned to 4 args)."
    - "ARM 5/1 stress uses the _CONV_5_1_ARM_TERMS constant from Plan 14-02 — full ARMRequest is constructed (Pitfall 8); ArmResetRequest.paths is REQUIRED (min_length=1) and is constructed with peak-cap RatePath rows."
    - "Refi block signed-Decimal fields (monthly_savings, npv_60mo) are populated with potentially-negative values (rate-up scenarios) — strict typing per Pitfall 3."
    - "All upstream API calls match actual signatures (verified against lib/stress.py L160-260, lib/refinance.py L288-525, lib/points.py L65-115): RateShockRequest.loan + .rates (full Rate values, not bps); IncomeShockRequest.base_request + .reductions + .dti_threshold; ArmResetRequest.paths required; RateAndTermRefiRequest(refi_kind='rate_and_term', old_loan_balance, old_annual_rate, new_annual_rate, new_term_months, old_remaining_months, closing_costs, discount_rate_annual); PointsRequestFromLoans(mode='from_loans', points_cost, loan_with_points, loan_without_points, hold_period_months, discount_rate_annual)."
    - "_DTI_CEILING_BY_PROGRAM constant supplies per-program DTI ceiling (Conv=0.50, FHA=0.57, VA=0.41, Jumbo=0.43) — NOT a hardcoded 0.50 for all programs (B-5 fix)."
  artifacts:
    - path: "lib/property_analysis.py"
      provides: "_build_stress_block + _build_refi_block + _build_points_block + _build_tax_block helpers + _DTI_CEILING_BY_PROGRAM constant"
      contains: "def _build_stress_block"
    - path: "tests/test_property_analysis.py"
      provides: "ANLZ-03 unit tests for stress/refi/points/tax blocks"
      contains: "def test_stress_at_preferred_dp_only"
  key_links:
    - from: "lib/property_analysis.py:_build_stress_block"
      to: "lib.stress.evaluate"
      via: "RateShockRequest / IncomeShockRequest / ArmResetRequest dispatch (verified signatures)"
      pattern: "stress_evaluate\\("
    - from: "lib/property_analysis.py:_build_refi_block"
      to: "lib.refinance.evaluate"
      via: "RateAndTermRefiRequest per program × 2 scenarios"
      pattern: "RateAndTermRefiRequest\\("
    - from: "lib/property_analysis.py:_build_points_block"
      to: "lib.points.evaluate"
      via: "PointsRequestFromLoans(mode='from_loans', ...) per program × 2 point drops"
      pattern: "PointsRequestFromLoans\\("
    - from: "lib/property_analysis.py:_build_tax_block"
      to: "lib.rules.irs_pub936.qualified_loan_limit"
      via: "$750k cap awareness"
      pattern: "qualified_loan_limit\\("
    - from: "lib/property_analysis.py:_build_stress_block"
      to: "lib.arm.build_arm_schedule"
      via: "ARM 5/1 peak-cap reset stress (Conv30 only); ArmResetRequest.paths required"
      pattern: "RatePath\\("
---

<objective>
Ship the four auxiliary-block builders that complete the AnalysisReport substrate: stress, refi, points, tax. All run at user's preferred DP only per D-14-STRESS-01.

Closes ANLZ-03 (auto-applied stress tests + points breakeven + refi scan + IRS Pub 936 deductibility rollup).

Purpose: After Plans 14-01 + 14-02 ship the matrix layer, Plan 14-04 (verdict) consumes the StressBlock. Plan 14-05 (top-level analyze) needs all four block builders. Plan 14-06 (golden fixtures) asserts each block's structure end-to-end.

Output: ~400 LOC added to lib/property_analysis.py + ~250 LOC added to tests/test_property_analysis.py.

---

## Iteration-2 Fixes (Check Report)

The v1 of this plan invoked upstream APIs with **fabricated field names** that do not exist in `lib/stress.py`, `lib/refinance.py`, `lib/points.py`. Every `<action>` code block in Tasks 1 + 2 has been rewritten against the VERIFIED upstream signatures (re-read 2026-05-17):

- **B-1 (Stress/Refi/Points API signatures):**
  - `RateShockRequest(mode="rate-shock", loan: Loan, rates: list[Rate], baseline_label, scenario_label)` — NOT `base_loan` / `rate_shocks_bps`. `rates` is a list of FULL Rate values (e.g., `[Decimal("0.085000")]` for +2% on a 6.5% baseline), NOT bps offsets.
  - `IncomeShockRequest(mode="income-shock", base_request: AffordabilityRequest, reductions: list[Rate], dti_threshold: Rate)` — NOT `base_loan` / `income_multipliers` / `max_dti`. `reductions` is the SHOCK MAGNITUDE: `[Decimal("0.30")]` for -30% income shock (NOT `[0.70]` multiplier). `base_request` is a fully-constructed Phase-4 `ForwardModeRequest`; Plan 14-03 reconstructs it inline via a private helper (`_construct_affordability_request_for_cell`) that mirrors Plan 14-02 step 11-12 (including the B-2 VA-synthesis branch).
  - `ArmResetRequest(mode="arm-reset", base_arm_request: ARMRequest, paths: list[RatePath])` — `paths` is REQUIRED with `min_length=1`. Phase 14 supplies a single `RatePath(name="parallel-shift", params={"shift_bps": <lifetime_cap_bps>})` per D-14-STRESS-03 (peak-cap reset stress).
  - `RefiRequest` is a discriminated union: `Annotated[RateAndTermRefiRequest | CashOutRefiRequest, Field(discriminator="refi_kind")]`. Use `RateAndTermRefiRequest(refi_kind="rate_and_term", old_loan_balance, old_annual_rate, new_annual_rate, new_term_months, old_remaining_months, closing_costs, discount_rate_annual)`. NOTE: `refi_kind="rate_and_term"` (underscore); the field is `old_remaining_months` (verified at lib/refinance.py L304), `old_annual_rate` (verified at L301), `new_annual_rate` (verified at L307). `discount_rate_annual` is REQUIRED (D-05).
  - `RefiResponse` readout: `resp.monthly_savings: Decimal`, `resp.npv: Decimal`, `resp.breakeven: RefiBreakeven`. For breakeven months, use `resp.breakeven.npv_months: int | None` (verified at lib/refinance.py L279 — field is `npv_months`, NOT `npv_breakeven_months`).
  - `PointsRequestFromLoans(mode="from_loans", points_cost: Money, loan_with_points: Loan, loan_without_points: Loan, hold_period_months: int, discount_rate_annual: Rate)` — underscore in `from_loans`, NOT hyphen. NO `no_points_loan` / `discounted_loan` / `points_purchased` fields. Phase 14 pins `hold_period_months=60` (5-year hold; standard Phase 6 convention) and `discount_rate_annual=current_rate` (program's current rate per Phase 6 D-09).

- **B-5 (DTI ceiling per program):** Hardcoded `Decimal("0.50")` replaced with a module-level `_DTI_CEILING_BY_PROGRAM` constant carrying per-program ceilings with regulatory citations (Conv=0.50, FHA=0.57, VA=0.41, Jumbo=0.43).

- **B-6 (tax_block signature consistency):** `must_haves.truths` line 4 updated to `_build_tax_block(matrix, household, profile, todays_rates)` (4 args, matching the `<action>` body in Task 2 + the 14-05 callsite).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md
@.planning/phases/14-property-analysis-pipeline/14-RESEARCH.md
@.planning/phases/14-property-analysis-pipeline/14-PATTERNS.md
@.planning/phases/14-property-analysis-pipeline/14-01-SUMMARY.md
@.planning/phases/14-property-analysis-pipeline/14-02-SUMMARY.md
@CLAUDE.md
@lib/property_analysis.py
@lib/stress.py
@lib/refinance.py
@lib/points.py
@lib/arm.py
@lib/amortize.py
@lib/affordability.py
@lib/rules/irs_pub936.py
@lib/money.py
@lib/household.py
@lib/profile.py
@tests/test_property_analysis.py
@tests/test_stress.py
@tests/test_refinance.py
@tests/test_points.py

<interfaces>
<!-- VERIFIED 2026-05-17 against lib/stress.py L160-260. -->

```python
# lib/stress.py L177-189
class RateShockRequest(_CommonStressFields):
    mode: Literal["rate-shock"] = "rate-shock"
    loan: Loan
    rates: list[Rate] = Field(min_length=1)        # FULL Rate values, NOT bps offsets
    baseline_label: str | None = None              # defaults to str(rates[0])
    # inherits scenario_label: str | None = None

# lib/stress.py L192-205
class IncomeShockRequest(_CommonStressFields):
    mode: Literal["income-shock"] = "income-shock"
    base_request: AffordabilityRequest             # Phase-4 ForwardModeRequest or ReverseModeRequest
    reductions: list[Rate] = Field(min_length=1)   # shock MAGNITUDE (0.30 = -30%), NOT multiplier
    dti_threshold: Rate                            # REQUIRED (D-04)

# lib/stress.py L208-223
class ArmResetRequest(_CommonStressFields):
    mode: Literal["arm-reset"] = "arm-reset"
    base_arm_request: ARMRequest                   # full ARMRequest (loan + arm_terms + assumed_index_rate)
    paths: list[RatePath] = Field(min_length=1)    # REQUIRED — peak-cap path

# lib/stress.py L94-109
class RatePath(BaseModel):
    name: Literal["parallel-shift", "gradual-rise", "fall-then-rise"]
    params: dict[str, int]
    # parallel-shift: {"shift_bps": int}
```

<!-- VERIFIED 2026-05-17 against lib/refinance.py L288-525. -->

```python
# lib/refinance.py L288-381 (_CommonRefiFields)
class _CommonRefiFields(BaseModel):
    old_loan_balance: Money
    old_annual_rate: Rate
    old_remaining_months: int = Field(ge=1, le=600)   # NOTE: old_remaining_months, NOT remaining_months
    new_annual_rate: Rate
    new_term_months: int = Field(ge=1, le=600)
    closing_costs: Money
    discount_rate_annual: Rate                        # REQUIRED (D-05)
    analysis_horizon_months: int | None = None        # None → use new_term_months
    after_tax_mode: bool = False
    # ... (after-tax fields + new_loan_monthly_pi_override; not used in Phase 14)

# lib/refinance.py L389-401
class RateAndTermRefiRequest(_CommonRefiFields):
    refi_kind: Literal["rate_and_term"] = "rate_and_term"   # underscore form

RefiRequest = Annotated[
    RateAndTermRefiRequest | CashOutRefiRequest,
    Field(discriminator="refi_kind"),
]

# lib/refinance.py L257-280
class RefiBreakeven(BaseModel):
    simple_months: int | None
    simple_status: Literal["ok", "no_savings", "zero_costs", "never_breaks_even"]
    npv_months: int | None                          # USE THIS for Phase 14 breakeven_months
    npv_status: Literal["ok", "never_breaks_even"]

# lib/refinance.py L452-533
class RefiResponse(BaseModel):
    refi_kind: Literal["rate_and_term", "cash_out"]
    npv: Decimal                                    # USE THIS for Phase 14 npv_60mo
    breakeven: RefiBreakeven                        # access .npv_months
    old_monthly_pi: Money
    new_monthly_pi: Money
    monthly_savings: Decimal                        # SIGNED — USE THIS for Phase 14 monthly_savings
    # ... cash_out fields are None for rate_and_term

def evaluate(request: RefiRequest) -> RefiResponse: ...
```

<!-- VERIFIED 2026-05-17 against lib/points.py L65-115. -->

```python
# lib/points.py L85-103
class PointsRequestFromLoans(BaseModel):
    mode: Literal["from_loans"] = "from_loans"        # underscore, NOT hyphen
    points_cost: Money = Field(strict=True, gt=Decimal("0"))
    loan_with_points: Loan
    loan_without_points: Loan
    hold_period_months: int = Field(ge=1, le=600)
    discount_rate_annual: Rate                        # REQUIRED (D-02)

# lib/points.py L116-144
class PointsResponse(BaseModel):
    simple_breakeven_months: int | None
    npv_breakeven_months: int | None
    diverge: bool
    decision: Literal["buy_points", "skip_points"]
    discount_rate_used: Rate
    hold_period_months: int
    monthly_savings: Decimal
    cumulative_npv_at_hold: Decimal
    warnings: list[str]

def evaluate(request: PointsRequest) -> PointsResponse: ...
```

<!-- VERIFIED 2026-05-17 against lib/arm.py L87-105. -->

```python
class ARMRequest(BaseModel):
    loan: Loan                                       # NOTE: loan, not base_loan
    arm_terms: ARMTerms
    assumed_index_rate: Rate                         # REQUIRED (D-01)
    index_path: list[IndexPathEntry] = Field(default_factory=list)

class IndexPathEntry(BaseModel):
    period: int = Field(ge=1)                        # aligned to a reset trigger
    value: Rate
```

<!-- From lib/rules/irs_pub936.py L66-90 — Pub 936 cap. -->

```python
def qualified_loan_limit(
    filing_status: Literal["single", "mfj", "mfs", "hoh"],
    has_grandfathered_debt: bool = False,
    binding_contract_signed_before_2017_12_15: bool = False,
    binding_contract_closed_before_2018_04_01: bool = False,
) -> Decimal: ...
# Returns Decimal("750000") for single/MFJ/HoH; Decimal("375000") for MFS.
# Phase 14 calls with defaults (all False) per Pitfall 11.
```

<!-- From lib/amortize.py — first-year interest helper. -->

```python
def build_schedule(loan: Loan, frequency: str = "monthly") -> Schedule: ...
# Schedule.payments: list[Payment]; sum first 12 payments' interest = first-year interest.
```

<!-- From lib/property_analysis.py (Plan 14-02 output) — types we extend. -->

```python
class StressRow / StressBlock / RefiRow / RefiBlock / PointsRow / PointsBlock / TaxBlock
class ProgramResult / DownPaymentMatrix
_CONV_5_1_ARM_TERMS: Final[ARMTerms]  # for Conv30 ARM stress only (D-14-STRESS-03)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _build_stress_block + _build_refi_block helpers + _DTI_CEILING_BY_PROGRAM to lib/property_analysis.py</name>
  <files>lib/property_analysis.py</files>
  <read_first>
    - lib/property_analysis.py (Plan 14-02 output: models + matrix builder)
    - lib/stress.py L160-260 (RateShockRequest, IncomeShockRequest, ArmResetRequest, RatePath shapes — VERIFY field names verbatim)
    - lib/refinance.py L288-525 (RateAndTermRefiRequest, RefiResponse, RefiBreakeven shapes)
    - lib/arm.py L87-145 (ARMRequest + ARMTerms + IndexPathEntry; D-01 reset-trigger alignment)
    - lib/affordability.py L441-540 (ForwardModeRequest shape — needed as `IncomeShockRequest.base_request`)
    - lib/amortize.py L255-292 (build_schedule for first-year interest in TaxBlock helper next task)
    - .planning/phases/14-property-analysis-pipeline/14-CONTEXT.md (D-14-STRESS-01..03, D-14-REFI-01..03 — locks)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L209-237 (Step 5 architecture: stress/refi/points/tax blocks at preferred DP only)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L617-694 (Pitfall 8: ARM 5/1 stress requires full ARMRequest with ARMTerms)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L267-307 (StressResponse shape; signed-Decimal-fields-not-Money for refi)
    - .planning/phases/14-property-analysis-pipeline/14-PLAN-CHECK.md (B-1 fix paths — verbatim upstream signatures table)
  </read_first>
  <behavior>
    - Behavior 1: `_build_stress_block(matrix, listing, household, profile, todays_rates)` returns a StressBlock with `preferred_down_payment_pct == household.preferred_down_payment_pct` and `rows` containing one entry per (eligible program, stress_kind) tuple where stress_kind ∈ {"rate_shock", "income_shock", "arm_reset"}; "arm_reset" rows appear ONLY for the Conv30 program (D-14-STRESS-03). Programs ineligible at preferred DP are SKIPPED (D-14-STRESS-01).
    - Behavior 2: A rate_shock stress row carries `stressed_piti` (Money, non-null) and `stressed_dti_back` (Rate); `breaches_dti_ceiling` reflects whether `stressed_dti_back > _DTI_CEILING_BY_PROGRAM[cell.program]` (B-5 — per-program ceiling, NOT hardcoded 0.50).
    - Behavior 3: An income_shock stress row has `stressed_piti is None` (income doesn't change PITI per RESEARCH L322 + lib/stress.py L131); `stressed_dti_back` is the engine's recomputed DTI under the -30% shock; `breaches_dti_ceiling=True` when the shocked DTI exceeds the per-program ceiling.
    - Behavior 4: An arm_reset stress row's `stressed_piti` is the PITI computed at the ARM's peak-cap reset rate (note_rate + lifetime_cap_bps/10000, capped by floor); only emitted for program=="Conv30".
    - Behavior 5: `_build_refi_block(matrix, household, todays_rates_dict)` returns RefiBlock with exactly `len(eligible_at_preferred_dp_programs) × 2` rows. Each row's `target_rate` is one of: `quantize_rate(FRED_current_for_program - Decimal("0.01"))` OR `quantize_rate(FRED_current_for_program * Decimal("0.85"))`. `scenario_label` is `"minus_100bps"` or `"fred_times_0_85"` respectively.
    - Behavior 6: Refi rows have `monthly_savings: Decimal` (NOT Money — signed) read from `resp.monthly_savings`; `npv_60mo` read from `resp.npv`; `breakeven_months` read from `resp.breakeven.npv_months`. Negative values appear when target_rate > current rate.
    - Behavior 7: `_build_stress_block` constructs `ArmResetRequest(mode="arm-reset", base_arm_request=ARMRequest(loan=conv30_loan, arm_terms=_CONV_5_1_ARM_TERMS, assumed_index_rate=todays_rates["Conv30-ARM-5-1"]), paths=[RatePath(name="parallel-shift", params={"shift_bps": _CONV_5_1_ARM_TERMS.lifetime_cap_bps})])` — `paths` is REQUIRED with `min_length=1` (B-1 fix).
    - Behavior 8: `_build_stress_block` and `_build_refi_block` raise no exceptions when the matrix has zero eligible cells at preferred DP — they return empty `rows: []`.
    - Behavior 9: Total stress row count for the SFH-conforming reference fixture (Conv30 + Conv15 + FHA30 all eligible at 20% DP) is 3×2 + 1 (Conv30-only ARM-reset) = 7 rows total.
    - Behavior 10 (B-5): `_DTI_CEILING_BY_PROGRAM` is a module-level constant: Conv30=0.50, Conv15=0.50, FHA30=0.57, VA30=0.41, Jumbo30=0.43.
  </behavior>
  <action>
    Extend `lib/property_analysis.py` by adding two private helpers + one module constant BEFORE the `analyze` stub. Reuse the imports from Plan 14-02 (extend the import block as needed).

    **Add module-level constant (B-5 fix):**

    Place near the existing `_CONV_PMI_ANNUAL_RATE` constant block at the module top:
    ```python
    # B-5: Per-program DTI ceilings. Hardcoded 0.50 for all programs is silently
    # wrong for 3 of 5 programs (false-positive WATCH on FHA cells, false-negative
    # GO on VA cells). Each citation links the regulatory source.
    _DTI_CEILING_BY_PROGRAM: Final[dict[str, Decimal]] = {
        # Conventional (Fannie / Freddie ATR-QM safe harbor; QM Patch sunset 2021)
        "Conv30":  Decimal("0.50"),
        "Conv15":  Decimal("0.50"),
        # FHA: HUD Handbook 4000.1 II.A.5.d max back-end ratio
        "FHA30":   Decimal("0.57"),
        # VA: VA Lender Handbook 26-7 Ch. 4 §7 — 41% baseline (residual income
        # gating provides the upside cushion separately)
        "VA30":    Decimal("0.41"),
        # Jumbo: ATR/QM safe harbor for non-QM jumbo (lender-conservative)
        "Jumbo30": Decimal("0.43"),
    }
    ```

    **Add to import block at top of file:**
    ```python
    from lib.stress import (
        evaluate as stress_evaluate,
        RateShockRequest,
        IncomeShockRequest,
        ArmResetRequest,
        RatePath,
    )
    from lib.refinance import evaluate as refi_evaluate, RateAndTermRefiRequest
    from lib.arm import ARMRequest, IndexPathEntry  # noqa: F401  # IndexPathEntry reserved for path overrides
    ```

    **Helper 0: `_construct_affordability_request_for_cell(cell, listing, household, profile, annual_rate) -> ForwardModeRequest`**

    Private helper that reconstructs the Phase-4 ForwardModeRequest used by `_build_program_result` step 11-12 (Plan 14-02). Body mirrors the affordability-request construction in Plan 14-02, including the B-2 VA-synthesis branch (when `cell.program == "VA30"`, supply `va=VAInputs(region="northeast", family_size=2, actual_residual_income=quantize_cents(household.monthly_income * Decimal("0.5")))`). Document loudly that any change to Plan 14-02's request construction MUST be mirrored here. (Acceptable v1 duplication; surfacing the request as `ProgramResult._affordability_request` is a v1.2 option.)

    Signature:
    ```python
    def _construct_affordability_request_for_cell(
        cell: ProgramResult,
        listing: PropertyListing,
        household: Household,
        profile: Profile,
        annual_rate: Decimal,
    ) -> ForwardModeRequest:
        """Reconstruct the Phase-4 ForwardModeRequest used by lib.affordability.evaluate
        for this cell. Mirrors the construction in Plan 14-02 _build_program_result
        steps 11-12. Includes the B-2 VA-synthesis branch when cell.program == "VA30"."""
        ...
    ```

    **Helper 1: `_eligible_cells_at_preferred_dp(matrix: DownPaymentMatrix, preferred_dp: Decimal) -> list[ProgramResult]`** — returns the subset of matrix.cells where `down_payment_pct == preferred_dp` AND `eligible is True`.

    **Helper 2: `_build_stress_block(matrix, listing, household, profile, todays_rates) -> StressBlock`** — per D-14-STRESS-01..03 (REWRITTEN against verified upstream signatures):

    Body:
    ```python
    def _build_stress_block(
        matrix: DownPaymentMatrix,
        listing: PropertyListing,
        household: Household,
        profile: Profile,
        todays_rates: dict[str, Decimal],
    ) -> StressBlock:
        preferred = household.preferred_down_payment_pct
        eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
        rows: list[StressRow] = []

        for cell in eligible_cells:
            current_rate = todays_rates[cell.program]
            term_months = 180 if cell.program == "Conv15" else 360
            loan_type = (
                "fha" if cell.program == "FHA30"
                else "va" if cell.program == "VA30"
                else "fixed"
            )
            cell_loan = Loan(
                principal=cell.loan_amount,
                annual_rate=current_rate,
                term_months=term_months,
                loan_type=loan_type,
            )
            ceiling = _DTI_CEILING_BY_PROGRAM[cell.program]

            # ============================================================
            # 1. Rate shock +2% — RateShockRequest (verified L177-189)
            # ============================================================
            shocked_rate = quantize_rate(current_rate + Decimal("0.02"))
            rate_resp = stress_evaluate(
                RateShockRequest(
                    mode="rate-shock",
                    loan=cell_loan,
                    rates=[shocked_rate],                 # FULL Rate value, NOT bps
                    baseline_label=str(current_rate),
                    scenario_label=f"{cell.program}+200bps",
                )
            )
            rows.append(_stress_row_from_rate_shock(cell, rate_resp, household, ceiling))

            # ============================================================
            # 2. Income shock -30% — IncomeShockRequest (verified L192-205)
            # ============================================================
            base_request = _construct_affordability_request_for_cell(
                cell, listing, household, profile, current_rate,
            )
            income_resp = stress_evaluate(
                IncomeShockRequest(
                    mode="income-shock",
                    base_request=base_request,
                    reductions=[Decimal("0.30")],         # shock MAGNITUDE, NOT multiplier
                    dti_threshold=ceiling,                # B-5: per-program ceiling
                    scenario_label=f"{cell.program}-30%-income",
                )
            )
            rows.append(_stress_row_from_income_shock(cell, income_resp, household, ceiling))

            # ============================================================
            # 3. ARM reset — ArmResetRequest (verified L208-223; Conv30 only)
            # ============================================================
            if cell.program == "Conv30":
                arm_index_rate = todays_rates.get(
                    "Conv30-ARM-5-1",
                    quantize_rate(current_rate - Decimal("0.0025")),
                )
                arm_req = ARMRequest(
                    loan=cell_loan,                       # field is `loan`, NOT `base_loan`
                    arm_terms=_CONV_5_1_ARM_TERMS,
                    assumed_index_rate=arm_index_rate,
                )
                # paths is REQUIRED (min_length=1). Use a parallel-shift at the
                # lifetime cap to capture the peak-cap reset stress (D-14-STRESS-03).
                peak_cap_path = RatePath(
                    name="parallel-shift",
                    params={"shift_bps": _CONV_5_1_ARM_TERMS.lifetime_cap_bps},
                )
                arm_resp = stress_evaluate(
                    ArmResetRequest(
                        mode="arm-reset",
                        base_arm_request=arm_req,
                        paths=[peak_cap_path],            # REQUIRED
                        scenario_label=f"{cell.program}-arm-peak-cap",
                    )
                )
                rows.append(_stress_row_from_arm_reset(cell, arm_resp, household, ceiling))

        return StressBlock(preferred_down_payment_pct=preferred, rows=rows)
    ```

    **Define 3 thin row-builder helpers** (`_stress_row_from_rate_shock`, `_stress_row_from_income_shock`, `_stress_row_from_arm_reset`) that convert lib.stress's StressRow shape (lib/stress.py L112-141) into Phase 14's StressRow shape. Each helper:
    - Sets `program = cell.program`
    - Sets `stress_kind` to the appropriate Literal (`"rate_shock"`, `"income_shock"`, `"arm_reset"`)
    - Sets `baseline_piti = cell.piti`
    - Sets `stressed_piti` (rate_shock + arm_reset only; None for income_shock per RESEARCH L322 + lib/stress.py L131 — income-shock rows do NOT carry `monthly_pi`/`stressed_piti` since income changes don't change PITI)
    - Sets `stressed_dti_back` — for rate_shock + arm_reset: recompute `(stressed_piti + household.monthly_obligations) / household.monthly_income`; for income_shock: read from upstream `lib.stress.StressRow.dti_back` (L135)
    - Sets `breaches_dti_ceiling = stressed_dti_back > ceiling` (B-5: per-program ceiling passed in)
    - Sets `blocker_reasons` to a list containing the appropriate VERDICT_WATCH_STRESS_* style code WHEN breaches=True (e.g., `["STRESS-INCOME-SHOCK-30PCT"]`); empty list when not.

    For rate-shock + arm-reset: extract `stressed_monthly_pi` from upstream `lib.stress.StressRow.monthly_pi` (rate-shock) or from `lib.stress.StressRow.max_payment` (arm-reset — the peak monthly_pi after the reset). Recompute Phase 14's `stressed_piti = stressed_monthly_pi + cell.monthly_tax + cell.monthly_insurance + cell.monthly_hoa + cell.monthly_mi` and `stressed_dti_back = (stressed_piti + household.monthly_obligations) / household.monthly_income`.

    **Helper 3: `_build_refi_block(matrix, household, todays_rates_dict) -> RefiBlock`** — per D-14-REFI-01..03 (REWRITTEN against verified upstream signatures):

    Body:
    ```python
    def _build_refi_block(
        matrix: DownPaymentMatrix,
        household: Household,
        todays_rates: dict[str, Decimal],
    ) -> RefiBlock:
        preferred = household.preferred_down_payment_pct
        eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
        rows: list[RefiRow] = []

        for cell in eligible_cells:
            current_rate = todays_rates[cell.program]
            new_term = 180 if cell.program == "Conv15" else 360
            closing = quantize_cents(cell.loan_amount * Decimal("0.02"))

            # Scenario A: target = current - 0.01 (D-14-REFI-03 FRED-1.00)
            target_a = quantize_rate(current_rate - Decimal("0.01"))
            refi_a = refi_evaluate(
                RateAndTermRefiRequest(
                    refi_kind="rate_and_term",            # underscore, not hyphen
                    old_loan_balance=cell.loan_amount,
                    old_annual_rate=current_rate,
                    old_remaining_months=new_term,        # baseline matches new term
                    new_annual_rate=target_a,
                    new_term_months=new_term,
                    closing_costs=closing,
                    discount_rate_annual=current_rate,    # REQUIRED (D-05); Phase 6 D-09 convention
                    analysis_horizon_months=60,           # 5-year NPV horizon
                )
            )
            rows.append(RefiRow(
                program=cell.program,
                target_rate=target_a,
                scenario_label="minus_100bps",
                monthly_savings=refi_a.monthly_savings,    # signed Decimal
                breakeven_months=refi_a.breakeven.npv_months,  # .breakeven.npv_months
                npv_60mo=refi_a.npv,                       # signed Decimal
            ))

            # Scenario B: target = current * 0.85 (D-14-REFI-03 FRED×0.85)
            target_b = quantize_rate(current_rate * Decimal("0.85"))
            refi_b = refi_evaluate(
                RateAndTermRefiRequest(
                    refi_kind="rate_and_term",
                    old_loan_balance=cell.loan_amount,
                    old_annual_rate=current_rate,
                    old_remaining_months=new_term,
                    new_annual_rate=target_b,
                    new_term_months=new_term,
                    closing_costs=closing,
                    discount_rate_annual=current_rate,
                    analysis_horizon_months=60,
                )
            )
            rows.append(RefiRow(
                program=cell.program,
                target_rate=target_b,
                scenario_label="fred_times_0_85",
                monthly_savings=refi_b.monthly_savings,
                breakeven_months=refi_b.breakeven.npv_months,
                npv_60mo=refi_b.npv,
            ))

        return RefiBlock(rows=rows)
    ```

    Notes:
    - `analysis_horizon_months=60` (5-year hold) matches the Phase 14 `RefiRow.npv_60mo` field semantics.
    - `discount_rate_annual=current_rate` follows Phase 6 D-09 convention (program's own current rate; documented as policy).
    - `old_remaining_months=new_term` is the rate-and-term refi convention (refinancing a freshly originated loan; no residual months from a prior origination).
    - `closing_costs` estimated at 2% of loan_amount (industry rule-of-thumb for rate-and-term refi).
    - monthly_savings is signed; rate-up scenarios produce negative values — this is correct (Pitfall 3).

    DO NOT implement _build_points_block or _build_tax_block here — those land in Task 2.
    DO NOT modify the analyze() stub — it still raises NotImplementedError until Plan 14-05.
    DO NOT re-implement amortization or NPV math — delegate entirely to lib.stress + lib.refinance.
    DO use the exact field names verified in <interfaces> above; if the executor finds a divergence, the executor STOPS and reports back rather than guessing.
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py::test_stress_at_preferred_dp_only tests/test_property_analysis.py::test_arm_reset_conv30_only tests/test_property_analysis.py::test_stress_income_shock_dti_recompute tests/test_property_analysis.py::test_refi_two_scenarios_per_program tests/test_property_analysis.py::test_refi_signed_decimal_fields tests/test_property_analysis.py::test_dti_ceiling_per_program -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def _build_stress_block' lib/property_analysis.py` returns 1.
    - `grep -c 'def _build_refi_block' lib/property_analysis.py` returns 1.
    - `grep -c 'def _eligible_cells_at_preferred_dp' lib/property_analysis.py` returns 1.
    - `grep -c 'def _construct_affordability_request_for_cell' lib/property_analysis.py` returns 1.
    - `grep -c '_DTI_CEILING_BY_PROGRAM' lib/property_analysis.py` returns at least 4 (1 declaration + 3 uses: rate-shock ceiling, income-shock dti_threshold, arm-reset ceiling) (B-5 fix).
    - `grep -c '"Conv30":  *Decimal("0.50")' lib/property_analysis.py` returns at least 1.
    - `grep -c '"FHA30":  *Decimal("0.57")' lib/property_analysis.py` returns at least 1.
    - `grep -c '"VA30":  *Decimal("0.41")' lib/property_analysis.py` returns at least 1.
    - `grep -c '"Jumbo30":  *Decimal("0.43")' lib/property_analysis.py` returns at least 1.
    - `grep -c 'RateShockRequest(' lib/property_analysis.py` returns at least 1.
    - `grep -c 'loan=cell_loan' lib/property_analysis.py` returns at least 1 (B-1 — correct field name `loan`, NOT `base_loan`).
    - `grep -c 'rates=\[shocked_rate\]' lib/property_analysis.py` returns at least 1 (B-1 — full Rate values list, NOT bps).
    - `grep -c 'base_request=base_request' lib/property_analysis.py` returns at least 1 (B-1 — IncomeShockRequest correct field).
    - `grep -c 'reductions=\[Decimal("0.30")\]' lib/property_analysis.py` returns at least 1 (B-1 — shock magnitude, not multiplier).
    - `grep -c 'dti_threshold=ceiling' lib/property_analysis.py` returns at least 1 (B-5 — per-program ceiling threaded through).
    - `grep -c 'ArmResetRequest(mode="arm-reset"' lib/property_analysis.py` returns at least 1.
    - `grep -c 'base_arm_request=arm_req' lib/property_analysis.py` returns at least 1 (Pitfall 8 — full ARMRequest).
    - `grep -c 'paths=\[peak_cap_path\]' lib/property_analysis.py` returns at least 1 (B-1 — paths REQUIRED).
    - `grep -c 'RatePath(' lib/property_analysis.py` returns at least 1.
    - `grep -c 'arm_terms=_CONV_5_1_ARM_TERMS' lib/property_analysis.py` returns at least 1.
    - `grep -c '_CONV_5_1_ARM_TERMS' lib/property_analysis.py` returns at least 2 (declaration in Plan 14-02 + use in stress).
    - `grep -c 'if cell.program == "Conv30"' lib/property_analysis.py` returns at least 1 (D-14-STRESS-03 ARM-Conv30-only gate).
    - `grep -c 'RateAndTermRefiRequest(' lib/property_analysis.py` returns at least 2 (one per scenario).
    - `grep -c 'refi_kind="rate_and_term"' lib/property_analysis.py` returns at least 2 (B-1 — underscore form).
    - `grep -c 'old_loan_balance=cell.loan_amount' lib/property_analysis.py` returns at least 2 (B-1 — correct field name).
    - `grep -c 'old_annual_rate=current_rate' lib/property_analysis.py` returns at least 2 (B-1).
    - `grep -c 'new_annual_rate=target_' lib/property_analysis.py` returns at least 2 (B-1 — correct field).
    - `grep -c 'old_remaining_months' lib/property_analysis.py` returns at least 2 (B-1 — verified field name).
    - `grep -c 'discount_rate_annual=current_rate' lib/property_analysis.py` returns at least 2 (B-1 — REQUIRED field).
    - `grep -c 'refi_a.breakeven.npv_months\|refi_b.breakeven.npv_months' lib/property_analysis.py` returns at least 2 (B-1 — correct readout path).
    - `grep -c 'scenario_label="minus_100bps"' lib/property_analysis.py` returns 1.
    - `grep -c 'scenario_label="fred_times_0_85"' lib/property_analysis.py` returns 1.
    - `grep -c 'current_rate - Decimal("0.01")' lib/property_analysis.py` returns 1 (D-14-REFI-03 FRED−1.00).
    - `grep -c 'current_rate \* Decimal("0.85")' lib/property_analysis.py` returns 1 (D-14-REFI-03 FRED×0.85).
    - Tests pass: `pytest tests/test_property_analysis.py -x -k "stress_at_preferred_dp_only or arm_reset_conv30_only or stress_income_shock_dti_recompute or refi_two_scenarios_per_program or refi_signed_decimal_fields or dti_ceiling_per_program"` exits 0.
  </acceptance_criteria>
  <done>
    Stress + refi blocks composable from the matrix using ACTUAL upstream API signatures (verified against lib/stress.py, lib/refinance.py). ARM-reset stress fires Conv30-only per D-14-STRESS-03 with REQUIRED paths field. Refi scans 2 scenarios per eligible-at-preferred-DP program per D-14-REFI-03 with correct `refi_kind="rate_and_term"` underscore form. Per-program DTI ceiling (B-5) replaces hardcoded 0.50. All linkage verified by 6 named tests.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add _build_points_block + _build_tax_block helpers to lib/property_analysis.py</name>
  <files>lib/property_analysis.py</files>
  <read_first>
    - lib/property_analysis.py (Task 1 of this plan output)
    - lib/points.py L65-145 (PointsRequestFromLoans signature — VERIFY underscore in "from_loans" + field names: points_cost, loan_with_points, loan_without_points, hold_period_months, discount_rate_annual)
    - lib/rules/irs_pub936.py L1-95 (qualified_loan_limit signature; defaults to False booleans)
    - lib/amortize.py L255-292 (build_schedule + Schedule.payments for first-year interest calculation)
    - .planning/phases/14-property-analysis-pipeline/14-CONTEXT.md (Locked: Pub 936 ships flag + first-year interest only — Phase 15 formatter decides partial-deduction dollar display)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L1044-1064 (Open Question 1: PointsBlock applies to Conv-family only — Conv30/Conv15/Jumbo30; FHA + VA carry WARNING-NO-POINTS-FOR-FHA-VA note)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L679-693 (Pitfall 11: Phase 14 defaults all IRS booleans to False — post-2017 acquisition by definition)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L1037-1040 (Assumption A3: 25bps rate drop per discount point)
    - .planning/phases/14-property-analysis-pipeline/14-PLAN-CHECK.md (B-1 PointsRequestFromLoans fix path + B-6 tax_block signature consistency)
  </read_first>
  <behavior>
    - Behavior 1: `_build_points_block(matrix, household, todays_rates)` returns a PointsBlock with rows where `points_purchased ∈ {1, 2}`. For Conv30 / Conv15 / Jumbo30 programs eligible at preferred DP, exactly 2 rows per program (one for 1pt, one for 2pt) are present with `simple_breakeven_months` and `npv_breakeven_months` populated.
    - Behavior 2: For FHA30 / VA30 programs eligible at preferred DP, exactly 2 rows per program are present BUT both breakeven_months fields are None AND `note == "WARNING-NO-POINTS-FOR-FHA-VA"` (Open Question 1 resolution).
    - Behavior 3: Each row's `rate_drop` equals Decimal("0.0025") × points_purchased (Assumption A3); 1pt → rate_drop=Decimal("0.002500"); 2pt → rate_drop=Decimal("0.005000").
    - Behavior 4 (B-6 — 4-arg signature): `_build_tax_block(matrix, household, profile, todays_rates)` returns a TaxBlock where:
        - `qualified_loan_limit == Decimal("750000")` when profile.filing_status ∈ {"single", "mfj", "hoh"}.
        - `qualified_loan_limit == Decimal("375000")` when profile.filing_status == "mfs".
        - `filing_status` echoes profile.filing_status.
        - `first_year_interest_per_program[program]` is a Money equal to the sum of the first 12 interest components of the program's preferred-DP cell's amortization schedule.
        - `over_750k_cap_per_program[program] is True` IFF the program's preferred-DP cell's loan_amount > qualified_loan_limit.
    - Behavior 5: TaxBlock builder works for ANY profile.filing_status without invoking grandfathering booleans (Pitfall 11 — Phase 14 uses defaults).
    - Behavior 6: For an empty `eligible_cells_at_preferred_dp` list, TaxBlock has empty dicts; PointsBlock has empty rows list — neither crashes.
    - Behavior 7 (B-1 PointsRequestFromLoans): The call uses `mode="from_loans"` (underscore, NOT hyphen), passes `loan_with_points` + `loan_without_points` (NOT `discounted_loan`/`no_points_loan`), `hold_period_months=60` (5-year hold policy), `discount_rate_annual=current_rate` (program's current rate per Phase 6 D-09 convention).
  </behavior>
  <action>
    Extend `lib/property_analysis.py` with two more helpers.

    Add to imports:
    ```python
    from lib.points import evaluate as points_evaluate, PointsRequestFromLoans
    from lib.rules.irs_pub936 import qualified_loan_limit as pub936_qualified_loan_limit
    ```

    **Helper 1 (B-1 REWRITTEN): `_build_points_block(matrix, household, todays_rates) -> PointsBlock`**

    Body:
    ```python
    _POINTS_CONV_FAMILY: Final[frozenset[str]] = frozenset({"Conv30", "Conv15", "Jumbo30"})
    _POINTS_HOLD_PERIOD_MONTHS: Final[int] = 60  # 5-year hold policy (Phase 6 D-09 convention)


    def _build_points_block(
        matrix: DownPaymentMatrix,
        household: Household,
        todays_rates: dict[str, Decimal],
    ) -> PointsBlock:
        preferred = household.preferred_down_payment_pct
        eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
        rows: list[PointsRow] = []

        for cell in eligible_cells:
            current_rate = todays_rates[cell.program]
            term_months = 180 if cell.program == "Conv15" else 360

            for points in (1, 2):
                rate_drop_raw = Decimal("0.002500") * points  # Assumption A3
                rate_drop = quantize_rate(rate_drop_raw)

                if cell.program in _POINTS_CONV_FAMILY:
                    discounted_rate = quantize_rate(current_rate - rate_drop)
                    loan_without_points = Loan(
                        principal=cell.loan_amount,
                        annual_rate=current_rate,
                        term_months=term_months,
                        loan_type="fixed",
                    )
                    loan_with_points = Loan(
                        principal=cell.loan_amount,
                        annual_rate=discounted_rate,
                        term_months=term_months,
                        loan_type="fixed",
                    )
                    points_cost = quantize_cents(
                        cell.loan_amount * Decimal("0.01") * Decimal(str(points))
                    )

                    resp = points_evaluate(
                        PointsRequestFromLoans(
                            mode="from_loans",                        # underscore form (B-1)
                            points_cost=points_cost,
                            loan_with_points=loan_with_points,        # B-1 — correct field name
                            loan_without_points=loan_without_points,  # B-1 — correct field name
                            hold_period_months=_POINTS_HOLD_PERIOD_MONTHS,
                            discount_rate_annual=current_rate,        # Phase 6 D-09 convention
                        )
                    )
                    rows.append(PointsRow(
                        program=cell.program,
                        points_purchased=points,
                        rate_drop=rate_drop,
                        simple_breakeven_months=resp.simple_breakeven_months,
                        npv_breakeven_months=resp.npv_breakeven_months,
                        note=None,
                    ))
                else:
                    # FHA + VA: points not modeled (Open Question 1 resolution)
                    rows.append(PointsRow(
                        program=cell.program,
                        points_purchased=points,
                        rate_drop=rate_drop,
                        simple_breakeven_months=None,
                        npv_breakeven_months=None,
                        note="WARNING-NO-POINTS-FOR-FHA-VA",
                    ))

        return PointsBlock(rows=rows)
    ```

    **Helper 2 (B-6 — 4-arg signature): `_build_tax_block(matrix, household, profile, todays_rates) -> TaxBlock`**

    Body:
    ```python
    def _build_tax_block(
        matrix: DownPaymentMatrix,
        household: Household,
        profile: Profile,
        todays_rates: dict[str, Decimal],
    ) -> TaxBlock:
        preferred = household.preferred_down_payment_pct
        eligible_cells = _eligible_cells_at_preferred_dp(matrix, preferred)
        cap = pub936_qualified_loan_limit(filing_status=profile.filing_status)
        # Defaults: has_grandfathered_debt=False, binding_contract_*=False (Pitfall 11)

        first_year: dict[str, Decimal] = {}
        over_cap: dict[str, bool] = {}
        for cell in eligible_cells:
            term_months = 180 if cell.program == "Conv15" else 360
            loan_type = "fixed"
            if cell.program == "FHA30":
                loan_type = "fha"
            elif cell.program == "VA30":
                loan_type = "va"
            loan = Loan(
                principal=cell.loan_amount,
                annual_rate=todays_rates[cell.program],
                term_months=term_months,
                loan_type=loan_type,
            )
            schedule = build_schedule(loan, frequency="monthly")
            # Sum interest component of first 12 payments
            first_year[cell.program] = quantize_cents(
                sum((p.interest for p in schedule.payments[:12]), start=Decimal("0"))
            )
            over_cap[cell.program] = cell.loan_amount > cap

        return TaxBlock(
            first_year_interest_per_program=first_year,
            over_750k_cap_per_program=over_cap,
            qualified_loan_limit=cap,
            filing_status=profile.filing_status,
        )
    ```

    Notes:
    - Uses `start=Decimal("0")` on sum() per PATTERNS.md L237 (avoid int 0 contamination).
    - `schedule.payments[:12]` slices the first 12 monthly payments; `.interest` is the Decimal interest component (verify against lib.amortize.Payment shape during implementation).
    - `qualified_loan_limit` is called with defaults — DO NOT pass `has_grandfathered_debt=True` or any binding-contract flag (Pitfall 11).
    - The 4-arg signature `(matrix, household, profile, todays_rates)` is the authoritative shape (matches Plan 14-05 callsite + must_haves.truths line 4). Plan 14-04's frontmatter `key_links` may show a stale 2-arg shape — that's informational only and has no execution impact (per 14-PLAN-CHECK B-6).

    DO NOT modify _build_stress_block / _build_refi_block from Task 1.
    DO NOT modify the analyze() stub — still raises NotImplementedError until Plan 14-05.
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py::test_points_breakeven_per_program tests/test_property_analysis.py::test_points_fha_va_warning_note tests/test_property_analysis.py::test_tax_block_pub936 tests/test_property_analysis.py::test_tax_block_mfs_filing_status_halves_cap tests/test_property_analysis.py::test_tax_block_over_cap_flag -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def _build_points_block' lib/property_analysis.py` returns 1.
    - `grep -c 'def _build_tax_block' lib/property_analysis.py` returns 1.
    - `grep -c 'pub936_qualified_loan_limit(filing_status=profile.filing_status)' lib/property_analysis.py` returns 1.
    - `grep -c 'WARNING-NO-POINTS-FOR-FHA-VA' lib/property_analysis.py` returns at least 1.
    - `grep -c '_POINTS_CONV_FAMILY' lib/property_analysis.py` returns at least 2 (declaration + use).
    - `grep -c '_POINTS_HOLD_PERIOD_MONTHS' lib/property_analysis.py` returns at least 2 (declaration + use).
    - `grep -c 'mode="from_loans"' lib/property_analysis.py` returns at least 1 (B-1 — underscore form).
    - `grep -c 'loan_with_points=' lib/property_analysis.py` returns at least 1 (B-1 — correct field).
    - `grep -c 'loan_without_points=' lib/property_analysis.py` returns at least 1 (B-1 — correct field).
    - `grep -c 'hold_period_months=_POINTS_HOLD_PERIOD_MONTHS' lib/property_analysis.py` returns at least 1 (B-1).
    - `grep -c 'Decimal("0.002500") \* points' lib/property_analysis.py` returns 1 (Assumption A3).
    - `grep -cn 'has_grandfathered_debt' lib/property_analysis.py | head -1` returns 0 lines outside comments (Pitfall 11 — defaults only; verify via `grep 'has_grandfathered_debt' lib/property_analysis.py | grep -v '^[[:space:]]*#'`).
    - `grep -c 'start=Decimal("0")' lib/property_analysis.py` returns at least 1 (PATTERNS.md L237).
    - `grep -c 'def _build_tax_block(' lib/property_analysis.py` returns 1 AND signature matches 4 args (matrix, household, profile, todays_rates): verified via `awk '/def _build_tax_block\\(/,/\\)/' lib/property_analysis.py` showing all 4 parameters.
    - Behavior verification: `python -c "from lib.rules.irs_pub936 import qualified_loan_limit; from decimal import Decimal; assert qualified_loan_limit(filing_status='mfj') == Decimal('750000'); assert qualified_loan_limit(filing_status='mfs') == Decimal('375000')"` exits 0.
    - Tests pass: `pytest tests/test_property_analysis.py -x -k "points_breakeven_per_program or points_fha_va_warning_note or tax_block_pub936 or tax_block_mfs_filing_status_halves_cap or tax_block_over_cap_flag"` exits 0.
  </acceptance_criteria>
  <done>
    Points + tax blocks composable from the matrix. PointsRequestFromLoans uses correct `mode="from_loans"` underscore + `loan_with_points`/`loan_without_points` + `hold_period_months=60` + `discount_rate_annual=current_rate` (B-1 fix). PointsBlock handles FHA/VA "not modeled" path per Open Question 1. TaxBlock surfaces over-$750k flag per program; MFS halves cap; grandfathering booleans default-False per Pitfall 11. tax_block signature pinned to 4 args (B-6). Verified by 5 named tests.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Flip Wave-2 stress/refi/points/tax test stubs in tests/test_property_analysis.py to real assertions</name>
  <files>tests/test_property_analysis.py</files>
  <read_first>
    - tests/test_property_analysis.py (Plan 14-02 output — Wave-2 stubs)
    - lib/property_analysis.py (this plan's Tasks 1 + 2 output)
    - lib/household.py, lib/profile.py
    - lib/property_listing.py L40-105 (PropertyListing fields)
    - tests/test_stress.py L100-300 (stress test patterns)
    - tests/test_refinance.py (refi test patterns)
    - tests/test_points.py (points test patterns)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L1103-1107 (test-to-requirement mapping for ANLZ-03)
  </read_first>
  <behavior>
    Flip the following test stubs from `pytest.skip(...)` to real assertions:
    - `test_stress_at_preferred_dp_only` — Build a matrix from a non-jumbo SFH listing; build stress block; assert every row's program is in matrix.programs_present; assert every row corresponds to a cell where down_payment_pct == household.preferred_down_payment_pct AND eligible==True; assert no stress rows reference ineligible cells.
    - `test_arm_reset_conv30_only` — Build stress block; assert `sum(1 for r in stress.rows if r.stress_kind == "arm_reset") == 1` when only Conv30 is eligible at preferred DP; assert all arm_reset rows have `program == "Conv30"`.
    - `test_stress_income_shock_dti_recompute` — Income-shock row's `stressed_dti_back > cell.dti_back` (income drops → DTI rises); `stressed_piti is None`.
    - `test_stress_rate_shock_piti_rises` — Rate-shock row's `stressed_piti > baseline_piti` (rate +200bps → PITI rises).
    - `test_refi_two_scenarios_per_program` — Refi block has exactly 2 × len(eligible_at_preferred_dp_programs) rows; each program has one "minus_100bps" row + one "fred_times_0_85" row.
    - `test_refi_signed_decimal_fields` — When target_rate > current_rate (rate-up — unusual but possible if base rate is very low), `monthly_savings < 0` and `npv_60mo < 0`; assert these fields accept negative values (not Money-aliased).
    - `test_points_breakeven_per_program` — Points block has exactly 2 rows per Conv-family eligible-at-preferred-DP program; rate_drop is Decimal("0.002500") for 1pt and Decimal("0.005000") for 2pt.
    - `test_points_fha_va_warning_note` — For an FHA30-eligible or VA30-eligible scenario, points rows for those programs have `note == "WARNING-NO-POINTS-FOR-FHA-VA"` AND breakeven_months fields are None.
    - `test_tax_block_pub936` — TaxBlock.qualified_loan_limit == Decimal("750000") for mfj/single/hoh; TaxBlock.first_year_interest_per_program[program] > 0 for every eligible-at-preferred-DP program; sum of interest matches Phase 3 oracle to exact Decimal equality (compute expected via build_schedule output, no hand-calc magic numbers in the test).
    - `test_tax_block_mfs_filing_status_halves_cap` — Profile(filing_status="mfs") → TaxBlock.qualified_loan_limit == Decimal("375000").
    - `test_tax_block_over_cap_flag` — When a cell's loan_amount > $750k (e.g., jumbo case), over_750k_cap_per_program[program] is True; otherwise False.
    - `test_dti_ceiling_per_program` (B-5 NEW) — Build stress block for a Profile(va_eligible=True) scenario with a household income tuned so the income-shock magnitude breaches VA's 0.41 ceiling but not FHA's 0.57. Assert that the VA30 stress row has `breaches_dti_ceiling=True` while the FHA30 stress row has `breaches_dti_ceiling=False`. This directly verifies B-5 (per-program ceiling, not hardcoded 0.50).
  </behavior>
  <action>
    Edit `tests/test_property_analysis.py` to replace the `pytest.skip(...)` bodies in the Wave-2 stubs (introduced by Plan 14-02 Task 3) with real assertion bodies.

    Each test should:
    1. Use the `_make_clean_household() / _make_clean_profile() / _make_clean_listing()` builders established in Plan 14-02 Task 3.
    2. Inject `todays_rates` directly as a dict (e.g., `{"Conv30": Decimal("0.065000"), "Conv15": Decimal("0.058000"), "FHA30": Decimal("0.065000"), "VA30": Decimal("0.065000"), "Jumbo30": Decimal("0.065000"), "Conv30-ARM-5-1": Decimal("0.062500")}`) to avoid the FRED dependency.
    3. Call `_build_matrix(listing, household, profile, todays_rates)` to get the matrix, then call `_build_stress_block` / `_build_refi_block` / `_build_points_block` / `_build_tax_block` directly.
    4. Use exact Decimal equality. For `test_tax_block_pub936`, the expected first-year interest value is computed in the test by directly calling `build_schedule(...)` and summing the first-12 payment interest components — NOT a hardcoded magic number; the test asserts that `_build_tax_block`'s output equals `quantize_cents(sum(p.interest for p in expected_schedule.payments[:12]))`.

    Add the new `test_dti_ceiling_per_program` test:
    ```python
    def test_dti_ceiling_per_program() -> None:
        """B-5: Per-program DTI ceilings differ — VA=0.41 stresses differently than
        FHA=0.57 under the same income-shock magnitude. Hardcoded 0.50 would
        false-positive WATCH on FHA and false-negative GO on VA."""
        listing = _make_clean_listing(price="500000.00")
        # Tune household so the -30% income shock pushes DTI between VA's 0.41 and
        # FHA's 0.57 ceilings (loud assertion that the engine reads per-program).
        household = _make_clean_household(monthly_income="9500.00", monthly_obligations="500.00")
        profile = _make_clean_profile(va_eligible=True)
        todays_rates = {
            "Conv30": Decimal("0.065000"),
            "Conv15": Decimal("0.058000"),
            "FHA30":  Decimal("0.065000"),
            "VA30":   Decimal("0.065000"),
            "Conv30-ARM-5-1": Decimal("0.062500"),
        }
        matrix, _ = _build_matrix(listing, household, profile, todays_rates)
        stress = _build_stress_block(matrix, listing, household, profile, todays_rates)

        # Locate income-shock rows for FHA30 and VA30 (both should be eligible at
        # 20% DP given the tuned income).
        fha_shock = next(r for r in stress.rows
                         if r.program == "FHA30" and r.stress_kind == "income_shock")
        va_shock  = next(r for r in stress.rows
                         if r.program == "VA30"  and r.stress_kind == "income_shock")

        # The shocked DTI should be the SAME magnitude (same income drop, same
        # cell numerics modulo program-specific MI), but the breach flag differs.
        assert va_shock.breaches_dti_ceiling is True,  "VA30 should breach 0.41 ceiling"
        assert fha_shock.breaches_dti_ceiling is False, "FHA30 should NOT breach 0.57 ceiling"
    ```

    DO NOT introduce new helper functions in tests/test_property_analysis.py beyond the builders already in place from Plan 14-02 Task 3.
    DO NOT load fixture JSON files yet — those are created in Plan 14-06; these tests must run on in-test-constructed objects.
    DO NOT use `pytest.approx`.

    For `test_arm_reset_conv30_only`, you may need to engineer a scenario where only Conv30 is eligible at preferred DP (e.g., low income that makes FHA fail DTI but Conv passes with a wider DTI ceiling). Alternative: build the matrix and then explicitly filter to a Conv30-only-eligible subset for the assertion.

    For `test_dti_ceiling_per_program`: if the tuned income values do not produce the desired ceiling-straddle in the executor's environment, the executor MAY adjust monthly_income / monthly_obligations to achieve the straddle while preserving the test's INTENT (B-5 verification — different programs apply different ceilings).
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py -x -k "stress or refi or points or tax or dti_ceiling"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'pytest.skip' tests/test_property_analysis.py` returns at most 4 (only golden-fixture + report_size_budget stubs remain skipped; 4 stubs total: test_sfh_conforming_king_county_golden, test_condo_with_hoa_seattle_golden, test_sfh_jumbo_bay_area_golden, test_report_size_budget — all deferred to Plan 14-06).
    - Each Wave-2 test exists as a real function body (not pytest.skip): `grep -A2 'def test_stress_at_preferred_dp_only' tests/test_property_analysis.py | grep -v 'pytest.skip'` shows actual assertions.
    - The new B-5 test exists: `grep -c 'def test_dti_ceiling_per_program' tests/test_property_analysis.py` returns 1.
    - All 12 Wave-2 named tests from Behavior list pass: `pytest tests/test_property_analysis.py::test_stress_at_preferred_dp_only tests/test_property_analysis.py::test_arm_reset_conv30_only tests/test_property_analysis.py::test_stress_income_shock_dti_recompute tests/test_property_analysis.py::test_stress_rate_shock_piti_rises tests/test_property_analysis.py::test_refi_two_scenarios_per_program tests/test_property_analysis.py::test_refi_signed_decimal_fields tests/test_property_analysis.py::test_points_breakeven_per_program tests/test_property_analysis.py::test_points_fha_va_warning_note tests/test_property_analysis.py::test_tax_block_pub936 tests/test_property_analysis.py::test_tax_block_mfs_filing_status_halves_cap tests/test_property_analysis.py::test_tax_block_over_cap_flag tests/test_property_analysis.py::test_dti_ceiling_per_program -x` exits 0.
    - `pytest tests/test_property_analysis.py -x -k "not golden and not report_size_budget and not analyze_end_to_end"` exits 0 (full Wave-1 + Wave-2 test surface green; only golden + size budget + end-to-end remain stubbed).
    - `pytest -x` (full suite) exits 0 — no regression.
  </acceptance_criteria>
  <done>
    All ANLZ-03 unit-test surface flipped from stubs to passing assertions. Stress/refi/points/tax helpers fully verified at the in-test level. Per-program DTI ceiling (B-5) verified by dedicated test. Only golden-fixture + JSON-size-budget + end-to-end analyze() tests remain stubbed (deferred to Plans 14-05 + 14-06).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase 14 lib → lib.stress / lib.refinance / lib.points / lib.rules.irs_pub936 | Pure-Python in-process delegation. No new boundaries introduced by this plan. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-FLOAT | Tampering | StressRow, RefiRow, PointsRow, TaxBlock Money/Rate fields | mitigate | All models inherited from Plan 14-02 have strict=True; tests in this plan verify type discipline via existing Plan 14-02 test_float_rejection (no regression). Refi signed-Decimal fields use raw Decimal per Pitfall 3 (proved by test_refi_signed_decimal_fields). |
| T-14-FRED-RACE | Tampering | n/a in this plan | accept | This plan does not invoke FRED reads directly; todays_rates is passed in. FRED lock mitigation lives in Plan 14-02 Task 2 + Plan 14-05 analyze() composition. |
| T-14-STALE-REF | Tampering | lib.rules.irs_pub936 reads data/reference/irs-pub936.yml | mitigate | Reads via existing predicate; StaleReferenceWarning auto-surfaces. |
| T-14-REASON | Repudiation | Stress row blocker_reasons (carry stress-level codes like STRESS-INCOME-SHOCK) | mitigate | Stress-level codes prefixed STRESS-* by convention; Plan 14-04 cross-checks via citation coverage. |
| T-14-PII | Information Disclosure | tests/test_property_analysis.py Wave-2 tests | mitigate | Tests use synthetic data only. |
</threat_model>

<verification>
- All Wave-2 unit tests in tests/test_property_analysis.py pass.
- `pytest -x` (full suite) exits 0 — no regression.
- `python -c "from lib.property_analysis import _build_stress_block, _build_refi_block, _build_points_block, _build_tax_block, _DTI_CEILING_BY_PROGRAM"` succeeds.
- `python -c "from lib.property_analysis import analyze; analyze()"` STILL raises NotImplementedError mentioning Plan 14-05 (analyze() body deferred).
- All `<action>` code blocks verified against actual upstream lib signatures (lib/stress.py L160-260, lib/refinance.py L288-525, lib/points.py L65-115, lib/arm.py L87-105) — NO fabricated field names.
</verification>

<success_criteria>
1. _build_stress_block fans out 3 stresses × eligible-at-preferred-DP programs; ARM-reset Conv30 only.
2. _build_refi_block fans out 2 scenarios × eligible-at-preferred-DP programs (FRED−1.00 + FRED×0.85).
3. _build_points_block fans out 2 point levels × eligible-at-preferred-DP programs; FHA + VA carry WARNING-NO-POINTS-FOR-FHA-VA note.
4. _build_tax_block computes first-year interest via lib.amortize.build_schedule + sum first-12 payments interest; over_750k_cap flag per program; qualified_loan_limit via lib.rules.irs_pub936.qualified_loan_limit with default booleans. Signature pinned to 4 args (B-6).
5. **B-1 RESOLVED:** All stress/refi/points API calls match actual upstream signatures (RateShockRequest.loan + .rates; IncomeShockRequest.base_request + .reductions + .dti_threshold; ArmResetRequest.paths required; RateAndTermRefiRequest underscore + old_remaining_months + .breakeven.npv_months readout; PointsRequestFromLoans `mode="from_loans"` + loan_with_points + loan_without_points + hold_period_months=60 + discount_rate_annual=current_rate).
6. **B-5 RESOLVED:** `_DTI_CEILING_BY_PROGRAM` constant supplies per-program ceiling; `dti_threshold=ceiling` threaded into IncomeShockRequest; `breaches_dti_ceiling` evaluated against per-program ceiling in all stress kinds.
7. **B-6 RESOLVED:** `_build_tax_block` signature is `(matrix, household, profile, todays_rates)` matching 14-05 callsite + must_haves.truths line 4.
8. Pitfall 8 (ARM 5/1 stress requires full ARMRequest with ARMTerms): mitigated — uses _CONV_5_1_ARM_TERMS constant + ArmResetRequest.paths supplied.
9. Pitfall 11 (IRS Pub 936 grandfathering defaults False): mitigated — no booleans passed.
10. Open Question 1 (PointsBlock for which programs): resolved — Conv-family only; FHA/VA get warning note.
11. ANLZ-03 closed.
12. All 12 Wave-2 unit tests pass (11 base + 1 new B-5); only 4 stubs remain (golden fixtures + size budget + end-to-end).
</success_criteria>

<output>
After completion, create `.planning/phases/14-property-analysis-pipeline/14-03-SUMMARY.md` documenting:
- 4 new helper signatures (_build_stress_block, _build_refi_block, _build_points_block, _build_tax_block) + the _eligible_cells_at_preferred_dp utility + _construct_affordability_request_for_cell helper.
- Iteration-2 fix summary: B-1 (verified upstream API signatures used), B-5 (per-program DTI ceiling), B-6 (tax_block 4-arg signature).
- _DTI_CEILING_BY_PROGRAM constant values (Conv=0.50, FHA=0.57, VA=0.41, Jumbo=0.43) with regulatory citations.
- Stress row count expected for the canonical SFH-conforming case (3 programs × 2 stresses + 1 Conv30-only ARM-reset = 7 rows).
- Refi row count expected (eligible-at-preferred-DP programs × 2 scenarios).
- Points row count expected (eligible-at-preferred-DP programs × 2 point levels; FHA/VA rows carry note).
- TaxBlock structure (first_year_interest dict + over_cap dict + qualified_loan_limit + filing_status).
- Pitfalls mitigated: 8 (ARM-full-request), 11 (Pub 936 defaults).
- Open Question 1 resolution: PointsBlock for Conv-family only.
- Requirements closed: ANLZ-03.
- Interfaces consumed by Plans 14-04 + 14-05: _build_stress_block, _build_refi_block, _build_points_block, _build_tax_block (all imported by analyze() in Plan 14-05; StressBlock consumed by synthesize() in Plan 14-04).
</output>
