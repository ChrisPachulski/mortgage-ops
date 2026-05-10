# Phase 11: Subagents - Research

**Researched:** 2026-05-02
**Domain:** Claude Code subagent definitions for context-isolated calc dispatch
**Confidence:** HIGH (frontmatter spec, model selection, skill resolution all verified against current Anthropic docs as of May 2026)

## Summary

Phase 11 ships three project-scoped subagents under `.claude/agents/` so that calc-heavy parameter sweeps (especially Phase 8 stress sweeps with > 5 scenarios) execute in an isolated context window and return only a summary to the main thread. Each subagent is a Markdown file with YAML frontmatter (`name`, `description`, `model`, `tools`, `skills`); the body is a focused system prompt. The `skills: [mortgage-ops]` field injects the full Phase 10 SKILL.md content into the subagent's startup context — bundled `scripts/` are filesystem-resident and reachable via the subagent's Bash tool, exactly the same way the main thread reaches them.

Model selection: `amortization-agent: haiku` (single deterministic shell-out + format), `refi-npv-agent: sonnet` (compositional ranking across multiple offers), `stress-test-agent: haiku` (a single sweep CLI call + summarization — Haiku is fine for table compression; reserve Sonnet for the refi case which actually needs reasoning). All three run with a tightly whitelisted toolset (`Read, Bash, Write` for the agents that emit CSV; `Read, Bash` for the agents that emit only inline tables).

Token-budget verification (SC-3, < 1k tokens) uses Anthropic's official `client.messages.count_tokens()` Python SDK call against a recorded transcript fixture — not a live LLM dispatch — to keep tests deterministic, free, and CI-safe. tiktoken/cl100k_base is explicitly rejected: it is OpenAI-specific and not Tiktoken-compatible with the Claude tokenizer.

**Primary recommendation:** Three project-scoped agent files at `.claude/agents/{amortization,refi-npv,stress-test}-agent.md`, each with `skills: [mortgage-ops]`, narrow `tools:` whitelist (no Edit/Write to user/data layers), and a body prompt that mirrors the SKILL.md "shell out, never compute inline; --help first, do not read source" doctrine. Token budgets pinned by `anthropic.Anthropic().messages.count_tokens(...)` against transcript fixtures.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Subagent dispatch routing | Skill (SKILL.md + modes/stress.md) | Main-thread Claude | Routing rules live in SKILL.md so all agents share the contract; main-thread Claude executes the dispatch decision |
| Subagent definition + lifecycle | Claude Code runtime (`.claude/agents/`) | Filesystem | Agents are filesystem-resident MD files Claude Code loads at session start (per Anthropic spec) |
| Calculation engine (math) | Python lib/ + scripts/ CLIs | numpy-financial / pyxirr | Subagents NEVER compute numbers — they shell out to the same scripts the main thread uses (CLAUDE.md + PROJECT.md "Math correctness first") |
| Token-budget verification | pytest + anthropic-py count_tokens | Transcript fixtures | Test asserts the agent's output token count without invoking the LLM; deterministic + free + CI-safe |
| Skill content injection | `skills:` frontmatter (Anthropic-resolved) | `.claude/skills/mortgage-ops/SKILL.md` | Phase 10 ships the skill; Phase 11 references it by name; runtime injects content at agent spawn |
| Bundled-script access | Subagent Bash tool + filesystem | `.claude/skills/mortgage-ops/scripts/` | Bundled scripts are regular files; the Bash tool reaches them at the same path the main thread does |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Claude Code subagent spec | latest (docs current 2026-05) | Agent file format + dispatch | The official Anthropic mechanism — no alternative `[VERIFIED: code.claude.com/docs/en/sub-agents]` |
| `pyyaml` | >=6.0.2 (already pinned in pyproject.toml) | Frontmatter parsing for SC-1 test | Already in the project's dependency graph (used by reference YAML loaders); no new dep `[VERIFIED: pyproject.toml line 8]` |
| `anthropic` Python SDK | >=0.40 (latest as of 2026-05; verify with `pip index versions anthropic`) | `client.messages.count_tokens()` for SC-3 token-budget assertion | Official tokenizer; tiktoken is OpenAI-specific and inaccurate for Claude `[CITED: platform.claude.com/docs/en/build-with-claude/token-counting]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | >=9.0 (already pinned) | All Phase 11 tests | Project standard; no new dep `[VERIFIED: pyproject.toml line 14]` |
| `subprocess` (stdlib) | n/a | Smoke test: spawn agent → assert it can `bash`-run a bundled script | The `Bash` tool ultimately invokes a subprocess; tests can simulate the same path |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `anthropic.count_tokens` | `tiktoken` cl100k_base | REJECTED — OpenAI-only tokenizer, "anecdotally not great" accuracy for Claude `[CITED: blog.gopenai.com/counting-claude-tokens-without-a-tokenizer]`. count_tokens is FREE (separate rate limit, doesn't bill content) `[CITED: platform.claude.com/docs/en/build-with-claude/token-counting]` |
| `anthropic.count_tokens` (live) | Local approximation (chars/4) | REJECTED for SC-3 verification — < 1k token budget is tight enough that ±20% approximation drift could mask a real overage. count_tokens is the source of truth. |
| Project-scope `.claude/agents/` | User-scope `~/.claude/agents/` | Project-scope wins: agent definitions ARE the artifact under test (SC-1) and must be checked into version control with the rest of the skill `[VERIFIED: code.claude.com/docs/en/sub-agents — "Project subagents (`.claude/agents/`) are ideal for subagents specific to a codebase. Check them into version control"]` |
| Three subagents | One generic "calc-agent" | REJECTED per PROJECT.md decision #5 (locked) — three distinct dispatch surfaces let SKILL.md route deterministically by intent (amortize vs refi vs stress) and let Haiku/Sonnet selection match the actual reasoning load |

**Installation:**

```bash
# anthropic SDK is the only new dependency
uv add --group dev anthropic
```

**Version verification:**

```bash
# Run before pinning the version in pyproject.toml
pip index versions anthropic 2>/dev/null | head -2
# Expected: anthropic (X.Y.Z) — current latest as of 2026-05
```

`[ASSUMED]` exact version pin — the planner should run `pip index versions anthropic` at plan time to lock the current latest. This research did not invoke the registry.

## Architecture Patterns

### System Architecture Diagram

```
                   ┌──────────────────────────┐
                   │  Main Claude conversation│
                   │  (any model — opus/sonnet)│
                   └────────┬─────────────────┘
                            │
                            │ user: "stress-test 50 rate-shock scenarios"
                            ▼
               ┌────────────────────────────┐
               │  SKILL.md routing logic    │  ← Phase 10 ships this
               │  (modes/stress.md)         │
               └────────┬───────────────────┘
                        │
            ┌───────────┼───────────────┐
            │   if scenario_count > 5   │
            ▼                           │
  ┌─────────────────────┐               │  if scenario_count ≤ 5
  │ Dispatch via Agent  │               │  → main thread runs script inline
  │ tool to             │               │
  │ stress-test-agent   │               │
  └─────────┬───────────┘               │
            │                           │
            ▼                           │
  ┌────────────────────────────────┐    │
  │  stress-test-agent (haiku)     │    │
  │  ─ skills: [mortgage-ops]      │    │  ← injected at spawn time
  │  ─ tools: Read, Bash           │    │
  │                                │    │
  │  1. bash: scripts/stress_test  │    │
  │     --mode rate-shock          │    │
  │     --rates 0.06,0.065,...     │    │
  │  2. read JSON output           │    │
  │  3. summarize: rank by         │    │
  │     dti_back, flag breaches    │    │
  │  4. RETURN ≤ 1k token markdown │    │
  └─────────┬──────────────────────┘    │
            │                           │
            └─────────┬─────────────────┘
                      ▼
           ┌──────────────────┐
           │  Summary returned │
           │  to main context  │
           │  (≤ 1k tokens)    │
           └──────────────────┘
```

### Recommended Project Structure

```
.claude/
├── agents/                              # ← Phase 11 ships these 3 files
│   ├── amortization-agent.md            # Haiku, calls scripts/amortize.py
│   ├── refi-npv-agent.md                # Sonnet, sweeps refi offers
│   └── stress-test-agent.md             # Haiku, dispatches stress sweeps
└── skills/
    └── mortgage-ops/                    # ← Phase 10 ships this
        ├── SKILL.md                     # routing; modes/stress.md has the >5 rule
        ├── modes/
        │   ├── stress.md                # documents subagent dispatch
        │   ├── amortize.md
        │   └── refinance.md
        ├── scripts/
        │   ├── stress_test.py           # invoked by stress-test-agent
        │   ├── amortize.py              # invoked by amortization-agent
        │   ├── refi_npv.py              # invoked by refi-npv-agent
        │   └── ...
        └── references/
            └── ...

tests/
├── test_subagents.py                    # ← Phase 11 ships
│   - test_SUBA_01_frontmatter_parses    # YAML parse + required fields
│   - test_SUBA_04_skills_field_lists_mortgage_ops
│   - test_SUBA_05_stress_routing_in_modes_stress
│   - test_SUBA_06_summary_under_1k_tokens (transcript fixture)
└── fixtures/
    └── subagent_transcripts/            # ← Phase 11 ships
        ├── stress_50_scenario_summary.md
        ├── refi_3_offer_ranked.md
        └── amortize_single_loan.md
```

### Pattern 1: Project-scoped subagent file

**What:** Markdown file with YAML frontmatter, body is the system prompt
**When to use:** Always for Phase 11 — never user-scope (must be version-controlled)
**Example:**

```markdown
---
name: amortization-agent
description: Generates amortization schedules from a single-loan request. Use when the user asks for a payment schedule, monthly P&I, total interest, or biweekly/extra-principal scenarios for ONE loan. Returns a markdown table or a CSV file path.
model: haiku
tools: Read, Bash, Write
skills:
  - mortgage-ops
---

[system prompt body]
```

`[CITED: code.claude.com/docs/en/sub-agents — Quickstart and Supported frontmatter fields]`

### Pattern 2: Skills preloading

**What:** `skills: [mortgage-ops]` injects the full SKILL.md content into the subagent's context at startup
**When to use:** Always for Phase 11 — every agent needs the SKILL.md routing/conventions/script-help doctrine
**Verbatim from Anthropic docs:**

> "The full content of each skill is injected into the subagent's context, not just made available for invocation. Subagents don't inherit skills from the parent conversation; you must list them explicitly." `[CITED: code.claude.com/docs/en/sub-agents § Preload skills into subagents]`

**Implication for SC-5:** Bundled scripts under `.claude/skills/mortgage-ops/scripts/` are filesystem files, not context-loaded content. The `skills:` injection brings the SKILL.md *instructions* into context; the scripts themselves remain on disk and are reached via the subagent's `Bash` tool the same way the main thread reaches them. SC-5's "smoke test that asserts the subagent has access to bundled scripts" is verified by spawning the agent and confirming `bash: ls .claude/skills/mortgage-ops/scripts/amortize.py` succeeds — not by checking that the script content is in the context window.

### Pattern 3: Tool whitelist

**What:** Explicit `tools:` field is an allowlist; subagent inherits NOTHING outside the list
**When to use:** Always for Phase 11 — enforce "shell out for math, don't write to user layer"
**Example:**

```yaml
tools: Read, Bash, Write
```

Phase 11's three agents need:
- `Read` — read fixture inputs, household.yml (read-only per DATA_CONTRACT)
- `Bash` — invoke scripts/*.py
- `Write` — only for amortization-agent (CSV output) and stress-test-agent (could write a CSV summary). refi-npv-agent doesn't need Write (returns inline ranked table).

`[CITED: code.claude.com/docs/en/sub-agents § Available tools]`

### Anti-Patterns to Avoid

- **Subagent that recomputes numbers inline:** Violates PROJECT.md core value ("Math correctness first. Every dollar figure must be traceable to a tested deterministic Python function"). The system prompt MUST instruct the agent to shell out to scripts, never compute.
- **Subagent that writes to User Layer:** household.yml, profile.yml, mortgage-ops.duckdb are read-only from system code per DATA_CONTRACT.md. The subagent prompt MUST repeat this constraint. (Defense-in-depth: the pre-commit hook catches it post-hoc, but the prompt prevents it pre-hoc.)
- **Subagent that returns the raw 50-scenario JSON:** Defeats the entire point of context isolation. The prompt MUST instruct: "Read the full JSON, extract the table, return ONLY the summary." SC-3 (< 1k tokens) is the test gate.
- **Setting `disallowedTools` AND `tools`:** Pick one. The Anthropic spec says `disallowedTools` is applied first, then `tools` is resolved against the remainder — confusing and error-prone. Use `tools:` (allowlist) only.
- **Subagents trying to spawn other subagents:** Not supported. "Subagents cannot spawn other subagents, so `Agent(agent_type)` has no effect in subagent definitions." `[CITED: code.claude.com/docs/en/sub-agents]`. If we ever need that, the routing decision must happen in the main thread.
- **Live LLM calls in CI:** Burns API credits, is non-deterministic, and breaks airgapped CI. SC-3/SC-4/SC-6 use *recorded transcript fixtures* + offline `count_tokens` calls.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tokenizer for Claude | Custom char-counter or tiktoken approximation | `anthropic.Anthropic().messages.count_tokens(model="claude-haiku-4-5", messages=[...])` | Tiktoken is OpenAI-specific; rough approximations drift ±20% on the < 1k boundary `[CITED: platform.claude.com/docs/en/build-with-claude/token-counting]` |
| Subagent dispatcher | Custom routing layer in SKILL.md that explicitly invokes the Task tool | Just write the description and let Claude auto-delegate per `description` field | "Claude uses each subagent's description to decide when to delegate tasks." Auto-delegation is the supported path. `[CITED: code.claude.com/docs/en/sub-agents § Understand automatic delegation]` |
| Skill-content loader | Write a script that reads SKILL.md and prepends to system prompt | Use `skills: [mortgage-ops]` frontmatter — Anthropic injects it at spawn | Per spec, "the full content of each skill is injected into the subagent's context" |
| Frontmatter parser | Custom regex on `---` blocks | `pyyaml.safe_load` on the head block | pyyaml is already in pyproject.toml; safe_load handles the spec correctly |
| Token-budget assertion harness | Build an LLM-call harness that records transcripts | Hand-author transcript fixtures from one-off live runs (committed under `tests/fixtures/subagent_transcripts/`) + assert via count_tokens | Deterministic, free at CI time, regenerable when the contract changes |

**Key insight:** Phase 11's "code" is mostly YAML frontmatter and prompt copy. The complexity is in the *test discipline*, not the agent definitions themselves. Three short MD files + a focused test suite + an `anthropic` SDK dev dep is the entire surface area.

## Runtime State Inventory

> Phase 11 is greenfield (introduces new files); no rename/refactor of existing runtime state. This section is included for completeness because Phase 11 *creates* runtime state that downstream phases (12) will assume exists.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 11 ships no persistent data; agent transcripts are session-scoped per Anthropic spec | None |
| Live service config | Subagent definitions are filesystem-resident under `.claude/agents/`; loaded at session start. Restart of Claude Code is required after manual file changes (per docs Note: "Subagents are loaded at session start. If you create a subagent by manually adding a file, restart your session or use `/agents` to load it immediately.") | Document in modes/stress.md / README.md so user knows to restart Claude Code after Phase 11 ships |
| OS-registered state | None | None |
| Secrets/env vars | `ANTHROPIC_API_KEY` required ONLY if developer wants to regenerate transcript fixtures live (not required at CI time — fixtures are committed) | Document in tests/fixtures/subagent_transcripts/README.md |
| Build artifacts / installed packages | `uv add anthropic` adds the SDK to `uv.lock` — committed | Verify `uv sync` is idempotent in CI |

## Common Pitfalls

### Pitfall 1: Treating `skills:` as a script-bundling mechanism
**What goes wrong:** Author writes `skills: [mortgage-ops]` and assumes the bundled scripts under `.claude/skills/mortgage-ops/scripts/` are now "imported" into the subagent's context.
**Why it happens:** The Anthropic docs say "the full content of each skill is injected" — but "skill content" means SKILL.md and its referenced markdown files at progressive-disclosure load time, NOT the executable scripts. Scripts remain on disk and are reached via Bash.
**How to avoid:** SC-5's smoke test must `bash: ls -la .claude/skills/mortgage-ops/scripts/amortize.py` (assert filesystem reachability via Bash), not assert that the script source is in the context window.
**Warning signs:** Test asserts `"def amortize" in context` instead of `subprocess.run(["bash", "-c", "ls .claude/skills/..."])`.

### Pitfall 2: Description field too vague → wrong agent gets dispatched
**What goes wrong:** All three agents have similar descriptions ("calculates mortgage stuff"), so Claude routes ambiguously: amortization questions go to refi-npv-agent, stress sweeps go to amortization-agent, etc.
**Why it happens:** Description is the dispatch signal — Claude reads it to decide which agent to delegate to. Vague or overlapping descriptions cause routing collisions.
**How to avoid:** Each description names (a) the specific intent ("single-loan amortization", "rank competing refi offers", "parameter-grid sweeps with > 5 scenarios"), (b) the *output shape* the agent returns (markdown table, CSV path, ranked NPV table, < 1k summary), (c) the trigger keyword pattern ("when user asks for X").
**Warning signs:** SC-2 / SC-4 eval prompts in Phase 12 misroute. Mitigation: ship a routing eval in Phase 12 (EVAL-03) that exercises ambiguous prompts and asserts the right agent gets picked.

### Pitfall 3: Forgetting to restart Claude Code after editing agent files
**What goes wrong:** Developer edits `.claude/agents/stress-test-agent.md`, runs the test suite, sees the same old behavior — assumes the test is broken or the change didn't take.
**Why it happens:** Per Anthropic spec: "Subagents are loaded at session start. If you create a subagent by manually adding a file, restart your session or use `/agents` to load it immediately." Tests that exercise live agent dispatch (vs. fixture-driven tests) need a fresh session.
**How to avoid:** SC-1/SC-2/SC-5 tests are file-system-only (parse the .md, regex the routing rule, ls the scripts dir) — no live agent invocation needed. SC-3/SC-4 use recorded transcripts. Reserve live invocation for manual verification only, and document the restart requirement in tests/test_subagents.py docstring.
**Warning signs:** A test passes locally after a session restart but fails in CI. CI doesn't have an interactive Claude Code session — but our tests don't need one because they're fixture-driven.

### Pitfall 4: count_tokens drift between SDK versions
**What goes wrong:** The `anthropic` SDK pin in pyproject.toml is loose (>=0.40), a new version changes the response shape (`.input_tokens` → `.usage.input_tokens`), and SC-3 starts failing in CI.
**Why it happens:** SDK is on rapid release cadence; the count_tokens response shape has changed before.
**How to avoid:** Pin a tight SDK version in pyproject.toml (`anthropic==X.Y.Z`); add a smoke test `test_count_tokens_response_shape` that asserts `response.input_tokens` is an int. Bump deliberately, not transitively.
**Warning signs:** CI flake on `'Anthropic' object has no attribute 'messages'` or `AttributeError: 'CountTokensResponse' object has no attribute 'input_tokens'`.

### Pitfall 5: Subagent emits raw JSON instead of summary
**What goes wrong:** stress-test-agent runs `scripts/stress_test.py`, gets back the full 50-scenario JSON, dumps it verbatim. Output is 8k tokens, blowing past the 1k budget.
**Why it happens:** Default LLM behavior on "I have data, return it" is "show the data". The system prompt MUST explicitly say "DO NOT return the raw JSON. Read it, extract a summary table, return ONLY the summary."
**How to avoid:** Hard rule in the agent body prompt + SC-3 token-budget test as the gate. SC-3 catches this exact failure mode.
**Warning signs:** The transcript fixture you author for SC-3 is itself > 1k tokens. If you can't write a < 1k summary by hand, the agent prompt is asking the wrong thing.

## Code Examples

Verified patterns from official sources and project files.

### Example 1: Frontmatter for amortization-agent (Haiku)

```markdown
---
name: amortization-agent
description: Generates a single-loan amortization schedule. Use when the user asks for a payment schedule, monthly P&I, total interest, biweekly cadence, or extra-principal scenarios for ONE loan (not a sweep). Returns a markdown table or a CSV file path. Does NOT compute numbers — always shells out to scripts/amortize.py.
model: haiku
tools: Read, Bash, Write
skills:
  - mortgage-ops
---

You are the mortgage-ops amortization specialist. Your one job is to take a single-loan request, shell out to the amortization CLI, and return a clean output.

## Hard rules

1. **Never compute numbers inline.** Every dollar figure comes from `scripts/amortize.py`. If you do mental math, you have failed the task.
2. **Run --help first.** Before invoking the script, check its current usage with `bash: python .claude/skills/mortgage-ops/scripts/amortize.py --help`. Do not read the script source.
3. **READ-ONLY user layer.** Never write to `config/household.yml`, `config/profile.yml`, or `data/mortgage-ops.duckdb`. You can read them.
4. **Output format.** Return ONE of:
   - A markdown table (≤ 50 rows; if more, return a CSV path).
   - A CSV file path under `reports/{###}-amortization-{YYYY-MM-DD}.csv` (write via the Write tool).
5. **Validation surfaces.** If `scripts/amortize.py` exits non-zero, the stderr is a 6-key Pydantic envelope. Surface the `loc` (which field) and `msg` (why) verbatim — do not paraphrase.

## Workflow

1. Receive the loan request as natural language or a JSON-shaped dict.
2. Construct the input JSON per the script's `--help` (all money/rate fields are JSON STRINGS; floats rejected).
3. Write the input JSON to a tmpfile under `/tmp/`.
4. Invoke: `bash: python .claude/skills/mortgage-ops/scripts/amortize.py --input /tmp/<file>.json`.
5. Parse the JSON output. Format as a markdown table OR write to a CSV and return the path.
6. Return a 2-3 line summary above the table/path: "30-year fixed @ 6.5%, $400k principal → $2,528.27 monthly P&I, $510,178.20 total interest. Schedule below."

## Cost discipline

You are running on Haiku because this work is one shell-out + one format. If a request would require multiple amortization runs (e.g., comparing 3 rate scenarios), you are the WRONG agent — return: "This is a multi-loan comparison. Route to refi-npv-agent or stress-test-agent."
```

### Example 2: Frontmatter for refi-npv-agent (Sonnet)

```markdown
---
name: refi-npv-agent
description: Sweeps multiple refinance offers and returns a ranked NPV table with breakeven analysis. Use when the user has 2+ refi quotes and asks "which is best?" or "rank by NPV" or "what's the breakeven on each?". Composes scripts/refi_npv.py across all offers. Returns a ranked table to the main context.
model: sonnet
tools: Read, Bash
skills:
  - mortgage-ops
---

You are the mortgage-ops refinance NPV specialist. You compose multiple `scripts/refi_npv.py` invocations to rank competing refi offers from a borrower's perspective.

## Hard rules

1. **Never compute NPV inline.** Every NPV number comes from `scripts/refi_npv.py`. Sign convention: outflows negative, savings positive (per `references/refi-npv.md`).
2. **Run --help first.** Check `bash: python .claude/skills/mortgage-ops/scripts/refi_npv.py --help`. Do not read the script source.
3. **READ-ONLY user layer.** Read `config/household.yml` for the current loan if needed. Never write user-layer files.
4. **Output format.** A ranked markdown table, sorted by NPV descending. Columns: lender | rate | closing_costs | breakeven_months | NPV (with sign). Plus a 2-3 sentence narrative naming the winner and the runner-up reason.
5. **Sign-convention discipline.** If a refi has NPV < 0, surface that with a "❌ negative NPV" annotation. The user must understand sign convention by reading the table.

## Workflow

1. Receive 2+ refi offers (lender, rate, term, closing_costs, etc.) plus the current loan.
2. For each offer, construct the JSON input per `--help`.
3. Invoke `scripts/refi_npv.py --input /tmp/<file>.json` once per offer.
4. Collect outputs, build a ranked table.
5. Return: ranked table + 2-3 sentence narrative + breakeven warnings.

## Cost discipline

You are running on Sonnet because ranking compositions require reasoning about tradeoffs (rate vs. closing costs vs. cash-out). If the user has only ONE refi to evaluate, you are the WRONG agent — return: "Single-offer refi → main thread can run `scripts/refi_npv.py` directly without subagent dispatch."
```

### Example 3: Frontmatter for stress-test-agent (Haiku)

```markdown
---
name: stress-test-agent
description: Runs parameter-grid stress sweeps (rate-shock, income-shock, ARM-reset path) and returns a < 1k token summary. Use when the user requests a sweep with > 5 scenarios. Dispatches scripts/stress_test.py with the full grid, then summarizes — does NOT return raw scenario data.
model: haiku
tools: Read, Bash, Write
skills:
  - mortgage-ops
---

You are the mortgage-ops stress-test specialist. Your one job: run a parameter sweep, summarize the results in < 1,000 tokens, return ONLY the summary.

## Hard rules

1. **NEVER return raw JSON.** The point of dispatching to you is context isolation. The full sweep output stays in YOUR context; only the summary returns to the main thread. If your output is > 1,000 tokens, you have failed the task.
2. **Never compute numbers inline.** All sweep numbers come from `scripts/stress_test.py`.
3. **Run --help first.** `bash: python .claude/skills/mortgage-ops/scripts/stress_test.py --help`.
4. **READ-ONLY user layer.** Read household.yml; never write it.
5. **Output format.** A markdown table of ≤ 10 representative rows (binned/sampled if > 10) + 2-3 sentence narrative naming (a) the worst-case scenario, (b) which scenarios breach the configured affordability threshold, (c) the median outcome.
6. **CSV escape hatch.** If the user explicitly asks for the full sweep, write the JSON to `reports/{###}-stress-{YYYY-MM-DD}.csv` via the Write tool and return the PATH (not the content).

## Workflow

1. Receive the sweep request (mode + parameter grid).
2. Construct one input JSON per `--help`.
3. Invoke `scripts/stress_test.py --input /tmp/<file>.json` ONCE — the script handles the full grid internally.
4. Read the JSON output (full payload stays in your context).
5. Bin/sample to ≤ 10 representative rows.
6. Compose the summary table + narrative.
7. Return summary + (optionally) CSV path.

## Token budget

Your output target is ≤ 1,000 tokens to the main context. If you cannot summarize in 1k tokens, you are returning too much detail — go coarser on the binning.

## Cost discipline

You are running on Haiku because this is one shell-out + one summarization. The reasoning load is "compress this table to its essential shape" — Haiku is fine for that. Reserve Sonnet for the refi case where ranking requires tradeoff reasoning.
```

### Example 4: SUBA-01 frontmatter parse test

```python
# tests/test_subagents.py
"""SUBA-01..06 tests for Phase 11 subagent definitions.

Source: SC-1..SC-5 in ROADMAP.md Phase 11.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable

AGENTS_DIR = Path(__file__).parent.parent / ".claude" / "agents"
SKILLS_DIR = Path(__file__).parent.parent / ".claude" / "skills" / "mortgage-ops"
EXPECTED_AGENTS = ["amortization-agent", "refi-npv-agent", "stress-test-agent"]
VALID_MODELS = {"haiku", "sonnet", "opus", "inherit"}


def _split_frontmatter(md_path: Path) -> dict:
    """Parse the YAML frontmatter from a markdown agent file.

    Spec: file starts with '---\n', frontmatter ends at next '---\n', body follows.
    """
    text = md_path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{md_path}: missing opening '---' frontmatter delimiter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"{md_path}: missing closing '---' frontmatter delimiter")
    return yaml.safe_load(parts[1])


@pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
def test_SUBA_01_frontmatter_parses_with_required_fields(agent_name: str) -> None:
    """SC-1: frontmatter has model, skills: [mortgage-ops], description, name."""
    fm = _split_frontmatter(AGENTS_DIR / f"{agent_name}.md")
    assert fm["name"] == agent_name
    assert isinstance(fm["description"], str) and len(fm["description"]) > 30
    assert fm["model"] in VALID_MODELS or re.match(r"^claude-(haiku|sonnet|opus)-", fm["model"])
    assert fm["skills"] == ["mortgage-ops"], "SUBA-04: skills frontmatter must be [mortgage-ops]"


def test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent() -> None:
    """SC-2: modes/stress.md documents the >5 scenario dispatch rule."""
    stress_md = (SKILLS_DIR / "modes" / "stress.md").read_text()
    # Regex matches phrasings like "scenarios > 5", "more than 5 scenarios",
    # "scenario_count > 5" — pinned by an explicit positive assertion.
    pattern = re.compile(
        r"(scenarios?\s*(>|more than|greater than)\s*5|scenario[_ ]count\s*>\s*5).*"
        r"(stress-test-agent|subagent)",
        re.IGNORECASE | re.DOTALL,
    )
    assert pattern.search(stress_md), (
        "modes/stress.md must document 'sweeps with > 5 scenarios route to stress-test-agent'"
    )


@pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
def test_SUBA_05_skill_resolution_smoke(agent_name: str) -> None:
    """SC-5: subagent's skills frontmatter resolves at spawn time.

    Smoke test: assert (a) the named skill exists on disk, (b) bundled scripts
    are reachable via the subagent's Bash tool path (filesystem-only check;
    we do not invoke the LLM here).
    """
    fm = _split_frontmatter(AGENTS_DIR / f"{agent_name}.md")
    assert "mortgage-ops" in fm["skills"]
    skill_md = SKILLS_DIR / "SKILL.md"
    assert skill_md.exists(), f"SUBA-05: {skill_md} must exist (Phase 10 dependency)"
    # Bundled scripts are filesystem files; bash reaches them at this exact path.
    expected_scripts = ["amortize.py", "refi_npv.py", "stress_test.py"]
    for script in expected_scripts:
        path = SKILLS_DIR / "scripts" / script
        assert path.exists(), f"SUBA-05: {path} must exist (Phase 10 dependency)"
```

### Example 5: SUBA-06 token-budget test (transcript fixture)

```python
# tests/test_subagents.py (continued)
import os

import pytest

# Skip the count_tokens test if the SDK or API key isn't available.
# We intentionally use the SDK at *test* time only — production agent dispatch
# does NOT call count_tokens. The test asserts the recorded transcript fixture
# (representative of what the agent returns) fits in the budget.
anthropic = pytest.importorskip("anthropic")

TRANSCRIPT_DIR = Path(__file__).parent / "fixtures" / "subagent_transcripts"


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="SUBA-06 token-budget test requires ANTHROPIC_API_KEY (free tier; count_tokens is not billed for content)",
)
def test_SUBA_06_stress_summary_under_1k_tokens() -> None:
    """SC-3: 50-scenario rate-shock summary fits under 1,000 tokens.

    Uses the official anthropic count_tokens API against a recorded transcript
    fixture. tiktoken is REJECTED — it is OpenAI-specific and not Tiktoken-
    compatible with the Claude tokenizer.

    Trade-off: this test requires ANTHROPIC_API_KEY at run time. count_tokens
    is FREE (separate rate limit, no content billing) but still requires a
    network round-trip. CI must inject the key as a secret. The skipif gate
    keeps local dev unblocked for engineers without the key.

    Reproducibility: the transcript fixture is committed at
    tests/fixtures/subagent_transcripts/stress_50_scenario_summary.md and
    represents what stress-test-agent returns to the main thread for a
    canonical 50-scenario rate-shock sweep. Regenerate by manually invoking
    the agent and copying the summary; document the regeneration ritual in
    the fixture's README.md.
    """
    transcript = (TRANSCRIPT_DIR / "stress_50_scenario_summary.md").read_text()
    client = anthropic.Anthropic()
    response = client.messages.count_tokens(
        model="claude-haiku-4-5",
        messages=[{"role": "assistant", "content": transcript}],
    )
    assert response.input_tokens < 1000, (
        f"SUBA-06: stress summary returned {response.input_tokens} tokens, exceeds 1000-token budget"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tools` field as comma-separated string | Same — still comma-separated; YAML list `tools: [Read, Bash]` also accepted | n/a | Both work; comma-separated is in the official examples |
| Task tool name | `Agent` tool (Task is a backwards-compatible alias) | Claude Code 2.1.63 | Existing `Task(...)` references still work; new code should use `Agent(...)` `[CITED: code.claude.com/docs/en/sub-agents § Restrict which subagents can be spawned]` |
| Manual SKILL.md content paste | `skills: [name]` frontmatter auto-injection | Recent | The mechanism Phase 11 depends on |
| tiktoken approximations | `client.messages.count_tokens()` | SDK >= 0.40 | The only accurate way to count tokens for Claude |

**Deprecated/outdated:**
- Manually injecting SKILL.md by paste-into-prompt: superseded by `skills:` frontmatter
- tiktoken cl100k_base for Claude token counts: never accurate; explicitly called out as inaccurate by community sources

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUBA-01 | `.claude/agents/amortization-agent.md` — Haiku, runs amortize/scripts; returns markdown table or CSV path | Frontmatter spec verified; model alias `haiku` is in `VALID_MODELS`; `tools: Read, Bash, Write` covers script invocation + CSV emission; draft frontmatter in Code Example 1 |
| SUBA-02 | `.claude/agents/refi-npv-agent.md` — Sonnet (multi-step NPV reasoning), can sweep multiple offers | Sonnet is the right tier per the Augment Code 2026 routing guide ("Sonnet for complex reasoning, ranking, tradeoffs"); `tools: Read, Bash` (no Write — returns inline table); draft frontmatter in Code Example 2 |
| SUBA-03 | `.claude/agents/stress-test-agent.md` — Haiku, runs parameter-grid sweeps; returns < 1k token summary | Haiku is appropriate — the reasoning load is "compress table to representative shape", not multi-step composition. The hard token budget enforces summarization discipline. Draft frontmatter in Code Example 3 |
| SUBA-04 | Each subagent has `skills: [mortgage-ops]` frontmatter to preload skill content | Verified mechanism per Anthropic docs § Preload skills into subagents; full SKILL.md content injects at spawn; subagents do NOT inherit skills from parent — must list explicitly |
| SUBA-05 | Stress mode invokes stress-test-agent for sweeps > 5 scenarios | Routing rule lives in `.claude/skills/mortgage-ops/modes/stress.md` (Phase 10 file); SC-2 test regex-asserts the rule; auto-delegation is the supported mechanism (description-driven) |
| SUBA-06 | End-to-end test: 50-scenario stress sweep returns summary < 1k tokens to main context | Test uses `anthropic.Anthropic().messages.count_tokens(model="claude-haiku-4-5", messages=[...])` against a recorded transcript fixture. Skipif on missing API key. tiktoken explicitly rejected. |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ (already in `pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_subagents.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SUBA-01 | amortization-agent.md frontmatter parses | unit (yaml) | `pytest tests/test_subagents.py::test_SUBA_01_frontmatter_parses_with_required_fields[amortization-agent] -x` | ❌ Wave 0 |
| SUBA-02 | refi-npv-agent.md frontmatter parses + model=sonnet | unit (yaml) | `pytest tests/test_subagents.py::test_SUBA_01_frontmatter_parses_with_required_fields[refi-npv-agent] -x` + a model-pin assertion | ❌ Wave 0 |
| SUBA-03 | stress-test-agent.md frontmatter parses + model=haiku | unit (yaml) | `pytest tests/test_subagents.py::test_SUBA_01_frontmatter_parses_with_required_fields[stress-test-agent] -x` + a model-pin assertion | ❌ Wave 0 |
| SUBA-04 | Each agent's skills field is `[mortgage-ops]` | unit (yaml) | Same parametrized test as SUBA-01; assertion line `assert fm["skills"] == ["mortgage-ops"]` | ❌ Wave 0 |
| SUBA-05 | modes/stress.md routes >5 scenarios; bundled scripts reachable | unit (regex + filesystem) | `pytest tests/test_subagents.py::test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent -x` + `test_SUBA_05_skill_resolution_smoke` | ❌ Wave 0 |
| SUBA-06 | 50-scenario summary < 1k tokens (transcript fixture) | integration (count_tokens API) | `pytest tests/test_subagents.py::test_SUBA_06_stress_summary_under_1k_tokens -x` (skipif no API key) | ❌ Wave 0 |
| (bonus) SUBA-04+SC-4 | refi-npv-agent ranks 3 offers; amortization-agent returns CSV path | integration (transcript fixture) | `test_SUBA_04_refi_ranked_table_under_1k_tokens` + `test_SUBA_04_amortize_csv_or_markdown_table` (same fixture pattern) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_subagents.py -x`
- **Per wave merge:** `uv run pytest` (full project suite — Phase 11 adds ~7-10 tests)
- **Phase gate:** Full suite green + SC-1..SC-5 verbatim assertions pass before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_subagents.py` — covers SUBA-01..06 (new file)
- [ ] `tests/fixtures/subagent_transcripts/stress_50_scenario_summary.md` — committed transcript fixture for SC-3
- [ ] `tests/fixtures/subagent_transcripts/refi_3_offer_ranked.md` — committed transcript fixture for SC-4 (refi)
- [ ] `tests/fixtures/subagent_transcripts/amortize_single_loan.md` — committed transcript fixture for SC-4 (amortize)
- [ ] `tests/fixtures/subagent_transcripts/README.md` — documents how to regenerate fixtures (manual live invocation + paste)
- [ ] `uv add --group dev anthropic` — pin SDK version after `pip index versions anthropic` lookup
- [ ] `.claude/agents/.gitkeep` — seam directory if no agents present yet during planning iteration
- [ ] `.claude/agents/amortization-agent.md` — Phase 11 deliverable
- [ ] `.claude/agents/refi-npv-agent.md` — Phase 11 deliverable
- [ ] `.claude/agents/stress-test-agent.md` — Phase 11 deliverable
- [ ] `.claude/skills/mortgage-ops/modes/stress.md` — Phase 10 deliverable; Phase 11 inserts the >5 routing rule (or asserts it's already there)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Subagents inherit Claude Code's auth; no separate identity |
| V3 Session Management | no | Sessions are Claude Code's responsibility |
| V4 Access Control | yes | Tool whitelist (`tools:` field) is the access-control surface; agents NEVER get Edit/Write to `config/` (User Layer) — verified by DATA_CONTRACT.md and the pre-commit hook |
| V5 Input Validation | yes (delegated) | Inputs reach scripts as JSON files; scripts already enforce Pydantic v2 strict + 6-key envelope on validation failure (Phase 3 D-19, inherited). Agents must surface errors verbatim, not paraphrase. |
| V6 Cryptography | no | No crypto handling in Phase 11 |
| V7 Error Handling | yes | Agents MUST surface the 6-key Pydantic envelope verbatim when scripts exit non-zero — never silently swallow or paraphrase the error |
| V12 Files and Resources | yes | Agents read User Layer (household.yml) but NEVER write it; `tools` whitelist enforces; pre-commit hook is the belt-and-suspenders |

### Known Threat Patterns for subagent dispatch

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Subagent writes to User Layer (household.yml) | Tampering | `tools` whitelist (Write only when needed); explicit prompt rule; pre-commit hook on commit; CI re-runs the hook |
| Subagent leaks sensitive household data via summary | Information Disclosure | Phase 11 doesn't change household-data exposure surface — same data the main thread already sees. Subagent summaries should follow same redaction conventions as main-thread reports (no SSNs, applicant DOBs in markdown output). |
| Subagent paraphrases a Pydantic validation error and hides the offending field | Repudiation / poor error tracing | Hard rule in agent prompts: surface stderr 6-key envelope `loc` + `msg` verbatim |
| Subagent runs an arbitrary bash command not whitelisted | Elevation of Privilege | The `Bash` tool is broad — there is no fine-grained per-command allowlist in vanilla subagent frontmatter. If we need it, use a `PreToolUse` hook with a validator script (Anthropic-supported pattern; see code.claude.com/docs/en/sub-agents § Conditional rules with hooks). For Phase 11, we accept the risk: the agent prompts only ever invoke `python .claude/skills/mortgage-ops/scripts/<name>.py --input ...` and the project-scope agent files are version-controlled (any change is reviewable). |

## Project Constraints (from CLAUDE.md)

These are CLAUDE.md / PROJECT.md / DATA_CONTRACT.md directives that Phase 11 MUST honor:

1. **Math correctness first** — subagents NEVER compute numbers; always shell out to `scripts/*.py` (CLAUDE.md "Calc engine separation").
2. **`--help` first; do not read source** — agents check script help before invocation; do not read script source for "customization" (Anthropic webapp-testing doctrine, lifted into CLAUDE.md).
3. **READ-ONLY user layer** — `config/household.yml`, `config/profile.yml`, `data/mortgage-ops.duckdb` are User Layer; subagents read but NEVER write them. Pre-commit hook + `.gitignore` are the enforcement; agent prompts repeat the rule for defense-in-depth.
4. **Scripts live INSIDE `.claude/skills/mortgage-ops/scripts/`** — Phase 10 will physically relocate scripts from project root to the skill folder (CLAUDE.md decision #8 / Phase 3 D-17). Agent prompts reference the skill-resident path: `.claude/skills/mortgage-ops/scripts/amortize.py`. NOT `scripts/amortize.py`.
5. **6-key Pydantic envelope verbatim** — when a script exits non-zero, stderr is the canonical 6-key envelope (`type`, `loc`, `msg`, `input`, `url`, `ctx`). Agents surface `loc` + `msg` verbatim; do not paraphrase.
6. **No Co-Authored-By Claude/Anthropic in commits** — global rule (`/Users/cujo253/CLAUDE.md`). Phase 11 commits must follow this.
7. **uv lockfile + reproducible installs** — `uv add anthropic` updates `uv.lock`; commit it.
8. **mypy --strict + ruff clean** — `tests/test_subagents.py` must pass both gates (matches Phase 1 D-08 / Phase 3-5 inheritance).

## Sources

### Primary (HIGH confidence)
- [Create custom subagents — Claude Code Docs](https://code.claude.com/docs/en/sub-agents) — full frontmatter spec (`name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`); subagent dispatch / auto-delegation / spawn lifecycle / scope priority (managed → CLI → project → user → plugin); `skills:` injection semantics; "subagents cannot spawn other subagents"; project scope `.claude/agents/` is version-controlled
- [Agent Skills Overview — Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) — three-level loading model (metadata always / instructions on trigger / scripts via bash); SKILL.md content vs. bundled scripts (scripts run via bash, never enter context); name + description field constraints
- [Token counting — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/token-counting) — `client.messages.count_tokens()` Python SDK signature; FREE (separate rate limit, no content billing); supports system prompt, tools, images, PDFs, extended thinking
- mortgage-ops project files (verified by direct read):
  - `/Users/cujo253/Documents/mortgage-ops/CLAUDE.md` — Math correctness, --help-first, skill portability, READ-ONLY user layer
  - `/Users/cujo253/Documents/mortgage-ops/DATA_CONTRACT.md` — `.claude/agents/**` is System Layer (auto-updatable, committed)
  - `/Users/cujo253/Documents/mortgage-ops/.planning/REQUIREMENTS.md` — SUBA-01..06 verbatim
  - `/Users/cujo253/Documents/mortgage-ops/.planning/ROADMAP.md` — Phase 11 SC-1..SC-5 verbatim
  - `/Users/cujo253/Documents/mortgage-ops/scripts/amortize.py:71-160` — JSON-in/JSON-out CLI shape; 6-key Pydantic envelope on stderr; lazy-import for fast --help
  - `/Users/cujo253/Documents/mortgage-ops/scripts/affordability.py:1-100` — same JSON-in/JSON-out + envelope pattern (the agents will invoke similar CLIs)
  - `/Users/cujo253/Documents/mortgage-ops/scripts/arm_simulate.py:1-100` — same pattern
  - `/Users/cujo253/Documents/mortgage-ops/pyproject.toml` — pyyaml 6.0.2, pytest 9.0, mypy --strict, ruff already configured
  - `/Users/cujo253/.claude/agents/data-scientist.md` — example agent file format reference

### Secondary (MEDIUM confidence)
- [Token Counting Explained: tiktoken, Anthropic, and Gemini (2025 Guide) — Propel Code](https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025) — tiktoken is OpenAI-specific; Anthropic count_tokens is the source of truth for Claude
- [Counting Claude Tokens Without a Tokenizer — Peta Muir / GoPenAI](https://blog.gopenai.com/counting-claude-tokens-without-a-tokenizer-e767f2b6e632) — tiktoken accuracy for Claude is "anecdotally not great"
- [Best AI Model for Coding Agents in 2026 — Augment Code](https://www.augmentcode.com/guides/ai-model-routing-guide) — Haiku for explore/dispatch, Sonnet for reasoning/ranking; 40-50% cost reduction with tiered routing

### Tertiary (LOW confidence — flagged)
- None — all model-selection / frontmatter / skill-resolution claims trace to primary Anthropic sources

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `anthropic` Python SDK's exact pinned version | Standard Stack — Installation | Low. Planner runs `pip index versions anthropic` at plan time and pins explicitly. SDK is on rapid release cadence; tight pin prevents surprise. |
| A2 | Phase 10 ships `.claude/skills/mortgage-ops/modes/stress.md` (Phase 11 expects to insert/assert the >5 routing rule there) | Architecture / SUBA-05 | Medium. If Phase 10 ships modes/stress.md WITHOUT a placeholder for subagent routing, Phase 11's first task is to add the dispatch rule. If Phase 10 ALREADY ships the rule (anticipating Phase 11), Phase 11's test just asserts it's present. The dependency is real and explicit in ROADMAP.md ("Depends on: Phase 10"). |
| A3 | Bundled `scripts/*.py` are physically relocated to `.claude/skills/mortgage-ops/scripts/` by Phase 10 (per CLAUDE.md decision #8 + Phase 3 D-17 docstrings) | Code examples — agent prompts reference `.claude/skills/mortgage-ops/scripts/amortize.py` | Medium. If Phase 10 doesn't relocate, agent prompts must reference `scripts/amortize.py` instead. The Phase 3 D-17 design contract explicitly says "Phase 10 physically relocates it; only the path moves". This is a strong upstream commitment, not a guess. |
| A4 | Haiku 4.5 is suitable for stress-test-agent's summarization workload | Architectural Responsibility Map / SUBA-03 | Low-medium. Industry consensus (Augment Code 2026 routing guide) places Haiku in the "fast summarization, table compression" tier. If at runtime the Haiku summary quality is poor, switching to Sonnet is a one-line frontmatter change (`model: sonnet`) — no test, prompt, or interface change required. |
| A5 | The transcript fixture for SUBA-06 (50-scenario summary) can be hand-authored to fit < 1k tokens | Code Example 5 / Pitfall #5 | Low. The whole point of the budget is forcing terse output. If a hand-written summary can't fit, the agent's prompt is asking the wrong question — that's the diagnostic, not a research gap. |
| A6 | `client.messages.count_tokens()` works with `messages=[{"role": "assistant", ...}]` for measuring agent OUTPUT (not just input) | Code Example 5 | Medium. The docs show `messages` as a structured input list; count_tokens names imply input-side counting. We're using it to count what an assistant message would tokenize to — a documented use case (the docs example uses `role: assistant` for thinking-block counting). Verify in Wave 0 with a 5-line probe before committing the test. |

## Open Questions

1. **Should refi-npv-agent get `Write` tool access for emitting a CSV summary?**
   - What we know: Sonnet runs at higher cost; users with many refi offers might want a CSV.
   - What's unclear: Whether the typical user wants a markdown table inline (no Write needed) or a CSV file (Write needed).
   - Recommendation: Ship without Write in v1 (inline table is sufficient for typical 2-5 offer comparisons). If user feedback in Phase 12 evals demands CSV, add Write in a future iteration. Keeps the v1 attack surface narrower.

2. **Where exactly does the `> 5 scenarios` routing rule live?**
   - What we know: ROADMAP.md SC-2 says "Stress mode in SKILL.md routes any sweep with > 5 scenarios to stress-test-agent (documented in modes/stress.md and tested by an eval prompt)".
   - What's unclear: Is the rule encoded in SKILL.md primary OR in modes/stress.md OR both?
   - Recommendation: SKILL.md mentions the rule briefly in the routing-decision table; modes/stress.md states it explicitly with the threshold and the exact agent name. SC-2 test asserts modes/stress.md (the canonical location).

3. **Does the agent need to handle the 5-scenario edge case (exactly 5)?**
   - What we know: ROADMAP says "> 5 scenarios" → subagent. So 5 scenarios stays on main thread.
   - What's unclear: Off-by-one risk if the prompt says "more than 5" vs ">= 5".
   - Recommendation: Pin the threshold as strictly `> 5` (so 6+ scenarios route). modes/stress.md uses literal "> 5" and the SC-2 test regex matches that. Document in modes/stress.md why: "5 or fewer scenarios produce a small enough output (~5 rows × ~100 tokens = ~500 tokens) to fit comfortably in main context; the dispatch overhead isn't worth it".

4. **Should the smoke test in SC-5 actually spawn the agent live, or just verify filesystem reachability?**
   - What we know: Anthropic agents are loaded at session start; CI doesn't have an interactive Claude Code session.
   - What's unclear: ROADMAP SC-5 says "verified by a smoke test that asserts the subagent has access to bundled scripts" — does "smoke test" require live spawn?
   - Recommendation: Filesystem-only smoke test is sufficient. The `skills:` frontmatter mechanism is documented and stable; if the agent exists, the named skill exists, and the bundled scripts exist on the documented path, the contract is satisfied. Live spawn would burn API credits and require interactive Claude Code in CI — neither is feasible. Document this trade-off in test docstrings.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All tests | ✓ | (already required by pyproject.toml) | — |
| pyyaml | SUBA-01 frontmatter parse | ✓ | 6.0.2+ already pinned | — |
| pytest 9.0+ | All tests | ✓ | already pinned | — |
| anthropic Python SDK | SUBA-06 token-budget test | ✗ | — | `uv add --group dev anthropic` (one-line); test skipif on missing key |
| ANTHROPIC_API_KEY env var | SUBA-06 live count_tokens call | ✗ at CI install time | — | Test skipif keeps local dev unblocked; CI must inject the key as a secret. count_tokens is FREE (no content billing) so the budget impact is negligible. |
| Claude Code runtime | Live agent invocation (NOT used in tests) | ✓ for dev / ✗ for CI | n/a | Tests are filesystem + count_tokens only — no live agent invocation needed |
| `.claude/skills/mortgage-ops/SKILL.md` | SUBA-05 smoke test | ✗ at Phase 11 start (Phase 10 ships it) | — | Phase 11 cannot complete tests until Phase 10 is done — this is the explicit dependency in ROADMAP.md |
| `.claude/skills/mortgage-ops/scripts/{amortize,refi_npv,stress_test}.py` | SUBA-05 smoke test | ✗ at Phase 11 start | — | Same as above — Phase 10 dependency |
| `.claude/skills/mortgage-ops/modes/stress.md` | SUBA-05 routing regex test | ✗ at Phase 11 start | — | Same as above |

**Missing dependencies with no fallback:**
- Phase 10 deliverables (SKILL.md, modes/stress.md, scripts in skill folder) — Phase 11 is BLOCKED until Phase 10 ships these. The ROADMAP "Depends on: Phase 10" directive captures this.
- `scripts/refi_npv.py` and `scripts/stress_test.py` don't exist yet (Phase 6 / Phase 8 deliverables). Phase 11's test for SUBA-05 only requires their existence at the skill-folder path — which Phases 6+8 ship at project root, then Phase 10 relocates. So the actual blocker chain is: Phase 6 ships refi_npv.py → Phase 8 ships stress_test.py → Phase 10 relocates everything → Phase 11 references the skill-folder paths. ROADMAP correctly orders all of this.

**Missing dependencies with fallback:**
- `anthropic` SDK + API key — fallback is `pytest.skipif` on the SC-3 test only; SC-1, SC-2, SC-4 (frontmatter), SC-5 (filesystem) all run without the SDK or key.

## Metadata

**Confidence breakdown:**
- Standard stack (frontmatter, model selection, skills mechanism): HIGH — verified directly against Anthropic docs current as of 2026-05-02
- Architecture (3 agents, project-scope, tool whitelist): HIGH — matches PROJECT.md decision #5 (locked) and Anthropic best-practice "design focused subagents"
- Pitfalls: HIGH — derived from explicit Anthropic spec quotes ("subagents loaded at session start", "scripts run via bash never enter context")
- Token-counting choice: HIGH — `anthropic.count_tokens` is the documented source of truth; tiktoken explicitly rejected
- Test-fixture strategy (recorded transcripts vs live LLM): MEDIUM-HIGH — pragmatic engineering call; trade-off documented; A6 flagged for Wave 0 verification

**Research date:** 2026-05-02
**Valid until:** 2026-06-02 (30 days — subagent spec is stable; Anthropic SDK count_tokens API has been stable for 6+ months. Re-verify if `anthropic` SDK ships a major-version bump or if Claude Code adds new frontmatter fields.)
