# Stress Tests — mortgage-ops Phase 8 Reference

This document records the conventions implemented by `lib/stress.py`
(Phase 8 stress-sweep dispatcher) and pairs each convention with its
regulatory citation. All section numbers and URLs were verified on
2026-05-03 against the live eCFR + CFPB explainer (per `08-RESEARCH.md`
§Citations and §6.3).

Cited from:
- `lib.stress` module docstring (D-08-06-01 cite-from contract;
  mirrors `lib.apr` D-29 idiom)
- `scripts/stress_test.py --help` epilog (per Plan 08-06 Task 3 cross-reference)
- ROADMAP § Phase 8 SC-5 (subagent consumption contract)

This file is the headline reference for the Phase 8 stress-test
conventions; the six numbered sections below are the load-bearing
surfaces every downstream consumer (Phase 10 Claude skill, Phase 11
`stress-test-agent`, future evals) reads. Phase 11 lifts the
"Subagent Consumption Hint" paragraph (§4) verbatim into
`.claude/agents/stress-test-agent.md` per locked decision D-06-04.

---

## Overview

Mortgage-ops stress sweeps are parameter-grid evaluations of the
underlying calc engines (Phase 3 amortization, Phase 4 affordability,
Phase 5 ARM). Three sweep modes are supported via the
`lib.stress.evaluate(req)` dispatcher and
`scripts/stress_test.py --mode {rate-shock|income-shock|arm-reset}`:

- **Rate-shock** (STRS-01): Re-solve monthly P&I for a grid of interest
  rates against a fixed loan.
- **Income-shock** (STRS-02): Recompute back-end DTI for a grid of
  household income reductions; flag rows that breach a configured
  affordability threshold.
- **ARM-reset** (STRS-03): Simulate three named index-path scenarios
  (parallel-shift, gradual-rise, fall-then-rise) over a 30-year horizon;
  report total interest paid per path.

Phase 8 invents NO new mathematical primitive — every cell in every grid
is a single call into a Phase 3/4/5 engine, then summary-scalar capture.
The composition-over-reinvention discipline keeps the stress layer thin
and the math anchored in already-tested code paths.

The dispatcher is a Pydantic v2 discriminated union by `mode` (locked at
Plan 08-01 D-01); the request payload's `mode` field selects exactly one
of `RateShockRequest` / `IncomeShockRequest` / `ArmResetRequest` and the
engine routes to the appropriate inner loop. The `--mode` CLI flag is an
**advisory hint** that helps users construct the right JSON shape but
the JSON body's `mode` discriminator is authoritative (Plan 08-04
D-04-01).

---

## Sweep Modes

### Rate-Shock (STRS-01 + ROADMAP SC-1)

Parameters: a `Loan` (principal + term + origination_date) plus a list
of rates and an optional `baseline_label`. The engine re-builds the
schedule per rate via `lib.amortize.build_schedule(loan_with_swapped_rate)`.
Output rows carry `monthly_pi`, `total_interest`, and signed deltas vs
the baseline rate (`delta_vs_baseline_monthly`,
`delta_vs_baseline_pct`).

**Example invocation (ROADMAP SC-1 verbatim):**

```
scripts/stress_test.py --mode rate-shock \
  --rates 0.06,0.065,0.07,0.075,0.08 \
  --input request.json
```

The `--rates` shortcut overlays the parsed list into `request.rates`
BEFORE Pydantic validation (Plan 08-04 D-04-02), so users can run the
canonical SC-1 invocation without hand-editing JSON. Last-write-wins:
if the JSON already supplies `rates`, the CLI shortcut overrides. The
parsed values stay strings end-to-end so the JSON-float gate semantics
(D-19) are preserved.

`baseline_label` defaults to `rates[0]` when unspecified; downstream
deltas are computed relative to whichever rate carries that label. The
fixture `rate_shock_baseline_label_override.json` (Plan 08-05) pins the
override behavior — `baseline_label="0.0700"` against a rate grid where
0.0700 is not the first entry yields negative deltas at the lower rates
and positive deltas above.

### Income-Shock (STRS-02 + ROADMAP SC-2)

Parameters: a baseline `AffordabilityRequest` plus a list of income
reductions and a DTI threshold. The engine scales each applicant's
`gross_monthly_income` by `(1 - reduction)` per cell, calls
`lib.affordability.evaluate(shocked_request)`, captures `dti_back` and a
`breach` flag (`dti_back > dti_threshold`).

**Example invocation (ROADMAP SC-2 verbatim):**

```
scripts/stress_test.py --mode income-shock \
  --reductions 0.05,0.10,0.20 \
  --input request.json
```

**Note on threshold:** The ATR/QM heuristic is `0.43`. The 43% DTI cap
is no longer a Black-letter rule (the March 2021 General QM Final Rule
replaced it with a price-based test in `lib/rules/atr_qm.py`), but it
remains the industry "comfortable affordability" anchor. The caller
MUST explicitly supply `dti_threshold` in the JSON body — there is no
module-level default (Plan 08-01 D-04). This matches the project's
fail-loud-on-implicit-default discipline (Phase 4 D-12 `max_dti`,
Phase 5 D-02 `floor_rate`, Phase 8 D-02 `discount_rate_annual`).

The CLI's `--help` epilog documents `0.43` as a recommended starting
point ONLY; the engine surface still requires the field.

### ARM-Reset (STRS-03 + ROADMAP SC-3)

Parameters: a baseline `ARMRequest` plus a list of named `RatePath`
scenarios. The engine synthesizes an `index_path` covering all reset
triggers per path via `lib.arm.compute_reset_triggers`, then calls
`lib.arm.build_arm_schedule(syn_request)` per path. Output rows:
`total_interest`, `max_payment`, `reset_count`, `highest_rate`.

Three canonical paths (closed-set per Plan 08-01 D-05 LOCKED):

- `parallel-shift` — instantaneous rate jump, held for the term horizon
  (worst-case stress: every reset trigger sees the shifted index).
- `gradual-rise` — steady upward step per reset (e.g., +25 bps per
  reset cadence, capped by ARMTerms periodic/lifetime caps).
- `fall-then-rise` — recession-then-recovery shape (drops first, then
  rises; exercises the floor algebra in `lib.arm` per Plan 05-05's
  references/arm-mechanics.md §3).

The closed-set `Literal["parallel-shift", "gradual-rise", "fall-then-rise"]`
is v1; future paths (e.g., shock-and-revert, regime-shift) require an
explicit `RatePath.name` extension and a new fixture per Plan 08-05
citation-coverage discipline.

---

## Output Schema (top-table-summary contract for SC-5)

`StressResponse` declares `summary` BEFORE `rows` in field-declaration
order. Pydantic v2 preserves this order in `model_dump_json`, so the
JSON blob always reads:

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

**This field order is LOAD-BEARING and NEVER reordered** (Plan 08-01
D-02 LOCKED). The Phase 11 `stress-test-agent` (Haiku, ≤1k token return
budget) reads the first ~30 lines of the indented JSON and gets the
summary table + worst-case label + invariant-violation list without
paging the per-row detail. Plan 08-05 verifies the field order via a
fixture-driven byte-position check (substring `"summary"` precedes
substring `"rows"` in the indented serialization).

### Size budget (SC-5: <100KB)

Per-row `schedule_summary` is ~150 bytes JSON (a handful of Decimal
strings, no full payment schedules). 50-scenario sweep ≈ 50 × 150 +
summary overhead ≈ 8KB — well under the 100KB ceiling. **Critical rule
pinned in Plan 08-01 D-03:** do NOT serialize per-row
`Schedule.payments[]` (each schedule has 360+ rows; 50 schedules × 360
rows × 200 bytes ≈ 3.6MB — would blow the budget by 36×). `StressRow`
carries ONLY summary scalars from each engine call; the full schedules
are recomputed on demand by Phase 11 if a deep-dive is needed.

The 50-rate fixture `rate_shock_size_budget_50_rates.json` (Plan 08-05)
empirically validates the budget — the engine-emitted JSON is 37,623
bytes, comfortably under the 100KB SC-5 contract.

### Stress invariants

Surfaced as `summary.stress_invariant_violations: list[str]`:

| Code | Mode | Meaning |
|---|---|---|
| `RATE_SHOCK_MONOTONE_PI` | rate-shock | `monthly_pi` did NOT strictly increase as rate strictly increased — Phase 3 engine bug signal |

Empty list = happy path. Future Phase 11+ test-coverage expansions will
add income-shock and arm-reset invariants (e.g.,
`INCOME_SHOCK_MONOTONE_DTI`, `ARM_RESET_LIFETIME_CEILING_NOT_EXCEEDED`).
The fail-loud-via-list pattern (Plan 08-01 D-06) lets the agent narrate
the violation rather than a raise blowing up the sweep mid-flight.

---

## Subagent Consumption Hint (Phase 11 contract)

When Phase 11 ships `stress-test-agent` (Haiku, 1k token return budget),
its system prompt should include the following paragraph **verbatim**
per locked decision D-06-04:

> Read the `summary.table` block first. Each row is one scenario. The
> `worst_case_label` field names the most stressed scenario. The
> `stress_invariant_violations` field, if non-empty, lists
> physics-of-amortization violations (e.g., `monthly_pi` went DOWN as
> rate went UP — would indicate an engine bug). If empty, narrate the
> table directly. Only drill into `rows` if the user asks for
> per-scenario detail.

Phase 11 lifts this paragraph verbatim into
`.claude/agents/stress-test-agent.md`. The structural contract is
load-bearing (the agent must read summary first, drill into rows only
on demand); the byte-exact wording is an inheritance convenience and
trims to the 1k-token budget are explicitly permitted (Plan 08-06
deviation Rule 2).

---

## Citations

Primary regulatory references (eCFR / CFPB; verification cadence: annual
per the Phase 2 staleness convention):

- **CFPB ATR/QM rule, 12 CFR §1026.43(c)(5)** — Max-payment stress test
  mandate for ARM products (lender must consider the maximum-rate
  payment in the first 5 years for non-balloon, non-step-rate, non-
  negative-amortization loans). The `arm-reset` sweep enables this
  calculation; per-row `max_payment` field surfaces the worst-case
  payment across the path. Sole regulatory anchor for STRS-03.
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-E/section-1026.43

- **CFPB Stress Test Guidance** (post-2008 supervisory commentary) —
  Rate-shock sweeps are the regulatory-blessed framework for evaluating
  borrower resilience to interest-rate volatility. Underwriters use
  rate-shock at origination; servicers use it for portfolio risk.
  https://www.consumerfinance.gov/

- **March 2021 General QM Final Rule** — Replaced the strict 43% DTI
  cap with a price-based test (encoded in `lib/rules/atr_qm.py` per
  Phase 2). The `0.43` threshold default in income-shock sweeps is a
  **heuristic affordability anchor only**, NOT a regulatory pass/fail
  gate. The price-based test (loan APR vs APOR spread) lives in
  `within_qm_apr_apor_spread` per Phase 2 plans; income-shock sweeps
  consume DTI as a borrower-facing comfort metric, not as a Reg Z QM
  qualification.
  https://www.consumerfinance.gov/rules-policy/final-rules/qualified-mortgage-definition-under-truth-lending-act-regulation-z-general-qm-loan-definition/

CFPB explainer + supervisory references:

- **CFPB Ask CFPB §1951** (ARM rate caps explainer) — Cross-referenced
  by `references/arm-mechanics.md` §2; the ARM-reset sweep exercises the
  cap precedence implemented per the same predicate.
  https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/

Cross-phase / internal references:

- **Phase 3 amortization engine** — `lib/amortize.py::build_schedule`.
  Rate-shock sweeps call this once per rate cell.
- **Phase 4 affordability engine** — `lib/affordability.py::evaluate`.
  Income-shock sweeps call this once per reduction cell with the income
  rescaled.
- **Phase 5 ARM engine** — `lib/arm.py::build_arm_schedule` plus
  `compute_reset_triggers`. ARM-reset sweeps synthesize a per-path
  `index_path` and call `build_arm_schedule` once per named path.
- **Phase 5 ARM mechanics doc** — `references/arm-mechanics.md` (cap /
  floor / reset conventions inherited by ARM-reset rows).
- **Phase 8 points-breakeven sibling** — `references/points-breakeven.md`
  (Plan 08-06 same-wave companion doc; common section-structure
  inheritance from `references/arm-mechanics.md` per D-06-01).

---

## Glossary

- **Rate shock** — interest-rate parameter sweep against a fixed loan;
  re-solves monthly P&I per cell.
- **Payment shock** — the resulting payment delta when a rate shock or
  ARM reset occurs (the consumer-facing dollar figure).
- **Income shock** — household-income reduction sweep against a baseline
  affordability request; recomputes DTI per cell.
- **Stressed DTI** — DTI computed under one of the shocks (typically
  income-shock or rate-shock-with-housing-update); the sweep flags rows
  above the configured threshold.
- **Path** (ARM-reset) — one of the three named index-trajectory
  scenarios (`parallel-shift`, `gradual-rise`, `fall-then-rise`).
- **Reset trigger** (ARM) — a month at which the ARM rate is recomputed
  per the ARMTerms cadence; `compute_reset_triggers(arm_terms)` returns
  the trigger month list.
- **Worst-case label** — the row label (rate string, reduction string,
  or path name) carrying the highest stress metric (max `monthly_pi`,
  max `dti_back`, or max `total_interest`); reported in
  `summary.worst_case_label` for fast subagent narration.
- **Invariant violation** — a physics-of-amortization expectation that
  failed (e.g., `monthly_pi` decreased as rate increased); reported as a
  citation string in `summary.stress_invariant_violations` and treated
  as a Phase 3/4/5 engine bug signal.

---

## Appendix — Citation Index

| URL | Section / Anchor | Last verified |
|-----|------------------|----------------|
| https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-E/section-1026.43 | 12 CFR §1026.43(c)(5) ATR/QM max-payment stress test | 2026-05-03 |
| https://www.consumerfinance.gov/rules-policy/final-rules/qualified-mortgage-definition-under-truth-lending-act-regulation-z-general-qm-loan-definition/ | March 2021 General QM Final Rule | 2026-05-03 |
| https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/ | CFPB Ask CFPB §1951 ARM rate caps | 2026-05-03 |
| https://www.consumerfinance.gov/ | CFPB stress test supervisory guidance (umbrella) | 2026-05-03 |

Annual re-validation cadence: each calendar year, confirm each URL still
resolves; if any have moved, update the index above. Mirrors
`references/arm-mechanics.md` and `references/apr-reg-z.md` cadence.
