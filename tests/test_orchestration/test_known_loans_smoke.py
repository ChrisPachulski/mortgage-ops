"""Phase 9 known-loans.yml smoke test (PERS-07).

Wave 5 (Plan 09-05) ships data/known-loans.yml with at least 7 product
entries; this stub flips to verify catalog completeness + Reference Layer
discipline (source: URL + effective: ISO date) per REF-09 inheritance.
"""

from __future__ import annotations

from pathlib import Path

import pytest

KNOWN_LOANS_PATH: Path = Path(__file__).resolve().parent.parent.parent / "data" / "known-loans.yml"
"""Reference Layer file per DATA_CONTRACT.md line 67 (committed; manually refreshed)."""


@pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-05 ships data/known-loans.yml")
def test_known_loans_catalog_complete() -> None:
    """PERS-07 + ROADMAP SC-5: data/known-loans.yml contains at least 7
    product entries (30yr fixed conv, 15yr fixed conv, ARM 5/1, ARM 7/1,
    FHA 30yr, VA 30yr, jumbo 30yr) AND has top-level `source:` URL plus
    `effective:` date per Reference Layer discipline (REF-09 inheritance).
    Each product's `loan_type` value MUST be one of the lib.models.Loan
    Literal options ('fixed', 'arm', 'fha', 'va', 'usda', 'jumbo').
    """
    pytest.fail("Wave 0 stub")
