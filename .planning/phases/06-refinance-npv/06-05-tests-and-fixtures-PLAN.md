---
phase: 06
plan: 05
type: execute
wave: 5
depends_on:
  - "06-00"
  - "06-01"
  - "06-02"
  - "06-03"
  - "06-04"
files_modified:
  - tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json
  - tests/fixtures/refinance/negative_npv_short_horizon.json
  - tests/fixtures/refinance/cash_out_proceeds_50k.json
  - tests/fixtures/refinance/breakeven_divergence.json
  - tests/fixtures/refinance/sign_validator_outflow_positive.json
  - tests/fixtures/refinance/after_tax_mode_smoke.json
  - tests/test_refinance.py
autonomous: true
requirements:
  - REFI-01
  - REFI-02
  - REFI-03
  - REFI-05
  - REFI-06
  - REFI-07
  - REFI-08
tags:
  - phase-06
  - refinance-npv
  - fixtures
  - oracle
must_haves:
  truths:
    - "6 fixtures shipped at tests/fixtures/refinance/ (one per scenario, per-fixture-per-file pattern from Phase 4)"
    - "Each fixture has request: + expected: + _meta: blocks"
    - "Expected-NPV values are EMPIRICALLY DERIVED via the engine (Plan 06-02 hand_calc_check witness pattern; Phase 5 D-04 [REVISED] inheritance)"
    - "All Decimal values are STRINGS in JSON; tests compare via Decimal == strict equality"
    - "13 remaining Wave-0 stubs (REFI-01/02/03/05/06/07/08 fixture-flip group + cross-cutting kind-coverage) flip from xfail to PASS"
    - "Citation-coverage meta-test asserts every RefiCashflow.kind Literal value appears in ≥1 fixture (D-03)"
  artifacts:
    - path: "tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json"
      provides: "SC-1 + REFI-05 anchor; Oracle 1 (NPV > 0)"
    - path: "tests/fixtures/refinance/negative_npv_short_horizon.json"
      provides: "SC-1 + REFI-06 anchor; Oracle 2 (NPV < 0; horizon=12mo per D-13)"
    - path: "tests/fixtures/refinance/cash_out_proceeds_50k.json"
      provides: "SC-3 + REFI-07 anchor; Oracle 3 (cash_proceeds=$47k, total_interest_delta surfaced)"
    - path: "tests/fixtures/refinance/breakeven_divergence.json"
      provides: "SC-2 anchor; simple_breakeven != npv_breakeven by ≥ 1 month"
    - path: "tests/fixtures/refinance/sign_validator_outflow_positive.json"
      provides: "SC-4 CLI-layer anchor; CLI rejects with 6-key envelope"
    - path: "tests/fixtures/refinance/after_tax_mode_smoke.json"
      provides: "D-09 smoke test; after_tax_npv populated; cites RUL-11"
---

<objective>
Ship 6 hand-calc fixtures + flip 13 remaining Wave-0 stubs to passing tests. Closes REFI-05/06/07 fixture-shipping requirements + ROADMAP SC-1 (positive + negative NPV) + SC-2 (breakeven divergence) + SC-3 (cash-out fields surfaced) + REFI-08 (CLI fixture round-trip beyond the smoke from Wave 4).

Empirical-derivation discipline (Phase 5 D-04 [REVISED] inheritance): ALL expected-NPV / breakeven values are derived by RUNNING the engine at fixture-creation time, then PINNED into the fixture JSON. The test then asserts `engine_output == fixture_expected` via Decimal `==`. This catches engine drift.
</objective>

<context>
@.planning/phases/06-refinance-npv/06-RESEARCH.md
@.planning/phases/06-refinance-npv/06-PATTERNS.md
@lib/refinance.py
@scripts/refi_npv.py
@tests/test_refinance.py
@tests/conftest.py
@tests/fixtures/affordability/forward_conventional_baseline.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create positive_npv_200bps_drop_2k_costs.json (SC-1 + Oracle 1)</name>
  <files>tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json</files>
  <action>
    Build the fixture. `request:` block matches RESEARCH §"Oracle 1" setup. `expected:` block populated by RUNNING `evaluate(req)` at fixture-creation time and capturing the exact Decimal-string values returned (Phase 5 D-04 [REVISED] hand_calc_check witness pattern).

    Schema:
    ```json
    {
      "_meta": {
        "oracle_source": "06-RESEARCH.md §'Pinned Oracles' Oracle 1",
        "derivation": "engine-derived 2026-05-02 via lib.refinance.evaluate; pinned for SC-1 sign-rigor",
        "citation": "ROADMAP Phase 6 SC-1 (positive-NPV with $2k closing costs)"
      },
      "request": {
        "refi_kind": "rate_and_term",
        "old_loan_balance": "300000.00",
        "old_annual_rate": "0.070000",
        "old_remaining_months": 300,
        "new_annual_rate": "0.050000",
        "new_term_months": 300,
        "closing_costs": "2000.00",
        "discount_rate_annual": "0.050000",
        "analysis_horizon_months": null
      },
      "expected": {
        "refi_kind": "rate_and_term",
        "npv": "<DERIVED>",
        "old_monthly_pi": "<DERIVED>",
        "new_monthly_pi": "<DERIVED>",
        "monthly_savings": "<DERIVED>",
        "breakeven": {
          "simple_months": "<DERIVED>",
          "simple_status": "ok",
          "npv_months": "<DERIVED>",
          "npv_status": "ok"
        }
      }
    }
    ```

    Run engine, capture values, replace `<DERIVED>` placeholders. Verify Plan 06-02 docstring-pinned NPV value matches what the fixture records here (cross-check).
  </action>
  <acceptance_criteria>
    - Fixture file exists; valid JSON; loads via refinance_fixture('positive_npv_200bps_drop_2k_costs')
    - expected.npv is positive (string parsed as Decimal > 0)
    - expected.simple_status == 'ok' AND expected.npv_status == 'ok'
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Create negative_npv_short_horizon.json (SC-1 + Oracle 2)</name>
  <files>tests/fixtures/refinance/negative_npv_short_horizon.json</files>
  <action>
    Same setup as Task 1 BUT `closing_costs: "5000.00"` and `analysis_horizon_months: 12`. Engine-derive expected values. NPV must be negative.
  </action>
  <acceptance_criteria>
    - Fixture loads; expected.npv parsed as Decimal < 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Create cash_out_proceeds_50k.json (SC-3 + Oracle 3)</name>
  <files>tests/fixtures/refinance/cash_out_proceeds_50k.json</files>
  <action>
    RESEARCH §"Oracle 3" setup. expected: block populates cash_proceeds, new_monthly_pi, monthly_payment_delta, total_interest_delta per SC-3 mandate. Engine-derive.
  </action>
  <acceptance_criteria>
    - Fixture loads; expected.cash_proceeds == "47000.00"; expected.refi_kind == "cash_out"
    - expected.total_interest_delta is positive (new costs more interest)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Create breakeven_divergence.json (SC-2 anchor)</name>
  <files>tests/fixtures/refinance/breakeven_divergence.json</files>
  <action>
    RESEARCH §"(d) Divergence" pinned setup: old=$300k@7%/30y, new=$300k@6%/30y, closing=$5000, discount=0.08. Engine-derive simple + NPV breakeven months. Assert in fixture _meta block that simple != npv (divergence anchor for SC-2).
  </action>
  <acceptance_criteria>
    - Fixture loads
    - expected.breakeven.simple_months and expected.breakeven.npv_months differ by ≥ 1 month
    - Both labeled in JSON (SC-2)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 5: Create sign_validator_outflow_positive.json (SC-4 CLI-layer anchor)</name>
  <files>tests/fixtures/refinance/sign_validator_outflow_positive.json</files>
  <action>
    Build a fixture whose `request:` JSON would be REJECTED by the CLI. Since Phase 6 D-15 hides RefiCashflow construction inside the engine (caller doesn't pass cashflows directly), trigger the validator another way: ship a fixture with closing_costs=0 and old_pi == new_pi (forcing zero savings). The Wave 0 sign-validator stubs from Plan 06-01 already cover construction-time rejection at the model layer; this fixture provides the CLI round-trip variant.

    Alternate (simpler): ship a fixture with `discount_rate_annual: "1.5"` (above Pydantic Rate's le=1) so TypeAdapter rejects it; assert stderr is the 6-key envelope.
  </action>
  <acceptance_criteria>
    - Fixture loads
    - Subprocess invocation against this fixture exits 2 with 6-key envelope on stderr
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 6: Create after_tax_mode_smoke.json (D-09)</name>
  <files>tests/fixtures/refinance/after_tax_mode_smoke.json</files>
  <action>
    Rate-and-term request with `after_tax_mode: true, marginal_tax_rate: "0.240000", filing_status: "mfj", has_grandfathered_debt: false`. Engine-derive after_tax_npv > pre-tax npv (tax shield should INCREASE present value).
  </action>
  <acceptance_criteria>
    - Fixture loads; expected.after_tax_npv > expected.npv (shield improves NPV)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 7: Flip remaining 13 Wave-0 stubs to passing fixture-driven tests</name>
  <files>tests/test_refinance.py</files>
  <action>
    Remove xfail decorators and ship real bodies for these 13 stubs:
    - test_refi_rate_and_term_positive_npv (uses positive_npv fixture; assert npv > 0 + Decimal exact match against expected.npv)
    - test_refi_rate_and_term_negative_npv (uses negative_npv_short_horizon fixture)
    - test_refi_npv_decimal_exact (assert engine output Decimal-equals expected for positive fixture, exercising Decimal == discipline)
    - test_refi_cash_out_proceeds (cash_out fixture; assert cash_proceeds matches)
    - test_refi_cash_out_new_monthly_pi (assert new_monthly_pi matches)
    - test_refi_cash_out_total_interest_delta (assert total_interest_delta matches AND is signed positive)
    - test_refi_breakeven_simple_labeled (assert response.breakeven.simple_months is in JSON output AND has simple_status field)
    - test_refi_breakeven_npv_labeled (assert response.breakeven.npv_months is in JSON output AND has npv_status field)
    - test_refi_breakeven_divergence_documented (uses breakeven_divergence fixture; assert simple != npv by ≥ 1 month)
    - test_refi_cashflow_kind_citation_coverage (D-03; iterate fixtures in tests/fixtures/refinance/, collect every RefiCashflow.kind Literal value across all expected.cashflows lists, assert each of {closing_costs, cash_proceeds, monthly_savings, monthly_payment_delta, tax_shield} appears in ≥1 fixture)
    - test_pyxirr_deferred_to_phase11_documented (assert lib/refinance.py docstring contains "Phase 11" AND "pyxirr" — D-07 deferral discipline)
    - test_refi_npv_doc_sections_present (Wave 6 ships references/refi-npv.md; this test is here as a stub flip pre-condition for Wave 6)
    - test_refi_npv_doc_sign_convention_phrase (same — stub left flippable to Wave 6)
  </action>
  <acceptance_criteria>
    - All listed stubs PASS or remain XFAIL with clear deferral-to-Wave-6 reason for the 2 doc-related ones
    - Phase 5 baseline preserved (≥ 432 passed)
    - mypy + ruff clean
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- Empirical-derivation discipline: expected values are engine-derived at fixture-creation time then PINNED. Do NOT hand-calculate analytically and risk drift.
- Phase 5 D-04 [REVISED] inheritance: hand_calc_check witness pattern preserved.
- All Decimal values are JSON STRINGS; tests compare via Decimal `==` (Phase 4 D-18 idiom).
</locked_decisions>

<verify_block>
- 6 fixtures committed at tests/fixtures/refinance/
- 11 Wave-0 stubs flipped (rate-and-term + cash-out + breakeven + cashflow-kind-coverage + pyxirr-doc); 2 doc stubs deferred to Wave 6 (test_refi_npv_doc_*)
- All earlier-flipped tests still PASS
- Phase 5 baseline + Phase 6 Wave 1-4 tests all green
- mypy + ruff clean
</verify_block>

<deviation_rules>
- Rule-1: if engine-derivation produces a value that contradicts RESEARCH §"Pinned Oracles" expected (e.g., NPV expected sign FLIPS), STOP — that is a math bug in Wave 2/3, not a fixture issue. Route through gsd-debug.
- Rule-2: do NOT relax Decimal exact equality in favor of `pytest.approx`. SC-1 sign-rigor requires strict equality (Phase 4 D-18 idiom).
- Rule-3: hygiene-only deviations noted in SUMMARY.md.
</deviation_rules>

<success_criteria>
- 6 fixtures shipped + 11 stubs flipped
- SC-1, SC-2, SC-3 all pinned by passing tests
- Phase 5 baseline + Wave 1-4 tests preserved
- mypy --strict + ruff clean
</success_criteria>
