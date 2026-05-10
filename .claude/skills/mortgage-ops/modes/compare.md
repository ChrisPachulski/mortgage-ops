# Mode: compare — Multi-offer ranking (2-5 offers side-by-side)

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here when the user provides 2+ offers and asks for a ranking or
side-by-side comparison. Examples (UI-SPEC §a rows 3-4):

- "Compare these three: 6.5% / 30yr vs 6.0% / 30yr with 1.5 points vs
  5.875% / 15yr"
- "Which is better, the BoA 30-year or the Chase 15-year?"
- "Rank these four offers by total cost"
- "Side-by-side these two and tell me which wins"

Do NOT route here if:

- Single offer + judgment → `evaluate`
- "refi" / "refinance" verb → `refinance` (refinance can compare too,
  but the refi NPV scenario is the inner loop, not the outer mode)
- Pure schedule question ("show me the amortization") → `amortize`

## What scripts to call

Single script invoked once per offer:
`.claude/skills/mortgage-ops/scripts/refi_npv.py` (Phase 6 SHIPPED;
relocated by Plan 10-01).

Run `--help` first to see the JSON-input shape. The compare flow uses
`refi_npv.py` in rate-and-term mode with each offer as the "new loan"
side and a fixed reference baseline (the user's current loan or a
chosen reference offer) as the "old loan" side. This produces a
per-offer NPV that is directly rankable.

For a pure rate/term/points comparison without a current-loan baseline,
construct synthetic identical "old" sides for each comparison so the
relative NPV deltas isolate the offer differences. Otherwise, use
`scripts/amortize.py` per offer to gather monthly_pi + total_interest,
then narrate the ranking from those scalars.

Build per-offer JSON. Example (rate-and-term refi mode):

```json
{
  "refi_kind": "rate_and_term",
  "old_loan_balance": "400000.00",
  "old_annual_rate": "0.06500",
  "old_remaining_months": 360,
  "new_annual_rate": "0.06000",
  "new_term_months": 360,
  "closing_costs": "5500.00",
  "discount_rate_annual": "0.05000",
  "analysis_horizon_months": 60,
  "after_tax_mode": false,
  "marginal_tax_rate": null,
  "filing_status": null,
  "has_grandfathered_debt": false,
  "new_loan_monthly_pi_override": null
}
```

Invoke once per offer:

```bash
python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/compare-offer-N.json
```

Persist each scenario via `insert-scenario`, then Save Report once
with the merged narration per `_shared.md` § Save Report.

## What to narrate

Use the canonical "answer + provenance" template, BUT lead with the
ranking. Example:

> Top offer: **Chase 5.875% / 15yr** *(computed by `refi_npv.py` at
> 2026-05-10 14:32:11)*. Lifetime interest **$129,452.18**, monthly
> P&I **$3,341.76**.
>
> Ranked (lowest lifetime interest first):
> 1. Chase 5.875% / 15yr — $129,452.18 interest, $3,341.76/mo
> 2. BoA 6.000% / 30yr (1.5 pts) — $431,676.40 interest, $2,398.20/mo
> 3. Wells 6.500% / 30yr (0 pts) — $510,177.94 interest, $2,528.27/mo
>
> Caveat: lifetime interest favors shorter terms; monthly affordability
> may favor the longer terms. Apply your `_profile.md` ranking weights
> if you want a single composite score.

Apply `_profile.md` `citation_density` knob to control how many
regulatory citations appear in the narration (D-VOICE-02 mapping).
Money D-NUM-01, rates D-NUM-02.

## Edge cases

- **Only 1 offer provided:** route to `evaluate` instead — do not
  compare a single offer against itself.
- **More than 5 offers:** narrow the scope. Ask the user to drop the
  least promising ones; compare-ranking degrades past 5 (UI-SPEC §b
  density rule).
- **Mismatched terms (15yr vs 30yr):** lead with this in the narration
  — total-interest comparison is meaningful but monthly-affordability
  comparison is near-meaningless without a horizon.
- **Missing `closing_costs` for one offer:** ask the user; do NOT
  default to 0 (silently winning the ranking on a missing field is a
  trap).
- **Float-in-money error:** see `_shared.md` § Error Narration Template.

## RELATED REFERENCES

(Load on demand only.)

- `references/refi-npv.md` — "explain NPV" / "what's the breakeven"
- `references/points-breakeven.md` — "are points worth it"
- `references/amortization-formulas.md` — "explain the formula"
