"""Phase 12 Wave-0 stubs for lib/fred_cache.py — 7-day TTL + lockfile contract.

Plan 12-02 flips LIVE-03 stubs. Per D-12-LIVE02-01: 7-day TTL with strict-`<`
boundary (RESEARCH §Pitfall 2: 6d23h59m fresh / 7d0h stale / 8d stale).
Lock writes via a Python port of orchestration/lockfile.mjs `withLock`
(60s stale recovery, JSON-content `acquired_at` not mtime, read-back-verify
CAS pattern per Phase 9 inheritance).

All tests in this module are decorated `@pytest.mark.xfail(strict=True)`.

Requirements covered:
  - LIVE-03 + SC-2: 7-day TTL boundary cases (fresh / stale / refetch trigger)
  - LIVE-03: cache writes acquire .fred-cache.lock for the duration of the write
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import freezegun
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _seed_cache(tmp_path: Path, fetched_at_iso: str) -> Path:
    """Write a minimal cache file used by all freezegun TTL boundary tests.

    Cache schema matches lib/fred_cache.py canonical shape pinned in
    12-PATTERNS.md (schema_version: 1, entries: {series_id: {...}}).
    Money/rate fields are JSON STRINGS per D-19 money discipline.
    """
    cache_file = tmp_path / "fred_MORTGAGE30US.json"
    cache_file.write_text(json.dumps({
        "schema_version": 1,
        "entries": {
            "MORTGAGE30US": {
                "value": "6.84",
                "observation_date": "2026-04-25",
                "fetched_at": fetched_at_iso,
                "source_url": (
                    "https://api.stlouisfed.org/fred/series/observations"
                    "?series_id=MORTGAGE30US&api_key=***&file_type=json"
                    "&sort_order=desc&limit=1"
                ),
                "fred_realtime_start": "2026-04-26",
                "fred_realtime_end": "2026-04-26",
            },
        },
    }))
    return cache_file


@pytest.mark.xfail(
    reason="Plan 12-02 ships lib/fred_cache.py — LIVE-03 fresh boundary",
    strict=True,
)
def test_six_d_twenty_three_h_old_cache_is_fresh(tmp_path: Path) -> None:
    """LIVE-03 + SC-2 boundary: 6d 23h 59m -> fresh (strict-< TTL)."""
    from lib.fred_cache import is_fresh  # type: ignore[import-not-found]

    cache_file = _seed_cache(tmp_path, "2026-04-25T12:00:00Z")
    with freezegun.freeze_time("2026-05-02T11:59:59Z"):
        entry = json.loads(cache_file.read_text())["entries"]["MORTGAGE30US"]
        assert is_fresh(entry) is True


@pytest.mark.xfail(
    reason="Plan 12-02 ships lib/fred_cache.py — LIVE-03 strict-< boundary",
    strict=True,
)
def test_seven_d_exactly_old_cache_is_stale(tmp_path: Path) -> None:
    """LIVE-03 + SC-2 boundary: exactly 7d -> stale (strict `<` means age == TTL
    triggers refetch). Documented in RESEARCH §Pitfall 2."""
    from lib.fred_cache import is_fresh

    cache_file = _seed_cache(tmp_path, "2026-04-25T12:00:00Z")
    with freezegun.freeze_time("2026-05-02T12:00:00Z"):
        entry = json.loads(cache_file.read_text())["entries"]["MORTGAGE30US"]
        assert is_fresh(entry) is False


@pytest.mark.xfail(
    reason="Plan 12-02 ships lib/fred_cache.py — LIVE-03 8d refetch",
    strict=True,
)
def test_eight_d_old_cache_triggers_refetch(tmp_path: Path) -> None:
    """SC-2: 8d -> stale -> refetch path engages (StaleCacheWarning emitted)."""
    from lib.fred_cache import (
        StaleCacheWarning,
        is_fresh,
        warn_if_stale,
    )

    cache_file = _seed_cache(tmp_path, "2026-04-25T12:00:00Z")
    with freezegun.freeze_time("2026-05-03T12:00:00Z"):
        entry = json.loads(cache_file.read_text())["entries"]["MORTGAGE30US"]
        assert is_fresh(entry) is False
        with pytest.warns(StaleCacheWarning):
            # Plan 12-02 emits StaleCacheWarning when callers query a stale entry
            # via get_cached_or_fetch — assert the warning channel exists.
            warn_if_stale(entry)


@pytest.mark.xfail(
    reason="Plan 12-02 ports withLock from orchestration/lockfile.mjs",
    strict=True,
)
def test_cache_write_acquires_lock(tmp_path: Path) -> None:
    """LIVE-03 lock contract: cache writes hold the .fred-cache.lock for the
    duration of the write (Python port of orchestration/lockfile.mjs withLock —
    60s stale recovery)."""
    from lib.fred_cache import with_cache_lock

    with with_cache_lock(cache_dir=tmp_path, reason="test"):
        lock_file = tmp_path / ".fred-cache.lock"
        assert lock_file.exists()
        data = json.loads(lock_file.read_text())
        assert "pid" in data
        assert "acquired_at" in data
    # After context exit, lock released
    assert not (tmp_path / ".fred-cache.lock").exists()
