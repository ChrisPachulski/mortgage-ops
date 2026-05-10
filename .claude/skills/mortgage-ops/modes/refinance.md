# Mode: refinance — Refi NPV decision (current vs new loan)

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here when the user uses "refi" / "refinance" verb anywhere in the
prompt. The refi verb wins precedence over `arm` / `amortize` / `stress`
vocabulary (SKILL.md routing precedence rule 2). Examples (UI-SPEC §a
rows 5-6):

- "Should I refi my current 7.125% / 28-years-remaining loan into a
  6.0% / 30yr?"
- "Worth refinancing if I can get 5.875%?"
- "Refi cash-out: pull $50k at 6.0% / 30yr"
- "Is a refi worth it after the rate drop?"

Do NOT route here if the prompt is pure NPV without the refi verb
(unusual; route to `compare`).

### AMBIGUITY RULE (UI-SPEC §a Case 1)

If the prompt mentions BOTH "refi" / "refinance" AND "ARM" (or "5/1",
"7/1", "10/1"), route HERE (refinance), pass `loan_type: "arm"` +
`arm_terms: {...}` to the new-loan side. Do NOT route to `arm`
standalone — that mode is for ARM modeling against an existing or
hypothetical loan, not against a refi-decision pair. The refi NPV is
the user's intent; the ARM is the target product.

If the prompt mentions BOTH "refi" AND "stress" (or sweep / shock
verb), see UI-SPEC §a Case 3: route to refinance, dispatch the sweep
as inner loop (Phase 11 stress-test-agent forward-link applies).

## What scripts to call

Single script: `.claude/skills/mortgage-ops/scripts/refi_npv.py` (Phase 6
SHIPPED; relocated by Plan 10-01).

Run `--help` first. Build the JSON input matching the discriminator
field `refi_kind` (one of `rate_and_term` or `cash_out`):

```json
{
  "refi_kind": "rate_and_term",
  "old_loan_balance": "300000.00",
  "old_annual_rate": "0.07125",
  "old_remaining_months": 336,
  "new_annual_rate": "0.06000",
  "new_term_months": 360,
  "closing_costs": "5500.00",
  "discount_rate_annual": "0.05000",
  "analysis_horizon_months": null,
  "after_tax_mode": false,
  "marginal_tax_rate": null,
  "filing_status": null,
  "has_grandfathered_debt": false,
  "new_loan_monthly_pi_override": null
}
```

For cash-out: set `refi_kind: "cash_out"`, add `cash_out_amount`, set
`new_principal = old_loan_balance + cash_out_amount`.

For after-tax mode (D-09 opt-in): set `after_tax_mode: true`, supply
`marginal_tax_rate` AND `filing_status` together.

Invoke:

```bash
python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi.json
```

Output: JSON `RefiResponse` with `npv`, `breakeven_months`, monthly
P&I delta, total-interest delta, sign-validated cashflows.

Persist via `insert-scenario`, then Save Report per `_shared.md`.

## What to narrate

Lead with the verdict. Use the canonical "answer + provenance" template:

> The refi has positive NPV: **+$8,427.16** at a 5.000% discount rate
> over the new 360-month term *(computed by `refi_npv.py` at
> 2026-05-10 14:32:11)*. Breakeven: **18 months**.
>
> Monthly P&I drops from **$2,041.55** to **$1,798.65** — a **$242.90**
> savings each month. After closing costs of **$5,500.00**, you
> recoup the upfront cost at month 18.
>
> Total interest (full new term): **$347,514.00** vs **$485,231.20**
> on the old loan — **$137,717.20** saved over 30 years.

Apply `_profile.md` `verbosity` knob (D-VOICE-02). For `concise`, drop
the breakdown; for `verbose`, add the full cashflow table.

If `npv` is NEGATIVE, lead with that ("Negative NPV: -$X — refinance
is NOT worth it on these inputs"); do NOT bury the verdict.

## Edge cases

- **Missing `discount_rate_annual`:** REQUIRED per D-05. Ask the user;
  reference `references/refi-npv.md` for guidance ("borrower after-tax
  marginal opportunity cost, 5-7% typical").
- **Cash-out with PMI breach (LTV > 0.80):** v1 does NOT recompute PMI
  on LTV change (D-08). Surface this caveat to the user; if they need
  PMI in the new payment, supply
  `new_loan_monthly_pi_override` (D-10) computed from
  `affordability.py`.
- **Pre-TCJA grandfathered loan:** set `has_grandfathered_debt: true`
  for after-tax mode (uses the $1M cap instead of $750k post-2017).
- **Refi + ARM:** see AMBIGUITY RULE above. Pass arm_terms inside the
  new-loan request; route stays here.
- **Refi + stress:** route here, dispatch the sweep as inner loop. If
  N > 5 scenarios, follow the modes/stress.md existence-check seam to
  defer to `.claude/agents/stress-test-agent.md`.
- **Float-in-money error:** see `_shared.md` § Error Narration Template.

## RELATED REFERENCES

(Load on demand only.)

- `references/refi-npv.md` — "explain NPV" / "what's the breakeven" /
  "discount rate guidance"
- `references/tax-deductibility.md` — "after-tax mode" / "Pub 936"
- `references/points-breakeven.md` — "are points worth it"
