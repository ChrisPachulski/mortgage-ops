"""Phase 16 live integration smoke test for fred_cli.py.

Exercises the real FRED API path end-to-end:

  1. Invokes the bundled ``fred_cli.py`` against ``MORTGAGE30US --latest``.
  2. Asserts the always-exit-0 envelope contract (D-12-LIVE02-01).
  3. Asserts ``value`` is a non-null Decimal-stringable number.
  4. Asserts ``fetched_at`` parses as ISO 8601 and is within the last hour
     when the network actually fetched (cache hits emit an older
     ``fetched_at`` but the envelope shape is identical — we tolerate both).

Gated by both:
  * ``@pytest.mark.live`` — excluded by ``-m 'not live'`` in the default
    ``pyproject.toml`` addopts so ``uv run pytest`` never reaches this file
    locally. The scheduled ``.github/workflows/integration.yml`` workflow
    overrides with ``-m 'live'`` and injects ``FRED_API_KEY``.
  * ``@pytest.mark.skipif(not FRED_API_KEY)`` — belt-and-suspenders second
    gate so a misconfigured live run skips cleanly rather than failing with
    a missing-key envelope (which is a valid no-key contract output, not a
    real failure).

Cache tolerance: the CLI consults the 7-day TTL cache before any network
fetch (D-12-LIVE02-01 cache-first ordering). On a fresh runner the cache
is empty and the test hits the live FRED API; on a re-run within 7 days
the cache short-circuits and ``fetched_at`` may be older than 1 hour.
Both outcomes are valid smoke signals — we only assert the envelope
shape, non-null value, and ISO 8601 ``fetched_at``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
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


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("FRED_API_KEY"),
    reason=(
        "Live FRED smoke test requires FRED_API_KEY. The default "
        "`uv run pytest` filters this via `-m 'not live'` in pyproject.toml; "
        ".github/workflows/integration.yml overrides with `-m 'live'` and "
        "injects FRED_API_KEY from repo secrets. The skipif gate remains as "
        "belt-and-suspenders so a missing key in the live job still skips "
        "cleanly rather than failing with the no-key envelope contract."
    ),
)
def test_fred_cli_live_smoke_mortgage30us() -> None:
    """Live FRED smoke: ``MORTGAGE30US --latest`` returns a usable envelope.

    Does NOT redirect the cache (no env-var override exists on
    ``lib.fred_cache.CACHE_DIR``). On a CI runner with no checked-in cache
    file at ``data/cache/fred_MORTGAGE30US.json`` this exercises the real
    HTTP path; on a re-run within 7 days the cache short-circuits and we
    still validate the envelope shape.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "MORTGAGE30US", "--latest"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"fred_cli exited {result.returncode}; stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    envelope = json.loads(result.stdout.strip().splitlines()[-1])

    assert envelope["error"] is None, (
        f"live FRED smoke surfaced envelope.error={envelope['error']!r}; "
        f"either FRED is down, the response shape changed, or the API key "
        f"is invalid. See docs/live-integration.md failure runbook."
    )
    assert envelope["series_id"] == "MORTGAGE30US"

    # `value` must be a non-null string parseable as Decimal (D-19 boundary).
    raw_value = envelope["value"]
    assert raw_value is not None, "live FRED returned null value with no error"
    assert isinstance(raw_value, str), (
        f"D-19: envelope.value must be a JSON string; got {type(raw_value).__name__}"
    )
    try:
        parsed = Decimal(raw_value)
    except InvalidOperation as exc:
        pytest.fail(f"envelope.value={raw_value!r} not Decimal-stringable: {exc!r}")
    # MORTGAGE30US historically ranges roughly 2.5%-9%. A 0 or > 25 result
    # signals a parsing bug or upstream schema change, not a real rate.
    assert Decimal("0") < parsed < Decimal("25"), (
        f"envelope.value={parsed} outside plausible MORTGAGE30US band; "
        f"likely FRED schema change or parsing regression."
    )

    # `fetched_at` must be ISO 8601 with `Z` suffix (UTC).
    fetched_at_raw = envelope["fetched_at"]
    assert fetched_at_raw is not None, "envelope.fetched_at must not be null"
    assert isinstance(fetched_at_raw, str)
    assert fetched_at_raw.endswith("Z"), (
        f"envelope.fetched_at={fetched_at_raw!r} must end with 'Z' (UTC); "
        f"see fred_cli._fetcher ISO 8601 normalization."
    )
    # Replace trailing 'Z' with '+00:00' so datetime.fromisoformat accepts it.
    fetched_at = datetime.fromisoformat(fetched_at_raw.replace("Z", "+00:00"))
    assert fetched_at.tzinfo is not None, "fetched_at must be tz-aware"

    # Cache-tolerance: when the cache short-circuits, fetched_at can be up
    # to 7 days old. When we actually fetched, fetched_at should be within
    # the last hour. Accept the 7-day window so cache hits don't false-fail.
    now = datetime.now(UTC)
    age = now - fetched_at
    assert age >= timedelta(seconds=0), (
        f"fetched_at={fetched_at.isoformat()} is in the future relative to "
        f"now={now.isoformat()}; clock skew or fixture corruption."
    )
    assert age <= timedelta(days=7), (
        f"fetched_at={fetched_at.isoformat()} is older than the 7-day cache "
        f"TTL; stale cache file should have been refetched by get_cached_or_fetch."
    )
