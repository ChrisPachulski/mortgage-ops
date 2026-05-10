# Mode: stress — Rate-shock / income-shock / ARM-path sweeps

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here when the user uses "stress" / "shock" / "sweep" / "what if"
+ scenario perturbation vocabulary. Examples (UI-SPEC §a rows 9-10):

- "What happens to our payment if rates jump to 9% at first reset?"
- "Run a stress sweep across rate paths from 5% to 10% in 0.25% steps"
- "What if my income drops 20%?"
- "Stress-test our affordability with a 2-percentage-point rate shock"

Do NOT route here if:

- "refi" / "refinance" verb present → `refinance` (sweep becomes inner
  loop; see AMBIGUITY RULE below)
- Single rate, single scenario → `evaluate` or `affordability`
- Schedule with extra-principal scenarios → `amortize`

### AMBIGUITY RULE (UI-SPEC §a Case 3)

If the prompt mentions BOTH "stress" AND "refi" / "refinance", route
to `refinance` mode. Stress is the *technique*; refi is the *intent*.
The refinance mode dispatches the parameter sweep as an inner loop
with the refi-NPV scenario at each grid point.

## What scripts to call

Single script:
`.claude/skills/mortgage-ops/scripts/stress_test.py` (Phase 8 SHIPPED;
relocated by Plan 10-01).

Run `--help` first. The script supports three modes via the `mode`
discriminator (D-01): `rate-shock` (parametrized rate grid),
`income-shock` (parametrized DTI reductions), `arm-reset`
(named ARM rate paths).

Example (rate-shock):

```json
{
  "mode": "rate-shock",
  "loan": {
    "principal": "400000.00",
    "annual_rate": "0.065000",
    "term_months": 360,
    "origination_date": "2026-05-10",
    "loan_type": "fixed"
  },
  "rates": ["0.06", "0.065", "0.07", "0.075", "0.08"],
  "baseline_label": "0.065"
}
```

Example (income-shock):

```json
{
  "mode": "income-shock",
  "base_request": { "...": "full AffordabilityRequest" },
  "reductions": ["0.05", "0.10", "0.20"],
  "dti_threshold": "0.43"
}
```

Invoke:

```bash
python .claude/skills/mortgage-ops/scripts/stress_test.py --input /tmp/stress.json
```

Output: JSON with top-of-payload scenario-summary table for SC-5
subagent consumption (< 100KB total, per Phase 8 STRS-04). Persist
via `insert-scenario`, then Save Report per `_shared.md`.

### PHASE 11 SUBAGENT FORWARD-LINK (D-SUBA-FW-02)

For sweeps with N > 5 scenarios, defer to
`.claude/agents/stress-test-agent.md` if it exists; otherwise run the
stress sweep inline.

User-visible behavior when the agent file exists (Phase 11 ships):
one-line dispatch announcement → subagent runs in isolated context
(intermediate token usage NOT in main chat) → subagent returns ≤ 1k
token summary (SUBA-06).

User-visible behavior when the agent file is absent (Phase 10 ship
state, Phase 11 not yet landed): run the stress sweep inline using
`.claude/skills/mortgage-ops/scripts/stress_test.py`. No dispatch
boilerplate appears.

For `scenario_count ≤ 5`, ALWAYS run inline regardless of whether the
agent file exists; the context cost of dispatch is not justified.

The `if it exists` check is the seam — Phase 11 lands by writing the
agent file, and `modes/stress.md` does NOT need a follow-up commit.

## What to narrate

Lead with the headline sensitivity. Use the canonical "answer +
provenance" template:

> Stress sweep complete *(computed by `stress_test.py` at 2026-05-10
> 14:38:22)*.
>
> **Summary** (5 rate scenarios; baseline 6.500%):
> - At 6.000%: monthly P&I = **$2,398.20**, total interest = **$463,352.00**
> - At 6.500% (baseline): monthly P&I = **$2,528.27**, total interest = **$510,177.94**
> - At 7.000%: monthly P&I = **$2,661.21**, total interest = **$558,036.00**
> - At 7.500%: monthly P&I = **$2,797.83**, total interest = **$607,219.00**
> - At 8.000%: monthly P&I = **$2,935.06**, total interest = **$656,621.00**
>
> **Sensitivity:** ~$1.27 increase in monthly P&I per basis-point
> increase in rate. Worst-case (8.000%): payment is **16.1%** higher
> than baseline.

Apply `_profile.md` `verbosity` knob (D-VOICE-02). For `concise`,
collapse to baseline + worst-case + sensitivity scalar. For `verbose`,
include every scenario row.

D-NUM-01 money, D-NUM-02 rates, D-NUM-03 ratios. Stress mode does NOT
use D-NUM-04 (bps) unless ARM-reset mode is active — it follows
percent-only narration for rate-shock and income-shock.

## Edge cases

- **No `rates` array (rate-shock):** ask the user for the grid; do
  NOT default to a hardcoded sweep.
- **No `dti_threshold` (income-shock):** REQUIRED per Phase 4 D-12;
  no module-level default. Ask the user (heuristic 0.43 is the
  ATR/QM cap per RESEARCH §3.2).
- **N > 5 scenarios:** see SUBAGENT FORWARD-LINK above. Existence
  check on `.claude/agents/stress-test-agent.md` decides
  inline-vs-dispatch.
- **Stress + refi:** see AMBIGUITY RULE above; route to `refinance`.
- **ARM-reset path with no `paths` array:** ask the user; do NOT
  invent rate paths.
- **Float-in-money error:** see `_shared.md` § Error Narration Template.

## RELATED REFERENCES

(Load on demand only.)

- `references/stress-tests.md` — "explain the sweep" / "what's the
  ATR/QM heuristic"
- `references/arm-mechanics.md` — "explain the cap structure" /
  "how does the reset work" (when ARM-reset mode is active)
- `references/affordability-rules.md` — "explain the DTI cap" /
  "ATR/QM"

## Subagent dispatch (SUBA-05)

If `scenario_count > 5`, dispatch to `stress-test-agent` (see `.claude/agents/stress-test-agent.md`).
The agent receives the sweep request, invokes `scripts/stress_test.py` once with the full grid,
and returns a ≤1,000-token summary to the main context (Phase 11 SC-2 + SC-3 contract).

Sweeps with 5 or fewer scenarios stay on the main thread — the dispatch overhead is not worth
it for outputs that fit in main context (≤500 tokens for typical 5-scenario sweeps).

The exact routing trigger Claude Code reads at dispatch time is the `description:` field of
`.claude/agents/stress-test-agent.md`, which begins: "Use proactively for stress sweeps with
>5 scenarios..." (Plan 11-03 LOCKED DECISION D-04). Do not duplicate the trigger phrasing
here — describe the routing decision in plain prose so this mode file stays a routing map,
not a copy of the agent file.
