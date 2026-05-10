# Amortization Formulas (Phase 3 numpy-financial wrap)

Loaded on demand from SKILL.md per the topic→reference table. Triggers: "how is the monthly payment computed", "PMT formula", "amortization math".

## What this doc covers

The math behind `lib/amortize.py` and `.claude/skills/mortgage-ops/scripts/amortize.py`: the level-payment PMT formula, the four golden oracles that pin our implementation, biweekly modes (true 26/year vs half-monthly 24/year), extra-principal handling, and the final-payment cleanup that guarantees a zero balance.

## Level-Payment PMT Formula

For a fully-amortizing fixed-rate loan, the constant level monthly payment satisfies:

```
PMT = P × r × (1 + r)^n / ((1 + r)^n − 1)
```

Where:
- `P` = principal (loan amount, in dollars)
- `r` = periodic interest rate (annual rate ÷ 12 for monthly)
- `n` = total number of periods (term in months for monthly)

We do NOT reimplement this. We wrap `numpy_financial.pmt(rate, nper, pv)` (returns negative for cashflow-out per Excel convention; we negate to surface a positive payment). See `lib/amortize.py` line 308:

```python
level_pmt = quantize_cents(-npf.pmt(period_rate, loan.term_months, loan.principal))
```

`npf.pmt` is called ONCE per build (Phase 3 D-04); per-period interest is then `balance × period_rate`, principal is `level_pmt − interest`, and balance reduces by principal each period. End-of-period quantize at 2 decimal places (`ROUND_HALF_UP`).

## Four Golden Oracles (from CLAUDE.md FND-09)

The implementation is pinned by four independent fixtures. Any change to `lib/amortize.py` MUST preserve all four to the cent.

### 1. Wikipedia textbook example
- `P = $200,000`, `annual_rate = 6.5%`, `term = 30 yr (360 months)`
- Monthly P&I → **$1,264.14**
- Source: Wikipedia article on amortization calculator (textbook reference value).

### 2. CFPB Loan Estimate
- `P = $162,000`, `annual_rate = 3.875%`, `term = 30 yr (360 months)`
- Monthly P&I → **$761.78**
- Source: CFPB sample Loan Estimate document; the published P&I value is the one the regulator displays.

### 3. Computed: round numbers, conforming
- `P = $400,000`, `annual_rate = 6.5%`, `term = 30 yr (360 months)`
- Monthly P&I → **$2,528.27**
- Derivation: `PMT = 400000 × (0.065/12) × (1+0.065/12)^360 / ((1+0.065/12)^360 − 1)` then quantize.

### 4. Computed: 15-year term
- `P = $200,000`, `annual_rate = 7.0%`, `term = 15 yr (180 months)`
- Monthly P&I → **$1,797.66**
- Derivation: same formula, `n = 180`, `r = 0.07/12`.

Tests at `tests/test_amortize.py::test_oracle_*` cite each oracle by name and assert exact `Decimal` equality (NOT `assertAlmostEqual`).

## Biweekly Mode (AMRT-03)

Two competing definitions exist; we ship both behind a `biweekly_mode` enum:

- **True biweekly (26 payments/year):** `relativedelta(weeks=2)` between payment dates; effective accelerated payoff (~6 years off a 30yr term at 6%). The level half-payment is `monthly_PI / 2`, applied 26 times/year. See `_build_biweekly_true()` in `lib/amortize.py` line 386.

- **Half-monthly (24 payments/year):** marketed as "biweekly" by some servicers but is actually two half-payments per month (twice on the same calendar dates each month). Equivalent to monthly amortization in cashflow terms; no payoff acceleration. See `_build_biweekly_half_monthly()`.

The user-facing default (when `biweekly_mode` is unspecified) is `true_biweekly` — matches the colloquial expectation.

## Extra Principal (AMRT-04 + Phase 3 D-05)

Three extra-principal modes are supported:

1. **Single one-time:** `{ "period": 24, "amount": "5000.00" }` — applied at end of period 24, reduces balance directly (does NOT reduce the level payment).
2. **Recurring monthly:** `{ "amount": "200.00", "start_period": 1 }` — applied every period from `start_period` onward.
3. **Per-period custom:** `[ {"period": 12, "amount": "1000"}, {"period": 24, "amount": "1000"} ]` — explicit list; D-05 uniqueness rider rejects duplicate `period` entries.

Each extra payment is added to the period's principal portion; interest the following period is computed on the post-extra balance.

## Final Payment Cleanup (AMRT-05 + Phase 3 D-09)

Floating-point and rounding accumulate over 360 periods. The final payment is computed as `prev_balance + final_interest` (NOT the level payment) so the post-final balance is exactly `Decimal("0.00")`. Test `test_final_balance_zero` asserts this on every fixture.

## Cross-References

- `lib/amortize.py` — the wrap (build_schedule, _build_fixed_monthly, _build_biweekly_*)
- `lib/money.py` — `quantize_cents`, `_quantize_rate` (6dp), `Decimal` discipline
- `.claude/skills/mortgage-ops/scripts/amortize.py` — JSON-in/JSON-out CLI wrapper
- `references/spreadsheet-conventions.md` — why our numbers may differ from Excel (sign convention, numpy-financial bugs)

**Last reviewed:** 2026-05-08
