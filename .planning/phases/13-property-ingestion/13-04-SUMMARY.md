---
phase: 13-property-ingestion
plan: 04
subsystem: cli-orchestrator
tags: [phase-13, wave-4, cli, property-fetch, gap-fill, ingest-01, ingest-03, ingest-04, d-13-gapfill-01, d-13-block-01, d-13-musthave-01]
dependency_graph:
  requires:
    - "Phase 13 Wave 0 scaffolding (tests/test_property_fetch.py xfail scaffold + .gitignore data/cache/property-*.html)"
    - "Phase 13 Wave 1 lib.property_listing.PropertyListing + ProvenancedMoney (Plan 13-01)"
    - "Phase 13 Wave 2 lib.property_block_detector.detect_block + extract_zpid (Plan 13-02)"
    - "Phase 13 Wave 3 lib.property_extractor.extract_listing (Plan 13-03)"
    - "Phase 13 Wave 5 lib.property_persistence.write_listing (Plan 13-05; landed ahead of 13-04 in commit history) — wrapped in try/except so missing module would still degrade gracefully"
    - "Phase 12 scripts/fred_cli.py exemplar (argparse, sys.path parents[4], lazy imports, _emit, outer try CR-02)"
    - "Phase 12 lib.fred_cache.get_cached_or_fetch (MORTGAGE30US lookup for household_hash; best-effort)"
  provides:
    - ".claude/skills/mortgage-ops/scripts/property_fetch.py — CLI orchestrator (431 LOC; main() + 5 helpers + outer try block)"
    - "3-shape envelope contract on stdout (success / awaiting_user_input / blocked) per D-13-GAPFILL-01"
    - "_strip_money(raw) -> str (§Pitfall 16 normalization)"
    - "_coerce_money_to_string(d) -> dict (§Pitfall 15 strict-Decimal mitigation)"
    - "_wrap_scraped_provenanced_money(d) -> dict (flat Sonnet output -> PropertyListing ProvenancedMoney + sibling *_provenance shape)"
    - "_merge_user_provided(extracted, user) -> dict (overlay + provenance tagging per INGEST-03)"
    - "_mock_sonnet_extract(body, root) -> dict | None (MORTGAGE_OPS_MOCK_SONNET=1 test hook; sha-keyed fixture lookup)"
    - "Q1 default cache at data/cache/property-{zpid}.json (Round-2 --user-provided skips re-Sonnet entirely)"
    - "tests/test_property_fetch.py — 13 subprocess-driven envelope tests; all Wave 0 xfail markers removed"
  affects:
    - "Plan 13-06 (integration): end-to-end URL -> DuckDB round-trip; uses the MORTGAGE_OPS_MOCK_SONNET hook + real Zillow fixtures for shape-1 happy path"
    - "Phase 15 (property mode): SKILL.md routes natural-language property requests to this CLI; consumes the envelope.error field for prose-only recovery (Phase 12 D-12-LIVE02-01 inherited)"
    - ".gitignore — data/cache/property-*.json added (Q1 JSON companion of the existing .html line)"
tech_stack:
  added:
    - "scripts/property_fetch.py CLI (composes lib.property_block_detector + lib.property_extractor + lib.property_listing + lib.property_persistence + lib.fred_cache)"
  patterns:
    - "argparse + sys.path[parents[4]] + lazy lib.property_* imports (D-18 inherited; --help <60ms measured)"
    - "Block detection BEFORE Sonnet (D-13-BLOCK-01; saves $0.16/blocked page)"
    - "PropertyListing.model_validate_json route (not model_validate(dict)) — strict=True needs Pydantic's JSON parser for string-Decimal + string-datetime coercion"
    - "Q1 cache: extracted-dict JSON companion at data/cache/property-{zpid}.json (NOT raw HTML) so Round-2 reuse is byte-cheap"
    - "Outer try/except CR-02: SystemExit re-raised (argparse exit 2); everything else -> shape-3 unexpected_failure envelope + exit 0"
    - "ANTHROPIC_API_KEY scrubbed from subprocess env in every test (defense-in-depth; extractor already returns None on missing key)"
    - "Synthetic-inline HTML via tmp_path in Wave 4 tests; real pinned fixtures land in Wave 6"
key_files:
  created:
    - ".claude/skills/mortgage-ops/scripts/property_fetch.py"
    - ".planning/phases/13-property-ingestion/13-04-SUMMARY.md"
  modified:
    - "tests/test_property_fetch.py"
    - ".gitignore"
decisions:
  - "model_validate_json instead of model_validate(dict): PropertyListing.strict=True rejects string Decimals and ISO-string datetimes when ingested via the dict path, but accepts them via the JSON-parser path. Mirrors lib/property_persistence.read_latest_for_zpid pattern."
  - "Two-helper money handling: _coerce_money_to_string runs first (Sonnet stray floats → strings), then _wrap_scraped_provenanced_money lifts the 4 ProvenancedMoney fields into {value, provenance: \"scraped\"} dicts. Order matters because the wrapper expects strings."
  - "Q1 cache writes the POST-MERGE extracted dict, not the raw HTML. Round-2 cache hits bypass block-detect, Sonnet, AND wrapping (cached JSON is already in the wrapped shape). Saves $0.16 per --user-provided round-trip per the cost analysis in 13-CONTEXT.md."
  - "MORTGAGE_OPS_MOCK_SONNET=1 env hook is documented as TEST-ONLY in the module docstring. Production usage MUST leave it unset; the hook reads tests/fixtures/zillow/extracted/{sha16}.json (same key as the conftest mock_sonnet fixture)."
  - "Persistence call is wrapped in nested try/except: outer catches ImportError if 13-05 module is absent; inner catches OSError/duckdb errors. Either path writes a stderr warning but never blocks the envelope emission — the CLI's success contract is the envelope, not the side-effect."
  - "household_hash falls back to the literal string 'uncomputed' when MORTGAGE30US is uncached + offline OR when config/household.yml / config/profile.yml are absent (Data Contract: user-layer files are gitignored). This keeps the persistence call total even on cold first runs."
  - "Wave-4 tests do NOT cover the live shape-1 happy path (deferred to Plan 13-06 integration). Without ANTHROPIC_API_KEY, extract_listing returns None and the CLI falls through to shape-2 — Wave 4 tests assert the no-API-key shape-2 behavior; --user-provided round-trips synthesize shape-1 because the merge fills MUST-HAVEs."
metrics:
  duration_minutes: 8
  completed_date: "2026-05-17"
  loc_added: 431
  loc_test: 306
  tests_passed: 13
  tests_failed: 0
  property_suite_passed: 87
---

# Phase 13 Plan 04: CLI Orchestrator (property_fetch.py) Summary

`scripts/property_fetch.py` ships the Zillow URL → 3-shape envelope CLI orchestrator that composes Wave 1-3 + Wave 5 modules behind the D-13-GAPFILL-01 / D-13-BLOCK-01 / D-13-MUSTHAVE-01 locks. 431 LOC, 13 subprocess-driven tests, all 11 Wave-0 xfail markers removed, --help benchmarks at ~43ms (D-18 budget: 300ms).

## What Shipped

### `.claude/skills/mortgage-ops/scripts/property_fetch.py` (431 LOC)

**Structure** (top-down):

1. **Module docstring** (40 lines) — pins all 3 envelope shapes by name, Q1 cache semantics, MORTGAGE_OPS_MOCK_SONNET test-hook contract, exit-code contract (always 0 except argparse exit 2).
2. **Module constants** — `MUST_HAVE`, `MONEY_FIELDS`, `PROVENANCED_MONEY_FIELDS`, `NON_MONEY_NUMBER_FIELDS`, `NON_MONEY_DECIMAL_FIELDS`, `PLAIN_OVERLAY_FIELDS` (all `frozenset[str]` or `tuple[str, ...]`).
3. **5 helper functions** — `_now_iso_z`, `_strip_money` (§Pitfall 16), `_coerce_money_to_string` (§Pitfall 15), `_wrap_scraped_provenanced_money` (plan-check BLOCKER 1 fix), `_merge_user_provided` (INGEST-03), `_mock_sonnet_extract` (plan-check BLOCKER 2 fix — `MORTGAGE_OPS_MOCK_SONNET=1` hook).
4. **`main()`** — argparse → sys.path[parents[4]] injection → lazy `from lib.property_* import` → ZPID extract → cache lookup (Q1) → body acquisition (cache / `--html-from` / stdin) → block-detect (D-13-BLOCK-01) → Sonnet extract (or mock or cached) → coerce/wrap/merge → audit-field add → `PropertyListing.model_validate_json` → Q1 cache write → best-effort persistence → shape-1 emit.
5. **`if __name__ == "__main__"` outer try/except** — `SystemExit` re-raised (argparse exit 2); any other Exception → shape-3 `unexpected_failure: {exc!r}` envelope, exit 0 (Phase 12 CR-02).

### `tests/test_property_fetch.py` (306 LOC, 13 tests)

All 11 Wave-0 xfail markers removed. New coverage matrix:

| Test                                              | Asserts                                                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `test_property_fetch_help_fast_lazy_imports`      | `--help` returns 0 in <300ms; stdout mentions shape/envelope/awaiting (D-18)                     |
| `test_argparse_error_exit_2`                      | Missing positional `url` → exit 2 (the one documented exception to always-exit-0)                |
| `test_blocked_captcha_envelope_exit_0`            | "press & hold" body → shape-3 `error="captcha_detected"`                                         |
| `test_body_too_short_envelope`                    | 100-byte body → shape-3 `error="body_too_short"`                                                 |
| `test_missing_next_data_envelope`                 | 6KB body without `<script id="__NEXT_DATA__">` → shape-3 `error="missing_next_data"`             |
| `test_zpid_extraction_failed_envelope`            | `https://redfin.com/...` URL → shape-3 `error="zpid_extraction_failed"` (after block-detect)     |
| `test_no_api_key_falls_through_to_shape_2`        | No ANTHROPIC_API_KEY → extract returns None → shape-2 with all 3 MUST_HAVE listed missing        |
| `test_user_provided_strips_dollar_comma`          | `--user-provided '{"price":"$625,000",...}'` → `listing.price == "625000.00"`                    |
| `test_user_provided_tags_provenance_on_tax_annual`| `--user-provided '{"tax_annual":"8200"}'` → `{"value": "8200.00", "provenance": "user_provided"}`|
| `test_user_provided_tags_sibling_provenance_on_beds` | `--user-provided '{"beds":3}'` → `beds=3 + beds_provenance="user_provided"`                  |
| `test_envelope_always_has_fetched_at_z_suffix`    | `fetched_at` ends in `Z`, not `+00:00` (Pitfall 21 inherited)                                    |
| `test_outer_try_catches_unexpected_failure`       | Malformed `--user-provided` JSON → shape-3 `error="unexpected_failure: ..."`, exit 0             |
| `test_cli_writes_html_cache_on_round_1`           | Successful shape-1 round writes `data/cache/property-12345.json` (Q1 default)                    |

### `.gitignore` — one-line addition

`data/cache/property-*.json` added immediately under the existing
`data/cache/property-*.html` entry. Both the raw-HTML and extracted-JSON
cache files are Data Layer / generated / never committed.

## Requirements Closed

- **INGEST-01** (CLI-level): WebFetch HTML → __NEXT_DATA__ extraction → structured error envelope; no Python tracebacks on failure modes.
- **INGEST-03** (CLI-level): MUST-HAVE missing → shape-2; `--user-provided` merge tags `provenance="user_provided"` for ProvenancedMoney fields + sibling `*_provenance` field for non-money fields.
- **INGEST-04** (CLI-level): non-Zillow URL → shape-3 `zpid_extraction_failed`; both `/homedetails/{slug}/{zpid}_zpid/` and `/b/{zpid}_zpid/` patterns supported (delegates to `lib.property_block_detector.extract_zpid`).

## Locks Honored

- **D-13-GAPFILL-01**: 3 envelope shapes are exhaustive; CLI never opens an interactive prompt (no `input()` / `sys.stdin.readline` for prompts; only the WebFetch HTML body comes through stdin).
- **D-13-BLOCK-01**: block detection runs BEFORE Sonnet; verified by source-order grep (`detect_block` line < `extract_listing` line) and by the 3 shape-3 block tests.
- **D-13-MUSTHAVE-01**: `MUST_HAVE = ("price", "zip", "property_type")` drives the missing-fields computation; tested across the no-API-key shape-2 path.
- **D-13-MODEL-01**: no auto-retries; CLI invokes Sonnet exactly once; no `tenacity`/`@retry` imports.
- **D-12-LIVE02-01 / Phase 12 CR-02**: always exit 0 except argparse exit 2; outer try/except converts any uncaught exception to shape-3 envelope.
- **D-18**: lazy imports preserve `--help <300ms`; measured at ~43ms.
- **Q1 default**: `data/cache/property-{zpid}.json` companion of the post-merge extracted dict; Round-2 `--user-provided` cache hits skip block-detect + Sonnet + wrapping entirely.

## Deviations from Plan

### Rule 1 (Bug Fix) — `PropertyListing.model_validate_json` instead of `model_validate(dict)`

**Found during**: Task 2 test execution. The §Example 5 spine used
`PropertyListing.model_validate(extracted)`, but `PropertyListing` is
declared with `strict=True`, so the dict path rejected the string-encoded
Decimal in `extracted["price"]` and the ISO-string `extracted["fetched_at"]`.
Tests `test_user_provided_strips_dollar_comma`,
`test_user_provided_tags_provenance_on_tax_annual`, and
`test_user_provided_tags_sibling_provenance_on_beds` all surfaced as
shape-2 instead of shape-1.

**Fix**: route validation through `PropertyListing.model_validate_json(json.dumps(extracted))`.
This delegates string→Decimal / string→datetime coercion to Pydantic's
JSON parser path, which strict=True accepts. Same pattern lib/property_persistence.py
uses for round-tripping a stored row.

**Secondary fix**: replaced `missing or list(MUST_HAVE)` with an explicit
`missing if missing else list(MUST_HAVE)`. The original short-circuit
treated an empty list (no missing fields) as falsy and replaced it with
the full MUST_HAVE list — the wrong "everything missing" envelope when
the partial dict had every must-have key present but some downstream
validation failed.

**Commit**: `4dbf8e3 fix(13-04): route property_fetch Pydantic validation through model_validate_json`.

### Rule 3 (Blocking Issue) — `dict | None` mypy annotation

**Found during**: Task 2 commit (pre-commit mypy hook).

**Fix**: tightened `dict | None` → `dict[str, object] | None` (the helper
factory) and `dict | None` → `dict[str, str] | None` (the `env` kwarg of
`_run_cli`). Both are str-keyed dicts; the latter is `os.environ`-shaped
which is `str: str`.

### Rule 3 (Blocking Issue) — pre-commit ruff/format auto-fixes

Pre-commit's `ruff` + `ruff-format` hooks auto-fixed 5 style nits (mostly
trailing-whitespace + line-length) on the first commit attempt of
`property_fetch.py` and 1 style nit on `test_property_fetch.py`. Each
fix was automatically restaged + recommitted.

## Self-Check: PASSED

- File present: `.claude/skills/mortgage-ops/scripts/property_fetch.py` (431 LOC, mode 755)
- Commit `8fe61a6 feat(13-04): add scripts/property_fetch.py CLI orchestrator` in `git log`
- Commit `4dbf8e3 fix(13-04): route property_fetch Pydantic validation through model_validate_json` in `git log`
- Commit `6dc30aa test(13-04): flip xfails + add 13 subprocess envelope tests for property_fetch` in `git log`
- `tests/test_property_fetch.py` contains zero `@pytest.mark.xfail` markers
- `uv run pytest tests/test_property_fetch.py -v` → 13/13 passed
- `uv run pytest tests/ -k 'property'` → 87 passed, 1 skipped (the Sonnet live-key skip is intentional per Phase 11 D-02), 0 failed
- `uv run python .claude/skills/mortgage-ops/scripts/property_fetch.py --help` exits 0 in ~43ms; stdout mentions all 3 envelope shapes
- `.gitignore` contains `data/cache/property-*.json` (new line) and `data/cache/property-*.html` (Wave 0; unchanged)
- No `Co-Authored-By` / AI attribution in any commit message

## Next Plan

Plan 13-06 (integration + fixtures) — depends on this plan + 13-05. Will:

1. Land the 5 pinned Zillow HTML fixtures (`tests/fixtures/zillow/*.html`).
2. Land matching sha-keyed extracted JSON (`tests/fixtures/zillow/extracted/{sha16}.json`).
3. Add an end-to-end test that invokes `property_fetch.py` with `MORTGAGE_OPS_MOCK_SONNET=1` against the real fixtures, asserts shape-1 envelope, then asserts `lib.property_persistence.read_latest_for_zpid` round-trips the same `PropertyListing` instance from DuckDB.
