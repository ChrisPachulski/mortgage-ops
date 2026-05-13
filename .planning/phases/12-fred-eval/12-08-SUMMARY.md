---
phase: 12-fred-eval
plan: 08
subsystem: references-fred-context
tags: [phase-12, wave-8, references, progressive-disclosure, documentation, fred-context, phase-12-closure]

# Dependency graph
requires:
  - phase: 12-fred-eval
    plan: 01
    provides: scripts/fred_cli.py (HTTP wrapper canonical per D-12-LIVE01-01) — documented here as §1
  - phase: 12-fred-eval
    plan: 02
    provides: lib/fred_cache.py (7-day TTL cache + lockfile port) — documented here as §3
  - phase: 12-fred-eval
    plan: 03
    provides: SKILL.md `## Live Mortgage Rates` section (D-12-LIVE02-01 Pattern A) — documented here as §4
  - phase: 12-fred-eval
    plan: 04
    provides: evals/metrics.py STDOUT-only sourcing (D-12-SC3-01) — documented here as §5
  - phase: 12-fred-eval
    plan: 05
    provides: evals/prompts/live-rate-injection-01.md (SC-1 closure eval) — documented here as §5
  - phase: 12-fred-eval
    plan: 06
    provides: evals/expected/live-rate-injection-01.json (fixture oracle with provenance:static) — documented here as §5
  - phase: 12-fred-eval
    plan: 07
    provides: REQUIREMENTS.md LIVE-01/02 wording (HTTP-canonical canon) — referenced from §2 rationale
  - phase: 10-claude-skill
    provides: SKILL.md references-table progressive-disclosure pattern (D-09) — extended here with the fred-context.md row
  - phase: 05-arm
    provides: references/arm-mechanics.md 6-section template — inherited as the doc skeleton
  - phase: 07-estimated-apr
    provides: references/apr-reg-z.md Citation Index appendix idiom — inherited verbatim
provides:
  - .claude/skills/mortgage-ops/references/fred-context.md (559-line long-form reference)
  - SKILL.md references-table fred-context.md row (FRED / MORTGAGE30US / current-rate triggers)
  - CLAUDE.md External integrations bullet rewrite (HTTP-canonical + MCP-optional)
  - .claude/agents/README.md "Phase 12: FRED MCP Server (optional)" section
  - 2 new supplementary tests (no xfail; ship green) in tests/test_skill_md_fred.py
  - Phase 12 v1 closure: 8 functional requirements + 5 SC + 5 D-12 locks all green
affects: [progressive-disclosure, phase-12-closure, future-fred-mcp-v2-reconsideration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - 6-section template + Citation Index appendix (inherited verbatim from references/arm-mechanics.md + references/apr-reg-z.md per D-28 LOCKED in Phase 7)
    - Progressive-disclosure references-table extension (Phase 10 D-09 — SKILL.md gains one row, loaded on-demand only)
    - HTTP-canonical / MCP-optional documentation pattern (NEW Phase 12 pattern — D-12-LIVE01-01)
    - Plan-test joint-pin idiom (Plan 12-03 + Plan 12-08 jointly pin SKILL.md grep invariants — section §4 Routing Rule table)
    - Cite-from contract: fred-context.md cites scripts/fred_cli.py module docstring + lib/fred_cache.py + 12-CONTEXT.md D-12 locks
    - Citation Index annual re-validation cadence (URLs verified 2026-05-10; rev each calendar year)

key-files:
  created:
    - .claude/skills/mortgage-ops/references/fred-context.md (559 lines, 6 numbered sections + Citation Index appendix)
    - .planning/phases/12-fred-eval/12-08-SUMMARY.md (this file)
  modified:
    - .claude/skills/mortgage-ops/SKILL.md (1 new row appended to references-table after spreadsheet-conventions.md)
    - CLAUDE.md (External integrations bullet rewritten — HTTP-canonical + cross-link)
    - .claude/agents/README.md (new "Phase 12: FRED MCP Server (optional)" section appended before "## No AI attribution")
    - tests/test_skill_md_fred.py (2 new supplementary tests appended; no xfail; both ship green)

key-decisions:
  - "Plan-test joint-pin idiom: SKILL.md grep invariants (heading literal, 4-token presence, no `!`-injection, position vs Math Discipline, token+line budgets) are pinned by tests/test_skill_md_fred.py Plan 12-03 tests AND newly documented in fred-context.md §4 as a routing-rule reference table — joint surface makes intent legible without coupling code to docs"
  - "Citation Index annual re-validation cadence (2026-05-10 stamp) inherits the references/arm-mechanics.md + references/apr-reg-z.md convention — each calendar year, confirm each URL still resolves; if any have moved, update the index + inline references in one commit"
  - "Per-series cache file layout (NOT combined fred-cache.json) is pinned by D-12-LIVE02-01 SKILL.md citations; fred-context.md §3 documents this and explicitly cross-references the SKILL.md citations so a future consolidation would be visibly breaking"
  - "MCP server section §2 documents three rationale points for HTTP-as-canonical (determinism for CI, no system dependency, upstream gap — fred-mcp-server v1.0.2 has no shell-invocable CLI) plus a v2-reconsideration carve-out for when Anthropic's MCP runtime ships with Claude Code AND upstream ships a fred-cli binary"

requirements-completed: []
# Plan 12-08 closes the LAST documentation layer for Phase 12; the underlying
# requirements (LIVE-01..04 + EVAL-01..04) are CLOSED by Plans 12-01..07.

# Metrics
duration: ~5min
completed: 2026-05-13
---

# Plan 12-08: references/fred-context.md + cross-links — SUMMARY

**Long-form FRED reference doc (~560 lines, 6-section template + Citation Index appendix) shipped at `.claude/skills/mortgage-ops/references/fred-context.md`; cross-linked from SKILL.md references-table (progressive disclosure per Phase 10 D-09), CLAUDE.md External integrations bullet, and `.claude/agents/README.md` Phase 12 section. 2 new supplementary tests pass green. Phase 12 v1 closes here at the documentation layer.**

## Performance

- **Duration:** ~5 min (single executor pass; 2 tasks; 2 atomic commits)
- **Lines added:** 597 net (559 in fred-context.md + 47 in tests + 32 in cross-links − 1 in CLAUDE.md replaced)
- **Files created:** 2 (fred-context.md + this SUMMARY)
- **Files modified:** 4 (SKILL.md, CLAUDE.md, agents/README.md, tests/test_skill_md_fred.py)
- **Tests added:** 2 (`test_skill_md_references_table_includes_fred_context`, `test_fred_context_reference_doc_has_required_sections`)
- **Test status:** test_skill_md_fred.py 8/8 PASS; test_skill.py 37/37 PASS; full suite 639 passed, 5 skipped, 1 xfailed (pre-existing; unrelated)
- **Eval gate:** `evals/runner.py --gate 0.95` exits 0

## Accomplishments

### Task 1 — `references/fred-context.md` long-form reference doc (commit `978bc05`)

Created the 559-line FRED reference document mirroring the 6-section template
from `references/arm-mechanics.md` + the Citation Index appendix from
`references/apr-reg-z.md` (D-28 LOCKED template inheritance from Phase 7).

The 6 numbered sections plus appendix:

| § | Heading | Content |
|---|---|---|
| 1 | HTTP API (canonical path per D-12-LIVE01-01) | Endpoint, allowlist (V5 input validation), auth (FRED_API_KEY env var), rate limits, JSON envelope shape, always-exit-0 contract with failure-mode table |
| 2 | MCP Server (optional secondary path per D-12-LIVE01-01) | .mcp.json registration recipe, Smithery install fallback, what the MCP server exposes (and why SKILL.md doesn't use it), 3-point rationale for HTTP-as-canonical, v2 reconsideration carve-out |
| 3 | Cache Schema | Per-series file layout, schema_version pin, field semantics (8 fields × Decimal/string discipline), strict-< 7d TTL boundary table, lockfile port from orchestration/lockfile.mjs (60s STALE_THRESHOLD, 30s DEFAULT_TIMEOUT, 100ms POLL_INTERVAL, read-back-and-verify CAS) |
| 4 | SKILL.md Routing Rule | Cache-miss recovery contract, plan-test joint-pin invariants table (6 rows), loading-on-demand discipline (Phase 10 D-09) |
| 5 | Eval Harness Integration | Fixture pinning for CI determinism, three-bucket gate math (13/22 anchored, 9 skipped), D-12-SC3-01 STDOUT-only sourcing + static-provenance exemption |
| 6 | Pitfalls (verbatim from 12-RESEARCH.md) | All 6 pitfalls (SKILL.md injection failure, TTL boundary off-by-one, parroted user numbers, replay drift, 95% threshold w/ small N, FRED_API_KEY leak) each paired with the Phase 12 code-level mitigation |
| Appendix | Citation Index | 12 sources (FRED docs ×4, PMMS source ×3, MCP server, Anthropic ×2, Smithery, freezegun, internal Phase 9 lockfile.mjs cross-ref) verified 2026-05-10 |

Supplementary tests appended to `tests/test_skill_md_fred.py`:

- `test_skill_md_references_table_includes_fred_context` — asserts SKILL.md
  contains the `references/fred-context.md` row AND the trigger phrases
  (`FRED`, `MORTGAGE30US`) appear within the references-table region
  (between `Loading Additional Context` and `## Number Formatting`).
- `test_fred_context_reference_doc_has_required_sections` — asserts all 7
  required headings (6 numbered sections + Citation Index appendix) are
  present in the new reference doc.

Both tests ship green — no xfail.

### Task 2 — cross-links from SKILL.md, CLAUDE.md, `.claude/agents/README.md` (commit `bdb1e20`)

**SKILL.md (1 new row in references-table)** — appended after the
`spreadsheet-conventions.md` row:

```markdown
| "what's the current rate", "FRED", "MORTGAGE30US", "how do live rates work" | `references/fred-context.md` |
```

The row lives inside the existing `## Loading Additional Context` section
between `## Bundled Scripts` and `## Number Formatting`. Token + line budget
preserved (SKILL.md grew by 1 row ≈ 150 chars; Phase 10 `test_skill.py`
token/line tests still pass; Phase 12 `test_skill_md_token_budget_after_phase12_insert`
+ `test_skill_md_line_budget_after_phase12_insert` still pass).

**CLAUDE.md (External integrations bullet rewritten)** — before/after:

Before:
```
- FRED MCP (`stefanoamorelli/fred-mcp-server`) — Live `MORTGAGE30US`/`MORTGAGE15US` rate data (mirrors PMMS).
```

After:
```
- FRED API via `scripts/fred_cli.py` HTTP wrapper (canonical path per D-12-LIVE01-01) — Live `MORTGAGE30US`/`MORTGAGE15US` rate data (mirrors Freddie Mac PMMS). The `stefanoamorelli/fred-mcp-server` MCP server is documented as an optional secondary path; see `.claude/skills/mortgage-ops/references/fred-context.md` for HTTP/MCP recipes, cache schema, and routing rules.
```

This rewrite is the canonical project-level surface for the D-12-LIVE01-01
decision — every agent invocation that reads CLAUDE.md now sees the HTTP-
canonical statement and the cross-link to the long-form reference.

**`.claude/agents/README.md` (new "Phase 12: FRED MCP Server (optional)" section)**
— inserted before the existing "No AI attribution" trailer. The section
documents:

- Why HTTP is canonical (CI determinism, SKILL.md cites cache files directly,
  no MCP-runtime coupling)
- How to optionally register the MCP server (`npx -y @smithery/cli install
  @stefanoamorelli/fred-mcp-server --client claude`)
- Pointer to `references/fred-context.md` §2 for the full rationale + the
  manual `.mcp.json` recipe

This README is intentionally NOT loaded into agent context (per the file's
existing "NOT loaded into agent context" disclaimer) — it's a
browser-friendly summary for human repo-browsers (e.g., GitHub).

## Task Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `978bc05` | Ship `references/fred-context.md` long-form reference + 2 supplementary tests |
| 2 | `bdb1e20` | Cross-link `references/fred-context.md` from SKILL.md, CLAUDE.md, `agents/README.md` |

(Final metadata commit follows separately, attaching this SUMMARY.md.)

## Files Created/Modified

### Created

- `.claude/skills/mortgage-ops/references/fred-context.md` (559 lines, 6 numbered sections + Citation Index appendix; PINNED by `test_fred_context_reference_doc_has_required_sections`)
- `.planning/phases/12-fred-eval/12-08-SUMMARY.md` (this file)

### Modified

- `.claude/skills/mortgage-ops/SKILL.md` — 1 row appended to references-table (line 153); token + line budgets preserved
- `CLAUDE.md` — External integrations bullet rewritten (line 27); D-12-LIVE01-01 cite + cross-link to fred-context.md
- `.claude/agents/README.md` — new "Phase 12: FRED MCP Server (optional)" section appended (line 104); cross-link to fred-context.md §2
- `tests/test_skill_md_fred.py` — 2 new supplementary tests appended (8 total, all PASS)

## Decisions Made

### Documentation pattern: 6-section template + Citation Index appendix inherited from Phase 5 + Phase 7

Phase 7's `references/apr-reg-z.md` D-28 LOCKED decision pinned the 6-section
template + Citation Index appendix idiom (originally established by Phase 5's
`references/arm-mechanics.md`). Plan 12-08 inherits this verbatim — no new
documentation patterns introduced. The reference doc skeleton was modeled on
both predecessors:

- Title + cited-from block + on-demand-loading disclaimer (top matter)
- 6 numbered sections (HTTP API / MCP / Cache Schema / Routing / Evals / Pitfalls)
- Appendix: Citation Index with URL verification timestamp + annual re-validation cadence

### Cross-link surface choice: 3 documentation surfaces, not 1

Three cross-link surfaces (SKILL.md / CLAUDE.md / `agents/README.md`) each
serve a different reader:

- **SKILL.md references-table** — Agents at runtime, on-demand (progressive
  disclosure per Phase 10 D-09). The skill loads this only when the
  borrower's prompt matches the trigger phrases.
- **CLAUDE.md External integrations** — Agents at session start (CLAUDE.md
  is eagerly loaded into every agent invocation). This is the canonical
  project-level statement of D-12-LIVE01-01.
- **`.claude/agents/README.md` Phase 12 section** — Human repo-browsers (the
  file is NOT loaded into agent context per its existing disclaimer). This
  is the "stumble across the repo on GitHub" entry point.

Three separate surfaces because the audiences (runtime skill / runtime agents
/ humans browsing the repo) are different.

## Deviations from Plan

None — plan executed exactly as written. The skeleton in Task 1's `<action>`
block was followed and expanded into the full 559-line file; section content
was expanded with citations from `scripts/fred_cli.py`, `lib/fred_cache.py`,
12-RESEARCH.md §Common Pitfalls (verbatim), 12-CONTEXT.md D-12 decisions, and
the 12-RESEARCH.md MCP server registration recipe.

The Task 1 test `test_skill_md_references_table_includes_fred_context` was
intentionally introduced in Task 1 but only passes after Task 2 ships the
SKILL.md row — this is the standard Wave-0 xfail-or-future-pass pattern
inherited from Phase 11. (No xfail decorator needed because Task 2 runs
immediately in the same execution pass.) After both task commits, all 8
tests in `test_skill_md_fred.py` pass green.

## Issues Encountered

None.

## Phase 12 v1 Closure

Plan 12-08 is the FINAL documentation layer for Phase 12. With this plan
committed:

### 8 Functional Requirements — all CLOSED

| Requirement | Closed by | Documented in fred-context.md |
|---|---|---|
| LIVE-01 (FRED HTTP wrapper canonical + MCP optional) | Plan 12-01 (HTTP wrapper) + Plan 12-08 (MCP optional docs) | §1 + §2 |
| LIVE-02 (SKILL.md prose-only injection citing cache files) | Plan 12-03 | §4 |
| LIVE-03 (7-day TTL cache + lockfile) | Plan 12-02 | §3 |
| LIVE-04 (always-exit-0 envelope on stdout) | Plan 12-01 | §1 (envelope shape + failure-mode table) |
| EVAL-01 (evals/runner.py harness) | Plan 12-04 | §5 |
| EVAL-02 (route_match metric) | Plan 12-04 | §5 (D-12-SC3-01 cross-check Pitfall #2b) |
| EVAL-03 (numeric_match three-bucket gate) | Plan 12-04 | §5 (13/22 anchored math) |
| EVAL-04 (Pitfall #2 detector — STDOUT-only sourcing) | Plan 12-04 | §5 + §6 Pitfall 3 |

### 5 Success Criteria — all CLOSED

| SC | Closed by | Notes |
|---|---|---|
| SC-1 (Live rate injection works end-to-end) | Plan 12-05/06 (`evals/prompts/live-rate-injection-01.md` + oracle) | Per D-12-SC1-01 — structural grep stays as complementary check |
| SC-2 (7-day TTL strict-< boundary) | Plan 12-02 (`lib/fred_cache.py is_fresh`) | freezegun boundary tests at 6d23h59m/7d/8d |
| SC-3 (STDOUT-only sourcing hallucination detector) | Plan 12-04 (`evals/metrics.detect_hallucinations`) | Per D-12-SC3-01 + provenance:static exemption |
| SC-4 (95% gate over 22 prompts with skip bucket) | Plan 12-04/05 + Plan 12-07 CI wiring | Per D-12-SC4-01 — 13 anchored / 9 skip; 12/13 = 92.3% < 95% on single failure |
| SC-5 (References doc for FRED context) | Plan 12-08 (this plan) | `references/fred-context.md` shipped at 559 lines |

### 5 D-12 LOCKED Decisions — all RATIFIED in documentation

| Lock | Documented in fred-context.md |
|---|---|
| D-12-LIVE01-01 (HTTP canonical + MCP optional) | §1 + §2 (both paths documented; §2 rationale + v2 carve-out) |
| D-12-LIVE02-01 (Pattern A prose-only injection; no shell-injection) | §4 (SKILL.md grep contract; FORBIDDEN syntax called out) |
| D-12-SC1-01 (live-rate-injection-01 eval added to Wave 5) | §5 (fixture pinning + oracle path documented) |
| D-12-SC3-01 (STDOUT-only sourcing; provenance:static exemption) | §5 + §6 Pitfall 3 |
| D-12-SC4-01 (three-bucket numeric_skip gate) | §5 (13/22 anchored math + 9 skipped) |

Phase 12 v1 is structurally complete: code + tests + documentation all green.

## TDD Gate Compliance

Plan 12-08 is `type: execute` (not `type: tdd`). The new test added in Task 1
(`test_fred_context_reference_doc_has_required_sections`) passes immediately
on commit — no RED gate required because the reference doc was authored in
the same commit. The second new test
(`test_skill_md_references_table_includes_fred_context`) initially fails
after Task 1 commit and passes after Task 2 commit — but this is intentional
plan ordering, NOT a TDD RED-then-GREEN sequence. Both tests are
supplementary structural pins; neither participates in a TDD gate cycle.

## User Setup Required

None. This plan ships pure documentation (reference doc + cross-links + 2
test pins). No code changes; no environment setup; no fixture refresh; no
secrets rotation.

## Next Phase Readiness

Phase 12 v1 PHASE COMPLETE. The orchestrator will perform the final Phase 12
closure step:

- Mark Phase 12 `[x]` complete in `.planning/ROADMAP.md`
- (Optional) Consolidate the 9 plan SUMMARYs into a top-level
  `.planning/phases/12-fred-eval/12-SUMMARY.md`
- Advance STATE.md to the v1.0 milestone gate

Deferred items (Phase 13+, NOT a Phase 12 closure blocker):

- Filling the 9 TBD oracles (refinance/stress/ARM) — discoverable via
  `defer_until_phase: N` pointers in each TBD prompt's frontmatter
- Live-mode eval driver (Phase 12 ships replay-stub only)
- LLM-as-judge eval scoring (v2)
- Multi-model eval comparison (v2)
- MCP-server-as-canonical reconsideration (gated on Anthropic MCP runtime
  ship + upstream `fred-cli` binary)

## Self-Check: PASSED

**1. Created files exist:**
- `.claude/skills/mortgage-ops/references/fred-context.md` — FOUND (559 lines)
- `.planning/phases/12-fred-eval/12-08-SUMMARY.md` — FOUND (this file)

**2. Modified files exist:**
- `.claude/skills/mortgage-ops/SKILL.md` — FOUND (row added at line 153)
- `CLAUDE.md` — FOUND (External integrations rewritten at line 27)
- `.claude/agents/README.md` — FOUND (Phase 12 section appended at line 104)
- `tests/test_skill_md_fred.py` — FOUND (2 new tests appended; 8 total)

**3. Commits exist:**
- `978bc05` (Task 1: fred-context.md + 2 supplementary tests) — FOUND
- `bdb1e20` (Task 2: SKILL.md + CLAUDE.md + agents/README.md cross-links) — FOUND

**4. Verification gates:**
- 7 grep checks for fred-context.md required tokens — ALL PASS
- 7 grep checks for cross-link presence (SKILL.md, CLAUDE.md, agents/README.md) — ALL PASS
- `tests/test_skill_md_fred.py` (8 tests) — 8/8 PASS
- `tests/test_skill.py` (37 tests, Phase 10 token+line budgets) — 37/37 PASS
- `evals/runner.py --gate 0.95` — exits 0
- Full suite (`uv run pytest`) — 639 passed, 5 skipped, 1 xfailed (all pre-existing)

Self-check PASSED on all criteria.
