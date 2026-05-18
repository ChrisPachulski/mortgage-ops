---
phase: 14
plan: 06
plan_id: 14-06
slug: golden-fixtures
type: execute
wave: 3
depends_on:
  - 14-01
  - 14-02
  - 14-03
  - 14-04
  - 14-05
files_modified:
  - tests/fixtures/property_analysis/sfh_conforming_king_county.json
  - tests/fixtures/property_analysis/condo_with_hoa_seattle.json
  - tests/fixtures/property_analysis/sfh_jumbo_bay_area.json
  - tests/fixtures/property_analysis/README.md
  - tests/test_property_analysis.py
  - tests/test_property_verdict.py
autonomous: true
requirements:
  - ANLZ-01
  - ANLZ-02
  - ANLZ-03
  - VERD-01
nyquist_compliant: true
tags:
  - fixtures
  - golden-values
  - citation-coverage
  - integration

must_haves:
  truths:
    - "tests/fixtures/property_analysis/ contains exactly 3 hand-calculated golden fixtures + 1 README: sfh_conforming_king_county.json (Conv30/Conv15/FHA30 eligible at 20% DP; verdict=GO), condo_with_hoa_seattle.json (HOA threads into PITI; Conv30 95% LTV with PMI; verdict pinned by hand-calc to exactly one of {GO, WATCH}), sfh_jumbo_bay_area.json (price > conforming limit; Jumbo30 row appears)."
    - "Every fixture has top-level keys: $schema, id, source, rounding=ROUND_HALF_UP, notes, _meta (with citation + requirements list), listing, household, profile, fred_rates, expected_response."
    - "Every fixture's `listing` block contains the Phase-13 required audit fields source_url, zpid, fetched_at (B-3 propagation)."
    - "Every Decimal value in fixtures is a JSON STRING (e.g., '425000.00'), never numeric — Pydantic strict=True rejects float (CLAUDE.md money discipline)."
    - "Every fixture's expected_response is hand-calculated with citation comments in the `notes` field — never auto-captured from the engine."
    - "Three golden-value tests in tests/test_property_analysis.py (test_sfh_conforming_king_county_golden, test_condo_with_hoa_seattle_golden, test_sfh_jumbo_bay_area_golden) load each fixture, call analyze(), and assert exact Decimal equality on every preferred-DP cell's monthly_pi + piti + dti_back + eligible + blocker_reasons + verdict.level + verdict.reasons[].predicate_code."
    - "test_verdict_code_citation_coverage in tests/test_property_verdict.py tightens to assert every VERDICT_* constant appears in at least one fixture's expected_response.verdict.reasons[].predicate_code (replacing the in-test cascade-coverage from Plan 14-04)."
    - "test_phase_14_requirement_coverage_meta asserts every requirement ID (ANLZ-01, ANLZ-02, ANLZ-03, VERD-01) appears in at least one fixture's _meta.citation field."
    - "Condo fixture's verdict.level is pinned to exactly ONE of {'GO', 'WATCH'} (W-1: not the string 'GO or WATCH'); notes field contains a cascade-level derivation explanation."
    - "tests/fixtures/property_analysis/README.md cites the synthetic-only-in-CI policy per Phase 11 D-02 (PATTERNS.md L919) and documents the capture-and-sanitize recipe (hand-calc per fixture; never auto-capture)."
  artifacts:
    - path: "tests/fixtures/property_analysis/sfh_conforming_king_county.json"
      provides: "SFH conforming golden fixture (verdict=GO)"
      contains: "sfh_conforming_king_county"
    - path: "tests/fixtures/property_analysis/condo_with_hoa_seattle.json"
      provides: "Condo+HOA conforming golden fixture (PMI applies at 95% LTV)"
      contains: "condo_with_hoa_seattle"
    - path: "tests/fixtures/property_analysis/sfh_jumbo_bay_area.json"
      provides: "Jumbo golden fixture (Jumbo30 row appears; conv ineligible)"
      contains: "sfh_jumbo_bay_area"
    - path: "tests/fixtures/property_analysis/README.md"
      provides: "Fixture policy + capture-and-sanitize recipe"
      contains: "Phase 11 D-02 inherited"
    - path: "tests/test_property_analysis.py"
      provides: "3 golden-value tests flipped from pytest.skip to real assertions"
      contains: "def test_sfh_conforming_king_county_golden"
    - path: "tests/test_property_verdict.py"
      provides: "Citation-coverage meta-test tightened to fixture-based"
      contains: "tests/fixtures/property_analysis"
  key_links:
    - from: "tests/test_property_analysis.py:test_sfh_conforming_king_county_golden"
      to: "tests/fixtures/property_analysis/sfh_conforming_king_county.json"
      via: "property_analysis_fixture loader (Plan 14-02)"
      pattern: "property_analysis_fixture\\(.sfh_conforming"
    - from: "tests/test_property_verdict.py:test_verdict_code_citation_coverage"
      to: "tests/fixtures/property_analysis/*.json"
      via: "filesystem read + JSON parse + predicate_code collection"
      pattern: "fixtures.*property_analysis"
---

<objective>
Ship the three hand-calculated golden-value fixtures + their integration tests. Tighten the citation-coverage meta-test from in-test cascade-coverage (Plan 14-04) to fixture-based coverage. Closes the phase: every requirement (ANLZ-01, ANLZ-02, ANLZ-03, VERD-01) now has fixture-level proof in addition to unit-level coverage.

Each fixture:
1. Is a real Pydantic-validatable JSON envelope (every Decimal value is a quoted string per CLAUDE.md money discipline).
2. Includes the Phase-13 required audit fields (source_url, zpid, fetched_at) on every listing block (B-3 propagation).
3. Has a `_meta.citation` block naming the requirements covered (ANLZ-01..03 + VERD-01 + the relevant ROADMAP SC).
4. Has an `expected_response` block that pins every preferred-DP cell's `monthly_pi`, `piti`, `dti_back`, `eligible`, `blocker_reasons` exactly, plus the verdict.level + verdict.reasons[].predicate_code.
5. Carries hand-calc citations in `notes` (e.g., "Phase 3 oracle: $400k @ 6.5%/30yr → monthly_pi=$2528.27").

The three fixtures cover the verdict-cascade space:
- **sfh_conforming_king_county.json** — verdict=GO (multiple non-FHA programs eligible at preferred DP).
- **condo_with_hoa_seattle.json** — verdict pinned by hand-calc to EXACTLY one of {GO, WATCH} (W-1 fix); notes field explains the cascade level derivation.
- **sfh_jumbo_bay_area.json** — verdict=NO_GO at preferred 20% DP (Conv/FHA ineligible due to jumbo; if Jumbo30 also fails DTI then full NO_GO at preferred DP — Cascade Level 2).

Output: 3 JSON fixtures (~150-250 lines each) + 1 README + 3 golden tests (flipped from stubs) + 2 tightened citation-coverage meta-tests.

---

## Iteration-2 Fixes (Check Report)

- **B-3 propagation (PropertyListing required fields in fixture JSON):** All three fixture `listing` blocks MUST include `source_url`, `zpid`, `fetched_at`. Updated acceptance criteria assert these fields exist.
- **W-1 (Condo verdict pinned with cascade-level derivation):** Task 2's condo fixture acceptance criterion tightened — `expected_response.verdict.level` MUST be exactly one of `{"GO", "WATCH"}` (NOT the string "GO or WATCH"). Fixture JSON MUST include a top-level `notes` field containing a cascade-level derivation explanation.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md
@.planning/phases/14-property-analysis-pipeline/14-RESEARCH.md
@.planning/phases/14-property-analysis-pipeline/14-PATTERNS.md
@.planning/phases/14-property-analysis-pipeline/14-05-SUMMARY.md
@CLAUDE.md
@lib/property_analysis.py
@lib/property_verdict.py
@lib/property_listing.py
@lib/household.py
@lib/profile.py
@tests/conftest.py
@tests/test_property_analysis.py
@tests/test_property_verdict.py
@tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json
@tests/fixtures/affordability/forward_jumbo_above_county_limit.json
@tests/fixtures/stress/income_shock_5_10_20_pct.json
@tests/fixtures/zillow/README.md
@tests/fixtures/golden_pmt.json

<interfaces>
From Plan 14-02 (conftest):
- `property_analysis_fixture: Callable[[str], dict[str, Any]]` — loads tests/fixtures/property_analysis/{stem}.json.

From Plan 14-05:
- `analyze(listing, household, profile, *, fred_mortgage_30us, fred_mortgage_15us) -> AnalysisReport`

From Plan 14-04:
- `lib.property_verdict.VERDICT_*` constants (5 total: NO_GO_DTI_ALL_PROGRAMS, NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP, WATCH_FHA_MIP_BURDEN, WATCH_STRESS_INCOME_FAIL, GO).

Fixture envelope shape (mirrors tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json):
```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "id": "<fixture-stem>",
  "source": "<provenance>",
  "rounding": "ROUND_HALF_UP",
  "notes": "<hand-calc citations + cascade-level derivation>",
  "_meta": {
    "citation": "ANLZ-01 + ANLZ-02 + VERD-01 verbatim: ...",
    "engine_version": "Phase 14 Plan 14-06",
    "requirements": ["ANLZ-01", "ANLZ-02", "ANLZ-03", "VERD-01"]
  },
  "listing": {
    "price": "...",
    "zip": "...",
    "property_type": "...",
    "source_url": "https://www.zillow.com/homedetails/synthetic/1_zpid/",
    "zpid": "1",
    "fetched_at": "2026-05-17T00:00:00Z",
    "tax_annual": {"value": "...", "provenance": "estimated"}
  },
  "household": { /* Household */ },
  "profile": { /* Profile */ },
  "fred_rates": { "MORTGAGE30US": "0.065000", "MORTGAGE15US": "0.058000" },
  "expected_response": {
    "verdict": { "level": "GO", "headline_reason": "...", "reasons": [...] },
    "matrix": {
      "cells_count": 18,
      "programs_present": ["Conv30", "Conv15", "FHA30"],
      "preferred_dp_cells": [
        {"program": "Conv30", "dp_pct": "0.200000", "monthly_pi": "...", "piti": "...", "dti_back": "...", "eligible": true, "blocker_reasons": []},
        ...
      ]
    },
    "tax": { "qualified_loan_limit": "750000", "over_750k_cap_per_program": {...} }
  }
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create tests/fixtures/property_analysis/ directory + sfh_conforming_king_county.json + README.md</name>
  <files>tests/fixtures/property_analysis/sfh_conforming_king_county.json, tests/fixtures/property_analysis/README.md</files>
  <read_first>
    - tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json (full — verbatim envelope shape)
    - tests/fixtures/stress/income_shock_5_10_20_pct.json (_meta block pattern)
    - tests/fixtures/zillow/README.md (full — README-style for synthetic-only policy + capture-and-sanitize recipe)
    - tests/fixtures/golden_pmt.json (4 Phase 3 oracles: $200k @ 6.5%/30yr → $1264.14; $200k @ 7%/15yr → $1797.66; $400k @ 6.5%/30yr → $2528.27; CFPB LE $162k @ 3.875%/30yr → $761.78)
    - lib/property_analysis.py:_build_program_result + _build_stress_block + _build_refi_block + _build_points_block + _build_tax_block (Plans 14-02, 14-03 output — to hand-trace the expected report)
    - lib/property_listing.py L44-86 (REQUIRED fields: source_url, zpid, fetched_at — B-3 propagation)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L785-922 (fixture envelope + README content patterns)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L972-1018 (Code Example 6 — fixture organization)
    - data/reference/conforming-limits-2026.yml (King County WA 1-unit limit; needed to ensure SFH @ $625k is conforming, not jumbo)
    - CLAUDE.md "Money discipline" (Decimal-from-strings; JSON strings, never numeric)
  </read_first>
  <behavior>
    - Behavior 1: tests/fixtures/property_analysis/ directory exists.
    - Behavior 2: tests/fixtures/property_analysis/README.md exists with sections: "Files" table, "Why synthetic, not live", "Capture-and-sanitize recipe", "When to regenerate", "What NOT to put here" — verbatim section headings per tests/fixtures/zillow/README.md.
    - Behavior 3: sfh_conforming_king_county.json validates as JSON.
    - Behavior 4: sfh_conforming_king_county.json has top-level keys: $schema, id, source, rounding, notes, _meta, listing, household, profile, fred_rates, expected_response.
    - Behavior 5: All Decimal values are JSON strings (e.g., `"price": "625000.00"`, not `"price": 625000`).
    - Behavior 6 (B-3 propagation): The `listing` block contains the Phase-13 required audit fields: `source_url` (length >= 10), `zpid` (matches `^\d+$`), `fetched_at` (ISO-8601 UTC string).
    - Behavior 7: The `listing` block validates as PropertyListing: `PropertyListing(**fixture["listing"])` succeeds (or model_validate_json after json.dumps). NOTE: PropertyListing's money fields are wrapped in ProvenancedMoney — fixture uses the nested `{"value": "...", "provenance": "scraped|user_provided|estimated"}` shape.
    - Behavior 8: The `household` block validates as lib.household.Household: `Household(**fixture["household"])` succeeds.
    - Behavior 9: The `profile` block validates as lib.profile.Profile: `Profile(**fixture["profile"])` succeeds.
    - Behavior 10: `fred_rates` has exactly two keys: "MORTGAGE30US" and "MORTGAGE15US" with values as quoted Decimal strings.
    - Behavior 11: `_meta.citation` references ANLZ-01..03 + VERD-01.
    - Behavior 12: `_meta.requirements` is a JSON array containing at least ["ANLZ-01", "ANLZ-02", "ANLZ-03", "VERD-01"].
    - Behavior 13: `expected_response.verdict.level` == "GO" for this fixture (multiple non-FHA programs eligible at 20% DP).
    - Behavior 14: `expected_response.verdict.reasons[0].predicate_code` == "GO-ALL-GREEN" (VERDICT_GO).
    - Behavior 15: `expected_response.matrix.programs_present` == ["Conv30", "Conv15", "FHA30"] (non-jumbo, non-VA-eligible).
    - Behavior 16: `expected_response.matrix.cells_count` == 18 (3 programs × 6 DPs).
    - Behavior 17: `expected_response.matrix.preferred_dp_cells` is an array of 3 cells (one per program at dp_pct=0.20) with hand-calculated `monthly_pi`, `piti`, `dti_back`, `eligible`, `blocker_reasons`.
    - Behavior 18: `expected_response.tax.qualified_loan_limit` == "750000" (profile.filing_status="mfj"; Pitfall 11 defaults).
    - Behavior 19: `notes` field contains hand-calc citations naming Phase 3 oracle values (e.g., "$400k @ 6.5% 30yr → monthly_pi=$2528.27 from tests/fixtures/golden_pmt.json").
    - Behavior 20: README.md contains the verbatim phrase "synthetic-only per Phase 11 D-02 inherited" (PATTERNS.md L919).
  </behavior>
  <action>
    Create tests/fixtures/property_analysis/ directory + sfh_conforming_king_county.json + README.md.

    **Scenario design (hand-calculated, not engine-captured):**

    Pick numbers that anchor to Phase 3 golden oracles where possible:
    - **Listing:** SFH @ $625,000 in King County WA (zip 98101); tax_annual=$6,000; insurance_estimate_annual=$1,200; HOA=$0 (SFH); zestimate=$640,000; year_built=2010; property_type="SFH". All money fields wrapped in `{"value": "...", "provenance": "estimated"}` per Phase 13 PropertyListing schema.
    - **Listing audit fields (B-3 propagation REQUIRED):**
      - `source_url`: `"https://www.zillow.com/homedetails/synthetic/1_zpid/"` (length 49 — passes `min_length=10`)
      - `zpid`: `"1"` (matches `^\d+$`)
      - `fetched_at`: `"2026-05-17T00:00:00Z"` (ISO-8601 UTC; matches the `_serialize_dt` Z-suffix convention from lib/property_listing.py L102-105)
    - **Household:** monthly_income=$12,000; monthly_obligations=$400 (low debt); fico=740; liquid_reserves=$150,000; state_fips="53", county_fips="033", county_name="King"; preferred_down_payment_pct=Decimal("0.20") (default).
    - **Profile:** all defaults (va_eligible=False, first_time_buyer=False, military_status="none", filing_status="mfj", marginal_tax_rate=null).
    - **FRED rates:** MORTGAGE30US="0.065000"; MORTGAGE15US="0.058000".

    **Expected report at preferred DP=0.20 (hand-calc):**
    - Conv30 at 20% DP: loan_amount = $625,000 × 0.80 = $500,000. monthly_pi via Phase 3 oracle reference (computed: $500k @ 6.5%/30yr — use lib.amortize directly to derive; embed in notes). Approximate: ~$3,160.34. monthly_tax = $500.00 ($6000/12). monthly_insurance = $100.00 ($1200/12). monthly_hoa = $0.00. monthly_mi = $0.00 (LTV=0.80, no PMI). piti = monthly_pi + 600 ≈ $3,760.34. dti_back = ($3,760.34 + $400) / $12,000 ≈ 0.346695. ltv = 0.800000. eligible = true. blocker_reasons = [].
    - Conv15 at 20% DP: loan_amount = $500,000. monthly_pi: $500k @ 5.8%/15yr (compute via lib.amortize for precision; reference Phase 3 oracle pattern). piti ≈ monthly_pi + $600. eligible = true.
    - FHA30 at 20% DP: loan_amount = base $500,000 + UFMIP financed (1.75% of $500k = $8,750) → $508,750. monthly_pi: $508,750 @ 6.5%/30yr. monthly_mi: $508,750 × FHA annual_mip_pct / 12 (read FHA-mip-rates.yml's 80% LTV row). piti accordingly. eligible = true (with FHA-specific DTI ceiling 0.57, easily passes given household income).

    Important: Run `python -c "from lib.amortize import build_schedule; from lib.models import Loan; from decimal import Decimal; l = Loan(principal=Decimal('500000.00'), annual_rate=Decimal('0.065000'), term_months=360, loan_type='fixed'); print(build_schedule(l).monthly_pi)"` to derive the EXACT monthly_pi value, then embed that string in the fixture. Document this derivation in `notes`. DO NOT guess — hand-calc anchors must match engine output to exact Decimal equality.

    **Verdict:** level=GO; reasons=[{"predicate_code": "GO-ALL-GREEN", "computed_value": "2", "program": null, "dp_pct": null}] (2 non-FHA programs eligible = Conv30 + Conv15).

    **Tax block:** qualified_loan_limit = "750000"; over_750k_cap_per_program for each of Conv30/Conv15/FHA30 = false ($500k < $750k for Conv30/15; $508,750 < $750k for FHA30); first_year_interest_per_program populated via hand-calc against build_schedule[:12] sums.

    **README.md content** (mirrors tests/fixtures/zillow/README.md style):

    ```markdown
    # Property Analysis Fixtures (Phase 14)

    Pinned, hand-calculated AnalysisReport oracles for deterministic ANLZ-01..03 +
    VERD-01 tests. Each fixture pins every preferred-DP cell of the matrix and the
    full verdict.reasons[] list by exact Decimal equality.

    ## Files

    | File | Tested SC | Covers |
    |------|-----------|--------|
    | `sfh_conforming_king_county.json` | ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 | Conv30/Conv15/FHA30 conforming SFH; full 3×6 matrix; verdict=GO |
    | `condo_with_hoa_seattle.json` | ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 | Condo at 95% LTV with HOA + PMI; verdict pinned by hand-calc |
    | `sfh_jumbo_bay_area.json` | ANLZ-01, VERD-01 | price > conforming → Jumbo30 row appears; FHA + Conv ineligible |

    ## Why synthetic, not live (D-02 inherited from Phase 11)

    - Determinism: tests must produce identical bytes across runs and machines.
    - Zero recurring cost: no Zillow API key; no FRED live fetch in CI.
    - Airgap-safe: tests run with network disabled.
    - Contract-is-shape: fixtures pin the AnalysisReport schema, not market data.

    ## Capture-and-sanitize recipe (Phase 14-specific)

    Each fixture's `expected_response` is HAND-CALCULATED with citation comments
    in the `notes` field — never auto-captured from the engine.

    1. Derive monthly_pi via Phase 3 oracle pattern (use `python -c "from lib.amortize import build_schedule; from lib.models import Loan; ..."` to compute, then embed).
    2. Compose PITI = P&I + tax/12 + insurance/12 + HOA + MI (Pitfall 6).
    3. Compute DTI back-end = (PITI + obligations) / monthly_income.
    4. Cite the hand-calc in `notes`.
    5. Audit fields (source_url, zpid, fetched_at) default to synthetic values
       per Plan 14-06 B-3 fix.

    ## When to regenerate

    - After any change to lib/property_analysis.py `analyze()` body that changes
      the AnalysisReport shape — every fixture's expected_response must be
      re-hand-calculated.
    - After any `data/reference/*.yml` refresh — re-derive PITI cells.

    ## What NOT to put here

    - **No real addresses.** Synthetic-only per Phase 11 D-02 inherited. Use
      `123 Synthetic Way, Seattle, WA 98101` style values. ZIP stays real (the
      ZIP is not PII on its own).
    - **No AI-attribution markers.** Per the project-wide CLAUDE.md global rule.
    - **No raw lender quotes.** Conventional PMI rates are bureau-specific; use
      the RESEARCH Pitfall 1 estimated value `Decimal("0.0075")` annualized.
    - **No `config/household.yml` values.** Synthetic financial profiles only.
    ```

    DO NOT auto-capture the expected_response from the engine. Hand-derive every numeric value and cite the derivation in `notes`.
    DO NOT use numeric (non-string) JSON values for any money or rate field.
    DO NOT include PII, real addresses, or real lender quotes.
    DO NOT add Co-Authored-By or AI-attribution markers anywhere.
    DO ensure household.preferred_down_payment_pct is "0.200000" (exact decimal_places=6 per the Rate alias).
    DO derive monthly_pi values by running build_schedule once and pinning the result; the fixture's exact-Decimal values must match what the engine will produce when the test runs.
    DO include source_url, zpid, fetched_at in the listing block (B-3 propagation).
  </action>
  <verify>
    <automated>python -c "import json; data = json.loads(open('tests/fixtures/property_analysis/sfh_conforming_king_county.json').read()); assert 'expected_response' in data and 'verdict' in data['expected_response']; assert data['expected_response']['verdict']['level'] == 'GO'; assert 'source_url' in data['listing'] and 'zpid' in data['listing'] and 'fetched_at' in data['listing']"</automated>
  </verify>
  <acceptance_criteria>
    - `tests/fixtures/property_analysis/` directory exists.
    - `tests/fixtures/property_analysis/sfh_conforming_king_county.json` exists and parses as JSON.
    - `tests/fixtures/property_analysis/README.md` exists.
    - `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/sfh_conforming_king_county.json').read()); assert set(d.keys()) >= {'\$schema', 'id', 'source', 'rounding', 'notes', '_meta', 'listing', 'household', 'profile', 'fred_rates', 'expected_response'}"` exits 0.
    - **B-3 (Task 1):** `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/sfh_conforming_king_county.json').read()); l = d['listing']; assert 'source_url' in l and len(l['source_url']) >= 10; assert 'zpid' in l and l['zpid'].isdigit(); assert 'fetched_at' in l"` exits 0.
    - `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/sfh_conforming_king_county.json').read()); assert d['expected_response']['verdict']['level'] == 'GO'; assert d['expected_response']['verdict']['reasons'][0]['predicate_code'] == 'GO-ALL-GREEN'"` exits 0.
    - `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/sfh_conforming_king_county.json').read()); assert d['expected_response']['matrix']['cells_count'] == 18; assert d['expected_response']['matrix']['programs_present'] == ['Conv30', 'Conv15', 'FHA30']"` exits 0.
    - Validates as Pydantic models: `python -c "import json; from lib.property_listing import PropertyListing; from lib.household import Household; from lib.profile import Profile; d = json.loads(open('tests/fixtures/property_analysis/sfh_conforming_king_county.json').read()); PropertyListing.model_validate_json(json.dumps(d['listing'])); Household.model_validate_json(json.dumps(d['household'])); Profile.model_validate_json(json.dumps(d['profile']))"` exits 0.
    - `grep -c '"price": [0-9]' tests/fixtures/property_analysis/sfh_conforming_king_county.json` returns 0 (no numeric Decimal values — all quoted strings).
    - `grep -c 'synthetic-only per Phase 11 D-02 inherited' tests/fixtures/property_analysis/README.md` returns 1.
    - `grep -c 'Co-Authored-By\|Generated with' tests/fixtures/property_analysis/sfh_conforming_king_county.json tests/fixtures/property_analysis/README.md` returns 0 (no AI attribution).
    - `grep -c 'ANLZ-01\|ANLZ-02\|ANLZ-03\|VERD-01' tests/fixtures/property_analysis/sfh_conforming_king_county.json` returns at least 4.
    - `grep -c '"source_url"' tests/fixtures/property_analysis/sfh_conforming_king_county.json` returns 1 (B-3).
    - `grep -c '"zpid"' tests/fixtures/property_analysis/sfh_conforming_king_county.json` returns 1 (B-3).
    - `grep -c '"fetched_at"' tests/fixtures/property_analysis/sfh_conforming_king_county.json` returns 1 (B-3).
  </acceptance_criteria>
  <done>
    First golden fixture + README ship; both validate as JSON; listing/household/profile sub-blocks validate as their Pydantic models; verdict=GO with predicate_code "GO-ALL-GREEN" pinned; B-3 audit fields present.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create condo_with_hoa_seattle.json + sfh_jumbo_bay_area.json fixtures</name>
  <files>tests/fixtures/property_analysis/condo_with_hoa_seattle.json, tests/fixtures/property_analysis/sfh_jumbo_bay_area.json</files>
  <read_first>
    - tests/fixtures/property_analysis/sfh_conforming_king_county.json (Task 1 output — fixture-shape template to mirror, INCLUDING source_url/zpid/fetched_at defaults)
    - tests/fixtures/property_analysis/README.md (Task 1 output)
    - tests/fixtures/affordability/forward_jumbo_above_county_limit.json (jumbo-shape sibling fixture)
    - data/reference/conforming-limits-2026.yml (Santa Clara CA limit for the jumbo case; King County WA limit if needed)
    - data/reference/fha-mip-rates.yml (FHA monthly MIP percentages by LTV)
    - lib/property_analysis.py (Plan 14-05 output)
    - lib/property_verdict.py (Plan 14-04 — VERDICT_* constants)
    - lib/property_listing.py L44-86 (REQUIRED fields: source_url, zpid, fetched_at — B-3 propagation)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L972-1015 (Code Example 6 + fixture organization)
    - .planning/phases/14-property-analysis-pipeline/14-PLAN-CHECK.md W-1 (verdict-level pin + cascade-derivation requirement)
  </read_first>
  <behavior>
    - Behavior 1: condo_with_hoa_seattle.json validates as JSON + listing/household/profile validate as their Pydantic models.
    - Behavior 2: Condo fixture's listing has `property_type="condo"`, `hoa_monthly` as ProvenancedMoney with value > 0 (e.g., "450.00").
    - Behavior 2b (B-3 propagation): Condo fixture's listing block contains `source_url`, `zpid`, `fetched_at`.
    - Behavior 3: Condo fixture's household.preferred_down_payment_pct == "0.050000" (5% DP scenario to force PMI). At 5% LTV=95%, Conv30 carries PMI per Pitfall 1.
    - Behavior 4 (W-1 fix): Condo fixture's `expected_response.verdict.level` is pinned by hand-calc to EXACTLY one of `"GO"` or `"WATCH"` (NOT the string "GO or WATCH"). The chosen value is determined by hand-tracing the cascade levels at fixture-construction time and embedded as a single Literal.
    - Behavior 4b (W-1 fix): Condo fixture has a top-level `notes` field containing a cascade-level derivation explanation: substring `"cascade"` (case-insensitive) AND substring `"hand-calc"` (case-insensitive) MUST appear; the explanation names which cascade level resolved the verdict (e.g., "Cascade level 5: Conv30 + Conv15 + FHA30 eligible at 20% DP; no income-shock failures across eligible → GO. Hand-calc anchor: see _build_program_result for Conv30 @ 20% DP.").
    - Behavior 5: At least one preferred_dp_cells entry has `eligible_reasons` containing "PMI-RATE-ESTIMATED-0.0075" (Conv30 cell at LTV=0.95).
    - Behavior 6: Condo fixture's matrix.cells_count == 18 (3 programs × 6 DPs; non-jumbo, non-VA).
    - Behavior 7: sfh_jumbo_bay_area.json validates as JSON + Pydantic.
    - Behavior 7b (B-3 propagation): Jumbo fixture's listing block contains `source_url`, `zpid`, `fetched_at`.
    - Behavior 8: Jumbo fixture's listing.price > Santa Clara CA conforming limit (use $1,850,000 to comfortably exceed both baseline and high-cost county limit; verify against data/reference/conforming-limits-2026.yml).
    - Behavior 9: Jumbo fixture's household.state_fips="06", county_fips="085", county_name="Santa Clara".
    - Behavior 10: Jumbo fixture's `expected_response.matrix.programs_present` includes "Jumbo30"; cells_count == 24 (4 × 6).
    - Behavior 11: Jumbo fixture's `expected_response.matrix.preferred_dp_cells` contains a Jumbo30 entry; Conv30 + FHA30 are present-but-ineligible (per D-14-MATRIX-02 numerics-populated-anyway) with blocker_reasons containing the conforming-limit / FHA-loan-limit citation strings.
    - Behavior 12: Jumbo fixture's `expected_response.verdict.level` is one of: "GO" (Jumbo30 eligible at preferred DP), "WATCH" (Jumbo30-only eligible + stress-fail), or "NO_GO" (if Jumbo30 also fails DTI at preferred DP — Cascade Level 2). Pinned by hand-calc.
    - Behavior 13: Both fixtures have `_meta.citation` referencing ANLZ-01..03 + VERD-01; `_meta.requirements` array contains those IDs.
    - Behavior 14: Both fixtures use synthetic state/county FIPS that EXIST in data/reference/conforming-limits-2026.yml (so MissingCountyDataError does NOT fire for the jumbo case; that's a separate behavior covered in Plan 14-02 unit tests).
  </behavior>
  <action>
    Create both fixture files mirroring sfh_conforming_king_county.json structure exactly (INCLUDING the source_url/zpid/fetched_at audit-field defaults from Task 1).

    **condo_with_hoa_seattle.json scenario:**
    - **Listing:** condo @ $475,000 in zip 98101 King WA; tax_annual=$5,000; insurance_estimate_annual=$900; hoa_monthly=$450; property_type="condo"; year_built=2015. All money in ProvenancedMoney wrapper.
    - **Listing audit fields (B-3 propagation REQUIRED):**
      - `source_url`: `"https://www.zillow.com/homedetails/synthetic/2_zpid/"`
      - `zpid`: `"2"`
      - `fetched_at`: `"2026-05-17T00:00:00Z"`
    - **Household:** monthly_income=$9,500; monthly_obligations=$300; fico=720; liquid_reserves=$40,000; state_fips="53", county_fips="033", county_name="King"; preferred_down_payment_pct="0.050000" (5% — forces PMI on Conv).
    - **Profile:** all defaults; filing_status="mfj".
    - **FRED rates:** MORTGAGE30US="0.065000"; MORTGAGE15US="0.058000".

    Hand-calc anchor at 5% DP:
    - Conv30: loan_amount = $475,000 × 0.95 = $451,250. ltv=0.950000. monthly_pi via lib.amortize @ $451,250 @ 6.5% 30yr → derive exact value. monthly_mi = quantize_cents($451,250 × Decimal("0.0075") / 12) = $282.03 (≈). piti = monthly_pi + ($5000/12) + ($900/12) + $450 + monthly_mi. dti_back = (piti + $300) / $9500. Likely close to ceiling; pin eligibility status via hand-calc.
    - Conv15: similar but 5.8% / 15yr.
    - FHA30: UFMIP financed; monthly_mip per FHA table at 95% LTV (typically 0.85%/yr).

    **W-1 RESOLUTION — verdict pinning:**
    1. Hand-trace the cascade (Plan 14-04 levels 1-5) for this scenario:
       - Level 1 NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP — applicable iff zero programs eligible at 5% DP.
       - Level 2 NO_GO_DTI_ALL_PROGRAMS — applicable iff all programs fail DTI.
       - Level 3 WATCH_STRESS_INCOME_FAIL — applicable iff stress-block income-shock breaches.
       - Level 4 WATCH_FHA_MIP_BURDEN — applicable iff FHA-only path AND monthly_mi > $300.
       - Level 5 GO — multiple non-FHA programs eligible.
    2. Compute which level fires. Embed the chosen Literal as `expected_response.verdict.level`.
    3. **Pin to exactly ONE of {"GO", "WATCH"}** — never the string "GO or WATCH". The hand-calc decides.
    4. Add `notes` field with cascade derivation, e.g.:
       ```
       "Cascade level 5: Conv30 + Conv15 + FHA30 eligible at 5% DP; income-shock check
        shows VA's 0.41 ceiling not in play (VA not eligible). Conv30 stressed DTI under
        -30% income = (piti + $300)/(9500*0.70) ≈ 0.46 < 0.50 → no breach. Hand-calc
        anchor: see _build_program_result for Conv30 @ 5% DP + _build_stress_block
        income_shock evaluation. Final verdict pinned: <GO|WATCH>."
       ```

    **sfh_jumbo_bay_area.json scenario:**
    - **Listing:** SFH @ $1,850,000 in zip 95110 (San Jose CA); tax_annual=$22,000; insurance_estimate_annual=$2,400; hoa_monthly=$0; property_type="SFH"; year_built=2005. All money in ProvenancedMoney wrapper.
    - **Listing audit fields (B-3 propagation REQUIRED):**
      - `source_url`: `"https://www.zillow.com/homedetails/synthetic/3_zpid/"`
      - `zpid`: `"3"`
      - `fetched_at`: `"2026-05-17T00:00:00Z"`
    - **Household:** monthly_income=$28,000; monthly_obligations=$1,000; fico=760; liquid_reserves=$500,000; state_fips="06", county_fips="085", county_name="Santa Clara"; preferred_down_payment_pct="0.200000".
    - **Profile:** all defaults; filing_status="mfj".
    - **FRED rates:** MORTGAGE30US="0.065000"; MORTGAGE15US="0.058000".

    Hand-calc anchor at 20% DP:
    - loan_amount = $1,850,000 × 0.80 = $1,480,000. Above any conforming limit including Santa Clara high-cost ($1,149,825 2026 baseline 1-unit). classify() returns "jumbo".
    - Conv30 / Conv15: present-but-ineligible (D-14-MATRIX-02 numerics still populated); blocker_reasons[0] = "FHFA-LIMIT-CONVENTIONAL" or similar (read verbatim from lib.affordability.AffordabilityResponse.blocked_by).
    - FHA30: present-but-ineligible (loan_amount > FHA county limit); blocker_reasons[0] = "HUD-LIMIT-FHA" or similar.
    - Jumbo30: appears as 4th program; loan_amount=$1,480,000 @ 6.5% 30yr. monthly_pi derived via lib.amortize. dti_back = (piti + $1000) / $28,000 — likely passes given high income against Jumbo's 0.43 ceiling. eligible=true.
    - Tax: over_750k_cap_per_program["Jumbo30"] == true ($1,480,000 > $750,000).

    Expected verdict: GO (Jumbo30 eligible at preferred 20% DP, no income-shock failure). Pin in fixture with cascade-level explanation in notes.

    For BOTH fixtures, generate the exact monthly_pi + monthly_mi + piti values by:
    1. Building a Loan() with the precise principal/rate/term.
    2. Calling lib.amortize.build_schedule(loan).
    3. Reading schedule.monthly_pi.
    4. Pasting the EXACT Decimal string into the fixture.
    5. Citing this derivation in the `notes` field.

    Do not skip the derivation. The integration test that loads this fixture WILL assert exact Decimal equality and will fail loudly if the pinned value differs by even one cent from the engine's output.

    DO NOT use random fips codes. Verify "06"/"085"/"Santa Clara" appears in data/reference/conforming-limits-2026.yml so classify() succeeds (avoids the MissingCountyDataError path which is covered elsewhere).
    DO NOT exceed 250 lines per fixture file. preferred_dp_cells is a 3-5 entry list; non-preferred cells are NOT in expected_response (golden tests only assert preferred-DP cells).
    DO NOT add full Schedule.payments — Pitfall 10 says no full schedules; only summary scalars (this is already enforced by ProgramResult shape from Plan 14-02).
    DO include source_url, zpid, fetched_at in BOTH listing blocks (B-3 propagation).
    DO write a single Literal value for condo verdict.level (W-1).
    DO include a cascade-level derivation string in the condo notes field (W-1).
  </action>
  <verify>
    <automated>python -c "import json; from lib.property_listing import PropertyListing; from lib.household import Household; from lib.profile import Profile; [PropertyListing.model_validate_json(json.dumps(json.loads(open(p).read())['listing'])) for p in ['tests/fixtures/property_analysis/condo_with_hoa_seattle.json', 'tests/fixtures/property_analysis/sfh_jumbo_bay_area.json']]; [Household.model_validate_json(json.dumps(json.loads(open(p).read())['household'])) for p in ['tests/fixtures/property_analysis/condo_with_hoa_seattle.json', 'tests/fixtures/property_analysis/sfh_jumbo_bay_area.json']]"</automated>
  </verify>
  <acceptance_criteria>
    - `tests/fixtures/property_analysis/condo_with_hoa_seattle.json` and `tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` both exist.
    - Both parse as JSON: `python -c "import json; [json.loads(open(p).read()) for p in ['tests/fixtures/property_analysis/condo_with_hoa_seattle.json', 'tests/fixtures/property_analysis/sfh_jumbo_bay_area.json']]"` exits 0.
    - Both sub-models validate against their Pydantic contracts (see <automated> above).
    - **B-3 (condo):** `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/condo_with_hoa_seattle.json').read()); l = d['listing']; assert 'source_url' in l and len(l['source_url']) >= 10; assert 'zpid' in l and l['zpid'].isdigit(); assert 'fetched_at' in l"` exits 0.
    - **B-3 (jumbo):** `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/sfh_jumbo_bay_area.json').read()); l = d['listing']; assert 'source_url' in l and len(l['source_url']) >= 10; assert 'zpid' in l and l['zpid'].isdigit(); assert 'fetched_at' in l"` exits 0.
    - **W-1 (condo verdict pin):** `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/condo_with_hoa_seattle.json').read()); assert d['expected_response']['verdict']['level'] in ('GO','WATCH'); assert 'notes' in d and 'cascade' in d['notes'].lower() and 'hand-calc' in d['notes'].lower()"` exits 0.
    - Condo fixture matrix shape: `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/condo_with_hoa_seattle.json').read()); assert d['listing']['property_type'] == 'condo' and d['expected_response']['matrix']['cells_count'] == 18"` exits 0.
    - Jumbo fixture: `python -c "import json; d = json.loads(open('tests/fixtures/property_analysis/sfh_jumbo_bay_area.json').read()); assert 'Jumbo30' in d['expected_response']['matrix']['programs_present']; assert d['expected_response']['matrix']['cells_count'] == 24"` exits 0.
    - Condo fixture has `PMI-RATE-ESTIMATED-0.0075` in at least one cell's eligible_reasons: `grep -c 'PMI-RATE-ESTIMATED-0.0075' tests/fixtures/property_analysis/condo_with_hoa_seattle.json` returns at least 1.
    - All money values are quoted JSON strings: `grep -c '"price": [0-9]' tests/fixtures/property_analysis/condo_with_hoa_seattle.json tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` returns 0.
    - Both fixtures reference ANLZ + VERD requirement IDs: `grep -c 'ANLZ-01\|ANLZ-02\|ANLZ-03\|VERD-01' tests/fixtures/property_analysis/condo_with_hoa_seattle.json tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` returns at least 6 (3 minimum per fixture).
    - Condo + jumbo source_url/zpid/fetched_at present (B-3): `grep -c '"source_url"' tests/fixtures/property_analysis/condo_with_hoa_seattle.json tests/fixtures/property_analysis/sfh_jumbo_bay_area.json` returns 2; same for `"zpid"` and `"fetched_at"`.
  </acceptance_criteria>
  <done>
    Both remaining golden fixtures ship. All 3 fixtures validate against their Pydantic models. Jumbo30 row appears in jumbo fixture; PMI-rate-estimated warning surfaces in condo fixture. Condo verdict.level pinned to a single Literal value with cascade-derivation in notes (W-1). All fixtures include B-3 audit fields.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Flip golden-fixture tests in tests/test_property_analysis.py + tighten citation-coverage in tests/test_property_verdict.py</name>
  <files>tests/test_property_analysis.py, tests/test_property_verdict.py</files>
  <read_first>
    - tests/test_property_analysis.py (Plans 14-02, 14-03, 14-05 output — includes 3 pytest.skip stubs for golden tests)
    - tests/test_property_verdict.py (Plan 14-04 output — contains test_verdict_code_citation_coverage with in-test scenario coverage)
    - tests/test_affordability.py L1162-1199 (test_blocked_by_citation_coverage — fixture-based pattern to mirror)
    - tests/test_stress.py L718-790 (test_phase_08_citation_coverage_meta — phase-wide pattern)
    - tests/fixtures/property_analysis/*.json (Tasks 1 + 2 output)
    - tests/conftest.py (property_analysis_fixture loader from Plan 14-02)
    - lib/property_analysis.py (analyze() from Plan 14-05)
    - lib/property_verdict.py (Plan 14-04)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L593-662 (fixture-driven test pattern + meta-test patterns)
  </read_first>
  <behavior>
    Flip the 3 golden-fixture stubs in tests/test_property_analysis.py:
    - `test_sfh_conforming_king_county_golden` — Load fixture via `property_analysis_fixture("sfh_conforming_king_county")`; construct PropertyListing/Household/Profile from fixture; call `analyze(listing, household, profile, fred_mortgage_30us=Decimal(fixture["fred_rates"]["MORTGAGE30US"]), fred_mortgage_15us=Decimal(fixture["fred_rates"]["MORTGAGE15US"]))`; assert:
        - `report.matrix.cells_count == fixture["expected_response"]["matrix"]["cells_count"]`
        - For each expected preferred_dp_cell, find matching cell in report.matrix.cells (by program + down_payment_pct) and assert exact Decimal equality on monthly_pi, piti, dti_back, eligible, blocker_reasons.
        - `report.verdict.level == fixture["expected_response"]["verdict"]["level"]`
        - For each expected verdict reason, find matching reason in report.verdict.reasons (by predicate_code) and assert computed_value matches.
        - `report.tax.qualified_loan_limit == Decimal(fixture["expected_response"]["tax"]["qualified_loan_limit"])`.

    - `test_condo_with_hoa_seattle_golden` — Same pattern; expect at least one cell with "PMI-RATE-ESTIMATED-0.0075" in eligible_reasons. Verdict.level read from fixture (pinned by W-1 to exactly "GO" or "WATCH").

    - `test_sfh_jumbo_bay_area_golden` — Same pattern; expect Jumbo30 in matrix.programs_present; expect over_750k_cap_per_program["Jumbo30"] == true.

    Tighten the citation-coverage meta-test in tests/test_property_verdict.py:
    - `test_verdict_code_citation_coverage` — Replace the in-test cascade-based coverage with FIXTURE-BASED coverage (mirrors tests/test_affordability.py:test_blocked_by_citation_coverage):
        ```python
        def test_verdict_code_citation_coverage() -> None:
            """Pitfall 12: every VERDICT_* constant in lib/property_verdict.py is
            exercised by at least one fixture's expected_response.verdict.reasons[].predicate_code.
            (Plan 14-04 covered this in-test; Plan 14-06 tightens to fixture-based.)"""
            from pathlib import Path
            import json
            import lib.property_verdict as v

            constants = {name: val for name, val in vars(v).items()
                         if isinstance(name, str) and name.startswith("VERDICT_") and isinstance(val, str)}
            assert constants, "No VERDICT_* constants found"

            fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "property_analysis"
            all_predicate_codes: list[str] = []
            for fp in sorted(fixtures_dir.glob("*.json")):
                data = json.loads(fp.read_text())
                expected = data.get("expected_response", {})
                verdict = expected.get("verdict", {})
                for r in verdict.get("reasons", []):
                    all_predicate_codes.append(r.get("predicate_code", ""))

            for name, code in constants.items():
                assert code in all_predicate_codes, (
                    f"VERDICT constant {name}={code!r} not exercised by any fixture's "
                    f"verdict.reasons[].predicate_code"
                )
        ```

    Add NEW test `test_phase_14_requirement_coverage_meta` in tests/test_property_verdict.py:
        ```python
        def test_phase_14_requirement_coverage_meta() -> None:
            """RESEARCH §"Validation Architecture": every ANLZ-XX + VERD-01 requirement
            appears in at least one fixture's _meta.citation or _meta.requirements.
            Mirrors tests/test_stress.py:test_phase_08_citation_coverage_meta."""
            from pathlib import Path
            import json

            fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "property_analysis"
            all_meta_text: list[str] = []
            all_requirements: set[str] = set()
            for fp in sorted(fixtures_dir.glob("*.json")):
                data = json.loads(fp.read_text())
                meta = data.get("_meta", {})
                all_meta_text.append(meta.get("citation", ""))
                all_requirements.update(meta.get("requirements", []))

            target_ids = ["ANLZ-01", "ANLZ-02", "ANLZ-03", "VERD-01"]
            for req_id in target_ids:
                in_citation = any(req_id in c for c in all_meta_text)
                in_requirements = req_id in all_requirements
                assert in_citation or in_requirements, (
                    f"Phase 14 requirement {req_id} not found in any fixture's "
                    f"_meta.citation or _meta.requirements"
                )
        ```

    Both meta-tests must PASS now that 3 fixtures ship.

    Strict-mode Decimal JSON re-validation (per PATTERNS.md L590): every golden test loads JSON, re-encodes the listing/household/profile sub-blocks via `json.dumps(...)`, then calls `Model.model_validate_json(...)` (NOT `Model(**dict)`) because strict-mode Decimal fields require the JSON parsing path.
  </behavior>
  <action>
    Edit `tests/test_property_analysis.py`:
    1. Replace `pytest.skip(...)` in `test_sfh_conforming_king_county_golden` with the real fixture-driven assertion body per Behavior 1.
    2. Same for `test_condo_with_hoa_seattle_golden`.
    3. Same for `test_sfh_jumbo_bay_area_golden`.

    Each golden test follows this template (pattern verbatim from PATTERNS.md L1157-1192 + tests/test_stress.py:L547-590):

    ```python
    def test_sfh_conforming_king_county_golden(
        property_analysis_fixture,
    ) -> None:
        """ANLZ-01..03 + VERD-01 golden-value pin: SFH conforming King County WA.
        Fixture: tests/fixtures/property_analysis/sfh_conforming_king_county.json.
        Hand-calc anchor per fixture `notes`."""
        fx = property_analysis_fixture("sfh_conforming_king_county")

        # PATTERNS.md L590: strict-mode Decimal fields require JSON parse path,
        # NOT validate_python(dict). Re-encode each sub-block.
        listing = PropertyListing.model_validate_json(json.dumps(fx["listing"]))
        household = Household.model_validate_json(json.dumps(fx["household"]))
        profile = Profile.model_validate_json(json.dumps(fx["profile"]))

        report = analyze(
            listing, household, profile,
            fred_mortgage_30us=Decimal(fx["fred_rates"]["MORTGAGE30US"]),
            fred_mortgage_15us=Decimal(fx["fred_rates"]["MORTGAGE15US"]),
        )

        expected_matrix = fx["expected_response"]["matrix"]
        assert len(report.matrix.cells) == expected_matrix["cells_count"]
        assert sorted(report.matrix.programs_present) == sorted(expected_matrix["programs_present"])

        for expected_cell in expected_matrix["preferred_dp_cells"]:
            actual = next(
                c for c in report.matrix.cells
                if c.program == expected_cell["program"]
                and c.down_payment_pct == Decimal(expected_cell["dp_pct"])
            )
            assert actual.monthly_pi == Decimal(expected_cell["monthly_pi"]), f"{expected_cell['program']}@{expected_cell['dp_pct']}: monthly_pi mismatch"
            assert actual.piti == Decimal(expected_cell["piti"])
            assert actual.dti_back == Decimal(expected_cell["dti_back"])
            assert actual.eligible == expected_cell["eligible"]
            assert actual.blocker_reasons == expected_cell["blocker_reasons"]

        expected_verdict = fx["expected_response"]["verdict"]
        assert report.verdict.level == expected_verdict["level"]
        for expected_reason in expected_verdict["reasons"]:
            assert any(
                r.predicate_code == expected_reason["predicate_code"]
                and r.computed_value == expected_reason["computed_value"]
                for r in report.verdict.reasons
            ), f"Expected reason {expected_reason['predicate_code']} not in report.verdict.reasons"

        if "tax" in fx["expected_response"]:
            assert report.tax.qualified_loan_limit == Decimal(fx["expected_response"]["tax"]["qualified_loan_limit"])
    ```

    Edit `tests/test_property_verdict.py`:
    1. Replace the in-test cascade-based body of `test_verdict_code_citation_coverage` with the fixture-based body per Behavior list.
    2. Add `test_phase_14_requirement_coverage_meta` per Behavior list.

    DO NOT delete the cascade-level unit tests in tests/test_property_verdict.py (those still verify synthesize() at the unit level — Plan 14-04 output).
    DO NOT modify lib/property_analysis.py or lib/property_verdict.py — those are frozen at end of Plans 14-04 + 14-05.
    DO NOT use `pytest.approx`.
    DO NOT skip any test in this plan. All 3 golden + both meta-tests must PASS on first run.
  </action>
  <verify>
    <automated>pytest tests/test_property_analysis.py::test_sfh_conforming_king_county_golden tests/test_property_analysis.py::test_condo_with_hoa_seattle_golden tests/test_property_analysis.py::test_sfh_jumbo_bay_area_golden tests/test_property_verdict.py::test_verdict_code_citation_coverage tests/test_property_verdict.py::test_phase_14_requirement_coverage_meta -x</automated>
  </verify>
  <acceptance_criteria>
    - All 3 golden tests pass: `pytest tests/test_property_analysis.py::test_sfh_conforming_king_county_golden tests/test_property_analysis.py::test_condo_with_hoa_seattle_golden tests/test_property_analysis.py::test_sfh_jumbo_bay_area_golden -x` exits 0.
    - Fixture-based citation-coverage passes: `pytest tests/test_property_verdict.py::test_verdict_code_citation_coverage -x` exits 0.
    - Phase requirement coverage passes: `pytest tests/test_property_verdict.py::test_phase_14_requirement_coverage_meta -x` exits 0.
    - `grep -c 'pytest.skip' tests/test_property_analysis.py` returns 0 (all stubs flipped).
    - `grep -c 'property_analysis_fixture(' tests/test_property_analysis.py` returns at least 3.
    - `grep -c 'model_validate_json(json.dumps' tests/test_property_analysis.py` returns at least 9 (3 sub-blocks × 3 fixtures — PATTERNS.md L590 strict-mode-Decimal idiom).
    - `pytest tests/test_property_analysis.py tests/test_property_verdict.py -x` exits 0 (FULL Phase 14 test surface green).
    - `pytest -x` (full suite) exits 0 — no regression in other phases.
    - `pytest tests/test_property_analysis.py tests/test_property_verdict.py tests/test_household.py tests/test_profile.py --collect-only -q | tail -5` reports the full Phase 14 test count (target: at least 50 tests collected).
  </acceptance_criteria>
  <done>
    All 3 golden tests pass against the 3 hand-calc fixtures. Citation-coverage tightened to fixture-based (every VERDICT_* constant exercised by at least one fixture). Phase requirement-coverage meta-test passes (ANLZ-01..03 + VERD-01 all referenced in fixture metadata). Phase 14 success criterion #7 (golden-value fixtures pin every cell) is satisfied.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Fixture JSON → Pydantic model | Pydantic v2 strict mode validates all Decimal-from-string conversions; rejects float/numeric where Money/Rate expected. |
| Fixture (committed) → repository | Synthetic-only-in-CI per Phase 11 D-02 inherited; no PII; no AI attribution. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-FLOAT | Tampering | Fixture JSON Decimal fields | mitigate | All money/rate values are quoted JSON strings; tests assert this via grep-no-numeric-decimals; Pydantic strict=True catches at validate_json boundary. |
| T-14-FRED-RACE | Tampering | Golden tests' FRED reads | mitigate | Tests pass fred_mortgage_30us + fred_mortgage_15us explicitly; cache is bypassed. |
| T-14-STALE-REF | Tampering | data/reference/conforming-limits-2026.yml and fha-mip-rates.yml read transitively | mitigate | Existing predicates surface StaleReferenceWarning; this is verified to not crash any fixture-driven test. |
| T-14-REASON | Repudiation | VerdictReason coverage | mitigate | test_verdict_code_citation_coverage now asserts every VERDICT_* constant appears in at least one fixture's expected_response.verdict.reasons[].predicate_code. |
| T-14-PII | Information Disclosure | Fixture JSON | mitigate | README.md "What NOT to put here" section enforces synthetic-only policy; fixture locations use real ZIPs but synthetic addresses; no agent contact info; no real lender quotes; no Co-Authored-By markers (verified via grep). |
</threat_model>

<verification>
- `pytest tests/test_property_analysis.py tests/test_property_verdict.py tests/test_household.py tests/test_profile.py -x` exits 0 (FULL Phase 14 test surface).
- `pytest -x` (full suite) exits 0 — no regression in other phases.
- 3 fixture JSON files exist and validate as JSON.
- 3 fixture sub-blocks (listing, household, profile) each validate against their Pydantic models.
- All 3 fixtures contain source_url + zpid + fetched_at in listing (B-3 propagation).
- Condo fixture verdict.level is a single Literal value (W-1).
- `python -c "import json; from pathlib import Path; total = sum(1 for _ in Path('tests/fixtures/property_analysis').glob('*.json')); assert total == 3, f'expected 3 fixtures, found {total}'"` exits 0.
- README.md cites synthetic-only-in-CI policy + "Phase 11 D-02 inherited" phrase.
- No AI-attribution markers anywhere in fixtures or README per CLAUDE.md global rule.
</verification>

<success_criteria>
1. 3 hand-calc golden fixtures ship: sfh_conforming_king_county.json, condo_with_hoa_seattle.json, sfh_jumbo_bay_area.json — each with verbatim envelope shape per PATTERNS.md L791-839.
2. **B-3 RESOLVED:** All 3 fixture listing blocks include source_url + zpid + fetched_at; acceptance criteria assert these fields in each task.
3. **W-1 RESOLVED:** Condo fixture verdict.level pinned to exactly one of {"GO", "WATCH"}; notes field contains cascade-level derivation explanation (cascade + hand-calc substrings).
4. tests/fixtures/property_analysis/README.md cites synthetic-only-in-CI policy + capture-and-sanitize recipe.
5. 3 golden tests in tests/test_property_analysis.py flipped from pytest.skip to real assertions; all pass with exact Decimal equality on every preferred-DP cell.
6. tests/test_property_verdict.py:test_verdict_code_citation_coverage tightened to fixture-based; every VERDICT_* constant exercised.
7. tests/test_property_verdict.py:test_phase_14_requirement_coverage_meta added; every ANLZ-XX + VERD-01 referenced in fixture metadata.
8. All 4 phase requirements (ANLZ-01, ANLZ-02, ANLZ-03, VERD-01) closed at fixture + integration + unit levels.
9. Pitfall 12 (citation-coverage meta-test missing) fully mitigated — both VERDICT_* constants AND phase requirement IDs verified.
10. Phase 14 ROADMAP success criterion #7 ("Golden-value fixtures: 3 hand-calculated AnalysisReport cases pin every cell of the matrix; full suite green") satisfied.
11. `pytest -x` exits 0; full suite green at phase end.
</success_criteria>

<output>
After completion, create `.planning/phases/14-property-analysis-pipeline/14-06-SUMMARY.md` documenting:
- 3 golden fixtures shipped with verdict.level + key cell numerics pinned.
- Iteration-2 fix summary: B-3 propagation (audit fields on every listing block), W-1 (condo verdict pinned + cascade-derivation in notes).
- README.md provenance / "what NOT to put here" rules.
- Citation-coverage meta-test promoted to fixture-based.
- Total Phase 14 test count + breakdown by file.
- All 4 phase requirements closed at all 3 verification levels (unit, integration, fixture).
- Pitfall 12 fully mitigated.
- Phase 14 success criterion #7 satisfied.
- Hand-off to Phase 15: AnalysisReport schema is FROZEN; Phase 15's lib/property_report.py consumes it for markdown rendering.
</output>
