---
phase: 11
plan: 06
subsystem: subagents
tags:
  - phase-11
  - subagents
  - references
  - documentation
  - phase-closeout
dependency_graph:
  requires:
    - "11-01: amortization-agent"
    - "11-02: refi-npv-agent"
    - "11-03: stress-test-agent"
    - "11-04: SUBA-05 routing seam (skill-routing-update or TODO marker)"
    - "11-05: synthetic transcripts + fixture README live-capture recipe"
  provides:
    - "Phase 10-progressive-disclosure-loaded routing-decision reference (subagent-routing.md)"
    - "Browser-friendly per-agent summary README (.claude/agents/README.md)"
    - "CLAUDE.md GSD:subagents cross-link block"
    - "Phase 11 documentation surface complete; ready for closeout SUMMARY consolidation"
  affects:
    - "Phase 12 (FRED MCP + Eval Harness): EVAL-03 / EVAL-04 reference the routing-decision detail; live-capture recipe feeds nightly eval regeneration."
    - "Future planners landing in the project: read CLAUDE.md → see GSD:subagents block → follow cross-link to .claude/agents/README.md → drill into agent files OR routing-decision reference."
tech_stack:
  added: []
  patterns:
    - "references/*.md sibling-doctrine (one MD file per domain concern, on-demand-loaded by Phase 10 progressive disclosure) — mirrors Phase 5 references/arm-mechanics.md, Phase 6 references/refi-npv.md, Phase 8 references/stress-tests.md"
    - "GSD:* CLAUDE.md managed-block convention (mirrors GSD:project, GSD:stack, GSD:conventions, GSD:architecture, GSD:skills, GSD:workflow, GSD:profile)"
    - "Three-tier discoverability: CLAUDE.md (top-level) → .claude/agents/README.md (browser-friendly) → .claude/skills/mortgage-ops/references/subagent-routing.md (deep-detail, on-demand)"
key_files:
  created:
    - ".claude/skills/mortgage-ops/references/subagent-routing.md (175 lines)"
    - ".claude/agents/README.md (104 lines)"
    - ".planning/phases/11-subagents/11-06-references-SUMMARY.md (this file)"
  modified:
    - "CLAUDE.md (added GSD:subagents block, +22 lines)"
decisions:
  - "D-01 honored: subagent-routing.md placed in .claude/skills/mortgage-ops/references/ where Phase 10 SKLL-09 enforces on-demand load. The doc itself documents the loading semantics in its 'Loading semantics' section."
  - "D-02 honored: .claude/agents/README.md disclaimer (second heading) explicitly notes it is NOT loaded into agent context — Anthropic agents directory loader scans for *-agent.md only."
  - "D-03 honored: CLAUDE.md cross-link is a new GSD:subagents block as a sibling AFTER GSD:skills-end and BEFORE GSD:workflow-start. Pre-existing GSD blocks are unmodified."
metrics:
  duration: "3m 45s"
  completed: "2026-05-10"
  tasks_completed: 3
  files_created: 3
  files_modified: 1
  commits: 3
---

# Phase 11 Plan 06: References — Final Wave Summary

Closed the Phase 11 documentation surface: shipped the on-demand-loaded routing-decision
reference (`subagent-routing.md`), the browser-friendly per-agent README, and the
CLAUDE.md cross-link block. Pure docs additions — no code change, no new tests, no
regression risk.

## What was shipped

### 1. `.claude/skills/mortgage-ops/references/subagent-routing.md` (175 lines)

The Phase 10-progressive-disclosure-loaded routing-decision reference. Sections shipped:

1. **Header + Purpose** — declares on-demand loading; names the audience (main thread,
   user, future planners/debuggers).
2. **The three agents — at a glance** — single table with name | model | trigger | output
   shape | source plan.
3. **When each agent fires (in detail)** — per-agent decision tree:
   - amortization-agent (Haiku, single-loan) — trigger keywords + does-NOT-fire-for list
   - refi-npv-agent (Sonnet, 2-5 offers) — 2-5 range rationale + trigger keywords + tool
     whitelist note
   - stress-test-agent (Haiku, >5 scenarios) — strictly-more-than-5 threshold per literal
     SC-2 wording + tool whitelist (Read/Bash/Write for CSV escape hatch)
4. **The 1,000-token budget for stress-test-agent (SC-3 rationale)** — why 1,000
   specifically; how it's enforced (anthropic.count_tokens against synthetic transcript per
   Plan 11-05 D-01 + D-03); how to diagnose a budget breach.
5. **Capturing replacement transcripts via claude -p** — pointer to
   `tests/fixtures/subagent_transcripts/README.md` for the recipe; quarterly cadence;
   warning that live capture is non-deterministic + paid-tier and DOES NOT belong in CI.
6. **Loading semantics (Phase 10 progressive disclosure)** — explicit doctrine reminder
   that this file does NOT auto-load with SKILL.md (D-01).
7. **Cross-references** — links to all three agent files, modes/stress.md (SUBA-05),
   references/stress-tests.md (Phase 8 input contract), references/refi-npv.md (Phase 6
   sign convention), .claude/agents/README.md.

Cross-references verified:
- `tests/fixtures/subagent_transcripts/README.md` → 1 cross-link (live-capture recipe)
- `modes/stress.md` → 2 cross-links (SUBA-05 routing seam)
- `references/stress-tests.md` → 2 cross-links (Phase 8 input contract)
- `references/refi-npv.md` → 2 cross-links (Phase 6 sign convention)
- `.claude/agents/{amortization,refi-npv,stress-test}-agent.md` → all three referenced

Commit: `55ae4ac` — `docs(11-06): add subagent-routing.md reference doc`

### 2. `.claude/agents/README.md` (104 lines)

The browser-friendly per-agent summary file. NOT loaded into agent context per D-02
(Anthropic agents directory loader scans for `*-agent.md` only — see Plan 11-RESEARCH.md
spec citation). Sections shipped:

1. **Header** — directory purpose + frontmatter convention summary.
2. **NOT loaded into agent context** — D-02 disclaimer as the second heading so casual
   repo-browsers see it BEFORE the per-agent summaries.
3. **The three agents** — one paragraph per agent (name + model tier + rationale + trigger
   summary + output format + tools whitelist + script path + closes-which-requirement).
4. **Frontmatter summary** — shared fields across all three agents (name, description,
   model, skills, tools).
5. **When NOT to dispatch a subagent** — three explicit anti-patterns + the Cost
   Discipline self-correction note.
6. **Where to learn more** — cross-links to subagent-routing.md, modes/stress.md,
   ROADMAP.md Phase 11, REQUIREMENTS.md SUBA-01..06, tests/test_subagents.py + fixtures.
7. **No AI attribution reminder** — global CLAUDE.md rule.

Commit: `c8b11b2` — `docs(11-06): add .claude/agents/README.md browser-friendly summary`

### 3. CLAUDE.md GSD:subagents block (+22 lines)

Inserted as a sibling block AFTER `GSD:skills-end` and BEFORE `GSD:workflow-start` per
D-03. Block structure:

```
<!-- GSD:subagents-start source:agents/ -->
## Project Subagents

Three context-isolated Claude Code subagents under .claude/agents/:
- amortization-agent (Haiku) — closes SUBA-01
- refi-npv-agent (Sonnet) — closes SUBA-02
- stress-test-agent (Haiku) — closes SUBA-03

Browser-friendly: .claude/agents/README.md (NOT loaded into agent context).
Routing detail: .claude/skills/mortgage-ops/references/subagent-routing.md (on-demand).

See .planning/phases/11-subagents/ for source plans.
<!-- GSD:subagents-end -->
```

Pre-existing GSD blocks untouched; verified by:
`grep -cE '<!-- GSD:(project|stack|conventions|architecture|skills|workflow|profile)-(start|end)' CLAUDE.md`
returns **14** (7 sections × 2 markers each — unchanged from before Plan 11-06).

Commit: `bc6a112` — `docs(11-06): cross-link CLAUDE.md to .claude/agents/`

## Locked decisions honored

| ID | Decision | Honored | Evidence |
|----|----------|---------|----------|
| D-01 | references/subagent-routing.md is on-demand-loaded (NOT auto-included in SKILL.md) | YES | File lives in `.claude/skills/mortgage-ops/references/` where Phase 10 SKLL-09 enforces progressive disclosure. The doc's "Loading semantics" section explicitly documents this contract. |
| D-02 | .claude/agents/README.md is NOT loaded into agent context | YES | README's second heading is "NOT loaded into agent context"; cites Anthropic sub-agents spec URL (https://code.claude.com/docs/en/sub-agents) and explains the loader pattern (`*-agent.md` only). |
| D-03 | CLAUDE.md cross-link via new GSD:subagents sibling block | YES | New `<!-- GSD:subagents-start ... GSD:subagents-end -->` block placed between GSD:skills and GSD:workflow; no other GSD block modified. |

## Verification

| Gate | Result | Evidence |
|------|--------|----------|
| references/subagent-routing.md exists, ≥100 lines | PASS | 175 lines |
| All required keywords present in subagent-routing.md | PASS | All 3 agent names, >5 threshold, 1000-token budget, on-demand/progressive-disclosure, claude -p, fixture-README cross-link, modes/stress.md cross-link, sibling references cross-links |
| .claude/agents/README.md exists, ≥50 lines | PASS | 104 lines |
| All required keywords present in README | PASS | 3 agent names, NOT loaded disclaimer, Haiku ×3, Sonnet ×2, subagent-routing.md cross-link, CLAUDE.md mention |
| CLAUDE.md GSD:subagents block added | PASS | grep -c `<!-- GSD:subagents-start` returns 1; ditto end marker |
| Pre-existing GSD blocks unmodified | PASS | grep -cE on 7 standard blocks × 2 markers returns 14 |
| pytest collection still works (no regression) | PASS | 606 tests collected (including SUBA-04, SUBA-05, SUBA-06 from Plan 11-05) |
| ruff clean | PASS | "All checks passed!" |
| No AI attribution in any file or commit | PASS | All three commits use only the global "no Co-Authored-By" rule; the only `co-authored-by` reference in CLAUDE.md (line 77) is pre-existing in the conventions block ("**Commits:** No Co-Authored-By or AI attribution (per global rule)") and is NOT introduced by Plan 11-06 |

## Deviations from Plan

None — plan executed exactly as written. Documentation-only plan with three discrete file
operations; no Rules 1-4 deviations triggered.

## Self-Check

- `test -f .claude/skills/mortgage-ops/references/subagent-routing.md` → FOUND (175 lines)
- `test -f .claude/agents/README.md` → FOUND (104 lines)
- `git log` contains commit `55ae4ac` → FOUND
- `git log` contains commit `c8b11b2` → FOUND
- `git log` contains commit `bc6a112` → FOUND
- CLAUDE.md contains `GSD:subagents-start` block → FOUND
- CLAUDE.md retains all 14 pre-existing GSD markers → CONFIRMED

## Phase 11 closeout candidate status

After this plan ships:
- Plans 11-00 through 11-06 all delivered and committed.
- SC-1..SC-5 all have measurable test gates (SUBA-04 / SUBA-05 / SUBA-06 in
  `tests/test_subagents.py`, plus SUBA-01..03 frontmatter/content gates from earlier waves).
- SUBA-01, SUBA-02, SUBA-03, SUBA-04, SUBA-06 are CLOSED.
- SUBA-05 status is determined by Plan 11-04 branch:
  - Branch (a) — Phase 10 had shipped at Plan 11-04 time → SUBA-05 CLOSED.
  - Branch (b) — Phase 10 had not yet shipped → SUBA-05 DEFERRED-WITH-CONTRACT
    (cross-phase TODO marker at `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md`
    persists for Phase 10 closeout to consume).
- Documentation surface complete: routing detail (subagent-routing.md), browser-friendly
  summaries (.claude/agents/README.md), top-level cross-link (CLAUDE.md GSD:subagents).

**Recommendation:** Phase 11 is ready for `/gsd-verify-work` audit pass and a Phase 11
closeout SUMMARY consolidation.

## Commits

| Hash | Message |
|------|---------|
| `55ae4ac` | `docs(11-06): add subagent-routing.md reference doc` |
| `c8b11b2` | `docs(11-06): add .claude/agents/README.md browser-friendly summary` |
| `bc6a112` | `docs(11-06): cross-link CLAUDE.md to .claude/agents/` |

## Self-Check: PASSED
