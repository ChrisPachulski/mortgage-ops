---
phase: 12-fred-eval
reviewed: 2026-05-13T19:26Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - .claude/skills/mortgage-ops/scripts/fred_cli.py
  - lib/fred_cache.py
  - evals/__init__.py
  - evals/runner.py
  - evals/metrics.py
  - tests/test_fred_cli.py
  - tests/test_fred_cache.py
  - tests/test_evals_runner.py
  - tests/test_evals_metrics.py
  - tests/test_evals_coverage.py
  - tests/test_skill_md_fred.py
  - .claude/skills/mortgage-ops/SKILL.md
  - .claude/skills/mortgage-ops/references/fred-context.md
  - .claude/agents/README.md
  - CLAUDE.md
  - pyproject.toml
  - .github/workflows/ci.yml
  - .gitignore
  - tests/fixtures/fred/README.md
  - tests/fixtures/fred/MORTGAGE30US-2026-05-13.json
  - tests/fixtures/fred/MORTGAGE15US-2026-05-13.json
  - tests/fixtures/fred/stale_8_day_cache.json
  - evals/expected/live-rate-injection-01.json
  - evals/expected/evaluate-01.json
  - evals/expected/compare-01.json
  - evals/prompts/live-rate-injection-01.md
  - evals/prompts/evaluate-01.md
findings:
  critical: 2
  warning: 5
  info: 0
  total: 7
status: issues_found
---

# Phase 12: Code Review Report

**Implementation faithfully executes the 5 D-12 locks.** Eval gate runs green
end-to-end (13 pass / 0 fail / 9 skip / rate 1.0 / exit 0), 22 oracles share
consistent schema, `api_key=***` redaction is correct, urllib timeout is
enforced, ALLOWED_SERIES allowlist prevents URL injection, 7-day strict-`<`
TTL boundary is freezegun-tested, SKILL.md `## Live Mortgage Rates` is
prose-only (no `` !` `` syntax).

The 2 BLOCKERS are both contract violations of "always exit 0 with JSON envelope"
(D-12-LIVE02-01 + Pitfall 1): exceptions escape `get_cached_or_fetch` and
crash `scripts/fred_cli.py` with a Python traceback + non-zero exit, defeating
SKILL.md's prose-only recovery.

---

## BLOCKER

### CR-01: Malformed cache file crashes `fred_cli.py` with uncaught `KeyError`

**Files:** `lib/fred_cache.py:103-113` (`is_fresh`) + `:290-327` (`get_cached_or_fetch`); `.claude/skills/mortgage-ops/scripts/fred_cli.py:207`

`is_fresh(entry)` does `entry["fetched_at"]` without defensive handling. `_load_cache` only validates `schema_version` and `isinstance(entry, dict)` — it does NOT validate required fields. A cache file whose entry is missing `fetched_at` raises `KeyError`, which propagates through `get_cached_or_fetch` → `main():207` (no try/except) → traceback on stderr + non-zero exit. Breaks D-12-LIVE02-01 + Pitfall 1.

`get_cached_or_fetch` docstring at `lib/fred_cache.py:311` claims "Never raises (delegates to fetcher's error envelope)" — that claim is **false**.

No test exercises this path.

**Fix:** Either (a) guard `is_fresh` against shape mismatch, (b) validate shape in `_load_cache`, or (c) catch-all in `fred_cli.py:main()`. Option (b) is cleanest:
```python
REQUIRED_FIELDS = ("value", "fetched_at")
if isinstance(entry, dict) and all(k in entry for k in REQUIRED_FIELDS):
    return entry
return None  # malformed entry → refetch
```
Add regression test that seeds malformed cache and asserts fall-through to fetcher.

### CR-02: Lock timeout + disk-write OSError crash `fred_cli.py` — same contract violation

**Files:** `lib/fred_cache.py:206-209` + `:277-287`; `.claude/skills/mortgage-ops/scripts/fred_cli.py:207`

Three additional uncaught exception paths:
1. `FredCacheLockError` from `_acquire_lock` after 30s timeout
2. `OSError`/`PermissionError` from `Path.write_text` in `_save_cache`
3. `OSError` from `cache_dir.mkdir` in `_acquire_lock`

All propagate to `fred_cli.py:main()` → traceback + non-zero exit. No test exercises lock-timeout (`test_cache_write_acquires_lock` is happy-path only).

**Fix:** Outermost catch-all in `fred_cli.py:main()`:
```python
try:
    return _emit(get_cached_or_fetch(series_id, fetcher=_fetcher))
except Exception as exc:
    return _emit({
        "series_id": series_id, "value": None, "observation_date": None,
        "fetched_at": None, "source_url": redacted_url,
        "fred_realtime_start": None, "fred_realtime_end": None,
        "error": f"FRED cache failure: {exc!r}",
    })
```
Also update `lib/fred_cache.py:get_cached_or_fetch` docstring to honestly enumerate raised exceptions.

---

## WARNING

### WR-01: `fred-context.md` references non-existent fixture filename

**File:** `.claude/skills/mortgage-ops/references/fred-context.md:400`

References `tests/fixtures/fred/MORTGAGE30US-2026-05-10.json` but the actual file is `MORTGAGE30US-2026-05-13.json`. Same drift that Wave 5 SUMMARY flagged and fixed in `tests/fixtures/fred/README.md`, but this doc was missed.

**Fix:** `s/2026-05-10/2026-05-13/` in `fred-context.md:400`.

### WR-02: `fred_cli.py` docstring overstates "always exits 0"

**File:** `.claude/skills/mortgage-ops/scripts/fred_cli.py:9, 60`

Module docstring + `--help` epilog promise "Always exits 0", but `argparse` exits 2 on parse errors. SKILL.md only invokes with allowlisted args so this never fires in production, but the contract is overstated.

**Fix:** Narrow the claim to "Always exits 0 once arguments parse" OR override `argparse.ArgumentParser.error()` to emit the JSON envelope.

### WR-03: SKILL.md shell-injection guard test is narrower than D-12-LIVE02-01

**File:** `tests/test_skill_md_fred.py:53-70`

Test regex `r"!`[^`]*fred[^`]*`"` only catches `fred`-mentioning injection. D-12-LIVE02-01 forbids ALL `!`...`` syntax. A future edit introducing `` !`bash scripts/foo.sh` `` (no `fred` mention) would not trip the test.

**Fix:** Broaden regex: `r"(?<![\\])!`[^`\n]+`"`.

### WR-04: `get_cached_or_fetch` docstring claims "Never raises" — load-bearing and misleading

**File:** `lib/fred_cache.py:311`

Function actually raises `KeyError`, `NotImplementedError`, `FredCacheLockError`, `OSError`. The misleading claim is load-bearing because `fred_cli.py:207` relies on it.

**Fix:** After CR-01 + CR-02, update docstring to enumerate raised exceptions honestly.

### WR-05: Runner CLI silently expands single-file arg to parent directory

**File:** `evals/runner.py:283-286`

`if target.is_file(): prompts_dir = target.parent` silently re-scores all 22 prompts when user passes a single `.md` file. argparse help says "Prompt file or directory" but file-mode is broken.

**Fix:** Either support single-file scoring or `parser.error()` on file input.

---

## Confirmed clean

- All 5 D-12 locks honored verbatim
- 22 oracles share consistent schema_version, mode, numeric_status, expected_route_keywords
- `api_key=***` redaction correct
- urllib 10s timeout enforced
- 7-day strict-`<` TTL boundary exercised by freezegun (6d23h59m / 7d / 8d)
- SKILL.md prose-only — no `!`-syntax anywhere
- No `Co-Authored-By` / `🤖` / `claude.com` markers across all Phase 12 commits
- Eval gate: `route_match_rate=1.0`, `numeric_match_rate=1.0`, exit 0
- pytest: 639 passed, 5 skipped, 1 xfailed (pre-existing Phase 5 ARM oracle), 0 failed

## Items considered and dismissed (INFO-level, not findings)

- `_save_cache` writes not atomic (truncate+write window). v1 single-user use; performance concern only.
- Schema-mismatch silent downgrade on read. Not active at v1 (SCHEMA_VERSION=1).
- `live-rate-injection-01` keyword `"6.50"` is substring of `"6.500%"`. D-NUM-02 compliance protects.
- Stub-mode preamble synthesis weakens route_match in stub mode — intentional per runner docstring; flagged in 12-RESEARCH.md as Phase 13+ live-mode closure.
- `_release_lock` only catches `FileNotFoundError` — edge case.
