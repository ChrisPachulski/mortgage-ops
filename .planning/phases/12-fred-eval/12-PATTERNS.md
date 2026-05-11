# Phase 12: fred-eval - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 17 (new + modified)
**Analogs found:** 15 / 17 (88%)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.claude/skills/mortgage-ops/scripts/fred_cli.py` | controller (CLI) | request-response (HTTP fetch + cache I/O) | `.claude/skills/mortgage-ops/scripts/stress_test.py` + `.claude/skills/mortgage-ops/scripts/_cli_helpers.py` + `.claude/skills/mortgage-ops/scripts/amortize.py` | role-match (CLI shape; new data-flow: HTTP) |
| `lib/fred_cache.py` | service (cache module) | file-I/O + TTL staleness | `lib/rules/_loader.py` (`_check_staleness`) + `orchestration/lockfile.mjs` (`withLock`) | partial (composite: staleness + lock) |
| `data/cache/fred_*.json` | data artifact | persisted JSON | `data/.lock`, `data/reference/*.yml` (gitignore + Data Layer pattern) | role-match |
| `.claude/skills/mortgage-ops/SKILL.md` (modify) | config (skill spec) | request-response (loaded by Claude) | `.claude/skills/mortgage-ops/SKILL.md` (existing Phase 10 — modify only the `## Live Mortgage Rates` section + routing block) | exact (self-analog; in-place section insert) |
| `.claude/skills/mortgage-ops/references/fred-context.md` | reference doc (progressive disclosure) | request-response (on-demand load) | `.claude/skills/mortgage-ops/references/apr-reg-z.md` + `references/arm-mechanics.md` | exact |
| `evals/runner.py` | controller (orchestrator) | batch / transform | none in repo (greenfield); closest tooling analog `tests/test_subagents.py` (transcript-replay + count_tokens loop) | partial (no analog; use RESEARCH.md Patterns 5+7) |
| `evals/metrics.py` | service (scoring) | transform | none in repo (greenfield); closest helper analog `tests/_skill_helpers.py` (count_tokens) | none |
| `evals/prompts/*.md` | data fixture (input) | static fixture | `.claude/agents/*.md` (frontmatter + body shape) | role-match |
| `evals/expected/*.json` | data fixture (oracle) | static fixture | `tests/fixtures/amortize/*.json`, `tests/fixtures/golden_pmt.json` | exact (one-per-file fixture idiom) |
| `tests/test_fred_cli.py` | test (CLI surface) | request-response (subprocess) | `tests/test_amortize.py` (SCRIPT_PATH + subprocess.run + lazy-import gate) | exact |
| `tests/test_fred_cache.py` | test (cache TTL + lock) | event-driven (time mock) | `tests/test_orchestration/` (lockfile parallel-write tests) + `lib/rules/_loader.py` `StaleReferenceWarning` test patterns | role-match |
| `tests/test_evals_runner.py` | test (eval harness) | batch | `tests/test_subagents.py` (transcript-fixture replay + parametrize over agents) | role-match |
| `tests/test_evals_metrics.py` | test (scorer) | transform | `tests/test_cli_helpers.py` (pure-function helpers, parametric coverage) | role-match |
| `tests/fixtures/fred/` | test fixture dir | static fixture | `tests/fixtures/subagent_transcripts/` (synthetic-only-in-CI policy + README + live-capture recipe) | exact |
| `.github/workflows/ci.yml` (modify) | config (CI) | event-driven | existing `.github/workflows/ci.yml` (Pytest step + USER-LAYER guard pattern) | exact (self-analog; add eval step) |

## Pattern Assignments

### `.claude/skills/mortgage-ops/scripts/fred_cli.py` (controller, request-response)

**Analog:** `.claude/skills/mortgage-ops/scripts/stress_test.py` (CLI shape) + `.claude/skills/mortgage-ops/scripts/_cli_helpers.py` (envelope shape) + `.claude/skills/mortgage-ops/scripts/amortize.py` (sys.path-injection idiom + lazy-import + JSON-in/JSON-out boundary)

**Module docstring + lazy-import header** (analog `amortize.py:1-69`):
```python
#!/usr/bin/env python3
"""scripts/fred_cli.py — JSON-out CLI for the latest FRED observation, with 7d TTL cache.

Per LIVE-01..04 + D-12-LIVE01-01:
  - HTTP wrapper (canonical) — calls api.stlouisfed.org/fred/series/observations directly
  - 7-day TTL cache at data/cache/fred_{series_id}.json (refetch-on-stale per SC-2)
  - --help works without importing urllib / json (lazy-import per D-18 inherited)
  - Always exits 0; failures emit {"value": null, "error": "..."} per Pitfall 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
```

**sys.path injection (5-levels-deep relocation; analog `amortize.py:92-103`):**
```python
# Phase 10 relocation (D-01): script lives at
# .claude/skills/mortgage-ops/scripts/fred_cli.py (5 levels deep). Inject BOTH
# the repo root (so `from lib.fred_cache import ...` resolves) AND the skill
# root (so `from scripts._cli_helpers import ...` resolves to the colocated
# helper). parents[4] = repo root; parents[1] = skill root.
_skill_root = str(Path(__file__).resolve().parents[1])
_project_root = str(Path(__file__).resolve().parents[4])
for _p in (_project_root, _skill_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

**argparse pattern** (analog `stress_test.py:51-130`):
```python
parser = argparse.ArgumentParser(
    prog="fred_cli",
    description="Fetch latest FRED observation for a mortgage series; emit JSON to stdout.",
    epilog=("Series: MORTGAGE30US | MORTGAGE15US. Output JSON shape:\n"
            '  {"series_id": str, "value": str, "observation_date": str,\n'
            '   "fetched_at": str, "source_url": str, "error": null}\n'
            "All money/rate fields are JSON STRINGS (D-19 inherited).\n"
            "FRED_API_KEY env var required; falls back to {error: ...} envelope when absent."),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("series_id", choices=["MORTGAGE30US", "MORTGAGE15US"])
parser.add_argument("--latest", action="store_true", help="Return only the latest observation (default).")
args = parser.parse_args()
```

**Always-exit-0 error envelope** (Pitfall 1 — divergence from `amortize.py` exit-2 pattern):
```python
# SKILL.md `!`...`` injection requires exit 0 always; failure mode replaces stdout
# content but Claude routes via the envelope's `error` field per D-12-LIVE02-01.
def _emit_error(msg: str) -> int:
    print(json.dumps({"series_id": args.series_id, "value": None, "error": msg}))
    return 0  # NOT 2 — see SKILL.md prose: error envelope is the recovery contract
```

---

### `lib/fred_cache.py` (service, file-I/O + TTL)

**Analog:** `lib/rules/_loader.py` (`_check_staleness` + `lru_cache` + reference-dir Path constant) — adapt 12-month threshold to 7-day TTL; `orchestration/lockfile.mjs` `withLock` (Python port for cache writes).

**Path constant + TTL constant** (analog `lib/rules/_loader.py:23-24`):
```python
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

CACHE_DIR: Final[Path] = Path(__file__).parent.parent / "data" / "cache"
CACHE_TTL: Final[timedelta] = timedelta(days=7)  # SC-2 7-day TTL per D-12-LIVE02-01
```

**Staleness check pattern** (analog `lib/rules/_loader.py:90-101`):
```python
class StaleCacheWarning(UserWarning):
    """Emitted when a FRED cache entry's fetched_at is more than 7 days old.
    Mirrors lib.rules._loader.StaleReferenceWarning idiom (12-month threshold there;
    7-day threshold here per SC-2 + Phase 12 RESEARCH §Pattern 2).
    """

def _is_fresh(entry: dict[str, Any]) -> bool:
    """SC-2: strict < (7.0d EXACTLY counts as stale — refetch). Documented in
    RESEARCH §Pitfall 2 boundary cases (6d-23h-59m fresh; 7d-0h stale; 8d stale)."""
    fetched_at = datetime.fromisoformat(entry["fetched_at"].replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - fetched_at) < CACHE_TTL
```

**Lock-write pattern for cache file** (analog `orchestration/lockfile.mjs:51-95`):
Python port of `withLock()` for cache-file writes. Mirror the **read-back-and-verify** poor-man's-CAS pattern; reuse `STALE_THRESHOLD_MS = 60_000` semantics.
```python
# Lock file: data/cache/.fred-cache.lock (gitignored, ephemeral)
# Same JSON shape as orchestration/lockfile.mjs:53 — {pid, acquired_at, reason}
# Same 60_000ms stale-recovery threshold; same writeFileSync(flag='w') + read-back-verify
# (NOT O_EXCL — see lockfile.mjs:12 header comment).

LOCK_PATH: Final[Path] = CACHE_DIR / ".fred-cache.lock"
STALE_THRESHOLD_MS: Final[int] = 60_000

def _acquire_lock(timeout_ms: int = 30_000, reason: str = "") -> dict[str, Any]:
    """Python port of orchestration/lockfile.mjs:acquireLock. Read-back-verify CAS."""
    # ... (lifted from lockfile.mjs:51-74)
```

---

### `data/cache/fred_*.json` (data artifact)

**Analog:** `data/.lock` (gitignored ephemeral) + `data/reference/*.yml` (committed Reference Layer).

**`.gitignore` entry** (analog `.gitignore:23-26, 31-32, 39`):
```gitignore
# Phase 12: FRED cache (Data Layer — generated, never committed)
data/cache/fred_*.json
data/cache/.fred-cache.lock
```

**Cache JSON shape** (PINNED by 12-RESEARCH.md §Pattern 2, lines 204-227):
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
    }
  }
}
```
Note: `value` is a **JSON string** per project D-19 money-discipline; `api_key=***` redacted per Pitfall 6.

---

### `.claude/skills/mortgage-ops/SKILL.md` (modify — config)

**Analog:** existing SKILL.md (self-analog). Insert new `## Live Mortgage Rates` section BEFORE `## Math Discipline` (line 54) to preserve "first 200 lines" routing budget (SKLL-02 D-12).

**Verbatim section copy** (PINNED by CONTEXT.md D-12-LIVE02-01):
```markdown
## Live Mortgage Rates

Latest weekly rates (refreshed via `scripts/fred_cli.py` on weekly cron;
cached 7 days max in `data/cache/fred_MORTGAGE30US.json`):

- 30-yr fixed (MORTGAGE30US): see cache file `data/cache/fred_MORTGAGE30US.json`
  field `value`
- 15-yr fixed (MORTGAGE15US): see cache file `data/cache/fred_MORTGAGE15US.json`

Skill loads these via Read tool when borrower asks 'what's the current rate?'
```

**Token budget check** (analog `tests/test_skill.py:121-129`): new section ~80 cl100k tokens added to existing ~3400-token SKILL.md → ~3480, still under 4500 budget. No additional offload to references needed.

**Cache-miss recovery prose** (analog Pitfall 1 mitigation; add adjacent to section):
```markdown
If the cache file is absent or stale (>7 days old), invoke
`python ${CLAUDE_SKILL_DIR}/scripts/fred_cli.py MORTGAGE30US --latest`
yourself to refresh; the script writes the cache and emits the value to stdout.
```

**Forbidden grep** (CONTEXT.md D-12-LIVE02-01): tests MUST NOT grep for `` !` `` shell-injection syntax (uncertain Claude Code support per Open Question 1).

---

### `.claude/skills/mortgage-ops/references/fred-context.md` (reference doc)

**Analog:** `.claude/skills/mortgage-ops/references/apr-reg-z.md:1-19` + `references/arm-mechanics.md:1-11` (Phase 7/5 reference docs).

**Header pattern** (analog `apr-reg-z.md:1-19`):
```markdown
# FRED Context — mortgage-ops Phase 12 Reference

This document records the conventions implemented by `scripts/fred_cli.py`
(Phase 12 FRED HTTP wrapper + 7-day TTL cache) and pairs each convention
with its data source citation. All URLs verified on 2026-05-10.

Cited from:
- `scripts/fred_cli.py` module docstring (D-12-LIVE01-01 HTTP-canonical decision)
- `lib/fred_cache.py` cache schema (mirrors RESEARCH §Pattern 2)
- ROADMAP § Phase 12 SC-1..SC-2 (live-rate injection + 7d TTL)

---

## 1. HTTP API (canonical path per D-12-LIVE01-01)

[FRED endpoint shape, auth, rate limits — verbatim from RESEARCH.md lines 109-110]
```

**Required sections** (per CONTEXT.md D-12-LIVE01-01):
1. HTTP canonical path — endpoint, auth (`FRED_API_KEY` env var), rate limits, JSON response shape
2. MCP server optional secondary path — registration recipe (`.claude/settings.json` MCP entry + auth env var), rationale for HTTP-as-canonical (determinism for evals, no MCP system dependency)
3. Cache schema reference (cross-link to `lib/fred_cache.py`)
4. SKILL.md routing rule (when to read the cache vs invoke the CLI)

**SKILL.md topic→reference table update** (analog `SKILL.md:124-133`): add row `| "what's the current rate", "FRED", "MORTGAGE30US" | references/fred-context.md |`.

---

### `evals/runner.py` (controller, batch)

**Analog:** None directly. Closest tooling: `tests/test_subagents.py:53-56, 296+` (TRANSCRIPT_DIR + transcript-shape replay loop). Use RESEARCH.md §Pattern 5 (lines 370-437) and §Pattern 7 (lines 503-536) for the controller skeleton.

**Module-level Path constants** (analog `tests/test_subagents.py:45-56`):
```python
EVALS_DIR: Path = Path(__file__).resolve().parent
PROMPTS_DIR: Path = EVALS_DIR / "prompts"
EXPECTED_DIR: Path = EVALS_DIR / "expected"
RUNS_DIR: Path = EVALS_DIR / "runs"  # DATA_CONTRACT.md System Layer write target
```

**Three-bucket aggregator** (PINNED by CONTEXT.md D-12-SC4-01):
```python
@dataclass
class HarnessReport:
    n_prompts: int
    route_match_count: int
    numeric_pass_count: int      # D-12-SC4-01: pass | fail | SKIP three buckets
    numeric_fail_count: int
    numeric_skip_count: int      # TBD prompts; filtered out of gate denominator
    failures: list[FailureReport]

    @property
    def numeric_match_rate(self) -> float:
        # D-12-SC4-01: denominator excludes numeric_skip
        denom = self.numeric_pass_count + self.numeric_fail_count
        if denom == 0:
            return 0.0
        return self.numeric_pass_count / denom

# SC-4 gate (post D-12-SC4-01):
#   numeric_match_rate >= 0.95 over (pass + fail), skip excluded
#   Example: 12 anchored pass + 9 skip + 0 fail → 12/(12+0) = 100% >= 95% ✓
#   Example: 11 anchored pass + 1 fail + 9 skip → 11/(11+1) = 91.7% < 95% ✗
```

**Output report MUST show three counts explicitly** per D-12-SC4-01: `numeric_pass=N, numeric_fail=N, numeric_skip=N`.

---

### `evals/metrics.py` (service, transform)

**Analog:** `tests/_skill_helpers.py` (pure-function helper module pattern). Use RESEARCH.md §Pattern 6 (lines 441-501) for the hallucination detector skeleton.

**Three-state numeric scorer** (PINNED by D-12-SC4-01):
```python
from enum import Enum

class NumericScore(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"  # D-12-SC4-01: TBD prompts with numeric_status: skip frontmatter

def score_numeric_match(
    model_response: str,
    expected: dict[str, Any],
    subprocess_calls: list[dict[str, Any]],
) -> NumericScore:
    """Return one of three states. SKIP when expected.numeric_status == 'skip'
    OR expected_numbers == [] AND defer_until_phase is set."""
    if expected.get("numeric_status") == "skip":
        return NumericScore.SKIP
    if not expected.get("expected_numbers"):
        return NumericScore.SKIP
    # ... pass/fail logic (analog: RESEARCH §Pattern 7 lines 530-534)
```

**STDOUT-only hallucination detector** (PINNED by D-12-SC3-01 — TIGHTER than RESEARCH §Pattern 6):
```python
def detect_hallucinations(
    model_response: str,
    subprocess_calls: list[dict[str, Any]],
    tolerance: Decimal = Decimal("0.005"),
) -> list[Decimal]:
    """D-12-SC3-01: TIGHTENED — credit numbers as 'sourced' ONLY if they appear in
    STDOUT of a scripts/*.py invocation. Numbers from cmd args, stdin, or prose
    are NOT credited. Diverges from RESEARCH §Pattern 6 which accepted cmd/stdin.

    Trade-off: false-positive risk if a prompt legitimately echoes a static number
    (e.g., IRS Pub 936 $750,000 cap). Mitigation: expected_numbers entries with
    `provenance: static` are exempt from the stdout requirement.
    """
    response_nums = extract_numbers(model_response)

    script_stdout_nums: set[Decimal] = set()
    for call in subprocess_calls:
        if call["type"] != "subprocess":
            continue
        # D-12-SC3-01: STDOUT ONLY — do NOT union cmd args or stdin (diverges
        # from RESEARCH §Pattern 6 lines 472-481 which unioned all three).
        script_stdout_nums.update(extract_numbers(call.get("stdout", "")))
    # ...
```

**Route-match cross-check** (PINNED by D-12-SC3-01):
```python
# If numeric_output is non-empty AND no script invocation occurred in the trace,
# the prompt fails BOTH numeric_match (Pitfall #2) AND route_match (Pitfall #2b).
def score_route_match(...) -> bool:
    has_numeric_output = bool(extract_numbers(model_response))
    has_script_invocation = any(c["type"] == "subprocess" for c in subprocess_calls)
    if has_numeric_output and not has_script_invocation:
        return False  # Pitfall #2b: parroted number with no script
    # ... rest of route_match logic
```

---

### `evals/prompts/*.md` (data fixture, 22 files)

**Analog:** `.claude/agents/{amortization,refi-npv,stress-test}-agent.md` (frontmatter + markdown body shape). Frontmatter schema from RESEARCH.md §Pattern 3 lines 293-324.

**Frontmatter shape** (PINNED by CONTEXT.md D-12-SC4-01 — `numeric_status: skip` is the new key):
```markdown
---
id: evaluate-01
mode: evaluate
description: Single-loan evaluation for a $400k conforming 30yr at 6.5% — Wikipedia oracle.
expected_route_keywords:
  - evaluate
  - amortize.py
expected_scripts:
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "2528.27"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout   # D-12-SC3-01: default; "static" exempts from stdout-only rule
---

I am buying a house with a $400,000 mortgage at a 6.5% fixed rate for 30 years.
Walk me through the monthly payment and total interest.
```

**TBD-prompt frontmatter** (PINNED by D-12-SC4-01):
```markdown
---
id: refinance-03
mode: refinance
numeric_status: skip
defer_until_phase: 13.0
expected_numbers: []
description: TBD — refinance NPV oracle deferred until Phase 6 ships richer fixtures.
expected_route_keywords:
  - refi
  - refi_npv.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
---

[prompt body]
```

**22-prompt set** (PINNED by D-12-SC1-01): 21 mode-coverage (3 per mode × 7 modes) + 1 `live-rate-injection-01.md`. 13 anchored + 9 TBD-with-skip-pointer.

**`live-rate-injection-01.md`** (PINNED by D-12-SC1-01) — anchored to fixture cache (NOT live FRED):
```markdown
---
id: live-rate-injection-01
mode: evaluate
description: SC-1 closure eval — borrower asks current 30-yr rate; skill reads fixture cache.
expected_route_keywords:
  - data/cache/fred_MORTGAGE30US.json
  - 6.50
expected_scripts: []   # No calc-script invocation expected; Read tool only
expected_numbers:
  - label: current_30yr_rate
    value: "6.50"
    tolerance: "0.01"
    source_script: fixture_cache   # pins to tests/fixtures/fred/MORTGAGE30US-2026-05-10.json
    provenance: static            # D-12-SC3-01 exempt — number sourced from cache, not stdout
---

What's the current 30-year fixed mortgage rate?
```

---

### `evals/expected/*.json` (data fixture oracles)

**Analog:** `tests/fixtures/amortize/*.json` + `tests/fixtures/golden_pmt.json` (one-fixture-per-file shape — `tests/conftest.py:41-54` pattern: `amortize_fixture` loader takes a filename stem).

**Oracle JSON shape** (PINNED by RESEARCH.md §Pattern 4 lines 338-368 + D-12-SC4-01 skip extension):
```json
{
  "schema_version": 1,
  "id": "evaluate-01",
  "mode": "evaluate",
  "numeric_status": "anchored",
  "expected_numbers": [
    {"label": "monthly_pi", "value": "2528.27", "tolerance": "0.005", "source_script": "amortize.py", "provenance": "stdout"}
  ],
  "expected_route_keywords": ["evaluate", "amortize.py"],
  "v1_frozen_at": "2026-05-10"
}
```

**TBD oracle shape** (per D-12-SC4-01):
```json
{
  "schema_version": 1,
  "id": "refinance-03",
  "mode": "refinance",
  "numeric_status": "skip",
  "defer_until_phase": "13.0",
  "expected_numbers": [],
  "expected_route_keywords": ["refi", "refi_npv.py"],
  "v1_frozen_at": "2026-05-10"
}
```

Money/tolerance fields are **JSON strings** per D-19 money discipline (Phase 1 inheritance; same rule as `tests/fixtures/amortize/`).

---

### `tests/test_fred_cli.py` (test, request-response via subprocess)

**Analog:** `tests/test_amortize.py:1-100` (SCRIPT_PATH constant, subprocess.run idiom, lazy-import gate test).

**SCRIPT_PATH constant** (analog `tests/test_amortize.py:51-62`):
```python
SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "fred_cli.py"
)
"""Phase 12 CLI ships in .claude/skills/mortgage-ops/scripts/ directly (no
project-root → skill-folder relocation pass like Phase 3 / 8 had). Per
D-12-LIVE01-01 HTTP-canonical decision."""
```

**Always-exit-0 envelope test** (analog Pitfall 1 — diverges from `tests/test_amortize.py` exit-2 pattern):
```python
def test_fred_cli_missing_api_key_exits_zero_with_error_envelope(monkeypatch) -> None:
    """Pitfall 1: SKILL.md `!`...`` injection requires exit 0 always.
    On missing FRED_API_KEY, stdout MUST be valid JSON with {value: null, error: ...}."""
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    result = subprocess.run([sys.executable, str(SCRIPT_PATH), "MORTGAGE30US"],
                            capture_output=True, text=True)
    assert result.returncode == 0  # NOT 2 — diverges from amortize.py
    envelope = json.loads(result.stdout)
    assert envelope["value"] is None
    assert "FRED_API_KEY" in envelope["error"]
```

---

### `tests/test_fred_cache.py` (test, file-I/O + time mock)

**Analog:** `tests/test_orchestration/` (lockfile tests) + `lib/rules/_loader.py` staleness pattern (look for `pytest.warns(StaleReferenceWarning)`).

**freezegun TTL boundary test** (PINNED by RESEARCH.md §Pattern 2 lines 250-285 + Pitfall 2 boundary cases):
```python
import freezegun

def test_six_d_twenty_three_h_old_cache_is_fresh(tmp_path) -> None:
    """SC-2 + Pitfall 2: 6d-23h-59m → fresh (no refetch)."""
    cache_file = tmp_path / "fred_MORTGAGE30US.json"
    cache_file.write_text(json.dumps({
        "schema_version": 1,
        "entries": {"MORTGAGE30US": {"value": "6.84",
                                     "fetched_at": "2026-04-25T12:00:00Z",
                                     # ...
                                     }}
    }))
    with freezegun.freeze_time("2026-05-02T11:59:59Z"):  # 6d-23h-59m later
        from lib.fred_cache import is_fresh
        cache = json.loads(cache_file.read_text())
        assert is_fresh(cache["entries"]["MORTGAGE30US"]) is True

def test_seven_d_exactly_old_cache_is_stale(tmp_path) -> None:
    """SC-2 + Pitfall 2: 7d-0h-0s EXACTLY → stale (strict < boundary)."""
    # ... freeze_time("2026-05-02T12:00:00Z") → expect is_fresh == False
```

**Lock-write parallel-write test** (analog `orchestration/lockfile.mjs` test pattern in `tests/test_orchestration/`): two concurrent writers must serialize.

---

### `tests/test_evals_runner.py` (test, batch)

**Analog:** `tests/test_subagents.py:53-56, 296-340` (TRANSCRIPT_DIR + parametrize over agents/prompts).

**Parametrize over prompts** (analog `tests/test_subagents.py:255-256` parametrize idiom):
```python
PROMPTS_DIR: Path = Path(__file__).resolve().parents[1] / "evals" / "prompts"
ALL_PROMPT_IDS = [p.stem for p in PROMPTS_DIR.glob("*.md")]

@pytest.mark.parametrize("prompt_id", ALL_PROMPT_IDS, ids=lambda p: p)
def test_each_prompt_has_paired_oracle(prompt_id: str) -> None:
    """Every evals/prompts/{id}.md has a paired evals/expected/{id}.json."""
    expected = Path(__file__).resolve().parents[1] / "evals" / "expected" / f"{prompt_id}.json"
    assert expected.is_file()
```

**Three-bucket gate tests** (PINNED by D-12-SC4-01 — REQUIRED assertions):
```python
def test_gate_passes_with_12_anchored_pass_and_9_skip() -> None:
    """D-12-SC4-01: 12/(12+0) = 100% ≥ 95% — gate PASSES."""
    report = HarnessReport(n_prompts=21, route_match_count=21,
                          numeric_pass_count=12, numeric_fail_count=0,
                          numeric_skip_count=9, failures=[])
    assert report.numeric_match_rate == 1.0
    assert report.numeric_match_rate >= 0.95

def test_gate_fails_with_one_anchored_fail_among_12() -> None:
    """D-12-SC4-01: 11/(11+1) = 91.7% < 95% — gate FAILS."""
    report = HarnessReport(n_prompts=21, route_match_count=21,
                          numeric_pass_count=11, numeric_fail_count=1,
                          numeric_skip_count=9, failures=[])
    assert report.numeric_match_rate < 0.95
```

---

### `tests/test_evals_metrics.py` (test, transform)

**Analog:** `tests/test_cli_helpers.py` (pure-function parametric coverage of `find_json_float_loc` + `make_decimal_type_envelope`).

**STDOUT-only hallucination tests** (PINNED by D-12-SC3-01):
```python
def test_prose_only_number_fails_both_gates() -> None:
    """D-12-SC3-01: a transcript citing $1,264.14 from prose with NO script
    invocation fails BOTH numeric_match AND route_match."""
    transcript = [
        {"type": "user_prompt", "content": "What's the payment?"},
        {"type": "model_response", "content": "Your payment is $1,264.14"},
    ]
    expected = {"expected_numbers": [{"value": "1264.14", "tolerance": "0.005"}]}
    assert score_numeric_match(...) == NumericScore.FAIL
    assert score_route_match(...) is False  # Pitfall #2b: no script invocation

def test_stdout_sourced_number_passes_both_gates() -> None:
    """D-12-SC3-01: number cited AFTER scripts/amortize.py stdout passes."""
    transcript = [
        {"type": "subprocess", "cmd": ["python", "scripts/amortize.py", "--input", "fx.json"],
         "stdout": '{"monthly_pi": "1264.14"}', "returncode": 0},
        {"type": "model_response", "content": "Your payment is $1,264.14"},
    ]
    assert score_numeric_match(...) == NumericScore.PASS
    assert score_route_match(...) is True

def test_cmd_arg_only_number_fails_numeric_match() -> None:
    """D-12-SC3-01: prompt body says $400,000 → flows into --principal=400000;
    if the model echoes 400000.00 with no stdout occurrence, the new tighter
    detector flags it (RESEARCH §Pattern 6 would have accepted it)."""
    # ... assert NumericScore.FAIL with reason='unsourced_number'
```

---

### `tests/fixtures/fred/` (test fixture directory)

**Analog:** `tests/fixtures/subagent_transcripts/README.md` (synthetic-only-in-CI rationale + live-capture recipe + `.NEW` promote workflow).

**Directory structure** (mirror Phase 11):
```
tests/fixtures/fred/
├── README.md                              # synthetic rationale + nightly refresh recipe
├── MORTGAGE30US-2026-05-10.json           # pinned to live-rate-injection-01.md
├── MORTGAGE15US-2026-05-10.json
└── stale_8_day_cache.json                 # SC-2 boundary fixture (8d-old fetched_at)
```

**README pattern** (analog `tests/fixtures/subagent_transcripts/README.md:1-40`):
```markdown
# FRED cache fixtures

This directory holds the synthetic cache fixtures that anchor Phase 12 SC-1
(live-rate-injection eval) and SC-2 (7d TTL boundary tests). Each fixture is
hand-authored to match the canonical cache schema from `lib/fred_cache.py`
and is committed so that CI runs are deterministic, free of FRED API charges,
and reproducible across machines.

## Why synthetic, not live (D-02 inherited from Phase 11)

Live FRED dispatch in CI is non-deterministic (rates change weekly), burns
API quota, and requires FRED_API_KEY in CI secrets. Synthetic fixtures give
us the four properties we need: determinism, zero recurring cost,
airgap-safe, contract-is-shape.

## Live-capture recipe (NOT run in CI)

[FRED_API_KEY=xxx python .claude/skills/mortgage-ops/scripts/fred_cli.py \
  MORTGAGE30US > tests/fixtures/fred/MORTGAGE30US-YYYY-MM-DD.json.NEW
 diff -u tests/fixtures/fred/MORTGAGE30US-<prev>.json{,.NEW}
 mv ...NEW <new-date>.json]
```

---

### `.github/workflows/ci.yml` (modify — config)

**Analog:** existing `.github/workflows/ci.yml:1-62` (single self-contained job; add eval step alongside Pytest).

**New `Eval gate` step** (analog `.github/workflows/ci.yml:38-39` Pytest step):
```yaml
      - name: Eval gate (transcript-replay, deterministic)
        run: |
          uv run python evals/runner.py --mode replay --gate 0.95
          # D-12-SC4-01: gate denominator excludes numeric_skip;
          # passes if numeric_pass / (numeric_pass + numeric_fail) >= 0.95
```

**Live-LLM eval split** (defer per Claude's Discretion in CONTEXT.md): planner decides whether to gate live mode in CI or run nightly via separate workflow `.github/workflows/evals-nightly.yml`.

---

## Shared Patterns

### Citation discipline (`Computed by:`)

**Source:** Phase 11 `.claude/agents/*.md` body — every numeric output cites `Computed by: scripts/<name>.py <args>`.

**Apply to:** All eval prompt expected outputs + `evals/runner.py` transcript-shape assertions + `evals/metrics.py` route_match scoring (the runner parses `Computed by:` lines from transcripts to verify provenance).

```markdown
**Computed by:** `scripts/amortize.py --input /tmp/loan.json`
```

---

### `--help` fast / lazy-import doctrine (D-18)

**Source:** `.claude/skills/mortgage-ops/scripts/amortize.py:105-112` ("Lazy-import per D-18: heavy deps... are NOT loaded on the --help fast path. argparse has already parsed by here").

**Apply to:** `scripts/fred_cli.py` — urllib + pydantic + lib.fred_cache MUST be lazy-imported after argparse parses. Test asserts `--help` completes in <100ms.

```python
def main() -> int:
    parser = argparse.ArgumentParser(...)
    # ... add_argument calls
    args = parser.parse_args()  # SystemExit on --help before any heavy imports

    # Lazy-import: only when actually fetching
    from lib.fred_cache import get_cached_or_fetch
    ...
```

---

### Money discipline — JSON strings everywhere (D-19)

**Source:** `CLAUDE.md §Money discipline` + `.claude/skills/mortgage-ops/scripts/_cli_helpers.py:39-64` (find_json_float_loc pre-validation gate).

**Apply to:** `scripts/fred_cli.py` (cache `value` is JSON string `"6.84"` not float), `evals/expected/*.json` (`value` + `tolerance` are JSON strings), `lib/fred_cache.py` (Decimal coerced via `Decimal(str(...))` per Pydantic strict mode).

```python
# scripts/fred_cli.py output:
print(json.dumps({"series_id": "MORTGAGE30US", "value": "6.84", ...}))
# NOT: {"value": 6.84} — JSON floats violate D-19
```

---

### Lock-write pattern (Phase 9 `withLock`)

**Source:** `orchestration/lockfile.mjs:51-95` — read-back-and-verify CAS; 60s stale-recovery; JSON-content `acquired_at` (not mtime).

**Apply to:** `lib/fred_cache.py` cache-file writes — Python port of `withLock()`; mirror the **flag='w' + read-back-verify** poor-man's-CAS pattern (NOT `O_EXCL`). Test parallel writes serialize correctly.

```python
def with_cache_lock(fn):
    """Python port of orchestration/lockfile.mjs:withLock for fred_cache writes.
    Mirrors all 4 invariants from lockfile.mjs:6-18 header comment."""
```

---

### Synthetic-fixture-only-in-CI policy (Phase 11 D-02)

**Source:** `tests/fixtures/subagent_transcripts/README.md` — "Why synthetic, not live (D-02)" section.

**Apply to:** `tests/fixtures/fred/` (cache fixtures) + `evals/expected/live-rate-injection-01.json` (pinned to fixture, NOT live FRED per D-12-SC1-01). Live FRED runs only on weekly cron / manual refresh, never CI.

---

### Test xfail → pass flip discipline

**Source:** `tests/test_subagents.py:9-11` ("All SUBA-01..06 tests are live (no xfail decorators remain). Wave provenance for historical traceability...") + `tests/test_skill.py:30-31` ("xfail decorator carries strict=True so a passing test in xfail state raises XPASS at collection time").

**Apply to:** Wave 0 of Phase 12 (test stubs) → Wave N (flip to passing). Use `@pytest.mark.xfail(reason="...", strict=True)` until the implementation wave lands.

---

### SCRIPT_PATH constant — single seam for relocation

**Source:** `tests/test_amortize.py:51-62`, `tests/test_stress.py:27-37` — single Path constant at top of test module; only edit point when scripts relocate.

**Apply to:** `tests/test_fred_cli.py` — define `SCRIPT_PATH` at module top pointing into `.claude/skills/mortgage-ops/scripts/fred_cli.py` (Phase 12 ships directly into the skill folder; no project-root → skill-folder relocation pass needed).

---

### Progressive disclosure — references loaded on-demand

**Source:** `.claude/skills/mortgage-ops/SKILL.md:114-138` + `tests/test_skill.py:300-316` (`test_skill_md_documents_progressive_disclosure`).

**Apply to:** `references/fred-context.md` — added to SKILL.md topic→reference table (line 134 area) with trigger phrase "what's the current rate", "FRED", "MORTGAGE30US". Test asserts the reference filename appears in SKILL.md.

---

### Data Contract Layer assignments (User / System / Data / Reference)

**Source:** `DATA_CONTRACT.md` + `CLAUDE.md §Data Contract`.

**Apply to:**
- `data/cache/fred_*.json` → **Data Layer** (generated, gitignored)
- `scripts/fred_cli.py`, `lib/fred_cache.py`, `evals/runner.py`, `evals/metrics.py` → **System Layer** (auto-updatable)
- `evals/prompts/*.md`, `evals/expected/*.json`, `tests/fixtures/fred/*.json` → **Reference Layer** (committed, manually refreshed)
- `evals/runs/*` → **Data Layer** (generated; gitignored)
- `FRED_API_KEY` → env var only; **NEVER** in `config/household.yml` or other User Layer files

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `evals/runner.py` | controller | batch | No prior eval harness in this repo. Use RESEARCH.md §Pattern 5 + §Pattern 7 for skeleton; closest internal tooling is `tests/test_subagents.py` transcript-replay loop. |
| `evals/metrics.py` | service | transform | Pure scoring functions; no prior in-repo analog. Use RESEARCH.md §Pattern 6 (hallucination detector — TIGHTENED to STDOUT-ONLY per D-12-SC3-01) + §Pattern 7 (route + numeric match rates — EXTENDED to three buckets per D-12-SC4-01). |

For both files, planner should use RESEARCH.md patterns 5/6/7 as the implementation source, but ADAPT to:
- D-12-SC4-01 three-bucket gate (pass | fail | skip)
- D-12-SC3-01 STDOUT-only sourcing (NOT cmd args / stdin)
- D-12-SC1-01 22-prompt set (21 + live-rate-injection-01)

---

## Metadata

**Analog search scope:**
- `/Users/cujo253/Documents/mortgage-ops/.claude/skills/mortgage-ops/` (scripts/, references/, SKILL.md)
- `/Users/cujo253/Documents/mortgage-ops/lib/` (rules/, models.py)
- `/Users/cujo253/Documents/mortgage-ops/orchestration/` (lockfile.mjs, db-write.mjs)
- `/Users/cujo253/Documents/mortgage-ops/tests/` (conftest.py, test_amortize.py, test_subagents.py, test_skill.py, test_stress.py, fixtures/)
- `/Users/cujo253/Documents/mortgage-ops/.github/workflows/` (ci.yml)

**Files scanned:** 18 read in full or in load-bearing range
**Pattern extraction date:** 2026-05-10
