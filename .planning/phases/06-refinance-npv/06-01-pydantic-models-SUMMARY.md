---
phase: 06
plan: 01
subsystem: pydantic-models
tags:
  - phase-06
  - refinance-npv
  - pydantic-models
  - sign-validator
  - sc-4
requires:
  - "tests.conftest.refinance_fixture (Plan 06-00)"
  - "tests/test_refinance.py 25 xfail stubs (Plan 06-00)"
  - "lib.models.Loan / Money / Rate (Phase 1)"
  - "lib.amortize.build_schedule (Phase 3)"
  - "lib.money.quantize_cents / quantize_rate (Phase 1 + Phase 5 D-14)"
  - "numpy_financial.npv (already pinned 1.0.0)"
provides:
  - "lib.refinance.RefiCashflow (D-03 + SC-4 sign-validator)"
  - "lib.refinance.RefiBreakeven (SC-2 dual-form sub-model)"
  - "lib.refinance._CommonRefiFields (D-02 base; not instantiated)"
  - "lib.refinance.RateAndTermRefiRequest (D-02 leaf; refi_kind='rate_and_term')"
  - "lib.refinance.CashOutRefiRequest (D-02 leaf; refi_kind='cash_out')"
  - "lib.refinance.RefiRequest (D-02 Pydantic v2 discriminated union)"
  - "lib.refinance.RefiResponse (SC-1/SC-2/SC-3 surface; cashflow audit trail)"
  - "lib.refinance._validate_common (D-09 after-tax cross-field validator)"
  - "lib.refinance.evaluate_rate_and_term (cross-plan stub; Plan 06-02 ships body)"
  - "lib.refinance.evaluate_cash_out (cross-plan stub; Plan 06-03 ships body)"
  - "lib.refinance.evaluate (cross-plan stub; Plan 06-04 ships body)"
  - "lib.refinance.SIGN_CONVENTION_CITATION + BREAKEVEN_NEVER_SENTINEL constants"
affects:
  - "Wave 2 (Plan 06-02): consumes RateAndTermRefiRequest + RefiResponse + RefiCashflow + RefiBreakeven; ships evaluate_rate_and_term body + _compute_npv + _compute_breakeven_simple/_npv helpers"
  - "Wave 3 (Plan 06-03): consumes CashOutRefiRequest + after_tax_mode fields; ships evaluate_cash_out body + tax_shield cashflow stream"
  - "Wave 4 (Plan 06-04): consumes RefiRequest discriminated union + evaluate stub; ships scripts/refi_npv.py CLI + 6-key envelope + lazy-import + SC-5 --help epilog"
  - "Wave 5 (Plan 06-05): consumes RefiCashflow.kind Literal for citation-coverage test; consumes RefiResponse.cashflows audit trail for fixture assertions"
  - "Wave 6 (Plan 06-06): no direct dependency (doc-layer plan); module-docstring-cite test already flipped here"
tech-stack:
  added: []
  patterns:
    - "@model_validator(mode='after') sign-direction consistency check at Pydantic boundary (mirrors lib/affordability.py::_validate_forward + lib/arm.py::_floor_does_not_exceed_lifetime_ceiling)"
    - "Pydantic v2 discriminated union via Annotated[A | B, Field(discriminator='X')] alias (mirrors lib/affordability.py::AffordabilityRequest)"
    - "_CommonRequestFields base + leaf-variants pattern for shared-field DRY (mirrors lib/affordability.py::_CommonRequestFields)"
    - "Cross-plan stub idiom: NotImplementedError with explicit cite to the wave that ships the body (Phase 2 D-08 inheritance)"
    - "Module-docstring LOCKED DECISION blocks D-01..D-16 inline at top of file (mirrors lib/affordability.py:22-172)"
    - "amount: Decimal (NOT Money) for sign-bearing fields where Money's ge=0 would block negatives at the type layer (D-03)"
    - "Module-level constants (SIGN_CONVENTION_CITATION, BREAKEVEN_NEVER_SENTINEL) for grep-discoverability + single-source-of-truth citation strings"
    - "Reserved-import-with-noqa convention for Wave-1 placeholders (Loan / build_schedule / quantize_cents / quantize_rate / npf / date / Sequence) consumed by Waves 2-4"
key-files:
  created:
    - lib/refinance.py
    - .planning/phases/06-refinance-npv/06-01-pydantic-models-SUMMARY.md
  modified:
    - tests/test_refinance.py
key-decisions:
  - "D-01..D-16 inherited verbatim from 06-RESEARCH.md; LOCKED DECISION blocks shipped inline in lib/refinance.py module docstring (15 decision blocks total covering deps, structure, sign-validator shape, sign convention, discount rate, breakeven algo, pyxirr deferral, PMI/MIP carve-out, after-tax mode, override field, horizon, closing-cost financing, fixture details, zero-amount carve-out, top-level closing_costs, citation surfaces)"
  - "RefiCashflow.amount uses raw Decimal (NOT lib.models.Money) because Money is ge=0 — would block negative outflow amounts BEFORE the @model_validator can run. Constrained via Field(strict=True, max_digits=14, decimal_places=2) to inherit money discipline without the ge=0 floor (D-03)."
  - "_validate_common enforces after-tax-mode cross-field requirement at construction time (D-09): when after_tax_mode=True, BOTH marginal_tax_rate AND filing_status must be supplied; otherwise tax_shield cashflow stream cannot be built. The reverse direction (after_tax_mode=False with tax fields supplied) is NOT enforced at construction so callers can carry tax fields across mode toggles without re-constructing the request."
  - "Reserved-import-with-noqa convention adopted (mirrors Phase 6 Plan 06-00 test scaffold convention): Loan / build_schedule / quantize_cents / quantize_rate / npf / date / Sequence imported at top of lib/refinance.py with `# noqa: F401  (reserved for Plan 06-NN ...)` rationale comments. Waves 2-4 drop the noqa when the symbol is consumed; trades a 5-line module-top overhead for zero per-wave import-block churn."
  - "TC001 noqa applied on Money + Rate imports (matches lib/models.py convention). The lint rule fires because both symbols appear only in Pydantic field annotations, but Pydantic v2 resolves field annotations at runtime — moving them to TYPE_CHECKING would break Pydantic at import. Documented inline."
  - "Module docstring opens with the verbatim D-04 sign convention statement AND cites references/refi-npv.md so the on-disk artifact satisfies both halves of test_lib_refinance_module_docstring_cites (the test reads the file directly, not via __doc__, so future readers see the contract immediately at the import boundary)."
requirements-completed: []  # REFI-01 + REFI-02 are partially closed (model layer); engine bodies ship Waves 2-3, full closure tracked at Plan 06-04 (CLI) or Plan 06-05 (fixture flips)
metrics:
  duration: 7m 11s
  completed: 2026-05-03
---

# Phase 06 Plan 01: Pydantic Models Summary

Wave 1 of Phase 6 (Refinance NPV) ships the entire Pydantic v2 type contract for `lib/refinance.py` — 6 strict+frozen+forbid models (RefiCashflow with the SC-4 sign-validator + RefiBreakeven sub-model + _CommonRefiFields base + RateAndTermRefiRequest + CashOutRefiRequest + RefiResponse) plus the RefiRequest discriminated-union alias plus 3 cross-plan stubs (evaluate_rate_and_term / evaluate_cash_out / evaluate) — and flips the 5 Wave-0 xfail stubs that the model layer closes (4 sign-validator behaviors + 1 module-docstring citation). Engine math arrives in Wave 2 (rate-and-term + breakeven helpers, Plan 06-02), Wave 3 (cash-out + after-tax mode, Plan 06-03), and Wave 4 (CLI dispatcher, Plan 06-04). The SC-4 sign-rigor anchor — "constructing an outflow with positive amount or inflow with negative amount raises a validation error" — is now a Pydantic-boundary fact, not a runtime assertion that engine code could bypass.

## Performance

- **Duration:** 7m 11s
- **Started:** 2026-05-03T05:36:24Z
- **Completed:** 2026-05-03 (single-session, sequential)
- **Tasks:** 2 / 2
- **Files created:** 1 (lib/refinance.py — 567 lines)
- **Files modified:** 1 (tests/test_refinance.py — +107 / -30 lines net; 5 xfail decorators removed + 5 real bodies + 3 new imports + 1 import re-sort)

## Accomplishments

- `lib/refinance.py` shipped at 567 lines with the full LOCKED DECISION header (D-01..D-16; 15 decision blocks) opening with the verbatim D-04 sign-convention statement and citing `references/refi-npv.md` per D-16. Module is importable; `mypy --strict` clean; `ruff check` + `ruff format --check` clean.
- All 6 Pydantic models satisfy `ConfigDict(strict=True, frozen=True, extra="forbid")` (Phase 1 D-08 inheritance). Verified via `grep -c 'ConfigDict(strict=True, frozen=True, extra=\"forbid\")' lib/refinance.py` returning 6.
- `RefiCashflow` ships with `direction: Literal["outflow", "inflow"]` + `amount: Decimal` (NOT Money — Money's ge=0 would block negative outflows at the type layer before the validator can fire) + `kind: Literal[5 values]` + `period: int (ge=0)` + `@model_validator(mode="after") _direction_sign_consistency` that rejects sign-mismatched constructions per D-04 SC-4. Zero accepted in either direction per D-14.
- `RefiBreakeven` sub-model with paired `(simple_months, simple_status)` and `(npv_months, npv_status)` fields encodes SC-2 dual-form breakeven reporting; `*_status` Literals distinguish failure modes (`no_savings` / `zero_costs` / `never_breaks_even`).
- `_CommonRefiFields` base carries the 9 shared fields used by both refi variants: `old_loan_balance` / `old_annual_rate` / `old_remaining_months` / `new_annual_rate` / `new_term_months` / `closing_costs` (D-15 top-level) / `discount_rate_annual` (D-05 REQUIRED) / `analysis_horizon_months` (D-11 optional) / after-tax block (`after_tax_mode` / `marginal_tax_rate` / `filing_status` / `has_grandfathered_debt` per D-09) / `new_loan_monthly_pi_override` (D-10 cash-out PMI/MIP escape hatch).
- `_validate_common` enforces D-09 cross-field requirement: when `after_tax_mode=True`, BOTH `marginal_tax_rate` AND `filing_status` MUST be supplied. Validator wired into both `RateAndTermRefiRequest._validate_rate_and_term` and `CashOutRefiRequest._validate_cash_out` after-validators (mirrors Phase 4's `ForwardModeRequest._validate_forward` / `ReverseModeRequest._validate_reverse` pattern).
- `RateAndTermRefiRequest` adds `refi_kind: Literal["rate_and_term"] = "rate_and_term"`. `CashOutRefiRequest` adds `refi_kind: Literal["cash_out"] = "cash_out"` + `cash_out_amount: Money = Field(gt=Decimal("0"))` (a cash-out by definition has positive cash extraction; rate-and-term is the zero-cash-out sibling).
- `RefiRequest = Annotated[RateAndTermRefiRequest | CashOutRefiRequest, Field(discriminator="refi_kind")]` Pydantic v2 discriminated union per D-02; mirrors `lib/affordability.py::AffordabilityRequest` exactly.
- `RefiResponse` populated for both refi_kind variants: `npv` (signed Decimal NOT Money), `breakeven` (RefiBreakeven), `old_monthly_pi` / `new_monthly_pi` (Money), `monthly_savings` (signed), cash-out-only `cash_proceeds` / `monthly_payment_delta` / `total_interest_delta` (None for rate-and-term), `after_tax_npv` (None unless `after_tax_mode=True`), `discount_rate_annual_used` + `analysis_horizon_months_used` (echoes for traceability), `cashflows: list[RefiCashflow]` (per-period audit trail), `warnings: list[str]` (soft signals).
- 3 cross-plan stubs (`evaluate_rate_and_term` / `evaluate_cash_out` / `evaluate`) raise `NotImplementedError` with explicit cites to the wave that ships the body (Phase 2 D-08 cross-plan stub idiom inheritance).
- Module-level constants `SIGN_CONVENTION_CITATION: Final[str]` and `BREAKEVEN_NEVER_SENTINEL: Final[None]` provide single-source-of-truth strings for the validator error messages and the breakeven helpers (Plan 06-02 will consume `BREAKEVEN_NEVER_SENTINEL`).
- 5 Wave-0 xfail stubs flipped to PASS:
  - `test_refi_cashflow_outflow_positive_rejected` — pytest.raises(ValidationError, match="outflow cashflow must have non-positive amount") on RefiCashflow(direction='outflow', amount=Decimal('2000.00'), ...)
  - `test_refi_cashflow_inflow_negative_rejected` — pytest.raises(ValidationError, match="inflow cashflow must have non-negative amount") on RefiCashflow(direction='inflow', amount=Decimal('-100.00'), ...)
  - `test_refi_cashflow_zero_accepted_either_dir` — both outflow + inflow with amount=Decimal('0.00') construct cleanly + round-trip field values per D-14
  - `test_refi_cashflow_correctly_signed_passes` — outflow + amount=Decimal('-2000.00') (kind='closing_costs') AND inflow + amount=Decimal('366.57') (kind='monthly_savings') both construct + round-trip per SC-4 happy path
  - `test_lib_refinance_module_docstring_cites` — reads lib/refinance.py from disk and asserts both `references/refi-npv.md` AND verbatim phrase `outflows negative, savings positive` are present (D-16 belt-and-suspenders surface)
- Phase 5 baseline preserved exactly: 441 passed (was 436 + 5 = 441) + 4 skipped + 21 xfailed (was 26 - 5 flipped) + 0 failed + 0 errored. Net delta: +5 passed, -5 xfailed, no other movement.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lib/refinance.py with module docstring + imports + 6 Pydantic models** — `f1ec795` (feat)
2. **Task 2: Flip 4 Wave-0 stubs (SC-4 sign-validator coverage) + 1 module-docstring-cite stub to passing tests** — `34b6132` (test)

**Plan metadata:** _to be appended_ (final commit covers SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md)

## Files Created/Modified

- `lib/refinance.py` (created, 567 lines) — Module docstring with D-01..D-16 LOCKED DECISION blocks (opens with verbatim D-04 sign convention + cites references/refi-npv.md per D-16); imports (Loan/Money/Rate/build_schedule/quantize_cents/quantize_rate/npf/date/Sequence with reserved-noqa where consumed Waves 2-4; Money + Rate carry TC001 noqa for the Pydantic-runtime-resolution pattern from lib/models.py); 2 module-level constants (SIGN_CONVENTION_CITATION + BREAKEVEN_NEVER_SENTINEL); 6 Pydantic models + 1 base + 1 union alias; 1 cross-field validator (_validate_common); 3 cross-plan stubs (evaluate_rate_and_term + evaluate_cash_out + evaluate)
- `tests/test_refinance.py` (modified, +107 / -30 net) — Added 3 runtime imports (Decimal — was reserved-noqa; ValidationError from pydantic; RefiCashflow from lib.refinance); removed 5 @pytest.mark.xfail decorators + their pytest.fail("Wave 0 stub") bodies; shipped 5 real test bodies (4 SC-4 sign-validator behaviors + 1 D-16 module-docstring cite). Imports re-sorted to alphabetical third-party group (lib < pydantic < pytest) per existing project convention from tests/test_affordability.py.

## Decisions Made

- **D-01..D-16 inherited verbatim from 06-RESEARCH.md.** All 16 decisions are now documented inline in lib/refinance.py module docstring as LOCKED DECISION blocks (the D-15 entry covers the closing_costs-as-top-level-field convention; the D-16 entry inventories the 4 belt-and-suspenders citation surfaces). No re-decision in this plan.
- **`amount: Decimal` (NOT lib.models.Money) for RefiCashflow** — Money's `ge=Decimal("0")` would reject negative outflows AT THE TYPE LAYER before the @model_validator can fire, defeating the whole SC-4 sign-validator design. Constrained via `Field(strict=True, max_digits=14, decimal_places=2)` to inherit money discipline (strict=True rejects floats; 14-digit cap matches Money) without the ge=0 floor. Documented in RefiCashflow class docstring AND in module-docstring D-03 LOCKED DECISION block.
- **`_validate_common` enforces D-09 at construction time, but only the True→required direction** — when `after_tax_mode=True`, both `marginal_tax_rate` AND `filing_status` MUST be supplied (otherwise the tax_shield cashflow stream cannot be built). The reverse (after_tax_mode=False with tax fields supplied) is NOT enforced at construction so callers can carry tax fields across mode toggles without re-constructing the request. Plan 06-03 engine body will warn-but-allow on this case.
- **Reserved-import-with-noqa convention** (mirrors Phase 6 Plan 06-00 test scaffold + Phase 5 inheritance) — `Loan`, `build_schedule`, `quantize_cents`, `quantize_rate`, `numpy_financial as npf`, `date`, `Sequence` are all imported at top of lib/refinance.py with `# noqa: F401  (reserved for Plan 06-NN ...)` rationale comments. Waves 2-4 drop the noqa when the symbol becomes consumed at runtime; trades a 7-line stub-file overhead for zero per-wave import-block churn (matches the Plan 06-00 stub-file convention; same precedent in Phase 5).
- **TC001 noqa on Money + Rate imports** (matches lib/models.py convention) — both symbols appear only in Pydantic field annotations in this file, which makes ruff's TC001 lint flag them as type-checking-only imports. But Pydantic v2 resolves field annotations at runtime — moving them to TYPE_CHECKING would break model construction at import. The noqa is documented inline with a "Pydantic resolves annotations at runtime" rationale matching the lib/models.py:18 convention.
- **Module docstring opens with the verbatim D-04 sign-convention statement AND cites references/refi-npv.md** so the on-disk artifact satisfies both halves of test_lib_refinance_module_docstring_cites (the test reads the file from disk via REFINANCE_MODULE_PATH.read_text(), NOT via __doc__ — this defends against future docstring stripping by build tools and ensures the on-disk source contains the SC-5 verbatim phrase).
- **Cross-plan stub error messages cite the wave + plan number explicitly** ("Plan 06-02 ships rate-and-term engine body (Wave 2 of Phase 6)" etc.) so a downstream caller hitting the stub sees the exact remediation path. Mirrors Phase 2 D-08 cross-plan stub idiom verbatim.

## Deviations from Plan

### Rule-3 (Hygiene): ruff TC001 on Money + Rate imports

- **Found during:** Task 1 (after first ruff check on lib/refinance.py)
- **Issue:** ruff TC001 fired on `from lib.models import Loan, Money, Rate` because Money + Rate appear only in Pydantic field annotations. ruff's static analysis sees them as type-checking-only and wants them moved into a TYPE_CHECKING block. But Pydantic v2 resolves field annotations at runtime — moving them to TYPE_CHECKING would break model construction at import.
- **Fix:** Split the import into a multi-line form and added `# noqa: TC001  (Pydantic resolves annotations at runtime; matches lib/models.py convention)` on Money + Rate (Loan keeps `# noqa: F401  (reserved for Plan 06-02 schedule synthesis)` because it's not yet used in any annotation — Plan 06-02 will consume it for `Loan(principal=..., annual_rate=...)` schedule synthesis and drop the noqa).
- **Files modified:** `lib/refinance.py`
- **Verification:** `.venv/bin/ruff check lib/refinance.py` exits 0; `.venv/bin/ruff format --check lib/refinance.py` exits 0; `.venv/bin/mypy --strict lib/refinance.py` exits 0
- **Committed in:** `f1ec795` (Task 1 commit)
- **Precedent:** `lib/models.py:18` uses identical pattern (`from datetime import date  # noqa: TC003  # Pydantic resolves annotations at runtime`); the convention is documented in Phase 4 Plan 04-01 deviations as well (TC001/TC003 noqa with reworded comment block to dodge RUF100 on 'noqa codes' substring).

### Rule-3 (Hygiene): ruff format auto-applied to lib/refinance.py

- **Found during:** Task 1 (after `.venv/bin/ruff check`)
- **Issue:** `ruff format --check` reported "Would reformat: lib/refinance.py" — auto-formatter wanted to adjust trivia (likely line-wrapping in the `from lib.models import (Loan, Money, Rate)` block I had just split for the TC001 noqa).
- **Fix:** Ran `.venv/bin/ruff format lib/refinance.py` to apply the auto-format. Re-verified mypy --strict + ruff check + ruff format --check all clean.
- **Files modified:** `lib/refinance.py`
- **Verification:** `.venv/bin/ruff format --check lib/refinance.py` exits 0
- **Committed in:** `f1ec795` (Task 1 commit; format applied before commit)
- **Precedent:** Eighth occurrence of this hygiene-class deviation in the project (mirrors Phase 4 Plan 04-04 SUMMARY: "ruff format auto-formats across the two task commits — seventh occurrence of this hygiene-class deviation in the project; no semantic changes to math contract").

### Rule-3 (Hygiene): ruff I001 import-block re-sort in tests/test_refinance.py

- **Found during:** Task 2 (after first ruff check on the import additions)
- **Issue:** Added `from pydantic import ValidationError` and `from lib.refinance import RefiCashflow` to tests/test_refinance.py; ruff I001 wanted them sorted differently. ruff's isort treats `lib.*` as third-party (no `known-first-party = ["lib"]` configuration in pyproject.toml — the `tool.ruff.src = ["lib", "tests", "scripts"]` setting affects path resolution but NOT first-party classification for isort).
- **Fix:** Manually re-sorted to match `tests/test_affordability.py` convention: `import pytest` / `from lib.refinance import RefiCashflow` / `from pydantic import ValidationError` (alphabetical within the third-party group: `lib` < `pydantic` < `pytest` is the order ruff wants for `from`-imports following an `import` statement).
- **Files modified:** `tests/test_refinance.py`
- **Verification:** `.venv/bin/ruff check tests/test_refinance.py` exits 0
- **Committed in:** `34b6132` (Task 2 commit)
- **Precedent:** `tests/test_affordability.py:38-67` uses identical ordering (`import pytest` then `import yaml as _yaml` then `from lib.affordability import (...)`).

---

**Total deviations:** 3 auto-fixed (all Rule-3 hygiene; ruff TC001 + ruff format + ruff I001; zero semantic impact)
**Impact on plan:** No semantic impact — every locked invariant (SC-4 sign-validator behavior + D-14 zero-acceptance carve-out + D-16 module-docstring cite + 6 strict+frozen+forbid models + RefiRequest discriminated union + 5 stubs flipped + Phase 5 baseline preserved) is satisfied.

## Issues Encountered

None — plan executed cleanly. Pre-commit hooks (ruff legacy + ruff format + mypy) ran on every commit and passed.

## Authentication Gates

None — Wave 1 is pure file-creation + test-flip (no external services touched).

## Verification Outcomes

| Acceptance criterion (PLAN.md Task 1) | Result |
| --- | --- |
| `python -c "from lib.refinance import RefiCashflow, RefiBreakeven, RateAndTermRefiRequest, CashOutRefiRequest, RefiRequest, RefiResponse"` exits 0 | PASS (returned `OK`) |
| `grep -c 'class RefiCashflow' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'class RefiBreakeven' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'class _CommonRefiFields' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'class RateAndTermRefiRequest' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'class CashOutRefiRequest' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'class RefiResponse' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'RefiRequest = Annotated' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'Literal\["outflow", "inflow"\]' lib/refinance.py` returns 1 | PASS (1; on RefiCashflow.direction line) |
| `grep -c 'def _direction_sign_consistency' lib/refinance.py` returns 1 | PASS (1) |
| `grep -c 'outflows negative, savings positive' lib/refinance.py` returns ≥ 1 | PASS (3 — module docstring opening + module-docstring D-04 LOCKED DECISION block + outflow validator error message; inflow validator error message also contains the phrase but in a context grep counts as 3 distinct occurrences) |
| `grep -c 'references/refi-npv.md' lib/refinance.py` returns ≥ 2 | PASS (10 — module docstring + 9 D-NN LOCKED DECISION block citations + validator error messages via SIGN_CONVENTION_CITATION constant) |
| `grep -c 'ConfigDict(strict=True, frozen=True, extra="forbid")' lib/refinance.py` returns ≥ 6 | PASS (6 — one per Pydantic model: RefiCashflow + RefiBreakeven + _CommonRefiFields + RateAndTermRefiRequest + CashOutRefiRequest + RefiResponse) |
| `mypy --strict lib/refinance.py` exits 0 | PASS |
| `ruff check lib/refinance.py` exits 0 | PASS |
| `ruff format --check lib/refinance.py` exits 0 | PASS |

| Acceptance criterion (PLAN.md Task 2) | Result |
| --- | --- |
| All 5 listed tests PASS (no longer XFAIL) | PASS — verified via `pytest tests/test_refinance.py::test_refi_cashflow_outflow_positive_rejected tests/test_refinance.py::test_refi_cashflow_inflow_negative_rejected tests/test_refinance.py::test_refi_cashflow_zero_accepted_either_dir tests/test_refinance.py::test_refi_cashflow_correctly_signed_passes tests/test_refinance.py::test_lib_refinance_module_docstring_cites -v` → 5 passed |
| Other 20 stubs remain XFAIL | PASS — full suite shows 21 xfailed (= 20 remaining Phase 6 stubs + 1 inherited Phase 5 strict xfail) |
| Phase 5 baseline preserved (≥ 432 passed; now ≥ 437 with the 5 flipped) | PASS (441 passed; was 436 baseline + 5 flips; +5 net) |
| mypy + ruff clean | PASS — `mypy --strict lib/refinance.py tests/test_refinance.py` Success; `ruff check lib/refinance.py tests/test_refinance.py` All checks passed; `ruff format --check lib/refinance.py tests/test_refinance.py` 2 files already formatted |

## Known Stubs

3 intentional `NotImplementedError` stubs remain in lib/refinance.py — these are the planned cross-plan stub idiom from Phase 2 D-08 (the PLAN's `<objective>` says "Wave 1 ships ONLY: types + validators + cross-plan stubs for `evaluate_rate_and_term` / `evaluate_cash_out` / `evaluate` (stub bodies raise NotImplementedError with cite to Wave 2/3 plan)"):

| Function | File:line | Reason | Resolved by |
|---|---|---|---|
| `evaluate_rate_and_term(req)` | `lib/refinance.py:534` | Wave 2 ships rate-and-term engine math | Plan 06-02 |
| `evaluate_cash_out(req)` | `lib/refinance.py:550` | Wave 3 ships cash-out + after-tax math | Plan 06-03 |
| `evaluate(req)` | `lib/refinance.py:565` | Wave 4 ships public discriminated-union dispatcher | Plan 06-04 |

Each NotImplementedError message explicitly cites the resolving plan + wave so a downstream caller hitting the stub sees the exact remediation path. NO unintentional stubs (no hardcoded `[]` / `{}` / `null` placeholder UI data; no "coming soon" / "not available" strings).

## Self-Check: PASSED

- `lib/refinance.py` exists at `/Users/cujo253/Documents/mortgage-ops/lib/refinance.py` — FOUND (567 lines)
- `tests/test_refinance.py` modified with 5 flipped stubs + new RefiCashflow + ValidationError + Decimal imports — FOUND (`grep -c 'pytest.mark.xfail' tests/test_refinance.py` returns 20 — was 25 in Wave 0, exactly -5)
- Commit `f1ec795` (Task 1: feat add lib/refinance.py) — FOUND in `git log --oneline -5`
- Commit `34b6132` (Task 2: test flip 5 Wave-0 xfail stubs) — FOUND in `git log --oneline -5`
- Both commits passed pre-commit hooks (ruff legacy + ruff format + mypy + check yaml + block-user-layer)
- mypy --strict + ruff check + ruff format --check all clean across both modified files
- Full pytest suite: 441 passed + 4 skipped + 21 xfailed + 0 failed + 0 errored (was 436 + 4 + 26; net +5 passed, -5 xfailed, no other movement)

## Next Phase Readiness

- **Wave 2 (Plan 06-02)** unblocked — can now ship `evaluate_rate_and_term` body + `_compute_npv` + `_compute_breakeven_simple` + `_compute_breakeven_npv` + `_build_old_loan_residual` private helpers. Will consume `RateAndTermRefiRequest` + `RefiResponse` + `RefiCashflow` + `RefiBreakeven` + `BREAKEVEN_NEVER_SENTINEL` from this plan; will drop the `# noqa: F401` from `Loan` + `build_schedule` + `numpy_financial as npf` + `quantize_cents` + `quantize_rate` + `date` once consumed at runtime.
- **Wave 3 (Plan 06-03)** unblocked — can now ship `evaluate_cash_out` body + tax_shield cashflow stream + StaleReferenceWarning surfacing for the after-tax IRS Pub 936 lookup. Will consume `CashOutRefiRequest` + the after_tax_mode block on `_CommonRefiFields` + `_validate_common`'s D-09 cross-field check + the `after_tax_npv` + `cash_proceeds` + `monthly_payment_delta` + `total_interest_delta` fields on `RefiResponse`.
- **Wave 4 (Plan 06-04)** unblocked — can now ship `scripts/refi_npv.py` + 6-key envelope on stderr + lazy-import discipline + SC-5 --help epilog + the `evaluate(req)` dispatcher body. Will consume `RefiRequest` discriminated union + `TypeAdapter(RefiRequest).validate_json` at the script boundary.
- **Wave 5 (Plan 06-05)** unblocked at the type layer — will ship 6 fixtures + flip 11 fixture-driven tests (engine math validation must wait on Waves 2-3 bodies before fixtures can be derived empirically). Will consume `RefiCashflow.kind` Literal coverage + `RefiResponse.cashflows` audit trail.
- **Wave 6 (Plan 06-06)** unblocked at the doc layer — will ship `references/refi-npv.md` (≥250 lines + verbatim "outflows negative, savings positive" phrase) + flip the remaining 2 doc tests. The module-docstring-cite test was already flipped here, so Wave 6 ships only 2 more flips (sections + verbatim phrase).
- No blockers; Wave 2 is unblocked. Phase 6 remains on the 5/7 + 1/7 → 2/7 plan track.

---
*Phase: 06-refinance-npv*
*Completed: 2026-05-03*
