---
phase: 12-fred-eval
plan: 01
subsystem: fred-cli
tags: [phase-12, wave-1, fred-cli, http-wrapper, live-01, live-04, always-exit-0]

# Dependency graph
requires:
  - phase: 12-fred-eval
    plan: 00
    provides: tests/test_fred_cli.py 5 strict-xfail stubs covering LIVE-01 + LIVE-04 — this plan flips them to live
  - phase: 10-claude-skill
    provides: .claude/skills/mortgage-ops/scripts/ landing folder + sys.path-injection idiom (amortize.py parents[4]/parents[1])
  - phase: 04-amortize
    provides: D-18 lazy-import discipline (--help <300ms via post-argparse imports)
provides:
  - .claude/skills/mortgage-ops/scripts/fred_cli.py (HTTP wrapper canonical path per D-12-LIVE01-01)
  - always-exit-0 envelope contract on stdout (per Pitfall 1 + D-12-LIVE02-01 recovery contract)
  - ALLOWED_SERIES allowlist (MORTGAGE30US, MORTGAGE15US) enforced at argparse parse time
  - redacted source_url shape (api_key=***) reusable by Plan 12-02 cache writer
  - landing surface for Plan 12-02 lib.fred_cache.get_cached_or_fetch integration
affects: [fred-cli, plan 12-02 (cache integration), plan 12-03 (SKILL.md prose-only injection), plan 12-04 (evals/runner.py reads envelope), plan 12-08 (references/fred-context.md documents this as canonical)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Always-exit-0 envelope contract (NEW pattern; diverges from amortize.py exit-2 ValidationError envelope; Pitfall 1 + D-12-LIVE02-01)
    - HTTP-wrapper-as-canonical (NEW pattern; D-12-LIVE01-01 — MCP server documented as optional secondary in Plan 12-08)
    - Hand-built redacted source_url (NEW pattern; T-12-01-02 — independent string construction, real api_key never str-interpolated into any output channel)
    - Inherited: sys.path-injection 5-levels-deep (amortize.py parents[4]/parents[1])
    - Inherited: D-18 lazy-import (urllib + os + datetime imported AFTER argparse.parse_args())
    - Inherited: Wave-0-strict-xfail-then-flip discipline (4 xfails removed; tests pass live)

key-files:
  created:
    - .claude/skills/mortgage-ops/scripts/fred_cli.py
  modified:
    - tests/test_fred_cli.py (4 @pytest.mark.xfail decorators removed; module docstring updated to reflect Wave-1 live state; ruff format applied)

key-decisions:
  - "Per-series cache file path data/cache/fred_{series_id}.json (NOT RESEARCH §Example 1 combined evals/cache/fred-cache.json) pinned by D-12-LIVE02-01 SKILL.md citations — documented as Plan 12-02 landing target in module docstring"
  - "Cache integration deferred to Plan 12-02 (Wave 1 always performs the live fetch; Plan 12-02 lib.fred_cache.get_cached_or_fetch will replace the network block with a single call) — TODO marker lives in module docstring, NOT the body"
  - "Hand-built redacted source_url constructed independently of the real URL — a future refactor cannot accidentally leak FRED_API_KEY by stringifying the real url"
  - "Plan 12-00 left tests/test_fred_cli.py un-formatted by ruff; this commit applies ruff format alongside the xfail removal (Rule 1 — file is part of files_modified)"

requirements-completed: [LIVE-01, LIVE-04]

# Metrics
duration: ~4min
completed: 2026-05-13
---

# Phase 12 Plan 01: fred-cli Summary

**FRED HTTP wrapper CLI (canonical per D-12-LIVE01-01) shipped at `.claude/skills/mortgage-ops/scripts/fred_cli.py` (212 lines) with allowlist + 10s timeout + redacted source_url + always-exit-0 envelope; 4 Wave-0 LIVE-01/LIVE-04 xfails flipped to passing.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-13T17:57:05Z
- **Completed:** 2026-05-13T18:00:52Z
- **Tasks:** 1 (single TDD-flow GREEN task — Wave-0 commit `ec6363e` was the RED gate)
- **Files created:** 1 (`.claude/skills/mortgage-ops/scripts/fred_cli.py`, 212 lines)
- **Files modified:** 1 (`tests/test_fred_cli.py` — 4 xfail decorators removed + ruff format)
- **Tests delta:** +5 passing (605 vs Wave-0 baseline of 600); xfails 30 → 25

## Accomplishments

- **`.claude/skills/mortgage-ops/scripts/fred_cli.py` (212 lines)** — JSON-out CLI for the latest FRED observation:
  - **Allowlist** (`ALLOWED_SERIES = ("MORTGAGE30US", "MORTGAGE15US")`) enforced at argparse `choices=` parse time (T-12-01-01 mitigation — no URL interpolation possible for non-allowed series).
  - **10s urllib timeout** caps Slowloris-style worst-case (T-12-01-04 — RESEARCH §Pitfall: Slowloris cap).
  - **Redacted source_url** (`api_key=***`) constructed independently of the real URL so a future refactor cannot leak the key (T-12-01-02 mitigation).
  - **D-18 lazy-import**: urllib + os + datetime imported AFTER `argparse.parse_args()` so `--help` clocks in at ~50ms (test gate is <300ms).
  - **Always-exit-0 envelope** on every failure path (missing FRED_API_KEY, network failure, malformed FRED response) — emits `{value: null, error: "..."}` on stdout and returns 0 per Pitfall 1 + D-12-LIVE02-01 recovery contract.
  - **sys.path injection** mirrors amortize.py `parents[4]` (repo root) + `parents[1]` (skill root); runs AFTER argparse so D-18 fast-`--help` is preserved.
  - **Threat-model coverage**: all 6 threats in the plan threat-register (T-12-01-01..06) implemented with code comments citing each mitigation.

- **`tests/test_fred_cli.py` flipped to live (Wave 1)**:
  - 4 `@pytest.mark.xfail(strict=True)` decorators removed (`test_fred_cli_script_exists`, `test_fred_cli_help_fast_lazy_imports`, `test_fred_cli_missing_api_key_returns_exit_0_with_error_envelope`, `test_fred_cli_supports_both_series` — parametric over MORTGAGE30US + MORTGAGE15US).
  - Module docstring updated to declare LIVE-01 + LIVE-04 closed.
  - Test bodies preserved verbatim (only decorator removal + ruff format whitespace).
  - All 5 collected test items PASS (4 unique + 1 parametric expansion).

- **Full suite**: 605 passed / 5 skipped / 25 xfailed (was 600/5/30). Zero regressions to Phases 1-11.

## Task Commits

1. **Task 1 (TDD GREEN gate): ship fred_cli.py + flip 4 Wave-0 xfails** — `7529585` (feat). Single atomic commit pairing the implementation with the xfail removal so the GREEN transition is observable in one diff. The TDD RED gate is the pre-existing Wave-0 commit `ec6363e` (`test(12-00): add Wave-0 strict-xfail stubs...`).

_Commit used `--no-verify` per parallel-executor protocol. No Co-Authored-By or AI-attribution trailers per global CLAUDE.md rule + project CLAUDE.md._

## Files Created/Modified

### Created
- **`.claude/skills/mortgage-ops/scripts/fred_cli.py`** (212 lines) — JSON-out CLI. Module structure mirrors `.claude/skills/mortgage-ops/scripts/amortize.py`:
  - Header: module docstring with envelope-shape contract + Plan 12-02 cache-integration TODO marker.
  - Top-level imports: `argparse`, `json`, `sys`, `pathlib.Path`, `typing.Any` (no `urllib`, no `os`, no `datetime` — those are lazy-imported inside `main()` after `parser.parse_args()`).
  - `ALLOWED_SERIES` constant at module level (V5 input validation per RESEARCH §Security Domain).
  - `main()` body:
    - Build argparse with `prog="fred_cli"`, `choices=ALLOWED_SERIES`, RawDescriptionHelpFormatter epilog documenting the envelope shape.
    - Parse args (SystemExit happens HERE on `--help` — before any heavy import).
    - sys.path injection (skill root + repo root via parents[1] + parents[4]).
    - Lazy imports.
    - `_emit()` inner helper: `print(json.dumps(envelope))` + `return 0`.
    - Missing FRED_API_KEY → emit envelope with `error: "FRED_API_KEY not set..."` + return 0.
    - Otherwise: build query string + real URL + redacted URL (constructed independently), `urllib.request.urlopen(url, timeout=10)`, parse the first observation, emit success envelope.
    - Three exception arms: URLError/HTTPError/OSError/TimeoutError (network failure), KeyError/IndexError/JSONDecodeError (malformed response). Both emit `{value: null, error: "..."}` and return 0.

### Modified
- **`tests/test_fred_cli.py`** — 4 `@pytest.mark.xfail(...)` decorators removed; module docstring updated from "Phase 12 Wave-0 stubs" to "Phase 12 Wave-1 live tests"; ruff format applied (whitespace + line-folding only; test logic byte-identical).

## Decisions Made

### Architectural choice: per-series cache file path

The RESEARCH §Example 1 reference implementation used a single combined cache file at `evals/cache/fred-cache.json` with a nested `entries: {series_id: ...}` shape. This plan diverges — pinned by D-12-LIVE02-01 SKILL.md citations and re-confirmed by the plan action:

- **Chosen shape**: per-series file at `data/cache/fred_{series_id}.json` (one file for MORTGAGE30US, one for MORTGAGE15US).
- **Rationale**: D-12-LIVE02-01 specifies the canonical SKILL.md section copy that cites `data/cache/fred_MORTGAGE30US.json` and `data/cache/fred_MORTGAGE15US.json` as discrete Read-tool targets. A combined file would break Plan 12-03's prose-only injection contract.
- **Where pinned**: documented in the module docstring (lines 25-27) as the Plan 12-02 landing target — `lib.fred_cache.get_cached_or_fetch(series_id)` will read/write the per-series file shape.

### Deferral marker: cache integration → Plan 12-02

The Wave 1 script always performs the live network fetch (cache miss every time). This is the planned Wave-1 / Wave-2 split:

- **Plan 12-01 (this plan)**: ships the HTTP fetch + envelope + allowlist + redaction surface.
- **Plan 12-02**: ships `lib/fred_cache.py` with `get_cached_or_fetch(series_id)` (7-day TTL, `withLock` port from `orchestration/lockfile.mjs`); replaces the network block in `main()` with a single `get_cached_or_fetch(...)` call.

The TODO marker lives in the module docstring (NOT the body) so it doesn't accumulate as scattered "TODO" comments throughout the code.

### Style choice: hand-built redacted source_url

The redacted URL is constructed independently of the real URL via:

```python
redacted_url = (
    f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}"
    "&api_key=***&file_type=json&sort_order=desc&limit=1"
)
```

NOT via `url.replace(api_key, "***")` because:
1. `replace()` would require the real api_key in memory at print time — a future refactor that adds logging at that point could leak it.
2. The independently-constructed form is provably FRED_API_KEY-free at every output site by inspection.
3. T-12-01-02 mitigation is enforced structurally, not via runtime sanitization.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff RUF100 + UP017 lint failures on first draft of `fred_cli.py`**
- **Found during:** Task 1 verification (post-Write ruff check).
- **Issue:** Initial draft had `# noqa: S310` on the `urllib.request.urlopen` line (defensive — `S310` is the bandit-derived audit-url rule), but this project's `pyproject.toml [tool.ruff.lint]` does NOT enable the `S` category, so the noqa directive triggered `RUF100 [unused-noqa]`. Separately, `datetime.timezone.utc` triggered `UP017 [datetime.UTC alias]` (Python 3.12 idiom).
- **Fix:** Removed the unused `# noqa: S310` directive; switched `from datetime import datetime, timezone` to `from datetime import UTC, datetime` and `datetime.now(timezone.utc)` to `datetime.now(UTC)`.
- **Files modified:** `.claude/skills/mortgage-ops/scripts/fred_cli.py`
- **Verification:** `uv run ruff check .claude/skills/mortgage-ops/scripts/fred_cli.py` → "All checks passed!".
- **Committed in:** `7529585` (same atomic commit — the lint fix is part of the task's done criteria).

**2. [Rule 1 - Bug] ruff format whitespace fix on `fred_cli.py`**
- **Found during:** Task 1 verification (post-lint ruff format check).
- **Issue:** `description=( ... )` had a wrapped parenthesized string that ruff format wanted to collapse onto a single line (the content fit within the 100-char line limit).
- **Fix:** `uv run ruff format .claude/skills/mortgage-ops/scripts/fred_cli.py` — single whitespace change to the description string.
- **Files modified:** `.claude/skills/mortgage-ops/scripts/fred_cli.py`
- **Verification:** `uv run ruff format --check .claude/skills/mortgage-ops/scripts/fred_cli.py` → "1 file already formatted".
- **Committed in:** `7529585` (same atomic commit).

**3. [Rule 1 - Bug] Pre-existing `tests/test_fred_cli.py` ruff format issues exposed by Wave-1 edit**
- **Found during:** Task 1 verification (full ruff format check across both files).
- **Issue:** The Wave-0 commit `ec6363e` left `tests/test_fred_cli.py` un-formatted by ruff (the `SCRIPT_PATH` Path-joining chain and the `test_fred_cli_supports_both_series` signature both exceeded format expectations). Wave 0 apparently didn't gate on `ruff format --check tests/test_fred_cli.py` specifically. Since this plan touches the file (xfail removal), leaving it format-dirty in the Wave-1 commit would re-broadcast a pre-existing bug.
- **Fix:** `uv run ruff format tests/test_fred_cli.py` — whitespace-only changes (no test-logic alteration). Test bodies remain byte-identical per the plan's "byte-identical" instruction (which referred to test logic, not formatting).
- **Files modified:** `tests/test_fred_cli.py`
- **Verification:** `uv run ruff format --check tests/test_fred_cli.py` → "1 file already formatted"; `uv run pytest tests/test_fred_cli.py -v` → 5 passed.
- **Committed in:** `7529585` (same atomic commit; the file is part of plan `files_modified` so its lint state is task-owned).

---

**Total deviations:** 3 auto-fixed Rule 1 lint bugs (zero Rule 2 missing-critical, zero Rule 3 blocking, zero Rule 4 architectural). All fixes were narrow lint conformance — zero changes to runtime behavior or test logic. The threat-model and always-exit-0 contract from the plan were implemented exactly as specified; no auto-added functionality was needed.

**Impact on plan:** Zero scope creep. All three fixes serve the plan's stated `<verify>` block (which requires `ruff check`, `ruff format --check`, and `mypy --strict` to pass on the new file).

## Known Stubs

| File | Line | Stub | Reason | Resolved By |
|------|------|------|--------|-------------|
| `.claude/skills/mortgage-ops/scripts/fred_cli.py` | 25 | "Cache integration TODO (Plan 12-02): when lib.fred_cache.get_cached_or_fetch ships, the network path below collapses to a single get_cached_or_fetch(series_id) call." | Plan-sanctioned (explicitly listed in plan's `<output>` block as the deferred-cache-integration marker). Wave 1 ships the network path; Wave 2 (Plan 12-02) replaces the network block with a single cache call. | Plan 12-02 |

The TODO marker is intentional documentation of the Wave-1 / Wave-2 split, not unfinished work in this plan's scope. Plan 12-01's done criteria explicitly states "cache integration deferred to Plan 12-02 as documented in the script's lazy-import comment."

## Issues Encountered

- **Token-budget check on `--help` output**: the epilog includes the full envelope JSON shape on multiple lines. Verified that `python3 .claude/skills/mortgage-ops/scripts/fred_cli.py --help` still completes in <300ms — the formatter does NOT eagerly render epilog text via heavy module imports, so D-18 lazy-import discipline holds.
- **Network smoke not run**: the `<verify>` block does NOT require a live FRED hit (which would require a real FRED_API_KEY). All four happy-path tests use `monkeypatch.delenv("FRED_API_KEY")` to exercise the no-key envelope path. The success-envelope branch (lines 152-175) is covered by the threat model + KeyError/IndexError exception arm pattern, NOT by a unit test in this plan. Plan 12-02 (cache integration) will add a stub-FRED smoke via `urllib.request.urlopen` monkeypatch.

## TDD Gate Compliance

Plan 12-01 frontmatter `type: execute` with Task 1 `tdd="true"` — single GREEN-flip task pattern.

- **RED gate:** Wave-0 commit `ec6363e` (`test(12-00): add Wave-0 strict-xfail stubs for LIVE-01..04 + EVAL-01..04`). The 4 strict-xfail stubs for LIVE-01 + LIVE-04 are anchored with assertions that fail until this plan ships `fred_cli.py` (verified pre-task: `uv run pytest tests/test_fred_cli.py -v` reported `5 xfailed`).
- **GREEN gate:** Commit `7529585` (`feat(12-01): ship fred_cli.py HTTP wrapper + flip LIVE-01/LIVE-04 xfails`) — single atomic commit pairing implementation with xfail removal so the RED → GREEN transition is observable in one diff (verified post-task: `uv run pytest tests/test_fred_cli.py -v` reports `5 passed`).
- **REFACTOR gate:** Not exercised (no separate refactor commit needed; the auto-fix lint corrections were applied during the GREEN commit's verification loop, before commit).

Gate sequence: `ec6363e` (RED) → `7529585` (GREEN). No TDD gate-sequence violations.

## User Setup Required

None — no external service configuration needed for this plan's done criteria. The plan tests use `monkeypatch.delenv("FRED_API_KEY")` to exercise the no-key envelope path.

For the success-envelope branch to run live (manual smoke), the user would set `FRED_API_KEY` in their environment per https://fred.stlouisfed.org/docs/api/api_key.html — but this is not required by any gate in this plan. Plan 12-08 (`references/fred-context.md`) will document the FRED_API_KEY setup recipe for end-users.

## Next Phase Readiness

- **Plan 12-02 (LIVE-03 — `lib/fred_cache.py`)**: The HTTP fetch block in `fred_cli.py` lines 133-203 is the landing target — `lib.fred_cache.get_cached_or_fetch(series_id)` will replace it. The redacted source_url shape is already in the right form for the cache writer to persist (T-12-01-02 carries forward).
- **Plan 12-03 (LIVE-02 — SKILL.md FRED section)**: The script's allowlist (`ALLOWED_SERIES`) + envelope contract is the surface that SKILL.md prose-only injection cites. The TODO marker in the module docstring keeps the Plan 12-02 split visible to Plan 12-03 implementation.
- **Plan 12-04 (EVAL-03 + EVAL-04)**: `evals/runner.py`'s STDOUT-only hallucination detector (D-12-SC3-01) can use this script's envelope as a positive provenance test fixture — `value` is sourced from stdout, NOT prose.
- **Plan 12-08 (`references/fred-context.md`)**: Documents `fred_cli.py` as the canonical HTTP wrapper path AND the MCP server (`stefanoamorelli/fred-mcp-server`) as an optional secondary path per D-12-LIVE01-01.
- **No blockers** — every downstream Phase 12 wave has its landing point pinned by this plan's surface.

## Self-Check: PASSED

Verified each created/modified file exists and the commit is in `git log`:

- FOUND: `.claude/skills/mortgage-ops/scripts/fred_cli.py` (212 lines; `wc -l` confirmed)
- FOUND: `tests/test_fred_cli.py` (modified — 4 xfail decorators removed, ruff format applied)
- FOUND commit: `7529585` (`feat(12-01): ship fred_cli.py HTTP wrapper + flip LIVE-01/LIVE-04 xfails`)

Verification commands ran successfully:

- `test -f .claude/skills/mortgage-ops/scripts/fred_cli.py` → exit 0
- `grep -q 'ALLOWED_SERIES = ("MORTGAGE30US", "MORTGAGE15US")' .claude/skills/mortgage-ops/scripts/fred_cli.py` → exit 0
- `grep -q 'api_key=\*\*\*' .claude/skills/mortgage-ops/scripts/fred_cli.py` → exit 0
- `grep -q 'timeout=10' .claude/skills/mortgage-ops/scripts/fred_cli.py` → exit 0
- `! grep -qE '^import urllib|^from urllib' .claude/skills/mortgage-ops/scripts/fred_cli.py` → exit 0 (no top-level urllib imports — lazy-import discipline holds)
- `grep -c 'pytest.mark.xfail' tests/test_fred_cli.py` → 0 (all xfails removed)
- `uv run pytest tests/test_fred_cli.py -v` → 5 passed in 0.23s
- `uv run mypy --strict .claude/skills/mortgage-ops/scripts/fred_cli.py` → Success: no issues found in 1 source file
- `uv run mypy tests/test_fred_cli.py` → Success: no issues found in 1 source file
- `uv run ruff check .claude/skills/mortgage-ops/scripts/fred_cli.py tests/test_fred_cli.py` → All checks passed!
- `uv run ruff format --check .claude/skills/mortgage-ops/scripts/fred_cli.py tests/test_fred_cli.py` → 2 files already formatted
- `uv run pytest` (full suite) → 605 passed, 5 skipped, 25 xfailed in 45.27s (was 600 / 5 / 30 — net +5 passing, -5 xfailed, zero regressions)
- Smoke: `python3 .claude/skills/mortgage-ops/scripts/fred_cli.py --help` → exit 0 in ~0.05s (well under 300ms gate)
- Smoke: `FRED_API_KEY= python3 .claude/skills/mortgage-ops/scripts/fred_cli.py MORTGAGE30US --latest` → exit 0; stdout = `{"series_id": "MORTGAGE30US", "value": null, ..., "error": "FRED_API_KEY not set in environment; ask the user for the current rate."}`
- Smoke: `python3 .claude/skills/mortgage-ops/scripts/fred_cli.py BADSERIES` → exit 2 (argparse `invalid choice` message; T-12-01-01 mitigation verified)

---
*Phase: 12-fred-eval*
*Plan: 01 — fred-cli HTTP wrapper*
*Completed: 2026-05-13*
