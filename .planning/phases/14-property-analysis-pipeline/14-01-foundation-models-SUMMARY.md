---
phase: 14-property-analysis-pipeline
plan: 01-foundation-models
subsystem: models
tags: [pydantic, models, household, profile, decimal, strict-mode, frozen]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Money / Rate Annotated aliases from lib/models.py (strict=True, max_digits, ge/le)"
  - phase: 04-affordability
    provides: "LocationFIPS pattern (state_fips/county_fips/county_name FIPS-code idiom) + Phase 4 Household contract name to disambiguate against"
provides:
  - "lib/household.py — Phase 14 analysis-time Household model (DISTINCT from lib.affordability.Household)"
  - "lib/profile.py — Phase 14 analysis-time Profile model + MilitaryStatus / FilingStatus Literal aliases"
  - "Frozen contract for Wave 2+ downstream plans (14-02..14-06) to import"
affects:
  - 14-02-matrix-models (consumes Household + Profile; will import affordability.Household as AffordabilityHousehold)
  - 14-03-auxiliary-blocks (TaxBlock reads Profile.filing_status + marginal_tax_rate)
  - 14-04-verdict-synthesis (reads Household.preferred_down_payment_pct for D-14-VERDICT-03)
  - 14-05-analyze-composition (analyze(listing, household, profile) entrypoint signature)
  - 14-06-golden-fixtures (golden inputs need Household + Profile shapes)

# Tech tracking
tech-stack:
  added: []  # No new libraries; reuses lib/models.Money / lib/models.Rate Annotated aliases
  patterns:
    - "Module-level Literal alias declared above the class (MilitaryStatus, FilingStatus) — mirrors PropertyType in lib/property_listing.py and TargetLoanType in lib/affordability.py"
    - "Docstring-as-disambiguation-anchor: a same-named class in a new module declares the distinction in its module + class docstrings; downstream consumers grep the docstring text to confirm which symbol they're holding"

key-files:
  created:
    - lib/household.py
    - lib/profile.py
    - tests/test_household.py
    - tests/test_profile.py
    - .planning/phases/14-property-analysis-pipeline/deferred-items.md
  modified: []

key-decisions:
  - "D-14-MODELS-01 (locked by plan): Household carries financial state only — monthly_income, monthly_obligations, fico, liquid_reserves, state_fips, county_fips, county_name, preferred_down_payment_pct."
  - "D-14-MODELS-02 (resolved by plan as Claude's Discretion): Profile carries va_eligible + first_time_buyer + military_status + filing_status + marginal_tax_rate — NOT Household. Rationale: eligibility booleans + preferences are a distinct concern from financial state."
  - "D-14-STRESS-02 default: preferred_down_payment_pct defaults to Decimal('0.20') when household.yml omits the field."
  - "OQ #1 (Household name collision) RESOLVED — docstring + downstream import-alias (`from lib.affordability import Household as AffordabilityHousehold`, applied in Plan 14-02) jointly mitigate. No code change in 14-01."
  - "RED+GREEN gate consolidation: lib/* + tests/* land in one commit per task because mypy --strict pre-commit hooks reject test files that import not-yet-existing modules. The RED phase was still proven (tests run-and-fail before the implementation lands; see Task 1 RED gate output)."

patterns-established:
  - "Phase 14 input-contract Pydantic discipline: every analysis-time input model uses strict=True + frozen=True + extra=forbid; Money/Rate aliases from lib.models; module-level Literal aliases for Literal-typed fields with >1 member."
  - "Same-class-name across modules pattern: when a Phase N domain model has a distinct meaning from a same-named class in Phase M, the new module ships a loud docstring identifying the distinction and downstream consumers use import aliasing. Codified for lib.household.Household vs lib.affordability.Household."

requirements-completed: []  # Plan 14-01 enables ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 but closes none directly. Closure happens in Plan 14-04 / 14-05.

# Metrics
duration: 6 min
completed: 2026-05-18
---

# Phase 14 Plan 01: Foundation Models Summary

**Phase 14 Wave 0 interface contracts: lib/household.py (financial state) and lib/profile.py (eligibility + preferences) Pydantic v2 models, with 22 contract tests pinning strict/frozen/extra=forbid behavior and Money/Rate boundary enforcement.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-18T16:53:23Z
- **Completed:** 2026-05-18T16:59:19Z
- **Tasks:** 3
- **Files created:** 5 (2 lib modules + 2 test modules + 1 deferred-items log)
- **Tests added:** 22 (10 in test_household.py, 12 in test_profile.py)
- **Full-suite regression:** 752 passed, 6 skipped, 1 xfailed (with the pre-existing fha_mip.py uncommitted changes deselected; see Deviations).

## Accomplishments

- **lib/household.py** ships the Phase 14 Household model (DISTINCT from Phase 4 lib.affordability.Household). 8 fields: monthly_income (Money), monthly_obligations (Money), fico (int 300..850), liquid_reserves (Money), state_fips (2-digit), county_fips (3-digit), county_name (str), preferred_down_payment_pct (Rate, default Decimal('0.20')).
- **lib/profile.py** ships the Profile model with 5 fields per D-14-MODELS-02: va_eligible (bool default False), first_time_buyer (bool default False), military_status (MilitaryStatus default "none"), filing_status (FilingStatus default "mfj"), marginal_tax_rate (Rate | None default None). Module-level Literal aliases (MilitaryStatus, FilingStatus) follow the PropertyType / TargetLoanType idiom.
- **tests/test_household.py** (10 tests) and **tests/test_profile.py** (12 tests) pin every Pydantic invariant required by PATTERNS.md L719-727: extra=forbid, strict=True float rejection, range bounds (fico, Rate ≤1), pattern enforcement (FIPS regexes, Literal members), frozen hashability, JSON round-trip with Decimal-as-string.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lib/household.py with frozen Household model** — `ddedb57` (feat)
2. **Task 2: Create lib/profile.py with frozen Profile model** — `036ff7a` (feat)
3. **Task 3: Test taxonomies + deferred-items log** — `35c9a33` (chore)

_TDD note: Task 1's tests were written first and proven RED (ModuleNotFoundError) before the lib/household.py implementation landed; the same was true for Task 2. The RED test commits could not be separately committed because mypy --strict pre-commit hooks reject test files that import not-yet-existing modules. Each Task's commit nonetheless captures the test-first artifact alongside the implementation that makes it pass._

## Field Set Shipped

### lib/household.py — Household
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| monthly_income | Money | required | aggregated gross monthly income across earners |
| monthly_obligations | Money | required | aggregated auto + student + cc + other debts |
| fico | int (300..850) | required | representative score (mid-of-3 if 3 scores) |
| liquid_reserves | Money | required | cash/cash-equivalents at close |
| state_fips | str (^\d{2}$) | required | LocationFIPS 2-digit code |
| county_fips | str (^\d{3}$) | required | LocationFIPS 3-digit code |
| county_name | str (min_length=1) | required | human-readable display |
| preferred_down_payment_pct | Rate | `Decimal("0.20")` | D-14-STRESS-02 default |

### lib/profile.py — Profile
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| va_eligible | bool | False | gates VA30 4th program row in Plan 14-02 |
| first_time_buyer | bool | False | informational for future FHA UFMIP / DPA |
| military_status | MilitaryStatus | "none" | Plan 14-02 VA funding-fee lookup |
| filing_status | FilingStatus | "mfj" | Plan 14-03 IRS Pub 936 TaxBlock |
| marginal_tax_rate | Rate \| None | None | after-tax savings estimator (Plan 14-03) |

### Module-level Literal aliases (lib/profile.py)
- `MilitaryStatus = Literal["active", "veteran", "reserve", "none"]`
- `FilingStatus = Literal["single", "mfj", "mfs", "hoh"]`

## Files Created/Modified

- `lib/household.py` (NEW) — Phase 14 Household model + module/class docstrings disambiguating from lib.affordability.Household (OQ #1 anchor)
- `lib/profile.py` (NEW) — Phase 14 Profile model + MilitaryStatus/FilingStatus aliases
- `tests/test_household.py` (NEW) — 10 contract tests
- `tests/test_profile.py` (NEW) — 12 contract tests
- `.planning/phases/14-property-analysis-pipeline/deferred-items.md` (NEW) — pre-existing-failure log

## Decisions Made

- **D-14-MODELS-02 Profile/Household split resolved per PATTERNS.md L123-165 guidance.** Profile carries eligibility + preferences; Household carries financial state. This is the Claude's Discretion item identified in 14-CONTEXT.md; the plan locked it in advance, so execution simply implemented the locked split.
- **mypy --strict / pre-commit interaction with TDD RED gates:** when adding a test file that imports a not-yet-existing module, the mypy pre-commit hook fails because it cannot resolve the import. The standard "commit RED, then commit GREEN" TDD ritual is therefore consolidated into a single per-task commit. The RED phase is still preserved as a runtime artifact (tests collected and failed before the implementation landed) but only commits after the implementation makes them pass. This is the right tradeoff for this repo's tooling configuration; documented for downstream Plan 14-02..14-06.

## Deviations from Plan

### Out-of-scope discoveries (logged, not fixed)

**1. [Pre-existing] lib/rules/fha_mip.py uncommitted modification breaks 2 citation_coverage tests**
- **Found during:** Task 3 (full-suite regression verification)
- **Issue:** `pytest -x` fails on `test_predicate_has_citation_in_docstring[fha_mip]` because the working tree has an uncommitted change to lib/rules/fha_mip.py that altered the docstring to use `"Citation (operative):"` instead of the literal `"Citation:"` the meta-test asserts.
- **Action:** Documented in `.planning/phases/14-property-analysis-pipeline/deferred-items.md`. Verified `git stash` → tests pass; `git stash pop` → tests fail. Failure is unrelated to Plan 14-01's lib/household.py + lib/profile.py changes.
- **Boundary:** The agent prompt's `<work_in_progress_note>` explicitly instructed NOT to touch lib/rules/fha_mip.py; therefore left alone.

### Plan-text inaccuracy noted (not a deviation per se)

The plan's Task 1 acceptance-criteria CLI check uses `Decimal-from-string` kwargs (e.g., `monthly_income='12000.00'`). With Money's `strict=True` annotation this raises ValidationError — strings are not Decimal instances. The implementation is correct (matches lib.models.Loan precedent); the plan's `python -c` text would need `Decimal("12000.00")` constructions to actually pass. The corresponding test (`test_clean_household_validates`) does use proper `Decimal("12000.00")` constructions and passes. No code change needed; documented here for transparency.

---

**Total deviations:** 0 auto-fixes to plan-scope work. 1 out-of-scope pre-existing failure logged.
**Impact on plan:** None — Plan 14-01 ships clean with all 22 new tests green and no regressions caused by its own changes.

## Issues Encountered

- **mypy --strict pre-commit blocks the canonical TDD RED commit** (test file imports not-yet-existing module). Workaround: combine RED+GREEN per task; preserve RED as runtime evidence via the in-session pytest run before the implementation lands. Documented in Decisions Made above.

## OQ #1 Resolution Confirmation

The Plan 14-01 objective marked OQ #1 (Household name collision with lib/affordability.py) as RESOLVED by combining:
1. **lib/household.py docstring** identifying the model as DISTINCT from lib.affordability.Household (grep verifies 2 occurrences of the anchor text — module docstring + class docstring).
2. **Plan 14-02 import-alias** (`from lib.affordability import Household as AffordabilityHousehold`) — applied downstream, not in this plan.

Verification: `grep -c 'DISTINCT from lib.affordability.Household' lib/household.py` returns 2. Downstream Plan 14-02 will land the import alias when it consumes both symbols.

## Next Phase Readiness

- **Plan 14-02 (matrix-models)** unblocked: the two input-contract symbols it needs (`lib.household.Household` + `lib.profile.Profile`) are now importable, frozen, and contract-tested.
- **Plan 14-03 (auxiliary-blocks)** unblocked: TaxBlock can now type-annotate against `Profile.filing_status` (FilingStatus Literal) and `Profile.marginal_tax_rate` (Rate | None).
- **No blockers** to Wave 2+ entry.

## Self-Check: PASSED

- [x] lib/household.py exists — verified via `ls`
- [x] lib/profile.py exists — verified via `ls`
- [x] tests/test_household.py exists, 10 tests, all pass
- [x] tests/test_profile.py exists, 12 tests, all pass
- [x] All 3 task commits present in `git log --oneline`:
  - `ddedb57` feat(14-01): add Household model with contract tests
  - `036ff7a` feat(14-01): add Profile model with contract tests
  - `35c9a33` chore(14-01): log Plan 14-01 deferred items from execution

---
*Phase: 14-property-analysis-pipeline*
*Plan: 01-foundation-models*
*Completed: 2026-05-18*
