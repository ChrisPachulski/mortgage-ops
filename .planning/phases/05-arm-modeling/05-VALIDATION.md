---
phase: 5
slug: arm-modeling
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-30
updated: 2026-04-30
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `05-RESEARCH.md` §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project standard, configured in `pyproject.toml` since Phase 1) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_arm.py -x` |
| **Full suite command** | `pytest -x` |
| **Estimated runtime** | ~5–10s for `tests/test_arm.py`; ~30s for full suite (Phase 4 baseline 379 passed + 4 skipped, Phase 5 adds ~30–40 tests) |

**Phase gate:** Full suite green + `mypy --strict` clean + `ruff` clean across `lib/arm.py`, `scripts/arm_simulate.py`, `tests/test_arm.py`, `scripts/_cli_helpers.py` (factored by Plan 05-04a) before `/gsd-verify-work`.

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_arm.py -x` (quick — ~5–10s)
- **After every plan wave:** Run `pytest -x` (full suite — ~30s)
- **Before `/gsd-verify-work`:** Full suite green + mypy --strict + ruff clean
- **Max feedback latency:** 30 seconds (full suite)

---

## Per-Task Verification Map

> Populated by planner per BLOCKER I-001 (gsd-plan-checker iteration 1, 2026-04-30).
> Plan 05-04 has been split into 05-04a (cli-helpers-factor; hygiene) and 05-04b (arm-cli; ARM-08 closure) per BLOCKER I-003.
> 29 tasks across 8 plans (05-00, 05-01, 05-02, 05-03, 05-04a, 05-04b, 05-05, 05-06).
> Threat refs cite the threat IDs declared in each plan's `<threat_model>` section.
> Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T-00-01 | 05-00 | 0 | (Wave 0 stubs) | — | N/A — fixture loader (test infra only) | unit | `python -c "from tests.conftest import *; print('OK')"` | ❌ W0 | ⬜ pending |
| T-00-02 | 05-00 | 0 | (Wave 0 stubs) | — | N/A — empty fixture dirs | structural | `test -d tests/fixtures/arm && test -d tests/fixtures/arm/oracle` | ❌ W0 | ⬜ pending |
| T-00-03 | 05-00 | 0 | (Wave 0 stubs) | — | N/A — xfail-decorated stubs only | meta | `pytest tests/test_arm.py -v --no-header` (all xfail) | ❌ W0 | ⬜ pending |
| T-00-04 | 05-00 | 0 | (Wave 0 stubs) | — | Phase 4 baseline preserved | smoke | `pytest -q` (379+ passed, 4 skipped, ~32 xfailed) | ❌ W0 | ⬜ pending |
| T-01-01 | 05-01 | 1 | (D-14 hygiene) | — | N/A — pure helper promotion | unit | `python -c "from lib.money import quantize_rate, _RATE_QUANTUM; print('OK')"` | ❌ W1 | ⬜ pending |
| T-01-02 | 05-01 | 1 | (D-14 hygiene) | — | Phase 4 byte-equivalent | smoke | `pytest tests/test_affordability.py -q` | ❌ W1 | ⬜ pending |
| T-01-03 | 05-01 | 1 | (D-14 hygiene) | — | quantize_rate ROUND_HALF_UP semantics | unit | `pytest tests/test_money.py::test_quantize_rate_round_half_up -x` | ❌ W1 | ⬜ pending |
| T-01-04 | 05-01 | 1 | (D-14 hygiene) | — | Phase 3 + Phase 4 baselines preserved | smoke | `pytest -q` | ❌ W1 | ⬜ pending |
| T-02-01 | 05-02 | 2 | ARM-01 | T-05-02, T-05-03 (model-layer) | Pydantic strict/frozen/forbid contract; required floor_rate; aligned index_path validator | unit | `python -c "from lib.arm import ARMTerms, IndexPathEntry, ARMRequest, ARMPayment, ResetEvent, ARMSchedule; print('OK')"` | ❌ W2 | ⬜ pending |
| T-02-02 | 05-02 | 2 | ARM-01 | T-05-02, T-05-03 | extra="forbid" rejects unknown fields (I-007); missing floor_rate raises ValidationError; misaligned index_path raises | unit | `pytest tests/test_arm.py::test_arm_terms_field_set tests/test_arm.py::test_arm_terms_missing_floor_rate_raises tests/test_arm.py::test_note_rate_defaults_to_loan_annual_rate tests/test_arm.py::test_arm_request_misaligned_index_path_raises tests/test_arm.py::test_arm_request_aligned_index_path_succeeds -xvs` | ❌ W2 | ⬜ pending |
| T-02-03 | 05-02 | 2 | (regression check) | T-05-25 | Phase 3 + Phase 4 + Wave 0/1 baselines preserved | smoke | `pytest -q` | ❌ W2 | ⬜ pending |
| T-03-01 | 05-03 | 3 | ARM-02, ARM-03, ARM-04, ARM-05 | T-05-04..T-05-09 (engine layer) | D-02 reset formula; D-05 per-epoch re-amortize; D-09 final cleanup; bear-trap shortcut NOT taken (I-006) | unit | `python -c "from lib.arm import build_arm_schedule, _compute_reset_triggers, _compute_new_rate, ARMRequest; print('OK')"` | ❌ W3 | ⬜ pending |
| T-03-02 | 05-03 | 3 | ARM-02, ARM-03, ARM-04, ARM-05, ARM-07 | T-05-04..T-05-09 | 8 invariant tests pinning engine math (period jumps, off-by-one, cap precedence, floor enforcement, continuous numbering, cumulative totals, full-remaining-term re-amortization, non-final-epoch balance > 0) | invariant | `pytest tests/test_arm.py -k "test_arm_5_1_payment_jump_at_61 or test_arm_initial_cap_at_first_reset or test_arm_lifetime_cap_binds or test_arm_floor_below_margin_blocked or test_arm_continuous_period_numbering or test_cumulative_totals_continuous_across_resets or test_full_remaining_term_re_amortization or test_non_final_epoch_does_not_zero_balance" -xvs` | ❌ W3 | ⬜ pending |
| T-03-03 | 05-03 | 3 | (regression check) | T-05-25 | Phase 3 + Phase 4 + Wave 0/1/2 baselines preserved | smoke | `pytest -q` | ❌ W3 | ⬜ pending |
| T-04a-01 | 05-04a | 4 | (D-discretion factor) | T-05-01 (helper layer), T-05-23 | scripts/_cli_helpers.py exports find_json_float_loc + make_decimal_type_envelope; lazy pydantic.VERSION import preserves D-18 fast --help | unit | `python -c "import sys; sys.path.insert(0, '.'); from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope; print('OK')"` | ❌ W4 | ⬜ pending |
| T-04a-02 | 05-04a | 4 | (D-discretion factor) | T-05-01 (helper layer), T-05-23 | 18 parametric tests pinning JSON-float walker + 6-key envelope shape | unit | `pytest tests/test_cli_helpers.py -xvs` | ❌ W4 | ⬜ pending |
| T-04a-03 | 05-04a | 4 | (regression check) | T-05-25 | Phase 3 + Phase 4 byte-equivalent after refactor; inline _find_json_float_loc removed; imports added | smoke | `pytest tests/test_amortize.py tests/test_affordability.py tests/test_cli_helpers.py -q` | ❌ W4 | ⬜ pending |
| T-04b-01 | 05-04b | 4 | ARM-08 | T-05-01 (CLI), T-05-24, T-05-26 | scripts/arm_simulate.py mirrors D-07; --help fast (no lib.arm import); sys.path injection precedes lazy imports | smoke | `python scripts/arm_simulate.py --help` | ❌ W4 | ⬜ pending |
| T-04b-02 | 05-04b | 4 | ARM-08 | T-05-01 (CLI), T-05-24, T-05-26 | 8 ARM-08 stub flips: subprocess round-trip with last-trigger pin (I-005), --help no-import, 4× float-rejects, envelope uniformity, misaligned period | unit | `pytest tests/test_arm.py -k "test_cli_smoke_subprocess_round_trip or test_cli_help_does_not_import_lib_arm or test_cli_rejects_float_principal or test_cli_rejects_float_assumed_index_rate or test_cli_rejects_float_index_path_value or test_cli_rejects_float_floor_rate or test_cli_error_envelope_uniformity or test_cli_misaligned_index_path_period_rejected" -xvs` | ❌ W4 | ⬜ pending |
| T-04b-03 | 05-04b | 4 | (regression check) | T-05-25 | Phase 3 + Phase 4 + Plan 05-04a baselines preserved; 418 passed + 14 xfailed | smoke | `pytest -q` | ❌ W4 | ⬜ pending |
| T-05-01 | 05-05 | 5 | ARM-09 | — | references/arm-mechanics.md exists with 7 D-08 [REVISED] sections + corrected citations (Fannie B2-1.4-02, Freddie 6302.7(b), CFPB §1951, AmericU) | structural | `test -f references/arm-mechanics.md && grep -c 'b2-1.4-02' references/arm-mechanics.md` returns ≥ 1 | ❌ W5 | ⬜ pending |
| T-05-02 | 05-05 | 5 | ARM-09 | — | ARMTerms docstring cites references/arm-mechanics.md (ROADMAP SC-5) | structural | `grep -c 'See references/arm-mechanics.md' lib/arm.py` returns 1 | ❌ W5 | ⬜ pending |
| T-05-03 | 05-05 | 5 | ARM-09 | — | 3 ARM-09 stubs flipped: doc-sections-present, docstring-cites, citations-present | unit | `pytest tests/test_arm.py -k "test_arm_mechanics_doc_sections_present or test_arm_terms_docstring_cites_arm_mechanics or test_arm_mechanics_citations" -xvs` | ❌ W5 | ⬜ pending |
| T-05-04 | 05-05 | 5 | (regression check) | T-05-25 | All prior baselines preserved | smoke | `pytest -q` | ❌ W5 | ⬜ pending |
| T-06-01 | 05-06 | 6 | ARM-02..05 | T-05-32, T-05-36 | 11 hand-calc fixtures generated by engine + applied_cap classification spans all 5 Literals (D-10) + cap-bound trio has hand_calc_check Decimal witness (I-004 — Fannie B2-1.4-02 formula) | fixture | `python scripts/_generate_arm_fixtures.py && python -c "import json,glob; vals=set(); [vals.add(re['applied_cap']) for f in glob.glob('tests/fixtures/arm/*.json') for re in json.load(open(f))['expected']['reset_events']]; assert {'initial','periodic','lifetime','floor','none'} <= vals; print('OK')"` | ❌ W6 | ⬜ pending |
| T-06-02 | 05-06 | 6 | ARM-06 | T-05-33, T-05-34 | 5 oracle PDFs captured (Bankrate 5/1/7/1/10/1 + Vertex42 5/1 + AmericU 5/6 SOFR) | smoke | `ls tests/fixtures/arm/oracle/*.pdf | wc -l` returns ≥ 5 | ❌ W6 | ⬜ pending |
| T-06-03 | 05-06 | 6 | ARM-06 | T-05-33 | 5 oracle PDFs transcribed to .json with expected_per_period rows | structural | `bash -c 'for f in tests/fixtures/arm/oracle/*.json; do python -c "import json; d=json.load(open(\"$f\")); assert \"expected_per_period\" in d"; done'` | ❌ W6 | ⬜ pending |
| T-06-04 | 05-06 | 6 | ARM-02, ARM-03, ARM-04, ARM-06, ARM-07 | T-05-33, T-05-35, T-05-36, T-05-37 | 11 fixture-based stub flips via _request_from_fixture helper (I-010); cap-bound fixtures cross-checked against hand_calc_check (I-004); applied_cap citation coverage verified | invariant | `pytest tests/test_arm.py -k "test_arm_5_1_payment_jump_at_61 or test_arm_7_1_payment_jump_at_85 or test_arm_10_1_payment_jump_at_121 or test_arm_5_6_payment_jump_at_61_and_67 or test_arm_initial_cap_at_first_reset or test_arm_lifetime_cap_binds or test_arm_floor_below_margin_blocked or test_arm_5_1_off_by_one_negative or test_oracle_cross_validation_5_1 or test_oracle_cross_validation_5_6 or test_applied_cap_citation_coverage" -xvs` | ❌ W6 | ⬜ pending |
| T-06-05 | 05-06 | 6 | (final phase closure) | T-05-25 | 432 passed, 0 xfailed, 4 skipped; all 9 ARM-N closed; ROADMAP SC-1..SC-5 verified; mypy + ruff clean across 12 files | smoke | `pytest -q && mypy --strict lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py scripts/_generate_arm_fixtures.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py` | ❌ W6 | ⬜ pending |

*File-Exists legend: ❌ Wn = file is created/modified by Wave n. ✅ = already exists in repo (Phase 1/3/4 artifacts). The Wave-0 row "❌ W0" means tests/test_arm.py is created in Wave 0 (Plan 05-00) and downstream waves flip its xfail decorators.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Planner-checker enforcement: every task has a row; threat refs cite per-plan `<threat_model>` IDs.*

---

## Phase Requirements → Test Map (locked from research)

| Req ID | Behavior | Test | File Exists |
|--------|----------|------|---|
| ARM-01 | ARMTerms has 8 explicit fields + REQUIRED floor_rate + optional note_rate | `test_arm_terms_field_set` | ❌ W0 |
| ARM-01 | ARMTerms rejects missing floor_rate at construction | `test_arm_terms_missing_floor_rate_raises` | ❌ W0 |
| ARM-01 | ARMTerms.note_rate defaults to None; engine substitutes loan.annual_rate | `test_note_rate_defaults_to_loan_annual_rate` | ❌ W0 |
| ARM-02 | 5/1 (initial=60, reset=12) builds correctly | `test_arm_5_1_payment_jump_at_61` | ❌ W0 |
| ARM-02 | 7/1 (initial=84, reset=12) builds correctly | `test_arm_7_1_payment_jump_at_85` | ❌ W0 |
| ARM-02 | 10/1 (initial=120, reset=12) builds correctly | `test_arm_10_1_payment_jump_at_121` | ❌ W0 |
| ARM-02 | 5/6 (initial=60, reset=6) — first reset 61, second 67 | `test_arm_5_6_payment_jump_at_61_and_67` | ❌ W0 |
| ARM-03 | Reset formula clamp(quantize(index+margin), low=floor, high=min(periodic_ceil, lifetime_ceil)) | `test_reset_formula_locked` | ❌ W0 |
| ARM-03 | First-reset uses initial_cap; subsequent uses periodic_cap | `test_arm_initial_cap_at_first_reset` | ❌ W0 |
| ARM-03 | Lifetime cap binds when fully-indexed > note_rate + lifetime_cap | `test_arm_lifetime_cap_binds` | ❌ W0 |
| ARM-04 | Floor enforcement: new_rate >= max(margin, floor_rate) | `test_arm_floor_below_margin_blocked` | ❌ W0 |
| ARM-05 | Re-amortization over FULL remaining term | `test_full_remaining_term_re_amortization` | ❌ W0 |
| ARM-05 | Continuous period numbering 1..N; final balance == 0.00 | `test_arm_continuous_period_numbering` | ❌ W0 |
| ARM-05 | Cumulative totals continuous across epoch boundaries | `test_cumulative_totals_continuous_across_resets` | ❌ W0 |
| ARM-05 | Non-final epoch's last sliced row has balance > 0.00 | `test_non_final_epoch_does_not_zero_balance` | ❌ W0 |
| ARM-05 | First epoch matches Phase 1 oracle ($400k @ 6.5%/30yr → $2528.27) | `test_initial_fixed_period_matches_phase1_oracle` | ❌ W0 |
| ARM-06 | Hand-calc + Bankrate/Vertex42 capture AGREE EXACTLY (5/1) | `test_oracle_cross_validation_5_1` | ❌ W0 |
| ARM-06 | 5/6 ARM oracle: AmericU disclosure cross-validation | `test_oracle_cross_validation_5_6` | ❌ W0 |
| ARM-07 | Off-by-one negative: month 59 still old; month 61 already new | `test_arm_5_1_off_by_one_negative` | ❌ W0 |
| ARM-07 | Reset boundary: payments[59].rate == initial; payments[60].rate == new | (covered by `test_arm_5_1_payment_jump_at_61`) | ❌ W0 |
| ARM-08 | CLI subprocess round-trip: write JSON → invoke → parse stdout | `test_cli_smoke_subprocess_round_trip` | ❌ W0 |
| ARM-08 | CLI --help fast (lazy-import; no lib.arm before argparse) | `test_cli_help_does_not_import_lib_arm` | ❌ W0 |
| ARM-08 | CLI rejects JSON-float in loan.principal with 6-key envelope | `test_cli_rejects_float_principal` | ❌ W0 |
| ARM-08 | CLI rejects JSON-float in assumed_index_rate | `test_cli_rejects_float_assumed_index_rate` | ❌ W0 |
| ARM-08 | CLI rejects JSON-float in index_path[].value (deep loc) | `test_cli_rejects_float_index_path_value` | ❌ W0 |
| ARM-08 | CLI rejects JSON-float in floor_rate | `test_cli_rejects_float_floor_rate` | ❌ W0 |
| ARM-08 | CLI envelope-uniformity: float-gate + Pydantic emit identical 6-key shape | `test_cli_error_envelope_uniformity` | ❌ W0 |
| ARM-08 | CLI surfaces misaligned index_path period as 6-key envelope | `test_cli_misaligned_index_path_period_rejected` | ❌ W0 |
| ARM-09 | references/arm-mechanics.md exists with all D-08 sections | `test_arm_mechanics_doc_sections_present` | ❌ W0 |
| ARM-09 | ARMTerms docstring cites references/arm-mechanics.md | `test_arm_terms_docstring_cites_arm_mechanics` | ❌ W0 |
| ARM-09 | references/arm-mechanics.md cites B2-1.4-02 + Freddie 6302.7(b) + CFPB §1951 + AmericU 5/6 | `test_arm_mechanics_citations` | ❌ W0 |
| Cross  | applied_cap citation-coverage: every Literal value exercised by ≥1 fixture (D-10) | `test_applied_cap_citation_coverage` | ❌ W0 |
| Cross  | Phase 3 + Phase 4 suites still pass after quantize_rate promotion (no regression) | `pytest tests/test_amortize.py tests/test_affordability.py -x` | ✓ existing |

---

## ROADMAP Success Criteria → Test Map

| SC | Description | Pinned Test |
|----|-------------|-------------|
| SC-1 | ARMTerms has 8 explicit fields | `test_arm_terms_field_set` |
| SC-2 | 5/1 ARM payment-jump at month 61 (not 60, not 62) | `test_arm_5_1_payment_jump_at_61` |
| SC-3 | Both reset-month conventions (60 and 61) covered as separate fixtures | `test_arm_5_1_payment_jump_at_61` (positive) + `test_arm_5_1_off_by_one_negative` (negative) |
| SC-4 | Floor enforced: never below max(margin, configured_floor) | `test_arm_floor_below_margin_blocked` |
| SC-5 | references/arm-mechanics.md cites Selling Guides; cited from ARMTerms docstring | `test_arm_mechanics_doc_sections_present` + `test_arm_terms_docstring_cites_arm_mechanics` + `test_arm_mechanics_citations` |

---

## applied_cap Literal Coverage (D-10 citation-coverage meta-test)

Every value of `Literal["initial", "periodic", "lifetime", "floor", "none"]` MUST appear in `expected.reset_events[*].applied_cap` of at least one fixture. Meta-test asserts coverage by walking all `tests/fixtures/arm/*.json` and verifying every Literal value is present.

| applied_cap | Fixture pinning the value |
|---|---|
| `"initial"` | `arm_initial_cap_at_first_reset.json` (first reset binds at initial_cap) |
| `"periodic"` | `arm_initial_cap_at_first_reset.json` (second reset binds at periodic_cap) |
| `"lifetime"` | `arm_lifetime_cap_binds.json` |
| `"floor"` | `arm_floor_below_margin_blocked.json` |
| `"none"` | `arm_5_1_payment_jump_at_61.json` (modest reset within all caps) |

---

## hand_calc_check Witness Coverage (I-004 cap-bound oracle replacement)

Cap-bound fixtures have NO external oracle (Bankrate/Vertex42/AmericU don't capture cap-bound paths). Per BLOCKER I-004 fix, each cap-bound fixture embeds a `hand_calc_check` block in `expected.reset_events[0]` containing a Decimal-arithmetic hand-calc per the locked D-02 formula (Fannie Mae §B2-1.4-02). The fixture-based test asserts engine output's first ResetEvent matches the hand-calc EXACTLY.

| Cap-bound fixture | Hand-calc witness |
|---|---|
| `arm_lifetime_cap_binds.json` | `new_rate_expected="0.080000"`, `applied_cap_expected="lifetime"` |
| `arm_initial_cap_at_first_reset.json` | `new_rate_expected="0.100000"`, `applied_cap_expected="initial"` |
| `arm_floor_below_margin_blocked.json` | `new_rate_expected="0.040000"`, `applied_cap_expected="floor"` |

Non-cap-bound fixtures (5/1, 7/1, 10/1, 5/6 vanilla, off-by-one, teaser, continuous-numbering, index-path-overrides) do NOT have a `hand_calc_check` block — they cross-validate against external Bankrate/Vertex42/AmericU oracles.

---

## Wave 0 Requirements

- [ ] `tests/test_arm.py` — full file with ~32 xfail stubs covering ARM-01..09 + cross-cutting + applied_cap citation coverage + 6-key envelope contract
- [ ] `tests/conftest.py` extension — add `arm_fixture` loader (Phase 4 D-17 pattern; ~12 lines)
- [ ] `tests/fixtures/arm/.gitkeep` — directory created
- [ ] `tests/fixtures/arm/oracle/.gitkeep` — oracle directory created
- [ ] No framework install needed (pytest + mypy + ruff already configured Phase 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bankrate ARM calculator capture (PDF) | ARM-06 oracle | Browser-print of third-party tool; output not deterministically scrapeable | Open https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/, populate the canonical 5/1 scenario from `arm_5_1_payment_jump_at_61.json`, browser-print to `tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.pdf`, transcribe per-period rate/payment table to `bankrate_5_1_capture_2026.json`. Repeat for 7/1, 10/1. |
| Vertex42 Excel capture (PDF) | ARM-06 oracle | Excel template; manual cell entry | Download https://www.vertex42.com/ExcelTemplates/arm-calculator.html, populate same canonical 5/1 scenario, print-to-PDF to `vertex42_5_1_capture_2026.pdf`, transcribe to `.json`. |
| AmericU 5/6 SOFR disclosure | ARM-06 oracle (5/6) | Static lender PDF (already published) | `curl -o tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf`; transcribe disclosed worked example to `americu_5_6_disclosure.json`. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (per-task map populated in Per-Task Verification Map above; 29 tasks across 8 plans)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task row has an Automated Command)
- [x] Wave 0 covers all MISSING references (per-task map populated; all xfail stubs land in Wave 0 (T-00-03), flipped by Waves 2/3/4/5/6)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter (per-task map populated; threat refs cite per-plan threat_model IDs)

**Approval:** pending (awaiting execution Wave 0)
