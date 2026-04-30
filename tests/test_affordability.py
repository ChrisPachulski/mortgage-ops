"""Phase 4 Affordability — test surface (AFFD-01..09 + Plan 04-01 model contract).

Wave 0 stubs: every AFFD-XX behavioral requirement has a stub function that pytest
collects. Stubs are marked `pytest.mark.xfail(strict=False, reason="Wave N
implementation pending")` so the suite stays green during Wave 1-3
implementation. Each Wave 1+ task replaces its stub body with the real
test (RED->GREEN flip).

Plan 04-01 model-contract tests: 16 model-shape assertions exercising the
Pydantic v2 contract shipped by lib/affordability.py — Applicant, Household,
EscrowInputs, VAInputs, LocationFIPS, MonthlyDebts, ForwardModeRequest,
ReverseModeRequest, AffordabilityRequest discriminated union, AffordabilityResponse,
TARGET_LOAN_TYPE_CROSSWALK + TARGET_LOAN_TYPE_TO_PROGRAM cross-walk constants,
and evaluate_forward / evaluate_reverse cross-plan stubs.

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
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

AFFORDABILITY_MODULE_PATH: Path = (
    Path(__file__).resolve().parent.parent / "lib" / "affordability.py"
)
SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "affordability.py"
"""Phase 4 CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""


# ---------------------------------------------------------------------------
# Plan 04-01 model-contract tests (16 behaviors per PLAN.md <behavior> block)
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
    from lib.affordability import Applicant, EscrowInputs, LocationFIPS, MonthlyDebts

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
    from lib.affordability import Household

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


def test_affordability_imports_clean() -> None:
    """Test 1: import surface for Plan 04-01 lands cleanly."""
    from lib.affordability import (  # noqa: F401
        TARGET_LOAN_TYPE_CROSSWALK,
        TARGET_LOAN_TYPE_TO_PROGRAM,
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
        evaluate_forward,
        evaluate_reverse,
    )


def test_applicant_constructs_from_decimal() -> None:
    """Test 2: Applicant accepts Decimal-from-Decimal cleanly."""
    from lib.affordability import Applicant

    applicant = Applicant(
        name="A",
        gross_monthly_income=Decimal("5000.00"),
        credit_score=720,
    )
    assert applicant.gross_monthly_income == Decimal("5000.00")
    assert applicant.credit_score == 720


def test_applicant_rejects_float_income() -> None:
    """Test 3: strict=True rejects float for Money field."""
    from lib.affordability import Applicant

    with pytest.raises(ValidationError):
        Applicant(name="A", gross_monthly_income=5000.00, credit_score=720)  # type: ignore[arg-type]


def test_applicant_rejects_str_income_at_dict_validation() -> None:
    """Test 4: strict=True rejects str at dict-validation (Phase 3 D-19 idiom)."""
    from lib.affordability import Applicant

    with pytest.raises(ValidationError):
        Applicant(name="A", gross_monthly_income="5000.00", credit_score=720)  # type: ignore[arg-type]


def test_household_constructs_with_required_size() -> None:
    """Test 5: Household constructs cleanly with explicit size."""
    from lib.affordability import Household

    household = Household(**_valid_household_kwargs())  # type: ignore[arg-type]
    assert household.size == 1
    assert len(household.applicants) == 1
    assert household.location.state_fips == "53"
    assert household.location.county_fips == "033"


def test_household_requires_size_field() -> None:
    """Test 5b: Household without `size` raises ValidationError (BLOCKER 2 fix)."""
    from lib.affordability import Household

    kwargs = _valid_household_kwargs()
    del kwargs["size"]
    with pytest.raises(ValidationError) as exc:
        Household(**kwargs)  # type: ignore[arg-type]
    assert "size" in str(exc.value)


def test_household_rejects_size_zero() -> None:
    """Test 5c: Household with size=0 raises ValidationError (ge=1 constraint)."""
    from lib.affordability import Household

    kwargs = _valid_household_kwargs()
    kwargs["size"] = 0
    with pytest.raises(ValidationError):
        Household(**kwargs)  # type: ignore[arg-type]


def test_household_supports_size_greater_than_applicants() -> None:
    """Test 5d: Household supports size > len(applicants) (2 applicants + 3 children case)."""
    from lib.affordability import Applicant, Household

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
    from lib.affordability import Household

    kwargs = _valid_household_kwargs()
    kwargs["applicants"] = []
    with pytest.raises(ValidationError):
        Household(**kwargs)  # type: ignore[arg-type]


def test_request_discriminates_on_mode_field_via_json() -> None:
    """Test 7: AffordabilityRequest discriminates on `mode` from JSON."""
    from lib.affordability import AffordabilityRequest, ForwardModeRequest

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
    import json

    adapter: TypeAdapter[AffordabilityRequest] = TypeAdapter(AffordabilityRequest)
    request = adapter.validate_json(json.dumps(payload))
    assert isinstance(request, ForwardModeRequest)
    assert request.mode == "forward"


def test_va_target_loan_type_requires_va_block() -> None:
    """Test 8: target_loan_type=='va' without household.va raises ValidationError."""
    from lib.affordability import ForwardModeRequest

    kwargs = _valid_forward_request_kwargs()
    kwargs["target_loan_type"] = "va"
    # household.va is None by default in _valid_household_kwargs
    with pytest.raises(ValidationError) as exc:
        ForwardModeRequest(**kwargs)  # type: ignore[arg-type]
    assert "va" in str(exc.value).lower()


def test_conventional_above_80_ltv_requires_monthly_pmi() -> None:
    """Test 9: target=='conventional' AND ltv>0.80 AND monthly_pmi=None raises."""
    from lib.affordability import ForwardModeRequest

    kwargs = _valid_forward_request_kwargs()
    kwargs["target_loan_type"] = "conventional"
    # LTV = 350k/400k = 0.875 (>0.80); no monthly_pmi
    kwargs["loan_amount"] = Decimal("350000.00")
    kwargs["property_value"] = Decimal("400000.00")
    kwargs["monthly_pmi"] = None
    with pytest.raises(ValidationError) as exc:
        ForwardModeRequest(**kwargs)  # type: ignore[arg-type]
    assert "monthly_pmi" in str(exc.value)


def test_request_extra_field_forbidden() -> None:
    """Test 10: extra='forbid' rejects unknown fields on the request."""
    from lib.affordability import ForwardModeRequest

    kwargs = _valid_forward_request_kwargs()
    kwargs["nonexistent_field"] = "junk"
    with pytest.raises(ValidationError):
        ForwardModeRequest(**kwargs)  # type: ignore[arg-type]


def test_target_loan_type_crosswalk_table() -> None:
    """Test 11: TARGET_LOAN_TYPE_CROSSWALK exposes RESEARCH Open Q#3 cross-walk."""
    from lib.affordability import TARGET_LOAN_TYPE_CROSSWALK

    assert TARGET_LOAN_TYPE_CROSSWALK["conventional"] == frozenset({"conforming", "high_balance"})
    assert TARGET_LOAN_TYPE_CROSSWALK["jumbo"] == frozenset({"jumbo"})
    assert TARGET_LOAN_TYPE_CROSSWALK["fha"] == frozenset({"fha_standard", "fha_high_balance"})
    assert TARGET_LOAN_TYPE_CROSSWALK["va"] == frozenset({"va_standard", "va_high_balance"})
    assert TARGET_LOAN_TYPE_CROSSWALK["usda"] == frozenset({"usda"})


def test_target_loan_type_to_program_table() -> None:
    """Test 12: TARGET_LOAN_TYPE_TO_PROGRAM maps target to Phase 2 program kwarg."""
    from lib.affordability import TARGET_LOAN_TYPE_TO_PROGRAM

    assert TARGET_LOAN_TYPE_TO_PROGRAM["conventional"] == "conventional"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["jumbo"] == "conventional"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["fha"] == "fha"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["va"] == "va"
    assert TARGET_LOAN_TYPE_TO_PROGRAM["usda"] == "usda"


def test_evaluate_forward_returns_response_for_valid_request() -> None:
    """Test 13: evaluate_forward composes Phase 1/2/3 into AffordabilityResponse.

    Plan 04-02 replaced the cross-plan stub body; this test now exercises the
    happy path against the $400k @ 6.5%/30yr conforming oracle ($2528.27 monthly P&I).
    Mirrors Phase 2 02-02's pattern of REPLACING `test_*_raises_not_implemented_until_*`
    stub-presence tests with positive behavior tests when the stub body lands.
    """
    from lib.affordability import (
        AffordabilityResponse,
        Applicant,
        EscrowInputs,
        ForwardModeRequest,
        Household,
        LocationFIPS,
        MonthlyDebts,
        evaluate_forward,
    )

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
    assert response.ltv == Decimal("0.80")
    assert response.loan_type == "conforming"


def test_evaluate_reverse_is_cross_plan_stub() -> None:
    """Test 14: evaluate_reverse raises NotImplementedError citing Plan 04-03."""
    from lib.affordability import evaluate_reverse

    with pytest.raises(NotImplementedError) as exc:
        evaluate_reverse(None)  # type: ignore[arg-type]
    assert "Plan 04-03" in str(exc.value)


def test_response_required_fields() -> None:
    """Test 15: AffordabilityResponse requires the D-11 always-populated fields."""
    from lib.affordability import AffordabilityResponse

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
    from lib.affordability import AffordabilityResponse

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


# ---------------------------------------------------------------------------
# Wave 0 xfail stubs (AFFD-01..09 — bodies replaced in Wave 1+ plans)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-01 implementation pending (Plan 04-02)")
def test_AFFD_01_dti_calculations() -> None:
    """AFFD-01: DTI front-end + back-end exact Decimal (per RESEARCH Test Map).

    Wave 1+ replaces this body with real assertions against
    lib.affordability.evaluate_forward(...).
    """
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-02 implementation pending (Plan 04-02)")
def test_AFFD_02_ltv_calculation() -> None:
    """AFFD-02: LTV = loan_amount / property_value (per RESEARCH §LTV/CLTV)."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-03 implementation pending (Plan 04-02)")
def test_AFFD_03_cltv_with_junior_liens() -> None:
    """AFFD-03: CLTV = (loan_amount + sum(junior_liens)) / property_value (D-discretion: list[Money])."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-04 implementation pending (Plan 04-02)")
def test_AFFD_04_piti_composition() -> None:
    """AFFD-04: PITI = quantize_cents(P&I + tax + ins + HOA + MI) (D-01 caller-supplied escrow; D-02 predicate-derived MI; quantize ONCE end-of-period)."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-05 implementation pending (Plan 04-03)")
def test_AFFD_05_reverse_round_trip() -> None:
    """AFFD-05 + SC-2: npf.pv reverse + round-trip closure within Decimal('0.0001') (D-08 + D-09)."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-03")


@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-06 implementation pending (Plan 04-02)")
def test_AFFD_06_joint_applicants() -> None:
    """AFFD-06 + SC-5: sum(income) + min(credit_score) across applicants (D-05 + D-06)."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


@pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-07 implementation pending (Plan 04-04)")
def test_AFFD_07_blocked_by_va_residual_west_family_4() -> None:
    """AFFD-07 + SC-3: blocked_by == 'VA-RESIDUAL-WEST-FAMILY-4' verbatim (Phase 2 D-11 stable citation)."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-04")


@pytest.mark.xfail(strict=False, reason="Wave 2: AFFD-08 implementation pending (Plan 04-05)")
def test_AFFD_08_cli_smoke() -> None:
    """AFFD-08: scripts/affordability.py JSON-in/JSON-out subprocess smoke (D-13 + Phase 3 D-17/18/19)."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-05")


@pytest.mark.xfail(strict=False, reason="Wave 3: AFFD-09 implementation pending (Plan 04-06)")
def test_AFFD_09_household_example_yml_e2e() -> None:
    """AFFD-09 + SC-4: config/household.example.yml end-to-end via subprocess (D-15 + D-17 fixture)."""
    raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-06")
