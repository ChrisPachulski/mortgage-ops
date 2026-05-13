# FRED cache fixtures

This directory holds the synthetic FRED cache fixtures that anchor Phase 12
SC-1 (live-rate-injection eval) and SC-2 (7-day TTL boundary tests). Each
fixture is hand-authored to match the canonical cache schema from
`lib/fred_cache.py` and is committed so CI runs are deterministic, free of
FRED API charges, and reproducible across machines.

Wave 0 (Plan 12-00) ships this README plus a `.gitkeep` seam; Wave 5
(Plan 12-05) populates the directory with `MORTGAGE30US-2026-05-10.json`
and `MORTGAGE15US-2026-05-10.json` to back the `live-rate-injection-01`
eval per D-12-SC1-01.

## Why synthetic, not live (D-02 inherited from Phase 11)

Live FRED dispatch in CI is non-deterministic (rates change weekly), burns
API quota, and requires `FRED_API_KEY` in CI secrets. Synthetic fixtures
give us the four properties we need:

- **Determinism.** Same fixture, same bytes, same eval result.
- **Zero recurring cost.** No FRED API hits during pytest.
- **Airgap-safe.** Tests run anywhere; no network.
- **Contract-is-shape.** The fixture cache value (e.g. MORTGAGE30US=6.50%) is
  what `evals/expected/live-rate-injection-01.json` pins against. Eval pass
  means "the skill cited the cached number", not "the skill agrees with
  today's PMMS print."

## Files (populated by later waves)

| Fixture | Used by | Schema |
|---------|---------|--------|
| `MORTGAGE30US-2026-05-10.json` | Plan 12-05 `live-rate-injection-01.md` | lib/fred_cache.py cache schema (single-entry) |
| `MORTGAGE15US-2026-05-10.json` | Plan 12-05 live-rate-injection (companion) | same |
| `stale_8_day_cache.json` | Plan 12-02 test_fred_cache.py (TTL boundary) | same — `fetched_at` 8 days before "now" |

## Live-capture recipe (NOT run in CI)

For nightly refresh or when locking the next `live-rate-injection-NN` eval
oracle, a developer with `FRED_API_KEY` in their env can capture a live
observation and promote it intentionally:

```bash
# 1. Capture (writes a .NEW so the developer can diff before promote)
FRED_API_KEY=xxx python .claude/skills/mortgage-ops/scripts/fred_cli.py \
  MORTGAGE30US --latest \
  > tests/fixtures/fred/MORTGAGE30US-$(date +%Y-%m-%d).json.NEW

# 2. Diff against committed
diff -u \
  tests/fixtures/fred/MORTGAGE30US-2026-05-10.json \
  tests/fixtures/fred/MORTGAGE30US-$(date +%Y-%m-%d).json.NEW

# 3. If acceptable, promote and update evals/expected/live-rate-injection-*.json
#    in the same commit (oracle value must move with the fixture).
mv tests/fixtures/fred/MORTGAGE30US-$(date +%Y-%m-%d).json.NEW \
   tests/fixtures/fred/MORTGAGE30US-$(date +%Y-%m-%d).json
```

## What NOT to put here

- **No raw API keys.** `source_url` redacts `api_key=***` per Phase 12 RESEARCH §Pitfall 6.
- **No live transcripts.** Use `evals/runs/` (gitignored) for ad-hoc replay captures.
- **No AI-attribution markers.** Per global CLAUDE.md rule.
