# Zillow HTML Fixtures (Phase 13 + Phase 17)

Pinned, sanitized Zillow listing HTML for deterministic INGEST-01..04 +
PROP-01..02 tests. Wave 0 (Plan 13-00) ships this directory + the synthetic-
only-in-CI policy README; Wave 6 (Plan 13-06) drops the first batch of
fixtures into place; Phase 17 expands the corpus with jumbo + multifamily
fixtures.

## Files (Wave 0 state: directory only — Wave 6 / Phase 17 ships fixtures)

| File | Tested SC | Covers |
|------|-----------|--------|
| `sfh_conforming_happy_path.html` | SC-1, INGEST-02 | shape-1 success on SFH all-fields (the happy path) |
| `condo_partial_tax_missing.html` | INGEST-02, INGEST-03 | shape-1 with condo HOA scraped, tax null (gap-fill candidate) |
| `blocked_perimeterx.html` | SC-2, D-13-BLOCK-01 | shape-3 `captcha_detected` ("Press & Hold" PerimeterX-style block page) |
| `extracted/{sha16}.json` | INGEST-02 | Mocked Sonnet outputs, one per HTML fixture, indexed by `sha256(html)[:16]` |

ZPID URL patterns (INGEST-04) are exercised by the parametric test matrix
in `tests/test_property_block_detector.py::test_extract_zpid` — no
dedicated fixture needed for those.

## Why synthetic, not live (D-02 Phase 11 inherits)

Live Zillow scrapes in CI burn ANTHROPIC_API_KEY budget, are non-deterministic
(A/B tests change page layouts), and require network egress that headless
CI runners may not have. Synthetic fixtures give us the four properties we
need:

- **Determinism.** The same HTML always hashes to the same `sha16`, so the
  paired `extracted/{sha16}.json` is a stable mock for `extract_listing`.
  Tests are rerunnable byte-for-byte across machines and runs.
- **Zero recurring cost.** No live `messages.create()` round trip in CI; the
  `mock_sonnet` fixture (added by Wave 3 in `tests/conftest.py`) keys off
  the digest and serves the pre-recorded extraction dict.
- **Airgap-safe.** Tests parse + assert against filesystem fixtures only;
  no network round trip needed for the shape contracts.
- **Contract-is-shape.** What we test is the envelope shape (shape-1
  success / shape-2 awaiting_user_input / shape-3 blocked) and the Pydantic
  `PropertyListing` model invariants, NOT Zillow's verbatim copy. Committing
  hand-authored synthetic HTML that mirrors the canonical `__NEXT_DATA__`
  shape is more useful than committing a one-shot live capture.

See `.planning/phases/13-property-ingestion/13-RESEARCH.md` §"Test Fixture
Strategy" (lines 943-976) for the underlying rationale + `mock_sonnet`
conftest pattern.

## Capture-and-sanitize recipe (HTML-specific)

1. View Source on the live Zillow listing page → Save As `.html`. **Strip**
   `<img>` tags, agent contact info (phone, email, agent bio paragraphs),
   reviewer-visible PII, and any cookie/session identifiers in inline
   scripts.
2. Preserve the `<script id="__NEXT_DATA__">{...}</script>` block verbatim —
   this IS the extraction target. The exact attribute order can vary
   (`id="__NEXT_DATA__" type="application/json"` vs reverse); the regex
   in `lib/property_block_detector.NEXT_DATA_RE` is attribute-order-agnostic
   so don't normalize.
3. Inside `__NEXT_DATA__`, rewrite address fields (`streetAddress`, `city`,
   any reviewer-name fields, agent metadata) to synthetic values. **ZIP
   stays real** — Phase 14 per-zip property-tax-rate lookups need it, and
   the ZIP is not PII on its own.
4. For paired mocked Sonnet outputs:
   `sha16 = hashlib.sha256(html_bytes).hexdigest()[:16]`. Save the expected
   extraction dict at `extracted/{sha16}.json`. The `mock_sonnet` conftest
   fixture (added in Wave 3) keys off this digest. If the HTML changes,
   the `sha16` changes and the paired JSON must be re-generated alongside.

## When to regenerate

- **Quarterly drift check.** Zillow A/B-tests page layouts; a quarterly
  regenerate-and-diff catches silent extraction drift before it bites
  Wave 3's extractor in production.
- **After any change to the Sonnet extraction prompt** in
  `lib/property_extractor.py`. Prompt edits can shift the JSON shape the
  model emits; the paired `extracted/{sha16}.json` must move with it.
- **After any `PropertyListing` schema change** in `lib/property_listing.py`.
  New required fields, new validators, or changed Literal members all
  invalidate the cached extraction dict — regenerate to confirm the
  fixture still validates under the new schema.

## Required `ANTHROPIC_API_KEY` scope

| Action | Needs key? | Allowed in CI? |
|--------|-----------|----------------|
| Load fixture for test | No | Yes |
| Live `extract_listing()` capture | Yes | No (manual only) |
| Regenerate `extracted/{sha16}.json` | Yes | No (manual only) |

`anthropic.messages.count_tokens` is free of content billing (Phase 11
SUBA-06 inheritance), but `messages.create()` / `messages.parse()` IS
billed; nightly drift checks or fixture regenerations should run locally
with a paid-tier key, never in CI.

## What NOT to put here

- **No PII.** No real addresses outside the synthetic ones explicitly
  inserted via the capture-and-sanitize recipe; no agent contact info; no
  `config/household.yml` values; no anything you would not want a stranger
  to read.
- **No AI-attribution trailers.** Per the project-wide CLAUDE.md global
  rule, fixtures and any commit that touches them must remain free of
  attribution markers — no `Co-Authored-By` style annotations, no
  Anthropic credits, no Claude credits in fixture text. This applies to
  the HTML body, the `__NEXT_DATA__` JSON, AND the paired
  `extracted/{sha16}.json` mock outputs.
- **No real Zillow non-public-API responses.** We do not touch their
  non-public API; if a fixture's `__NEXT_DATA__` JSON looks like an
  internal API payload, sanitize down to the public-page surface.
- **No copyrighted listing photos.** Strip all `<img>` tags during
  sanitization; if a fixture needs a photo placeholder, use a synthetic
  `<img src="placeholder.png">` reference, never a real Zillow CDN URL.
