"""FHA Mortgage Insurance Premium (MIP) computation.

Citation: HUD Mortgagee Letter 2023-05 (annual MIP rates — 30bps reduction
effective 2023-03-20) and HUD Mortgagee Letter 2013-04 (termination rules:
life-of-loan if origination LTV > 90%; 132 months / 11 years if LTV <= 90%).
Source URL: https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf
Effective: 2023-03-20

What this predicate decides:
  Given a Loan, the original property appraised value, and the FHA endorsement
  date, return UFMIP (upfront MIP, dollar amount) + annual MIP rate + the period
  at which annual MIP terminates (or "life_of_loan" sentinel).

Inputs:
    loan: Loan (Phase-1 model — provides principal, term_months, annual_rate)
    original_property_value: Decimal (appraised value at origination, used for LTV)
    endorsement_date: date (FHA case endorsement date — pre-2023-03-20 rates
                            are deferred to v2; predicate raises
                            NotImplementedError so a future refresh is explicit)

Outputs:
    MIPResult — frozen Pydantic model with:
        ufmip: Decimal (dollar amount, end-of-period quantized to cents)
        annual_mip_pct: Decimal (annual rate as decimal, e.g. 0.0055 = 55bps)
        terminates_at_period: int | Literal["life_of_loan"]

Edge cases:
  - endorsement_date < 2023-03-20: raises NotImplementedError (pre-HUD-ML-2023-05
    rates differ; grandfathering deferred to v2)
  - LTV > 1.00: raises ValueError (loan exceeds appraised value — invalid input)
  - original_property_value <= 0: raises ValueError (invalid input)
  - No matching annual_mip_table row: raises LookupError (REF-03 schema gap)

Termination rule (HUD ML 2013-04, unchanged by 2023-05):
  - Origination LTV > 0.90: MIP for life of loan ("life_of_loan" sentinel)
  - Origination LTV <= 0.90: MIP terminates at month 132 (= 11 years x 12)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict

from lib.money import quantize_cents
from lib.rules._loader import load_reference

if TYPE_CHECKING:
    from lib.models import Loan

_EARLIEST_SUPPORTED_ENDORSEMENT: date = date(2023, 3, 20)


class MIPResult(BaseModel):
    """FHA MIP result. Frozen + strict per project Pydantic discipline."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    ufmip: Decimal
    annual_mip_pct: Decimal
    terminates_at_period: int | Literal["life_of_loan"]


def compute(
    loan: Loan,
    original_property_value: Decimal,
    endorsement_date: date,
) -> MIPResult:
    """Compute FHA UFMIP + annual MIP rate + termination period per HUD MLs.

    See module docstring for full edge-case behavior.
    """
    if endorsement_date < _EARLIEST_SUPPORTED_ENDORSEMENT:
        raise NotImplementedError(
            f"endorsement_date {endorsement_date.isoformat()} is before "
            f"the 2023-03-20 effective date of HUD ML 2023-05. "
            f"pre-2023-03-20 MIP rates differ from current rates; "
            f"grandfathering is deferred to v2. See REF-03 notes."
        )
    ref = load_reference("fha-mip-rates")

    # UFMIP = principal * ufmip_rate, quantized once at end-of-period.
    ufmip_rate = Decimal(ref["ufmip_rate"])
    ufmip = quantize_cents(loan.principal * ufmip_rate)

    # LTV at origination = principal / original_property_value
    if original_property_value <= 0:
        raise ValueError(f"original_property_value must be positive, got {original_property_value}")
    ltv = loan.principal / original_property_value
    if ltv > Decimal("1.00"):
        raise ValueError(
            f"LTV={ltv} exceeds 1.00 (loan principal {loan.principal} > "
            f"original_property_value {original_property_value}); invalid input"
        )

    # Annual MIP rate lookup: find the row matching (term, LTV bucket, loan-amount tier)
    annual_mip_pct = _lookup_annual_mip(
        table=ref["annual_mip_table"],
        term_months=loan.term_months,
        ltv=ltv,
        loan_amount=loan.principal,
    )

    # Termination rule (HUD ML 2013-04 — UNchanged by 2023-05)
    terminates: int | Literal["life_of_loan"]
    if ltv > Decimal("0.90"):
        terminates = ref["termination"]["ltv_above_90_pct"]
    else:
        terminates = ref["termination"]["ltv_at_or_below_90_pct"]

    return MIPResult(
        ufmip=ufmip,
        annual_mip_pct=annual_mip_pct,
        terminates_at_period=terminates,
    )


def _lookup_annual_mip(
    table: list[dict[str, Any]],
    term_months: int,
    ltv: Decimal,
    loan_amount: Decimal,
) -> Decimal:
    """Find the annual_mip_table row whose (term, ltv, loan_amount_max) bracket
    matches the given inputs. Raises LookupError if no row matches.

    LTV bucket convention: ltv_min is exclusive lower bound for non-zero buckets;
    ltv_max is inclusive upper. The 0.00..0.78 / 0.78..0.90 / 0.90..0.95 /
    0.95..1.00 buckets cover [0, 1] without gap or overlap; we treat ltv_min as
    inclusive when it is the lowest bucket (0.00), exclusive otherwise.
    """
    for row in table:
        if not (row["term_months_min"] <= term_months <= row["term_months_max"]):
            continue
        ltv_min = Decimal(row["ltv_min"])
        ltv_max = Decimal(row["ltv_max"])
        if ltv_min == Decimal("0.00"):
            if not (ltv <= ltv_max):
                continue
        else:
            if not (ltv_min < ltv <= ltv_max):
                continue
        if loan_amount > Decimal(row["loan_amount_max"]):
            continue
        return Decimal(row["annual_mip_rate"])
    raise LookupError(
        f"No annual_mip_table row matched term_months={term_months}, "
        f"ltv={ltv}, loan_amount={loan_amount}. REF-03 schema gap."
    )
