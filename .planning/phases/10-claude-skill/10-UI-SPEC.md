---
phase: 10
slug: claude-skill
status: draft
shadcn_initialized: false
preset: not applicable
created: 2026-05-02
surface: claude-skill (text/JSON only, no graphical UI)
---

# Phase 10 — UI Design Contract (Claude-Skill Surface)

> The "UI" here is text-only. There is no DOM, no shadcn, no spacing scale, no
> color palette. The user-facing surfaces are: (1) `SKILL.md` routing copy,
> (2) `modes/*.md` mode files Claude loads on demand, (3) JSON output schemas
> the user sees rendered in chat, (4) the 6-key Pydantic error envelope as
> Claude *narrates* it (not as raw JSON), and (5) `references/*.md` loaded
> only when the user asks for explanation. This document is the visual /
> interaction contract for those surfaces.
>
> Standard graphical-UI sections (spacing, color, typography, registry safety)
> are marked **N/A — text-only surface** with rationale rather than removed,
> so the gsd-ui-checker rubric can still score the contract.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (no graphical UI; Claude-skill text surface) |
| Preset | not applicable |
| Component library | not applicable |
| Icon library | not applicable (Unicode only — see "Output Narration Discipline") |
| Font | client-rendered (Claude.ai / CLI / IDE — author cannot control) |

**Why no shadcn gate:** the skill emits markdown + JSON to a chat transcript.
There is no React/Next.js/Vite project to initialize against. The shadcn gate
in the gsd-ui-researcher rubric does not apply.

---

## Spacing Scale

**N/A — text-only surface.** Markdown spacing is determined by the renderer
(Claude.ai web app, terminal, IDE). The contract instead pins **structural
density**:

| Surface | Density Rule |
|---------|--------------|
| `SKILL.md` | ≤ 500 lines, ≤ 5k tokens, routing table in first 200 lines (SKLL-01, SKLL-02) |
| `modes/*.md` | ≤ 200 lines per mode (allows ~7 modes + `_shared.md` + `_profile.md` to load together when needed without blowing the context budget) |
| `references/*.md` | No upper bound — loaded on demand only, one reference at a time (SKLL-09 progressive disclosure) |
| Mode narration to user | ≤ 25 lines for happy path; ≤ 8 lines for error narration (see "Error UX") |
| Subagent return summary | ≤ 1k tokens (SUBA-06) |

---

## Typography

**N/A — text-only surface.** The contract instead pins **markdown
conventions** every mode file MUST follow:

| Role | Markdown Convention | Usage |
|------|---------------------|-------|
| Mode title | `# Mode: {name} — {one-line purpose}` | First line of every `modes/*.md` |
| Section heading | `## When to invoke` / `## What scripts to call` / `## What to narrate` | Mandatory three-section spine |
| Inline value | `` `value` `` (backticks) | Filenames, JSON keys, dollar figures Claude is *quoting* |
| Provenance | `*(computed by `script.py` at 2026-05-02 14:32:11)*` | Italic + backtick — see "Output Narration Discipline" |
| User-facing money | `$2,528.27` (USD literal, two decimals, comma thousands) | Always — not `2528.27` or `2,528` |
| User-facing rate | `6.500% APR` or `6.500% note rate` | Always 3-decimal % with explicit qualifier |
| Estimated APR | `**estimated APR** of 6.872%` | Bold "estimated APR" literal — see SKLL-APR-1 below |

---

## Color

**N/A — text-only surface.** No color tokens. The functional analog of
"60/30/10 color discipline" is **information hierarchy in narration**:

| Role | Convention | Usage |
|------|------------|-------|
| Dominant (the answer) | Plain prose, first sentence | The number the user asked for, with its unit |
| Secondary (provenance) | Italic parenthetical | Which script computed it, when |
| Accent (caveats) | `> blockquote` | Disclaimers, "estimated APR" qualifier, regulatory notes |
| Destructive (errors) | Plain prose, no emoji, no all-caps | "I couldn't process that input because…" — see "Error UX" |

**Forbidden:** emoji indicators (no ✅ ❌ ⚠️), ANSI color codes, ASCII
art status banners. The skill is rendered in arbitrary clients (Claude.ai
web, Claude Code TUI, third-party MCP hosts) — many strip or mangle these.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Discovery menu (no args) | See "Discovery Menu" block below |
| Primary CTA per mode | None — modes are routed by user intent, not by buttons. The "CTA equivalent" is the `## When to invoke` section in each mode file. |
| Empty state — no household.yml | "I don't have your household profile yet. Create `config/household.yml` from the example at `config/household.example.yml`, then re-run this command. I won't auto-create it because `config/household.yml` is User-Layer (per `DATA_CONTRACT.md`)." |
| Empty state — no profile.yml | "I don't have your `config/profile.yml` yet. Copy `config/profile.example.yml` to `config/profile.yml` and edit your defaults (state, credit-score bucket, narrative style). I won't auto-create it." |
| Empty state — no known-loans.yml | "No loans cataloged yet. Add an entry to `data/known-loans.yml` with `principal`, `annual_rate`, `term_months`, and `origination_date`, then re-run." |
| Error state | "I couldn't process that input because **{msg}**. The field `{loc}` expected {explanation}. The value I received was `{input}`." (see "Error UX" below for full template) |
| Destructive confirmation | None in v1. The skill is read-only with respect to User Layer (DATA_CONTRACT). The only writes are System Layer reports under `reports/{###}-{slug}-{YYYY-MM-DD}.md`, which do not require confirmation per career-ops pattern. |
| Subagent dispatch | "Running 50-scenario stress sweep — this may take a moment…" (see SKLL-UX-8) |
| "Estimated APR" disclaimer | "This is an **estimated APR** — it is not a regulatory APR disclosure. Reg Z requires lender disclosure on the Loan Estimate; my number is computed by `apr.py` from your inputs and may differ from the LE." (load with every APR result) |

---

## Routing UX (a) — User Prompt → Mode

The skill supports 7 modes plus a discovery default. Every example below MUST
work; the routing table in `SKILL.md` will be tested by the eval harness
(EVAL-03).

### Worked Examples (10)

| # | User prompt | Mode | Why |
|---|-------------|------|-----|
| 1 | "Should I lock the 6.5% rate Wells offered me on $400k?" | `evaluate` | "Should I" + offer details + single loan = single-offer evaluation |
| 2 | "Is this 6.5% / 30yr offer any good?" | `evaluate` | Single offer + qualitative judgment |
| 3 | "Compare these three: 6.5% / 30yr vs 6.0% / 30yr with 1.5 points vs 5.875% / 15yr" | `compare` | Multiple offer specs + ranking verb |
| 4 | "Which is better, the BoA 30-year or the Chase 15-year?" | `compare` | Comparison + 2+ named offers |
| 5 | "Should I refi my current 7.125% / 28-years-remaining loan into a 6.0% / 30yr?" | `refinance` | "refi" / "refinance" verb + current-loan + new-loan pair |
| 6 | "Worth refinancing if I can get 5.875%?" | `refinance` | "refinanc-" verb anywhere in prompt |
| 7 | "How much house can we afford on $250k household income at today's rates?" | `affordability` | "afford" verb + household income |
| 8 | "What's the most we can borrow with $100k down and a 43% DTI cap?" | `affordability` | "borrow" + DTI / down-payment vocabulary, reverse mode |
| 9 | "What happens to our payment if rates jump to 9% at first reset?" | `stress` | "what if" / "what happens if" + scenario perturbation |
| 10 | "Run a stress sweep across rate paths from 5% to 10% in 0.25% steps" | `stress` | "stress" or "sweep" verb + parameter range (auto-dispatches to `stress-test-agent` per SUBA-05) |
| 11 | "Show me the amortization schedule for $400k @ 6.5% / 30yr" | `amortize` | "amortization" / "schedule" + loan terms |
| 12 | "What's the P&I on $400k at 6.5% over 30 years?" | `amortize` | Pure calc question, no judgment requested |
| 13 | "Model a 7/1 ARM at 6.0% intro with 5/2/5 caps" | `arm` | "ARM" or "X/Y" hybrid spec |
| 14 | "If SOFR climbs to 4.5% by year 8, what's my reset payment on this 5/1?" | `arm` | ARM vocabulary + index path |

### Ambiguous Cases & Disambiguation Strategy

**Ambiguous case 1:** *"What if I refinance into a 7/1 ARM?"*

Routing collision: `refinance` (refi verb) AND `arm` (ARM vocabulary).

**Strategy:** `refinance` wins. The user's primary question is the refi
decision; the ARM is the *target product*. The `refinance` mode internally
calls `lib/arm.py` for the new loan's payment schedule, then computes NPV.
Document this in `modes/refinance.md` under `## When to invoke`:

> If the prompt mentions both "refi" and "ARM", route to `refinance` and pass
> `loan_type: "arm"` + `arm_terms: {...}` to the new-loan side of the NPV
> request. Do NOT route to `arm` standalone — that mode is for ARM modeling
> against an existing or hypothetical loan, not against a refi-decision pair.

**Ambiguous case 2:** *"Can we afford a $600k house and what would the
payment be?"*

Routing collision: `affordability` (afford verb) AND `amortize` (payment
question).

**Strategy:** `affordability` wins, and the `affordability.py` response
already includes the PITI breakdown (principal, interest, taxes, insurance,
PMI, HOA) — see `lib/affordability.py::AffordabilityResponse`. So the user
gets *both* pieces of information from one mode invocation. Document in
`modes/affordability.md`:

> If the user asks "can I afford X *and* what's the payment", do NOT make
> two script calls. `affordability.py` already returns `monthly_pi`,
> `monthly_taxes`, `monthly_insurance`, `monthly_pmi`, `monthly_hoa` in its
> response. Narrate from one call.

**Ambiguous case 3 (forward-link to Phase 11):** *"Stress-test this refi
across 50 rate paths."*

Routing collision: `stress` AND `refinance`.

**Strategy:** `refinance` is the *intent*; `stress` is the *technique*.
Route to `refinance` mode, which then dispatches the parameter sweep to
`stress-test-agent` (Phase 11) with the refi-NPV scenario as the inner loop.
The user sees one narrative ("Running 50-scenario stress sweep on your refi
decision…") and one summary report.

### Disambiguation Mechanics

`SKILL.md` Section "Mode Routing" includes a precedence table:

```
Precedence (top wins):
1. Explicit sub-command           → /mortgage-ops {mode}
2. "refinance" / "refi" verb      → refinance (overrides arm/amortize/stress vocabulary)
3. "afford" / "borrow" verb       → affordability (overrides amortize)
4. "compare" / multi-offer        → compare (overrides evaluate)
5. "stress" / "sweep" + range     → stress (dispatches to subagent if N>5)
6. "ARM" / "X/Y" + no refi verb   → arm
7. "amortization" / "schedule"    → amortize
8. Single offer + judgment verb   → evaluate
9. Fallback                       → discovery menu
```

When precedence is tied, Claude asks ONE clarifying question (not two):

> "I can read this two ways: (a) refinance analysis with an ARM target, or
> (b) standalone ARM modeling. Which did you mean?"

---

## Mode File Format Spec (b)

Every `modes/{mode}.md` mirrors a single skeleton. The skeleton has exactly
four required sections in this order:

1. `## When to invoke` — routing predicate, what user prompts trigger this mode
2. `## What scripts to call` — the script(s), input JSON shape, output JSON shape
3. `## What to narrate` — output narration discipline (template + provenance)
4. `## Edge cases` — empty state, error states, ambiguous routing

### Sample Skeleton: `modes/amortize.md`

```markdown
# Mode: amortize — Generate an amortization schedule

## When to invoke

Route here when the user asks for:
- A monthly payment ("what's the P&I on $X at Y% over Z years?")
- A full amortization schedule ("show me the schedule for…")
- A specific period's interest/principal split ("how much interest in year 5?")
- Extra-principal modeling ("what if I pay an extra $500/mo?")

Do NOT route here if:
- The user uses "refi" / "refinance" verb → `refinance`
- The user asks "can I afford" → `affordability`
- The user mentions ARM caps / X/Y notation → `arm`

## What scripts to call

Single script: `scripts/amortize.py` (relocated to
`.claude/skills/mortgage-ops/scripts/amortize.py` per SKLL-10).

**Read `--help` first.** Do not read the source unless customization is needed
(Anthropic webapp-testing doctrine; CLAUDE.md "Bundled scripts" convention).

Build a JSON input file matching the documented shape:

```json
{
  "loan": {
    "principal": "400000.00",
    "annual_rate": "0.065000",
    "term_months": 360,
    "origination_date": "2026-05-01",
    "loan_type": "fixed"
  },
  "frequency": "monthly",
  "extra_principal": []
}
```

**Money discipline:** All money/rate fields MUST be JSON strings (Pydantic v2
strict mode rejects JSON floats at the boundary — see `_shared.md` "Money
Discipline" and Phase 3 D-19). If you write `"principal": 400000.00`
(JSON float) the script will reject with a 6-key envelope on stderr.

Invocation:

```bash
python .claude/skills/mortgage-ops/scripts/amortize.py --input /tmp/amortize-req.json
```

Output: JSON `Schedule` on stdout, exit 0. Validation error: 6-key envelope
on stderr, exit 2.

## What to narrate

Use the canonical "answer + provenance" template:

> Your monthly P&I is **$2,528.27** *(computed by `amortize.py` at
> 2026-05-02 14:32:11)*.
>
> Total interest over the 360-month term: **$510,177.94**. The first month's
> interest is $2,166.67; the first month's principal is $361.60.
>
> *Reading the full schedule? It's saved to `reports/{###}-amortize-2026-05-02.md`.*

Do NOT recompute any number. Every dollar figure must come from the JSON
output verbatim.

## Edge cases

- **No principal in prompt:** ask "What's the loan principal?" — do not guess.
- **No rate in prompt:** check if FRED MCP is available (Phase 12); if yes,
  offer "Use today's MORTGAGE30US (X.XXX%)?". If no, ask the user.
- **Float-in-money error:** see `_shared.md` "Error UX" (the 6-key envelope
  narration template). Show the user the field name and the corrected JSON
  shape; offer to retry.
```

All other modes (`compare`, `refinance`, `affordability`, `stress`,
`amortize`, `arm`, plus the `evaluate` umbrella) MUST follow this exact
section spine. Deviations break the gsd-ui-checker dimension 1 (copywriting
consistency).

---

## Error UX (c) — 6-Key Pydantic Envelope Narration

Scripts emit a uniform 6-key envelope on stderr (Phase 3 WR-02 closure shape;
inherited by Phase 4 D-13 and Phase 5 D-07):

```json
[{
  "type": "decimal_type",
  "loc": ["loan", "principal"],
  "msg": "Input should be a valid decimal — JSON string required because the project's money-discipline contract forbids JSON floats in money/rate fields",
  "input": "400000.0",
  "url": "https://errors.pydantic.dev/2.13/v/decimal_type",
  "ctx": {"class": "DecimalType"}
}]
```

**Cardinal rule:** Claude NEVER dumps this JSON to the user. Claude reads
the four fields it needs (`loc`, `msg`, `input`, optionally `type`) and
narrates a one-paragraph explanation in the user's vocabulary.

### Narration Template (`modes/_shared.md` — every mode inherits)

```
I couldn't process that input because **{summarized_msg}**.

The field `{loc_dotted}` expected {expectation_in_plain_english}.
The value I received was `{input}`.

{one_line_fix_suggestion}
```

Where:
- `{summarized_msg}` = first sentence of `msg` (cut at the em-dash if present)
- `{loc_dotted}` = `loc` array joined with `.` (e.g., `["loan", "principal"]`
  → `loan.principal`)
- `{expectation_in_plain_english}` = derived from `type` (table below)
- `{input}` = the offending value, in code formatting
- `{one_line_fix_suggestion}` = derived from `type` (table below)

### Worked Example 1: Float-in-money

**Envelope (stderr):**
```json
[{"type": "decimal_type", "loc": ["loan", "principal"],
  "msg": "Input should be a valid decimal — JSON string required …",
  "input": "400000.0", "url": "…", "ctx": {"class": "DecimalType"}}]
```

**Claude narrates:**

> I couldn't process that input because **the principal was sent as a JSON
> number (`400000.0`) instead of a JSON string**.
>
> The field `loan.principal` expected a quoted decimal like `"400000.00"`.
> The value I received was `400000.0` (unquoted), which Python's float type
> can't represent precisely enough for money math.
>
> Want me to retry with `"principal": "400000.00"`?

### Worked Example 2: Missing required field

**Envelope (stderr):**
```json
[{"type": "missing", "loc": ["loan", "term_months"],
  "msg": "Field required",
  "input": {"principal": "400000.00", "annual_rate": "0.065000"},
  "url": "…", "ctx": {}}]
```

**Claude narrates:**

> I couldn't process that input because **the loan term was missing**.
>
> The field `loan.term_months` is required — it should be an integer count
> of months (e.g., `360` for a 30-year loan or `180` for a 15-year).
>
> What term did you have in mind? I'll add `"term_months": <value>` and
> retry.

### Worked Example 3: Invalid loan_type enum

**Envelope (stderr):**
```json
[{"type": "enum", "loc": ["loan", "loan_type"],
  "msg": "Input should be 'fixed', 'arm', 'fha', 'va', 'usda', 'conventional', or 'jumbo'",
  "input": "FHA-streamline",
  "url": "…", "ctx": {"expected": "'fixed', 'arm', 'fha', …"}}]
```

**Claude narrates:**

> I couldn't process that input because **`FHA-streamline` isn't one of the
> recognized loan types**.
>
> The field `loan.loan_type` expected one of: `fixed`, `arm`, `fha`, `va`,
> `usda`, `conventional`, `jumbo`. (FHA Streamline is a refinance *program*,
> not a loan type — the underlying loan is `fha`.)
>
> Want me to retry with `"loan_type": "fha"`?

### What Claude does NOT do

- Does NOT print the raw JSON envelope.
- Does NOT print the `url` field (it's a Pydantic docs link, not a user
  resource).
- Does NOT print the `ctx` object (internal Pydantic metadata).
- Does NOT print Python tracebacks if any leak through (file the leak as a
  bug — every error path must hit the 6-key envelope per WR-02).
- Does NOT retry automatically — always asks the user before re-invoking.

### File-not-found / OSError surfaces

These are NOT 6-key envelopes (predate the contract; see `amortize.py`
lines 113-124). They emit `{"error": "input file not found: /path/to/file"}`.
Claude narrates:

> I couldn't read the input file `/path/to/file` — it doesn't exist or I
> don't have permission. Did the temp file get cleaned up between calls?

---

## Progressive Disclosure UX (d) — Reference Loading

`references/*.md` files are loaded ONLY when the user asks for an
explanation. The default narration cites the *script* that produced a number;
the *formula* behind that script lives in `references/` and is loaded on
demand.

### Trigger Phrases → Reference File

| User says (any of) | Load `references/{file}.md` |
|--------------------|------------------------------|
| "explain the formula", "how is P&I calculated", "show the math" | `amortization-formulas.md` |
| "what's APR", "how do you compute APR", "why does APR differ from rate" | `apr-reg-z.md` |
| "explain the cap structure", "what does 5/1 mean", "how does the reset work" | `arm-mechanics.md` |
| "how do you decide if a refi is worth it", "what's the breakeven", "explain NPV" | `refi-npv.md` |
| "what's DTI", "how is affordability computed", "explain residual income" | `affordability-rules.md` |
| "what's the conforming limit", "what's a jumbo", "what's the FHA ceiling here" | `gse-limits.md` |
| "what are MIP rules", "when does PMI drop off", "FHA insurance" | `mip-pmi.md` |
| "is mortgage interest deductible", "tax implications", "Pub 936" | `tax-deductibility.md` |
| "what's the 8x table convention", "how do you round", "spreadsheet tradition" | `spreadsheet-conventions.md` |

### Default Behavior

If the user does NOT use one of these phrases, do NOT load any
`references/*.md`. The mode file + `_shared.md` + `_profile.md` together
provide enough context to route, call the script, and narrate. Loading
references on every invocation would blow the SKILL token budget (SKLL-01,
≤ 5k tokens).

### One Reference at a Time

If a user asks two explanation questions in one prompt, load both files but
narrate sequentially. Do NOT pre-load all 9 references at session start.

### Forward-Link to Phase 11

Subagents (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`)
inherit the skill via `skills: [mortgage-ops]` frontmatter (SUBA-04). The
references are part of the inherited skill — subagents can load them too,
but the same trigger-phrase discipline applies.

---

## "Estimated APR" Literal-Text Rule (e) — SKLL-APR-1

Phase 7 SC-4 (Estimated APR) requires that every APR figure surfaced by the
skill is labeled "estimated APR" — never just "APR". This is a regulatory
hygiene rule (we are not a Reg-Z-disclosing lender; calling our number "the
APR" is misleading).

**SKILL.md user-facing instruction (paste into `## Output Discipline`
section, top-level rule):**

> **Rule SKLL-APR-1 (Estimated APR literal text).** Every APR number this
> skill emits MUST be labeled "estimated APR" with both words present and
> the modifier "estimated" preceding it. Forbidden phrasings:
> - "APR of 6.872%" → must be "estimated APR of 6.872%"
> - "your APR is 6.872%" → must be "your estimated APR is 6.872%"
> - "6.872% APR" → must be "6.872% estimated APR" (modifier may follow if
>   the noun is the last word)
> - "APR (estimated): 6.872%" → must be "estimated APR: 6.872%"
>
> When summarizing or paraphrasing earlier output, the rule still applies.
> If the user types "what was the APR you said?", respond "the **estimated
> APR** I computed was 6.872%" — never drop the qualifier even when echoing
> the user's vocabulary.
>
> When loading `references/apr-reg-z.md`, the reference itself uses the
> qualifier consistently and explains *why*: "this is not a Reg Z
> disclosure; lenders compute and disclose the official APR on the Loan
> Estimate. Our number is an *estimate* derived from the inputs you
> provided, computed by `apr.py` via Newton-Raphson per Reg Z Appendix J."

**Eval harness check (Phase 12 EVAL-04):** the eval prompts include APR
queries; the runner asserts every response containing the substring "APR"
also contains "estimated APR" (case-insensitive, with at most one whitespace
character between words). If the rule is violated, the eval fails.

---

## household.yml + profile.yml Interaction (f)

### Read vs Write Matrix

| Operation | `config/household.yml` | `config/profile.yml` | `modes/_profile.md` |
|-----------|-------------------------|----------------------|---------------------|
| Read by skill | YES — when mode requires household data (`affordability`, `evaluate`, `stress` if income-dependent) | YES — every invocation, for default state / credit bucket / narrative style | YES — every invocation, for user-specific overrides |
| Write by skill | **NEVER** (DATA_CONTRACT User Layer) | **NEVER** (DATA_CONTRACT User Layer) | **NEVER** (DATA_CONTRACT User Layer) |
| Auto-create if missing | **NEVER** | **NEVER** | **NEVER** |
| Auto-edit on user request | **NEVER** — instruct the user to edit by hand | **NEVER** — instruct the user | **NEVER** — instruct the user |
| Read source if missing | Surface friendly error (below) | Surface friendly error | Skip silently (file is optional; use `_shared.md` defaults) |

**Enforcement:** the pre-commit hook (`scripts/hooks/block-user-layer.py`)
will refuse any commit that stages a User Layer path. The skill MUST NOT
attempt a write — even a read-after-write idiom would trigger the runtime
guard. See `DATA_CONTRACT.md` Layer Cross-References.

### Friendly Error: household.yml missing

When a mode that needs household data discovers `config/household.yml` does
not exist, Claude says:

> I don't have your household profile yet. To run `affordability` (or
> `evaluate` for a household-dependent decision), I need:
>
> - Joint applicant credit scores
> - Household income (gross monthly)
> - Monthly debts (auto, student loans, credit cards, alimony)
> - Location (state FIPS + county FIPS — e.g., King County WA = `53` / `033`)
>
> Create `config/household.yml` from the example skeleton at
> `config/household.example.yml` and re-run this command. I won't
> auto-create the file — `config/household.yml` is User Layer per
> `DATA_CONTRACT.md`, and the system never writes to your personal data.
>
> Once it exists, this command will work without further prompting.

### Friendly Error: profile.yml missing

> I don't have your `config/profile.yml` yet. Copy
> `config/profile.example.yml` to `config/profile.yml` and edit the
> defaults you care about (default state for affordability lookups, default
> credit-score bucket, narrative style). Then re-run.

### Friendly Error: _profile.md missing

(Optional file.) Claude does NOT surface an error. It silently falls back
to `_shared.md` defaults (career-ops pattern — see
`career-ops/CLAUDE.md` "If `modes/_profile.md` is missing, copy from
`modes/_profile.template.md` silently"). For mortgage-ops we do NOT
auto-copy, because `_profile.md` is User Layer per DATA_CONTRACT — we just
skip it.

---

## Output Narration Discipline (g)

### The Cardinal Rule

> Every dollar figure Claude emits MUST come verbatim from a `scripts/`
> invocation. Claude never recomputes, never rounds, never restates "in
> round numbers". The script is the source of truth; Claude is the narrator.

### The Canonical "Answer + Provenance" Template

```
Your monthly P&I is **$2,528.27** *(computed by `amortize.py` at 2026-05-02 14:32:11)*.
```

Components:
1. **Answer in the first clause** — the number the user asked for, with its
   unit (`$` for money, `%` for rates, `months` for terms).
2. **Bold the figure** — `**$2,528.27**` so it survives skim-reading.
3. **Provenance in italic parenthetical** — `*(computed by `script.py` at
   ISO-8601 timestamp)*`. The timestamp comes from the script's stdout JSON
   if available, else from the moment of invocation.
4. **No restatement** — do NOT add "which is roughly $2,500/month". The
   user can round in their head; Claude must not introduce a second number.

### Multi-Number Responses

When narrating a Schedule (full amortization output), Claude:

1. Pulls the headline figures (`monthly_pi`, `total_interest`,
   `total_payments`) from the JSON.
2. Quotes them verbatim with provenance.
3. Saves the full schedule to `reports/{###}-amortize-{YYYY-MM-DD}.md`
   (SKLL-13) so the user can read every row.
4. Does NOT inline 360 rows in chat.

Example:

> Your monthly P&I is **$2,528.27** *(computed by `amortize.py` at
> 2026-05-02 14:32:11)*.
>
> Over the 360-month term you'll pay **$910,177.94** total ($510,177.94 of
> that is interest). The first payment is 85.7% interest / 14.3% principal;
> the crossover (where principal exceeds interest) happens at month 195.
>
> Full schedule saved to `reports/047-amortize-2026-05-02.md`.

### Forbidden Patterns

| Don't | Do |
|-------|-----|
| "Roughly $2,500/month" | "**$2,528.27**" |
| "About $510k in interest" | "**$510,177.94** in interest" |
| "Let me calculate that — 400000 × 0.065 / 12 = $2,166.67" (Claude doing arithmetic) | "**$2,166.67** *(computed by `amortize.py`…)*" |
| "Your APR is approximately 6.87%" | "Your **estimated APR** is **6.872%** *(computed by `apr.py`…)*" |
| Echoing the user's input math without verification | Re-running the script with the user's inputs, then narrating the script output |

### Why This Matters

PROJECT.md "Core Value": *Math correctness first. Every dollar figure that
exits this system must be traceable to a tested, deterministic Python
function. The LLM frontend is a router and narrator — it never owns numbers.*

If Claude inlines arithmetic, the contract breaks: the eval harness EVAL-04
("every reported number traces back to a `scripts/` invocation") will fail,
and the user can't trust any number the system emits.

---

## Subagent Handoff UX (h) — Forward-link to Phase 11

When `stress` mode receives a sweep request with N > 5 scenarios, it
dispatches to `stress-test-agent` (Phase 11 SUBA-03 / SUBA-05).

### What the User Sees

**Step 1 — Dispatch announcement (one line, no progress bar):**

> Running 50-scenario stress sweep (rate paths from 5.000% to 10.000% in
> 0.250% steps) — this may take a moment…

**Step 2 — Subagent runs in isolated context** (user sees nothing during
this; the subagent's intermediate token usage does NOT appear in the main
chat).

**Step 3 — Return summary (≤ 1k tokens per SUBA-06):**

> Stress sweep complete *(computed by `stress-test-agent` invoking
> `scripts/stress.py` 50 times at 2026-05-02 14:38:22)*.
>
> **Summary:**
> - At 5.000%: monthly P&I = **$2,147.29**, total interest = **$373,025**
> - At 6.500% (today): monthly P&I = **$2,528.27**, total interest = **$510,178**
> - At 8.000%: monthly P&I = **$2,935.06**, total interest = **$656,621**
> - At 9.500%: monthly P&I = **$3,364.20**, total interest = **$810,914**
> - At 10.000%: monthly P&I = **$3,510.29**, total interest = **$863,704**
>
> **Sensitivity:** $1.27 increase in monthly P&I per basis-point increase
> in rate. **Worst-case scenario** (10.000%): payment is 38.8% higher than
> today's quote.
>
> Full sweep CSV saved to `reports/048-stress-sweep-2026-05-02.csv`.

### Anti-patterns

- Do NOT show "thinking" / intermediate scenarios as they compute. The
  subagent runs in isolation; the main thread sees only the dispatch line
  and the final summary.
- Do NOT exceed the 1k-token summary budget. If the user wants every row,
  point them to the CSV report file.
- Do NOT auto-dispatch to subagent for N ≤ 5 scenarios. Run inline; the
  context cost of dispatch isn't justified.

### Other Subagent Handoffs (Phase 11)

Same pattern applies to `amortization-agent` (SUBA-01) and `refi-npv-agent`
(SUBA-02):

| Subagent | Dispatch line | Summary budget |
|----------|---------------|----------------|
| `amortization-agent` | "Building amortization schedule…" | ≤ 1k tokens (table or CSV path) |
| `refi-npv-agent` | "Comparing {N} refi offers across {M} rate-path scenarios…" | ≤ 1k tokens (ranked recommendations + NPV deltas) |
| `stress-test-agent` | "Running {N}-scenario stress sweep…" | ≤ 1k tokens (sensitivity summary + report path) |

---

## `modes/_shared.md` Content (i)

This file is loaded with EVERY mode (mirrors `career-ops/modes/_shared.md`
pattern). Contents Claude inherits before executing any mode:

### Mandatory Sections (in order)

```markdown
# System Context — mortgage-ops

<!-- AUTO-UPDATABLE. Don't put personal data here.
     Personalization → modes/_profile.md (User Layer; gitignored). -->

## Sources of Truth

| File | Path | When |
|------|------|------|
| household.yml | `config/household.yml` | When mode needs household data (affordability, evaluate, stress with income) |
| profile.yml | `config/profile.yml` | ALWAYS — defaults |
| _profile.md | `modes/_profile.md` | ALWAYS if exists — user overrides |
| known-loans.yml | `data/known-loans.yml` | When user references "my loan" / "the BoA loan" |
| reference YAMLs | `data/reference/*.yml` | Read by scripts; Claude does NOT read these directly |

## Money Discipline (non-negotiable)

- Claude NEVER computes money. Every dollar figure comes from a `scripts/`
  invocation, verbatim.
- Money fields in script JSON inputs MUST be JSON strings: `"400000.00"`,
  not `400000.0`. Pydantic v2 strict rejects floats at the boundary.
- Rate fields are also strings: `"0.065000"`, six decimals for stability.
- See `references/spreadsheet-conventions.md` for the rounding contract
  (load only if the user asks "why don't your numbers match Excel?").

## Always Cite the Script

Every number quoted to the user MUST carry provenance:

> Your monthly P&I is **$2,528.27** *(computed by `amortize.py` at
> 2026-05-02 14:32:11)*.

If a number cannot be traced to a script invocation, do NOT emit it.

## Never Invent Numbers

If the user gives partial inputs (e.g., "what's the payment on a $400k
loan?" without rate or term), Claude asks for the missing input. Claude
does NOT guess "assume 6.5% / 30yr" — Claude asks "what rate and term?".

Exception: if FRED MCP is available (Phase 12) and the user has not
specified a rate, Claude offers "use today's MORTGAGE30US ({rate}%)?".

## Estimated APR Literal Text

Rule SKLL-APR-1 — every APR figure is labeled "estimated APR" with the
qualifier "estimated" preceding the noun. Never drop the qualifier, even
when echoing user vocabulary. See Phase 10 UI-SPEC §"(e) Estimated APR
Literal-Text Rule" for the full contract.

## Script Invocation Doctrine

- ALWAYS run `scripts/{script}.py --help` first if you haven't called it
  this session. Read the help text; do not read the source unless
  customization is required (Anthropic webapp-testing pattern;
  `CLAUDE.md` "Bundled scripts" convention).
- Build the input JSON in a temp file; pass with `--input <path>`.
- Parse stdout as the success-path JSON. Parse stderr as the 6-key
  envelope on validation failure (Phase 3 WR-02 closure).
- Exit code 0 = success; exit code 2 = boundary failure; any other code
  = unexpected, surface as "I hit an unexpected error running
  `{script}.py` (exit code {N}). Try again or check the script
  installation."

## Error Narration Template

(See Phase 10 UI-SPEC §"(c) Error UX" for the full template and three
worked examples. Every mode inherits this verbatim.)

## Output File Naming (Reports)

Reports go to `reports/{###}-{slug}-{YYYY-MM-DD}.md`, sequentially
numbered (3-digit zero-padded, max existing + 1) — career-ops pattern.
After writing, ingest into DuckDB via `orchestration/db-write.mjs
insert-report --file reports/...` (Phase 9 contract).

## Forbidden Behaviors

- Editing User Layer files (`config/household.yml`, `config/profile.yml`,
  `modes/_profile.md`, anything under `data/` user-private).
- Computing money inline.
- Dropping the "estimated" qualifier on APR.
- Dumping raw JSON envelopes to the user.
- Auto-retrying after a validation error (always ask first).
- Loading multiple `references/*.md` when the user asks one question.
- Calling FRED MCP without checking the 7-day cache first (Phase 12 LIVE-03).
```

This file is ~120 lines, well within budget. Total `SKILL.md` +
`_shared.md` + (one mode file) is the typical context load per
invocation: ≈ 500 + 120 + 200 = 820 lines, ~6-8k tokens, leaves ample
headroom under Anthropic's skill convention.

---

## `modes/_profile.md` Content (j)

This file is **User Layer** (DATA_CONTRACT, gitignored, NEVER auto-edited).
The system layer ships `modes/_profile.template.md` (committed) which the
user copies/edits manually. Contents:

### Template Structure (`modes/_profile.template.md`, committed)

```markdown
# User Profile Overrides — mortgage-ops

<!-- This file is User Layer (DATA_CONTRACT). Customize freely.
     The system never auto-edits it. Copy from this template:
       cp modes/_profile.template.md modes/_profile.md
     Then edit the values below. -->

## Default Geography

- Default state: WA
- Default county FIPS: 53/033 (King County)
- (Used for affordability lookups when the user doesn't specify; can be
  overridden per-invocation.)

## Default Credit Score Buckets

- Primary applicant bucket: 760+
- Joint applicant bucket: 740-759
- (Used for PMI rate lookups, FHA tier selection, etc. Can be overridden
  per-invocation.)

## Default Loan Terms

- Default term_months: 360 (30-year fixed)
- Default loan_type: conventional
- Default frequency: monthly

## Default Rates

- Use FRED MCP (MORTGAGE30US) when available, else prompt
- Manual override rate (when FRED unavailable and user wants a default):
  6.500%

## Narrative Style Preferences

- Verbosity: concise (1-2 sentences per number) | detailed (full context)
  | terse (number + provenance only)
  Default: concise
- Include caveats inline: yes | no
  Default: yes (regulatory caveats are non-negotiable; this controls
  *additional* context like "this assumes you escrow taxes and insurance")
- Currency display: $X,XXX.XX (USD with comma) | bare-number
  Default: $X,XXX.XX
- Rate decimal places: 3 | 4 | 5
  Default: 3 (e.g., 6.500%, not 6.5000%)
- "Round-number" sanity checks: include | omit
  When include: after every multi-thousand calculation, Claude adds a
  one-line sanity check ("$2,528/mo × 360 = $910k total — matches script
  output").
  Default: omit (Claude is the narrator, not the auditor; the script is
  the source of truth and the unit tests have already verified totals)

## Personal Defaults

- Down payment cash available: $___,___.__
- Target DTI cap: 0.43 (43%, the QM safe-harbor ceiling)
- Maximum monthly housing payment comfortable: $_,___.__
- Stress-test floor rate to assume: 9.000%
- (These are used as defaults in `affordability` and `stress` modes when
  not specified per-invocation.)

## Scoring & Recommendation Style

- For "should I refi" questions, the breakeven horizon I care about: 36
  months
  (`refinance` mode uses this as the NPV horizon default.)
- For ARM modeling, the rate-path scenarios I care about most:
  ["base", "fed-cuts-100bp", "fed-hikes-200bp", "stress-floor"]
- For "compare" mode, my ranking weights:
  - Total interest: 40%
  - Monthly payment: 30%
  - Closing costs: 20%
  - Flexibility (no prepayment penalty, recast available): 10%

## Notes Field (free-form)

(Anything else you want Claude to know about your situation. E.g.:
"We plan to move within 5 years, so favor low-closing-cost options."
"My spouse is self-employed; expect lender skepticism on income docs.")
```

### What Goes Here vs. _shared.md

| Belongs in `_profile.md` (User Layer) | Belongs in `_shared.md` (System Layer) |
|---------------------------------------|-----------------------------------------|
| Default state, county, credit bucket | Money discipline rule |
| Personal narrative preferences (verbosity, decimal places) | Estimated-APR literal-text rule |
| Personal financial defaults (down payment, DTI cap) | Script invocation doctrine |
| User-specific ranking weights for compare mode | Error narration template |
| Free-form notes | Output file naming convention |

If a `_profile.md` value conflicts with a `_shared.md` value, `_profile.md`
wins (career-ops pattern: "Read _profile.md AFTER this file. User
customizations in _profile.md override defaults here.").

### Enforcement

- `.gitignore` blocks `git add` of `modes/_profile.md` (DATA_CONTRACT
  enforcement #1).
- `scripts/hooks/block-user-layer.py` refuses any commit that stages
  `modes/_profile.md` (enforcement #2).
- The skill MUST NOT write to `modes/_profile.md`. If the user says "save
  my preference for terse output", Claude says: "I can't auto-edit
  `modes/_profile.md` (it's User Layer per DATA_CONTRACT). Edit it
  yourself — change the `Verbosity:` line to `terse`. I'll respect it on
  the next invocation."

---

## Discovery Menu (no args)

When the user invokes `/mortgage-ops` with no arguments (or with an
unrecognized sub-command that doesn't match auto-detection), show:

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
    never auto-edited)
  - Defaults: modes/_profile.md (your preferences; never auto-edited)
```

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| not applicable | not applicable | not applicable — no UI components consumed |

**Rationale:** the skill emits markdown + JSON to a chat transcript. There
is no shadcn registry, no third-party block, nothing to vet. The
gsd-ui-checker dimension 6 (Registry Safety) auto-passes for this phase.

---

## Pre-Populated From

| Source | Decisions Used |
|--------|---------------|
| `CLAUDE.md` (project root) | Skill portability rules (SKLL-01..04, ≤500 lines, ≤5k tokens, references on demand); money discipline (Decimal-from-strings, never floats); script invocation doctrine (--help first); estimated APR rule (PROJECT decision); reports/ directory pattern |
| `DATA_CONTRACT.md` | User/System/Data layer split; `config/household.yml` + `config/profile.yml` + `modes/_profile.md` are User Layer (NEVER auto-written); pre-commit hook enforcement; .gitignore enforcement |
| `.planning/REQUIREMENTS.md` (SKLL-01..13) | All 13 Phase 10 requirements pre-populate the contract — file structure, mode list, references list, script invocation rules, report file naming |
| Phase 3 / Phase 4 / Phase 5 D-13 / D-17 / D-18 / D-19 / WR-02 | 6-key Pydantic envelope shape on stderr; `--input <path>` only (no stdin); lazy-import doctrine; relocation of scripts to `.claude/skills/mortgage-ops/scripts/` in Phase 10 |
| Phase 7 SC-4 | "Estimated APR" literal-text rule (SKLL-APR-1) |
| Phase 11 SUBA-01..06 (forward-link) | Subagent handoff UX, ≤1k token summary contract |
| `career-ops/.claude/skills/career-ops/SKILL.md` + `career-ops/modes/_shared.md` + `career-ops/modes/evaluate.md` | Mode file structure (when-to-invoke / what-scripts-to-call / what-to-narrate / edge-cases spine); discovery menu format; `_shared.md` + `_profile.md` split; "Read _profile.md AFTER this file. User customizations override" rule; report numbering convention |
| `scripts/amortize.py` + `scripts/affordability.py` + `scripts/arm_simulate.py` + `scripts/_cli_helpers.py` | Exact 6-key envelope shape; success/failure stdout/stderr contract; exit code semantics; file-not-found vs validation-error envelope distinction |

---

## Checker Sign-Off (gsd-ui-checker dimensions)

| Dimension | Disposition | Notes |
|-----------|-------------|-------|
| Dimension 1 — Copywriting | PASS pending | Discovery menu, error narration template (3 worked examples), empty-state copy for household.yml / profile.yml / known-loans.yml, subagent dispatch line, "estimated APR" literal-text rule, narration template ("answer + provenance"), forbidden patterns table — all defined |
| Dimension 2 — Visuals | N/A | Text-only surface (markdown + JSON in chat); no graphical elements |
| Dimension 3 — Color | N/A | Text-only surface; functional analog (information hierarchy in narration) defined instead |
| Dimension 4 — Typography | N/A | Markdown conventions defined instead — money formatting, rate formatting, "estimated APR" bolding, provenance italics |
| Dimension 5 — Spacing | N/A | Structural density defined instead — line budgets per file, narration length budgets, subagent summary budget |
| Dimension 6 — Registry Safety | PASS | No registry consumed; auto-pass |

**Approval:** pending — awaiting gsd-ui-checker review.

---

*Phase 10 UI-SPEC drafted 2026-05-02 by gsd-ui-researcher. Source documents:
`/Users/cujo253/Documents/mortgage-ops/CLAUDE.md`,
`/Users/cujo253/Documents/mortgage-ops/DATA_CONTRACT.md`,
`/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md`,
`/Users/cujo253/Documents/career-ops/modes/_shared.md`,
`/Users/cujo253/Documents/career-ops/modes/evaluate.md`,
`/Users/cujo253/Documents/mortgage-ops/scripts/amortize.py`,
`/Users/cujo253/Documents/mortgage-ops/scripts/affordability.py`,
`/Users/cujo253/Documents/mortgage-ops/scripts/arm_simulate.py`,
`/Users/cujo253/Documents/mortgage-ops/scripts/_cli_helpers.py`,
`/Users/cujo253/Documents/mortgage-ops/.planning/REQUIREMENTS.md`.*
