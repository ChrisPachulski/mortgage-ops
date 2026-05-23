# Live Integration Workflow

This document is the runbook for `.github/workflows/integration.yml` —
the scheduled GitHub Actions job that exercises the tests gated by
`ANTHROPIC_API_KEY` and `FRED_API_KEY` against real APIs.

It is the live-integration companion to `docs/dependency-review.md`
(which covers the weekly `audit.yml` dependency / license scan).

## What the workflow does

`integration.yml` runs the subset of the test suite marked
`@pytest.mark.live`. That marker is registered in `pyproject.toml`
under `[tool.pytest.ini_options].markers` and excluded by default via
the `-m "not live"` filter in `addopts`. The scheduled workflow
overrides with `-m "live"` and injects both API keys from repo secrets,
producing the only context in which these tests actually run.

Today the `live` marker covers three tests:

| Test | API touched | Cost per run |
|------|-------------|--------------|
| `tests/test_property_extractor.py::test_extract_listing_live_smoke` | Anthropic Sonnet (extract_listing) | ~3-5k tokens |
| `tests/test_subagents.py::test_SUBA_06_stress_summary_under_1000_tokens` | Anthropic `messages.count_tokens` | $0 (count_tokens is free per Anthropic docs) |
| `tests/test_fred_cli_live.py::test_fred_cli_live_smoke_mortgage30us` | FRED `series/observations` | $0 (FRED is free) |

Total expected wall-clock: under 2 minutes including dependency sync.
The job carries a 10-minute hard cap (`timeout-minutes: 10`) plus a
per-test 120s cap via `--timeout=120` as runaway-process guards.

## Schedule

- **Cron:** `0 13 * * 0` (Sunday 13:00 UTC).
- **Manual dispatch:** `gh workflow run "Live Integration"` (or the
  Actions → Live Integration → "Run workflow" button).

Sunday off-peak was chosen because both providers are quietest then and
because FRED publishes weekly on Thursday noon ET — running Sunday
gives the upstream rate two business days to settle before we smoke
the cached envelope.

## Setting up the required secrets

The workflow needs two secrets configured at
**Settings → Secrets and variables → Actions → Repository secrets**:

1. **`ANTHROPIC_API_KEY`**
   - Paid-tier key with at least `messages.count_tokens` access.
   - `messages.count_tokens` itself is free per Anthropic docs but the
     `extract_listing` smoke also calls `messages.create` against Sonnet,
     which IS billed. Budget impact is bounded by the test running once a
     week against a ~5k-token contrived HTML fixture.
   - Source: <https://console.anthropic.com/settings/keys>

2. **`FRED_API_KEY`**
   - Free key from the St. Louis Fed.
   - Source: <https://fred.stlouisfed.org/docs/api/api_key.html>

The "Verify required secrets are present" step in `integration.yml`
fails fast with a `::error::` annotation if either is missing — without
this guard the belt-and-suspenders `@pytest.mark.skipif(not env)` gates
on each live test would skip every test and the workflow would pass
green with zero real API exercise, exactly the silent-failure mode
this docs page warns against.

## Manual dispatch

```bash
gh workflow run "Live Integration"
```

To watch a manual run in the terminal:

```bash
gh run watch
```

Or list recent runs:

```bash
gh run list --workflow="Live Integration" --limit=10
```

## Cost expectations

Per run:

- **Anthropic**: < 10k tokens of Sonnet input + bounded output, plus
  ~2k tokens of free `count_tokens` traffic. At Sonnet's current
  per-token pricing this is on the order of a few cents — call it < $0.10
  per run as a conservative bound.
- **FRED**: free.

Per month (4 scheduled runs + any manual dispatches): well under $1 in
Anthropic spend. The workflow is intentionally light — it is a stability
check, not a load test.

## Failure runbook

When the weekly run goes red, or when a manual dispatch fails:

1. **Open the Actions tab** → **Live Integration** → click the failed run.
   The "Run live integration tests" step has the pytest output in
   verbose mode (`-v`).

2. **Triage by which test failed**:

   - `test_extract_listing_live_smoke` failure → check the assertion
     message. The test only asserts `result is None or isinstance(result, dict)`,
     so a real failure here typically means Anthropic surfaced an
     exception (rate limit, model deprecation, key revoked).
     Check the Anthropic status page and verify `ANTHROPIC_API_KEY`
     is still valid in the console.

   - `test_SUBA_06_stress_summary_under_1000_tokens` failure with
     `input_tokens >= 1000` → not an API problem. The transcript
     fixture at `tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl`
     has drifted past the SC-3 budget. Either shorten the fixture or
     surface as a Phase 12 follow-up (see Plan 11-05 D-03).

   - `test_SUBA_06_stress_summary_under_1000_tokens` failure with a
     network / auth exception → Anthropic side. Same triage as the
     extractor failure.

   - `test_fred_cli_live_smoke_mortgage30us` failure on `envelope.error`
     non-null → FRED side. Check <https://fred.stlouisfed.org/> for an
     outage notice; verify `FRED_API_KEY` in the secrets page.

   - `test_fred_cli_live_smoke_mortgage30us` failure on `value` band
     `0 < x < 25` → likely upstream FRED schema change. Inspect
     `envelope.value` in the log; if it looks like `"."` (FRED's
     missing-observation sentinel), update `_fetcher` in
     `.claude/skills/mortgage-ops/scripts/fred_cli.py` to handle the
     sentinel. If it looks like a wildly different number, the
     `MORTGAGE30US` series may have been retired — confirm with
     <https://fred.stlouisfed.org/series/MORTGAGE30US>.

3. **Re-dispatch after a fix**: `gh workflow run "Live Integration"`.

4. **If a real API endpoint changed** (FRED schema, Anthropic API
   surface): open a phase plan under `.planning/phases/` per the GSD
   workflow before patching. Live-integration drift is a phase-level
   concern, not a hotfix.

## Relationship to other workflows

- `ci.yml` (every push / PR) — fast unit + integration, never touches
  live APIs. Always green except for real code regressions.
- `audit.yml` (weekly Monday) — dependency + license + vulnerability
  scan. See `docs/dependency-review.md`.
- `integration.yml` (weekly Sunday) — this workflow. Live API
  smoke. Failures here block nothing in PRs — they signal that an
  external dependency has drifted.
