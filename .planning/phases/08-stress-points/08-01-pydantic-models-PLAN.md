---
phase: 08
plan: 01
type: execute
wave: 1
depends_on: ["08-00"]
files_modified:
  - lib/stress.py
  - lib/points.py
autonomous: true
requirements: []
tags:
  - phase-08
  - stress-points
  - pydantic-models
must_haves:
  truths:
    - "lib/stress.py defines StressRequest as a Pydantic v2 discriminated union by field 'mode' over RateShockRequest | IncomeShockRequest | ArmResetRequest"
    - "lib/stress.py defines StressResponse with 'summary' field declared BEFORE 'rows' field (SC-5 field-order contract)"
    - "lib/points.py defines PointsRequest with mode discriminator from_savings | from_loans, and PointsResponse with simple_breakeven_months + npv_breakeven_months + diverge + decision fields"
    - "All Pydantic models use ConfigDict(strict=True, frozen=True, extra='forbid')"
    - "Public engine functions exist as cross-plan stubs (lib.stress.evaluate, lib.points.evaluate) raising NotImplementedError — Plans 08-02 and 08-03 fill bodies"
    - "STRS-04 model contract test (test_stress_request_discriminated_union_by_mode) flips xfail → pass"
    - "SC-5 summary-before-rows test (test_sc5_summary_table_appears_before_rows_in_json) flips xfail → pass"
  artifacts:
    - path: "lib/stress.py"
      provides: "Pydantic models + cross-plan stub for evaluate()"
      min_lines: 250
    - path: "lib/points.py"
      provides: "Pydantic models + cross-plan stub for evaluate()"
      min_lines: 120
---

<objective>
Ship the Pydantic v2 type contract for both Phase 8 engines. Discriminated unions for stress (3 modes) and points (2 modes), response models with the SC-5 field-order contract baked in (`summary` declared before `rows` in StressResponse), and cross-plan stubs for `evaluate()` so Plans 08-02 / 08-03 can fill bodies without re-importing the surface.

This plan ships ZERO algorithm code. Engine bodies stub-raise `NotImplementedError` per Phase 4 D-08 cross-plan stub idiom (lib.affordability.py Wave 1 → Wave 2 pattern).
</objective>

<context>
@.planning/phases/08-stress-points/08-PATTERNS.md
@.planning/phases/08-stress-points/08-RESEARCH.md
@lib/affordability.py (read 1-540 for discriminated-union shape, _CommonRequestFields, model_validator pattern)
@lib/arm.py (ARMTerms + ARMRequest + IndexPathEntry — Phase 8 reuses ARMRequest in ArmResetRequest)
@lib/amortize.py (Loan + ExtraPrincipalEntry; Phase 8 reuses Loan in RateShockRequest)
@lib/money.py (CENT, MONEY_CONTEXT, quantize_cents, quantize_rate; reuse, do not redefine)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create lib/stress.py with discriminated-union models + cross-plan evaluate stub</name>
  <files>lib/stress.py</files>
  <action>
    Create lib/stress.py from scratch with this skeleton:

    ```python
    """Stress-test engine for Phase 8 (STRS-01..04 + ROADMAP SC-1/2/3/5).

    Composition over Phase 3 (lib.amortize.build_schedule), Phase 4
    (lib.affordability.evaluate), and Phase 5 (lib.arm.build_arm_schedule).
    Phase 8 invents NO new mathematical primitive; every stress sweep is a
    loop over an existing engine.

    Wave 1 (this plan, 08-01) ships ONLY the Pydantic v2 type contract +
    documented stubs for evaluate(). Wave 2 (Plan 08-02) adds the body to
    evaluate() and ships rate_shock(), income_shock(), arm_path() helpers.

    LOCKED DECISION - D-01 (mode discriminator):
      StressRequest is a Pydantic v2 discriminated union via Field(discriminator='mode')
      over three subclasses: RateShockRequest (mode='rate-shock'), IncomeShockRequest
      (mode='income-shock'), ArmResetRequest (mode='arm-reset'). Mirrors Phase 4
      AffordabilityRequest pattern.

    LOCKED DECISION - D-02 (SC-5 field order: summary BEFORE rows):
      StressResponse declares `summary: ScenarioSummary` BEFORE `rows: list[StressRow]`.
      Pydantic v2 preserves field-declaration order in model_dump_json. Subagent reads
      first ~30 lines and gets the summary table. ROADMAP SC-5 verbatim closure.

    LOCKED DECISION - D-03 (per-row schedule_summary scalars only; no full schedules):
      StressRow carries SUMMARY SCALARS (monthly_pi, total_interest, dti_back, etc.) —
      NEVER full Schedule.payments[] arrays. 50-rate sweep × 360 rows × 200 bytes per
      row would be 3.6MB, blowing the 100KB SC-5 budget by 36×. Rule pinned in 08-RESEARCH §1.3.

    LOCKED DECISION - D-04 (caller-supplied threshold; no module default):
      IncomeShockRequest.dti_threshold is REQUIRED (Rate). No module-level default;
      the CLI exposes 0.43 as a documented default in --help epilog only. Matches
      Phase 4 D-12 max_dti discipline.

    LOCKED DECISION - D-05 (RatePath name closed-set):
      RatePath.name is Literal["parallel-shift", "gradual-rise", "fall-then-rise"].
      Closed set per ROADMAP SC-3 verbatim. v2 may extend; v1 is closed.

    LOCKED DECISION - D-06 (ScenarioSummary stress_invariant_violations is
    fail-loud-via-list, not a raise):
      ScenarioSummary.stress_invariant_violations: list[str] = []. Engine appends
      a citation when an invariant is violated (e.g., "RATE_SHOCK_MONOTONE_PI" if
      monthly_pi went down as rate went up). Empty list is the happy path.
    """

    from __future__ import annotations

    from decimal import Decimal
    from typing import Annotated, Literal

    from pydantic import BaseModel, ConfigDict, Field

    from lib.affordability import AffordabilityRequest
    from lib.arm import ARMRequest
    from lib.models import Loan, Money, Rate


    # ---------------------------------------------------------------------------
    # Leaf models
    # ---------------------------------------------------------------------------

    class RatePath(BaseModel):
        """One named rate-path scenario for ARM-reset sweeps (D-05).

        params shape varies by name:
          parallel-shift: {"shift_bps": int}
          gradual-rise:   {"step_bps": int}
          fall-then-rise: {"drop_bps": int, "rise_bps": int}
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        name: Literal["parallel-shift", "gradual-rise", "fall-then-rise"]
        params: dict[str, int]


    class StressRow(BaseModel):
        """One scenario row in StressResponse.rows. Summary scalars only (D-03)."""

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        label: str
        # Mode-specific scalars (only the ones relevant for the row's mode are non-None)
        monthly_pi: Money | None = None         # rate-shock
        total_interest: Money | None = None     # rate-shock + arm-reset
        delta_vs_baseline_monthly: Money | None = None  # rate-shock
        delta_vs_baseline_pct: Rate | None = None       # rate-shock
        dti_back: Rate | None = None            # income-shock
        breaches_threshold: bool | None = None  # income-shock
        blocked_by: str | None = None           # income-shock
        max_payment: Money | None = None        # arm-reset
        reset_count: int | None = None          # arm-reset
        highest_rate: Rate | None = None        # arm-reset


    class ScenarioSummary(BaseModel):
        """The top-of-JSON table for SC-5 subagent consumption."""

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        table: list[StressRow]
        baseline_label: str | None = None
        worst_case_label: str | None = None
        stress_invariant_violations: list[str] = Field(default_factory=list)


    # ---------------------------------------------------------------------------
    # Request union (D-01)
    # ---------------------------------------------------------------------------

    class _CommonStressFields(BaseModel):
        """Shared base; do NOT instantiate directly (no mode field here)."""

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        scenario_label: str | None = None  # optional human-readable run tag


    class RateShockRequest(_CommonStressFields):
        """STRS-01 + ROADMAP SC-1: re-solve PMT for a grid of rates."""

        mode: Literal["rate-shock"] = "rate-shock"
        loan: Loan
        rates: list[Rate] = Field(min_length=1)
        baseline_label: str | None = None  # if None, defaults to str(rates[0])


    class IncomeShockRequest(_CommonStressFields):
        """STRS-02 + ROADMAP SC-2: recompute back-end DTI for a grid of income reductions."""

        mode: Literal["income-shock"] = "income-shock"
        base_request: AffordabilityRequest
        reductions: list[Rate] = Field(min_length=1)
        dti_threshold: Rate  # D-04: REQUIRED; no module default


    class ArmResetRequest(_CommonStressFields):
        """STRS-03 + ROADMAP SC-3: simulate index-path scenarios for an ARM."""

        mode: Literal["arm-reset"] = "arm-reset"
        base_arm_request: ARMRequest
        paths: list[RatePath] = Field(min_length=1)


    StressRequest = Annotated[
        RateShockRequest | IncomeShockRequest | ArmResetRequest,
        Field(discriminator="mode"),
    ]


    # ---------------------------------------------------------------------------
    # Response (D-02 field order: summary BEFORE rows)
    # ---------------------------------------------------------------------------

    class StressResponse(BaseModel):
        """Top-level response. Field declaration order pinned for SC-5: summary first."""

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        mode: Literal["rate-shock", "income-shock", "arm-reset"]
        scenario_count: int = Field(ge=0)
        summary: ScenarioSummary  # D-02: BEFORE rows
        rows: list[StressRow]


    # ---------------------------------------------------------------------------
    # Engine — cross-plan stub (Plan 08-02 fills body)
    # ---------------------------------------------------------------------------

    def evaluate(req: StressRequest) -> StressResponse:  # type: ignore[empty-body]
        """Dispatch on req.mode and run the matching sweep. Plan 08-02 body."""
        raise NotImplementedError("lib.stress.evaluate body lives in Plan 08-02")
    ```
  </action>
  <acceptance_criteria>
    - File lib/stress.py exists with at least 250 lines
    - `grep -c 'class RateShockRequest' lib/stress.py` returns 1
    - `grep -c 'class IncomeShockRequest' lib/stress.py` returns 1
    - `grep -c 'class ArmResetRequest' lib/stress.py` returns 1
    - `grep -c 'StressRequest = Annotated' lib/stress.py` returns 1
    - `grep -c 'discriminator="mode"' lib/stress.py` returns 1
    - `grep -c 'class StressResponse' lib/stress.py` returns 1
    - In lib/stress.py, `summary: ScenarioSummary` line number < `rows: list[StressRow]` line number (verified by `grep -n` ordering)
    - `python -c "from lib.stress import StressRequest, StressResponse, RateShockRequest, IncomeShockRequest, ArmResetRequest, RatePath, StressRow, ScenarioSummary, evaluate; print('OK')"` exits 0
    - mypy --strict lib/stress.py exits 0
    - ruff check + format clean on lib/stress.py
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Create lib/points.py with discriminated-union request + response models + cross-plan stub</name>
  <files>lib/points.py</files>
  <action>
    Create lib/points.py:

    ```python
    """Discount-points breakeven engine for Phase 8 (PNTS-01..03 + ROADMAP SC-4).

    Two modes:
      from_savings — caller already computed monthly_savings (single Decimal in)
      from_loans   — caller supplies two Loans (with-points + without-points);
                     engine derives monthly_savings via two build_schedule calls.

    Wave 1 ships only the type contract + cross-plan stub. Wave 3 (Plan 08-03)
    ships simple_breakeven, npv_breakeven, and the body of evaluate().

    LOCKED DECISION - D-01 (mode discriminator):
      PointsRequest is a Pydantic v2 discriminated union over PointsRequestFromSavings
      (mode='from_savings') and PointsRequestFromLoans (mode='from_loans').

    LOCKED DECISION - D-02 (caller-supplied discount_rate; no module default):
      PointsRequest.discount_rate_annual is REQUIRED (Rate). Phase 6 will pin the
      project-wide borrower-perspective default; Phase 8 punts to caller. Single-
      line additive non-breaking change when Phase 6 lands. Documented in
      references/points-breakeven.md (Plan 08-06). Matches Phase 4 D-12 max_dti
      discipline. Cross-phase coupling note pinned in 08-RESEARCH §5.5.

    LOCKED DECISION - D-03 (None for never-breakeven):
      Both simple_breakeven_months and npv_breakeven_months are int | None. None
      means "never crosses zero within hold_period_months". negative-savings
      scenarios (rate-up; PNTS-01 edge case) return None for both with a warning
      in PointsResponse.warnings.

    LOCKED DECISION - D-04 (decision dispatcher reports BOTH outputs):
      ROADMAP SC-4 verbatim: "reports breakeven months as points_cost / monthly_savings
      AND a parallel NPV-based decision". PointsResponse always carries both
      simple_breakeven_months AND npv_breakeven_months side-by-side; diverge=True
      iff they're not equal (and both non-None). decision = "buy_points" iff
      cum_npv(hold_period_months) >= 0; "skip_points" otherwise.
    """

    from __future__ import annotations

    from decimal import Decimal
    from typing import Annotated, Literal

    from pydantic import BaseModel, ConfigDict, Field

    from lib.models import Loan, Money, Rate


    class PointsRequestFromSavings(BaseModel):
        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        mode: Literal["from_savings"] = "from_savings"
        points_cost: Money = Field(strict=True, gt=Decimal("0"))
        monthly_savings: Money  # may be negative for rate-up scenarios; engine warns
        hold_period_months: int = Field(ge=1, le=600)
        discount_rate_annual: Rate  # D-02: REQUIRED


    class PointsRequestFromLoans(BaseModel):
        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        mode: Literal["from_loans"] = "from_loans"
        points_cost: Money = Field(strict=True, gt=Decimal("0"))
        loan_with_points: Loan
        loan_without_points: Loan
        hold_period_months: int = Field(ge=1, le=600)
        discount_rate_annual: Rate  # D-02: REQUIRED


    PointsRequest = Annotated[
        PointsRequestFromSavings | PointsRequestFromLoans,
        Field(discriminator="mode"),
    ]


    class PointsResponse(BaseModel):
        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
        simple_breakeven_months: int | None  # D-03: None = never
        npv_breakeven_months: int | None     # D-03: None = never (within hold)
        diverge: bool
        diverge_explanation: str | None = None
        decision: Literal["buy_points", "skip_points"]
        discount_rate_used: Rate
        hold_period_months: int
        monthly_savings: Money  # echoed; useful when caller used from_loans
        cumulative_npv_at_hold: Money  # cum_npv(hold_period_months); decision driver
        warnings: list[str] = Field(default_factory=list)


    def evaluate(req: PointsRequest) -> PointsResponse:  # type: ignore[empty-body]
        """Dispatch on req.mode and run the matching breakeven analysis. Plan 08-03 body."""
        raise NotImplementedError("lib.points.evaluate body lives in Plan 08-03")
    ```
  </action>
  <acceptance_criteria>
    - File lib/points.py exists with at least 120 lines
    - `grep -c 'class PointsRequestFromSavings' lib/points.py` returns 1
    - `grep -c 'class PointsRequestFromLoans' lib/points.py` returns 1
    - `grep -c 'PointsRequest = Annotated' lib/points.py` returns 1
    - `grep -c 'discriminator="mode"' lib/points.py` returns 1
    - `grep -c 'class PointsResponse' lib/points.py` returns 1
    - `python -c "from lib.points import PointsRequest, PointsResponse, PointsRequestFromSavings, PointsRequestFromLoans, evaluate; print('OK')"` exits 0
    - mypy --strict lib/points.py exits 0
    - ruff check + format clean on lib/points.py
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Flip 2 Wave 0 xfails (model contract + summary-before-rows)</name>
  <files>tests/test_stress.py</files>
  <action>
    Replace the xfail bodies for these two tests with real assertions, AND remove their `@pytest.mark.xfail(strict=True, ...)` decorators (D-00-02 contract):

    1. `test_stress_request_discriminated_union_by_mode`:
    ```python
    def test_stress_request_discriminated_union_by_mode() -> None:
        from decimal import Decimal
        from datetime import date
        from pydantic import TypeAdapter, ValidationError
        from lib.stress import StressRequest, RateShockRequest, IncomeShockRequest, ArmResetRequest
        from lib.models import Loan
        adapter = TypeAdapter(StressRequest)
        loan = Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.065000"),
                    term_months=360, origination_date=date(2026, 1, 1), loan_type="conventional")
        rs = adapter.validate_python({"mode": "rate-shock", "loan": loan.model_dump(mode="json"),
                                      "rates": ["0.06"]})
        assert isinstance(rs, RateShockRequest)
        with pytest.raises(ValidationError):
            adapter.validate_python({"mode": "bogus-mode", "loan": loan.model_dump(mode="json"),
                                     "rates": ["0.06"]})
    ```

    2. `test_sc5_summary_table_appears_before_rows_in_json`:
    ```python
    def test_sc5_summary_table_appears_before_rows_in_json() -> None:
        from lib.stress import StressResponse, ScenarioSummary
        resp = StressResponse(mode="rate-shock", scenario_count=0,
                              summary=ScenarioSummary(table=[]), rows=[])
        out = resp.model_dump_json()
        keys = list(__import__("json").loads(out).keys())
        assert keys.index("summary") < keys.index("rows"), \
            f"SC-5 violation: summary must appear before rows; got order {keys}"
    ```
  </action>
  <acceptance_criteria>
    - `grep -c '@pytest.mark.xfail' tests/test_stress.py` returns 11 (was 13; 2 flipped)
    - `pytest tests/test_stress.py::test_stress_request_discriminated_union_by_mode -v` exits 0 (passes)
    - `pytest tests/test_stress.py::test_sc5_summary_table_appears_before_rows_in_json -v` exits 0 (passes)
    - Full suite: ≥413 passed, ≥16 xfailed, 0 failed, 0 errored
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-01-01: StressRequest discriminated by 'mode' over 3 subclasses (mirrors Phase 4 AffordabilityRequest).
- D-01-02: StressResponse field order is `summary` BEFORE `rows` — SC-5 contract baked into the model declaration. NEVER reorder.
- D-01-03: StressRow carries summary SCALARS only; no full Schedule.payments[] arrays (D-03 in lib/stress.py docstring; SC-5 size budget).
- D-01-04: PointsRequest.discount_rate_annual REQUIRED (no default). Phase 6 cross-phase coupling deferred via additive non-breaking change. 08-RESEARCH §5.5.
- D-01-05: RatePath.name is Literal closed-set [parallel-shift, gradual-rise, fall-then-rise]. ROADMAP SC-3 verbatim.
- D-01-06: ScenarioSummary.stress_invariant_violations is a list[str], not a raise — engine appends citations; empty = happy path.
- D-01-07: PointsResponse always reports BOTH simple_breakeven_months AND npv_breakeven_months side-by-side; diverge flag set when they're unequal.
</locked_decisions>

<verify_block>
- lib/stress.py imports cleanly: `python -c "from lib.stress import *; print('OK')"`
- lib/points.py imports cleanly: `python -c "from lib.points import *; print('OK')"`
- mypy --strict lib/stress.py lib/points.py exits 0
- ruff check + format clean on both files
- 2 xfail flipped (test count = 16 xfailed remaining out of original 18)
- Full suite ≥413 passed (Wave 0 baseline 411 + 2 new flipped)
</verify_block>

<deviation_rules>
- Rule 1: If pydantic discriminated-union behavior differs from Phase 4 (e.g., discriminator field can't be Literal in v2 syntax), document the workaround in this PLAN.md AND in the SUMMARY.md, citing the pydantic docs URL.
- Rule 2: If `summary` field-order is somehow not preserved by Pydantic (regression), this is a HARD STOP — SC-5 is verbatim ROADMAP commitment.
- Rule 3: ruff format auto-collapse of long type-aliases (`StressRequest = Annotated[...]`) is accepted hygienically.
</deviation_rules>

<success_criteria>
- lib/stress.py + lib/points.py exist; both import cleanly with cross-plan stubs raising NotImplementedError
- 2 of the 18 Wave 0 xfails flipped (model contract + summary-before-rows)
- mypy + ruff clean on both new files
- Field-declaration order in StressResponse satisfies SC-5
- Phase 6 discount-rate coupling documented as DEFERRED (caller-supplied; non-breaking when Phase 6 lands)
</success_criteria>
