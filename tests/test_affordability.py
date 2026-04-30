"""Phase 4 Affordability — test surface (AFFD-01..09).

Wave 0 stub: every AFFD-XX requirement has a stub function that pytest
collects. Stubs are marked `pytest.mark.xfail(strict=False, reason="Wave N
implementation pending")` so the suite stays green during Wave 1-3
implementation. Each Wave 1+ task replaces its stub body with the real
test (RED->GREEN flip).

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

from pathlib import Path

import pytest

AFFORDABILITY_MODULE_PATH: Path = (
    Path(__file__).resolve().parent.parent / "lib" / "affordability.py"
)
SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "affordability.py"
"""Phase 4 CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""


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
