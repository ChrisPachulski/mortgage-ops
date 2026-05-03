# Phase 8: Stress Tests & Points Breakeven — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 11 NEW (Phase 8 scope) + 4 MODIFIED (extension of existing infrastructure) + 13 fixture files
**Analogs found:** 11 / 11 — Phase 8 is composition-not-reimplementation; every new file maps onto an existing Phase 3/4/5 analog with file paths + line numbers below.

## Phase 8 Strategy: Composition-Not-Reimplementation

Phase 8 stress sweeps are essentially calling `lib.amortize.build_schedule` (Phase 3), `lib.affordability.evaluate` (Phase 4), and `lib.arm.build_arm_schedule` (Phase 5) in a loop with parameter grids, then assembling a top-table-summary JSON envelope. Discount-points breakeven is two functions: `simple_breakeven` (one division) and `npv_breakeven` (cumulative-NPV walk). NO new mathematical primitive is required — every dollar figure derives from a Phase 3/4/5 engine call.

This pattern map's main job is to enforce that planners route through the existing engines (NOT re-derive amortization or DTI inline). The "weak match" cells below are where Phase 8 is the FIRST consumer of a structural pattern (e.g., scenario-summary table at top of JSON for SC-5 subagent consumption); those mark the genuinely new design choices that 08-RESEARCH.md must pin.

## File Classification

### NEW files (Phase 8 creates)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lib/stress.py` | domain-engine (3 sweep functions: rate_shock, income_shock, arm_path) | transform (parameters grid → list[result]) | `lib/affordability.py` (composition over Phase 2 predicates + Phase 3 engine) + `lib/arm.py` (per-epoch loop calling Phase 3 engine) | exact (composite) |
| `lib/points.py` | domain-engine (simple_breakeven + npv_breakeven + dispatcher) | transform (PointsRequest → PointsResponse) | `lib/affordability.py:_compute_*` private helpers (pure-function math layer) | exact |
| `scripts/stress_test.py` | CLI entrypoint with `--mode {rate-shock\|income-shock\|arm-reset}` dispatcher | request-response (JSON-in --input → JSON-out stdout) | `scripts/affordability.py` (mode dispatch via Pydantic discriminated union) + `scripts/arm_simulate.py` (single-mode shape) | exact (composite) |
| `scripts/points_breakeven.py` | CLI entrypoint | request-response | `scripts/amortize.py` (single-engine shape, simplest analog) | exact |
| `tests/test_stress.py` | test (parametric + fixture + CLI smoke + meta) | test | `tests/test_arm.py` (32-stub xfail Nyquist scaffold; SCRIPT_PATH constant) + `tests/test_affordability.py` (composite header + 6-key envelope tests) | exact (composite) |
| `tests/test_points.py` | test (golden + structural + CLI smoke) | test | `tests/test_amortize.py` (smaller-surface single-engine analog) | exact |
| `tests/fixtures/stress/*.json` (11 fixtures: 5 rate-shock + 3 income-shock + 3 arm-path) | test fixture (one-per-file JSON) | static data | `tests/fixtures/arm/*.json` (one-per-file shape) + `tests/fixtures/affordability/*.json` | exact |
| `tests/fixtures/points/*.json` (3 fixtures: 2 standard + 1 divergence-pin) | test fixture | static data | `tests/fixtures/amortize/*.json` | exact |
| `references/stress-tests.md` | reference doc (sweep mechanics + scenario-summary table schema + subagent consumption contract for Phase 11) | static doc | `references/arm-mechanics.md` (Phase 5 doc style; the only existing `references/*.md` analog) | exact |
| `references/points-breakeven.md` | reference doc (simple vs NPV decision; discount-rate disclosure; divergence example) | static doc | `references/arm-mechanics.md` | exact |
| `tests/fixtures/stress/oracle/.gitkeep` | committable empty oracle dir | n/a (placeholder) | `tests/fixtures/arm/oracle/.gitkeep` (Phase 5 idiom) | exact |

### MODIFIED files (Phase 8 extends existing)

| Modified File | Role | Modification | Closest Analog Pattern |
|---|---|---|---|
| `tests/conftest.py` | test fixture loader | extend with `stress_fixture` + `points_fixture` factories (lines appended after current `arm_fixture` at line 91) | own file lines 38-90 (`amortize_fixture` + `affordability_fixture` + `arm_fixture` factories) |
| `scripts/_cli_helpers.py` | shared CLI utility | NO new functions required — Phase 8 reuses `find_json_float_loc` + `make_decimal_type_envelope` AS-IS | own file (Phase 5 already factored both helpers; Phase 8 is the third+fourth consumer) |
| `lib/amortize.py` | Phase 3 engine | NO modification — Phase 8 calls `build_schedule(loan)` once per rate in the rate-shock grid and reads `Schedule.monthly_pi` | (used as-is) |
| `lib/affordability.py` | Phase 4 engine | NO modification — Phase 8 calls `evaluate(req)` once per reduction in the income-shock grid and reads `AffordabilityResponse.dti_back` | (used as-is) |
| `lib/arm.py` | Phase 5 engine | NO modification — Phase 8 constructs `ARMRequest(index_path=[...])` per rate-path and reads `ARMSchedule.total_interest` | (used as-is) |

---

## Pattern Assignments

### `lib/stress.py` (domain engine — composite analog)

**Primary analogs:**
- `lib/affordability.py` — Pydantic v2 strict+frozen+forbid models + private helper layer + `evaluate(req)` dispatcher over a discriminated union (Phase 8 mode discriminator: `rate-shock | income-shock | arm-reset`)
- `lib/arm.py` — per-epoch loop CALLING the Phase 3 engine via synthesized `Loan` objects (Phase 8 sweeps follow the same pattern: synthesize a request per grid cell, call the engine, collect results)

**Pattern 1: Pydantic v2 discriminated union over `mode` (sweep dispatcher)**

Source: `lib/affordability.py:441-528` (the `_CommonRequestFields` base + `ForwardModeRequest(mode='forward')` + `ReverseModeRequest(mode='reverse')` + Pydantic `Field(discriminator='mode')`).

```python
# lib/affordability.py:441-528 (excerpt — discriminated union shape)
class _CommonRequestFields(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    household: Household
    max_dti: Rate
    target_loan_type: TargetLoanType
    term_months: int = Field(ge=1, le=600)
    annual_rate: Rate
    # ...

class ForwardModeRequest(_CommonRequestFields):
    mode: Literal["forward"] = "forward"
    loan_amount: Money
    property_value: Money

class ReverseModeRequest(_CommonRequestFields):
    mode: Literal["reverse"] = "reverse"
    down_payment: Money
    target_ltv_pct: Rate

AffordabilityRequest = Annotated[
    ForwardModeRequest | ReverseModeRequest,
    Field(discriminator="mode"),
]
```

**Apply to `lib/stress.py`:** Define `_CommonStressFields` base (loan or household + scenario_label + threshold), then three subclasses:
- `RateShockRequest(mode='rate-shock', loan: Loan, rates: list[Rate])`
- `IncomeShockRequest(mode='income-shock', household: Household, base_request: AffordabilityRequest, reductions: list[Rate], dti_threshold: Rate)`
- `ArmResetRequest(mode='arm-reset', base_arm_request: ARMRequest, paths: list[RatePath])`

Combined as `StressRequest = Annotated[RateShockRequest | IncomeShockRequest | ArmResetRequest, Field(discriminator='mode')]`. The CLI's `--mode` arg routes to the matching shape via `model_validate_json` discrimination — no manual if/elif chain.

**Pattern 2: Pure-function helper layer (per-cell computation)**

Source: `lib/affordability.py` private helpers `_compute_dti`, `_compute_ltv`, `_compute_cltv`, `_compute_piti`, `_classify_target_loan_type` — each is a pure function returning a Decimal or struct.

**Apply to `lib/stress.py`:** Three pure-function sweep primitives, each loops over its grid and calls a Phase 3/4/5 engine:
```python
def rate_shock(loan: Loan, rates: Sequence[Rate], term_months: int) -> list[RateShockRow]:
    """For each rate r in rates: synthesize Loan(annual_rate=r), call build_schedule, capture monthly_pi + total_interest."""
def income_shock(req: AffordabilityRequest, reductions: Sequence[Rate], threshold: Rate) -> list[IncomeShockRow]:
    """For each reduction r in reductions: scale household income by (1-r), call evaluate(), capture dti_back + breach flag."""
def arm_path(arm_req: ARMRequest, paths: Sequence[RatePath]) -> list[ArmPathRow]:
    """For each named path: synthesize index_path entries per reset trigger, call build_arm_schedule, capture total_interest."""
```

**Pattern 3: Per-epoch synthetic Loan re-entering Phase 3 engine (for stress sweeps that hold Phase 3 fixed)**

Source: `lib/arm.py:418-432` (Wave 3 epoch synthesis):
```python
# lib/arm.py:418-432 (the synthetic-Loan + re-call-build_schedule idiom)
synthetic_loan = Loan(
    principal=remaining_balance,
    annual_rate=current_rate,
    term_months=remaining_full_term,
    origination_date=loan.origination_date,
    loan_type="arm",
)
synthetic = build_schedule(
    synthetic_loan,
    frequency="monthly",
    biweekly_mode=None,
    extra_principal=(),
)
```

**Apply to `lib/stress.py::rate_shock`:** Each rate in the grid synthesizes a `Loan(annual_rate=rate, principal=base_principal, term_months=base_term)` and calls `build_schedule(loan)` once. Read `schedule.monthly_pi` + `schedule.total_interest`. Exact-to-cent per ROADMAP SC-1 because Phase 3 is exact-to-cent.

**Pattern 4: ARM index_path injection for path simulation (Phase 5 ARM-01 already shipped this surface)**

Source: `lib/arm.py:70-84` (`IndexPathEntry` + `ARMRequest.index_path` field) + `lib/arm.py:107-145` (`_index_path_periods_align_to_reset_triggers` validator).

**Apply to `lib/stress.py::arm_path`:** For each named rate path (parallel-shift / gradual-rise / fall-then-rise), synthesize a list of `IndexPathEntry(period=trigger, value=path_value_at_trigger)` covering ALL reset triggers in the term. Construct `ARMRequest(loan=base_loan, arm_terms=base_terms, assumed_index_rate=base_index, index_path=synthesized_entries)`, call `build_arm_schedule(req)`, read `schedule.total_interest`. ROADMAP SC-3 closure.

The reset-trigger formula is already exposed via `lib.arm._compute_reset_triggers(arm_terms, term_months)` (lib/arm.py:244-259) — Plan 08-02 imports it OR re-derives the formula `[initial+1, +reset, ...]` to keep `lib/stress.py` decoupled from `lib.arm` private helpers. **DECISION POINT for Plan 08-02 LOCKED DECISIONS block.**

---

### `lib/points.py` (domain engine — pure-function pair)

**Primary analog:** `lib/affordability.py` private helpers (`_compute_dti`, `_compute_piti`) — pure-function math layer with hand-calculable expected values.

**Pattern 5: Two pure functions + dispatcher**

```python
# lib/points.py shape (mirrors lib/affordability.py's pure-helper layer)
def simple_breakeven(points_cost: Money, monthly_savings: Money) -> int:
    """months_to_breakeven = ceil(points_cost / monthly_savings). PNTS-01."""

def npv_breakeven(
    points_cost: Money,
    monthly_savings: Money,
    hold_months: int,
    discount_rate_annual: Rate,
) -> tuple[Decimal, int | None]:
    """Returns (cumulative_npv_at_hold, months_to_npv_zero | None). PNTS-02."""

def evaluate(req: PointsRequest) -> PointsResponse:
    """Dispatch: compute simple AND npv breakeven side-by-side; report disagreement flag. PNTS-02 + ROADMAP SC-4."""
```

**Numerical recipe for `npv_breakeven`:** Cumulative NPV at month m = `sum_{k=1..m} (monthly_savings / (1 + discount_rate_monthly)^k) - points_cost`. Find first m where `cum_npv >= 0`. Discount-rate convention is Phase 6's borrower opportunity cost — see 08-RESEARCH.md §"Discount-rate cross-phase coupling" for the deferred-coupling note.

---

### `scripts/stress_test.py` (CLI dispatcher — composite analog)

**Primary analogs:**
- `scripts/affordability.py:70-130` — `--input <path>` only, lazy-import after argparse, mode discriminated via Pydantic (NOT argparse subparsers — keeps CLI symmetric with affordability)
- `scripts/arm_simulate.py:32-103` — single-engine 100-line shape; lazy-import idiom; subprocess-portable

**Pattern 6: Lazy-import + JSON-float gate + 6-key envelope (inherited from Phase 3 D-19 / WR-02 closure)**

Source: `scripts/arm_simulate.py:60-99` (the entire main body is the canonical Phase 5 shape). Phase 8 lifts this verbatim, adding only the `--mode` argparse hint.

```python
# scripts/arm_simulate.py:60-99 (Phase 5 canonical CLI body)
def main() -> int:
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--input", required=True, type=Path, ...)
    args = parser.parse_args()
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    from lib.arm import ARMRequest, build_arm_schedule  # lazy!
    from pydantic import ValidationError
    from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope
    raw = args.input.read_text()
    float_hit = find_json_float_loc(raw)
    if float_hit is not None:
        loc, input_str = float_hit
        envelope = make_decimal_type_envelope(loc, input_str)
        print(json.dumps(envelope), file=sys.stderr)
        return 2
    try:
        request = ARMRequest.model_validate_json(raw)
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2
    schedule = build_arm_schedule(request)
    print(schedule.model_dump_json(indent=2))
    return 0
```

**Apply to `scripts/stress_test.py`:** Replace `ARMRequest` → `StressRequest`, `build_arm_schedule` → `lib.stress.evaluate`. Add `--mode` arg as advisory hint (the discriminator is in JSON; argparse just helps users construct the right shape via examples in `--help`). The `--rates` and `--reductions` lists from ROADMAP SC-1 / SC-2 are SHORTCUTS that argparse parses into the `rates` / `reductions` JSON fields — pinned in Plan 08-04 LOCKED DECISIONS.

**Pattern 7: 6-key Pydantic error envelope on stderr (D-19 / WR-02 inheritance)**

Source: `scripts/_cli_helpers.py:67-106` (`make_decimal_type_envelope`). Phase 8 reuses AS-IS — no helper extension needed.

---

### `scripts/points_breakeven.py` (CLI — simplest analog)

**Primary analog:** `scripts/amortize.py` (single-engine, single-mode CLI shape).

Same lazy-import + JSON-float gate + 6-key envelope. Calls `lib.points.evaluate(req)` once. Stdout: pretty-printed `PointsResponse`.

---

### `tests/test_stress.py` + `tests/test_points.py` (test scaffolds — composite analog)

**Primary analogs:**
- `tests/test_arm.py:1-50` (Phase 5 module header + `SCRIPT_PATH` constant + `_request_from_fixture` helper)
- `tests/test_affordability.py` (6-key envelope test pattern + citation-coverage meta-test pattern)

**Pattern 8: 32-stub Nyquist xfail scaffold + strict=True**

Phase 8 needs 7 requirements × ~1-2 stubs + cross-cutting = **~13 xfail stubs in tests/test_stress.py + ~5 in tests/test_points.py**. Wave 0 (Plan 08-00) ships every stub; Waves 2-5 flip them.

**Pattern 9: Subprocess-only CLI invocation (D-17)**

Source: `tests/test_arm.py:34` — `SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "arm_simulate.py"`. Phase 8 mirrors with two `SCRIPT_PATH` constants (one per CLI).

---

### `tests/conftest.py` (extend with two new fixture loaders)

Source: own file lines 38-90 (`amortize_fixture`, `affordability_fixture`, `arm_fixture` — all near-identical shape).

```python
# Phase 8 appends to tests/conftest.py (after line 90 `arm_fixture`)
@pytest.fixture
def stress_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "stress" / f"{stem}.json"
        return json.loads(path.read_text())
    return _load

@pytest.fixture
def points_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "points" / f"{stem}.json"
        return json.loads(path.read_text())
    return _load
```

---

### `references/stress-tests.md` + `references/points-breakeven.md` (reference docs)

**Primary analog:** `references/arm-mechanics.md` (Phase 5 D-08 [REVISED]) — the only existing Markdown reference doc, sets the doctrine for `references/*.md` shape.

**Sections (mirroring arm-mechanics.md's structure):**
- Stress: Overview → Sweep modes (rate-shock / income-shock / arm-reset) → Output schema (top-table-summary contract for SC-5) → Citations (CFPB stress-test guidance / ATR-QM 1026.43(c)(5) for max-payment scenarios) → Subagent consumption hint (Phase 11 stress-test-agent)
- Points: Overview → Simple breakeven formula → NPV breakeven formula + discount-rate disclosure → Divergence example (the Plan 08-05 SC-4 fixture) → Citations (IRS Pub 936 §"Points" + Reg Z 1026.18 disclosure rules)

---

## Cross-Cutting Patterns Inherited (do not re-derive)

| Pattern | Source | Phase 8 use |
|---|---|---|
| Decimal money discipline (CENT, ROUND_HALF_UP, end-of-period only) | `lib/money.py` | All money fields in stress/points models |
| `quantize_rate` 6dp (Phase 5 D-14 promotion) | `lib/money.py:58-73` | Rate fields in StressRequest grids |
| `ConfigDict(strict=True, frozen=True, extra="forbid")` | every Phase 1+ Pydantic model | All Phase 8 models |
| 6-key Pydantic envelope on stderr | `scripts/_cli_helpers.py:67-106` | scripts/stress_test.py + scripts/points_breakeven.py |
| Lazy-import after argparse for fast --help | `scripts/arm_simulate.py:60-99` | both Phase 8 CLIs |
| Subprocess-only CLI test invocation | `tests/test_arm.py:34` | tests/test_stress.py + tests/test_points.py |
| One-fixture-per-file JSON shape | `tests/fixtures/arm/*.json` | tests/fixtures/stress/ + tests/fixtures/points/ |
| Hand-calc fixtures with citation comments | `tests/fixtures/golden_pmt.json` (Phase 1) | All Plan 08-05 fixtures |
| Nyquist xfail scaffold with strict=True | `tests/test_arm.py` (Phase 5 Wave 0) | tests/test_stress.py + tests/test_points.py (Wave 0) |
| Reference doc section structure | `references/arm-mechanics.md` (Phase 5 D-08) | references/stress-tests.md + references/points-breakeven.md |
| Composition over Phase 3/4/5 engines (no re-derivation) | `lib/affordability.py` (composes Phase 2+3) + `lib/arm.py` (composes Phase 3) | `lib/stress.py` composes Phase 3+4+5; `lib/points.py` composes Phase 3 (via savings derived from two amortize calls) |

---

## Notes for Planner

1. **Phase 8 is composition-only.** No new mathematical primitives. Every stress sweep is a loop over an existing engine. Plans 08-02 and 08-03 should be SHORT — most lines are Pydantic model definitions and three-line loop bodies.

2. **Discount-rate cross-phase coupling.** `lib.points.npv_breakeven` requires a discount rate. Phase 6 (Refinance NPV) will pin the project-wide borrower-perspective discount-rate convention. Phase 6 is not yet implemented. **Plan 08-03 LOCKED DECISIONS must document the deferred coupling**: Phase 8 ships a CALLER-SUPPLIED `discount_rate_annual: Rate` field on `PointsRequest` with a documented "Phase 6 will lock the project-wide default; Phase 8 has no default to force explicit choice (matches `max_dti` discipline from Phase 4 D-12)" comment. NO blocker on Phase 6 because Phase 8 punts the default to the caller. This is the single cross-phase coupling and 08-RESEARCH.md §"Discount-rate cross-phase coupling" must elaborate.

3. **SC-5 subagent-summarization output discipline is Phase 8's only genuinely-new design constraint.** Top-of-JSON scenario-summary table + < 100KB total. No existing Phase 1-5 output has this constraint (those are detail-only). 08-RESEARCH.md §"Output schema" sketches the schema; Plan 08-01 LOCKED DECISIONS pins the exact field order.

4. **No new dependencies.** Pure composition over `numpy_financial` (already in via Phase 3) + `pydantic` (already in via Phase 1) + `python-dateutil` (Phase 3) + Phase 3/4/5 lib modules.

5. **Reset-trigger formula reuse.** Plan 08-02 `arm_path` needs the same `_compute_reset_triggers` formula as `lib/arm.py:244-259`. Two options pinned in Plan 08-02 LOCKED DECISIONS:
   - (a) Import `lib.arm._compute_reset_triggers` (couples Phase 8 to a private helper).
   - (b) Re-derive inline from `arm_terms.initial_period_months + 1, +reset_period_months, ...`.
   Recommendation: (a) — promote `_compute_reset_triggers` from private to public in `lib/arm.py` via a single rename (mirrors Phase 5 D-14 `quantize_rate` promotion). Plan 08-02 ships this one-line public-API addition.
