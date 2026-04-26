---
phase: 01-foundations-money-discipline
plan: 03
status: complete
type: tdd
requirements:
  - FND-01
completed_date: 2026-04-26
---

# Phase 01 Plan 03: lib/money.py + Decimal-Discipline Unit Tests — Summary

Shipped `lib/money.py` — the project's single source of truth for Decimal money discipline (FND-01) — with `to_money(str) -> Decimal`, `quantize_cents(Decimal) -> Decimal` (ROUND_HALF_UP, not banker's), `CENT = Decimal("0.01")`, and `MONEY_CONTEXT = Context(prec=28, rounding=ROUND_HALF_UP)`. TDD: failing tests committed first, implementation second; both commits visible in `git log`. Full Wave-1 phase gate (`ruff check . && ruff format --check . && mypy --strict . && pytest`) exits 0 with 9 tests passing (1 smoke + 8 money).

## Status

**COMPLETE.** All `must_haves.truths` verified. All `success_criteria` met. RED→GREEN cadence preserved as separate commits per TDD type contract.

## Public Surface (Plan 04+ imports from here)

| Export | Type | Contract |
|--------|------|----------|
| `to_money` | `Callable[[str], Decimal]` | String-only construction; `mypy --strict` rejects `to_money(0.065)` at type level (verified via scratch file: `error: Argument 1 to "to_money" has incompatible type "float"; expected "str"`) |
| `quantize_cents` | `Callable[[Decimal], Decimal]` | Quantizes to `CENT` using `ROUND_HALF_UP` inside `with localcontext(MONEY_CONTEXT):` so global `getcontext()` is not mutated (Pitfall 9) |
| `CENT` | `Final[Decimal]` = `Decimal("0.01")` | The quantum for end-of-period money rounding |
| `MONEY_CONTEXT` | `Final[Context]` = `Context(prec=28, rounding=ROUND_HALF_UP)` | Project-wide Decimal context; `prec` is Python's default, `rounding` is overridden because Python's default ROUND_HALF_EVEN is wrong for US consumer mortgage math |

## Files Created

| Path | Purpose | Lines |
|------|---------|-------|
| `lib/money.py` | The Decimal discipline module — module docstring cites FND-01 + Pitfall 2 rationale; uses `from __future__ import annotations`; imports only from `decimal` and `typing.Final` | 46 |
| `tests/test_money.py` | 8 unit tests proving the FND-01 contract — string round-trip, ROUND_HALF_UP at 0.005/0.015/0.025, MONEY_CONTEXT invariants, CENT constant, localcontext non-mutation | 69 |

## Files Modified

None — both files are greenfield additions to a Wave-1 scaffold.

## Commits Made

| SHA | Subject | Phase |
|-----|---------|-------|
| `c16ad7f` | `test(01-03): add failing money discipline tests (FND-01)` | RED |
| `b8b66f7` | `feat(01-03): implement lib/money.py — Decimal discipline (FND-01)` | GREEN |

(A third commit will land for this SUMMARY.md per `commit_docs: true`.)

REFACTOR step intentionally omitted — the implementation is the canonical pattern from `01-RESEARCH.md` Pattern 1 lines 244-275; no cleanup beneficial.

## Behavior Contracts Proven by tests/test_money.py

| # | Test | Hand-calculated expectation | Why it matters |
|---|------|-----------------------------|----------------|
| 1 | `test_to_money_from_string_round_trips` | `to_money("0.065") == Decimal("0.065")` | String construction has no float drift |
| 2 | `test_to_money_preserves_canonical_oracle_string` | `to_money("1264.14") == Decimal("1264.14")` | Wikipedia oracle PMT round-trips intact (FND-09 link) |
| 3 | `test_quantize_cents_uses_round_half_up_at_0p005` | `quantize_cents(Decimal("0.005")) == Decimal("0.01")` | **Load-bearing.** Banker's would yield 0.00 — proves ROUND_HALF_UP is in effect |
| 4 | `test_quantize_cents_uses_round_half_up_at_0p015` | `quantize_cents(Decimal("0.015")) == Decimal("0.02")` | Boundary consistency on odd→up tiebreaker |
| 5 | `test_quantize_cents_uses_round_half_up_at_0p025` | `quantize_cents(Decimal("0.025")) == Decimal("0.03")` | Cleanest discriminator — only ROUND_HALF_UP yields 0.03 (banker's gives 0.02) |
| 6 | `test_money_context_invariants` | `MONEY_CONTEXT.prec == 28` and `MONEY_CONTEXT.rounding == ROUND_HALF_UP` | Future patch flipping either constant fails loud at every test run |
| 7 | `test_cent_constant` | `CENT == Decimal("0.01")` | Quantum constant locked |
| 8 | `test_quantize_cents_does_not_mutate_global_context` | `getcontext().prec` and `getcontext().rounding` unchanged after `quantize_cents(...)` call | Proves `with localcontext(MONEY_CONTEXT):` discipline (Pitfall 9); guards against test-order-dependent flakiness |

## Must-Haves Verification

### `must_haves.truths`

| Truth | Result |
|-------|--------|
| `to_money(s: str) -> Decimal` constructs from strings only (mypy --strict rejects float at type level) | **PASS** — Verified in repo by signature `def to_money(value: str) -> Decimal:`. Independently verified by writing `to_money(0.065)` to a scratch file and running `uv run mypy --strict`: produced `error: Argument 1 to "to_money" has incompatible type "float"; expected "str"  [arg-type]`. |
| `quantize_cents` uses `ROUND_HALF_UP`, not Python's default `ROUND_HALF_EVEN` | **PASS** — Module body contains `value.quantize(CENT, rounding=ROUND_HALF_UP)` and the literal `ROUND_HALF_UP` is imported from `decimal`. Tests 3, 4, 5 prove behavior at three boundaries. |
| `MONEY_CONTEXT.prec == 28` and `MONEY_CONTEXT.rounding == ROUND_HALF_UP` | **PASS** — Module declares `Context(prec=28, rounding=ROUND_HALF_UP)`; test 6 asserts both at runtime. |
| Tests assert `quantize_cents(Decimal('0.005')) == Decimal('0.01')` (NOT 0.00 — banker's would give 0.00) | **PASS** — Test 3 (`test_quantize_cents_uses_round_half_up_at_0p005`) makes exactly this assertion and passes. |

### `must_haves.artifacts`

| Path | Provides | Exports / Contains | Verified |
|------|----------|--------------------|----------|
| `lib/money.py` | `to_money, quantize_cents, CENT, MONEY_CONTEXT` — project-wide Decimal discipline | `to_money`, `quantize_cents`, `CENT`, `MONEY_CONTEXT`; contains literal `ROUND_HALF_UP` | **PASS** — `grep -n ROUND_HALF_UP lib/money.py` returns 3 matches (import, MONEY_CONTEXT init, quantize call) |
| `tests/test_money.py` | Unit tests for FND-01: string construction, ROUND_HALF_UP, immutability | Contains literal `ROUND_HALF_UP` | **PASS** — `grep -n ROUND_HALF_UP tests/test_money.py` returns 4 matches (import, three behavior tests, invariants test) |

### `must_haves.key_links`

| Link | Pattern | Verified |
|------|---------|----------|
| `lib/money.py` → `decimal.Context, decimal.localcontext` via `with localcontext(MONEY_CONTEXT)` | `localcontext\(MONEY_CONTEXT\)` | **PASS** — appears in `quantize_cents` body |
| `tests/test_money.py` → `lib/money.py` via `from lib.money import to_money, quantize_cents, CENT, MONEY_CONTEXT` | `from lib\.money import` | **PASS** — line 16: `from lib.money import CENT, MONEY_CONTEXT, quantize_cents, to_money` (alphabetized by ruff `I` rule, semantically identical) |

### Full Wave-1 Phase Gate

```
$ uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest
All checks passed!
7 files already formatted
Success: no issues found in 7 source files
======================== 9 passed in 0.01s ========================
```

All four gates exit 0. Test count target was 9 (1 smoke + 8 money) — exactly 9 collected and passing.

## Deviations from Plan

### 1. [Rule 1 — Bug] Plan literal content failed `ruff SIM300` (Yoda condition)

- **Found during:** Task 1 (RED), pre-commit lint gate
- **Issue:** The plan's literal test `assert CENT == Decimal("0.01")` (test 7) tripped ruff `SIM300` because ruff treats the named constant `CENT` as the variable side and `Decimal("0.01")` as the literal-constant side, demanding the literal-on-the-left form.
- **Fix:** Inverted to `assert Decimal("0.01") == CENT`. Equality is symmetric, so behavior is byte-identical; the test still proves `CENT == Decimal("0.01")`.
- **Files modified:** `tests/test_money.py` (one line)
- **Commit:** `c16ad7f` (RED — fix applied before the RED commit so the failing-tests commit is itself ruff-clean)
- **Severity:** Minor. Plan intent ("CENT is the quantum") preserved verbatim.

### 2. [Rule 1 — Bug] Plan literal import order failed `ruff I001`

- **Found during:** Task 1 (RED), pre-commit lint gate (autofix)
- **Issue:** The plan's literal `from decimal import Decimal, ROUND_HALF_UP, getcontext` (test file) and `from decimal import Context, Decimal, ROUND_HALF_UP, localcontext` (module file) violate ruff `I001` import-sorting rules because uppercase `ROUND_HALF_UP` should sort before mixed-case `Context`/`Decimal` in alphabetical order. Same ruff `UP`/`I` ruleset that bit Plan 01 (see Plan 01 SUMMARY deviation 1).
- **Fix:** Re-sorted to `from decimal import ROUND_HALF_UP, Context, Decimal, localcontext` (module) and `from decimal import ROUND_HALF_UP, Decimal, getcontext` (test). Imports are functionally identical — same names from same module.
- **Files modified:** `lib/money.py`, `tests/test_money.py`
- **Commits:** `c16ad7f`, `b8b66f7`
- **Severity:** Minor. Ruff `I` is in `[tool.ruff.lint] select` (per Plan 01 config), so this is enforced; the plan's intent ("import what you need from `decimal`") is preserved.

No other deviations. No architectural decisions, no auth gates, no scope changes.

## Authentication Gates

None.

## Threat Flags

None — no new security-relevant surface introduced beyond what the plan's `<threat_model>` already enumerated. STRIDE register entries `T-1-09` (localcontext leak), `T-1-10` (float→Decimal coercion), and `T-1-12` (MONEY_CONTEXT mutation) all have shipped mitigations:

- `T-1-09` — `quantize_cents` uses `with localcontext(MONEY_CONTEXT):`; test 8 asserts `getcontext()` is unchanged after a roundtrip
- `T-1-10` — `to_money(value: str) -> Decimal` is typed str-only; `mypy --strict` rejects float at type level (verified independently)
- `T-1-12` — `MONEY_CONTEXT` is `Final[Context]`; test 6 asserts `prec` and `rounding` at every test run

`T-1-11` (DoS via giant Decimals) is mitigated downstream in Plan 04 (Pydantic `max_digits=14`); not in scope here.

## Forward Notes for Plan 04

- Plan 04 (Pydantic Loan/Schedule/Payment models) imports `to_money` and `quantize_cents` from `lib.money` for `model_dump_json` round-trip stability and any test-side Decimal construction. Do NOT add a parallel money helper module.
- `model_dump_json` should serialize Decimal fields as strings; `to_money` deserializes them back. The Wave-1 oracle string `"1264.14"` is the canonical round-trip target (test 2).
- Pydantic `condecimal(max_digits=14, decimal_places=2)` closes the runtime float-coercion gate at script boundaries; `lib/money.py` does not need a runtime float guard because mypy --strict + Pydantic together provide both type-level and runtime defenses.

## TDD Gate Compliance

Plan type is `tdd`. Verification:

- RED commit (`test(01-03)`): `c16ad7f` — present, contains tests/test_money.py only, no lib/money.py
- GREEN commit (`feat(01-03)`): `b8b66f7` — present, follows RED, contains lib/money.py implementation
- REFACTOR commit: intentionally omitted (implementation is the canonical pattern; no refactor needed)

Both gate commits visible in `git log --oneline`. RED→GREEN ordering preserved.

## Self-Check: PASSED

- `lib/money.py` exists, 46 lines, contains `ROUND_HALF_UP` (3 occurrences), `localcontext(MONEY_CONTEXT)` (1 occurrence), `def to_money(value: str) -> Decimal:`, `def quantize_cents(value: Decimal) -> Decimal:`
- `tests/test_money.py` exists, 69 lines, 8 test functions, contains `from lib.money import CENT, MONEY_CONTEXT, quantize_cents, to_money` and `getcontext()` invariance test
- Commits `c16ad7f` and `b8b66f7` present in `git log --oneline`
- Wave-1 phase gate: `ruff check . && ruff format --check . && mypy --strict . && pytest` exits 0 with 9 passed
- Mypy --strict independently rejects `to_money(0.065)` (verified via scratch file)
