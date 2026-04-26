---
phase: 01-foundations-money-discipline
plan: 04
status: complete
type: tdd
requirements:
  - FND-02
completed_date: 2026-04-26
---

# Phase 01 Plan 04: lib/models.py + Pydantic v2 Model Tests — Summary

Shipped `lib/models.py` — `Money` / `Rate` `Annotated[Decimal, Field(...)]` type aliases plus `Loan`, `Payment`, `Schedule` Pydantic v2 BaseModels with the load-bearing `ConfigDict(strict=True, frozen=True, extra="forbid")` triad. TDD cadence: failing tests committed first (`421daf0`), implementation second (`e6ac22f`). Full Wave-1 phase gate (`ruff check . && ruff format --check . && mypy --strict . && pytest`) exits 0 with 23 tests passing (1 smoke + 8 money + 14 models).

## Status

**COMPLETE.** All `must_haves.truths` verified. All `success_criteria` met. RED→GREEN cadence preserved as separate commits per `type: tdd` contract.

## Public Surface (Phase 4+ imports from here)

| Export       | Type                                                    | Contract                                                                                                                                          |
| ------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Money`      | `Annotated[Decimal, Field(strict=True, ...)]`           | `max_digits=14, decimal_places=2, ge=Decimal("0")` — non-negative money up to 12 integer digits + 2 decimal places                                |
| `Rate`       | `Annotated[Decimal, Field(strict=True, ...)]`           | `max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1")` — fractional rate in [0, 1] with up to 6 decimal places (e.g. 0.065000 = 6.5%) |
| `Loan`       | `pydantic.BaseModel`                                    | `principal: Money`, `annual_rate: Rate`, `term_months: int = Field(ge=1, le=600)`, `origination_date: date \| None = None`, `loan_type: Literal["fixed","arm","fha","va","usda","jumbo"] = "fixed"` |
| `Payment`    | `pydantic.BaseModel`                                    | `period: int = Field(ge=1)`, `payment_date: date`, `payment/principal/interest/balance: Money`, `extra_principal: Money = Decimal("0.00")`        |
| `Schedule`   | `pydantic.BaseModel`                                    | `loan: Loan`, `monthly_pi: Money`, `total_interest: Money`, `payments: list[Payment]`                                                              |

All three BaseModels carry `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`.

## Files Created

| Path                  | Purpose                                                                                                          | Lines |
| --------------------- | ---------------------------------------------------------------------------------------------------------------- | ----- |
| `lib/models.py`       | Pydantic v2 domain models + `Money` / `Rate` Annotated aliases. Module docstring cites FND-02 + Pitfall 10 rationale | 70    |
| `tests/test_models.py` | 14 unit tests proving the FND-02 contract — strict mode, max_digits, ge=0, term boundaries, extra=forbid, frozen, JSON-string serialization, JSON round-trip | 163   |

## Files Modified

None — both files are greenfield additions to a Wave-1 scaffold; sibling 01-03 already shipped `lib/money.py` (no shared edits).

## Commits Made

| SHA       | Subject                                                                                              | Phase |
| --------- | ---------------------------------------------------------------------------------------------------- | ----- |
| `421daf0` | `test(01-04): add failing Pydantic v2 model tests (FND-02)`                                          | RED   |
| `e6ac22f` | `feat(01-04): implement lib/models.py — Loan/Schedule/Payment + Money/Rate aliases (FND-02)`         | GREEN |

(A third commit lands for this SUMMARY.md per `commit_docs: true`.)

REFACTOR step intentionally omitted — implementation is the canonical pattern from `01-RESEARCH.md` Pattern 2; no cleanup beneficial.

## Behavior Contracts Proven by tests/test_models.py

| #  | Test                                                            | Expected                                                                                | Why it matters                                                                                                                  |
| -- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 1  | `test_loan_accepts_decimal_from_string`                         | `Loan(principal=Decimal("400000.00"), …)` constructs                                    | Happy-path Decimal-from-string is the canonical input shape                                                                     |
| 2  | `test_loan_rejects_float_principal`                             | `Loan(principal=400000.0, …)` raises `ValidationError`                                  | **Load-bearing.** `strict=True` rejects float coercion at runtime; mypy `--strict` rejects it at compile time                   |
| 3  | `test_loan_rejects_float_annual_rate`                           | `Loan(annual_rate=0.065, …)` raises `ValidationError`                                   | Same gate applied to `Rate` field                                                                                               |
| 4  | `test_loan_rejects_too_many_decimal_places_on_principal`        | `Loan(principal=Decimal("400000.001"), …)` raises `ValidationError`                     | **Load-bearing.** `decimal_places=2` rejects 3-place precision (defense against Pitfall 7-style sub-cent leakage)               |
| 5  | `test_loan_rejects_negative_principal`                          | `Loan(principal=Decimal("-1.00"), …)` raises `ValidationError`                          | `ge=Decimal("0")` rejects negative dollar amounts                                                                               |
| 6  | `test_loan_rejects_unknown_field`                               | `Loan(…, unknown_field="x")` raises `ValidationError`                                   | `extra="forbid"` surfaces JSON typos as ValidationError instead of silently dropping data                                       |
| 7  | `test_loan_rejects_term_months_below_one`                       | `Loan(term_months=0)` raises `ValidationError`                                          | `Field(ge=1)` lower-bound enforcement                                                                                           |
| 8  | `test_loan_rejects_term_months_above_six_hundred`               | `Loan(term_months=601)` raises `ValidationError`                                        | `Field(le=600)` upper-bound enforcement (50 years is longer than any consumer mortgage product)                                 |
| 9  | `test_loan_is_frozen_after_construction`                        | `loan.principal = Decimal("999.00")` raises `ValidationError`                           | `frozen=True` prevents post-construction mutation (defense against accidental aliasing)                                          |
| 10 | `test_loan_serializes_decimal_as_string_in_json`                | `model_dump_json()` contains `"principal":"400000.00"` (string) and `"term_months":360` (int) | **Load-bearing.** Pitfall 3 documented contract — Phase 9's Node consumer must `Decimal(s)` parse                              |
| 11 | `test_loan_json_round_trips_losslessly`                         | `Loan.model_validate_json(loan.model_dump_json()) == loan`                              | Round-trip integrity; the JSON-string convention deserializes back to the exact same Decimal                                    |
| 12 | `test_payment_constructs_with_phase_3_shape`                    | `Payment(period=1, payment_date=date(2026,5,1), payment=2528.27, ...)` constructs       | Shape validation for Phase 3's amortization rows                                                                                |
| 13 | `test_schedule_aggregates_loan_and_payments`                    | `Schedule(loan=…, monthly_pi=…, total_interest=…, payments=[Payment(…)])` constructs    | Phase 3's output container shape                                                                                                |
| 14 | `test_money_and_rate_aliases_are_exported`                      | `from lib.models import Money, Rate` succeeds                                            | Phase 4+ models reuse these aliases — public-API contract                                                                       |

## Must-Haves Verification

### `must_haves.truths`

| # | Truth                                                                                                                       | Result                                                                                                                                                                                                                          |
| - | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Loan accepts Decimal-from-string for principal and annual_rate, rejects float (strict=True)                                  | **PASS** — Test 1 verifies happy path; Tests 2 & 3 verify float rejection. Independently verified at runtime: `Loan(principal=100.0, ...)` raises `ValidationError` with `decimal_type` error. mypy --strict rejects at compile time. |
| 2 | Loan rejects principal with > 2 decimal places (max_digits=14, decimal_places=2)                                             | **PASS** — Test 4 asserts `Loan(principal=Decimal("400000.001"), ...)` raises `ValidationError`. Independently verified: 3-decimal principal rejected.                                                                              |
| 3 | Loan rejects negative principal and rate (ge=Decimal("0"))                                                                   | **PASS** — Test 5 asserts negative principal raises. `ge=Decimal("0")` is on both Money and Rate aliases.                                                                                                                       |
| 4 | Loan.model_dump_json() emits Decimals as JSON strings (Pitfall 3 documented behavior)                                        | **PASS** — Test 10 asserts literal `"principal":"400000.00"` substring (string, not number). Independently verified: full JSON output is `{"principal":"100.00","annual_rate":"0.065000","term_months":360,...}`.                  |
| 5 | Loan, Schedule, Payment all use ConfigDict(strict=True, frozen=True, extra='forbid')                                         | **PASS** — All three classes carry the directive. Independently verified by introspection: `cls.model_config == {'strict': True, 'frozen': True, 'extra': 'forbid'}` for each of Loan, Schedule, Payment.                          |
| 6 | Money and Rate type aliases are exported for Phase 4+ reuse                                                                 | **PASS** — Test 14 asserts `from lib.models import Money, Rate` succeeds. Both are module-level `Annotated[Decimal, Field(...)]` aliases with full strict/bound annotation.                                                       |

### `must_haves.artifacts`

| Path                 | Provides                                                                                          | Contains                                                              | Verified                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `lib/models.py`      | `Loan, Schedule, Payment` BaseModels + `Money / Rate` Annotated type aliases                      | `ConfigDict(strict=True, frozen=True, extra="forbid")`                | **PASS** — file exists, exports verified by import; configdict literal present (3 occurrences)    |
| `tests/test_models.py` | Unit tests for FND-02: strict mode, max_digits/decimal_places, JSON-string serialization, frozen, extra=forbid | `ValidationError`                                                     | **PASS** — file exists, 14 tests collected, all pass; `ValidationError` referenced in 9 tests     |

### `must_haves.key_links`

| Link                                                                                                            | Pattern                              | Verified                                                                                                              |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `lib/models.py` → `pydantic.BaseModel` via `BaseModel + ConfigDict(strict=True, frozen=True, extra='forbid')`   | `from pydantic import`               | **PASS** — line 20: `from pydantic import BaseModel, ConfigDict, Field`                                              |
| `lib/models.py` → `lib/money.py` via Decimal-discipline reuse                                                   | `lib\.money\|Decimal`                | **PASS** — `lib/models.py` imports `Decimal` from stdlib (the same construct sibling `lib/money.py` exposes via `to_money`); Phase 3+ scripts will validate inbound JSON via these models then trust them |
| `tests/test_models.py` → `lib/models.py` via `from lib.models import Loan, Schedule, Payment, Money, Rate`      | `from lib\.models import`            | **PASS** — line 21: `from lib.models import Loan, Money, Payment, Rate, Schedule` (alphabetized by ruff `I`, semantically identical) |

### Full Wave-1 Phase Gate

```
$ uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest
All checks passed!
9 files already formatted
Success: no issues found in 9 source files
======================== 23 passed in 0.07s ========================
```

All four gates exit 0. Test count target was 23 (1 smoke + 8 money + 14 models) — exactly 23 collected and passing.

### Independent Cross-Checks (beyond the test suite)

| Cross-check                                                                              | Result                                                                                                          |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| mypy --strict on a scratch file with `Loan(principal=400000.0, ...)`                     | **error: Argument "principal" to "Loan" has incompatible type "float"; expected "Decimal" [arg-type]**          |
| Runtime: `Loan(principal=100.0, ...)` raises `ValidationError`                           | **PASS** — confirmed                                                                                            |
| Runtime: `Loan(principal=Decimal("100.001"), ...)` raises `ValidationError`              | **PASS** — confirmed                                                                                            |
| Runtime: `loan.model_dump_json()` literal output                                          | `{"principal":"100.00","annual_rate":"0.065000","term_months":360,"origination_date":null,"loan_type":"fixed"}` |
| All three BaseModel `model_config` introspection                                          | All three: `{'strict': True, 'frozen': True, 'extra': 'forbid'}`                                                |

## Deviations from Plan

### 1. [Rule 1 — Bug] Plan literal `# type: ignore` comment in test docstring tripped mypy `[syntax]`

- **Found during:** Task 1 (RED) verification gate
- **Issue:** The plan's literal content for `tests/test_models.py` includes the prose comment `# type: ignore documents that mypy --strict would catch this at compile time.` directly above the actual `# type: ignore[arg-type]` directive. mypy parses *every* `# type: ignore` comment and reports `error: Invalid "type: ignore" comment [syntax]` because the prose form lacks a bracketed error-code spec.
- **Fix:** Reworded the prose comment to `# The \`# type: ignore[arg-type]\` on the call below documents that mypy --strict / would catch this at compile time; the runtime test verifies Pydantic catches it too.`. The comment text no longer begins with `type: ignore`, so mypy ignores it as ordinary commentary. The underlying `# type: ignore[arg-type]` on the actual call is unchanged and load-bearing.
- **Files modified:** `tests/test_models.py` (one comment block, 2 lines → 3 lines)
- **Commit:** `421daf0` (RED — fix applied before RED commit so the failing-tests commit is itself mypy-syntax-clean)
- **Severity:** Minor. Plan intent ("the line below would be caught by mypy at compile time") preserved.

### 2. [Rule 1 — Bug] Plan literal import of `datetime.date` triggered ruff `TC003`

- **Found during:** Task 2 (GREEN), pre-commit lint gate
- **Issue:** ruff `TC003` (`flake8-type-checking`) flagged `from datetime import date` because `date` only appears in annotations (`origination_date: date | None`, `payment_date: date`). Ruff suggests moving it inside `if TYPE_CHECKING:`. This is **wrong** for Pydantic v2: Pydantic resolves model annotations at runtime via `typing.get_type_hints()` to build validators, so `date` must be runtime-importable. (Same family of footgun as Plan 01 deviation 1's `Callable` resolution.)
- **Fix:** Added `# noqa: TC003  # Pydantic resolves annotations at runtime` to the `from datetime import date` line. The runtime import survives; ruff is silenced for this one line only.
- **Files modified:** `lib/models.py` (one line)
- **Commit:** `e6ac22f`
- **Severity:** Minor. Same Pydantic-runtime-resolution constraint that drove Plan 01's `TYPE_CHECKING`/`Callable` decision; opposite resolution because Pydantic *needs* the runtime import.

### 3. [Rule 1 — Bug] Plan literal `# noqa: F401` import suppressor was unnecessary

- **Found during:** Task 1 (RED), pre-commit lint gate
- **Issue:** The plan specified `from lib.models import Loan, Money, Payment, Rate, Schedule  # noqa: F401`. Ruff's `RUF100` flagged this as `Unused noqa directive` because every imported name (`Loan`, `Money`, `Payment`, `Rate`, `Schedule`) is genuinely used in test bodies — no F401 to suppress.
- **Fix:** Removed the `# noqa: F401` directive. ruff also auto-resorted the import statement (`I001`) so `from lib.models import ...` now sits between `import pytest` and `from pydantic import ValidationError` (alphabetical; ruff treats both `lib` and `pydantic` as third-party because pyproject doesn't set `[tool.ruff.lint.isort] known-first-party`).
- **Files modified:** `tests/test_models.py` (one import line + auto-sort)
- **Commit:** `421daf0`
- **Severity:** Minor. Same family of `I001`/`RUF100` autofixes that hit Plan 01 deviation 1 and Plan 03 deviation 2; plan intent preserved.

No other deviations. No architectural decisions, no auth gates, no scope changes.

## Authentication Gates

None.

## Threat Flags

None — no new security-relevant surface introduced beyond what the plan's `<threat_model>` already enumerated. STRIDE register entries `T-1-13` through `T-1-19` all have shipped mitigations:

- `T-1-13` (T — silent float coercion): `strict=True` + Test 2 + mypy --strict. Defense in depth across compile and runtime.
- `T-1-14` (T — excess Decimal precision): `decimal_places=2` + Test 4.
- `T-1-15` (I — unknown field disclosure): `extra="forbid"` + Test 6.
- `T-1-16` (T — post-construction mutation): `frozen=True` + Test 9.
- `T-1-17` (D — Decimal memory blowup): `max_digits=14` (validation gate fires before any expensive Decimal arithmetic).
- `T-1-18` (T — nonsensical term_months): `Field(ge=1, le=600)` + Tests 7 & 8.
- `T-1-19` (I — JSON output Decimal as float): explicitly `accept-with-doc` per plan; Pydantic v2's intentional behavior emits Decimal as JSON string. Tests 10 & 11 lock the contract; Phase 9 Node writer must `new Decimal(str)` parse incoming strings.

## Forward Notes for Plan 05 + Phase 4+

- **Plan 05 (sibling Wave 2):** Ships `tests/fixtures/golden_pmt.json` + `tests/test_fixtures.py`. No file overlap with this plan; no merge conflict.
- **Phase 3 (amortization scripts):** Will import `Loan`, `Schedule`, `Payment` from `lib.models` and produce `Schedule` instances. Scripts must validate inbound JSON via `Loan.model_validate_json(...)` and trust the parsed model — this is the boundary contract.
- **Phase 4 (affordability/household models):** Will define `Affordability`, `Household` BaseModels that reuse `Money` and `Rate` aliases. The aliases are stable, public surface — do not redefine them downstream.
- **Phase 9 (Node skill orchestration):** Consumes JSON output from Python scripts. Decimal fields arrive as JSON strings (Pitfall 3 contract); Node code must `new Decimal(str)` parse them. `DATA_CONTRACT.md` (Plan 02) declares this; the load-bearing test is `test_loan_serializes_decimal_as_string_in_json`.

## TDD Gate Compliance

Plan type is `tdd`. Verification:

- RED commit (`test(01-04)`): `421daf0` — present, contains `tests/test_models.py` only, no `lib/models.py` (collection failed at import). `pytest` exit was 2.
- GREEN commit (`feat(01-04)`): `e6ac22f` — present, follows RED, contains `lib/models.py` implementation. All 14 tests pass. mypy --strict + ruff exit 0.
- REFACTOR commit: intentionally omitted (implementation is the canonical pattern from `01-RESEARCH.md` Pattern 2; no refactor needed).

Both gate commits visible in `git log --oneline`. RED→GREEN ordering preserved.

## Self-Check: PASSED

- `lib/models.py` exists, 70 lines, contains `Money = Annotated[`, `Rate = Annotated[`, three `class … (BaseModel):` declarations, three `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` literals, and the `Literal["fixed", "arm", "fha", "va", "usda", "jumbo"]` declaration
- `tests/test_models.py` exists, 163 lines, 14 test functions, contains `from lib.models import Loan, Money, Payment, Rate, Schedule`, `ValidationError` (9 occurrences), `400000.001` (max_digits/decimal_places test), `extra` (extra=forbid test), `loan.principal = ` (frozen mutation test), `model_dump_json` (JSON-string test), `model_validate_json` (round-trip test)
- Commits `421daf0` and `e6ac22f` present in `git log --oneline`
- Wave-1 phase gate: `ruff check . && ruff format --check . && mypy --strict . && pytest` exits 0 with 23 passed
- mypy --strict independently rejects `Loan(principal=400000.0, ...)` (verified via scratch file: `error: Argument "principal" to "Loan" has incompatible type "float"; expected "Decimal" [arg-type]`)
- Runtime introspection confirms all three BaseModels carry `{'strict': True, 'frozen': True, 'extra': 'forbid'}`
- Runtime confirms `model_dump_json()` emits `"principal":"100.00"` and `"annual_rate":"0.065000"` as JSON strings
