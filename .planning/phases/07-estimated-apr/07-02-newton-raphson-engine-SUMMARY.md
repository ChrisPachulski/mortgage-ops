---
phase: 07-estimated-apr
plan: 02
subsystem: solver-engine
tags:
  - phase-07
  - estimated-apr
  - newton-raphson
  - reg-z-appendix-j
  - sc-1-anchor
  - sc-3-anchor

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "lib/money.MONEY_CONTEXT (prec=28) + lib/money.quantize_cents + lib/money.quantize_rate + Decimal-from-string discipline"
  - phase: 02-rules-predicates
    provides: "lib/rules/reg_z.within_apr_tolerance + TOLERANCE_REGULAR (Decimal('0.00125') = 1/8 pp) consumed by tolerance_check dict"
  - phase: 07-estimated-apr (Plan 07-01)
    provides: "lib/apr.APRRequest + APRResponse + AdvanceScheduleEntry + PaymentScheduleEntry + solve_apr stub raising NotImplementedError"
provides:
  - "lib/apr.py — Newton-Raphson solver body + 4 helper functions + APRConvergenceError exception class + 3 module-level constants"
  - "lib/apr._decimal_pow(base, exponent) — Decimal-power via ln/exp under MONEY_CONTEXT for fractional exponents (D-13)"
  - "lib/apr._unit_period_equation(advances, payments, i) — f(i) per Reg Z Appendix J §(b)"
  - "lib/apr._derivative(advances, payments, i) — closed-form f'(i) for Newton iteration"
  - "lib/apr._seed_apr(advance_schedule, payment_schedule) — npf.rate seed with NaN/range fallback (D-11)"
  - "lib/apr.APRConvergenceError — ValueError subclass; carries iterations + last_residual + last_i for caller debugging (D-12)"
  - "lib/apr.solve_apr — Newton-Raphson body in pure Decimal under MONEY_CONTEXT; D-10 dual-criterion convergence (rate <= 0.00001 AND residual <= 0.01); MAX_ITER 50 cap"
  - "3 Wave-0 stubs flipped to PASS: test_apr_solver_seeded_from_npf_rate, test_apr_solver_converges_within_decimal_00001_tolerance, test_apr_solver_raises_on_non_convergence"
affects:
  - 07-03-odd-first-period-helpers
  - 07-04-cli
  - 07-05-fixtures-and-reg-z-anchor
  - 07-06-references-doc
  - 07-07-ffiec-fixtures

# Tech tracking
tech-stack:
  added:
    - "numpy_financial.rate — seed for Newton-Raphson (regular-transaction approximation; APR-02)"
  patterns:
    - "Decimal-context Newton iteration with localcontext(MONEY_CONTEXT) wrapper (Phase 4 evaluate_reverse + Phase 3 _build_fixed_monthly per-period idiom generalized to root-finder)"
    - "Pure-Decimal iteration with Decimal(str(float)) cast at the seed boundary ONCE (D-11; closest sibling: lib/affordability.py:1045 npf.pv seed pattern)"
    - "Dollar-residual sanity gate alongside rate-tolerance (D-10 dual criterion; defense-in-depth per RESEARCH OPEN Q2)"
    - "ValueError subclass for solver failure surfaces via 6-key envelope (Phase 4 D-13 inheritance)"
    - "ASCII hyphen-minus in docstring math expressions to satisfy ruff RUF002 (no unicode minus signs)"
    - "Auto-fix pattern: catch internal-helper ValueError + bound-check next iterate to convert solver-domain blow-ups into APRConvergenceError signals"

key-files:
  created: []
  modified:
    - lib/apr.py
    - tests/test_apr.py

key-decisions:
  - "D-09 honored: Newton iteration runs under localcontext(MONEY_CONTEXT) (prec=28); no custom prec=50 escalation (RESEARCH §Q(h) confirms 28 sufficient)"
  - "D-10 honored: dual-criterion convergence — abs(i_next - i) <= TOLERANCE (Decimal('0.00001')) AND abs(f(i)) <= DOLLAR_RESIDUAL (Decimal('0.01')) — both must hold"
  - "D-11 honored: seed via npf.rate (float); cast Decimal(str(...)) ONCE at boundary; Newton iterate stays Decimal — verified by mypy --strict no-float-leak in iteration"
  - "D-12 honored: MAX_ITER = 50 module-level constant; APRConvergenceError(ValueError) raised on breach with iterations + last_residual + last_i for debugging"
  - "D-13 honored: _decimal_pow uses (base.ln() * exponent).exp() for fractional exponents; negative-base raises ValueError"
  - "D-14 honored: solve_apr quantizes final APR via quantize_rate(i * unit_periods_per_year) ONCE at end (Phase 5 D-14 inheritance)"
  - "Auto-fix [Rule 2 / Rule 3]: catch ValueError from _decimal_pow during Newton iteration + bound-check next iterate to convert non-convergent (1+i)<=0 paths into clean APRConvergenceError signals (vs raw Decimal-domain errors); pre-iteration seed sanity also bounds-checks"

patterns-established:
  - "First iterative root-finder in mortgage-ops; module-level TOLERANCE/DOLLAR_RESIDUAL/MAX_ITER constants pin SC-1 + SC-3 anchors at the engine boundary"
  - "Dual-criterion convergence (rate AND dollar residual) prevents the 'rate stalled, residual huge' edge case (Phase 7-invented, RESEARCH OPEN Q2)"
  - "Seed-with-fallback pattern: npf.rate -> nominal-rate-of-return -> 0.005 last-resort (RESEARCH §Q(c))"
  - "Domain-error-as-non-convergence: Newton iterates that wander to (1+i)<=0 are caught and converted to APRConvergenceError (the equation is undefined there; this is non-convergence, not a programmer bug)"

requirements-completed:
  - APR-01  # lib/apr.py Newton-Raphson solver body shipped (model surface from Plan 07-01 + body from this plan)
  - APR-02  # Newton-Raphson seeded from npf.rate with NaN/range fallback (_seed_apr)
  - APR-03  # Convergence tolerance Decimal("0.00001") (TOLERANCE constant + dual-criterion D-10)

# Metrics
duration: 8min 21s
completed: 2026-05-03
---

# Phase 7 Plan 2: Newton-Raphson Engine Summary

**Reg Z Appendix J Newton-Raphson APR solver shipped: `_decimal_pow` + `_unit_period_equation` + `_derivative` + `_seed_apr` + `APRConvergenceError` + `solve_apr` body — pure Decimal iteration under `MONEY_CONTEXT.prec=28` with the D-10 dual-criterion convergence (rate <= `Decimal("0.00001")` AND residual <= `Decimal("0.01")`) and the D-12 `MAX_ITER = 50` hard cap. SC-1 anchor verified ($5000 / 36 / $166.07 → 0.119994 within `Decimal("0.00001")` of 12.00% in 1 iteration). 3 Wave-0 stubs flipped (full suite 469 passed / 10 xfailed; +3 net pass over Plan 07-01 baseline).**

## Performance

- **Duration:** 8 min 21 s
- **Started:** 2026-05-03T20:06:57Z
- **Completed:** 2026-05-03T20:15:18Z
- **Tasks:** 7 (all atomically committed; no checkpoints, no human action)
- **Files modified:** 2 (lib/apr.py +263 lines; tests/test_apr.py flipped 3 stubs)
- **Files created:** 0

## Accomplishments

- Shipped the full Reg Z Appendix J Newton-Raphson solver in `lib/apr.py`: 6 expected callables/classes (`_decimal_pow`, `_unit_period_equation`, `_derivative`, `_seed_apr`, `APRConvergenceError`, `solve_apr`) plus 3 module-level constants (`TOLERANCE`, `DOLLAR_RESIDUAL`, `MAX_ITER`)
- Replaced the Wave 1 `solve_apr` `NotImplementedError` stub with a full Newton-Raphson body running in `localcontext(MONEY_CONTEXT)` (prec=28) — pure Decimal iteration, D-10 dual-criterion convergence, D-12 50-iteration cap, D-14 single `quantize_rate` at the end
- **SC-1 anchor verified end-to-end:** Reg Z Appendix J Example J-1 ($5000 / 36 / $166.07) → `Decimal("0.119994")` in 1 iteration, within `Decimal("0.00001")` of the regulatory 12.00% (diff = `Decimal("0.000006")`)
- **SC-3 anchor verified:** the Reg Z anchor + ill-conditioned non-convergence case both respect the `MAX_ITER = 50` cap; `APRConvergenceError` raised correctly on the non-convergence path
- Flipped 3 Wave-0 stubs to real assertions: `test_apr_solver_seeded_from_npf_rate` (APR-02 contract), `test_apr_solver_converges_within_decimal_00001_tolerance` (SC-1 anchor), `test_apr_solver_raises_on_non_convergence` (APRConvergenceError contract)
- **Suite count after:** 469 passed (was 466; +3 from flipped stubs) / 4 skipped / 10 xfailed (was 13; -3 flipped) — zero regression to Plan 07-01 baseline

## Task Commits

Each task committed atomically against `main` (sequential executor; no branching per `parallelization=false`; no AI attribution per global + project CLAUDE.md):

1. **Task 1: Add `_decimal_pow` helper** — `82e3017` (feat)
2. **Task 2: Add `_unit_period_equation` f(i)** — `34b4d07` (feat)
3. **Task 3: Add `_derivative` f'(i) closed-form** — `f275180` (feat)
4. **Task 4: Add `_seed_apr` with npf.rate fallback** — `d815be0` (feat)
5. **Task 5: Add `APRConvergenceError` ValueError subclass** — `6104485` (feat)
6. **Task 6: Implement `solve_apr` Newton-Raphson body** — `609caf7` (feat)
7. **Task 7: Flip 3 Wave-0 stubs** — `1d4385f` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `lib/apr.py` (modified, 380 → 642 lines, +263) — added 3 module-level constants + 4 helper functions + 1 exception class + replaced `solve_apr` stub body with full Newton-Raphson iteration; module docstring updated to reflect Wave 2 status (NotImplementedError reference removed)
- `tests/test_apr.py` (modified, 203 → 318 lines, +118/-11) — added imports (`Decimal`, `date`, `numpy_financial as npf`, `lib.apr` symbols, `lib.models.Loan`), flipped 3 xfail-strict stubs to real assertions

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|-------------|--------|--------|
| `grep -c 'def _unit_period_equation' lib/apr.py` | 1 | 1 | PASS |
| `grep -c 'def _derivative' lib/apr.py` | 1 | 1 | PASS |
| `grep -c 'def _seed_apr' lib/apr.py` | 1 | 1 | PASS |
| `grep -c 'def _decimal_pow' lib/apr.py` | 1 | 1 | PASS |
| `grep -c 'class APRConvergenceError' lib/apr.py` | 1 | 1 | PASS |
| `grep -c 'NotImplementedError' lib/apr.py` | 0 | 0 | PASS |
| `wc -l lib/apr.py` (>= 450) | >= 450 | 642 | PASS |
| `mypy --strict lib/apr.py` | clean | clean | PASS |
| `ruff check lib/apr.py` | clean | clean | PASS |
| `ruff format --check lib/apr.py` | clean | clean | PASS |
| `pytest tests/test_apr.py::test_apr_solver_seeded_from_npf_rate -v` | PASS | PASS | PASS |
| `pytest tests/test_apr.py::test_apr_solver_converges_within_decimal_00001_tolerance -v` | PASS (or xfail-stays if Wave 5 anchor not yet shipped) | PASS (inline temp-fixture per plan permission) | PASS |
| `pytest tests/test_apr.py::test_apr_solver_raises_on_non_convergence -v` | PASS | PASS | PASS |
| Full-suite `pytest` | >= 461 (executor floor) | 469 passed / 4 skipped / 10 xfailed / 0 failed / 0 errors | PASS |
| Plan Acceptance Rule-2 (math): SC-1 anchor (Reg Z Appendix J Example J-1) returns 12.00% APR within `Decimal("0.00001")` | within 0.00001 | got 0.119994; diff=0.000006 (within tolerance) | PASS |

## Decisions Made

None novel — followed the plan's 6 LOCKED DECISIONS (D-09 through D-14) verbatim. Several smoke-test invariants were validated empirically before each commit:

- After Task 1: `_decimal_pow(1.01, 36)` ≈ 1.4307688; `_decimal_pow(1.01, -36)` ≈ 0.6989249; negative-base raises ValueError
- After Task 2: `f(0.005)=-458.89`, `f(0.01)=0.046`, `f(0.02)=767.07` — monotonically increasing through the root; `f(0.01)` essentially zero (anchor confirmation at the seed level)
- After Task 3: closed-form `f'(0.01)=86278.82` matches numerical-difference derivative at relative-error 1e-12
- After Task 4: `_seed_apr` for the Reg Z anchor returns 0.0099994 (matches direct `npf.rate(36,-166.07,5000,0)` to 1e-12 ULP-drift)
- After Task 5: `APRConvergenceError` instance subclasses `ValueError`, carries `iterations`/`last_residual`/`last_i` attributes
- After Task 6: SC-1 anchor end-to-end (`solve_apr` → 0.119994 in 1 iteration); ill-conditioned input raises `APRConvergenceError`; `disclosed_apr=0.12` populates `tolerance_check` with `within_tolerance=True`
- After Task 7: 4 of 13 stubs PASS (1 from Wave 1 + 3 from Wave 2); remaining 9 stay xfail-strict per plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Hygiene] Replace unicode minus signs in `_derivative` docstring with ASCII hyphen-minus**

- **Found during:** Task 3 (immediately after writing the function body verbatim from the plan spec)
- **Issue:** The plan's task code block uses unicode MINUS SIGN (U+2212 `−`) in the docstring math expression. ruff RUF002 flags it as "ambiguous unicode character in docstring". The character would silently confuse readers (and grep'd math-text searchers) without changing semantics.
- **Fix:** Rewrote the docstring math using ASCII characters: `sum`, `*`, `-`, `^`. The math expressions remain readable and grep-friendly without unicode hazards.
- **Files modified:** `lib/apr.py`
- **Verification:** `ruff check lib/apr.py` clean post-fix
- **Committed in:** `f275180` (Task 3)
- **Plan deviation rule:** Rule-3 (hygiene only — formatting/lint fixes that do not change semantics). Plan's Deviation Rules: "Rule-3: hygiene only".

**2. [Rule 2 — Missing critical functionality] Convert `_decimal_pow` ValueError-during-Newton into `APRConvergenceError` + bound-check next iterate**

- **Found during:** Task 6 smoke test (constructed an ill-conditioned non-convergence input → solver crashed with raw `ValueError: _decimal_pow requires positive base; got -7.45`)
- **Issue:** The plan's `solve_apr` body block did not handle the case where Newton-Raphson wanders into a region where `(1+i) <= 0`. In that region the unit-period equation is mathematically undefined; the next call to `_decimal_pow` raises `ValueError`. The plan calls for `APRConvergenceError` on non-convergence, so callers should see *that* exception (with iteration count + last residual for debugging), not a raw `ValueError` about the helper function's internals. This is a non-convergence signal that needs a clean exception, not a programmer bug.
- **Fix:** Wrapped the per-iteration `_unit_period_equation`/`_derivative` calls in `try/except ValueError` and re-raised as `APRConvergenceError(iterations=n, last_residual=abs(f_val), last_i=i) from exc`. Also added a guard `if i_next <= Decimal("-1"): raise APRConvergenceError(...)` BEFORE the next iteration so the failure mode is detected proactively. Pre-iteration seed sanity check `if i <= Decimal("-1"): raise APRConvergenceError(iterations=0, ...)` covers the (very unlikely) case where the seed itself is degenerate.
- **Files modified:** `lib/apr.py` (Task 6 commit)
- **Verification:** ill-conditioned input ($5000 advances vs $36 total payments) now raises `APRConvergenceError(iterations=1, ...)` cleanly; `test_apr_solver_raises_on_non_convergence` (Task 7) PASSES asserting this contract
- **Committed in:** `609caf7` (Task 6; the deviation lives entirely in this commit)
- **Plan deviation rule:** Rule-2 (auto-add missing critical functionality — the contract `APRConvergenceError` on ill-conditioned input was specified by the plan but the plan's task-code block did not actually catch the helper-function ValueError that fires before the iteration check would). The plan's Test 7 explicitly says "construct a deliberately ill-conditioned APRRequest (e.g., advances summing to 0; or payments summing to less than advances → no positive-rate solution); assert `pytest.raises(APRConvergenceError)`" — which means the contract was expected; only the precise call-path (helper-ValueError vs in-loop divergence) was unspecified. The fix wires the contract to its actual failure path.

**3. [Rule 3 — Hygiene] Update module docstring to reflect Wave 2 ships the body**

- **Found during:** Task 6 (acceptance gate `grep -c 'NotImplementedError' lib/apr.py` returned 1 instead of 0)
- **Issue:** The Wave 1 module docstring described the file as "ships ONLY the Pydantic v2 boundary models ... plus a `solve_apr` stub that raises NotImplementedError". The acceptance gate explicitly requires zero `NotImplementedError` references. The remaining hit was inside the Wave 1 historical narrative.
- **Fix:** Rewrote the Wave-1-narrative paragraph to describe both Plan 07-01 (model surface) and Plan 07-02 (this commit set: helpers + body + APRConvergenceError). Removed the `NotImplementedError` mention.
- **Files modified:** `lib/apr.py`
- **Verification:** `grep -c 'NotImplementedError' lib/apr.py` → 0
- **Committed in:** `609caf7` (Task 6 commit, alongside the body replacement)
- **Plan deviation rule:** Rule-3 (hygiene — docstring text update; no semantic change to behavior).

**4. [Rule 3 — Hygiene] Trim test-file imports + remove erroneous `noqa: ARG001` directives + auto-organize import block**

- **Found during:** Task 7 (after writing the three test-flip bodies, ruff caught: (a) the `apr_fixture` parameter IS used in `test_apr_solver_seeded_from_npf_rate`'s and `test_apr_solver_converges_..._tolerance`'s NEW assertions even though I had pre-emptively added `# noqa: ARG001`; (b) the import block was not in canonical isort order)
- **Issue:** I added `# noqa: ARG001` to the still-`apr_fixture`-typed parameters anticipating they'd be unused (the inline temp-fixture variant of the SC-1 test does not actually consume `apr_fixture`); ruff RUF100 flagged the directives as unnecessary because the parameters ARE referenced... wait, actually they aren't — the SC-1 test constructs the request inline. The deviation here was the redundant-noqa false-positive that ruff resolved by stripping the directives (and the import-ordering auto-fix).
- **Fix:** `uv run ruff check --fix tests/test_apr.py` (removed 3 unnecessary `noqa` directives + reorganized imports); `uv run ruff format tests/test_apr.py` (canonical line-wrapping)
- **Files modified:** `tests/test_apr.py`
- **Verification:** `ruff check`, `ruff format --check`, `mypy --strict` all clean post-fix
- **Committed in:** `1d4385f` (Task 7 commit)
- **Plan deviation rule:** Rule-3 (hygiene only — lint-driven mechanical fixes; no semantic test change).

---

**Total deviations:** 4 auto-fixed (3 Rule-3 hygiene + 1 Rule-2 missing-critical-functionality)
**Impact on plan:** Rule-2 Deviation 2 is the only semantically-load-bearing change — it ensures the documented `APRConvergenceError` contract fires on the most-likely non-convergence failure path (Newton wandering out of the equation's domain). All other deviations are formatting/docstring/import-organization. Plan acceptance gates all PASS.

## Issues Encountered

None — all 7 tasks executed sequentially, all 4 deviations resolved inline, no checkpoints, no escalations.

## Threat Flags

None — Plan 07-02 modifies a single internal calc-engine module (`lib/apr.py`) with no new network surface, no new authentication boundaries, no new file-system access patterns, no schema changes at trust boundaries. The new code paths (`_decimal_pow`, `_unit_period_equation`, `_derivative`, `_seed_apr`, `APRConvergenceError`, `solve_apr` body) operate entirely within the Pydantic-validated input boundary (`APRRequest`) shipped in Plan 07-01. The `numpy_financial.rate` import is the one new external dependency surface, but `numpy-financial` is already a project-pinned dependency (per `pyproject.toml` and `lib/amortize.py`/`lib/affordability.py` prior usage) — no new third-party trust boundary.

## Known Stubs

The following intentional placeholder is documented for Wave 5:

- **`tests/test_apr.py:test_apr_solver_converges_within_decimal_00001_tolerance`** — uses inline-constructed `APRRequest`/`Loan`/`AdvanceScheduleEntry`/`PaymentScheduleEntry` for the Reg Z Appendix J Example J-1 inputs ($5000 / 36 monthly $166.07 / 12.00%). The plan explicitly authorizes this Wave-2-only inline variant: *"`apr_fixture("regz_appendix_j_5000_36_166_07")` (Wave 5 ships the fixture; Wave 2 can land an inline temp-fixture variant if needed for Wave-2-only verification, with a TODO comment to swap for the Wave 5 file)."* A `TODO:` comment in the test docstring (line 135) marks the swap point. Wave 5 Plan 07-05 will (a) ship `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` and (b) replace this test's inline construction with an `apr_fixture("regz_appendix_j_5000_36_166_07")` load.

No unintentional stubs introduced. No mock/placeholder data. No `FIXME` comments. The single `TODO` is documented + tracked + tied to a specific downstream wave plan.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture, no human-in-the-loop verification. All 7 tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

- **Wave 3 (Plan 07-03 odd-first-period helpers)** — unblocked. The engine already supports `unit_period_fraction` on both `AdvanceScheduleEntry` and `PaymentScheduleEntry` (Plan 07-01) and uses them correctly in `_unit_period_equation` + `_derivative` (this plan). Wave 3 just adds the `_compute_odd_first_period_fraction(origination, first_payment, day_count)` date-arithmetic helper that converts a `(origination_date, first_payment_date)` pair into a Decimal `f ∈ [0, 1)`. The engine surface needs no change.
- **Wave 4 (Plan 07-04 CLI)** — unblocked. `solve_apr` now actually returns valid `APRResponse` objects (no more `NotImplementedError`). The 6-key error envelope at the CLI boundary will pick up `APRConvergenceError` via the Phase 4 D-13 `ValueError` inheritance pattern (`type='value_error'`, `loc=['solver']`, `ctx={'class':'APRConvergenceError', 'iterations':50, 'last_residual':str(...)}`).
- **Wave 5 (Plan 07-05 Reg Z anchor + tests)** — unblocked + has a small swap to do. The Wave 2 inline-temp-fixture variant of `test_apr_solver_converges_within_decimal_00001_tolerance` should be swapped for `apr_fixture("regz_appendix_j_5000_36_166_07")` once Wave 5 lands the JSON file. Wave 5 also flips two more stubs (`test_apr_reg_z_appendix_j_worked_example_returns_12_percent` and `test_newton_raphson_iterations_under_50_for_all_fixtures`) — both of those are SC-1/SC-3 anchors that the engine already satisfies (the SC-1 anchor passes empirically in this plan's Task 6 smoke test).
- **Wave 6 (Plan 07-06 references doc)** — unblocked.
- **Wave 7 (Plan 07-07 HMDA Platform fixtures)** — unblocked. The 20+ HMDA Platform captures will exercise the multi-fixture `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` against the engine; per CONTEXT.md D-09 ("HMDA delta policy — engine is wrong"), any divergence > `Decimal("0.00001")` will fail the test.
- **APR-01 / APR-02 / APR-03 status:** all three closed by this plan (full body + npf.rate seed + dual-criterion convergence). REQUIREMENTS.md will mark them complete. Open items remaining in Phase 7: APR-04 (Wave 7), APR-05 (Wave 5), APR-06 (Wave 4 — already partially closed at Pydantic boundary in Plan 07-01), APR-07 (Wave 4), APR-08 (Wave 6).

## TDD Gate Compliance

The plan does not declare `type: tdd`; this is a vanilla `type: execute` plan. Per the executor protocol's TDD section, no RED/GREEN/REFACTOR cycle gate enforcement is required. For traceability, however: Wave 0 (Plan 07-00) shipped 13 xfail-strict stubs (RED gate); this plan flips 3 of them to passing assertions backed by working engine code (GREEN gate via Tasks 1-6 + Task 7's flips). No REFACTOR phase needed — the file was built additively, task-by-task, and never restructured.

## Self-Check: PASSED

Verified at execution end:

- [x] `lib/apr.py` exists at the path declared in plan frontmatter (`files_modified: [lib/apr.py]`) — `wc -l` = 642 (>= 450 plan minimum)
- [x] `git log --oneline | grep 82e3017` (Task 1 _decimal_pow) → present
- [x] `git log --oneline | grep 34b4d07` (Task 2 _unit_period_equation) → present
- [x] `git log --oneline | grep f275180` (Task 3 _derivative) → present
- [x] `git log --oneline | grep d815be0` (Task 4 _seed_apr) → present
- [x] `git log --oneline | grep 6104485` (Task 5 APRConvergenceError) → present
- [x] `git log --oneline | grep 609caf7` (Task 6 solve_apr body) → present
- [x] `git log --oneline | grep 1d4385f` (Task 7 stub flips) → present
- [x] All seven task commits reachable from `main`
- [x] No commit message contains "Co-Authored-By", "claude", or any AI attribution (verified by inspection of all 7 messages)
- [x] All 6 required defs/classes present: `_decimal_pow`, `_unit_period_equation`, `_derivative`, `_seed_apr`, `APRConvergenceError`, `solve_apr`
- [x] `grep -c 'NotImplementedError' lib/apr.py` → 0
- [x] Full suite: 469 passed / 4 skipped / 10 xfailed / 0 failed / 0 errors (was 466+4+13; +3 net pass from flipped stubs; zero regression to Plan 07-01 baseline of 466)
- [x] `pytest tests/test_apr.py -v`: 4 passed / 9 xfailed (was 1 passed / 12 xfailed; +3 net pass from this plan's Task 7 flips)
- [x] mypy --strict + ruff check + ruff format --check all clean on `lib/apr.py` and `tests/test_apr.py`
- [x] SC-1 anchor empirically verified: `solve_apr` on $5000 / 36 / $166.07 returns 0.119994 in 1 iteration; |actual - 12.00%| = 0.000006 (within `Decimal("0.00001")` tolerance)
- [x] SC-3 anchor empirically verified: 1 iteration <= 50 cap; APRConvergenceError raised on ill-conditioned input

---
*Phase: 07-estimated-apr*
*Completed: 2026-05-03*
