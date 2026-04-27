---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Phase 2 plan 02 complete (FHA branch wired; cross-plan-stub idiom validated end-to-end)
last_updated: "2026-04-27T03:22:05.000Z"
last_activity: 2026-04-27 -- Phase 2 plan 02 complete (REF-02, REF-03, RUL-04 landed; FHA branch of loan_type.classify now live)
progress:
  total_phases: 12
  completed_phases: 1
  total_plans: 13
  completed_plans: 8
  percent: 62
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-26)

**Core value:** Math correctness first — every dollar figure traces to a tested, deterministic Python function; the LLM is a router and narrator that never owns numbers.
**Current focus:** Phase 2 in progress — Regulatory Reference Data + Rules Predicates

## Current Position

Phase: 2 of 12 in progress (Regulatory Reference Data + Rules Predicates)
Plan: 2 of 7 in Phase 2 complete
Status: Wave 2 in progress — 02-02 FHA branch wired (REF-02 + REF-03 + RUL-04 landed); ready for 02-03 (VA) and 02-04 (USDA + IRS)
Last activity: 2026-04-27 -- Phase 2 plan 02 complete (FHA limits + MIP + loan_type FHA branch; 90/90 tests pass)

Progress: [█░░░░░░░░░] 8% (1/12 phases)

## Performance Metrics

**Velocity:**

- Total plans completed: 8
- Phase 1 wall time: ~1.5 hours (orchestrated, sequential)
- Phase 2 plan 01 wall time: ~35 min (sequential, single executor)
- Phase 2 plan 02 wall time: ~7 min (sequential, single executor — fastest plan to date thanks to 02-01 foundation pattern)

**By Phase:**

| Phase | Plans | Status |
|-------|-------|--------|
| 1     | 6/6   | Complete (PASS-WITH-CAVEATS) |
| 2     | 2/7   | In progress — 02-01 + 02-02 green (FHA branch wired) |

**Plan-level metrics:**

| Plan | Duration | Tasks | Files | Tests added | Result |
|------|----------|-------|-------|-------------|--------|
| 02-01 | 35 min | 2 | 16 created + 3 modified | 17 (5 loader + 9 loan_type + 1 schema + 2 citation-coverage) | green |
| 02-02 | 7 min | 2 | 10 created + 2 modified | +13 net (+6 fha_mip + +4 new FHA loan_type + +2 new schema params + +2 new citation-cov params, -1 stub-presence test removed) | green |

**Recent Trend:**

- Last 8 plans: 01-01..01-06 + 02-01 + 02-02 (all green; 90/90 tests pass)
- Trend: clean — no node repairs, no rework cycles. 02-02 was 5x faster than 02-01 because the foundation pattern (loader, fixture convention, predicate template) was already in place.

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Wrap numpy-financial; do not reimplement amortization math
- Init: One-predicate-per-citation rules pattern (HMDA Platform style)
- Init: Pydantic v2 + condecimal over plain dataclasses for money fields
- Init: DuckDB + lockfile (career-ops pattern) over parquet/YAML for cross-scenario SQL
- Init: Subagents for context isolation on stress sweeps (Anthropic sub-agents pattern)
- Init: APR labeled "estimated" — Newton-Raphson against FFIEC fixtures, not Reg Z compliant
- Init: Fine granularity (12 phases) — each calc family gets dedicated phase + golden-value tests
- Init: Sequential plan execution within phases — natural dependencies (models → calcs → orchestration → skill → evals)
- 02-01: `@lru_cache(maxsize=None)` kept with `# noqa: UP033` — plan acceptance criteria locks the explicit lru_cache idiom; ruff would auto-rewrite to `@cache` and break the grep gate
- 02-01: Mypy overrides for `yaml` + `dateutil.*` (mirrors numpy_financial precedent) instead of types-PyYAML/types-python-dateutil stub packages
- 02-01: Cross-plan stub idiom — `NotImplementedError("... shipped in plan XX-YY")` with positive test asserting the stub fires; the wiring plan rewrites the test
- 02-01: Per-predicate fixture convention — one JSON file per fixture under tests/fixtures/rules/{stem}_*.json with mandatory citation/source_url/comment fields; differs intentionally from Phase 1's single-file array convention
- 02-01: Reference-YAML schema — top-level source: URL + effective: ISO-8601 unquoted date + notes: + body uses regulator-specific keys; ALL numeric scalars QUOTED strings to defend against PyYAML float downconversion (Pitfall 1)
- 02-01: 54 high-cost counties shipped in REF-01 (target was >=50) covering CA Bay Area + LA + NYC metro + DC/NoVA/MD + Boston + NJ commuter belt + Fairfield CT + Miami-Dade/Monroe FL + King/Snohomish WA (Pachulski household state) + all of HI + all of AK
- 02-02: LTV bucket convention encoded in `_lookup_annual_mip` (REF-03 annual_mip_table) — ltv_min EXCLUSIVE for non-zero buckets, INCLUSIVE for the 0.00 bucket; ltv_max always INCLUSIVE. Covers [0,1] without gap or overlap. Reusable for any tiered-rate lookup (PMI rates, VA funding fees, USDA guarantee fees).
- 02-02: MIPResult Pydantic frozen-strict-extra=forbid model with `int | Literal["life_of_loan"]` sentinel union for terminates_at_period — established shape for "predicate returns money + ratio + termination-period" output. RUL-05 (conventional_pmi) will follow same pattern.
- 02-02: Cross-plan stub idiom validated end-to-end — 02-01 stubbed `_classify_fha` → 02-02 REPLACED stub body with REF-02-backed implementation → 02-02 REMOVED `test_fha_program_raises_not_implemented_until_ref_02_lands` and ADDED 4 positive FHA tests. Plans 02-03 (VA) + 02-04 (USDA/IRS) repeat this sequence.
- 02-02: Pre-2023-03-20 FHA endorsement dates raise `NotImplementedError` with regex-matchable substring `pre-2023-03-20` (lowercase, since the fixture uses case-sensitive regex). Pitfall 5 (silent grandfathering) is covered.
- 02-02: REF-03 effective=2023-03-20 is intentionally older than 12mo staleness threshold; `StaleReferenceWarning` fires every load and IS correct (yearly nudge to re-verify HUD hasn't republished). YAML notes block documents this expected loud behavior.

### Pending Todos

- When a GitHub remote is configured, enable branch protection on `main` requiring CI green (FND-06 sub-clause; deferred from Plan 01-06).

### Blockers/Concerns

None active. Phase 1 verified PASS-WITH-CAVEATS — only deferral is the GitHub UI branch-protection step (no remote exists).

**Phases flagged for deeper research at planning time:**

- Phase 5 (ARM): Cap/floor/margin/reset conventions — read Freddie/Fannie Selling Guides before coding
- Phase 7 (APR): Reg Z Appendix J unit-period model + day-count — capture FFIEC fixtures before coding
- Phase 11 (Subagents): Anthropic sub-agent docs evolving — verify current frontmatter fields

## Deferred Items

Items acknowledged and carried forward:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| infra-policy | Enable GitHub branch protection on `main` requiring CI green (FND-06) | deferred — no remote | Phase 1 / Plan 01-06 |

## Session Continuity

Last session: 2026-04-27T03:22:05.000Z
Stopped at: Phase 2 plan 02 complete; ready for 02-03 (VA funding fee + residual income) and 02-04 (USDA + IRS Pub 936)
Resume file: .planning/phases/02-regulatory-reference-data-rules-predicates/02-02-SUMMARY.md
