# Phase 5: ARM Modeling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 05-arm-modeling
**Areas discussed:** Index supply model, Rate-update formula at reset, Schedule output + epoch stitching, Test oracle strategy

---

## Index supply model

| Option | Description | Selected |
|--------|-------------|----------|
| Flat assumed_index_rate only | Single Decimal `assumed_index_rate` held constant at every reset after the initial fixed period. Simplest. Phase 8 stress externally varies it across runs. | |
| Flat + per-reset overrides | `assumed_index_rate` (Decimal, REQUIRED) AND optional `index_path: list[{period: int, value: Decimal}]` keyed to reset-trigger periods. Override wins; otherwise flat. | ✓ |
| Per-reset path only | `index_path: list[Decimal]` of length = number of resets. Caller must count resets. Stricter; no implicit flat fallback. | |
| Per-month index series | `index_history: dict[int, Decimal]` keyed by absolute month; engine looks up the index AT each reset trigger month. Most flexible. | |

**User's choice:** Flat + per-reset overrides
**Notes:** Picked the shape that handles both the simple "what if rates sit flat" question AND Phase 8 stress sweeps directly via the same surface. `assumed_index_rate` REQUIRED (no None); `index_path` optional default `[]`. Override wins at exact reset trigger periods; misalignment fails loud at the request boundary.

---

## Rate-update formula at reset (combined: cap rules + floor + note_rate)

### Round 1 — Clamp ruleset

| Option | Description | Selected |
|--------|-------------|----------|
| Industry standard (5/2/5 conventions) | initial_cap at first reset, periodic_cap subsequently; floor = max(margin, floor_rate or 0); lifetime ceiling vs note_rate. (Recommended) | partial |
| ARM-03 verbatim (periodic-only) | Apply ARM-03 as written; initial_cap_bps captured but UNUSED in v1. Simpler engine; less faithful. | partial |
| Strict floor (no margin fallback) | Industry caps + initial_cap-on-first-reset, BUT floor_rate REQUIRED (no default to margin). | partial |
| Note-rate vs initial-rate distinction | Industry caps + lifetime cap measured against `note_rate` field (separate from Loan.annual_rate). Lets caller model teaser-rate ARMs. | partial |

**User's choice:** "All options" (response noted)
**Notes:** User selected all four; clarification rounds below disambiguate the mutually-exclusive sub-rules.

### Round 2a — Floor algebra

| Option | Description | Selected |
|--------|-------------|----------|
| Margin fallback (industry default) | When floor_rate is None, effective_floor = margin. Matches Selling Guide convention. (Recommended) | |
| Required floor_rate (fail loud) | floor_rate is REQUIRED (no None / no default). Pydantic rejects requests missing it. | ✓ |

**User's choice:** Required floor_rate (fail loud)
**Notes:** Aligns with project's "fail loud, no inference" discipline (see PROJECT.md money discipline + Phase 4 D-12 max_dti precedent). effective_floor = max(margin, floor_rate); both terms always present.

### Round 2b — Note rate distinction

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — separate note_rate field | ARMTerms gets `note_rate: Rate \| None = None` (defaults to Loan.annual_rate when None). Lifetime cap ceiling = note_rate + lifetime_cap_bps. Supports teaser-rate ARMs. | ✓ |
| No — use Loan.annual_rate as initial_note_rate | Lifetime cap ceiling = Loan.annual_rate + lifetime_cap_bps. No teaser-rate modeling in v1. (Recommended) | |

**User's choice:** Yes — separate note_rate field
**Notes:** Field is OPTIONAL (defaults to Loan.annual_rate when None); supports teaser-rate ARMs without forcing every caller to set it. Common case stays simple.

**Final formula locked (D-02):**
```
fully_indexed = quantize_rate(index + margin_bps/10000)
effective_floor = max(margin_bps/10000, floor_rate)            # floor_rate REQUIRED
applicable_cap_bps = initial_cap_bps if first_reset else periodic_cap_bps
periodic_ceiling = prior_rate + applicable_cap_bps/10000
lifetime_ceiling = (note_rate or loan.annual_rate) + lifetime_cap_bps/10000
ceiling = min(periodic_ceiling, lifetime_ceiling)
new_rate = quantize_rate(clamp(fully_indexed, low=effective_floor, high=ceiling))
```

---

## Schedule output + epoch stitching

### Round 1 — Schedule shape

| Option | Description | Selected |
|--------|-------------|----------|
| Extend Phase 1 Schedule (D-14 pattern) | Add `rate_in_effect: Rate` to Payment + `Schedule.reset_events: list[ResetEvent] = []`. Backwards-compatible. (Recommended) | |
| New ARMSchedule wraps Schedule | `lib.arm.ARMSchedule` containing `schedule: Schedule` (Phase 1) + parallel reset metadata. Phase 1 untouched; downstream branches on type. | |
| Parallel ARMSchedule + ARMPayment | Full parallel hierarchy: ARMSchedule.payments: list[ARMPayment] (subclass Payment + adds rate_in_effect). Most ARM-clarity, doubles model count. | ✓ |

**User's choice:** Parallel ARMSchedule + ARMPayment
**Notes:** Phase 1 Payment / Schedule remain untouched. ARMPayment subclasses Phase 1 Payment via Pydantic v2 inheritance (so list[ARMPayment] is structurally compatible with list[Payment] for Phase 4/8 consumers). New ResetEvent model captures per-reset metadata.

### Round 2 — Period numbering across epochs

| Option | Description | Selected |
|--------|-------------|----------|
| Continuous (1..N) | One unbroken schedule. payments[60].period == 61 (first post-reset month for 5/1). (Recommended) | ✓ |
| Per-epoch restart (1..M each) | Each epoch is its own Schedule rooted at period 1; ARMSchedule holds list[Schedule]. | |

**User's choice:** Continuous (1..N)
**Notes:** Simpler downstream indexing for Phase 4/8 consumers. ResetEvent.period locates each reset boundary in the continuous numbering. final_payment_adjusted applies ONLY to the FINAL epoch per Phase 3 D-09 inheritance.

---

## Test oracle strategy

| Option | Description | Selected |
|--------|-------------|----------|
| MGIC ARM calculator (capture-as-fixture) | 6–8 scenarios captured as PDF/screenshots; expected values transcribed into JSON. | |
| Hand-calc per Freddie Selling Guide | Compute every fixture by hand per Selling Guide formula. No external calculator dep. | |
| MGIC + hand-calc cross-validation | Hand-calc per Selling Guide AND verify against MGIC capture. Both must agree. (Recommended) | ✓ |
| Bankrate + hand-calc cross-validation | Same but Bankrate instead of MGIC. Bankrate consumer-facing; MGIC lender-facing. | |

**User's choice:** MGIC + hand-calc cross-validation (Recommended)
**Notes:** Both oracles must agree EXACTLY (Decimal equality). Disagreement = bug in either implementation OR in our reading of MGIC's tool — surfaces as test failure with both sides logged. Annual re-capture cadence parallels FFIEC for Phase 7 APR. Bankrate deferred to v2 if MGIC + hand-calc disagree on edge cases.

---

## Claude's Discretion

Carried into D-section "Claude's Discretion" of CONTEXT.md:

- `_quantize_rate` helper location (keep in `lib/affordability.py` vs promote to `lib/money.py` as second consumer)
- `ARMRequest` Pydantic shape (flat vs nested composition with `loan: Loan` + `arm_terms: ARMTerms`)
- `IndexPathEntry` placement (inline in `lib/arm.py` vs `lib/models.py`)
- Per-epoch slice strategy (full remaining term + slice, vs term=reset_period_months — first is correct per ARM-05)
- `ARMSchedule.as_phase1_schedule() -> Schedule` adapter (ship only if a downstream consumer needs it)
- JSON-float pre-validation gate factoring (inline vs `scripts/_cli_helpers.py` shared module)
- MGIC capture format (PDF screenshot, HTML snapshot, or direct JSON transcription)

## Deferred Ideas

Carried into `<deferred>` section of CONTEXT.md:

- Option ARM / payment-cap / negative-amortization products (v2; D-12 OUT of v1)
- FRED MCP live index injection (Phase 12)
- Index lookback windows (v2)
- `index_series_id` → FRED enum mapping (Phase 12)
- ARM-aware affordability re-evaluation per reset (Phase 8 stress)
- Stress-test rate-shock + ARM-reset sweeps (Phase 8)
- DuckDB persistence of ARMSchedule + ResetEvent (Phase 9)
- Skill physical relocation of `scripts/arm_simulate.py` (Phase 10)
- `.claude/skills/mortgage-ops/references/arm-mechanics.md` mirror (Phase 10)
- `amortization-agent` / `stress-test-agent` ARM routing (Phase 11)
- Bankrate cross-validation as third oracle (v2)
- Expanded teaser-rate ARM fixture matrix (v2)
- `ARMSchedule.as_phase1_schedule()` adapter (ship-if-needed)
- Stdin-based CLI input (v2)
- Vectorized ARM schedule generation across parameter grid (Phase 8)
- `tests/fixtures/arm/oracle/bankrate_*.pdf` (v2)
- `data/reference/arm-known-products.yml` catalog (Phase 8/10/12 if needed)
- JSON-Schema export of `ARMRequest` (Phase 10 if needed)
- Half-monthly biweekly ARMs (v2 if a real product surfaces)
