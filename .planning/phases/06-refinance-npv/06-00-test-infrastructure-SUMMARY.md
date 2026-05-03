---
phase: 06
plan: 00
subsystem: test-infrastructure
tags:
  - phase-06
  - refinance-npv
  - test-infrastructure
  - nyquist
  - xfail-stubs
requires: []
provides:
  - "tests.conftest.refinance_fixture (parametric loader for tests/fixtures/refinance/)"
  - "tests/test_refinance.py (25 xfail-decorated stubs covering REFI-01..09 + SC-1..5 + SC-4 sign-validator + cross-cutting)"
  - "tests/fixtures/refinance/ directory (committed via .gitkeep)"
affects:
  - "Wave 1 (Plan 06-01): flips 5 stubs (4 sign-validator + 1 module-docstring cite)"
  - "Wave 2 (Plan 06-02): empirical engine validation; flips 0 stubs (rate-and-term math validated by Wave 5 fixtures)"
  - "Wave 3 (Plan 06-03): flips 1 stub (after-tax cross-field validator, D-09)"
  - "Wave 4 (Plan 06-04): flips 6 stubs (CLI subprocess + lazy-import + 3 float-rejections + envelope + SC-5 cite)"
  - "Wave 5 (Plan 06-05): flips 11 stubs (rate-and-term + cash-out + breakeven + cashflow-kind coverage + pyxirr-deferred docstring)"
  - "Wave 6 (Plan 06-06): flips 2 stubs (references/refi-npv.md sections + sign-convention phrase)"
tech-stack:
  added: []
  patterns:
    - "FIXTURE_DIR / refinance / <stem>.json loader — verbatim mirror of arm_fixture / affordability_fixture / amortize_fixture (Phase 4/5 inheritance, D-15)"
    - "subprocess-only CLI invocation reservation (D-17 inherited; subprocess + sys imported with noqa: F401 reserved-for-Wave-4)"
    - "SCRIPT_PATH + REFINANCE_MODULE_PATH + REFI_NPV_DOC_PATH module constants for Phase 10 relocation single-edit portability"
    - "@pytest.mark.xfail(strict=True) Nyquist gate — Phase 5 inheritance; XPASS hard-fails CI so flipping waves MUST remove decorators"
key-files:
  created:
    - tests/test_refinance.py
    - tests/fixtures/refinance/.gitkeep
    - .planning/phases/06-refinance-npv/06-00-test-infrastructure-SUMMARY.md
  modified:
    - tests/conftest.py
key-decisions:
  - "All 25 stubs use @pytest.mark.xfail(strict=True); flipping waves MUST also remove the decorator (Rule-2 from PLAN deviation_rules)."
  - "Reserved imports (json, re, subprocess, sys, Decimal, Any, Callable) are kept with `# noqa: F401  (reserved for Wave N ...)` comments rather than re-added per wave; downstream waves drop the noqa when they actually use the symbol. Trades stub-file purity for zero per-wave import-churn."
  - "Long xfail decorator reasons were ruff-format-broken across multiple lines; PLAN acceptance criterion `grep -c '@pytest.mark.xfail(strict=True'` returns 3 (only single-line decorators match the literal substring), but the semantic invariant — 25 strict xfail decorators, 25 XFAIL pytest outcomes, 0 FAILED, 0 ERROR — is fully satisfied. Documented as Rule-3 deviation (ruff format wins, mirrors Plan 05-00 same-shape note)."
  - "Phase 5 actual baseline at execution time was 436 passed (PLAN cited ≥432 from earlier ROADMAP snapshot prior to Phase 5 weak-rope WR-01..05 fix commits). Wave 0 is purely additive — no regressions to passes/skips/failures; xfailed went 1 → 26 (= 1 inherited Phase 5 strict xfail + 25 new Phase 6 stubs)."
patterns-established:
  - "Phase-6 test scaffold mirrors Phase 5 Plan 05-00 verbatim: empty fixtures dir + .gitkeep + per-requirement xfail stubs with locked-verbatim names + conftest fixture loader"
  - "Reserved-import-with-noqa convention for Wave-0 scaffolds (avoids per-wave import churn)"
requirements-completed: []

# Metrics
duration: 4m 16s
completed: 2026-05-03
---

# Phase 6 Plan 00: Test Infrastructure Summary

Wave 0 of Phase 6 (Refinance NPV) lands the Nyquist validation scaffold for the 7-plan phase: 25 strict-xfail-decorated test stubs in `tests/test_refinance.py` covering every REFI-01..09 + SC-1..5 closure + the SC-4 model-layer sign-validator + cross-cutting Literal-coverage and after-tax-cross-field-validator gates, the `refinance_fixture` parametric loader extending `tests/conftest.py`, and the empty `tests/fixtures/refinance/` directory committed via `.gitkeep` — every requirement-closing wave (Plans 06-01..06) now has a known landing pad to flip xfail → pass against, with `strict=True` guaranteeing a stub that accidentally passes raises XPASS at CI rather than silently going green.

## Performance

- **Duration:** 4m 16s
- **Started:** 2026-05-03T05:25:02Z
- **Completed:** 2026-05-03T05:29:18Z
- **Tasks:** 4/4
- **Files modified:** 1
- **Files created:** 2

## Accomplishments

- 25 strict-xfail stubs in `tests/test_refinance.py` (302 lines), all collecting as XFAIL with zero FAILED/ERROR
- `refinance_fixture` pytest fixture appended to `tests/conftest.py` (mirrors `arm_fixture` shape verbatim — `arm` → `refinance` swap)
- `tests/fixtures/refinance/.gitkeep` committed (empty, 0 bytes); directory ready for Wave 5 hand-calc fixtures
- Phase 5 baseline preserved exactly: 436 passed + 4 skipped + 26 xfailed (was 436 passed + 4 skipped + 1 xfailed; +25 from Wave 0 additions); 0 failed; 0 errored
- mypy --strict + ruff check + ruff format all clean across `tests/conftest.py` and `tests/test_refinance.py`
- Module constants (`SCRIPT_PATH`, `REFINANCE_MODULE_PATH`, `REFI_NPV_DOC_PATH`) wired for Phase 10 single-constant-edit relocation portability

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend tests/conftest.py with refinance_fixture loader** — `eca1a57` (feat)
2. **Task 2: Create tests/fixtures/refinance/.gitkeep** — `e2a1a61` (chore)
3. **Task 3: Create tests/test_refinance.py with 25 xfail stubs** — `bbfb674` (test)
4. **Task 4: Verify zero regression to Phase 5 baseline** — verification-only (no source changes; mypy/ruff/pytest all green; consolidated into Plan metadata commit)

**Plan metadata:** _to be appended_ (final commit covers SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md)

## Files Created/Modified

- `tests/conftest.py` — Appended `refinance_fixture` Pydantic-fixture-loader factory after the existing `arm_fixture` (D-15 path: `FIXTURE_DIR / "refinance" / f"{stem}.json"`)
- `tests/test_refinance.py` — 302 lines, 25 strict-xfail stubs covering: REFI-01 (3) + REFI-02 (3) + REFI-03 (3) + REFI-04 deferral (1) + REFI-08 CLI (6) + REFI-09 doc (3) + SC-4 sign-validator (4) + cross-cutting Literal-kind coverage + after-tax validator (2)
- `tests/fixtures/refinance/.gitkeep` — Empty placeholder (0 bytes) so the directory commits

## Decisions Made

- **Strict-xfail across all 25 stubs**: Phase 5 inheritance; flipping waves MUST also remove the decorator or pytest XPASS-fails (Rule-2 from `PLAN.md::deviation_rules`).
- **Reserved-imports-with-noqa**: rather than have each downstream wave re-edit the import block, Wave 0 imports `json`, `re`, `subprocess`, `sys`, `Decimal`, `Any`, `Callable` upfront with `# noqa: F401  (reserved for Wave N ...)` rationale comments. Downstream waves drop the noqa when they actually use the symbol. Trades a 7-line stub-file overhead for zero per-wave import churn.
- **Verbatim test names locked**: 25 names from `PLAN.md::test_inventory` are committed as-is. Per Rule-1, downstream waves can rename only via documented Rule-1 deviations in their SUMMARY.md.
- **Phase 6 wave-1 flip count tightening**: PLAN cites 5 wave-1 flips (4 sign-validator + 1 module-docstring cite), but the docstring `Wave 1 (Plan 06-01)` block lists 5 also (matches). The PLAN-CHECK Per-Plan Audit row for 06-01 says "5 (4 sign-validator + 1 docstring cite)". No flip-count drift.

## Deviations from Plan

### Rule-3 (Hygiene): ruff format multi-lined long xfail decorator reasons

- **Found during:** Task 3 (after initial Write of tests/test_refinance.py)
- **Issue:** PLAN acceptance criterion `grep -c '@pytest.mark.xfail(strict=True'` was specified to return 25, but ruff format auto-broke 22 of the 25 long-reason decorators across multiple lines (e.g., `@pytest.mark.xfail(\n    strict=True, reason="..."\n)`), so the literal-substring grep returns 3.
- **Fix:** None required — semantic invariant is satisfied:
  - 25 `@pytest.mark.xfail(` decorators (multiline-aware grep)
  - 25 `def test_` definitions
  - 25 XFAIL outcomes via `pytest tests/test_refinance.py --tb=no -q`
  - 0 FAILED, 0 ERROR
  - All 25 stub names from PLAN test_inventory present exactly once (per-name grep loop verified)
- **Files modified:** `tests/test_refinance.py` (ruff format auto-fix)
- **Verification:** `pytest tests/test_refinance.py --tb=no -q` → `25 xfailed in 0.02s`; `mypy --strict` + `ruff check` + `ruff format --check` all clean
- **Committed in:** `bbfb674` (Task 3 commit; ruff format applied before commit)
- **Precedent:** Identical Rule-3 deviation in `.planning/phases/05-arm-modeling/05-00-SUMMARY.md` key-decisions section ("ruff format multi-lined long-reason xfail decorators; the plan's grep gate is satisfied semantically").

### Rule-3 (Hygiene): ruff isort moved Callable import inside parens

- **Found during:** Task 3 (after initial Write)
- **Issue:** Wrote `from collections.abc import Callable  # noqa: F401  ...`; ruff isort wanted it as `from collections.abc import (\n    Callable,  # noqa: F401  ...\n)` due to line length.
- **Fix:** Auto-applied via `ruff check --fix`.
- **Files modified:** `tests/test_refinance.py`
- **Committed in:** `bbfb674`

---

**Total deviations:** 2 auto-fixed (both Rule-3 hygiene; ruff formatter wins; zero scope-creep)
**Impact on plan:** No semantic impact — every locked invariant in PLAN.md (25 stubs, 25 XFAIL outcomes, all 25 names verbatim, Phase 5 baseline preserved, mypy/ruff clean) is satisfied. The ruff-format multi-line reason-string is cosmetic and the same precedent was set in Phase 5 Plan 05-00.

## Issues Encountered

None — plan executed cleanly. Pre-commit hooks (ruff legacy + ruff format + mypy) ran on every commit and passed.

## Authentication Gates

None — Wave 0 is pure file-creation (no external services touched).

## Verification Outcomes

| Acceptance criterion (PLAN.md) | Result |
| --- | --- |
| `grep -c 'def refinance_fixture' tests/conftest.py` returns 1 | PASS (1) |
| `grep -c 'def arm_fixture' tests/conftest.py` returns 1 | PASS (1) |
| `grep -c 'def affordability_fixture' tests/conftest.py` returns 1 | PASS (1) |
| `grep -c '"refinance"' tests/conftest.py` returns 1 | PASS (1) |
| `pytest tests/test_arm.py tests/test_affordability.py tests/test_amortize.py --collect-only -q` exits 0 | PASS (161 tests collected, 0 errors) |
| `tests/fixtures/refinance/.gitkeep` exists, 0 bytes | PASS |
| `grep -c '@pytest.mark.xfail(strict=True' tests/test_refinance.py` returns 25 | DEVIATION (Rule-3 ruff format → 3 single-line; semantic invariant satisfied via multiline-aware grep + 25 XFAIL pytest outcomes) |
| `grep -c 'def test_' tests/test_refinance.py` returns 25 | PASS (25) |
| Every stub name from test_inventory appears exactly once | PASS (25/25 per-name grep) |
| `grep -c 'SCRIPT_PATH: Path = ...refi_npv.py' tests/test_refinance.py` returns 1 | PASS (1) |
| `pytest tests/test_refinance.py -v --tb=no` shows 25 XFAIL | PASS (25 xfailed) |
| `pytest tests/test_refinance.py -v --tb=no` shows 0 FAILED + 0 ERROR | PASS |
| `pytest -q` shows ≥ 432 passed | PASS (436 passed; baseline drift +4 vs PLAN due to post-PLAN Phase 5 WR fixes — additive only) |
| `pytest -q` shows ≥ 25 new xfailed (total ≥ 26) | PASS (26 xfailed total) |
| 0 failed, 0 errored | PASS |
| mypy --strict + ruff clean | PASS |

## Self-Check: PASSED

- `tests/conftest.py` exists and contains `def refinance_fixture` — FOUND
- `tests/test_refinance.py` exists (302 lines, 25 stubs) — FOUND
- `tests/fixtures/refinance/.gitkeep` exists (0 bytes) — FOUND
- Commit `eca1a57` (Task 1: refinance_fixture) — FOUND in `git log --oneline`
- Commit `e2a1a61` (Task 2: .gitkeep) — FOUND in `git log --oneline`
- Commit `bbfb674` (Task 3: 25 stubs) — FOUND in `git log --oneline`

## Next Phase Readiness

- **Wave 1 (Plan 06-01)** can now flip 5 stubs (4 SC-4 sign-validator + 1 D-16 module-docstring cite) once `lib/refinance.py::RefiCashflow` model + `_direction_sign_consistency` validator + module docstring ship.
- **Wave 2 (Plan 06-02)** flips 0 stubs (engine validation is empirical against Oracle 1/Oracle 2 hand-calcs); rate-and-term + breakeven helper landing zone is open.
- **Wave 3 (Plan 06-03)** flips 1 stub (after-tax cross-field validator) once `after_tax_mode` opt-in + `_validate_after_tax_inputs` ship.
- **Wave 4 (Plan 06-04)** flips 6 stubs once `scripts/refi_npv.py` + 6-key envelope + lazy-import + SC-5 `--help` epilog cite ship.
- **Wave 5 (Plan 06-05)** flips 11 stubs once 6 fixtures (positive-NPV + negative-NPV + cash-out + breakeven-divergence + sign-validator-rejection + after-tax-smoke) land in `tests/fixtures/refinance/`.
- **Wave 6 (Plan 06-06)** flips the final 2 stubs once `references/refi-npv.md` (≥250 lines + literal "outflows negative, savings positive" phrase) ships.
- No blockers; Wave 1 is unblocked.

---
*Phase: 06-refinance-npv*
*Completed: 2026-05-03*
