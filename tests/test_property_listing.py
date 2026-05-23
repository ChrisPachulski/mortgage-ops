"""Tests for lib/property_listing.py — PROP-01 + ProvenancedMoney wrapper.

Wave 1 (Plan 13-01) flips the Wave 0 xfail scaffold to live tests. Every
assertion proves a load-bearing property of the contract that Phase 14-15
plus Wave 2-5 of Phase 13 depend on:

  - D-13-MUSTHAVE-01: price + zip + property_type alone validates.
  - D-19 money discipline: Decimal serializes as JSON STRING, never float.
  - Pitfall 21: datetime serializes with 'Z' suffix (not '+00:00').
  - strict=True rejects float for Decimal-typed Money fields.
  - zip regex r'^\\d{5}$' rejects 4-digit zips.
  - property_type Literal rejects unknown values (e.g. "Manufactured").
  - baths must be on a 0.5 grid; 2.25 rejected, 2.5 accepted.
  - extra="forbid" rejects unknown fields.
  - frozen=True makes instances hashable.
  - ProvenancedMoney provenance Literal rejects unknown values.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from lib.property_listing import PropertyListing, ProvenancedMoney
from pydantic import ValidationError


def _make_min_listing(**overrides: Any) -> PropertyListing:
    """Factory: return a minimum-valid PropertyListing; overrides override any field.

    Defaults are MUST-HAVE-only (price + zip + property_type) plus the three
    audit fields required by the model (source_url, zpid, fetched_at).
    """
    defaults: dict[str, Any] = {
        "price": Decimal("625000.00"),
        "zip": "94110",
        "property_type": "SFH",
        "source_url": "https://www.zillow.com/homedetails/x/12345_zpid/",
        "zpid": "12345",
        "fetched_at": datetime(2026, 5, 10, 14, 30, 0, 123456, tzinfo=UTC),
    }
    defaults.update(overrides)
    return PropertyListing(**defaults)


# --- D-13-MUSTHAVE-01 baseline -------------------------------------------------


def test_must_haves_only_validates() -> None:
    """D-13-MUSTHAVE-01: price + zip + property_type validates; others default None."""
    listing = _make_min_listing()
    # MUST-HAVEs round-tripped
    assert listing.price == Decimal("625000.00")
    assert listing.zip == "94110"
    assert listing.property_type == "SFH"
    # NICE-TO-HAVE money fields default None
    assert listing.tax_annual is None
    assert listing.hoa_monthly is None
    assert listing.insurance_estimate_annual is None
    assert listing.zestimate is None
    # NICE-TO-HAVE non-money fields default None
    assert listing.beds is None
    assert listing.baths is None
    assert listing.sqft is None
    assert listing.year_built is None
    assert listing.days_on_market is None
    assert listing.list_date is None
    # And their sibling provenances
    assert listing.beds_provenance is None
    assert listing.baths_provenance is None


# --- PROP-02 baseline: byte-equal JSON round-trip -----------------------------


def test_round_trip_serialization_money_as_string() -> None:
    """PROP-02 baseline: model_dump_json -> Decimal-as-string; full byte-equal round-trip.

    Pydantic v2's default JSON output is compact (no whitespace around ':'),
    matching tests/test_models.py:103 — see `'"principal":"400000.00"'` there.
    """
    listing = _make_min_listing(
        tax_annual=ProvenancedMoney(value=Decimal("7800.00"), provenance="scraped"),
    )
    s = listing.model_dump_json()
    # CRITICAL: Decimal serialized as JSON STRING (D-19 money discipline)
    assert '"price":"625000.00"' in s
    # ProvenancedMoney.value also serialized as JSON STRING
    assert '"value":"7800.00"' in s
    # datetime serializes with 'Z' suffix (Pitfall 21)
    assert '"fetched_at":"2026-05-10T14:30:00.123456Z"' in s
    # Full byte-equal round-trip (frozen=True makes __eq__ available)
    assert PropertyListing.model_validate_json(s) == listing


# --- strict=True money discipline ---------------------------------------------


def test_rejects_float_price_strict_true() -> None:
    """strict=True must reject float for Decimal Money (CLAUDE.md money discipline)."""
    with pytest.raises(ValidationError):
        # Intentional type-system bypass via factory dict — strict=True is the runtime gate.
        _make_min_listing(price=625000.0)


def test_rejects_zero_price() -> None:
    """price=0 must raise — Money alias allows ge=0 for other uses, but a
    listing's price=0 would explode downstream LTV / cash-to-close denominators
    in lib/property_analysis.py. Boundary type rejects strictly."""
    with pytest.raises(ValidationError) as exc_info:
        _make_min_listing(price=Decimal("0"))
    # Validator emits a clear message naming the field and value.
    assert "Property price must be > 0" in str(exc_info.value)


# --- zip + property_type validators -------------------------------------------


def test_rejects_invalid_zip_and_property_type() -> None:
    """zip regex r'^\\d{5}$'; property_type Literal SFH|condo|townhouse|multifamily-2-4."""
    # 4-digit zip
    with pytest.raises(ValidationError):
        _make_min_listing(zip="9411")
    # Not in the Literal
    with pytest.raises(ValidationError):
        _make_min_listing(property_type="Manufactured")


# --- baths half-step validator -----------------------------------------------


def test_baths_half_step_validator() -> None:
    """baths must be on a 0.5 grid; 2.25 rejected, 2.5 accepted."""
    with pytest.raises(ValidationError):
        _make_min_listing(baths=Decimal("2.25"))
    # 2.5 accepted
    listing = _make_min_listing(baths=Decimal("2.5"))
    assert listing.baths == Decimal("2.5")


# --- net-new (Wave 1 additions) ----------------------------------------------


def test_serialized_baths_is_string_not_float() -> None:
    """field_serializer('baths') emits Decimal-as-string (D-19 money discipline)."""
    listing = _make_min_listing(baths=Decimal("2.5"))
    s = listing.model_dump_json()
    assert '"baths":"2.5"' in s


def test_provenanced_money_validates() -> None:
    """ProvenancedMoney(value=..., provenance=...) validates; value serializes as JSON string."""
    pm = ProvenancedMoney(value=Decimal("7800.00"), provenance="scraped")
    assert pm.value == Decimal("7800.00")
    assert pm.provenance == "scraped"
    assert '"value":"7800.00"' in pm.model_dump_json()


def test_provenanced_money_rejects_invalid_provenance() -> None:
    """ProvenancedMoney.provenance is a Literal — unknown members raise."""
    with pytest.raises(ValidationError):
        ProvenancedMoney(value=Decimal("7800.00"), provenance="invalid")  # type: ignore[arg-type]


def test_extra_field_forbidden() -> None:
    """extra='forbid' rejects unknown fields (Phase 1 D-19 inheritance)."""
    with pytest.raises(ValidationError):
        _make_min_listing(unknown_field="x")


def test_frozen_listing_is_hashable() -> None:
    """frozen=True makes the model hashable (usable as dict key / set member)."""
    listing = _make_min_listing()
    # hash() does not raise; instance is usable in a set
    assert hash(listing) is not None
    assert {listing} == {listing}


def test_fetched_at_z_suffix_not_plus_zero() -> None:
    """Pitfall 21: datetime serializes with 'Z' suffix, never '+00:00'."""
    listing = _make_min_listing()
    s = listing.model_dump_json()
    assert '"fetched_at":"2026-05-10T14:30:00.123456Z"' in s
    assert "+00:00" not in s


def test_user_provided_provenance_on_tax_annual() -> None:
    """ProvenancedMoney.provenance='user_provided' preserved through round-trip."""
    listing = _make_min_listing(
        tax_annual=ProvenancedMoney(value=Decimal("8200.00"), provenance="user_provided"),
    )
    assert listing.tax_annual is not None
    assert listing.tax_annual.value == Decimal("8200.00")
    assert listing.tax_annual.provenance == "user_provided"
    # Round-trip preserves provenance
    s = listing.model_dump_json()
    restored = PropertyListing.model_validate_json(s)
    assert restored.tax_annual is not None
    assert restored.tax_annual.provenance == "user_provided"
