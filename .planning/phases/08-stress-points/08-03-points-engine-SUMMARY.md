---
phase: 08-stress-points
plan: 03
subsystem: stress-points
tags:
  - phase-08
  - stress-points
  - points-engine
  - simple-breakeven
  - npv-breakeven
  - phase-3-composition

# Dependency graph
requires:
  - phase: 03-amortization
    provides: "lib.amortize.build_schedule (Phase 3 D-09 cleanup; exact-to-cent monthly_pi via lib.money.quantize_cents) — re-entered TWICE per from_loans request to derive monthly_savings"
  - phase: 08-stress-points/08-01
    provides: "lib.points type contract (PointsRequestFromSavings|PointsRequestFromLoans discriminated union; PointsResponse simple-vs-NPV-side-by-side per ROADMAP SC-4 D-01-07; evaluate() cross-plan stub raising NotImplementedError) — Plan 08-03 fills evaluate() body and adds simple_breakeven + npv_breakeven helpers"
  - phase: 08-stress-points/08-00
    provides: "tests/test_points.py 5 strict-xfail stubs (Wave 0 Nyquist gate) — this plan flips 2 of them"

provides:
  - "lib.points.simple_breakeven(points_cost, monthly_savings) — Decimal-safe ceil(points_cost / monthly_savings) under localcontext(MONEY_CONTEXT); returns int | None where None signals monthly_savings <= 0 (D-03-01 mirrors Phase 4 D-11)"
  - "lib.points.npv_breakeven(points_cost, monthly_savings, hold_months, discount_rate_annual) — month-by-month cumulative discounted-savings walk per 08-RESEARCH §5.2; returns (cum_npv_at_hold, months_to_zero | None); zero-discount branch collapses to undiscounted accumulation by mathematical identity (D-03-03)"
  - "lib.points._derive_monthly_savings(loan_with_points, loan_without_points) — private helper for from_loans branch; runs build_schedule on each Loan and diffs monthly_pi (D-03-05)"
  - "lib.points.evaluate(req) — discriminated-union dispatcher: from_savings uses caller-supplied monthly_savings directly; from_loans derives via _derive_monthly_savings. Always reports BOTH simple AND npv side-by-side per ROADMAP SC-4. diverge=True iff both non-None AND unequal. decision='buy_points' iff cum_npv_at_hold >= 0; forced to 'skip_points' when simple_breakeven is None"
  - "Type-contract correctness fix [Rule 2]: relax PointsRequestFromSavings.monthly_savings + PointsResponse.monthly_savings + PointsResponse.cumulative_npv_at_hold from Money (ge=0) to signed Decimal (max_digits=14, decimal_places=2) so the documented rate-up-scenario edge case actually round-trips through the response model (mirrors Phase 6 D-03 RefiCashflow.amount precedent)"
  - "2 Wave-0 xfails flipped at the engine layer: simple_breakeven ceil-division + evaluate() decision dispatcher (zero-discount no-divergence + 7%-discount divergence). 3 xfails remain: 2 CLI stubs (Plan 08-04) + 1 SC-4 divergence-pin fixture (Plan 08-05)"

affects:
  - 08-04-clis
  - 08-05-fixtures-and-tests
  - 08-06-references

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Decimal-safe ceil idiom: `(quotient).to_integral_value(rounding=ROUND_CEILING)` under `localcontext(MONEY_CONTEXT)` — never goes through float; never mutates the global Decimal context. New project-wide pattern."
    - "Cumulative discounted-sum walk for NPV breakeven (08-RESEARCH §5.2 documented formula): `cum_npv(m) = sum_{k=1..m} monthly_savings/(1+r_monthly)^k - points_cost`; iterate, capture first m where cum_npv >= 0. Closed-form annuity-PV would require iterating anyway to find m, so the walk is no slower (D-03-02)."
    - "Cross-validation against numpy_financial.nper for solo-helper sanity: `npf.nper(0.07/12, 65.40, -8000)` returns 214.95 -> ceil=215, matching the engine's npv_breakeven exactly. The plan-spec narrative '160 months' was wrong; numpy_financial validates the engine."
    - "Signed-Decimal field-type pattern for fields that can legitimately be negative (Money's ge=0 would block them): `Decimal = Field(strict=True, max_digits=14, decimal_places=2)` — second project use after Phase 6 D-03 RefiCashflow.amount."
    - "Cross-plan stub idiom matures: Plan 08-01 ships `evaluate()` raising NotImplementedError; Plan 08-03 replaces the single line with the real body. Identical pattern to Plan 08-02 evaluate-stub closure (Phase 4 D-08 inheritance)."

key-files:
  created: []
  modified:
    - lib/points.py
    - tests/test_points.py
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "D-03-01 (LOCKED, honored): simple_breakeven returns None for monthly_savings <= 0 (instead of raising) so the dispatcher can surface a structured warning. Mirrors Phase 4 D-11 blocked_by-via-field-not-raise convention."
  - "D-03-02 (LOCKED, honored): npv_breakeven uses month-by-month cumulative walk (NOT closed-form annuity formula). Easier to verify hand-calc; matches discrete monthly-payment cadence; supports 'first m where cum_npv >= 0' question naturally."
  - "D-03-03 (LOCKED, honored): Discount rate of 0 collapses to simple breakeven (no divergence). Verified by inline smoke (123 == 123 at 0% discount; diverge=False)."
  - "D-03-04 (LOCKED, honored): Decision dispatcher uses cum_npv_at_hold >= 0 as the buy/skip oracle. If simple_breakeven is None (negative savings), decision is forced to 'skip_points' regardless of cum_npv — explicit defensive force."
  - "D-03-05 (LOCKED, honored): from_loans mode runs build_schedule TWICE (once per Loan). _derive_monthly_savings private helper diffs monthly_pi."
  - "D-03-06 (LOCKED, honored): Phase 6 cross-phase coupling on discount_rate_annual remains DEFERRED. Phase 8 punts default to caller; single-line additive non-breaking edit when Phase 6 lands. Documented in references/points-breakeven.md (Plan 08-06)."
  - "D-03-07 (NEW, deviation Rule-2): Relaxed three Money-typed fields to signed Decimal (max_digits=14, decimal_places=2) so the documented rate-up-scenario edge case round-trips through PointsResponse. Mirrors Phase 6 D-03 RefiCashflow.amount precedent. Documented in lib/points.py PointsResponse field comments."

patterns-established:
  - "Decimal-safe ceil + ROUND_CEILING + localcontext(MONEY_CONTEXT) — composable Decimal-pure-math idiom for any project helper that needs ceiling division without going through float."
  - "Cumulative-walk NPV pattern with explicit zero-rate branch: avoid the (1+0)^k = 1 special-case at runtime; one branch for r > 0 (multiplicative discount factor), one for r == 0 (undiscounted accumulation). Saves 240 multiplications-by-1 in the zero-discount path while keeping the math identical to the closed-form."
  - "Engine-actual value pinning when plan-spec narrative disagrees with documented formula: cross-validate against an independent oracle (numpy_financial.nper here), pin the engine-actual value with deviation documentation in test docstring, defer fixture-driven SC-4 verification to Plan 08-05 with the engine-actual value substituted for the planner's incorrect 160."

requirements-completed:
  - PNTS-01
  - PNTS-02

# Metrics
duration: ~9min
completed: 2026-05-04
---

# Phase 8 Plan 03: Points Engine Summary

**Discount-points breakeven engine landed: lib.points.simple_breakeven (Decimal-safe ceil) + lib.points.npv_breakeven (cumulative-discounted-sum walk) + lib.points.evaluate (discriminated-union dispatcher reporting simple AND npv side-by-side per ROADMAP SC-4), with one Rule-2 type-contract correctness fix to allow rate-up-scenario negatives in three response fields and 2 Wave-0 xfails flipped to engine-actual values cross-validated against numpy_financial.nper.**

## Performance

- **Duration:** ~9 minutes
- **Started:** 2026-05-04T00:27:42Z
- **Completed:** 2026-05-04T00:36:27Z
- **Tasks:** 4 (all atomic, all committed)
- **Files modified:** 2 (lib/points.py 140 -> 291 lines +151 net new; tests/test_points.py 74 -> 128 lines +54 net new)
- **Files created:** 0

## Accomplishments

- Added `lib.points.simple_breakeven(points_cost: Money, monthly_savings: Money) -> int | None` — Decimal-safe `ceil(points_cost / monthly_savings)` via `to_integral_value(rounding=ROUND_CEILING)` under `localcontext(MONEY_CONTEXT)`. Returns `None` when `monthly_savings <= 0` (D-03-01: rate-up scenario surfaced as warning at response layer, not as raise). Verified via plan-spec inline smoke: 8000/65.40 -> 123, 8000/80.00 -> 100, 8000/0.00 -> None, 8000/-1.00 -> None.

- Added `lib.points.npv_breakeven(points_cost, monthly_savings, hold_months, discount_rate_annual) -> tuple[Decimal, int | None]` — cumulative-discounted-sum walk per 08-RESEARCH §5.2 documented formula. Two branches: `r > 0` uses multiplicative discount factor; `r == 0` collapses to undiscounted accumulation by mathematical identity (D-03-03 verified empirically: 123 == 123 at 0% discount, no divergence). Single `quantize_cents` at boundary; never mid-walk (Phase 1 pitfall #2 + Phase 3 D-04 inheritance). Cross-validated against `numpy_financial.nper(0.07/12, 65.40, -8000) -> 214.95 ceil=215` and the closed-form `n = -ln(1 - 8000*r/m)/ln(1+r)` -> 214.95. Engine produces 215 at 7% discount (NOT the plan-spec 160 — see Deviations section).

- Added `lib.points._derive_monthly_savings(loan_with_points, loan_without_points)` private helper for the from_loans branch (D-03-05): runs `build_schedule` on each Loan and diffs `monthly_pi`. Verified empirically: $400k @ 6.50% (no points) - $400k @ 6.25% (with points) -> monthly_savings = $65.40 exactly, matching the from_savings pinned scenario end-to-end.

- Wired `lib.points.evaluate(req)` dispatcher replacing Plan 08-01's `NotImplementedError` stub. isinstance-narrows over `PointsRequestFromSavings | PointsRequestFromLoans`. Always reports BOTH `simple_breakeven_months` AND `npv_breakeven_months` side-by-side per ROADMAP SC-4 / D-04. `diverge=True` iff both non-None AND unequal; `diverge_explanation` surfaces the gap with discount-rate citation. `decision = "buy_points"` iff `cumulative_npv_at_hold >= 0`; defensively forced to `"skip_points"` when `simple_breakeven` is None (D-03-04). `NEGATIVE_OR_ZERO_SAVINGS_<value>` warning emitted via `PointsResponse.warnings` rather than raising (D-03-01).

- Type-contract correctness fix per Rule 2 (auto-add missing critical functionality): relaxed `PointsRequestFromSavings.monthly_savings` + `PointsResponse.monthly_savings` + `PointsResponse.cumulative_npv_at_hold` from `Money` (which has `ge=0`) to `Decimal = Field(strict=True, max_digits=14, decimal_places=2)`. Plan 08-01 docstrings explicitly promised negative-savings support but the type contract inadvertently used `Money` which blocks `ge<0`. Mirrors Phase 6 D-03 `RefiCashflow.amount` precedent (which has the identical "outflows can be negative" constraint). The fix is additive — every previously-valid construction still validates; the relaxation only ENABLES previously-blocked rate-up edge cases (negative-savings paths).

- Flipped 2 of 5 Wave-0 xfails in `tests/test_points.py`:
  - `test_pnts_01_simple_breakeven_ceil_division` — 4 inline assertions covering ceil case (123), exact-division case (100), zero-savings None edge case, negative-savings None edge case.
  - `test_pnts_02_npv_breakeven_decision_dispatcher` — 2 scenarios end-to-end through `evaluate(PointsRequestFromSavings)`: zero-discount (`simple==npv==123, diverge=False, buy_points`) + 7%-discount (`simple=123, npv=215, diverge=True, buy_points` — engine-actual; cross-validated against numpy_financial.nper).

- Suite count after: **511 passed, 4 skipped, 10 xfailed** (was 509/4/12 at Plan 08-02 close; +2 net pass exactly per the 2 stub flips, -2 xfailed exactly corresponding to the flipped stubs; 0 failed; 0 errored; zero regression to Plan 08-02 baseline). 3 points xfails remain: 2 CLI stubs (`test_pnts_03_cli_*`) for Plan 08-04 + 1 SC-4 divergence-pin fixture (`test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin`) for Plan 08-05.

## Task Commits

Each task committed atomically against `main` (sequential executor; `parallelization=false`; `branching_strategy=none`; commits authored solely by repo owner per global + project CLAUDE.md):

1. **Task 1: Implement lib.points.simple_breakeven** — `de32157` (feat)
2. **Task 2: Implement lib.points.npv_breakeven** — `15f91bb` (feat)
3. **Task 3: Wire lib.points.evaluate dispatcher** — `d5c51a3` (feat)
4. **Task 4: Flip 2 Wave 0 xfails (PNTS-01 + PNTS-02 engine smoke)** — `5353354` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `lib/points.py` — added 3 module-level imports (`ROUND_CEILING`, `localcontext`, `lib.amortize.build_schedule`, `lib.money.MONEY_CONTEXT`, `lib.money.quantize_cents`); added 4 top-level definitions (`simple_breakeven`, `npv_breakeven`, `_derive_monthly_savings`, replaced `evaluate` stub body with real dispatcher); relaxed 3 field types from `Money` to signed `Decimal` per Rule-2 deviation. 140 -> 291 lines (+151 net new).
- `tests/test_points.py` — 2 xfail decorators removed, bodies replaced with real assertions; reformatted module to add `from decimal import Decimal` import. 74 -> 128 lines (+54 net new). 3 xfail decorators remaining (was 5; 2 flipped).

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|-------------|--------|--------|
| `grep -c 'def simple_breakeven' lib/points.py` | 1 | 1 | PASS |
| Smoke `simple_breakeven(8000.00, 65.40)` | 123 | 123 | PASS |
| Smoke `simple_breakeven(8000.00, -10.00)` | None | None | PASS |
| `grep -c 'def npv_breakeven' lib/points.py` | 1 | 1 | PASS |
| Smoke `npv_breakeven(8000.00, 65.40, 240, 0.000000)[1]` (zero-discount) | 123 | 123 | PASS |
| Smoke `npv_breakeven(8000.00, 65.40, 240, 0.070000)[1]` (7% discount) | 160 (planner) / **215 (engine-actual)** | 215 | DEVIATION (Rule 1; see Deviations §1) |
| Smoke `npv_breakeven(8000.00, -10.00, 120, 0.07)[1]` (negative savings) | None | None | PASS |
| `grep -c '^def evaluate' lib/points.py` | 1 | 1 | PASS |
| `grep -c 'NotImplementedError' lib/points.py` | 0 | 0 | PASS |
| Smoke `evaluate(...7%...).simple_breakeven_months / .npv_breakeven_months / .diverge / .decision` | 123 / 160 (planner) / True / buy_points | 123 / **215 (engine-actual)** / True / buy_points | DEVIATION (Rule 1; see Deviations §1) |
| `grep -c '@pytest.mark.xfail' tests/test_points.py` | 3 (was 5; 2 flipped) | 3 | PASS |
| `pytest tests/test_points.py -v --tb=short` | 2 passed, 3 xfailed | 2 passed, 3 xfailed | PASS |
| Full-suite passed count | >= 420 | 511 | PASS (well above target) |
| Full-suite xfailed count | >= 9 | 10 | PASS |
| Full-suite failed count | 0 | 0 | PASS |
| Full-suite errored count | 0 | 0 | PASS |
| `mypy --strict lib/points.py` | clean | Success: no issues | PASS |
| `ruff check lib/points.py` | clean | All checks passed | PASS |
| `ruff format --check lib/points.py` | clean | 1 file already formatted | PASS |

## Decisions Made

D-03-01..D-03-06 LOCKED decisions from plan frontmatter all honored verbatim. One NEW decision added inline as Rule-2 correctness fix:

- **D-03-07 (NEW, deviation Rule-2):** Relaxed three response/request fields from `Money` (ge=0) to signed `Decimal` (max_digits=14, decimal_places=2) so the documented rate-up-scenario edge case round-trips through `PointsResponse`. Plan 08-01 docstrings explicitly say "Negative monthly_savings is ALLOWED at construction" but used the project-wide `Money` type which blocks negatives at the Pydantic boundary. Mirrors Phase 6 D-03 `RefiCashflow.amount` ("NOT Money — Money's ge=0 would block negative outflows") precedent. The `npv_breakeven` function signature was also relaxed (`monthly_savings: Decimal`, `-> tuple[Decimal, int | None]`) for documentation accuracy — `Money` was misleading because the function legitimately produces negatives in the rate-up branch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan-spec acceptance value '160 months at 7% discount' is mathematically incorrect; engine produces 215**

- **Found during:** Task 2 hand-verification of the plan's Task-2 acceptance smoke `npv_breakeven(8000.00, 65.40, 240, 0.070000)`
- **Issue:** The plan frontmatter Task 2 acceptance criterion + Task 3 acceptance smoke + Task 4 flipped-test acceptance ALL pin `npv_breakeven_months == 160` for the 7%-discount case. The 08-RESEARCH §5.4 narrative also lists "Year 14 cum_npv ≈ +$430" supporting the 160-month claim. But the documented §5.2 formula `cum_npv(m) = sum_{k=1..m} monthly_savings/(1+r_monthly)^k - points_cost` produces 215 months, not 160, for these parameters. Cross-validated three ways:
  1. **Engine implementation (this commit):** walks month-by-month per §5.2 formula -> first m where cum_npv >= 0 is m=215 (cum_npv at m=215 is +$0.98; at m=214 is -$17.75).
  2. **numpy_financial.nper:** `npf.nper(0.07/12, 65.40, -8000) = 214.9476` -> ceil = 215.
  3. **Closed-form annuity:** `n = -ln(1 - 8000*r/65.40)/ln(1+r)` at `r = 0.07/12` -> 214.95 -> ceil = 215.
  All three independent oracles agree: the plan's 160 is wrong by ~55 months. The 08-RESEARCH §5.4 cum_npv values (Year 14 ≈ +$430) are also internally inconsistent with the §5.2 formula they purport to compute (engine actual at Year 14 = -$1008.34, not +$430).
- **Fix:** Implemented the engine using the §5.2 documented formula (which is the mathematically correct one); pinned engine-actual value 215 in Task 4's `test_pnts_02_npv_breakeven_decision_dispatcher`. Added explicit docstring comment in the test explaining the deviation and citing the three independent cross-validations. Decision-dispatcher logic still produces `decision='buy_points'` because hold_period_months=240 > 215 means `cum_npv_at_hold = +$435.46 >= 0`. The plan's substantive intent (divergence pin: `simple != npv` at 7% discount) is preserved; only the magnitude of the divergence changes (planner: 37 months gap; actual: 92 months gap).
- **Files modified:** `lib/points.py` (Task 2: npv_breakeven implementation), `tests/test_points.py` (Task 4: pinned 215).
- **Verification:** Three independent oracles (engine walk, numpy_financial.nper, closed-form annuity) all agree on 215. Documented in commit messages for Tasks 2-4 and in the test docstring.
- **Committed in:** `15f91bb` (Task 2), `d5c51a3` (Task 3), `5353354` (Task 4).
- **Plan deviation rule:** Rule-1 bug — plan-spec acceptance value contradicts the documented formula; engine ships the correct math; tests pin the engine-actual value. The downstream impact: Plan 08-05 will need the same engine-actual value (215, not 160) for the SC-4 divergence-pin fixture; Plan 08-06 reference doc divergence-example table also needs the engine-actual value (or a different parameter pairing that ACTUALLY produces a 37-month gap if that gap is desired narratively). Pre-emptive flag added to the SC-4 xfail-stub docstring in `tests/test_points.py:test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin` so Plan 08-05 author sees the engine-actual value.

**2. [Rule 2 - Missing critical functionality] Plan 08-01 type contract blocks the documented negative-savings edge case at the Pydantic boundary**

- **Found during:** Task 3 (smoke-testing the from_loans rate-up scenario through evaluate)
- **Issue:** Plan 08-01 ships three Pydantic fields typed as `Money` (which has `ge=Decimal("0")` per `lib/models.py:25`):
  - `PointsRequestFromSavings.monthly_savings` — but the field comment + class docstring explicitly say "may be negative for rate-up scenarios; engine warns".
  - `PointsResponse.monthly_savings` — echoed; for from_loans rate-up, this WILL be negative.
  - `PointsResponse.cumulative_npv_at_hold` — for negative-savings paths, this monotonically decreases from `-points_cost` and stays negative.
  Constructing any of these with a negative value raises `ValidationError` at the Pydantic boundary, so the dispatcher branch that's supposed to surface the warning never reaches the warning line — the rate-up scenario `evaluate()` call itself fails with a Pydantic error instead of returning a `PointsResponse(decision='skip_points', warnings=['NEGATIVE_OR_ZERO_SAVINGS_-132.94'])`. This contradicts D-03-01 ("D-03-01 mirrors Phase 4 D-11 blocked_by-via-field-not-raise convention"): the engine is supposed to surface the negative-savings condition as a structured warning, not to fail at Pydantic validation.
- **Fix:** Relaxed the three field types from `Money` to `Decimal = Field(strict=True, max_digits=14, decimal_places=2)`. The decimal-place + max-digit constraints are preserved (no precision loss); only the `ge=0` constraint is dropped. Mirrors Phase 6 D-03 `RefiCashflow.amount` precedent (line 1 in `lib/refinance.py` D-03 LOCKED DECISION: "amount: Decimal (max_digits=14, decimal_places=2; NOT Money — Money's ge=0 would block negative outflows)"). Also relaxed `npv_breakeven` signature (`monthly_savings: Decimal` and return tuple type) for documentation accuracy. Documented inline in the field comments and in commit message for Task 3.
- **Files modified:** `lib/points.py` (Task 3 only — both request + response models + npv_breakeven signature).
- **Verification:** All five dispatcher branches now round-trip cleanly:
  - from_savings + 7% positive savings -> simple=123, npv=215, diverge=True, buy_points
  - from_savings + 0% positive savings -> simple=123, npv=123, diverge=False, buy_points
  - from_savings + negative savings -> None/None, skip_points + warning
  - from_loans + positive savings (6.50% no-points vs 6.25% with-points) -> identical to from_savings 7%
  - from_loans + rate-up (7.00% no-points vs 6.50% with-points; "with-points" is HIGHER) -> None/None, skip_points + warning, monthly_savings=-132.94 echoed
  Pre-fix, branches 3 and 5 raised `ValidationError`. Post-fix, all five produce well-formed `PointsResponse` objects.
- **Committed in:** `d5c51a3` (Task 3).
- **Plan deviation rule:** Rule-2 missing-critical-functionality — D-03-01 documents an engine behavior (warn-not-raise) that the plan's own type contract makes impossible. The fix is additive (every previously-valid construction still validates; only previously-blocked rate-up paths newly succeed) and follows an established project precedent (Phase 6 D-03). No semantic change to D-03-01..D-03-06; D-03-07 (this fix) is recorded as a NEW locked decision in the SUMMARY frontmatter for downstream traceability.

**3. [Rule 3 - Hygiene] PT018 compound-assert split + ruff format auto-applied**

- **Found during:** Task 3 ruff check after the dispatcher body landed
- **Issue:** The dispatcher's mypy-narrowing assertion `assert simple_m is not None and npv_m is not None  # mypy narrow` tripped ruff PT018 ("assertion should be broken down into multiple parts") — same hygiene class as Plan 08-02 deviation #1 third sub-bullet. Additionally, the relaxed `cumulative_npv_at_hold` field declaration exceeded the ruff line-length budget on a single line and was auto-formatted to a multi-line `Field(...)` call.
- **Fix:** Split the compound assert into two single-condition asserts (preserves the mypy narrowing semantics; both branches still flow into the `gap = npv_m - simple_m` line with both names narrowed to non-None). Ran `ruff format` to apply the auto-applied multi-line `Field(...)` call hygiene.
- **Files modified:** `lib/points.py` (Task 3).
- **Verification:** `ruff check lib/points.py` -> All checks passed; `ruff format --check lib/points.py` -> 1 file already formatted; `mypy --strict lib/points.py` -> Success: no issues.
- **Committed in:** `d5c51a3` (Task 3) — final committed shape includes the split + format.
- **Plan deviation rule:** Rule-3 hygiene-only — formatting/lint fix that doesn't change behavior. Same root cause as Plan 08-02 deviation #1's PT018 split; project-wide ruff config consistently flags compound asserts.

**4. [Rule 3 - Hygiene] Removed extraneous backslash-escape in test docstring**

- **Found during:** Task 4 `pytest tests/test_points.py` (Python SyntaxWarning at collection time: `invalid escape sequence '\$'`)
- **Issue:** The flipped `test_pnts_02_npv_breakeven_decision_dispatcher` docstring used `\$430` and `\$435.46` to escape dollar signs in a `\$NNN` pattern. Inside a regular Python string, `\$` is not a valid escape sequence in Python 3.12+ (Python 3.6+ deprecated, 3.12+ warns). The dollar sign needs no escaping; `$430` is just a literal string.
- **Fix:** Replaced both `\$` occurrences with plain `$`.
- **Files modified:** `tests/test_points.py` (Task 4 follow-up edit; squashed into the same Task 4 commit `5353354`).
- **Verification:** `pytest tests/test_points.py -v` -> 2 passed, 3 xfailed, no warnings.
- **Committed in:** `5353354` (Task 4) — final committed shape.
- **Plan deviation rule:** Rule-3 hygiene-only — Python SyntaxWarning class. No semantic impact on the test assertions.

---

**Total deviations:** 4 auto-fixed (1 Rule-1 plan-spec math bug spanning Tasks 2-4 [pin engine-actual 215 vs planner-claimed 160]; 1 Rule-2 missing critical functionality at the type-contract layer [Money -> signed Decimal on three fields]; 2 Rule-3 hygiene-only fixes [PT018 split + format; backslash-escape SyntaxWarning]). No Rule-4 cases triggered (no architectural decisions deferred to user).

**Impact on plan:** No semantic change to D-03-01..D-03-06 LOCKED decisions; all six honored verbatim. ONE new locked decision added (D-03-07 type relaxation; mirrors Phase 6 D-03 precedent). The math layer is mathematically correct (cross-validated three ways against numpy_financial.nper + closed-form annuity). The plan's 160-month claim was wrong; the engine ships 215 — Plan 08-05 author MUST use the engine-actual value (215) when authoring the SC-4 divergence-pin fixture, OR pick a different parameter pairing that genuinely produces a 37-month gap (e.g., a much lower discount rate ~0.04). Pre-emptive flag added to the SC-4 xfail-stub docstring in `tests/test_points.py:test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin` so Plan 08-05 sees the engine-actual gap of 92 months. Plan 08-06 reference-doc divergence-example table will face the same choice (re-pin 215, or re-parameter to genuinely produce 37); a one-line update to `references/points-breakeven.md` per the engine-actual-value path closes both with full traceability.

## Issues Encountered

None blocking. All 4 deviations resolved inline within the same task they were discovered. Pre-commit hooks (ruff legacy + ruff format + mypy + check yaml + block-user-layer) ran on every commit and passed.

## Threat Flags

None — Plan 08-03 is a pure-engine plan with no new network surface, no auth boundaries, no schema persistence (DuckDB lands Phase 9), no file I/O. The plan frontmatter has no `<threat_model>` block, which is correct for a pure-math plan. The Rule-2 type-contract relaxation does NOT introduce any new attack surface — the `max_digits=14 + decimal_places=2 + strict=True` constraint is preserved; only the `ge=0` lower bound is dropped, which is necessary for the documented rate-up-scenario edge case.

## Known Stubs

None ship in this plan. Plan 08-01's `lib.points.evaluate()` NotImplementedError stub is now RESOLVED by Task 3's dispatcher body. The remaining 3 xfailed tests in `tests/test_points.py` are intentionally-deferred Wave-0 stubs awaiting Plans 08-04 (CLI; 2 stubs) and 08-05 (SC-4 divergence-pin fixture; 1 stub). Per Plan 08-04 and Plan 08-05 frontmatter requirements, those will flip in their respective waves.

## Cross-wave Dependency Notes (forward)

- **Plan 08-04 (CLIs, Wave 4)** is unblocked at the engine surface: `scripts/points_breakeven.py` calls `lib.points.evaluate(req)` after `TypeAdapter(PointsRequest).validate_json(...)`. The engine is fully operational. The 2 CLI xfails in `tests/test_points.py` (`test_pnts_03_cli_points_subprocess_round_trip` + `test_pnts_03_cli_help_does_not_import_lib_points_and_rejects_float`) remain Wave 0 stubs awaiting Plan 08-04. PNTS-03 contract preserved: `discount_rate_annual` REMAINS REQUIRED with no CLI default per Plan 08-04 D-04-05 advisory (deferred-coupling boundary stays at the model layer; Phase 6 lifts the default in a future single-line additive edit).

- **Plan 08-05 (fixtures + tests, Wave 5)** is unblocked at the engine surface for the points fixtures (3 of 14 total): `points_simple_eq_npv_zero_discount.json` (zero-discount no-divergence — engine pin: simple==npv==123), `points_simple_lt_npv_seven_pct_discount.json` (SC-4 divergence-pin — engine pin: simple=123, npv=215, gap=92 months), `points_negative_savings_warning.json` (rate-up scenario — engine pin: None/None + warning). **CRITICAL pre-emptive flag for Plan 08-05 author:** the plan-spec value of `160 months` for the 7%-discount divergence-pin fixture is mathematically wrong. Use **215** (engine-actual; cross-validated three ways) OR re-parameter the fixture (e.g., reduce discount_rate_annual to ~0.04 to genuinely produce a ~37-month gap). The xfail-stub docstring in `tests/test_points.py:test_sc4_simple_vs_npv_diverge_at_seven_pct_discount_pin` has been pre-updated to "92 months" — Plan 08-05 author should match this OR re-parameter. The same flag applies to Plan 08-06 reference-doc divergence-example table.

- **Phase 6 (Refinance NPV) deferred coupling** remains UNCHANGED from Plan 08-01 SUMMARY's notes: `PointsRequest.discount_rate_annual` REMAINS REQUIRED with no module default. When Phase 6 lands, an additive non-breaking edit to `lib/points.py` adds the project-wide default; no Phase 8 plan needs to be re-executed. Documented in `references/points-breakeven.md` (Plan 08-06).

## Next Phase Readiness

- **Plan 08-04 (CLIs, Wave 4)** is unblocked: engine surface stable; the CLI just wraps `lib.points.evaluate(req)` and assembles the JSON-in/JSON-out envelope.
- **Plan 08-05 (fixtures + tests, Wave 5)** is unblocked at the engine surface for the 3 points fixtures; SEE the CRITICAL pre-emptive flag above re: 160 vs 215 for the SC-4 divergence-pin.
- REQUIREMENTS.md PNTS-01 + PNTS-02 transition Pending -> Done at the math layer; PNTS-03 (CLI) remains Pending pending Plan 08-04.
- ROADMAP SC-4 (simple AND NPV-based decision side-by-side, divergence documented with a fixture) remains pending fixture closure in Plan 08-05 — the engine layer is fully wired.
- The 8 remaining Phase-8 xfails in the suite (10 total - 2 inherited Phase 5 ARM oracle) are: 2 points CLI (Plan 08-04) + 1 SC-4 divergence-pin fixture (Plan 08-05) + 4 stress CLI (Plan 08-04) + 1 SC-5 size-budget fixture (Plan 08-05) + 1 stress envelope-uniformity (Plan 08-04) — actually that's 9 total minus 1 inherited Phase 5 ARM oracle = 9 Phase-8 + 1 Phase-5 = 10 total xfails matching the actual count.

## Self-Check: PASSED

Verified at execution end:

- [x] `lib/points.py` modified across 3 task commits (`git log --oneline | grep -E 'de32157|15f91bb|d5c51a3'` -> all three present)
- [x] `tests/test_points.py` modified (`git log --oneline | grep 5353354` -> present)
- [x] All four task commits (de32157, 15f91bb, d5c51a3, 5353354) reachable from `main`
- [x] Full suite: 511 passed / 4 skipped / 10 xfailed / 0 failed / 0 errored (+2 / -2 vs Plan 08-02 baseline of 509/4/12)
- [x] `mypy --strict lib/points.py` clean
- [x] `ruff check lib/points.py` clean
- [x] `ruff format --check lib/points.py` clean
- [x] `grep -c 'NotImplementedError' lib/points.py` returns 0 (Plan 08-01 stub resolved)
- [x] `grep -c '@pytest.mark.xfail' tests/test_points.py` returns 3 (was 5; 2 flipped exactly per plan)
- [x] `grep -c 'def simple_breakeven' lib/points.py` returns 1
- [x] `grep -c 'def npv_breakeven' lib/points.py` returns 1
- [x] `grep -c '^def evaluate' lib/points.py` returns 1
- [x] All inline smoke tests reproduce the documented engine-actual values:
  - simple_breakeven(8000, 65.40) = 123
  - npv_breakeven(8000, 65.40, 240, 0.0) = (7696.00, 123)  # zero-discount; matches simple
  - npv_breakeven(8000, 65.40, 240, 0.07) = (435.46, 215)  # engine-actual; cross-validated against numpy_financial.nper
  - npv_breakeven(8000, -10.00, 120, 0.07) = (-8861.26, None)  # rate-up; never crosses
  - evaluate(from_savings 7%) -> (123, 215, True, buy_points)  # engine-actual
  - evaluate(from_loans 7%) -> identical to from_savings 7%  # round-trip via _derive_monthly_savings
  - evaluate(from_loans rate-up) -> (None, None, False, skip_points, warning)  # negative-savings path

---
*Phase: 08-stress-points*
*Completed: 2026-05-04*
