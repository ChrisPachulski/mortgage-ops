---
phase: 07
plan: 01
type: execute
wave: 1
depends_on: ["07-00"]
files_modified:
  - lib/apr.py
autonomous: true
requirements: [APR-01]
tags:
  - phase-07
  - estimated-apr
  - pydantic-models
must_haves:
  truths:
    - "lib/apr.py exists with module docstring listing APR-01..08 + LOCKED DECISIONS D-01..D-08"
    - "APRRequest, AdvanceScheduleEntry, PaymentScheduleEntry, APRResponse all use ConfigDict(strict=True, frozen=True, extra='forbid')"
    - "APRResponse.summary contains the literal substring 'estimated APR' enforced by @model_validator"
    - "APRRequest cross-field validators reject (a) advance schedule with no t=0 advance and (b) payment schedule whose periods sum to 0"
    - "Wave 0 stub test_apr_solver_module_exists_with_newton_raphson_signature flips PARTIALLY (model imports succeed; solver call still raises NotImplementedError until Wave 2)"
  artifacts:
    - path: "lib/apr.py"
      provides: "Pydantic models + solve_apr stub raising NotImplementedError"
      contains: "class APRRequest"
      min_lines: 250
---

## Goal

Ship the Pydantic v2 boundary models for Phase 7 (`APRRequest`,
`AdvanceScheduleEntry`, `PaymentScheduleEntry`, `APRResponse`) with the
"estimated APR" literal-text invariant enforced via `@model_validator`,
plus a `solve_apr` stub that raises `NotImplementedError` (Wave 2 fills
the body).

## Tasks

### Task 1 — Create `lib/apr.py` with module docstring + LOCKED DECISIONS

Top-of-file docstring enumerates D-01..D-08 (the load-bearing decisions
listed in §LOCKED DECISIONS below) + the Phase-7 consumer note pointing
back to `lib/rules/reg_z.py:43-47`.

### Task 2 — Define `AdvanceScheduleEntry`, `PaymentScheduleEntry`

```python
class AdvanceScheduleEntry(BaseModel):
    """One advance in the loan disbursement schedule (Reg Z Appendix J §(b)(2))."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    unit_period_offset: int = Field(ge=0, description="Whole unit periods between t=0 and the advance")
    unit_period_fraction: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), lt=Decimal("1"))
    amount: Money

class PaymentScheduleEntry(BaseModel):
    """One regular-payment block in the schedule.

    A 30-year monthly mortgage with one payment level is a single entry
    with periods=360. Construction loans with payment changes mid-term
    use multiple entries.
    """
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    starting_unit_period: int = Field(ge=1)
    periods: int = Field(ge=1)
    amount: Money
    unit_period_fraction: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), lt=Decimal("1"))
```

### Task 3 — Define `APRRequest` with cross-field validators

```python
class APRRequest(BaseModel):
    """Reg Z Appendix J APR-solve request.

    See `references/apr-reg-z.md` for the unit-period model + day-count
    conventions. Pydantic v2 strict + frozen + forbid per Phase 1 D-08.
    """
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    finance_charges: Money = Field(description="Sum of §1026.4 finance charges; subtracted from loan_amount per §1026.18(b)")
    advance_schedule: list[AdvanceScheduleEntry]
    payment_schedule: list[PaymentScheduleEntry]
    day_count: Literal["30/360", "actual/365", "actual/actual"] = "30/360"
    unit_periods_per_year: int = Field(default=12, ge=1, le=365)
    odd_first_period_days: int = Field(default=0, ge=0, le=365, description="Days beyond standard unit period from origination to first payment; 0 = no odd period")
    disclosed_apr: Money | None = Field(default=None, description="Optional lender-disclosed APR; when set, APRResponse.tolerance_check is populated")

    @model_validator(mode="after")
    def _advance_schedule_has_t0_advance(self) -> APRRequest:
        if not any(a.unit_period_offset == 0 and a.unit_period_fraction == Decimal("0") for a in self.advance_schedule):
            raise ValueError("advance_schedule MUST contain at least one advance at unit_period_offset=0 (Reg Z Appendix J §(b)(2))")
        return self

    @model_validator(mode="after")
    def _payment_schedule_non_empty(self) -> APRRequest:
        total_periods = sum(p.periods for p in self.payment_schedule)
        if total_periods == 0:
            raise ValueError("payment_schedule MUST sum to at least 1 period")
        return self
```

### Task 4 — Define `APRResponse` with literal-text invariant

```python
class APRResponse(BaseModel):
    """Result of solve_apr().

    summary always contains the literal text 'estimated APR' (ROADMAP SC-4).
    """
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    estimated_apr: Decimal = Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1"))
    iterations: int = Field(ge=1, le=50, description="Newton iterations to converge (ROADMAP SC-3 cap)")
    final_residual: Money = Field(description="abs(f(i_final)) — dollar residual at convergence")
    summary: str = Field(min_length=10, description="User-facing summary; MUST contain literal 'estimated APR' (SC-4)")
    tolerance_check: dict[str, Any] | None = Field(default=None, description="Populated when APRRequest.disclosed_apr supplied; cites 12 CFR §1026.22(a)")

    @model_validator(mode="after")
    def _summary_contains_literal_estimated_apr(self) -> APRResponse:
        # ROADMAP SC-4: literal 'estimated APR' MUST appear; bare 'APR' MUST NOT
        if "estimated APR" not in self.summary:
            raise ValueError(
                f"APRResponse.summary MUST contain literal 'estimated APR' per ROADMAP SC-4; got: {self.summary!r}"
            )
        # Strip the allowed literal then check for any bare 'APR' word
        stripped = self.summary.replace("estimated APR", "")
        # Allow 'APR tolerance' (regulatory phrase) but not bare 'APR'
        bare_apr = re.search(r'\bAPR\b(?!\s*tolerance)', stripped)
        if bare_apr is not None:
            raise ValueError(
                f"APRResponse.summary MUST NOT contain bare 'APR' (only 'estimated APR' or 'APR tolerance'); got: {self.summary!r}"
            )
        return self
```

### Task 5 — Solver stub raising `NotImplementedError`

```python
def solve_apr(request: APRRequest) -> APRResponse:
    """Solve for the estimated APR via Newton-Raphson (Wave 2 implements body).

    See references/apr-reg-z.md §5 for the algorithm.
    """
    raise NotImplementedError("Wave 2 (Plan 07-02) implements the Newton-Raphson body")
```

### Task 6 — Flip Wave 0 stub `test_apr_solver_module_exists_with_newton_raphson_signature`

Replace stub body with:
```python
from lib.apr import APRRequest, APRResponse, solve_apr
import inspect
sig = inspect.signature(solve_apr)
assert "request" in sig.parameters
assert sig.return_annotation is APRResponse or sig.return_annotation == "APRResponse"
```
Remove the `@pytest.mark.xfail` decorator (xfail strict would fail otherwise).

## Acceptance

- `lib/apr.py` exists, ≥250 lines
- `grep -c 'ConfigDict(strict=True, frozen=True, extra="forbid")' lib/apr.py` returns 4
- `grep -c '@model_validator(mode="after")' lib/apr.py` returns ≥3
- `grep -c "estimated APR" lib/apr.py` returns ≥2 (validator string + docstring)
- `pytest tests/test_apr.py::test_apr_solver_module_exists_with_newton_raphson_signature -v` PASSES (xfail removed)
- All other 12 stubs still XFAIL
- mypy --strict lib/apr.py exits clean
- ruff check + format clean

## LOCKED DECISIONS

- **D-01:** All four boundary models use `ConfigDict(strict=True, frozen=True, extra="forbid")`. Phase 1 D-08 inheritance.
- **D-02:** `APRRequest.day_count` defaults to `"30/360"` per FFIEC tool default + RESEARCH §Q(b). Settable.
- **D-03:** `APRRequest.unit_periods_per_year` defaults to 12 (monthly mortgage). Settable for non-monthly products (Phase 8+ stress paths may use 26 for biweekly).
- **D-04:** `APRRequest.finance_charges` is REQUIRED and CALLER-SUPPLIED. Engine does NOT classify per §1026.4 (orchestrator-locked decision; documented in references/apr-reg-z.md §3).
- **D-05:** `APRResponse.summary` literal-text invariant enforced at the Pydantic model boundary (not just at the CLI). Constructing `APRResponse(summary="APR is 7%")` raises ValidationError.
- **D-06:** `APRRequest.advance_schedule` MUST contain a t=0 advance. Reverse-mode "amount financed only" callers pass a single entry `AdvanceScheduleEntry(unit_period_offset=0, amount=request.loan.principal - request.finance_charges)`.
- **D-07:** `APRResponse.iterations` is `Field(ge=1, le=50)` — Pydantic enforces SC-3 at the model level. Solver MUST raise APRConvergenceError before constructing the response if cap exceeded.
- **D-08:** `APRResponse.tolerance_check` is `dict[str, Any] | None` (not a typed model) to keep the schema flexible for Phase 8/12 extensions; documented field-by-field in the docstring.

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
pytest tests/test_apr.py::test_apr_solver_module_exists_with_newton_raphson_signature -v
pytest tests/test_apr.py -v --tb=no 2>&1 | tail -20  # expect 1 passed + 12 xfailed
mypy --strict lib/apr.py
ruff check lib/apr.py
ruff format --check lib/apr.py
```

## Deviation Rules

- Rule-1: any change to model field NAMES requires plan revision (Wave 2-4
  reference these names verbatim).
- Rule-3: hygiene only (mypy/ruff fixes that do not change semantics) — log in SUMMARY.

## Cross-wave Dependency Notes

- **Upstream:** Wave 0 (test stubs).
- **Downstream:** Wave 2 (solve_apr body) depends on these models being
  importable; Wave 4 (CLI) imports `APRRequest` for Pydantic validation.
- APR-01 is partially closed here (model surface) and fully closed by Wave 2.
