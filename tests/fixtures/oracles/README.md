# Independent Oracle Fixtures

This directory hosts **independent oracles** — captured once from external
sources, never re-fetched — that cross-validate the calc engine against the
outside world. They are the antidote to self-validating golden fixtures
(`tests/fixtures/{amortize,apr,arm,points,refinance,stress}/`) which are
engine-emitted and therefore cannot, by construction, catch a systematic
bug in the engine.

Captured: **2026-05-23** (see each fixture's `captured_at` field).
Do not re-fetch live URLs from CI — these are pinned snapshots.

## Layout

| Subdir            | Source type                                            | Tolerance philosophy                                     |
| ----------------- | ------------------------------------------------------ | -------------------------------------------------------- |
| `cfpb-le/`        | CFPB Loan Estimate sample PDFs (H-24 series)           | Reg Z `+/- 0.125%` on APR (12 CFR §1026.22(a)(2))        |
| `bankrate-html/`  | Bankrate / mortgagecalculator.org HTML snapshots       | Cent-level on monthly P&I (engine wraps `numpy_financial.pmt`) |
| `excel-arm/`      | CFPB CHARM booklet ARM worked example (CSV form)       | Cent-level on per-period payment & rate                  |
| `handcalc/`       | Hand-calculated arithmetic with reviewer signature     | Exact `Decimal` equality                                 |

Each fixture carries `source_url`, `captured_at`, `inputs`, and an
`expected` block with the values to assert against. Tests live at
`tests/test_oracles_*.py`.

## What this catches that engine-emitted goldens cannot

Engine-emitted golden fixtures (every `tests/fixtures/<family>/*.json` not
under `oracles/`) are derived from `lib.<family>` itself. They cannot, by
construction, catch a systematic bug in the engine — they'd shift in
lockstep with the bug. Oracle fixtures are derived from independent
third-party sources, so a divergence between the engine and the oracle is a
real signal.

The oracle data here was captured from sources that compute mortgage math
themselves (CFPB regulatory worked examples, public calculator pages, hand
arithmetic) — so they answer the same arithmetic the engine answers, and
disagreement is evidence the engine (or the oracle) is wrong.

## Documented oracle gaps

- **Bankrate ARM / refinance / points calculators**: All three pages are
  JS-rendered. `WebFetch` returns the landing-page copy but the calculator
  widget never executes. We fell back to **mortgagecalculator.org**, which
  publishes static worked examples in HTML. The Bankrate captures
  themselves are documented as skip-with-reason — see
  `tests/test_oracles_*.py`.
- **Vertex42 ARM Excel template**: Excel-only; cannot be opened
  autonomously. We substituted with the CFPB **CHARM** consumer booklet's
  published worked example (a published "Excel-equivalent" ARM payment
  table — same shape, same purpose) under `excel-arm/`.
- **FFIEC APRWIN tool**: Windows-only desktop app; not capturable from this
  environment. The pre-existing `tests/fixtures/apr/oracle/ffiec_*.json`
  set is engine-emitted with honest provenance; the CFPB-LE oracle here
  closes that gap independently for at least one input combination.

## Discovered discrepancies (oracle bugs, not engine bugs)

While capturing oracles we found two oracle sources are themselves wrong:

1. `mortgagecalculator_org_should_i_pay_points.html` claims `$200,000 @
   4.5% / 30yr` produces a P&I of `$993.10`. The engine, the closed-form
   PMT formula, and `numpy_financial.pmt` all return **$1,013.37** (an
   independent computation; verified three ways). The oracle's `$993.10`
   appears to be a copy-paste from a different example (possibly
   `$195,000 @ 4.5%`). The corresponding "breakeven 5yr 9mo" claim is
   likewise inconsistent with its own quoted inputs (using $4,000 / $38.27
   the breakeven is 105 months, not 69). The points test asserts the
   engine matches the **correct** P&I and the with-points value ($954.83
   at 4.0%) — which the oracle also reports correctly.
2. `mortgagecalculator_org_refinance_breakeven.html` Example A claims a
   "Months to Breakeven = 21" for a refi where the monthly payment
   **increases** by $85.43. That contradicts simple-breakeven definitions
   (no monthly savings -> no payment-recovery breakeven). The engine
   correctly reports `simple_status="no_savings"`. The refi test asserts
   engine `old_pi`, `new_pi`, and `monthly_savings` match the oracle's
   numbers (which are correct); the inconsistent "21 months" claim is
   documented but not asserted.

Both of these are documented in the README rather than the fixture JSON,
because the JSON is the *engine* contract — the engine is correct.

## Updating these fixtures

Annual cadence at most. If a CFPB sample is re-issued, capture the new PDF
to the same path with the new `captured_at` and re-derive the expected
values. The HTML snapshots intentionally keep the captured-once
`source_url` + `captured_at` so anyone auditing the run can replay the
capture against the live URL and compare.

Do **not** fetch these URLs from `pytest` itself — that turns a hermetic
oracle into a flaky network dependency.
