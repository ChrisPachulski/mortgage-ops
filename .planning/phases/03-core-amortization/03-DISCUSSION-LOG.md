# Phase 3: Core Amortization - Discussion Log

**Discussed:** 2026-04-29
**Mode:** discuss (default)
**Phase:** 03-core-amortization

This log captures the back-and-forth that produced `03-CONTEXT.md`. It is for human reference (audits, retrospectives) and is NOT consumed by downstream agents (researcher, planner, executor) — they read CONTEXT.md.

---

## Round 1 — Core gray areas

### Q1: Biweekly semantics (AMRT-03)

**Question asked:** What does 'biweekly' mean for the schedule generator?

**Options presented:**
1. True biweekly: `rate/26` per period, 26 payments/yr, naturally shortens term — uses `relativedelta(weeks=2)` (Recommended)
2. Half-monthly: monthly P&I via `npf.pmt` at `rate/12`, debit half every 14 days, interest booked monthly — same total interest as monthly
3. Both — schema field `biweekly_mode: 'true'|'half-monthly'` selects the algorithm at schedule-gen time

**User selected:** Both — schema field selects mode

**Notes:** Real lenders implement both conventions. Conflating them is a known mistake in calculator tools. Decision recorded as D-01.

### Q2: Extra-principal input shape (AMRT-04)

**Question asked:** How should extra-principal payments be specified in the JSON input?

**Options presented:**
1. `list[ExtraPrincipalEntry]` with `{period, amount, recurring}` — single schema covers single, recurring, and per-period (Recommended)
2. Three top-level fields: `extra_monthly`, `extra_one_time`, `extra_per_period` — easier to read in fixtures, three branches in engine
3. Single optional `extra_monthly` field; defer one-shot and per-period to v2

**User selected:** List of period+amount entries (Recommended)

**Notes:** One schema, one validator, one rule. Caller composes complex scenarios from primitives. Decision recorded as D-05.

### Q3: Final-payment cleanup (AMRT-05)

**Question asked:** How is the final-payment cleanup done so balance hits exactly $0.00?

**Options presented:**
1. Adjust ONLY the final period's `principal = prior_balance`, surface `final_payment_adjusted: bool` flag (Recommended)
2. Adjust whole final payment (`prior_balance + final_interest`) — slightly different from #1 only when extra-principal accelerated payoff into a partial period
3. Spread cents drift across last 12 periods — smoother but harder to test against golden values

**User selected:** Adjust final period's principal only (Recommended)

**Notes:** The `final_payment_adjusted: bool` flag is consumed by Phase 6 refi (early-payoff detection) and Phase 8 stress (shortened schedules). Decisions recorded as D-09 + D-10.

### Q4: Script home (AMRT-06)

**Question asked:** Where does `scripts/amortize.py` live in Phase 3?

**Options presented:**
1. Project-root `scripts/amortize.py` for now; Phase 10 migrates to `.claude/skills/.../scripts/` (Recommended)
2. Skill-bundled now: build `.claude/skills/mortgage-ops/scripts/amortize.py` with stub LICENSE + frontmatter — avoid the Phase 10 move
3. Both: project-root + symlink/copy in skill folder — doubles surface area

**User selected:** Project-root `scripts/amortize.py` for now (Recommended)

**Notes:** PROJECT.md decision #8 (scripts INSIDE skill folder) still binding for Phase 10. Phase 3 keeps it simple — no premature `.claude/` skeleton work. Decision recorded as D-17.

---

## Round 2 — Follow-ups opened by Round 1 decisions

The "ship both biweekly modes" decision (D-01) and the "list of entries" extra-principal shape (D-05) both opened sub-questions. The "scripts at project root" choice (D-17) opened a CLI-surface question. Round 2 closed these.

### Q5: Default biweekly_mode

**Question asked:** If `biweekly_mode` is omitted on a biweekly Loan input, what's the default?

**Options presented:**
1. Default to `'true'` (rate/26) — colloquial "should I do biweekly?" almost always means the accelerated kind (Recommended)
2. Default to `'half-monthly'` — conservative; same total interest, just timing changes
3. No default — require explicit field; loud, but adds friction

**User selected:** Default to 'true' (rate/26) (Recommended)

**Notes:** Document the default in `--help` text and `lib/amortize.py` module docstring. Decision recorded as D-02.

### Q6: Biweekly + extra-principal composition

**Question asked:** How does extra-principal compose with biweekly schedules?

**Options presented:**
1. Period-indexed: `period` field counts biweekly periods (1..~780 for 30yr biweekly); caller converts "$200/month" → "$100/biweekly" (Recommended)
2. Always month-indexed; engine spreads to biweekly periods internally — more user-friendly, adds a conversion layer
3. Disallow extra + biweekly in v1 — punt to v2

**User selected:** Period-indexed (Recommended)

**Notes:** One rule: `period` matches the schedule's emitted period numbers. Decision recorded as D-06.

### Q7: Date defaults when origination_date is None

**Question asked:** When `origination_date` is None on the input, what dates appear in the schedule?

**Options presented:**
1. Omit `payment_date` from output rows (loosen Phase 1 model) (Recommended)
2. Synthesize from today's run date (UTC) — every fixture gets a real-looking date; tests need time-freezing for determinism
3. Synthesize a fixed sentinel like 2000-01-01 — deterministic but fake-looking

**User selected:** Synthesize from today's run date

**Notes:** Tests that need date determinism MUST pass an explicit `origination_date` (or use freezegun-style fixture; planner picks). Synthesis happens in `lib/amortize.py` at schedule-generation time, NOT in the Pydantic model — `Loan.origination_date: date | None` stays per Phase 1 frozen surface. Decision recorded as D-12. (Note: chose option 2 instead of recommended option 1 — preserves visible dates in JSON output for human-reader narration.)

### Q8: Schedule output extras

**Question asked:** Should the Schedule output include cumulative-interest and cumulative-principal columns?

**Options presented:**
1. Yes — add `cumulative_interest` + `cumulative_principal` to each Payment row (Recommended)
2. No — keep Payment minimal; consumers compute totals themselves
3. Add a top-level summary block, not per-row

**User selected:** Yes — add to each Payment row (Recommended)

**Notes:** Phase 6 (refi NPV) and Phase 8 (stress) consume these to avoid recomputing. Backwards-compatible extension to Phase 1's `Payment` model (default values). Adds a model-level invariant: `Schedule.total_interest == payments[-1].cumulative_interest`. Decisions recorded as D-14 + D-15.

---

## Deferred / Out-of-Scope Ideas Surfaced

None — discussion stayed within Phase 3 scope. All "deferred" items in CONTEXT.md were inferred from the requirements + roadmap (e.g., ARM re-amortization → Phase 5, refi NPV → Phase 6) rather than user-suggested scope creep.

---

## Claude's Discretion Items

Areas where the user did not pin a specific decision; the planner/executor decides:

- numpy-financial wrapper internals: scalar per-period vs vectorized `npf.ipmt(rate, periods_array, n, principal)` — both correct, planner picks based on extra-principal mid-stream interaction
- Decimal/float boundary inside numpy-financial calls: if a specific path needs float, isolate with explicit `Decimal(str(...))` reconstruction at the boundary; document inline
- `ExtraPrincipalEntry` Pydantic model placement: `lib/amortize.py` (scoped) vs `lib/models.py` (frozen surface) — prefer scoped until a second consumer appears
- Test fixture filenames + structure under `tests/fixtures/amortize/` — JSON shape mirrors `golden_pmt.json` but planner names files
- Whether to add `freezegun` to dev deps for date-determinism in tests where fixtures don't already pass explicit `origination_date` — planner picks
- mypy --strict / ruff continue clean; no new lint rules

---

*Discussion log for: 03-core-amortization*
*Logged: 2026-04-29*
