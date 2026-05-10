# Spreadsheet Conventions (Why Our Numbers Differ from Excel)

Loaded on demand from SKILL.md per the topic→reference table. Triggers: "why don't your numbers match Excel", "how do you round", "spreadsheet tradition".

## What this doc covers

The four reasons our P&I, schedule, and refi-NPV numbers may not byte-match a spreadsheet a user has been keeping: the Excel sign convention, two known `numpy-financial` bugs (#130 + #131) that we work around, our `Decimal`-from-strings discipline vs Excel's float storage, and the two flavors of "biweekly" mode that confuse direct comparison.

## 1. Excel PMT Sign Convention

`numpy-financial.pmt(rate, nper, pv)` — like Excel's `PMT()` — returns the cashflow **outflow** (negative) when `pv` is positive (the loan principal arrives as a positive cashflow; the payments leaving the borrower are negative). For a $400,000, 6.5%, 30-year loan:

```
>>> import numpy_financial as npf
>>> npf.pmt(0.065/12, 360, 400000)
-2528.265...
```

User-facing UIs (and our reports) want a positive `$2,528.27`. Our wrap negates explicitly:

```python
level_pmt = quantize_cents(-npf.pmt(period_rate, loan.term_months, loan.principal))
```

(See `lib/amortize.py` line 308.) If a user pastes our output into a spreadsheet that expects negative payments, the sign will appear inverted; that's a sign-convention gap, not a math gap.

## 2. numpy-financial Bug #130 — `pmt` fv-sign issue

GitHub: <https://github.com/numpy/numpy-financial/issues/130>.

Summary: when `fv` (future value, balloon) is non-zero, `npf.pmt` mis-handles the sign such that a balloon payment expected to leave a positive balance can produce a payment that overshoots zero. We do NOT use `fv != 0` in v1 (no balloon products are in scope). If a future phase adds balloon support, the wrapper will compute the balloon-equivalent amortization manually rather than passing `fv` directly to `npf.pmt`.

`lib/amortize.py` carries a comment at line 125 documenting this.

## 3. numpy-financial Bug #131 — `irr` architecture-dependent results

GitHub: <https://github.com/numpy/numpy-financial/issues/131>.

Summary: `npf.irr(cashflows)` uses `numpy.roots` which can return slightly different complex-root selections on x86-64 vs arm64 (M1/M2/M3) hardware. For some pathological cashflow sequences this surfaces as a 0.01-0.05% IRR delta between architectures, which fails byte-equality tests in CI.

Our mitigation (per CLAUDE.md ## Technology Stack):
- **Single-loan IRR:** we don't use it directly; we compute breakeven-month and NPV instead.
- **Batch refi-NPV / XIRR:** we use `pyxirr` (Rust + PyO3) which is deterministic across architectures.

Tests that span macOS-arm64 dev machines and Linux-x86 CI runners pass byte-identical because `pyxirr` is the source of truth for IRR-flavored calculations.

## 4. Decimal vs Float

Excel uses 64-bit IEEE 754 binary floats internally. `0.1 + 0.2` in Excel is technically `0.30000000000000004` but Excel hides the trailing junk in the display layer.

We use `Decimal`:
- Constructed from strings, NEVER from floats: `Decimal("0.065")` not `Decimal(0.065)`. The latter inherits the float's binary-fraction noise (`Decimal(0.1) → 0.1000000000000000055511151231257827021181583404541015625`).
- Quantized at end-of-period only via `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` — see `lib/money.py`.
- Rates internally carry 6 decimal places (`_quantize_rate`); display formatters re-round for narration but do NOT propagate back into storage (D-NUM-05).

Net effect: on simple cases (no balloon, no extra principal), our P&I should byte-match Excel to the cent. On long schedules, a single penny may drift between Excel and our output because Excel quantizes implicitly during display while we quantize once at end of period; over 360 periods that drift can show up as a ±$0.01-0.04 final-payment difference. Our `test_final_balance_zero` enforces `Decimal("0.00")` exactly.

## 5. Biweekly Mode — Two Flavors

Some servicers market "biweekly" as twice a month (24 payments/year, same calendar dates), which is mathematically equivalent to monthly amortization with no payoff acceleration. Others market "true biweekly" as every 14 days (26 payments/year), which DOES accelerate payoff (~6 years off a 30yr at 6%).

Our `biweekly_mode` enum:
- `true_biweekly` (default): `relativedelta(weeks=2)` between payment dates → 26 payments/year → accelerated.
- `half_monthly`: two same-day half-payments per month → 24 payments/year → equivalent to monthly.

If a user's spreadsheet shows "biweekly" but no payoff acceleration, they're modeling `half_monthly`. Our default is `true_biweekly`; specify `biweekly_mode: "half_monthly"` in the request to match.

## Cross-References

- `lib/money.py` — `quantize_cents`, `_quantize_rate`, the `Decimal`-from-strings idiom
- `lib/amortize.py` — sign-flip wrap, biweekly modes, bug #130 docstring
- CLAUDE.md ## Technology Stack — pinned `numpy-financial` + `pyxirr` choice
- `references/amortization-formulas.md` — formulas + four golden oracles

**Last reviewed:** 2026-05-08
