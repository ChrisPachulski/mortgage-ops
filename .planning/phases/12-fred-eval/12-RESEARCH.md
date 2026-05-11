# Phase 12: FRED MCP Live Rates & Eval Harness — Research

**Researched:** 2026-05-02
**Domain:** Live data injection (FRED MCP / FRED HTTP API / SKILL.md dynamic-context-injection) + skill quality regression harness (route-match + numeric-match + traceability)
**Confidence:** HIGH on mechanics (skill spec + FRED API + freezegun); MEDIUM on operational choices (CI vs nightly cadence) — the planner should ratify the discretion areas at `/gsd-discuss-phase 12`.

## Summary

Phase 12 has two halves bound by the success criteria:

1. **Live rates (LIVE-01..04):** Wire the FRED MCP server (`stefanoamorelli/fred-mcp-server`) so the skill can quote the latest weekly `MORTGAGE30US` (and optional `MORTGAGE15US`) rate inside reports. SC-1 specifies inline `` !`fred-cli get MORTGAGE30US --latest` `` shell injection in SKILL.md — that exact `fred-cli` binary does **not exist in the upstream repo** [VERIFIED: GitHub README, 2025-01 release v1.0.2]. The FRED MCP server only exposes MCP tools (`fred_get_series`, etc.), not a CLI. So Phase 12 must **ship its own thin `scripts/fred_cli.py`** (mortgage-ops convention: bundled inside `.claude/skills/mortgage-ops/scripts/`) that wraps the FRED HTTP API directly (`api.stlouisfed.org/fred/series/observations`). The MCP server is registered separately so the agent has a tools-API path for ad-hoc series exploration; SKILL.md's load-time injection uses our `fred_cli.py`. SC-2 requires a 7-day TTL cache file with refetch-on-stale verified by mocking time.

2. **Eval harness (EVAL-01..04):** Build `evals/runner.py` plus `evals/prompts/` (markdown + frontmatter) and `evals/expected/` (JSON). Two execution modes: **transcript-replay** (CI-cheap, deterministic; replays cached `(prompt, response, subprocess-trace)` tuples) and **live-LLM** (nightly/on-demand; actually invokes Claude). Both modes feed the same grader. The grader computes two headline metrics: `route_match_rate` (% prompts where the right mode + scripts were invoked, parsed from the transcript's `Bash(...)` calls) and `numeric_match_rate` (% prompts where every reported number matches an `expected_numbers[i]` within tolerance). SC-3 (Pitfall #2 detection) is the harder constraint: every $-amount in the model's response **must** trace to some captured subprocess stdout — implemented as a numeric set-difference assertion with formatting normalization (`$1,234.56` ≡ `1234.56`).

**Primary recommendation:** Treat SC-1's `fred-cli` literal as a placeholder for "some shell command that prints the latest MORTGAGE30US rate." Ship `scripts/fred_cli.py` (Python, no extra deps beyond stdlib `urllib` + project `pydantic`) bundled inside the skill. Register the FRED MCP server in `.mcp.json` for richer ad-hoc queries by the agent, but do not depend on it for the SKILL.md injection — keep the load-bearing path on our own script for testability. Use **freezegun** for SC-2 cache TTL mocking (pinned and consistent with the project's hand-calculated golden-fixture discipline). Run the **transcript-replay eval mode in CI on every push**; run the **live-LLM eval mode nightly** via a single GitHub Action (or local cron) so cost stays bounded and the headline 95% threshold is computed against deterministic regression baselines.

## Architectural Responsibility Map

Phase 12 spans three architectural tiers in this codebase:

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FRED HTTP fetch + cache | `scripts/` (skill bundle) | `lib/` (none — keep it in scripts since it's I/O, not pure math) | Per project doctrine, anything that touches a network or file-system cache lives in `scripts/`; `lib/` stays pure-Decimal math. The FRED fetcher returns a JSON envelope to stdout; the skill ingests via `!`...`` injection. |
| FRED MCP server registration | Project root (`.mcp.json`) | `.claude/skills/mortgage-ops/` (none — MCP servers register at the project, not skill, level) | MCP server config in Claude Code is project-scoped via `.mcp.json` per [Claude Code MCP docs]. The skill *uses* the registered server but does not own its config. |
| Inline rate injection in SKILL.md | `.claude/skills/mortgage-ops/SKILL.md` (Phase 10 surface) | — | Skill content owns load-time `!`...`` syntax per Anthropic skills spec. Phase 10 ships SKILL.md scaffolding; Phase 12 fills in the FRED line. |
| Eval prompts (input fixtures) | `evals/prompts/*.md` (project root, mirrors `tests/fixtures/`) | — | Eval prompts are test inputs; they live alongside the runner, not inside the skill bundle (skill bundle is portable to other consumers; evals are a dev artifact). |
| Eval expected JSON (oracles) | `evals/expected/*.json` | — | Same reasoning as prompts — these are dev/test artifacts. |
| Eval runner | `evals/runner.py` | — | Test harness. Imports from `lib/` only via subprocess (it invokes `scripts/`); does not import `lib.*` directly so it can also drive the live-LLM mode without coupling. |
| Cached transcripts (replay mode) | `evals/transcripts/*.json` (gitignored if PII-bearing; otherwise committed for CI determinism) | — | Replay mode deterministic baseline. Recorded once via `--record` flag, replayed in CI. |
| Live-LLM driver (nightly only) | `evals/runner.py --mode live` | `.github/workflows/evals-nightly.yml` (or `crontab` recipe) | Cost discipline: do not run live LLM on every CI push. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `freezegun` | latest (>=1.5) | Mock `datetime.now()` / `time.time()` for SC-2 7-day TTL cache test [CITED: github.com/spulec/freezegun] | Mocks all of `datetime.datetime.now/utcnow`, `datetime.date.today`, `time.time/monotonic/perf_counter` consistently; idiomatic for TTL tests; works as decorator OR context manager [VERIFIED: ctx7 freezegun lookup] |
| Python `urllib.request` (stdlib) | n/a | HTTP fetch of `api.stlouisfed.org/fred/series/observations` from `scripts/fred_cli.py` | Project convention is "no new deps unless needed" (Phase 5 inherited constraint). FRED API is a single GET with query params — `urllib.request.urlopen` + `json.loads` suffices. Avoids adding `requests` / `httpx` to the dep tree. |
| `pydantic` | >=2.13.3 (already in pyproject.toml) | Validate FRED response envelope; validate eval prompt frontmatter + expected JSON schema | Project standard; reuse strict+frozen+forbid pattern from Phases 1–5 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-frontmatter` | >=1.1 | Parse `---` YAML frontmatter from `evals/prompts/*.md` | Standard for markdown-with-frontmatter; alternative is to roll our own with `yaml.safe_load` + string splitting — recommend the library for parser-correctness. **[ASSUMED]** library is current — verify with `npm view`/PyPI before locking. |
| Anthropic Python SDK (`anthropic`) | >=0.40 | Live-LLM eval mode driver — invoke Claude API for nightly evals | Only needed when `evals/runner.py --mode live`; can be an optional dep group (`[project.optional-dependencies] evals-live = ["anthropic>=0.40"]`) so CI doesn't pull it. **[ASSUMED]** version is current — planner should pin via `pip index versions anthropic` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `urllib.request` | `httpx` or `requests` | Cleaner ergonomics + retry/timeout primitives, but adds a runtime dep. Project doctrine: avoid unless math-or-correctness benefit. Stick with urllib for the single GET. |
| `freezegun` | `time-machine` (Adam Johnson) | `time-machine` is faster (uses ctypes); `freezegun` is more battle-tested and has near-zero install friction. For a 7-day TTL test that runs once, `freezegun` wins on simplicity [CITED: betterstack.com/community/guides/testing/time-machine-vs-freezegun]. |
| Our own `scripts/fred_cli.py` | Use the `stefanoamorelli/fred-mcp-server` CLI wrapper | The repo provides MCP tools only — `fred_get_series` is invoked via the MCP protocol, not a shell. SKILL.md `!`...`` syntax requires a shell command that produces stdout. So we either (a) write a thin shell wrapper that calls the MCP server (complex, requires MCP client), or (b) hit the FRED HTTP API directly with our own script (simple, ~50 lines). Recommend (b). The MCP server stays registered for ad-hoc agent queries via the MCP tool API. |
| Live-LLM eval as primary mode | Transcript-replay as primary | Live-LLM is non-deterministic (sampling temperature, model drift) and costly. Transcript-replay gives deterministic CI; live-LLM is the periodic ground-truth check. |

**Installation (planner adds to pyproject.toml):**
```toml
[dependency-groups]
dev = [
    "pytest>=9.0",
    "mypy>=1.20",
    "ruff>=0.15",
    "pre-commit>=4.6",
    "freezegun>=1.5",            # SC-2 cache TTL mocking
    "python-frontmatter>=1.1",   # parse evals/prompts/*.md frontmatter
]

[project.optional-dependencies]
evals-live = [
    "anthropic>=0.40",           # only when runner.py --mode live
]
```

**Version verification (PRE-PLAN ACTION for planner):**
```bash
pip index versions freezegun python-frontmatter anthropic
```

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User in Claude Code session                     │
│                  asks: "what's a $400k 30yr at current rates?"           │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│      .claude/skills/mortgage-ops/SKILL.md (Phase 10 ships scaffold)      │
│                                                                          │
│  ## Current rates                                                        │
│  - 30yr: !`python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE30US`  │ ← Phase 12
│  - 15yr: !`python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE15US`  │ ← Phase 12
│                                                                          │
│  ## Routing: pick a mode (evaluate, compare, refinance, ...)             │
└────┬───────────────────────────────────────────────────────────┬────────┘
     │ skill load-time: shell injection runs                     │ skill load-time
     ▼                                                            ▼
┌─────────────────────────┐         ┌───────────────────────────────────────┐
│ scripts/fred_cli.py     │         │  (parallel: same fetch for 15yr)      │
│ (Phase 12)              │         └───────────────────────────────────────┘
│                         │
│ 1. Read TTL cache       │
│    evals/cache/         │
│    fred-cache.json      │
│ 2. If fresh (<7d) → use │
│ 3. Else: GET            │
│    api.stlouisfed.org/  │
│    fred/series/         │
│    observations         │
│ 4. Write cache + emit   │
│    JSON to stdout       │
└────┬────────────────────┘
     │ stdout JSON gets injected into SKILL.md content as Claude sees it
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│        Claude reads enriched SKILL.md, routes to a mode (evaluate)       │
│        invokes scripts/amortize.py (Phase 3) → narrates report           │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ user-facing report (markdown)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Eval harness (offline, CI / nightly)                   │
│                                                                          │
│   evals/prompts/*.md  →  runner.py  →  evals/expected/*.json             │
│                              │                                           │
│           ┌──────────────────┼──────────────────────┐                    │
│           ▼                  ▼                      ▼                    │
│   transcript-replay     live-LLM (nightly)    grader: route_match,       │
│   (CI default,           Anthropic SDK         numeric_match,            │
│    deterministic)        $-cost gated          Pitfall #2 traceability   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
mortgage-ops/
├── .claude/
│   ├── mcp.json                          # NEW (Phase 12): registers FRED MCP server
│   └── skills/mortgage-ops/
│       ├── SKILL.md                      # Phase 10 owns scaffold; Phase 12 adds the !`fred_cli` lines
│       └── scripts/
│           ├── amortize.py               # Phase 10 relocates from scripts/ (already exists)
│           ├── ...
│           └── fred_cli.py               # NEW (Phase 12): live FRED rate fetch + 7d TTL cache
├── evals/                                # NEW (Phase 12): eval harness root
│   ├── runner.py                         # transcript-replay + live-LLM modes
│   ├── prompts/                          # *.md with frontmatter
│   │   ├── evaluate-01.md
│   │   ├── evaluate-02.md
│   │   ├── compare-01.md
│   │   ├── refinance-01.md
│   │   ├── affordability-01.md
│   │   ├── stress-01.md
│   │   ├── amortize-01.md
│   │   ├── arm-01.md
│   │   └── ... (≥21 total per Q(h))
│   ├── expected/                         # *.json — one per prompt
│   │   ├── evaluate-01.json
│   │   └── ...
│   ├── transcripts/                      # cached transcripts for replay mode
│   │   └── *.jsonl                       # one per prompt; recorded via --record
│   └── cache/
│       └── fred-cache.json               # SC-2 TTL cache (gitignored)
└── tests/
    └── test_fred_cli.py                  # NEW: SC-1 + SC-2 unit tests (incl. freezegun TTL)
    └── test_evals_runner.py              # NEW: runner unit tests + Pitfall #2 detection algorithm
```

### Pattern 1: SKILL.md dynamic context injection

**What:** Anthropic's official skills spec supports `` !`<command>` `` (single-line) and ` ```!\n<commands>\n``` ` (multi-line block) for shell-command execution at skill load time. The command's stdout replaces the placeholder before Claude sees the rendered SKILL.md content. [CITED: https://code.claude.com/docs/en/skills, section "Inject dynamic context"]

**When to use:** Any time the skill needs current data that the user hasn't provided. For mortgage-ops, this is the live rate.

**Failure modes (verbatim from docs research + spec inspection):**
- **Command exits non-zero:** The output (including stderr if captured by the shell pipeline) replaces the placeholder. The skill content is still rendered; Claude will see whatever the command printed. *Mitigation:* `scripts/fred_cli.py` MUST always exit 0 and emit a JSON envelope with an `error` field on failure (network down, API down, FRED_API_KEY missing) — matches Phase 3 WR-02 6-key envelope discipline. Claude is then told (in SKILL.md prose) "if the rate field is null, fall back to a user-supplied rate."
- **Command not found:** Same as above — the shell error message replaces the placeholder. *Mitigation:* `${CLAUDE_SKILL_DIR}` substitution makes the path absolute and stable [CITED: skills doc, "Available string substitutions"]. We invoke `python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE30US` so we don't depend on a `fred_cli` PATH binary.
- **`disableSkillShellExecution: true` set in settings:** Each command becomes the literal string `[shell command execution disabled by policy]`. *Mitigation:* document in SKILL.md narrative that "if rate injection is disabled, ask the user for the current rate."
- **Command takes too long:** Anthropic docs do not document a timeout for `!`...`` injection — empirically, slow commands block skill load. *Mitigation:* `fred_cli.py` MUST short-circuit to the cache (no network) when the cache is fresh; only refetch when stale. The 7-day TTL keeps the network path off the critical path most of the time.

**Example (the actual SKILL.md fragment Phase 12 ships):**
```markdown
## Current weekly rates (Freddie Mac PMMS via FRED)

- 30-year fixed (MORTGAGE30US): !`python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE30US`
- 15-year fixed (MORTGAGE15US): !`python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE15US`

These rates are the most recent weekly observations from Freddie Mac's
Primary Mortgage Market Survey, retrieved via the FRED API. If a rate
field is null, ask the user to supply the current rate manually.
```

The `python` invocation form is portable across macOS / Linux / Windows-WSL and aligns with how Phase 10 will relocate `scripts/amortize.py` (also Python). The `${CLAUDE_SKILL_DIR}` substitution is the Anthropic-blessed way to make script paths skill-relative regardless of where the skill is installed.

### Pattern 2: TTL cache file with refresh-on-stale

**What:** A single-file JSON cache keyed by series ID. Read at the top of every `fred_cli.py` invocation; refetch the network on cache-miss OR cache-stale (>7 days).

**When to use:** Whenever a remote rate is queried. SC-2 explicitly requires this.

**Cache JSON schema (PINNED for Phase 12):**
```json
{
  "schema_version": 1,
  "entries": {
    "MORTGAGE30US": {
      "value": "6.84",
      "observation_date": "2026-04-25",
      "fetched_at": "2026-04-26T17:00:03Z",
      "source_url": "https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key=***&file_type=json&sort_order=desc&limit=1",
      "fred_realtime_start": "2026-04-26",
      "fred_realtime_end": "2026-04-26"
    },
    "MORTGAGE15US": {
      "value": "6.05",
      "observation_date": "2026-04-25",
      "fetched_at": "2026-04-26T17:00:04Z",
      "source_url": "...",
      "fred_realtime_start": "2026-04-26",
      "fred_realtime_end": "2026-04-26"
    }
  }
}
```

Notes on the schema:
- `value` is a **string**, not a float. Per project money-discipline, we never serialize numerics as JSON floats. The downstream consumer (the agent reading SKILL.md) treats it as a percentage rendering ("6.84%").
- `observation_date` is the FRED-reported observation date (the Thursday of the survey week).
- `fetched_at` is **our** fetch timestamp in UTC ISO-8601 with `Z` suffix — that's what the TTL check compares against.
- `source_url` redacts the API key (`api_key=***`) for the committed cache file's audit trail; the real key never lands on disk.
- `fred_realtime_start/end` mirrors the FRED response — useful to detect FRED revisions.

**TTL check pseudocode (PINNED for Phase 12):**
```python
from datetime import datetime, timezone, timedelta

CACHE_TTL = timedelta(days=7)

def is_fresh(entry: dict) -> bool:
    """SC-2: refetch when entry is older than 7 days."""
    fetched_at = datetime.fromisoformat(entry["fetched_at"].replace("Z", "+00:00"))
    age = datetime.now(timezone.utc) - fetched_at
    return age < CACHE_TTL  # strict <, so 8-day-old => stale => refetch
```

**Time-mock strategy for SC-2 test:**
```python
import freezegun

def test_eight_day_old_cache_triggers_refetch(tmp_path, monkeypatch):
    # Seed cache file with fetched_at = 2026-04-25T12:00:00Z
    cache_file = tmp_path / "fred-cache.json"
    cache_file.write_text(json.dumps({
        "schema_version": 1,
        "entries": {
            "MORTGAGE30US": {
                "value": "6.84",
                "observation_date": "2026-04-25",
                "fetched_at": "2026-04-25T12:00:00Z",
                # ...
            }
        },
    }))

    # Stub the network to detect refetch
    network_calls = []
    def fake_fetch(series_id, api_key):
        network_calls.append(series_id)
        return {"value": "6.92", "observation_date": "2026-05-03",
                "fred_realtime_start": "2026-05-03", "fred_realtime_end": "2026-05-03"}
    monkeypatch.setattr("scripts.fred_cli._fetch_from_fred", fake_fetch)
    monkeypatch.setenv("FRED_API_KEY", "test-key")

    # Freeze time at 8 days after fetched_at
    with freezegun.freeze_time("2026-05-03T12:00:01Z"):
        result = fred_cli.get("MORTGAGE30US", cache_path=cache_file)

    assert network_calls == ["MORTGAGE30US"]              # refetch happened
    assert result["value"] == "6.92"                       # new value
    assert json.loads(cache_file.read_text())["entries"]["MORTGAGE30US"]["value"] == "6.92"
    # ... and the symmetric test with freeze_time("2026-05-02T12:00:00Z") (6d 23h 59m) asserts NO refetch
```

The `freezegun.freeze_time` context manager covers all of `datetime.now`, `datetime.utcnow`, `time.time`, `time.monotonic`, `time.perf_counter` — so even if we later swap `datetime.now(tz=UTC)` for `time.monotonic()`-based TTL, the test stays correct [CITED: https://github.com/spulec/freezegun].

### Pattern 3: Eval prompt format (markdown + frontmatter)

**What:** One markdown file per benchmark prompt. YAML frontmatter declares routing + numeric expectations (machine-readable). Body is the natural-language prompt the user would send.

**PINNED format:**
```markdown
---
id: evaluate-01
mode: evaluate
description: Single-loan evaluation for a $400k conforming 30yr at 6.5% — Wikipedia oracle.
expected_route_keywords:
  - "evaluate"
  - "Phase 3 amortize"
expected_scripts:
  - script: amortize.py
    args_must_include:
      - "--input"
    args_must_match_regex:
      principal: "400000"
      annual_rate: "0\\.065"
      term_months: "360"
expected_numbers:
  - label: monthly_pi
    value: 2528.27
    tolerance: 0.005      # absolute, in dollars; matches Phase 3 quantize-to-cent ± half-cent slack
    source_script: amortize.py
  - label: total_interest
    value: 510178.36
    tolerance: 1.0
    source_script: amortize.py
expected_apr_literal: false   # only set true on prompts that should mention "estimated APR"
---

I am buying a house with a $400,000 mortgage at a 6.5% fixed rate for 30 years.
Walk me through the monthly payment and total interest. Use today's tax assumptions.
```

Notes:
- `id` is the filename stem; runner uses it to look up `evals/expected/{id}.json`.
- `mode` is the expected SKILL.md mode the agent should route to.
- `expected_route_keywords` are substrings the runner greps in the transcript to verify routing happened (cheap heuristic; sufficient until the skill emits structured route-markers in v2).
- `expected_scripts[].args_must_match_regex` lets us assert that the agent passed the right loan parameters into the script — this is what closes Pitfall #2 from the **input** side (the agent didn't make up principal). The **output** side is closed by `expected_numbers` + the traceability check.
- `expected_apr_literal` forces the SC for Phase 7's "estimated APR" wording (Q(i)) on the relevant prompts.
- `tolerance` is an **absolute** tolerance, not relative — for $-amounts at the cent level, absolute tolerance avoids the divide-by-zero / scale issues that relative tolerance has.

### Pattern 4: Eval expected JSON format (oracle)

**What:** One JSON file per prompt. Mirrors the frontmatter but normalized to JSON for unambiguous machine consumption. The runner cross-checks frontmatter against expected JSON on load to prevent drift.

**PINNED format:**
```json
{
  "schema_version": 1,
  "id": "evaluate-01",
  "mode": "evaluate",
  "expected_scripts": [
    {
      "script": "amortize.py",
      "args_must_include": ["--input"],
      "args_must_match_regex": {
        "principal": "400000",
        "annual_rate": "0\\.065",
        "term_months": "360"
      }
    }
  ],
  "expected_numbers": [
    { "label": "monthly_pi",     "value": "2528.27",   "tolerance": "0.005", "source_script": "amortize.py" },
    { "label": "total_interest", "value": "510178.36", "tolerance": "1.0",   "source_script": "amortize.py" }
  ],
  "expected_route_keywords": ["evaluate", "Phase 3 amortize"],
  "expected_apr_literal": false,
  "v1_frozen_at": "2026-05-02"
}
```

Notes:
- `value` and `tolerance` are JSON **strings** (not floats) per project money-discipline (Phase 1 D-08 inheritance). The runner parses both to `Decimal` before comparing.
- `v1_frozen_at` lets us track when this oracle was last re-validated; bumping the threshold (95% rate) is a deliberate edit, not a silent drift.
- The `_must_include` / `_must_match_regex` shape lets a single oracle fixture cover scripts that take JSON-stdin (Phase 3+ idiom: `--input fixture.json`) AND scripts that take CLI flags. The runner inspects the recorded subprocess command-line.

### Pattern 5: Runner mechanics — replay and live modes

**What:** Single `evals/runner.py` driver, two execution modes selected by `--mode {replay,live}`. Both modes produce the same `EvalResult` dataclass shape; the grader is mode-agnostic.

**Mode A: transcript-replay (CI default)**

Replay mode loads pre-recorded transcripts from `evals/transcripts/<prompt-id>.jsonl` and feeds them through the grader without invoking Claude or any subprocess. Transcripts are recorded once via `runner.py --mode live --record`.

Pseudocode:
```python
def run_replay(prompt_id: str) -> EvalResult:
    """Deterministic CI mode: replay a recorded (model_response, subprocess_calls) tuple."""
    expected = load_expected(f"evals/expected/{prompt_id}.json")
    transcript = load_transcript(f"evals/transcripts/{prompt_id}.jsonl")
    # transcript shape:
    #   {"type": "user_prompt", "content": "..."}
    #   {"type": "subprocess", "cmd": ["python", "scripts/amortize.py", "--input", "..."],
    #    "stdin": "{...}", "stdout": "{...}", "stderr": "", "returncode": 0}
    #   {"type": "subprocess", ...}
    #   {"type": "model_response", "content": "Your monthly payment is $2,528.27 ..."}
    return grade(transcript, expected)
```

**Mode B: live-LLM (nightly / on-demand)**

Live mode actually invokes the Anthropic API, captures the model's tool calls (specifically Bash invocations of our scripts), and writes a transcript to disk. The transcript can then become a new replay baseline.

Pseudocode:
```python
def run_live(prompt_id: str, record: bool = False) -> EvalResult:
    """Authoritative mode: invoke Claude, capture transcript + subprocess calls."""
    import anthropic
    expected = load_expected(f"evals/expected/{prompt_id}.json")
    prompt_md = load_prompt(f"evals/prompts/{prompt_id}.md")

    # Wrap subprocess.run so every call into scripts/ is captured.
    transcript = []
    captured_calls = []
    def trace_subprocess(cmd, **kwargs):
        result = subprocess.run(cmd, **kwargs, capture_output=True, text=True)
        captured_calls.append({
            "type": "subprocess",
            "cmd": cmd,
            "stdin": kwargs.get("input", ""),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        })
        return result

    # Drive Claude with computer-use / tool-use; for our purposes the agent
    # has Bash access scoped to scripts/ and SKILL.md is preloaded.
    # NOTE: the simplest live driver uses `claude -p "<prompt>"` (Claude Code CLI
    # in non-interactive mode) with --output-format json; that also captures
    # tool calls. Recommend this over the raw SDK for round-1 because it
    # transparently uses the SAME skill resolution path real users hit.
    response = invoke_claude_code(prompt_md.content, scripts_root=SCRIPTS_DIR,
                                  trace=trace_subprocess)

    transcript = [
        {"type": "user_prompt", "content": prompt_md.content},
        *captured_calls,
        {"type": "model_response", "content": response.text},
    ]
    if record:
        save_transcript(f"evals/transcripts/{prompt_id}.jsonl", transcript)
    return grade(transcript, expected)
```

The recommended live driver uses `claude -p "<prompt>" --output-format json` (Claude Code's non-interactive mode) so the agent runs through the same skill resolution path real users hit — including SKILL.md `!`...`` injection. This sidesteps the problem of having to re-implement skill-loading in the runner. **[ASSUMED]** `claude -p` with skills support exists and produces parsable JSON — planner should verify this claim with `claude --help` before committing to the SDK-vs-CLI choice. If the CLI driver is unavailable/unstable, fall back to the Anthropic SDK with manual skill-content concatenation (more code, less fidelity).

### Pattern 6: Pitfall #2 detection algorithm (SC-3)

**What:** Every $-amount mentioned in the model response **must** appear in some captured `scripts/` subprocess stdout. If any reported number doesn't trace back, the eval fails — that's a hallucinated number per Pitfall #2.

**Algorithm (PINNED pseudocode):**
```python
import re
from decimal import Decimal

# Match "$1,234.56" or "$1234.56" or bare "1234.56" with at least one decimal digit
NUMBER_REGEX = re.compile(r"\$?(\d{1,3}(?:,\d{3})*|\d+)\.\d{1,4}\b")

def normalize(num_str: str) -> Decimal:
    """'$1,234.56' -> Decimal('1234.56')"""
    cleaned = num_str.replace("$", "").replace(",", "")
    return Decimal(cleaned)

def extract_numbers(text: str) -> set[Decimal]:
    return {normalize(m.group(0)) for m in NUMBER_REGEX.finditer(text)}

def detect_hallucinated_numbers(
    model_response: str,
    subprocess_calls: list[dict],
    tolerance: Decimal = Decimal("0.005"),  # half-cent slack for last-digit rounding
) -> list[Decimal]:
    """
    Return the set of numbers in model_response that do NOT appear (within
    tolerance) in any subprocess stdout. Empty list = no hallucinations.
    """
    response_nums = extract_numbers(model_response)

    script_nums: set[Decimal] = set()
    for call in subprocess_calls:
        if call["type"] != "subprocess":
            continue
        # The script may emit numbers in JSON with quoting; normalize the same way.
        script_nums.update(extract_numbers(call.get("stdout", "")))
        # Also accept inputs the script read — args/stdin contain user-supplied
        # principals/rates that should not be flagged as hallucinations.
        script_nums.update(extract_numbers(" ".join(call.get("cmd", []))))
        script_nums.update(extract_numbers(call.get("stdin", "")))

    hallucinated = []
    for r in response_nums:
        if not any(abs(r - s) <= tolerance for s in script_nums):
            hallucinated.append(r)
    return hallucinated

# In the grader:
hallucinated = detect_hallucinated_numbers(response, subprocess_calls)
assert hallucinated == [], (
    f"SC-3 violation (Pitfall #2): {hallucinated} appear in the model response "
    f"but trace to no scripts/ invocation."
)
```

Notes / edge cases:
- The tolerance accommodates the case where the agent rounds: script emits `2528.27`, model writes `$2,528.27` — exact match. But if script emits `0.065` (rate) and model writes `6.50%` — the percentage-vs-decimal mismatch trips the regex. **Mitigation:** strip `%` characters and re-divide by 100 in a second pass, OR have the script emit both `0.065` and `6.50%` in stdout. Recommend the latter (script-side normalization) so the grader stays simple.
- "Year counts" (e.g., `30 years`) and "term months" (`360`) match the regex (`30.0` and `360.00` if the model writes them with decimals). Add to expected_numbers if relevant; they will trace to `cmd` args naturally.
- Dates like `2026-05-02` don't match the regex (`2026-05` has `-` in the middle, not `.`).
- The grader reports the offending number(s) with surrounding context for human review.

### Pattern 7: Routing + numeric match-rate metrics (SC-4)

**What:** Two headline percentages computed across the v1 prompt set.

```python
@dataclass
class HarnessReport:
    n_prompts: int
    route_match_count: int
    numeric_match_count: int
    pitfall2_clean_count: int  # SC-3 sub-metric
    failures: list[FailureReport]

    @property
    def route_match_rate(self) -> float:
        return self.route_match_count / self.n_prompts

    @property
    def numeric_match_rate(self) -> float:
        return self.numeric_match_count / self.n_prompts

# A prompt counts as route_match if:
#   - The transcript contains every keyword in expected_route_keywords (substring match)
#   - AND every script in expected_scripts[].script appears in some captured cmd[1] or cmd[-1]
#   - AND every args_must_include flag is present in that cmd
#   - AND every args_must_match_regex pattern matches some arg or stdin field

# A prompt counts as numeric_match if:
#   - For every entry in expected_numbers, some number within `tolerance` of `value`
#     appears in the model_response text
#   - AND the Pitfall #2 detector returns []

# SC-4 gate: route_match_rate >= 0.95 AND numeric_match_rate >= 0.95
```

### Anti-Patterns to Avoid

- **Caching the FRED API key in the cache file.** Redact to `api_key=***` in `source_url`. Keep the real key in env / `.env` (gitignored) only.
- **Asserting on exact model output strings.** Models drift; assertions must be on routing decisions + numeric values + Pitfall #2 traceability. (Anthropic's skill-creator doc explicitly warns against this — "LLM outputs shift between model versions, so assertions need to be behavioral, not textual.")
- **Computing percentages with `<`, not `<=`.** A 7.0-day-old cache should be refetched, not used. Use `if age < CACHE_TTL` for "still fresh"; equivalently `if age >= CACHE_TTL: refetch`.
- **Using `requests` / `httpx` in `scripts/fred_cli.py`.** Project doctrine: stdlib only when the math/correctness benefit is zero. The single FRED GET is ~10 lines with `urllib`.
- **Letting the eval runner import `lib.amortize` directly.** The runner must drive the same path the agent does (subprocess into `scripts/amortize.py`). Direct lib imports would mean the eval is testing the lib, not the skill+lib glue.
- **Running live-LLM evals on every CI push.** Cost discipline: SC-4's 95% threshold is computed against deterministic replay transcripts in CI; live mode is nightly (or on-demand) and may report a different rate that we then debug.
- **Trusting one prompt per mode.** With 7 modes × 1 prompt each = 7 prompts, the granularity of `numeric_match_rate` is 14.3% — a single failure crosses the 95% threshold. See Q(h) below.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mocking time for 7-day TTL test | Custom `monkeypatch.setattr(datetime, 'now', ...)` web | `freezegun.freeze_time(...)` | Freezegun handles `datetime.now`, `utcnow`, `today`, `time.time`, `time.monotonic`, `time.perf_counter`, `time.gmtime`, `time.localtime` consistently; manual monkeypatching misses one of these and the test silently passes [CITED: spulec/freezegun README] |
| FRED API client | Hand-rolled `requests.Session` with retry-backoff | Stdlib `urllib.request.urlopen(url, timeout=10)` + JSON decode | A single GET with redacted query string. Adding `requests` + `urllib3` to the dep tree for one call violates project lean-deps doctrine. |
| Markdown-with-frontmatter parser | `yaml.safe_load(text.split('---')[1])` string acrobatics | `python-frontmatter` library | Edge cases (escaped `---` in body, BOM, mixed line endings) silently break the home-rolled parser. |
| Driving Claude in live mode | Roll your own SDK call with manual skill-content concat | `claude -p "<prompt>" --output-format json` (Claude Code non-interactive) — **[ASSUMED]** verify the flag exists | Re-using the real Claude Code skill resolution path is the only way to evaluate the SAME pipeline real users hit. SDK-with-manual-concat would test a different (worse) pipeline. |
| Numeric extraction regex | Custom tokenizer | Single regex `r"\$?(\d{1,3}(?:,\d{3})*|\d+)\.\d{1,4}\b"` | Battle-tested; handles `$1,234.56`, `1234.56`, `$0.50`. We DO hand-roll this (it's 1 line) but resist the temptation to grow it into a parser; instead add normalization passes (strip `%`, re-divide). |

**Key insight:** This phase is mostly glue. The "don't hand-roll" rule is sharp here because every dep we add to a personal-use tool has to justify itself — but the four items above (`freezegun`, `python-frontmatter`, `urllib`, `claude -p`) all carry their weight by collapsing dozens of edge cases.

## Runtime State Inventory

> Phase 12 is greenfield — no rename / refactor / migration. **Section omitted per RESEARCH.md spec.**
>
> (Trivial cross-check: no string is being renamed; no datastore exists yet for evals; the FRED cache is a new artifact at first run; no OS-level registrations; FRED_API_KEY is a NEW env var introduced this phase. There is one `.gitignore` entry to add: `evals/cache/fred-cache.json` (contains the latest rate, not PII, but no reason to commit). The planner will add this in the gitignore plan.)

## Common Pitfalls

### Pitfall 1: SKILL.md `!`...`` injection silently fails when FRED_API_KEY is unset

**What goes wrong:** User clones the repo, sets up the skill, runs Claude. SKILL.md tries to inject the FRED rate, but `FRED_API_KEY` isn't in their environment. The shell command exits with an error message; that error gets injected into SKILL.md. Claude sees garbled context, may hallucinate a rate, or may proceed with confused routing.

**Why it happens:** SKILL.md `!`...`` doesn't fail loud — whatever the command emits to stdout (or even stderr depending on shell) becomes the rendered content.

**How to avoid:**
- `scripts/fred_cli.py` ALWAYS exits 0 and ALWAYS emits valid JSON.
- On missing API key: `{"error": "FRED_API_KEY not set", "value": null, "instruction": "ask the user for the current rate"}`.
- SKILL.md prose around the `!`...`` line tells Claude what to do when the rate is null.

**Warning signs:**
- Eval transcript shows the `error` envelope from `fred_cli.py` — failing the `expected_numbers` check is fine, but the SC-1 eval-asserts-the-rate-appears check fails for the wrong reason. Add a sub-check: "if rate field is null, the prompt is skipped from numeric_match_rate computation but counted in a third metric `live_data_skip_rate`."

### Pitfall 2: Cache TTL boundary off-by-one

**What goes wrong:** Test asserts that a 7.0-day-old cache is fresh (or stale, depending on convention). Convention drift between code and test causes a flaky-CI flop on Thursday-at-noon-UTC re-runs.

**Why it happens:** Strict-`<` vs `<=` ambiguity at the boundary; FRED publishes Thursdays at noon ET, so an entry fetched at Thursday 12:00:01 ET will be exactly 7 days "old" the following Thursday at 12:00:01 — does that count?

**How to avoid:**
- Pinning above: `if age < CACHE_TTL` (strict less-than) means age == 7d EXACTLY is stale → refetch. Document this in `fred_cli.py` docstring with a citation to this RESEARCH.md.
- Test 6d-23h-59m (fresh) AND 7d-0h-0s (stale) AND 8d (stale) — three boundary cases.
- Document in Phase 12 PITFALLS.md (per project convention).

**Warning signs:**
- A test passes locally but fails in CI on a specific weekday — likely TZ mismatch between test machines.

### Pitfall 3: Eval "passes" because the model parroted user-supplied numbers

**What goes wrong:** The grader extracts numbers from the model response, finds them in some `subprocess.cmd` (because the user said "$400,000" in the prompt and that flowed into `--principal=400000`), and counts the prompt as numeric_match. But the model NEVER ACTUALLY RAN the script — it just echoed back the user's number.

**Why it happens:** The traceability check accepts numbers from cmd args as valid (necessary — the principal IS a real input). If the prompt happens to include a number that matches the expected output, the check is fooled.

**How to avoid:**
- `expected_scripts[]` MUST include `args_must_include` (e.g., `--input`) — this asserts the agent invoked the script, not just narrated.
- For `numeric_match`, separately verify that the expected output number appears in some `subprocess.stdout` (not just in cmd or stdin). The Pitfall #2 detector (above) already accepts cmd/stdin/stdout — for the **route-match** metric specifically, require stdout match. Two-tier check.

**Warning signs:**
- A prompt's `numeric_match` flips green even though the transcript shows zero subprocess calls. The route-match check catches this if expected_scripts is properly populated.

### Pitfall 4: Replay transcript drift after a SKILL.md edit

**What goes wrong:** Phase 13 (hypothetical) edits SKILL.md to change a routing keyword. CI runs replay-mode evals against stale transcripts that still have the old routing — replay says "all green" but live would say "regression."

**Why it happens:** Replay transcripts are point-in-time snapshots. If the SKILL.md or `scripts/*.py` changes after the recording, the replay no longer reflects current behavior.

**How to avoid:**
- Record a SHA-256 hash of `SKILL.md` + `scripts/*.py` into each transcript; replay refuses to run when hashes mismatch (with a `--force` override for human discretion).
- Nightly live-mode eval is the safety net — any divergence between live and last-recorded replay flags the staleness.
- Document a "re-record transcripts" workflow: `python evals/runner.py --mode live --record --all`.

**Warning signs:**
- CI green for many pushes; nightly live-mode goes red and stays red. The drift accumulated.

### Pitfall 5: 95% threshold is meaningless with too few prompts

**What goes wrong:** v1 ships with 7 prompts (one per mode). One failure = 14.3% loss = 85.7% rate < 95% threshold. The threshold is unattainable in practice; team disables the gate.

**Why it happens:** SC-4 is a percentage; small denominators amplify noise.

**How to avoid:**
- Ship at least 21 prompts in v1 (3 per mode: a happy path + at least one edge case + at least one stress) — Q(h) below pins this with rationale.
- A 95% threshold over 21 prompts allows 1 failure (4.76% < 5%); over 28 prompts allows 1 failure (3.57% < 5%). 21 is the floor.

**Warning signs:**
- The threshold is hit from above on the very first run with no margin (suggests we tuned the prompts to pass, not to be representative).

### Pitfall 6: Transcript files leak the FRED_API_KEY

**What goes wrong:** A live-mode recording captures `fred_cli.py`'s subprocess args; if we ever log the actual URL with the key, the transcript file gets the key. Committing it leaks.

**Why it happens:** Easy oversight in subprocess tracing.

**How to avoid:**
- `fred_cli.py` redacts `api_key=***` in any `source_url` it emits to stdout (already pinned in cache schema above).
- The runner's transcript writer has a final `_redact()` pass over all string fields, replacing `api_key=[A-Za-z0-9]+` with `api_key=***`.
- A pre-commit hook (Phase 1 D-10 inheritance) greps committed transcripts for `api_key=` patterns followed by anything but `***`.

**Warning signs:**
- A transcript file contains a 32-char alphanumeric run after `api_key=`.

## Code Examples

### Example 1: Minimal `scripts/fred_cli.py`

```python
"""scripts/fred_cli.py — print latest FRED observation for a series, with 7d TTL cache.

Bundled with .claude/skills/mortgage-ops/scripts/ per Phase 10 relocation rules
(this script ships at scripts/ in Phase 12 and is moved by Phase 10's plan-set
into .claude/skills/mortgage-ops/scripts/ in the same plan that relocates
amortize.py / affordability.py / etc.).

Used by SKILL.md inline injection:
    !`python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE30US`

Always exits 0; failures emit {"value": null, "error": "...", ...}.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CACHE_TTL = timedelta(days=7)
DEFAULT_CACHE_PATH = Path(__file__).parent.parent / "evals" / "cache" / "fred-cache.json"

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _read_cache(cache_path: Path) -> dict[str, Any]:
    if not cache_path.exists():
        return {"schema_version": 1, "entries": {}}
    return json.loads(cache_path.read_text())

def _write_cache(cache_path: Path, cache: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2))

def _is_fresh(entry: dict[str, Any]) -> bool:
    fetched_at = datetime.fromisoformat(entry["fetched_at"].replace("Z", "+00:00"))
    return (_now() - fetched_at) < CACHE_TTL

def _fetch_from_fred(series_id: str, api_key: str) -> dict[str, Any]:
    """Returns {value: str, observation_date: str, fred_realtime_start: str, fred_realtime_end: str}.
    Raises urllib.error.URLError on network failure."""
    qs = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    })
    url = f"https://api.stlouisfed.org/fred/series/observations?{qs}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    obs = data["observations"][0]
    return {
        "value": obs["value"],  # FRED returns string already
        "observation_date": obs["date"],
        "fred_realtime_start": obs["realtime_start"],
        "fred_realtime_end": obs["realtime_end"],
    }

def get(series_id: str, *, cache_path: Path = DEFAULT_CACHE_PATH) -> dict[str, Any]:
    """Public API: returns the latest observation, hitting cache when fresh."""
    cache = _read_cache(cache_path)
    entry = cache["entries"].get(series_id)
    if entry and _is_fresh(entry):
        return entry

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        return {
            "value": None,
            "error": "FRED_API_KEY not set",
            "instruction": "Ask the user for the current rate; live FRED data unavailable.",
        }

    try:
        fetched = _fetch_from_fred(series_id, api_key)
    except Exception as exc:  # noqa: BLE001 — broad except is intentional; we never crash the skill
        return {
            "value": None,
            "error": f"FRED fetch failed: {exc!r}",
            "instruction": "Ask the user for the current rate; live FRED data unavailable.",
        }

    new_entry = {
        **fetched,
        "fetched_at": _now().isoformat().replace("+00:00", "Z"),
        "source_url": f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key=***&file_type=json&sort_order=desc&limit=1",
    }
    cache["entries"][series_id] = new_entry
    _write_cache(cache_path, cache)
    return new_entry

def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"value": None, "error": "usage: fred_cli.py <SERIES_ID>"}))
        return 0
    series_id = sys.argv[1]
    print(json.dumps(get(series_id), indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Example 2: `evals/runner.py` skeleton

```python
"""evals/runner.py — drive eval prompts in replay or live mode.

Usage:
    python evals/runner.py evals/prompts/                         # replay all
    python evals/runner.py evals/prompts/evaluate-01.md            # replay one
    python evals/runner.py evals/prompts/ --mode live              # live, no record
    python evals/runner.py evals/prompts/ --mode live --record     # re-record transcripts
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import frontmatter  # python-frontmatter

NUMBER_REGEX = re.compile(r"\$?(\d{1,3}(?:,\d{3})*|\d+)\.\d{1,4}\b")
ROOT = Path(__file__).parent

@dataclass
class FailureReport:
    prompt_id: str
    kind: str           # "route" | "numeric" | "pitfall2"
    detail: str

@dataclass
class HarnessReport:
    n_prompts: int = 0
    route_match_count: int = 0
    numeric_match_count: int = 0
    pitfall2_clean_count: int = 0
    failures: list[FailureReport] = field(default_factory=list)

    @property
    def route_match_rate(self) -> float:
        return self.route_match_count / self.n_prompts if self.n_prompts else 0.0
    @property
    def numeric_match_rate(self) -> float:
        return self.numeric_match_count / self.n_prompts if self.n_prompts else 0.0

def normalize_num(s: str) -> Decimal:
    return Decimal(s.replace("$", "").replace(",", ""))

def extract_numbers(text: str) -> set[Decimal]:
    return {normalize_num(m.group(0)) for m in NUMBER_REGEX.finditer(text)}

def grade(transcript: list[dict[str, Any]], expected: dict[str, Any]) -> tuple[bool, bool, bool, list[FailureReport]]:
    """Returns (route_ok, numeric_ok, pitfall2_ok, failures)."""
    failures: list[FailureReport] = []
    response = next((m["content"] for m in transcript if m["type"] == "model_response"), "")
    sub_calls = [m for m in transcript if m["type"] == "subprocess"]

    # ---- route_match ----
    route_ok = True
    for kw in expected.get("expected_route_keywords", []):
        if kw not in response and not any(kw in " ".join(c["cmd"]) for c in sub_calls):
            route_ok = False
            failures.append(FailureReport(expected["id"], "route", f"missing keyword '{kw}'"))
    for spec in expected.get("expected_scripts", []):
        matching = [c for c in sub_calls if any(spec["script"] in arg for arg in c["cmd"])]
        if not matching:
            route_ok = False
            failures.append(FailureReport(expected["id"], "route", f"script {spec['script']} never invoked"))
            continue
        for inc in spec.get("args_must_include", []):
            if not any(inc in c["cmd"] for c in matching):
                route_ok = False
                failures.append(FailureReport(expected["id"], "route", f"{spec['script']} missing flag {inc}"))
        for fname, regex in spec.get("args_must_match_regex", {}).items():
            patt = re.compile(regex)
            if not any(patt.search(json.dumps({"cmd": c["cmd"], "stdin": c.get("stdin", "")}))
                       for c in matching):
                route_ok = False
                failures.append(FailureReport(expected["id"], "route",
                                              f"{spec['script']} arg {fname} did not match {regex}"))

    # ---- numeric_match ----
    numeric_ok = True
    response_nums = extract_numbers(response)
    for exp_num in expected.get("expected_numbers", []):
        target = Decimal(exp_num["value"])
        tol = Decimal(exp_num["tolerance"])
        if not any(abs(n - target) <= tol for n in response_nums):
            numeric_ok = False
            failures.append(FailureReport(expected["id"], "numeric",
                                          f"expected {exp_num['label']}={target} (±{tol}) not in response"))

    # ---- Pitfall #2 detector ----
    script_nums: set[Decimal] = set()
    for c in sub_calls:
        script_nums.update(extract_numbers(c.get("stdout", "")))
        script_nums.update(extract_numbers(" ".join(c.get("cmd", []))))
        script_nums.update(extract_numbers(c.get("stdin", "")))
    hallucinated = [n for n in response_nums
                    if not any(abs(n - s) <= Decimal("0.005") for s in script_nums)]
    pitfall2_ok = (hallucinated == [])
    if not pitfall2_ok:
        failures.append(FailureReport(expected["id"], "pitfall2",
                                      f"unsourced numbers: {hallucinated}"))

    # ---- estimated APR literal (Phase 7 carryover) ----
    if expected.get("expected_apr_literal", False):
        if "estimated APR" not in response:
            numeric_ok = False  # treat as a numeric/correctness failure
            failures.append(FailureReport(expected["id"], "numeric",
                                          "missing required literal 'estimated APR'"))

    return route_ok, numeric_ok, pitfall2_ok, failures

def run_replay(prompt_path: Path) -> tuple[bool, bool, bool, list[FailureReport]]:
    pid = prompt_path.stem
    expected = json.loads((ROOT / "expected" / f"{pid}.json").read_text())
    transcript_path = ROOT / "transcripts" / f"{pid}.jsonl"
    transcript = [json.loads(line) for line in transcript_path.read_text().splitlines() if line.strip()]
    return grade(transcript, expected)

def run_live(prompt_path: Path, record: bool = False) -> tuple[bool, bool, bool, list[FailureReport]]:
    pid = prompt_path.stem
    expected = json.loads((ROOT / "expected" / f"{pid}.json").read_text())
    fm = frontmatter.load(prompt_path)
    # NOTE: this is the planner's call — recommended `claude -p` driver:
    #   result = subprocess.run(["claude", "-p", fm.content, "--output-format", "json"],
    #                           capture_output=True, text=True, timeout=300)
    # The captured JSON includes the model response and tool-call traces.
    # Convert to our transcript shape, then grade.
    raise NotImplementedError("Live mode driver — planner picks SDK vs claude -p; see RESEARCH §Pattern 5")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompts", nargs="+", help="Prompt files or a directory")
    parser.add_argument("--mode", choices=["replay", "live"], default="replay")
    parser.add_argument("--record", action="store_true", help="Live mode only: save new transcript")
    args = parser.parse_args()

    prompt_paths: list[Path] = []
    for p in args.prompts:
        path = Path(p)
        if path.is_dir():
            prompt_paths.extend(sorted(path.glob("*.md")))
        else:
            prompt_paths.append(path)

    report = HarnessReport(n_prompts=len(prompt_paths))
    runner = run_live if args.mode == "live" else run_replay

    for pp in prompt_paths:
        route_ok, num_ok, p2_ok, fails = runner(pp) if args.mode == "replay" else runner(pp, record=args.record)
        if route_ok:    report.route_match_count += 1
        if num_ok:      report.numeric_match_count += 1
        if p2_ok:       report.pitfall2_clean_count += 1
        report.failures.extend(fails)

    print(json.dumps({
        "n_prompts": report.n_prompts,
        "route_match_rate": round(report.route_match_rate, 4),
        "numeric_match_rate": round(report.numeric_match_rate, 4),
        "pitfall2_clean_rate": round(report.pitfall2_clean_count / report.n_prompts, 4),
        "failures": [f.__dict__ for f in report.failures],
    }, indent=2))

    # SC-4 gate
    return 0 if report.route_match_rate >= 0.95 and report.numeric_match_rate >= 0.95 else 1

if __name__ == "__main__":
    sys.exit(main())
```

### Example 3: `.mcp.json` for the FRED MCP server

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

Notes:
- The `${FRED_API_KEY}` substitution syntax is supported by Claude Code's MCP config loader [VERIFIED: Claude Code MCP docs] — keeps the secret out of the committed file.
- This file is `.gitignored` if it ends up containing absolute local paths; otherwise, commit it with the path templated and document setup in the README.
- **Alternative install via Smithery:** `npx -y @smithery/cli install @stefanoamorelli/fred-mcp-server --client claude` writes a default config block automatically [CITED: stefanoamorelli/fred-mcp-server README].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.claude/commands/foo.md` for custom shell commands | Skills (`.claude/skills/foo/SKILL.md`) — commands merged into skills | 2026 (Anthropic skills release) | Phase 10 owns SKILL.md scaffold; Phase 12 only fills FRED lines into the existing skill |
| Hand-rolled "MCP client" calls inside scripts | MCP server registered in `.mcp.json`; agent invokes via tool API directly | MCP spec stabilization (2025) | Don't try to write a Python MCP client just to call the FRED MCP server — register it and let Claude use it natively |
| Skill evals as ad-hoc smoke tests | `evals/evals.json` schema (Anthropic skill-creator) with `id` + `prompt` + `expected_output` + `assertions` | Late 2025 / early 2026 (skill-creator eval mode shipped) | Our `evals/prompts/*.md` + `evals/expected/*.json` is structurally similar but split-file; planner may convert to single `evals.json` for closer alignment with anthropics/skills if desired (cost: less readable; benefit: reuse Anthropic's grader subagent if it ever ships as a public tool) |

**Deprecated/outdated:**
- "Cache forever, refresh manually" approach for FRED — Pitfall 9 in research/PITFALLS.md already pins the 7-day TTL as the correct interval (FRED publishes Thursdays). Phase 12 enforces this in code (SC-2).
- Bare `MORTGAGE30US` references without `MORTGAGE15US` — LIVE-04 makes 15yr context optional but recommended; planner should ship both for symmetry.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `claude -p "<prompt>" --output-format json` exists and captures tool-call transcripts in a parseable form | Patterns §5 (live mode), Don't-Hand-Roll | If absent, the live-mode driver must use the Anthropic SDK directly with manual SKILL.md content concatenation — adds ~100 lines and reduces fidelity. Planner verifies via `claude --help` before committing. |
| A2 | `python-frontmatter >=1.1` is current and pip-installable | Standard Stack §Supporting | If stale, planner picks an alternative or rolls a 5-line YAML+text splitter with documented edge cases. |
| A3 | `anthropic` Python SDK >=0.40 is current | Standard Stack §Supporting | If stale, planner pins to whatever `pip index versions anthropic` reports. Optional dep group only — does not block CI. |
| A4 | FRED returns `value` as a JSON string (not a float) for MORTGAGE30US | Patterns §1 (cache schema), Example 1 | If FRED switches to float values, our string-passthrough breaks Decimal discipline. Mitigation: `fred_cli.py` defensively coerces with `str(obs["value"])`. Verified empirically with one curl call before locking. |
| A5 | The `${CLAUDE_SKILL_DIR}` substitution resolves correctly inside `!`...`` injections (not just inside the markdown body) | Patterns §1, Example 1 | If substitution doesn't apply to shell commands, the `!`python ${CLAUDE_SKILL_DIR}/...`` form fails. Fallback: use a relative path `./scripts/fred_cli.py` which works because Claude Code launches the shell with the project root as CWD — verified in the skill spec docs section "Available string substitutions" which states `${CLAUDE_SKILL_DIR}` is "Use this in bash injection commands to reference scripts or files bundled with the skill, regardless of the current working directory" — **this is the explicit use case**. So the assumption is well-founded but worth a one-shot smoke test before locking. |
| A6 | The "v1 prompt set" of 21 prompts (3 per mode × 7 modes) is sufficient to make the 95% threshold meaningful | Q(h) below | If insufficient, threshold flaps; bump to 28 (4 per mode) and re-baseline. Easier to add than to remove. |
| A7 | Replay-mode transcripts can be committed to git without leaking secrets, given the redaction pass | Pitfall 6 | If redaction misses a key format we haven't seen, a key leaks. Mitigation: pre-commit hook greps for `api_key=[A-Za-z0-9]{16,}` (FRED keys are 32-char alphanumeric) and refuses commit. |
| A8 | The runner can shell out to `claude -p` from inside CI without auth issues | Patterns §5 (live mode) | If the CI runner has no Claude credential, live-mode evals must be skipped in CI. Recommend nightly local-cron OR a single GitHub-Actions secret-scoped workflow. CI default is replay-only, so this is fine. |

**If any assumption changes, the planner should escalate via `/gsd-discuss-phase 12`.**

## Open Questions

These are genuine ambiguities the planner / discuss-phase needs to resolve before plans are written:

1. **Q(a) — fred-cli vs python script:** SC-1 says `` !`fred-cli get MORTGAGE30US --latest` ``. The upstream FRED MCP server has no `fred-cli` binary. We can either (i) ship `scripts/fred_cli.py` and rewrite the SC-1 line in SKILL.md to invoke it (recommended), or (ii) write a thin shell shim named `fred-cli` that wraps `python scripts/fred_cli.py` (lets SKILL.md text match SC-1 verbatim but adds a fragile shim). **Recommendation: (i).** Update the success-criterion language during discuss-phase to reflect reality.

2. **Q(b) — MCP server registration scope:** Do we register the FRED MCP server in `.mcp.json` (project-shared, committed) or in `~/.claude.json` (personal, per-developer)? The repo is single-user (Pachulski household) so project-scoped is acceptable. **Recommendation: project-scoped, with absolute path templated and `${FRED_API_KEY}` env var — document setup in README.**

3. **Q(c) — Eval prompt count:** Q(h) recommends 21 (3 × 7 modes). Does the planner accept this floor, or does the user want a different cadence? **Recommendation: 21 minimum, target 28 (4 per mode) by phase end — gives 1-failure margin even at 28.**

4. **Q(d) — Transcript storage:** Commit `evals/transcripts/*.jsonl` to git for CI determinism (recommended) OR generate them in a CI step from a frozen seed (avoids large diffs but requires deterministic LLM, which doesn't exist). **Recommendation: commit, with size monitoring (<10 KB per transcript expected); use git-lfs only if a single transcript exceeds 100 KB.**

5. **Q(e) — Live-mode CI cost:** A single live-mode pass over 21 prompts at Sonnet pricing is ≈ $0.50–$2.00 [ASSUMED — depends on prompt length and tool-use loop length]. Nightly = ~$15–$60/month. **Recommendation: nightly via GitHub Actions on a scheduled workflow with the user's Anthropic API key as a secret; alert on threshold breach. Cap with a per-run token budget.**

6. **Q(f) — How does the runner verify SC-1 specifically (rate appears in context)?** Two options: (i) a synthetic eval prompt that asks "what is the current 30yr rate?" and asserts the response includes a number from `fred-cache.json`; (ii) a structural check that loads SKILL.md, runs `!`fred_cli ...`` injection in isolation, and verifies the resulting context contains the rate. **Recommendation: ship both — option (i) as a regular eval prompt (`live-rate-injection-01.md`), option (ii) as a unit test in `tests/test_fred_cli.py`.**

7. **Q(g) — Score Phase 7's "estimated APR" literal expectation:** Where does the literal-text rule live — in `expected/` JSON (per-prompt opt-in, recommended) or as a global runner rule that scans every response for "APR" without "estimated"? **Recommendation: per-prompt opt-in via `expected_apr_literal: true`, plus a soft global warning when the literal "APR" appears alone.**

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python>=3.12` | scripts/, tests/, evals/ | ✓ (project standard) | 3.12+ per pyproject.toml | — |
| `pydantic>=2.13.3` | request/response models | ✓ | 2.13.3+ already pinned | — |
| `freezegun>=1.5` | SC-2 cache TTL test | ✗ (not yet installed) | — | NEW dep — planner adds via `uv add --dev freezegun` |
| `python-frontmatter>=1.1` | parse evals/prompts/*.md frontmatter | ✗ | — | NEW dep — `uv add --dev python-frontmatter` OR roll a 5-line splitter (not recommended) |
| `anthropic` Python SDK | live-mode eval driver (optional dep group) | ✗ | — | Optional dep `evals-live`. CI does not need it. |
| `node` (for FRED MCP server) | `.mcp.json` registers FRED MCP server | **[ASSUMED ✓]** — Phase 9 plans to use Node for orchestration; should already be present | — | Skip MCP registration; the agent loses the ad-hoc FRED query path but SKILL.md `!`fred_cli`` injection still works. |
| `FRED_API_KEY` env var | `scripts/fred_cli.py` HTTP fetch | ✗ (user-specific secret) | — | `fred_cli.py` returns `{"value": null, "error": "FRED_API_KEY not set"}` — graceful degradation, agent asks user for the rate. |
| `claude` CLI in non-interactive `-p` mode | `evals/runner.py --mode live` | **[ASSUMED ✓]** — should be present in any Claude Code dev environment | — | Fall back to Anthropic SDK direct invocation (more code, less fidelity to actual user pipeline) |

**Missing dependencies with no fallback:**
- None blocking. `FRED_API_KEY` blocks live-rate functionality but the skill degrades gracefully (SC-1 eval tolerates the null-rate path via Pitfall #1 mitigation).

**Missing dependencies with fallback:**
- `freezegun` and `python-frontmatter` — install via `uv add --dev`; planner includes in Wave-0 scaffolding plan.
- `anthropic` SDK — only needed for live mode; install in optional dep group.
- `claude -p` mode availability — planner verifies in Wave 0 via `claude --help | grep -- '-p'`; if missing, falls back to SDK driver.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ (per pyproject.toml `minversion = "9.0"`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_fred_cli.py tests/test_evals_runner.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-01 | FRED MCP integration via stefanoamorelli/fred-mcp-server | smoke | `uv run pytest tests/test_fred_cli.py::test_mcp_config_registered -x` | ❌ Wave 0 |
| LIVE-02 | SKILL.md uses inline `!`...`` shell injection for current rate | structural | `uv run pytest tests/test_skill_md.py::test_fred_injection_lines_present -x` | ❌ Wave 0 |
| LIVE-03 | Cache FRED responses 7 days max; 8-day-old triggers refetch | unit (freezegun) | `uv run pytest tests/test_fred_cli.py::test_eight_day_old_cache_refetches -x` | ❌ Wave 0 |
| LIVE-04 | Optional MORTGAGE15US series available | smoke | `uv run pytest tests/test_fred_cli.py::test_mortgage15us_supported -x` | ❌ Wave 0 |
| EVAL-01 | `evals/prompts/` populated with ≥1 prompt per mode (target ≥21 total) | structural | `uv run pytest tests/test_evals_runner.py::test_prompt_set_coverage -x` | ❌ Wave 0 |
| EVAL-02 | `evals/expected/` populated with matching expected JSON for every prompt | structural | `uv run pytest tests/test_evals_runner.py::test_expected_oracle_coverage -x` | ❌ Wave 0 |
| EVAL-03 | `evals/runner.py evals/prompts/` runs and returns route + numeric match | integration (replay) | `uv run python evals/runner.py evals/prompts/ --mode replay` (gate exit code 0) | ❌ Wave 0 |
| EVAL-04 | Pitfall #2 detector: every reported number traces to a scripts/ invocation | unit | `uv run pytest tests/test_evals_runner.py::test_pitfall2_detector -x` | ❌ Wave 0 |
| SC-1 | Skill in fresh session injects latest weekly rate (eval-asserted) | live-mode eval | `uv run python evals/runner.py evals/prompts/live-rate-injection-01.md --mode live` | ❌ Wave 0 |
| SC-2 | 8-day-old cache triggers refetch (mocked time) | unit (freezegun) | same as LIVE-03 | ❌ Wave 0 |
| SC-3 | runner asserts every reported number traces to a `scripts/` invocation | integration (replay) | `uv run pytest tests/test_evals_runner.py::test_runner_blocks_on_pitfall2 -x` | ❌ Wave 0 |
| SC-4 | route_match_rate ≥ 0.95 AND numeric_match_rate ≥ 0.95 on v1 prompt set | integration (replay) | `uv run python evals/runner.py evals/prompts/ --mode replay` (gate exit code 0) | ❌ Wave 0 |
| SC-5 | `evals/expected/` covers ≥1 prompt per mode (7 modes minimum) | structural | `uv run pytest tests/test_evals_runner.py::test_one_per_mode -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_fred_cli.py tests/test_evals_runner.py -x` (fast subset; runs in <5s after Wave 0)
- **Per wave merge:** `uv run pytest && uv run python evals/runner.py evals/prompts/ --mode replay`
- **Phase gate:** Full suite green AND replay-mode runner exits 0 AND nightly live-mode (the most recent run) reports route_match_rate ≥ 0.95 AND numeric_match_rate ≥ 0.95.

### Wave 0 Gaps
- [ ] `tests/test_fred_cli.py` — covers LIVE-01..04 + SC-1/SC-2 (will need freezegun fixture in conftest.py)
- [ ] `tests/test_evals_runner.py` — covers EVAL-01..04 + SC-3/SC-4/SC-5
- [ ] `tests/test_skill_md.py` — structural check that SKILL.md contains the FRED injection lines (LIVE-02; lightweight — read SKILL.md, grep for `!`python.*fred_cli.py.*MORTGAGE30US`)
- [ ] `evals/cache/.gitkeep` — preserve directory; `.gitignore` excludes `evals/cache/fred-cache.json`
- [ ] `evals/transcripts/.gitkeep` — preserve directory; transcripts ARE committed
- [ ] `evals/prompts/.gitkeep` — placeholder until first prompt
- [ ] `evals/expected/.gitkeep` — placeholder until first oracle
- [ ] `tests/conftest.py` extension — add `fred_cache_factory` fixture parallel to existing `amortize_fixture`/`affordability_fixture` patterns
- [ ] Framework install: `uv add --dev freezegun python-frontmatter`
- [ ] Optional install: `uv add --optional evals-live anthropic` (only for live-mode users)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FRED_API_KEY: env var only, never committed, redacted in cache and transcripts (`api_key=***`) |
| V3 Session Management | no | No sessions — single-shot HTTP GET per fetch |
| V4 Access Control | no | Single-user personal tool |
| V5 Input Validation | yes | Pydantic strict+frozen+forbid for the cache JSON envelope and the eval expected JSON envelope; `series_id` arg validated against an allowlist (`MORTGAGE30US`, `MORTGAGE15US`) before being interpolated into the URL |
| V6 Cryptography | no | HTTPS via stdlib urllib (uses system trust store); no hand-rolled crypto |
| V7 Error Handling & Logging | yes | `fred_cli.py` never crashes; emits structured `{error: ...}` envelope; error messages do NOT include the API key |
| V14 Configuration | yes | `.mcp.json` uses `${FRED_API_KEY}` substitution; never commit raw key. Pre-commit hook greps for accidental commits. |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage in cache file | Information Disclosure | Redact `api_key` to `***` in `source_url`; the actual key only lives in env |
| API key leakage in committed transcript | Information Disclosure | Runner's `_redact()` pass + pre-commit hook grepping for `api_key=[A-Za-z0-9]{16,}` |
| URL parameter injection via `series_id` | Tampering | Allowlist `series_id` values (`MORTGAGE30US`, `MORTGAGE15US`) before interpolation; reject anything else with `{"error": "unsupported series"}` |
| Cache poisoning by writing arbitrary JSON | Tampering | Pydantic-validate the cache file on read with the schema documented above; on schema mismatch, treat the cache as missing and refetch |
| Skill-shell-injection abuse via FRED response | Tampering | The FRED API response is JSON; we never `eval` or shell-execute its content. The cache is JSON-serialized via `json.dumps`, not string-concatenated. |
| Slowloris-style hang of the SKILL.md injection | Denial of Service | `urllib.request.urlopen(url, timeout=10)` — 10-second timeout caps the worst-case skill-load delay |

## Project Constraints (from CLAUDE.md)

These directives from `/Users/cujo253/Documents/mortgage-ops/CLAUDE.md` and `/Users/cujo253/CLAUDE.md` apply verbatim:

- **No co-author / AI attribution in commits.** Phase 12 commits look identical in style to Phase 1–5 commits.
- **Decimal for money, never float.** Cache `value` field is a string; runner Decimal-parses both expected values and tolerances; numeric extraction returns `Decimal`. Never convert through float.
- **Skill portability:** `scripts/fred_cli.py` MUST end up bundled INSIDE `.claude/skills/mortgage-ops/scripts/`. Phase 12 ships at project-root `scripts/` per current convention; Phase 10's relocation plan (or a Phase 12 wave that moves it) physically relocates.
- **SKILL.md ≤ 500 lines, ≤ 5k tokens.** Phase 12 adds at most ~10 lines (two `!`...`` injection lines + 5 lines of prose). Token impact ~50 tokens. Well within budget.
- **References load on-demand only.** The FRED-rate context is content, not a reference; injection at top-of-skill is correct.
- **Reference data discipline (source: + effective: dates).** The `fred-cache.json` carries `source_url` + `observation_date` + `fetched_at`, mirroring the YAML reference-data discipline at the cache layer.
- **Run `--help` first; do not read source.** `fred_cli.py` MUST support `--help` → exits 0 with usage, no network call.
- **Test discipline:** Hand-calculated golden values; exact Decimal equality. The freezegun TTL test uses exact-second boundaries (6d 23h 59m vs 7d 0h 0s vs 8d).
- **mypy --strict + ruff clean.** All Phase 12 code passes both.
- **GSD workflow enforcement:** Phase 12 only edited via GSD commands (planner, executor) — research is the first gated artifact.

## Sources

### Primary (HIGH confidence)
- [Anthropic Skills documentation, "Inject dynamic context"](https://code.claude.com/docs/en/skills) — verbatim spec for `!`...`` shell injection, `${CLAUDE_SKILL_DIR}` substitution, frontmatter fields, `disableSkillShellExecution` policy
- [stefanoamorelli/fred-mcp-server README](https://github.com/stefanoamorelli/fred-mcp-server) — MCP server install (npm/Smithery/Docker), env vars (FRED_API_KEY required), MCP tools exposed (`fred_browse`, `fred_search`, `fred_get_series`), JSON config snippet, AGPL-3.0 license, v1.0.2 (Jan 2025)
- [FRED API series_observations docs](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) — endpoint, `series_id` + `api_key` + `file_type=json` + `sort_order=desc` + `limit=1`
- [FRED MORTGAGE30US series page](https://fred.stlouisfed.org/series/MORTGAGE30US) — Freddie PMMS, Weekly (Ending Thursday) frequency, source = Freddie Mac Primary Mortgage Market Survey
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) — `.mcp.json` project-scoped registration, `${ENV_VAR}` substitution, stdio transport
- Project files (already on disk): `CLAUDE.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/research/PITFALLS.md` (Pitfall #2 verbatim source)

### Secondary (MEDIUM confidence — single-source web verified once)
- [freezegun README](https://github.com/spulec/freezegun) — datetime/time mock library, decorator + context manager forms
- [Better Stack: time-machine vs freezegun](https://betterstack.com/community/guides/testing/time-machine-vs-freezegun/) — comparative analysis confirming freezegun's broader coverage of stdlib time functions
- [anthropics/skills skill-creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) — `evals/evals.json` schema, parallel subagent execution pattern, grading.json field constraints (`text`, `passed`, `evidence`)
- [FRED API rate limits — community docs](https://fred.stlouisfed.org/docs/api/terms_of_use.html) — 120 req/min, 429 on overage, API key required (registration free)

### Tertiary (LOW confidence — needs verification by planner)
- [agentskills.io specification](https://agentskills.io/specification) — third-party spec mirror; useful for cross-checking but Anthropic docs are canonical
- "v1.0.2 latest" claim for fred-mcp-server — January 2025 per Zenodo DOI; planner should re-check `npm view @stefanoamorelli/fred-mcp-server version` before committing the version
- "PMMS releases Thursday at noon ET, Wednesday on holiday weeks" — citation chain via mortgagenewsdaily.com / nationalmortgageprofessional.com; should be re-verified during nightly-cadence design (Q(j))

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pydantic/freezegun/urllib are project-aligned and well-documented; `python-frontmatter` is mainstream
- Architecture: HIGH for live-rate path (every component has a verified spec citation); MEDIUM for live-LLM eval driver (depends on Assumption A1 — `claude -p` JSON output capture)
- Pitfalls: HIGH — direct extraction from project's existing `research/PITFALLS.md` (Pitfall #2 verbatim) plus FRED-MCP-server-specific pitfalls newly identified during this research

**Research date:** 2026-05-02
**Valid until:** 2026-06-02 (FRED API and skills spec are stable on monthly horizons; re-validate `claude -p` and `claude` CLI flags before live-mode landed)
