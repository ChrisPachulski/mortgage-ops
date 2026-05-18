# Phase 14 Plan Check (PRE-EXECUTION VERIFICATION)

**Checked:** 2026-05-17
**Plans verified:** 14-01, 14-02, 14-03, 14-04, 14-05, 14-06 (6 plans, 3 waves)
**CONTEXT.md:** Read; all D-14-* decisions cross-referenced.
**RESEARCH.md:** Read end-to-end; Pitfalls 1-12, Code Examples 1-6, Validation Architecture all consulted.
**PATTERNS.md:** Spot-checked for analog mapping discipline.
**Existing library code:** Read `lib/property_listing.py`, `lib/affordability.py`, `lib/stress.py`, `lib/refinance.py`, `lib/points.py`, `lib/arm.py`, `lib/rules/types.py`, `lib/rules/loan_type.py`, `lib/models.py` for API-surface verification.

---

## Adversarial Stance

Starting hypothesis: these plans will not deliver the phase goal. Verification proceeds goal-backward; an issue is a **BLOCKER** if it prevents the goal, **WARNING** if it degrades quality but execution can still proceed.

---

## Dimension Scoring

### 1. Goal Achievement — **1 / 2 (partial)**

Each of the 7 ROADMAP success criteria traces to plan tasks:

| SC | Coverage Plan(s) | Status |
|----|------------------|--------|
| 1. `analyze(...)` runs 4 program-eligibility checks + jumbo branch | 14-02 `_determine_programs` + 14-05 `analyze()` | Covered |
| 2. 6-cell DP sweep per program with PMI/MIP/funding-fee | 14-02 `_build_matrix` + `_build_program_result` | Covered |
| 3. Auto-applied stress tests (rate +2%, income −30%, ARM reset) | 14-03 `_build_stress_block` | Covered **but API misuse (see BLOCKER B-1)** |
| 4. Points breakeven 1pt/2pt + refi scan FRED−1% / FRED×0.85 | 14-03 `_build_points_block` + `_build_refi_block` | Covered **but API misuse (B-1)** |
| 5. IRS Pub 936 first-year interest + $750k cap flag | 14-03 `_build_tax_block` | Covered |
| 6. GO/WATCH/NO_GO verdict with predicate-cited reasons + cascade tests | 14-04 `synthesize()` + `tests/test_property_verdict.py` | Covered |
| 7. 3 hand-calculated golden fixtures pin every matrix cell | 14-06 fixtures + golden tests | Covered |

Each criterion has at least one covering task. Plans 14-04 and 14-05 are sound. Plans 14-01, 14-02 are sound except for SC-2's PropertyListing fixture construction (see WARNING W-1). However Plan 14-03 prescribes **construction code against an invented stress/refi/points API** that does not match the actual lib signatures. Without revision, execution will halt at the first call to `stress_evaluate(...)` because Pydantic strict + extra="forbid" rejects the fabricated field names. SC-3, SC-4, partial SC-2 will not be delivered.

### 2. Requirement Coverage — **2 / 2 (pass)**

| Requirement | Plan(s) | Closing task | Acceptance criteria |
|-------------|---------|--------------|---------------------|
| ANLZ-01 | 14-02 (unit), 14-05 (integration), 14-06 (fixture) | matrix fan-out + jumbo trigger | concrete |
| ANLZ-02 | 14-02 (unit), 14-05 (integration), 14-06 (fixture) | DP sweep + per-cell numerics | concrete |
| ANLZ-03 | 14-03 (unit), 14-05 (integration), 14-06 (fixture) | stress/refi/points/tax | concrete |
| VERD-01 | 14-04 (unit), 14-05 (integration), 14-06 (fixture-coverage meta) | synthesize() + cascade tests | concrete |

Every requirement listed in `requirements:` frontmatter of at least one plan; every requirement has at least one task with `<acceptance_criteria>`.

### 3. CONTEXT.md Locked-Decision Compliance — **1 / 2 (partial — see BLOCKERS)**

| Decision | Honored | Notes |
|----------|---------|-------|
| D-14-MATRIX-01 (explicit ineligible rows with blocker_reasons) | yes | 14-02 ProgramResult shape |
| D-14-MATRIX-02 (numerics populated on ineligible rows) | yes | 14-02 test `test_ineligible_rows_populate_numerics` |
| D-14-MATRIX-03 (jumbo as 5th row when triggered) | yes | 14-02 `_determine_programs` + 14-05 ARM rate dict |
| D-14-VERDICT-01 ($300/mo MIP-burden WATCH) | yes | 14-04 `_MIP_BURDEN_THRESHOLD = Decimal("300.00")` |
| D-14-VERDICT-02 (income-shock WATCH) | yes | 14-04 cascade level 3 |
| D-14-VERDICT-03 (GO wins over MIP-burden when non-FHA eligible) | yes | 14-04 cascade level 4 logic + test `test_go_wins_over_mip_burden_when_non_fha_eligible` |
| D-14-VERDICT-04 (predicate code + computed value on every reason) | yes | 14-04 VerdictReason field requirement; citation-coverage meta-test |
| D-14-STRESS-01 (stress at preferred DP only) | yes (intent) | 14-03 `_eligible_cells_at_preferred_dp` filter |
| D-14-STRESS-02 (`preferred_down_payment_pct` on Household, default 0.20) | yes | 14-01 Task 1 |
| D-14-STRESS-03 (ARM reset Conv30 only) | yes | 14-03 `if cell.program == "Conv30":` gate |
| D-14-REFI-01 (baseline = matrix cell rate) | yes | 14-03 helper docs |
| D-14-REFI-02 (FRED sourcing per program) | yes | 14-05 `todays_rates` dict |
| D-14-REFI-03 (FRED−1.00 AND FRED×0.85) | yes | 14-03 `scenario_label` literal pair |
| D-14-MODELS-01 (Household in lib/household.py) | yes | 14-01 |
| D-14-MODELS-02 (Profile/Household split — Claude's discretion → split) | yes | 14-01 |
| D-14-MODELS-03 (lib/property_verdict.py) | yes | 14-04 |
| D-14-MODELS-04 (lib/property_analysis.py + analyze()) | yes | 14-02 + 14-05 |

Locked decisions are referenced and intended. The compliance failure surfaces in Dimension 4 / Dimension 9 — D-14-STRESS-01, D-14-STRESS-03, D-14-REFI-01..03 are *prescribed in the plan* but the `<action>` code that prescribes them invokes incorrect upstream APIs, so the implementation cannot actually run and therefore cannot actually honor the decisions.

### 4. Anti-Shallow Execution — **1 / 2 (partial — fabricated API references)**

Every task has `<read_first>`, `<behavior>`, `<action>`, `<verify>`, `<acceptance_criteria>`, `<done>`. Acceptance criteria are mechanically checkable (grep counts, exit-0 invariants, Pydantic round-trips, exact-Decimal assertions). No subjective language.

Failure mode: Plan 14-03's `<action>` blocks describe `stress_evaluate(RateShockRequest(...))`, `refi_evaluate(RefiRequest(mode="rate-term", ...))`, `points_evaluate(PointsRequestFromLoans(no_points_loan=...))` using field names that DO NOT EXIST in the upstream APIs (see BLOCKER B-1). This is shallow-execution-by-fabrication: a verifier checking the grep counts in the acceptance criteria would mark them green even though the resulting code raises at the first `model_validate(...)` call.

### 5. Dependency Correctness — **2 / 2 (pass)**

- Wave 1 (`depends_on: []`): 14-01, 14-02 (independent — Household/Profile models vs. matrix/output models).
- Wave 2 (`depends_on: [14-01, 14-02]`): 14-03 (auxiliary blocks), 14-04 (verdict synthesis).
- Wave 3 (`depends_on: [14-01..14-04]`): 14-05 (analyze() composition), 14-06 (fixtures + flips).

No cycles; no forward references; wave numbers consistent with `depends_on`. Plan 14-05 correctly depends on 14-04 (synthesize is imported). Plan 14-06 correctly depends on 14-05 (analyze is the end-to-end driver).

### 6. Pitfall Mitigation — **2 / 2 (pass)**

All 5 RESEARCH pitfalls called out in the check prompt are addressed with concrete `<acceptance_criteria>` greps:

| Pitfall | Plan | Acceptance Criterion |
|---------|------|----------------------|
| 1 — Conv PMI rate constant | 14-02 | `grep -c '_CONV_PMI_ANNUAL_RATE' ≥ 2`; eligible_reasons includes "PMI-RATE-ESTIMATED-0.0075"; surface as warning in analyze() (14-05) |
| 2 — DP fan-out uses Decimal-from-strings | 14-02 | DOWN_PAYMENT_PCTS exact-equality assertion; `test_dp_sweep_uses_decimal_strings` |
| 3 — Signed Decimals (refi_savings, npv_60mo) not Money | 14-02 | grep for `Decimal = Field(strict=True, max_digits=14, decimal_places=2)` on RefiRow.monthly_savings and npv_60mo |
| 4 — Conforming-limit from County(state_fips, county_fips, name), not zip | 14-02 | `grep -c 'County(state_fips=household.state_fips' ≥ 1`; Pitfall 5 in RESEARCH |
| 5 — ARM 5/1 stress requires full ARMRequest | 14-03 | `grep -c 'base_arm_request=ARMRequest(' ≥ 1`; `_CONV_5_1_ARM_TERMS` constant |
| 6 — MI included in PITI (quantize once at end) | 14-02 | exact `piti_pre = monthly_pi + monthly_tax + ...` grep; `piti = quantize_cents(piti_pre)` |
| 7 — VERDICT_* prefix discipline | 14-04 | 5 `VERDICT_*: Final[str]` constants; citation-coverage meta-test |
| 8 — ARMTerms full shape | 14-02 | `_CONV_5_1_ARM_TERMS` constant with all 8 ARMTerms fields |
| 9 — FRED with_cache_lock | 14-02 + 14-05 | `grep -c 'with_cache_lock(CACHE_DIR' ≥ 1`; `test_fred_lock_serialization` |
| 10 — JSON < 100KB | 14-05 | `test_report_size_budget`; no Schedule.payments on ProgramResult |
| 11 — IRS Pub 936 defaults False | 14-03 | grep for `has_grandfathered_debt` returns 0 in non-comment lines |
| 12 — Citation-coverage meta-test | 14-04 (in-test) + 14-06 (fixture-based) | both versions specified |

Mitigations are explicit and verifiable. This is the best-executed dimension across the phase.

### 7. Security Threat Model — **2 / 2 (pass)**

Every plan ships a `<threat_model>` block citing T-14-FLOAT, T-14-FRED-RACE, T-14-STALE-REF, T-14-REASON, T-14-PII. Each threat carries a Disposition (mitigate / accept) and a Mitigation Plan that points at a specific test or invariant. Architectural Responsibility Map from RESEARCH §"Architectural Responsibility Map" honored (all logic in Python lib; no spillover into skill / CLI / data tiers).

### 8. Validation / Nyquist Coverage — **2 / 2 (pass)**

- VALIDATION.md exists with 24 test-map rows mapped to ANLZ-01..03, VERD-01, model contract, and composition invariants.
- Test counts roughly match RESEARCH §"Validation Architecture": ~12 Wave-1 + ~11 Wave-2 (in `test_property_analysis.py`) + 10 in `test_property_verdict.py` + 10+ each in `test_household.py`/`test_profile.py` + 3 golden fixtures + meta-tests. Estimate: 50+ tests collected at end-of-phase (14-06 acceptance criterion explicitly asserts `≥ 50`).
- Sampling continuity: every implementation task has `<automated>pytest ...</automated>` in `<verify>`. No 3-consecutive-tasks-without-tests gap.
- Wave 0 stubs are committed in 14-02 Task 3 (`pytest.skip("Plan 14-XX")` placeholders for stress/refi/points/tax/golden/size-budget) — preserves shape-stability through waves.

---

## Findings

### BLOCKER B-1 — Plan 14-03 prescribes calls against a non-existent stress/refi/points API surface

**Severity:** BLOCKER. ANLZ-03 (success criteria 3, 4) cannot be delivered as planned. Implementation will fail at the first Pydantic model validation in each helper.

**Evidence (verified by direct read of upstream lib modules):**

| Plan 14-03 `<action>` reference | Actual upstream signature (verified) | File:Line |
|----|----|----|
| `RateShockRequest(mode="rate-shock", base_loan=cell_loan, rate_shocks_bps=[200], ...)` | `RateShockRequest(mode="rate-shock", loan=Loan, rates: list[Rate], baseline_label=None, scenario_label=None)` — no `base_loan`, no `rate_shocks_bps`; expects a list of full Rate values, NOT bps offsets | lib/stress.py L178-189 |
| `IncomeShockRequest(mode="income-shock", base_loan=cell_loan, income_multipliers=[Decimal("0.70")], ..., max_dti=Decimal("0.50"))` | `IncomeShockRequest(mode="income-shock", base_request: AffordabilityRequest, reductions: list[Rate], dti_threshold: Rate)` — no `base_loan`, no `income_multipliers`, no `max_dti`; reductions are `[0.30]` (the shock magnitude), NOT multipliers `[0.70]` | lib/stress.py L192-205 |
| `ArmResetRequest(mode="arm-reset", base_arm_request=arm_req, ...)` | `ArmResetRequest(mode="arm-reset", base_arm_request: ARMRequest, paths: list[RatePath])` — `paths` is REQUIRED with `min_length=1`; plan omits it entirely | lib/stress.py L208-223 |
| `RefiRequest(mode="rate-term", current_loan=cell_loan, new_rate=target_a, new_term_months=..., closing_costs=..., discount_horizon_months=60)` | RefiRequest is a discriminated union with `refi_kind="rate_and_term"` (note: underscore, not hyphen); `_CommonRefiFields` requires `old_loan_balance: Money`, `old_annual_rate: Rate`, `new_annual_rate: Rate`, `new_term_months: int`, `closing_costs: Money`, `remaining_months: int`. No `current_loan` field exists; no `mode` discriminator (it's `refi_kind`); no `new_rate` (it's `new_annual_rate`). | lib/refinance.py L288-435 |
| `refi_a.monthly_savings`, `refi_a.npv_breakeven_months`, `refi_a.npv_at_horizon` | RefiResponse exposes `monthly_savings: Decimal`, `npv: Decimal`, `breakeven: RefiBreakeven` (composite). There is no flat `npv_breakeven_months` or `npv_at_horizon`; those live inside `breakeven`. | lib/refinance.py L452-525 |
| `PointsRequestFromLoans(mode="from-loans", no_points_loan=..., points_purchased=points, discounted_loan=..., points_cost=...)` | `PointsRequestFromLoans(mode="from_loans" — underscore, not hyphen, points_cost, loan_with_points: Loan, loan_without_points: Loan, hold_period_months: int, discount_rate_annual: Rate)`. No `no_points_loan`/`discounted_loan`/`points_purchased` fields. | lib/points.py L85-103 |

Because every model is `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`, an executor following Plan 14-03's `<action>` literally will hit `pydantic.ValidationError` on the first call. The acceptance criteria (e.g., `grep -c 'ArmResetRequest(mode="arm-reset"' ≥ 1`) will pass even though the code never runs — that's the shallow-execution risk Dimension 4 flagged.

**Fix Path (planner revision):**

1. Re-read `lib/stress.py` L160-260, `lib/refinance.py` L288-525, `lib/points.py` L65-115. Update the `<action>` blocks in Plan 14-03 Task 1 and Task 2 with the actual upstream field names.
2. Note that `IncomeShockRequest.base_request: AffordabilityRequest` — Phase 14's `_build_stress_block` must construct a full `ForwardModeRequest` (which itself requires a Phase 4 `Household` with `applicants: list[Applicant]`, `escrow: EscrowInputs`, `size`, etc.) for each stress invocation. This is non-trivial composition work that Plan 14-03 currently glosses over; either expand the helper, or compose at the `_build_program_result` boundary (Plan 14-02) and pass the AffordabilityRequest through.
3. `RateShockRequest.rates` is a list of full Rate values, not bps offsets. The +2% rate shock is therefore `[Decimal("0.085000")]` when the base rate is 0.065, not `[200]`.
4. `ArmResetRequest.paths: list[RatePath]` is required. Add `paths=[RatePath(...)]` with the peak-cap index entries (see `lib/arm.py` for `IndexPathEntry` / `RatePath` shapes — Plan 14-03 did not even confirm `RatePath` is the correct class name).
5. `RefiRequest` is `Annotated[RateAndTermRefiRequest | CashOutRefiRequest, Field(discriminator="refi_kind")]`. Use `RateAndTermRefiRequest(refi_kind="rate_and_term", old_loan_balance=..., old_annual_rate=..., new_annual_rate=target_a, new_term_months=..., remaining_months=..., closing_costs=...)`.
6. Map RefiResponse readout to `resp.monthly_savings`, `resp.breakeven.npv_months` (or whichever field on RefiBreakeven; planner verifies), and `resp.npv` for npv_60mo.
7. PointsRequestFromLoans: use `loan_without_points` + `loan_with_points` + `hold_period_months` + `discount_rate_annual`. Plan 14-03 must decide on a `hold_period_months` policy (60? 84?) and a `discount_rate_annual` (mortgage rate? T-bond?). Both are required.

This is a substantial revision (≈ 40% rewrite of Plan 14-03). Recommended: keep the structural decisions intact (D-14-STRESS-01..03, D-14-REFI-01..03) but replace every `<action>` code snippet with one that compiles against the actual upstream API.

### BLOCKER B-2 — VA-program affordability call has no working path

**Severity:** BLOCKER. Plan 14-02 Task 2's `_build_program_result` for `program == "VA30"` constructs an affordability `ForwardModeRequest` with `target_loan_type="va"`. Per `lib/affordability.py` L467-471 (`_validate_common`), this requires `household.va` to be non-None — but Phase 14's NEW `lib.household.Household` has no `va` field, and the plan's note `"VAInputs=None unless program=='VA30' (then construct sentinel residual inputs sufficient to not block; if data unavailable, set residual to a high value that won't trigger VA-RESIDUAL blocker)"` is ambiguous and untested. Plan 14-02 ships no acceptance criterion proving the VA path actually constructs a valid Phase-4 Household.

**Fix Path:** Plan 14-02 Task 2 `<action>` must specify:
- Construction of `VAInputs(region=..., family_size=..., actual_residual_income=...)` for every VA cell. Either (a) add the three fields to Phase 14's Profile, or (b) derive them from Profile + Household (military_status → region mapping; household monthly_income → residual heuristic). Decision is the planner's, but must be made explicit before execution.
- Add a unit test (`test_va_cell_constructs_valid_affordability_request`) that asserts a VA30 cell at any DP does NOT raise `ValueError("household.va block is required ...")`.

### BLOCKER B-3 — `_make_clean_listing` test helper plan omits PropertyListing required fields

**Severity:** BLOCKER (will surface at first golden-test run and at every Wave-1 unit test that calls `_build_program_result`).

**Evidence:** PropertyListing (`lib/property_listing.py` L44-86) requires `price`, `zip`, `property_type`, `source_url` (`min_length=10`), `zpid` (`pattern=r"^\d+$"`), `fetched_at` (datetime). Plan 14-02 Task 3 helper builder docs:

> `_make_clean_listing(price="625000.00", **overrides) -> PropertyListing` — returns a PropertyListing with at minimum price + zip="98101" + property_type="SFH"; allows tax_annual / hoa_monthly / insurance_estimate_annual overrides

This omits `source_url`, `zpid`, `fetched_at`. Construction will raise `ValidationError` on every test. Same issue in Plan 14-06 fixture JSON specs — task action describes `{listing: {price, zip, property_type, tax_annual, ...}}` but does not enumerate source_url / zpid / fetched_at in the required fields.

**Fix Path:** Plan 14-02 Task 3 and Plan 14-06 Tasks 1+2 must add `source_url="https://www.zillow.com/homedetails/synthetic/1_zpid/"`, `zpid="1"` (or similar synthetic value matching the `^\d+$` pattern), `fetched_at=datetime.now(timezone.utc)` (or fixed timestamp string for fixtures) to every PropertyListing construction. Helper-builder signature should default these.

### BLOCKER B-4 — `_build_program_result` references `listing.tax_annual.value` which can be None

**Severity:** BLOCKER (latent — fires on any PropertyListing where the NICE-TO-HAVE money field is omitted, which is the default).

**Evidence:** `ProvenancedMoney.value: Money | None` (L40). Plan 14-02 Task 2 action:

> monthly_tax = quantize_cents((listing.tax_annual.value if listing.tax_annual else Decimal("0")) / Decimal("12"))

This guards `listing.tax_annual is None` but does NOT guard `listing.tax_annual.value is None`. When a tax_annual is present-but-value-None (legitimate state per Phase 13's gap-fill envelope), `quantize_cents(None / Decimal("12"))` raises `TypeError`.

**Fix Path:** Plan 14-02 Task 2 should specify `monthly_tax = quantize_cents((listing.tax_annual.value or Decimal("0")) / Decimal("12")) if listing.tax_annual and listing.tax_annual.value is not None else Decimal("0.00")` (or hoist into a small `_unwrap_provenanced(...)` helper documented at module top). Same fix for `hoa_monthly` and `insurance_estimate_annual`.

### BLOCKER B-5 — DTI ceiling `Decimal("0.50")` for stress eligibility recompute is unjustified

**Severity:** BLOCKER (this is one of the planner's open questions and is currently unresolved in the plan; will produce wrong stress verdict triggers).

**Evidence:** Plan 14-03 Task 1 `<action>` says:

> Sets `breaches_dti_ceiling` per Phase 14 verdict logic (use Decimal("0.50") as the conventional DTI ceiling for now; document as policy choice)

But the actual DTI ceiling is program-specific (Conv ≈ 0.50, FHA ≈ 0.57, VA ≈ 0.41 with residual income gating, Jumbo ≈ 0.43). Hardcoding 0.50 for ALL stress rows over-conservatively breaches DTI on FHA cells (false-positive WATCH) and under-conservatively passes VA cells (false-negative GO). This contradicts D-14-VERDICT-02 ("DTI breaches ceiling at income × 0.70") which is meant to reuse the affordability engine's per-program ceiling.

**Fix Path:** Plan 14-03 must call `lib.affordability.evaluate(...)` for each shocked cell and read the `blocked_by` string to determine breach (mirrors Plan 14-02 Task 2's existing pattern for matrix eligibility), OR pull program-specific ceilings from a new module constant (e.g., `DTI_CEILING_BY_PROGRAM`). This decision is the planner's, but the current hardcoded `Decimal("0.50")` is silently wrong for 3 of 5 programs.

### BLOCKER B-6 — Plan 14-03 helper signature inconsistencies vs. 14-05 callsite

**Severity:** BLOCKER (mechanical).

Plan 14-03 ships `_build_tax_block(matrix, household, profile, todays_rates)` (4 args) but `must_haves.truths` describes `_build_tax_block(matrix, profile)` (2 args) and Plan 14-04 frontmatter `key_links` says `_build_tax_block(matrix, profile)`. Plan 14-05 Task 1 `<action>` calls `_build_tax_block(matrix, household, profile, todays_rates)` (4 args). The 14-03 frontmatter is the authoritative version (4 args), so 14-04 frontmatter is just outdated (warning), but the 14-03 `must_haves.truths` line "(matrix, profile)" is genuinely contradictory with its own `<action>` body.

**Fix Path:** Plan 14-03 `must_haves.truths` line 4 should read `_build_tax_block(matrix, household, profile, todays_rates)`. Plan 14-04 `key_links` is informational only and need not be updated (no execution impact), so this is a minor consistency fix.

### WARNING W-1 — Condo fixture verdict is non-deterministic (Open Question #6 from planner)

**Severity:** WARNING. Plan 14-06 says verdict for `condo_with_hoa_seattle.json` is "GO or WATCH" — to be pinned by hand-calc during fixture creation. This is acceptable IF the planner commits to running the hand-calc as part of Task 2; the risk is the executor punts and pins to whichever the engine emits (auto-capture), which contradicts the explicit "hand-calculated, never auto-captured" policy.

**Fix Path:** Plan 14-06 Task 2 `<acceptance_criteria>` should add: `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/condo_with_hoa_seattle.json').read()); assert d['expected_response']['verdict']['level'] in ('GO', 'WATCH'); assert 'notes' in d and 'hand-calc anchor' in d['notes'].lower()"` — and require the `notes` field to cite a specific cascade-level derivation (e.g., "Cascade level 5: 2 non-FHA programs eligible → GO"). Current acceptance criteria do not enforce hand-calc provenance for the condo case.

### WARNING W-2 — Refi target_rate scenario_label uses underscore (planner OQ #2 from check prompt)

**Severity:** OK as-is — `Literal["minus_100bps", "fred_times_0_85"]`. Python `Literal` accepts any string, the underscore form is valid, and "fred_times_0_85" reads cleanly. RESEARCH.md L338 used the period form `"fred_times_0.85"`, which would also work in a Literal but is mildly noisier in JSON. Either form is acceptable; planner's choice of underscore is consistent and clean.

### WARNING W-3 — VA funding fee `funding_fee / 360` for monthly_mi is incorrect amortization (planner OQ #4)

**Severity:** WARNING (mathematically off; not blocking for cell-shape verification but golden fixtures will be slightly off if hand-calc uses true amortization).

**Evidence:** Plan 14-02 Task 2 says `monthly_mi=quantize_cents(funding_fee / Decimal(360))` for VA cells. This is straight-line, not amortized. Phase 4 D-03 (referenced in Plan 14-02 read_first) FINANCES the UFMIP into the principal and the monthly cost is then `quantize_cents(financed_principal * mip.annual_mip_pct / 12)` — same approach should apply to VA. VA funding fee, like FHA UFMIP, is typically FINANCED INTO PRINCIPAL (no separate monthly_mi line item), with the amortization absorbing it. Straight-line `funding_fee / 360` produces a number that's too low by the interest-component fraction.

**Fix Path:** Plan 14-02 Task 2's VA branch should set `monthly_mi = Decimal("0.00")` and rely on the financed-principal path to capture the funding fee in monthly_pi. OR pass an explicit annotation that monthly_mi for VA is "amortized funding-fee proxy" with the straight-line formula intentionally chosen as a v1.1 simplification (document loudly in module docstring + cell `eligible_reasons`). Either way, the current plan is silent on this trade-off — the planner's open question #4 is not resolved.

### WARNING W-4 — Household docstring "DISTINCT from lib.affordability.Household" (planner OQ #1)

**Severity:** WARNING (cosmetic). Plan 14-01 Task 1 prescribes the docstring `"DISTINCT from lib.affordability.Household (Phase 4 frozen contract)"` per PATTERNS.md L105-108. This is a reasonable name-collision mitigation, but the import boundary issue persists: any file that does `from lib.household import Household` AND `from lib.affordability import Household` will shadow one symbol. Plan 14-02 Task 2 already does both imports (it imports the Phase 14 Household at the top and `Household as AffordabilityHousehold` from affordability via the `from lib.affordability import (..., Household as AffordabilityHousehold, ...)` block) — the `as AffordabilityHousehold` alias resolves the shadowing.

This is fine. No fix required, but the planner's open question #1 should be marked RESOLVED in the next iteration of Plan 14-01.

### WARNING W-5 — `_build_program_result`'s mapping of `monthly_obligations` into `MonthlyDebts.other` (planner OQ #3)

**Severity:** WARNING. Plan 14-02 Task 2 step 10 says:

> MonthlyDebts populated from household.monthly_obligations (place all in "other" bucket)

This is intentional — Phase 14's Household carries an AGGREGATED `monthly_obligations` (per CONTEXT D-14-MODELS-01), while Phase 4's MonthlyDebts splits auto/student/cc/other. Lumping into `other` preserves the DTI math but loses the per-category audit trail. For Phase 14 v1.1 this is acceptable (no per-category report rendering); for v1.2 if users want category breakdown the Household model would need expansion.

**Fix Path:** No fix required for Phase 14. Add a planner note to Plan 14-02 `<output>` summary documenting the split-collapse decision so future-you understands why the audit trail is reduced.

---

## Test-Map Coverage (Dimension 8 supplemental)

Per VALIDATION.md row → plan task mapping:

| VALIDATION.md row | Plan that closes it | Status |
|---|---|---|
| ANLZ-01 (multi-program fan-out) | 14-02 Task 3 + 14-05 Task 2 | covered |
| ANLZ-01 (MissingCountyDataError graceful) | 14-02 Task 3 | covered |
| ANLZ-01 (VA gating) | 14-02 Task 3 + 14-05 Task 2 | covered |
| ANLZ-02 (24 or 30 cells) | 14-02 Task 3 + 14-05 Task 2 | covered |
| ANLZ-02 (ineligible rows populate numerics) | 14-02 Task 3 | covered |
| ANLZ-02 (DP sweep Decimal-from-strings) | 14-02 Task 3 | covered |
| ANLZ-03 (stress @ preferred DP only) | 14-03 Task 3 — **blocked by B-1** | red |
| ANLZ-03 (ARM reset Conv30 only) | 14-03 Task 3 — **blocked by B-1** | red |
| ANLZ-03 (refi 2 scenarios per program) | 14-03 Task 3 — **blocked by B-1** | red |
| ANLZ-03 (points breakeven Conv-family only) | 14-03 Task 3 — **blocked by B-1** | red |
| ANLZ-03 (Pub 936) | 14-03 Task 3 | covered |
| VERD-01 (NO_GO no eligible at any DP) | 14-04 Task 2 | covered |
| VERD-01 (NO_GO at preferred DP) | 14-04 Task 2 | covered |
| VERD-01 (WATCH income shock) | 14-04 Task 2 | covered |
| VERD-01 (WATCH FHA-MIP burden) | 14-04 Task 2 | covered |
| VERD-01 (GO non-FHA eligible) | 14-04 Task 2 | covered |
| VERD-01 (predicate_code + computed_value) | 14-04 Task 2 + 14-06 Task 3 | covered |
| VERD-01 (citation coverage) | 14-04 Task 2 + 14-06 Task 3 | covered |
| (model) Household extra=forbid | 14-01 Task 3 | covered |
| (model) Profile va_eligible default | 14-01 Task 3 | covered |
| (composition) Float rejection | 14-02 Task 3 | covered |
| (composition) JSON < 100KB | 14-05 Task 2 | covered |
| (composition) FRED lock serialization | 14-02 Task 3 + 14-05 Task 2 | covered |

Coverage matrix is complete by intent. ANLZ-03 rows are red because Plan 14-03's API misuse will fail at runtime.

---

## Dimensional Scoring Summary

| Dimension | Score | Status |
|-----------|-------|--------|
| 1. Goal achievement | 1/2 | partial — B-1, B-2, B-3, B-4, B-5 block delivery |
| 2. Requirement coverage | 2/2 | pass |
| 3. CONTEXT.md compliance | 1/2 | partial — locked decisions intended but B-1 prevents implementation |
| 4. Anti-shallow execution | 1/2 | partial — Plan 14-03 acceptance criteria are grep-only, not semantic |
| 5. Dependency correctness | 2/2 | pass |
| 6. Pitfall mitigation | 2/2 | pass (Pitfalls 1-12 explicitly addressed) |
| 7. Security threat model | 2/2 | pass (T-14-* across all 6 plans) |
| 8. Validation / Nyquist | 2/2 | pass (VALIDATION.md complete; sampling continuous) |

**Total: 13 / 16 — would be 16/16 if Plan 14-03 is revised to match actual upstream lib APIs and Plans 14-02 / 14-06 are tightened on PropertyListing required-fields + DTI ceiling + VA path + ProvenancedMoney null-value handling.**

---

## Recommended Revisions

### Plan 14-01
- (cosmetic) Mark planner OQ #1 (Household name collision) RESOLVED in summary.

### Plan 14-02
- **[14-02] [Task 2] [Dimension 1+4] B-2:** Resolve the VA-program affordability construction. Either extend Profile with `va_region: Region | None`, `va_family_size: int | None`, `va_actual_residual_income: Money | None` and propagate these into the VAInputs construction, OR specify a deterministic synthesis policy (e.g., "VA cells construct VAInputs(region='north_midwest', family_size=2, actual_residual_income=household.monthly_income * Decimal('0.5'))" and add eligible_reasons += ["VA-RESIDUAL-SYNTHESIZED-V1"] warning). Add a unit test asserting VA30 cell at preferred DP does not raise the household.va-required ValueError.
- **[14-02] [Task 3] [Dimension 1] B-3:** Update `_make_clean_listing` builder to default `source_url="https://www.zillow.com/homedetails/synthetic/1_zpid/"`, `zpid="1"`, `fetched_at=datetime.now(timezone.utc)` so PropertyListing construction does not raise.
- **[14-02] [Task 2] [Dimension 1] B-4:** Replace the ProvenancedMoney unwrap pattern with a guarded helper: `def _unwrap_provenanced(pm: ProvenancedMoney | None, default: Decimal = Decimal("0.00")) -> Decimal: return pm.value if (pm and pm.value is not None) else default`. Use it for tax_annual / hoa_monthly / insurance_estimate_annual.
- **[14-02] [Task 2] [Dimension 6] W-3:** Resolve VA funding-fee monthly treatment. Recommend: finance into principal, set `monthly_mi = Decimal("0.00")` for VA cells, document in module docstring + add eligible_reasons += ["VA-FUNDING-FEE-FINANCED"].

### Plan 14-03
- **[14-03] [Task 1] [Dimension 1+3] B-1:** Rewrite the `_build_stress_block` + `_build_refi_block` `<action>` code blocks against the actual upstream APIs (lib/stress.py L160-260; lib/refinance.py L288-525). Specifically:
  - `RateShockRequest(mode="rate-shock", loan=cell_loan, rates=[shocked_rate])` (full Rate, not bps).
  - `IncomeShockRequest(mode="income-shock", base_request=<ForwardModeRequest>, reductions=[Decimal("0.30")], dti_threshold=program_specific_ceiling)`.
  - `ArmResetRequest(mode="arm-reset", base_arm_request=ARMRequest(...), paths=[RatePath(...)])` — paths is required.
  - `RateAndTermRefiRequest(refi_kind="rate_and_term", old_loan_balance=..., old_annual_rate=current_rate, new_annual_rate=target_rate, new_term_months=..., remaining_months=..., closing_costs=...)`.
  - Read RefiResponse via `resp.monthly_savings` + `resp.breakeven.npv_months` + `resp.npv`.
- **[14-03] [Task 1] [Dimension 1] B-5:** Replace hardcoded `Decimal("0.50")` DTI ceiling with per-program ceiling sourced from `lib.affordability.evaluate(...)` blocker output, OR introduce a module constant `_DTI_CEILING_BY_PROGRAM: Final[dict[str, Decimal]] = {"Conv30": ..., "Conv15": ..., "FHA30": ..., "VA30": ..., "Jumbo30": ...}` with citations.
- **[14-03] [Task 2] [Dimension 1] B-1:** Rewrite `_build_points_block` against `PointsRequestFromLoans(mode="from_loans", points_cost, loan_with_points, loan_without_points, hold_period_months, discount_rate_annual)`. Plan must specify the `hold_period_months` policy (recommend 60 months — 5-year hold) and `discount_rate_annual` (recommend the program's `current_rate` to match Phase 6 D-09 convention).
- **[14-03] [must_haves.truths line 4] [Dimension 5] B-6:** Update to `_build_tax_block(matrix, household, profile, todays_rates) → TaxBlock` (4 args, matching the `<action>` body).

### Plan 14-04
- No changes required. Plan is sound.

### Plan 14-05
- No changes required if Plan 14-03 is revised. Plan 14-05 composes 14-03's helpers and inherits the API fix.

### Plan 14-06
- **[14-06] [Task 1] [Dimension 1] B-3:** Fixture `listing` block JSON must include `source_url`, `zpid`, `fetched_at` (e.g., `"source_url": "https://www.zillow.com/homedetails/synthetic/1_zpid/"`, `"zpid": "1"`, `"fetched_at": "2026-05-17T00:00:00Z"`). Same for Tasks 2 condo + jumbo fixtures. Update acceptance criteria to assert these fields exist.
- **[14-06] [Task 2] [Dimension 1] W-1:** Tighten condo fixture acceptance criterion to require the `notes` field to cite a specific cascade-level derivation (planner OQ #6 — verdict "GO or WATCH" must be pinned to one value by hand-calc, with the cascade-level reasoning embedded in notes).

---

## CHECK VERDICT: REVISE

Plan 14-03 is unimplementable as written — every helper invokes upstream APIs with fabricated field names. Five additional blockers (B-2 through B-6) and four warnings (W-1, W-3, W-4, W-5) compound the risk. Plans 14-01, 14-04, 14-05 are sound; Plan 14-02 needs three targeted fixes (B-2, B-3, B-4, W-3); Plan 14-06 needs two targeted fixes (B-3 propagation, W-1).

**Single-pass fix:** the planner should re-read `lib/stress.py`, `lib/refinance.py`, `lib/points.py` once, then rewrite Plan 14-03's two `<action>` blocks against the verified upstream signatures (B-1, B-5, B-6) and apply the smaller fixes to Plans 14-02 + 14-06 (B-2, B-3, B-4, W-1, W-3). After revision, this check should return PASS — every other dimension is solid.

---

## Iteration 2 Re-Check (2026-05-17)

**Re-checked:** 2026-05-17
**Plans re-verified:** 14-01 (RESOLVED notes), 14-02 (substantial), 14-03 (substantial rewrite), 14-04 (unchanged), 14-05 (unchanged), 14-06 (substantial)
**Upstream lib code re-read:** `lib/stress.py` L94-225, `lib/refinance.py` L253-535, `lib/points.py` L65-145, `lib/arm.py` L28-145, `lib/affordability.py` L390-495, `lib/property_listing.py` L25-105, `lib/rules/types.py` L29, `lib/rules/irs_pub936.py` L60-95, `lib/amortize.py` L41-71 (Schedule/Payment).

### Per-Finding Verification Table

| ID | Original Severity | Iteration 1 Failure | Iteration 2 Fix Location | Verified? |
|----|---|---|---|---|
| **B-1** | BLOCKER — fabricated stress/refi/points API surface | Plan 14-03 invoked fields that did not exist: `base_loan`, `rate_shocks_bps`, `income_multipliers`, `max_dti`, `current_loan`, `new_rate`, `mode="rate-term"`, `no_points_loan`, `discounted_loan`, `mode="from-loans"`. | Plan 14-03 `<action>` Task 1 + Task 2 rewritten against actual signatures: `RateShockRequest(mode="rate-shock", loan=cell_loan, rates=[shocked_rate], baseline_label=..., scenario_label=...)`; `IncomeShockRequest(mode="income-shock", base_request=..., reductions=[Decimal("0.30")], dti_threshold=ceiling)`; `ArmResetRequest(mode="arm-reset", base_arm_request=ARMRequest(loan=cell_loan, arm_terms=_CONV_5_1_ARM_TERMS, assumed_index_rate=...), paths=[RatePath(name="parallel-shift", params={"shift_bps": _CONV_5_1_ARM_TERMS.lifetime_cap_bps})])`; `RateAndTermRefiRequest(refi_kind="rate_and_term", old_loan_balance, old_annual_rate, new_annual_rate, new_term_months, old_remaining_months, closing_costs, discount_rate_annual, analysis_horizon_months=60)`; `PointsRequestFromLoans(mode="from_loans", points_cost, loan_with_points, loan_without_points, hold_period_months=60, discount_rate_annual)`. RefiResponse readout via `resp.monthly_savings`, `resp.npv`, `resp.breakeven.npv_months`. Acceptance criteria L548-583 enumerate ≥20 grep gates that pin each correct field name. **Cross-checked against actual lib code: every signature matches verbatim** (lib/stress.py L177-205, L208-223; lib/refinance.py L288-401, L452-489; lib/points.py L85-103; lib/arm.py L87-105). | ✅ RESOLVED |
| **B-2** | BLOCKER — VA-program affordability has no working path | `_build_program_result` for `program=="VA30"` did not construct `VAInputs`, causing `_validate_common` (lib/affordability.py L467-471) to raise `ValueError("household.va block is required ...")`. No test proved the path constructs valid input. | Plan 14-02 Task 2 step 11 + Behavior 12b. VA branch builds `VAInputs(region="northeast", family_size=2, actual_residual_income=quantize_cents(household.monthly_income * Decimal("0.5")))`; affordability `Household` is constructed with `va=va_inputs` for VA cells, `va=None` otherwise. `region="northeast"` matches `lib/rules/types.py` L29 `Region = Literal["northeast","midwest","south","west"]` exactly. `eligible_reasons += ["VA-RESIDUAL-SYNTHESIZED-V1"]`. New test `test_va_cell_constructs_valid_affordability_request` (Plan 14-02 Task 3 Behavior list L743) asserts no `ValueError("household.va block is required …")` raised and both `VA-RESIDUAL-SYNTHESIZED-V1` and `VA-FUNDING-FEE-FINANCED` appear in `eligible_reasons`. Plan 14-03 Helper 0 `_construct_affordability_request_for_cell` mirrors this branch for income-shock reconstruction (loud doc that any change to 14-02 must be mirrored). | ✅ RESOLVED |
| **B-3** | BLOCKER — `_make_clean_listing` omits PropertyListing required fields (`source_url`, `zpid`, `fetched_at`) | Helper builder + fixture JSON would raise `ValidationError` at construction. | Plan 14-02 Task 3 step 4 redefines `_make_clean_listing(... source_url="https://www.zillow.com/homedetails/synthetic/1_zpid/", zpid="1", fetched_at=datetime(2026,5,17,tzinfo=timezone.utc), ...)` with all three audit fields defaulted (acceptance criterion L839). Plan 14-06 Task 1 (L226-228) + Task 2 (L370-373, L403-406) all enumerate the same defaults verbatim in fixture JSON. Acceptance criteria L314, L322-324, L443-451 explicitly assert `'source_url' in l and len(l['source_url']) >= 10`, `l['zpid'].isdigit()`, `'fetched_at' in l` for every fixture. Pydantic round-trip validation (Plan 14-06 Task 1 L317, Task 2 L437) re-validates each listing block via `PropertyListing.model_validate_json(json.dumps(d['listing']))`. | ✅ RESOLVED |
| **B-4** | BLOCKER — `listing.tax_annual.value` can be None | `ProvenancedMoney.value: Money \| None` — present-wrapper-with-None-value is a legitimate Phase 13 gap-fill state; `None / Decimal("12")` raises `TypeError`. | Plan 14-02 Task 2 Helper 0 introduces `_unwrap_provenanced(pm: ProvenancedMoney \| None, default: Decimal = Decimal("0.00")) -> Decimal`: returns `pm.value if (pm is not None and pm.value is not None) else default` (L562-576). Step 6 uses it 3× for `tax_annual`, `insurance_estimate_annual`, `hoa_monthly` (L614-619). Grep gate `grep -c '_unwrap_provenanced' lib/property_analysis.py` returns ≥4 (1 def + 3 uses; L682). New test `test_provenanced_value_none_unwraps_to_zero` (Behavior 16 L531; acceptance L744) asserts no TypeError + each component equals `Decimal("0.00")`. | ✅ RESOLVED |
| **B-5** | BLOCKER — DTI ceiling hardcoded `Decimal("0.50")` for all stress rows | False-positive WATCH on FHA cells (real ceiling 0.57); false-negative GO on VA cells (real ceiling 0.41). | Plan 14-03 Task 1 adds module-level `_DTI_CEILING_BY_PROGRAM` constant (L310-321) — Conv30=0.50, Conv15=0.50, FHA30=0.57, VA30=0.41, Jumbo30=0.43, each with regulatory citation. Threaded into `IncomeShockRequest(... dti_threshold=ceiling)` (L415); rate-shock + arm-reset rows compute `breaches_dti_ceiling = stressed_dti_back > ceiling` (L459, behavior 2). New test `test_dti_ceiling_per_program` (Task 3 L820-851) tunes household income so income-shock breaches VA's 0.41 ceiling but NOT FHA's 0.57, asserting VA row has `breaches_dti_ceiling=True` AND FHA row has `breaches_dti_ceiling=False`. Acceptance L553-557 pins all 4 dictionary entries by grep. | ✅ RESOLVED |
| **B-6** | BLOCKER — `_build_tax_block` `must_haves.truths` line 4 said 2 args; `<action>` body + 14-05 callsite said 4 args | Internal contradiction in 14-03 frontmatter. | Plan 14-03 frontmatter `must_haves.truths` line 4 (L30 of 14-03) now reads `_build_tax_block(matrix, household, profile, todays_rates) → TaxBlock computes first-year interest per program AND over_750k_cap flag via lib.rules.irs_pub936.qualified_loan_limit(filing_status=profile.filing_status) with default grandfathering booleans (Pitfall 11) (B-6 — signature pinned to 4 args)`. Task 2 `<action>` body (L706-744) ships signature `def _build_tax_block(matrix, household, profile, todays_rates)`. Acceptance L773 asserts `awk` extraction shows all 4 parameters. Plan 14-05 Task 1 callsite (L241) calls `_build_tax_block(matrix, household, profile, todays_rates)` — aligned. | ✅ RESOLVED |
| **W-1** | WARNING — Condo fixture verdict is non-deterministic ("GO or WATCH") | Risk: executor auto-captures whichever the engine emits, violating "hand-calculated, never auto-captured" policy. | Plan 14-06 Task 2 Behavior 4 + 4b (L351-352) require `expected_response.verdict.level` to be EXACTLY one of `"GO"` or `"WATCH"` (NOT the string "GO or WATCH"). Top-level `notes` MUST contain BOTH substrings `"cascade"` (case-insensitive) AND `"hand-calc"` (case-insensitive). Acceptance L445 enforces via inline Python: `assert d['expected_response']['verdict']['level'] in ('GO','WATCH'); assert 'notes' in d and 'cascade' in d['notes'].lower() and 'hand-calc' in d['notes'].lower()`. Action L383-399 prescribes the 5-step hand-trace recipe and a verbatim cascade-derivation template for the notes. | ✅ RESOLVED |
| **W-3** | WARNING — VA funding-fee straight-line `funding_fee / 360` is wrong amortization | Hand-calc fixtures would diverge from engine output by the interest-component fraction. | Plan 14-02 Task 2 Step 4 VA branch (L612): `financed_principal = quantize_cents(base_loan_amount + funding_fee)`; `monthly_mi = Decimal("0.00")`; `eligible_reasons += ["VA-FUNDING-FEE-FINANCED"]`. Mirrors Phase 4 D-03 financed-UFMIP convention. Acceptance L693-694 pins `VA-FUNDING-FEE-FINANCED` marker grep. Plan 14-02 Behavior 12 (L526) + Behavior 12b confirm both `VA-RESIDUAL-SYNTHESIZED-V1` AND `VA-FUNDING-FEE-FINANCED` markers appear together. | ✅ RESOLVED |
| **W-4** | WARNING (cosmetic) — Household name-collision OQ #1 should be marked RESOLVED | Status note only. | Plan 14-01 objective L68-70 explicitly states: "**OQ #1 (Household name collision) — RESOLVED.** PATTERNS.md L105-108 + Plan 14-02 import-aliasing (`from lib.affordability import Household as AffordabilityHousehold`) fully disambiguate." Success criterion 6 (L362) repeats. Output instructions (L373) require summary note. | ✅ RESOLVED |
| **W-2** | WARNING — `scenario_label="fred_times_0_85"` underscore form (planner OQ #2) | Already noted as "OK as-is" in iteration 1. | Plan 14-02 RefiRow scenario_label literal pair `Literal["minus_100bps", "fred_times_0_85"]` unchanged. No action required. | ✅ (no change needed) |
| **W-5** | WARNING — `monthly_obligations` collapse into `MonthlyDebts.other` | Already deemed acceptable for v1.1 with planner-note recommendation. | Plan 14-02 Task 2 step 11 documents collapse (L635) + 14-PLAN-CHECK W-5 reference; output summary instructions intact. | ✅ (acceptable for v1.1) |

### Cross-Plan Regression Sweep

- **Plans 14-04 + 14-05 compatibility:** Plan 14-04 imports `Verdict`, `VerdictReason`, `ProgramResult`, `DownPaymentMatrix`, `StressBlock`, `StressRow` from `lib.property_analysis` — no dependence on 14-02/14-03 helper signatures (verified via `grep -c "_build_(tax_block|stress_block|refi_block|points_block)" 14-04-PLAN.md` returns 0). Plan 14-05 Task 1 callsites match 14-02/14-03 helper signatures exactly: `_build_stress_block(matrix, listing, household, profile, todays_rates)` (5 args), `_build_refi_block(matrix, household, todays_rates)` (3 args), `_build_points_block(matrix, household, todays_rates)` (3 args), `_build_tax_block(matrix, household, profile, todays_rates)` (4 args). Synthesize signature `synthesize(matrix, stress, household, profile)` matches 14-04 frontmatter L184 and 14-05 L244, L286.
- **Pitfall mitigations 1-12 (RESEARCH §"Pitfalls"):** All preserved through revision. Pitfall 1 (`_CONV_PMI_ANNUAL_RATE` constant + `PMI-RATE-ESTIMATED-0.0075` reason) — intact (14-02 Task 1 L334-335, Task 2 step 4 L610, acceptance L691, L738). Pitfall 2 (Decimal-from-strings on DOWN_PAYMENT_PCTS) — intact (14-02 Behavior 3 L291, Task 3 `test_dp_sweep_uses_decimal_strings`). Pitfall 3 (signed Decimal not Money for RefiRow.monthly_savings/npv_60mo) — intact (14-02 Task 1 L399-401 explicit Field annotations + `test_refi_signed_decimal_fields`). Pitfall 4 (delegate to predicates) — intact (every helper delegates). Pitfall 5 (County from Household, not zip) — intact (14-02 Task 2 Helper 2 L590, acceptance L684). Pitfall 6 (MI in PITI; quantize ONCE) — intact (14-02 step 7 L622, acceptance L686-687). Pitfall 7 (VERDICT_* prefix discipline) — intact (14-04 Task 1 L142-147 + acceptance L175-179, citation-coverage meta-test 14-04 Task 2 + tightened in 14-06 Task 3). Pitfall 8 (ARM 5/1 stress requires full ARMRequest with ARMTerms) — intact (14-02 `_CONV_5_1_ARM_TERMS` constant L337-346; 14-03 Behavior 7 + Task 1 `<action>` L429-447 with all 8 ARMTerms fields; `paths` field added per B-1 fix). Pitfall 9 (FRED with_cache_lock) — intact (14-02 Helper 1 L578 + acceptance L683; 14-05 integration test_fred_lock_serialization). Pitfall 10 (JSON < 100KB; no Schedule.payments on ProgramResult) — intact (14-02 ProgramResult has no `payments` field L362-376; 14-05 `test_report_size_budget` flipped to assertion L325). Pitfall 11 (IRS Pub 936 grandfathering defaults False) — intact (14-03 Task 2 L713-715 uses defaults; acceptance L771 grep excludes `has_grandfathered_debt` outside comments). Pitfall 12 (citation-coverage meta-test) — intact (14-04 in-test version + 14-06 fixture-based tightening L488-513).
- **VALIDATION.md alignment:** All 24 test-map rows mapped to plan tasks. ANLZ-03 rows (previously red due to B-1) — now green: Task 1 of 14-03 + Task 3 flip stubs to real assertions for `test_stress_at_preferred_dp_only`, `test_arm_reset_conv30_only`, `test_refi_two_scenarios_per_program`, `test_points_breakeven_per_program`, `test_tax_block_pub936`. New test `test_dti_ceiling_per_program` (B-5) added in 14-03 Task 3 — extends VERD-01 coverage beyond the original test map (acceptable expansion).
- **Threat models (T-14-FLOAT, T-14-FRED-RACE, T-14-STALE-REF, T-14-REASON, T-14-PII):** Present in all 6 plans' `<threat_model>` blocks. Each carries Disposition + Mitigation Plan citing specific test or invariant.
- **Architectural Responsibility Map (RESEARCH §"Architectural Responsibility Map"):** All logic remains in Python `lib/` tier; no spillover into skill / CLI / data tiers. Plans 14-01..14-06 all touch only `lib/*.py` + `tests/*.py` + `tests/fixtures/property_analysis/*.json` (file-modified frontmatter verified).

### New Issues Detected in Iteration 2

| Severity | Finding | Location | Recommendation |
|----------|---------|----------|----------------|
| INFO | Plan 14-02 Behavior 4 says `PROGRAMS_BASE == ["Conv30", "Conv15", "FHA30"]` (3 entries); Task 3 Behavior says `test_matrix_cell_count` expects 18 cells (3×6) for non-jumbo non-VA. Plan 14-05 `test_analyze_end_to_end` Behavior says 18 cells. **Internal consistency confirmed across plans.** | 14-02 L292, L729; 14-05 L314 | No action — earlier check report contained a stale "24-or-30" hint that was about jumbo/VA states; default base is 18, jumbo+VA adds rows. Confirmed correct. |
| INFO | Plan 14-03 Task 1's `_stress_row_from_arm_reset` reads `max_payment` from upstream `StressRow` (lib/stress.py L138 confirms field exists). For arm_reset, the planner recomputes `stressed_piti = max_payment + cell.monthly_tax + ... + cell.monthly_mi`. This is correct (monthly_pi at peak rate equals max_payment in arm-reset mode per lib/stress.py L121: "arm-reset: total_interest, max_payment, reset_count, highest_rate"). | 14-03 L462 | No action. |
| INFO | Plan 14-03 income-shock `breaches_dti_ceiling` derivation: the planner passes `dti_threshold=ceiling` (per-program) to `IncomeShockRequest`, so upstream `StressRow.breaches_threshold` (lib/stress.py L136) already reflects the per-program ceiling. Phase 14's `breaches_dti_ceiling` should mirror it. The plan's behavior 3 + helper text says "for income_shock: read from upstream `lib.stress.StressRow.dti_back`" which is the engine-recomputed DTI — Phase 14 then compares against `ceiling` again. **Both paths converge to the same boolean** because `dti_threshold` and `ceiling` are the same value. Defensible. | 14-03 L458-459 | No action; planner could collapse to reading upstream `breaches_threshold` directly in v1.2 for less redundancy. |
| INFO | RESEARCH.md §"Open Questions" heading lacks the `(RESOLVED)` suffix the Dimension 11 check looks for. However, each individual OQ has an inline resolution: OQ #1 RESOLVED in 14-01 L70; OQ #2 resolved as `fred_times_0_85` literal in 14-02 RefiRow; OQ #3 (closing-costs hardcode) resolved per `_CLOSING_COSTS_PCT` 14-02 L349; OQ #4 (MissingCountyDataError) resolved per `_determine_programs` warnings path 14-02 L515. | 14-RESEARCH.md L1044 | Cosmetic. Recommend the planner update the RESEARCH header to `## Open Questions (RESOLVED)` in a future iteration; no execution impact. Not a blocker. |
| INFO | Plan 14-06 Task 2's hand-calc cascade trace example (L394-399) for condo verdict cites "Conv30 stressed DTI under -30% income = (piti + $300)/(9500*0.70) ≈ 0.46 < 0.50 → no breach". This relies on Conv30's 0.50 ceiling per `_DTI_CEILING_BY_PROGRAM` (B-5 constant). **Consistency confirmed.** | 14-06 L397 | No action. |

### Dimensional Re-Scoring (Iteration 2)

| Dimension | Iteration 1 | Iteration 2 | Note |
|-----------|-------------|-------------|------|
| 1. Goal achievement | 1/2 | **2/2** | B-1 + B-2 + B-3 + B-4 + B-5 + B-6 all resolved; every helper uses verified upstream signatures. |
| 2. Requirement coverage | 2/2 | 2/2 | unchanged. |
| 3. CONTEXT.md compliance | 1/2 | **2/2** | Locked decisions now implementable; D-14-STRESS-01..03 + D-14-REFI-01..03 actually constructible. |
| 4. Anti-shallow execution | 1/2 | **2/2** | Plan 14-03 `<action>` blocks no longer grep-pass-but-runtime-fail; acceptance criteria pin exact field names from verified signatures. |
| 5. Dependency correctness | 2/2 | 2/2 | unchanged. |
| 6. Pitfall mitigation | 2/2 | 2/2 | unchanged. |
| 7. Security threat model | 2/2 | 2/2 | unchanged. |
| 8. Validation / Nyquist | 2/2 | 2/2 | unchanged; new test `test_dti_ceiling_per_program` extends coverage. |

**Total: 16 / 16.**

---

## CHECK VERDICT (Iteration 2): PASS

All 6 blockers (B-1..B-6) and 4 actionable warnings (W-1, W-3, W-4, W-5) from iteration 1 are fully resolved with verifiable acceptance criteria. W-2 was deemed OK as-is in iteration 1 (no action required). Every upstream API call in Plan 14-03 has been cross-checked against actual `lib/stress.py`, `lib/refinance.py`, `lib/points.py`, `lib/arm.py`, `lib/affordability.py` code and matches verbatim. No new blockers introduced by the revision. Plans 14-04 + 14-05 remain compatible with revised 14-02/14-03 helper signatures.

**Plans are ready for `/gsd-execute-phase 14`.**

### What's Ready for Execution

- **Wave 1 (parallel):** 14-01 (Household + Profile models + tests), 14-02 (matrix models + per-cell engine + Wave-1 tests + Wave-2+ stubs).
- **Wave 2 (parallel after Wave 1):** 14-03 (stress/refi/points/tax helpers + flipping Wave-2 stubs), 14-04 (verdict synthesis + cascade tests + in-test citation coverage).
- **Wave 3 (sequential after Wave 2):** 14-05 (analyze() composition + end-to-end + size-budget tests), 14-06 (3 hand-calc golden fixtures + flipping golden stubs + fixture-based citation coverage).

### Verified Surface Areas

| Concern | Where Verified |
|---------|----------------|
| Upstream stress API | `RateShockRequest(loan, rates, baseline_label, scenario_label)` — lib/stress.py L177-189 ✓ |
| Upstream stress API | `IncomeShockRequest(base_request, reductions, dti_threshold, scenario_label)` — lib/stress.py L192-205 ✓ |
| Upstream stress API | `ArmResetRequest(base_arm_request, paths, scenario_label)` + `paths min_length=1` — lib/stress.py L208-223 ✓ |
| Upstream stress API | `RatePath(name, params)` with `parallel-shift` literal — lib/stress.py L94-109 ✓ |
| Upstream refi API | `RateAndTermRefiRequest(refi_kind="rate_and_term", old_loan_balance, old_annual_rate, old_remaining_months, new_annual_rate, new_term_months, closing_costs, discount_rate_annual, analysis_horizon_months)` — lib/refinance.py L288-401 ✓ |
| Upstream refi response | `RefiResponse.monthly_savings`, `.npv`, `.breakeven: RefiBreakeven`; `RefiBreakeven.npv_months` — lib/refinance.py L452-489 + L257-280 ✓ |
| Upstream points API | `PointsRequestFromLoans(mode="from_loans", points_cost, loan_with_points, loan_without_points, hold_period_months, discount_rate_annual)` — lib/points.py L85-103 ✓ |
| Upstream points response | `PointsResponse.simple_breakeven_months`, `.npv_breakeven_months` — lib/points.py L128-129 ✓ |
| Upstream ARM API | `ARMRequest(loan, arm_terms, assumed_index_rate, index_path)` — lib/arm.py L87-105 ✓ |
| Upstream affordability VA | `VAInputs(region: Region, family_size, actual_residual_income)`; `Region = Literal["northeast","midwest","south","west"]` — lib/affordability.py L393-405 + lib/rules/types.py L29 ✓ |
| Upstream affordability VA gate | `_validate_common` raises when `target_loan_type=="va" and household.va is None` — lib/affordability.py L467-471 ✓ |
| Upstream PropertyListing | Required fields `source_url` (min_length=10), `zpid` (pattern `^\d+$`), `fetched_at: datetime` — lib/property_listing.py L84-86 ✓ |
| Upstream ProvenancedMoney | `value: Money \| None` (nullable even when wrapper present) — lib/property_listing.py L40 ✓ |
| Upstream IRS Pub 936 | `qualified_loan_limit(filing_status, has_grandfathered_debt=False, binding_contract_signed_before_2017_12_15=False, binding_contract_closed_before_2018_04_01=False)` — lib/rules/irs_pub936.py L60-69 ✓ |
| Upstream amortize | `Schedule.payments: list[Payment]`; `Payment.interest: Money` — lib/models.py L48-71 ✓ |
