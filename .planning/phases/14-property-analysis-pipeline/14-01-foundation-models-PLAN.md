---
phase: 14
plan: 01
plan_id: 14-01
slug: foundation-models
type: execute
wave: 1
depends_on: []
files_modified:
  - lib/household.py
  - lib/profile.py
  - tests/test_household.py
  - tests/test_profile.py
autonomous: true
requirements:
  - ANLZ-01
  - ANLZ-02
  - VERD-01
nyquist_compliant: true
tags:
  - pydantic
  - models
  - household
  - profile

must_haves:
  truths:
    - "lib/household.py defines a frozen/strict/extra=forbid Pydantic Household model carrying monthly_income, monthly_obligations, fico, liquid_reserves, state_fips, county_fips, county_name, preferred_down_payment_pct."
    - "lib/profile.py defines a frozen/strict/extra=forbid Pydantic Profile model carrying va_eligible, first_time_buyer, military_status, filing_status, marginal_tax_rate."
    - "Household.preferred_down_payment_pct defaults to Decimal('0.20') per D-14-STRESS-02."
    - "Profile.va_eligible defaults to False; military_status defaults to 'none'; filing_status defaults to 'mfj'."
    - "Both models reject float for Decimal-typed fields (strict=True) and reject unknown fields (extra='forbid')."
  artifacts:
    - path: "lib/household.py"
      provides: "Household analysis-time financial-state model"
      contains: "class Household(BaseModel)"
    - path: "lib/profile.py"
      provides: "Profile analysis-time preferences + eligibility model"
      contains: "class Profile(BaseModel)"
    - path: "tests/test_household.py"
      provides: "Household model contract tests"
      contains: "def test_extra_forbid"
    - path: "tests/test_profile.py"
      provides: "Profile model contract tests"
      contains: "def test_va_eligible_default"
  key_links:
    - from: "lib/household.py"
      to: "lib/models.py"
      via: "from lib.models import Money, Rate"
      pattern: "from lib\\.models import Money, Rate"
    - from: "lib/profile.py"
      to: "lib/models.py"
      via: "from lib.models import Rate"
      pattern: "from lib\\.models import .*Rate"
---

<objective>
Ship the two new Pydantic v2 input models that downstream Phase 14 plans consume: `Household` (analysis-time financial state) and `Profile` (analysis-time eligibility + preferences). Both models follow project-wide strict/frozen/extra=forbid conventions and use the existing `Money`/`Rate` Annotated aliases from `lib/models.py`.

Per D-14-MODELS-02 Claude's Discretion resolution (see 14-RESEARCH.md L416-478): land `va_eligible`, `first_time_buyer`, `military_status`, `filing_status`, `marginal_tax_rate` on a SEPARATE `Profile` model, NOT on Household. Rationale: `lib.affordability.Household` is a Phase 4 frozen contract; re-using the name is acceptable per PATTERNS.md L119 but the FIELD SETS must be cleanly separated. Household = financial state; Profile = analysis-time eligibility + preferences.

Purpose: Phase 14's `analyze(listing, household, profile)` entrypoint cannot be written without these two contracts frozen first. They are the "Wave 0 interface contracts" of Phase 14.

Output: 2 lib/ models + 2 test files (Household contract tests + Profile contract tests). Every Pydantic invariant from PATTERNS.md L725-733 is exercised.

---

## Open Question Resolutions (Iteration 2)

**OQ #1 (Household name collision) — RESOLVED.** PATTERNS.md L105-108 + Plan 14-02 import-aliasing (`from lib.affordability import Household as AffordabilityHousehold`) fully disambiguate. Phase 14's `lib.household.Household` is a DISTINCT model from `lib.affordability.Household` (Phase 4 frozen contract). Task 1 docstring loudly cites the distinction; the affordability symbol is renamed at import time so no consumer ever has shadowed names in scope. **No code change required in Plan 14-01.**
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md
@.planning/phases/14-property-analysis-pipeline/14-RESEARCH.md
@.planning/phases/14-property-analysis-pipeline/14-PATTERNS.md
@CLAUDE.md
@lib/models.py
@lib/affordability.py
@lib/property_listing.py
@tests/test_property_listing.py
@tests/test_models.py

<interfaces>
<!-- From lib/models.py L23-33 — the Money/Rate Annotated aliases Phase 14 uses. -->
<!-- Both have strict=True, max_digits=14/7, decimal_places=2/6; Money has ge=0; Rate has ge=0, le=1. -->

```python
# lib/models.py L23-33
Money = Annotated[
    Decimal,
    Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0")),
]
Rate = Annotated[
    Decimal,
    Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1")),
]
```

<!-- From lib/affordability.py L339-348 — LocationFIPS pattern (the closest 1:1 sibling for state_fips/county_fips/county_name fields on the new Household). -->

```python
class LocationFIPS(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
    county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    county_name: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    zip: str | None = None
```

<!-- From lib/property_listing.py L25 — module-top Literal-alias idiom that Profile mirrors for MilitaryStatus + FilingStatus. -->

```python
PropertyType = Literal["SFH", "condo", "townhouse", "multifamily-2-4"]
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create lib/household.py with frozen Household model</name>
  <files>lib/household.py</files>
  <read_first>
    - lib/models.py (full — Money, Rate alias definitions L23-33 + Loan class L39-91 for ConfigDict pattern)
    - lib/affordability.py L339-348 (LocationFIPS — closest analog with state_fips/county_fips/county_name pattern fields)
    - lib/affordability.py L407-433 (Phase 4 Household — DO NOT modify or shadow; new file is a DISTINCT model)
    - lib/property_listing.py L1-30 (module-header convention: from __future__ import annotations + Literal aliases at top)
    - .planning/phases/14-property-analysis-pipeline/14-CONTEXT.md (D-14-MODELS-01 + D-14-STRESS-02 locked decisions)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L33-119 (Household pattern with verbatim field set)
    - CLAUDE.md "Money discipline" section
  </read_first>
  <behavior>
    - Test 1: `Household(monthly_income=Decimal("12000.00"), monthly_obligations=Decimal("400.00"), fico=740, liquid_reserves=Decimal("50000.00"), state_fips="53", county_fips="033", county_name="King")` validates with `preferred_down_payment_pct == Decimal("0.20")` default.
    - Test 2: `Household(...float price...)` raises pydantic ValidationError (strict=True rejects float).
    - Test 3: `Household(..., unknown_field="x")` raises ValidationError (extra="forbid").
    - Test 4: `Household(..., fico=299)` raises ValidationError; `fico=851` raises ValidationError (Field(ge=300, le=850)).
    - Test 5: `Household(..., state_fips="5")` raises ValidationError; `state_fips="ABC"` raises ValidationError (pattern enforcement).
    - Test 6: `hash(household_instance) is not None` (frozen=True provides hashability).
    - Test 7: `Household.model_validate_json(h.model_dump_json()) == h` (round-trip equality).
    - Test 8: JSON output contains `'"monthly_income":"12000.00"'` quoted Decimal-as-string (CLAUDE.md money discipline).
  </behavior>
  <action>
    Create `lib/household.py` mirroring lib/property_listing.py header style and lib/affordability.py:LocationFIPS field idioms.

    Required module structure:
    1. `from __future__ import annotations` as first line.
    2. Imports: `from decimal import Decimal`; `from pydantic import BaseModel, ConfigDict, Field`; `from lib.models import Money, Rate  # noqa: TC001  # Pydantic resolves field annotations at runtime` (verbatim noqa comment per PATTERNS.md L52).
    3. Single `class Household(BaseModel)` with `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`.
    4. Docstring naming D-14-MODELS-01 + a one-line note "DISTINCT from lib.affordability.Household (Phase 4 frozen contract)" per PATTERNS.md L105-108. This docstring is the OQ #1 disambiguation anchor — consumers grep this string to confirm they're holding the Phase 14 model.

    Required fields (per PATTERNS.md L104-117 and CONTEXT D-14-MODELS-01 + D-14-STRESS-02):
    - `monthly_income: Money`
    - `monthly_obligations: Money` (aggregated auto + student + cc + other)
    - `fico: int = Field(ge=300, le=850)`
    - `liquid_reserves: Money`
    - `state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")`
    - `county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")`
    - `county_name: str = Field(min_length=1)`
    - `preferred_down_payment_pct: Rate = Decimal("0.20")` per D-14-STRESS-02. Include `Field(description=...)` block citing D-14-STRESS-02 + default rationale per PATTERNS.md L84-99 idiom.

    DO NOT add escrow fields, applicants, or VA inputs — those live elsewhere (escrow comes from PropertyListing; VA inputs come from Profile).
    DO NOT add a `va_eligible` field — that lives on Profile per D-14-MODELS-02 resolution.
    DO NOT add `va_region`, `va_family_size`, or `va_actual_residual_income` fields — Plan 14-02 (B-2 fix) synthesizes these deterministically inside `_build_program_result` rather than carrying them on Household. Rationale: keeps Household focused on cross-program financial state; VA-specific residual inputs are loud sentinels (synthesized + tagged with `VA-RESIDUAL-SYNTHESIZED-V1` reason).
    DO NOT reformat the Phase 4 Household; this is a NEW module with a DISTINCT but same-named class.
  </action>
  <verify>
    <automated>pytest tests/test_household.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `lib/household.py` exists at the absolute path and contains `class Household(BaseModel):` and `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`.
    - File contains all 8 required fields with exact names: `monthly_income`, `monthly_obligations`, `fico`, `liquid_reserves`, `state_fips`, `county_fips`, `county_name`, `preferred_down_payment_pct`.
    - `grep -n 'preferred_down_payment_pct: Rate = Decimal("0.20")' lib/household.py` returns a match.
    - `grep -c 'DISTINCT from lib.affordability.Household' lib/household.py` returns at least 1 (OQ #1 disambiguation anchor).
    - `python -c "from lib.household import Household; h = Household(monthly_income='12000.00', monthly_obligations='400.00', fico=740, liquid_reserves='50000.00', state_fips='53', county_fips='033', county_name='King'); assert h.preferred_down_payment_pct == __import__('decimal').Decimal('0.20')"` exits 0.
    - `python -c "from lib.household import Household; import pytest; pytest.raises(Exception, lambda: Household(monthly_income=12000.0, monthly_obligations='0', fico=740, liquid_reserves='0', state_fips='53', county_fips='033', county_name='King'))"` exits 0 (float rejection).
    - `grep -c 'from __future__ import annotations' lib/household.py` returns 1.
    - `grep -c 'noqa: TC001' lib/household.py` returns 1 (Money/Rate import idiom).
  </acceptance_criteria>
  <done>
    `pytest tests/test_household.py -x` exits 0; all 8 behavior tests pass; Household model is importable and matches the field set above.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create lib/profile.py with frozen Profile model</name>
  <files>lib/profile.py</files>
  <read_first>
    - lib/affordability.py L393-405 (VAInputs — closest analog for "eligibility-gating Pydantic block")
    - lib/affordability.py L239 (TargetLoanType Literal-alias-at-module-top precedent)
    - lib/property_listing.py L25-26 (PropertyType Literal alias precedent for MilitaryStatus + FilingStatus aliases)
    - lib/models.py L23-33 (Rate alias; Profile uses Rate for marginal_tax_rate)
    - .planning/phases/14-property-analysis-pipeline/14-CONTEXT.md (D-14-MODELS-02 Claude's Discretion: Profile carries va_eligible + first_time_buyer + military_status + filing_status + marginal_tax_rate)
    - .planning/phases/14-property-analysis-pipeline/14-RESEARCH.md L458-477 (recommended Profile shape)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L123-165 (Profile pattern with verbatim aliases)
  </read_first>
  <behavior>
    - Test 1: `Profile()` (all defaults) validates with `va_eligible == False`, `first_time_buyer == False`, `military_status == "none"`, `filing_status == "mfj"`, `marginal_tax_rate is None`.
    - Test 2: `Profile(va_eligible=True, military_status="veteran")` validates with the overrides intact.
    - Test 3: `Profile(military_status="invalid")` raises ValidationError (Literal enforcement).
    - Test 4: `Profile(filing_status="invalid")` raises ValidationError.
    - Test 5: `Profile(unknown_field="x")` raises ValidationError (extra="forbid").
    - Test 6: `Profile(marginal_tax_rate=Decimal("0.32"))` validates; `marginal_tax_rate=Decimal("1.5")` raises (Rate le=1).
    - Test 7: `hash(profile_instance) is not None` (frozen=True hashability).
    - Test 8: Round-trip JSON equality (model_validate_json(model_dump_json()) == original).
  </behavior>
  <action>
    Create `lib/profile.py` mirroring lib/property_listing.py module style and lib/affordability.py:VAInputs idioms.

    Required module structure:
    1. `from __future__ import annotations` as first line.
    2. Imports: `from decimal import Decimal`; `from typing import Literal`; `from pydantic import BaseModel, ConfigDict, Field`; `from lib.models import Rate  # noqa: TC001  # Pydantic resolves field annotations at runtime`.
    3. Module-level Literal aliases per PATTERNS.md L147-149 idiom:
       - `MilitaryStatus = Literal["active", "veteran", "reserve", "none"]`
       - `FilingStatus = Literal["single", "mfj", "mfs", "hoh"]`
    4. Single `class Profile(BaseModel)` with `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`.
    5. Docstring citing D-14-MODELS-02 + the rationale ("split from Household because these are user preferences and program-eligibility booleans, NOT financial state" per PATTERNS.md L153).

    Required fields (per PATTERNS.md L156-161 and CONTEXT D-14-MODELS-02):
    - `va_eligible: bool = False`
    - `first_time_buyer: bool = False`
    - `military_status: MilitaryStatus = "none"`
    - `filing_status: FilingStatus = "mfj"`
    - `marginal_tax_rate: Rate | None = None` (optional; only consumed by Phase 14 TaxBlock if non-None)

    DO NOT add display_money_format / display_rate_format fields — those are deferred to Phase 15 (formatter concern, not analysis concern; RESEARCH.md L475-477 mentions them but they aren't consumed by analyze()).
    DO NOT add IRS Pub 936 grandfathering booleans — Pitfall 11 confirms v1.1 scope is purely post-2017 acquisition; defaults of qualified_loan_limit() suffice.
  </action>
  <verify>
    <automated>pytest tests/test_profile.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `lib/profile.py` exists at the absolute path with `class Profile(BaseModel):` and `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`.
    - File contains module-top `MilitaryStatus = Literal[...]` and `FilingStatus = Literal[...]` aliases (grep returns 1 match each).
    - File contains all 5 required fields with exact names: `va_eligible`, `first_time_buyer`, `military_status`, `filing_status`, `marginal_tax_rate`.
    - `grep -n 'va_eligible: bool = False' lib/profile.py` returns a match.
    - `grep -n 'military_status: MilitaryStatus = "none"' lib/profile.py` returns a match.
    - `grep -n 'filing_status: FilingStatus = "mfj"' lib/profile.py` returns a match.
    - `python -c "from lib.profile import Profile; p = Profile(); assert p.va_eligible is False and p.military_status == 'none' and p.filing_status == 'mfj' and p.marginal_tax_rate is None"` exits 0.
    - `grep -c 'from __future__ import annotations' lib/profile.py` returns 1.
  </acceptance_criteria>
  <done>
    `pytest tests/test_profile.py -x` exits 0; all 8 behavior tests pass; Profile model is importable with the field set above.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create tests/test_household.py and tests/test_profile.py with model contract suites</name>
  <files>tests/test_household.py, tests/test_profile.py</files>
  <read_first>
    - tests/test_property_listing.py L1-191 (full — model contract test taxonomy: must-haves, float rejection, extra-forbid, frozen-hashable, round-trip)
    - tests/test_models.py L1-130 (Loan/Money/Rate boundary tests)
    - lib/household.py (the file created by Task 1)
    - lib/profile.py (the file created by Task 2)
    - .planning/phases/14-property-analysis-pipeline/14-PATTERNS.md L668-728 (required test taxonomy for each new model)
    - CLAUDE.md "Testing" section ("Exact Decimal equality, never assertAlmostEqual for money")
  </read_first>
  <behavior>
    tests/test_household.py contains at least these named tests (each must independently call Household construction and assert behavior):
    - `test_clean_household_validates` — minimum-required-fields-only construction succeeds with preferred_down_payment_pct defaulting to Decimal("0.20").
    - `test_extra_forbid` — `Household(..., unknown_field="x")` raises pydantic.ValidationError.
    - `test_rejects_float_monthly_income_strict_true` — `Household(monthly_income=12000.0, ...)` raises ValidationError.
    - `test_fico_range_rejects_below_300_and_above_850` — fico=299 raises; fico=851 raises.
    - `test_state_fips_pattern_enforced` — state_fips="5" raises; state_fips="ABC" raises.
    - `test_county_fips_pattern_enforced` — county_fips="33" raises (too short); county_fips="ABCD" raises.
    - `test_frozen_household_is_hashable` — `hash(h) is not None`; `{h} == {h}`.
    - `test_preferred_dp_default_decimal_0_20` — explicit default check: omitted field equals Decimal("0.20").
    - `test_preferred_dp_rate_ge_0_le_1` — preferred_down_payment_pct=Decimal("1.5") raises.
    - `test_round_trip_serialization_money_as_string` — `Household.model_validate_json(h.model_dump_json()) == h`; assert `'"monthly_income":"12000.00"'` substring appears in JSON.

    tests/test_profile.py contains at least these named tests:
    - `test_va_eligible_default` — `Profile().va_eligible is False`.
    - `test_military_status_default_none` — `Profile().military_status == "none"`.
    - `test_filing_status_default_mfj` — `Profile().filing_status == "mfj"`.
    - `test_marginal_tax_rate_optional_default_none` — `Profile().marginal_tax_rate is None`.
    - `test_invalid_military_status_rejected` — `Profile(military_status="invalid")` raises.
    - `test_invalid_filing_status_rejected` — `Profile(filing_status="invalid")` raises.
    - `test_extra_forbid` — `Profile(unknown_field="x")` raises.
    - `test_marginal_tax_rate_range` — `Profile(marginal_tax_rate=Decimal("1.5"))` raises (Rate le=1).
    - `test_frozen_profile_is_hashable` — `hash(p) is not None`.
    - `test_round_trip_serialization` — `Profile.model_validate_json(p.model_dump_json()) == p`.
  </behavior>
  <action>
    Create both test files following the verbatim style of tests/test_property_listing.py.

    Required for tests/test_household.py:
    1. Module docstring naming Phase 14 + the requirements covered (model contract for Household).
    2. `from __future__ import annotations` first line.
    3. Imports: `pytest`, `Decimal`, `ValidationError` from pydantic, `Household` from `lib.household`.
    4. Module-private `_make_clean_household_kwargs()` helper that returns a dict with all required fields populated (monthly_income="12000.00", monthly_obligations="400.00", fico=740, liquid_reserves="50000.00", state_fips="53", county_fips="033", county_name="King") — mirror `_valid_applicant_kwargs` from tests/test_affordability.py L136.
    5. Each test exactly named per the Behavior list above; each test follows the `pytest.raises(ValidationError)` idiom for negative cases per tests/test_property_listing.py L48-191.
    6. Use `Decimal("...")` (string construction) for every Decimal literal — CLAUDE.md money discipline.

    Required for tests/test_profile.py:
    1. Same module-header style.
    2. Imports `Profile`, `MilitaryStatus`, `FilingStatus` from `lib.profile` (verify aliases are importable).
    3. Each test exactly named per the Behavior list above.

    DO NOT use `assertAlmostEqual`, `pytest.approx`, or any fuzzy comparator — exact `==` for every Decimal assertion.
    DO NOT import `analyze` or `lib.property_analysis` here — those don't exist yet (Wave 2+) and these tests must be runnable standalone.
  </action>
  <verify>
    <automated>pytest tests/test_household.py tests/test_profile.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `tests/test_household.py` exists; `grep -c '^def test_' tests/test_household.py` returns at least 10.
    - `tests/test_profile.py` exists; `grep -c '^def test_' tests/test_profile.py` returns at least 10.
    - `grep -n 'def test_extra_forbid' tests/test_household.py` matches.
    - `grep -n 'def test_va_eligible_default' tests/test_profile.py` matches.
    - `grep -n 'def test_preferred_dp_default_decimal_0_20' tests/test_household.py` matches.
    - `grep -n 'def test_rejects_float_monthly_income_strict_true' tests/test_household.py` matches.
    - `pytest tests/test_household.py tests/test_profile.py -x` exits 0.
    - `pytest tests/test_household.py tests/test_profile.py --collect-only -q | tail -5` reports at least 20 tests collected total.
    - `grep -E 'assertAlmostEqual|pytest\.approx' tests/test_household.py tests/test_profile.py | grep -v '^#' | wc -l` returns 0 (no fuzzy comparators).
  </acceptance_criteria>
  <done>
    `pytest tests/test_household.py tests/test_profile.py -x` exits 0; Household + Profile contracts are fully test-pinned and ready for downstream consumption by Plans 14-02..14-06.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User config → Pydantic model construction | `config/household.yml` / `config/profile.yml` values (User Layer per Data Contract) cross into the System Layer via Household/Profile model construction. strict=True + extra="forbid" is the validation seam. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-FLOAT | Tampering | Household.monthly_income, monthly_obligations, liquid_reserves; Profile.marginal_tax_rate | mitigate | Money/Rate aliases have `strict=True`; tests in this plan verify ValidationError on float input (`test_rejects_float_monthly_income_strict_true`). |
| T-14-FRED-RACE | Tampering | n/a in this plan | accept | This plan does not touch the FRED cache; mitigation lives in Plan 14-05. |
| T-14-STALE-REF | Tampering | n/a in this plan | accept | This plan does not read reference YAMLs; mitigation lives in Plans 14-02 + 14-03. |
| T-14-REASON | Repudiation | n/a in this plan | accept | This plan does not produce VerdictReasons; mitigation lives in Plan 14-04. |
| T-14-PII | Information Disclosure | tests/test_household.py, tests/test_profile.py | mitigate | Tests use synthetic fixed values (income "12000.00", state_fips "53"); no real user data referenced. |
</threat_model>

<verification>
- All tests in tests/test_household.py and tests/test_profile.py pass.
- Both lib/household.py and lib/profile.py importable via `python -c "from lib.household import Household; from lib.profile import Profile"`.
- No regression in existing test suite: `pytest -x` exits 0 (only NEW files added; no modifications to existing lib/* or tests/*).
- Pre-commit hook does not flag lib/household.py or lib/profile.py for User-Layer policy (these are System Layer, not config/*).
</verification>

<success_criteria>
1. `lib/household.py` ships the Household model with the exact field set in PATTERNS.md L104-117.
2. `lib/profile.py` ships the Profile model with the exact field set in PATTERNS.md L156-161.
3. `tests/test_household.py` and `tests/test_profile.py` each ship ≥ 10 tests covering the full taxonomy from PATTERNS.md L719-727.
4. `pytest tests/test_household.py tests/test_profile.py -x` exits 0.
5. `pytest -x` (full suite) exits 0 (no regression).
6. Open Question #1 (Household name collision) marked RESOLVED in objective; docstring + Plan 14-02 import alias jointly mitigate (no code change in 14-01).
</success_criteria>

<output>
After completion, create `.planning/phases/14-property-analysis-pipeline/14-01-SUMMARY.md` documenting:
- Field set shipped on Household (exact list with types + defaults).
- Field set shipped on Profile (exact list with types + defaults).
- D-14-MODELS-02 resolution (Profile carries eligibility/preferences, NOT Household).
- Test count per file + any deviations from the planned behavior list.
- Files consumed by downstream plans: lib/household.py, lib/profile.py.
- Note: Open Question #1 (Household name collision) RESOLVED — docstring + Plan 14-02 `Household as AffordabilityHousehold` import alias jointly mitigate; no code change in this plan.
</output>
