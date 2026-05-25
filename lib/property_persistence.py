"""DuckDB persistence for analyzed_listings. Phase 13 PROP-02 + PERS-08.

Schema: composite PK (zpid, analyzed_at) per D-13-REANALYSIS-01 — re-analysis
appends rather than overwrites. TIMESTAMP defaults to microsecond precision.
listing_json + analysis_json use DuckDB's native JSON type (enables ->>
operators for Phase 14 query convenience).

Reuses lib.fred_cache.with_cache_lock (Phase 12 Python port of
orchestration/lockfile.mjs:withLock) but OVERRIDES the lock filename to
``.lock`` AND pins the lock directory to the repo-rooted ``data/`` (see
``LOCK_DIR`` below). Lock-dir is decoupled from ``db_path`` because
``orchestration/lockfile.mjs`` (lines 24-25) hardcodes the repo-rooted
``data/.lock`` regardless of which DuckDB file the Node writer touches.
Python must match that behavior so the cross-language mutex stays mutually
exclusive even when ``MORTGAGE_OPS_DB_PATH`` overrides ``db_path`` to live
outside the repo. The default ``.fred-cache.lock`` filename is wrong for
this caller — FRED and DuckDB writers must share the SAME lock basename to
be mutually exclusive.

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
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from lib.fred_cache import with_cache_lock

if TYPE_CHECKING:
    from lib.property_listing import PropertyListing

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
"""Repo root: ``lib/property_persistence.py`` is one level deep so
``Path(__file__).resolve().parent.parent`` is ``<repo>/``. ``.resolve()`` makes
this robust to symlinks (e.g. macOS ``/var`` → ``/private/var``)."""

LOCK_DIR: Final[Path] = REPO_ROOT / "data"
"""Repo-rooted ``<repo>/data/`` — the directory ``orchestration/lockfile.mjs``
(lines 24-25) hardcodes for ``LOCK_PATH``. The Node writer ALWAYS locks
``<repo>/data/.lock`` even when ``MORTGAGE_OPS_DB_PATH`` overrides the DB
location (see ``orchestration/db-write.mjs``). Python conforms: lock-dir is
decoupled from ``db_path.parent`` so the two writers stay mutually exclusive
when the DB lives outside the repo."""

DB_PATH: Final[Path] = REPO_ROOT / "data" / "mortgage-ops.duckdb"
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


DUCKDB_LOCK_FILENAME: Final[str] = ".lock"
"""Mirror ``orchestration/lockfile.mjs:LOCK_PATH`` basename. Source of truth is
the Node writer (do NOT change Node code). Both writers must hold the same
basename in ``data/`` to be mutually exclusive — see ``write_listing`` below."""


def write_listing(
    listing: PropertyListing,
    household_hash: str,
    db_path: Path = DB_PATH,
) -> None:
    """PROP-02 + PERS-08: persist a validated listing.

    Acquires ``<repo>/data/.lock`` (NOT ``.fred-cache.lock``, NOT
    ``<db_path.parent>/.lock``) via
    ``with_cache_lock(LOCK_DIR, lock_filename='.lock')`` so this Python writer
    serializes against ``orchestration/lockfile.mjs:withLock``, which is the
    Node writer's mutex. The shared lock-dir is the repo-rooted ``data/``
    (``orchestration/lockfile.mjs`` lines 24-25 hardcode this) and the shared
    basename is ``.lock``. Both must match for cross-process mutex semantics
    to hold even when ``MORTGAGE_OPS_DB_PATH`` overrides ``db_path``.
    """
    import duckdb  # D-18 lazy-import

    # Lock path = REPO_ROOT/data/.lock — byte-identical to
    # orchestration/lockfile.mjs:LOCK_PATH (lines 24-25 of that file pin it to
    # ``dirname(dirname(__filename))/data/.lock``, NOT a path derived from the
    # DB file). Using ``db_path.parent`` here would diverge from Node whenever
    # MORTGAGE_OPS_DB_PATH points outside ``<repo>/data/``, leaving the two
    # writers NOT mutually exclusive. Using ``.fred-cache.lock`` (the
    # with_cache_lock default) was the original PROP-02 contract bug.
    with with_cache_lock(
        LOCK_DIR,
        reason=f"write zpid={listing.zpid}",
        lock_filename=DUCKDB_LOCK_FILENAME,
    ):
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

    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except (duckdb.Error, OSError):
        return None
    try:
        try:
            row = con.execute(
                "SELECT listing_json FROM analyzed_listings WHERE zpid = ? "
                "ORDER BY analyzed_at DESC LIMIT 1",
                [zpid],
            ).fetchone()
        except duckdb.Error:
            # §Pitfall 14: read-only conn cannot run DDL; treat missing-table as no rows
            return None
    finally:
        con.close()

    if row is None:
        return None

    from pydantic import ValidationError

    from lib.property_listing import PropertyListing

    try:
        return PropertyListing.model_validate_json(row[0])
    except (ValidationError, json.JSONDecodeError, KeyError, TypeError):
        return None
