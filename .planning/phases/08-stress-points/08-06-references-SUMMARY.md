---
phase: 08-stress-points
plan: 06
subsystem: stress-points
tags:
  - phase-08
  - stress-points
  - documentation
  - references
  - phase-6-deferred-coupling
  - phase-11-subagent-contract
  - phase-closure

# Dependency graph
requires:
  - phase: 08-stress-points/08-05
    provides: "Plan 08-05 SC-4 divergence-pin fixture (123 simple / 215 NPV at 7% discount, +92 month gap, decision=buy_points, cum_npv_at_hold=435.46) — Plan 08-06 Divergence Example section reproduces the engine-emitted truth verbatim"
  - phase: 08-stress-points/08-04
    provides: "scripts/stress_test.py + scripts/points_breakeven.py CLIs — Plan 08-06 Task 3 appends doc-path cross-references to both --help epilogs"
  - phase: 08-stress-points/08-03
    provides: "lib.points.evaluate dispatcher with caller-supplied discount_rate_annual contract (D-02 LOCKED) — Plan 08-06 documents the cross-phase coupling AUTHORITATIVELY in references/points-breakeven.md §Discount-Rate Convention"
  - phase: 08-stress-points/08-02
    provides: "lib.stress.evaluate dispatcher (rate-shock | income-shock | arm-reset discriminated union) — Plan 08-06 documents the dispatcher conventions in references/stress-tests.md"
  - phase: 08-stress-points/08-01
    provides: "All 6 LOCKED DECISIONS (D-01 mode discriminator, D-02 SC-5 field order, D-03 schedule_summary scalars only, D-04 caller-supplied dti_threshold, D-05 RatePath closed-set, D-06 stress_invariant_violations list) — references/stress-tests.md surfaces all six in numbered sections"

provides:
  - "references/stress-tests.md (316 lines): six-section reference doc inheriting references/arm-mechanics.md structure (D-06-01 LOCKED): Overview, Sweep Modes (rate-shock/income-shock/arm-reset), Output Schema (SC-5 top-table-summary contract), Subagent Consumption Hint (D-06-04 verbatim-lift target for Phase 11 stress-test-agent), Citations (CFPB §1026.43(c)(5) + March 2021 General QM + CFPB §1951), Glossary, Citation Index appendix"
  - "references/points-breakeven.md (363 lines): six-section reference doc inheriting references/arm-mechanics.md structure (D-06-01 LOCKED): Overview, Simple Breakeven Formula, NPV Breakeven Formula, Discount-Rate Convention (Phase 6 deferred-coupling AUTHORITATIVE per D-06-02 LOCKED), Decision Dispatcher, Divergence Example (SC-4 pin), Citations (IRS Pub 936 + Reg Z §1026.18 + CFPB §136), Glossary, Citation Index appendix"
  - "lib/stress.py module docstring: D-29 cite-from paragraph pointing readers to references/stress-tests.md (mirrors Phase 7 lib.apr → references/apr-reg-z.md idiom)"
  - "lib/points.py module docstring: D-29 cite-from paragraph pointing readers to references/points-breakeven.md (mirrors Phase 7 lib.apr → references/apr-reg-z.md idiom)"
  - "scripts/stress_test.py --help epilog: appended 'See references/stress-tests.md for sweep mechanics, output-schema details, and Phase 11 subagent consumption contract.'"
  - "scripts/points_breakeven.py --help epilog: appended 'See references/points-breakeven.md for formula details, discount-rate guidance, and the SC-4 divergence example.' (in addition to the existing inline reference on the discount_rate_annual line from Plan 08-04)"
  - "Phase 6 cross-phase deferred coupling DOCUMENTED authoritatively in references/points-breakeven.md §Discount-Rate Convention; the Phase 6 planner is authorized per D-06-02 to edit this section when shipping the project-wide convention"
  - "Phase 11 subagent consumption contract DOCUMENTED in references/stress-tests.md §Subagent Consumption Hint as the verbatim-lift target for .claude/agents/stress-test-agent.md per D-06-04"
  - "Phase 8 CLOSED at the documentation layer: 7/7 plans complete; all 3 SC-4-relevant + SC-5-relevant + STRS/PNTS-XX requirements have a documented surface; ROADMAP SC-1..SC-5 closure intact"

affects:
  - 09-duckdb-orchestration
  - 10-claude-skill
  - 11-subagents
  - 12-fred-eval

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Six-section reference-doc template inherited from references/arm-mechanics.md (D-08 LOCKED in Phase 5; D-06-01 inherited verbatim in Plan 08-06): Overview → Sweep/Formula sections → Schema/Dispatcher → Citations → Glossary → Citation Index appendix. Same template used by references/apr-reg-z.md (Phase 7 D-28) and references/refi-npv.md (Phase 6 D-16). Universal across mortgage-ops reference docs."
    - "D-29 cite-from-doc idiom inherited from Phase 7 (lib.apr → references/apr-reg-z.md): module docstring carries a paragraph pointing readers to the reference doc; the reference doc's citation list points back to the module + CLI epilog. Belt-and-suspenders multi-surface anchoring."
    - "Citation Index appendix table (URL / Section / Last verified) inherited from references/refi-npv.md (Phase 6) and references/apr-reg-z.md (Phase 7). Annual re-validation cadence; mirrors data/reference/*.yml staleness convention."
    - "Authoritative deferred-coupling documentation pattern: when a cross-phase contract spans two unfinished phases, the LATER-completing phase ships the authoritative doc that the EARLIER phase will edit on landing. Phase 8 ships references/points-breakeven.md §Discount-Rate Convention; Phase 6 will edit it when its convention lands. D-06-02 LOCKED authorizes the future edit."
    - "Subagent verbatim-lift contract pattern (D-06-04): the doc's hint paragraph is the LITERAL text Phase 11 will copy into .claude/agents/stress-test-agent.md. Cross-phase contract surface; structural lift is mandatory, byte-exact wording is convenience-only (Plan 08-06 deviation Rule 2 explicitly permits trimming for the 1k-token return budget)."

key-files:
  created:
    - references/stress-tests.md
    - references/points-breakeven.md
    - .planning/phases/08-stress-points/08-06-references-SUMMARY.md
  modified:
    - lib/stress.py
    - lib/points.py
    - scripts/stress_test.py
    - scripts/points_breakeven.py

key-decisions:
  - "D-06-01 (LOCKED, honored): Both reference docs follow references/arm-mechanics.md (Phase 5 D-08 [REVISED]) section-structure convention. Markdown headers, citation discipline, length budget targeting Phase 11 subagent context budget. references/stress-tests.md is 316 lines; references/points-breakeven.md is 363 lines; both well within the references/apr-reg-z.md (523 lines) ceiling."
  - "D-06-02 (LOCKED, honored): references/points-breakeven.md §Discount-Rate Convention is the AUTHORITATIVE documentation for the Phase 6 deferred discount-rate coupling. Spells out the contract: caller-supplied today; additive non-breaking default once Phase 6 lands. Phase 6 planner is explicitly authorized to edit this section when shipping its project-wide borrower-perspective convention."
  - "D-06-03 (LOCKED, honored): All citations are real regulatory sources verified 2026-05-03. CFPB ATR/QM 1026.43(c)(5) cites match lib/rules/atr_qm.py. Reg Z 1026.18 cite matches the established Phase 6/7 convention. IRS Pub 936 cite matches data/reference/irs-pub936.yml. NO fabricated citations."
  - "D-06-04 (LOCKED, honored): Subagent consumption hint paragraph in references/stress-tests.md §4 is the LITERAL text Phase 11 will lift into .claude/agents/stress-test-agent.md. Cross-phase contract surface. Phase 11 inherits the structural read-summary-first / drill-into-rows-on-demand discipline; byte-exact wording is convenience-only."
  - "D-06-05 (LOCKED, honored): SC-4 divergence example (123 simple / 215 NPV at 7% discount; +92 month gap) is reproduced verbatim from the Plan 08-05 SC-4 divergence-pin fixture (points_simple_lt_npv_seven_pct_discount.json) with a narrative paragraph documenting the engine truth + Plan 08-03 deviation #1 cross-validation history."

# Metrics
metrics:
  duration_minutes: 25
  completed_date: 2026-05-04
  tasks_total: 3
  tasks_completed: 3
  files_created: 3
  files_modified: 4

---

# Phase 8 Plan 06: References Summary

Two regulatory-cited reference docs shipped at `references/stress-tests.md`
(316 lines) and `references/points-breakeven.md` (363 lines) with full
cross-phase contract anchoring; Phase 8 closes at 7/7 plans, the doc layer is
the load-bearing closure for SC-4 narrative + Phase 11 subagent verbatim-lift
contract + Phase 6 deferred discount-rate coupling.

## What Was Built

### Task 1: references/stress-tests.md (316 lines, commit c5ff926)

Six-section reference doc inheriting `references/arm-mechanics.md` structure
per D-06-01:

- **Overview** — Three sweep modes (rate-shock / income-shock / arm-reset),
  composition-over-reinvention discipline, Pydantic v2 discriminated-union
  dispatcher.
- **Sweep Modes** — One subsection each: rate-shock (STRS-01 + ROADMAP SC-1
  with `--rates 0.06,0.065,...` shortcut), income-shock (STRS-02 + ROADMAP
  SC-2 with `--reductions 0.05,0.10,0.20` shortcut and 0.43 ATR/QM heuristic
  note), arm-reset (STRS-03 + ROADMAP SC-3 with three closed-set RatePath
  names).
- **Output Schema (SC-5 top-table-summary contract)** — `summary` BEFORE
  `rows` field-order discipline, size-budget validation (37,623 bytes for
  50-rate sweep < 100KB), stress invariants table.
- **Subagent Consumption Hint (Phase 11 contract)** — Verbatim-lift target
  paragraph for `.claude/agents/stress-test-agent.md` per D-06-04 LOCKED.
- **Citations** — CFPB §1026.43(c)(5) ATR/QM ARM max-payment stress test,
  March 2021 General QM Final Rule (DTI heuristic context), CFPB §1951 ARM
  rate caps explainer, internal cross-phase refs.
- **Glossary + Citation Index Appendix** — Reset trigger, worst-case label,
  invariant violation, and 4-row URL/section/verification-date table.

`lib/stress.py` module docstring extended with Phase 7 D-29-style cite-from
paragraph pointing readers to the doc.

### Task 2: references/points-breakeven.md (363 lines, commit d6a5023)

Six-section reference doc inheriting `references/arm-mechanics.md` structure:

- **Overview** — Two breakeven framings (simple / NPV), side-by-side
  reporting per ROADMAP SC-4 D-04, two-mode dispatcher (`from_savings` /
  `from_loans`).
- **Simple Breakeven Formula** — `ceil(points_cost / monthly_savings)` with
  Decimal-safe ceil semantics; rate-up scenario returns `None` + warning.
- **NPV Breakeven Formula** — Cumulative-NPV walk with month-by-month walk
  algorithm, zero-discount collapse identity (verified by
  `points_simple_eq_npv_zero_discount.json` fixture), negative-savings +
  high-discount non-crossing edge cases.
- **Discount-Rate Convention (Phase 6 deferred coupling)** —
  AUTHORITATIVE per D-06-02. Spells out caller-supplied-today contract,
  three recommended starting points (zero / loan annual rate / 5% Treasury
  proxy), Phase-6-future-edit authorization, three plausible Phase 6 picks
  (marginal opportunity rate / 5% fixed / loan annual rate).
- **Decision Dispatcher** — `buy_points` iff `cum_npv_at_hold >= 0`,
  `diverge` semantics, side-by-side reporting closure for SC-4.
- **Divergence Example (ROADMAP SC-4 pin)** — Engine-emitted truth from
  Plan 08-05 fixture: 123 simple / 215 NPV at 7% discount; +92 month gap;
  cross-validation history with Plan 08-03 deviation #1 (215 NOT
  planner-claimed 160).
- **Citations** — IRS Pub 936, Reg Z §1026.18 Loan Estimate disclosure,
  CFPB §136 consumer-explainer.
- **Glossary + Citation Index Appendix** — 4-row URL/section/verification
  table.

`lib/points.py` module docstring extended with Phase 7 D-29-style cite-from
paragraph pointing readers to the doc.

### Task 3: CLI --help epilog cross-references (commit 4dbb18e)

- `scripts/stress_test.py` epilog: appended "See references/stress-tests.md
  for sweep mechanics, output-schema details, and Phase 11 subagent
  consumption contract."
- `scripts/points_breakeven.py` epilog: appended "See
  references/points-breakeven.md for formula details, discount-rate
  guidance, and the SC-4 divergence example." (in addition to the existing
  inline reference on the `discount_rate_annual` line from Plan 08-04).

## Test Baseline

**Preserved at 521 passed / 4 skipped / 1 xfailed** (zero regression to Plan
08-05 closing baseline). The 1 xfail is the inherited Phase 5 ARM oracle
Bankrate/Vertex42 deferral, outside Phase 8 scope.

`mypy --strict` + `ruff check` + `ruff format --check` all clean across both
modified `lib/*.py` modules and both modified `scripts/*.py` CLIs (verified
via pre-commit hooks on each task commit).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Acceptance criterion forecast] Task 3 `points_breakeven.py
--help | grep -c references/points-breakeven.md` returns 2, not 1**

- **Found during:** Task 3 verification
- **Issue:** Plan acceptance criterion stated `returns 1`, but the existing
  `discount_rate_annual` line in the JSON-shape example already contained an
  inline reference to `references/points-breakeven.md` (added in Plan 08-04
  Task 2). Appending the new closing line per the Task 3 action body
  produces 2 occurrences in `--help` output, not 1.
- **Fix:** No code change. The ESSENCE of the criterion ("CLI --help epilog
  cross-references the doc paths") is met; the second occurrence is benign
  belt-and-suspenders cross-referencing. Documented here for traceability.
  The `<success_criteria>` block ("CLI --help epilogs cross-reference the
  docs") is fully satisfied.
- **Files modified:** none (forecast issue, not a code defect)
- **Commit:** N/A (no fix commit needed)

No other deviations. Plan executed exactly as written.

## Phase 8 Closure Summary

This plan completes Phase 8 at 7/7 plans:

| Plan | Title | Closes |
|---|---|---|
| 08-00 | test-infrastructure | Wave 0 xfail scaffolds |
| 08-01 | models | Type contracts + 6 LOCKED DECISIONS |
| 08-02 | stress-engine | rate_shock / income_shock / arm_path bodies |
| 08-03 | points-engine | simple_breakeven / npv_breakeven bodies |
| 08-04 | clis | scripts/stress_test.py + scripts/points_breakeven.py |
| 08-05 | fixtures-and-tests | 14 fixtures + meta-test + final 2 xfails flipped |
| 08-06 | references | references/stress-tests.md + references/points-breakeven.md (this plan) |

**Requirement closure:** STRS-01 (rate-shock), STRS-02 (income-shock),
STRS-03 (arm-reset), STRS-04 (CLI), PNTS-01 (simple breakeven), PNTS-02 (NPV
breakeven), PNTS-03 (CLI) — all 7 closed at the test, CLI, and documentation
layers.

**ROADMAP SC closure:** SC-1 (rate-shock --rates verbatim), SC-2
(income-shock --reductions verbatim), SC-3 (arm-reset three named paths),
SC-4 (simple-vs-NPV side-by-side with SC-4 divergence pin), SC-5
(top-table-summary < 100KB) — all 5 closed at the test layer (Plan 08-05) +
documented at the reference-doc layer (this plan).

**Cross-phase contracts shipped:**
- Phase 11 subagent verbatim-lift target paragraph (D-06-04) ready in
  `references/stress-tests.md §Subagent Consumption Hint`.
- Phase 6 deferred discount-rate coupling AUTHORITATIVELY documented
  (D-06-02) in `references/points-breakeven.md §Discount-Rate Convention`;
  Phase 6 planner authorized to edit on landing.

## Self-Check: PASSED

- [x] `references/stress-tests.md` exists (316 lines, 6 required sections,
  CFPB §1026.43(c)(5) cited 2x)
- [x] `references/points-breakeven.md` exists (363 lines, 6 required
  sections, IRS Pub 936 + Reg Z §1026.18 + CFPB §136 cited; Phase 6
  mentioned 17x)
- [x] `lib/stress.py` cites `references/stress-tests.md` (2x: docstring +
  per-decision context)
- [x] `lib/points.py` cites `references/points-breakeven.md` (3x: docstring
  + D-02 deferred-coupling note + Wave 6 commit)
- [x] `scripts/stress_test.py --help` epilog cites the doc (1x)
- [x] `scripts/points_breakeven.py --help` epilog cites the doc (2x — see
  deviation #1)
- [x] Three commits on `main` (c5ff926, d6a5023, 4dbb18e), each
  pre-commit-hook-clean (ruff + mypy + format)
- [x] Test baseline preserved at 521 passed / 4 skipped / 1 xfailed
