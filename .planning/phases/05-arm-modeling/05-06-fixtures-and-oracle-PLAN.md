---
phase: 05
plan: 06
type: execute
wave: 6
depends_on:
  - "05-00"
  - "05-02"
  - "05-03"
  - "05-04a"
  - "05-04b"
  - "05-05"
files_modified:
  - tests/fixtures/arm/arm_5_1_payment_jump_at_61.json
  - tests/fixtures/arm/arm_5_1_off_by_one_negative.json
  - tests/fixtures/arm/arm_7_1_payment_jump_at_85.json
  - tests/fixtures/arm/arm_10_1_payment_jump_at_121.json
  - tests/fixtures/arm/arm_5_6_payment_jump_at_61_and_67.json
  - tests/fixtures/arm/arm_floor_below_margin_blocked.json
  - tests/fixtures/arm/arm_lifetime_cap_binds.json
  - tests/fixtures/arm/arm_initial_cap_at_first_reset.json
  - tests/fixtures/arm/arm_teaser_rate.json
  - tests/fixtures/arm/arm_continuous_period_numbering.json
  - tests/fixtures/arm/arm_index_path_overrides.json
  - tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf
  - tests/fixtures/arm/oracle/americu_5_6_disclosure.json
  - tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.pdf
  - tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.json
  - tests/fixtures/arm/oracle/vertex42_5_1_capture_2026.pdf
  - tests/fixtures/arm/oracle/vertex42_5_1_capture_2026.json
  - tests/fixtures/arm/oracle/bankrate_7_1_capture_2026.pdf
  - tests/fixtures/arm/oracle/bankrate_7_1_capture_2026.json
  - tests/fixtures/arm/oracle/bankrate_10_1_capture_2026.pdf
  - tests/fixtures/arm/oracle/bankrate_10_1_capture_2026.json
  - tests/test_arm.py
autonomous: false  # Has checkpoint:human-action for browser PDF captures
requirements:
  - ARM-02
  - ARM-03
  - ARM-04
  - ARM-05
  - ARM-06
  - ARM-07
user_setup:
  - service: bankrate.com
    why: "Capture-as-fixture oracle PDFs for 5/1, 7/1, 10/1 ARM cross-validation per D-04 [REVISED 2026-04-30]"
    dashboard_config:
      - task: "Browser-print 5/1 ARM scenario from https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/ with the canonical scenario inputs from the fixture"
        location: "Bankrate ARM Calculator web UI"
      - task: "Browser-print 7/1 + 10/1 ARM scenarios with same protocol"
        location: "Bankrate ARM Calculator web UI"
  - service: vertex42.com
    why: "Vertex42 Excel ARM template — secondary oracle (transparent formulas) per D-04 [REVISED]"
    dashboard_config:
      - task: "Download https://www.vertex42.com/ExcelTemplates/arm-calculator.html, populate the same canonical 5/1 scenario, browser-print to PDF"
        location: "Vertex42 Excel template (local download + Excel)"
  - service: americu.com
    why: "AmericU 5/6 SOFR ARM Disclosure — only credible 5/6 oracle (no consumer calc supports 5/6) per D-04 [REVISED]"
    dashboard_config:
      - task: "curl -o tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf"
        location: "Project workstation (Claude can run this CLI directly; no browser needed)"
tags:
  - phase-05
  - arm-modeling
  - fixtures
  - oracle-cross-validation
  - arm-02
  - arm-03
  - arm-04
  - arm-05
  - arm-06
  - arm-07
  - applied-cap-coverage
must_haves:
  truths:
    - "tests/fixtures/arm/ contains 11 hand-calc fixtures per D-09 [REVISED] with engine-emitted Decimal-string expected values + source-citation comments"
    - "tests/fixtures/arm/oracle/ contains 5 capture pairs (PDF + JSON transcription) per D-04 [REVISED 2026-04-30]: 3 Bankrate (5/1, 7/1, 10/1) + 1 Vertex42 (5/1) + 1 AmericU (5/6 SOFR disclosure)"
    - "Hand-calc fixture values are computed by lib.arm.build_arm_schedule (the engine) — NOT by hand-typing per-row payment values into JSON. The 'hand-calc per Selling Guide' verification is achieved by running the engine + cross-checking against the oracle captures (Bankrate/Vertex42/AmericU)"
    - "Oracle cross-validation tests verify engine output AGREES EXACTLY with the captured tool outputs on dollar-anchored fields per D-09 (exact Decimal equality, never assertAlmostEqual)"
    - "applied_cap citation-coverage meta-test (D-10): every Literal value in {initial, periodic, lifetime, floor, none} is exercised by at least one fixture's expected.reset_events[*].applied_cap"
    - "All 11 remaining ARM Wave 0 stubs flip from xfail to passing: test_arm_5_1_payment_jump_at_61, test_arm_7_1_payment_jump_at_85, test_arm_10_1_payment_jump_at_121, test_arm_5_6_payment_jump_at_61_and_67, test_arm_initial_cap_at_first_reset, test_arm_lifetime_cap_binds, test_arm_floor_below_margin_blocked, test_arm_5_1_off_by_one_negative, test_oracle_cross_validation_5_1, test_oracle_cross_validation_5_6, test_applied_cap_citation_coverage"
    - "Final phase pass count: 432 passed, 0 xfailed, 4 skipped, 0 failed, 0 errors"
    - "ARM-02..07 all closed with fixture-pinned dollar-anchored assertions"
  artifacts:
    - path: "tests/fixtures/arm/arm_5_1_payment_jump_at_61.json"
      provides: "Primary 5/1 ARM ROADMAP SC-2 fixture; verifies payment-jump at month 61, applied_cap=='none' for D-10"
      contains: "expected"
    - path: "tests/fixtures/arm/arm_5_1_off_by_one_negative.json"
      provides: "ROADMAP SC-3 negative direction; month 59 still old payment, month 61 already new"
      contains: "expected"
    - path: "tests/fixtures/arm/arm_floor_below_margin_blocked.json"
      provides: "ROADMAP SC-4 + ARM-04; index drops to 0%, new_rate >= max(margin, floor_rate); applied_cap=='floor'"
      contains: "applied_cap"
    - path: "tests/fixtures/arm/arm_initial_cap_at_first_reset.json"
      provides: "ARM-03; first reset binds at initial_cap (applied_cap=='initial'); subsequent reset binds at periodic_cap (applied_cap=='periodic')"
      contains: "applied_cap"
    - path: "tests/fixtures/arm/arm_lifetime_cap_binds.json"
      provides: "ARM-03; uncapped fully-indexed > note_rate + lifetime_cap; applied_cap=='lifetime'"
      contains: "applied_cap"
    - path: "tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.pdf"
      provides: "Browser-print PDF of Bankrate 5/1 ARM calculator output"
    - path: "tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf"
      provides: "Lender-published 5/6 SOFR ARM disclosure (frozen 2022 artifact)"
  key_links:
    - from: "tests/test_arm.py oracle tests"
      to: "tests/fixtures/arm/oracle/{bankrate,vertex42,americu}_*.json"
      via: "arm_fixture('oracle/...') loader"
      pattern: "arm_fixture\\(\"oracle/"
    - from: "tests/test_arm.py applied_cap_citation_coverage"
      to: "tests/fixtures/arm/*.json expected.reset_events[*].applied_cap"
      via: "directory walk + Literal-value set check"
      pattern: "fixtures/arm.*glob"
---

<objective>
Ship the 11 hand-calc fixtures + 5 oracle capture pairs that pin every ARM-02..07 requirement with dollar-anchored exact-Decimal-equality assertions. Flip the 11 remaining Wave-0 xfail stubs to passing tests. This is the FINAL Phase 5 plan — after this plan, ALL 9 ARM requirements are closed and the phase is ready for `/gsd-verify-work`.

Closes ARM-02 (4 product fixtures: 5/1, 7/1, 10/1, 5/6), ARM-03 (initial_cap + periodic_cap + lifetime_cap fixtures), ARM-04 (floor fixture), ARM-05 (continuous-numbering fixture), ARM-06 (oracle cross-validation: Bankrate + Vertex42 + AmericU captures per D-04 [REVISED]), ARM-07 (off-by-one negative fixture). Verifies D-10 applied_cap citation-coverage.

Purpose: Two reasons that REQUIRE this plan to ship as one unit (not split):
1. **Fixture data is the contract** — Wave 3 engine ships without ANY dollar-anchored assertion (the engine math is invariant-tested only). Fixtures translate "the engine produced X" into "the engine MUST produce X for this canonical scenario," locking the math against silent regressions.
2. **Oracle cross-validation is the credibility anchor** — RESEARCH §Q3 + Q4 + LM-1 made clear that the original D-04 source (MGIC) doesn't exist. The replacement triple (Bankrate + Vertex42 + AmericU) provides cross-tool agreement ("our engine matches three independent industry tools"); shipping fewer than all three weakens the credibility chain that ROADMAP SC + project goals depend on.

The fixtures use ENGINE-EMITTED expected values (the Phase 4 idiom from Plan 04-06 — engine output IS the spec; fixtures pin against drift). The PROOF that the engine is correct is the cross-check against Bankrate/Vertex42/AmericU oracle JSON. Disagreement = bug; agreement = math correctness with three independent witnesses.

Output: 11 hand-calc fixtures + 5 oracle pairs (10 files: 5 PDFs + 5 JSONs) + 11 Wave-0 stub flips + applied_cap coverage meta-test. Final phase state: 432 passed, 0 xfailed, ARM-01..09 all closed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-arm-modeling/05-CONTEXT.md
@.planning/phases/05-arm-modeling/05-RESEARCH.md
@.planning/phases/05-arm-modeling/05-PATTERNS.md
@.planning/phases/05-arm-modeling/05-VALIDATION.md
@CLAUDE.md
@tests/fixtures/affordability
@tests/fixtures/amortize
@tests/fixtures/golden_pmt.json
@lib/arm.py
@tests/test_arm.py

<interfaces>
Phase 4 fixture-loader pattern (already in conftest.py via Plan 05-00):

```python
@pytest.fixture
def arm_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "arm" / f"{stem}.json"
        return json.loads(path.read_text())
    return _load
```

Caller passes `arm_fixture("oracle/bankrate_5_1_capture_2026")` for an oracle file (per Plan 05-00 docstring).

Phase 4 hand-calc fixture shape (typical example from tests/fixtures/affordability/forward_conventional_80_ltv.json):

```json
{
  "id": "forward_conventional_80_ltv",
  "source": "computed in-tree per Phase 4 D-09 _quantize_rate; cross-verified against Phase 1 oracle anchor",
  "notes": "...",
  "request": { ... },
  "expected_response": { ... }
}
```

Phase 5 fixture shape (D-09 + Plan 04-06 idiom — engine-emitted expected values):

```json
{
  "id": "<stem>",
  "source": "engine-emitted (lib.arm.build_arm_schedule on 2026-04-30); cross-validated against <oracle source>",
  "notes": "...",
  "request": {
    "loan": { "principal": "...", "annual_rate": "...", "term_months": ..., "origination_date": "...", "loan_type": "arm" },
    "arm_terms": { ... },
    "assumed_index_rate": "...",
    "index_path": []
  },
  "expected": {
    "payments": [
      { "period": 1, "rate_in_effect": "0.065000", "payment": "2528.27", "principal": "...", "interest": "...", "extra_principal": "0.00", "balance": "...", "cumulative_interest": "...", "cumulative_principal": "..." }
    ],
    "reset_events": [
      { "period": 61, "old_rate": "0.065000", "new_rate": "0.077500", "old_pmt": "...", "new_pmt": "...", "index_value_used": "0.052500", "applied_cap": "none" }
    ],
    "total_interest": "...",
    "final_payment_adjusted": false
  }
}
```

D-09 [REVISED 2026-04-30] fixture list (CONTEXT.md lines 217-228):

| Fixture | Purpose |
|---|---|
| arm_5_1_payment_jump_at_61.json | Primary 5/1 ARM (ROADMAP SC-2); applied_cap='none' (D-10) |
| arm_5_1_off_by_one_negative.json | ROADMAP SC-3 negative direction (month 59 old, month 61 new) |
| arm_7_1_payment_jump_at_85.json | 7/1 ARM (initial=84, reset=12) |
| arm_10_1_payment_jump_at_121.json | 10/1 ARM (initial=120, reset=12) |
| arm_5_6_payment_jump_at_61_and_67.json | 5/6 SOFR (initial=60, reset=6); BOTH first and second reset |
| arm_floor_below_margin_blocked.json | ARM-04 + ROADMAP SC-4; applied_cap='floor' (D-10) |
| arm_lifetime_cap_binds.json | applied_cap='lifetime' (D-10) |
| arm_initial_cap_at_first_reset.json | ARM-03; applied_cap='initial' on first reset, 'periodic' on subsequent (D-10) |
| arm_teaser_rate.json | LM-3 + D-02 teaser-ARM (already engine-tested in Wave 3); fixture-pin the values |
| arm_continuous_period_numbering.json | ARM-05 + D-03; pins per-row continuous numbering, final_balance=0.00 |
| arm_index_path_overrides.json | D-01 override-wins; supplies index_path with 2 overrides + assumed_index_rate fallback |

D-04 [REVISED 2026-04-30] oracle list (CONTEXT.md lines 230-247):

| Oracle | Product | Files |
|---|---|---|
| Bankrate ARM Calculator | 5/1 | bankrate_5_1_capture_2026.{pdf,json} |
| Bankrate ARM Calculator | 7/1 | bankrate_7_1_capture_2026.{pdf,json} |
| Bankrate ARM Calculator | 10/1 | bankrate_10_1_capture_2026.{pdf,json} |
| Vertex42 Excel | 5/1 | vertex42_5_1_capture_2026.{pdf,json} |
| AmericU 5/6 SOFR Disclosure | 5/6 | americu_5_6_disclosure_2022.pdf + americu_5_6_disclosure.json |
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Generate the 11 hand-calc fixtures using engine-emitted values</name>
  <files>tests/fixtures/arm/arm_5_1_payment_jump_at_61.json, tests/fixtures/arm/arm_5_1_off_by_one_negative.json, tests/fixtures/arm/arm_7_1_payment_jump_at_85.json, tests/fixtures/arm/arm_10_1_payment_jump_at_121.json, tests/fixtures/arm/arm_5_6_payment_jump_at_61_and_67.json, tests/fixtures/arm/arm_floor_below_margin_blocked.json, tests/fixtures/arm/arm_lifetime_cap_binds.json, tests/fixtures/arm/arm_initial_cap_at_first_reset.json, tests/fixtures/arm/arm_teaser_rate.json, tests/fixtures/arm/arm_continuous_period_numbering.json, tests/fixtures/arm/arm_index_path_overrides.json</files>
  <read_first>
    - lib/arm.py (Wave 3 engine)
    - tests/fixtures/affordability/forward_conventional_80_ltv.json (shape model)
    - tests/fixtures/amortize/biweekly_true_200k_6_5.json (per-period structure model)
    - 05-CONTEXT.md D-09 [REVISED] (lines 217-228) — fixture list + each one's purpose
    - 05-RESEARCH.md §LM-5 (lines 668-670) — applied_cap=='none' fixture construction
    - 05-RESEARCH.md §LM-6 (lines 674-676) — Phase 1 oracle anchor for epoch 0
  </read_first>
  <action>
    Generate 11 fixture JSON files. Each fixture is constructed by:
    1. Defining the canonical request inputs (loan + arm_terms + assumed_index_rate + index_path).
    2. Running `build_arm_schedule(req)` to get the engine output.
    3. Serializing the engine output as JSON with Decimal strings.
    4. Augmenting with `id`, `source`, `notes` blocks per D-09.

    **PRE-GENERATION STEP per I-004 — Compute Decimal hand-calc witness for cap-bound fixtures.** For each cap-bound fixture (lifetime / initial / floor binding), compute the FIRST reset's `new_rate` per the locked D-02 formula in pure Decimal arithmetic with citation comments to Fannie Mae §B2-1.4-02. These witnesses are NOT engine output — they are hand-derived from the regulatory formula and used to cross-check engine output. They prevent the tautological "pin the engine against itself" failure mode that would otherwise apply to cap-bound scenarios (where Bankrate/Vertex42/AmericU don't capture cap-bound paths).

    **Cap-bound fixtures requiring hand_calc_check (3 fixtures):**

    1. **arm_lifetime_cap_binds.json** — first-reset hand-calc:
       ```
       index = Decimal("0.20")  # assumed_index_rate
       margin = Decimal("250") / Decimal("10000")  # = 0.025
       fully_indexed = quantize_rate(index + margin) = quantize_rate(Decimal("0.225")) = Decimal("0.225000")
       effective_floor = max(margin, Decimal("0.030000")) = Decimal("0.030000")  # floor_rate=0.03
       periodic_ceiling = Decimal("0.05") + (Decimal("2000") / Decimal("10000")) = Decimal("0.250000")  # initial_cap_bps=2000
       lifetime_ceiling = Decimal("0.05") + (Decimal("300") / Decimal("10000")) = Decimal("0.080000")  # note_rate=loan.annual_rate=0.05; lifetime_cap_bps=300
       ceiling = min(periodic_ceiling, lifetime_ceiling) = Decimal("0.080000")
       new_rate = quantize_rate(clamp(fully_indexed, low=floor, high=ceiling))
                = quantize_rate(min(max(Decimal("0.225"), Decimal("0.030000")), Decimal("0.080000")))
                = Decimal("0.080000")
       applied_cap_expected = "lifetime"  # ceiling came from lifetime branch
       ```

    2. **arm_initial_cap_at_first_reset.json** — first-reset hand-calc:
       ```
       index = Decimal("0.20")
       margin = Decimal("250") / Decimal("10000") = 0.025
       fully_indexed = quantize_rate(Decimal("0.225")) = Decimal("0.225000")
       effective_floor = max(margin, Decimal("0.030000")) = Decimal("0.030000")
       periodic_ceiling = Decimal("0.05") + (Decimal("500") / Decimal("10000")) = Decimal("0.100000")  # initial_cap_bps=500
       lifetime_ceiling = Decimal("0.05") + (Decimal("2000") / Decimal("10000")) = Decimal("0.250000")  # lifetime_cap_bps=2000 (large)
       ceiling = min(periodic_ceiling, lifetime_ceiling) = Decimal("0.100000")
       new_rate = quantize_rate(min(max(Decimal("0.225"), Decimal("0.030000")), Decimal("0.100000"))) = Decimal("0.100000")
       applied_cap_expected = "initial"  # ceiling came from initial-cap (first reset, applicable_cap=initial_cap)
       ```

    3. **arm_floor_below_margin_blocked.json** — first-reset hand-calc:
       ```
       index = Decimal("0.001")
       margin = Decimal("200") / Decimal("10000") = 0.020
       fully_indexed = quantize_rate(index + margin) = quantize_rate(Decimal("0.021")) = Decimal("0.021000")
       effective_floor = max(margin, Decimal("0.040000")) = Decimal("0.040000")  # floor_rate=0.04
       periodic_ceiling = Decimal("0.05") + (Decimal("500") / Decimal("10000")) = Decimal("0.100000")
       lifetime_ceiling = Decimal("0.05") + (Decimal("500") / Decimal("10000")) = Decimal("0.100000")
       ceiling = Decimal("0.100000")
       new_rate = quantize_rate(min(max(Decimal("0.021"), Decimal("0.040000")), Decimal("0.100000"))) = Decimal("0.040000")
       applied_cap_expected = "floor"  # floor binding (raised the rate)
       ```

    Embed each hand-calc witness as a sibling field `hand_calc_check` in the corresponding fixture's `expected.reset_events[0]`. Schema for the witness block (cited from Fannie B2-1.4-02 + D-02 lock):

    ```json
    "expected": {
      "reset_events": [
        {
          "period": 61,
          "old_rate": "0.050000",
          "new_rate": "0.080000",
          "old_pmt": "...",
          "new_pmt": "...",
          "index_value_used": "0.200000",
          "applied_cap": "lifetime",
          "hand_calc_check": {
            "_citation": "Fannie Mae Selling Guide §B2-1.4-02 + Phase 5 D-02 locked formula",
            "_method": "Pure Decimal arithmetic; not engine output",
            "fully_indexed": "0.225000",
            "effective_floor": "0.030000",
            "periodic_ceiling": "0.250000",
            "lifetime_ceiling": "0.080000",
            "applied_cap_expected": "lifetime",
            "new_rate_expected": "0.080000"
          }
        },
        ...
      ]
    }
    ```

    The non-cap-bound fixtures (5/1, 7/1, 10/1, 5/6 vanilla resets, off-by-one, teaser, continuous-numbering, index-path-overrides) do NOT get a `hand_calc_check` block — they are cross-validated against Bankrate/Vertex42/AmericU oracle captures, which IS the external witness. The cap-bound trio is the only set without an external oracle, so they need the hand-calc witness.

    **Generator script extension:** When the generator builds these 3 fixtures, AFTER calling `build_arm_schedule(req)` and serializing to JSON, MERGE the `hand_calc_check` dict into `expected.reset_events[0]` programmatically:

    ```python
    # Excerpt from scripts/_generate_arm_fixtures.py — applied for cap-bound fixtures only.
    fixture_dict = {
        "id": "arm_lifetime_cap_binds",
        "source": "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; cap-bound fixture has hand_calc_check witness per I-004 (no external oracle covers cap-bound scenarios)",
        ...
        "expected": json.loads(schedule.model_dump_json()),
    }
    fixture_dict["expected"]["reset_events"][0]["hand_calc_check"] = {
        "_citation": "Fannie Mae Selling Guide §B2-1.4-02 + Phase 5 D-02 locked formula",
        "_method": "Pure Decimal arithmetic; not engine output",
        "fully_indexed": "0.225000",
        "effective_floor": "0.030000",
        "periodic_ceiling": "0.250000",
        "lifetime_ceiling": "0.080000",
        "applied_cap_expected": "lifetime",
        "new_rate_expected": "0.080000",
    }
    ```

    **Generator approach — use a one-shot Python script per fixture.** For each fixture, write a small standalone Python script that constructs the ARMRequest, invokes the engine, and dumps to disk:

    ```
    # Example for arm_5_1_payment_jump_at_61.json
    from datetime import date
    from decimal import Decimal
    import json
    from pathlib import Path
    from lib.arm import ARMRequest, ARMTerms, IndexPathEntry, build_arm_schedule
    from lib.models import Loan

    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.050000"),
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="arm",
    )
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    req = ARMRequest(
        loan=loan,
        arm_terms=terms,
        assumed_index_rate=Decimal("0.052500"),  # produces fully_indexed=0.0775 → applied_cap='none' per LM-5
        index_path=[],
    )
    schedule = build_arm_schedule(req)

    # Serialize
    fixture = {
        "id": "arm_5_1_payment_jump_at_61",
        "source": "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ROADMAP SC-2 primary fixture; cross-validated against bankrate_5_1_capture_2026.{pdf,json}",
        "notes": "5/1 ARM 30yr; 5% initial / 2.5pp margin / 0.0525 assumed index → fully_indexed=0.0775. Modest reset within all caps; applied_cap='none' per D-10 LM-5.",
        "request": json.loads(req.model_dump_json()),
        "expected": json.loads(schedule.model_dump_json()),
    }
    Path("tests/fixtures/arm/arm_5_1_payment_jump_at_61.json").write_text(
        json.dumps(fixture, indent=2)
    )
    ```

    **Specific request inputs for each of the 11 fixtures.** Use these exact values (LM-5 numbers chosen so applied_cap classification spans all 5 Literal values across the fixture set):

    **1. arm_5_1_payment_jump_at_61.json** (primary; SC-2; applied_cap='none')
    - loan: principal=$400000, annual_rate=0.05, term=360, origination_date=2026-01-01, loan_type='arm'
    - terms: initial_period_months=60, reset_period_months=12, initial_cap_bps=500, periodic_cap_bps=200, lifetime_cap_bps=500, floor_rate=0.03, margin_bps=250, index_series_id="MORTGAGE30US"
    - assumed_index_rate=0.0525 (fully_indexed=0.0775; floor=0.03; periodic_ceiling=0.10; lifetime_ceiling=0.10 — all open intervals; applied_cap='none')

    **2. arm_5_1_off_by_one_negative.json** (SC-3 negative direction)
    - Same inputs as #1 — purpose is to assert payments[58].payment == initial_pmt AND payments[60].payment != initial_pmt. The fixture content is the same; the test on this fixture asserts the off-by-one boundary.
    - id: "arm_5_1_off_by_one_negative" (different file; same engine output content)
    - notes: "ROADMAP SC-3 negative direction. Re-uses arm_5_1_payment_jump_at_61 numbers. Test asserts month 59 still uses initial rate AND month 61 already uses new rate (covers BOTH sides of the off-by-one)."

    **3. arm_7_1_payment_jump_at_85.json**
    - loan: principal=$400000, annual_rate=0.05, term=360, origination_date=2026-01-01, loan_type='arm'
    - terms: initial_period_months=84, reset_period_months=12, otherwise identical to #1
    - assumed_index_rate=0.055 (modest reset; applied_cap='none')

    **4. arm_10_1_payment_jump_at_121.json**
    - loan: principal=$400000, annual_rate=0.05, term=360
    - terms: initial_period_months=120, reset_period_months=12, otherwise identical to #1
    - assumed_index_rate=0.055

    **5. arm_5_6_payment_jump_at_61_and_67.json**
    - loan: principal=$400000, annual_rate=0.05, term=360, loan_type='arm'
    - terms: initial_period_months=60, reset_period_months=6, initial_cap_bps=200 (5/6 caps are 2/1/5 per AmericU), periodic_cap_bps=100, lifetime_cap_bps=500, floor_rate=0.03, margin_bps=250
    - assumed_index_rate=0.052 (modest first reset → fully_indexed=0.077, periodic_ceiling = 0.05 + 200bps = 0.07 → applied_cap='initial' for first reset since fully_indexed > ceiling; second reset 0.07 + 100bps = 0.08, fully_indexed still 0.077 → applied_cap='none')
    - notes: "5/6 SOFR ARM with 2/1/5 caps per AmericU disclosure. First reset binds at initial_cap (0.07); second reset within new periodic ceiling (0.08); spans applied_cap='initial' AND 'none' for D-10 coverage."

    **6. arm_floor_below_margin_blocked.json** (SC-4; applied_cap='floor')
    - loan: principal=$400000, annual_rate=0.05, term=360
    - terms: initial_period_months=60, reset_period_months=12, initial_cap_bps=500, periodic_cap_bps=200, lifetime_cap_bps=500, floor_rate=0.04, margin_bps=200
    - assumed_index_rate=0.001 (huge drop) → fully_indexed = 0.001 + 0.02 = 0.021; effective_floor = max(0.02, 0.04) = 0.04; new_rate = 0.04; applied_cap='floor'
    - notes: "ARM-04 + ROADMAP SC-4. Index drops to 0.1%; without floor, fully_indexed=0.021 would breach floor. Floor enforces new_rate=floor_rate=0.04. applied_cap='floor' for D-10 coverage."

    **7. arm_lifetime_cap_binds.json** (applied_cap='lifetime')
    - loan: principal=$400000, annual_rate=0.05, term=360
    - terms: initial_period_months=60, reset_period_months=12, initial_cap_bps=2000, periodic_cap_bps=2000, lifetime_cap_bps=300 (3pp lifetime — small), floor_rate=0.03, margin_bps=250
    - assumed_index_rate=0.20 (huge index) → fully_indexed=0.225; periodic_ceiling=0.05+0.20=0.25 (huge initial cap doesn't bind); lifetime_ceiling=0.05+0.03=0.08; ceiling=min(0.25, 0.08)=0.08; new_rate=0.08; applied_cap='lifetime'

    **8. arm_initial_cap_at_first_reset.json** (applied_cap='initial' first; 'periodic' second)
    - loan: principal=$400000, annual_rate=0.05, term=360
    - terms: initial_period_months=60, reset_period_months=12, initial_cap_bps=500 (5pp first), periodic_cap_bps=200 (2pp subsequent), lifetime_cap_bps=2000 (large; doesn't bind), floor_rate=0.03, margin_bps=250
    - assumed_index_rate=0.20 → fully_indexed=0.225; periodic_ceiling at first reset = 0.05+0.05=0.10 (initial_cap binds); new_rate=0.10; applied_cap='initial'
    - At second reset (period 73): prior=0.10, fully_indexed=0.225, periodic_ceiling=0.10+0.02=0.12; new_rate=0.12; applied_cap='periodic'
    - notes: "Fixture spans both applied_cap='initial' (first reset) AND 'periodic' (second reset) for D-10 coverage. Lifetime cap large; doesn't bind."

    **9. arm_teaser_rate.json** (LM-3)
    - loan: principal=$400000, annual_rate=0.03 (teaser), term=360
    - terms: initial_period_months=60, reset_period_months=12, initial_cap_bps=2000, periodic_cap_bps=2000, lifetime_cap_bps=500, floor_rate=0.02, margin_bps=250, note_rate=0.05 (post-teaser)
    - assumed_index_rate=0.15 → fully_indexed=0.175; lifetime_ceiling=note_rate(0.05)+0.05=0.10; ceiling=0.10; new_rate=0.10; applied_cap='lifetime'
    - notes: "Teaser ARM. loan.annual_rate=0.03, note_rate=0.05. Lifetime ceiling computed against note_rate=0.05 (engine choice per D-02 LM-3), NOT against loan.annual_rate=0.03. CFPB §1951 alternative convention would yield 0.08; engine deliberately yields 0.10 per industry/Fannie convention."

    **10. arm_continuous_period_numbering.json** (ARM-05 + D-03)
    - Same inputs as #1 (modest reset)
    - id: "arm_continuous_period_numbering"
    - notes: "Pins continuous period numbering 1..360, final_balance=0.00, total_interest = payments[-1].cumulative_interest (Phase 1 D-15 invariant)."

    **11. arm_index_path_overrides.json** (D-01)
    - loan: principal=$400000, annual_rate=0.05, term=360
    - terms: same as #1
    - assumed_index_rate=0.05 (fallback)
    - index_path: [{"period": 61, "value": "0.060000"}, {"period": 73, "value": "0.045000"}]
    - notes: "D-01 override-wins. First reset uses 0.06 (override); second uses 0.045 (override); subsequent resets fall back to assumed_index_rate=0.05."

    **Implementation procedure:**

    1. Write a single Python generator script `scripts/_generate_arm_fixtures.py` (this is a developer-only one-shot tool — gitignore it OR keep as a regen helper; recommend keeping committed for future re-validation):

    ```
    #!/usr/bin/env python3
    """One-shot generator for tests/fixtures/arm/*.json (Phase 5 Plan 05-06).

    Run with: python scripts/_generate_arm_fixtures.py

    Per CONTEXT.md D-09 [REVISED 2026-04-30] + Plan 04-06 idiom: expected values
    are engine-emitted by lib.arm.build_arm_schedule. Cross-validation against
    Bankrate/Vertex42/AmericU oracle captures (separate task) provides the
    industry-tool-agreement credibility anchor.

    Re-run this script if the engine math changes (it shouldn't — but it's the
    single source of truth for fixture regeneration).
    """
    # ... full content with one function per fixture, all 11 produced ...
    ```

    2. Run: `python scripts/_generate_arm_fixtures.py`. Should produce 11 JSON files in tests/fixtures/arm/.

    3. Verify each fixture file is well-formed JSON and contains the expected stubs:
    ```
    for f in tests/fixtures/arm/*.json; do
        python -c "import json; d=json.load(open('$f')); assert 'id' in d; assert 'request' in d; assert 'expected' in d"
    done
    ```

    4. Commit the generator script + the 11 fixture files together.

    Each fixture's JSON content is large (a 360-row payments list per scenario); these are committed as-is because they ARE the contract. Phase 4 fixtures are similar size.
  </action>
  <verify>
    <automated>bash -c 'cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; python scripts/_generate_arm_fixtures.py &amp;&amp; ls tests/fixtures/arm/*.json | wc -l | xargs -I {} test {} -ge 11 &amp;&amp; for f in tests/fixtures/arm/*.json; do python -c "import json; json.load(open(\"$f\"))" || exit 1; done &amp;&amp; echo OK'</automated>
  </verify>
  <acceptance_criteria>
    - File scripts/_generate_arm_fixtures.py exists and executes cleanly
    - All 11 fixture files exist:
      - tests/fixtures/arm/arm_5_1_payment_jump_at_61.json
      - tests/fixtures/arm/arm_5_1_off_by_one_negative.json
      - tests/fixtures/arm/arm_7_1_payment_jump_at_85.json
      - tests/fixtures/arm/arm_10_1_payment_jump_at_121.json
      - tests/fixtures/arm/arm_5_6_payment_jump_at_61_and_67.json
      - tests/fixtures/arm/arm_floor_below_margin_blocked.json
      - tests/fixtures/arm/arm_lifetime_cap_binds.json
      - tests/fixtures/arm/arm_initial_cap_at_first_reset.json
      - tests/fixtures/arm/arm_teaser_rate.json
      - tests/fixtures/arm/arm_continuous_period_numbering.json
      - tests/fixtures/arm/arm_index_path_overrides.json
    - Every fixture parses as valid JSON
    - Every fixture has top-level keys: id, source, notes, request, expected
    - Every fixture's expected.payments has length = request.loan.term_months (e.g., 360 for 30yr)
    - Every fixture's expected.reset_events has at least 1 entry (the engine emits a ResetEvent per reset boundary)
    - The applied_cap classifications across the fixture set cover all 5 Literal values:
      - "none" appears in arm_5_1_payment_jump_at_61.json (and others)
      - "floor" appears in arm_floor_below_margin_blocked.json
      - "lifetime" appears in arm_lifetime_cap_binds.json AND arm_teaser_rate.json
      - "initial" appears in arm_initial_cap_at_first_reset.json AND arm_5_6_payment_jump_at_61_and_67.json
      - "periodic" appears in arm_initial_cap_at_first_reset.json (second reset)
    - Verify by: `python -c "import json, glob; vals=set(); [vals.add(re['applied_cap']) for f in glob.glob('tests/fixtures/arm/*.json') for re in json.load(open(f))['expected']['reset_events']]; assert {'initial','periodic','lifetime','floor','none'} <= vals, vals; print('OK')"`
    - **I-004 hand_calc_check** — the 3 cap-bound fixtures (`arm_lifetime_cap_binds.json`, `arm_initial_cap_at_first_reset.json`, `arm_floor_below_margin_blocked.json`) each have `expected.reset_events[0].hand_calc_check` dict with keys: `_citation`, `_method`, `fully_indexed`, `effective_floor`, `periodic_ceiling`, `lifetime_ceiling`, `applied_cap_expected`, `new_rate_expected`
    - Verify by: `python -c "import json; [print(f, sorted(json.load(open(f))['expected']['reset_events'][0]['hand_calc_check'].keys())) for f in ['tests/fixtures/arm/arm_lifetime_cap_binds.json','tests/fixtures/arm/arm_initial_cap_at_first_reset.json','tests/fixtures/arm/arm_floor_below_margin_blocked.json']]"` shows all 8 expected keys per fixture
    - The 8 non-cap-bound fixtures do NOT have `hand_calc_check` (they have external Bankrate/Vertex42/AmericU oracle witnesses instead): `python -c "import json, glob; assert not any('hand_calc_check' in re for f in glob.glob('tests/fixtures/arm/arm_5_1_payment_jump_at_61.json') for re in json.load(open(f))['expected']['reset_events']); print('OK')"`
  </acceptance_criteria>
  <done>
    11 hand-calc fixtures shipped; applied_cap classification spans all 5 Literal values; every fixture parses; values are engine-emitted.
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 2: Capture 5 oracle PDFs (Bankrate 5/1 + 7/1 + 10/1, Vertex42 5/1, AmericU 5/6)</name>
  <what-built>Tasks 1 generated 11 hand-calc fixtures; Task 3 will produce 5 oracle JSON transcriptions. This checkpoint is the human-only PDF-capture step that cannot be fully automated (browser-print of third-party UIs).</what-built>
  <how-to-verify>
    Per CONTEXT.md D-04 [REVISED 2026-04-30] + RESEARCH §"Manual-Only Verifications" table, perform these 5 captures and commit the resulting PDFs to tests/fixtures/arm/oracle/:

    1. **Bankrate 5/1 ARM** — Open https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/ in a browser. Populate the canonical 5/1 scenario from `tests/fixtures/arm/arm_5_1_payment_jump_at_61.json`:
       - Loan amount: $400,000
       - Term: 30 years
       - ARM type: 5/1 ARM
       - Initial interest rate: 5.0%
       - Index after the initial period: 5.25% (= assumed_index_rate)
       - Margin: 2.5%
       - Caps: 5/2/5 (initial 5pp / periodic 2pp / lifetime 5pp)
       - Rate floor: 3%
       Browser-print to PDF. Save as `tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.pdf`.

    2. **Bankrate 7/1 ARM** — Same Bankrate UI, switch to 7/1 ARM, use scenario from arm_7_1_payment_jump_at_85.json. Save as `bankrate_7_1_capture_2026.pdf`.

    3. **Bankrate 10/1 ARM** — Same Bankrate UI, switch to 10/1 ARM. Save as `bankrate_10_1_capture_2026.pdf`.

    4. **Vertex42 5/1 ARM** — Download https://www.vertex42.com/ExcelTemplates/arm-calculator.html (Excel template). Open in Excel/LibreOffice/Numbers. Populate the same 5/1 scenario as Bankrate. Print the populated worksheet to PDF. Save as `vertex42_5_1_capture_2026.pdf`.

    5. **AmericU 5/6 SOFR Disclosure** — This is a static lender PDF (already published; no capture needed):
       ```
       curl -o tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf \
            https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf
       ```
       (Claude can run this curl directly — no browser needed for this file.)

    After all 5 PDFs are committed, verify with:
    ```
    ls -la tests/fixtures/arm/oracle/
    ```
    Should list 5 .pdf files. Each PDF should be > 10KB (sanity check; small PDFs likely failed capture).
  </how-to-verify>
  <resume-signal>Type "approved" when all 5 PDFs are committed to tests/fixtures/arm/oracle/, OR describe any blockers (e.g., "Bankrate UI changed schema; can't populate the scenario").</resume-signal>
</task>

<task type="auto">
  <name>Task 3: Transcribe 5 oracle PDFs into JSON files (one .json per .pdf)</name>
  <files>tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.json, tests/fixtures/arm/oracle/bankrate_7_1_capture_2026.json, tests/fixtures/arm/oracle/bankrate_10_1_capture_2026.json, tests/fixtures/arm/oracle/vertex42_5_1_capture_2026.json, tests/fixtures/arm/oracle/americu_5_6_disclosure.json</files>
  <read_first>
    - The 5 PDFs committed in Task 2 (manual capture)
    - 05-CONTEXT.md D-04 [REVISED] (lines 230-251) — capture pair convention
    - 05-PATTERNS.md "tests/fixtures/arm/oracle/*.pdf + .json" section (lines 680-695) — JSON transcription schema
  </read_first>
  <action>
    Transcribe the per-period rate/payment table from each oracle PDF into a JSON file (the .json sibling of each .pdf). Schema (planner-finalized per RESEARCH §Q3):

    ```json
    {
      "id": "<oracle>_<product>_capture_<year>",
      "source": "<URL of source tool> (captured YYYY-MM-DD)",
      "notes": "...",
      "scenario_inputs": {
        "loan_amount": "400000.00",
        "term_months": 360,
        "arm_type": "5/1",
        "initial_rate": "0.050000",
        "index_after_initial": "0.052500",
        "margin": "0.025000",
        "caps": "5/2/5",
        "floor": "0.030000"
      },
      "expected_per_period": [
        { "period": 1, "rate": "0.050000", "payment": "2147.29" },
        { "period": 60, "rate": "0.050000", "payment": "2147.29" },
        { "period": 61, "rate": "0.077500", "payment": "<from PDF>" },
        { "period": 73, "rate": "<from PDF>", "payment": "<from PDF>" }
      ]
    }
    ```

    For each oracle file:
    - Extract every per-period row Bankrate/Vertex42 actually prints (typically 360 rows for 30yr; AmericU disclosure prints only the worked-example rows at months 61, 67, 73).
    - Use exact Decimal-string formatting (CLAUDE.md money discipline; never use JSON floats).
    - Commit the .json alongside the .pdf.

    **Important:** If a Bankrate or Vertex42 capture truncates the table (e.g., shows only every 12th row), transcribe ONLY the rows actually shown. The cross-validation test (Task 4) iterates over the rows present in the JSON; missing rows just aren't asserted.

    **AmericU 5/6 transcription** is the simplest — the disclosure publishes a worked example in the PDF text:
    - Initial rate: 5.000% (months 1-60)
    - First Change Date: month 61. Quote: "the rate at the first Change Date can change by no more than 2 percentage points up or down" (initial_cap=200bps).
    - Subsequent: every 6 months thereafter. periodic_cap=100bps.
    - Lifetime cap: 5pp above initial rate.
    - The disclosure typically shows worst-case payment example at month 61 + 67. Transcribe those 2 rows minimum.

    Note: this task assumes Task 2 has been completed (PDFs are committed). If any PDF is missing, the corresponding JSON cannot be created — block on Task 2 first.
  </action>
  <verify>
    <automated>bash -c 'cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for f in tests/fixtures/arm/oracle/*.json; do python -c "import json; d=json.load(open(\"$f\")); assert \"id\" in d; assert \"source\" in d; assert \"expected_per_period\" in d; assert len(d[\"expected_per_period\"]) >= 2" || exit 1; done &amp;&amp; ls tests/fixtures/arm/oracle/*.json | wc -l | xargs test 5 -le'</automated>
  </verify>
  <acceptance_criteria>
    - 5 .json files exist alongside the 5 .pdf files in tests/fixtures/arm/oracle/
    - Each .json parses as valid JSON
    - Each has keys: id, source, notes, scenario_inputs, expected_per_period
    - americu_5_6_disclosure.json has at least 2 rows in expected_per_period (the worked-example month 61 + month 67)
    - bankrate_5_1_capture_2026.json + bankrate_7_1_capture_2026.json + bankrate_10_1_capture_2026.json + vertex42_5_1_capture_2026.json each have at least 5 rows in expected_per_period (sampled rows from the per-period table)
    - All money/rate fields in expected_per_period are JSON strings (no JSON floats)
  </acceptance_criteria>
  <done>
    5 oracle JSON transcriptions committed; all parse; expected_per_period has minimum row coverage.
  </done>
</task>

<task type="auto">
  <name>Task 4: Flip the remaining 11 Wave-0 stubs in tests/test_arm.py to fixture-based passing tests</name>
  <files>tests/test_arm.py</files>
  <read_first>
    - tests/test_arm.py (Wave 5 state: 11 xfails)
    - The 11 hand-calc fixtures + 5 oracle pairs from Tasks 1-3
    - 05-VALIDATION.md "Phase Requirements → Test Map" rows for ARM-02..07
    - 05-PATTERNS.md "Pattern 5: Citation-coverage meta-test" + "Pattern 6: Phase 1 oracle anchor reuse"
  </read_first>
  <action>
    Flip exactly 11 Wave-0 stubs to passing tests. Each stub uses the `arm_fixture(...)` loader to load a hand-calc fixture and asserts the engine output matches the fixture's `expected` block via exact Decimal equality.

    Stubs to flip:
    1. test_arm_5_1_payment_jump_at_61 (uses arm_5_1_payment_jump_at_61)
    2. test_arm_7_1_payment_jump_at_85 (uses arm_7_1_payment_jump_at_85)

    **PRE-FLIP STEP — Add `_request_from_fixture` helper at tests/test_arm.py module top (BEFORE flipping any test) per I-010.** This helper deduplicates ~150 lines of identical request-reconstruction code across the 8 fixture-based flips and reduces typo-drift risk:

    ```python
    # tests/test_arm.py — module level, after imports, before the flipped tests.
    def _request_from_fixture(fx: dict[str, Any]) -> "ARMRequest":
        """Reconstruct an ARMRequest from a fixture dict (Phase 5 D-09 pattern).

        Handles arbitrary fixture shapes — Loan, ARMTerms, IndexPathEntry, ARMRequest
        rebuilding from JSON-string Decimals. Used by all 8 fixture-based flips in
        Plan 05-06 Task 4 (I-010 deduplication).
        """
        from datetime import date
        from decimal import Decimal
        from lib.arm import ARMRequest, ARMTerms, IndexPathEntry
        from lib.models import Loan

        req_dict = fx["request"]
        loan_dict = req_dict["loan"]
        terms_dict = req_dict["arm_terms"]
        loan = Loan(
            principal=Decimal(loan_dict["principal"]),
            annual_rate=Decimal(loan_dict["annual_rate"]),
            term_months=loan_dict["term_months"],
            origination_date=date.fromisoformat(loan_dict["origination_date"]),
            loan_type=loan_dict["loan_type"],
        )
        terms_kwargs = {
            "initial_period_months": terms_dict["initial_period_months"],
            "reset_period_months": terms_dict["reset_period_months"],
            "initial_cap_bps": terms_dict["initial_cap_bps"],
            "periodic_cap_bps": terms_dict["periodic_cap_bps"],
            "lifetime_cap_bps": terms_dict["lifetime_cap_bps"],
            "floor_rate": Decimal(terms_dict["floor_rate"]),
            "margin_bps": terms_dict["margin_bps"],
            "index_series_id": terms_dict["index_series_id"],
        }
        if terms_dict.get("note_rate") is not None:
            terms_kwargs["note_rate"] = Decimal(terms_dict["note_rate"])
        terms = ARMTerms(**terms_kwargs)
        index_path = [
            IndexPathEntry(period=e["period"], value=Decimal(e["value"]))
            for e in req_dict.get("index_path", [])
        ]
        return ARMRequest(
            loan=loan,
            arm_terms=terms,
            assumed_index_rate=Decimal(req_dict["assumed_index_rate"]),
            index_path=index_path,
        )
    ```

    With this helper in place, each of the 8 fixture-based flips (1-8) shrinks from ~25 lines of inline reconstruction to:

    ```python
    fx = arm_fixture("arm_5_1_payment_jump_at_61")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)
    # ... assertions follow ...
    ```

    The detailed inline reconstruction shown in the per-flip skeletons below is REPLACED by the `_request_from_fixture(fx)` call. Apply this substitution to flips 1-8.
    3. test_arm_10_1_payment_jump_at_121 (uses arm_10_1_payment_jump_at_121)
    4. test_arm_5_6_payment_jump_at_61_and_67 (uses arm_5_6_payment_jump_at_61_and_67)
    5. test_arm_initial_cap_at_first_reset (uses arm_initial_cap_at_first_reset)
    6. test_arm_lifetime_cap_binds (uses arm_lifetime_cap_binds)
    7. test_arm_floor_below_margin_blocked (uses arm_floor_below_margin_blocked)
    8. test_arm_5_1_off_by_one_negative (uses arm_5_1_off_by_one_negative)
    9. test_oracle_cross_validation_5_1 (uses oracle/bankrate_5_1_capture_2026 + oracle/vertex42_5_1_capture_2026 + arm_5_1_payment_jump_at_61)
    10. test_oracle_cross_validation_5_6 (uses oracle/americu_5_6_disclosure + arm_5_6_payment_jump_at_61_and_67)
    11. test_applied_cap_citation_coverage (walks tests/fixtures/arm/*.json directory; D-10 meta-test)

    Generic fixture-based test pattern (apply to flips 1-8):

    ```
    def test_arm_5_1_payment_jump_at_61(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-02 + ROADMAP SC-2: 5/1 ARM produces payment-jump at month 61."""
        from decimal import Decimal
        from datetime import date
        from lib.arm import ARMRequest, ARMTerms, IndexPathEntry, build_arm_schedule
        from lib.models import Loan
        fx = arm_fixture("arm_5_1_payment_jump_at_61")

        # Reconstruct request from fixture
        req_dict = fx["request"]
        loan_dict = req_dict["loan"]
        terms_dict = req_dict["arm_terms"]
        loan = Loan(
            principal=Decimal(loan_dict["principal"]),
            annual_rate=Decimal(loan_dict["annual_rate"]),
            term_months=loan_dict["term_months"],
            origination_date=date.fromisoformat(loan_dict["origination_date"]),
            loan_type=loan_dict["loan_type"],
        )
        terms = ARMTerms(
            initial_period_months=terms_dict["initial_period_months"],
            reset_period_months=terms_dict["reset_period_months"],
            initial_cap_bps=terms_dict["initial_cap_bps"],
            periodic_cap_bps=terms_dict["periodic_cap_bps"],
            lifetime_cap_bps=terms_dict["lifetime_cap_bps"],
            floor_rate=Decimal(terms_dict["floor_rate"]),
            margin_bps=terms_dict["margin_bps"],
            index_series_id=terms_dict["index_series_id"],
            note_rate=Decimal(terms_dict["note_rate"]) if terms_dict.get("note_rate") else None,
        )
        index_path = [
            IndexPathEntry(period=e["period"], value=Decimal(e["value"]))
            for e in req_dict.get("index_path", [])
        ]
        request = ARMRequest(
            loan=loan,
            arm_terms=terms,
            assumed_index_rate=Decimal(req_dict["assumed_index_rate"]),
            index_path=index_path,
        )

        # Run engine
        schedule = build_arm_schedule(request)

        # Assert against fixture's expected — exact Decimal equality on dollar-anchored fields.
        expected = fx["expected"]
        assert len(schedule.payments) == len(expected["payments"])
        # Last fixed-period payment (period 60): still old rate
        p_60 = schedule.payments[59]
        e_60 = expected["payments"][59]
        assert p_60.payment == Decimal(e_60["payment"])
        assert p_60.rate_in_effect == Decimal(e_60["rate_in_effect"])
        # First post-reset payment (period 61): new rate, new payment
        p_61 = schedule.payments[60]
        e_61 = expected["payments"][60]
        assert p_61.payment == Decimal(e_61["payment"])
        assert p_61.rate_in_effect == Decimal(e_61["rate_in_effect"])
        # Payment jump assertion (the load-bearing SC-2 assertion)
        assert p_61.payment != p_60.payment
        # Reset event at period 61
        assert schedule.reset_events[0].period == 61
        assert schedule.reset_events[0].old_rate == Decimal(e_60["rate_in_effect"])
        assert schedule.reset_events[0].new_rate == Decimal(e_61["rate_in_effect"])
        assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]

        # I-004: when fixture has a hand_calc_check witness (cap-bound fixtures only),
        # assert engine output matches the Decimal hand-calc EXACTLY (Decimal `==`).
        # This catches "engine pinned against itself" tautology for cap-bound scenarios
        # that Bankrate/Vertex42/AmericU oracles don't cover.
        first_re = expected["reset_events"][0]
        if "hand_calc_check" in first_re:
            hcc = first_re["hand_calc_check"]
            assert schedule.reset_events[0].new_rate == Decimal(hcc["new_rate_expected"]), (
                f"engine new_rate {schedule.reset_events[0].new_rate} != "
                f"hand_calc {hcc['new_rate_expected']} (Fannie B2-1.4-02 + D-02 formula)"
            )
            assert schedule.reset_events[0].applied_cap == hcc["applied_cap_expected"], (
                f"engine applied_cap {schedule.reset_events[0].applied_cap} != "
                f"hand_calc {hcc['applied_cap_expected']}"
            )
    ```

    Apply this pattern (with appropriate scenario adjustments) to flips 2-8. The `hand_calc_check` assertion block is generic — it activates only when the fixture has the witness (cap-bound) and is a no-op otherwise (non-cap-bound). The 7/1 test asserts `payments[83]` (last fixed) and `payments[84]` (first post-reset). The 10/1 test uses period 120/121. The 5/6 test asserts BOTH reset boundaries (period 61 + period 67). The off-by-one negative test asserts month 58 still old AND month 60 already new (the negative direction). Cap-bound tests assert applied_cap == "initial" / "lifetime" / "floor" matches fixture.

    **Flip 9: test_oracle_cross_validation_5_1** (cross-checks engine against Bankrate + Vertex42 captures)

    ```
    def test_oracle_cross_validation_5_1(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-06 + D-04 [REVISED]: hand-calc engine output AGREES EXACTLY with Bankrate
        AND Vertex42 5/1 ARM captures (industry-tool cross-validation per D-09)."""
        from decimal import Decimal
        # Load engine output (hand-calc fixture)
        engine_fx = arm_fixture("arm_5_1_payment_jump_at_61")
        engine_payments = engine_fx["expected"]["payments"]
        engine_by_period = {p["period"]: p for p in engine_payments}

        # Cross-check 1: Bankrate
        bankrate = arm_fixture("oracle/bankrate_5_1_capture_2026")
        for row in bankrate["expected_per_period"]:
            period = row["period"]
            engine_p = engine_by_period.get(period)
            assert engine_p is not None, f"Bankrate row for period {period} not in engine output"
            assert engine_p["rate_in_effect"] == row["rate"], (
                f"period {period}: engine rate {engine_p['rate_in_effect']} != Bankrate {row['rate']}"
            )
            assert engine_p["payment"] == row["payment"], (
                f"period {period}: engine payment {engine_p['payment']} != Bankrate {row['payment']}"
            )

        # Cross-check 2: Vertex42
        vertex42 = arm_fixture("oracle/vertex42_5_1_capture_2026")
        for row in vertex42["expected_per_period"]:
            period = row["period"]
            engine_p = engine_by_period.get(period)
            assert engine_p is not None, f"Vertex42 row for period {period} not in engine output"
            assert engine_p["rate_in_effect"] == row["rate"]
            assert engine_p["payment"] == row["payment"]
    ```

    **Flip 10: test_oracle_cross_validation_5_6**

    ```
    def test_oracle_cross_validation_5_6(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
        """ARM-06 + D-04 [REVISED]: 5/6 ARM engine output AGREES EXACTLY with AmericU SOFR disclosure
        worked example (lender-published 2/1/5-cap example)."""
        engine_fx = arm_fixture("arm_5_6_payment_jump_at_61_and_67")
        engine_by_period = {p["period"]: p for p in engine_fx["expected"]["payments"]}

        americu = arm_fixture("oracle/americu_5_6_disclosure")
        for row in americu["expected_per_period"]:
            period = row["period"]
            engine_p = engine_by_period.get(period)
            assert engine_p is not None, f"AmericU row for period {period} not in engine output"
            assert engine_p["rate_in_effect"] == row["rate"], (
                f"period {period}: engine rate {engine_p['rate_in_effect']} != AmericU {row['rate']}"
            )
            assert engine_p["payment"] == row["payment"], (
                f"period {period}: engine payment {engine_p['payment']} != AmericU {row['payment']}"
            )
    ```

    **Flip 11: test_applied_cap_citation_coverage** (D-10 meta-test)

    ```
    def test_applied_cap_citation_coverage() -> None:
        """D-10: every applied_cap Literal value (initial/periodic/lifetime/floor/none)
        is exercised by at least one fixture in tests/fixtures/arm/."""
        import json
        from pathlib import Path
        fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "arm"
        seen: set[str] = set()
        for fp in sorted(fixtures_dir.glob("*.json")):
            data = json.loads(fp.read_text())
            for re_event in data.get("expected", {}).get("reset_events", []):
                seen.add(re_event["applied_cap"])
        required = {"initial", "periodic", "lifetime", "floor", "none"}
        missing = required - seen
        assert not missing, (
            f"applied_cap coverage missing: {missing}. Seen: {seen}. "
            f"D-10 requires every Literal value to be exercised by ≥1 fixture."
        )
    ```

    For each of the 11 flips, REMOVE the `@pytest.mark.xfail(...)` decorator before the test definition.

    **Important note on test_oracle_cross_validation_5_1:** if Bankrate/Vertex42 captures only show e.g. 12 rows (yearly samples), only those 12 rows are asserted. The hand-calc 360-row fixture is internally complete; the oracle JSONs may be sparse — the test iterates oracle rows, not engine rows.
  </action>
  <verify>
    <automated>pytest tests/test_arm.py -k "test_arm_5_1_payment_jump_at_61 or test_arm_7_1_payment_jump_at_85 or test_arm_10_1_payment_jump_at_121 or test_arm_5_6_payment_jump_at_61_and_67 or test_arm_initial_cap_at_first_reset or test_arm_lifetime_cap_binds or test_arm_floor_below_margin_blocked or test_arm_5_1_off_by_one_negative or test_oracle_cross_validation_5_1 or test_oracle_cross_validation_5_6 or test_applied_cap_citation_coverage" -xvs</automated>
  </verify>
  <acceptance_criteria>
    - All 11 stubs flipped: 0 xfail decorators on the stub names listed above
    - `grep -c 'def _request_from_fixture' tests/test_arm.py` returns 1 (I-010 helper exists at module top)
    - Each of flips 1-8 calls `_request_from_fixture(fx)` exactly once (no inline Loan/ARMTerms reconstruction blocks remain duplicated): `grep -c '_request_from_fixture(' tests/test_arm.py` returns at least 8
    - `grep -c '@pytest.mark.xfail' tests/test_arm.py` returns 0 (FINAL phase: zero xfails remain)
    - All 11 named tests pass via `pytest tests/test_arm.py -k "<each name>" -x`
    - I-004 hand_calc_check assertion fires for all 3 cap-bound fixtures: tests for `arm_lifetime_cap_binds`, `arm_initial_cap_at_first_reset`, `arm_floor_below_margin_blocked` each exercise the `if "hand_calc_check" in first_re:` branch and assert engine output matches Decimal hand-calc EXACTLY. Verify by: `grep -c 'hand_calc_check' tests/test_arm.py` returns at least 1 (the conditional block) — and the test bodies include the `Decimal(hcc["new_rate_expected"])` assertion
    - `pytest tests/test_arm.py -x` runs 0 xfails AND 0 failures
    - `mypy --strict tests/test_arm.py` exits 0
    - `ruff check tests/test_arm.py` exits 0
    - `ruff format --check tests/test_arm.py` exits 0
  </acceptance_criteria>
  <done>
    All 11 remaining Wave-0 stubs flipped to passing; xfail count drops from 11 to 0; ARM-02..07 closed at the fixture layer.
  </done>
</task>

<task type="auto">
  <name>Task 5: Final verification — full Phase 5 closure check</name>
  <files>(verification only)</files>
  <read_first>
    - 05-VALIDATION.md "Phase gate" + ROADMAP SC rows
    - All prior plan SUMMARYs (Plans 05-00..05-05)
  </read_first>
  <action>
    Run the full pytest suite and full mypy/ruff hygiene check across every Phase 5 file. Expected counts:
    - Plan 05-05 baseline (Wave 5 closure; downstream of 05-04a + 05-04b): 421 passed + 4 skipped + 11 xfailed
    - Plan 05-06 delta: +11 stubs flipped → +11 passed, -11 xfailed
    - Final expected: 432 passed + 4 skipped + 0 xfailed + 0 failed + 0 errored

    **CRITICAL — ROADMAP SC final-verification matrix.** The following must all be true (pin via grep + targeted pytest):

    | Success Criterion | Verification |
    |---|---|
    | SC-1: ARMTerms has 8 explicit fields | test_arm_terms_field_set passes (Wave 2 verified) |
    | SC-2: 5/1 ARM payment-jump at month 61 | test_arm_5_1_payment_jump_at_61 passes (this Wave) |
    | SC-3: Both reset-month conventions (60/61) | test_arm_5_1_payment_jump_at_61 + test_arm_5_1_off_by_one_negative both pass |
    | SC-4: Floor enforced | test_arm_floor_below_margin_blocked passes (this Wave) |
    | SC-5: arm-mechanics.md cites Selling Guides + cited from ARMTerms docstring | test_arm_mechanics_doc_sections_present + test_arm_terms_docstring_cites_arm_mechanics + test_arm_mechanics_citations all pass (Wave 5) |

    Also verify:
    - All 9 ARM-N requirements are closed (every one has at least one passing test pinning it)
    - applied_cap citation coverage: D-10 meta-test passes (test_applied_cap_citation_coverage)
    - Phase 3 + Phase 4 byte-equivalent (zero regression)

    Run mypy + ruff on every Phase 5 file (the full set Phase 5 has touched):
    - `mypy --strict lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py scripts/_generate_arm_fixtures.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py`
    - `ruff check ...` (same)
    - `ruff format --check ...` (same)

    All MUST be clean. mypy --strict on scripts/_generate_arm_fixtures.py is included since it is a committed dev-tool.

    Final REPL sanity check — run scripts/arm_simulate.py end-to-end against the canonical fixture:
    ```
    python scripts/arm_simulate.py --input tests/fixtures/arm/arm_5_1_payment_jump_at_61.json
    ```
    Wait — this won't work directly because the fixture JSON has both `request` AND `expected` keys; the CLI takes JUST the request. Either:
    - (a) Extract the request portion: `python -c "import json; print(json.dumps(json.load(open('tests/fixtures/arm/arm_5_1_payment_jump_at_61.json'))['request']))" > /tmp/req.json && python scripts/arm_simulate.py --input /tmp/req.json | head -20`
    - (b) Skip this sanity check (the test_cli_smoke_subprocess_round_trip test already covers it)

    Choose (b) — the smoke test in Plan 05-04b already covers this; no need for a manual REPL sanity at this point.

    After all checks pass, declare Phase 5 closed.
  </action>
  <verify>
    <automated>pytest -q &amp;&amp; mypy --strict lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py scripts/_generate_arm_fixtures.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py &amp;&amp; ruff check lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py scripts/_generate_arm_fixtures.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q` final summary shows passed >= 432
    - `pytest -q` final summary shows xfailed = 0 (final phase: every stub flipped)
    - `pytest -q` final summary shows skipped >= 4
    - `pytest -q` final summary shows failed = 0
    - `pytest -q` final summary shows errors = 0
    - `pytest tests/test_amortize.py -q` byte-equivalent to Phase 3 closure
    - `pytest tests/test_affordability.py -q` byte-equivalent to Phase 4 closure
    - `mypy --strict` across all 12 Phase 5 files exits 0
    - `ruff check` across all 12 Phase 5 files exits 0
    - `ruff format --check` across all 12 Phase 5 files exits 0
    - All 9 ARM-N requirements closed (verify by `grep -c "ARM-0[1-9]" tests/test_arm.py` returns at least 30 — covers ARM-01 through ARM-09 with multiple tests each)
    - The applied_cap coverage meta-test exits 0 (verifies all 5 Literal values exercised across fixtures)
    - All 5 ROADMAP SCs pinned by named tests passing
  </acceptance_criteria>
  <done>
    Phase 5 fully closed. All ARM-01..09 requirements have passing tests. ROADMAP SC-1..SC-5 verified verbatim. Zero xfails. mypy + ruff clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Engine math → fixture values | Engine-emitted expected values (Phase 4 idiom) couple fixtures tightly to current engine; oracle cross-validation is the external check |
| Oracle PDFs (3rd party) → JSON transcription | Bankrate/Vertex42 UIs may change schema; transcription is manual; capture-date pinned in source field |
| AmericU PDF (frozen artifact) | 2022 lender disclosure; URL may eventually 404 — annual re-validation cadence |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-32 | Tampering (silent fixture drift) | tests/fixtures/arm/*.json expected blocks | mitigate | Each fixture has `source` field pointing to the engine version; regenerator script (scripts/_generate_arm_fixtures.py) is committed; any engine-math change requires re-running and re-committing fixtures |
| T-05-33 | Information Disclosure (oracle disagreement hidden) | test_oracle_cross_validation_5_1/5_6 | mitigate | Test compares engine output to Bankrate/Vertex42/AmericU on EXACT Decimal equality; ANY disagreement fails the test loudly with both sides logged in the assertion message |
| T-05-34 | Tampering (oracle URL rot) | tests/fixtures/arm/oracle/*.pdf | accept | Annual re-capture cadence (D-04 [REVISED]); AmericU is frozen artifact; if URLs 404 in the future, swap-in replacement oracle is a Phase 8+ concern |
| T-05-35 | Tampering (applied_cap classification gap) | D-10 citation-coverage meta-test | mitigate | test_applied_cap_citation_coverage walks ALL fixtures and asserts the 5 Literal values are present; missing value fails the test with explicit "missing: {set}" message |
| T-05-36 | Repudiation (ROADMAP SC-2 fixture lands at boundary) | arm_5_1_payment_jump_at_61 fixture's applied_cap | mitigate | Per LM-5: this fixture's request inputs explicitly chosen to produce applied_cap='none' (open interval); fixture generator pins those exact inputs; regression catches if numbers are changed |
| T-05-37 | Tampering (off-by-one regression on the off-by-one fixture) | arm_5_1_off_by_one_negative.json | mitigate | The fixture has the same engine output as the positive fixture; the test on this fixture asserts BOTH p[58] (month 59 = still old rate) and p[60] (month 61 = already new rate). Any off-by-one engine bug fails this test specifically |
</threat_model>

<verification>
- 11 hand-calc fixtures shipped + 5 oracle pairs (PDF + JSON) committed
- All 11 remaining Wave-0 stubs flipped to passing
- Final state: 432 passed, 0 xfailed, 4 skipped, 0 failed, 0 errors
- ARM-01..09 all closed
- ROADMAP SC-1..SC-5 verbatim verified
- applied_cap citation coverage (D-10) verified
- Phase 3 + Phase 4 byte-equivalent
- mypy --strict + ruff clean across 12 files
</verification>

<success_criteria>
- ARM-02 closed (4 product fixtures: 5/1, 7/1, 10/1, 5/6)
- ARM-03 closed (initial_cap + periodic_cap + lifetime_cap fixtures)
- ARM-04 closed (floor fixture)
- ARM-05 closed (continuous-numbering, cumulative-totals, full-remaining-term, non-final-no-zero, oracle-anchor — fixture-pinned)
- ARM-06 closed (Bankrate + Vertex42 + AmericU oracle cross-validation)
- ARM-07 closed (off-by-one negative direction)
- D-10 applied_cap citation-coverage verified
- Phase 5 ready for /gsd-verify-work
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-06-SUMMARY.md` documenting:
- 11 hand-calc fixtures shipped (each with source citation)
- 5 oracle pairs committed (Bankrate 5/1/7/1/10/1, Vertex42 5/1, AmericU 5/6)
- 11 Wave-0 stubs flipped to passing (full list)
- Final test counts: 432 passed + 4 skipped + 0 xfailed + 0 failed + 0 errors
- ARM-01..09 closure status (all closed)
- ROADMAP SC-1..SC-5 verification status (all closed)
- D-10 applied_cap coverage matrix (which fixture pins each Literal value)
- mypy + ruff status across 12 files
- Phase 5 ready for /gsd-verify-work
</output>
