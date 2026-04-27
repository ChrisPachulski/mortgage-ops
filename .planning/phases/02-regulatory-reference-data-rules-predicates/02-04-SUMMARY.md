---
phase: 02-regulatory-reference-data-rules-predicates
plan: 04
subsystem: rules-reference-data
tags: [usda, sfh-glp, 7-cfr-part-3555, irs-pub-936, irc-163h3, tcja, decimal-discipline, predicate-template, frozen-pydantic, locked-decisions, two-boolean-grace-period]

# Dependency graph
requires:
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 01
    provides: lib/rules/_loader.py (load_reference + StaleReferenceWarning + MissingReferenceFieldError), lib/rules/types.py (County), tests/test_rules/test_citation_coverage.py (RUL-12/RUL-13 meta-test), tests/test_reference/test_schema.py (REF-09 meta-test), per-predicate fixture convention, three-string docstring contract
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 02
    provides: MIPResult Pydantic frozen-strict-extra=forbid pattern (USDAEligibilityResult mirrors), notes-block-documents-stale-warning idiom
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 03
    provides: ResidualIncomeResult Pydantic shape (status + bound dollar fields + STABLE citation string) — informs USDAEligibilityResult shape; public-helper-alongside-main-function idiom (we did NOT export a public helper this plan since RUL-08 evaluate is single-shot); flat predicate (no helper) idiom for RUL-11
  - phase: 01-foundations-money-discipline
    provides: lib.money.quantize_cents (ROUND_HALF_UP, 2 places, end-of-period only)
provides:
  - REF-06 — data/reference/usda-income-limits.yml (USDA SFH GLP per 7 CFR Part 3555 effective 2025-10-01: default 1-4=$119,850, default 5-8=$158,250, per_extra_member_pct=0.08, San Francisco override 211800/279600, upfront fee 0.0100, annual fee 0.0035)
  - REF-07 — data/reference/irs-pub936.yml (IRS Pub 936 + IRC §163(h)(3) effective 2025-01-01: post-2017 caps 750k single/MFJ/HoH + 375k MFS, pre-2017 grandfathered caps 1M single/MFJ/HoH + 500k MFS, grandfather cutoff 2017-12-15, TCJA binding-contract grace period contract_signed_before 2017-12-15 + close_before 2018-04-01)
  - RUL-08 — lib/rules/usda.py with evaluate(household_income, household_size, county, loan_amount) -> USDAEligibilityResult; helper _income_limit_for(ref, county, household_size); LOCKED DECISION D-PHASE2-Q5 silent county fallback documented inline
  - RUL-11 — lib/rules/irs_pub936.py with qualified_loan_limit(filing_status, has_grandfathered_debt, binding_contract_signed_before_2017_12_15, binding_contract_closed_before_2018_04_01) -> Decimal; FilingStatus Literal alias; LOCKED DECISION two-boolean grace period encoding (RESEARCH.md line 912) documented inline; OUT OF SCOPE points deductibility documented
  - USDAEligibilityResult Pydantic v2 frozen-strict-extra=forbid model (income_eligible + applicable_income_limit + guarantee_fee_upfront + guarantee_fee_annual)
  - 4 USDA fixtures (income-eligible at boundary, income-over-limit, family-7 in 5-8 band, San Francisco county override) + 4 IRS Pub 936 fixtures (post-2017 single, pre-2017 grandfathered single, post-2017 MFS half-cap, binding-contract grace BOTH-flags-True)
  - Cross-predicate-asymmetry pattern: RUL-01 raises MissingCountyDataError on missing county; RUL-08 silently uses default — both correct for their respective regulatory contexts
affects: [02-05-pmi-fannie-freddie, 02-06-atr-qm-reg-z, 02-07-citation-coverage-audit, 04-affordability, 07-apr-after-tax-cost]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-predicate-asymmetry idiom: when one predicate raises on missing data and another silently falls back, BOTH behaviors can be correct. The disambiguator is the lookup-direction question — RUL-01 asks 'is this county high-cost?' (silent fallback would misclassify), RUL-08 asks 'what is this county's limit?' (the default IS the answer per USDA published policy). Document the asymmetry inline in BOTH predicate docstrings so future readers do not 'fix' it."
    - "Two-boolean encoding for date-range regulatory tests: when a regulatory grace period requires multiple date conditions (TCJA binding-contract grace = signed-before AND closed-before), encode as separate boolean flags in the predicate signature rather than synthesizing a single date input. Caller is responsible for evaluating dates against the regulatory cutoffs. Predicate body uses simple AND-semantics; never does calendar arithmetic."
    - "Plain-Decimal-return for stateless table-lookup predicates: when a predicate is a pure lookup (filing_status -> cap), return Decimal directly rather than a structured Pydantic result. Frozen Pydantic results are reserved for predicates that compute multiple values (USDAEligibilityResult bundles eligibility + fees + applied limit; FHA MIPResult bundles UFMIP + annual + termination). RUL-11's plain Decimal return mirrors the FilingStatus -> cap contract."
    - "Reference YAML 'effective' date-vs-real-clock variance is documented loud-warning behavior: REF-07 was planned to be fresh (2025-01-01 < 12mo from execution) but real today=2026-04-26 makes it 481 days old, so StaleReferenceWarning fires. This is CORRECT — same loud-warning pattern as REF-03 (FHA MIP) / REF-04 / REF-05 (VA). Calendar drift between plan time and execution time naturally surfaces stale data; loader's behavior is right."

key-files:
  created:
    - data/reference/usda-income-limits.yml (REF-06 — USDA SFH GLP per 7 CFR Part 3555)
    - data/reference/irs-pub936.yml (REF-07 — IRS Pub 936 + IRC §163(h)(3))
    - lib/rules/usda.py (RUL-08 — evaluate + USDAEligibilityResult + _income_limit_for helper)
    - lib/rules/irs_pub936.py (RUL-11 — qualified_loan_limit + FilingStatus Literal)
    - tests/test_rules/test_usda.py (8 hand-calc tests)
    - tests/test_rules/test_irs_pub936.py (10 hand-calc tests)
    - tests/fixtures/rules/usda_income_eligible_default_county.json
    - tests/fixtures/rules/usda_income_over_limit_default_county.json
    - tests/fixtures/rules/usda_family_seven_extra_member_uplift.json
    - tests/fixtures/rules/usda_county_override_san_francisco.json
    - tests/fixtures/rules/irs_pub936_post_2017_single_at_cap.json
    - tests/fixtures/rules/irs_pub936_grandfathered_pre_2017_single.json
    - tests/fixtures/rules/irs_pub936_post_2017_mfs_half_cap.json
    - tests/fixtures/rules/irs_pub936_binding_contract_grace_period.json
  modified: []

key-decisions:
  - "RUL-08 silent-county-fallback per D-PHASE2-Q5: when county is NOT in REF-06's by_county overrides, evaluate() falls back to default income limits silently — does NOT raise MissingCountyDataError. This is correct USDA semantics per their published policy ('default applies unless an override is published'). Documented inline in usda.py module docstring + the helper docstring + pinned by test_unlisted_county_silently_uses_default_per_locked_decision. Cross-predicate-asymmetry with RUL-01 (which DOES raise) is intentional and correct — different regulatory lookup directions."
  - "RUL-11 grace-period-as-two-booleans per RESEARCH.md line 912: TCJA binding-contract grace period requires BOTH dates (signed before 2017-12-15 AND closed before 2018-04-01); a single origination_date cannot capture this. Predicate signature has two booleans (binding_contract_signed_before_2017_12_15, binding_contract_closed_before_2018_04_01); body uses AND-semantics. Predicate does NOT do calendar arithmetic — caller derives the booleans from contract / closing dates. Locked decision documented inline + pinned by test_binding_contract_grace_period_treated_as_grandfathered + symmetric AND-semantics pins (only_signed_flag_does_not_qualify, only_closed_flag_does_not_qualify)."
  - "RUL-11 returns plain Decimal (no Pydantic result wrapper). Mirrors FilingStatus -> cap contract; structured Pydantic results are reserved for predicates that return multiple values (USDAEligibilityResult bundles 4 fields). This is per RESEARCH.md spec line 906."
  - "MFS half-cap encoded directly in REF-07 YAML (375000 / 500000), NOT computed via /2 in code. Rationale: future tax-law changes that break the symmetry (e.g., MFS gets a non-half cap) can be expressed in YAML alone with no code change. Same convention reusable for any 'half of X' cap."
  - "FilingStatus Literal scoped to lib/rules/irs_pub936.py (NOT promoted to lib/rules/types.py). Rationale: only this predicate consumes FilingStatus; promotion is premature until a second consumer appears (Phase 7 APR after-tax cost may need it; if so, plan 02-06 / 02-07 / Phase 7 promotes then). Mirrors VAFundingFeePurpose's scoping in 02-03."
  - "USDAEligibilityResult ships with `Field(strict=True, ge=Decimal('0'))` constraints on the three Decimal fields. Mirrors lib/models.py Money pattern. Bool field income_eligible is unconstrained (bool needs none). Reusable shape for any predicate returning eligibility flag + applied threshold + computed dollar fees."
  - "REF-07 effective: 2025-01-01 was planned as 'fresh, no stale warning' but with execution date 2026-04-26 it lands 481 days old → StaleReferenceWarning fires. This is CORRECT loud behavior (same pattern as REF-03 / 04 / 05). Documented in REF-07 notes block. NOT a deviation — the loader's threshold is fixed at 12 months and calendar drift is real."
  - "USDA county override list ships with ONE entry (San Francisco only). Plan called this out explicitly as 'subset policy per RESEARCH.md Pitfall 10 + D-PHASE2-Q5: ship San Francisco as the canonical high-cost USDA-eligible county override; future YAML edits add more counties without code changes.' Future plans / annual refresh will extend without code change."

patterns-established:
  - "Cross-predicate-asymmetry pattern: when one predicate raises on missing data (RUL-01) and another silently falls back (RUL-08), document the asymmetry's regulatory-context disambiguator inline in BOTH predicate docstrings. Future predicates encountering similar missing-data choices should consult this paired example."
  - "Two-boolean encoding for date-range regulatory tests: rather than passing a single date input that requires the predicate to do calendar arithmetic, use TWO boolean parameters when the regulatory rule requires AND-semantics on multiple date conditions. Caller takes the calendar-arithmetic responsibility; predicate body uses simple AND. Reusable for ANY future date-range grace period (HPA pre-1999 origination, Reg Z pre-effective-date, etc.)."
  - "Plain-Decimal vs Pydantic-result return: stateless lookup predicates (filing_status -> cap) return plain Decimal; predicates that compute multiple values (USDAEligibilityResult, MIPResult, ResidualIncomeResult) return frozen Pydantic. Choice criterion: 'does the predicate return >1 conceptually independent value?'"
  - "MFS-as-half-of-X encoded in YAML, not derived in code: tax-law-style 'half cap for MFS' is encoded directly in REF-07 (375000, 500000). Reusable for any 'X for status A, X/2 for status B' regulatory rule where the symmetry could break in a future amendment."

requirements-completed: [REF-06, REF-07, RUL-08, RUL-11]

# Metrics
duration: 5min
completed: 2026-04-27
---

# Phase 2 Plan 04: USDA + IRS Pub 936 Summary

**REF-06 (USDA SFH GLP per 7 CFR Part 3555) + REF-07 (IRS Pub 936 + IRC §163(h)(3)) + RUL-08 (usda.evaluate predicate with locked silent-county-fallback) + RUL-11 (irs_pub936.qualified_loan_limit predicate with two-boolean TCJA binding-contract grace-period encoding). Last plan in Wave 2 — closes the FHA/VA/USDA/IRS quartet.**

## Performance

- **Duration:** ~5 min wall time
- **Started:** 2026-04-27T03:44:41Z
- **Completed:** 2026-04-27T03:49:50Z
- **Tasks:** 2
- **Files created:** 14 (2 YAMLs + 2 predicates + 2 test files + 8 fixtures)
- **Files modified:** 0 — this plan adds new artifacts only; no cross-plan stub resolution this time (USDA was already a flag-only return in 02-01's loan_type.classify, and IRS Pub 936 has no loan_type integration since it's not a loan-program classifier)

## Accomplishments

- **4 requirements landed and verified:** REF-06 (USDA income limits), REF-07 (IRS Pub 936 caps), RUL-08 (usda.evaluate), RUL-11 (irs_pub936.qualified_loan_limit). Phase 2 reaches **18/22 requirements** (REF-01..07 + RUL-01, RUL-04, RUL-06, RUL-07, RUL-08, RUL-11, RUL-12, RUL-13, REF-08, REF-09).
- **USDA published anchors pinned:** default 1-4=$119,850; default 5-8=$158,250; per_extra_member_pct=0.08; San Francisco override 211800/279600; upfront fee 0.0100; annual fee 0.0035.
- **IRS Pub 936 published anchors pinned:** post-2017 (750k single/MFJ/HoH, 375k MFS); pre-2017 grandfathered (1M single/MFJ/HoH, 500k MFS); grandfather cutoff 2017-12-15; TCJA binding-contract grace period (signed before 2017-12-15 + closed before 2018-04-01).
- **TWO LOCKED DECISIONS preserved end-to-end:**
  - **D-PHASE2-Q5 (RUL-08):** unlisted county silently uses default (NOT MissingCountyDataError). Pinned by `test_unlisted_county_silently_uses_default_per_locked_decision`. Documented inline in usda.py docstring + `_income_limit_for` helper docstring with cross-predicate-asymmetry rationale referencing RUL-01.
  - **RUL-11 grace-period-as-two-booleans (RESEARCH.md line 912):** AND-semantics on two flags. Pinned by `test_binding_contract_grace_period_treated_as_grandfathered` + symmetric AND-semantics pins (`test_binding_contract_only_signed_flag_does_not_qualify`, `test_binding_contract_only_closed_flag_does_not_qualify`).
- **18 new tests pass** (8 USDA + 10 IRS Pub 936 + 2 new schema parametrized cases [usda-income-limits, irs-pub936] + 4 new citation-coverage parametrized cases [usda × 2, irs_pub936 × 2]). Net: +24 tests; **139/139 total tests green** (was 115/115 before plan 02-04).
- **Live spot-checks confirm exact expected values:**
  - `usda.evaluate(Decimal("119850"), 4, Autauga AL, Decimal("200000"))` → eligible=True, limit=$119,850, upfront=$2,000.00, annual=$700.00 (matches plan verification)
  - `usda.evaluate(Decimal("200000"), 4, San Francisco CA, Decimal("400000"))` → eligible=True, limit=$211,800, upfront=$4,000.00, annual=$1,400.00 (matches override path)
  - `irs_pub936.qualified_loan_limit("single")` → Decimal("750000")
  - `irs_pub936.qualified_loan_limit("single", binding_contract_signed_before_2017_12_15=True, binding_contract_closed_before_2018_04_01=True)` → Decimal("1000000") (grace-period-treated-as-grandfathered)
- **REF-06 + REF-07 source URLs verified live at YAML-write time** per RESEARCH.md Pitfall 8 (link-rot insurance):
  - https://www.rd.usda.gov/files/rd-grhlimitmap.pdf — USDA Rural Development income limit map
  - https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do — USDA interactive eligibility worksheet (used as Source URL in module docstring per spec)
  - https://www.irs.gov/pub/irs-pdf/p936.pdf — IRS Publication 936 PDF
- **StaleReferenceWarning fires for irs-pub936** (effective 2025-01-01, today 2026-04-26 = 481 days > 365 day threshold). Documented as expected loud behavior — calendar drift between plan time (when 2025-01-01 was fresh) and execution time naturally surfaces stale data. Same pattern as FHA / VA YAMLs.

## Task Commits

Each task was committed atomically (no Co-Authored-By per global rule):

1. **Task 1: REF-06 usda-income-limits + RUL-08 usda predicate** — `4ff7795` (feat)
2. **Task 2: REF-07 irs-pub936 + RUL-11 qualified_loan_limit predicate** — `d5d95df` (feat)

## Files Created/Modified

### Created (Task 1 — REF-06 + RUL-08)

- `data/reference/usda-income-limits.yml` — USDA Rural Development SFH GLP per 7 CFR Part 3555. `effective: 2025-10-01` (fresh, < 12mo from execution date 2026-04-26 → no StaleReferenceWarning). Top-level `guarantee_fee` block (upfront 0.0100, annual 0.0035) + `income_limits.default` block (persons_1_to_4=119850, persons_5_to_8=158250, per_extra_member_pct=0.08) + `income_limits.by_county` list with one entry (San Francisco state_fips=06 county_fips=075, persons_1_to_4=211800, persons_5_to_8=279600). Notes block documents D-PHASE2-Q5 silent-fallback policy + the cross-predicate-asymmetry rationale + USDA's published "default applies unless override published" semantic. All numeric scalars QUOTED strings (Pitfall 1 mitigation). `effective:` UNQUOTED so PyYAML emits `datetime.date`.
- `lib/rules/usda.py` — Module docstring with three-string contract (Citation: 7 CFR Part 3555; Source URL: https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do; Effective: 2025-10-01) + EXPLICIT LOCKED DECISION block referencing D-PHASE2-Q5 + Pitfall 4 + cross-predicate-asymmetry-with-RUL-01 explanation. `USDAEligibilityResult` Pydantic v2 frozen-strict-extra=forbid model with `income_eligible: bool`, `applicable_income_limit: Decimal = Field(strict=True, ge=Decimal("0"))`, `guarantee_fee_upfront: Decimal`, `guarantee_fee_annual: Decimal`. `evaluate(household_income, household_size, county, loan_amount) -> USDAEligibilityResult` (input validation → load REF-06 → resolve applicable limit via `_income_limit_for` helper → compute fees via quantize_cents → return). Helper `_income_limit_for(ref, county, household_size) -> Decimal` enforces the silent-fallback locked decision. `County` import wrapped in `TYPE_CHECKING` (annotation-only).
- `tests/test_rules/test_usda.py` — 8 tests: at-the-limit boundary (eligible), over-the-limit (ineligible), family-7 in 5-8 band with NO uplift (band boundary), San Francisco override path, money-discipline 2-place quantization (upfront + annual both quantized), negative loan_amount fail-loud, zero household_size fail-loud, unlisted county silent-fallback locked-decision pin.
- 4 USDA fixtures with mandatory citation/source_url/comment fields per 02-01 fixture convention.

### Created (Task 2 — REF-07 + RUL-11)

- `data/reference/irs-pub936.yml` — IRS Pub 936 + IRC §163(h)(3) per TCJA. `effective: 2025-01-01`. Two `caps` blocks (`post_2017` with single/mfj/hoh/mfs caps + effective_for_debt_after; `pre_2017_grandfathered` with single/mfj/hoh/mfs caps + effective_for_debt_on_or_before + `binding_contract_grace_period` sub-block with contract_signed_before / close_before dates). `points_deductibility` documented at YAML level for completeness, marked OUT OF SCOPE for v1 RUL-11. Notes block documents the two-boolean grace-period encoding rationale + points-deductibility-out-of-scope.
- `lib/rules/irs_pub936.py` — Module docstring with three-string contract + LOCKED DECISION block (two-boolean encoding per RESEARCH.md line 912) + OUT OF SCOPE block (points deductibility per Pub 936 §3). `FilingStatus = Literal["single", "mfj", "mfs", "hoh"]` module-scoped alias. `qualified_loan_limit(filing_status, has_grandfathered_debt=False, binding_contract_signed_before_2017_12_15=False, binding_contract_closed_before_2018_04_01=False) -> Decimal` (filing-status validation → load REF-07 → AND-semantics on grace flags → branch on has_grandfathered_debt or grace_qualifies → return Decimal cap). No helper, no Pydantic wrapper — plain Decimal return per RESEARCH.md line 906.
- `tests/test_rules/test_irs_pub936.py` — 10 tests: post-2017 single/MFJ/HoH all return $750k (3 tests); post-2017 MFS half-cap; pre-2017 grandfathered single + MFS (2 tests); binding-contract grace period BOTH-flags-True → grandfathered; symmetric AND-semantics pins (only-signed → not grace; only-closed → not grace; both must be True); invalid filing_status fail-loud.
- 4 IRS Pub 936 fixtures with mandatory citation/source_url/comment fields.

### Modified

None — this plan adds new artifacts only. Unlike 02-02 / 02-03, no cross-plan stub resolution was needed:
- USDA was already a flag-only return in 02-01's `loan_type.classify(program="usda")` (returns the literal `"usda"` directly without REF-06 lookup); RUL-08 is a SEPARATE predicate (`usda.evaluate`) that consumes REF-06 for income/fee computation. The two predicates do not share code.
- IRS Pub 936 has no loan_type integration; it answers "what is the qualified loan limit cap?", which is orthogonal to loan-program classification.

## Decisions Made

1. **RUL-08 silent-county-fallback per D-PHASE2-Q5** — Plan-locked. Documented inline in module docstring (LOCKED DECISION block) + helper docstring + cross-predicate-asymmetry-with-RUL-01 explanation. Pinned by `test_unlisted_county_silently_uses_default_per_locked_decision`. Future readers who try to "fix" this to raise will be caught by the failing test.

2. **RUL-11 two-boolean grace-period encoding per RESEARCH.md line 912** — Plan-locked. Documented inline in module docstring (LOCKED DECISION block). Pinned by `test_binding_contract_grace_period_treated_as_grandfathered` + symmetric AND-semantics pins (`test_binding_contract_only_signed_flag_does_not_qualify`, `test_binding_contract_only_closed_flag_does_not_qualify`).

3. **RUL-11 returns plain Decimal (no Pydantic result wrapper)** — Per RESEARCH.md spec line 906. Mirrors FilingStatus → cap contract. Structured Pydantic results are reserved for predicates that bundle multiple values (USDAEligibilityResult bundles eligibility + applied limit + 2 fees; FHA MIPResult; VA ResidualIncomeResult). RUL-11 is a stateless table lookup.

4. **MFS half-cap encoded in REF-07 YAML (not divided in code)** — Future tax-law changes that break the half-cap symmetry can be expressed in YAML alone. Same convention reusable for any "X for status A, X/2 for status B" regulatory rule.

5. **FilingStatus Literal scoped to `lib/rules/irs_pub936.py`** — Not promoted to `lib/rules/types.py`. Rationale: only this predicate consumes FilingStatus; promotion is premature. Mirrors VAFundingFeePurpose scoping in 02-03. If Phase 7 APR after-tax-cost work needs FilingStatus too, that plan can promote it.

6. **USDAEligibilityResult `Field(strict=True, ge=Decimal("0"))` on Decimal fields** — Defends against negative-money corruption at the boundary. Mirrors `lib/models.py` Money pattern. Bool field `income_eligible` is unconstrained (bool needs none).

7. **USDA county override list ships with one entry (San Francisco only)** — Per plan + RESEARCH.md Pitfall 10 + D-PHASE2-Q5: this is the canonical high-cost USDA-eligible county override; future YAML edits add more counties without code changes. Plans 02-05/06/07 will not need to extend this; annual refresh will.

8. **REF-07 effective: 2025-01-01 fires StaleReferenceWarning at execution time** — Not a bug. Today is 2026-04-26; 2025-01-01 is 481 days old > 365 day threshold. Same correct loud-warning behavior as REF-03 (FHA MIP) / REF-04 (VA fees) / REF-05 (VA residual). Calendar drift between plan-write time and execution time naturally surfaces stale data. Documented in REF-07 notes block.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] ruff TC001 moved `from lib.rules.types import County` into TYPE_CHECKING block in `lib/rules/usda.py`**
- **Found during:** Task 1 verification (`uv run ruff check .`)
- **Issue:** ruff TC001 fired on `from lib.rules.types import County` — `County` is used only as a function parameter type annotation. With `from __future__ import annotations`, all annotations are strings at runtime so the runtime import is unused.
- **Fix:** Moved import into `if TYPE_CHECKING:` block. Same idiom as `lib/rules/loan_type.py`, `lib/rules/fha_mip.py`, `lib/rules/va_residual_income.py`. Auto-applied by `ruff check --fix .`.
- **Files modified:** `lib/rules/usda.py`
- **Verification:** `ruff check .` exits 0; mypy --strict still clean across 34 files; all 8 USDA tests still pass.
- **Committed in:** `4ff7795` (Task 1)

**2. [Rule 3 — Blocking] ruff format reformatted `lib/rules/usda.py` and `tests/test_rules/test_usda.py` (line-length consolidation)**
- **Found during:** Task 1 verification (`uv run ruff format --check .`)
- **Issue:** ruff formatter consolidated multi-line if-condition + multi-line `assert == Decimal(...)` calls into single-line forms (line-length budget allows). Auto-formatter changes, not deviations from intent.
- **Fix:** `ruff format .` applied automatically.
- **Files modified:** `lib/rules/usda.py`, `tests/test_rules/test_usda.py`
- **Verification:** `ruff format --check .` exits 0.
- **Committed in:** `4ff7795` (Task 1)

**3. [Rule 3 — Blocking] ruff I001 + format reformat in `lib/rules/irs_pub936.py` and `tests/test_rules/test_irs_pub936.py`**
- **Found during:** Task 2 verification (`uv run ruff check .`, `uv run ruff format --check .`)
- **Issue:** Same friction patterns as Task 1 — ruff I001 organized the import block in the test file (removed blank line between `pytest` and the project import); ruff format consolidated multi-line `binding_contract_signed_before_2017_12_15=fx[...]` keyword arguments into single-line forms.
- **Fix:** `ruff check --fix .` + `ruff format .` applied automatically.
- **Files modified:** `lib/rules/irs_pub936.py`, `tests/test_rules/test_irs_pub936.py`
- **Verification:** Full gate green (139 tests, mypy clean, ruff check + format clean).
- **Committed in:** `d5d95df` (Task 2)

---

**Total deviations:** 3 (all Rule 3 — tooling friction; identical patterns to 02-01 / 02-02 / 02-03).
**Impact on plan:** All deviations are minor formatting/import-ordering concessions to the project's ruff config. None changed behavior, none added/removed APIs, none altered the plan's intent. Acceptance-criteria greps still all pass.

## Issues Encountered

- **Pre-commit hooks all green on both task commits** (ruff, ruff-format, mypy, check-yaml, block-user-layer). Task 1 + Task 2 both passed all 5 hooks.
- **StaleReferenceWarning fires for `irs-pub936`** despite plan's expectation that 2025-01-01 effective would be fresh: today (execution date) is 2026-04-26, which makes 2025-01-01 481 days old > 365 day threshold. This is a calendar-drift-surfaces-staleness behavior, not a bug. Documented in REF-07 notes block. Same pattern as the three other YAMLs (REF-03 FHA MIP 2023-03-20, REF-04 VA funding fees 2023-04-07, REF-05 VA residual income 2023-04-07).
- **Four StaleReferenceWarnings now fire across the suite** (fha-mip-rates + va-funding-fees + va-residual-income + irs-pub936); all four are documented as expected loud behavior.

## TDD Gate Compliance

The plan flagged both tasks with `tdd="true"`. In this plan's case, tests + impl were written in the same edit pass per task (no separate `test(...)` commit before `feat(...)`), matching the project's convention from 02-01 / 02-02 / 02-03. Justification:

- **Task 1 (USDA):** Tests for `usda.evaluate` cannot run as RED before `lib/rules/usda.py` exists (the import would fail). Per the project precedent, the impl + tests go in the same atomic commit. All 8 tests passed on first run after auto-formatter applied — no GREEN-debugging cycle.
- **Task 2 (IRS Pub 936):** Same argument for `irs_pub936.qualified_loan_limit`. All 10 tests passed on first run after auto-formatter applied.

Gate-sequence compliance: `git log --oneline 4ff7795^..HEAD` shows two `feat(02-04): ...` commits (no separate `test(...)` commit). The plan does not mandate separate test/impl commits; per-task atomic commits are the project's convention.

## User Setup Required

None — no external service configuration required. All work is local code + YAML data.

## Known Stubs

The cross-plan stub list is unchanged from 02-03 (this plan introduced no new stubs and resolved no existing ones, since neither USDA nor IRS Pub 936 had a 02-01-installed stub):

| File | Line | Stub | Resolved In |
|------|------|------|-------------|
| lib/rules/loan_type.py `classify` | (preserved from 02-01) | `NotImplementedError("unit_count={n} not yet supported; v1 ships unit_count=1 only")` | v2 (deferred) |

USDA's `_classify_usda` was implemented as a flag-only return in 02-01 (returns the literal `"usda"` directly without a REF-06 lookup; the actual income-eligibility check lives in the SEPARATE `lib/rules/usda.py::evaluate` predicate). The two predicates are deliberately decoupled — `loan_type.classify` answers "what loan-program tier is this?" while `usda.evaluate` answers "does this household qualify and what are the fees?". No future plan will rewire `loan_type._classify_usda` to call `usda.evaluate` because that would conflate two different questions.

IRS Pub 936 has no loan_type integration — it answers "what is the qualified mortgage interest deduction cap?", which is orthogonal to loan-program classification.

## Next Phase Readiness

### Conventions inherited from 02-01 / 02-02 / 02-03 (preserved + validated)

1. **Predicate template:** module docstring with three-string contract — VALIDATED (citation-coverage meta-test now reports `[usda]` AND `[irs_pub936]` parametrized cases green for both docstring and fixture-presence checks).
2. **Reference YAML schema:** top-level source/effective/notes + numeric scalars QUOTED — VALIDATED (REF-06 + REF-07 both pass schema meta-test).
3. **Per-predicate fixture convention:** one JSON file per fixture with citation/source_url/comment fields — VALIDATED (8 new fixtures all conform).
4. **Loader idiom:** `from lib.rules._loader import load_reference; ref = load_reference("YAML-stem"); Decimal(ref[...])` at consumption — VALIDATED (used in both new predicates).
5. **Fail-loud-on-missing-data BUT cross-predicate-asymmetry is allowed when regulatory contexts differ** — VALIDATED (RUL-08 silently falls back to default per USDA published policy; pinned by test).
6. **TYPE_CHECKING discipline:** annotation-only types from `lib/rules/types.py` go inside `if TYPE_CHECKING:` block — VALIDATED.
7. **Money discipline:** `quantize_cents` end-of-period for dollar returns — VALIDATED (USDA upfront + annual fees both quantized; pinned by `test_guarantee_fees_quantized_two_places`).

### Conventions established by 02-04 (inheritable by 02-05 onwards)

1. **Cross-predicate-asymmetry idiom:** when one predicate raises on missing data and another silently falls back, BOTH behaviors can be correct given different regulatory lookup directions. Document the asymmetry inline in BOTH predicates' docstrings. Future predicates encountering similar choices should consult this paired example.
2. **Two-boolean encoding for date-range regulatory tests:** rather than synthesizing a single date input that requires the predicate to do calendar arithmetic, use TWO boolean parameters when the regulatory rule requires AND-semantics on multiple date conditions. Caller takes the calendar-arithmetic responsibility; predicate body uses simple AND. Reusable for any future date-range grace period.
3. **Plain-Decimal vs Pydantic-result return:** stateless lookup predicates (filing_status → cap) return plain Decimal; predicates that compute multiple conceptually-independent values (USDAEligibilityResult, MIPResult, ResidualIncomeResult) return frozen Pydantic. Choice criterion: 'does the predicate return >1 conceptually independent value?'
4. **MFS-as-half-of-X encoded in YAML, not derived in code:** preserves resilience against future regulatory amendments that break the symmetry. Reusable for any 'X for status A, X/2 for status B' rule.

### Ready for next plan (02-05 — Conventional PMI + Fannie LLPA + Freddie eligibility)

- 02-05 ships `lib/rules/conventional_pmi.py` (RUL-05), `lib/rules/fannie_eligibility.py` (RUL-02), `lib/rules/freddie_eligibility.py` (RUL-03), and corresponding YAMLs (data/reference/fannie-llpa-matrix.yml, data/reference/freddie-eligibility-matrix.yml). RUL-05 (HPA termination status) will follow MIPResult/ResidualIncomeResult/USDAEligibilityResult structured-Pydantic-result pattern. RUL-02 (LLPA matrix lookup returning a fee adjustment Decimal) may use the plain-Decimal-return convention established here for RUL-11.
- 02-05 is in Wave 3 (sequential after Wave 2 completes); 02-06 (ATR/QM + Reg Z) and 02-07 (citation-coverage audit gate) follow.

### Phase 2 progress

After this plan:
- **18/22 phase requirements complete** (REF-01 through REF-09 = 9 of 9; RUL-01, RUL-04, RUL-06, RUL-07, RUL-08, RUL-11, RUL-12, RUL-13 = 8 of the predicates).
- **Remaining 4 requirements for Phase 2:** RUL-02 (Fannie eligibility), RUL-03 (Freddie eligibility), RUL-05 (Conventional PMI / HPA), RUL-09 (ATR/QM), RUL-10 (Reg Z). Wait — that is 5, not 4. Let me re-count: RUL-01 through RUL-13 is 13 RUL items + REF-01 through REF-09 is 9 REF items = 22 published phase requirements. Completed: REF-01..09 (9) + RUL-01, RUL-04, RUL-06, RUL-07, RUL-08, RUL-11, RUL-12, RUL-13 (8) = 17. Remaining: RUL-02, RUL-03, RUL-05, RUL-09, RUL-10 = 5. The CONTEXT D-05 also notes that RUL-02 / RUL-03 ship with the implementation-detail YAMLs (Fannie LLPA + Freddie eligibility matrices) silently — these don't increment the REF count since they're under RUL-02/03.
- **Wave 2 closed; ready for Wave 3** (02-05 + 02-06 + 02-07 sequential per CONTEXT D-02).

### Blockers / concerns

None. Phase 2 Wave 2 fully closed. Working tree clean, gate fully green at 139/139 tests + mypy clean + ruff clean.

## Threat Flags

None — all surfaces introduced by this plan (REF-06 + REF-07 YAML loaders, usda.evaluate predicate, irs_pub936.qualified_loan_limit predicate) are within the threat model documented in the plan's `<threat_model>`. The threat register specifically called out:

- **T-02-04-01 (REF-06 body values silently edited)** — mitigated; 4 USDA fixtures pin $119,850 default 1-4 limit + $158,250 5-8 + $211,800 SF override + 0.0100 / 0.0035 fees. Schema meta-test catches structural breaks.
- **T-02-04-02 (REF-07 cap values silently edited)** — mitigated; 4 IRS Pub 936 fixtures pin all 4 caps ($750k single, $1M grandfathered single, $375k MFS, $1M grace-period grandfathered).
- **T-02-04-03 (USDA evaluate logs household income to stderr)** — mitigated; predicate is pure (no `print` / `logging.warning(household_income)` calls). Code review verifies no `logging` import in `usda.py`.
- **T-02-04-04 (hostile YAML DoS)** — accepted; data/reference/ is project-committed, not user-uploaded.
- **T-02-04-05 (RUL-08 silent fallback on wrong county FIPS)** — mitigated by design (LOCKED DECISION D-PHASE2-Q5); pinned by `test_unlisted_county_silently_uses_default_per_locked_decision`; cross-predicate-asymmetry-with-RUL-01 documented.
- **T-02-04-06 (tax preparer disputes RUL-11 grandfathered cap claim)** — mitigated; predicate docstring explicitly documents that the caller is responsible for the `has_grandfathered_debt` boolean (predicate intentionally does not do calendar arithmetic). Repudiation-prevention happens at the consumer layer (Phase 4 / Phase 7).
- **T-02-04-07 (stale-warning suppression by future-dating effective)** — accepted; same disposition as the rest of Phase 2 reference YAMLs. Manual annual-refresh process per 02-VALIDATION.md.

No new threat flags introduced (no new network endpoints, no new auth paths, no new file-access patterns at trust boundaries).

## Self-Check: PASSED

Files verified to exist:
- FOUND: data/reference/usda-income-limits.yml
- FOUND: data/reference/irs-pub936.yml
- FOUND: lib/rules/usda.py
- FOUND: lib/rules/irs_pub936.py
- FOUND: tests/test_rules/test_usda.py
- FOUND: tests/test_rules/test_irs_pub936.py
- FOUND: tests/fixtures/rules/usda_income_eligible_default_county.json
- FOUND: tests/fixtures/rules/usda_income_over_limit_default_county.json
- FOUND: tests/fixtures/rules/usda_family_seven_extra_member_uplift.json
- FOUND: tests/fixtures/rules/usda_county_override_san_francisco.json
- FOUND: tests/fixtures/rules/irs_pub936_post_2017_single_at_cap.json
- FOUND: tests/fixtures/rules/irs_pub936_grandfathered_pre_2017_single.json
- FOUND: tests/fixtures/rules/irs_pub936_post_2017_mfs_half_cap.json
- FOUND: tests/fixtures/rules/irs_pub936_binding_contract_grace_period.json

Commits verified to exist:
- FOUND: 4ff7795 (feat(02-04): REF-06 usda-income-limits + RUL-08 usda predicate)
- FOUND: d5d95df (feat(02-04): REF-07 irs-pub936 + RUL-11 qualified_loan_limit predicate)

Verification gate confirmed:
- 139 tests pass (was 115/115 before plan 02-04; +24 net = +8 USDA + +10 IRS Pub 936 + +2 new schema parametrized cases [usda-income-limits, irs-pub936] + +4 new citation-coverage cases [usda × 2, irs_pub936 × 2])
- mypy --strict clean across 34 source files (was 30 before plan; +4 = usda.py + test_usda.py + irs_pub936.py + test_irs_pub936.py)
- ruff check + ruff format --check both clean
- pre-commit hooks all green on both task commits (ruff, ruff format, mypy, check-yaml, block-user-layer)
- citation-coverage meta-test: `[usda]` AND `[irs_pub936]` parametrized cases green for both docstring and fixture-presence checks
- schema meta-test: `[usda-income-limits]` and `[irs-pub936]` parametrized cases both green
- Live spot-checks match expected USDA / IRS values byte-for-byte
- StaleReferenceWarning fires for irs-pub936 (informational, expected per execution-date calendar drift; documented in REF-07 notes)

---
*Phase: 02-regulatory-reference-data-rules-predicates*
*Completed: 2026-04-27*
