---
name: mortgage-ops
description: Personal-use mortgage analysis for the Pachulski household. Routes natural-language requests (evaluate, compare, refinance, affordability, stress test, amortization schedule, ARM simulation) to deterministic Python scripts that wrap numpy-financial. Every dollar figure is computed by Python and traced to a regulatory citation. Use when the user asks about mortgage payments, refinance NPV, affordability, DTI, ARM resets, points breakeven, amortization schedules, or any other home-loan math.
license: MIT (complete terms in LICENSE.txt)
compatibility: Requires Python 3.12+, numpy-financial, pydantic v2 (>=2.13), pyyaml. Designed for Claude Code (or any agent-skills-compatible client). Bundled scripts are deterministic CLIs; no network access required at runtime. DuckDB optional (Phase 9; needed only when scenarios are persisted).
---

# mortgage-ops — Personal Mortgage Command Center

This skill routes natural-language mortgage requests to deterministic Python
scripts. You determine the mode, collect inputs, invoke the script, narrate
the result. You DO NOT compute mortgage math inline — see "Math Discipline"
below for the full doctrine and the reasoning.

Bundled scripts live in `.claude/skills/mortgage-ops/scripts/`; references
load on demand from `.claude/skills/mortgage-ops/references/`; mode files
live in `.claude/skills/mortgage-ops/modes/`.

## Mode Routing

Determine the mode from the user's input:

| Input pattern | Mode | Script |
|---|---|---|
| Single loan + payment question (`"$400k @ 6.5%/30yr, what's my payment?"`) | `evaluate` | `scripts/amortize.py` + `lib.affordability` composition |
| Multiple offers, "compare", "rank by NPV" | `compare` | `scripts/refi_npv.py` per offer |
| "refi", "refinance", "should I refi" | `refinance` | `scripts/refi_npv.py` |
| "afford", "qualify", "max loan", "DTI" | `affordability` | `scripts/affordability.py` |
| "stress", "shock", "what if rates jump", "sweep" | `stress` | `scripts/stress_test.py` |
| "amortization schedule", "amortize", "extra principal" | `amortize` | `scripts/amortize.py` |
| "ARM", "5/1", "7/1", "10/1", "5/6", "SOFR ARM" | `arm` | `scripts/arm_simulate.py` |

(All 7 calc scripts are live at Phase 10 ship per Plan 10-01 SC-3 full
closure — SKILL.md routes every mode to its real script; no "ship in
Phase X" placeholder routing.)

Precedence (top wins; UI-SPEC §a):

1. Explicit sub-command           → `/mortgage-ops {mode}`
2. "refinance" / "refi" verb      → `refinance` (overrides arm/amortize/stress vocabulary)
3. "afford" / "borrow" verb       → `affordability` (overrides amortize)
4. "compare" / multi-offer        → `compare` (overrides evaluate)
5. "stress" / "sweep" + range     → `stress`
6. "ARM" / "X/Y" + no refi verb   → `arm`
7. "amortization" / "schedule"    → `amortize`
8. Single offer + judgment verb   → `evaluate`
9. Fallback                       → discovery menu (see bottom)

When precedence is tied, ask ONE clarifying question (not two):

> "I can read this two ways: (a) refinance analysis with an ARM target, or
> (b) standalone ARM modeling. Which did you mean?"

## Math Discipline (load-bearing — read carefully)

Every dollar figure, rate, breakeven, or schedule entry in your response MUST
come from a script invocation. You do NOT compute mortgage math inline.
Reasoning chains like "the payment is roughly X" or "let me estimate the
breakeven" are forbidden — even if the answer would be approximately right,
the user's house-buying decision deserves audit-traceable numbers.

The contract:

1. Determine the mode + collect inputs from the user (free-form English → JSON).
2. Write the JSON input to a tempfile (e.g. `/tmp/mortgage-ops-input-<uuid>.json`).
3. Invoke the relevant script:
   `python ${CLAUDE_SKILL_DIR}/scripts/<script>.py --input <tempfile>`
4. Read the script's stdout JSON. If exit code != 0, narrate the stderr
   6-key Pydantic envelope (loc + msg + input fields) to explain the
   validation failure (see UI-SPEC §c for the narration template).
5. Translate the JSON response into a human-readable report using
   `modes/_shared.md` report structure.

If you find yourself "estimating" or "approximating" a dollar figure, STOP.
Build a fuller JSON input and re-run the script. The Python engine is fast
(`--help` returns in < 100ms; full schedule for 360 months returns in < 50ms);
there is no performance reason to compute inline.

**This rule has zero exceptions.**

ALWAYS shell out to scripts/ for math; NEVER compute numbers inline.

## Bundled Scripts — black-box discipline

Use bundled scripts as black boxes. To accomplish a math task, identify the
script in `${CLAUDE_SKILL_DIR}/scripts/` that handles the workflow, then:

1. **Run `python ${CLAUDE_SKILL_DIR}/scripts/<script>.py --help` first** to
   see the JSON-input schema. The `--help` is fast (lazy-imports happen
   AFTER argparse).

2. Construct the JSON input matching the schema. Money fields MUST be JSON
   strings (e.g. `"400000.00"`) — Pydantic v2 strict mode rejects JSON
   floats at the boundary with a 6-key envelope on stderr.

3. Write the JSON to a tempfile (e.g. `/tmp/mortgage-ops-<uuid>.json`).

4. Invoke: `python ${CLAUDE_SKILL_DIR}/scripts/<script>.py --input <tempfile>`.

5. Parse the stdout JSON response. On non-zero exit, parse stderr — it
   carries a uniform 6-key Pydantic error envelope `[{"type", "loc", "msg",
   "input", "url", "ctx"}]` that you narrate to explain the validation
   failure (e.g., "your principal field was a float; rewrite as a JSON
   string"). Never dump raw JSON to the user.

**Always run scripts with `--help` first; do not read the source until you
try running the script first and find that a customized solution is
absolutely necessary.** These scripts can be very large and pollute your
context window. They exist to be called directly as black-box scripts
rather than ingested into your context window. (Doctrine lifted from
anthropics/skills/skills/webapp-testing/SKILL.md per RESEARCH §(b).)

## Loading Additional Context

When you decide on a mode, read `modes/_shared.md` first (always — D-10),
then read `modes/{mode}.md`.

When the user explicitly asks for a regulatory citation, formula derivation,
or methodology explanation AND the topic matches one of these references,
read the reference file ON DEMAND (D-09 progressive disclosure — do NOT
eagerly read references):

| User asks about... | Read reference |
|---|---|
| "how is the monthly payment computed", "PMT formula", "amortization math" | `references/amortization-formulas.md` |
| "Reg Z APR", "what's the difference between APR and APOR", "estimated APR methodology" | `references/apr-reg-z.md` |
| "what does 5/1 mean", "ARM cap structure", "how does the reset work" | `references/arm-mechanics.md` |
| "how do you decide if a refi is worth it", "what's the breakeven", "explain NPV" | `references/refi-npv.md` |
| "what's DTI", "how is affordability computed", "explain residual income" | `references/affordability-rules.md` |
| "what's the conforming limit", "what's a jumbo", "what's the FHA ceiling here" | `references/gse-limits.md` |
| "what are MIP rules", "when does PMI drop off", "FHA insurance" | `references/mip-pmi.md` |
| "is mortgage interest deductible", "tax implications", "Pub 936" | `references/tax-deductibility.md` |
| "why don't your numbers match Excel", "how do you round", "spreadsheet tradition" | `references/spreadsheet-conventions.md` |

If the user does NOT use one of these phrases, do NOT load any reference
file. The mode file + `_shared.md` + `_profile.md` together provide enough
context to route, call the script, and narrate. Loading references on every
invocation would blow the SKILL token budget (SKLL-01).

If the user asks two explanation questions in one prompt, load both
references but narrate sequentially. Do NOT pre-load all 9 references at
session start.

## Number Formatting

Display formatters live in `modes/_shared.md` § "Number Formatting" (Wave 3
ships them). The convention summary, per LOCKED DECISIONS D-NUM-01..06:

- **Money** (D-NUM-01): `$1,264.14` — 2 decimals, comma thousands, `$` prefix.
- **Rates** (D-NUM-02): `6.500%` — 3 decimals, trailing zeros preserved.
- **Ratios** (DTI / LTV / CLTV — D-NUM-03): `43.0%` — 1 decimal, `%` suffix.
  NOT raw `0.43`. NOT integer `43%`.
- **ARM bps** (D-NUM-04): `250 bps (2.50%)` — basis points with parenthesized
  percent, only in `arm` mode.
- **Internal Decimal precision** (D-NUM-05): unchanged — `lib/` rounds at
  end-of-period only. Display formatting is narration-layer only; it does
  NOT propagate back into stored Decimals.
- **Helper location** (D-NUM-06): `_shared.md` inline templates, NOT Python
  helpers. Scripts return raw Decimal-string JSON; you format per these
  conventions when narrating.

## Estimated APR Literal Text (SKLL-APR-1)

Every APR number this skill emits MUST be labeled "estimated APR" with both
words present and "estimated" preceding it. Forbidden phrasings:

- "APR of 6.872%" → must be "estimated APR of 6.872%"
- "your APR is 6.872%" → must be "your estimated APR is 6.872%"
- "6.872% APR" → must be "6.872% estimated APR" (modifier may follow if the
  noun is the last word)

When summarizing or paraphrasing earlier output, the rule still applies. If
the user types "what was the APR you said?", respond "the **estimated APR**
I computed was 6.872%" — never drop the qualifier even when echoing the
user's vocabulary.

`scripts/apr_reg_z.py` (Phase 7) is the actual APR solver. Both `evaluate`
and `compare` modes invoke it when an APR figure is requested; this rule
binds every emitted APR figure regardless of which mode produced it.

## Subagents (Phase 11)

Three subagents will land in Phase 11 to provide context isolation for
calc-heavy operations. Their files will be created at
`.claude/agents/{agent}.md`:

- `amortization-agent` (Haiku) — single-loan ARM amortization requests
- `refi-npv-agent` (Sonnet) — multi-step NPV reasoning, sweeps multiple offers
- `stress-test-agent` (Haiku) — parameter-grid sweeps; returns < 1k token summary

Phase 10 ships ONLY the forward-link. The skill does NOT delegate to these
agents at Phase 10. When Phase 11 lands, `modes/stress.md` (D-SUBA-FW-02)
will activate the dispatch automatically via an existence check on
`.claude/agents/stress-test-agent.md` — no SKILL.md edit required.

## Discovery Menu (no args)

When invoked with no arguments (or with an unrecognized sub-command that
doesn't match auto-detection), show:

```
mortgage-ops — Personal Mortgage Analysis

Available commands:
  /mortgage-ops                      → This menu
  /mortgage-ops {natural language}   → Auto-detect mode from your question
  /mortgage-ops evaluate             → Evaluate a single offer (judgment)
  /mortgage-ops compare              → Compare 2+ offers, rank them
  /mortgage-ops refinance            → Refi NPV analysis (current vs new loan)
  /mortgage-ops affordability        → How much house can we afford?
  /mortgage-ops stress               → Rate / income shock scenarios
  /mortgage-ops amortize             → Schedule + payment for a single loan
  /mortgage-ops arm                  → ARM modeling (5/1, 7/1, 10/1, 5/6)

Tips:
  - Just paste your question — auto-detect handles most cases.
  - Want an explanation of the math? Ask "explain the formula" or
    "how is APR computed" and I'll load the relevant reference.
  - First-time setup: copy config/household.example.yml →
    config/household.yml and edit, then config/profile.example.yml →
    config/profile.yml and edit.

Sources of truth:
  - Math: scripts/*.py (deterministic Python; never recomputed inline)
  - Personal data: config/household.yml + config/profile.yml (User Layer;
    never auto-edited by this skill — see DATA_CONTRACT.md)
  - Defaults: modes/_profile.md (your preferences; never auto-edited)
```

## First-Session Onboarding

If `${CLAUDE_SKILL_DIR}/modes/_profile.md` does not exist, instruct the user:

> I notice you don't have `modes/_profile.md` yet. To customize my behavior
> (default loan term, narrative tone, default state for affordability), copy
> the template:
>
>     cp .claude/skills/mortgage-ops/modes/_profile.example.md \
>        .claude/skills/mortgage-ops/modes/_profile.md
>
> Then edit it. I won't auto-create it — `modes/_profile.md` is User Layer
> per DATA_CONTRACT.md and the system never writes to your personal files.

DO NOT auto-copy the file (User Layer enforcement).

## Footer

For doctrine, math reasoning, or "why did you compute it that way?" questions,
load the relevant `references/*.md` per the table above.

For commit attribution: this repository's contributions are authored solely
by the repo owner. Do NOT add Co-Authored-By or any AI attribution to commits,
PRs, or code comments produced via this skill (per global CLAUDE.md rule).
