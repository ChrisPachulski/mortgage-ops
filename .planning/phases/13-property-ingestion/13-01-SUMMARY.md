---
phase: 13-property-ingestion
plan: 01
subsystem: property-listing-model
tags: [phase-13, wave-1, pydantic-v2, property-listing, provenanced-money, prop-01, prop-02-baseline]
dependency_graph:
  requires:
    - "Phase 13 Wave 0 scaffolding (xfail markers + pyproject mypy overrides)"
    - "Phase 1 lib.models.Money Annotated[Decimal] alias"
    - "Phase 1 ConfigDict(strict=True, frozen=True, extra='forbid') pattern"
    - "Phase 12 datetime Z-suffix convention (Pitfall 21)"
  provides:
    - "lib.property_listing.PropertyListing (PROP-01 Pydantic v2 model)"
    - "lib.property_listing.ProvenancedMoney (value + provenance wrapper)"
    - "lib.property_listing.PropertyType (4-member Literal)"
    - "lib.property_listing.Provenance (4-member Literal)"
    - "PROP-02 baseline: JSON byte-equal round-trip (full DuckDB round-trip in Plan 13-05)"
  affects:
    - "Plan 13-02 (block detector): parallel-eligible, does not depend on this"
    - "Plan 13-03 (extractor): consumes PropertyListing for Sonnet output validation"
    - "Plan 13-04 (CLI): consumes PropertyListing + ProvenancedMoney in envelope shapes"
    - "Plan 13-05 (persistence): consumes PropertyListing for DuckDB JSON column writes"
    - "Phase 14 (analysis): every analysis function will accept PropertyListing"
tech_stack:
  added:
    - "lib.property_listing module (Pydantic v2 model)"
  patterns:
    - "Reuse lib.models.Money Annotated alias (no re-derived condecimal)"
    - "ConfigDict(strict=True, frozen=True, extra='forbid') mirror of lib/models.py"
    - "field_serializer for datetime Z-suffix normalization (Pitfall 21)"
    - "field_serializer for Decimal-as-string on Decimal-typed fields (D-19)"
    - "field_validator for baths half-step grid"
    - "PEP 604 union syntax (X | None), no typing.Optional"
key_files:
  created:
    - "lib/property_listing.py"
  modified:
    - "tests/test_property_listing.py"
    - "pyproject.toml"
decisions:
  - "Reuse lib.models.Money Annotated alias for the bare price field — single source of truth for money discipline"
  - "ProvenancedMoney wraps NICE-TO-HAVE money fields only; bare price is shape-1-implied-scraped per docstring"
  - "Non-money NICE-TO-HAVEs (beds, baths, sqft, year_built, days_on_market, list_date) use sibling *_provenance Literal, not ProvenancedMoney wrapper (wrappers on non-money would be over-engineering per CONTEXT specifics §3)"
  - "datetime serializer pins Z suffix to match Phase 12 _now_utc convention (Pitfall 21) — avoids '+00:00' vs 'Z' query drift in Plan 13-05 listing_json column"
  - "No Optional[X] — PEP 604 union syntax throughout, matching lib/models.py"
  - "No model_validator cross-field rules — conditional-MUST-HAVE upgrades (HOA-for-condo, tax estimation) deferred to Phase 14 per CONTEXT.md"
metrics:
  duration_minutes: 2
  completed_date: "2026-05-17"
  tasks_completed: 2
  files_changed: 3
  loc_added: 268
---

# Phase 13 Plan 01: Property-Listing Model Summary

One-liner: PROP-01 Pydantic v2 `PropertyListing` + `ProvenancedMoney` wrapper —
mirrors `lib/models.py` shape verbatim (`strict=True, frozen=True, extra="forbid"`),
reuses `lib.models.Money` Annotated alias for the MUST-HAVE `price` field, pins
datetime serialization to the Phase 12 Z-suffix convention, and flips all
Wave-0 xfail markers to 12 live green tests covering money discipline,
half-step baths, frozen-hashability, and byte-equal JSON round-trip.

## What Shipped

### Task 1 — `lib/property_listing.py` (commit `2979748`)

105 LOC. Two classes, two type aliases, two field serializers, one field validator.

**Field summary (20 fields total):**

| Group | Fields | Type / Notes |
|-------|--------|--------------|
| MUST-HAVE (3) | `price`, `zip`, `property_type` | `Money` / `Annotated[str, Field(pattern=r"^\d{5}$")]` / `PropertyType` Literal |
| NICE-TO-HAVE money (4) | `tax_annual`, `hoa_monthly`, `insurance_estimate_annual`, `zestimate` | `ProvenancedMoney \| None = None` |
| NICE-TO-HAVE non-money (6) | `beds`, `baths`, `sqft`, `year_built`, `days_on_market`, `list_date` | `int \| None` / `Decimal \| None` / `date \| None` with bound constraints |
| Sibling provenance (6) | `beds_provenance`, `baths_provenance`, `sqft_provenance`, `year_built_provenance`, `days_on_market_provenance`, `list_date_provenance` | `Provenance \| None = None` |
| Audit (3) | `source_url`, `zpid`, `fetched_at` | `str(min_length=10)` / `Annotated[str, Field(pattern=r"^\d+$")]` / `datetime` |

**Type aliases:**

```python
PropertyType = Literal["SFH", "condo", "townhouse", "multifamily-2-4"]
Provenance = Literal["scraped", "user_provided", "estimated", "unknown"]
```

The 4 `PropertyType` members lock the analysis pipeline schema for Phase 14
(per Wave 0 plan-check); the 4 `Provenance` members are the gap-fill envelope
semantics (scraped / user_provided / estimated / unknown).

**Validators + serializers:**

- `@field_validator("baths")` rejects values not on the 0.5 grid (`(v * 2) % 1 != 0`).
- `@field_serializer("baths")` emits Decimal-as-string per D-19.
- `@field_serializer("fetched_at")` swaps `+00:00` → `Z` per Phase 12 convention.

**`ProvenancedMoney` wrapper:** 2 fields (`value: Money | None`, `provenance: Provenance`)
with the same `ConfigDict(strict=True, frozen=True, extra="forbid")` envelope.

`pyproject.toml`: removed the `[[tool.mypy.overrides]] module = "lib.property_listing"`
ignore_missing_imports entry now that the module exists (per 13-00-SUMMARY hand-off note).

### Task 2 — `tests/test_property_listing.py` (commit `4b5a0d4`)

191 LOC. 12 tests, all green. All 5 Wave-0 `@pytest.mark.xfail(..., strict=True)`
markers removed. Module-level `_make_min_listing(**overrides)` factory keeps
each test focused on the property under assertion.

**Test list:**

| # | Test | Property asserted |
|---|------|-------------------|
| 1 | `test_must_haves_only_validates` | D-13-MUSTHAVE-01: 3-field minimum; all NICE-TO-HAVEs default `None` |
| 2 | `test_round_trip_serialization_money_as_string` | PROP-02 baseline: `"price":"625000.00"` + `"value":"7800.00"` + Z-suffix datetime + byte-equal round-trip |
| 3 | `test_rejects_float_price_strict_true` | strict=True rejects JSON float for Decimal Money |
| 4 | `test_rejects_invalid_zip_and_property_type` | zip regex (4-digit zip rejected) + Literal gate ("Manufactured" rejected) |
| 5 | `test_baths_half_step_validator` | 2.25 → ValidationError; 2.5 → accepts |
| 6 | `test_serialized_baths_is_string_not_float` | `"baths":"2.5"` literal in JSON output |
| 7 | `test_provenanced_money_validates` | `ProvenancedMoney(value, provenance="scraped")` happy path |
| 8 | `test_provenanced_money_rejects_invalid_provenance` | Literal gate on provenance |
| 9 | `test_extra_field_forbidden` | extra="forbid" surfaces typos |
| 10 | `test_frozen_listing_is_hashable` | frozen=True → `hash()` + set membership |
| 11 | `test_fetched_at_z_suffix_not_plus_zero` | Pitfall 21: Z suffix only, `+00:00` absent from JSON |
| 12 | `test_user_provided_provenance_on_tax_annual` | `provenance="user_provided"` survives round-trip |

**Pydantic JSON literal-form note:** Pydantic v2's `model_dump_json()` defaults
to the compact no-whitespace form (`'"price":"625000.00"'`), matching
`tests/test_models.py:103` (`'"principal":"400000.00"'`). The plan's
`<behavior>` block specified the space-after-colon form (`'"price": "625000.00"'`)
— actual library output drove the assertion form. No behavior change; this is
a docstring-fidelity deviation only.

## Round-trip JSON shape (literal snippet)

```json
{
  "price":"625000.00",
  "zip":"94110",
  "property_type":"SFH",
  "tax_annual":{"value":"7800.00","provenance":"scraped"},
  "hoa_monthly":null,
  ...
  "source_url":"https://www.zillow.com/homedetails/x/12345_zpid/",
  "zpid":"12345",
  "fetched_at":"2026-05-10T14:30:00.123456Z"
}
```

(Single-line in the actual `model_dump_json()` output — pretty-printed here
for readability.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Lint hygiene unblocking pre-commit] ruff TC001 on `from lib.models import Money`**

- **Found during:** Task 1 commit attempt (pre-commit ruff hook).
- **Issue:** ruff TC001 demanded `from lib.models import Money` move into a
  `TYPE_CHECKING` block. But `Money` is `Annotated[Decimal, Field(...)]` and
  Pydantic resolves the annotation at runtime to build the field — moving it
  to `TYPE_CHECKING` would break model construction (`NameError: name 'Money'
  is not defined`).
- **Fix:** Added `# noqa: TC001  # Pydantic resolves annotations at runtime`
  comment on the import line, mirroring `lib/models.py:16` which carries the
  identical `# noqa: TC003` pattern for `from datetime import date` for the
  same reason.
- **Files modified:** `lib/property_listing.py` (import-line comment only).
- **Commit:** `2979748` (bundled into Task 1's commit).

### Assertion-form fidelity adjustment (NOT a deviation, but worth flagging)

The plan's `<behavior>` block specified Pydantic JSON assertions in the
space-after-colon form (`'"price": "625000.00"'`). Pydantic v2's default
`model_dump_json()` actually emits the compact no-whitespace form
(`'"price":"625000.00"'`), as verified against `tests/test_models.py:103`
(the established project convention). Tests use the actual library output
form. This is a literal-string-fidelity correction, not a behavior change.

## Authentication Gates

None. PROP-01 is a pure-Pydantic model; no API keys or external services touched.

## Verification

- [x] `lib/property_listing.py` exists; `wc -l` = 105 (≥ 70 required)
- [x] Exactly one `class PropertyListing(BaseModel):` declaration
- [x] Exactly one `class ProvenancedMoney(BaseModel):` declaration
- [x] Both classes carry `ConfigDict(strict=True, frozen=True, extra="forbid")` (2 model_config lines + 1 docstring mention)
- [x] `from lib.models import Money` present; no re-derived `Annotated[Decimal,...]` alias
- [x] `PropertyType = Literal["SFH", "condo", "townhouse", "multifamily-2-4"]` verbatim
- [x] `Provenance = Literal["scraped", "user_provided", "estimated", "unknown"]` verbatim
- [x] `@field_validator("baths")` with half-step check present
- [x] `@field_serializer("fetched_at")` with `.isoformat().replace("+00:00", "Z")` present
- [x] `@field_serializer("baths")` with Decimal-as-string present
- [x] `zip` field has regex `r"^\d{5}$"`; `zpid` has regex `r"^\d+$"`; `source_url` has `min_length=10`
- [x] No `Optional[`, no `condecimal(`, no `from typing import Optional` (PEP 604 only)
- [x] No `Co-Authored-By`, no `Claude`, no AI-attribution strings (CLAUDE.md global rule)
- [x] `uv run python -c "from lib.property_listing import PropertyListing, ProvenancedMoney; print('OK')"` prints `OK`
- [x] `grep -c '@pytest.mark.xfail' tests/test_property_listing.py` returns 0
- [x] `grep -c '^def test_' tests/test_property_listing.py` returns 12 (≥ 10)
- [x] `uv run pytest tests/test_property_listing.py -v` → 12 passed, no xfail, no XPASS, no failed, no error
- [x] No `assertAlmostEqual` anywhere
- [x] `uv run pytest tests/test_models.py tests/test_money.py` → 28 passed (no regression)
- [x] Pre-commit hooks pass (ruff, ruff-format, mypy, DATA_CONTRACT.md guard) on both task commits
- [x] Pre-existing dirty file (`lib/rules/fha_mip.py`) NOT staged; pre-existing untracked files (`.planning/*.md` notes, `data/.lock 2..5`) NOT staged — per executor constraints

## Next: Wave 2 (parallel-eligible) + Wave 3

`/gsd-execute-phase 13` continues with:

- **Plan 13-02 (block detector)** — runs parallel-eligible with this; depends only on Wave 0 (xfail scaffold). Pure stdlib + regex per 13-RESEARCH Example 2. Will close INGEST-04 + D-13-BLOCK-01.
- **Plan 13-03 (extractor)** — depends on PROP-01 shipped here. Sonnet `messages.parse(output_format=PropertyListing)` per Wave-0 probe A outcome. Will close INGEST-02.

The `[[tool.mypy.overrides]]` entry for `lib.property_listing` was removed in
this wave's pyproject.toml edit (per the 13-00-SUMMARY hand-off plan). The
remaining 3 overrides (`lib.property_block_detector`, `lib.property_extractor`,
`lib.property_persistence`) will come off as their respective waves ship.

## Self-Check: PASSED

Verified by direct filesystem + git inspection:

- FOUND: lib/property_listing.py
- FOUND: tests/test_property_listing.py (modified — xfail markers removed; 12 live tests)
- FOUND: pyproject.toml (modified — lib.property_listing mypy override removed)
- FOUND: commit 2979748 (Task 1 — lib/property_listing.py + pyproject.toml)
- FOUND: commit 4b5a0d4 (Task 2 — tests/test_property_listing.py flipped)
- VERIFIED: `uv run pytest tests/test_property_listing.py` → 12 passed
- VERIFIED: `uv run pytest tests/test_models.py tests/test_money.py` → 28 passed (no regression)
