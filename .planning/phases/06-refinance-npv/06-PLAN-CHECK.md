# Phase 6: Refinance NPV — Plan Check (Goal-Backward Verification)

**Checked:** 2026-05-02
**Phase:** 06-refinance-npv
**Plans audited:** 7 (06-00 through 06-06)
**Verdict:** **PASS-WITH-CONCERNS** (5 PASS, 4 CONCERN, 0 BLOCK across SC + REFI requirements; 0 BLOCK = phase is executable; CONCERNs are flagged for human review but do not gate execution)

## Method

Goal-backward audit: for each ROADMAP §"Phase 6" Success Criterion (SC-1..SC-5) and each REQUIREMENTS.md Phase 6 requirement (REFI-01..09), trace forward through the plans (06-00..06-06) and confirm at least one plan ships an artifact + test that closes the criterion. Verdict per criterion: **PASS** (clearly closed), **CONCERN** (closed but with caveat), **BLOCK** (not closed; execution would fail SC).

## Verdict Summary

| Criterion | Verdict | Closing plan(s) |
|---|---|---|
| SC-1 (positive + negative NPV; sign-convention verified) | **PASS** | 06-02 (engine), 06-05 (fixtures + test flips) |
| SC-2 (simple + NPV-based breakeven both labeled) | **PASS** | 06-02 (helpers), 06-05 (divergence fixture + test) |
| SC-3 (cash-out: cash_proceeds + new_pi + total_interest_delta) | **PASS** | 06-03 (engine), 06-05 (cash-out fixture) |
| SC-4 (RefiCashflow direction Literal + sign-validator) | **PASS** | 06-01 (model + validator), 06-01 (4 test flips) |
| SC-5 (references/refi-npv.md + cited from --help) | **PASS** | 06-04 (CLI epilog cites doc), 06-06 (doc body) |
| REFI-01 (rate-and-term NPV, borrower perspective) | **PASS** | 06-01 + 06-02 |
| REFI-02 (cash-out modeling) | **PASS** | 06-01 + 06-03 |
| REFI-03 (simple + NPV breakeven) | **PASS** | 06-02 |
| REFI-04 (pyxirr OPTIONAL) | **CONCERN** | 06-RESEARCH §D-07 + 06-05 deferral test |
| REFI-05 (positive-NPV fixture) | **PASS** | 06-05 |
| REFI-06 (negative-NPV fixture) | **CONCERN** | 06-05 (Oracle 2 uses horizon=12 trick) |
| REFI-07 (cash-out fixture) | **PASS** | 06-05 |
| REFI-08 (CLI scripts/refi_npv.py) | **PASS** | 06-04 |
| REFI-09 (references/refi-npv.md sign convention) | **PASS** | 06-06 |
| Cross-cutting: D-09 after-tax mode | **CONCERN** | 06-03 (opt-in; tests cover validator + smoke fixture) |
| Cross-cutting: D-08 PMI/MIP recalc | **CONCERN** | DEFERRED via D-10 override; documented in 06-06 |

**Aggregate:** 14 PASS, 4 CONCERN, 0 BLOCK across 18 line items.

## Per-Criterion Detail

### SC-1: positive-NPV fixture (rate drops 200bps, $2k closing) → NPV > 0; negative-NPV fixture (same rate, $5k closing) → NPV < 0 — sign convention verified

**Verdict: PASS**

- **Engine path** (06-02): `evaluate_rate_and_term` calls `_compute_npv` which wraps `npf.npv` with Decimal cashflows; Plan 06-02 Task 4 derives the exact Decimal NPV for Oracle 1 + Oracle 2 and pins them in the docstring.
- **Fixture path** (06-05 Task 1 + Task 2): `positive_npv_200bps_drop_2k_costs.json` (NPV > 0) and `negative_npv_short_horizon.json` (NPV < 0).
- **Test path** (06-05 Task 7): `test_refi_rate_and_term_positive_npv` + `test_refi_rate_and_term_negative_npv` flip from xfail to PASS, asserting Decimal exact match against engine-derived expected values.
- **Sign convention** (06-01 + 06-RESEARCH D-04): RefiCashflow validator REJECTS sign-mismatched constructions at Pydantic boundary; engine never bypasses.

**Caveat noted (NOT a blocker):** SC-1 ROADMAP language says "negative-NPV fixture (same rate, $5k closing costs)". Strict reading: SAME 200bps rate drop + $5k costs would still produce positive NPV over a 25-year horizon (savings ~$367/mo × 25y discounted ≈ $63k > $5k). Plan 06-RESEARCH §"Pinned Oracles" + D-13 honestly addresses this by using `analysis_horizon_months=12` to make the fixture honest to the borrower-decision use case. The fixture's _meta block documents this departure. This is a CONCERN for SC-1 verbatim adherence but is mitigated by:
1. The fixture STILL exercises the negative-NPV sign-rigor anchor SC-1 demands
2. The deviation is documented at 3 places (D-13, fixture _meta, 06-06 doc §5)
3. RESEARCH §"Pinned Oracles" Oracle 2 explicitly notes ROADMAP language is over-stated and proposes the horizon-truncation as "more honest to the borrower-decision use case (FHFA median tenure ~13 years)"

If the human prefers strict ROADMAP literalism, the fix is to replace `analysis_horizon_months=12` with a smaller rate-drop (e.g., 25bps); Plan 06-05 Task 2 documents both alternatives.

### SC-2: Breakeven months reported in two forms (simple + NPV-based); both labeled in output JSON

**Verdict: PASS**

- **Engine** (06-02 Task 2): `_compute_breakeven_simple` returns `(int|None, status)`; `_compute_breakeven_npv` runs cumulative-NPV scan per D-06 (NOT npf.irr).
- **Response shape** (06-01): `RefiBreakeven` Pydantic sub-model with explicit `simple_months`, `simple_status`, `npv_months`, `npv_status` fields — labeled in output JSON via `model_dump_json`.
- **Divergence fixture** (06-05 Task 4): `breakeven_divergence.json` with discount=0.08; documented divergence-by-≥1-month.
- **Test** (06-05 Task 7): `test_refi_breakeven_simple_labeled`, `test_refi_breakeven_npv_labeled`, `test_refi_breakeven_divergence_documented` all flip to PASS.

### SC-3: Cash-out fixture reports cash_proceeds + new_monthly_pi + total_interest_delta

**Verdict: PASS**

- **Engine** (06-03 Task 3): `evaluate_cash_out` populates all 3 fields on `RefiResponse`.
- **Fixture** (06-05 Task 3): `cash_out_proceeds_50k.json` per Oracle 3 setup.
- **Tests** (06-05 Task 7): `test_refi_cash_out_proceeds`, `test_refi_cash_out_new_monthly_pi`, `test_refi_cash_out_total_interest_delta` all flip to PASS.

### SC-4: RefiCashflow has direction: Literal["outflow","inflow"]; mismatched-sign construction raises ValidationError

**Verdict: PASS** (strongest closure of any SC — model layer + 4 dedicated tests)

- **Model** (06-01 Task 1): `RefiCashflow` defines `direction: Literal["outflow","inflow"]` + `@model_validator(mode="after") _direction_sign_consistency` per RESEARCH §"(e)" + D-03.
- **Tests** (06-01 Task 2): 4 stubs flip to PASS — outflow_positive_rejected, inflow_negative_rejected, zero_accepted_either_dir (D-14 explicit), correctly_signed_passes.

### SC-5: references/refi-npv.md documents "outflows negative, savings positive" + cited from --help

**Verdict: PASS**

- **Doc** (06-06 Task 1): `references/refi-npv.md` ships ≥ 250 lines with the literal phrase in §1.
- **CLI cite** (06-04 Task 1): `scripts/refi_npv.py --help` epilog contains literal "see references/refi-npv.md" string per SC-5 mandate.
- **Test** (06-04 Task 2 `test_cli_help_cites_references_refi_npv` + 06-06 Task 2 `test_refi_npv_doc_sign_convention_phrase`): both flip to PASS.
- **Belt-and-suspenders cites**: `lib/refinance.py` module docstring also cites references/refi-npv.md (06-01 D-16) + RefiCashflow validator error messages cite the doc (06-01 D-04).

### REFI-04: Optional pyxirr integration — **CONCERN**

**Verdict: CONCERN**

REFI-04 says **"Optional `pyxirr` integration for batch NPV across many refi offers"**. RESEARCH §"(a-bis)" + D-07 explicitly DEFER pyxirr to Phase 11 SUBA-02. Phase 6 ships `numpy_financial.npv` only.

**Why CONCERN, not BLOCK:**
- The requirement says "OPTIONAL" — Phase 6 deferral is consistent with that language.
- pyxirr is NOT in `pyproject.toml` (verified via Bash); adding it would inflate Phase 6's surface beyond the v1 brief.
- Plan 06-05 Task 7 ships `test_pyxirr_deferred_to_phase11_documented` which asserts `lib/refinance.py` docstring contains "Phase 11" + "pyxirr" — explicit deferral documentation, not silent omission.

**Open Q for human:** confirm REFI-04 is satisfied by documented deferral, OR decide to add pyxirr to pyproject.toml + ship a `lib.refinance.evaluate_batch` helper in Phase 6 (would need a new wave 06-07).

### REFI-06: negative-NPV fixture — **CONCERN** (same caveat as SC-1)

See SC-1 caveat above. Verdict identical.

### D-09 After-Tax Mode — **CONCERN**

**Verdict: CONCERN** (cross-cutting; not a SC line item but architecturally significant)

After-tax mode (06-03) IS shipped, with cross-field validator + tax_shield cashflow stream + after_tax_npv response field. However:
- ROADMAP § Phase 6 SCs do not mandate after-tax behavior — this is a Phase 6 ENRICHMENT proposed by RESEARCH §"(f)" + D-09.
- Test coverage is minimal: 1 fixture (`after_tax_mode_smoke.json`) + 1 cross-field validator test. SC-driven oracles do not exercise after-tax math depth.

**Why CONCERN, not BLOCK:** ROADMAP doesn't require after-tax; shipping it as opt-in is value-add not contract-creep. But the human should explicitly endorse the D-09 enrichment vs. deferring to Phase 8 stress testing (where it might compose better with rate-shock sweeps).

**Open Q for human:** keep D-09 in Phase 6 (current plan), or punt to a Phase 6.1 / Phase 8?

### D-08 PMI/MIP Recalc on Cash-Out LTV Change — **CONCERN**

**Verdict: CONCERN**

Cash-out scenarios where `new_principal / property_value > 0.80` SHOULD trigger PMI on conventional loans (or change FHA MIP tier). Phase 6 D-08 + D-10 carve this OUT of v1 with caller-supplied `new_loan_monthly_pi_override`. The carve-out is documented in `references/refi-npv.md` §7 (06-06).

**Why CONCERN, not BLOCK:** ROADMAP § Phase 6 SCs do not mandate PMI recalc; the carve-out is documented; and the override field gives callers a clean escape hatch. But a borrower running cash-out without supplying the override will get a misleadingly low new_monthly_pi (no PMI factored in) — the Pareto outcome is to surface a soft warning when LTV breaches 0.80 in cash-out scenarios.

**Open Q for human:** Phase 6 closes as-is, OR add a Wave 3 enhancement: when `cash_out_amount > 0` AND no override, warn "consider PMI/MIP on new principal — use Phase 4 evaluate_forward to compute or supply new_loan_monthly_pi_override".

## Per-Plan Audit

| Plan | Wave | Files | Locked decisions cited | Tests flipped | Notes |
|---|---|---|---|---|---|
| 06-00 | 0 | conftest.py, test_refinance.py, fixtures/refinance/.gitkeep | D-00 | N/A (xfail seeding) | 25 stubs, mirrors Phase 5 05-00 |
| 06-01 | 1 | lib/refinance.py, test_refinance.py | D-01..D-16 | 5 (4 sign-validator + 1 docstring cite) | Models only; engine stubbed |
| 06-02 | 2 | lib/refinance.py, test_refinance.py | D-04, D-06, D-11, D-15, AMRT-01 | 0 (engine validation via empirical Oracle reproduction) | Rate-and-term + 4 helpers |
| 06-03 | 3 | lib/refinance.py, test_refinance.py | D-09, D-12, D-15, RUL-11 | 1 (after_tax validator) | Cash-out + after-tax + dispatcher |
| 06-04 | 4 | scripts/refi_npv.py, test_refinance.py | D-13, D-17, D-18, D-19, WR-02, SC-5 | 6 (CLI smoke + envelope + --help cite) | Mirrors scripts/affordability.py |
| 06-05 | 5 | tests/fixtures/refinance/*.json (6 files), test_refinance.py | Phase 5 D-04 [REVISED] hand_calc_check | 11 (rate-and-term + cash-out + breakeven + cashflow-kind-coverage + pyxirr-deferred) | Empirical-derivation discipline |
| 06-06 | 6 | references/refi-npv.md, test_refinance.py | SC-5 verbatim, D-04..D-16 cross-ref | 2 (doc sections + sign-convention phrase) | Final 2 stubs; doc ≥ 250 lines |

**Total tests flipped across plans:** 5 + 0 + 1 + 6 + 11 + 2 = **25** = matches Plan 06-00 stub count exactly. **No xfail leakage; no orphan stubs.**

## Cross-Cutting Inheritance Audit

| Discipline | Source phase | Plan 06-NN inheriting | Verified |
|---|---|---|---|
| Decimal money discipline (FND-01) | Phase 1 | 06-01..06-03, 06-05 | YES (Decimal-from-strings; quantize_cents end-of-period only) |
| Pydantic strict+frozen+forbid (Phase 1 D-08) | Phase 1 | 06-01 | YES (every model has ConfigDict explicit) |
| numpy-financial wrap-not-reimplement (AMRT-01) | Phase 3 | 06-02 (npf.npv) | YES (NEVER calls npf.irr per D-06) |
| 6-key Pydantic envelope on stderr (Phase 3 WR-02) | Phase 3 | 06-04 | YES (reuses scripts/_cli_helpers.py per Phase 5 factor) |
| --help fast / lazy-import (D-18) | Phase 3 | 06-04 | YES (lazy import after argparse) |
| lib.money.quantize_rate (Phase 5 D-14) | Phase 5 | 06-01, 06-02 (discount_rate quantize) | YES |
| scripts/_cli_helpers.py reuse (Phase 5 factor) | Phase 5 | 06-04 | YES (no duplication of find_json_float_loc / make_decimal_type_envelope) |
| One-fixture-per-file convention | Phase 4 | 06-05 | YES |
| @pytest.mark.xfail(strict=True) discipline | Phase 5 | 06-00 | YES |
| Wave 0 Nyquist gate | Phase 4 / 5 | 06-00 | YES |

**No regressions to prior phase contracts.**

## Open Questions for Human Review

1. **REFI-04 pyxirr deferral**: confirm Phase 6 deferral to Phase 11 is acceptable, OR add pyxirr-batch helper inside Phase 6 (would require new Wave 06-07 + pyproject.toml dep edit).
2. **SC-1 / REFI-06 negative-NPV fixture realism**: confirm `analysis_horizon_months=12` (D-13) is acceptable substitute for "$5k closing same rate" producing positive NPV at full horizon; alternative is to use a smaller rate drop (25bps) instead. Plan 06-05 Task 2 documents both options.
3. **D-09 after-tax mode placement**: keep in Phase 6 (current plan) or punt to Phase 8 (stress + tax scenarios)?
4. **D-08 PMI/MIP cash-out warning**: add a soft warning when LTV breaches 0.80 without override, or accept silent caller responsibility?

## Phase 5 Baseline Preservation Check

| Plan | Baseline impact | Net new passing |
|---|---|---|
| 06-00 | +0 (only adds 25 xfail) | 0 (xfail not pass) |
| 06-01 | +5 (model layer flips) | 5 |
| 06-02 | +0 (no test flips; engine validation empirical) | 0 |
| 06-03 | +1 (after-tax validator) | 1 |
| 06-04 | +6 (CLI flips) | 6 |
| 06-05 | +11 (fixture-driven flips) | 11 |
| 06-06 | +2 (doc flips) | 2 |
| **Total Phase 6 net new passing** | | **25** |

After all 7 plans execute: **Phase 5 baseline (≥ 432 passed) + 25 Phase 6 new passing = ≥ 457 passed**, 0 failed, 0 errored, 0 xfailed (all 25 Phase 6 stubs flipped). Phase 5's 1 strict xfail (per ROADMAP) inherited unchanged.

## Final Verdict

**PASS-WITH-CONCERNS**: All 5 ROADMAP SCs and all 9 REFI requirements have a clear closing path through the 7 plans; 4 concerns are flagged for human visibility but none are execution-blockers. Phase 6 is **APPROVED for execution** subject to human sign-off on the 4 open questions (or explicit choice to defer them to Phase 6.1).

**Counts:**
- PASS: 14
- CONCERN: 4 (REFI-04 pyxirr deferral, REFI-06/SC-1 horizon trick, D-09 after-tax placement, D-08 PMI/MIP carve-out)
- BLOCK: 0
