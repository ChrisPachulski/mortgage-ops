"""Phase 14 property-analysis pipeline — Wave 1 tests (ANLZ-01, ANLZ-02).

Wave 1 (Plan 14-02) covers ONLY matrix-shape, cell-numeric, eligibility-gating,
and basic composition invariants. Stress / refi / points / tax / verdict
tests are stubbed and deferred to Plans 14-03..14-06.

Per CLAUDE.md money discipline: exact Decimal equality only; never
``pytest.approx`` or ``assertAlmostEqual``. Per RESEARCH Pitfall 2:
every Decimal in this file is constructed from a string literal.

Test taxonomy:
  - Wave-0 (Task 1 of Plan 14-02): model + module-constant contract tests.
  - Wave-1 (Task 2 of Plan 14-02): per-cell composition + matrix builder
    + iteration-2 fixes (B-2 VA-construction, B-3 PropertyListing
    defaults, B-4 ProvenancedMoney unwrap, W-3 VA financed funding fee).
  - Wave-2+ (Plan 14-03..14-06): stress / refi / points / tax / verdict
    / golden fixtures — stubbed below with ``pytest.skip``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
from lib.household import Household
from lib.money import quantize_rate
from lib.profile import Profile
from lib.property_analysis import (
    _CONV_5_1_ARM_TERMS,
    _CONV_PMI_ANNUAL_RATE,
    _DTI_CEILING_BY_PROGRAM,
    DOWN_PAYMENT_PCTS,
    PROGRAMS_BASE,
    AnalysisReport,
    DownPaymentMatrix,
    PointsBlock,
    PointsRow,
    ProgramResult,
    RefiBlock,
    RefiRow,
    StressBlock,
    StressRow,
    TaxBlock,
    Verdict,
    VerdictReason,
    _build_matrix,
    _build_points_block,
    _build_program_result,
    _build_refi_block,
    _build_stress_block,
    _build_tax_block,
    _determine_programs,
    _todays_rate_per_program,
    _unwrap_provenanced,
    analyze,
)
from lib.property_listing import PropertyListing, PropertyType, ProvenancedMoney
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Wave-0 — model + module-constant contract tests (Task 1 deliverable)
# ---------------------------------------------------------------------------


def test_models_importable() -> None:
    """All 12 output models + 5 module constants + analyze stub import."""
    assert ProgramResult is not None
    assert DownPaymentMatrix is not None
    assert StressRow is not None
    assert StressBlock is not None
    assert RefiRow is not None
    assert RefiBlock is not None
    assert PointsRow is not None
    assert PointsBlock is not None
    assert TaxBlock is not None
    assert Verdict is not None
    assert VerdictReason is not None
    assert AnalysisReport is not None
    assert analyze is not None


def test_module_constants() -> None:
    """DOWN_PAYMENT_PCTS / PROGRAMS_BASE / _CONV_PMI_ANNUAL_RATE / _CONV_5_1_ARM_TERMS values exact."""
    assert [
        Decimal("0.03"),
        Decimal("0.05"),
        Decimal("0.10"),
        Decimal("0.15"),
        Decimal("0.20"),
        Decimal("0.25"),
    ] == DOWN_PAYMENT_PCTS
    assert PROGRAMS_BASE == ["Conv30", "Conv15", "FHA30"]
    assert Decimal("0.0075") == _CONV_PMI_ANNUAL_RATE
    assert _CONV_5_1_ARM_TERMS.initial_period_months == 60
    assert _CONV_5_1_ARM_TERMS.reset_period_months == 12
    assert _CONV_5_1_ARM_TERMS.initial_cap_bps == 500
    assert _CONV_5_1_ARM_TERMS.periodic_cap_bps == 200
    assert _CONV_5_1_ARM_TERMS.lifetime_cap_bps == 500
    assert _CONV_5_1_ARM_TERMS.floor_rate == Decimal("0.025")
    assert _CONV_5_1_ARM_TERMS.margin_bps == 250
    assert _CONV_5_1_ARM_TERMS.index_series_id == "MORTGAGE30US"


def test_analyze_end_to_end() -> None:
    """Plan 14-05 Task 1 RED->GREEN: analyze() composes the 6-step pipeline into
    a fully-populated AnalysisReport. SFH-conforming King County WA scenario;
    FRED rates passed explicitly so the test does not hit the cache."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )

    assert isinstance(report, AnalysisReport)
    # 3 base programs x 6 DPs = 18 cells (non-jumbo, non-VA-eligible).
    assert len(report.matrix.cells) == 18
    # Eligible programs at preferred DP drive auxiliary block counts.
    eligible_at_preferred = [
        c for c in report.matrix.cells if c.down_payment_pct == Decimal("0.200000") and c.eligible
    ]
    n_eligible = len(eligible_at_preferred)
    # Stress: 2 stresses (rate + income) per eligible program + 1 ARM-reset if Conv30 eligible.
    n_conv30_eligible = sum(1 for c in eligible_at_preferred if c.program == "Conv30")
    assert len(report.stress.rows) == 2 * n_eligible + n_conv30_eligible
    # Refi + points: 2 rows per eligible program.
    assert len(report.refi.rows) == 2 * n_eligible
    assert len(report.points.rows) == 2 * n_eligible
    # Tax block uses default mfj filing -> $750k cap.
    assert report.tax.qualified_loan_limit == Decimal("750000.00")
    # Verdict is one of the three allowed letters.
    assert report.verdict.level in {"GO", "WATCH", "NO_GO"}
    # Snapshot hash: 64-char lowercase hex.
    assert len(report.household_snapshot_hash) == 64
    assert all(c in "0123456789abcdef" for c in report.household_snapshot_hash)
    # fetched_at is timezone-aware (UTC).
    assert report.fetched_at.tzinfo is not None
    # Echoed FRED rates match the overrides (post-quantize).
    assert report.fred_mortgage_30us == quantize_rate(Decimal("0.065000"))
    assert report.fred_mortgage_15us == quantize_rate(Decimal("0.058000"))
    # listing_snapshot echoed by frozen-model equality.
    assert report.listing_snapshot == listing


def test_program_result_validates_with_clean_inputs() -> None:
    """ProgramResult accepts a clean Conv30-at-20%-DP inputs (Behavior 7)."""
    pr = ProgramResult(
        program="Conv30",
        down_payment_pct=Decimal("0.200000"),
        loan_amount=Decimal("500000.00"),
        monthly_pi=Decimal("3160.34"),
        monthly_tax=Decimal("500.00"),
        monthly_insurance=Decimal("100.00"),
        monthly_hoa=Decimal("0.00"),
        monthly_mi=Decimal("0.00"),
        piti=Decimal("3760.34"),
        cash_to_close=Decimal("125000.00"),
        dti_back=Decimal("0.350000"),
        ltv=Decimal("0.800000"),
        eligible=True,
    )
    assert pr.program == "Conv30"
    assert pr.eligible is True
    assert pr.blocker_reasons == []
    assert pr.eligible_reasons == []
    assert pr.closing_costs_estimated is True


def test_program_result_rejects_unknown_program_literal() -> None:
    """ProgramResult enforces program Literal (Behavior 8)."""
    with pytest.raises(ValidationError):
        ProgramResult(
            program="not_a_program",  # type: ignore[arg-type]
            down_payment_pct=Decimal("0.200000"),
            loan_amount=Decimal("500000.00"),
            monthly_pi=Decimal("3160.34"),
            monthly_tax=Decimal("500.00"),
            monthly_insurance=Decimal("100.00"),
            monthly_hoa=Decimal("0.00"),
            monthly_mi=Decimal("0.00"),
            piti=Decimal("3760.34"),
            cash_to_close=Decimal("125000.00"),
            dti_back=Decimal("0.350000"),
            ltv=Decimal("0.800000"),
            eligible=True,
        )


def test_refi_row_accepts_signed_decimal_savings() -> None:
    """RefiRow.monthly_savings and .npv_60mo are signed Decimals (Pitfall 3)."""
    row = RefiRow(
        program="Conv30",
        target_rate=Decimal("0.055000"),
        scenario_label="minus_100bps",
        monthly_savings=Decimal("-150.00"),
        npv_60mo=Decimal("-2500.00"),
    )
    assert row.monthly_savings == Decimal("-150.00")
    assert row.npv_60mo == Decimal("-2500.00")


def test_verdict_reason_accepts_string_computed_value() -> None:
    """VerdictReason.computed_value is a string (polymorphic numeric)."""
    vr = VerdictReason(
        predicate_code="DTI-CAP-CONVENTIONAL",
        computed_value="0.510000",
        program="Conv30",
        dp_pct=Decimal("0.200000"),
    )
    assert vr.predicate_code == "DTI-CAP-CONVENTIONAL"
    assert vr.computed_value == "0.510000"


def test_verdict_rejects_unknown_level_literal() -> None:
    """Verdict.level enforces Literal["GO", "WATCH", "NO_GO"] (Behavior 11)."""
    Verdict(level="GO", headline_reason="x", reasons=[])  # accepted
    with pytest.raises(ValidationError):
        Verdict(level="MAYBE", headline_reason="x", reasons=[])  # type: ignore[arg-type]


def test_program_result_rejects_float_on_money_field() -> None:
    """strict=True rejects Python float on Money/Rate fields (Pitfall 2)."""
    with pytest.raises(ValidationError):
        ProgramResult(
            program="Conv30",
            down_payment_pct=0.2,  # type: ignore[arg-type]
            loan_amount=Decimal("500000.00"),
            monthly_pi=Decimal("3160.34"),
            monthly_tax=Decimal("500.00"),
            monthly_insurance=Decimal("100.00"),
            monthly_hoa=Decimal("0.00"),
            monthly_mi=Decimal("0.00"),
            piti=Decimal("3760.34"),
            cash_to_close=Decimal("125000.00"),
            dti_back=Decimal("0.350000"),
            ltv=Decimal("0.800000"),
            eligible=True,
        )


# ---------------------------------------------------------------------------
# Wave-1 helper builders (Task 2/3 deliverable)
# ---------------------------------------------------------------------------


def _make_clean_household(**overrides: Any) -> Household:
    """Build a Phase-14 Household with sensible defaults; overrides override."""
    defaults: dict[str, Any] = {
        "monthly_income": Decimal("12000.00"),
        "monthly_obligations": Decimal("400.00"),
        "fico": 740,
        "liquid_reserves": Decimal("200000.00"),
        "state_fips": "53",
        "county_fips": "033",
        "county_name": "King",
        "preferred_down_payment_pct": Decimal("0.200000"),
    }
    defaults.update(overrides)
    return Household(**defaults)


def _make_clean_profile(**overrides: Any) -> Profile:
    """Build a Phase-14 Profile with sensible defaults; overrides override."""
    return Profile(**overrides)


def _make_clean_listing(
    price: str = "625000.00",
    zip: str = "98101",
    property_type: PropertyType = "SFH",
    source_url: str = "https://www.zillow.com/homedetails/synthetic/1_zpid/",
    zpid: str = "1",
    fetched_at: datetime | None = None,
    **provenanced_overrides: Any,
) -> PropertyListing:
    """Build a Phase-13-valid PropertyListing for use in Phase-14 tests.

    B-3 fix: source_url / zpid / fetched_at are REQUIRED per
    lib/property_listing.py L84-86. Defaulted here so callers don't have to
    enumerate them.

    ``provenanced_overrides`` routes to NICE-TO-HAVE money fields (e.g.,
    tax_annual=ProvenancedMoney(value=..., provenance="estimated")).
    """
    if fetched_at is None:
        fetched_at = datetime(2026, 5, 17, tzinfo=UTC)
    return PropertyListing(
        price=Decimal(price),
        zip=zip,
        property_type=property_type,
        source_url=source_url,
        zpid=zpid,
        fetched_at=fetched_at,
        **provenanced_overrides,
    )


def _make_jumbo_listing() -> PropertyListing:
    """Listing above 2026 King County conforming limit ($1,027,000)."""
    return _make_clean_listing(price="1500000.00")


_TEST_RATE: Decimal = Decimal("0.065000")
"""Pinned annual_rate for unit tests — bypasses FRED dependency."""


def _make_test_rates() -> dict[str, Decimal]:
    """Pinned per-program rates dict — bypasses FRED dependency in block tests."""
    return {
        "Conv30": Decimal("0.065000"),
        "Conv15": Decimal("0.058000"),
        "FHA30": Decimal("0.065000"),
        "VA30": Decimal("0.065000"),
        "Jumbo30": Decimal("0.065000"),
        "Conv30-ARM-5-1": Decimal("0.062500"),
    }


# ---------------------------------------------------------------------------
# Wave-1 matrix shape + composition tests
# ---------------------------------------------------------------------------


def test_matrix_cell_count() -> None:
    """Non-jumbo + va_eligible=False -> 18 cells (3 programs x 6 DPs)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    rates = {p: _TEST_RATE for p in PROGRAMS_BASE}
    matrix, warnings = _build_matrix(listing, household, profile, rates)
    assert len(matrix.cells) == 18
    assert matrix.programs_present == ["Conv30", "Conv15", "FHA30"]
    assert warnings == []


def test_matrix_fanout_conforming() -> None:
    """Each base program contributes exactly 6 cells."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    rates = {p: _TEST_RATE for p in PROGRAMS_BASE}
    matrix, _ = _build_matrix(listing, household, profile, rates)
    for prog in ("Conv30", "Conv15", "FHA30"):
        assert sum(1 for c in matrix.cells if c.program == prog) == 6


def test_va_eligibility_gates_program() -> None:
    """Profile(va_eligible=True) appends VA30; False omits it."""
    household = _make_clean_household()
    listing = _make_clean_listing()

    programs_no_va, _ = _determine_programs(
        listing, household, _make_clean_profile(va_eligible=False)
    )
    assert "VA30" not in programs_no_va

    programs_with_va, _ = _determine_programs(
        listing, household, _make_clean_profile(va_eligible=True)
    )
    assert "VA30" in programs_with_va


def test_jumbo_trigger_at_county_limit() -> None:
    """listing.price > King County conforming → Jumbo30 in programs."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_jumbo_listing()
    programs, warnings = _determine_programs(listing, household, profile)
    assert "Jumbo30" in programs
    assert warnings == []


def test_missing_county_graceful() -> None:
    """MissingCountyDataError from classify_loan_type is caught — base programs
    returned + "MissingCountyDataError" appended to warnings (no exception).

    Note: the conventional classifier's silent-fallback to baseline (per
    lib/rules/loan_type.py:_county_limit) means a real unlisted-county +
    loan-above-baseline does NOT raise — it returns "jumbo". MissingCountyDataError
    only fires when county is None in conventional (we always pass a non-None
    County) or in FHA classification with a not-listed high-cost county. To prove
    the catch-and-warn behavior independent of the source exception, we monkey-
    patch classify_loan_type to raise.
    """
    from lib.rules.loan_type import MissingCountyDataError as MCDE

    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()

    def _raise_mcde(*_args: object, **_kwargs: object) -> None:
        raise MCDE("synthetic - county not in shipped table")

    with patch("lib.property_analysis.classify_loan_type", _raise_mcde):
        programs, warnings = _determine_programs(listing, household, profile)

    # No exception — base programs returned, warning surfaced.
    assert programs == list(PROGRAMS_BASE)
    assert "MissingCountyDataError" in warnings


def test_ineligible_rows_populate_numerics() -> None:
    """D-14-MATRIX-02: ineligible rows still populate piti / dti / ltv."""
    # Low-income household + expensive listing forces DTI breach.
    # Moderate income + moderate listing: DTI breaches but stays within Rate's le=1.
    household = _make_clean_household(
        monthly_income=Decimal("6000.00"), monthly_obligations=Decimal("500.00")
    )
    profile = _make_clean_profile()
    listing = _make_clean_listing(price="500000.00")
    cell = _build_program_result("Conv30", Decimal("0.03"), listing, household, profile, _TEST_RATE)
    assert cell.eligible is False
    assert cell.piti > Decimal("0.00")
    assert cell.dti_back > Decimal("0")
    assert cell.ltv > Decimal("0")
    assert cell.blocker_reasons  # at least one citation


def test_dp_sweep_uses_decimal_strings() -> None:
    """Every cell.down_payment_pct is a Decimal exactly in DOWN_PAYMENT_PCTS
    (Pitfall 2 — no float contamination)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    rates = {p: _TEST_RATE for p in PROGRAMS_BASE}
    matrix, _ = _build_matrix(listing, household, profile, rates)
    for cell in matrix.cells:
        assert isinstance(cell.down_payment_pct, Decimal)
        # quantize_rate may have padded; the underlying value must match a
        # DOWN_PAYMENT_PCTS entry once compared by numeric equality.
        assert cell.down_payment_pct in DOWN_PAYMENT_PCTS


def test_mi_included_in_piti() -> None:
    """Pitfall 6: PITI = monthly_pi + monthly_tax + monthly_insurance +
    monthly_hoa + monthly_mi, quantized ONCE; LTV>0.80 produces monthly_mi>0."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    cell = _build_program_result("Conv30", Decimal("0.05"), listing, household, profile, _TEST_RATE)
    assert cell.monthly_mi > Decimal("0.00")
    from lib.money import quantize_cents

    expected = quantize_cents(
        cell.monthly_pi
        + cell.monthly_tax
        + cell.monthly_insurance
        + cell.monthly_hoa
        + cell.monthly_mi
    )
    assert cell.piti == expected


def test_fha_cell_ufmip_financed_into_principal() -> None:
    """FHA30 financed loan_amount > base loan (UFMIP added per Phase 4 D-03)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing(price="400000.00")
    cell = _build_program_result("FHA30", Decimal("0.035"), listing, household, profile, _TEST_RATE)
    base_loan_amount = Decimal("400000.00") * Decimal("0.965")
    assert cell.loan_amount > base_loan_amount


def test_conv_pmi_warning_surfaces() -> None:
    """Conv30 at 5% DP tags eligible_reasons with PMI-RATE-ESTIMATED-0.0075."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    cell = _build_program_result("Conv30", Decimal("0.05"), listing, household, profile, _TEST_RATE)
    assert "PMI-RATE-ESTIMATED-0.0075" in cell.eligible_reasons


def test_float_rejection() -> None:
    """Constructing ProgramResult with a float on Money/Rate raises ValidationError."""
    with pytest.raises(ValidationError):
        ProgramResult(
            program="Conv30",
            down_payment_pct=Decimal("0.200000"),
            loan_amount=500000.00,  # type: ignore[arg-type]
            monthly_pi=Decimal("3160.34"),
            monthly_tax=Decimal("500.00"),
            monthly_insurance=Decimal("100.00"),
            monthly_hoa=Decimal("0.00"),
            monthly_mi=Decimal("0.00"),
            piti=Decimal("3760.34"),
            cash_to_close=Decimal("125000.00"),
            dti_back=Decimal("0.350000"),
            ltv=Decimal("0.800000"),
            eligible=True,
        )


def test_blocker_reason_verbatim() -> None:
    """blocker_reasons[0] is exactly the affordability blocked_by string."""
    # Moderate income + moderate listing: DTI breaches but stays within Rate's le=1.
    household = _make_clean_household(
        monthly_income=Decimal("6000.00"), monthly_obligations=Decimal("500.00")
    )
    profile = _make_clean_profile()
    listing = _make_clean_listing(price="500000.00")
    cell = _build_program_result("Conv30", Decimal("0.03"), listing, household, profile, _TEST_RATE)
    assert cell.eligible is False
    # Verbatim citation — uppercase, hyphen-separated, no reformatting.
    assert cell.blocker_reasons
    # The citation prefix should be one of the known affordability blocker codes.
    blocker = cell.blocker_reasons[0]
    assert any(
        blocker.startswith(prefix)
        for prefix in (
            "DTI-CAP-",
            "LTV-CEILING-",
            "CLTV-CEILING-",
            "FHFA-LIMIT-",
            "HUD-LIMIT-",
            "ATR-QM-",
        )
    )


def test_fred_lock_serialization() -> None:
    """_todays_rate_per_program invokes with_cache_lock with reason containing
    'property-analysis read'."""
    with patch("lib.property_analysis.with_cache_lock") as mock_lock:
        mock_lock.return_value.__enter__.return_value = {"acquired_at": 0}
        with patch("lib.property_analysis.get_cached_or_fetch") as mock_fetch:
            mock_fetch.return_value = {"value": "0.06500"}
            _todays_rate_per_program("Conv30")
    assert mock_lock.called
    call_kwargs = mock_lock.call_args.kwargs
    reason = call_kwargs.get("reason", "")
    assert "property-analysis read" in reason


def test_fred_cold_cache_raises_valueerror_with_guidance() -> None:
    """Cold cache → ValueError with scripts/fred_cli.py guidance."""
    with patch("lib.property_analysis.with_cache_lock") as mock_lock:
        mock_lock.return_value.__enter__.return_value = {"acquired_at": 0}
        with patch("lib.property_analysis.get_cached_or_fetch") as mock_fetch:
            mock_fetch.side_effect = NotImplementedError("cold")
            with pytest.raises(ValueError, match=r"scripts/fred_cli\.py") as exc:
                _todays_rate_per_program("Conv30")
            assert "scripts/fred_cli.py" in str(exc.value)


def test_va_cell_constructs_valid_affordability_request() -> None:
    """B-2: VA cells construct VAInputs deterministically; affordability
    eval does NOT raise 'household.va block is required'."""
    household = _make_clean_household()
    profile = _make_clean_profile(va_eligible=True)
    listing = _make_clean_listing()
    cell = _build_program_result("VA30", Decimal("0.05"), listing, household, profile, _TEST_RATE)
    # No exception raised; Phase 14 marks missing VA residual inputs explicitly.
    assert "VA-RESIDUAL-NOT-SUPPLIED" in cell.blocker_reasons
    assert "VA-FUNDING-FEE-FINANCED" in cell.eligible_reasons


def test_matrix_eligibility_uses_per_program_dti_ceiling() -> None:
    """B-5 follow-on: matrix eligibility must thread the per-program DTI ceiling
    through ForwardModeRequest.max_dti — NOT a hardcoded 0.500000.

    A household tuned so DTI sits between VA's 0.41 (block) and Conventional's
    0.50 (eligible) proves the lookup is wired correctly: same household, same
    listing, same DP — Conv30 stays eligible, VA30 blocks with DTI-CAP-VA.
    Under the previous hardcoded max_dti=0.50, VA30 would have been silently
    marked eligible.
    """
    # Tuned so back-end DTI lands roughly at 0.46 — above 0.41 (VA), below 0.50
    # (Conv). Listing kept low enough that 20% DP works against $5k income.
    household = _make_clean_household(
        monthly_income=Decimal("5000.00"),
        monthly_obligations=Decimal("300.00"),
    )
    profile = _make_clean_profile(va_eligible=True)
    listing = _make_clean_listing(price="400000.00")

    conv30_cell = _build_program_result(
        "Conv30", Decimal("0.20"), listing, household, profile, _TEST_RATE
    )
    va30_cell = _build_program_result(
        "VA30", Decimal("0.20"), listing, household, profile, _TEST_RATE
    )

    # Sanity: both cells land in the band we designed for. If this fails the
    # fixture drifted; pin the band rather than the exact value so small
    # changes to escrow / funding-fee math don't bit-rot the test.
    assert Decimal("0.41") < conv30_cell.dti_back < Decimal("0.50"), (
        f"Conv30 DTI {conv30_cell.dti_back} not in (0.41, 0.50) band — fixture drifted"
    )
    assert Decimal("0.41") < va30_cell.dti_back < Decimal("0.50"), (
        f"VA30 DTI {va30_cell.dti_back} not in (0.41, 0.50) band — fixture drifted"
    )

    # Conv30 eligible because its ceiling is 0.50 and DTI < 0.50.
    assert conv30_cell.eligible is True, (
        f"Conv30 should be eligible (DTI {conv30_cell.dti_back} < 0.50 ceiling); "
        f"got blockers: {conv30_cell.blocker_reasons}"
    )

    # VA30 blocked because its ceiling is 0.41 and DTI > 0.41. Blocker must
    # come from the DTI cap predicate — DTI-CAP-VA verbatim. Under the old
    # hardcoded max_dti=0.50 this cell would have been silently eligible.
    assert va30_cell.eligible is False, (
        f"VA30 should block on DTI cap (DTI {va30_cell.dti_back} > 0.41 ceiling)"
    )
    assert any("DTI-CAP-VA" in r for r in va30_cell.blocker_reasons), (
        f"expected DTI-CAP-VA in blocker_reasons; got {va30_cell.blocker_reasons}"
    )


def test_provenanced_value_none_unwraps_to_zero() -> None:
    """B-4: ProvenancedMoney(value=None, ...) and None wrappers both unwrap
    to Decimal('0.00') in escrow paths without raising TypeError."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing(
        tax_annual=ProvenancedMoney(value=None, provenance="unknown"),
        hoa_monthly=None,
        insurance_estimate_annual=ProvenancedMoney(value=None, provenance="unknown"),
    )
    cell = _build_program_result("Conv30", Decimal("0.20"), listing, household, profile, _TEST_RATE)
    assert cell.monthly_tax == Decimal("0.00")
    assert cell.monthly_hoa == Decimal("0.00")
    assert cell.monthly_insurance == Decimal("0.00")


def test_unwrap_provenanced_handles_none_wrapper() -> None:
    """B-4 unit-level: _unwrap_provenanced(None) returns the default."""
    assert _unwrap_provenanced(None) == Decimal("0.00")
    assert _unwrap_provenanced(None, default=Decimal("5.00")) == Decimal("5.00")
    pm_with_none = ProvenancedMoney(value=None, provenance="unknown")
    assert _unwrap_provenanced(pm_with_none) == Decimal("0.00")
    pm_with_value = ProvenancedMoney(value=Decimal("100.00"), provenance="scraped")
    assert _unwrap_provenanced(pm_with_value) == Decimal("100.00")


# ---------------------------------------------------------------------------
# Wave-2+ stubs (Plans 14-03 / 14-04 / 14-05 / 14-06 deliverables)
#
# These tests exist for shape stability: ``pytest --collect-only`` should list
# them so the full Phase-14 test surface is visible up-front. Each body is a
# pytest.skip with a pointer to the plan that flips it green.
# ---------------------------------------------------------------------------


def test_stress_at_preferred_dp_only() -> None:
    """D-14-STRESS-01: stress block fans out at preferred DP only — every stress
    row references a cell whose down_payment_pct equals
    household.preferred_down_payment_pct AND eligible=True; no rows reference
    ineligible cells or non-preferred DP cells."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    stress = _build_stress_block(matrix, listing, household, profile, todays_rates)

    # Block carries the preferred DP marker.
    assert stress.preferred_down_payment_pct == Decimal("0.200000")

    eligible_programs_at_preferred_dp = {
        c.program for c in matrix.cells if c.down_payment_pct == Decimal("0.200000") and c.eligible
    }
    # Every row's program is in the eligible-at-preferred-DP set.
    for row in stress.rows:
        assert row.program in eligible_programs_at_preferred_dp, (
            f"stress row for {row.program} references a program NOT eligible at preferred DP"
        )

    # Each program in the eligible-at-preferred set gets at least 2 rows
    # (rate_shock + income_shock), and exactly one of them gets an arm_reset
    # (Conv30 only). Total = 2 * n_eligible + (1 if Conv30 eligible else 0).
    n_eligible = len(eligible_programs_at_preferred_dp)
    expected_total = 2 * n_eligible + (1 if "Conv30" in eligible_programs_at_preferred_dp else 0)
    assert len(stress.rows) == expected_total


def test_arm_reset_conv30_only() -> None:
    """D-14-STRESS-03: ARM-reset stress fires for Conv30 only. With the clean
    fixture, all 3 base programs are eligible at 20% DP, so we expect exactly
    one arm_reset row and it's for Conv30."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    stress = _build_stress_block(matrix, listing, household, profile, todays_rates)

    arm_reset_rows = [r for r in stress.rows if r.stress_kind == "arm_reset"]
    # Conv30 is eligible at 20% DP in the clean fixture, so exactly one arm_reset row.
    assert len(arm_reset_rows) == 1
    assert all(r.program == "Conv30" for r in arm_reset_rows)


def test_refi_two_scenarios_per_program() -> None:
    """D-14-REFI-03: refi block emits two scenarios per eligible-at-preferred-DP
    program — one ``minus_100bps`` (FRED-1.00) and one ``fred_times_0_85``
    (FREDx0.85)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    refi = _build_refi_block(matrix, household, todays_rates)

    eligible_programs_at_preferred_dp = {
        c.program for c in matrix.cells if c.down_payment_pct == Decimal("0.200000") and c.eligible
    }
    # Exactly 2 rows per eligible-at-preferred-DP program.
    assert len(refi.rows) == 2 * len(eligible_programs_at_preferred_dp)
    for program in eligible_programs_at_preferred_dp:
        prog_rows = [r for r in refi.rows if r.program == program]
        assert len(prog_rows) == 2
        labels = sorted(r.scenario_label for r in prog_rows)
        assert labels == ["fred_times_0_85", "minus_100bps"]

    # Target rates match the formulas (D-14-REFI-03).
    for row in refi.rows:
        current_rate = todays_rates[row.program]
        if row.scenario_label == "minus_100bps":
            assert row.target_rate == quantize_rate(current_rate - Decimal("0.01"))
        else:
            assert row.target_rate == quantize_rate(current_rate * Decimal("0.85"))


def test_stress_income_shock_dti_recompute() -> None:
    """An income_shock stress row has stressed_piti=None (income changes do NOT
    change PITI per RESEARCH L322); stressed_dti_back is strictly greater than
    the cell's baseline dti_back (income drops -> DTI rises)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    stress = _build_stress_block(matrix, listing, household, profile, todays_rates)

    income_rows = [r for r in stress.rows if r.stress_kind == "income_shock"]
    assert income_rows, "expected at least one income_shock row"
    for row in income_rows:
        assert row.stressed_piti is None
        # Locate the matching cell so we can compare against baseline DTI.
        cell = next(
            c
            for c in matrix.cells
            if c.program == row.program and c.down_payment_pct == Decimal("0.200000")
        )
        # -30% income reduction strictly raises DTI (PITI unchanged + denom -30%).
        assert row.stressed_dti_back > cell.dti_back


def test_stress_rate_shock_piti_rises() -> None:
    """A rate_shock stress row carries stressed_piti > baseline_piti (rate
    +200bps raises P&I → PITI rises with unchanged escrow + MI)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    stress = _build_stress_block(matrix, listing, household, profile, todays_rates)

    rate_rows = [r for r in stress.rows if r.stress_kind == "rate_shock"]
    assert rate_rows, "expected at least one rate_shock row"
    for row in rate_rows:
        assert row.stressed_piti is not None
        assert row.stressed_piti > row.baseline_piti, (
            f"{row.program} rate-shock should raise PITI "
            f"({row.baseline_piti} -> {row.stressed_piti})"
        )


def test_refi_signed_decimal_fields() -> None:
    """RefiRow.monthly_savings + .npv_60mo are signed Decimals (Pitfall 3 —
    raw Decimal, NOT Money-aliased). Construct a refi block from a synthetic
    matrix where current_rate is low enough that target rates are HIGHER, so
    monthly_savings is negative — the engine returns signed values and Phase 14
    surfaces them verbatim."""
    # When current_rate is already very low (e.g., 0.030), then:
    #   target_a = current - 0.01 = 0.020  (lower; positive savings)
    #   target_b = current * 0.85 = 0.0255 (lower; positive savings)
    # Both targets stay LOWER at any positive current_rate so monthly_savings
    # is non-negative for rate_and_term refi. The signed-Decimal field shape
    # is enforced at the model layer regardless (covered by the Wave-0 test
    # test_refi_row_accepts_signed_decimal_savings); here we verify that the
    # block builder produces a Decimal (NOT Money) and accepts negative values.

    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    refi = _build_refi_block(matrix, household, todays_rates)

    assert refi.rows
    for row in refi.rows:
        # Always raw Decimal (not Money — Money has ge=0; Decimal does not).
        assert isinstance(row.monthly_savings, Decimal)
        assert isinstance(row.npv_60mo, Decimal)

    # Independent assertion that the model accepts negative values directly
    # (covered structurally by Wave-0 but proves the type contract here too).
    negative_row = RefiRow(
        program="Conv30",
        target_rate=Decimal("0.085000"),
        scenario_label="minus_100bps",
        monthly_savings=Decimal("-100.00"),
        npv_60mo=Decimal("-3000.00"),
    )
    assert negative_row.monthly_savings < Decimal("0")
    assert negative_row.npv_60mo < Decimal("0")


def test_dti_ceiling_per_program() -> None:
    """B-5: per-program DTI ceilings differ — VA=0.41, Conv=0.50, FHA=0.57,
    Jumbo=0.43. Verify the constant exists with the correct citation values
    AND the stress block actually USES them (income_shock breach flag should
    differ across programs sharing the same shocked DTI when ceilings differ).
    """
    # First — the constant carries the correct citation values.
    assert _DTI_CEILING_BY_PROGRAM["Conv30"] == Decimal("0.50")
    assert _DTI_CEILING_BY_PROGRAM["Conv15"] == Decimal("0.50")
    assert _DTI_CEILING_BY_PROGRAM["FHA30"] == Decimal("0.57")
    assert _DTI_CEILING_BY_PROGRAM["VA30"] == Decimal("0.41")
    assert _DTI_CEILING_BY_PROGRAM["Jumbo30"] == Decimal("0.43")

    # Second — the stress block USES these per-program ceilings. Tune household
    # so that the -30% income shock pushes DTI between VA's 0.41 and FHA's 0.57.
    # At monthly_income=$10500, monthly_obligations=$500, listing=$500k, 20% DP:
    #   loan_amount ≈ $400k; conv P&I @ 6.5% over 360 = $2528.27
    #   PITI (no MI at 80% LTV) ≈ $2528 + monthly_obligations adjustment
    #   Pre-shock DTI = (PITI + $500) / $10500 ≈ 0.288
    #   Post-shock DTI = (PITI + $500) / $7350 ≈ 0.411 — sits in the band
    # We don't pin exact numerics; we assert the BREACH FLAG differs by program.
    listing = _make_clean_listing(price="500000.00")
    household = _make_clean_household(
        monthly_income=Decimal("10500.00"),
        monthly_obligations=Decimal("500.00"),
    )
    profile = _make_clean_profile(va_eligible=True)
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    stress = _build_stress_block(matrix, listing, household, profile, todays_rates)

    fha_shock = next(
        (r for r in stress.rows if r.program == "FHA30" and r.stress_kind == "income_shock"),
        None,
    )
    va_shock = next(
        (r for r in stress.rows if r.program == "VA30" and r.stress_kind == "income_shock"),
        None,
    )
    # Both programs must be eligible-at-preferred-DP for this household for the
    # test to prove the ceiling difference. If either is missing, the income
    # tuning produced an ineligible cell — fail loudly so the executor knows.
    assert fha_shock is not None, "FHA30 should be eligible at preferred DP in this fixture"
    assert va_shock is not None, "VA30 should be eligible at preferred DP in this fixture"

    # The shocked DTI for VA + FHA cells is roughly the same magnitude (the
    # cells differ only in MI treatment which slightly tilts PITI), but the
    # ceiling is different. We assert VA's stressed_dti exceeds 0.41 while
    # FHA's stressed_dti stays under 0.57 — the breach flag is the proof.
    assert va_shock.stressed_dti_back > _DTI_CEILING_BY_PROGRAM["VA30"]
    assert va_shock.breaches_dti_ceiling is True
    assert fha_shock.stressed_dti_back < _DTI_CEILING_BY_PROGRAM["FHA30"]
    assert fha_shock.breaches_dti_ceiling is False


def test_points_breakeven_per_program() -> None:
    """Points block has exactly 2 rows per eligible-at-preferred-DP program;
    rate_drop is Decimal("0.002500") for 1pt and Decimal("0.005000") for 2pt
    (Assumption A3)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    points = _build_points_block(matrix, household, todays_rates)

    eligible_programs_at_preferred_dp = {
        c.program for c in matrix.cells if c.down_payment_pct == Decimal("0.200000") and c.eligible
    }
    # Exactly 2 rows per eligible-at-preferred-DP program.
    assert len(points.rows) == 2 * len(eligible_programs_at_preferred_dp)
    for program in eligible_programs_at_preferred_dp:
        prog_rows = [r for r in points.rows if r.program == program]
        assert len(prog_rows) == 2
        purchased_levels = sorted(r.points_purchased for r in prog_rows)
        assert purchased_levels == [1, 2]
        for r in prog_rows:
            if r.points_purchased == 1:
                assert r.rate_drop == Decimal("0.002500")
            else:
                assert r.rate_drop == Decimal("0.005000")


def test_points_fha_va_warning_note() -> None:
    """FHA30 + VA30 points rows carry note='WARNING-NO-POINTS-FOR-FHA-VA' and
    None breakeven months (Open Question 1 resolution)."""
    household = _make_clean_household()
    profile = _make_clean_profile(va_eligible=True)
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    auxiliary_programs_at_preferred_dp = {
        c.program
        for c in matrix.cells
        if c.down_payment_pct == Decimal("0.200000")
        and (
            c.eligible
            or (c.program == "VA30" and c.blocker_reasons == ["VA-RESIDUAL-NOT-SUPPLIED"])
        )
    }
    assert {"FHA30", "VA30"}.issubset(auxiliary_programs_at_preferred_dp)
    points = _build_points_block(matrix, household, todays_rates)

    fha_rows = [r for r in points.rows if r.program == "FHA30"]
    va_rows = [r for r in points.rows if r.program == "VA30"]
    # The clean fixture has FHA30 eligible and VA30 available for residual-input diagnostics at 20% DP.
    assert fha_rows, "expected at least one FHA30 points row"
    assert va_rows, "expected at least one VA30 points row"
    for r in fha_rows + va_rows:
        assert r.note == "WARNING-NO-POINTS-FOR-FHA-VA"
        assert r.simple_breakeven_months is None
        assert r.npv_breakeven_months is None

    # Conv-family rows do NOT carry the warning note.
    conv_rows = [r for r in points.rows if r.program in ("Conv30", "Conv15")]
    for r in conv_rows:
        assert r.note is None


def test_tax_block_pub936() -> None:
    """IRS Pub 936: qualified_loan_limit == $750,000 for mfj/single/hoh
    filings. first_year_interest_per_program[program] is exactly the sum of
    the first 12 interest components of the program's preferred-DP cell
    schedule (exact Decimal equality, no fuzzy comparator)."""
    household = _make_clean_household()
    profile = _make_clean_profile()  # default filing_status="mfj"
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    tax = _build_tax_block(matrix, household, profile, todays_rates)

    assert tax.qualified_loan_limit == Decimal("750000.00")
    assert tax.filing_status == "mfj"

    # Exact Decimal equality: compare against a freshly-computed schedule.
    from lib.amortize import build_schedule
    from lib.models import Loan
    from lib.money import quantize_cents

    for cell in matrix.cells:
        if cell.down_payment_pct != Decimal("0.200000") or not cell.eligible:
            continue
        term_months = 180 if cell.program == "Conv15" else 360
        loan_type: Literal["fixed", "fha", "va"] = "fixed"
        if cell.program == "FHA30":
            loan_type = "fha"
        elif cell.program == "VA30":
            loan_type = "va"
        expected_loan = Loan(
            principal=cell.loan_amount,
            annual_rate=todays_rates[cell.program],
            term_months=term_months,
            loan_type=loan_type,
        )
        expected_schedule = build_schedule(expected_loan, frequency="monthly")
        expected_first_year = quantize_cents(
            sum(
                (p.interest for p in expected_schedule.payments[:12]),
                start=Decimal("0"),
            )
        )
        assert tax.first_year_interest_per_program[cell.program] == expected_first_year


def test_tax_block_mfs_filing_status_halves_cap() -> None:
    """Profile(filing_status='mfs') halves the qualified_loan_limit to $375,000
    per IRS Pub 936 (the predicate looks up the MFS-specific cap from
    data/reference/irs-pub936.yml, not divided here)."""
    household = _make_clean_household()
    profile = _make_clean_profile(filing_status="mfs")
    listing = _make_clean_listing()
    todays_rates = _make_test_rates()
    matrix, _ = _build_matrix(listing, household, profile, todays_rates)
    tax = _build_tax_block(matrix, household, profile, todays_rates)

    assert tax.qualified_loan_limit == Decimal("375000.00")
    assert tax.filing_status == "mfs"


def test_tax_block_over_cap_flag() -> None:
    """over_750k_cap_per_program[program] is True iff the cell's loan_amount
    exceeds the qualified_loan_limit. Verified by constructing a synthetic
    matrix with a single eligible Jumbo30 cell whose loan_amount clears the
    $750k cap, and a sibling matrix where every loan stays under the cap.

    Construct the DownPaymentMatrix directly (not via _build_matrix) so the
    test does not depend on the affordability engine's per-program eligibility
    decisions for a jumbo listing — those would short-circuit the
    eligible-at-preferred-DP filter and the test would not exercise the
    over_cap flag for Jumbo30. The TaxBlock builder reads cell.loan_amount
    directly; it does not re-run the matrix engine."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    todays_rates = _make_test_rates()

    # Hand-craft a single-cell matrix that exercises the True path: Jumbo30
    # at preferred DP with loan_amount > $750k.
    jumbo_cell = ProgramResult(
        program="Jumbo30",
        down_payment_pct=Decimal("0.200000"),
        loan_amount=Decimal("900000.00"),  # clearly > $750k cap
        monthly_pi=Decimal("5500.00"),
        monthly_tax=Decimal("500.00"),
        monthly_insurance=Decimal("100.00"),
        monthly_hoa=Decimal("0.00"),
        monthly_mi=Decimal("0.00"),
        piti=Decimal("6100.00"),
        cash_to_close=Decimal("260000.00"),
        dti_back=Decimal("0.350000"),
        ltv=Decimal("0.800000"),
        eligible=True,
    )
    jumbo_matrix = DownPaymentMatrix(
        cells=[jumbo_cell],
        programs_present=["Jumbo30"],
        down_payment_pcts=[Decimal("0.200000")],
    )
    tax_jumbo = _build_tax_block(jumbo_matrix, household, profile, todays_rates)
    assert tax_jumbo.qualified_loan_limit == Decimal("750000.00")
    assert tax_jumbo.over_750k_cap_per_program["Jumbo30"] is True

    # Non-jumbo conforming-limit cells (where loan_amount < $750k) should NOT
    # breach. Use the existing _build_matrix on a small listing; at $500k price
    # / 20% DP -> $400k loan; under cap for every program.
    small_listing = _make_clean_listing(price="500000.00")
    small_matrix, _ = _build_matrix(small_listing, household, profile, todays_rates)
    small_tax = _build_tax_block(small_matrix, household, profile, todays_rates)
    for program, flag in small_tax.over_750k_cap_per_program.items():
        assert flag is False, f"{program} loan should NOT exceed $750k cap"


def test_report_size_budget() -> None:
    """Pitfall 10: AnalysisReport JSON serialization stays under 100KB for the
    canonical SFH-conforming scenario. Mirrors tests/test_stress.py L528-567."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )
    serialized = report.model_dump_json(indent=2)
    size_bytes = len(serialized.encode("utf-8"))
    assert size_bytes < 100 * 1024, f"Size budget violation: {size_bytes} bytes >= 100KB"


def test_analyze_with_jumbo_listing() -> None:
    """Jumbo trigger: listing.price > King County conforming limit appends
    Jumbo30 as a 5th program row -> matrix.cells has 24 entries (4 programs x 6 DPs).

    Uses an income high enough that every cell's DTI stays under Rate's le=1 cap
    (cells may be ineligible per affordability, but PITI / income must remain
    representable as a Rate)."""
    household = _make_clean_household(
        monthly_income=Decimal("30000.00"),  # $360k/yr supports a $1.5M analysis
        monthly_obligations=Decimal("500.00"),
        liquid_reserves=Decimal("500000.00"),
    )
    profile = _make_clean_profile()
    listing = _make_jumbo_listing()  # $1.5M in King County WA
    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )
    assert "Jumbo30" in report.matrix.programs_present
    # 4 programs (Conv30, Conv15, FHA30, Jumbo30) x 6 DPs = 24 cells
    assert len(report.matrix.cells) == 24


def test_analyze_with_va_eligible_profile() -> None:
    """va_eligible=True appends VA30 -> matrix.cells has 24 entries (4 x 6)."""
    household = _make_clean_household()
    profile = _make_clean_profile(va_eligible=True)
    listing = _make_clean_listing()
    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )
    assert "VA30" in report.matrix.programs_present
    # 4 programs (Conv30, Conv15, FHA30, VA30) x 6 DPs = 24 cells
    assert len(report.matrix.cells) == 24


def test_analyze_fred_rate_overrides_bypass_cache() -> None:
    """When both fred_mortgage_30us and fred_mortgage_15us are passed
    explicitly, _todays_rate_per_program is NOT invoked (FRED cache bypassed)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    with patch("lib.property_analysis._todays_rate_per_program") as mock_rate:
        mock_rate.side_effect = AssertionError(
            "FRED cache must NOT be touched when overrides are supplied"
        )
        analyze(
            listing,
            household,
            profile,
            fred_mortgage_30us=Decimal("0.065000"),
            fred_mortgage_15us=Decimal("0.058000"),
        )
    assert not mock_rate.called


def test_analyze_household_snapshot_hash_deterministic() -> None:
    """Running analyze() twice with identical inputs yields the same
    household_snapshot_hash (deterministic SHA256) but different fetched_at
    (timestamps differ by definition)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    report1 = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )
    report2 = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )
    assert report1.household_snapshot_hash == report2.household_snapshot_hash
    # fetched_at differs (two distinct datetime.now(UTC) calls). On a fast
    # machine the resolution may collide at microsecond level; assert
    # >= to capture the monotonic-or-equal property.
    assert report2.fetched_at >= report1.fetched_at


def test_analyze_warnings_dedup_pmi_estimated() -> None:
    """Multiple Conv30/Conv15 cells with LTV > 0.80 (95%, 90%, 85%) all tag
    eligible_reasons with PMI-RATE-ESTIMATED-0.0075, but the top-level
    report.warnings carries 'PMI-RATE-ESTIMATED' EXACTLY ONCE (dict.fromkeys
    dedup preserving first-occurrence order)."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )
    # Sanity: multiple cells carry the PMI tag.
    n_pmi_cells = sum(
        1 for c in report.matrix.cells if any("PMI-RATE-ESTIMATED" in r for r in c.eligible_reasons)
    )
    assert n_pmi_cells > 1, "expected multiple cells with LTV > 0.80 carrying PMI tag"
    # The top-level warning is dedup'd to a single occurrence.
    pmi_warnings = [w for w in report.warnings if w == "PMI-RATE-ESTIMATED"]
    assert len(pmi_warnings) == 1


def test_analyze_verdict_matches_synthesize() -> None:
    """report.verdict is passed through verbatim from
    lib.property_verdict.synthesize(matrix, stress, household, profile) — no
    post-processing in analyze()."""
    from lib.property_verdict import synthesize

    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal("0.065000"),
        fred_mortgage_15us=Decimal("0.058000"),
    )
    direct_verdict = synthesize(report.matrix, report.stress, household, profile)
    assert report.verdict == direct_verdict


def test_analyze_cold_fred_cache_raises_valueerror() -> None:
    """When get_cached_or_fetch raises NotImplementedError (cold cache) AND no
    fred_mortgage_* overrides are provided, analyze() raises a ValueError whose
    message points the caller at scripts/fred_cli.py for refresh guidance."""
    household = _make_clean_household()
    profile = _make_clean_profile()
    listing = _make_clean_listing()
    with patch("lib.property_analysis.with_cache_lock") as mock_lock:
        mock_lock.return_value.__enter__.return_value = {"acquired_at": 0}
        with patch("lib.property_analysis.get_cached_or_fetch") as mock_fetch:
            mock_fetch.side_effect = NotImplementedError("cold")
            with pytest.raises(ValueError, match=r"scripts/fred_cli\.py") as exc:
                analyze(listing, household, profile)
            assert "scripts/fred_cli.py" in str(exc.value)


def _assert_preferred_dp_cells_pinned(
    report: AnalysisReport,
    expected_matrix: dict[str, Any],
) -> None:
    """Shared helper: assert every expected preferred-DP cell matches the report
    by exact Decimal equality (CLAUDE.md money discipline; never pytest.approx).

    Looks up each expected cell in report.matrix.cells by (program, dp_pct),
    then pins monthly_pi / piti / dti_back / ltv / monthly_mi / monthly_tax /
    monthly_insurance / monthly_hoa / loan_amount / eligible / blocker_reasons.
    """
    assert len(report.matrix.cells) == expected_matrix["cells_count"]
    assert sorted(report.matrix.programs_present) == sorted(expected_matrix["programs_present"])
    for expected_cell in expected_matrix["preferred_dp_cells"]:
        target_dp = Decimal(expected_cell["dp_pct"])
        actual = next(
            (
                c
                for c in report.matrix.cells
                if c.program == expected_cell["program"] and c.down_payment_pct == target_dp
            ),
            None,
        )
        assert actual is not None, (
            f"Expected cell {expected_cell['program']}@{expected_cell['dp_pct']} "
            f"not found in report.matrix.cells"
        )
        program_label = f"{expected_cell['program']}@{expected_cell['dp_pct']}"
        assert actual.loan_amount == Decimal(expected_cell["loan_amount"]), (
            f"{program_label}: loan_amount mismatch (got {actual.loan_amount}, "
            f"expected {expected_cell['loan_amount']})"
        )
        assert actual.monthly_pi == Decimal(expected_cell["monthly_pi"]), (
            f"{program_label}: monthly_pi mismatch (got {actual.monthly_pi}, "
            f"expected {expected_cell['monthly_pi']})"
        )
        assert actual.monthly_tax == Decimal(expected_cell["monthly_tax"]), program_label
        assert actual.monthly_insurance == Decimal(expected_cell["monthly_insurance"]), (
            program_label
        )
        assert actual.monthly_hoa == Decimal(expected_cell["monthly_hoa"]), program_label
        assert actual.monthly_mi == Decimal(expected_cell["monthly_mi"]), (
            f"{program_label}: monthly_mi mismatch"
        )
        assert actual.piti == Decimal(expected_cell["piti"]), (
            f"{program_label}: piti mismatch (got {actual.piti}, expected {expected_cell['piti']})"
        )
        assert actual.dti_back == Decimal(expected_cell["dti_back"]), (
            f"{program_label}: dti_back mismatch"
        )
        assert actual.ltv == Decimal(expected_cell["ltv"]), f"{program_label}: ltv mismatch"
        assert actual.eligible == expected_cell["eligible"], (
            f"{program_label}: eligible flag mismatch"
        )
        assert actual.blocker_reasons == expected_cell["blocker_reasons"], (
            f"{program_label}: blocker_reasons mismatch (got {actual.blocker_reasons!r}, "
            f"expected {expected_cell['blocker_reasons']!r})"
        )
        assert actual.eligible_reasons == expected_cell["eligible_reasons"], (
            f"{program_label}: eligible_reasons mismatch"
        )


def _assert_verdict_pinned(
    report: AnalysisReport,
    expected_verdict: dict[str, Any],
) -> None:
    """Shared helper: assert verdict.level and every expected verdict reason
    match by exact code + computed_value.
    """
    assert report.verdict.level == expected_verdict["level"], (
        f"verdict.level mismatch (got {report.verdict.level!r}, "
        f"expected {expected_verdict['level']!r})"
    )
    for expected_reason in expected_verdict["reasons"]:
        match = next(
            (
                r
                for r in report.verdict.reasons
                if r.predicate_code == expected_reason["predicate_code"]
                and r.computed_value == expected_reason["computed_value"]
            ),
            None,
        )
        assert match is not None, (
            f"Expected verdict reason {expected_reason['predicate_code']}="
            f"{expected_reason['computed_value']} not in report.verdict.reasons "
            f"(got: {[(r.predicate_code, r.computed_value) for r in report.verdict.reasons]})"
        )


def test_sfh_conforming_king_county_golden(
    property_analysis_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ANLZ-01..03 + VERD-01 golden-value pin: SFH conforming King County WA.

    Fixture: tests/fixtures/property_analysis/sfh_conforming_king_county.json.
    Hand-calc anchors via lib.amortize.build_schedule (see fixture `notes`).
    Verdict=GO (cascade Level 5 GO-ALL-GREEN); 2 non-FHA programs eligible at
    preferred 20% DP."""
    fx = property_analysis_fixture("sfh_conforming_king_county")

    # PATTERNS.md L590: strict-mode Decimal fields require the JSON parse path,
    # NOT validate_python(dict). Re-encode each sub-block separately.
    listing = PropertyListing.model_validate_json(json.dumps(fx["listing"]))
    household = Household.model_validate_json(json.dumps(fx["household"]))
    profile = Profile.model_validate_json(json.dumps(fx["profile"]))

    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal(fx["fred_rates"]["MORTGAGE30US"]),
        fred_mortgage_15us=Decimal(fx["fred_rates"]["MORTGAGE15US"]),
    )

    _assert_preferred_dp_cells_pinned(report, fx["expected_response"]["matrix"])
    _assert_verdict_pinned(report, fx["expected_response"]["verdict"])

    expected_tax = fx["expected_response"]["tax"]
    assert report.tax.qualified_loan_limit == Decimal(expected_tax["qualified_loan_limit"])
    assert report.tax.filing_status == expected_tax["filing_status"]
    for prog, expected_flag in expected_tax["over_750k_cap_per_program"].items():
        assert report.tax.over_750k_cap_per_program[prog] == expected_flag, (
            f"over_750k_cap_per_program[{prog}] mismatch"
        )
    for prog, expected_int in expected_tax["first_year_interest_per_program"].items():
        assert report.tax.first_year_interest_per_program[prog] == Decimal(expected_int), (
            f"first_year_interest_per_program[{prog}] mismatch"
        )


def test_condo_with_hoa_seattle_golden(
    property_analysis_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ANLZ-01..03 + VERD-01 golden-value pin: Condo+HOA Seattle at 5% DP.

    Fixture: tests/fixtures/property_analysis/condo_with_hoa_seattle.json.
    Demonstrates HOA threading into PITI + PMI applying on Conv30 at 95% LTV
    (PMI-RATE-ESTIMATED-0.0075 soft signal). Verdict=WATCH (W-1 single literal);
    cascade Level 3 STRESS-INCOME-SHOCK on the lone eligible Conv30 cell."""
    fx = property_analysis_fixture("condo_with_hoa_seattle")

    # PATTERNS.md L590: strict-mode Decimal fields require the JSON parse path.
    listing = PropertyListing.model_validate_json(json.dumps(fx["listing"]))
    household = Household.model_validate_json(json.dumps(fx["household"]))
    profile = Profile.model_validate_json(json.dumps(fx["profile"]))

    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal(fx["fred_rates"]["MORTGAGE30US"]),
        fred_mortgage_15us=Decimal(fx["fred_rates"]["MORTGAGE15US"]),
    )

    _assert_preferred_dp_cells_pinned(report, fx["expected_response"]["matrix"])
    _assert_verdict_pinned(report, fx["expected_response"]["verdict"])

    # Soft-signal: PMI-RATE-ESTIMATED-0.0075 surfaces on the Conv30 cell.
    conv30_cell = next(
        c
        for c in report.matrix.cells
        if c.program == "Conv30"
        and c.down_payment_pct == Decimal(fx["household"]["preferred_down_payment_pct"])
    )
    assert "PMI-RATE-ESTIMATED-0.0075" in conv30_cell.eligible_reasons


def test_sfh_jumbo_bay_area_golden(
    property_analysis_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ANLZ-01..03 + VERD-01 golden-value pin: SFH jumbo Bay Area at 20% DP.

    Fixture: tests/fixtures/property_analysis/sfh_jumbo_bay_area.json.
    Demonstrates D-14-MATRIX-03 Jumbo30 5th-row materialization on price >
    conforming county limit, D-14-MATRIX-02 explicit-ineligible-rows on
    Conv/FHA cells with populated numerics + stable blocker codes, and
    cascade Level 3 STRESS-INCOME-SHOCK on the eligible Jumbo30 cell."""
    fx = property_analysis_fixture("sfh_jumbo_bay_area")

    # PATTERNS.md L590: strict-mode Decimal fields require the JSON parse path.
    listing = PropertyListing.model_validate_json(json.dumps(fx["listing"]))
    household = Household.model_validate_json(json.dumps(fx["household"]))
    profile = Profile.model_validate_json(json.dumps(fx["profile"]))

    report = analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal(fx["fred_rates"]["MORTGAGE30US"]),
        fred_mortgage_15us=Decimal(fx["fred_rates"]["MORTGAGE15US"]),
    )

    _assert_preferred_dp_cells_pinned(report, fx["expected_response"]["matrix"])
    _assert_verdict_pinned(report, fx["expected_response"]["verdict"])

    # Jumbo30 row materialized at the 5th-program slot (D-14-MATRIX-03).
    assert "Jumbo30" in report.matrix.programs_present
    # B-5 follow-on: with the corrected Jumbo DTI ceiling 0.43, Jumbo30 is no
    # longer eligible at preferred 20% DP in this fixture (dti_back=0.442426 >
    # 0.43). The tax block only materializes rows for eligible-at-preferred-DP
    # cells, so over_750k_cap_per_program is empty here. Eligibility at higher
    # DPs (the 25% slot keeps Jumbo30 under the ceiling) prevents the cascade
    # from reaching Level 1.
    assert "Jumbo30" not in report.tax.over_750k_cap_per_program
    jumbo_25 = next(
        c
        for c in report.matrix.cells
        if c.program == "Jumbo30" and c.down_payment_pct == Decimal("0.250000")
    )
    assert jumbo_25.eligible is True, (
        "Jumbo30 should remain eligible at 25% DP — keeps verdict cascade at "
        "Level 2 instead of dropping to Level 1 (all-DPs-ineligible)"
    )
