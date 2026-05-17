"""PropertyListing Pydantic v2 model. Phase 13 PROP-01.

Mirrors lib/models.py shape: strict=True, frozen=True, extra="forbid".
MUST-HAVE per D-13-MUSTHAVE-01: price + zip + property_type. All other fields
default to None and are NICE-TO-HAVE.

Money fields:
  - `price` is bare Money (shape-1 envelope by definition means scraped).
  - NICE-TO-HAVE money fields use the ProvenancedMoney wrapper (value + provenance).

Non-money NICE-TO-HAVE fields use a sibling `*_provenance` field per
CONTEXT.md specifics §3 — wrappers on non-money fields would be over-engineering.
"""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003  # Pydantic resolves annotations at runtime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from lib.models import Money  # noqa: TC001  # Pydantic resolves annotations at runtime

PropertyType = Literal["SFH", "condo", "townhouse", "multifamily-2-4"]
Provenance = Literal["scraped", "user_provided", "estimated", "unknown"]


class ProvenancedMoney(BaseModel):
    """Money field with attribution. Used for NICE-TO-HAVE money fields only.

    The MUST-HAVE `price` on PropertyListing is unwrapped Money — a shape-1
    envelope by definition means price was scraped (the gap-fill path emits
    shape-2 if price is missing, so a successful PropertyListing's price is
    always scraped or user_provided via the merge step).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    value: Money | None
    provenance: Provenance


class PropertyListing(BaseModel):
    """Validated Zillow listing. PROP-01.

    Field grouping per D-13-MUSTHAVE-01:
      - MUST-HAVE: price, zip, property_type
      - NICE-TO-HAVE money (ProvenancedMoney wrapper): tax_annual, hoa_monthly,
        insurance_estimate_annual, zestimate
      - NICE-TO-HAVE non-money + sibling *_provenance: beds, baths, sqft,
        year_built, days_on_market, list_date
      - Audit: source_url, zpid, fetched_at
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    # MUST-HAVE
    price: Money
    zip: Annotated[str, Field(pattern=r"^\d{5}$")]
    property_type: PropertyType

    # NICE-TO-HAVE money (ProvenancedMoney wrappers, default None)
    tax_annual: ProvenancedMoney | None = None
    hoa_monthly: ProvenancedMoney | None = None
    insurance_estimate_annual: ProvenancedMoney | None = None
    zestimate: ProvenancedMoney | None = None

    # NICE-TO-HAVE non-money + sibling provenance
    beds: int | None = Field(default=None, ge=0, le=20)
    beds_provenance: Provenance | None = None
    baths: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("20"))
    baths_provenance: Provenance | None = None
    sqft: int | None = Field(default=None, gt=0, le=50_000)
    sqft_provenance: Provenance | None = None
    year_built: int | None = Field(default=None, ge=1700, le=2030)
    year_built_provenance: Provenance | None = None
    days_on_market: int | None = Field(default=None, ge=0, le=10_000)
    days_on_market_provenance: Provenance | None = None
    list_date: date | None = None
    list_date_provenance: Provenance | None = None

    # Audit
    source_url: str = Field(min_length=10)
    zpid: Annotated[str, Field(pattern=r"^\d+$")]
    fetched_at: datetime

    @field_validator("baths")
    @classmethod
    def _baths_half_step(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if (v * 2) % 1 != 0:
            raise ValueError(f"baths must be 0.5 increments; got {v}")
        return v

    @field_serializer("baths")
    def _serialize_baths(self, v: Decimal | None) -> str | None:
        # D-19 money discipline: Decimal -> JSON STRING, not float.
        return str(v) if v is not None else None

    @field_serializer("fetched_at")
    def _serialize_dt(self, v: datetime) -> str:
        # Pitfall 21: pin Z suffix to match Phase 12 _now_utc convention.
        return v.isoformat().replace("+00:00", "Z")
