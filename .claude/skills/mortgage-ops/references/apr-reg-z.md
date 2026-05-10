# Estimated APR — mortgage-ops Phase 7 Reference

This document records the conventions implemented by `lib/apr.py`
(Phase 7 estimated APR Newton-Raphson solver) and pairs each convention
with its regulatory citation. All section numbers and URLs were verified
on 2026-05-02 against the live eCFR + CFPB explainer (per
`07-RESEARCH.md` §Citations).

Cited from:
- `lib.apr.APRRequest.__doc__` (D-29 cite-from contract — pinned by
  `tests/test_apr.py::test_references_apr_reg_z_doc_present_with_required_sections`)
- `lib/apr.py` module docstring D-04, D-15..D-18 cross-references
- ROADMAP § Phase 7 SC-5 (estimated-APR reference doc)

This file is the headline reference for the Phase 7 conventions; the
six numbered sections below are the load-bearing surfaces every
downstream consumer (Claude skill in Phase 10, Phase 8 stress wrappers,
Phase 11 evals) reads.

---

## 1. Unit-Period Model (12 CFR Part 1026 Appendix J)

The actuarial APR is the periodic rate `i` per unit period that
satisfies the Reg Z Appendix J §(b)(1)–(b)(5) "U-equation":

```
Σⱼ [Aⱼ × (1 + fⱼ·i) × (1+i)^(-tⱼ)]  =  Σₖ [Pₖ × (1 + gₖ·i) × (1+i)^(-sₖ)]
```

where:

| Symbol  | Meaning |
|---------|---------|
| `Aⱼ`    | the j-th advance amount (Decimal dollars) |
| `tⱼ`    | the j-th advance's full unit-period offset from origination |
| `fⱼ`    | the j-th advance's fractional unit-period component (in [0, 1)) |
| `Pₖ`    | the k-th payment amount (Decimal dollars) |
| `sₖ`    | the k-th payment's full unit-period offset from origination |
| `gₖ`    | the k-th payment's fractional unit-period component (in [0, 1)) |
| `i`     | the periodic rate per unit period (Decimal; the unknown) |

**APR is then `i × unit_periods_per_year`** (12 for monthly mortgages —
the Phase 7 default per D-03; settable in [1, 365] for non-monthly
products like biweekly stress paths in Phase 8+).

**Engine surface:** `lib.apr._unit_period_equation(rate, request)`
returns `f(i)` = LHS − RHS as a Decimal residual. `lib.apr._derivative`
returns the closed-form `f'(i)`. `lib.apr.solve_apr` runs Newton-Raphson
on these in pure Decimal.

### Collapse to the regular-PV case

For a regular monthly mortgage with no odd first period (every advance
has `t=0, f=0`; every payment has `s=k` for k=1..n with `g=0`), the
U-equation collapses to the standard present-value equation:

```
loan_amount = pmt × ((1 - (1+i)^(-n)) / i)
```

— exactly the equation `numpy_financial.rate(nper, pmt, pv)` solves.
Phase 7 uses `npf.rate` as the **seed** for Newton-Raphson (see §5
below); the Newton step is then a one-or-two-iteration polish (the SC-1
anchor converges in 1 iteration).

### Multi-advance and irregular schedules

`APRRequest.advance_schedule: list[AdvanceScheduleEntry]` accepts
multiple advances with arbitrary `unit_period_offset` and
`unit_period_fraction` per entry, and `payment_schedule:
list[PaymentScheduleEntry]` accepts grouped payment runs (each entry
carries `amount`, `periods`, `unit_period_offset`,
`unit_period_fraction`). The U-equation form generalizes naturally; the
Newton iteration handles arbitrary schedules without a separate code
path. v1 cross-validation only covers single-advance fixtures (Phase 7
LOCKED D-04 in 07-CONTEXT.md); the U-equation form means relaxing that
bound is a config change (drop `max_length=1`) without an engine
rewrite. See §7 v1 carve-outs in this file's neighbor doc
`references/refi-npv.md` for the analogous "engine ready, fixtures
constrained" pattern Phase 6 used.

**Citations:**
- 12 CFR Part 1026 Appendix J §(b)(1)–(b)(5) — eCFR (verified 2026-05-02):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026
- 12 CFR §1026.18(b) (amount-financed disclosure):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.18

---

## 2. Day-Count Conventions

Reg Z does NOT mandate a single day-count convention; the lender's
choice governs (12 CFR §1026.17(c)(4)). Whatever convention the lender
used to compute the finance charge MUST also be used to compute the
fractional unit-period factors `f` and `g` in the U-equation.

Phase 7 supports three conventions, defaulting to US 30/360 (the FFIEC
APR Tool default per RESEARCH §Q(b)):

| Convention      | Unit-period days (monthly) | Use case                                     |
|-----------------|----------------------------|----------------------------------------------|
| `30/360`        | 30 (every month)           | Default for closed-end mortgages (US convention) |
| `actual/365`    | 365 / 12 ≈ 30.4167         | Some adjustable-rate products                |
| `actual/actual` | days(orig → orig+1mo)      | Treasury convention; rare for mortgages     |

**Engine surface:**
`APRRequest.day_count: Literal["30/360", "actual/365", "actual/actual"] = "30/360"`.
The Pydantic boundary rejects any string outside the Literal. The same
Literal flows into `lib.apr._compute_odd_first_period_fraction` and is
honored throughout the Newton iteration's per-period exponent
computation.

### v1 cross-validation scope

v1 hand-calc fixtures (`tests/fixtures/apr/regz_appendix_j_*.json`) all
use `"30/360"`. The 20+ HMDA Platform oracle fixtures (Plan 07-07 /
Wave 7) also use `"30/360"`. The other two conventions are accepted at
the Pydantic boundary and exercised by `_compute_odd_first_period_fraction`
unit tests, but no oracle cross-validation fixture targets them in v1
(documented in 07-CONTEXT.md "Deferred Ideas"). Future work: ship
additional oracle fixtures for `actual/365` and `actual/actual` when an
ARM or treasury product demands it.

### "Small differences" non-treatment (D-18)

§1026.17(c)(4) permits creditors to disregard small differences (< 7
days for monthly) when computing fractional unit periods. **Phase 7 does
NOT auto-zero small fractions** — the engine reports the exact computed
`f` per the day-count formula. Callers (or future Phase 8 stress
wrappers) may zero small fractions before passing to the engine; the
engine itself stays mathematically faithful to the days as supplied.

**Citations:**
- 12 CFR §1026.17(c)(4) (basis of disclosures + day-count + odd-first-period):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.17
- 12 CFR Part 1026 Appendix J §(b)(5)(iii) (fractional unit periods —
  see URL §1).

---

## 3. Odd First Period Handling (§1026.17(c)(4))

When the first payment is more than one full unit period after
origination (the "long first period" case), the additional days form a
"fractional unit period" denoted `f`:

```
f = (days_origination_to_first_payment - unit_period_days) / unit_period_days
```

This `f` factor enters the U-equation as the simple-interest term
`(1 + f·i)` on the first payment. (Reg Z prescribes simple interest
within a fractional period, NOT compound interest — Appendix J §(b)(5)(iii).)

### Day-count-specific formulas

For the three v1-supported day-count conventions:

| Convention      | Unit-period days | Formula                                           |
|-----------------|------------------|---------------------------------------------------|
| `30/360`        | 30               | `f = (days - 30) / 30` (US convention)            |
| `actual/365`    | 365 / 12 ≈ 30.4167 | `f = (days - 30.4167) / 30.4167`                |
| `actual/actual` | days(orig→orig+1mo) | `f = (days - actual_days_in_unit_period) / actual_days_in_unit_period` |

### Engine surfaces

- **Helper:** `lib.apr._compute_odd_first_period_fraction(origination,
  first_payment, day_count)` — accepts the same three-Literal
  `day_count`; returns `Decimal` in `[-1, 1)` per Reg Z §1026.17(c)(4)
  (D-15).
- **User shortcut:** `APRRequest.odd_first_period_days: int = 0` — the
  engine internally rewrites `payment_schedule[0].unit_period_fraction`
  from this integer day count (D-17). Advanced callers bypass by setting
  `unit_period_fraction` directly on the `PaymentScheduleEntry` and
  leaving `odd_first_period_days=0` (e.g., Phase 8 stress callers using
  `_compute_odd_first_period_fraction` with explicit dates).

### Long case (positive `f`) — supported and cross-validated

Long first periods (`f ∈ [0, 1)`) are the standard case for retail
mortgages where the first payment falls 30–60 days after origination.
The 15-day fixture `tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json`
pins `odd_first_period_days=15` (so `f = (45 - 30) / 30 = 0.5`); engine
emits APR `0.065002` in 2 Newton iterations (D-24 engine-emitted value
per Plan 07-05 D-24).

### Negative case (short first period, negative `f`)

§1026.17(c)(4) does NOT forbid SHORT first periods (origination
2026-01-01, first payment 2026-01-25 → `f = -5/30 ≈ -0.167`). The
`(1 + f·i)` factor algebra is well-defined for negative `f`, and the
engine accepts `f ∈ [-1, 0)`; v1 fixtures cover only positive `f`
(documented as "not extensively tested in Phase 7" per 07-RESEARCH OPEN
Q1 + 07-CONTEXT.md "Claude's Discretion"). When ARM or short-fuse closing
scenarios drive demand, capture short-`f` HMDA Platform fixtures and add
parametric coverage.

### Long-long case (`f >= 1` — rejected at boundary, D-16)

When `odd_first_period_days >= unit_period_days` (e.g., 45 days with the
30/360 default), the implied `f >= 1` violates the Appendix J §(b)(5)(iii)
single-fractional-unit-period assumption. **The engine raises
`ValueError`** at `_compute_odd_first_period_fraction` (or at the
`solve_apr` rewrite step when `odd_first_period_days` is supplied).
Callers should insert an extra advance entry instead of stretching the
first period across multiple unit periods. Pinned by the negative-path
fixture `tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json`
+ sibling `test_odd_first_period_too_long_raises` per Plan 07-05 D-26.

**Citation:**
- 12 CFR §1026.17(c)(4) — see URL §2.

---

## 4. Worked Example — Reg Z Appendix J Example J(c)(1)

The SC-1 anchor pins the Reg Z Appendix J §(c)(1) published example end
to end through `lib/apr.py` and the JSON fixture surface. Any
engine-output divergence from `Decimal("0.120000")` exceeding
`Decimal("0.00001")` is a P0 release blocker per Plan 07-05 D-25 LOCKED.

### Inputs (regulatory-publication values)

```
loan_amount       : $5,000.00 (single advance at t=0)
finance_charges   : $0.00 (entire $5,000 is financed)
payment_schedule  : 36 monthly payments of $166.07
day_count         : "30/360"
odd_first_period_days : 0 (no odd first period)
unit_periods_per_year : 12 (monthly)
```

### U-equation collapses to standard PV

With no odd first period and no finance charges:

```
5000 = Σ_{k=1}^{36} 166.07 / (1+i)^k
     = 166.07 × ((1 - (1+i)^(-36)) / i)
```

### Seed via `numpy_financial.rate`

```
seed = npf.rate(nper=36, pmt=-166.07, pv=5000, fv=0) ≈ 0.0099991
```

(approximately 1%/month — already very close to the regulatory
solution; the seed is essentially exact for this regular-transaction
case.)

### Newton iterations

| Iter | i              | f(i) (residual, $) | Notes                          |
|------|----------------|--------------------|--------------------------------|
| 0    | 0.0099991...   | ~0.04              | seed from `npf.rate`           |
| 1    | 0.00999998...  | ~0                 | converged within tolerance     |

### Result

```
i_converged = Decimal("0.009999...")
APR         = quantize_rate(i × 12) = Decimal("0.120000") = 12.00%
iterations  = 1
final_residual ≈ Decimal("0.000006") (< Decimal("0.00001"))
```

**Engine emits `0.119994` in the actual run; |engine − regulatory| =
`Decimal("0.000006")` (within SC-1 tolerance `Decimal("0.00001")`).**
The fixture `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json`
pins `expected.estimated_apr = "0.120000"` (the regulatory-publication
value, NOT the engine-emitted value, per Plan 07-05 D-25 LOCKED).
The test `test_apr_reg_z_appendix_j_worked_example_returns_12_percent`
asserts `abs(response.estimated_apr - Decimal("0.120000")) <= Decimal("0.00001")`.

### Why the regulatory anchor stays anchored

D-25 LOCKED establishes the regulatory-anchor exception to the engine-
emitted-value default (which Phase 7's other hand-calc fixtures use per
D-24). The SC-1 anchor stays anchored to the regulation, NOT the engine
— any future engine drift > `Decimal("0.00001")` from `0.120000` is a
P0 release blocker pinned by this test. The other 20+ HMDA Platform
oracle fixtures (Wave 7) cross-validate engine output against the HMDA
Platform reference impl per CONTEXT D-09 ("HMDA delta policy — engine is
wrong" if divergence > `Decimal("0.00001")`).

**Citation:**
- 12 CFR Part 1026 Appendix J §(c)(1) — eCFR (verified 2026-05-02):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026

---

## 5. Newton-Raphson Convergence

Phase 7 uses standard Newton-Raphson root-finding on the U-equation
residual `f(i)`. The algorithm is:

```
i_{n+1} = i_n - f(i_n) / f'(i_n)
```

iterated until BOTH convergence criteria below are satisfied (D-06
dual-criterion).

### Seed strategy (D-02 / APR-02)

The seed comes from `numpy_financial.rate` treating the loan as a
regular transaction:

```python
seed = Decimal(str(npf.rate(
    nper=sum(p.periods for p in payments),
    pmt=-float(mean_payment_amount),
    pv=float(sum_of_advances),
    fv=0,
)))
```

For a regular fixed-rate mortgage this seed is correct to machine
precision; Newton converges in 1–2 iterations (the SC-1 anchor: 1
iteration). For irregular schedules (multi-advance, odd first period,
mixed payment runs) the seed is approximate; Newton converges in 5–15
iterations empirically per RESEARCH §Q(c).

**Fallback:** if `npf.rate` returns NaN or a value outside `[0, 1]`
(ill-conditioned input), the seed falls back to a nominal-rate-of-return
estimate `total_interest / pv / n`. This path is exercised in the engine
unit tests; v1 fixtures don't trigger it.

**numpy_financial issue #131 note:** the architecture-dependent IRR bug
in `numpy_financial.irr` does NOT apply to `numpy_financial.rate`, which
uses a deterministic Newton iteration. Phase 7 uses `npf.rate` for the
seed and never `npf.irr` (per `lib/amortize.py:128-131` precedent
inherited from Phase 3; same precedent Phase 6 D-06 cites for breakeven).

### Tolerance

```
TOLERANCE      = Decimal("0.00001")     # rate convergence (SC-1 anchor)
DOLLAR_RESIDUAL = Decimal("0.01")       # 1-cent residual sanity (D-10)
```

`Decimal("0.00001")` is **125x tighter** than Reg Z §1026.22(a)(2) regular
tolerance `Decimal("0.00125")` (1/8 percentage point). The "10x tighter
than Reg Z" goal in ROADMAP is a min-floor; SC-1 exceeds it by 12.5x.
RESEARCH §Finding 1 reconciles the orchestrator brief's decimal-point
typo ("0.0125%" → actual: 0.125% = `Decimal("0.00125")` fractional).

### Convergence test (D-06 dual-criterion)

Newton terminates only when BOTH:

1. `abs(i_{n+1} - i_n) <= Decimal("0.00001")` — rate tolerance (SC-1).
2. `abs(f(i_{n+1})) <= Decimal("0.01")` — dollar-residual sanity guard
   (Phase 7-invented defense in depth, NOT Reg Z required).

Prevents the "rate stalled, residual huge" edge case (a degenerate
schedule where consecutive iterates happen to be close but the equation
isn't actually satisfied). `APRResponse.final_residual` surfaces the
second criterion's value (D-05) for debugging.

### Iteration cap (D-07 / SC-3)

```
MAX_ITERATIONS = 50
```

The engine raises `APRConvergenceError(ValueError)` when the cap is
exceeded, with iteration count + last residual in the message. The
`APRResponse.iterations` field is `Field(ge=1, le=50)` — the Pydantic
boundary refuses to construct a malformed response with iterations > 50,
defense in depth against a future bug. Pinned by
`test_apr_solver_raises_on_non_convergence` and the SC-3 sweep
`test_newton_raphson_iterations_under_50_for_all_fixtures`.

### Decimal vs. float discipline

The entire Newton iteration runs in `with localcontext(MONEY_CONTEXT)`
(prec=28). The seed is the only float→Decimal transition (cast through
`Decimal(str(seed))`). `mypy --strict` enforces no other float in the
engine; the load-bearing helper for fractional exponents is:

```python
def _decimal_pow(base: Decimal, exponent: Decimal) -> Decimal:
    """Compute base ** exponent via (base.ln() * exponent).exp()."""
    with localcontext(MONEY_CONTEXT):
        if base <= Decimal("0"):
            raise ValueError(...)
        return (base.ln() * exponent).exp()
```

Native `Decimal.__pow__` only supports integer exponents reliably; for
fractional `t + f` the exp/ln route preserves full prec=28. A `prec=50`
localcontext is NOT needed — verified empirically against Reg Z Appendix
J Example J-1 (RESEARCH §Finding 7).

**Sanity guard:** `test_decimal_pow_fractional_exponent_correctness`
pins `_decimal_pow(2, 0.5) ≈ sqrt(2)` within `Decimal("0.0000001")`.
Catches order-of-magnitude regressions in the load-bearing helper
before the SC-1 anchor test runs (cheaper failure surface).

### Iteration logging

The engine emits a structured `logging.debug(...)` line per iteration
with `(iteration, current_rate, residual)`. Off by default; surfaces
under `LOG_LEVEL=DEBUG`. Not exposed in `APRResponse`. Useful for
diagnosing slow-convergence fixtures during development.

**Citations:**
- 12 CFR §1026.22(a)(2)–(a)(3) (Reg Z APR tolerance):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.22
- numpy_financial documentation (`rate` function):
  https://numpy.org/numpy-financial/latest/rate.html
- numpy_financial issue #131 (IRR architecture-dependent — irrelevant to
  `rate`, noted for context):
  https://github.com/numpy/numpy-financial/issues/131

---

## 6. Citations Summary (verified 2026-05-02)

Primary regulatory references (eCFR / CFPB; verification cadence: annual
per the Phase 2 staleness convention):

- **12 CFR Part 1026 Appendix J** (Reg Z APR computation — the binding
  algebra):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026
- **12 CFR §1026.17(c)(4)** (basis of disclosures + day-count + odd-first-period):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.17
- **12 CFR §1026.18(b), (e)** (amount-financed disclosure + APR
  disclosure label):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.18
- **12 CFR §1026.4** (finance-charge enumeration; Phase 7 does NOT
  classify, but cites for reader reference per D-04):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-A/section-1026.4
- **12 CFR §1026.22(a)(2)–(a)(3)** (APR tolerance — encoded in
  `lib/rules/reg_z.py` Phase 2 + cross-referenced by
  `APRResponse.tolerance_check` per D-08):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.22

CFPB explainer + tool oracles:

- **CFPB TILA-RESPA Integrated Disclosure Rule Compliance Guide:**
  https://files.consumerfinance.gov/f/documents/cfpb_tila-respa-integrated-disclosure-rule_compliance-guide.pdf
- **FFIEC APR Calculator (APRWIN; out-of-scope as oracle per D-02 — see
  07-CONTEXT.md):** https://www.ffiec.gov/aprwin.htm
- **CFPB Rate Spread Calculator (FFIEC fallback for spot checks):**
  https://ffiec.cfpb.gov/tools/rate-spread
- **HMDA Platform (sole oracle per D-01 — see 07-CONTEXT.md; pinned by
  `oracle_commit_sha` in Plan 07-07 fixtures):**
  https://github.com/cfpb/hmda-platform

Library + tooling references:

- **numpy_financial v1.0.0 documentation (`rate` function):**
  https://numpy.org/numpy-financial/latest/rate.html
- **numpy_financial issue #131** (IRR architecture-dependent — Phase 7
  uses `rate` not `irr`; mirrors Phase 3 + Phase 6 D-06):
  https://github.com/numpy/numpy-financial/issues/131

Cross-phase / internal references:

- **Phase 1 money discipline** — `lib/money.py` (MONEY_CONTEXT,
  `quantize_cents`, `quantize_rate`, `to_money`).
- **Phase 2 Reg Z tolerance predicate** — `lib/rules/reg_z.py:1-89`
  (`within_apr_tolerance`, `TOLERANCE_REGULAR = Decimal("0.00125")`,
  `TOLERANCE_IRREGULAR`); the predicate's docstring already references
  "Phase-7 consumer" (line 43).
- **Phase 4 affordability seed-then-refine archetype** —
  `lib/affordability.py::evaluate_reverse` (the closest precedent for
  Phase 7's seed-then-Newton structure; `npf.pv` seed → MI estimate →
  final solve generalized to `npf.rate` seed → Newton iterate).
- **Phase 5 ARM-mechanics doc precedent** — `references/arm-mechanics.md`
  (six-section template inheritance per D-28 LOCKED in this plan; same
  cite-from contract idiom as `ARMTerms.__doc__` → `references/arm-mechanics.md`).
- **Phase 6 refi-NPV doc precedent** — `references/refi-npv.md` (closest
  same-shape sibling for sectioned reference docs; D-16 "belt and
  suspenders" multi-surface idiom inspires this doc's cite-from contract
  with `lib/apr.py`).

### Phase 7 LOCKED DECISIONS cross-reference

For full text, see `.planning/phases/07-estimated-apr/07-CONTEXT.md` and
the per-plan PLAN.md LOCKED DECISIONS sections. Brief cross-references
that surface in this document:

| Decision | Cross-reference                                                        | Section in this doc |
|----------|------------------------------------------------------------------------|---------------------|
| D-01     | HMDA Platform sole oracle (07-CONTEXT.md)                              | §6                  |
| D-02     | FFIEC APRWIN out of scope as oracle (07-CONTEXT.md)                    | §6                  |
| D-04     | Caller-supplied `finance_charges` (orchestrator-locked)                | §1                  |
| D-09     | HMDA delta policy: engine is wrong if `> Decimal("0.00001")`           | §4                  |
| D-15     | `_compute_odd_first_period_fraction` returns Decimal in [-1, 1)        | §3                  |
| D-16     | `f >= 1` raises ValueError (caller inserts extra advance)              | §3                  |
| D-17     | `odd_first_period_days` integer shortcut on `APRRequest`               | §3                  |
| D-18     | "Small differences" not auto-zeroed by engine                          | §2                  |
| D-25     | SC-1 anchor pinned at regulatory `0.120000`, NOT engine value          | §4                  |
| D-28     | Six-section template inherited from `references/arm-mechanics.md`      | (this section)      |
| D-29     | Cite-from contract: `APRRequest.__doc__` cites this file               | (this section)      |
| D-30     | All citation URLs verified 2026-05-02 against eCFR + CFPB              | §6                  |

---

## Appendix — Citation Index

| URL                                                                                                                                            | Section / Anchor                                       | Last verified |
|------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|---------------|
| https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026                                                 | Reg Z Appendix J — U-equation + worked example         | 2026-05-02    |
| https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.17                                               | §1026.17(c)(4) — basis + day-count + odd-first-period  | 2026-05-02    |
| https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.18                                               | §1026.18(b), (e) — amount financed + APR disclosure    | 2026-05-02    |
| https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-A/section-1026.4                                                | §1026.4 — finance-charge enumeration                   | 2026-05-02    |
| https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.22                                               | §1026.22(a)(2)–(a)(3) — APR tolerance                  | 2026-05-02    |
| https://files.consumerfinance.gov/f/documents/cfpb_tila-respa-integrated-disclosure-rule_compliance-guide.pdf                                  | CFPB TILA-RESPA Compliance Guide                       | 2026-05-02    |
| https://www.ffiec.gov/aprwin.htm                                                                                                               | FFIEC APR Calculator (APRWIN — out of scope per D-02)  | 2026-05-02    |
| https://ffiec.cfpb.gov/tools/rate-spread                                                                                                       | CFPB / FFIEC Rate Spread Calculator                    | 2026-05-02    |
| https://github.com/cfpb/hmda-platform                                                                                                          | HMDA Platform (sole oracle per D-01)                   | 2026-05-02    |
| https://numpy.org/numpy-financial/latest/rate.html                                                                                             | numpy_financial.rate documentation                     | 2026-05-02    |
| https://github.com/numpy/numpy-financial/issues/131                                                                                            | numpy-financial issue #131 (IRR arch-dependent)        | 2026-05-02    |

Annual re-validation cadence: each calendar year, confirm each URL still
resolves; if any have moved, update the index above and the §6 inline
references.
