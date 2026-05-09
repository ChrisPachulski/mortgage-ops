# Phase 10: Claude Skill Frontend - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning (existing 7 plans must be replanned against these decisions via `/gsd-plan-phase 10 --reviews` or replan-from-scratch)

<domain>
## Phase Boundary

Build `.claude/skills/mortgage-ops/` — a self-contained Anthropic Agent Skill bundle that routes seven natural-language mortgage tasks (`evaluate`, `compare`, `refinance`, `affordability`, `stress`, `amortize`, `arm`) to seven JSON-in/JSON-out Python scripts physically relocated from project-root `scripts/` to `.claude/skills/mortgage-ops/scripts/`. SKILL.md (≤ 500 lines, ≤ 4500 cl100k tokens, routing in first 200 lines) carries the routing table, the math-discipline doctrine, and the run-help-first doctrine. Nine progressive-disclosure references load on demand. Modes load from `modes/{name}.md`; `modes/_shared.md` carries the shared scoring/report/narration template; `modes/_profile.example.md` is committed as the User Layer customization schema (`_profile.md` itself is gitignored). `LICENSE.txt` is bundled with MIT terms.

This phase does NOT add subagents — those ship in Phase 11. This phase DOES close SKLL-13 (auto-write reports + DuckDB ingest) by adding a "Save Report" step at the end of every mode invocation.

</domain>

<decisions>
## Implementation Decisions

### SKLL-13 Reports Flow (Area 1)

- **D-13-01: Phase 10 closes SKLL-13.** modes/_shared.md adds a "Save Report" step at the end of every mode invocation. The skill is responsible for both writing the report file and persisting it to DuckDB.
- **D-13-02: Filename convention.** `reports/{seq:03d}-{mode}-{YYYY-MM-DD}.md`. Sequence number derived from `SELECT COUNT(*)+1 FROM reports` at write time. Slug = mode name (one of: evaluate / compare / refinance / affordability / stress / amortize / arm). Date = current ISO date. Example: `reports/042-stress-2026-05-08.md`.
- **D-13-03: Auto-write on every invocation.** No SKILL.md-level opt-out — every mode invocation produces a report. The User Layer override knob `save_report: false` in `modes/_profile.md` (D-PROF-01) is the only escape hatch; the skill default is unconditional save. Rationale: matches FND-09 "every dollar figure traces" philosophy; reports/ is gitignored (Phase 1 FND-08) so no git noise.
- **D-13-04: Persistence call.** Each report invokes `node orchestration/db-write.mjs --insert-report --json {meta}` after writing the .md file. The JSON `--json` payload contains: `{ "scenario_id": <int>, "kind": "<mode>", "markdown_blob": <full file contents>, "filename": "reports/{seq:03d}-{mode}-{YYYY-MM-DD}.md" }`. The withLock-gated INSERT is already shipped (Phase 9 D-03-04 PERS-03 closure).
- **D-13-05: Test coverage.** Phase 10 ships at least 2 new flips on top of the existing Wave-0 stub set: (a) `test_skll_13_report_file_written` — invoking any mode produces a `reports/{seq}-{mode}-{date}.md` matching the convention; (b) `test_skll_13_report_persisted_to_db` — after the mode invocation, `SELECT COUNT(*) FROM reports WHERE filename = ?` returns 1. Wave 5 wires both.

### modes/_profile.example.md Schema (Area 2)

- **D-PROF-01: Four committed fields.** The shipped example schema contains exactly these four knobs (no more — keep _profile.md narrow to skill behavior, not calc inputs):

  ```yaml
  # modes/_profile.example.md  (User Layer — copy to modes/_profile.md and edit; _profile.md is gitignored)
  verbosity: standard         # concise | standard | verbose
  citation_density: inline    # full | inline | minimal
  save_report: true           # true (default) | false to opt out of D-13-03 auto-write
  disambiguation: always-ask  # always-ask (default) | auto-pick
  ```

  - `verbosity` scales narration length (D-VOICE-02 mapping).
  - `citation_density` controls how aggressively regulatory references appear in narration (full = every claim cited; inline = key claims; minimal = only blocking claims like DTI cap rejections).
  - `save_report: false` is the ONLY user-level override of D-13-03's unconditional auto-write.
  - `disambiguation: auto-pick` silently routes ambiguous prompts to the most-likely mode; `always-ask` (default) matches UI-SPEC's printed disambiguation question.

- **D-PROF-02: No duplication of calc inputs.** Calc inputs (joint income, applicants, monthly debts, state_fips/county_fips, escrow, va block, target property value, lender preferences) stay in `config/household.yml` + `config/profile.yml` per Phase 1 DATA_CONTRACT User Layer. The skill-level `_profile.md` is for SKILL behavior knobs only. If a future field is "should I look up X in household.yml or profile.yml or _profile.md?", the answer is whichever Phase 1 file already covers it — `_profile.md` does NOT duplicate.

- **D-PROF-03: User Layer commit discipline (inherits D-07).** `_profile.example.md` committed; `_profile.md` gitignored; pre-commit hook `scripts/hooks/block-user-layer.py` extends to reject staged changes to `modes/_profile.md` (Phase 1 FND-10 pattern).

- **D-PROF-04: _shared.md reads _profile.md as source-of-truth.** When `_profile.md` is missing on disk (fresh checkout, user hasn't customized), `_shared.md` falls back to the four defaults (`standard / inline / true / always-ask`). Document this fallback in `_shared.md` § "Profile Loading".

### Voice / Tone (Area 3)

- **D-VOICE-01: Default voice = semi-clinical-with-citations.** At `verbosity: standard` (the default), every numeric result follows the three-part template:
  1. **Number first** — bare value with units (`Back-end DTI: 0.45`)
  2. **1-2 sentence interpretation** — what it means in context (`This exceeds the 0.43 ATR/QM cap`)
  3. **Citation last** — regulatory or doc anchor (`Per CFPB §1026.43`)

  This matches UI-SPEC §Copywriting Contract verbatim. The narration template in `modes/_shared.md` enforces this structure.

- **D-VOICE-02: Verbosity knob mapping.** The `verbosity` field in `_profile.md` (D-PROF-01) scales the standard template:
  - `concise` — number + 1-line context. Citations dropped unless blocking. Skip interpretation when number is unambiguous.
  - `standard` — full UI-SPEC three-part template above. Default.
  - `verbose` — full citations + worked-example breakdowns + footnoted cross-references to references/*.md.

- **D-VOICE-03: Per-mode voice override deferred.** The "per-mode customization" option (e.g., stress.md formal, affordability.md conversational) was considered and rejected for v1 — adds plumbing without clear benefit. All modes ship with the standard template; a future phase can revisit if user feedback warrants per-mode tones.

### Numeric Formatting (Area 3)

- **D-NUM-01: Money — `$1,264.14`.** Always 2 decimal places, comma thousand separators, `$` prefix. Matches CFPB Loan Estimate disclosure convention. Examples: `$400,000.00`, `$2,528.27/mo`, `$163,200.00`.
- **D-NUM-02: Rates — `6.500%`.** Always 3 decimal places, trailing zeros preserved, `%` suffix. Matches Reg Z APR disclosure precision. Examples: `6.500%` (not `6.5%`), `3.875%`, `0.000%` (theoretical floor).
- **D-NUM-03: Ratios (DTI / LTV / CLTV) — `43.0%`.** Always 1 decimal place, `%` suffix. Matches CFPB consumer-facing disclosure. Examples: `43.0%`, `97.5%` (FHA at-ceiling LTV), `0.0%` (no second lien CLTV). NOT raw decimal `0.43`. NOT integer `43%`.
- **D-NUM-04: ARM bps — `250 bps (2.50%)`.** ARM mode (modes/arm.md) shows margin/caps/floors in basis points with parenthesized percent. Other modes use percent only (D-NUM-02). Examples: `periodic_cap: 200 bps (2.00%)`, `lifetime_cap: 500 bps (5.00%)`, `margin: 275 bps (2.75%)`.
- **D-NUM-05: Internal Decimal precision unchanged.** All formatting is a DISPLAY layer in `modes/_shared.md` § "Number Formatting" (or equivalent). `lib/` continues to round at end-of-period only (Phase 1 D-01 / Phase 5 D-14 _quantize_rate at 6dp). The display layer does not propagate back into Decimal storage.
- **D-NUM-06: Helper location.** Display formatters (`fmt_money`, `fmt_rate`, `fmt_ratio`, `fmt_bps`) live in `_shared.md` as inline templates Claude follows during narration — NOT as Python helpers in `lib/`. Rationale: skill output is Claude's narration, not script output; scripts return raw Decimal-string JSON and Claude formats per these conventions when narrating.

### Phase 11 Subagent Forward-Reference (Area 4)

- **D-SUBA-FW-01: SKILL.md ships a "## Subagents (Phase 11)" section.** One paragraph naming the three Phase 11 subagents and what each handles:
  - `amortization-agent` (Haiku) — single-loan ARM amortization requests
  - `refi-npv-agent` (Sonnet) — multi-step NPV reasoning, sweeps multiple offers
  - `stress-test-agent` (Haiku) — parameter-grid sweeps; returns < 1k token summary

  The paragraph is forward-link only — it tells Claude these agents will exist when Phase 11 lands; it does NOT instruct Claude to delegate to them. Token budget impact: ~80-120 cl100k tokens; absorbed within the 4500-token ceiling.

- **D-SUBA-FW-02: modes/stress.md gets the existence-check escape hatch.** Single load-bearing instruction added:

  > "For sweeps with N > 5 scenarios, defer to `.claude/agents/stress-test-agent.md` if it exists; otherwise run the stress sweep inline."

  The `if it exists` check is the seam — Phase 11 lands by writing the agent file, and SKILL.md does NOT need a follow-up commit. Phase 10 ships with the file absent → inline execution; Phase 11 ships with the file present → delegation. Same SKILL.md token footprint either way.

- **D-SUBA-FW-03: 10-05 'subagent forward-link' bonus test pins both surfaces.** The Wave-5 forward-link test asserts:
  1. `SKILL.md` contains the `## Subagents (Phase 11)` section header AND all three agent filenames (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`).
  2. `modes/stress.md` contains the literal substring `if it exists` AND the agent path `.claude/agents/stress-test-agent.md`.
  3. (Optional, deferred to Phase 11): an end-to-end test that the existence-check actually delegates correctly when the agent file is present.

### Claude's Discretion

- Exact wording of SKILL.md routing examples (UI-SPEC §"Routing UX (a)" already locks 10 worked examples — use those verbatim or paraphrase as needed for token budget).
- Exact `_shared.md` section ordering (PATTERNS already lists 9 required sections; planner picks the order).
- Exact LICENSE.txt copyright holder line (RESEARCH §h suggests "Copyright (c) 2026 Pachulski Household" — planner can use that or substitute "Christopher Pachulski" for personal-use precision).
- Whether Wave 0's existing 13 xfail stubs need to grow to 15+ for D-13-05 (planner decides: 2 new strict-xfail stubs OR fold into existing test_db_lifecycle.py extension).
- Token-budget allocation between routing skeleton (first 200 lines), math discipline doctrine, modes table, references table, and subagent stub paragraph — planner balances within 4500 cl100k token ceiling.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 10 artifacts (already on disk)
- `.planning/phases/10-claude-skill/10-RESEARCH.md` — Anthropic skill spec verbatim, anthropics/skills/webapp-testing exemplar, tokenizer choice rationale, script-relocation strategy lock (option (i) MOVE), LICENSE.txt MIT default
- `.planning/phases/10-claude-skill/10-PATTERNS.md` — file classification (NEW vs MODIFIED), Critical Issues #1-#6, mode-routing table, context-loading-by-mode, math-discipline doctrine wording, _shared.md / _profile.md / individual-mode templates, subprocess-only CLI testing pattern
- `.planning/phases/10-claude-skill/10-UI-SPEC.md` — design system, copywriting contract, 10 worked routing examples, disambiguation strategy, mode file format spec, 6-key Pydantic error envelope narration template, sample modes/amortize.md skeleton

### Phase contracts this phase consumes
- `.planning/phases/01-foundations-money-discipline/01-CONTEXT.md` — DATA_CONTRACT layer rules (User Layer is read-only; pre-commit hook FND-10)
- `.planning/phases/03-core-amortization/03-CONTEXT.md` — D-17 documents "Phase 10 physically relocates"; SCRIPT_PATH constants pattern
- `.planning/phases/05-arm-modeling/05-CONTEXT.md` — D-13 caller-supplied `assumed_index_rate`; FRED MCP populates at narration time (Phase 12)
- `.planning/phases/09-duckdb-orchestration/09-RESEARCH.md` — Decimal-as-VARCHAR discipline (Critical Issue 2); reports table schema
- `.planning/phases/09-duckdb-orchestration/09-VERIFICATION.md` — confirmed cmdInsertReport handler ships (Phase 9 D-03-04)

### Project-level
- `.planning/REQUIREMENTS.md` — SKLL-01..SKLL-13 wording (line 133-145)
- `.planning/ROADMAP.md` — Phase 10 section line 195+ (SC-1..SC-5)
- `CLAUDE.md` — money discipline, skill portability, `scripts/`/`references/`/`assets/`/`LICENSE.txt` INSIDE skill folder, 500 lines / 5k tokens budget, references progressive disclosure, run-help-first doctrine, no AI attribution
- `.planning/PROJECT.md` — core value (math correctness; LLM is router/narrator, never owns numbers)

### External (Anthropic spec — locked verbatim from RESEARCH)
- `agentskills.io/specification` — frontmatter contract (`name`, `description`, `license`, `compatibility` free-form text)
- `code.claude.com/docs/en/skills` — progressive disclosure budget
- `platform.claude.com/docs/en/agents-and-tools/agent-skills/overview` — 5000-token recommendation
- `raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md` — canonical complex-skill exemplar (math discipline + run-help-first wording lifted verbatim)

### Phase 9 contracts now consumed
- `orchestration/db-write.mjs` — `--insert-report` subcommand (Phase 9 D-03-04 PERS-03 closure)
- `orchestration/init-db.mjs` — reports table schema (markdown_blob TEXT NOT NULL; Phase 9 D-02-04)
- `orchestration/lockfile.mjs` — `withLock` wrapping all DB writes (Phase 9 PERS-05)
- `data/known-loans.yml` — `loan_type:` keyed catalog with 7 entries (Phase 9 D-05-02-revised; consumed by SKILL.md routing examples)
- `references/data-layer.md` — Phase 9 onboarding doc; SKILL.md cross-references it from the routing skeleton

### Phase 11 forward-link surfaces (per D-SUBA-FW-01..03)
- `.claude/agents/amortization-agent.md` — does NOT exist at Phase 10 ship; Phase 11 creates it
- `.claude/agents/refi-npv-agent.md` — does NOT exist at Phase 10 ship; Phase 11 creates it
- `.claude/agents/stress-test-agent.md` — does NOT exist at Phase 10 ship; Phase 11 creates it. modes/stress.md `if it exists` check is the seam.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **Phase 9 orchestration/db-write.mjs** (`cmdInsertReport`): the SKLL-13 auto-write step (D-13-04) calls this verbatim — no new Node code needed.
- **Phase 9 orchestration/lockfile.mjs** (`withLock`): D-13's INSERT path inherits the lock discipline; SKILL.md does not need to know about the lockfile mechanism.
- **Phase 1 scripts/hooks/block-user-layer.py**: the User Layer enforcement hook already gates `config/household.yml` + `config/profile.yml`. Plan 10-03 extends this gate to `modes/_profile.md` (D-PROF-03 inherits this pattern).
- **Phase 5 lib/money.py `_quantize_rate`**: already at 6 decimal places. Display formatters in `_shared.md` (D-NUM-06) consume the quantized output and only rebound for narration.
- **Phase 1-8 references/* docs** (arm-mechanics.md, refi-npv.md, apr-reg-z.md, stress-tests.md, points-breakeven.md): the 9 reference files in Phase 10 either COPY (arm-mechanics, per Critical Issue #4) or forward-link (refi-npv, apr-reg-z) into `.claude/skills/mortgage-ops/references/`.
- **Phase 1 config/household.yml + config/profile.yml**: User Layer schemas already cover calc inputs (D-PROF-02). `modes/_profile.example.md` (D-PROF-01) does NOT duplicate any field these cover.

### Established Patterns

- **Subprocess-only CLI testing** (PATTERNS line 803): every test invokes `subprocess.run([sys.executable, str(SCRIPT_PATH), ...])` with `cwd=REPO_ROOT`, never imports the script as a module. Survives the Phase 10 relocation transparently — only `SCRIPT_PATH` constants change.
- **Filesystem-introspection meta-tests** (PATTERNS line 811): tests assert on directory structure (e.g., `for f in EXPECTED_REFERENCES: assert (skill_root / "references" / f).exists()`). Pattern continues for SC-3 / SC-4 / SC-5 verification in Wave 5.
- **Strict-xfail stub pattern** (Phase 9 Wave 0): D-13-05's two new flips follow the same `@pytest.mark.xfail(strict=True)` → flip-via-real-test-body discipline used through Phase 9.
- **D-29 cite-from-doc paragraphs** (Phase 7/8): `lib/*.py` modules carry a docstring paragraph citing the relevant references/*.md. Phase 10 SKILL.md inherits this idiom by listing all 9 reference filenames in a topic→reference table (PATTERNS Mode Routing section).
- **Pre-flight existence check seam** (Phase 9 D-06 timeout strategy): the "file-exists check is the seam" pattern is reused in D-SUBA-FW-02 — Phase 11 lands by writing the agent file; no SKILL.md edit needed.

### Integration Points

- **SKILL.md → orchestration/db-write.mjs**: SKLL-13 auto-write step (D-13-04) shells out via `node orchestration/db-write.mjs --insert-report --json {meta}`. Path is relative to project root (NOT skill folder), reflecting the "Node orchestration owns DuckDB" tier per Phase 9 architecture.
- **modes/_shared.md → modes/_profile.md (or fallback defaults)**: D-PROF-04 fallback discipline. `_shared.md` reads `_profile.md` if present; defaults to (`standard / inline / true / always-ask`) if absent.
- **modes/stress.md → .claude/agents/stress-test-agent.md (Phase 11)**: D-SUBA-FW-02 existence-check seam.
- **scripts/{amortize,affordability,arm_simulate}.py → .claude/skills/mortgage-ops/scripts/**: physical relocation (Plan 10-01) flips test SCRIPT_PATH constants. Phase 6/7/8 scripts (refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py) ship directly into the skill folder per D-08 cross-phase contract.

</code_context>

<specifics>
## Specific Ideas

- **Filename example**: `reports/042-stress-2026-05-08.md` (D-13-02 sequence + mode + date format).
- **Routing copy from UI-SPEC**: 10 worked examples are the canonical voice baseline (D-VOICE-01). The planner uses these verbatim or near-verbatim for SKILL.md routing examples to maintain consistency.
- **Voice example (verbose tier)**: "Back-end DTI: **0.45**. This is **2 percentage points** above the **0.43** ATR/QM cap (CFPB §1026.43(c)(2)) — lenders may still approve under non-QM with compensating factors (e.g., 6+ months reserves, residual income > 120% of VA grid, or LTV ≤ 75%). See `references/affordability-rules.md` §"ATR/QM Pathways" for the full compensating-factor matrix."
- **Voice example (concise tier)**: "Back-end DTI: 0.45 (over 0.43 ATR/QM cap)."
- **Voice example (standard tier — default)**: "Back-end DTI: 0.45. This exceeds the 0.43 ATR/QM cap. Per CFPB §1026.43, lenders may still approve under non-QM with compensating factors."
- **ARM-mode narration example (D-NUM-04)**: "After month 60: rate steps to **6.500%** (margin 275 bps + index 3.750%, capped at periodic_cap of 200 bps (2.00%)). New monthly P&I: **$2,652.41** (was $2,528.27)."

</specifics>

<deferred>
## Deferred Ideas

- **Per-mode voice customization** (Area 3, Option 4 considered + rejected): all modes ship with the standard semi-clinical template at v1. Future phase may revisit if user feedback shows specific modes feel wrong-toned.
- **Auto-pick disambiguation as default** (Area 2 Option D-PROF-01: 4th field, default = `always-ask`): power-user opt-in via `_profile.md`; not the v1 default to avoid silent mis-routing.
- **Discovery mode UX** (no-args invocation flow): not discussed; planner uses default behavior from PATTERNS line 432 ("Discovery Mode (no arguments)" section). Future phase may revisit for first-run UX polish.
- **Per-script `--save` flag** (Area 1 Option 4 considered + rejected for v1): not adopted; D-13-03 ships unconditional save with `_profile.md` opt-out as the only override.
- **Subagent end-to-end delegation test** (D-SUBA-FW-03 #3): deferred to Phase 11 as part of SUBA-04/05 verification. Phase 10 ships only the file-existence-check seam, not the runtime delegation test.
- **Token-budget recovery if SKILL.md exceeds 4500 cl100k post-D-SUBA-FW-01**: if the subagent stub paragraph plus everything else exceeds budget, planner first compacts the references topic→reference table to a 1-line-per-ref form, then trims routing-example prose, then escalates to the user. Not expected to bind given current research estimate.

</deferred>

---

*Phase: 10-claude-skill*
*Context gathered: 2026-05-08*
