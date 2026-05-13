---
phase: 12-fred-eval
plan: 02
subsystem: fred-cache
tags: [phase-12, wave-2, fred-cache, ttl, lockfile, live-03, sc-2]

# Dependency graph
requires:
  - phase: 12-fred-eval
    plan: 00
    provides: tests/test_fred_cache.py 4 strict-xfail stubs (LIVE-03 + SC-2 boundary + lock contract) — this plan flips them to live
  - phase: 12-fred-eval
    plan: 01
    provides: .claude/skills/mortgage-ops/scripts/fred_cli.py with the lazy-import seam and redacted_url shape this plan reuses inside the _fetcher closure
  - phase: 09-persistence
    provides: orchestration/lockfile.mjs withLock pattern (60s acquired_at-based stale recovery, read-back-verify CAS NOT O_EXCL) — Python-ported into lib.fred_cache.with_cache_lock
  - phase: 01-foundation
    provides: lib/rules/_loader.StaleReferenceWarning idiom mirrored as lib.fred_cache.StaleCacheWarning (12-month threshold there; 7-day here)
provides:
  - lib/fred_cache.py module surface — is_fresh, warn_if_stale, with_cache_lock, get_cached_or_fetch, StaleCacheWarning, FredCacheLockError, FredCacheSchemaError
  - 7-day TTL strict-< boundary semantic verified by freezegun-driven tests at 6d23h59m fresh / 7d exact stale / 8d stale
  - Python port of orchestration/lockfile.mjs:withLock with full 1:1 invariant parity (60s stale, read-back-verify CAS, JSON-content acquired_at)
  - get_cached_or_fetch read-through fetcher-injection contract (lib.fred_cache stays pure; urllib coupling lives in fred_cli)
  - tests/fixtures/fred/stale_8_day_cache.json fixture pinned to fetched_at 2026-04-25T12:00:00Z (8d-stale relative to 2026-05-03T12:00:00Z test now)
affects: [fred-cli (now cache-first), plan 12-03 (SKILL.md prose-only injection cites the cache files this writes), plan 12-04 (evals/runner.py reads cache value via Read tool for SC-1 closure), plan 12-08 (references/fred-context.md documents cache schema)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Python port of orchestration/lockfile.mjs:withLock (NEW pattern; first cross-language port of the Phase 9 lockfile idiom — 1:1 invariant table below)
    - Read-through cache with injected fetcher (NEW pattern; lib stays urllib-free, fred_cli supplies the closure)
    - Hand-built redacted_url captured by fetcher closure (carried forward from Plan 12-01 T-12-01-02; api_key never str-interpolated into output channels)
    - Inherited: StaleReferenceWarning idiom (UserWarning subclass + warnings.warn with stacklevel=2 + module-level constants)
    - Inherited: Wave-0-strict-xfail-then-flip discipline (4 xfails removed; 2 new integration tests ship green)

key-files:
  created:
    - lib/fred_cache.py
    - tests/fixtures/fred/stale_8_day_cache.json
  modified:
    - .claude/skills/mortgage-ops/scripts/fred_cli.py (unconditional urllib block → _fetcher closure dispatched through get_cached_or_fetch; ~70 LOC of inline fetch refactored into the cache-first wrapper)
    - tests/test_fred_cache.py (4 @pytest.mark.xfail decorators removed; 2 new integration tests for get_cached_or_fetch added; module docstring updated to reflect Wave-2 live state)

key-decisions:
  - "Lock semantics ported verbatim from orchestration/lockfile.mjs — STALE_THRESHOLD=60s, DEFAULT_TIMEOUT=30s, POLL_INTERVAL=100ms, JSON-content acquired_at not mtime, read-back-verify CAS NOT O_EXCL (per Phase 9 D-01-01/02 inheritance)"
  - "Strict-< TTL boundary (NOT <=) — age == 7d EXACTLY counts as stale, documented in is_fresh docstring with citation to RESEARCH §Pitfall 2 Thursday-noon-ET boundary rationale"
  - "Per-series cache file (data/cache/fred_{series_id}.json) NOT consolidated fred-cache.json — D-12-LIVE02-01 SKILL.md citations + Plan 12-01 inheritance pinned this shape"
  - "Schema wrapper {schema_version: 1, entries: {series_id: ...}} — single-entry-per-file in v1, but the dict wrapping makes a future consolidation pass byte-compatible with RESEARCH §Pattern 2 lines 204-227"
  - "Fetcher-injection contract: get_cached_or_fetch accepts a Callable[[str], dict] keyword arg; lib.fred_cache stays urllib-free and the fred_cli _fetcher closure captures api_key + redacted_url from the enclosing main() scope"
  - "Default fetcher (when fetcher=None) raises NotImplementedError NOT a silent fallback — explicit failure when a caller forgets to inject the fetcher, vs accidental network-on-import"
  - "contextlib.suppress(FileNotFoundError) for the lock release path (SIM105 lint compliance + clearer intent than try/except/pass)"

requirements-completed: [LIVE-03]

# Metrics
duration: ~15min
completed: 2026-05-10
---

# Phase 12 Plan 02: fred-cache Summary

**`lib/fred_cache.py` ships with 7-day TTL strict-`<` boundary + Python port of `orchestration/lockfile.mjs:withLock` + read-through `get_cached_or_fetch`; `scripts/fred_cli.py` wired cache-first via injected `_fetcher` closure; 4 Wave-0 LIVE-03 xfails flipped + 2 new integration tests ship green.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 1 (single TDD-flow GREEN task — Wave-0 commit `ec6363e` was the RED gate; Plan 12-01's GREEN commit `7529585` is the upstream Wave 1 baseline this plan extends)
- **Files created:** 2 (`lib/fred_cache.py` 327 lines; `tests/fixtures/fred/stale_8_day_cache.json` 13 lines)
- **Files modified:** 2 (`.claude/skills/mortgage-ops/scripts/fred_cli.py` cache-first rewire; `tests/test_fred_cache.py` 4 xfails flipped + 2 new tests)
- **Tests delta:** +6 passing (611 vs Wave-1 baseline of 605); xfails 25 → 21

## Accomplishments

### `lib/fred_cache.py` (~330 lines including docstrings + comments)

**Constants** (PINNED by 12-PATTERNS.md + D-12-LIVE02-01):

| Constant | Value | Rationale |
|----------|-------|-----------|
| `CACHE_DIR` | `Path(__file__).parent.parent / "data" / "cache"` | repo-relative; `lib/` is one level deep from repo root |
| `CACHE_TTL` | `timedelta(days=7)` | SC-2 7-day TTL; strict-`<` means age == 7d EXACTLY is stale |
| `LOCK_FILENAME` | `".fred-cache.lock"` | gitignored per Plan 12-00 |
| `STALE_THRESHOLD` | `timedelta(milliseconds=60_000)` | mirror `lockfile.mjs:STALE_THRESHOLD_MS = 60_000` |
| `DEFAULT_TIMEOUT` | `timedelta(milliseconds=30_000)` | mirror `lockfile.mjs:DEFAULT_TIMEOUT_MS = 30_000` |
| `POLL_INTERVAL` | `0.1` (sec) | mirror `lockfile.mjs:POLL_INTERVAL_MS = 100ms` |
| `SCHEMA_VERSION` | `1` | bump on cache JSON shape change |

**Exceptions / warnings:**

- `StaleCacheWarning(UserWarning)` — emitted by `warn_if_stale` when entry is older than 7d. Mirrors `StaleReferenceWarning` idiom (12mo threshold there; 7d here).
- `FredCacheLockError(RuntimeError)` — raised when `with_cache_lock` cannot acquire within `DEFAULT_TIMEOUT`. Carries blocker JSON in `str(exc)`.
- `FredCacheSchemaError(ValueError)` — defined for future explicit-validate paths. `_load_cache` returns `None` on `schema_version` mismatch (caller falls through to fetch).

**Public functions:**

- `is_fresh(entry: dict) -> bool` — strict-`<` TTL check; parses `fetched_at` ISO-8601 (with `Z` suffix or `+00:00` offset).
- `warn_if_stale(entry: dict) -> None` — emits `StaleCacheWarning` if stale; never raises. Loud-by-default per project convention.
- `with_cache_lock(cache_dir=CACHE_DIR, *, timeout=DEFAULT_TIMEOUT, reason="")` — `@contextmanager` yielding the lock JSON; releases on exit (even on exception).
- `get_cached_or_fetch(series_id, *, cache_dir=CACHE_DIR, fetcher=None) -> dict` — read-through. Fresh → return cached entry (no fetcher invocation). Stale/missing → invoke fetcher and write-through if `value` is non-None.

**Private helpers:**

- `_now_utc`, `_now_ms` — single seams for freezegun freezing / Node-parity epoch-ms timing.
- `_read_lock`, `_is_lock_stale`, `_acquire_lock`, `_release_lock` — port of `readLock` / `isStale` / `acquireLock` / `releaseLock` from `lockfile.mjs`.
- `_cache_path`, `_load_cache`, `_save_cache` — per-series file I/O (`fred_{series_id}.json`); `_save_cache` writes inside `with_cache_lock`.

### Python port: `orchestration/lockfile.mjs` → `lib.fred_cache.with_cache_lock`

| `lockfile.mjs` (JS) | `lib.fred_cache` (Python) | Invariant |
|---------------------|---------------------------|-----------|
| `STALE_THRESHOLD_MS = 60_000` | `STALE_THRESHOLD = timedelta(milliseconds=60_000)` | 60s stale-recovery threshold |
| `DEFAULT_TIMEOUT_MS = 30_000` | `DEFAULT_TIMEOUT = timedelta(milliseconds=30_000)` | 30s acquire timeout |
| `POLL_INTERVAL_MS = 100` | `POLL_INTERVAL = 0.1` (sec for `time.sleep`) | 100ms poll cadence |
| `readLock()` | `_read_lock(lock_path)` | Return parsed JSON or `None` on absent/corrupt |
| `isStale(lock)` | `_is_lock_stale(lock)` | `None` lock → stale; missing/non-numeric `acquired_at` → stale; `now - acquired_at > 60_000` → stale |
| `acquireLock({timeoutMs, reason})` | `_acquire_lock(cache_dir, *, timeout, reason)` | Read-back-and-verify CAS (poll until deadline) |
| `writeFileSync(LOCK_PATH, ..., {flag:'w'})` | `lock_path.write_text(json.dumps(...))` | flag='w' equivalent (NOT `O_EXCL`) |
| Read-back verify: `readBack.pid == process.pid && readBack.acquired_at == myLock.acquired_at` | `read_back.get("pid") == my_lock["pid"] and read_back.get("acquired_at") == my_lock["acquired_at"]` | Poor-man's CAS — only return after re-read confirms our write |
| `releaseLock(myLock)` | `_release_lock(cache_dir, my_lock)` | Only `unlink` if existing lock's pid+acquired_at match ours |
| `withLock(fn, opts)` | `with_cache_lock(cache_dir, *, timeout, reason)` | Context manager (Python) vs HOF (JS); same lifecycle |
| `throw new Error('Lock acquire timeout ... Blocker: ...')` | `raise FredCacheLockError('Lock acquire timeout ... Blocker: ...')` | Same blocker-JSON-in-message pattern |

The Python port preserves all 4 invariants from `lockfile.mjs` lines 6-18:

1. **60s stale recovery** — `_is_lock_stale` uses `acquired_at` from JSON content, NOT mtime (Phase 9 D-01-02 inheritance — mtime is vulnerable to `touch` + clock-skew).
2. **NOT O_EXCL** — `lock_path.write_text(...)` is `O_TRUNC | O_CREAT | O_WRONLY` equivalent; O_EXCL would crash on every acquire because the stale lock is still on disk.
3. **Read-back-verify CAS** — after writing, we re-read and confirm our pid + acquired_at survived (handles racy parallel writers).
4. **PID + acquired_at ownership check on release** — `_release_lock` only unlinks if the on-disk lock's pid+acquired_at still match ours (prevents stomping a successor process's lock).

### Strict-`<` TTL boundary semantic (LOCKED by D-12-LIVE02-01 + RESEARCH §Pitfall 2)

```python
def is_fresh(entry: dict[str, Any]) -> bool:
    ...
    age = _now_utc() - fetched_at
    return age < CACHE_TTL  # strict <, NOT <=
```

Three test boundaries (all driven via `freezegun.freeze_time`):

| Boundary | `fetched_at` | `now` | Age | `is_fresh` | Test |
|----------|--------------|-------|-----|-----------|------|
| 6d 23h 59m 59s | `2026-04-25T12:00:00Z` | `2026-05-02T11:59:59Z` | `6d 23h 59m 59s` | **True** (fresh) | `test_six_d_twenty_three_h_old_cache_is_fresh` |
| 7d 0h 0s (EXACT) | `2026-04-25T12:00:00Z` | `2026-05-02T12:00:00Z` | `7d 0h 0s` | **False** (stale) | `test_seven_d_exactly_old_cache_is_stale` |
| 8d 0h 0s | `2026-04-25T12:00:00Z` | `2026-05-03T12:00:00Z` | `8d 0h 0s` | **False** (stale) | `test_eight_d_old_cache_triggers_refetch` |

The 8d case ALSO asserts `warn_if_stale` emits `StaleCacheWarning` via `pytest.warns(...)`.

### Per-series cache file layout (NOT consolidated `fred-cache.json`)

- **Path:** `data/cache/fred_{series_id}.json` (one file per series — `MORTGAGE30US` lands at `fred_MORTGAGE30US.json`, `MORTGAGE15US` at `fred_MORTGAGE15US.json`).
- **Schema** (PINNED by 12-RESEARCH.md §Pattern 2 lines 204-227):
  ```json
  {
    "schema_version": 1,
    "entries": {
      "MORTGAGE30US": {
        "value": "6.84",
        "observation_date": "2026-04-25",
        "fetched_at": "2026-04-26T17:00:03Z",
        "source_url": "...api_key=***...",
        "fred_realtime_start": "2026-04-26",
        "fred_realtime_end": "2026-04-26",
        "error": null
      }
    }
  }
  ```
- **Why per-series + dict-wrapped:** D-12-LIVE02-01 SKILL.md citations pin the per-series shape (the prose-only injection cites discrete cache files). The `entries: {series_id: ...}` dict wrapping mirrors RESEARCH §Pattern 2 byte-for-byte so a future consolidation pass would be a single-file `cat`-and-deep-merge instead of a schema migration.
- **`value` is a JSON string** ("6.84" not 6.84) per project D-19 money discipline — JSON floats are forbidden at any boundary.

### `scripts/fred_cli.py` wiring point: the `_fetcher` closure

The Wave 1 plan left this comment block as the wiring marker:
```
    # Cache-first path: Plan 12-02 ships lib.fred_cache with read-through semantics
    # ...
```

Wave 2 replaces ~70 LOC of inline urllib fetch with:

```python
    from lib.fred_cache import get_cached_or_fetch

    redacted_url = (...)  # hand-built; T-12-01-02 mitigation carried forward

    def _fetcher(sid: str) -> dict[str, Any]:
        """urllib-based FRED fetcher. ALWAYS returns an envelope; NEVER raises.

        Closure captures api_key + redacted_url from the enclosing main()
        scope so the lib.fred_cache module stays pure (no urllib / no HTTP /
        no env-var coupling).
        """
        ...  # same three exception arms as Wave 1

    return _emit(get_cached_or_fetch(series_id, fetcher=_fetcher))
```

The closure pattern keeps `lib.fred_cache` urllib-free and env-var-free — important because:

1. **Tests can inject stub fetchers** without monkey-patching urllib (see `test_get_cached_or_fetch_returns_cached_when_fresh` and `test_get_cached_or_fetch_invokes_fetcher_when_stale`).
2. **No accidental network-on-import** if `lib.fred_cache` is loaded outside `fred_cli` (e.g., from a future skill-side cache pre-warm script).
3. **api_key + redacted_url stay in fred_cli's scope** — the cache library never sees the real key (T-12-01-02 enforced by structure, not runtime sanitization).
4. **Plan 12-01's three exception arms preserved verbatim** (URLError/HTTPError/OSError/TimeoutError; KeyError/IndexError/JSONDecodeError) — the always-exit-0 envelope contract from Pitfall 1 + D-12-LIVE02-01 is unchanged.

### Test deltas

**Flipped (4 xfails → passing):**

1. `test_six_d_twenty_three_h_old_cache_is_fresh` — strict-`<` fresh boundary at 6d23h59m59s.
2. `test_seven_d_exactly_old_cache_is_stale` — strict-`<` stale boundary at exactly 7d.
3. `test_eight_d_old_cache_triggers_refetch` — 8d → stale + `StaleCacheWarning` emitted.
4. `test_cache_write_acquires_lock` — `with_cache_lock` creates `.fred-cache.lock` with `{pid, acquired_at, ...}` JSON content for the duration of the with-block; releases on exit.

**Added (2 new tests, ship green):**

5. `test_get_cached_or_fetch_returns_cached_when_fresh` — fresh entry in `tmp_path` cache → fetcher is NOT invoked, cached `value` returned.
6. `test_get_cached_or_fetch_invokes_fetcher_when_stale` — stale entry → fetcher invoked exactly once → cache file rewritten with new `value`.

Both new tests use `_save_cache` directly (not the live `fred_cli` script) so they exercise the library contract independently of urllib.

## Task Commits

1. **Task 1 (GREEN gate): ship lib/fred_cache.py + wire fred_cli through get_cached_or_fetch** — `dc37a9a` (feat). Single atomic commit pairing the new module + fixture + cli rewire + xfail flips + new integration tests. The TDD RED gate is the pre-existing Wave-0 commit `ec6363e`.

_Commit used `--no-verify` per parallel-executor protocol. No Co-Authored-By or AI-attribution trailers per global CLAUDE.md rule + project CLAUDE.md._

## Files Created/Modified

### Created
- **`lib/fred_cache.py`** (327 lines, formatted) — full module described above. Section organization: header docstring → constants → exceptions/warnings → TTL freshness → lockfile port → read-through cache.
- **`tests/fixtures/fred/stale_8_day_cache.json`** (13 lines) — pinned-to-`2026-04-25T12:00:00Z` 8-day-stale fixture used by SC-2 boundary tests when tests freeze to `2026-05-03T12:00:00Z`.

### Modified
- **`.claude/skills/mortgage-ops/scripts/fred_cli.py`** — module docstring updated (cache-integration TODO → cache-integration shipped); ~70 LOC inline urllib fetch replaced by a `_fetcher` closure dispatched through `get_cached_or_fetch`. The fetcher's three exception arms (network/timeout, response-shape, payload) preserved byte-for-byte; the `redacted_url` shape carried forward to keep T-12-01-02 mitigation intact. File grew by 1 net line (the lazy-import of `get_cached_or_fetch` added vs the inline url construction removed).
- **`tests/test_fred_cache.py`** — module docstring flipped from "Wave-0 stubs" to "Wave-2 live"; 4 `@pytest.mark.xfail(...)` decorators removed; 2 new integration tests added (`test_get_cached_or_fetch_returns_cached_when_fresh`, `test_get_cached_or_fetch_invokes_fetcher_when_stale`). `freezegun` already at module top; `pytest` import preserved for `pytest.warns(StaleCacheWarning)`.

## Decisions Made

### Lock semantics: verbatim port of orchestration/lockfile.mjs

Every invariant from `lockfile.mjs`'s header comment (lines 6-18) is mirrored in `lib.fred_cache`:

- **60s `acquired_at`-based stale recovery** — NOT mtime (Phase 9 D-01-02 — mtime is vulnerable to `touch` and fs-clock vs process-clock skew).
- **`writeFileSync(flag:'w')` equivalent** — `lock_path.write_text(...)` is `O_TRUNC | O_CREAT | O_WRONLY`. NOT `O_EXCL` — `O_EXCL` would crash on every acquire because the stale lock from a crashed writer is still on disk; the existing code intentionally OVERWRITES stale locks.
- **Read-back-and-verify CAS** — after writing, re-read and confirm our `pid` + `acquired_at` survived. Handles racy parallel writers.
- **PID + acquired_at ownership on release** — `_release_lock` only `unlink`s if the on-disk lock matches our `pid` + `acquired_at` (prevents stomping a successor process's lock).

### Strict-`<` TTL boundary (NOT `<=`)

```python
return age < CACHE_TTL  # strict less-than
```

- **Why strict-`<`:** FRED publishes weekly on Thursday at noon ET. An entry fetched at Thursday 12:00:01 ET will be exactly 7 days "old" the following Thursday at 12:00:01. The boundary case matters: we want the entry to be refetched on that Thursday's publication window, not narrowly inside the window.
- **Citation:** RESEARCH §Pitfall 2 lines 582-595 + D-12-LIVE02-01.

### Per-series cache file (NOT consolidated)

- **Path shape:** `data/cache/fred_{series_id}.json` (one file per series).
- **Why NOT `data/cache/fred-cache.json` with all series in one file:** D-12-LIVE02-01 specifies the canonical SKILL.md section copy citing discrete cache files (`data/cache/fred_MORTGAGE30US.json`, `data/cache/fred_MORTGAGE15US.json`). A consolidated file would break Plan 12-03's prose-only injection contract because the SKILL.md prose cites discrete Read-tool targets.
- **`entries: {series_id: ...}` dict wrapping:** Even though we ship one file per series in v1, the dict wrapping mirrors RESEARCH §Pattern 2 byte-for-byte. A future consolidation pass would be a single-file `cat`-and-deep-merge, not a schema migration.

### Fetcher-injection contract (lib.fred_cache stays pure)

```python
def get_cached_or_fetch(series_id, *, cache_dir=CACHE_DIR, fetcher=None) -> dict[str, Any]:
    ...
    if fetcher is None:
        raise NotImplementedError(...)  # explicit, NOT silent fallback
    new_entry = fetcher(series_id)
    ...
```

- **Why injection:** `lib.fred_cache` should be unit-testable without `urllib` (or any network). The fetcher contract is "takes `series_id`, returns an envelope `dict`, NEVER raises" — `fred_cli`'s closure satisfies this with the same urllib code Plan 12-01 shipped.
- **Why `NotImplementedError` on missing fetcher (not silent fallback):** if a caller forgets to inject the fetcher, we want an explicit error at the cache-miss boundary, NOT an accidental network call when `lib.fred_cache` is imported by an unrelated future module.
- **What this enables for tests:** the 2 new integration tests use a stub fetcher (just a `list.append` + dict return) to verify cached-when-fresh and stale-triggers-fetch paths without any network coupling.

### contextlib.suppress(FileNotFoundError) on release

```python
with contextlib.suppress(FileNotFoundError):
    lock_path.unlink()
```

- **Why:** SIM105 lint compliance + clearer intent than the `try / except FileNotFoundError: pass` form. The race is the same race `lockfile.mjs:releaseLock` handles (a third process already unlinked our lock — fine, we just need to not crash).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff SIM105 violation on `_release_lock` try/except/pass**
- **Found during:** Task 1 verification (post-Write `ruff check`).
- **Issue:** The first draft of `_release_lock` used `try: lock_path.unlink() except FileNotFoundError: pass` — ruff's SIM105 rule wants this rewritten as `contextlib.suppress(FileNotFoundError)`.
- **Fix:** Added `import contextlib` to the stdlib imports section and replaced the try/except/pass with `with contextlib.suppress(FileNotFoundError): lock_path.unlink()`. Semantically identical; lint-compliant.
- **Files modified:** `lib/fred_cache.py`
- **Verification:** `uv run ruff check lib/fred_cache.py .claude/skills/mortgage-ops/scripts/fred_cli.py tests/test_fred_cache.py` → "All checks passed!".
- **Committed in:** `dc37a9a` (Task 1 commit — same atomic transaction).

**2. [Rule 1 - Bug] ruff format whitespace fix on `lib/fred_cache.py`**
- **Found during:** Task 1 verification (post-lint `ruff format --check`).
- **Issue:** Multi-line dict literal in `_acquire_lock` had whitespace that ruff format wanted to normalize.
- **Fix:** `uv run ruff format lib/fred_cache.py` — whitespace-only changes; semantics unchanged.
- **Files modified:** `lib/fred_cache.py`
- **Verification:** `uv run ruff format --check lib/fred_cache.py .claude/skills/mortgage-ops/scripts/fred_cli.py tests/test_fred_cache.py` → "3 files already formatted".
- **Committed in:** `dc37a9a` (Task 1 commit — same atomic transaction).

---

**Total deviations:** 2 auto-fixed Rule 1 lint conformance bugs (zero Rule 2 missing-critical, zero Rule 3 blocking, zero Rule 4 architectural). Both fixes were narrow lint conformance — zero changes to runtime behavior or test logic.

**Impact on plan:** Zero scope creep. Both fixes serve the plan's stated `<verify>` block (`uv run ruff check ...` clean + `uv run ruff format --check ...` clean are required).

## Known Stubs

None. The plan's deliverables are all real-runtime (no placeholder data, no TODO markers in code). The only stub-like element is `FredCacheSchemaError` which is defined but only triggered indirectly via `_load_cache` returning `None` on `schema_version` mismatch — this is the documented Pydantic-deferred design from the threat model (T-12-02-01: "FredCacheSchemaError defined for future explicit-validate paths; pydantic validation deferred to v2").

## Issues Encountered

- **Plan's verify block uses HTML entities (`&amp;&amp;`, `&lt;`)** — interpreted as `&&` and `<` in the actual shell command. Ran the de-entified form directly.
- **The TODO marker in fred_cli.py's module docstring (left by Plan 12-01)** — this plan rewrote it to reflect the shipped cache integration rather than leaving the stale "Cache integration TODO" line.

## TDD Gate Compliance

Plan 12-02 frontmatter `type: execute` with Task 1 `tdd="true"` — single GREEN-flip task pattern (same shape as Plan 12-01).

- **RED gate:** Wave-0 commit `ec6363e` (`test(12-00): add Wave-0 strict-xfail stubs...`). The 4 strict-xfail stubs for LIVE-03 are anchored with assertions that fail until this plan ships `lib/fred_cache.py` (verified pre-task: `uv run pytest tests/test_fred_cache.py -v` reported `4 xfailed`).
- **GREEN gate:** Commit `dc37a9a` (`feat(12-02): ship lib/fred_cache.py + wire fred_cli through get_cached_or_fetch`) — single atomic commit pairing implementation, fixture, cli rewire, xfail removal, and new integration tests. Verified post-task: `uv run pytest tests/test_fred_cache.py -v` reports `6 passed` (4 flipped + 2 new).
- **REFACTOR gate:** Not exercised (no separate refactor commit needed; the SIM105 + format auto-fixes were applied during the GREEN commit's verification loop, before commit).

Gate sequence: `ec6363e` (RED) → `dc37a9a` (GREEN). No TDD gate-sequence violations.

## User Setup Required

None — no external service configuration needed for this plan's done criteria. The plan tests use `freezegun.freeze_time(...)` + stub fetchers; no real `FRED_API_KEY` involved.

The Wave-1 manual smoke (`FRED_API_KEY=xxx python3 .claude/skills/mortgage-ops/scripts/fred_cli.py MORTGAGE30US`) now writes its result to `data/cache/fred_MORTGAGE30US.json` on success and the second invocation within 7 days will hit the cache instead of FRED — but this is an integration smoke, not a gate.

## Next Phase Readiness

- **Plan 12-03 (LIVE-02 — SKILL.md FRED section):** `lib.fred_cache` writes the per-series cache files (`data/cache/fred_MORTGAGE30US.json`, `data/cache/fred_MORTGAGE15US.json`) that the SKILL.md prose-only injection cites by path. The cache schema (`entries.{series_id}.value`) is the field SKILL.md references in its "see cache file field `value`" prose.
- **Plan 12-04 (EVAL-03 + EVAL-04 — `evals/runner.py` + `evals/metrics.py`):** `lib.fred_cache.get_cached_or_fetch` can be used by `evals/runner.py` to pre-warm or read fixtures during live-rate-injection evaluation (D-12-SC1-01); the synthetic-only-in-CI policy still holds via the `cache_dir` injection.
- **Plan 12-05 (live-rate-injection prompt):** The `tests/fixtures/fred/MORTGAGE30US-2026-05-10.json` fixture (Plan 12-05 will ship) lands directly in the schema this plan locked.
- **Plan 12-08 (`references/fred-context.md`):** Documents the cache schema and `lib.fred_cache` API surface as the canonical reference for SKILL.md routing.
- **No blockers** — every downstream Phase 12 wave has its landing point pinned by this plan's surface.

## Self-Check: PASSED

Verified each created/modified file exists and the commit is in `git log`:

- FOUND: `lib/fred_cache.py` (327 lines after `ruff format`)
- FOUND: `tests/fixtures/fred/stale_8_day_cache.json` (13 lines)
- FOUND: `.claude/skills/mortgage-ops/scripts/fred_cli.py` (modified — `_fetcher` closure + cache-first dispatch)
- FOUND: `tests/test_fred_cache.py` (modified — 4 xfails removed, 2 new integration tests added)
- FOUND commit: `dc37a9a` (`feat(12-02): ship lib/fred_cache.py + wire fred_cli through get_cached_or_fetch`)

Verification commands ran successfully:

- `test -f lib/fred_cache.py` → exit 0
- `grep -q 'CACHE_TTL: Final\[timedelta\] = timedelta(days=7)' lib/fred_cache.py` → exit 0
- `grep -q 'class StaleCacheWarning(UserWarning)' lib/fred_cache.py` → exit 0
- `grep -q 'class FredCacheLockError' lib/fred_cache.py` → exit 0
- `grep -q 'def with_cache_lock' lib/fred_cache.py` → exit 0
- `grep -q 'def get_cached_or_fetch' lib/fred_cache.py` → exit 0
- `grep -q 'age < CACHE_TTL' lib/fred_cache.py` → exit 0
- `grep -q 'STALE_THRESHOLD' lib/fred_cache.py` → exit 0
- `grep -q 'from lib.fred_cache import get_cached_or_fetch' .claude/skills/mortgage-ops/scripts/fred_cli.py` → exit 0
- `test -f tests/fixtures/fred/stale_8_day_cache.json` → exit 0
- `grep -q '2026-04-25T12:00:00Z' tests/fixtures/fred/stale_8_day_cache.json` → exit 0
- `grep -c 'pytest.mark.xfail' tests/test_fred_cache.py` → 0 (all xfails removed)
- `uv run pytest tests/test_fred_cache.py tests/test_fred_cli.py -x -v` → 11 passed in 0.27s
- `uv run mypy --strict lib/fred_cache.py .claude/skills/mortgage-ops/scripts/fred_cli.py` → Success: no issues found in 2 source files
- `uv run ruff check lib/fred_cache.py .claude/skills/mortgage-ops/scripts/fred_cli.py tests/test_fred_cache.py` → All checks passed!
- `uv run ruff format --check lib/fred_cache.py .claude/skills/mortgage-ops/scripts/fred_cli.py tests/test_fred_cache.py` → 3 files already formatted
- `uv run pytest` (full suite) → 611 passed, 5 skipped, 21 xfailed (was 605 / 5 / 25 — net +6 passing, -4 xfailed, zero regressions)
- Smoke: `FRED_API_KEY= python3 .claude/skills/mortgage-ops/scripts/fred_cli.py MORTGAGE30US --latest` → exit 0; stdout = `{"series_id": "MORTGAGE30US", "value": null, ..., "error": "FRED_API_KEY not set..."}` (cache-first contract preserved; no urllib invoked on missing key)
- Smoke: `python3 .claude/skills/mortgage-ops/scripts/fred_cli.py --help` → exit 0 in ~0.05s (D-18 lazy-import discipline holds; `--help` still <300ms gate)

---
*Phase: 12-fred-eval*
*Plan: 02 — fred-cache 7-day TTL + lockfile port*
*Completed: 2026-05-10*
