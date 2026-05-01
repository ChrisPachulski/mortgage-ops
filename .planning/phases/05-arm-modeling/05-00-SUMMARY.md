---
phase: 05
plan: 00
subsystem: test-infrastructure
tags:
  - phase-05
  - arm-modeling
  - test-infrastructure
  - nyquist
  - xfail-stubs
requires: []
provides:
  - "tests.conftest.arm_fixture (parametric loader for tests/fixtures/arm/)"
  - "tests/test_arm.py (32 xfail-decorated stubs covering ARM-01..09 + cross-cutting)"
  - "tests/fixtures/arm/ directory (committed via .gitkeep)"
  - "tests/fixtures/arm/oracle/ directory (committed via .gitkeep)"
affects:
  - "Wave 2 (Plan 05-02): flips ARM-01 (3 stubs)"
  - "Wave 3 (Plan 05-03): flips ARM-02..05 (13 stubs) — cumulative-totals stitch + reset formula + re-amortization"
  - "Wave 4 (Plan 05-04): flips ARM-08 (8 stubs) — CLI smoke + float-gate + envelope uniformity + lazy-import"
  - "Wave 5 (Plan 05-05): flips ARM-09 (3 stubs) — references/arm-mechanics.md doc + citations"
  - "Wave 6 (Plan 05-06): flips ARM-06 + ARM-07 + cross-cutting (8 stubs) — fixtures + oracle captures"
tech_stack_added:
  - "pytest xfail with strict=True (gate against accidental XPASS)"
patterns_used:
  - "FIXTURE_DIR / <subsystem> / <stem>.json — mirror of amortize_fixture + affordability_fixture"
  - "subprocess-only CLI invocation (D-17) — never `import scripts.arm_simulate`"
  - "SCRIPT_PATH + ARM_MODULE_PATH module constants for Phase 10 relocation"
key_files_created:
  - tests/test_arm.py
  - tests/fixtures/arm/.gitkeep
  - tests/fixtures/arm/oracle/.gitkeep
key_files_modified:
  - tests/conftest.py
key_decisions:
  - "All 32 stubs use @pytest.mark.xfail(strict=True): an accidental pass triggers XPASS so the wave that flips a test must also remove the decorator (T-05-10 mitigation)."
  - "Imports in test_arm.py trimmed to Wave 0 actual usage (Path, pytest, Callable, Any). Waves 4/5/6 re-add json/subprocess/Decimal/re/sys when they flip stubs (Rule 3: ruff F401 hook wins over plan-text 'pre-import everything')."
  - "ruff format multi-lined long-reason xfail decorators; the plan's `grep -c '@pytest.mark.xfail(strict=True'` literal-substring gate is satisfied semantically (32/32 stubs strict=True per AST) but the substring grep returns 15 (Rule 3: formatter wins)."
metrics:
  duration_seconds: 209
  duration_human: "3m 29s"
  tasks_completed: 4
  tasks_total: 4
  files_created: 3
  files_modified: 1
  tests_added: 32
  xfail_outcomes: 32
  full_suite_passed: 379
  full_suite_skipped: 4
  full_suite_xfailed: 32
  full_suite_failed: 0
  full_suite_errored: 0
  completed_date: 2026-04-30
---

# Phase 5 Plan 00: Test Infrastructure Summary

Wave 0 of Phase 5 (ARM Modeling) lands the Nyquist validation scaffold: 32 xfail-decorated test stubs, the `arm_fixture` parametric loader, and two empty fixture directories — every requirement-closing wave (Plans 02..06) now has a known landing pad to flip xfail → pass against, with `strict=True` guaranteeing a stub that accidentally passes raises XPASS at CI rather than silently going green.

## Tasks Completed (4/4)

| # | Task | Commit | Outcome |
|---|------|--------|---------|
| 1 | Extend tests/conftest.py with arm_fixture loader | `7629e49` | arm_fixture importable; existing golden_fixture / amortize_fixture / affordability_fixture untouched. |
| 2 | Create tests/fixtures/arm/ + tests/fixtures/arm/oracle/ via .gitkeep | `c834473` | Both .gitkeep files committed (zero bytes); directories tracked. |
| 3 | Create tests/test_arm.py with 32 xfail stubs covering ARM-01..09 + cross-cutting | `62a6fc0` | 322 lines; 32 test functions; 32 xfail decorators (all strict=True per AST); pytest tests/test_arm.py -v reports 32 XFAIL outcomes. |
| 4 | Verify zero regression to Phase 4 baseline + commit Wave 0 | (verification only — no file changes) | Full suite: 379 passed + 4 skipped + 32 xfailed + 0 failed + 0 errored; mypy --strict + ruff check + ruff format all clean. |

## Stub-to-Wave Flip Map

The contract every downstream wave inherits: each row is one xfail stub Wave 0 ships and the wave that owns flipping it.

| Stub | Requirement | Flipping Wave (Plan) | Reason |
|------|-------------|----------------------|--------|
| `test_arm_terms_field_set` | ARM-01 | Wave 2 (05-02) | ARMTerms Pydantic model |
| `test_arm_terms_missing_floor_rate_raises` | ARM-01 | Wave 2 (05-02) | floor_rate required (no default) |
| `test_note_rate_defaults_to_loan_annual_rate` | ARM-01 | Wave 3 (05-03) | engine note_rate fallback |
| `test_arm_5_1_payment_jump_at_61` | ARM-02 | Wave 6 (05-06) | 5/1 fixture |
| `test_arm_7_1_payment_jump_at_85` | ARM-02 | Wave 6 (05-06) | 7/1 fixture |
| `test_arm_10_1_payment_jump_at_121` | ARM-02 | Wave 6 (05-06) | 10/1 fixture |
| `test_arm_5_6_payment_jump_at_61_and_67` | ARM-02 | Wave 6 (05-06) | 5/6 fixture (D-15) |
| `test_reset_formula_locked` | ARM-03 | Wave 3 (05-03) + Wave 6 (05-06) | clamp(quantize(idx+margin), floor, min(per_ceil, life_ceil)) |
| `test_arm_initial_cap_at_first_reset` | ARM-03 | Wave 6 (05-06) | initial vs periodic cap |
| `test_arm_lifetime_cap_binds` | ARM-03 | Wave 6 (05-06) | lifetime cap binding |
| `test_arm_floor_below_margin_blocked` | ARM-04 | Wave 6 (05-06) | floor enforcement |
| `test_full_remaining_term_re_amortization` | ARM-05 | Wave 3 (05-03) + Wave 6 (05-06) | full-term re-amort (D-05) |
| `test_arm_continuous_period_numbering` | ARM-05 | Wave 6 (05-06) | continuous 1..N; final balance == 0 |
| `test_cumulative_totals_continuous_across_resets` | ARM-05 | Wave 3 (05-03) | cumulative_interest stitch |
| `test_non_final_epoch_does_not_zero_balance` | ARM-05 | Wave 3 (05-03) + Wave 6 (05-06) | slice-stitch invariant (RESEARCH Q1.2 bear trap) |
| `test_initial_fixed_period_matches_phase1_oracle` | ARM-05 | Wave 6 (05-06) | reuse Phase 1 oracle anchor (LM-6) |
| `test_oracle_cross_validation_5_1` | ARM-06 | Wave 6 (05-06) | Bankrate + Vertex42 cross-validation |
| `test_oracle_cross_validation_5_6` | ARM-06 | Wave 6 (05-06) | AmericU 5/6 disclosure |
| `test_arm_5_1_off_by_one_negative` | ARM-07 | Wave 6 (05-06) | month 59/61 boundary (SC-3) |
| `test_cli_smoke_subprocess_round_trip` | ARM-08 | Wave 4 (05-04) | CLI subprocess round-trip |
| `test_cli_help_does_not_import_lib_arm` | ARM-08 | Wave 4 (05-04) | lazy-import (D-18) |
| `test_cli_rejects_float_principal` | ARM-08 | Wave 4 (05-04) | float-gate (D-19) |
| `test_cli_rejects_float_assumed_index_rate` | ARM-08 | Wave 4 (05-04) | float-gate |
| `test_cli_rejects_float_index_path_value` | ARM-08 | Wave 4 (05-04) | float-gate (deep loc) |
| `test_cli_rejects_float_floor_rate` | ARM-08 | Wave 4 (05-04) | float-gate |
| `test_cli_error_envelope_uniformity` | ARM-08 | Wave 4 (05-04) | uniform 6-key envelope (WR-02) |
| `test_cli_misaligned_index_path_period_rejected` | ARM-08 | Wave 2 (05-02) + Wave 4 (05-04) | ARMRequest cross-field validator (D-01) |
| `test_arm_mechanics_doc_sections_present` | ARM-09 | Wave 5 (05-05) | references/arm-mechanics.md (D-08) |
| `test_arm_terms_docstring_cites_arm_mechanics` | ARM-09 | Wave 2 (05-02) + Wave 5 (05-05) | docstring cite (SC-5) |
| `test_arm_mechanics_citations` | ARM-09 | Wave 5 (05-05) | corrected D-08 citations |
| `test_applied_cap_citation_coverage` | cross-cutting | Wave 6 (05-06) | every applied_cap Literal exercised (D-10) |
| `test_arm_teaser_rate` | cross-cutting | Wave 6 (05-06) | teaser-rate ARM (D-02 + LM-3) |

**Counts by flipping wave:** Wave 2 — 4 stubs (1 ARM-01 model field + 1 ARM-01 model validator + 1 ARM-08 cross-field surface + 1 ARM-09 docstring); Wave 3 — 4 stubs (note_rate fallback, reset formula, cumulative stitch, slice-stitch invariant); Wave 4 — 8 stubs (CLI surface); Wave 5 — 3 stubs (doc); Wave 6 — 13 stubs (fixtures + oracle + cross-cutting). Some stubs are co-owned (e.g. `test_reset_formula_locked` requires Wave 3's engine logic + Wave 6's fixture); the wave that lands the *last* missing dependency is responsible for removing the decorator.

## Acceptance Gates

All `<must_haves>` truths confirmed:

- tests/test_arm.py exists in repo and is collected by pytest — `.venv/bin/pytest tests/test_arm.py --collect-only -q` reports 32 tests.
- Every Phase 5 requirement (ARM-01..09) + every cross-cutting test name from 05-VALIDATION.md has a stub function with `@pytest.mark.xfail` decorator — verified via per-name `grep -c "def <name>" tests/test_arm.py` returning 1 for each of the 32 names listed in the plan's `<test_inventory>`.
- Stubbed file runs without ImportError; xfail tests show as XFAIL not ERROR — `.venv/bin/pytest tests/test_arm.py -v --tb=no` reports `32 xfailed in 0.02s`.
- tests/conftest.py exposes `arm_fixture` pytest fixture loadable by name from any test — `from tests.conftest import arm_fixture` succeeds.
- tests/fixtures/arm/ and tests/fixtures/arm/oracle/ directories committed via .gitkeep (both zero bytes).
- Phase 5 test scaffold is additive: no behavior change to Phase 1/3/4 production code or existing tests — full suite still reports 379 passed + 4 skipped (Phase 4 baseline preserved); only NEW XFAIL outcomes were added.

Artifact contracts:

- tests/test_arm.py — 322 lines (>200 floor); 32 xfail stubs covering ARM-01..09 + applied_cap citation coverage + envelope uniformity (test_cli_error_envelope_uniformity).
- tests/conftest.py — contains `def arm_fixture` (1 occurrence) alongside the existing 3 fixtures.
- tests/fixtures/arm/.gitkeep — zero bytes.
- tests/fixtures/arm/oracle/.gitkeep — zero bytes.

Hygiene:

- `mypy --strict tests/conftest.py tests/test_arm.py` → "Success: no issues found in 2 source files".
- `ruff check tests/conftest.py tests/test_arm.py` → "All checks passed!".
- `ruff format --check tests/conftest.py tests/test_arm.py` → "2 files already formatted".

Full-suite numbers (`.venv/bin/pytest -q`):

- 379 passed (Phase 4 baseline of 379 preserved)
- 4 skipped (Phase 4 LTV-ceiling unreachable cases, unchanged)
- 32 xfailed (this plan's scaffold)
- 0 failed
- 0 errored

## Deviations

Three plan-vs-tooling reconciliations; none affect semantic intent. Each is logged with rule classification.

### Rule 1 — plan-text grep gate has malformed substring (cosmetic; structural intent satisfied)

**Found during:** Task 1 acceptance verification.
**Issue:** Plan acceptance criterion `grep -c 'fixtures" / "arm" / f"{stem}.json"' tests/conftest.py returns 1`. The string `'fixtures" / "arm" / f"{stem}.json"'` cannot match the actual code, which is `FIXTURE_DIR / "arm" / f"{stem}.json"` (mirroring the existing amortize_fixture / affordability_fixture pattern that uses the `FIXTURE_DIR` constant from line 19 of conftest.py rather than re-quoting `"fixtures"`).
**Resolution:** Followed the plan's *intent* (path component is exactly `fixtures/arm/<stem>.json`) and *pattern* (mirror existing fixtures verbatim). Confirmed via `grep -E '/ "(amortize|arm|affordability)" / f"\{stem\}.json"'` showing all three fixtures share the same `FIXTURE_DIR / <subsystem> / f"{stem}.json"` shape.
**Impact:** Zero runtime impact. Acceptance criterion's grep-substring is malformed but the equivalent semantic check passes.

### Rule 3 — ruff F401 hook prunes unused-yet imports

**Found during:** Task 3 hygiene re-check (after creating tests/test_arm.py).
**Issue:** Plan instructed Task 3 to import `json, re, subprocess, sys, Decimal, Path` (with note "Imports cover everything subsequent waves need ... No imports of lib.arm yet"). Ruff F401 flagged 5 unused imports (json, re, subprocess, sys, Decimal); only Path (used by SCRIPT_PATH/ARM_MODULE_PATH module constants) and pytest (used by xfail decorator + pytest.fail) are referenced in Wave 0.
**Resolution:** Trimmed imports to actual Wave 0 usage (Path, pytest, Callable, Any). Subsequent waves re-add the others when they flip stubs to real assertions (Wave 4 needs subprocess/json/re for CLI tests; Wave 6 needs Decimal for fixture decoding).
**Impact:** Zero. Each downstream wave's plan must include "add `import json` / `import subprocess` / `from decimal import Decimal`" as a normal coding step when it flips its stubs.

### Rule 3 — ruff format wraps long-reason xfail decorators across two lines

**Found during:** Task 3 hygiene re-check.
**Issue:** Plan acceptance criterion `grep -c '@pytest.mark.xfail(strict=True' tests/test_arm.py returns 32 (one per stub)`. Ruff format reformats 17 of the 32 xfail decorators (the ones with reasons that push the line past the project's line-length limit) to multi-line form, e.g.:
```python
@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_1_payment_jump_at_61.json"
)
```
The literal substring `@pytest.mark.xfail(strict=True` no longer appears on those decorators; substring grep returns 15.
**Resolution:** Left ruff's formatting in place (formatter wins per project deviation Rule 3). Verified semantic equivalence via AST: 32 test functions, 32 xfail decorators with `strict=True`, 32 XFAIL outcomes at runtime.
**Impact:** Zero runtime impact. Future grep gates should match the AST-equivalent pattern, e.g. `grep -B1 'def test_' tests/test_arm.py | grep -c 'strict=True'` returns 32, or use the runtime check `pytest tests/test_arm.py -v --tb=no | grep -c XFAIL` returning 32.

## Threat Mitigations Confirmed

- **T-05-09 (test contract drift)** — All 32 stub names from `<test_inventory>` are present in tests/test_arm.py; verified by per-name grep in Task 3 acceptance.
- **T-05-10 (false-pass via skipped xfail)** — Every xfail uses `strict=True` (32/32 confirmed by AST). An accidental pass will raise XPASS at the wave that flips it; the wave's plan must remove the decorator.
- **T-05-11 (test-suite slowdown)** — All 32 stubs are zero-cost `pytest.fail("Wave 0 stub")`; full suite still runs in 9.02s (vs Phase 4 baseline 9.19s — within noise).
- **T-05-12 (silent regression to Phase 4 baseline)** — Full suite reports ≥379 passed (exactly 379, matching Phase 4 baseline); mypy + ruff clean across both touched files.

## Threat Flags

None. The scaffold introduces no network, auth, file access, or schema surface — only test stubs that fail intentionally.

## Self-Check: PASSED

Files claimed to be created:

- `/Users/cujo253/Documents/mortgage-ops/tests/test_arm.py` — FOUND
- `/Users/cujo253/Documents/mortgage-ops/tests/fixtures/arm/.gitkeep` — FOUND
- `/Users/cujo253/Documents/mortgage-ops/tests/fixtures/arm/oracle/.gitkeep` — FOUND

File modified:

- `/Users/cujo253/Documents/mortgage-ops/tests/conftest.py` — modified (arm_fixture appended at end; existing fixtures unchanged)

Commits claimed:

- `7629e49 feat(05-00): add arm_fixture loader to tests/conftest.py` — FOUND
- `c834473 chore(05-00): create tests/fixtures/arm/ + arm/oracle/ placeholders` — FOUND
- `62a6fc0 test(05-00): add 32 xfail stubs for ARM-01..09 + cross-cutting` — FOUND
