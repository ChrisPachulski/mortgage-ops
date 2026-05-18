# Property Analysis Fixtures (Phase 14)

Pinned, hand-calculated AnalysisReport oracles for deterministic ANLZ-01..03 +
VERD-01 tests. Each fixture pins every preferred-DP cell of the matrix and the
full verdict.reasons[] list by exact Decimal equality.

## Files

| File                                | Tested SC                          | Covers                                                                                  |
| ----------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------- |
| `sfh_conforming_king_county.json`   | ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 | Conv30/Conv15/FHA30 conforming SFH @ 20% DP; 3-program 18-cell matrix; verdict=GO       |
| `condo_with_hoa_seattle.json`       | ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 | Condo @ 95% LTV with HOA + PMI; verdict=WATCH (cascade Level 3 STRESS-INCOME-SHOCK)     |
| `sfh_jumbo_bay_area.json`           | ANLZ-01, ANLZ-02, ANLZ-03, VERD-01 | Jumbo SFH @ 20% DP; price > Santa Clara CA conforming → Jumbo30 row; FHA/Conv ineligible |

## Why synthetic, not live (D-02 inherited from Phase 11)

- **Determinism:** tests must produce identical bytes across runs and machines.
- **Zero recurring cost:** no Zillow API key; no FRED live fetch in CI.
- **Airgap-safe:** tests run with network disabled.
- **Contract-is-shape:** fixtures pin the AnalysisReport schema, not market data.

synthetic-only per Phase 11 D-02 inherited.

## Capture-and-sanitize recipe (Phase 14-specific)

Each fixture's `expected_response` is HAND-CALCULATED with citation comments
in the `notes` field — never auto-captured from the engine. This is the
Phase 4 / Phase 8 golden-value oracle discipline (CLAUDE.md "Hand-calculated
golden-value fixtures with citation comments").

1. Derive monthly_pi via `lib.amortize.build_schedule` against a `Loan(principal,
   annual_rate, term_months, loan_type)` constructed from the scenario inputs.
   The four pinned Phase 3 oracles in `tests/fixtures/golden_pmt.json`
   anchor the underlying numpy-financial PMT path:
   - Wikipedia: $200k @ 6.5%/30yr → $1,264.14
   - CFPB LE:   $162k @ 3.875%/30yr → $761.78
   - Computed:  $400k @ 6.5%/30yr → $2,528.27
   - Computed:  $200k @ 7%/15yr → $1,797.66
2. Add escrow (tax/12 + insurance/12 + HOA + monthly_mi) for the PITI composition
   per Pitfall 6 (quantize ONCE at the end).
3. Compute back-end DTI = (PITI + monthly_obligations) / monthly_income.
4. Cite the hand-calc derivation in `notes`: e.g., "Conv30 @ 6.5%/30yr on
   $500k principal → build_schedule.monthly_pi = $3160.34".
5. Audit fields (`source_url`, `zpid`, `fetched_at`) default to synthetic values
   per Plan 14-06 B-3 fix:
   - `source_url`: `"https://www.zillow.com/homedetails/synthetic/<n>_zpid/"`
   - `zpid`: a digit-only string (e.g., `"1"`, `"2"`, `"3"`)
   - `fetched_at`: ISO-8601 UTC string with Z suffix (e.g., `"2026-05-17T00:00:00Z"`)

## When to regenerate

- **After any change to `lib/property_analysis.py` `analyze()` body** that
  changes the AnalysisReport shape — every fixture's `expected_response`
  must be re-hand-calculated against the new shape.
- **After any `data/reference/*.yml` refresh** (Phase 16 owns the
  refresh — Phase 14 fixtures inherit). Re-derive PITI cells if FHA MIP
  rates, conforming limits, or IRS Pub 936 caps move.
- **After any change to `lib/property_verdict.py`** cascade order — re-pin
  the `expected_response.verdict.level` and `reasons[]` per fixture.

## What NOT to put here

- **No real addresses.** Synthetic-only per Phase 11 D-02 inherited. Use
  `123 Synthetic Way, Seattle, WA 98101` style values. ZIP stays real (the
  ZIP is not PII on its own; matches Phase 13 README precedent).
- **No AI-attribution markers.** Per the project-wide CLAUDE.md global rule:
  no co-author trailers, no AI-tooling generation footnotes, no AI-assistance
  evidence in any form.
- **No raw lender quotes.** Conventional PMI rates are bureau-specific
  (MGIC / Genworth / Radian all differ); use the RESEARCH Pitfall 1
  estimated value `Decimal("0.0075")` annualized.
- **No `config/household.yml` values.** Synthetic financial profiles only —
  fixtures are committed to a public repo and household.yml may contain
  real numbers.

## Cascade-level pinning (W-1 fix per Plan 14-06)

Each fixture's `expected_response.verdict.level` is pinned to EXACTLY ONE of
`"GO" | "WATCH" | "NO_GO"` (never the string `"GO or WATCH"`). The choice is
derived by hand-tracing the `lib.property_verdict.synthesize` cascade levels
1-5 at fixture-construction time and documented in the fixture's `notes`
field with the cascade-level explanation.
