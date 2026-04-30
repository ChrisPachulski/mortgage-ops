---
phase: 04-affordability
verified: 2026-04-30T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 4: Affordability — Verification Report

**Phase Goal:** Compose Phase 1 models + Phase 2 rules into household-aware DTI/LTV/CLTV/PITI calculations and reverse-affordability ("what loan amount can I qualify for?")
**Verified:** 2026-04-30T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md SC-1..5)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `scripts/affordability.py` accepts a household JSON with joint income + joint applicants + monthly debts and returns front-end DTI, back-end DTI, LTV, CLTV, and PITI as exact Decimal strings | VERIFIED | Direct CLI run with two-applicant household ($6k+$4k income, $50k junior lien) returned: `dti_front="0.312827"`, `dti_back="0.372827"`, `ltv="0.800000"`, `cltv="0.900000"`, `piti="3128.27"` — all as JSON strings. `tests/test_affordability.py::test_AFFD_01_dti_calculations`, `test_AFFD_02_ltv_calculation`, `test_AFFD_03_cltv_with_junior_liens`, `test_AFFD_04_piti_composition` PASS. |
| 2 | Reverse-affordability mode given (max_dti=0.43, income, debts) returns `max_loan_amount` computed via `npf.pv` from max-affordable PMT, and the result feeds back through forward affordability within `Decimal("0.01")` | VERIFIED | `lib/affordability.py::evaluate_reverse` calls `npf.pv(rate=monthly_rate, nper=term_months, pmt=-max_pi, fv=0)` (lines 1095-1100). Direct CLI test with max_dti=0.43 returned `max_loan_amount="465953.46"`, `implied_pi="3100.00"`. Round-trip back through forward at that loan_amount produced `dti_back="0.430000"` exactly (well within the 0.01 tolerance — round-trip is in fact tighter than required: `Decimal("0.0001")` per D-09). `test_AFFD_05_reverse_round_trip` PASSES with assertion `fwd_resp.loan_amount == rev_resp.max_loan_amount` (exact Decimal equality, D-18). |
| 3 | When a binding rule blocks qualification (e.g., VA residual income failure), the output JSON includes a `blocked_by` field naming the predicate citation (e.g., `"blocked_by": "VA-RESIDUAL-WEST-FAMILY-4"`) — never silent | VERIFIED | Direct CLI test with VA target + region=west, family_size=4, residual=$100 returned exact JSON `"blocked": true, "blocked_by": "VA-RESIDUAL-WEST-FAMILY-4"`. Citation read VERBATIM from `va_result.binding_rule_citation` per Phase 2 D-11 (`lib/affordability.py:1382`); never constructed in this module. `test_AFFD_07_blocked_by_va_residual_west_family_4` and `test_evaluate_va_residual_citation_read_verbatim_not_constructed` PASS. |
| 4 | `config/household.example.yml` is committed and documents the schema (joint income, applicants with credit scores, monthly debts, location); a fixture-based test loads it and runs through `scripts/affordability.py` end-to-end | VERIFIED | `config/household.example.yml` (101 lines) committed and documents: `location.{state_fips, county_fips, county_name, state, zip}`, `size`, `applicants[].{name, gross_monthly_income, credit_score}`, `monthly_debts.{auto, student_loans, credit_cards, other}`, `escrow.{property_tax_monthly, insurance_monthly, hoa_monthly}`, `va.{region, family_size, actual_residual_income}`, `current_housing_payment`. `tests/fixtures/affordability/household_example_yml_e2e.json` mirrors the schema; `test_AFFD_09_household_example_yml_e2e` invokes `scripts/affordability.py` via subprocess AND parses the actual `config/household.example.yml` to assert all schema keys exist. PASS. |
| 5 | Joint-applicant test cases pass for both two-income households and dual-credit-score handling (lower-mid score selected per Fannie/Freddie convention) | VERIFIED | `tests/fixtures/affordability/joint_applicants_two_incomes.json` (A=$6k/720 + B=$4k/680). `test_AFFD_06_joint_applicants` asserts `total_gross_monthly_income == Decimal("10000.00")` (sum) AND `"680-699" in fannie_warning` (min of {720, 680} = 680). PASS. Direct CLI confirmation: warning emitted as `"FANNIE-LLPA-680-699-75-80"`. Implementation: `lib/affordability.py:840` `_min_credit_score = min(a.credit_score for a in applicants)` and `lib/affordability.py:1436` `min_credit_score = min(...)` for both Fannie and Freddie lookups. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lib/affordability.py` | Pydantic v2 discriminated union request, evaluate_forward, evaluate_reverse, evaluate, blocker precedence, citation constants | VERIFIED | 1,513 lines. Contains `AffordabilityRequest` (Annotated discriminated union), `ForwardModeRequest`, `ReverseModeRequest`, `Household`, `Applicant`, `MonthlyDebts`, `EscrowInputs`, `VAInputs`, `LocationFIPS`, `AffordabilityResponse`, `evaluate_forward`, `evaluate_reverse`, `evaluate` (public dispatcher), `_evaluate_blockers`, `_append_soft_warnings`. Imports Phase 2 predicates by full path per D-08. |
| `scripts/affordability.py` | JSON-in/JSON-out CLI with --input, lazy import, 6-key envelope on validation errors | VERIFIED | 321 lines. argparse skeleton, `--input <path>` only (D-13), lazy-imports lib.affordability after parse (D-18 fast --help), JSON-float pre-validation, 6-key Pydantic envelope on stderr per Phase 3 D-19, MissingCountyDataError catch with 6-key envelope (BLOCKER fix). `--help` runs in <100ms (test_cli_help_fast PASS). |
| `config/household.example.yml` | Documents joint income, applicants, monthly debts, location schema | VERIFIED | 101 lines, clean YAML. Contains location (with state_fips + county_fips per D-15), size, applicants list (multiple), monthly_debts breakdown, escrow components, va block, current_housing_payment. Heavily commented with citations. |
| `tests/test_affordability.py` | Comprehensive test suite covering AFFD-01..09 | VERIFIED | 1,653 lines, 78 passed + 4 skipped (skips documented as constraint-driven). All 9 AFFD-* requirement tests present and passing. |
| `tests/fixtures/affordability/*.json` | Hand-calc golden fixtures with citation comments | VERIFIED | 10 fixtures: forward_conventional_80_ltv, forward_conventional_85_ltv_with_pmi, forward_fha_above_dti_cap, forward_jumbo_above_county_limit, forward_missing_county_data, forward_va_residual_fail, household_example_yml_e2e, joint_applicants_two_incomes, reverse_conventional_80_ltv_43_dti, single_applicant. Each has source/notes/rounding citations. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `scripts/affordability.py` | `lib.affordability.evaluate` | Lazy import + dispatch on validated AffordabilityRequest | WIRED | `from lib.affordability import AffordabilityRequest, evaluate` (line 203-206); `response = evaluate(request)` (line 297). |
| `lib/affordability.py::evaluate_forward` | `lib.amortize.build_schedule` | Built financed Loan → schedule.monthly_pi | WIRED | Line 184 imports `build_schedule`; line 890 invokes `schedule = build_schedule(financed_loan)`; `monthly_pi = schedule.monthly_pi`. |
| `lib/affordability.py::evaluate_reverse` | `numpy_financial.pv` | Direct call with negated PMT | WIRED | `import numpy_financial as npf` (line 181); `raw_pv = npf.pv(rate=monthly_rate, nper=request.term_months, pmt=-max_pi, fv=0)` (line 1095-1100). |
| `lib/affordability.py::_evaluate_blockers` | `lib.rules.va_residual_income.evaluate` | Citation read verbatim from result | WIRED | Line 204 imports as `va_residual_evaluate`; lines 1370-1382 invoke and read `va_result.binding_rule_citation` verbatim into `new_blocked_by`. |
| `lib/affordability.py::_evaluate_blockers` | `lib.rules.usda.evaluate` | Income eligibility check using request.household.size | WIRED | Line 203 imports as `usda_evaluate`; lines 1309-1319 invoke with `household_size=request.household.size` (BLOCKER 2 fix — uses full household size, not len(applicants)). |
| `lib/affordability.py::_evaluate_blockers` | `lib.rules.atr_qm.general_qm_passes` | When apr/apor present | WIRED | Line 194 imports; lines 1356-1363 invoke; sets `BLOCKED_BY_ATR_QM_PRICE_FIRST` on fail. |
| `lib/affordability.py::_evaluate_blockers` | `lib.rules.fannie_eligibility.compute_llpa` | Soft warning emission | WIRED | Line 196 imports as `fannie_compute_llpa`; lines 1444-1457 invoke and emit `FANNIE-LLPA-{FICO}-{LTV}` warning. |
| `lib/affordability.py::_evaluate_blockers` | `lib.rules.freddie_eligibility.evaluate` | Soft warning emission | WIRED | Line 198 imports as `freddie_evaluate`; lines 1466-1479 invoke and emit `FREDDIE-INELIGIBLE-{FICO}-{LTV}` warning. |
| `lib/affordability.py::_classify_target_loan_type` | `lib.rules.loan_type.classify` | Phase 2 RUL-01 with corrected signature | WIRED | Line 200 imports as `loan_type_classify`; lines 712-716 invoke with `program=` kwarg per RESEARCH §A.1. |
| `lib/affordability.py::_compute_monthly_mi` | `lib.rules.fha_mip.compute` | FHA monthly MIP | WIRED | Line 197 imports as `fha_mip_compute`; lines 766-772 invoke with corrected signature `(loan, original_property_value, endorsement_date)`. |
| `tests/test_affordability.py` | `scripts/affordability.py` | subprocess.run JSON round-trip | WIRED | `test_AFFD_08_cli_smoke` and `test_AFFD_09_household_example_yml_e2e` both invoke the CLI via `subprocess.run([sys.executable, str(SCRIPT_PATH), '--input', ...])` and parse stdout JSON. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `evaluate_forward` response | `monthly_pi` | `lib.amortize.build_schedule(financed_loan).monthly_pi` (Phase 3 numpy-financial PMT wrapper) | Yes (real Decimal from numpy-financial PMT) | FLOWING |
| `evaluate_reverse` response | `max_loan_amount` | `quantize_cents(npf.pv(...))` — direct numpy-financial call | Yes (real Decimal from npf.pv) | FLOWING |
| `evaluate_forward` response | `dti_front`, `dti_back` | `_compute_dti(piti, sum_monthly_debts, total_gross_monthly_income)` | Yes (computed from income/debt sums) | FLOWING |
| `evaluate` response | `blocked_by` | `_evaluate_blockers` precedence pipeline reading verbatim from predicate results (e.g., `va_result.binding_rule_citation`) | Yes (real predicate output, never silent) | FLOWING |
| `evaluate` response | `warnings` | StaleReferenceWarning capture + soft-warning citation strings (Fannie LLPA, Freddie ineligibility, HPA-PMI, ATR-QM advisory) | Yes (real predicate output + classification logic) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI --help fast | `python scripts/affordability.py --help` | Argparse output emitted, no heavy imports loaded | PASS |
| CLI forward mode JSON-in/JSON-out | `python scripts/affordability.py --input /tmp/sc1_test.json` | Returned JSON with all SC-1 fields as Decimal strings; rc=0 | PASS |
| CLI reverse mode round-trip | Reverse → forward chain via two CLI invocations | `dti_back="0.430000"` exactly equals `max_dti`; `loan_amount` matches reverse `max_loan_amount` exactly | PASS |
| CLI VA blocker emits citation | `python scripts/affordability.py --input /tmp/sc3_va_blocker.json` | `"blocked_by": "VA-RESIDUAL-WEST-FAMILY-4"` | PASS |
| CLI consumes household.example.yml schema | yaml.safe_load + JSON envelope + subprocess | rc=0, response with `monthly_pi`, `ltv`, `piti` populated | PASS |
| Module imports clean | `import lib.affordability` and access all public names | All exports present including BLOCKED_BY_*, WARNING_*, ceiling tables, crosswalks | PASS |
| Full test suite | `uv run pytest tests/` | 379 passed, 4 skipped (constraint-driven), 3 warnings | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AFFD-01 | 04-00, 04-01, 04-02, 04-06 | DTI (front-end and back-end) given household income + monthly debts | SATISFIED | `_compute_dti` (lib/affordability.py:651); `test_AFFD_01_dti_calculations` PASS |
| AFFD-02 | 04-00, 04-01, 04-02, 04-06 | LTV calculation given loan amount + property value | SATISFIED | `_compute_ltv` (line 670); `test_AFFD_02_ltv_calculation` PASS |
| AFFD-03 | 04-00, 04-01, 04-02, 04-06 | CLTV calculation given loan amount + junior liens + property value | SATISFIED | `_compute_cltv` (line 675); `test_AFFD_03_cltv_with_junior_liens` PASS; CLI run with `junior_liens=["50000.00"]` produced `cltv="0.900000"` |
| AFFD-04 | 04-00, 04-01, 04-02, 04-06 | PITI calculation (P&I + property tax + insurance + HOA + PMI/MIP) | SATISFIED | PITI composition in evaluate_forward (lines 911-920); test_AFFD_04_piti_composition PASS |
| AFFD-05 | 04-00, 04-03, 04-06 | Reverse direction via npf.pv from max-affordable PMT | SATISFIED | `evaluate_reverse` calls `npf.pv` (line 1095-1100); test_AFFD_05_reverse_round_trip PASS with exact Decimal equality |
| AFFD-06 | 04-00, 04-01, 04-02, 04-06 | Household-aware: joint income, joint applicants, dual-credit-score handling | SATISFIED | `total_gross_monthly_income = sum(...)` (line 828-831); `min(applicants[].credit_score)` (line 840 + line 1436); test_AFFD_06_joint_applicants PASS |
| AFFD-07 | 04-00, 04-01, 04-04, 04-06 | Affordability output cites the binding rule when blocking | SATISFIED | `blocked_by` field on AffordabilityResponse (line 571); D-11 precedence in `_evaluate_blockers`; VA citation read verbatim (line 1382); test_AFFD_07_blocked_by_va_residual_west_family_4 PASS with literal `"VA-RESIDUAL-WEST-FAMILY-4"` |
| AFFD-08 | 04-00, 04-05, 04-06 | scripts/affordability.py JSON-in / JSON-out CLI | SATISFIED | scripts/affordability.py (321 lines); test_AFFD_08_cli_smoke PASS via subprocess |
| AFFD-09 | 04-00, 04-05, 04-06 | config/household.example.yml documents schema | SATISFIED | config/household.example.yml (101 lines, all schema fields present); test_AFFD_09_household_example_yml_e2e PASS — parses YAML AND runs through CLI |

**No orphaned requirements.** All 9 AFFD-* IDs claimed in plan frontmatters AND mapped in REQUIREMENTS.md to Phase 4.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| lib/affordability.py | 866-904, 757-772 | Redundant FHA MIP computation (CR-02 / WR-01 in 04-REVIEW.md) | Info | Quality issue, not correctness today; produces correct results because both LTV codepoints map to same MIP table cell for tested fixtures. Documented in code review. Does NOT affect SC-1..5 robustness for the tested target loan types. |
| lib/affordability.py | 1066-1090 | FHA reverse-mode untested (CR-02 in 04-REVIEW.md) | Info | No fixture exercises FHA reverse mode; would be caught by round-trip closure if tested. SC-2 specifies max_dti=0.43 + reverse + DTI feedback within Decimal("0.01"); the conventional reverse path (which IS tested and verified above) satisfies SC-2 exactly. FHA reverse-mode robustness is a documented warning in 04-REVIEW.md, not a Phase 4 SC failure. |
| lib/affordability.py | 1102-1117 | Sign-convention deviation pinned only by round-trip closure (WR-02 in 04-REVIEW.md) | Info | Inline-documented; pinned by test_AFFD_05_reverse_round_trip exact-equality assertion. Empirically verified against numpy_financial 1.0.0. SC-2 round-trip closure currently holds. |
| lib/affordability.py | 1090-1100 | `max_pi` not validated > 0 in evaluate_reverse (WR-03) | Info | Pydantic Money `ge=0` constraint catches downstream. Not a SC-1..5 failure mode; would surface as a clear ValidationError envelope on the CLI rather than silent. |

**No blocker-class anti-patterns.** All findings from 04-REVIEW.md are advisory (Info/Quality). The 2 critical issues from the code review (CR-01 brittle isinstance ladder; CR-02 FHA reverse mode untested) do not affect any of the 5 ROADMAP success criteria as written:
- SC-1 (forward DTI/LTV/CLTV/PITI as Decimal strings) — NOT affected by CR-01/02; verified by direct CLI exercise.
- SC-2 (reverse mode at max_dti=0.43, conventional, round-trip within 0.01) — NOT affected; the conventional reverse path is verified end-to-end with exact Decimal equality (well within 0.01 tolerance).
- SC-3 (blocked_by VA citation verbatim) — NOT affected; verified by direct CLI exercise.
- SC-4 (config/household.example.yml schema + e2e test) — NOT affected; YAML parses cleanly and CLI subprocess test passes.
- SC-5 (joint-applicant + dual-credit) — NOT affected; verified by direct CLI exercise and dedicated test.

CR-01/02 should be tracked in the 04-REVIEW.md follow-up but do not block phase verification per the prompt instructions ("These are advisory and do NOT block phase verification").

### Human Verification Required

None. All 5 success criteria are programmatically verifiable via CLI subprocess + automated tests, all of which pass with deterministic JSON output and exact Decimal equality where required.

### Gaps Summary

No gaps found. Phase 4 goal is achieved:

1. **Forward-mode CLI** correctly composes Phase 1 models (Loan, Money, Rate from `lib/models.py`) + Phase 2 rules predicates (loan_type, conventional_pmi, fha_mip, va_residual_income, usda, atr_qm, fannie_eligibility, freddie_eligibility) + Phase 3 amortization (`build_schedule.monthly_pi`) into household-aware DTI/LTV/CLTV/PITI surface. Output shape is exact Decimal strings per CLAUDE.md money discipline.

2. **Reverse-mode CLI** wraps `numpy_financial.pv` directly (not reimplemented) per AMRT-01-style discipline; one-shot solve with assumed-MI estimation refinement. Round-trip closure to forward mode is exact (Decimal equality on `loan_amount`; DTI within `Decimal("0.0001")` — tighter than the SC-2 `Decimal("0.01")` requirement).

3. **Blocker precedence** is wired (D-11): loan-type-classify → USDA-income → LTV/CLTV ceiling → DTI cap → ATR/QM → VA-residual. The VA-residual citation is read VERBATIM from `va_result.binding_rule_citation` (not constructed in lib/affordability.py), ensuring the predicate-side stable format from `lib/rules/va_residual_income.py` flows through unchanged. Direct CLI test produced literal `"blocked_by": "VA-RESIDUAL-WEST-FAMILY-4"` exactly matching SC-3.

4. **Schema documentation** is complete in `config/household.example.yml` (101 lines, all required fields, citation-rich comments). Test `test_AFFD_09_household_example_yml_e2e` not only invokes the CLI on a synthetic mirroring fixture but also parses the actual YAML file and asserts the schema fields are present — making this a true end-to-end SC-4 verification.

5. **Joint-applicant handling** uses `sum()` for income aggregation (D-06) and `min()` for credit-score reduction (D-05) per Fannie/Freddie convention. Direct CLI test with two applicants ($6k/720, $4k/680) emitted `"FANNIE-LLPA-680-699-75-80"` warning, confirming the lower score (680) was selected and bucketed correctly.

**Code review findings note:** The accompanying 04-REVIEW.md flagged 2 critical issues (CR-01 brittle isinstance check in `_validate_common`; CR-02 FHA reverse mode untested) and 8 warnings. Per the verification prompt, these are advisory and do not block phase verification. None of them affect the 5 ROADMAP SC-1..5 success criteria as currently tested:
- CR-01 is a refactoring/robustness issue against future subclasses; today both branches of the isinstance ladder set `origination_ltv` and the validator works correctly for ForwardModeRequest and ReverseModeRequest as exercised.
- CR-02 (FHA reverse mode untested) is real but does not regress SC-2, which specifies the conventional reverse-affordability path with max_dti=0.43 — that path is verified end-to-end with exact Decimal equality.

Recommendation: track CR-01, CR-02, and WR-01..08 as follow-up tickets, but Phase 4 goal is achieved and the phase passes verification.

---

*Verified: 2026-04-30T00:00:00Z*
*Verifier: Claude (gsd-verifier)*
