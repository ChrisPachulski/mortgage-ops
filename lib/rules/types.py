"""Phase-2 extension types for lib/rules/ predicates.

Phase 1's lib/models.py surface (Loan, Payment, Schedule, Money, Rate) is FROZEN
per Phase 1 PATTERNS Convention #2. Phase 2 adds new domain types HERE so that
frozen surface stays untouched. Phase 4+ may import from both lib.models and
lib.rules.types.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lib.models import Money  # noqa: TC001  # Pydantic resolves annotations at runtime

LoanType = Literal[
    "conforming",
    "high_balance",
    "jumbo",
    "fha_standard",
    "fha_high_balance",
    "va_standard",
    "va_high_balance",
    "usda",
]
"""Loan-program classification result (RUL-01)."""

Region = Literal["northeast", "midwest", "south", "west"]
"""VA's four geographic regions for residual income (RUL-07)."""


class County(BaseModel):
    """A US county identified by 5-digit FIPS code (state_fips + county_fips).

    Used by RUL-01 (loan_type), RUL-08 (usda), and any predicate that needs
    per-county lookup against FHFA / HUD / USDA tables.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
    county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    name: str = Field(min_length=1)


class Borrower(BaseModel):
    """Borrower attributes consumed by VA / FHA / Fannie / Freddie predicates."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    credit_score: int = Field(ge=300, le=850)
    family_size: int = Field(ge=1, le=20)
    region: Region | None = None
    is_va_funding_fee_exempt: bool = False


class Property(BaseModel):
    """Property attributes consumed by loan-type / PMI predicates.

    `original_value` is the appraised value at origination — REQUIRED for HPA
    PMI termination math (per HPA, LTV is computed against ORIGINAL value, not
    current market value).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    original_value: Money
    unit_count: int = Field(ge=1, le=4)
    is_primary_residence: bool = True
