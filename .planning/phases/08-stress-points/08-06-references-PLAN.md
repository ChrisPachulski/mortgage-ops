---
phase: 08
plan: 06
type: execute
wave: 6
depends_on: ["08-00", "08-01", "08-02", "08-03", "08-04", "08-05"]
files_added:
  - references/stress-tests.md
  - references/points-breakeven.md
files_modified: []
autonomous: true
requirements: []
tags:
  - phase-08
  - stress-points
  - documentation
must_haves:
  truths:
    - "references/stress-tests.md exists with sections: Overview, Sweep modes (3 subsections), Output schema (top-table-summary contract for SC-5), Citations, Subagent consumption hint, Glossary"
    - "references/points-breakeven.md exists with sections: Overview, Simple breakeven formula, NPV breakeven formula, Discount-rate disclosure (Phase 6 deferred coupling note), Divergence example (the SC-4 fixture), Citations"
    - "Both reference docs cite at least one regulatory source: stress-tests.md cites CFPB ATR/QM 1026.43(c)(5); points-breakeven.md cites IRS Pub 936 + Reg Z 1026.18"
    - "Both reference docs follow references/arm-mechanics.md style (Phase 5 D-08 [REVISED]) — markdown headers, citation format, length targeting Phase 11 stress-test-agent context budget"
    - "scripts/stress_test.py and scripts/points_breakeven.py --help epilogs cross-reference the doc paths (references/stress-tests.md / references/points-breakeven.md)"
---

<objective>
Ship the two Phase 8 reference docs that Phase 11 (Subagents) and Phase 10 (Skill Frontend) will load on-demand. Both follow references/arm-mechanics.md's section structure and citation discipline.

points-breakeven.md is the authoritative documentation for the Phase 6 cross-phase coupling — explicitly names the deferred discount-rate convention and provides starting-point recommendations until Phase 6 lands.
</objective>

<context>
@.planning/phases/08-stress-points/08-PATTERNS.md (§References section)
@.planning/phases/08-stress-points/08-RESEARCH.md (§5.5, §6.3, §9)
@references/arm-mechanics.md (canonical Phase 5 doc style; lift section structure)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create references/stress-tests.md</name>
  <files>references/stress-tests.md</files>
  <action>
    Create references/stress-tests.md with the following sections (mirrors references/arm-mechanics.md structure):

    # Stress Tests

    ## Overview
    Mortgage-ops stress sweeps are parameter-grid evaluations of the underlying calc engines (Phase 3 amortization, Phase 4 affordability, Phase 5 ARM). Three sweep modes are supported via the `lib.stress.evaluate(req)` dispatcher and `scripts/stress_test.py --mode {rate-shock|income-shock|arm-reset}`:
    - **Rate-shock** (STRS-01): Re-solve monthly P&I for a grid of interest rates against a fixed loan.
    - **Income-shock** (STRS-02): Recompute back-end DTI for a grid of household income reductions; flag rows that breach a configured affordability threshold.
    - **ARM-reset** (STRS-03): Simulate three named index-path scenarios (parallel-shift, gradual-rise, fall-then-rise) over a 30-year horizon; report total interest paid per path.

    Phase 8 invents NO new mathematical primitive — every cell in every grid is a single call into a Phase 3/4/5 engine, then summary-scalar capture.

    ## Sweep Modes

    ### Rate-Shock
    Parameters: a `Loan` (principal + term + origination_date) plus a list of rates. The engine re-builds the schedule per rate via `lib.amortize.build_schedule(loan_with_swapped_rate)`. Output rows carry `monthly_pi`, `total_interest`, and deltas vs the baseline rate.

    Example invocation (ROADMAP SC-1 verbatim):
    `scripts/stress_test.py --mode rate-shock --rates 0.06,0.065,0.07,0.075,0.08 --input request.json`

    ### Income-Shock
    Parameters: a baseline `AffordabilityRequest` plus a list of income reductions and a DTI threshold. The engine scales each applicant's `gross_monthly_income` by `(1 - reduction)` per cell, calls `lib.affordability.evaluate(shocked_request)`, captures `dti_back` and a breach flag.

    Example invocation (ROADMAP SC-2 verbatim):
    `scripts/stress_test.py --mode income-shock --reductions 0.05,0.10,0.20 --input request.json`

    Note on threshold: ATR/QM heuristic is `0.43`. The 43% DTI cap is no longer a Black-letter rule (March 2021 Final Rule replaced it with a price-based test in `lib.rules.atr_qm`), but it remains the industry "comfortable affordability" anchor. Caller must explicitly supply `dti_threshold` — no module default.

    ### ARM-Reset
    Parameters: a baseline `ARMRequest` plus a list of named `RatePath` scenarios. The engine synthesizes an `index_path` covering all reset triggers per path, then calls `lib.arm.build_arm_schedule(syn_request)` per path. Output rows: `total_interest`, `max_payment`, `reset_count`, `highest_rate`.

    Three canonical paths (closed-set per Phase 8 D-01-05):
    - `parallel-shift` — instantaneous rate jump, held for the term horizon
    - `gradual-rise` — steady upward step per reset
    - `fall-then-rise` — recession-then-recovery shape

    ## Output Schema (top-table-summary contract for SC-5)

    `StressResponse` declares `summary` BEFORE `rows` in field-declaration order. Pydantic v2 preserves this order in `model_dump_json`, so the JSON blob always reads:

    ```json
    {
      "mode": "<mode>",
      "scenario_count": N,
      "summary": {
        "table": [<row-shape repeated N times>],
        "baseline_label": "...",
        "worst_case_label": "...",
        "stress_invariant_violations": []
      },
      "rows": [<full-detail rows>]
    }
    ```

    Size budget: under 100KB for sweeps up to 50 scenarios. The summary table is < 30 lines for any practical sweep size; subagents read the summary block first and decide whether to drill into rows.

    Stress invariants surfaced as `summary.stress_invariant_violations: list[str]`:
    | Code | Mode | Meaning |
    |---|---|---|
    | `RATE_SHOCK_MONOTONE_PI` | rate-shock | monthly_pi did NOT strictly increase as rate strictly increased — Phase 3 engine bug signal |

    Empty list = happy path. Future Phase 11+ test-coverage expansions will add income-shock and arm-reset invariants.

    ## Subagent Consumption Hint (Phase 11 contract)

    When Phase 11 ships `stress-test-agent` (Haiku, 1k token return budget), its system prompt should include:
    > "Read the `summary.table` block first. Each row is one scenario. The `worst_case_label` field names the most stressed scenario. The `stress_invariant_violations` field, if non-empty, lists physics-of-amortization violations (e.g., monthly_pi went DOWN as rate went UP — would indicate an engine bug). If empty, narrate the table directly. Only drill into `rows` if the user asks for per-scenario detail."

    Phase 11 lifts this paragraph verbatim into `.claude/agents/stress-test-agent.md`.

    ## Citations
    - **CFPB ATR/QM rule, 12 CFR 1026.43(c)(5)** — Max-payment stress test mandate for ARM products. The `arm-reset` sweep enables this calculation; per-row `max_payment` field surfaces the worst-case payment.
    - **CFPB Stress Test Guidance** (post-2008 commentary) — Rate-shock sweeps are the regulatory-blessed framework for evaluating borrower resilience.
    - **March 2021 General QM Final Rule** — Replaced the 43% DTI cap with a price-based test (lib/rules/atr_qm.py); the 0.43 threshold here is heuristic only.

    ## Glossary
    - **Rate shock** — interest-rate parameter sweep
    - **Payment shock** — the resulting payment delta when a rate shock or ARM reset occurs
    - **Income shock** — household-income reduction sweep
    - **Stressed DTI** — DTI computed under one of the shocks
    - **Path** (ARM-reset) — one of the three named index-trajectory scenarios
  </action>
  <acceptance_criteria>
    - File references/stress-tests.md exists
    - `grep -c "^## Overview" references/stress-tests.md` returns 1
    - `grep -c "^## Sweep Modes" references/stress-tests.md` returns 1
    - `grep -c "^## Output Schema" references/stress-tests.md` returns 1
    - `grep -c "^## Subagent Consumption Hint" references/stress-tests.md` returns 1
    - `grep -c "^## Citations" references/stress-tests.md` returns 1
    - `grep -c "1026.43(c)(5)" references/stress-tests.md` returns ≥1
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Create references/points-breakeven.md</name>
  <files>references/points-breakeven.md</files>
  <action>
    Create references/points-breakeven.md:

    # Discount-Points Breakeven

    ## Overview
    Discount points let borrowers pay an upfront premium (typically 1% of loan amount per "point") in exchange for a lower interest rate. The breakeven question — "at what month does the rate savings recoup the upfront cost?" — has two valid framings, both reported side-by-side by `lib.points.evaluate(req)` and `scripts/points_breakeven.py`:

    1. **Simple breakeven** (PNTS-01): `ceil(points_cost / monthly_savings)` — ignores time value of money.
    2. **NPV breakeven** (PNTS-02): The first month where cumulative discounted savings exceed the upfront cost, given a borrower-perspective discount rate.

    Per ROADMAP SC-4, the two outputs disagree only when discount factors materially differ — a divergence-pin fixture (`tests/fixtures/points/points_simple_lt_npv_seven_pct_discount.json`) documents the canonical 37-month gap at a 7% discount rate.

    ## Simple Breakeven Formula

    ```
    months_to_breakeven = ceil(points_cost / monthly_savings)
    ```

    Returns `None` when `monthly_savings <= 0` (rate-up scenario; points cost MORE than they save). Caller-surfaced as a warning in `PointsResponse.warnings`.

    ## NPV Breakeven Formula

    Cumulative NPV at month m:
    ```
    cum_npv(m) = sum_{k=1..m} (monthly_savings / (1 + r_monthly)^k) - points_cost
    where r_monthly = discount_rate_annual / 12
    ```

    The engine walks month-by-month from 1 to `hold_period_months` and returns the first m where `cum_npv(m) >= 0`. If never crosses within hold, returns `None`.

    Discount rate of `0` collapses NPV to simple breakeven (no time-value adjustment) — verified by the `points_simple_eq_npv_zero_discount.json` fixture.

    ## Discount-Rate Convention (Phase 6 deferred coupling)

    The borrower-perspective discount rate represents the borrower's opportunity cost: the alternative return they'd earn by NOT paying the points cost upfront. Phase 6 (Refinance NPV) will pin a project-wide convention. Until then, callers MUST explicitly choose — `discount_rate_annual` is REQUIRED on `PointsRequest` (no default).

    Recommended starting points until Phase 6 lands:
    - **Zero (0.000000)** — No opportunity cost; collapses NPV to simple breakeven. Use when the alternative is "money sits in checking".
    - **Loan annual rate** — Paying-down-debt opportunity. Use when the alternative is "make extra principal payments on this loan".
    - **0.050000** — Rough US 10-year Treasury proxy. Use when the alternative is "buy bonds".

    When Phase 6 lands, this section will be updated and `lib.points.PointsRequest.discount_rate_annual` will gain an additive non-breaking default. Existing callers (and existing fixtures) will continue to work.

    ## Decision Dispatcher

    `PointsResponse.decision` is `"buy_points"` iff `cum_npv(hold_period_months) >= 0`; `"skip_points"` otherwise. If `simple_breakeven_months is None` (negative savings), decision is forced to `"skip_points"`.

    ## Divergence Example (ROADMAP SC-4 pin)

    Loan: $400k / 30yr. Without points: 6.50% → monthly_pi = $2528.27. With 2 points (cost $8000): 6.25% → monthly_pi = $2462.87. monthly_savings = $65.40.

    | Discount rate | Simple breakeven | NPV breakeven | Diverge | Gap |
    |---|---|---|---|---|
    | 0.00% | 123 months | 123 months | False | 0 |
    | 7.00% | 123 months | 160 months | True  | 37 months |

    Borrowers with hold horizons in the 10-13 year range face a meaningful decision: simple breakeven says "buy" by year 11, NPV says "buy only if you'll hold past year 14". This is the SC-4 contract closure.

    ## Citations
    - **IRS Publication 936** (Home Mortgage Interest Deduction) — Points are deductible per the rules in `data/reference/irs-pub936.yml`. Discount points (origination points) get separate treatment from loan-origination fees.
    - **Regulation Z, 12 CFR 1026.18** — Disclosure rules for discount points on the Loan Estimate. Reg Z requires lenders to disclose the upfront cost in the "Origination Charges" section.
    - **CFPB Consumer Resources** — "What are discount points?" — borrower-facing explanation of the rate-vs-cost tradeoff.

    ## Glossary
    - **Point** — 1% of loan amount paid upfront in exchange for a lower interest rate.
    - **Discount rate** (in NPV context) — the borrower's opportunity cost; the rate of return on the alternative use of the upfront cash.
    - **Hold period** — the number of months the borrower expects to hold the loan before selling, refinancing, or paying off.
    - **Breakeven** — the month at which cumulative savings equal upfront cost. Reported in two flavors (simple, NPV) by this engine.
  </action>
  <acceptance_criteria>
    - File references/points-breakeven.md exists
    - `grep -c "^## Overview" references/points-breakeven.md` returns 1
    - `grep -c "^## Simple Breakeven Formula" references/points-breakeven.md` returns 1
    - `grep -c "^## NPV Breakeven Formula" references/points-breakeven.md` returns 1
    - `grep -c "^## Discount-Rate Convention" references/points-breakeven.md` returns 1
    - `grep -c "^## Divergence Example" references/points-breakeven.md` returns 1
    - `grep -c "^## Citations" references/points-breakeven.md` returns 1
    - `grep -c "Phase 6" references/points-breakeven.md` returns ≥2 (deferred coupling note)
    - `grep -c "1026.18" references/points-breakeven.md` returns ≥1
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Cross-reference doc paths from CLI --help epilogs (optional polish)</name>
  <files>scripts/stress_test.py, scripts/points_breakeven.py</files>
  <action>
    Add a final line to each CLI's --help epilog text:

    `scripts/stress_test.py` epilog gets appended:
    `"See references/stress-tests.md for sweep mechanics, output-schema details, and Phase 11 subagent consumption contract."`

    `scripts/points_breakeven.py` epilog gets appended:
    `"See references/points-breakeven.md for formula details, discount-rate guidance, and the SC-4 divergence example."`
  </action>
  <acceptance_criteria>
    - `python scripts/stress_test.py --help 2>&1 | grep -c "references/stress-tests.md"` returns 1
    - `python scripts/points_breakeven.py --help 2>&1 | grep -c "references/points-breakeven.md"` returns 1
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-06-01: references/stress-tests.md and references/points-breakeven.md follow the references/arm-mechanics.md (Phase 5 D-08 [REVISED]) section-structure convention. Markdown headers, citation discipline, length budget (target ~150-300 lines per doc to fit Phase 11 subagent context budget).
- D-06-02: points-breakeven.md is the AUTHORITATIVE documentation for the Phase 6 deferred discount-rate coupling. The "## Discount-Rate Convention (Phase 6 deferred coupling)" section spells out the contract: caller-supplied today; additive non-breaking default once Phase 6 lands. Phase 6 planner WILL edit this section when shipping its convention.
- D-06-03: Both docs cite real regulatory sources (CFPB / IRS / Reg Z) — no fabricated citations. The 1026.43(c)(5) and 1026.18 citations match `lib/rules/atr_qm.py` and `lib/rules/reg_z.py` respectively (verified during Plan 08-06 authoring).
- D-06-04: The "subagent consumption hint" paragraph in stress-tests.md is the LITERAL text Phase 11 will lift into `.claude/agents/stress-test-agent.md` (per 08-RESEARCH §6.3). Cross-phase contract.
- D-06-05: SC-4 divergence example fixture-pin (123 simple / 160 NPV at 7%) is reproduced in the table in points-breakeven.md. If Plan 08-05 fixture math drifts, this section drifts with it.
</locked_decisions>

<verify_block>
- Both reference docs exist with all required sections
- Citations include CFPB / IRS / Reg Z (real-world references)
- Phase 6 deferred coupling explicitly documented in points-breakeven.md
- CLI --help epilogs cross-reference the doc paths
- markdown formatting clean (no broken headers, code-fence balance)
</verify_block>

<deviation_rules>
- Rule 1: If markdown linting (e.g., markdownlint via pre-commit) flags structural issues, fix them and document in SUMMARY.md.
- Rule 2: If the "subagent consumption hint" paragraph is overly long for Phase 11's 1k-token return budget, trim — the verbatim-lift contract (D-06-04) is structural, not byte-exact.
</deviation_rules>

<success_criteria>
- 2 reference docs shipped under references/
- Phase 6 cross-phase coupling DOCUMENTED in points-breakeven.md (resolves the deferred-coupling doc gap)
- Phase 11 subagent consumption contract DOCUMENTED in stress-tests.md (verbatim-lift target)
- CLI --help epilogs cross-reference the docs
- No regulatory-citation fabrication (every citation traces to a real CFPB / IRS / Reg Z section)
</success_criteria>
