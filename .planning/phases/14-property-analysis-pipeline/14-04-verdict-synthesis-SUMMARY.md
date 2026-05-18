---
phase: 14-property-analysis-pipeline
plan: 04-verdict-synthesis
subsystem: property-analysis
tags: [verdict, blocker-cascade, citation-coverage, falsifiable-reasons]

# Dependency graph
requires:
  - phase: 14-property-analysis-pipeline (plan 01-foundation-models)
    provides: "lib/household.py (Household.preferred_down_payment_pct) + lib/profile.py (Profile signature placeholder)"
  - phase: 14-property-analysis-pipeline (plan 02-matrix-models)
    provides: "lib/property_analysis.py (DownPaymentMatrix, ProgramResult, StressBlock, StressRow, Verdict, VerdictReason)"
  - phase: 14-property-analysis-pipeline (plan 03-auxiliary-blocks)
    provides: "StressBlock rows with stress_kind + breaches_dti_ceiling populated"
  - phase: 04-affordability
    provides: "_evaluate_blockers first-match-wins cascade pattern + BLOCKED_BY_* Final[str] prefix-discipline idiom"
provides:
  - "lib/property_verdict.py — 5 VERDICT_* Final[str] constants + _MIP_BURDEN_THRESHOLD + synthesize() pure function implementing D-14-VERDICT-01..04 cascade"
  - "tests/test_property_verdict.py — 12 named tests covering 5 cascade levels + 2 precedence scenarios + format compliance + edge case + 2 meta-tests"
  - "Frozen interface for Plan 14-05: synthesize(matrix, stress, household, profile) -> Verdict signature pinned"
affects:
  - 14-05-analyze-composition (top-level analyze() body calls synthesize() after _build_tax_block)
  - 14-06-golden-fixtures (golden Verdict.reasons[] pin the 5 VERDICT_* citation strings)
  - 15-property-skill-mode (report formatter consumes Verdict.headline_reason + reasons[].predicate_code)

# Tech tracking
tech-stack:
  added: []  # No new libraries; pure Decimal + Pydantic over Plan 14-02 output models
  patterns:
    - "Verdict cascade with first-match-wins early-return idiom mirrors lib/affordability.py:_evaluate_blockers L1207-1380. Each cascade level is `if <condition>: return Verdict(...)` so precedence is encoded in source-order."
    - "Falsifiable-reason discipline (D-14-VERDICT-04): every VerdictReason carries predicate_code (one of 5 VERDICT_* Final[str] constants) AND computed_value (string of the number that triggered it). Mirrors Phase 4's BLOCKED_BY_* + (loan_type, computed_value) shape."
    - "Citation-coverage meta-test pattern: tests/test_property_verdict.py:test_verdict_code_citation_coverage introspects lib.property_verdict via vars() for VERDICT_* prefixed strings and asserts each is emitted by at least one cascade-level scenario. Mirrors tests/test_affordability.py:test_blocked_by_citation_coverage."
    - "Unused-parameter-suppression-with-rationale: synthesize(...) takes profile in its signature for forward-compat with Plan 14-05's analyze() callsite but never reads it; `del profile` after entry documents the intentional non-use without an `_ = profile` style warning. Future-proof: VERD-01 may grow to read filing_status/marginal_tax_rate without changing the callsite."

key-files:
  created:
    - lib/property_verdict.py
    - tests/test_property_verdict.py
    - .planning/phases/14-property-analysis-pipeline/14-04-verdict-synthesis-SUMMARY.md
  modified: []

key-decisions:
  - "D-14-VERDICT-01 (locked by plan): WATCH when ONLY FHA eligible at preferred DP AND FHA monthly_mi > Decimal('300.00'). _MIP_BURDEN_THRESHOLD constant pins the policy choice; CONTEXT 'Claude's Discretion' permits planner-driven swap with citation."
  - "D-14-VERDICT-02 (locked by plan): WATCH when ANY eligible-at-preferred-DP program's income-shock stress row has breaches_dti_ceiling=True. Most-protective stance; income-shock fail on any eligible path downgrades the verdict."
  - "D-14-VERDICT-03 (locked by plan): GO wins over MIP-burden WATCH when any non-FHA program is eligible at preferred DP. Stress-fail WATCH still downgrades GO. Encoded as cascade ordering — income-shock check at Level 3 (before MIP-burden Level 4), and MIP-burden branch guarded by `if not non_fha_eligible:`."
  - "D-14-VERDICT-04 (locked by plan): every VerdictReason carries predicate_code AND computed_value. Verified by test_reason_format_compliance + test_verdict_code_citation_coverage."
  - "synthesize() signature pinned: (matrix, stress, household, profile) -> Verdict. Profile retained for Plan 14-05 callsite compatibility + future filing_status/marginal_tax_rate reads."
  - "5 VERDICT_* constants only — no VERDICT_WATCH_STRESS_RATE_FAIL or VERDICT_WATCH_STRESS_ARM_RESET declared. D-14-VERDICT-02 locks income-shock as the only WATCH stress trigger; declaring unused codes would fail the citation-coverage meta-test."
  - "TDD-RED gate consolidation (inherited from Plan 14-01..14-03): mypy --strict pre-commit hook blocks test files that import not-yet-existing modules. Task 1 (lib) and Task 2 (tests) each land as a single per-task commit. RED phase preserved as runtime evidence: tests/test_property_verdict.py imports collected and failed before lib/property_verdict.py committed in `ed01b1d`."

patterns-established:
  - "Phase-14 verdict-cascade idiom: declare VERDICT_* Final[str] constants at module-top in cascade-order, then implement synthesize() as N consecutive `if <condition>: return Verdict(...)` blocks in that same order. Source-order = precedence. Future verdict modules in other phases (e.g., refi verdict, points verdict) adopt the same pattern."
  - "Synthesize-time citation-coverage gate: every cascade level's emitted reason must reference a constant declared at module-top; the citation-coverage meta-test grep-discovers the constants and asserts each is reached. Drift between declaration and emission breaks the gate."

requirements-completed:
  - VERD-01

# Metrics
duration: 7 min
completed: 2026-05-18
---

# Phase 14 Plan 04: Verdict Synthesis Summary

**Pure-function `synthesize(matrix, stress, household, profile) -> Verdict` ships the D-14-VERDICT-01..04 first-match-wins cascade with 5 VERDICT_* Final[str] constants, $300/mo FHA MIP-burden threshold, and 12 unit tests including a citation-coverage meta-test that pins every constant to at least one cascade scenario — VERD-01 closes at the unit-test level.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-18T17:49:41Z
- **Completed:** 2026-05-18T17:56:42Z
- **Tasks:** 2 (lib + tests, each as a per-task commit per the established Plan 14-01..14-03 RED+GREEN consolidation pattern)
- **Files created:** 2 (lib/property_verdict.py + tests/test_property_verdict.py)
- **Tests added:** 12 (all passing; 0 stubs)
- **Full-suite regression:** 812 passed, 10 skipped, 2 deselected (pre-existing fha_mip dirty-file failures per Plan 14-02 work-in-progress carve-out), 1 xfailed

## Accomplishments

- **`lib/property_verdict.py` (258 lines)** ships the verdict synthesis surface:
  - **5 VERDICT_* Final[str] constants** with exact string values per RESEARCH §"Pattern 5: Verdict synthesis":
    - `VERDICT_NO_GO_DTI_ALL_PROGRAMS == "DTI-CEILING-ALL-PROGRAMS"`
    - `VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP == "NO-ELIGIBLE-AT-PREFERRED-DP"`
    - `VERDICT_WATCH_FHA_MIP_BURDEN == "MIP-BURDEN-FHA"`
    - `VERDICT_WATCH_STRESS_INCOME_FAIL == "STRESS-INCOME-SHOCK"`
    - `VERDICT_GO == "GO-ALL-GREEN"`
  - **`_MIP_BURDEN_THRESHOLD = Decimal("300.00")`** — D-14-VERDICT-01 policy choice (Assumption A1).
  - **`synthesize(matrix, stress, household, profile) -> Verdict`** — pure function (no I/O, no global state reads, inputs never mutated) implementing the 5-level cascade with first-match-wins early-return idiom mirroring `lib/affordability.py:_evaluate_blockers` L1207-1380.

- **`tests/test_property_verdict.py` (535 lines)** ships 12 named tests:
  - **5 cascade-level tests** — one per VERDICT_* constant. Each asserts level + predicate_code + computed_value + (where applicable) program / dp_pct.
  - **2 cascade-precedence tests** (D-14-VERDICT-03) — `test_go_wins_over_mip_burden_when_non_fha_eligible` proves GO wins over WATCH-MIP-burden when ANY non-FHA cell eligible at preferred DP; `test_watch_income_shock_overrides_go` proves income-shock WATCH still downgrades a GO when stress fails.
  - **1 format-compliance test** (D-14-VERDICT-04) — every VerdictReason emitted across all cascade scenarios has non-empty predicate_code + computed_value.
  - **1 edge-case test** — empty matrix returns NO_GO via `min(..., default=Decimal("0"))`.
  - **1 citation-coverage meta-test** (Pitfall 7 + 12) — introspects `lib.property_verdict` via `vars()` for VERDICT_* prefixed strings and asserts every constant is emitted by at least one cascade scenario. Mirrors `tests/test_affordability.py:test_blocked_by_citation_coverage`.
  - **1 phase-level requirement-coverage meta-test** — source-grep asserts D-14-VERDICT-01..04 + VERD-01 all referenced.
  - **1 policy-threshold anchor test** — `_MIP_BURDEN_THRESHOLD == Decimal("300.00")` pinned.

- **Cascade ordering** encoded as source-order:
  1. `if not any(c.eligible for c in matrix.cells):` -> NO_GO (Level 1)
  2. `if not eligible_at_preferred:` -> NO_GO (Level 2)
  3. `if income_stress_fails:` -> WATCH (Level 3 / D-14-VERDICT-02)
  4. `if not non_fha_eligible and fha_cells[0].monthly_mi > _MIP_BURDEN_THRESHOLD:` -> WATCH (Level 4 / D-14-VERDICT-01 + GO-wins precedence guard)
  5. fall-through -> GO (Level 5 / D-14-VERDICT-03 default)

## Task Commits

Per the Plan 14-01/14-02/14-03 RED+GREEN consolidation pattern: mypy --strict + ruff pre-commit hooks block separate test-first commits when test files import not-yet-existing impl, so per-task tests + impl land in the same commit. For Plan 14-04 the file-natural split lets us keep the two commits as a clean "feat (lib) -> test (tests)" pair:

1. **Task 1 (lib/property_verdict.py):** `ed01b1d` — feat
2. **Task 2 (tests/test_property_verdict.py):** `90d1b58` — test

_TDD-RED proof: tests/test_property_verdict.py imports collected and failed (ModuleNotFoundError: No module named 'lib.property_verdict') before commit `ed01b1d` landed; commit `90d1b58` could only land after the lib was committed and importable. The RED-then-GREEN ritual is preserved across the two task commits._

## Field Set Shipped

### lib/property_verdict.py module surface

| Symbol | Type | Value |
|--------|------|-------|
| `VERDICT_NO_GO_DTI_ALL_PROGRAMS` | `Final[str]` | `"DTI-CEILING-ALL-PROGRAMS"` |
| `VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP` | `Final[str]` | `"NO-ELIGIBLE-AT-PREFERRED-DP"` |
| `VERDICT_WATCH_STRESS_INCOME_FAIL` | `Final[str]` | `"STRESS-INCOME-SHOCK"` |
| `VERDICT_WATCH_FHA_MIP_BURDEN` | `Final[str]` | `"MIP-BURDEN-FHA"` |
| `VERDICT_GO` | `Final[str]` | `"GO-ALL-GREEN"` |
| `_MIP_BURDEN_THRESHOLD` | `Final[Decimal]` | `Decimal("300.00")` |
| `synthesize(matrix, stress, household, profile)` | function | `-> Verdict` |

### 12 named tests + D-14-VERDICT-XX coverage

| Test | Closes | Level |
|------|--------|-------|
| `test_no_go_no_eligible` | VERD-01 cascade entry | Level 1 |
| `test_no_go_at_preferred_dp` | D-14-VERDICT cascade Level 2 | Level 2 |
| `test_watch_income_shock` | D-14-VERDICT-02 | Level 3 |
| `test_watch_fha_mip_burden` | D-14-VERDICT-01 | Level 4 |
| `test_go_non_fha_eligible` | D-14-VERDICT-03 default | Level 5 |
| `test_go_wins_over_mip_burden_when_non_fha_eligible` | D-14-VERDICT-03 precedence | Levels 4 vs 5 |
| `test_watch_income_shock_overrides_go` | D-14-VERDICT-02 vs D-14-VERDICT-03 | Levels 3 vs 5 |
| `test_reason_format_compliance` | D-14-VERDICT-04 | All levels |
| `test_empty_matrix_returns_no_go` | Behavior 9 edge case | Level 1 (degenerate) |
| `test_verdict_code_citation_coverage` | Pitfall 7 + 12 (VERD-01) | All levels |
| `test_phase_14_verdict_requirement_coverage` | Phase-14 source-grep gate | n/a (meta) |
| `test_mip_burden_threshold_pinned_at_300` | Assumption A1 anchor | n/a (constant) |

## Citation-Coverage Meta-Test Behavior

`test_verdict_code_citation_coverage` is the Pitfall 12 gate:

1. Imports `lib.property_verdict`.
2. Inspects module globals via `vars()` for symbols matching `name.startswith("VERDICT_") and isinstance(val, str)`.
3. Runs 5 cascade scenarios in-test (one per level) and collects every `reason.predicate_code` emitted.
4. Asserts every discovered `VERDICT_*` constant value appears in the collected emission set.

In-test coverage gate (current Plan 14-04 scope). **Plan 14-06 tightens this to fixture-based coverage** — once `tests/fixtures/property_analysis/*.json` ships the 3 golden fixtures (SFH conforming, condo with HOA, SFH jumbo), the meta-test will introspect every fixture's `verdict.reasons[].predicate_code` and assert the full constant set is exercised at the fixture level. Until then, in-test scenarios serve as the gate.

## Pitfalls Mitigated

| Pitfall | Mitigation | Verification |
|---------|-----------|---------------|
| 7 (VERDICT_* prefix discipline) | All 5 verdict citation constants share the `VERDICT_` prefix; introspection via `name.startswith("VERDICT_")` discovers them deterministically | test_verdict_code_citation_coverage |
| 12 (citation-coverage meta-test missing) | tests/test_property_verdict.py:test_verdict_code_citation_coverage mirrors tests/test_affordability.py:test_blocked_by_citation_coverage; every VERDICT_* constant must be emitted by at least one cascade scenario | test_verdict_code_citation_coverage + test_phase_14_verdict_requirement_coverage |
| 2 (Decimal from strings) | _MIP_BURDEN_THRESHOLD = Decimal("300.00") string-constructed; every Decimal in tests/test_property_verdict.py constructed from a string literal | test_mip_burden_threshold_pinned_at_300 |
| 7 (no unused VERDICT_* constants) | Plan explicitly forbade declaring VERDICT_WATCH_STRESS_RATE_FAIL / VERDICT_WATCH_STRESS_ARM_RESET because D-14-VERDICT-02 locks income-shock as the only WATCH stress trigger; grep -c returns 0 for unused names | acceptance criterion #8 |

## Decisions Made

- **D-14-VERDICT-01..04 are LOCKED by CONTEXT.md.** Plan 14-04 implements verbatim; no Claude's-Discretion swap was needed (the $300/mo MIP threshold stands; no published HUD/MBA citation surfaced).
- **`profile` parameter retained in synthesize() signature despite non-use.** Plan 14-05's analyze() callsite passes profile uniformly to each block builder + verdict synthesizer. Removing profile from synthesize() would break that uniformity. Future verdict logic may grow to read filing_status / marginal_tax_rate (e.g., tax-aware verdict downgrades when high marginal_tax_rate amplifies mortgage-interest-deduction value) — keeping the parameter avoids a follow-on signature change. Documented in synthesize() docstring + `del profile` at function entry.
- **5 VERDICT_* constants only, NOT 7.** The plan explicitly forbade declaring VERDICT_WATCH_STRESS_RATE_FAIL or VERDICT_WATCH_STRESS_ARM_RESET — D-14-VERDICT-02 locks income-shock as the only WATCH stress trigger, and the citation-coverage meta-test would fail if unused constants were declared. Rate-shock + ARM-reset stress rows are still computed by Plan 14-03's _build_stress_block; the verdict cascade simply does not act on them as WATCH triggers.
- **Cascade-precedence ordering encoded as source-order.** Level 3 (income-shock) appears BEFORE Level 4 (MIP-burden) so that an FHA-MIP-burden scenario combined with an income-shock failure produces WATCH-income-shock (not WATCH-MIP-burden). The source-order = precedence convention mirrors lib/affordability.py:_evaluate_blockers L1207-1380.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Ruff TC001 import-classification on lib/property_verdict.py + tests/test_property_verdict.py**
- **Found during:** Task 2 verification (running `uv run ruff check`).
- **Issue:** Ruff initially flagged the `from lib.household import Household` and `from lib.profile import Profile` imports as TC001 (move-to-type-checking-block) because synthesize() only uses Household/Profile as parameter annotations under `from __future__ import annotations`. Then after adding the `# noqa: TC001` directive, ruff complained that `DownPaymentMatrix` + `StressBlock` did NOT need the noqa (because they are referenced by helper builders in tests, but the lib doesn't use them at runtime).
- **Fix:** Applied `# noqa: TC001` to Household + Profile imports (mirroring the established pattern in `lib/property_analysis.py` L96, L101 — Pydantic resolves field annotations at runtime so the imports stay top-level even when ruff's static-analysis sees them as type-only). Removed unused `noqa` from DownPaymentMatrix + StressBlock since they were not flagged. Also removed the unused `VerdictReason` re-export in tests (`F401`) and rewrote one `_MIP_BURDEN_THRESHOLD == Decimal("300.00")` assertion as `Decimal("300.00") == _MIP_BURDEN_THRESHOLD` (`SIM300` Yoda-condition preference).
- **Files modified:** lib/property_verdict.py (lines 39-40); tests/test_property_verdict.py (import block + final assertion).
- **Verification:** `uv run ruff check` + `uv run ruff format --check` + `uv run mypy --strict` all clean on both files.
- **Committed in:** ed01b1d (Task 1 lib) + 90d1b58 (Task 2 tests).

### Plan-text grep inaccuracy noted (not a deviation)

The plan's acceptance criterion `grep -E 'assertAlmostEqual|pytest\.approx' tests/test_property_verdict.py | grep -v '^#' | wc -l` returns 1 because the module docstring contains the literal prohibition phrase `"never \`\`pytest.approx\`\` / \`\`assertAlmostEqual\`\`"`. This is a docstring annotation, not an actual usage. The intent (no fuzzy comparators in test bodies) is satisfied — every numeric assertion in the test file uses exact Decimal equality. Same false-positive pattern documented in Plan 14-02's SUMMARY.md.

---

**Total deviations:** 1 auto-fixed (Rule 3 — ruff TC001/F401/SIM300 lint findings on imports + Yoda-condition style). No Rule 1 / Rule 2 / Rule 4 deviations.
**Impact on plan:** None — the fixes are pure linter-driven import-classification + style adjustments. Cascade behavior, constant values, and test assertions are unchanged.

## Issues Encountered

- **mypy --strict + pre-commit blocks the canonical TDD RED commit** (test files importing not-yet-existing modules) — same inherited issue as Plans 14-01/14-02/14-03. The natural lib-then-tests split for Plan 14-04 makes this less painful: Task 1 lands lib first; Task 2 lands tests once the import resolves. RED phase preserved as runtime evidence (tests collected and failed before Task 1 commit landed).
- **Pre-existing fha_mip dirty-file failures** (2 tests deselected: `test_predicate_has_citation_in_docstring[fha_mip]` + `test_meta_tests_pass_unmutated_baseline`) — unchanged from Plan 14-02/14-03. The work_in_progress_note explicitly forbids touching lib/rules/fha_mip.py; verified via `git stash` that both tests pass without the dirty file.

## Threat Flags

None — Plan 14-04's changes match the threat surface declared in the PLAN.md `<threat_model>` register:
- T-14-FLOAT mitigation preserved: VerdictReason.computed_value is intentionally a string (polymorphic numeric serialization per PATTERNS.md L455); tests assert exact string equality (`computed_value == "325.00"`, `computed_value == str(Decimal("0.610000"))`).
- T-14-FRED-RACE accepted (synthesize() does NOT call FRED).
- T-14-STALE-REF accepted (synthesize() does NOT read reference YAMLs).
- T-14-REASON mitigated: D-14-VERDICT-04 + Pitfall 7 — VerdictReason Pydantic model REQUIRES predicate_code + computed_value (strict mode rejects empty/None for required str fields); test_reason_format_compliance verifies both fields are non-empty on every emitted reason; test_verdict_code_citation_coverage verifies every VERDICT_* constant is exercised.
- T-14-PII mitigated: tests use synthetic Household / Profile / ProgramResult instances; no real data.

## Interfaces Frozen for Downstream Plans

- **`synthesize(matrix: DownPaymentMatrix, stress: StressBlock, household: Household, profile: Profile) -> Verdict`** — Plan 14-05's analyze() body calls this last (after _build_tax_block). Signature pinned by `test_verdict_code_citation_coverage` and `inspect.signature(...).parameters` invariant.
- **`VERDICT_NO_GO_DTI_ALL_PROGRAMS` / `VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP` / `VERDICT_WATCH_STRESS_INCOME_FAIL` / `VERDICT_WATCH_FHA_MIP_BURDEN` / `VERDICT_GO`** — Plan 14-06 golden fixtures pin these in `verdict.reasons[].predicate_code` for fixture-based citation-coverage tightening.
- **`_MIP_BURDEN_THRESHOLD = Decimal("300.00")`** — Plan 14-06 fixtures hand-anchor the threshold for the WATCH-MIP-burden cascade-level fixture (`sfh_conforming_king_county.json` with FHA-only-eligible variant).

## Pitfalls Mitigated (full list)

| Pitfall | Mitigation | Verification |
|---------|-----------|---------------|
| 2 (Decimal from strings) | _MIP_BURDEN_THRESHOLD declared as `Decimal("300.00")` string-constructed; every test Decimal constructed from string literal | test_mip_burden_threshold_pinned_at_300 |
| 7 (VERDICT_* prefix discipline) | All 5 verdict citation constants share the `VERDICT_` prefix; introspection via `name.startswith("VERDICT_")` is deterministic | test_verdict_code_citation_coverage |
| 12 (citation-coverage meta-test) | tests/test_property_verdict.py:test_verdict_code_citation_coverage introspects lib.property_verdict and asserts every VERDICT_* constant is emitted by at least one cascade scenario | test_verdict_code_citation_coverage + test_phase_14_verdict_requirement_coverage |

## Next Plan Readiness

- **Plan 14-05 (analyze-composition)** unblocked: `synthesize(matrix, stress, household, profile) -> Verdict` ready for the analyze() body. Plan 14-05 will compose `_build_matrix` -> `_build_stress_block` -> `_build_refi_block` -> `_build_points_block` -> `_build_tax_block` -> `synthesize` into the AnalysisReport.
- **Plan 14-06 (golden-fixtures)** unblocked: the 5 VERDICT_* citation strings + _MIP_BURDEN_THRESHOLD scalar pinned. Hand-calculated fixtures can anchor `verdict.reasons[].predicate_code` against the same constants; the citation-coverage meta-test will tighten to fixture-introspection mode once the JSONs exist.

## Self-Check: PASSED

- [x] lib/property_verdict.py exists — verified via `ls`
- [x] tests/test_property_verdict.py exists — verified via `ls`
- [x] Both task commits present in `git log --oneline -4`:
  - `ed01b1d` feat(14-04): add lib/property_verdict.py with synthesize() cascade
  - `90d1b58` test(14-04): add tests/test_property_verdict.py with cascade + meta coverage
- [x] All 12 tests pass: `uv run pytest tests/test_property_verdict.py -x` -> 12 passed
- [x] Full-suite regression: 812 passed, 10 skipped, 2 deselected (pre-existing fha_mip), 1 xfailed — net +12 from Plan 14-03's 800.
- [x] Acceptance criteria from PLAN.md Task 1 + Task 2 all green (12 grep checks + import + signature round-trip).
- [x] mypy --strict clean on both new files.
- [x] ruff check + ruff format --check clean on both new files.
- [x] VERD-01 unit-level requirement closed.

---

*Phase: 14-property-analysis-pipeline*
*Plan: 04-verdict-synthesis*
*Completed: 2026-05-18*
