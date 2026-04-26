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
    )
    sched = Schedule(
        loan=loan,
        monthly_pi=Decimal("2528.27"),
        total_interest=Decimal("510178.27"),
        payments=[p],
    )
    assert sched.loan.principal == Decimal("400000.00")
    assert len(sched.payments) == 1


def test_money_and_rate_aliases_are_exported() -> None:
    # Phase 4+ models import these aliases; Phase 1 ships the contract.
    assert Money is not None
    assert Rate is not None
