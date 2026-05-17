---
phase: 13
researched: 2026-05-10
status: complete
research_kind: phase-implementation-deep-dive
inherits_from: .planning/research/v1.1-property-analysis.md
overall_confidence: MEDIUM-HIGH
---

# Phase 13: Property Ingestion — Implementation Research

<user_constraints>
## User Constraints (from 13-CONTEXT.md)

### Locked Decisions

- **D-13-GAPFILL-01** — Two-step envelope. `scripts/property_fetch.py {url}` exits 0
  with one of three envelope shapes: `success` / `awaiting_user_input` / `blocked`.
  Re-invocation: `... --user-provided '{...}'` merges user values onto the
  freshly-extracted listing, tagging them `provenance: user_provided`. The CLI
  NEVER opens an interactive prompt — all interaction lives in the Claude
  conversation layer.
- **D-13-MUSTHAVE-01** — MUST-HAVE = `{price, zip, property_type}`. All others
  default to `None` without blocking. Conditional upgrades (condo+missing-HOA,
  missing-tax) are Phase 14 concerns (surface as `estimated` in the report).
- **D-13-REANALYSIS-01** — `analyzed_listings` PK is `(zpid, analyzed_at)` composite.
  Every re-run appends. `analyzed_at` is UTC with **microsecond precision**.
  Schema lives in `lib/property_persistence.py:_ensure_schema()` and runs
  idempotently — no migration runner. `analysis_json` is nullable (Phase 14
  backfills).
- **D-13-MODEL-01** — Sonnet extracts `__NEXT_DATA__`. The call lives INSIDE the
  CLI subprocess (raw HTML never enters the main thread). No retry on failure —
  emit shape-2 listing all MUST-HAVEs.
- **D-13-BLOCK-01** — Four signals → shape-3:
  1. HTTP status ≠ 200 → `http_403` / `http_429` / `http_503` / `http_other`
  2. Missing `<script id="__NEXT_DATA__">` → `missing_next_data`
  3. Captcha substring match (case-insensitive) against `{"press & hold",
     "human verification", "px-captcha", "are you a robot", "unusual traffic",
     "recaptcha"}` → `captcha_detected`
  4. `len(body) < 5000` → `body_too_short`

### Claude's Discretion (researcher recommendations)

- **CLI module split:** SPLIT into `scripts/property_fetch.py` (entrypoint) +
  `lib/property_extractor.py` (Sonnet) + `lib/property_block_detector.py` (signal
  predicates) + `lib/property_persistence.py` (DuckDB). Mirrors Phase 12 split.
- **Direct API call (not subagent):** Direct `anthropic.Anthropic().messages.create(...)`
  inside the CLI; subprocess is already context-isolated.
- **`household_hash` = content hash** SHA256 of `(household.yml + profile.yml +
  MORTGAGE30US cached value)`. Opaque to consumers; v1.2 may swap to structural
  without schema migration.

### Deferred (OUT OF SCOPE)

Apify/Bright Data; watchlist UX; saved-search alerts; county-assessor enrichment;
Playwright; multi-source ingestion. All v1.2+.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGEST-01 | WebFetch + `__NEXT_DATA__`; captcha/403 → structured envelope | §Example 2 (block detection); §Pitfall 1 |
| INGEST-02 | Sonnet pulls canonical fields from `__NEXT_DATA__` | §Example 1 (Sonnet call); §Example 3 (target schema) |
| INGEST-03 | Gap-fill: MUST-HAVE missing → shape-2; merge with `provenance: user_provided` | §Example 5 |
| INGEST-04 | ZPID extraction from `/homedetails/{slug}/{zpid}_zpid/` and `/b/{zpid}_zpid/` | §Example 2 (regex + tests) |
| PROP-01 | `lib/property_listing.py` Pydantic v2: condecimal money, Literal property_type, zip 5-digit, `ProvenancedMoney` wrapper | §Example 3 |
| PROP-02 | Round-trip serialization to DuckDB | §Example 4 |
| PERS-08 | `analyzed_listings` Wave-0 migration; `household_hash` distinguishes re-analyses | §Example 4; §Open Q4 |

</phase_requirements>

## Summary

Phase 13 turns a Zillow URL into a validated `PropertyListing` Pydantic record
persisted to DuckDB. The pipeline is hybrid: parent agent invokes WebFetch →
CLI runs block-detection FIRST against raw body → Sonnet extracts `__NEXT_DATA__`
JSON → on missing MUST-HAVEs, emit `awaiting_user_input` for the conversation
layer to gap-fill → on user re-invocation with `--user-provided`, merge and
re-validate. Three envelope shapes (`success`/`awaiting_user_input`/`blocked`) are
exhaustive; the CLI always exits 0 (per Phase 12 D-12-LIVE02-01); argparse parse
errors are the one documented exit-2 exception.

The milestone research (`.planning/research/v1.1-property-analysis.md`) covers
the architectural shape — what fields live in `PropertyListing`, why
`__NEXT_DATA__` works, why hybrid + gap-fill beats Apify. This file goes
deeper on implementation: which exact `anthropic` SDK call (the 2026
`messages.parse()` API or `messages.create()` fallback), the captcha-detection
+ ZPID regex composition, the `_ensure_schema()` SQL for the `(zpid, analyzed_at)`
composite PK with microsecond precision, and the `--user-provided` merge
semantics with `provenance="user_provided"` tagging.

**Primary recommendation:** SPLIT the implementation across 4 modules
(scripts + 3 lib files) mirroring Phase 12's `fred_cli`/`fred_cache` split.
This isolates the slow/costly Sonnet call from fast/cheap block detection and
unit-testable Pydantic validation. Two new runtime deps required:
`anthropic` (promote from dev), `duckdb` (Python; new). All `[ASSUMED]` claims
are catalogued in the Assumptions Log for user confirmation.

## Architectural Responsibility Map

| Capability | Primary Tier | Rationale |
|------------|-------------|-----------|
| HTML fetch | Parent agent (WebFetch tool) | Per milestone §Pattern 1: WebFetch is zero-dep; Python CLI consumes its output |
| `__NEXT_DATA__` extraction | `lib/property_extractor.py` (Sonnet call) | Per D-13-MODEL-01: raw HTML stays out of main thread |
| Block-signal detection | `lib/property_block_detector.py` (stdlib + regex) | Runs BEFORE Sonnet — cheap to test, no API cost on blocks |
| Pydantic validation | `lib/property_listing.py` | Single schema source; consumed by Phases 14-15 |
| DuckDB persistence | `lib/property_persistence.py` (Python `duckdb`) | `[ASSUMED]` — see §Pitfall 13 + §Open Q3 |
| CLI orchestration | `scripts/property_fetch.py` | Thin entrypoint per Phase 12 `fred_cli.py` shape |

## Project Constraints (from CLAUDE.md)

- **Money discipline:** `Decimal` from strings only; never mix `float` and
  `Decimal`; `condecimal(max_digits=14, decimal_places=2)` at boundaries;
  quantize end-of-period with `ROUND_HALF_UP`.
- **Calc engine separation:** Sonnet extracts (deterministic copy from page),
  never computes. Output round-trips through Pydantic strict validation before
  any downstream touch.
- **Pydantic v2 ≥2.13.3** `[VERIFIED: pyproject.toml line 8]`.
- **Skill portability:** `scripts/property_fetch.py` lives at
  `.claude/skills/mortgage-ops/scripts/` per Phase 10 D-02.
- **No AI attribution** in any commit, comment, doc, or string literal.

## Standard Stack

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `anthropic` | ≥0.100.0,<1.0 | Sonnet extraction call | Currently dev-only → **promote to runtime** |
| `duckdb` (Python) | ≥1.4,<2.0 | `analyzed_listings` writes | **NEW runtime dep** `[ASSUMED]` acceptable; see §Open Q3 |
| `pydantic` | ≥2.13.3 | All listing models | Already runtime `[VERIFIED]` |
| `freezegun` | ≥1.5 (dev) | `fetched_at` test-time pinning | Already dev `[VERIFIED]` |

**NOT used:** BeautifulSoup/lxml (regex on raw HTML is faster + zero-dep);
`requests`/`httpx` (WebFetch is sole network path per D-13-MODEL-01);
`tenacity` retry (no auto-retries in v1.1 per D-13-MODEL-01); Apify/Playwright
(deferred v1.2+).

## Anthropic SDK Runtime Promotion

`[VERIFIED: pyproject.toml line 15]` `anthropic==0.100.0` is currently in
`[dependency-groups].dev` only. Used today by `tests/test_subagents.py` for
token counting. Phase 13 ships `scripts/property_fetch.py` INSIDE the
distributed skill folder — `anthropic` must be runtime-available.

**Exact `pyproject.toml` edit:**

```toml
# BEFORE: lines 6-22
[project]
...
dependencies = [
    "pydantic>=2.13.3",
    "python-dateutil>=2.9.0",
    "numpy-financial==1.0.0",
    "pyyaml>=6.0.2",
]
[dependency-groups]
dev = [
    "anthropic==0.100.0",   # <-- move out
    "freezegun>=1.5",
    ...
]

# AFTER
[project]
...
dependencies = [
    "anthropic>=0.100.0,<1.0",     # <-- runtime promotion
    "duckdb>=1.4,<2.0",            # <-- new for Phase 13 persistence
    "pydantic>=2.13.3",
    "python-dateutil>=2.9.0",
    "numpy-financial==1.0.0",
    "pyyaml>=6.0.2",
]
[dependency-groups]
dev = [
    "freezegun>=1.5",
    ...
]
```

**Side effects:** `uv.lock` regenerates (commit must include delta); CI matrix
unchanged (`anthropic` already installs via `uv sync`); skill now requires
`ANTHROPIC_API_KEY` at execution.

## Code Examples (drop into PLAN.md actions)

### Example 1: Sonnet structured-extraction call

`lib/property_extractor.py` (new).

```python
"""Sonnet-driven __NEXT_DATA__ extraction. Phase 13 D-13-MODEL-01.

Never raises; ALL failure modes return None so the caller emits shape-2
awaiting_user_input per the always-exit-0 contract.
"""
from __future__ import annotations
import json, os, re
from typing import Final

# claude-sonnet-4-6 is the canonical 2026 Sonnet
# [CITED: platform.claude.com/docs/en/build-with-claude/structured-outputs, 2026-05-10]
SONNET_MODEL: Final[str] = "claude-sonnet-4-6"
SONNET_MAX_TOKENS: Final[int] = 4096   # 3-7x headroom over typical 600-1200 token JSON output

EXTRACTION_PROMPT: Final[str] = """\
You are extracting structured property data from a Zillow listing's HTML.
The HTML contains a <script id="__NEXT_DATA__"> tag holding the full property
record as JSON. Find that JSON. Then output a SINGLE JSON object with exactly
these fields:

  zpid               (string, required)
  price              (string, required — Decimal-safe, e.g. "625000.00")
  zip                (string, required — 5 digits)
  property_type      (one of: "SFH", "condo", "townhouse", "multifamily-2-4")
  beds               (integer or null)
  baths              (string Decimal or null — e.g. "2.5")
  sqft               (integer or null)
  year_built         (integer or null)
  tax_annual         (string Decimal or null — annual)
  hoa_monthly        (string Decimal or null — null if no HOA)
  insurance_estimate_annual  (string Decimal or null)
  zestimate          (string Decimal or null)
  days_on_market     (integer or null)
  list_date          (string YYYY-MM-DD or null)

Rules:
  1. Output JSON ONLY. No prose, no fences, no preamble.
  2. Use null for fields you cannot extract. Null is better than wrong.
  3. Money/decimal fields are JSON STRINGS, never numbers (Pydantic strict
     rejects floats for Decimal).
  4. Do not infer or guess. If the page does not state it, the field is null.
  5. property_type maps: SingleFamily/Detached -> "SFH"; Condo -> "condo";
     Townhouse -> "townhouse"; Multifamily/Duplex/Triplex/Fourplex -> "multifamily-2-4".
     Anything else (Manufactured, Cooperative) -> null (gap-fill required).

The HTML follows:

{html}
"""


def extract_listing(html: str, source_url: str) -> dict[str, object] | None:
    """Call Sonnet to extract PropertyListing fields. Returns None on any failure."""
    try:
        import anthropic  # lazy-import per D-18 fast --help

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=SONNET_MAX_TOKENS,
            messages=[{"role": "user",
                       "content": EXTRACTION_PROMPT.format(html=html[:200_000])}],
        )
        if not response.content or response.content[0].type != "text":
            return None
        raw = response.content[0].text
    except Exception:  # noqa: BLE001 — always-exit-0 contract per Phase 12 CR-02
        return None

    # Sonnet sometimes prepends prose despite "JSON ONLY". Extract first {...}.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
```

**Cost estimate** `[CITED: pricepertoken.com/anthropic-claude-sonnet-4.6, 2026-05-10]`:

| Bucket | Tokens | Rate | Per-call |
|---|---|---|---|
| Input (200KB page ≈ 50k tokens) | 50,000 | $3/1M | $0.150 |
| Output (≈ 800 tokens JSON) | 800 | $15/1M | $0.012 |
| **Total** | | | **~$0.16** |

At 30 listings/mo → ~$5/mo. CONTEXT.md's earlier ~$0.02 estimate was Haiku-era;
Sonnet on 200KB is ~8x more expensive. Document in plan.

**Failure-mode map (all → shape-2 `awaiting_user_input` with all MUST-HAVEs missing):**

| Cause | Exception |
|---|---|
| Bad API key | `anthropic.AuthenticationError` |
| Rate limit (429) | `anthropic.RateLimitError` |
| Server overload (529) | `anthropic.APIStatusError` |
| Malformed JSON output | `json.JSONDecodeError` |
| Network timeout | `anthropic.APIConnectionError` |
| Partial extraction (price OK, zip null) | None — Pydantic validates partial |

Shape-3 is reserved for **Zillow-side blocks** (captcha/403); Sonnet-side
failures are recoverable via `--user-provided` re-invocation.

**`messages.parse()` alternative (preferred when available):** The 2026 SDK
adds `client.messages.parse(model=..., output_format=PropertyListing)`
`[CITED: platform.claude.com/docs/en/build-with-claude/structured-outputs]`.
`[ASSUMED]` `anthropic==0.100.0` ships it; Wave 0 verifies. If present, body
collapses to:

```python
response = client.messages.parse(model=SONNET_MODEL, max_tokens=SONNET_MAX_TOKENS,
    output_format=PropertyListing, messages=[{"role":"user","content":prompt}])
return response.parsed_output.model_dump()
```

### Example 2: Block-signal detection + ZPID extraction

`lib/property_block_detector.py` (new). Pure stdlib + regex; no `anthropic` import.

```python
"""Block-signal detection. Phase 13 D-13-BLOCK-01 + INGEST-04."""
from __future__ import annotations
import re
from typing import Final, Literal

BlockError = Literal[
    "http_403", "http_429", "http_503", "http_other",
    "missing_next_data", "captcha_detected", "body_too_short",
]

CAPTCHA_PHRASES: Final[tuple[str, ...]] = (
    "press & hold", "human verification", "px-captcha",
    "are you a robot", "unusual traffic", "recaptcha",
)
MIN_BODY_BYTES: Final[int] = 5000

# Attribute order-agnostic: matches <script id="__NEXT_DATA__"> AND
# <script type="application/json" id="__NEXT_DATA__"> AND uppercase variant
NEXT_DATA_RE: Final[re.Pattern[str]] = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>', re.IGNORECASE,
)

# Supports both /homedetails/{slug}/{zpid}_zpid/ and /b/{zpid}_zpid/
ZPID_RE: Final[re.Pattern[str]] = re.compile(
    r"/(?:homedetails/[^/]+/|b/)(\d+)_zpid/?", re.IGNORECASE,
)


def detect_block(status_code: int, body: str) -> BlockError | None:
    """Return first matching block error or None. Order: status → length → captcha → __NEXT_DATA__."""
    if status_code == 403: return "http_403"
    if status_code == 429: return "http_429"
    if status_code == 503: return "http_503"
    if status_code != 200: return "http_other"
    if len(body) < MIN_BODY_BYTES: return "body_too_short"
    lowered = body.lower()
    if any(p in lowered for p in CAPTCHA_PHRASES): return "captcha_detected"
    if NEXT_DATA_RE.search(body) is None: return "missing_next_data"
    return None


def extract_zpid(url: str) -> str | None:
    """Extract ZPID from Zillow URL. Returns None for non-Zillow / malformed URLs."""
    match = ZPID_RE.search(url)
    return match.group(1) if match else None
```

**ZPID test matrix (target for `tests/test_property_block_detector.py`):**

| URL | Expected |
|---|---|
| `https://www.zillow.com/homedetails/123-Main-SF-CA-94110/12345678_zpid/` | `"12345678"` |
| `https://zillow.com/b/87654321_zpid/` | `"87654321"` |
| `https://zillow.com/.../12345_zpid` (no trailing slash) | `"12345"` |
| `https://zillow.com/.../12345_zpid/?source=email` | `"12345"` |
| `https://zillow.com/.../12345_zpid/#photos` | `"12345"` |
| `http://www.zillow.com/.../12345_zpid/` (http) | `"12345"` |
| `https://redfin.com/property/12345` | `None` |
| `https://zillow.com/homedetails/foo/` (no `_zpid`) | `None` |
| `""` | `None` |

**Why block-detect BEFORE Sonnet:** a 200KB captcha page costs ~$0.10 to Sonnet
for zero data. Detection is microseconds. Saves cost on accidental block-storms.

### Example 3: PropertyListing Pydantic model

`lib/property_listing.py` (new).

```python
"""PropertyListing Pydantic model. Phase 13 PROP-01.
Mirrors lib/models.py shape: strict=True, frozen=True, extra="forbid"."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from lib.models import Money

PropertyType = Literal["SFH", "condo", "townhouse", "multifamily-2-4"]
Provenance = Literal["scraped", "user_provided", "estimated", "unknown"]


class ProvenancedMoney(BaseModel):
    """Money field with attribution. Used for NICE-TO-HAVE money fields.
    `price` is unwrapped Money — shape-1 by definition means price is scraped."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    value: Money | None
    provenance: Provenance


class PropertyListing(BaseModel):
    """Validated Zillow listing. PROP-01."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    # MUST-HAVE
    price: Money
    zip: Annotated[str, Field(pattern=r"^\d{5}$")]
    property_type: PropertyType

    # NICE-TO-HAVE money — ProvenancedMoney wrappers, all default None
    tax_annual: ProvenancedMoney | None = None
    hoa_monthly: ProvenancedMoney | None = None
    insurance_estimate_annual: ProvenancedMoney | None = None
    zestimate: ProvenancedMoney | None = None

    # NICE-TO-HAVE non-money + sibling *_provenance
    beds: int | None = Field(default=None, ge=0, le=20)
    beds_provenance: Provenance | None = None
    baths: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("20"))
    baths_provenance: Provenance | None = None
    sqft: int | None = Field(default=None, gt=0, le=50_000)
    sqft_provenance: Provenance | None = None
    year_built: int | None = Field(default=None, ge=1700, le=2030)
    year_built_provenance: Provenance | None = None
    days_on_market: int | None = Field(default=None, ge=0, le=10_000)
    days_on_market_provenance: Provenance | None = None
    list_date: date | None = None
    list_date_provenance: Provenance | None = None

    # Audit
    source_url: str = Field(min_length=10)
    zpid: Annotated[str, Field(pattern=r"^\d+$")]
    fetched_at: datetime

    @field_validator("baths")
    @classmethod
    def _baths_half_step(cls, v: Decimal | None) -> Decimal | None:
        if v is None: return v
        if (v * 2) % 1 != 0:
            raise ValueError(f"baths must be 0.5 increments; got {v}")
        return v

    @field_serializer("baths")
    def _serialize_baths(self, v: Decimal | None) -> str | None:
        # D-19 money discipline: serialize Decimal as string, not float
        return str(v) if v is not None else None

    @field_serializer("fetched_at")
    def _serialize_dt(self, v: datetime) -> str:
        # Phase 12 _now_utc convention: ISO-8601 with 'Z' suffix (not '+00:00')
        return v.isoformat().replace("+00:00", "Z")
```

**Test pattern (`tests/test_property_listing.py`):**

```python
def test_round_trip_serialization():
    """PROP-02: serialize → JSON → deserialize → byte-equal."""
    listing = PropertyListing(
        price=Decimal("625000.00"), zip="94110", property_type="SFH",
        tax_annual=ProvenancedMoney(value=Decimal("7800.00"), provenance="scraped"),
        source_url="https://www.zillow.com/homedetails/x/12345_zpid/", zpid="12345",
        fetched_at=datetime(2026, 5, 10, 14, 30, 0, 123456, tzinfo=UTC),
    )
    s = listing.model_dump_json()
    assert '"price": "625000.00"' in s   # CRITICAL: money as string
    assert '"value": "7800.00"' in s
    assert PropertyListing.model_validate_json(s) == listing
```

Additional asserts (one test each): 4-digit zip rejection; invalid property_type
("Manufactured") rejection; float-price JSON rejection (Pydantic strict);
baths=2.25 rejection.

### Example 4: DuckDB schema + `_ensure_schema` + idempotent INSERT

`lib/property_persistence.py` (new). Structurally parallel to `lib/fred_cache.py`.

```python
"""DuckDB persistence for analyzed_listings. Phase 13 PROP-02 + PERS-08.
Reuses with_cache_lock from lib.fred_cache (Phase 12 lockfile primitive)."""
from __future__ import annotations
import hashlib, json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

from lib.fred_cache import with_cache_lock

if TYPE_CHECKING:
    from lib.property_listing import PropertyListing

DB_PATH: Final[Path] = Path(__file__).parent.parent / "data" / "mortgage-ops.duckdb"
SCHEMA_VERSION: Final[int] = 1

CREATE_TABLE_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS analyzed_listings (
    zpid            VARCHAR     NOT NULL,
    analyzed_at     TIMESTAMP   NOT NULL,   -- DuckDB default: microsecond precision
    source_url      VARCHAR     NOT NULL,
    listing_json    JSON        NOT NULL,   -- native JSON type per duckdb.org/docs/data/json
    analysis_json   JSON,                   -- nullable; Phase 14 backfills
    verdict         VARCHAR,                -- nullable; GO|WATCH|NO_GO from Phase 14
    household_hash  VARCHAR     NOT NULL,
    schema_version  INTEGER     NOT NULL DEFAULT 1,
    PRIMARY KEY (zpid, analyzed_at)
);
CREATE INDEX IF NOT EXISTS idx_listings_zpid ON analyzed_listings(zpid);
CREATE INDEX IF NOT EXISTS idx_listings_verdict ON analyzed_listings(verdict);
CREATE INDEX IF NOT EXISTS idx_listings_analyzed_at ON analyzed_listings(analyzed_at DESC);
"""


def _now_utc() -> datetime:
    """Microsecond-precision UTC. freezegun-friendly. Mirrors lib.fred_cache._now_utc."""
    return datetime.now(UTC)


def compute_household_hash(
    household_yml: Path, profile_yml: Path, mortgage30us_value: str,
) -> str:
    """D-13-REANALYSIS-01: content hash of the 3 inputs that affect verdict."""
    h = hashlib.sha256()
    h.update(household_yml.read_bytes())
    h.update(profile_yml.read_bytes())
    h.update(mortgage30us_value.encode("utf-8"))
    return h.hexdigest()


def _ensure_schema(con) -> None:
    """Idempotent DDL. Runs on every write; IF NOT EXISTS makes it a no-op after first call.
    No migration runner — v1.2 column changes write _migrate_v2() + bump SCHEMA_VERSION."""
    con.execute(CREATE_TABLE_SQL)


def write_listing(
    listing: PropertyListing, household_hash: str, db_path: Path = DB_PATH,
) -> None:
    """PROP-02. Wrapped in with_cache_lock (cross-process serialization)."""
    import duckdb  # lazy-import per D-18

    with with_cache_lock(db_path.parent, reason=f"write zpid={listing.zpid}"):
        con = duckdb.connect(str(db_path))
        try:
            _ensure_schema(con)
            con.execute(
                """INSERT INTO analyzed_listings
                   (zpid, analyzed_at, source_url, listing_json,
                    analysis_json, verdict, household_hash, schema_version)
                   VALUES (?, ?, ?, ?, NULL, NULL, ?, ?)""",
                [listing.zpid, _now_utc(), listing.source_url,
                 listing.model_dump_json(), household_hash, SCHEMA_VERSION],
            )
        finally:
            con.close()


def read_latest_for_zpid(zpid: str, db_path: Path = DB_PATH) -> PropertyListing | None:
    """Read most recent listing for zpid; None if zpid unknown OR table doesn't exist."""
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        row = con.execute(
            "SELECT listing_json FROM analyzed_listings WHERE zpid = ? "
            "ORDER BY analyzed_at DESC LIMIT 1", [zpid],
        ).fetchone()
    except duckdb.CatalogException:
        return None   # §Pitfall 14: read-only conn can't run DDL; treat missing-table as no-rows
    finally:
        con.close()
    if row is None: return None
    try:
        from lib.property_listing import PropertyListing
        return PropertyListing.model_validate_json(row[0])
    except Exception:  # noqa: BLE001 — defensive, mirrors fred_cache CR-01
        return None
```

**Round-trip test:**

```python
def test_composite_pk_allows_reanalysis(tmp_path):
    """D-13-REANALYSIS-01: same zpid, different analyzed_at → both rows persist."""
    db_path = tmp_path / "test.duckdb"
    listing = PropertyListing(...)
    with freezegun.freeze_time("2026-05-10T14:30:00.123456Z"):
        write_listing(listing, household_hash="abc", db_path=db_path)
    with freezegun.freeze_time("2026-05-10T14:30:00.123457Z"):   # +1µs
        write_listing(listing, household_hash="def", db_path=db_path)
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM analyzed_listings WHERE zpid='12345'").fetchone()[0]
    assert n == 2
```

**Key schema notes:**
- JSON column type chosen over VARCHAR `[VERIFIED: duckdb.org/docs/current/data/json/overview]`:
  enables `listing_json->>'price'` operators in Phase 14 queries; cost is bytes-equivalent.
- TIMESTAMP default is microsecond `[VERIFIED: duckdb.org/docs/current/sql/data_types/timestamp]`.
- Composite PK syntax `[VERIFIED: duckdb.org/docs/current/sql/statements/create_table]`.

### Example 5: Two-step envelope + `--user-provided` merge

`scripts/property_fetch.py` (new). Mirrors `scripts/fred_cli.py` Phase 12 shape:
argparse → lazy-import → always-exit-0 envelope.

```python
#!/usr/bin/env python3
"""scripts/property_fetch.py — Zillow URL → PropertyListing envelope.
Phase 13 INGEST-01..04 + D-13-GAPFILL-01 + D-13-BLOCK-01.

Envelope contract (single-line JSON on stdout, ALWAYS exit 0):

  shape-1 success:    {listing: {...}, missing: [], error: null,
                       awaiting_user_input: false, source_url, fetched_at}
  shape-2 awaiting:   {listing: {...partial...}, missing: ["price","zip"],
                       error: null, awaiting_user_input: true, source_url, fetched_at}
  shape-3 blocked:    {listing: null, missing: [],
                       error: "http_403"|"captcha_detected"|..., 
                       awaiting_user_input: false, source_url, fetched_at}

Usage:
  property_fetch.py <url>                                  # initial
  property_fetch.py <url> --user-provided '{"price":"625000","zip":"94110","property_type":"SFH"}'
  property_fetch.py <url> --html-from <path>               # test fixture loader
"""
from __future__ import annotations
import argparse, json, sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MUST_HAVE = ("price", "zip", "property_type")


def main() -> int:
    parser = argparse.ArgumentParser(prog="property_fetch")
    parser.add_argument("url")
    parser.add_argument("--user-provided", type=str, default=None,
                        help="JSON dict of user-supplied field values (gap-fill round 2)")
    parser.add_argument("--html-from", type=Path, default=None,
                        help="Read HTML from local file (test path)")
    args = parser.parse_args()

    # sys.path injection (parents[4] = project root) per fred_cli.py idiom
    _root = str(Path(__file__).resolve().parents[4])
    if _root not in sys.path:
        sys.path.insert(0, _root)

    # Lazy imports per D-18
    from lib.property_block_detector import detect_block, extract_zpid
    from lib.property_extractor import extract_listing
    from lib.property_listing import PropertyListing
    from lib.property_persistence import write_listing, compute_household_hash

    fetched_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _emit(env: dict[str, Any]) -> int:
        print(json.dumps(env))
        return 0

    # HTML acquisition: --html-from fixture, or stdin from parent agent's WebFetch.
    # CLI itself NEVER fetches via requests/httpx — D-13-MODEL-01.
    if args.html_from is not None:
        body = args.html_from.read_text(encoding="utf-8", errors="replace")
        status_code = 200
    else:
        body = sys.stdin.read()
        status_code = 200  # parent passes only on success; non-200 envelope-routed upstream

    # 1. Block detection (BEFORE Sonnet — saves ~$0.10/blocked-page)
    block_err = detect_block(status_code, body)
    if block_err is not None:
        return _emit({"listing": None, "missing": [], "error": block_err,
                      "awaiting_user_input": False, "source_url": args.url,
                      "fetched_at": fetched_at})

    zpid = extract_zpid(args.url)
    if zpid is None:
        return _emit({"listing": None, "missing": [], "error": "zpid_extraction_failed",
                      "awaiting_user_input": False, "source_url": args.url,
                      "fetched_at": fetched_at})

    # 2. Sonnet extraction
    extracted = extract_listing(body, args.url)
    if extracted is None:
        return _emit({"listing": None, "missing": list(MUST_HAVE), "error": None,
                      "awaiting_user_input": True, "source_url": args.url,
                      "fetched_at": fetched_at})

    # 3. Defensive money-coercion (§Pitfall 15): Sonnet occasionally emits floats
    extracted = _coerce_money_to_string(extracted)

    # 4. Merge --user-provided values (D-13-GAPFILL-01); tag provenance
    if args.user_provided:
        extracted = _merge_user_provided(extracted, json.loads(args.user_provided))

    # 5. Add audit fields
    extracted["source_url"] = args.url
    extracted["zpid"] = zpid
    extracted["fetched_at"] = fetched_at

    # 6. Validate; shape-2 on validation failure with computed missing set
    try:
        listing = PropertyListing.model_validate(extracted)
    except Exception:  # noqa: BLE001
        missing = [f for f in MUST_HAVE if not extracted.get(f)]
        partial = {k: v for k, v in extracted.items() if k in MUST_HAVE}
        return _emit({"listing": partial, "missing": missing or list(MUST_HAVE),
                      "error": None, "awaiting_user_input": True,
                      "source_url": args.url, "fetched_at": fetched_at})

    # 7. Persist (best-effort; never blocks the envelope emission)
    try:
        from lib.fred_cache import get_cached_or_fetch
        mort_value = get_cached_or_fetch("MORTGAGE30US")["value"]
        h = compute_household_hash(Path("config/household.yml"),
                                    Path("config/profile.yml"), mort_value)
        write_listing(listing, household_hash=h)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"persistence warning: {exc!r}\n")

    return _emit({"listing": json.loads(listing.model_dump_json()),
                  "missing": [], "error": None, "awaiting_user_input": False,
                  "source_url": args.url, "fetched_at": fetched_at})


MONEY_FIELDS = {"price", "tax_annual", "hoa_monthly", "insurance_estimate_annual", "zestimate"}


def _coerce_money_to_string(d: dict[str, object]) -> dict[str, object]:
    """§Pitfall 15: Sonnet occasionally emits floats despite 'JSON STRINGS' instruction.
    Pydantic strict=True rejects JSON numbers for Decimal. Coerce at the boundary."""
    for k, v in list(d.items()):
        if k in MONEY_FIELDS and isinstance(v, (int, float)):
            d[k] = f"{v:.2f}"
        elif k in MONEY_FIELDS and isinstance(v, dict) and "value" in v:
            inner = v["value"]
            if isinstance(inner, (int, float)):
                v["value"] = f"{inner:.2f}"
    return d


def _merge_user_provided(extracted: dict[str, object], user: dict[str, object]) -> dict[str, object]:
    """Overlay user values; tag provenance: user_provided. INGEST-03."""
    for field, value in user.items():
        if field in {"tax_annual", "hoa_monthly", "insurance_estimate_annual", "zestimate"}:
            extracted[field] = {"value": _strip_money(str(value)),
                                "provenance": "user_provided"}
        elif field == "price":
            extracted["price"] = _strip_money(str(value))
        elif field in {"beds", "sqft", "year_built", "days_on_market"}:
            extracted[field] = int(value) if value else None
            extracted[f"{field}_provenance"] = "user_provided"
        elif field == "baths":
            extracted["baths"] = str(value) if value else None
            extracted["baths_provenance"] = "user_provided"
        else:   # zip, property_type, list_date — plain overlay
            extracted[field] = value
    return extracted


def _strip_money(raw: str) -> str:
    """§Pitfall 16: users type '$625,000' not '625000.00'. Strip $ and , and pad to .00."""
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if "." not in cleaned:
        cleaned += ".00"
    return cleaned


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise   # argparse parse errors (exit 2) — the one documented non-zero exit
    except Exception as exc:  # noqa: BLE001 — Phase 12 CR-02 outer-try contract
        print(json.dumps({
            "listing": None, "missing": [],
            "error": f"unexpected_failure: {exc!r}", "awaiting_user_input": False,
            "source_url": "<unknown>",
            "fetched_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }))
        sys.exit(0)
```

**Required tests (`tests/test_property_fetch.py`):**
1. Shape-1 happy path (mocked Sonnet, SFH fixture)
2. Shape-2 missing-zip path (mocked Sonnet returns price+property_type only)
3. Shape-3 captcha block (`tests/fixtures/zillow/blocked_perimeterx.html`)
4. Shape-3 body-too-short (synthetic 1KB body)
5. Shape-3 zpid-extraction-failed (non-Zillow URL)
6. `--user-provided '{"price":"$625,000"}'` strips $ and , → "625000.00"
7. `--user-provided` tags `provenance: user_provided` on overlaid money fields
8. Re-invocation idempotency (same args twice → same envelope mod `fetched_at`)
9. Argparse parse error → exit 2 (documented exception to always-exit-0)
10. Unexpected exception during merge → outer try catches → exit 0 + envelope

## Pitfalls (Phase-13-specific — extend milestone §10)

### Pitfall 13: Python `duckdb` is NOT currently a runtime dep

`[VERIFIED: pyproject.toml + grep import duckdb]` no Python code imports
`duckdb` today. All DuckDB I/O is via Node `orchestration/db-write.mjs`
(`duckdb-async`). CONTEXT.md says `lib/property_persistence.py` writes via
`with_cache_lock` — needs either Python `duckdb` (recommended) or subprocess
shell-out to Node (slow). **Mitigation:** add `duckdb>=1.4,<2.0` to runtime
deps alongside the `anthropic` promotion. `[ASSUMED]` Python `duckdb` coexists
safely with Node `duckdb-async` on the same `.duckdb` file via DuckDB's WAL
serialization; both processes use `with_cache_lock` so writes serialize. See
§Open Q3.

### Pitfall 14: read-only DuckDB conn cannot run `_ensure_schema()`

DuckDB rejects DDL inside `connect(read_only=True)`. Calling `_ensure_schema()`
in `read_latest_for_zpid` raises. **Mitigation:** writers ensure schema;
readers catch `duckdb.CatalogException` for the first-call-on-empty-db case
and return None (equivalent to "no rows yet"). Pattern shown in §Example 4.

### Pitfall 15: Sonnet emits `"price": 625000.0` (JSON float) ~5% of the time

Pydantic v2 `strict=True` rejects JSON numbers for Decimal fields. Whole
envelope falls through to shape-2 even though the value is right there.
**Mitigation:** `_coerce_money_to_string()` walks the dict before Pydantic
validation, str-formatting any money-named field whose value is int/float
(see §Example 5). Use `f"{v:.2f}"` (str format) NOT `Decimal(v)` (forbidden
float-to-Decimal per CLAUDE.md).

### Pitfall 16: `--user-provided '{"price":"$625,000"}'` shell escaping

Users type `$625,000` not `625000.00`. Comma + dollar break Pydantic's
Decimal-from-string parsing. **Mitigation:** `_strip_money()` strips `$`,
`,`, whitespace; pads `.00` if no decimal point (§Example 5). Test cases:
`"$625,000"` → `"625000.00"`; `"625000"` → `"625000.00"`; `"  625000.50  "` →
`"625000.50"`; `""` → ValueError (let Pydantic reject empty).

### Pitfall 17: ZPID recycling across years

Zillow occasionally re-uses ZPIDs when listings get relisted months/years
later. The `(zpid, analyzed_at)` composite PK catches same-property
re-analysis, but TWO-different-properties-same-ZPID corrupts watchlist queries.
**Mitigation v1.1 (lean):** document the risk; don't fix. Personal-scale
probability ~0.1%/yr `[ASSUMED]`. **v1.2:** add `address_hash` column; filter
at read time. Out of scope for Phase 13.

### Pitfall 18: Sonnet prepends prose despite "JSON ONLY"

"Here is the extracted data:\n\n{...}" instead of bare `{...}`. Plain
`json.loads` fails. **Mitigation:** `re.search(r"\{.*\}", raw, re.DOTALL)`
before parsing (§Example 1). For higher robustness, a brace-balance walker:

```python
def _extract_first_json_object(raw: str) -> str | None:
    depth, start = 0, -1
    for i, ch in enumerate(raw):
        if ch == "{":
            if depth == 0: start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0: return raw[start : i + 1]
    return None
```

### Pitfall 19: `<script id="__NEXT_DATA__">` attribute order varies

Zillow sometimes ships `id="__NEXT_DATA__" type="application/json"`, sometimes
the reverse. **Mitigation:** `r'<script[^>]*id="__NEXT_DATA__"[^>]*>'` is
order-agnostic (§Example 2). Already in `NEXT_DATA_RE`.

### Pitfall 20: WebFetch `max_content_tokens` may truncate `__NEXT_DATA__`

`[CITED: platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool]`
WebFetch caps content at `max_content_tokens` (default 100k tokens, approximate).
A 400KB Zillow page (with verbose agent bios + photo metadata) can exceed this
and truncate `__NEXT_DATA__` off the end. **Mitigation:** parent agent
explicitly sets `max_content_tokens: 100000` in WebFetch invocation (codify in
Phase 18 `modes/property.md` template). Optional: when
`detect_block`→`missing_next_data` AND `len(body)>90_000`, return
`missing_next_data_likely_truncated` for clearer error semantics.

### Pitfall 21: `datetime` serialization drift (`Z` vs `+00:00`)

Pydantic v2 default serializes `datetime` as ISO-8601 with `+00:00`. Phase 12
cache uses `Z` suffix. Mixed forms in the same `listing_json` column break
`WHERE listing_json->>'fetched_at' = '2026-05-10T14:30:00Z'` queries.
**Mitigation:** explicit `field_serializer` on `PropertyListing.fetched_at`
pinning to `.isoformat().replace("+00:00", "Z")` (already in §Example 3).
DuckDB-native `analyzed_at` column doesn't need this (DuckDB handles tz).

## Open Questions (planner picks; defaults recommended)

### Q1: How does HTML get from WebFetch to the CLI subprocess?

Three options:
1. Argv temp-file path (`--html-from /tmp/property-XYZ.html`)
2. Stdin pipe
3. Skill-side cache file (`data/cache/property-{zpid}.html`)

**Recommendation:** Option 3 (cache file) so `--user-provided` round-trips
skip re-Sonnet on the same HTML. Cache file is gitignored per DATA_CONTRACT.md
Data Layer. CLI prefers cache file if exists, falls back to stdin/argv on
first invocation. The CLI itself never invokes WebFetch — that lives in the
parent agent per D-13-MODEL-01.

### Q2: `messages.create()` vs `messages.parse()` (SDK output_format API)

The 2026 SDK adds `client.messages.parse(output_format=PydanticModel)`
`[CITED: platform.claude.com/docs/en/build-with-claude/structured-outputs]`.
`[ASSUMED]` `anthropic==0.100.0` ships it; verify in Wave 0.

**Recommendation:** Wave-0 task probes `'parse' in dir(client.messages)`. If
True, use parse() pattern (~5% fewer LOC, no regex extraction). If False,
fall back to `messages.create()` + regex (§Example 1 default).

### Q3: Python `duckdb` runtime dep OR subprocess-Node-wrapper?

Either path satisfies CONTEXT.md, but only one is cheap.

| Option | Speed | New deps | Risk |
|---|---|---|---|
| Python `duckdb` | same-process | +1 runtime dep | Dual-language schema drift over time |
| Subprocess Node | +200ms/write | none | Slow; `node` must be on PATH |

**Recommendation:** Python `duckdb`. Phase 9's "Node owns DuckDB" rule predates
the Python lockfile port (Phase 12); now that `with_cache_lock` is in Python,
"writes go through the lock" is the load-bearing constraint, not "writes go
through Node." Wave-0 still extends `cmdInsertAnalyzedListing` in
`db-write.mjs` (Phase 14/15 may need it from Node-side rendering).

### Q4: `household_hash` — content hash or structural hash?

**Recommendation:** Content hash (SHA256 of `household.yml + profile.yml +
MORTGAGE30US value`) for v1.1. Simpler; whitespace-flip risk is benign
(extra row in append-only table). Structural hash needs Phase 14 to declare
which fields it consumes — circular dep at planning time. v1.2 may swap;
`household_hash` is opaque to consumers, so no migration needed.

## Test Fixture Strategy (Phase 13 minimum; Phase 17 finishes)

```
tests/fixtures/zillow/
├── sfh_conforming_happy_path.html   # SFH all-fields → shape-1
├── condo_partial_tax_missing.html   # condo HOA scrapable, tax null → shape-1
├── blocked_perimeterx.html          # "Press & Hold" → shape-3 captcha_detected
├── extracted/<sha16>.json           # pre-recorded Sonnet outputs (CI mock)
└── README.md                        # capture+sanitize recipe
```

**Sanitization recipe (README.md skeleton):**

1. View Source → Save As `.html`. Strip `<img>` tags, agent bios, PII contact info.
2. Preserve `<script id="__NEXT_DATA__">{...}</script>` verbatim — that's the target.
3. Rewrite address fields inside `__NEXT_DATA__` to synthetic values. ZIP stays real
   (Phase 14's per-zip tax lookups need it).
4. For mocked Sonnet outputs: compute `sha16 = hashlib.sha256(html_bytes).hexdigest()[:16]`,
   save the expected extraction dict at `extracted/{sha16}.json`.

**CI mock pattern (`tests/conftest.py`):**

```python
@pytest.fixture
def mock_sonnet(monkeypatch):
    def _fake(html: str, source_url: str) -> dict | None:
        digest = hashlib.sha256(html.encode()).hexdigest()[:16]
        f = Path(f"tests/fixtures/zillow/extracted/{digest}.json")
        return json.loads(f.read_text()) if f.exists() else None
    monkeypatch.setattr("lib.property_extractor.extract_listing", _fake)
```

CI never calls live Sonnet (per Phase 12 D-12-LIVE01-* synthetic-only-in-CI
inherited). Phase 17 expands with 2 more fixtures (jumbo, multifamily-2unit).

## Validation Architecture

| Property | Value |
|----------|-------|
| Framework | pytest ≥9.0 (existing) |
| Quick run | `uv run pytest tests/test_property_*.py -x` (~5s) |
| Full suite | `uv run pytest -x` (~30s) |
| Phase gate | Full suite green before `/gsd-verify-work` |

**Requirements → tests map:**

| Req ID | Test | File (Wave 0 creates) |
|--------|------|---------------------|
| INGEST-01 | `test_shape_3_captcha_block` | `tests/test_property_fetch.py` |
| INGEST-02 | `test_extract_listing_*` | `tests/test_property_extractor.py` |
| INGEST-03 | `test_user_provided_merges_with_provenance_tag` | `tests/test_property_fetch.py` |
| INGEST-04 | `test_zpid_extraction[*]` (parametrized) | `tests/test_property_block_detector.py` |
| PROP-01 | `test_round_trip_serialization` + validator tests | `tests/test_property_listing.py` |
| PROP-02 | `test_round_trip_write_read` | `tests/test_property_persistence.py` |
| PERS-08 | `test_composite_pk_allows_reanalysis` | `tests/test_property_persistence.py` |

**Wave 0 gaps:**

- [ ] `tests/test_property_listing.py` — PROP-01
- [ ] `tests/test_property_block_detector.py` — INGEST-04 + D-13-BLOCK-01 (4 signals × edge cases)
- [ ] `tests/test_property_extractor.py` — INGEST-02 (mocked Sonnet)
- [ ] `tests/test_property_fetch.py` — INGEST-01 + INGEST-03 (CLI envelopes)
- [ ] `tests/test_property_persistence.py` — PROP-02 + PERS-08
- [ ] `tests/fixtures/zillow/` — 3 HTML fixtures + `extracted/` mock outputs
- [ ] `pyproject.toml` — promote `anthropic` to `[project].dependencies`; add `duckdb>=1.4,<2.0`
- [ ] `uv.lock` regenerate after pyproject edit
- [ ] Wave-0 probe: `python -c "import anthropic; print('parse' in dir(anthropic.Anthropic().messages))"`
- [ ] Wave-0 probe: `python -c "import duckdb; print(duckdb.__version__)"`

## Security Domain

| ASVS | Applies | Control |
|------|---------|---------|
| V2 Auth | yes | `ANTHROPIC_API_KEY` env var only; never str-interpolated into outputs (mirror `fred_cli.py` redaction) |
| V5 Input Validation | yes | Pydantic `strict=True, extra="forbid"`; URL regex in `extract_zpid`; argparse parse-validation |
| V6 Crypto | yes | `hashlib.sha256` for `household_hash` — stdlib, never hand-roll |

**Threat patterns:**

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| API key in logs or `source_url` | Info Disclosure | Mirror `fred_cli.py` — never str-interpolate `ANTHROPIC_API_KEY`; SDK handles auth header |
| Malicious URL (`file:///`, internal host) | Tampering | `extract_zpid` returns None for non-Zillow → shape-3 envelope |
| `--user-provided` extra fields | Tampering | Pydantic `extra="forbid"`; explicit allowlist in `_merge_user_provided` |
| Untrusted Sonnet output | Tampering | Output parsed as JSON only; never executed; Pydantic strict is the gate |
| SQL injection via listing fields | Tampering | Parameterized `con.execute(sql, [params])`; never str-interpolate |
| Aggressive retry storms after block | Repudiation | No retries in v1.1 per D-13-MODEL-01; block envelope forces manual intervention |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `anthropic==0.100.0` has `messages.parse(output_format=...)` | §Ex 1, §Q2 | Fall back to `create()` + regex (already coded); zero rework |
| A2 | Python `duckdb` co-exists safely with Node `duckdb-async` on same `.duckdb` | §Ex 4, §Pitfall 13, §Q3 | Fall back to subprocess Node-wrapper; +200ms/write |
| A3 | Zillow ZPID recycling ≤0.1%/year | §Pitfall 17 | Watchlist v1.2 shows wrong cross-property rows; add `address_hash` in v1.2 |
| A4 | WebFetch default `max_content_tokens=100000` is enough for 200KB Zillow | §Pitfall 20 | Explicit cap in Phase 18 `modes/property.md` |
| A5 | Sonnet 4.6 pricing is $3 input / $15 output per 1M tokens, May 2026 | §Ex 1 cost table | Update plan + references doc |
| A6 | Sonnet emits non-JSON prefix ~5% of the time | §Pitfall 18 | Mitigation handles either rate; affects shape-2 false-positive rate only |
| A7 | SDK exceptions remain `AuthenticationError` / `RateLimitError` / `APIStatusError` in 0.100.0 | §Ex 1 | Catch-all `except Exception` preserves always-exit-0; minor refactor if renamed |

## Environment Availability

| Dep | Required By | Available | Fallback |
|-----|------------|-----------|----------|
| `anthropic` SDK | `lib/property_extractor.py` | ✓ dev → promote runtime | None |
| `duckdb` Python | `lib/property_persistence.py` | ✗ | Subprocess Node (§Q3) |
| `pydantic>=2.13.3` | `lib/property_listing.py` | ✓ | None |
| `freezegun` | tests | ✓ dev | None |
| `ANTHROPIC_API_KEY` env | Sonnet call | runtime | Shape-2 with error context |
| WebFetch tool | Parent agent | runtime | None — agent-level block |
| `data/mortgage-ops.duckdb` | Persistence | ✓ (Phase 9) | Wave 0 creates if missing |

## References

### Primary (HIGH confidence)

- `.planning/phases/13-property-ingestion/13-CONTEXT.md` — locked decisions
- `.planning/research/v1.1-property-analysis.md` — milestone patterns (§Pattern 1, 2, 5; §10 pitfalls)
- `.planning/REQUIREMENTS.md` — INGEST-01..04 + PROP-01..02 + PERS-08
- `.planning/ROADMAP.md` — Phase 13 SC-1..SC-5
- `lib/fred_cache.py` — Phase 12 analog (lockfile, schema_version, always-exit-0)
- `lib/models.py` + `lib/money.py` — Money type + Decimal discipline
- `.claude/skills/mortgage-ops/scripts/fred_cli.py` — exemplar CLI shape
- `pyproject.toml` — current dependency state
- `orchestration/lockfile.mjs` + `orchestration/db-write.mjs` — Node-side patterns
- `tests/test_fred_cache.py` + `tests/test_fred_cli.py` — analog test patterns
- `CLAUDE.md` + `DATA_CONTRACT.md` — money discipline + layer membership

### Secondary (MEDIUM confidence — cross-verified)

- [Anthropic structured outputs docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — `messages.parse()`, `output_format`, supported models
- [Anthropic Web Fetch tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool) — `max_content_tokens`, error codes, no-JS caveat
- [DuckDB JSON column](https://duckdb.org/docs/current/data/json/overview) — native JSON type vs VARCHAR
- [DuckDB Timestamp types](https://duckdb.org/docs/current/sql/data_types/timestamp) — microsecond default
- [DuckDB CREATE TABLE](https://duckdb.org/docs/current/sql/statements/create_table) — composite PK syntax
- [Sonnet 4.6 pricing](https://pricepertoken.com/pricing-page/model/anthropic-claude-sonnet-4.6) — $3/$15 per 1M

### Tertiary (LOW confidence — flagged Wave 0 probes)

- `[ASSUMED]` `anthropic==0.100.0` ships `messages.parse()` — verify via `dir(client.messages)`
- `[ASSUMED]` Python `duckdb` coexists safely with Node `duckdb-async` on same `.duckdb`
- `[ASSUMED]` ZPID recycling rate ~0.1%/year at personal scale

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — ecosystem-standard libraries
- Architecture (4-module split): HIGH — mirrors Phase 12 verbatim
- Envelope contract: HIGH — three shapes are exhaustive; CONTEXT.md locks them
- Pydantic model: HIGH — matches Phase 1 patterns
- DuckDB schema: MEDIUM — Python `duckdb` runtime promotion `[ASSUMED]`; SQL itself HIGH
- Pitfalls 13-16 + 18-21: HIGH; 17 (ZPID recycling): MEDIUM (probability estimate)
- Cost estimate: MEDIUM — pricing `[CITED]` but verify before implementation

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (30 days)

---

*Phase 13 Research — ready for `/gsd-plan-phase 13`.*
