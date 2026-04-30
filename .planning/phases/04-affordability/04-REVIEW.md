---
phase: 04-affordability
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - lib/affordability.py
  - scripts/affordability.py
  - config/household.example.yml
  - tests/conftest.py
  - tests/test_affordability.py
  - tests/fixtures/affordability/forward_conventional_80_ltv.json
  - tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json
  - tests/fixtures/affordability/forward_fha_above_dti_cap.json
  - tests/fixtures/affordability/forward_jumbo_above_county_limit.json
  - tests/fixtures/affordability/forward_missing_county_data.json
  - tests/fixtures/affordability/forward_va_residual_fail.json
  - tests/fixtures/affordability/household_example_yml_e2e.json
  - tests/fixtures/affordability/joint_applicants_two_incomes.json
  - tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json
  - tests/fixtures/affordability/single_applicant.json
findings:
  critical: 2
  warning: 8
  info: 5
  total: 15
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-30T00:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 4 ships a substantial Pydantic v2 affordability surface (forward + reverse modes), a CLI entrypoint, and a comprehensive test suite (~1650 lines). The architecture follows the documented project conventions well: Decimal money discipline, frozen Pydantic models with strict mode, predicate-style rule integration, and the Phase 3 D-19 6-key envelope contract.

However, the review identified two correctness/contract defects that should be addressed before this code ships, plus several quality issues that complicate maintenance. The most concerning issues are:

1. **Reverse-mode round-trip closure violates D-09 contract for FHA target** — UFMIP financing is intentionally skipped in reverse mode (per code comment) but `_compute_monthly_mi` still uses `zero_mi_loan_amount` as the financed amount in the FHA branch's `fha_mip.compute()` call, which then re-invokes UFMIP financing logic against an unfinanced principal. Combined with the fact that no fixture exercises FHA reverse mode, this is untested behavior.
2. **`_compute_monthly_mi` performs redundant FHA MIP computation** in `evaluate_forward` — the FHA branch is computed twice (once inline at lines 866-879 to get UFMIP, then again inside `_compute_monthly_mi` at lines 766-772 against the same financed loan). This is a quality/maintenance issue but produces correct results today.
3. **Sign-convention deviation in `evaluate_reverse`** is documented inline but contradicts the locked decision D-08 and the module's own RESEARCH-derived pseudocode. The runtime divergence ("library already inverts internally") is plausible but pinned only by the round-trip closure assertion. If the round-trip test is ever skipped or weakened, this becomes a silent sign-flip bug.

## Critical Issues

### CR-01: `_validate_common` — `origination_ltv` undefined when `req` is neither subtype

**File:** `lib/affordability.py:479-492`
**Issue:** The conventional-PMI conditional uses an `if/elif` ladder with no `else` setting `origination_ltv`. The `else` branch returns early (`return req`), which means if a future subclass is added, the variable is never set. Today the discriminated union only has Forward/Reverse, but the comment `# pragma: no cover — defensive` suggests the author knew this was fragile. The current code happens to work because both branches set the variable. However, the structure is brittle: a future ReverseModeRequest subclass would silently bypass the PMI check.

More importantly, **`isinstance(req, ForwardModeRequest)` and `isinstance(req, ReverseModeRequest)` are evaluated at runtime against forward references** — `_validate_common` is defined at line 458 BEFORE `ForwardModeRequest` (line 496) and `ReverseModeRequest` (line 513). Python resolves these names at call time via the module's global scope, so this works, but the order is non-obvious and breaks `from __future__ import annotations` semantics that suggest names should be resolvable at definition time. This makes the file harder to refactor (e.g., extracting the validator to a separate module).

**Fix:** Move `_validate_common` AFTER `ForwardModeRequest`/`ReverseModeRequest` definitions, or replace `isinstance` with a check on `req.mode`:

```python
def _validate_common(req: _CommonRequestFields) -> Any:
    # ... existing va + apr/apor checks ...
    if req.target_loan_type == "conventional":
        if req.mode == "forward":
            origination_ltv = req.loan_amount / req.property_value
        else:  # mode == "reverse"
            origination_ltv = req.target_ltv_pct
        if origination_ltv > LTV_REQUEST_ELIGIBLE and req.monthly_pmi is None:
            raise ValueError(...)
    return req
```

### CR-02: Reverse-mode FHA MIP estimation uses unfinanced principal — silent under-estimation

**File:** `lib/affordability.py:1066-1090`
**Issue:** In `evaluate_reverse`, the zero-MI seed solve produces `zero_mi_loan_amount`. This is then passed to `_compute_monthly_mi` as `financed_loan_amount`. But `_compute_monthly_mi`'s FHA branch (line 757-772) treats its `financed_loan_amount` parameter as already-financed (i.e., loan_amount + UFMIP) and computes monthly MIP against it. In reverse mode, `zero_mi_loan_amount` is NOT financed — there is no UFMIP add-on per the inline comment "Reverse mode does NOT auto-finance UFMIP" (lines 1025-1031). 

This means for FHA reverse-mode requests, the monthly MIP estimate is too LOW (computed against unfinanced principal). This propagates to `max_pi`, then to `npf.pv`, producing a `max_loan_amount` that is too HIGH (the household's "max" is over-stated because actual PITI in forward mode would include MIP on the financed principal, which is higher).

**No fixture exercises FHA reverse mode**, so this is currently untested. The round-trip closure assertion (`forward(reverse).dti_back <= max_dti + 0.0001`) would catch it for FHA — but only if a fixture exercises it.

**Fix:** Add an FHA reverse-mode fixture and assert the round-trip closure. If it fails, either:
1. Auto-finance UFMIP in reverse mode (breaks D-08 one-shot premise per code comment), or
2. Adjust `_compute_monthly_mi` to take an explicit `is_financed: bool` parameter, or
3. Document that FHA reverse mode is unsupported and raise at validator time.

```python
# In _validate_common or evaluate_reverse:
if isinstance(req, ReverseModeRequest) and req.target_loan_type == "fha":
    raise ValueError(
        "FHA reverse mode is not supported in v1 — UFMIP financing breaks "
        "the D-08 one-shot LTV-pinning premise; use forward mode with "
        "pre-financed loan_amount instead"
    )
```

## Warnings

### WR-01: `evaluate_forward` performs redundant FHA MIP computation

**File:** `lib/affordability.py:866-904`
**Issue:** The FHA branch is computed twice. Lines 866-879 build a Loan with `principal=request.loan_amount` and call `fha_mip_compute` to get `pre_mip.ufmip`. Then line 881 builds `financed_loan_amount = loan_amount + ufmip`. Then lines 896-904 call `_compute_monthly_mi(target_loan_type='fha', financed_loan_amount=...)`, which (lines 757-772) builds a NEW Loan with `principal=financed_loan_amount` and calls `fha_mip_compute` AGAIN. Two YAML loads, two predicate calls, two warnings emitted (the StaleReferenceWarning is emitted on each load — though deduplicated by `simplefilter("always", ...)` semantics, the captured list may still contain duplicates depending on the filter implementation).

**Fix:** Refactor to compute UFMIP and monthly MIP in a single pass:

```python
if request.target_loan_type == "fha":
    pre_mip = fha_mip_compute(loan=pre_finance_loan, ...)
    ufmip_to_finance = pre_mip.ufmip
    financed_loan_amount = quantize_cents(request.loan_amount + ufmip_to_finance)
    # Compute monthly_mi against the FINANCED amount using the SAME annual_mip_pct
    monthly_mi = quantize_cents((financed_loan_amount * pre_mip.annual_mip_pct) / Decimal("12"))
else:
    financed_loan_amount = request.loan_amount
    monthly_mi, _ = _compute_monthly_mi(...)  # non-FHA branch
```

Note that the current code computes monthly_mip against `financed_loan_amount` while `pre_mip.annual_mip_pct` came from a Loan with `principal=request.loan_amount` (unfinanced). The annual_mip_pct depends on LTV (loan / property_value), so the two computations may produce DIFFERENT annual_mip_pct values — `pre_mip` uses the unfinanced LTV (e.g., 400k/425k = 0.941), while the second call uses the financed LTV (407k/425k = 0.957). For the `forward_fha_above_dti_cap` fixture, both LTVs map to the same MIP table cell, so the result is correct, but this is a correctness landmine if the LTV crosses a HUD MIP-table boundary.

### WR-02: Sign-convention deviation pinned only by round-trip closure assertion

**File:** `lib/affordability.py:1102-1117`
**Issue:** RESEARCH §"Sign conventions" prescribes `max_loan_amount = quantize_cents(-raw_pv)` but the code uses `quantize_cents(raw_pv)` based on empirically observed numpy_financial 1.0.0 behavior. The inline comment acknowledges the deviation:

> "Empirically numpy_financial 1.0.0 returns POSITIVE pv when pmt is NEGATIVE — the library already inverts internally — so the additional negation prescribed by RESEARCH would yield a NEGATIVE max_loan_amount that fails Pydantic's Money ge=0 constraint"

This is a known bug pattern (`numpy_financial` issue #130 referenced in CLAUDE.md). The deviation is pinned by `test_AFFD_05_reverse_round_trip` — but if that test is weakened (e.g., property_value rounding changes break exact equality), the sign flip becomes silent.

**Fix:** Add a defensive assertion immediately after `npf.pv`:

```python
raw_pv = npf.pv(rate=monthly_rate, nper=request.term_months, pmt=-max_pi, fv=0)
if raw_pv <= 0:
    raise RuntimeError(
        f"npf.pv returned non-positive value {raw_pv}; numpy_financial "
        f"sign-convention may have changed. See lib/affordability.py L1102-1117 "
        f"for context."
    )
max_loan_amount = quantize_cents(raw_pv)
```

This converts a silent contract violation into a loud failure if numpy_financial's behavior ever changes.

### WR-03: `evaluate_reverse` does not check `max_pi` is positive — silent producer of invalid loans

**File:** `lib/affordability.py:1090-1100`
**Issue:** `max_pi = max_pi_plus_mi - assumed_monthly_mi` can be negative or zero if (a) `max_dti * income < monthly_debts` or (b) escrow + MI consumes the entire DTI budget. When `max_pi <= 0`, `npf.pv(pmt=-max_pi, ...)` returns a non-positive or negative value. The downstream `quantize_cents(raw_pv)` may emit a value that fails Pydantic's `Money` field validation (`ge=0`) at response construction — but the error site is far from the cause, making debugging hard.

**Fix:** Validate at the source:

```python
max_piti = request.max_dti * total_gross_monthly_income - sum_monthly_debts
if max_piti <= 0:
    raise ValueError(
        f"Household income/debt structure has zero/negative PITI capacity: "
        f"max_dti={request.max_dti}, income={total_gross_monthly_income}, "
        f"debts={sum_monthly_debts}; reverse-mode max_loan_amount is undefined"
    )
# similar check after subtracting escrow/MI
```

### WR-04: `_validate_common` is called inside `@model_validator(mode="after")` but ignores its return value side-effects

**File:** `lib/affordability.py:507-528`
**Issue:** `_validate_common` returns `req` but the callers (`_validate_forward`, `_validate_reverse`) call it for side-effects (raising `ValueError`) and ignore the returned value, then return `self`. This is harmless today but subtly wrong: if `_validate_common` ever needs to MUTATE the request (it can't because models are frozen), the mutation would be silently dropped.

**Fix:** Change `_validate_common` to return `None` and document that it raises on validation failure:

```python
def _validate_common(req: _CommonRequestFields) -> None:
    """Cross-field validators... Raises ValueError on validation failure."""
    # ... existing checks; remove the `return req` lines ...
```

### WR-05: `MonthlyDebts` field defaults use mutable Decimal class attributes

**File:** `lib/affordability.py:368-375`
**Issue:** While `Decimal` instances are immutable so this is not a "mutable default" bug in the classical Python sense, the pattern of using `Decimal("0.00")` as a Pydantic field default is correct. However, the field is declared as `Money = Decimal("0.00")`. `Money` is `Annotated[Decimal, Field(...)]` with constraints — using the bare `Decimal("0.00")` as the default bypasses the Pydantic validation pipeline for the default value. If `Money` ever adds e.g. a `gt=0` constraint, the `0.00` defaults would fail to round-trip via `model_dump → model_validate`.

**Fix:** Use `Field(default=Decimal("0.00"))` to make the validation path explicit:

```python
auto: Money = Field(default=Decimal("0.00"))
student_loans: Money = Field(default=Decimal("0.00"))
# etc.
```

### WR-06: `_compute_monthly_mi` for `target_loan_type=="fha"` issues StaleReferenceWarning twice in `evaluate_forward`

**File:** `lib/affordability.py:866-904, 757-772`
**Issue:** Connected to WR-01. Each call to `fha_mip_compute` triggers a YAML load that emits a `StaleReferenceWarning` (per the docstring at line 165-171). The captured warnings list in `evaluate_forward` will contain DUPLICATE stale-warning strings for FHA forward-mode requests. The fixture `forward_fha_above_dti_cap.json` shows only ONE stale warning in `expected_response.warnings`, suggesting either:
1. The duplicate is silently de-duplicated somewhere (pytest's warning filter behavior), or
2. The expected fixture is incorrect.

If the test passes today, the de-duplication is implicit (e.g., Python's warning-registry de-duplicates identical warnings within `simplefilter("always", ...)` for the same source location). This is fragile.

**Fix:** De-duplicate captured_warnings explicitly before appending to the response:

```python
seen: set[str] = set()
unique_warnings = []
for w_str in captured_warnings:
    if w_str not in seen:
        seen.add(w_str)
        unique_warnings.append(w_str)
captured_warnings = unique_warnings
```

Alternatively, fix WR-01 (single MIP compute) which eliminates the duplicate at the source.

### WR-07: Test grep gate for VA citation construction is permeable

**File:** `tests/test_affordability.py:1114-1127`
**Issue:** The negative-grep test asserts `'f"VA-RESIDUAL-' not in source`. But:
1. It only matches double-quoted f-strings. A future contributor using single-quoted f-strings (`f'VA-RESIDUAL-...'`) bypasses the gate. (Line 397 of lib/affordability.py contains this exact pattern in a docstring — it's documentation, not code, but illustrates the false-negative risk.)
2. It only checks for the literal substring `f"VA-RESIDUAL-` — a contributor using `.format("VA-RESIDUAL-{REGION}-...", ...)` or string concatenation also bypasses the gate.

**Fix:** Strengthen the grep with multiple patterns and use AST analysis where possible:

```python
forbidden_patterns = [
    'f"VA-RESIDUAL-',
    "f'VA-RESIDUAL-",
    '"VA-RESIDUAL-{',
    "'VA-RESIDUAL-{",
    '"VA-RESIDUAL-".format',
]
for pattern in forbidden_patterns:
    assert pattern not in source, (
        f"Phase 4 must NEVER construct VA-residual citations; "
        f"found forbidden pattern {pattern!r} in lib/affordability.py"
    )
```

### WR-08: `evaluate_reverse` does not validate `target_ltv_pct > 0`

**File:** `lib/affordability.py:1073, 1121`
**Issue:** `target_ltv_pct` is a `Rate` field; Pydantic constrains decimal_places=6 and max_digits=7 but does not enforce `gt=0`. A caller supplying `target_ltv_pct=Decimal("0.000000")` would cause divide-by-zero on line 1073: `quantize_cents(zero_mi_loan_amount / request.target_ltv_pct)` and again on line 1121. Result: `decimal.DivisionByZero` exception not caught at the script boundary.

**Fix:** Add a Field constraint or model_validator:

```python
class ReverseModeRequest(_CommonRequestFields):
    target_ltv_pct: Rate = Field(gt=Decimal("0"), le=Decimal("1.0"))
```

(Note that `Rate` already constrains decimal_places, but does not appear to constrain `gt=0` based on the surrounding code.)

## Info

### IN-01: `current_housing_payment` field defined but never consumed

**File:** `lib/affordability.py:433`
**Issue:** `Household.current_housing_payment: Money = Decimal("0.00")` is defined but never read anywhere in lib/affordability.py. The docstring at line 67-69 of `config/household.example.yml` says "reserved for Phase 8 stress-test". This is acceptable per the documented deferral, but:
- The field has no explicit constraint that it's currently unused
- A future reviewer may waste time tracing dead code

**Fix:** Add a `# Phase 8 reserved` comment on the field declaration, or move to an explicit `Reserved` block in the docstring.

### IN-02: `_RATE_QUANTUM` is module-private but `_quantize_rate` is the public-ish helper

**File:** `lib/affordability.py:613-627`
**Issue:** Both are underscore-prefixed (private) but they're foundational enough that a Phase 4 consumer (Phase 8 stress, Phase 9 orchestration) might want to reuse the rate-quantization discipline. Today they're duplicated across plans; consider exposing them via the public surface.

**Fix:** Rename to `RATE_QUANTUM` and `quantize_rate` (drop underscore prefix) and add to module-public exports.

### IN-03: Discriminated-union narrowing comment claims compile-time impossibility but runtime check exists

**File:** `lib/affordability.py:484-485`
**Issue:** The comment `# pragma: no cover — defensive; req must be one of the two subtypes` indicates the author considers the branch unreachable. If unreachable, the `return req` is dead code. If reachable, the test coverage is missing. Either remove the branch (let `origination_ltv` raise `UnboundLocalError` for unknown types) or add a test that exercises it via a custom subclass.

**Fix:** Remove the dead `else` branch and let `origination_ltv` raise loudly:

```python
if isinstance(req, ForwardModeRequest):
    origination_ltv = req.loan_amount / req.property_value
elif isinstance(req, ReverseModeRequest):
    origination_ltv = req.target_ltv_pct
else:
    raise TypeError(f"unexpected request type: {type(req).__name__}")
```

### IN-04: `_ = derived_property_value` discard pattern is non-idiomatic

**File:** `lib/affordability.py:1143`
**Issue:** The line `_ = derived_property_value  # documentation: intentional non-export` is unnecessary. The variable IS used at line 1126 (passed implicitly via the `loan_amount` arg of `_classify_target_loan_type`)... wait, looking again: at line 1121 `derived_property_value` is computed, but the only subsequent use is line 1143 (the discard). It's NOT passed to `_classify_target_loan_type` (line 1126 passes `loan_amount=max_loan_amount`, not derived_property_value). So `derived_property_value` is genuinely unused after computation — the comment claims it "feeds the classify call site" but that's wrong; the classify call uses `max_loan_amount`. Either the variable is dead code (delete it) or the classify call should use it.

**Fix:** Delete the unused variable and the discard:

```python
# Remove lines 1119-1121 (the comment + derived_property_value computation)
# Remove line 1143 (the discard)
```

If the classify call SHOULD use `derived_property_value` per the original design, that's a different bug — verify against RESEARCH §"reverse pseudocode".

### IN-05: Test fixtures duplicate `extra="forbid"` boundary fields explicitly

**File:** `tests/fixtures/affordability/*.json`
**Issue:** Every fixture explicitly sets fields like `"va": null`, `"apr": null`, `"apor": null`, `"monthly_pmi": null`, `"endorsement_date_override": null`, `"junior_liens": []`. Since the Pydantic models have defaults for all of these, the fixtures could omit them. The current pattern is verbose but defensible (explicit > implicit at boundary contracts) — keeping it for traceability is fine. However, note that 9 fixtures × ~6 default fields each = ~54 lines of redundant JSON, which inflates the diff for any future schema change.

**Fix:** None required — flag for awareness. If schema evolves, batch-update fixtures via a script rather than hand-editing.

---

_Reviewed: 2026-04-30T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
