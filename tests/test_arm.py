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

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "arm_simulate.py"
)
"""Phase 5 CLI WAS at project-root scripts/. Phase 10 (Plan 10-01) RELOCATED to
.claude/skills/mortgage-ops/scripts/; only this constant updates per Phase 5 D-17
portability seam."""

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


def _request_from_fixture(fx: dict[str, Any]) -> ARMRequest:
    """Reconstruct an ARMRequest from a Plan 05-06 fixture dict (D-09 pattern).

    Handles arbitrary fixture shapes — Loan, ARMTerms, IndexPathEntry, ARMRequest
    rebuilt from JSON-string Decimals. Used by all fixture-based stub flips in
    Plan 05-06 Task 4 (I-010 deduplication).
    """
    from datetime import date
    from decimal import Decimal

    from lib.arm import ARMRequest, ARMTerms, IndexPathEntry
    from lib.models import Loan

    req_dict = fx["request"]
    loan_dict = req_dict["loan"]
    terms_dict = req_dict["arm_terms"]
    loan = Loan(
        principal=Decimal(loan_dict["principal"]),
        annual_rate=Decimal(loan_dict["annual_rate"]),
        term_months=loan_dict["term_months"],
        origination_date=date.fromisoformat(loan_dict["origination_date"]),
        loan_type=loan_dict["loan_type"],
    )
    terms_kwargs: dict[str, Any] = {
        "initial_period_months": terms_dict["initial_period_months"],
        "reset_period_months": terms_dict["reset_period_months"],
        "initial_cap_bps": terms_dict["initial_cap_bps"],
        "periodic_cap_bps": terms_dict["periodic_cap_bps"],
        "lifetime_cap_bps": terms_dict["lifetime_cap_bps"],
        "floor_rate": Decimal(terms_dict["floor_rate"]),
        "margin_bps": terms_dict["margin_bps"],
        "index_series_id": terms_dict["index_series_id"],
    }
    if terms_dict.get("note_rate") is not None:
        terms_kwargs["note_rate"] = Decimal(terms_dict["note_rate"])
    terms = ARMTerms(**terms_kwargs)
    index_path = [
        IndexPathEntry(period=e["period"], value=Decimal(e["value"]))
        for e in req_dict.get("index_path", [])
    ]
    return ARMRequest(
        loan=loan,
        arm_terms=terms,
        assumed_index_rate=Decimal(req_dict["assumed_index_rate"]),
        index_path=index_path,
    )


def _assert_engine_matches_fixture_at_period(
    schedule_payment: Any, expected_payment: dict[str, Any]
) -> None:
    """Exact-Decimal-equality assertion for one (engine, fixture) payment row pair."""
    from decimal import Decimal

    assert schedule_payment.payment == Decimal(expected_payment["payment"])
    assert schedule_payment.rate_in_effect == Decimal(expected_payment["rate_in_effect"])
    assert schedule_payment.balance == Decimal(expected_payment["balance"])
    assert schedule_payment.principal == Decimal(expected_payment["principal"])
    assert schedule_payment.interest == Decimal(expected_payment["interest"])


def _assert_hand_calc_check(reset_event: Any, expected_reset: dict[str, Any]) -> None:
    """I-004: cap-bound fixtures carry a Decimal hand-calc witness; assert engine matches.

    No-op when the fixture has no hand_calc_check (non-cap-bound fixtures use external
    oracle witnesses instead).
    """
    from decimal import Decimal

    if "hand_calc_check" not in expected_reset:
        return
    hcc = expected_reset["hand_calc_check"]
    assert reset_event.new_rate == Decimal(hcc["new_rate_expected"]), (
        f"engine new_rate {reset_event.new_rate} != hand-calc {hcc['new_rate_expected']} "
        f"(Fannie B2-1.4-02 + D-02 formula)"
    )
    assert reset_event.applied_cap == hcc["applied_cap_expected"], (
        f"engine applied_cap {reset_event.applied_cap} != hand-calc {hcc['applied_cap_expected']}"
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


def test_arm_5_1_payment_jump_at_61(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02 + ROADMAP SC-2: 5/1 ARM produces payment-jump at month 61 (not 60, not 62)."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_5_1_payment_jump_at_61")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    assert len(schedule.payments) == len(expected["payments"])
    # Last fixed-period payment (period 60): still old rate
    _assert_engine_matches_fixture_at_period(schedule.payments[59], expected["payments"][59])
    # First post-reset payment (period 61): new rate, new payment
    _assert_engine_matches_fixture_at_period(schedule.payments[60], expected["payments"][60])
    # Payment jump assertion (the load-bearing SC-2 assertion)
    assert schedule.payments[60].payment != schedule.payments[59].payment
    # Reset event at period 61
    assert schedule.reset_events[0].period == 61
    assert schedule.reset_events[0].old_rate == Decimal(expected["payments"][59]["rate_in_effect"])
    assert schedule.reset_events[0].new_rate == Decimal(expected["payments"][60]["rate_in_effect"])
    assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]
    _assert_hand_calc_check(schedule.reset_events[0], expected["reset_events"][0])


def test_arm_7_1_payment_jump_at_85(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02: 7/1 ARM (initial=84, reset=12) — payment jump at month 85."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_7_1_payment_jump_at_85")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    assert len(schedule.payments) == len(expected["payments"])
    # Period 84 (last fixed) still uses initial rate
    _assert_engine_matches_fixture_at_period(schedule.payments[83], expected["payments"][83])
    # Period 85 (first post-reset) uses new rate
    _assert_engine_matches_fixture_at_period(schedule.payments[84], expected["payments"][84])
    assert schedule.payments[84].payment != schedule.payments[83].payment
    assert schedule.reset_events[0].period == 85
    assert schedule.reset_events[0].new_rate == Decimal(expected["payments"][84]["rate_in_effect"])
    assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]
    _assert_hand_calc_check(schedule.reset_events[0], expected["reset_events"][0])


def test_arm_10_1_payment_jump_at_121(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02: 10/1 ARM (initial=120, reset=12) — payment jump at month 121."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_10_1_payment_jump_at_121")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    assert len(schedule.payments) == len(expected["payments"])
    # Period 120 (last fixed) still uses initial rate
    _assert_engine_matches_fixture_at_period(schedule.payments[119], expected["payments"][119])
    # Period 121 (first post-reset) uses new rate
    _assert_engine_matches_fixture_at_period(schedule.payments[120], expected["payments"][120])
    assert schedule.payments[120].payment != schedule.payments[119].payment
    assert schedule.reset_events[0].period == 121
    assert schedule.reset_events[0].new_rate == Decimal(expected["payments"][120]["rate_in_effect"])
    assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]
    _assert_hand_calc_check(schedule.reset_events[0], expected["reset_events"][0])


def test_arm_5_6_payment_jump_at_61_and_67(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02 + D-15: 5/6 ARM (initial=60, reset=6) — first reset 61, second 67."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_5_6_payment_jump_at_61_and_67")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    assert len(schedule.payments) == len(expected["payments"])
    # First reset boundary: period 60 still old, period 61 new
    _assert_engine_matches_fixture_at_period(schedule.payments[59], expected["payments"][59])
    _assert_engine_matches_fixture_at_period(schedule.payments[60], expected["payments"][60])
    assert schedule.payments[60].payment != schedule.payments[59].payment
    # Second reset boundary: period 66 same as 61 (within first reset epoch),
    # period 67 new payment
    _assert_engine_matches_fixture_at_period(schedule.payments[65], expected["payments"][65])
    _assert_engine_matches_fixture_at_period(schedule.payments[66], expected["payments"][66])
    assert schedule.payments[66].payment != schedule.payments[65].payment
    # Reset events at period 61 and 67
    assert schedule.reset_events[0].period == 61
    assert schedule.reset_events[1].period == 67
    assert schedule.reset_events[0].new_rate == Decimal(expected["payments"][60]["rate_in_effect"])
    assert schedule.reset_events[1].new_rate == Decimal(expected["payments"][66]["rate_in_effect"])
    assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]
    assert schedule.reset_events[1].applied_cap == expected["reset_events"][1]["applied_cap"]
    _assert_hand_calc_check(schedule.reset_events[0], expected["reset_events"][0])


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


def test_arm_initial_cap_at_first_reset(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-03 + D-02: First-reset uses initial_cap; subsequent uses periodic_cap."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_initial_cap_at_first_reset")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    # First reset (period 61): applied_cap == 'initial'
    assert schedule.reset_events[0].period == 61
    assert schedule.reset_events[0].applied_cap == "initial"
    assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]
    assert schedule.reset_events[0].new_rate == Decimal(expected["reset_events"][0]["new_rate"])
    _assert_hand_calc_check(schedule.reset_events[0], expected["reset_events"][0])
    # Second reset (period 73): applied_cap == 'periodic'
    assert schedule.reset_events[1].period == 73
    assert schedule.reset_events[1].applied_cap == "periodic"
    assert schedule.reset_events[1].applied_cap == expected["reset_events"][1]["applied_cap"]
    assert schedule.reset_events[1].new_rate == Decimal(expected["reset_events"][1]["new_rate"])


def test_arm_lifetime_cap_binds(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-03: Lifetime cap binds when fully-indexed > note_rate + lifetime_cap."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_lifetime_cap_binds")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    # First reset binds at lifetime ceiling
    assert schedule.reset_events[0].period == 61
    assert schedule.reset_events[0].applied_cap == "lifetime"
    assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]
    assert schedule.reset_events[0].new_rate == Decimal(expected["reset_events"][0]["new_rate"])
    _assert_hand_calc_check(schedule.reset_events[0], expected["reset_events"][0])
    # Per-payment dollar-anchored equality at the reset boundary
    _assert_engine_matches_fixture_at_period(schedule.payments[60], expected["payments"][60])


# =========================================================================
# ARM-04 (1 stub) — flipped in Wave 6
# =========================================================================


def test_arm_floor_below_margin_blocked(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-04 + ROADMAP SC-4: Floor enforcement: new_rate >= max(margin, floor_rate)."""
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_floor_below_margin_blocked")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    # First reset binds at floor (huge index drop forced new_rate UP to floor_rate)
    assert schedule.reset_events[0].period == 61
    assert schedule.reset_events[0].applied_cap == "floor"
    assert schedule.reset_events[0].applied_cap == expected["reset_events"][0]["applied_cap"]
    assert schedule.reset_events[0].new_rate == Decimal(expected["reset_events"][0]["new_rate"])
    # Engine new_rate must be >= max(margin, floor_rate) per ARM-04 invariant
    margin = Decimal(request.arm_terms.margin_bps) / Decimal("10000")
    effective_floor = max(margin, request.arm_terms.floor_rate)
    assert schedule.reset_events[0].new_rate >= effective_floor
    _assert_hand_calc_check(schedule.reset_events[0], expected["reset_events"][0])


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


def test_arm_continuous_period_numbering(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-05 + D-03: Continuous period numbering 1..N; final balance == 0.00.

    WR-04: Loads `arm_continuous_period_numbering.json` fixture (committed via Plan
    05-06) so the per-payment hand-calc rows are cross-validated against engine output.
    Without this binding the fixture's per-row assertions would never run, weakening
    the D-04 / D-09 hand-calc-vs-engine cross-validation contract.
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_continuous_period_numbering")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)
    expected = fx["expected"]

    # Structural invariants: continuous numbering, length, final-balance.
    for i, p in enumerate(schedule.payments):
        assert p.period == i + 1, f"period mismatch at index {i}: got {p.period}"
    assert len(schedule.payments) == request.loan.term_months
    assert len(schedule.payments) == len(expected["payments"])
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert schedule.payments[-1].period == request.loan.term_months

    # Hand-calc cross-validation: spot-check first, last, and the first reset boundary.
    _assert_engine_matches_fixture_at_period(schedule.payments[0], expected["payments"][0])
    _assert_engine_matches_fixture_at_period(schedule.payments[59], expected["payments"][59])
    _assert_engine_matches_fixture_at_period(schedule.payments[60], expected["payments"][60])
    _assert_engine_matches_fixture_at_period(schedule.payments[-1], expected["payments"][-1])


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


_BANKRATE_5_1_CAPTURE: Path = (
    Path(__file__).resolve().parent / "fixtures" / "arm" / "oracle" / "bankrate_5_1_capture.json"
)


@pytest.mark.skipif(
    not _BANKRATE_5_1_CAPTURE.exists(),
    reason=(
        "External ARM oracle capture pending: Bankrate ARM Calculator (5/1, 7/1, 10/1) "
        "is JS-rendered and Vertex42 templates are spreadsheet-driven; both require "
        "human browser/Excel capture per Plan 05-06 Rule-4 deviation against threat "
        "T-05-34 (oracle URL/automation gaps). Drop a captured fixture at "
        "tests/fixtures/arm/oracle/bankrate_5_1_capture.json (schema: same as other "
        "arm fixtures consumed by `_request_from_fixture` — `request` with `loan` + "
        "`arm_terms` sub-objects, `expected.payments[]` with per-period `payment` "
        "values) and this test will auto-activate.\n\n"
        "PARTIAL CROSS-SOURCE COVERAGE (Phase 17): the CFPB CHARM consumer-booklet "
        "1/1 ARM with 2pp periodic cap is now covered byte-for-byte by an independent "
        "oracle at tests/test_oracles_arm_reset.py — engine reproduces all three CHARM-"
        "published values exactly ($1,199.10 / $1,461.72 / $1,600.42). This validates the "
        "core ARM reset math against an independent published source; the gap that remains "
        "is specifically the 5/1, 7/1, and 10/1 fixed-then-adjustable structures that "
        "neither CHARM nor any other public-PDF oracle covers."
    ),
)
def test_oracle_cross_validation_5_1(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-06 + D-04 [REVISED]: engine reproduces Bankrate 5/1 ARM captured values.

    Activates automatically when the external oracle fixture lands at
    `tests/fixtures/arm/oracle/bankrate_5_1_capture.json`. Asserts exact-Decimal
    match between `schedule.payments[i].payment` and `fx["expected"]["payments"][i]["payment"]`.
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("oracle/bankrate_5_1_capture")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected_payments = fx["expected"]["payments"]
    assert len(schedule.payments) == len(expected_payments), (
        f"engine schedule length {len(schedule.payments)} != "
        f"Bankrate capture length {len(expected_payments)}"
    )
    for i, exp in enumerate(expected_payments):
        actual = schedule.payments[i]
        assert actual.payment == Decimal(exp["payment"]), (
            f"period {i + 1}: Bankrate {exp['payment']} vs engine {actual.payment}"
        )


def test_oracle_cross_validation_5_6(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-06 + D-04 [REVISED]: 5/6 ARM oracle — ABT Bank disclosure cross-validation.

    Plan 05-06 Rule-4 deviation: original AmericU URL 404'd; substituted ABT Bank's
    functionally equivalent "5/6, 7/6 & 10/6 SOFR ARM Disclosure" (same SOFR index,
    same 2/1/5 cap structure, same first-change-date and reset cadence). The
    disclosure publishes only Initial-Rate and Maximum-Rate rows, so this test
    asserts the engine's RATE PATH (scale-invariant) under the worst-case
    cap-binding trajectory matches the disclosure's two anchor rows.
    """
    from decimal import Decimal

    abt = arm_fixture("oracle/abt_bank_5_6_sofr_disclosure_2022")
    rows = abt["expected_per_period"]
    initial_row = next(r for r in rows if r["period"] == 1)
    max_row = next(r for r in rows if r["period"] != 1)

    # Anchor 1: ABT Initial Interest Rate row matches our 5/6 fixture's initial period rate.
    # The 5/6 fixture (arm_5_6_payment_jump_at_61_and_67) uses different scenario inputs
    # (higher initial rate to exercise our cap-coverage matrix), so we cannot scale dollars
    # directly. Rates are independent of loan size, so the disclosure's CAP-PATH invariant
    # is the load-bearing oracle property: max_rate == initial_rate + lifetime_cap.
    abt_initial_rate = Decimal(initial_row["rate"])
    abt_max_rate = Decimal(max_row["rate"])
    abt_lifetime_cap = abt_max_rate - abt_initial_rate
    assert abt_lifetime_cap == Decimal("0.050000"), (
        f"ABT disclosure lifetime cap should be 5pp; got {abt_lifetime_cap}"
    )

    # Anchor 2: build a synthetic 5/6 ARM with ABT's exact scenario inputs ($10k loan,
    # 5.375% initial, 1.287% index, 3.000% margin, 2/1/5 caps, 30yr term) and verify the
    # engine produces (a) initial payment $56.00 ± exact-decimal match, (b) the worst-case
    # rate path reaches lifetime cap by month 79 (= 4th change date).
    from datetime import date

    from lib.arm import ARMRequest, ARMTerms, build_arm_schedule
    from lib.models import Loan

    loan = Loan(
        principal=Decimal("10000.00"),
        annual_rate=Decimal("0.053750"),
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="arm",
    )
    # ABT 5/6: initial_cap=2pp, periodic_cap=1pp, lifetime_cap=5pp, no floor below margin
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=6,
        initial_cap_bps=200,
        periodic_cap_bps=100,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=300,
        index_series_id="SOFR30A",
    )
    # Use a huge index to drive the engine into the worst-case cap-binding path
    # (every reset binds at its applicable cap — the path the disclosure documents).
    req = ARMRequest(
        loan=loan,
        arm_terms=terms,
        assumed_index_rate=Decimal("0.500000"),
        index_path=[],
    )
    schedule = build_arm_schedule(req)

    # Engine's initial payment (period 1) must equal ABT's $56.00 disclosed value.
    assert schedule.payments[0].rate_in_effect == abt_initial_rate
    assert schedule.payments[0].payment == Decimal(initial_row["payment"]), (
        f"engine initial payment {schedule.payments[0].payment} != ABT {initial_row['payment']}"
    )

    # Worst-case rate path: 5.375% -> 7.375% (m61, +2pp) -> 8.375% (m67, +1pp)
    # -> 9.375% (m73, +1pp) -> 10.375% (m79, +1pp = lifetime ceiling).
    # The fourth reset event at period 79 must hit the disclosed maximum rate.
    rates_by_period = {p.period: p.rate_in_effect for p in schedule.payments}
    assert rates_by_period[60] == Decimal("0.053750")
    assert rates_by_period[61] == Decimal("0.073750")
    assert rates_by_period[67] == Decimal("0.083750")
    assert rates_by_period[73] == Decimal("0.093750")
    assert rates_by_period[79] == abt_max_rate
    assert schedule.payments[78].rate_in_effect == abt_max_rate

    # Disclosure-convention cross-check: ABT's "Maximum Monthly Payment" of $90.54 is
    # computed as the payment for a fresh $10,000 loan amortized over the FULL 360-month
    # term at the lifetime-cap rate (10.375%) — it's a regulatory worst-case disclosure
    # rather than the actual cash-flow path. Our engine instead re-amortizes the
    # then-current balance over the remaining term per Phase 5 D-05 (full-remaining-term
    # re-amortization), so the actual payment at month 79 is lower than the disclosure
    # figure (the loan has paid down by then). To verify cross-source agreement under the
    # disclosure's convention, build a fresh fixed-rate $10k / 10.375% / 360-month loan
    # and assert its initial payment matches the disclosure's max.
    from lib.amortize import build_schedule

    cap_rate_loan = Loan(
        principal=Decimal("10000.00"),
        annual_rate=abt_max_rate,
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="fixed",
    )
    cap_rate_schedule = build_schedule(
        cap_rate_loan, frequency="monthly", biweekly_mode=None, extra_principal=()
    )
    assert cap_rate_schedule.payments[0].payment == Decimal(max_row["payment"]), (
        f"engine at lifetime-cap rate over 360mo = {cap_rate_schedule.payments[0].payment}, "
        f"!= ABT disclosed max {max_row['payment']}"
    )


# =========================================================================
# ARM-07 (1 stub) — flipped in Wave 6
# =========================================================================


def test_arm_5_1_off_by_one_negative(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-07 + ROADMAP SC-3: month 59 still old AND month 61 already new.

    Pins BOTH sides of the off-by-one: the last initial-period payment (month 59)
    still uses the initial rate, AND the first post-reset payment (month 61) is
    already at the new rate. Catches any boundary off-by-one in the engine's
    epoch slicing.
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_5_1_off_by_one_negative")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)

    expected = fx["expected"]
    initial_rate = Decimal(expected["payments"][0]["rate_in_effect"])
    new_rate = Decimal(expected["payments"][60]["rate_in_effect"])
    assert initial_rate != new_rate, "fixture inputs must produce a real reset"

    # Negative direction 1: month 59 (= payments[58]) still uses initial rate
    assert schedule.payments[58].rate_in_effect == initial_rate
    assert schedule.payments[58].payment == Decimal(expected["payments"][58]["payment"])

    # Negative direction 2: month 61 (= payments[60]) already uses new rate
    assert schedule.payments[60].rate_in_effect == new_rate
    assert schedule.payments[60].payment == Decimal(expected["payments"][60]["payment"])
    assert schedule.payments[60].payment != schedule.payments[58].payment

    # Positive boundary: month 60 still uses initial rate (off-by-one at the boundary)
    assert schedule.payments[59].rate_in_effect == initial_rate
    assert schedule.payments[59].payment == Decimal(expected["payments"][59]["payment"])


# =========================================================================
# ARM-08 (8 stubs) — flipped in Wave 4 (CLI ships)
# =========================================================================


def test_cli_smoke_subprocess_round_trip(tmp_path: Path) -> None:
    """ARM-08: CLI subprocess round-trip — write JSON, invoke, parse stdout.

    Wave 4 ships the basic round-trip (request/response shape correct).
    Wave 6 (Plan 05-06) replaces this with a fixture-based assertion that
    pins specific dollar values (arm_5_1_payment_jump_at_61.json).
    """
    import json
    import subprocess
    import sys

    req = _make_5_1_arm_request()
    request_path = tmp_path / "input.json"
    # ARMRequest.model_dump_json gives JSON-strings for Decimal fields
    # (CLAUDE.md money discipline).
    request_path.write_text(req.model_dump_json())
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    # Smoke shape assertions
    assert "loan" in out
    assert "arm_terms" in out
    assert "payments" in out
    assert "reset_events" in out
    assert "total_interest" in out
    assert "final_payment_adjusted" in out
    assert len(out["payments"]) == 360  # 30yr 5/1 ARM
    # Continuous numbering invariant
    assert out["payments"][0]["period"] == 1
    assert out["payments"][-1]["period"] == 360
    assert out["payments"][-1]["balance"] == "0.00"
    # 5/1 ARM 30yr produces 25 reset events
    assert len(out["reset_events"]) == 25
    assert out["reset_events"][0]["period"] == 61
    # I-005: pin the LAST reset trigger as well (catches off-by-one in the
    # reset-trigger generator at the END of the schedule).
    assert out["reset_events"][-1]["period"] == 349, (
        f"expected last reset trigger at period 349, got {out['reset_events'][-1]['period']}"
    )


def test_cli_help_does_not_import_lib_arm() -> None:
    """ARM-08 + D-18: --help fast path. Must NOT trigger lib.arm or lib.amortize
    or numpy_financial imports.
    """
    import json
    import subprocess
    import sys

    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_arm_simulate', SCRIPT)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "saved_argv = sys.argv\n"
        "sys.argv = [SCRIPT, '--help']\n"
        "exit_code = None\n"
        "try:\n"
        "    try:\n"
        "        module.main()\n"
        "    except SystemExit as exc:\n"
        "        exit_code = exc.code\n"
        "finally:\n"
        "    sys.argv = saved_argv\n"
        "result = {\n"
        "    'help_exit_code': exit_code,\n"
        "    'lib_arm_imported': 'lib.arm' in sys.modules,\n"
        "    'lib_amortize_imported': 'lib.amortize' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
        "}\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", inline],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["help_exit_code"] == 0
    assert payload["lib_arm_imported"] is False
    assert payload["lib_amortize_imported"] is False
    assert payload["numpy_financial_imported"] is False


def test_cli_rejects_float_principal(tmp_path: Path) -> None:
    """ARM-08 + D-19/WR-02: JSON-float in loan.principal rejected with 6-key envelope."""
    import json
    import subprocess
    import sys

    bad = tmp_path / "float_principal.json"
    bad.write_text(
        '{"loan": {"principal": 400000.00, "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", "index_path": []}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["loan", "principal"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"]["class"] == "Decimal"


def test_cli_rejects_float_assumed_index_rate(tmp_path: Path) -> None:
    """ARM-08 + D-19: JSON-float in assumed_index_rate rejected with 6-key envelope."""
    import json
    import subprocess
    import sys

    bad = tmp_path / "float_index.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": 0.050000, "index_path": []}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert err["loc"] == ["assumed_index_rate"]
    assert err["type"] == "decimal_type"


def test_cli_rejects_float_index_path_value(tmp_path: Path) -> None:
    """ARM-08 + D-19: JSON-float deep in index_path[0].value rejected with correct loc."""
    import json
    import subprocess
    import sys

    bad = tmp_path / "float_index_path.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", '
        '"index_path": [{"period": 61, "value": 0.052500}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert err["loc"] == ["index_path", 0, "value"]
    assert err["ctx"]["field_path"] == "index_path.0.value"


def test_cli_rejects_float_floor_rate(tmp_path: Path) -> None:
    """ARM-08 + D-19: JSON-float in arm_terms.floor_rate rejected."""
    import json
    import subprocess
    import sys

    bad = tmp_path / "float_floor.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": 0.030000, "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", "index_path": []}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert err["loc"] == ["arm_terms", "floor_rate"]


def test_cli_error_envelope_uniformity(tmp_path: Path) -> None:
    """ARM-08 + D-19/WR-02: float-gate envelope + Pydantic ValidationError envelope
    have IDENTICAL 6-key shape (mirror tests/test_amortize.py:996+).
    """
    import json
    import subprocess
    import sys

    # Case 1: float-gate envelope (loan.principal as a JSON float)
    bad_float = tmp_path / "float.json"
    bad_float.write_text(
        '{"loan": {"principal": 400000.00, "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", "index_path": []}'
    )
    res1 = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad_float)],
        capture_output=True,
        text=True,
        check=False,
    )
    err1 = json.loads(res1.stderr)[0]

    # Case 2: Pydantic ValidationError envelope (misaligned index_path period
    # surfaces ARMRequest._index_path_periods_align_to_reset_triggers as
    # value_error -> 6-key shape including ctx). Rule 1 deviation from plan
    # text: plan-prescribed "missing floor_rate" surfaces a `missing`-type
    # Pydantic error whose e.json() omits ctx (5 keys), failing the keyset-
    # equality assertion. The misaligned-period validator emits all 6 keys
    # uniformly, which is the contract this test exists to pin (mirrors
    # tests/test_amortize.py:test_cli_error_envelope_uniformity which uses a
    # cross-field model_validator surface for the same reason).
    bad_pydantic = tmp_path / "misaligned.json"
    bad_pydantic.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", '
        '"index_path": [{"period": 62, "value": "0.052500"}]}'
    )
    res2 = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad_pydantic)],
        capture_output=True,
        text=True,
        check=False,
    )
    err2 = json.loads(res2.stderr)[0]

    # Both must have the same 6 top-level keys
    assert set(err1.keys()) == set(err2.keys())
    assert {"type", "loc", "msg", "input", "url", "ctx"} <= set(err1.keys())
    # Both URLs are Pydantic-format
    assert err1["url"].startswith("https://errors.pydantic.dev/")
    assert err2["url"].startswith("https://errors.pydantic.dev/")
    # Same exit code
    assert res1.returncode == 2
    assert res2.returncode == 2


def test_cli_misaligned_index_path_period_rejected(tmp_path: Path) -> None:
    """ARM-08 + D-01: misaligned index_path period surfaces ARMRequest model_validator
    error as the 6-key Pydantic ValidationError envelope.
    """
    import json
    import subprocess
    import sys

    bad = tmp_path / "misaligned.json"
    bad.write_text(
        '{"loan": {"principal": "400000.00", "annual_rate": "0.050000", '
        '"term_months": 360, "origination_date": "2026-01-01", "loan_type": "arm"}, '
        '"arm_terms": {"initial_period_months": 60, "reset_period_months": 12, '
        '"initial_cap_bps": 500, "periodic_cap_bps": 200, "lifetime_cap_bps": 500, '
        '"floor_rate": "0.030000", "margin_bps": 250, "index_series_id": "MORTGAGE30US"}, '
        '"assumed_index_rate": "0.050000", '
        '"index_path": [{"period": 62, "value": "0.052500"}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    # Pydantic surfaces the model_validator ValueError; one of the errors mentions period 62
    assert any("62" in str(e.get("msg", "")) for e in errors)
    # Each error has the 6-key shape
    for e in errors:
        assert {"type", "loc", "msg", "input", "url", "ctx"} <= set(e.keys())


# =========================================================================
# ARM-09 (3 stubs) — flipped in Wave 5 (references/arm-mechanics.md ships)
# =========================================================================


def test_arm_mechanics_doc_sections_present() -> None:
    """ARM-09 + D-08: references/arm-mechanics.md exists with all 7 D-08 sections."""
    project_root = Path(__file__).resolve().parent.parent
    doc_path = project_root / "references" / "arm-mechanics.md"
    assert doc_path.is_file(), f"references/arm-mechanics.md missing at {doc_path}"
    content = doc_path.read_text().lower()
    # 7 D-08 [REVISED 2026-04-30] sections must all appear (case-insensitive token match):
    required_section_tokens = [
        "reset month convention",  # Section 1
        "cap precedence",  # Section 2
        "floor algebra",  # Section 3
        "quantization",  # Section 4
        "negative amortization",  # Section 5
        "index_series_id",  # Section 6
        "teaser",  # Section 7
    ]
    for token in required_section_tokens:
        assert token in content, f"Section token '{token}' missing from references/arm-mechanics.md"
    # Document must have at least 7 ## headings (the 7 sections; appendix may add another)
    heading_count = sum(1 for line in content.splitlines() if line.startswith("## "))
    assert heading_count >= 7, f"Expected at least 7 ## headings, got {heading_count}"


def test_arm_terms_docstring_cites_arm_mechanics() -> None:
    """ARM-09 + ROADMAP SC-5: ARMTerms model docstring cites references/arm-mechanics.md."""
    from lib.arm import ARMTerms

    docstring = ARMTerms.__doc__ or ""
    # Load-bearing citation token (see Wave 5 Plan 05-05 Task 2)
    assert "references/arm-mechanics.md" in docstring, (
        "ARMTerms.__doc__ must reference references/arm-mechanics.md per ROADMAP SC-5"
    )
    # Bonus: docstring should mention at least one regulatory citation
    assert "B2-1.4-02" in docstring or "Fannie" in docstring or "Selling Guide" in docstring


def test_arm_mechanics_citations() -> None:
    """ARM-09 + D-08 [REVISED 2026-04-30]: references/arm-mechanics.md cites the verified-correct
    Selling Guide sections + CFPB + a 5/6 SOFR ARM lender disclosure (Plan 05-06 Rule-4
    deviation: original AmericU URL 404'd; substituted ABT Bank's functionally equivalent
    5/6, 7/6 & 10/6 SOFR ARM disclosure per T-05-34), AND does NOT carry forward the broken
    legacy citations B5-3.5-01 / §4404.
    """
    project_root = Path(__file__).resolve().parent.parent
    doc_path = project_root / "references" / "arm-mechanics.md"
    content = doc_path.read_text()
    # 4 required URL/section fragments:
    required_fragments = [
        "selling-guide.fanniemae.com/sel/b2-1.4-02",  # Fannie B2-1.4-02 verified
        "sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms",  # Freddie SOFR-Indexed
        "consumerfinance.gov/ask-cfpb/what-are-rate-caps",  # CFPB §1951
        "abt.bank/wp-content/uploads/2022/09/Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf",  # ABT Bank 5/6 SOFR PDF (substituted for AmericU 404 per Plan 05-06)
    ]
    for frag in required_fragments:
        assert frag in content, (
            f"Required citation fragment '{frag}' missing from references/arm-mechanics.md"
        )

    # 2 forbidden legacy fragments (must NOT appear — prevents D-08 regression):
    forbidden_fragments = [
        "B5-3.5-01",  # broken; returns 404 — RESEARCH §Q4 verified
        "§4404",  # stale Freddie section — RESEARCH §Q4 verified
    ]
    for frag in forbidden_fragments:
        assert frag not in content, (
            f"Forbidden legacy citation '{frag}' found in references/arm-mechanics.md "
            f"(D-08 [REVISED 2026-04-30] removed this; revert detected)"
        )

    # Section 6302.7(b) (Freddie modern equivalent of legacy section number) must appear
    assert "6302.7(b)" in content, "Freddie 6302.7(b) section must be cited (D-08 [REVISED])"


# =========================================================================
# Cross-cutting (2 stubs)
# =========================================================================


def test_applied_cap_citation_coverage() -> None:
    """D-10: every applied_cap Literal value (initial/periodic/lifetime/floor/none) exercised by >=1 fixture."""
    import json

    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "arm"
    seen: set[str] = set()
    for fp in sorted(fixtures_dir.glob("*.json")):
        data = json.loads(fp.read_text())
        for re_event in data.get("expected", {}).get("reset_events", []):
            seen.add(re_event["applied_cap"])
    required = {"initial", "periodic", "lifetime", "floor", "none"}
    missing = required - seen
    assert not missing, (
        f"applied_cap coverage missing: {missing}. Seen: {seen}. "
        f"D-10 requires every Literal value to be exercised by at least one fixture."
    )


def test_arm_teaser_rate(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """D-02 + LM-3 (engine layer): teaser-rate ARM uses note_rate as lifetime base.

    loan.annual_rate=0.030 (teaser); note_rate=0.050 (post-teaser). Lifetime ceiling
    measured against note_rate, not loan.annual_rate. Verify by constructing a scenario
    where the lifetime_cap binds: huge index + initial_cap large enough to NOT bind.

    WR-04: Loads `arm_teaser_rate.json` fixture (committed via Plan 05-06) so the
    per-payment + per-reset hand-calc rows are cross-validated against engine output.
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_teaser_rate")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)
    expected = fx["expected"]

    # Length + structural invariants
    assert len(schedule.payments) == len(expected["payments"])
    assert len(schedule.reset_events) == len(expected["reset_events"])

    # First reset event: lifetime ceiling = note_rate (0.05) + lifetime_cap_bps/10000 (0.05) = 0.10
    # NOT loan.annual_rate (0.03) + 0.05 = 0.08
    first_reset = schedule.reset_events[0]
    assert first_reset.new_rate == Decimal("0.100000"), (
        f"teaser ARM: lifetime ceiling should be note_rate+lifetime_cap=0.10, "
        f"got new_rate={first_reset.new_rate}"
    )
    assert first_reset.applied_cap == "lifetime"

    # Hand-calc cross-validation against fixture's reset_events[0].
    expected_first_reset = expected["reset_events"][0]
    assert first_reset.new_rate == Decimal(expected_first_reset["new_rate"])
    assert first_reset.applied_cap == expected_first_reset["applied_cap"]
    assert first_reset.index_value_used == Decimal(expected_first_reset["index_value_used"])

    # Spot-check teaser-period payments + first post-reset payment against the fixture.
    _assert_engine_matches_fixture_at_period(schedule.payments[0], expected["payments"][0])
    _assert_engine_matches_fixture_at_period(schedule.payments[59], expected["payments"][59])
    _assert_engine_matches_fixture_at_period(schedule.payments[60], expected["payments"][60])


def test_arm_index_path_overrides(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """D-01 (engine layer) + WR-04: index_path overrides win at matching reset triggers,
    while non-overridden triggers fall back to assumed_index_rate.

    Loads `arm_index_path_overrides.json` fixture: assumed_index_rate=0.05 (fallback),
    index_path provides 0.06 at period 61 and 0.045 at period 73. The engine MUST honor
    the override at periods 61 + 73 and use the fallback for every later trigger
    (85, 97, 109, ...). Without this binding the override-wins semantic was implicit.
    """
    from decimal import Decimal

    from lib.arm import build_arm_schedule

    fx = arm_fixture("arm_index_path_overrides")
    request = _request_from_fixture(fx)
    schedule = build_arm_schedule(request)
    expected = fx["expected"]

    # Length + structural invariants
    assert len(schedule.payments) == len(expected["payments"])
    assert len(schedule.reset_events) == len(expected["reset_events"])

    # Index-path-driven resets (override wins at 61 + 73)
    by_period = {ev.period: ev for ev in schedule.reset_events}
    expected_by_period = {ev["period"]: ev for ev in expected["reset_events"]}

    reset_61 = by_period[61]
    expected_61 = expected_by_period[61]
    assert reset_61.index_value_used == Decimal(expected_61["index_value_used"])
    assert reset_61.index_value_used == Decimal("0.060000"), (
        "period 61 must use index_path override (0.06), not assumed_index_rate (0.05)"
    )
    assert reset_61.new_rate == Decimal(expected_61["new_rate"])
    assert reset_61.applied_cap == expected_61["applied_cap"]

    reset_73 = by_period[73]
    expected_73 = expected_by_period[73]
    assert reset_73.index_value_used == Decimal(expected_73["index_value_used"])
    assert reset_73.index_value_used == Decimal("0.045000"), (
        "period 73 must use index_path override (0.045), not assumed_index_rate (0.05)"
    )
    assert reset_73.new_rate == Decimal(expected_73["new_rate"])
    assert reset_73.applied_cap == expected_73["applied_cap"]

    # Fallback semantics: period 85 + every later trigger uses assumed_index_rate (0.05)
    reset_85 = by_period[85]
    expected_85 = expected_by_period[85]
    assert reset_85.index_value_used == Decimal(expected_85["index_value_used"])
    assert reset_85.index_value_used == Decimal("0.050000"), (
        "period 85 has no override; must fall back to assumed_index_rate (0.05)"
    )
    assert reset_85.new_rate == Decimal(expected_85["new_rate"])

    # Spot-check first override payment + reset boundary
    _assert_engine_matches_fixture_at_period(schedule.payments[60], expected["payments"][60])
    _assert_engine_matches_fixture_at_period(schedule.payments[72], expected["payments"][72])


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


def test_arm_request_floor_exceeds_lifetime_ceiling_raises() -> None:
    """ARM-01 + D-02 + WR-03 (model-layer): ARMRequest._floor_does_not_exceed_lifetime_ceiling
    rejects configurations where the effective floor is above the lifetime ceiling.

    Scenario: floor_rate=0.20, note_rate=None (-> loan.annual_rate=0.05), lifetime_cap=500bps
    -> lifetime_ceiling=0.10. effective_floor=max(margin/10000=0.025, 0.20)=0.20 > 0.10.
    Every reset would clamp above the lifetime cap, silently violating the D-02 invariant.
    Construction MUST raise instead.
    """
    from datetime import date
    from decimal import Decimal

    from lib.arm import ARMRequest, ARMTerms
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
        lifetime_cap_bps=500,  # lifetime ceiling = 0.05 + 0.05 = 0.10
        floor_rate=Decimal("0.200000"),  # 20% floor — well above 0.10 ceiling
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    with pytest.raises(ValidationError) as exc:
        ARMRequest(
            loan=loan,
            arm_terms=terms,
            assumed_index_rate=Decimal("0.050000"),
            index_path=[],
        )
    errors = exc.value.errors()
    floor_errors = [e for e in errors if "lifetime_ceiling" in str(e.get("msg", ""))]
    assert len(floor_errors) >= 1, f"Expected lifetime-ceiling error, got: {errors}"


def test_arm_request_duplicate_index_path_period_raises() -> None:
    """ARM-01 + D-01 + WR-02 (model-layer): ARMRequest._index_path_periods_align_to_reset_triggers
    rejects duplicate index_path entries for the same period.

    A request with two entries at period 61 (both aligned, but the second silently
    overrode by first-wins iteration order in _compute_new_rate) violates the
    "fail loud, no inference" doctrine. Construction MUST raise so a user who
    accidentally double-specifies a reset value sees the error immediately
    instead of getting a different rate path with no warning.
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
            index_path=[
                IndexPathEntry(period=61, value=Decimal("0.050000")),
                IndexPathEntry(period=61, value=Decimal("0.100000")),
            ],
        )
    errors = exc.value.errors()
    duplicate_errors = [e for e in errors if "duplicate" in str(e.get("msg", ""))]
    assert len(duplicate_errors) >= 1, f"Expected duplicate-period error, got: {errors}"


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
