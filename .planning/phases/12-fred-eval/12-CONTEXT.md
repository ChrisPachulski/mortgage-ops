# Phase 12: fred-eval - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning (replan to incorporate D-12-* decisions; existing 9 plans were drafted before these locks)

<domain>
## Phase Boundary

Phase 12 wires live FRED data (MORTGAGE30US, MORTGAGE15US) into SKILL.md and ships the eval harness that regression-tests skill quality across all 7 modes (evaluate, compare, refinance, affordability, stress, amortize, arm). Closes v1.0.

**In scope:** FRED HTTP wrapper at `.claude/skills/mortgage-ops/scripts/fred_cli.py`, 7-day cache at `data/cache/fred_*.json`, SKILL.md prose-only injection of cached rates, eval runner at `evals/runner.py`, ≥21 prompt set with paired oracles in `evals/expected/`, route_match + numeric_match metrics with explicit `numeric_skip` bucket, hallucination detector tightened to stdout-only sources, optional MCP server registration documented in `references/fred-context.md`, CI integration.

**Out of scope:** Filling oracles for the 9 TBD prompts (refinance/stress/arm — deferred until those phases ship richer fixtures), v2 eval features (LLM-as-judge scoring, multi-model comparison), MCP server as the canonical injection path (ratified as optional secondary).

</domain>

<decisions>
## Implementation Decisions

### SC-4 numeric_match gate behavior (BLOCKER — was making 95% gate trivially-passable)

- **D-12-SC4-01:** TBD-Phase-N prompts (those with `expected_numbers: []`) go into a `numeric_skip` third bucket — neither pass nor fail. The 95% gate computes on `numeric_pass / (numeric_pass + numeric_fail)`. Eval runner reports must show `numeric_pass=N`, `numeric_fail=N`, `numeric_skip=N` explicitly so future-you sees the real shape of the eval set.
  - Plan 12-04 `evals/metrics.score_numeric_match` must return one of three states (`pass | fail | skip`) per prompt. The aggregator in `evals/runner.py` filters skip out of the gate denominator.
  - Plan 12-05 prompt frontmatter must include a non-empty `expected_numbers:` list OR explicit `numeric_status: skip` (with a `defer_until_phase: N` pointer to the phase that will fill it).
  - Tests must assert: a TBD prompt is reported as `skipped` not `passed`; the gate at 100% pass on 13 anchored prompts + 9 skipped passes (`13/(13+0) = 100% ≥ 95%`); a single fail among the 13 anchored fails the gate (`12/(12+1) = 92.3% < 95%`). NOTE: 13 anchored = 12 mode-coverage anchored + 1 live-rate-injection-01 per D-12-SC1-01 below.

### LIVE-01 scope (CONCERN — upstream MCP has no `fred-cli` binary)

- **D-12-LIVE01-01:** HTTP wrapper at `scripts/fred_cli.py` is the canonical path. MCP server registration documented in `references/fred-context.md` as an optional secondary path for users who want session-scoped MCP-tool dispatch.
  - Plan 12-08 references doc must include the MCP server registration recipe (`.claude/settings.json` MCP entry + auth env var) and the rationale for HTTP-as-canonical (determinism for evals, no MCP system dependency).
  - REQUIREMENTS.md LIVE-01 wording updates to: `FRED API integration via HTTP wrapper (canonical) with optional fred-mcp-server registration documented as secondary path.`

### LIVE-02 SKILL.md FRED injection pattern (CONCERN — Pattern A vs B ambiguity)

- **D-12-LIVE02-01:** Pattern A — prose-only injection with cache-file references. SKILL.md contains a static `## Live Mortgage Rates` section pointing at `data/cache/fred_MORTGAGE30US.json` and `data/cache/fred_MORTGAGE15US.json`. Skill loads the rates via Read tool when borrower asks current-rate questions. NO literal `!`...`` shell-injection syntax (Anthropic-documented but Claude Code support uncertain per 12-RESEARCH.md Open Question 1).
  - Canonical SKILL.md section copy (verbatim — Plan 12-03 must ship this exact text):
    ```markdown
    ## Live Mortgage Rates

    Latest weekly rates (refreshed via `scripts/fred_cli.py` on weekly cron;
    cached 7 days max in `data/cache/fred_MORTGAGE30US.json`):

    - 30-yr fixed (MORTGAGE30US): see cache file `data/cache/fred_MORTGAGE30US.json`
      field `value`
    - 15-yr fixed (MORTGAGE15US): see cache file `data/cache/fred_MORTGAGE15US.json`

    Skill loads these via Read tool when borrower asks 'what's the current rate?'
    ```
  - REQUIREMENTS.md LIVE-02 wording updates to: `SKILL.md cites cache-file paths for MORTGAGE30US and MORTGAGE15US in a "Live Mortgage Rates" section; cache refreshed by scripts/fred_cli.py with 7-day TTL.`
  - Tests verify: SKILL.md contains the heading `## Live Mortgage Rates`, contains both `MORTGAGE30US` and `MORTGAGE15US` strings, contains `data/cache/fred_*.json` path references, contains `scripts/fred_cli.py` reference. NO grep for `` !` `` syntax.
  - Cache miss behavior: if cache file is absent or stale, skill must invoke `scripts/fred_cli.py get MORTGAGE30US --latest` itself (documented in the SKILL.md routing section so Claude knows the recovery path).

### SC-1 fresh-session injection verification (CONCERN — only structural grep test)

- **D-12-SC1-01:** Add a live `evals/prompts/live-rate-injection-01.md` eval prompt to Wave 5 (Plan 12-05). Prompt: borrower asks "what's the current 30-year fixed rate?" Expected behavior: skill reads `data/cache/fred_MORTGAGE30US.json`, cites the value, route_match credits the Read invocation. numeric_match credits the cited rate against the cache value.
  - Plan 12-05 prompt count goes from 21 to **22** (21 mode-coverage prompts + 1 live-rate-injection prompt). The 22nd is anchored (real cache fixture), so the SC-4 denominator becomes 13 anchored / 9 skipped.
  - Plan 12-06 oracle file `evals/expected/live-rate-injection-01.json` ships with a fixture cache value (e.g., `MORTGAGE30US: 6.50%` valid as of `effective: 2026-05-10`). Test eval pins to the fixture, not live FRED — determinism per D-02 patterns from Phase 11.
  - SC-1 closure: end-to-end via this eval prompt. Structural grep test stays as a complementary check.

### SC-3 hallucination detector strictness (CONCERN — accepts cmd-args/stdin as sourced)

- **D-12-SC3-01:** Tighten `evals/metrics.detect_hallucinations` to credit numbers as "sourced" only if they appear in the **stdout** of a `scripts/*.py` invocation. Numbers from cmd args, stdin, or prose are NOT credited. Add a complementary `route_match` cross-check: if `numeric_output` is non-empty AND no script invocation occurred in the trace, the prompt fails BOTH `numeric_match` (Pitfall #2: hallucinated number) AND `route_match` (Pitfall #2b: parroted number with no script).
  - Plan 12-04 `evals/metrics.py` must return `numeric_match: fail` with reason `unsourced_number` for stdin-only or prose-only number provenance.
  - Tests verify: a transcript that cites `$1,264.14` from prose with no script invocation fails both gates; a transcript that cites the same number after `scripts/amortize.py ...` stdout passes both gates; a transcript that echoes a user-supplied number from the prompt body without invoking any script fails both gates.
  - Trade-off: false-positive risk if a prompt legitimately echoes a static number (e.g., "the IRS Pub 936 cap is $750,000"). Mitigation: `expected_numbers` entries can carry a `provenance: static` tag that exempts them from the stdout requirement.

### Claude's Discretion (planner/researcher decide during planning)

- Eval-runner output format (JSON, JUnit XML, or both) — researcher should investigate what Claude Code's CI integration expects.
- Cache-file lockfile pattern — Plan 12-02 should mirror `orchestration/lockfile.mjs` (Phase 9 pattern) but exact API signature is open.
- MCP server auth env var name — `FRED_API_KEY` is conventional; researcher should confirm against `stefanoamorelli/fred-mcp-server` README.
- CI gate strictness on `numeric_skip` count — should `numeric_skip > N` warn or block? Defer to Plan 12-07 wiring.

</decisions>

<specifics>
## Specific Ideas

- **Determinism via fixture caches** — pattern locked in Phase 11 (synthetic transcript fixtures for SUBA-04/06). Phase 12 mirrors it: `data/cache/fred_*.json` fixtures shipped under `tests/fixtures/fred/` are used in CI; live FRED calls only run on weekly cron / manual refresh, not in CI.
- **22-prompt eval set** — 21 mode-coverage (3 per mode × 7 modes) + 1 live-rate-injection. 13 anchored + 9 TBD-with-skip-pointer.
- **Citation discipline carries forward** — every eval prompt's expected output must carry `Computed by: scripts/<name>.py <args>` line, mirroring the convention shipped in Phase 11 stress-test-agent and refi-npv-agent.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12 planning artifacts (current draft — needs replanning per D-12-* locks)
- `.planning/phases/12-fred-eval/12-RESEARCH.md` — Open Questions Q(a)..Q(f); §Critical Finding (upstream MCP has no `fred-cli` binary); pattern catalog
- `.planning/phases/12-fred-eval/12-PATTERNS.md` — Issue 1 (MCP server entry-point mismatch); reusable patterns from Phases 9-11
- `.planning/phases/12-fred-eval/12-PLAN-CHECK.md` — 4 BLOCKERS + 7 CONCERNS that this CONTEXT.md addresses
- `.planning/phases/12-fred-eval/12-00..08-PLAN.md` — existing draft plans (REPLAN required to incorporate D-12-* decisions before execution)

### Project-wide constraints
- `.planning/PROJECT.md` — Core value (math correctness, LLM never owns numbers); evolution rules
- `.planning/REQUIREMENTS.md` LIVE-01..04 + EVAL-01..04 — wording updates needed for LIVE-01 + LIVE-02 per D-12-LIVE01-01 + D-12-LIVE02-01
- `.planning/ROADMAP.md` §Phase 12 SC-1..SC-5 — gate semantics now refined per D-12-SC4-01 + D-12-SC1-01 + D-12-SC3-01
- `CLAUDE.md` §Money discipline + §Calc engine separation + §Skill portability + §Reference data discipline — all apply
- `DATA_CONTRACT.md` — User Layer is READ-ONLY; eval runner writes to `evals/runs/` (System Layer) only

### Patterns to inherit from prior phases
- `.planning/phases/09-persistence/09-*-SUMMARY.md` — `withLock()` pattern for cache writes
- `.planning/phases/10-claude-skill/10-*-SUMMARY.md` — SKILL.md ≤500 lines / ≤5k tokens; progressive disclosure via `references/`; mode-routing layout
- `.planning/phases/11-subagents/11-*-SUMMARY.md` — synthetic-fixture-only-in-CI policy (D-02); citation discipline (`Computed by:`); test surface flips (xfail → pass) pattern

### External docs
- FRED API: https://fred.stlouisfed.org/docs/api/fred/series_observations.html (HTTP endpoint shape, auth, rate limits)
- `stefanoamorelli/fred-mcp-server`: https://github.com/stefanoamorelli/fred-mcp-server (MCP server registration recipe — secondary path per D-12-LIVE01-01)
- Anthropic Claude Code skills docs: https://docs.claude.com/en/docs/build-with-claude/claude-code/skills (SKILL.md token budget; mode routing; subagent dispatch)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`orchestration/lockfile.mjs` + `withLock()`** (Phase 9): cache writes to `data/cache/fred_*.json` should reuse this lock pattern to prevent racy refreshes.
- **`tests/fixtures/subagent_transcripts/` README + regen recipe** (Phase 11 Wave 5): exact pattern to mirror for `tests/fixtures/fred/` — synthetic-only in CI, live-capture recipe documented for nightly regen.
- **`scripts/_cli_helpers.py`** (Phase 10): standard CLI argparse boilerplate — `fred_cli.py` should use it.
- **`lib/rules/_loader.py:_check_staleness`** (Phase 1+): 12-month staleness warning pattern — adapt for cache 7-day TTL warning.
- **`evals/` skeleton** (currently doesn't exist) — Phase 12 creates the directory; runner imports `lib/` modules for ground-truth recomputation.

### Established Patterns
- **Citation discipline**: every numeric output cites `Computed by: scripts/<name>.py <args>`. Eval runner extracts this from transcripts to verify provenance.
- **Skill ≤5k token budget**: SKILL.md after Phase 10 is at ~3.4k tokens (1.6k headroom). The new `## Live Mortgage Rates` section adds ~80 tokens — well within budget.
- **Test xfail flip discipline**: Wave 0 ships test stubs as xfail; later waves flip them to passing. Phase 12 inherits this.
- **Subagent dispatch (Phase 11)**: Phase 12 evals should invoke `stress-test-agent` for ≥6-scenario stress prompts (Plan 12-05 prompt design must respect SUBA-05 routing).

### Integration Points
- **SKILL.md (Phase 10)** — modify only the new `## Live Mortgage Rates` section + the routing block reference. Do not touch other Phase 10 sections.
- **`.claude/skills/mortgage-ops/scripts/`** — `fred_cli.py` lands here, alongside the 7 calc CLIs from Phase 10.
- **`data/cache/`** — new dir under Data Layer (gitignored); `data/cache/fred_*.json` lifecycle managed by `fred_cli.py`.
- **CI** (`.github/workflows/test.yml` or equivalent) — Plan 12-07 wires the eval gate. Investigate current CI shape before planning.

</code_context>

<deferred>
## Deferred Ideas

- **Filling the 9 TBD oracles** — Phase 6 (refinance NPV) ships 3 refi oracles; Phase 8 (stress) ships 3 stress oracles; Phase 5 (ARM) — already shipped, but ARM oracle prompts may need a follow-up pass to align with Phase 12 prompt format. Track as `Phase 13.0+` follow-ups; the `defer_until_phase: N` pointer in each TBD prompt's frontmatter makes this discoverable via `/gsd-audit-uat`.
- **MCP server canonical path (v2)** — if Anthropic's MCP system matures and `fred-mcp-server` ships a `fred-cli` binary, v2 can flip the canonical path. CONTEXT.md ratifies HTTP-as-canonical for v1.
- **LLM-as-judge eval scoring** — current plan uses route_match + numeric_match (deterministic). LLM-judged answer-quality scoring is a v2 idea.
- **Multi-model eval comparison** — running the same prompts against Opus/Sonnet/Haiku and comparing route/numeric match. v2 idea.

</deferred>

---

*Phase: 12-fred-eval*
