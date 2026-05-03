---
phase: 05-arm-modeling
reviewed: 2026-05-02T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - lib/affordability.py
  - lib/arm.py
  - lib/money.py
  - references/arm-mechanics.md
  - scripts/_cli_helpers.py
  - scripts/affordability.py
  - scripts/amortize.py
  - scripts/arm_simulate.py
  - tests/fixtures/arm/oracle/abt_bank_5_6_sofr_disclosure_2022.json
  - tests/test_arm.py
  - tests/test_cli_helpers.py
  - tests/test_money.py
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
status: issues_found
---

# Phase 5: ARM Modeling — Code Review Report

**Reviewed:** 2026-05-02
**Depth:** standard
**Files Reviewed:** 11 (plus PDF binary verified by SHA256 only)
**Status:** issues_found

## Summary

The ARM engine is well-structured: parallel `ARMSchedule`/`ARMPayment` models, per-epoch slice-stitch over `lib.amortize.build_schedule`, full `Decimal` discipline (no float contamination found), proper `quantize_rate`/`quantize_cents` end-of-period quantization, and uniform 6-key Pydantic envelope at the CLI boundary. The core math (`_compute_new_rate` clamp + classifier) is correct for the documented test scenarios, and `_compute_reset_triggers` cleanly implements the +1 off-by-one. The `lib/affordability.py` change is a minimal refactor swapping a private `_quantize_rate` to the promoted `lib.money.quantize_rate` — clean.

However, the review surfaces five WARNING-level defects: a real correctness bug for the `loan.origination_date is None` path that produces nonsensical `payment_date` values across epochs; missing `ARMRequest` validation for duplicate `index_path` periods (silent first-wins instead of "fail loud"); missing `ARMTerms` cross-field guard against `floor_rate` exceeding `note_rate + lifetime_cap` (degenerate config silently warps classifier output); three fixture files committed but never bound to a named test (weak coverage); and an unbounded recursion in `find_json_float_loc` reachable from a malformed-but-valid JSON input. INFO-level items cover representation drift on `rate_in_effect` for epoch 0 and a few minor docstring/comment issues.

No BLOCKER findings: the bugs identified do not corrupt the load-bearing rate/balance math when `origination_date` is supplied, and the test suite covers the documented scenarios. Address the five warnings before Phase 8 stress consumes `ARMSchedule.payments[i].payment_date`.

## Warnings

### WR-01: Per-epoch payment_date is wrong when loan.origination_date is None

**File:** `lib/arm.py:402-404`
**Issue:** Inside the per-epoch slice-stitch loop, `build_arm_schedule` builds an `ARMPayment` with:

```python
payment_date=loan.origination_date + relativedelta(months=absolute_period)
if loan.origination_date is not None
else p.payment_date,
```

When `loan.origination_date is None`, the engine reuses `p.payment_date` from the **synthetic** epoch schedule. Each per-epoch synthetic Loan also receives `origination_date=loan.origination_date` (line 381), which is `None`, so `lib.amortize._build_fixed_monthly` synthesizes its own origination via `datetime.now(UTC).date()` (`lib/amortize.py:278`). The synthetic's payments have `period=1, 2, 3, ...` relative to that synthesized origination — so the first payment of epoch 1 (`absolute_period=61`) carries `payment_date = today + 1 month`, **not** `today + 61 months`. Across multiple epochs, every epoch's first payment is approximately `today + 1 month`, producing a non-monotonic, duplicated-date `payment_date` sequence. Two independent synthetic builds may also straddle midnight and use different "today" values.

The CLI test exercises only `origination_date=date(2026, 1, 1)`, so this defect is not caught by `tests/test_arm.py`. Phase 8 stress (which iterates `ARMSchedule.payments[i].payment_date` for cash-flow simulations) will see broken dates if any caller omits `origination_date`.

**Fix:** Synthesize a single origination date once per `build_arm_schedule` call and offset every per-epoch row from that anchor:

```python
# Near top of build_arm_schedule (after the `loan = req.loan` line):
from datetime import datetime, UTC
origination_anchor = loan.origination_date or datetime.now(UTC).date()

# Replace lines 402-404 with:
payment_date=origination_anchor + relativedelta(months=absolute_period),
```

This mirrors `lib.amortize._build_fixed_monthly`'s D-12 idiom and removes the multi-call drift.

---

### WR-02: ARMRequest does not reject duplicate index_path periods

**File:** `lib/arm.py:106-134` (model_validator) and `lib/arm.py:259-264` (consumer)
**Issue:** `_index_path_periods_align_to_reset_triggers` validates that every `IndexPathEntry.period` matches a reset trigger, but it does NOT detect duplicates. A request like:

```json
"index_path": [
  {"period": 61, "value": "0.0500"},
  {"period": 61, "value": "0.1000"}
]
```

is accepted. Inside `_compute_new_rate`, the for-loop returns the **first** match and `break`s (lines 261-264), silently ignoring the second entry. This violates the project's "fail loud, no inference" doctrine (CLAUDE.md money discipline + CONTEXT.md D-01). A user who accidentally double-specifies a reset value will see a different rate path with no warning.

**Fix:** Extend `_index_path_periods_align_to_reset_triggers` to reject duplicates:

```python
seen_periods: set[int] = set()
for entry in self.index_path:
    if entry.period not in triggers:
        # ... existing alignment check ...
    if entry.period in seen_periods:
        raise ValueError(
            f"index_path contains duplicate entries for period {entry.period} "
            f"(D-01: each reset trigger may appear at most once)"
        )
    seen_periods.add(entry.period)
return self
```

Add a regression test in `tests/test_arm.py` mirroring `test_arm_request_misaligned_index_path_raises`.

---

### WR-03: ARMTerms accepts floor_rate > lifetime ceiling without cross-field validation

**File:** `lib/arm.py:27-66` (ARMTerms model)
**Issue:** `ARMTerms` field validators bound `floor_rate` to `[0, 1]` and `lifetime_cap_bps` to `[0, 2000]`, but no model_validator checks that the floor is reachable. If a caller supplies `floor_rate=Decimal("0.20")`, `note_rate=Decimal("0.05")`, `lifetime_cap_bps=500` (lifetime ceiling = 0.10), then for any reset:

- `effective_floor = max(margin/10000, 0.20) = 0.20`
- `ceiling = min(periodic, lifetime) <= 0.10`
- `clamped = max(0.20, min(fully_indexed, 0.10)) = 0.20`
- `new_rate = 0.20`

The lifetime cap is silently violated (rate exceeds it), and the classifier at `lib/arm.py:294` reports `applied_cap="floor"` if `0.20 > fully_indexed_q` — but a downstream consumer reading `applied_cap` cannot detect that `lifetime_ceiling` was breached. This is a configuration error class that should be caught at request construction, not silently propagated.

`note_rate` is optional (collapses to `loan.annual_rate` per D-02), so the cross-field check would need to run inside `ARMRequest` (which has access to `loan.annual_rate`) rather than `ARMTerms`.

**Fix:** Add an `ARMRequest` model_validator:

```python
@model_validator(mode="after")
def _floor_does_not_exceed_lifetime_ceiling(self) -> ARMRequest:
    note_rate_eff = self.arm_terms.note_rate or self.loan.annual_rate
    lifetime_ceiling = note_rate_eff + Decimal(self.arm_terms.lifetime_cap_bps) / Decimal("10000")
    margin_rate = Decimal(self.arm_terms.margin_bps) / Decimal("10000")
    effective_floor = max(margin_rate, self.arm_terms.floor_rate)
    if effective_floor > lifetime_ceiling:
        raise ValueError(
            f"effective_floor ({effective_floor}) exceeds lifetime_ceiling "
            f"({lifetime_ceiling}); this would force every reset to violate "
            f"the lifetime cap (D-02 invariant)."
        )
    return self
```

---

### WR-04: Three ARM fixtures are not bound to a named test

**File:** `tests/fixtures/arm/arm_continuous_period_numbering.json`, `tests/fixtures/arm/arm_index_path_overrides.json`, `tests/fixtures/arm/arm_teaser_rate.json`
**Issue:** `tests/test_arm.py` references named fixtures by string at 9 sites (grep `arm_fixture("...")`), but three committed fixtures have no matching call:

- `arm_continuous_period_numbering.json` — `test_arm_continuous_period_numbering` (line 591) builds its request via `_make_5_1_arm_request()` instead of loading this fixture.
- `arm_index_path_overrides.json` — no test loads this fixture; the only `index_path` override coverage is in CLI envelope tests using a misaligned period (which is rejected, never executed).
- `arm_teaser_rate.json` — `test_arm_teaser_rate` (line 1290) constructs the request inline via `_make_5_1_arm_request(...)` instead of loading this fixture.

These fixtures are scanned by `test_applied_cap_citation_coverage` only for `applied_cap` distribution, providing no per-payment / per-reset assertion. If a fixture's hand-calc drifts away from engine output, no test fails. This weakens the D-04 / D-09 hand-calc-vs-engine cross-validation contract. Particularly concerning: `arm_index_path_overrides.json` is meant to lock D-01 override-wins semantics; without a binding test, the override path's correctness is implicit only.

**Fix:** Either (a) wire each fixture into its corresponding test (rewrite `test_arm_continuous_period_numbering`, `test_arm_teaser_rate`, and add `test_arm_index_path_overrides`), or (b) delete the unreferenced fixtures and document the inline-construction choice in CONTEXT.md. Option (a) is preferred — it preserves the hand-calc cross-validation contract.

---

### WR-05: find_json_float_loc has unbounded recursion on deeply nested JSON

**File:** `scripts/_cli_helpers.py:47-62`
**Issue:** The `_walk` inner function recursively descends through JSON objects/arrays without a depth limit. A pathological input with >1000 levels of nesting (Python's default `sys.getrecursionlimit()`) raises `RecursionError`, which is not caught. Pydantic itself can handle deep JSON via iterative parsing, but the project's own pre-validation gate cannot. While untrusted external input is not the threat model here (the user runs the CLI on their own machine), a malformed input file from a user-driven workflow can crash the CLI with an opaque traceback instead of the documented `{"error": ...}` envelope.

**Fix:** Convert the walker to an iterative stack:

```python
def _walk(root: Any) -> tuple[list[str | int], str] | None:
    stack: list[tuple[Any, list[str | int]]] = [(root, [])]
    while stack:
        node, path = stack.pop()
        if isinstance(node, _Decimal):
            return (path, str(node))
        if isinstance(node, dict):
            for k, v in node.items():
                stack.append((v, [*path, k]))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                stack.append((v, [*path, i]))
    return None
```

Note: stack-based traversal flips iteration order versus the recursive version. The test `test_multiple_floats_returns_first_depth_first` asserts the FIRST float in dict-insertion order is returned — preserve that semantic by reversing inserts (`for k, v in reversed(list(node.items())):` etc.) so that LIFO pop order matches recursive descent.

---

## Info

### IN-01: ARMPayment.rate_in_effect not quantize_rate'd in epoch 0

**File:** `lib/arm.py:351, 365, 412`
**Issue:** `current_rate` for epoch 0 is set directly from `loan.annual_rate` (line 365), which is a Pydantic `Rate` field but is not auto-quantized to 6 decimal places by Pydantic. If a user supplies `Decimal("0.065")`, every epoch-0 `ARMPayment.rate_in_effect` carries `Decimal("0.065")`, while subsequent epochs' `rate_in_effect` are quantized to 6 places (e.g., `Decimal("0.077500")`). Downstream consumers that use `==` get correct results, but consumers using `.as_tuple()` or `str()` see inconsistent representations across epoch boundaries. The ARMTerms `note_rate` field has the same issue at lines 276-277.

**Fix:** Quantize once at the entry point:
```python
current_rate = quantize_rate(loan.annual_rate)
prior_rate = quantize_rate(loan.annual_rate)
```
And in `_compute_new_rate`:
```python
note_rate_eff = quantize_rate(terms.note_rate if terms.note_rate is not None else loan_annual_rate)
```

---

### IN-02: index_value_used in ResetEvent is not quantized

**File:** `lib/arm.py:260-264, 306` (return value), `lib/arm.py:152-177` (ResetEvent)
**Issue:** `index_value_used` is returned from `_compute_new_rate` as the raw `req.assumed_index_rate` or `entry.value`. ResetEvent's `index_value_used: Rate` field accepts whatever digits the caller supplied. A user providing `Decimal("0.0525")` (4 places) yields `index_value_used = Decimal("0.0525")` while engine-computed rates use 6 places. Same representation drift as IN-01.

**Fix:** Wrap with `quantize_rate(index_value)` at the return.

---

### IN-03: model_validator boundary diagnostic truncates trigger list

**File:** `lib/arm.py:127-133`
**Issue:** When index_path period is misaligned, the error sample is the first 5 triggers + ellipsis. For a 5/6 ARM (50 triggers) or a long-term ARM, callers see only `[61, 67, 73, 79, 85]...` with no hint of whether `period=349` was actually invalid. The `f"{sample}{suffix}"` formatting also produces awkward `[61, 67, 73, 79, 85]...` (list repr followed by string `...`).

**Fix:** Include the term-month upper bound and the cadence so users can compute valid periods themselves:
```python
raise ValueError(
    f"index_path entry at period {entry.period} does not align to a reset trigger period (D-01). "
    f"Triggers for this product: every {cadence} months starting at month {initial + 1}, "
    f"up to month {term}. First five: {sample}"
)
```

---

### IN-04: scripts/arm_simulate.py argparse description duplicates --help epilog

**File:** `scripts/arm_simulate.py:33-52`
**Issue:** The argparse `description` and `epilog` both narrate input shape; in particular, `description` says "JSON-in / JSON-out per Phase 5 D-07" while the epilog includes another `Input JSON shape (D-01 + D-06)` block. Mostly cosmetic, but `--help` output is repetitive.

**Fix:** Trim the description to one line; keep the epilog as the single shape reference (consistent with `scripts/affordability.py:74-123` style).

---

### IN-05: Magic number 2000 (sanity rail) appears in three ARMTerms field bounds

**File:** `lib/arm.py:47, 50, 53, 59`
**Issue:** `Field(ge=0, le=2000)` repeats four times for cap/margin bps fields. The 20 percentage-point rail is a project sanity convention, not a regulatory limit. A `MAX_CAP_BPS = 2000` module-level Final constant with a one-line citation comment would make the rail discoverable when someone reads only the ARMTerms class. Also makes future tightening (e.g., to 1500 once you've researched real-world ARMs) a one-line edit.

**Fix:**
```python
_MAX_CAP_BPS: Final[int] = 2000  # 20pp sanity rail; not regulatory (CONTEXT.md D-06)

class ARMTerms(BaseModel):
    initial_cap_bps: int = Field(ge=0, le=_MAX_CAP_BPS)
    # ...
```

---

### IN-06: Inline comment refers to wrong file path

**File:** `lib/arm.py:146-148`
**Issue:** `ARMPayment` docstring says "Pydantic v2 model_config IS auto-inherited from Payment per RESEARCH LM-4". The RESEARCH file is `.planning/phases/05-arm-modeling/05-RESEARCH.md`, but the comment doesn't qualify the path. A future reader running grep on "RESEARCH LM-4" project-wide will find references in multiple phases. Low-risk traceability nit.

**Fix:** Cite the canonical path: `"per .planning/phases/05-arm-modeling/05-RESEARCH.md LM-4"`.

---

### IN-07: test_oracle_cross_validation_5_1 is a strict-xfail pytest.fail

**File:** `tests/test_arm.py:710-724`
**Issue:** The Bankrate/Vertex42 cross-oracle test is decorated `@pytest.mark.xfail(strict=True, ...)` and its body is `pytest.fail(...)`. With `strict=True`, an XPASS (test unexpectedly passing) raises an error — but `pytest.fail` always fails, so the strict-xfail is effectively a forced-XFAIL. The test will silently keep "failing" (XFAIL) forever until someone manually drops the decorator. There's no automatic reminder when the captures land. Acceptable per Phase 5 plan (deferred to Phase 8+), but worth noting that the `strict=True` is doing nothing useful here.

**Fix:** Either (a) drop `strict=True` since it cannot trigger, or (b) replace with `@pytest.mark.skip(reason=...)` to communicate "not yet implemented" rather than "expected to fail." Option (b) is a clearer signal.

---

_Reviewed: 2026-05-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
