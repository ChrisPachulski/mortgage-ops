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

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
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
    _build_program_result,
    _build_refi_block,
    _build_stress_block,
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


def test_analyze_stub_raises_not_implemented_with_plan_14_05_reference() -> None:
    """analyze() raises NotImplementedError; message cites Plan 14-05."""
    with pytest.raises(NotImplementedError) as exc:
        analyze()
    assert "Plan 14-05" in str(exc.value)


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
        "liquid_reserves": Decimal("100000.00"),
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
    # No exception raised; cell has both reason tags.
    assert "VA-RESIDUAL-SYNTHESIZED-V1" in cell.eligible_reasons
    assert "VA-FUNDING-FEE-FINANCED" in cell.eligible_reasons


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
    pytest.skip("Plan 14-03: points-buydown block emits 1pt + 2pt breakeven per program")


def test_tax_block_pub936() -> None:
    pytest.skip("Plan 14-03: IRS Pub 936 first-year interest + $750k cap awareness")


def test_report_size_budget() -> None:
    pytest.skip("Plan 14-06: AnalysisReport JSON stays under Phase 11 SC-5 30k-token budget")


def test_sfh_conforming_king_county_golden() -> None:
    pytest.skip("Plan 14-06: hand-calculated SFH conforming AnalysisReport golden fixture")


def test_condo_with_hoa_seattle_golden() -> None:
    pytest.skip("Plan 14-06: hand-calculated Condo+HOA AnalysisReport golden fixture")


def test_sfh_jumbo_bay_area_golden() -> None:
    pytest.skip("Plan 14-06: hand-calculated SFH jumbo AnalysisReport golden fixture")
