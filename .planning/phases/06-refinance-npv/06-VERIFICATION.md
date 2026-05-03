---
phase: 06-refinance-npv
verified: 2026-05-02T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
must_haves_total: 5
must_haves_met: 5
phase_req_ids:
  - REFI-01  # verified
  - REFI-02  # verified
  - REFI-03  # verified
  - REFI-04  # OPTIONAL — deferred to Phase 11 per D-07, documented in source
  - REFI-05  # verified
  - REFI-06  # verified (D-13: horizon=12 trick accepted by PLAN-CHECK)
  - REFI-07  # verified
  - REFI-08  # verified
  - REFI-09  # verified
advisory:
  # CR-01 from 06-REVIEW.md — noted here per user instruction; NOT a gap in this report
  - id: CR-01
    source: 06-REVIEW.md
    summary: >
      evaluate_cash_out drops the cash_out_amount gross inflow from the RefiResponse.cashflows
      audit trail when closing_costs >= cash_out_amount. NPV value is also incorrect on that
      path (treats -closing_costs as the only t=0 cashflow; the cash_out_amount inflow
      never enters the signed stream). Confirmed in behavioral spot-check below.
      Severity: blocker per code review. User must decide: gap-close before Phase 11
      consumers (recommended) or accept with a deliberate override.
    action_needed: Decision required — gap-close or override before Phase 11 SUBA-02 dependency
human_verification: []
---

# Phase 6: Refinance NPV Verification Report

**Phase Goal:** Calculate refinance NPV (rate-and-term + cash-out) and breakeven months from
the borrower's perspective with sign-convention rigor enforced by Pydantic models

**Verified:** 2026-05-02T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The phase goal is achieved. All five ROADMAP success criteria are satisfied by the
codebase, backed by 25 passing tests (25/25 pass; 0 xfail). The test gate baseline
(461 passed + 4 skipped + 1 inherited xfail + 0 failed) is confirmed in the full suite run.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1: positive-NPV fixture returns NPV > 0 and negative-NPV fixture returns NPV < 0 | VERIFIED | Engine spot-check: positive fixture → 60705.48 (>0); negative fixture (horizon=12) → -718.01 (<0). Backed by test_refi_rate_and_term_positive_npv and test_refi_rate_and_term_negative_npv (both PASS) |
| 2 | SC-2: breakeven reported in two labeled forms (simple + NPV-based) in output JSON | VERIFIED | RefiBreakeven model has simple_months/simple_status + npv_months/npv_status. Engine spot-check: divergence fixture returns simple=26, npv=28 (2-month gap). Backed by test_refi_breakeven_simple_labeled, test_refi_breakeven_npv_labeled, test_refi_breakeven_divergence_documented (all PASS) |
| 3 | SC-3: cash-out fixture reports cash_proceeds, new_monthly_pi, total_interest_delta | VERIFIED | Engine spot-check: cash_proceeds=47000.00, new_monthly_pi=1498.88, total_interest_delta=145706.07 (positive). Backed by test_refi_cash_out_proceeds, test_refi_cash_out_new_monthly_pi, test_refi_cash_out_total_interest_delta (all PASS) |
| 4 | SC-4: RefiCashflow direction field rejects outflow+positive and inflow+negative | VERIFIED | Engine spot-check: outflow+Decimal("2000.00") raises ValidationError; inflow+Decimal("-100.00") raises ValidationError. Backed by test_refi_cashflow_outflow_positive_rejected, test_refi_cashflow_inflow_negative_rejected (both PASS) |
| 5 | SC-5: references/refi-npv.md has verbatim phrase "outflows negative, savings positive" and is cited in --help | VERIFIED | File exists at 630 lines (>= 250 required); contains phrase 3 times; 8 numbered H2 sections present. --help output contains "see references/refi-npv.md" and "outflows negative, savings positive". Backed by test_refi_npv_doc_sections_present, test_refi_npv_doc_sign_convention_phrase, test_cli_help_cites_references_refi_npv (all PASS) |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lib/refinance.py` | Pydantic models + engine | VERIFIED | 1098 lines; 6 models (RefiCashflow, RefiBreakeven, _CommonRefiFields, RateAndTermRefiRequest, CashOutRefiRequest, RefiResponse); discriminated union; evaluate_rate_and_term + evaluate_cash_out + evaluate bodies all present and functional |
| `scripts/refi_npv.py` | JSON-in/JSON-out CLI | VERIFIED | 254 lines; lazy imports after argparse (D-18); float-gate via _cli_helpers; 6-key WR-02 envelope on stderr; --help cites references/refi-npv.md |
| `references/refi-npv.md` | Sign-convention doc >= 250 lines | VERIFIED | 630 lines; 8 numbered sections; verbatim SC-5 phrase present 3 times; all required citations (Investopedia, Federal Reserve, CFPB, IRS Pub 936, numpy-financial docs + bug #131) |
| `tests/test_refinance.py` | 25 tests covering REFI-01..09 + SC-1..5 | VERIFIED | 1004 lines; all 25 stubs flipped to passing assertions; zero xfail remaining in phase-6 test surface |
| `tests/fixtures/refinance/*.json` | 6 fixtures (one per scenario) | VERIFIED | 6 files present: positive_npv_200bps_drop_2k_costs.json, negative_npv_short_horizon.json, cash_out_proceeds_50k.json, breakeven_divergence.json, sign_validator_outflow_positive.json, after_tax_mode_smoke.json |
| `tests/conftest.py` | refinance_fixture loader | VERIFIED | Contains def refinance_fixture alongside arm_fixture and affordability_fixture; existing fixtures untouched |
| `tests/fixtures/refinance/.gitkeep` | Directory anchor | VERIFIED | Present (no .gitkeep file needed once JSON fixtures exist, but directory exists with 6 JSON files) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `scripts/refi_npv.py` | `lib/refinance.py` | lazy import `from lib.refinance import RefiRequest, evaluate` inside main() | WIRED | Import confirmed at line 188; test_cli_help_does_not_import_lib_refinance verifies D-18 lazy-load |
| `scripts/refi_npv.py` | `scripts/_cli_helpers.py` | `from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope` | WIRED | Phase 5 helper reuse confirmed; float-gate tested by test_cli_rejects_float_closing_costs |
| `lib/refinance.py` | `lib/amortize.build_schedule` | `from lib.amortize import build_schedule`; called in both engine paths | WIRED | Used to compute old_monthly_pi + new_monthly_pi in evaluate_rate_and_term and evaluate_cash_out |
| `lib/refinance.py` | `lib/rules/irs_pub936.qualified_loan_limit` | lazy import inside `_compute_tax_shield_cashflows` | WIRED | Lazy import preserves cold-path performance; called when after_tax_mode=True |
| `tests/test_refinance.py` | `tests/fixtures/refinance/*.json` | `refinance_fixture(stem)` fixture loader | WIRED | All 6 fixture files consumed by 13+ fixture-driven tests |
| `RefiCashflow._direction_sign_consistency` | SC-4 sign convention | `@model_validator(mode="after")` at lib/refinance.py:229 | WIRED | Confirmed by spot-check and 4 passing SC-4 tests |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `evaluate_rate_and_term` | `npv` (Decimal) | `_compute_npv` → `npf.npv` → `build_schedule` DB/math calls | Yes — amortization schedule produces real P&I values; NPV wraps numpy_financial.npv | FLOWING |
| `evaluate_cash_out` | `cash_proceeds`, `total_interest_delta` | `quantize_cents(req.cash_out_amount - req.closing_costs)`, `new_schedule.total_interest - old_schedule.total_interest` | Yes — arithmetic on validated request fields + schedule totals | FLOWING |
| `RefiResponse.cashflows` | `list[RefiCashflow]` | `_build_refi_cashflows(...)` with real P&I values | Yes — per-period construction from computed old_pi, new_pi, closing_costs | FLOWING |

Note on CR-01 audit-trail gap (from 06-REVIEW.md): when `closing_costs >= cash_out_amount`,
the `cash_out_amount` gross inflow is absent from `cashflows` AND the NPV value is
incorrect (only `-closing_costs` enters the t=0 position; the borrower's gross receipt
is silently dropped). This is NOT a gap in the success criteria (which cover the normal
`cash_out_amount > closing_costs` path used by all fixtures), but it is a correctness
defect in an untested edge case. See Advisory section.

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| SC-1 positive: evaluate(rate-and-term, 200bps drop, $2k closing) → NPV > 0 | npv=60705.48 | PASS |
| SC-1 negative: evaluate(rate-and-term, 200bps drop, $5k closing, horizon=12) → NPV < 0 | npv=-718.01 | PASS |
| SC-4 outflow+positive: RefiCashflow(direction='outflow', amount=Decimal('2000.00')) → raises | ValidationError raised | PASS |
| SC-4 inflow+negative: RefiCashflow(direction='inflow', amount=Decimal('-100.00')) → raises | ValidationError raised | PASS |
| SC-3 cash-out: cash_proceeds=47000.00, new_monthly_pi=1498.88, total_interest_delta=145706.07 | All values match fixtures | PASS |
| SC-5 --help: "see references/refi-npv.md" present | 1 match in --help output | PASS |
| SC-5 --help: "outflows negative, savings positive" present | 1 match in --help output | PASS |
| Full test suite: 461 passed + 4 skipped + 1 inherited xfail | 461 passed + 4 skipped + 1 xfailed | PASS |
| CR-01 spot-check: closing_costs==cash_out_amount, t=0 cashflows | Only -50000 outflow; cash_out inflow absent; NPV=-50771.19 | CONFIRMED BUG (advisory only, edge case outside SC scope) |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| REFI-01 | 06-01, 06-02, 06-05 | rate-and-term refi NPV, borrower perspective | SATISFIED | evaluate_rate_and_term ships real body; 3 positive-NPV tests PASS; fixture pins NPV=60705.48 |
| REFI-02 | 06-01, 06-03, 06-05 | cash-out refi modeling | SATISFIED | evaluate_cash_out ships real body; 3 cash-out tests PASS; fixture pins cash_proceeds=47000.00 |
| REFI-03 | 06-02, 06-05 | breakeven months: simple + NPV-based | SATISFIED | RefiBreakeven model; 3 breakeven tests PASS; divergence fixture shows simple=26, npv=28 |
| REFI-04 | 06-05 | Optional pyxirr integration | OPTIONAL/DEFERRED | Documented in lib/refinance.py with "Phase 11" + "pyxirr" markers; test_pyxirr_deferred_to_phase11_documented PASS; per D-07 and PLAN-CHECK accepted concern |
| REFI-05 | 06-05 | Tests with positive-NPV fixture | SATISFIED | positive_npv_200bps_drop_2k_costs.json committed; test PASS |
| REFI-06 | 06-05 | Tests with negative-NPV fixture | SATISFIED | negative_npv_short_horizon.json committed (D-13 horizon=12 trick accepted); test PASS |
| REFI-07 | 06-03, 06-05 | Tests with cash-out fixture | SATISFIED | cash_out_proceeds_50k.json committed; 3 SC-3 tests PASS |
| REFI-08 | 06-04 | scripts/refi_npv.py JSON-in/JSON-out CLI | SATISFIED | scripts/refi_npv.py ships; 6 CLI tests PASS including subprocess round-trip, float-gate, D-18 lazy import |
| REFI-09 | 06-06 | references/refi-npv.md documents sign convention | SATISFIED | 630-line doc; 8 sections; SC-5 phrase 3x; 2 doc-tests PASS |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `lib/refinance.py:872-873, 1010-1011` | `assert` statements in production code paths (WR-09 from review) | Warning | assert stripped under python -O; type narrowing intent but not -O safe |
| `lib/refinance.py:141` | `from datetime import date  # noqa: F401` — unused import after Wave 6 (IN-01 from review) | Info | Dead import; suppressed lint; no functional impact |
| `lib/refinance.py:157-158` | `TYPE_CHECKING` block with unused Sequence import (IN-02 from review) | Info | Dead reservation; no functional impact |
| `lib/refinance.py:169-174` | `BREAKEVEN_NEVER_SENTINEL` defined but never referenced in helpers (IN-03 from review) | Info | Constant not wired to the None returns it was meant to label |
| `references/refi-npv.md:127` | Helper table cites `_build_cashflow_stream` (wrong name) and `_compute_npv` with wrong signature (IN-05 from review) | Info | Documentation drift; no functional impact |
| `lib/refinance.py:986-1001` | CR-01: evaluate_cash_out drops cash_out_amount gross inflow from audit trail when closing_costs >= cash_out_amount | Advisory blocker | See Advisory section — this is a correctness defect on an untested edge case, confirmed by spot-check |

All anti-patterns flagged by 06-REVIEW.md are advisory warnings or info items. None prevent
the phase-6 success criteria from being met. CR-01 is an edge-case correctness defect with no
current test coverage that may matter to Phase 11 SUBA-02 consumers.

### Human Verification Required

None. All five success criteria are verified programmatically.

## Advisory: CR-01 from Code Review (Not a Verification Gap)

The code review (06-REVIEW.md, filed 2026-05-02) identified a BLOCKER-class defect in `evaluate_cash_out` that the verification is directed to note but not classify as a gap:

**Defect:** When `closing_costs >= cash_out_amount`, `evaluate_cash_out` calls `_build_refi_cashflows` with `cash_proceeds_net=Decimal("0.00")`. The `_build_refi_cashflows` guard `if cash_proceeds_net > Decimal("0")` then emits NO `cash_proceeds` inflow. The `closing_costs` outflow IS emitted as the t=0 cashflow. The borrower's gross `cash_out_amount` receipt is entirely absent from `RefiResponse.cashflows`, and the NPV is computed without it.

**Confirmed by spot-check:** `closing_costs==cash_out_amount=50000` → t=0 cashflows contain only `('closing_costs', -50000.00, 'outflow')`; `cash_proceeds=None`; `NPV=-50771.19` (the gross inflow was never discounted).

**Why this is advisory, not a verification gap:**
- All five ROADMAP success criteria cover the normal-path scenario where `cash_out_amount > closing_costs` (the fixtures use cash_out=50000 and closing=3000).
- The edge case is unreachable via any committed fixture.
- The PLAN-CHECK already accepted multiple adjacent concerns under its "concerns, not blocks" posture.
- The user directed this verification to note CR-01 rather than derive it afresh.

**Recommended action:** Gap-close before Phase 11 SUBA-02 takes a dependency on `evaluate_cash_out`. The fix is in 06-REVIEW.md CR-01: emit both gross legs (cash_out_amount inflow + closing_costs outflow) when the net is non-positive, so the audit trail and NPV both reflect the actual transaction.

---

_Verified: 2026-05-02T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
