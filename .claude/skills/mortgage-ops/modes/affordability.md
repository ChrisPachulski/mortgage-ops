# Mode: affordability — DTI/LTV/CLTV/PITI + reverse-affordability

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here when the user uses "afford" / "borrow" / "qualify" / "DTI" /
"can we" vocabulary. The afford verb wins precedence over `amortize`
vocabulary (SKILL.md routing precedence rule 3). Examples (UI-SPEC §a
rows 7-8):

- "How much house can we afford on $250k household income at today's
  rates?"
- "What's the most we can borrow with $100k down and a 43% DTI cap?"
- "Can we qualify for $600k FHA?"
- "Will we be approved at 6.5% with $45k in monthly debts?"

Do NOT route here if:

- "refi" verb present → `refinance`
- Multiple offers + ranking → `compare`
- Pure schedule question → `amortize`

### AMBIGUITY RULE (UI-SPEC §a Case 2)

If the user asks "can I afford X *and* what's the payment", do NOT
make two script calls. The `affordability.py` response already
includes the PITI breakdown (`monthly_pi`, `monthly_taxes`,
`monthly_insurance`, `monthly_pmi`, `monthly_hoa`, `monthly_mip` for
FHA). Narrate from one call. The `monthly_pi` figure inside the
response is byte-identical to what `amortize.py` would have returned
— a second call would be wasteful and adds confusion to provenance.

## What scripts to call

Single script:
`.claude/skills/mortgage-ops/scripts/affordability.py` (Phase 4
SHIPPED; relocated by Plan 10-01).

Run `--help` first. The script supports two modes via the `mode`
discriminator (D-14): `forward` (known loan + property → DTI / LTV
/ CLTV / PITI + blocker list) and `reverse` (known DTI cap + LTV
target → max loan amount).

### Forward mode (known loan + property)

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

REQUIRED rules (per `--help`):
- `household.location.state_fips` (2 digits) + `county_fips` (3 digits)
  for Phase 2 county lookup (e.g., King WA = 53/033).
- `target_loan_type=='va'` requires `household.va` block (region,
  family_size, actual_residual_income).
- `target_loan_type=='conventional'` with LTV > 0.80 requires
  `monthly_pmi` (caller supplies the premium per Open Question #1).
- FHA UFMIP auto-financed into principal; response surfaces
  `financed_loan_amount`.

### Reverse mode (max loan amount)

```json
{
  "mode": "reverse",
  "household": { "...": "from config/household.yml" },
  "max_dti": "0.430000",
  "target_loan_type": "conventional",
  "term_months": 360,
  "annual_rate": "0.070000",
  "down_payment": "100000.00",
  "target_ltv_pct": "0.800000"
}
```

Invoke:

```bash
python .claude/skills/mortgage-ops/scripts/affordability.py --input /tmp/aff.json
```

Output: JSON `AffordabilityResponse` with full PITI breakdown, ratios,
and a blocker precedence list (DTI cap > LTV ceiling > residual income
> reserves).

Persist via `insert-scenario`, then Save Report per `_shared.md`.

## What to narrate

Lead with the answer (yes/no on affordability OR the max loan amount).
Use the canonical "answer + provenance" template:

> Yes, you qualify for **$400,000.00** at 6.500% / 30yr conventional
> *(computed by `affordability.py` at 2026-05-10 14:32:11)*.
>
> Back-end DTI: **42.3%** (under the 43.0% ATR/QM cap). LTV: **80.0%**
> (no PMI needed). Total PITI: **$3,127.45/mo** (P&I $2,528.27 + tax
> $480 + insurance $119 + PMI $0).
>
> Per CFPB §1026.43, the 43.0% back-end ratio is the QM safe harbor;
> non-QM lenders may approve higher with compensating factors.

If a blocker fires, lead with the blocker. Surface the precedence
order (DTI > LTV > residual income > reserves) so the user knows
which constraint to relax. Apply `_profile.md` `citation_density` knob
to scale the regulatory citations.

D-NUM-01 money, D-NUM-02 rates, D-NUM-03 ratios. Never recompute.

## Edge cases

- **`config/household.yml` missing:** surface the friendly error from
  `_shared.md` § Sources of Truth — do NOT auto-create.
- **VA without `household.va` block:** ask the user for region +
  family_size + actual_residual_income (validation will fail
  otherwise).
- **Conventional + LTV > 0.80 without `monthly_pmi`:** ask the user
  for the PMI premium; do NOT default to 0 (silently winning the DTI
  ratio is a trap).
- **APR + APOR mismatch:** both-or-neither (D-19); validation error
  if only one is supplied.
- **Multiple junior liens:** include all in `junior_liens` array
  (CLTV ratio handled by lib).
- **Float-in-money error:** see `_shared.md` § Error Narration Template.

## RELATED REFERENCES

(Load on demand only.)

- `references/affordability-rules.md` — "what's DTI" / "explain
  residual income" / "ATR/QM Pathways"
- `references/gse-limits.md` — "what's the conforming limit" / "jumbo"
- `references/mip-pmi.md` — "MIP rules" / "when does PMI drop off"
