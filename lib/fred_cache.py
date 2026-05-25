"""FRED response cache with 7-day TTL + cross-process lock (Phase 12 SC-2 + LIVE-03).

Single source of truth for FRED cache reads/writes. Mirrors:
  - ``lib.rules._loader.StaleReferenceWarning`` — staleness warning idiom (here at 7d,
    not 12mo)
  - ``orchestration/lockfile.mjs`` — same lockfile shape and stale-recovery timing,
    with Python-side atomic creation to avoid partial lock reads

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
    fetched_at_str = entry.get("fetched_at")
    if not isinstance(fetched_at_str, str):
        return False
    try:
        fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
    except ValueError:
        return False
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
        result: Any = json.loads(lock_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(result, dict):
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


def _write_lock_exclusive(lock_path: Path, lock: dict[str, Any]) -> bool:
    """Create ``lock_path`` only if absent and write the JSON lock body."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd: int | None = None
    try:
        fd = os.open(lock_path, flags, 0o644)
    except FileExistsError:
        return False

    try:
        with os.fdopen(fd, "w") as fh:
            fd = None
            json.dump(lock, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError:
        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()
        raise
    finally:
        if fd is not None:
            os.close(fd)
    return True


def _lock_token_matches(left: dict[str, Any] | None, right: dict[str, Any]) -> bool:
    """Compare the ownership token fields used by release/stale recovery."""
    return (
        left is not None
        and left.get("pid") == right.get("pid")
        and left.get("acquired_at") == right.get("acquired_at")
    )


def _try_remove_stale_lock(lock_path: Path, stale_lock: dict[str, Any]) -> bool:
    """Remove a stale lock only while holding a local recovery guard."""
    guard_path = lock_path.with_name(f"{lock_path.name}.stale-recovery")
    guard = {
        "pid": os.getpid(),
        "acquired_at": _now_ms(),
        "reason": f"stale recovery for {lock_path.name}",
    }
    if not _write_lock_exclusive(guard_path, guard):
        existing_guard = _read_lock(guard_path)
        if not _is_lock_stale(existing_guard):
            return False
        with contextlib.suppress(FileNotFoundError):
            guard_path.unlink()
        if not _write_lock_exclusive(guard_path, guard):
            return False
    try:
        current = _read_lock(lock_path)
        if not (_is_lock_stale(current) and _lock_token_matches(current, stale_lock)):
            return False
        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()
        return True
    finally:
        with contextlib.suppress(FileNotFoundError):
            guard_path.unlink()


def _try_remove_unreadable_lock(lock_path: Path) -> bool:
    """Remove an existing unreadable lock only while holding a local recovery guard."""
    guard_path = lock_path.with_name(f"{lock_path.name}.stale-recovery")
    guard = {
        "pid": os.getpid(),
        "acquired_at": _now_ms(),
        "reason": f"unreadable lock recovery for {lock_path.name}",
    }
    if not _write_lock_exclusive(guard_path, guard):
        existing_guard = _read_lock(guard_path)
        if not _is_lock_stale(existing_guard):
            return False
        with contextlib.suppress(FileNotFoundError):
            guard_path.unlink()
        if not _write_lock_exclusive(guard_path, guard):
            return False
    try:
        if not lock_path.exists() or _read_lock(lock_path) is not None:
            return False
        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()
        return True
    finally:
        with contextlib.suppress(FileNotFoundError):
            guard_path.unlink()


def _acquire_lock(
    cache_dir: Path,
    *,
    timeout: timedelta = DEFAULT_TIMEOUT,
    reason: str = "",
    lock_filename: str = LOCK_FILENAME,
) -> dict[str, Any]:
    """Acquire the lockfile with atomic create plus stale-lock recovery.

    Returns the lock JSON if acquired; raises ``FredCacheLockError`` on timeout.

    ``lock_filename`` defaults to ``.fred-cache.lock`` (FRED cache contract).
    The DuckDB writer (``lib.property_persistence.write_listing``) passes
    ``.lock`` instead so it serializes against ``orchestration/lockfile.mjs``
    (the Node writer's ``data/.lock``). Both filename choices preserve the
    same 60s stale recovery / 100ms poll semantics; only the file basename
    changes.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    lock_path = cache_dir / lock_filename
    deadline_ms = _now_ms() + int(timeout.total_seconds() * 1000)

    while _now_ms() < deadline_ms:
        existing = _read_lock(lock_path)
        lock_exists = lock_path.exists()
        if existing is None and lock_exists:
            _try_remove_unreadable_lock(lock_path)
        if existing is None or _is_lock_stale(existing):
            my_lock: dict[str, Any] = {
                "pid": os.getpid(),
                "acquired_at": _now_ms(),
                "reason": reason,
            }
            if existing is not None and _is_lock_stale(existing):
                _try_remove_stale_lock(lock_path, existing)
            try:
                if _write_lock_exclusive(lock_path, my_lock):
                    return my_lock
            except OSError:
                pass
        time.sleep(POLL_INTERVAL)

    blocker = _read_lock(lock_path)
    raise FredCacheLockError(
        f"Lock acquire timeout after {timeout.total_seconds():.0f}s. Blocker: {json.dumps(blocker)}"
    )


def _release_lock(
    cache_dir: Path,
    my_lock: dict[str, Any],
    *,
    lock_filename: str = LOCK_FILENAME,
) -> None:
    """Mirror ``orchestration/lockfile.mjs:releaseLock`` — only unlink if we own it.

    ``lock_filename`` MUST match the value passed to ``_acquire_lock`` for the
    same lock; ``with_cache_lock`` threads this through automatically.
    """
    lock_path = cache_dir / lock_filename
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
    lock_filename: str = LOCK_FILENAME,
) -> Iterator[dict[str, Any]]:
    """Context manager: acquire lock, yield lock JSON, release on exit.

    Mirror ``orchestration/lockfile.mjs:withLock``. Always releases even on
    exception.

    ``lock_filename`` defaults to ``.fred-cache.lock`` so FRED-cache callers
    are unchanged. ``lib.property_persistence.write_listing`` overrides this
    to ``.lock`` to share the Node writer's mutex
    (``orchestration/lockfile.mjs:LOCK_PATH = data/.lock``). Stale-recovery /
    poll semantics are identical regardless of filename.

    Raises:
        FredCacheLockError: if acquisition times out.
    """
    lock = _acquire_lock(
        cache_dir,
        timeout=timeout,
        reason=reason,
        lock_filename=lock_filename,
    )
    try:
        yield lock
    finally:
        _release_lock(cache_dir, lock, lock_filename=lock_filename)


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
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != SCHEMA_VERSION:
        return None
    entries = payload.get("entries", {})
    if not isinstance(entries, dict):
        return None
    entry = entries.get(series_id)
    # CR-01: shape-validate before returning. A malformed entry (missing
    # ``fetched_at`` or ``value``) used to raise ``KeyError`` deep inside
    # ``is_fresh`` → traceback out of ``fred_cli.py:main()`` → non-zero exit,
    # breaking D-12-LIVE02-01 + Pitfall 1 (always-exit-0 envelope contract).
    # Returning ``None`` here falls through to the fetcher refetch path.
    if (
        isinstance(entry, dict)
        and all(k in entry for k in REQUIRED_ENTRY_FIELDS)
        and isinstance(entry.get("fetched_at"), str)
        and isinstance(entry.get("value"), str)
    ):
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
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp_path.write_text(json.dumps(payload, indent=2))
            os.replace(tmp_path, path)
        finally:
            with contextlib.suppress(FileNotFoundError):
                tmp_path.unlink()


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
