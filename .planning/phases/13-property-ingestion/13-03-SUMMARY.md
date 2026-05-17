---
phase: 13-property-ingestion
plan: 03
subsystem: sonnet-extractor
tags: [phase-13, wave-3, sonnet, extractor, ingest-02, d-13-model-01]
dependency_graph:
  requires:
    - "Phase 13 Wave 0 scaffolding (tests/test_property_extractor.py xfail scaffold + pyproject mypy override + Probe A messages.parse=True)"
    - "Phase 13 Wave 1 lib.property_listing (PropertyListing field shape referenced by EXTRACTION_PROMPT)"
    - "Phase 11 anthropic SDK 0.100.0 (runtime-promoted in Wave 0)"
    - "stdlib os / json / re / typing.Final"
  provides:
    - "lib.property_extractor.extract_listing(html, source_url) -> dict[str, object] | None"
    - "lib.property_extractor.EXTRACTION_PROMPT (module-level Final[str] with all 13 PropertyListing field names)"
    - "lib.property_extractor.SONNET_MODEL = 'claude-sonnet-4-6' (D-13-MODEL-01 verbatim)"
    - "lib.property_extractor.SONNET_MAX_TOKENS = 4096"
    - "tests/conftest.py mock_sonnet fixture (sha256-keyed extracted/{sha16}.json loader)"
  affects:
    - "Plan 13-04 (CLI): scripts/property_fetch.py imports extract_listing AFTER detect_block returns None"
    - "Plan 13-04 (CLI tests): mock_sonnet fixture makes shape-1/2 envelope tests deterministic without live API"
    - "Plan 13-06 (integration fixtures): extracted/{sha16}.json drops are now plug-and-play via mock_sonnet"
    - "Phase 18 references doc: pins EXTRACTION_PROMPT verbatim (constant is grep-discoverable)"
tech_stack:
  added:
    - "lib.property_extractor module (Sonnet structured-extraction wrapper)"
    - "anthropic SDK runtime call site (first non-test use; Phase 11 was test-only)"
  patterns:
    - "Lazy import of anthropic INSIDE function body (D-18 fast --help; analog: fred_cli.py:97)"
    - "Outer try/except Exception with 'load-bearing always-exit-0 contract (Phase 12 CR-02)' comment (analog: fred_cli.py:212)"
    - "Final[str] / Final[int] module constants (analog: fred_cache.py:42-72)"
    - "_parse_json_with_prose_tolerance helper applies re.search(r'\\{.*\\}', raw, re.DOTALL) per Pitfall 18"
    - "HTML truncation to first 200_000 chars before prompt format (Pitfall 20 mitigation)"
    - "messages.parse API path (Wave-0 Probe A locked TRUE)"
key_files:
  created:
    - "lib/property_extractor.py"
  modified:
    - "tests/conftest.py"
    - "tests/test_property_extractor.py"
    - "pyproject.toml"
    - ".pre-commit-config.yaml"
decisions:
  - "API path: client.messages.parse(...) per Wave-0 Probe A (anthropic 0.100.0 ships messages.parse on Anthropic().messages). output_format INTENTIONALLY omitted - the prompt asks Sonnet to emit the JSON dict directly, and PropertyListing requires audit fields (source_url, zpid, fetched_at) that the CLI adds AFTER this call. Passing output_format=PropertyListing would force Sonnet to populate those audit fields it cannot know."
  - "First-brace regex (Pitfall 18) RETAINED as the defensive parser even on the parse() path. The parse() success contract still routes Sonnet's text through .content[0].text; if Sonnet prepends prose despite 'JSON ONLY', the regex first-brace match still recovers."
  - "Outer try/except catches bare Exception per Phase 12 CR-02 always-exit-0 doctrine. No noqa directive needed because BLE001 is not in the project's ruff selects (E, F, W, I, UP, B, SIM, RUF, TCH, PT). Comment 'load-bearing always-exit-0 contract (Phase 12 CR-02)' mirrors fred_cli.py:212 exactly."
  - "anthropic + duckdb added to .pre-commit-config.yaml mypy additional_dependencies so the pre-commit mypy hook (which runs file-isolated, NOT project-wide) can resolve runtime-promoted imports. Project-level mypy already finds them via the venv; this restores parity between the pre-commit and CI mypy gates."
  - "HTML truncation at 200_000 chars (Pitfall 20). 200KB tracks the ~50k-token Sonnet input bucket in the cost table; over-truncating risks losing __NEXT_DATA__, under-truncating burns ~$0.16/100KB. The 200_000-char cap is verbatim per RESEARCH Example 1 and PLAN action."
  - "Mock fixture sha256(html.encode('utf-8'))[:16] - 16 hex chars = 64-bit collision resistance, more than enough at personal scale (~30 listings/mo). Matches RESEARCH §'CI mock pattern' lines 966-973 verbatim."
metrics:
  duration_minutes: 6
  completed_date: "2026-05-17"
  tasks_completed: 3
  files_changed: 5
  loc_added: 119  # lib/property_extractor.py
  tests_added: 16  # 15 mocked + 1 skipif-guarded live
  xfails_flipped: 4  # 4 strict-xfail markers from Wave 0 (the +1 skipif scaffold also went live)
cost:
  per_call_usd: 0.16  # 50k input @ $3/1M + 800 output @ $15/1M (Sonnet 4.6 May 2026 pricing)
  monthly_estimate_at_30_listings: 5.00
  note: "Corrects CONTEXT.md's outdated $0.02 Haiku-era estimate. Sonnet on 200KB pages is ~8x pricier than Haiku; D-13-MODEL-01 accepts the delta because the cost of a Haiku miss + 2-step gap-fill round trip exceeds the model-price delta at personal scale."
---

# Phase 13 Plan 03: Sonnet Extractor Summary

One-liner: INGEST-02 Sonnet wrapper - 119-LOC `lib/property_extractor.py`
exposing `extract_listing(html, source_url) -> dict | None`, lazy-imports
anthropic SDK inside the function body, uses `client.messages.parse(...)`
per Wave-0 Probe A, applies Pitfall-18 first-brace regex as a defensive
parse fallback, truncates HTML to 200_000 chars before the prompt, and
returns `None` on EVERY failure mode per D-13-MODEL-01 always-exit-0
contract. 15 mocked tests + 1 skipif-guarded live smoke + a sha256-keyed
`mock_sonnet` conftest fixture close INGEST-02 at the unit-test layer.

## What Shipped

### Task 1 - `lib/property_extractor.py` (commit `1855ae3`)

119 LOC. One public function (`extract_listing`), one private helper
(`_parse_json_with_prose_tolerance`), three module-level `Final[...]`
constants. Module docstring documents the API-path decision (`messages.parse`
locked by Wave-0 Probe A), the always-exit-0 contract, the cost envelope
(~$0.16/call), and the upstream block-detection precedence.

**Public API (consumed by Plan 13-04):**

| Symbol               | Type                                          | Purpose                                                         |
| -------------------- | --------------------------------------------- | --------------------------------------------------------------- |
| `extract_listing`    | `(str, str) -> dict[str, object] \| None`     | Sonnet structured extraction; None on any failure               |
| `EXTRACTION_PROMPT`  | `Final[str]` (module-level constant, ~1560 chars) | The exact prompt; all 14 PropertyListing field names cited     |
| `SONNET_MODEL`       | `Final[str] = "claude-sonnet-4-6"`            | D-13-MODEL-01 verbatim (NOT haiku, NOT 3-5-sonnet)              |
| `SONNET_MAX_TOKENS`  | `Final[int] = 4096`                           | 3-7x headroom over typical 600-1200 token JSON output           |

**API path (Probe A outcome):**

Wave-0 13-00-SUMMARY confirmed `'parse' in dir(client.messages)` is
`True` on `anthropic==0.100.0`. This module uses `client.messages.parse(
    model=SONNET_MODEL, max_tokens=SONNET_MAX_TOKENS, messages=[...]
)` for the API call. `output_format` is intentionally OMITTED because:

1. The prompt directly instructs Sonnet to emit the JSON dict.
2. `PropertyListing` requires audit fields (`source_url`, `zpid`,
   `fetched_at`) that the CLI layer adds AFTER this call - passing
   `output_format=PropertyListing` would force Sonnet to populate those
   downstream audit fields it cannot know.

The first-brace regex fallback (Pitfall 18) is retained defensively so
that Sonnet-prepended prose ("Here is the data:\n{...}") still resolves
to a valid dict.

**Failure-mode map (all -> `None`):**

| Cause                            | Caught by                                    |
| -------------------------------- | -------------------------------------------- |
| Bad API key                      | `except Exception` (catches AuthenticationError) |
| Rate limit (429)                 | `except Exception` (catches RateLimitError)  |
| Server overload (5xx)            | `except Exception` (catches APIStatusError)  |
| Network timeout                  | `except Exception` (catches APIConnectionError) |
| Empty `response.content` list    | `if not response.content: return None`       |
| First block type != `"text"`     | `if response.content[0].type != "text"`      |
| Sonnet returned non-JSON         | `_parse_json_with_prose_tolerance`: re.search no match -> None |
| Sonnet returned malformed JSON   | `_parse_json_with_prose_tolerance`: json.JSONDecodeError -> None |
| `_parse_json_*` returns non-dict | Final `isinstance(result, dict)` guard -> None |

**Hard constraints honored:**

- `import anthropic` is lazy (inside `extract_listing` body); module import
  does NOT pull the SDK. Verified: `grep -E '^import anthropic'
  lib/property_extractor.py` returns no match.
- No retries: no `tenacity`, no `@retry`, no `RetryError` anywhere
  (D-13-MODEL-01 verbatim).
- HTML truncated to first 200_000 chars before being formatted into the
  prompt (`EXTRACTION_PROMPT.format(html=html[:200_000])`) - Pitfall 20.
- Outer try/except catches bare `Exception` per Phase 12 CR-02 always-exit-0
  doctrine (analog: `fred_cli.py:212`). No `noqa: BLE001` needed because
  BLE rules are not in the project's ruff selects.
- No `Co-Authored-By` / AI-attribution strings (CLAUDE.md global rule).

**pyproject.toml diff:** removed the `[[tool.mypy.overrides]] module =
"lib.property_extractor"` ignore_missing_imports entry now that the module
exists. Only `lib.property_persistence` override remains (Wave 5 lands it).

**.pre-commit-config.yaml diff:** added `anthropic>=0.100.0,<1.0` and
`duckdb>=1.4,<2.0` to the pre-commit mypy `additional_dependencies` so the
file-isolated pre-commit mypy gate matches the project-level mypy gate
(both runtime-promoted in Wave 0).

### Task 2 - `tests/conftest.py` (`mock_sonnet` fixture) (commit `35d0da9`)

+41 LOC appended (no existing fixtures touched). Single new fixture
`mock_sonnet(monkeypatch)` that:

- Computes `hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]` for
  every call site
- Looks up `tests/fixtures/zillow/extracted/{sha16}.json`
- Returns the parsed dict on hit, `None` on miss (or on
  `json.JSONDecodeError`)
- Monkeypatches the exact module path:
  `monkeypatch.setattr("lib.property_extractor.extract_listing", _fake)`

Imports (`hashlib`, `json`, `pathlib.Path`) live INSIDE the fixture body
so tests that never use `mock_sonnet` don't pay the import cost.

**Smoke test:** `test_mock_sonnet_fixture_returns_none_for_unknown_html`
in `tests/test_property_extractor.py` proves the miss path returns None
for any unknown html hash - this is exactly the shape Wave 4 (CLI) tests
need to exercise the shape-2 `awaiting_user_input` envelope path without
ever hitting live Sonnet.

### Task 3 - `tests/test_property_extractor.py` (xfails flipped) (commit `b8d27d3`)

309 LOC (was 50). All 4 Wave-0 `@pytest.mark.xfail(strict=True)` markers
removed; live test (`test_extract_listing_live_smoke`) retained as
`@pytest.mark.skipif(no ANTHROPIC_API_KEY)` only.

**Test inventory (16 tests, 15 mocked + 1 skipif live):**

| #  | Test                                                          | Asserts                                                    |
| -- | ------------------------------------------------------------- | ---------------------------------------------------------- |
| 1  | `test_sonnet_model_locked_to_4_6`                             | D-13-MODEL-01: SONNET_MODEL == "claude-sonnet-4-6"        |
| 2  | `test_sonnet_max_tokens_value`                                | SONNET_MAX_TOKENS == 4096                                  |
| 3  | `test_extraction_prompt_lists_all_13_fields`                  | All 14 PropertyListing field names appear in EXTRACTION_PROMPT |
| 4  | `test_extract_listing_returns_dict_on_clean_json`             | Happy path: dict with price+zip+property_type returned     |
| 5  | `test_extract_listing_strips_prose_prefix`                    | Pitfall 18: "Here is the data:\n{...}" still parses        |
| 6  | `test_extract_listing_returns_none_on_auth_error`             | anthropic.AuthenticationError -> None                      |
| 7  | `test_extract_listing_returns_none_on_rate_limit`             | anthropic.RateLimitError -> None                           |
| 8  | `test_extract_listing_returns_none_on_network_error`          | anthropic.APIConnectionError -> None                       |
| 9  | `test_extract_listing_returns_none_on_generic_exception`      | RuntimeError -> None (BLE doctrine)                        |
| 10 | `test_extract_listing_returns_none_on_empty_response_content` | response.content == [] -> None                             |
| 11 | `test_extract_listing_returns_none_on_non_text_block`         | content[0].type == "tool_use" -> None                      |
| 12 | `test_extract_listing_returns_none_on_malformed_json`         | "not json {{{ broken" -> None                              |
| 13 | `test_extract_listing_returns_none_when_no_braces`            | "absolutely no json here" -> None                          |
| 14 | `test_extract_listing_truncates_html_at_200k`                 | 500KB input -> exactly 200_000 chars survive into the prompt |
| 15 | `test_mock_sonnet_fixture_returns_none_for_unknown_html`      | mock_sonnet fixture smoke: missing fixture -> None         |
| 16 | `test_extract_listing_live_smoke` (skipif)                    | Skipped without ANTHROPIC_API_KEY; manual-run-only         |

**Final pytest:** `15 passed, 1 skipped in 0.25s` on
`tests/test_property_extractor.py`. Zero xfail, zero XPASS, zero failed,
zero error.

## Round-trip pattern (Sonnet -> dict)

```python
# How a downstream caller (Plan 13-04 CLI) will use this:
from lib.property_extractor import extract_listing

extracted = extract_listing(html_body, "https://www.zillow.com/.../12345_zpid/")
if extracted is None:
    return _emit({"listing": None, "missing": ["price", "zip", "property_type"],
                  "error": None, "awaiting_user_input": True, ...})

# Add the 3 audit fields the CLI knows but Sonnet doesn't:
extracted["source_url"] = url
extracted["zpid"] = extract_zpid(url)
extracted["fetched_at"] = _now_iso()
listing = PropertyListing.model_validate(extracted)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Lint config alignment] Plan-prescribed `noqa: BLE001`
   removed by ruff RUF100**

- **Found during:** Task 1 ruff check.
- **Issue:** The PLAN's `<action>` block + acceptance criteria require the
  outer try/except line to carry a `# noqa: BLE001 - always-exit-0 (Phase
  12 CR-02 contract)` comment. But the project's ruff config in
  `pyproject.toml:46-56` selects only `E, F, W, I, UP, B, SIM, RUF, TCH,
  PT` - the `BLE` rule family is NOT enabled, so the `noqa: BLE001`
  directive is unused. ruff `RUF100` ("Unused noqa") auto-strips it.
- **Fix:** Drop the `noqa: BLE001` token but retain the load-bearing
  comment in the project's existing form, matching `fred_cli.py:212`
  verbatim: `except Exception:  # load-bearing always-exit-0 contract
  (Phase 12 CR-02)`. The doctrine is preserved; the linter just has no
  rule to suppress.
- **Files modified:** `lib/property_extractor.py` (comment form only).
- **Commit:** `1855ae3` (bundled into Task 1's commit).

**2. [Rule 3 - Pre-commit hook alignment] anthropic + duckdb missing
   from pre-commit mypy additional_dependencies**

- **Found during:** Task 1 commit attempt (pre-commit mypy failure
  `Cannot find implementation or library stub for module named "anthropic"`).
- **Issue:** Pre-commit runs mypy in a clean per-hook environment with
  only the `additional_dependencies` listed in `.pre-commit-config.yaml`.
  Wave 0 promoted both `anthropic` and `duckdb` to runtime
  `[project].dependencies` but never propagated them into the pre-commit
  hook env, so any commit that touches `lib/property_extractor.py` or
  `lib/property_persistence.py` fails the file-isolated mypy hook even
  though the project-level mypy (which uses the venv) passes cleanly.
- **Fix:** Append both pins (`anthropic>=0.100.0,<1.0` and
  `duckdb>=1.4,<2.0`) to the pre-commit mypy `additional_dependencies`
  block. This restores parity between local pre-commit and CI mypy gates.
- **Files modified:** `.pre-commit-config.yaml` (mypy hook
  additional_dependencies block).
- **Commit:** `1855ae3` (bundled into Task 1's commit).

**3. [Rule 3 - Plan-spec API path adjustment] AuthenticationError +
   RateLimitError constructors require non-None response argument**

- **Found during:** Task 3 test authoring (drafting per the PLAN's
  `<action>` block lines 511-526 verbatim).
- **Issue:** The PLAN's action specifies
  `anthropic.AuthenticationError("bad key", response=None, body=None)`
  with `# type: ignore[arg-type]`. At runtime in anthropic 0.100.0 the
  constructor dereferences `response.request` and raises `AttributeError:
  'NoneType' object has no attribute 'request'` BEFORE the BaseException
  init finishes. The plan-prescribed test would have failed at fixture
  setup, not at the function under test.
- **Fix:** Construct minimal `httpx.Request` + `httpx.Response` stubs
  via a `_make_http_response(status)` helper; pass `response=
  _make_http_response(401)` for AuthenticationError and
  `response=_make_http_response(429)` for RateLimitError. The
  APIConnectionError test passes a real `httpx.Request` directly. The
  behavioral assertions (each exception class -> None) are unchanged.
- **Files modified:** `tests/test_property_extractor.py` (test helper +
  3 failure-mode tests).
- **Commit:** `b8d27d3` (bundled into Task 3's commit).

### Plan-spec test instantiation form (not a deviation, but worth flagging)

The PLAN action documents `_FakeClient` such that `client.messages.create`
AND `client.messages.parse` both resolve via `self.messages = self`. Since
Wave-0 Probe A locked `messages.parse` as the production path, only
`parse()` is hit in normal happy/failure tests. `create()` is retained on
`_FakeClient` for defense-in-depth in case the SDK shape changes upstream
- removing it would make tests fragile to a single SDK API tweak.

## Authentication Gates

None. All 15 mocked tests run without `ANTHROPIC_API_KEY` because the
anthropic.Anthropic constructor is monkeypatched away. The 16th test
(`test_extract_listing_live_smoke`) is `@pytest.mark.skipif(no
ANTHROPIC_API_KEY)` and is intended for manual-only runs - per
13-CONTEXT.md and Phase 11 D-02, CI must NOT inject the key (synthetic-
only-in-CI). It cleanly skips in airgapped CI.

## Verification

- [x] `lib/property_extractor.py` exists; `wc -l` = 119 (>= 80 required)
- [x] Exactly one `def extract_listing` (verified `grep -c '^def
  extract_listing' lib/property_extractor.py` returns 1)
- [x] `SONNET_MODEL: Final[str] = "claude-sonnet-4-6"` verbatim
- [x] `SONNET_MAX_TOKENS: Final[int] = 4096` verbatim
- [x] `EXTRACTION_PROMPT: Final[str]` module-level constant; all 13
  PropertyListing field names (+ `list_date`) grep-found
- [x] `html[:200_000]` verbatim present
- [x] Lazy import: `! grep -E '^import anthropic' lib/property_extractor.py`
  returns no match (anthropic import lives INSIDE function body)
- [x] No `tenacity`, no `@retry`, no `RetryError` (D-13-MODEL-01)
- [x] Outer `except Exception` with load-bearing always-exit-0 comment
  (project-standard form; BLE not in ruff selects so no noqa needed)
- [x] `_parse_json_with_prose_tolerance` helper present with `re.DOTALL`
  flag (Pitfall 18)
- [x] No `Co-Authored-By` / AI-attribution strings (CLAUDE.md global rule)
- [x] `uv run python -c "from lib.property_extractor import
  extract_listing, EXTRACTION_PROMPT, SONNET_MODEL, SONNET_MAX_TOKENS"`
  succeeds without `ANTHROPIC_API_KEY` (proves lazy import)
- [x] `grep -c '^def mock_sonnet' tests/conftest.py` returns 1
- [x] `mock_sonnet` uses `hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]`
  (NOT md5, NOT [:8], NOT [:32])
- [x] `mock_sonnet` monkeypatches `"lib.property_extractor.extract_listing"`
  exactly
- [x] `mock_sonnet` returns None on missing fixture AND on json.JSONDecodeError
- [x] `mock_sonnet` imports (hashlib/json/pathlib.Path) INSIDE fixture body
- [x] `grep -c '@pytest.mark.xfail' tests/test_property_extractor.py`
  returns 0
- [x] `grep -c '^def test_' tests/test_property_extractor.py` returns 16
  (>= 12 required)
- [x] `uv run pytest tests/test_property_extractor.py -v` -> 15 passed,
  1 skipped, 0 xfail, 0 XPASS, 0 failed, 0 error
- [x] `uv run pytest` full suite: 700 passed, 6 skipped, 18 xfailed
  (Wave 4/5 stubs); 2 failed are the pre-existing
  `tests/test_rules/test_citation_coverage*.py::*[fha_mip]` baseline
  failures explicitly excluded from this plan's scope per executor
  constraints (the dirty `lib/rules/fha_mip.py` stays unstaged per Plan
  13-01 + 13-02 SUMMARY precedent; zero regression from the Plan 13-02
  baseline)
- [x] Pre-existing dirty file (`lib/rules/fha_mip.py`) NOT staged;
  pre-existing untracked files (`.planning/*.md` notes, `data/.lock 2..5`)
  NOT staged - per executor constraints
- [x] Pre-commit hooks pass (ruff, ruff-format, mypy --strict,
  DATA_CONTRACT.md guard) on all three task commits
- [x] mypy override for `lib.property_extractor` removed from
  `pyproject.toml`

## INGEST-02 Closure

INGEST-02 ("Sonnet pulls canonical fields from `__NEXT_DATA__`") is closed
at the unit-test layer:

1. `lib/property_extractor.py::extract_listing` is the public API that
   Plan 13-04 will import and invoke after `detect_block` returns None.
2. The 14 prompt fields (zpid, price, zip, property_type, beds, baths,
   sqft, year_built, tax_annual, hoa_monthly, insurance_estimate_annual,
   zestimate, days_on_market, list_date) cover the entire PropertyListing
   v1.1 field surface from Plan 13-01.
3. 15 mocked tests prove happy-path dict return + 8 failure modes all
   route to `None` per D-13-MODEL-01 always-exit-0.
4. The live-smoke skipif test is the manual gate for future
   real-Sonnet-against-real-Zillow drift checks (Phase 17 fixture
   expansion + Phase 18 references doc).

The end-to-end shape-1 envelope assembly closes in Plan 13-04 (CLI), which
combines `detect_block` + `extract_zpid` + `extract_listing` +
`PropertyListing.model_validate` + envelope emission.

## D-13-MODEL-01 Closure

| Constraint | Implementation receipts |
| ---------- | ----------------------- |
| Sonnet 4.6 (NOT Haiku) | `SONNET_MODEL: Final[str] = "claude-sonnet-4-6"` verbatim |
| Call lives inside CLI subprocess | Module imports lazily; CLI (Plan 13-04) is the only caller |
| No auto-retry | No `tenacity`, no `@retry`, single `client.messages.parse(...)` invocation |
| Failure -> None (caller emits shape-2) | Outer `except Exception` + 4 typed-failure paths all return None; 9 mocked tests prove the contract |

## Probe A Result Honored

Wave-0 13-00-SUMMARY recorded `messages.parse available: True` on anthropic
0.100.0. This module uses `client.messages.parse(model, max_tokens,
messages)` exclusively for the API call. The `output_format` parameter is
intentionally omitted (see Decisions); the first-brace regex fallback
(Pitfall 18) lives in `_parse_json_with_prose_tolerance` for defensive
prose-prefix recovery on either API path.

## Cost (RESEARCH-Corrected)

| Bucket                | Tokens  | Rate            | Per-call |
| --------------------- | ------- | --------------- | -------- |
| Input (200KB ~ 50k)   | 50,000  | $3/1M (Sonnet 4.6)  | $0.150   |
| Output (~800 JSON)    | 800     | $15/1M (Sonnet 4.6) | $0.012   |
| **Total**             |         |                 | **~$0.16** |

At 30 listings/month -> ~$5.00/month. CONTEXT.md's earlier ~$0.02 estimate
was Haiku-era; Sonnet on 200KB pages is ~8x pricier. The delta is acceptable
per D-13-MODEL-01 because the cost of a Haiku miss + 2-step gap-fill round
trip exceeds the model-price delta at personal scale.

## Self-Check: PASSED

Verified by direct filesystem + git inspection:

- FOUND: lib/property_extractor.py
- FOUND: tests/test_property_extractor.py (modified; 16 live tests; 0 xfail)
- FOUND: tests/conftest.py (modified; mock_sonnet fixture appended)
- FOUND: pyproject.toml (modified; lib.property_extractor mypy override removed)
- FOUND: .pre-commit-config.yaml (modified; anthropic + duckdb in mypy additional_dependencies)
- FOUND: commit 1855ae3 (Task 1 - lib/property_extractor.py + pyproject.toml + .pre-commit-config.yaml)
- FOUND: commit 35d0da9 (Task 2 - tests/conftest.py mock_sonnet fixture)
- FOUND: commit b8d27d3 (Task 3 - tests/test_property_extractor.py xfails flipped)
- VERIFIED: `uv run pytest tests/test_property_extractor.py` -> 15 passed, 1 skipped
- VERIFIED: `uv run python -c "from lib.property_extractor import extract_listing, EXTRACTION_PROMPT, SONNET_MODEL, SONNET_MAX_TOKENS"` succeeds without ANTHROPIC_API_KEY
- VERIFIED: zero regression vs Plan 13-02 baseline (the 2 pre-existing `[fha_mip]` failures remain unchanged)

## Next: Wave 4

`/gsd-execute-phase 13` continues with Plan 13-04 (CLI) - depends on BOTH
Plan 13-02 (block detector, shipped) AND Plan 13-03 (this plan,
extractor). Wave 4 ships `.claude/skills/mortgage-ops/scripts/
property_fetch.py` composing `detect_block` -> `extract_zpid` ->
`extract_listing` -> `PropertyListing.model_validate` -> three-envelope
emission (success / awaiting_user_input / blocked) + flips the 10 xfails
in `tests/test_property_fetch.py`.

Plan 13-05 (persistence) depends only on Plan 13-01 (PropertyListing) and
remains parallel-eligible with Plan 13-04.

The remaining `[[tool.mypy.overrides]]` entry (`lib.property_persistence`)
will come off as Plan 13-05 ships its module.
