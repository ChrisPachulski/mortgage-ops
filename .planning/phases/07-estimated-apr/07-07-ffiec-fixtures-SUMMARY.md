---
phase: 07-estimated-apr
plan: 07
subsystem: ffiec-fixtures
tags:
  - phase-07
  - estimated-apr
  - oracle
  - apr-04
  - sc-2
  - partial-closure
  - autonomous-override

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Decimal-from-string discipline + Wikipedia $200k @ 6.5%/30yr → $1,264.14 oracle anchor (cross-validation source for the 12 regular-monthly archetypes via PV-form collapse identity)"
  - phase: 07-estimated-apr (Plan 07-01)
    provides: "APRRequest + APRResponse + AdvanceScheduleEntry + PaymentScheduleEntry boundary models (the corpus's request payloads validate against these surfaces verbatim)"
  - phase: 07-estimated-apr (Plan 07-02)
    provides: "solve_apr Newton-Raphson body + APRConvergenceError (every fixture's expected.estimated_apr is solve_apr's output at fixture-write time)"
  - phase: 07-estimated-apr (Plan 07-03)
    provides: "_compute_odd_first_period_fraction + APRRequest.odd_first_period_days wiring (4 of the 20 fixtures exercise this surface — ffiec_013..016 with 5/10/20/15-day odd first periods)"
  - phase: 07-estimated-apr (Plan 07-05)
    provides: "tests/conftest.py apr_fixture factory + the 'oracle/<stem>' addressing convention (the parametric test loads oracle fixtures via apr_fixture('oracle/ffiec_NNN_...'))"
  - phase: 07-estimated-apr (Plan 07-06)
    provides: "references/apr-reg-z.md §6 already documents the HMDA Platform sole-oracle decision per CONTEXT D-01 + the FFIEC-out-of-scope decision per D-02 — Wave 7 inherits doc cover without edit"
  - phase: 07-estimated-apr (Plan 07-00)
    provides: "13 Wave-0 xfail-strict stubs in tests/test_apr.py — this wave flips the 13th and final stub (test_apr_ffiec_oracle_fixtures_match_within_decimal_00001 / APR-04)"
provides:
  - "tests/fixtures/apr/oracle/ffiec_001..ffiec_020.json (20 oracle fixtures spanning 5 archetypes; 12 cross-validated against Wikipedia worked example + 8 engine-emitted)"
  - "tests/fixtures/apr/oracle/README.md (provenance disclosure, capture protocol, fallback substitution log, refresh cadence, recommended path to full closure)"
  - "scripts/_generate_apr_oracle_fixtures.py (deterministic regenerator; reproducible at any commit + dates)"
  - "test_apr_ffiec_oracle_fixtures_match_within_decimal_00001 flipped from Wave-0 single-stub xfail to @pytest.mark.parametrize over 20 fixture stems (closes APR-04 partial-style)"
  - "All 13 Wave-0 stubs in tests/test_apr.py now flipped (zero xfails remaining for APR-XX requirements)"
affects:
  - phase 08 stress-points: solve_apr is the Phase 8 stress-test integration point; the 20 oracle fixtures are now part of the regression baseline (any engine drift > Decimal('0.00001') will fail loudly)
  - phase 10 claude-skill: oracle fixtures will move with the test suite if the Phase 10 relocation includes them; otherwise apr_fixture's relative-path lookup keeps them addressable

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Engine-emitted oracle corpus with honest provenance disclosure (oracle_provenance block per fixture). Class taxonomy: regulatory / engine-emitted / engine-emitted+xval — 0 / 8 / 12 of 20 in this corpus"
    - "Deterministic generator script (scripts/_generate_apr_oracle_fixtures.py) — single source of truth; re-run on annual cadence or after engine math changes"
    - "Wikipedia PV-form-collapse cross-validation: regular-monthly archetypes with no finance charges have the unit-period equation collapse to the standard PV form, so engine APR == nominal rate exactly is a genuine cross-validation against the Phase 1 anchor (algebraic identity)"
    - "Parametric-over-stems test pattern: @pytest.mark.parametrize over a list of fixture stems (mirrors Phase 5 oracle vs hand-calc test split per Plan 07-05 D-27)"
    - "Partial-closure precedent: this plan mirrors Phase 5 ARM-06 (Bankrate cross-source agreement deferred to Phase 8+ after human capture session). Phase 7 documents its analog in oracle/README.md and STATE.md for parent rollup"

key-files:
  created:
    - scripts/_generate_apr_oracle_fixtures.py
    - tests/fixtures/apr/oracle/README.md
    - tests/fixtures/apr/oracle/ffiec_001_30yr_150k_6_5.json
    - tests/fixtures/apr/oracle/ffiec_002_30yr_250k_6_5.json
    - tests/fixtures/apr/oracle/ffiec_003_30yr_400k_6_5.json
    - tests/fixtures/apr/oracle/ffiec_004_30yr_750k_6_5.json
    - tests/fixtures/apr/oracle/ffiec_005_30yr_1_2m_6_5.json
    - tests/fixtures/apr/oracle/ffiec_006_15yr_300k_5_0.json
    - tests/fixtures/apr/oracle/ffiec_007_15yr_300k_6_0.json
    - tests/fixtures/apr/oracle/ffiec_008_15yr_300k_7_0.json
    - tests/fixtures/apr/oracle/ffiec_009_15yr_300k_8_0.json
    - tests/fixtures/apr/oracle/ffiec_010_10yr_300k_6_5.json
    - tests/fixtures/apr/oracle/ffiec_011_10yr_500k_7_0.json
    - tests/fixtures/apr/oracle/ffiec_012_10yr_200k_5_5.json
    - tests/fixtures/apr/oracle/ffiec_013_30yr_300k_6_5_oddfp_5.json
    - tests/fixtures/apr/oracle/ffiec_014_30yr_300k_6_5_oddfp_10.json
    - tests/fixtures/apr/oracle/ffiec_015_30yr_300k_6_5_oddfp_20.json
    - tests/fixtures/apr/oracle/ffiec_016_15yr_500k_7_0_oddfp_15.json
    - tests/fixtures/apr/oracle/ffiec_017_30yr_400k_6_5_fc_5k.json
    - tests/fixtures/apr/oracle/ffiec_018_30yr_600k_7_5_fc_10k.json
    - tests/fixtures/apr/oracle/ffiec_019_15yr_250k_6_0_fc_3k.json
    - tests/fixtures/apr/oracle/ffiec_020_30yr_800k_7_0_fc_15k.json
  modified:
    - tests/test_apr.py

key-decisions:
  - "Autonomous-execution override accepted by project owner: ship 20 engine-emitted fixtures with honest provenance disclosure RATHER than block on a human capture session that has been deferred multiple times. Mirrors Phase 5 ARM-06 partial-closure precedent (Bankrate 5/1/7/1/10/1 + Vertex42 cross-source agreement deferred to Phase 8+ after human session)"
  - "Engine output of regular-monthly cases (no finance charges, no odd first period) is APR == nominal rate exactly (the unit-period equation collapses to the standard PV form via algebraic identity). 12 of the 20 corpus fixtures are this archetype; their expected values are CROSS-VALIDATED against the Phase 1 Wikipedia oracle anchor by identity, not by independent computation. The honest provenance class is 'engine-emitted, cross-validated against Wikipedia worked example'"
  - "Plan archetype substitutions (documented in oracle/README.md §Fallback Substitution Log): (1) 30/45/60-day odd-FP archetypes substituted with 5/10/15/20-day because 30+ violates D-16 boundary (f >= 1) per Plan 07-05 D-26 negative-path fixture; (2) 10-year balloon archetypes substituted with 10-year fully-amortizing fixed because v1 engine has no balloon construct (single payment_schedule entry); (3) multi-advance / construction-style archetypes substituted with regular-monthly + finance-charge variants because D-04 LOCKED max_length=1 forbids multi-advance in v1"
  - "Generator script's iterations_max = max(observed + 5, 10) gives every fixture generous headroom while still catching Newton-Raphson iteration regressions vs the snapshot. SC-3 global 50-iteration cap is also asserted independently in the parametric test"
  - "Each fixture's oracle_provenance block records class + captured_at + captured_by + engine_module + notes (and cross_validated_against when applicable). README.md per-fixture provenance table makes the disclosure scannable; future re-verifiers walk one table"

patterns-established:
  - "Engine-emitted oracle corpus pattern with honest provenance disclosure — when an external oracle is unreachable / deferred, ship engine-emitted fixtures with explicit provenance metadata rather than fabricate values OR block delivery. The oracle_provenance.class taxonomy (regulatory / engine-emitted / engine-emitted+xval) is the disclosure surface; the README's per-fixture table is the consumer surface; the generator script is the reproducibility surface"
  - "Wikipedia PV-form-collapse cross-validation as a 'free' cross-source — when the input combination has no finance charges and no odd first period, the unit-period equation reduces algebraically to the standard PV formula. Engine APR == nominal rate exactly THEN is a genuine cross-validation against any standard amortization oracle (Wikipedia, Bankrate, etc.) by identity, not by independent computation. This makes the 12 regular-monthly archetypes legitimately +xval class without requiring a fresh capture session"
  - "Partial-closure SUMMARY documents the gap honestly under §Partial Closure (Phase 5 ARM-06 precedent). STATE.md and ROADMAP.md note the partial-closure status for parent rollup. Future sessions know exactly what's left to do (HMDA Platform Docker container OR FFIEC APRWIN under Wine/VM OR CFPB Rate Spread Calculator captures for the 8 engine-emitted-only fixtures)"

requirements-completed:
  - APR-04  # 20+ oracle fixtures shipped + parametric test asserts engine within Decimal('0.00001'); partial closure per autonomous-execution override (8/20 fixtures await future external cross-validation)

# Metrics
duration: 5min 7s
completed: 2026-05-03
---

# Phase 7 Plan 7: FFIEC / Oracle Fixtures Summary

**Phase 7 Wave 7 (final wave) ships the 20-fixture oracle corpus + flips the 13th and final Wave-0 xfail stub.** Per the autonomous-execution override accepted by the project owner, the corpus is engine-emitted with honest provenance disclosure (`oracle_provenance` block on every fixture; per-fixture provenance table + capture protocol + partial-closure disclosure in `tests/fixtures/apr/oracle/README.md`). 12 of 20 fixtures are class `engine-emitted, cross-validated against Wikipedia worked example` (regular-monthly PV-form collapse identity); 8 of 20 are class `engine-emitted` (odd-first-period + finance-charge archetypes). A deterministic generator script (`scripts/_generate_apr_oracle_fixtures.py`) is the single source of truth for fixture regeneration on annual cadence. The parametric test `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` now sweeps 20 cases asserting `|engine - expected| <= Decimal("0.00001")` per CONTEXT D-09 + `iterations <= iterations_max` per fixture + `iterations <= 50` per SC-3. **All 13 Wave-0 stubs in `tests/test_apr.py` are now flipped (zero xfails remaining for APR-XX requirements).** Suite 502 passed / 4 skipped / 1 xfailed (was 482/4/2; +20 net pass / -1 xfail; the remaining 1 xfail is the Phase 5 ARM oracle deferral, NOT Phase 7). APR-04 closes partial-style; ROADMAP SC-2 closes partial-style.

## Performance

- **Duration:** ~5 min 7 s (estimated from session interactions)
- **Started:** 2026-05-03T23:12:40Z
- **Completed:** 2026-05-03T23:17:47Z
- **Tasks:** 3 atomic commits (Tasks 1-3 each mapped 1:1 to commits)
- **Files created:** 22 (1 generator script + 1 README + 20 fixtures)
- **Files modified:** 1 (`tests/test_apr.py`; +69 / -3)

## Accomplishments

- **Shipped 20 oracle fixtures** at `tests/fixtures/apr/oracle/ffiec_*.json` covering 5 archetype groups:
  - **5 × 30-year fixed at varying loan amounts** (`ffiec_001..005`): $150k, $250k, $400k, $750k, $1.2M @ 6.5% — all class `engine-emitted, cross-validated against Wikipedia worked example` (regular-monthly PV-form collapse identity; engine APR == nominal rate `0.065000` exactly)
  - **4 × 15-year fixed at varying rates** (`ffiec_006..009`): $300k @ 5.0% / 6.0% / 7.0% / 8.0% — class `engine-emitted+xval`; engine APR == nominal exactly
  - **3 × 10-year fixed** (`ffiec_010..012`): $300k @ 6.5%, $500k @ 7.0%, $200k @ 5.5% — class `engine-emitted+xval`; engine APR == nominal exactly. (Plan archetype said "10-year balloon" but v1 engine has no balloon construct; substitution documented in README §Fallback Substitution Log.)
  - **4 × odd-first-period long cases** (`ffiec_013..016`): 5, 10, 20, 15-day odd FPs — class `engine-emitted` (no public worked example with the exact input combination exists; future HMDA Platform Docker session would cross-validate). Engine APR drift from nominal: +0.0 / +0.000001 / +0.000002 / +0.000004 (correctly above nominal as required by the long-case sign-flip detector). (Plan archetype said 15/30/45/60-day but 30+ violates D-16; substitution documented.)
  - **4 × regular monthly with finance charges** (`ffiec_017..020`): $400k+5k / $600k+10k / $250k+3k / $800k+15k — class `engine-emitted`; APR drift above nominal: +0.001213 / +0.001725 / +0.001891 / +0.001886 (correctly above nominal because finance_charges reduces amount_financed without reducing total payment cost). (Plan archetype said multi-advance / construction; substituted because D-04 LOCKED forbids multi-advance in v1.)

- **Shipped `tests/fixtures/apr/oracle/README.md`** (234 lines) with:
  - **Partial Closure Disclosure** explaining the autonomous-execution override pivot from human FFIEC APRWIN capture → engine-emitted with honest provenance
  - Fixture schema documentation (the `oracle_provenance` block + class taxonomy)
  - Per-fixture provenance table (20 rows: class + cross-validated-against)
  - Provenance breakdown: 12/20 (60%) cross-validated against Wikipedia + 8/20 (40%) engine-emitted only + 0/20 regulatory-class
  - Fallback Substitution Log explaining D-16 / no-balloon / D-04-locked archetype substitutions
  - Refresh Cadence (annual; mirrors Phase 2 staleness convention)
  - Recommended Path to Full Closure (HMDA Platform Docker container > FFIEC APRWIN under Wine/VM > CFPB Rate Spread Calculator)
  - Cross-references to SC-1 anchor + parametric test + references doc + STATE.md / CONTEXT.md / 07-PLAN-CHECK.md

- **Shipped `scripts/_generate_apr_oracle_fixtures.py`** (516 lines) — deterministic regenerator. Single source of truth for the corpus. Re-run produces identical output bytes (modulo `CAPTURED_AT` constant) at any commit.

- **Flipped the 13th and final Wave-0 stub** — `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` now sweeps 20 parametric cases asserting:
  - `|response.estimated_apr - expected| <= Decimal("0.00001")` per CONTEXT D-09 (engine-is-wrong-on-divergence policy)
  - `response.iterations <= fix["expected"]["iterations_max"]` (catches Newton-Raphson iteration regressions vs the capture snapshot)
  - `response.iterations <= 50` (SC-3 global cap)
  - All 20 cases PASS

- **Suite count after:** 502 passed (was 482; +20 net pass exactly per the 20 new parametric cases) / 4 skipped (unchanged) / 1 xfailed (was 2; -1 corresponding to the Wave-0 stub flip; the remaining xfail is the Phase 5 ARM oracle Bankrate/Vertex42 deferral, NOT Phase 7) / 0 failed / 0 errors. Zero regression to Plan 07-06 baseline.

- **Lint/format/typecheck:** mypy --strict + ruff check + ruff format --check all clean on `scripts/_generate_apr_oracle_fixtures.py` and `tests/test_apr.py` (pre-commit hooks confirm).

## Partial Closure

**This plan closes APR-04 / ROADMAP SC-2 partial-style.** Mirrors Phase 5 ARM-06 partial-closure precedent (Bankrate 5/1, 7/1, 10/1 + Vertex42 cross-source agreement deferred to Phase 8+ after a human capture session).

### Closure metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Fixtures shipped | ≥ 20 | **20** ✓ |
| Provenance class: regulatory | (no target; aspirational) | 0 |
| Provenance class: engine-emitted, cross-validated | (no target) | 12 (60%) |
| Provenance class: engine-emitted only | (no target) | 8 (40%) |
| All fixtures pass solver within Decimal("0.00001") | yes | **yes** ✓ |
| `iterations <= iterations_max` per fixture | yes | **yes** ✓ |
| `iterations <= 50` (SC-3) per fixture | yes | **yes** ✓ |
| Wave-0 stub flipped | yes | **yes** ✓ |
| README documents capture protocol + provenance | yes | **yes** ✓ |
| README documents fallback substitutions | yes | **yes** ✓ |

### What couldn't be captured (and why)

- **8 fixtures are class `engine-emitted` only** (odd-first-period archetypes `ffiec_013..016` + finance-charge archetypes `ffiec_017..020`). For these input combinations, no public worked example with the exact same inputs exists in:
  - Reg Z Appendix J §(c) examples (covers J-1 / J-2 / J-3 / J-4 — none with these input shapes)
  - CFPB Loan Estimate worked examples ($162k @ 3.875%/30yr → $761.78 — single archetype)
  - Bankrate / Wikipedia worked examples ($200k @ 6.5%/30yr → $1,264.14 — regular-monthly only)
  - HMDA Platform documentation (the platform itself requires a stood-up Docker container, which was out of scope for this autonomous session)
  - FFIEC APRWIN (2008-era Windows desktop binary; would require Wine/VM session)
- **No FFIEC APRWIN screenshot SHAs are pinned** because no human capture session was performed in this plan. The original plan frontmatter envisioned screenshots; the autonomous override pivots away from this surface in favor of `oracle_provenance.captured_by: scripts/_generate_apr_oracle_fixtures.py` reproducibility.

### Recommended path to full closure

A future maintenance session could upgrade the 8 `engine-emitted` fixtures to `engine-emitted, cross-validated against <oracle>` by running ONE of:

1. **HMDA Platform Docker container** (highest value; CFPB-published reference implementation)
2. **FFIEC APRWIN under Wine / Windows VM** (lower value; 2008-era binary)
3. **CFPB Rate Spread Calculator web form** (web-based; free; lowest friction but covers a narrower input space)

The README.md §Recommended Path to Full Closure documents the exact upgrade procedure for each option (which fixture fields to update, what `class` value to bump to). Phase 8+ legacy backlog is the natural home for this work, alongside the Phase 5 ARM-06 cross-source agreement deferral.

## Task Commits

Each task committed atomically against `main` (sequential executor; no branching per `parallelization=false`; no AI attribution per global + project CLAUDE.md):

1. **Task 1 — Ship 20 oracle fixtures via deterministic generator** — `bee1417` (feat)
2. **Task 2 — Add oracle corpus README with provenance + partial-closure** — `c6e8fb0` (docs)
3. **Task 3 — Flip Wave-0 APR-04 stub to parametric over 20 fixtures** — `4dd4a42` (test)

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates):** committed at end of execution.

## Files Created/Modified

- `scripts/_generate_apr_oracle_fixtures.py` (**created**, 516 lines) — deterministic fixture regenerator
- `tests/fixtures/apr/oracle/README.md` (**created**, 234 lines) — provenance disclosure + capture protocol + recommended path to closure
- `tests/fixtures/apr/oracle/ffiec_001..ffiec_020.json` (**created**, 20 files) — the oracle corpus (avg ~30 lines/file)
- `tests/test_apr.py` (**modified**, +69 / -3 lines) — Wave-0 APR-04 stub flipped to `@pytest.mark.parametrize` over 20 stems

## Acceptance Gate Verification

| Gate | Plan target | Actual | Status |
|------|-------------|--------|--------|
| `ls tests/fixtures/apr/oracle/ffiec_*.json \| wc -l` | ≥ 20 | 20 | PASS |
| `tests/fixtures/apr/oracle/README.md` exists | yes | 234 lines | PASS |
| README has capture-protocol § | yes | §Provenance Classes + §Per-Fixture Provenance Table + §Fallback Substitution Log + §Refresh Cadence + §Recommended Path to Full Closure | PASS |
| `pytest tests/test_apr.py::test_apr_ffiec_oracle_fixtures_match_within_decimal_00001 -v` | PASS (≥20 cases) | 20 PASS | PASS |
| All 13 Wave-0 stubs flipped (zero xfails for APR-XX) | yes | yes (37 passed / 0 xfailed in `tests/test_apr.py`) | PASS |
| Full-suite `pytest -q` | ≥461 passed (executor floor) + 20 new = ≥481; actual baseline +20 | 502 passed / 4 skipped / 1 xfailed / 0 failed / 0 errors | PASS |
| `mypy --strict scripts/_generate_apr_oracle_fixtures.py tests/test_apr.py` | clean | clean | PASS |
| `ruff check scripts/_generate_apr_oracle_fixtures.py tests/test_apr.py` | clean | clean | PASS |
| `ruff format --check scripts/_generate_apr_oracle_fixtures.py tests/test_apr.py` | clean | clean | PASS |
| `iterations <= 50` per fixture (SC-3) | yes | yes (max observed: 2) | PASS |
| `iterations <= iterations_max` per fixture (snapshot guard) | yes | yes | PASS |

## Decisions Made

The plan's frontmatter said `autonomous: false` and the body called for human FFIEC APRWIN captures. The user accepted an explicit autonomous-execution override before this session: ship engine-emitted fixtures with honest provenance disclosure, target ≥ 20, document the gap honestly, and use the documented fallback chain per RESEARCH §Q(d).

Decisions made in service of the override:

- **Substituted plan archetype list (15/30/45/60-day odd FP) → (5/10/15/20-day odd FP)** because 30+ violates D-16 (f >= 1). The 45-day case is already covered as a NEGATIVE-path fixture by Plan 07-05 (`regz_appendix_j_odd_first_period_45_days.json`); v1 long-case fixtures must have f in [0, 1).
- **Substituted "10-year balloon" archetypes with 10-year fully-amortizing fixed** because v1 engine has no balloon construct (single payment_schedule entry; balloon would need a final lump-sum entry). Same short-term unit-period algebra exercised. True balloon support is on the v2 backlog.
- **Substituted "multi-advance / construction-style" archetypes with regular-monthly + finance-charge variants** because D-04 LOCKED constrains `APRRequest.advances` to `Field(min_length=1, max_length=1)` in v1. Finance-charge variants exercise the `amount_financed = principal − finance_charges` algebra (Reg Z §1026.18(b)) which is the orthogonal Phase 7 surface to multi-advance.
- **No fixture claims `regulatory` class** because no published value with the exact input combination was captured. The SC-1 anchor at `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` is the sole regulatory-class fixture in Phase 7 (Plan 07-05 D-25 LOCKED), and lives outside this `oracle/` subdirectory by design.
- **12 of 20 fixtures claim `engine-emitted, cross-validated against Wikipedia worked example`** because regular-monthly + no-finance-charges + no-odd-FP cases collapse the unit-period equation to the standard PV form by algebraic identity. Engine APR == nominal rate exactly THEN is a genuine cross-validation against the Phase 1 Wikipedia oracle anchor ($200k @ 6.5%/30yr → $1,264.14 monthly), not a circular self-validation.
- **`iterations_max = max(observed + 5, 10)`** per fixture in the generator script — gives every fixture generous headroom while still catching iteration-count regressions vs the snapshot. Independent of the SC-3 global 50-iteration cap (also asserted in the parametric test).

## Deviations from Plan

The autonomous-execution override IS a planned deviation (user-directed pre-execution), so the deltas below are documented for traceability rather than as Rule 1-3 inline fixes:

### Deviations from the original Plan 07-07 frontmatter (per autonomous-execution override)

**1. [Override - Plan reframing] FFIEC manual capture → engine-emitted with honest provenance**

- **Plan said:** `autonomous: false` + 20+ FFIEC APRWIN screenshots with SHA-256 hashes + human capture protocol
- **Override directed:** Ship engine-emitted fixtures with honest `oracle_provenance` block; target ≥ 20; document the gap; use fallback oracle chain per RESEARCH §Q(d)
- **Implementation:** 20 fixtures via `scripts/_generate_apr_oracle_fixtures.py`; per-fixture `oracle_provenance.class` discloses provenance class; README §Partial Closure documents the gap honestly
- **Closes:** APR-04 partial-style; ROADMAP SC-2 partial-style
- **Recommended next step:** Phase 8+ legacy backlog session stands up HMDA Platform Docker container OR FFIEC APRWIN under Wine/VM and upgrades the 8 `engine-emitted` fixtures to `engine-emitted, cross-validated against <oracle>` (per README §Recommended Path to Full Closure)

**2. [Override - Plan archetype substitution] D-16 / no-balloon / D-04 boundary substitutions**

- **Plan said:** archetypes including 30/45/60-day odd-FP, 10-year balloon, multi-advance/construction
- **Engine boundaries:** D-16 rejects f >= 1 (30+ days odd-FP); v1 has no balloon construct; D-04 LOCKED max_length=1 forbids multi-advance
- **Implementation:** substituted with 5/10/15/20-day odd-FP, 10-year fully-amortizing, regular-monthly + finance-charge variants
- **Documentation:** README §Fallback Substitution Log + this SUMMARY §Decisions Made
- **Closes:** same APR-04 surface area in a v1-compliant manner

### No Rule 1/2/3 inline fixes

The plan executed exactly as the override directed. No bugs found in shipped code; no missing critical functionality (the corpus is functional and all gates pass); no blocking issues. ruff format auto-applied 1 reformat at Task 1 (mechanical hygiene; pre-commit hook handled it transparently).

**Total deviations:** 2 (both are planned, user-directed overrides documented above; no Rule 1-3 inline fixes).

## Issues Encountered

None — all 3 task commits executed sequentially, no checkpoints, no escalations, no auth gates, no blocking errors. The autonomous-execution override eliminated the human-capture checkpoint that would otherwise have been hit at Task 1.

## Threat Flags

None — Plan 07-07 ships 22 read-only files (1 generator script + 1 README + 20 JSON fixtures) plus 1 test-file edit. The generator script is a dev-only one-shot (not imported anywhere; not in the production code path); the JSON fixtures are read-only data; the README is documentation. No new code paths in `lib/`, no network surface, no auth boundary, no schema changes at trust boundaries, no new third-party dependencies, no untracked file generation. The fixtures live under `tests/fixtures/apr/oracle/` and are loaded by the existing `apr_fixture` fixture factory (Plan 07-00) via the `oracle/<stem>` addressing convention (no `conftest.py` modification).

## Known Stubs

None introduced this wave. The pre-existing inline-stub status (3 inline-constructed-input tests carried forward from Plan 07-04 SUMMARY's "Known Stubs" list) is unchanged; those are hygiene-only refactors and were explicitly not in this plan's scope.

**Zero xfails remain in `tests/test_apr.py` for any APR-XX requirement.** All 13 Wave-0 stubs are now flipped (Plan 07-01 flipped 1; Plan 07-02 flipped 4; Plan 07-04 flipped 5; Plan 07-05 flipped 2; Plan 07-06 flipped 1; **Plan 07-07 flipped the final 1**).

The only xfailed test in the full project suite is `tests/test_arm.py::test_oracle_cross_validation_5_1` — a Phase 5 ARM oracle deferral (Bankrate / Vertex42), unrelated to Phase 7.

No mock/placeholder data introduced. No `FIXME` comments. No hardcoded empty values that flow to UI rendering.

## User Setup Required

None — no external service configuration, no environment variables, no manual capture, no human-in-the-loop verification. All 3 tasks executed autonomously per the override.

The `scripts/_generate_apr_oracle_fixtures.py` regenerator is dev-only; users / consumers don't run it. Annual refresh is the maintainer's responsibility (per oracle/README.md §Refresh Cadence).

## Cross-wave Dependency Notes (forward)

- **Phase 8 (stress-points)** — `solve_apr` continues to be the integration point. The 20-fixture oracle corpus is now part of the regression baseline; Phase 8 stress-test parameter sweeps will indirectly exercise these fixtures via solve_apr per grid cell. Any engine drift > Decimal("0.00001") on the 20 corpus members will fail the parametric test loudly per CONTEXT D-09.
- **Phase 8+ legacy backlog** — addition: stand up HMDA Platform Docker container OR FFIEC APRWIN under Wine/VM and upgrade the 8 `engine-emitted` fixtures (`ffiec_013..020`) to `engine-emitted, cross-validated against <oracle>`. Mirrors the Phase 5 ARM oracle backlog item (Bankrate 5/1, 7/1, 10/1 + Vertex42 captures).
- **Phase 10 (Claude skill)** — fixtures will move with the test suite if the Phase 10 relocation includes them; otherwise the existing `apr_fixture` factory + relative-path lookup keeps them addressable. The `oracle/<stem>` addressing convention works inside the skill folder transparently. No Phase 10 work required from this plan.
- **Requirement closure status:** Plan 07-07 closes **APR-04** partial-style (20 oracle fixtures shipped + parametric test asserts engine within Decimal('0.00001'); 8 fixtures await future external cross-validation). **All Phase 7 requirements (APR-01..APR-08) are now closed.** ROADMAP SC-1 (Plan 07-05), SC-2 (this plan, partial), SC-3 (Plan 07-05), SC-4 (Plan 07-04), SC-5 (Plan 07-06) — all closed.

## TDD Gate Compliance

The plan does not declare `type: tdd`; this is a vanilla `type: execute-with-human-checkpoint` plan executed autonomously per the override. Per the executor protocol's TDD section, no RED/GREEN/REFACTOR cycle gate enforcement is required. For traceability: the stub flip in Task 3 is a RED → GREEN transition of the pre-existing Wave-0 xfail stub. The flip removes the `@pytest.mark.xfail(strict=True)` decorator (the RED gate marker per Wave-0's stub-then-flip pattern) and replaces the `pytest.fail("Wave 0 stub")` body with real parametric assertions that PASS against the 20 fixtures shipped in Tasks 1-2 (the GREEN gate). No REFACTOR pass needed — the test as written is canonical against ruff format.

## Self-Check: PASSED

Verified at execution end:

- [x] All 22 created files exist at paths declared in plan frontmatter:
  - `scripts/_generate_apr_oracle_fixtures.py` — present (516 lines)
  - `tests/fixtures/apr/oracle/README.md` — present (234 lines)
  - `tests/fixtures/apr/oracle/ffiec_001..020*.json` — 20 files present
- [x] `tests/test_apr.py` modified — Wave-0 APR-04 stub flipped (no `@pytest.mark.xfail` decorator on `test_apr_ffiec_oracle_fixtures_match_within_decimal_00001`; body replaced with `@pytest.mark.parametrize` over 20 stems)
- [x] `git log --oneline | grep bee1417` (Task 1 generator + 20 fixtures) → present
- [x] `git log --oneline | grep c6e8fb0` (Task 2 README) → present
- [x] `git log --oneline | grep 4dd4a42` (Task 3 stub flip) → present
- [x] All three task commits reachable from `main`
- [x] No commit message contains "Co-Authored-By", "Claude", "Generated with", or any AI attribution (verified by `git log --format='%B' bee1417 c6e8fb0 4dd4a42` inspection — solely-authored as repo owner per global + project CLAUDE.md)
- [x] All plan acceptance gates PASS (see Acceptance Gate Verification table above)
- [x] `pytest tests/test_apr.py::test_apr_ffiec_oracle_fixtures_match_within_decimal_00001 -v` → 20 PASS
- [x] Full apr suite: 37 passed / 0 xfailed (was 17/1 pre-Wave-7; +20 net pass / -1 xfail)
- [x] Full project suite: 502 passed / 4 skipped / 1 xfailed / 0 failed / 0 errors (was 482+4+2; +20 net pass / -1 xfail; zero regression to Plan 07-06 baseline of 482)
- [x] mypy --strict + ruff check + ruff format --check all clean on `scripts/_generate_apr_oracle_fixtures.py` and `tests/test_apr.py` (pre-commit hooks confirm)
- [x] APR-04 closes per `requirements-completed` frontmatter (verified via the parametric test sweep end-to-end through 20 oracle fixtures; engine within Decimal('0.00001') of pinned values for all 20)
- [x] All 13 Wave-0 stubs flipped (verified: 0 xfail remain in `tests/test_apr.py`; the only project-wide xfail is `tests/test_arm.py::test_oracle_cross_validation_5_1` which is Phase 5 ARM-06 deferral, NOT Phase 7)
- [x] Phase 7 complete: APR-01 (Plan 07-01) + APR-02 (Plan 07-02) + APR-03 (Plan 07-02 / 07-03) + APR-04 (this plan, partial) + APR-05 (Plan 07-05) + APR-06 (Plan 07-04) + APR-07 (Plan 07-04) + APR-08 (Plan 07-06) — all 8 requirements closed; Phase 7 closes 8/8 plans

---
*Phase: 07-estimated-apr*
*Completed: 2026-05-03*
*Final wave; closes Phase 7*
