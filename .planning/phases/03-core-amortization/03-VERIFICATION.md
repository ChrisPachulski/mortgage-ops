---
phase: 03-core-amortization
verified: 2026-04-29T20:00:00Z
status: human_needed
score: 5/5 success criteria verified (with 1 advisory determinism warning under personal-use scope)
overrides_applied: 0
human_verification:
  - test: "CR-01 determinism deviation acceptance — duplicate recurring ExtraPrincipalEntry rows at the same period produce different schedules depending on caller-supplied list order"
    expected: "Decide whether the engine accepts user input where two ExtraPrincipalEntry rows share `(period, recurring=True)`. Two acceptable resolutions: (a) Add a `model_validator` on `AmortizeRequest` rejecting duplicate `(period, recurring=True)` pairs (defensive, matches D-05 spirit). (b) Document an explicit tie-breaker in CONTEXT.md D-05 and pin a fixture/test. Status quo (current) is non-deterministic for that input class."
    why_human: "The locked decision D-05 wording (`the LATEST entry with entry.period <= p AND entry.recurring=True`) is order-of-list-ambiguous when two entries tie on period. The phase goal explicitly cites 'arbitrary extra-principal schedules'; whether 'arbitrary' includes duplicate-period recurring entries is a product/spec call, not a test verdict. CLAUDE.md states 'Math correctness first. Every dollar figure that exits this system must be traceable to a tested, deterministic Python function' — making this potentially relevant. The phase plans' must_haves do NOT explicitly list 'reject duplicate (period, recurring) pairs' as a truth, and no current test or fixture exercises it. All locked D-05 examples use distinct periods."
  - test: "WR-02 error envelope shape inconsistency acceptance — CLI emits a 3-key envelope on float-rejection but a 6-key envelope on Pydantic ValidationError"
    expected: "Decide whether downstream Phase 9 Node consumers / Phase 10 SKILL.md narration tolerate two error JSON shapes for closely related failure modes (D-19 boundary)."
    why_human: "Two different shapes are emitted from `scripts/amortize.py` stderr depending on which gate fired. The phase goal does not mandate a single envelope shape; this is a cross-phase consistency concern that surfaces when Phase 9/10 land. The current CLI tests pass (both shapes parse as JSON arrays of error dicts)."
re_verification:
  previous_status: none
  previous_score: N/A
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 3: Core Amortization Verification Report

**Phase Goal:** Build the foundational amortization engine wrapping numpy-financial, supporting fixed-rate, biweekly, and arbitrary extra-principal schedules with no float drift.

**Verified:** 2026-04-29T20:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| SC1 | `scripts/amortize.py --input <400k/30yr/6.5% loan>` returns JSON with `monthly_pi == "2528.27"` and final-row `balance == "0.00"` | VERIFIED | Manual run: `uv run python scripts/amortize.py --input /tmp/sc1_loan.json` → `monthly_pi: 2528.27`, `final_balance: 0.00`. Confirmed in `test_cli_smoke_subprocess_round_trip` (Wikipedia 200k case) + `test_fixed_rate_oracle[computed_400k_30yr]` parity test. NOTE: the literal fixture path `fixtures/loan_400k_30yr_6_5.json` does NOT exist as a committed file; the SC contract is behavioral (the script produces these values for the input shape), and the equivalent JSON in tmp produces the contract values exactly. |
| SC2 | All 4 golden-fixture tests (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr) pass with exact Decimal equality (no `assertAlmostEqual`) | VERIFIED | `test_fixed_rate_oracle` parametrized over 4 IDs all PASS: wikipedia_200k_30yr, cfpb_le_162k_30yr, computed_400k_30yr, computed_200k_15yr. Each asserts `schedule.monthly_pi == Decimal(fx["expected_monthly_pi"])`. `grep -c "assertAlmostEqual" tests/test_amortize.py tests/test_models.py` returns 0 in both files. Pinned values: 1264.14 / 761.78 / 2528.27 / 1797.66. |
| SC3 | Biweekly schedule produces 26 payments/year via `relativedelta(weeks=2)`; sum of all principal payments equals original principal exactly | VERIFIED | Smoke check on 200k/6.5/30 biweekly-true: 628 periods, sum(principal+extra) = 200000.00 EQ original; `payment[1].payment_date - payment[0].payment_date == 14 days`. `lib/amortize.py:412` uses `relativedelta(weeks=2 * period)`. Test `test_biweekly_true_oracle` + `test_biweekly_half_monthly_oracle` PASS. `assert_schedule_invariants` enforces sum-equals-original on every schedule-producing test. |
| SC4 | Extra-principal scenarios (single, recurring, per-period) shorten schedule and final balance reaches `Decimal("0.00")` | VERIFIED | Smoke: one-shot $5000 at period 60 → 341 periods, balance 0.00, sum 200000.00. Recurring $200/period → 250 periods, balance 0.00, sum 200000.00. Tests `test_extra_oneshot_period_60`, `test_extra_recurring_200_from_period_1`, `test_extra_step_up_200_to_300_at_period_13`, `test_extra_caps_at_remaining_balance_silently` all PASS. Each calls `assert_schedule_invariants` confirming AMRT-07. |
| SC5 | `scripts/amortize.py --help` prints usage without importing heavy deps; running with no input prints clear schema-error message | VERIFIED | `--help` exits 0 and prints `--input` option. Structural check (importlib.util.spec_from_file_location + sys.modules assertion): `lib.amortize imported during --help? False`, `numpy_financial imported during --help? False`. No-input run exits 2 with stderr `usage: amortize [-h] --input INPUT\namortize: error: the following arguments are required: --input`. Test `test_cli_help_does_not_import_lib_amortize` PASSES (subprocess-spawned variant). |

**Score:** 5/5 ROADMAP Success Criteria verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `lib/models.py` | Phase-1 models extended with D-10/D-14/D-15: `Payment.cumulative_interest`, `Payment.cumulative_principal`, `Schedule.final_payment_adjusted`, `@model_validator` enforcing `total_interest == payments[-1].cumulative_interest` | VERIFIED | All 4 fields/validator present at expected lines (60, 61, 73, 76). `model_validator` raises ValueError with `"D-15 invariant:"` prefix. Empty-payments path early-returns (constructor convenience). |
| `lib/amortize.py` | Engine wrapping numpy-financial with `ExtraPrincipalEntry`, `AmortizeRequest`, `_resolve_extra`, `_build_fixed_monthly`, `_build_biweekly_true`, `_build_biweekly_half_monthly`, `build_schedule` | VERIFIED | 461 lines. `import numpy_financial as npf` present (line 136); `npf.pmt(` called twice (line 271, 370). Bug-avoidance docstring contains `issues/130` AND `issues/131`. No hand-rolled PMT formula (`grep -E 'principal\s*\*.*rate.*\*\*'` returns 0). All three private build helpers present. AmortizeRequest D-02 validator emits literal `"biweekly_mode must be None when frequency='monthly' (D-02)"`. |
| `scripts/amortize.py` | argparse CLI + lazy-import + `AmortizeRequest.model_validate_json` + structured JSON error envelopes | VERIFIED | 187 lines. Shebang `#!/usr/bin/env python3`. Lazy-imports inside `def main()` AFTER `parser.parse_args()` (lines 127-128). `AmortizeRequest.model_validate_json(raw)` at line 170. `e.json()` pass-through at line 173. `_find_json_float_loc` pre-validation gate (lines 46-90) addresses Pydantic v2 documented permissive JSON-float-to-Decimal coercion. |
| `tests/test_amortize.py` | ~22+ tests covering AMRT-01..08 + D-02 + D-15 + month-end + CLI; `assert_schedule_invariants` helper invoked once per schedule-producing test | VERIFIED | 25 def test_ functions / 35 parametrized cases. `assert_schedule_invariants` defined at line 56-75 and invoked 14 times (helper definition + 13 call sites). Subprocess-based D-18 lazy-import test in `test_cli_help_does_not_import_lib_amortize`. All 35 tests PASS in 0.94s. |
| `tests/conftest.py` | `amortize_fixture` factory (filename-stem loader) added; `golden_fixture` preserved | VERIFIED | `amortize_fixture` defined at lines 38-52. Loads from `tests/fixtures/amortize/{stem}.json`. Existing `golden_fixture` factory unchanged. |
| `tests/fixtures/amortize/*.json` | 7 JSON fixtures with engine-emitted values | VERIFIED | All 7 files exist: biweekly_half_monthly_200k_6_5.json, biweekly_true_200k_6_5.json, extra_caps_at_balance.json, extra_oneshot_5k_period_60.json, extra_recurring_200_30yr.json, extra_step_up_200_to_300.json, month_end_jan_31.json. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `lib/amortize.py:build_schedule` | `numpy_financial.pmt` | `-npf.pmt(period_rate, n, principal)` | WIRED | Two call sites: line 271 (`_build_fixed_monthly`), line 370 (`_build_biweekly_true` for implied monthly_pi). |
| `lib/amortize.py:build_schedule` | `lib.money.quantize_cents` | end-of-period quantization on every Money assignment | WIRED | 11 `quantize_cents(` calls. No mid-expression compound `quantize_cents(...) [op] quantize_cents(...)` pattern present. |
| `lib/amortize.py:build_schedule` | `lib.models.Schedule` | `Schedule(loan=..., monthly_pi=..., total_interest=..., final_payment_adjusted=..., payments=[...])` | WIRED | Both `_build_fixed_monthly` (line 340) and `_build_biweekly_true` (line 434) construct Schedule with all 5 fields populated. `total_interest = last.cumulative_interest` per D-15 by construction. |
| `scripts/amortize.py:main` | `lib.amortize.AmortizeRequest` | lazy-import after `argparse.parse_args()` | WIRED | Line 127 `from lib.amortize import AmortizeRequest, build_schedule` is INSIDE `def main()` AFTER parse_args() (line 112). Verified D-18 contract: `lib.amortize` and `numpy_financial` are NOT in sys.modules after a `--help` run. |
| `scripts/amortize.py:main` | `lib.amortize.build_schedule` | `build_schedule(request.loan, frequency=..., biweekly_mode=..., extra_principal=...)` | WIRED | Line 176-181. Passes through validated `request` fields verbatim. |
| `scripts/amortize.py:main` | `Schedule.model_dump_json` | `print(schedule.model_dump_json(indent=2))` | WIRED | Line 182. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `lib/amortize.py::build_schedule` | `payments: list[Payment]` | per-period iteration computing interest, principal_paid, extra, balance from `npf.pmt` + scalar Decimal arithmetic | YES — verified by all 4 golden oracles producing exact pinned values + biweekly producing 628 periods + sum(principal+extra) == original | FLOWING |
| `scripts/amortize.py::main` | `schedule: Schedule` | `build_schedule(...)` after Pydantic validation | YES — CLI smoke run produces actual JSON output with monthly_pi=2528.27 + 360 payments + final balance=0.00 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| 4 golden oracles produce pinned monthly_pi exactly | `uv run pytest tests/test_amortize.py -k test_fixed_rate_oracle` | 4 passed | PASS |
| Biweekly-true accelerates 200k/6.5/30 to ~628 periods, balance=0.00 | manual smoke run | 628 periods, balance 0.00, sum=200000.00, 14 days between adjacent payments | PASS |
| Extra-principal one-shot fires only at named period | `uv run pytest -k test_extra_oneshot_period_60` | passed | PASS |
| Extra-principal recurring shortens schedule, balance ends at 0 | smoke run | 250 periods, balance 0.00, sum=200000.00 | PASS |
| Step-up extras: later recurring overrides earlier from its period | `uv run pytest -k test_extra_step_up` | passed | PASS |
| D-08 cap: huge extra silently caps at remaining balance, sets flag | `uv run pytest -k test_extra_caps` | passed | PASS |
| AMRT-07 invariant: sum(principal+extra) == original | `assert_schedule_invariants` invoked 13× across schedule-producing tests | all 13 invocations pass | PASS |
| `--help` is fast and does NOT import lib.amortize / numpy_financial | importlib.util.spec_from_file_location + sys.modules assertion | both False | PASS |
| `--help` works AND prints --input | `uv run python scripts/amortize.py --help` | exit 0, includes `--input INPUT` | PASS |
| No-input invocation exits 2 with argparse usage | `uv run python scripts/amortize.py` | exit 2, stderr contains `usage:` and `--input` | PASS |
| File-not-found returns structured JSON error | `--input /tmp/nope.json` | exit 2, stderr `{"error": "input file not found: ..."}` | PASS |
| Float-in-money rejected at boundary | `--input` with `principal: 400000.00` (number) | exit 2, stderr `[{"type": "decimal_type", "loc": ["loan", "principal"], "msg": "..."}]` | PASS |
| D-02 violation rejected | monthly + biweekly_mode=true | exit 2, Pydantic ValidationError JSON mentioning `biweekly_mode` | PASS |
| Full pytest suite | `uv run pytest` | 294 passed, 4 warnings (pre-existing StaleReferenceWarning, unrelated to phase 3) | PASS |
| `mypy --strict` clean | `uv run mypy --strict .` | Success: no issues found in 50 source files | PASS |
| `ruff check` clean | `uv run ruff check .` | All checks passed! | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| AMRT-01 | 03-01, 03-02, 03-04 | `lib/amortize.py` wraps numpy-financial PMT/IPMT/PPMT (does NOT reimplement) | SATISFIED | `import numpy_financial as npf` + `npf.pmt(` present; no hand-rolled PMT; `test_amortize_module_uses_numpy_financial` PASS. |
| AMRT-02 | 03-02, 03-04 | Schedule generator handles fixed-rate loans (any term, any rate) | SATISFIED | `_build_fixed_monthly` produces correct schedules for all 4 oracles spanning 162k-400k principal, 3.875%-7% rate, 180-360 month term. |
| AMRT-03 | 03-02, 03-04 | Schedule generator handles biweekly payment frequency (`relativedelta(weeks=2)`) | SATISFIED | `_build_biweekly_true` uses `relativedelta(weeks=2 * period)`; biweekly-true 200k/6.5/30 → 628 periods, sum=200000.00, final balance=0.00. Tests `test_biweekly_true_oracle` + `test_biweekly_half_monthly_oracle` + `test_biweekly_mode_defaults_to_true_when_omitted` PASS. |
| AMRT-04 | 03-02, 03-04 | Schedule generator handles arbitrary extra principal payments (single, recurring, or per-period) | SATISFIED (with advisory note) | One-shot, recurring, step-up, cap-at-balance scenarios all PASS. ExtraPrincipalEntry `period: int>=1`, `amount: Decimal>0`. ADVISORY: code review CR-01 (HUMAN_NEEDED below) flags non-determinism for the unspecified case of duplicate `(period, recurring=True)` entries — locked D-05 spec uses distinct periods in all examples; behavior at duplicates is order-of-list. |
| AMRT-05 | 03-02, 03-04 | Final payment cleanup ensures balance reaches exactly $0.00 (no float drift) | SATISFIED | `test_final_payment_cleans_to_zero_fixed[4 oracles]` + `test_final_payment_cleans_to_zero_biweekly[true,half-monthly]` all PASS. Engine D-09 cleanup: `principal = balance` on final period; cents-drift absorbed (-$4.58 to +$2.90 across the 4 oracles). |
| AMRT-06 | 03-03, 03-04 | `scripts/amortize.py` provides JSON-in / JSON-out CLI for skill use | SATISFIED | 187-line CLI; argparse `--input <path>`; lazy-import per D-18; AmortizeRequest.model_validate_json boundary; structured JSON errors on stderr; 8 subprocess CLI tests PASS. |
| AMRT-07 | 03-04 | Tests assert `sum(principal_payments) == original_principal` exactly | SATISFIED | `assert_schedule_invariants` defined and invoked 14× (helper + 13 call sites) covering all schedule-producing tests; uses `Decimal == Decimal` exact equality. No `assertAlmostEqual` anywhere in tests. |
| AMRT-08 | 03-04 | Tests pass against all 4 golden fixtures (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr) | SATISFIED | `test_fixed_rate_oracle[wikipedia_200k_30yr|cfpb_le_162k_30yr|computed_400k_30yr|computed_200k_15yr]` 4/4 PASS with exact Decimal equality on `monthly_pi`. |

All 8 declared requirement IDs (AMRT-01..AMRT-08) are SATISFIED. REQUIREMENTS.md `Phase 3: Core Amortization | AMRT-01..08 | 8` mapping matches plan frontmatter; no orphans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `lib/amortize.py` | 254 | `assert biweekly_mode == "half-monthly"  # mypy narrowing` (load-bearing assert that elides under `python -O`) | Info | Currently no functional impact — `_build_biweekly_half_monthly` ignores `biweekly_mode`. Future refactor risk only (WR-07 in 03-REVIEW). Not blocking the phase goal. |
| `lib/amortize.py` | 247 vs `AmortizeRequest._biweekly_mode_consistency` | Two exception types (`ValueError` vs `pydantic.ValidationError`) for the same logical D-02 violation | Info | Library callers and CLI callers see different error types for one logical contract. Not blocking; WR-08 in 03-REVIEW. |
| `scripts/amortize.py` | 151-163 vs 169-174 | Two error envelope shapes for adjacent failure modes (3-key float-gate vs 6-key Pydantic) | Warning | Float-gate emits `{type, loc, msg}`; Pydantic emits `{type, loc, msg, input, url, ctx}`. WR-02 in 03-REVIEW. Phase 9 Node consumers / Phase 10 SKILL.md narration may need conditional parsing. Surfaced as HUMAN_NEEDED below. |
| `lib/amortize.py` | 203-207 (`_resolve_extra`) | Order-dependent behavior when two `(period, recurring=True)` entries share the same period (CR-01 BLOCKER per code review) | Warning (under personal-use scope) | Empirically confirmed: `[100,200]` order returns 100; `[200,100]` returns 200. Two semantically equivalent inputs produce different schedules. The locked D-05 spec uses distinct periods in all examples; this edge case is not covered by current tests or fixtures. Surfaced as HUMAN_NEEDED below. |
| `lib/models.py` | 76-91 (D-15 validator) | Validator early-returns on `payments=[]` without checking `total_interest` (WR-01 in 03-REVIEW) | Info | Engine never produces empty payments; consumer-side stub Schedule construction can silently violate D-15 invariant. Not blocking phase goal. |
| `tests/test_amortize.py` | (entire) | No test for biweekly+extras (D-06 contract: WR-05); no test for one-shot+recurring stacking on same period (WR-04); no test for rate=0 / term=1 edge cases (WR-06) | Info | Coverage gaps surfaced by 03-REVIEW. The phase goal does not enumerate these scenarios; current tests cover all stated SC1-5 success criteria. |

### Human Verification Required

#### 1. CR-01 determinism deviation acceptance

**Test:** Decide whether the engine should reject duplicate `(period, recurring=True)` `ExtraPrincipalEntry` rows at the request boundary, OR document a tie-breaker (e.g., last-in-list-wins) AND pin a fixture/test for it. Reproducer (already verified):

```
[ExtraPrincipalEntry(period=1, amount=100, recurring=True),
 ExtraPrincipalEntry(period=1, amount=200, recurring=True)]
  -> _resolve_extra(period=5, ...) returns 100.00

[ExtraPrincipalEntry(period=1, amount=200, recurring=True),
 ExtraPrincipalEntry(period=1, amount=100, recurring=True)]
  -> _resolve_extra(period=5, ...) returns 200.00
```

**Expected:** Either (a) engine rejects with a ValidationError citing D-05; (b) engine documents and tests the tie-breaker; or (c) developer accepts the status quo as out-of-scope under personal-use scope (acceptable answer: "this isn't an input class real users will hit, defer to Phase 11/12 hardening").

**Why human:** The phase goal cites "arbitrary extra-principal schedules" — whether "arbitrary" includes duplicate-period recurring entries is a product call, not a test verdict. The locked D-05 spec wording is ambiguous on ties; all examples use distinct periods. CLAUDE.md's "Math correctness first ... deterministic Python function" is potentially relevant. None of the phase plans' must_haves list duplicate-period rejection as a truth.

#### 2. WR-02 error envelope shape inconsistency acceptance

**Test:** Decide whether `scripts/amortize.py` should emit a single uniform error envelope shape across all failure modes, or accept the current two-shape behavior (3-key float-gate envelope vs 6-key Pydantic envelope).

**Expected:** Decision recorded explicitly. If unifying: build the float-gate envelope to match Pydantic's full shape `{type, loc, msg, input, url, ctx}`. If accepting: document that Phase 9/10 consumers must handle both shapes.

**Why human:** Phase 9 (DuckDB persistence + Node orchestration) and Phase 10 (Claude skill frontend) are downstream consumers of stderr JSON. Whether two shapes are tolerable is a cross-phase contract question; current Phase 3 CLI tests pass with either shape (they just `json.loads(stderr)` and check it's a list).

### Gaps Summary

No gaps blocking the phase goal. All 5 ROADMAP Success Criteria are verified by a combination of (a) the 35-case Phase 3 test suite (all passing), (b) the CLI subprocess smoke runs verifying `--help` lazy-import contract and structured error surfaces, and (c) full-suite parity (294 / 294 tests passing; mypy --strict clean over 50 files; ruff clean). All 8 AMRT requirement IDs are SATISFIED with concrete test evidence. The engine produces exact `Decimal == Decimal` parity on the 4 golden oracles, biweekly-true accelerates to 628 periods exactly with `sum(principal+extra) == original`, extra-principal scenarios shorten the schedule and land at exactly `Decimal("0.00")`, and the CLI surfaces all error modes with structured JSON.

Two items surface as HUMAN_NEEDED — neither blocks the phase goal under the project's personal-use scope (CONTEXT.md / PROJECT.md), but both warrant an explicit accept-or-fix decision before downstream phases (5, 8, 9, 10) lock against the current behavior:

1. **CR-01** (BLOCKER per code reviewer / advisory per phase yardstick): determinism deviation when duplicate `(period, recurring=True)` ExtraPrincipalEntry rows are submitted. Real-world impact for personal-use household scope is near-zero (no realistic caller workflow produces duplicates), but math-correctness narrative in CLAUDE.md is potentially affected.
2. **WR-02**: two distinct error envelope shapes across the CLI's failure modes. Affects Phase 9/10 consumer parsing.

The 35-case test suite + behavioral spot-checks confirm engine correctness on the spec'd input classes; the human items are about input classes the spec doesn't explicitly cover.

---

_Verified: 2026-04-29T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
