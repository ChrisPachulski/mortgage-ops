---
phase: 3
slug: core-amortization
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
last_audited: 2026-04-30
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0+ (per `pyproject.toml [dependency-groups].dev`) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_amortize.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~2s quick (42 tests) / ~5s full (Phase 1 + Phase 2 + Phase 3 = ~150 tests) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_amortize.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green AND `uv run mypy --strict .` AND `uv run ruff check .`
- **Max feedback latency:** 5 seconds (quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | D-14, D-15 | T-03-01-01..04 | D-15 model_validator rejects mismatched cumulative totals; frozen+strict+extra=forbid carried over | structural / typing | `uv run mypy --strict lib/models.py` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | D-14, D-15 | T-03-01-01..03 | D-15 mismatch raises `ValidationError`; empty-payments early-return is intentional and pinned | unit | `uv run pytest tests/test_models.py -x` | ✅ | ✅ green |
| 03-02-01 | 02 | 2 | AMRT-01, AMRT-02 | T-03-02-01..09 | numpy-financial wrapped (not reimplemented); D-02 validator at boundary; floats rejected by Money/Rate | structural / typing | `uv run mypy --strict lib/amortize.py` | ✅ | ✅ green |
| 03-02-02 | 02 | 2 | AMRT-03 | T-03-02-01..09 | Biweekly-true + half-monthly engines distinct; rate/26 vs rate/12 split enforced; biweekly_mode required when frequency=biweekly | structural / typing | `uv run mypy --strict lib/amortize.py` | ✅ | ✅ green |
| 03-02-03 | 02 | 2 | AMRT-04, AMRT-05 | T-03-02-01..09 | ExtraPrincipalEntry pydantic-validated (period≥1, amount>0); D-05 recurring-overrides; D-08 cap-at-balance; final cleanup quantizes to `Decimal("0.00")` | structural / typing | `uv run mypy --strict lib/amortize.py` | ✅ | ✅ green |
| 03-03-01 | 03 | 3 | AMRT-06 | T-03-03-01..09 | argparse + lazy-import (D-18); `model_validate_json` boundary (D-19); float-gate pre-Pydantic envelope; exit 0/2 | structural / typing | `uv run mypy --strict scripts/amortize.py` | ✅ | ✅ green |
| 03-04-01 | 04 | 4 | (test foundation: AMRT-01..08) | T-03-04-01,04,08 | Fixtures pin engine-emitted values with `source` provenance; no JSON-number money; no `RECORDED` placeholders | json-validate | `uv run python -c "import json; from pathlib import Path; [json.loads(p.read_text()) for p in Path('tests/fixtures/amortize').glob('*.json')]"` | ✅ | ✅ green |
| 03-04-02 | 04 | 4 | AMRT-01, AMRT-02, AMRT-03, AMRT-04, AMRT-05, AMRT-07, AMRT-08, D-15 | T-03-04-01..08 | `assert_schedule_invariants` called from every schedule-producing test (14 call sites); exact `Decimal` equality; no `assertAlmostEqual`/`pytest.approx` | unit / invariant | `uv run pytest tests/test_amortize.py -x` | ✅ | ✅ green |
| 03-04-03 | 04 | 4 | AMRT-06 | T-03-04-01..08 | Subprocess round-trip; D-18 lazy-import via `spec_from_file_location` (canonical project pattern); D-19 float rejection | integration (subprocess) | `uv run pytest tests/test_amortize.py -k "cli" -x` | ✅ | ✅ green |
| 03-05-01 | 05 | 5 | AMRT-04 (CR-01 closure) | T-03-05-01..08 | RED tests pin determinism contract: 3 negative (duplicate-recurring rejected) + 3 positive (D-05 step-up, duplicate one-shots, recurring+one-shot at same period legal) | unit (RED) | `uv run pytest tests/test_amortize.py -k "rejects_duplicate or accepts_d05_step_up or accepts_duplicate_one_shots or accepts_recurring_plus_oneshot or rejects_three_way" --tb=short` | ✅ | ✅ green |
| 03-05-02 | 05 | 5 | AMRT-04 (CR-01 closure) | T-03-05-01..08 | `_no_duplicate_recurring_periods` validator runs after D-02 consistency; raises `ValueError` (Pydantic wraps to `ValidationError`); rider scoped to `recurring=True` only | unit (GREEN) | `uv run pytest tests/test_amortize.py -k "rejects_duplicate or accepts_d05_step_up or accepts_duplicate_one_shots or accepts_recurring_plus_oneshot or rejects_three_way" -v` | ✅ | ✅ green |
| 03-06-01 | 06 | 6 | AMRT-06 (WR-02 closure) | T-03-06-01..02 | RED tests assert 6-key Pydantic v2 keyset on float-gate path + cross-shape uniformity vs native ValidationError | integration (RED) | `uv run pytest tests/test_amortize.py::test_cli_rejects_float_principal tests/test_amortize.py::test_cli_error_envelope_uniformity --tb=short` | ✅ | ✅ green |
| 03-06-02 | 06 | 6 | AMRT-06 (WR-02 closure) | T-03-06-01..02 | `_find_json_float_loc` returns `tuple[loc, value]`; envelope emits all 6 Pydantic keys (type, loc, msg, input, url, ctx); `pydantic.VERSION` lazy-imported inside `main()` (D-18 preserved) | integration (GREEN) | `uv run pytest tests/test_amortize.py::test_cli_rejects_float_principal tests/test_amortize.py::test_cli_error_envelope_uniformity -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AMRT-01 | `lib/amortize.py` wraps numpy-financial (does NOT reimplement) | structural | `uv run pytest tests/test_amortize.py::test_amortize_module_uses_numpy_financial -x` | ✅ |
| AMRT-02 | Fixed-rate schedule: 4 golden oracles | unit (parametrized) | `uv run pytest tests/test_amortize.py::test_fixed_rate_oracle -x` | ✅ |
| AMRT-03 | Biweekly true mode + half-monthly mode (separate algorithms) | unit | `uv run pytest tests/test_amortize.py -k "biweekly" -x` | ✅ |
| AMRT-04 | Extra-principal: one-shot + recurring + step-up + cap-at-balance | unit | `uv run pytest tests/test_amortize.py -k "extra" -x` | ✅ |
| AMRT-05 | Final-payment cleanup (balance == Decimal("0.00") exactly) | invariant | `uv run pytest tests/test_amortize.py -k "final_payment" -x` | ✅ |
| AMRT-06 | CLI smoke: JSON-in/out, lazy `--help`, error surface, 6-key envelope | integration (subprocess) | `uv run pytest tests/test_amortize.py -k "cli" -x` | ✅ |
| AMRT-07 | `sum(principal) + sum(extra_principal) == original_principal` exactly | invariant (asserted on every schedule-producing test via shared helper) | `uv run pytest tests/test_amortize.py -x` (helper `assert_schedule_invariants` called from 14 call sites) | ✅ |
| AMRT-08 | All 4 golden oracles pass with exact Decimal equality | unit | `uv run pytest tests/test_amortize.py::test_fixed_rate_oracle -x` (4 parametrized cases: wikipedia_200k_30yr, cfpb_le_162k_30yr, computed_400k_30yr, computed_200k_15yr) | ✅ |

---

## Nyquist Coverage Matrix

> Each branch sampled at least once with rationale. AMRT-07 invariant fires on every schedule-producing test (no skipping).

| Branch / Behavior | Test | Sampling Rationale |
|-------------------|------|-------------------|
| Fixed monthly, baseline | `test_fixed_rate_oracle[wikipedia_200k_30yr]` | Wikipedia oracle: simplest baseline; locks fundamental math |
| Fixed monthly, low rate | `test_fixed_rate_oracle[cfpb_le_162k_30yr]` | Pins regulator-published example |
| Fixed monthly, scale-up | `test_fixed_rate_oracle[computed_400k_30yr]` | 2× principal — proves no scale-dependent bugs |
| Fixed monthly, shorter term | `test_fixed_rate_oracle[computed_200k_15yr]` | 15yr term — proves term-independence |
| Biweekly true | `test_biweekly_true_oracle` | rate/26 + half-monthly-pmt; acceleration to ~628 periods |
| Biweekly half-monthly | `test_biweekly_half_monthly_oracle` | rate/12 + monthly schedule with biweekly cashflow label |
| Biweekly default mode | `test_biweekly_mode_defaults_to_true_when_omitted` | D-02 default behavior pinned |
| D-02 validator | `test_amortize_request_rejects_biweekly_mode_when_monthly` | Cross-field validator pinned at boundary |
| Extra one-shot | `test_extra_oneshot_period_60` | period 60 only, $5000; shortens by ~3-4 periods |
| Extra recurring | `test_extra_recurring_200_from_period_1` | $200/period from period 1; meaningfully shortens schedule |
| Extra step-up | `test_extra_step_up_200_to_300_at_period_13` | proves later-recurring-overrides-earlier (D-05) |
| Extra cap-at-balance | `test_extra_caps_at_remaining_balance_silently` | recurring $50k on small loan; D-08 cap; `final_payment_adjusted=True` |
| Extra zero/negative period | `test_extra_principal_entry_rejects_period_zero` | Field(ge=1) at boundary |
| Extra zero amount | `test_extra_principal_entry_rejects_zero_amount` | Field(gt=0) at boundary |
| Final cleanup, fixed | `test_final_payment_cleans_to_zero_fixed` | drift absorption; balance == `Decimal("0.00")` |
| Final cleanup, biweekly | `test_final_payment_cleans_to_zero_biweekly` | accelerated payoff; flag fires (parametrized over biweekly modes) |
| AMRT-07 invariant (global) | `assert_schedule_invariants` invoked by every schedule-test | 14 call sites; sum(principal+extra) == original_principal exact |
| D-15 model invariant | `test_schedule_d15_invariant_holds_for_all_engine_outputs` (engine) + `test_schedule_total_interest_must_match_last_cumulative` (model) | engine outputs satisfy D-15; direct-construction with mismatched totals raises `ValidationError` |
| D-15 empty-payments guard | `test_schedule_with_empty_payments_skips_d15_validator` | empty-payments early-return is intentional and pinned |
| Month-end edge | `test_month_end_origination_clips_to_feb_28` | Jan 31 + 1mo → Feb 28; locks `relativedelta` behavior |
| Date synthesis | `test_build_schedule_synthesizes_origination_when_none` | D-12 path with `monkeypatch` on `datetime.now` |
| CLI happy path | `test_cli_smoke_subprocess_round_trip` | subprocess: input JSON in, output JSON out |
| CLI fast `--help` | `test_cli_help_does_not_import_lib_amortize` | import-mock check via `spec_from_file_location` (canonical project pattern) |
| CLI missing input | `test_cli_no_input_returns_argparse_error` | exit 2 + argparse usage on stderr |
| CLI file not found | `test_cli_file_not_found_returns_structured_error` | exit 2 + structured JSON envelope |
| CLI invalid JSON | `test_cli_invalid_json_input` | exit 2 + structured error |
| CLI float in money field | `test_cli_rejects_float_principal` | 6-key Pydantic v2 envelope (WR-02 closure) |
| CLI D-02 violation at boundary | `test_cli_d02_violation_at_boundary` | end-to-end Pydantic ValidationError surface |
| CLI biweekly round-trip | `test_cli_biweekly_round_trip` | end-to-end biweekly path through CLI |
| CLI envelope uniformity | `test_cli_error_envelope_uniformity` | float-gate keyset == native ValidationError keyset (6 Pydantic keys) |
| CR-01 duplicate recurring [100,200] | `test_amortize_request_rejects_duplicate_recurring_periods` | order-1 rejected at boundary |
| CR-01 duplicate recurring [200,100] | `test_amortize_request_rejects_duplicate_recurring_periods_reversed` | order-2 rejected at boundary (determinism contract) |
| CR-01 three-way duplicate | `test_amortize_request_rejects_three_way_duplicate_recurring` | n-way rejection generalizes |
| CR-01 positive: D-05 step-up | `test_amortize_request_accepts_d05_step_up_with_distinct_periods` | over-rejection guard: distinct-period step-up legal |
| CR-01 positive: duplicate one-shots | `test_amortize_request_accepts_duplicate_one_shots_at_same_period` | over-rejection guard: one-shot stacking legal |
| CR-01 positive: recurring + one-shot | `test_amortize_request_accepts_recurring_plus_oneshot_at_same_period` | over-rejection guard: mixed-recurring legal |
| AMRT-08 oracle parity | `test_fixed_rate_oracle` parametrized over `golden_pmt.json` | 4 fixtures × exact `==` comparison; AMRT-08 contract |

---

## Wave 0 Requirements

- [x] `tests/test_amortize.py` — created in plan 03-04; 42 tests covering AMRT-01..08 + D-02 + D-15 + month-end + CLI + CR-01 + WR-02; defines top-of-file `assert_schedule_invariants(schedule, original_principal)` helper (14 call sites)
- [x] `tests/conftest.py` — extended with `amortize_fixture` loader (additive change; existing fixtures untouched)
- [x] `tests/fixtures/amortize/` — 7 JSON fixtures (`biweekly_half_monthly_200k_6_5.json`, `biweekly_true_200k_6_5.json`, `extra_caps_at_balance.json`, `extra_oneshot_5k_period_60.json`, `extra_recurring_200_30yr.json`, `extra_step_up_200_to_300.json`, `month_end_jan_31.json`); `golden_pmt.json` reused for AMRT-08
- [x] `lib/amortize.py` — production code: scalar per-period engine + `ExtraPrincipalEntry` + `AmortizeRequest` + D-02 + D-05 (CR-01) validators
- [x] `lib/models.py` — extended `Payment` with `cumulative_interest` + `cumulative_principal` (D-14); extended `Schedule` with `final_payment_adjusted` + D-15 model_validator
- [x] `tests/test_models.py::test_schedule_aggregates_loan_and_payments` — updated to satisfy D-15 validator
- [x] `scripts/amortize.py` — argparse + lazy-import + boundary validation + 6-key Pydantic v2 envelope (WR-02 closure)
- [x] `pyproject.toml` — `numpy-financial==1.0.0` pinned

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual sanity-check on biweekly-true acceleration vs monthly equivalent | AMRT-03 | Cross-tool verification against external mortgage calculator (e.g., bankrate.com) — sanity, not contract | Run `uv run python scripts/amortize.py --input tests/fixtures/amortize/biweekly_true_200k_6_5.json` and compare total interest to bankrate's biweekly calculator output for the same loan; document delta in commit message if deviates |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all required test files (all 8 wave-0 artifacts present)
- [x] No watch-mode flags (pytest invoked with `-x`, no `--looponfail`)
- [x] Feedback latency < 5s (quick run `tests/test_amortize.py` runs in ~1.6s)
- [x] AMRT-07 invariant helper (`assert_schedule_invariants`) called from every schedule-producing test (14 call sites; gate ≥11)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-30

---

## Validation Audit 2026-04-30

| Metric | Count |
|--------|-------|
| Gaps found | 0 (implementation) / 1 (documentation lag) |
| Resolved | 1 |
| Escalated | 0 |

**Audit summary:** Phase 3 implementation is fully Nyquist-compliant. All 8 AMRT requirements + D-14/D-15 + CR-01 + WR-02 closures have automated coverage. Test suite green: 61/61 (`tests/test_amortize.py` 42, `tests/test_models.py` 19). The only audit finding was documentation lag — the Per-Task Verification Map carried the planner's pre-execution scaffold row instead of the 13 actual task entries, and the `File Exists` column read ❌ Wave 0. Updated to reflect post-execution reality. No new tests generated (none missing). Phase verifier independently scored 5/5 on 2026-04-29 with both gap closures (CR-01 plan 03-05, WR-02 plan 03-06) verified against commits and code anchors.
