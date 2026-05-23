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
    LOCK_DIR,
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
    """PERS-08: write_listing acquires the lockfile at ``<repo>/data/.lock``.

    Verifies BOTH (a) lock-dir is the repo-rooted ``LOCK_DIR`` (decoupled from
    ``db_path.parent``), AND (b) lock basename is exactly ``.lock`` — matching
    ``orchestration/lockfile.mjs:LOCK_PATH`` (lines 24-25 of that file).

    The dir check closes the cross-language edge case where
    ``MORTGAGE_OPS_DB_PATH`` points outside ``<repo>/data/``: Node hardcodes
    ``<repo>/data/.lock`` regardless of DB path, so Python must too — or the
    two writers stop being mutually exclusive.

    The basename check closes the original PROP-02 concurrency contract bug:
    pre-fix the writer was holding ``.fred-cache.lock`` while the Node writer
    held ``.lock``, so the two were NOT mutually exclusive.
    """
    from contextlib import contextmanager

    from lib import property_persistence

    acquired_dirs: list[Any] = []
    acquired_filenames: list[str] = []

    @contextmanager
    def _spy_lock(cache_dir: Any, **kwargs: Any) -> Any:
        acquired_dirs.append(cache_dir)
        # Capture explicit lock_filename kwarg — None means caller fell back
        # to the with_cache_lock default (`.fred-cache.lock`), which is the
        # PROP-02 bug. We require the caller to pass ``.lock`` explicitly.
        acquired_filenames.append(kwargs.get("lock_filename", ""))
        yield {"acquired_at": "spy", "pid": -1, "reason": kwargs.get("reason", "")}

    monkeypatch.setattr(property_persistence, "with_cache_lock", _spy_lock)

    # db_path lives in tmp_path/subdir — intentionally NOT under <repo>/data/.
    # write_listing must STILL acquire <repo>/data/.lock (LOCK_DIR), matching
    # the Node writer's hardcoded path.
    db = tmp_path / "subdir" / "t.duckdb"
    db.parent.mkdir(parents=True, exist_ok=True)
    write_listing(_make_listing(), household_hash="abc", db_path=db)

    assert len(acquired_dirs) == 1
    # lock-dir is the repo-rooted LOCK_DIR, NOT db.parent — serializes with
    # Phase 9 Node writer even when MORTGAGE_OPS_DB_PATH overrides db_path.
    assert acquired_dirs[0] == LOCK_DIR, (
        f"write_listing must pass LOCK_DIR (<repo>/data/) to share Node writer's "
        f"mutex regardless of db_path. Got: {acquired_dirs[0]!r}, expected: {LOCK_DIR!r}"
    )
    assert acquired_dirs[0] != db.parent, (
        "write_listing must NOT key the lock off db.parent — Node's "
        "orchestration/lockfile.mjs (lines 24-25) hardcodes <repo>/data/.lock "
        "regardless of MORTGAGE_OPS_DB_PATH."
    )
    # Lock basename MUST equal ``.lock`` to match orchestration/lockfile.mjs.
    assert acquired_filenames[0] == ".lock", (
        f"write_listing must pass lock_filename='.lock' to share Node writer's "
        f"mutex (orchestration/lockfile.mjs:LOCK_PATH = data/.lock). "
        f"Got: {acquired_filenames[0]!r}"
    )


def test_write_creates_lockfile_with_exact_filename_dot_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PROP-02 concurrency contract: a real write_listing call (with only
    LOCK_DIR redirected to tmp_path for test isolation, NOT the lock primitive
    itself) MUST create / hold ``<LOCK_DIR>/.lock`` — byte-identical basename
    to ``orchestration/lockfile.mjs:LOCK_PATH``. A test that verifies "some
    lock file in the right directory" is not enough; the BASENAME must match
    the Node writer or the two are not mutually exclusive.

    Strategy: redirect LOCK_DIR to tmp_path so we don't touch the real
    ``<repo>/data/.lock``. Then hold the same ``.lock`` ourselves via the
    underlying with_cache_lock primitive in tmp_path, and call write_listing
    in a thread with a short timeout. If write_listing is asking for
    ``.lock``, it will block (timeout). If it's asking for
    ``.fred-cache.lock`` (the original bug), it will succeed and we'll see
    the wrong-basename file appear.
    """
    import threading
    from datetime import timedelta

    from lib import property_persistence
    from lib.fred_cache import FredCacheLockError, with_cache_lock

    # Redirect LOCK_DIR to tmp_path so this test exercises the lock contract
    # WITHOUT touching the real <repo>/data/.lock. The contract under test is
    # "write_listing locks <LOCK_DIR>/.lock"; redirecting LOCK_DIR is the
    # canonical unit-isolation move.
    monkeypatch.setattr(property_persistence, "LOCK_DIR", tmp_path)

    db = tmp_path / "t.duckdb"
    lock_dir = tmp_path
    listing = _make_listing()

    blocker_held = threading.Event()
    blocker_release = threading.Event()

    def _hold_dot_lock() -> None:
        # Hold the SAME basename Node uses. If write_listing asks for ``.lock``,
        # it will be blocked here.
        with with_cache_lock(lock_dir, reason="test-blocker", lock_filename=".lock"):
            blocker_held.set()
            blocker_release.wait(timeout=10)

    holder = threading.Thread(target=_hold_dot_lock, daemon=True)
    holder.start()
    assert blocker_held.wait(timeout=5), "blocker thread did not acquire .lock"

    # While ``.lock`` is held, ``data/.lock`` should be present with that exact basename.
    dot_lock = lock_dir / ".lock"
    assert dot_lock.exists(), f"expected {dot_lock} to exist while held"
    assert dot_lock.name == ".lock"
    # And there must NOT be a separate ``.fred-cache.lock`` doing the work.
    fred_lock = lock_dir / ".fred-cache.lock"
    assert not fred_lock.exists(), (
        "write_listing must not fall back to .fred-cache.lock — that is the "
        "PROP-02 bug. The Node writer uses .lock, so the Python writer must too."
    )

    # Now attempt write_listing with a very short timeout — it should BLOCK
    # because we're holding the right basename. If it succeeds quickly,
    # the Python writer is locking a different file (the bug).
    write_error: list[BaseException] = []

    def _try_write() -> None:
        try:
            # Patch timeout via monkey on _acquire_lock? Simpler: rely on
            # ``with_cache_lock`` raising FredCacheLockError after timeout
            # when blocker holds the lock. We use a fresh import so we can
            # inject a short timeout via override.
            from lib import fred_cache as _fc
            from lib import property_persistence as _pp

            orig = _fc.with_cache_lock

            from contextlib import contextmanager

            @contextmanager
            def _short_to(cache_dir: Any, **kwargs: Any) -> Any:
                kwargs["timeout"] = timedelta(milliseconds=500)
                with orig(cache_dir, **kwargs) as lk:
                    yield lk

            _pp.with_cache_lock = _short_to  # type: ignore[attr-defined,assignment]
            try:
                write_listing(listing, household_hash="abc", db_path=db)
            finally:
                _pp.with_cache_lock = orig  # type: ignore[attr-defined]
        except BaseException as exc:
            write_error.append(exc)

    writer = threading.Thread(target=_try_write, daemon=True)
    writer.start()
    writer.join(timeout=5)
    blocker_release.set()
    holder.join(timeout=5)

    assert not writer.is_alive(), "writer thread did not return"
    assert write_error, (
        "write_listing did NOT block on .lock — it must be using a different "
        "lock filename (PROP-02 contract bug)."
    )
    assert isinstance(write_error[0], FredCacheLockError), (
        f"expected FredCacheLockError from blocked write_listing; got "
        f"{type(write_error[0]).__name__}: {write_error[0]!r}"
    )


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
