---
phase: 05
plan: 02
type: execute
wave: 2
depends_on:
  - "05-00"
  - "05-01"
files_modified:
  - lib/arm.py
  - tests/test_arm.py
autonomous: true
requirements:
  - ARM-01
tags:
  - phase-05
  - arm-modeling
  - pydantic-models
  - arm-01
must_haves:
  truths:
    - "lib/arm.py exists at project root and is importable (`from lib.arm import ARMTerms, ARMRequest, ARMPayment, ARMSchedule, ResetEvent, IndexPathEntry` succeeds)"
    - "ARMTerms has exactly the 8 explicit fields per ARM-01: initial_period_months, reset_period_months, initial_cap_bps, periodic_cap_bps, lifetime_cap_bps, floor_rate, margin_bps, index_series_id, plus the optional 9th field note_rate (per D-02)"
    - "floor_rate is REQUIRED in ARMTerms (no default, not Optional) — constructing ARMTerms without floor_rate raises ValidationError"
    - "ARMRequest has a model_validator(mode='after') named _index_path_periods_align_to_reset_triggers that raises ValueError when an index_path entry's period does not match a reset trigger"
    - "ARMPayment subclasses Phase 1 Payment via Pydantic v2 inheritance; adds rate_in_effect: Rate; re-specifies model_config (defense-in-depth) per D-03"
    - "ARMSchedule is a parallel BaseModel (NOT a subclass of Phase 1 Schedule) with payments: list[ARMPayment] and reset_events: list[ResetEvent]"
    - "ResetEvent.applied_cap is typed as Literal['initial', 'periodic', 'lifetime', 'floor', 'none'] — exactly 5 values per D-10"
    - "IndexPathEntry is defined inline in lib/arm.py (not in lib/models.py) per D-discretion scope-to-file convention"
    - "Wave 0 stubs test_arm_terms_field_set, test_arm_terms_missing_floor_rate_raises, test_note_rate_defaults_to_loan_annual_rate, and test_cli_misaligned_index_path_period_rejected (the part testable at the model layer) flip from xfail to PASS"
    - "Phase 4 baseline preserved (tests/test_affordability.py + tests/test_amortize.py unchanged)"
  artifacts:
    - path: "lib/arm.py"
      provides: "Six Pydantic v2 models: ARMTerms, IndexPathEntry, ARMRequest, ARMPayment, ResetEvent, ARMSchedule. NO build_arm_schedule yet (Wave 3 ships it). NO docstring citation to references/arm-mechanics.md (Wave 5 adds it)."
      contains: "class ARMTerms"
      min_lines: 150
    - path: "tests/test_arm.py"
      provides: "Wave 2 flips ARM-01 stubs to passing tests; adds NEW tests for ARMRequest.model_validator and ARMPayment subclass shape; introduces a build_arm_schedule stub-import test (engine arrives Wave 3)"
      contains: "def test_arm_terms_field_set"
  key_links:
    - from: "lib/arm.py"
      to: "lib/models.py"
      via: "imports Loan, Payment, Money, Rate"
      pattern: "from lib.models import.*Payment"
    - from: "lib/arm.py"
      to: "lib/money.py"
      via: "imports quantize_cents (rate quantize used in Wave 3 engine)"
      pattern: "from lib.money import"
    - from: "ARMRequest._index_path_periods_align_to_reset_triggers"
      to: "ARMTerms.initial_period_months + reset_period_months"
      via: "cross-field validator"
      pattern: "model_validator.*after"
---

<objective>
Ship the Pydantic v2 model layer of `lib/arm.py`: 6 strict+frozen+forbid models implementing the locked D-06 ARMTerms field schema (8 explicit fields + optional note_rate), the D-01 ARMRequest cross-field validator that aligns index_path entries to reset trigger periods, the D-03 parallel ARMPayment + ARMSchedule + ResetEvent shape, and the IndexPathEntry sub-model. NO engine code yet — `build_arm_schedule` ships in Wave 3 (Plan 05-03).

Closes ARM-01 ("`lib/arm.py` Pydantic model with explicit fields...") + closes ROADMAP SC-1 ("ARMTerms has 8 explicit fields, no implicit conventions").

Purpose: Give Wave 3 (engine), Wave 4 (CLI), and downstream Phase 8/11 consumers a stable type contract. Pydantic v2 models with `strict=True, frozen=True, extra="forbid"` enforce CLAUDE.md money discipline at every boundary — a JSON-float in `floor_rate` raises `ValidationError`, a missing `floor_rate` raises `ValidationError`, an index_path entry at month 62 (not a reset trigger) raises `ValueError` from the model_validator. Wave 4's CLI catches all three at the `model_validate_json` boundary and emits the WR-02 6-key Pydantic envelope; no engine code needs defensive checks.

Output: `lib/arm.py` ~150 lines containing the 6 model classes plus their validators; ~3 Wave-0 stubs flipped to passing tests in `tests/test_arm.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-arm-modeling/05-CONTEXT.md
@.planning/phases/05-arm-modeling/05-RESEARCH.md
@.planning/phases/05-arm-modeling/05-PATTERNS.md
@.planning/phases/05-arm-modeling/05-VALIDATION.md
@CLAUDE.md
@lib/models.py
@lib/affordability.py
@lib/amortize.py
@tests/test_arm.py

<interfaces>
Phase 1 Loan/Payment/Schedule (lib/models.py) — Phase 5 IMPORTS; does NOT modify:

```python
class Loan(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    principal: Money
    annual_rate: Rate
    term_months: int = Field(ge=1, le=600)
    origination_date: date
    loan_type: Literal["fixed", "arm", "interest_only", "balloon"] = "fixed"

class Payment(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=1)
    payment_date: date
    payment: Money
    principal: Money
    interest: Money
    extra_principal: Money
    balance: Money
    cumulative_interest: Money
    cumulative_principal: Money

class Schedule(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    monthly_pi: Money
    total_interest: Money
    payments: list[Payment]
    final_payment_adjusted: bool = False
```

Money = Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2)]
Rate  = Annotated[Decimal, Field(strict=True, max_digits=7, decimal_places=6)]

Phase 4 cross-field validator pattern (lib/amortize.py:184-194 + lib/affordability.py `_validate_common`) — the analog for ARMRequest._index_path_periods_align_to_reset_triggers:

```python
@model_validator(mode="after")
def _biweekly_mode_consistency(self) -> AmortizeRequest:
    if self.frequency == "monthly" and self.biweekly_mode is not None:
        raise ValueError("biweekly_mode must be None when frequency='monthly' (D-02)")
    return self
```

D-06 ARMTerms field schema (CONTEXT.md lines 153-175) — locked verbatim:

```python
initial_period_months: int = Field(ge=1, le=600)
reset_period_months: int = Field(ge=1, le=600)
initial_cap_bps: int = Field(ge=0, le=2000)
periodic_cap_bps: int = Field(ge=0, le=2000)
lifetime_cap_bps: int = Field(ge=0, le=2000)
floor_rate: Rate                                 # REQUIRED — no None, no default
margin_bps: int = Field(ge=0, le=2000)
index_series_id: str = Field(min_length=1, max_length=64)
note_rate: Rate | None = None                    # optional per D-02
```

D-03 ARMPayment + ARMSchedule + ResetEvent shape (CONTEXT.md lines 100-124) — locked verbatim:

```python
class ARMPayment(Payment):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    rate_in_effect: Rate

class ResetEvent(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=1)
    old_rate: Rate
    new_rate: Rate
    old_pmt: Money
    new_pmt: Money
    index_value_used: Rate
    applied_cap: Literal["initial", "periodic", "lifetime", "floor", "none"]

class ARMSchedule(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    arm_terms: ARMTerms
    payments: list[ARMPayment]
    reset_events: list[ResetEvent]
    total_interest: Money
    final_payment_adjusted: bool = False
```

Reset trigger formula (RESEARCH §Q5 + Q7):

```
triggers = []
period = arm_terms.initial_period_months + 1
while period <= loan.term_months:
    triggers.append(period)
    period += arm_terms.reset_period_months
# 5/1: [61, 73, 85, ...]; 5/6: [61, 67, 73, ...]; 7/1: [85, 97, ...]; 10/1: [121, 133, ...]
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create lib/arm.py with 6 Pydantic v2 models + ARMRequest cross-field validator</name>
  <files>lib/arm.py</files>
  <read_first>
    - lib/models.py (full file, 92 lines) — for Loan/Payment/Schedule field shape, Money/Rate Annotated types
    - lib/amortize.py:175-223 (AmortizeRequest with model_validator pattern) — analog for ARMRequest validator
    - lib/affordability.py:174-187 (imports block convention) — match the import order
    - lib/affordability.py:441-528 (_CommonRequestFields locked-shape model with `_validate_common`) — pattern for cross-field validators that raise ValueError
    - 05-CONTEXT.md D-01, D-02, D-03, D-06, D-15 — locked decisions on field shape + validators
    - 05-RESEARCH.md §Q7 (Code Example 1, lines 488-518) — explicit ARMRequest validator skeleton
    - 05-PATTERNS.md "Pattern 1" + "Pattern 2" sections (lines 43-122) — strict+frozen+forbid Pydantic v2 patterns + Field(ge=, le=) constraints
  </read_first>
  <action>
    Create lib/arm.py at project root. Place all 6 models in this single file (per D-discretion scope-to-file convention). Do NOT add any docstring citation to references/arm-mechanics.md — Wave 5 (Plan 05-05) injects that citation.

    File structure (literal Python):

    ```
    """ARM (adjustable-rate mortgage) models + engine for Phase 5.

    This file is the entry point for ARM modeling per CONTEXT.md D-03:
    parallel ARMSchedule + ARMPayment in lib/arm.py; Phase 1 Payment / Schedule
    UNCHANGED. Models live here (D-discretion scope-to-file) until a second
    consumer needs them — current consumers: lib.arm, scripts.arm_simulate.

    Wave 2 (Plan 05-02) ships the model layer (this file).
    Wave 3 (Plan 05-03) adds build_arm_schedule(...) per-epoch slice-stitch.
    Wave 5 (Plan 05-05) adds the references/arm-mechanics.md docstring citation
    on ARMTerms (ROADMAP SC-5).
    """

    from __future__ import annotations

    from typing import Literal

    from pydantic import BaseModel, ConfigDict, Field, model_validator

    from lib.models import Loan, Money, Payment, Rate


    class ARMTerms(BaseModel):
        """ARM contractual terms (8 explicit fields per ARM-01 + optional note_rate per D-02).

        Field schema locked in CONTEXT.md D-06. Every field is REQUIRED except
        note_rate; floor_rate has NO default per D-02 (forces explicit caller
        choice; matches mortgage-ops 'fail loud, no inference' discipline).

        Wave 5 (Plan 05-05) appends a docstring citation:
            See references/arm-mechanics.md for reset/cap/floor convention.
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

        initial_period_months: int = Field(ge=1, le=600)
        """Months at the initial fixed rate. 5/1 ARM = 60; 7/1 = 84; 10/1 = 120; 5/6 = 60."""

        reset_period_months: int = Field(ge=1, le=600)
        """Months between resets after the initial period. 5/1, 7/1, 10/1 = 12; 5/6 = 6."""

        initial_cap_bps: int = Field(ge=0, le=2000)
        """First-reset cap in basis points; common: 500 (5pp). 2000 (20pp) sanity rail."""

        periodic_cap_bps: int = Field(ge=0, le=2000)
        """Cap for resets after the first; common: 200 (2pp)."""

        lifetime_cap_bps: int = Field(ge=0, le=2000)
        """Lifetime cap measured against note_rate (D-02); common: 500 (5pp)."""

        floor_rate: Rate
        """REQUIRED per D-02. No default. Effective floor = max(margin_bps/10000, floor_rate)."""

        margin_bps: int = Field(ge=0, le=2000)
        """Spread over index in basis points; common: 250 (2.5pp)."""

        index_series_id: str = Field(min_length=1, max_length=64)
        """Metadata only in v1 (e.g., 'MORTGAGE30US', 'SOFR1Y'). Phase 12 maps to FRED MCP."""

        note_rate: Rate | None = None
        """Optional per D-02. None = use loan.annual_rate as lifetime base. Provide for teaser-rate ARMs."""


    class IndexPathEntry(BaseModel):
        """One entry in ARMRequest.index_path: an index value applied at a specific reset period.

        Scoped to lib/arm.py per D-discretion (scope-to-file until second consumer).
        Pattern mirrors Phase 3's ExtraPrincipalEntry (lib/amortize.py).
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

        period: int = Field(ge=1)
        """The reset trigger period this index value applies to (e.g., 61, 73 for a 5/1 ARM).
        Validated against the reset cadence by ARMRequest._index_path_periods_align_to_reset_triggers."""

        value: Rate
        """The index value at this period (e.g., 0.0525 = 5.25%)."""


    class ARMRequest(BaseModel):
        """Top-level request schema for build_arm_schedule + scripts/arm_simulate.py.

        Locked structure per D-01: assumed_index_rate REQUIRED + optional index_path overrides.
        Override-wins semantics: at a reset trigger period, index_path[period] wins over assumed_index_rate.
        Misaligned index_path periods (not a reset trigger) raise ValueError at construction.
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

        loan: Loan
        """Phase 1 Loan; loan.annual_rate is the INITIAL fixed-period rate. loan.loan_type='arm' is conventional but not validated here."""

        arm_terms: ARMTerms
        assumed_index_rate: Rate
        """REQUIRED per D-01. Engine fallback when index_path does not cover a reset period."""

        index_path: list[IndexPathEntry] = Field(default_factory=list)
        """Optional per-reset overrides. Empty list = use assumed_index_rate at every reset."""

        @model_validator(mode="after")
        def _index_path_periods_align_to_reset_triggers(self) -> ARMRequest:
            """D-01: every index_path entry's period MUST match a reset trigger.

            Reset triggers (per RESEARCH §Q5):
                triggers = [initial_period_months + 1 + k * reset_period_months for k in 0..]
                up to and including loan.term_months.

            For a 5/1 ARM (initial=60, reset=12, term=360): triggers = {61, 73, 85, ..., 349}.
            An index_path entry at period 62 raises ValueError — caller must align.
            """
            initial = self.arm_terms.initial_period_months
            cadence = self.arm_terms.reset_period_months
            term = self.loan.term_months
            triggers: set[int] = set()
            period = initial + 1
            while period <= term:
                triggers.add(period)
                period += cadence
            for entry in self.index_path:
                if entry.period not in triggers:
                    sample = sorted(triggers)[:5]
                    suffix = "..." if len(triggers) > 5 else ""
                    raise ValueError(
                        f"index_path entry at period {entry.period} does not align to a "
                        f"reset trigger period (D-01). Valid triggers for this product: "
                        f"{sample}{suffix}"
                    )
            return self


    class ARMPayment(Payment):
        """Payment row in an ARM schedule; subclass of Phase 1 Payment per D-03.

        Adds rate_in_effect to capture the per-period annualized rate. Pydantic v2
        model_config IS auto-inherited from Payment per RESEARCH LM-4, but we
        re-specify here for defense-in-depth + grep-discoverability.
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

        rate_in_effect: Rate
        """The annualized rate active during this period. Equals loan.annual_rate during epoch 0
        (initial fixed period); equals new_rate after each reset (D-02 formula)."""


    class ResetEvent(BaseModel):
        """One ARM reset boundary (per D-03).

        Records old/new rate, old/new payment, the index value used, and the cap
        kind that bound the new rate (Literal value enables D-10 citation-coverage).
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

        period: int = Field(ge=1)
        """Absolute period (continuous numbering) where the new rate first applies. 5/1: 61, 73, ..."""

        old_rate: Rate
        new_rate: Rate
        old_pmt: Money
        """P&I in effect immediately before the reset (last payment of the prior epoch)."""

        new_pmt: Money
        """P&I that takes effect at this period (first payment of the new epoch)."""

        index_value_used: Rate
        """The index value used to compute new_rate. Equals index_path[period].value if supplied,
        else assumed_index_rate (D-01 override-wins)."""

        applied_cap: Literal["initial", "periodic", "lifetime", "floor", "none"]
        """Which constraint bound new_rate. D-10 citation-coverage requires every value exercised."""


    class ARMSchedule(BaseModel):
        """ARM-aware schedule. Parallel to Phase 1 Schedule; NOT a subclass per D-03.

        Continuous period numbering 1..N across epochs. final_payment_adjusted reflects
        ONLY the final epoch's Phase 3 D-09 cleanup (intermediate epochs always carry
        forward — see Plan 05-03 D-05 algorithm).
        """

        model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

        loan: Loan
        arm_terms: ARMTerms
        payments: list[ARMPayment]
        """Continuous 1..N. payments[0].period == 1; payments[-1].period == loan.term_months."""

        reset_events: list[ResetEvent]
        """One entry per reset boundary (period >= initial_period_months + 1)."""

        total_interest: Money
        """Sum of all interest paid; preserves Phase 1 D-15 invariant: total_interest == payments[-1].cumulative_interest."""

        final_payment_adjusted: bool = False
        """Only the FINAL epoch sets True (per Phase 3 D-09 / D-10 cleanup); intermediate epochs always False."""
    ```

    Notes on the file:
    - All 6 model classes use `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`. Re-specifying on ARMPayment is defense-in-depth (per RESEARCH LM-4 Pydantic v2 model_config IS auto-inherited; re-specifying is harmless and grep-discoverable).
    - No engine code in this file yet. Wave 3 appends `build_arm_schedule(...)` after ARMSchedule.
    - The ARMTerms `_initial_period_aligns_with_reset` cross-field validator from D-06 sketch is intentionally OMITTED per CONTEXT.md A4 ("Not strictly required by ARM-01; planner can skip if it surfaces no real bugs").
    - Imports follow Phase 4 pattern (lib/affordability.py:174-187): `__future__` first, stdlib second, third-party third, lib.* last.
  </action>
  <verify>
    <automated>python -c "from lib.arm import ARMTerms, IndexPathEntry, ARMRequest, ARMPayment, ResetEvent, ARMSchedule; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File lib/arm.py exists with at least 150 lines
    - `grep -c 'class ARMTerms(BaseModel)' lib/arm.py` returns 1
    - `grep -c 'class IndexPathEntry(BaseModel)' lib/arm.py` returns 1
    - `grep -c 'class ARMRequest(BaseModel)' lib/arm.py` returns 1
    - `grep -c 'class ARMPayment(Payment)' lib/arm.py` returns 1
    - `grep -c 'class ResetEvent(BaseModel)' lib/arm.py` returns 1
    - `grep -c 'class ARMSchedule(BaseModel)' lib/arm.py` returns 1
    - `grep -c 'floor_rate: Rate' lib/arm.py` returns at least 1 (the field declaration)
    - `grep -c 'floor_rate: Rate | None' lib/arm.py` returns 0 (REQUIRED per D-02; never optional)
    - `grep -c 'note_rate: Rate | None = None' lib/arm.py` returns 1 (optional per D-02)
    - `grep -c 'applied_cap: Literal' lib/arm.py` returns 1
    - `grep -cE 'Literal\["initial", "periodic", "lifetime", "floor", "none"\]' lib/arm.py` returns 1
    - `grep -c '_index_path_periods_align_to_reset_triggers' lib/arm.py` returns 1
    - `grep -c '@model_validator(mode="after")' lib/arm.py` returns 1
    - `grep -c 'model_config = ConfigDict(strict=True, frozen=True, extra="forbid")' lib/arm.py` returns 6 (one per model class)
    - `grep -c 'rate_in_effect: Rate' lib/arm.py` returns 1
    - `grep -c 'index_series_id: str' lib/arm.py` returns 1
    - `grep -c 'index_path: list\[IndexPathEntry\]' lib/arm.py` returns 1
    - `grep -c 'def build_arm_schedule' lib/arm.py` returns 0 (Wave 3 ships engine; this plan ONLY ships models)
    - `python -c 'from lib.arm import ARMTerms, IndexPathEntry, ARMRequest, ARMPayment, ResetEvent, ARMSchedule'` exits 0
    - `mypy --strict lib/arm.py` exits 0
    - `ruff check lib/arm.py` exits 0
    - `ruff format --check lib/arm.py` exits 0
  </acceptance_criteria>
  <done>
    lib/arm.py imports cleanly; all 6 models constructable; mypy --strict + ruff clean; no engine code present.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip ARM-01 Wave 0 stubs in tests/test_arm.py to passing tests</name>
  <files>tests/test_arm.py</files>
  <read_first>
    - tests/test_arm.py (current Wave 0 stub state) — locate the 3 ARM-01 stubs + the test_cli_misaligned_index_path_period_rejected stub
    - 05-CONTEXT.md D-06 + D-02 + D-01 — locked field semantics
    - 05-VALIDATION.md "Phase Requirements → Test Map" rows for ARM-01
    - lib/arm.py (just-created) — for the import surface
    - tests/test_amortize.py (search for `model_validator` test patterns) — analog test for cross-field validator
  </read_first>
  <action>
    Flip exactly 3 ARM-01 stubs to passing tests AND add the model-layer half of test_cli_misaligned_index_path_period_rejected (the request boundary validator can be tested at the model layer; the CLI wrapping ships in Wave 4).

    For each flip, REMOVE the `@pytest.mark.xfail(strict=True, reason=...)` decorator (otherwise strict=True will turn the now-passing test into XPASS failure). Replace the `pytest.fail("Wave 0 stub")` body with the real assertion logic.

    Also ADD a new test `test_arm_request_misaligned_index_path_raises` (model-layer; complements the CLI-layer test that ships in Wave 4) — this is NOT a Wave-0 stub flip; it is a brand-new test.

    **Flip 1: test_arm_terms_field_set**

    Remove `@pytest.mark.xfail(...)` decorator. Replace body with:

    ```
    """ARM-01 + ROADMAP SC-1: ARMTerms has 8 explicit fields + REQUIRED floor_rate + optional note_rate."""
    from datetime import date
    from decimal import Decimal
    from lib.arm import ARMTerms
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    # All 8 ARM-01 fields plus the optional note_rate must exist on the model.
    field_names = set(ARMTerms.model_fields.keys())
    assert field_names == {
        "initial_period_months",
        "reset_period_months",
        "initial_cap_bps",
        "periodic_cap_bps",
        "lifetime_cap_bps",
        "floor_rate",
        "margin_bps",
        "index_series_id",
        "note_rate",
    }
    # Locked-shape model: strict, frozen, forbid extras.
    assert terms.model_config["strict"] is True
    assert terms.model_config["frozen"] is True
    assert terms.model_config["extra"] == "forbid"
    # Verify default for optional note_rate
    assert terms.note_rate is None
    # I-007: behavioral assertion — extra="forbid" actually rejects unknown fields at construction.
    from pydantic import ValidationError as _VErr
    with pytest.raises(_VErr) as exc:
        ARMTerms(
            initial_period_months=60,
            reset_period_months=12,
            initial_cap_bps=500,
            periodic_cap_bps=200,
            lifetime_cap_bps=500,
            floor_rate=Decimal("0.030000"),
            margin_bps=250,
            index_series_id="MORTGAGE30US",
            extra_field="x",  # type: ignore[call-arg]
        )
    extra_errors = [e for e in exc.value.errors() if "extra_field" in e["loc"]]
    assert len(extra_errors) >= 1
    assert extra_errors[0]["type"] == "extra_forbidden"
    ```

    **Flip 2: test_arm_terms_missing_floor_rate_raises**

    Remove decorator. Replace body with:

    ```
    """ARM-01 + D-02: ARMTerms rejects missing floor_rate at construction (no default)."""
    from lib.arm import ARMTerms
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc:
        # Same fields as test_arm_terms_field_set MINUS floor_rate.
        ARMTerms(
            initial_period_months=60,
            reset_period_months=12,
            initial_cap_bps=500,
            periodic_cap_bps=200,
            lifetime_cap_bps=500,
            margin_bps=250,
            index_series_id="MORTGAGE30US",
        )
    errors = exc.value.errors()
    # At least one error mentions the missing floor_rate field
    floor_rate_errors = [e for e in errors if "floor_rate" in e["loc"]]
    assert len(floor_rate_errors) >= 1
    assert floor_rate_errors[0]["type"] == "missing"
    ```

    **Flip 3: test_note_rate_defaults_to_loan_annual_rate**

    This test asserts engine BEHAVIOR (engine substitutes loan.annual_rate when note_rate is None), but the engine ships in Wave 3. The model-layer half of the test is just "note_rate defaults to None" — flip ONLY that portion in Wave 2; leave a one-line assertion that note_rate=None is the default; Wave 3 will REPLACE this test with the full engine-behavior assertion.

    Remove decorator. Replace body with:

    ```
    """ARM-01 + D-02 (model-layer half): note_rate defaults to None.

    Wave 3 (Plan 05-03) replaces this test with the full engine assertion that
    when note_rate=None, build_arm_schedule treats it as loan.annual_rate for
    lifetime ceiling math.
    """
    from decimal import Decimal
    from lib.arm import ARMTerms
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    # Wave 2 model-layer assertion: default is None when not supplied.
    assert terms.note_rate is None
    # Wave 2 model-layer assertion: explicit value preserved.
    teaser_terms = terms.model_copy(update={"note_rate": Decimal("0.050000")})
    assert teaser_terms.note_rate == Decimal("0.050000")
    ```

    **NEW TEST — Add `test_arm_request_misaligned_index_path_raises`** at the bottom of tests/test_arm.py (NOT a Wave 0 flip — brand-new test that pins the ARMRequest validator at the model layer; the CLI version `test_cli_misaligned_index_path_period_rejected` stays as an xfail stub for Wave 4 to flip):

    ```
    def test_arm_request_misaligned_index_path_raises() -> None:
        """ARM-01 + D-01 (model-layer): ARMRequest._index_path_periods_align_to_reset_triggers
        raises ValueError when an index_path entry's period is not a reset trigger.

        Reset triggers for 5/1 ARM (initial=60, reset=12): {61, 73, 85, ...}.
        Period 62 is NOT a trigger; construction must fail loud.

        Wave 4 (Plan 05-04) ships test_cli_misaligned_index_path_period_rejected
        which wraps this same validation through the scripts/arm_simulate.py CLI
        and verifies the 6-key envelope on stderr.
        """
        from datetime import date
        from decimal import Decimal
        from pydantic import ValidationError
        from lib.arm import ARMRequest, ARMTerms, IndexPathEntry
        from lib.models import Loan

        loan = Loan(
            principal=Decimal("400000.00"),
            annual_rate=Decimal("0.050000"),
            term_months=360,
            origination_date=date(2026, 1, 1),
            loan_type="arm",
        )
        terms = ARMTerms(
            initial_period_months=60,
            reset_period_months=12,
            initial_cap_bps=500,
            periodic_cap_bps=200,
            lifetime_cap_bps=500,
            floor_rate=Decimal("0.030000"),
            margin_bps=250,
            index_series_id="MORTGAGE30US",
        )
        with pytest.raises(ValidationError) as exc:
            ARMRequest(
                loan=loan,
                arm_terms=terms,
                assumed_index_rate=Decimal("0.050000"),
                index_path=[IndexPathEntry(period=62, value=Decimal("0.052500"))],
            )
        # ValueError raised in model_validator surfaces in errors()
        errors = exc.value.errors()
        # At least one error mentions period 62 misalignment
        period_errors = [e for e in errors if "62" in str(e.get("msg", ""))]
        assert len(period_errors) >= 1, f"Expected period-62 misalignment error, got: {errors}"


    def test_arm_request_aligned_index_path_succeeds() -> None:
        """ARM-01 + D-01 (model-layer): ARMRequest accepts index_path entries that
        align to reset triggers. 5/1 ARM trigger 61 + 73 should both pass.
        """
        from datetime import date
        from decimal import Decimal
        from lib.arm import ARMRequest, ARMTerms, IndexPathEntry
        from lib.models import Loan

        loan = Loan(
            principal=Decimal("400000.00"),
            annual_rate=Decimal("0.050000"),
            term_months=360,
            origination_date=date(2026, 1, 1),
            loan_type="arm",
        )
        terms = ARMTerms(
            initial_period_months=60,
            reset_period_months=12,
            initial_cap_bps=500,
            periodic_cap_bps=200,
            lifetime_cap_bps=500,
            floor_rate=Decimal("0.030000"),
            margin_bps=250,
            index_series_id="MORTGAGE30US",
        )
        request = ARMRequest(
            loan=loan,
            arm_terms=terms,
            assumed_index_rate=Decimal("0.050000"),
            index_path=[
                IndexPathEntry(period=61, value=Decimal("0.052500")),
                IndexPathEntry(period=73, value=Decimal("0.055000")),
            ],
        )
        assert len(request.index_path) == 2
        assert request.index_path[0].period == 61
        assert request.index_path[1].period == 73
    ```

    Notes:
    - Do NOT touch any other xfail stub. Wave 3/4/5/6 each flip their own assigned stubs.
    - The test_cli_misaligned_index_path_period_rejected stub stays as xfail in this wave; Wave 4 flips it.
    - The test_note_rate_defaults_to_loan_annual_rate flip is intentionally PARTIAL (model-layer assertion only); Wave 3 replaces it with the full engine assertion. Document this in the test docstring.
  </action>
  <verify>
    <automated>pytest tests/test_arm.py::test_arm_terms_field_set tests/test_arm.py::test_arm_terms_missing_floor_rate_raises tests/test_arm.py::test_note_rate_defaults_to_loan_annual_rate tests/test_arm.py::test_arm_request_misaligned_index_path_raises tests/test_arm.py::test_arm_request_aligned_index_path_succeeds -xvs</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_arm.py::test_arm_terms_field_set -x` exits 0 with 1 passed
    - test_arm_terms_field_set body asserts `terms.model_config['strict'] is True` AND `terms.model_config['frozen'] is True` AND constructs `ARMTerms(..., extra_field="x")` inside `pytest.raises(ValidationError)` (I-007 behavioral assertion — extra="forbid" actually fires)
    - `pytest tests/test_arm.py::test_arm_terms_missing_floor_rate_raises -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_note_rate_defaults_to_loan_annual_rate -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_arm_request_misaligned_index_path_raises -x` exits 0 with 1 passed (NEW test)
    - `pytest tests/test_arm.py::test_arm_request_aligned_index_path_succeeds -x` exits 0 with 1 passed (NEW test)
    - `grep -c '@pytest.mark.xfail' tests/test_arm.py` returns 29 (32 Wave 0 stubs minus 3 flipped in this plan)
    - `grep -c 'def test_arm_request_misaligned_index_path_raises' tests/test_arm.py` returns 1
    - `grep -c 'def test_arm_request_aligned_index_path_succeeds' tests/test_arm.py` returns 1
    - `mypy --strict tests/test_arm.py` exits 0
    - `ruff check tests/test_arm.py` exits 0
    - `ruff format --check tests/test_arm.py` exits 0
  </acceptance_criteria>
  <done>
    3 ARM-01 stubs passing; 2 NEW tests pinning the ARMRequest validator at the model layer; xfail count drops from 32 to 29; mypy + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero regression to Phase 3 + Phase 4 + Wave 0/1 baselines</name>
  <files>(verification only)</files>
  <read_first>
    - 05-VALIDATION.md "Phase gate" row
    - Plan 05-00 + Plan 05-01 SUMMARY for baseline pass counts
  </read_first>
  <action>
    Run the full pytest suite. Expected counts after this plan:
    - Plan 05-01 baseline: 380 passed (was 379 + 1 new test_quantize_rate_round_half_up) + 4 skipped + 32 xfailed
    - Plan 05-02 delta: +3 ARM-01 flips (xfail → pass) + 2 new tests (test_arm_request_*) → +5 passed, -3 xfailed
    - Final expected: 385 passed + 4 skipped + 29 xfailed + 0 failed + 0 errored

    Run: `pytest -q`

    Also confirm no Phase 3 regression (lib/amortize.py UNTOUCHED) and no Phase 4 regression (only the import + 4 call-site renames touched lib/affordability.py from Plan 05-01; this plan does not touch it).

    Run mypy + ruff on every file Phase 5 has touched so far:
    - `mypy --strict lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py`
    - `ruff check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py`
    - `ruff format --check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py`

    All MUST be clean. If any fail, fix and re-run.
  </action>
  <verify>
    <automated>pytest -q &amp;&amp; mypy --strict lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py &amp;&amp; ruff check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py &amp;&amp; ruff format --check lib/arm.py lib/money.py lib/affordability.py tests/test_arm.py tests/test_money.py tests/conftest.py</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q` final summary shows passed >= 385
    - `pytest -q` final summary shows xfailed = 29 (was 32; minus 3 flipped)
    - `pytest -q` final summary shows skipped >= 4 (Phase 4 baseline preserved)
    - `pytest -q` final summary shows failed = 0
    - `pytest -q` final summary shows errors = 0
    - `pytest tests/test_amortize.py -q` shows zero regression vs Phase 3 closure
    - `pytest tests/test_affordability.py -q` shows zero regression vs Phase 4 closure
    - `mypy --strict` across all 6 files exits 0
    - `ruff check` across all 6 files exits 0
    - `ruff format --check` across all 6 files exits 0
  </acceptance_criteria>
  <done>
    Full suite green; ARM-01 closure verified at the model layer; mypy + ruff clean; no regression.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ARMRequest model_validate boundary | Untrusted JSON crosses here; cross-field validator rejects misaligned index_path before engine sees it |
| ARMTerms model construction | Caller-supplied cap_bps + floor_rate + index_series_id; Pydantic Field constraints reject malformed values |
| ARMPayment subclass shape | Phase 8 stress / Phase 11 amortization-agent iterate ARMSchedule.payments expecting Phase 1 Payment fields + rate_in_effect |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-02 | Tampering (index-path period misalignment) | ARMRequest._index_path_periods_align_to_reset_triggers | mitigate | model_validator(mode="after") raises ValueError at construction; CLI wraps as 6-key envelope (Wave 4); tested by test_arm_request_misaligned_index_path_raises (this plan) |
| T-05-16 | Tampering (silent floor_rate omission via default) | ARMTerms.floor_rate field declaration | mitigate | floor_rate has NO default per D-02; missing field raises ValidationError(type='missing'); tested by test_arm_terms_missing_floor_rate_raises (this plan) |
| T-05-17 | Information Disclosure (extra fields silently accepted) | ARMTerms / ARMRequest model_config | mitigate | extra='forbid' on every model rejects unknown fields with ValidationError(type='extra_forbidden') — the 6 model_config greps in acceptance_criteria pin this |
| T-05-18 | Tampering (ARMPayment fields drift from Phase 1 Payment) | ARMPayment subclass relationship | mitigate | ARMPayment(Payment) Pydantic v2 inheritance: subclass adds rate_in_effect; Phase 1 fields auto-included. Re-specifying model_config is defense-in-depth per RESEARCH LM-4 |
| T-05-19 | Repudiation (model_config not enforced because not re-specified) | ARMPayment model_config inheritance | accept | RESEARCH LM-4 confirms Pydantic v2 auto-inherits config; we re-specify anyway for grep-discoverability. Even if Pydantic v3 changes inheritance, our re-spec maintains behavior |
</threat_model>

<verification>
- lib/arm.py exists with all 6 model classes; mypy + ruff clean
- ARMRequest model_validator pins the D-01 alignment rule; misaligned index_path raises ValueError
- floor_rate is REQUIRED (no default); missing-field tests raise ValidationError
- 3 Wave-0 ARM-01 stubs flipped to passing; 29 xfails remain (32 - 3 = 29)
- 2 NEW tests pin the ARMRequest validator at the model layer (the CLI half stays xfail for Wave 4)
- Phase 3 + Phase 4 baselines preserved
- ARM-01 requirement closed at the model layer (engine behavior — note_rate fallback — closes in Wave 3)
</verification>

<success_criteria>
- ARM-01 closed at the model layer (8 explicit fields + REQUIRED floor_rate + optional note_rate verified)
- ROADMAP SC-1 verified ("ARMTerms has 8 explicit fields, no implicit conventions")
- ARMRequest cross-field validator pins D-01 index-path alignment rule
- Pydantic v2 strict+frozen+forbid model_config on all 6 models
- Test count: 385 passed, 29 xfailed, 4 skipped, 0 failed, 0 errors
- mypy --strict + ruff clean across all touched files
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-02-SUMMARY.md` documenting:
- lib/arm.py line count (~150)
- 6 model classes inventoried
- 3 Wave-0 stubs flipped (test_arm_terms_field_set, test_arm_terms_missing_floor_rate_raises, test_note_rate_defaults_to_loan_annual_rate)
- 2 new model-layer tests added (test_arm_request_misaligned_index_path_raises, test_arm_request_aligned_index_path_succeeds)
- xfail count: 32 → 29
- Pass count: 380 → 385
- mypy + ruff status across 6 files
- ARM-01 closure status (closed at model layer; engine behavior closure in Wave 3)
</output>
