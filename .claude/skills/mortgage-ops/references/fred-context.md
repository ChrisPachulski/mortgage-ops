# FRED Context — mortgage-ops Phase 12 Reference

This document records the conventions implemented by `scripts/fred_cli.py`
(Phase 12 FRED HTTP wrapper) and `lib/fred_cache.py` (7-day TTL read-through
cache) and pairs each convention with its data-source citation. All URLs were
verified on 2026-05-10 against the live FRED docs site + the
`stefanoamorelli/fred-mcp-server` repository.

Cited from:
- `.claude/skills/mortgage-ops/scripts/fred_cli.py` module docstring
  (D-12-LIVE01-01 HTTP-canonical decision)
- `lib/fred_cache.py` cache schema + lockfile port (mirrors RESEARCH §Pattern 2
  + `orchestration/lockfile.mjs`)
- `.planning/ROADMAP.md` § Phase 12 SC-1..SC-2 (live-rate injection + 7-day TTL)
- `.planning/phases/12-fred-eval/12-CONTEXT.md` D-12-LIVE01-01 +
  D-12-LIVE02-01 + D-12-SC1-01 + D-12-SC3-01 + D-12-SC4-01

This reference is loaded on demand by SKILL.md when the borrower asks about
"current rate", "FRED", "MORTGAGE30US", or "how do live rates work" — see
the references-table row in SKILL.md `## Loading Additional Context`. It is
NOT eagerly loaded into every skill invocation (Phase 10 D-09 progressive
disclosure).

---

## 1. HTTP API (canonical path per D-12-LIVE01-01)

Phase 12 ships `scripts/fred_cli.py` as the **canonical** FRED integration
path. The HTTP wrapper calls the FRED `series_observations` endpoint directly
via stdlib `urllib.request` — no extra runtime dependencies beyond what the
mortgage-ops calc engine already needs.

### Endpoint

```
GET https://api.stlouisfed.org/fred/series/observations
    ?series_id={SID}
    &api_key={KEY}
    &file_type=json
    &sort_order=desc
    &limit=1
```

Returns the single latest observation as JSON. `sort_order=desc` + `limit=1`
together pin the response shape to one entry; the script extracts
`data["observations"][0]` deterministically.

### Series allowlist (V5 input validation per T-12-01-01 mitigation)

`argparse choices=ALLOWED_SERIES` rejects any `series_id` outside the
allowlist at parse time — no URL interpolation is possible for non-allowlisted
series:

- `MORTGAGE30US` — 30-year fixed conventional rate, weekly (Thursday noon ET).
- `MORTGAGE15US` — 15-year fixed conventional rate, weekly (Thursday noon ET).

Both series source from Freddie Mac's Primary Mortgage Market Survey (PMMS);
FRED republishes the same weekly print under a stable ID.

### Authentication

The `FRED_API_KEY` environment variable is required. Register a free key at
https://fred.stlouisfed.org/docs/api/api_key.html (32-character alphanumeric
key; never commit it to git). When the env var is missing,
`scripts/fred_cli.py` ALWAYS exits 0 with this envelope on stdout:

```json
{
  "series_id": "MORTGAGE30US",
  "value": null,
  "observation_date": null,
  "fetched_at": null,
  "source_url": null,
  "fred_realtime_start": null,
  "fred_realtime_end": null,
  "error": "FRED_API_KEY not set in environment; ask the user for the current rate."
}
```

This is the **recovery contract** (D-12-LIVE02-01 + Pitfall 1): SKILL.md prose
around the cache citation tells Claude what to do when the envelope's `error`
field is non-null — narrate the error and ask the user for the current rate
manually.

### Rate limits

FRED publishes a 120-requests-per-minute soft limit; see
https://fred.stlouisfed.org/docs/api/terms_of_use.html. We never hit this in
practice — the read-through cache means a typical 7-day window has at most
1 network call per series. Even a cold cache backfilling both series is
2 requests / 0 risk.

### Output JSON shape (single-line stdout)

```json
{
  "series_id": "MORTGAGE30US",
  "value": "6.84",
  "observation_date": "2026-04-25",
  "fetched_at": "2026-04-26T17:00:03Z",
  "source_url": "https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key=***&file_type=json&sort_order=desc&limit=1",
  "fred_realtime_start": "2026-04-26",
  "fred_realtime_end": "2026-04-26",
  "error": null
}
```

The envelope is emitted on a single line (not pretty-printed) so a downstream
log scrape stays one-line-per-fetch.

### Always exits 0 (Pitfall 1 + D-12-LIVE02-01)

`scripts/fred_cli.py` ALWAYS exits 0. Failures replace `value` /
`observation_date` with `null` and populate the `error` field. The full set
of failure modes:

| Failure mode | Where caught | `error` field example |
|---|---|---|
| `FRED_API_KEY` missing | `os.environ.get` returns `None` | `"FRED_API_KEY not set in environment; ask the user for the current rate."` |
| Network timeout / DNS / refused | `URLError, HTTPError, OSError, TimeoutError` | `"FRED fetch failed: <repr>"` |
| FRED response schema drift | `KeyError, IndexError, json.JSONDecodeError` | `"FRED response shape unexpected: <repr>"` |

Non-zero exit codes are NOT used because SKILL.md's prose-only injection
pattern (D-12-LIVE02-01) reads the envelope's `error` field as the recovery
contract; a non-zero exit would break the SKILL.md routing that depends on
stdout-only sourcing (D-12-SC3-01).

---

## 2. MCP Server (optional secondary path per D-12-LIVE01-01)

The `stefanoamorelli/fred-mcp-server` MCP server is documented as an
**optional secondary path** for users who want session-scoped MCP-tool
dispatch to FRED from inside an interactive Claude Code session. Phase 12
does NOT depend on it being registered:

- The CI eval gate (`evals/runner.py`) uses HTTP-canonical for determinism.
- SKILL.md's `## Live Mortgage Rates` section cites the cache file directly
  (`data/cache/fred_*.json`), not an MCP tool.
- If the MCP server is unavailable (no Node, no Smithery install), the skill
  still works — the HTTP wrapper has zero MCP-runtime coupling.

### Registration recipe (project-scoped via `.mcp.json`)

```json
{
  "mcpServers": {
    "fred": {
      "type": "stdio",
      "command": "node",
      "args": ["/abs/path/to/fred-mcp-server/build/index.js"],
      "env": {
        "FRED_API_KEY": "${FRED_API_KEY}"
      }
    }
  }
}
```

Place `.mcp.json` at the repo root; Claude Code picks it up at session start
(see https://code.claude.com/docs/en/mcp for the project-scoped MCP file
format). The `${FRED_API_KEY}` interpolation reads from the user's shell
environment — never commit a literal key.

### Alternative install via Smithery (upstream-recommended)

```bash
npx -y @smithery/cli install @stefanoamorelli/fred-mcp-server --client claude
```

Smithery handles the Node build + the `.mcp.json` entry automatically. This
is the path the upstream README recommends; the manual `.mcp.json` recipe
above is the fallback when Smithery is unavailable or the user wants a
pinned local build.

### What the MCP server exposes (and why SKILL.md doesn't use it)

The MCP server exposes three tools — `fred_browse`, `fred_search`,
`fred_get_series` — for ad-hoc FRED-catalog exploration. SKILL.md does NOT
route to these:

- Phase 12 Plan 12-03 ships a prose-only `## Live Mortgage Rates` section
  (D-12-LIVE02-01 Pattern A) that reads `data/cache/fred_{series_id}.json`
  via the Read tool, NOT via an MCP-tool call.
- The cache is populated by `scripts/fred_cli.py` (HTTP-canonical), so the
  MCP server is never on the critical path for the skill's two PMMS series.

The MCP server is useful for **interactive** sessions where the user wants
to explore other FRED series (CPI, unemployment, etc.) that aren't part of
the mortgage-ops scope. For the two PMMS series the skill cares about, the
HTTP wrapper is canonical.

### Rationale for HTTP-as-canonical (D-12-LIVE01-01)

Three reasons HTTP wins over MCP for the v1 critical path:

1. **Determinism for CI evals.** `evals/runner.py` runs in `replay-stub` mode
   under CI with no live FRED dispatch and no MCP runtime. An MCP-dependent
   canonical path would require either a fake MCP runtime in CI (extra
   harness surface) or live FRED dispatch (non-deterministic, costs network).
2. **No system dependency.** `scripts/fred_cli.py` is pure stdlib (`urllib`,
   `json`, `argparse`, `os`, `datetime`) + the project's already-installed
   `lib.fred_cache`. The MCP server requires Node + the
   `@anthropic-ai/mcp-runtime` + Smithery install — three layers of system
   dependency the skill would inherit.
3. **Upstream gap (verified 2026-05-02).** As of `fred-mcp-server` v1.0.2,
   the upstream package exposes MCP tools only; it has NO shell-invocable
   `fred-cli` binary. Even if SKILL.md wanted to inline-invoke FRED via the
   MCP server, it would need a shim binary that doesn't exist upstream.

### v2 reconsideration

If Anthropic's MCP runtime ships with Claude Code (no separate install) AND
`fred-mcp-server` ships a shell-invocable `fred-cli` binary, v2 can revisit
the canonical-path decision. The HTTP wrapper would stay as a fallback for
non-Claude-Code consumers. v1 ratifies HTTP-as-canonical with no MCP
dependency.

---

## 3. Cache Schema

`lib/fred_cache.py` writes per-series cache files at
`data/cache/fred_{series_id}.json`. The per-series file layout (NOT a single
combined `fred-cache.json`) is pinned by D-12-LIVE02-01 SKILL.md citations:
the SKILL.md `## Live Mortgage Rates` section names both files individually
(`data/cache/fred_MORTGAGE30US.json`, `data/cache/fred_MORTGAGE15US.json`)
so a future consolidation would break the prose.

### File schema (PINNED by 12-RESEARCH.md §Pattern 2)

```json
{
  "schema_version": 1,
  "entries": {
    "MORTGAGE30US": {
      "series_id": "MORTGAGE30US",
      "value": "6.84",
      "observation_date": "2026-04-25",
      "fetched_at": "2026-04-26T17:00:03Z",
      "source_url": "https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key=***&file_type=json&sort_order=desc&limit=1",
      "fred_realtime_start": "2026-04-26",
      "fred_realtime_end": "2026-04-26",
      "error": null
    }
  }
}
```

`schema_version: 1` is pinned by `lib.fred_cache.SCHEMA_VERSION`. A cache
file with an unrecognized schema version is treated as missing — the cache
loader falls through to a fresh fetch (see `_load_cache` in `lib/fred_cache.py`).
Bump `SCHEMA_VERSION` if the entry shape ever changes.

### Field semantics

- **`series_id`** — Echoes the FRED series identifier. Always a member of
  `ALLOWED_SERIES`.
- **`value`** — JSON STRING per CLAUDE.md money/rate discipline (D-19
  inherited from Phase 1). Downstream consumers (SKILL.md citation prose,
  `evals/runner.py`) Decimal-parse via `Decimal(str(...))`. NEVER `float()`.
  The fetcher defensively coerces with `str(obs["value"])` in case FRED
  ever changes the field type from string to number.
- **`observation_date`** — FRED's observation date (the survey Thursday for
  PMMS series). ISO-8601 date string (`YYYY-MM-DD`).
- **`fetched_at`** — Our fetch timestamp, ISO-8601 UTC with the `Z` suffix.
  The 7-day TTL boundary is computed against this field, NOT the file mtime
  (mtime is unreliable across editors and lockfile rewrites).
- **`source_url`** — Audit trail of what we hit. `api_key=***` is ALWAYS
  redacted (T-12-01-02 mitigation; Pitfall 6). The redacted URL is
  constructed independently from the real URL in `scripts/fred_cli.py` so
  a future refactor cannot accidentally leak the key.
- **`fred_realtime_start` / `fred_realtime_end`** — FRED's "as-of-when did
  this value exist" fields. Equal on first fetch; diverge if FRED publishes
  a revision. Useful for detecting upstream PMMS revisions without diffing
  the cache file.
- **`error`** — `null` on success; populated string on fetch failure
  (`scripts/fred_cli.py` never raises; the cache writer only writes when
  `value is not None` so failure envelopes don't pollute the cache).

### TTL semantics (strict `<` boundary per D-12-LIVE02-01 + Pitfall 2)

```python
CACHE_TTL = timedelta(days=7)  # lib/fred_cache.py:47
# is_fresh: returns True iff (now - fetched_at) < CACHE_TTL
```

| Cache age | Fresh? | Refetch on next call? |
|---|---|---|
| 0s – 6d 23h 59m 59s | YES | No |
| 7d 0h 0m 0s (exact) | NO | Yes |
| 7d 0h 0m 1s+ | NO | Yes |
| 8d | NO | Yes |

FRED publishes PMMS rates Thursdays around noon ET (Wednesday on holiday
weeks). A cache entry fetched Thursday at 12:00:01 ET will be exactly 7 days
old the following Thursday at 12:00:01 ET — strict-`<` means re-invocation
that Thursday triggers a refetch and catches the latest weekly print.

Boundary tests live at `tests/test_fred_cache.py` (4 freezegun cases:
6d-23h-59m fresh, 7d-exact stale, 8d stale, lock-acquire timing).

### Lock semantics (Python port of `orchestration/lockfile.mjs`)

`data/cache/.fred-cache.lock` is a JSON content-based lockfile (NOT
`O_EXCL`). Shape:

```json
{
  "pid": 12345,
  "acquired_at": 1715626803000,
  "reason": "write MORTGAGE30US"
}
```

| Property | Value | Source |
|---|---|---|
| `STALE_THRESHOLD` | 60s | `lockfile.mjs:STALE_THRESHOLD_MS = 60_000` |
| `DEFAULT_TIMEOUT` | 30s | `lockfile.mjs:DEFAULT_TIMEOUT_MS = 30_000` |
| `POLL_INTERVAL` | 100ms | `lockfile.mjs:POLL_INTERVAL_MS = 100` |
| Acquire pattern | Read-back-and-verify CAS | `lockfile.mjs:acquireLock` |
| Stale detection | `acquired_at` (NOT `mtime`) | D-01-01 inherited |

Concurrent acquire polls every 100ms up to 30s; if the deadline elapses
with the lock still held by another process, `FredCacheLockError` is raised
with the blocker JSON in the message. The lock is gitignored
(`data/cache/.fred-cache.lock` in `.gitignore`).

---

## 4. SKILL.md Routing Rule

When the borrower asks current-rate questions, SKILL.md routes to the cache
files via the Read tool. The `## Live Mortgage Rates` section (Plan 12-03,
verbatim per D-12-LIVE02-01) names both cache files explicitly:

- `data/cache/fred_MORTGAGE30US.json` (30-year fixed)
- `data/cache/fred_MORTGAGE15US.json` (15-year fixed)

### Cache-miss / staleness recovery

If the cache file is absent or stale (>7 days old), SKILL.md instructs
Claude to invoke:

```
python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE30US --latest
```

The script writes the cache and emits the value to stdout (single-line
envelope). If the envelope's `error` field is non-null (e.g.,
`FRED_API_KEY` missing, network down), narrate the error to the user and
ask for the current rate manually — per D-12-LIVE02-01 + Pitfall 1
recovery contract. NEVER fabricate a rate; NEVER fall back to a stale cache
silently.

### SKILL.md grep contract (Plan 12-03 + Plan 12-08 jointly pin)

The following invariants are enforced by `tests/test_skill_md_fred.py`:

| Invariant | Pinned by |
|---|---|
| Heading `## Live Mortgage Rates` literal present | `test_skill_md_has_live_mortgage_rates_heading` |
| All 4 tokens present: `MORTGAGE30US`, `MORTGAGE15US`, `data/cache/fred_*`, `scripts/fred_cli.py` | `test_skill_md_cites_both_series_and_cache_paths` |
| FORBIDDEN: `` !` ``...`` `` `` shell-injection syntax | `test_skill_md_does_not_use_shell_injection_syntax` |
| Section precedes `## Math Discipline` | `test_skill_md_section_appears_before_math_discipline` |
| Token budget ≤ 4500 cl100k tokens | `test_skill_md_token_budget_after_phase12_insert` |
| Line budget ≤ 500 lines | `test_skill_md_line_budget_after_phase12_insert` |

The `` !` ``-injection form is FORBIDDEN because Anthropic Claude Code
support for SKILL.md inline-shell-injection is uncertain (12-RESEARCH.md
Open Question 1 — unresolved). Pattern A prose-only is the v1 contract;
v2 may revisit if Anthropic publishes definitive guidance.

### Loading-on-demand discipline (Phase 10 D-09)

This reference file is loaded ONLY when the borrower's prompt matches one
of the trigger phrases in SKILL.md's `## Loading Additional Context` table:

> "what's the current rate", "FRED", "MORTGAGE30US", "how do live rates work"

If the prompt does NOT match these phrases, the skill answers from
SKILL.md alone (the `## Live Mortgage Rates` section is itself ~14 lines
and lives inside the SKILL.md token budget). Eager-loading every reference
on every invocation would blow the 5k-token SKILL.md envelope (SKLL-01).

---

## 5. Eval Harness Integration

`evals/prompts/live-rate-injection-01.md` is the SC-1 closure eval per
D-12-SC1-01. The prompt has the borrower ask "what's the current 30-year
fixed mortgage rate?" — closing SC-1 end-to-end through SKILL.md
prose-only injection, NOT only via a structural grep test.

### CI determinism via fixture pinning

The eval pins to a FIXTURE cache value (NOT live FRED) so CI runs are
deterministic and cost-free:

- **Fixture cache:** `tests/fixtures/fred/MORTGAGE30US-2026-05-13.json`
  contains `"value": "6.50"` (synthetic; representative-of-2026-range; not
  an actual PMMS observation).
- **Oracle:** `evals/expected/live-rate-injection-01.json` pins
  `expected_numbers[0].value = "6.50"` with `provenance: "static"` —
  exempt from D-12-SC3-01's STDOUT-only sourcing requirement because the
  value comes from a cache file read, not a subprocess stdout. (The
  static-provenance exemption is the trade-off for legitimate static
  citations like the IRS Pub 936 cap; Plan 12-04 `evals/metrics.py`
  pin.)

Live FRED dispatch in CI is never run — the cost is non-zero, the network
is non-deterministic, and the FRED upstream may publish revisions that
flip the oracle silently. Nightly fixture refresh is documented in
`tests/fixtures/fred/README.md` per the Phase 11 D-02 synthetic-fixtures-only
pattern.

### Three-bucket gate per D-12-SC4-01

The 22-prompt eval set has:

- **13 anchored** prompts (12 mode-coverage + 1 live-rate-injection-01)
  — these contribute to the `numeric_match` denominator.
- **9 TBD-with-skip-pointer** prompts (refinance / stress / ARM modes that
  haven't shipped richer fixtures yet) — these report as `numeric_skip`,
  NEITHER pass NOR fail, and are excluded from the gate denominator.

Math: `13/(13+0) = 100% ≥ 95%` on a green run; `12/(12+1) = 92.3% < 95%`
on a single failure among the 13 anchored. The 9 skipped prompts each
carry a `defer_until_phase: N` pointer to the phase that will fill them
(discoverable via `/gsd-audit-uat`).

### D-12-SC3-01 STDOUT-only sourcing

The hallucination detector (Plan 12-04 `evals/metrics.detect_hallucinations`)
credits numbers as "sourced" only if they appear in `subprocess.stdout` of
a `scripts/*.py` invocation. Numbers from cmd args, stdin, or prose are
NOT credited. A complementary cross-check (Pitfall #2b): if `numeric_output`
is non-empty AND no script invocation occurred, the prompt fails BOTH
`numeric_match` and `route_match`. The `provenance: "static"` exemption
is the single trade-off escape hatch for legitimate cite-from-cache cases
like the FRED live-rate-injection prompt.

---

## 6. Pitfalls (verbatim from 12-RESEARCH.md §Common Pitfalls, applied)

The six pitfalls below are extracted verbatim from
`.planning/phases/12-fred-eval/12-RESEARCH.md` §Common Pitfalls. Each is
paired with the Phase 12 code-level mitigation.

### Pitfall 1: SKILL.md inline-shell injection silently fails when `FRED_API_KEY` is unset

**Root cause:** SKILL.md `` !` ``-style injection does not fail loud —
whatever the command emits to stdout (or stderr depending on shell) becomes
the rendered content.

**Mitigation:** `scripts/fred_cli.py` ALWAYS exits 0 with a JSON envelope.
On missing key: `{"error": "FRED_API_KEY not set in environment; ask the
user for the current rate.", "value": null, ...}`. SKILL.md prose around
the cache citation tells Claude what to do when the envelope's `error`
field is non-null. The v1 SKILL.md uses Pattern A prose-only injection
(NOT `` !` `` syntax) so the failure mode is even narrower — the recovery
contract only fires after a deliberate cache-miss recovery `Bash(...)` call.

### Pitfall 2: Cache TTL boundary off-by-one

**Root cause:** Strict-`<` vs `<=` ambiguity. FRED publishes Thursdays at
noon ET, so an entry fetched at Thursday 12:00:01 ET will be exactly 7 days
old the following Thursday at 12:00:01 ET — and the v1 convention says
that re-invocation that Thursday should refetch (catch the latest weekly
print).

**Mitigation:** `lib/fred_cache.py:is_fresh` uses `age < CACHE_TTL` (strict
less-than). 4 freezegun boundary tests at 6d-23h-59m / 7d / 8d /
lock-acquire pin the convention.

### Pitfall 3: Eval "passes" because the model parroted user-supplied numbers

**Root cause:** The grader extracts numbers from the model response, finds
them in some `subprocess.cmd` (because the user said "$400,000" and that
flowed into `--principal=400000`), and counts the prompt as `numeric_match`
— but the model NEVER actually ran the script.

**Mitigation:** D-12-SC3-01 tightens `detect_hallucinations` to credit only
`subprocess.stdout`. A complementary `route_match` cross-check (Pitfall
#2b in Plan 12-04): if `numeric_output` is non-empty AND no script
invocation occurred, the prompt fails BOTH gates.

### Pitfall 4: Replay transcript drift after a SKILL.md edit

**Root cause:** Replay transcripts are point-in-time snapshots. If
SKILL.md or `scripts/*.py` change after the recording, the replay no
longer reflects current behavior — CI says "green" but live would say
"regression."

**Mitigation:** v1 ships `replay-stub` mode that synthesizes transcripts
from `(prompt, oracle)` pairs at runtime — no recorded transcript files,
no drift surface. Live-mode driver is Phase 13+.

### Pitfall 5: 95% threshold is meaningless with too few prompts

**Root cause:** Small denominator amplifies noise. With 7 prompts, one
failure = 14.3% loss = 85.7% rate < 95%; the threshold is unattainable
in practice and the team disables the gate.

**Mitigation:** 22 prompts in v1 (13 anchored + 9 TBD-skip via the
D-12-SC4-01 three-bucket gate). At 13 anchored, the math is
`13/(13+0) = 100%` on a green run with 1 failure margin to
`12/(12+1) = 92.3% < 95%` — i.e., the gate is achievable AND meaningful.

### Pitfall 6: Transcript files leak the `FRED_API_KEY`

**Root cause:** Subprocess tracing or live-mode recording might capture
the actual FRED URL with the key, then a transcript commit leaks it.

**Mitigation:** All `source_url` fields ALWAYS use `api_key=***` redaction
at construction time. The redacted URL in `scripts/fred_cli.py` is built
independently of the real URL via hand-assembled string interpolation —
the real key NEVER str-interpolates into any output channel (T-12-01-02).
Defense in depth: the runner's transcript writer has a final `_redact()`
pass that regex-replaces `api_key=[A-Za-z0-9]{16,}` with `api_key=***`.

---

## Appendix: Citation Index

All URLs verified 2026-05-10 via the `/gsd-research-phase` audit pass.
Annual re-validation cadence: each calendar year, confirm each URL still
resolves; if any have moved, update the index below.

| Citation | Source | URL |
|---|---|---|
| FRED API `series_observations` endpoint | Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/docs/api/fred/series_observations.html |
| FRED API key registration | Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/docs/api/api_key.html |
| FRED API terms of use + rate limits | Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/docs/api/terms_of_use.html |
| MORTGAGE30US series page (PMMS source) | Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/series/MORTGAGE30US |
| MORTGAGE15US series page (PMMS source) | Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/series/MORTGAGE15US |
| Freddie Mac Primary Mortgage Market Survey (PMMS) | Freddie Mac | https://www.freddiemac.com/pmms |
| stefanoamorelli/fred-mcp-server v1.0.2 | GitHub | https://github.com/stefanoamorelli/fred-mcp-server |
| Anthropic Claude Code — MCP project-scoped config | Anthropic | https://code.claude.com/docs/en/mcp |
| Anthropic Claude Code — Skills documentation | Anthropic | https://code.claude.com/docs/en/skills |
| Smithery CLI (MCP server installer) | Smithery | https://smithery.ai/ |
| freezegun (TTL boundary mocking) | spulec / freezegun | https://github.com/spulec/freezegun |
| Phase 9 `orchestration/lockfile.mjs` pattern (source for `lib/fred_cache.py` Python port) | (internal) | `.planning/phases/09-persistence/09-*-SUMMARY.md` |

Cross-phase / internal references (always-present, verified by repo
structure):

- **Phase 12 plans** — `.planning/phases/12-fred-eval/12-00..08-PLAN.md` +
  paired SUMMARY files. 12-CONTEXT.md ratifies D-12-LIVE01-01 +
  D-12-LIVE02-01 + D-12-SC1-01 + D-12-SC3-01 + D-12-SC4-01.
- **CLAUDE.md External integrations** — points at this file for the full
  HTTP-canonical / MCP-optional decision rationale.
- **`.claude/agents/README.md` Phase 12 section** — browser-friendly
  summary of the optional MCP server registration recipe; NOT loaded into
  agent context.
- **`.claude/skills/mortgage-ops/SKILL.md` references table** — names this
  file as the on-demand load for "current rate" / "FRED" / "MORTGAGE30US"
  trigger phrases (D-09 progressive disclosure).
