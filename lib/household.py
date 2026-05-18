"""Phase 14 Household model — analysis-time financial state for the property pipeline.

D-14-MODELS-01: Pydantic v2 Household model (strict / frozen / extra=forbid) that
the Phase 14 `analyze(listing, household, profile) -> AnalysisReport` entrypoint
consumes alongside PropertyListing (Phase 13) and Profile (lib/profile.py, this phase).

DISTINCT from lib.affordability.Household (Phase 4 frozen contract). The Phase 4
model is a multi-applicant container (applicants list, MonthlyDebts, EscrowInputs,
optional VAInputs) used by lib.affordability.evaluate_request. THIS model is a
flat analysis-time financial snapshot: a single aggregated monthly_income,
aggregated monthly_obligations, single representative fico, single liquid_reserves
balance, plus a location triplet (state_fips/county_fips/county_name) and the
user's preferred_down_payment_pct. Plan 14-02 disambiguates downstream consumers
via `from lib.affordability import Household as AffordabilityHousehold` so the
two symbols never collide in the same scope. PATTERNS.md L105-108 is the
authority on this naming decision.

Field set (PATTERNS.md L104-117 + CONTEXT D-14-MODELS-01 + D-14-STRESS-02):
  - monthly_income: Money — aggregated gross monthly income across all earners
  - monthly_obligations: Money — aggregated auto + student + cc + other debts
  - fico: int in [300, 850] — representative score (mid-of-3 if 3 scores)
  - liquid_reserves: Money — cash/cash-equivalents available at close
  - state_fips: 2-digit FIPS code (LocationFIPS pattern from lib/affordability.py L347)
  - county_fips: 3-digit FIPS code
  - county_name: human-readable display
  - preferred_down_payment_pct: Rate, default Decimal("0.20") per D-14-STRESS-02

Excluded by design:
  - No escrow fields (those come from PropertyListing in Phase 13).
  - No applicants list (analysis flattens to a single household snapshot).
  - No va_eligible / first_time_buyer / military_status / filing_status /
    marginal_tax_rate — those live on lib/profile.py:Profile per D-14-MODELS-02
    (Profile carries analysis-time preferences + eligibility booleans; Household
    carries financial state).
  - No va_region / va_family_size / va_actual_residual_income — Plan 14-02
    synthesizes those deterministically inside _build_program_result (tagged with
    VA-RESIDUAL-SYNTHESIZED-V1 reason); keeping Household program-agnostic.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from lib.models import Money, Rate  # noqa: TC001  # Pydantic resolves field annotations at runtime


class Household(BaseModel):
    """Analysis-time household financial snapshot for Phase 14 `analyze()`.

    DISTINCT from lib.affordability.Household (Phase 4 frozen contract) — see
    module docstring. Plan 14-02 imports the affordability symbol as
    `AffordabilityHousehold` to keep both visible without name collision.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    monthly_income: Money
    monthly_obligations: Money
    fico: int = Field(ge=300, le=850)
    liquid_reserves: Money
    state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
    county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    county_name: str = Field(min_length=1)
    preferred_down_payment_pct: Rate = Field(
        default=Decimal("0.20"),
        description=(
            "User's preferred down-payment fraction. Drives D-14-STRESS-01 "
            "(stress tests run at preferred DP only) and Plan 14-04 verdict "
            "synthesis (D-14-VERDICT-03 'any non-FHA program eligible at "
            "preferred DP' rule). Default Decimal('0.20') per D-14-STRESS-02 "
            "when household.yml omits the field."
        ),
    )
