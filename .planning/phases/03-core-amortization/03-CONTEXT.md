# Phase 3: Core Amortization - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `lib/amortize.py` wrapping `numpy-financial` PMT/IPMT/PPMT into a deterministic schedule generator and ship `scripts/amortize.py` as the JSON-in/JSON-out CLI surface that the future skill (Phase 10) will call. Engine handles fixed-rate, biweekly (both lender conventions), and arbitrary extra-principal scenarios with no float drift; final balance lands at exactly `Decimal("0.00")`.

**Delivered this phase:**
- `lib/amortize.py` — wrapper around `npf.pmt/ipmt/ppmt` (NEVER reimplement); produces a `Schedule`
- Schedule generator paths: fixed-rate monthly (AMRT-02), biweekly (AMRT-03; both modes), extra-principal composition (AMRT-04)
- Final-payment cleanup that brings balance to exactly `Decimal("0.00")` (AMRT-05)
- `scripts/amortize.py` — JSON-in / JSON-out CLI at project root (AMRT-06)
- Tests pinning `sum(principal_payments) == original_principal` (AMRT-07)
- Tests exercising all four golden fixtures (AMRT-08) with exact Decimal equality
- Minimal extension of Phase 1's `Payment` model: `cumulative_interest` + `cumulative_principal` (running totals)

**NOT delivered this phase** (deferred to consumer phases):
- Property tax / insurance / HOA / PMI / MIP layered on schedule (PITI) — Phase 4 affordability
- DTI / LTV / CLTV / reverse-affordability (`npf.pv`) — Phase 4
- ARM rate-reset re-amortization — Phase 5
- Refi NPV / breakeven / cash-out — Phase 6
- Estimated APR (Newton-Raphson Reg Z Appendix J) — Phase 7
- Rate-shock / income-shock / ARM-reset stress sweeps — Phase 8
- DuckDB persistence of computed schedules — Phase 9
- Skill physical relocation: `scripts/amortize.py` → `.claude/skills/mortgage-ops/scripts/amortize.py` — Phase 10
- `lib.rules.*` consumption — Phase 3 does NOT depend on Phase 2 predicates (locked by 02-CONTEXT.md)

</domain>

<decisions>
## Implementation Decisions

### Biweekly semantics

- **D-01: Ship BOTH biweekly modes via a schema field.** `Loan.biweekly_mode: Literal["true", "half-monthly"] | None`. Two distinct algorithms, two distinct golden-fixture sets. Reason: real lenders implement both — "true biweekly" (rate/26 per period, 26 payments/yr, accelerates payoff) and "half-monthly" (compute monthly P&I at rate/12, debit half every 14 days, books interest monthly, same total interest). Conflating them is a known calculator-tool mistake; we ship both and label.
- **D-02: Default `biweekly_mode = "true"` when `frequency: biweekly` is set without an explicit mode.** Rationale: the colloquial "should I do biweekly?" question almost always means the accelerated kind. Document this default in the script's `--help` text and in `lib/amortize.py` module docstring. When `frequency: monthly`, `biweekly_mode` MUST be None (validation error otherwise).
- **D-03: Date cadence.** Biweekly periods step via `relativedelta(weeks=2)` from origination. Monthly periods step via `relativedelta(months=1)`. First payment is one period after origination (industry standard). Reuse `python-dateutil` from PROJECT.md decision.
- **D-04: Rate-per-period conversion.** True biweekly: `period_rate = annual_rate / Decimal("26")`. Half-monthly: `period_rate = annual_rate / Decimal("12")` for the monthly P&I, then split the resulting payment in half for the biweekly cashflow (interest still booked monthly). Monthly: `annual_rate / Decimal("12")`. All conversions stay in Decimal — never go through float.

### Extra-principal input shape

- **D-05: Single list-of-entries schema.** Input shape: `extra_principal: list[ExtraPrincipalEntry]` where `ExtraPrincipalEntry` has `period: int (>=1)`, `amount: Money (>0)`, `recurring: bool = False`. One-shot, recurring monthly, and per-period scenarios collapse into one schema:
  - One-shot at period 60: `[{period: 60, amount: "5000", recurring: false}]`
  - Recurring $200 from period 1: `[{period: 1, amount: "200", recurring: true}]`
  - Step-up at period 13: `[{period: 1, amount: "200", recurring: true}, {period: 13, amount: "300", recurring: true}]` (later recurring entry replaces earlier from its period onward)
- **D-06: `period` is period-indexed in the schedule's natural cadence.** For monthly schedules, `period` = month number. For biweekly schedules, `period` = biweekly period number (1..~780 for 30yr biweekly true). Caller is responsible for converting "extra $200/month" → "extra $100/biweekly period" when running biweekly. Keep one rule: `period` matches the schedule's emitted period numbers, no internal conversion.
- **D-07: Extra-principal applies AFTER the regular-principal portion of the same period.** Order of operations: (1) compute regular `interest = period_rate * prior_balance`; (2) compute regular `principal = pmt - interest`; (3) apply `extra_principal_for_period`; (4) `new_balance = prior_balance - principal - extra_principal_for_period`. This ordering matches numpy-financial's pmt/ipmt convention and is what consumers expect.
- **D-08: Cap extra-principal at remaining balance.** If a recurring extra-principal entry would overpay the remaining balance, cap it at the remaining balance (and trigger the final-payment-adjusted flag). DO NOT raise — overpaying is a legitimate scenario (early payoff). The cap is silent at the row level but visible in the schedule's final-payment flag.

### Final-payment cleanup

- **D-09: Adjust ONLY the final period's principal.** Algorithm: compute schedule normally row-by-row; on the final period, set `principal = prior_balance` (clear remaining balance), then `payment = principal + interest` (interest still computed as `period_rate * prior_balance`), `balance = Decimal("0.00")`.
- **D-10: Surface a `final_payment_adjusted: bool` flag on the Schedule.** Top-level field on `Schedule` indicating whether the final period's principal was adjusted away from the formulaic value (cents-drift cleanup OR extra-principal-induced early payoff). Consumers (Phase 6 refi, Phase 8 stress) need this to detect "schedule terminated early" vs "schedule ran full term." Default False; set True when adjustment is non-zero.
- **D-11: Hard invariant test.** Every test must assert `sum(principal_payments) + sum(extra_principal_payments) == original_principal` exactly (no `assertAlmostEqual`). This is the AMRT-07 contract; the cleanup logic exists to make it true.

### Date handling

- **D-12: When `origination_date` is None, synthesize from today's run date (UTC).** Engine call: `origination_date = origination_date or datetime.now(UTC).date()`. Tests that need date determinism MUST pass an explicit `origination_date` in their fixtures (or use a `freezegun`-style fixture; planner picks). Synthesis happens in `lib/amortize.py` at schedule-generation time, NOT in the Pydantic model — `Loan.origination_date` stays `date | None` per Phase 1 frozen surface.
- **D-13: Month-end edge handling delegated to `relativedelta`.** Origination 2026-01-31 → first monthly payment 2026-02-28 (Feb has no 31st; relativedelta clips). PITFALLS.md flags this; we trust dateutil's behavior and pin a fixture exercising the edge to lock it in.

### Schedule output schema

- **D-14: Extend Phase 1's `Payment` model with `cumulative_interest: Money` and `cumulative_principal: Money`.** Each Payment row carries running totals from period 1 through itself. This is a backwards-compatible addition (default values; existing Phase 1 tests on `Payment` still pass). Phase 6 (refi NPV) and Phase 8 (stress) consume these to avoid recomputing totals from the payments list.
- **D-15: `Schedule.total_interest` (already in Phase 1 model) equals `payments[-1].cumulative_interest` by contract.** Add a Pydantic model-level validator (or test) that enforces this invariant. No silent disagreement between summary and per-row totals.
- **D-16: Schedule order = ascending by period.** No reverse, no skipping. Period numbering starts at 1 and is dense (every period from 1..N has a row, including the final adjusted period). This matches numpy-financial's per-period array convention.

### CLI surface

- **D-17: `scripts/amortize.py` lives at project root for Phase 3.** Path: `<repo>/scripts/amortize.py`. Phase 10 will physically relocate to `.claude/skills/mortgage-ops/scripts/amortize.py` (PROJECT.md decision #8 still binding for Phase 10). Phase 3 keeps things simple: no `.claude/` skeleton work this phase. Tests import via `python -m scripts.amortize` or subprocess invocation per Phase 1's test pattern.
- **D-18: CLI accepts `--input <path>` only (file-based JSON), per architecture pattern.** No stdin support in v1. Output is stdout JSON (pipe-friendly). `--help` works without importing heavy deps (lazy-load `lib.amortize` after argparse). Per AMRT-06 success criterion 5: running with no input prints a clear schema-error message via Pydantic surface.
- **D-19: CLI uses `Loan.model_validate_json` at the boundary.** Pydantic v2 strict-mode validation rejects float inputs to money fields. Errors surface as JSON-readable Pydantic validation messages (not raw tracebacks).

### Claude's Discretion

- **numpy-financial wrapper details:** Whether to call `npf.pmt(...)` once and iterate via `npf.ipmt`/`npf.ppmt` per period, or compute schedule via single vectorized call to `npf.ipmt(rate, periods_array, n, principal)` and `npf.ppmt(...)`. Both are correct; planner picks based on extra-principal interaction (single-call paths break when extra-principal mid-stream changes the remaining balance).
- **Decimal/float boundary:** numpy-financial accepts and returns Decimal in recent versions (per STACK.md). If a specific path hits a numpy-financial bug requiring float, isolate the float region with explicit `Decimal(str(...))` reconstruction at the boundary; document inline.
- **Pydantic model placement:** New `ExtraPrincipalEntry` Pydantic model — put in `lib/amortize.py` (scoped to this phase) OR `lib/models.py` (Phase 1 frozen surface). Prefer scoped-to-amortize.py until a second consumer needs it (mirrors Phase 2's "scope predicate-locals to predicate file" convention).
- **Test fixture format:** JSON files in `tests/fixtures/amortize/` keyed by scenario (`fixed_30yr_400k_6_5.json`, `biweekly_true_200k_6_5.json`, `biweekly_half_monthly_200k_6_5.json`, `extra_recurring_200_30yr.json`, `extra_oneshot_5k_period_60.json`, etc.). Each fixture has `loan` block + `expected_schedule_summary` block; fixture-level golden assertions on first/last row + invariants per AMRT-07.
- **Numpy-financial bug avoidance:** Always pass `fv=0` (default) — bug #130 (fv-sign flipped) does not affect us. Never use `npf.irr` — use `pyxirr` if/when needed (Phase 6).
- **Pre-commit / mypy:** Phase 3 does not modify pyproject.toml beyond adding `numpy-financial` (already in PROJECT.md stack). No new ruff rules; mypy --strict continues clean.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Inputs (project-level)

- `.planning/PROJECT.md` — project context, key decisions table (Decision #1: wrap numpy-financial; Decision #8: scripts INSIDE skill folder applies at Phase 10)
- `.planning/REQUIREMENTS.md` §"Amortization" — Phase 3 requirements AMRT-01..08 (definitive)
- `.planning/ROADMAP.md` §"Phase 3: Core Amortization" — phase goal + success criteria (5 must-haves)
- `.planning/STATE.md` — current project state (Phase 2 complete; ready to start Phase 3)
- `CLAUDE.md` — money discipline (Decimal from strings, ROUND_HALF_UP, never mix with float), calc-engine separation (Claude never owns numbers), Pydantic v2 condecimal at script boundaries
- `DATA_CONTRACT.md` — User/System/Data layer separation (scripts/ is System Layer)

### Phase 3 Research + Patterns

- `.planning/research/STACK.md` — numpy-financial verdict matrix (BSD-3, Decimal support, vectorizes; bugs #130 fv-sign, #131 irr arch-dependent — avoid)
- `.planning/research/FEATURES.md` — amortization in MVP (HIGH priority); biweekly via `relativedelta(weeks=2)`; extra-principal via `addl_principal` pattern (pbpython); ARM/refi/APR explicitly OUT of Phase 3
- `.planning/research/PITFALLS.md` — float drift over 360 periods; final-payment cleanup (`sum(principal_payments) == original_principal`); month-end edges (Jan 31 + relativedelta(months=1) → Feb 28/29); numpy-financial bug catalog
- `.planning/research/ARCHITECTURE.md` §"Pattern 1: Claude/Python Calc Split" — JSON-in/JSON-out script boundary; Pydantic validates on read
- `.planning/research/SUMMARY.md` — top-level research index

### Phase 1 Frozen Surface (Phase 3 USES; modifies only `Payment` minimally per D-14)

- `lib/models.py` — `Loan`, `Payment`, `Schedule`, `Money`, `Rate` types; `condecimal(max_digits=14, decimal_places=2)` discipline. Phase 3 ADDS `cumulative_interest` + `cumulative_principal` fields to `Payment` (default-valued, backwards-compatible).
- `lib/money.py` — `to_money(str)`, `quantize_cents(Decimal)`, `CENT`, `MONEY_CONTEXT` (ROUND_HALF_UP). Use these EVERYWHERE in `lib/amortize.py`.
- `tests/fixtures/golden_pmt.json` — 4 pinned oracles (Wikipedia $200k/6.5/30 → $1,264.14, CFPB LE $162k/3.875/30 → $761.78, computed $400k/6.5/30 → $2,528.27, computed $200k/7/15 → $1,797.66). AMRT-08 success criterion requires all four pass with exact Decimal equality.
- `tests/test_models.py`, `tests/test_money.py` — Phase 1 frozen test surface; Phase 3 must NOT regress.
- `tests/conftest.py` — pytest fixture pattern; new `tests/test_amortize.py` follows same structure.

### Phase 2 Frozen Surface (Phase 3 does NOT consume)

- `lib/rules/*.py` — explicitly NOT consumed by Phase 3 per `02-CONTEXT.md` line 162. Schedules don't need predicates. Phase 4 affordability is the first consumer.

### External Sources

- https://numpy.org/numpy-financial/latest/ — npf.pmt/ipmt/ppmt API docs
- https://github.com/numpy/numpy-financial/issues/130 — fv-sign bug (avoid `fv != 0` path)
- https://github.com/numpy/numpy-financial/issues/131 — irr arch-dependent (use pyxirr later)
- https://en.wikipedia.org/wiki/Mortgage_calculator — Wikipedia worked example (oracle fixture #1)
- https://files.consumerfinance.gov/f/201405_cfpb_loan-estimate-h-24-b.pdf — CFPB LE sample (oracle fixture #2)
- https://github.com/pbpython/code/blob/master/notebooks/Amortization-Complete.ipynb — Pat Walls' addl_principal pattern (extra-principal generator idiom)

### Pattern References

- `tests/test_money.py` (Phase 1) — Decimal-discipline test pattern (construct from string, exact equality, no `assertAlmostEqual`)
- `tests/test_fixtures.py` (Phase 1) — golden-fixture loader pattern (FND-09)
- `lib/rules/_loader.py` (Phase 2) — `lru_cache(maxsize=None)` fixture-load idiom (NOT directly applicable; reference only)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`lib/models.py`** (Phase 1): `Loan` (principal: Money, annual_rate: Rate, term_months: int, origination_date: date | None, loan_type: Literal[...]); `Payment` (period, payment_date, payment, principal, interest, extra_principal, balance — all Money); `Schedule` (loan, monthly_pi, total_interest, payments). Phase 3 EXTENDS `Payment` with two cumulative-total Money fields (D-14). `Loan` and `Schedule` shapes stay frozen.
- **`lib/money.py`** (Phase 1): `to_money(str) -> Decimal`, `quantize_cents(Decimal) -> Decimal` (ROUND_HALF_UP), `CENT`, `MONEY_CONTEXT`. Every Decimal cents-rounding in `lib/amortize.py` MUST go through `quantize_cents`.
- **`tests/fixtures/golden_pmt.json`** (Phase 1): 4 oracle fixtures already pinned with `expected_monthly_pi` strings. Phase 3 tests load these and assert exact equality against `Schedule.monthly_pi` per AMRT-08.
- **`tests/conftest.py`** (Phase 1): pytest fixture factory pattern. New `tests/conftest.py` extension or `tests/test_amortize/conftest.py` follows same structure (JSON-keyed inputs).
- **`pyproject.toml`** (Phase 1): mypy --strict, ruff, pytest configured. Phase 3 ADDS `numpy-financial>=1.0.0`. Already on PROJECT.md stack list — uv add at first plan.

### Established Patterns

- **Decimal-from-strings:** `Decimal("0.065")` not `Decimal(0.065)`. YAML/JSON scalars stored as quoted strings. Pydantic v2 strict-mode rejects float at validation.
- **Pydantic v2 strict + frozen + extra=forbid:** `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` for all domain models. Already established in `lib/models.py`.
- **Hand-calculated golden fixtures with citation comments:** `tests/fixtures/golden_pmt.json` has `source` URL + `notes` per fixture. Phase 3's biweekly + extra-principal fixtures follow same shape.
- **Exact Decimal equality, never `assertAlmostEqual` for money:** Established Phase 1 + reinforced by CLAUDE.md.
- **Quantize end-of-period only:** Never quantize mid-calculation; one `quantize_cents()` call per period at the end. PITFALLS.md flags this.
- **Pre-commit hooks:** Phase 1 ruff + mypy + user-layer block in place. Phase 3 doesn't touch these.

### Integration Points

- **`pyproject.toml`** — add `numpy-financial>=1.0.0` (uv add at first Phase 3 plan). Already on PROJECT.md stack list.
- **`lib/amortize.py`** — new file. Imports: `npf` (numpy-financial), `dateutil.relativedelta`, `lib.models` (Loan/Payment/Schedule), `lib.money` (quantize_cents, CENT).
- **`lib/models.py`** — minimal extension to `Payment`: `cumulative_interest: Money = Decimal("0.00")`, `cumulative_principal: Money = Decimal("0.00")`. Backwards-compatible defaults. Test surface (`tests/test_models.py`) gets two assertions added; existing tests unchanged.
- **`scripts/amortize.py`** — new file at project root. Argparse + `Loan.model_validate_json` + call into `lib.amortize.build_schedule(loan)` + `print(schedule.model_dump_json(indent=2))`. Lazy-import `lib.amortize` after argparse so `--help` is fast.
- **`tests/test_amortize.py`** — new file. Cases: 4 golden fixtures (AMRT-08), biweekly true mode + half-monthly mode separately (AMRT-03), extra-principal one-shot + recurring + per-period (AMRT-04), final-cleanup invariants (AMRT-05/07), CLI smoke (AMRT-06).
- **`tests/fixtures/amortize/`** — new directory. JSON fixtures per scenario; reuse `golden_pmt.json` shape for fixed-rate cases.

### Phase 4+ downstream consumers (DO NOT BREAK in Phase 3)

- **Phase 4 (Affordability):** consumes `Schedule.monthly_pi` (the P&I number) and reverse-direction `npf.pv` from a max PMT. Does NOT consume `Schedule.payments` — it only needs the headline P&I. Stable contract: `Schedule.monthly_pi: Money` (already in Phase 1).
- **Phase 5 (ARM):** Phase 5 will RE-ENTER `lib.amortize.build_schedule` at each ARM reset with new rate + remaining balance + remaining term. Phase 3's wrapper must accept `principal`, `annual_rate`, `term_months` directly (or via Loan); Phase 5 won't construct an ARMTerms-flavored Loan, it'll loop calling Phase 3.
- **Phase 6 (Refi NPV):** consumes `Schedule.payments[i].cumulative_interest` per D-14 (avoid recomputing totals from the payments list). Stable contract: D-14 + D-15 (cumulative_interest matches Schedule.total_interest at last row).
- **Phase 8 (Stress):** rate-shock sweep re-solves PMT for a grid of rates; calls `lib.amortize.build_schedule` repeatedly. Vectorization is OPTIONAL in Phase 8 (not required by Phase 3's wrapper).
- **Phase 10 (Skill):** moves `scripts/amortize.py` → `.claude/skills/mortgage-ops/scripts/amortize.py`. Phase 3 should NOT lock the path in any test that imports `scripts.amortize` — prefer subprocess invocation with a `SCRIPT_PATH` constant in the test module.

</code_context>

<specifics>
## Specific Ideas

- **Biweekly = both modes:** "true biweekly" + "half-monthly" both ship with their own golden fixtures. The default (when `frequency: biweekly` is set without `biweekly_mode`) is `"true"` because the colloquial "should I do biweekly?" question almost always means accelerated payoff.
- **Extra-principal as one schema:** the `list[ExtraPrincipalEntry]` shape collapses one-shot, recurring, and per-period inputs into one validator. Each entry: `{period, amount, recurring}`. Recurring entries take effect from `period` onward until a later recurring entry overrides; one-shot entries fire only on the named period.
- **`final_payment_adjusted: bool` on Schedule:** consumers downstream (Phase 6 refi sees early-payoff scenarios; Phase 8 stress detects shortened schedules from rate shock + extra-principal) need to know whether the final period's principal was massaged from the formulaic value. Default False; set True when adjustment is non-zero.
- **Cumulative totals on every Payment row:** future phases (refi NPV, stress) consume `cumulative_interest` and `cumulative_principal` directly; without these, Phase 6/8 either recompute (waste) or risk drift. Adds two `Money` fields to `Payment` with default `Decimal("0.00")`.
- **`origination_date` defaulting:** when None, synthesize from today's UTC date inside `lib/amortize.py` at schedule-generation time. Tests that need date determinism MUST pass an explicit `origination_date` (or use `freezegun`-style time freezing — planner picks). Phase 1's `Loan.origination_date: date | None` stays as-is.
- **Period-indexed extras for biweekly:** when running biweekly, extra-principal `period` field counts biweekly periods (1..~780 for 30yr biweekly true). Caller converts "$200/month" → "$100/biweekly period" themselves. One rule: `period` matches the schedule's emitted period numbers.
- **Bug avoidance:** never use `npf.pmt` with `fv != 0` (bug #130 fv-sign flipped). Never use `npf.irr` (bug #131 arch-dependent). Both are out of Phase 3 scope but worth a comment in `lib/amortize.py` module docstring.
- **Wikipedia + CFPB LE oracles:** AMRT-08 success criterion 1 reads `monthly_pi == "2528.27"` for the $400k/6.5/30 fixture. All four oracles in `tests/fixtures/golden_pmt.json` are exact strings, not floats. Test asserts use `==`, not `assertAlmostEqual`.

</specifics>

<deferred>
## Deferred Ideas

- **Vectorized schedule generation (numpy-financial vector path):** scalar per-period iteration is sufficient for Phase 3. Phase 8 stress tests may want vectorization across a parameter grid — defer to Phase 8 if profiling shows scalar paths are too slow (unlikely for personal-use tool).
- **`pyxirr` integration:** out of Phase 3 (no NPV/IRR work). Phase 6 refi NPV is the first consumer.
- **DuckDB persistence of computed schedules:** Phase 9.
- **Skill physical relocation of `scripts/amortize.py`:** Phase 10 (PROJECT.md decision #8 binds at Phase 10, not Phase 3).
- **`freezegun` test dependency:** add only if the planner finds we need date-determinism in fixtures that don't already pass an explicit `origination_date`. Most fixtures should just pass an explicit date.
- **Stdin-based CLI input:** v2 if needed. v1 is `--input <path>` only per D-18.
- **Schema migrations for `Payment` cumulative fields if persisted to DuckDB:** Phase 9 problem; Phase 3 only emits in-memory + JSON.
- **Validation of "extra-principal would overpay" as a structured warning:** v1 silently caps at remaining balance and surfaces via `final_payment_adjusted`. v2 could add a `notes: list[str]` field to Schedule for soft warnings.
- **ARM re-amortization mid-schedule (rate reset triggers recomputation of remaining periods):** Phase 5. Phase 3's wrapper should be callable with arbitrary `principal/annual_rate/term_months` so Phase 5 can loop into it at each reset boundary.

</deferred>

---

*Phase: 03-core-amortization*
*Context gathered: 2026-04-29*
