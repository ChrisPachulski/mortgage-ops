# Phase 5: ARM Modeling - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `lib/arm.py` — the ARM (adjustable-rate mortgage) modeling layer composing on top of Phase 3's `lib.amortize.build_schedule`. Ships:

- `lib/arm.py` — `ARMTerms` Pydantic v2 model with the eight explicit ARM-01 fields plus a `note_rate` discretion field (D-02); `ARMPayment` (subclasses Phase 1 `Payment`, adds `rate_in_effect: Rate`); `ARMSchedule` (parallel to Phase 1 `Schedule`, holds `list[ARMPayment]` + `reset_events: list[ResetEvent]`); `ResetEvent` (per-reset metadata: period, old/new rate, old/new pmt, index value used, applied cap kind); `build_arm_schedule(...)` engine
- `scripts/arm_simulate.py` — JSON-in / JSON-out CLI at project root mirroring `scripts/affordability.py` (Phase 4 D-13/14) and `scripts/amortize.py` (Phase 3 D-17/D-18/D-19); Phase 10 relocates into `.claude/skills/mortgage-ops/scripts/`
- `references/arm-mechanics.md` — documents reset convention (rate change at start of month 61 for 5/1), cap precedence (initial_cap at first reset; periodic_cap subsequently), floor algebra (max(margin, floor_rate)), and lifetime-cap reference (note_rate + lifetime_cap_bps), each citing Freddie/Fannie Selling Guides; cited from `ARMTerms` model docstring per ARM-09
- Five products supported via the structured fields: 5/1 (initial=60, reset=12), 7/1 (84, 12), 10/1 (120, 12), 5/6 (60, 6) — and any other `(initial_period_months, reset_period_months)` combo per ARM-01 (no implicit conventions)
- Tests covering all 9 ARM requirements with hand-calculated golden fixtures cross-validated against MGIC ARM calculator captures (D-04); both reset-month conventions (60 and 61) explicitly exercised per ROADMAP SC-3

**Delivered this phase:**
- `lib/arm.py` (ARMTerms + ARMPayment + ARMSchedule + ResetEvent + ARMRequest + `build_arm_schedule`) — ARM-01..05
- `scripts/arm_simulate.py` JSON-in/JSON-out CLI — ARM-08
- `tests/test_arm.py` + `tests/fixtures/arm/` (hand-calc fixtures + MGIC oracle captures) — ARM-06, ARM-07
- `references/arm-mechanics.md` with Freddie/Fannie Selling Guide citations — ARM-09
- `tests/conftest.py` extension: `arm_fixture` loader mirroring Phase 3's `amortize_fixture` and Phase 4's `affordability_fixture`

**NOT delivered this phase** (deferred to consumer phases or v2):
- ARM-aware affordability re-evaluation (DTI at each reset) — Phase 8 stress (consumes ARMSchedule + Phase 4 `lib.affordability`)
- Refi NPV against ARM payoff trajectories — Phase 6 (decoupled; refi sees a balance + new loan, not the prior ARM schedule)
- Estimated APR for ARMs (Reg Z Appendix J unit-period equation handles ARMs as a sequence of unit-periods) — Phase 7
- Stress-test rate-shock + index-path parameter sweeps — Phase 8 (re-invokes `build_arm_schedule` per grid cell)
- DuckDB persistence of ARMSchedule — Phase 9
- FRED MCP live `MORTGAGE30US` / `SOFR1Y` index injection — Phase 12 (Phase 5 takes caller-supplied index values only — D-13)
- Skill physical relocation: `scripts/arm_simulate.py` → `.claude/skills/mortgage-ops/scripts/arm_simulate.py` — Phase 10
- `.claude/skills/mortgage-ops/references/arm-mechanics.md` mirror — Phase 10 (Phase 5 ships at repo root `references/arm-mechanics.md`)
- Option ARM / payment-cap / negative-amortization products — explicitly OUT of v1 (D-12); conventional ARMs always re-amortize to fully-amortizing payment at reset
- Index lookback windows (e.g., "use index value 45 days before reset") — out of v1 (D-13)
- `.claude/skills/mortgage-ops/modes/arm.md` mode file — Phase 10
- `.claude/agents/amortization-agent.md` ARM routing — Phase 11

</domain>

<decisions>
## Implementation Decisions

### Index supply model (ARM-01, ARM-02, ARM-03)

- **D-01: Flat `assumed_index_rate` (REQUIRED) + optional per-reset `index_path` overrides.** The runtime request shape:

  ```
  {
    "loan": { ...Phase 1 Loan with annual_rate = INITIAL note rate during fixed period },
    "arm_terms": { ...ARMTerms per D-06 },
    "assumed_index_rate": "0.0500",           // Decimal string, REQUIRED
    "index_path": [                           // OPTIONAL, [] default
      {"period": 61, "value": "0.0525"},
      {"period": 73, "value": "0.0550"}
    ]
  }
  ```

  At each reset trigger period (61, 73, 85, ... for 5/1; 61, 67, 73, ... for 5/6), the engine looks up that exact period in `index_path` first; on miss, falls back to `assumed_index_rate`. Override-wins semantics. `index_path` periods that don't align to any reset trigger raise a Pydantic validation error at the request boundary (fail loud — surface via Phase 3 D-19 / WR-02 6-key envelope).

  Reason: this single shape answers two consumer questions directly:
  - "What's my payment if rates sit flat at 5%?" → set only `assumed_index_rate: "0.05"`; leave `index_path: []`
  - "What does Phase 8 stress look like under a parallel-shift / gradual-rise / fall-then-rise path?" → fill `index_path` per reset period; `assumed_index_rate` stays as the fallback floor (and as the "first-reset assumption" if `index_path` doesn't cover period 61)

  Phase 12 FRED MCP integration (deferred) will populate `assumed_index_rate` from `MORTGAGE30US` latest weekly value at SKILL.md narration time; Phase 5's CLI takes the value as-is.

### Reset-time rate update formula (ARM-03, ARM-04)

- **D-02: Industry-standard clamp with REQUIRED `floor_rate`, optional `note_rate`, and first-reset `initial_cap` precedence.** Locked formula at every reset trigger period:

  ```
  index = index_path[period] if period in index_path else assumed_index_rate
  fully_indexed = quantize_rate(index + (margin_bps / 10000))
  effective_floor = max(margin_bps / 10000, floor_rate)
  is_first_reset = (epoch_index == 1)  # epoch 0 is the initial fixed period
  applicable_cap_bps = initial_cap_bps if is_first_reset else periodic_cap_bps
  periodic_ceiling = prior_rate + (applicable_cap_bps / 10000)
  lifetime_ceiling = note_rate + (lifetime_cap_bps / 10000)
  ceiling = min(periodic_ceiling, lifetime_ceiling)
  new_rate = quantize_rate(clamp(fully_indexed, low=effective_floor, high=ceiling))
  ```

  Field-level constraints baked into the Pydantic `ARMTerms` model:
  - `floor_rate: Rate` is **REQUIRED** (no `None`, no default). No implicit margin fallback. Forces every caller to make an explicit choice. Matches mortgage-ops "fail loud, no inference" discipline.
  - `note_rate: Rate | None = None`. When `None`, engine treats `note_rate = loan.annual_rate` (the initial fixed-period rate). When provided (teaser-rate ARMs where `note_rate ≠ loan.annual_rate`), engine uses the provided value for the lifetime ceiling computation.
  - `initial_cap_bps`, `periodic_cap_bps`, `lifetime_cap_bps`: `int >= 0`, basis points (e.g., 200 = 2.00 percentage points). Rate conversion: `Decimal(cap_bps) / Decimal("10000")` at use time, NEVER pre-converted in the model.
  - `margin_bps`: `int >= 0`, basis points.
  - Quantization: every rate output flows through `quantize_rate(...)` at 6 decimal places (matches Phase 4 D-09 `_quantize_rate`). If Phase 5 is the second consumer of this helper, **promote it to `lib/money.py`** as a public `quantize_rate(Decimal) -> Decimal` helper following Phase 2 D-08 / Phase 3 discretion convention. Otherwise keep importing from `lib.affordability` — planner picks at first plan.

  Reason: this is the union of (a) industry standard (initial_cap distinct from periodic_cap; lifetime_cap measured against initial note rate; floor = max(margin, floor_rate)) and (b) project's "fail loud" discipline (REQUIRED floor; no implicit margin fallback). The optional `note_rate` field supports teaser-rate ARMs (initial < note) without forcing every caller to set it — common case `note_rate=None` collapses to `loan.annual_rate`.

  ResetEvent's `applied_cap: Literal["initial", "periodic", "lifetime", "floor", "none"]` records WHICH constraint bound the new rate. Test fixtures assert the `applied_cap` value to lock the cap-precedence implementation exactly.

### ARM Schedule output shape (ARM-05)

- **D-03: Parallel `ARMSchedule` + `ARMPayment` models in `lib/arm.py`; Phase 1 Payment / Schedule UNCHANGED. Continuous period numbering 1..N across epochs.** Concretely:

  ```python
  # lib/arm.py
  class ARMPayment(Payment):  # Pydantic v2 model inheritance
      """Payment row in an ARM schedule. Adds rate_in_effect to Phase 1 Payment."""
      model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
      rate_in_effect: Rate  # the period's annualized rate; populated per-row by build_arm_schedule

  class ResetEvent(BaseModel):
      model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
      period: int                                                          # absolute period (61, 73, ...)
      old_rate: Rate
      new_rate: Rate
      old_pmt: Money                                                       # P&I before reset
      new_pmt: Money                                                       # P&I after reset
      index_value_used: Rate                                               # the index value (override or flat)
      applied_cap: Literal["initial", "periodic", "lifetime", "floor", "none"]

  class ARMSchedule(BaseModel):
      """ARM-aware schedule. Parallel to Phase 1 Schedule; NOT a subclass."""
      model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
      loan: Loan
      arm_terms: ARMTerms
      payments: list[ARMPayment]                                           # continuous 1..N
      reset_events: list[ResetEvent]
      total_interest: Money
      final_payment_adjusted: bool = False                                 # only LAST epoch sets this; intermediate epochs always False
  ```

  Period numbering rule: `payments[0].period == 1` (first month after origination), `payments[-1].period == loan.term_months` (last month of full original term). For a 5/1 ARM 30-year, `payments[59].period == 60` (last month of fixed period; old payment), `payments[60].period == 61` (first month after first reset; new payment). `reset_events[0].period == 61`.

  `final_payment_adjusted` semantics across epochs: only the FINAL epoch (the one that contains `term_months`) inherits Phase 3 D-09 / D-10 cleanup (sets `final_payment_adjusted = True` if cents-drift). Intermediate epochs do NOT trigger D-09 cleanup — their final period is just one before the next reset boundary, the balance carries forward, never reaches zero. Engine implementation strategy: per epoch, call `build_schedule(synthetic_loan, ...)` with `term_months = remaining_full_term`, then SLICE off only the periods up to the next reset boundary (or to the end for the final epoch). Slicing preserves Phase 3 invariants — interest accrual, principal application, cumulative-totals math — for the rows we actually emit.

  Reason: parallel models (chosen over Phase 1 D-14-style extension) keeps Phase 1 frozen surface untouched. Phase 4 affordability + Phase 8 stress consumers that need a Phase 1 `Schedule` view read `ARMSchedule.payments` directly — `ARMPayment` IS-A `Payment` via Pydantic v2 inheritance, so `list[ARMPayment]` is structurally compatible with `list[Payment]` (covariant in practice; mypy --strict happy via the subclass relationship). For consumers that want a fully-typed Phase 1 `Schedule`, an adapter helper `ARMSchedule.as_phase1_schedule() -> Schedule` may ship if a downstream consumer needs it (Claude's discretion at planning time).

### Re-amortization at each reset (ARM-05)

- **D-05: Per-epoch re-entry into `lib.amortize.build_schedule` with synthetic Loan + slice.** Algorithm:

  1. Epoch 0 (months 1..initial_period_months): one `build_schedule` call with the original `Loan(principal, annual_rate, term_months)`. Slice off `payments[0:initial_period_months]`. Carry `remaining_balance = payments[initial_period_months - 1].balance`.
  2. For each subsequent reset epoch N (months reset_N..reset_{N+1} - 1):
     - Compute `new_rate` per D-02 reset formula.
     - Synthesize `Loan(principal=remaining_balance, annual_rate=new_rate, term_months=remaining_full_term)` where `remaining_full_term = original_term_months - first_period_of_epoch + 1`. (Re-amortizes over the FULL remaining term per ARM-05.)
     - Call `build_schedule(synthetic_loan, frequency='monthly', ...)`. The Phase 3 engine produces a `Schedule` for the full remaining term.
     - Slice off only the rows from `synthetic_schedule.payments[0:reset_period_months]` (or, for the FINAL epoch, all remaining rows).
     - Adjust each sliced `Payment.period` and `Payment.payment_date` to absolute (continuous 1..N numbering); convert each to `ARMPayment` with `rate_in_effect = new_rate`. Adjust cumulative totals (`cumulative_interest` and `cumulative_principal`) by adding the prior epoch's terminal totals (so the continuous schedule's cumulative fields tell the truth across epochs).
     - Carry `remaining_balance = sliced_payments[-1].balance` to the next epoch.
  3. After the FINAL epoch, set `ARMSchedule.final_payment_adjusted = synthetic_final_schedule.final_payment_adjusted` (only the final epoch's Phase 3 D-10 detection bubbles up). Set `ARMSchedule.total_interest = sliced_payments[-1].cumulative_interest` (preserves Phase 1 D-15 invariant).
  4. Record one `ResetEvent` per reset boundary (period at start of each epoch ≥ 1).

  Reason: re-using `lib.amortize.build_schedule` per epoch (rather than reimplementing per-period iteration in `lib/arm.py`) preserves every Phase 3 invariant — D-04 rate-per-period, D-07 composition order, D-09 final cleanup at the LAST epoch, D-14 cumulative totals — without copying logic. Slicing-then-stitching is the explicit cost; the planner may choose to compute `synthetic_loan.term_months = reset_period_months` for non-final epochs (saves the slice but loses the "full remaining term re-amortization" semantics) — DO NOT take that shortcut. ARM-05 specifies "remaining balance recasts over remaining term at new rate", which means full remaining term, not just the next reset window.

  Date cadence: synthetic_loan.origination_date = original_loan.origination_date + relativedelta(months=first_period_of_epoch - 1). Or skip per-epoch origination dates and let `build_schedule` synthesize per Phase 3 D-12, then overwrite payment_date in the slice (planner picks; both are correct).

### ARMTerms Pydantic model fields (ARM-01)

- **D-06: ARMTerms field schema (final lock).** Locked field set:

  ```python
  class ARMTerms(BaseModel):
      model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

      initial_period_months: int = Field(ge=1, le=600)        # 60 (5/1), 84 (7/1), 120 (10/1), 60 (5/6)
      reset_period_months: int = Field(ge=1, le=600)          # 12 (5/1), 12 (7/1), 12 (10/1), 6 (5/6)
      initial_cap_bps: int = Field(ge=0, le=2000)             # first-reset cap; common: 500 (5pp)
      periodic_cap_bps: int = Field(ge=0, le=2000)            # subsequent-reset cap; common: 200 (2pp)
      lifetime_cap_bps: int = Field(ge=0, le=2000)            # vs note_rate; common: 500 (5pp)
      floor_rate: Rate                                        # REQUIRED per D-02 (no None, no default)
      margin_bps: int = Field(ge=0, le=2000)                  # spread over index; common: 250 (2.5pp)
      index_series_id: str = Field(min_length=1, max_length=64)  # metadata only; e.g., "MORTGAGE30US", "SOFR1Y"
      note_rate: Rate | None = None                           # defaults to loan.annual_rate per D-02 when None

      @model_validator(mode="after")
      def _initial_period_aligns_with_reset(self) -> ARMTerms:
          # Optional cross-field check; planner finalizes shape.
          # Reasonable invariant: reset_period_months <= initial_period_months for all common products.
          # Not strictly required by ARM-01; planner can skip if it surfaces no real bugs.
          ...
  ```

  Notes:
  - The `2000` upper bound on `*_cap_bps` (20pp) is a sanity rail, not regulatory — caps higher than 20pp are not realistic for retail ARMs. Planner may tighten or loosen.
  - `index_series_id` is a free-form string in v1; Phase 12 may add a Literal-or-enum constraint when FRED MCP integrates.
  - `note_rate` semantic: when `loan.annual_rate == 0.0500` (initial fixed) and `note_rate=None`, the engine treats `note_rate = 0.0500` for lifetime-cap math. When `loan.annual_rate == 0.0300` (teaser) and `note_rate = 0.0500` (post-teaser note rate), lifetime ceiling = `0.0500 + lifetime_cap_bps/10000`.

### CLI surface (ARM-08)

- **D-07: `scripts/arm_simulate.py` mirrors Phase 3/4 conventions exactly.** Locked behavior:
  - Lives at project root (Phase 5); Phase 10 relocates to `.claude/skills/mortgage-ops/scripts/arm_simulate.py` (PROJECT.md decision #8 binds at Phase 10, NOT Phase 5)
  - Uses `--input <path>` only (no stdin support in v1; Phase 3 D-18 / Phase 4 D-13 inherited)
  - Lazy-imports `lib.arm` (and transitively `lib.amortize`, `numpy_financial`) AFTER argparse — `--help` is fast (Phase 3 D-18 / Phase 4 D-13 inherited)
  - Validates request via `ARMRequest.model_validate_json(...)` at the boundary; emits Phase 3 D-19 / WR-02 6-key Pydantic envelope on stderr for validation errors (`type / loc / msg / input / url / ctx`); pretty-prints the resulting `ARMSchedule.model_dump_json(indent=2)` to stdout
  - JSON-float pre-validation gate (Phase 3 WR-02 closure) extends to ARM money fields: any JSON-float in `loan.principal`, `assumed_index_rate`, `index_path[].value`, or `floor_rate` is rejected at the boundary BEFORE Pydantic sees it, with the same 6-key envelope shape on stderr. The planner inherits the existing `_find_json_float_loc` helper from `scripts/affordability.py` (or factors it out into a shared `scripts/_cli_helpers.py` module — Claude's discretion)
  - Subprocess-invocation pattern in tests, NOT direct import (Phase 3 D-17 portability — Phase 10 may relocate the script and tests must keep working)

  Reason: zero-creativity CLI shape. Every prior calc-script in the project follows the same six conventions (root path, --input, lazy-import, Pydantic envelope, float-gate, subprocess-invocation in tests); Phase 5 inherits all of them.

### `references/arm-mechanics.md` (ARM-09)

- **D-08 [REVISED 2026-04-30]: Lock the convention with explicit Selling Guide citations.** `references/arm-mechanics.md` MUST include:
  1. **Reset month convention** (locked: rate change applies at START of month 61 for 5/1; month 85 for 7/1; month 121 for 10/1; month 61 for 5/6 with second reset at month 67) — cite **Fannie Mae Selling Guide §B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)"** (https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms, last updated 2025-12-10) + **Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b)** + the **Freddie SOFR-Indexed ARMs product page** (https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms) for cross-reference
  2. **Cap precedence** (initial_cap at first reset; periodic_cap at every subsequent reset; lifetime_cap measured against note_rate) — cite Fannie B2-1.4-02 + Freddie 6302.7(b)
  3. **Floor algebra** (effective_floor = max(margin, floor_rate); floor_rate is REQUIRED in this engine — no implicit margin fallback) — cite Fannie B2-1.4-02 + Freddie 6302.7(b)
  4. **Quantization** (rate quantize at 6 decimal places per Phase 4 D-09 `_quantize_rate`)
  5. **Negative amortization OUT of scope** (Phase 5 supports only fully-amortizing ARMs; Option ARM / payment-cap products deferred to v2)
  6. **`index_series_id` semantics** (metadata only in Phase 5; Phase 12 maps to FRED MCP series IDs)
  7. **Teaser-ARM lifetime cap base — engine choice, not regulator-mandated.** D-02 measures the lifetime ceiling against `arm_terms.note_rate` (with `note_rate=None` collapsing to `loan.annual_rate`). CFPB §1951 (https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/) describes the lifetime cap as measured "from the initial rate" — for teaser-rate ARMs (where `loan.annual_rate < note_rate`), this engine deliberately uses `note_rate` as the lifetime base because that matches industry practice for teaser products. Document this as an explicit engine choice, not silent.

  > **REVISION NOTE (2026-04-30, plan-phase research finding):** Original D-08 cited "Fannie Mae §B5-3.5-01" — that section returns 404. Verified correct location is §B2-1.4-02 (last updated 2025-12-10). Original cited "Freddie §4404" — that section is stale; modern equivalent is §6302.7(b) plus the SOFR-Indexed ARMs product page. Item 7 (CFPB-vs-engine teaser-ARM choice) added as researcher landmine LM-3 — disclosed as engine choice rather than left silent.

  The file lives at `<repo>/references/arm-mechanics.md` for Phase 5 (parallel to `<repo>/data/reference/*.yml`). Phase 10 either copies or symlinks it into `.claude/skills/mortgage-ops/references/arm-mechanics.md` (Phase 10 picks).

  Cited from `ARMTerms` model docstring as an inline reference: `"""See references/arm-mechanics.md for reset/cap/floor convention. ..."""` — satisfies ROADMAP SC-5.

### Test oracle strategy (ARM-06, ARM-07)

- **D-04 [REVISED 2026-04-30]: Bankrate + Vertex42 + AmericU capture-as-fixture + hand-calc per Selling Guide CROSS-VALIDATION.** Required fixture set in `tests/fixtures/arm/`:

  > **REVISION NOTE (2026-04-30, plan-phase research finding):** Original D-04 cited MGIC's ARM calculator as the capture-as-fixture oracle. Direct verification (https://www.mgic.com/tools/consumer-calculators) confirmed MGIC publishes only 5 consumer calculators — none for ARMs. D-04 is REPLACED with a three-source oracle (one ground-truth source per product family) — see "Capture-as-oracle" subsection below.

  Hand-calculated (computed by Decimal arithmetic per Selling Guide formula, with citation comments):
  - `arm_5_1_payment_jump_at_61.json` — primary 5/1 ARM, asserts `payments[59].rate_in_effect == initial_rate`, `payments[59].payment == initial_pmt`, `payments[60].rate_in_effect == new_rate`, `payments[60].payment == new_pmt`. PRIMARY ROADMAP SC-2 fixture.
  - `arm_5_1_off_by_one_negative.json` — same 5/1 ARM, but asserts `payments[58].payment == initial_pmt` (month 59 still old rate) AND `payments[60].payment != initial_pmt` (month 61 already new rate). Catches both off-by-one directions. ROADMAP SC-3.
  - `arm_7_1_payment_jump_at_85.json` — 7/1 ARM (initial=84, reset=12).
  - `arm_10_1_payment_jump_at_121.json` — 10/1 ARM (initial=120, reset=12).
  - `arm_5_6_payment_jump_at_61_and_67.json` — 5/6 ARM (initial=60, reset=6); asserts BOTH the first reset (month 61) and the second reset (month 67).
  - `arm_floor_below_margin_blocked.json` — index drops to 0%, assert `new_rate >= max(margin, floor_rate)`. ARM-04 fixture.
  - `arm_lifetime_cap_binds.json` — uncapped fully-indexed > note_rate + lifetime_cap_bps/10000; assert ceiling = note_rate + lifetime_cap_bps/10000; assert `reset_event.applied_cap == "lifetime"`.
  - `arm_initial_cap_at_first_reset.json` — first reset would jump > initial_cap; assert ceiling = prior_rate + initial_cap_bps/10000; assert `applied_cap == "initial"`. Subsequent reset (same fixture, second reset boundary) also tests periodic_cap binding.
  - `arm_teaser_rate.json` — `loan.annual_rate = 0.0300` (teaser), `arm_terms.note_rate = 0.0500`, lifetime ceiling = 0.0500 + lifetime_cap_bps/10000; verifies `note_rate` is decoupled from `loan.annual_rate`.
  - `arm_continuous_period_numbering.json` — asserts `payments[i].period == i + 1` for all i; asserts `payments[-1].period == loan.term_months`; asserts `payments[-1].balance == Decimal("0.00")` (final epoch terminates correctly per Phase 3 D-09).
  - `arm_index_path_overrides.json` — supplies `index_path` with two overrides + `assumed_index_rate` fallback; verifies override-wins at exact reset trigger periods.

  Capture-as-oracle (three-source ground-truth, one per product family — replaces MGIC after 2026-04-30 verification):

  **Primary oracle — Bankrate ARM Calculator** (https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/) — supports 3/1, 5/1, 7/1, 10/1. Produces per-period payment table. Used for 5/1, 7/1, 10/1 cross-validation.
  - `tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.pdf` — browser-print PDF of the Bankrate output for one 5/1 ARM scenario (committed artifact).
  - `tests/fixtures/arm/oracle/bankrate_5_1_capture_2026.json` — JSON transcription (inputs + expected per-period rate/payment rows).
  - `tests/fixtures/arm/oracle/bankrate_7_1_capture_2026.pdf` + `.json` — same shape, 7/1 ARM.
  - `tests/fixtures/arm/oracle/bankrate_10_1_capture_2026.pdf` + `.json` — same shape, 10/1 ARM.

  **Secondary oracle — Vertex42 Excel ARM Calculator** (https://www.vertex42.com/ExcelTemplates/arm-calculator.html) — transparent Excel formulas. Used as the deterministic "open-source-formula" cross-check against Bankrate's closed tool.
  - `tests/fixtures/arm/oracle/vertex42_5_1_capture_2026.pdf` — print-to-PDF of the populated Excel sheet for the same 5/1 scenario as the Bankrate capture (committed artifact).
  - `tests/fixtures/arm/oracle/vertex42_5_1_capture_2026.json` — JSON transcription.
  - At least ONE other product (7/1 or 10/1) cross-captured via Vertex42 — planner picks.

  **5/6 oracle — AmericU 5/6 SOFR ARM Disclosure** (https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf) — lender-published worked example with 2/1/5 caps. Bankrate does not support 5/6; this is the only credible 5/6 ground-truth source.
  - `tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf` — committed PDF of the disclosure (already public lender artifact; no expiration).
  - `tests/fixtures/arm/oracle/americu_5_6_disclosure.json` — JSON transcription of the disclosure's worked example (inputs + expected reset rates + expected payments at month 61, 67, 73).

  Test asserts: hand-calc per Selling Guide formula AND tool output AGREE EXACTLY (Decimal equality on `rate_in_effect` and `payment` for each transcribed row). Disagreement = bug in either our engine or our reading of the tool — surfaces as a test failure with both sides logged.

  **Annual re-capture cadence:** Bankrate + Vertex42 captures re-validated annually (parallel to FFIEC for Phase 7 APR). AmericU PDF is a frozen 2022 lender disclosure — no re-capture cycle, but re-validate annually that the URL still resolves; if the disclosure is withdrawn, fall back to a different lender's 5/6 SOFR disclosure (planner Phase 8+ concern).

  Reason: hand-calc gives us mathematical correctness against the regulatory citation; the three captured oracles give us "industry-tool-output matches engine" attestation across all four product families (5/1, 7/1, 10/1, 5/6). Bankrate covers the most common products; Vertex42 provides a transparent-formula cross-check; AmericU's lender disclosure covers 5/6 SOFR which has no consumer-calculator equivalent. All must agree — that's the credibility anchor for the whole phase.

- **D-09: Exact Decimal equality, never `assertAlmostEqual`.** All money fields in fixture `expected` blocks are quoted Decimal strings. Compare using `==` against `Decimal("...")` parsed values. Same discipline as Phase 1+3+4. The only tolerance allowed is for documented hand-calc-vs-oracle discrepancies (Bankrate/Vertex42/AmericU) — and those should ZERO out (any non-zero discrepancy is a bug to investigate, not to assert away).

- **D-10: Citation-coverage meta-test.** Every `applied_cap` Literal value (`"initial"`, `"periodic"`, `"lifetime"`, `"floor"`, `"none"`) MUST be exercised by at least one fixture. `tests/test_arm.py::test_citation_coverage` asserts this (mirrors Phase 2 RUL-12/13 + Phase 4 D-17 inheritance). Catches "we added a new cap kind but never tested it" drift.

### Negative amortization out of scope (D-12)

- **D-12: Conventional fully-amortizing ARMs only.** Phase 5's engine assumes payment is recomputed each epoch via `npf.pmt(period_rate, remaining_term, remaining_balance)`. Negative-amortization products (Option ARM, payment-cap ARMs where the borrower may pay less than full interest) are explicitly OUT of v1. The PROJECT.md "Out of Scope" section already implicitly covers this via "personal-use, not commercial DU/LPA replication". Document the constraint in `references/arm-mechanics.md` (D-08 item 5).

### Index source v1 (D-13)

- **D-13: Caller-supplied index values only in Phase 5.** No FRED MCP integration in this phase (Phase 12). `assumed_index_rate` is REQUIRED in every request (D-01). `index_series_id` is metadata only (a string label like `"MORTGAGE30US"` or `"SOFR1Y"`); the engine does NOT look up the value at runtime. Phase 12 will populate `assumed_index_rate` via `MORTGAGE30US` weekly value at SKILL.md narration time; Phase 5's CLI takes the value as-is.

### Quantization (D-14)

- **D-14: Rate quantization at 6 decimal places via shared helper.** Use Phase 4's `_quantize_rate` (currently in `lib/affordability.py`). If Phase 5 is the second consumer, **promote `quantize_rate(Decimal) -> Decimal` to `lib/money.py`** as a public helper following the Phase 2 D-08 / Phase 3 discretion convention (scope-to-file until a second consumer needs it). Money quantization continues to use `lib.money.quantize_cents` (2 decimal places, ROUND_HALF_UP). Both helpers MUST be called at end-of-period only (Phase 1 PITFALLS, Phase 3 D-04 inherited) — never quantize mid-calculation.

### 5/6 ARM (D-15)

- **D-15: 5/6 ARM = same engine path with `reset_period_months=6`.** No special-case code in `lib/arm.py`. The structured ARMTerms fields capture the cadence; the per-epoch loop iterates per the field. Test fixture `arm_5_6_payment_jump_at_61_and_67.json` exercises this explicitly to lock the `reset_period_months` plumbing.

### Claude's Discretion

- **`_quantize_rate` helper location** — D-14 prescribes promotion to `lib/money.py` if Phase 5 is the second consumer. Planner finalizes: either keep `from lib.affordability import _quantize_rate as quantize_rate` (smallest blast radius; Phase 4 retains the helper) OR ship `lib/money.py.quantize_rate(...)` and update both `lib/affordability.py` + `lib/arm.py` imports in the same plan (cleaner long-term but touches Phase 4's frozen surface lightly). Both correct.
- **`ARMRequest` Pydantic shape** — D-01 + D-02 + D-06 specify the fields; the planner finalizes whether the request is a single flat model OR composed via Pydantic `BaseModel` nesting (`ARMRequest.loan: Loan` + `ARMRequest.arm_terms: ARMTerms` + `ARMRequest.assumed_index_rate: Decimal` + `ARMRequest.index_path: list[IndexPathEntry]`). Recommend nested for clarity; flat is also valid.
- **`IndexPathEntry` placement** — Pydantic model for each `{period, value}` index-path entry. Either inline in `lib/arm.py` (scoped to Phase 5) OR factor into `lib/models.py` (Phase 1 frozen surface — recommend NOT). Mirror Phase 3 `ExtraPrincipalEntry` discretion convention: scope to `lib/arm.py` until a second consumer needs it.
- **Per-epoch slice strategy** — D-05 mandates "build full remaining term, slice off epoch window, stitch with continuous numbering". Sub-decision for the planner: whether to call `build_schedule` once per epoch with a `synthetic_loan(term_months=remaining_full_term)` OR once per epoch with `term_months=reset_period_months` (saves the slice but loses the "full remaining term re-amortization" semantics — DO NOT take this shortcut). The first approach is correct per ARM-05.
- **`ARMSchedule.as_phase1_schedule() -> Schedule` adapter** — useful for Phase 8 stress consumers that want a Phase 1-typed view. Not required by Phase 5; ship if a downstream consumer needs it. Trivially implementable: `Schedule(loan=arm_schedule.loan, monthly_pi=arm_schedule.payments[0].payment - arm_schedule.payments[0].extra_principal, total_interest=arm_schedule.total_interest, final_payment_adjusted=arm_schedule.final_payment_adjusted, payments=[Payment(**p.model_dump(exclude={"rate_in_effect"})) for p in arm_schedule.payments])`. Trade-off: `monthly_pi` is the FIRST epoch's P&I (since `Schedule.monthly_pi` is a single value per Phase 1 convention); ARM has multiple — document the convention.
- **JSON-float pre-validation gate factoring** — Phase 4 added the float-gate to `scripts/affordability.py` (WR-02 closure). Phase 5 needs the same gate for `loan.principal`, `assumed_index_rate`, `index_path[].value`, and `floor_rate`. Either inline-copy the helper into `scripts/arm_simulate.py` OR factor into a shared `scripts/_cli_helpers.py` module. Recommend factor (Phase 6 refi NPV, Phase 7 APR, Phase 8 stress all need the same gate). Planner picks.
- **Test runner pattern** — extend `tests/conftest.py` (Phase 1) with an `arm_fixture` loader mirroring Phase 3's `amortize_fixture` and Phase 4's `affordability_fixture`. Reuse the established pattern; do not invent a new one.
- **MGIC capture format** — PDF screenshot OR HTML snapshot OR direct JSON transcription? Recommend: capture the MGIC tool output as a PDF (browser-print or screenshot to PDF), then transcribe the per-period rate/payment table into a JSON sibling. The PDF is the ground-truth artifact (committed); the JSON is the test input. Annual re-capture replaces the PDF; if MGIC changes the per-period output schema, the JSON updates too.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Inputs (project-level)

- `.planning/PROJECT.md` — project context, key decisions table (Decision #1: wrap numpy-financial; Decision #2: Decimal money; Decision #3: Pydantic v2 + condecimal; Decision #6: rules-as-predicates per citation; Decision #8: scripts INSIDE skill folder applies at Phase 10; Decision #10: bundled scripts ship with `--help` first)
- `.planning/REQUIREMENTS.md` §"ARM Modeling" — Phase 5 requirements ARM-01..09 (definitive)
- `.planning/ROADMAP.md` §"Phase 5: ARM Modeling" — phase goal + 5 success criteria (esp. SC-1 ARMTerms field set; SC-2 5/1 payment-jump at month 61; SC-3 both 60/61 reset-month conventions; SC-4 floor enforcement; SC-5 references/arm-mechanics.md citation chain)
- `.planning/STATE.md` — current project state (Phase 4 complete; ready to start Phase 5)
- `CLAUDE.md` — money discipline (Decimal from strings, ROUND_HALF_UP, never mix with float), calc-engine separation (Claude never owns numbers), Pydantic v2 condecimal at script boundaries, no Co-Authored-By in commits
- `DATA_CONTRACT.md` — User/System/Data/Reference layer separation; `scripts/` is System Layer

### Phase 5 Research + Patterns (will be created by gsd-phase-researcher)

- `.planning/phases/05-arm-modeling/05-RESEARCH.md` — to be written; researcher consumes this CONTEXT.md to know what to investigate (MGIC ARM calculator capture mechanics, Freddie/Fannie Selling Guide ARM section citations, per-epoch slice-stitch strategy validation, ARMPayment subclassing pattern under Pydantic v2, index_path + assumed_index_rate override semantics)
- `.planning/phases/05-arm-modeling/05-PATTERNS.md` — to be written by gsd-pattern-mapper; identifies Phase 1/3/4 analogs for new Phase 5 files

### Project Research (already verified by Phase 1/2/3/4 research; Phase 5 reads as background)

- `.planning/research/STACK.md` — numpy-financial verdict matrix (BSD-3, Decimal support, vectorizes; bugs #130 fv-sign avoid `fv != 0`, #131 irr arch-dependent avoid `npf.irr`)
- `.planning/research/FEATURES.md` §"ARM modeling" — HIGH priority MVP feature; index + margin + caps + floor + reset logic
- `.planning/research/PITFALLS.md` §"Pitfall 5: ARM cap/floor/margin/reset off-by-one" — drives D-02 (formula lock) + D-03 (period numbering) + D-09 (both-conventions test fixtures)
- `.planning/research/ARCHITECTURE.md` §"Pattern 1: Claude/Python Calc Split" — JSON-in/JSON-out script boundary; Pydantic validates on read
- `.planning/research/SUMMARY.md` — top-level research index

### Prior-Phase Frozen Surfaces (Phase 5 USES; does NOT modify)

- `lib/models.py` (Phase 1 + Phase 3 D-14 extensions) — `Loan`, `Schedule`, `Payment` (with `cumulative_interest` + `cumulative_principal`), `Money`, `Rate` types. Phase 5 imports `Loan` + `Payment` + `Schedule` + `Money` + `Rate`. Phase 5 does NOT modify Phase 1 Payment or Schedule (D-03 parallel-models choice).
- `lib/money.py` (Phase 1) — `to_money(str)`, `quantize_cents(Decimal)`, `CENT`, `MONEY_CONTEXT` (ROUND_HALF_UP). Use in EVERY Decimal cents-rounding inside `lib/arm.py`. Phase 5 may PROMOTE `quantize_rate(Decimal) -> Decimal` to `lib/money.py` if it becomes the second consumer (D-14).
- `lib/amortize.py` (Phase 3) — `build_schedule(loan, frequency='monthly', biweekly_mode=None, extra_principal=())` produces `Schedule.payments`. Phase 5 RE-ENTERS this once per epoch with synthetic `Loan(principal=remaining_balance, annual_rate=new_rate, term_months=remaining_full_term)` per D-05.
- `lib/affordability.py` (Phase 4) — `_quantize_rate(Decimal) -> Decimal` (currently private; D-14 candidate for promotion to `lib/money.py`). Phase 5 imports either as `from lib.affordability import _quantize_rate as quantize_rate` (smaller blast radius) OR via the promoted `lib.money.quantize_rate` (cleaner long-term).
- `tests/conftest.py` (Phase 1 + Phase 3 + Phase 4 extensions) — pytest `amortize_fixture` + `affordability_fixture` loaders. Phase 5 ADDS `arm_fixture` loader following the same pattern (D-09).
- `tests/fixtures/golden_pmt.json` (Phase 1) — 4 oracle fixtures. Phase 5 reuses the $400k @ 6.5% / 30yr → $2,528.27 P&I anchor for the initial-fixed-period assertion (epoch 0 must produce this PMT exactly when `loan.annual_rate = 0.065`).
- `tests/test_amortize.py` (Phase 3) — model for `tests/test_arm.py` structure (golden + structural + invariant + CLI smoke).
- `tests/test_affordability.py` (Phase 4) — model for fixture-loader pattern + 6-key envelope test pattern + citation-coverage meta-test pattern.
- `pyproject.toml` (Phase 1 + Phase 3 numpy-financial add) — mypy --strict, ruff, pytest, numpy-financial all configured. Phase 5 ADDS no new deps (pure composition over Phase 1/3/4 surface).

### Prior-Phase CONTEXT.md (read for decisions that affect Phase 5)

- `.planning/phases/03-core-amortization/03-CONTEXT.md` — Phase 3 D-04 (rate-per-period: monthly = annual_rate / 12), D-09 (final-payment cleanup applies to LAST epoch only per Phase 5 D-05), D-10 (`final_payment_adjusted: bool`), D-14 (Payment cumulative totals), D-17 (`scripts/` lives at project root for now; Phase 10 relocates), D-18 (`--input <path>` only, lazy-import for fast `--help`), D-19 (Pydantic envelope at boundary). Lines 169–174: explicit Phase 3 → Phase 5 contract ("Phase 5 will RE-ENTER `lib.amortize.build_schedule` at each ARM reset with new rate + remaining balance + remaining term").
- `.planning/phases/04-affordability/04-CONTEXT.md` — Phase 4 D-09 (`_quantize_rate` at 6 decimal places — Phase 5 D-14 reuses or promotes), D-13 (CLI mirror conventions — Phase 5 D-07 inherits), D-14 (Pydantic discriminated union pattern — Phase 5 ARMRequest may use), D-17 (fixture-loader pattern — Phase 5 D-09 mirrors). Lines 277–282: explicit Phase 4 → Phase 5 contract ("Phase 5 (ARM): ARM affordability uses Phase 4's `lib.affordability` at each reset to recompute DTI under the new payment").
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-CONTEXT.md` — Phase 2 D-08 (predicates imported by full path; no re-exports — Phase 5 inherits this convention for any new helpers), D-12 (no `staleness_acknowledged_until` override — Phase 5 reads YAML if any reference data is needed, but Phase 5 currently has no `data/reference/arm-*.yml` need; defer if a reference YAML emerges).

### External Sources (regulatory + tool oracles)

- https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms — Fannie Mae Single-Family Selling Guide §B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)" (last updated 2025-12-10). Citation source for D-02 reset formula, D-08 reference doc, D-04 oracle hand-calc.
- https://guide.freddiemac.com/ — Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b) (ARM mechanics — modern equivalent of the legacy §4404). Citation source for D-02 reset formula, D-08 reference doc.
- https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms — Freddie Mac SOFR-Indexed ARMs product page. Cross-reference for SOFR-based 5/6 ARMs (D-15).
- https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/ — Bankrate ARM Calculator (3/1, 5/1, 7/1, 10/1). Primary capture-as-fixture oracle for D-04 (5/1, 7/1, 10/1 products). Annual re-capture cadence.
- https://www.vertex42.com/ExcelTemplates/arm-calculator.html — Vertex42 ARM Calculator (Excel, transparent formulas). Secondary oracle for D-04 cross-validation.
- https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf — AmericU 5/6 SOFR ARM Disclosure (2/1/5 caps). Lender-published worked example; only credible 5/6 ARM ground-truth oracle for D-04.
- https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/ — CFPB §1951 ARM rate caps explainer. Cited in D-08 item 7 (teaser-ARM lifetime cap base — engine choice vs CFPB consumer convention).
- https://www.cfpb.gov/owning-a-home/loan-options/adjustable-rate-mortgage/ — CFPB ARM consumer disclosure (background reading; not load-bearing for engine math).
- https://numpy.org/numpy-financial/latest/ — `npf.pmt` API docs (called per epoch via `lib.amortize.build_schedule`). Phase 3 STACK.md already cites; Phase 5 inherits.
- https://github.com/numpy/numpy-financial/issues/130 — pmt fv-sign bug (Phase 3 D-19 / Phase 4 D-08 reinforced; Phase 5 inherits — `build_schedule` always passes `fv=0`).

### Phase 1 Reference YAMLs (Phase 5 does NOT consume)

- Phase 5 has NO `data/reference/arm-*.yml` need in v1. ARM mechanics are formula-driven (D-02), not table-driven. If Phase 8 stress or Phase 12 FRED MCP triggers a need for an ARM-product catalog YAML (e.g., known ARM products with default cap structures), defer to that phase.

### Pattern References

- `https://github.com/cfpb/hmda-platform` — predicate-per-citation pattern (Phase 2 follows; Phase 5 does not introduce new predicates — caps/floor/margin live as ARMTerms fields, not as `lib/rules/*` predicates)
- `tests/test_money.py` (Phase 1) — Decimal-discipline test pattern (string construction, exact equality)
- `tests/test_fixtures.py` (Phase 1) — golden-fixture loader pattern (FND-09)
- `tests/test_amortize.py` (Phase 3) — model for `tests/test_arm.py` structure (golden + structural + invariant + CLI smoke + lazy-import test + envelope-uniformity test)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`lib/models.py`** (Phase 1+3): `Loan`, `Payment`, `Schedule`, `Money`, `Rate`. Phase 5 USES; does NOT modify. New Phase 5 Pydantic models (`ARMTerms`, `ARMRequest`, `IndexPathEntry`, `ARMPayment(Payment)`, `ARMSchedule`, `ResetEvent`) live in `lib/arm.py` (scoped per Phase 2 D-08 / Phase 3 D-discretion convention) until a second consumer needs them.
- **`lib/money.py`** (Phase 1): `to_money(str)`, `quantize_cents(Decimal)`, `CENT`, `MONEY_CONTEXT`. Every Decimal cents-rounding in `lib/arm.py` MUST flow through `quantize_cents`. Phase 5 may PROMOTE `quantize_rate(Decimal) -> Decimal` here if planner picks the promotion path (D-14).
- **`lib/amortize.py`** (Phase 3): `build_schedule(loan, frequency='monthly', biweekly_mode=None, extra_principal=())` is the per-epoch re-entry point (D-05). Phase 5 calls per epoch with `Loan(principal=remaining_balance, annual_rate=new_rate, term_months=remaining_full_term)` and slices off `payments[0:reset_period_months]` for non-final epochs.
- **`lib/affordability.py`** (Phase 4): `_quantize_rate(Decimal) -> Decimal` at 6 decimal places. Phase 5 either imports as-is (smallest blast radius) OR is the promotion catalyst (D-14).
- **`scripts/amortize.py`** (Phase 3) + **`scripts/affordability.py`** (Phase 4): mirror exactly for `scripts/arm_simulate.py` shape — argparse + `--input <path>` + lazy-import + 6-key Pydantic envelope on validation errors + JSON-float pre-validation gate.
- **`tests/conftest.py`** (Phase 1+3+4): pytest fixture factory pattern. Phase 5 ADDS `arm_fixture` loader mirroring Phase 3's `amortize_fixture` + Phase 4's `affordability_fixture`.
- **`tests/fixtures/golden_pmt.json`** (Phase 1): 4 oracle fixtures. Phase 5 epoch-0 (initial-fixed-period) PMT computation must match the $400k @ 6.5% / 30yr → $2,528.27 anchor when `loan.annual_rate = 0.065`.
- **`pyproject.toml`** (Phase 1): mypy --strict, ruff, pytest, numpy-financial all configured. Phase 5 ADDS no new deps (pure composition over Phase 1/3/4 surface).

### Established Patterns

- **One Pydantic model per concern, scoped to file** (Phase 2 D-08 / Phase 3 D-discretion / Phase 4 D-discretion): Phase 5 keeps ARM-specific models in `lib/arm.py`. Promote to `lib/models.py` only on a second consumer.
- **Pydantic v2 strict + frozen + extra=forbid** (Phase 1, reinforced Phase 2/3/4): `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` for ALL Phase 5 domain models. ARMPayment subclassing Phase 1 Payment retains the same model_config (the parent's config doesn't auto-inherit; planner re-specifies).
- **Decimal-from-strings, exact equality, no `assertAlmostEqual`** (Phase 1+3+4): `Decimal("0.065")` not `Decimal(0.065)`. Test fixture `expected` fields are quoted strings.
- **JSON-in / JSON-out CLI at project root** (Phase 3 D-17/18/19 + Phase 4 D-13): Phase 5 inherits all six conventions exactly (D-07).
- **6-key Pydantic envelope on validation errors** (Phase 3 WR-02 + Phase 4 D-13): `type / loc / msg / input / url / ctx`. URL version segment runtime-pinned via `pydantic.VERSION` per Phase 3 03-PLAN-06 closure. Phase 5 inherits.
- **JSON-float pre-validation gate** (Phase 4 WR-02 closure in `scripts/affordability.py`): floats in money fields rejected at the boundary BEFORE Pydantic sees them. Phase 5 EXTENDS this to ARM money fields (`loan.principal`, `assumed_index_rate`, `index_path[].value`, `floor_rate`). Either inline-copy the helper OR factor into `scripts/_cli_helpers.py` (D-discretion).
- **Hand-calculated golden fixtures with `source` URL + citation comments** (Phase 1+2+3+4): each ARM fixture JSON has `source: ROADMAP.md SC-N` or Selling Guide section reference in a `notes` block. MGIC oracle captures get a `source: https://www.mgic.com/tools/calculators (captured YYYY-MM-DD)` comment.
- **Quantize end-of-period only** (Phase 1 PITFALLS, Phase 3 D-04, Phase 4 D-09): one `quantize_cents()` or `quantize_rate()` call per money/rate output; never quantize mid-calculation.
- **Subprocess invocation in CLI tests** (Phase 3 D-17 portability): Phase 5 tests invoke `scripts/arm_simulate.py` via subprocess with a `SCRIPT_PATH` constant. NEVER `from scripts.arm_simulate import main` — Phase 10 may relocate.
- **Citation-coverage meta-test pattern** (Phase 2 RUL-12/13 + Phase 4 inheritance): every `applied_cap` Literal value MUST be exercised by at least one fixture (D-10).

### Integration Points

- **`pyproject.toml`** — no new deps expected. Phase 5 composes existing `numpy-financial`, `pydantic`, `python-dateutil`, `lib.amortize`. Verify mypy --strict + ruff stay clean across `lib/arm.py` + `scripts/arm_simulate.py` + `tests/test_arm.py`.
- **`lib/arm.py`** — new file. Imports: `numpy_financial as npf` (transitively via `lib.amortize`; not strictly needed direct), `decimal`, `pydantic`, `lib.models` (Loan, Payment, Schedule, Money, Rate), `lib.money` (quantize_cents, CENT, MONEY_CONTEXT, optionally promoted quantize_rate), `lib.amortize` (build_schedule), `lib.affordability` (optionally `_quantize_rate` if not promoted), `dateutil.relativedelta` for per-epoch origination_date offsets if planner picks that strategy.
- **`scripts/arm_simulate.py`** — new file at project root. Argparse + `ARMRequest.model_validate_json` + dispatch into `lib.arm.build_arm_schedule(arm_request) -> ARMSchedule` + `print(arm_schedule.model_dump_json(indent=2))`. Lazy-import `lib.arm` after argparse. JSON-float pre-validation gate inline OR via shared helper (D-discretion).
- **`lib/models.py`** — NO modifications expected (D-03 parallel-models choice). If a planner finds Phase 5 needs a new shared model, prefer `lib/arm.py` first; promote to `lib/models.py` only on the second consumer.
- **`lib/affordability.py`** — touched ONLY if planner picks the `_quantize_rate` → `lib.money.quantize_rate` promotion path (D-14). In that case: rename + add public symbol in `lib/money.py`, update `lib/affordability.py` import, run Phase 4's full test suite (379 passed + 4 skipped) to verify zero regression. Otherwise UNTOUCHED.
- **`lib/amortize.py`** — UNTOUCHED. Phase 5 only calls `build_schedule(...)` per D-05; does not modify Phase 3 frozen surface. Verify Phase 3's 301-test suite still passes after Phase 5 ships.
- **`tests/test_arm.py`** — new file. Cases per D-09 fixture list + envelope-uniformity test (Phase 3 03-PLAN-06 pattern) + lazy-import test (Phase 3 D-18 pattern) + citation-coverage meta-test (D-10).
- **`tests/fixtures/arm/`** — new directory. JSON fixtures per scenario.
- **`tests/fixtures/arm/oracle/`** — new directory. MGIC capture PDFs + JSON transcriptions.
- **`tests/conftest.py`** — extend with `arm_fixture` loader mirroring Phase 3+4 patterns.
- **`references/arm-mechanics.md`** — new file at repo root. Documents D-02 reset formula + D-13 floor algebra + D-04 oracle strategy + D-12 negative-amortization-OUT-of-scope + D-15 5/6 ARM convention + D-08 Selling Guide citations.

### Phase 6+ downstream consumers (DO NOT BREAK in Phase 5)

- **Phase 6 (Refi NPV):** decoupled. Refi NPV sees a current loan balance + a new loan offer; it does NOT consume `ARMSchedule` directly. Stable contract: `ARMSchedule.payments[i].balance` is the at-period-i remaining balance for refi NPV inputs (consumer reads as needed; no Phase 5 obligation).
- **Phase 7 (Estimated APR Reg Z Appendix J):** ARMs are modeled as a sequence of unit-periods per Reg Z Appendix J. Phase 7 may consume `ARMSchedule.payments[i].rate_in_effect` per unit-period for the APR Newton-Raphson solve. Stable contract: D-03 `ARMPayment.rate_in_effect: Rate` field is locked.
- **Phase 8 (Stress):** rate-shock + ARM-reset sweeps re-invoke `build_arm_schedule` per grid cell with parameter-shifted `index_path` arrays. Stable contract: `build_arm_schedule(arm_request) -> ARMSchedule`. Vectorization is OPTIONAL (per-cell Python loop fine for personal-use stress sweeps < 100 cells).
- **Phase 9 (DuckDB persistence):** Schema must accommodate `ARMSchedule` shape (loan, arm_terms, payments, reset_events, total_interest, final_payment_adjusted). Phase 9 owns the schema; Phase 5 just emits Pydantic-serializable JSON.
- **Phase 10 (Skill):** `arm` mode in `.claude/skills/mortgage-ops/modes/arm.md` routes to `scripts/arm_simulate.py`. Phase 5 should NOT lock the script path in any test that imports `scripts.arm_simulate` — prefer subprocess invocation with a `SCRIPT_PATH` constant per Phase 3 D-17 + Phase 4 D-13.
- **Phase 11 (Subagents):** `amortization-agent` (Haiku) handles single-loan ARM amortization requests; `stress-test-agent` (Sonnet) handles multi-scenario ARM-reset sweeps. Both consume the Phase 5 CLI surface unchanged.
- **Phase 12 (FRED MCP):** populates `assumed_index_rate` from `MORTGAGE30US` weekly value at SKILL.md narration time. Phase 5's CLI takes the value as-is — no Phase 5 obligation to integrate FRED.

</code_context>

<specifics>
## Specific Ideas

- **Reset month convention LOCKED at month 61 for 5/1.** (ROADMAP SC-2 + PITFALL 5 + D-02). Rate change applies at the START of the post-fixed-period month. Tests must explicitly cover both 60-month-end (assert: still old payment) and 61-month-start (assert: already new payment) per ROADMAP SC-3.
- **REQUIRED `floor_rate` in ARMTerms (no None / no default).** Forces explicit caller choice every request. Matches mortgage-ops "fail loud, no inference" discipline. Effective floor at run time = `max(margin_bps/10000, floor_rate)`.
- **`note_rate: Rate | None = None` in ARMTerms.** When None, engine treats `note_rate = loan.annual_rate`. When provided (teaser-rate ARMs), engine uses the provided value for lifetime-cap ceiling math. Lets common case stay simple; supports teaser ARMs without forcing every caller to set the field.
- **First reset uses `initial_cap_bps`; all subsequent resets use `periodic_cap_bps`.** Industry standard; locked in D-02. ResetEvent.applied_cap captures which constraint bound (`"initial"` vs `"periodic"` vs `"lifetime"` vs `"floor"` vs `"none"`).
- **Lifetime cap measured against `note_rate`.** ceiling = `note_rate + lifetime_cap_bps/10000`, NOT against `prior_rate + lifetime_cap_bps`. Standard convention.
- **Index supply = flat `assumed_index_rate` (REQUIRED) + optional per-reset `index_path` overrides.** Override-wins at exact reset trigger periods; misaligned `index_path` periods raise Pydantic validation errors at the request boundary. `index_series_id` is metadata only in v1; Phase 12 maps to FRED.
- **Parallel `ARMSchedule` + `ARMPayment(Payment)` in `lib/arm.py`.** Phase 1 Payment / Schedule UNCHANGED. ARMPayment subclasses Payment via Pydantic v2 inheritance; `list[ARMPayment]` is structurally compatible with `list[Payment]`. Phase 8 + Phase 4 consumers iterate ARMSchedule.payments directly without an adapter.
- **Continuous period numbering 1..N across epochs.** payments[i].period == i + 1; payments[-1].period == loan.term_months. ResetEvent.period locates each reset boundary.
- **Per-epoch re-entry into `lib.amortize.build_schedule` with FULL remaining term + slice.** Each epoch builds a synthetic schedule over the FULL remaining term (not just reset_period_months) per ARM-05 "remaining balance recasts over remaining term at new rate". Engine slices off only the rows for the current epoch window. Phase 3 D-09 final cleanup applies ONLY to the FINAL epoch (intermediate epochs always carry forward).
- **MGIC capture-as-fixture oracle + hand-calc per Selling Guide cross-validation.** Both must agree exactly. Annual re-capture cadence parallels FFIEC for Phase 7 APR.
- **Citation-coverage meta-test for `applied_cap` Literal values.** Every cap-kind (`"initial"`, `"periodic"`, `"lifetime"`, `"floor"`, `"none"`) must be exercised by at least one fixture (D-10).
- **5/6 ARM via `reset_period_months=6`, no special-case code.** Test fixture `arm_5_6_payment_jump_at_61_and_67.json` exercises this explicitly to lock the field plumbing.
- **Negative amortization OUT of scope (D-12).** Conventional fully-amortizing ARMs only. Option ARM / payment-cap products deferred to v2. Document the constraint in `references/arm-mechanics.md`.
- **No new deps.** Phase 5 is pure composition over numpy-financial + pydantic + python-dateutil + `lib.amortize` + `lib.money`.

</specifics>

<deferred>
## Deferred Ideas

- **Option ARM / payment-cap / negative-amortization products** — explicitly OUT of v1 (D-12). Add only if a real consumer needs to model these (rare for personal-use household analysis).
- **FRED MCP live `MORTGAGE30US` / `SOFR1Y` index injection** — Phase 12. Phase 5 takes caller-supplied `assumed_index_rate` only.
- **Index lookback windows** ("use index value 45 days before reset date") — out of v1. ARM-mechanics.md notes the simplification; v2 if a real product surfaces.
- **`index_series_id` → FRED series ID enum/Literal mapping** — Phase 12. v1 keeps the field as a free-form string (metadata only).
- **ARM-aware affordability re-evaluation** (DTI at each reset) — Phase 8 stress (consumes ARMSchedule + Phase 4 `lib.affordability`).
- **Stress-test rate-shock + ARM-reset parameter sweeps** — Phase 8.
- **DuckDB persistence of ARMSchedule + ResetEvent rows** — Phase 9.
- **Skill physical relocation of `scripts/arm_simulate.py`** → `.claude/skills/mortgage-ops/scripts/arm_simulate.py` — Phase 10.
- **`.claude/skills/mortgage-ops/references/arm-mechanics.md` mirror** — Phase 10 (copy or symlink from `references/arm-mechanics.md`).
- **`amortization-agent` / `stress-test-agent` ARM routing** — Phase 11.
- **Bankrate cross-validation as third oracle** — v2 if MGIC + hand-calc disagree on edge cases. v1 sticks with MGIC + hand-calc per D-04.
- **Teaser-rate ARM fixtures with `note_rate ≠ loan.annual_rate`** — v1 supports the field (D-06) and ships ONE fixture exercising it (`arm_teaser_rate.json` per D-09); v2 expands the matrix if real teaser products emerge.
- **`ARMSchedule.as_phase1_schedule() -> Schedule` adapter** — ship if a downstream consumer needs it (Phase 8 stress most likely candidate). Phase 5 leaves the helper out unless planning surfaces a need.
- **Stdin-based CLI input** — v2 (inherits Phase 3 D-18 + Phase 4 D-13 deferral).
- **Vectorized ARM schedule generation** (numpy-financial vector path across the parameter grid) — Phase 8 stress problem if scalar paths are too slow for the sweep size. Unlikely for personal-use < 100 cells.
- **`tests/fixtures/arm/oracle/bankrate_*.pdf`** — v2 cross-oracle. v1 ships MGIC only per D-04.
- **`data/reference/arm-known-products.yml`** — known ARM products catalog (5/1 conventional, 5/1 FHA-insured, 7/1 jumbo, ...) with default cap structures. Defer until a Phase 8/10 consumer needs default values.
- **JSON-Schema export of `ARMRequest`** — useful for SKILL.md routing in Phase 10. Phase 5 emits via `ARMRequest.model_json_schema()` only if a planner finds a downstream consumer needs it.
- **Half-monthly biweekly ARMs** — out of v1. Phase 3 D-01 supports biweekly fixed-rate; Phase 5 ARMs are monthly only. Add only if a real biweekly ARM product surfaces (rare).

</deferred>

---

*Phase: 05-arm-modeling*
*Context gathered: 2026-04-30*
