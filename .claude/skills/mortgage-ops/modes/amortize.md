# Mode: amortize — Generate an amortization schedule

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here when the user asks for:

- A monthly payment ("what's the P&I on $X at Y% over Z years?")
- A full amortization schedule ("show me the schedule for…")
- A specific period's interest/principal split ("how much interest in
  year 5?")
- Extra-principal modeling ("what if I pay an extra $500/mo?")
- Biweekly payment modeling ("what does biweekly do?")

Examples (UI-SPEC §a rows 11-12):

- "Show me the amortization schedule for $400k @ 6.5% / 30yr"
- "What's the P&I on $400k at 6.5% over 30 years?"
- "How much interest do I pay in year 5?"
- "What if I add $300/mo to principal starting in month 13?"

Do NOT route here if:

- "refi" / "refinance" verb → `refinance`
- "afford" / "borrow" → `affordability`
- ARM caps / X/Y notation → `arm`

## What scripts to call

Single script: `.claude/skills/mortgage-ops/scripts/amortize.py` (Phase
3 SHIPPED; relocated by Plan 10-01).

Run `--help` first. Build a JSON input matching the documented shape:

```json
{
  "loan": {
    "principal": "400000.00",
    "annual_rate": "0.065000",
    "term_months": 360,
    "origination_date": "2026-05-10",
    "loan_type": "fixed"
  },
  "frequency": "monthly",
  "extra_principal": []
}
```

Optional fields per `--help`:

- `frequency`: `"monthly"` (default) or `"biweekly"`. When biweekly,
  also set `biweekly_mode`: `"true"` (default; 26 actual biweekly
  payments) or `"half-monthly"` (24 payments simulating
  half-of-monthly).
- `extra_principal`: list of `{period, amount, recurring}` entries.
  E.g. `[{"period": 13, "amount": "300.00", "recurring": true}]` for
  $300/mo extra principal starting at month 13.

All money/rate fields MUST be JSON strings (Pydantic v2 strict; D-19).

Invoke:

```bash
python .claude/skills/mortgage-ops/scripts/amortize.py --input /tmp/amortize.json
```

Output: JSON `Schedule` to stdout, exit 0. Validation error: 6-key
envelope on stderr, exit 2.

Persist via `insert-scenario`, then Save Report per `_shared.md`.

## What to narrate

Use the canonical "answer + provenance" template:

> Your monthly P&I is **$2,528.27** *(computed by `amortize.py` at
> 2026-05-10 14:32:11)*.
>
> Total interest over the 360-month term: **$510,177.94**. The first
> month's interest is **$2,166.67**; the first month's principal is
> **$361.60**. Crossover (where principal exceeds interest) at
> month **195**.
>
> *Full schedule saved to `reports/047-amortize-2026-05-10.md`.*

Do NOT recompute any number. Every dollar figure must come from the
JSON output verbatim. Do NOT inline 360 schedule rows in chat —
narrate headline figures + reference the saved report file.

For extra-principal scenarios, surface the term reduction and total
interest delta:

> With $300/mo extra principal starting month 13, your effective
> term shortens to **264 months** (was 360). Total interest
> **$382,891.45** (was $510,177.94) — saving **$127,286.49**.

D-NUM-01 money, D-NUM-02 rates, D-NUM-03 ratios. Apply
`_profile.md` `verbosity` knob (D-VOICE-02).

## Edge cases

- **No principal in prompt:** ask "What's the loan principal?" — do
  not guess.
- **No rate in prompt:** check FRED MCP (Phase 12); if available,
  offer "Use today's MORTGAGE30US ({rate}%)?". Otherwise ask.
- **Biweekly without `biweekly_mode`:** the default is `"true"` (26
  payments). Be explicit if the user wants `"half-monthly"`.
- **Negative `extra_principal.amount`:** validation error; surface
  the 6-key envelope.
- **Float-in-money error:** see `_shared.md` § Error Narration Template.

## RELATED REFERENCES

(Load on demand only.)

- `references/amortization-formulas.md` — "explain the formula" /
  "PMT" / "how is P&I calculated"
- `references/spreadsheet-conventions.md` — "why don't your numbers
  match Excel" / "8x table convention"
