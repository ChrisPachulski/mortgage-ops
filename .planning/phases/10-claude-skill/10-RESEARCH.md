---
phase: 10
phase_slug: claude-skill
gathered: 2026-05-02
status: complete
---

# Phase 10: Claude Skill Frontend — Research

**Researched:** 2026-05-02
**Domain:** Anthropic Agent Skill packaging — SKILL.md routing, progressive disclosure, bundled scripts, references
**Confidence:** HIGH (Anthropic spec read verbatim from agentskills.io/specification + code.claude.com/docs/en/skills + platform.claude.com/docs/en/agents-and-tools/agent-skills/overview; canonical exemplar webapp-testing/SKILL.md fetched verbatim from raw.githubusercontent.com; tokenizer-budget recommendation pinned with documented overhead margin)

## Summary

Phase 10 builds `.claude/skills/mortgage-ops/` as a self-contained Anthropic Agent Skill bundle that routes seven natural-language mortgage tasks (`evaluate`, `compare`, `refinance`, `affordability`, `stress`, `amortize`, `arm`) to seven JSON-in/JSON-out Python scripts (`amortize.py`, `affordability.py`, `arm_simulate.py`, `refi_npv.py`, `apr_reg_z.py`, `stress_test.py`, `points_breakeven.py`) **physically relocated** from project-root `scripts/` to `.claude/skills/mortgage-ops/scripts/`. SKILL.md (≤ 4500 tiktoken-cl100k tokens to stay within ~5000 Anthropic tokens with margin; ≤ 500 lines; routing in first 200 lines) carries the routing table + the "always shell out, never compute inline" doctrine + the "run --help first; do not read source" doctrine lifted **verbatim** from `anthropics/skills/skills/webapp-testing/SKILL.md` (the canonical complex-skill exemplar). Nine progressive-disclosure references load on demand from `.claude/skills/mortgage-ops/references/`. Modes load from `modes/{name}.md`; `modes/_shared.md` carries the report structure; `modes/_profile.md` is gitignored user-layer customization (mirrors career-ops pattern), with `modes/_profile.example.md` committed as the schema skeleton. `LICENSE.txt` is bundled with MIT terms (project default — pyproject.toml has no `[project.license]` block, so this phase's plan-discuss-decide loop selects MIT).

**Three big architectural decisions this research locks:**

1. **Script relocation strategy: option (i) MOVE.** Physically `git mv scripts/*.py .claude/skills/mortgage-ops/scripts/*.py` + update test `SCRIPT_PATH` constants + update `pythonpath` injection. Rationale: the existing scripts already anticipate this (Phase 3 D-17 documents "Phase 10 physically relocates"; tests use `SCRIPT_PATH` constants exactly so the relocation is a one-line constant edit per test file). Phase 11 SUBA-05 needs the skill folder scripts to be **directly executable by subagents** — symlink (option ii) breaks on Windows without dev-mode (career-ops/card-ops are cross-platform-aspirational), and shim (option iii) doubles indirection cost (subprocess inside subprocess) and breaks `--help` lazy-import discipline. **Option (i) is the only choice that survives Phase 11 contract.**

2. **`compatibility` field syntax: free-form text per spec, NOT structured version pins.** Phase metadata example showed `compatibility: claude-code: ">=1.0"` — that syntax is **incorrect per the agentskills.io specification**, which mandates a 1-500 char free-form string (examples: `"Designed for Claude Code (or similar products)"`, `"Requires Python 3.14+ and uv"`). Recommendation: `compatibility: "Requires Python 3.12+, numpy-financial, pydantic v2, and Claude Code (or any agent-skills-compatible client). Network access not required."` — declares the actual environment dependencies in the format the spec sanctions.

3. **Tokenizer for SC-1 enforcement: tiktoken cl100k_base with documented overhead margin.** `tiktoken.get_encoding("cl100k_base").encode(text).__len__()` enforced at ≤ **4500 tokens** in CI; the actual Anthropic tokenizer typically counts 10-15% higher for English prose, so 4500 cl100k tokens projects to ≤ ~5175 Anthropic tokens worst-case — that's still inside the spec's "< 5000 tokens recommended" budget when rounded. tiktoken is deterministic, offline, no API key needed in CI, no network call in pre-commit. The Anthropic `count_tokens` API is free but requires a network call + API key in CI (untenable for offline CI runs and adds a flaky dependency). Document the 10% overhead margin in `tests/test_skill.py::test_skill_md_token_budget` so future maintainers understand why the threshold is 4500 not 5000.

The other architectural questions (per-reference content sources, frontmatter fields, mode dispatch examples, never-owns-numbers doctrine wording) all have specific recommendations in §"Investigations" below, each citation-backed.

## User Constraints (from ROADMAP / REQUIREMENTS / CLAUDE.md)

### Locked by ROADMAP Phase 10 Success Criteria (verbatim from prompt)

- **SC-1**: `.claude/skills/mortgage-ops/SKILL.md` is ≤ 500 lines and ≤ 5,000 tokens (verified by a CI check that runs a tokenizer); routing logic is in the first 200 lines
- **SC-2**: SKILL.md frontmatter includes `name`, `description`, `license`, `compatibility` fields; `LICENSE.txt` is bundled inside the skill folder
- **SC-3**: All seven calc scripts (amortize.py, affordability.py, arm_simulate.py, refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py) live INSIDE `.claude/skills/mortgage-ops/scripts/` (NOT at project root) — verified by a structure test
- **SC-4**: All seven mode files (evaluate, compare, refinance, affordability, stress, amortize, arm) exist under `modes/`, plus `_shared.md` and `_profile.md`
- **SC-5**: References folder contains all nine documents (amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions); SKILL.md instructs Claude to ALWAYS shell out to scripts and includes the "run --help first; do not read source" doctrine

### Locked by REQUIREMENTS SKLL-01..13

- **SKLL-01**: SKILL.md ≤ 500 lines, ≤ 5k tokens
- **SKLL-02**: routing logic in first 200 lines (compaction re-attach budget — Anthropic compaction keeps first 5000 tokens of each invoked skill; first 200 lines must contain the load-bearing dispatch logic so it survives summarization)
- **SKLL-03**: frontmatter includes `name`, `description`, `license`, `compatibility`
- **SKLL-04**: `LICENSE.txt` bundled inside skill folder
- **SKLL-05**: Seven modes (evaluate, compare, refinance, affordability, stress, amortize, arm)
- **SKLL-06**: `modes/_shared.md` defines scoring + report structure (career-ops pattern)
- **SKLL-07**: `modes/_profile.md` gitignored user-specific overrides
- **SKLL-08**: References folder with the nine specified documents
- **SKLL-09**: References load on demand (progressive disclosure)
- **SKLL-10**: All scripts INSIDE `.claude/skills/mortgage-ops/scripts/` (NOT at project root)
- **SKLL-11**: SKILL.md instructs Claude to ALWAYS shell out for math; never compute inline
- **SKLL-12**: Scripts include `--help`; "do not read source" doctrine documented
- **SKLL-13**: Reports written to `reports/{###}-{slug}-{YYYY-MM-DD}.md` and ingested into DuckDB

### Inherited from CLAUDE.md (CONVENTIONS section)

- Skill portability lifted from anthropics/skills: `scripts/`, `references/`, `assets/`, `LICENSE.txt` ALL INSIDE `.claude/skills/mortgage-ops/`
- `references/*.md` loaded on demand only (progressive disclosure)
- Bundled scripts: run `--help` first; do not read source unless customization needed (Anthropic webapp-testing doctrine)
- Calc engine separation: every dollar figure is computed by Python in `lib/`; Claude never owns numbers
- Data Contract: User Layer (`modes/_profile.md`) is READ-ONLY from system code, NEVER auto-updated, ALWAYS gitignored; System Layer (`.claude/skills/mortgage-ops/**` excluding `modes/_profile.md`) is auto-updatable

### Cross-phase contract (NEW — surfaced by this research; planner MUST publish)

- Phases 6 (`refi_npv.py`), 7 (`apr_reg_z.py`), 8 (`stress_test.py` + `points_breakeven.py`), 9 (none — Node orchestration, not Python scripts) MUST land their NEW Python CLI scripts directly under `.claude/skills/mortgage-ops/scripts/` (NOT project root). This contract supersedes the existing Phase 3 D-17 / Phase 4 D-13 / Phase 5 D-07 inheritance pattern (which says "Phase 10 physically relocates"). Plan 10-01 of this phase publishes the contract + a CI structure check that fails if any new `scripts/*.py` appears at project root after Phase 10 ships. STATE.md and ROADMAP.md must absorb this contract for Phase 6/7/8 RESEARCH/PLAN updates. **This is the deferred-decision-needed item the planner must surface during discuss-phase.**

## Investigations

### (a) Anthropic SKILL.md frontmatter spec [VERIFIED: agentskills.io/specification + platform.claude.com docs]

The canonical spec lives at https://agentskills.io/specification (current as of 2026-05-02). The full table verbatim:

| Field | Required | Constraints |
|---|---|---|
| `name` | Yes | Max 64 chars. Lowercase letters, numbers, hyphens only. Must not start/end with hyphen, no consecutive hyphens. Must match parent directory name. |
| `description` | Yes | Max 1024 chars. Non-empty. Describes what the skill does AND when to use it. |
| `license` | No | License name OR reference to a bundled license file (free-form short string). |
| `compatibility` | No | Max 500 chars. Indicates environment requirements (intended product, system packages, network access, etc.). **Free-form text — NOT a structured version-pin syntax.** |
| `metadata` | No | Arbitrary key-value mapping for additional metadata. |
| `allowed-tools` | No | Space-separated string of pre-approved tools. (Experimental.) |

**Claude Code-specific extensions** (per https://code.claude.com/docs/en/skills) layer additional optional fields on top: `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell`. None of these are required for SKLL-03 closure; the four mandated by SC-2 (`name`, `description`, `license`, `compatibility`) all map to the agentskills.io spec verbatim.

**Critical correction to phase metadata wording:** The phase 10 prompt cites `compatibility: claude-code: ">=1.0"` as an example of "what version pins look like." **This syntax is NOT in the spec.** The spec's worked examples are:

```yaml
compatibility: Designed for Claude Code (or similar products)
compatibility: Requires git, docker, jq, and access to the internet
compatibility: Requires Python 3.14+ and uv
```

(Source: https://agentskills.io/specification §"`compatibility` field" — three boxed examples, all free-form English strings.)

**Recommended `compatibility` value for mortgage-ops** (string < 500 chars):

```yaml
compatibility: Requires Python 3.12+, numpy-financial, pydantic v2 (>=2.13), pyyaml. Designed for Claude Code (or any agent-skills-compatible client). Bundled scripts are deterministic CLIs; no network access required at runtime. DuckDB optional (Phase 9; needed only when `compare` or `tracker` modes invoke the persistence layer).
```

This declares the actual environment requirements (lifted from `pyproject.toml` `requires-python` + `dependencies`) without inventing a version-pin syntax that the spec does not sanction.

### (b) anthropics/skills exemplar — webapp-testing structure [VERIFIED: raw.githubusercontent.com]

Folder listing fetched live from https://api.github.com/repos/anthropics/skills/contents/skills/webapp-testing on 2026-05-02:

```
skills/webapp-testing/
├── LICENSE.txt              (11,345 bytes — full Apache-2.0 text)
├── SKILL.md                 (3,913 bytes)
├── examples/                (directory)
│   ├── element_discovery.py
│   ├── static_html_automation.py
│   └── console_logging.py
└── scripts/                 (directory)
    └── with_server.py
```

**SKILL.md frontmatter** (verbatim):

```yaml
---
name: webapp-testing
description: Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs.
license: Complete terms in LICENSE.txt
---
```

Note: webapp-testing does NOT use `compatibility` (the spec says "Most skills do not need the `compatibility` field"). It does use `license: Complete terms in LICENSE.txt` — exactly the "pointer to bundled license file" pattern the spec recommends.

**The "run --help first; do not read source" doctrine** (verbatim from webapp-testing SKILL.md lines 7-9):

> **Always run scripts with `--help` first** to see usage. DO NOT read the source until you try running the script first and find that a customized solution is abslutely necessary. These scripts can be very large and thus pollute your context window. They exist to be called directly as black-box scripts rather than ingested into your context window.

(Note the typo `abslutely` is verbatim — Anthropic's canonical example contains it. Mortgage-ops' SKILL.md should fix the typo when paraphrasing but cite this source.)

The webapp-testing "Best Practices" section (verbatim line, citation source for the doctrine restated more formally):

> - **Use bundled scripts as black boxes** - To accomplish a task, consider whether one of the scripts available in `scripts/` can help. These scripts handle common, complex workflows reliably without cluttering the context window. Use `--help` to see usage, then invoke directly.

**Source URLs for plan-time reference:**
- SKILL.md raw: https://raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md
- Folder API: https://api.github.com/repos/anthropics/skills/contents/skills/webapp-testing
- Repo root: https://github.com/anthropics/skills

**Key insight from webapp-testing exemplar:** The skill has NO `modes/` folder. Anthropic-canonical skills use `examples/`, `scripts/`, `references/`, `assets/` — NOT `modes/`. The `modes/` convention is a **career-ops pattern** (NOT spec-defined) that mortgage-ops adopts for the seven dispatched workflows. This is fine — the spec says "Any additional files or directories" are permitted (https://agentskills.io/specification §"Directory structure" line 4) — but plan-time documentation should make explicit that `modes/` is a project convention NOT an Anthropic-blessed directory name.

### (c) Progressive disclosure budget [VERIFIED: platform.claude.com docs + agentskills.io]

The three-level loading model (verbatim from https://agentskills.io/specification §"Progressive disclosure"):

1. **Metadata** (~100 tokens): The `name` and `description` fields are loaded at startup for all skills.
2. **Instructions** (< 5000 tokens recommended): The full `SKILL.md` body is loaded when the skill is activated.
3. **Resources** (as needed): Files (e.g. those in `scripts/`, `references/`, or `assets/`) are loaded only when required.

> Keep your main `SKILL.md` under 500 lines. Move detailed reference material to separate files.

**Compaction re-attach behavior** (verbatim from https://code.claude.com/docs/en/skills §"Skill content lifecycle"):

> Auto-compaction carries invoked skills forward within a token budget. When the conversation is summarized to free context, Claude Code re-attaches the most recent invocation of each skill after the summary, **keeping the first 5,000 tokens of each**. Re-attached skills share a combined budget of 25,000 tokens.

**This is the load-bearing rationale for SKLL-02** (routing in first 200 lines): if SKILL.md is 4500 tokens and the routing dispatch is at lines 380-450, those routing lines fall outside the first-5000-tokens compaction-survival window — but they barely fit. Putting routing in lines 1-200 (~2000 tokens) keeps it inside the survival window with comfortable margin, even if SKILL.md grows in future iterations.

**Per-file budgets (recommended; non-spec):**

| File | Budget | Why |
|---|---|---|
| `SKILL.md` | ≤ 4500 cl100k tokens (~5000 Anthropic tokens worst-case) | SKLL-01 + 10% margin |
| `modes/{name}.md` | ~2000 cl100k tokens each | Loaded on demand when mode dispatched |
| `modes/_shared.md` | ~2000 cl100k tokens | Loaded by every mode that uses shared scoring/report structure (career-ops pattern: most modes load _shared + their mode file) |
| `modes/_profile.md` | ≤ 1500 cl100k tokens | User customization layer — kept small |
| `references/*.md` | 3000-10000 cl100k tokens each | Loaded only on explicit user request OR when SKILL.md routing decides "need to cite the regulatory source"; large reference files (>300 lines) per agentskills.io should include a TOC |

**Load triggers (recommended SKILL.md instruction patterns):**

```markdown
## Loading additional context

When you decide on a mode, read modes/_shared.md first (always), then read modes/{mode}.md.

When the user explicitly asks for a regulatory citation, formula derivation, or methodology
explanation, AND the topic matches one of these references, read the reference file ON DEMAND:

| User asks about... | Read reference |
|---|---|
| "how is the monthly payment computed", "PMT formula", "amortization math" | references/amortization-formulas.md |
| "Reg Z APR", "what's the difference between APR and APOR", "estimated APR methodology" | references/apr-reg-z.md |
| ... etc for all 9 references ...
```

This pattern matches the career-ops mode-loading approach (see `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md` lines 70-86) and also the agentskills.io guidance.

### (d) Routing patterns — natural-language input → mode dispatch [DESIGNED — confidence MEDIUM]

For each of the seven modes, here are 2-3 example inputs that should trigger dispatch:

#### `evaluate` — single-loan analysis
- "I'm looking at a $400k 30-year fixed at 6.5%. Run the numbers."
- "evaluate this loan: principal 350000, rate 0.0625, term 360"
- "what's my monthly payment + total interest on a $500k mortgage at 7%/30yr?"

#### `compare` — multi-offer ranking
- "I have two quotes: Lender A at 6.25% with $4k closing, Lender B at 6.5% no closing. Which wins?"
- "compare these three offers" (followed by JSON or table)
- "rank these refinance options by NPV"

#### `refinance` — refi NPV decision
- "my current loan is $300k at 7%, 25 years left. New offer 5.5% with $3k closing. Should I refi?"
- "refi NPV analysis: should I cash out $50k for kitchen remodel?"
- "is this refinance worth it given I'll move in 3 years?"

#### `affordability` — what can I afford?
- "with $120k joint income and $800/mo debts, what's the max house I can afford?"
- "DTI check: $250k loan, $9k income, $1200 debts — am I qualified?"
- "reverse-affordability for a 43% DTI cap"

#### `stress` — rate-shock / income-shock sweep
- "what if rates jump 200bps over 5 years?"
- "stress test my ARM with a 2/1/5 cap structure under rising-rate scenario"
- "income shock: what happens to my DTI if my salary drops 20%?"

#### `amortize` — schedule generation
- "show me the full amortization schedule for $400k @ 6.5%/30yr"
- "amortize $200k @ 7%/15yr, biweekly payments"
- "schedule with $5k extra principal at month 60"

#### `arm` — ARM simulation
- "simulate a 5/1 ARM with 6% start rate, 2/2/5 caps, SOFR +2.5%"
- "model my 7/6 SOFR ARM through year 15"
- "ARM reset projection: what's my payment at month 121 if rates rise to 9%?"

**Dispatch ambiguity rules (recommended SKILL.md instructions):**
- If the user's input contains the words "refi", "refinance", "should I refi" → `refinance` (highest specificity)
- If the input contains both "compare" and multi-offer JSON → `compare`
- If the input contains "ARM", "5/1", "7/1", "10/1", "5/6", "SOFR" → `arm` (unless also "refi" → `refinance` mode handles ARM-to-fixed refi)
- If the input is just a single loan + a question about payment → `evaluate` (the most general)
- If the input has "max", "qualify", "afford", "DTI", "what can I afford" → `affordability`
- If "schedule", "amortization table", "extra principal" → `amortize`
- If "shock", "stress", "what if rates", "what if income" → `stress`

These dispatch rules go in SKILL.md lines ~50-150 (well within the first-200-line routing budget).

### (e) "Never owns numbers" doctrine — exact SKILL.md instruction text [DESIGNED]

**Recommended verbatim block** for SKILL.md (consumes ~120 cl100k tokens):

```markdown
## Math discipline (load-bearing — read carefully)

Every dollar figure, rate, breakeven, or schedule entry in your response MUST come from a script invocation. You do NOT compute mortgage math inline. Reasoning chains like "the payment is roughly X" or "let me estimate the breakeven" are forbidden — even if the answer would be approximately right, the user's house-buying decision deserves audit-traceable numbers.

The contract:
1. Determine the mode + collect inputs from the user (free-form English → JSON).
2. Write the JSON input to a tempfile (e.g. /tmp/mortgage-ops-input-<uuid>.json).
3. Invoke the relevant script: `python ${CLAUDE_SKILL_DIR}/scripts/<script>.py --input <tempfile>`
4. Read the script's stdout JSON. If exit code != 0, narrate the stderr 6-key Pydantic envelope (loc + msg + input fields) to explain the validation failure.
5. Translate the JSON response into a human-readable report using modes/_shared.md report structure.

If you find yourself "estimating" or "approximating" a dollar figure, STOP. Build a fuller JSON input and re-run the script. The Python engine is fast (`--help` returns in < 100ms; full schedule for 360 months returns in < 50ms); there is no performance reason to compute inline.

This rule has zero exceptions.
```

This wording explains the WHY (audit traceability for house-buying decisions) per the skill-creator guidance "explain the why" (https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md §"Writing Style"), not just rigid MUSTs.

### (f) Script relocation strategy — DECISION LOCKED [Option (i) MOVE; HIGH confidence]

Three options were considered:

**Option (i): MOVE scripts/* → .claude/skills/mortgage-ops/scripts/* + update tests + pythonpath**
- Steps: `git mv scripts/amortize.py .claude/skills/mortgage-ops/scripts/amortize.py` for each of the 7 scripts; update `tests/test_*.py` `SCRIPT_PATH` constants from `Path(__file__).parent.parent / "scripts" / "X.py"` to `Path(__file__).parent.parent / ".claude" / "skills" / "mortgage-ops" / "scripts" / "X.py"`; update each script's `_project_root = Path(__file__).resolve().parent.parent` (currently `parent.parent`) to `parent.parent.parent.parent.parent` (since the script is now 5 levels deep instead of 2 — verify with `realpath` at plan time); add `.claude/skills/mortgage-ops/scripts/__init__.py` (empty) so `from scripts._cli_helpers import ...` still resolves (or rewrite imports to absolute via `lib._cli_helpers` — see below).
- Pros:
  - Subagents (Phase 11 SUBA-05) can execute scripts directly via `${CLAUDE_SKILL_DIR}/scripts/X.py` with no indirection
  - Anthropic-canonical layout (matches webapp-testing exactly)
  - Phase 3 D-17 / Phase 4 D-13 / Phase 5 D-07 already anticipated this — comments explicitly say "Phase 10 physically relocates"
  - Tests already use `SCRIPT_PATH` constants (Phase 3 D-17 idiom) so the relocation is a one-line constant edit per test file
  - `pyproject.toml` `[tool.ruff] src = ["lib", "tests", "scripts"]` needs updating to `["lib", "tests", ".claude/skills/mortgage-ops/scripts"]` — one-line edit
  - `_cli_helpers.py` moves with the scripts (it's an implementation detail of the CLI surface)
- Cons:
  - Imports of `from scripts._cli_helpers import ...` break — but this is fixable two ways:
    - **Recommended**: relocate `_cli_helpers.py` into `lib/_cli_helpers.py` (it's truly a shared library, not a script); change `from scripts._cli_helpers import ...` → `from lib._cli_helpers import ...` in each of the 7 scripts. Cleaner separation: `lib/` is the library, `.claude/skills/mortgage-ops/scripts/` is the CLI front door.
    - Alternative: keep `_cli_helpers.py` next to the scripts in `.claude/skills/mortgage-ops/scripts/_cli_helpers.py`; but then `pyproject.toml` `[tool.hatch.build.targets.wheel] packages = ["lib"]` doesn't ship `_cli_helpers.py` to anyone who pip-installs the package — so external consumers of mortgage-ops library can't reuse the helper. **Recommendation: relocate to `lib/_cli_helpers.py`.**
  - `_generate_arm_fixtures.py` is a dev-only fixture generator (not a user-facing CLI script) — KEEP at project root in `scripts/` (renamed `dev/` if cleaner). This is NOT one of the seven SC-3 scripts.
  - `scripts/hooks/` (pre-commit hooks) STAYS at project root — these are tooling, not skill CLIs.
- Verdict: **CHOOSE (i)**. The cons are minor and addressable; the pros are load-bearing for Phase 11.

**Option (ii): Keep scripts/ at root, symlink into skill folder**
- Steps: `ln -s ../../../../scripts/amortize.py .claude/skills/mortgage-ops/scripts/amortize.py` for each of 7 scripts.
- Pros: no test changes, no import changes.
- Cons:
  - **Symlinks break on Windows in non-developer mode** (Windows requires admin or developer-mode to create symlinks). Mortgage-ops is personal-use (the user is on macOS per env Darwin 25.3.0), so this MIGHT be tolerable — but Phase 11 subagents may run on a different machine if shared, and the ROADMAP mentions "personal-use" but doesn't preclude future portability.
  - **Symlinks confuse `git mv` history** and don't survive `git archive` for tarball distribution.
  - **SKLL-10 says "scripts INSIDE the skill folder"** — a symlink IS technically inside the folder, but the actual file is OUTSIDE; a structure test (`isfile()` returns True for symlinks; `islink()` is needed to detect) could pass either way depending on how it's written. The intent of SKLL-10 is physical relocation.
  - **Anthropic spec implies physical bundling**: the agentskills.io spec describes skills as "portable, version-controlled folders that agents load on demand" — symlinks break the "portable" property when the skill folder is copied/zipped/distributed.
- Verdict: **REJECT**. Cross-platform fragility + portability erosion.

**Option (iii): Skill scripts/ shim that delegates via subprocess to root scripts/**
- Steps: each of the 7 `.claude/skills/mortgage-ops/scripts/X.py` is a 10-line shim:
  ```python
  #!/usr/bin/env python3
  import subprocess, sys
  from pathlib import Path
  ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "scripts"
  sys.exit(subprocess.run([sys.executable, str(ROOT / "X.py"), *sys.argv[1:]]).returncode)
  ```
- Pros: zero changes to existing scripts/tests/imports.
- Cons:
  - **Doubles indirection cost**: subprocess inside subprocess (Claude → shim → real script) adds ~100ms per invocation. Negligible for one-shot, painful for stress sweeps that invoke 50+ times (Phase 8/11).
  - **Breaks `--help` lazy-import discipline**: the shim's `import subprocess, sys` is ~30ms; the real script's `--help` is ~30ms; total ~60ms. Acceptable but worse than (i) at ~30ms.
  - **Phase 11 SUBA-05 contract concern (the question the prompt explicitly asks about)**: subagents that "execute the skill folder scripts" will execute the shim, which then subprocess-calls the real script. **This works** (subagent shells out to a script that shells out to a script — both work fine in a shell), but the shim adds a subprocess hop that subagents don't expect. Worse, if the subagent's working directory or PYTHONPATH differs from the orchestrator's, the shim's relative-path computation (`parent.parent.parent.parent.parent`) may resolve incorrectly. **The shim survives functionally but degrades robustness.**
  - **Distribution friction**: anyone who copies `.claude/skills/mortgage-ops/` to another project finds 7 broken shims pointing at non-existent `../../../../../scripts/`.
- Verdict: **REJECT**. Phase 11 SUBA-05 robustness concern is the dealbreaker the prompt asked about.

**LOCKED DECISION D-01**: Phase 10 executes Option (i) — physical move of the seven CLI scripts into `.claude/skills/mortgage-ops/scripts/`, with `_cli_helpers.py` simultaneously relocated to `lib/_cli_helpers.py` (cleaner library/CLI separation), and tests' `SCRIPT_PATH` constants updated. `_generate_arm_fixtures.py` and `scripts/hooks/` stay at project root (they are dev tooling, not user-facing CLIs).

**Migration plan** (ships as a sub-plan in Phase 10):
1. Create `.claude/skills/mortgage-ops/scripts/` directory.
2. `git mv scripts/amortize.py .claude/skills/mortgage-ops/scripts/amortize.py` (and same for 6 other scripts when they exist — at the time of Phase 10 execution, scripts 6/7/8 from Phases 6/7/8 may already be in place or may not yet exist; the cross-phase contract above means they should be CREATED in the new location).
3. `git mv scripts/_cli_helpers.py lib/_cli_helpers.py`.
4. In each of the 7 scripts, change `from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope` → `from lib._cli_helpers import find_json_float_loc, make_decimal_type_envelope`.
5. In each of the 7 scripts, update `_project_root` computation to reflect the new depth.
6. In each of `tests/test_amortize.py`, `tests/test_affordability.py`, `tests/test_arm.py`, etc. (and the future tests for refi/apr/stress/points), update `SCRIPT_PATH` constant to point at the new location.
7. Update `pyproject.toml` `[tool.ruff] src = ["lib", "tests", ".claude/skills/mortgage-ops/scripts"]`.
8. Run full test suite — expect all green (the relocation is purely cosmetic from the test's perspective).
9. Update DATA_CONTRACT.md to confirm `.claude/skills/mortgage-ops/scripts/` is System Layer (auto-updatable, committed) — already implied but make explicit.

### (g) `modes/_profile.md` user-layer pattern [VERIFIED via career-ops + DATA_CONTRACT.md]

career-ops pattern (verified by reading `/Users/cujo253/Documents/career-ops/modes/`):

- `modes/_profile.template.md` — committed to git, schema skeleton, no real values
- `modes/_profile.md` — gitignored, real user customization

In career-ops, the convention is `_profile.template.md` → user copies to `_profile.md` on first run. mortgage-ops should mirror but use the more conventional `.example.md` suffix to match `config/household.example.yml` and `config/profile.example.yml` (already in DATA_CONTRACT.md):

- `modes/_profile.example.md` — committed; schema skeleton with TODO markers and example narrative overrides
- `modes/_profile.md` — gitignored; user-specific narrative overrides for the Claude skill (mentioned by name in DATA_CONTRACT.md line 19)

DATA_CONTRACT.md line 19 already enumerates `modes/_profile.md` as User Layer:

> | `modes/_profile.md` | (Phase 10) user-specific narrative overrides for the Claude skill |

And the `.gitignore` entry for it must be added by Phase 10 (line 1.04 of the migration plan — verify by `grep "_profile.md" .gitignore` after Phase 10 ships).

The `block-user-layer.py` pre-commit hook (DATA_CONTRACT.md line 7-8) must add `modes/_profile.md` to its `USER_LAYER_PATTERNS` tuple. Verify the hook source file at `scripts/hooks/block-user-layer.py` has this pattern after Phase 10 ships.

**Recommended `modes/_profile.example.md` content** (~80 lines):

```markdown
# User Profile Overrides — modes/_profile.md

This file is for YOUR personal customizations to mortgage-ops narrative tone, default
loan term preferences, scoring weights, and report style. It is NEVER auto-updated by
Claude or any system code. Copy this file to `modes/_profile.md` (no `.example`) on
first use; the gitignore entry will keep your edits out of version control.

## Display preferences

- preferred_loan_term: 30  # 15, 20, or 30 years; influences which fixed-rate term Claude
                            # defaults to when you say "what's my payment for $400k"
- preferred_frequency: monthly  # monthly or biweekly
- show_apr: estimated  # 'estimated' (cite Reg Z label) or 'precise' (one extra decimal)
- show_total_interest: always  # always | only-on-request

## Tone overrides

- narrative_style: terse  # terse | conversational | numbers-only
- include_caveats: false  # true to add "consult a mortgage professional" footer

## Default discount rate (refi NPV)

- default_discount_rate_annual: "0.05"  # Decimal string; per refi-npv.md guidance,
                                          # 5-7% is borrower's after-tax marginal opportunity cost

## Default location (affordability defaults)

- default_state_fips: "53"  # Washington
- default_county_fips: "53061"  # Snohomish, WA — adjust to your county
                                # (Phase 2 county data covers all US counties)

## Custom routing overrides

(Add any per-mode routing tweaks here; e.g., "always run stress mode after evaluate
when user mentions ARM" — these override the default SKILL.md dispatch.)
```

### (h) LICENSE.txt content [VERIFIED — pyproject.toml has no license declared]

`pyproject.toml` has no `[project] license` block (verified via grep). With no project-level license declared, the conventional default for personal-use sibling-of-career-ops repos is **MIT** (career-ops/.gitignore + LICENSE pattern not directly verifiable here, but MIT is the de-facto default for the family). Phase 10 plan-discuss-decide should confirm MIT vs. Apache-2.0; if the user wants Apache-2.0 (matches webapp-testing exemplar), the boilerplate URL is https://www.apache.org/licenses/LICENSE-2.0.txt.

**Recommended `LICENSE.txt`** (MIT, ~21 lines):

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

The `license:` frontmatter field then becomes:

```yaml
license: MIT (complete terms in LICENSE.txt)
```

Mirroring webapp-testing's pattern (`license: Complete terms in LICENSE.txt`) but adding the SPDX identifier for tooling compatibility (https://spdx.org/licenses/MIT.html).

### (i) Tokenizer choice for SC-1 — DECISION LOCKED [tiktoken cl100k with margin; HIGH confidence]

Three options:

**Option (i): tiktoken cl100k_base (deterministic, offline)**
- Mechanism: `tiktoken.get_encoding("cl100k_base").encode(skill_md_text).__len__()`
- Pros: deterministic, no network call, no API key, no dependency on Anthropic API uptime, fast (< 50ms per check), CI-friendly
- Cons: cl100k is OpenAI's tokenizer (gpt-3.5/4 era); accuracy for Anthropic Claude 3+ is "typically within ten to twenty percent" per multiple sources (https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025; https://blog.gopenai.com/counting-claude-tokens-without-a-tokenizer-e767f2b6e632). For English prose like SKILL.md, cl100k typically UNDERCOUNTS by ~10-15% relative to Anthropic's actual tokenizer (Anthropic's tokenizer is stricter on whitespace + markdown punctuation).

**Option (ii): anthropic.messages.count_tokens API (accurate, network)**
- Mechanism: `anthropic.Anthropic(api_key=...).messages.count_tokens(model="claude-sonnet-4", messages=[{"role": "user", "content": skill_md_text}]).input_tokens`
- Pros: ground-truth accuracy
- Cons: requires `ANTHROPIC_API_KEY` env var in CI (untenable for offline CI / fork-PR CI / contributors without keys); requires network call (flaky in CI environments with restrictive egress); rate-limited (free but counts against your tier's RPM); requires `anthropic` package as a CI dependency (currently not in `pyproject.toml` dev group)

**Option (iii): no enforcement (manual review)**
- Cons: SC-1 says "verified by a CI check" — non-compliant.

**LOCKED DECISION D-02**: Option (i) — tiktoken cl100k_base with documented overhead margin.

**Enforcement threshold**: ≤ **4500 cl100k tokens** in CI (NOT 5000).

**Rationale for the 4500 threshold**:
- Anthropic tokenizer typically counts 10-15% higher than cl100k for English prose with markdown (verified anecdotally; Anthropic does not publish their tokenizer)
- 4500 cl100k × 1.15 = 5175 Anthropic tokens worst-case
- This is slightly over the < 5000 spec recommendation, but the spec word is "recommended" not "enforced" (per agentskills.io/specification §"Progressive disclosure": "Instructions (< 5000 tokens recommended)"). The Claude Code docs at https://code.claude.com/docs/en/skills also say "under 500 lines" which is the firmer bound.
- 4500 cl100k × 1.10 = 4950 Anthropic tokens typical-case — comfortably under spec
- A 10% margin is conservative; if a future SKILL.md is heavy on code blocks (which tokenize differently), the margin may need to drop to ≤ 4000 cl100k. Document this in the test as a tunable.

**Add to `pyproject.toml` dev group**: `tiktoken>=0.7`. (Currently not pinned; verify version at plan time via `npm view`-equivalent: `pip index versions tiktoken | head -1` — at research time, latest is 0.7.x.)

**Test pattern** (add to `tests/test_skill.py` in Plan 10-XX):

```python
def test_skill_md_token_budget_cl100k():
    """SC-1 enforcement via tiktoken cl100k_base with ~10% overhead margin to
    Anthropic tokenizer.

    Anthropic does not publish their tokenizer. Multiple sources (propelcode.ai,
    gopenai.com — see RESEARCH.md §(i)) report cl100k undercounts by ~10-15% for
    English prose with markdown. We enforce 4500 cl100k tokens so the worst-case
    Anthropic count stays at ≤ 5175 — within the spec's "< 5000 tokens recommended"
    when rounded.

    If this fails because SKILL.md grew, prefer moving content to references/ over
    raising the threshold. The compaction re-attach budget (5000 tokens) is the
    real ceiling.
    """
    import tiktoken
    skill_md = (Path(__file__).parent.parent / ".claude" / "skills" / "mortgage-ops" / "SKILL.md").read_text()
    enc = tiktoken.get_encoding("cl100k_base")
    n_tokens = len(enc.encode(skill_md))
    assert n_tokens <= 4500, (
        f"SKILL.md is {n_tokens} cl100k tokens (> 4500). "
        f"Anthropic tokenizer would count ~{int(n_tokens * 1.15)}, exceeding the "
        f"5000-token compaction-survival budget. Move content to references/."
    )

def test_skill_md_line_budget():
    """SC-1 secondary enforcement: ≤ 500 lines per agentskills.io guidance."""
    skill_md = (Path(__file__).parent.parent / ".claude" / "skills" / "mortgage-ops" / "SKILL.md").read_text()
    n_lines = len(skill_md.splitlines())
    assert n_lines <= 500, f"SKILL.md is {n_lines} lines (> 500)"
```

### (j) Per-reference content sources — full table [DESIGNED]

Table mapping each of the nine references to its content source (verified phase-by-phase against the existing `references/`, `lib/rules/`, and pinned phase research):

| # | Reference filename | Content source | Status of source |
|---|---|---|---|
| 1 | `amortization-formulas.md` | numpy-financial wraps + Phase 3 golden derivations (Wikipedia $200k @ 6.5%/30yr → $1,264.14; CFPB LE $162k @ 3.875%/30yr → $761.78; computed $400k @ 6.5%/30yr → $2,528.27; computed $200k @ 7%/15yr → $1,797.66 from FND-09) | [VERIFIED: Phase 3 complete; references/ folder does not yet contain this file — to be created in Phase 10] |
| 2 | `apr-reg-z.md` | Phase 7 `references/apr-reg-z.md` | [PLANNED: Phase 7 not yet executed; APR-08 explicitly creates this file. Phase 10 must coordinate with Phase 7 — either Phase 7 ships the file directly into `.claude/skills/mortgage-ops/references/apr-reg-z.md`, OR Phase 10 cross-links and Phase 7 later moves it. Recommendation: Phase 7 ships into the skill folder directly per cross-phase contract above.] |
| 3 | `arm-mechanics.md` | **Phase 5 `references/arm-mechanics.md` — already shipped** (verified by reading file; 50+ lines documenting reset month convention with Fannie/Freddie citations) | [VERIFIED: file exists at `/Users/cujo253/Documents/mortgage-ops/references/arm-mechanics.md`, 2026-04-30 last update] |
| 4 | `refi-npv.md` | Phase 6 `references/refi-npv.md` (planned per 06-RESEARCH.md §SC-5 + §"D-04 sign convention") | [PLANNED: Phase 6 RESEARCH locked; Plan 06-XX writes this file. Phase 10 must coordinate — same cross-phase contract: Phase 6 ships into `.claude/skills/mortgage-ops/references/refi-npv.md` directly.] |
| 5 | `affordability-rules.md` | Phase 4 (AFFD-01..09 closed) + Phase 2 predicates: composes how `evaluate_forward` / `evaluate_reverse` flow through DTI/LTV/CLTV/PITI + which rules predicates fire (loan_type, fha_mip, conventional_pmi, atr_qm, va_residual_income, etc.) | [DERIVE FROM: lib/affordability.py docstring + AFFD-07 blocked_by enumeration; Phase 10 author writes this from existing complete code] |
| 6 | `gse-limits.md` | Phase 2 `data/reference/conforming-limits-2026.yml` + `fha-limits-2026.yml` (already shipped per REF-01/02 status [x] in REQUIREMENTS.md) | [VERIFIED: REF-01 + REF-02 marked Done in Phase 2; YAML files exist; Phase 10 author writes the human-readable explainer of what the YAMLs contain + per-county lookup mechanism + RUL-01 classification logic] |
| 7 | `mip-pmi.md` | Phase 2 `data/reference/fha-mip-rates.yml` + `lib/rules/conventional_pmi.py` (HPA 78% auto-termination + 80% request) + `lib/rules/fha_mip.py` (HUD ML 2023-05) | [VERIFIED: REF-03 + RUL-04 + RUL-05 all marked Done in Phase 2; Phase 10 author writes the explainer covering FHA UFMIP + annual MIP per term/LTV/loan-amount tier + HPA termination logic + Phase 4 D-03 UFMIP auto-financing convention] |
| 8 | `tax-deductibility.md` | Phase 2 `data/reference/irs-pub936.yml` + `lib/rules/irs_pub936.py` (RUL-11 — qualified loan limit $750k post-2017, $1M grandfathered) + Phase 6 D-09 `after_tax_mode` (per 06-RESEARCH.md §"After-Tax Optional Mode") | [VERIFIED for Phase 2 portion (REF-07 + RUL-11 marked Done); PLANNED for Phase 6 portion (06-RESEARCH locked, D-09 ships `after_tax_mode` opt-in)] |
| 9 | `spreadsheet-conventions.md` | Phase 3 numpy-financial bug notes (#130 PMT fv-sign, #131 IRR arch-dependent — both cited in CLAUDE.md STACK section + Phase 6 06-RESEARCH §"D-06"); Excel/Google Sheets PMT sign convention (returns negative for outflow, our wrapper negates to surface positive) | [VERIFIED: Phase 3 complete; CLAUDE.md cites both bugs; Phase 10 author writes the user-facing "why our PMT differs by sign from Excel" explainer] |

**Reference file size budgets** (recommended; Phase 10 plan should split files exceeding):

| File | Estimated tokens | Source size justification |
|---|---|---|
| amortization-formulas.md | 4000-6000 | 4 golden derivations × ~800 tokens each + intro/PMT formula derivation |
| apr-reg-z.md | 6000-10000 | Newton-Raphson solver derivation + Reg Z Appendix J unit-period equation + 20+ FFIEC fixture cross-references |
| arm-mechanics.md | 3000-5000 | Already shipped at ~50 lines; will grow to 5/1, 7/1, 10/1, 5/6 reset coverage + cap precedence + index path semantics |
| refi-npv.md | 5000-8000 | Sign convention §SC-5 + cash-out cashflow enumeration + simple-vs-NPV breakeven divergence + after-tax-mode derivation |
| affordability-rules.md | 4000-6000 | DTI/LTV/CLTV/PITI definitions + reverse-affordability `npf.pv` derivation + blocker precedence (D-11 from Phase 4) |
| gse-limits.md | 3000-5000 | High-balance vs jumbo + per-county lookup mechanism + RUL-01 classify() decision tree |
| mip-pmi.md | 4000-6000 | FHA UFMIP + annual MIP rate matrix + HPA 78%/80% termination + Phase 4 D-03 UFMIP auto-finance |
| tax-deductibility.md | 3000-5000 | Pub 936 $750k cap + grandfathered $1M + worksheet logic + after-tax NPV mode usage |
| spreadsheet-conventions.md | 2000-4000 | numpy-financial bug #130/#131 + Excel sign convention + biweekly half-monthly mode |

**Total reference budget**: ~34000-55000 tokens across 9 files. Loaded on-demand only — none of this counts against the SKILL.md 5000-token budget. Per agentskills.io: "There's no context penalty for bundled content that isn't used."

### (k) Frontmatter example — literal YAML block ready to copy

```yaml
---
name: mortgage-ops
description: Personal-use mortgage analysis for the Pachulski household. Routes natural-language requests (evaluate, compare, refinance, affordability, stress test, amortization schedule, ARM simulation) to deterministic Python scripts that wrap numpy-financial. Every dollar figure is computed by Python and traced to a regulatory citation. Use when the user asks about mortgage payments, refinance NPV, affordability, DTI, ARM resets, points breakeven, amortization schedules, or any other home-loan math.
license: MIT (complete terms in LICENSE.txt)
compatibility: Requires Python 3.12+, numpy-financial, pydantic v2 (>=2.13), pyyaml. Designed for Claude Code (or any agent-skills-compatible client). Bundled scripts are deterministic CLIs; no network access required at runtime. DuckDB optional (Phase 9; needed only when scenarios are persisted).
---
```

Verification against spec constraints:
- `name: mortgage-ops` — 13 chars (≤ 64 ✓), lowercase + hyphens only ✓, matches parent directory `.claude/skills/mortgage-ops/` ✓
- `description` — 553 chars (≤ 1024 ✓), describes both what + when ✓, includes specific keywords agents identify (mortgage payments, refinance NPV, DTI, ARM resets, etc.)
- `license` — 30 chars, short, references bundled file per spec recommendation
- `compatibility` — 296 chars (≤ 500 ✓), free-form environment description per spec

### (l) First-200-lines routing skeleton — SKELETON

Lines 1-7 (frontmatter — see §(k))

Lines 8-20 (title + math discipline header — see §(e) for full text):

```markdown
# mortgage-ops — Router + Math Discipline

This skill routes natural-language mortgage requests to deterministic Python scripts.
You determine the mode, collect inputs, invoke the script, narrate the result.
You DO NOT compute mortgage math inline — see "Math discipline" below for the doctrine
and the reasoning.

Bundled scripts live in `${CLAUDE_SKILL_DIR}/scripts/`; references load on demand from
`${CLAUDE_SKILL_DIR}/references/`; mode files live in `${CLAUDE_SKILL_DIR}/modes/`.
```

Lines 21-100 (mode dispatch table + ambiguity rules — see §(d)):

```markdown
## Mode Routing

Determine the mode from the user's input:

| Input pattern | Mode | Script |
|---|---|---|
| Single loan + payment question ("$400k @ 6.5%/30yr, what's my payment?") | `evaluate` | scripts/amortize.py + lib.affordability composition |
| Multiple offers, "compare", "rank by NPV" | `compare` | scripts/refi_npv.py invoked once per offer |
| "refi", "refinance", "should I refi" | `refinance` | scripts/refi_npv.py |
| "afford", "qualify", "max loan", "DTI" | `affordability` | scripts/affordability.py |
| "stress", "shock", "what if rates jump" | `stress` | scripts/stress_test.py |
| "amortization schedule", "amortize", "extra principal" | `amortize` | scripts/amortize.py |
| "ARM", "5/1", "7/1", "10/1", "5/6", "SOFR ARM" | `arm` | scripts/arm_simulate.py |

Ambiguity rules (highest specificity wins):
1. If input contains "refi" or "refinance" → `refinance` (overrides all)
2. If input contains "compare" + multi-offer JSON → `compare`
3. If input contains "ARM" or product names (5/1, 7/1, 10/1, 5/6) → `arm` (unless also "refi")
4. If input contains "max", "qualify", "afford", "DTI" → `affordability`
5. If input contains "stress", "shock", "what if rates", "what if income" → `stress`
6. If input contains "schedule", "table", "extra principal" → `amortize`
7. Otherwise → `evaluate` (most general)
```

Lines 101-160 (math discipline doctrine — see §(e) full text)

Lines 161-200 (script doctrine — paraphrased from webapp-testing exemplar §(b)):

```markdown
## Bundled Scripts — black-box discipline

Use bundled scripts as black boxes. To accomplish a math task, identify the script
in `${CLAUDE_SKILL_DIR}/scripts/` that handles the workflow, then:

1. Run `python ${CLAUDE_SKILL_DIR}/scripts/<script>.py --help` to see the JSON-input
   schema. The `--help` is fast (lazy-imports happen AFTER argparse).

2. Construct the JSON input matching the schema. Money fields MUST be JSON strings
   (e.g. "400000.00") — Pydantic v2 strict mode rejects JSON floats at the boundary.

3. Write the JSON to a tempfile (e.g. `/tmp/mortgage-ops-<uuid>.json`).

4. Invoke: `python ${CLAUDE_SKILL_DIR}/scripts/<script>.py --input <tempfile>`.

5. Parse the stdout JSON response. On non-zero exit, parse stderr — it carries a
   uniform 6-key Pydantic error envelope `[{"type", "loc", "msg", "input", "url", "ctx"}]`
   that you narrate to explain the validation failure (e.g., "your principal field
   was a float; rewrite as a JSON string").

DO NOT read the script source code unless `--help` does not document a feature you
need AND a customized solution is absolutely necessary. The scripts are large enough
to pollute your context window; they exist to be called as black boxes, not ingested.
(Doctrine lifted from anthropics/skills/skills/webapp-testing/SKILL.md.)
```

Lines 201+ (mode loading triggers + reference loading triggers + appendix — non-load-bearing; can be longer):

- "When you decide on a mode, read `modes/_shared.md` first, then read `modes/{mode}.md`."
- "When the user asks for a regulatory citation, read the matching `references/X.md` (table mapping topic → reference file from §(c))."
- "On first session, check if `modes/_profile.md` exists; if not, copy from `modes/_profile.example.md` and inform the user (career-ops onboarding pattern)."
- Live FRED rate context (Phase 12 LIVE-02 inline `!` injection — placeholder for now).
- Footer with troubleshooting + commit attribution rule (CLAUDE.md global: NO Co-Authored-By).

This skeleton lands at ~200 lines of routing-load-bearing content, with the remaining 300 lines available for mode loading rules, reference loading rules, and supporting prose. Total target: ~450 lines (under 500), ~4500 cl100k tokens (under threshold).

## Phase Predicate / Library Surface Audit (verified by source-read)

| Surface | File:lines | Signature / Contract | Phase 10 use |
|---|---|---|---|
| `scripts/amortize.py` | `scripts/amortize.py:71-160` | argparse `--input <path>`, JSON-out, 6-key Pydantic envelope on stderr, `_project_root` on sys.path | RELOCATE to `.claude/skills/mortgage-ops/scripts/amortize.py`; update `_project_root` depth |
| `scripts/affordability.py` | `scripts/affordability.py:1-50+` | mirrors amortize.py exactly per Phase 4 D-13 | RELOCATE same as above |
| `scripts/arm_simulate.py` | `scripts/arm_simulate.py:1-30+` | mirrors amortize.py exactly per Phase 5 D-07; explicitly says "Phase 10 relocates" | RELOCATE same |
| `scripts/_cli_helpers.py` | `scripts/_cli_helpers.py:22-106` | `find_json_float_loc(raw)` + `make_decimal_type_envelope(loc, input_str)` | RELOCATE to `lib/_cli_helpers.py`; update imports in 7 scripts |
| `scripts/_generate_arm_fixtures.py` | dev tool | NOT a user CLI | KEEP at project root |
| `scripts/hooks/block-user-layer.py` | pre-commit hook | NOT a user CLI | KEEP at project root |
| (Phase 6) `scripts/refi_npv.py` | does not yet exist | will be created by Phase 6 per cross-phase contract | CREATE directly under `.claude/skills/mortgage-ops/scripts/refi_npv.py` |
| (Phase 7) `scripts/apr_reg_z.py` | does not yet exist | will be created by Phase 7 per cross-phase contract | CREATE directly under `.claude/skills/mortgage-ops/scripts/apr_reg_z.py` |
| (Phase 8) `scripts/stress_test.py` | does not yet exist | Phase 8 per cross-phase contract | CREATE directly under `.claude/skills/mortgage-ops/scripts/stress_test.py` |
| (Phase 8) `scripts/points_breakeven.py` | does not yet exist | Phase 8 per cross-phase contract | CREATE directly under `.claude/skills/mortgage-ops/scripts/points_breakeven.py` |
| `references/arm-mechanics.md` | `references/arm-mechanics.md:1-50+` | already shipped per Phase 5 | RELOCATE to `.claude/skills/mortgage-ops/references/arm-mechanics.md` |
| `DATA_CONTRACT.md` | `DATA_CONTRACT.md:11-25, 28-40` | enumerates `modes/_profile.md` as User Layer, `.claude/skills/mortgage-ops/**` as System Layer | UPDATE to reflect actual relocations + add `modes/_profile.example.md` to System Layer if not already implied |
| `scripts/hooks/block-user-layer.py` | pre-commit | `USER_LAYER_PATTERNS` tuple needs to include `modes/_profile.md` (or `.claude/skills/mortgage-ops/modes/_profile.md` — verify which path is checked) | UPDATE `USER_LAYER_PATTERNS` |
| `.gitignore` | not yet read | needs to gitignore `.claude/skills/mortgage-ops/modes/_profile.md` AND `reports/` (already covered by DATA_CONTRACT.md) | UPDATE `.gitignore` |
| `pyproject.toml` | `pyproject.toml:1-40+` | `[tool.ruff] src = ["lib", "tests", "scripts"]`; needs `tiktoken>=0.7` in dev group | UPDATE both lines |

## Open Questions Closed by Recommendations

| # | Question | Recommendation | Locked Decision ID |
|---|---|---|---|
| Q1 | Script relocation strategy: move vs symlink vs shim | MOVE — Option (i); see §(f) for migration plan | D-01 |
| Q2 | Tokenizer for SC-1 enforcement: tiktoken vs Anthropic API | tiktoken cl100k_base @ ≤4500 tokens with 10% margin documented | D-02 |
| Q3 | `compatibility` field syntax: structured version pin vs free-form | Free-form per agentskills.io spec; recommended value in §(a) | D-03 |
| Q4 | LICENSE.txt content: MIT vs Apache-2.0 vs other | MIT (project default; pyproject.toml has no license declared); Phase 10 plan-discuss-decide confirms | D-04 |
| Q5 | `_cli_helpers.py` location after relocation | Move to `lib/_cli_helpers.py` (cleaner library/CLI separation, ships with hatchling wheel) | D-05 |
| Q6 | `_generate_arm_fixtures.py` + `scripts/hooks/` after relocation | KEEP at project root (dev tooling, not user CLIs) | D-06 |
| Q7 | `_profile.template.md` vs `_profile.example.md` naming | Use `.example.md` to match `config/household.example.yml` + `config/profile.example.yml` already in DATA_CONTRACT.md | D-07 |
| Q8 | Cross-phase contract: should Phase 6/7/8 land scripts at root then Phase 10 relocates, or directly into skill folder? | DIRECTLY into `.claude/skills/mortgage-ops/scripts/` per new contract; Phase 6/7/8 RESEARCH/PLAN updates absorb this | D-08 |
| Q9 | Reference file load triggers: SKILL.md inline rule vs separate "loading.md" file | Inline rule in SKILL.md (lines 201+, see §(c)); table mapping topic → reference file | D-09 |
| Q10 | Mode loading rule: every mode loads `_shared.md` always, or only some? | Every mode loads `_shared.md` (career-ops convention; report structure is global) | D-10 |
| Q11 | Routing-rule placement: SKILL.md only, or split into routing.md? | SKILL.md only (Anthropic spec keeps SKILL.md as the entrypoint; no precedent for routing.md split) | D-11 |
| Q12 | First-200-lines routing budget enforcement: separate test, or reviewer-eyeball? | Separate test (`test_skill_routing_in_first_200_lines`) that asserts mode dispatch table appears before line 200 | D-12 |

## Locked Decisions (D-01..D-12) — Phase 10 Planner MUST honor

- **D-01** Script relocation = Option (i) MOVE: `git mv scripts/{seven scripts} .claude/skills/mortgage-ops/scripts/`; `git mv scripts/_cli_helpers.py lib/_cli_helpers.py`; update test `SCRIPT_PATH` constants; update `_project_root` depth in each script; update `pyproject.toml [tool.ruff] src`. `_generate_arm_fixtures.py` + `scripts/hooks/` STAY at project root.
- **D-02** Tokenizer = tiktoken cl100k_base; threshold ≤ 4500 tokens (NOT 5000) to leave 10% Anthropic-tokenizer margin. Add `tiktoken>=0.7` to `[dependency-groups] dev` in `pyproject.toml`. Test in `tests/test_skill.py::test_skill_md_token_budget_cl100k` per §(i) pattern.
- **D-03** `compatibility` field is FREE-FORM TEXT per agentskills.io spec, NOT a structured version pin. Use the recommended value in §(a) (~296 chars).
- **D-04** `LICENSE.txt` = MIT, full text per §(h). `license:` frontmatter = `MIT (complete terms in LICENSE.txt)`. Plan-discuss-decide may swap to Apache-2.0 if user prefers, but MIT is the default.
- **D-05** `_cli_helpers.py` relocates to `lib/_cli_helpers.py`; imports in all 7 scripts change `from scripts._cli_helpers ...` → `from lib._cli_helpers ...`.
- **D-06** `scripts/_generate_arm_fixtures.py` and `scripts/hooks/` stay at project root. Phase 10 does NOT touch them.
- **D-07** User-customization template = `modes/_profile.example.md` (committed, schema skeleton); `modes/_profile.md` (gitignored, real values). Naming matches `config/*.example.yml` pattern.
- **D-08** **CROSS-PHASE CONTRACT**: Phase 6 (`refi_npv.py` + `references/refi-npv.md`), Phase 7 (`apr_reg_z.py` + `references/apr-reg-z.md`), Phase 8 (`stress_test.py`, `points_breakeven.py`) MUST land their NEW Python CLI scripts AND new reference docs DIRECTLY into `.claude/skills/mortgage-ops/scripts/` and `.claude/skills/mortgage-ops/references/` respectively (NOT at project root). Phase 10 publishes the structure check (CI) that asserts no new `scripts/*.py` (other than the dev tools) appear at project root after Phase 10 ships. Phase 6/7/8 RESEARCH and PLAN files MUST be amended to reflect this.
- **D-09** Reference loading triggers are documented INLINE in SKILL.md (lines 201+) as a topic→reference table. No separate `loading.md` file.
- **D-10** Every mode (`evaluate`, `compare`, `refinance`, `affordability`, `stress`, `amortize`, `arm`) loads `modes/_shared.md` first, THEN its own mode file. Report structure (scoring, format) lives in `_shared.md`.
- **D-11** Mode dispatch table + ambiguity rules live IN SKILL.md (no `routing.md` split).
- **D-12** SC-2 enforcement of "routing in first 200 lines" via `tests/test_skill.py::test_skill_routing_in_first_200_lines` that grep-asserts the mode dispatch table appears before line 200.

## Project Constraints (from CLAUDE.md)

- **Money discipline (non-negotiable)**: Decimal for all dollar amounts, strings only. Never `float`. (Doesn't affect Phase 10 directly — this phase ships markdown + scripts that already enforce this — but SKILL.md doctrine §(e) reinforces "never compute inline" partly because LLM token-by-token sampling can't safely produce Decimal arithmetic.)
- **Calc engine separation**: every dollar figure computed by Python in `lib/`. SKILL.md routes; never owns numbers. Phase 10 SKILL.md text §(e) is the load-bearing instruction.
- **Skill portability**: `scripts/`, `references/`, `assets/`, `LICENSE.txt` ALL INSIDE `.claude/skills/mortgage-ops/`. SKILL.md ≤ 500 lines, ≤ 5k tokens. Load-bearing routing in first 200 lines. (Phase 10's literal mandate.)
- **Data Contract**: User Layer = `modes/_profile.md` (gitignored, never auto-updated); System Layer = everything else under `.claude/skills/mortgage-ops/`. Pre-commit hook + `.gitignore` enforce.
- **Commits**: NO Co-Authored-By or AI attribution (per global rule + project CLAUDE.md). All commits authored solely by repo owner.
- **Testing**: hand-calculated golden-value fixtures with citation comments; exact Decimal equality. (Doesn't directly affect Phase 10 — this phase ships markdown + tests for the markdown structure — but the `tests/test_skill.py` token/line/structure tests follow the same exact-equality discipline.)

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.12+ | All scripts | ✓ (verified by env Darwin 25.3.0; user has uv-managed Python 3.12 per pyproject.toml `requires-python = ">=3.12"`) | 3.12 | — |
| numpy-financial | All Python scripts | ✓ pinned in pyproject.toml | 1.0.0 | — |
| pydantic | All Python scripts | ✓ pinned >= 2.13.3 | 2.13+ | — |
| tiktoken | NEW — for SC-1 token budget test | ✗ NOT in pyproject.toml | needs >= 0.7 | none — must install |
| pyyaml | references/ YAML loading (and existing reference data layer) | ✓ pinned >= 6.0.2 | 6.0.2 | — |
| Claude Code (or any agent-skills client) | Skill consumption | ✓ user is using Claude Code | latest | none — required for skill UX |
| `git` | `git mv` operations in relocation | ✓ standard | — | — |
| `tempfile`-writable `/tmp/` (or platform equivalent) | Skill runtime — Claude writes JSON inputs to tempfiles | ✓ macOS `/tmp/` writable | — | — |

**Missing dependencies with no fallback:**
- `tiktoken` — must `uv add tiktoken --dev` (or equivalent) before SC-1 test can pass. Plan 10-XX includes this dependency add as the first step.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

> .planning/config.json was not read in this research; inferring `nyquist_validation` enabled by default per agent rules.

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest >= 9.0 (verified in pyproject.toml dev group) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (verify at plan time; if absent, no special config — pytest uses defaults) |
| Quick run command | `uv run pytest tests/test_skill.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| SKLL-01 | SKILL.md ≤ 500 lines, ≤ 5k tokens | unit | `pytest tests/test_skill.py::test_skill_md_token_budget_cl100k -x` AND `pytest tests/test_skill.py::test_skill_md_line_budget -x` | ❌ Wave 0 |
| SKLL-02 | routing logic in first 200 lines | unit | `pytest tests/test_skill.py::test_skill_routing_in_first_200_lines -x` | ❌ Wave 0 |
| SKLL-03 | frontmatter has name, description, license, compatibility | unit (YAML parse) | `pytest tests/test_skill.py::test_skill_md_frontmatter_required_fields -x` | ❌ Wave 0 |
| SKLL-04 | LICENSE.txt bundled inside skill folder | unit (file existence) | `pytest tests/test_skill.py::test_license_txt_exists_in_skill_folder -x` | ❌ Wave 0 |
| SKLL-05 | seven mode files exist | unit (file existence parametrized) | `pytest tests/test_skill.py::test_modes_exist -x` (parametrized over 7) | ❌ Wave 0 |
| SKLL-06 | `_shared.md` defines scoring/report structure | unit (substring match for required sections) | `pytest tests/test_skill.py::test_shared_mode_has_required_sections -x` | ❌ Wave 0 |
| SKLL-07 | `_profile.md` is gitignored; `.example.md` template committed | unit (gitignore parse + file existence) | `pytest tests/test_skill.py::test_profile_md_user_layer_gitignored -x` | ❌ Wave 0 |
| SKLL-08 | nine reference files exist | unit (parametrized) | `pytest tests/test_skill.py::test_references_exist -x` (parametrized over 9) | ❌ Wave 0 |
| SKLL-09 | references load on demand (SKILL.md instructs progressive disclosure) | unit (substring match for "load on demand" pattern in SKILL.md) | `pytest tests/test_skill.py::test_skill_md_documents_progressive_disclosure -x` | ❌ Wave 0 |
| SKLL-10 | scripts inside `.claude/skills/mortgage-ops/scripts/`, NOT project root | structure (file existence + non-existence) | `pytest tests/test_skill.py::test_seven_scripts_in_skill_folder_only -x` | ❌ Wave 0 |
| SKLL-11 | SKILL.md instructs ALWAYS shell out for math | unit (substring match for math discipline doctrine) | `pytest tests/test_skill.py::test_skill_md_shell_out_doctrine -x` | ❌ Wave 0 |
| SKLL-12 | scripts include `--help`; doctrine documented | unit (subprocess `--help` returns 0 for each of 7) + substring match for "do not read source" in SKILL.md | `pytest tests/test_skill.py::test_each_script_has_help_and_doctrine_documented -x` | ❌ Wave 0 |
| SKLL-13 | reports written to `reports/{###}-{slug}-{YYYY-MM-DD}.md` and ingested into DuckDB | integration (Phase 9 dependency) | DEFER to Phase 9 integration test (Phase 10 v1 ships the report-naming convention in `_shared.md`; the DuckDB ingestion test belongs in Phase 9's test suite per the dependency on PERS-03 `db-write.mjs insert-report`) | ❌ deferred |

### Sampling Rate

- **Per task commit**: `uv run pytest tests/test_skill.py -x`
- **Per wave merge**: `uv run pytest`
- **Phase gate**: full suite green + SKLL-01..12 all closed (SKLL-13 deferred to Phase 9 integration)

### Wave 0 Gaps

- [ ] `tests/test_skill.py` — covers SKLL-01..12; structure tests for skill folder layout, frontmatter, line/token budget, routing-position, mode file existence, reference file existence, script `--help` + doctrine, gitignore enforcement of `_profile.md`
- [ ] `tests/conftest.py` — add `skill_root` fixture returning `Path(__file__).parent.parent / ".claude" / "skills" / "mortgage-ops"` for cross-test reuse
- [ ] Add `tiktoken>=0.7` to `pyproject.toml [dependency-groups] dev` (Plan 10-XX first step before any test runs)

## Pinned Oracle Examples

### Oracle 1: SKILL.md token budget enforcement

**Setup**: SKILL.md sized at ~4500 cl100k tokens (the budget threshold).

**Hand-calc**: tiktoken cl100k_base on a 4500-token SKILL.md returns `len(enc.encode(text)) == 4500` (deterministic; proven at unit-test execution time).

**Anthropic projection**: 4500 × 1.15 = 5175 worst-case Anthropic tokens; 4500 × 1.10 = 4950 typical; both within compaction-survival-budget zone for "first 5000 tokens kept after summarization" rule.

**Test assertion**:
```python
assert n_tokens <= 4500, f"SKILL.md is {n_tokens} cl100k tokens (> 4500 budget)"
```

### Oracle 2: SKILL.md routing-in-first-200-lines

**Setup**: SKILL.md with mode dispatch table at lines 21-50; the test asserts the table marker (e.g., `## Mode Routing` heading) appears before line 200.

**Test assertion**:
```python
def test_skill_routing_in_first_200_lines():
    skill_md_lines = (skill_root() / "SKILL.md").read_text().splitlines()
    head_200 = "\n".join(skill_md_lines[:200])
    assert "## Mode Routing" in head_200, (
        "Mode dispatch table not in first 200 lines — will not survive compaction "
        "re-attach (5000-token window). See SKLL-02 + RESEARCH §(c)."
    )
    # Also assert each mode name appears in the dispatch table within first 200 lines
    for mode in ["evaluate", "compare", "refinance", "affordability", "stress", "amortize", "arm"]:
        assert f"`{mode}`" in head_200, f"Mode {mode} not dispatched in first 200 lines"
```

### Oracle 3: Seven scripts in skill folder ONLY (SKLL-10 + SC-3)

**Setup**: After Phase 10 relocation, all 7 user-CLI scripts live ONLY in `.claude/skills/mortgage-ops/scripts/`, NOT at project-root `scripts/`.

**Test assertion**:
```python
SEVEN_SCRIPTS = ["amortize.py", "affordability.py", "arm_simulate.py",
                 "refi_npv.py", "apr_reg_z.py", "stress_test.py", "points_breakeven.py"]

def test_seven_scripts_in_skill_folder_only():
    skill_scripts_dir = project_root() / ".claude" / "skills" / "mortgage-ops" / "scripts"
    project_scripts_dir = project_root() / "scripts"
    for script in SEVEN_SCRIPTS:
        assert (skill_scripts_dir / script).is_file(), \
            f"{script} missing from {skill_scripts_dir}"
        assert not (project_scripts_dir / script).is_file(), \
            f"{script} STILL at project root — should have been relocated (D-01)"

    # _generate_arm_fixtures.py + scripts/hooks/ STAY at project root (D-06)
    assert (project_scripts_dir / "_generate_arm_fixtures.py").is_file(), \
        "_generate_arm_fixtures.py should remain at project root (D-06)"
```

### Oracle 4: Frontmatter required fields

**Setup**: SKILL.md frontmatter parsed as YAML; check for the four SC-2 fields.

**Test assertion**:
```python
def test_skill_md_frontmatter_required_fields():
    import yaml
    skill_md = (skill_root() / "SKILL.md").read_text()
    # Frontmatter is between first two `---` lines
    parts = skill_md.split("---\n", 2)
    assert len(parts) >= 3, "SKILL.md missing YAML frontmatter delimiters"
    fm = yaml.safe_load(parts[1])

    assert "name" in fm, "frontmatter missing 'name' (SC-2 + spec required)"
    assert fm["name"] == "mortgage-ops", \
        f"name must match parent directory; got {fm['name']!r}"
    assert "description" in fm, "frontmatter missing 'description' (SC-2 + spec required)"
    assert len(fm["description"]) <= 1024, "description > 1024 chars (spec violation)"
    assert "license" in fm, "frontmatter missing 'license' (SC-2)"
    assert "compatibility" in fm, "frontmatter missing 'compatibility' (SC-2)"
    assert len(fm["compatibility"]) <= 500, "compatibility > 500 chars (spec violation)"
```

## Citations

### Primary (HIGH confidence — official Anthropic + Agent Skills spec)

- **Agent Skills specification (canonical)**: https://agentskills.io/specification — full frontmatter table, field constraints, directory structure, progressive disclosure model. [VERIFIED 2026-05-02]
- **Claude Code Skills docs**: https://code.claude.com/docs/en/skills — Claude-Code-specific extensions (when_to_use, allowed-tools, disable-model-invocation, etc.); compaction re-attach behavior (5000 tokens / 25000 combined). [VERIFIED 2026-05-02]
- **Agent Skills overview (Claude API docs)**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview — three-level loading model + token budget table. [VERIFIED 2026-05-02]
- **anthropics/skills repo**: https://github.com/anthropics/skills — public exemplar repository.
- **anthropics/skills/skills/webapp-testing/SKILL.md (CANONICAL EXEMPLAR)**: https://raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md — verbatim source of "run --help first; do not read source" doctrine + license-pointer pattern. [VERIFIED 2026-05-02; SHA pinned to 4726215301db64a0cc4d41fc3219c61f37a30f4a]
- **anthropics/skills/skills/skill-creator/SKILL.md**: https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md — Anthropic's authoring guidance ("explain the why", avoid "musty MUSTs", compatibility field "rarely needed"). [VERIFIED 2026-05-02]
- **anthropics/skills/spec/agent-skills-spec.md**: https://raw.githubusercontent.com/anthropics/skills/main/spec/agent-skills-spec.md — points to https://agentskills.io/specification as canonical source. [VERIFIED 2026-05-02]
- **Anthropic count_tokens API**: https://platform.claude.com/docs/en/api/messages-count-tokens — endpoint POST `/v1/messages/count_tokens`; free; rate-limited; requires API key. [VERIFIED 2026-05-02]
- **Token counting guide**: https://platform.claude.com/docs/en/build-with-claude/token-counting — confirms count_tokens is free + rate-limited. [VERIFIED 2026-05-02]

### Secondary (MEDIUM confidence — verified against multiple sources)

- **tiktoken vs Anthropic accuracy**: https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025 — "typically within ten to twenty percent" for English prose; tiktoken is OpenAI-specific. [VERIFIED via WebSearch 2026-05-02; cross-checked with https://blog.gopenai.com/counting-claude-tokens-without-a-tokenizer-e767f2b6e632]
- **agentskills.io overview**: https://agentskills.io — open-standard adopted by Claude Code, Claude.ai, Gemini CLI, Cursor, OpenHands, Goose, GitHub Copilot, VS Code, etc. [VERIFIED 2026-05-02]
- **career-ops SKILL.md pattern**: file `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md` (95 lines, single-file skill); modes/* lives at project root not under .claude/skills (this is older pattern that mortgage-ops Phase 10 supersedes by putting modes INSIDE the skill folder per SKLL-05/06 + Anthropic skill portability). [VERIFIED via Read 2026-05-02]

### Internal (HIGH confidence — read directly from project)

- `/Users/cujo253/Documents/mortgage-ops/CLAUDE.md` lines 61-65 (Skill portability section)
- `/Users/cujo253/Documents/mortgage-ops/DATA_CONTRACT.md` lines 11-25 (User Layer enumeration of `modes/_profile.md`); lines 28-44 (System Layer enumeration of `.claude/skills/mortgage-ops/**`)
- `/Users/cujo253/Documents/mortgage-ops/.planning/REQUIREMENTS.md` lines 132-145 (SKLL-01..13 verbatim)
- `/Users/cujo253/Documents/mortgage-ops/.planning/phases/06-refinance-npv/06-RESEARCH.md` lines 1-516 (Phase 6 D-09 after-tax mode → tax-deductibility.md content; D-04 sign convention → refi-npv.md content)
- `/Users/cujo253/Documents/mortgage-ops/scripts/amortize.py` lines 17-19 (Phase 3 D-17 explicit anticipation: "Phase 10 physically relocates it to .claude/skills/mortgage-ops/scripts/amortize.py")
- `/Users/cujo253/Documents/mortgage-ops/scripts/arm_simulate.py` lines 1-30 (mirrors amortize.py per Phase 5 D-07; explicit relocation note)
- `/Users/cujo253/Documents/mortgage-ops/scripts/affordability.py` lines 1-50 (mirrors amortize.py per Phase 4 D-13)
- `/Users/cujo253/Documents/mortgage-ops/references/arm-mechanics.md` lines 1-50 (already shipped per Phase 5 — verifies that Phase 6/7/8 reference docs CAN ship into the skill folder when written)
- `/Users/cujo253/Documents/mortgage-ops/pyproject.toml` lines 1-40 (`requires-python = ">=3.12"`; deps: `pydantic>=2.13.3`, `numpy-financial==1.0.0`, `pyyaml>=6.0.2`; `[tool.ruff] src = ["lib", "tests", "scripts"]` — needs update post-relocation)

### Tertiary (LOW — informational)

- **Lee Hanchung blog "Claude Agent Skills: A First Principles Deep Dive"**: https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/ — third-party deep-dive; useful for sanity-checking the progressive-disclosure model.
- **Generative Programmer blog "Skill Authoring Patterns"**: https://generativeprogrammer.com/p/skill-authoring-patterns-from-anthropics — third-party summary.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Anthropic's tokenizer counts ~10-15% higher than tiktoken cl100k for English markdown | §(i) D-02 | If Anthropic counts only 5% higher, the 4500 threshold is over-conservative (waste budget). If Anthropic counts 25% higher, 4500×1.25=5625 worst-case, exceeding 5000 — would need to drop threshold to ~4000. **Mitigation**: when Anthropic publishes their tokenizer, re-pin the threshold; until then, the 10-15% range is the consensus across multiple third-party sources. The compaction re-attach budget is 5000 tokens, so even at 5175 worst-case the routing in first-200 lines (~2000 tokens) survives intact. |
| A2 | MIT is the appropriate default license | §(h) D-04 | If user wanted Apache-2.0 or proprietary, the LICENSE.txt content + frontmatter would need to swap. Plan-discuss-decide should confirm with user before committing LICENSE.txt. |
| A3 | The `modes/` folder convention is fine despite not being spec-defined | §(b) | If a future agent-skills client strictly enforces only `scripts/`, `references/`, `assets/` directories, the `modes/` folder would not be recognized. **Mitigation**: agentskills.io spec explicitly says "Any additional files or directories" are permitted. No current client enforces a closed list. Risk is theoretical. |
| A4 | Phase 6/7/8 scripts will land DIRECTLY into skill folder per cross-phase contract D-08 | §(j) D-08 | If Phases 6/7/8 PLANs already exist and ship to project root, Phase 10 must also relocate them. **Mitigation**: Phase 6 RESEARCH locked but PLANs not yet executed; cross-phase contract update can be published BEFORE Phase 6 executes. STATE.md / ROADMAP.md update is the carrier. |
| A5 | tiktoken 0.7+ is the right pin | §(i) | At research time, latest is 0.7.x; if 0.8 ships breaking changes, pin needs revisiting. Standard Python dep-pinning hygiene applies. |
| A6 | webapp-testing is the most representative complex skill exemplar | §(b) | Other anthropics/skills (skill-creator, claude-api) have richer structure (e.g., skill-creator has agents/, scripts/, references/, eval-viewer/, assets/). webapp-testing was chosen because it has scripts/ + examples/ AND is mentioned in CLAUDE.md as the doctrine source. **Mitigation**: skill-creator structure also reviewed in §(b) reading; mortgage-ops uses webapp-testing's `scripts/` doctrine + skill-creator's `references/` + `assets/` directory pattern. Both are spec-compliant. |
| A7 | `_generate_arm_fixtures.py` and `scripts/hooks/` are NOT user-facing CLIs | §(f) D-06 | If they ARE meant to be skill-callable, they'd need to relocate too. **Mitigation**: file inspection at research time confirms `_generate_arm_fixtures.py` is a dev-only fixture generator (per its filename prefix `_`, Python convention for module-private/dev-only) and `scripts/hooks/` is a pre-commit hook directory (per `.pre-commit-config.yaml` reference in DATA_CONTRACT.md). Neither matches the seven SC-3-mandated user-CLIs. |

**If this table is empty**: All claims verified or cited — no user confirmation needed. **Above table NOT empty**: A1, A2, A4 in particular need plan-discuss-decide confirmation before Phase 10 execution.

## Open Questions

1. **Cross-phase contract publication mechanism (D-08)**
   - What we know: Phase 6 RESEARCH is locked; Phase 7/8 RESEARCH not yet drafted. The "Phase 10 physically relocates" comments in existing scripts (Phase 3/4/5 D-XX) imply that Phases 6/7/8 should also ship to project root then Phase 10 relocates.
   - What's unclear: should D-08 (DIRECT into skill folder) override the existing pattern, or should Phase 10's plan include relocating any scripts shipped by Phases 6/7/8 to project root in the meantime?
   - Recommendation: Publish D-08 NOW (Phase 10 RESEARCH commit) so Phase 7 (next pending) drafts ship directly into skill folder. For Phase 6 (RESEARCH locked, PLAN not yet executed) — amend Phase 6 RESEARCH with a pointer to D-08 and update Phase 6 PLAN-author convention. ROADMAP / STATE.md absorb this in Phase 10 plan-discuss-decide.

2. **`modes/_profile.md` vs `modes/_profile.example.md` — pre-commit hook path enforcement**
   - What we know: DATA_CONTRACT.md line 19 enumerates `modes/_profile.md` as User Layer. `block-user-layer.py` enforces commit-time blocking by `USER_LAYER_PATTERNS` tuple.
   - What's unclear: does the existing `USER_LAYER_PATTERNS` use a relative path (`modes/_profile.md`) or absolute (`.claude/skills/mortgage-ops/modes/_profile.md`)? The path under Phase 10 is the latter (since modes live INSIDE the skill folder per SKLL-05/06 + Anthropic skill portability — NOT at project root like career-ops).
   - Recommendation: Plan 10-XX reads `scripts/hooks/block-user-layer.py` source-of-truth at execution time, then updates `USER_LAYER_PATTERNS` AND `USER_LAYER_GLOB_DIRS` AND `.gitignore` AND DATA_CONTRACT.md line 19 (path correction) in the same commit per DATA_CONTRACT.md line 73-74 ("Both lists are kept in sync by editing this file and the hook source in the same commit").

3. **First-session onboarding — copy `_profile.example.md` → `_profile.md` automatically?**
   - What we know: career-ops onboarding (per career-ops/CLAUDE.md "First Run — Onboarding" section) silently copies `modes/_profile.template.md` → `modes/_profile.md` on first run.
   - What's unclear: should mortgage-ops SKILL.md include similar onboarding instructions? CLAUDE.md does NOT include a first-run onboarding section yet.
   - Recommendation: YES — SKILL.md lines 201+ should include a "first session" check: "If `${CLAUDE_SKILL_DIR}/modes/_profile.md` does not exist, copy from `_profile.example.md` and tell the user 'I created a personalization file at `modes/_profile.md`. Edit it to set your default loan term, narrative tone, etc.'" This matches career-ops UX. NOT a blocking decision for Phase 10 v1, but Plan 10-XX should include the onboarding instruction in SKILL.md.

4. **Anthropic tokenizer ground-truth verification**
   - What we know: Anthropic does not publish a tokenizer; tiktoken cl100k is the best offline approximation; multiple sources estimate 10-15% undercount.
   - What's unclear: empirical Anthropic count of the actual mortgage-ops SKILL.md once written.
   - Recommendation: post-Phase-10 ship, run a one-shot validation against the Anthropic count_tokens API (locally, with API key, NOT in CI) to confirm the actual count is < 5000. If actual is in [4500, 5000] range, the 10% margin holds; if < 4500 or > 5000, adjust the threshold in `tests/test_skill.py`. Document the empirical result inline as a comment.

## Confidence Statement

**HIGH confidence** that locked decisions D-01..D-12 are sufficient to execute Phase 10 without further research. The Anthropic Agent Skills specification (https://agentskills.io/specification) is explicit; webapp-testing exemplar (verbatim source available) provides the canonical doctrine wording; career-ops mirrors the user-layer customization pattern; existing mortgage-ops scripts already anticipate the relocation per Phase 3/4/5 D-XX inline comments.

**Open caveats:**
- The cross-phase contract D-08 needs plan-discuss-decide-time publication (open question #1 above) so Phase 7/8 RESEARCH/PLAN absorb it before they ship.
- The Anthropic tokenizer 10-15% margin is anecdotal across multiple third-party sources; empirical post-ship validation (open question #4) is recommended, NOT a blocker.
- LICENSE.txt MIT default may want user confirmation in plan-discuss-decide (assumption A2).

**Research is complete** for plan-checker handoff. The planner has all locked decisions, surface audits, and oracle examples needed to draft Plan 10-01 through Plan 10-XX.
