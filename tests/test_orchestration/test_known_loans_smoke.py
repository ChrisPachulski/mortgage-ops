"""Phase 9 known-loans.yml catalog smoke test (PERS-07 + ROADMAP SC-5).

Wave 5 (Plan 09-05) ships data/known-loans.yml as the Reference Layer
product catalog. This test asserts: (1) the file is valid YAML, (2) the
top-level Reference Layer keys (source, effective) are present, (3) all
7 PERS-07-required product IDs exist, and (4) every product entry has
the full 9-key schema.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH: Path = REPO_ROOT / "data" / "known-loans.yml"

# PERS-07: catalog must include 30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1,
# FHA 30yr, VA 30yr, jumbo 30yr (verbatim from REQUIREMENTS.md PERS-07
# and 09-RESEARCH.md §"Sample data/known-loans.yml" lines 488-492).
REQUIRED_IDS: frozenset[str] = frozenset(
    {
        "conv-30yr-fixed",
        "conv-15yr-fixed",
        "arm-5-1",
        "arm-7-1",
        "fha-30yr",
        "va-30yr",
        "jumbo-30yr-fixed",
    }
)

# Per RESEARCH §Sample lines 481-503: every product entry MUST carry these
# 9 keys. Missing keys break Phase 10 routing + Phase 12 eval-harness lookup.
REQUIRED_PER_ENTRY_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "label",
        "loan_type",
        "principal",
        "apr",
        "term_months",
        "frequency",
        "origination_date",
        "citation_url",
    }
)


def test_known_loans_catalog_complete() -> None:
    """PERS-07 + ROADMAP SC-5: data/known-loans.yml exists with at least
    the 7 required product entries, each carrying the full 9-key schema,
    and the top-level Reference Layer convention keys (source, effective)
    are present (per DATA_CONTRACT.md line 69).
    """
    assert CATALOG_PATH.exists(), (
        f"data/known-loans.yml missing at {CATALOG_PATH}; "
        f"Plan 09-05 must commit the Reference Layer catalog."
    )

    catalog = yaml.safe_load(CATALOG_PATH.read_text())
    assert isinstance(catalog, dict), (
        f"catalog root must be a YAML mapping; got {type(catalog).__name__}"
    )

    # Reference Layer convention (DATA_CONTRACT.md line 69)
    assert "source" in catalog, "missing top-level 'source:' key (Reference Layer convention)"
    assert "effective" in catalog, "missing top-level 'effective:' key (Reference Layer convention)"

    # PERS-07 required products
    assert "products" in catalog, "missing top-level 'products:' array"
    products = catalog["products"]
    assert isinstance(products, list), (
        f"'products' must be a YAML list; got {type(products).__name__}"
    )

    ids = {p["id"] for p in products}
    missing = REQUIRED_IDS - ids
    assert not missing, (
        f"PERS-07 violation: missing required product IDs: {sorted(missing)}; have: {sorted(ids)}"
    )

    # Per-entry schema check
    for p in products:
        entry_keys = set(p.keys())
        entry_missing = REQUIRED_PER_ENTRY_KEYS - entry_keys
        assert not entry_missing, (
            f"product {p.get('id', '<unknown>')} missing keys: {sorted(entry_missing)}"
        )

        # Decimal-string discipline (CLAUDE.md non-negotiable):
        # principal + apr must be quoted strings, not bare YAML floats.
        assert isinstance(p["principal"], str), (
            f"product {p['id']}: principal must be a quoted string "
            f"(Decimal discipline), got {type(p['principal']).__name__}"
        )
        assert isinstance(p["apr"], str), (
            f"product {p['id']}: apr must be a quoted string "
            f"(Decimal discipline), got {type(p['apr']).__name__}"
        )

        # PATTERNS Critical Issue (lib/models.py:45 Loan.loan_type Literal):
        # known-loans.yml must round-trip into the Loan Pydantic model in
        # Phase 10 routing; loan_type values MUST be drawn from the same
        # Literal options as lib.models.Loan.loan_type.
        assert p["loan_type"] in {"fixed", "arm", "fha", "va", "usda", "jumbo"}, (
            f"product {p['id']}: loan_type {p['loan_type']!r} is not a "
            f"valid lib.models.Loan.loan_type Literal option "
            f"(must be one of: fixed, arm, fha, va, usda, jumbo)"
        )
