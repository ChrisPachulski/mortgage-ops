---
phase: 09-duckdb-orchestration
plan: 00
subsystem: testing

tags:
  - phase-09
  - duckdb-orchestration
  - test-infrastructure
  - nyquist
  - pytest
  - xfail-stubs
  - subprocess-helper
  - node-orchestration

# Dependency graph
requires:
  - phase: 08-stress-points
    provides: "521 passed + 4 skipped + 1 xfailed Phase 5+ baseline that Wave 0 must preserve verbatim"
provides:
  - "tests/test_orchestration/ Python package (zero-byte __init__.py marker per tests/test_reference/ convention)"
  - "9 @pytest.mark.xfail(strict=True) stubs covering PERS-01..PERS-07 + cross-cutting decimal-cents discipline"
  - "node_orchestration_run module-level helper in tests/conftest.py (subprocess.run wrapper with MORTGAGE_OPS_DB_PATH env-var override seam for tmp DBs)"
  - "REPO_ROOT module-level constant in tests/conftest.py (cwd source for Node subprocesses)"
  - "Wave-flip mapping documented in stub docstrings — every later wave (09-01..09-06) knows exactly which xfail name to flip and remove the decorator"
affects:
  - "09-01 lockfile (Wave 1) — flips test_stale_lockfile_reclaimed_after_60s in Wave 6"
  - "09-02 init-db (Wave 2) — flips test_init_db_idempotent + must implement MORTGAGE_OPS_DB_PATH override"
  - "09-03 db-write subcommands (Wave 3) — flips test_insert_loan_round_trip + test_insert_scenario_round_trip + test_insert_report_round_trip + test_decimal_string_round_trip_preserves_cents"
  - "09-04 render-markdown (Wave 4) — flips test_render_markdown_byte_identical"
  - "09-05 known-loans.yml (Wave 5) — flips test_known_loans_catalog_complete"
  - "09-06 concurrency tests (Wave 6) — flips test_concurrent_writes_serialize + test_stale_lockfile_reclaimed_after_60s"
  - "09-07 references doc (Wave 7) — no stub flip; documents the data-layer contract"

# Tech tracking
tech-stack:
  added: []  # Wave 0 is test infrastructure only; no new runtime libraries
  patterns:
    - "Module-level helper (NOT pytest fixture) for subprocess shellout — direct import via `from tests.conftest import node_orchestration_run` parallels tests/test_amortize.py:722-751 idiom; fixture wrapper would add zero value over varying argv per call"
    - "Environment-variable seam (MORTGAGE_OPS_DB_PATH) for prod-vs-tmp DB targeting — Wave 2 init-db.mjs must honor this override; locks the contract before implementation"
    - "@pytest.mark.xfail(strict=True) stubs as Nyquist validation gates — accidental pass triggers XPASS, forcing the wave that fixes it to also remove the decorator (per Phase 5 LM precedent on 32 ARM stubs + Phase 4 9 affordability stubs)"
    - "Zero-byte __init__.py package marker convention (rule-of-three: tests/test_reference/, tests/test_rules/, now tests/test_orchestration/)"

key-files:
  created:
    - "tests/test_orchestration/__init__.py — zero-byte package marker"
    - "tests/test_orchestration/test_db_lifecycle.py — 6 stubs (init idempotency + 3 insert round-trips + decimal cents discipline + concurrent-writes)"
    - "tests/test_orchestration/test_lockfile.py — 1 stub (60s stale-lockfile reclaim)"
    - "tests/test_orchestration/test_known_loans_smoke.py — 1 stub (>=7 product entries + REF-09 source/effective)"
    - "tests/test_orchestration/test_render_markdown.py — 1 stub (byte-identical regeneration)"
  modified:
    - "tests/conftest.py — appended os + subprocess imports + REPO_ROOT constant + node_orchestration_run helper (47 insertions; existing fixtures untouched)"

key-decisions:
  - "D-00-01 LOCKED: tests/test_orchestration/ package path (mirrors tests/test_reference/ + tests/test_rules/ rule-of-three convention)"
  - "D-00-02 LOCKED: node_orchestration_run is module-level helper, NOT pytest fixture (direct import; per-call varying argv makes fixture wrapper zero-value)"
  - "D-00-03 LOCKED: All 9 stubs use @pytest.mark.xfail(strict=True) — accidental pass triggers XPASS forcing wave-flip plan to also remove decorator"
  - "D-00-04 LOCKED: MORTGAGE_OPS_DB_PATH env-var is the prod-vs-tmp seam — Wave 2 init-db.mjs MUST honor this override; locked here before implementation"

patterns-established:
  - "Module-level subprocess helper (not pytest fixture) for shellout-based tests — pattern source for any future Node-bridge tests"
  - "Env-var override seam for tmp DB targeting — locked contract that Wave 2 implementation must honor"
  - "Wave-flip xfail-stub-as-contract — every requirement-closing wave (09-01..09-06) flips a specific named xfail to a real assertion"

requirements-completed:
  - PERS-01  # Wave 0 stub for init-db idempotency landed; flipped in Wave 2
  - PERS-02  # Wave 0 stub for init-db idempotency landed; flipped in Wave 2
  - PERS-03  # Wave 0 stubs for insert-loan/scenario/report round-trips landed; flipped in Wave 3
  - PERS-04  # Wave 0 stub for stale-lockfile reclaim landed; flipped in Wave 6
  - PERS-05  # Wave 0 stub for concurrent-writes serialization landed; flipped in Wave 6
  - PERS-06  # Wave 0 stub for byte-identical render landed; flipped in Wave 4
  - PERS-07  # Wave 0 stub for known-loans.yml catalog landed; flipped in Wave 5

# Metrics
duration: 11min
completed: 2026-05-07
---

# Phase 09 Plan 00: Test Infrastructure Summary

**9 @pytest.mark.xfail(strict=True) stubs covering PERS-01..PERS-07 + cross-cutting decimal-cents guard, plus node_orchestration_run subprocess helper with MORTGAGE_OPS_DB_PATH env-var seam — Wave 0 lands the test scaffold every Phase 9 requirement-closing wave will flip.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-05-07T16:24:28Z
- **Completed:** 2026-05-07T16:35:06Z
- **Tasks:** 3 (Task 3 was verification-only — no commit)
- **Files modified:** 1 (tests/conftest.py)
- **Files created:** 5 (tests/test_orchestration/{__init__.py, test_db_lifecycle.py, test_lockfile.py, test_known_loans_smoke.py, test_render_markdown.py})

## Accomplishments

- **9 xfail stubs landed**, one per requirement-closing wave (revision 2026-05-04 bumped from 7 to 9 per checker Blocker #2 — PERS-03 ships three insert subcommands so each gets its own round-trip stub)
- **node_orchestration_run helper** appended to tests/conftest.py with MORTGAGE_OPS_DB_PATH env-var override — locks the prod-vs-tmp DB seam before Wave 2 implements init-db.mjs
- **Phase 5+ baseline preserved exactly**: 521 passed + 4 skipped + 1 xfailed → 521 passed + 4 skipped + 10 xfailed (+9 net xfails; zero regression)
- **mypy --strict + ruff check + ruff format --check all clean** across both touched paths (tests/conftest.py + tests/test_orchestration/)

## Wave-Flip Mapping

Every xfail stub names the wave that flips it; the wave that flips MUST also remove `@pytest.mark.xfail(strict=True, ...)` (else XPASS fires).

| Stub | File | Wave | Plan |
|------|------|------|------|
| `test_init_db_idempotent` | test_db_lifecycle.py | Wave 2 | 09-02 |
| `test_insert_loan_round_trip` | test_db_lifecycle.py | Wave 3 | 09-03 |
| `test_insert_scenario_round_trip` | test_db_lifecycle.py | Wave 3 | 09-03 |
| `test_insert_report_round_trip` | test_db_lifecycle.py | Wave 3 | 09-03 |
| `test_decimal_string_round_trip_preserves_cents` | test_db_lifecycle.py | Wave 3 | 09-03 |
| `test_concurrent_writes_serialize` | test_db_lifecycle.py | Wave 6 | 09-06 |
| `test_stale_lockfile_reclaimed_after_60s` | test_lockfile.py | Wave 6 | 09-06 |
| `test_render_markdown_byte_identical` | test_render_markdown.py | Wave 4 | 09-04 |
| `test_known_loans_catalog_complete` | test_known_loans_smoke.py | Wave 5 | 09-05 |

## Test Counts

- **Pre-Wave-0 baseline (Plan 08-06 final):** 521 passed + 4 skipped + 1 xfailed (the 1 xfailed is `test_oracle_cross_validation_5_1` from Phase 5 ARM oracle deferral, NOT Phase 9)
- **Post-Wave-0 (Plan 09-00 final):** 521 passed + 4 skipped + 10 xfailed (+9 net xfails; the 9 are the new orchestration stubs)
- **Wave 0 verify-block 7-vs-9 reconciliation:** Plan was revised on 2026-05-04 from 7 to 9 stubs per checker Blocker #2 (PERS-03 split into insert-loan + insert-scenario + insert-report subcommands per career-ops db-write.mjs pattern); the SUMMARY count of 9 supersedes the 7 mentioned in stale verify-block lines.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend tests/conftest.py with node_orchestration_run helper** — `1983818` (test)
2. **Task 2: Create tests/test_orchestration/ package marker + 4 xfail stub modules** — `bb89687` (test)
3. **Task 3: Verify zero regression to Phase 5 baseline + lint hygiene** — verification-only, no commit

## Files Created/Modified

- `tests/conftest.py` — appended `os` + `subprocess` imports, `REPO_ROOT: Path` module-level constant (parents.parent of conftest), and `node_orchestration_run(*args, db_path=None, timeout=30, check=False)` module-level helper with capture_output=True + text=True. Existing 8 fixture functions (golden_fixture, amortize_fixture, affordability_fixture, arm_fixture, refinance_fixture, apr_fixture, stress_fixture, points_fixture) untouched (Rule-2 preserve discipline).
- `tests/test_orchestration/__init__.py` — zero-byte package marker (mirrors tests/test_reference/__init__.py + tests/test_rules/__init__.py rule-of-three).
- `tests/test_orchestration/test_db_lifecycle.py` — 100 lines, 6 xfail stubs with wave-flip-pointer reasons.
- `tests/test_orchestration/test_lockfile.py` — 28 lines, 1 xfail stub (PERS-04 60s stale reclaim, acquired_at-based per PATTERNS Critical Issue 1).
- `tests/test_orchestration/test_known_loans_smoke.py` — 31 lines, 1 xfail stub (PERS-07 + REF-09 source/effective + loan_type Literal validation).
- `tests/test_orchestration/test_render_markdown.py` — 30 lines, 1 xfail stub (PERS-06 + ROADMAP SC-4 byte-identical regeneration).

## Decisions Made

All four decisions are LOCKED at the plan level (D-00-01..D-00-04) — the executor honored them verbatim. No new plan-level decisions emerged during execution.

- **D-00-01 LOCKED — tests/test_orchestration/ package path:** rule-of-three (tests/test_reference/__init__.py + tests/test_rules/__init__.py + now tests/test_orchestration/__init__.py).
- **D-00-02 LOCKED — node_orchestration_run is module-level helper, NOT pytest fixture:** rule-of-three (subprocess.run is invoked directly in tests/test_amortize.py + tests/test_affordability.py CLI tests + tests/test_arm.py CLI tests — none use a fixture wrapper).
- **D-00-03 LOCKED — All 9 stubs use @pytest.mark.xfail(strict=True):** rule-of-three (tests/test_arm.py 32 stubs in Plan 05-00; tests/test_affordability.py 9 stubs in Plan 04-00; this plan adds 9 more).
- **D-00-04 LOCKED — MORTGAGE_OPS_DB_PATH env-var override is the seam between prod DB and tmp DB:** Wave 2 init-db.mjs MUST honor this env var; the contract is locked here so Wave 2 implements it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule-3 Hygiene] Ruff format auto-collapsed multi-line decorator + multi-line constant**
- **Found during:** Task 2 (after writing the 4 stub files)
- **Issue:** Three `@pytest.mark.xfail(strict=True, reason="...")` decorators in test_db_lifecycle.py (insert-scenario, insert-report, decimal-string-round-trip) had reason-strings that pushed the literal `'@pytest.mark.xfail(strict=True'` over the 100-char line-length, so `ruff format` wrapped them into `@pytest.mark.xfail(\n    strict=True, reason="..."\n)` form. Additionally `ruff format` collapsed the multi-line `KNOWN_LOANS_PATH: Path = (Path(__file__).resolve()...)` parens-wrapped expression into a single 102-char line (still under the 100 limit after collapse).
- **Fix:** Accepted ruff's reformat verbatim; the test contract is identical (pytest still sees `xfail(strict=True)` on all 9 stubs and reports 9 XFAIL).
- **Plan-level acknowledgement:** The plan's deviation_rules section explicitly authorizes Rule-3 ruff-format auto-collapse: "ruff format auto-collapse of multi-line expressions. These are hygiene-only and do not affect the test contract."
- **Plan acceptance criterion drift:** The plan's literal `grep -c '@pytest.mark.xfail(strict=True'` returns 6 acceptance criterion now reads 3 (single-line) for test_db_lifecycle.py because 3 of 6 decorators are wrapped. All 6 decorators ARE present and functional — verified via `grep -c '@pytest.mark.xfail' tests/test_orchestration/test_db_lifecycle.py` returning 6 and pytest collecting 9 XFAIL.
- **Files modified:** tests/test_orchestration/test_db_lifecycle.py, tests/test_orchestration/test_known_loans_smoke.py
- **Verification:** `uv run ruff format --check tests/test_orchestration/` → 5 files already formatted; pytest still reports 9 xfailed.
- **Committed in:** `bb89687` (Task 2 commit, post-format)

**2. [Rule-3 Hygiene] Ruff TC003 — `pathlib.Path` moved into TYPE_CHECKING block in 2 stub files**
- **Found during:** Task 2 lint-check after initial file writes
- **Issue:** Ruff TC003 fired on `tests/test_orchestration/test_lockfile.py:10` and `tests/test_orchestration/test_render_markdown.py:10`: "Move standard library import `pathlib.Path` into a type-checking block." Both files use `Path` only as a function parameter annotation (`tmp_path: Path`); with `from __future__ import annotations` the annotations are strings at runtime, so Path is never imported at runtime.
- **Fix:** Moved `from pathlib import Path` into an `if TYPE_CHECKING:` block in both files. Added `from typing import TYPE_CHECKING` import. Did NOT modify test_db_lifecycle.py (uses `Path(__file__).resolve()` at module-load for `REPO_ROOT`) or test_known_loans_smoke.py (same — `KNOWN_LOANS_PATH` is module-level).
- **Files modified:** tests/test_orchestration/test_lockfile.py, tests/test_orchestration/test_render_markdown.py
- **Verification:** `uv run ruff check tests/test_orchestration/` → All checks passed; mypy --strict still clean.
- **Committed in:** `bb89687` (Task 2 commit, applied during lint-fix sub-loop before commit)

---

**Total deviations:** 2 auto-fixed (both Rule-3 hygiene-only).
**Impact on plan:** Zero functional change. Both deviations are explicitly authorized by the plan's deviation_rules section ("hygiene-only and do not affect the test contract"). No Rule-1 or Rule-2 deviations occurred — the test contract (9 named xfail stubs + node_orchestration_run helper signature) is preserved verbatim.

## Issues Encountered

None — execution was clean. The two Rule-3 hygiene deviations were anticipated by the plan's deviation_rules section.

## Lint + Type Hygiene Status

| Check | Result |
|-------|--------|
| `uv run pytest -q` | 521 passed + 4 skipped + 10 xfailed (was 521+4+1; +9 new xfails; zero regression) |
| `uv run mypy --strict tests/conftest.py tests/test_orchestration/` | Success: no issues found in 6 source files |
| `uv run ruff check tests/conftest.py tests/test_orchestration/` | All checks passed! |
| `uv run ruff format --check tests/conftest.py tests/test_orchestration/` | 6 files already formatted |

## User Setup Required

None — Wave 0 is test infrastructure only; no environment variables, dashboard configuration, or credential setup needed. The MORTGAGE_OPS_DB_PATH env-var override is consumed only by Wave 2 init-db.mjs (not yet shipped); pytest tests will set it via the node_orchestration_run helper's `db_path` parameter.

## Self-Check: PASSED

Verified at SUMMARY-write time:
- `tests/conftest.py` exists; `node_orchestration_run` + `REPO_ROOT` importable (`uv run python -c "from tests.conftest import node_orchestration_run, REPO_ROOT; print('OK', REPO_ROOT)"` → `OK /Users/cujo253/Documents/mortgage-ops`)
- `tests/test_orchestration/__init__.py` exists at zero bytes (`wc -c` → 0)
- `tests/test_orchestration/test_db_lifecycle.py` exists; 6 xfail decorators (3 single-line + 3 wrapped)
- `tests/test_orchestration/test_lockfile.py` exists; 1 xfail decorator
- `tests/test_orchestration/test_known_loans_smoke.py` exists; 1 xfail decorator
- `tests/test_orchestration/test_render_markdown.py` exists; 1 xfail decorator
- All 9 required test names verified present (one grep each, all OK)
- Commit `1983818` (Task 1) found via `git log --oneline`
- Commit `bb89687` (Task 2) found via `git log --oneline`
- Full pytest suite reports 521 passed + 4 skipped + 10 xfailed (verified)
- mypy --strict + ruff check + ruff format --check all clean (verified)

## Next Phase Readiness

**Wave 1 (Plan 09-01 lockfile.mjs) unblocked** — has a known xfail name to flip: `test_stale_lockfile_reclaimed_after_60s` in tests/test_orchestration/test_lockfile.py (Wave 6 actually flips it; Wave 1 just ships the production code).

**Waves 2-6 unblocked** — every later requirement-closing wave has a named xfail target:
- Wave 2 (09-02 init-db.mjs): `test_init_db_idempotent`
- Wave 3 (09-03 db-write.mjs subcommands): `test_insert_loan_round_trip`, `test_insert_scenario_round_trip`, `test_insert_report_round_trip`, `test_decimal_string_round_trip_preserves_cents`
- Wave 4 (09-04 render-markdown): `test_render_markdown_byte_identical`
- Wave 5 (09-05 known-loans.yml): `test_known_loans_catalog_complete`
- Wave 6 (09-06 concurrency tests): `test_concurrent_writes_serialize`, `test_stale_lockfile_reclaimed_after_60s`

**Wave 7 (09-07 references doc)** — no stub flip; documents the data-layer contract (lockfile mechanics, DECIMAL string round-trip, single-writer + transaction layering, byte-identical render).

**Cross-phase contract for Wave 2:** init-db.mjs MUST honor `MORTGAGE_OPS_DB_PATH` env-var override on the `DB_PATH` constant (D-00-04 LOCKED). The conftest helper sets this env var when `db_path` is provided.

**No blockers carry over** — Phase 9 still has 3 BLOCKERS pending (lockfile path contradiction across plans 09-01/09-06/09-07; known-loans.yml field name `type:` violating `lib.models.Loan.loan_type`; .gitignore additions duplicated across 09-02 + 09-07) per STATE.md, but Wave 0 was specifically scoped as "additive test scaffold; zero behavior change" so those blockers do not gate this plan's completion. They DO gate Waves 1+ and must be resolved before `/gsd-execute-phase 09` continues.

---
*Phase: 09-duckdb-orchestration*
*Plan: 00 (Wave 0 — test infrastructure)*
*Completed: 2026-05-07*
