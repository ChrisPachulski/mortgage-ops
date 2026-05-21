"""Phase 15 AnalysisReport -> markdown formatter (RPRT-01, RPRT-02).

Pure-transform module. ``render(report, orchestrator_argv)`` consumes a
Pydantic ``AnalysisReport`` (Phase 14 frozen contract) plus the orchestrator's
``sys.argv[1:]`` and returns a one-page markdown body. CLAUDE.md calc-engine
separation: NO I/O, NO math, NO IEEE-754 binary types ever; only Decimal display formatting.

Decision-IDs honored:
  - D-15-MATRIX-01 — YOUR FIT renders Program x DP matrix.
  - D-15-MATRIX-02 — every cell shows ``$X,XXX/mo`` plus ``✓`` or ``✗`` + blocker code.
  - D-15-MATRIX-03 — ineligible cells are INCLUDED (not hidden).
  - D-15-MATRIX-04 — preferred-DP column header bolded + annotated ``*(your DP)*``.
  - D-15-CITATION-01 — exactly 6 italic citation footers, one per section.
  - D-15-CITATION-02 — footer cites the orchestrator-only invocation.
  - D-15-CITATION-03 — footer is full re-runnable invocation (orchestrator argv joined).

Pitfalls mitigated:
  - Pitfall 4 — signed-money formats negatives as ``-$X,XXX.XX`` (NOT ``$-X,XXX.XX``)
    via ``_fmt_signed_money``.
  - Pitfall 5 — RATE STRESS rows sorted by ``(program, _STRESS_KIND_ORDER.index(kind))``
    so arm_reset rows (Conv30-only) land last within Conv30 grouping.
  - Pitfall 11 — matrix cells use whole-dollar display via ``_fmt_money_whole``
    so a 6-column matrix stays readable; cents precision remains in the
    underlying Decimal storage.

ROADMAP SC-4: header (``# Property Analysis``) + 6 ``## ``-prefixed section headers.

Public surface:
  - ``render(report: AnalysisReport, orchestrator_argv: list[str]) -> str``

Preferred-DP derivation: ``report.stress.preferred_down_payment_pct`` (per the
Phase 14 ``StressBlock`` field that pins which DP the auxiliary blocks were
computed at; AnalysisReport is frozen+extra=forbid so we cannot add a top-level
field, and the StressBlock already exposes the value we need).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from lib.property_analysis import (
        AnalysisReport,
        DownPaymentMatrix,
        PointsBlock,
        ProgramResult,
        RefiBlock,
        StressBlock,
        TaxBlock,
        Verdict,
    )
    from lib.property_listing import PropertyListing

# ---------------------------------------------------------------------------
# Constants (Pitfall 5 ordering; D-15-CITATION-01..03 prefix; SC-4 section list)
# ---------------------------------------------------------------------------

_STRESS_KIND_ORDER: Final[tuple[str, str, str]] = (
    "rate_shock",
    "income_shock",
    "arm_reset",
)
"""Pitfall 5: stable per-program sort key for RATE STRESS rows."""

_FOOTER_PREFIX: Final[str] = (
    "*Computed by: python .claude/skills/mortgage-ops/scripts/property_analyze.py"
)
"""D-15-CITATION-01..03 + RESEARCH OQ2 RESOLVED: full skill-relative invocation
prefix. Footer is closed with a trailing ``*`` (italic close) per markdown."""

_SECTION_HEADERS: Final[tuple[str, str, str, str, str, str]] = (
    "## YOUR FIT",
    "## RATE STRESS",
    "## POINTS BREAKEVEN",
    "## REFI OPPORTUNITY",
    "## TAX",
    "## VERDICT",
)
"""ROADMAP SC-4: six top-level section headers in fixed order."""

_SCENARIO_LABEL_PRIORITY: Final[dict[str, int]] = {
    "minus_100bps": 0,
    "fred_times_0_85": 1,
}
"""Stable refi-scenario sort key so the ``-100 bps`` row precedes
``FRED x 0.85`` within each program grouping."""


# ---------------------------------------------------------------------------
# Display formatters (Decimal-only; CLAUDE.md money discipline — Decimal-strict)
# ---------------------------------------------------------------------------


def _fmt_money(d: Decimal) -> str:
    """Two-decimal money: ``$X,XXX.XX``. Decimal direct, no binary-fp coercion."""
    return f"${d:,.2f}"


def _fmt_money_whole(d: Decimal) -> str:
    """Whole-dollar money for matrix cell display (Pitfall 11): ``$X,XXX``."""
    return f"${d:,.0f}"


def _fmt_signed_money(d: Decimal) -> str:
    """Signed money: ``-$X,XXX.XX`` for negatives (NOT ``$-X,XXX.XX``).

    Pitfall 4 — negative refi monthly_savings / npv_60mo MUST display with the
    minus sign OUTSIDE the dollar sign. Zero renders unsigned.
    """
    if d < 0:
        return f"-${abs(d):,.2f}"
    return f"${d:,.2f}"


def _fmt_pct(d: Decimal) -> str:
    """Percent with one decimal: ``20.0%``."""
    return f"{d:.1%}"


def _fmt_rate(d: Decimal) -> str:
    """Rate with three decimals: ``6.500%``."""
    return f"{d:.3%}"


def _fmt_dp_header(d: Decimal) -> str:
    """DP column header: ``3% DP`` (whole percent — DP ladder is 3/5/10/15/20/25)."""
    return f"{d:.0%} DP"


# ---------------------------------------------------------------------------
# Citation footer (D-15-CITATION-01..03)
# ---------------------------------------------------------------------------


def _render_footer(argv: list[str]) -> str:
    """Render the single-line italic citation footer.

    D-15-CITATION-03: emits the FULL re-runnable invocation by joining
    ``orchestrator_argv`` with spaces after the skill-relative prefix.
    """
    if argv:
        return f"{_FOOTER_PREFIX} {' '.join(argv)}*"
    return f"{_FOOTER_PREFIX}*"


# ---------------------------------------------------------------------------
# Header (no citation footer — per D-15-CITATION-01 footers are post-section only)
# ---------------------------------------------------------------------------


def _render_header(report: AnalysisReport) -> str:
    """Render the report header: title + property/household snapshot table.

    PropertyListing has no ``address`` field (Phase 13 D-13-MUSTHAVE-01), so
    the title uses the ``ZPID {zpid}`` fallback path documented in the Plan.
    """
    listing: PropertyListing = report.listing_snapshot

    title = f"# Property Analysis: ZPID {listing.zpid}"

    # Tax / insurance / HOA monthly: divide the annual values by 12 (Decimal).
    # ProvenancedMoney.value may be None — fall back to Decimal("0.00") so the
    # header still renders. Append ``*(estimated)*`` when provenance is
    # ``estimated`` OR the wrapper is absent entirely.
    def _monthly_from_annual(
        pm_value: Decimal | None,
        provenance: str | None,
        annualized: bool,
    ) -> str:
        if pm_value is None:
            return "—"
        monthly = (pm_value / Decimal("12")) if annualized else pm_value
        rendered = _fmt_money(monthly)
        if provenance == "estimated":
            rendered = f"{rendered} *(estimated)*"
        return rendered

    tax_pm = listing.tax_annual
    ins_pm = listing.insurance_estimate_annual
    hoa_pm = listing.hoa_monthly
    zest_pm = listing.zestimate

    tax_disp = _monthly_from_annual(
        tax_pm.value if tax_pm is not None else None,
        tax_pm.provenance if tax_pm is not None else None,
        annualized=True,
    )
    ins_disp = _monthly_from_annual(
        ins_pm.value if ins_pm is not None else None,
        ins_pm.provenance if ins_pm is not None else None,
        annualized=True,
    )
    hoa_disp = _monthly_from_annual(
        hoa_pm.value if hoa_pm is not None else None,
        hoa_pm.provenance if hoa_pm is not None else None,
        annualized=False,
    )

    # Zestimate + delta% display.
    zest_disp = "—"
    if zest_pm is not None and zest_pm.value is not None:
        zest_value = zest_pm.value
        delta_disp = ""
        if listing.price != 0:
            delta = (zest_value - listing.price) / listing.price
            delta_disp = f" ({_fmt_pct(delta)} vs list)"
        zest_disp = f"{_fmt_money(zest_value)}{delta_disp}"
        if zest_pm.provenance == "estimated":
            zest_disp = f"{zest_disp} *(estimated)*"

    rows = [
        f"| Listed price | {_fmt_money(listing.price)} |",
        f"| Zestimate | {zest_disp} |",
        f"| Tax (monthly) | {tax_disp} |",
        f"| Insurance (monthly) | {ins_disp} |",
        f"| HOA (monthly) | {hoa_disp} |",
        f"| ZIP | {listing.zip} |",
        (
            f"| FRED 30yr / 15yr | {_fmt_rate(report.fred_mortgage_30us)} / "
            f"{_fmt_rate(report.fred_mortgage_15us)} |"
        ),
        f"| Household snapshot | `{report.household_snapshot_hash[:8]}` |",
        f"| Fetched at | {report.fetched_at.isoformat()} |",
    ]

    table = "| Field | Value |\n|---|---|\n" + "\n".join(rows)
    return f"{title}\n\n{table}"


# ---------------------------------------------------------------------------
# YOUR FIT — Program x DP matrix (D-15-MATRIX-01..04)
# ---------------------------------------------------------------------------


def _truncate_blocker_code(reason: str) -> str:
    """Strip ``:``-suffix and ``(``-suffix from a blocker reason string.

    Per RESEARCH L720 + D-15-MATRIX-02: ineligible cells display only the
    leading blocker code (e.g., ``DTI-CEILING-CONV``) without the verbose
    parenthetical or value suffix.
    """
    head = reason.split(":")[0].split("(")[0].strip()
    return head if head else "BLOCKED"


def _render_your_fit(
    matrix: DownPaymentMatrix,
    _listing: PropertyListing,
    preferred_dp: Decimal,
) -> str:
    """Render the YOUR FIT section: Program x DP matrix with eligibility marks.

    Each cell renders as ``$X,XXX/mo ✓`` (eligible) or
    ``$X,XXX/mo ✗ (BLOCKER_CODE)`` (ineligible — D-15-MATRIX-02). Preferred-DP
    column is bolded (header + every data cell) per D-15-MATRIX-04.
    """
    section_header = "## YOUR FIT (Program x Down Payment)"

    # Build {(program, dp_pct): ProgramResult} for O(1) cell lookup.
    # Typed as ``tuple[str, Decimal]`` (not Literal[...]) so the runtime
    # lookup key from ``matrix.programs_present`` (a ``list[str]``) is
    # type-compatible with the dict key under mypy --strict.
    cell_map: dict[tuple[str, Decimal], ProgramResult] = {
        (c.program, c.down_payment_pct): c for c in matrix.cells
    }

    dp_pcts = list(matrix.down_payment_pcts)
    programs = list(matrix.programs_present)

    # Header row: bold the preferred-DP column + annotate it.
    header_cells = ["Program"]
    for dp in dp_pcts:
        label = _fmt_dp_header(dp)
        if dp == preferred_dp:
            header_cells.append(f"**{label}** *(your DP)*")
        else:
            header_cells.append(label)
    header_row = "| " + " | ".join(header_cells) + " |"
    separator_row = "|" + "|".join(["---"] * (len(dp_pcts) + 1)) + "|"

    # Data rows: one per program; render each cell using the truncation rules.
    data_rows: list[str] = []
    for program in programs:
        row_cells = [program]
        for dp in dp_pcts:
            cell = cell_map.get((program, dp))
            if cell is None:
                row_cells.append("—")
                continue
            piti_disp = f"{_fmt_money_whole(cell.piti)}/mo"
            if cell.eligible:
                txt = f"{piti_disp} ✓"
            else:
                first = cell.blocker_reasons[0] if cell.blocker_reasons else "BLOCKED"
                code = _truncate_blocker_code(first)
                extra = (
                    f" (+{len(cell.blocker_reasons) - 1} more)"
                    if len(cell.blocker_reasons) > 1
                    else ""
                )
                txt = f"{piti_disp} ✗ ({code}{extra})"
            if cell.down_payment_pct == preferred_dp:
                txt = f"**{txt}**"
            row_cells.append(txt)
        data_rows.append("| " + " | ".join(row_cells) + " |")

    table = "\n".join([header_row, separator_row, *data_rows])
    return f"{section_header}\n\n{table}"


# ---------------------------------------------------------------------------
# RATE STRESS (Pitfall 5: program -> stress_kind ordering; D-14-STRESS-03)
# ---------------------------------------------------------------------------


def _stress_label(kind: str) -> str:
    if kind == "rate_shock":
        return "+200bps rate shock"
    if kind == "income_shock":
        return "-30% income shock"
    if kind == "arm_reset":
        return "ARM reset 5/1 @ peak cap"
    return kind


def _render_rate_stress(stress: StressBlock) -> str:
    """Render the RATE STRESS section: program x stress-kind table.

    Rows sorted by (program, _STRESS_KIND_ORDER.index(stress_kind)) so
    rate_shock precedes income_shock precedes arm_reset within each program
    (Pitfall 5). arm_reset rows only appear for Conv30 (D-14-STRESS-03).
    """
    section_header = "## RATE STRESS"

    def _sort_key(row: object) -> tuple[str, int]:
        # row is a StressRow Pydantic instance
        program = row.program  # type: ignore[attr-defined]
        kind = row.stress_kind  # type: ignore[attr-defined]
        idx = (
            _STRESS_KIND_ORDER.index(kind)
            if kind in _STRESS_KIND_ORDER
            else len(_STRESS_KIND_ORDER)
        )
        return (program, idx)

    sorted_rows = sorted(stress.rows, key=_sort_key)

    header_row = (
        "| Program | Stress | Baseline PITI | Stressed PITI | Stressed DTI | Breaches ceiling? |"
    )
    separator_row = "|---|---|---|---|---|---|"

    data_rows: list[str] = []
    for row in sorted_rows:
        baseline = _fmt_money(row.baseline_piti)
        stressed = _fmt_money(row.stressed_piti) if row.stressed_piti is not None else "(n/a)"
        dti = _fmt_pct(row.stressed_dti_back)
        if row.breaches_dti_ceiling:
            first_reason = row.blocker_reasons[0] if row.blocker_reasons else "DTI-CEILING"
            breaches = f"**Yes ({_truncate_blocker_code(first_reason)})**"
        else:
            breaches = "No"
        data_rows.append(
            f"| {row.program} | {_stress_label(row.stress_kind)} | {baseline} | "
            f"{stressed} | {dti} | {breaches} |"
        )

    body = "\n".join([header_row, separator_row, *data_rows]) if data_rows else "_(no stress rows)_"
    return f"{section_header}\n\n{body}"


# ---------------------------------------------------------------------------
# POINTS BREAKEVEN
# ---------------------------------------------------------------------------


def _render_points_breakeven(points: PointsBlock) -> str:
    """Render the POINTS BREAKEVEN section: program x points-purchased table."""
    section_header = "## POINTS BREAKEVEN"

    sorted_rows = sorted(points.rows, key=lambda r: (r.program, r.points_purchased))

    header_row = "| Program | Points | Rate drop | Simple breakeven | NPV breakeven | Note |"
    separator_row = "|---|---|---|---|---|---|"

    data_rows: list[str] = []
    for row in sorted_rows:
        rate_drop = _fmt_rate(row.rate_drop) if row.rate_drop is not None else "—"
        simple_be = (
            f"{row.simple_breakeven_months} mo" if row.simple_breakeven_months is not None else "—"
        )
        npv_be = f"{row.npv_breakeven_months} mo" if row.npv_breakeven_months is not None else "—"
        note = row.note if row.note else "—"
        data_rows.append(
            f"| {row.program} | {row.points_purchased} | {rate_drop} | "
            f"{simple_be} | {npv_be} | {note} |"
        )

    body = "\n".join([header_row, separator_row, *data_rows]) if data_rows else "_(no points rows)_"
    return f"{section_header}\n\n{body}"


# ---------------------------------------------------------------------------
# REFI OPPORTUNITY (Pitfall 4: signed-money discipline on monthly_savings/npv)
# ---------------------------------------------------------------------------


def _scenario_display(label: str) -> str:
    if label == "minus_100bps":
        return "-100 bps"
    if label == "fred_times_0_85":
        return "FRED x 0.85"
    return label


def _render_refi_opportunity(refi: RefiBlock) -> str:
    """Render the REFI OPPORTUNITY section: program x scenario table.

    monthly_savings and npv_60mo can be NEGATIVE (Phase 14 RefiRow allows
    signed Decimal). Pitfall 4: render as ``-$X,XXX.XX`` not ``$-X,XXX.XX``.
    """
    section_header = "## REFI OPPORTUNITY"

    def _sort_key(row: object) -> tuple[str, int]:
        program = row.program  # type: ignore[attr-defined]
        label = row.scenario_label  # type: ignore[attr-defined]
        return (program, _SCENARIO_LABEL_PRIORITY.get(label, 99))

    sorted_rows = sorted(refi.rows, key=_sort_key)

    header_row = (
        "| Program | Scenario | Target rate | Monthly savings | Breakeven months | 60-mo NPV |"
    )
    separator_row = "|---|---|---|---|---|---|"

    data_rows: list[str] = []
    for row in sorted_rows:
        target_rate = _fmt_rate(row.target_rate)
        monthly = _fmt_signed_money(row.monthly_savings)
        breakeven = f"{row.breakeven_months}" if row.breakeven_months is not None else "—"
        npv = _fmt_signed_money(row.npv_60mo)
        data_rows.append(
            f"| {row.program} | {_scenario_display(row.scenario_label)} | "
            f"{target_rate} | {monthly} | {breakeven} | {npv} |"
        )

    body = "\n".join([header_row, separator_row, *data_rows]) if data_rows else "_(no refi rows)_"
    return f"{section_header}\n\n{body}"


# ---------------------------------------------------------------------------
# TAX (Assumption A8: never compute partial-deduction dollars; "see CPA" gate)
# ---------------------------------------------------------------------------


def _render_tax(tax: TaxBlock, matrix: DownPaymentMatrix) -> str:
    """Render the TAX section: IRS Pub 936 first-year deductibility.

    Per Assumption A8 + CLAUDE.md calc-engine separation: when
    ``over_750k_cap_per_program[program]`` is True, emit a "**see CPA**" callout
    rather than computing partial-deduction dollars. The calc engine renders
    facts; it never paraphrases tax law.
    """
    section_header = "## TAX (IRS Pub 936)"

    qualified_limit = _fmt_money(tax.qualified_loan_limit)

    bullets: list[str] = [
        f"- Filing status: **{tax.filing_status}**",
        f"- Qualified loan limit: {qualified_limit}",
    ]

    for program in matrix.programs_present:
        interest = tax.first_year_interest_per_program.get(program)
        if interest is None:
            continue
        line = f"- First-year deductible interest ({program}): {_fmt_money(interest)}"
        if tax.over_750k_cap_per_program.get(program, False):
            line += (
                f" — ⚠ Loan exceeds qualified loan limit of {qualified_limit}; "
                "partial deduction applies — **see CPA**."
            )
        bullets.append(line)

    body = "\n".join(bullets)
    return f"{section_header}\n\n{body}"


# ---------------------------------------------------------------------------
# VERDICT (D-14-VERDICT-04 passthrough — no paraphrasing of Phase 14 copy)
# ---------------------------------------------------------------------------


def _render_verdict(verdict: Verdict) -> str:
    """Render the VERDICT section: level + headline + falsifiable reasons.

    D-14-VERDICT-04: every VerdictReason is passed through verbatim with its
    ``predicate_code`` and ``computed_value`` so the report carries the audit
    trail Phase 14 produced. No paraphrasing.
    """
    section_header = f"## VERDICT — **{verdict.level}**"
    headline = f"**Headline:** {verdict.headline_reason}"

    reason_lines: list[str] = []
    for r in verdict.reasons:
        line = f"- `{r.predicate_code}`: {r.computed_value}"
        if r.program is not None and r.dp_pct is not None:
            line += f" (program={r.program}, dp={_fmt_pct(r.dp_pct)})"
        elif r.program is not None:
            line += f" (program={r.program})"
        reason_lines.append(line)

    body_parts = [headline]
    if reason_lines:
        body_parts.append("\n".join(reason_lines))
    body = "\n\n".join(body_parts)

    return f"{section_header}\n\n{body}"


# ---------------------------------------------------------------------------
# Public surface — render(report, orchestrator_argv) -> str
# ---------------------------------------------------------------------------


def render(report: AnalysisReport, orchestrator_argv: list[str]) -> str:
    """Render an ``AnalysisReport`` to one-page markdown.

    Pure transform: NO I/O, NO math beyond Decimal display formatting, NO
    IEEE-754 binary types ever (CLAUDE.md money discipline + calc-engine separation).
    The caller (.claude/skills/mortgage-ops/scripts/property_analyze.py —
    Plan 15-03) owns the file write.

    Args:
        report: The AnalysisReport from Phase 14 ``analyze()``.
        orchestrator_argv: The orchestrator's ``sys.argv[1:]`` joined verbatim
            into the citation footer per D-15-CITATION-03 (full re-runnable
            invocation).

    Returns:
        Markdown body string with ``# Property Analysis`` title + 6 ``## ``
        section headers + 6 italic citation footers.
    """
    footer = _render_footer(orchestrator_argv)
    preferred_dp: Decimal = report.stress.preferred_down_payment_pct

    header = _render_header(report)
    your_fit = _render_your_fit(report.matrix, report.listing_snapshot, preferred_dp)
    rate_stress = _render_rate_stress(report.stress)
    points = _render_points_breakeven(report.points)
    refi = _render_refi_opportunity(report.refi)
    tax = _render_tax(report.tax, report.matrix)
    verdict = _render_verdict(report.verdict)

    sections_with_footers = [
        f"{your_fit}\n\n{footer}",
        f"{rate_stress}\n\n{footer}",
        f"{points}\n\n{footer}",
        f"{refi}\n\n{footer}",
        f"{tax}\n\n{footer}",
        f"{verdict}\n\n{footer}",
    ]

    return "\n\n".join([header, *sections_with_footers])
