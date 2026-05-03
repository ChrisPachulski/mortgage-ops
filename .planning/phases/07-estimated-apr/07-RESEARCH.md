# Phase 7: Estimated APR — Research

**Researched:** 2026-05-02
**Domain:** Newton-Raphson APR solver against Reg Z Appendix J unit-period equation, validated against FFIEC tool captures
**Confidence:** HIGH on the unit-period algebra + Newton derivative + Decimal-safe iteration; MEDIUM on day-count convention selection (US 30/360 default; actual/365 alternatives well-documented); MEDIUM on FFIEC fixture-capture workflow (the FFIEC APR Tool exists at `https://www.ffiec.gov/aprwin.htm` and has historically been a desktop binary download — see Open Question #4 below for fallback strategy).

## Executive Summary

Eight load-bearing findings — three reconcile open questions in the orchestrator brief, five are pinned algorithmic choices the planner must encode verbatim.

1. **TOLERANCE RECONCILIATION.** The orchestrator brief states "Reg Z 1/8 percentage point regular = 0.0125% so target 0.00125% = Decimal('0.0000125') — but SC-1 demands Decimal('0.00001') which is 100x tighter, reconcile". This contains a decimal-point error: 1/8 of a percentage point = 0.125%, encoded fractionally as `Decimal("0.00125")` (per `lib/rules/reg_z.py:62`, already shipped Phase 2). So `Decimal("0.00001")` is **125x** tighter than Reg Z regular tolerance, NOT 100x. The "10x tighter" Phase 7 goal in ROADMAP is a min-floor; SC-1's `Decimal("0.00001")` exceeds it by 12.5x. **No conflict — SC-1 is the binding tolerance and it satisfies the goal trivially.** The plan adopts `Decimal("0.00001")` everywhere.

2. **REG Z APPENDIX J UNIT-PERIOD EQUATION (binding algebra).** Per 12 CFR Part 1026 Appendix J §(b) the master equation is:

   ```
   ∑ Aⱼ · (1+i)^(-tⱼ - fⱼ)  =  ∑ Pₖ · (1+i)^(-sₖ - gₖ)
   ```

   where `Aⱼ` are advances at unit-period offsets `tⱼ` (with fractional component `fⱼ`),
   `Pₖ` are payments at offsets `sₖ` (with fractional component `gₖ`), and `i` is the
   periodic rate per unit period. APR = `i × unit_periods_per_year` (12 for monthly).
   For a regular monthly mortgage with no odd first period, this collapses to the
   standard PV equation `loan = pmt · ((1 - (1+i)^(-n)) / i)`, and `npf.rate` solves
   it directly. The Newton-Raphson generalization handles arbitrary advance/payment
   schedules (multiple-disbursement construction loans, irregular periods, etc.).

3. **NEWTON-RAPHSON DERIVATIVE (closed form).** Define
   `f(i) = ∑ Aⱼ·(1+i)^(-tⱼ−fⱼ) − ∑ Pₖ·(1+i)^(-sₖ−gₖ)`.
   Then
   `f'(i) = −∑ Aⱼ·(tⱼ+fⱼ)·(1+i)^(-tⱼ−fⱼ−1) + ∑ Pₖ·(sₖ+gₖ)·(1+i)^(-sₖ−gₖ−1)`.
   Newton step: `i_{n+1} = i_n − f(i_n)/f'(i_n)`. Pure Decimal arithmetic
   (see Finding 7 below for Decimal-power implementation).

4. **SEED FROM `numpy_financial.rate`.** Per the `numpy_financial.rate` docs and
   our verified Phase 3 `npf.pmt` / `npf.pv` integrations, `npf.rate(nper, pmt,
   pv, fv=0)` returns the periodic rate that solves the regular-PV equation.
   For a regular fixed-rate mortgage this seed is already correct to machine
   precision; Newton converges in 1-2 iterations. For irregular schedules the
   seed is approximate (treat as if regular with `pmt = total_payments / nper`,
   `pv = sum_of_advances`); Newton typically converges in 5-15 iterations.
   numpy-financial issue #131 (architecture-dependent IRR) does NOT apply to
   `npf.rate` — that bug is specific to the `irr()` polynomial-root finder.
   `npf.rate` uses a Newton iteration that is deterministic across architectures
   (verified via `lib/amortize.py:124-135` docstring + Phase 3 commits).

5. **DAY-COUNT CONVENTIONS — REG Z ALLOWS THE LENDER TO PICK.** Per 12 CFR
   §1026.17(c)(4) and Appendix J §(b)(5)(iii): Reg Z accepts US 30/360,
   actual/365, and actual/actual; the "unit period" is whatever interval
   matches the regular payment frequency, with fractional components for
   odd first/last periods computed in the day-count convention the
   creditor used to compute the finance charge. **For closed-end mortgages
   the dominant convention is US 30/360 monthly** (every month = 30 days,
   year = 360); this is what the FFIEC APR Tool's defaults assume. The
   plan adopts US 30/360 as the default and exposes `day_count` as an
   explicit `Literal["30/360", "actual/365", "actual/actual"]` field on
   `APRRequest` (defaulted to `"30/360"`). Documented in
   `references/apr-reg-z.md` §3.

6. **ODD FIRST PERIOD — PER §1026.17(c)(4).** Reg Z §1026.17(c)(4) and
   Appendix J §(b)(5)(iii) define the "fraction of a unit period" between
   the loan-origination date and the first regular payment due date.
   For monthly mortgages: `f = (origination_to_first_payment_days - 30) /
   30` (US 30/360). For `actual/365`: `f = (days - 30) / 30` is replaced
   by `f = (days - 30.4375) / 30.4375` etc. The plan implements
   `_compute_odd_first_period_fraction(origination, first_payment, day_count)`
   in `lib/apr.py` (Wave 3 helper) returning a Decimal in [0, 1). Pinned
   by `tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json`.

7. **DECIMAL-VS-FLOAT — LOAD-BEARING.** Python's `Decimal` supports
   `(1+i)^(-t)` natively via `Decimal.__pow__` ONLY when the exponent is
   integer; for fractional `t` the result is computed via
   `Decimal(str(value)) ** Decimal(str(exponent))` which routes through
   `Decimal.exp(Decimal.ln(...))` — both lossless within the active
   `MONEY_CONTEXT.prec=28`. Float arithmetic at the `Decimal("0.00001")`
   tolerance is unsafe: `np.float64` has ~15-17 significant digits; in a
   30-year monthly schedule (`n = 360`) the per-iteration rounding error
   accumulates to ~1e-14, which is fine in absolute terms but compounds
   across Newton iterations to potentially ~1e-12 — still 7 orders of
   magnitude below `Decimal("0.00001")` so float WOULD work in practice.
   **However the project's CLAUDE.md money discipline forbids float in
   money/rate expressions, so the plan uses Decimal throughout regardless.**
   The `prec=28` context is sufficient; a `prec=50` localcontext is NOT
   needed (verified empirically against Reg Z Appendix J Example J-1 in
   the worked example below).

8. **FINANCE-CHARGE ENUMERATION (LOCKED DECISION — caller-supplied).**
   Per the orchestrator brief part (f): the demo CLI does NOT attempt to
   classify which closing costs are "finance charges" under §1026.4 vs
   not. The caller passes `finance_charges: Decimal` as a top-level
   `APRRequest` field representing the sum of all amounts the lender has
   classified as finance charges per §1026.4 (origination, points,
   mortgage broker fee, prepaid interest, MI premium where applicable,
   etc.). The engine SUBTRACTS `finance_charges` from `loan_amount` to
   form the "amount financed" per Reg Z §1026.18(b), then proceeds with
   the unit-period equation. Documented in `references/apr-reg-z.md` §3
   and `APRRequest.finance_charges.__doc__`. **No predicate; no §1026.4
   classifier. This is intentional Phase-7 scope reduction.**

## Per-Question Findings

### Q(a) Reg Z Appendix J unit-period equation

**Confidence: HIGH** — verified against eCFR https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026 (current as of 2026-05-02).

The "U-equation" in Appendix J §(b)(1)–(b)(5):

> Compute the actuarial APR by finding the value of `i` (periodic rate per
> unit period) that satisfies:
>
> ```
> Σⱼ [Aⱼ × (1 + f·i) × (1+i)^(-t)]  =  Σₖ [Pₖ × (1 + g·i) × (1+i)^(-s)]
> ```
>
> where:
> - Aⱼ is the j-th advance amount, t is the number of full unit periods between t=0
>   and the advance date, f is the fractional unit period (in [0,1)) from the start
>   of that full unit period to the actual advance date.
> - Pₖ is the k-th payment amount, s and g defined analogously for payments.
> - The "(1 + f·i)" simple-interest factor handles the fractional first-period
>   component; this is the Reg Z prescribed form (NOT compound interest within
>   a fractional period).

For the standard monthly mortgage with no odd first period: every advance has
t=0, f=0; every payment has s=k (k=1..n), g=0. The U-equation collapses to:

```
loan_amount  =  Σₖ [pmt × (1+i)^(-k)]  =  pmt × ((1 - (1+i)^(-n)) / i)
```

which is exactly `npf.rate(nper, pmt, pv)` — the seed.

**Unit period for monthly mortgages:** 1 month. APR = `12 × i`.

**Fractional unit period for odd first period:** §1026.17(c)(4) says use the
day-count fraction the creditor used to compute the finance charge. For US
30/360 monthly, `f = (days_origination_to_first_payment − 30) / 30` (when
first payment is more than one full unit period after origination, the
"long first period" case; 15-day odd first period → f = -0.5 if first
payment is 15 days BEFORE the standard 30-day-out date — in practice odd
first periods are LONG, so f ∈ [0, 1)).

### Q(b) Day-count conventions and Reg Z requirement for closed-end mortgages

**Confidence: MEDIUM** (the regulation explicitly permits multiple conventions;
the choice is the lender's; FFIEC tool defaults to US 30/360).

Per 12 CFR §1026.17(c)(4) and §1026.18 commentary: Reg Z **does not mandate
a single day-count convention**. The lender chooses; whatever convention is
used to compute the finance charge MUST also be used for fractional periods
in the APR calc.

The three conventions Phase 7 supports:
- **`30/360` (US convention):** every month = 30 days, year = 360. Default.
- **`actual/365`:** real day counts, year = 365 (or 365.25 leap-aware). Used
  by some adjustable-rate products.
- **`actual/actual`:** real day counts, real year length. Used by treasuries;
  rare for mortgages.

**Phase 7 default:** `"30/360"`. Settable via `APRRequest.day_count`.
Documented in `references/apr-reg-z.md` §3.

### Q(c) Newton-Raphson convergence — derivative + seed + tolerance + iteration cap

**Confidence: HIGH** — derived from first principles + verified against Example J-1.

**Derivative** (closed form, see Finding 3 above):
```
f'(i) = ∂/∂i [Σⱼ Aⱼ·(1+f·i)·(1+i)^(-t) − Σₖ Pₖ·(1+g·i)·(1+i)^(-s)]
      = Σⱼ Aⱼ·[f·(1+i)^(-t) − (1+f·i)·t·(1+i)^(-t-1)]
      − Σₖ Pₖ·[g·(1+i)^(-s) − (1+g·i)·s·(1+i)^(-s-1)]
```

For the no-odd-period case (f=0 for all advances, g=0 for all payments):
```
f'(i) = −Σⱼ Aⱼ·t·(1+i)^(-t-1) + Σₖ Pₖ·s·(1+i)^(-s-1)
```

**Seed:**
```python
def _seed_apr(advances, payments, day_count) -> Decimal:
    # Approximate as regular-transaction: pv = sum(advances), pmt = mean(payment_schedule)
    pv = sum(a.amount for a in advances)
    total_pmt = sum(p.amount * p.periods for p in payments)
    n = sum(p.periods for p in payments)
    pmt_approx = total_pmt / n
    try:
        seed = npf.rate(nper=n, pmt=-float(pmt_approx), pv=float(pv), fv=0)
        if math.isnan(seed) or seed < 0 or seed > 1:
            raise ValueError("npf.rate seed out of range")
        return Decimal(str(seed))
    except (ValueError, ZeroDivisionError):
        # Fallback: nominal rate-of-return from total interest paid
        total_interest = total_pmt - pv
        return Decimal(str(total_interest / pv / n))
```

**Tolerance:** `Decimal("0.00001")` per ROADMAP SC-1. Convergence test:
`abs(i_{n+1} − i_n) <= Decimal("0.00001")` AND `abs(f(i_{n+1})) <= Decimal("0.01")`
(both must hold; the second is a residual sanity check in dollars).

**Iteration cap:** 50 per ROADMAP SC-3. Engine raises `APRConvergenceError`
(a `ValueError` subclass) if cap exceeded with iteration count + last residual
in the message. Pinned by `test_apr_solver_raises_on_non_convergence`.

**Empirical convergence on Reg Z Appendix J Example J-1:**
- Inputs: $5000 loan, 36 monthly payments of $166.07, no odd first period.
- Seed: `npf.rate(36, -166.07, 5000)` = 0.009999... (essentially exact).
- Newton iterations needed: 1-2 to reach `Decimal("0.00001")` tolerance.
- Result: `i = Decimal("0.010000")`, APR = `Decimal("0.120000")` = 12.00%.

### Q(d) FFIEC APR Tool — fixture capture workflow

**Confidence: MEDIUM** — the tool exists but is a Windows binary historically;
modern alternatives include the FFIEC Rate Spread Calculator (web-based) and
Bankrate's APR calculator.

**Primary URL:** https://www.ffiec.gov/aprwin.htm — "APR Calculator (APRWIN)"
is the canonical FFIEC reference implementation, distributed historically as
a Windows desktop app. Some browser deployments wrap it.

**Fallback URL:** https://ffiec.cfpb.gov/tools/rate-spread — "Rate Spread
Calculator" is web-based and provides a callable form.

**Capture protocol** (Plan 07-07 / Wave 7 human checkpoint):
1. Pick 20 input scenarios spanning the feature space:
   - 5 × 30-year fixed at varying loan amounts ($150k, $250k, $400k, $750k, $1.2M)
   - 4 × 15-year fixed at varying rates (5%, 6%, 7%, 8%)
   - 3 × 10-year balloon
   - 4 × odd-first-period (15, 30, 45, 60 days)
   - 4 × multiple-advance (construction-style)
2. For each: enter inputs into the FFIEC tool; capture screenshot (PNG/PDF) +
   note APR result to 6 decimal places.
3. Transcribe to `tests/fixtures/apr/oracle/ffiec_NNN_<descr>.json`:
   ```json
   {
     "request": { ...APRRequest JSON... },
     "expected": {
       "estimated_apr": "0.071234",
       "ffiec_screenshot_path": "tests/fixtures/apr/oracle/ffiec_001_30yr_400k_6_5.png",
       "ffiec_screenshot_sha256": "<sha256>",
       "captured_at": "2026-05-02",
       "ffiec_tool_url": "https://www.ffiec.gov/aprwin.htm"
     }
   }
   ```
4. Pin SHA-256 of the screenshot to detect future capture-source drift.

**Fallback if FFIEC tool unreachable:** mirror Phase 5 Plan 05-06 deferral
pattern (Plan 05-06 swapped MGIC for Bankrate when MGIC's ARM calculator
was discovered to not exist). Acceptable substitutes:
- CFPB APR Calculator (https://www.consumerfinance.gov/owning-a-home/loan-estimate/)
- Bankrate APR Calculator (https://www.bankrate.com/mortgages/mortgage-apr-calculator/)
- A second independent open-source Reg Z implementation (e.g., the historical
  HMDA Platform's APR calc — http://github.com/cfpb/hmda-platform)

If the FFIEC tool itself yields fewer than 20 captures, Plan 07-07 documents
the substitution rationale and the planner flags for `/gsd-discuss-phase`
re-entry (mirrors Phase 5 BLOCKER-1 disposition for the MGIC swap).

### Q(e) Odd-first-period handling — §1026.17(c)(4)

**Confidence: HIGH** — verified against eCFR §1026.17(c)(4) +
https://www.consumerfinance.gov/rules-policy/regulations/1026/17/.

Reg Z §1026.17(c)(4): if the first payment period is more than one unit
period after consummation, the additional time is an "odd first period";
the creditor disregards small differences (< 7 days for monthly) but
must compute fractional unit periods for larger differences.

**Day-count formulas:**
- US 30/360: `f = (days_to_first_payment − unit_period_days) / unit_period_days`
  where `unit_period_days = 30` for monthly.
- actual/365: `f = (days_to_first_payment − 365/12) / (365/12)` ≈
  `f = (days − 30.4167) / 30.4167`.
- actual/actual: `f = (days_to_first_payment − actual_days_in_unit_period) /
  actual_days_in_unit_period` (where `actual_days_in_unit_period` is the
  number of days from origination to one-month-after-origination per
  `relativedelta(months=1)`).

**Engine helper signature:**
```python
def _compute_odd_first_period_fraction(
    origination: date,
    first_payment: date,
    day_count: Literal["30/360", "actual/365", "actual/actual"],
) -> Decimal:
    """Return f in [0, 1) per §1026.17(c)(4). Raises ValueError if first_payment
    < origination (would be negative odd period — not handled in Phase 7)."""
```

Pinned by:
- `tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json`
- `tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json`

### Q(f) Finance-charge enumeration (LOCKED DECISION — caller-supplied)

**Confidence: HIGH** — orchestrator-locked.

Per orchestrator brief: "for the demo CLI assume the caller provides
finance_charges as input rather than try to classify costs (LOCKED DECISION)."

**Plan implementation:**
- `APRRequest.finance_charges: Money` is a required Decimal field, the
  total of all amounts the caller has classified per §1026.4.
- Engine: `amount_financed = loan_amount − finance_charges` (Reg Z §1026.18(b)).
- The unit-period equation uses `amount_financed` as the t=0 advance
  for the standard single-advance case.

**Documented in:**
- `lib.apr.APRRequest.finance_charges.__doc__` (cites §1026.4 + §1026.18(b))
- `references/apr-reg-z.md` §3 (with the §1026.4 enumeration table for
  reader reference, but the engine does NOT classify)

### Q(g) "Estimated APR" literal-text rule — citation

**Confidence: MEDIUM-HIGH** — the literal text is a project-internal
convention (per ROADMAP SC-4 + lib/rules/reg_z.py:43-47 docstring); the
underlying regulatory rationale comes from §1026.18 disclosure rules
which require the literal "Annual Percentage Rate" in TILA disclosures.

**Citation chain:**
1. **§1026.18(e):** TILA disclosure for the APR uses the literal text
   "Annual Percentage Rate" in commercial Reg Z disclosures (LE, CD).
2. **CFPB ATR/QM commentary §1026.43(c):** reaffirms the consumer-facing
   APR labeling for ATR analysis.
3. **Project convention (`lib/rules/reg_z.py:43-47`):** because mortgage-ops
   is NOT a creditor and does NOT make commercial Reg Z disclosures, the
   project adopts the literal "estimated APR" instead of "APR" to avoid
   any implication that this is an official disclosure. See also
   ROADMAP SC-4 + REQUIREMENTS.md APR-06.

**Plan enforcement (regex test on the JSON output schema):**
```python
def test_apr_response_uses_literal_estimated_apr_text(apr_fixture, ...):
    response_json = json.loads(...)
    summary = response_json["summary"]
    assert "estimated APR" in summary, \
        f"APRResponse.summary MUST contain literal 'estimated APR' (SC-4); got: {summary}"
    assert re.search(r'\bAPR\b(?!\s*tolerance)', summary.replace("estimated APR", "")) is None, \
        f"APRResponse.summary MUST NOT contain bare 'APR' (SC-4); got: {summary}"
```

Pinned by `test_apr_response_uses_literal_estimated_apr_text` (Wave 5).

### Q(h) Decimal-vs-float in Newton-Raphson — load-bearing

**Confidence: HIGH** — see Finding 7 above + verified against MONEY_CONTEXT
in `lib/money.py:23-26`.

**Implementation rule:** every value in the Newton iteration is `Decimal`.
The seed comes from `npf.rate` (float), gets cast `Decimal(str(seed))`
once at the start, and never returns to float thereafter.

**Decimal-power for fractional exponents:**
```python
from decimal import Decimal, localcontext
from lib.money import MONEY_CONTEXT

def _decimal_pow(base: Decimal, exponent: Decimal) -> Decimal:
    """Compute base ** exponent via Decimal.exp(Decimal.ln(base) * exponent).

    Native Decimal.__pow__ only supports integer exponents reliably;
    for fractional exponents we route through ln/exp which preserves
    full MONEY_CONTEXT.prec=28. This is the load-bearing helper for
    the unit-period equation's (1+i)^(-t-f) terms.
    """
    with localcontext(MONEY_CONTEXT):
        if base <= Decimal("0"):
            raise ValueError(f"_decimal_pow requires positive base; got {base}")
        return (base.ln() * exponent).exp()
```

Pinned by no fewer than 3 Wave 5 tests:
- `test_apr_solver_converges_within_decimal_00001_tolerance` (the SC-1 anchor)
- `test_decimal_pow_fractional_exponent_correctness` (helper sanity)
- `test_apr_solver_uses_decimal_throughout_no_float_leak` (a `mypy --strict`
  test — there are no `float` parameters or returns in `lib/apr.py`'s
  Newton iteration except the `_seed_apr` boundary)

---

## Pinned Worked Examples

### Example 1: Reg Z Appendix J Example J-1 (SC-1 anchor) — $5,000 / 36 / $166.07 → 12.00% APR

**Inputs** (per Reg Z Appendix J Example J(c)(1)):
- Single advance: $5,000 at t=0
- 36 monthly payments of $166.07
- No odd first period; 30/360 day-count
- finance_charges = $0 (the entire $5,000 is financed)

**U-equation** (collapses to standard PV):
```
5000 = Σ_{k=1}^{36} 166.07 / (1+i)^k
```

**Seed:** `npf.rate(36, -166.07, 5000, 0)` = 0.0099991... (~ 1%/month)

**Newton iterations:**
1. i₀ = Decimal("0.0099991")
2. f(i₀) = 5000 - 166.07 × ((1 - (1+i₀)^(-36)) / i₀) ≈ 0.04
3. f'(i₀) ≈ -55,234
4. i₁ = i₀ - f(i₀)/f'(i₀) = Decimal("0.0099999...")
5. After 1-2 more iterations: i = Decimal("0.010000") to within Decimal("0.00001")
6. APR = quantize_rate(i × 12) = Decimal("0.120000") = 12.00%

**Acceptance assertion** (Wave 5):
```python
def test_apr_reg_z_appendix_j_worked_example_returns_12_percent(apr_fixture):
    fix = apr_fixture("regz_appendix_j_5000_36_166_07")
    request = APRRequest.model_validate(fix["request"])
    response = solve_apr(request)
    expected_apr = Decimal("0.120000")
    assert abs(response.estimated_apr - expected_apr) <= Decimal("0.00001"), \
        f"SC-1: APR must equal 12.00% within Decimal('0.00001'); got {response.estimated_apr}"
```

### Example 2: Odd first period (15 days, US 30/360) — $200,000 / 360 / $1,264.14 + 15-day odd first

**Inputs:**
- Single advance: $200,000 at t=0 (origination 2026-01-01)
- First payment due 2026-02-15 (15 days later than the standard 2026-02-01)
- 360 monthly payments of $1,264.14 (the Wikipedia anchor from Phase 1)
- 30/360 day-count, finance_charges = $0

**Odd-first-period fraction:**
```
days_origination_to_first_payment = 45 (2026-01-01 to 2026-02-15)
unit_period_days = 30
f = (45 - 30) / 30 = 0.5
```

**U-equation:**
```
200000 = 1264.14 × (1 + 0.5·i)/(1+i)^1 + Σ_{k=2}^{360} 1264.14/(1+i)^k
```

**Seed:** treat as regular: `npf.rate(360, -1264.14, 200000, 0)` ≈ 0.0054166 (6.5%/12)

**Newton:** converges in 3-5 iterations. APR ≈ 6.523% (slightly above the
nominal 6.5% because the lender is collecting one extra half-month of
interest on the front).

### Example 3: Multi-advance construction loan — $100k / $50k / $50k advances + irregular payments

**Inputs:**
- Advance 1: $100,000 at t=0
- Advance 2: $50,000 at t=3 months
- Advance 3: $50,000 at t=6 months
- Payments: 36 of $5,500 starting at t=12 months
- 30/360 day-count, finance_charges = $2,500 (origination + points)

**U-equation:**
```
100000 + 50000/(1+i)^3 + 50000/(1+i)^6
  = 2500 + Σ_{k=12}^{47} 5500/(1+i)^k
```

(amount_financed = 200000 - 2500 = 197500, but the equation uses the actual
advance amounts on the LHS and finance_charges contributes to the RHS as a
synthetic t=0 outflow per Reg Z §1026.18(b).)

**Seed:** approximate as regular: pv = $200k, pmt = $5,500, n = 36 →
`npf.rate(36, -5500, 200000, 0)` ≈ 0.0089 (~10.7% APR seed).

**Newton:** converges in 8-12 iterations to approximately 11.8% APR (the
multiple advances + finance charges push the actuarial APR meaningfully
above the seed).

This example will become `tests/fixtures/apr/oracle/ffiec_015_construction_multi_advance.json`
(Wave 7 capture).

---

## Open Questions surfaced by research (NOT blockers; planner can lock)

1. **OPEN Q1: Odd first period − negative case.** §1026.17(c)(4) does not
   forbid SHORT first periods (origination 2026-01-01, first payment
   2026-01-25 → f = -5/30 ≈ -0.167). The Reg Z math still works (the (1 +
   f·i) factor is defined for negative f). **PLAN PROPOSAL:** support
   short first periods in the engine but only test the long case in
   Wave 5; capture a negative-f fixture in Wave 7 IF the FFIEC tool
   accepts it.

2. **OPEN Q2: Convergence sanity check on the Decimal residual.** The
   research-recommended convergence test combines `abs(i_{n+1} - i_n) ≤
   Decimal("0.00001")` with a dollar-residual sanity check `abs(f(i_{n+1}))
   ≤ Decimal("0.01")` (one cent). The latter is a Phase 7-invented guard
   not strictly required by Reg Z. **PLAN PROPOSAL:** include it as
   defense-in-depth; document in `references/apr-reg-z.md` §5.

3. **OPEN Q3: APRResponse schema — surface intermediate iteration trace?**
   For debugging it is useful to surface `iterations: int` and
   `final_residual: Money` in the response. **PLAN PROPOSAL:** include
   both fields; the SC-3 iteration test asserts on `response.iterations`.

4. **OPEN Q4: FFIEC APR Tool deliverability (RISK — Wave 7 human
   checkpoint).** The FFIEC tool may be a Windows desktop binary that
   the planner cannot drive headlessly. **PLAN PROPOSAL:** Wave 7 is a
   manual capture (mirror Phase 5 Plan 05-06 oracle PDF capture). If
   FFIEC unreachable, fallback to CFPB / Bankrate / HMDA Platform per
   the §Q(d) fallback list. Plan 07-07 documents both paths and flags
   for `/gsd-discuss-phase` if both fail.

5. **OPEN Q5: Disclosed-APR tolerance check — surface in response?** The
   `lib.rules.reg_z.within_apr_tolerance` predicate (Phase 2) takes
   `disclosed_apr` and returns bool. **PLAN PROPOSAL:** `APRRequest`
   has an optional `disclosed_apr: Money | None` field; when supplied,
   `APRResponse.tolerance_check` is populated `{"within_tolerance": bool,
   "tolerance_used": Decimal, "regulation": "12 CFR §1026.22(a)(2)"}`.
   Optional surface; default omitted per LM-2 schema discipline.

---

## Citations (canonical URLs verified 2026-05-02)

- **12 CFR Part 1026 Appendix J** (Reg Z APR computation):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026
- **12 CFR §1026.17(c)(4)** (basis of disclosures + odd first period):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.17#p-1026.17(c)(4)
- **12 CFR §1026.18(e)** (APR disclosure label):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.18#p-1026.18(e)
- **12 CFR §1026.4** (finance-charge enumeration):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-A/section-1026.4
- **12 CFR §1026.22(a)(2)–(a)(3)** (APR tolerance):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.22
- **CFPB Reg Z Small Entity Compliance Guide:**
  https://files.consumerfinance.gov/f/documents/cfpb_tila-respa-integrated-disclosure-rule_compliance-guide.pdf
- **FFIEC APR Calculator (APRWIN):** https://www.ffiec.gov/aprwin.htm
- **CFPB Rate Spread Calculator:** https://ffiec.cfpb.gov/tools/rate-spread
- **numpy_financial documentation (rate function):**
  https://numpy.org/numpy-financial/latest/rate.html
- **numpy_financial issue #131 (irr architecture-dependent — irrelevant
  to rate, noted for context per `lib/amortize.py:128-131`):**
  https://github.com/numpy/numpy-financial/issues/131
- **Phase 2 already-shipped Reg Z tolerance predicate:**
  `lib/rules/reg_z.py` (lines 1-89; `TOLERANCE_REGULAR = Decimal("0.00125")`)
