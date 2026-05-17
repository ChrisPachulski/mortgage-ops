---
phase: 13-property-ingestion
plan: 06
subsystem: property-ingestion
tags: [phase-13, fixtures, integration, end-to-end, scope-test-01]
requires:
  - 13-00-SUMMARY.md (Wave 0 scaffolding + tests/fixtures/zillow/ + mock_sonnet conftest scaffold)
  - 13-01-SUMMARY.md (PropertyListing + ProvenancedMoney models)
  - 13-02-SUMMARY.md (lib/property_block_detector — detect_block + extract_zpid)
  - 13-03-SUMMARY.md (lib/property_extractor — Sonnet extract_listing)
  - 13-04-SUMMARY.md (scripts/property_fetch.py CLI orchestrator + mock-Sonnet env hook)
  - 13-05-SUMMARY.md (lib/property_persistence — write_listing + read_latest_for_zpid)
provides:
  - 3 sanitized synthetic Zillow HTML fixtures under tests/fixtures/zillow/
  - 2 sha-keyed extracted/{sha16}.json pre-recorded mock-Sonnet outputs
  - tests/fixtures/zillow/README.md updated with the actual fixture inventory + sha-key recipe
  - tests/test_property_ingestion_integration.py (11 end-to-end tests)
affects:
  - .planning/ROADMAP.md (Phase 13 checkbox flipped to [x] + Status COMPLETED line)
  - .planning/REQUIREMENTS.md (INGEST-01..04 + PROP-01..02 status table row updated to Closed)
  - .planning/STATE.md (Current Position + Phase 13 closure entry)
tech-stack:
  added: []
  patterns:
    - "sha-keyed pre-recorded mock fixture pattern (synthetic-only-in-CI per Phase 11 D-02)"
    - "subprocess-driven end-to-end integration test (mirrors tests/test_fred_cli.py + tests/test_property_fetch.py)"
    - "MORTGAGE_OPS_MOCK_SONNET=1 env-var subprocess hook (shipped in Plan 13-04; consumed here)"
key-files:
  created:
    - tests/fixtures/zillow/sfh_conforming_happy_path.html (6500 bytes)
    - tests/fixtures/zillow/condo_partial_tax_missing.html (6622 bytes)
    - tests/fixtures/zillow/blocked_perimeterx.html (5428 bytes)
    - tests/fixtures/zillow/extracted/c9d5a0df4baa57a5.json (SFH mock-Sonnet output)
    - tests/fixtures/zillow/extracted/5810e207ecf14e21.json (condo mock-Sonnet output)
    - tests/test_property_ingestion_integration.py (11 tests, 298 lines)
    - .planning/phases/13-property-ingestion/13-06-SUMMARY.md (this file)
  modified:
    - tests/fixtures/zillow/README.md (Wave-0 placeholder table -> actual file table + worked sha-key example + pairings table)
    - .planning/ROADMAP.md (Phase 13 [x] + Status: COMPLETED line)
    - .planning/REQUIREMENTS.md (status table row updated for INGEST-01..04 + PROP-01..02)
    - .planning/STATE.md (Current Position + Phase 13 closure entry)
decisions:
  - "Fixture body sizes (SFH 6500, condo 6622, blocked 5428 bytes) all exceed MIN_BODY_BYTES=5000 so block detection fires on the captcha PHRASE for blocked_perimeterx (the realistic detection path) rather than body_too_short. Real captcha pages from anti-bot CDNs are typically 8-15KB."
  - "ZIPs kept real (94110 SF, 98052 Redmond, no ZIP on blocked) per README sanitization recipe; Phase 14 per-zip tax-rate lookups need real ZIPs to exercise their normal code path."
  - "Test DB roundtrip routes PropertyListing through model_validate_json (not model_validate) because strict=True rejects string-typed Decimal/date/datetime when validating from a dict; the JSON parser handles the coercion at the boundary. Mirrors lib.property_persistence.read_latest_for_zpid pattern."
  - "Q1 cache isolation: the --user-provided overlay test runs with cwd=tmp_path so the CLI's data/cache/property-{zpid}.json cache writes to the tmp directory instead of polluting the repo's data/cache/."
metrics:
  duration: 1 session
  completed: 2026-05-16
  tasks: 5
  files_created: 7
  files_modified: 4
  tests_added: 11
---

# Phase 13 Plan 06: Fixtures + End-to-End Integration Test — Summary

End-to-end pipeline test landed: a Zillow URL goes in, a validated PropertyListing
comes out, DuckDB round-trips. 3 synthetic HTML fixtures + 2 sha-keyed mock-Sonnet
outputs + 11 integration tests prove the full URL → CLI → block-detect → Sonnet
(mocked) → ProvenancedMoney wrap → Pydantic → DuckDB write → read-back contract
without any live Sonnet calls or ANTHROPIC_API_KEY. Phase 13 closed: 7
requirements green, 5 D-13 locks proven via tests, 4 open questions resolved.

## What shipped

### HTML fixtures (Task 1)

| Fixture | Bytes | __NEXT_DATA__ | Captcha phrase | Purpose |
|---|---|---|---|---|
| `sfh_conforming_happy_path.html` | 6500 | yes | no | SC-1: shape-1 SFH happy path; all 13 fields populated |
| `condo_partial_tax_missing.html` | 6622 | yes | no | D-13-MUSTHAVE-01: condo HOA scraped, tax_annual=null, still shape-1 |
| `blocked_perimeterx.html` | 5428 | no | "Press & Hold" | SC-2: shape-3 captcha_detected, body length above MIN_BODY_BYTES so captcha (not length) fires |

All fixtures are 100% synthetic (no PII, no real addresses, no agent contact info,
no phone-number or email patterns, no AI-attribution strings). ZIPs are real
(94110, 98052) per README sanitization recipe so Phase 14 per-zip lookups behave
normally.

### Sha-keyed mock-Sonnet outputs (Task 2)

| HTML | SHA-16 | Extracted JSON |
|---|---|---|
| `sfh_conforming_happy_path.html` | `c9d5a0df4baa57a5` | `tests/fixtures/zillow/extracted/c9d5a0df4baa57a5.json` |
| `condo_partial_tax_missing.html` | `5810e207ecf14e21` | `tests/fixtures/zillow/extracted/5810e207ecf14e21.json` |

Money fields stored as JSON strings per D-19. Both dicts validate against
`PropertyListing` after the CLI's `_wrap_scraped_provenanced_money` + audit-field
augmentation (verified manually + in `test_extracted_json_has_expected_shape`).

### README update (Task 3)

`tests/fixtures/zillow/README.md` now contains:
- Files table with actual fixture inventory + byte sizes
- "Worked sha-key example" subsection with runnable `python -c` one-liner
- Committed pairings table mapping each HTML fixture to its `extracted/{sha16}.json`
- All 6 original policy sections preserved (synthetic-only, sanitization recipe,
  when to regenerate, ANTHROPIC_API_KEY scope, what NOT to put here)

### Integration test (Task 4)

`tests/test_property_ingestion_integration.py` ships 11 tests:

| # | Test | Covers |
|---|---|---|
| 1 | `test_cli_exposes_mock_sonnet_hook_and_provenance_wrapping` | Meta: surface the Plan 13-04 dependency |
| 2 | `test_end_to_end_sfh_happy_path_shape_1` | SC-1: shape-1 envelope, ProvenancedMoney + sibling provenance |
| 3 | `test_end_to_end_condo_partial_tax_missing_shape_1` | D-13-MUSTHAVE-01: tax_annual=null is non-blocking |
| 4 | `test_end_to_end_blocked_captcha_shape_3` | SC-2: captcha block, Sonnet skipped (cost saved) |
| 5 | `test_end_to_end_zpid_url_pattern_homedetails` | INGEST-04: /homedetails/ pattern → correct zpid |
| 6 | `test_end_to_end_zpid_url_pattern_b_shortlink` | INGEST-04: /b/ shortlink, URL zpid wins over body |
| 7 | `test_end_to_end_user_provided_price_override` | D-13-GAPFILL-01: flat price overlay |
| 8 | `test_end_to_end_database_roundtrip` | SC-5: PropertyListing → DuckDB → read-back equality |
| 9 | `test_no_ai_attribution_in_committed_html_fixtures` | Meta: CLAUDE.md global rule guard |
| 10 | `test_extracted_json_sha_keys_match_html_fixtures` | Meta: drift guard catches HTML edits without JSON regen |
| 11 | `test_extracted_json_has_expected_shape` | Meta: required keys + money-fields-are-strings |

All 11 pass. The CLI surface is unchanged in this plan — Task 4 verified (via
`test_cli_exposes_mock_sonnet_hook_and_provenance_wrapping` source-grep) that
Plan 13-04 already shipped `MORTGAGE_OPS_MOCK_SONNET` + `_mock_sonnet_extract` +
`_wrap_scraped_provenanced_money`.

## Phase 13 closure audit

### Requirement closure (7/7)

| Req ID | Status | Closed by |
|---|---|---|
| INGEST-01 | Closed | Plan 13-04 (CLI block-detect routing) + Plan 13-06 integration test |
| INGEST-02 | Closed | Plan 13-03 (Sonnet extractor) + Plan 13-06 integration test |
| INGEST-03 | Closed | Plan 13-04 (CLI gap-fill merge) + Plan 13-06 integration test |
| INGEST-04 | Closed | Plan 13-02 (extract_zpid regex) + Plan 13-04 (CLI integration) + Plan 13-06 both-URL-pattern tests |
| PROP-01 | Closed | Plan 13-01 (PropertyListing + ProvenancedMoney) |
| PROP-02 | Closed | Plan 13-05 (DuckDB persistence) + Plan 13-06 full round-trip test |
| PERS-08 | Closed | Plan 13-05 (analyzed_listings schema + composite PK + lockfile) |

### D-13 lock audit (5/5 locks proven via tests)

- **D-13-GAPFILL-01:** 3-shape envelope (success / awaiting_user_input / blocked) proven across all plans; Plan 13-06 integration tests assert each shape on dedicated fixtures.
- **D-13-MUSTHAVE-01:** MUST_HAVE = (price, zip, property_type); condo-no-tax shape-1 test (`test_end_to_end_condo_partial_tax_missing_shape_1`) proves tax_annual is non-blocking NICE-TO-HAVE.
- **D-13-REANALYSIS-01:** composite PK (zpid, analyzed_at) proven via Plan 13-05's microsecond-delta freezegun test.
- **D-13-MODEL-01:** Sonnet 4.6 (not Haiku) inside CLI subprocess; no auto-retry; failure → None → shape-2 (Plan 13-03 + Plan 13-04 enforcement; Plan 13-06 verifies via `MORTGAGE_OPS_MOCK_SONNET=1` subprocess hook).
- **D-13-BLOCK-01:** 4 signals (status / length / captcha / missing_next_data); detection fires BEFORE Sonnet per cheap-first ordering locked in Plan 13-02 + verified in Plan 13-06's captcha fixture test (Sonnet never called because block-detect fires first).

### Open Questions audit (4/4 resolved)

- **Q1 (HTML cache mechanism):** Resolved — skill-side per-zpid cache at `data/cache/property-{zpid}.json` shipped in Plan 13-04. Round-2 `--user-provided` invocations skip Sonnet by reading the cache. Plan 13-06 verifies cache isolation via `cwd=tmp_path` in the user-overlay test.
- **Q2 (messages.parse vs messages.create):** Resolved — Plan 13-03 chose `messages.create()` + regex extraction (recorded in 13-00 + 13-03 summaries).
- **Q3 (Python duckdb runtime dep):** Resolved — `duckdb>=1.4,<2.0` promoted to runtime dependency in Plan 13-00.
- **Q4 (household_hash content vs structural):** Resolved — content SHA256 of `(household.yml + profile.yml + MORTGAGE30US value)` shipped in Plan 13-05 (`compute_household_hash`).

### Realistic Sonnet cost

Per Plan 13-03 research (priced at Sonnet 4.6 $3/$15 per 1M tokens): ~$0.16 per
extraction call (~50k input tokens for a 200KB Zillow page + ~800 output tokens).
At ~30 listings/month → ~$5/month. This corrects CONTEXT.md's earlier ~$0.02
estimate, which was Haiku-era; Sonnet is ~8x more expensive on large HTML inputs
but recovers the cost via fewer gap-fill round trips and higher extraction
fidelity.

## Verification

- `uv run pytest tests/test_property_listing.py tests/test_property_block_detector.py tests/test_property_extractor.py tests/test_property_fetch.py tests/test_property_persistence.py tests/test_property_ingestion_integration.py` → 98 passed, 1 skipped (intentional live-Sonnet skip without ANTHROPIC_API_KEY)
- `uv run pytest tests/test_property_ingestion_integration.py -v` → 11 passed in ~1.4s

## Deviations from plan

### Auto-fixed issues

**1. [Rule 1 - Bug] Fixture body contained `__NEXT_DATA__` substring in HTML comment**
- **Found during:** Task 1 verification (`! grep -q '__NEXT_DATA__' blocked_perimeterx.html` failed)
- **Issue:** The synthetic captcha-page fixture's explanatory prose referenced "script id=__NEXT_DATA__" in two paragraphs. Behaviorally harmless (captcha phrase fires first per cheap-first ordering), but violates the plan's verbatim acceptance criterion that the blocked fixture not contain `__NEXT_DATA__`.
- **Fix:** Rewrote both paragraphs to use "embedded listing payload" / "missing structured-payload tag" phrasing. Captcha detection still fires correctly.
- **Files modified:** tests/fixtures/zillow/blocked_perimeterx.html
- **Commit:** 469130c

**2. [Rule 3 - Blocking] Strict-mode Pydantic rejected dict-with-string-decimals via model_validate**
- **Found during:** Task 4 first test run (`test_end_to_end_database_roundtrip` failed)
- **Issue:** PropertyListing uses `strict=True, frozen=True, extra="forbid"`. Passing the CLI's envelope dict (where money/date/datetime are JSON strings) through `PropertyListing.model_validate(env["listing"])` raised 6 ValidationErrors — strict mode rejects string inputs for Decimal/date/datetime fields when validating from a dict.
- **Fix:** Route through `PropertyListing.model_validate_json(json.dumps(env["listing"]))` instead. Pydantic's JSON parser handles the string → Decimal / string → date / string → datetime coercion at the boundary. This is the same pattern `lib.property_persistence.read_latest_for_zpid` uses (matching the existing precedent rather than relaxing the model's strict-mode contract).
- **Files modified:** tests/test_property_ingestion_integration.py
- **Commit:** dbc1eff

**3. [Rule 3 - Blocking] Ruff pre-commit hook reformatted the integration test**
- **Found during:** Task 4 commit attempt
- **Issue:** Pre-commit ran ruff (legacy alias) + ruff format which removed an unused `import pytest` (no `pytest.*` references in the test module) and normalized one quoted-string-with-escaped-quotes line. Tests pass with or without the import; ruff fix is correctness, not a tradeoff.
- **Fix:** Allowed ruff's auto-fixes; re-ran tests (still 11/11 pass); committed.
- **Files modified:** tests/test_property_ingestion_integration.py
- **Commit:** dbc1eff

No architectural changes required (Rule 4); no auth gates.

## Out-of-scope items observed

The full `uv run pytest` shows 2 pre-existing failures in
`tests/test_rules/test_citation_coverage*.py` caused by a working-tree
modification to `lib/rules/fha_mip.py` (its docstring now reads "Citation
(operative):" instead of the expected literal "Citation:"). This modification
predates Plan 13-06 (`git status` showed it as already dirty at plan start) and
the plan's important_constraints explicitly preserve it untouched. These
failures are NOT in scope for Plan 13-06; they should be addressed in a
follow-up under the FHA-MIP / citation-coverage subsystem. All Phase-13 test
files are green (98 passed, 1 intentional skip).

## Self-Check: PASSED

All 7 created files exist on disk. All 4 per-task commits (469130c, ebc2add,
1231ca9, dbc1eff) exist in git log. Integration test suite green (11/11).
Phase-13 test files green (98/1 skip).
