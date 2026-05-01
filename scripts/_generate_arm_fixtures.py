#!/usr/bin/env python3
"""One-shot generator for tests/fixtures/arm/*.json (Phase 5 Plan 05-06).

Run with: python scripts/_generate_arm_fixtures.py

Per CONTEXT.md D-09 [REVISED 2026-04-30] + Plan 04-06 idiom: expected values
are engine-emitted by lib.arm.build_arm_schedule. Cross-validation against
Bankrate/Vertex42/AmericU oracle captures (separate task) provides the
industry-tool-agreement credibility anchor.

Re-run this script if the engine math changes (it shouldn't — but it's the
single source of truth for fixture regeneration).

Cap-bound fixtures (3 of 11) carry a `hand_calc_check` witness in
expected.reset_events[0] per I-004. This witness is NOT engine output: it is a
pure-Decimal hand-derivation of Fannie B2-1.4-02 + Phase 5 D-02 formula values
that the engine MUST match. The non-cap-bound fixtures (8 of 11) are
cross-validated against external Bankrate/Vertex42/AmericU oracle JSONs
(Tasks 2 + 3) and therefore do not embed a hand-calc witness.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.arm import (  # noqa: E402  -- after sys.path injection
    ARMRequest,
    ARMTerms,
    IndexPathEntry,
    build_arm_schedule,
)
from lib.models import Loan  # noqa: E402

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "arm"


def _serialize(req: ARMRequest, fixture_id: str, source: str, notes: str) -> dict[str, Any]:
    """Run the engine and assemble the fixture dict (engine-emitted expected)."""
    schedule = build_arm_schedule(req)
    return {
        "id": fixture_id,
        "source": source,
        "notes": notes,
        "request": json.loads(req.model_dump_json()),
        "expected": json.loads(schedule.model_dump_json()),
    }


def _write(fixture: dict[str, Any]) -> Path:
    path = FIXTURE_DIR / f"{fixture['id']}.json"
    path.write_text(json.dumps(fixture, indent=2) + "\n")
    return path


# Pure-Decimal hand-calc witnesses for cap-bound fixtures (I-004).
# These values come from manual application of the D-02 / Fannie B2-1.4-02
# formula — NOT from the engine. The fixture/test then asserts the engine
# matches these witnesses exactly.
HAND_CALC_LIFETIME = {
    "_citation": "Fannie Mae Selling Guide §B2-1.4-02 + Phase 5 D-02 locked formula",
    "_method": "Pure Decimal arithmetic; not engine output",
    "fully_indexed": "0.225000",
    "effective_floor": "0.030000",
    "periodic_ceiling": "0.250000",
    "lifetime_ceiling": "0.080000",
    "applied_cap_expected": "lifetime",
    "new_rate_expected": "0.080000",
}

HAND_CALC_INITIAL = {
    "_citation": "Fannie Mae Selling Guide §B2-1.4-02 + Phase 5 D-02 locked formula",
    "_method": "Pure Decimal arithmetic; not engine output",
    "fully_indexed": "0.225000",
    "effective_floor": "0.030000",
    "periodic_ceiling": "0.100000",
    "lifetime_ceiling": "0.250000",
    "applied_cap_expected": "initial",
    "new_rate_expected": "0.100000",
}

HAND_CALC_FLOOR = {
    "_citation": "Fannie Mae Selling Guide §B2-1.4-02 + Phase 5 D-02 locked formula",
    "_method": "Pure Decimal arithmetic; not engine output",
    "fully_indexed": "0.021000",
    "effective_floor": "0.040000",
    "periodic_ceiling": "0.100000",
    "lifetime_ceiling": "0.100000",
    "applied_cap_expected": "floor",
    "new_rate_expected": "0.040000",
}


# ---------------------------------------------------------------------------
# Fixture builders — one per scenario from the D-09 [REVISED] table.
# ---------------------------------------------------------------------------


def _canonical_5_1_loan() -> Loan:
    """Canonical 5/1 ARM loan inputs ($400k @ 5% / 30yr, origination 2026-01-01)."""
    return Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.050000"),
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="arm",
    )


def _canonical_5_1_terms() -> ARMTerms:
    return ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )


def build_arm_5_1_payment_jump_at_61() -> dict[str, Any]:
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=_canonical_5_1_terms(),
        assumed_index_rate=Decimal("0.052500"),
        index_path=[],
    )
    return _serialize(
        req,
        "arm_5_1_payment_jump_at_61",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ROADMAP SC-2 primary fixture; cross-validated against bankrate_5_1_capture_2026.{pdf,json} + vertex42_5_1_capture_2026.{pdf,json}",
        "5/1 ARM 30yr; 5% initial / 2.5pp margin / 0.0525 assumed index -> fully_indexed=0.0775. "
        "Modest reset within all caps; applied_cap='none' per D-10 LM-5.",
    )


def build_arm_5_1_off_by_one_negative() -> dict[str, Any]:
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=_canonical_5_1_terms(),
        assumed_index_rate=Decimal("0.052500"),
        index_path=[],
    )
    fx = _serialize(
        req,
        "arm_5_1_off_by_one_negative",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ROADMAP SC-3 negative-direction fixture; reuses arm_5_1_payment_jump_at_61 inputs; cross-validation is the per-period equality test against the same engine output",
        "ROADMAP SC-3 negative direction. Re-uses arm_5_1_payment_jump_at_61 numbers. "
        "Test asserts month 59 still uses initial rate AND month 61 already uses new rate "
        "(covers BOTH sides of the off-by-one).",
    )
    return fx


def build_arm_7_1_payment_jump_at_85() -> dict[str, Any]:
    terms = ARMTerms(
        initial_period_months=84,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=terms,
        assumed_index_rate=Decimal("0.055000"),
        index_path=[],
    )
    return _serialize(
        req,
        "arm_7_1_payment_jump_at_85",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ARM-02 7/1 product fixture; cross-validated against bankrate_7_1_capture_2026.{pdf,json}",
        "7/1 ARM 30yr (initial=84, reset=12); 5% initial / 2.5pp margin / 0.055 assumed index "
        "-> fully_indexed=0.080. Modest reset within all caps; applied_cap='none'.",
    )


def build_arm_10_1_payment_jump_at_121() -> dict[str, Any]:
    terms = ARMTerms(
        initial_period_months=120,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=terms,
        assumed_index_rate=Decimal("0.055000"),
        index_path=[],
    )
    return _serialize(
        req,
        "arm_10_1_payment_jump_at_121",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ARM-02 10/1 product fixture; cross-validated against bankrate_10_1_capture_2026.{pdf,json}",
        "10/1 ARM 30yr (initial=120, reset=12); 5% initial / 2.5pp margin / 0.055 assumed index "
        "-> fully_indexed=0.080. Modest reset within all caps; applied_cap='none'.",
    )


def build_arm_5_6_payment_jump_at_61_and_67() -> dict[str, Any]:
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=6,
        initial_cap_bps=200,
        periodic_cap_bps=100,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="SOFR1Y",
    )
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=terms,
        assumed_index_rate=Decimal("0.052000"),
        index_path=[],
    )
    return _serialize(
        req,
        "arm_5_6_payment_jump_at_61_and_67",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ARM-02 5/6 SOFR product fixture; cross-validated against americu_5_6_disclosure_2022.pdf + americu_5_6_disclosure.json (2/1/5 caps)",
        "5/6 SOFR ARM with 2/1/5 caps per AmericU disclosure. First reset binds at "
        "initial_cap (0.07); second reset within new periodic ceiling (0.08). "
        "Spans applied_cap='initial' (first reset) AND 'none' (second reset) for D-10 coverage.",
    )


def build_arm_floor_below_margin_blocked() -> dict[str, Any]:
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.040000"),
        margin_bps=200,
        index_series_id="MORTGAGE30US",
    )
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=terms,
        assumed_index_rate=Decimal("0.001000"),
        index_path=[],
    )
    fx = _serialize(
        req,
        "arm_floor_below_margin_blocked",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ARM-04 + ROADMAP SC-4; cap-bound fixture has hand_calc_check witness per I-004 (no external oracle covers floor-bound scenarios)",
        "ARM-04 + ROADMAP SC-4. Index drops to 0.1%; fully_indexed=0.021 < floor_rate=0.04; "
        "floor enforces new_rate=0.04. applied_cap='floor' for D-10 coverage. "
        "Hand-calc witness per I-004; cap-bound paths not covered by Bankrate/Vertex42/AmericU.",
    )
    fx["expected"]["reset_events"][0]["hand_calc_check"] = HAND_CALC_FLOOR
    return fx


def build_arm_lifetime_cap_binds() -> dict[str, Any]:
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=2000,
        periodic_cap_bps=2000,
        lifetime_cap_bps=300,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=terms,
        assumed_index_rate=Decimal("0.200000"),
        index_path=[],
    )
    fx = _serialize(
        req,
        "arm_lifetime_cap_binds",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ARM-03 lifetime-cap fixture; cap-bound fixture has hand_calc_check witness per I-004 (no external oracle covers cap-bound scenarios)",
        "ARM-03 lifetime cap. Index spikes to 20%; fully_indexed=0.225; periodic_ceiling=0.25 "
        "(huge initial cap doesn't bind); lifetime_ceiling=0.05+0.03=0.08; ceiling=0.08; "
        "new_rate=0.08. applied_cap='lifetime' for D-10 coverage. Hand-calc witness per I-004.",
    )
    fx["expected"]["reset_events"][0]["hand_calc_check"] = HAND_CALC_LIFETIME
    return fx


def build_arm_initial_cap_at_first_reset() -> dict[str, Any]:
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=500,
        periodic_cap_bps=200,
        lifetime_cap_bps=2000,
        floor_rate=Decimal("0.030000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
    )
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=terms,
        assumed_index_rate=Decimal("0.200000"),
        index_path=[],
    )
    fx = _serialize(
        req,
        "arm_initial_cap_at_first_reset",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ARM-03 initial+periodic cap fixture; cap-bound fixture has hand_calc_check witness per I-004 (no external oracle covers cap-bound scenarios)",
        "ARM-03 initial-vs-periodic cap. Index=0.20; fully_indexed=0.225. "
        "First reset: periodic_ceiling=0.05+0.05=0.10 (initial_cap binds); applied_cap='initial'. "
        "Second reset (period 73): periodic_ceiling=0.10+0.02=0.12; applied_cap='periodic'. "
        "Lifetime cap large; doesn't bind. Spans 'initial' + 'periodic' for D-10 coverage. "
        "Hand-calc witness on first reset per I-004.",
    )
    fx["expected"]["reset_events"][0]["hand_calc_check"] = HAND_CALC_INITIAL
    return fx


def build_arm_teaser_rate() -> dict[str, Any]:
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.030000"),
        term_months=360,
        origination_date=date(2026, 1, 1),
        loan_type="arm",
    )
    terms = ARMTerms(
        initial_period_months=60,
        reset_period_months=12,
        initial_cap_bps=2000,
        periodic_cap_bps=2000,
        lifetime_cap_bps=500,
        floor_rate=Decimal("0.020000"),
        margin_bps=250,
        index_series_id="MORTGAGE30US",
        note_rate=Decimal("0.050000"),
    )
    req = ARMRequest(
        loan=loan,
        arm_terms=terms,
        assumed_index_rate=Decimal("0.150000"),
        index_path=[],
    )
    return _serialize(
        req,
        "arm_teaser_rate",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; LM-3 teaser-ARM fixture; documents D-02 lifetime-ceiling computed against note_rate (industry/Fannie convention) — alternative CFPB §1951 against loan.annual_rate is explicitly NOT used per D-02 lock",
        "Teaser ARM. loan.annual_rate=0.03 (teaser), note_rate=0.05 (post-teaser base). "
        "Lifetime ceiling = note_rate(0.05)+0.05 = 0.10 (engine choice per D-02 LM-3), "
        "NOT loan.annual_rate-based 0.08. fully_indexed=0.175 -> ceiling=0.10 -> new_rate=0.10. "
        "applied_cap='lifetime'. Pins LM-3 convention against silent regression.",
    )


def build_arm_continuous_period_numbering() -> dict[str, Any]:
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=_canonical_5_1_terms(),
        assumed_index_rate=Decimal("0.052500"),
        index_path=[],
    )
    return _serialize(
        req,
        "arm_continuous_period_numbering",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; ARM-05 + D-03 continuous-period-numbering fixture; reuses canonical 5/1 inputs to pin period 1..360, final_balance=0, total_interest=cumulative_interest invariant",
        "ARM-05 + D-03. Pins continuous period numbering 1..360, final_balance=0.00, "
        "total_interest = payments[-1].cumulative_interest (Phase 1 D-15 invariant). "
        "Same engine inputs as arm_5_1_payment_jump_at_61; different test focuses on "
        "structural invariants instead of payment-jump.",
    )


def build_arm_index_path_overrides() -> dict[str, Any]:
    req = ARMRequest(
        loan=_canonical_5_1_loan(),
        arm_terms=_canonical_5_1_terms(),
        assumed_index_rate=Decimal("0.050000"),
        index_path=[
            IndexPathEntry(period=61, value=Decimal("0.060000")),
            IndexPathEntry(period=73, value=Decimal("0.045000")),
        ],
    )
    return _serialize(
        req,
        "arm_index_path_overrides",
        "engine-emitted by lib.arm.build_arm_schedule on 2026-04-30; D-01 override-wins fixture; pins per-reset index_path precedence over assumed_index_rate fallback",
        "D-01 override-wins. assumed_index_rate=0.05 (fallback). index_path provides 0.06 at "
        "period 61 and 0.045 at period 73; subsequent resets fall back to assumed_index_rate. "
        "Pins override-wins semantics against silent regression.",
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


BUILDERS = (
    build_arm_5_1_payment_jump_at_61,
    build_arm_5_1_off_by_one_negative,
    build_arm_7_1_payment_jump_at_85,
    build_arm_10_1_payment_jump_at_121,
    build_arm_5_6_payment_jump_at_61_and_67,
    build_arm_floor_below_margin_blocked,
    build_arm_lifetime_cap_binds,
    build_arm_initial_cap_at_first_reset,
    build_arm_teaser_rate,
    build_arm_continuous_period_numbering,
    build_arm_index_path_overrides,
)


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for builder in BUILDERS:
        fixture = builder()
        path = _write(fixture)
        written.append(path)
        print(f"  wrote {path.relative_to(PROJECT_ROOT)}")
    print(f"\nGenerated {len(written)} ARM fixtures in {FIXTURE_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
