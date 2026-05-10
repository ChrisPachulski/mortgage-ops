# Subagent transcript fixtures

This directory holds the synthetic transcript fixtures that anchor the
Phase 11 SUBA-04 (SC-4) and SUBA-06 (SC-3) tests. Each fixture is
hand-authored to match the canonical agent-output shape from Plans
11-01..11-03 and is committed alongside the agent files it exercises so
that CI runs are deterministic, free of API charges, and reproducible
across machines.

Wave 0 (Plan 11-00) shipped this README plus a `.gitkeep`; Wave 5 (Plan
11-05) populates the directory with three `.transcript.jsonl` files and
extends this README with the live-capture recipe + synthetic-vs-live
rationale (D-02).

## Files

Each transcript is a one-line JSONL file: `{"role": "assistant",
"content": "<markdown>"}`. The format leaves room for future multi-turn
transcripts (one JSON object per line) without breaking the v1 loader.

| Fixture | Tested SC | Approx tokens (target) | What the agent returns |
|---------|-----------|-----------------------:|------------------------|
| `stress_50_scenarios.transcript.jsonl`   | SC-3 (SUBA-06: <1000 tokens) + the SUBA-04 amort/refi share the loader pattern | ~600 | `stress-test-agent` summarizing a 50-scenario rate-shock sweep — top 5 binned rows + worst-case / median / affordability-cliff narrative + `Computed by:` cite to `stress_test.py` |
| `refi_3_offers.transcript.jsonl`         | SC-4 (SUBA-04 refi: ranked-NPV-table) | ~250 | `refi-npv-agent` ranking three competing refi offers; markdown table sorted **descending by NPV** + 1-paragraph "Winner:" narrative + `Computed by:` cite to `refi_npv.py` (3 invocations) |
| `amort_single_loan.transcript.jsonl`     | SC-4 (SUBA-04 amort: markdown OR CSV path) | ~250 | `amortization-agent` returning a single fixed-rate amortization summary; first 2 rows + last row of the schedule + a `reports/NNN-amortization-YYYY-MM-DD.csv` path for the full 360-row schedule + `Computed by:` cite to `amortize.py` |

The "Approx tokens" column is informational. The actual SC-3 assertion
calls `anthropic.messages.count_tokens` at test time. The synthetic
content is hand-tuned to leave ~40% headroom under the 1000-token budget
so future content edits do not push the test onto the knife edge.

## Why synthetic, not live (D-02)

Live LLM dispatch in CI is non-deterministic, burns API credits, and
requires an interactive Claude Code session that headless runners do not
provide. Synthetic transcripts give us the four properties we need:

- **Determinism.** The same fixture always produces the same byte
  sequence, so token counts and shape assertions are stable across runs.
- **Zero recurring cost.** `anthropic.messages.count_tokens` is FREE per
  the Anthropic billing docs (separate rate limit, no content billing),
  and we never invoke the model itself in CI.
- **Airgap-safe.** Synthetic fixtures parse + assert without any
  network round-trip, so the SUBA-04 shape tests run anywhere; only the
  SUBA-06 token-budget test requires the network because
  `count_tokens` itself round-trips to Anthropic.
- **Contract-is-shape.** What we test is the agent-output **shape**
  (markdown table sorted descending by NPV; markdown OR CSV path;
  `Computed by:` citation; under 1000 tokens). The agent's exact
  numerical values do not matter for the shape contracts, so committing
  hand-authored content that mirrors the canonical shape from Plans
  11-01..11-03 is more useful than committing a one-shot live capture.

See `.planning/phases/11-subagents/11-RESEARCH.md` "Anti-Patterns to
Avoid" and "Pitfall 3" + "Pitfall 5" for the underlying rationale.

## Live-capture recipe (NOT run in CI)

For nightly eval regeneration (Phase 12 EVAL-03 / EVAL-04) or when an
agent prompt changes and the synthetic fixtures need to be drift-checked
against reality, a developer with `ANTHROPIC_API_KEY` (paid tier — `claude
-p` invokes the model, unlike `count_tokens`) can capture a live
transcript. The recipe writes to a `.NEW` file so the developer can diff
and promote intentionally; CI never runs this.

### Stress (50-scenario rate-shock sweep)

```bash
# 1. Restart Claude Code so any agent-file edits are picked up
#    (per 11-RESEARCH.md Pitfall 3).
# 2. Capture the live transcript via `claude -p` with the canonical prompt.
claude -p \
  --output-format json \
  --max-turns 6 \
  "Run a 50-scenario rate-shock stress sweep on the canonical \
\$400k @ 6.5%/30yr fixture (DTI cap 43%); summarize." \
  | jq -r '.result' \
  | jq -Rsc '{role:"assistant", content:.}' \
  > tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl.NEW

# 3. Diff against the committed synthetic fixture.
diff -u \
  tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl \
  tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl.NEW

# 4. If the diff is acceptable AND the new transcript still passes
#    SUBA-06 (uv run pytest tests/test_subagents.py::test_SUBA_06_stress_summary_under_1000_tokens),
#    promote:  mv ...jsonl.NEW ...jsonl
# 5. Otherwise, fix the agent prompt (NOT the budget).
```

### Refi (3-offer ranked NPV)

```bash
claude -p \
  --output-format json \
  --max-turns 6 \
  "Rank these three refi offers by NPV: Acme 5.875% \$3,200 cc; \
Bedrock 5.750% \$5,800 cc; ColdStream 6.000% \$2,400 cc. \
Current loan: \$400k @ 6.5%/30yr fixed, 24 months in." \
  | jq -r '.result' \
  | jq -Rsc '{role:"assistant", content:.}' \
  > tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl.NEW
```

### Amortization (single loan)

```bash
claude -p \
  --output-format json \
  --max-turns 4 \
  "Generate a 360-row amortization schedule for \$400,000 @ 6.50% / 30yr fixed." \
  | jq -r '.result' \
  | jq -Rsc '{role:"assistant", content:.}' \
  > tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl.NEW
```

The `--output-format json` + `jq -r '.result'` pipeline strips the
session/cost metadata that `claude -p` emits and keeps only the
assistant's final returned message; the second `jq -Rsc` wraps it as
`{"role":"assistant","content":<string>}` to match the loader contract.

## When to regenerate

Regenerate via the live-capture recipe in any of these cases:

- **Quarterly drift check.** Even with no prompt changes, the
  underlying model can drift; a quarterly regenerate-and-diff catches
  silent regressions before they bite.
- **After an agent prompt change.** Any edit to
  `.claude/agents/{amortization,refi-npv,stress-test}-agent.md` — Hard
  rules, Workflow, output format — should be followed by a regenerate
  + diff to confirm the synthetic fixture still mirrors live reality.
- **After a Phase 10 SKILL.md change.** The `skills: [mortgage-ops]`
  field injects SKILL.md content into the agent at spawn; SKILL.md
  edits can shift agent behavior even with no agent-file change.
- **When SUBA-06 fails.** If the synthetic stress fixture exceeds the
  1000-token budget, the diagnostic is "trim the synthetic" first;
  if the live capture also exceeds 1000, the agent prompt is the
  problem (per 11-RESEARCH.md Pitfall 5).

## Required `ANTHROPIC_API_KEY` scope

| Operation | Key required? | Cost | Notes |
|-----------|---------------|------|-------|
| `anthropic.messages.count_tokens` (SC-3 token-budget assertion in SUBA-06) | YES | FREE — separate rate limit, no content billing | Per `platform.claude.com/docs/en/build-with-claude/token-counting`. CI must inject the key as a secret; without it, SUBA-06 SKIPs cleanly via `pytest.mark.skipif`. |
| `claude -p ...` (live-capture recipe above) | YES | PAID — billed against your usage tier | NOT run in CI. Local-only. |
| Loading + asserting fixture shape (SUBA-04 refi/amort tests) | NO | n/a | Filesystem + `json.loads` only. Run anywhere, no key, no network. |

## What NOT to put here

- **No PII.** No values from `config/household.yml`, `config/profile.yml`,
  or `data/mortgage-ops.duckdb`. Synthetic inputs only, per the project
  Data Contract. Fixtures are committed and public-by-default.
- **No raw 50-scenario JSON dumps.** Per Pitfall 5 in 11-RESEARCH.md, the
  whole point of `stress-test-agent` is to compress sweep output into a
  short summary. If a transcript exceeds the 1000-token budget, fix the
  agent prompt — do not raise the budget.
- **No model-side reasoning traces.** Tool-use traces, scratchpad
  thinking, and Bash transcripts go in test logs, not in these fixtures.
- **No AI-attribution trailers.** Per the global commit rule, these
  fixtures and any commit that touches them must remain free of
  attribution markers (no `Co Authored By` style annotations, no
  Anthropic credits, no Claude credits in the transcript text).
