"""Tests for lib/property_listing.py — PROP-01 + ProvenancedMoney wrapper.

Wave 0 xfail scaffold; Wave 1 (Plan 13-01) flips green.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Phase 13 Wave 1: lib/property_listing.py not yet built", strict=True)
def test_must_haves_only_validates() -> None:
    """D-13-MUSTHAVE-01: price + zip + property_type validates; others default None."""
    from lib.property_listing import PropertyListing  # noqa: F401

    raise AssertionError("Wave 1 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 1: lib/property_listing.py not yet built", strict=True)
def test_round_trip_serialization_money_as_string() -> None:
    """PROP-02 baseline: model_dump_json -> '"price": "625000.00"' (D-19 money discipline)."""
    from lib.property_listing import PropertyListing  # noqa: F401

    raise AssertionError("Wave 1 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 1: lib/property_listing.py not yet built", strict=True)
def test_rejects_float_price_strict_true() -> None:
    """strict=True must reject float for Decimal Money (CLAUDE.md Money discipline)."""
    from lib.property_listing import PropertyListing  # noqa: F401

    raise AssertionError("Wave 1 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 1: lib/property_listing.py not yet built", strict=True)
def test_rejects_invalid_zip_and_property_type() -> None:
    """zip regex r'^\\d{5}$'; property_type Literal SFH|condo|townhouse|multifamily-2-4."""
    from lib.property_listing import PropertyListing  # noqa: F401

    raise AssertionError("Wave 1 fills body")


@pytest.mark.xfail(reason="Phase 13 Wave 1: lib/property_listing.py not yet built", strict=True)
def test_baths_half_step_validator() -> None:
    """baths must be 0.5 increments; 2.25 rejected, 2.5 accepted."""
    from lib.property_listing import PropertyListing  # noqa: F401

    raise AssertionError("Wave 1 fills body")
