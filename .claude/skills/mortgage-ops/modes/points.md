# Mode: points — Discount-points breakeven

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md FIRST (per D-10), then this file.

## When to invoke

Route here for a single-loan points decision: "are points worth it",
"buy down the rate", "discount points", or "points breakeven".
If the prompt compares multiple lender offers, route to `compare` unless the
only requested judgment is the points breakeven for one offer.

## What scripts to call

Single script: `.claude/skills/mortgage-ops/scripts/points_breakeven.py`.

Run `--help` first. Use `mode: "from_loans"` when the prompt supplies the
with-points and no-points loan terms; use `mode: "from_savings"` only when
monthly savings is already known.

```bash
python .claude/skills/mortgage-ops/scripts/points_breakeven.py --input /tmp/points.json
```

Persist via `insert-scenario --kind points`, then Save Report per `_shared.md`.

## What to narrate

Lead with `decision`, then report both `simple_breakeven_months` and
`npv_breakeven_months`. Mention the caller-supplied `discount_rate_used`
because it drives the NPV breakeven.

## RELATED REFERENCES

- `references/points-breakeven.md` — "are points worth it" / "points breakeven"
