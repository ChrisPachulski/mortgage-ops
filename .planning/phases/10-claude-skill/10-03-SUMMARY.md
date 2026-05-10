---
phase: 10-claude-skill
plan: 03
subsystem: claude-skill
tags:
  - phase-10
  - claude-skill
  - modes
  - skll-05
  - skll-06
  - skll-07
  - skll-13
  - d-13
  - d-num
  - d-prof
  - d-suba-fw-02
  - wave-3

requires:
  - phase: 10-00
    provides: tests/test_skill.py xfail stubs (Wave 5 will flip to consume modes/_shared.md + modes/_profile.example.md)
  - phase: 10-02
    provides: SKILL.md routing skeleton (forward-references modes/_shared.md + modes/{mode}.md that this wave ships)
provides:
  - .claude/skills/mortgage-ops/modes/_shared.md (263 lines / 3447 cl100k tokens; 12 mandatory H2 sections inc. D-PROF-04 / D-NUM-01..06 / D-13-01..05)
  - .claude/skills/mortgage-ops/modes/_profile.example.md (42 lines; pure YAML; 4 top-level keys per D-PROF-01 + D-PROF-02; defaults match D-PROF-04 fallback)
  - .claude/skills/mortgage-ops/modes/evaluate.md (142 lines / 1435 tokens; ONLY mode that composes amortize.py + affordability.py)
  - .claude/skills/mortgage-ops/modes/compare.md (114 lines / 1214 tokens; refi_npv.py per offer)
  - .claude/skills/mortgage-ops/modes/refinance.md (125 lines / 1440 tokens; UI-SPEC §a Case 1 refi+ARM ambiguity rule)
  - .claude/skills/mortgage-ops/modes/affordability.md (146 lines / 1510 tokens; UI-SPEC §a Case 2 affordability+amortize ambiguity rule)
  - .claude/skills/mortgage-ops/modes/stress.md (151 lines / 1591 tokens; D-SUBA-FW-02 existence-check seam to stress-test-agent)
  - .claude/skills/mortgage-ops/modes/amortize.md (120 lines / 1154 tokens)
  - .claude/skills/mortgage-ops/modes/arm.md (142 lines / 1523 tokens; D-NUM-04 bps formatting)
  - User Layer enforcement triple wired for new path .claude/skills/mortgage-ops/modes/_profile.md (.gitignore + hook + DATA_CONTRACT.md + tests/test_block_user_layer.py)
  - SKLL-13 closure at modes layer (Save Report step uses REAL Phase 9 CLI per orchestration/db-write.mjs:296-310)
affects:
  - "10-04 (Wave 4 references/*.md): every mode file's RELATED REFERENCES footer names references/*.md files Wave 4 ships (amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions); cross-link audit below"
  - "10-05 (Wave 5 CI tests): Wave 5 flips Wave-0 xfail stubs against this Wave-3 surface (test_shared_mode_has_required_sections / test_profile_example_md_has_exact_four_keys / test_profile_md_user_layer_gitignored / test_report_filename_format / test_report_persisted_to_duckdb)"
  - "10-06 (Wave 6 end-to-end smoke): Plan 10-06 runs the Save Report step against a real DuckDB instance to verify the insert-report --scenario-id <int> --file <path> invocation pattern documented in modes/_shared.md"
  - "11 (Phase 11 subagents): D-SUBA-FW-02 existence-check seam in modes/stress.md activates dispatch when .claude/agents/stress-test-agent.md is written -- zero edits to modes/stress.md required"

tech-stack:
  added: []
  patterns:
    - "Pure-YAML-in-.md-file template (Round-2 codex HIGH 4 Option A): _profile.example.md keeps the .md extension to match the modes/ folder convention but the body is parseable directly via yaml.safe_load. The cp-and-parse contract (cp _profile.example.md _profile.md) produces a file that yaml.safe_load parses without fenced-block extraction. modes/_shared.md Profile Loading section relies on this contract."
    - "Real-CLI substring discipline (Round-2 codex HIGH 2): _shared.md Save Report step uses 'node orchestration/db-write.mjs insert-report --scenario-id <int> --file <path>' (real per orchestration/db-write.mjs:296-310). The fictional --insert-report --json flag form was caught by the cross-AI Round-2 review and replaced with the real subcommand. Sequence number lookup uses the real 'query --sql' subcommand (not '--query'). The reports table has no 'filename' column; the file on disk is the durable filename anchor."
    - "Existence-check seam (D-SUBA-FW-02): modes/stress.md carries the literal phrase 'if it exists' AND the literal path '.claude/agents/stress-test-agent.md'. Phase 11 lands by writing the agent file -- modes/stress.md does NOT need a follow-up commit. Same routing logic regardless of whether the agent file is present (existence check is the seam)."
    - "Atomic enforcement-triple commit (DATA_CONTRACT line 73-74 sync rule): Task 3 commits .gitignore + scripts/hooks/block-user-layer.py + tests/test_block_user_layer.py + DATA_CONTRACT.md TOGETHER in a single commit. The DATA_CONTRACT line 73 rule requires hook source + DATA_CONTRACT to update in the same commit; this wave extends that discipline to include the parametrize test list (Round-2 codex HIGH 3 + LOW 11 catch -- the prior Round-1 test exercised the hook with no argv args and passed for the wrong reason)."
    - "12-section _shared.md inheritance: original UI-SPEC §i listed 9 mandatory sections; this wave extends to 12 by adding Profile Loading (D-PROF-04 fallback), Output Formatting (D-NUM-01..06), and Save Report (D-13-01..05). Token budget grew from ~120 lines to 263 lines / 3447 tokens (under the 3500 cap with margin)."
    - "Mode file 4-section spine consistency: every mode file (evaluate / compare / refinance / affordability / stress / amortize / arm) opens with the D-10 inheritance reminder, follows the UI-SPEC §b spine (When to invoke / What scripts to call / What to narrate / Edge cases), and ends with a RELATED REFERENCES footer naming references/*.md files for progressive disclosure."

key-files:
  created:
    - .claude/skills/mortgage-ops/modes/_shared.md
    - .claude/skills/mortgage-ops/modes/_profile.example.md
    - .claude/skills/mortgage-ops/modes/evaluate.md
    - .claude/skills/mortgage-ops/modes/compare.md
    - .claude/skills/mortgage-ops/modes/refinance.md
    - .claude/skills/mortgage-ops/modes/affordability.md
    - .claude/skills/mortgage-ops/modes/stress.md
    - .claude/skills/mortgage-ops/modes/amortize.md
    - .claude/skills/mortgage-ops/modes/arm.md
  modified:
    - .gitignore
    - scripts/hooks/block-user-layer.py
    - tests/test_block_user_layer.py
    - DATA_CONTRACT.md

key-decisions:
  - "D-10 honored: every mode file opens with 'Read modes/_shared.md FIRST (per D-10), then this file.'"
  - "D-13-01..D-13-05 honored: _shared.md Save Report section codifies the unconditional auto-write + DuckDB ingest with save_report:false as the only opt-out; Phase 10 closes SKLL-13"
  - "D-NUM-01..D-NUM-06 honored: _shared.md Output Formatting section codifies money/rate/ratio/bps display directives with verbatim D-NUM example tokens (\\$1,264.14 / 6.500% / 43.0% / 250 bps (2.50%))"
  - "D-PROF-01 honored: _profile.example.md ships EXACTLY 4 top-level keys (verbosity / citation_density / save_report / disambiguation); pytest yaml.safe_load asserts the key set"
  - "D-PROF-02 honored: NO calc-input duplication in _profile.example.md (no income / applicants / monthly_debts / FIPS / escrow / VA block / target_property_value / lender preferences)"
  - "D-PROF-03 honored: _profile.md is gitignored AND blocked by pre-commit hook AND enumerated in DATA_CONTRACT.md User Layer table (triple-check enforcement)"
  - "D-PROF-04 honored: _shared.md Profile Loading section codifies fallback defaults (standard / inline / true / always-ask) when _profile.md is missing; matches _profile.example.md committed defaults"
  - "D-SUBA-FW-02 honored: modes/stress.md contains literal 'if it exists' AND literal '.claude/agents/stress-test-agent.md' (Phase 11 lands by writing the agent file -- zero edits required to modes/stress.md)"
  - "Round-2 codex HIGH 2 honored: _shared.md uses REAL Phase 9 CLI per orchestration/db-write.mjs:296-310 ('insert-report --scenario-id <int> --file <path>'); fictional '--insert-report --json' and '--query' flag forms are absent from the file body"
  - "Round-2 codex HIGH 3 honored: hook test exercises argv-based invocation (not no-args invocation that returned 0 for the wrong reason); parametrize list extended to include both legacy 'modes/_profile.md' AND new '.claude/skills/mortgage-ops/modes/_profile.md'"
  - "Round-2 codex HIGH 4 Option A honored: _profile.example.md is pure YAML in a .md-named file; no fenced block; no markdown headers; no HTML comments. yaml.safe_load(open(path).read()) parses directly. cp-and-parse contract works without extraction logic"

requirements-completed:
  - SKLL-05
  - SKLL-06
  - SKLL-07
  - SKLL-13

duration: ~15 min
completed: "2026-05-10"
---

# Phase 10 Plan 03: Mode Files + User Layer Enforcement Summary

**9 mode files written under `.claude/skills/mortgage-ops/modes/` (`_shared.md`, `_profile.example.md`, `evaluate.md`, `compare.md`, `refinance.md`, `affordability.md`, `stress.md`, `amortize.md`, `arm.md`); 4 enforcement-config files updated (`.gitignore`, `scripts/hooks/block-user-layer.py`, `tests/test_block_user_layer.py`, `DATA_CONTRACT.md`); SKLL-13 closes at the modes layer via the Save Report step in `_shared.md` using the REAL `node orchestration/db-write.mjs insert-report --scenario-id <int> --file <path>` CLI per `orchestration/db-write.mjs:296-310` (Round-2 codex HIGH 2 satisfied — no fictional `--insert-report --json` or `--query` flag forms). `_profile.example.md` is pure YAML in a .md-named file (Round-2 codex HIGH 4 Option A) with EXACTLY 4 top-level keys per D-PROF-01 + D-PROF-02 (`verbosity`, `citation_density`, `save_report`, `disambiguation`). `modes/stress.md` carries the D-SUBA-FW-02 existence-check seam (literal `if it exists` + literal `.claude/agents/stress-test-agent.md`) so Phase 11 lands by writing the agent file alone. Test count: 550 → 551 passed (one new parametrize case in `test_block_user_layer.py`); 4 skipped / 16 xfailed preserved.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-10T01:01:21Z
- **Completed:** 2026-05-10T01:16:31Z
- **Tasks:** 4 (Task 1 _shared.md, Task 2 _profile.example.md, Task 3 enforcement triple, Task 4 7 mode files)
- **Files created:** 9 (7 mode files + _shared.md + _profile.example.md)
- **Files modified:** 4 (.gitignore + hook + test + DATA_CONTRACT)

## Wave Outcome

| Metric | Wave 2 baseline | Wave 3 result | Delta |
|--------|-----------------|---------------|-------|
| `pytest` total passed | 550 | 551 | +1 (new parametrize case in test_block_user_layer.py) |
| skipped | 4 | 4 | 0 |
| xfailed | 16 | 16 | 0 |
| failed | 0 | 0 | 0 |
| errored | 0 | 0 | 0 |
| Files at `.claude/skills/mortgage-ops/modes/` | 0 | 9 (7 mode files + _shared.md + _profile.example.md) | +9 |

Wave 5 (Plan 10-05) flips the following Wave-0 xfail stubs against this Wave-3 surface — at that point `xfailed` drops by 4 to 12 (modulo any other Wave 5 flips):

- `test_shared_mode_has_required_sections` → asserts the 12 mandatory H2 sections exist in `_shared.md`
- `test_profile_example_md_has_exact_four_keys` → asserts `yaml.safe_load(_profile.example.md).keys() == {verbosity, citation_density, save_report, disambiguation}`
- `test_profile_md_user_layer_gitignored` → asserts `.gitignore` blocks `.claude/skills/mortgage-ops/modes/_profile.md`
- `test_report_filename_format` → asserts `_shared.md` contains the literal `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md` filename pattern
- `test_report_persisted_to_duckdb` → asserts `_shared.md` contains the literal `node orchestration/db-write.mjs insert-report` substring

## Accomplishments

- **`modes/_shared.md` (263 lines / 3447 cl100k tokens)** — 12 mandatory H2 sections per UI-SPEC §i + Round-2 MEDIUM 7 (Sources of Truth / Profile Loading / Money Discipline / Always Cite the Script / Never Invent Numbers / Estimated APR Literal Text / Script Invocation Doctrine / Error Narration Template / Output File Naming / Output Formatting / Save Report / Forbidden Behaviors). Profile Loading codifies D-PROF-04 fallback (standard / inline / true / always-ask) and the cp-and-parse contract with `_profile.example.md`. Output Formatting carries D-NUM-01..06 with verbatim example tokens (`$1,264.14`, `6.500%`, `43.0%`, `250 bps (2.50%)`). Save Report invokes the REAL Phase 9 CLI: `node orchestration/db-write.mjs insert-report --scenario-id <int> --file <path>`. Sequence number lookup uses `query --sql`. Token budget at 3447 / 3500 cap (53 tokens of margin).

- **`modes/_profile.example.md` (42 lines; pure YAML)** — Round-2 codex HIGH 4 Option A. The body is parseable by `yaml.safe_load(open(path).read())` directly. EXACTLY 4 top-level keys per D-PROF-01: `verbosity` / `citation_density` / `save_report` / `disambiguation`. Defaults match D-PROF-04 fallback. NO calc-input duplication per D-PROF-02 (income, applicants, monthly debts, FIPS, escrow, VA block, target property value, lender preferences all stay in `config/household.yml` + `config/profile.yml`).

- **User Layer enforcement triple wired for `.claude/skills/mortgage-ops/modes/_profile.md`** — Round-2 codex HIGH 3 + LOW 11. `.gitignore` blocks bare `git add`; `scripts/hooks/block-user-layer.py` blocks `git add -f` bypasses (exit 1 with offending file named); `tests/test_block_user_layer.py` parametrize list extended to assert the new path is blocked AND the legacy `modes/_profile.md` is still blocked (defense in depth — both paths in `USER_LAYER_PATTERNS`). `DATA_CONTRACT.md` line 19 path corrected to the canonical skill-folder location. All four files committed atomically per the line 73-74 sync rule.

- **7 mode files (940 lines total; ≤ 2500 token budget per file with substantial margin)** — every file follows the UI-SPEC §b 4-section spine (`## When to invoke` / `## What scripts to call` / `## What to narrate` / `## Edge cases`), opens with the D-10 inheritance reminder, ends with a RELATED REFERENCES footer naming Wave 4 references files for progressive disclosure. Each mode references the relocated `.claude/skills/mortgage-ops/scripts/*` paths.

- **`modes/evaluate.md` dual-dispatch composition (UI-SPEC §a rows 1-2)** — the ONLY mode that composes TWO scripts. Calls `amortize.py` for monthly P&I + total interest, then `affordability.py` for DTI / LTV / CLTV / PITI breakdown + blocker precedence list. Single narration merges both JSON outputs into the canonical "answer + provenance" template.

- **`modes/refinance.md` AMBIGUITY RULE (UI-SPEC §a Case 1)** — if the prompt mentions BOTH "refi" + "ARM" / "X/Y", routes HERE and passes `loan_type: arm` + `arm_terms: {...}` to the new-loan side. Refi+stress collision routes here too with the sweep as inner loop (forward-link to `modes/stress.md` existence-check seam).

- **`modes/affordability.md` AMBIGUITY RULE (UI-SPEC §a Case 2)** — "can I afford X *and* what's the payment" makes ONE call. The `affordability.py` response already includes `monthly_pi` + `monthly_taxes` + `monthly_insurance` + `monthly_pmi` + `monthly_hoa` + (FHA) `monthly_mip`; a second call would be wasteful and confuse provenance.

- **`modes/stress.md` D-SUBA-FW-02 EXISTENCE-CHECK SEAM** — contains literal `if it exists` AND literal `.claude/agents/stress-test-agent.md` (per Round-2 acceptance grep). For N>5 scenarios, defers to the Phase 11 subagent IF the agent file exists; otherwise runs the stress sweep inline. The seam is the file-existence check — Phase 11 lands by writing the agent file with no edit required to `modes/stress.md`.

- **`modes/arm.md` D-NUM-04 bps formatting** — uses `250 bps (2.50%)` notation for margin / caps / floors per CONTEXT.md; D-NUM-02 percent-only for the actual rate at any period. Contains all four bps example forms: `periodic_cap: 200 bps (2.00%)`, `lifetime_cap: 500 bps (5.00%)`, `margin: 275 bps (2.75%)`, `floor: 200 bps (2.00%)`.

## Task Commits

Each task committed atomically per CLAUDE.md / global no-AI-attribution rule:

1. **Task 1: `modes/_shared.md`** — `15236b0` (feat)
2. **Task 2: `modes/_profile.example.md`** — `3ab3cac` (feat)
3. **Task 3: User Layer enforcement triple** — `784dd63` (feat — atomic 4-file commit per DATA_CONTRACT line 73-74 sync rule)
4. **Task 4: 7 mode files** — `79e0e7d` (feat)

**Plan metadata commit:** _to be appended_ (this SUMMARY commit).

## Files Created/Modified

### Created (9)

- `.claude/skills/mortgage-ops/modes/_shared.md` (263 lines / 3447 cl100k tokens) — 12-section shared inheritance for every mode.
- `.claude/skills/mortgage-ops/modes/_profile.example.md` (42 lines; pure YAML) — User Layer schema skeleton with 4 D-PROF-01 keys + D-PROF-04 defaults.
- `.claude/skills/mortgage-ops/modes/evaluate.md` (142 lines / 1435 tokens) — single-loan analysis; dual-dispatch composition.
- `.claude/skills/mortgage-ops/modes/compare.md` (114 lines / 1214 tokens) — multi-offer ranking via `refi_npv.py`.
- `.claude/skills/mortgage-ops/modes/refinance.md` (125 lines / 1440 tokens) — refi NPV with refi+ARM ambiguity rule.
- `.claude/skills/mortgage-ops/modes/affordability.md` (146 lines / 1510 tokens) — DTI/LTV/CLTV/PITI + reverse-affordability with affordability+amortize ambiguity rule.
- `.claude/skills/mortgage-ops/modes/stress.md` (151 lines / 1591 tokens) — rate-shock / income-shock / ARM-reset sweeps with D-SUBA-FW-02 existence-check seam.
- `.claude/skills/mortgage-ops/modes/amortize.md` (120 lines / 1154 tokens) — amortization schedule with biweekly + extra-principal options.
- `.claude/skills/mortgage-ops/modes/arm.md` (142 lines / 1523 tokens) — ARM modeling with D-NUM-04 bps formatting.

### Modified (4)

- `.gitignore` — appended `.claude/skills/mortgage-ops/modes/_profile.md` Phase 10 User Layer entry.
- `scripts/hooks/block-user-layer.py` — added `.claude/skills/mortgage-ops/modes/_profile.md` to `USER_LAYER_PATTERNS` tuple. Legacy `modes/_profile.md` retained for defense in depth.
- `tests/test_block_user_layer.py` — extended `test_user_layer_pattern_paths_are_blocked` parametrize list with the new path.
- `DATA_CONTRACT.md` — line 19 path corrected from `modes/_profile.md` to `.claude/skills/mortgage-ops/modes/_profile.md`.

## Substring-Presence Audit

Every Round-2-locked acceptance criterion was verified end-to-end before commit:

| Required substring / structure | Plan-cited requirement | Verified |
|--------------------------------|------------------------|----------|
| `modes/_shared.md` 12 H2 sections (Sources of Truth / Profile Loading / Money Discipline / Always Cite the Script / Never Invent Numbers / Estimated APR / Script Invocation Doctrine / Error Narration Template / Output File Naming / Output Formatting / Save Report / Forbidden Behaviors) | UI-SPEC §i + Round-2 MEDIUM 7 | PASSED |
| `modes/_shared.md` ≤ 3500 cl100k tokens | Plan §Task 1 acceptance | PASSED (3447) |
| `modes/_shared.md` contains `db-write.mjs insert-report --scenario-id` | Round-2 codex HIGH 2 | PASSED |
| `modes/_shared.md` does NOT contain `--insert-report --json` | Round-2 codex HIGH 2 | PASSED (0 occurrences) |
| `modes/_shared.md` does NOT contain `db-write.mjs --query` | Round-2 codex HIGH 2 | PASSED (0 occurrences) |
| `modes/_shared.md` does NOT reference a `filename` column | Round-2 codex HIGH 2 | PASSED |
| `modes/_shared.md` contains `save_report: false` | D-13-05 override | PASSED |
| `modes/_shared.md` contains D-NUM example tokens (`$1,264.14` or `$2,528.27` or `$400,000.00`) | D-NUM-01 | PASSED |
| `modes/_shared.md` contains `6.500%` or `3.875%` | D-NUM-02 | PASSED |
| `modes/_shared.md` contains `43.0%` | D-NUM-03 | PASSED |
| `modes/_shared.md` contains `bps (2.50%)` or `bps (2.00%)` etc. | D-NUM-04 | PASSED |
| `modes/_shared.md` contains `estimated APR` | UI-SPEC §e Phase 7 forward-link | PASSED |
| `modes/_shared.md` contains `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md` filename pattern | D-13-02 | PASSED |
| `_profile.example.md` parses cleanly via `yaml.safe_load` (no fenced block; no markdown headers; no HTML comments) | Round-2 codex HIGH 4 Option A | PASSED |
| `_profile.example.md` parsed dict has EXACTLY `{verbosity, citation_density, save_report, disambiguation}` keys | D-PROF-01 + D-PROF-02 | PASSED |
| `_profile.example.md` defaults are `standard / inline / True / always-ask` | D-PROF-04 | PASSED |
| `_profile.example.md` does NOT contain calc-input field tokens (`joint_income`, `state_fips`, `county_fips`, `monthly_debts`, `target_property_value`, `default_loan_term`) | D-PROF-02 | PASSED |
| `.gitignore` blocks `.claude/skills/mortgage-ops/modes/_profile.md` | D-PROF-03 | PASSED |
| `scripts/hooks/block-user-layer.py` USER_LAYER_PATTERNS contains `.claude/skills/mortgage-ops/modes/_profile.md` | D-PROF-03 | PASSED |
| `tests/test_block_user_layer.py` parametrize list contains BOTH legacy `modes/_profile.md` AND new `.claude/skills/mortgage-ops/modes/_profile.md` | Round-2 codex HIGH 3 + LOW 11 | PASSED |
| `pytest tests/test_block_user_layer.py -q` passes | Plan §Task 3 verify | PASSED (28 passed) |
| `DATA_CONTRACT.md` User Layer table contains the corrected path | DATA_CONTRACT line 73-74 sync | PASSED |
| `DATA_CONTRACT.md` does NOT enumerate the OLD project-root `modes/_profile.md` path | Round-2 codex line 19 correction | PASSED |
| End-to-end: `python scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md` exits 1 with file named in stderr | Round-2 codex HIGH 3 | PASSED |
| All 7 mode files have the 4-section UI-SPEC §b spine | SKLL-05 | PASSED |
| `modes/stress.md` contains literal `if it exists` AND `.claude/agents/stress-test-agent.md` | D-SUBA-FW-02 | PASSED (both 2 occurrences) |
| `modes/evaluate.md` dispatches to BOTH `affordability.py` AND `amortize.py` | UI-SPEC §a row 1-2 + plan SC | PASSED |
| `modes/refinance.md` contains refi+ARM ambiguity rule | UI-SPEC §a Case 1 | PASSED |
| `modes/affordability.md` contains affordability+amortize ambiguity rule | UI-SPEC §a Case 2 | PASSED |
| Each mode file references its relocated script path under `.claude/skills/mortgage-ops/scripts/` | Plan 10-01 SC-3 | PASSED (all 7) |
| Each mode file ≤ 2500 cl100k tokens | UI-SPEC §b density rule | PASSED (all 7; max 1591) |

## End-to-End User Layer Enforcement Test

```
$ echo "test" > .claude/skills/mortgage-ops/modes/_profile.md
$ git add .claude/skills/mortgage-ops/modes/_profile.md
The following paths are ignored by one of your .gitignore files:
.claude/skills/mortgage-ops/modes/_profile.md
hint: Use -f if you really want to add them.
$ git status --short | grep _profile.md   # no output -- gitignored, no stage
$ python scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md
ERROR: refusing to commit User Layer files (DATA_CONTRACT.md):
  - .claude/skills/mortgage-ops/modes/_profile.md
$ echo $?
1
$ rm .claude/skills/mortgage-ops/modes/_profile.md
```

Triple-check enforcement verified: gitignore blocks bare `git add`; the hook rejects with exit 1 + offending file named in stderr when invoked with the candidate path AS argv (Round-2 codex HIGH 3 — NOT with no args, which would have returned 0 for the wrong reason).

## Cross-Link Audit: Mode → references/*.md

Every mode file ends with a RELATED REFERENCES footer naming Wave 4 reference files. Wave 4 (Plan 10-04) ships these 9 reference files; this audit confirms cross-links are in place.

| Mode | references/*.md cross-links |
|------|-----------------------------|
| evaluate.md | amortization-formulas.md, affordability-rules.md, apr-reg-z.md, spreadsheet-conventions.md |
| compare.md | refi-npv.md, points-breakeven.md, amortization-formulas.md |
| refinance.md | refi-npv.md, tax-deductibility.md, points-breakeven.md |
| affordability.md | affordability-rules.md, gse-limits.md, mip-pmi.md |
| stress.md | stress-tests.md, arm-mechanics.md, affordability-rules.md |
| amortize.md | amortization-formulas.md, spreadsheet-conventions.md |
| arm.md | arm-mechanics.md, amortization-formulas.md |

All 9 Wave-4 references are referenced by at least one mode file (amortization-formulas: 4 modes; affordability-rules: 3; refi-npv: 2; etc.). Wave 5 CI may assert this cross-link coverage if needed.

## Phase 11 Forward-Link Confirmation in modes/stress.md

`modes/stress.md` carries the D-SUBA-FW-02 EXISTENCE-CHECK SEAM in the `## What scripts to call` section (subsection PHASE 11 SUBAGENT FORWARD-LINK). The seam contains BOTH required literal substrings:

- Literal phrase `if it exists` (2 occurrences — once in the rule statement, once in the user-visible behavior callout)
- Literal path `.claude/agents/stress-test-agent.md` (2 occurrences — same)

The N > 5 scenario threshold is documented; for `scenario_count ≤ 5` inline execution is mandated regardless of agent existence (context cost not justified).

When Phase 11 lands by writing `.claude/agents/stress-test-agent.md`, dispatch activates automatically. NO edit to `modes/stress.md` is required.

## DATA_CONTRACT.md Sync-Rule Compliance

DATA_CONTRACT.md line 73-74 sync rule:

> The User Layer paths in this document must match the `USER_LAYER_PATTERNS` and `USER_LAYER_GLOB_DIRS` tuples in `scripts/hooks/block-user-layer.py` exactly. Both lists are kept in sync by editing this file and the hook source in the same commit.

Task 3 commit (`784dd63`) edits FOUR files in one commit: `.gitignore` + `scripts/hooks/block-user-layer.py` + `tests/test_block_user_layer.py` + `DATA_CONTRACT.md`. The hook source + DATA_CONTRACT update together (per the explicit line 73-74 rule); the gitignore + parametrize test extend the discipline to the gitignore enforcement layer + CI test layer. Wave 3 lands the entire enforcement quadruple in a single commit so no intermediate commit could leave the layers inconsistent.

## Decisions Made

None beyond the LOCKED DECISIONS already pinned by 10-CONTEXT.md and the Round-2 review. The plan was executed verbatim:

- D-10 honored (every mode file references `modes/_shared.md FIRST`)
- D-13-01..D-13-05 honored (Save Report step in `_shared.md`; SKLL-13 closes)
- D-NUM-01..D-NUM-06 honored (Output Formatting section + ARM bps)
- D-PROF-01 honored (4-key schema)
- D-PROF-02 honored (no calc-input duplication)
- D-PROF-03 honored (User Layer enforcement triple-check)
- D-PROF-04 honored (fallback defaults)
- D-SUBA-FW-02 honored (existence-check seam)
- Round-2 codex HIGH 2 honored (real `db-write.mjs insert-report` CLI; no fictional flags)
- Round-2 codex HIGH 3 honored (hook test exercises argv-based invocation; parametrize extended)
- Round-2 codex HIGH 4 Option A honored (pure-YAML `_profile.example.md`)

## Deviations from Plan

None — plan executed exactly as written, with one micro-adjustment caught during execution:

**1. [Self-correction] Trimmed `modes/_shared.md` token count from 3752 → 3447 to fit under 3500 cap**
- **Found during:** Task 1 verification (`count_tokens(open(p).read())` returned 3752, over the 3500 budget)
- **Issue:** initial draft of `_shared.md` exceeded the token cap by 252 tokens because the `## Output Formatting` section had verbose inline-template descriptions and `## Save Report` had redundant "Round-2 codex HIGH 2" annotations that were ALREADY captured in the prose decision pointers
- **Fix:** compressed the `Output Formatting` inline-template list to a one-liner (templates remain mentally applicable; the example tokens `$1,264.14` / `6.500%` / `43.0%` / `250 bps (2.50%)` are still present); compressed `Save Report` step intros without dropping any required substring or step body
- **Files modified:** `.claude/skills/mortgage-ops/modes/_shared.md` only
- **Commit:** included in Task 1 commit `15236b0` (the trim happened pre-commit during verify-fail iteration)

**2. [Self-correction] Removed direct `--insert-report --json` substring from `_shared.md` Forbidden Behaviors**
- **Found during:** Task 1 verification (forbidden-substring grep flagged `--insert-report --json`)
- **Issue:** the original draft of the `## Forbidden Behaviors` section included an explicit "do not use the fictional `db-write.mjs --insert-report --json` flag" bullet, which itself contained the forbidden substring and tripped the grep guard
- **Fix:** rephrased the bullet to "Inventing CLI flag forms that the real `db-write.mjs` handler does not expose — use only the documented subcommands listed in the Save Report section above (`insert-report --scenario-id <int> --file <path>`, `query --sql "..."`)." This conveys the same prohibition without naming the prohibited form
- **Files modified:** `.claude/skills/mortgage-ops/modes/_shared.md` only
- **Commit:** included in Task 1 commit `15236b0`

**3. [Self-correction] Removed `state_fips` / `county_fips` substrings from `_profile.example.md` D-PROF-02 comment**
- **Found during:** Task 2 verification (substring grep flagged `state_fips` and `county_fips` even though they appeared only inside YAML comments listing what NOT to put in the file)
- **Issue:** the comment listing calc-input fields contained the literal tokens, tripping the substring guard meant to catch actual key duplication
- **Fix:** rephrased the comment to "geography FIPS codes" instead of listing the specific `state_fips` / `county_fips` token names. Semantic intent preserved; substring guard satisfied
- **Files modified:** `.claude/skills/mortgage-ops/modes/_profile.example.md` only
- **Commit:** included in Task 2 commit `3ab3cac`

These three micro-adjustments are NOT plan deviations — they are verify-loop iterations that occurred BEFORE the respective task commits. The committed content satisfies every acceptance criterion as written.

## Issues Encountered

None blocking.

## Self-Check: PASSED

**Files exist:**

- FOUND: `.claude/skills/mortgage-ops/modes/_shared.md` (263 lines / 3447 tokens)
- FOUND: `.claude/skills/mortgage-ops/modes/_profile.example.md` (42 lines)
- FOUND: `.claude/skills/mortgage-ops/modes/evaluate.md` (142 lines / 1435 tokens)
- FOUND: `.claude/skills/mortgage-ops/modes/compare.md` (114 lines / 1214 tokens)
- FOUND: `.claude/skills/mortgage-ops/modes/refinance.md` (125 lines / 1440 tokens)
- FOUND: `.claude/skills/mortgage-ops/modes/affordability.md` (146 lines / 1510 tokens)
- FOUND: `.claude/skills/mortgage-ops/modes/stress.md` (151 lines / 1591 tokens)
- FOUND: `.claude/skills/mortgage-ops/modes/amortize.md` (120 lines / 1154 tokens)
- FOUND: `.claude/skills/mortgage-ops/modes/arm.md` (142 lines / 1523 tokens)

**Commits exist (verified via `git log --oneline`):**

- FOUND: `15236b0` feat(10-03): ship modes/_shared.md (D-10 inheritance + 12 mandatory sections)
- FOUND: `3ab3cac` feat(10-03): ship modes/_profile.example.md (D-PROF-01 4-key schema)
- FOUND: `784dd63` feat(10-03): wire User Layer enforcement triple for skill _profile.md
- FOUND: `79e0e7d` feat(10-03): ship 7 mode files (evaluate, compare, refinance, affordability, stress, amortize, arm)

**Acceptance gates (all 4 tasks):**

All gates listed in the Substring-Presence Audit table above PASSED. End-to-end User Layer enforcement test PASSED. Token budgets PASSED. Pytest baseline preserved (550 → 551 passed; the +1 is a new parametrize case).

**Test suite:**

- 551 passed / 4 skipped / 16 xfailed / 0 failed / 0 errored: PASSED (Wave 2 baseline +1 parametrize case preserved; no regressions)

## Next Wave Readiness

Wave 4 (Plan 10-04 references/*.md) can proceed:

- Each mode file's RELATED REFERENCES footer names the Wave-4 references files; Wave 4 ships them. The cross-link audit table above documents which references are referenced by which modes.
- `_shared.md` § Sources of Truth lists `references/*.md` as "ON DEMAND only (D-09 progressive disclosure); see SKILL.md topic→reference table" — Wave 4 lands the actual files behind that table.
- Wave 4 also ships `references/data-layer.md` (already exists from Phase 9) into the skill folder; `_shared.md` § Script Invocation Doctrine cross-references it.

Wave 5 (Plan 10-05 CI tests) flips the Wave-0 xfail stubs against this Wave-3 surface. The Substring-Presence Audit table documents every assertion Wave 5 needs.

Wave 6 (Plan 10-06 end-to-end smoke) exercises the Save Report step against a real DuckDB instance. The CLI invocations in `_shared.md` § Save Report are taken verbatim from `orchestration/db-write.mjs:296-310` (the real Phase 9 surface), so the Wave 6 smoke runs against the real handler — no mocks needed.

Phase 11 (subagents) can land by writing `.claude/agents/{amortization,refi-npv,stress-test}-agent.md`. `modes/stress.md` already carries the D-SUBA-FW-02 existence-check seam; dispatch activates automatically when the agent file is present. Zero edits to Wave-3 surface required.

---
*Phase: 10-claude-skill*
*Plan: 03*
*Completed: 2026-05-10*
