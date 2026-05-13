#!/usr/bin/env python3
"""scripts/fred_cli.py — JSON-out CLI for the latest FRED observation, with 7d TTL cache.

Per LIVE-01 + LIVE-04 + D-12-LIVE01-01:
  - HTTP wrapper (canonical path) — calls api.stlouisfed.org/fred/series/observations
  - 7-day TTL cache at data/cache/fred_{series_id}.json (Plan 12-02 ships lib.fred_cache)
  - Allowlist: series_id ∈ {MORTGAGE30US, MORTGAGE15US}
  - --help works without importing urllib / lib.fred_cache (lazy-import per D-18 inherited)
  - Always exits 0; failures emit {value: null, error: "..."} envelope on stdout
    (per Pitfall 1 + D-12-LIVE02-01 recovery contract — SKILL.md prose-only
    injection reads the envelope's `error` field, NOT a non-zero exit)

Output JSON shape (stdout, one line — NOT pretty-printed):
  {
    "series_id": "MORTGAGE30US" | "MORTGAGE15US",
    "value": "6.84" | null,                # JSON string per D-19; null on error
    "observation_date": "2026-04-25" | null,
    "fetched_at": "2026-04-26T17:00:03Z" | null,
    "source_url": "...api_key=***..." | null,    # api_key ALWAYS redacted per Pitfall 6
    "fred_realtime_start": "2026-04-26" | null,
    "fred_realtime_end": "2026-04-26" | null,
    "error": null | "<message>"
  }

Cache integration TODO (Plan 12-02): when lib.fred_cache.get_cached_or_fetch ships,
the network path below collapses to a single get_cached_or_fetch(series_id) call.
Wave 1 (this plan) always performs the live fetch (cache miss every time).

MCP server registration (stefanoamorelli/fred-mcp-server) is documented as an
OPTIONAL secondary path in references/fred-context.md per D-12-LIVE01-01.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_SERIES = ("MORTGAGE30US", "MORTGAGE15US")
"""V5 input validation per RESEARCH §Security Domain (T-12-01-01 mitigation).
argparse `choices=ALLOWED_SERIES` rejects any other value at parse time — no
URL interpolation possible for non-allowed series."""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fred_cli",
        description=("Fetch latest FRED observation for a mortgage series; emit JSON to stdout."),
        epilog=(
            "Series allowlist: MORTGAGE30US | MORTGAGE15US.\n"
            "Output JSON shape (single line on stdout):\n"
            '  {"series_id": str, "value": str|null, "observation_date": str|null,\n'
            '   "fetched_at": str|null, "source_url": str|null,\n'
            '   "fred_realtime_start": str|null, "fred_realtime_end": str|null,\n'
            '   "error": null|str}\n'
            "All money/rate fields are JSON STRINGS (D-19 inherited).\n"
            "FRED_API_KEY env var required; falls back to {error: ...} envelope when absent.\n"
            "Always exits 0; check envelope.error field for failure mode."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "series_id",
        choices=ALLOWED_SERIES,
        help="FRED series identifier (allowlist of 2).",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        default=True,
        help="Return only the latest observation (v1 default).",
    )
    args = parser.parse_args()

    # Phase 12 D-12-LIVE01-01: scripts/fred_cli.py lives at
    # .claude/skills/mortgage-ops/scripts/fred_cli.py (5 levels deep).
    # Mirror Phase 10 sys.path-injection idiom (amortize.py parents[4]/parents[1]).
    # parents[4] = repo root (so future `from lib.fred_cache import ...` resolves);
    # parents[1] = skill root (so `from scripts._cli_helpers import ...` resolves
    # to the colocated helper). Runs AFTER --help has exited above, so D-18
    # (--help fast) is unaffected.
    _skill_root = str(Path(__file__).resolve().parents[1])
    _project_root = str(Path(__file__).resolve().parents[4])
    for _p in (_project_root, _skill_root):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    # Lazy-import per D-18 inherited: heavy deps (urllib, lib.fred_cache) are NOT
    # loaded on the --help fast path. argparse has already parsed by here, so any
    # --help / --version invocation has SystemExit'd above this line.
    import os
    import urllib.error
    import urllib.parse
    import urllib.request
    from datetime import UTC, datetime

    series_id: str = args.series_id

    def _emit(envelope: dict[str, Any]) -> int:
        """Emit the JSON envelope on stdout (single line) and return 0.

        Pitfall 1 + D-12-LIVE02-01: ALWAYS exit 0 — SKILL.md prose-only injection
        reads envelope.error as the recovery contract; non-zero exits would break
        the SKILL.md routing that depends on stdout-only sourcing (D-12-SC3-01).
        """
        print(json.dumps(envelope))
        return 0

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        return _emit(
            {
                "series_id": series_id,
                "value": None,
                "observation_date": None,
                "fetched_at": None,
                "source_url": None,
                "fred_realtime_start": None,
                "fred_realtime_end": None,
                "error": "FRED_API_KEY not set in environment; ask the user for the current rate.",
            }
        )

    # Cache-first path: Plan 12-02 ships lib.fred_cache with read-through semantics
    # at data/cache/fred_{series_id}.json (per-series file shape pinned by
    # D-12-LIVE02-01 SKILL.md citations, NOT the RESEARCH §Example 1 combined
    # `fred-cache.json`). Wave 1 (this plan) ships the network path; cache
    # integration happens at Plan 12-02 when `from lib.fred_cache import
    # get_cached_or_fetch` replaces the body of the fetch path below with a
    # single get_cached_or_fetch(series_id) call.
    qs = urllib.parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{qs}"
    # T-12-01-02 mitigation: redacted source_url ALWAYS uses the hand-built
    # `api_key=***` form; the real key is never str-interpolated into any output
    # channel. Constructed independently of `url` so a future refactor cannot
    # accidentally leak the key.
    redacted_url = (
        f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}"
        "&api_key=***&file_type=json&sort_order=desc&limit=1"
    )

    try:
        # T-12-01-04 mitigation: 10s timeout caps Slowloris-style worst-case at
        # 10 seconds (RESEARCH §Pitfall: Slowloris cap). SKILL.md prose-only
        # injection (Plan 12-03) does not block on this script — cache-first
        # read in Plan 12-02 means the live fetch is on the refresh cron path.
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        obs = data["observations"][0]
        now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        # FRED returns "value" as a string (e.g., "6.84"). Defensive coercion:
        # if it ever returns a number, str() preserves the digits for D-19
        # compliance (money/rate fields are JSON strings at the boundary).
        return _emit(
            {
                "series_id": series_id,
                "value": str(obs["value"]),
                "observation_date": obs["date"],
                "fetched_at": now_iso,
                "source_url": redacted_url,
                "fred_realtime_start": obs["realtime_start"],
                "fred_realtime_end": obs["realtime_end"],
                "error": None,
            }
        )
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
        # T-12-01-03 mitigation: repr(URLError) does NOT include the request URL
        # by default in Python 3.12 — URLError doesn't carry the URL; HTTPError
        # carries response, not request URL. So FRED_API_KEY cannot leak via
        # exception repr. Verified by the always-exit-0 stub test.
        return _emit(
            {
                "series_id": series_id,
                "value": None,
                "observation_date": None,
                "fetched_at": None,
                "source_url": redacted_url,
                "fred_realtime_start": None,
                "fred_realtime_end": None,
                "error": f"FRED fetch failed: {exc!r}",
            }
        )
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        # T-12-01-05 mitigation: malformed FRED response never propagates to the
        # caller; envelope.error explains the shape mismatch. Plan 12-02 layers
        # Pydantic validation on top.
        return _emit(
            {
                "series_id": series_id,
                "value": None,
                "observation_date": None,
                "fetched_at": None,
                "source_url": redacted_url,
                "fred_realtime_start": None,
                "fred_realtime_end": None,
                "error": f"FRED response shape unexpected: {exc!r}",
            }
        )


if __name__ == "__main__":
    sys.exit(main())
