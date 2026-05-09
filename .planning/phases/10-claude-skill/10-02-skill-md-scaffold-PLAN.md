---
phase: 10
plan: 02
type: execute
wave: 2
depends_on:
  - "10-00"
  - "10-01"
files_modified:
  - .claude/skills/mortgage-ops/SKILL.md
  - .claude/skills/mortgage-ops/LICENSE.txt
autonomous: true
requirements:
  - SKLL-01
  - SKLL-02
  - SKLL-03
  - SKLL-04
  - SKLL-09
  - SKLL-11
  - SKLL-12
tags:
  - phase-10
  - claude-skill
  - skill-md
  - frontmatter
  - skll-01
  - skll-02
  - skll-03
  - skll-04
  - skll-09
  - skll-11
  - skll-12
must_haves:
  truths:
    - ".claude/skills/mortgage-ops/SKILL.md exists with valid YAML frontmatter (parses via yaml.safe_load)"
    - "Frontmatter has all four SC-2 keys: name, description, license, compatibility (per LOCKED DECISION D-03)"
    - "name == 'mortgage-ops' (matches parent directory name per agentskills.io spec)"
    - "description ≤ 1024 chars; compatibility ≤ 500 chars; both per spec constraints"
    - ".claude/skills/mortgage-ops/LICENSE.txt exists with MIT terms (per LOCKED DECISION D-04 default)"
    - "SKILL.md ≤ 500 lines AND ≤ 4500 cl100k tokens (10% margin under Anthropic 5000 spec per D-02)"
    - "First 200 lines of SKILL.md contain '## Mode Routing' heading + all 7 mode names (per D-12 enforcement)"
    - "SKILL.md contains the ALWAYS-shell-out doctrine substring (SKLL-11 + UI-SPEC §g) and the 'run --help first' doctrine substring (SKLL-12 + webapp-testing exemplar)"
    - "SKILL.md contains the topic→reference progressive-disclosure table (SKLL-09 + D-09 + UI-SPEC §d)"
    - "SKILL.md contains a `## Subagents (Phase 11)` section naming all THREE Phase 11 subagent filenames (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) per LOCKED DECISION D-SUBA-FW-01 — forward-link only, no delegation instruction"
  artifacts:
    - path: ".claude/skills/mortgage-ops/SKILL.md"
      provides: "Skill-router entrypoint: frontmatter + routing skeleton + math-discipline doctrine + script invocation doctrine + progressive-disclosure rules + Subagents (Phase 11) forward-link section + discovery menu"
      min_lines: 250
      contains: "name: mortgage-ops"
    - path: ".claude/skills/mortgage-ops/LICENSE.txt"
      provides: "MIT license bundled inside skill folder (SKLL-04 + D-04 default)"
      contains: "MIT License"
  key_links:
    - from: ".claude/skills/mortgage-ops/SKILL.md frontmatter"
      to: "agentskills.io/specification §frontmatter"
      via: "name + description + license + compatibility fields per spec §a"
      pattern: "^---$"
    - from: "SKILL.md routing table"
      to: "Wave 3 modes/*.md files"
      via: "dispatch table lists 7 modes; Wave 3 ships their files"
      pattern: "## Mode Routing"
    - from: "SKILL.md progressive-disclosure section"
      to: "Wave 4 references/*.md files"
      via: "topic→reference table; Wave 4 ships the 9 reference files"
      pattern: "## (Loading|Progressive|References)"
---

<objective>
Ship the SKILL.md skeleton + LICENSE.txt that the Claude skill needs to be valid and routable. SKILL.md MUST satisfy the four hard structural requirements (≤ 500 lines, ≤ 4500 cl100k tokens, routing in first 200 lines, frontmatter has 4 SC-2 keys) PLUS embed the four load-bearing doctrines (math-discipline always-shell-out, run-help-first, progressive-disclosure topic→reference table, discovery menu).

Wave 2 ships the FILE; Wave 5 wires the CI assertions that prove the file complies. The split exists because the doctrines are author-time prose decisions (this wave) while the assertions are machine-checkable contracts (Wave 5). Mode files (Wave 3) and reference files (Wave 4) are referenced from SKILL.md but ship in their own waves.

Closes SKLL-01 (token + line budget — file is the artifact; Wave 5 asserts), SKLL-02 (routing in first 200 lines — file is the artifact; Wave 5 asserts), SKLL-03 (frontmatter — file is the artifact; Wave 5 asserts), SKLL-04 (LICENSE.txt — file is the artifact), SKLL-09 (progressive disclosure — doctrine present in SKILL.md), SKLL-11 (always-shell-out — doctrine present), SKLL-12 (run-help-first — doctrine present + scripts already have --help from Phases 3/4/5).

Purpose: The skill cannot exist without SKILL.md. Routing must be in the first 200 lines so the Anthropic compaction re-attach budget (5000 tokens) preserves it after summarization. The doctrines are load-bearing — every downstream prompt response depends on them being present in Claude's context.

Output: 2 files (SKILL.md + LICENSE.txt) inside `.claude/skills/mortgage-ops/`. ~250-450 lines for SKILL.md (target ~350 to leave headroom under both 500-line and 4500-token caps). ~21 lines for LICENSE.txt.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/10-claude-skill/10-PATTERNS.md
@.planning/phases/10-claude-skill/10-RESEARCH.md
@.planning/phases/10-claude-skill/10-UI-SPEC.md
@CLAUDE.md
@DATA_CONTRACT.md

<interfaces>
LOCKED DECISIONS in scope:
- D-02 = ≤ 4500 cl100k tokens (10% margin under 5000 Anthropic spec) — Wave 5 asserts
- D-03 = compatibility field FREE-FORM TEXT per agentskills.io spec — see RESEARCH §(a) for recommended ~296-char value
- D-04 = LICENSE.txt = MIT — see RESEARCH §(h) for full ~21-line text
- D-09 = Reference loading triggers documented INLINE in SKILL.md as topic→reference table (no separate loading.md)
- D-10 = Every mode loads modes/_shared.md FIRST, then its own mode file
- D-11 = Mode dispatch table + ambiguity rules live IN SKILL.md (no routing.md split)
- D-12 = SKLL-02 enforcement = `## Mode Routing` heading must appear before line 200

Frontmatter spec (RESEARCH §(a) — verbatim verification table):
| Field | Required | Constraint |
| name | YES | ≤ 64 chars; lowercase + numbers + hyphens; matches parent dir |
| description | YES | ≤ 1024 chars; describes what + when |
| license | NO (but SC-2 mandates) | free-form short string |
| compatibility | NO (but SC-2 mandates) | ≤ 500 chars; free-form text |

Recommended frontmatter (RESEARCH §(k) — copy verbatim):
```yaml
---
name: mortgage-ops
description: Personal-use mortgage analysis for the Pachulski household. Routes natural-language requests (evaluate, compare, refinance, affordability, stress test, amortization schedule, ARM simulation) to deterministic Python scripts that wrap numpy-financial. Every dollar figure is computed by Python and traced to a regulatory citation. Use when the user asks about mortgage payments, refinance NPV, affordability, DTI, ARM resets, points breakeven, amortization schedules, or any other home-loan math.
license: MIT (complete terms in LICENSE.txt)
compatibility: Requires Python 3.12+, numpy-financial, pydantic v2 (>=2.13), pyyaml. Designed for Claude Code (or any agent-skills-compatible client). Bundled scripts are deterministic CLIs; no network access required at runtime. DuckDB optional (Phase 9; needed only when scenarios are persisted).
---
```

Routing-skeleton lines 1-200 layout (RESEARCH §(l)):
- Lines 1-7: frontmatter
- Lines 8-20: title + math discipline header
- Lines 21-100: mode dispatch table + ambiguity rules
- Lines 101-160: math discipline doctrine (RESEARCH §(e) full text)
- Lines 161-200: script doctrine (run --help first; do not read source)
- Lines 201+: progressive-disclosure topic→reference table; discovery menu; appendix

UI-SPEC §a Routing UX — ambiguous-case disambiguation rules (paste verbatim):
> Precedence (top wins):
> 1. Explicit sub-command           → /mortgage-ops {mode}
> 2. "refinance" / "refi" verb      → refinance (overrides arm/amortize/stress vocabulary)
> 3. "afford" / "borrow" verb       → affordability (overrides amortize)
> 4. "compare" / multi-offer        → compare (overrides evaluate)
> 5. "stress" / "sweep" + range     → stress (dispatches to subagent if N>5)
> 6. "ARM" / "X/Y" + no refi verb   → arm
> 7. "amortization" / "schedule"    → amortize
> 8. Single offer + judgment verb   → evaluate
> 9. Fallback                       → discovery menu

UI-SPEC §g Output Narration Discipline — cardinal rule (paste verbatim):
> Every dollar figure Claude emits MUST come verbatim from a `scripts/` invocation.
> Claude never recomputes, never rounds, never restates "in round numbers". The
> script is the source of truth; Claude is the narrator.

UI-SPEC §e Estimated APR Literal-Text Rule (SKLL-APR-1; paste verbatim into SKILL.md doctrine section):
> **Rule SKLL-APR-1 (Estimated APR literal text).** Every APR number this skill
> emits MUST be labeled "estimated APR" with both words present and the modifier
> "estimated" preceding it. ... When summarizing or paraphrasing earlier output,
> the rule still applies.

Webapp-testing run-help-first doctrine (RESEARCH §(b) verbatim — fix typo when paraphrasing):
> Always run scripts with `--help` first to see usage. DO NOT read the source
> until you try running the script first and find that a customized solution
> is absolutely necessary. These scripts can be very large and thus pollute
> your context window. They exist to be called directly as black-box scripts
> rather than ingested into your context window.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create LICENSE.txt with MIT terms (D-04)</name>
  <files>.claude/skills/mortgage-ops/LICENSE.txt</files>
  <read_first>
    10-RESEARCH §(h) — full MIT text verbatim
  </read_first>
  <action>
Create `.claude/skills/mortgage-ops/LICENSE.txt` with the standard MIT License text. Per LOCKED DECISION D-04: MIT is the project default (pyproject.toml has no `[project] license` block; mortgage-ops is sibling-of-career-ops which uses permissive defaults).

Exact content (copy verbatim from 10-RESEARCH §(h)):

```
MIT License

Copyright (c) 2026 Pachulski Household

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

DO NOT add anything else (no preamble, no SPDX header — just the standard MIT block). The frontmatter `license:` field will reference "MIT (complete terms in LICENSE.txt)" so the cross-link is explicit.

DO NOT also create a project-root `LICENSE` file in this wave. The pyproject.toml `[project] license` add is OUT OF SCOPE for Phase 10 (would touch unrelated config); raise as a follow-up if needed.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/skills/mortgage-ops/LICENSE.txt &amp;&amp; grep -c 'MIT License' .claude/skills/mortgage-ops/LICENSE.txt &amp;&amp; grep -c 'Pachulski Household' .claude/skills/mortgage-ops/LICENSE.txt &amp;&amp; wc -l .claude/skills/mortgage-ops/LICENSE.txt</automated>
  </verify>
  <acceptance_criteria>
- File exists at `.claude/skills/mortgage-ops/LICENSE.txt`
- Contains "MIT License" on first line
- Contains "Copyright (c) 2026 Pachulski Household"
- Contains "WITHOUT WARRANTY OF ANY KIND"
- Line count between 18 and 25 (standard MIT is ~21 lines)
  </acceptance_criteria>
  <done>
    LICENSE.txt bundled inside skill folder (SKLL-04 closed at file level; Wave 5 asserts existence).
  </done>
</task>

<task type="auto">
  <name>Task 2: Create SKILL.md with frontmatter + routing skeleton (lines 1-200) + doctrine + progressive-disclosure section</name>
  <files>.claude/skills/mortgage-ops/SKILL.md</files>
  <read_first>
    10-RESEARCH §(a) frontmatter spec verbatim;
    10-RESEARCH §(k) recommended frontmatter copy-block verbatim;
    10-RESEARCH §(l) first-200-lines routing skeleton verbatim;
    10-RESEARCH §(e) "Never owns numbers" doctrine verbatim text;
    10-RESEARCH §(d) per-mode example inputs (paste 2-3 per mode into the dispatch table);
    10-UI-SPEC §a Routing UX precedence table verbatim;
    10-UI-SPEC §g Output Narration Discipline cardinal rule verbatim;
    10-UI-SPEC §e Estimated APR Literal-Text Rule verbatim;
    10-UI-SPEC §"Discovery Menu (no args)" verbatim copy block;
    career-ops/.claude/skills/career-ops/SKILL.md (if accessible) lines 70-95 — context-loading-by-mode pattern (D-10)
  </read_first>
  <action>
Create `.claude/skills/mortgage-ops/SKILL.md` with the structure below. Use Write tool. Target ~350 lines total (well under 500-line cap; well under 4500-token cap with margin).

STRUCTURE (lines are approximate; exact counts depend on prose density):

LINES 1-7: YAML frontmatter (copy verbatim from RESEARCH §(k); LOCKED DECISIONS D-03 + D-04 fix the values).

```yaml
---
name: mortgage-ops
description: Personal-use mortgage analysis for the Pachulski household. Routes natural-language requests (evaluate, compare, refinance, affordability, stress test, amortization schedule, ARM simulation) to deterministic Python scripts that wrap numpy-financial. Every dollar figure is computed by Python and traced to a regulatory citation. Use when the user asks about mortgage payments, refinance NPV, affordability, DTI, ARM resets, points breakeven, amortization schedules, or any other home-loan math.
license: MIT (complete terms in LICENSE.txt)
compatibility: Requires Python 3.12+, numpy-financial, pydantic v2 (>=2.13), pyyaml. Designed for Claude Code (or any agent-skills-compatible client). Bundled scripts are deterministic CLIs; no network access required at runtime. DuckDB optional (Phase 9; needed only when scenarios are persisted).
---
```

LINES 8-20: Title + math discipline header (intro). Mention that detailed math doctrine appears below.

```markdown
# mortgage-ops — Personal Mortgage Command Center

This skill routes natural-language mortgage requests to deterministic Python
scripts. You determine the mode, collect inputs, invoke the script, narrate
the result. You DO NOT compute mortgage math inline — see "Math Discipline"
below for the full doctrine and the reasoning.

Bundled scripts live in `.claude/skills/mortgage-ops/scripts/`; references
load on demand from `.claude/skills/mortgage-ops/references/`; mode files
live in `.claude/skills/mortgage-ops/modes/`.
```

LINES 21-100: `## Mode Routing` table + ambiguity rules. The heading `## Mode Routing` MUST appear in the first 200 lines (D-12 enforcement). Use the precedence table from UI-SPEC §a verbatim.

```markdown
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
5. "stress" / "sweep" + range     → `stress` (dispatches to subagent if N>5 — Phase 11 SUBA-05)
6. "ARM" / "X/Y" + no refi verb   → `arm`
7. "amortization" / "schedule"    → `amortize`
8. Single offer + judgment verb   → `evaluate`
9. Fallback                       → discovery menu (see bottom)

When precedence is tied, ask ONE clarifying question (not two):

> "I can read this two ways: (a) refinance analysis with an ARM target, or
> (b) standalone ARM modeling. Which did you mean?"
```

LINES 101-160: `## Math Discipline` doctrine block. Use RESEARCH §(e) verbatim text.

```markdown
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
```

(The trailing literal sentence "ALWAYS shell out to scripts/ for math; NEVER compute numbers inline." is the SUBSTRING that the SKLL-11 test will assert — make sure it appears verbatim.)

LINES 161-200: `## Bundled Scripts — black-box discipline` (run --help first; do not read source). Use RESEARCH §(b) webapp-testing-paraphrased text.

```markdown
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
```

(The phrase "run `--help` first; do not read source" appears verbatim above — that's the SKLL-12 substring the Wave 5 test will assert.)

LINES 201-250 (NOT in load-bearing-routing zone — fine to push past 200): `## Loading Additional Context` (D-09 + D-10).

```markdown
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
```

LINES 251-280: `## Estimated APR Literal Text` (UI-SPEC §e + Phase 7 forward-link).

```markdown
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

Phase 7 ships `scripts/apr_reg_z.py` (the actual APR solver); until then,
`evaluate` and `compare` modes do NOT report APR figures. When they do (post
Phase 7), this rule binds.
```

LINES 281-330: `## Discovery Menu (no args)` — copy verbatim from UI-SPEC.

```markdown
## Discovery Menu (no args)

When invoked with no arguments (or with an unrecognized sub-command that
doesn't match auto-detection), show:

\```
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
\```
```

(The triple-backtick lines must be `\`` escaped in your Write content — when the file is written to disk the backslash is removed; in the actual SKILL.md file, the menu must be enclosed in a real ``` code fence. If your Write tool strips the escape, use Edit to fix.)

LINES 331-end: `## First-Session Onboarding` + `## Footer` (short).

```markdown
## First-Session Onboarding

If `${CLAUDE_SKILL_DIR}/modes/_profile.md` does not exist, instruct the user:

> I notice you don't have `modes/_profile.md` yet. To customize my behavior
> (default loan term, narrative tone, default state for affordability), copy
> the template:
>
>     cp .claude/skills/mortgage-ops/modes/_profile.example.md \\
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
```

CRITICAL CONSTRAINTS:
- Total file ≤ 500 lines (target ~350; hard cap 500)
- Frontmatter MUST appear at lines 1-7 with the four SC-2 keys
- `## Mode Routing` heading MUST appear at line ≤ 200 (D-12 — target line ~21)
- The literal substring "ALWAYS shell out to scripts/ for math; NEVER compute numbers inline." MUST appear (SKLL-11 assertion in Wave 5)
- The literal substring "run `--help` first; do not read source" or near-equivalent ("`--help` first; do not read the source") MUST appear (SKLL-12 assertion)
- The 9 reference filenames (amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions) MUST appear in the topic→reference table (SKLL-09 assertion)
- All 7 mode names (evaluate, compare, refinance, affordability, stress, amortize, arm) MUST appear in the routing table (SKLL-02 indirect assertion)
- The literal heading `## Subagents (Phase 11)` MUST appear (D-SUBA-FW-01 assertion in Wave 5)
- All THREE subagent filenames (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) MUST appear under the Subagents section (D-SUBA-FW-01 assertion in Wave 5)
- File MUST parse cleanly: `python -c "import yaml; yaml.safe_load(open('.claude/skills/mortgage-ops/SKILL.md').read().split('---', 2)[1])"`
- File MUST be ≤ 4500 cl100k tokens (run `python -c "from tests._skill_helpers import count_tokens; print(count_tokens(open('.claude/skills/mortgage-ops/SKILL.md').read()))"` to verify)

DO NOT include FRED MCP `!` shell injection (Phase 12 LIVE-02 ships that).
DO NOT include runtime subagent dispatch logic (Phase 11 SUBA-05 wires actual delegation). DO include the `## Subagents (Phase 11)` forward-link section below per D-SUBA-FW-01 — naming the three agents is a forward-link only, NOT a delegation instruction.

LINES 271-300 (between Estimated APR and Discovery Menu): MANDATORY `## Subagents (Phase 11)` section per LOCKED DECISION D-SUBA-FW-01. One paragraph naming all three Phase 11 subagent filenames. The section ships in Phase 10 SKILL.md but the agent files themselves do NOT exist until Phase 11 — this section is a forward-link, not an instruction to delegate.

```markdown
## Subagents (Phase 11)

Three subagents will land in Phase 11 to provide context isolation for calc-heavy operations. Their files will be created at `.claude/agents/{agent}.md`:

- `amortization-agent` (Haiku) — single-loan ARM amortization requests
- `refi-npv-agent` (Sonnet) — multi-step NPV reasoning, sweeps multiple offers
- `stress-test-agent` (Haiku) — parameter-grid sweeps; returns < 1k token summary

Phase 10 ships ONLY the forward-link. The skill does NOT delegate to these agents at Phase 10. When Phase 11 lands, `modes/stress.md` (D-SUBA-FW-02) will activate the dispatch automatically via an existence check on `.claude/agents/stress-test-agent.md` — no SKILL.md edit required.
```

The section MUST contain ALL THREE filenames as bare tokens (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) so Wave 5 substring assertions can grep them. Token impact estimate per CONTEXT D-SUBA-FW-01: ~80-120 cl100k tokens; absorbed within the 4500-token ceiling.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/skills/mortgage-ops/SKILL.md &amp;&amp; python -c "import yaml; fm = yaml.safe_load(open('.claude/skills/mortgage-ops/SKILL.md').read().split('---', 2)[1]); assert fm['name'] == 'mortgage-ops'; assert all(k in fm for k in ('name', 'description', 'license', 'compatibility')); print('OK frontmatter')" &amp;&amp; python -c "from tests._skill_helpers import count_tokens; n = count_tokens(open('.claude/skills/mortgage-ops/SKILL.md').read()); print(f'tokens={n}'); assert n &lt;= 4500, n" &amp;&amp; test $(wc -l &lt; .claude/skills/mortgage-ops/SKILL.md) -le 500 &amp;&amp; head -200 .claude/skills/mortgage-ops/SKILL.md | grep -q '## Mode Routing'</automated>
  </verify>
  <acceptance_criteria>
- File exists at `.claude/skills/mortgage-ops/SKILL.md`
- File ≤ 500 lines (`wc -l` ≤ 500)
- File ≤ 4500 cl100k tokens (count_tokens helper)
- Frontmatter parses as YAML; contains keys: name, description, license, compatibility
- `name` value == "mortgage-ops"
- `description` length ≤ 1024 chars
- `compatibility` length ≤ 500 chars
- First 200 lines contain `## Mode Routing` heading
- First 200 lines contain all 7 mode names: evaluate, compare, refinance, affordability, stress, amortize, arm
- File contains substring "ALWAYS shell out to scripts/ for math; NEVER compute numbers inline." (SKLL-11)
- File contains substring "run `--help` first" or "`--help` first" (SKLL-12)
- File contains all 9 reference filenames in the topic→reference table
- File contains substring "estimated APR" (SKLL-APR-1 forward-link)
- File contains the discovery menu code fence
- File contains literal heading `## Subagents (Phase 11)` (D-SUBA-FW-01)
- File contains all THREE subagent filenames: `amortization-agent`, `refi-npv-agent`, `stress-test-agent` (D-SUBA-FW-01)
  </acceptance_criteria>
  <done>
    SKILL.md exists, parses, fits all budgets, contains all load-bearing doctrines and the routing skeleton.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SKILL.md frontmatter → agentskills.io spec compliance | Wrong field name or constraint violation breaks skill loading in Claude Code |
| SKILL.md routing-in-first-200-lines → Anthropic compaction re-attach | If routing slides past line 200 (and especially past token 5000), it disappears after summarization → skill silently breaks mid-conversation |
| Doctrine substrings → Wave 5 CI assertions | Wording drift between SKILL.md and the test substring breaks SKLL-11/12 enforcement (false negatives) |
| LICENSE.txt content → DATA_CONTRACT System Layer | LICENSE.txt is committed (System Layer); editing it post-ship requires plan-discuss (license changes are weighty) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-12 | Tampering (frontmatter spec drift) | SKILL.md lines 1-7 | mitigate | Task 2 acceptance asserts each field name + length constraint per RESEARCH §(a) verbatim spec |
| T-10-13 | Information Disclosure (routing lost in compaction) | line 200 boundary | mitigate | Task 2 acceptance asserts `## Mode Routing` heading appears in first 200 lines (D-12) |
| T-10-14 | Tampering (token budget overrun) | SKILL.md body | mitigate | Task 2 verify uses count_tokens helper (D-02) with 4500-cap; will fail loudly if prose grows past margin |
| T-10-15 | Tampering (doctrine substring drift) | SKLL-11 + SKLL-12 substrings | mitigate | Task 2 acceptance grep-asserts the literal substrings; Wave 5 wires the same assertion in CI so future SKILL.md edits cannot silently drop the doctrine |
| T-10-16 | Spoofing (license claim mismatch) | LICENSE.txt + frontmatter | accept | LICENSE.txt is the source of truth; frontmatter `license:` field is human-readable summary. Both reference MIT consistently |
| T-10-38 | Tampering (subagent forward-link drift) | `## Subagents (Phase 11)` section | mitigate | Task 2 acceptance grep-asserts heading + all 3 filenames; Wave 5 (10-05) wires the same assertion in CI; if SKILL.md edits silently drop a name, the test fails |
</threat_model>

<verification>
- LICENSE.txt exists, contains MIT terms, ≤ 25 lines
- SKILL.md exists, ≤ 500 lines, ≤ 4500 cl100k tokens
- Frontmatter parses; all 4 SC-2 keys present; constraints satisfied
- `## Mode Routing` heading + all 7 mode names appear in first 200 lines
- ALWAYS-shell-out doctrine literal substring present
- Run --help first doctrine literal substring present
- All 9 reference filenames listed in topic→reference table
- Discovery menu code fence present
- `## Subagents (Phase 11)` section present with all 3 agent filenames (D-SUBA-FW-01)
</verification>

<success_criteria>
- 2 files (SKILL.md + LICENSE.txt) created at the right paths
- SKILL.md fits both budgets (≤ 500 lines AND ≤ 4500 cl100k tokens) with margin
- All Wave 5 CI substring assertions will be satisfiable against this SKILL.md content
- Frontmatter is spec-compliant per agentskills.io
- LICENSE.txt is plain MIT (D-04 default)
- D-SUBA-FW-01 satisfied: SKILL.md ships forward-link section naming all 3 Phase 11 subagents
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-02-SUMMARY.md` documenting:
- SKILL.md final line count + cl100k token count (both vs caps)
- LICENSE.txt line count
- Substring-presence audit (all 4 doctrines + 9 references + 7 modes accounted for)
- Any deviation from RESEARCH §(k) recommended frontmatter, with rationale
- Confirmation that Wave 5 CI assertions can satisfy against this content
</output>
</content>
</invoke>