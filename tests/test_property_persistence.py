"""Tests for lib/property_persistence.py — PROP-02 + PERS-08.

Inherits Phase 12 freezegun + lockfile + CR-01-malformed-row testing patterns
from tests/test_fred_cache.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import freezegun
from lib.property_listing import PropertyListing, ProvenancedMoney
from lib.property_persistence import (
    CREATE_TABLE_SQL,
    DB_PATH,
    SCHEMA_VERSION,
    _ensure_schema,
    compute_household_hash,
    read_latest_for_zpid,
    write_listing,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


# ---------- Helpers ----------


def _make_listing(**overrides: Any) -> PropertyListing:
    defaults: dict[str, Any] = {
        "price": Decimal("625000.00"),
        "zip": "94110",
        "property_type": "SFH",
        "source_url": "https://www.zillow.com/homedetails/x/12345_zpid/",
        "zpid": "12345",
        "fetched_at": datetime(2026, 5, 10, 14, 30, 0, 123456, tzinfo=UTC),
    }
    defaults.update(overrides)
    return PropertyListing(**defaults)


# ---------- Schema ----------


def test_ensure_schema_creates_table_and_indexes(tmp_path: Path) -> None:
    """PERS-08: _ensure_schema is idempotent (IF NOT EXISTS) and creates 1 table + 3 indexes."""
    import duckdb

    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    try:
        _ensure_schema(con)
        # Verify table exists
        tables = con.execute("SHOW TABLES").fetchall()
        table_names = {row[0] for row in tables}
        assert "analyzed_listings" in table_names
        # Verify second call is no-op (no exception)
        _ensure_schema(con)
        # Verify 3 indexes created
        indexes = con.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE table_name = 'analyzed_listings'"
        ).fetchall()
        names = {r[0] for r in indexes}
        assert "idx_listings_zpid" in names
        assert "idx_listings_verdict" in names
        assert "idx_listings_analyzed_at" in names
    finally:
        con.close()


def test_schema_has_composite_pk_in_sql() -> None:
    """D-13-REANALYSIS-01: PK is composite (zpid, analyzed_at)."""
    assert "PRIMARY KEY (zpid, analyzed_at)" in CREATE_TABLE_SQL


def test_schema_version_is_one() -> None:
    assert SCHEMA_VERSION == 1


# ---------- Round-trip ----------


def test_round_trip_write_read(tmp_path: Path) -> None:
    """PROP-02: write_listing → read_latest_for_zpid → byte-equal PropertyListing."""
    db = tmp_path / "t.duckdb"
    listing = _make_listing(
        tax_annual=ProvenancedMoney(value=Decimal("7800.00"), provenance="scraped"),
    )
    write_listing(listing, household_hash="abc123", db_path=db)
    read_back = read_latest_for_zpid("12345", db_path=db)
    assert read_back is not None
    assert read_back == listing


def test_read_latest_returns_none_on_missing_db_file(tmp_path: Path) -> None:
    """read_latest_for_zpid on path-doesn't-exist → None (not FileNotFoundError)."""
    assert read_latest_for_zpid("12345", db_path=tmp_path / "nonexistent.duckdb") is None


def test_read_latest_returns_none_on_missing_table(tmp_path: Path) -> None:
    """§Pitfall 14: read-only conn cannot run DDL; missing table → CatalogException → None."""
    import duckdb

    db = tmp_path / "t.duckdb"
    # Create the db file with NO analyzed_listings schema
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE unrelated (x INTEGER)")
    con.close()
    assert read_latest_for_zpid("12345", db_path=db) is None


def test_read_latest_returns_none_on_unknown_zpid(tmp_path: Path) -> None:
    """Schema exists, table exists, zpid not present → None."""
    db = tmp_path / "t.duckdb"
    write_listing(_make_listing(), household_hash="abc", db_path=db)
    assert read_latest_for_zpid("not-this-zpid", db_path=db) is None


# ---------- Composite PK / D-13-REANALYSIS-01 ----------


def test_composite_pk_allows_reanalysis_with_microsecond_delta(tmp_path: Path) -> None:
    """D-13-REANALYSIS-01: same zpid, different analyzed_at (1µs apart) → both rows persist."""
    db = tmp_path / "t.duckdb"
    listing = _make_listing()

    with freezegun.freeze_time("2026-05-10T14:30:00.123456Z"):
        write_listing(listing, household_hash="abc", db_path=db)
    with freezegun.freeze_time("2026-05-10T14:30:00.123457Z"):  # +1µs
        write_listing(listing, household_hash="def", db_path=db)

    import duckdb

    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT COUNT(*) FROM analyzed_listings WHERE zpid = '12345'").fetchone()
    finally:
        con.close()
    assert row is not None
    assert row[0] == 2


def test_read_latest_returns_most_recent_when_multiple_rows(tmp_path: Path) -> None:
    """ORDER BY analyzed_at DESC: read returns the LATER row."""
    db = tmp_path / "t.duckdb"
    listing_old = _make_listing(price=Decimal("500000.00"))
    listing_new = _make_listing(price=Decimal("625000.00"))

    with freezegun.freeze_time("2026-05-10T14:30:00.111111Z"):
        write_listing(listing_old, household_hash="abc", db_path=db)
    with freezegun.freeze_time("2026-05-10T14:30:00.222222Z"):
        write_listing(listing_new, household_hash="def", db_path=db)

    read_back = read_latest_for_zpid("12345", db_path=db)
    assert read_back is not None
    assert read_back.price == Decimal("625000.00")


# ---------- Malformed row (CR-01 idiom) ----------


def test_malformed_listing_json_falls_through(tmp_path: Path) -> None:
    """CR-01: a corrupted listing_json row → read_latest_for_zpid returns None (not raises)."""
    import duckdb

    db = tmp_path / "t.duckdb"
    # First write a valid row so the table exists
    write_listing(_make_listing(zpid="99999"), household_hash="abc", db_path=db)
    # Now insert a row with malformed JSON manually for zpid 77777
    con = duckdb.connect(str(db))
    try:
        con.execute(
            """INSERT INTO analyzed_listings
               (zpid, analyzed_at, source_url, listing_json,
                analysis_json, verdict, household_hash, schema_version)
               VALUES (?, ?, ?, ?, NULL, NULL, ?, ?)""",
            [
                "77777",
                datetime.now(UTC),
                "https://example.com/.../77777_zpid/",
                '{"corrupted": "missing required PropertyListing fields"}',
                "abc",
                1,
            ],
        )
    finally:
        con.close()
    # Read should return None, not raise ValidationError
    assert read_latest_for_zpid("77777", db_path=db) is None


# ---------- Lockfile ----------


def test_write_acquires_data_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PERS-08: write_listing acquires the lockfile in db_path.parent (data/.lock)."""
    from contextlib import contextmanager

    from lib import property_persistence

    acquired_dirs: list[Any] = []

    @contextmanager
    def _spy_lock(cache_dir: Any, **kwargs: Any) -> Any:
        acquired_dirs.append(cache_dir)
        yield {"acquired_at": "spy", "pid": -1, "reason": kwargs.get("reason", "")}

    monkeypatch.setattr(property_persistence, "with_cache_lock", _spy_lock)

    db = tmp_path / "subdir" / "t.duckdb"
    db.parent.mkdir(parents=True, exist_ok=True)
    write_listing(_make_listing(), household_hash="abc", db_path=db)

    assert len(acquired_dirs) == 1
    # lock-dir is db_path.parent, NOT a subdir (serializes with Phase 9 Node writer)
    assert acquired_dirs[0] == db.parent


# ---------- Household hash (Q4 default) ----------


def test_compute_household_hash_is_sha256_hex(tmp_path: Path) -> None:
    """Q4: content hash is hex SHA256 of (household.yml + profile.yml + MORTGAGE30US value)."""
    household = tmp_path / "household.yml"
    household.write_bytes(b"{income: 250000}")
    profile = tmp_path / "profile.yml"
    profile.write_bytes(b"{first_time_buyer: true}")

    h = compute_household_hash(household, profile, "0.0625")
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_household_hash_is_deterministic(tmp_path: Path) -> None:
    household = tmp_path / "household.yml"
    household.write_bytes(b"data")
    profile = tmp_path / "profile.yml"
    profile.write_bytes(b"more")
    h1 = compute_household_hash(household, profile, "0.0625")
    h2 = compute_household_hash(household, profile, "0.0625")
    assert h1 == h2


def test_compute_household_hash_changes_on_household_edit(tmp_path: Path) -> None:
    household = tmp_path / "household.yml"
    household.write_bytes(b"original")
    profile = tmp_path / "profile.yml"
    profile.write_bytes(b"static")
    h1 = compute_household_hash(household, profile, "0.0625")
    household.write_bytes(b"edited")
    h2 = compute_household_hash(household, profile, "0.0625")
    assert h1 != h2


def test_compute_household_hash_changes_on_rate_edit(tmp_path: Path) -> None:
    household = tmp_path / "household.yml"
    household.write_bytes(b"static")
    profile = tmp_path / "profile.yml"
    profile.write_bytes(b"static")
    h1 = compute_household_hash(household, profile, "0.0625")
    h2 = compute_household_hash(household, profile, "0.0700")
    assert h1 != h2


# ---------- DB_PATH default ----------


def test_db_path_points_to_data_mortgage_ops_duckdb() -> None:
    """DB_PATH is data/mortgage-ops.duckdb relative to project root."""
    assert DB_PATH.name == "mortgage-ops.duckdb"
    assert DB_PATH.parent.name == "data"
