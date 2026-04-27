---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Phase 2 plan 04 complete (Wave 2 closed — USDA + IRS Pub 936 landed; locked decisions D-PHASE2-Q5 + RUL-11 two-boolean grace period preserved end-to-end)
last_updated: "2026-04-27T03:50:00.000Z"
last_activity: 2026-04-27 -- Phase 2 plan 04 complete (REF-06, REF-07, RUL-08, RUL-11 landed; cross-predicate-asymmetry pattern + two-boolean grace-period idiom established; 18/22 phase-2 requirements done)
progress:
  total_phases: 12
  completed_phases: 1
  total_plans: 14
  completed_plans: 10
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-26)

**Core value:** Math correctness first — every dollar figure traces to a tested, deterministic Python function; the LLM is a router and narrator that never owns numbers.
**Current focus:** Phase 2 in progress — Regulatory Reference Data + Rules Predicates

## Current Position

Phase: 2 of 12 in progress (Regulatory Reference Data + Rules Predicates)
Plan: 4 of 7 in Phase 2 complete
Status: Wave 2 closed — 02-04 USDA + IRS Pub 936 wired (REF-06 + REF-07 + RUL-08 + RUL-11 landed); ready for Wave 3 (02-05 PMI + Fannie + Freddie, sequential)
Last activity: 2026-04-27 -- Phase 2 plan 04 complete (USDA SFH GLP eligibility + IRS Pub 936 deduction caps; 139/139 tests pass)

Progress: [█░░░░░░░░░] 8% (1/12 phases)

## Performance Metrics

**Velocity:**

- Total plans completed: 10
- Phase 1 wall time: ~1.5 hours (orchestrated, sequential)
- Phase 2 plan 01 wall time: ~35 min (sequential, single executor)
- Phase 2 plan 02 wall time: ~7 min (sequential, single executor — fastest plan to date thanks to 02-01 foundation pattern)
- Phase 2 plan 03 wall time: ~12 min (sequential, single executor — VA scope had two predicates + cross-plan stub resolution + AFFD-07 contract; still well under 02-01)
- Phase 2 plan 04 wall time: ~5 min (sequential, single executor — new fastest plan to date; pattern fully internalized; no stub resolution this plan; both new predicates were pure new artifacts)

**By Phase:**

| Phase | Plans | Status |
|-------|-------|--------|
| 1     | 6/6   | Complete (PASS-WITH-CAVEATS) |
| 2     | 4/7   | In progress — 02-01..02-04 green (FHA + VA + USDA + IRS Pub 936 wired); Wave 2 closed |

**Plan-level metrics:**

| Plan | Duration | Tasks | Files | Tests added | Result |
|------|----------|-------|-------|-------------|--------|
| 02-01 | 35 min | 2 | 16 created + 3 modified | 17 (5 loader + 9 loan_type + 1 schema + 2 citation-coverage) | green |
| 02-02 | 7 min | 2 | 10 created + 2 modified | +13 net (+6 fha_mip + +4 new FHA loan_type + +2 new schema params + +2 new citation-cov params, -1 stub-presence test removed) | green |
| 02-03 | 12 min | 2 | 19 created + 2 modified | +25 net (+9 va_funding_fee + +7 va_residual_income + +4 new VA loan_type + +2 new schema params + +4 new citation-cov params, -1 stub-presence test removed) | green |
| 02-04 | 5 min | 2 | 14 created + 0 modified | +24 net (+8 USDA + +10 IRS Pub 936 + +2 new schema params + +4 new citation-cov params; no test removal since no cross-plan stub resolution this plan) | green |

**Recent Trend:**

- Last 10 plans: 01-01..01-06 + 02-01..02-04 (all green; 139/139 tests pass)
- Trend: clean — no node repairs, no rework cycles. 02-04 is the new speed record (5 min) thanks to (a) two regulators bundled but each with smaller surface area than VA/FHA, (b) no cross-plan stub to resolve, (c) plan-author wrote tightly-scoped behavior specs that all passed on first run after auto-formatter applied. The Wave-2 internal pattern is fully locked.

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
- 02-03: VA full-entitlement loans REUSE REF-01 (conforming-limits-2026.yml) — NO separate va-limits YAML — per Blue Water Navy Vietnam Veterans Act of 2019 (effective 2020). Saves a YAML file + a loader call + an annual-refresh burden. Above-county-ceiling (partial-entitlement) raises NotImplementedError (out of v1).
- 02-03: ResidualIncomeResult Pydantic shape mirrors MIPResult (frozen + strict + extra='forbid' + sentinel-union/Literal-union fields). New convention: any predicate returning structured pass/fail evaluations follows this shape. RUL-09 (atr_qm) and RUL-10 (reg_z) will follow.
- 02-03: STABLE f-string citation contract for AFFD-07 sentinel: `binding_rule_citation = f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"`. TRIPLE-locked (module docstring + every test asserts literal equality + grep gate in plan acceptance criteria). Format drift would break Phase 4. Pattern reusable for any predicate output consumed as downstream sentinel.
- 02-03: Public-helper-alongside-main-function pattern: `evaluate(...)` is high-level pass/fail; `minimum_required(...)` is the threshold lookup helper. Allows callers to fetch threshold without running full evaluation. Phase 4 affordability scoring will reuse for credit-score / DTI tiers.
- 02-03: Down-payment band convention in REF-04 purchase_and_cash_out: down_payment_min INCLUSIVE, down_payment_max EXCLUSIVE EXCEPT for the top band where 1.00 is INCLUSIVE. Boundary test pins 0.10 → >=10 band (not 5..<10). Reusable for any tiered-rate lookup with similar interval semantics.
- 02-03: ruff RUF003 enforces ASCII multiplication in code comments — replace `×` with `*` (matches existing test_fha_mip.py convention). The `→` arrow character is not flagged by RUF003 and is preserved.
- 02-04: Cross-predicate-asymmetry pattern — when one predicate raises on missing data (RUL-01 MissingCountyDataError) and another silently falls back (RUL-08 silent default per D-PHASE2-Q5), BOTH behaviors can be correct given different regulatory lookup directions. Document the asymmetry inline in BOTH predicate docstrings. Pinned by `test_unlisted_county_silently_uses_default_per_locked_decision` to defend against future "fix" attempts.
- 02-04: Two-boolean encoding for date-range regulatory tests — when a regulatory rule requires AND-semantics on multiple date conditions (TCJA binding-contract grace = signed-before AND closed-before), encode as separate boolean parameters in the predicate signature rather than synthesizing a single date input. Caller takes calendar-arithmetic responsibility; predicate body uses simple AND. Reusable for any future date-range grace period.
- 02-04: Plain-Decimal-return for stateless table-lookup predicates (RUL-11 qualified_loan_limit returns plain Decimal). Structured Pydantic results are reserved for predicates that bundle multiple conceptually-independent values (USDAEligibilityResult bundles eligibility + applied limit + 2 fees; MIPResult; ResidualIncomeResult). Choice criterion: 'does the predicate return >1 conceptually independent value?'
- 02-04: MFS-as-half-of-X encoded in YAML, not derived in code. Future tax-law changes that break the half-cap symmetry can be expressed in YAML alone with no code change. Reusable for any 'X for status A, X/2 for status B' regulatory rule.
- 02-04: REF-07 effective: 2025-01-01 fires StaleReferenceWarning at execution time (today=2026-04-26 makes it 481 days old > 365 day threshold). NOT a bug — same correct loud-warning pattern as REF-03 / REF-04 / REF-05. Calendar drift between plan-write time and execution time naturally surfaces stale data; documented in REF-07 notes block.
- 02-04: USDA county override list ships with one entry (San Francisco only). Per RESEARCH.md Pitfall 10 + D-PHASE2-Q5: canonical high-cost USDA-eligible county override; future YAML edits add more counties without code changes.
- 02-04: FilingStatus Literal scoped to lib/rules/irs_pub936.py (not promoted to lib/rules/types.py). Mirrors VAFundingFeePurpose scoping in 02-03. Promotion deferred until a second consumer appears (Phase 7 APR after-tax cost may need it).

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

Last session: 2026-04-27T03:50:00.000Z
Stopped at: Phase 2 plan 04 complete; Wave 2 closed; ready for Wave 3 (02-05 PMI + Fannie LLPA + Freddie eligibility, sequential)
Resume file: .planning/phases/02-regulatory-reference-data-rules-predicates/02-04-SUMMARY.md
