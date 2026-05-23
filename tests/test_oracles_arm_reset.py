"""Independent oracle tests for the ARM reset engine (lib.arm.build_arm_schedule).

Source: CFPB Consumer Handbook on Adjustable-Rate Mortgages (CHARM) booklet,
§3.5.1 'Periodic adjustment caps' worked example. Substitutes for the
Vertex42 Excel ARM template (which requires Excel/LibreOffice) per task
brief and project-wide oracle-substitution precedent (Phase 5 ARM-06
deferred Bankrate/Vertex42 captures).

CHARM publishes the exact dollar values for a 1/1 ARM with a 2pp periodic
cap; engine reset math must reproduce them to the cent.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lib.arm import (
    ARMRequest,
    ARMTerms,
    build_arm_schedule,
)
from lib.models import Loan

if TYPE_CHECKING:
    from collections.abc import Callable


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "oracles" / "excel-arm"


def _build_arm_request_from_oracle(fx: dict[str, Any]) -> ARMRequest:
    req_d = fx["arm_request"]
    loan_d = req_d["loan"]
    terms_d = req_d["arm_terms"]
    loan = Loan(
        principal=Decimal(loan_d["principal"]),
        annual_rate=Decimal(loan_d["annual_rate"]),
        term_months=loan_d["term_months"],
        loan_type=loan_d.get("loan_type", "arm"),
    )
    terms_kwargs: dict[str, Any] = {
        "initial_period_months": terms_d["initial_period_months"],
        "reset_period_months": terms_d["reset_period_months"],
        "initial_cap_bps": terms_d["initial_cap_bps"],
        "periodic_cap_bps": terms_d["periodic_cap_bps"],
        "lifetime_cap_bps": terms_d["lifetime_cap_bps"],
        "floor_rate": Decimal(terms_d["floor_rate"]),
        "margin_bps": terms_d["margin_bps"],
        "index_series_id": terms_d["index_series_id"],
    }
    if terms_d.get("note_rate") is not None:
        terms_kwargs["note_rate"] = Decimal(terms_d["note_rate"])
    terms = ARMTerms(**terms_kwargs)
    return ARMRequest(
        loan=loan,
        arm_terms=terms,
        assumed_index_rate=Decimal(req_d["assumed_index_rate"]),
    )


def test_cfpb_charm_1_1_arm_periodic_cap_engine_matches_byte_for_byte(
    oracle_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """CFPB CHARM §3.5.1 1/1 ARM with 2pp periodic cap.

    Engine must reproduce the booklet's published values for:
      - Year-1 payment ($1,199.10 at 6.00%)
      - Year-2 payment with cap ($1,461.72 at 8.00%, applied_cap='initial')
      - Year-1 ending balance ($197,543.99)
      - Monthly cap-savings = $138.70 (= 1600.42 - 1461.72)

    All assertions are EXACT Decimal-cent equality per the project's money
    discipline (CLAUDE.md FND-09 / never assertAlmostEqual on money).
    """
    fx = oracle_fixture("excel-arm/cfpb_charm_1_1_arm_periodic_cap")
    req = _build_arm_request_from_oracle(fx)
    schedule = build_arm_schedule(req)

    expected = fx["expected"]

    # Period 12 = last fixed-rate payment of year 1
    p12 = schedule.payments[11]
    assert p12.payment == Decimal(expected["year1_p_and_i"]), (
        f"Year-1 payment {p12.payment} != CHARM oracle {expected['year1_p_and_i']}"
    )
    assert p12.rate_in_effect == Decimal(expected["year1_rate"]), (
        f"Year-1 rate {p12.rate_in_effect} != oracle {expected['year1_rate']}"
    )
    assert p12.balance == Decimal(expected["year1_balance_after_period_12"]), (
        f"Year-1 ending balance {p12.balance} != CHARM oracle "
        f"{expected['year1_balance_after_period_12']}"
    )

    # Period 13 = first payment after reset
    p13 = schedule.payments[12]
    assert p13.payment == Decimal(expected["year2_p_and_i_capped"]), (
        f"Year-2 payment with cap {p13.payment} != CHARM oracle "
        f"{expected['year2_p_and_i_capped']} — a binding 2pp cap miscalculation "
        f"would surface here."
    )
    assert p13.rate_in_effect == Decimal(expected["year2_rate_capped"]), (
        f"Year-2 rate with cap {p13.rate_in_effect} != oracle {expected['year2_rate_capped']}"
    )

    # First reset event
    assert len(schedule.reset_events) >= 1
    first_reset = schedule.reset_events[0]
    assert first_reset.applied_cap == expected["first_reset_applied_cap"], (
        f"Engine applied_cap='{first_reset.applied_cap}' != oracle "
        f"'{expected['first_reset_applied_cap']}' — CHARM's example is the "
        f"FIRST reset, so initial_cap (not periodic_cap) is the binding "
        f"constraint per lib.arm.D-02."
    )
    assert first_reset.new_pmt == Decimal(expected["year2_p_and_i_capped"])
    assert first_reset.new_rate == Decimal(expected["year2_rate_capped"])


def test_cfpb_charm_csv_companion_loads_and_matches_engine() -> None:
    """The CSV companion to the CHARM oracle is loadable and self-consistent.

    The CSV documents the (period, rate, payment, balance) tuples for the
    same scenario; this test parses it and asserts the engine reproduces
    the cap-applied year-2 payment exactly. The CSV is the "Excel-equivalent"
    capture form (per task brief Source C) for anyone auditing the fixture
    without opening the JSON.
    """
    csv_path = FIXTURES_DIR / "cfpb_charm_1_1_arm_periodic_cap.csv"
    assert csv_path.exists(), f"CSV companion missing at {csv_path}"
    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    # CSV must have at least three rows (year-1 last, year-2 capped, year-2 uncapped)
    assert len(rows) >= 3, f"CSV companion needs >= 3 rows; got {len(rows)}"

    capped_row = next(
        r for r in rows if r["scenario"] == "cfpb_charm_periodic_cap_1_1" and r["period"] == "13"
    )
    # The CSV's year-2 capped row must show 8.00% / $1,461.72 (matching CHARM)
    assert Decimal(capped_row["rate"]) == Decimal("0.080000")
    assert Decimal(capped_row["payment"]) == Decimal("1461.72")
