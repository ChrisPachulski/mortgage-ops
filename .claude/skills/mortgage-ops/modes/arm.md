# Mode: arm — ARM modeling (5/1, 7/1, 10/1, 5/6 with caps + reset paths)

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here when the user uses ARM vocabulary AND no refi verb. ARM
loses precedence to `refinance` (SKILL.md routing precedence rule 6 —
"ARM" / "X/Y" + no refi verb). Examples (UI-SPEC §a rows 13-14):

- "Model a 7/1 ARM at 6.0% intro with 5/2/5 caps"
- "If SOFR climbs to 4.5% by year 8, what's my reset payment on this
  5/1?"
- "Show me a 10/1 ARM amortization with 2/2/5 caps"
- "What's the worst-case payment on a 5/6 SOFR ARM?"

Do NOT route here if:

- "refi" / "refinance" verb present → `refinance` (the AMBIGUITY RULE
  in `modes/refinance.md` makes refi the outer mode; ARM is the
  target product)
- Single fixed-rate scenario → `amortize`
- Multi-scenario rate sweep → `stress` (with `arm-reset` mode)

## What scripts to call

Single script:
`.claude/skills/mortgage-ops/scripts/arm_simulate.py` (Phase 5 SHIPPED;
relocated by Plan 10-01).

Run `--help` first. Build the JSON input matching the documented shape
(D-01 + D-06):

```json
{
  "loan": {
    "principal": "400000.00",
    "annual_rate": "0.060000",
    "term_months": 360,
    "origination_date": "2026-05-10",
    "loan_type": "arm"
  },
  "arm_terms": {
    "initial_period_months": 84,
    "reset_period_months": 12,
    "initial_cap_bps": 500,
    "periodic_cap_bps": 200,
    "lifetime_cap_bps": 500,
    "floor_rate": "0.020000",
    "margin_bps": 275,
    "index_series_id": "SOFR1Y"
  },
  "assumed_index_rate": "0.050000",
  "index_path": []
}
```

Notes on ARM-specific fields (per `--help`):

- `arm_terms`: 8 required fields + optional `note_rate`
  (`initial_period_months`, `reset_period_months`, `initial_cap_bps`,
  `periodic_cap_bps`, `lifetime_cap_bps`, `floor_rate`, `margin_bps`,
  `index_series_id`).
- `assumed_index_rate`: caller-supplied fallback when `index_path` is
  empty (Phase 5 D-13 caller-supplies-index discipline; FRED MCP
  populates at narration time per Phase 12).
- `index_path`: list of `{period, value}` entries overriding
  `assumed_index_rate` at named periods (e.g.,
  `[{"period": 85, "value": "0.045000"}]` for the first reset).

All money/rate fields MUST be JSON strings.

Invoke:

```bash
python .claude/skills/mortgage-ops/scripts/arm_simulate.py --input /tmp/arm.json
```

Output: JSON `Schedule` with applied-cap markers per period. Persist
via `insert-scenario`, then Save Report per `_shared.md`.

## What to narrate

Use the canonical "answer + provenance" template. ARM mode uses
**D-NUM-04 bps formatting** for margin / caps / floors (basis points
with parenthesized percent). Other rate references use D-NUM-02
percent-only.

> Your initial monthly P&I is **$2,398.20** at the 6.000% intro rate
> *(computed by `arm_simulate.py` at 2026-05-10 14:32:11)*.
>
> ARM terms: **7/1 SOFR** with caps **200 bps (2.00%)** periodic /
> **500 bps (5.00%)** lifetime / margin **275 bps (2.75%)** /
> floor **200 bps (2.00%)**.
>
> **First reset** (month 85): index path puts SOFR at **4.500%**;
> fully-indexed rate is **7.250%** (margin 275 bps + index 4.500%),
> capped at periodic_cap of **200 bps (2.00%)** above intro → new
> rate **8.000%**. New monthly P&I: **$2,838.97**.
>
> **Lifetime cap** (month 85+): rate cannot exceed **11.000%**
> (intro + 500 bps lifetime).

D-NUM-04 examples in stock formatting:
- `periodic_cap: 200 bps (2.00%)`
- `lifetime_cap: 500 bps (5.00%)`
- `margin: 275 bps (2.75%)`
- `floor: 200 bps (2.00%)`

For the actual rate at any period, use D-NUM-02 percent-only:
**6.500%**, **7.250%**, **8.000%**.

Apply `_profile.md` `verbosity` knob (D-VOICE-02). For `concise`,
collapse to intro P&I + worst-case P&I + applied caps.

## Edge cases

- **No `arm_terms` in prompt:** ask the user; do NOT default to
  industry-standard caps (5/2/5, 2/2/5) silently — the cap structure
  is load-bearing for the worst-case payment.
- **No `assumed_index_rate` AND empty `index_path`:** validation
  error; ask the user for current SOFR or offer to use FRED MCP
  (Phase 12).
- **`floor` > current `assumed_index_rate`:** the floor binds; surface
  this in narration ("rate cannot drop below {floor}% even if the
  index falls").
- **Periodic cap binding before lifetime cap:** narration must
  surface which cap actually applied at each reset (the JSON output
  flags `applied_cap` per period).
- **5/6 SOFR ARM (semi-annual reset):** set
  `reset_period_months: 6`. Narration should note the more-frequent
  reset cadence.
- **Float-in-money error:** see `_shared.md` § Error Narration Template.

## RELATED REFERENCES

(Load on demand only.)

- `references/arm-mechanics.md` — "explain the cap structure" /
  "what does 5/1 mean" / "how does the reset work"
- `references/amortization-formulas.md` — "explain the formula" /
  "PMT"
