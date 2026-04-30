"""Domain models for mortgage-ops. Phase 1 defines the shapes; later phases populate.

FND-02 specifies "Pydantic v2 models with `condecimal(max_digits=14, decimal_places=2)`".
The canonical Pydantic v2 form is `Annotated[Decimal, Field(strict=True, max_digits=14,
decimal_places=2, ...)]` — see pitfall 10 in 01-RESEARCH.md. The two are equivalent in
behavior; the Annotated form is what current Pydantic + mypy + ruff understand best.

Money fields: max 12 digits before decimal + 2 after = 14 total. strict=True rejects
float at validation time. ge=Decimal("0") rejects negative dollar amounts.

Rate fields: a fraction in [0, 1] (so 0.065 = 6.5%). max 7 total digits + 6 places.
"""

from __future__ import annotations

from datetime import date  # noqa: TC003  # Pydantic resolves annotations at runtime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Public type aliases — Phase 4+ models import these.
Money = Annotated[
    Decimal,
    Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0")),
]
"""Non-negative money: up to 12 integer digits + 2 decimal places."""

Rate = Annotated[
    Decimal,
    Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1")),
]
"""A fractional rate in [0, 1] with up to 6 decimal places (e.g. 0.065000 = 6.5%)."""


class Loan(BaseModel):
    """Inputs to an amortization. Phase 3 will use this; Phase 1 just defines it."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    principal: Money
    annual_rate: Rate
    term_months: int = Field(ge=1, le=600)
    origination_date: date | None = None
    loan_type: Literal["fixed", "arm", "fha", "va", "usda", "jumbo"] = "fixed"


class Payment(BaseModel):
    """A single period in the schedule."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    period: int = Field(ge=1)
    payment_date: date
    payment: Money
    principal: Money
    interest: Money
    extra_principal: Money = Decimal("0.00")
    balance: Money
    cumulative_interest: Money = Decimal("0.00")  # D-14: running total through this period
    cumulative_principal: Money = Decimal("0.00")  # D-14: running total through this period


class Schedule(BaseModel):
    """Output of an amortization run. Phase 3 produces this; Phase 1 only defines."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    monthly_pi: Money
    total_interest: Money
    # D-10: True when final period principal != formulaic value
    final_payment_adjusted: bool = False
    payments: list[Payment]

    @model_validator(mode="after")
    def _total_interest_matches_last_cumulative(self) -> Schedule:
        """D-15: Schedule.total_interest == payments[-1].cumulative_interest exactly.

        Skipped when payments is empty (constructor convenience for in-progress
        scaffolds; Phase 3+ tests cover non-empty schedules end-to-end).
        """
        if not self.payments:
            return self
        last = self.payments[-1].cumulative_interest
        if self.total_interest != last:
            raise ValueError(
                f"D-15 invariant: Schedule.total_interest ({self.total_interest}) != "
                f"payments[-1].cumulative_interest ({last})"
            )
        return self
