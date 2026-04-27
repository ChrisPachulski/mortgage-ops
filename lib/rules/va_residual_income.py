"""VA residual income evaluation per VA Lender Handbook M26-7 Topic 7.

Citation: VA Lender Handbook M26-7 Topic 7 — Residual Income (geographic regional
tables). Loans with actual residual income below the table minimum are flagged
as failing VA underwriting; the binding rule is reported in a stable format
suitable for downstream affordability "blocked_by" reporting (AFFD-07 in Phase 4).
Source URL: https://benefits.va.gov/WARMS/docs/admin26/m26-07/
Effective: 2023-04-07

What this predicate decides:
  Given region (northeast/midwest/south/west), family_size, loan_amount, and
  actual residual income, return ResidualIncomeResult with pass/fail status,
  the minimum required dollar amount, and a stable binding_rule_citation string.

Inputs:
    region: Region (Literal from lib.rules.types — VA's four regions)
    family_size: int (>= 1; VA tables published for sizes 1..5; sizes >5 add
                      per_extra_member_increment ($80) per additional member)
    loan_amount: Decimal (positive; selects table_above_80k or table_below_80k
                          based on $80,000 threshold)
    actual_residual_income: Decimal (current household residual income to compare
                                     against the table minimum)

Outputs:
    ResidualIncomeResult — frozen Pydantic model with:
        status: Literal["pass", "fail"]
        minimum_required: Decimal (table value, quantized to cents)
        actual: Decimal (input echoed back for trace)
        binding_rule_citation: str — STABLE format
            f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"
            (Phase 4 AFFD-07 reads this; format drift breaks Phase 4.)

Edge cases:
  - family_size < 1: raises ValueError.
  - loan_amount <= 0: raises ValueError.
  - region not in the Literal set: pydantic-typed at the call boundary; if a raw
    string is passed and doesn't match, KeyError will surface during table lookup.

Public helper:
  minimum_required(region, family_size, loan_amount) -> Decimal — exposed so
  callers (e.g. Phase 4 affordability) can fetch the threshold without running
  the full evaluation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from lib.money import quantize_cents
from lib.rules._loader import load_reference

if TYPE_CHECKING:
    from lib.rules.types import Region

LOAN_BAND_THRESHOLD_KEY: str = "loan_band_threshold"
ResidualIncomeStatus = Literal["pass", "fail"]


class ResidualIncomeResult(BaseModel):
    """VA residual income evaluation result. Frozen + strict per project Pydantic
    discipline. binding_rule_citation is STABLE — Phase 4 AFFD-07 depends on the
    exact f-string format documented in the module docstring."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    status: ResidualIncomeStatus
    minimum_required: Decimal
    actual: Decimal
    binding_rule_citation: str


def minimum_required(
    region: Region,
    family_size: int,
    loan_amount: Decimal,
) -> Decimal:
    """Return the VA M26-7 minimum residual income for the given region / family
    size / loan band. Family sizes > 5 add per_extra_member_increment per
    additional member.
    """
    if family_size < 1:
        raise ValueError(f"family_size must be >= 1, got {family_size}")
    if loan_amount <= 0:
        raise ValueError(f"loan_amount must be positive, got {loan_amount}")

    ref = load_reference("va-residual-income")
    threshold = Decimal(ref[LOAN_BAND_THRESHOLD_KEY])
    table_key = "table_above_80k" if loan_amount >= threshold else "table_below_80k"
    table = ref[table_key][region]

    base_family_size = min(family_size, 5)
    base = Decimal(table[str(base_family_size)])
    if family_size > 5:
        extra = (family_size - 5) * Decimal(ref["per_extra_member_increment"])
        base = base + extra
    return quantize_cents(base)


def evaluate(
    region: Region,
    family_size: int,
    loan_amount: Decimal,
    actual_residual_income: Decimal,
) -> ResidualIncomeResult:
    """Evaluate actual residual income against the VA M26-7 table minimum.

    Returns ResidualIncomeResult; the binding_rule_citation field is STABLE
    (`VA-RESIDUAL-{REGION}-FAMILY-{N}`) — Phase 4 AFFD-07 reads this verbatim.
    """
    required = minimum_required(region, family_size, loan_amount)
    status: ResidualIncomeStatus = "pass" if actual_residual_income >= required else "fail"
    citation = f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"
    return ResidualIncomeResult(
        status=status,
        minimum_required=required,
        actual=actual_residual_income,
        binding_rule_citation=citation,
    )
