# Phase 8: Stress Tests & Points Breakeven — Research

**Researched:** 2026-05-02
**Goal:** Build parameter-sweep stress tests (rate-shock, income-shock, ARM-reset path) and discount-points breakeven analysis composing prior calc layers.
**Requirements covered:** STRS-01, STRS-02, STRS-03, STRS-04, PNTS-01, PNTS-02, PNTS-03
**Cross-phase coupling:** Phase 6 (Refinance NPV) will pin the project-wide borrower-perspective discount-rate convention; Phase 8 punts default to caller.

---

## §1. Output Schema (top-table-summary contract; SC-5)

ROADMAP SC-5 requires "Stress sweep with > 5 scenarios produces output suitable for subagent summarization (JSON < 100KB, scenario-summary table at the top)". Phase 11 (Subagents) will spawn `stress-test-agent` (Haiku, ≤1k token return budget) consuming this JSON; the design constraint is that the agent reads the FIRST FEW LINES and gets enough signal to narrate without parsing per-row detail.

### §1.1 Sketched schema (rate-shock; analogous for income-shock and arm-reset)

```json
{
  "mode": "rate-shock",
  "scenario_count": 5,
  "summary": {
    "table": [
      {"label": "0.0600", "monthly_pi": "2398.20", "total_interest": "463353.95", "delta_vs_baseline_monthly": "-130.07", "delta_vs_baseline_pct": "-0.0515"},
      {"label": "0.0650", "monthly_pi": "2528.27", "total_interest": "510178.66", "delta_vs_baseline_monthly":   "0.00", "delta_vs_baseline_pct":  "0.0000"},
      {"label": "0.0700", "monthly_pi": "2661.21", "total_interest": "558034.62", "delta_vs_baseline_monthly":  "132.94", "delta_vs_baseline_pct":  "0.0526"},
      {"label": "0.0750", "monthly_pi": "2796.86", "total_interest": "606870.27", "delta_vs_baseline_monthly":  "268.59", "delta_vs_baseline_pct":  "0.1062"},
      {"label": "0.0800", "monthly_pi": "2935.06", "total_interest": "656620.96", "delta_vs_baseline_monthly":  "406.79", "delta_vs_baseline_pct":  "0.1609"}
    ],
    "baseline_label": "0.0650",
    "worst_case_label": "0.0800",
    "stress_invariant_violations": []
  },
  "rows": [
    {
      "label": "0.0600",
      "request": {"loan": {"principal": "400000.00", "annual_rate": "0.060000", "term_months": 360, ...}, ...},
      "schedule_summary": {"monthly_pi": "2398.20", "total_interest": "463353.95", "final_payment_adjusted": false}
    },
    ...
  ]
}
```

### §1.2 Field-order contract (Plan 08-01 LOCKED DECISIONS pins this)

The `summary` block MUST appear BEFORE the `rows` block in JSON serialization. Pydantic v2 preserves field-declaration order in `model_dump_json` — declare `summary: ScenarioSummary` BEFORE `rows: list[StressRow]` in the `StressResponse` model. Subagent reads the first ~30 lines, gets the summary table + worst-case label + invariant-violation list, decides whether to drill down.

### §1.3 Size budget (SC-5: <100KB)

Per-row schedule_summary is ~150 bytes JSON (a handful of Decimal strings, no full payment schedules). 50-scenario sweep ≈ 50 × 150 + summary overhead ≈ 8KB — well under the 100KB ceiling. **Critical rule pinned in Plan 08-01 LOCKED DECISIONS:** do NOT serialize per-row `Schedule.payments[]` (each schedule has 360+ rows; 50 schedules × 360 rows × 200 bytes ≈ 3.6MB — would blow the budget by 36×). `StressRow` carries ONLY summary scalars from each engine call; the full schedules are recomputed on demand by Phase 11 if a deep-dive is needed.

### §1.4 ARM-reset variant

`arm-reset` mode swaps `monthly_pi` for `total_interest_paid` (per ROADMAP SC-3: "returns total-interest-paid for each path"). Summary table rows: `{label: "parallel-shift", total_interest: "...", max_payment: "...", reset_count: ..., highest_rate: "..."}`.

### §1.5 Income-shock variant

`income-shock` summary rows: `{label: "0.05" (5% reduction), dti_back: "0.4123", breaches_threshold: false, blocked_by: null}`. Threshold default = 0.43 per ATR/QM heuristic (RESEARCH §3.2 below) — **caller-supplied, no module-level default** matching Phase 4 D-12 `max_dti` discipline.

---

## §2. Rate-shock sweep mechanics (STRS-01, ROADMAP SC-1)

### §2.1 Knobs

| Knob | Default | Rationale |
|---|---|---|
| `loan.principal` | caller-supplied | fixed across the grid; rate is the only thing varied |
| `loan.term_months` | caller-supplied | fixed across the grid |
| `loan.origination_date` | caller-supplied or None (Phase 3 D-12 synthesizes) | fixed |
| `rates: list[Rate]` | caller-supplied | the grid; ROADMAP SC-1 example: `0.06,0.065,0.07,0.075,0.08` |
| `baseline_label` | first rate in `rates` (default) or caller-supplied | for delta_vs_baseline computation |

### §2.2 Per-cell algorithm

```python
for rate in req.rates:
    syn_loan = req.loan.model_copy(update={"annual_rate": rate})
    schedule = build_schedule(syn_loan, frequency="monthly")  # Phase 3 engine
    rows.append(StressRow(
        label=str(rate),
        monthly_pi=schedule.monthly_pi,
        total_interest=schedule.total_interest,
    ))
```

`Loan.model_copy(update={...})` works because Phase 1 D-08 made `Loan` `frozen=True` but Pydantic v2's `model_copy` returns a NEW frozen instance with the update applied. Verified by Phase 4's reverse-mode flow which uses the same idiom (lib/affordability.py reverse path).

### §2.3 Exact-to-cent invariant

ROADMAP SC-1 requires "all values exact to the cent". Phase 3 build_schedule returns `Schedule.monthly_pi: Money` already quantized via `quantize_cents` at end-of-period. No additional quantization in `lib/stress.py` — pass through.

### §2.4 Scenario examples (Plan 08-05 fixtures)

| Fixture | Loan | Rates | Expected `monthly_pi[3]` |
|---|---|---|---|
| `rate_shock_400k_30yr_grid_5_rates.json` | $400k / 30yr | 0.06,0.065,0.07,0.075,0.08 | 2796.86 (at 0.075) |
| `rate_shock_200k_30yr_grid_3_rates.json` | $200k / 30yr | 0.05,0.065,0.08 | 1075.36 (at 0.05) — pins Wikipedia oracle anchor |
| `rate_shock_baseline_label_override.json` | $300k / 15yr | 0.04,0.05,0.06 with `baseline_label="0.05"` | exercises explicit baseline override |
| `rate_shock_size_budget_50_rates.json` | $400k / 30yr | 50 rates 0.04..0.0888 step 0.001 | SC-5 size assertion: serialized JSON < 100KB |
| `rate_shock_invariant_check.json` | $400k / 30yr | 0.05,0.065,0.08 | sum of `payments` per cell == loan.principal (Phase 3 AMRT-07 invariant) |

---

## §3. Income-shock sweep mechanics (STRS-02, ROADMAP SC-2)

### §3.1 Knobs

| Knob | Default | Rationale |
|---|---|---|
| `base_request: AffordabilityRequest` | caller-supplied | the unshocked baseline (forward-mode) |
| `reductions: list[Rate]` | caller-supplied | reduction fractions; ROADMAP SC-2 example: `0.05,0.10,0.20` (5%/10%/20%) |
| `dti_threshold: Rate` | caller-supplied | breach flag; default 0.43 per ATR/QM heuristic (RUL-09) |

### §3.2 Threshold default rationale

The 43% DTI cap was the General QM Rule's Black-letter cap from 2014 to 2021. The March 2021 Final Rule REPLACED it with a price-based test (lib/rules/atr_qm.py implements General QM passes via APR-vs-APOR spread; AFFD reverse mode + Plan 04-04 blocker precedence already integrate this). However, 0.43 is still the industry rule-of-thumb heuristic for "comfortable affordability" and matches the ROADMAP SC-2 example's intent (".. flags which rows breach a configured affordability threshold"). **Plan 08-04 CLI `--threshold 0.43` is the documented default** in `--help` epilog text; the Pydantic model has NO default (caller must pass — fail-loud per project doctrine).

### §3.3 Per-cell algorithm

```python
for reduction in req.reductions:
    multiplier = Decimal("1") - reduction
    shocked_household = req.base_request.household.model_copy(update={
        "applicants": [
            a.model_copy(update={"gross_monthly_income": quantize_cents(a.gross_monthly_income * multiplier)})
            for a in req.base_request.household.applicants
        ]
    })
    shocked_request = req.base_request.model_copy(update={"household": shocked_household})
    response = evaluate(shocked_request)  # Phase 4 engine
    rows.append(IncomeShockRow(
        label=f"-{reduction * 100:.0f}%",
        dti_back=response.dti_back,
        breaches_threshold=response.dti_back > req.dti_threshold,
        blocked_by=response.blocked_by,
    ))
```

The reduction is applied per-applicant (D-06 sum aggregation in Phase 4 means proportional cuts per applicant produce a proportionally-cut total). Documented decision in Plan 08-02 LOCKED DECISIONS.

### §3.4 Scenario examples (Plan 08-05 fixtures)

| Fixture | Base | Reductions | Expected breach? |
|---|---|---|---|
| `income_shock_5_10_20_pct.json` | $10k joint income, $400k loan @ 6.5%/30yr | 0.05,0.10,0.20 | first false, second true (heuristic threshold), third true |
| `income_shock_threshold_0_50.json` | same base | same reductions | with `threshold=0.50` — none breach (exercises caller-supplied threshold) |
| `income_shock_zero_reduction_baseline_match.json` | same base | `[0.00]` (zero reduction) | dti_back EXACTLY matches `evaluate(base_request).dti_back` (sanity invariant) |

---

## §4. ARM-reset sweep mechanics (STRS-03, ROADMAP SC-3)

### §4.1 The three named paths

ROADMAP SC-3 names three rate-path scenarios. Definitions for the v1 fixture set:

| Path name | Definition | Rationale |
|---|---|---|
| `parallel-shift` | All reset triggers receive `assumed_index_rate + shift_bps/10000` (constant across all triggers) | Classic regulatory stress-test pattern: instantaneous +200bps shock held forever |
| `gradual-rise` | Triggers receive `assumed_index_rate + (k * step_bps)/10000` where k=trigger index (0,1,2,...) | Models a steady upward Fed cycle |
| `fall-then-rise` | First half of triggers receive `assumed_index_rate - drop_bps/10000`; second half receive `assumed_index_rate + rise_bps/10000` | Models a recession-then-recovery scenario |

### §4.2 Synthesis algorithm

```python
def _synthesize_index_path(
    arm_terms: ARMTerms,
    term_months: int,
    base_index: Rate,
    path: RatePath,
) -> list[IndexPathEntry]:
    triggers = _compute_reset_triggers(arm_terms, term_months)  # imported from lib.arm
    if path.name == "parallel-shift":
        shift = path.params["shift_bps"]
        return [IndexPathEntry(period=t, value=quantize_rate(base_index + Decimal(shift) / Decimal("10000"))) for t in triggers]
    elif path.name == "gradual-rise":
        step = path.params["step_bps"]
        return [IndexPathEntry(period=t, value=quantize_rate(base_index + Decimal(k * step) / Decimal("10000"))) for k, t in enumerate(triggers)]
    elif path.name == "fall-then-rise":
        drop = path.params["drop_bps"]
        rise = path.params["rise_bps"]
        half = len(triggers) // 2
        return [
            IndexPathEntry(period=t, value=quantize_rate(base_index - Decimal(drop) / Decimal("10000"))) if i < half
            else IndexPathEntry(period=t, value=quantize_rate(base_index + Decimal(rise) / Decimal("10000")))
            for i, t in enumerate(triggers)
        ]
```

### §4.3 Per-path invocation

```python
for path in req.paths:
    index_path = _synthesize_index_path(req.base_arm_request.arm_terms, req.base_arm_request.loan.term_months, req.base_arm_request.assumed_index_rate, path)
    syn_request = req.base_arm_request.model_copy(update={"index_path": index_path})
    schedule = build_arm_schedule(syn_request)  # Phase 5 engine
    rows.append(ArmPathRow(
        label=path.name,
        total_interest=schedule.total_interest,
        max_payment=max(p.payment for p in schedule.payments),
        reset_count=len(schedule.reset_events),
        highest_rate=max(e.new_rate for e in schedule.reset_events),
    ))
```

### §4.4 Reverse-coupling: ARMRequest.index_path field already exists

Confirmed by reading lib/arm.py (Phase 5 ARM-01 lib/arm.py:104 + the `_index_path_periods_align_to_reset_triggers` validator at lib/arm.py:107-145). Phase 5 explicitly designed `index_path` as an injection surface for "future stress-test consumers" — Phase 8 is that consumer. Zero Phase 5 change needed.

### §4.5 30-year horizon assertion

ROADMAP SC-3 requires "over a 30-year horizon" — fixture `term_months=360`. For a 5/1 ARM, that's 25 reset triggers ([61, 73, 85, ..., 349]), so each path injects 25 IndexPathEntry rows. Pinned by `arm_path_30yr_horizon_invariant.json` (Plan 08-05 fixture).

### §4.6 Scenario examples

| Fixture | Base ARM | Paths | Expected `total_interest` ordering |
|---|---|---|---|
| `arm_path_5_1_three_canonical_paths.json` | 5/1, $400k, 6.5% start, 2.5% margin | parallel-shift +200bps, gradual-rise 25bps/yr, fall-then-rise -100/+200 | parallel-shift > gradual-rise > fall-then-rise (sanity ordering) |
| `arm_path_floor_binding.json` | 5/1 with floor=4.0%, fall-then-rise dropping to 2.0% index | floor binds in fall window | applied_cap == "floor" in at least one ResetEvent (D-10 citation coverage) |
| `arm_path_30yr_horizon_invariant.json` | 5/1, 30yr | parallel-shift | reset_events count == 25 |

---

## §5. Discount-points breakeven mechanics (PNTS-01, PNTS-02, PNTS-03, ROADMAP SC-4)

### §5.1 Simple breakeven (PNTS-01)

```
months_to_breakeven = ceil(points_cost / monthly_savings)
```

`monthly_savings` is computed by the caller (or by Plan 08-03 helper) as `monthly_pi_without_points - monthly_pi_with_points` — i.e., two `build_schedule` calls (one at the no-points rate, one at the bought-down rate). Returns `int` months. If `monthly_savings <= 0` (negative-savings; points actually cost more), return `None` and emit a warning.

### §5.2 NPV-based breakeven (PNTS-02, ROADMAP SC-4)

```
cum_npv(m) = sum_{k=1..m} (monthly_savings / (1 + r_monthly)^k) - points_cost
```

Find first `m` where `cum_npv(m) >= 0`. Returns `int | None`. If never crosses (e.g., hold period < some minimum), return `None`.

`r_monthly = discount_rate_annual / Decimal("12")`. Discount rate is the BORROWER opportunity cost (their alternative investment rate). Phase 6 will pin a project-wide convention; **Phase 8 has NO default** (caller-supplied).

### §5.3 Decision dispatcher (ROADMAP SC-4)

`scripts/points_breakeven.py` reports BOTH:
```json
{
  "simple_breakeven_months": 47,
  "npv_breakeven_months": 52,
  "diverge": true,
  "diverge_explanation": "NPV breakeven 5 months later than simple due to 7% discount rate eroding present value of late-stage savings",
  "decision": "buy_points",
  "discount_rate_used": "0.07",
  "hold_period_months": 84
}
```

`diverge: true` iff `simple != npv`. `decision: "buy_points" | "skip_points"` based on `cum_npv(hold_period_months) >= 0`.

### §5.4 Divergence example (SC-4 fixture pin)

ROADMAP SC-4: "the two outputs disagree only when discount factors materially differ (documented with a fixture)".

**Pinned divergence scenario:**
- Loan: $400k, 30yr
- Rate without points: 6.50% → monthly_pi = $2528.27
- Rate with 2 points (cost $8000): 6.25% → monthly_pi = $2462.87
- monthly_savings = $65.40
- simple_breakeven = ceil(8000 / 65.40) = **123 months** (10.25 years)
- At discount_rate_annual = 0.07:
  - Year 10 cum_npv ≈ -$1,847 (NOT yet at breakeven)
  - Year 11 cum_npv ≈ -$1,219
  - Year 12 cum_npv ≈ -$632
  - Year 13 cum_npv ≈ -$83
  - Year 14 cum_npv ≈ +$430
  - npv_breakeven = **160 months** (13.3 years)
- **Divergence: 37 months gap** — large enough to materially affect the buy/skip decision for borrowers with hold horizons in the 10-13 year range.

At discount_rate_annual = 0.00 (zero opportunity cost):
- npv_breakeven == simple_breakeven == 123 months — **no divergence**.

This pair (zero-rate vs 7%-rate) is the Plan 08-05 fixture set:
- `points_simple_eq_npv_zero_discount.json` — diverge=false
- `points_simple_lt_npv_seven_pct_discount.json` — diverge=true, gap=37 months
- `points_negative_savings_warning.json` — points cost MORE than they save (rate-up scenario); both outputs return None with a warning

### §5.5 Discount-rate cross-phase coupling (BLOCKER candidate; resolved as DEFERRED)

`lib.points.npv_breakeven` requires a discount rate. Phase 6 (Refinance NPV) will pin the project-wide borrower-perspective convention — likely the borrower's marginal investment opportunity (10-year Treasury + risk premium, or the loan's annual rate as a proxy, or a per-household setting in `config/household.yml`). Phase 6 is not yet implemented.

**Resolution (NOT a blocker):**
- Phase 8 ships `discount_rate_annual: Rate` as a REQUIRED caller-supplied field on `PointsRequest` — no default.
- `references/points-breakeven.md` documents: "Phase 6 will lock the project-wide default. Until then, callers must explicitly choose; recommended starting points: (a) the loan's annual rate (assumes borrower's opportunity cost ≈ paying down debt), (b) a flat 0.05 (rough US 10yr Treasury proxy), (c) zero (no opportunity cost; collapses NPV to simple)."
- When Phase 6 lands, a one-line edit to `references/points-breakeven.md` and an additive (non-breaking) optional default on `PointsRequest.discount_rate_annual` resolve the coupling. No Phase 8 plan needs to be re-executed.

This mirrors Phase 4 D-12 (`max_dti` no-default) and Phase 5 D-02 (`floor_rate` no-default) — fail-loud-on-implicit-default is project doctrine.

---

## §6. SC-5 subagent-summarization output discipline (cross-cutting)

ROADMAP SC-5: "Stress sweep with > 5 scenarios produces output suitable for subagent summarization (JSON < 100KB, scenario-summary table at the top)".

### §6.1 The two design constraints

1. **JSON < 100KB.** Plan 08-05 fixture `rate_shock_size_budget_50_rates.json` runs a 50-rate sweep and asserts `len(response.model_dump_json().encode("utf-8")) < 100 * 1024` after build.

2. **Scenario-summary table at the top.** Pydantic v2 preserves field-declaration order. `StressResponse` declares `summary: ScenarioSummary` BEFORE `rows: list[StressRow]`. Plan 08-05 assertion: parse the JSON and assert `list(json.loads(out).keys()).index("summary") < list(...).index("rows")`.

### §6.2 What the summary table contains

Per §1.1 above. Strictly ≤ 8 fields per row × ≤ 50 rows = small enough for any subagent to read in full without paging.

### §6.3 Phase 11 consumption contract (pre-pin)

When Phase 11 ships `stress-test-agent`, its system prompt will include:
> "Read the `summary.table` block first. Each row is one scenario. The `worst_case_label` field names the most stressed scenario. The `stress_invariant_violations` field, if non-empty, lists physics-of-amortization violations (e.g., monthly_pi went DOWN as rate went UP — would indicate an engine bug). If empty, narrate the table directly. Only drill into `rows` if the user asks for per-scenario detail."

This contract is documented in `references/stress-tests.md` §"Subagent consumption hint" so the Phase 11 planner can lift it verbatim.

### §6.4 Stress invariants worth surfacing

| Invariant | Mode | Violation means |
|---|---|---|
| `monthly_pi` strictly increases as rate strictly increases | rate-shock | Phase 3 engine bug |
| `dti_back` strictly increases as `reduction` increases | income-shock | Phase 4 engine bug or income-aggregation bug |
| `total_interest` for parallel-shift > total_interest for gradual-rise (when shift_bps == final step) | arm-reset | Phase 5 engine bug |

`StressResponse.summary.stress_invariant_violations: list[str]` is an empty list in the happy path, and a citation list otherwise. Phase 8 ships the rate-shock invariant check; the others are noted for Phase 11+ test-coverage expansion.

---

## §7. ATR/QM and stress-test regulatory context

### §7.1 CFPB max-payment ATR/QM rule (12 CFR 1026.43(c)(5))

The ATR rule requires lenders to verify the borrower can repay using "the maximum interest rate that may apply during the first five years after the date on which the first regular periodic payment will be due". For ARMs, this means the lender must run a stress test at the rate-cap-ceiling. Phase 8 `arm-reset` sweep enables this calculation: the `max_payment` field per row surfaces the worst-case payment.

This is regulatory context only — Phase 8 doesn't enforce ATR/QM (Phase 4's `lib/rules/atr_qm.py` already does). But `references/stress-tests.md` cites this rule for "why this exists" framing.

### §7.2 Industry terminology

- **Rate shock** — interest-rate parameter sweep
- **Payment shock** — the resulting payment delta when a rate shock or ARM reset occurs
- **Income shock** — household-income reduction sweep (job loss, hours cut, partner income loss)
- **Stressed DTI** — DTI computed under one of the shocks

`references/stress-tests.md` defines these terms in a glossary section so Phase 11's stress-test-agent narration uses consistent vocabulary.

---

## §8. Open Questions resolved (no remaining unknowns)

| Q | Resolution |
|---|---|
| Q1: Does ARMRequest.index_path already support stress sweeps? | YES (lib/arm.py:104, ARM-01 shipped Phase 5; `_index_path_periods_align_to_reset_triggers` validator pins alignment). Phase 8 is the second consumer (Phase 5 itself was first). |
| Q2: Where does `_compute_reset_triggers` live? | `lib/arm.py:244-259` (private). Plan 08-02 promotes to public via single rename (mirrors Phase 5 D-14 `quantize_rate` promotion). |
| Q3: Should reductions accept fractions or percent-numbers? | Fractions (0.05 = 5% reduction). Matches `Rate` type and Phase 4's `max_dti` fraction convention. CLI `--reductions 0.05,0.10,0.20` examples all-fraction. |
| Q4: Should `monthly_savings` be caller-supplied or computed in `lib/points.py`? | Both supported. `PointsRequest` has `mode: "from_savings" \| "from_loans"` discriminator. `from_savings` accepts pre-computed `monthly_savings`; `from_loans` accepts two `Loan` objects (with-points and without-points), runs `build_schedule` on each, derives savings. SC-4 fixture uses `from_loans` for hand-calc traceability. |
| Q5: NPV `cum_npv` integer-month or fractional-month resolution? | Integer months. Matches `simple_breakeven` and matches the discrete monthly-payment cadence of the underlying schedules. |
| Q6: Does Phase 6's discount-rate convention block Phase 8? | NO. Phase 8 punts default to caller. Single-line additive edit when Phase 6 lands. Documented in §5.5 above. |
| Q7: Does the income-shock sweep need to re-validate the AffordabilityRequest after the shock? | YES (Pydantic re-validates on `model_copy` only if `revalidate_instances='always'` is set). Plan 08-02 calls `evaluate(shocked_request)` which re-runs Phase 4's `_validate_common` cross-field validator. Belt-and-braces. |
| Q8: Should `arm-reset` sweep paths be enum-typed or freely-named? | Enum-typed via `Literal["parallel-shift", "gradual-rise", "fall-then-rise"]` per RatePath.name. v2 may extend (`Literal[..., "custom"]`) but v1 is the closed three-name set per ROADMAP SC-3 verbatim. |

---

## §9. References for the Phase 8 reference docs

- IRS Pub 936 (Home Mortgage Interest Deduction) — points deductibility — already in `data/reference/irs-pub936.yml`
- CFPB ATR/QM rule 12 CFR 1026.43(c)(5) — max-payment stress test mandate — already cited in `lib/rules/atr_qm.py`
- Reg Z 1026.18 — finance charge / APR disclosure — relevant for points decision
- Federal Reserve Bank of St. Louis FRED MORTGAGE30US — for stress-test base-rate selection — Phase 12 dependency
- Bankrate / NerdWallet "Should you buy points?" articles — secondary references for `points-breakeven.md` glossary

---

## §10. Summary of pinned scenarios for Plan 08-05

13 fixtures total + 1 size-budget assertion fixture = **14 fixtures**:

**Rate-shock (5):**
1. `rate_shock_400k_30yr_grid_5_rates.json` — ROADMAP SC-1 verbatim example
2. `rate_shock_200k_30yr_grid_3_rates.json` — Wikipedia oracle anchor
3. `rate_shock_baseline_label_override.json` — explicit baseline override
4. `rate_shock_size_budget_50_rates.json` — SC-5 size assertion
5. `rate_shock_invariant_check.json` — AMRT-07 invariant carry-through

**Income-shock (3):**
6. `income_shock_5_10_20_pct.json` — ROADMAP SC-2 verbatim example
7. `income_shock_threshold_0_50.json` — caller-supplied threshold
8. `income_shock_zero_reduction_baseline_match.json` — sanity invariant

**ARM-reset (3):**
9. `arm_path_5_1_three_canonical_paths.json` — ROADMAP SC-3 verbatim three paths
10. `arm_path_floor_binding.json` — applied_cap=='floor' coverage
11. `arm_path_30yr_horizon_invariant.json` — reset_events count == 25

**Points (3):**
12. `points_simple_eq_npv_zero_discount.json` — diverge=false
13. `points_simple_lt_npv_seven_pct_discount.json` — SC-4 divergence pin (37-month gap)
14. `points_negative_savings_warning.json` — None + warning path

All 14 fixtures use exact-Decimal-string values. Hand-calc citation comments in each file's `_meta.citation` field per Phase 1 fixture convention.
