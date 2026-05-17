---
phase: 13-property-ingestion
plan: 00
subsystem: scaffolding
tags: [phase-13, wave-0-probe, scaffolding, test-infra, deps]
dependency_graph:
  requires:
    - "Phase 11 anthropic SDK dev-dep (now promoted to runtime)"
    - "Phase 12 fred_cache.with_cache_lock primitive (consumed by Wave 5)"
    - "tests/fixtures/subagent_transcripts/README.md (D-02 synthetic policy analog)"
  provides:
    - "5 xfail test scaffolds covering all 7 Phase-13 requirement IDs"
    - "anthropic + duckdb in [project].dependencies (runtime promotion)"
    - "tests/fixtures/zillow/ directory + synthetic-only-in-CI policy README"
    - "data/cache/property-*.html .gitignore entry"
    - "Wave-0 probe outcomes: messages.parse=True (Wave 3 path locked); duckdb 1.5.2"
  affects:
    - "Wave 1 (Plan 13-01): tests/test_property_listing.py xfails ready to flip"
    - "Wave 2 (Plan 13-02): tests/test_property_block_detector.py xfails ready to flip"
    - "Wave 3 (Plan 13-03): tests/test_property_extractor.py xfails ready to flip; messages.parse() path AVAILABLE"
    - "Wave 4 (Plan 13-04): tests/test_property_fetch.py xfails ready to flip"
    - "Wave 5 (Plan 13-05): tests/test_property_persistence.py xfails ready to flip"
    - "Wave 6 (Plan 13-06): tests/fixtures/zillow/{,extracted/} ready for HTML drops"
tech_stack:
  added:
    - "anthropic>=0.100.0,<1.0 (runtime; was dev-only)"
    - "duckdb>=1.4,<2.0 (new runtime; resolved to 1.5.2)"
  patterns:
    - "xfail-strict=True wave gating (Phase 11/12 inheritance)"
    - "synthetic-only-in-CI fixture policy (Phase 11 D-02 inheritance)"
    - "lazy-import inside test bodies for collect-before-implement"
    - "[[tool.mypy.overrides]] ignore_missing_imports for stubbed modules"
key_files:
  created:
    - "tests/test_property_listing.py"
    - "tests/test_property_block_detector.py"
    - "tests/test_property_extractor.py"
    - "tests/test_property_fetch.py"
    - "tests/test_property_persistence.py"
    - "tests/fixtures/zillow/.gitkeep"
    - "tests/fixtures/zillow/extracted/.gitkeep"
    - "tests/fixtures/zillow/README.md"
  modified:
    - "pyproject.toml"
    - "uv.lock"
    - ".gitignore"
decisions:
  - "Probe A outcome (Q2): anthropic SDK has messages.parse — Wave 3 can use the structured-output API path (5% fewer LOC; no first-brace regex needed in the success path)"
  - "Probe B outcome (Q3): Python duckdb 1.5.2 installed cleanly; Wave 5 uses Python duckdb (not subprocess Node) for analyzed_listings writes"
  - "[[tool.mypy.overrides]] with ignore_missing_imports=true for the 4 stubbed lib.property_* modules (waves 1-5 will land them and the overrides come off as each wave ships)"
metrics:
  duration_minutes: 12
  completed_date: "2026-05-16"
  tasks_completed: 3
  files_changed: 8
  test_xfail_added: 47
  strict_markers: 32
---

# Phase 13 Plan 00: Wave-0 Scaffolding Summary

One-liner: Wave-0 dependency promotion + 5 xfail-marked test scaffolds + Zillow
fixture directory policy README + per-zpid HTML cache gitignore entry; both
Wave-0 probes returned (anthropic.messages.parse AVAILABLE; duckdb 1.5.2).

## What Shipped

### Task 1 — Runtime dependency promotion + Wave-0 probes (commit `9c54add`)

`pyproject.toml` diff applied verbatim per 13-RESEARCH §"Anthropic SDK Runtime Promotion":

- Removed `"anthropic==0.100.0"` from `[dependency-groups].dev`
- Added `"anthropic>=0.100.0,<1.0"` as the first line of `[project].dependencies`
- Added `"duckdb>=1.4,<2.0"` as the second line of `[project].dependencies`
- `[dependency-groups].dev` retained the tiktoken comment block and all other
  entries unchanged.

`uv sync` regenerated `uv.lock`:
```
Resolved 51 packages in 437ms
Downloaded duckdb
Installed 2 packages: duckdb==1.5.2 + mortgage-ops (rebuild)
```

**Probe A (Q2 — `messages.parse` availability):**
```
$ uv run python -c "import anthropic; c = anthropic.Anthropic(api_key='sk-fake'); print('messages.parse available:', 'parse' in dir(c.messages))"
messages.parse available: True
```
**Outcome:** TRUE. Wave 3 (`lib/property_extractor.py`) can use the structured-
output `client.messages.parse(output_format=PropertyListing)` API path — ~5%
fewer LOC and no first-brace regex extraction needed in the success path. The
regex-extract fallback (Pitfall 18) still ships as a defensive secondary path
for when Sonnet emits prose despite "JSON ONLY".

**Probe B (Q3 — Python `duckdb` import + version):**
```
$ uv run python -c "import duckdb; print('duckdb version:', duckdb.__version__)"
duckdb version: 1.5.2
```
**Outcome:** 1.5.2 (satisfies `>=1.4,<2.0` pin). Wave 5 (`lib/property_persistence.py`)
uses Python `duckdb` directly (not subprocess-Node-wrapper); same-process,
no `+200ms/write` overhead from the Node alternative.

`tests/test_smoke.py` still passes (1 passed in 0.01s) — no regression.

### Task 2 — 5 xfail-marked test scaffolds (commit `50dbae8`)

Wave-0 stubs land for every Phase-13 requirement ID. Every `@pytest.mark.xfail`
carries `strict=True` so a Wave-N "accidental pass" without implementation
fails the suite and forces the executor to remove the marker explicitly.

| File | Requirement IDs covered | xfail count | strict=True |
|------|-------------------------|-------------|-------------|
| `tests/test_property_listing.py` | PROP-01 (+ PROP-02 baseline) | 5 | 6 |
| `tests/test_property_block_detector.py` | INGEST-04 + D-13-BLOCK-01 (parametric) | 10 | 5 |
| `tests/test_property_extractor.py` | INGEST-02 (+ 1 skipif live) | 4 + 1 skip | 4 |
| `tests/test_property_fetch.py` | INGEST-01 + INGEST-03 | 10 | 10 |
| `tests/test_property_persistence.py` | PROP-02 + PERS-08 | 7 | 7 |
| **Total** | **all 7 phase requirement IDs** | **47 xfail + 1 skipped** | **32** |

Final pytest output on the 5 new files:
```
1 skipped, 47 xfailed in 0.07s
```
(The 1 skip is `test_extract_listing_live` — gated on `ANTHROPIC_API_KEY` per
the SUBA-06 inheritance pattern from `tests/test_subagents.py:432-471`.)

All 7 phase requirement IDs (INGEST-01..04, PROP-01..02, PERS-08) are
name-cited in test docstrings (grep-verifiable). Lazy `from lib.property_*
import ...` lives inside function bodies so collection succeeds before
waves 1-5 ship the lib modules.

### Task 3 — Zillow fixture directory + policy README + .gitignore (commit `d428655`)

Created:
- `tests/fixtures/zillow/.gitkeep`
- `tests/fixtures/zillow/extracted/.gitkeep`
- `tests/fixtures/zillow/README.md` — 6 required sections mirroring
  `tests/fixtures/subagent_transcripts/README.md` (Phase 11 D-02): Files table,
  Why synthetic (4 properties: determinism / zero cost / airgap / contract-is-shape),
  Capture-and-sanitize recipe (HTML-specific 4-step), When to regenerate
  (3 triggers), ANTHROPIC_API_KEY scope table (3 rows), What NOT to put here
  (no PII, no AI-attribution per CLAUDE.md global rule, no real Zillow non-public-
  API responses, no copyrighted listing photos).

Modified `.gitignore`: appended after the `data/cache/fred_*.json` block:
```
# Phase 13 — per-zpid HTML cache for --user-provided round-trips (Data Layer; generated)
data/cache/property-*.html
```

No HTML fixtures land in this wave — those are Wave 6 (Plan 13-06) and
Phase 17 expansion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Lint hygiene unblocking pre-commit] PT006 + TC003 + mypy import-not-found**

- **Found during:** Task 2 commit attempt (pre-commit hook failures).
- **Issue:**
  - ruff PT006: `@pytest.mark.parametrize("status,expected", ...)` style with
    a comma-string is disallowed by project lint config; must use a tuple.
  - ruff TC003: `from pathlib import Path` is used only as a type annotation
    in `tests/test_property_persistence.py`; must live in a `TYPE_CHECKING`
    block when `from __future__ import annotations` is in effect.
  - mypy: lazy `from lib.property_* import ...` raised `import-not-found`
    for all 4 not-yet-built modules (`lib.property_block_detector`,
    `lib.property_extractor`, `lib.property_listing`, `lib.property_persistence`).
- **Fix:**
  - Switched 2 `parametrize` first-args to tuples (`("status", "expected")`
    and `("url", "expected")`) in `tests/test_property_block_detector.py`.
  - Moved `from pathlib import Path` into a `TYPE_CHECKING` block in
    `tests/test_property_persistence.py`.
  - Added 4 `[[tool.mypy.overrides]]` entries in `pyproject.toml` for the
    4 stubbed modules with `ignore_missing_imports = true` and a comment
    documenting that each entry comes off as the corresponding wave ships.
  - ruff format auto-applied to all 5 new test files (mechanical hygiene).
- **Files modified:** `tests/test_property_block_detector.py`,
  `tests/test_property_persistence.py`, `pyproject.toml` (mypy overrides
  block append), plus ruff-format normalization of the other 3 test files.
- **Commit:** `50dbae8` (bundled into Task 2's commit).

**Rationale for bundling pyproject.toml mypy overrides with Task 2:** The
overrides ARE part of the test-scaffold's correctness — without them, mypy
fails on the lazy imports and Task 2 cannot be committed at all. They belong
with the test files they unblock, not as a separate "config" commit. Per
the plan's `files_modified` list, `pyproject.toml` is already in scope.

## Authentication Gates

None. Both Wave-0 probes ran with `api_key='sk-fake'` (Probe A — `messages.parse`
attribute is a SDK feature check, not an API call) and no key at all (Probe B —
`duckdb` is purely local). No `ANTHROPIC_API_KEY` is required at this wave.
Wave 3's live extractor test (`test_extract_listing_live`) is `@pytest.mark.skipif`
on the env var being absent, so it cleanly skips in airgapped CI per the
SUBA-06 inheritance pattern.

## Probe Outcomes (for Wave 3+ planning)

| Probe | Question | Result | Wave that consumes |
|-------|----------|--------|---------------------|
| A | `'parse' in dir(client.messages)`? | **True** | Wave 3 — use `messages.parse(output_format=PropertyListing)` for the happy path; keep `re.search(r"\{.*\}", raw, re.DOTALL)` as Pitfall-18 fallback |
| B | `duckdb.__version__` on `>=1.4,<2.0` pin? | **1.5.2** | Wave 5 — Python `duckdb` direct (not subprocess Node); `with_cache_lock(data/)` serializes against Phase 9 Node writer's `data/.lock` |

## Verification

- [x] All 5 test files exist with `from __future__ import annotations` first
- [x] Every `@pytest.mark.xfail` carries `strict=True` (32 markers across 5 files)
- [x] `uv run pytest tests/test_property_*.py` → 47 xfail + 1 skipped, 0 failed, 0 errors
- [x] All 7 phase requirement IDs (INGEST-01..04, PROP-01..02, PERS-08) grep-found in test docstrings
- [x] `pyproject.toml`: `anthropic>=0.100.0,<1.0` AND `duckdb>=1.4,<2.0` in `[project].dependencies`; no `anthropic==0.100.0` in `[dependency-groups].dev`
- [x] `uv.lock` regenerated (duckdb==1.5.2 entry added; 51 packages resolved)
- [x] Probe A result recorded: `messages.parse available: True`
- [x] Probe B result recorded: `duckdb version: 1.5.2`
- [x] `tests/fixtures/zillow/` exists with 2 `.gitkeep` files + README
- [x] `tests/fixtures/zillow/README.md` contains all 6 required sections (synthetic, D-13-BLOCK-01, ANTHROPIC_API_KEY, AI-attribution prohibition all grep-confirmed)
- [x] `.gitignore` contains `data/cache/property-*.html` (exactly one entry)
- [x] No HTML fixtures land yet (`ls tests/fixtures/zillow/*.html` returns no match) — those are Wave 6
- [x] No regression in Phase 1-12 suite (the one pre-existing failure in `test_citation_coverage.py::[fha_mip]` is caused by the pre-existing dirty `lib/rules/fha_mip.py` — confirmed by stashing the file and re-running the test, which then passes 11/11; that file was explicitly excluded from this plan's scope per the executor's important_constraints)

## Next: Wave 1

`/gsd-execute-phase 13` continues with Plan 13-01 (property-listing-model):
ship `lib/property_listing.py` (Pydantic `PropertyListing` + `ProvenancedMoney`
wrapper per 13-RESEARCH Example 3) and flip all 5 xfail markers in
`tests/test_property_listing.py`. The `[[tool.mypy.overrides]]` entry for
`lib.property_listing` should come off in that wave's commit.

## Self-Check: PASSED

Verified by direct filesystem + git inspection:

- FOUND: pyproject.toml (modified — anthropic + duckdb in [project].dependencies)
- FOUND: uv.lock (regenerated — duckdb 1.5.2 entry present)
- FOUND: tests/test_property_listing.py
- FOUND: tests/test_property_block_detector.py
- FOUND: tests/test_property_extractor.py
- FOUND: tests/test_property_fetch.py
- FOUND: tests/test_property_persistence.py
- FOUND: tests/fixtures/zillow/.gitkeep
- FOUND: tests/fixtures/zillow/extracted/.gitkeep
- FOUND: tests/fixtures/zillow/README.md
- FOUND: .gitignore (modified — data/cache/property-*.html entry added)
- FOUND: commit 9c54add (Task 1 — pyproject.toml + uv.lock)
- FOUND: commit 50dbae8 (Task 2 — 5 test files + pyproject.toml mypy overrides)
- FOUND: commit d428655 (Task 3 — zillow fixture scaffold + .gitignore)
