"""Phase 5 ARM Modeling — full test surface (ARM-01..09 + cross-cutting).

Per Phase 3 D-17 portability + Phase 4 D-13 inheritance: subprocess
invocation only for CLI tests, never `import scripts.arm_simulate`
directly. SCRIPT_PATH is the single constant edited at Phase 10 when
scripts/ relocates to .claude/skills/mortgage-ops/scripts/.

Wave 0 (Plan 05-00) creates ALL 32 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 2 (Plan 05-02 Pydantic models): ARM-01 (3 tests)
- Wave 3 (Plan 05-03 build_arm_schedule): ARM-02..05 (13 tests)
- Wave 4 (Plan 05-04 CLI + helper factor): ARM-08 (8 tests)
- Wave 5 (Plan 05-05 references doc): ARM-09 (3 tests)
- Wave 6 (Plan 05-06 fixtures + oracle): ARM-06, ARM-07, plus cross-cutting (5 tests)

Each xfail decorator carries `strict=True` so a passing test in xfail state
raises XPASS at collection time — the wave that flips it MUST also remove
the decorator. This prevents accidental "fixed but still marked xfail" drift.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from lib.arm import ARMRequest

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "arm_simulate.py"
"""Phase 5 CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""

ARM_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "arm.py"
"""For lazy-import test (D-18 inherited): assert lib.arm is NOT imported by --help."""


def _make_5_1_arm_request(
    principal: str = "400000.00",
    annual_rate: str = "0.065000",
    term_months: int = 360,
    floor_rate: str = "0.030000",
    margin_bps: int = 250,
    initial_cap_bps: int = 500,
    periodic_cap_bps: int = 200,
    lifetime_cap_bps: int = 500,
    assumed_index_rate: str = "0.050000",
    index_path_entries: list[tuple[int, str]] | None = None,
    note_rate: str | None = None,
) -> ARMRequest:
    """Construct a canonical 5/1 ARM ARMRequest for invariant tests.

    Used across the Wave 3 invariant tests + Wave 6 fixture tests. Defaults match
    the canonical scenario in 05-CONTEXT.md D-09 / RESEARCH LM-5 (modest reset
    whose new_rate falls in the open interval, applied_cap == 'none').
    """
    from datetime import date
    from decimal import Decimal

    from lib.arm import ARMRequest, ARMTerms, IndexPathEntry
    from lib.models import Loan

    loan = Loan(
        principal=Decimal(principal),
        annual_rate=Decimal(annual_rate),
        term_months=term_months,
        origination_date=date(2026, 1, 1),
        loan_type="arm",
    )
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=initial_cap_bps,
        periodic_cap_bps=periodic_cap_bps,
        lifetime_cap_bps=lifetime_cap_bps,
        floor_rate=Decimal(floor_rate),
        margin_bps=margin_bps,
        index_series_id="MORTGAGE30US",
        note_rate=Decimal(note_rate) if note_rate is not None else None,
    )
    index_path = [IndexPathEntry(period=p, value=Decimal(v)) for p, v in (index_path_entries or [])]
    return ARMRequest(
        loan=loan,
        arm_terms=terms,
        assumed_index_rate=Decimal(assumed_index_rate),
        index_path=index_path,
    )


# =========================================================================
# ARM-01 (3 stubs) — flipped in Wave 2 (Plan 05-02)
# =========================================================================


def test_arm_terms_field_set() -> None:
    """ARM-01 + ROADMAP SC-1: ARMTerms has 8 explicit fields + REQUIRED floor_rate + optional note_rate."""
    from decimal import Decimal

    from lib.arm import ARMTerms
    from pydantic import ValidationError as _VErr

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


def test_arm_terms_missing_floor_rate_raises() -> None:
    """ARM-01 + D-02: ARMTerms rejects missing floor_rate at construction (no default)."""
    from lib.arm import ARMTerms
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        # Same fields as test_arm_terms_field_set MINUS floor_rate.
        ARMTerms(  # type: ignore[call-arg]
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


def test_note_rate_defaults_to_loan_annual_rate() -> None:
    """ARM-01 + D-02 (engine layer): note_rate=None -> engine treats note_rate=loan.annual_rate
    for lifetime ceiling math.

    Wave 2 (Plan 05-02) verified the model-layer default (note_rate=None). This Wave 3
    test verifies the engine BEHAVIOR: when note_rate is None, lifetime_ceiling is computed
    from loan.annual_rate. We pin this by constructing two requests that differ only in
    note_rate (None vs an explicit value matching loan.annual_rate) and asserting they
    produce identical schedules.
    """
    from lib.arm import build_arm_schedule

    req_none = _make_5_1_arm_request(annual_rate="0.050000", note_rate=None)
    req_explicit = _make_5_1_arm_request(annual_rate="0.050000", note_rate="0.050000")
    sched_none = build_arm_schedule(req_none)
    sched_explicit = build_arm_schedule(req_explicit)

    # Schedules must match exactly (note_rate=None collapses to loan.annual_rate)
    assert len(sched_none.payments) == len(sched_explicit.payments)
    for p_none, p_explicit in zip(sched_none.payments, sched_explicit.payments, strict=True):
        assert p_none.payment == p_explicit.payment
        assert p_none.rate_in_effect == p_explicit.rate_in_effect
        assert p_none.balance == p_explicit.balance

    # Reset events also match
    assert len(sched_none.reset_events) == len(sched_explicit.reset_events)
    for re_none, re_explicit in zip(
        sched_none.reset_events, sched_explicit.reset_events, strict=True
    ):
        assert re_none.new_rate == re_explicit.new_rate
        assert re_none.applied_cap == re_explicit.applied_cap


# =========================================================================
# ARM-02 (4 stubs) — flipped in Wave 6 (fixtures land)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_1_payment_jump_at_61.json"
)
def test_arm_5_1_payment_jump_at_61(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02 + ROADMAP SC-2: 5/1 ARM produces payment-jump at month 61 (not 60, not 62)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_7_1_payment_jump_at_85.json"
)
def test_arm_7_1_payment_jump_at_85(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02: 7/1 ARM (initial=84, reset=12)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_10_1_payment_jump_at_121.json"
)
def test_arm_10_1_payment_jump_at_121(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02: 10/1 ARM (initial=120, reset=12)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_6_payment_jump_at_61_and_67.json"
)
def test_arm_5_6_payment_jump_at_61_and_67(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02 + D-15: 5/6 ARM (initial=60, reset=6) — first reset 61, second 67."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-03 (3 stubs) — flipped in Wave 6
# =========================================================================


def test_reset_formula_locked() -> None:
    """ARM-03 + D-02: clamp(quantize(index+margin), low=floor, high=min(periodic, lifetime)).

    Direct call into the private _compute_new_rate helper to pin the formula. Three scenarios:
    - Modest reset (applied_cap == 'none'): index=0.0525, margin=2.5pp -> fully=0.0775; floor=0.03;
      prior=0.05; periodic_ceiling=0.05+5pp=0.10; note=0.05; lifetime=0.05+5pp=0.10; ceiling=min=0.10.
      new_rate = clamp(0.0775, 0.03, 0.10) = 0.0775 (in the open interval; applied_cap='none').
    - Periodic-bound (applied_cap == 'initial'): make fully_indexed > prior+initial_cap.
      index=0.20 (huge), margin=2.5pp -> fully=0.225; periodic_ceiling=0.05+5pp=0.10;
      lifetime=0.05+5pp=0.10; ceiling=0.10. new_rate=quantize(0.10)=0.10. applied_cap='initial' (epoch_idx==1).
    - Floor-bound (applied_cap == 'floor'): index=0.001, margin=0bps -> fully=0.001; floor=0.03;
      effective_floor=max(0,0.03)=0.03. new_rate=0.03. applied_cap='floor'.
    """
    from decimal import Decimal

    from lib.arm import _compute_new_rate

    # Modest reset
    new_rate, applied_cap, _idx_used = _compute_new_rate(
        prior_rate=Decimal("0.050000"),
        epoch_idx=1,
        period=61,
        req=_make_5_1_arm_request(assumed_index_rate="0.052500"),
        loan_annual_rate=Decimal("0.050000"),
    )
    assert new_rate == Decimal("0.077500"), f"modest reset: {new_rate}"
    assert applied_cap == "none"

    # Periodic-bound (initial_cap_bps) at first reset.
    # Use lifetime_cap=1000 (10pp) so lifetime_ceiling=0.05+0.10=0.15 strictly > periodic_ceiling=0.10.
    # On a tie (lifetime <= periodic) the classifier prefers 'lifetime' per D-10; we need
    # strict periodic < lifetime to exercise the 'initial' branch distinctly.
    new_rate, applied_cap, _ = _compute_new_rate(
        prior_rate=Decimal("0.050000"),
        epoch_idx=1,
        period=61,
        req=_make_5_1_arm_request(
            assumed_index_rate="0.200000",
            margin_bps=250,
            initial_cap_bps=500,
            periodic_cap_bps=200,
            lifetime_cap_bps=1000,  # 10pp — well above initial_cap so periodic strictly binds
        ),
        loan_annual_rate=Decimal("0.050000"),
    )
    # prior 0.05 + initial_cap 500bps (5pp) = 0.10; lifetime = 0.05 + 1000bps = 0.15; ceiling = 0.10.
    assert new_rate == Decimal("0.100000"), f"periodic-bound: {new_rate}"
    assert applied_cap == "initial"

    # Floor-bound
    new_rate, applied_cap, _ = _compute_new_rate(
        prior_rate=Decimal("0.050000"),
        epoch_idx=1,
        period=61,
        req=_make_5_1_arm_request(
            assumed_index_rate="0.001000", margin_bps=0, floor_rate="0.030000"
        ),
        loan_annual_rate=Decimal("0.050000"),
    )
    assert new_rate == Decimal("0.030000"), f"floor-bound: {new_rate}"
    assert applied_cap == "floor"


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_initial_cap_at_first_reset.json"
)
def test_arm_initial_cap_at_first_reset(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-03 + D-02: First-reset uses initial_cap; subsequent uses periodic_cap."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_lifetime_cap_binds.json")
def test_arm_lifetime_cap_binds(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-03: Lifetime cap binds when fully-indexed > note_rate + lifetime_cap."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-04 (1 stub) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_floor_below_margin_blocked.json"
)
def test_arm_floor_below_margin_blocked(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-04 + ROADMAP SC-4: Floor enforcement: new_rate >= max(margin, floor_rate)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-05 (5 stubs) — flipped in Wave 6
# =========================================================================


def test_full_remaining_term_re_amortization() -> None:
    """ARM-05 + D-05: each epoch re-amortizes over the FULL remaining term.

    For epoch 1 (months 61..72), the synthetic Loan must have term_months=300 (loan.term_months - 60),
    not 12 (reset_period_months). Verify by reasoning about the per-payment principal/interest
    split: at month 61 with remaining balance ~$370k and a remaining 300-month term at the new rate,
    the P&I should match a fresh build_schedule of those parameters at month 1.
    """
    from datetime import date

    from lib.amortize import build_schedule
    from lib.arm import build_arm_schedule
    from lib.models import Loan

    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    payments_by_period = {p.period: p for p in schedule.payments}

    # Compute what build_schedule would produce for epoch 1 alone.
    epoch_1_balance_in = payments_by_period[60].balance
    epoch_1_rate = payments_by_period[61].rate_in_effect
    synthetic_remaining_term = req.loan.term_months - 60  # 300 for 30yr 5/1
    synthetic = build_schedule(
        Loan(
            principal=epoch_1_balance_in,
            annual_rate=epoch_1_rate,
            term_months=synthetic_remaining_term,
            origination_date=date(2026, 1, 1),
            loan_type="arm",
        ),
        frequency="monthly",
        biweekly_mode=None,
        extra_principal=(),
    )
    # The first 12 rows of this synthetic = the engine's epoch 1 (months 61..72).
    for i in range(12):
        absolute_period = 61 + i
        engine_p = payments_by_period[absolute_period]
        synthetic_p = synthetic.payments[i]
        assert engine_p.payment == synthetic_p.payment, (
            f"period {absolute_period}: engine payment={engine_p.payment}, synthetic={synthetic_p.payment}"
        )
        assert engine_p.principal == synthetic_p.principal
        assert engine_p.interest == synthetic_p.interest
        assert engine_p.balance == synthetic_p.balance


def test_arm_continuous_period_numbering() -> None:
    """ARM-05 + D-03: Continuous period numbering 1..N; final balance == 0.00."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    # Continuous numbering: payments[i].period == i + 1 for all i
    for i, p in enumerate(schedule.payments):
        assert p.period == i + 1, f"period mismatch at index {i}: got {p.period}"
    # Length matches loan term
    assert len(schedule.payments) == req.loan.term_months
    # Final balance is exactly zero (Phase 3 D-09 cleanup on final epoch)
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert schedule.payments[-1].period == req.loan.term_months


def test_cumulative_totals_continuous_across_resets() -> None:
    """ARM-05 + D-05: cumulative_interest + cumulative_principal continuous across epoch boundaries.

    For every i >= 1: payments[i].cumulative_interest == payments[i-1].cumulative_interest + payments[i].interest.
    Particularly important AT the reset boundary (period 61 in 5/1) — Phase 3 build_schedule resets
    its internal cum_int to zero on the synthetic loan, so the engine MUST add cum_int_carry.
    """
    from lib.arm import build_arm_schedule

    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    payments = schedule.payments
    # Cumulative interest invariant
    assert payments[0].cumulative_interest == payments[0].interest
    for i in range(1, len(payments)):
        expected_cum_int = payments[i - 1].cumulative_interest + payments[i].interest
        # Use exact Decimal equality (no almostEqual)
        assert payments[i].cumulative_interest == expected_cum_int, (
            f"cumulative_interest discontinuity at period {payments[i].period}: "
            f"prev={payments[i - 1].cumulative_interest}, this.interest={payments[i].interest}, "
            f"this.cum_int={payments[i].cumulative_interest}"
        )
    # Final invariant: ARMSchedule.total_interest == payments[-1].cumulative_interest (Phase 1 D-15)
    assert schedule.total_interest == payments[-1].cumulative_interest
    # Continuity at the reset boundary specifically (period 60 -> 61)
    period_60 = next(p for p in payments if p.period == 60)
    period_61 = next(p for p in payments if p.period == 61)
    assert period_61.cumulative_interest == period_60.cumulative_interest + period_61.interest
    assert period_61.cumulative_principal == period_60.cumulative_principal + period_61.principal


def test_non_final_epoch_does_not_zero_balance() -> None:
    """ARM-05 + RESEARCH Q1.2 bear trap: non-final epoch's last sliced row has balance > 0.00.

    If the engine took the discouraged shortcut (synthetic_loan.term_months=reset cadence),
    Phase 3 D-09 cleanup would zero the balance at every epoch's last sliced row — silently
    paying off the loan at every reset. This test pins the bear trap.
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    req = _make_5_1_arm_request()
    schedule = build_arm_schedule(req)
    # 5/1 ARM 30yr: epoch 0 ends at month 60 (last fixed-period payment).
    payments_by_period = {p.period: p for p in schedule.payments}
    # Period 60 is the last sliced row of epoch 0 — its balance MUST be > 0.
    assert payments_by_period[60].balance > Decimal("0.00"), (
        "epoch 0 final row was zeroed — engine took the D-05 forbidden shortcut"
    )
    # Period 72 is the last sliced row of epoch 1 (months 61..72).
    assert payments_by_period[72].balance > Decimal("0.00"), (
        "epoch 1 final row was zeroed — engine took the D-05 forbidden shortcut"
    )
    # Every NON-final period's balance must be > 0
    for p in schedule.payments[:-1]:
        assert p.balance > Decimal("0.00"), (
            f"period {p.period} balance is zero before final period — engine misbehavior"
        )
    # The FINAL period's balance MUST be exactly zero (Phase 3 D-09 cleanup applies HERE only).
    assert schedule.payments[-1].balance == Decimal("0.00")


def test_initial_fixed_period_matches_phase1_oracle(
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ARM-05 + LM-6: First epoch matches Phase 1 oracle ($400k @ 6.5%/30yr -> $2528.27 P&I).

    Direct cross-phase oracle anchor reuse. The initial fixed period (months 1..60)
    must produce identical P&I to Phase 3's _build_fixed_monthly with the same
    Loan(principal=400000, annual_rate=0.065, term_months=360).
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = golden_fixture("computed_400k_30yr")
    req = _make_5_1_arm_request(
        principal=fx["principal"],
        annual_rate=fx["annual_rate"],
        term_months=fx["term_months"],
    )
    schedule = build_arm_schedule(req)
    expected_pi = Decimal(fx["expected_monthly_pi"])
    # Every payment in epoch 0 (months 1..60) must equal the Phase 1 oracle P&I exactly.
    for i in range(60):
        assert schedule.payments[i].payment == expected_pi, (
            f"epoch 0 month {i + 1}: got {schedule.payments[i].payment}, expected {expected_pi}"
        )
    # Last month of fixed period:
    assert schedule.payments[59].rate_in_effect == Decimal(fx["annual_rate"]).quantize(
        Decimal("0.000001")
    )
    assert schedule.payments[59].period == 60


# =========================================================================
# ARM-06 (2 stubs) — flipped in Wave 6 (oracle PDF + JSON ship)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships bankrate + vertex42 5/1 captures"
)
def test_oracle_cross_validation_5_1(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-06 + D-04 [REVISED]: Hand-calc + Bankrate + Vertex42 captures AGREE EXACTLY (5/1)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships AmericU 5/6 disclosure capture"
)
def test_oracle_cross_validation_5_6(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-06 + D-04 [REVISED]: 5/6 ARM oracle — AmericU disclosure cross-validation."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-07 (1 stub) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_1_off_by_one_negative.json"
)
def test_arm_5_1_off_by_one_negative(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-07 + ROADMAP SC-3: month 59 still old AND month 61 already new."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-08 (8 stubs) — flipped in Wave 4 (CLI ships)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships scripts/arm_simulate.py")
def test_cli_smoke_subprocess_round_trip(
    arm_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """ARM-08: CLI subprocess round-trip — write JSON, invoke, parse stdout."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-04 ships lazy-import in scripts/arm_simulate.py"
)
def test_cli_help_does_not_import_lib_arm() -> None:
    """ARM-08 + D-18: --help fast (no lib.arm or numpy_financial import before argparse)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate in scripts/arm_simulate.py"
)
def test_cli_rejects_float_principal(tmp_path: Path) -> None:
    """ARM-08 + D-19/WR-02: CLI rejects JSON-float in loan.principal with 6-key envelope."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate")
def test_cli_rejects_float_assumed_index_rate(tmp_path: Path) -> None:
    """ARM-08 + D-19: CLI rejects JSON-float in assumed_index_rate."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate (deep loc)")
def test_cli_rejects_float_index_path_value(tmp_path: Path) -> None:
    """ARM-08 + D-19: CLI rejects JSON-float in index_path[].value (deep loc through list)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate")
def test_cli_rejects_float_floor_rate(tmp_path: Path) -> None:
    """ARM-08 + D-19: CLI rejects JSON-float in arm_terms.floor_rate."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships uniform envelope")
def test_cli_error_envelope_uniformity(tmp_path: Path) -> None:
    """ARM-08 + D-19/WR-02: float-gate + Pydantic ValidationError emit identical 6-key shape."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-02 ships ARMRequest cross-field validator"
)
def test_cli_misaligned_index_path_period_rejected(tmp_path: Path) -> None:
    """ARM-08 + D-01: CLI surfaces ARMRequest._index_path_periods_align_to_reset_triggers as 6-key envelope."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-09 (3 stubs) — flipped in Wave 5 (references/arm-mechanics.md ships)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-05 ships references/arm-mechanics.md")
def test_arm_mechanics_doc_sections_present() -> None:
    """ARM-09 + D-08: references/arm-mechanics.md exists with all 6 D-08 sections."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 + 05-05 add docstring cite")
def test_arm_terms_docstring_cites_arm_mechanics() -> None:
    """ARM-09 + ROADMAP SC-5: ARMTerms docstring cites references/arm-mechanics.md."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-05 ships corrected D-08 citations")
def test_arm_mechanics_citations() -> None:
    """ARM-09 + D-08 [REVISED]: cites B2-1.4-02 + Freddie 6302.7(b) + CFPB §1951 + AmericU 5/6 disclosure."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# Cross-cutting (2 stubs)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships fixtures covering all 5 Literal values"
)
def test_applied_cap_citation_coverage() -> None:
    """D-10: every applied_cap Literal value (initial/periodic/lifetime/floor/none) exercised by ≥1 fixture."""
    pytest.fail("Wave 0 stub")


def test_arm_teaser_rate() -> None:
    """D-02 + LM-3 (engine layer): teaser-rate ARM uses note_rate as lifetime base.

    loan.annual_rate=0.030 (teaser); note_rate=0.050 (post-teaser). Lifetime ceiling
    measured against note_rate, not loan.annual_rate. Verify by constructing a scenario
    where the lifetime_cap binds: huge index + initial_cap large enough to NOT bind.
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    # Teaser ARM: 3% initial, 5% post-teaser note rate, 5% lifetime cap -> lifetime ceiling = 10%.
    # Without the teaser semantic, lifetime ceiling against loan.annual_rate=0.03 would be 8%.
    req = _make_5_1_arm_request(
        annual_rate="0.030000",  # teaser initial
        note_rate="0.050000",  # post-teaser note rate (lifetime base)
        lifetime_cap_bps=500,  # 5pp
        initial_cap_bps=2000,  # 20pp (large; won't bind)
        periodic_cap_bps=2000,
        floor_rate="0.020000",
        margin_bps=250,
        assumed_index_rate="0.150000",  # huge index -> fully_indexed = 0.175 (above lifetime ceiling)
    )
    schedule = build_arm_schedule(req)
    first_reset = schedule.reset_events[0]
    # Lifetime ceiling = note_rate (0.05) + lifetime_cap_bps/10000 (0.05) = 0.10
    # NOT loan.annual_rate (0.03) + 0.05 = 0.08
    assert first_reset.new_rate == Decimal("0.100000"), (
        f"teaser ARM: lifetime ceiling should be note_rate+lifetime_cap=0.10, got new_rate={first_reset.new_rate}"
    )
    assert first_reset.applied_cap == "lifetime"


# =========================================================================
# Plan 05-02 NEW tests — ARMRequest model_validator at the model layer
# (CLI half ships Wave 4 in test_cli_misaligned_index_path_period_rejected)
# =========================================================================


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

    from lib.arm import ARMRequest, ARMTerms, IndexPathEntry
    from lib.models import Loan
    from pydantic import ValidationError

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
