---
phase: 02-regulatory-reference-data-rules-predicates
plan: 02
subsystem: rules-reference-data
tags: [fha, hud-ml-2023-05, hud-ml-2025-23, hud-ml-2013-04, mip, ufmip, decimal-discipline, predicate-template, frozen-pydantic, ltv-buckets]

# Dependency graph
requires:
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 01
    provides: lib/rules/_loader.py (load_reference + StaleReferenceWarning), lib/rules/types.py (LoanType, County), lib/rules/loan_type.py (_classify_fha STUB pointing at plan 02-02), tests/test_rules/test_citation_coverage.py (RUL-12/RUL-13 meta-test), tests/test_reference/test_schema.py (REF-09 meta-test), per-predicate fixture convention, three-string docstring contract
  - phase: 01-foundations-money-discipline
    provides: lib.models.Loan (Phase-1 frozen surface), lib.money.quantize_cents (ROUND_HALF_UP, 2 places, end-of-period only)
provides:
  - REF-02 — data/reference/fha-limits-2026.yml (HUD ML 2025-23 — floor $541,287 + ceiling $1,249,125 + 31 high-cost counties)
  - REF-03 — data/reference/fha-mip-rates.yml (HUD ML 2023-05 annual MIP rates after 30bps reduction + HUD ML 2013-04 termination rules)
  - RUL-04 — lib/rules/fha_mip.py with compute(loan, original_property_value, endorsement_date) -> MIPResult
  - MIPResult Pydantic v2 frozen-strict-extra=forbid model (ufmip + annual_mip_pct + terminates_at_period: int | Literal["life_of_loan"])
  - Extended _classify_fha branch in lib/rules/loan_type.py — now returns fha_standard / fha_high_balance / NotImplementedError-for-jumbo-FHA
  - Two new FHA loan_type fixtures (fha_standard low-cost county, fha_high_balance SF) and four new fha_mip fixtures (term30/ltv95, term30/ltv85, term15/ltv75, pre-2023-raises)
  - LTV bucket convention proven for [0,1] gap-free coverage (ltv_min exclusive except for 0.00 bucket which is inclusive; ltv_max inclusive)
affects: [02-03-va, 02-04-usda-irs, 02-05-pmi-fannie-freddie, 02-06-atr-qm-reg-z, 04-affordability, 06-refi-npv]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Predicate output as a frozen+strict Pydantic model with `int | Literal[\"sentinel\"]` field (MIPResult.terminates_at_period). Phase 4 consumers can match on `if isinstance(r.terminates_at_period, int): terminate at month X else: never_terminates`. Reusable shape for any predicate that returns money + ratio + termination-period."
    - "REF-03 annual_mip_table LTV bucket convention: ltv_min EXCLUSIVE for non-zero buckets, ltv_max INCLUSIVE; the 0.00 bucket treats ltv_min as inclusive. Covers [0, 1] without gap or overlap. _lookup_annual_mip helper enforces this at lookup time."
    - "Cross-plan stub idiom RESOLVED (first instance): loan_type.py FHA stub pointing at plan 02-02 was REPLACED with the real implementation in this plan; the stub-presence test (test_fha_program_raises_not_implemented_until_ref_02_lands) was removed and replaced with 4 positive FHA tests. Validates the 02-01 cross-plan-stub pattern end-to-end."
    - "Reference YAML 'effective' date older than 12mo is intentional + documented in YAML notes block (REF-03 effective=2023-03-20). StaleReferenceWarning fires every load -- correct loud behavior, not a bug. Re-verify annually."

key-files:
  created:
    - data/reference/fha-limits-2026.yml (REF-02 — HUD ML 2025-23 — floor $541,287 + ceiling $1,249,125 + 31 high-cost counties)
    - data/reference/fha-mip-rates.yml (REF-03 — HUD ML 2023-05 + 2013-04 — UFMIP 1.75% + 11 annual_mip_table rows + termination rules)
    - lib/rules/fha_mip.py (RUL-04 — compute() + MIPResult + _lookup_annual_mip helper)
    - tests/test_rules/test_fha_mip.py (6 tests: 3 LTV-bucket-pinned hand-calcs + pre-2023-raises + UFMIP money-discipline + LTV>1.00 fail-loud)
    - tests/fixtures/rules/loan_type_fha_standard.json
    - tests/fixtures/rules/loan_type_fha_high_balance.json
    - tests/fixtures/rules/fha_mip_term30_ltv95_post_2023.json
    - tests/fixtures/rules/fha_mip_term30_ltv85_post_2023.json
    - tests/fixtures/rules/fha_mip_term15_ltv90_post_2023.json
    - tests/fixtures/rules/fha_mip_pre_2023_raises.json
  modified:
    - lib/rules/loan_type.py (REPLACED _classify_fha body — was stub raising NotImplementedError("REF-02 ... shipped in plan 02-02"), now reads REF-02 and returns fha_standard / fha_high_balance / raises for above-ceiling and missing-county; ADDED _county_limit_fha helper; UPDATED edge-cases section in module docstring to remove FHA-stubbed mention)
    - tests/test_rules/test_loan_type.py (REMOVED test_fha_program_raises_not_implemented_until_ref_02_lands stub-presence test; ADDED 4 positive tests: classifies_below_floor_as_fha_standard, classifies_above_floor_as_fha_high_balance, above_county_ceiling_raises, above_floor_missing_county_raises; updated module docstring Coverage section)

key-decisions:
  - "LTV bucket convention encoded in _lookup_annual_mip: ltv_min EXCLUSIVE for non-zero buckets, INCLUSIVE for 0.00 bucket; ltv_max always INCLUSIVE. Defends against off-by-one at bucket boundaries (T-2-02-03)."
  - "Pre-2023-03-20 endorsement raises NotImplementedError with both 'before the 2023-03-20 effective date' and 'pre-2023-03-20 MIP rates differ' phrasing. The lowercase 'pre-2023-03-20' substring is what the fixture's expected_match regex pins; the capitalized 'Pre-' was rejected by the case-sensitive regex (Rule 1 bug fixed during execution)."
  - "loan.principal pulled from the Phase-1 Loan Pydantic model rather than passing principal as a separate Decimal arg. Validates that lib.models.Loan is a stable Phase-2 input contract; future predicates (RUL-05 conventional_pmi, RUL-06 va_funding_fee) should follow the same shape."
  - "MIPResult.terminates_at_period typed as int | Literal['life_of_loan'] (not str). The 'life_of_loan' sentinel is loaded directly from the REF-03 YAML as the string 'life_of_loan' (quoted in YAML) -- mypy --strict accepts the union because Pydantic narrows the type at validation. Phase 4 / Phase 6 consumers can match on isinstance(x, int)."
  - "loan_type.py edge-cases docstring section refactored to drop 'before REF-02 lands' phrasing for FHA (since we just landed it) and replaced with the new edge-case enumeration: missing-county-above-floor + above-county-ceiling. VA branch text preserved (still stubbed for plan 02-03)."
  - "FHA county subset (31 counties in REF-02) is a strict subset of REF-01's high-cost subset (54 counties). Rationale: HUD's ceiling matches FHFA's ceiling, so any high-cost county at FHFA's $1,249,125 ceiling has the same FHA limit. Counties NOT in REF-02 high_cost_counties get the floor (per HUD convention: low-cost-areas use the floor)."

patterns-established:
  - "Predicate output Pydantic model shape: frozen+strict+extra=forbid with int | Literal['sentinel'] for termination-period style fields. Reused by future RUL-05 (conventional_pmi) for HPA termination status."
  - "REF-YAML LTV-bucket table convention with ltv_min/ltv_max/loan_amount_max keys + helper that enforces inclusive/exclusive bucket boundaries with explicit 0.00-special-case. Reusable for any tiered-rate lookup (PMI rates, VA funding fees by LTV bucket, USDA guarantee fees by loan-amount tier)."
  - "Cross-plan stub idiom resolution sequence (now demonstrated end-to-end): (a) 02-01 stubbed _classify_fha with NotImplementedError mentioning 02-02; (b) 02-01 added a positive test asserting the stub fires; (c) 02-02 REPLACED stub body with real implementation; (d) 02-02 REMOVED the stub-presence test and ADDED positive behavior tests in its place. Plans 02-03 (VA branch in loan_type) and 02-04 (USDA / IRS) will repeat this sequence."

requirements-completed: [REF-02, REF-03, RUL-04]

# Metrics
duration: 7min
completed: 2026-04-27
---

# Phase 2 Plan 02: FHA Limits + MIP + loan_type FHA-branch wiring Summary

**REF-02 (FHA 2026 limits per HUD ML 2025-23) + REF-03 (FHA MIP rates per HUD ML 2023-05 with HUD ML 2013-04 termination rules) + RUL-04 (fha_mip.compute predicate with MIPResult frozen-Pydantic output) + extended loan_type._classify_fha branch (replaces 02-01 cross-plan stub).**

## Performance

- **Duration:** ~7 min wall time
- **Started:** 2026-04-27T03:15:27Z
- **Completed:** 2026-04-27T03:22:05Z
- **Tasks:** 2
- **Files created:** 10 (2 YAMLs + 1 predicate + 1 test + 6 fixtures)
- **Files modified:** 2 (lib/rules/loan_type.py — _classify_fha replaced + _county_limit_fha added; tests/test_rules/test_loan_type.py — old stub test removed + 4 positive tests added)

## Accomplishments

- **3 requirements landed and verified:** REF-02 (FHA limits), REF-03 (FHA MIP rates), RUL-04 (fha_mip predicate).
- **FHA branch of loan_type.classify is now LIVE.** `classify(amount, county, program="fha")` returns `fha_standard` / `fha_high_balance` (or raises `MissingCountyDataError` for missing-county-above-floor or `NotImplementedError` for above-county-ceiling). The 02-01 cross-plan stub idiom is fully validated: stub → wiring plan → positive tests in the same file.
- **HUD numeric anchors pinned:** UFMIP = 1.75%; annual MIP rates {0.0055, 0.0050, 0.0040, 0.0015, 0.0070, 0.0075}; termination {life_of_loan, 132}; FHA floor $541,287; FHA ceiling $1,249,125.
- **Pitfall 5 (silent FHA grandfathering) is COVERED.** `compute(...)` raises `NotImplementedError` for endorsement_date < 2023-03-20 with the regex-matchable substring `pre-2023-03-20`; pinned by `test_fha_mip_pre_2023_endorsement_raises`.
- **Pitfall 6 (PMI/MIP confusion) is PROTECTED.** RUL-04 lives in `lib/rules/fha_mip.py`; future RUL-05 will live in `lib/rules/conventional_pmi.py`. Tests assert FHA-specific termination = `"life_of_loan"` or `132` — never the HPA's 78%/80% sentinel.
- **13 new tests pass** (6 fha_mip + 4 new FHA loan_type + 1 new schema [fha-limits-2026] + 1 new schema [fha-mip-rates] + the citation-coverage test for fha_mip auto-discovers itself via 2 new parametrized cases). One test was REMOVED (the 02-01 stub-presence test). Net: +12 tests; 90/90 total tests green (was 77/77 before plan 02-02).
- **Live spot-checks confirm exact expected values:**
  - `compute($400k loan, $410k value, 360mo, 2024-06-15)` → `UFMIP=7000.00 annual=0.0055 term=life_of_loan` (matches plan verification block 3 byte-for-byte)
  - `classify($400k, Autauga AL, program="fha")` → `fha_standard` (matches plan verification block 4)
- **StaleReferenceWarning correctly fires** for `fha-mip-rates` (effective 2023-03-20 > 12mo threshold); informational, not error. Documented in REF-03 notes block as expected behavior.

## Task Commits

Each task was committed atomically (no Co-Authored-By per global rule):

1. **Task 1: REF-02 + REF-03 YAMLs + extend FHA classify branch** — `3073204` (feat)
2. **Task 2: RUL-04 fha_mip.py predicate + 4 hand-calc fixtures** — `af1c7ef` (feat)

## Files Created/Modified

### Created (Task 1 — REF-02 + REF-03 + FHA classify wiring)

- `data/reference/fha-limits-2026.yml` — HUD ML 2025-23, effective 2026-01-01: floor (1-unit $541,287, 2/3/4-unit), ceiling (1-unit $1,249,125, matches FHFA conforming ceiling), 31 high-cost counties (CA Bay Area + LA / NYC metro / DC + NoVA + suburban MD / Boston Middlesex+Suffolk at $928,000 / NJ commuter belt / King+Snohomish WA at $1,027,000 / all of HI / Anchorage AK). All numeric scalars QUOTED strings (Pitfall 1 mitigation). `effective: 2026-01-01` UNQUOTED so PyYAML emits `datetime.date`.
- `data/reference/fha-mip-rates.yml` — HUD ML 2023-05 (annual rates after 30bps reduction) + HUD ML 2013-04 (termination rules), effective 2023-03-20 (intentionally older than 12mo staleness threshold; documented in YAML notes). UFMIP rate 0.0175. annual_mip_table: 11 rows covering term-15 vs term-30 × standard ($≤726,200) vs high-balance ($>726,200) × LTV buckets {0.00..0.78, 0.78..0.90, 0.90..0.95, 0.95..1.00}. termination: `ltv_above_90_pct: "life_of_loan"`, `ltv_at_or_below_90_pct: 132`. grandfathering: pre-2023 endorsements raise NotImplementedError.
- `tests/fixtures/rules/loan_type_fha_standard.json` — $400k loan in Autauga AL (NOT in high_cost_counties; FHA limit IS the floor) → fha_standard.
- `tests/fixtures/rules/loan_type_fha_high_balance.json` — $700k loan in San Francisco (FHA ceiling $1,249,125) → fha_high_balance.

### Created (Task 2 — RUL-04 fha_mip predicate + fixtures)

- `lib/rules/fha_mip.py` — Module docstring with three-string contract (Citation: HUD ML 2023-05 + HUD ML 2013-04; Source URL: https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf; Effective: 2023-03-20). `MIPResult` Pydantic v2 frozen-strict-extra=forbid model with `ufmip: Decimal`, `annual_mip_pct: Decimal`, `terminates_at_period: int | Literal["life_of_loan"]`. `compute(loan, original_property_value, endorsement_date) -> MIPResult` (sentinel-date check → load REF-03 → UFMIP via quantize_cents → LTV bounds checks → annual MIP table lookup → termination decision). `_lookup_annual_mip` helper enforces LTV bucket convention.
- `tests/test_rules/test_fha_mip.py` — 6 tests: `term30_ltv95_post_2023_returns_life_of_loan`, `term30_ltv85_post_2023_terminates_at_132mo`, `term15_ltv75_post_2023_short_term_low_rate`, `pre_2023_endorsement_raises`, `ufmip_returns_quantized_two_places` (asserts `result.ufmip.as_tuple().exponent == -2`), `ltv_above_one_raises`. Helper `_loan_from_fx` reconstructs the Phase-1 `Loan` model from fixture JSON.
- `tests/fixtures/rules/fha_mip_term30_ltv95_post_2023.json` — $400k loan, $410k value, term 360, 2024-06-15 → expected ufmip=$7,000.00, annual=0.0055, term=life_of_loan.
- `tests/fixtures/rules/fha_mip_term30_ltv85_post_2023.json` — $400k loan, $470k value, term 360, 2024-06-15 → ufmip=$7,000.00, annual=0.0050, term=132.
- `tests/fixtures/rules/fha_mip_term15_ltv90_post_2023.json` — $300k loan, $400k value, term 180, 2024-06-15 → ufmip=$5,250.00, annual=0.0015, term=132.
- `tests/fixtures/rules/fha_mip_pre_2023_raises.json` — endorsement_date 2014-08-01 → expected NotImplementedError matching `pre-2023-03-20`.

### Modified

- `lib/rules/loan_type.py` — REPLACED `_classify_fha` body (was a 2-step stub raising NotImplementedError pointing at plan 02-02) with the real REF-02-backed implementation; ADDED `_county_limit_fha(ref, county, unit_key, floor)` helper (mirrors `_county_limit` but uses `floor` as the unlisted-county fallback per HUD's "low-cost areas use the floor" convention); UPDATED module-level Edge cases docstring section to remove the now-obsolete "before REF-02/REF-04 land" line and replace with the FHA-specific enumeration (missing-county-above-floor + above-county-ceiling).
- `tests/test_rules/test_loan_type.py` — REMOVED `test_fha_program_raises_not_implemented_until_ref_02_lands` (the 02-01 stub-presence test); ADDED 4 positive FHA tests covering the four FHA outcomes (fha_standard, fha_high_balance, above-county-ceiling NotImplementedError, missing-county-above-floor MissingCountyDataError); UPDATED Coverage section in module docstring.

## Decisions Made

1. **LTV bucket convention encoded in `_lookup_annual_mip` helper** — the 0.00..0.78 / 0.78..0.90 / 0.90..0.95 / 0.95..1.00 buckets cover [0, 1] without gap or overlap. Implemented as: ltv_min EXCLUSIVE for non-zero buckets, ltv_max INCLUSIVE always, with explicit `if ltv_min == Decimal("0.00"):` special case so the lowest bucket is inclusive at 0. This is the only valid encoding given the YAML structure; the alternative (overlap at boundaries) would be ambiguous for an LTV exactly at 0.90 / 0.95. Defends against T-2-02-03 (off-by-one at LTV bucket boundary).

2. **Pre-2023 NotImplementedError message must contain lowercase `pre-2023-03-20` substring** — first draft had `Pre-2023-03-20` (capitalized) which the fixture's case-sensitive regex (`expected_match: "pre-2023-03-20"`) rejected. The fix made BOTH occurrences lowercase. Documented as Rule 1 deviation below.

3. **`Loan` import wrapped in TYPE_CHECKING block in `fha_mip.py`** — `Loan` is used only as a function parameter type annotation; with `from __future__ import annotations` all annotations are strings at runtime. ruff TC001 catches this. Mirrors the same pattern used in `loan_type.py`.

4. **`re.escape`-style raw-string regex `r"LTV.*exceeds 1\.00"`** — ruff RUF043 caught the unescaped `.` metacharacter in `match="LTV.*exceeds 1.00"`. Switching to a raw string lets us escape `\.` explicitly (the `1.00` should be a literal period, not a wildcard); the `.*` between `LTV` and `exceeds` is intentional (matches `=0.95...`).

5. **MIPResult.terminates_at_period typed `int | Literal["life_of_loan"]`** — the YAML stores "life_of_loan" as a quoted string, so `ref["termination"]["ltv_above_90_pct"]` returns the str `"life_of_loan"`. Pydantic strict+frozen+extra=forbid validates the union at construction; mypy --strict accepts the assignment after the `terminates: int | Literal["life_of_loan"]` annotation on the local variable.

6. **MIPResult includes `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` verbatim per Phase 1 + 02-01 PATTERNS Convention** — no paraphrases. This makes MIPResult instances hashable (frozen) and rejects unexpected keys (extra=forbid) so future API extensions are explicit.

7. **`loan_type.py` Edge cases docstring section rewritten** — was a stale list referencing "before REF-02/REF-04 land" for both FHA and VA. Now: FHA-specific edge cases enumerated (missing-county-above-floor, above-county-ceiling) + VA still references plan 02-03. This keeps the docstring accurate for each shipped feature.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Lowercased `pre-` in NotImplementedError message to match fixture regex**
- **Found during:** Task 2 RED→GREEN transition (test_fha_mip_pre_2023_endorsement_raises failed even after compute() correctly raised NotImplementedError)
- **Issue:** The fixture's `expected_match: "pre-2023-03-20"` is case-sensitive; my first-pass error message had `"Pre-2023-03-20 MIP rates differ"` (capitalized P). The plan's `<behavior>` for Test 4 explicitly specified `"pre-2023-03-20"` (lowercase). The fix made the substring lowercase in the second sentence of the message; the human-readable phrasing of the first sentence was preserved.
- **Fix:** Reworded the error message to: `"endorsement_date {iso} is before the 2023-03-20 effective date of HUD ML 2023-05. pre-2023-03-20 MIP rates differ from current rates; grandfathering is deferred to v2. See REF-03 notes."`
- **Files modified:** `lib/rules/fha_mip.py`
- **Verification:** `pytest tests/test_rules/test_fha_mip.py::test_fha_mip_pre_2023_endorsement_raises -x` exits 0
- **Committed in:** `af1c7ef` (Task 2)

**2. [Rule 3 — Blocking] Wrapped `from lib.models import Loan` in `TYPE_CHECKING` block (ruff TC001)**
- **Found during:** Task 2 verification (`uv run ruff check .`)
- **Issue:** ruff TC001 fired on `from lib.models import Loan` in `lib/rules/fha_mip.py` because `Loan` is used only in function annotations (no runtime construction in this module — tests instantiate Loan directly).
- **Fix:** Moved import into `if TYPE_CHECKING:` block. Same idiom as `lib/rules/loan_type.py` for `County` / `LoanType`. With `from __future__ import annotations`, annotations are strings at runtime so the TYPE_CHECKING guard is correct.
- **Files modified:** `lib/rules/fha_mip.py`
- **Verification:** `ruff check .` exits 0; mypy --strict still clean.
- **Committed in:** `af1c7ef` (Task 2)

**3. [Rule 3 — Blocking] Used raw string + escaped period in regex match arg (ruff RUF043)**
- **Found during:** Task 2 verification (`uv run ruff check .`)
- **Issue:** ruff RUF043 flagged `pytest.raises(ValueError, match="LTV.*exceeds 1.00")` — the `.` is a regex metacharacter and not escaped or marked raw.
- **Fix:** Changed to `pytest.raises(ValueError, match=r"LTV.*exceeds 1\.00")` — raw string + explicit escape on `\.` to mean literal period. The `.*` between `LTV` and `exceeds` is intentional (matches the variable LTV value `=0.97...` in the actual error message).
- **Files modified:** `tests/test_rules/test_fha_mip.py`
- **Verification:** `ruff check .` exits 0; the test still passes.
- **Committed in:** `af1c7ef` (Task 2)

---

**Total deviations:** 3 (1 Rule 1 bug + 2 Rule 3 tooling-friction blockers)
**Impact on plan:** Rule 1 deviation was a real bug — the plan's behavior spec specified the lowercase `pre-2023-03-20` regex, and my first-pass message didn't match it. Caught in TDD GREEN phase (the test failed; I fixed the message). Rule 3 deviations were ruff TC001 + RUF043 friction (same patterns from 02-01: `Loan` annotation-only import + unescaped regex metachar). None changed behavior, none added/removed APIs, none altered the plan's intent. Acceptance-criteria greps still match.

## Issues Encountered

- **Pre-commit `check-yaml` hook skipped on Task 2 commit:** Expected — Task 2 added no `data/reference/*.yml` files (those landed in Task 1). Hook output: "(no files to check)Skipped". Confirms file scoping works.
- **StaleReferenceWarning fires every load of fha-mip-rates:** Expected per REF-03 notes block. The HUD ML 2023-05 effective date IS 2023-03-20, which IS more than 12 months old. The warning is a yearly nudge to re-verify HUD hasn't republished. NOT a bug — fixing it would require either acknowledging the staleness in YAML (deferred per D-12) or downgrading the threshold (would defeat the warning's purpose).
- **`Plan Verification Block 3` shell echo lost the `$400k` literal** because the inline `$4` looked like a shell variable: prints `k @ k val` instead of `$400k @ $410k val` in the verification log header. Cosmetic only — the actual Python spot-check output (`UFMIP=7000.00 annual=0.0055 term=life_of_loan`) is correct.

## TDD Gate Compliance

The plan flagged both tasks with `tdd="true"`. Both tasks followed real RED → GREEN cycles:

- **Task 1 (FHA classify):** RED — wrote new test fixtures + replaced the stub-presence test with 4 positive tests; ran `pytest tests/test_rules/test_loan_type.py -k fha` → 4/4 failed with `NotImplementedError: FHA classify() body shipped in plan 02-02`. GREEN — replaced `_classify_fha` body with REF-02-backed implementation; ran the same selector → 4/4 pass.
- **Task 2 (fha_mip):** RED — wrote 4 fixtures + the 6-test test file; ran `pytest tests/test_rules/test_fha_mip.py -x` → `ModuleNotFoundError: No module named 'lib.rules.fha_mip'`. GREEN — wrote `lib/rules/fha_mip.py`; ran the same selector → 5 pass + 1 fail (pre-2023 regex). REFACTOR-style fix (Rule 1 deviation #1 above) → 6/6 pass.

Gate-sequence compliance: `git log --oneline 3073204^..HEAD` shows two `feat(02-02): ...` commits (no separate `test(...)` commit because the tests + impl were committed atomically per task). The plan does not mandate separate test/impl commits; per-task atomic commits are the project's convention.

## User Setup Required

None — no external service configuration required. All work is local code + YAML data.

## Known Stubs

The cross-plan stub list shrinks by ONE relative to 02-01 (FHA stub was the resolution target of THIS plan):

| File | Line | Stub | Resolved In |
|------|------|------|-------------|
| ~~lib/rules/loan_type.py `_classify_fha`~~ | ~~old~~ | ~~`NotImplementedError("REF-02 ... shipped in plan 02-02")`~~ | **02-02 (THIS PLAN — RESOLVED)** |
| lib/rules/loan_type.py `_classify_va` | (preserved) | `NotImplementedError("VA classify() body shipped in plan 02-03 (RUL-06/RUL-07 wiring)")` | Plan 02-03 |
| lib/rules/loan_type.py `classify` | (preserved) | `NotImplementedError("unit_count={n} not yet supported; v1 ships unit_count=1 only")` | v2 (deferred) |

No new stubs introduced. The MIPResult shape's `int | Literal["life_of_loan"]` field is intentional sentinel design, not a stub.

## Next Phase Readiness

### Conventions inherited from 02-01 (preserved + validated)

1. **Predicate template:** module docstring with three-string contract — VALIDATED (citation-coverage meta-test now reports `[fha_mip]` parametrized case green for both docstring and fixture-presence checks).
2. **Reference YAML schema:** top-level source/effective/notes + numeric scalars QUOTED — VALIDATED (REF-02 + REF-03 both pass schema meta-test; live load via `load_reference()` returns the expected dict shape).
3. **Per-predicate fixture convention:** one JSON file per fixture under tests/fixtures/rules/{stem}_*.json with citation/source_url/comment fields — VALIDATED (4 new fha_mip fixtures + 2 new loan_type FHA fixtures all conform).
4. **Loader idiom:** `from lib.rules._loader import load_reference; ref = load_reference("YAML-stem"); Decimal(ref[...])` at consumption — VALIDATED (used in both `_classify_fha` and `fha_mip.compute`).
5. **Cross-plan stub idiom resolution:** stub → wiring plan → positive tests in the same file — VALIDATED end-to-end (FHA stub-presence test removed; 4 positive FHA tests added; gate green).
6. **Fail-loud-on-missing-data:** `MissingCountyDataError` for missing-county-above-floor (FHA); `NotImplementedError` for above-county-ceiling (jumbo FHA not in v1); `ValueError` for LTV>1.00 invalid input — all loud, no silent defaults.
7. **TYPE_CHECKING discipline:** `Loan` import wrapped in TYPE_CHECKING block in fha_mip.py — VALIDATED.

### Conventions established by 02-02 (inheritable by 02-05 onwards)

1. **Predicate output as a frozen+strict Pydantic model with sentinel union types** — `MIPResult.terminates_at_period: int | Literal["life_of_loan"]` is the established shape for "predicate returns money + ratio + termination-period." Future RUL-05 (conventional_pmi) will use the same shape (its termination is HPA-defined: 78% LTV auto, 80% LTV request, neither yet → `None` sentinel or analogous union).
2. **REF-YAML LTV-bucket table convention** — ltv_min/ltv_max/loan_amount_max keys + helper that enforces inclusive/exclusive bucket boundaries with explicit 0.00 inclusivity. Reusable for any tiered-rate lookup (PMI rates by LTV bucket, VA funding fees by LTV bucket, USDA guarantee fees by loan-amount tier).
3. **YAML notes block can document expected-but-loud behavior** — REF-03's notes block explicitly documents that StaleReferenceWarning WILL fire and IS correct. Future YAMLs that ship intentionally-old-but-still-current data should follow the same pattern (won't apply to REF-04/05/06 since VA M26-7 is also 2023, IRS Pub 936 dates from 2017 — both will inherit this idiom).

### Ready for next plan (02-03 — VA funding fee + residual income)

- 02-03 ships `data/reference/va-funding-fees.yml` (REF-04) + `data/reference/va-residual-income.yml` (REF-05) + `lib/rules/va_funding_fee.py` (RUL-06) + `lib/rules/va_residual_income.py` (RUL-07). It will also rewrite `_classify_va` in `lib/rules/loan_type.py` to load REF-04 (or use FHFA conforming since 2020 for full-entitlement vets) and rewrite `test_va_program_raises_not_implemented_until_va_wiring_lands` to assert positive VA classification.
- The same cross-plan-stub-resolution sequence demonstrated by 02-02 applies: 02-03 will REPLACE the VA stub body, REMOVE the VA stub-presence test, and ADD positive VA tests in its place.
- The MIPResult/_lookup_annual_mip patterns established here are the template for VA RUL-06 (funding fee = principal × rate by use/down-payment-tier).

### Blockers / concerns

None. Phase 2 Wave 2 first plan is locked in cleanly. Working tree clean, gate fully green.

## Threat Flags

None — all surfaces introduced by this plan (REF-02 + REF-03 YAML loaders, fha_mip predicate, extended FHA classify branch) are within the threat model documented in the plan's `<threat_model>`. The threat register specifically called out:

- **T-2-02-01 (silent grandfathering of pre-2023 endorsements)** — mitigated; `test_fha_mip_pre_2023_endorsement_raises` pins the NotImplementedError.
- **T-2-02-02 (FHA termination rule confused with HPA PMI rule)** — mitigated; RUL-04 lives in `lib/rules/fha_mip.py` (not `conventional_pmi.py`); MIPResult.terminates_at_period values are `"life_of_loan"` or `132` (never the HPA's 78%/80% sentinel).
- **T-2-02-03 (annual MIP row off-by-one at LTV bucket boundary)** — mitigated; `_lookup_annual_mip` enforces inclusive-upper / exclusive-lower bounds with explicit `ltv_min == Decimal("0.00")` special-case. Tests pin LTV ≈ 0.9756 (above 0.95 boundary), 0.8511 (above 0.78, below 0.90 boundary), 0.75 (in 0.00..0.78 bucket).
- **T-2-02-04 (UFMIP money-discipline drift)** — mitigated; `quantize_cents` called once at end-of-period on `loan.principal * ufmip_rate`. `test_fha_mip_ufmip_returns_quantized_two_places` pins 2-place exponent + ROUND_HALF_UP behavior.
- **T-2-02-05 (silent fallback when annual_mip_table has gap)** — mitigated; `_lookup_annual_mip` raises `LookupError` when no row matches. Future REF-03 schema regressions caught immediately.

No new threat flags introduced (no new network endpoints, no new auth paths, no new file-access patterns at trust boundaries).

## Self-Check: PASSED

Files verified to exist:
- FOUND: data/reference/fha-limits-2026.yml
- FOUND: data/reference/fha-mip-rates.yml
- FOUND: lib/rules/fha_mip.py
- FOUND: lib/rules/loan_type.py (modified)
- FOUND: tests/test_rules/test_fha_mip.py
- FOUND: tests/test_rules/test_loan_type.py (modified — old stub test removed, 4 positive tests added)
- FOUND: tests/fixtures/rules/loan_type_fha_standard.json
- FOUND: tests/fixtures/rules/loan_type_fha_high_balance.json
- FOUND: tests/fixtures/rules/fha_mip_term30_ltv95_post_2023.json
- FOUND: tests/fixtures/rules/fha_mip_term30_ltv85_post_2023.json
- FOUND: tests/fixtures/rules/fha_mip_term15_ltv90_post_2023.json
- FOUND: tests/fixtures/rules/fha_mip_pre_2023_raises.json

Commits verified to exist:
- FOUND: 3073204 (feat(02-02): REF-02 + REF-03 + extend FHA classify branch)
- FOUND: af1c7ef (feat(02-02): RUL-04 fha_mip predicate + 4 hand-calc fixtures)

Verification gate confirmed:
- 90 tests pass (was 77/77 before plan 02-02; +13 net = +6 fha_mip + +4 new FHA loan_type + +2 new schema parametrized cases + +1 net change from removing stub test and adding 4 FHA tests)
- mypy --strict clean across 26 source files (was 24 before plan; +2 = fha_mip.py + test_fha_mip.py)
- ruff check + ruff format --check both clean
- pre-commit hooks all green on both task commits (ruff, ruff format, mypy, check-yaml, block-user-layer)
- citation-coverage meta-test: `[fha_mip]` parametrized case green for both docstring and fixture-presence checks
- schema meta-test: `[fha-limits-2026]` and `[fha-mip-rates]` parametrized cases both green
- Live spot-checks match plan verification block 3 + 4 byte-for-byte
- StaleReferenceWarning fires for fha-mip-rates (informational, expected per REF-03 notes)

---
*Phase: 02-regulatory-reference-data-rules-predicates*
*Completed: 2026-04-27*
