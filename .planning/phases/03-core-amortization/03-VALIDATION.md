---
phase: 3
slug: core-amortization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
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
| **Estimated runtime** | ~5s quick / ~30s full (Phase 1 + Phase 2 + new Phase 3 = ~224 tests) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_amortize.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green AND `uv run mypy --strict .` AND `uv run ruff check .`
- **Max feedback latency:** 5 seconds (quick run)

---

## Per-Task Verification Map

> Filled by gsd-planner per plan/task. Initial scaffold below; planner will append rows keyed by actual task IDs (e.g., `03-01-01`, `03-02-03`).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-XX-YY | XX | W | AMRT-01..08 | T-03-XX / — | (per-task; or N/A for pure-math) | unit/invariant/integration | `uv run pytest tests/test_amortize.py::<node> -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AMRT-01 | `lib/amortize.py` wraps numpy-financial (does NOT reimplement) | structural | `uv run pytest tests/test_amortize.py::test_amortize_module_uses_numpy_financial -x` | ❌ Wave 0 |
| AMRT-02 | Fixed-rate schedule: 4 golden oracles | unit (parametrized) | `uv run pytest tests/test_amortize.py::test_fixed_rate_oracle -x` | ❌ Wave 0 |
| AMRT-03 | Biweekly true mode + half-monthly mode (separate algorithms) | unit | `uv run pytest tests/test_amortize.py -k "biweekly" -x` | ❌ Wave 0 |
| AMRT-04 | Extra-principal: one-shot + recurring + step-up + cap-at-balance | unit | `uv run pytest tests/test_amortize.py -k "extra_principal" -x` | ❌ Wave 0 |
| AMRT-05 | Final-payment cleanup (balance == Decimal("0.00") exactly) | invariant | `uv run pytest tests/test_amortize.py -k "final_payment" -x` | ❌ Wave 0 |
| AMRT-06 | CLI smoke: JSON-in/out, lazy `--help`, error surface | integration (subprocess) | `uv run pytest tests/test_amortize.py -k "cli" -x` | ❌ Wave 0 |
| AMRT-07 | `sum(principal) + sum(extra_principal) == original_principal` exactly | invariant (asserted on EVERY schedule-producing test via shared helper) | covered by every test calling `build_schedule` via `assert_schedule_invariants` | ❌ Wave 0 |
| AMRT-08 | All 4 golden oracles pass with exact Decimal equality | unit | `uv run pytest tests/test_amortize.py::test_fixed_rate_oracle -x` (uses Phase 1's `golden_fixture`) | ❌ Wave 0 |

---

## Nyquist Coverage Matrix

> Each branch sampled at least once with rationale. AMRT-07 invariant fires on EVERY schedule-producing test (no skipping).

| Branch / Behavior | Test | Sampling Rationale |
|-------------------|------|-------------------|
| Fixed monthly, baseline | `test_fixed_rate_oracle[wikipedia]` | Wikipedia oracle: simplest baseline; locks fundamental math |
| Fixed monthly, low rate | `test_fixed_rate_oracle[cfpb_le]` | Pins regulator-published example |
| Fixed monthly, scale-up | `test_fixed_rate_oracle[400k]` | 2× principal — proves no scale-dependent bugs |
| Fixed monthly, shorter term | `test_fixed_rate_oracle[200k_15yr]` | 15yr term — proves term-independence |
| Biweekly true | `test_biweekly_true_oracle` | rate/26 + half-monthly-pmt; acceleration to ~628 periods |
| Biweekly half-monthly | `test_biweekly_half_monthly_oracle` | rate/12 + monthly schedule with biweekly cashflow label |
| Extra one-shot | `test_extra_oneshot_period_60` | period 60 only, $5000; shortens by ~3-4 periods |
| Extra recurring | `test_extra_recurring_200_from_period_1` | $200/period from period 1; meaningfully shortens schedule |
| Extra step-up | `test_extra_step_up_200_to_300_at_period_13` | proves later-recurring-overrides-earlier (D-05) |
| Extra cap-at-balance | `test_extra_caps_at_remaining_balance_silently` | recurring $50k on small loan; D-08 cap; `final_payment_adjusted=True` |
| Final cleanup, fixed | `test_final_payment_cleans_to_zero_fixed` | drift absorption; balance == `Decimal("0.00")` |
| Final cleanup, biweekly-true | `test_final_payment_cleans_to_zero_biweekly` | accelerated payoff; flag fires |
| AMRT-07 invariant (global) | `assert_schedule_invariants` invoked by EVERY schedule-test | sum(principal+extra) == original_principal exact |
| D-15 model invariant | `test_schedule_total_interest_matches_last_cumulative` | direct-construction tests with mismatched totals raise `ValidationError` |
| Month-end edge | `test_month_end_origination_clips_to_feb_28` | Jan 31 + 1mo → Feb 28; locks `relativedelta` behavior |
| Date synthesis | `test_build_schedule_synthesizes_origination_when_none` | D-12 path with `monkeypatch` on `datetime.now` |
| CLI happy path | `test_cli_smoke_subprocess_round_trip` | subprocess: input JSON in, output JSON out |
| CLI fast `--help` | `test_cli_help_does_not_import_lib_amortize` | import-mock check (preferred over timing) |
| CLI missing input | `test_cli_no_input_returns_pydantic_error` | exit 2 + Pydantic JSON on stderr |
| CLI invalid JSON | `test_cli_invalid_json_input` | exit 2 + structured error |
| CLI float in money field | `test_cli_rejects_float_principal` | Pydantic strict-mode rejection at boundary |
| AMRT-08 oracle parity | `test_fixed_rate_oracle` parametrized over `golden_pmt.json` | 4 fixtures × exact `==` comparison; AMRT-08 contract |

---

## Wave 0 Requirements

- [ ] `tests/test_amortize.py` — new file; ~22 tests covering AMRT-01..08 + D-15 + month-end + CLI; defines top-of-file `assert_schedule_invariants(schedule, original_principal)` helper
- [ ] `tests/conftest.py` — extend with `amortize_fixture` loader (small additive change; existing fixtures untouched)
- [ ] `tests/fixtures/amortize/` — new directory; 11 JSON fixtures (per RESEARCH §9: `fixed_30yr_400k_6_5.json`, `biweekly_true_200k_6_5.json`, `biweekly_half_monthly_200k_6_5.json`, `extra_oneshot_5k_period_60.json`, `extra_recurring_200_30yr.json`, `extra_step_up_200_to_300.json`, `extra_caps_at_balance.json`, `month_end_jan_31.json`, plus the four `golden_pmt.json` references reused for AMRT-08)
- [ ] `lib/amortize.py` — production code: scalar per-period engine + `ExtraPrincipalEntry` Pydantic model + `AmortizeRequest` boundary type + module docstring with bug #130/#131 avoidance comment block
- [ ] `lib/models.py` — extend `Payment` with `cumulative_interest: Money = Decimal("0.00")` + `cumulative_principal: Money = Decimal("0.00")`; extend `Schedule` with `final_payment_adjusted: bool = False` + `@model_validator(mode="after")` enforcing D-15
- [ ] `tests/test_models.py::test_schedule_aggregates_loan_and_payments` — UPDATE to satisfy the new D-15 validator (set `total_interest` to match `payments[-1].cumulative_interest`)
- [ ] `scripts/amortize.py` — new file at project root; argparse + lazy-import of `lib.amortize` + `Loan.model_validate_json` boundary + stdout JSON output
- [ ] `pyproject.toml` — `numpy-financial` already pinned in dependencies; verify version pin includes Decimal-supporting release; otherwise no change

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual sanity-check on biweekly-true acceleration vs monthly equivalent | AMRT-03 | Cross-tool verification against external mortgage calculator (e.g., bankrate.com) — sanity, not contract | Run `uv run python -m scripts.amortize --input tests/fixtures/amortize/biweekly_true_200k_6_5.json` and compare total interest to bankrate's biweekly calculator output for the same loan; document delta in commit message if deviates |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (Wave 0 = first-wave tests scaffold all required test files)
- [ ] No watch-mode flags (pytest invoked with `-x`, no `--looponfail`)
- [ ] Feedback latency < 5s (quick run on `tests/test_amortize.py`)
- [ ] AMRT-07 invariant helper (`assert_schedule_invariants`) called from EVERY schedule-producing test
- [ ] `nyquist_compliant: true` set in frontmatter when planner finalizes Per-Task Verification Map

**Approval:** pending
