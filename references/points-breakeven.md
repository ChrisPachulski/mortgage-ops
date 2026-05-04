# Discount-Points Breakeven — mortgage-ops Phase 8 Reference

This document records the conventions implemented by `lib/points.py`
(Phase 8 discount-points breakeven engine) and pairs each convention
with its regulatory citation. All section numbers and URLs were
verified on 2026-05-03 against the live IRS / eCFR / CFPB sources (per
`08-RESEARCH.md` §5.5 and §Citations).

Cited from:
- `lib.points` module docstring (D-08-06-01 cite-from contract;
  mirrors `lib.apr` D-29 idiom)
- `scripts/points_breakeven.py --help` epilog (per Plan 08-06 Task 3
  cross-reference)
- ROADMAP § Phase 8 SC-4 (simple-vs-NPV divergence pin)

This file is the headline reference for the Phase 8 points-breakeven
conventions AND the **authoritative documentation for the Phase 6
deferred discount-rate coupling** (Plan 08-06 D-06-02 LOCKED). The
"Discount-Rate Convention" section (§3) spells out the cross-phase
contract: caller-supplied today; additive non-breaking default once
Phase 6 lands its project-wide borrower-perspective convention.

---

## Overview

Discount points let borrowers pay an upfront premium (typically 1% of
loan amount per "point") in exchange for a lower interest rate. The
breakeven question — "at what month does the rate savings recoup the
upfront cost?" — has two valid framings, both reported side-by-side by
`lib.points.evaluate(req)` and `scripts/points_breakeven.py`:

1. **Simple breakeven** (PNTS-01): `ceil(points_cost / monthly_savings)`
   — ignores time value of money. Easy mental model; what most
   consumer-facing breakeven calculators report.
2. **NPV breakeven** (PNTS-02): The first month where cumulative
   discounted savings exceed the upfront cost, given a borrower-
   perspective discount rate. Honest with respect to opportunity cost;
   what a financially-informed buyer should care about for long-hold
   decisions.

Per ROADMAP SC-4 (D-04 LOCKED), `PointsResponse` carries BOTH outputs
side-by-side along with a `diverge` flag and a `decision`
(`buy_points` | `skip_points`) derived from the cumulative NPV at the
caller-supplied hold horizon. The two outputs disagree only when
discount factors materially differ from 1; a divergence-pin fixture
(`tests/fixtures/points/points_simple_lt_npv_seven_pct_discount.json`)
documents the canonical 92-month gap at a 7% discount rate (§5).

The dispatcher is a Pydantic v2 discriminated union by `mode` (Plan
08-01 D-01) over two payload shapes:

- `from_savings` — caller pre-computed `monthly_savings` (single
  Decimal in).
- `from_loans` — engine derives `monthly_savings` from two Loans
  (with-points + without-points); two `lib.amortize.build_schedule`
  calls under the hood.

Both modes route to the same `simple_breakeven` and `npv_breakeven`
helpers, so the breakeven math is mode-independent.

---

## Simple Breakeven Formula

```
months_to_breakeven = ceil(points_cost / monthly_savings)
```

Implementation: `lib.points.simple_breakeven(points_cost,
monthly_savings)`. Decimal-safe ceil via
`Decimal.to_integral_value(rounding=ROUND_CEILING)` under
`localcontext(MONEY_CONTEXT)` so the project-wide `ROUND_HALF_UP`
context is preserved (Phase 1 money discipline).

Returns `None` when `monthly_savings <= 0` (rate-up scenario; points
cost MORE than they save). The caller surfaces a structured
`NEGATIVE_OR_ZERO_SAVINGS` warning in `PointsResponse.warnings` and
forces `decision = skip_points`. This is Plan 08-01 D-03-01 mirroring
Phase 4 D-11's blocked-by-via-field-not-raise convention; the engine
returns a clean response rather than blowing up the sweep.

The simple breakeven is cited in consumer-facing CFPB / Bankrate /
NerdWallet calculators because it's the easiest framing to explain. It
is correct as a first-order approximation when discount rates are near
zero (e.g., money-sits-in-checking opportunity cost) and increasingly
diverges from the NPV truth as discount rates rise.

---

## NPV Breakeven Formula

Cumulative NPV at month `m`:

```
cum_npv(m) = sum_{k=1..m} (monthly_savings / (1 + r_monthly)^k) - points_cost
where r_monthly = discount_rate_annual / 12
```

Implementation: `lib.points.npv_breakeven(points_cost, monthly_savings,
hold_months, discount_rate_annual)`. The engine walks month-by-month
from 1 to `hold_period_months` and returns the first `m` where
`cum_npv(m) >= 0`. If the walk never crosses within the hold horizon,
returns `None`.

The walk is performed with the unquantized accumulator (one quantize at
the boundary, never mid-walk per Phase 1 money discipline). The
returned `cumulative_npv_at_hold` drives the buy/skip decision:
`buy_points` iff `cum_npv_at_hold >= 0`; `skip_points` otherwise (Plan
08-03 D-03-04).

### Discount rate of zero collapses to simple breakeven

A discount rate of `0` reduces every discount factor `1 / (1 +
r_monthly)^k` to exactly `1`, so the NPV walk becomes a plain
accumulation of `monthly_savings` against `-points_cost` — and crosses
zero at the same month as `simple_breakeven`. This mathematical
identity is verified by the Plan 08-05 fixture
`points_simple_eq_npv_zero_discount.json` (engine-emitted: simple = 123
months, npv = 123 months at `discount_rate_annual = 0.000000`).

The collapse is the foundation for the "Zero" recommendation in §3
below — a caller who genuinely has no opportunity cost (e.g., the
alternative is "money sits in checking earning 0%") gets a clean,
defensible NPV identical to the simple breakeven.

### Negative savings + non-crossing scenarios

For negative `monthly_savings` (rate-up scenarios; allowed at
construction in `from_savings` mode per Plan 08-01 D-03), the cumulative
NPV strictly decreases — `cum_npv(m) < cum_npv(m-1)` for all `m` —
so `months_to_zero = None` and the discount rate has no effect on
break-detection in this branch. The dispatcher routes the warning at
the response level and forces `decision = skip_points`.

For positive `monthly_savings` at very high discount rates (e.g.,
`discount_rate_annual = 0.20`), the discounted savings stream may
asymptotically approach a limit BELOW `points_cost`, so `cum_npv(m)`
stays negative through the hold horizon. `months_to_zero = None` again,
but the response carries the engine-emitted negative
`cumulative_npv_at_hold` so the caller can read the magnitude of the
miss.

---

## Discount-Rate Convention (Phase 6 deferred coupling)

The borrower-perspective discount rate represents the borrower's
**opportunity cost**: the alternative return they'd earn by NOT paying
the points cost upfront. There is no single right answer — the value
depends on the borrower's actual financial situation.

Phase 6 (Refinance NPV) will pin a project-wide borrower-perspective
discount-rate convention as part of its broader
`outflows-negative / savings-positive` sign discipline (Phase 6 D-04;
see `references/refi-npv.md` §1). Until Phase 6 lands, `lib/points.py`
**punts to the caller**: `PointsRequest.discount_rate_annual` is
REQUIRED with no module-level default (Plan 08-01 D-02 + Plan 08-04
D-04-05 LOCKED).

This matches the project's fail-loud-on-implicit-default discipline:
Phase 4 `max_dti`, Phase 5 `floor_rate`, Phase 8 `dti_threshold` all
follow the same pattern. The cross-phase coupling is documented here in
§3 because Phase 6 hasn't shipped yet — when it does, Plan 08-06 D-06-02
authorizes the Phase 6 planner to edit this section and add the
project-wide default.

### Recommended starting points until Phase 6 lands

The CLI's `--help` epilog and this section both surface three plausible
choices for `discount_rate_annual` so callers aren't left guessing:

- **Zero (`0.000000`)** — No opportunity cost; collapses NPV to simple
  breakeven (verified by `points_simple_eq_npv_zero_discount.json`
  fixture). Use when the alternative is "money sits in checking earning
  0%". Conservative; over-estimates the case for buying points.
- **Loan annual rate** — Paying-down-debt opportunity. Use when the
  alternative is "make extra principal payments on this loan instead of
  buying points". Self-consistent: the borrower's borrowing rate IS
  their reinvestment rate in this framing.
- **`0.050000`** — Rough US 10-year Treasury proxy (~5% as of 2026-05).
  Use when the alternative is "buy bonds with the upfront cash". Pinned
  in the Plan 08-05 SC-4 divergence fixture (`points_simple_lt_npv_
  seven_pct_discount.json`) at `0.070000` — slightly above the 5%
  Treasury baseline to amplify the divergence for the contract test;
  callers in production should use real market data.

When Phase 6 lands, this section will be UPDATED (Plan 08-06 D-06-02
authorizes the edit) and `lib.points.PointsRequest.discount_rate_annual`
will gain an additive non-breaking default. Existing callers (and
existing fixtures) will continue to work because the field becomes
optional rather than required-with-default; the migration is a
single-line change in `lib/points.py` plus a section rewrite here.

### What Phase 6 will pin

The exact phase-6 default is Phase 6's call. Likely candidates per
`08-RESEARCH.md §5.5` (non-binding forecast):

1. **Borrower's marginal opportunity rate** (parametric; surfaced via
   `config/profile.yml` user-layer per the data contract). Most
   defensible; demands more user input.
2. **5% / 10-year Treasury proxy** (fixed default; refreshed annually
   via the staleness convention in `data/reference/`). Easiest to
   implement; opaque rationale for non-financial-savvy users.
3. **Loan annual rate** (per-request; engine derives from
   `loan.annual_rate`). Self-consistent but only meaningful for loans
   with positive balance; refi-NPV's broader cashflow framing makes
   this less natural.

The Phase 6 planner picks; this section gets the post-decision rewrite.

---

## Decision Dispatcher

`PointsResponse.decision` is `"buy_points"` iff `cum_npv(hold_period_
months) >= 0`; `"skip_points"` otherwise. If `simple_breakeven_months
is None` (negative savings — points cost more than they save), the
decision is forced to `"skip_points"` regardless of the NPV walk
(Plan 08-03 D-03-04).

The `diverge` boolean is `True` iff `simple_breakeven_months !=
npv_breakeven_months` AND both are non-None. Equal values (including
the both-None case where the engine never breaks even) carry
`diverge=False`. The optional `diverge_explanation` string narrates the
gap when present (e.g., "NPV breakeven is 92 months later than simple
breakeven at this discount rate").

The dispatcher always reports BOTH `simple_breakeven_months` AND
`npv_breakeven_months` side-by-side per ROADMAP SC-4 D-04 verbatim —
"reports breakeven months as `points_cost / monthly_savings` AND a
parallel NPV-based decision". This is the load-bearing closure for
SC-4.

---

## Divergence Example (ROADMAP SC-4 pin)

The Plan 08-05 SC-4 divergence fixture
(`tests/fixtures/points/points_simple_lt_npv_seven_pct_discount.json`)
pins the canonical engine-emitted truth:

| Loan | Rate | monthly_pi | Notes |
|---|---|---|---|
| Without points | 6.50% / 30yr / $400k | $2,528.27 | Phase 1 oracle anchor |
| With 2 points (cost $8,000) | 6.25% / 30yr / $400k | $2,462.87 | $65.40 monthly savings |

| Discount rate | Simple breakeven | NPV breakeven | Diverge | Gap |
|---|---|---|---|---|
| 0.00% | 123 months | 123 months | False | 0 months |
| 7.00% | 123 months | 215 months | True | +92 months |

**Note on the SC-4 pins (Plan 08-05 D-05-05 LOCKED):** The 215-month
NPV figure at 7% discount is the engine-emitted truth, cross-validated
three ways (numpy_financial.nper + closed-form annuity + the engine's
month-by-month walk per `lib.points.npv_breakeven`'s implementation).
Earlier planning docs forecast 160 months; the engine is correct, the
forecast was off by 55 months due to a back-of-envelope geometric-
series approximation that ignored the $8,000 upfront drag (Plan 08-03
deviation #1 captured the cross-validation).

Borrowers with hold horizons in the 10-13 year range face a meaningful
decision: simple breakeven says "buy" by year 11, NPV at 7% discount
says "buy only if you'll hold past year 18". This 7-year delta is the
load-bearing reason BOTH outputs are reported side-by-side — neither
alone tells the full story.

The fixture `_meta.requirements` array tags this fixture with `PNTS-02`
+ `ROADMAP SC-4` per Plan 08-05 D-05-04 citation-coverage discipline.

---

## Citations

Primary regulatory references (IRS / eCFR / CFPB; verification cadence:
annual per the Phase 2 staleness convention):

- **IRS Publication 936** (Home Mortgage Interest Deduction) —
  Discount points are deductible per the rules summarized in
  `data/reference/irs-pub936.yml`. Discount points (origination points)
  get separate treatment from loan-origination fees; the breakeven math
  here ignores the deduction (after-tax mode is Phase 6 territory per
  `references/refi-npv.md §6`).
  https://www.irs.gov/publications/p936

- **Regulation Z, 12 CFR §1026.18** — Disclosure rules for discount
  points on the Loan Estimate. Reg Z requires lenders to disclose the
  upfront cost in the "Origination Charges" section. The engine's
  `points_cost` field is the same dollar figure that appears on the
  Loan Estimate.
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.18

- **CFPB Consumer Resources** — "What are (discount) points and lender
  credits and how do they work?" (consumer-facing explanation of the
  rate-vs-cost tradeoff that this engine mechanizes).
  https://www.consumerfinance.gov/ask-cfpb/what-are-discount-points-and-lender-credits-and-how-do-they-work-en-136/

CFPB explainer + supervisory references:

- **CFPB Loan Estimate explainer** (origination-charges section
  walkthrough; the `points_cost` field maps to Box A on the Loan
  Estimate per TRID).
  https://www.consumerfinance.gov/owning-a-home/loan-estimate/

Cross-phase / internal references:

- **Phase 1 money discipline** — `lib/money.py` (`MONEY_CONTEXT`,
  `quantize_cents`, `quantize_rate`); the NPV walk performs one
  quantize at the boundary, never mid-walk.
- **Phase 3 amortization engine** — `lib/amortize.py::build_schedule`.
  `from_loans` mode calls this once per loan to derive
  `monthly_savings = no_pts.monthly_pi - with_pts.monthly_pi`.
- **Phase 6 refi-NPV doc precedent** — `references/refi-npv.md` §1
  (sign convention for the broader borrower-perspective family;
  discount-rate coupling lives downstream of that convention).
- **Phase 6 IRS Pub 936 reference data** —
  `data/reference/irs-pub936.yml` (deductibility cliff at $750k loan
  cap per IRS Pub 936; tax shield modeled in Phase 6 after-tax mode,
  NOT here).
- **Phase 8 stress sibling** — `references/stress-tests.md` (Plan 08-06
  same-wave companion doc; common section-structure inheritance from
  `references/arm-mechanics.md` per D-06-01).

---

## Glossary

- **Point** — 1% of loan amount paid upfront in exchange for a lower
  interest rate. "2 points on a $400k loan" = $8,000 upfront cost.
- **Discount rate** (in NPV context) — the borrower's opportunity cost;
  the rate of return on the alternative use of the upfront cash. NOT
  the loan's annual rate (unless the borrower's specific opportunity is
  paying down principal on this same loan).
- **Hold period** — the number of months the borrower expects to hold
  the loan before selling, refinancing, or paying off. Caller-supplied
  via `hold_period_months`; bounded `[1, 600]` (50 years) per the
  Pydantic model.
- **Breakeven** — the month at which cumulative savings equal upfront
  cost. Reported in two flavors (simple, NPV) by this engine, always
  side-by-side per ROADMAP SC-4.
- **Diverge** — `simple_breakeven_months != npv_breakeven_months` AND
  both non-None. The Plan 08-05 SC-4 fixture pins a 92-month divergence
  at 7% discount.
- **Cumulative NPV at hold** — the engine-emitted Decimal value of
  `cum_npv(hold_period_months)`; positive means the borrower comes out
  ahead by holding through the horizon (decision = `buy_points`).

---

## Appendix — Citation Index

| URL | Section / Anchor | Last verified |
|-----|------------------|----------------|
| https://www.irs.gov/publications/p936 | IRS Publication 936 (Home Mortgage Interest Deduction; discount-point deductibility) | 2026-05-03 |
| https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.18 | 12 CFR §1026.18 Reg Z disclosure of discount points (Loan Estimate origination charges) | 2026-05-03 |
| https://www.consumerfinance.gov/ask-cfpb/what-are-discount-points-and-lender-credits-and-how-do-they-work-en-136/ | CFPB Ask CFPB §136 (consumer-facing discount-points explainer) | 2026-05-03 |
| https://www.consumerfinance.gov/owning-a-home/loan-estimate/ | CFPB Loan Estimate explainer (origination charges Box A walkthrough) | 2026-05-03 |

Annual re-validation cadence: each calendar year, confirm each URL
still resolves; if any have moved, update the index above. Mirrors
`references/arm-mechanics.md`, `references/refi-npv.md`, and
`references/apr-reg-z.md` cadence.
