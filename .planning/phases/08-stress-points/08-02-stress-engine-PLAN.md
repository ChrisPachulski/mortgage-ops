---
phase: 08
plan: 02
type: execute
wave: 2
depends_on: ["08-00", "08-01"]
files_modified:
  - lib/stress.py
  - lib/arm.py  # one-line public-API promotion of _compute_reset_triggers
files_added: []
autonomous: true
requirements: ["STRS-01", "STRS-02", "STRS-03"]
tags:
  - phase-08
  - stress-points
  - engine
must_haves:
  truths:
    - "lib.stress.rate_shock(loan, rates, baseline_label) returns list[StressRow] with monthly_pi exact-to-cent for each rate (closes STRS-01)"
    - "lib.stress.income_shock(base_request, reductions, threshold) returns list[StressRow] with dti_back per reduction and breaches_threshold flag (closes STRS-02)"
    - "lib.stress.arm_path(base_arm_request, paths) returns list[StressRow] with total_interest per path; index_path synthesized for ALL reset triggers in 30yr horizon (closes STRS-03)"
    - "lib.stress.evaluate(req) dispatches on req.mode and assembles full StressResponse with summary table, stress_invariant_violations, and rows"
    - "lib.arm._compute_reset_triggers promoted to public lib.arm.compute_reset_triggers (one-line rename + re-export shim) to avoid Phase 8 importing a private helper"
    - "Phase 5 baseline preserved: all Phase 5 tests still pass (no behavioral change to lib/arm.py)"
    - "5 Wave 0 xfails flipped: rate_shock + income_shock + arm_path canonical + arm_path 30yr + monthly_pi monotone invariant"
---

<objective>
Implement the three Phase 8 stress sweep engines as pure-function helpers + an `evaluate()` dispatcher in lib/stress.py. Each helper is a 5-15 line loop calling Phase 3/4/5 engines per grid cell. Promote `lib.arm._compute_reset_triggers` to public API via a one-line rename + re-export shim so lib/stress.py doesn't import a private name.

This plan closes STRS-01, STRS-02, STRS-03 at the math layer. STRS-04 (CLI) lands in Plan 08-04. Fixture-driven assertions land in Plan 08-05.
</objective>

<context>
@.planning/phases/08-stress-points/08-PATTERNS.md (§Pattern 3, 4)
@.planning/phases/08-stress-points/08-RESEARCH.md (§2, §3, §4)
@lib/stress.py (Plan 08-01 type contract; this plan adds bodies)
@lib/amortize.py (build_schedule entrypoint; Schedule.monthly_pi + Schedule.total_interest)
@lib/affordability.py (evaluate dispatcher; AffordabilityResponse.dti_back + .blocked_by)
@lib/arm.py (build_arm_schedule; _compute_reset_triggers private helper at lib/arm.py:244-259)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Promote _compute_reset_triggers to public API in lib/arm.py</name>
  <files>lib/arm.py</files>
  <action>
    Single-line rename: `_compute_reset_triggers` → `compute_reset_triggers` at lib/arm.py:244 (the def line). Then add a backward-compat alias right after the def block:

    ```python
    # Backward compat: keep the underscore-prefixed name as an alias for in-module callers.
    _compute_reset_triggers = compute_reset_triggers
    ```

    Update the one in-module call site (`triggers = _compute_reset_triggers(terms, loan.term_months)` at lib/arm.py:380) — it will resolve via the alias, but for hygiene replace with the public name.

    Update the docstring of `compute_reset_triggers` to add: "Public per Phase 8 D-02-01 (08-02 plan): lib/stress.py imports this for ARM-reset path synthesis. Was private until Phase 8."

    Mirrors Phase 5 D-14 quantize_rate promotion exactly (private-to-public via single rename + alias).
  </action>
  <acceptance_criteria>
    - `grep -c 'def compute_reset_triggers' lib/arm.py` returns 1
    - `grep -c '_compute_reset_triggers = compute_reset_triggers' lib/arm.py` returns 1
    - `python -c "from lib.arm import compute_reset_triggers; print(compute_reset_triggers.__doc__[:50])"` succeeds
    - All Phase 5 tests still pass (no behavioral change): `pytest tests/test_arm.py -q` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Implement lib.stress.rate_shock</name>
  <files>lib/stress.py</files>
  <action>
    Add this private helper to lib/stress.py (Wave 1 left a stub; this fills the rate-shock path):

    ```python
    from collections.abc import Sequence
    from lib.amortize import build_schedule
    from lib.money import quantize_cents, quantize_rate


    def rate_shock(
        loan: Loan,
        rates: Sequence[Rate],
        baseline_label: str | None = None,
    ) -> tuple[list[StressRow], ScenarioSummary]:
        """STRS-01 + ROADMAP SC-1: re-solve PMT for each rate in the grid.

        Returns (rows, summary). Each row carries monthly_pi + total_interest +
        delta_vs_baseline_monthly + delta_vs_baseline_pct (the last two computed
        relative to the baseline_label cell, defaulting to rates[0]).

        stress_invariant_violations appends "RATE_SHOCK_MONOTONE_PI" if monthly_pi
        does NOT strictly increase as rate strictly increases (Phase 3 engine bug
        signal per 08-RESEARCH §6.4).
        """
        rows: list[StressRow] = []
        for rate in rates:
            syn_loan = loan.model_copy(update={"annual_rate": rate})
            schedule = build_schedule(syn_loan, frequency="monthly")
            rows.append(StressRow(
                label=str(rate),
                monthly_pi=schedule.monthly_pi,
                total_interest=schedule.total_interest,
            ))
        # Resolve baseline
        if baseline_label is None:
            baseline_label = rows[0].label
        baseline_row = next((r for r in rows if r.label == baseline_label), rows[0])
        baseline_pi = baseline_row.monthly_pi
        assert baseline_pi is not None  # mypy narrow
        # Fill deltas
        enriched: list[StressRow] = []
        for r in rows:
            assert r.monthly_pi is not None  # mypy narrow
            delta_m = quantize_cents(r.monthly_pi - baseline_pi)
            delta_pct = quantize_rate(
                (r.monthly_pi - baseline_pi) / baseline_pi
            ) if baseline_pi > Decimal("0") else Decimal("0.000000")
            enriched.append(r.model_copy(update={
                "delta_vs_baseline_monthly": delta_m,
                "delta_vs_baseline_pct": delta_pct,
            }))
        # Invariants
        violations: list[str] = []
        sorted_pairs = sorted(zip(rates, [r.monthly_pi for r in rows]), key=lambda p: p[0])
        for i in range(1, len(sorted_pairs)):
            r_lo, pi_lo = sorted_pairs[i-1]
            r_hi, pi_hi = sorted_pairs[i]
            if r_hi > r_lo and pi_hi is not None and pi_lo is not None and pi_hi <= pi_lo:
                violations.append("RATE_SHOCK_MONOTONE_PI")
                break
        # Worst case = highest monthly_pi
        worst = max(enriched, key=lambda r: r.monthly_pi or Decimal("0"))
        summary = ScenarioSummary(
            table=enriched,
            baseline_label=baseline_label,
            worst_case_label=worst.label,
            stress_invariant_violations=violations,
        )
        return enriched, summary
    ```
  </action>
  <acceptance_criteria>
    - `grep -c 'def rate_shock' lib/stress.py` returns 1
    - mypy --strict lib/stress.py exits 0
    - Smoke: `python -c "from decimal import Decimal; from datetime import date; from lib.models import Loan; from lib.stress import rate_shock; loan = Loan(principal=Decimal('400000.00'), annual_rate=Decimal('0.065000'), term_months=360, origination_date=date(2026, 1, 1), loan_type='conventional'); rows, summary = rate_shock(loan, [Decimal('0.06'), Decimal('0.065'), Decimal('0.07')]); print([r.monthly_pi for r in rows])"` prints three Decimal monthly_pi values, monotone increasing
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Implement lib.stress.income_shock</name>
  <files>lib/stress.py</files>
  <action>
    Add to lib/stress.py:

    ```python
    from lib.affordability import evaluate as affordability_evaluate


    def income_shock(
        base_request: AffordabilityRequest,
        reductions: Sequence[Rate],
        dti_threshold: Rate,
    ) -> tuple[list[StressRow], ScenarioSummary]:
        """STRS-02 + ROADMAP SC-2: recompute back-end DTI for each reduction.

        Per 08-RESEARCH §3.3: scale each applicant's gross_monthly_income by
        (1 - reduction); call lib.affordability.evaluate; capture dti_back +
        breach flag (dti_back > dti_threshold).
        """
        rows: list[StressRow] = []
        for reduction in reductions:
            multiplier = Decimal("1") - reduction
            shocked_household = base_request.household.model_copy(update={
                "applicants": [
                    a.model_copy(update={
                        "gross_monthly_income": quantize_cents(a.gross_monthly_income * multiplier)
                    })
                    for a in base_request.household.applicants
                ]
            })
            shocked = base_request.model_copy(update={"household": shocked_household})
            response = affordability_evaluate(shocked)
            rows.append(StressRow(
                label=f"-{int(reduction * 100)}%",
                dti_back=response.dti_back,
                breaches_threshold=response.dti_back > dti_threshold,
                blocked_by=response.blocked_by,
            ))
        # Worst case = highest dti_back
        worst = max(rows, key=lambda r: r.dti_back or Decimal("0"))
        summary = ScenarioSummary(
            table=rows,
            baseline_label=rows[0].label if rows else None,
            worst_case_label=worst.label,
            stress_invariant_violations=[],  # invariants for income-shock TBD Phase 11+
        )
        return rows, summary
    ```
  </action>
  <acceptance_criteria>
    - `grep -c 'def income_shock' lib/stress.py` returns 1
    - mypy --strict lib/stress.py exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Implement lib.stress.arm_path + index_path synthesis</name>
  <files>lib/stress.py</files>
  <action>
    Add to lib/stress.py:

    ```python
    from lib.arm import IndexPathEntry, compute_reset_triggers, build_arm_schedule, ARMTerms


    def _synthesize_index_path(
        arm_terms: ARMTerms,
        term_months: int,
        base_index: Rate,
        path: RatePath,
    ) -> list[IndexPathEntry]:
        """08-RESEARCH §4.2 algorithm. Returns one IndexPathEntry per reset trigger."""
        triggers = compute_reset_triggers(arm_terms, term_months)
        if path.name == "parallel-shift":
            shift = path.params["shift_bps"]
            return [
                IndexPathEntry(period=t, value=quantize_rate(base_index + Decimal(shift) / Decimal("10000")))
                for t in triggers
            ]
        if path.name == "gradual-rise":
            step = path.params["step_bps"]
            return [
                IndexPathEntry(period=t, value=quantize_rate(base_index + Decimal(k * step) / Decimal("10000")))
                for k, t in enumerate(triggers)
            ]
        # fall-then-rise
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
        """STRS-03 + ROADMAP SC-3: simulate each named rate-path; return total_interest_paid + max_payment + reset_count + highest_rate per path."""
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
            highest_rate = max((e.new_rate for e in schedule.reset_events), default=base_arm_request.loan.annual_rate)
            max_payment = max((p.payment for p in schedule.payments), default=Decimal("0.00"))
            rows.append(StressRow(
                label=path.name,
                total_interest=schedule.total_interest,
                max_payment=max_payment,
                reset_count=len(schedule.reset_events),
                highest_rate=highest_rate,
            ))
        worst = max(rows, key=lambda r: r.total_interest or Decimal("0"))
        summary = ScenarioSummary(
            table=rows,
            baseline_label=rows[0].label if rows else None,
            worst_case_label=worst.label,
            stress_invariant_violations=[],
        )
        return rows, summary
    ```
  </action>
  <acceptance_criteria>
    - `grep -c 'def arm_path' lib/stress.py` returns 1
    - `grep -c 'def _synthesize_index_path' lib/stress.py` returns 1
    - mypy --strict lib/stress.py exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 5: Implement lib.stress.evaluate dispatcher</name>
  <files>lib/stress.py</files>
  <action>
    Replace the NotImplementedError stub from Plan 08-01 with the real dispatcher:

    ```python
    def evaluate(req: StressRequest) -> StressResponse:
        """Dispatch on req.mode; build StressResponse with summary BEFORE rows (D-02)."""
        if isinstance(req, RateShockRequest):
            rows, summary = rate_shock(req.loan, req.rates, req.baseline_label)
            return StressResponse(mode="rate-shock", scenario_count=len(rows), summary=summary, rows=rows)
        if isinstance(req, IncomeShockRequest):
            rows, summary = income_shock(req.base_request, req.reductions, req.dti_threshold)
            return StressResponse(mode="income-shock", scenario_count=len(rows), summary=summary, rows=rows)
        # ArmResetRequest
        rows, summary = arm_path(req.base_arm_request, req.paths)
        return StressResponse(mode="arm-reset", scenario_count=len(rows), summary=summary, rows=rows)
    ```
  </action>
  <acceptance_criteria>
    - `grep -c 'def evaluate' lib/stress.py` returns 1 (the real dispatcher; the stub is gone)
    - `grep -c 'NotImplementedError' lib/stress.py` returns 0
    - Smoke: `python -c "from decimal import Decimal; from datetime import date; from lib.models import Loan; from lib.stress import evaluate, RateShockRequest; loan = Loan(principal=Decimal('400000.00'), annual_rate=Decimal('0.065000'), term_months=360, origination_date=date(2026, 1, 1), loan_type='conventional'); req = RateShockRequest(loan=loan, rates=[Decimal('0.06'), Decimal('0.07')]); resp = evaluate(req); print(resp.scenario_count, resp.summary.worst_case_label)"` prints `2 0.07`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 6: Flip 5 Wave 0 xfails (engine smoke tests)</name>
  <files>tests/test_stress.py</files>
  <action>
    Flip these 5 tests from xfail to real in-process assertions (do NOT add fixture loads — those land in Plan 08-05). Use synthesized requests:
    - `test_rate_shock_per_cell_calls_phase3_engine_exact_to_cent` — construct a 3-rate sweep on $400k/30yr; assert each row's `monthly_pi` equals the Phase 3 oracle (rate 0.065 → "2528.27"); assert all values are quantized to 2 decimal places (e.g., `monthly_pi.as_tuple().exponent == -2`).
    - `test_income_shock_per_cell_calls_phase4_engine_with_threshold_breach` — construct a 2-reduction sweep [0.0, 0.50] on a baseline AffordabilityRequest with a marginal DTI; assert reduction=0.0 row matches baseline dti_back exactly; reduction=0.50 row has higher dti_back AND breaches_threshold==True at threshold=0.43.
    - `test_arm_path_three_canonical_paths_total_interest` — construct 5/1 ARM 30yr request + three canonical paths; assert all three rows return positive `total_interest` and that parallel-shift's total_interest > fall-then-rise's total_interest (sanity ordering).
    - `test_arm_path_30yr_horizon_reset_count` — same 5/1 ARM 30yr; assert all rows have reset_count == 25 (one per reset trigger from 61, 73, ..., 349).
    - `test_sc5_stress_invariants_monthly_pi_monotone_in_rate` — run a 4-rate sweep; assert response.summary.stress_invariant_violations == [] for monotone-increasing rates.

    Remove the @pytest.mark.xfail decorator on all five.
  </action>
  <acceptance_criteria>
    - `grep -c '@pytest.mark.xfail' tests/test_stress.py` returns 6 (was 11 after Plan 08-01; 5 more flipped)
    - `pytest tests/test_stress.py -v --tb=short` shows 7 passed (the 2 from Plan 08-01 + 5 new) and 6 xfailed
    - Full suite: ≥418 passed, ≥11 xfailed (16 from Plan 08-01 minus 5), 0 failed, 0 errored
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- D-02-01: Promote `_compute_reset_triggers` → `compute_reset_triggers` (public) in lib/arm.py via single-line rename + backward-compat alias. Mirrors Phase 5 D-14 `quantize_rate` promotion. Avoids Phase 8 importing a private name.
- D-02-02: rate_shock uses `loan.model_copy(update={"annual_rate": rate})` — Pydantic v2's frozen-model update idiom. Verified by Phase 4 reverse-mode flow.
- D-02-03: income_shock applies the reduction PER-APPLICANT (each applicant's gross_monthly_income is scaled). Phase 4 D-06 sum aggregation means proportional cuts produce a proportionally-cut total. Documented in 08-RESEARCH §3.3.
- D-02-04: arm_path._synthesize_index_path generates one IndexPathEntry per reset trigger — every trigger MUST be covered (alignment-validator on ARMRequest enforces this; misalignment would be a Plan-08-02 bug, not a runtime issue).
- D-02-05: stress_invariant_violations populated ONLY for rate-shock monotone-pi check in v1. Other invariants (income-shock dti monotone, arm-reset parallel-shift dominance) are NOTED in 08-RESEARCH §6.4 for Phase 11+ expansion. Empty list in income-shock and arm-reset paths is intentional.
- D-02-06: model_copy on AffordabilityRequest preserves the discriminated-union type because Pydantic v2 preserves the runtime type of the source object. Verified by Phase 4 fixture tests using the same idiom.
</locked_decisions>

<verify_block>
- All five Phase 8 engine functions defined and importable: rate_shock, income_shock, arm_path, _synthesize_index_path, evaluate
- compute_reset_triggers public; backward-compat alias preserves Phase 5 internal callers
- Phase 5 baseline preserved (zero behavioral change to lib/arm.py — only the rename is observable, and the alias preserves the old name)
- 5 Wave 0 xfails flipped (engine smoke); 6 remaining (4 CLI + 2 SC-5 fixture-driven, all flipped in Plans 08-04 and 08-05)
- mypy --strict lib/stress.py lib/arm.py exits 0
- ruff clean
</verify_block>

<deviation_rules>
- Rule 1: If `loan.model_copy(update={...})` triggers a Pydantic re-validation that wasn't expected, document the workaround (e.g., dump-then-reconstruct via TypeAdapter); pin the rationale in SUMMARY.md.
- Rule 2: If income_shock's per-applicant scaling produces a household with zero applicants somehow, that's a STOP — Plan 08-01 model contract should have prevented this; treat as a Plan 08-01 gap.
- Rule 3: arm_path's path-name mapping is a closed set (D-01-05). If a future caller wants a custom path, they extend RatePath.name Literal — NOT this dispatcher.
</deviation_rules>

<success_criteria>
- STRS-01, STRS-02, STRS-03 closed at the math layer (CLI closure happens in Plan 08-04; fixture-driven closure in Plan 08-05)
- 5 Wave 0 xfails flipped
- mypy + ruff clean across lib/stress.py and lib/arm.py
- Phase 5 test suite preserved (no regression from compute_reset_triggers rename)
- 08-RESEARCH §2/§3/§4 algorithms implemented verbatim
</success_criteria>
