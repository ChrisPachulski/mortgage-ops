---
phase: 01-foundations-money-discipline
plan: 05
status: complete
requirements:
  - FND-09
completed_date: 2026-04-26
---

# Phase 01 Plan 05: Golden P&I Fixture Set + Schema Tests — Summary

Shipped `tests/fixtures/golden_pmt.json` (4 immutable monthly P&I oracles) and `tests/test_fixtures.py` (10 schema + pinned-value tests). The four pinned `expected_monthly_pi` values — 1264.14, 761.78, 2528.27, 1797.66 — are the immutable contract Phase 3's `lib/amortize.py` must satisfy with exact Decimal equality (no `pytest.approx`). Plan 01's `golden_fixture` loader is dogfooded end-to-end against the real file; Phase 3+ must consume it (no parallel loader). FND-09 satisfied.

## Status

**COMPLETE.** All 6 `must_haves.truths` verified. All `success_criteria` met. Both planned tasks executed and committed atomically. Wave-1 phase gate (`uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest`) exits 0 with 33/33 tests passing.

## Files Created

| Path | Purpose | Tests/Lines |
|------|---------|-------------|
| `tests/fixtures/golden_pmt.json` | 4 pinned monthly P&I oracles (FND-09 contract) — Wikipedia $200k/6.5%/30yr → $1,264.14; CFPB LE $162k/3.875%/30yr → $761.78; computed $400k/6.5%/30yr → $2,528.27; computed $200k/7%/15yr → $1,797.66 | 4 fixtures, 8 fields each |
| `tests/test_fixtures.py` | Schema + pinned-value tests; dogfoods Plan 01's `golden_fixture` loader | 10 tests |

## Files Modified

None — both files are net-new.

## Commits Made

| SHA | Subject |
|-----|---------|
| `ae6068d` | `feat(01-05): add golden_pmt.json — 4 pinned monthly P&I oracles (FND-09)` |
| `a93a06e` | `test(01-05): add tests/test_fixtures.py — schema + pinned-value assertions (FND-09)` |

(A third commit will land for this SUMMARY.md.)

## Fixture Schema (immutable, 8 required fields)

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `id` | string | `"wikipedia_200k_30yr"` | Unique key; loader matches on this |
| `source` | string | `"https://en.wikipedia.org/wiki/Mortgage_calculator"` | URL or in-tree provenance note |
| `principal` | **string** | `"200000.00"` | Decimal-safe round-trip |
| `annual_rate` | **string** | `"0.065000"` | Decimal-safe; 6 decimal places |
| `term_months` | integer | `360` | JSON number, not string |
| `expected_monthly_pi` | **string** | `"1264.14"` | The immutable pinned value |
| `rounding` | string | `"ROUND_HALF_UP"` | Pinned literal across all fixtures |
| `notes` | string | `"Wikipedia worked example..."` | Provenance commentary |

All money/rate values are JSON strings so `Decimal(s)` reads them losslessly. `term_months` is the only numeric type.

## The Four Pinned Oracles (immutable contract)

| ID | Principal | Annual Rate | Term | Expected Monthly P&I |
|----|-----------|-------------|------|----------------------|
| `wikipedia_200k_30yr` | $200,000.00 | 6.5000% | 360 mo | **$1,264.14** |
| `cfpb_le_162k_30yr` | $162,000.00 | 3.8750% | 360 mo | **$761.78** |
| `computed_400k_30yr` | $400,000.00 | 6.5000% | 360 mo | **$2,528.27** |
| `computed_200k_15yr` | $200,000.00 | 7.0000% | 180 mo | **$1,797.66** |

These four values are independently re-derived in `01-RESEARCH.md` A1 (line 514). They are NOT recomputed at execution time — they are the contract Phase 3 must satisfy with exact equality.

## Must-Haves Verification

### `must_haves.truths`

| Truth | Result | Evidence |
|-------|--------|----------|
| `tests/fixtures/golden_pmt.json` contains exactly 4 fixtures with IDs `wikipedia_200k_30yr`, `cfpb_le_162k_30yr`, `computed_400k_30yr`, `computed_200k_15yr` | **PASS** | `jq '.fixtures \| length'` → `4`; `jq -r '.fixtures[].id'` → exact 4 IDs in order |
| Each fixture's `expected_monthly_pi` is the immutable pinned value: `1264.14`, `761.78`, `2528.27`, `1797.66` | **PASS** | `jq -r '.fixtures[] \| "\(.id): \(.expected_monthly_pi)"'` printed all four pinned values verbatim |
| Each fixture has all 8 required fields: `id`, `source`, `principal`, `annual_rate`, `term_months`, `expected_monthly_pi`, `rounding`, `notes` | **PASS** | `jq -r '.fixtures[] \| keys'` shows the same 8-field set on each of the 4 records |
| Each fixture's `rounding` field equals literal string `"ROUND_HALF_UP"` | **PASS** | `jq -r '.fixtures[].rounding' \| sort -u` → single value `ROUND_HALF_UP` |
| All money/rate values in the JSON are strings (Decimal-safe round-trip) | **PASS** | `jq '.fixtures[0].principal \| type'` → `"string"`; same for `annual_rate` and `expected_monthly_pi` across all 4 fixtures (single unique result `string`); `term_months` correctly stays `number` |
| The conftest.py `golden_fixture` loader (Plan 01) successfully loads each by id | **PASS** | `tests/test_fixtures.py::test_conftest_golden_fixture_loader_finds_each_id` passes; iterates the 4 EXPECTED_IDS and asserts each loaded record's `id` field matches |

### `must_haves.artifacts`

| Path | Provides | Verified |
|------|----------|----------|
| `tests/fixtures/golden_pmt.json` | Four pinned monthly P&I oracles | **PASS** — file exists, valid JSON, contains `wikipedia_200k_30yr` |
| `tests/test_fixtures.py` | Schema + pinned-value assertions on golden_pmt.json | **PASS** — file exists, contains `expected_monthly_pi`, 10 tests pass |

### `must_haves.key_links`

| Link | Verified |
|------|----------|
| `tests/test_fixtures.py` → `tests/fixtures/golden_pmt.json` via `Path(__file__).parent / "fixtures" / "golden_pmt.json"` | **PASS** — `FIXTURE_PATH` constant; tests read it directly |
| `tests/test_fixtures.py` → `tests/conftest.py::golden_fixture` (dogfooding Plan 01 loader) | **PASS** — two tests consume the `golden_fixture` fixture by parameter injection |
| `tests/fixtures/golden_pmt.json` → `lib/amortize.py` (Phase 3) via `expected_monthly_pi` | **DEFERRED** — Phase 3 will compute and assert exact equality; the contract is locked here |

### Wave-1 Phase Gate (from `<verification>`)

| Command | Result |
|---------|--------|
| `uv run ruff check .` | exit 0 — `All checks passed!` |
| `uv run ruff format --check .` | exit 0 — `10 files already formatted` |
| `uv run mypy --strict .` | exit 0 — `Success: no issues found in 10 source files` |
| `uv run pytest` | exit 0 — `33 passed in 0.07s` |

Test count target was 33 (1 smoke + 8 money + 14 models + 10 fixtures). Achieved exactly 33/33.

## Deviations from Plan

### 1. [Rule 1 — Bug] Plan's literal `tests/test_fixtures.py` content failed ruff `SIM300` + `UP035`/`TC003`

- **Found during:** Task 2 verify (`uv run ruff check tests/test_fixtures.py`)
- **Issue:** The plan's literal source had two ruff violations against the project's own ruff `select` set:
  1. `SIM300` (Yoda condition): `assert REQUIRED_FIELDS <= fx.keys()` — ruff prefers `assert fx.keys() >= REQUIRED_FIELDS`.
  2. `UP035` + `TC003`: `from typing import ... Callable` triggers `UP035` (Callable is in `collections.abc` per Python 3.9+); once moved, it's annotation-only with `from __future__ import annotations` in effect, so `TC003` requires a `TYPE_CHECKING` import.
- **Fix:** (1) Flipped the comparison to `fx.keys() >= REQUIRED_FIELDS`. (2) Imported `Callable` inside `if TYPE_CHECKING:` (mirrors Plan 01's identical fix to `tests/conftest.py`). Same runtime behavior, same test semantics, ruff-clean and mypy-clean.
- **Files modified:** `tests/test_fixtures.py`
- **Commit:** `a93a06e` (the fix landed before commit; never an intermediate broken commit)

This is the same class of deviation Plan 01 logged for `tests/conftest.py` — the plan's literal Python content predates the project's ruff config. No semantic change; the contract `REQUIRED_FIELDS ⊆ fx.keys()` is preserved verbatim.

## Authentication Gates

None.

## Threat Flags

None — no new security-relevant surface introduced beyond what the plan's `<threat_model>` already enumerated. T-1-20 (silent value tampering) is mitigated by `test_pinned_expected_values`; T-1-21 (schema drift) by `test_golden_pmt_each_fixture_well_formed`; T-1-22 (loader collision) by uniqueness of EXPECTED_IDS frozenset.

## Forward Notes

- **Phase 3 (`lib/amortize.py` + `tests/test_amortize.py`):** Compute monthly P&I against each of the 4 fixtures and assert exact Decimal equality (NEVER `pytest.approx` for money). The contract is locked here — if Phase 3's computed value disagrees with any pinned `expected_monthly_pi`, Phase 3 is wrong, not the fixture.
- **Phase 3+ loader convention:** Use `tests/conftest.py::golden_fixture` (the canonical loader). Do not roll a per-phase loader. Plan 01 ships it; Plan 05 dogfoods it; downstream tests consume it.
- **Future fixture additions (e.g., ARM, biweekly):** New fixture files (`golden_arm.json`, etc.) should follow the same 8-field schema convention and be loaded via a parallel fixture in `conftest.py`. Do not extend `golden_pmt.json` with non-P&I data.

## Self-Check: PASSED

- `tests/fixtures/golden_pmt.json` exists, tracked in git, valid JSON
- `tests/test_fixtures.py` exists, tracked in git
- Commit `ae6068d` (golden_pmt.json) present in `git log`
- Commit `a93a06e` (test_fixtures.py) present in `git log`
- Wave-1 phase gate exits 0 (33/33 tests, mypy --strict clean, ruff clean, ruff format clean)
- All 6 `must_haves.truths` independently verified via `jq` and pytest
