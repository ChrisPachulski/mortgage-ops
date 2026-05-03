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

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

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


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-02 ships npf.rate seed")
def test_apr_solver_seeded_from_npf_rate(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-02: First Newton iterate is exactly Decimal(str(npf.rate(n, -pmt, pv, 0)))."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-03 (1 stub) — flipped in Wave 2
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-02 ships convergence test")
def test_apr_solver_converges_within_decimal_00001_tolerance(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-03 + ROADMAP SC-1: |estimated_apr - expected| <= Decimal('0.00001') for the Reg Z anchor."""
    pytest.fail("Wave 0 stub")


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


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-02 ships APRConvergenceError")
def test_apr_solver_raises_on_non_convergence() -> None:
    """Phase 7 contract: ill-conditioned input → APRConvergenceError(iterations, last_residual) after 50 caps."""
    pytest.fail("Wave 0 stub")
