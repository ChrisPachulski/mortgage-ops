# ARM Mechanics — mortgage-ops Phase 5 Reference

This document records the conventions implemented by `lib/arm.py` (ARM
adjustable-rate mortgage engine) and pairs each convention with its
regulatory citation. All section numbers and URLs were verified on
2026-04-30 against the live Selling Guides + CFPB explainer.

Cited from `lib.arm.ARMTerms.__doc__` per ROADMAP SC-5.

---

## 1. Reset Month Convention

The rate change applies at the START of the post-fixed-period month:

| Product | Initial fixed period | First reset month | Subsequent resets |
|---------|---------------------|-------------------|-------------------|
| 5/1     | 60 months            | Month 61          | Every 12 months (73, 85, ...) |
| 7/1     | 84 months            | Month 85          | Every 12 months (97, 109, ...) |
| 10/1    | 120 months           | Month 121         | Every 12 months (133, 145, ...) |
| 5/6 SOFR| 60 months            | Month 61          | Every 6 months (67, 73, 79, ...) |

The off-by-one — payment at month 60 still uses the initial rate; payment
at month 61 uses the new rate — is the source of PITFALL 5 in
`.planning/research/PITFALLS.md`. ROADMAP SC-3 mandates fixtures covering
BOTH directions (month 59 still old rate; month 61 already new rate).

**Citations:**
- Fannie Mae Selling Guide §B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)" (last updated 2025-12-10):
  https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms
- Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b) (delivery instructions for ARM mortgages)
- Freddie SOFR-Indexed ARMs product page (3/6, 5/6, 7/6, 10/6 reset cadence):
  https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms
- ABT Bank "5/6, 7/6 & 10/6 SOFR ARM Disclosure" (worked example confirming month 61
  first reset, every-6-months thereafter, 2/1/5 caps for the 5/6 product):
  https://www.abt.bank/wp-content/uploads/2022/09/Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf

> **Citation correction note (2026-04-30):** The originally locked
> references in CONTEXT.md D-08 cited a Fannie subsection in the B5
> chapter (which returned 404; that section group is about VA-related
> underwriting, not ARMs) and a four-digit Freddie section number that
> is now stale (modern Freddie URLs use §6302.7(b) + Chapter 4203).
> Both have been corrected to the verified-current sections shown
> above. The forbidden legacy tokens are deliberately omitted here so
> that automated tests can assert their absence as a regression guard.

---

## 2. Cap Precedence

Three caps apply to every reset event:

| Cap | Applied at | Formula |
|-----|------------|---------|
| `initial_cap_bps` | First reset only (epoch_idx == 1) | `prior_rate + initial_cap_bps / 10000` |
| `periodic_cap_bps` | Every reset after the first | `prior_rate + periodic_cap_bps / 10000` |
| `lifetime_cap_bps` | Every reset (a single ceiling for the loan's life) | `note_rate + lifetime_cap_bps / 10000` |

The binding ceiling for any reset = `min(applicable_cap_ceiling, lifetime_ceiling)`.
The `applied_cap` field on `ResetEvent` records WHICH constraint bound the new rate
(`"initial"`, `"periodic"`, `"lifetime"`, `"floor"`, or `"none"`); D-10 citation-coverage
requires every Literal value to be exercised by at least one fixture.

**Citations:**
- Fannie Mae Selling Guide §B2-1.4-02 (cap structure, periodic cap precedence)
- Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b)
- CFPB §1951 (lifetime cap explainer):
  https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/

---

## 3. Floor Algebra

The post-reset rate is never below the effective floor:

```
effective_floor = max(margin_bps / 10000, floor_rate)
```

`floor_rate` is REQUIRED on the `ARMTerms` model — there is no default and no
implicit margin fallback. This is a deliberate "fail loud, no inference" choice
(project root coding-standards file, money discipline section + the project's
"engine owns the numbers" doctrine): every caller must explicitly choose a floor.

Fannie Mae Selling Guide §B2-1.4-02 specifies:
> "Mortgage interest rates may never decrease to less than the ARM's margin,
> regardless of any downward interest rate cap."

The engine's `max(margin, floor_rate)` is a strict generalization (allows the
caller to set a configured floor higher than margin); industry-standard but
engine-specific in the sense that the configured floor is an extension beyond
the regulatory minimum.

**Citations:**
- Fannie Mae Selling Guide §B2-1.4-02 (no rate decrease below margin)
- Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b)

---

## 4. Quantization

All `Rate`-typed values flow through `lib.money.quantize_rate(...)` at 6 decimal
places using ROUND_HALF_UP (project root coding-standards file, money discipline
section; Phase 4 D-09 / Phase 5 D-14).

Quantize ONCE at end-of-period; never quantize mid-calculation (Phase 1 PITFALLS,
Phase 3 D-04 inherited).

The 6-decimal-place quantum matches `lib.models.Rate` constraint
(`Annotated[Decimal, Field(max_digits=7, decimal_places=6)]`). Values computed
via division — LTV, DTI, fully-indexed ARM rate — can otherwise produce 28-digit
Decimals that the model rejects.

**Engine choice; not regulator-mandated.** Selling Guides specify the cap formulas
but not the rate quantum. The 6-decimal choice aligns with project's `lib.models.Rate`
type contract (Phase 1).

---

## 5. Negative Amortization OUT of Scope

Phase 5's engine assumes the per-period payment is recomputed at each epoch via
`npf.pmt(period_rate, remaining_term, remaining_balance)`. Negative-amortization
products — Option ARM, payment-cap ARMs where the borrower may pay less than
full interest — are explicitly OUT of v1 (CONTEXT.md D-12).

Conventional fully-amortizing ARMs only: every payment fully covers interest;
principal balance trends to zero by the loan's term_months.

Add support only if a real consumer needs to model these products (rare for
personal-use household analysis).

**Citation:** CONTEXT.md D-12 (project decision).

---

## 6. `index_series_id` Semantics

`ARMTerms.index_series_id` is metadata only in Phase 5: a free-form string
identifying the rate index ("MORTGAGE30US", "SOFR1Y", etc.). The engine does
NOT look up the index value at runtime — Phase 5 takes caller-supplied
`assumed_index_rate` + optional `index_path` overrides per D-01.

Phase 12 will integrate the FRED MCP server (`stefanoamorelli/fred-mcp-server`)
to populate `assumed_index_rate` from `MORTGAGE30US` weekly value at SKILL.md
narration time. At that point `index_series_id` may be tightened from a free-form
string to a Literal-or-enum constraint mapping to FRED series IDs.

**Citation:** Phase 12 plans (deferred); CONTEXT.md D-13.

---

## 7. Teaser-ARM Lifetime Cap Base — Engine Choice

For non-teaser ARMs, `loan.annual_rate == initial_rate == note_rate` and the
lifetime ceiling computation is unambiguous: `note_rate + lifetime_cap_bps / 10000`.

For TEASER ARMs, where `loan.annual_rate < note_rate` (e.g., a 3% teaser
introductory rate with a 5% post-teaser note rate), there are two valid conventions:

- **Engine choice (locked in CONTEXT.md D-02):** Lifetime ceiling = `note_rate + lifetime_cap_bps / 10000`.
  For the example above (note_rate=0.05, lifetime_cap_bps=500), ceiling = 0.10.
  Callers supply the post-teaser note rate explicitly via `arm_terms.note_rate`;
  this engine produces a 10% ceiling.
- **CFPB §1951 description:** "the rate can never be more than five percentage
  points either higher or lower from the **initial rate**." For the same
  example with initial=0.03, this would yield a ceiling of 0.08 (3pp lower).

The engine deliberately uses the post-teaser `note_rate` as the lifetime base
because that matches industry practice for teaser products and is the convention
in Fannie B2-1.4-02 "Standard ARM" worked examples (where teaser products use
the post-teaser rate as the regulatory note rate). The CFPB phrasing is a
consumer-explainer simplification that conflates teaser and non-teaser ARMs.

**Disclosed as explicit engine choice** rather than left silent so a teaser-rate
ARM consumer (e.g., Phase 8 stress, Phase 11 amortization-agent) gets a
reproducible 10% ceiling regardless of which convention the user expected.

**Citations:**
- CFPB §1951 (alternative convention):
  https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/
- Fannie Mae Selling Guide §B2-1.4-02 (industry convention; engine-aligned)

---

## Appendix — Citation Index

| URL | Section / Anchor | Last verified |
|-----|------------------|----------------|
| https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms | §B2-1.4-02 ARM eligibility, cap structure, floor convention | 2026-04-30 (last updated 2025-12-10) |
| https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms | Freddie SOFR-Indexed ARMs (3/6, 5/6, 7/6, 10/6) | 2026-04-30 |
| https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/ | CFPB Ask CFPB §1951 ARM rate caps | 2026-04-30 |
| https://www.abt.bank/wp-content/uploads/2022/09/Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf | ABT Bank 5/6, 7/6 & 10/6 SOFR ARM Disclosure (5/6 product: 2/1/5 caps) | 2026-04-30 (frozen lender artifact, 2022; replaced AmericU URL after 404 confirmed) |

Annual re-validation cadence: each calendar year, confirm each URL still
resolves; if any have moved, update the index above.
