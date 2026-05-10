# Mode: evaluate — Single-loan analysis (judgment + math)

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here when the user asks for a judgment about a SINGLE offer/loan AND
expects both the payment math AND the affordability angle (DTI / LTV / CLTV
/ PITI). Examples (UI-SPEC §a rows 1-2):

- "Should I lock the 6.5% rate Wells offered me on $400k?"
- "Is this 6.5% / 30yr offer any good?"
- "We're staring down a $480k loan at 6.875% — does that work for us?"
- "Wells offered 6.5%/30yr on $400k. Smart move?"

Do NOT route here if:

- Multiple offers to compare → `compare`
- Refi verb anywhere ("refi", "refinance") → `refinance`
- "afford" / "borrow" / "qualify" with no specific offer → `affordability`
- Pure schedule question ("show me the amortization") → `amortize`
- ARM-specific vocabulary ("5/1", "7/1", caps) without judgment → `arm`

## What scripts to call

`evaluate` is the ONLY mode that composes TWO scripts. Other modes route to
a single script. Call BOTH in this order:

### Script 1: `.claude/skills/mortgage-ops/scripts/amortize.py`

Run `--help` first if you have not invoked it this session.

Build the loan input JSON (Phase 1 Loan model):

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

All money/rate fields MUST be JSON strings (Pydantic v2 strict; D-19).
Invoke:

```bash
python .claude/skills/mortgage-ops/scripts/amortize.py --input /tmp/eval-amortize.json
```

Output: JSON `Schedule` to stdout. Pull `monthly_pi`, `total_interest`,
`total_payments` for the headline.

### Script 2: `.claude/skills/mortgage-ops/scripts/affordability.py`

Compose the loan inputs above with the user's `config/household.yml`
data into a forward-mode AffordabilityRequest:

```json
{
  "mode": "forward",
  "household": { "...": "from config/household.yml" },
  "max_dti": "0.430000",
  "target_loan_type": "conventional",
  "term_months": 360,
  "annual_rate": "0.065000",
  "loan_amount": "400000.00",
  "property_value": "500000.00",
  "monthly_pmi": "150.00",
  "junior_liens": [],
  "apr": null,
  "apor": null
}
```

Invoke:

```bash
python .claude/skills/mortgage-ops/scripts/affordability.py --input /tmp/eval-affordability.json
```

Output: JSON `AffordabilityResponse` with DTI / LTV / CLTV / PITI breakdown
+ blocker precedence list.

### Persist + Save

Per `_shared.md` § Save Report — call
`node orchestration/db-write.mjs insert-scenario` once with the merged
request, then run the Save Report flow with the resulting `<scenario_id>`.

## What to narrate

Use the canonical "answer + provenance" template from UI-SPEC §g. Merge
both JSON outputs into ONE narration:

> Your monthly P&I is **$2,528.27** *(computed by `amortize.py` at
> 2026-05-10 14:32:11)*.
>
> Total PITI is **$3,127.45/mo** (P&I $2,528.27 + tax $480 + insurance
> $119 + PMI $0). Back-end DTI: **42.3%** (under the 43.0% ATR/QM cap).
> LTV: **80.0%** *(computed by `affordability.py` at 2026-05-10
> 14:32:14)*.
>
> Total interest over the 360-month term: **$510,177.94**.

Use D-NUM-01..04 formatters: money `$1,264.14`, rates `6.500%`, ratios
`43.0%`. NEVER recompute; every figure traces to a script. Apply
verbosity from `_profile.md` (D-VOICE-02 mapping in `_shared.md`).

If the affordability response includes a blocker (DTI cap exceeded, LTV
> ceiling, etc.), surface it as the lead sentence and treat it as the
"answer" — judgment requires the blocker to be visible.

## Edge cases

- **No principal in prompt:** ask "What's the loan principal?" — do not
  guess.
- **No rate in prompt:** check FRED MCP (Phase 12); if available, offer
  "Use today's MORTGAGE30US ({rate}%)?". Otherwise ask.
- **No `config/household.yml`:** surface the friendly error from
  `_shared.md` § Sources of Truth — do NOT auto-create the file.
- **Float-in-money error:** see `_shared.md` § Error Narration Template
  (UI-SPEC §c worked example 1). Show the field name, the corrected
  JSON shape; offer to retry.
- **Affordability blocker:** lead with the blocker; still narrate the
  P&I from `amortize.py` so the user knows the unblocked alternative.
- **APR requested:** invoke `scripts/apr_reg_z.py` separately and label
  per SKLL-APR-1 ("estimated APR" literal text).

## RELATED REFERENCES

(Load on demand only — D-09 progressive disclosure.)

- `references/amortization-formulas.md` — "explain the formula" / "PMT"
- `references/affordability-rules.md` — "what's DTI" / "explain ATR/QM"
- `references/apr-reg-z.md` — "explain APR" / "what's APOR"
- `references/spreadsheet-conventions.md` — "why don't your numbers match Excel"
