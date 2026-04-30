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


def test_evaluate_reverse_returns_response_for_valid_request() -> None:
    """Test 14: evaluate_reverse positive behavior — SC-2 anchor (replaces Plan 04-01 stub-presence test).

    SC-2 anchor: max_dti=0.43, joint income=10000, no debts, no escrow,
    conventional, target_ltv=0.80, 7%/30yr, down_payment=100000.
    Verifies response shape (mode='reverse'; assumed_ltv_pct echoed;
    assumed_monthly_mi=0 for conventional<=80; max_loan_amount > 0;
    implied_pi > 0; loan_type populated).

    Round-trip closure (D-09) is asserted in Plan 04-06's fixture-based
    test_AFFD_05_reverse_round_trip; this test verifies only the basic
    contract that evaluate_reverse returns a populated AffordabilityResponse
    on a happy-path request.
    """
    from lib.affordability import (
        AffordabilityResponse,
        Applicant,
        EscrowInputs,
        Household,
        LocationFIPS,
        MonthlyDebts,
        ReverseModeRequest,
        evaluate_reverse,
    )

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
    # Conventional + LTV<=0.80 → no PMI
    assert resp.assumed_monthly_mi == Decimal("0.00")
    # Forward-only fields are None in reverse mode
    assert resp.dti_front is None
    assert resp.dti_back is None
    assert resp.ltv is None
    assert resp.cltv is None
    assert resp.monthly_pi is None
    assert resp.piti is None
    # Reverse-only fields populated
    assert resp.max_loan_amount is not None
    assert resp.max_loan_amount > Decimal("0.00")
    assert resp.implied_pi is not None
    assert resp.implied_pi > Decimal("0.00")
    # Loan-type classified (no blocker for SC-2 anchor)
    assert resp.loan_type is not None


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


# ---------------------------------------------------------------------------
# Plan 04-04 Task 1: D-11 blocker citation constants + ceiling tables
# ---------------------------------------------------------------------------


def test_ltv_ceiling_table_values() -> None:
    """Plan 04-04 Task 1 Tests 1-5: LTV_CEILING_BY_TARGET per RESEARCH §LTV/CLTV."""
    from lib.affordability import LTV_CEILING_BY_TARGET

    assert LTV_CEILING_BY_TARGET["conventional"] == Decimal("0.97")
    assert LTV_CEILING_BY_TARGET["fha"] == Decimal("0.965")
    assert LTV_CEILING_BY_TARGET["va"] == Decimal("1.00")
    assert LTV_CEILING_BY_TARGET["usda"] == Decimal("1.00")
    assert LTV_CEILING_BY_TARGET["jumbo"] == Decimal("1.00")


def test_cltv_ceiling_table_values() -> None:
    """Plan 04-04 Task 1: CLTV_CEILING_BY_TARGET mirrors LTV ceilings for v1."""
    from lib.affordability import CLTV_CEILING_BY_TARGET

    assert CLTV_CEILING_BY_TARGET["conventional"] == Decimal("0.97")
    assert CLTV_CEILING_BY_TARGET["fha"] == Decimal("0.965")
    assert CLTV_CEILING_BY_TARGET["va"] == Decimal("1.00")
    assert CLTV_CEILING_BY_TARGET["usda"] == Decimal("1.00")
    assert CLTV_CEILING_BY_TARGET["jumbo"] == Decimal("1.00")


def test_blocked_by_citation_template_constants() -> None:
    """Plan 04-04 Task 1 Tests 6-10: hard-blocker citation templates."""
    from lib.affordability import (
        BLOCKED_BY_ATR_QM_PRICE_FIRST,
        BLOCKED_BY_CLTV_CEILING_TEMPLATE,
        BLOCKED_BY_DTI_CAP_TEMPLATE,
        BLOCKED_BY_LTV_CEILING_TEMPLATE,
        BLOCKED_BY_USDA_INCOME_TEMPLATE,
        BLOCKED_BY_VA_RESIDUAL_PATTERN,
    )

    assert BLOCKED_BY_DTI_CAP_TEMPLATE == "DTI-CAP-{LOAN_TYPE}"
    assert BLOCKED_BY_LTV_CEILING_TEMPLATE == "LTV-CEILING-{LOAN_TYPE}"
    assert BLOCKED_BY_CLTV_CEILING_TEMPLATE == "CLTV-CEILING-{LOAN_TYPE}"
    assert BLOCKED_BY_USDA_INCOME_TEMPLATE == "USDA-INCOME-LIMIT-{state_fips}-{county_fips}"
    assert BLOCKED_BY_ATR_QM_PRICE_FIRST == "ATR-QM-PRICE-FIRST"
    assert (
        BLOCKED_BY_VA_RESIDUAL_PATTERN == r"^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$"
    )


def test_warning_citation_constants() -> None:
    """Plan 04-04 Task 1 Tests 11-14: soft-warning citation strings + templates."""
    from lib.affordability import (
        WARNING_ATR_QM_NOT_EVALUATED,
        WARNING_FANNIE_LLPA_TEMPLATE,
        WARNING_FREDDIE_INELIGIBLE_TEMPLATE,
        WARNING_HPA_PMI_REQUIRED,
    )

    assert WARNING_HPA_PMI_REQUIRED == "HPA-PMI-REQUIRED"
    assert WARNING_ATR_QM_NOT_EVALUATED == "ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR"
    assert WARNING_FANNIE_LLPA_TEMPLATE == "FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}"
    assert WARNING_FREDDIE_INELIGIBLE_TEMPLATE == "FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}"


def test_citation_constants_module_level_exposure() -> None:
    """Plan 04-04 Task 1 Test 15: BLOCKED_BY_* + WARNING_* constants are
    module-level (citation-coverage meta-test in Plan 04-06 introspects via
    `dir(lib.affordability)` to discover them)."""
    import lib.affordability as aff

    names = dir(aff)
    blocked_by_constants = [n for n in names if n.startswith("BLOCKED_BY_")]
    warning_constants = [n for n in names if n.startswith("WARNING_")]
    # Plan 04-06 grep introspection target: at least 5 BLOCKED_BY_* constants
    assert len(blocked_by_constants) >= 5, blocked_by_constants
    # ... and at least 4 WARNING_* constants
    assert len(warning_constants) >= 4, warning_constants


# ---------------------------------------------------------------------------
# Plan 04-04 Task 2: _evaluate_blockers + public evaluate() dispatcher
# ---------------------------------------------------------------------------


def _make_clean_household(**overrides: object) -> object:
    """Build a clean household for blocker tests. Returns Household."""
    from lib.affordability import (
        Applicant,
        EscrowInputs,
        Household,
        LocationFIPS,
        MonthlyDebts,
    )

    defaults = dict(
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


def test_evaluate_clean_conventional_no_blocker() -> None:
    """Task 2 Test 1: clean conv 80% LTV → blocked=False, blocked_by=None."""
    from lib.affordability import ForwardModeRequest, evaluate

    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
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
    → blocked=True, blocked_by='VA-RESIDUAL-WEST-FAMILY-4' VERBATIM from predicate."""
    from lib.affordability import ForwardModeRequest, VAInputs, evaluate

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
        household=household,  # type: ignore[arg-type]
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
    from lib.affordability import (
        EscrowInputs,
        ForwardModeRequest,
        MonthlyDebts,
        evaluate,
    )

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
        household=household,  # type: ignore[arg-type]
        max_dti=Decimal("0.380000"),  # tight cap
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
    """Task 2 Test 4: conv loan with LTV=0.98 (above 0.97 ceiling) → blocked_by='LTV-CEILING-CONVENTIONAL'."""
    from lib.affordability import ForwardModeRequest, evaluate

    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("250.00"),  # required for conv > 0.80 LTV
        loan_amount=Decimal("490000.00"),
        property_value=Decimal("500000.00"),  # LTV = 0.98
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "LTV-CEILING-CONVENTIONAL"


def test_evaluate_classify_blocker_preserved_for_jumbo() -> None:
    """Task 2 Test 5: jumbo-classify-step blocker (Plan 04-02) precedes precedence pipeline."""
    from lib.affordability import Applicant, ForwardModeRequest, evaluate

    household = _make_clean_household(
        applicants=[
            Applicant(
                name="A",
                gross_monthly_income=Decimal("50000.00"),  # high enough that DTI stays sane
                credit_score=720,
            ),
        ],
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("2000000.00"),  # jumbo-tier for King WA
        property_value=Decimal("2500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by is not None
    assert resp.blocked_by.startswith("FHFA-LIMIT-CONFORMING-")


def test_evaluate_usda_income_blocker() -> None:
    """Task 2 Test 6: USDA target with household income above USDA limit
    → blocked_by='USDA-INCOME-LIMIT-{state_fips}-{county_fips}'."""
    from lib.affordability import Applicant, ForwardModeRequest, evaluate

    household = _make_clean_household(
        applicants=[
            Applicant(
                name="A",
                gross_monthly_income=Decimal("30000.00"),  # ~$360k/yr — way above USDA limit
                credit_score=720,
            ),
        ],
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,  # type: ignore[arg-type]
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
    from lib.affordability import (
        BLOCKED_BY_ATR_QM_PRICE_FIRST,
        ForwardModeRequest,
        evaluate,
    )

    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        apr=Decimal("0.090000"),
        apor=Decimal("0.040000"),  # 5pp spread > 2.25pp threshold for first-lien tier-1
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == BLOCKED_BY_ATR_QM_PRICE_FIRST


def test_evaluate_atr_qm_advisory_when_apr_apor_missing() -> None:
    """Task 2 Test 8: both apr and apor None → ATR-QM-NOT-EVALUATED warning, no blocker."""
    from lib.affordability import (
        WARNING_ATR_QM_NOT_EVALUATED,
        ForwardModeRequest,
        evaluate,
    )

    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    assert WARNING_ATR_QM_NOT_EVALUATED in resp.warnings
    # Not blocked on ATR/QM (advisory only when missing)
    assert resp.blocked_by != "ATR-QM-PRICE-FIRST"


def test_evaluate_hpa_pmi_required_warning_for_conv_above_80_ltv() -> None:
    """Task 2 Test 9: conventional 85% LTV with monthly_pmi
    → warnings contains 'HPA-PMI-REQUIRED'."""
    from lib.affordability import WARNING_HPA_PMI_REQUIRED, ForwardModeRequest, evaluate

    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("150.00"),
        loan_amount=Decimal("425000.00"),
        property_value=Decimal("500000.00"),  # LTV = 0.85
    )
    resp = evaluate(req)
    assert WARNING_HPA_PMI_REQUIRED in resp.warnings


def test_evaluate_invariant_blocked_iff_blocked_by() -> None:
    """Task 2 Test 15: response.blocked is True iff response.blocked_by is not None."""
    from lib.affordability import ForwardModeRequest, evaluate

    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("490000.00"),
        property_value=Decimal("500000.00"),  # LTV=0.98 → ceiling blocker
        monthly_pmi=Decimal("250.00"),
    )
    resp = evaluate(req)
    assert resp.blocked is (resp.blocked_by is not None)


def test_evaluate_dispatcher_routes_reverse_mode() -> None:
    """Task 2 Test 14: public evaluate() dispatches by mode → ReverseModeRequest."""
    from lib.affordability import (
        Applicant,
        ReverseModeRequest,
        evaluate,
    )

    household = _make_clean_household(
        applicants=[
            Applicant(name="A", gross_monthly_income=Decimal("5000.00"), credit_score=720),
            Applicant(name="B", gross_monthly_income=Decimal("5000.00"), credit_score=680),
        ],
        size=2,
    )
    req = ReverseModeRequest(
        mode="reverse",
        household=household,  # type: ignore[arg-type]
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
    from lib.affordability import ForwardModeRequest, VAInputs, evaluate

    household = _make_clean_household(
        size=4,
        va=VAInputs(
            region="west",
            family_size=4,
            actual_residual_income=Decimal("2000.00"),  # well above $1,117 minimum
        ),
    )
    req = ForwardModeRequest(
        mode="forward",
        household=household,  # type: ignore[arg-type]
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
    from lib.affordability import ForwardModeRequest, evaluate

    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        loan_amount=Decimal("400000.00"),
        property_value=Decimal("500000.00"),
    )
    resp = evaluate(req)
    # No VA-RESIDUAL citation in either blocked_by or warnings
    if resp.blocked_by is not None:
        assert not resp.blocked_by.startswith("VA-RESIDUAL")
    assert all(not w.startswith("VA-RESIDUAL") for w in resp.warnings)


def test_evaluate_va_residual_citation_read_verbatim_not_constructed() -> None:
    """Task 2 Test 13: Phase 4 reads VA citation from predicate, never constructs it."""
    import inspect

    from lib import affordability

    # Negative-grep gate: source must NOT contain `f"VA-RESIDUAL-` (anywhere
    # — comments included, since the literal grep gate is the discipline).
    source = inspect.getsource(affordability)
    assert 'f"VA-RESIDUAL-' not in source, (
        "Phase 4 must NEVER construct the VA-residual citation; reads "
        "verbatim via va_result.binding_rule_citation per Phase 2 D-11"
    )
    # Positive evidence: the verbatim-read site exists.
    assert "va_result.binding_rule_citation" in source


def test_evaluate_blockers_appends_soft_warnings_even_when_blocked() -> None:
    """Task 2 T-04-04-05: soft warnings always evaluated even when hard-blocked."""
    from lib.affordability import (
        WARNING_ATR_QM_NOT_EVALUATED,
        ForwardModeRequest,
        evaluate,
    )

    # LTV ceiling blocker fires first, but ATR-QM-NOT-EVALUATED warning
    # must still appear (apr/apor both None).
    req = ForwardModeRequest(
        mode="forward",
        household=_make_clean_household(),  # type: ignore[arg-type]
        max_dti=Decimal("0.430000"),
        target_loan_type="conventional",
        term_months=360,
        annual_rate=Decimal("0.065000"),
        monthly_pmi=Decimal("250.00"),
        loan_amount=Decimal("490000.00"),
        property_value=Decimal("500000.00"),  # LTV=0.98 → blocker
    )
    resp = evaluate(req)
    assert resp.blocked is True
    assert resp.blocked_by == "LTV-CEILING-CONVENTIONAL"
    assert WARNING_ATR_QM_NOT_EVALUATED in resp.warnings
