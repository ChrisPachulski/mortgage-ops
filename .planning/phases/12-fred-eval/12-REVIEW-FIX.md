---
phase: 12-fred-eval
fixed_at: 2026-05-13T20:30Z
review_path: .planning/phases/12-fred-eval/12-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-05-13T20:30Z
**Source review:** `.planning/phases/12-fred-eval/12-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (2 BLOCKER + 5 WARNING, 0 info)
- Fixed: 7
- Skipped: 0

**Verification:**
- `uv run python -m pytest -q` → 644 passed, 5 skipped, 1 xfailed, 0 failed (baseline was 639; 5 net new regression tests added: 2 for CR-01, 2 for CR-02, 1 for WR-05).
- `uv run python -m evals.runner` → `route_match_rate=1.0`, `numeric_match_rate=1.0`, exit 0.
- `uv run mypy --strict` clean on every touched file.
- `uv run ruff check` clean on every touched file.

**Note on WR-04 bundling:** WR-04 was applied alongside CR-02 in commit `2ff6450`
because the WR-04 directive explicitly conditioned the docstring update on
"after CR-01 + CR-02 are applied" — the honest enumeration of raised exceptions
(`NotImplementedError`, `FredCacheLockError`, `OSError`/`PermissionError`) is
load-bearing for the CR-02 caller contract.

## Fixed Issues

### CR-01: Malformed cache file crashes `fred_cli.py` with uncaught `KeyError`

**Files modified:** `lib/fred_cache.py`, `tests/test_fred_cache.py`
**Commit:** `7a873ec`
**Applied fix:** Added `REQUIRED_ENTRY_FIELDS = ("value", "fetched_at")` constant
and a shape-validate guard in `_load_cache` — entries missing either field
return `None` (falls through to fetcher refetch path) instead of propagating
a `KeyError` from `is_fresh`. Added two regression tests:
`test_malformed_cache_entry_missing_fetched_at_falls_through_to_fetcher` and
`test_malformed_cache_entry_missing_value_falls_through_to_fetcher`.

### CR-02: Lock timeout + disk-write OSError crash `fred_cli.py`

**Files modified:** `.claude/skills/mortgage-ops/scripts/fred_cli.py`, `lib/fred_cache.py`, `tests/test_fred_cli.py`
**Commit:** `2ff6450`
**Applied fix:** Wrapped the `get_cached_or_fetch` call in `fred_cli.main()`
with `try / except Exception` that converts any cache-layer exception to
the standard error envelope (`error` field populated, exit 0). Updated
`get_cached_or_fetch` docstring (WR-04) to enumerate raised exceptions
honestly: `NotImplementedError`, `FredCacheLockError`,
`OSError`/`PermissionError`. Added two regression tests using an inline
subprocess with `lib.fred_cache._save_cache` monkey-patched to raise
`FredCacheLockError` and `PermissionError` respectively — both assert
exit 0 + populated envelope `error` field.

### WR-01: `fred-context.md` references non-existent fixture filename

**Files modified:** `.claude/skills/mortgage-ops/references/fred-context.md`
**Commit:** `7a077a9`
**Applied fix:** Changed line 400 from `MORTGAGE30US-2026-05-10.json` to
`MORTGAGE30US-2026-05-13.json` (matches actual fixture on disk). Verified
the other two `2026-05-10` occurrences in the file (lines 6 and 527) are
unrelated FRED-docs / research-audit timestamps and left intact.

### WR-02: `fred_cli.py` docstring overstates "always exits 0"

**Files modified:** `.claude/skills/mortgage-ops/scripts/fred_cli.py`
**Commit:** `6a10f83`
**Applied fix:** Narrowed the claim in both the module docstring (line 9
area) and the `--help` epilog to "Always exits 0 once arguments parse;
argparse exits 2 on parse errors per stdlib convention" with a note that
SKILL.md only invokes with allowlisted args so the parse-error path never
fires in production.

### WR-03: SKILL.md shell-injection guard test is narrower than D-12-LIVE02-01

**Files modified:** `tests/test_skill_md_fred.py`
**Commit:** `f314011`
**Applied fix:** Broadened the forbidden-syntax regex from
`r"!`[^`]*fred[^`]*`"` to `r"(?<![\\])!`[^`\n]+`"` — now catches ALL
backtick-shell-injection forms (e.g. `!`bash scripts/foo.sh``), not
just commands mentioning `fred`. The negative-lookbehind `(?<![\\])`
allows escaped `\!` so prose can safely discuss the syntax. SKILL.md
still passes (no `!`-syntax present).

### WR-04: `get_cached_or_fetch` docstring claims "Never raises"

**Files modified:** `lib/fred_cache.py` (bundled into CR-02 commit)
**Commit:** `2ff6450`
**Applied fix:** Replaced the false "Never raises (delegates to fetcher's
error envelope)" line with an explicit `Raises:` block enumerating
`NotImplementedError`, `FredCacheLockError`, and `OSError`/`PermissionError`,
plus a note pointing at the CR-02 catch-all in `fred_cli.py:main()` as
the upstream-catch contract. Includes a back-reference to CR-01 noting
the prior `KeyError` path was closed via `_load_cache` shape validation.

### WR-05: Runner CLI silently expands single-file arg to parent directory

**Files modified:** `evals/runner.py`, `tests/test_evals_runner.py`
**Commit:** `a93c6d4`
**Applied fix:** Replaced the silent `target.parent` expansion with
`parser.error("single-file scoring not supported in v1; pass a directory. Got: {target}")`
when `target.is_dir()` is False. Single-file scoring is deferred to v1.1.
Added regression test `test_runner_main_fails_loudly_on_single_file_input`
asserting `SystemExit(2)` + stderr message.

## Skipped Issues

None — all 7 in-scope findings were successfully fixed.

---

_Fixed: 2026-05-13T20:30Z_
_Fixer: gsd-code-fixer_
_Iteration: 1_
