"""E2E snapshot-test fixtures and helpers.

The four `test_scenario_*.py` modules use these helpers to load a YAML input
fixture, invoke the matching CLI via ``subprocess.run``, and assert that the
parsed stdout JSON deep-equals a committed JSON snapshot.

Snapshot strategy
=================

Snapshots are generated ONCE manually (see tests/e2e/README.md) by running
the engine against each input fixture and committing the resulting JSON.
Subsequent test runs assert equality. When the engine output legitimately
changes, regenerate the snapshot via the documented `--update-snapshots`
workflow and commit the diff.

Dynamic-field scrubbing
=======================

The engine occasionally embeds values into its output that are clock-driven
(e.g., the 12-month staleness threshold rendered into FHA MIP warnings is
``date.today() - relativedelta(months=12)``; that string drifts daily). The
`scrub_dynamic_fields` helper walks the parsed JSON and applies a small set
of deterministic substitutions BEFORE the deep-equality assertion:

  - Any ISO-date suffix inside the StaleReferenceWarning ``threshold: YYYY-MM-DD``
    fragment is replaced with ``threshold: <DATE>``.
  - Top-level keys whose name matches the `DYNAMIC_FIELD_NAMES` allowlist
    are dropped (e.g., ``run_id``, ``timestamp``, ``fetched_at``).

The scrub is symmetric: it runs on BOTH the actual CLI output and the
committed snapshot before comparison, so the snapshot file may contain the
post-scrub placeholders verbatim. Today snapshots are written WITH the
clock-driven values present; the scrubber normalizes them at compare time.

Hermetic isolation
==================

E2E tests must not touch the real ``data/mortgage-ops.duckdb``,
``data/cache/``, or ``reports/``. The :func:`run_cli` helper accepts an
``output_dir`` (``tmp_path``-rooted) and sets the appropriate env vars when
the CLI honors one. CLIs that lack an output-dir override (notably
``property_analyze.py``, which writes a sidecar listing to a hardcoded
``data/property-listings/`` rooted on the repo) are NOT exercised by this
suite; see tests/e2e/README.md "Hermetic Gaps".
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
"""Project root for cwd of subprocess invocations."""

SKILL_SCRIPTS: Path = REPO_ROOT / ".claude" / "skills" / "mortgage-ops" / "scripts"
"""Phase 10 relocated CLI scripts (D-01)."""

FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"
INPUTS_DIR: Path = FIXTURES_DIR / "inputs"
SNAPSHOTS_DIR: Path = FIXTURES_DIR / "snapshots"


# Map a fixture's `cli:` field to the relocated script path on disk.
CLI_PATHS: dict[str, Path] = {
    "affordability": SKILL_SCRIPTS / "affordability.py",
    "amortize": SKILL_SCRIPTS / "amortize.py",
    "arm_simulate": SKILL_SCRIPTS / "arm_simulate.py",
    "refi_npv": SKILL_SCRIPTS / "refi_npv.py",
    "points_breakeven": SKILL_SCRIPTS / "points_breakeven.py",
    "stress_test": SKILL_SCRIPTS / "stress_test.py",
    "apr_reg_z": SKILL_SCRIPTS / "apr_reg_z.py",
}


DYNAMIC_FIELD_NAMES: frozenset[str] = frozenset(
    {
        # Observability sidecar fields that may leak into stdout in some CLIs.
        "run_id",
        "ts",
        "timestamp",
        "started_at",
        "ended_at",
        "fetched_at",
        "log_path",
        # FRED cache freshness markers (some payloads may surface these).
        "as_of",
        "duration_ms",
    }
)
"""Top-level keys to STRIP from both actual and snapshot before comparison.

Anything clock- or run-driven that the engine MIGHT emit lands here. Today no
shipped CLI puts these on stdout (observability runs to stderr + file only),
but we strip defensively so a future CLI that surfaces a `run_id` does not
silently break every E2E snapshot.
"""


_THRESHOLD_RE = re.compile(r"threshold:\s*\d{4}-\d{2}-\d{2}")
"""Matches the FHA / staleness ``threshold: YYYY-MM-DD`` fragment in warning
strings emitted by lib.rules helpers. The threshold is computed as
``date.today() - relativedelta(months=12)`` so it drifts daily — we replace
the date with ``<DATE>`` in BOTH the actual and snapshot copies before
comparing.
"""


def _scrub_value(value: Any) -> Any:
    """Recursive, dynamic-field-aware copy of `value` suitable for comparison.

    Rules applied:
      - dict: drop keys named in ``DYNAMIC_FIELD_NAMES`` at every depth.
      - str: ``threshold: YYYY-MM-DD`` -> ``threshold: <DATE>``.
      - list / tuple: scrub each element.
      - other scalars: returned unchanged.

    The scrub is idempotent (applying twice gives the same result) so it can
    be safely applied to BOTH sides of an equality assertion.
    """
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items() if k not in DYNAMIC_FIELD_NAMES}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(v) for v in value)
    if isinstance(value, str):
        return _THRESHOLD_RE.sub("threshold: <DATE>", value)
    return value


def scrub_dynamic_fields(value: Any) -> Any:
    """Public entry point — see :func:`_scrub_value`.

    Returns a deep copy with dynamic fields normalized so two clock-different
    runs of the same engine compare equal. Idempotent.
    """
    return _scrub_value(value)


def load_input_fixture(stem: str) -> dict[str, Any]:
    """Load ``tests/e2e/fixtures/inputs/<stem>.yml`` as a dict.

    The fixture YAML must contain:
      - ``cli``: one of the keys in :data:`CLI_PATHS`.
      - ``request``: the JSON-serialisable request body the CLI's
        ``--input`` flag consumes.

    Optional keys (forward-compatible; unused by current scenarios):
      - ``args``: extra argv list appended after ``--input``.
      - ``env``: dict[str, str] of env vars to set on the subprocess.
    """
    path = INPUTS_DIR / f"{stem}.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"input fixture {path} did not parse as a mapping")
    return data


def load_snapshot(stem: str) -> dict[str, Any] | list[Any]:
    """Load ``tests/e2e/fixtures/snapshots/<stem>.json`` as parsed JSON.

    Snapshots are committed JSON with sorted keys + 2-space indent so diffs
    are review-friendly (per the E2E task spec). Returned as-parsed; the
    caller is expected to pass it through :func:`scrub_dynamic_fields` before
    comparing.
    """
    path = SNAPSHOTS_DIR / f"{stem}.json"
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict | list):
        raise TypeError(f"snapshot {path} did not parse as JSON object/array")
    return data


def run_cli(
    stem: str,
    *,
    extra_env: dict[str, str] | None = None,
    output_dir: Path | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    """Run the CLI declared by ``tests/e2e/fixtures/inputs/<stem>.yml``.

    The fixture's ``request`` body is serialised to a temporary JSON file
    that is passed via ``--input``. Stdout / stderr are captured as text;
    the returned :class:`subprocess.CompletedProcess` is the only thing the
    test asserts against.

    Hermetic discipline:
      - ``cwd = REPO_ROOT`` so the CLI's sys.path injection (parents[4]) and
        any project-relative path lookups (e.g. ``data/reference/*.yml``)
        resolve to the repo on disk.
      - ``extra_env`` lets a test add or override env vars (e.g. point a
        future ``MORTGAGE_OPS_DB_PATH`` at a tmp DB).
      - ``output_dir`` is forwarded to CLIs that accept ``--output-dir``
        (currently only ``property_analyze.py``; affordability / amortize /
        refi_npv / arm_simulate are pure JSON-in/JSON-out and write nothing
        to disk).

    Timeouts default to 60s — long enough for the 300-row refi cashflow
    output but tight enough to fail fast on a hung subprocess.
    """
    fixture = load_input_fixture(stem)
    cli_name: str = fixture["cli"]
    script: Path = CLI_PATHS[cli_name]
    if not script.exists():
        raise FileNotFoundError(f"CLI script not found: {script}")

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    # Serialize the request payload to a temp JSON file so we can pass --input.
    # Using NamedTemporaryFile(delete=False) so the subprocess can open it on
    # platforms where the parent's file handle blocks child reads (Windows).
    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as f:
        json.dump(fixture["request"], f)
        request_path = Path(f.name)

    try:
        cmd: list[str] = [
            sys.executable,
            str(script),
            "--input",
            str(request_path),
        ]
        if output_dir is not None:
            cmd += ["--output-dir", str(output_dir)]
        extra_args = fixture.get("args") or []
        cmd += [str(a) for a in extra_args]
        return subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    finally:
        # Cleanup failures should never mask a test failure.
        with contextlib.suppress(OSError):
            request_path.unlink()


def assert_snapshot_matches(stem: str, actual: dict[str, Any] | list[Any]) -> None:
    """Compare ``actual`` against ``tests/e2e/fixtures/snapshots/<stem>.json``.

    Both sides are run through :func:`scrub_dynamic_fields` first. The
    assertion uses pytest's structured equality so diff output points at the
    exact JSON path that drifted.
    """
    snapshot = load_snapshot(stem)
    scrubbed_actual = scrub_dynamic_fields(actual)
    scrubbed_snapshot = scrub_dynamic_fields(snapshot)
    assert scrubbed_actual == scrubbed_snapshot, (
        f"E2E snapshot drift for {stem}.\n"
        f"  Snapshot path: tests/e2e/fixtures/snapshots/{stem}.json\n"
        f"  Diff key paths reported by pytest above.\n"
        f"  If the engine change is INTENTIONAL, regenerate the snapshot:\n"
        f"    uv run python tests/e2e/_regenerate_snapshots.py {stem}\n"
        f"  (or see tests/e2e/README.md)."
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def e2e_repo_root() -> Path:
    """Repo root for the subprocess `cwd` argument.

    Distinct from the `repo_root` fixture in `tests/conftest.py` so the E2E
    module is self-contained and does not depend on parent-directory imports.
    """
    return REPO_ROOT


@pytest.fixture
def isolated_output_dir(tmp_path: Path) -> Path:
    """A `tmp_path`-rooted directory safe to pass as ``--output-dir`` to any
    CLI that writes files. Currently only used by future tests that exercise
    ``property_analyze.py`` (which the v1 suite skips due to a hardcoded
    sidecar write under ``data/property-listings/``; see README "Hermetic
    Gaps").
    """
    out = tmp_path / "e2e_output"
    out.mkdir(parents=True, exist_ok=True)
    return out
