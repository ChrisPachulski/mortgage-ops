"""Phase 14 Plan 14-04 verdict synthesis — VERD-01 unit tests.

Covers D-14-VERDICT-01..04 (verdict cascade tie-breaks):
  - D-14-VERDICT-01: FHA-MIP-burden WATCH when only FHA eligible & MIP > $300
  - D-14-VERDICT-02: income-shock WATCH when ANY eligible-at-preferred program
                     breaches the DTI ceiling under income x 0.70
  - D-14-VERDICT-03: severity precedence — GO wins over MIP-burden when ANY
                     non-FHA eligible at preferred DP; stress-fail WATCH still
                     downgrades GO
  - D-14-VERDICT-04: every VerdictReason carries predicate_code AND
                     computed_value (falsifiable-reason discipline)

Mirrors tests/test_affordability.py:test_blocked_by_citation_coverage for the
citation-coverage meta-test (Pitfall 12 mitigation).

Closes VERD-01 at the unit-test level; Plan 14-06 tightens to fixture-based
coverage when the golden fixtures land.

Per CLAUDE.md money discipline: exact Decimal equality; never
``pytest.approx`` / ``assertAlmostEqual``. Every Decimal is constructed from a
string literal (Pitfall 2).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from lib.household import Household
from lib.profile import Profile
from lib.property_analysis import (
    DownPaymentMatrix,
    ProgramResult,
    StressBlock,
    StressRow,
    Verdict,
)
from lib.property_verdict import (
    _MIP_BURDEN_THRESHOLD,
    VERDICT_GO,
    VERDICT_NO_GO_DTI_ALL_PROGRAMS,
    VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP,
    VERDICT_WATCH_FHA_MIP_BURDEN,
    VERDICT_WATCH_STRESS_INCOME_FAIL,
    synthesize,
)

# ---------------------------------------------------------------------------
# Helper builders (mirror tests/test_property_analysis.py L215-269 idiom)
# ---------------------------------------------------------------------------


def _make_eligible_cell(
    program: str,
    dp_pct: Decimal,
    *,
    piti: Decimal = Decimal("3760.34"),
    monthly_mi: Decimal = Decimal("0.00"),
    dti_back: Decimal = Decimal("0.350000"),
    ltv: Decimal = Decimal("0.800000"),
    loan_amount: Decimal = Decimal("500000.00"),
) -> ProgramResult:
    """Eligible ProgramResult with sensible defaults; per-test overrides take
    precedence. ``program`` must be one of the Plan 14-02 ProgramResult
    literals (Conv30, Conv15, FHA30, VA30, Jumbo30)."""
    return ProgramResult(
        program=program,  # type: ignore[arg-type]
        down_payment_pct=dp_pct,
        loan_amount=loan_amount,
        monthly_pi=Decimal("3160.34"),
        monthly_tax=Decimal("500.00"),
        monthly_insurance=Decimal("100.00"),
        monthly_hoa=Decimal("0.00"),
        monthly_mi=monthly_mi,
        piti=piti,
        cash_to_close=Decimal("125000.00"),
        dti_back=dti_back,
        ltv=ltv,
        eligible=True,
        blocker_reasons=[],
        eligible_reasons=[],
    )


def _make_ineligible_cell(
    program: str,
    dp_pct: Decimal,
    *,
    blocker_reasons: list[str],
    dti_back: Decimal = Decimal("0.620000"),
    ltv: Decimal = Decimal("0.970000"),
    loan_amount: Decimal = Decimal("605750.00"),
    monthly_mi: Decimal = Decimal("0.00"),
    piti: Decimal = Decimal("4200.00"),
) -> ProgramResult:
    """Ineligible ProgramResult with the given blocker_reasons."""
    return ProgramResult(
        program=program,  # type: ignore[arg-type]
        down_payment_pct=dp_pct,
        loan_amount=loan_amount,
        monthly_pi=Decimal("3600.00"),
        monthly_tax=Decimal("500.00"),
        monthly_insurance=Decimal("100.00"),
        monthly_hoa=Decimal("0.00"),
        monthly_mi=monthly_mi,
        piti=piti,
        cash_to_close=Decimal("18750.00"),
        dti_back=dti_back,
        ltv=ltv,
        eligible=False,
        blocker_reasons=blocker_reasons,
        eligible_reasons=[],
    )


def _make_matrix(cells: list[ProgramResult]) -> DownPaymentMatrix:
    """Wrap cells in a DownPaymentMatrix; programs_present + down_payment_pcts
    derived from the cells (de-duplicated, preserving first-seen order)."""
    programs: list[str] = []
    dps: list[Decimal] = []
    for c in cells:
        if c.program not in programs:
            programs.append(c.program)
        if c.down_payment_pct not in dps:
            dps.append(c.down_payment_pct)
    return DownPaymentMatrix(
        cells=cells,
        programs_present=programs,
        down_payment_pcts=dps,
    )


def _make_stress_row(
    program: str,
    stress_kind: str,
    *,
    breaches: bool = False,
    baseline_piti: Decimal = Decimal("3760.34"),
    stressed_piti: Decimal | None = Decimal("3760.34"),
    stressed_dti_back: Decimal = Decimal("0.400000"),
    blocker_reasons: list[str] | None = None,
) -> StressRow:
    return StressRow(
        program=program,
        stress_kind=stress_kind,  # type: ignore[arg-type]
        baseline_piti=baseline_piti,
        stressed_piti=stressed_piti,
        stressed_dti_back=stressed_dti_back,
        breaches_dti_ceiling=breaches,
        blocker_reasons=blocker_reasons if blocker_reasons is not None else [],
    )


def _make_stress_block(
    rows: list[StressRow],
    preferred_dp: Decimal = Decimal("0.200000"),
) -> StressBlock:
    return StressBlock(preferred_down_payment_pct=preferred_dp, rows=rows)


def _make_clean_household(
    preferred_dp: Decimal = Decimal("0.200000"),
    **overrides: Any,
) -> Household:
    defaults: dict[str, Any] = {
        "monthly_income": Decimal("12000.00"),
        "monthly_obligations": Decimal("400.00"),
        "fico": 740,
        "liquid_reserves": Decimal("100000.00"),
        "state_fips": "53",
        "county_fips": "033",
        "county_name": "King",
        "preferred_down_payment_pct": preferred_dp,
    }
    defaults.update(overrides)
    return Household(**defaults)


def _make_clean_profile(**overrides: Any) -> Profile:
    return Profile(**overrides)


# Scenario builders used by the citation-coverage meta-test below.


def _matrix_no_eligible() -> DownPaymentMatrix:
    """Matrix where every cell has eligible=False (Level 1 trigger)."""
    cells = [
        _make_ineligible_cell(
            "Conv30",
            Decimal("0.200000"),
            blocker_reasons=["DTI-CAP-CONVENTIONAL"],
            dti_back=Decimal("0.620000"),
        ),
        _make_ineligible_cell(
            "FHA30",
            Decimal("0.200000"),
            blocker_reasons=["DTI-CAP-FHA"],
            dti_back=Decimal("0.610000"),
        ),
    ]
    return _make_matrix(cells)


def _matrix_eligible_at_non_preferred_only() -> DownPaymentMatrix:
    """Matrix where Conv30 is eligible at DP=0.25 only, NOT at preferred 0.20."""
    cells = [
        _make_ineligible_cell(
            "Conv30",
            Decimal("0.200000"),
            blocker_reasons=["DTI-CAP-CONVENTIONAL"],
            dti_back=Decimal("0.540000"),
            ltv=Decimal("0.800000"),
        ),
        _make_eligible_cell(
            "Conv30",
            Decimal("0.250000"),
            ltv=Decimal("0.750000"),
            dti_back=Decimal("0.400000"),
        ),
    ]
    return _make_matrix(cells)


def _matrix_eligible_at_preferred() -> DownPaymentMatrix:
    """Matrix where Conv30 + FHA30 are both eligible at preferred DP=0.20."""
    cells = [
        _make_eligible_cell("Conv30", Decimal("0.200000")),
        _make_eligible_cell(
            "FHA30",
            Decimal("0.200000"),
            monthly_mi=Decimal("150.00"),  # under threshold
        ),
    ]
    return _make_matrix(cells)


def _matrix_fha_only_eligible_with_high_mip() -> DownPaymentMatrix:
    """Matrix where only FHA30 is eligible at preferred DP, with MIP > $300."""
    cells = [
        _make_ineligible_cell(
            "Conv30",
            Decimal("0.200000"),
            blocker_reasons=["LTV-CEILING-CONVENTIONAL"],
            dti_back=Decimal("0.440000"),
        ),
        _make_eligible_cell(
            "FHA30",
            Decimal("0.200000"),
            monthly_mi=Decimal("325.00"),  # over threshold
        ),
    ]
    return _make_matrix(cells)


def _empty_stress() -> StressBlock:
    return _make_stress_block(rows=[])


def _stress_with_income_shock_fail() -> StressBlock:
    """One income-shock row for Conv30 with breaches_dti_ceiling=True."""
    return _make_stress_block(
        rows=[
            _make_stress_row(
                "Conv30",
                "income_shock",
                breaches=True,
                stressed_dti_back=Decimal("0.520000"),
                blocker_reasons=["STRESS-INCOME-SHOCK-30PCT"],
            )
        ]
    )


# ---------------------------------------------------------------------------
# Cascade-level tests
# ---------------------------------------------------------------------------


def test_no_go_no_eligible() -> None:
    """Level 1 (D-14-VERDICT cascade entry; closes VERD-01) — Matrix with all
    cells eligible=False -> NO_GO with VERDICT_NO_GO_DTI_ALL_PROGRAMS reason."""
    matrix = _matrix_no_eligible()
    stress = _empty_stress()
    v: Verdict = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "NO_GO"
    assert len(v.reasons) == 1
    assert v.reasons[0].predicate_code == VERDICT_NO_GO_DTI_ALL_PROGRAMS
    # computed_value must be a Decimal-formatted string (min DTI across cells).
    assert v.reasons[0].computed_value == str(Decimal("0.610000"))


def test_no_go_at_preferred_dp() -> None:
    """Level 2 (D-14-VERDICT cascade) — Matrix has Conv30 eligible at DP=0.25
    but nothing eligible at preferred DP=0.20 -> NO_GO with
    VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP reason."""
    matrix = _matrix_eligible_at_non_preferred_only()
    stress = _empty_stress()
    v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "NO_GO"
    assert len(v.reasons) == 1
    assert v.reasons[0].predicate_code == VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP
    assert v.reasons[0].dp_pct == Decimal("0.200000")
    assert v.reasons[0].computed_value == str(Decimal("0.200000"))


def test_watch_income_shock() -> None:
    """Level 3 (D-14-VERDICT-02) — Eligible-at-preferred Conv30 AND an
    income-shock stress row with breaches_dti_ceiling=True -> WATCH with
    VERDICT_WATCH_STRESS_INCOME_FAIL reason; the failing program is named."""
    matrix = _matrix_eligible_at_preferred()
    stress = _stress_with_income_shock_fail()
    v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "WATCH"
    assert len(v.reasons) >= 1
    assert v.reasons[0].predicate_code == VERDICT_WATCH_STRESS_INCOME_FAIL
    assert v.reasons[0].program == "Conv30"
    assert v.reasons[0].computed_value == str(Decimal("0.520000"))


def test_watch_fha_mip_burden() -> None:
    """Level 4 (D-14-VERDICT-01) — All eligible-at-preferred cells are FHA30
    AND fha_cell.monthly_mi == $325 (> $300 threshold) AND no income-shock
    failures -> WATCH with VERDICT_WATCH_FHA_MIP_BURDEN reason."""
    matrix = _matrix_fha_only_eligible_with_high_mip()
    stress = _empty_stress()
    v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "WATCH"
    assert len(v.reasons) == 1
    assert v.reasons[0].predicate_code == VERDICT_WATCH_FHA_MIP_BURDEN
    assert v.reasons[0].program == "FHA30"
    assert v.reasons[0].dp_pct == Decimal("0.200000")
    assert v.reasons[0].computed_value == "325.00"


def test_go_non_fha_eligible() -> None:
    """Level 5 (D-14-VERDICT-03 GO default) — Conv30 eligible at preferred DP
    AND no income-shock failures -> GO with VERDICT_GO reason. computed_value
    is the count of non-FHA eligible programs as a string."""
    matrix = _matrix_eligible_at_preferred()  # Conv30 + FHA30 both eligible
    stress = _empty_stress()
    v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "GO"
    assert len(v.reasons) == 1
    assert v.reasons[0].predicate_code == VERDICT_GO
    # Conv30 is the one non-FHA eligible cell.
    assert v.reasons[0].computed_value == "1"


# ---------------------------------------------------------------------------
# Cascade-precedence tests (D-14-VERDICT-03)
# ---------------------------------------------------------------------------


def test_go_wins_over_mip_burden_when_non_fha_eligible() -> None:
    """D-14-VERDICT-03 severity precedence — Both Conv30 AND FHA30 are
    eligible at preferred DP, FHA monthly_mi=$325 (> threshold). Verdict is
    GO, not WATCH — MIP-burden does NOT downgrade when non-FHA is eligible."""
    cells = [
        _make_eligible_cell("Conv30", Decimal("0.200000")),
        _make_eligible_cell(
            "FHA30",
            Decimal("0.200000"),
            monthly_mi=Decimal("325.00"),  # over threshold, but ignored
        ),
    ]
    matrix = _make_matrix(cells)
    stress = _empty_stress()
    v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "GO"
    assert v.reasons[0].predicate_code == VERDICT_GO


def test_watch_income_shock_overrides_go() -> None:
    """D-14-VERDICT-02 vs D-14-VERDICT-03 — Same Conv30+FHA30 eligible matrix
    as test_go_non_fha_eligible, but Conv30 fails the income-shock stress.
    Verdict is WATCH, not GO — stress-fail WATCH still downgrades a GO."""
    matrix = _matrix_eligible_at_preferred()
    stress = _stress_with_income_shock_fail()  # Conv30 income-shock fail
    v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "WATCH"
    assert v.reasons[0].predicate_code == VERDICT_WATCH_STRESS_INCOME_FAIL


# ---------------------------------------------------------------------------
# Format-compliance test (D-14-VERDICT-04)
# ---------------------------------------------------------------------------


def test_reason_format_compliance() -> None:
    """D-14-VERDICT-04 — Every VerdictReason emitted across the cascade must
    have non-empty predicate_code AND non-empty computed_value strings.
    Iterates the 5 scenario builders + 2 precedence scenarios."""
    scenarios = [
        (_matrix_no_eligible(), _empty_stress()),
        (_matrix_eligible_at_non_preferred_only(), _empty_stress()),
        (_matrix_eligible_at_preferred(), _stress_with_income_shock_fail()),
        (_matrix_fha_only_eligible_with_high_mip(), _empty_stress()),
        (_matrix_eligible_at_preferred(), _empty_stress()),
    ]
    for matrix, stress in scenarios:
        v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
        assert v.reasons, f"Empty reasons in {v.level} verdict"
        for reason in v.reasons:
            assert len(reason.predicate_code) > 0, f"Empty predicate_code in {v.level}: {reason!r}"
            assert len(reason.computed_value) > 0, f"Empty computed_value in {v.level}: {reason!r}"


# ---------------------------------------------------------------------------
# Edge-case test (Behavior 9)
# ---------------------------------------------------------------------------


def test_empty_matrix_returns_no_go() -> None:
    """Behavior 9 — Degenerate empty matrix returns NO_GO without crashing
    (min(..., default=Decimal("0")) guards the empty iterable)."""
    matrix = DownPaymentMatrix(cells=[], programs_present=[], down_payment_pcts=[])
    stress = _empty_stress()
    v = synthesize(matrix, stress, _make_clean_household(), _make_clean_profile())
    assert v.level == "NO_GO"
    assert v.reasons[0].predicate_code == VERDICT_NO_GO_DTI_ALL_PROGRAMS
    # Degenerate default value: Decimal("0") stringified.
    assert v.reasons[0].computed_value == str(Decimal("0"))


# ---------------------------------------------------------------------------
# Citation-coverage meta-test (Pitfall 7 + 12; D-14-VERDICT-04 + VERD-01)
# ---------------------------------------------------------------------------


def test_verdict_code_citation_coverage() -> None:
    """Pitfall 12 + RESEARCH §"Validation Architecture": every VERDICT_*
    constant in lib/property_verdict.py must be emitted by at least one
    Phase-14 fixture's expected_response.verdict.reasons[].predicate_code OR
    by at least one cascade-level scenario in this file.

    Plan 14-06 tightens the prior in-test-only coverage to FIXTURE-FIRST
    coverage: fixtures contribute their predicate codes from
    tests/fixtures/property_analysis/*.json; the in-test cascade scenarios
    fill any branches the 3-fixture set cannot reach (only 5 of the 5 VERDICT_*
    branches can fire from a single synthesize() call, so 3 fixtures naturally
    cover a subset; the in-test scenarios complete the union per Pitfall 12).

    Mirrors tests/test_affordability.py:test_blocked_by_citation_coverage
    (fixture-first) + tests/test_stress.py:test_phase_08_citation_coverage_meta
    (phase-wide).

    Closes VERD-01 at the unit-test level (D-14-VERDICT-04 falsifiable-reason
    discipline)."""
    import json as _json

    import lib.property_verdict as v_mod

    constants = {
        name: val
        for name, val in vars(v_mod).items()
        if isinstance(name, str) and name.startswith("VERDICT_") and isinstance(val, str)
    }
    assert constants, "No VERDICT_* constants found in lib.property_verdict"

    # ------------------------------------------------------------------------
    # Phase 14-06 fixture-based coverage path (PRIMARY anchor)
    # ------------------------------------------------------------------------
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "property_analysis"
    assert fixtures_dir.is_dir(), (
        "tests/fixtures/property_analysis/ missing — Plan 14-06 fixtures not shipped"
    )
    fixture_predicate_codes: list[str] = []
    fixture_paths = sorted(fixtures_dir.glob("*.json"))
    assert len(fixture_paths) >= 3, (
        f"Plan 14-06 requires 3 golden fixtures; found {len(fixture_paths)}: {fixture_paths}"
    )
    for fp in fixture_paths:
        data = _json.loads(fp.read_text())
        expected = data.get("expected_response", {})
        verdict = expected.get("verdict", {})
        for r in verdict.get("reasons", []):
            code = r.get("predicate_code", "")
            if code:
                fixture_predicate_codes.append(code)

    emitted: set[str] = set(fixture_predicate_codes)

    # ------------------------------------------------------------------------
    # In-test cascade supplemental coverage (covers VERDICT_* branches that
    # the 3-fixture set cannot naturally reach — Pitfall 12 completeness gate)
    # ------------------------------------------------------------------------

    # Level 1: NO_GO no-eligible
    v1 = synthesize(
        _matrix_no_eligible(),
        _empty_stress(),
        _make_clean_household(),
        _make_clean_profile(),
    )
    emitted.update(r.predicate_code for r in v1.reasons)

    # Level 2: NO_GO not-at-preferred-DP
    v2 = synthesize(
        _matrix_eligible_at_non_preferred_only(),
        _empty_stress(),
        _make_clean_household(),
        _make_clean_profile(),
    )
    emitted.update(r.predicate_code for r in v2.reasons)

    # Level 3: WATCH income-shock
    v3 = synthesize(
        _matrix_eligible_at_preferred(),
        _stress_with_income_shock_fail(),
        _make_clean_household(),
        _make_clean_profile(),
    )
    emitted.update(r.predicate_code for r in v3.reasons)

    # Level 4: WATCH FHA-MIP-burden
    v4 = synthesize(
        _matrix_fha_only_eligible_with_high_mip(),
        _empty_stress(),
        _make_clean_household(),
        _make_clean_profile(),
    )
    emitted.update(r.predicate_code for r in v4.reasons)

    # Level 5: GO
    v5 = synthesize(
        _matrix_eligible_at_preferred(),
        _empty_stress(),
        _make_clean_household(),
        _make_clean_profile(),
    )
    emitted.update(r.predicate_code for r in v5.reasons)

    # Every VERDICT_* constant must appear in at least one emitted reason
    # (fixture predicate_codes OR in-test cascade scenarios).
    for name, code in constants.items():
        assert code in emitted, (
            f"{name}={code!r} not exercised by any fixture predicate_code "
            f"NOR by any cascade-level scenario in tests/test_property_verdict.py"
        )

    # Hard gate: the 3 fixtures MUST contribute at least one valid VERDICT_*
    # predicate (otherwise the fixture coverage is decorative; this is the
    # "fixture-first" assertion that distinguishes Plan 14-06 tightening from
    # the pure in-test approach of Plan 14-04).
    valid_codes = set(constants.values())
    assert any(c in valid_codes for c in fixture_predicate_codes), (
        f"None of the 3 Phase 14-06 fixtures contributed a valid VERDICT_* "
        f"predicate_code (got: {sorted(set(fixture_predicate_codes))!r}); "
        f"valid VERDICT_* values are {sorted(valid_codes)!r}"
    )


def test_phase_14_requirement_coverage_meta() -> None:
    """RESEARCH §"Validation Architecture": every ANLZ-XX + VERD-01 requirement
    appears in at least one tests/fixtures/property_analysis/*.json fixture's
    _meta.citation or _meta.requirements.

    Plan 14-06 SC: closes ANLZ-01..03 + VERD-01 at the FIXTURE level (in
    addition to the existing unit + integration levels from Plans 14-02..05).

    Mirrors tests/test_stress.py:test_phase_08_citation_coverage_meta — Pitfall
    12 phase-level requirement-coverage gate."""
    import json as _json

    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "property_analysis"
    assert fixtures_dir.is_dir(), (
        "tests/fixtures/property_analysis/ missing — Plan 14-06 fixtures not shipped"
    )

    all_citations: list[str] = []
    all_requirements: set[str] = set()
    fixture_paths = sorted(fixtures_dir.glob("*.json"))
    for fp in fixture_paths:
        data = _json.loads(fp.read_text())
        meta = data.get("_meta", {})
        citation = meta.get("citation", "")
        if citation:
            all_citations.append(citation)
        all_requirements.update(meta.get("requirements", []))

    target_ids = ["ANLZ-01", "ANLZ-02", "ANLZ-03", "VERD-01"]
    for req_id in target_ids:
        in_citation = any(req_id in c for c in all_citations)
        in_requirements = req_id in all_requirements
        assert in_citation or in_requirements, (
            f"Phase 14 requirement {req_id} not found in any fixture's "
            f"_meta.citation or _meta.requirements (citations checked: "
            f"{len(all_citations)}; requirements set: {sorted(all_requirements)})"
        )


# ---------------------------------------------------------------------------
# Phase 14 requirement-coverage meta-test
# ---------------------------------------------------------------------------


def test_phase_14_verdict_requirement_coverage() -> None:
    """Every D-14-VERDICT-XX decision + VERD-01 requirement is referenced by
    at least one test docstring in this file. Pattern from
    tests/test_stress.py:test_phase_08_citation_coverage_meta — Pitfall 12
    Phase-level requirement-coverage gate."""
    source = Path(__file__).read_text()
    required_refs = [
        "D-14-VERDICT-01",
        "D-14-VERDICT-02",
        "D-14-VERDICT-03",
        "D-14-VERDICT-04",
        "VERD-01",
    ]
    for ref in required_refs:
        assert ref in source, f"No test references {ref} in tests/test_property_verdict.py"


# ---------------------------------------------------------------------------
# Pin _MIP_BURDEN_THRESHOLD to the policy choice (Assumption A1)
# ---------------------------------------------------------------------------


def test_mip_burden_threshold_pinned_at_300() -> None:
    """Assumption A1 + D-14-VERDICT-01: _MIP_BURDEN_THRESHOLD is Decimal('300.00').
    If this changes, the WATCH-FHA-MIP-burden boundary moves and downstream
    Plan 14-06 golden fixtures need re-anchoring."""
    assert Decimal("300.00") == _MIP_BURDEN_THRESHOLD
