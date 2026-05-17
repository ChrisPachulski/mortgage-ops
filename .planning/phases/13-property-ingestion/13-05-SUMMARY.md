---
phase: 13-property-ingestion
plan: 05
subsystem: duckdb-persistence
tags: [phase-13, wave-5, duckdb, analyzed-listings, persistence, lockfile, prop-02, pers-08, d-13-reanalysis-01, q4-default]
dependency_graph:
  requires:
    - "Phase 13 Wave 0 scaffolding (tests/test_property_persistence.py xfail scaffold + pyproject mypy override)"
    - "Phase 13 Wave 1 lib.property_listing.PropertyListing + ProvenancedMoney (Plan 13-01)"
    - "Phase 12 lib.fred_cache.with_cache_lock (lockfile primitive)"
    - "Phase 9 orchestration/lockfile.mjs (Node writer counterpart serializing on data/.lock)"
    - "duckdb >= 1.4 runtime dependency (already promoted in Wave 0)"
    - "freezegun dev dep (already in pyproject.toml + .pre-commit-config.yaml as of this plan)"
  provides:
    - "lib.property_persistence.write_listing(listing, household_hash, db_path) -> None"
    - "lib.property_persistence.read_latest_for_zpid(zpid, db_path) -> PropertyListing | None"
    - "lib.property_persistence.compute_household_hash(household_yml, profile_yml, mortgage30us_value) -> str"
    - "lib.property_persistence._ensure_schema(con) -> None"
    - "lib.property_persistence.DB_PATH constant (data/mortgage-ops.duckdb)"
    - "lib.property_persistence.SCHEMA_VERSION = 1"
    - "lib.property_persistence.CREATE_TABLE_SQL with composite PK + 3 indexes"
    - "tests/test_property_persistence.py 16 live tests (PROP-02 + PERS-08 closed at unit-test layer)"
  affects:
    - "Plan 13-04 (CLI): scripts/property_fetch.py may import write_listing on the success path (planner's call; not a hard dependency)"
    - "Plan 13-06 (integration): end-to-end URL -> DuckDB round-trip can use write_listing + read_latest_for_zpid"
    - "Phase 14 (analysis): every analysis run inserts a new (zpid, analyzed_at) row; reads via read_latest_for_zpid or future get_history_for_zpid helper"
    - "Phase 15 (property mode): persisted listings are queryable for re-analysis / watchlist views"
tech_stack:
  added:
    - "lib.property_persistence module (DuckDB writer/reader + household_hash)"
  patterns:
    - "Composite PK (zpid, analyzed_at) for append-only re-analysis history (D-13-REANALYSIS-01)"
    - "Lazy `import duckdb` inside function bodies (D-18 fast --help discipline; analog: scripts/fred_cli.py)"
    - "TYPE_CHECKING-guarded `from lib.property_listing import PropertyListing` (runtime import inside read_latest_for_zpid)"
    - "with_cache_lock(db_path.parent) -- lock-dir matches Phase 9 Node writer's data/.lock"
    - "freezegun microsecond-delta composite-PK test (proves TIMESTAMP precision splits PK)"
    - "CR-01 defensive idiom: malformed listing_json -> broad-except -> None (mirrors Phase 12 fred_cache._load_cache)"
    - "Pitfall 14 defense: read-only conn cannot run DDL -> catch duckdb.CatalogException, return None"
    - "Content-SHA256 household_hash (hashlib.sha256 over 2 YAML files + rate string; Q4 default)"
key_files:
  created:
    - "lib/property_persistence.py"
    - ".planning/phases/13-property-ingestion/13-05-SUMMARY.md"
  modified:
    - "tests/test_property_persistence.py"
    - "pyproject.toml"
    - ".pre-commit-config.yaml"
    - ".planning/REQUIREMENTS.md"
decisions:
  - "Composite PK (zpid, analyzed_at) verbatim per D-13-REANALYSIS-01: re-analysis APPENDS new rows; never overwrites. Tested via freezegun microsecond-delta."
  - "Lock-dir = db_path.parent (data/), NOT a subdirectory. This serializes Python writes against the Phase 9 Node writer (orchestration/db-write.mjs uses the same data/.lock). Asserted via lockfile spy test."
  - "Native DuckDB JSON column for listing_json + analysis_json (NOT VARCHAR). Enables ->> operators for Phase 14 query convenience."
  - "household_hash uses hashlib.sha256 over (household.yml bytes + profile.yml bytes + MORTGAGE30US value bytes). Content hash chosen over structural per Q4 default rationale; whitespace edits produce a different hash (acceptable since analyzed_listings is append-only)."
  - "read_latest_for_zpid never raises to caller: 4 None-return cases (missing DB file, missing table via CatalogException, unknown zpid, malformed listing_json). Inherits CR-01 defensive idiom from Phase 12 fred_cache."
  - "Lazy `import duckdb` inside write_listing + read_latest_for_zpid bodies (D-18 fast --help). NO top-level duckdb import."
  - "TYPE_CHECKING-guarded PropertyListing import at module top + runtime import inside read_latest_for_zpid avoids any circular-import surface (property_listing has no upward deps on persistence today, but the lazy-import discipline is the standing rule)."
  - "schema_version = 1 pinned at module level for forward migration discipline; v1.2 will write _migrate_v2() and bump."
metrics:
  duration_minutes: 4
  completed_date: "2026-05-16"
  tasks_completed: 2
  files_changed: 5
  loc_added: 157  # lib/property_persistence.py
  tests_added: 16  # 16 live tests (was 7 strict-xfail stubs)
  xfails_flipped: 7  # all Wave-0 PERS-08 + PROP-02 stubs
---

# Phase 13 Plan 05: DuckDB Persistence Summary

One-liner: PROP-02 + PERS-08 close via 157-LOC `lib/property_persistence.py`
shipping `write_listing` + `read_latest_for_zpid` + `compute_household_hash`
+ `_ensure_schema` against the `analyzed_listings` table with composite PK
`(zpid, analyzed_at)` per D-13-REANALYSIS-01, 3 indexes, JSON columns,
schema_version=1, all wrapped in `with_cache_lock(db_path.parent, ...)` so
Python writes serialize against the Phase 9 Node writer on the same
`data/.lock`. 16 live tests (was 7 xfail stubs) prove schema idempotence,
round-trip equality, microsecond-delta append, ORDER BY DESC latest, lockfile
acquisition at db_path.parent, CR-01 malformed-row defense, missing-table
CatalogException defense, and 4 household_hash properties (shape +
determinism + sensitivity to household + sensitivity to rate).

## What Shipped

### Task 1 - `lib/property_persistence.py` (commit `91c7c7d`)

157 LOC. Four functions, three module constants, one CREATE_TABLE_SQL literal
with PK + 3 indexes, two lazy `import duckdb` sites, one outer
`with_cache_lock` wrap on the writer, one defensive double-try in the reader.

**Public API:**

| Symbol | Type | Purpose |
| ------ | ---- | ------- |
| `write_listing(listing, household_hash, db_path=DB_PATH)` | `(PropertyListing, str, Path) -> None` | INSERT row under data/.lock; lazy duckdb import; auto-`_ensure_schema` |
| `read_latest_for_zpid(zpid, db_path=DB_PATH)` | `(str, Path) -> PropertyListing \| None` | SELECT latest by analyzed_at DESC; 4 None-return cases |
| `compute_household_hash(household_yml, profile_yml, mortgage30us_value)` | `(Path, Path, str) -> str` | 64-char hex SHA256 over the 3 inputs that affect verdict |
| `_ensure_schema(con)` | `(duckdb.Connection) -> None` | Idempotent DDL (IF NOT EXISTS) - table + 3 indexes |
| `DB_PATH` | `Final[Path]` | `data/mortgage-ops.duckdb` relative to repo root |
| `SCHEMA_VERSION` | `Final[int] = 1` | Pinned migration anchor |
| `CREATE_TABLE_SQL` | `Final[str]` | Composite PK + JSON columns + 3 indexes |

**Schema literals (CREATE_TABLE_SQL):**

```sql
CREATE TABLE IF NOT EXISTS analyzed_listings (
    zpid            VARCHAR     NOT NULL,
    analyzed_at     TIMESTAMP   NOT NULL,
    source_url      VARCHAR     NOT NULL,
    listing_json    JSON        NOT NULL,
    analysis_json   JSON,
    verdict         VARCHAR,
    household_hash  VARCHAR     NOT NULL,
    schema_version  INTEGER     NOT NULL DEFAULT 1,
    PRIMARY KEY (zpid, analyzed_at)
);
CREATE INDEX IF NOT EXISTS idx_listings_zpid ON analyzed_listings(zpid);
CREATE INDEX IF NOT EXISTS idx_listings_verdict ON analyzed_listings(verdict);
CREATE INDEX IF NOT EXISTS idx_listings_analyzed_at ON analyzed_listings(analyzed_at DESC);
```

**Failure-mode map (read_latest_for_zpid -> None):**

| Cause | Caught by |
| ----- | --------- |
| `db_path` does not exist | `if not db_path.exists(): return None` |
| Table `analyzed_listings` does not exist | `except duckdb.CatalogException` (Pitfall 14) |
| Zpid has no matching rows | `if row is None: return None` |
| `listing_json` is corrupted / missing fields | `except Exception` around `PropertyListing.model_validate_json` (CR-01) |

**Hard constraints honored:**

- `import duckdb` is lazy (inside `write_listing` + `read_latest_for_zpid` bodies).
  Verified: `grep -E '^import duckdb' lib/property_persistence.py` returns no match.
- `from lib.fred_cache import with_cache_lock` is at module top (Phase 12 already
  validated as a fast import).
- `TYPE_CHECKING` guards the top-level `PropertyListing` import; the runtime
  import lives inside `read_latest_for_zpid` for lazy-import discipline.
- `_now_utc()` returns `datetime.now(UTC)` -- microsecond precision is critical
  for D-13-REANALYSIS-01 PK splitting.
- `_ensure_schema()` runs the multi-statement CREATE_TABLE_SQL as a single
  execute call (DuckDB processes multi-statement strings).
- Both `with_cache_lock` and the duckdb connection follow try/finally to
  guarantee close + lock release.
- `read_latest_for_zpid` checks `db_path.exists()` BEFORE connecting (DuckDB's
  `read_only=True` on a non-existent file behavior varies by version -- explicit
  check is the safe path).
- `compute_household_hash` uses stdlib `hashlib.sha256` (CLAUDE.md V6 crypto rule:
  never hand-roll).
- No retries on lock acquisition beyond what `with_cache_lock` provides (5s
  acquire timeout, 60s stale recovery -- Phase 12 defaults).

**pyproject.toml diff:** removed the `[[tool.mypy.overrides]] module =
"lib.property_persistence"` entry. With Plan 13-03 having already cleared
`lib.property_extractor`, the entire Wave 0 override block is now empty and
was deleted (4-line removal). This is the last Phase 13 mypy stub override --
all 4 `lib.property_*` modules now ship.

### Task 2 - `tests/test_property_persistence.py` (commit `0733a71`)

16 live tests; 7 Wave-0 strict-xfail markers removed; freezegun used for
microsecond-delta composite-PK proof.

**Test inventory:**

| # | Test | Asserts |
| - | ---- | ------- |
| 1 | `test_ensure_schema_creates_table_and_indexes` | `_ensure_schema` creates 1 table + 3 indexes via `duckdb_indexes()`; idempotent on second call |
| 2 | `test_schema_has_composite_pk_in_sql` | `"PRIMARY KEY (zpid, analyzed_at)"` literal present in CREATE_TABLE_SQL (D-13-REANALYSIS-01) |
| 3 | `test_schema_version_is_one` | SCHEMA_VERSION == 1 pinned |
| 4 | `test_round_trip_write_read` | PROP-02: byte-equal model returned after write_listing -> read_latest_for_zpid |
| 5 | `test_read_latest_returns_none_on_missing_db_file` | Non-existent path -> None (not FileNotFoundError) |
| 6 | `test_read_latest_returns_none_on_missing_table` | Pitfall 14: CatalogException on missing table -> None |
| 7 | `test_read_latest_returns_none_on_unknown_zpid` | Table populated, zpid absent -> None |
| 8 | `test_composite_pk_allows_reanalysis_with_microsecond_delta` | freezegun 1us delta -> 2 rows for same zpid (D-13-REANALYSIS-01 proof) |
| 9 | `test_read_latest_returns_most_recent_when_multiple_rows` | ORDER BY analyzed_at DESC returns the later row |
| 10 | `test_malformed_listing_json_falls_through` | CR-01: corrupted listing_json -> None (not ValidationError) |
| 11 | `test_write_acquires_data_lock` | Lockfile spy proves `cache_dir == db.parent` (NOT a subdir) |
| 12 | `test_compute_household_hash_is_sha256_hex` | Q4: 64-char hex SHA256 shape |
| 13 | `test_compute_household_hash_is_deterministic` | Same inputs -> identical digest |
| 14 | `test_compute_household_hash_changes_on_household_edit` | Single-byte household.yml edit -> different digest |
| 15 | `test_compute_household_hash_changes_on_rate_edit` | MORTGAGE30US value edit -> different digest |
| 16 | `test_db_path_points_to_data_mortgage_ops_duckdb` | DB_PATH default = `data/mortgage-ops.duckdb` |

**Final pytest:** `16 passed in 0.21s` on `tests/test_property_persistence.py`.
Zero xfail, zero XPASS, zero failed, zero error.

**Full-suite regression:** `716 passed, 6 skipped, 11 xfailed, 2 failed`.
The +16 against the Plan 13-03 baseline (700 passed) is exactly the new
tests; the 2 failed are the pre-existing `test_citation_coverage*[fha_mip]`
baseline failures from the unstaged dirty `lib/rules/fha_mip.py` (out of scope
per executor constraints; same baseline as Plan 13-01/02/03 SUMMARIES). The 11
xfailed are the Wave-4 stubs in `tests/test_property_fetch.py` (Plan 13-04
not yet executed). Zero regression vs Plan 13-03 baseline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Lint config alignment] Plan-prescribed `noqa: BLE001` removed by ruff RUF100**

- **Found during:** Task 1 pre-commit ruff hook.
- **Issue:** The PLAN's `<action>` block specifies `except Exception:  # noqa:
  BLE001 -- CR-01 defensive (Phase 12 fred_cache idiom)` on the malformed-JSON
  defense in `read_latest_for_zpid`. The project's ruff config selects only
  `E, F, W, I, UP, B, SIM, RUF, TCH, PT` (pyproject.toml:46-56); `BLE` is NOT
  enabled, so the noqa directive is unused. ruff `RUF100` ("Unused noqa")
  auto-strips it. This exactly matches the Plan 13-03 Rule 3 deviation
  (Task 1 there had the identical interaction).
- **Fix:** Allowed ruff's --fix to drop the `# noqa: BLE001` token; the
  load-bearing CR-01 comment is retained. The doctrine is preserved; the
  linter just has no rule to suppress.
- **Files modified:** `lib/property_persistence.py` (comment form only;
  semantic behavior unchanged).
- **Commit:** `91c7c7d` (bundled into Task 1's commit after pre-commit
  auto-fix).

**2. [Rule 3 - Pre-commit hook alignment] freezegun missing from pre-commit mypy additional_dependencies**

- **Found during:** Task 2 commit attempt (pre-commit mypy failure
  `Cannot find implementation or library stub for module named "freezegun"`).
- **Issue:** Pre-commit runs mypy in a clean per-hook environment with only
  the `additional_dependencies` listed in `.pre-commit-config.yaml`. freezegun
  is already in `pyproject.toml` dev deps (used by `tests/test_fred_cache.py`)
  but was never propagated into the pre-commit hook env. The hook had not
  fired on freezegun-using tests before this plan because `test_fred_cache.py`
  doesn't trigger annotation-resolution paths for the `freezegun` symbol
  (it only calls `freezegun.freeze_time(...)`); but `tests/test_property_
  persistence.py` also imports freezegun and triggers the missing-stub check.
- **Fix:** Append `freezegun>=1.5` to the pre-commit mypy
  `additional_dependencies` block (one-line addition). This restores parity
  between the file-isolated pre-commit mypy hook and the project-level mypy
  gate (which finds freezegun via the venv). Mirrors Plan 13-03's identical
  addition of `anthropic>=0.100.0,<1.0` + `duckdb>=1.4,<2.0`.
- **Files modified:** `.pre-commit-config.yaml` (mypy hook additional_
  dependencies block).
- **Commit:** `0733a71` (bundled into Task 2's commit).

**3. [Rule 3 - Lint hygiene] TC002 + I001 on tests/test_property_persistence.py imports**

- **Found during:** Task 2 pre-commit ruff hook.
- **Issue (3a TC002):** Initially `import pytest` was at module top because
  `pytest.MonkeyPatch` is used as an annotation on `test_write_acquires_data_
  lock`. ruff `TC002` ("Move third-party import into a type-checking block")
  fires because pytest is only used as a type hint -- the test's
  `pytest.MonkeyPatch` parameter annotation is `from __future__ import
  annotations`-deferred and never resolved at runtime. Note: this differs
  from `tests/test_fred_cache.py` where pytest is also called at runtime
  (`pytest.warns(...)`, `pytest.raises(...)`) -- so TC002 doesn't fire there.
- **Issue (3b I001):** After moving pytest into TYPE_CHECKING, ruff I001
  flagged the resulting import block ordering.
- **Fix:** Moved `import pytest` into the `if TYPE_CHECKING:` block alongside
  `from pathlib import Path`; ran `ruff check --fix` + `ruff format` to
  normalize ordering. Tests still consume `monkeypatch: pytest.MonkeyPatch`
  via the from-future annotations.
- **Files modified:** `tests/test_property_persistence.py` (import block only).
- **Commit:** `0733a71` (bundled into Task 2's commit after pre-commit
  auto-fix).

**4. [Rule 3 - Type-narrow tuple unpacking] mypy "Value of type 'tuple[Any, ...] | None' is not indexable"**

- **Found during:** Task 2 pre-commit mypy hook.
- **Issue:** Plan action wrote `count = con.execute(...).fetchone()[0]` in
  the composite-PK row-count test. DuckDB's `fetchone()` return is typed as
  `tuple[Any, ...] | None`, so direct `[0]` subscripting fails mypy --strict.
- **Fix:** Split into `row = con.execute(...).fetchone()` then
  `assert row is not None; assert row[0] == 2`. The assert is also a real
  precondition check, not just a type narrower. Same logical assertion.
- **Files modified:** `tests/test_property_persistence.py` (composite-PK test
  body only).
- **Commit:** `0733a71` (bundled into Task 2's commit).

### Removed entire mypy override block (NOT a deviation; documented for traceability)

`pyproject.toml` had a Wave-0 `[[tool.mypy.overrides]]` block stubbing
`lib.property_persistence` with `ignore_missing_imports = true`. Plans 13-01
+ 13-02 + 13-03 each removed their own module's override line; this plan
removed the last remaining `lib.property_persistence` entry. With no
`lib.property_*` entries left, the entire 4-line Wave-0 comment block was
also dropped (it referenced waves 1-5 which have all now shipped). pyproject
diff is `-8 / +0` for this section.

## Authentication Gates

None. This plan is pure local DuckDB + filesystem + stdlib hashlib; no API
keys, no external services touched.

## Verification

- [x] `lib/property_persistence.py` exists; `wc -l` = 157 (>= 100 required)
- [x] 4 module-top functions: `write_listing`, `read_latest_for_zpid`,
  `compute_household_hash`, `_ensure_schema` (verified via `grep -c '^def
  <name>'` -- each returns 1)
- [x] Module constants: `DB_PATH: Final[Path]`, `SCHEMA_VERSION: Final[int]
  = 1`, `CREATE_TABLE_SQL: Final[str]`
- [x] SQL contains `PRIMARY KEY (zpid, analyzed_at)` exactly
  (D-13-REANALYSIS-01)
- [x] SQL creates 3 indexes: `idx_listings_zpid`, `idx_listings_verdict`,
  `idx_listings_analyzed_at` (all 3 grep-found)
- [x] Uses `with_cache_lock` from `lib.fred_cache` (NOT hand-rolled)
- [x] Lock-dir is `db_path.parent` (data/), NOT a subdirectory
  (asserted by lockfile spy test)
- [x] `compute_household_hash` uses `hashlib.sha256` + reads bytes from both
  YAML files + encodes the rate string
- [x] Lazy `import duckdb` inside function bodies; no top-level `import
  duckdb` (verified `! grep -E '^import duckdb' lib/property_persistence.py`)
- [x] `read_latest_for_zpid` catches `duckdb.CatalogException` (Pitfall 14)
- [x] Defensive `except Exception` around `PropertyListing.model_validate_
  json` (CR-01 idiom)
- [x] `_now_utc()` returns `datetime.now(UTC)` (microsecond precision)
- [x] No `Co-Authored-By`, no AI-attribution strings (CLAUDE.md global rule;
  also project CLAUDE.md "Project" section commits convention)
- [x] `uv run python -c "from lib.property_persistence import write_listing,
  read_latest_for_zpid, compute_household_hash, _ensure_schema, DB_PATH,
  SCHEMA_VERSION"` succeeds without needing data/ dir to exist
- [x] `grep -c '@pytest.mark.xfail' tests/test_property_persistence.py`
  returns 0 (all 7 Wave-0 stubs flipped)
- [x] `grep -c '^def test_' tests/test_property_persistence.py` returns 16
  (>= 13 required)
- [x] `uv run pytest tests/test_property_persistence.py -v` -> 16 passed,
  0 xfail, 0 XPASS, 0 failed, 0 error
- [x] `uv run pytest tests/test_fred_cache.py` -> 8 passed (no regression
  from `with_cache_lock` reuse)
- [x] Composite PK proven to split on microsecond precision (freezegun
  test with 1us delta -> count == 2)
- [x] Lockfile spy test asserts `acquired_dirs[0] == db.parent` (NOT
  subdir; matches Phase 9 Node writer's lock-dir)
- [x] household_hash is 64-char hex SHA256; deterministic; sensitive to
  household.yml AND profile.yml AND MORTGAGE30US value (4 separate tests)
- [x] Malformed-row test proves CR-01 defensive idiom (corrupted JSON
  in DB -> read returns None, never raises)
- [x] Full suite: 716 passed + 6 skipped + 11 xfailed + 2 failed (the 2
  failed are pre-existing `[fha_mip]` baseline failures explicitly excluded
  from scope; zero regression from Plan 13-03's 700 passed)
- [x] Pre-existing dirty file (`lib/rules/fha_mip.py`) NOT staged;
  pre-existing untracked files (`.planning/*.md` notes, `data/.lock 2..5`)
  NOT staged -- per executor constraints
- [x] Pre-commit hooks pass (ruff, ruff-format, mypy --strict,
  DATA_CONTRACT.md guard) on both task commits

## PROP-02 + PERS-08 Closure

**PROP-02 ("Round-trip serialization to DuckDB"):** Closed.

- `test_round_trip_write_read` writes a PropertyListing (with a
  ProvenancedMoney tax_annual to exercise the wrapper), reads it back via
  `read_latest_for_zpid`, and asserts byte-equal model equality (Pydantic
  `__eq__` over frozen models).
- `test_read_latest_returns_most_recent_when_multiple_rows` proves
  ORDER BY analyzed_at DESC selects the latest write.
- The full PropertyListing v1.1 field surface (price + zip + property_type +
  4 ProvenancedMoney optional fields + 6 NICE-TO-HAVE non-money + 6 sibling
  *_provenance + 3 audit fields) round-trips byte-for-byte via DuckDB's
  native JSON column.

**PERS-08 ("analyzed_listings table + lockfile pattern from Phase 9"):**
Closed.

- `_ensure_schema(con)` creates the table + 3 indexes idempotently
  (CREATE IF NOT EXISTS) and is asserted by
  `test_ensure_schema_creates_table_and_indexes`.
- Lockfile pattern from Phase 9 reused VERBATIM via Phase 12's Python port
  `lib.fred_cache.with_cache_lock`. Lock-dir == `db_path.parent` (data/),
  which is the same directory `orchestration/lockfile.mjs` and
  `orchestration/db-write.mjs` write their `.lock` to -- so Python and Node
  writers serialize on the SAME file. Asserted by `test_write_acquires_
  data_lock`.
- `household_hash` is a 64-char hex SHA256 over (household.yml bytes +
  profile.yml bytes + MORTGAGE30US value string) per Q4 default; sensitive
  to all three inputs (3 separate tests).

## D-13-REANALYSIS-01 Lock Surface

| Requirement | Implementation receipts |
| ----------- | ---------------------- |
| Composite PK (zpid, analyzed_at) | Literal string in CREATE_TABLE_SQL; asserted by `test_schema_has_composite_pk_in_sql` |
| Same zpid + different analyzed_at = 2 rows | `test_composite_pk_allows_reanalysis_with_microsecond_delta` with freezegun 1us delta -> COUNT = 2 |
| Latest-wins read | `test_read_latest_returns_most_recent_when_multiple_rows` -- ORDER BY analyzed_at DESC LIMIT 1 |
| Microsecond TIMESTAMP precision | `_now_utc()` returns `datetime.now(UTC)` (Python default = microseconds); DuckDB TIMESTAMP type stores microseconds |
| analyzed_at column never overwritten | INSERT ONLY; no UPDATE statements anywhere in the module |
| analysis_json nullable | Phase 14 backfills the analysis column; the Phase 13 ingest writes NULL |

## Self-Check: PASSED

Verified by direct filesystem + git inspection:

- FOUND: lib/property_persistence.py (157 LOC)
- FOUND: tests/test_property_persistence.py (modified; 16 live tests; 0 xfail)
- FOUND: pyproject.toml (modified; entire Wave-0 mypy override block removed)
- FOUND: .pre-commit-config.yaml (modified; freezegun in mypy additional_deps)
- FOUND: .planning/REQUIREMENTS.md (modified; PROP-02 + PERS-08 marked [x] + traceability rows updated)
- FOUND: commit 91c7c7d (Task 1 - lib/property_persistence.py + pyproject.toml)
- FOUND: commit 0733a71 (Task 2 - tests/test_property_persistence.py + .pre-commit-config.yaml)
- VERIFIED: `uv run pytest tests/test_property_persistence.py` -> 16 passed
- VERIFIED: `uv run pytest tests/test_fred_cache.py` -> 8 passed (no regression)
- VERIFIED: `uv run python -c "from lib.property_persistence import ..."` succeeds without data/ existing
- VERIFIED: zero regression vs Plan 13-03 baseline (the 2 pre-existing `[fha_mip]` failures remain unchanged; 700 -> 716 passed = +16 new tests)

## Next: Wave 4 (Plan 13-04 CLI) + Wave 6 (Plan 13-06 fixtures)

Plan 13-05 was parallel-eligible with Plan 13-04 (only depends on Plans
13-00 + 13-01). Plan 13-04 (CLI) is still pending (11 xfails in
`tests/test_property_fetch.py`) and composes `detect_block` (Plan 13-02) +
`extract_zpid` + `extract_listing` (Plan 13-03) + `PropertyListing.model_
validate` + three-envelope emission. Plan 13-04 MAY optionally import
`write_listing` on the success path (planner's call; not a hard dependency
of Plan 13-04 per the dependency_graph in this plan's frontmatter).

Plan 13-06 (integration fixtures) is the final Phase 13 wave: 5 pinned
Zillow HTML fixtures + golden expected envelopes + end-to-end URL ->
DuckDB round-trip test using `write_listing` + `read_latest_for_zpid` from
this plan.

After Phase 13 closes (all 7 plans), Phase 14 (analysis pipeline) consumes
both `PropertyListing` (Plan 13-01) and `write_listing` (this plan) for
the multi-program x DP fan-out flow.
