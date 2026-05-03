# Phase 7: Estimated APR — Pattern Map

**Mapped:** 2026-05-02
**Phase:** 07-estimated-apr
**Files analyzed:** 10 (8 NEW + 2 MODIFIED) + 21 fixture files (1 Reg Z anchor + 20 FFIEC captures)
**Analogs found:** 10 / 10 (every NEW file has a strong existing analog from Phases 3 / 4 / 5)

## Summary

Phase 7 is a Newton-Raphson root-finder over a Reg Z Appendix J unit-period
equation, layered ON TOP OF the Phase 3 amortization engine (which is the
only "depends_on" in ROADMAP for Phase 7). The closest precedent for the
solver pattern is **Phase 4 `evaluate_reverse`** (`lib/affordability.py:952-1109`),
which performs a one-shot `npf.pv` solve seeded from a candidate value
and refined once. Phase 7 generalizes that pattern: **seed via `npf.rate(...)`
treating the loan as a regular transaction, then iterate Newton-Raphson on
the Reg Z Appendix J U-equation in Decimal arithmetic until convergence
within `Decimal("0.00001")`.**

Every new file maps to a near-1:1 analog:
- `lib/apr.py` ← `lib/arm.py` (composite engine + Pydantic boundary models) +
  `lib/affordability.py:evaluate_reverse` (npf seed + refine)
- `scripts/apr_reg_z.py` ← `scripts/affordability.py` (CLI shape + 6-key envelope
  + lazy-import + `_cli_helpers` reuse)
- `tests/test_apr.py` ← `tests/test_arm.py` (xfail-stub-then-flip + subprocess CLI)
- `tests/fixtures/apr/*.json` ← `tests/fixtures/affordability/*.json`
  (one-fixture-per-file)
- `tests/fixtures/apr/oracle/*.json` ← `tests/fixtures/arm/oracle/*` (capture-as-fixture
  pattern — Phase 5 D-04 inheritance; FFIEC stands in for Bankrate/Vertex42)
- `references/apr-reg-z.md` ← `references/arm-mechanics.md` (only existing
  `references/*.md` — same section structure: Citations → Conventions →
  Worked Example → Citation correction notes if any)

## File Classification

### NEW files (Phase 7 creates)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lib/apr.py` | calc-engine module + Pydantic models + Newton-Raphson solver | request-response (in-process) | `lib/arm.py` (engine + models) + `lib/affordability.py:evaluate_reverse` (numpy_financial seed + refine) | exact (composite) |
| `scripts/apr_reg_z.py` | CLI entrypoint | request-response (JSON-in/JSON-out subprocess) | `scripts/arm_simulate.py` | exact |
| `references/apr-reg-z.md` | reference doc | static doc | `references/arm-mechanics.md` (only existing analog) | exact (sole sibling) |
| `tests/test_apr.py` | unit + integration + meta tests (golden + structural + invariant + CLI subprocess + literal-text regex) | test | `tests/test_arm.py` (closest by surface area) + `tests/test_affordability.py` (closest by SC literal-coverage idiom) | exact (composite) |
| `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` | Reg Z anchor fixture | data-only | `tests/fixtures/golden_pmt.json` (Phase 1 oracle anchor pattern) | exact (anchor pattern) |
| `tests/fixtures/apr/*.json` (Reg Z + odd-first-period + finance-charge variants) | hand-calc fixture (one-per-file) | data-only | `tests/fixtures/affordability/*.json` | exact |
| `tests/fixtures/apr/oracle/ffiec_*.json` (20 captures) | oracle-capture fixture pair (FFIEC tool screen + JSON transcription) | data-only + transcription | `tests/fixtures/arm/oracle/*` (Phase 5 D-04 capture-as-fixture pattern) | exact (FFIEC subs for Bankrate/Vertex42) |
| `tests/fixtures/apr/oracle/.gitkeep` | committed empty placeholder | static | `tests/fixtures/arm/oracle/.gitkeep` | exact |

### MODIFIED files (Phase 7 touches existing)

| Modified File | Modification | Closest Analog Pattern |
|---|---|---|
| `tests/conftest.py` | extend with `apr_fixture` factory (mirrors `arm_fixture` lines 73-90) | own file lines 55-70 (`affordability_fixture`) and 73-90 (`arm_fixture`) |
| `lib/rules/reg_z.py` | NO MODIFICATION — Phase 7 IMPORTS `within_apr_tolerance` + `TOLERANCE_REGULAR` + `TOLERANCE_IRREGULAR` (already shipped Phase 2). Listed here because the predicate's docstring already references "Phase-7 consumer" (line 43). | n/a (read-only consumer) |

---

## Pattern Assignments (NEW files → closest existing analog)

### `lib/apr.py` — composite analog (engine + models + solver)

**Primary analogs:**
- `lib/arm.py` (`lib/arm.py:1-489`) — Pydantic v2 strict+frozen+forbid model
  cluster (`ARMTerms`, `ARMRequest`, `ARMPayment`, `ResetEvent`, `ARMSchedule`,
  `IndexPathEntry`) + cross-field `model_validator(mode="after")` + per-period
  iteration with cumulative-totals carry. Phase 7 mirrors the model cluster:
  `APRRequest`, `AdvanceScheduleEntry`, `PaymentScheduleEntry`, `APRResponse`.
- `lib/affordability.py:evaluate_reverse` (`lib/affordability.py:952-1109`) —
  THIS IS THE CLOSEST PRECEDENT FOR THE SOLVER. The reverse evaluator does
  a **seed-then-refine** numpy-financial solve (zero-MI seed → MI estimate →
  final solve). Phase 7 generalizes to Newton-Raphson but inherits:
  - Seed from `numpy_financial` (`npf.pv` there → `npf.rate` here)
  - Decimal arithmetic throughout with `quantize_cents` end-of-period
  - `quantize_rate` from `lib.money` for the final APR result
  - `warnings.catch_warnings(record=True)` to capture stale-reference warnings
- `lib/amortize.py:_build_fixed_monthly` (`lib/amortize.py:295-383`) —
  per-period iteration shape, scalar Decimal arithmetic, level-payment
  `numpy-financial` invocation pattern.

**Pattern 1: numpy-financial seed pattern (`evaluate_reverse` reference at line 1045)**

```python
# lib/affordability.py:1045-1051 — closest analog for the npf.rate seed
zero_mi_pv = npf.pv(
    rate=monthly_rate,
    nper=request.term_months,
    pmt=-max_pi_plus_mi,
    fv=0,
)
zero_mi_loan_amount = quantize_cents(zero_mi_pv)
```

**Apply to `lib/apr.py`:** seed Newton-Raphson with `npf.rate(...)` against a
**regular-transaction approximation** (treat the irregular loan as if
each advance were a single net principal at t=0 and each payment were
identical). The seed is float; cast through `Decimal(str(seed))` before
entering the Newton iteration. Per `lib/amortize.py:124-135` numpy-financial
bug-avoidance docstring: bug #131 (architecture-dependent IRR) is irrelevant
to `npf.rate`, but the seed must be sanity-checked (clamp to `[0, 1]` and
fall back to the disclosed nominal-rate guess if `npf.rate` returns `nan`
or infinity).

**Pattern 2: Pydantic v2 strict+frozen+forbid + cross-field model_validator**

Source: `lib/amortize.py:175-223` (`AmortizeRequest`).

```python
class AmortizeRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    frequency: Literal["monthly", "biweekly"] = "monthly"
    ...
    @model_validator(mode="after")
    def _no_duplicate_recurring_periods(self) -> AmortizeRequest:
        ...
```

**Apply to `lib/apr.py`:** every model uses `ConfigDict(strict=True,
frozen=True, extra="forbid")`. The cross-field validator needed in Phase 7
is `APRRequest._payment_schedule_sums_match_loan` (every payment-schedule
amount × periods reconciles to a positive total), and
`APRRequest._advance_schedule_first_advance_at_t0` (the first advance must
have `unit_period_offset = 0`).

**Pattern 3: Decimal-context iteration with `quantize_rate` at result**

Source: `lib/money.py:58-73` (`quantize_rate`) + `lib/affordability.py:1096`
(quantize once at end).

```python
# lib/money.py:58-73
def quantize_rate(rate: Decimal) -> Decimal:
    """Quantize a fractional rate to 6 decimal places using ROUND_HALF_UP."""
    with localcontext(MONEY_CONTEXT):
        return rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)
```

**Apply to `lib/apr.py`:** Newton iterations run in `with localcontext(MONEY_CONTEXT)`
(prec=28 inherited). Iterate `i_{n+1} = i_n - f(i_n) / f'(i_n)` in Decimal
throughout. After convergence, call `quantize_rate(estimated_apr)`. **NEVER
mix float into the Decimal iteration** — this is the load-bearing rule for
the `Decimal("0.00001")` tolerance (see PHASE-WIDE-CONSTRAINT below).

**Pattern 4: Convergence with hard iteration cap**

NO direct codebase analog (Phase 7 is the project's first iterative solver).
RESEARCH §"Newton-Raphson convergence" specifies the algorithm. The hard
cap of 50 iterations comes from ROADMAP SC-3.

**Pattern 5: warnings.catch_warnings idiom**

Source: `lib/affordability.py:1033-1035` (`evaluate_reverse` warning capture).

```python
captured_warnings: list[str] = []
with warnings.catch_warnings(record=True) as captured:
    warnings.simplefilter("always", StaleReferenceWarning)
    ...
```

**Apply to `lib/apr.py`:** if a future phase wires the APR solver into a
predicate-bearing pipeline (Phase 8 stress, Phase 12 eval), the same
warning-capture pattern propagates StaleReferenceWarning surfaces. Phase 7
itself does NOT call any `lib/rules/*` predicate (Reg Z Appendix J is pure
math; the only Phase 2 cross-reference is `lib/rules/reg_z.py:within_apr_tolerance`
which is a pure function with no YAML).

---

### `scripts/apr_reg_z.py` — exact analog of `scripts/arm_simulate.py`

**Analog:** `scripts/arm_simulate.py` (lines 1-103, see read above).

Same skeleton, same shape: argparse + `--input <path>` only, sys.path
injection AFTER --help, lazy-import block, `find_json_float_loc` +
`make_decimal_type_envelope` from `scripts/_cli_helpers.py` (factored Phase 5),
Pydantic ValidationError → `e.json()` on stderr, happy path
`response.model_dump_json(indent=2)` on stdout.

**Two notable adaptations:**

1. The CLI's `--help` epilog MUST cite `references/apr-reg-z.md` per
   ROADMAP SC-5 (Phase 5 D-08 set the precedent: `arm_simulate.py` does NOT
   currently cite `references/arm-mechanics.md` in --help; Phase 7 adds the
   citation idiom). RESEARCH §"references citation in --help" specifies the
   exact placement (last paragraph of epilog).

2. The output JSON schema MUST contain `"estimated_apr"` and any
   user-facing summary string MUST contain the literal "estimated APR"
   (ROADMAP SC-4). The simplest enforcement: every string field in
   `APRResponse` that includes the APR value uses the f-string template
   `f"estimated APR: {value}%"` (compile-time guarantee). Pinned by a
   regex test in `tests/test_apr.py`.

---

### `tests/test_apr.py` — composite analog (test_arm.py + test_affordability.py)

**Primary analog:** `tests/test_arm.py` (Wave 0 stub-then-flip pattern,
see `tests/test_arm.py` excerpt in `05-00-test-infrastructure-PLAN.md`
above).

**Secondary analog:** `tests/test_affordability.py` (literal-text regex
test pattern for AFFD-07 `blocked_by` citation surface — closest analog
for ROADMAP SC-4 "estimated APR" literal enforcement).

**Test inventory** (Wave 0 ships 8 xfail stubs; subsequent waves flip them):

```
APR-01 (1 stub): test_apr_solver_module_exists_with_newton_raphson_signature
APR-02 (1 stub): test_apr_solver_seeded_from_npf_rate
APR-03 (1 stub): test_apr_solver_converges_within_decimal_00001_tolerance
APR-04 (1 stub): test_apr_ffiec_oracle_fixtures_match_within_decimal_00001
APR-05 (1 stub): test_apr_reg_z_appendix_j_worked_example_returns_12_percent
APR-06 (1 stub): test_apr_response_uses_literal_estimated_apr_text
APR-07 (1 stub): test_apr_cli_subprocess_round_trip
APR-08 (1 stub): test_references_apr_reg_z_doc_present_with_required_sections

Cross-cutting (5 stubs):
- test_newton_raphson_iterations_under_50_for_all_fixtures (SC-3)
- test_apr_cli_help_does_not_import_lib_apr (D-18 inheritance)
- test_apr_cli_rejects_float_loan_amount (D-19 / WR-02 inheritance)
- test_apr_cli_error_envelope_uniformity (WR-02 inheritance)
- test_apr_solver_raises_on_non_convergence (Phase 7 ConvergenceError contract)

TOTAL Wave 0: 13 xfail stubs.
```

Lifted shape from `tests/test_arm.py:1-300` (xfail-decorator-with-strict=True +
SCRIPT_PATH constant + module docstring listing wave-by-wave flip plan).

---

### `tests/fixtures/apr/*.json` — exact analog of `tests/fixtures/affordability/*.json`

**Analog:** one-fixture-per-file JSON, named by scenario. Phase 5 idiom
(`tests/fixtures/arm/arm_5_1_payment_jump_at_61.json`) extended.

**Wave 5 fixture inventory (≥21 files, one Reg Z anchor + ≥20 FFIEC):**

```
Hand-calc anchor (Wave 5 ships immediately):
- regz_appendix_j_5000_36_166_07.json (the SC-1 anchor: $5000 / 36 mo / $166.07 → 12.00%)

Hand-calc variants (Wave 5 ships, derived from Reg Z Appendix J §J(c)(1) examples):
- regz_appendix_j_odd_first_period_15_days.json (Example J-1: 15-day first period)
- regz_appendix_j_odd_first_period_45_days.json (variant)
- regz_appendix_j_unit_period_monthly_regular.json (no odd period — sanity)

FFIEC oracle captures (Wave 7 ships — human checkpoint):
- oracle/ffiec_001_30yr_400k_6_5.json
- oracle/ffiec_002_30yr_200k_7_0.json
- ... (≥18 more, varying amount/term/advance schedule)
- oracle/ffiec_020_15yr_300k_5_5.json
```

Each FFIEC capture contains:
```json
{
  "request": { ... APRRequest JSON ... },
  "expected": {
    "estimated_apr": "0.071234",
    "ffiec_screenshot_sha256": "<hash of captured PDF/PNG>",
    "captured_at": "2026-05-02",
    "ffiec_tool_url": "https://www.ffiec.gov/aprwin.htm"
  }
}
```

(See Plan 07-07 for the full capture protocol + Wave-N human checkpoint
mirroring Phase 5 Plan 05-06.)

---

### `references/apr-reg-z.md` — analog of `references/arm-mechanics.md`

**Analog:** `references/arm-mechanics.md` (the only existing `references/*.md`).

Same six-section template (per Phase 5 D-08 + ARM-09 contract):
1. **Title + cite-from contract** — "Cited from `lib.apr.APRRequest.__doc__`
   per ROADMAP SC-5"
2. **Unit-period model** (Reg Z Appendix J §(b)(1)–(b)(5))
3. **Day-count conventions** (12 CFR §1026.17(c)(4) odd first period;
   §1026.4 finance-charge enumeration)
4. **Worked example** (Reg Z Appendix J Example J-1 — $5,000 / 36 ×
   $166.07 → 12.00%)
5. **Newton-Raphson convergence** (algorithm + seed + iteration cap;
   cite numpy-financial issue #131 as background)
6. **Citation correction notes** (any drift between CONTEXT decisions and
   live regulatory text — mirrors ARM-mechanics.md "Citation correction
   note (2026-04-30)")

`references/arm-mechanics.md` is also the source of the **citation-from-docstring**
pattern: `ARMTerms.__doc__` cites `references/arm-mechanics.md`. Phase 7
extends: `lib.apr.APRRequest.__doc__` cites `references/apr-reg-z.md`.

---

## MODIFIED files (Phase 7 touches existing)

### `tests/conftest.py` — extend with `apr_fixture`

**Pattern:** identical to `arm_fixture` (lines 73-90):

```python
@pytest.fixture
def apr_fixture() -> Callable[[str], dict[str, Any]]:
    """Loads APR fixtures by filename stem from tests/fixtures/apr/.
    Mirrors arm_fixture; oracle pairs at tests/fixtures/apr/oracle/<stem>.
    """
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "apr" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    return _load
```

### `lib/rules/reg_z.py` — NO modification

The predicate (lines 1-89, see read above) already docstrings:

> "Phase-7 consumer note (RESEARCH.md line 898): Phase 7 (Estimated APR)
> imports this predicate to verify the estimated APR is within Reg Z
> tolerance of the lender's disclosed APR."

Phase 7 reads `TOLERANCE_REGULAR = Decimal("0.00125")` (1/8 pp) and
`TOLERANCE_IRREGULAR = Decimal("0.0025")` (1/4 pp) from this module.
**CRITICAL CORRECTION TO ORCHESTRATOR PROMPT:** the orchestrator prompt
states "Reg Z 1/8 percentage point regular = 0.0125%" — this is wrong.
1/8 of a percentage point = 0.125% = `Decimal("0.00125")` fractional (per
`reg_z.py:62`). So `Decimal("0.00001")` is **125x tighter** than Reg Z's
regular-transaction tolerance, NOT 100x. RESEARCH.md flags this and the
plan reconciles it.

---

## Phase-wide constraints (inherited; reaffirmed for Phase 7)

| Constraint | Source | Phase 7 Application |
|---|---|---|
| Decimal money discipline (CENT, MONEY_CONTEXT) | `lib/money.py` (FND-01) | All money/rate values constructed from JSON strings; never mix float in Decimal arithmetic |
| `quantize_cents` end-of-period only | `lib/money.py:39-46` | NEVER called inside the Newton iteration; only on finance_charge totals |
| `quantize_rate` at 6dp at result | `lib/money.py:58-73` (Phase 5 D-14) | Called ONCE on the converged APR before returning to the caller |
| Pydantic v2 `strict=True, frozen=True, extra="forbid"` | Phase 1 D-08 (CLAUDE.md) | All `lib/apr.py` models |
| 6-key Pydantic envelope on stderr | Phase 3 WR-02 + Phase 4 D-13 | `scripts/apr_reg_z.py` JSON-float gate + ValidationError surfaces |
| Lazy-import D-18 (--help fast) | Phase 3 D-18 | `scripts/apr_reg_z.py` imports `lib.apr` + `numpy_financial` AFTER argparse |
| Subprocess-only CLI tests | Phase 3 D-17 | `tests/test_apr.py` uses `SCRIPT_PATH` + `subprocess.run`; never `from scripts.apr_reg_z import main` |
| `scripts._cli_helpers` reuse | Phase 5 Plan 05-04a | Phase 7 imports both `find_json_float_loc` + `make_decimal_type_envelope` byte-identically |

## Watch out for (load-bearing pitfalls; planner MUST honor verbatim)

1. **`numpy_financial.rate` returns float; never mix into Decimal arithmetic.**
   The seed must be `Decimal(str(npf.rate(...)))` and the Newton iteration
   must stay pure Decimal. RESEARCH §"Decimal vs float" specifies why
   `np.float64` precision (~1e-16) is insufficient for `Decimal("0.00001")`
   tolerance — the relative precision is borderline at that level and
   accumulating Decimal-equation evaluations in float would compound.

2. **Reg Z tolerance is `Decimal("0.00125")` fractional (1/8 pp), not `0.0125`.**
   The orchestrator prompt has the decimal point off. `Decimal("0.00001")` is
   125x tighter than Reg Z regular tolerance (per `reg_z.py:62`).

3. **`numpy_financial.rate` may return `nan` for ill-conditioned inputs.**
   The seed function MUST sanity-check the result and fall back to the
   nominal-rate-from-disclosure (`Decimal("12") * pmt / loan_amount` or
   similar) if `npf.rate` is `nan` or out of `[0, 1]`. Pinned by
   `test_apr_solver_seeded_from_npf_rate` (the fallback path is exercised
   by an irregular-fixture test).

4. **Reg Z Appendix J Example J-1 ($5000 / 36 / $166.07) is the SC-1 anchor;
   any deviation in the engine that breaks this fixture is a release blocker.**
   Wave 5 ships this fixture FIRST and only then enables Newton iteration.

5. **The "estimated APR" literal-text rule (SC-4) requires REGEX enforcement
   on the JSON output schema.** The simplest implementation: `APRResponse`
   has a `summary: str` field and a `@model_validator(mode="after")` that
   asserts `"estimated APR" in self.summary`. Pinned by
   `test_apr_response_uses_literal_estimated_apr_text`.

6. **FFIEC fixture capture is a Wave 7 human checkpoint.** Mirror Phase 5
   Plan 05-06 (oracle PDF captures) — flag for `/gsd-discuss-phase` if
   the FFIEC tool URL (`https://www.ffiec.gov/aprwin.htm` per RESEARCH) is
   unreachable. Fallback documented in Plan 07-07.

7. **`scripts/_cli_helpers.py` is not a Python package.** Phase 5 D-discretion
   factor-extract: `scripts/` has no `__init__.py`; consumers do
   `sys.path.insert(0, project_root)` then `from scripts._cli_helpers import ...`
   AFTER argparse. See `scripts/affordability.py:140-164` for the canonical
   import block.

8. **Phase 7 has no Phase 2 predicate dependency BEYOND `reg_z.py:within_apr_tolerance`.**
   Unlike Phase 4 (which threads through 6 predicates), Phase 7 is pure math.
   The CLI does NOT need to handle `MissingCountyDataError` or any
   `lib.rules` exception. The only `lib.rules` import is the optional
   tolerance check (caller may pass `disclosed_apr` for a within-tolerance
   advisory in `APRResponse.tolerance_check`).

## Cross-wave dependency notes (for the planner)

```
Wave 0 (test infrastructure)
  └─→ Wave 1 (Pydantic models)             [closes: APR-01 partial]
        └─→ Wave 2 (Newton-Raphson engine)  [closes: APR-01 + APR-02 + APR-03]
              ├─→ Wave 3 (odd-first-period + day-count helpers)
              │     └─→ Wave 4 (CLI)        [closes: APR-06 + APR-07]
              │           └─→ Wave 5 (tests + Reg Z anchor fixture) [closes: APR-05]
              │                 ├─→ Wave 6 (references/apr-reg-z.md) [closes: APR-08]
              │                 └─→ Wave 7 (FFIEC fixture capture)   [closes: APR-04]
              └─ (Wave 3 can technically run parallel with Wave 2 once models exist;
                  project config = parallelization=false → sequential)
```

Each wave's Plan.md has explicit `depends_on:` frontmatter naming the
upstream plan(s).
