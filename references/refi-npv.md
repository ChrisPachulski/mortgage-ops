# Refinance NPV — Borrower-Perspective Conventions (REFI-09 / SC-5)

This document records the borrower-perspective sign convention, NPV
derivation, breakeven definitions, and after-tax-mode optionality
implemented by `lib/refinance.py` (Phase 6 refinance NPV engine).
Every section pairs an engine convention with the regulatory or
academic citation that justifies it.

Cited from:
- `lib.refinance` module docstring (D-04 + D-16 belt-and-suspenders surface 2)
- `RefiCashflow._direction_sign_consistency` ValidationError messages (D-16 surface 1)
- `scripts/refi_npv.py --help` epilog (ROADMAP SC-5 mandate; D-16 surface 4)

This file is D-16 surface 3 — the headline reference.

All section numbers and URLs were verified on 2026-05-02 against the
live Investopedia / Federal Reserve / CFPB / IRS / numpy-financial
sources. Annual re-validation cadence: each calendar year, confirm
each URL still resolves; if any have moved, update §8 Citations.

---

## 1. Sign Convention — outflows negative, savings positive

The Phase 6 refinance NPV engine takes the **borrower's perspective**:
outflows negative, savings positive. This single sentence is the
load-bearing convention for every cashflow that enters
`numpy_financial.npv` and the `RefiCashflow` Pydantic model — and the
literal phrase is enforced verbatim by ROADMAP § Phase 6 SC-5.

What this means concretely:

| Cashflow | Direction | Sign | Example |
|---|---|---|---|
| Closing costs paid at refi origination | outflow | negative | $2,000 closing → `Decimal("-2000.00")` |
| Monthly P&I savings (old_pi - new_pi > 0) | inflow | positive | $367/mo savings → `Decimal("+366.57")` |
| Cash proceeds from cash-out refi | inflow | positive | $50k cash less $3k closing → `Decimal("+47000.00")` |
| Monthly payment delta (new_pi > old_pi for cash-out) | outflow | negative | +$66/mo new payment → `Decimal("-66.02")` |
| Tax shield (after-tax mode opt-in) | inflow | positive | $300/mo deductible interest × marginal rate → `Decimal("+300.00")` |

The convention is enforced at THREE layers, defense in depth:

1. **`RefiCashflow` Pydantic model** rejects sign-direction mismatches
   at construction time. An outflow with positive amount or an inflow
   with negative amount raises `ValidationError`. Zero is accepted in
   either direction (Phase 6 D-14: no sign hazard at zero). Source:
   `lib/refinance.py::RefiCashflow._direction_sign_consistency`.
2. **`evaluate(req)` engine layer** never bypasses the model — every
   cashflow flowing into `numpy_financial.npv` has been
   construction-validated. Engine code paths build cashflows by
   constructing `RefiCashflow` instances explicitly so any sign bug
   surfaces at the model boundary, not silently inside the NPV math.
3. **CLI / response layer** reports signed Decimal values verbatim;
   the JSON consumer (Claude skill, downstream notebooks, Phase 11
   refi-npv-agent) sees the borrower-perspective signs directly.

### Worked example — sign convention in action

A 30-year refi at a 200bps rate drop with $2,000 closing costs (Oracle 1
from `06-RESEARCH.md`):

```
old_loan: $300,000 @ 7.0% / 25 years remaining → old_pi = $2,120.34
new_loan: $300,000 @ 5.0% / 25 years           → new_pi = $1,753.77
monthly_savings = old_pi - new_pi              = +$366.57

Cashflows (length 301: t=0..300, signed Decimal):
  t=0:        -2000.00     (closing costs OUTFLOW)
  t=1..300:   +366.57 each (monthly savings INFLOW)

NPV(rate=0.05/12, cashflows) = +$60,705.48 (positive — refi wins)
```

The literal sign-convention phrase **outflows negative, savings positive**
appears in:
- this section (§1, headline)
- `lib/refinance.py` module docstring opening sentence
- `scripts/refi_npv.py --help` epilog
- `RefiCashflow` validator error messages

So a grep across the codebase for the verbatim phrase returns four
hits, each documenting the same contract from a different surface.

**Citations:**
- Investopedia "Net Present Value (NPV)" — sign convention reference for
  retail-investor NPV calculations: https://www.investopedia.com/terms/n/npv.asp
- Federal Reserve "Consumer's Guide to Mortgage Refinancing" — borrower-
  perspective framing ("compare expected savings to closing costs"):
  https://www.federalreserve.gov/pubs/refinancings/

---

## 2. Borrower NPV Formula

The canonical refi NPV formula (borrower POV, monthly compounding):

```
NPV = Σ ( CF_t / (1 + r/m)^t )    for t = 0 to N
```

where:
- `CF_t` — per-period signed cashflow at period t (Decimal). t=0 is the
  refi origination instant (closing costs and cash proceeds). t=1..N are
  monthly periods following.
- `r` — annual discount rate (Decimal in [0,1]; e.g. `Decimal("0.05")` =
  5.00%). REQUIRED on `RefiRequest` per D-05.
- `m` — periods per year. Phase 6 v1 = 12 (monthly compounding). Biweekly
  refi NPV is OUT of v1 scope.
- `N` — analysis horizon in periods. Default = `new_loan.term_months`.
  Caller may set `analysis_horizon_months` to truncate the cashflow
  stream (D-11 + D-13 — see §5 below).

### Phase 6 implementation primitive

The engine wraps `numpy_financial.npv(rate, values)` with the documented
quirk that `values[0]` is the t=0 cashflow (NOT t=1). This matches the
formula above when `values = [CF_0, CF_1, ..., CF_N]`. Phase 3 D-04
verified empirically that `numpy_financial==1.0.0` returns `Decimal`
when fed `Decimal` cashflow inputs; Phase 6 inherits this discipline
and never falls back to `float`.

Helper layer in `lib/refinance.py`:

| Helper | Purpose |
|---|---|
| `_compute_npv(discount_rate_annual, cashflows)` | Wraps `npf.npv` with Decimal discipline; quantizes only at boundary |
| `_build_cashflow_stream(...)` | Constructs the `list[RefiCashflow]` stream from request inputs; honors `analysis_horizon_months` truncation |
| `_build_old_loan_residual(loan)` | Synthesizes a Loan representing the OLD loan's remaining balance + remaining term (for residual P&I + interest computation) |
| `_compute_breakeven_simple(closing_costs, monthly_savings)` | Simple breakeven (REFI-03); returns `(months: int|None, status: Literal[...])` |
| `_compute_breakeven_npv(rate, cashflows)` | Cumulative-NPV scan (D-06; NOT npf.irr — bug #131) |

### Quantization discipline

Per CLAUDE.md FND-01 + Phase 5 D-14:
- **Decimal context**: 28-digit precision throughout intermediate NPV computation.
- **`quantize_cents`** (2 decimal places, ROUND_HALF_UP): applied ONCE at the
  final `RefiResponse.npv` boundary. Never mid-calculation.
- **`quantize_rate`** (6 decimal places, ROUND_HALF_UP): applied ONCE to the
  caller-supplied `discount_rate_annual` at request entry; used unchanged
  throughout the cashflow / NPV pipeline.

**Citation:**
- Investopedia "Net Present Value (NPV)" (formula derivation):
  https://www.investopedia.com/terms/n/npv.asp
- numpy-financial v1.0.0 docs (`npv(rate, values)` signature):
  https://numpy.org/numpy-financial/latest/

---

## 3. Discount-Rate Selection (D-05)

The `discount_rate_annual` field on `RefiRequest` is **REQUIRED**. The
engine has no default. This mirrors Phase 4 D-12 (`max_dti` is caller-
supplied, no default) — the project's "fail loud, no inference" doctrine
applies to every input that materially affects the answer.

Three plausible defaults exist in the academic / industry literature.
None is universally correct; the engine declines to choose for the user.

### Option (a) — Borrower's marginal opportunity cost (RECOMMENDED)

The rate the borrower would earn investing the closing-cost cash in their
next-best alternative. Per Investopedia "NPV in Real Estate" (and broad-
market historical data), a typical retail-investor opportunity cost is
**5-7% nominal** (broad-market equity index after-tax expected return).

For a borrower in their accumulation phase with regular 401(k) /
brokerage contributions, the opportunity cost is the marginal expected
return of that next dollar. Using this as the discount rate makes
"refinance NPV > 0" mean "refi is better than investing the closing
cash in your normal portfolio".

This is the most defensible single number for personal-use household
refi decisions and the recommended default callers should consider when
no scenario-specific reason favors one of the alternatives below.

### Option (b) — Risk-free rate (10-year Treasury or SOFR)

The yield on a roughly term-matched government instrument. Conservative
choice — biases the calculation toward "refi looks worse" because the
savings stream gets less discounting offset relative to the t=0 closing-
cost outflow. Defensible for risk-averse borrowers who treat the
opportunity cost as the floor on a guaranteed return.

### Option (c) — The OLD loan's interest rate

What the borrower is "earning" by paying down debt at that rate (every
extra dollar of principal saves OLD interest). Common in academic
mortgage finance; equates `NPV > 0` to "refinancing dominates doing
nothing else". Conceptually clean but tends to bias high (mortgage rates
are well above risk-free rates), making the savings stream look smaller
in present-value terms.

### Engine choice — caller MUST supply

`RefiRequest.discount_rate_annual: Rate` — REQUIRED, no default. The
engine documents the three options in this section and recommends (a)
"borrower's after-tax marginal opportunity cost (5-7% typical)" but
DOES NOT silently apply any of them. The `--help` epilog of
`scripts/refi_npv.py` repeats the recommendation; the Claude skill (Phase
10) will narrate the choice in human-readable form.

**Citations:**
- Investopedia "Net Present Value (NPV)" — discount-rate selection
  guidance for personal finance: https://www.investopedia.com/terms/n/npv.asp
- Federal Reserve "Consumer's Guide to Mortgage Refinancing" — borrower
  framing of "expected return on alternatives":
  https://www.federalreserve.gov/pubs/refinancings/

---

## 4. Cashflow Inventory: Rate-and-Term vs. Cash-Out

Phase 6's `RefiRequest` is a discriminated union over `refi_kind`:

- `refi_kind="rate_and_term"` → `RateAndTermRefiRequest`
- `refi_kind="cash_out"` → `CashOutRefiRequest`

Each kind has a fully enumerated cashflow inventory.

### 4.1 Rate-and-Term Refi (REFI-01 / REFI-05 / REFI-06)

Same balance, same horizon, lower rate. The borrower's only winnings are
the reduced monthly P&I across the new loan's life.

| Period | Inflow (positive) | Outflow (negative) | Engine `RefiCashflow.kind` |
|---|---|---|---|
| t=0 | (none) | `-closing_costs` | `closing_costs` |
| t=1..N | `+(old_pi - new_pi)` | (none — new P&I is baked into new_pi) | `monthly_savings` |

**Why we don't enumerate "old P&I that stops":** the `old_pi - new_pi`
delta IS the savings; we model the borrower's NET cashflow change, not
two separate streams. This makes the sign convention unambiguous and
matches `numpy_financial.npv`'s single-list signature.

### 4.2 Cash-Out Refi (REFI-02 / REFI-07)

`new_principal > old_balance`. The borrower extracts equity (e.g., $50k
for home improvements). The new loan's principal grows; the new monthly
P&I is typically HIGHER (so the savings stream flips negative); the
benefit is the t=0 cash proceeds.

| Period | Inflow (positive) | Outflow (negative) | Engine `RefiCashflow.kind` |
|---|---|---|---|
| t=0 | `+(new_principal - old_balance) - closing_costs` (CASH PROCEEDS net of costs per industry convention) | (closing costs already netted) | `cash_proceeds` |
| t=1..N | (none in typical cash-out where new_pi > old_pi) | `-(new_pi - old_pi)` (extra payment for the larger principal) | `monthly_payment_delta` |

The dual exposure of `cash_proceeds` (t=0 net inflow) and
`monthly_payment_delta` (t=1..N signed delta) makes SC-3 testable
against hand-calculated values without the borrower needing to reverse-
engineer which side of the netting we used.

**Closing-costs netting convention:** v1 nets closing costs out of the
t=0 cash proceeds, NOT out of monthly cashflows. This matches industry
"Closing Disclosure" (CFPB) conventions where the borrower sees a single
net cash-to-borrower number at signing. D-15 makes `closing_costs` a
top-level `RefiRequest` field; the engine constructs the
`RefiCashflow(period=0, direction='outflow', kind='closing_costs',
amount=-closing_costs)` internally.

**Citations:**
- Federal Reserve "Consumer's Guide to Mortgage Refinancing" — refi
  cashflow framing: https://www.federalreserve.gov/pubs/refinancings/
- CFPB Closing Disclosure Examples — closing-cost itemization
  conventions: https://www.consumerfinance.gov/owning-a-home/closing-disclosure/

---

## 5. Simple vs. NPV-Based Breakeven (REFI-03)

Two breakeven definitions; both reported in `RefiResponse.breakeven`
per ROADMAP SC-2. The engine labels both forms in output JSON so the
consumer never has to guess which one a number refers to.

### 5.1 Simple breakeven

```
simple_breakeven_months = ceil(closing_costs / monthly_savings)
```

where `monthly_savings = old_pi - new_pi` (positive when refi reduces
payment).

Pathological cases (engine returns `(None, status_label)`):
- `monthly_savings <= 0` → `(None, "no_savings")` (cash-out where new_pi
  > old_pi; or rate-and-term where the new rate doesn't actually drop).
- `closing_costs == 0` → `(0, "ok")` — the refi pays for itself
  immediately at t=0.

### 5.2 NPV-based breakeven (D-06; cumulative-NPV scan)

```
For each n in 1..N:
    cumulative_npv_n = npv(rate, cashflows[0:n+1])
    if cumulative_npv_n >= 0:
        return (n, "ok")
return (None, "never_breaks_even")
```

**Why scan, NOT npf.irr:** `numpy_financial.irr` is BROKEN per upstream
bug #131 (architecture-dependent return values). Phase 6 D-06 mandates
the cumulative-NPV scan instead — every iteration uses `numpy_financial.npv`
on an increasingly long prefix, which IS reliable. Plan 06-02 ships
`_compute_breakeven_npv` with this algorithm; the divergence-fixture
oracle below was hand-verified independently of the engine.

### 5.3 Divergence cases (SC-2 anchor)

Simple and NPV-based breakeven diverge whenever the discount rate is
nontrivial relative to the savings horizon. The pinned divergence
oracle (`tests/fixtures/refinance/breakeven_divergence.json`):

```
old_loan: $300k @ 7.0%/30yr → old_pi = $1,995.91
new_loan: $300k @ 6.0%/30yr → new_pi = $1,798.65
monthly_savings = $197.26
closing_costs = $5,000
discount_rate_annual = 0.08  (high — drives divergence)

simple_breakeven_months = ceil(5000 / 197.26) = 26
NPV-breakeven (cumulative scan)            = 28 months
```

The 2-month gap is the discounting drag: at 8% annual discount, future
savings are worth less in present-value terms than their nominal sum,
so it takes longer for the cumulative discounted savings to overcome the
$5k upfront outflow. At very low discount rates (~0.5%), the two values
converge (within rounding). Plan 06-05 ships `breakeven_divergence.json`
as the SC-2 anchor.

### 5.4 Cash-out scenarios

For cash-out refis where the savings stream is negative (`new_pi >
old_pi`), simple breakeven is meaningless and reported as
`(None, "no_savings")`. NPV-based breakeven, however, is typically `0`
because the t=0 `cash_proceeds` inflow is itself ≥ 0 — the borrower
"breaks even" the moment they sign because they walked away with cash.
This is the correct semantic: the borrower's cumulative present-value
change went non-negative immediately at signing.

### 5.5 Horizon truncation (D-11 + D-13 rationale)

The `analysis_horizon_months` field on `RefiRequest` is OPTIONAL. When
None, the engine uses the new loan's full term (e.g., 360 months for a
30-year refi). When supplied, the cashflow stream is truncated to
`t=0..analysis_horizon_months`.

**Why truncation matters for the borrower-decision use case:** real
borrowers move. The FHFA 2023 housing-finance survey reports a median
US homeowner tenure of ~13 years. A refi that "looks great" over 30
years discounted at 5% may be net-negative at the borrower's actual
expected tenure. The horizon-truncation knob lets the consumer model
their realistic decision horizon.

**D-13 specifically:** the SC-1 "negative-NPV fixture" uses
`analysis_horizon_months=12` to satisfy ROADMAP's "(same rate, $5k
closing costs returns NPV < 0)" SC at the borrower-decision use case.
At a 200bps rate drop with $367/mo savings, $5k closing costs WOULD be
net-positive over 25-30 years discounted at 5% (by ~$58k). But over a
12-month tenure, the savings stream truncates to ~$4,260 in present-
value terms; the NPV is `-5000 + 4260 ≈ -$740` (engine-derived
`-718.01`). The fixture honors SC-1's literal numerical assertion at
the realistic short-tenure decision context. The departure from
ROADMAP's full-horizon framing is documented in the fixture's `_meta`
block, in 06-RESEARCH §"Pinned Oracles" Oracle 2, and here.

**Citations:**
- numpy-financial v1.0.0 docs (`npv` signature; `irr` deprecation
  context): https://numpy.org/numpy-financial/latest/
- numpy-financial bug #131 (`irr` arch-dependent — Phase 6 D-06 forbids
  use): https://github.com/numpy/numpy-financial/issues/131
- Federal Reserve "Consumer's Guide to Mortgage Refinancing" (breakeven
  framing): https://www.federalreserve.gov/pubs/refinancings/
- FHFA 2023 housing-finance survey (~13yr median tenure context for
  D-13): https://www.fhfa.gov/research

---

## 6. After-Tax Optional Mode (D-09)

Mortgage interest is tax-deductible in the United States, subject to the
post-2017 $750k qualified-loan-limit cap (or pre-2017 grandfathered $1M
cap). For borrowers who itemize, the after-tax savings from a refi are
LOWER than the pre-tax savings because both the OLD and NEW loans
generate (different amounts of) deductible interest — the refi's NPV is
modulated by the change in tax shield.

Phase 6 ships after-tax mode as **opt-in** to keep the v1 happy path
(SC-1 / SC-2 / SC-3 fixtures) independent of IRS predicate behavior.

### 6.1 Opt-in fields

- `after_tax_mode: bool = False` — default False.
- `marginal_tax_rate: Rate | None = None` — REQUIRED when `after_tax_mode=True`.
- `filing_status: Literal["single","mfj","mfs","hoh"] | None = None` —
  REQUIRED when `after_tax_mode=True`.

The cross-field validator `_validate_common` raises `ValueError` if
`after_tax_mode=True` but either of the two companion fields is missing.

### 6.2 Tax-shield computation

```
qualified_limit = qualified_loan_limit(filing_status, ...)  # RUL-11; lib.rules.irs_pub936
deductible_principal = min(new_loan_principal, qualified_limit)
deduction_fraction = deductible_principal / new_loan_principal

For each period t in 1..N:
    interest_t = new_schedule.payments[t-1].interest
    deductible_interest_t = interest_t * deduction_fraction
    tax_shield_t = deductible_interest_t * marginal_tax_rate

    Append RefiCashflow(period=t, direction="inflow",
                        amount=tax_shield_t, kind="tax_shield")
```

The tax-shield cashflows enter `_compute_npv` alongside the savings
stream; the engine surfaces both `npv` (pre-tax) and `after_tax_npv`
(includes tax shield) on `RefiResponse` so the consumer sees both
numbers without a second engine call.

### 6.3 Grandfathering ($1M vs $750k caps)

IRS Publication 936 (2024) specifies:
- **Post-2017** (Tax Cuts and Jobs Act): home-acquisition debt limit
  $750k (single / MFJ / HoH) or $375k (MFS). Applies to mortgages
  taken out after 2017-12-15.
- **Pre-2017 grandfathered**: $1M (single / MFJ / HoH) or $500k (MFS).
  Applies to mortgages taken out on or before 2017-12-15.

The `qualified_loan_limit` predicate (`lib/rules/irs_pub936.py` per
RUL-11) takes a `has_grandfathered_debt: bool = False` flag and returns
the appropriate Decimal cap. Phase 6 callers wanting to model
grandfathered scenarios pass that flag through; the engine propagates
it to the predicate.

### 6.4 v1 carve-outs in after-tax mode

After-tax mode does NOT model:
- Standard deduction crowding (the deductible interest is "wasted" if
  the borrower's total itemized deductions don't exceed the standard
  deduction). The caller is responsible for confirming itemization
  applies.
- State income tax deductibility (varies by state; v1 federal-only).
- AMT (Alternative Minimum Tax) interactions.
- HELOC / second-mortgage qualified-debt aggregation.

These are documented in `lib/refinance.py` after-tax cross-field
validator docstring as known scope limits; future plans (Phase 8
stress, Phase 11 SUBA-02 multi-offer) may revisit if a real consumer
needs them.

**Citations:**
- IRS Publication 936 (2024) — Home Mortgage Interest Deduction:
  https://www.irs.gov/pub/irs-pdf/p936.pdf
- `lib.rules.irs_pub936.qualified_loan_limit` (RUL-11 predicate; ships
  the post-2017 / grandfathered cap logic).

---

## 7. v1 Carve-Outs

Phase 6 v1 deliberately scopes OUT four areas that future phases will
revisit. Each is documented here to set caller expectations and prevent
silent under-modeling.

### 7.1 PMI/MIP recalc on cash-out LTV change (D-08; caller-supplied override per D-10)

Cash-out refinances that push `new_principal / property_value > 0.80`
typically trigger Private Mortgage Insurance (conventional) or alter
the FHA Mortgage Insurance Premium tier. v1 does NOT recalc PMI/MIP on
LTV change because the predicates (`lib.rules.conventional_pmi.status`
returns a TERMINATION enum, not a rate; `lib.rules.fha_mip.compute`
requires a full Loan + property_value + endorsement_date) are heavy
enough that wiring them into refi NPV would double Phase 6's surface
area.

**Caller-supplied escape hatch (D-10):** when the caller knows the new
monthly P&I includes PMI/MIP that v1 doesn't recalc, they pass
`new_loan_monthly_pi_override: Money | None = None` on the request. The
engine uses the override when supplied; otherwise computes via
`build_schedule(new_loan).monthly_pi`. This is the same "caller
supplies a number that crosses an out-of-scope predicate" pattern Phase
4 used for `monthly_pmi` (RESEARCH Open Q#1 inheritance).

A future plan (Phase 8 stress sweeps where LTV varies systematically,
or a dedicated 06-NN+1 if a consumer needs cash-out PMI in v1.x) may
revisit. For now, cash-out callers should EITHER ensure their cash-out
keeps LTV ≤ 0.80 OR supply the override field with a correctly-computed
PI+MI value.

### 7.2 Closing costs paid out-of-pocket only (D-12)

v1 does NOT support financing closing costs into the new loan's
principal. The caller computes new principal accordingly. This avoids
ambiguity about whether closing costs hit t=0 as an outflow OR whether
they inflate the principal (and thus the new monthly P&I) and get
amortized.

A future enhancement (Phase 8 or a 06-NN+1) may add a
`finance_closing_costs: bool = False` field that auto-bumps the new
principal and removes the t=0 closing-costs outflow. Ship it only when
a real consumer needs it.

### 7.3 pyxirr deferred to Phase 11 SUBA-02 (D-07)

Phase 6 v1 uses `numpy_financial.npv` exclusively. CLAUDE.md mentions
`pyxirr` aspirationally for "Rust+PyO3 XIRR/XNPV for batch refi-NPV
scenarios", but `pyxirr` is NOT a current `pyproject.toml` dependency
(REFI-04 wisely calls it "Optional").

Deferral path:
- Phase 11 SUBA-02 (refi-npv-agent multi-offer ranking) is the natural
  consumer of batch NPV across N≥3 refi offers. At that point:
  - Add `pyxirr` to `pyproject.toml` (Rust toolchain available in CI per
    Phase 11 plan check).
  - Build `lib.refinance.evaluate_batch(requests: list[RefiRequest])`
    that fans out to `pyxirr.npv` (or `xnpv` for irregular-date
    cashflows in the multi-offer comparison context).
  - The single-scenario `evaluate(req)` continues to use
    `numpy_financial.npv` to preserve Decimal discipline.

The deferral is documented in `lib/refinance.py::evaluate` docstring
with a `# Phase 11: see pyxirr migration note` marker so
`test_pyxirr_deferred_to_phase11_documented` (Plan 06-05 flip) passes.

### 7.4 Competing-offer comparison deferred to Phase 11 SUBA-02

Comparing N refi offers (e.g., 3 different lenders' rate sheets) and
ranking them by NPV is OUT of Phase 6 scope. v1 ships single-scenario
`evaluate(req)`; multi-offer ranking is the SUBA-02 brief.

Phase 6's contribution to that future work: making `evaluate()` SAFE
TO CALL N TIMES (no module-global mutation, no caching pitfalls). The
agent at Phase 11 will accept a `list[RefiRequest]`, run `evaluate()`
on each, and return a ranked NPV table. Documented in Plan 06-04 (CLI
plan) as a "downstream contract" note.

---

## 8. Citations

Primary references (all verified 2026-05-02):

- **Investopedia "Net Present Value (NPV)"** —
  https://www.investopedia.com/terms/n/npv.asp
  Borrower-side NPV formula and sign-convention reference; discount-rate
  selection guidance for personal-finance scenarios.
- **Federal Reserve "Consumer's Guide to Mortgage Refinancing" (2024)** —
  https://www.federalreserve.gov/pubs/refinancings/
  Breakeven framing for borrowers; "compare expected savings to closing
  costs over your expected tenure" guidance; reinforces the borrower-
  perspective convention this document codifies.
- **CFPB Refinance Closing Disclosure Examples** —
  https://www.consumerfinance.gov/owning-a-home/closing-disclosure/
  Closing-cost itemization conventions; supports the v1 decision to net
  closing costs out of t=0 cash proceeds in the cash-out cashflow
  inventory (§4.2).
- **IRS Publication 936 (2024) — Home Mortgage Interest Deduction** —
  https://www.irs.gov/pub/irs-pdf/p936.pdf
  Authoritative source for the $750k post-2017 cap and pre-2017
  grandfathered $1M cap. Encoded by `lib/rules/irs_pub936.py`
  (RUL-11 predicate). Powers the after-tax-mode tax-shield computation
  in §6.
- **numpy-financial v1.0.0 documentation** —
  https://numpy.org/numpy-financial/latest/
  Authoritative `npv(rate, values)` signature reference. Phase 3 D-04
  empirically verified that Decimal inputs return Decimal outputs;
  Phase 6 inherits this discipline.
- **numpy-financial bug #131 (`irr` arch-dependent)** —
  https://github.com/numpy/numpy-financial/issues/131
  Source of the D-06 "no `npf.irr`" mandate. Phase 6 uses cumulative-NPV
  scan for breakeven instead. The bug remains open in v1.0.0 as of the
  2026-05-02 verification.

Cross-phase / internal references:

- **Phase 4 affordability sign archetype** — `lib/affordability.py::evaluate_reverse`
  uses `npf.pv(..., pmt=-max_PI, fv=0)` and the negative-PMT convention.
  Phase 6's `_compute_npv` mirrors that borrower-perspective sign
  discipline at the NPV layer.
- **Phase 3 amortization wrap-not-reimplement** — `lib/amortize.py:1-136`
  module docstring + AMRT-01. Phase 6 follows the same convention with
  `npf.npv`.
- **Phase 5 D-14 quantize_rate promotion** — `lib/money.py:58-73`. Phase
  6 uses `quantize_rate(discount_rate_annual)` at request entry.
- **`references/arm-mechanics.md`** (Phase 5 doc precedent). Phase 6's
  doc structure mirrors that file's section-per-convention discipline.

### Phase 6 LOCKED DECISIONS cross-reference (D-01..D-16)

For full text, see `06-RESEARCH.md §"Locked Decisions"`. Brief
cross-references that surface in this document:

| Decision | Cross-reference | Section in this doc |
|---|---|---|
| D-01 | No new external deps; `numpy_financial.npv` is canonical | §2 |
| D-02 | Module structure mirrors `lib/affordability.py` | §2 (helper layer) |
| D-03 | `RefiCashflow` 5-Literal `kind` field | §1, §4 |
| D-04 | Borrower-perspective sign convention (THIS DOC HEADLINE) | §1 (verbatim) |
| D-05 | `discount_rate_annual` REQUIRED, no default | §3 (entire) |
| D-06 | NPV-breakeven via cumulative scan (NOT `npf.irr`) | §5.2 |
| D-07 | `pyxirr` deferred to Phase 11 | §7.3 |
| D-08 | PMI/MIP recalc OUT of v1 | §7.1 |
| D-09 | After-tax mode opt-in | §6 (entire) |
| D-10 | Caller PMI/MIP override field | §7.1 |
| D-11 | `analysis_horizon_months` optional | §5.5 |
| D-12 | Closing costs out-of-pocket only | §7.2 |
| D-13 | Negative-NPV fixture uses horizon=12 | §5.5 |
| D-14 | Sign-validator accepts `amount=0` either direction | §1 |
| D-15 | `closing_costs` is a top-level request field | §4.2 |
| D-16 | Belt-and-suspenders sign-convention surfaces (4 places) | §1, this doc + 3 others |

---

## Appendix — Citation Index

| URL | Section / Anchor | Last verified |
|-----|------------------|----------------|
| https://www.investopedia.com/terms/n/npv.asp | NPV formula + sign convention reference | 2026-05-02 |
| https://www.federalreserve.gov/pubs/refinancings/ | Consumer's Guide to Mortgage Refinancing (2024) | 2026-05-02 |
| https://www.consumerfinance.gov/owning-a-home/closing-disclosure/ | CFPB Closing Disclosure examples | 2026-05-02 |
| https://www.irs.gov/pub/irs-pdf/p936.pdf | IRS Publication 936 (2024); $750k / $1M caps | 2026-05-02 |
| https://numpy.org/numpy-financial/latest/ | numpy-financial v1.0.0 docs (`npv` signature) | 2026-05-02 |
| https://github.com/numpy/numpy-financial/issues/131 | numpy-financial bug #131 (`irr` arch-dependent) | 2026-05-02 |
| https://www.fhfa.gov/research | FHFA 2023 housing-finance survey (~13yr median tenure context for D-13) | 2026-05-02 |

Annual re-validation cadence: each calendar year, confirm each URL still
resolves; if any have moved, update the index above and the §8 inline
references.
