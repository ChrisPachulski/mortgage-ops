"""Phase 12 Wave-2 live tests: LIVE-03 + SC-2 boundary closed.

Plan 12-02 ships ``lib/fred_cache.py``. Per D-12-LIVE02-01: 7-day TTL with strict-``<``
boundary (RESEARCH §Pitfall 2: 6d23h59m fresh / 7d0h stale / 8d stale).
Lock writes via a Python port of ``orchestration/lockfile.mjs:withLock``
(60s stale recovery, JSON-content ``acquired_at`` not mtime, read-back-verify
CAS pattern per Phase 9 inheritance).

Requirements closed:
  - LIVE-03 + SC-2: 7-day TTL boundary cases (fresh / stale / refetch trigger)
  - LIVE-03: cache writes acquire ``.fred-cache.lock`` for the duration of the write
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import freezegun
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _seed_cache(tmp_path: Path, fetched_at_iso: str) -> Path:
    """Write a minimal cache file used by all freezegun TTL boundary tests.

    Cache schema matches ``lib/fred_cache.py`` canonical shape pinned in
    ``12-PATTERNS.md`` (``schema_version: 1``, ``entries: {series_id: {...}}``).
    Money/rate fields are JSON STRINGS per D-19 money discipline.
    """
    cache_file = tmp_path / "fred_MORTGAGE30US.json"
    cache_file.write_text(
        json.dumps(
            {
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
            }
        )
    )
    return cache_file


def test_six_d_twenty_three_h_old_cache_is_fresh(tmp_path: Path) -> None:
    """LIVE-03 + SC-2 boundary: 6d 23h 59m -> fresh (strict-< TTL)."""
    from lib.fred_cache import is_fresh

    cache_file = _seed_cache(tmp_path, "2026-04-25T12:00:00Z")
    with freezegun.freeze_time("2026-05-02T11:59:59Z"):
        entry = json.loads(cache_file.read_text())["entries"]["MORTGAGE30US"]
        assert is_fresh(entry) is True


def test_seven_d_exactly_old_cache_is_stale(tmp_path: Path) -> None:
    """LIVE-03 + SC-2 boundary: exactly 7d -> stale (strict ``<`` means age == TTL
    triggers refetch). Documented in RESEARCH §Pitfall 2."""
    from lib.fred_cache import is_fresh

    cache_file = _seed_cache(tmp_path, "2026-04-25T12:00:00Z")
    with freezegun.freeze_time("2026-05-02T12:00:00Z"):
        entry = json.loads(cache_file.read_text())["entries"]["MORTGAGE30US"]
        assert is_fresh(entry) is False


def test_eight_d_old_cache_triggers_refetch(tmp_path: Path) -> None:
    """SC-2: 8d -> stale -> refetch path engages (``StaleCacheWarning`` emitted)."""
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


def test_cache_write_acquires_lock(tmp_path: Path) -> None:
    """LIVE-03 lock contract: cache writes hold the ``.fred-cache.lock`` for the
    duration of the write (Python port of ``orchestration/lockfile.mjs:withLock`` —
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


# ---------------------------------------------------------------------------
# Wave 2 integration tests for get_cached_or_fetch (no xfail — ship green)
# ---------------------------------------------------------------------------


def test_get_cached_or_fetch_returns_cached_when_fresh(tmp_path: Path) -> None:
    """Read-through: fresh cache → no fetcher invocation."""
    from lib.fred_cache import _save_cache, get_cached_or_fetch

    fresh_entry: dict[str, Any] = {
        "series_id": "MORTGAGE30US",
        "value": "6.84",
        "observation_date": "2026-04-25",
        "fetched_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_url": "https://...api_key=***...",
        "fred_realtime_start": "2026-04-26",
        "fred_realtime_end": "2026-04-26",
        "error": None,
    }
    _save_cache("MORTGAGE30US", fresh_entry, cache_dir=tmp_path)
    fetcher_calls: list[str] = []

    def stub_fetcher(sid: str) -> dict[str, Any]:
        fetcher_calls.append(sid)
        return {"series_id": sid, "value": "99.99", "error": None}

    result = get_cached_or_fetch("MORTGAGE30US", cache_dir=tmp_path, fetcher=stub_fetcher)
    assert fetcher_calls == []
    assert result["value"] == "6.84"


def test_get_cached_or_fetch_invokes_fetcher_when_stale(tmp_path: Path) -> None:
    """Read-through: stale cache → fetcher invoked exactly once + cache updated."""
    from lib.fred_cache import _save_cache, get_cached_or_fetch

    stale_entry: dict[str, Any] = {
        "series_id": "MORTGAGE30US",
        "value": "6.84",
        "observation_date": "2026-04-25",
        "fetched_at": "2026-04-25T12:00:00Z",
        "source_url": "...api_key=***...",
        "fred_realtime_start": "2026-04-26",
        "fred_realtime_end": "2026-04-26",
        "error": None,
    }
    _save_cache("MORTGAGE30US", stale_entry, cache_dir=tmp_path)
    fetcher_calls: list[str] = []

    def stub_fetcher(sid: str) -> dict[str, Any]:
        fetcher_calls.append(sid)
        return {
            "series_id": sid,
            "value": "6.92",
            "observation_date": "2026-05-03",
            "fetched_at": "2026-05-03T12:00:00Z",
            "source_url": "...api_key=***...",
            "fred_realtime_start": "2026-05-03",
            "fred_realtime_end": "2026-05-03",
            "error": None,
        }

    with freezegun.freeze_time("2026-05-03T12:00:01Z"):
        result = get_cached_or_fetch("MORTGAGE30US", cache_dir=tmp_path, fetcher=stub_fetcher)
    assert fetcher_calls == ["MORTGAGE30US"]
    assert result["value"] == "6.92"
    # Cache updated:
    reread = json.loads((tmp_path / "fred_MORTGAGE30US.json").read_text())
    assert reread["entries"]["MORTGAGE30US"]["value"] == "6.92"
