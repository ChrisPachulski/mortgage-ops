"""Phase 1 only validates the fixture file's SHAPE and the immutable pinned values.

Phase 3's test_amortize.py will compute against these fixtures using lib/amortize.py.
Keeping these separate prevents Phase 1 from importing amortization code (which
doesn't exist yet).

Every assertion includes the hand-calculated expected value and why; the four pinned
expected_monthly_pi strings (1264.14, 761.78, 2528.27, 1797.66) are immutable contracts
per FND-09 + RESEARCH.md A1.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURE_PATH: Path = Path(__file__).parent / "fixtures" / "golden_pmt.json"

REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "source",
        "principal",
        "annual_rate",
        "term_months",
        "expected_monthly_pi",
        "rounding",
        "notes",
    }
)
EXPECTED_IDS: frozenset[str] = frozenset(
    {
        "wikipedia_200k_30yr",
        "cfpb_le_162k_30yr",
        "computed_400k_30yr",
        "computed_200k_15yr",
    }
)


def test_golden_pmt_fixture_loads() -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    assert "fixtures" in data
    assert isinstance(data["fixtures"], list)
    assert len(data["fixtures"]) == 4


def test_golden_pmt_has_all_four_oracles() -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    ids = {f["id"] for f in data["fixtures"]}
    assert ids == EXPECTED_IDS


@pytest.mark.parametrize("idx", range(4))
def test_golden_pmt_each_fixture_well_formed(idx: int) -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    fx: dict[str, Any] = data["fixtures"][idx]
    assert fx.keys() >= REQUIRED_FIELDS
    # money / rate values must be parseable as Decimal from the string form
    Decimal(fx["principal"])
    Decimal(fx["annual_rate"])
    Decimal(fx["expected_monthly_pi"])
    assert fx["rounding"] == "ROUND_HALF_UP"
    assert isinstance(fx["term_months"], int)


def test_pinned_expected_values() -> None:
    """Lock the actual numbers. If anyone edits the file, the test fails loud.

    These are the FND-09 contract values, independently re-derived in RESEARCH.md A1.
    """
    data = {f["id"]: f for f in json.loads(FIXTURE_PATH.read_text())["fixtures"]}
    assert data["wikipedia_200k_30yr"]["expected_monthly_pi"] == "1264.14"
    assert data["cfpb_le_162k_30yr"]["expected_monthly_pi"] == "761.78"
    assert data["computed_400k_30yr"]["expected_monthly_pi"] == "2528.27"
    assert data["computed_200k_15yr"]["expected_monthly_pi"] == "1797.66"


def test_pinned_principals_and_terms() -> None:
    """Cross-check that the principal / annual_rate / term_months also match
    REQUIREMENTS.md FND-09 verbatim."""
    data = {f["id"]: f for f in json.loads(FIXTURE_PATH.read_text())["fixtures"]}
    assert data["wikipedia_200k_30yr"]["principal"] == "200000.00"
    assert data["wikipedia_200k_30yr"]["annual_rate"] == "0.065000"
    assert data["wikipedia_200k_30yr"]["term_months"] == 360
    assert data["cfpb_le_162k_30yr"]["principal"] == "162000.00"
    assert data["cfpb_le_162k_30yr"]["annual_rate"] == "0.038750"
    assert data["cfpb_le_162k_30yr"]["term_months"] == 360
    assert data["computed_400k_30yr"]["principal"] == "400000.00"
    assert data["computed_400k_30yr"]["annual_rate"] == "0.065000"
    assert data["computed_400k_30yr"]["term_months"] == 360
    assert data["computed_200k_15yr"]["principal"] == "200000.00"
    assert data["computed_200k_15yr"]["annual_rate"] == "0.070000"
    assert data["computed_200k_15yr"]["term_months"] == 180


def test_conftest_golden_fixture_loader_finds_each_id(
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Dogfood the conftest.py golden_fixture loader (Plan 01).

    Phase 3+ will use this loader to fetch fixtures; Phase 1 verifies it works on
    the real file before downstream phases depend on it.
    """
    for fixture_id in EXPECTED_IDS:
        fx = golden_fixture(fixture_id)
        assert fx["id"] == fixture_id
        assert fx["rounding"] == "ROUND_HALF_UP"


def test_conftest_golden_fixture_raises_on_unknown_id(
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    with pytest.raises(KeyError):
        golden_fixture("nonexistent_fixture_id_xyz")
