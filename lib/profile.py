"""Phase 14 Profile model — analysis-time eligibility + preferences.

D-14-MODELS-02 (Claude's Discretion resolution): the Profile model carries
va_eligible + first_time_buyer + military_status + filing_status +
marginal_tax_rate. Split from lib.household.Household because these are
USER PREFERENCES and PROGRAM-ELIGIBILITY BOOLEANS, not financial state.
Household = "what I earn / owe / saved / where I live"; Profile = "who I am
for program eligibility + what tax bracket I'm in."

PATTERNS.md L153 records the rationale: when downstream Phase 14 plans read
the analysis-time inputs, Household fields and Profile fields cluster
distinctly (financial state vs eligibility/preferences). Mixing them on a
single Pydantic model muddies the two concerns.

Field set (PATTERNS.md L156-161 + CONTEXT D-14-MODELS-02):
  - va_eligible: bool (default False) — gates the VA30 4th program row in
    Plan 14-02 fan-out (Conv30/Conv15/FHA30/VA30 base programs).
  - first_time_buyer: bool (default False) — informational flag for downstream
    FHA UFMIP exemptions / state-DPA hooks in future phases.
  - military_status: MilitaryStatus Literal (default "none") — used by Plan
    14-02 VA funding-fee lookup (first-use vs subsequent-use; veteran vs reserve).
  - filing_status: FilingStatus Literal (default "mfj") — drives the IRS Pub 936
    deductibility computation in Plan 14-03 TaxBlock.
  - marginal_tax_rate: Rate | None (default None) — when set, Plan 14-03 multiplies
    against first-year deductible interest to estimate after-tax savings.

Excluded by design:
  - display_money_format / display_rate_format — formatter concerns deferred to
    Phase 15 (RESEARCH.md L475-477; not consumed by analyze()).
  - IRS Pub 936 grandfathering booleans — Pitfall 11 confirms v1.1 scope is
    purely post-2017 acquisition; defaults of qualified_loan_limit() suffice.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from lib.models import Rate  # noqa: TC001  # Pydantic resolves field annotations at runtime

# Module-level Literal aliases (PATTERNS.md L147-149 idiom; mirrors PropertyType
# in lib/property_listing.py L25 and TargetLoanType in lib/affordability.py L239).
MilitaryStatus = Literal["active", "veteran", "reserve", "none"]
FilingStatus = Literal["single", "mfj", "mfs", "hoh"]


class Profile(BaseModel):
    """Analysis-time eligibility + preferences for Phase 14 `analyze()`.

    Split from Household per D-14-MODELS-02 because these are user preferences
    and program-eligibility booleans, NOT financial state (PATTERNS.md L153).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    va_eligible: bool = False
    first_time_buyer: bool = False
    military_status: MilitaryStatus = "none"
    filing_status: FilingStatus = "mfj"
    marginal_tax_rate: Rate | None = None
