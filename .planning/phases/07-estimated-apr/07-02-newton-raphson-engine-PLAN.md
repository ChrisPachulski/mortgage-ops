---
phase: 07
plan: 02
type: execute
wave: 2
depends_on: ["07-01"]
files_modified:
  - lib/apr.py
autonomous: true
requirements: [APR-01, APR-02, APR-03]
tags:
  - phase-07
  - estimated-apr
  - solver-engine
must_haves:
  truths:
    - "lib/apr.py exposes _unit_period_equation(advances, payments, i) -> Decimal returning f(i)"
    - "lib/apr.py exposes _derivative(advances, payments, i) -> Decimal returning f'(i)"
    - "lib/apr.py exposes _seed_apr(advance_schedule, payment_schedule) -> Decimal using npf.rate with NaN/out-of-range fallback"
    - "lib/apr.py exposes solve_apr(request) -> APRResponse running Newton-Raphson with hard cap 50"
    - "Solver raises APRConvergenceError(ValueError subclass) if cap exceeded"
    - "All Decimal arithmetic in iteration uses with localcontext(MONEY_CONTEXT); no float leaks"
    - "_decimal_pow(base, exponent) helper computed via Decimal.exp(Decimal.ln(base) * exponent)"
  artifacts:
    - path: "lib/apr.py"
      provides: "Newton-Raphson solver body + helper functions"
      contains: "def solve_apr"
      min_lines: 450
---

## Goal

Implement the Newton-Raphson APR solver against the Reg Z Appendix J
unit-period equation. Decimal-context iteration; npf.rate seed with
fallback; hard 50-iteration cap; `Decimal("0.00001")` convergence
tolerance plus dollar-residual sanity check; `quantize_rate` ONCE at
result.

## Tasks

### Task 1 — Helper `_decimal_pow(base, exponent) -> Decimal`

For fractional exponents (the (1+i)^(-t-f) terms in the U-equation),
native `Decimal.__pow__` is unreliable. Route through ln/exp:

```python
def _decimal_pow(base: Decimal, exponent: Decimal) -> Decimal:
    """Compute base ** exponent via Decimal.exp(Decimal.ln(base) * exponent).

    Native Decimal.__pow__ requires integer exponents; we route through
    ln/exp for fractional exponents, preserving MONEY_CONTEXT.prec=28.
    """
    if base <= Decimal("0"):
        raise ValueError(f"_decimal_pow requires positive base; got {base}")
    with localcontext(MONEY_CONTEXT):
        return (base.ln() * exponent).exp()
```

### Task 2 — `_unit_period_equation(advances, payments, i) -> Decimal` (compute f(i))

```python
def _unit_period_equation(
    advances: list[AdvanceScheduleEntry],
    payments: list[PaymentScheduleEntry],
    i: Decimal,
) -> Decimal:
    """Reg Z Appendix J §(b): f(i) = sum_advances - sum_payments (PV at rate i).

    Each advance/payment uses the (1 + f·i)·(1+i)^(-t) form (simple interest
    within the fractional period; compound between full periods).
    Returns f(i) — zero at the converged APR.
    """
    with localcontext(MONEY_CONTEXT):
        one = Decimal("1")
        adv_sum = Decimal("0")
        for a in advances:
            t = Decimal(a.unit_period_offset)
            f = a.unit_period_fraction
            adv_sum += a.amount * (one + f * i) * _decimal_pow(one + i, -t)
        pmt_sum = Decimal("0")
        for p in payments:
            for k in range(p.periods):
                s = Decimal(p.starting_unit_period + k)
                g = p.unit_period_fraction if k == 0 else Decimal("0")
                pmt_sum += p.amount * (one + g * i) * _decimal_pow(one + i, -s)
        return adv_sum - pmt_sum
```

### Task 3 — `_derivative(advances, payments, i) -> Decimal` (compute f'(i))

```python
def _derivative(
    advances: list[AdvanceScheduleEntry],
    payments: list[PaymentScheduleEntry],
    i: Decimal,
) -> Decimal:
    """f'(i) closed-form per RESEARCH §Q(c)."""
    with localcontext(MONEY_CONTEXT):
        one = Decimal("1")
        adv_d = Decimal("0")
        for a in advances:
            t = Decimal(a.unit_period_offset)
            f = a.unit_period_fraction
            term1 = a.amount * f * _decimal_pow(one + i, -t)
            term2 = a.amount * (one + f * i) * t * _decimal_pow(one + i, -t - one)
            adv_d += term1 - term2
        pmt_d = Decimal("0")
        for p in payments:
            for k in range(p.periods):
                s = Decimal(p.starting_unit_period + k)
                g = p.unit_period_fraction if k == 0 else Decimal("0")
                term1 = p.amount * g * _decimal_pow(one + i, -s)
                term2 = p.amount * (one + g * i) * s * _decimal_pow(one + i, -s - one)
                pmt_d += term1 - term2
        return adv_d - pmt_d
```

### Task 4 — `_seed_apr(advance_schedule, payment_schedule) -> Decimal` with fallback

```python
def _seed_apr(
    advance_schedule: list[AdvanceScheduleEntry],
    payment_schedule: list[PaymentScheduleEntry],
) -> Decimal:
    """Seed Newton-Raphson via npf.rate treating loan as regular transaction.

    Per APR-02: treat as if every advance were a single t=0 net principal
    and every payment were the average. npf.rate is float; cast through
    Decimal(str(...)) at the boundary.

    Fallback (per RESEARCH §Q(c)): if npf.rate returns NaN or out of [0,1],
    use nominal_rate = total_interest / pv / n.
    """
    pv_float = float(sum(a.amount for a in advance_schedule))
    total_pmt_float = float(sum(p.amount * p.periods for p in payment_schedule))
    n_total = sum(p.periods for p in payment_schedule)
    pmt_avg_float = total_pmt_float / n_total
    try:
        seed_float = float(npf.rate(nper=n_total, pmt=-pmt_avg_float, pv=pv_float, fv=0))
        if math.isnan(seed_float) or seed_float < 0 or seed_float > 1:
            raise ValueError("npf.rate seed out of range")
        return Decimal(str(seed_float))
    except (ValueError, ZeroDivisionError):
        # Fallback: nominal rate-of-return
        total_interest = total_pmt_float - pv_float
        if pv_float <= 0 or n_total <= 0:
            return Decimal("0.005")  # 6%/yr last-resort
        return Decimal(str(total_interest / pv_float / n_total))
```

### Task 5 — `APRConvergenceError` exception class

```python
class APRConvergenceError(ValueError):
    """Newton-Raphson failed to converge within the 50-iteration cap (SC-3).

    Surfaced via scripts/apr_reg_z.py 6-key envelope as type='value_error',
    loc=['solver'], ctx={'class':'APRConvergenceError', 'iterations': 50,
    'last_residual': str(...)} — Phase 4 D-13 inheritance.
    """
    def __init__(self, iterations: int, last_residual: Decimal, last_i: Decimal):
        self.iterations = iterations
        self.last_residual = last_residual
        self.last_i = last_i
        super().__init__(
            f"Newton-Raphson did not converge within {iterations} iterations "
            f"(ROADMAP SC-3 cap=50); last_residual={last_residual}, last_i={last_i}"
        )
```

### Task 6 — `solve_apr(request) -> APRResponse` body

Replace the Wave 1 NotImplementedError stub with:

```python
def solve_apr(request: APRRequest) -> APRResponse:
    """Solve for the estimated APR via Newton-Raphson per Reg Z Appendix J.

    Pipeline:
      1. Seed via _seed_apr (npf.rate of regular-transaction approximation).
      2. Newton iteration in MONEY_CONTEXT (prec=28 Decimal):
         i_{n+1} = i_n - f(i_n)/f'(i_n)
      3. Convergence: abs(i_{n+1} - i_n) <= Decimal("0.00001")
                  AND abs(f(i_{n+1})) <= Decimal("0.01")  (dollar residual)
      4. Hard cap 50 iterations; APRConvergenceError if exceeded.
      5. APR = quantize_rate(i_final * unit_periods_per_year)
      6. tolerance_check populated if disclosed_apr supplied.
    """
    TOLERANCE = Decimal("0.00001")
    DOLLAR_RESIDUAL = Decimal("0.01")
    MAX_ITER = 50

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with localcontext(MONEY_CONTEXT):
            i = _seed_apr(request.advance_schedule, request.payment_schedule)
            iterations = 0
            for n in range(1, MAX_ITER + 1):
                iterations = n
                f_val = _unit_period_equation(request.advance_schedule, request.payment_schedule, i)
                fprime = _derivative(request.advance_schedule, request.payment_schedule, i)
                if fprime == Decimal("0"):
                    raise APRConvergenceError(iterations=n, last_residual=abs(f_val), last_i=i)
                i_next = i - f_val / fprime
                if abs(i_next - i) <= TOLERANCE and abs(f_val) <= DOLLAR_RESIDUAL:
                    i = i_next
                    break
                i = i_next
            else:
                raise APRConvergenceError(iterations=MAX_ITER, last_residual=abs(f_val), last_i=i)

            estimated_apr = quantize_rate(i * Decimal(request.unit_periods_per_year))
            final_residual_quantized = quantize_cents(abs(f_val))

    apr_pct_str = f"{estimated_apr * Decimal('100'):.4f}"
    summary = (
        f"estimated APR: {apr_pct_str}% "
        f"(converged in {iterations} iterations, residual ${final_residual_quantized})"
    )

    tolerance_check: dict[str, Any] | None = None
    if request.disclosed_apr is not None:
        from lib.rules.reg_z import within_apr_tolerance, TOLERANCE_REGULAR
        is_within = within_apr_tolerance(
            disclosed_apr=request.disclosed_apr,
            actual_apr=estimated_apr,
            is_irregular_transaction=False,  # caller-supplied via separate flag in future extension
        )
        tolerance_check = {
            "disclosed_apr": str(request.disclosed_apr),
            "estimated_apr": str(estimated_apr),
            "within_tolerance": is_within,
            "tolerance_used": str(TOLERANCE_REGULAR),
            "regulation": "12 CFR §1026.22(a)(2)",
        }

    return APRResponse(
        estimated_apr=estimated_apr,
        iterations=iterations,
        final_residual=final_residual_quantized,
        summary=summary,
        tolerance_check=tolerance_check,
    )
```

### Task 7 — Flip Wave 0 stubs

Remove `@pytest.mark.xfail` and replace bodies with real assertions for:
- `test_apr_solver_seeded_from_npf_rate` — assert `_seed_apr(...) ==
  Decimal(str(npf.rate(...)))` for a regular fixture.
- `test_apr_solver_converges_within_decimal_00001_tolerance` — uses
  `apr_fixture("regz_appendix_j_5000_36_166_07")` (Wave 5 ships the
  fixture; Wave 2 can land an inline temp-fixture variant if needed for
  Wave-2-only verification, with a TODO comment to swap for the Wave 5
  file).
- `test_apr_solver_raises_on_non_convergence` — construct a deliberately
  ill-conditioned APRRequest (e.g., advances summing to 0; or payments
  summing to less than advances → no positive-rate solution); assert
  `pytest.raises(APRConvergenceError)`.

## Acceptance

- `grep -c 'def _unit_period_equation' lib/apr.py` returns 1
- `grep -c 'def _derivative' lib/apr.py` returns 1
- `grep -c 'def _seed_apr' lib/apr.py` returns 1
- `grep -c 'def _decimal_pow' lib/apr.py` returns 1
- `grep -c 'class APRConvergenceError' lib/apr.py` returns 1
- `grep -c 'NotImplementedError' lib/apr.py` returns 0 (Wave 1 stub removed)
- `mypy --strict lib/apr.py` exits clean (no `float` leaks except inside `_seed_apr`)
- `pytest tests/test_apr.py::test_apr_solver_seeded_from_npf_rate -v` PASSES
- `pytest tests/test_apr.py::test_apr_solver_converges_within_decimal_00001_tolerance -v` PASSES (or xfail-stays if Wave 5 anchor not yet shipped — document in SUMMARY)
- `pytest tests/test_apr.py::test_apr_solver_raises_on_non_convergence -v` PASSES
- ruff check + format clean

## LOCKED DECISIONS

- **D-09:** Newton iteration runs in `with localcontext(MONEY_CONTEXT)` (prec=28). NO custom `prec=50` — RESEARCH §Q(h) confirms 28 sufficient for `Decimal("0.00001")` tolerance.
- **D-10:** Convergence test combines `abs(i_{n+1} − i_n) ≤ 0.00001` AND `abs(f(i_n)) ≤ 0.01` (dollar residual). Both must hold (defense-in-depth per RESEARCH OPEN Q2).
- **D-11:** Seed function uses `float`/`npf.rate` and casts through `Decimal(str(...))` exactly once at the boundary. The cast is the ONLY float→Decimal transition. `mypy --strict` enforces no other float in the iteration.
- **D-12:** Hard cap 50 iterations is encoded as a module-level constant `MAX_ITER = 50`. APRConvergenceError surfaces with the iteration count + last residual for debugging.
- **D-13:** `_decimal_pow` for fractional exponents uses `Decimal.exp(Decimal.ln(base) * exponent)`. Negative-base inputs raise ValueError (mathematically undefined for fractional exponents). Pinned by `test_decimal_pow_fractional_exponent_correctness` (sibling test added in Wave 5).
- **D-14:** `solve_apr` quantizes the final APR via `quantize_rate(i * unit_periods_per_year)` ONCE at end (Phase 5 D-14 + lib.money inheritance).

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
pytest tests/test_apr.py -v --tb=short 2>&1 | tail -30
mypy --strict lib/apr.py
ruff check lib/apr.py
ruff format --check lib/apr.py
# Sanity: full suite holds the Phase 5 baseline
pytest -q 2>&1 | tail -5
```

## Deviation Rules

- Rule-1: any change to convergence tolerance, iteration cap, or seed
  fallback strategy requires plan revision.
- Rule-2 (math): hand-verify against Reg Z Appendix J Example J-1 BEFORE
  declaring the wave done. If the engine returns anything other than
  Decimal("0.120000") within Decimal("0.00001") on that fixture, STOP and
  investigate the U-equation implementation (sign flip in advance vs
  payment is the most common bug).
- Rule-3: hygiene only.

## Cross-wave Dependency Notes

- **Upstream:** Wave 1 (Pydantic models). Models MUST exist before solver
  references them.
- **Downstream:** Wave 5 (tests + Reg Z anchor fixture) flips
  `test_apr_reg_z_appendix_j_worked_example_returns_12_percent` (the
  SC-1 anchor) once the fixture file lands. Wave 7 (FFIEC fixtures)
  exercises the solver on the 20+ irregular-schedule corpus (validates
  the multi-advance / odd-period / day-count code paths).
- APR-01..APR-03 fully closed by this wave (model + body + convergence).
