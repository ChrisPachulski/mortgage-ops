# Phase 6: Refinance NPV — Pattern Map

**Mapped:** 2026-05-02
**Phase:** 06-refinance-npv
**Files analyzed:** 14 (existing analogs across Phases 1, 3, 4, 5)
**Analogs found:** 13 / 13 (every new Phase 6 file has a strong existing analog)

## Summary

Phase 6 is **pure composition over Phase 1 (`lib/models.py`, `lib/money.py`), Phase 3 (`lib/amortize.py`, `scripts/amortize.py`, `tests/test_amortize.py`), Phase 4 (the closest sign-convention archetype via `evaluate_reverse` + `npf.pv`), and Phase 5 (`scripts/_cli_helpers.py`, `lib.money.quantize_rate` D-14 promotion)**. Phase 6 introduces NO new external deps — `numpy_financial.npv` (already pinned at 1.0.0) is the canonical NPV primitive; `pyxirr` is **NOT** in `pyproject.toml` (REFI-04 calls it "Optional" — deferred to Phase 8/11 if a multi-offer agent emerges).

The single new architectural primitive is the **`RefiCashflow` discriminated-direction Pydantic model** with a sign-validator (`direction: Literal["outflow","inflow"]` + `@model_validator(mode="after")` that rejects positive amount on outflow and negative on inflow). The closest analog is `lib/affordability.py::ForwardModeRequest._validate_forward` + the cross-field validator pattern at `lib/amortize.py::AmortizeRequest._biweekly_mode_consistency` — same `@model_validator(mode="after")` shape, same "raise ValueError with locked-decision citation in the message" idiom.

Every other Phase 6 deliverable (CLI, fixtures, test layout, references doc, 6-key envelope) has a 1:1 analog in Phase 4 or Phase 5.

## File Classification

| New / Modified File | Role | Closest Analog | Match Quality |
|---|---|---|---|
| `lib/refinance.py` | calc-engine module + Pydantic request/response models | `lib/affordability.py` | exact (composition shape) |
| `scripts/refi_npv.py` | CLI wrapper (JSON-in/JSON-out) | `scripts/affordability.py` | exact (D-13/17/18/19 inheritance + Phase 5 _cli_helpers reuse) |
| `tests/test_refinance.py` | unit + integration + CLI subprocess | `tests/test_affordability.py` + `tests/test_arm.py` | exact |
| `tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json` | golden fixture (SC-1 positive) | `tests/fixtures/affordability/forward_*.json` | exact |
| `tests/fixtures/refinance/negative_npv_same_rate_5k_costs.json` | golden fixture (SC-1 negative) | `tests/fixtures/affordability/forward_*.json` | exact |
| `tests/fixtures/refinance/cash_out_proceeds_50k.json` | golden fixture (SC-3 cash-out) | `tests/fixtures/affordability/forward_*.json` | exact |
| `tests/fixtures/refinance/breakeven_divergence.json` | golden fixture (SC-2 simple≠NPV breakeven) | `tests/fixtures/amortize/extra_principal_step_up.json` | role-match |
| `tests/fixtures/refinance/sign_validator_outflow_positive.json` | rejection fixture (SC-4 negative case) | `tests/fixtures/affordability/forward_invalid_*.json` | exact |
| `tests/fixtures/refinance/.gitkeep` | committed empty placeholder | `tests/fixtures/arm/.gitkeep` | exact |
| `tests/conftest.py` (MODIFY) | add `refinance_fixture` factory | existing `arm_fixture` factory | exact (extend with sibling factory) |
| `references/refi-npv.md` | sign-convention doc + cited from `--help` | `references/arm-mechanics.md` | exact |
| `tests/test_refinance.py` Wave-0 stubs | xfail scaffolding | `tests/test_arm.py` Wave 0 (32 stubs) | exact |
| `scripts/_cli_helpers.py` (REUSE only — no edit) | factor-extracted JSON-float gate + 6-key envelope | already shipped in Phase 5 | exact (reuse) |

## Pattern Assignments

### `lib/refinance.py` (calc engine + Pydantic models)

**Closest analog:** `lib/affordability.py` (537+ lines; composes Phase 1 + Phase 2 + Phase 3 with discriminated unions + `_validate_common` cross-field validators + `evaluate_forward`/`evaluate_reverse` dispatch).

Lift from `lib/affordability.py`:
- **Module docstring header** (`lib/affordability.py:1-172`): "Phase X is the FIRST consumer of …" introduction + LOCKED DECISION blocks D-01..D-NN inline at top of file. Phase 6 lifts this verbatim, replacing AFFD with REFI and adjusting decision content.
- **`from __future__ import annotations`** + **`from decimal import Decimal`** + **`from typing import Annotated, Literal`** (`lib/affordability.py:174-180`) — exact import block ordering.
- **`from lib.amortize import build_schedule`** (`lib/affordability.py:184`) — Phase 3 engine consumption pattern. Phase 6 uses it twice: once for the OLD loan's remaining schedule (to compute interest from "today" through term-end) and once for the NEW loan post-refi.
- **`from lib.money import quantize_cents, quantize_rate`** (`lib/affordability.py:186`) — Phase 5 D-14 promotion is already shipped; Phase 6 inherits.
- **`ConfigDict(strict=True, frozen=True, extra="forbid")`** on every Pydantic model (`lib/affordability.py:341, 354, 362, ...`) — Phase 1 D-08 inherited.
- **Discriminated union via `Field(discriminator="mode")`** (`lib/affordability.py:531-534`) for `RefiRequest = Annotated[RateAndTermRefiRequest | CashOutRefiRequest, Field(discriminator="refi_kind")]`. Models inherit a `_CommonRefiFields` base.
- **`@model_validator(mode="after")` cross-field validator** raising `ValueError` (`lib/amortize.py:184-194` + `lib/affordability.py:507-510`) — the **EXACT** pattern Phase 6 uses for `RefiCashflow`'s sign-direction validator (SC-4):
  ```python
  @model_validator(mode="after")
  def _direction_sign_consistency(self) -> RefiCashflow:
      if self.direction == "outflow" and self.amount > Decimal("0"):
          raise ValueError(
              "outflow cashflow must have non-positive amount; got {self.amount} "
              "(D-04 borrower-perspective sign convention; outflows negative, savings positive; "
              "see references/refi-npv.md)"
          )
      if self.direction == "inflow" and self.amount < Decimal("0"):
          raise ValueError(...)
      return self
  ```
- **Module-level constants block with citation comments** (`lib/affordability.py:214-260` `TARGET_LOAN_TYPE_CROSSWALK` + `_LOAN_TYPE_BLOCKER_PREFIX`) — Phase 6 has `_DEFAULT_DISCOUNT_RATE_BASIS` + `BREAKEVEN_NEVER_SENTINEL`.
- **`evaluate(request) -> RefiResponse` public dispatcher** (`lib/affordability.py` end of file) that switches on `refi_kind` and routes to `_evaluate_rate_and_term` / `_evaluate_cash_out` private helpers. Mirrors `evaluate(req)` dispatcher pattern shipped in Phase 4 Plan 04-04.

**Reverse-affordability sign archetype to mirror (LOAD-BEARING):** `lib/affordability.py::evaluate_reverse` uses `npf.pv(rate=..., nper=..., pmt=-max_PI, fv=0)` and the negative-pmt convention. Phase 6's `_compute_npv` uses `npf.npv(discount_rate, cashflows)` where `cashflows` is a list of `Decimal` per-period values built from `RefiCashflow` instances:
- `direction="outflow"` → negative Decimal (closing costs at t=0; old-loan P&I that stops; whatever the borrower PAYS)
- `direction="inflow"` → positive Decimal (savings = old_pi - new_pi each month; cash-out proceeds at t=0; tax shield if after-tax mode)

### `scripts/refi_npv.py` (CLI)

**Closest analog:** `scripts/affordability.py:1-245` (Phase 4 Plan 04-05 shipped; D-13/17/18/19 + WR-02 6-key envelope inheritance from Phase 3).

Lift verbatim:
- **Module docstring header** (`scripts/affordability.py:1-59`) — full WR-02 envelope contract + Phase 9/10 consumer notes. Replace AFFD references with REFI.
- **`def main() -> int`** + **`argparse.ArgumentParser(prog="refi_npv", ...)`** (`scripts/affordability.py:70-132`) — exact skeleton.
- **`--help` epilog with input JSON shape** (`scripts/affordability.py:74-123`) — Phase 6 documents both `refi_kind="rate_and_term"` and `refi_kind="cash_out"` shapes; **REFI-09 / SC-5 mandate**: include `cite: see references/refi-npv.md for the borrower-perspective sign convention` line in epilog.
- **`sys.path.insert(0, _project_root)`** (`scripts/affordability.py:140-142`) — script-as-script importability shim.
- **Lazy import of `from lib.refinance import RefiRequest, evaluate`** + **`from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope`** AFTER `argparse` parses (`scripts/affordability.py:158-164`) — D-18 fast `--help` discipline.
- **JSON-float pre-validation gate** (`scripts/affordability.py:194-199`) — calls Phase 5's `find_json_float_loc` + `make_decimal_type_envelope`. **DO NOT** re-implement; reuse the shipped helpers.
- **`TypeAdapter(RefiRequest).validate_json(raw)`** (`scripts/affordability.py:205-210`) — discriminated-union TypeAdapter idiom; 6-key envelope on stderr via `e.json()`.
- **`response.model_dump_json(indent=2)`** to stdout (`scripts/affordability.py:240`).

### `tests/test_refinance.py`

**Closest analog:** `tests/test_arm.py` Wave-0 layout (32 xfail stubs) + `tests/test_affordability.py` Wave-6 fixture-flip pattern.

Lift:
- **Module docstring header + `SCRIPT_PATH` + `MODULE_PATH` constants** (`tests/test_arm.py:1-300+`).
- **`@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 06-NN ...")`** decorators on every Wave-0 stub.
- **Subprocess invocation idiom** for CLI tests (`tests/test_arm.py` ARM-08 cluster) — Phase 3 D-17 inheritance.
- **Citation-coverage meta-test** (`tests/test_affordability.py::test_citation_coverage` analog) — Phase 6 asserts every `RefiCashflow` `kind` Literal appears in at least one fixture (per D-08 below).
- **Round-trip / oracle pattern** (`tests/test_amortize.py::test_golden_oracle_*`) — Phase 6 uses the three pinned hand-calc oracles in `06-RESEARCH.md` §"Pinned Oracles".

### `tests/fixtures/refinance/*.json`

**Closest analog:** `tests/fixtures/affordability/*.json` (one fixture per file; Decimal-string values; per-fixture-per-file pattern).

Each fixture has:
- A top-level `request:` block (the JSON the CLI eats)
- A top-level `expected:` block (what `RefiResponse.model_dump_json()` should produce)
- A `_meta:` block with `oracle_source:`, `derivation:`, and `citation:` (mirrors `tests/fixtures/arm/oracle/*` convention).

### `tests/conftest.py` (MODIFY — add `refinance_fixture`)

**Closest analog:** `tests/conftest.py` Plan 05-00 `arm_fixture` extension — verbatim shape with `arm` → `refinance` path swap.

```python
@pytest.fixture
def refinance_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "refinance" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    return _load
```

Append at end of file; do NOT modify existing fixtures.

### `references/refi-npv.md`

**Closest analog:** `references/arm-mechanics.md` (Phase 5 Plan 05-05; cited in `lib/arm.py::ARMTerms` docstring).

Required sections (REFI-09 / SC-5):
1. **Sign Convention (HEADLINE — ROADMAP SC-5 verbatim phrase)**: "outflows negative, savings positive" must appear literally.
2. **Borrower-Perspective NPV Formula**
3. **Discount-Rate Selection** (borrower marginal opportunity cost; default rationale per D-05 below)
4. **Rate-and-Term vs. Cash-Out cashflow inventory**
5. **Simple vs. NPV-Based Breakeven** (with divergence-case worked example)
6. **After-Tax Optional Mode** (D-09: deferred behind a flag; cites `lib.rules.irs_pub936.qualified_loan_limit`)
7. **Citations** (Investopedia / Federal Reserve / IRS Pub 936 RUL-11)

The CLI `--help` epilog (REFI-09 / SC-5) cites this file by relative path.

## Watch Out For

- **`pyxirr` is NOT in `pyproject.toml`.** CLAUDE.md mentions it as a "Rust+PyO3 XIRR/XNPV for batch refi-NPV scenarios" but the on-disk dependency list is `pydantic`, `python-dateutil`, `numpy-financial==1.0.0`, `pyyaml`. **REFI-04 says "Optional `pyxirr` integration for batch NPV across many refi offers" — D-07 below DEFERS pyxirr to Phase 11 (refi-npv-agent multi-offer sweep) and uses `numpy_financial.npv` for v1.** Adding pyxirr is OUT of Phase 6 scope; Phase 6 closes REFI-04 by documenting the deferral with a docstring link to `lib/refinance.py::evaluate` ("pyxirr-batch entry point reserved for Phase 11 SUBA-02").
- **`numpy_financial.npv` quirk #1**: signature is `npv(rate, values)` where `values` is iterable starting at t=0 (NOT t=1). The first cashflow IS the t=0 cashflow. Plan 06-02 + RESEARCH §"NPV Convention" pin this; misuse = off-by-one period that flips signs.
- **`numpy_financial.npv` Decimal handling**: confirmed working with `Decimal` inputs in Phase 3 D-04 (numpy-financial 1.0.0 returns Decimal when fed Decimal). Plan 06-02 verifies empirically before locking.
- **`numpy_financial.irr` IS BROKEN** (bug #131 — arch-dependent). Phase 6 must NOT use it. Use bisection or Newton-Raphson if NPV-based-breakeven needs IRR-style root-finding (we don't — D-06 below uses cumulative-NPV scan, not IRR).
- **Phase 3's `lib.amortize.build_schedule` signature** takes a `Loan` (with required `term_months`, `annual_rate`, `principal`) — for the OLD-loan remaining schedule, Phase 6 must construct a **synthetic Loan** representing "the remaining balance at today's date, amortizing at the OLD rate over the remaining term". This is documented in Plan 06-02 as `_build_old_loan_residual` private helper; the trap is using `loan.term_months` from the original loan note instead of `remaining_months`.
- **Sign-convention rigor (LOAD-BEARING for SC-1 + SC-4)**: The `RefiCashflow` model must reject construction-time sign violations BEFORE the cashflow list reaches `_compute_npv`. If sign-checking is done inside `_compute_npv`, a malformed user input (`{"direction":"outflow","amount":"500.00"}`) silently flips NPV. Plan 06-01 ships the validator at the model layer per SC-4 verbatim.
- **`lib.money.quantize_cents` end-of-period only** (CLAUDE.md FND-01). NPV intermediate computations stay at full Decimal precision (28 digits via `MONEY_CONTEXT`); quantize ONLY at the final `RefiResponse.npv` boundary. Same discipline as Phase 4 PITI.
- **`lib.money.quantize_rate` for the discount rate** (Phase 5 D-14 promotion). The discount rate is a `Rate`-typed Decimal in [0,1] with 6 decimal places. Plan 06-02 quantizes the caller-supplied `discount_rate_annual` once at request entry and uses it throughout.
- **Phase 1 `Rate` type constraint `le=Decimal("1")`** (`lib/models.py:31`). The discount rate per ANNUM (e.g. 0.05 = 5%) fits; Phase 6 documents this in `RefiRequest.discount_rate_annual` field comment so callers don't pass `Decimal("5")` thinking percent.
- **No `pyxirr`, no `pandas`** in Phase 6 (kept lean — pandas was listed as a stack option but has not been adopted in any phase yet).

## Cross-Phase Dependencies

| Phase 6 imports | From phase | File:lines |
|---|---|---|
| `Loan`, `Money`, `Rate` | Phase 1 | `lib/models.py:23-46` |
| `quantize_cents`, `quantize_rate` | Phase 1 + Phase 5 D-14 | `lib/money.py:39-73` |
| `build_schedule` | Phase 3 | `lib/amortize.py:255-292` |
| `find_json_float_loc`, `make_decimal_type_envelope` | Phase 5 | `scripts/_cli_helpers.py:22-106` |
| (optional) `qualified_loan_limit` | Phase 2 RUL-11 | `lib/rules/irs_pub936.py` (only if D-09 after-tax mode is invoked) |

| Phase 6 EXPORTS to (downstream) | Consumed by phase |
|---|---|
| `RefiRequest`, `RefiResponse`, `evaluate()` | Phase 8 (stress sweeps over refi offers) — STRS-01 / STRS-02 |
| `RefiCashflow` model | Phase 11 SUBA-02 (refi-npv-agent multi-offer ranking) |
| `references/refi-npv.md` | Phase 10 SKILL.md `references/` bundle (SKLL-08) |
| `scripts/refi_npv.py` | Phase 10 `.claude/skills/mortgage-ops/scripts/` relocation (SKLL-10) |
