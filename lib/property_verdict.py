"""Phase 14 verdict synthesis — GO / WATCH / NO_GO cascade.

D-14-MODELS-03 module: consumes a populated ``DownPaymentMatrix`` +
``StressBlock`` and emits a falsifiable ``Verdict`` (level + headline_reason
+ reasons[]). The cascade implements D-14-VERDICT-01..04 in first-match-wins
order, mirroring ``lib/affordability.py:_evaluate_blockers`` (L1207-1380) —
the closest 1:1 architectural analog (RESEARCH §"Pattern: lib/property_verdict.py";
PATTERNS.md L328-455).

Cascade order (CONTEXT D-14-VERDICT-01..04):
  Level 1: NO_GO if no eligible cell at any DP across any program
           -> VERDICT_NO_GO_DTI_ALL_PROGRAMS
  Level 2: NO_GO if no eligible cell at preferred DP
           -> VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP
  Level 3: WATCH if ANY eligible-at-preferred-DP program fails the income-shock
           stress (D-14-VERDICT-02 — DTI breaches program ceiling at income x 0.70)
           -> VERDICT_WATCH_STRESS_INCOME_FAIL
  Level 4: WATCH if all eligible-at-preferred-DP cells are FHA30; the headline
           calls out when FHA monthly MIP is above $300
           -> VERDICT_WATCH_FHA_MIP_BURDEN
  Level 5: GO (D-14-VERDICT-03 — any non-FHA program eligible at preferred DP)
           -> VERDICT_GO

Every emitted ``VerdictReason`` carries BOTH ``predicate_code`` (one of the
VERDICT_* constants) AND ``computed_value`` (the number that triggered the
branch). D-14-VERDICT-04 falsifiable-reason discipline; Pitfall 7 prefix
discipline; Pitfall 12 mitigation via the citation-coverage meta-test in
``tests/test_property_verdict.py``.

VERD-01 closes at unit-test level when this module + the companion test file
both land; Plan 14-06 tightens to fixture-based coverage.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from lib.household import Household  # noqa: TC001  # used at runtime by synthesize()
from lib.profile import Profile  # noqa: TC001  # used at runtime by synthesize()
from lib.property_analysis import (
    DownPaymentMatrix,
    StressBlock,
    Verdict,
    VerdictReason,
)

# ---------------------------------------------------------------------------
# VERDICT_* citation constants (Pitfall 7 prefix discipline)
# ---------------------------------------------------------------------------
#
# Every constant below is a ``Final[str]`` with a stable string value the
# downstream report formatter (Phase 15) cites VERBATIM. The
# ``test_verdict_code_citation_coverage`` meta-test in
# tests/test_property_verdict.py introspects this module via ``vars()`` to
# discover every ``VERDICT_`` prefixed string and assert each is exercised by
# at least one cascade-level scenario — Plan 14-06 tightens that to
# fixture-based coverage.

VERDICT_NO_GO_DTI_ALL_PROGRAMS: Final[str] = "DTI-CEILING-ALL-PROGRAMS"
"""Level 1 — emitted when no cell in the matrix is eligible at any DP.

The cascade emits the minimum DTI across all cells as ``computed_value`` so
the report can cite the smallest DTI ratio we computed (the closest-to-passing
attempt). Falls back to ``Decimal("0")`` when ``matrix.cells`` is empty
(degenerate path; Behavior 9)."""

VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP: Final[str] = "NO-ELIGIBLE-AT-PREFERRED-DP"
"""Level 2 — emitted when SOME cell is eligible at SOME non-preferred DP but
no cell is eligible at ``household.preferred_down_payment_pct``. The user's
constraint (the DP they want to put down) is the binding rule."""

VERDICT_WATCH_STRESS_INCOME_FAIL: Final[str] = "STRESS-INCOME-SHOCK"
"""Level 3 (D-14-VERDICT-02) — emitted when ANY eligible-at-preferred-DP
program's income-shock stress row has ``breaches_dti_ceiling=True`` (income
falls to 0.70x and DTI exceeds the program's ceiling per
``lib.property_analysis._DTI_CEILING_BY_PROGRAM``). One VerdictReason per
failing row; computed_value is the stressed DTI."""

VERDICT_WATCH_FHA_MIP_BURDEN: Final[str] = "MIP-BURDEN-FHA"
"""Level 4 (D-14-VERDICT-01 + D-14-VERDICT-03 precedence) — emitted when ALL
eligible-at-preferred-DP cells are FHA30 (no Conv/VA/Jumbo eligible). The
headline distinguishes an above-threshold FHA monthly MIP from an FHA-only path
with acceptable MIP. D-14-VERDICT-03 GO-wins precedence: this branch is SKIPPED
when a non-FHA program is eligible at preferred DP."""

VERDICT_GO: Final[str] = "GO-ALL-GREEN"
"""Level 5 (default; D-14-VERDICT-03) — emitted when at least one non-FHA
program is eligible at preferred DP AND no income-shock failures occurred.
computed_value is the count of non-FHA eligible programs."""

# ---------------------------------------------------------------------------
# Policy thresholds (Assumption A1; CONTEXT "Claude's Discretion")
# ---------------------------------------------------------------------------

_MIP_BURDEN_THRESHOLD: Final[Decimal] = Decimal("300.00")
"""D-14-VERDICT-01 policy choice (Assumption A1): the fixed dollar threshold
above which an FHA-only eligible path downgrades a verdict to WATCH. Pinned
as a falsifiable scalar rather than a comparative ratio so the verdict copy
stays short and explainable. CONTEXT "Claude's Discretion" permits a planner
swap if a credible HUD / MBA published heuristic surfaces; for v1.1 the
$300/mo policy choice stands."""


# ---------------------------------------------------------------------------
# synthesize() — D-14-VERDICT-01..04 cascade (first-match-wins)
# ---------------------------------------------------------------------------


def synthesize(
    matrix: DownPaymentMatrix,
    stress: StressBlock,
    household: Household,
    profile: Profile,
) -> Verdict:
    """Synthesize a Verdict from the populated matrix + stress block.

    Pure function — no I/O, no global state reads, no ``time.now()`` calls
    (Behavior 10). Inputs are never mutated; all returned Pydantic instances
    are fresh constructions (Behavior 8). Mirrors the first-match-wins
    cascade idiom from ``lib.affordability._evaluate_blockers`` L1207-1380.

    Args:
        matrix: The fully-populated DownPaymentMatrix from
            ``lib.property_analysis._build_matrix``.
        stress: The StressBlock from ``_build_stress_block`` (rows at
            ``household.preferred_down_payment_pct`` only per D-14-STRESS-01).
        household: The analysis-time Household snapshot; the cascade reads
            ``preferred_down_payment_pct`` to select the binding DP.
        profile: The analysis-time Profile (currently unused by the cascade
            but retained in the signature for forward-compat with Plan
            14-05's ``analyze()`` call-site — VERD-01 may grow to read
            ``filing_status`` / ``marginal_tax_rate`` in a follow-on phase).

    Returns:
        Verdict with ``level`` in ("NO_GO", "WATCH", "GO") and a list of
        falsifiable reasons; every reason carries predicate_code +
        computed_value per D-14-VERDICT-04.
    """
    # Unused-arg suppression: profile is reserved for forward-compat with
    # tax-aware verdicts. Plan 14-04 scope intentionally does NOT consume it;
    # signature pinned so Plan 14-05's analyze() callsite never changes.
    del profile

    preferred = household.preferred_down_payment_pct
    cells_at_preferred = [c for c in matrix.cells if c.down_payment_pct == preferred]
    eligible_at_preferred = [c for c in cells_at_preferred if c.eligible]
    non_fha_eligible = [c for c in eligible_at_preferred if c.program != "FHA30"]

    # -----------------------------------------------------------------------
    # Level 1 (D-14-VERDICT cascade entry): no cell eligible at ANY DP
    # -----------------------------------------------------------------------
    if not any(c.eligible for c in matrix.cells):
        # Behavior 9: empty matrix degenerate path uses default=Decimal("0")
        # so min(...) does not raise on an empty iterable.
        min_dti = min((c.dti_back for c in matrix.cells), default=Decimal("0"))
        return Verdict(
            level="NO_GO",
            headline_reason="No program qualifies at any DP scenario",
            reasons=[
                VerdictReason(
                    predicate_code=VERDICT_NO_GO_DTI_ALL_PROGRAMS,
                    computed_value=str(min_dti),
                )
            ],
        )

    # -----------------------------------------------------------------------
    # Level 2: SOMETHING eligible at non-preferred DP, but nothing at preferred
    # -----------------------------------------------------------------------
    if not eligible_at_preferred:
        return Verdict(
            level="NO_GO",
            headline_reason=f"No program qualifies at preferred DP {preferred}",
            reasons=[
                VerdictReason(
                    predicate_code=VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP,
                    computed_value=str(preferred),
                    dp_pct=preferred,
                )
            ],
        )

    # -----------------------------------------------------------------------
    # Level 3 (D-14-VERDICT-02): WATCH if any eligible-at-preferred-DP program
    # fails the income-shock stress. Income-shock WATCH precedes BOTH the
    # FHA-MIP burden branch AND the GO default — a stress failure on any
    # eligible path is the conservative most-protective signal (CONTEXT
    # D-14-VERDICT-02).
    # -----------------------------------------------------------------------
    income_stress_fails = [
        s
        for s in stress.rows
        if s.stress_kind == "income_shock"
        and s.breaches_dti_ceiling
        and any(c.program == s.program for c in eligible_at_preferred)
    ]
    if income_stress_fails:
        return Verdict(
            level="WATCH",
            headline_reason=(
                "Income-shock stress breaches DTI ceiling for "
                f"{len(income_stress_fails)} eligible program(s)"
            ),
            reasons=[
                VerdictReason(
                    predicate_code=VERDICT_WATCH_STRESS_INCOME_FAIL,
                    computed_value=str(f.stressed_dti_back),
                    program=f.program,
                )
                for f in income_stress_fails
            ],
        )

    # -----------------------------------------------------------------------
    # Level 4 (D-14-VERDICT-01 + D-14-VERDICT-03 GO-wins precedence): WATCH
    # if ONLY FHA30 is eligible at preferred DP. The guard ``not non_fha_eligible``
    # enforces D-14-VERDICT-03: any non-FHA eligible cell short-circuits this
    # branch straight to Level 5 (GO).
    # -----------------------------------------------------------------------
    if not non_fha_eligible:
        fha_cells = [c for c in eligible_at_preferred if c.program == "FHA30"]
        if fha_cells:
            headline = (
                f"FHA-only path with monthly MIP {fha_cells[0].monthly_mi}"
                if fha_cells[0].monthly_mi > _MIP_BURDEN_THRESHOLD
                else f"FHA-only path eligible with monthly MIP {fha_cells[0].monthly_mi}"
            )
            return Verdict(
                level="WATCH",
                headline_reason=headline,
                reasons=[
                    VerdictReason(
                        predicate_code=VERDICT_WATCH_FHA_MIP_BURDEN,
                        computed_value=str(fha_cells[0].monthly_mi),
                        program="FHA30",
                        dp_pct=preferred,
                    )
                ],
            )

    # -----------------------------------------------------------------------
    # Level 5 (D-14-VERDICT-03 default GO): at least one non-FHA program is
    # eligible at preferred DP AND no income-shock stress failures occurred
    # AND we did not fall through the FHA-only-MIP-burden branch.
    # -----------------------------------------------------------------------
    return Verdict(
        level="GO",
        headline_reason=(
            f"{len(non_fha_eligible)} non-FHA program(s) eligible at preferred DP {preferred}"
        ),
        reasons=[
            VerdictReason(
                predicate_code=VERDICT_GO,
                computed_value=str(len(non_fha_eligible)),
            )
        ],
    )
