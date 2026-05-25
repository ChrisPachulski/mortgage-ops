"""Stress-test engine for Phase 8 (STRS-01..04 + ROADMAP SC-1/2/3/5).

Composition over Phase 3 (lib.amortize.build_schedule), Phase 4
(lib.affordability.evaluate), and Phase 5 (lib.arm.build_arm_schedule).
Phase 8 invents NO new mathematical primitive; every stress sweep is a
loop over an existing engine.

See ``references/stress-tests.md`` for the sweep-mode conventions, the
SC-5 top-table-summary output-schema contract, the Phase 11
``stress-test-agent`` consumption hint (verbatim-lift target per locked
decision D-06-04), and the regulatory citations (CFPB ATR/QM
1026.43(c)(5) for ARM-reset, March 2021 General QM Final Rule for the
DTI heuristic, CFPB §1951 for ARM rate caps). Plan 08-06 D-06-01
inherits the section structure from ``references/arm-mechanics.md``
(Phase 5 D-08 [REVISED]); Phase 7 D-29 cite-from-doc idiom anchors this
docstring back to the reference.

Wave 1 (Plan 08-01) ships ONLY the Pydantic v2 type contract +
documented stubs for evaluate(). Wave 2 (Plan 08-02) adds the body to
evaluate() and ships rate_shock(), income_shock(), arm_path() helpers.
Wave 6 (Plan 08-06) ships ``references/stress-tests.md`` and adds this
cite-from contract.

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

from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.affordability import AffordabilityRequest
from lib.affordability import (
    evaluate as affordability_evaluate,
)
from lib.amortize import build_schedule
from lib.arm import (
    ARMRequest,
    ARMTerms,
    IndexPathEntry,
    build_arm_schedule,
    compute_reset_triggers,
)
from lib.models import (  # noqa: TC001  # Pydantic resolves field annotations at runtime
    Loan,
    Money,
    NonNegativeRatio,
    Rate,
)
from lib.money import quantize_cents, quantize_rate

if TYPE_CHECKING:
    from collections.abc import Sequence


IncomeReduction = Annotated[
    Decimal,
    Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), lt=Decimal("1")),
]

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

    @model_validator(mode="after")
    def _params_match_name(self) -> RatePath:
        required_by_name: dict[str, set[str]] = {
            "parallel-shift": {"shift_bps"},
            "gradual-rise": {"step_bps"},
            "fall-then-rise": {"drop_bps", "rise_bps"},
        }
        required = required_by_name[self.name]
        actual = set(self.params)
        if actual != required:
            missing = sorted(required - actual)
            extra = sorted(actual - required)
            details: list[str] = []
            if missing:
                details.append(f"missing keys: {', '.join(missing)}")
            if extra:
                details.append(f"extra keys: {', '.join(extra)}")
            raise ValueError(
                f"params for {self.name!r} must be {sorted(required)}; {'; '.join(details)}"
            )
        return self


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
    dti_back: NonNegativeRatio | None = None  # income-shock
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
    reductions: list[IncomeReduction] = Field(min_length=1)
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
# Engine — per-mode helpers (Plan 08-02)
# ---------------------------------------------------------------------------


def rate_shock(
    loan: Loan,
    rates: Sequence[Rate],
    baseline_label: str | None = None,
) -> tuple[list[StressRow], ScenarioSummary]:
    """STRS-01 + ROADMAP SC-1: re-solve PMT for each rate in the grid.

    Returns ``(rows, summary)``. Each row carries ``monthly_pi`` +
    ``total_interest`` + ``delta_vs_baseline_monthly`` +
    ``delta_vs_baseline_pct`` (the last two computed relative to the
    ``baseline_label`` cell, defaulting to ``rates[0]``).

    ``stress_invariant_violations`` appends ``"RATE_SHOCK_MONOTONE_PI"`` if
    ``monthly_pi`` does NOT strictly increase as rate strictly increases
    (Phase 3 engine bug signal per 08-RESEARCH §6.4).
    """
    # Phase 1: build base rows by re-solving PMT per rate via Phase 3 engine.
    rows: list[StressRow] = []
    for rate in rates:
        syn_loan = loan.model_copy(update={"annual_rate": rate})
        schedule = build_schedule(syn_loan, frequency="monthly")
        rows.append(
            StressRow(
                label=str(rate),
                monthly_pi=schedule.monthly_pi,
                total_interest=schedule.total_interest,
            )
        )

    # Resolve baseline label + payment.
    if baseline_label is None:
        baseline_label = rows[0].label
    baseline_row = next((r for r in rows if r.label == baseline_label), None)
    if baseline_row is None:
        raise ValueError(f"baseline_label {baseline_label!r} did not match any rate-shock row")
    baseline_pi = baseline_row.monthly_pi
    assert baseline_pi is not None  # mypy narrow; constructed non-None above

    # Phase 2: enrich rows with delta_vs_baseline_monthly + delta_vs_baseline_pct.
    enriched: list[StressRow] = []
    for r in rows:
        assert r.monthly_pi is not None  # mypy narrow
        delta_m = quantize_cents(r.monthly_pi - baseline_pi)
        if baseline_pi > Decimal("0"):
            delta_pct = quantize_rate((r.monthly_pi - baseline_pi) / baseline_pi)
        else:
            delta_pct = Decimal("0.000000")
        enriched.append(
            r.model_copy(
                update={
                    "delta_vs_baseline_monthly": delta_m,
                    "delta_vs_baseline_pct": delta_pct,
                }
            )
        )

    # Invariants: monotone monthly_pi as rate increases (08-RESEARCH §6.4).
    violations: list[str] = []
    rate_pi_pairs: list[tuple[Rate, Money]] = []
    for rate, r in zip(rates, rows, strict=True):
        assert r.monthly_pi is not None  # mypy narrow
        rate_pi_pairs.append((rate, r.monthly_pi))
    sorted_pairs = sorted(rate_pi_pairs, key=lambda p: p[0])
    for i in range(1, len(sorted_pairs)):
        r_lo, pi_lo = sorted_pairs[i - 1]
        r_hi, pi_hi = sorted_pairs[i]
        if r_hi > r_lo and pi_hi <= pi_lo:
            violations.append("RATE_SHOCK_MONOTONE_PI")
            break

    # Worst case = highest monthly_pi (rows just constructed, all non-None).
    def _row_pi(r: StressRow) -> Money:
        assert r.monthly_pi is not None
        return r.monthly_pi

    worst = max(enriched, key=_row_pi)

    summary = ScenarioSummary(
        table=enriched,
        baseline_label=baseline_label,
        worst_case_label=worst.label,
        stress_invariant_violations=violations,
    )
    return enriched, summary


def income_shock(
    base_request: AffordabilityRequest,
    reductions: Sequence[Rate],
    dti_threshold: Rate,
) -> tuple[list[StressRow], ScenarioSummary]:
    """STRS-02 + ROADMAP SC-2: recompute back-end DTI for each reduction.

    Per 08-RESEARCH §3.3: scale each applicant's ``gross_monthly_income`` by
    ``(1 - reduction)``; call ``lib.affordability.evaluate``; capture
    ``dti_back`` + breach flag (``dti_back > dti_threshold``).

    The reduction is applied per-applicant (D-02-03): Phase 4 D-06 sum
    aggregation means proportional cuts per applicant produce a
    proportionally-cut total. Belt-and-braces re-validation happens via
    Pydantic's per-call ``model_copy``-induced revalidation in
    ``affordability_evaluate`` (Phase 4 forward-mode validators).
    """
    rows: list[StressRow] = []
    for reduction in reductions:
        if reduction < Decimal("0") or reduction >= Decimal("1"):
            raise ValueError(f"income-shock reduction must be >= 0 and < 1; got {reduction}")
        multiplier = Decimal("1") - reduction
        shocked_household = base_request.household.model_copy(
            update={
                "applicants": [
                    a.model_copy(
                        update={
                            "gross_monthly_income": quantize_cents(
                                a.gross_monthly_income * multiplier
                            )
                        }
                    )
                    for a in base_request.household.applicants
                ]
            }
        )
        shocked = base_request.model_copy(update={"household": shocked_household})
        response = affordability_evaluate(shocked)
        dti_back = response.dti_back  # Rate | None
        breaches = (dti_back is not None) and (dti_back > dti_threshold)
        percent = (reduction * Decimal("100")).normalize()
        rows.append(
            StressRow(
                label=f"-{percent:f}%",
                dti_back=dti_back,
                breaches_threshold=breaches,
                blocked_by=response.blocked_by,
            )
        )

    # Worst case = highest dti_back (None treated as 0 to keep max() total).
    def _row_dti(r: StressRow) -> NonNegativeRatio:
        return r.dti_back if r.dti_back is not None else Decimal("0")

    worst_label = max(rows, key=_row_dti).label if rows else None

    summary = ScenarioSummary(
        table=rows,
        baseline_label=rows[0].label if rows else None,
        worst_case_label=worst_label,
        # Per D-02-05: stress_invariant_violations populated only for rate-shock
        # in v1; income-shock dti monotone invariant noted for Phase 11+.
        stress_invariant_violations=[],
    )
    return rows, summary


def _synthesize_index_path(
    arm_terms: ARMTerms,
    term_months: int,
    base_index: Rate,
    path: RatePath,
) -> list[IndexPathEntry]:
    """08-RESEARCH §4.2 algorithm. Returns one IndexPathEntry per reset trigger.

    Three named paths (D-02-04 closed-set per ROADMAP SC-3):
      parallel-shift: every trigger receives ``base_index + shift_bps/10000``
      gradual-rise:   trigger ``k`` receives ``base_index + k * step_bps/10000``
      fall-then-rise: first half receives ``base_index - drop_bps/10000``;
                      second half receives ``base_index + rise_bps/10000``

    Every reset trigger MUST be covered (alignment-validator on ARMRequest
    enforces this; misalignment would be a Plan-08-02 bug, not a runtime issue).
    """
    triggers = compute_reset_triggers(arm_terms, term_months)
    if path.name == "parallel-shift":
        shift = path.params["shift_bps"]
        return [
            IndexPathEntry(
                period=t,
                value=quantize_rate(base_index + Decimal(shift) / Decimal("10000")),
            )
            for t in triggers
        ]
    if path.name == "gradual-rise":
        step = path.params["step_bps"]
        return [
            IndexPathEntry(
                period=t,
                value=quantize_rate(base_index + Decimal(k * step) / Decimal("10000")),
            )
            for k, t in enumerate(triggers)
        ]
    # fall-then-rise (closed-set; mypy exhaustiveness narrowed via Literal)
    drop = path.params["drop_bps"]
    rise = path.params["rise_bps"]
    half = len(triggers) // 2
    out: list[IndexPathEntry] = []
    for i, t in enumerate(triggers):
        if i < half:
            v = quantize_rate(base_index - Decimal(drop) / Decimal("10000"))
        else:
            v = quantize_rate(base_index + Decimal(rise) / Decimal("10000"))
        out.append(IndexPathEntry(period=t, value=v))
    return out


def arm_path(
    base_arm_request: ARMRequest,
    paths: Sequence[RatePath],
) -> tuple[list[StressRow], ScenarioSummary]:
    """STRS-03 + ROADMAP SC-3: simulate each named rate-path.

    Returns ``(rows, summary)``. Each row carries ``total_interest`` +
    ``max_payment`` + ``reset_count`` + ``highest_rate`` per path.

    Per D-02-04, ``_synthesize_index_path`` generates one IndexPathEntry per
    reset trigger so the ARMRequest alignment-validator passes
    (lib/arm.py:107-145).
    """
    rows: list[StressRow] = []
    for path in paths:
        index_path = _synthesize_index_path(
            base_arm_request.arm_terms,
            base_arm_request.loan.term_months,
            base_arm_request.assumed_index_rate,
            path,
        )
        syn = base_arm_request.model_copy(update={"index_path": index_path})
        schedule = build_arm_schedule(syn)
        highest_rate = max(
            (e.new_rate for e in schedule.reset_events),
            default=base_arm_request.loan.annual_rate,
        )
        max_payment = max(
            (p.payment for p in schedule.payments),
            default=Decimal("0.00"),
        )
        rows.append(
            StressRow(
                label=path.name,
                total_interest=schedule.total_interest,
                max_payment=max_payment,
                reset_count=len(schedule.reset_events),
                highest_rate=highest_rate,
            )
        )

    # Worst case = highest total_interest (None treated as 0 for total ordering).
    def _row_total(r: StressRow) -> Money:
        return r.total_interest if r.total_interest is not None else Decimal("0")

    worst_label = max(rows, key=_row_total).label if rows else None

    summary = ScenarioSummary(
        table=rows,
        baseline_label=rows[0].label if rows else None,
        worst_case_label=worst_label,
        # Per D-02-05: arm-reset parallel-shift dominance invariant noted for
        # Phase 11+; v1 ships empty.
        stress_invariant_violations=[],
    )
    return rows, summary


# ---------------------------------------------------------------------------
# Engine — top-level dispatcher (cross-plan stub; replaced in later tasks)
# ---------------------------------------------------------------------------


def evaluate(req: StressRequest) -> StressResponse:
    """Dispatch on ``req.mode``; build StressResponse with summary BEFORE rows (D-02).

    The discriminated union ``StressRequest`` narrows the type at validation
    time; here we ``isinstance``-narrow to route to the matching helper. The
    response always carries ``summary`` first then ``rows`` (Pydantic v2
    preserves field-declaration order — D-01-02 SC-5 contract).
    """
    if isinstance(req, RateShockRequest):
        rows, summary = rate_shock(req.loan, req.rates, req.baseline_label)
        return StressResponse(
            mode="rate-shock",
            scenario_count=len(rows),
            summary=summary,
            rows=rows,
        )
    if isinstance(req, IncomeShockRequest):
        rows, summary = income_shock(req.base_request, req.reductions, req.dti_threshold)
        return StressResponse(
            mode="income-shock",
            scenario_count=len(rows),
            summary=summary,
            rows=rows,
        )
    # ArmResetRequest (closed-set discriminator; mypy exhausts via isinstance chain)
    rows, summary = arm_path(req.base_arm_request, req.paths)
    return StressResponse(
        mode="arm-reset",
        scenario_count=len(rows),
        summary=summary,
        rows=rows,
    )
