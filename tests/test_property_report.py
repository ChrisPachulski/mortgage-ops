"""Phase 15 Plan 15-01 Wave 0 RED stubs for lib.property_report.render().

Covers RPRT-01 (matrix + 6-section layout) and RPRT-02 (per-section citation
footer). Every test function carries a docstring naming the requirement +
decision IDs. Tests fail RED until Plan 15-02 ships lib/property_report.py.

The module-level `pytestmark` xfails the whole file when lib.property_report
is unimportable, so pytest collection succeeds. Plan 15-02 SHIPS render() and
this entire file flips GREEN.

Per CLAUDE.md money discipline: every Decimal in this file is constructed
from a string literal; no floats touch any expression.

Fixture lineage:
- `sample_report` loads tests/fixtures/property_analysis/sfh_conforming_king_county.json
  (the canonical Phase 14 AnalysisReport-anchor fixture; NOT the eval fixture).
- `sample_report_with_negative_refi` mutates the AnalysisReport via model_copy
  to inject a synthetic RefiRow with negative monthly_savings / npv_60mo for
  Pitfall 4 (-$X,XXX vs $-X,XXX format) coverage.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from lib.household import Household
from lib.profile import Profile
from lib.property_analysis import AnalysisReport, RefiRow, analyze
from lib.property_listing import PropertyListing

# ---------------------------------------------------------------------------
# Wave 0 RED guard — lib.property_report shipped by Plan 15-02; the xfail
# branch and the `# type: ignore[import-not-found]` comment were removed once
# the module landed (mypy's warn_unused_ignores flagged the now-resolved
# ignore on first GREEN run, per Plan 15-01 SUMMARY's self-removing-hygiene
# anticipation).
# ---------------------------------------------------------------------------
from lib.property_report import render

HAS_RENDER = True

# ---------------------------------------------------------------------------
# Canonical Phase 14 fixture (NOT the eval fixture; per PATTERNS.md L607-619).
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "property_analysis"

DEFAULT_ARGV: list[str] = [
    "--listing",
    "data/property-listings/1-2026-05-20.json",
    "--household",
    "config/household.yml",
    "--profile",
    "config/profile.yml",
    "--output-dir",
    "reports/",
]
"""D-15-CITATION-03 canonical re-runnable argv; used by every test that
calls render() so footer assertions can grep for the resolved invocation."""


def _load_analysis_report() -> AnalysisReport:
    """Load tests/fixtures/property_analysis/sfh_conforming_king_county.json,
    construct PropertyListing + Household + Profile, and call analyze() with
    fred_mortgage_*us kwargs from the fixture's fred_rates block."""
    raw = json.loads((FIXTURES / "sfh_conforming_king_county.json").read_text())
    # Use model_validate_json (JSON mode) so Pydantic coerces fixture strings
    # into Decimal / datetime per the strict-mode field validators (mirrors
    # tests/test_property_analysis.py L1264-1266 pattern). model_validate
    # (dict mode) under strict=True rejects str-for-Decimal inputs.
    listing = PropertyListing.model_validate_json(json.dumps(raw["listing"]))
    household = Household.model_validate_json(json.dumps(raw["household"]))
    profile = Profile.model_validate_json(json.dumps(raw["profile"]))
    return analyze(
        listing,
        household,
        profile,
        fred_mortgage_30us=Decimal(raw["fred_rates"]["MORTGAGE30US"]),
        fred_mortgage_15us=Decimal(raw["fred_rates"]["MORTGAGE15US"]),
    )


@pytest.fixture
def sample_report() -> AnalysisReport:
    """RPRT-01 / RPRT-02: canonical AnalysisReport from the Phase 14 fixture.

    Returned report drives every render() invocation in this module. The
    underlying fixture pins Conv30 + Conv15 + FHA30 at 6 DP tiers (18 cells),
    GO-ALL-GREEN verdict, no warnings — i.e., the happy path the formatter
    must handle correctly before edge cases (negative refi, ineligible cells,
    over-cap tax) are layered on.
    """
    return _load_analysis_report()


@pytest.fixture
def sample_report_with_negative_refi() -> AnalysisReport:
    """Pitfall 4: AnalysisReport variant with a NEGATIVE monthly_savings refi row.

    AnalysisReport is frozen (model_config frozen=True, extra=forbid) — we
    use Pydantic model_copy(update=...) to swap in a synthetic RefiBlock whose
    first row's monthly_savings + npv_60mo are negative. Drives the
    `-$X,XXX.XX` vs `$-X,XXX.XX` regression assertion.
    """
    base = _load_analysis_report()
    # Build a synthetic negative refi row with the SAME contract as Phase 14.
    negative_row = RefiRow(
        program="Conv30",
        target_rate=Decimal("0.065000"),
        scenario_label="minus_100bps",
        monthly_savings=Decimal("-250.00"),
        breakeven_months=None,
        npv_60mo=Decimal("-5000.00"),
    )
    new_refi = base.refi.model_copy(update={"rows": [negative_row]})
    return base.model_copy(update={"refi": new_refi})


# ---------------------------------------------------------------------------
# RPRT-01 — six-section layout + matrix shape + preferred-DP highlight
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "section",
    [
        "## YOUR FIT",
        "## RATE STRESS",
        "## POINTS BREAKEVEN",
        "## REFI OPPORTUNITY",
        "## TAX",
        "## VERDICT",
    ],
)
def test_render_emits_six_sections(sample_report: AnalysisReport, section: str) -> None:
    """RPRT-01 + D-15-MATRIX-01..04 + D-15-CITATION-01: every one of the 6
    section headings (YOUR FIT, RATE STRESS, POINTS BREAKEVEN, REFI
    OPPORTUNITY, TAX, VERDICT) appears in the rendered markdown body."""
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    assert section in md, f"missing section heading {section!r} in render output"


def test_matrix_renders_all_cells(sample_report: AnalysisReport) -> None:
    """RPRT-01 + D-15-MATRIX-03: every cell (eligible AND ineligible)
    appears in the YOUR FIT section. We count occurrences of '/mo' inside
    YOUR FIT as a cell-count proxy (each cell renders '$X,XXX/mo')."""
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    your_fit = md.split("## YOUR FIT", 1)[1].split("## RATE STRESS", 1)[0]
    expected_cells = len(sample_report.matrix.cells)
    assert your_fit.count("/mo") >= expected_cells, (
        f"YOUR FIT section emitted {your_fit.count('/mo')} '/mo' tokens; "
        f"expected ≥ {expected_cells} (one per cell incl. ineligible per D-15-MATRIX-03)"
    )


def test_cell_eligibility_marks(sample_report: AnalysisReport) -> None:
    """RPRT-01 + D-15-MATRIX-02: eligible cells render '✓'; ineligible
    render '✗' + blocker code. Count '✓' inside YOUR FIT must equal the
    number of eligible cells in the matrix."""
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    your_fit = md.split("## YOUR FIT", 1)[1].split("## RATE STRESS", 1)[0]
    eligible_count = sum(1 for c in sample_report.matrix.cells if c.eligible)
    assert your_fit.count("✓") == eligible_count, (
        f"YOUR FIT shows {your_fit.count('✓')} '✓' marks; "
        f"expected exactly {eligible_count} (one per eligible cell per D-15-MATRIX-02)"
    )


def test_preferred_dp_column_bolded(sample_report: AnalysisReport) -> None:
    """RPRT-01 + D-15-MATRIX-04: the column matching
    household.preferred_down_payment_pct is annotated with '*(your DP)*'
    so the user's eye anchors there first."""
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    your_fit = md.split("## YOUR FIT", 1)[1].split("## RATE STRESS", 1)[0]
    assert "*(your DP)*" in your_fit, (
        "YOUR FIT section missing '*(your DP)*' annotation on preferred-DP "
        "column header (D-15-MATRIX-04)"
    )


def test_blocker_code_truncation(sample_report: AnalysisReport) -> None:
    """RPRT-01 + D-15-MATRIX-02 + RESEARCH L720: ineligible cell renders the
    first blocker code stripped of any parenthetical suffix or colon-suffix.
    We exercise this by mutating one cell to be ineligible with a verbose
    blocker reason; the rendered string must not contain the parenthetical
    or colon-suffix text."""
    # Always inject a synthetic blocker with a verbose suffix so we can assert
    # truncation; the fixture's own ineligible cells (LTV-CEILING-FHA) don't
    # exercise the ":" or "(" truncation paths.
    cells = list(sample_report.matrix.cells)
    mutated = cells[0].model_copy(
        update={
            "eligible": False,
            "blocker_reasons": ["DTI-CONV-CEILING (back-end > 0.45): see Conv guide"],
        }
    )
    cells[0] = mutated
    new_matrix = sample_report.matrix.model_copy(update={"cells": cells})
    report = sample_report.model_copy(update={"matrix": new_matrix})
    md = render(report, orchestrator_argv=DEFAULT_ARGV)
    your_fit = md.split("## YOUR FIT", 1)[1].split("## RATE STRESS", 1)[0]
    # The bare code (before "(" or ":") must appear; the parenthetical must NOT.
    assert "DTI-CONV-CEILING" in your_fit
    assert "(back-end > 0.45)" not in your_fit, (
        "Blocker code parenthetical suffix leaked into YOUR FIT — "
        "D-15-MATRIX-02 + RESEARCH L720 require truncation."
    )


def test_arm_reset_row_under_conv30(sample_report: AnalysisReport) -> None:
    """RPRT-01 + Pitfall 5: RATE STRESS section orders stress.rows by
    (program, stress_kind) and arm_reset rows appear ONLY for Conv30 (the
    only program that ships a 5/1 ARM in Phase 14). If the fixture has no
    arm_reset rows, the test asserts the section renders without crashing."""
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    rate_stress = md.split("## RATE STRESS", 1)[1].split("## POINTS BREAKEVEN", 1)[0]
    rate_stress_lower = rate_stress.lower().replace("_", " ")
    arm_rows = [r for r in sample_report.stress.rows if r.stress_kind == "arm_reset"]
    if arm_rows:
        # Every arm_reset row must be associated with Conv30 per Pitfall 5.
        for row in arm_rows:
            assert row.program == "Conv30", (
                f"arm_reset row found for program {row.program}; Pitfall 5 "
                f"requires arm_reset rows under Conv30 only"
            )
        # And the rendered markdown should mention arm_reset (case-insensitive,
        # underscores normalized to spaces so 'arm_reset' and 'arm reset' both match).
        assert "arm reset" in rate_stress_lower
    else:
        # No arm_reset rows in fixture; section still renders content.
        assert len(rate_stress.strip()) > 0, "RATE STRESS section rendered empty"


def test_tax_over_cap_see_cpa_callout(sample_report: AnalysisReport) -> None:
    """RPRT-01 + Assumption A8: when tax.over_750k_cap_per_program[program]
    is True, TAX section shows a 'see CPA' callout (non-numeric — calc-engine
    separation per CLAUDE.md). When False for every program, no such callout
    appears. We exercise both branches by mutating the tax block."""
    # Branch 1: no program over cap (fixture default).
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    tax_lower = md.split("## TAX", 1)[1].split("## VERDICT", 1)[0].lower()
    # In the all-False branch, no CPA callout (case-insensitive match).
    if not any(sample_report.tax.over_750k_cap_per_program.values()):
        assert "see cpa" not in tax_lower, (
            "TAX section emitted 'see CPA' callout even though no program "
            "exceeds the $750k IRS Pub 936 cap (A8 violation)"
        )

    # Branch 2: force one program over cap, re-render, assert callout appears.
    over_cap_dict = dict(sample_report.tax.over_750k_cap_per_program)
    first_program = next(iter(over_cap_dict))
    over_cap_dict[first_program] = True
    new_tax = sample_report.tax.model_copy(update={"over_750k_cap_per_program": over_cap_dict})
    over_cap_report = sample_report.model_copy(update={"tax": new_tax})
    md_over = render(over_cap_report, orchestrator_argv=DEFAULT_ARGV)
    tax_over_lower = md_over.split("## TAX", 1)[1].split("## VERDICT", 1)[0].lower()
    assert "see cpa" in tax_over_lower, (
        "TAX section missing 'see CPA' callout for program over $750k cap (A8)"
    )


# ---------------------------------------------------------------------------
# RPRT-02 — per-section citation footer (D-15-CITATION-01..03)
# ---------------------------------------------------------------------------


def test_six_citation_footers(sample_report: AnalysisReport) -> None:
    """RPRT-02 + D-15-CITATION-01: exactly 6 citation footers (one per
    section). Per PATTERNS.md L558 the footer prefix is
    '*Computed by: python .claude/skills/mortgage-ops/scripts/property_analyze.py'
    (full skill-relative invocation per RESEARCH OQ2 RESOLVED)."""
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    footer_prefix = "*Computed by: python .claude/skills/mortgage-ops/scripts/property_analyze.py"
    assert md.count(footer_prefix) == 6, (
        f"Expected exactly 6 citation footers; found {md.count(footer_prefix)} "
        f"(D-15-CITATION-01 + RESEARCH OQ2 RESOLVED)"
    )


def test_footer_is_full_invocation(sample_report: AnalysisReport) -> None:
    """RPRT-02 + D-15-CITATION-03: each footer carries the FULL re-runnable
    invocation including all flag values. We assert the resolved
    '--listing data/property-listings/1-2026-05-20.json' string appears
    in the rendered output."""
    md = render(sample_report, orchestrator_argv=DEFAULT_ARGV)
    assert "--listing data/property-listings/1-2026-05-20.json" in md, (
        "Footer missing the resolved --listing path; D-15-CITATION-03 "
        "requires full re-runnable copy-paste invocation."
    )


# ---------------------------------------------------------------------------
# Pitfall 4 — signed-money format in REFI OPPORTUNITY (-$X,XXX not $-X,XXX)
# ---------------------------------------------------------------------------


def test_signed_money_negative_format(
    sample_report_with_negative_refi: AnalysisReport,
) -> None:
    """RPRT-01 + Pitfall 4: negative monthly_savings / npv_60mo render as
    '-$250.00' not '$-250.00'. Scoped to REFI OPPORTUNITY where Phase 14
    documents these fields CAN be negative."""
    md = render(sample_report_with_negative_refi, orchestrator_argv=DEFAULT_ARGV)
    refi = md.split("## REFI OPPORTUNITY", 1)[1].split("## TAX", 1)[0]
    assert "$-" not in refi, (
        "REFI OPPORTUNITY section emitted '$-' (incorrect signed-money "
        "format). Pitfall 4 requires '-$X,XXX.XX' form."
    )
