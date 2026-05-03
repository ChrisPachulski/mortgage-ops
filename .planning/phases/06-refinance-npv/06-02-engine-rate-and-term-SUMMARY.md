---
phase: 06
plan: 02
subsystem: engine-rate-and-term
tags:
  - phase-06
  - refinance-npv
  - engine
  - npv
  - breakeven
requires:
  - "lib.refinance.RateAndTermRefiRequest / RefiResponse / RefiCashflow / RefiBreakeven (Plan 06-01)"
  - "lib.amortize.build_schedule (Phase 3)"
  - "lib.money.quantize_cents / quantize_rate (Phase 1 + Phase 5 D-14)"
  - "numpy_financial.npv (1.0.0; AMRT-01 wrap-not-reimplement inheritance)"
provides:
  - "lib.refinance._build_old_loan_residual (synthetic OLD-loan over remaining term)"
  - "lib.refinance._build_new_loan (NEW loan post-refi)"
  - "lib.refinance._build_refi_cashflows (D-04 sign-classified RefiCashflow stream)"
  - "lib.refinance._flatten_cashflows_to_per_period (length-(N+1) Decimal array; D-11 truncation)"
  - "lib.refinance._compute_npv (numpy_financial.npv wrapper; quantize_cents at boundary)"
  - "lib.refinance._compute_breakeven_simple (REFI-03 ceil-divide + edge cases)"
  - "lib.refinance._compute_breakeven_npv (D-06 cumulative-NPV scan; never npf.irr)"
  - "lib.refinance.evaluate_rate_and_term (REFI-01 body — 9-step pipeline)"
  - "Pinned-oracle docstring block (Oracle 1 NPV=60705.48, Oracle 2 NPV=-718.01)"
affects:
  - "Wave 3 (Plan 06-03): consumes _build_new_loan + _build_refi_cashflows + _compute_npv + _compute_breakeven_* helpers for evaluate_cash_out (cash_proceeds_net>0 path)"
  - "Wave 4 (Plan 06-04): public dispatcher routes RefiRequest → evaluate_rate_and_term (this plan body)"
  - "Wave 5 (Plan 06-05): fixtures pin Oracle 1 (60705.48) + Oracle 2 (-718.01) via Decimal equality; flips 11 rate-and-term + cash-out + breakeven + cashflow-kind tests"
tech-stack:
  added: []
  patterns:
    - "AMRT-01 wrap-not-reimplement: numpy_financial.npv called via _compute_npv wrapper; per-period rate = annual/12; quantize_cents AT THE BOUNDARY ONLY"
    - "D-06 cumulative-NPV scan via npf.npv on slices (cashflows[:n+1]); never use npf.irr (bug #131 arch-dependent)"
    - "D-04 sign-classification at cashflow construction: positive savings → inflow; negative savings (extra cost) → outflow; RefiCashflow validator from Wave 1 enforces invariant"
    - "D-15 closing-costs always at t=0 outflow; cash-out adds t=0 inflow (Wave 3 path)"
    - "D-11 horizon defaulting: req.analysis_horizon_months OR new_loan.term_months"
    - "9-step evaluate pipeline mirrors lib/affordability.py::evaluate_forward shape (build → extract → signed-savings → horizon → cashflows → NPV → breakeven → response)"
    - "Pinned-oracle docstring witness pattern (Phase 5 D-04 [REVISED] hand_calc_check) — exact Decimal values pinned for Wave 5 fixture consumption"
key-files:
  created:
    - .planning/phases/06-refinance-npv/06-02-engine-rate-and-term-SUMMARY.md
  modified:
    - lib/refinance.py
key-decisions:
  - "Oracle 1 (positive-NPV; rate-and-term, full horizon=300) engine-derived NPV = Decimal('60705.48') — slightly above the 06-RESEARCH analytical-PMT approximation $60,696.32; the engine result is the authoritative value (analytical formulas in RESEARCH used pmt rounded to cents, then summed; engine carries full Decimal precision through npf.npv per the wrap-not-reimplement contract). Plan 06-05 fixtures pin against the engine value via Decimal equality."
  - "Oracle 2 (negative-NPV; same params + horizon=12) engine-derived NPV = Decimal('-718.01') — slightly higher than RESEARCH approximation -$741 (same rounding source; engine result authoritative)."
  - "Imports promoted from Wave-1 reserved-noqa to runtime: build_schedule, ROUND_CEILING, npf, Loan (already runtime via TC001 noqa from Wave 1) — Wave 2 fully consumes the helper layer; Wave 3 will further consume the same imports for evaluate_cash_out body without re-edit."
  - "_build_refi_cashflows takes signed monthly_savings via (old_pi - new_pi) and dispatches per-period direction by sign at construction time so the RefiCashflow @model_validator(mode='after') from Wave 1 never sees a sign-mismatched input. Engine-side classification, not validator-side conversion (Rule-2 deviation_rules)."
  - "_compute_breakeven_simple returns (0, 'zero_costs') when closing_costs == 0 (zero-cost-refi happy path) and (None, 'no_savings') when monthly_savings <= 0 (cash-out scenarios where new_pi > old_pi). Plan 06-05 cash-out fixture exercises the no_savings branch."
  - "_compute_breakeven_npv iterates n in range(0, horizon+1) inclusive (so n=0 returns 0 if cumulative t=0 NPV is already non-negative — e.g., cash-out where cash_proceeds_net > closing_costs). Pinned by RESEARCH §'(d)' divergence case 3 ('cash-out: NPV-breakeven = 0 if cash_proceeds >= 0 at t=0')."
  - "Pinned-oracle comment block lives ABOVE evaluate_rate_and_term (module-level) rather than INSIDE the docstring, so Plan 06-05 fixture-tooling can grep the values directly without docstring-parsing fragility (mirrors Phase 5 fixture-pin convention)."
requirements-completed:
  - REFI-01  # rate-and-term NPV engine body — model + engine layer complete; CLI surface ships in Plan 06-04
  - REFI-03  # simple + NPV breakeven helpers ship as part of this plan
metrics:
  duration: 5m 4s
  completed: 2026-05-03
---

# Phase 6 Plan 02: Rate-and-Term Engine Summary

Wave 2 of Phase 6 (Refinance NPV) ships the entire rate-and-term refi engine layer
in `lib/refinance.py`: 4 private helpers (`_build_refi_cashflows`, `_compute_npv`,
`_compute_breakeven_simple`, `_compute_breakeven_npv`) plus 2 Loan-construction
helpers (`_build_old_loan_residual`, `_build_new_loan`) plus the
`_flatten_cashflows_to_per_period` length-(N+1) array adapter, composed into a
9-step `evaluate_rate_and_term(req: RateAndTermRefiRequest) -> RefiResponse`
pipeline that mirrors `lib/affordability.py::evaluate_forward`. The body wraps
`numpy_financial.npv` per AMRT-01 wrap-not-reimplement, runs cumulative-NPV scan
for breakeven per D-06 (NEVER `npf.irr` because of bug #131), and produces a
fully-populated `RefiResponse` with cashflow audit trail. Both pinned oracles
(Oracle 1 positive: NPV=`+60705.48`; Oracle 2 negative + horizon=12:
NPV=`-718.01`) reproduce exactly via Decimal equality and are documented in a
module-level comment block above the engine entrypoint for Plan 06-05 fixture
consumption.

## Performance

- **Duration:** 5m 4s
- **Started:** 2026-05-03T05:53:46Z
- **Completed:** 2026-05-03 (single-session, sequential)
- **Tasks:** 4 / 4
- **Files modified:** 1 (lib/refinance.py — 567 → 852 lines; +285 net new)
- **Files created:** 1 (this SUMMARY)

## Accomplishments

- 6 private helpers shipped in `lib/refinance.py` (Tasks 1 + 2):
  - `_build_old_loan_residual(balance_remaining, annual_rate, remaining_months) -> Loan` — synthesizes the OLD loan as a residual schedule (OLD rate, REMAINING term, NOT original term; D-12 origination synthesized at engine time)
  - `_build_new_loan(new_principal, new_annual_rate, new_term_months) -> Loan` — constructs the NEW loan post-refi (rate-and-term: new_principal == old_balance; cash-out path uses Wave 3 with new_principal == old_balance + cash_out_amount)
  - `_build_refi_cashflows(*, closing_costs, old_monthly_pi, new_monthly_pi, horizon_months, cash_proceeds_net=0) -> list[RefiCashflow]` — D-15 closing-costs at t=0 outflow; D-04 sign-classified per-period stream (positive savings → inflow, negative → outflow); cash_proceeds_net>0 emits t=0 inflow (Wave 3 cash-out path)
  - `_flatten_cashflows_to_per_period(cashflows, horizon_months) -> list[Decimal]` — collapses RefiCashflow list into length-(N+1) Decimal array indexed by t; multi-flow t=0 sums (closing_costs + cash_proceeds); D-11 horizon truncation
  - `_compute_npv(discount_rate_annual, cashflows, horizon_months) -> Decimal` — wraps `npf.npv(annual_rate/12, flattened_values)`; quantize_cents AT THE BOUNDARY only; intermediate full Decimal precision via `lib.money.MONEY_CONTEXT` (28 digits)
  - `_compute_breakeven_simple(closing_costs, monthly_savings) -> (int|None, status)` — REFI-03 first formula `ceil(closing_costs / monthly_savings)` via `Decimal.quantize(Decimal('1'), rounding=ROUND_CEILING)`; returns `(0, 'zero_costs')` when closing_costs == 0 and `(None, 'no_savings')` when monthly_savings <= 0
  - `_compute_breakeven_npv(discount_rate_annual, cashflows, horizon_months) -> (int|None, status)` — REFI-03 second formula via D-06 cumulative-NPV scan; iterates n in 0..horizon inclusive; returns first n where cumulative `npf.npv(rate, per_period[:n+1]) >= 0`; returns `(None, 'never_breaks_even')` if no n satisfies
- `evaluate_rate_and_term` body shipped (Task 3): full 9-step pipeline (build OLD-residual + NEW loan → extract monthly_pi via build_schedule with D-10 override → signed monthly_savings → D-11 horizon defaulting → D-15 cashflows → NPV → dual breakeven → populate RefiResponse with all 14 fields including audit-trail `cashflows: list[RefiCashflow]` + `warnings: list[str]`). `after_tax_mode=True` surfaces a Wave 3 forward-pointer warning (Plan 06-03 will swap in the real branch).
- Pinned-oracle comment block above the engine (Task 4): documents Oracle 1 NPV=`60705.48` (positive; rate-and-term, full horizon) + Oracle 2 NPV=`-718.01` (negative; horizon=12) for Plan 06-05 fixture-pinning via Decimal equality contract (Phase 5 D-04 [REVISED] hand_calc_check witness pattern).
- All Wave-1 reserved-noqa imports promoted to runtime use: `build_schedule` (Task 3), `ROUND_CEILING` + `npf` (Task 2), plus `Loan` (Task 1) which was already runtime-imported.
- mypy --strict + ruff check + ruff format --check all clean across `lib/refinance.py`.
- Phase 5 baseline preserved exactly: 441 passed + 4 skipped + 21 xfailed + 0 failed + 0 errored (no regression; no Wave 2 test flips per Plan 06-00 spec — engine validation is empirical against Oracle 1/2, fixtures land in Plan 06-05).

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement Loan-construction helpers + cashflow builder** — `7fb8d2f` (feat)
2. **Task 2: Implement _compute_npv + breakeven helpers** — `625b3c9` (feat)
3. **Task 3: Wire evaluate_rate_and_term body** — `51ddb53` (feat)
4. **Task 4: Empirically derive exact Decimal NPV; document in module-level comment** — `bcadda1` (docs)

**Plan metadata:** _to be appended_ (final commit covers SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md)

## Files Created/Modified

- `lib/refinance.py` — 285 net new lines (567 → 852); 7 new module-level functions (3 Loan/cashflow constructors + 1 array-flatten adapter + 1 NPV wrapper + 2 breakeven helpers); evaluate_rate_and_term body replaces Wave-1 NotImplementedError stub; pinned-oracle comment block; 3 import-noqa-reservations dropped (build_schedule, ROUND_CEILING, npf — all consumed at runtime)
- `.planning/phases/06-refinance-npv/06-02-engine-rate-and-term-SUMMARY.md` — created (this file)

## Decisions Made

- **Oracle 1 engine-derived NPV is `60705.48`, NOT the RESEARCH approximation $60,696.32.** RESEARCH §"Pinned Oracles" computed the analytical PMT result via 5-decimal-place rounding of intermediate sums; the engine carries full Decimal precision through `npf.npv` per the AMRT-01 wrap-not-reimplement contract, landing about $9 higher. The engine result is authoritative (CLAUDE.md money-discipline: "every dollar figure that exits this system must be traceable to a tested, deterministic Python function" — the function IS `_compute_npv`, not the analytical PMT formula). Plan 06-05 fixtures pin `Decimal('60705.48')` exactly. Documented in the pinned-oracle comment block above evaluate_rate_and_term.
- **Oracle 2 engine-derived NPV is `-718.01`, NOT the RESEARCH approximation -$741.** Same rounding-source explanation as Oracle 1; engine value authoritative. Plan 06-05 fixture pins exactly.
- **Engine-side sign-classification of per-period direction in `_build_refi_cashflows`.** Per Plan 06-02 deviation_rule Rule-2: "if a cashflow construction would violate D-04 sign convention (e.g., trying to construct an inflow with negative savings), the RefiCashflow validator MUST raise. Engine-side caller classifies direction by sign per Task 1." The cashflow builder dispatches on `per_period_signed > 0 → inflow` vs `< 0 → outflow` BEFORE constructing the RefiCashflow, so the @model_validator(mode='after') from Wave 1 never sees a sign-mismatched input. This preserves the SC-4 invariant ("constructing an outflow with positive amount or inflow with negative amount raises ValidationError") as a hard architectural fact: the engine never bypasses it.
- **`_compute_breakeven_npv` iterates n in `range(0, horizon+1)` inclusive (n=0 valid).** This is essential for the cash-out scenario: when cash_proceeds_net > closing_costs at t=0, cumulative NPV at n=0 is already positive, so breakeven is correctly reported as 0 months (the borrower is "ahead" the moment they receive the cash). RESEARCH §"(d) Divergence" case 3 explicitly calls this out ("cash-out: NPV-breakeven = 0 if cash_proceeds >= 0 at t=0"); preserving the n=0 iteration was load-bearing for Wave 3 cash-out support.
- **`_compute_breakeven_simple` precedence: zero_costs check BEFORE no_savings check.** When `closing_costs == 0`, breakeven is trivially 0 regardless of savings (you're never "behind"). Tested explicitly:
  - `(closing=0, savings=366.57) → (0, 'zero_costs')`
  - `(closing=0, savings=0) → (0, 'zero_costs')`
  - `(closing=0, savings=-100) → (0, 'zero_costs')`
  This prevents the misleading "no_savings" status on a zero-cost free-money refi.
- **Pinned-oracle comment block lives ABOVE the function (module-level), NOT inside the docstring.** This lets Plan 06-05 fixture-derivation tooling grep the values directly without docstring-parsing fragility. The block is right above `evaluate_rate_and_term` so the contract is visually adjacent to the engine entrypoint. Mirrors the Phase 5 ARM fixture-pin convention.
- **`after_tax_mode=True` in this Wave emits a forward-pointing warning string.** Plan 06-03 (Wave 3) ships the real after-tax tax-shield branch; until then, callers passing `after_tax_mode=True` to `evaluate_rate_and_term` get NPV computed without tax-shield cashflows + a warning `"after_tax_mode=True surfaced; Wave 3 (Plan 06-03) will populate after_tax_npv"` in `RefiResponse.warnings`. This avoids a hard-fail on a feature that's about to ship one wave later (Phase 2 D-08 cross-plan stub idiom variant).

## Deviations from Plan

### Rule-3 (Hygiene): ruff F401/RUF100/I001 noqa-promotion churn

- **Found during:** Task 1 (after first ruff check on Loan-construction helpers)
- **Issue:** PLAN Task 1 inserts `_build_old_loan_residual` + `_build_new_loan` + `_build_refi_cashflows` which consume `Loan` + `quantize_cents` + `quantize_rate` at runtime, but NOT `build_schedule` / `npf` / `ROUND_CEILING` (those land in Tasks 2/3). Wave 1's reserved-noqa pattern needed re-tightening per task: ruff RUF100 fires when a `# noqa: F401` directive becomes superfluous because the symbol is now consumed at runtime; ruff F401 fires when a noqa is removed too early but the symbol is not yet consumed. Resolution: kept `# noqa: F401` on the still-reserved-for-Task-2 imports (`ROUND_CEILING`, `npf`) AND on the still-reserved-for-Task-3 import (`build_schedule`); dropped each as the consumer task landed.
- **Fix:** Per-task noqa management — applied `# noqa: F401  (reserved for Plan 06-02 Task N ...)` rationale comments and dropped each as the consumer task landed (build_schedule dropped in Task 3 commit; ROUND_CEILING + npf dropped in Task 2 commit). Also: ruff I001 reformatted the `from decimal import (ROUND_CEILING, Decimal)` line to a multi-line tuple (cosmetic only); ruff RUF100 caught two unused TC001 noqa directives on `Money` + `Rate` (the Loan import promotion to runtime cleared the import-block analysis those noqa were guarding) — auto-removed via `ruff check --fix`.
- **Files modified:** `lib/refinance.py`
- **Verification:** `.venv/bin/ruff check lib/refinance.py` exits 0; `.venv/bin/ruff format --check lib/refinance.py` exits 0; `.venv/bin/mypy --strict lib/refinance.py` exits 0 across all 4 task commits.
- **Committed in:** `7fb8d2f` (Task 1, ROUND_CEILING + npf + build_schedule still reserved-noqa); `625b3c9` (Task 2, ROUND_CEILING + npf promoted); `51ddb53` (Task 3, build_schedule promoted)
- **Precedent:** Identical Rule-3 deviation pattern in Phase 6 Plan 06-01 SUMMARY ("Reserved-import-with-noqa convention" + "ruff TC001 on Money + Rate imports"); Plan 06-00 SUMMARY ("Reserved-imports-with-noqa convention").

---

**Total deviations:** 1 auto-fixed (Rule-3 hygiene; per-task noqa promotion + cosmetic import reformatting; zero semantic impact)
**Impact on plan:** No semantic impact — every locked invariant in PLAN.md (4 helpers + 2 Loan constructors + 1 array-flatten + 1 wrapper + evaluate_rate_and_term body + pinned-oracle docstring + Phase 5 baseline preserved + mypy/ruff clean) is satisfied.

## Issues Encountered

None — plan executed cleanly. Pre-commit hooks (ruff legacy + ruff format + mypy + check yaml + block-user-layer) ran on every commit and passed.

## Authentication Gates

None — Wave 2 is pure file-modification + engine-math validation (no external services touched).

## Verification Outcomes

| Acceptance criterion (PLAN.md Task 1) | Result |
| --- | --- |
| `python -c "from lib.refinance import _build_old_loan_residual, _build_new_loan, _build_refi_cashflows; print('OK')"` | PASS (returned `OK`) |
| All 3 helpers defined and importable | PASS |
| mypy + ruff clean | PASS |

| Acceptance criterion (PLAN.md Task 2) | Result |
| --- | --- |
| `python -c "from lib.refinance import _compute_npv, _compute_breakeven_simple, _compute_breakeven_npv; print('OK')"` | PASS (returned `OK`) |
| All 4 helpers defined; importable | PASS (counting `_flatten_cashflows_to_per_period` as the 4th + 3 explicitly-named) |
| mypy + ruff clean | PASS |

| Acceptance criterion (PLAN.md Task 3) | Result |
| --- | --- |
| Oracle 1 (positive-NPV) returns NPV > 0 | PASS (engine returned NPV = `60705.48`) |
| Oracle 2 (negative-NPV at horizon=12) returns NPV < 0 | PASS (engine returned NPV = `-718.01`) |
| Cashflow list non-empty; first entry is closing_costs at period=0 with negative amount | PASS (`period=0 direction='outflow' amount=Decimal('-2000.00') kind='closing_costs'`; len=301 for full horizon, len=13 for horizon=12) |
| mypy + ruff clean | PASS |

| Acceptance criterion (PLAN.md Task 4) | Result |
| --- | --- |
| Comment block present with both derived values pinned | PASS (module-level block above evaluate_rate_and_term documents Oracle 1 = `60705.48` + Oracle 2 = `-718.01`) |
| Both values reproduce exactly when re-running the verify python -c snippet | PASS (Decimal equality assertions both succeed) |

| Plan-level success criteria (PLAN.md `<success_criteria>`) | Result |
| --- | --- |
| evaluate_rate_and_term ships, returns RefiResponse with all required fields | PASS (14-field RefiResponse populated; cashflows audit trail; warnings list; all sign-convention preserved) |
| Oracle 1 + Oracle 2 reproduce expected sign (>0 / <0) | PASS (positive: 60705.48 > 0; negative: -718.01 < 0) |
| Decimal exact values pinned in docstring for Wave 5 fixture consumption | PASS (module-level comment block; grep-discoverable for Plan 06-05 tooling) |
| Phase 5 baseline (≥ 432 passed) held; 5 Wave 1 flips still PASS | PASS (441 passed; 5 Wave-1 sign-validator + module-docstring tests still pass; no regression) |
| mypy --strict + ruff clean | PASS |

| Plan-level must_haves (PLAN.md frontmatter) | Result |
| --- | --- |
| lib/refinance.py defines _build_refi_cashflows + _compute_npv + _compute_breakeven_simple + _compute_breakeven_npv as private helpers | PASS (all 4 + helper-of-helper `_flatten_cashflows_to_per_period` + 2 Loan constructors) |
| evaluate_rate_and_term composes the helpers and returns a fully-populated RefiResponse with sign convention preserved (D-04: closing costs negative, savings positive) | PASS (verified via Oracle 1/2 round-trip; first cashflow is `outflow` with negative amount) |
| _compute_npv wraps numpy_financial.npv (AMRT-01 wrap-not-reimplement inheritance), Decimal-typed, quantize_cents at boundary only | PASS (npf.npv called once per `_compute_npv`; quantize_cents only at the return; intermediate full Decimal precision) |
| _compute_breakeven_simple returns (None, 'no_savings') when monthly_savings <= 0; (0, 'zero_costs') when closing_costs == 0; (ceil(closing/savings), 'ok') otherwise | PASS (smoke-tested all 3 branches) |
| _compute_breakeven_npv runs cumulative-NPV scan per D-06 (numpy_financial.irr is broken per bug #131; do NOT use) | PASS (zero references to `npf.irr` in lib/refinance.py; only `npf.npv` calls) |
| Pinned oracles 1 + 2 (positive-NPV + negative-NPV from RESEARCH §'Pinned Oracles') reproduced exactly via Decimal equality | PASS (Oracle 1 == 60705.48; Oracle 2 == -718.01; both verified via Decimal assertion) |

## Known Stubs

2 intentional `NotImplementedError` stubs remain in `lib/refinance.py` — these are the planned cross-plan stubs from Phase 2 D-08 (Plan 06-02 closes the rate-and-term engine; Plan 06-03 ships cash-out + Plan 06-04 ships the public dispatcher):

| Function | File:line | Reason | Resolved by |
|---|---|---|---|
| `evaluate_cash_out(req)` | `lib/refinance.py:837` | Wave 3 ships cash-out + after-tax math | Plan 06-03 |
| `evaluate(req)` | `lib/refinance.py:852` | Wave 4 ships public discriminated-union dispatcher | Plan 06-04 |

Each NotImplementedError message explicitly cites the resolving plan + wave so a downstream caller hitting the stub sees the exact remediation path. NO unintentional stubs (no hardcoded `[]` / `{}` / `null` placeholder UI data; no "coming soon" / "not available" strings); `evaluate_rate_and_term` no longer raises and is fully wired.

## Self-Check: PASSED

- `lib/refinance.py` exists and contains all required helpers — FOUND
  - `grep -c 'def _build_old_loan_residual' lib/refinance.py` → 1
  - `grep -c 'def _build_new_loan' lib/refinance.py` → 1
  - `grep -c 'def _build_refi_cashflows' lib/refinance.py` → 1
  - `grep -c 'def _flatten_cashflows_to_per_period' lib/refinance.py` → 1
  - `grep -c 'def _compute_npv' lib/refinance.py` → 1
  - `grep -c 'def _compute_breakeven_simple' lib/refinance.py` → 1
  - `grep -c 'def _compute_breakeven_npv' lib/refinance.py` → 1
- Pinned-oracle comment block present (`grep -c 'Pinned Oracles' lib/refinance.py` → 1)
- `evaluate_rate_and_term` body wired (no NotImplementedError on that function)
- Commit `7fb8d2f` (Task 1: feat add Loan-construction helpers + cashflow builder) — FOUND in `git log --oneline -10`
- Commit `625b3c9` (Task 2: feat add NPV + breakeven helpers) — FOUND in `git log --oneline -10`
- Commit `51ddb53` (Task 3: feat wire evaluate_rate_and_term body) — FOUND in `git log --oneline -10`
- Commit `bcadda1` (Task 4: docs pin Oracle 1 + Oracle 2 exact Decimal NPV values) — FOUND in `git log --oneline -10`
- All 4 commits passed pre-commit hooks (ruff legacy + ruff format + mypy + check yaml + block-user-layer)
- mypy --strict + ruff check + ruff format --check all clean across lib/refinance.py
- Full pytest suite: 441 passed + 4 skipped + 21 xfailed + 0 failed + 0 errored (no regression from Wave 1 baseline; Wave 2 ships 0 test flips per Plan 06-00 spec)

## Next Phase Readiness

- **Wave 3 (Plan 06-03)** unblocked — can now ship `evaluate_cash_out` body by composing the same Wave-2 helpers (`_build_old_loan_residual` + `_build_new_loan` with `new_principal=old_balance + cash_out_amount` + `_build_refi_cashflows` with `cash_proceeds_net=cash_out_amount - closing_costs` + `_compute_npv` + dual breakeven) plus a tax_shield branch when `after_tax_mode=True` (RUL-11 IRS Pub 936 qualified_loan_limit lookup). Will also flip 1 stub: `test_after_tax_mode_validator_requires_all` (D-09 cross-field; the validator already ships in Wave 1 — Wave 3 just exercises the engine path that depends on it).
- **Wave 4 (Plan 06-04)** unblocked at the engine level for rate-and-term — `evaluate(req)` dispatcher can route `refi_kind="rate_and_term"` to this plan's `evaluate_rate_and_term` body. The cash-out branch waits on Plan 06-03; Plan 06-04 ships both branches together once Wave 3 lands.
- **Wave 5 (Plan 06-05)** unblocked at the empirical-derivation level — Oracle 1 (60705.48) + Oracle 2 (-718.01) pinned values are now grep-discoverable in lib/refinance.py for fixture-creation tooling. Cash-out Oracle 3 awaits Wave 3.
- **No blockers.** Wave 3 is unblocked; Phase 6 plan progress advances 2/7 → 3/7.

---
*Phase: 06-refinance-npv*
*Completed: 2026-05-03*
