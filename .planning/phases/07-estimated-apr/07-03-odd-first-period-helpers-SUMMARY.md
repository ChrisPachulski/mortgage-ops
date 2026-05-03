---
phase: 07-estimated-apr
plan: 03
subsystem: day-count-helpers
tags:
  - phase-07
  - estimated-apr
  - day-count
  - odd-first-period
  - reg-z-1026-17-c-4
  - reg-z-appendix-j-b-5-iii

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "lib/money.MONEY_CONTEXT (prec=28) + Decimal-from-string discipline"
  - phase: 07-estimated-apr (Plan 07-01)
    provides: "lib/apr.APRRequest with day_count Literal['30/360','actual/365','actual/actual'] + odd_first_period_days int field + AdvanceScheduleEntry/PaymentScheduleEntry boundary models with unit_period_fraction"
  - phase: 07-estimated-apr (Plan 07-02)
    provides: "solve_apr Newton-Raphson body that already consumes unit_period_fraction on PaymentScheduleEntry; engine surface needed no change for Wave 3"
provides:
  - "lib/apr._compute_odd_first_period_fraction(origination, first_payment, day_count) — date-arithmetic helper for Reg Z §1026.17(c)(4) + Appendix J §(b)(5)(iii); supports 30/360 (f = (days-30)/30), actual/365 (f = (days - 365/12) / (365/12)), actual/actual (f via dateutil.relativedelta(months=1))"
  - "solve_apr now consumes APRRequest.odd_first_period_days — internally rewrites the first PaymentScheduleEntry.unit_period_fraction so the U-equation's (1+g*i) factor on the first payment carries the long odd first period (D-17)"
  - "lib/apr.py module docstring extended with Day-count conventions section + 4 new LOCKED DECISIONS (D-15..D-18)"
  - "1 new passing test: test_odd_first_period_15_days_increases_apr_above_nominal (engine smoke gate per Plan Deviation Rule 2)"
affects:
  - 07-04-cli
  - 07-05-tests-and-fixtures
  - 07-06-references-doc
  - 07-07-ffiec-fixtures
  - phase-08-stress-points (parameter sweeps over rate paths x loan amounts x points may use _compute_odd_first_period_fraction with explicit dates per D-17)

# Tech tracking
tech-stack:
  added:
    - "python-dateutil relativedelta — used by _compute_odd_first_period_fraction's actual/actual branch for month-edge-aware unit-period computation (project-wide D-07 dateutil idiom)"
  patterns:
    - "Date-arithmetic helper using dateutil.relativedelta(months=1) (carries from lib/amortize.py biweekly idiom; first usage in lib/apr.py)"
    - "Pydantic model_copy(update={...}) idiom for synthesizing a per-call rewrite of a frozen schedule entry — keeps APRRequest itself frozen while letting solve_apr inject odd_first_period_days as a unit_period_fraction"
    - "Module-docstring LOCKED DECISIONS block extended additively (D-15..D-18) — never rewrite earlier decisions"

key-files:
  created: []
  modified:
    - lib/apr.py
    - tests/test_apr.py

key-decisions:
  - "D-15 honored: _compute_odd_first_period_fraction signature matches APRRequest.day_count Literal exactly ({'30/360', 'actual/365', 'actual/actual'}); helper rejects unsupported day_count values with ValueError"
  - "D-16 honored: helper returns Decimal in [-1, 1) — short cases (negative f) accepted (engine math supports them per (1+f*i) algebra), long cases >= 1 unit period rejected (caller should insert an extra t=1 advance)"
  - "D-17 honored: APRRequest.odd_first_period_days is the user-friendly INTEGER shortcut consumed in solve_apr; advanced callers can bypass by setting unit_period_fraction directly on PaymentScheduleEntry and leaving odd_first_period_days=0"
  - "D-18 honored: 'small differences' (< 7 days for monthly) per §1026.17(c)(4) are NOT auto-zeroed — engine reports the exact fraction; caller decides"
  - "Auto-fix [Rule 2 - Missing critical functionality]: Wave 3 simplification — solve_apr's odd_first_period_days handling for actual/actual day_count uses 30 days as proxy unit_days (the request lacks origination/first_payment dates at this surface; advanced actual/actual callers use _compute_odd_first_period_fraction with explicit dates and set unit_period_fraction directly per D-17). Documented inline in solve_apr."
  - "Auto-fix [Rule 3 - Hygiene]: ruff RUF002 flagged unicode MULTIPLICATION SIGN (U+00D7) in module docstring's 'rate paths × loan amounts × points' phrase; replaced with ASCII 'x' (matches Plan 07-02 D-derivative docstring fix pattern)"

requirements-completed: []
# Plan 07-03 itself does not close any APR-XX requirement directly — APR-08
# (references doc) cites the helper in Wave 6, which is when APR-08 closes;
# Wave 5/7 fixtures cite the helper for end-to-end APR-04/APR-05 validation.

# Metrics
duration: 6min 39s
completed: 2026-05-03
---

# Phase 7 Plan 3: Odd-First-Period Helpers Summary

**Reg Z §1026.17(c)(4) + Appendix J §(b)(5)(iii) day-count helpers shipped: `_compute_odd_first_period_fraction(origination, first_payment, day_count)` for the three v1-supported day-counts (30/360, actual/365, actual/actual via `dateutil.relativedelta(months=1)`) + `solve_apr` now wires `APRRequest.odd_first_period_days` into the first `PaymentScheduleEntry.unit_period_fraction` so the U-equation's `(1+g·i)` factor on the first payment carries the long odd first period. Module docstring extended with D-15..D-18 LOCKED DECISIONS + a Day-count conventions section. Engine smoke gate verified: $200k @ 6.5%/30yr Wikipedia anchor with 15-day long odd first period gives APR ≈ 6.5002% (above 6.50% nominal as required by Plan Deviation Rule 2 sign-flip detector). Suite 470 passed (was 469; +1 from new inline test) / 4 skipped / 10 xfailed; zero regression.**

## Performance

- **Duration:** 6 min 39 s
- **Started:** 2026-05-03T20:26:08Z
- **Completed:** 2026-05-03T20:32:47Z
- **Tasks:** 4 (all atomically committed; no checkpoints, no human action)
- **Files modified:** 2 (`lib/apr.py` 642 → 805 lines, +163; `tests/test_apr.py` 320 → 370 lines, +50)
- **Files created:** 0

## Accomplishments

- Shipped `_compute_odd_first_period_fraction(origination: date, first_payment: date, day_count: Literal["30/360","actual/365","actual/actual"]) -> Decimal` per Reg Z §1026.17(c)(4) + Appendix J §(b)(5)(iii). Supports the three v1 day-counts:
  - **30/360**: `f = (days - 30) / 30`
  - **actual/365**: `f = (days - 365/12) / (365/12)` (~30.4167-day month)
  - **actual/actual**: `f = (days - actual_unit_days) / actual_unit_days` where `actual_unit_days = (origination + relativedelta(months=1) - origination).days` (handles month-end edges per project-wide D-07 dateutil idiom)
- Wired `APRRequest.odd_first_period_days` into `solve_apr` via in-engine rewrite of the first `PaymentScheduleEntry.unit_period_fraction` (using Pydantic `model_copy(update={...})` to preserve immutability). Engine surface needed NO change — Plan 07-02's `_unit_period_equation` and `_derivative` already correctly consume `unit_period_fraction` on the first payment of each block.
- Extended `lib/apr.py` module docstring with **4 new LOCKED DECISIONS** (D-15..D-18) and a **Day-count conventions** subsection enumerating the three formulas with regulatory citations.
- **Engine smoke gate verified** (Plan Deviation Rule 2 sign-flip detector): $200k @ 6.5%/30yr Wikipedia anchor (`$1,264.14` payment) with `day_count="30/360"` + `odd_first_period_days=15` → APR = `0.065002` in 2 Newton iterations. APR is strictly above 6.50% nominal as required (the `(1+f·i)` factor on the first payment correctly increases that payment's PV contribution, requiring a higher `i` to balance the U-equation).
- Added 1 new passing test: `test_odd_first_period_15_days_increases_apr_above_nominal`. Wave 5 will replace this with a fixture-backed sibling.
- **Suite count after:** 470 passed (was 469; +1 from new test) / 4 skipped / 10 xfailed (unchanged) — zero regression to Plan 07-02 baseline.

## Task Commits

Each task committed atomically against `main` (sequential executor; no branching per `parallelization=false`; no AI attribution per global + project CLAUDE.md):

1. **Task 1: Add `_compute_odd_first_period_fraction` helper** — `da04778` (feat)
2. **Task 2: Wire `odd_first_period_days` into `solve_apr`** — `2f7ef94` (feat)
3. **Task 3: Document day-count conventions in module docstring** — `e8aa7a8` (docs)
4. **Task 4: Add Wave 3 inline hand-verify test** — `04ef33e` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `lib/apr.py` (modified, 642 → 805 lines, +163)
  - +84 lines: `_compute_odd_first_period_fraction` helper (Task 1) — new top-level private function with full docstring, three day-count branches, ValueError surfaces for negative-period / f>=1 / unsupported-day_count
  - +33 lines: `solve_apr` body rewrite (Task 2) — `payments_with_odd` synthesis block before `_seed_apr` call; ValueError on f_odd>=1; replaced `request.payment_schedule` with `payments_with_odd` in 3 call sites (`_seed_apr`, `_unit_period_equation`, `_derivative`)
  - +51 lines: module docstring extension (Task 3) — D-15..D-18 LOCKED DECISIONS + "Day-count conventions" subsection
  - +5 lines (header): added `from datetime import date` (with `# noqa: TC003` because the type is used at runtime by `_compute_odd_first_period_fraction`'s parameter annotations) and `from dateutil.relativedelta import relativedelta` import
- `tests/test_apr.py` (modified, 320 → 370 lines, +50)
  - +50 lines: `test_odd_first_period_15_days_increases_apr_above_nominal` (Task 4) — Wave 3 inline hand-verify per Plan §"Task 4". Imports `date as _date` inside the test body to keep the existing top-level imports unchanged.

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|-------------|--------|--------|
| `grep -c 'def _compute_odd_first_period_fraction' lib/apr.py` | 1 | 1 | PASS |
| `grep -c 'odd_first_period_days' lib/apr.py` | >=3 | 11 | PASS |
| `grep -cE '"30/360"\|"actual/365"\|"actual/actual"' lib/apr.py` | >=4 | 18 | PASS |
| `pytest tests/test_apr.py::test_odd_first_period_15_days_increases_apr_above_nominal -v` | PASS | PASS | PASS |
| `mypy --strict lib/apr.py` | clean | clean | PASS |
| `ruff check lib/apr.py` | clean | clean | PASS |
| `ruff format --check lib/apr.py` | clean | clean | PASS |
| Full-suite `pytest -q` | >=435 (=>432 baseline + >=3 new pass; executor floor >=461) | 470 passed / 4 skipped / 10 xfailed / 0 failed / 0 errors | PASS |
| `wc -l lib/apr.py` (>=550) | >=550 | 805 | PASS |
| Plan Acceptance Rule-2 (sign-flip detector): 15-day odd first period gives APR > 6.50% nominal on the Wikipedia anchor | APR > 0.065 | APR = 0.065002 (strictly above) | PASS |

## Decisions Made

Followed the plan's 4 LOCKED DECISIONS (D-15..D-18) verbatim. Several smoke-test invariants were validated empirically before each commit:

- **After Task 1:** Helper smoke-tested across 8 cases — 30/360 long (15 days → f=0.5), 30/360 exact (30 days → f=0), 30/360 short (24 days → f=-0.2), 30/360 too-long (62 days → ValueError f>=1), actual/365 long, actual/actual long (Jan 1 → 31-day month), negative-period (ValueError), unsupported-day_count (ValueError). All correct.
- **After Task 2:** Integration smoke-tested 4 cases:
  - SC-1 anchor regression check: $5000/36/$166.07 → APR = 0.119994 (within `Decimal("0.00001")` of 12.00%; same as Plan 07-02 baseline)
  - 15-day long odd first period on Wikipedia anchor: APR = 0.065002 (above 6.50% nominal — sign-flip detector PASSES)
  - `odd_first_period_days=0` produces byte-identical APR to default no-odd request: 0.065000 == 0.065000
  - `odd_first_period_days=30` (would give f=1) raises ValueError per D-16
- **After Task 3:** `grep -c '"30/360"'` jumped from 4 → 18 (docstring formulas surface the day-count strings); module docstring extension passed `mypy --strict` + `ruff check` + `ruff format --check` (after one ASCII-x fix described in deviations).
- **After Task 4:** New test passes; full suite 470 passed (was 469).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] `solve_apr` actual/actual day-count branch uses 30-day proxy when consuming `odd_first_period_days` integer shortcut**

- **Found during:** Task 2 implementation (transcribing the plan's exact code block)
- **Issue:** The plan's Task 2 code says `# Phase 7 Wave 3 simplification: use 30 days as proxy` for the actual/actual case. This is genuinely the right call: `APRRequest.odd_first_period_days` is an INTEGER (no origination/first_payment dates at the request surface), so the engine cannot compute the true actual/actual unit_days from `relativedelta(months=1)` without those dates. The plan documents this as the intended Wave 3 simplification (D-17 captures the "advanced callers use `_compute_odd_first_period_fraction` with explicit dates" path). I'm logging this as a Rule-2 disposition rather than a no-op so future readers understand WHY the proxy is correct: it's a deliberate scope reduction at the user-friendly-shortcut surface, not a bug.
- **Fix:** Implemented exactly as the plan prescribed (30-day proxy for actual/actual within `solve_apr`); documented inline with a comment pointing readers to D-17 + `_compute_odd_first_period_fraction` for the full-fidelity path.
- **Files modified:** `lib/apr.py` (Task 2 commit `2f7ef94`)
- **Verification:** Empirically the engine smoke gate passes; advanced actual/actual callers use the helper with explicit dates per D-17 (engine accepts the resulting `unit_period_fraction` directly, leaving `odd_first_period_days=0`).
- **Plan deviation rule:** Rule-2 (auto-add critical functionality) — I'm flagging this purely so the deferral surface is visible in the SUMMARY; the plan explicitly endorses the simplification.

**2. [Rule 3 — Hygiene] ASCII `x` for cartesian-product separator in module docstring**

- **Found during:** Task 3 (`uv run ruff check lib/apr.py` after writing the docstring extension)
- **Issue:** The phrase "rate paths × loan amounts × points" used unicode MULTIPLICATION SIGN (U+00D7); ruff RUF002 flagged it as ambiguous in docstrings.
- **Fix:** Replaced both `×` with ASCII `x`. Same fix pattern Plan 07-02 used for unicode MINUS SIGN in `_derivative`'s docstring (Plan 07-02 deviation log Rule-3).
- **Files modified:** `lib/apr.py` (Task 3 commit `e8aa7a8`)
- **Verification:** `ruff check lib/apr.py` clean post-fix.
- **Plan deviation rule:** Rule-3 (hygiene only).

**3. [Rule 3 — Hygiene] `ruff format` auto-applied 2 reformats during execution**

- **Found during:** End of Task 2 + end of Task 4 (`uv run ruff format --check` flagged "would reformat: 1 file" both times)
- **Issue:** Hand-written code had minor whitespace / line-wrap differences from ruff's canonical output.
- **Fix:** `uv run ruff format lib/apr.py` (Task 2) + `uv run ruff format tests/test_apr.py` (Task 4) — both purely mechanical.
- **Files modified:** `lib/apr.py` (Task 2 commit `2f7ef94`); `tests/test_apr.py` (Task 4 commit `04ef33e`)
- **Verification:** `ruff format --check` clean post-fix on both files.
- **Plan deviation rule:** Rule-3 (hygiene only — no semantic change).

**4. [Rule 1 — Bug check / informational] `must_haves.truths` "APR ≈ 6.523%" forecast is back-of-envelope incorrect by ~100x; engine math is right**

- **Found during:** Task 2 hand-verify (Plan Deviation Rule 2 sign-flip detector check)
- **Issue:** The plan's `must_haves.truths` line states "Hand-calc fixture (15-day odd first period, US 30/360) gives APR ≈ 6.523% on the Wikipedia anchor (verified by Wave 5)". RESEARCH §"Pinned Worked Examples / Example 2" makes the same claim. My engine produces APR = 0.065002 (≈ 6.5002%) — the BUMP above 6.50% nominal is +0.0002 percentage-points, not +0.023 percentage-points (~100x smaller).
- **Investigation:** Hand-derived the U-equation residual. At i=0.005417 (=6.5%/12), without odd period f(i) ≈ -0.625 (Wikipedia rounding noise); with 15-day odd, f(i) ≈ -4.03 (the `(1+0.5·i)` factor on the first payment adds ~$3.40 of PV → RHS overshoots LHS, requiring a HIGHER i to rebalance). The engine converges at i ≈ 0.005417, APR = 0.065002. Cross-checked at i=0.06523/12 (RESEARCH's claim): f(i) ≈ +473.67 (way off-balance). RESEARCH/plan narrative claim ≈ 6.523% is **arithmetically incorrect** — it overstates the bump by ~100x. The engine direction (APR strictly above 6.50%) is correct; the magnitude RESEARCH claims is the wrong order of magnitude.
- **Disposition:** **Engine is correct; plan/RESEARCH narrative was a back-of-envelope estimate**. The plan's Acceptance criteria (`response.estimated_apr > Decimal("0.065000")` AND `< Decimal("0.070000")`) PASS. The plan's Deviation Rule 2 sign-flip detector ("If APR is below the 6.5% nominal, the U-equation has a sign flip in the (1+f·i) factor") PASSES — APR is strictly above 6.5%, no sign flip. **Wave 5 will pin the exact value via an HMDA Platform-validated fixture**, at which point the precise magnitude will be cross-validated against the regulatory oracle (per CONTEXT.md D-09: "If HMDA Platform output diverges from `solve_apr` by more than `Decimal('0.00001')` on any fixture, the engine is presumed wrong"). Until Wave 5 runs, the engine math is correct as far as the plan's Wave 3 acceptance gates are concerned.
- **Files modified:** None — this is an informational note, not a code change. The Task 4 test docstring documents the magnitude finding for downstream readers.
- **Plan deviation rule:** Rule-1 disposition is "no change required" — the engine is right; the plan's truth claim was a forecast, and Wave 5 will precision-cross-validate.

---

**Total deviations:** 4 (1 Rule-2 plan-endorsed simplification, 2 Rule-3 hygiene, 1 Rule-1 informational — engine math correct, plan narrative magnitude was off ~100x; Wave 5 will pin via HMDA Platform oracle)
**Impact on plan:** Plan acceptance gates all PASS. The Rule-1 finding does not block Wave 3 — the plan's accept-criteria (`> 0.065 AND < 0.07`) are satisfied. The forecast magnitude is corrected here; Wave 5 will replace the forecast with an oracle-pinned value.

## Issues Encountered

None — all 4 tasks executed sequentially, all 4 deviations resolved inline, no checkpoints, no escalations.

## Threat Flags

None — Plan 07-03 modifies a single internal calc-engine module (`lib/apr.py`) plus its sibling test file (`tests/test_apr.py`). No new network surface, no new authentication boundaries, no new file-system access patterns, no schema changes at trust boundaries. The new code path (`_compute_odd_first_period_fraction`) is a private helper consumed only by Phase 8 stress wrappers (future) and via the engine-internal rewrite path in `solve_apr`. The new external dependency import (`from dateutil.relativedelta import relativedelta`) is already a project-pinned dependency (per `pyproject.toml` and prior usage in `lib/amortize.py` for biweekly schedules) — no new third-party trust boundary.

## Known Stubs

The following intentional placeholders are documented for future waves:

- **`tests/test_apr.py:test_odd_first_period_15_days_increases_apr_above_nominal`** — uses inline-constructed `APRRequest`/`Loan`/`AdvanceScheduleEntry`/`PaymentScheduleEntry`. The plan explicitly authorizes this Wave-3-only inline variant: *"This test is REPLACED by a fixture-backed sibling in Wave 5; it stays in Wave 3 as the 'engine smoke' gate."* Wave 5 Plan 07-05 will (a) ship `tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json` (and `_45_days.json` per RESEARCH §Q(e)) and (b) flip the inline-construction to an `apr_fixture("regz_appendix_j_odd_first_period_15_days")` load with an HMDA Platform-validated `expected.estimated_apr` value.
- **`solve_apr` actual/actual day-count branch with `odd_first_period_days > 0`** uses a 30-day proxy unit_period (since the request surface has no origination/first_payment dates). Documented inline in `solve_apr` body and in the module docstring (D-17) — not a bug; it's the deliberate scope reduction at the user-friendly-shortcut surface. Advanced actual/actual callers use `_compute_odd_first_period_fraction` with explicit dates and set `unit_period_fraction` directly on the `PaymentScheduleEntry`, leaving `odd_first_period_days=0`.

No unintentional stubs introduced. No mock/placeholder data. No `FIXME` comments. The single Wave-3-inline-test stub is documented + tracked + tied to Wave 5.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture, no human-in-the-loop verification. All 4 tasks executed autonomously per `autonomous: true` plan frontmatter.

## Cross-wave Dependency Notes (forward)

- **Wave 4 (Plan 07-04 CLI)** — unblocked. The CLI's `--help` epilog (per Plan 07-04 §"references citation in --help") will need to mention `odd_first_period_days` as a request field; the CLI body re-uses `solve_apr` unchanged. The 6-key error envelope at the CLI boundary will pick up `ValueError("odd_first_period_days >= 1 unit period")` via the Phase 4 D-13 inheritance pattern.
- **Wave 5 (Plan 07-05 tests + fixtures)** — unblocked + has small swap to do. Wave 5 will:
  - Ship `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` (Reg Z anchor; closes APR-05) AND `regz_appendix_j_odd_first_period_15_days.json` + `_45_days.json` (odd-first-period fixtures from RESEARCH §Q(e)).
  - Replace `test_odd_first_period_15_days_increases_apr_above_nominal`'s inline-construction body with `apr_fixture("regz_appendix_j_odd_first_period_15_days")` load + Decimal-equality assert against an HMDA Platform-validated `expected.estimated_apr` value (per CONTEXT.md D-09).
  - Note: Wave 5 expected.estimated_apr should reflect the ENGINE's 0.065002 result (cross-validated against HMDA Platform per D-09 — divergence > 0.00001 means engine is wrong), NOT the back-of-envelope 0.06523 from the plan/RESEARCH narrative (which is incorrect per this plan's Rule-1 informational deviation).
- **Wave 6 (Plan 07-06 references doc)** — unblocked. `references/apr-reg-z.md` §3 will document the three day-count formulas (verbatim from the new module docstring) + cite `_compute_odd_first_period_fraction` as the public helper for advanced callers. APR-08 closes when references/apr-reg-z.md ships.
- **Wave 7 (Plan 07-07 HMDA Platform fixtures)** — unblocked. The HMDA Platform captures will exercise the multi-fixture cross-validation against the engine; per CONTEXT.md D-09 ("HMDA delta policy — engine is wrong"), any divergence > `Decimal("0.00001")` will fail the test. Wave 7 may surface additional odd-first-period long cases (15, 30, 45, 60-day per RESEARCH §Q(d)) — engine is ready.
- **Phase 8 (stress-points)** — `_compute_odd_first_period_fraction(origination, first_payment, day_count)` is the canonical helper for stress wrappers that vary origination dates across grid cells (rate paths × loan amounts × points × first-payment-date variations). Direct callers will set `PaymentScheduleEntry.unit_period_fraction` from the helper output and leave `APRRequest.odd_first_period_days=0` per D-17.
- **Requirement closure status:** Plan 07-03 closes NO APR-XX requirement directly (the 4 remaining open requirements all close in Waves 4-7). REQUIREMENTS.md needs no edits this wave.

## TDD Gate Compliance

The plan does not declare `type: tdd`; this is a vanilla `type: execute` plan. Per the executor protocol's TDD section, no RED/GREEN/REFACTOR cycle gate enforcement is required. For traceability, however: Task 4 ships an inline test that PASSES on first run against the engine code shipped in Tasks 1-2 + docstring updated in Task 3 (not a TDD RED gate; the test exercises a code path that already works correctly per Task 2's empirical hand-verification).

## Self-Check: PASSED

Verified at execution end:

- [x] `lib/apr.py` exists at the path declared in plan frontmatter (`files_modified: [lib/apr.py]`) — `wc -l` = 805 (>= 550 plan minimum)
- [x] `tests/test_apr.py` exists — `wc -l` = 370 (was 320; +50 from Task 4)
- [x] `git log --oneline | grep da04778` (Task 1 _compute_odd_first_period_fraction) → present
- [x] `git log --oneline | grep 2f7ef94` (Task 2 odd_first_period_days wiring) → present
- [x] `git log --oneline | grep e8aa7a8` (Task 3 module docstring) → present
- [x] `git log --oneline | grep 04ef33e` (Task 4 inline hand-verify test) → present
- [x] All four task commits reachable from `main`
- [x] No commit message contains "Co-Authored-By", "claude", or any AI attribution (verified by inspection of all 4 messages — all solely-authored as repo owner per global + project CLAUDE.md)
- [x] `grep -c 'def _compute_odd_first_period_fraction' lib/apr.py` → 1 (gate PASS)
- [x] `grep -c 'odd_first_period_days' lib/apr.py` → 11 (gate PASS, target >=3)
- [x] `grep -cE '"30/360"|"actual/365"|"actual/actual"' lib/apr.py` → 18 (gate PASS, target >=4)
- [x] `pytest tests/test_apr.py::test_odd_first_period_15_days_increases_apr_above_nominal -v` → PASS
- [x] Full suite: 470 passed / 4 skipped / 10 xfailed / 0 failed / 0 errors (was 469+4+10; +1 net pass from new test; zero regression to Plan 07-02 baseline of 469)
- [x] `pytest tests/test_apr.py -v`: 5 passed / 9 xfailed (was 4/9; +1 net pass)
- [x] mypy --strict + ruff check + ruff format --check all clean on `lib/apr.py` and `tests/test_apr.py`
- [x] Plan Acceptance Rule-2 (sign-flip detector) verified: 15-day odd first period on Wikipedia anchor gives APR > 6.50% (got 0.065002; PASS — no sign flip)
- [x] APR-08 (the only requirement Plan 07-03 partially affects) remains Pending — closes in Wave 6 when references/apr-reg-z.md ships citing `_compute_odd_first_period_fraction`

---
*Phase: 07-estimated-apr*
*Completed: 2026-05-03*
