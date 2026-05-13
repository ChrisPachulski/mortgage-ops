"""Phase 12 Wave-1 live tests for .claude/skills/mortgage-ops/scripts/fred_cli.py.

LIVE-01 + LIVE-04 closed: HTTP wrapper canonical path per D-12-LIVE01-01.
Always-exit-0 envelope per Pitfall 1 + D-12-LIVE02-01 recovery contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "fred_cli.py"
)
"""Phase 12 ships fred_cli.py directly into .claude/skills/mortgage-ops/scripts/
(no project-root -> skill-folder relocation pass — D-12-LIVE01-01 + RESEARCH
§Architectural Responsibility Map). Mirrors Phase 10-relocated SCRIPT_PATH
pattern in tests/test_amortize.py."""

ALL_SERIES = ("MORTGAGE30US", "MORTGAGE15US")
"""Allowlist per RESEARCH §Security Domain V5 - reject other series_id values
to defend against URL parameter injection."""


def test_fred_cli_script_exists() -> None:
    """LIVE-01: scripts/fred_cli.py must exist at .claude/skills/mortgage-ops/scripts/."""
    assert SCRIPT_PATH.is_file(), f"missing {SCRIPT_PATH}"


def test_fred_cli_help_fast_lazy_imports() -> None:
    """LIVE-01: --help must complete in <300ms (lazy-import of urllib + lib.fred_cache
    after argparse)."""
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert elapsed < 0.3, f"--help took {elapsed:.3f}s; D-18 lazy-import discipline violated"


def test_fred_cli_missing_api_key_returns_exit_0_with_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LIVE-01 + Pitfall 1: missing FRED_API_KEY -> exit 0 + JSON envelope with `error` field.

    Diverges from amortize.py exit-2 pattern: SKILL.md prose-only injection per
    D-12-LIVE02-01 requires the recovery contract to be the envelope's `error` field,
    not a non-zero exit.
    """
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "MORTGAGE30US", "--latest"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0  # NOT 2 — see D-12-LIVE02-01 recovery contract
    envelope = json.loads(result.stdout)
    assert envelope["value"] is None
    assert envelope["error"] is not None
    assert "FRED_API_KEY" in envelope["error"]


@pytest.mark.parametrize("series_id", ALL_SERIES)
def test_fred_cli_supports_both_series(series_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """LIVE-04: MORTGAGE15US must be accepted alongside MORTGAGE30US (allowlist of 2)."""
    monkeypatch.delenv("FRED_API_KEY", raising=False)  # don't actually hit FRED
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), series_id, "--latest"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    envelope = json.loads(result.stdout)
    assert envelope["series_id"] == series_id


# ---------------------------------------------------------------------------
# CR-02 regression: cache-layer exceptions must be caught and converted to
# the always-exit-0 envelope per D-12-LIVE02-01 + Pitfall 1.
# ---------------------------------------------------------------------------


def _run_cli_with_mocked_save_cache(exc_class: str, exc_args_repr: str) -> dict[str, object]:
    """Invoke ``fred_cli.main()`` in a subprocess with ``lib.fred_cache._save_cache``
    patched to raise the named exception. Returns the parsed JSON envelope.

    Uses a subprocess + ``importlib.util`` script-loader so SKILL.md's path
    surgery (parents[4] = repo root) executes verbatim. Monkeypatches
    ``lib.fred_cache.get_cached_or_fetch`` to invoke a fetcher that returns a
    valid envelope, then has ``_save_cache`` raise — exercising the
    write-through error path that CR-02 closes.
    """
    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json, os\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        "os.environ['FRED_API_KEY'] = 'test-key-not-real'\n"
        # Pre-import lib.fred_cache so we can patch _save_cache BEFORE
        # the CLI's lazy import resolves it.
        "import lib.fred_cache as fc\n"
        f"def _raise(*a, **kw):\n"
        f"    raise {exc_class}({exc_args_repr})\n"
        "fc._save_cache = _raise\n"
        # Patch the fetcher path indirectly: replace get_cached_or_fetch with
        # a wrapper that runs the supplied fetcher and then invokes _save_cache
        # (now mocked to raise).\n"
        "_real = fc.get_cached_or_fetch\n"
        "def _patched(series_id, *, cache_dir=fc.CACHE_DIR, fetcher=None):\n"
        "    if fetcher is None:\n"
        "        raise NotImplementedError\n"
        "    new_entry = fetcher(series_id)\n"
        "    if isinstance(new_entry, dict) and new_entry.get('value') is not None:\n"
        "        fc._save_cache(series_id, new_entry, cache_dir)\n"
        "    return new_entry\n"
        "fc.get_cached_or_fetch = _patched\n"
        # Pre-stub urllib.request.urlopen so the fetcher gets a value worth\n"
        # writing through (triggering _save_cache → exception).\n"
        "import urllib.request\n"
        "class _FakeResp:\n"
        "    def __enter__(self): return self\n"
        "    def __exit__(self, *a): return False\n"
        "    def read(self):\n"
        "        return json.dumps({'observations': [{'value': '6.84',\n"
        "            'date': '2026-05-01',\n"
        "            'realtime_start': '2026-05-01',\n"
        "            'realtime_end': '2026-05-01'}]}).encode()\n"
        "urllib.request.urlopen = lambda *a, **kw: _FakeResp()\n"
        # Now load the CLI script as a module and invoke main().\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('fred_cli_under_test', SCRIPT)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "saved_argv = sys.argv\n"
        "sys.argv = [SCRIPT, 'MORTGAGE30US', '--latest']\n"
        "captured = []\n"
        "import builtins\n"
        "_real_print = builtins.print\n"
        "def _capture(*a, **kw):\n"
        "    captured.append(' '.join(str(x) for x in a))\n"
        "builtins.print = _capture\n"
        "try:\n"
        "    rc = module.main()\n"
        "finally:\n"
        "    builtins.print = _real_print\n"
        "    sys.argv = saved_argv\n"
        "envelope = json.loads(captured[0])\n"
        "envelope['__rc__'] = rc\n"
        "_real_print(json.dumps(envelope))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", inline],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0, (
        f"subprocess failed: stdout={completed.stdout!r} stderr={completed.stderr!r}"
    )
    payload: dict[str, object] = json.loads(completed.stdout.strip().splitlines()[-1])
    return payload


def test_fred_cli_lock_timeout_returns_exit_0_with_error_envelope() -> None:
    """CR-02 regression: ``FredCacheLockError`` raised by ``_save_cache`` MUST
    be caught and converted to a populated ``error`` field with exit 0
    (D-12-LIVE02-01 + Pitfall 1 always-exit-0 contract). Pre-fix, the exception
    propagated to ``main()`` as a traceback + non-zero exit, defeating SKILL.md
    prose-only recovery."""
    envelope = _run_cli_with_mocked_save_cache(
        exc_class="fc.FredCacheLockError",
        exc_args_repr="'lock timeout after 30s'",
    )
    assert envelope["__rc__"] == 0
    assert envelope["value"] is None
    assert isinstance(envelope["error"], str)
    assert "FRED cache failure" in envelope["error"]
    assert "FredCacheLockError" in envelope["error"]


def test_fred_cli_permission_error_returns_exit_0_with_error_envelope() -> None:
    """CR-02 regression: ``PermissionError`` from ``Path.write_text`` in
    ``_save_cache`` MUST be caught upstream by ``fred_cli.main()``. Same
    contract as the lock-timeout path."""
    envelope = _run_cli_with_mocked_save_cache(
        exc_class="PermissionError",
        exc_args_repr="'read-only filesystem'",
    )
    assert envelope["__rc__"] == 0
    assert envelope["value"] is None
    assert isinstance(envelope["error"], str)
    assert "FRED cache failure" in envelope["error"]
    assert "PermissionError" in envelope["error"]
