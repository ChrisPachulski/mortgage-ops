---
phase: 03-core-amortization
plan: 05
subsystem: amortization-validator
gap_closure: true
tags: [amortization, validator, d-05, cr-01, gap-closure]
requirements: [AMRT-04]
requires:
  - lib/amortize.py::AmortizeRequest (existing model + _biweekly_mode_consistency validator)
  - lib/amortize.py::ExtraPrincipalEntry (D-05 model)
  - tests/test_amortize.py (existing 35-case Phase 3 test surface)
provides:
  - lib/amortize.py::AmortizeRequest._no_duplicate_recurring_periods (new @model_validator)
  - D-05 docstring "Uniqueness rider (CR-01 closure)" paragraph
  - 6 new tests pinning the determinism contract (3 negative + 3 positive)
affects:
  - scripts/amortize.py D-19 error-envelope path (now surfaces a structured Pydantic envelope on stderr for the duplicate-recurring input class; behavior verified end-to-end)
decisions:
  - validator runs AFTER _biweekly_mode_consistency so a request that violates BOTH (D-02 and D-05) gets the D-02 error first, keeping existing D-02 tests stable
  - validator raises ValueError (NOT pydantic.ValidationError directly) per Pydantic v2 idiom — Pydantic wraps ValueError into ValidationError automatically inside @model_validator(mode="after"); matches the canonical _biweekly_mode_consistency pattern
  - rider scoped to recurring=True ONLY — duplicate one-shots remain legal (additive stacking is order-independent), as do recurring + one-shot pairs at the same period
key-files:
  modified:
    - lib/amortize.py
    - tests/test_amortize.py
metrics:
  duration: ~3 min
  tasks: 2
  commits: 2
  tests_added: 6
  files_modified: 2
  files_created: 0
  full_suite: 300 passed (was 294)
  completed: 2026-04-30
---

# Phase 3 Plan 5: AmortizeRequest Duplicate-Recurring Rejection (CR-01 Closure) Summary

**One-liner:** Closes gap CR-01 (D-05 order-of-list ambiguity) by adding `AmortizeRequest._no_duplicate_recurring_periods` model_validator that rejects duplicate `(period, recurring=True)` entries via pydantic.ValidationError, restoring AMRT-04's determinism contract at the request boundary.

## Objective

Phase requirement closed: **AMRT-04** ("semantic-equivalent extra-principal lists must produce semantic-equivalent results — order-independence at boundary").

Verification gap closed: **CR-01** — duplicate `(period, recurring=True)` ExtraPrincipalEntry rows previously produced non-deterministic schedules depending on caller-supplied list order, because D-05 (`the LATEST entry with entry.period <= p AND entry.recurring=True`) was order-of-list-ambiguous when two entries tied on period. Per UAT decision option (a), the input class is now rejected at the AmortizeRequest boundary instead of silently picking a tiebreaker — preserving CLAUDE.md's "Math correctness first ... deterministic Python function" rule.

## What Shipped

### lib/amortize.py

1. **New `@model_validator(mode="after")` on `AmortizeRequest`:** `_no_duplicate_recurring_periods` (37 lines including docstring). Iterates `self.extra_principal`, tracks `seen_recurring_periods: set[int]`, raises `ValueError` (Pydantic-wrapped to `ValidationError`) when a duplicate `(period, recurring=True)` is encountered. Validator is scoped to `recurring=True` ONLY — duplicate one-shots and recurring+one-shot pairs at the same period remain legal.

2. **Error message pinned by acceptance criteria:** `f"duplicate recurring extra_principal at period {entry.period}; two recurring entries at the same period are order-of-list-ambiguous (D-05); use one recurring entry per period or set recurring=False on duplicates to opt into additive stacking"`. Substring-pin contract on `"duplicate"`, `"period"`, `"recurring"` in 3 negative test assertions.

3. **D-05 LOCKED DECISION docstring extended:** New "Uniqueness rider (CR-01 closure)" paragraph after the existing D-05 paragraph, citing the new validator and confirming legal sibling cases (duplicate one-shots, recurring + one-shot at same period). Anchored by `grep -c "Uniqueness rider"` and `grep -c "CR-01 closure"` acceptance gates.

### tests/test_amortize.py

6 new tests added in a contiguous block AFTER `test_amortize_request_rejects_biweekly_mode_when_monthly` and BEFORE the `# AMRT-04: extra principal entries` section header (~184 lines):

| Test | Purpose | Result |
| --- | --- | --- |
| `test_amortize_request_rejects_duplicate_recurring_periods` | Negative: CR-01 reproducer in original `[100, 200]` order rejects with substring assertions on `duplicate`/`period`/`recurring` | PASS |
| `test_amortize_request_rejects_duplicate_recurring_periods_reversed` | Negative: CR-01 symmetric `[200, 100]` order rejects identically (no order-dependence) | PASS |
| `test_amortize_request_rejects_three_way_duplicate_recurring` | Negative: 3-way duplicate at period=5 rejects (validator iterates all entries, not adjacent pairs) | PASS |
| `test_amortize_request_accepts_d05_step_up_with_distinct_periods` | Positive: legitimate D-05 step-up (period=1 then period=13) still validates | PASS |
| `test_amortize_request_accepts_duplicate_one_shots_at_same_period` | Positive: duplicate one-shots at period=60 still validate (additive stacking is commutative) | PASS |
| `test_amortize_request_accepts_recurring_plus_oneshot_at_same_period` | Positive: recurring + one-shot at period=60 still validate (D-05 explicit composition) | PASS |

## Decision Implementation Map

| Gap / Decision | Cited In | Code Anchor | Evidence |
| --- | --- | --- | --- |
| CR-01 closure (UAT option a) | `03-VERIFICATION.md` `human_verification[0]`; `03-UAT.md` (decision recorded) | `lib/amortize.py::AmortizeRequest._no_duplicate_recurring_periods` | 3 negative + 3 positive tests; CLI end-to-end verified |
| D-05 uniqueness rider | `lib/amortize.py:50-62` D-05 LOCKED DECISION block (extended) | `Uniqueness rider (CR-01 closure):` paragraph | `grep -c "Uniqueness rider" lib/amortize.py` returns 1 |
| D-19 boundary preservation | `scripts/amortize.py:172-174` (`e.json()` pass-through) | Validator raises `ValueError` (not `ValidationError` directly); Pydantic wraps automatically | CLI run on CR-01 reproducer JSON exits 2 with parseable JSON list whose first error contains `duplicate recurring` |
| Validator ordering (D-02 first, D-05 rider second) | Pydantic v2 `@model_validator(mode="after")` runs in declaration order | New validator placed AFTER `_biweekly_mode_consistency` | `grep -c '@model_validator(mode="after")' lib/amortize.py` returns 2; existing D-02 tests still PASS |
| Scope: rider fires ONLY for `recurring=True` | Validator body: `if not entry.recurring: continue` | 3 positive sibling tests pin the legal cases | All 3 positive tests PASS |
| Determinism contract (CLAUDE.md "Math correctness first") | Validator docstring cites the rule explicitly | Validator + 6 tests | Symmetric reject in `[100,200]` and `[200,100]` orderings |

## Verification Results

### Grep Gates (acceptance criteria)

| Gate | Expected | Actual | Status |
| --- | --- | --- | --- |
| `grep -c "_no_duplicate_recurring_periods" lib/amortize.py` | >=2 | 2 | PASS |
| `grep -c '@model_validator(mode="after")' lib/amortize.py` | 2 | 2 | PASS |
| `grep -c "Uniqueness rider" lib/amortize.py` | >=1 | 1 | PASS |
| `grep -c "CR-01 closure" lib/amortize.py` | >=1 | 2 | PASS |
| `grep -E 'duplicate recurring extra_principal at period' lib/amortize.py | wc -l` | 1 | 1 | PASS |
| 6 new test definitions exist by exact name | 6 | 6 | PASS |

### Test + Tooling Gates

| Gate | Command | Result | Status |
| --- | --- | --- | --- |
| Targeted 6-test query (GREEN) | `uv run pytest tests/test_amortize.py -k "rejects_duplicate or accepts_d05_step_up or accepts_duplicate_one_shots or accepts_recurring_plus_oneshot or rejects_three_way" -v` | 6 passed | PASS |
| Phase 3 test file | `uv run pytest tests/test_amortize.py` | 41 passed (was 35) | PASS |
| Full project suite | `uv run pytest` | 300 passed (was 294) + 4 pre-existing StaleReferenceWarning warnings unchanged | PASS |
| mypy --strict | `uv run mypy --strict .` | Success: no issues found in 50 source files | PASS |
| ruff check | `uv run ruff check .` | All checks passed! | PASS |
| ruff format --check | `uv run ruff format --check .` | 50 files already formatted | PASS |

### CR-01 End-to-End Verification

**Direct AmortizeRequest construction** (`uv run python -c "..."`):
- Original `[100, 200]` ordering → `pydantic_core._pydantic_core.ValidationError` with message `duplicate recurring extra_principal at period 1; two recurring entries at the same period are order-of-list-ambiguous (D-05); ...` — exit 1
- Same input class is now rejected before reaching `_resolve_extra` (engine never sees the ambiguous input)

**CLI D-19 boundary** (`uv run python scripts/amortize.py --input <CR-01 reproducer JSON>`):
- Exit code: 2
- stderr: parseable JSON list `[{"type":"value_error","loc":[],"msg":"...","input":{...},"ctx":{"error":"..."},"url":"..."}]`
- Flattened JSON contains `duplicate recurring` substring
- Surfaced via `e.json()` pass-through; D-19 contract preserved (Phase 9/10 consumers see the same envelope shape they already handle for D-02)

### Zero Engine Regressions

`_resolve_extra` is unchanged in this plan. The validator catches the ambiguous input class BEFORE `build_schedule` is ever invoked, so the 35-case existing Phase 3 test surface — including all AMRT-04 fixtures (one-shot, recurring, step-up, cap-at-balance) — passes byte-identically.

## Commits

| Task | Commit | Subject |
| --- | --- | --- |
| 1 (RED) | `973456c` | `test(03-05): add CR-01 regression tests for duplicate recurring periods (RED)` |
| 2 (GREEN) | `f8c1ddb` | `fix(03-05): reject duplicate (period, recurring=True) extra_principal entries (CR-01)` |

Both commits contain zero AI attribution per CLAUDE.md global rule (`git log -1 --format=%B | grep -iE 'claude|anthropic|co-authored' | wc -l` returns 0 for both).

## Deviations from Plan

None - plan executed exactly as written. All grep gates, test pin counts, ruff/mypy hygiene gates, and the CLI end-to-end verification passed on first run after each task. RED state had the precise expected shape (3 `DID NOT RAISE ValidationError` failures, 3 sibling positives passing); GREEN state turned all 3 negatives into PASS without breaking any prior tests.

The plan's predicted positive sibling test outcomes (3 already-passing under current behavior) and negative test outcomes (3 fail with `DID NOT RAISE ValidationError` shape) materialized precisely as written. No Rule-1/Rule-2/Rule-3 deviations triggered.

## Threat Flags

No new STRIDE-relevant surface introduced beyond what the plan's `<threat_model>` already documents. The new validator:

- Adds no new network endpoints, file access, schema-at-trust-boundary surfaces
- Introduces no new error message PII (the message reveals only the offending period number, which the user submitted)
- Validator runtime is O(n) over `extra_principal` entries; n bounded by realistic ~720 biweekly periods; microseconds — no DoS concern under personal-use scope
- Determinism contract is now pinned by 3 negative regression tests + grep-anchored docstring; future drift detected immediately

T-03-05-01..T-03-05-08 dispositions remain as documented in `03-05-PLAN.md::<threat_model>`. No new threats discovered during execution.

## TDD Gate Compliance

Plan-level TDD discipline followed:

1. **RED gate (`test(...)` commit):** `973456c` `test(03-05): add CR-01 regression tests for duplicate recurring periods (RED)` — 3 failing tests + 3 passing siblings; failures of the precise expected shape (`DID NOT RAISE ValidationError`)
2. **GREEN gate (`feat(...)` / `fix(...)` commit):** `f8c1ddb` `fix(03-05): reject duplicate (period, recurring=True) extra_principal entries (CR-01)` — `fix(...)` is the appropriate type per the project's commit-type table since the plan closes a verification gap (CR-01) on existing functionality, not introduces a brand-new feature
3. **REFACTOR gate:** Not needed — implementation was minimal and clean on first write; no cleanup commit required

The full RED→GREEN cycle is observable in `git log --oneline -3`:
```
f8c1ddb fix(03-05): reject duplicate (period, recurring=True) extra_principal entries (CR-01)
973456c test(03-05): add CR-01 regression tests for duplicate recurring periods (RED)
599fb0f plan(03): add gap-closure plans 03-05 (CR-01) and 03-06 (WR-02)
```

## Self-Check: PASSED

- [x] New validator `AmortizeRequest._no_duplicate_recurring_periods` rejects duplicate `(period, recurring=True)` via `pydantic.ValidationError` (not `ValueError` at the surface — Pydantic wraps; verified empirically with both direct construction and CLI subprocess)
- [x] D-05 LOCKED DECISION docstring extended in place with `Uniqueness rider (CR-01 closure)` paragraph (one block per locked decision, mirrors atr_qm.py idiom)
- [x] Pinned CR-01 regression tests added: both `[100, 200]` and `[200, 100]` orderings rejected; plus 3-way duplicate; plus 3 positive sibling tests pinning legal cases
- [x] Full pytest suite green: 300/300 (was 294 + 6 new from this plan)
- [x] `tests/test_amortize.py` 41/41 (was 35 + 6 new)
- [x] mypy --strict clean (50 source files)
- [x] ruff check clean
- [x] ruff format --check clean
- [x] `lib/amortize.py` exists with `_no_duplicate_recurring_periods` def at expected location (after `_biweekly_mode_consistency`)
- [x] `tests/test_amortize.py` exists with all 6 new test functions defined exactly once each
- [x] Both commits exist in git log with exact required subjects
- [x] Both commits contain zero `Co-Authored-By` / Claude / Anthropic attribution
- [x] Both commits made WITH pre-commit hooks enabled (ruff/format/mypy/yaml/user-layer all passed)
- [x] No unintended file deletions in either commit (`git diff --diff-filter=D --name-only HEAD~2 HEAD` empty)
- [x] CR-01 reproducer end-to-end: direct construction raises ValidationError; CLI exits 2 with structured JSON envelope on stderr containing `duplicate recurring`
- [x] AMRT-04 determinism contract restored: semantically equivalent inputs (`[100, 200]` and `[200, 100]`) now produce semantically equivalent outputs (both reject identically)
