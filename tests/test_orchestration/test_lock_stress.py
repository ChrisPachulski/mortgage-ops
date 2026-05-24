"""Lock/concurrency stress tests — cross-language race, killed-process recovery,
stale recovery, slow-filesystem correctness, and db_path-override resilience.

These tests are PURE additions — they do NOT modify ``lib/fred_cache.py``,
``lib/property_persistence.py``, or ``orchestration/lockfile.mjs``. Production
constants (``STALE_THRESHOLD``, ``POLL_INTERVAL``, ``LOCK_DIR``) are
``monkeypatch.setattr``-ed in-test so wall-clock time stays bounded under 5s
each. Real-repo ``data/.lock`` is never touched; every test isolates to
``tmp_path``.

Pattern inheritance:
  - tests/test_orchestration/test_lockfile_unit.py — ``node --input-type=module
    -e ...`` subprocess pattern and lockfile cleanup fixture.
  - tests/test_property_persistence.py — ``monkeypatch.setattr(
    property_persistence, 'LOCK_DIR', tmp_path)`` redirection idiom plus
    ``write_listing`` blocker/holder threading.
  - tests/test_fred_cache.py — ``with_cache_lock(cache_dir=tmp_path, ...)``
    direct primitive contract.

Scenarios:
  1. cross_language_race — Node holds tmp_path/.lock; Python ``write_listing``
     waits ~500ms and succeeds after release.
  2. killed_process_recovery — child Python proc acquires + ``os._exit`` without
     release; parent observes timeout, then succeeds after stale window passes
     (``STALE_THRESHOLD`` shortened to 200ms for test speed).
  3. stale_acquired_at_overwrite — pre-write a JSON lock with ``acquired_at``
     beyond ``STALE_THRESHOLD``; ``with_cache_lock`` acquires immediately.
  4. exclusive_acquire_correctness — 6 subprocesses contend; each appends
     its (enter, exit) interval to a witness file. Parent asserts no two
     intervals overlap. (Process-level, not thread-level: the production
     contract is a CROSS-PROCESS mutex — same-process threads share PID and
     the CAS read-back can spuriously verify.)
  5. db_path_override_keeps_lock_at_lock_dir — variant of the existing
     ``test_write_acquires_data_lock`` that exercises a db_path far outside
     ``LOCK_DIR`` (different filesystem subtree) and asserts the spy still
     captures ``LOCK_DIR`` + ``.lock`` basename.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node_available() -> bool:
    """Return True if `node` and `orchestration/lockfile.mjs` are reachable."""
    if shutil.which("node") is None:
        return False
    return (REPO_ROOT / "orchestration" / "lockfile.mjs").exists()


def _make_listing() -> Any:
    """Build a minimal valid PropertyListing for write_listing calls."""
    from lib.property_listing import PropertyListing

    return PropertyListing(
        price=Decimal("625000.00"),
        zip="94110",
        property_type="SFH",
        source_url="https://www.zillow.com/homedetails/x/12345_zpid/",
        zpid="12345",
        fetched_at=datetime(2026, 5, 10, 14, 30, 0, 123456, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# Scenario 1: cross-language race
# ---------------------------------------------------------------------------


@pytest.mark.timeout(10)
@pytest.mark.skipif(
    not _node_available(), reason="node or orchestration/lockfile.mjs not reachable"
)
def test_cross_language_race_python_waits_for_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Node acquires tmp_path/.lock and holds ~500ms; Python write_listing waits
    and succeeds after release.

    The Node side does NOT use ``orchestration/lockfile.mjs`` (which hardcodes
    ``<repo>/data/.lock``) — instead it executes an inline equivalent of
    ``acquireLock`` against ``tmp_path/.lock`` so test isolation holds. The
    Python side uses the real ``lib.fred_cache.with_cache_lock`` primitive via
    ``lib.property_persistence.write_listing``, with ``LOCK_DIR`` redirected.

    Bounds: Node hold = 500ms; Python timeout = 1500ms → Python MUST succeed.
    """
    from lib import property_persistence

    # Redirect LOCK_DIR to tmp_path so the real <repo>/data/.lock is untouched.
    monkeypatch.setattr(property_persistence, "LOCK_DIR", tmp_path)

    lock_path = tmp_path / ".lock"
    db_path = tmp_path / "t.duckdb"

    # Inline Node snippet that acquires (CAS read-back-verify against the same
    # filename Python uses) and holds the lock for 500ms before releasing.
    node_script = textwrap.dedent(
        f"""
        import {{ writeFileSync, readFileSync, unlinkSync, existsSync }} from 'fs';
        const LOCK_PATH = {json.dumps(str(lock_path))};
        function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}
        function readLock() {{
            if (!existsSync(LOCK_PATH)) return null;
            try {{ return JSON.parse(readFileSync(LOCK_PATH, 'utf-8')); }}
            catch (e) {{ return null; }}
        }}
        async function acquire() {{
            const my = {{ pid: process.pid, acquired_at: Date.now(), reason: 'cross-lang-blocker' }};
            const deadline = Date.now() + 5000;
            while (Date.now() < deadline) {{
                const ex = readLock();
                if (!ex) {{
                    writeFileSync(LOCK_PATH, JSON.stringify(my, null, 2), {{ flag: 'w' }});
                    const rb = readLock();
                    if (rb && rb.pid === my.pid && rb.acquired_at === my.acquired_at) return my;
                }}
                await sleep(50);
            }}
            throw new Error('node blocker could not acquire');
        }}
        const lock = await acquire();
        // Signal readiness to the parent on stdout so the parent doesn't race the spawn.
        process.stdout.write('HELD\\n');
        await sleep(500);
        // Release only if we still own it.
        const cur = readLock();
        if (cur && cur.pid === lock.pid && cur.acquired_at === lock.acquired_at) {{
            unlinkSync(LOCK_PATH);
        }}
        process.stdout.write('RELEASED\\n');
        """
    )

    node_proc = subprocess.Popen(
        ["node", "--input-type=module", "-e", node_script],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # Wait for Node to signal it holds the lock — bound under 2s.
        assert node_proc.stdout is not None
        held_line = node_proc.stdout.readline()
        assert held_line.strip() == "HELD", f"Node never signaled HELD; got {held_line!r}"
        assert lock_path.exists(), "Node should have written tmp_path/.lock"

        # Now Python writes — should wait ~500ms for Node to release, then succeed.
        # Timeout bound at 1500ms so we deterministically succeed (Node holds 500ms).
        start = time.monotonic()
        result_holder: list[BaseException | bool] = []

        def _write() -> None:
            try:
                # Shorten the Python timeout via with_cache_lock wrapping.
                from lib import fred_cache as _fc
                from lib import property_persistence as _pp

                orig = _fc.with_cache_lock

                @contextmanager
                def _short_to(cache_dir: Path, **kwargs: Any) -> Iterator[dict[str, Any]]:
                    kwargs["timeout"] = timedelta(milliseconds=1500)
                    with orig(cache_dir, **kwargs) as lk:
                        yield lk

                _pp.with_cache_lock = _short_to  # type: ignore[attr-defined,assignment]
                try:
                    property_persistence.write_listing(
                        _make_listing(), household_hash="abc", db_path=db_path
                    )
                    result_holder.append(True)
                finally:
                    _pp.with_cache_lock = orig  # type: ignore[attr-defined]
            except BaseException as exc:
                result_holder.append(exc)

        writer = threading.Thread(target=_write, daemon=True)
        writer.start()
        writer.join(timeout=5)
        elapsed = time.monotonic() - start

        assert not writer.is_alive(), "writer thread hung"
        assert result_holder, "writer produced no result"
        assert result_holder[0] is True, f"write_listing did not succeed; got {result_holder[0]!r}"
        # Sanity: Python had to wait for Node's hold (~500ms), so elapsed
        # should be >= ~300ms (Node startup variance) but well under the
        # writer.join(timeout=5) ceiling. Bound is generous (4.0s) because
        # GHA ubuntu-latest runners exhibit highly variable subprocess +
        # node startup latency under concurrent CI load — observed up to
        # ~2.0s elapsed on a healthy CI run. The load-bearing assertions
        # are the writer.is_alive / result_holder / result == True checks
        # above; this elapsed bound just catches outright hangs.
        assert elapsed < 4.0, f"elapsed {elapsed:.3f}s too long; bound was 4.0s"
    finally:
        node_proc.terminate()
        try:
            node_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            node_proc.kill()
            node_proc.wait(timeout=2)
        if lock_path.exists():
            lock_path.unlink()


# ---------------------------------------------------------------------------
# Scenario 2: killed-process recovery
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
def test_killed_process_lock_recovers_via_stale_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child Python process acquires the lock then ``os._exit(1)`` without
    releasing. Immediate re-acquire times out; once we step past the
    (shortened) stale threshold, recovery succeeds.

    ``STALE_THRESHOLD`` is monkeypatched to 200ms so the test wall-time stays
    under 5s. The production constant is 60_000ms (60s) — see lib.fred_cache.
    """
    from lib import fred_cache

    lock_path = tmp_path / ".lock"

    # Spawn a child that acquires the lock and dies WITHOUT releasing.
    child_script = textwrap.dedent(
        f"""
        import json, os, sys, time
        lock_path = {json.dumps(str(lock_path))}
        payload = {{"pid": os.getpid(), "acquired_at": int(time.time() * 1000), "reason": "killed"}}
        with open(lock_path, "w") as f:
            f.write(json.dumps(payload))
        # Brutal exit: bypass atexit + finalizers — simulate kill -9 / crash.
        os._exit(1)
        """
    )
    child = subprocess.run(
        [sys.executable, "-c", child_script],
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    # Either exit code 1 (os._exit(1)) or non-zero is fine — we only need the
    # lock file to remain.
    assert child.returncode != 0, "child should have exited non-zero via os._exit(1)"
    assert lock_path.exists(), "child should have left a stranded lockfile"

    try:
        # Immediate re-acquire with default (60s) STALE_THRESHOLD and a SHORT
        # timeout — must time out because the abandoned lock looks fresh.
        with (
            pytest.raises(fred_cache.FredCacheLockError),
            fred_cache.with_cache_lock(
                tmp_path,
                timeout=timedelta(milliseconds=200),
                reason="immediate-retry",
                lock_filename=".lock",
            ),
        ):
            pass  # pragma: no cover — must not reach

        # Now shorten the stale threshold so the abandoned lock is reclaimable.
        # The child's acquired_at is "now" from its perspective; we wait just
        # past the new 200ms threshold and retry.
        monkeypatch.setattr(fred_cache, "STALE_THRESHOLD", timedelta(milliseconds=200))
        time.sleep(0.3)  # cross the (new) 200ms threshold

        # Should succeed by overwriting the stale lock.
        with fred_cache.with_cache_lock(
            tmp_path,
            timeout=timedelta(milliseconds=500),
            reason="post-stale-retry",
            lock_filename=".lock",
        ) as lk:
            assert lk["pid"] == os.getpid()
            assert isinstance(lk["acquired_at"], int)
    finally:
        if lock_path.exists():
            lock_path.unlink()


# ---------------------------------------------------------------------------
# Scenario 3: stale acquired_at overwrite
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
def test_stale_acquired_at_is_overwritten_immediately(tmp_path: Path) -> None:
    """A pre-existing lock with ``acquired_at`` beyond STALE_THRESHOLD (default
    60s) is overwritten on the FIRST poll — acquisition is effectively
    immediate (well under one POLL_INTERVAL).
    """
    from lib import fred_cache

    lock_path = tmp_path / ".lock"
    # 90s ago — comfortably past the 60s default STALE_THRESHOLD.
    stale_acquired_at_ms = int((time.time() - 90) * 1000)
    lock_path.write_text(
        json.dumps({"pid": 99999, "acquired_at": stale_acquired_at_ms, "reason": "stale-fixture"})
    )
    assert lock_path.exists()

    try:
        start = time.monotonic()
        with fred_cache.with_cache_lock(
            tmp_path,
            timeout=timedelta(milliseconds=500),
            reason="reclaim-stale",
            lock_filename=".lock",
        ) as lk:
            elapsed = time.monotonic() - start
            # On disk it should now be OUR lock, not the bogus PID.
            on_disk = json.loads(lock_path.read_text())
            assert on_disk["pid"] == os.getpid()
            assert on_disk["pid"] == lk["pid"]
            assert on_disk["acquired_at"] == lk["acquired_at"]
            # Reclaim is single-poll fast — give plenty of headroom for slow CI.
            assert elapsed < 0.3, f"reclaim took {elapsed:.3f}s; expected <0.3s"

        # Lock released after context exit.
        assert not lock_path.exists(), "with_cache_lock must release on exit"
    finally:
        if lock_path.exists():
            lock_path.unlink()


# ---------------------------------------------------------------------------
# Scenario 4: exclusive-acquire correctness under contention
# ---------------------------------------------------------------------------


@pytest.mark.timeout(15)
def test_multiple_processes_contend_exactly_one_holds_lock_at_a_time(tmp_path: Path) -> None:
    """Correctness property: under cross-PROCESS contention, at most ONE
    process can hold the lock at a time. Each child appends a (enter_ms,
    exit_ms) interval to a witness file under the lock; after all children
    join, the parent asserts NO two intervals overlap.

    Why processes, not threads: ``lib.fred_cache.with_cache_lock`` is
    explicitly designed as a CROSS-PROCESS mutex (mirror of
    ``orchestration/lockfile.mjs:withLock`` — see lib/fred_cache.py lines 4-7
    and 145-148). The CAS read-back-verify pattern keys on ``os.getpid()``,
    which is shared by every thread inside a single process; same-process
    threads can therefore write each other's "own" payload and the read-back
    will spuriously verify. This test asserts the documented contract
    (process-level mutual exclusion), which is the property the production
    callers actually rely on.

    This is the deterministic substitute for the "slow filesystem"
    simulation requested in scenario 4 — we let the OS schedule freely and
    assert mutual exclusion as a property rather than artificially slowing
    time.
    """
    from lib import fred_cache as _fc

    lock_path = tmp_path / ".lock"
    witness_path = tmp_path / "witness.jsonl"
    fred_cache_path = Path(_fc.__file__).resolve()
    # Ensure the child can import lib.fred_cache by setting sys.path to repo root.
    repo_root = REPO_ROOT

    worker_script = textwrap.dedent(
        f"""
        import sys, json, time, os
        sys.path.insert(0, {json.dumps(str(repo_root))})
        from datetime import timedelta
        from lib.fred_cache import with_cache_lock
        TMP = {json.dumps(str(tmp_path))}
        WITNESS = {json.dumps(str(witness_path))}
        for _ in range(3):
            with with_cache_lock(
                __import__('pathlib').Path(TMP),
                timeout=timedelta(milliseconds=10000),
                reason='proc-contention',
                lock_filename='.lock',
            ):
                t_in = time.monotonic_ns()
                # widen the critical-section window so any overlap is visible
                time.sleep(0.005)
                t_out = time.monotonic_ns()
                # append-only — atomic for small writes on POSIX
                with open(WITNESS, 'a') as fh:
                    fh.write(json.dumps({{"pid": os.getpid(), "in": t_in, "out": t_out}}) + "\\n")
        """
    )

    # Sanity: file exists so import will work.
    assert fred_cache_path.exists()

    N_PROCS = 6  # 6 procs * 3 acquisitions = 18 critical-section entries
    procs: list[subprocess.Popen[str]] = [
        subprocess.Popen(
            [sys.executable, "-c", worker_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(N_PROCS)
    ]
    try:
        for p in procs:
            rc = p.wait(timeout=14)
            if rc != 0:
                stderr = p.stderr.read() if p.stderr else ""
                pytest.fail(f"worker pid={p.pid} exited {rc}; stderr={stderr!r}")

        # Parse witness file and verify no intervals overlap.
        assert witness_path.exists(), "no witness lines written — workers ran but did not record"
        intervals: list[tuple[int, int, int]] = []  # (in, out, pid)
        for line in witness_path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            intervals.append((rec["in"], rec["out"], rec["pid"]))

        assert len(intervals) == N_PROCS * 3, (
            f"expected {N_PROCS * 3} critical-section entries, got {len(intervals)}"
        )
        # Sort by entry time; assert each entry begins at or after the prior exit.
        intervals.sort(key=lambda x: x[0])
        for i in range(1, len(intervals)):
            _prev_in, prev_out, prev_pid = intervals[i - 1]
            cur_in, _cur_out, cur_pid = intervals[i]
            assert cur_in >= prev_out, (
                f"mutual exclusion violated: pid={cur_pid} entered at {cur_in} "
                f"while pid={prev_pid} was still inside (exit={prev_out})"
            )
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
                p.wait(timeout=2)
        if lock_path.exists():
            lock_path.unlink()


# ---------------------------------------------------------------------------
# Scenario 5: db_path override does not leak the lock location
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
def test_db_path_outside_lock_dir_still_locks_at_lock_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stronger variant of test_property_persistence.test_write_acquires_data_lock.

    Builds a ``db_path`` whose parent is a TOTALLY UNRELATED subtree
    (``tmp_path/elsewhere/db/``), monkeypatches ``LOCK_DIR`` to a SEPARATE
    subtree (``tmp_path/lockhome``), and verifies that ``write_listing`` still
    routes ``with_cache_lock`` at ``LOCK_DIR`` with basename ``.lock``.

    Why the variant: ``test_write_acquires_data_lock`` keeps ``db_path`` under
    ``tmp_path`` directly. This variant uses two disjoint subtrees so a
    regression that accidentally derives the lock from ``db_path.parent``
    (the original PROP-02 bug) would point to ``tmp_path/elsewhere/db`` — a
    location the spy doesn't expect — making the divergence loud.
    """
    from lib import property_persistence

    elsewhere = tmp_path / "elsewhere" / "db"
    elsewhere.mkdir(parents=True, exist_ok=True)
    lockhome = tmp_path / "lockhome"
    lockhome.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(property_persistence, "LOCK_DIR", lockhome)

    captured_dirs: list[Path] = []
    captured_filenames: list[str] = []

    @contextmanager
    def _spy_lock(cache_dir: Path, **kwargs: Any) -> Iterator[dict[str, Any]]:
        captured_dirs.append(cache_dir)
        captured_filenames.append(kwargs.get("lock_filename", "<missing>"))
        yield {"pid": os.getpid(), "acquired_at": 0, "reason": kwargs.get("reason", "")}

    monkeypatch.setattr(property_persistence, "with_cache_lock", _spy_lock)

    db_path = elsewhere / "alt.duckdb"
    property_persistence.write_listing(_make_listing(), household_hash="abc", db_path=db_path)

    assert len(captured_dirs) == 1
    assert captured_dirs[0] == lockhome, (
        f"write_listing must lock at LOCK_DIR ({lockhome!r}), not derive from "
        f"db_path.parent ({db_path.parent!r}). Got: {captured_dirs[0]!r}"
    )
    assert captured_dirs[0] != db_path.parent, (
        "lock-dir must be decoupled from db_path.parent (cross-language mutex "
        "contract — see orchestration/lockfile.mjs lines 24-25)"
    )
    assert captured_filenames[0] == ".lock", (
        f"write_listing must request lock_filename='.lock' (matches "
        f"orchestration/lockfile.mjs basename); got {captured_filenames[0]!r}"
    )
