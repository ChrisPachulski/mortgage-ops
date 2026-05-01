"""Phase 5 ARM Modeling — full test surface (ARM-01..09 + cross-cutting).

Per Phase 3 D-17 portability + Phase 4 D-13 inheritance: subprocess
invocation only for CLI tests, never `import scripts.arm_simulate`
directly. SCRIPT_PATH is the single constant edited at Phase 10 when
scripts/ relocates to .claude/skills/mortgage-ops/scripts/.

Wave 0 (Plan 05-00) creates ALL 32 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 2 (Plan 05-02 Pydantic models): ARM-01 (3 tests)
- Wave 3 (Plan 05-03 build_arm_schedule): ARM-02..05 (13 tests)
- Wave 4 (Plan 05-04 CLI + helper factor): ARM-08 (8 tests)
- Wave 5 (Plan 05-05 references doc): ARM-09 (3 tests)
- Wave 6 (Plan 05-06 fixtures + oracle): ARM-06, ARM-07, plus cross-cutting (5 tests)

Each xfail decorator carries `strict=True` so a passing test in xfail state
raises XPASS at collection time — the wave that flips it MUST also remove
the decorator. This prevents accidental "fixed but still marked xfail" drift.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "arm_simulate.py"
"""Phase 5 CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""

ARM_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "arm.py"
"""For lazy-import test (D-18 inherited): assert lib.arm is NOT imported by --help."""


# =========================================================================
# ARM-01 (3 stubs) — flipped in Wave 2 (Plan 05-02)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 implements ARMTerms")
def test_arm_terms_field_set() -> None:
    """ARM-01 + ROADMAP SC-1: ARMTerms has 8 explicit fields + REQUIRED floor_rate + optional note_rate."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 implements ARMTerms")
def test_arm_terms_missing_floor_rate_raises() -> None:
    """ARM-01 + D-02: ARMTerms rejects missing floor_rate at construction (no default)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-03 implements engine note_rate fallback"
)
def test_note_rate_defaults_to_loan_annual_rate() -> None:
    """ARM-01 + D-02: note_rate=None means engine substitutes loan.annual_rate for lifetime base."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-02 (4 stubs) — flipped in Wave 6 (fixtures land)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_1_payment_jump_at_61.json"
)
def test_arm_5_1_payment_jump_at_61(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02 + ROADMAP SC-2: 5/1 ARM produces payment-jump at month 61 (not 60, not 62)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_7_1_payment_jump_at_85.json"
)
def test_arm_7_1_payment_jump_at_85(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02: 7/1 ARM (initial=84, reset=12)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_10_1_payment_jump_at_121.json"
)
def test_arm_10_1_payment_jump_at_121(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02: 10/1 ARM (initial=120, reset=12)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_6_payment_jump_at_61_and_67.json"
)
def test_arm_5_6_payment_jump_at_61_and_67(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-02 + D-15: 5/6 ARM (initial=60, reset=6) — first reset 61, second 67."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-03 (3 stubs) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-03 + 05-06 implement reset formula")
def test_reset_formula_locked() -> None:
    """ARM-03 + D-02: clamp(quantize(index+margin), low=floor, high=min(periodic_ceil, lifetime_ceil))."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_initial_cap_at_first_reset.json"
)
def test_arm_initial_cap_at_first_reset(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-03 + D-02: First-reset uses initial_cap; subsequent uses periodic_cap."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_lifetime_cap_binds.json")
def test_arm_lifetime_cap_binds(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-03: Lifetime cap binds when fully-indexed > note_rate + lifetime_cap."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-04 (1 stub) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_floor_below_margin_blocked.json"
)
def test_arm_floor_below_margin_blocked(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-04 + ROADMAP SC-4: Floor enforcement: new_rate >= max(margin, floor_rate)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-05 (5 stubs) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-03 + 05-06 implement re-amortization")
def test_full_remaining_term_re_amortization(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-05 + D-05: Re-amortization over FULL remaining term (not just reset window)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_continuous_period_numbering.json"
)
def test_arm_continuous_period_numbering(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-05 + D-03: Continuous period numbering 1..N; final balance == 0.00."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-03 implements cumulative-totals stitch"
)
def test_cumulative_totals_continuous_across_resets(
    arm_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ARM-05 + D-05 step 2.4: cumulative_interest + cumulative_principal continuous across epoch boundaries."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-03 + 05-06 lock the slice-stitch invariant"
)
def test_non_final_epoch_does_not_zero_balance(
    arm_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ARM-05 + RESEARCH Q1.2 bear trap: non-final epoch's last sliced row has balance > 0.00."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 reuses Phase 1 oracle anchor")
def test_initial_fixed_period_matches_phase1_oracle(
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ARM-05 + LM-6: First epoch matches Phase 1 oracle ($400k @ 6.5%/30yr → $2528.27 P&I)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-06 (2 stubs) — flipped in Wave 6 (oracle PDF + JSON ship)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships bankrate + vertex42 5/1 captures"
)
def test_oracle_cross_validation_5_1(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-06 + D-04 [REVISED]: Hand-calc + Bankrate + Vertex42 captures AGREE EXACTLY (5/1)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships AmericU 5/6 disclosure capture"
)
def test_oracle_cross_validation_5_6(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-06 + D-04 [REVISED]: 5/6 ARM oracle — AmericU disclosure cross-validation."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-07 (1 stub) — flipped in Wave 6
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_5_1_off_by_one_negative.json"
)
def test_arm_5_1_off_by_one_negative(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ARM-07 + ROADMAP SC-3: month 59 still old AND month 61 already new."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-08 (8 stubs) — flipped in Wave 4 (CLI ships)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships scripts/arm_simulate.py")
def test_cli_smoke_subprocess_round_trip(
    arm_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """ARM-08: CLI subprocess round-trip — write JSON, invoke, parse stdout."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-04 ships lazy-import in scripts/arm_simulate.py"
)
def test_cli_help_does_not_import_lib_arm() -> None:
    """ARM-08 + D-18: --help fast (no lib.arm or numpy_financial import before argparse)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate in scripts/arm_simulate.py"
)
def test_cli_rejects_float_principal(tmp_path: Path) -> None:
    """ARM-08 + D-19/WR-02: CLI rejects JSON-float in loan.principal with 6-key envelope."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate")
def test_cli_rejects_float_assumed_index_rate(tmp_path: Path) -> None:
    """ARM-08 + D-19: CLI rejects JSON-float in assumed_index_rate."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate (deep loc)")
def test_cli_rejects_float_index_path_value(tmp_path: Path) -> None:
    """ARM-08 + D-19: CLI rejects JSON-float in index_path[].value (deep loc through list)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships float-gate")
def test_cli_rejects_float_floor_rate(tmp_path: Path) -> None:
    """ARM-08 + D-19: CLI rejects JSON-float in arm_terms.floor_rate."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-04 ships uniform envelope")
def test_cli_error_envelope_uniformity(tmp_path: Path) -> None:
    """ARM-08 + D-19/WR-02: float-gate + Pydantic ValidationError emit identical 6-key shape."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-02 ships ARMRequest cross-field validator"
)
def test_cli_misaligned_index_path_period_rejected(tmp_path: Path) -> None:
    """ARM-08 + D-01: CLI surfaces ARMRequest._index_path_periods_align_to_reset_triggers as 6-key envelope."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# ARM-09 (3 stubs) — flipped in Wave 5 (references/arm-mechanics.md ships)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-05 ships references/arm-mechanics.md")
def test_arm_mechanics_doc_sections_present() -> None:
    """ARM-09 + D-08: references/arm-mechanics.md exists with all 6 D-08 sections."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-02 + 05-05 add docstring cite")
def test_arm_terms_docstring_cites_arm_mechanics() -> None:
    """ARM-09 + ROADMAP SC-5: ARMTerms docstring cites references/arm-mechanics.md."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-05 ships corrected D-08 citations")
def test_arm_mechanics_citations() -> None:
    """ARM-09 + D-08 [REVISED]: cites B2-1.4-02 + Freddie 6302.7(b) + CFPB §1951 + AmericU 5/6 disclosure."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# Cross-cutting (2 stubs)
# =========================================================================


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub — Plan 05-06 ships fixtures covering all 5 Literal values"
)
def test_applied_cap_citation_coverage() -> None:
    """D-10: every applied_cap Literal value (initial/periodic/lifetime/floor/none) exercised by ≥1 fixture."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 05-06 ships arm_teaser_rate.json")
def test_arm_teaser_rate(arm_fixture: Callable[[str], dict[str, Any]]) -> None:
    """D-02 + LM-3: teaser-rate ARM (loan.annual_rate=0.03, note_rate=0.05); lifetime base = note_rate."""
    pytest.fail("Wave 0 stub")
