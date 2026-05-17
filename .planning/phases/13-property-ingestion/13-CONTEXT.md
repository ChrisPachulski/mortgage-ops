# Phase 13: Property Ingestion — Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn a Zillow URL into a validated `PropertyListing` Pydantic record, persisted to DuckDB. Hybrid pipeline: WebFetch → Sonnet-extracted `__NEXT_DATA__` JSON → fallback to two-step interactive gap-fill when MUST-HAVE fields are missing or Zillow blocks the request. Zero paid-scraper dependency (Apify/Bright-Data deferred to v1.2 if/when WebFetch degrades in real use).

**In scope:** `scripts/property_fetch.py` CLI, `lib/property_listing.py` Pydantic model with `ProvenancedMoney` wrapper, `lib/property_persistence.py` DuckDB writer + lockfile, `analyzed_listings` schema migration, 5 pinned Zillow HTML fixtures, captcha-detection signals, ZPID extraction from both URL patterns.

**Out of scope:** the analysis pipeline (Phase 14), the `property` skill mode (Phase 15), report formatter (Phase 15), reference YAMLs (Phase 16), references doc (Phase 18).

</domain>

<decisions>
## Implementation Decisions

### Gap-fill UX flow

- **D-13-GAPFILL-01:** Two-step envelope. `scripts/property_fetch.py {url}` exits 0 with one of three envelope shapes:
  1. **success** — `{listing: {...full PropertyListing...}, missing: [], error: null}`
  2. **awaiting_user_input** — `{listing: {...partial with nulls...}, missing: ["price", "zip", ...], error: null, awaiting_user_input: true}`
  3. **blocked** — `{listing: null, missing: [], error: "<one of: http_403 | http_429 | captcha_detected | missing_next_data | body_too_short>", awaiting_user_input: false}`

  When shape 2 emits, the `property` mode (Phase 15) prompts the user for each missing field, then re-invokes `scripts/property_fetch.py {url} --user-provided '{"price": "625000", "zip": "94110", "property_type": "SFH"}'`. The CLI merges user-provided values with whatever it extracted, tagging the user values `provenance: user_provided`. CLI never opens an interactive prompt itself — all interaction happens in the Claude conversation layer.

  Tests must cover: (a) Zillow-success → shape 1 envelope; (b) Zillow-success-but-tax-null → shape 2 with `missing: ["tax_annual"]` IF tax_annual is MUST-HAVE (it isn't per D-13-MUSTHAVE-01, so this would fall through to shape 1 with `tax_annual=null, provenance=null`); (c) Zillow-block → shape 3 with appropriate error code; (d) re-invocation with `--user-provided` merges correctly + tags provenance.

### PropertyListing MUST-HAVE field set

- **D-13-MUSTHAVE-01:** MUST-HAVE = `price + zip + property_type` (3 fields). All other PropertyListing fields are NICE-TO-HAVE — default to `None` when scraping fails to extract them, no gap-fill blocker.
  - **Rationale:** maximum tolerance for partial Zillow scrapes. Most NICE-TO-HAVEs can be inferred from reference YAMLs (Phase 16): per-state HOI averages fill missing `insurance_estimate_annual`; price × per-zip property-tax-rate fills missing `tax_annual`; "0 HOA" is a defensible default for SFH (HOA defaults to 0 if missing and property_type=SFH, prompts gap-fill only if property_type=condo and HOA missing).
  - **Conditional MUST-HAVE upgrades** (not blocking Phase 13, but documented for Phase 14 pipeline):
    - If `property_type=condo` AND `hoa_monthly is None` → analysis pipeline (Phase 14) marks the report's HOA line `estimated $X (Phase 16 default)` with a `⚠ verify HOA before offer` note in `## VERDICT`.
    - If `tax_annual is None` → same pattern: estimate from `data/reference/property-tax-rates.yml` keyed by zip, label `estimated`, flag in verdict.
  - Tests must assert: PropertyListing with all 3 MUST-HAVEs + everything else None validates; PropertyListing missing any MUST-HAVE raises `ValidationError`.

### Re-analysis behavior (DuckDB schema)

- **D-13-REANALYSIS-01:** Append history. `analyzed_listings` PK = `(zpid, analyzed_at)` composite; every re-run inserts a new row. Storage cost is trivial at personal scale (rough sizing: 1000 re-runs × ~10KB JSON = 10MB, vs DuckDB file growing past 100MB only after ~10k re-runs).
  - Schema sketch:
    ```sql
    CREATE TABLE IF NOT EXISTS analyzed_listings (
      zpid           VARCHAR NOT NULL,
      analyzed_at    TIMESTAMP NOT NULL,
      source_url     VARCHAR NOT NULL,
      listing_json   JSON NOT NULL,            -- full PropertyListing
      analysis_json  JSON,                     -- AnalysisReport from Phase 14 (NULL on ingest-only runs)
      verdict        VARCHAR,                  -- GO | WATCH | NO_GO | null
      household_hash VARCHAR,                  -- so re-runs after household.yml edits are distinguishable
      schema_version INTEGER NOT NULL DEFAULT 1,
      PRIMARY KEY (zpid, analyzed_at)
    );
    CREATE INDEX IF NOT EXISTS idx_listings_zpid ON analyzed_listings(zpid);
    CREATE INDEX IF NOT EXISTS idx_listings_verdict ON analyzed_listings(verdict);
    CREATE INDEX IF NOT EXISTS idx_listings_analyzed_at ON analyzed_listings(analyzed_at DESC);
    ```
  - Watchlist queries become trivial via the indexes (Phase 14 ships `lib/property_persistence.get_latest_per_zpid()` and `get_history_for_zpid(zpid)`).
  - `analysis_json` is nullable so Phase 13 can write listing rows without waiting on Phase 14's pipeline (clean phase separation).
  - `household_hash` is a stable hash of `(household.yml + profile.yml + FRED cache key)` so re-analyses after a household change are distinguishable in queries.
  - Migration: schema lives in `lib/property_persistence.py:_ensure_schema()` and runs idempotently on first write — no separate migration runner.
  - Lockfile pattern from Phase 9 (`orchestration/lockfile.mjs`) is reused via the Python port shipped in Phase 12's `lib/fred_cache.py:with_cache_lock`. The persistence layer uses the same primitive.

### WebFetch extraction model

- **D-13-MODEL-01:** Sonnet extracts the `__NEXT_DATA__` JSON blob into structured PropertyListing fields. Rationale: Zillow A/B-tests page layouts; the personal-use absolute spend is trivial either way; the cost of a Haiku miss + 2-step gap-fill round trip is more painful than the model price delta. (Cost: ~$0.02 per fetch × ~30 listings/month I might analyze = ~$0.60/mo — negligible.)
  - The Sonnet call happens inside the property-fetch CLI (NOT in the main Claude conversation context) so it doesn't leak the raw HTML into the main thread.
  - Extraction prompt template lives in `scripts/property_fetch.py` as a module-level constant. Pinned in the references doc (Phase 18) so future-me can debug drift.
  - Fallback (if Sonnet returns invalid JSON or fails Pydantic validation): emit shape-2 `awaiting_user_input` envelope listing ALL MUST-HAVE fields. Don't try a Haiku retry — Sonnet-failed-then-Haiku-succeeded is unlikely enough that the complexity isn't worth it.

### Block-signal detection

- **D-13-BLOCK-01:** Four signals; ANY firing triggers shape-3 `blocked` envelope with a specific error code:
  1. **`http_403` / `http_429` / `http_503`** — HTTP status ≠ 200. The CLI never retries automatically; emits the envelope and lets the user decide (try again later, or paste in details manually via `--user-provided`).
  2. **`missing_next_data`** — Response body has no `<script id="__NEXT_DATA__">`. Strong signal of a block page or redirect.
  3. **`captcha_detected`** — Case-insensitive substring match against any of: `"press & hold"`, `"human verification"`, `"px-captcha"`, `"are you a robot"`, `"unusual traffic"`, `"recaptcha"`. Match list lives in a module constant in `scripts/property_fetch.py`, easy to extend.
  4. **`body_too_short`** — `len(body) < 5000` bytes. Real Zillow listings are 200KB+; sub-5KB is almost certainly a block page or 30x redirect chain.
  - Error envelope shape: `{listing: null, error: "<error_code>", missing: [], awaiting_user_input: false, source_url: "<original_url>", fetched_at: "<ISO timestamp>"}`. Stable enough for Phase 14 to react to.
  - Tests must cover each signal independently using pinned fixtures (e.g., `tests/fixtures/zillow/blocked_perimeterx.html`, `tests/fixtures/zillow/blocked_403.json`).

### Claude's Discretion (planner decides during planning)

- Whether to ship `scripts/property_fetch.py` as a single file or split into `scripts/property_fetch.py` (CLI entrypoint + arg parsing) + `lib/property_extractor.py` (Sonnet extraction logic) + `lib/property_block_detector.py` (signal detection). Lean toward split for testability, but planner picks.
- Exact Pydantic field validators (e.g., zip regex, property_type Literal members) — researcher/planner picks based on Zillow's actual data shape.
- Whether to use `anthropic.Anthropic().messages.create(model="claude-sonnet-4-6", ...)` directly inside the CLI, or to spawn a subagent. (Recommendation: direct API call. Subagents are for context isolation in the main conversation; the CLI is its own subprocess context already.)
- Whether the `household_hash` is a content hash (SHA256 of file contents) or a structural hash (only fields that affect analysis). Structural is more robust but more code. Lean content hash for v1.1.

</decisions>

<specifics>
## Specific Ideas

- The CLI must follow Phase 12 D-12-LIVE02-01 verbatim: ALWAYS exit 0, ALWAYS emit JSON envelope on stdout. Argparse parse errors are the one documented exception (exit 2 per Phase 12 WR-02 fix).
- Sonnet extraction prompt should explicitly require: "Output JSON only, no prose. Schema: `{...PropertyListing fields...}`. Use `null` for fields you cannot extract from the markdown. Do not infer or guess — null is better than wrong." Phase 18 documents the full prompt.
- `ProvenancedMoney` wrapper: pydantic v2 model with `value: condecimal` + `provenance: Literal["scraped", "user_provided", "estimated", "unknown"]`. Used for `price`, `tax_annual`, `hoa_monthly`, `insurance_estimate_annual`, `zestimate`. Non-money fields (beds, sqft, zip, property_type, year_built) carry their own `*_provenance: Literal[...]` sibling field rather than being wrapped — wrappers on non-money fields would be over-engineering.
- `analyzed_at` timestamp uses UTC ISO-8601 with microsecond precision so re-runs within the same second don't collide on PK. Mirrors Phase 12 `_now_utc()` pattern.
- Privacy note: `analyzed_listings` is personal data. The DuckDB file lives at `data/mortgage-ops.duckdb` and is already gitignored. The pinned test fixtures (Phase 17) must be from listings I'm willing to ship (or anonymized).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 13 planning artifacts (this milestone)
- `.planning/research/v1.1-property-analysis.md` §Pattern 1 (Zillow HTML extraction) + §Pattern 2 (PropertyListing schema) + §Pattern 5 (DuckDB analyzed_listings) + §10 (12 pitfalls) — the milestone-level research; Phase 13 implements Patterns 1+2+5
- `.planning/REQUIREMENTS.md` INGEST-01..04 + PROP-01..02 + PERS-08 — locked requirements for Phase 13
- `.planning/ROADMAP.md` §Phase 13 SC-1..SC-5 — success criteria

### Project-wide
- `.planning/PROJECT.md` — core value (math correctness, LLM never owns numbers), conventions, sibling-repo patterns
- `CLAUDE.md` §Money discipline + §Calc engine separation + §Skill portability + §Reference data discipline — all apply
- `DATA_CONTRACT.md` — User Layer (config/) is READ-ONLY; Data Layer (data/) is auto-generated and gitignored — `analyzed_listings` is Data Layer

### Patterns to inherit
- `lib/fred_cache.py` (Phase 12) — `with_cache_lock`, `_now_utc()`, schema_version pattern, always-exit-0 envelope discipline
- `lib/rules/_loader.py` (Phase 1+) — YAML reference data loading with staleness check (Phase 16 will use this)
- `orchestration/lockfile.mjs` (Phase 9) — lockfile primitive that `with_cache_lock` mirrors
- `.claude/skills/mortgage-ops/scripts/fred_cli.py` (Phase 12) — exemplar CLI: argparse, always-exit-0 envelope, redacted secrets in source_url, lazy imports
- `.claude/skills/mortgage-ops/scripts/_cli_helpers.py` (Phase 10) — standard CLI boilerplate
- `tests/fixtures/subagent_transcripts/README.md` (Phase 11 D-02) — synthetic-only-in-CI policy; Phase 17 fixtures inherit
- `tests/test_subagents.py` (Phase 11) + `tests/test_evals_runner.py` (Phase 12) — xfail → flip discipline; meta-tests
- `.claude/skills/mortgage-ops/agents/*.md` (Phase 11) — NOT applicable here; Phase 13 ships a CLI, not a subagent

### External docs
- Claude Code WebFetch: https://docs.claude.com/en/docs/agents-and-tools/tool-use/web-fetch-tool — request shape, response truncation, no-JS execution caveat
- Anthropic API reference (Sonnet model): https://docs.claude.com/en/docs/about-claude/models/all-models — for the direct extraction API call
- Zillow `__NEXT_DATA__` schema (informal, no public docs) — see research file Pattern 1 for the empirically-derived field map
- DuckDB JSON column docs: https://duckdb.org/docs/data/json/overview

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib/fred_cache.py:with_cache_lock` (Phase 12) — exact lockfile primitive to wrap DuckDB writes in `lib/property_persistence.py`. 60s stale recovery, JSON-content acquired_at, NOT O_EXCL.
- `lib/fred_cache.py:_now_utc()` (Phase 12) — UTC timestamp helper, freezegun-friendly. Reuse for `analyzed_at`.
- `lib/fred_cache.py:REQUIRED_ENTRY_FIELDS` shape-validation pattern (Phase 12 CR-01 fix) — mirror in `lib/property_persistence.py:_load_listing()` to fall through to refetch on malformed rows.
- `scripts/fred_cli.py:_emit()` (Phase 12) — always-exit-0 JSON envelope emitter; near drop-in for `scripts/property_fetch.py:_emit()`.
- `scripts/_cli_helpers.py` (Phase 10) — argparse boilerplate.
- `tests/fixtures/subagent_transcripts/README.md` (Phase 11) — Phase 17 fixture README inherits this synthetic-only-in-CI policy verbatim.

### Established Patterns
- **Always-exit-0 envelope contract** (Phase 12 D-12-LIVE02-01 + CR-02 outer-try fix) — non-negotiable for any new CLI under `scripts/`. Argparse parse errors get the documented exit-2 exception.
- **Provenance tagging** — Phase 12 introduced `provenance: scraped | user_provided | estimated | static` for eval prompts. Phase 13 extends to PropertyListing money fields via `ProvenancedMoney` wrapper.
- **Two-step Claude↔CLI conversation** — analogous to Phase 11 subagent dispatch but inverted (script asks Claude for help, not Claude asks subagent for compute). New pattern; documented in `references/property-analysis.md` (Phase 18).
- **Xfail → flip test discipline** — Phase 13's Wave 0 stubs go in test files like `tests/test_property_fetch.py`, `tests/test_property_listing.py`, `tests/test_property_persistence.py`; later waves flip them green.

### Integration Points
- **`data/mortgage-ops.duckdb`** (created in Phase 9; gitignored) — `analyzed_listings` table added here via idempotent `_ensure_schema()` in `lib/property_persistence.py`. No migration runner.
- **`.claude/skills/mortgage-ops/scripts/`** — `property_fetch.py` lands here. Same directory as the 7 Phase 10 calc CLIs + Phase 12's `fred_cli.py`.
- **`lib/`** — `property_listing.py`, `property_persistence.py` (and possibly `property_extractor.py` per planner's call) land in the project-root `lib/` directory alongside the other Phase 1-12 modules.
- **`tests/fixtures/zillow/`** (new dir, Phase 17) — pinned HTML snapshots; `tests/test_property_fetch.py` loads them as test inputs.
- **`anthropic` Python SDK** — already added in Phase 11 Wave 0 (`pyproject.toml` `[dependency-groups].dev`). Phase 13 uses it for Sonnet extraction. Need to verify it's NOT dev-only — if `scripts/property_fetch.py` ships to production via the skill, anthropic must be a runtime dep.

</code_context>

<deferred>
## Deferred Ideas

- **Apify / Bright-Data / scraper API fallback** — strict v1.2-only. Ship hybrid WebFetch+gap-fill first; watch for real-world degradation; wire paid path if needed. Captured in `.planning/research/v1.1-property-analysis.md` §Pattern 1 (secondary-path documentation only).
- **Watchlist queries / multi-listing comparison** — Phase 14 ships the `get_history_for_zpid` + `get_latest_per_zpid` helpers but no UI; Phase 15 doesn't expose `list listings` / `compare A B C` commands. Both deferred to v1.2.
- **Saved-search alerts / price-drop notifications** — v1.2+.
- **Tax-record / county-assessor enrichment** — when scraped `tax_annual` is null AND no `property-tax-rates.yml` entry covers the zip, fall back to county assessor APIs. v1.2.
- **Browser-automation fallback (Playwright headless)** — if WebFetch + Apify both degrade, last-resort path. Probably never needed at personal scale. v2.0+.
- **Multi-source ingestion** (Redfin / Realtor.com / FSBO parsers) — locked v1.2 per PROJECT.md.

</deferred>

---

*Phase: 13-property-ingestion*
