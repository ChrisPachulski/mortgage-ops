"""Phase 7 Estimated APR — full test surface (APR-01..08 + cross-cutting).

Per Phase 3 D-17 portability + Phase 4 D-13 inheritance: subprocess
invocation only for CLI tests, never `import scripts.apr_reg_z`
directly.

Wave 0 (Plan 07-00) creates ALL 13 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 1 (Plan 07-01 Pydantic models): APR-01 partial (1 stub)
- Wave 2 (Plan 07-02 Newton-Raphson engine): APR-01 + APR-02 + APR-03 + non-conv (4 stubs)
- Wave 3 (Plan 07-03 odd-first-period helpers): rolled into Wave 5 fixture flips
- Wave 4 (Plan 07-04 CLI): APR-06 + APR-07 + 3 CLI cross-cutting (5 stubs)
- Wave 5 (Plan 07-05 tests + Reg Z anchor): APR-05 + iteration-cap (2 stubs)
- Wave 6 (Plan 07-06 references doc): APR-08 (1 stub)
- Wave 7 (Plan 07-07 FFIEC fixtures): APR-04 (1 stub)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy_financial as npf
import pytest
from lib.apr import (
    AdvanceScheduleEntry,
    APRConvergenceError,
    APRRequest,
    PaymentScheduleEntry,
    _seed_apr,
    solve_apr,
)
from lib.models import Loan

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "apr_reg_z.py"
APR_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "apr.py"


# =========================================================================
# APR-01 (1 stub) — flipped in Wave 1 + 2
# =========================================================================


def test_apr_solver_module_exists_with_newton_raphson_signature() -> None:
    """APR-01: lib/apr.py exposes solve_apr(APRRequest) -> APRResponse using Newton-Raphson.

    Wave 1 (Plan 07-01) ships the boundary models + a NotImplementedError
    stub for solve_apr; Wave 2 (Plan 07-02) fills the body. This test
    asserts the contract that Wave 2 will satisfy: the function name +
    parameter name + return annotation. The body raising
    NotImplementedError is fine for Wave 1 — only the signature is checked.
    """
    import inspect

    from lib.apr import APRRequest, APRResponse, solve_apr

    # APRRequest + APRResponse must be importable as classes
    assert APRRequest is not None
    assert APRResponse is not None

    sig = inspect.signature(solve_apr)
    assert "request" in sig.parameters, (
        f"solve_apr must accept a 'request' parameter; got {list(sig.parameters)}"
    )
    # Under `from __future__ import annotations` the return annotation is the
    # string 'APRResponse' at runtime; under eager evaluation it is the class.
    # Accept either to keep the contract resilient to import-time changes.
    assert sig.return_annotation is APRResponse or sig.return_annotation == "APRResponse", (
        f"solve_apr must return APRResponse; got {sig.return_annotation!r}"
    )


# =========================================================================
# APR-02 (1 stub) — flipped in Wave 2
# =========================================================================


def test_apr_solver_seeded_from_npf_rate(
    apr_fixture: Callable[[str], dict[str, Any]],  # signature parity with sibling stubs
) -> None:
    """APR-02: _seed_apr returns the npf.rate-of-the-regular-transaction approximation as Decimal.

    Wave 2 (Plan 07-02) ships ``_seed_apr`` which casts npf.rate's float output
    through ``Decimal(str(...))`` once at the boundary (D-11). Because
    _seed_apr's float-domain arithmetic (sum/divide rather than the literal
    pmt) introduces a few ULPs of drift vs a direct npf.rate(n, -pmt, pv) call,
    the assertion checks near-equality (within 1e-12 absolute) rather than
    bit-exact identity. The IMPORTANT contract is: the seed comes from
    npf.rate (not a hand-rolled approximation) and stays Decimal thereafter.
    """
    advances = [
        AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("5000.00")),
    ]
    payments = [
        PaymentScheduleEntry(
            starting_unit_period=1,
            periods=36,
            amount=Decimal("166.07"),
        ),
    ]
    seed = _seed_apr(advances, payments)
    direct_seed = Decimal(str(float(npf.rate(nper=36, pmt=-166.07, pv=5000.0, fv=0))))
    drift = abs(seed - direct_seed)
    # The seed function computes pmt_avg = total/n which differs from direct
    # pmt by a few ULPs in float arithmetic; the resulting npf.rate output
    # drifts by < 1e-12.
    assert drift < Decimal("0.0000000001"), (
        f"_seed_apr drift from direct npf.rate exceeds 1e-10: {drift}"
    )
    # Sanity: seed is in [0, 1] (the documented in-range region)
    assert Decimal("0") <= seed <= Decimal("1"), f"seed out of [0, 1]: {seed}"


# =========================================================================
# APR-03 (1 stub) — flipped in Wave 2
# =========================================================================


def test_apr_solver_converges_within_decimal_00001_tolerance(
    apr_fixture: Callable[
        [str], dict[str, Any]
    ],  # Wave 5 swaps in apr_fixture("regz_appendix_j_5000_36_166_07")
) -> None:
    """APR-03 + ROADMAP SC-1: \\|estimated_apr - expected\\| <= Decimal('0.00001') for the Reg Z anchor.

    Reg Z Appendix J Example J-1: \\$5000 / 36 monthly payments of \\$166.07
    → 12.00% APR. Wave 5 (Plan 07-05) ships the
    ``regz_appendix_j_5000_36_166_07.json`` fixture; until then this test
    constructs the inputs inline (TODO: swap to apr_fixture("regz_appendix_j_5000_36_166_07")
    when the Wave 5 fixture lands).
    """
    loan = Loan(
        principal=Decimal("5000.00"),
        annual_rate=Decimal("0.120000"),
        term_months=36,
        origination_date=date(2026, 1, 1),
    )
    request = APRRequest(
        loan=loan,
        finance_charges=Decimal("0.00"),
        advance_schedule=[
            AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("5000.00")),
        ],
        payment_schedule=[
            PaymentScheduleEntry(
                starting_unit_period=1,
                periods=36,
                amount=Decimal("166.07"),
            ),
        ],
    )
    response = solve_apr(request)
    expected_apr = Decimal("0.120000")
    diff = abs(response.estimated_apr - expected_apr)
    assert diff <= Decimal("0.00001"), (
        f"SC-1: APR must equal 12.00% within Decimal('0.00001'); "
        f"got {response.estimated_apr} (diff={diff})"
    )
    # SC-3 sub-anchor: the Reg Z fixture must converge well under 50 iterations
    assert 1 <= response.iterations <= 50, (
        f"SC-3: iterations must be in [1, 50]; got {response.iterations}"
    )
    # Dollar residual sanity (D-10): converged residual <= one cent
    assert response.final_residual <= Decimal("0.01"), (
        f"D-10: final_residual must be <= \\$0.01; got {response.final_residual}"
    )


# =========================================================================
# APR-04 (1 stub) — flipped in Wave 7 (FFIEC capture human checkpoint)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-07 ships 20+ FFIEC fixtures")
def test_apr_ffiec_oracle_fixtures_match_within_decimal_00001(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-04 + ROADMAP SC-2: All 20+ FFIEC captures pass within Decimal('0.00001')."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-05 (1 stub) — flipped in Wave 5
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 07-05 ships regz_appendix_j_5000_36_166_07.json",
)
def test_apr_reg_z_appendix_j_worked_example_returns_12_percent(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-05 + ROADMAP SC-1: $5000 / 36 monthly $166.07 → APR == 12.00% within Decimal('0.00001')."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-06 (1 stub) — flipped in Wave 4
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 07-04 ships APRResponse.summary literal-text contract",
)
def test_apr_response_uses_literal_estimated_apr_text(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-06 + ROADMAP SC-4: APRResponse.summary contains literal 'estimated APR'; never bare 'APR'."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-07 (1 stub) — flipped in Wave 4
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships scripts/apr_reg_z.py")
def test_apr_cli_subprocess_round_trip(
    apr_fixture: Callable[[str], dict[str, Any]], tmp_path: Path
) -> None:
    """APR-07: CLI subprocess round-trip — write JSON, invoke, parse stdout."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-08 (1 stub) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-06 ships references/apr-reg-z.md")
def test_references_apr_reg_z_doc_present_with_required_sections() -> None:
    """APR-08 + ROADMAP SC-5: references/apr-reg-z.md exists with §1-6 (unit-period, day-count, odd-first, worked example, Newton, citations)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# Cross-cutting (5 stubs)
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 07-02 + 07-05 enforce SC-3 iteration cap",
)
def test_newton_raphson_iterations_under_50_for_all_fixtures(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-3: every fixture (anchor + 20 FFIEC) converges in <=50 Newton iterations."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 07-04 ships lazy-import in scripts/apr_reg_z.py",
)
def test_apr_cli_help_does_not_import_lib_apr() -> None:
    """D-18 inheritance: --help fast (no lib.apr or numpy_financial import before argparse)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships float-gate")
def test_apr_cli_rejects_float_loan_amount(tmp_path: Path) -> None:
    """D-19 + WR-02 inheritance: CLI rejects JSON-float in loan.principal with 6-key envelope."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships uniform envelope")
def test_apr_cli_error_envelope_uniformity(tmp_path: Path) -> None:
    """WR-02 inheritance: float-gate + Pydantic ValidationError emit identical 6-key shape."""
    pytest.fail("Wave 0 stub")


def test_apr_solver_raises_on_non_convergence() -> None:
    """Phase 7 contract: ill-conditioned input → APRConvergenceError(iterations, last_residual).

    Construct an APRRequest where the payments sum to far less than the
    advances; no positive-rate solution exists. The Newton iterate either
    wanders out of the (1+i) > 0 domain or fails the dual-criterion check
    within MAX_ITER iterations — either way solve_apr must raise
    APRConvergenceError (a ValueError subclass) carrying iteration count,
    last residual, and last rate guess for caller debugging.
    """
    loan = Loan(
        principal=Decimal("5000.00"),
        annual_rate=Decimal("0.001000"),
        term_months=36,
        origination_date=date(2026, 1, 1),
    )
    request = APRRequest(
        loan=loan,
        finance_charges=Decimal("0.00"),
        advance_schedule=[
            AdvanceScheduleEntry(unit_period_offset=0, amount=Decimal("5000.00")),
        ],
        # Payments sum to \\$36 but advances total \\$5000 → no positive-rate solution
        payment_schedule=[
            PaymentScheduleEntry(
                starting_unit_period=1,
                periods=36,
                amount=Decimal("1.00"),
            ),
        ],
    )
    with pytest.raises(APRConvergenceError) as excinfo:
        solve_apr(request)
    err = excinfo.value
    # ValueError subclass per Phase 4 D-13 inheritance
    assert isinstance(err, ValueError), "APRConvergenceError must subclass ValueError"
    # Surfaces iterations + last_residual + last_i for caller debugging
    assert err.iterations >= 0
    assert isinstance(err.last_residual, Decimal)
    assert isinstance(err.last_i, Decimal)
