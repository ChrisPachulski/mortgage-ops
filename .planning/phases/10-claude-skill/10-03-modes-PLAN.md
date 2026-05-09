---
phase: 10
plan: 03
type: execute
wave: 3
depends_on:
  - "10-00"
  - "10-02"
files_modified:
  - .claude/skills/mortgage-ops/modes/_shared.md
  - .claude/skills/mortgage-ops/modes/_profile.example.md
  - .claude/skills/mortgage-ops/modes/evaluate.md
  - .claude/skills/mortgage-ops/modes/compare.md
  - .claude/skills/mortgage-ops/modes/refinance.md
  - .claude/skills/mortgage-ops/modes/affordability.md
  - .claude/skills/mortgage-ops/modes/stress.md
  - .claude/skills/mortgage-ops/modes/amortize.md
  - .claude/skills/mortgage-ops/modes/arm.md
  - .gitignore
  - scripts/hooks/block-user-layer.py
  - tests/test_block_user_layer.py
  - DATA_CONTRACT.md
autonomous: true
requirements:
  - SKLL-05
  - SKLL-06
  - SKLL-07
  - SKLL-13
tags:
  - phase-10
  - claude-skill
  - modes
  - skll-05
  - skll-06
  - skll-07
  - skll-13
must_haves:
  truths:
    - "All 7 mode files (evaluate, compare, refinance, affordability, stress, amortize, arm) exist under .claude/skills/mortgage-ops/modes/ as committed System Layer files"
    - "modes/_shared.md exists and contains the mandatory sections from UI-SPEC §i PLUS a `## Save Report` step (D-13-01..05) PLUS an `## Output Formatting` section with D-NUM-01..06 money/rate/ratio/bps directives"
    - "modes/_shared.md `## Save Report` step writes `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md` then calls `node orchestration/db-write.mjs insert-report --scenario-id <int> --file <path>` per D-13-02 + D-13-03 + D-13-04 (REAL Phase 9 CLI per orchestration/db-write.mjs:296-310 — Round-2 codex HIGH 2). Sequence number is read via `node orchestration/db-write.mjs query --sql "SELECT COUNT(*)+1 ... FROM reports"`. Reports table schema has no `filename` column; the file on disk is the durable anchor. `_profile.md save_report: false` is the only D-13-05 override."
    - "modes/_shared.md `## Output Formatting` section copies D-NUM-01..06 verbatim (money $1,264.14; rates 6.500%; ratios 43.0%; bps `250 bps (2.50%)` for ARM; D-NUM-05 internal Decimal precision unchanged; D-NUM-06 helpers as inline templates)"
    - "modes/_profile.example.md exists with EXACTLY four top-level YAML keys per LOCKED DECISIONS D-PROF-01 + D-PROF-02: `verbosity`, `citation_density`, `save_report`, `disambiguation`. NO duplication of calc inputs (joint income, applicants, monthly debts, escrow, va block, etc. — those stay in config/household.yml + config/profile.yml per D-PROF-02)"
    - "modes/_profile.md is gitignored (NEVER appears in committed tree); the .gitignore entry exists"
    - "scripts/hooks/block-user-layer.py USER_LAYER_PATTERNS includes .claude/skills/mortgage-ops/modes/_profile.md (DATA_CONTRACT.md sync rule)"
    - "DATA_CONTRACT.md User Layer table has the path .claude/skills/mortgage-ops/modes/_profile.md (corrected from the project-root modes/_profile.md the file currently shows)"
    - "modes/stress.md includes the existence-check forward-link per LOCKED DECISION D-SUBA-FW-02: literal phrase `if it exists` AND literal path `.claude/agents/stress-test-agent.md`. For sweeps with N > 5 scenarios, defer to that agent IF EXISTS; otherwise run inline."
    - "modes/evaluate.md dispatches to BOTH `scripts/amortize.py` AND `scripts/affordability.py` (composes affordability outputs DTI/LTV/CLTV/PITI alongside P&I per UI-SPEC §a)"
    - "Each mode file follows the UI-SPEC §b 4-section spine: ## When to invoke, ## What scripts to call, ## What to narrate, ## Edge cases"
  artifacts:
    - path: ".claude/skills/mortgage-ops/modes/_shared.md"
      provides: "Shared inheritance for every mode: sources of truth, money discipline, error narration template, report file naming, forbidden behaviors. Loaded BEFORE every mode file (D-10)."
      min_lines: 80
    - path: ".claude/skills/mortgage-ops/modes/_profile.example.md"
      provides: "Schema skeleton (committed System Layer); user copies to _profile.md (gitignored User Layer)"
      min_lines: 40
    - path: ".claude/skills/mortgage-ops/modes/evaluate.md"
      provides: "evaluate mode dispatcher (single-loan analysis)"
      contains: "## When to invoke"
    - path: ".claude/skills/mortgage-ops/modes/compare.md"
      provides: "compare mode dispatcher (multi-offer ranking)"
      contains: "## When to invoke"
    - path: ".claude/skills/mortgage-ops/modes/refinance.md"
      provides: "refinance mode dispatcher (refi NPV); references Phase 6 scripts/refi_npv.py"
      contains: "## When to invoke"
    - path: ".claude/skills/mortgage-ops/modes/affordability.md"
      provides: "affordability mode dispatcher; lifts JSON shape from scripts/affordability.py --help epilog"
      contains: "## When to invoke"
    - path: ".claude/skills/mortgage-ops/modes/stress.md"
      provides: "stress mode dispatcher; includes Phase 11 SUBA-05 subagent forward-link for N>5 scenarios"
      contains: "stress-test-agent"
    - path: ".claude/skills/mortgage-ops/modes/amortize.md"
      provides: "amortize mode dispatcher; lifts from scripts/amortize.py --help epilog"
      contains: "## When to invoke"
    - path: ".claude/skills/mortgage-ops/modes/arm.md"
      provides: "arm mode dispatcher; lifts from scripts/arm_simulate.py --help epilog"
      contains: "## When to invoke"
  key_links:
    - from: "Every mode file"
      to: "modes/_shared.md"
      via: "loaded first per D-10 + UI-SPEC §i"
      pattern: "_shared.md"
    - from: "modes/_profile.md"
      to: ".gitignore + scripts/hooks/block-user-layer.py + DATA_CONTRACT.md"
      via: "User Layer enforcement triple-check (gitignore + hook + contract)"
      pattern: "_profile.md"
    - from: "modes/stress.md"
      to: "Phase 11 stress-test-agent"
      via: "subagent dispatch when scenario_count > 5 (UI-SPEC §h forward-link)"
      pattern: "stress-test-agent"
---

<objective>
Ship all 9 mode files (`_shared.md`, `_profile.example.md`, `evaluate.md`, `compare.md`, `refinance.md`, `affordability.md`, `stress.md`, `amortize.md`, `arm.md`) inside `.claude/skills/mortgage-ops/modes/`, plus the User Layer enforcement updates (`.gitignore`, `scripts/hooks/block-user-layer.py`, `DATA_CONTRACT.md`) so `modes/_profile.md` cannot accidentally be committed.

Each mode file follows the UI-SPEC §b 4-section spine: `## When to invoke` / `## What scripts to call` / `## What to narrate` / `## Edge cases`. `_shared.md` carries the shared inheritance per UI-SPEC §i. `_profile.example.md` is the committed schema skeleton per D-07.

Closes SKLL-05 (7 mode files), SKLL-06 (`_shared.md` defines scoring + report structure with NEW D-13/D-NUM/D-PROF-04 sections), SKLL-07 (`_profile.md` gitignored + `_profile.example.md` 4-key schema per D-PROF-01), AND SKLL-13 (Phase 10 closes SKLL-13 per D-13-01..D-13-05; the `_shared.md` Save Report step writes `reports/{NNN}-{mode}-{YYYY-MM-DD}.md` and persists via `node orchestration/db-write.mjs --insert-report`).

Purpose: SKILL.md (Wave 2) routes to modes/; modes/ tells Claude how to invoke each script + narrate the output. Without this wave the skill knows where to dispatch but has no per-mode body. The User Layer enforcement (gitignore + hook + DATA_CONTRACT) is critical — `_profile.md` will hold user PII (default DTI, default state, narrative tone overrides) and MUST never enter the commit tree.

Output: 9 mode files (~80-200 lines each) + 3 enforcement-config edits.
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
@.claude/skills/mortgage-ops/scripts/amortize.py
@.claude/skills/mortgage-ops/scripts/affordability.py
@.claude/skills/mortgage-ops/scripts/arm_simulate.py
@scripts/hooks/block-user-layer.py
@.gitignore

<interfaces>
LOCKED DECISIONS:
- D-07 = User-customization template = `modes/_profile.example.md` (committed); `modes/_profile.md` (gitignored). Naming matches `config/*.example.yml`.
- D-10 = Every mode loads `modes/_shared.md` first, THEN its own mode file.

UI-SPEC §b mode-file 4-section spine — every modes/{mode}.md MUST follow:
1. `## When to invoke` — routing predicate
2. `## What scripts to call` — script name + JSON-input shape + JSON-output shape
3. `## What to narrate` — output narration discipline (template + provenance)
4. `## Edge cases` — empty state, error states, ambiguous routing

UI-SPEC §i `_shared.md` mandatory sections (in order):
- Sources of Truth (which files Claude reads + when)
- Money Discipline (Decimal-from-strings; never recompute)
- Always Cite the Script (provenance template)
- Never Invent Numbers (ask for missing inputs)
- Estimated APR Literal Text (Phase 7 forward-link)
- Script Invocation Doctrine (--help first)
- Error Narration Template (cross-link to UI-SPEC §c)
- Output File Naming (reports/{###}-{slug}-{YYYY-MM-DD}.md per SKLL-13)
- Forbidden Behaviors (no User Layer writes; no inline math; no APR-without-estimated; no raw JSON dumps)

UI-SPEC §h Subagent Handoff (modes/stress.md MUST include):
> When `stress` mode receives a sweep request with N > 5 scenarios, it
> dispatches to `stress-test-agent` (Phase 11 SUBA-03 / SUBA-05). User sees
> one-line dispatch announcement + isolated subagent run + ≤ 1k token return summary.

UI-SPEC §j _profile.example.md template — sections:
- Default Geography (state, county FIPS)
- Default Credit Score Buckets
- Default Loan Terms (term_months, loan_type, frequency)
- Default Rates (FRED MORTGAGE30US fallback or manual override)
- Narrative Style Preferences (verbosity, currency display, rate decimals)
- Personal Defaults (down payment, target DTI, max comfortable PITI, stress floor)
- Scoring & Recommendation Style (refi breakeven horizon, ARM scenarios, compare weights)
- Notes (free-form)

DATA_CONTRACT.md line 19 currently says:
> | `modes/_profile.md` | (Phase 10) user-specific narrative overrides for the Claude skill |

This Wave UPDATES line 19 path to `.claude/skills/mortgage-ops/modes/_profile.md` (the actual location per Phase 10 portability rule).

scripts/hooks/block-user-layer.py USER_LAYER_PATTERNS tuple (lines ~17-25) currently lists:
- "config/household.yml"
- "config/profile.yml"
- (Phase 10 ADDS) ".claude/skills/mortgage-ops/modes/_profile.md"

Phase 10 PATTERNS CRITICAL #6 (LICENSE.txt content) is OUT OF SCOPE for this wave (Wave 2 already shipped MIT LICENSE.txt).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create modes/_shared.md (D-10 inheritance + UI-SPEC §i + D-13 Save Report + D-NUM-01..06 Output Formatting + D-PROF-04 fallback)</name>
  <files>.claude/skills/mortgage-ops/modes/_shared.md</files>
  <read_first>
    10-UI-SPEC §i — verbatim _shared.md mandatory sections content;
    10-PATTERNS `modes/_shared.md` section;
    10-CONTEXT.md D-13-01..D-13-05 (Save Report step verbatim);
    10-CONTEXT.md D-NUM-01..D-NUM-06 (formatting directives verbatim);
    10-CONTEXT.md D-PROF-04 (`_profile.md` fallback defaults: standard / inline / true / always-ask);
    Phase 9 orchestration/db-write.mjs (cmdInsertReport handler — verify --insert-report subcommand signature);
    references/data-layer.md (Phase 9 onboarding doc; cross-linked from _shared.md)
  </read_first>
  <action>
Create `.claude/skills/mortgage-ops/modes/_shared.md` (~180-220 lines — grew vs original ~120 because D-13 Save Report + D-NUM Output Formatting + D-PROF-04 fallback are new mandatory sections per CONTEXT.md).

Start by pasting the UI-SPEC §i "Mandatory Sections" markdown verbatim. Then EXTEND with the following NEW sections per CONTEXT.md:

**ADD `## Profile Loading` section (per D-PROF-04 fallback). Round-2 codex HIGH 4 Option A: parse `_profile.md` DIRECTLY as YAML — the example template (Task 2) is pure YAML in a .md-named file, so the user's `cp`'d copy is also pure YAML and `yaml.safe_load(open("modes/_profile.md").read())` works without fenced-block extraction.**

```markdown
## Profile Loading

Before any mode runs, attempt to read `modes/_profile.md` (User Layer; gitignored). If the file exists, parse the ENTIRE file body directly as YAML via `yaml.safe_load(open("modes/_profile.md").read())` and extract the four knobs: `verbosity`, `citation_density`, `save_report`, `disambiguation`.

`_profile.md` is pure YAML — comments are `#`-prefixed YAML comments, not markdown. Do NOT search for a fenced ` ```yaml ... ``` ` block; the file has no fence. The committed template `modes/_profile.example.md` (Plan 10-03 Task 2) is also pure YAML, so the user's `cp _profile.example.md _profile.md` produces a directly-parseable file (Round-2 codex HIGH 4 Option A: this is the cp-and-parse contract D-PROF-04 relies on).

If the file is missing (fresh checkout, user hasn't customized), fall back to defaults per D-PROF-04:

- `verbosity: standard`
- `citation_density: inline`
- `save_report: true`
- `disambiguation: always-ask`

These defaults match `_profile.example.md` (the committed template). Do NOT auto-create `_profile.md` — User Layer enforcement (DATA_CONTRACT.md / FND-10 hook) prohibits the system from writing User Layer files.
```

**ADD `## Output Formatting` section (per D-NUM-01..D-NUM-06 — copy directives verbatim from CONTEXT.md):**

```markdown
## Output Formatting

All numeric narration follows these rules. The lib/* layer continues to round at end-of-period only (Phase 1 D-01 / Phase 5 D-14); this is a DISPLAY layer (D-NUM-05).

- **Money (D-NUM-01):** Always 2 decimal places, comma thousand separators, `$` prefix. Examples: `$400,000.00`, `$2,528.27/mo`, `$163,200.00`.
- **Rates (D-NUM-02):** Always 3 decimal places, trailing zeros preserved, `%` suffix. Examples: `6.500%`, `3.875%`, `0.000%`.
- **Ratios (DTI / LTV / CLTV) (D-NUM-03):** Always 1 decimal place, `%` suffix. Examples: `43.0%`, `97.5%`, `0.0%`. NOT raw decimal `0.43`. NOT integer `43%`.
- **ARM bps (D-NUM-04):** ARM mode (`modes/arm.md`) shows margin/caps/floors in basis points with parenthesized percent. Other modes use percent only (D-NUM-02). Examples: `periodic_cap: 200 bps (2.00%)`, `lifetime_cap: 500 bps (5.00%)`, `margin: 275 bps (2.75%)`.
- **D-NUM-05 (no internal precision change):** scripts/* return raw Decimal-string JSON; this formatting is applied by Claude during narration only.
- **D-NUM-06 (helper location):** display formatters (`fmt_money`, `fmt_rate`, `fmt_ratio`, `fmt_bps`) are inline templates in this section, NOT Python helpers in `lib/`.
```

**ADD `## Save Report` section (per D-13-01..D-13-05 — Phase 10 closes SKLL-13):**

The CLI invocations below are the REAL Phase 9 surface from `orchestration/db-write.mjs:296-310` (Round-2 codex HIGH 2: prior draft used `--query "..."` and `--insert-report --json '{...}'` flags that do NOT exist on the actual handler). The reports table schema (`orchestration/init-db.mjs` lines 76-82) is `(id, scenario_id NOT NULL, markdown_blob TEXT NOT NULL, generated_at TIMESTAMP)` — NO `filename` column. The file on disk IS the durable filename anchor; the DB row stores the markdown body keyed by scenario_id.

```markdown
## Save Report (D-13-01..D-13-05; SKLL-13 closure)

After every mode invocation produces a report, write the report to disk and persist a row to DuckDB. This is unconditional unless the user opts out via `_profile.md` `save_report: false`. The Phase 9 CLI is `orchestration/db-write.mjs` — see its usage block (lines 296-310) for the canonical subcommand surface.

Step 1 — Determine the next report sequence number using the real `query` subcommand:
   ```
   node orchestration/db-write.mjs query --sql "SELECT COUNT(*)+1 AS next_seq FROM reports"
   ```
   Handler returns a JSON array on stdout (Phase 9 `cmdQuery` pattern), e.g. `[{"next_seq": 7}]`. Parse the first element's `next_seq` field.

Step 2 — Construct the filename per D-13-02 (`reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md`):
   - `NNN` = zero-padded 3-digit sequence number from Step 1
   - `mode` = current mode (one of: evaluate / compare / refinance / affordability / stress / amortize / arm)
   - `YYYY-MM-DD` = current ISO date
   Example: `reports/042-stress-2026-05-08.md`.

Step 3 — Ensure a `scenarios.id` exists for this run. The skill obtains `<scenario_id>` from the prior `insert-scenario` call in the mode body (modes/{mode}.md persists the scenario request/response BEFORE the Save Report step). If no scenario was persisted (rare — purely informational mode invocation), skip to Step 6 (file-only save).

Step 4 — Write the report markdown body to the filename from Step 2. The report content is the human-readable narration (this same response, formatted per D-VOICE-01 / D-NUM-01..06). The file path on disk is the durable filename anchor.

Step 5 — Persist the markdown body to DuckDB per D-13-04, using the REAL `insert-report` subcommand which takes the file path directly:
   ```
   node orchestration/db-write.mjs insert-report --scenario-id <int> --file reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md
   ```
   The handler reads the file body and INSERTs `(scenario_id, markdown_blob)` inside a withLock-gated transaction (Phase 9 D-03-04 / PERS-03). On success it prints `{"ok": true, "report_id": <int>, "scenario_id": <int>, "bytes": <n>}` to stdout. There is NO `--json` flag and there is NO `filename` column in the `reports` table — the file path is information that lives on disk, not in the row.

Step 6 — Override per D-13-05: if `_profile.md` `save_report: false`, SKIP all of steps 1-5. Skill default per D-13-03 is unconditional save; this opt-out is the only escape hatch. Reports/ is gitignored (Phase 1 FND-08) so saved reports do not pollute git history.

This section closes SKLL-13 in Phase 10; tests `test_report_filename_format` + `test_report_persisted_to_duckdb` (Wave 0 stubs from Plan 10-00) flip in Wave 5 to enforce both the filename pattern AND the literal `node orchestration/db-write.mjs insert-report` substring. Plan 10-06 ships an end-to-end smoke that actually exercises Steps 1-5.
```

Verify the file ends up with these H2 headings (in order):
1. `## Sources of Truth`
2. `## Profile Loading` (NEW — D-PROF-04)
3. `## Money Discipline (non-negotiable)`
4. `## Always Cite the Script`
5. `## Never Invent Numbers`
6. `## Estimated APR Literal Text`
7. `## Script Invocation Doctrine`
8. `## Error Narration Template`
9. `## Output File Naming (Reports)` (REUSED from UI-SPEC §i; cross-references the Save Report section below)
10. `## Output Formatting` (NEW — D-NUM-01..06)
11. `## Save Report` (NEW — D-13-01..D-13-05)
12. `## Forbidden Behaviors`

DO NOT add personal data (the file is System Layer).
DO NOT inline the full error-narration template body (UI-SPEC §c hosts it; this file just states the rule + cross-references).

Token budget: ≤ 3000 cl100k tokens (raised from prior 2000 to absorb three new sections; verify with count_tokens helper).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/skills/mortgage-ops/modes/_shared.md &amp;&amp; for h in "Sources of Truth" "Profile Loading" "Money Discipline" "Always Cite the Script" "Never Invent Numbers" "Estimated APR" "Script Invocation Doctrine" "Error Narration Template" "Output File Naming" "Output Formatting" "Save Report" "Forbidden Behaviors"; do grep -q "$h" .claude/skills/mortgage-ops/modes/_shared.md || { echo "MISSING: $h"; exit 1; }; done &amp;&amp; grep -q 'db-write.mjs insert-report --scenario-id' .claude/skills/mortgage-ops/modes/_shared.md &amp;&amp; ! grep -q -- '--insert-report --json' .claude/skills/mortgage-ops/modes/_shared.md &amp;&amp; ! grep -q -- 'db-write.mjs --query' .claude/skills/mortgage-ops/modes/_shared.md &amp;&amp; grep -q '250 bps (2.50%)\|periodic_cap: 200 bps\|margin: 275 bps' .claude/skills/mortgage-ops/modes/_shared.md &amp;&amp; grep -q 'save_report: false' .claude/skills/mortgage-ops/modes/_shared.md &amp;&amp; python -c "from tests._skill_helpers import count_tokens; assert count_tokens(open('.claude/skills/mortgage-ops/modes/_shared.md').read()) &lt;= 3500"</automated>
  </verify>
  <acceptance_criteria>
- File exists with ≥ 150 lines
- All 12 mandatory section headings present (9 UI-SPEC §i + Profile Loading + Output Formatting + Save Report)
- Token count ≤ 3500 cl100k (≤ 3000 nominal + buffer for D-13/D-NUM/D-PROF additions)
- Contains the substring "modes/_profile.md" (cross-reference to User Layer file)
- Contains the substring "reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md" or "{NNN}-{mode}-{YYYY-MM-DD}" (D-13-02 filename convention)
- Contains the literal substring "node orchestration/db-write.mjs insert-report --scenario-id" (D-13-04; REAL Phase 9 CLI per orchestration/db-write.mjs:296-310 — Round-2 codex HIGH 2)
- Does NOT contain the substring "--insert-report --json" (Round-2 codex HIGH 2: that flag form does not exist on the handler)
- Does NOT contain the substring "db-write.mjs --query" (Round-2 codex HIGH 2: real subcommand is `query --sql "..."`, not `--query "..."`)
- Does NOT reference a `filename` column on the `reports` table (Round-2 codex HIGH 2: schema per init-db.mjs is `(id, scenario_id, markdown_blob, generated_at)` — no `filename` column. The file on disk is the filename anchor.)
- Contains the literal substring "save_report: false" (D-13-05 override)
- Contains the literal substring "estimated APR" (Phase 7 forward-link)
- D-NUM-01: contains "$1,264.14" or "$2,528.27" or "$400,000.00" example
- D-NUM-02: contains "6.500%" or "3.875%" example
- D-NUM-03: contains "43.0%" example
- D-NUM-04: contains "bps (2.50%)" or "bps (2.00%)" or similar `bps (X.XX%)` example
- D-PROF-04 fallback defaults present: standard / inline / true / always-ask
  </acceptance_criteria>
  <done>
    _shared.md ships with 12 sections including D-PROF-04 fallback, D-NUM-01..06 Output Formatting, and D-13-01..05 Save Report — closing SKLL-13 at the modes layer.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create modes/_profile.example.md with EXACTLY four top-level keys per LOCKED DECISIONS D-PROF-01 + D-PROF-02</name>
  <files>.claude/skills/mortgage-ops/modes/_profile.example.md</files>
  <read_first>
    10-CONTEXT.md D-PROF-01 (verbatim 4-key YAML block);
    10-CONTEXT.md D-PROF-02 (no calc-input duplication rule);
    10-CONTEXT.md D-PROF-03 (gitignore + hook enforcement);
    10-CONTEXT.md D-PROF-04 (default values: standard / inline / true / always-ask)
  </read_first>
  <action>
Create `.claude/skills/mortgage-ops/modes/_profile.example.md` (~25-40 lines — DELIBERATELY narrow per D-PROF-02; supersedes UI-SPEC §j which was drafted before D-PROF-01 locked).

**Round-2 codex HIGH 4 — pure-YAML template (Option A):** The user `cp`s this file to `modes/_profile.md` (D-PROF-03), and `_shared.md` (Plan 10-03 Task 1 `## Profile Loading` section) parses `_profile.md` DIRECTLY as YAML per D-PROF-04. If the example template were a markdown wrapper around a fenced YAML block, the user's `cp`'d copy would fail `yaml.safe_load` because the file would start with `<!-- ... -->` and `# Skill Behavior Profile` (markdown), not YAML.

Resolution: the file extension stays `.md` (matches existing `config/*.example.yml` naming spirit and inherits the `.md` discipline of the modes/ folder), but the CONTENT is pure YAML throughout — `#` comments at the top of the file substitute for the markdown header, and there is NO fenced ` ```yaml ... ``` ` block. `yaml.safe_load(open(path).read())` parses the whole file directly. CONTEXT.md D-PROF-01 already shows this exact pattern (the verbatim YAML block IS the file).

The file body MUST have EXACTLY these four top-level keys (no others) per D-PROF-01:

- `verbosity` — concise | standard | verbose
- `citation_density` — full | inline | minimal
- `save_report` — true (D-13-03 default) | false (D-13-05 user override)
- `disambiguation` — always-ask | auto-pick

Write `.claude/skills/mortgage-ops/modes/_profile.example.md` with EXACTLY this content (verbatim — the leading `#` lines are YAML comments, NOT a markdown header):

```
# modes/_profile.example.md  (User Layer — copy to modes/_profile.md and edit; _profile.md is gitignored)
#
# Four knobs that scale the skill's narration and default behavior.
# Per LOCKED DECISIONS D-PROF-01 + D-PROF-02 (10-CONTEXT.md), this file does
# NOT duplicate calc inputs (joint income, applicants, monthly debts,
# state_fips, county_fips, escrow, va block, target property value, lender
# preferences) — those live in config/household.yml + config/profile.yml per
# Phase 1 DATA_CONTRACT.
#
# If _profile.md is missing on a fresh checkout, modes/_shared.md falls back
# to the four defaults below (D-PROF-04: standard / inline / true / always-ask).
#
# Field semantics:
#
#   verbosity:        concise = number + 1-line context;
#                     standard = full UI-SPEC three-part template
#                                (number / interpretation / citation);
#                     verbose  = full citations + worked-example breakdowns
#                                + footnoted cross-refs to references/*.md
#                                (D-VOICE-02).
#
#   citation_density: full = every claim cited;
#                     inline = key claims only;
#                     minimal = only blocking claims (e.g., DTI cap rejection).
#
#   save_report:      true  = unconditional auto-write per D-13-03;
#                     false = the ONLY user-level override of D-13-03 (suppresses
#                             both the report file AND the matching DuckDB row).
#
#   disambiguation:   always-ask = UI-SPEC §a printed disambiguation question;
#                     auto-pick  = silently route to most-likely mode (opt-in).
#
# To customize: copy this file to modes/_profile.md (without .example) and
# edit the four values below. modes/_profile.md is gitignored; your edits
# stay private. Do NOT add additional top-level keys — Plan 10-05 CI gate
# `test_profile_example_md_has_exact_four_keys` enforces the four-key schema
# (D-PROF-01 + D-PROF-02).

verbosity: standard         # concise | standard | verbose
citation_density: inline    # full | inline | minimal
save_report: true           # true (default) | false to opt out of D-13-03 auto-write
disambiguation: always-ask  # always-ask (default) | auto-pick
```

CRITICAL — schema-correctness rules (D-PROF-01 + D-PROF-02):

1. The ENTIRE file body MUST parse cleanly with `yaml.safe_load(text)` — NO fenced ` ```yaml ... ``` ` block, NO markdown headers, NO HTML comments. Comments are `#`-prefixed YAML comments only.
2. The parsed dict MUST have EXACTLY these four top-level keys: `verbosity`, `citation_density`, `save_report`, `disambiguation`. NO extras (no `default_geography`, no `default_loan_terms`, no `default_rates`, no `personal_defaults`, no `scoring_style`, no `notes` — those would duplicate calc inputs and violate D-PROF-02).
3. Default values match D-PROF-04: `verbosity: standard`, `citation_density: inline`, `save_report: true`, `disambiguation: always-ask`.
4. Calc inputs stay in `config/household.yml` + `config/profile.yml` per Phase 1 DATA_CONTRACT User Layer.

DO NOT include placeholder example values like `default_state_fips: "53"`, `joint_income: ...`, etc. — they belong in `config/profile.yml` not here.
DO NOT create `modes/_profile.md` itself in this wave — User Layer enforcement (D-PROF-03 hook) prohibits the system from writing User Layer files.
DO NOT wrap the YAML in a markdown fence (Round-2 codex HIGH 4: this would break the cp-and-parse contract that `_shared.md` D-PROF-04 fallback relies on).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/skills/mortgage-ops/modes/_profile.example.md &amp;&amp; python -c "import yaml; t=open('.claude/skills/mortgage-ops/modes/_profile.example.md').read(); d=yaml.safe_load(t); assert set(d.keys())=={'verbosity','citation_density','save_report','disambiguation'}, f'wrong keys: {set(d.keys())}'; assert d=={'verbosity':'standard','citation_density':'inline','save_report':True,'disambiguation':'always-ask'}, f'wrong defaults: {d}'; print('OK 4 keys + D-PROF-04 defaults')" &amp;&amp; grep -q 'copy to modes/_profile.md' .claude/skills/mortgage-ops/modes/_profile.example.md &amp;&amp; ! grep -q '\`\`\`yaml' .claude/skills/mortgage-ops/modes/_profile.example.md &amp;&amp; test ! -f .claude/skills/mortgage-ops/modes/_profile.md</automated>
  </verify>
  <acceptance_criteria>
- `_profile.example.md` exists (≥ 25 lines, ≤ 60 lines — schema is intentionally narrow per D-PROF-02)
- ENTIRE file is parseable by `yaml.safe_load(text)` directly — NOT a fenced markdown block (Round-2 codex HIGH 4 Option A: pure YAML in a .md-named file with `#` comments)
- File does NOT contain ` ```yaml ` (no fenced YAML block — Round-2 codex HIGH 4)
- File does NOT contain `<!--` (no HTML comments — Round-2 codex HIGH 4)
- Parsed dict has EXACTLY these four top-level keys: `verbosity`, `citation_density`, `save_report`, `disambiguation`. NO additional top-level keys allowed.
- Default values match D-PROF-04: `verbosity == "standard"`, `citation_density == "inline"`, `save_report == True`, `disambiguation == "always-ask"`
- Top-of-file `#` comment explains how to copy the template (e.g., "copy to modes/_profile.md")
- `modes/_profile.md` does NOT exist (User Layer file is user-created)
- File does NOT contain calc-input field names: NOT `joint_income`, NOT `state_fips`, NOT `county_fips`, NOT `monthly_debts`, NOT `target_property_value`, NOT `default_loan_term` (these all violate D-PROF-02)
  </acceptance_criteria>
  <done>
    Schema skeleton ships with EXACTLY four D-PROF-01 keys; no calc-input duplication; D-PROF-04 defaults locked in.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update .gitignore + scripts/hooks/block-user-layer.py + DATA_CONTRACT.md (User Layer enforcement triple)</name>
  <files>.gitignore, scripts/hooks/block-user-layer.py, DATA_CONTRACT.md</files>
  <read_first>
    .gitignore — current rules;
    scripts/hooks/block-user-layer.py — current USER_LAYER_PATTERNS tuple (lines 17-25);
    DATA_CONTRACT.md line 19 (existing modes/_profile.md entry);
    DATA_CONTRACT.md line 73-74 (sync rule: hook + DATA_CONTRACT in same commit)
  </read_first>
  <action>
PART A — .gitignore. Append a new section:

```
# Phase 10: skill user-layer override (DATA_CONTRACT.md User Layer)
.claude/skills/mortgage-ops/modes/_profile.md
```

Insert after the existing User Layer block (look for the `config/household.yml` line as anchor). Verify the entry is NOT shadowed by a more permissive rule earlier in the file.

PART B — scripts/hooks/block-user-layer.py. Edit the `USER_LAYER_PATTERNS` tuple to add the new path. Current (verify exact lines at edit time):
```python
USER_LAYER_PATTERNS: tuple[str, ...] = (
    "config/household.yml",
    "config/profile.yml",
    ...
)
```

After:
```python
USER_LAYER_PATTERNS: tuple[str, ...] = (
    "config/household.yml",
    "config/profile.yml",
    ".claude/skills/mortgage-ops/modes/_profile.md",
    ...  # any other existing entries unchanged
)
```

Insert in alphabetical order if the tuple is sorted; otherwise append at the natural position for new entries. Re-read the file before editing to determine the exact pattern.

If `USER_LAYER_GLOB_DIRS` exists (per DATA_CONTRACT.md line 73 reference), check whether it needs an analogous addition — likely NOT (the glob-dirs is for directory-wildcards like `data/`; `_profile.md` is a single explicit file).

**Round-2 codex HIGH 3 — verify hook source actually blocks the new path.** After editing the hook, run a unit-level invocation manually before moving on:

```
python3 scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md
echo $?   # MUST be 1 (offender detected); message MUST name the file
```

If the hook returns 0 for the new path, the `USER_LAYER_PATTERNS` edit was wrong — the hook reads `argv[1:]` and checks `path in USER_LAYER_PATTERNS` (exact match) before falling back to `path.startswith(d)` for `USER_LAYER_GLOB_DIRS`. The new exact path MUST appear in the tuple. Round-2 codex HIGH 3 caught a Round-1 design where the hook was invoked with NO args (`argv[1:] = []` → `offenders = []` → return 0) and the test passed for the wrong reason; this PART D below uses the correct argv-based invocation.

PART C-bis — Update `tests/test_block_user_layer.py` parametrize list to cover the new path (Round-2 codex HIGH 3 + LOW 11). The existing test parametrizes over the legacy paths:

```python
@pytest.mark.parametrize(
    "path",
    [
        "config/household.yml",
        "config/profile.yml",
        "modes/_profile.md",
    ],
)
def test_user_layer_pattern_paths_are_blocked(path: str) -> None:
    assert is_user_layer(path) is True
```

Append the new skill-folder path to the parametrize list (KEEP the legacy `modes/_profile.md` so the project-root path is also still blocked — defense in depth):

```python
@pytest.mark.parametrize(
    "path",
    [
        "config/household.yml",
        "config/profile.yml",
        "modes/_profile.md",
        ".claude/skills/mortgage-ops/modes/_profile.md",
    ],
)
def test_user_layer_pattern_paths_are_blocked(path: str) -> None:
    assert is_user_layer(path) is True
```

Run the existing test file to confirm zero regression:

```
pytest tests/test_block_user_layer.py -v
```

ALL existing test cases MUST still pass; the new parametrize case MUST also pass.

PART D — DATA_CONTRACT.md. Edit line 19 to correct the path. Current:
```
| `modes/_profile.md` | (Phase 10) user-specific narrative overrides for the Claude skill |
```

After:
```
| `.claude/skills/mortgage-ops/modes/_profile.md` | (Phase 10) user-specific narrative overrides for the Claude skill |
```

The path correction reflects that modes/ lives INSIDE the skill folder per CLAUDE.md "Skill portability" convention, not at project root.

PART E — Verify enforcement works end-to-end. The hook reads staged paths from `argv[1:]` (NOT from `git diff --cached`), so the test invocation passes the candidate path explicitly:

```
python3 scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md
# MUST exit non-zero with clear error message naming the offending file
```

For full belt-and-suspenders coverage (Round-2 codex HIGH 3), also exercise the `git add -f` + multi-arg path with the hook's argv interface:

```
mkdir -p .claude/skills/mortgage-ops/modes/
echo "test" > .claude/skills/mortgage-ops/modes/_profile.md

# Confirm gitignore: bare `git add` is a no-op
git add .claude/skills/mortgage-ops/modes/_profile.md
git status --short  # should NOT show _profile.md

# Confirm hook rejects when invoked with the path as argv:
python3 scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md
# exit 1 expected; cleanup
rm .claude/skills/mortgage-ops/modes/_profile.md
```

If the hook does NOT reject `python3 scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md` with a non-zero exit and a message naming the offending file, the USER_LAYER_PATTERNS edit was wrong — re-investigate.

DO NOT invoke the hook with NO arguments and assume a non-zero exit (Round-2 codex HIGH 3: with `argv[1:] = []`, `offenders = []`, the hook returns 0 — the test would pass for the wrong reason). The hook MUST be invoked with the candidate path AS argv.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; grep -q '\.claude/skills/mortgage-ops/modes/_profile.md' .gitignore &amp;&amp; grep -q '\.claude/skills/mortgage-ops/modes/_profile.md' scripts/hooks/block-user-layer.py &amp;&amp; grep -q '\.claude/skills/mortgage-ops/modes/_profile.md' tests/test_block_user_layer.py &amp;&amp; grep -q '\.claude/skills/mortgage-ops/modes/_profile.md' DATA_CONTRACT.md &amp;&amp; ! grep -E '^\| `modes/_profile.md`' DATA_CONTRACT.md &amp;&amp; ! python3 scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md &amp;&amp; pytest tests/test_block_user_layer.py -q</automated>
  </verify>
  <acceptance_criteria>
- `.gitignore` contains `.claude/skills/mortgage-ops/modes/_profile.md`
- `scripts/hooks/block-user-layer.py` USER_LAYER_PATTERNS contains `.claude/skills/mortgage-ops/modes/_profile.md`
- `tests/test_block_user_layer.py` parametrize list contains BOTH the legacy `modes/_profile.md` AND the new `.claude/skills/mortgage-ops/modes/_profile.md` (Round-2 codex HIGH 3 + LOW 11)
- `pytest tests/test_block_user_layer.py -q` exits 0 (no regressions; new case passes)
- `DATA_CONTRACT.md` line 19 (or wherever) shows the corrected path
- The OLD path `modes/_profile.md` (project-root) is NOT enumerated as User Layer in DATA_CONTRACT.md
- End-to-end: `python3 scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md` exits non-zero with a message naming the offending file (Round-2 codex HIGH 3: hook MUST be invoked with the candidate path as argv, NOT with no args)
  </acceptance_criteria>
  <done>
    User Layer enforcement triple-check (gitignore + hook + contract) wired for skill-folder _profile.md.
  </done>
</task>

<task type="auto">
  <name>Task 4: Create 7 mode files (evaluate, compare, refinance, affordability, stress, amortize, arm)</name>
  <files>.claude/skills/mortgage-ops/modes/evaluate.md, .claude/skills/mortgage-ops/modes/compare.md, .claude/skills/mortgage-ops/modes/refinance.md, .claude/skills/mortgage-ops/modes/affordability.md, .claude/skills/mortgage-ops/modes/stress.md, .claude/skills/mortgage-ops/modes/amortize.md, .claude/skills/mortgage-ops/modes/arm.md</files>
  <read_first>
    10-UI-SPEC §b sample skeleton for `modes/amortize.md` (lift verbatim 4-section spine);
    10-UI-SPEC §a Routing UX (per-mode worked examples 1-14) — paste examples into each mode's "When to invoke";
    10-UI-SPEC §h Subagent Handoff UX (for modes/stress.md ONLY — Phase 11 forward-link);
    .claude/skills/mortgage-ops/scripts/amortize.py --help epilog (lines ~71-90) — JSON shape spec for modes/amortize.md;
    .claude/skills/mortgage-ops/scripts/affordability.py --help epilog (lines ~71-123) — JSON shape spec for modes/affordability.md;
    .claude/skills/mortgage-ops/scripts/arm_simulate.py --help epilog (lines ~33-59) — JSON shape spec for modes/arm.md
  </read_first>
  <action>
Create 7 mode files, each ≤ 200 lines (UI-SPEC density rule), following the 4-section spine from UI-SPEC §b VERBATIM.

For each mode, lift the example skeleton from UI-SPEC §b "Sample Skeleton: `modes/amortize.md`" and adapt by:
- Updating `# Mode: {name} — {one-line purpose}` (first line)
- Updating `## When to invoke` with examples from UI-SPEC §a routing table (use the per-mode examples as triggers)
- Updating `## What scripts to call` with the JSON shape from the script's `--help` epilog (run `python .claude/skills/mortgage-ops/scripts/{script}.py --help` and lift the JSON spec verbatim)
- Updating `## What to narrate` with the canonical "answer + provenance" template from UI-SPEC §g
- Updating `## Edge cases` with mode-specific empty-state errors (per UI-SPEC §"Copywriting Contract" empty-state copy)

Per-mode specifics:

modes/evaluate.md:
- Title: `# Mode: evaluate — Single-loan analysis (judgment + math)`
- Scripts: composes BOTH `.claude/skills/mortgage-ops/scripts/amortize.py` (P&I + monthly schedule) AND `.claude/skills/mortgage-ops/scripts/affordability.py` (DTI/LTV/CLTV/PITI + blocker precedence). The mode collects loan + household inputs, dispatches to amortize.py for the payment, then dispatches to affordability.py for the affordability angle. JSON outputs from both are merged into the narration template per UI-SPEC §g.
- Examples (from UI-SPEC §a row 1-2): "Should I lock the 6.5% rate Wells offered me on $400k?", "Is this 6.5% / 30yr offer any good?"
- The "evaluate" mode is the only mode that composes two CLIs. Other modes route to a single script. The `## What scripts to call` section MUST list BOTH amortize.py AND affordability.py with their respective JSON shapes.

modes/compare.md:
- Title: `# Mode: compare — Multi-offer ranking (2-5 offers side-by-side)`
- Scripts: invokes `.claude/skills/mortgage-ops/scripts/refi_npv.py` once per offer (Phase 6 SHIPPED per STATE.md; relocated by Plan 10-01).
- Examples (UI-SPEC §a rows 3-4)

modes/refinance.md:
- Title: `# Mode: refinance — Refi NPV decision (current vs new loan)`
- Scripts: `.claude/skills/mortgage-ops/scripts/refi_npv.py` (Phase 6 SHIPPED; relocated by Plan 10-01).
- Examples (UI-SPEC §a rows 5-6)
- AMBIGUITY rule from UI-SPEC §a Case 1: "If the prompt mentions both 'refi' and 'ARM', route HERE (refinance), pass loan_type='arm' + arm_terms to new-loan side; do NOT route to arm standalone."

modes/affordability.md:
- Title: `# Mode: affordability — DTI/LTV/CLTV/PITI + reverse-affordability`
- Scripts: `.claude/skills/mortgage-ops/scripts/affordability.py` (relocated by Plan 10-01)
- JSON shape: lift from `python .claude/skills/mortgage-ops/scripts/affordability.py --help` epilog (Phase 4 D-13 documented JSON shape — reuse verbatim)
- Examples (UI-SPEC §a rows 7-8)
- AMBIGUITY rule from UI-SPEC §a Case 2: "If user asks 'can I afford X *and* what's the payment', do NOT make two script calls — affordability.py response already includes monthly_pi + monthly_taxes + monthly_insurance + monthly_pmi + monthly_hoa."

modes/stress.md:
- Title: `# Mode: stress — Rate-shock / income-shock / ARM-path sweeps`
- Scripts: `.claude/skills/mortgage-ops/scripts/stress_test.py` (Phase 8 SHIPPED; relocated by Plan 10-01).
- Examples (UI-SPEC §a rows 9-10)
- **PHASE 11 FORWARD-LINK per LOCKED DECISION D-SUBA-FW-02** — MANDATORY in this mode file. Use the EXISTENCE-CHECK seam (NOT an unconditional dispatch):

  > For sweeps with N > 5 scenarios, defer to `.claude/agents/stress-test-agent.md` if it exists; otherwise run the stress sweep inline.
  >
  > User-visible behavior when the agent file exists (Phase 11 ships): one-line dispatch announcement → subagent runs in isolated context (intermediate token usage NOT in main chat) → subagent returns ≤ 1k token summary (SUBA-06).
  >
  > User-visible behavior when the agent file is absent (Phase 10 ship state, Phase 11 not yet landed): run the stress sweep inline using `.claude/skills/mortgage-ops/scripts/stress_test.py`. No dispatch boilerplate appears.
  >
  > For `scenario_count ≤ 5`, ALWAYS run inline regardless of whether the agent file exists; the context cost of dispatch is not justified.

- The mode body MUST contain the LITERAL substring `if it exists` AND the LITERAL path `.claude/agents/stress-test-agent.md`. Phase 11 lands by writing the agent file; modes/stress.md does NOT need a follow-up commit. Same routing logic either way.
- AMBIGUITY rule from UI-SPEC §a Case 3: "Stress + refinance collision → route to refinance, dispatch sweep as inner loop"

modes/amortize.md:
- Title: `# Mode: amortize — Generate an amortization schedule`
- Scripts: `.claude/skills/mortgage-ops/scripts/amortize.py` (relocated)
- JSON shape: lift from `--help` epilog (Phase 3 documented; biweekly mode, extra_principal list)
- Examples (UI-SPEC §a rows 11-12)

modes/arm.md:
- Title: `# Mode: arm — ARM modeling (5/1, 7/1, 10/1, 5/6 with caps + reset paths)`
- Scripts: `.claude/skills/mortgage-ops/scripts/arm_simulate.py` (relocated)
- JSON shape: lift from `--help` epilog (Phase 5 documented; index_path, applied_cap)
- Examples (UI-SPEC §a rows 13-14)

EVERY mode file MUST:
- Open with the line `Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.`
- Section spine in EXACT ORDER: When to invoke / What scripts to call / What to narrate / Edge cases
- End with a "RELATED REFERENCES" footer naming the references/*.md files this mode might trigger via progressive disclosure (per SKILL.md topic→reference table)

Token budget per mode file: ≤ 2000 cl100k tokens (UI-SPEC density rule).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for m in evaluate compare refinance affordability stress amortize arm; do test -f .claude/skills/mortgage-ops/modes/$m.md &amp;&amp; for h in "## When to invoke" "## What scripts to call" "## What to narrate" "## Edge cases"; do grep -q "$h" .claude/skills/mortgage-ops/modes/$m.md || { echo "MISSING $h in $m"; exit 1; }; done; done &amp;&amp; grep -q 'stress-test-agent' .claude/skills/mortgage-ops/modes/stress.md &amp;&amp; grep -q 'if it exists' .claude/skills/mortgage-ops/modes/stress.md &amp;&amp; grep -q '\.claude/agents/stress-test-agent\.md' .claude/skills/mortgage-ops/modes/stress.md &amp;&amp; grep -q 'affordability\.py' .claude/skills/mortgage-ops/modes/evaluate.md &amp;&amp; grep -q 'amortize\.py' .claude/skills/mortgage-ops/modes/evaluate.md</automated>
  </verify>
  <acceptance_criteria>
- All 7 mode files exist
- Each contains all 4 spine headings (When to invoke / What scripts to call / What to narrate / Edge cases)
- modes/stress.md contains the LITERAL phrase `if it exists` (D-SUBA-FW-02 existence-check seam)
- modes/stress.md contains the LITERAL path `.claude/agents/stress-test-agent.md` (D-SUBA-FW-02)
- modes/stress.md still mentions `stress-test-agent` (compatibility with prior wording)
- modes/evaluate.md mentions BOTH `affordability.py` AND `amortize.py` (dual-dispatch composition for DTI/LTV/CLTV/PITI alongside P&I)
- modes/refinance.md contains the refi+ARM ambiguity rule
- modes/affordability.md contains the affordability+amortize ambiguity rule
- modes/amortize.md mentions `.claude/skills/mortgage-ops/scripts/amortize.py` (relocated path)
- modes/affordability.md mentions `.claude/skills/mortgage-ops/scripts/affordability.py`
- modes/arm.md mentions `.claude/skills/mortgage-ops/scripts/arm_simulate.py`
- modes/refinance.md mentions `.claude/skills/mortgage-ops/scripts/refi_npv.py`
- modes/compare.md mentions `.claude/skills/mortgage-ops/scripts/refi_npv.py`
- modes/stress.md mentions `.claude/skills/mortgage-ops/scripts/stress_test.py`
- Each mode file ≤ 2500 cl100k tokens (run count_tokens loop)
  </acceptance_criteria>
  <done>
    7 mode files committed; all follow UI-SPEC §b spine; stress mode has Phase 11 forward-link.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| modes/_profile.md → User Layer | Single most sensitive file in skill folder; PII / personal defaults; commit = data leak |
| modes/_profile.example.md → System Layer | Schema only; if it accidentally contains real PII, leak via commit |
| modes/stress.md → Phase 11 SUBA-05 | Forward-link contract; if SUBA-05 lands without mode-file knowing about subagent dispatch, scenarios hit the main context window (token blowout) |
| modes/refinance.md + modes/arm.md ambiguity rule → SKILL.md routing precedence | If mode files contradict SKILL.md precedence table, Claude gets conflicting instructions |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-17 | Information Disclosure (PII commit via _profile.md) | gitignore + hook + DATA_CONTRACT triple-check | mitigate | Task 3 PART D end-to-end test exercises the hook; force-add must be rejected |
| T-10-18 | Tampering (real PII in _profile.example.md template) | Task 2 acceptance | mitigate | Task 2 acceptance "no real PII in template values" (placeholder values only) |
| T-10-19 | Information Disclosure (subagent dispatch missed → main context blowout) | modes/stress.md | mitigate | Task 4 acceptance asserts "stress-test-agent" + "scenario_count" substrings present |
| T-10-20 | Tampering (mode-file ↔ SKILL.md contradiction) | ambiguity rules | accept | Task 4 explicitly cross-references SKILL.md precedence table; manual review during plan-check ensures consistency. No automated catch in this wave; Wave 5 routing-substring assertions are the closest backstop. |
| T-10-21 | Tampering (DATA_CONTRACT.md sync drift) | hook + DATA_CONTRACT | mitigate | DATA_CONTRACT line 73-74 sync rule; Task 3 PART C explicitly updates both in same commit |
| T-10-39 | Tampering (D-PROF-01 schema drift) | _profile.example.md | mitigate | Task 2 acceptance asserts EXACTLY 4 top-level YAML keys; Wave 5 CI test_profile_example_md_has_exact_four_keys repeats the assertion in CI |
| T-10-40 | Tampering (D-13 Save Report invokes fictional CLI) | _shared.md | mitigate | Task 1 acceptance grep-asserts the literal `node orchestration/db-write.mjs insert-report --scenario-id` substring (REAL Phase 9 CLI per orchestration/db-write.mjs:296-310). Forbidden-substring grep blocks `--insert-report --json` + `db-write.mjs --query` + any reference to a `filename` column. Wave 5 flips test_report_filename_format + test_report_persisted_to_duckdb against the REAL CLI (Round-2 codex HIGH 2). |
| T-10-41 | Tampering (D-SUBA-FW-02 existence-check seam dropped) | modes/stress.md | mitigate | Task 4 acceptance grep-asserts literal `if it exists` AND literal path `.claude/agents/stress-test-agent.md`; Wave 5 CI repeats both substring assertions |
| T-10-42 | Tampering (D-NUM formatting rules missing) | _shared.md Output Formatting | mitigate | Task 1 acceptance grep-asserts D-NUM-01 / D-NUM-02 / D-NUM-03 / D-NUM-04 example tokens ($1,264.14 / 6.500% / 43.0% / bps) |
</threat_model>

<verification>
- 9 mode files exist (_shared, _profile.example, evaluate, compare, refinance, affordability, stress, amortize, arm)
- Each mode file has the 4-section spine
- _shared.md has 12 mandatory sections (9 UI-SPEC §i + Profile Loading + Output Formatting + Save Report per D-13/D-NUM/D-PROF-04)
- _shared.md contains `db-write.mjs insert-report --scenario-id` (D-13-04; REAL Phase 9 CLI — Round-2 codex HIGH 2) AND `save_report: false` (D-13-05) AND D-NUM-01..06 examples ($1,264.14 / 6.500% / 43.0% / bps); does NOT contain the fictional `--insert-report --json` or `db-write.mjs --query` flag forms
- _profile.example.md has EXACTLY 4 top-level YAML keys per D-PROF-01 (verbosity / citation_density / save_report / disambiguation); NO calc-input duplication per D-PROF-02
- modes/_profile.md is gitignored AND blocked by pre-commit hook AND enumerated in DATA_CONTRACT.md
- modes/stress.md uses D-SUBA-FW-02 existence-check (literal `if it exists` + literal `.claude/agents/stress-test-agent.md`)
- modes/evaluate.md dispatches to BOTH amortize.py AND affordability.py
- modes/refinance.md + modes/affordability.md have ambiguity-collision rules
</verification>

<success_criteria>
- 9 mode files written, committed
- 3 enforcement-config files updated (.gitignore + block-user-layer.py + DATA_CONTRACT.md)
- End-to-end User Layer enforcement test (force-add → hook rejection) passes
- All mode files fit token budget (≤ 2500 cl100k each)
- All mode files reference the relocated script paths (`.claude/skills/mortgage-ops/scripts/*`)
- D-13-01..D-13-05 closure: `_shared.md` Save Report step ships; SKLL-13 closes in Phase 10 (not deferred)
- D-PROF-01 + D-PROF-02 closure: `_profile.example.md` ships with exactly 4 keys
- D-SUBA-FW-02 closure: `modes/stress.md` carries existence-check seam
- D-NUM-01..06 closure: `_shared.md` Output Formatting section ships display directives
- modes/evaluate.md dispatches to BOTH amortize.py AND affordability.py
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-03-SUMMARY.md` documenting:
- 9 mode files written + line/token count per file
- 3 enforcement-config files edited + diff summary
- End-to-end force-add rejection test result
- Cross-link audit: which mode files reference which references/*.md files
- Phase 11 forward-link confirmation in modes/stress.md
- Confirmation that DATA_CONTRACT.md path correction lands in same commit as hook update
</output>
</content>
</invoke>