---
phase: 13-property-ingestion
reviewed: 2026-05-16T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - lib/property_listing.py
  - lib/property_block_detector.py
  - lib/property_extractor.py
  - lib/property_persistence.py
  - .claude/skills/mortgage-ops/scripts/property_fetch.py
  - tests/conftest.py
  - tests/test_property_listing.py
  - tests/test_property_block_detector.py
  - tests/test_property_extractor.py
  - tests/test_property_fetch.py
  - tests/test_property_persistence.py
  - tests/test_property_ingestion_integration.py
  - tests/fixtures/zillow/README.md
findings:
  critical: 2
  warning: 8
  info: 6
  total: 16
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-05-16
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The Phase 13 property-ingestion stack is structurally sound: PropertyListing/ProvenancedMoney mirrors Phase 1 conventions, block detection runs before Sonnet to save cost, the CLI honors the always-exit-0 contract, and persistence reuses the Phase 12 lockfile pattern. Money discipline (Decimal-as-string, frozen + strict Pydantic) is enforced consistently.

Two correctness blockers stand out:

1. **Q1 cache is path-anchored to the real repo, not to the CWD**, so the integration test that passes `cwd=tmp_path` for "isolation" is not actually isolated — it writes into the real `data/cache/` and would pick up stale state across runs (BLOCKER CR-01).
2. **The prose-tolerant JSON extractor uses a greedy `{.*}` match across DOTALL**, which silently fuses two adjacent JSON objects from a chatty Sonnet response into one malformed object — exactly the case the fallback is meant to defend against (BLOCKER CR-02).

The remaining findings are robustness issues around user-input merging (null clears, decimal beds), test artifacts that pollute the real repo, and minor input-validation gaps.

## Critical Issues

### CR-01: Q1 cache path is project-root-anchored — integration test "isolation" via cwd does not work and tests pollute the real repo

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:213-241`, `tests/test_property_ingestion_integration.py:159-183`, `tests/test_property_fetch.py:270-296`

**Issue:** `cache_path` is computed from `project_root = Path(__file__).resolve().parents[4]`, which resolves to the real repo root regardless of the caller's CWD:

```python
project_root = Path(__file__).resolve().parents[4]
...
cache_path = project_root / "data" / "cache" / f"property-{zpid}.json"
```

This has two consequences:

1. `tests/test_property_ingestion_integration.py::test_end_to_end_user_provided_price_override` runs the CLI with `cwd=tmp_path` and creates `tmp_path/data/cache/`, but the CLI writes to `<repo>/data/cache/property-12345678.json`. The "isolation" is illusory — a prior failed run leaves a cached extraction that biases later runs, and the test silently writes into the real project tree.
2. `tests/test_property_fetch.py::test_cli_writes_html_cache_on_round_1` directly asserts that `<repo>/data/cache/property-12345.json` exists. It deletes the file at the start of the test but never deletes it after, so the test always leaves a build artifact in the real `data/` directory. Combined with `@pytest.mark.skipif(... not data/.exists())`, the test silently skips on fresh clones and writes a permanent artifact on every run thereafter.

This is a correctness blocker because:
- The CLI's documented Q1 behavior in the docstring ("on Round 2 ... the CLI reads that JSON instead of re-invoking Sonnet") becomes non-deterministic across users/branches who share the same repo path but different `data/cache/` contents.
- Test pollution of the real `data/` tree violates the project layer contract (`data/` is gitignored generated state, not test scratch).

**Fix:** Accept a `--cache-dir` CLI flag (default to `<project_root>/data/cache` for production, override to `tmp_path / "data" / "cache"` in tests), OR resolve the cache dir from `os.environ.get("MORTGAGE_OPS_CACHE_DIR")` with a project-root fallback. Then update the two tests to use the override:

```python
# property_fetch.py
import os
default_cache_dir = project_root / "data" / "cache"
cache_dir = Path(os.environ.get("MORTGAGE_OPS_CACHE_DIR", default_cache_dir))
cache_path = cache_dir / f"property-{zpid}.json"
```

```python
# test_property_ingestion_integration.py::_run_cli_with_mock_sonnet
env["MORTGAGE_OPS_CACHE_DIR"] = str(tmp_path / "cache")
```

Then `test_cli_writes_html_cache_on_round_1` should also point at a `tmp_path` cache dir rather than asserting on the real repo's `data/cache/`.

---

### CR-02: `_parse_json_with_prose_tolerance` greedy regex fuses adjacent JSON objects into malformed garbage

**File:** `lib/property_extractor.py:108-119`

**Issue:** The regex used to recover JSON from a prose-prefixed Sonnet response is:

```python
match = re.search(r"\{.*\}", raw, re.DOTALL)
```

`.*` is greedy under `DOTALL`, so given a response like:

```
Here is the data: {"price":"1.00","zip":"94110","property_type":"SFH"}

Note: I also considered {"alternative":"value"} but went with the first one.
```

the regex captures **everything from the first `{` to the last `}`**, producing the substring `{"price":"1.00",...,"SFH"} ... {"alternative":"value"}`. `json.loads` then fails on the embedded prose, and the function returns `None` — exactly the failure case the prose-tolerance helper is supposed to recover from.

The Pitfall-18 mitigation this code claims to be is therefore conditional: it works only when Sonnet emits a single brace pair, which is the case the bare `json.loads(raw)` already handles. Any chatty response with two brace pairs falls through to `None` and the user sees shape-2 awaiting_user_input despite a valid extraction being present in the response.

The unit test `test_extract_listing_strips_prose_prefix` (test_property_extractor.py:156-161) only covers single-pair input, so this is not caught by tests.

**Fix:** Use a non-greedy match anchored on balanced braces. The minimal one-line fix is non-greedy `.*?` combined with iteration to try each candidate, or — preferred — a brace-balanced scanner:

```python
def _parse_json_with_prose_tolerance(raw: str) -> dict[str, object] | None:
    import json

    start = raw.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(raw)):
            ch = raw[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(raw[start : i + 1])
                    except json.JSONDecodeError:
                        break
                    return result if isinstance(result, dict) else None
        start = raw.find("{", start + 1)
    return None
```

And add a unit test that asserts a response with prose between two JSON objects still returns the first dict.

## Warnings

### WR-01: User-provided `null` for ProvenancedMoney field crashes Pydantic with `Decimal("None.00")`

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:128-149`

**Issue:** `_merge_user_provided` does not handle null/empty for `PROVENANCED_MONEY_FIELDS`:

```python
if field in PROVENANCED_MONEY_FIELDS:
    extracted[field] = {
        "value": _strip_money(str(value)),
        "provenance": "user_provided",
    }
```

If the caller passes `{"tax_annual": null}` to *clear* a previously-extracted tax, `str(None)` → `"None"`, then `_strip_money("None")` → `"None.00"` (no dot present, padded), then Pydantic validation fails. The CLI falls through to shape-2 with all three MUST_HAVE fields listed as missing — even when those fields were actually present — because the failed validation is generic. The user sees a misleading "missing price/zip/property_type" message.

The non-money path (line 137-141) handles this correctly: `None`/`""` → assigns `None`. The money path should mirror that.

**Fix:**

```python
if field in PROVENANCED_MONEY_FIELDS:
    if value in (None, ""):
        extracted[field] = None
    else:
        extracted[field] = {
            "value": _strip_money(str(value)),
            "provenance": "user_provided",
        }
```

---

### WR-02: User-provided decimal value for integer field (e.g. `"beds": "3.5"`) becomes shape-3 unexpected_failure instead of shape-2 awaiting_user_input

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:136-138`

**Issue:** `_merge_user_provided` unconditionally casts non-money number fields with `int(value)`:

```python
elif field in NON_MONEY_NUMBER_FIELDS:
    extracted[field] = int(value) if value is not None and value != "" else None
```

If a user types `{"beds": "3.5"}` or `{"beds": "three"}`, `int(...)` raises ValueError. The outer try in `__main__` then routes to shape-3 `unexpected_failure: ValueError(...)` — visible to the LLM frontend as an unrecoverable error, when the correct UX is shape-2 with `beds` re-prompted.

**Fix:** Catch the ValueError per field and route to shape-2 with the offending field in `missing`, or coerce via float first then int:

```python
elif field in NON_MONEY_NUMBER_FIELDS:
    try:
        extracted[field] = int(value) if value not in (None, "") else None
        extracted[f"{field}_provenance"] = "user_provided"
    except (ValueError, TypeError):
        # Re-prompt by leaving field unset and tagging as still-missing
        extracted.pop(field, None)
        extracted.pop(f"{field}_provenance", None)
```

---

### WR-03: Unknown user-provided fields silently dropped to extra="forbid" failure with misleading "missing" list

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:144-148`

**Issue:** Unknown user keys are passed through verbatim:

```python
else:
    # Unknown / audit-adjacent field — overlay verbatim. Pydantic's
    # extra="forbid" on PropertyListing will reject genuinely invalid
    # keys at validation time (shape-2 path).
    extracted[field] = value
```

PropertyListing has `extra="forbid"`, so any unknown key triggers ValidationError. The shape-2 fallback (line 349) then reports the three MUST_HAVE fields as `missing` regardless of whether they're actually present — so a user typo like `{"bedz": 3, "price":"...", "zip":"...", "property_type":"SFH"}` gets a misleading "missing price/zip/property_type" response.

**Fix:** Either (a) drop unknown keys with a stderr warning instead of letting them poison validation, or (b) detect Pydantic's ValidationError on extra fields and surface the actual offending key in the missing list:

```python
else:
    sys.stderr.write(f"unknown user-provided field dropped: {field!r}\n")
    # do not assign
```

Or, in the validation handler at line 348, inspect `exc.errors()` for `type == "extra_forbidden"` and include those keys in the response.

---

### WR-04: Shape-2 `missing` list is hardcoded to MUST_HAVE, ignoring which MUST_HAVE fields are actually present

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:307-318, 349-360`

**Issue:** Two shape-2 emission paths report `missing` inconsistently:

- Line 312 (extractor returned None, no user_provided): hardcodes `list(MUST_HAVE)` — fine.
- Line 350: computes `present = {f for f in MUST_HAVE if extracted.get(f) not in (None, "")}`, then `missing = [f for f in MUST_HAVE if f not in present]`. But line 355 then does `missing if missing else list(MUST_HAVE)` — meaning *if Pydantic failed but all three MUST_HAVE keys were non-empty*, the response claims all three are missing.

This happens routinely: if Pydantic rejects because `baths="2.25"` (not on the 0.5 grid) or because `zip="9411"` (4 digits), the three MUST_HAVE fields are populated yet the response says all three are missing. The LLM frontend re-prompts for them and the user-visible error is wrong.

**Fix:** When Pydantic raises, extract the actual failing fields from `exc.errors()` and surface those in `missing`. Fall back to MUST_HAVE only when no field-specific info is available:

```python
except ValidationError as exc:
    failing = {err["loc"][0] for err in exc.errors() if err.get("loc")}
    missing = [f for f in MUST_HAVE if f not in extracted or extracted[f] in (None, "")]
    missing.extend(sorted(failing - set(missing)))
    ...
```

---

### WR-05: `compute_household_hash` lacks separator between inputs — concatenation collision possible

**File:** `lib/property_persistence.py:60-75`

**Issue:** The hash function concatenates raw bytes with no separator:

```python
h.update(household_yml.read_bytes())
h.update(profile_yml.read_bytes())
h.update(mortgage30us_value.encode("utf-8"))
```

This means `household.yml=b"ab", profile.yml=b"cd", rate="0.06"` hashes identically to `household.yml=b"abc", profile.yml=b"d", rate="0.06"`. While unlikely to manifest with real YAML content (which always starts with a key), the hash is used as the cache key for re-analysis decisions per D-13-REANALYSIS-01 — a collision would silently skip a re-analysis. Since the table is append-only the impact is degraded (no incorrect numbers shown), but the hash is no longer a content-fingerprint guarantee.

**Fix:** Insert a unique-byte separator between segments, or hash the segment lengths in:

```python
h = hashlib.sha256()
for blob in (household_yml.read_bytes(), profile_yml.read_bytes(), mortgage30us_value.encode("utf-8")):
    h.update(len(blob).to_bytes(8, "big"))
    h.update(blob)
return h.hexdigest()
```

(Existing tests still pass since they only assert determinism + variance, not collision-resistance.)

---

### WR-06: `_strip_money` accepts negatives, blanks, and non-numeric — propagates "garbage.00" to Pydantic

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:71-76`

**Issue:** `_strip_money` only strips `$` and `,`, then pads with `.00`. No validation:

- `_strip_money("")` → `".00"` → Decimal parses as 0 — but PropertyListing.price has no lower bound, so a user typo "" silently becomes $0.00. Pydantic accepts it; the persisted listing claims a $0 home.
- `_strip_money("-625000")` → `"-625000.00"` → Decimal accepts negative; PropertyListing.price has no `ge=0` constraint, so a negative price persists.
- `_strip_money("abc")` → `"abc.00"` → Decimal raises InvalidOperation → caught by outer try → shape-3 unexpected_failure (should be shape-2).

**Fix:** Either add `ge=Decimal("0")` to `price` and `gt=Decimal("0")` to the money ProvenancedMoney fields in PropertyListing, or validate at the strip layer and raise a typed exception that the merge step can convert to shape-2.

Minimum: add a positive-money constraint to the model:

```python
# lib/property_listing.py
price: Annotated[Money, Field(gt=Decimal("0"))]
```

---

### WR-07: `NEXT_DATA_RE` rejects single-quoted attributes; brittle against innocuous Zillow markup variants

**File:** `lib/property_block_detector.py:48-51`

**Issue:** The regex requires double-quoted `id`:

```python
NEXT_DATA_RE = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>', re.IGNORECASE)
```

Pages emitting `id='__NEXT_DATA__'` or even unquoted `id=__NEXT_DATA__` (legal HTML5) are silently flagged as `missing_next_data` and routed to shape-3, even though the JSON is present and Sonnet would happily extract it. Comments in the file reference Pitfall 19 (attribute *order* variance) but not quoting variance.

**Fix:** Broaden the regex:

```python
NEXT_DATA_RE = re.compile(
    r'<script[^>]*\bid\s*=\s*["\']?__NEXT_DATA__["\']?[^>]*>',
    re.IGNORECASE,
)
```

Add a test variant in `test_property_block_detector.py` for single-quoted and unquoted forms.

---

### WR-08: Persistence write failure swallowed silently in CLI — successful shape-1 emitted despite no DB row

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:376-405`

**Issue:** The persistence block is wrapped in `try/except Exception` that only writes to stderr:

```python
try:
    from lib.property_persistence import compute_household_hash, write_listing
    ...
    write_listing(listing, household_hash=household_hash)
except Exception as exc:
    sys.stderr.write(f"persistence warning: {exc!r}\n")
```

The next line emits a shape-1 envelope claiming `awaiting_user_input: false, error: null`. A downstream LLM consumer reading stdout-only (the documented contract) has no way to know the listing was NOT persisted. The Phase 14 query path (planned per the docstring) will then miss this listing entirely.

This is documented as "best-effort; never blocks envelope emission" — but the envelope contract has no field for "validated but not persisted," so the persistence failure is invisible to the caller.

**Fix:** Add a `persisted: bool` field to the envelope, or include `persistence_error: str | None`. At minimum, log the failure to a known location the LLM can re-read (e.g., stderr is not in the envelope contract; consider writing to `data/cache/last-persistence-error.json` or adding `persisted_at: str | null` alongside `fetched_at`).

If by-design the LLM doesn't care, document the silent-success-on-DB-failure mode explicitly in the SKILL.md routing docs.

## Info

### IN-01: `year_built` upper bound hardcoded to 2030 — will reject new construction in 4 years

**File:** `lib/property_listing.py:76`

**Issue:** `year_built: int | None = Field(default=None, ge=1700, le=2030)`. After 2030, new-construction listings will fail validation. The conventions section in CLAUDE.md emphasizes reference data should live in YAML with `effective:` dates, not in code.

**Fix:** Either compute the upper bound from `datetime.now().year + 1` (allowing pre-sales) or move the constant to `data/reference/property_validation.yml`.

---

### IN-02: `_coerce_money_to_string` treats `price` as a possibly-wrapped dict even though prompt says price is always a string

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:84-91`

**Issue:** The loop iterates `MONEY_FIELDS` (which includes "price") and branches on `isinstance(v, dict) and "value" in v` to coerce inner floats. Since the prompt explicitly tells Sonnet to emit `price` as a bare string, the dict branch is dead code for price.

Not a bug, but the asymmetric handling muddies intent. Consider splitting into `_coerce_bare_money` and `_coerce_provenanced_money`, each with a focused field set.

---

### IN-03: `MORTGAGE_OPS_MOCK_SONNET` env-var documented as test-only but no production guard

**File:** `.claude/skills/mortgage-ops/scripts/property_fetch.py:36-40, 297-298`

**Issue:** The docstring states "Production usage MUST leave this env var unset" but the code itself has no production guard. A future deployment that accidentally exports the var (e.g., from a CI cache) silently downgrades to shape-2 forever (the sha-keyed fixture won't exist in prod).

**Fix:** Either accept the documentation-only guarantee, or add a startup check: if `MORTGAGE_OPS_MOCK_SONNET=1` and `not (project_root / "tests").exists()`, emit a stderr warning and ignore the var.

---

### IN-04: `detect_block` uses `len(body)` (chars) but constant is named `MIN_BODY_BYTES`

**File:** `lib/property_block_detector.py:44, 70`

**Issue:** `MIN_BODY_BYTES = 5000` but the check is `len(body) < MIN_BODY_BYTES`. Python `len(str)` is character count; for ASCII these are equal but for UTF-8 multibyte sequences they differ. Documented intent is "5KB of body" — true byte count would be `len(body.encode("utf-8"))`.

For typical Zillow HTML (mostly ASCII) the discrepancy is small. Rename the constant to `MIN_BODY_CHARS` or change the check to use `.encode("utf-8")` if byte semantics are required.

---

### IN-05: `_make_http_response` test helper builds an httpx Response with no body — anthropic SDK exceptions may inspect content in future versions

**File:** `tests/test_property_extractor.py:83-87`

**Issue:** Minor test brittleness — the helper only sets the status code. If anthropic SDK exception constructors begin to require a non-empty response body for parsing error context, these tests will fail with cryptic SDK-internal errors. Currently fine on `anthropic` 0.100.0.

**Fix:** Optional — pass `json={"error": {"type": "...", "message": "..."}}` when constructing the response to mirror the real SDK shape.

---

### IN-06: Integration test `test_extracted_json_has_expected_shape` hardcodes count `== 2`

**File:** `tests/test_property_ingestion_integration.py:284-287`

**Issue:** `assert len(json_files) == 2` will fail the moment Phase 17 adds the planned jumbo + multifamily fixtures (mentioned in `tests/fixtures/zillow/README.md` line 18: "Phase 17 expansion target: 2 more fixtures"). Phase 17 then has to update Phase 13 tests.

**Fix:** Replace with `assert len(json_files) >= 2` and keep the per-file shape assertion. Or, drive the count from a manifest file under `tests/fixtures/zillow/`.

---

_Reviewed: 2026-05-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
