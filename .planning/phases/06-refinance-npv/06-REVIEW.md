---
phase: 06-refinance-npv
reviewed: 2026-05-02T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - lib/refinance.py
  - scripts/refi_npv.py
  - references/refi-npv.md
  - tests/conftest.py
  - tests/test_refinance.py
  - tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json
  - tests/fixtures/refinance/negative_npv_short_horizon.json
  - tests/fixtures/refinance/cash_out_proceeds_50k.json
  - tests/fixtures/refinance/breakeven_divergence.json
  - tests/fixtures/refinance/sign_validator_outflow_positive.json
  - tests/fixtures/refinance/after_tax_mode_smoke.json
findings:
  blocker: 1
  warning: 9
  info: 5
  total: 15
status: issues_found
---

# Phase 6: Refinance NPV - Code Review Report

**Reviewed:** 2026-05-02
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 6 ships a discriminated-union refi NPV engine (rate-and-term + cash-out, optional after-tax overlay) plus a JSON-in/JSON-out CLI, fixtures, and a borrower-perspective conventions doc. The work hews to project money-discipline rules (Decimal-from-strings, end-of-period quantize, no `npf.irr` per D-06, lazy script imports per D-18, 6-key envelope per WR-02). Pydantic v2 models correctly carry `strict=True, frozen=True, extra="forbid"` everywhere, and the SC-4 sign-validator on `RefiCashflow` is well-tested at the model layer.

However, several real defects exist that should be addressed before downstream consumers (Phase 9 orchestration / Phase 10 skill / Phase 11 multi-offer agent) take dependencies on this surface:

1. A **BLOCKER** in `evaluate_cash_out` causes the audit-trail cashflow stream to silently lose the cash-out proceeds inflow when `closing_costs >= cash_out_amount`. The NPV math is unaffected when costs strictly exceed proceeds, but on the equality boundary the entire cash-out side disappears from the audit trail, breaking SC-3's "labeled top-level + audit-trail" contract.
2. Two NEVER-EXERCISED fixtures (`after_tax_mode_smoke.json`, `sign_validator_outflow_positive.json`) ship pinned engine outputs that no test runs `evaluate()` against — the after-tax mode's `tax_shield` numerical contract (`amount: "300.00"`, `after_tax_npv: "96584.52"`) is therefore unverified at engine-output level despite shipping in fixtures.
3. The CLI's `FileNotFoundError` envelope dereferences `e.filename` which is `None` when the FileNotFoundError originates from `Path.read_text()` (Python wraps it through `open()`); the resulting envelope reports `"input file not found: None"` — broken UX.
4. Several lesser issues: docstring drift on `total_interest_delta`, simple-breakeven not honoring `analysis_horizon_months`, missing tests for cash-out negative-net path, and one defensive double-quantization.

The sign convention is enforced at the right place (Pydantic model boundary), no `npf.irr` is invoked, no `eval`/`exec`/`shell=True`, no hardcoded secrets, no float/Decimal mixing in math expressions. The discriminated union routing is sound and the dispatcher fail-loud branch is appropriate.

## Critical Issues

### CR-01: `evaluate_cash_out` drops cash-out inflow from audit trail when `closing_costs >= cash_out_amount` (BLOCKER)

**File:** `lib/refinance.py:986-1001`

**Issue:** The else branch of the cash_proceeds netting block (lines 994-1001) calls `_build_refi_cashflows` with `cash_proceeds_net=Decimal("0.00")`. Per `_build_refi_cashflows` line 595 (`if cash_proceeds_net > Decimal("0"):`), no `cash_proceeds` cashflow is emitted. Combined with the engine's else branch passing `closing_costs=req.closing_costs`, the audit trail surfaces ONLY a `closing_costs` outflow — the borrower's actual `cash_out_amount` inflow disappears from `RefiResponse.cashflows` entirely.

Concretely:
- When `closing_costs > cash_out_amount` (truly pathological): the audit trail shows `-closing_costs` outflow but no `+cash_out_amount` inflow. NPV is wrong because the loss-side gross cash receipt has been dropped from the model. A consumer reconstructing the NPV by summing `cashflows` will get a different number than `RefiResponse.npv` claims.
- When `closing_costs == cash_out_amount` (edge): `cash_proceeds_net == 0`, the inequality `> 0` fails, and the engine again drops the cash side. The audit trail loses both the proceeds AND the closing-costs netting story even though both actually occurred.

The fixture suite has NO scenario covering either case; the bug is unreachable through current fixtures and CLI examples but would surface the moment a real consumer (Phase 11 multi-offer agent comparing low-cash-out vs. high-fee offers) hits it. The CashOutRefiRequest model has `cash_out_amount: Money = Field(gt=Decimal("0"))` but nothing constrains `cash_out_amount > closing_costs` — the pathology is reachable.

The docstring at lines 921-926 acknowledges the negative-net path and claims "we keep cash_proceeds out of the t=0 cashflow inflow stream so NPV still uses signed cash flows correctly via the closing_costs outflow path" — this is INCORRECT. Dropping the cash inflow does NOT preserve NPV correctness; it erases the gross receipt from the borrower's signed-cashflow stream entirely.

**Fix:** Always emit BOTH cash_out_amount inflow AND closing_costs outflow as separate cashflows on the negative-net path, so the audit trail and NPV both reflect both legs of the actual transaction:

```python
if cash_proceeds_net > Decimal("0.00"):
    # Typical: closing costs netted into cash_proceeds per CFPB convention
    cashflows = _build_refi_cashflows(
        closing_costs=Decimal("0.00"),
        old_monthly_pi=old_monthly_pi,
        new_monthly_pi=new_monthly_pi,
        horizon_months=horizon,
        cash_proceeds_net=cash_proceeds_net,
    )
else:
    # Pathological: closing >= cash_out. Surface BOTH gross legs
    # (closing_costs outflow + cash_out_amount inflow) so NPV math
    # and audit trail agree on what actually moved.
    cashflows = _build_refi_cashflows(
        closing_costs=req.closing_costs,
        old_monthly_pi=old_monthly_pi,
        new_monthly_pi=new_monthly_pi,
        horizon_months=horizon,
        cash_proceeds_net=req.cash_out_amount,  # gross inflow, not net
    )
```

Then add a fixture exercising `closing_costs >= cash_out_amount` and a test that asserts `sum(cf.amount for cf in resp.cashflows if cf.period == 0)` equals `cash_out_amount - closing_costs`.

## Warnings

### WR-01: After-tax mode fixture is never exercised by any executing test

**File:** `tests/fixtures/refinance/after_tax_mode_smoke.json` (inputs/expected); `tests/test_refinance.py` (no consumer)

**Issue:** `after_tax_mode_smoke.json` pins concrete engine outputs: `npv: "60705.48"`, `after_tax_npv: "96584.52"`, and a `tax_shield_sample` block with `amount: "300.00"`. The only test that touches this fixture is `test_refi_cashflow_kind_citation_coverage` (test_refinance.py:879), which globs `*.json` and asserts `expected.cashflows_kinds` contains the required Literals — it does NOT call `evaluate()` and does NOT verify the pinned numerical values. Therefore the after-tax NPV math is unprotected by the test suite at the engine-output level. A regression in `_compute_tax_shield_cashflows` (e.g., wrong period indexing, wrong qualified_loan_limit branch, wrong marginal_tax_rate multiplication) would NOT be caught by any flipped test.

Additionally, `test_after_tax_mode_validator_requires_all` only exercises Pydantic validator-layer behavior (D-09 cross-field requirement); it does not call `evaluate()` with `after_tax_mode=True`.

**Fix:** Add a fixture-driven engine test that invokes `evaluate()` on `after_tax_mode_smoke.json` and asserts strict Decimal equality on `npv`, `after_tax_npv`, and the `tax_shield_sample` cashflow:

```python
def test_refi_after_tax_mode_engine(refinance_fixture):
    fx = refinance_fixture("after_tax_mode_smoke")
    req = RateAndTermRefiRequest.model_validate_json(json.dumps(fx["request"]))
    from lib.refinance import evaluate
    resp = evaluate(req)
    expected = fx["expected"]
    assert Decimal(resp.npv) == Decimal(expected["npv"])
    assert resp.after_tax_npv is not None
    assert Decimal(resp.after_tax_npv) == Decimal(expected["after_tax_npv"])
    # tax_shield first-period sample
    sample = expected["tax_shield_sample"]
    first_shield = next(cf for cf in resp.cashflows if cf.kind == "tax_shield")
    assert first_shield.period == sample["period"]
    assert Decimal(first_shield.amount) == Decimal(sample["amount"])
```

### WR-02: `sign_validator_outflow_positive.json` fixture is never consumed by any test

**File:** `tests/fixtures/refinance/sign_validator_outflow_positive.json`; `tests/test_refinance.py`

**Issue:** Per its `_meta` docstring, this fixture is supposed to exercise the CLI-layer 6-key envelope on a Rate-bound violation (`discount_rate_annual="1.5"` exceeds `Rate le=1`). No test in `tests/test_refinance.py` references it (`grep sign_validator_outflow_positive` returns zero hits). The CLI envelope-uniformity contract for Rate-bound violations is therefore unprotected.

The only Rate-related CLI test is `test_cli_rejects_float_discount_rate` which exercises the float-gate path, NOT the `le=1` validator path. The two paths produce 6-key envelopes through different code routes (manual `make_decimal_type_envelope` vs Pydantic native `e.json()`), and only the first is currently subprocess-tested for envelope shape on a Rate field.

**Fix:** Add a CLI subprocess test that consumes this fixture and asserts the 6-key envelope shape on a Rate `le=1` violation:

```python
def test_cli_rate_le1_envelope(refinance_fixture, tmp_path):
    fx = refinance_fixture("sign_validator_outflow_positive")
    p = tmp_path / "rate_violation.json"
    p.write_text(json.dumps(fx["request"]))
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(p)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == fx["expected"]["exit_code"]
    err = json.loads(result.stderr)[0]
    assert set(err.keys()) == set(fx["expected"]["envelope_keys"])
    assert err["type"] == fx["expected"]["error_type"]
```

### WR-03: `FileNotFoundError` envelope reports `e.filename` which is `None` for `Path.read_text()`

**File:** `scripts/refi_npv.py:196-202`

**Issue:** The handler catches `FileNotFoundError as e` and emits `f"input file not found: {e.filename}"`. When `Path.read_text()` (or any `Path.open()`-derived call) raises FileNotFoundError under CPython, `e.filename` is set, BUT the canonical contract is fragile — `e.filename` is only populated when the OS-level `open()` raised it, and on some interpreter / pathlib paths it may be None. More reliably, the user's actual input is `args.input` (already a `Path` object the script holds). Reporting `e.filename` instead of `args.input` is a regression vs the user-input echo pattern other scripts in this repo use, and produces awkward error messages on edge cases (symlink chain breaks, EACCES masquerading as FileNotFoundError, etc.).

**Fix:** Echo the user's argument back (this is what they typed; this is what's broken from their POV):

```python
except FileNotFoundError:
    print(
        json.dumps({"error": f"input file not found: {args.input}"}),
        file=sys.stderr,
    )
    return 2
except OSError as e:
    print(
        json.dumps({"error": f"could not read input file {args.input}: {e}"}),
        file=sys.stderr,
    )
    return 2
```

### WR-04: `_compute_breakeven_simple` ignores `analysis_horizon_months`, can return values exceeding the analysis horizon

**File:** `lib/refinance.py:672-689` (helper); `lib/refinance.py:863, 1037` (callsites)

**Issue:** `_compute_breakeven_simple(closing_costs, monthly_savings)` does not take horizon as a parameter and returns `ceil(closing_costs / monthly_savings)` unconditionally. The negative-NPV fixture (`negative_npv_short_horizon.json`) demonstrates the issue concretely: `analysis_horizon_months=12`, `monthly_savings=$366.57`, `closing_costs=$5000` → simple_months=14, status="ok". The borrower asked "model my decision over a 12-month tenure" and gets back "you'll break even at month 14" — an answer that lies outside the analysis horizon they explicitly requested.

The NPV-based breakeven correctly returns `(None, "never_breaks_even")` for the same scenario (because cumulative NPV at the truncated cashflow stream never crosses zero). The two breakeven values now contradict each other in a way the consumer cannot diagnose without re-reading docstrings.

**Fix:** Either (a) accept and honor `horizon_months`:

```python
def _compute_breakeven_simple(
    closing_costs: Decimal,
    monthly_savings: Decimal,
    horizon_months: int,
) -> tuple[int | None, Literal["ok", "no_savings", "zero_costs", "never_breaks_even"]]:
    if closing_costs == Decimal("0"):
        return 0, "zero_costs"
    if monthly_savings <= Decimal("0"):
        return None, "no_savings"
    months = int((closing_costs / monthly_savings).quantize(Decimal("1"), rounding=ROUND_CEILING))
    if months > horizon_months:
        return None, "never_breaks_even"
    return months, "ok"
```

Or (b) document the divergence explicitly in `RefiBreakeven`'s docstring AND `references/refi-npv.md §5.5` and add a `simple_exceeds_horizon: bool` flag on `RefiBreakeven` so consumers can detect the case programmatically. Option (a) is preferable — the dual-form contract should yield consistent semantics under horizon truncation.

### WR-05: `evaluate_cash_out` docstring claims "remaining" interest but compares full new-schedule total to old-residual total

**File:** `lib/refinance.py:491-493` (RefiResponse field doc); `lib/refinance.py:928-930, 976` (engine + comment)

**Issue:** The `total_interest_delta` field docstring says "new_total_remaining_interest - old_total_remaining_interest". Both terms suggest "interest from refi date forward". The implementation computes `new_schedule.total_interest - old_schedule.total_interest` where:
- `old_schedule.total_interest` is the residual-loan total interest (correct: from refi date forward, since `_build_old_loan_residual` synthesizes a Loan with `principal=balance_remaining, term_months=remaining_months`).
- `new_schedule.total_interest` is the FULL new-loan total interest (lifetime; from refi date forward as t=0 IS the refi origination of the new loan; correct).

So the comparison is internally consistent — both legs are "from refi date forward, over each loan's full remaining/lifetime". The docstring uses "remaining" loosely; a careful reader could reasonably interpret "new_total_remaining_interest" as "new loan's interest remaining at some unspecified later date". Minor doc clarity issue, not a math bug.

**Fix:** Tighten field docstring at line 491-493:

```python
total_interest_delta: Decimal | None = None
"""SC-3: signed Decimal. new_loan total lifetime interest (from refi origination
forward) minus old_loan residual total interest (from refi date forward over
remaining_months). Positive when the cash-out + extension increases lifetime
interest paid (typical for cash-out refis that lengthen the term)."""
```

### WR-06: `analysis_horizon_months` defaulting via `or` is fragile to falsy edge cases

**File:** `lib/refinance.py:847, 979`

**Issue:** Both engine entrypoints default the horizon via `req.analysis_horizon_months or new_loan.term_months`. The Pydantic field constraint `Field(default=None, ge=1, le=600)` precludes `0` as input today, so this is currently safe. But the idiom is brittle — if a future plan relaxes the lower bound to 0 (e.g., to allow "instant breakeven" smoke tests) or someone adds an `int` overload that bypasses the validator, the `or` will silently treat 0 as "use full term" rather than "analysis horizon is zero periods". This is a known Python anti-pattern called out in modern style guides.

**Fix:** Use explicit `is None`:

```python
horizon = (
    req.analysis_horizon_months
    if req.analysis_horizon_months is not None
    else new_loan.term_months
)
```

Or, tersely:

```python
horizon = req.analysis_horizon_months if req.analysis_horizon_months is not None else new_loan.term_months
```

### WR-07: `_validate_common` is invoked redundantly via two layers

**File:** `lib/refinance.py:351-369` (helper); `lib/refinance.py:388-391, 416-419` (callers)

**Issue:** `_validate_common(req)` is called by `RateAndTermRefiRequest._validate_rate_and_term` (line 390) AND `CashOutRefiRequest._validate_cash_out` (line 418). The helper's signature is `_validate_common(req: _CommonRefiFields) -> _CommonRefiFields` — it validates the input and returns it, but neither caller uses the return value (they just call it for side-effect of raising). The model_validator is `mode="after"` and returns `self` after the call, ignoring the helper's return. Functionally fine, but the helper's return-the-validated-instance signature is unused and could mislead future maintainers into chaining the validators differently.

Also: each subclass model has its own `_validate_*` shim that does nothing but call `_validate_common`. The shim pattern adds two methods to the public model surface (Pydantic model_validators are introspectable) without functional benefit.

**Fix:** Make the helper return-`None` and side-effect raise; or hoist the cross-field check directly into a `_CommonRefiFields` model_validator that subclasses inherit. The latter would eliminate both shims entirely:

```python
class _CommonRefiFields(BaseModel):
    # ... existing fields ...
    @model_validator(mode="after")
    def _validate_after_tax_fields_present(self) -> _CommonRefiFields:
        if self.after_tax_mode and (self.marginal_tax_rate is None or self.filing_status is None):
            raise ValueError(
                "after_tax_mode=True requires both marginal_tax_rate and filing_status "
                "(D-09; cites lib.rules.irs_pub936.qualified_loan_limit / RUL-11; "
                "see references/refi-npv.md §'After-Tax Optional Mode')"
            )
        return self
```

Pydantic v2 inherits `model_validator`s through subclassing; this would remove both `_validate_rate_and_term` and `_validate_cash_out` shims and the standalone `_validate_common` helper.

### WR-08: `quantize_rate` is double-applied in helper layer

**File:** `lib/refinance.py:535-541, 549-557` (helpers); `lib/refinance.py:859, 1007` (engine entry quantize)

**Issue:** Both `_build_old_loan_residual` and `_build_new_loan` call `quantize_rate(annual_rate)` on the input. They are called from `evaluate_rate_and_term` / `evaluate_cash_out` with `req.old_annual_rate` / `req.new_annual_rate`, both of which are already Pydantic-validated `Rate` types (max 6 decimals, validated at request boundary). The engine ALSO calls `quantize_rate(req.discount_rate_annual)` at lines 859 and 1007 before storing in `discount_rate`. The discount rate is quantized once (correct boundary), but the loan rates are quantized inside `_build_old_loan_residual` / `_build_new_loan` even though they entered already at-quantum.

Behavior is unchanged (idempotent quantize on already-at-quantum values returns the same value), but the pattern violates "quantize once at the boundary" discipline (CLAUDE.md FND-01 + lib/money.py:39-46). It also slightly inflates Decimal context churn.

**Fix:** Remove the inner quantize_rate calls in `_build_old_loan_residual` / `_build_new_loan`; if defensive quantization is desired, document it explicitly:

```python
def _build_old_loan_residual(
    balance_remaining: Decimal,
    annual_rate: Decimal,  # already at-quantum from Pydantic Rate validation
    remaining_months: int,
) -> Loan:
    return Loan(
        principal=quantize_cents(balance_remaining),
        annual_rate=annual_rate,  # already validated to 6dp by Rate Annotated type
        term_months=remaining_months,
        origination_date=None,
        loan_type="fixed",
    )
```

### WR-09: `assert` statements in production code paths are stripped under `python -O`

**File:** `lib/refinance.py:872-873, 1010-1011`

**Issue:** Both engine entrypoints contain `assert req.marginal_tax_rate is not None` / `assert req.filing_status is not None` after the after-tax-mode branch. The comment correctly states "validator (_validate_common D-09) guarantees both fields present", but these `assert`s are stripped when Python is invoked with `-O` (optimization) — the protection vanishes silently and the `_compute_tax_shield_cashflows` call below proceeds with `marginal_tax_rate=None`, which would raise an obscure `unsupported operand type` from Decimal arithmetic deep inside the helper.

This is mainly a style / robustness concern: production deployments rarely use `-O`, but `pytest -O` and packaging into bytecode-only distributions do. The asserts read more as type-narrowing for mypy than as runtime guards; making the intent explicit is cleaner.

**Fix:** Replace asserts with explicit type narrowing or runtime check that survives `-O`:

```python
if req.after_tax_mode:
    # validator (_validate_common D-09) guarantees both fields present
    if req.marginal_tax_rate is None or req.filing_status is None:
        raise RuntimeError(
            "internal invariant: after_tax_mode=True but tax fields None; "
            "_validate_common should have rejected this construction (D-09)"
        )
    # ... rest of branch
```

Or use `typing.assert_never` with an explicit check; either is mypy-friendly and survives `-O`.

## Info

### IN-01: `from datetime import date` is reserved for unused future use

**File:** `lib/refinance.py:141`

**Issue:** `from datetime import date  # noqa: F401  (reserved for Plan 06-02/06-03 schedule date math)`. Phases 06-02 and 06-03 are now COMPLETE per the project context, and `date` is still unused in the module. The `noqa: F401` lint suppression is preserved for a phase that closed. Either `date` should be removed entirely, or its use should be lit up if Phase 6 actually needs it (it doesn't — `evaluate_*` defers all date math to `build_schedule` via Phase 3 D-12 origination synthesis).

**Fix:** Delete the import:

```python
# REMOVE: from datetime import date  # noqa: F401  (...)
```

### IN-02: `TYPE_CHECKING` block reserves `Sequence` import that is also never used

**File:** `lib/refinance.py:157-158`

**Issue:** Same pattern as IN-01: `from collections.abc import Sequence  # noqa: F401  (reserved for Plan 06-04 dispatcher hints)`. Plan 06-04 is closed and the dispatcher (lines 1068-1097) does not type-hint a Sequence. Dead reservation.

**Fix:** Remove the `if TYPE_CHECKING` block entirely (no other types are reserved there):

```python
# Delete lines 157-158:
# if TYPE_CHECKING:
#     from collections.abc import Sequence  # noqa: F401  (...)
```

### IN-03: Module-level constant `BREAKEVEN_NEVER_SENTINEL` is defined but never referenced

**File:** `lib/refinance.py:169-174`

**Issue:** `BREAKEVEN_NEVER_SENTINEL: Final[None] = None` is defined with elaborate docstring explaining its role, but `grep BREAKEVEN_NEVER_SENTINEL` returns ONLY the definition site — neither `_compute_breakeven_simple` (returns `None` literal at line 686) nor `_compute_breakeven_npv` (returns `None` literal at line 707) uses the sentinel. Either rip it out or replace the `None` literals with `BREAKEVEN_NEVER_SENTINEL` so the docstring's claim is accurate.

**Fix:** Either delete the constant or wire it into both helpers:

```python
# In _compute_breakeven_simple line 686:
return BREAKEVEN_NEVER_SENTINEL, "no_savings"
# In _compute_breakeven_npv line 707:
return BREAKEVEN_NEVER_SENTINEL, "never_breaks_even"
```

### IN-04: `evaluate` dispatcher's "defensive" raise is unreachable through Pydantic

**File:** `lib/refinance.py:1087-1097`

**Issue:** The dispatcher branches on `isinstance(req, RateAndTermRefiRequest)` then `isinstance(req, CashOutRefiRequest)` then raises `ValueError("Unknown RefiRequest variant: ...")`. The discriminated union `RefiRequest` is `Annotated[RateAndTermRefiRequest | CashOutRefiRequest, Field(discriminator="refi_kind")]` — Pydantic guarantees the dispatched instance is one of these two types. The defensive raise is a fail-loud pattern which is fine, but the fallback message references "subclasses _CommonRefiFields directly" as the failure mode — that is an incomplete enumeration of how a caller could end up here (a third subclass also inheriting `_CommonRefiFields` would skip the discriminator entirely). Minor.

**Fix:** Rephrase the docstring to emphasize the discriminator contract rather than the (one of several possible) bypass paths:

```python
raise TypeError(
    f"Unhandled RefiRequest variant: {type(req).__name__!r}. "
    f"RefiRequest is a Pydantic discriminated union over refi_kind; only "
    f"RateAndTermRefiRequest and CashOutRefiRequest are valid runtime types. "
    f"Construct via TypeAdapter(RefiRequest).validate_*()."
)
```

(`TypeError` is also slightly more correct than `ValueError` for "you passed the wrong type".)

### IN-05: `references/refi-npv.md` lists a `_build_cashflow_stream` helper that ships under a different name

**File:** `references/refi-npv.md:127`

**Issue:** §2 "Helper layer" table cites `_build_cashflow_stream(...)` as the cashflow-builder helper name. The actual implementation in `lib/refinance.py:560` is named `_build_refi_cashflows`. Documentation drift between the contract and the engine.

Same line of the table also says `_compute_npv(discount_rate_annual, cashflows)` — the actual signature is `_compute_npv(discount_rate_annual, cashflows, horizon_months)`. The horizon parameter is omitted in the doc.

**Fix:** Update `references/refi-npv.md:122-130` to mirror the actual function names and signatures:

```
| Helper | Purpose |
|---|---|
| `_compute_npv(discount_rate_annual, cashflows, horizon_months)` | Wraps `npf.npv` with Decimal discipline; quantizes only at boundary |
| `_build_refi_cashflows(*, closing_costs, old_monthly_pi, new_monthly_pi, horizon_months, cash_proceeds_net)` | Constructs the `list[RefiCashflow]` stream from request inputs; honors `analysis_horizon_months` truncation |
| `_build_old_loan_residual(balance_remaining, annual_rate, remaining_months)` | Synthesizes a Loan representing the OLD loan's remaining balance + remaining term |
| `_compute_breakeven_simple(closing_costs, monthly_savings)` | Simple breakeven (REFI-03); returns `(months: int|None, status: Literal[...])` |
| `_compute_breakeven_npv(discount_rate_annual, cashflows, horizon_months)` | Cumulative-NPV scan (D-06; NOT npf.irr — bug #131) |
```

---

_Reviewed: 2026-05-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
