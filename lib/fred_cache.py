"""FRED response cache with 7-day TTL + cross-process lock (Phase 12 SC-2 + LIVE-03).

Single source of truth for FRED cache reads/writes. Mirrors:
  - ``lib.rules._loader.StaleReferenceWarning`` — staleness warning idiom (here at 7d,
    not 12mo)
  - ``orchestration/lockfile.mjs`` — Python port of the read-back-verify CAS lockfile
    (60s stale recovery, JSON-content ``acquired_at`` NOT mtime, NOT O_EXCL per D-01-01)

Strict ``<`` TTL boundary per D-12-LIVE02-01 + RESEARCH §Pitfall 2:
  - 6d 23h 59m old → fresh (no refetch)
  - 7d 0h 0s old → stale (refetch)
  - 8d old → stale (refetch)

Cache file layout: ``data/cache/fred_{series_id}.json`` (one file per series per
D-12-LIVE02-01 SKILL.md citations). Schema wraps entries in ``entries`` dict so a
future consolidation pass would be byte-compatible with RESEARCH §Pattern 2.

The lock at ``data/cache/.fred-cache.lock`` is gitignored per Plan 12-00 .gitignore
entry. Cross-process serialization at the cache-dir granularity (not per-series)
because the lock file is shared; concurrent fetches for different series_ids
serialize through the same lock — acceptable since FRED fetches are 10s-bounded
and rare (cache-first path makes the cold-fetch path the exception).
"""

from __future__ import annotations

import contextlib
import json
import os
import time
import warnings
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# ---------------------------------------------------------------------------
# Constants — PINNED by 12-RESEARCH.md + D-12-LIVE02-01
# ---------------------------------------------------------------------------

CACHE_DIR: Final[Path] = Path(__file__).parent.parent / "data" / "cache"
"""Repo-relative: ``<repo_root>/data/cache/``. ``lib/`` is one level deep from repo root."""

CACHE_TTL: Final[timedelta] = timedelta(days=7)
"""SC-2 + D-12-LIVE02-01: FRED publishes weekly (Thursday noon ET);
7-day TTL strict-``<`` boundary means age == 7d EXACTLY counts as stale."""

LOCK_FILENAME: Final[str] = ".fred-cache.lock"
STALE_THRESHOLD: Final[timedelta] = timedelta(milliseconds=60_000)
"""Mirror orchestration/lockfile.mjs:STALE_THRESHOLD_MS = 60_000."""

DEFAULT_TIMEOUT: Final[timedelta] = timedelta(milliseconds=30_000)
"""Mirror orchestration/lockfile.mjs:DEFAULT_TIMEOUT_MS = 30_000."""

POLL_INTERVAL: Final[float] = 0.1
"""Mirror orchestration/lockfile.mjs:POLL_INTERVAL_MS = 100ms."""

SCHEMA_VERSION: Final[int] = 1
"""Bump if the cache JSON shape changes; Plan 12-02 ships ``schema_version=1``."""

REQUIRED_ENTRY_FIELDS: Final[tuple[str, ...]] = ("value", "fetched_at")
"""Minimum fields an entry must carry for ``is_fresh`` to succeed.

A cache file whose entry is missing one of these is treated as malformed and
returned as ``None`` from ``_load_cache`` (falling through to the fetcher path
per CR-01 — see ``get_cached_or_fetch``). Defending in ``_load_cache`` keeps
``is_fresh`` simple and matches the "shape-validate on read" pattern in
``_read_lock``."""


# ---------------------------------------------------------------------------
# Exceptions / Warnings
# ---------------------------------------------------------------------------


class StaleCacheWarning(UserWarning):
    """Emitted when a FRED cache entry's ``fetched_at`` is more than 7 days old.

    Mirrors ``lib.rules._loader.StaleReferenceWarning`` idiom (12-month threshold
    there; 7-day threshold here per SC-2 + D-12-LIVE02-01). Loud-by-default;
    never suppressed by library code. Tests use
    ``pytest.warns(StaleCacheWarning)`` to assert.
    """


class FredCacheLockError(RuntimeError):
    """Raised when ``with_cache_lock`` cannot acquire ``.fred-cache.lock`` within
    the timeout window (default 30s; same as
    ``orchestration/lockfile.mjs:DEFAULT_TIMEOUT_MS``). Carries the blocker JSON
    envelope in ``str(exc)`` for debugging."""


class FredCacheSchemaError(ValueError):
    """Raised when a cache file's ``schema_version`` is missing or unrecognized.
    Caller (``get_cached_or_fetch``) treats as missing-cache and falls through
    to fetch."""


# ---------------------------------------------------------------------------
# TTL / freshness
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    """Wallclock UTC — single seam for freezegun freezing across tests."""
    return datetime.now(UTC)


def is_fresh(entry: dict[str, Any]) -> bool:
    """SC-2: returns True iff ``(now - fetched_at) < 7 days`` (strict less-than).

    Per RESEARCH §Pitfall 2: 6d23h59m fresh; 7d exact stale; 8d stale.
    ``fetched_at`` MUST be an ISO-8601 string with ``Z`` suffix or ``+00:00``
    offset.
    """
    fetched_at_str: str = entry["fetched_at"]
    fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
    age = _now_utc() - fetched_at
    return age < CACHE_TTL


def warn_if_stale(entry: dict[str, Any]) -> None:
    """Emit ``StaleCacheWarning`` if the entry is stale; no-op if fresh.

    Loud-by-default per project convention (mirrors ``StaleReferenceWarning``).
    Callers can suppress via ``warnings.catch_warnings()``; library never
    suppresses.
    """
    if is_fresh(entry):
        return
    fetched_at = entry.get("fetched_at", "<missing>")
    series_id = entry.get("series_id") or entry.get("_series_id_hint", "<unknown>")
    warnings.warn(
        f"FRED cache entry for {series_id!r} has fetched_at={fetched_at}, "
        f"which is more than {CACHE_TTL.days} days old. Refetch recommended.",
        category=StaleCacheWarning,
        stacklevel=2,
    )


# ---------------------------------------------------------------------------
# Lockfile (Python port of orchestration/lockfile.mjs)
# ---------------------------------------------------------------------------


def _now_ms() -> int:
    """Epoch milliseconds — mirror Node's ``Date.now()`` for ``lockfile.mjs`` parity."""
    return int(time.time() * 1000)


def _read_lock(lock_path: Path) -> dict[str, Any] | None:
    """Return parsed lock JSON, or ``None`` if absent / corrupt."""
    if not lock_path.exists():
        return None
    try:
        result: dict[str, Any] = json.loads(lock_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return result


def _is_lock_stale(lock: dict[str, Any] | None) -> bool:
    """Mirror ``orchestration/lockfile.mjs:isStale`` — ``acquired_at``-based.

    Returns True if lock is ``None``, missing/non-numeric ``acquired_at``, or
    older than ``STALE_THRESHOLD`` (60s).
    """
    if not lock or not isinstance(lock.get("acquired_at"), (int, float)):
        return True
    age_ms = _now_ms() - int(lock["acquired_at"])
    return age_ms > STALE_THRESHOLD.total_seconds() * 1000


def _acquire_lock(
    cache_dir: Path,
    *,
    timeout: timedelta = DEFAULT_TIMEOUT,
    reason: str = "",
) -> dict[str, Any]:
    """Mirror ``orchestration/lockfile.mjs:acquireLock`` — read-back-and-verify CAS.

    Returns the lock JSON if acquired; raises ``FredCacheLockError`` on timeout.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    lock_path = cache_dir / LOCK_FILENAME
    deadline_ms = _now_ms() + int(timeout.total_seconds() * 1000)

    while _now_ms() < deadline_ms:
        existing = _read_lock(lock_path)
        if existing is None or _is_lock_stale(existing):
            my_lock: dict[str, Any] = {
                "pid": os.getpid(),
                "acquired_at": _now_ms(),
                "reason": reason,
            }
            try:
                # flag='w' equivalent (NOT O_EXCL — per lockfile.mjs:12 header rationale).
                lock_path.write_text(json.dumps(my_lock, indent=2))
                # Read-back-verify CAS.
                read_back = _read_lock(lock_path)
                if (
                    read_back is not None
                    and read_back.get("pid") == my_lock["pid"]
                    and read_back.get("acquired_at") == my_lock["acquired_at"]
                ):
                    return my_lock
            except OSError:
                # Race: another process wrote between read and write. Retry.
                pass
        time.sleep(POLL_INTERVAL)

    blocker = _read_lock(lock_path)
    raise FredCacheLockError(
        f"Lock acquire timeout after {timeout.total_seconds():.0f}s. Blocker: {json.dumps(blocker)}"
    )


def _release_lock(cache_dir: Path, my_lock: dict[str, Any]) -> None:
    """Mirror ``orchestration/lockfile.mjs:releaseLock`` — only unlink if we own it."""
    lock_path = cache_dir / LOCK_FILENAME
    existing = _read_lock(lock_path)
    if (
        existing is not None
        and existing.get("pid") == my_lock.get("pid")
        and existing.get("acquired_at") == my_lock.get("acquired_at")
    ):
        with contextlib.suppress(FileNotFoundError):
            # already gone — fine
            lock_path.unlink()


@contextmanager
def with_cache_lock(
    cache_dir: Path = CACHE_DIR,
    *,
    timeout: timedelta = DEFAULT_TIMEOUT,
    reason: str = "",
) -> Iterator[dict[str, Any]]:
    """Context manager: acquire lock, yield lock JSON, release on exit.

    Mirror ``orchestration/lockfile.mjs:withLock``. Always releases even on
    exception.

    Raises:
        FredCacheLockError: if acquisition times out.
    """
    lock = _acquire_lock(cache_dir, timeout=timeout, reason=reason)
    try:
        yield lock
    finally:
        _release_lock(cache_dir, lock)


# ---------------------------------------------------------------------------
# Read-through cache
# ---------------------------------------------------------------------------


def _cache_path(series_id: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Per-series file: ``data/cache/fred_{series_id}.json`` (D-12-LIVE02-01)."""
    return cache_dir / f"fred_{series_id}.json"


def _load_cache(series_id: str, cache_dir: Path = CACHE_DIR) -> dict[str, Any] | None:
    """Return the cached entry for ``series_id``, or ``None`` if absent / schema-invalid."""
    path = _cache_path(series_id, cache_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != SCHEMA_VERSION:
        return None
    entries = payload.get("entries", {})
    entry = entries.get(series_id)
    # CR-01: shape-validate before returning. A malformed entry (missing
    # ``fetched_at`` or ``value``) used to raise ``KeyError`` deep inside
    # ``is_fresh`` → traceback out of ``fred_cli.py:main()`` → non-zero exit,
    # breaking D-12-LIVE02-01 + Pitfall 1 (always-exit-0 envelope contract).
    # Returning ``None`` here falls through to the fetcher refetch path.
    if isinstance(entry, dict) and all(k in entry for k in REQUIRED_ENTRY_FIELDS):
        result: dict[str, Any] = entry
        return result
    return None


def _save_cache(
    series_id: str,
    entry: dict[str, Any],
    cache_dir: Path = CACHE_DIR,
) -> None:
    """Write a single-series cache file under ``with_cache_lock``.
    ``schema_version`` is pinned."""
    path = _cache_path(series_id, cache_dir)
    with with_cache_lock(cache_dir, reason=f"write {series_id}"):
        payload = {"schema_version": SCHEMA_VERSION, "entries": {series_id: entry}}
        path.write_text(json.dumps(payload, indent=2))


def get_cached_or_fetch(
    series_id: str,
    *,
    cache_dir: Path = CACHE_DIR,
    fetcher: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read-through cache.

    1. If cache file exists AND entry is fresh (<7d) → return entry (no fetch).
    2. Else invoke ``fetcher(series_id)`` → return its envelope and write
       through if value present.

    Fetcher contract:
      - Takes ``series_id`` ``str``.
      - Returns a ``dict`` with at minimum a ``value`` field (``str|None``) and
        ``error`` field (``str|None``).
      - MUST NEVER raise; failure modes are envelope-encoded.
      - Default fetcher (when ``fetcher=None``) raises ``NotImplementedError`` —
        ``fred_cli.py`` injects its own urllib-based fetcher; ``lib.fred_cache``
        stays pure.

    Returns the envelope dict.

    Raises:
      - ``NotImplementedError`` — when ``fetcher`` is ``None`` and the cache
        is cold/stale. Callers (``fred_cli.py``) always inject a fetcher.
      - ``FredCacheLockError`` — when ``_save_cache`` cannot acquire
        ``.fred-cache.lock`` within 30s. Caller is responsible for catching
        and converting to an error envelope per the D-12-LIVE02-01 always-
        exit-0 contract; ``fred_cli.py:main()`` does this via an outermost
        ``try/except Exception`` (CR-02).
      - ``OSError`` / ``PermissionError`` — from ``Path.write_text`` in
        ``_save_cache`` or ``cache_dir.mkdir`` in ``_acquire_lock``. Same
        upstream-catch contract as above.

    Note: CR-01 fixed a prior ``KeyError`` path from malformed cache entries;
    ``_load_cache`` now returns ``None`` for shape-invalid entries instead.
    """
    entry = _load_cache(series_id, cache_dir)
    if entry is not None and is_fresh(entry):
        return entry

    if fetcher is None:
        raise NotImplementedError(
            "lib.fred_cache.get_cached_or_fetch requires a fetcher; "
            "scripts/fred_cli.py injects its urllib-based fetcher."
        )

    new_entry = fetcher(series_id)
    # Only write through if the fetch produced a real value (not an error envelope).
    if isinstance(new_entry, dict) and new_entry.get("value") is not None:
        _save_cache(series_id, new_entry, cache_dir)
    return new_entry
