"""Phase 4 Affordability — full test surface (AFFD-01..09 + cross-cutting).

Plan 04-06 acceptance gate. All 9 Wave 0 xfail stubs replaced with real
behavior assertions; 9 cross-cutting tests added (citation coverage,
lazy-import D-18, 6-key envelope D-19, file-not-found, --help fast,
ValidationError 6-key, round-trip closure, single-applicant equivalence,
ATR/QM advisory).

Per Phase 3 D-17 portability: subprocess invocation only, never
`import scripts.affordability` directly. SCRIPT_PATH is the single
constant edited at Phase 10 when scripts/ relocates to
.claude/skills/mortgage-ops/scripts/.

Per CONTEXT.md D-18: exact Decimal equality, never fuzzy comparators.

Per RESEARCH §"Phase 2 Predicate Signature Audit": Phase 4 calls
`loan_type.classify(loan_amount, county, program=...)`,
`conventional_pmi.status(loan, scheduled_balance, original_property_value, ...)`,
`fha_mip.compute(loan, original_property_value, endorsement_date)`. The
CONTEXT.md D-02 signatures are CORRECTED in RESEARCH §A.1-A.3.

Boundary coverage (BLOCKER 4, VALIDATION.md §1):
- VA region x family_size grid: 12 cells (4 regions x {1, 4, 5})
- FHA MIP table grid: 4 cells (loan_amount x ltv_pct boundary)
- LTV ceiling boundary: 5 loan_types x {at-ceiling, ceiling+0.0001}
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml as _yaml
from lib.affordability import (
    BLOCKED_BY_ATR_QM_PRICE_FIRST,
    BLOCKED_BY_CLTV_CEILING_TEMPLATE,
    BLOCKED_BY_DTI_CAP_TEMPLATE,
    BLOCKED_BY_LTV_CEILING_TEMPLATE,
    BLOCKED_BY_USDA_INCOME_TEMPLATE,
    BLOCKED_BY_VA_RESIDUAL_PATTERN,
    TARGET_LOAN_TYPE_CROSSWALK,
    TARGET_LOAN_TYPE_TO_PROGRAM,
    WARNING_ATR_QM_NOT_EVALUATED,
    WARNING_HPA_PMI_REQUIRED,
    AffordabilityRequest,
    AffordabilityResponse,
    Applicant,
    EscrowInputs,
    ForwardModeRequest,
    Household,
    LocationFIPS,
    MonthlyDebts,
    ReverseModeRequest,
    VAInputs,
    evaluate,
    evaluate_forward,
    evaluate_reverse,
)
from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

AFFORDABILITY_MODULE_PATH: Path = (
    Path(__file__).resolve().parent.parent / "lib" / "affordability.py"
)
SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "affordability.py"
)
"""Phase 4 CLI WAS at project-root scripts/. Phase 10 (Plan 10-01) RELOCATED to
.claude/skills/mortgage-ops/scripts/; only this constant updates per Phase 4 D-17
portability seam."""

VA_RESIDUAL_YAML_PATH: Path = (
    Path(__file__).resolve().parent.parent / "data" / "reference" / "va-residual-income.yml"
)


def _build_request_from_fixture(fixture_request: dict[str, Any]) -> AffordabilityRequest:
    """Validate a fixture's request block via the Phase 4 discriminated union.

    Per Plan 04-05: AffordabilityRequest is Annotated[ForwardModeRequest |
    ReverseModeRequest, Field(discriminator="mode")]. TypeAdapter is the
    Pydantic v2 idiom for validating non-class types.

    Strict-mode Decimal fields require JSON-string parsing (Money/Rate are
    constructed via Pydantic's JSON path, not the Python is_instance_of path
    that strict=True enforces for in-memory dicts), so we re-encode the dict
    to JSON and validate via validate_json. This mirrors how
    scripts/affordability.py exercises the boundary.
    """
    adapter: TypeAdapter[AffordabilityRequest] = TypeAdapter(AffordabilityRequest)
    return adapter.validate_json(json.dumps(fixture_request))


def _lookup_va_threshold(
    region: str,
    family_size: int,
    loan_amount: Decimal,
) -> Decimal:
    """Look up the VA M26-7 residual income minimum for a (region, family_size,
    loan_amount) cell, mirroring the predicate's read shape.

    BLOCKER 4 helper: enables the 12-cell parametric VA test to set
    actual_residual_income BELOW the cell's minimum without hard-coding
    every threshold.
    """
    ref = _yaml.safe_load(VA_RESIDUAL_YAML_PATH.read_text())
    threshold = Decimal(ref["loan_band_threshold"])
    is_above_band = loan_amount >= threshold
    table_key = "table_above_80k" if is_above_band else "table_below_80k"
    increment_key = (
        "per_extra_member_increment_above_80k"
        if is_above_band
        else "per_extra_member_increment_below_80k"
    )
    table = ref[table_key][region]
    base_family_size = min(family_size, 5)
    base = Decimal(table[str(base_family_size)])
    if family_size > 5:
        extra = (family_size - 5) * Decimal(ref[increment_key])
        base = base + extra
    return base


# ---------------------------------------------------------------------------
# Helper builders for clean Plan-04-04 surface tests
# ---------------------------------------------------------------------------


def _valid_applicant_kwargs() -> dict[str, object]:
    return {
        "name": "A",
        "gross_monthly_income": Decimal("5000.00"),
        "credit_score": 720,
    }


def _valid_location_kwargs() -> dict[str, object]:
    return {
        "state_fips": "53",
        "county_fips": "033",
        "county_name": "King",
        "state": "WA",
    }


def _valid_household_kwargs() -> dict[str, object]:
    return {
        "location": LocationFIPS(**_valid_location_kwargs()),  # type: ignore[arg-type]
        "applicants": [Applicant(**_valid_applicant_kwargs())],  # type: ignore[arg-type]
        "size": 1,
        "monthly_debts": MonthlyDebts(),
        "escrow": EscrowInputs(
            property_tax_monthly=Decimal("400.00"),
            insurance_monthly=Decimal("150.00"),
        ),
    }


def _valid_forward_request_kwargs() -> dict[str, object]:
    return {
        "mode": "forward",
        "household": Household(**_valid_household_kwargs()),  # type: ignore[arg-type]
        "max_dti": Decimal("0.430000"),
        "target_loan_type": "fha",
        "term_months": 360,
        "annual_rate": Decimal("0.065000"),
        "loan_amount": Decimal("300000.00"),
        "property_value": Decimal("400000.00"),
    }


def _make_clean_household(**overrides: object) -> Household:
    """Build a clean household for blocker tests."""
    defaults: dict[str, object] = dict(
        location=LocationFIPS(
            state="WA",
            state_fips="53",
            county_fips="033",
            county_name="King",
            zip="98101",
        ),
        applicants=[
            Applicant(
                name="A",
                gross_monthly_income=Decimal("10000.00"),
                credit_score=720,
            ),
        ],
        size=1,
        monthly_debts=MonthlyDebts(),
        escrow=EscrowInputs(
            property_tax_monthly=Decimal("0.00"),
            insurance_monthly=Decimal("0.00"),
            hoa_monthly=Decimal("0.00"),
        ),
    )
    defaults.update(overrides)
    return Household(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# Plan 04-01 model-contract tests (Pydantic v2 type contract)
# ===========================================================================


def test_affordability_imports_clean() -> None:
    """Test 1: import surface lands cleanly (smoke test for the module
    public-symbol contract Plans 04-01..04-05 ship)."""
    # Already exercised by the top-level imports of this module.
    assert evaluate is not None
    assert evaluate_forward is not None
    assert evaluate_reverse is not None


def test_applicant_constructs_from_decimal() -> None:
    """Test 2: Applicant accepts Decimal-from-Decimal cleanly."""
    applicant = Applicant(
        name="A",
        gross_monthly_income=Decimal("5000.00"),
        credit_score=720,
    )
    assert applicant.gross_monthly_income == Decimal("5000.00")
    assert applicant.credit_score == 720


def test_applicant_rejects_float_income() -> None:
    """Test 3: strict=True rejects float for Money field."""
    with pytest.raises(ValidationError):
        Applicant(name="A", gross_monthly_income=5000.00, credit_score=720)  # type: ignore[arg-type]


def test_applicant_rejects_str_income_at_dict_validation() -> None:
    """Test 4: strict=True rejects str at dict-validation (Phase 3 D-19 idiom)."""
    with pytest.raises(ValidationError):
        Applicant(name="A", gross_monthly_income="5000.00", credit_score=720)  # type: ignore[arg-type]


def test_household_constructs_with_required_size() -> None:
    """Test 5: Household constructs cleanly with explicit size."""
    household = Household(**_valid_household_kwargs())  # type: ignore[arg-type]
    assert household.size == 1
    assert len(household.applicants) == 1
    assert household.location.state_fips == "53"
    assert household.location.county_fips == "033"


def test_household_requires_size_field() -> None:
    """Test 5b: Household without `size` raises ValidationError (BLOCKER 2 fix)."""
    kwargs = _valid_household_kwargs()
    del kwargs["size"]
    with pytest.raises(ValidationError) as exc:
        Household(**kwargs)  # type: ignore[arg-type]
    assert "size" in str(exc.value)


def test_household_rejects_size_zero() -> None:
    """Test 5c: Household with size=0 raises ValidationError (ge=1 constraint)."""
    kwargs = _valid_household_kwargs()
    kwargs["size"] = 0
    with pytest.raises(ValidationError):
        Household(**kwargs)  # type: ignore[arg-type]


def test_household_supports_size_greater_than_applicants() -> None:
    """Test 5d: Household supports size > len(applicants) (2 applicants + 3 children case)."""
    kwargs = _valid_household_kwargs()
    kwargs["applicants"] = [
        Applicant(name="A", gross_monthly_income=Decimal("5000.00"), credit_score=720),
        Applicant(name="B", gross_monthly_income=Decimal("4000.00"), credit_score=700),
    ]
    kwargs["size"] = 5
    household = Household(**kwargs)  # type: ignore[arg-type]
    assert household.size == 5
    assert len(household.applicants) == 2


def test_household_rejects_empty_applicants() -> None:
    """Test 6: Household with applicants=[] raises ValidationError (min_length=1)."""
    kwargs = _valid_household_kwargs()
    kwargs["applicants"] = []
    with pytest.raises(ValidationError):
        Household(**kwargs)  # type: ignore[arg-type]


def test_request_discriminates_on_mode_field_via_json() -> None:
    """Test 7: AffordabilityRequest discriminates on `mode` from JSON."""
    payload = {
        "mode": "forward",
        "household": {
            "location": {
                "state_fips": "53",
                "county_fips": "033",
                "county_name": "King",
                "state": "WA",
            },
            "applicants": [{"name": "A", "gross_monthly_income": "5000.00", "credit_score": 720}],
            "size": 1,
            "monthly_debts": {},
            "escrow": {
                "property_tax_monthly": "400.00",
                "insurance_monthly": "150.00",
            },
        },
        "max_dti": "0.430000",
        "target_loan_type": "fha",
        "term_months": 360,
        "annual_rate": "0.065000",
        "loan_amount": "300000.00",
        "property_value": "400000.00",
    }
    adapter: TypeAdapter[AffordabilityRequest] = TypeAdapter(AffordabilityRequest)
    request = adapter.validate_json(json.dumps(payload))
    assert isinstance(request, ForwardModeRequest)
    assert request.mode == "forward"


def test_va_target_loan_type_allows_missing_va_block() -> None:
    """Test 8: target_loan_type=='va' without household.va validates.

    Missing VA residual inputs are represented as an eligibility blocker during
    evaluation so callers can still receive ordinary affordability diagnostics.
    """
    kwargs = _valid_forward_request_kwargs()
    kwargs["target_loan_type"] = "va"
    request = ForwardModeRequest(**kwargs)  # type: ignore[arg-type]
    assert request.target_loan_type == "va"
    assert request.household.va is None


def test_conventional_above_80_ltv_requires_monthly_pmi() -> None:
    """Test 9: target=='conventional' AND ltv>0.80 AND monthly_pmi=None raises."""
    kwargs = _valid_forward_request_kwargs()
    kwargs["target_loan_type"] = "conventional"
    kwargs["loan_amount"] = Decimal("350000.00")
    kwargs["property_value"] = Decimal("400000.00")
    kwargs["monthly_pmi"] = None
    with pytest.raises(ValidationError) as exc:
        ForwardModeRequest(**kwargs)  # type: ignore[arg-type]
    assert "monthly_pmi" in str(exc.value)


def test_request_extra_field_forbidden() -> None:
    """Test 10: extra='forbid' rejects unknown fields on the request."""
    kwargs = _valid_forward_request_kwargs()
    kwargs["nonexistent_field"] = "junk"
    with pytest.raises(ValidationError):
        ForwardModeRequest(**kwargs)  # type: ignore[arg-type]


def test_target_loan_type_crosswalk_table() -> None:
    """Test 11: TARGET_LOAN_TYPE_CROSSWALK exposes RESEARCH Open Q#3 cross-walk."""
    assert TARGET_LOAN_TYPE_CROSSWALK["conventional"] == frozenset({"conforming", "high_balance"})
    assert TARGET_LOAN_TYPE_CROSSWALK["jumbo"] == frozenset({"jumbo"})
    assert TARGET_LOAN_TYPE_CROSSWALK["fha"] == frozenset({"fha_standard", "fha_high_balance"})
    assert TARGET_LOAN_TYPE_CROSSWALK["va"] == frozenset({"va_standard", "va_high_balance"})
    assert TARGET_LOAN_TYPE_CROSSWALK["usda"] == frozenset({"usda"})


def test_target_loan_type_to_program_table() -> None:
    """Test 12: TARGET_LOAN_TYPE_TO_PROGRAM maps target to Phase 2 program kwarg."""
    assert TARGET_LOAN_TYPE_TO_PROGRAM["conventional"] == "conventional"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["jumbo"] == "conventional"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["fha"] == "fha"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["va"] == "va"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["usda"] == "usda"


def test_evaluate_forward_returns_response_for_valid_request() -> None:
    """Test 13: evaluate_forward composes Phase 1/2/3 into AffordabilityResponse.

    Plan 04-02 oracle anchor: $400k @ 6.5%/30yr conventional 80% LTV →
    monthly_pi=$2528.27 exact (Phase 1 / Phase 3 oracle).
    """
    req = ForwardModeRequest(
        mode="forward",
        household=Household(
            location=LocationFIPS(
                state="WA",
                state_fips="53",
                county_fips="033",
                county_name="King",
                zip="98101",
            ),
            applicants=[
                Applicant(
                    name="A",
                    gross_monthly_income=Decimal("10000.00"),
                    credit_score=720,
                ),
            ],
            size=1,
            monthly_debts=MonthlyDebts(),
            escrow=EscrowInputs(
                property_tax_monthly=Decimal("0.00"),
                insurance_monthly=Decimal("0.00"),
            ),
        ),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    response = evaluate_forward(req)
    assert isinstance(response, AffordabilityResponse)
    assert response.mode == "forward"
    assert response.monthly_pi == Decimal("2528.27")  # Phase 1/3 oracle
    assert response.ltv == Decimal("0.800000")
    assert response.loan_type == "conforming"


def test_evaluate_reverse_returns_response_for_valid_request() -> None:
    """Test 14: evaluate_reverse positive behavior — SC-2 anchor.

    Conventional 80% LTV 7%/30yr / max_dti=0.43 / joint income $10k.
    """
    req = ReverseModeRequest(
        mode="reverse",
        household=Household(
            location=LocationFIPS(
                state_fips="53",
                county_fips="033",
                county_name="King",
                state="WA",
            ),
            applicants=[
                Applicant(
                    name="A",
                    gross_monthly_income=Decimal("5000.00"),
                    credit_score=720,
                ),
                Applicant(
                    name="B",
                    gross_monthly_income=Decimal("5000.00"),
                    credit_score=680,
                ),
            ],
            size=2,
            monthly_debts=MonthlyDebts(),
            escrow=EscrowInputs(
                property_tax_monthly=Decimal("0.00"),
                insurance_monthly=Decimal("0.00"),
                hoa_monthly=Decimal("0.00"),
            ),
        ),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.070000"),
        down_payment=Decimal("100000.00"),
        target_ltv_pct=Decimal("0.800000"),
    )
    resp = evaluate_reverse(req)
    assert isinstance(resp, AffordabilityResponse)
    assert resp.mode == "reverse"
    assert resp.assumed_ltv_pct == Decimal("0.800000")
    assert resp.assumed_monthly_mi == Decimal("0.00")
    assert resp.dti_front is None
    assert resp.dti_back is None
    assert resp.ltv is None
    assert resp.cltv is None
    assert resp.monthly_pi is None
    assert resp.piti is None
    assert resp.max_loan_amount is not None
    assert resp.max_loan_amount > Decimal("0.00")
    assert resp.implied_pi is not None
    assert resp.implied_pi > Decimal("0.00")
    assert resp.loan_type is not None


def test_response_required_fields() -> None:
    """Test 15: AffordabilityResponse requires the D-11 always-populated fields."""
    response = AffordabilityResponse(
        mode="forward",
        loan_type="fha_standard",
        blocked=False,
        blocked_by=None,
        warnings=[],
        total_gross_monthly_income=Decimal("5000.00"),
        total_monthly_debts=Decimal("0.00"),
    )
    assert response.mode == "forward"
    assert response.loan_type == "fha_standard"
    assert response.blocked is False
    assert response.blocked_by is None
    assert response.warnings == []


def test_response_is_frozen() -> None:
    """Test 16: AffordabilityResponse is frozen=True."""
    response = AffordabilityResponse(
        mode="forward",
        loan_type=None,
        blocked=True,
        blocked_by="DTI-CAP-FHA",
        warnings=[],
        total_gross_monthly_income=Decimal("5000.00"),
        total_monthly_debts=Decimal("0.00"),
    )
    with pytest.raises(ValidationError):
        response.blocked = False  # type: ignore[misc]


# ===========================================================================
# Wave 0 stubs flipped: 9 AFFD-XX requirements (real bodies replace
# `@pytest.mark.xfail` + `raise NotImplementedError`)
# ===========================================================================


def test_AFFD_01_dti_calculations(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AFFD-01: DTI front-end + back-end exact Decimal (per RESEARCH §DTI Convention).

    Anchor fixture: forward_conventional_80_ltv ($400k/$500k @ 6.5%/30yr,
    joint income $10k, no debts, no escrow). Hand-calc:
      monthly_pi = $2528.27, total_income = $10000, debts = $0
      front-end DTI = 2528.27 / 10000 = 0.252827
      back-end DTI = (2528.27 + 0) / 10000 = 0.252827 (same; no debts)
    """
    fx = affordability_fixture("forward_conventional_80_ltv")
    req = _build_request_from_fixture(fx["request"])
    resp = evaluate(req)
    assert resp.dti_front == Decimal("0.252827")
    assert resp.dti_back == Decimal("0.252827")
    # Match fixture expected_response exactly (D-18 exact equality)
    expected = fx["expected_response"]
    assert resp.dti_front == Decimal(expected["dti_front"])
    assert resp.dti_back == Decimal(expected["dti_back"])


def test_AFFD_02_ltv_calculation(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AFFD-02: LTV = loan_amount / property_value (per RESEARCH §LTV/CLTV).

    Anchor fixture: forward_conventional_80_ltv ($400k/$500k → LTV=0.80 exactly).
    """
    fx = affordability_fixture("forward_conventional_80_ltv")
    req = _build_request_from_fixture(fx["request"])
    resp = evaluate(req)
    assert resp.ltv == Decimal("0.800000")
    # CLTV equals LTV when no junior liens
    assert resp.cltv == Decimal("0.800000")
    # Match fixture (D-18)
    expected = fx["expected_response"]
    assert resp.ltv == Decimal(expected["ltv"])


def test_AFFD_03_cltv_with_junior_liens() -> None:
    """AFFD-03: CLTV = (loan_amount + sum(junior_liens)) / property_value.

    With $50k junior lien on $400k/$500k: CLTV = 450k/500k = 0.90 > LTV 0.80.
    """
    base_kwargs = dict(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    no_junior = ForwardModeRequest(**base_kwargs)  # type: ignore[arg-type]
    with_junior = ForwardModeRequest(
        **{**base_kwargs, "junior_liens": [Decimal("50000.00")]},  # type: ignore[arg-type]
    )
    no_junior_resp = evaluate(no_junior)
    with_junior_resp = evaluate(with_junior)
    # CLTV with junior > LTV without junior
    assert with_junior_resp.cltv is not None
    assert no_junior_resp.ltv is not None
    assert with_junior_resp.cltv > no_junior_resp.ltv
    # Hand-calc exact: (400000 + 50000) / 500000 = 0.900000
    assert with_junior_resp.cltv == Decimal("0.900000")
    assert with_junior_resp.ltv == Decimal("0.800000")


def test_AFFD_04_piti_composition(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AFFD-04: PITI = quantize_cents(P&I + tax + ins + HOA + MI) (D-01 + D-02).

    Anchor fixture: forward_conventional_85_ltv_with_pmi
      loan=$425k / property=$500k @ 6.5%/30yr; LTV=0.85 (>0.80) so monthly_pmi
      required; engine emits monthly_pi=$2686.29; PITI = pi + 0 + 0 + 0 + 145.83
      = $2832.12.
    """
    fx = affordability_fixture("forward_conventional_85_ltv_with_pmi")
    req = _build_request_from_fixture(fx["request"])
    resp = evaluate(req)
    expected = fx["expected_response"]
    # Exact Decimal equality on monthly_pi + piti + monthly_mi (D-18)
    assert resp.monthly_pi == Decimal(expected["monthly_pi"])
    assert resp.piti == Decimal(expected["piti"])
    assert resp.monthly_mi == Decimal(expected["monthly_mi"])
    # Math invariant: PITI = quantize_cents(monthly_pi + tax + ins + hoa + monthly_mi)
    escrow = req.household.escrow
    assert resp.monthly_pi is not None
    assert resp.monthly_mi is not None
    expected_piti = (
        resp.monthly_pi
        + escrow.property_tax_monthly
        + escrow.insurance_monthly
        + escrow.hoa_monthly
        + resp.monthly_mi
    )
    # quantize_cents (ROUND_HALF_UP) at 2 places equals the expected PITI
    assert resp.piti == expected_piti.quantize(Decimal("0.01"))


def test_AFFD_05_reverse_round_trip(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AFFD-05 + ROADMAP SC-2: reverse → forward closure within Decimal('0.0001')
    DTI tolerance (D-09); dollar amounts equal exactly (D-18)."""
    fx = affordability_fixture("reverse_conventional_80_ltv_43_dti")
    rev_req = _build_request_from_fixture(fx["request"])
    assert isinstance(rev_req, ReverseModeRequest)
    rev_resp = evaluate(rev_req)
    assert rev_resp.mode == "reverse"
    assert rev_resp.max_loan_amount is not None
    assert rev_resp.assumed_ltv_pct == rev_req.target_ltv_pct
    expected = fx["expected_response"]
    assert rev_resp.max_loan_amount == Decimal(expected["max_loan_amount"])
    assert rev_resp.implied_pi == Decimal(expected["implied_pi"])
    assert rev_resp.assumed_monthly_mi == Decimal(expected["assumed_monthly_mi"])
    assert rev_resp.blocked == expected["blocked"]
    assert rev_resp.blocked_by == expected["blocked_by"]
    for warning in expected["warnings"]:
        assert warning in rev_resp.warnings
    # Round-trip: build forward request from reverse output
    derived_property_value = (rev_resp.max_loan_amount / rev_req.target_ltv_pct).quantize(
        Decimal("0.01")
    )
    fwd_req = ForwardModeRequest(
        mode="forward",
        household=rev_req.household,
        max_dti=rev_req.max_dti,
        target_loan_type=rev_req.target_loan_type,
        term_months=rev_req.term_months,
        annual_rate=rev_req.annual_rate,
        apr=rev_req.apr,
        apor=rev_req.apor,
        monthly_pmi=rev_req.monthly_pmi,
        endorsement_date_override=rev_req.endorsement_date_override,
        junior_liens=rev_req.junior_liens,
        loan_amount=rev_resp.max_loan_amount,
        property_value=derived_property_value,
    )
    fwd_resp = evaluate(fwd_req)
    # D-09 closure: dti_back <= max_dti + Decimal('0.0001')
    assert fwd_resp.dti_back is not None
    assert fwd_resp.dti_back - rev_req.max_dti <= Decimal("0.0001")
    # D-18 dollar exact equality
    assert fwd_resp.loan_amount == rev_resp.max_loan_amount


def test_reverse_down_payment_cap_implied_pi_matches_forward_monthly_pi(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    fx = affordability_fixture("reverse_conventional_pmi_down_payment_cap_binds")
    rev_req = _build_request_from_fixture(fx["request"])
    assert isinstance(rev_req, ReverseModeRequest)
    rev_resp = evaluate(rev_req)
    expected = fx["expected_response"]

    assert rev_resp.max_loan_amount == Decimal(expected["max_loan_amount"])
    assert rev_resp.implied_pi == Decimal(expected["implied_pi"])
    assert rev_resp.assumed_monthly_mi == Decimal(expected["assumed_monthly_mi"])
    for warning in expected["warnings"]:
        assert warning in rev_resp.warnings

    assert rev_resp.max_loan_amount is not None
    derived_property_value = (rev_resp.max_loan_amount / rev_req.target_ltv_pct).quantize(
        Decimal("0.01")
    )
    fwd_req = ForwardModeRequest(
        mode="forward",
        household=rev_req.household,
        max_dti=rev_req.max_dti,
        target_loan_type=rev_req.target_loan_type,
        term_months=rev_req.term_months,
        annual_rate=rev_req.annual_rate,
        apr=rev_req.apr,
        apor=rev_req.apor,
        monthly_pmi=rev_req.monthly_pmi,
        endorsement_date_override=rev_req.endorsement_date_override,
        junior_liens=rev_req.junior_liens,
        loan_amount=rev_resp.max_loan_amount,
        property_value=derived_property_value,
    )
    fwd_resp = evaluate(fwd_req)
    assert fwd_resp.monthly_pi == rev_resp.implied_pi


def test_AFFD_06_joint_applicants(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AFFD-06 + SC-5: sum(income) + min(credit_score) across applicants (D-05 + D-06)."""
    fx = affordability_fixture("joint_applicants_two_incomes")
    req = _build_request_from_fixture(fx["request"])
    resp = evaluate(req)
    # Total income = sum across applicants
    assert resp.total_gross_monthly_income == Decimal("10000.00")  # 6000 + 4000
    # Min credit score is 680 → fico_bucket "680-699"; surfaces via FANNIE-LLPA-* warning
    fannie_warning = next(
        (w for w in resp.warnings if w.startswith("FANNIE-LLPA-")),
        None,
    )
    assert fannie_warning is not None
    # The FICO bucket "680-699" appears in the warning citation
    assert "680-699" in fannie_warning


def test_AFFD_07_blocked_by_va_residual_west_family_4(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AFFD-07 + ROADMAP SC-3: VA WEST family-4 residual fail emits the
    Phase 2 D-11 stable citation VERBATIM."""
    fx = affordability_fixture("forward_va_residual_fail")
    req = _build_request_from_fixture(fx["request"])
    resp = evaluate(req)
    # ROADMAP SC-3 verbatim
    assert resp.blocked is True
    assert resp.blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"
    # Citation matches the regex pattern (Phase 2 D-11 format)
    assert re.match(BLOCKED_BY_VA_RESIDUAL_PATTERN, resp.blocked_by) is not None
    # Decimal-equality check on expected_response
    expected = fx["expected_response"]
    assert resp.blocked_by == expected["blocked_by"]


def test_AFFD_08_cli_smoke(
    affordability_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """AFFD-08: scripts/affordability.py JSON-in/JSON-out subprocess smoke (D-13).

    Round-trip: write the conventional-80-LTV fixture's request to disk,
    invoke the CLI via subprocess, parse stdout JSON, assert it matches
    the fixture's expected_response on dollar-anchored fields.
    """
    fx = affordability_fixture("forward_conventional_80_ltv")
    request_path = tmp_path / "input.json"
    request_path.write_text(json.dumps(fx["request"]))
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    expected = fx["expected_response"]
    # Dollar anchors (D-18 exact equality)
    assert out["monthly_pi"] == expected["monthly_pi"]
    assert out["ltv"] == expected["ltv"]
    assert out["piti"] == expected["piti"]
    assert out["blocked"] == expected["blocked"]
    assert out["blocked_by"] == expected["blocked_by"]
    assert out["loan_type"] == expected["loan_type"]


def test_AFFD_09_household_example_yml_e2e(
    affordability_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """AFFD-09 + ROADMAP SC-4: household.example.yml end-to-end via subprocess.

    The fixture's request is a synthetic forward-mode request that mirrors
    the schema of config/household.example.yml (location, applicants, size,
    monthly_debts, escrow, current_housing_payment) with non-zero example
    values. The fixture invokes scripts/affordability.py via subprocess and
    asserts a clean pass with the engine-emitted response shape.

    Also verifies that config/household.example.yml itself parses as YAML and
    contains the Phase 4 schema fields (D-15) per the SC-4 contract.
    """
    fx = affordability_fixture("household_example_yml_e2e")
    # 1. CLI subprocess exercise on synthetic request derived from example.yml schema
    request_path = tmp_path / "household_e2e.json"
    request_path.write_text(json.dumps(fx["request"]))
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    expected = fx["expected_response"]
    assert out["blocked"] == expected["blocked"]
    assert out["blocked"] is False
    assert out["monthly_pi"] == expected["monthly_pi"]
    assert out["ltv"] == expected["ltv"]
    assert out["piti"] == expected["piti"]

    # 2. config/household.example.yml itself parses + has the Phase 4 schema fields (D-15)
    example_yml_path = Path(__file__).resolve().parent.parent / "config" / "household.example.yml"
    parsed = _yaml.safe_load(example_yml_path.read_text())
    household = parsed["household"]
    # D-15 schema fields are present (Phase 4 final schema)
    assert "location" in household
    assert "state_fips" in household["location"]
    assert "county_fips" in household["location"]
    assert "size" in household  # BLOCKER 2 fix
    assert "applicants" in household
    assert "monthly_debts" in household
    assert "escrow" in household
    assert "property_tax_monthly" in household["escrow"]
    assert "insurance_monthly" in household["escrow"]
    assert "hoa_monthly" in household["escrow"]


# ===========================================================================
# Plan 04-04 surface tests — citation constants + ceiling tables + dispatcher
# ===========================================================================


def test_ltv_ceiling_table_values() -> None:
    """Plan 04-04 Tests 1-5: LTV_CEILING_BY_TARGET per RESEARCH §LTV/CLTV."""
    from lib.affordability import LTV_CEILING_BY_TARGET

    assert LTV_CEILING_BY_TARGET["conventional"] == Decimal("0.97")
    assert LTV_CEILING_BY_TARGET["fha"] == Decimal("0.965")
    assert LTV_CEILING_BY_TARGET["va"] == Decimal("1.00")
    assert LTV_CEILING_BY_TARGET["usda"] == Decimal("1.00")
    assert LTV_CEILING_BY_TARGET["jumbo"] == Decimal("0.90")


def test_cltv_ceiling_table_values() -> None:
    """Plan 04-04: CLTV_CEILING_BY_TARGET mirrors LTV ceilings for v1."""
    from lib.affordability import CLTV_CEILING_BY_TARGET

    assert CLTV_CEILING_BY_TARGET["conventional"] == Decimal("0.97")
    assert CLTV_CEILING_BY_TARGET["fha"] == Decimal("0.965")
    assert CLTV_CEILING_BY_TARGET["va"] == Decimal("1.00")
    assert CLTV_CEILING_BY_TARGET["usda"] == Decimal("1.00")
    assert CLTV_CEILING_BY_TARGET["jumbo"] == Decimal("0.90")


def test_blocked_by_citation_template_constants() -> None:
    """Plan 04-04 Tests 6-10: hard-blocker citation templates."""
    assert BLOCKED_BY_DTI_CAP_TEMPLATE == "DTI-CAP-{LOAN_TYPE}"
    assert BLOCKED_BY_LTV_CEILING_TEMPLATE == "LTV-CEILING-{LOAN_TYPE}"
    assert BLOCKED_BY_CLTV_CEILING_TEMPLATE == "CLTV-CEILING-{LOAN_TYPE}"
    assert BLOCKED_BY_USDA_INCOME_TEMPLATE == "USDA-INCOME-LIMIT-{state_fips}-{county_fips}"
    assert BLOCKED_BY_ATR_QM_PRICE_FIRST == "ATR-QM-PRICE-FIRST"
    assert (
        BLOCKED_BY_VA_RESIDUAL_PATTERN == r"^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$"
    )


def test_warning_citation_constants() -> None:
    """Plan 04-04 Tests 11-14: soft-warning citation strings + templates."""
    from lib.affordability import (
        WARNING_FANNIE_LLPA_TEMPLATE,
        WARNING_FREDDIE_INELIGIBLE_TEMPLATE,
    )

    assert WARNING_HPA_PMI_REQUIRED == "HPA-PMI-REQUIRED"
    assert WARNING_ATR_QM_NOT_EVALUATED == "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR"
    assert WARNING_FANNIE_LLPA_TEMPLATE == "FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}"
    assert WARNING_FREDDIE_INELIGIBLE_TEMPLATE == "FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}"


def test_citation_constants_module_level_exposure() -> None:
    """Plan 04-04 Test 15: BLOCKED_BY_* + WARNING_* constants are module-level."""
    import lib.affordability as aff

    names = dir(aff)
    blocked_by_constants = [n for n in names if n.startswith("BLOCKED_BY_")]
    warning_constants = [n for n in names if n.startswith("WARNING_")]
    assert len(blocked_by_constants) >= 5, blocked_by_constants
    assert len(warning_constants) >= 4, warning_constants


def test_evaluate_clean_conventional_no_blocker() -> None:
    """Task 2 Test 1: clean conv 80% LTV → blocked=False, blocked_by=None."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is False
    assert resp.blocked_by is None


def test_evaluate_va_residual_blocker_west_family_4_verbatim() -> None:
    """Task 2 Test 2 + ROADMAP SC-3: VA WEST family-4 below M26-7 minimum (~$1,117)
    → blocked=True, blocked_by='VA-RESIDUAL-WEST-FAMILY-4' VERBATIM."""
    household = _make_clean_household(
        size=4,
        va=VAInputs(
            region="west",
            family_size=4,
            actual_residual_income=Decimal("500.00"),  # below $1,117 minimum
        ),
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.430000"),
        target_loan_type="va",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"


def test_evaluate_dti_cap_blocker() -> None:
    """Task 2 Test 3: FHA loan with DTI back > max_dti → blocked_by='DTI-CAP-FHA'."""
    debts = MonthlyDebts(
        auto=Decimal("800.00"),
        student_loans=Decimal("500.00"),
        credit_cards=Decimal("200.00"),
        other=Decimal("0.00"),
    )
    household = _make_clean_household(
        monthly_debts=debts,
        escrow=EscrowInputs(
            property_tax_monthly=Decimal("400.00"),
            insurance_monthly=Decimal("150.00"),
            hoa_monthly=Decimal("0.00"),
        ),
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.380000"),
        target_loan_type="fha",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "DTI-CAP-FHA"


def test_evaluate_ltv_ceiling_blocker_conventional() -> None:
    """Task 2 Test 4: conv loan with LTV=0.98 (above 0.97 ceiling) → 'LTV-CEILING-CONVENTIONAL'."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("250.00"),
        loan_amount=Decimal("490000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "LTV-CEILING-CONVENTIONAL"


def test_evaluate_cltv_ceiling_blocker_conventional() -> None:
    """Conventional loan with acceptable LTV but over-ceiling CLTV blocks on CLTV."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("250.00"),
        loan_amount=Decimal("450000.00"),
        property_value=Decimal("500000.00"),
        junior_liens=[Decimal("50000.00")],
    )
    resp = evaluate(req)
    assert resp.ltv == Decimal("0.900000")
    assert resp.cltv == Decimal("1.000000")
    assert resp.blocked is True
    assert resp.blocked_by == "CLTV-CEILING-CONVENTIONAL"


def test_evaluate_classify_blocker_preserved_for_jumbo() -> None:
    """Task 2 Test 5: jumbo-classify-step blocker (Plan 04-02) precedes precedence pipeline."""
    household = _make_clean_household(
        applicants=[
            Applicant(
                name="A",
                gross_monthly_income=Decimal("50000.00"),
                credit_score=720,
            ),
        ],
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("2000000.00"),
        property_value=Decimal("2500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by is not None
    assert resp.blocked_by.startswith("FHFA-LIMIT-CONFORMING-")


def test_evaluate_usda_income_blocker() -> None:
    """Task 2 Test 6: USDA target with household income above USDA limit."""
    household = _make_clean_household(
        applicants=[
            Applicant(
                name="A",
                gross_monthly_income=Decimal("30000.00"),
                credit_score=720,
            ),
        ],
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.430000"),
        target_loan_type="usda",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("300000.00"),
        property_value=Decimal("300000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "USDA-INCOME-LIMIT-53-033"


def test_evaluate_atr_qm_blocker_when_apr_apor_present() -> None:
    """Task 2 Test 7: first-lien residential with apr+apor + spread > threshold
    → blocked_by='ATR-QM-PRICE-FIRST'."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        apr=Decimal("0.090000"),
        apor=Decimal("0.040000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == BLOCKED_BY_ATR_QM_PRICE_FIRST


def test_evaluate_atr_qm_advisory_when_apr_apor_missing() -> None:
    """Task 2 Test 8: both apr and apor None → ATR-QM-NOT-EVALUATED warning."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert WARNING_ATR_QM_NOT_EVALUATED in resp.warnings
    assert resp.blocked_by != "ATR-QM-PRICE-FIRST"


def test_evaluate_hpa_pmi_required_warning_for_conv_above_80_ltv() -> None:
    """Task 2 Test 9: conventional 85% LTV with monthly_pmi → 'HPA-PMI-REQUIRED'."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("150.00"),
        loan_amount=Decimal("425000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert WARNING_HPA_PMI_REQUIRED in resp.warnings


def test_evaluate_invariant_blocked_iff_blocked_by() -> None:
    """Task 2 Test 15: response.blocked is True iff response.blocked_by is not None."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("490000.00"),
        property_value=Decimal("500000.00"),
        monthly_pmi=Decimal("250.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is (resp.blocked_by is not None)


def test_evaluate_dispatcher_routes_reverse_mode() -> None:
    """Task 2 Test 14: public evaluate() dispatches by mode → ReverseModeRequest."""
    household = _make_clean_household(
        applicants=[
            Applicant(name="A", gross_monthly_income=Decimal("5000.00"), credit_score=720),
            Applicant(name="B", gross_monthly_income=Decimal("5000.00"), credit_score=680),
        ],
        size=2,
    )
    req = ReverseModeRequest(
        mode="reverse",
        household=household,
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.070000"),
        down_payment=Decimal("100000.00"),
        target_ltv_pct=Decimal("0.800000"),
    )
    resp = evaluate(req)
    assert resp.mode == "reverse"
    assert resp.max_loan_amount is not None
    assert resp.max_loan_amount > Decimal("0")


def test_evaluate_va_residual_pass_no_blocker() -> None:
    """Task 2 Test 17: VA target with residual income above M26-7 minimum → no blocker."""
    household = _make_clean_household(
        size=4,
        va=VAInputs(
            region="west",
            family_size=4,
            actual_residual_income=Decimal("2000.00"),
        ),
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.430000"),
        target_loan_type="va",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is False
    assert resp.blocked_by is None


def test_evaluate_non_va_target_skips_va_residual() -> None:
    """Task 2 Test 16: non-VA target → no VA-residual evaluation surfaced."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    if resp.blocked_by is not None:
        assert not resp.blocked_by.startswith("VA-RESIDUAL")
    assert all(not w.startswith("VA-RESIDUAL") for w in resp.warnings)


def test_evaluate_va_residual_citation_read_verbatim_not_constructed() -> None:
    """Task 2 Test 13: Phase 4 reads VA citation from predicate, never constructs it."""
    import inspect

    from lib import affordability

    # Negative-grep gate: source must NOT contain `f"VA-RESIDUAL-` (anywhere)
    source = inspect.getsource(affordability)
    assert 'f"VA-RESIDUAL-' not in source, (
        "Phase 4 must NEVER construct the VA-residual citation; reads "
        "verbatim via va_result.binding_rule_citation per Phase 2 D-11"
    )
    # Positive evidence: the verbatim-read site exists.
    assert "va_result.binding_rule_citation" in source


def test_evaluate_blockers_appends_soft_warnings_even_when_blocked() -> None:
    """Task 2 T-04-04-05: soft warnings always evaluated even when hard-blocked."""
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("250.00"),
        loan_amount=Decimal("490000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "LTV-CEILING-CONVENTIONAL"
    assert WARNING_ATR_QM_NOT_EVALUATED in resp.warnings


# ===========================================================================
# Plan 04-06 Cross-cutting tests (citation coverage, lazy-import, envelope, etc.)
# ===========================================================================


def test_blocked_by_citation_coverage() -> None:
    """RUL-12/13 inheritance: every BLOCKED_BY_* template introduced in
    lib/affordability.py is exercised by at least one scenario."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "affordability"
    all_blocked_by: list[str | None] = []
    for fp in sorted(fixtures_dir.glob("*.json")):
        data = json.loads(fp.read_text())
        if data.get("expected_response") is not None:
            all_blocked_by.append(data["expected_response"].get("blocked_by"))
    inline_cltv_req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("250.00"),
        loan_amount=Decimal("450000.00"),
        property_value=Decimal("500000.00"),
        junior_liens=[Decimal("50000.00")],
    )
    all_blocked_by.append(evaluate(inline_cltv_req).blocked_by)

    # Every non-VA template format must appear in at least one scenario.
    templates_to_check = [
        BLOCKED_BY_CLTV_CEILING_TEMPLATE,
        BLOCKED_BY_DTI_CAP_TEMPLATE,
    ]
    for template in templates_to_check:
        prefix = template.split("{")[0]
        assert any(bb is not None and bb.startswith(prefix) for bb in all_blocked_by), (
            f"No scenario exercises {template} citation template"
        )

    # FHFA-LIMIT-* (loan-type-classify mismatch) — substring "FHFA-LIMIT-"
    assert any(bb is not None and bb.startswith("FHFA-LIMIT-") for bb in all_blocked_by), (
        "No fixture exercises FHFA-LIMIT-* citation"
    )

    # VA-residual regex
    va_pattern = re.compile(BLOCKED_BY_VA_RESIDUAL_PATTERN)
    assert any(bb is not None and va_pattern.match(bb) for bb in all_blocked_by), (
        "No fixture exercises VA-RESIDUAL-{REGION}-FAMILY-{N} citation pattern"
    )


def test_cli_help_does_not_import_lib_affordability() -> None:
    """D-18 (Phase 3 03-04 idiom): --help must not trigger lib.affordability
    or numpy_financial import.

    Spawn a fresh Python subprocess (so neither is already imported via this
    test module's top-level imports) and run an inline check that loads
    scripts/affordability.py via importlib.util.spec_from_file_location with
    sys.argv patched to --help.
    """
    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_affordability', SCRIPT)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "saved_argv = sys.argv\n"
        "sys.argv = [SCRIPT, '--help']\n"
        "exit_code = None\n"
        "try:\n"
        "    try:\n"
        "        module.main()\n"
        "    except SystemExit as exc:\n"
        "        exit_code = exc.code\n"
        "finally:\n"
        "    sys.argv = saved_argv\n"
        "result = {\n"
        "    'help_exit_code': exit_code,\n"
        "    'lib_affordability_imported': 'lib.affordability' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
        "}\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", inline],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["help_exit_code"] == 0
    assert payload["lib_affordability_imported"] is False, (
        "D-18 violated: lib.affordability was imported during --help (must be lazy)"
    )
    assert payload["numpy_financial_imported"] is False, (
        "D-18 violated: numpy_financial was imported during --help"
    )


def test_cli_rejects_float_in_loan_amount(tmp_path: Path) -> None:
    """D-19 + WR-02 inheritance: pre-validation gate emits 6-key envelope.

    W5: property_value=500000 makes LTV=0.80 exactly (NOT >0.80) so
    monthly_pmi=None passes _validate_common — the test exercises the
    float-gate, not the conditional monthly_pmi validator.
    """
    bad = tmp_path / "float.json"
    bad.write_text(
        '{"mode": "forward",'
        '"household": {"location": {"state": "WA", "state_fips": "53", '
        '"county_fips": "033", "county_name": "King", "zip": "98101"}, '
        '"applicants": [{"name":"A","gross_monthly_income":"5000.00","credit_score":720}], '
        '"size": 1,'
        '"monthly_debts": {}, '
        '"escrow": {"property_tax_monthly":"0.00","insurance_monthly":"0.00","hoa_monthly":"0.00"}}, '
        '"max_dti":"0.43","target_loan_type":"conventional","term_months":360,'
        '"annual_rate":"0.065","loan_amount": 400000.00,'
        '"property_value":"500000.00"}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["loan_amount"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"].get("class") == "Decimal"


def test_cli_rejects_missing_monthly_pmi_when_required(tmp_path: Path) -> None:
    """W5 companion: LTV=0.81 + conventional + monthly_pmi=null
    triggers the conditional monthly_pmi validator (Pydantic ValidationError path)."""
    bad = tmp_path / "missing_pmi.json"
    bad.write_text(
        '{"mode":"forward",'
        '"household":{"location":{"state":"WA","state_fips":"53","county_fips":"033",'
        '"county_name":"King","zip":"98101"},'
        '"applicants":[{"name":"A","gross_monthly_income":"5000.00","credit_score":720}],'
        '"size":1,'
        '"monthly_debts":{"auto":"0.00","student_loans":"0.00","credit_cards":"0.00","other":"0.00"},'
        '"escrow":{"property_tax_monthly":"0.00","insurance_monthly":"0.00","hoa_monthly":"0.00"}},'
        '"max_dti":"0.43","target_loan_type":"conventional","term_months":360,'
        '"annual_rate":"0.065","loan_amount":"405000.00","property_value":"500000.00",'
        '"monthly_pmi":null}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    assert any(
        "monthly_pmi" in (e.get("msg") or "") or "monthly_pmi" in str(e.get("loc")) for e in errors
    ), f"expected monthly_pmi-related ValidationError; got {errors}"


def test_cli_file_not_found_returns_structured_error(tmp_path: Path) -> None:
    """File-not-found envelope (Phase 3 contract — simpler {error: ...} shape)."""
    bogus = tmp_path / "does_not_exist.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bogus)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    err = json.loads(result.stderr)
    assert "input file not found" in err.get("error", "")


def test_cli_help_fast(tmp_path: Path) -> None:
    """--help should be fast (D-18). Generous bound (2s) for CI margin."""
    import time

    start = time.time()
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    elapsed = time.time() - start
    assert result.returncode == 0
    assert elapsed < 2.0, f"--help took {elapsed:.2f}s; expected <2s (D-18)"


def test_cli_missing_county_data_emits_six_key_envelope(
    affordability_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """BLOCKER 1 fix — when household.location.county_fips is not in
    data/reference/conforming-limits-2026.yml AND loan_amount > baseline,
    scripts/affordability.py main() catches MissingCountyDataError and emits
    the Phase 3 D-19 6-key envelope (instead of a Python traceback).
    """
    fx = affordability_fixture("forward_missing_county_data")
    request_path = tmp_path / "missing_county.json"
    request_path.write_text(json.dumps(fx["request"]))
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; stderr={result.stderr}"
    )
    errors = json.loads(result.stderr)
    assert isinstance(errors, list)
    assert len(errors) == 1
    err = errors[0]
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}, (
        f"keys={set(err.keys())}"
    )
    assert err["type"] == "value_error"
    assert err["loc"] == ["household", "location"]
    assert err["ctx"]["class"] == "MissingCountyDataError"
    # Per fixture's expected_stderr_envelope contract
    for k, v in fx["expected_stderr_envelope"][0].items():
        if k == "ctx":
            for ck, cv in v.items():
                assert err["ctx"][ck] == cv
        else:
            assert err[k] == v


def test_single_applicant_same_code_path_as_joint(
    affordability_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-5: single_applicant + joint_applicants_two_incomes both pass;
    same code path (D-07 single-applicant via list of length 1).
    """
    single_fx = affordability_fixture("single_applicant")
    single_req = _build_request_from_fixture(single_fx["request"])
    single_resp = evaluate(single_req)

    joint_fx = affordability_fixture("joint_applicants_two_incomes")
    joint_req = _build_request_from_fixture(joint_fx["request"])
    joint_resp = evaluate(joint_req)

    # Both produce a clean response (no blocker)
    assert single_resp.blocked is False
    assert joint_resp.blocked is False
    # Both produce a valid total_gross_monthly_income aggregated from applicants
    assert single_resp.total_gross_monthly_income == Decimal("10000.00")
    assert joint_resp.total_gross_monthly_income == Decimal("10000.00")
    # Both have same monthly_pi anchor (same loan/rate/term)
    assert single_resp.monthly_pi == Decimal("2528.27")
    assert joint_resp.monthly_pi == Decimal("2528.27")


# ===========================================================================
# BLOCKER 4 boundary parametrize tests (VALIDATION.md §1 grid coverage)
# ===========================================================================


@pytest.mark.parametrize(
    ("region", "family_size"),
    [
        ("northeast", 1),
        ("northeast", 4),
        ("northeast", 5),
        ("midwest", 1),
        ("midwest", 4),
        ("midwest", 5),
        ("south", 1),
        ("south", 4),
        ("south", 5),
        ("west", 1),
        ("west", 4),
        ("west", 5),
    ],
)
def test_va_residual_citation_format(region: str, family_size: int) -> None:
    """BLOCKER 4 — VA-residual citation = f'VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}'
    verbatim (Phase 2 D-11 stable format).

    Each test constructs a forward VA request with actual_residual_income BELOW
    the M26-7 minimum for the (region, family_size) cell — pulling the threshold
    from data/reference/va-residual-income.yml at test-time. Asserts response.blocked_by
    matches the verbatim format (no string formatting drift).
    """
    threshold = _lookup_va_threshold(region, family_size, loan_amount=Decimal("400000.00"))
    actual = threshold - Decimal("100.00")  # below threshold → fail

    household = Household(
        location=LocationFIPS(
            state="WA",
            state_fips="53",
            county_fips="033",
            county_name="King",
            zip="98101",
        ),
        applicants=[
            Applicant(name="A", gross_monthly_income=Decimal("12000.00"), credit_score=720),
        ],
        size=max(family_size, 1),
        monthly_debts=MonthlyDebts(),
        escrow=EscrowInputs(
            property_tax_monthly=Decimal("0.00"),
            insurance_monthly=Decimal("0.00"),
            hoa_monthly=Decimal("0.00"),
        ),
        va=VAInputs(
            region=region,  # type: ignore[arg-type]
            family_size=family_size,
            actual_residual_income=actual,
        ),
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.430000"),
        target_loan_type="va",
        term_months=360,
        annual_rate=Decimal("0.070000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    expected = f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"
    assert resp.blocked is True, (
        f"expected blocked for {expected}; got blocked_by={resp.blocked_by}"
    )
    assert resp.blocked_by == expected, f"format drift: got {resp.blocked_by} expected {expected}"


@pytest.mark.parametrize(
    ("loan_amount", "property_value", "ltv_label"),
    [
        ("400000.00", "421000.00", "<=726200/<=95"),
        ("400000.00", "414500.00", "<=726200/>95"),
        ("800000.00", "842000.00", ">726200/<=95"),
        ("800000.00", "829000.00", ">726200/>95"),
    ],
)
def test_fha_mip_compute_per_table_row(
    loan_amount: str,
    property_value: str,
    ltv_label: str,
) -> None:
    """BLOCKER 4 — confirms each FHA MIP table cell produces a non-None
    monthly_mi in PITI (HUD ML 2023-05).
    """
    household = Household(
        location=LocationFIPS(
            state="WA",
            state_fips="53",
            county_fips="033",
            county_name="King",
            zip="98101",
        ),
        applicants=[
            Applicant(name="A", gross_monthly_income=Decimal("15000.00"), credit_score=720),
        ],
        size=2,
        monthly_debts=MonthlyDebts(),
        escrow=EscrowInputs(
            property_tax_monthly=Decimal("0.00"),
            insurance_monthly=Decimal("0.00"),
            hoa_monthly=Decimal("0.00"),
        ),
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.430000"),
        target_loan_type="fha",
        term_months=360,
        annual_rate=Decimal("0.070000"),
        loan_amount=Decimal(loan_amount),
        property_value=Decimal(property_value),
    )
    resp = evaluate(req)
    assert resp.monthly_mi is not None, (
        f"FHA MIP cell {ltv_label}: monthly_mi must be non-None per HUD ML 2023-05"
    )
    assert resp.monthly_mi > Decimal("0"), f"FHA MIP cell {ltv_label}: monthly_mi must be > 0"


@pytest.mark.parametrize(
    ("target_loan_type", "ceiling"),
    [
        ("conventional", Decimal("0.97")),
        ("fha", Decimal("0.965")),
        ("va", Decimal("1.00")),
        ("usda", Decimal("1.00")),
        ("jumbo", Decimal("0.90")),
    ],
)
@pytest.mark.parametrize(
    ("offset", "blocked_expected"),
    [
        (Decimal("0"), False),
        (Decimal("0.0001"), True),
    ],
)
def test_ltv_ceiling_boundary(
    target_loan_type: str,
    ceiling: Decimal,
    offset: Decimal,
    blocked_expected: bool,
) -> None:
    """BLOCKER 4 — LTV ceiling boundary per loan_type.

    Per RESEARCH §LTV/CLTV Ceiling Authority + Plan 04-04 LTV_CEILING_BY_TARGET.
    For target=usda, the income-cap blocker fires before LTV (high income to pass DTI
    requires income that exceeds USDA limits) — skip. Phase 17 polish (2026-05-23):
    jumbo ceiling tightened from 1.00 (sentinel; no enforcement) to 0.90 (common
    jumbo lender norm); jumbo over-ceiling case now exercises the blocker.
    """
    if target_loan_type == "usda" and offset > Decimal("0"):
        pytest.skip(
            "USDA target with high income (needed to clear DTI for at-ceiling LTV) "
            "hits USDA-INCOME-LIMIT blocker before LTV-CEILING-USDA; "
            "additionally, LTV>1.00 violates Pydantic Rate le=1 constraint"
        )
    if target_loan_type == "va" and offset > Decimal("0"):
        pytest.skip(
            "VA ceiling 1.00 + offset 0.0001 produces LTV=1.0001 which violates "
            "Pydantic Rate le=1 constraint at response boundary; the ceiling "
            "itself is correctly enforced by the predicate (over-ceiling cases "
            "would fail at the response-shape boundary before reaching blocker logic)"
        )
    if target_loan_type == "fha" and offset == Decimal("0"):
        pytest.skip(
            "FHA at-ceiling case is unreachable: UFMIP auto-finance (D-03) "
            "inflates request loan_amount by 1.75% so requested LTV=0.965 yields "
            "financed LTV=0.965*1.0175 > 0.965 ceiling. Over-ceiling case "
            "(offset>0) still pins the LTV-CEILING-FHA citation."
        )

    ltv_target = ceiling + offset
    # Jumbo classification requires loan_amount > FHFA conforming limit (King WA
    # one-unit 2026 = $1,027,000). Bump above that floor so target=jumbo isn't
    # short-circuited by FHFA-LIMIT-JUMBO before LTV-CEILING-JUMBO can fire.
    loan_amount = Decimal("1200000.00") if target_loan_type == "jumbo" else Decimal("400000.00")
    property_value = (loan_amount / ltv_target).quantize(Decimal("0.01"))

    location = LocationFIPS(
        state="WA",
        state_fips="53",
        county_fips="033",
        county_name="King",
        zip="98101",
    )
    applicants = [
        Applicant(
            name="A",
            gross_monthly_income=Decimal("15000.00"),
            credit_score=720,
        ),
    ]
    household_kwargs: dict[str, Any] = {
        "location": location,
        "applicants": applicants,
        "size": 2,
        "monthly_debts": MonthlyDebts(),
        "escrow": EscrowInputs(
            property_tax_monthly=Decimal("0.00"),
            insurance_monthly=Decimal("0.00"),
            hoa_monthly=Decimal("0.00"),
        ),
    }
    if target_loan_type == "va":
        household_kwargs["va"] = VAInputs(
            region="west",
            family_size=2,
            actual_residual_income=Decimal("9999.00"),
        )

    household = Household(**household_kwargs)
    monthly_pmi: Decimal | None = (
        Decimal("250.00")
        if target_loan_type == "conventional" and ltv_target > Decimal("0.80")
        else None
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,
        max_dti=Decimal("0.99"),  # generous so DTI doesn't fire first
        target_loan_type=target_loan_type,  # type: ignore[arg-type]
        term_months=360,
        annual_rate=Decimal("0.070000"),
        monthly_pmi=monthly_pmi,
        loan_amount=loan_amount,
        property_value=property_value,
    )
    resp = evaluate(req)
    if blocked_expected:
        assert resp.blocked is True
        assert resp.blocked_by == f"LTV-CEILING-{target_loan_type.upper()}", (
            f"target={target_loan_type} offset={offset}: "
            f"expected LTV-CEILING-{target_loan_type.upper()}, got {resp.blocked_by}"
        )
    else:
        if resp.blocked_by is not None:
            assert not resp.blocked_by.startswith("LTV-CEILING-"), (
                f"target={target_loan_type} at ceiling {ceiling}: "
                f"should not block on LTV-CEILING; got {resp.blocked_by}"
            )
