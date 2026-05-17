# Phase 13: Property Ingestion - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 19 (5 new source + 5 new tests + 5 new fixtures + 3 modified + 1 dir-policy)
**Analogs found:** 16 / 19 (84%)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.claude/skills/mortgage-ops/scripts/property_fetch.py` | controller (CLI) | request-response (stdin/argv + envelope) | `.claude/skills/mortgage-ops/scripts/fred_cli.py` | exact (CLI shape, always-exit-0 envelope, lazy-import, parents[4] path) |
| `lib/property_extractor.py` | service (LLM call) | request-response (Sonnet API) | `tests/test_subagents.py::SUBA-06` (anthropic SDK invocation pattern only); no full analog | partial (greenfield — use 13-RESEARCH Example 1) |
| `lib/property_block_detector.py` | utility (pure regex predicate) | transform (status+body → enum) | `lib/rules/*.py` predicate pattern (one citation per file); regex idiom from `lib/fred_cache.py` shape-validate | partial (greenfield — use 13-RESEARCH Example 2) |
| `lib/property_listing.py` | model (Pydantic) | transform (validation) | `lib/models.py` (Loan/Payment/Schedule — strict=True, frozen=True, extra="forbid", Money/Rate Annotated aliases, condecimal at boundaries) | exact (shape) |
| `lib/property_persistence.py` | service (DuckDB writer/reader) | CRUD (file-I/O + lockfile) | `lib/fred_cache.py` (with_cache_lock + schema_version + _now_utc + REQUIRED_ENTRY_FIELDS shape-validate) | role-match (DuckDB instead of JSON cache) |
| `tests/test_property_listing.py` | test (model unit) | transform | `tests/test_models.py` | exact |
| `tests/test_property_block_detector.py` | test (pure-function parametric) | transform | `tests/test_fred_cli.py` block-test patterns + `tests/test_cli_helpers.py` parametric | role-match |
| `tests/test_property_extractor.py` | test (mocked LLM) | request-response (mocked) | `tests/test_subagents.py::SUBA-06` (`pytest.importorskip("anthropic")` + `skipif on ANTHROPIC_API_KEY`) | role-match |
| `tests/test_property_fetch.py` | test (CLI subprocess) | request-response (subprocess) | `tests/test_fred_cli.py` (SCRIPT_PATH + subprocess.run + envelope assertions + always-exit-0 contract) | exact |
| `tests/test_property_persistence.py` | test (DB schema + lock) | event-driven (freezegun + lockfile) | `tests/test_fred_cache.py` (schema_version, freezegun TTL boundaries, malformed-row CR-01 regression, lockfile assertions) | exact (shape) |
| `tests/fixtures/zillow/sfh_conforming_happy_path.html` | data fixture | static fixture | `tests/fixtures/subagent_transcripts/*.jsonl` (synthetic-only-in-CI) | role-match |
| `tests/fixtures/zillow/condo_partial_tax_missing.html` | data fixture | static fixture | same | role-match |
| `tests/fixtures/zillow/blocked_perimeterx.html` | data fixture | static fixture | same | role-match |
| `tests/fixtures/zillow/README.md` | reference doc (fixture policy) | static doc | `tests/fixtures/subagent_transcripts/README.md` (D-02 synthetic policy + live-capture recipe + "What NOT to put here") | exact |
| `tests/fixtures/zillow/extracted/*.json` | data fixture (mock outputs) | static fixture | `tests/fixtures/golden_pmt.json`, `tests/fixtures/amortize/*.json` | exact (one-per-file fixture idiom) |
| `pyproject.toml` (modify) | config | static config | self-analog: Phase 11 `[dependency-groups].dev` add (`anthropic==0.100.0`); Phase 12 `freezegun` add | exact (self-analog) |
| `uv.lock` (regenerated) | config | static config | self-analog | exact |
| `.gitignore` (verify-only) | config | static config | self-analog (already covers `data/*.duckdb`) | exact |

## Pattern Assignments

### `.claude/skills/mortgage-ops/scripts/property_fetch.py` (controller, request-response)

**Analog:** `.claude/skills/mortgage-ops/scripts/fred_cli.py` (Phase 12 — argparse + always-exit-0 envelope + redacted secrets in source_url + lazy imports + sys.path injection from 5-levels-deep skill folder + outer try/except for CR-02 contract)

**Module header + lazy-import discipline** (analog `fred_cli.py:1-42`):
```python
#!/usr/bin/env python3
"""scripts/property_fetch.py — Zillow URL → PropertyListing envelope.

Per INGEST-01..04 + D-13-GAPFILL-01 + D-13-BLOCK-01 + D-13-MODEL-01:
  - WebFetch result is consumed via --html-from path OR stdin (CLI never invokes WebFetch)
  - Three envelope shapes: success / awaiting_user_input / blocked
  - --help works without importing anthropic / duckdb / lib.* (lazy-import per D-18)
  - Always exits 0; argparse parse errors are the documented exit-2 exception
    (Phase 12 D-12-LIVE02-01 + Pitfall 1 verbatim)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
```

**sys.path injection (5-levels-deep relocation; analog `fred_cli.py:81-92`):**
```python
# Phase 13 ships at .claude/skills/mortgage-ops/scripts/property_fetch.py (5 deep).
# parents[4] = repo root (so `from lib.property_* import ...` resolves);
# parents[1] = skill root (so `from scripts._cli_helpers import ...` resolves).
# Runs AFTER argparse so --help fast path is unaffected.
_skill_root = str(Path(__file__).resolve().parents[1])
_project_root = str(Path(__file__).resolve().parents[4])
for _p in (_project_root, _skill_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

**Argparse + envelope emitter** (analog `fred_cli.py:50-113`):
```python
parser = argparse.ArgumentParser(
    prog="property_fetch",
    description="Turn a Zillow URL into a validated PropertyListing envelope.",
    epilog=("Envelope shapes (stdout, single line):\n"
            '  success:   {listing: {...}, missing: [], error: null, ...}\n'
            '  awaiting:  {listing: {...partial...}, missing: ["price",...], awaiting_user_input: true}\n'
            '  blocked:   {listing: null, error: "http_403"|"captcha_detected"|..., ...}\n'
            "ANTHROPIC_API_KEY required; falls back to shape-2 envelope when absent.\n"
            "Always exits 0 once arguments parse; argparse exits 2 on parse errors."),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("url")
parser.add_argument("--user-provided", type=str, default=None)
parser.add_argument("--html-from", type=Path, default=None)
args = parser.parse_args()

def _emit(envelope: dict[str, Any]) -> int:
    """Mirror fred_cli._emit: single-line JSON on stdout, ALWAYS exit 0."""
    print(json.dumps(envelope))
    return 0
```

**Outer try/except CR-02 contract** (analog `fred_cli.py:211-233`):
```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise   # argparse exit-2 — the one documented non-zero exit
    except Exception as exc:  # noqa: BLE001 — load-bearing always-exit-0 (Phase 12 CR-02)
        print(json.dumps({
            "listing": None, "missing": [],
            "error": f"unexpected_failure: {exc!r}",
            "awaiting_user_input": False,
            "source_url": "<unknown>",
            "fetched_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }))
        sys.exit(0)
```

**Secret redaction discipline** (analog `fred_cli.py:138-145`): `ANTHROPIC_API_KEY` MUST NEVER be str-interpolated into envelope fields or error messages. The SDK handles the auth header; mirror `fred_cli.py`'s `redacted_url` posture for any URL that would otherwise carry credentials. (For Phase 13 there is no URL with the key — Sonnet SDK is the only consumer — but the anti-pattern guard remains.)

---

### `lib/property_extractor.py` (service, Sonnet API call)

**Analog:** No close functional analog (this is the first project module that calls Anthropic SDK from runtime code; `tests/test_subagents.py::SUBA-06` only uses `count_tokens` and only in test scope). Use 13-RESEARCH Code Example 1 verbatim.

**Conventions inherited from Phase 12:**
- `from __future__ import annotations` + `from typing import Final` for module-level constants (analog `lib/fred_cache.py:25-72`).
- Lazy-import `anthropic` INSIDE the function body, not at module top, so callers that only need module-level constants (e.g., test introspection, --help paths) don't pay the import cost (analog: `fred_cli.py:97` lazy `import urllib...`).
- **Never raises** — all failure modes return `None` so the CLI emits shape-2 per D-13-MODEL-01 + always-exit-0 (analog: `fred_cli.py:_fetcher` returns envelope on all exception classes; see `fred_cli.py:183-209`).

**Pattern excerpt** (full source: 13-RESEARCH Example 1 lines 194-272):
```python
SONNET_MODEL: Final[str] = "claude-sonnet-4-6"
SONNET_MAX_TOKENS: Final[int] = 4096

def extract_listing(html: str, source_url: str) -> dict[str, object] | None:
    """Call Sonnet. Returns None on any failure (auth/rate/network/JSON-decode)."""
    try:
        import anthropic
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
    except Exception:  # noqa: BLE001 — always-exit-0 contract (Phase 12 CR-02)
        return None
    match = re.search(r"\{.*\}", raw, re.DOTALL)  # §Pitfall 18: strip prose prefix
    if match is None:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
```

---

### `lib/property_block_detector.py` (utility, pure regex predicate)

**Analog:** No direct analog. Conceptually mirrors `lib/rules/*.py` "one predicate per citation" pattern from CLAUDE.md "Rules-as-predicates" convention. Regex compilation idiom mirrors `lib/fred_cache.py` `REQUIRED_ENTRY_FIELDS` module constant + shape-validate posture.

**Pattern excerpt** (full source: 13-RESEARCH Example 2 lines 316-361):
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

# §Pitfall 19: attribute order-agnostic
NEXT_DATA_RE: Final[re.Pattern[str]] = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>', re.IGNORECASE,
)
# Supports /homedetails/{slug}/{zpid}_zpid/ AND /b/{zpid}_zpid/
ZPID_RE: Final[re.Pattern[str]] = re.compile(
    r"/(?:homedetails/[^/]+/|b/)(\d+)_zpid/?", re.IGNORECASE,
)
```

**Detection order** (cheap-first; mirrors `lib/fred_cache.py:is_fresh` strict-`<` boundary discipline of testing the cheap predicate before the expensive one):
```python
def detect_block(status_code: int, body: str) -> BlockError | None:
    if status_code == 403: return "http_403"
    if status_code == 429: return "http_429"
    if status_code == 503: return "http_503"
    if status_code != 200: return "http_other"
    if len(body) < MIN_BODY_BYTES: return "body_too_short"
    lowered = body.lower()
    if any(p in lowered for p in CAPTCHA_PHRASES): return "captcha_detected"
    if NEXT_DATA_RE.search(body) is None: return "missing_next_data"
    return None
```

---

### `lib/property_listing.py` (model, Pydantic)

**Analog:** `lib/property_listing.py` mirrors `lib/models.py` (Phase 1 FND-02) verbatim in shape.

**Module header pattern** (analog `lib/models.py:1-33`):
```python
"""PropertyListing Pydantic model. Phase 13 PROP-01.
Mirrors lib/models.py shape: strict=True, frozen=True, extra="forbid"."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from lib.models import Money   # reuse the Annotated[Decimal, ...] alias
```

**ConfigDict pattern** (analog `lib/models.py:39, 51, 67`):
```python
model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
```
All three flags are load-bearing per the existing project convention — `strict=True` rejects floats for Decimal (CLAUDE.md "Money discipline"); `frozen=True` makes the model hashable for use in sets/dict keys; `extra="forbid"` surfaces JSON typos immediately (Phase 1 D-19 inheritance).

**Decimal serialization discipline** (analog `lib/models.py` + `tests/test_models.py:95-100`):
```python
@field_serializer("baths")
def _serialize_baths(self, v: Decimal | None) -> str | None:
    # D-19 money discipline: Decimal → JSON STRING, not float
    return str(v) if v is not None else None
```
Pydantic v2's default Decimal serialization is already string-typed when the input is Decimal (verified `tests/test_models.py:95-100`: `'"principal": "400000.00"'`). The explicit serializer is needed only for the datetime `Z`-suffix normalization per §Pitfall 21:
```python
@field_serializer("fetched_at")
def _serialize_dt(self, v: datetime) -> str:
    # Phase 12 _now_utc convention: ISO-8601 with 'Z' suffix (not '+00:00')
    return v.isoformat().replace("+00:00", "Z")
```

**Validator pattern** (analog `lib/models.py:76-91` `_total_interest_matches_last_cumulative`):
```python
@field_validator("baths")
@classmethod
def _baths_half_step(cls, v: Decimal | None) -> Decimal | None:
    if v is None: return v
    if (v * 2) % 1 != 0:
        raise ValueError(f"baths must be 0.5 increments; got {v}")
    return v
```

**Full target shape:** See 13-RESEARCH Code Example 3 (lines 384-457). `ProvenancedMoney` wrapper is greenfield (no analog) — its design (`value: Money | None` + `provenance: Literal[...]`) directly mirrors the `lib.models.Money` Annotated-alias idiom.

---

### `lib/property_persistence.py` (service, DuckDB writer/reader)

**Analog:** `lib/fred_cache.py` (Phase 12) — structurally parallel: module constants pinned with `Final`, schema_version pattern, `_now_utc()`, `with_cache_lock` reused verbatim, `REQUIRED_ENTRY_FIELDS`-style shape-validate on read for malformed rows (CR-01 regression), defensive `except Exception: return None` on read for always-exit-0 callers.

**Module-level constants pattern** (analog `lib/fred_cache.py:42-72`):
```python
"""DuckDB persistence for analyzed_listings. Phase 13 PROP-02 + PERS-08.
Reuses with_cache_lock from lib.fred_cache (Phase 12 lockfile primitive)."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

from lib.fred_cache import with_cache_lock

if TYPE_CHECKING:
    from lib.property_listing import PropertyListing

DB_PATH: Final[Path] = Path(__file__).parent.parent / "data" / "mortgage-ops.duckdb"
SCHEMA_VERSION: Final[int] = 1
```

**Schema DDL + idempotent `_ensure_schema`** (analog: Phase 9 `orchestration/db-write.mjs` schema pattern; analog for the Python idiom: `lib/fred_cache.py:_save_cache` writes schema-versioned payload):
```python
CREATE_TABLE_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS analyzed_listings (
    zpid            VARCHAR     NOT NULL,
    analyzed_at     TIMESTAMP   NOT NULL,   -- DuckDB default: microsecond precision
    source_url      VARCHAR     NOT NULL,
    listing_json    JSON        NOT NULL,
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

def _ensure_schema(con) -> None:
    """Idempotent DDL; runs on every write — IF NOT EXISTS makes it a no-op after first call."""
    con.execute(CREATE_TABLE_SQL)
```

**`_now_utc()` reuse** (analog `lib/fred_cache.py:107-109`):
```python
def _now_utc() -> datetime:
    """Microsecond-precision UTC. freezegun-friendly. Mirrors lib.fred_cache._now_utc."""
    return datetime.now(UTC)
```

**`with_cache_lock` wrapping** (analog `lib/fred_cache.py:_save_cache` lines 291-301):
```python
def write_listing(listing: PropertyListing, household_hash: str, db_path: Path = DB_PATH) -> None:
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
```
**Critical:** the lock-dir is `db_path.parent` (`data/`), not the cache subdirectory — this serializes against the Phase 9 Node writer's `data/.lock` so Python and Node writes to `mortgage-ops.duckdb` cannot interleave.

**Shape-validate on read (CR-01 regression idiom)** (analog `lib/fred_cache.py:267-288`):
```python
def read_latest_for_zpid(zpid: str, db_path: Path = DB_PATH) -> PropertyListing | None:
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        row = con.execute(
            "SELECT listing_json FROM analyzed_listings WHERE zpid = ? "
            "ORDER BY analyzed_at DESC LIMIT 1", [zpid],
        ).fetchone()
    except duckdb.CatalogException:   # §Pitfall 14: missing table on cold read
        return None
    finally:
        con.close()
    if row is None: return None
    try:
        from lib.property_listing import PropertyListing
        return PropertyListing.model_validate_json(row[0])
    except Exception:  # noqa: BLE001 — defensive, mirrors fred_cache CR-01
        return None
```

**Content-hash helper** (no analog — greenfield; uses stdlib `hashlib.sha256` per CLAUDE.md V6 Crypto):
```python
def compute_household_hash(household_yml: Path, profile_yml: Path, mortgage30us_value: str) -> str:
    """D-13-REANALYSIS-01: content hash of inputs that affect verdict."""
    h = hashlib.sha256()
    h.update(household_yml.read_bytes())
    h.update(profile_yml.read_bytes())
    h.update(mortgage30us_value.encode("utf-8"))
    return h.hexdigest()
```

---

### `tests/test_property_listing.py` (test, model unit)

**Analog:** `tests/test_models.py` (Phase 1)

**Imports + boilerplate** (analog `tests/test_models.py:1-23`):
```python
"""Tests for lib/property_listing.py — PROP-01 + ProvenancedMoney."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from lib.property_listing import PropertyListing, ProvenancedMoney
from lib.models import Money
from pydantic import ValidationError
```

**Test-naming + hand-calc-citation idiom** (analog `tests/test_models.py:25-71`):
```python
def test_property_listing_accepts_must_haves_only() -> None:
    # D-13-MUSTHAVE-01: price + zip + property_type validates; all others default None
    listing = PropertyListing(
        price=Decimal("625000.00"), zip="94110", property_type="SFH",
        source_url="https://www.zillow.com/homedetails/x/12345_zpid/",
        zpid="12345",
        fetched_at=datetime(2026, 5, 10, 14, 30, 0, 123456, tzinfo=UTC),
    )
    assert listing.tax_annual is None
    assert listing.hoa_monthly is None

def test_rejects_float_price() -> None:
    # strict=True must reject floats (CLAUDE.md Money discipline)
    with pytest.raises(ValidationError):
        PropertyListing(price=625000.0, zip="94110", property_type="SFH", ...)  # type: ignore

def test_rejects_4_digit_zip() -> None:
    with pytest.raises(ValidationError):
        PropertyListing(price=Decimal("625000.00"), zip="9411",
                        property_type="SFH", ...)
```

**Round-trip serialization** (analog `tests/test_models.py:95-100` — `'"principal": "400000.00"'` literal-in-string assertion):
```python
def test_round_trip_serialization() -> None:
    """PROP-02 baseline: serialize → JSON → deserialize → byte-equal."""
    listing = PropertyListing(...)
    s = listing.model_dump_json()
    assert '"price": "625000.00"' in s   # money as JSON STRING per D-19
    assert '"value": "7800.00"' in s     # ProvenancedMoney.value also string
    assert PropertyListing.model_validate_json(s) == listing
```

---

### `tests/test_property_block_detector.py` (test, parametric pure-function)

**Analog:** `tests/test_cli_helpers.py` (parametric coverage of pure helpers) + `tests/test_fred_cli.py:78-90` parametrize idiom

**Pattern excerpt:**
```python
import pytest
from lib.property_block_detector import detect_block, extract_zpid, MIN_BODY_BYTES

@pytest.mark.parametrize("status,expected", [
    (403, "http_403"), (429, "http_429"), (503, "http_503"),
    (500, "http_other"), (200, None),  # 200 alone is not blocked
])
def test_detect_block_status_codes(status: int, expected: str | None) -> None:
    body = "<html>" + "x" * (MIN_BODY_BYTES + 100) + '<script id="__NEXT_DATA__">{}</script></html>'
    assert detect_block(status, body) == expected

@pytest.mark.parametrize("url,expected", [
    ("https://www.zillow.com/homedetails/123-Main-SF-CA-94110/12345678_zpid/", "12345678"),
    ("https://zillow.com/b/87654321_zpid/", "87654321"),
    ("https://zillow.com/.../12345_zpid", "12345"),
    ("https://zillow.com/.../12345_zpid/?source=email", "12345"),
    ("https://zillow.com/.../12345_zpid/#photos", "12345"),
    ("http://www.zillow.com/.../12345_zpid/", "12345"),
    ("https://redfin.com/property/12345", None),
    ("https://zillow.com/homedetails/foo/", None),
    ("", None),
])
def test_extract_zpid(url: str, expected: str | None) -> None:
    assert extract_zpid(url) == expected
```
Full URL matrix in 13-RESEARCH Example 2 lines 363-376.

---

### `tests/test_property_extractor.py` (test, mocked Sonnet)

**Analog:** `tests/test_subagents.py::SUBA-06` lines 432-471 (`pytest.importorskip("anthropic")` + `@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), ...)`)

**Skip pattern** (verbatim from `tests/test_subagents.py:432-440`):
```python
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason=(
        "Live Sonnet extraction test requires ANTHROPIC_API_KEY. "
        "Skip is intentional for local dev without the key; "
        "CI must inject the key as a secret (or use the mock_sonnet fixture)."
    ),
)
def test_extract_listing_live() -> None:
    anthropic = pytest.importorskip("anthropic")
    ...
```

**Synthetic mock via conftest fixture** (analog: `tests/fixtures/subagent_transcripts/` synthetic-only-in-CI policy, applied here via the 13-RESEARCH conftest pattern lines 966-973):
```python
# tests/conftest.py (add this fixture)
@pytest.fixture
def mock_sonnet(monkeypatch):
    def _fake(html: str, source_url: str) -> dict | None:
        digest = hashlib.sha256(html.encode()).hexdigest()[:16]
        f = Path(f"tests/fixtures/zillow/extracted/{digest}.json")
        return json.loads(f.read_text()) if f.exists() else None
    monkeypatch.setattr("lib.property_extractor.extract_listing", _fake)
```

---

### `tests/test_property_fetch.py` (test, CLI subprocess)

**Analog:** `tests/test_fred_cli.py` (Phase 12) — `SCRIPT_PATH` constant, `subprocess.run` envelope assertions, `--help` fast-path lazy-import gate, always-exit-0 contract

**SCRIPT_PATH constant** (analog `tests/test_fred_cli.py:17-28`):
```python
SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude" / "skills" / "mortgage-ops" / "scripts" / "property_fetch.py"
)
```

**--help fast-path test** (analog `tests/test_fred_cli.py:40-52`):
```python
def test_property_fetch_help_fast_lazy_imports() -> None:
    """--help must complete in <300ms (lazy-import discipline per D-18)."""
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True, text=True, timeout=5,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert elapsed < 0.3, f"--help took {elapsed:.3f}s; D-18 violated"
```

**Always-exit-0 envelope test** (analog `tests/test_fred_cli.py:55-75`):
```python
def test_blocked_envelope_returns_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-13-BLOCK-01: captcha → exit 0 + envelope.error='captcha_detected'."""
    fixture = Path("tests/fixtures/zillow/blocked_perimeterx.html")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH),
         "https://www.zillow.com/homedetails/x/12345_zpid/",
         "--html-from", str(fixture)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0   # NOT 2 — D-13-MODEL-01 inherits D-12-LIVE02-01
    envelope = json.loads(result.stdout)
    assert envelope["listing"] is None
    assert envelope["error"] == "captcha_detected"
    assert envelope["awaiting_user_input"] is False
```

**Full 10-test matrix:** 13-RESEARCH Code Example 5 "Required tests" (lines 791-801).

---

### `tests/test_property_persistence.py` (test, DuckDB + lockfile + freezegun)

**Analog:** `tests/test_fred_cache.py` (Phase 12) — schema_version, freezegun TTL boundaries pattern, malformed-row CR-01 regression, lockfile acquisition assertions

**Freezegun composite-PK pattern** (analog `tests/test_fred_cache.py:59-77` TTL-boundary freezegun usage):
```python
def test_composite_pk_allows_reanalysis(tmp_path: Path) -> None:
    """D-13-REANALYSIS-01: same zpid, different analyzed_at (microsecond delta) → both rows persist."""
    from lib.property_persistence import write_listing
    from lib.property_listing import PropertyListing

    db_path = tmp_path / "test.duckdb"
    listing = PropertyListing(...)  # MUST-HAVE shape
    with freezegun.freeze_time("2026-05-10T14:30:00.123456Z"):
        write_listing(listing, household_hash="abc", db_path=db_path)
    with freezegun.freeze_time("2026-05-10T14:30:00.123457Z"):   # +1µs
        write_listing(listing, household_hash="def", db_path=db_path)
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM analyzed_listings WHERE zpid='12345'").fetchone()[0]
    assert n == 2
```

**Lockfile assertion** (analog `tests/test_fred_cache.py:98-111` `test_cache_write_acquires_lock`):
```python
def test_write_acquires_lock(tmp_path: Path) -> None:
    """PERS-08: write_listing holds data/.lock for the duration of the write
    (Python port of orchestration/lockfile.mjs:withLock)."""
    from lib.property_persistence import write_listing
    # (use a monkeypatched DB_PATH or db_path arg pointing to tmp_path/data/)
```

**Malformed-row CR-01-style regression** (analog `tests/test_fred_cache.py:189-234`):
```python
def test_malformed_listing_json_falls_through(tmp_path: Path) -> None:
    """CR-01 idiom: corrupted listing_json row → read returns None (not KeyError)."""
    # Insert a row with listing_json = "{partial garbage..." then assert
    # read_latest_for_zpid returns None.
```

---

### `tests/fixtures/zillow/README.md` (reference doc, fixture policy)

**Analog:** `tests/fixtures/subagent_transcripts/README.md` (Phase 11 D-02 — synthetic-only-in-CI policy + live-capture recipe + "What NOT to put here")

**Required sections (mirror `subagent_transcripts/README.md` 1-167):**
1. **Files table** — fixture name, tested SC, what it covers (mirror lines 19-28)
2. **"Why synthetic, not live (D-02)"** — determinism, zero recurring cost, airgap-safe, contract-is-shape (mirror lines 36-55)
3. **Capture-and-sanitize recipe** — adapted for HTML scrape (per 13-RESEARCH lines 954-961):
   - View Source → Save As `.html`. Strip `<img>` tags, agent bios, PII.
   - Preserve `<script id="__NEXT_DATA__">` verbatim.
   - Rewrite address fields in `__NEXT_DATA__` to synthetic values. **ZIP stays real** (Phase 14 needs it for per-zip tax lookups).
   - For mocked Sonnet outputs: `sha16 = hashlib.sha256(html_bytes).hexdigest()[:16]`; save at `extracted/{sha16}.json`.
4. **"When to regenerate"** — quarterly drift check, after Sonnet prompt change, after Pydantic schema change (mirror lines 126-143)
5. **`ANTHROPIC_API_KEY` scope table** — mirrors lines 145-151; rows: load fixture (no key), live capture (paid key, NOT in CI), `extract_listing` against real Zillow (paid key, NOT in CI)
6. **"What NOT to put here"** — no PII (no real addresses, no agent contact info, no household.yml values); no AI-attribution trailers (CLAUDE.md global rule) (mirror lines 153-167)

---

### `pyproject.toml` (modify)

**Analog:** self-analog — Phase 11 Wave 0 added `anthropic==0.100.0` under `[dependency-groups].dev` (verified `pyproject.toml:15`); Phase 12 added `freezegun>=1.5` + `python-frontmatter>=1.1` under same group (verified `pyproject.toml:16, 21`).

**Exact edit** (per 13-RESEARCH §Anthropic SDK Runtime Promotion lines 147-181):
```toml
# BEFORE pyproject.toml lines 6-22 (current state):
[project]
dependencies = [
    "pydantic>=2.13.3",
    "python-dateutil>=2.9.0",
    "numpy-financial==1.0.0",
    "pyyaml>=6.0.2",
]
[dependency-groups]
dev = [
    "anthropic==0.100.0",   # <-- move out (becomes runtime)
    "freezegun>=1.5",
    ...
]

# AFTER:
[project]
dependencies = [
    "anthropic>=0.100.0,<1.0",     # runtime promotion (Phase 13)
    "duckdb>=1.4,<2.0",            # new runtime dep (Phase 13)
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

**Side effect:** `uv.lock` regenerates after `uv sync`; commit must include the delta. CI matrix unchanged (`anthropic` already installs).

---

### `uv.lock` (regenerated)

No hand-edit — emitted by `uv sync` after the `pyproject.toml` edit lands. Commit the delta with the same PR.

---

### `.gitignore` (verify-only)

**Verified state:** `.gitignore:24` already covers `data/*.duckdb` (Phase 9). `analyzed_listings` lives inside `data/mortgage-ops.duckdb`, so no new entry needed for the table. Phase 9 also already covers `data/.lock` (line 43); `with_cache_lock(db_path.parent)` reuses this lockfile path. No `.gitignore` edit required for Phase 13.

If the planner decides to use a per-zpid HTML cache file at `data/cache/property-{zpid}.html` (13-RESEARCH §Open Q1 recommendation), add:
```
# Phase 13: per-zpid HTML cache (Data Layer — generated)
data/cache/property-*.html
```

## Shared Patterns

### Always-exit-0 envelope discipline (CLI files)

**Source:** `.claude/skills/mortgage-ops/scripts/fred_cli.py:105-113` (`_emit` helper) + `:211-233` (outer try/except CR-02)
**Apply to:** `scripts/property_fetch.py` (Phase 13's only CLI)

```python
def _emit(envelope: dict[str, Any]) -> int:
    """ALWAYS exit 0; SKILL.md prose-only injection reads envelope.error."""
    print(json.dumps(envelope))
    return 0

# At module bottom:
if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise   # argparse exit-2 — the one documented exception
    except Exception as exc:  # noqa: BLE001 — load-bearing per Phase 12 CR-02
        print(json.dumps({"listing": None, "error": f"unexpected_failure: {exc!r}",
                          "missing": [], "awaiting_user_input": False, ...}))
        sys.exit(0)
```

### Lazy-import discipline (D-18 inherited)

**Source:** `.claude/skills/mortgage-ops/scripts/fred_cli.py:88-101` (lazy `urllib`, `lib.fred_cache` after argparse parses)
**Apply to:** `scripts/property_fetch.py` (lazy `anthropic`, `duckdb`, `lib.property_*`); `lib/property_extractor.py` (lazy `anthropic` inside function body); `lib/property_persistence.py` (lazy `duckdb` inside `write_listing` / `read_latest_for_zpid`).

**Gate:** `--help` must complete in <300ms (asserted by `tests/test_fred_cli.py:40-52` — replicate in `tests/test_property_fetch.py`).

### Money discipline (CLAUDE.md)

**Source:** `lib/models.py:23-33` (Money/Rate Annotated aliases); `tests/test_models.py:37-100` (strict=True rejects floats; Decimal serializes as JSON STRING)
**Apply to:** `lib/property_listing.py` (all money fields use `lib.models.Money`); `lib/property_extractor.py` `_coerce_money_to_string` boundary defense (§Pitfall 15); `scripts/property_fetch.py` `_strip_money` user-input scrubber (§Pitfall 16).

**Forbidden:** `Decimal(float)` anywhere. Use `Decimal(str(v))` or `f"{v:.2f}"` at the boundary (per 13-RESEARCH §Pitfall 15 mitigation).

### Lockfile-wrapped writes (Phase 9 inheritance)

**Source:** `lib/fred_cache.py:235-254` `with_cache_lock` + `:291-301` `_save_cache` usage pattern; original `orchestration/lockfile.mjs:withLock`
**Apply to:** `lib/property_persistence.py:write_listing` — wraps DuckDB INSERT in `with_cache_lock(db_path.parent, reason=...)`. Lock-dir is `data/`, not `data/cache/`, so the lock serializes against the Phase 9 Node writer's `data/.lock`.

### Schema-version + shape-validate on read (Phase 12 CR-01)

**Source:** `lib/fred_cache.py:61-72` (`SCHEMA_VERSION` + `REQUIRED_ENTRY_FIELDS`) + `:267-288` (`_load_cache` returns None on missing required fields)
**Apply to:** `lib/property_persistence.py:read_latest_for_zpid` — catch `duckdb.CatalogException` for missing table (§Pitfall 14) AND wrap `PropertyListing.model_validate_json` in `try/except Exception: return None` so corrupted rows fall through to "no row" semantics rather than crashing the caller (CR-01 idiom verbatim).

### Synthetic-only-in-CI fixture policy (Phase 11 D-02)

**Source:** `tests/fixtures/subagent_transcripts/README.md` lines 36-167 (why synthetic, what NOT to put here, live-capture recipe, when to regenerate)
**Apply to:** `tests/fixtures/zillow/README.md` (Phase 13 ships seed fixtures; Phase 17 expands the set). All committed HTML fixtures must be PII-stripped + synthetic-address per the §Pitfall + 13-RESEARCH §Test Fixture Strategy.

### No AI attribution (CLAUDE.md global)

**Source:** CLAUDE.md global rule (no Co-Authored-By, no AI-attribution in any commit/comment/doc/string literal)
**Apply to:** every new file, every commit message, every docstring, every fixture comment. Verified `tests/fixtures/subagent_transcripts/README.md:163-167` carries this same prohibition; mirror verbatim into `tests/fixtures/zillow/README.md`.

## No Analog Found

Files with no close analog in the codebase — planner should rely on 13-RESEARCH.md Code Examples:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `lib/property_extractor.py` | service (Sonnet API) | request-response | First runtime caller of `anthropic` SDK; only test-scope use exists (`tests/test_subagents.py::SUBA-06` for `count_tokens`). Use 13-RESEARCH Example 1 verbatim. |
| `lib/property_block_detector.py` | utility (regex predicates) | transform | No project module performs URL/HTML regex classification today; closest doctrine ("one predicate per citation") is `lib/rules/*.py` but the role is different. Use 13-RESEARCH Example 2 verbatim. |
| `tests/fixtures/zillow/*.html` | data fixture | static fixture | No HTML fixtures in repo; closest committed-text fixtures are JSONL transcripts under `tests/fixtures/subagent_transcripts/`. Sanitization recipe is greenfield — see 13-RESEARCH §Test Fixture Strategy. |

## Metadata

**Analog search scope:**
- `lib/` (Phases 1-12: models, fred_cache, money, amortize, apr, refinance, affordability, stress, arm, points, rules/)
- `scripts/` + `.claude/skills/mortgage-ops/scripts/` (Phase 10 + 12 CLIs)
- `tests/` (24 test modules; all conftest/fixtures)
- `orchestration/` (Node lockfile + db-write; Python port lives in `lib/fred_cache.py`)
- `pyproject.toml`, `.gitignore`, `CLAUDE.md`
- `.planning/phases/12-fred-eval/12-PATTERNS.md` (for PATTERNS.md format reference)

**Files scanned:** ~60 source/test files; full repo `lib/`, `scripts/`, `tests/`, `orchestration/` trees.

**Pattern extraction date:** 2026-05-10
