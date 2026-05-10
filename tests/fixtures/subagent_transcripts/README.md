# Subagent Transcript Fixtures

This directory holds recorded subagent transcripts that anchor the Phase 11
test suite (SUBA-04 / SUBA-06). The fixtures are committed alongside the
agent files they exercise so that CI runs are deterministic, free of API
charges, and reproducible across machines.

Wave 0 (Plan 11-00) ships only this README plus a `.gitkeep`; the `.md`
transcripts themselves land in Wave 5 (Plan 11-05) once the agent files
(Waves 1-3) and the routing rule (Wave 4) are in place.

## Why recorded, not live?

Live LLM dispatch in CI is non-deterministic, burns API credits, and
requires an interactive Claude Code session that headless runners do not
provide. Recorded transcripts give us:

- **Determinism.** The same input always produces the same byte sequence,
  so token counts and golden assertions are stable across runs.
- **Zero recurring cost.** `anthropic.messages.count_tokens` is FREE per
  the Anthropic billing docs, and we never invoke the model at CI time.
- **Regenerability.** A developer with `ANTHROPIC_API_KEY` can rebuild
  any transcript by following the ritual below.

See `.planning/phases/11-subagents/11-RESEARCH.md` "Anti-Patterns to
Avoid" and "Pitfall 3" for why live invocation is out of scope for
automated tests.

## Files

Wave 5 will populate this directory with three transcripts. Each
transcript is the agent's RETURNED message — not the agent's internal
working text — for one canonical prompt.

- `stress_50_scenario_summary.md` — `stress-test-agent` returning a
  50-scenario rate-shock summary. SUBA-06 oracle. Hard budget: < 1000
  tokens per `anthropic.messages.count_tokens` (model `claude-haiku-4-5`).
- `refi_3_offer_ranked.md` — `refi-npv-agent` ranking three competing
  refi offers by NPV. Backs the SUBA-04 refi assertion (markdown table
  sorted descending by NPV).
- `amortize_single_loan.md` — `amortization-agent` returning a single
  fixed-rate amortization summary. Backs the SUBA-04 amortize assertion
  (markdown table OR CSV path).

Until Wave 5 lands, the transcripts do not exist; SUBA-04 and SUBA-06
remain `xfail` in `tests/test_subagents.py`.

## How to regenerate a transcript

Follow these five steps in order. Steps 1-2 require an interactive Claude
Code session; step 4 runs entirely offline.

1. **Confirm Phase 10 has shipped.** The skill folder
   `.claude/skills/mortgage-ops/`, `modes/stress.md`, and the relocated
   `.claude/skills/mortgage-ops/scripts/{amortize,refi_npv,stress_test}.py`
   must all exist on disk. Per Pitfall 3 in 11-RESEARCH.md, restart your
   Claude Code session after editing any agent file under
   `.claude/agents/` so the new definition is picked up.
2. **Dispatch the agent in an interactive session.** Use the canonical
   prompt for the transcript you are regenerating (see "Files" above for
   the intent of each). Set `ANTHROPIC_API_KEY` in your environment so
   the agent can shell out as expected.
3. **Copy ONLY the agent's returned message.** Do not capture the
   subagent's internal scratch notes, tool-call traces, or stdout from
   shelled-out scripts; only the final markdown the agent returned to
   the main thread belongs in the `.md`. Keep formatting verbatim.
4. **Verify locally.** Run
   `uv run pytest tests/test_subagents.py -v` and confirm SUBA-04 and
   SUBA-06 still pass. SUBA-06 requires `ANTHROPIC_API_KEY` because
   `count_tokens` makes a network round-trip (it is FREE for content but
   still requires the key).
5. **Commit the transcript.** Add the regenerated `.md` alongside any
   agent-file edits in the same commit so reviewers can see the prompt
   change and its anchored output together.

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
