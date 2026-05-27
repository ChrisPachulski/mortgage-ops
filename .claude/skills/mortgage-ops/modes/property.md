# Mode: property — Zillow listing → underwriting workup

Loaded by SKILL.md routing per the dispatch table (Row 0: URL-pin). Read
`modes/_shared.md` FIRST (per D-10), then this file.

## When to invoke

Route here when EITHER trigger fires (D-15-ROUTE-01 — URL-pin is HIGHEST
precedence; overrides every verb including explicit slash-commands):

- (a) user message contains substring `zillow.com`, OR
- (b) user literally typed `analyze listing`.

Examples: "Run the numbers on zillow.com/homedetails/.../12345_zpid/",
"analyze listing https://www.zillow.com/b/12345_zpid/", "Should we offer
on zillow.com/homedetails/.../67890_zpid/?"

Do NOT route here if neither trigger fires (existing precedence applies),
or if the URL is non-Zillow (Redfin / Realtor.com / Trulia) — the WebFetch
extractor below is Zillow-specific; switch to `evaluate` with manual inputs.

**Special case:** "analyze listing" with no URL → ask exactly "Sure — paste
the Zillow URL." Do NOT auto-route to `evaluate` / `compare` / `affordability`.

## Ingestion subroutine

### Step 1 — WebFetch the URL with the extractor prompt

Invoke `WebFetch` against the user-supplied URL with the prompt embedded
verbatim below (Pattern 1 from `.planning/research/v1.1-property-analysis.md`
§"Pattern 1"). The URL MUST come from the user — never construct/mutate
URLs (security policy: WebFetch URLs originate from user input only).

### Pattern 1 `__NEXT_DATA__` extractor prompt (embedded verbatim)

Pass this exact text as `WebFetch`'s `prompt:` argument:

```
Extract structured property data from this Zillow listing. The page
contains a <script id="__NEXT_DATA__"> JSON blob. Find it, parse it,
and return ONLY a JSON object with these fields (use null for missing
values, never invent values):

{
  "zpid": <integer>,
  "address": "<street + city + state + zip>",
  "zip": "<5-digit>",
  "list_price": "<decimal as string, e.g. '789000.00'>",
  "zestimate": "<decimal as string or null>",
  "property_tax_annual": "<decimal as string or null>",
  "hoa_monthly": "<decimal as string or null>",
  "insurance_estimate_annual": "<decimal as string or null>",
  "beds": <number or null>,
  "baths": <number or null>,
  "sqft": <integer or null>,
  "lot_sqft": <integer or null>,
  "year_built": <integer or null>,
  "property_type": "<one of: SingleFamily, Condo, Townhouse,
    Multifamily, Manufactured, Cooperative, Unknown>",
  "days_on_market": <integer or null>,
  "list_date": "<YYYY-MM-DD or null>",
  "county_name": "<string or null>",
  "state_fips": "<2-char string or null>",
  "county_fips": "<3-char string or null>"
}

If you see substrings like "px-captcha", "Press & Hold to confirm",
or "perimeterx", return {"_block_detected": true, "signal_phrase":
"<which matched>"}.

If __NEXT_DATA__ was truncated before you reached it, return
{"_truncated": true}.

Money fields MUST be Decimal-safe JSON strings (Pydantic v2 strict
mode rejects floats). Output ONLY the JSON object, no prose, no fences.
```

### Step 2 — Parse the WebFetch response; check sentinel keys

- `{"_block_detected": true, ...}` → Zillow captcha/PerimeterX. Narrate
  "Zillow served a bot block (`<signal_phrase>`). Paste the listing details
  manually." Switch to manual paste.
- `{"_truncated": true}` → `__NEXT_DATA__` truncated. Narrate "Zillow's
  response was truncated before I could parse the JSON. Paste manually."
- `{"_no_next_data": true}` (or no `zpid`/`list_price` returned) → manual paste.

### Step 3 — Validate via Pydantic round-trip

Build the full `PropertyListing` JSON (`source_url` = user URL;
`fetched_at` = ISO 8601 UTC now; `extraction_method` = `"webfetch"`;
HIGH-tier money fields wrapped as `ProvenancedMoney` with
`provenance: "zillow_scraped"`). Validate:

```bash
python -c "from lib.property_listing import PropertyListing; PropertyListing.model_validate_json(open('/tmp/listing.json').read())"
```

On `ValidationError`, surface the 6-key envelope per `_shared.md` §Error
Narration Template — one plain-English paragraph + one-line fix.

### Step 4 — Interactive gap-fill for MUST-HAVE fields

Per Phase 13 D-13-MUSTHAVE-01, the 3 MUST-HAVEs are `list_price`, `zip`,
`property_type`. If any are null after Step 3, ask ONE question per
missing field (never combine): price → "I couldn't extract the list price.
What's the asking price? (e.g., 789000)"; zip → "What's the 5-digit ZIP?";
property_type → "Property type? (SingleFamily / Condo / Townhouse /
Multifamily / Manufactured / Cooperative / Unknown)". Merge user values
with `provenance: "user_provided"` (audit-trail invariant). HIGH-tier
nulls (`property_tax_annual`, `hoa_monthly`, `insurance_estimate_annual`)
are optional; orchestrator falls back to defaults and surfaces a warning.

### Step 5 — Write the validated listing to a tempfile

Write to `/tmp/listing-{uuid}.json`. Orchestrator copies to a stable sidecar
under `data/property-listings/` for the citation footer.

## Orchestrator dispatch

Run `python .claude/skills/mortgage-ops/scripts/property_analyze.py --help`
first if you have not invoked it this session (CLAUDE.md skill portability:
read `--help` before calling; <300ms D-18 cap).

After WebFetch → gap-fill → tempfile write, invoke:

```bash
python .claude/skills/mortgage-ops/scripts/property_analyze.py \
  --listing /tmp/listing-{uuid}.json \
  --household config/household.yml \
  --profile config/profile.yml \
  --output-dir reports/
```

Parse the stdout JSON envelope:

```json
{"report_path": "reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md",
 "verdict": "GO|WATCH|NO_GO",
 "error": null}
```

On `error != null`, narrate `error.code` + `error.message` per `_shared.md`
§Error Narration Template AND consult Edge cases below.

## Result narration

On success, narrate:

> Saved underwriting report to **{report_path}**.
> Verdict: **{verdict}** — see the file for matrix, stress, refi, points,
> tax, and verdict sections.
> *(Computed by .claude/skills/mortgage-ops/scripts/property_analyze.py at
> {fetched_at}; citations embedded in every section.)*

Do NOT echo matrix / stress / refi numbers — the report file is the
durable artifact (D-15-CITATION-03; re-running the copy-paste reproduces it).

## Edge cases

Orchestrator error codes (one bullet per code):

- `listing_validation_failed` → Pydantic round-trip failed; 6-key envelope
  on stderr names the offending field. Surface plain English; ask user to
  fix or paste manually.
- `household_yaml_invalid` → `config/household.yml` failed validation.
  Point user at `config/household.example.yml`; DO NOT auto-edit (User Layer).
- `profile_yaml_invalid` → same recovery, with `config/profile.example.yml`.
- `fred_cache_cold` → run `python .claude/skills/mortgage-ops/scripts/fred_cli.py
  MORTGAGE30US --latest` (and `MORTGAGE15US --latest` if Conv15 in scope); retry.
- `output_dir_unwritable` → defensive; should never trigger with default
  `--output-dir reports/`. Ask user to inspect `reports/` permissions.
- `missing_county_data` → listing's ZIP absent from
  `data/reference/conforming-limits-2026.yml`; ask user for county + conforming limit.
- `analyze_internal_error` → catch-all; narrate `error.message` verbatim;
  ask for stderr + stdout. Do NOT auto-retry.

Ingestion-side edges: WebFetch 403 / captcha → manual paste (Step 2
sentinel); `_no_next_data` (Zillow A/B-tests the `<script id="__NEXT_DATA__">`
tag away) → manual paste; Pydantic validation fails after gap-fill (e.g.,
user typed `12345-6789` ZIP+4) → 6-key envelope narration; ask for 5-digit form.

## Save Report — SKIPPED in property mode

Unlike `evaluate` / `compare` / `refinance` / `affordability` / `stress` /
`amortize` / `arm` modes (which invoke `node orchestration/db-write.mjs
insert-report` after writing the .md), property mode SKIPS DuckDB
persistence. The orchestrator writes the markdown to `reports/` but does
NOT call `orchestration/db-write.mjs`. DuckDB persistence of
`analyzed_listings` is deferred to v1.2 watchlist (15-CONTEXT §Deferred
Ideas; 15-PATTERNS L933-939; Pitfall 12). Same-day re-runs use `-rN`
filename suffix (D-15-ORCH-04).

## Worked Example

End-to-end flow (mirrors `modes/evaluate.md` worked-example precedent):

1. **User:** "analyze listing https://www.zillow.com/homedetails/123-Main-St/12345_zpid/"
2. **WebFetch** with the `__NEXT_DATA__` extractor returns
   `{"zpid": 12345, "address": "123 Main St, Seattle WA 98101", "zip": "98101",
   "list_price": "789000.00", "property_type": "SingleFamily",
   "property_tax_annual": "6000.00", ...}` (no sentinel keys → real listing).
3. **Pydantic round-trip:** `PropertyListing.model_validate_json(...)` succeeds.
4. **Gap-fill:** `hoa_monthly` null; ask "Is HOA $0 or a specific dollar
   amount?" User replies `$0`; merge `{"value": "0.00", "provenance": "user_provided"}`.
5. **Tempfile write:** `/tmp/listing-a1b2c3d4.json`.
6. **Orchestrator dispatch:** `python .claude/skills/mortgage-ops/scripts/property_analyze.py
   --listing /tmp/listing-a1b2c3d4.json --household config/household.yml
   --profile config/profile.yml --output-dir reports/`.
7. **Stdout envelope:** `{"report_path": "reports/001-property-12345-2026-05-20.md",
   "verdict": "GO", "error": null}`.
8. **Narration:** "Saved underwriting report to **reports/001-property-12345-2026-05-20.md**.
   Verdict: **GO** — see the file for matrix, stress, refi, points, tax,
   and verdict sections. *(Computed by .claude/skills/mortgage-ops/scripts/property_analyze.py
   at 2026-05-20T17:32:11Z; citations embedded in every section.)*"

## RELATED REFERENCES

(Load on demand only — D-09 progressive disclosure.)
- `references/property-analysis.md` — Phase 18 ≥250-line reference doc
- `.planning/research/v1.1-property-analysis.md` — Pattern 1 prompt source; 12 pitfalls; 8 OQs
