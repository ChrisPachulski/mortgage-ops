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
  AffordabilityRequest pattern (lib/affordability.py:531-534).

LOCKED DECISION - D-02 (SC-5 field order: summary BEFORE rows):
  StressResponse declares ``summary: ScenarioSummary`` BEFORE
  ``rows: list[StressRow]``. Pydantic v2 preserves field-declaration order in
  ``model_dump_json``. The Phase 11 stress-test-agent (Haiku, ≤1k token return
  budget) reads the first ~30 lines of the JSON envelope and gets the summary
  table + worst-case label + invariant-violation list without paging the per-row
  detail. ROADMAP SC-5 verbatim closure. NEVER reorder these two fields.

LOCKED DECISION - D-03 (per-row schedule_summary scalars only; no full schedules):
  StressRow carries SUMMARY SCALARS (monthly_pi, total_interest, dti_back, etc.) —
  NEVER full Schedule.payments[] arrays. 50-rate sweep x 360 rows x 200 bytes per
  row would be 3.6MB, blowing the 100KB SC-5 budget by 36x. Rule pinned in
  08-RESEARCH §1.3.

LOCKED DECISION - D-04 (caller-supplied threshold; no module default):
  IncomeShockRequest.dti_threshold is REQUIRED (Rate). No module-level default;
  the CLI exposes 0.43 as a documented default in --help epilog only. Matches
  Phase 4 D-12 max_dti discipline (fail-loud-on-implicit-default project doctrine).

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

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from lib.affordability import (
    AffordabilityRequest,  # noqa: TC001  # Pydantic resolves field annotations at runtime
)
from lib.arm import ARMRequest  # noqa: TC001  # Pydantic resolves field annotations at runtime
from lib.models import (  # noqa: TC001  # Pydantic resolves field annotations at runtime
    Loan,
    Money,
    Rate,
)

# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------


class RatePath(BaseModel):
    """One named rate-path scenario for ARM-reset sweeps (D-05).

    params shape varies by name:
      parallel-shift: {"shift_bps": int}
      gradual-rise:   {"step_bps": int}
      fall-then-rise: {"drop_bps": int, "rise_bps": int}

    Wave 2 (Plan 08-02) ships ``_synthesize_index_path`` which dispatches on
    ``name`` and reads the matching keys from ``params``. This file's contract
    is the type surface only.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    name: Literal["parallel-shift", "gradual-rise", "fall-then-rise"]
    params: dict[str, int]


class StressRow(BaseModel):
    """One scenario row in StressResponse.rows. Summary scalars only (D-03).

    Per-mode field population (only the scalars relevant for the row's mode are
    non-None; all other fields default to None):

      rate-shock:    monthly_pi, total_interest, delta_vs_baseline_monthly,
                     delta_vs_baseline_pct
      income-shock:  dti_back, breaches_threshold, blocked_by
      arm-reset:     total_interest, max_payment, reset_count, highest_rate

    Wave 2 fills these from ``Schedule.monthly_pi`` (Phase 3),
    ``AffordabilityResponse.dti_back`` (Phase 4), and ``ARMSchedule.total_interest``
    + ResetEvent fields (Phase 5).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    label: str
    # Mode-specific scalars (only the ones relevant for the row's mode are non-None)
    monthly_pi: Money | None = None  # rate-shock
    total_interest: Money | None = None  # rate-shock + arm-reset
    delta_vs_baseline_monthly: Money | None = None  # rate-shock
    delta_vs_baseline_pct: Rate | None = None  # rate-shock
    dti_back: Rate | None = None  # income-shock
    breaches_threshold: bool | None = None  # income-shock
    blocked_by: str | None = None  # income-shock
    max_payment: Money | None = None  # arm-reset
    reset_count: int | None = None  # arm-reset
    highest_rate: Rate | None = None  # arm-reset


class ScenarioSummary(BaseModel):
    """The top-of-JSON table for SC-5 subagent consumption.

    Phase 11's stress-test-agent reads this block first, decides whether to
    drill into the per-row detail. The ``stress_invariant_violations`` list is
    empty in the happy path; non-empty when a physics-of-amortization invariant
    is violated (e.g., monthly_pi went DOWN as rate went UP — Phase 3 engine bug
    indicator). 08-RESEARCH §6.4 lists the invariants worth surfacing.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    table: list[StressRow]
    baseline_label: str | None = None
    worst_case_label: str | None = None
    stress_invariant_violations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request union (D-01)
# ---------------------------------------------------------------------------


class _CommonStressFields(BaseModel):
    """Shared base for all three stress subclasses; do NOT instantiate directly.

    The ``mode`` discriminator field lives on the SUBCLASSES (not here) so the
    Pydantic v2 Annotated/Field(discriminator='mode') union works identically to
    the Phase 4 AffordabilityRequest idiom (lib/affordability.py:441-534).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    scenario_label: str | None = None  # optional human-readable run tag


class RateShockRequest(_CommonStressFields):
    """STRS-01 + ROADMAP SC-1: re-solve PMT for a grid of rates.

    Each rate in ``rates`` is overlaid onto a synthetic copy of ``loan`` and
    fed to ``lib.amortize.build_schedule`` (Phase 3); the resulting
    ``Schedule.monthly_pi`` + ``Schedule.total_interest`` are captured as
    summary scalars (D-03). Plan 08-02 ships the loop body.
    """

    mode: Literal["rate-shock"] = "rate-shock"
    loan: Loan
    rates: list[Rate] = Field(min_length=1)
    baseline_label: str | None = None  # if None, defaults to str(rates[0])


class IncomeShockRequest(_CommonStressFields):
    """STRS-02 + ROADMAP SC-2: recompute back-end DTI for a grid of income reductions.

    Each reduction in ``reductions`` scales each applicant's
    ``gross_monthly_income`` by ``(1 - reduction)`` and re-runs
    ``lib.affordability.evaluate(shocked_request)``. The resulting ``dti_back``
    is compared to ``dti_threshold`` to populate ``breaches_threshold``.
    Plan 08-02 ships the loop body.
    """

    mode: Literal["income-shock"] = "income-shock"
    base_request: AffordabilityRequest
    reductions: list[Rate] = Field(min_length=1)
    dti_threshold: Rate  # D-04: REQUIRED; no module default


class ArmResetRequest(_CommonStressFields):
    """STRS-03 + ROADMAP SC-3: simulate index-path scenarios for an ARM.

    For each named ``RatePath`` in ``paths``, Plan 08-02 synthesizes a list of
    ``IndexPathEntry`` rows (one per reset trigger, derived via the promoted
    ``lib.arm.compute_reset_triggers`` helper), constructs an ``ARMRequest``
    via ``model_copy(update={"index_path": ...})``, and reads
    ``ARMSchedule.total_interest`` + ResetEvent fields. ARMRequest.index_path
    is the Phase 5 ARM-01 injection surface (lib/arm.py:104) explicitly designed
    for this consumer.
    """

    mode: Literal["arm-reset"] = "arm-reset"
    base_arm_request: ARMRequest
    paths: list[RatePath] = Field(min_length=1)


StressRequest = Annotated[
    RateShockRequest | IncomeShockRequest | ArmResetRequest,
    Field(discriminator="mode"),
]
"""Pydantic v2 discriminated union by ``mode`` (D-01).

Use ``TypeAdapter(StressRequest).validate_python(...)`` or
``validate_json(...)`` at the script boundary; the discriminator routes the
raw payload to the matching subclass. Mirrors Phase 4 AffordabilityRequest
(lib/affordability.py:531-534)."""


# ---------------------------------------------------------------------------
# Response (D-02 field order: summary BEFORE rows)
# ---------------------------------------------------------------------------


class StressResponse(BaseModel):
    """Top-level response. Field declaration order pinned for SC-5: summary first.

    Field declaration order is THE ROADMAP SC-5 contract. Pydantic v2
    preserves declaration order in ``model_dump_json`` so the serialized
    JSON always carries ``"summary": {...}`` before ``"rows": [...]``. The
    Phase 11 stress-test-agent reads the first ~30 lines of JSON and gets
    the summary table + worst-case label + invariant-violation list. Do NOT
    reorder ``summary`` and ``rows`` (D-02).

    Plan 08-05 fixture ``rate_shock_size_budget_50_rates.json`` asserts the
    serialized JSON is < 100KB AND that the summary key precedes the rows
    key in dict ordering.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["rate-shock", "income-shock", "arm-reset"]
    scenario_count: int = Field(ge=0)
    summary: ScenarioSummary  # D-02: BEFORE rows
    rows: list[StressRow]


# ---------------------------------------------------------------------------
# Engine — cross-plan stub (Plan 08-02 fills body)
# ---------------------------------------------------------------------------


def evaluate(req: StressRequest) -> StressResponse:
    """Dispatch on ``req.mode`` and run the matching sweep.

    Wave 1 (Plan 08-01 — this file) ships the type contract only. Wave 2
    (Plan 08-02) replaces this body with three branches over
    ``isinstance(req, RateShockRequest|IncomeShockRequest|ArmResetRequest)``,
    each calling the matching Phase 3/4/5 engine in a per-cell loop and
    assembling a ``StressResponse``.

    Cross-plan stub idiom: Phase 4 D-08 (lib.affordability Wave 1 → Wave 2
    pattern). Stubbing here lets Plans 08-02 and 08-03 fill bodies without
    re-importing the surface across the wave boundary.
    """
    raise NotImplementedError("lib.stress.evaluate body lives in Plan 08-02")
