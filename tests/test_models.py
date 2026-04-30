"""Tests for lib/models.py — Pydantic v2 domain models (FND-02).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - Loan: strict=True, max_digits=14, decimal_places=2, ge=Decimal("0"), term_months 1..600
  - Loan: extra="forbid" rejects unknown keys
  - Loan: frozen=True rejects post-construction mutation
  - Loan: model_dump_json emits Decimals as JSON strings (Pitfall 3 — intentional)
  - Loan: model_dump_json -> model_validate_json round-trips losslessly
  - Money / Rate: Annotated type aliases are public exports
  - Payment: constructs with Phase-3-shape data
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from lib.models import Loan, Money, Payment, Rate, Schedule
from pydantic import ValidationError


def test_loan_accepts_decimal_from_string() -> None:
    # Hand: principal=$400k, rate=6.5%, term=30yr — Phase 3 oracle.
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    assert loan.principal == Decimal("400000.00")
    assert loan.annual_rate == Decimal("0.065000")
    assert loan.term_months == 360


def test_loan_rejects_float_principal() -> None:
    # Strict=True must reject floats — load-bearing assertion for FND-01 + FND-02.
    # The `# type: ignore[arg-type]` on the call below documents that mypy --strict
    # would catch this at compile time; the runtime test verifies Pydantic catches it too.
    with pytest.raises(ValidationError) as exc:
        Loan(principal=400000.0, annual_rate=Decimal("0.065000"), term_months=360)  # type: ignore[arg-type]
    assert "decimal_type" in str(exc.value) or "Input should be" in str(exc.value)


def test_loan_rejects_float_annual_rate() -> None:
    with pytest.raises(ValidationError):
        Loan(principal=Decimal("400000.00"), annual_rate=0.065, term_months=360)  # type: ignore[arg-type]


def test_loan_rejects_too_many_decimal_places_on_principal() -> None:
    # Hand: principal "400000.001" has 3 decimal places; max is 2.
    with pytest.raises(ValidationError):
        Loan(principal=Decimal("400000.001"), annual_rate=Decimal("0.065000"), term_months=360)


def test_loan_rejects_negative_principal() -> None:
    # ge=Decimal("0"); negative principal is nonsense for a mortgage.
    with pytest.raises(ValidationError):
        Loan(principal=Decimal("-1.00"), annual_rate=Decimal("0.065000"), term_months=360)


def test_loan_rejects_unknown_field() -> None:
    # extra="forbid" — typos in script JSON inputs surface immediately.
    with pytest.raises(ValidationError):
        Loan(
            principal=Decimal("400000.00"),
            annual_rate=Decimal("0.065000"),
            term_months=360,
            unknown_field="x",  # type: ignore[call-arg]
        )


def test_loan_rejects_term_months_below_one() -> None:
    with pytest.raises(ValidationError):
        Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.065000"), term_months=0)


def test_loan_rejects_term_months_above_six_hundred() -> None:
    # 600 months = 50 years; longer than any consumer mortgage product.
    with pytest.raises(ValidationError):
        Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.065000"), term_months=601)


def test_loan_is_frozen_after_construction() -> None:
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    with pytest.raises(ValidationError):
        loan.principal = Decimal("999.00")  # type: ignore[misc]


def test_loan_serializes_decimal_as_string_in_json() -> None:
    # Pitfall 3: this is intentional. Phase 9's Node consumer must Decimal(s) parse.
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    j = loan.model_dump_json()
    assert '"principal":"400000.00"' in j
    assert '"annual_rate":"0.065000"' in j
    assert '"term_months":360' in j  # int stays an int


def test_loan_json_round_trips_losslessly() -> None:
    original = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    j = original.model_dump_json()
    restored = Loan.model_validate_json(j)
    assert restored == original


def test_payment_constructs_with_phase_3_shape() -> None:
    # Phase-3 row: month 1 of $400k @ 6.5%/30yr.
    # Hand: payment 2528.27, interest 400000 * 0.065/12 = 2166.666... -> 2166.67;
    # principal = 2528.27 - 2166.67 = 361.60; balance = 400000 - 361.60 = 399638.40.
    # (Approximate; Phase 3 will pin the exact row. Phase 1 only checks shape.)
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
    )
    assert p.period == 1
    assert p.principal == Decimal("361.60")


def test_schedule_aggregates_loan_and_payments() -> None:
    # Hand: Phase 1 test extended for D-15 validator. Payment.cumulative_interest
    # MUST equal Schedule.total_interest exactly (Phase 3 D-15). Both set to the
    # period-1 interest of $400k @ 6.5%/30yr = $2166.67.
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
        # D-14 + D-15: cumulative_interest must match Schedule.total_interest below
        cumulative_interest=Decimal("2166.67"),
        cumulative_principal=Decimal("361.60"),  # D-14
    )
    sched = Schedule(
        loan=loan,
        monthly_pi=Decimal("2528.27"),
        # D-15: matches p.cumulative_interest above
        total_interest=Decimal("2166.67"),
        payments=[p],
    )
    assert sched.loan.principal == Decimal("400000.00")
    assert len(sched.payments) == 1


def test_money_and_rate_aliases_are_exported() -> None:
    # Phase 4+ models import these aliases; Phase 1 ships the contract.
    assert Money is not None
    assert Rate is not None


def test_payment_carries_cumulative_totals() -> None:
    # D-14: running totals exposed on every Payment row.
    # Hand: period-1 of $400k @ 6.5%/30yr — interest $2166.67, principal $361.60.
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
        cumulative_interest=Decimal("2166.67"),
        cumulative_principal=Decimal("361.60"),
    )
    assert p.cumulative_interest == Decimal("2166.67")
    assert p.cumulative_principal == Decimal("361.60")


def test_payment_cumulative_totals_default_to_zero() -> None:
    # D-14: defaults keep Phase 1 callers (and any caller in another phase that
    # hasn't migrated yet) green. The cumulative fields are additive, NOT required.
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
    )
    assert p.cumulative_interest == Decimal("0.00")
    assert p.cumulative_principal == Decimal("0.00")


def test_schedule_total_interest_must_match_last_cumulative() -> None:
    # D-15: validator rejects Schedule where total_interest != payments[-1].cumulative_interest.
    # No silent disagreement between summary and per-row totals.
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
        cumulative_interest=Decimal("2166.67"),
        cumulative_principal=Decimal("361.60"),
    )
    with pytest.raises(ValidationError) as exc:
        Schedule(
            loan=loan,
            monthly_pi=Decimal("2528.27"),
            total_interest=Decimal("999.99"),  # mismatched on purpose
            payments=[p],
        )
    assert "D-15" in str(exc.value) or "total_interest" in str(exc.value)


def test_schedule_with_empty_payments_skips_d15_validator() -> None:
    # D-15 guard: empty payments skip the validator (constructor convenience).
    # Tests that produce real schedules in Phase 3+ exercise the non-empty branch.
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    sched = Schedule(
        loan=loan,
        monthly_pi=Decimal("2528.27"),
        total_interest=Decimal("0.00"),
        payments=[],
    )
    assert sched.payments == []
    assert sched.final_payment_adjusted is False  # D-10 default


def test_schedule_final_payment_adjusted_defaults_false() -> None:
    # D-10: backwards-compat default. Phase 3 engine sets True when adjustment
    # is non-zero (cents-drift cleanup or extra-principal early payoff).
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
        cumulative_interest=Decimal("2166.67"),
        cumulative_principal=Decimal("361.60"),
    )
    sched = Schedule(
        loan=loan,
        monthly_pi=Decimal("2528.27"),
        total_interest=Decimal("2166.67"),
        payments=[p],
    )
    assert sched.final_payment_adjusted is False
