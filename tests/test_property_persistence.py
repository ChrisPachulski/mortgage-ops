"""Tests for lib/property_persistence.py — PROP-02 + PERS-08.

Wave 0 xfail scaffold; Wave 5 (Plan 13-05) flips green.
Mirrors tests/test_fred_cache.py freezegun + lockfile assertion patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.xfail(reason="Phase 13 Wave 5: lib/property_persistence.py not yet built", strict=True)
def test_ensure_schema_creates_analyzed_listings_table(tmp_path: Path) -> None:
    """PERS-08: _ensure_schema creates analyzed_listings + 3 indexes idempotently."""
    from lib.property_persistence import write_listing  # noqa: F401

    raise AssertionError("Wave 5 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 5: persistence not yet built", strict=True)
def test_round_trip_write_read(tmp_path: Path) -> None:
    """PROP-02: write_listing -> read_latest_for_zpid -> byte-equal model."""
    from lib.property_persistence import write_listing  # noqa: F401

    raise AssertionError("Wave 5 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 5: persistence not yet built", strict=True)
def test_composite_pk_allows_reanalysis(tmp_path: Path) -> None:
    """PERS-08 + D-13-REANALYSIS-01: same zpid, different analyzed_at (microsecond delta) -> both rows persist."""
    from lib.property_persistence import write_listing  # noqa: F401

    raise AssertionError("Wave 5 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 5: persistence not yet built", strict=True)
def test_write_acquires_data_lock(tmp_path: Path) -> None:
    """PERS-08: write_listing acquires data/.lock for the duration of the INSERT (Phase 9 lockfile)."""
    from lib.property_persistence import write_listing  # noqa: F401

    raise AssertionError("Wave 5 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 5: persistence not yet built", strict=True)
def test_household_hash_is_content_sha256(tmp_path: Path) -> None:
    """PERS-08 + Q4 default: hashlib.sha256(household.yml + profile.yml + MORTGAGE30US value) hex digest."""
    from lib.property_persistence import compute_household_hash  # noqa: F401

    raise AssertionError("Wave 5 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 5: persistence not yet built", strict=True)
def test_read_latest_returns_none_on_missing_table(tmp_path: Path) -> None:
    """PROP-02 + Pitfall 14: read on fresh empty DB (no table) -> None, not CatalogException."""
    from lib.property_persistence import read_latest_for_zpid  # noqa: F401

    raise AssertionError("Wave 5 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 5: persistence not yet built", strict=True)
def test_malformed_listing_json_falls_through(tmp_path: Path) -> None:
    """PROP-02 + CR-01 idiom: corrupted listing_json row -> read returns None (not KeyError)."""
    from lib.property_persistence import read_latest_for_zpid  # noqa: F401

    raise AssertionError("Wave 5 fills body")
