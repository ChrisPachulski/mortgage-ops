"""DuckDB persistence for analyzed_listings. Phase 13 PROP-02 + PERS-08.

Schema: composite PK (zpid, analyzed_at) per D-13-REANALYSIS-01 — re-analysis
appends rather than overwrites. TIMESTAMP defaults to microsecond precision.
listing_json + analysis_json use DuckDB's native JSON type (enables ->>
operators for Phase 14 query convenience).

Reuses lib.fred_cache.with_cache_lock (Phase 12 Python port of
orchestration/lockfile.mjs:withLock) — lock-dir is db_path.parent (data/),
so this writer serializes against the Phase 9 Node writer on the same DB file.

All ``duckdb`` imports are lazy (inside function bodies) per D-18.

Pitfall mitigations:
  §Pitfall 14: read-only connection cannot run DDL → readers catch
    duckdb.CatalogException and treat missing-table as no-rows.
  §Pitfall 21: datetime serialization drift is owned by lib.property_listing
    (Z suffix on fetched_at); DuckDB-native analyzed_at column handles tz.
  CR-01 (Phase 12): malformed listing_json row → read returns None, not raise.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from lib.fred_cache import with_cache_lock

if TYPE_CHECKING:
    from lib.property_listing import PropertyListing

DB_PATH: Final[Path] = Path(__file__).parent.parent / "data" / "mortgage-ops.duckdb"
SCHEMA_VERSION: Final[int] = 1

CREATE_TABLE_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS analyzed_listings (
    zpid            VARCHAR     NOT NULL,
    analyzed_at     TIMESTAMP   NOT NULL,
    source_url      VARCHAR     NOT NULL,
    listing_json    JSON        NOT NULL,
    analysis_json   JSON,
    verdict         VARCHAR,
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
    household_yml: Path,
    profile_yml: Path,
    mortgage30us_value: str,
) -> str:
    """D-13-REANALYSIS-01 + Q4 default: content hash of the 3 inputs that affect verdict.

    Stable hex SHA256 of (household.yml contents + profile.yml contents +
    MORTGAGE30US value string). Whitespace changes count as changes (acceptable —
    analyzed_listings is append-only so an extra row is benign).
    """
    h = hashlib.sha256()
    h.update(household_yml.read_bytes())
    h.update(profile_yml.read_bytes())
    h.update(mortgage30us_value.encode("utf-8"))
    return h.hexdigest()


def _ensure_schema(con: Any) -> None:
    """Idempotent DDL. IF NOT EXISTS makes the second call a no-op.

    No migration runner — v1.2 column changes write _migrate_v2() and bump
    SCHEMA_VERSION above; the loader checks schema_version on read.
    """
    con.execute(CREATE_TABLE_SQL)


def write_listing(
    listing: PropertyListing,
    household_hash: str,
    db_path: Path = DB_PATH,
) -> None:
    """PROP-02 + PERS-08: persist a validated listing. Wrapped in with_cache_lock
    so Python and Node writers serialize on the same data/.lock file.
    """
    import duckdb  # D-18 lazy-import

    # Lock-dir is db_path.parent (data/), NOT a subdirectory — so this serializes
    # against the Phase 9 Node writer (orchestration/db-write.mjs:cmdInsert*).
    with with_cache_lock(db_path.parent, reason=f"write zpid={listing.zpid}"):
        con = duckdb.connect(str(db_path))
        try:
            _ensure_schema(con)
            con.execute(
                """INSERT INTO analyzed_listings
                   (zpid, analyzed_at, source_url, listing_json,
                    analysis_json, verdict, household_hash, schema_version)
                   VALUES (?, ?, ?, ?, NULL, NULL, ?, ?)""",
                [
                    listing.zpid,
                    _now_utc(),
                    listing.source_url,
                    listing.model_dump_json(),
                    household_hash,
                    SCHEMA_VERSION,
                ],
            )
        finally:
            con.close()


def read_latest_for_zpid(zpid: str, db_path: Path = DB_PATH) -> PropertyListing | None:
    """Return most-recent analyzed_listings row for the given zpid, or None.

    Returns None on:
      - DB file does not exist
      - Table does not exist (CatalogException — §Pitfall 14)
      - Zpid has no rows
      - Listing JSON is malformed (CR-01 idiom — defensive)
    """
    import duckdb

    if not db_path.exists():
        return None

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        try:
            row = con.execute(
                "SELECT listing_json FROM analyzed_listings WHERE zpid = ? "
                "ORDER BY analyzed_at DESC LIMIT 1",
                [zpid],
            ).fetchone()
        except duckdb.CatalogException:
            # §Pitfall 14: read-only conn cannot run DDL; treat missing-table as no rows
            return None
    finally:
        con.close()

    if row is None:
        return None

    try:
        from lib.property_listing import PropertyListing

        return PropertyListing.model_validate_json(row[0])
    except Exception:
        return None
