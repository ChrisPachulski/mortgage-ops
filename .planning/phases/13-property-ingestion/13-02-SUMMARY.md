---
phase: 13-property-ingestion
plan: 02
subsystem: block-detector
tags: [phase-13, wave-2, block-detector, zpid-regex, ingest-04, d-13-block-01]
dependency_graph:
  requires:
    - "Phase 13 Wave 0 scaffolding (tests/test_property_block_detector.py xfail stubs + pyproject mypy override)"
    - "stdlib re + typing (Final, Literal) — zero third-party"
  provides:
    - "lib.property_block_detector.detect_block (D-13-BLOCK-01 4-signal predicate)"
    - "lib.property_block_detector.extract_zpid (INGEST-04 both URL patterns)"
    - "lib.property_block_detector.BlockError (7-member Literal enum)"
    - "lib.property_block_detector.CAPTCHA_PHRASES (6 case-insensitive substrings)"
    - "lib.property_block_detector.MIN_BODY_BYTES (5000, strict-<)"
    - "lib.property_block_detector.NEXT_DATA_RE (attribute-order agnostic, IGNORECASE)"
    - "lib.property_block_detector.ZPID_RE (both URL patterns, IGNORECASE)"
  affects:
    - "Plan 13-03 (extractor): parallel-eligible; Wave 3 has no shared files"
    - "Plan 13-04 (CLI): detect_block fires BEFORE Sonnet — saves ~$0.16/blocked-page in wasted API spend"
    - "Plan 13-04 (CLI): extract_zpid fires after happy-path Sonnet call to populate audit field"
tech_stack:
  added:
    - "lib.property_block_detector module (pure stdlib regex predicate)"
  patterns:
    - "Final[tuple[str, ...]] module constants (mirrors lib/fred_cache.py:61-72 REQUIRED_ENTRY_FIELDS)"
    - "Cheap-first detection order: status -> length -> captcha -> __NEXT_DATA__ (mirrors lib/fred_cache.py:is_fresh strict-< boundary discipline)"
    - "re.IGNORECASE on both regex patterns for case-insensitive scrape resilience"
    - "Attribute-order-agnostic <script ...id=...> match (Pitfall 19)"
    - "Leaf module — zero imports from lib.* — anyone can import without circular-import risk"
key_files:
  created:
    - "lib/property_block_detector.py"
  modified:
    - "tests/test_property_block_detector.py"
    - "pyproject.toml"
decisions:
  - "Cheap-first detection order LOCKED: status_code -> body length -> captcha -> NEXT_DATA. A 1KB captcha page reports body_too_short (not captcha_detected); a 403 with 1KB body reports http_403 (not body_too_short). Either error is actionable for the CLI; ordering by computation cost is the load-bearing constraint."
  - "MIN_BODY_BYTES = 5000 with STRICT-< boundary (a 5000-byte body is NOT body_too_short). Mirrors lib/fred_cache.is_fresh TTL strict-< pattern."
  - "NEXT_DATA_RE uses [^>]*id=\"__NEXT_DATA__\"[^>]* (attribute-order agnostic) per Pitfall 19. Matches both <script id=\"__NEXT_DATA__\" type=\"application/json\"> and the reverse attribute order."
  - "ZPID_RE supports BOTH /homedetails/{slug}/{zpid}_zpid/ AND /b/{zpid}_zpid/ via a single alternation; trailing-slash optional; query/fragment irrelevant since regex anchors on _zpid sentinel."
  - "Leaf module discipline: no imports from lib.* — Plan 13-04 (CLI) can import this module without circular-import risk. lib.property_extractor (Plan 13-03) is the other leaf consumed by 13-04."
metrics:
  duration_minutes: 3
  completed_date: "2026-05-17"
  tasks_completed: 2
  files_changed: 3
  loc_added: 89  # lib/property_block_detector.py
  tests_flipped: 22  # xfail markers removed (5 markers gating 22 parametric cases)
  tests_added: 9    # new test functions beyond the original 5 stubs
---

# Phase 13 Plan 02: Block Detector Summary

One-liner: D-13-BLOCK-01 4-signal predicate + INGEST-04 ZPID extractor — pure
stdlib `re` leaf module (89 LOC, zero third-party imports) with cheap-first
detection order (status -> length -> captcha -> NEXT_DATA), attribute-order
agnostic `<script id="__NEXT_DATA__">` match (Pitfall 19), case-insensitive
captcha + ZPID regex, and 31 parametric green tests covering both URL patterns
+ 4-signal precedence + boundary discipline. Saves ~$0.16/blocked-page from
the Plan 13-04 Sonnet pipeline.

## What Shipped

### Task 1 — `lib/property_block_detector.py` (commit `a68c423`)

89 LOC. Two functions, one Literal enum, four module constants. Module docstring
documents all 4 D-13-BLOCK-01 signals + INGEST-04 + the cheap-first order
invariant that Plan 13-04 depends on for cost minimization.

**Public API:**

| Symbol | Type | Purpose |
|--------|------|---------|
| `detect_block(status, body)` | `(int, str) -> BlockError \| None` | D-13-BLOCK-01 4-signal predicate (returns first match in cheap-first order) |
| `extract_zpid(url)` | `(str) -> str \| None` | INGEST-04 ZPID parser (None on non-Zillow / malformed / empty) |
| `BlockError` | `Literal[7 members]` | http_403/429/503/other, missing_next_data, captcha_detected, body_too_short |
| `CAPTCHA_PHRASES` | `Final[tuple[str, ...]]` | 6 lowercased substrings; body is `.lower()`-folded once before scanning |
| `MIN_BODY_BYTES` | `Final[int] = 5000` | Strict-< boundary; 5000-byte body is NOT body_too_short |
| `NEXT_DATA_RE` | `Final[re.Pattern]` | `<script[^>]*id="__NEXT_DATA__"[^>]*>` with `re.IGNORECASE` |
| `ZPID_RE` | `Final[re.Pattern]` | `/(?:homedetails/[^/]+/\|b/)(\d+)_zpid/?` with `re.IGNORECASE` |

**Detection order (cheap-first, LOCKED):**

```
status != 200      -> http_403 / http_429 / http_503 / http_other
len(body) < 5000   -> body_too_short
any captcha phrase -> captcha_detected
no NEXT_DATA tag   -> missing_next_data
else               -> None  (happy path; pass to Sonnet)
```

**Hard constraints honored:**

- Pure stdlib only (`re`, `typing`). Zero third-party imports.
- No imports from `lib.*` (leaf module; Plan 13-04 imports it without circular-import risk).
- `MIN_BODY_BYTES` uses STRICT-`<` (mirrors lib/fred_cache.is_fresh TTL pattern).
- Module constants pinned with `Final[...]` (mirrors lib/fred_cache.py:61-72).
- No `Co-Authored-By` / AI-attribution strings (CLAUDE.md global rule).

**pyproject.toml diff:** removed the `[[tool.mypy.overrides]] module = "lib.property_block_detector"` ignore_missing_imports entry now that the module exists (per 13-00-SUMMARY hand-off note; mirrors Plan 13-01's removal of its own override).

### Task 2 — `tests/test_property_block_detector.py` (commit `410144a`)

114 LOC. 11 test functions / 31 parametric cases, all green. All 5 Wave-0
`@pytest.mark.xfail(..., strict=True)` markers removed; bodies filled with
real assertions against the just-built module. Module-level `_HAPPY_BODY`
canned fixture keeps each test focused on the property under assertion.

**Test list:**

| # | Test                                                       | Asserts                                                   |
|---|------------------------------------------------------------|-----------------------------------------------------------|
| 1 | `test_detect_block_status_codes` (6 cases)                 | 403/429/503 -> specific; 500/502 -> http_other; 200 -> None |
| 2 | `test_detect_block_body_too_short`                         | body length MIN-1 -> "body_too_short"                     |
| 3 | `test_detect_block_body_at_exactly_min_bytes_is_not_too_short` | STRICT-< boundary: 5000 bytes falls through to NEXT_DATA |
| 4 | `test_detect_block_captcha_phrases` (6 cases)              | each of 6 phrases fires "captcha_detected"                |
| 5 | `test_detect_block_captcha_case_insensitive`               | "PRESS & HOLD" uppercase still fires                      |
| 6 | `test_detect_block_missing_next_data`                      | big body without `<script id="__NEXT_DATA__">` -> "missing_next_data" |
| 7 | `test_detect_block_happy_path_returns_none`                | big body + captcha-free + NEXT_DATA tag -> None           |
| 8 | `test_detect_block_next_data_attribute_order_variant`      | Pitfall 19: `type=` before `id=` still matches            |
| 9 | `test_detect_block_status_wins_over_short_body`            | order: 403 with 1KB body -> http_403 (not body_too_short) |
| 10 | `test_detect_block_short_body_wins_over_captcha`          | order: 1KB body with "recaptcha" -> body_too_short        |
| 11 | `test_extract_zpid` (11 cases)                            | INGEST-04 URL matrix (see below)                          |

**ZPID URL coverage (11 parametric cases):**

| URL                                                                        | Expected     |
|----------------------------------------------------------------------------|--------------|
| `https://www.zillow.com/homedetails/123-Main-SF-CA-94110/12345678_zpid/`   | `"12345678"` |
| `https://zillow.com/b/87654321_zpid/`                                      | `"87654321"` |
| `https://zillow.com/homedetails/foo/12345_zpid` (no trailing slash)        | `"12345"`    |
| `https://zillow.com/homedetails/foo/12345_zpid/?source=email`              | `"12345"`    |
| `https://zillow.com/homedetails/foo/12345_zpid/#photos`                    | `"12345"`    |
| `http://www.zillow.com/homedetails/foo/12345_zpid/` (http)                 | `"12345"`    |
| `https://www.zillow.com/HOMEDETAILS/x/55_ZPID/` (uppercase)                | `"55"`       |
| `https://redfin.com/property/12345` (non-Zillow)                           | `None`       |
| `https://zillow.com/homedetails/foo/` (no `_zpid`)                         | `None`       |
| `https://zillow.com/no-zpid-here/` (no `_zpid`)                            | `None`       |
| `""` (empty string)                                                        | `None`       |

**Final pytest:** `31 passed in 0.02s` on `tests/test_property_block_detector.py`. Zero xfail, zero XPASS, zero failed, zero error.

## Deviations from Plan

None. Plan executed exactly as written. No Rule 1-4 deviations were triggered.

- The `lib/property_block_detector.py` source is byte-equivalent to the verbatim 13-RESEARCH §Example 2 + the plan's `<action>` block (modulo cosmetic single-line-vs-multi-line `if` bodies for ruff format compliance).
- The test file mirrors the plan's `<action>` block pattern exactly; the only mechanical adjustment was a ruff I001 import-sort auto-fix that moved `import pytest` adjacent to the `from lib.property_block_detector import ...` block (no semantic change — Wave 0 scaffold had `from __future__` + blank + `import pytest` + blank + lazy-import inside the function body; Wave 2 promoted the lib import to module level since the module now exists).

## Authentication Gates

None. The module is a pure regex predicate; no API keys or external services touched.

## Verification

- [x] `lib/property_block_detector.py` exists; `wc -l` = 89 (>= 45 required)
- [x] Exactly one `def detect_block(` definition
- [x] Exactly one `def extract_zpid(` definition
- [x] `MIN_BODY_BYTES: Final[int] = 5000` present verbatim
- [x] `CAPTCHA_PHRASES` contains exactly 6 phrases (verified via grep)
- [x] `NEXT_DATA_RE` uses `re.IGNORECASE` AND `[^>]*id="__NEXT_DATA__"[^>]*` (attribute-order agnostic)
- [x] `ZPID_RE` uses `re.IGNORECASE` AND matches BOTH `/homedetails/[^/]+/` and `/b/` prefixes
- [x] No `import requests` / `import httpx` / `from bs4` / `import lxml`
- [x] No imports from `lib.*` (leaf module)
- [x] No `Co-Authored-By` / AI-attribution strings (CLAUDE.md global rule)
- [x] `uv run python -c "from lib.property_block_detector import detect_block, extract_zpid, BlockError, CAPTCHA_PHRASES, MIN_BODY_BYTES; print('OK')"` prints `OK`
- [x] `grep -c '@pytest.mark.xfail' tests/test_property_block_detector.py` returns 0
- [x] `grep -c '^def test_' tests/test_property_block_detector.py` returns 11 (>= 11)
- [x] `uv run pytest tests/test_property_block_detector.py -v` -> 31 passed, no xfail, no XPASS, no failed, no error
- [x] No regression in Phase 1-12 tests (the 2 pre-existing failures in `test_citation_coverage.py::[fha_mip]` + `test_citation_coverage_mutations.py::test_meta_tests_pass_unmutated_baseline` are caused by the pre-existing dirty `lib/rules/fha_mip.py` — confirmed in Plan 13-01 SUMMARY; that file is explicitly excluded from this plan's scope per the executor's important_constraints)
- [x] Pre-commit hooks pass (ruff, ruff-format, mypy --strict, DATA_CONTRACT.md guard) on both task commits
- [x] Pre-existing dirty file (`lib/rules/fha_mip.py`) NOT staged; pre-existing untracked files (`.planning/*.md` notes, `data/.lock 2..5`) NOT staged — per executor constraints

## Detection Order — Test Receipts

The order-locking tests (Task 2 #9 + #10) explicitly verify the cheap-first
invariant that Plan 13-04 depends on for cost minimization:

| Test | Input                              | Expected            | Why it matters                                   |
|------|------------------------------------|---------------------|--------------------------------------------------|
| #9   | `(403, "x"*1000)`                  | `"http_403"`        | Status check fires BEFORE body-length check     |
| #10  | `(200, "recaptcha " + "x"*100)`    | `"body_too_short"`  | Length check fires BEFORE captcha scan          |

If the order were reordered (e.g., captcha before length), test #10 would
report `"captcha_detected"` instead. Either error is actionable for the CLI,
but cheap-first wins on cost: `len(body)` is microseconds vs `body.lower() +
6 substring scans` on a 200KB string.

## INGEST-04 Closure

INGEST-04 ("ZPID extraction from URL — supports both
`zillow.com/homedetails/{slug}/{zpid}_zpid/` and `zillow.com/b/{zpid}_zpid/`
URL patterns; ZPID is the durable primary key for `analyzed_listings`") is
**closed** by:

1. The `ZPID_RE` regex covers both URL patterns via a single alternation.
2. The 11-row parametric test in `tests/test_property_block_detector.py::test_extract_zpid` verifies both patterns + 3 tail variants (trailing slash optional, query string ignored, fragment ignored) + http scheme + uppercase + 3 negative cases (non-Zillow domain, missing `_zpid`, empty string).
3. Plan 13-04 will import `extract_zpid` directly and use the returned string as the `zpid` audit field on the `PropertyListing` (which already validates with `Field(pattern=r"^\d+$")` per Plan 13-01).

## D-13-BLOCK-01 Closure

D-13-BLOCK-01 ("Four signals; ANY firing triggers shape-3 `blocked` envelope
with a specific error code") is **fully implemented** at the predicate layer:

| Signal | BlockError member(s)            | Test coverage                                            |
|--------|---------------------------------|----------------------------------------------------------|
| 1      | http_403 / http_429 / http_503 / http_other | `test_detect_block_status_codes` (6 cases)   |
| 2      | missing_next_data               | `test_detect_block_missing_next_data` + attribute-order  |
| 3      | captcha_detected                | `test_detect_block_captcha_phrases` (6) + case-insensitive |
| 4      | body_too_short                  | `test_detect_block_body_too_short` + boundary            |

Plan 13-04 (CLI) imports `detect_block` and routes the returned member to the
shape-3 `blocked` envelope's `error` field. The full D-13-BLOCK-01 contract
(shape-3 envelope construction) closes in Plan 13-04.

## Self-Check: PASSED

Verified by direct filesystem + git inspection:

- FOUND: lib/property_block_detector.py
- FOUND: tests/test_property_block_detector.py (modified — xfail markers removed; 11 live tests / 31 parametric cases)
- FOUND: pyproject.toml (modified — lib.property_block_detector mypy override removed)
- FOUND: commit a68c423 (Task 1 — lib/property_block_detector.py + pyproject.toml)
- FOUND: commit 410144a (Task 2 — tests/test_property_block_detector.py flipped)
- VERIFIED: `uv run pytest tests/test_property_block_detector.py` -> 31 passed
- VERIFIED: `uv run python -c "from lib.property_block_detector import ...; print('OK')"` -> OK

## Next: Wave 3

`/gsd-execute-phase 13` continues with Plan 13-03 (extractor) — depends on
Plan 13-01 (PropertyListing model, already shipped). Wave 3 ships
`lib/property_extractor.py` with the Sonnet `messages.parse(output_format=PropertyListing)`
path (per Wave-0 Probe A: `messages.parse` AVAILABLE on anthropic 0.100.0) +
flips the 4 xfails + 1 skipif in `tests/test_property_extractor.py`. Plan 13-03
runs parallel-eligible with this Plan 13-02 (no shared files; Plan 13-02 is
already complete).

Plan 13-04 (CLI) depends on BOTH Plan 13-02 (this plan — `detect_block` +
`extract_zpid`) AND Plan 13-03 (extractor — `extract_listing`); cannot start
until 13-03 ships.

Plan 13-05 (persistence) depends only on Plan 13-01 (PropertyListing) and can
run in parallel with 13-03; both are unblocked.

The remaining 2 `[[tool.mypy.overrides]]` entries (`lib.property_extractor`,
`lib.property_persistence`) will come off as Plans 13-03 and 13-05 ship.
