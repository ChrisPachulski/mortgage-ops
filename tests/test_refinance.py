"""Phase 6 Refinance NPV — full test surface (REFI-01..09 + SC-1..SC-5 + cross-cutting).

Per Phase 3 D-17 portability + Phase 4 D-13 inheritance + Phase 5 inheritance:
subprocess invocation only for CLI tests, never `import scripts.refi_npv`
directly. SCRIPT_PATH is the single constant edited at Phase 10 when scripts/
relocates to .claude/skills/mortgage-ops/scripts/.

Wave 0 (Plan 06-00) creates ALL 25 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 1 (Plan 06-01 RefiCashflow + sign-validator + module docstring cite):
  4 sign-validator tests + 1 module-docstring cite (5 flips)
- Wave 2 (Plan 06-02 rate-and-term engine + breakeven helpers):
  empirical engine validation; no test flips (0 flips)
- Wave 3 (Plan 06-03 cash-out + after-tax mode):
  1 after-tax validator (1 flip)
- Wave 4 (Plan 06-04 CLI scripts/refi_npv.py + 6-key envelope):
  6 CLI tests (6 flips)
- Wave 5 (Plan 06-05 fixtures + REFI-01..03/05..07 + SC-1..3 + breakeven divergence):
  11 fixture-driven flips (rate-and-term + cash-out + breakeven + cashflow-kind
  citation coverage + pyxirr-deferral docstring assertion)
- Wave 6 (Plan 06-06 references/refi-npv.md doc):
  2 doc tests (sections + sign-convention phrase)

Each xfail decorator carries `strict=True` so a passing test in xfail state
raises XPASS at collection time — the wave that flips it MUST also remove
the decorator. This prevents accidental "fixed but still marked xfail" drift.

Phase 6 stub names are LOCKED verbatim by Plan 06-00 <test_inventory>; downstream
waves rename only via documented Rule-1 deviations in their SUMMARY.md.
"""

from __future__ import annotations

import json  # noqa: F401  (reserved for Wave 4+ CLI tests + Wave 5 fixtures)
import re  # noqa: F401  (reserved for Wave 6 doc-section regex assertions)
import subprocess  # noqa: F401  (reserved for Wave 4 CLI subprocess tests)
import sys  # noqa: F401  (reserved for Wave 4 sys.executable in subprocess invocations)
from decimal import Decimal  # noqa: F401  (reserved for Wave 1 sign-validator + Wave 5 NPV asserts)
from pathlib import Path
from typing import TYPE_CHECKING, Any  # noqa: F401  (Any reserved for fixture loaders in flips)

import pytest

if TYPE_CHECKING:
    from collections.abc import (
        Callable,  # noqa: F401  (reserved for refinance_fixture type hints in flips)
    )

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "refi_npv.py"
"""Phase 6 CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""

REFINANCE_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "refinance.py"
"""For lazy-import test (D-18 inherited): assert lib.refinance is NOT imported by --help."""

REFI_NPV_DOC_PATH: Path = Path(__file__).resolve().parent.parent / "references" / "refi-npv.md"
"""For SC-5 doc-presence + sign-convention-phrase tests (Wave 6 / Plan 06-06)."""


# =========================================================================
# REFI-01 (rate-and-term NPV) — 3 stubs, flipped Wave 5 (Plan 06-05)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-05 rate-and-term positive-NPV fixture (SC-1)"
)
def test_refi_rate_and_term_positive_npv() -> None:
    """SC-1 anchor: rate-and-term refi at 200bps drop + $2k closing → NPV > 0 (Oracle 1)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 06-05 rate-and-term negative-NPV fixture (SC-1, D-13 horizon=12)",
)
def test_refi_rate_and_term_negative_npv() -> None:
    """SC-1 anchor: same rate drop + $5k closing + analysis_horizon_months=12 → NPV < 0 (Oracle 2)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-05 Decimal exact NPV equality (D-04 sign rigor)"
)
def test_refi_npv_decimal_exact() -> None:
    """D-04: NPV asserted with strict Decimal equality (no assertAlmostEqual; CLAUDE.md money discipline)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# REFI-02 (cash-out) — 3 stubs, flipped Wave 5 (Plan 06-05)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-05 cash-out cash_proceeds field (SC-3)"
)
def test_refi_cash_out_proceeds() -> None:
    """SC-3 anchor: cash_proceeds surfaced as labeled top-level JSON field (Oracle 3)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-05 cash-out new_monthly_pi field (SC-3)"
)
def test_refi_cash_out_new_monthly_pi() -> None:
    """SC-3 anchor: new_monthly_pi surfaced as labeled top-level JSON field (Oracle 3)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-05 cash-out total_interest_delta field (SC-3)"
)
def test_refi_cash_out_total_interest_delta() -> None:
    """SC-3 anchor: total_interest_delta surfaced as labeled top-level JSON field (Oracle 3)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# REFI-03 (breakeven dual reporting) — 3 stubs, flipped Wave 5 (Plan 06-05)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 06-05 simple_breakeven labeled (SC-2)")
def test_refi_breakeven_simple_labeled() -> None:
    """SC-2 anchor: simple_breakeven_months + simple_breakeven_status labeled in output JSON."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 06-05 npv_breakeven labeled (SC-2)")
def test_refi_breakeven_npv_labeled() -> None:
    """SC-2 anchor: npv_breakeven_months + npv_breakeven_status labeled in output JSON (D-06 cumulative scan)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 06-05 breakeven divergence fixture (SC-2 divergence ≥1 month)",
)
def test_refi_breakeven_divergence_documented() -> None:
    """SC-2 anchor: breakeven_divergence.json exercises high-discount-rate divergence (simple ≠ NPV by ≥1 month)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# REFI-04 (pyxirr deferral) — 1 stub, flipped Wave 6 (Plan 06-05/06-06 docstring assertion)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-05 pyxirr deferred to Phase 11 SUBA-02 (D-07)"
)
def test_pyxirr_deferred_to_phase11_documented() -> None:
    """D-07: lib/refinance.py docstring cites Phase 11 + pyxirr deferral (REFI-04 OPTIONAL closure)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# REFI-08 (CLI scripts/refi_npv.py) — 6 stubs, flipped Wave 4 (Plan 06-04)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 06-04 CLI subprocess round-trip smoke")
def test_cli_smoke_subprocess_round_trip() -> None:
    """REFI-08: scripts/refi_npv.py JSON-in/JSON-out round-trip via subprocess (no direct import)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-04 D-18 fast-help / lazy-import discipline"
)
def test_cli_help_does_not_import_lib_refinance() -> None:
    """D-18: scripts/refi_npv.py --help does NOT import lib.refinance (lazy import after argparse)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-04 D-19/WR-02 reject float closing_costs"
)
def test_cli_rejects_float_closing_costs() -> None:
    """D-19/WR-02: CLI rejects JSON float closing_costs with 6-key envelope on stderr."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-04 D-19/WR-02 reject float discount_rate_annual"
)
def test_cli_rejects_float_discount_rate() -> None:
    """D-19/WR-02: CLI rejects JSON float discount_rate_annual with 6-key envelope on stderr."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-04 D-19/WR-02 envelope shape uniformity"
)
def test_cli_error_envelope_uniformity() -> None:
    """D-19/WR-02: CLI error envelope contains the 6 mandated keys (loc/msg/type/input/url/ctx)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-04 SC-5 mandate --help cites references/refi-npv.md"
)
def test_cli_help_cites_references_refi_npv() -> None:
    """SC-5 verbatim: scripts/refi_npv.py --help epilog includes 'see references/refi-npv.md'."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# REFI-09 (references/refi-npv.md) — 3 stubs
# - 2 flipped Wave 6 (Plan 06-06: doc body)
# - 1 flipped Wave 2 (Plan 06-01: lib/refinance.py module docstring cite)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-06 references/refi-npv.md sections present (SC-5)"
)
def test_refi_npv_doc_sections_present() -> None:
    """SC-5: references/refi-npv.md ships ≥250 lines with required sections (sign convention, formula, breakeven, after-tax)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-06 verbatim sign-convention phrase (SC-5)"
)
def test_refi_npv_doc_sign_convention_phrase() -> None:
    """SC-5 verbatim: doc contains literal 'outflows negative, savings positive'."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 06-01 lib/refinance.py module docstring cites references/refi-npv.md (D-16)",
)
def test_lib_refinance_module_docstring_cites() -> None:
    """D-16: lib/refinance.py module docstring cites references/refi-npv.md (belt-and-suspenders sign-convention surface)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# SC-4 sign-validator (model-layer) — 4 stubs, flipped Wave 1 (Plan 06-01)
# =========================================================================


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 06-01 RefiCashflow rejects outflow with positive amount (SC-4)",
)
def test_refi_cashflow_outflow_positive_rejected() -> None:
    """SC-4 verbatim: RefiCashflow(direction='outflow', amount=positive) raises ValidationError."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 06-01 RefiCashflow rejects inflow with negative amount (SC-4)",
)
def test_refi_cashflow_inflow_negative_rejected() -> None:
    """SC-4 verbatim: RefiCashflow(direction='inflow', amount=negative) raises ValidationError."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 06-01 RefiCashflow accepts amount=0 in either direction (D-14)",
)
def test_refi_cashflow_zero_accepted_either_dir() -> None:
    """D-14: RefiCashflow(direction='outflow' or 'inflow', amount=Decimal('0.00')) is valid (no sign hazard)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-01 RefiCashflow accepts correctly-signed cashflows"
)
def test_refi_cashflow_correctly_signed_passes() -> None:
    """SC-4 happy path: outflow + negative amount + inflow + positive amount construct cleanly."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# Cross-cutting — 2 stubs
# - test_refi_cashflow_kind_citation_coverage flipped Wave 5 (Plan 06-05) — every Literal kind appears in ≥1 fixture
# - test_after_tax_mode_validator_requires_all flipped Wave 3 (Plan 06-03) — D-09 cross-field validator
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-05 RefiCashflow kind Literal coverage (D-03)"
)
def test_refi_cashflow_kind_citation_coverage() -> None:
    """D-03: every value of RefiCashflow.kind Literal appears in ≥1 committed fixture (mirrors Phase 5 applied_cap)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 06-03 after-tax mode cross-field validator (D-09)"
)
def test_after_tax_mode_validator_requires_all() -> None:
    """D-09: when after_tax_mode=True, both marginal_tax_rate AND filing_status are required (else ValidationError)."""
    pytest.fail("Wave 0 stub")
