"""REF-09 final-pass: pin `data/reference/*.yml` count at exactly 10 (Phase 2 audit).

Per CONTEXT.md D-05 (line 43): Fannie LLPA and Freddie eligibility YAMLs are
implementation-detail YAMLs that ship under RUL-02 / RUL-03, NOT new REF-IDs.
The 10-file count is:

  | YAML stem                       | Plan  | Source                              |
  | conforming-limits-2026          | 02-01 | REF-01                              |
  | fha-limits-2026                 | 02-02 | REF-02                              |
  | fha-mip-rates                   | 02-02 | REF-03                              |
  | va-funding-fees                 | 02-03 | REF-04                              |
  | va-residual-income              | 02-03 | REF-05                              |
  | usda-income-limits              | 02-04 | REF-06                              |
  | irs-pub936                      | 02-04 | REF-07                              |
  | fannie-llpa-matrix              | 02-05 | RUL-02 implementation-detail (D-05) |
  | freddie-eligibility-matrix      | 02-05 | RUL-03 implementation-detail (D-05) |
  | atr-qm-thresholds               | 02-06 | RUL-09 implementation-detail        |

If a future plan introduces a new YAML, the FIX is to update this audit
(EXPECTED_YAML_STEMS + EXPECTED_YAML_COUNT) and document the new file in the
table above — NEVER to silently add the YAML and let this test slide.
"""

from __future__ import annotations

from pathlib import Path

REF_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data" / "reference"

EXPECTED_YAML_COUNT: int = 10

EXPECTED_YAML_STEMS: frozenset[str] = frozenset(
    {
        # REF-01..07 (Phase 2 reference YAMLs, plans 02-01..02-04)
        "conforming-limits-2026",
        "fha-limits-2026",
        "fha-mip-rates",
        "va-funding-fees",
        "va-residual-income",
        "usda-income-limits",
        "irs-pub936",
        # Implementation-detail YAMLs per CONTEXT.md D-05 (plan 02-05)
        "fannie-llpa-matrix",
        "freddie-eligibility-matrix",
        # Implementation-detail YAML for RUL-09 (plan 02-06)
        "atr-qm-thresholds",
    }
)


def test_reference_yaml_count_pinned_to_expected() -> None:
    """The Phase 2 audit pins `data/reference/*.yml` count at exactly EXPECTED_YAML_COUNT.

    A drift in either direction must fail loud. New YAMLs require a deliberate
    update to this audit, not a silent addition.
    """
    actual = sorted(p.stem for p in REF_DIR.glob("*.yml"))
    assert len(actual) == EXPECTED_YAML_COUNT, (
        f"data/reference/*.yml count drift: expected {EXPECTED_YAML_COUNT}, got {len(actual)}.\n"
        f"Actual stems: {actual}\n"
        f"If you intentionally added or removed a YAML, update EXPECTED_YAML_STEMS + "
        f"EXPECTED_YAML_COUNT in this file and document the change in the docstring."
    )


def test_reference_yaml_stems_match_expected_set() -> None:
    """Every expected YAML stem is present; no unexpected stems exist.

    Catches the case where two YAMLs are renamed but the count happens to balance.
    """
    actual = frozenset(p.stem for p in REF_DIR.glob("*.yml"))
    missing = EXPECTED_YAML_STEMS - actual
    unexpected = actual - EXPECTED_YAML_STEMS
    assert not missing, (
        f"Expected YAMLs missing from data/reference/: {sorted(missing)}.\n"
        f"This audit was last updated for a 10-YAML phase set; one or more shipped YAMLs are gone."
    )
    assert not unexpected, (
        f"Unexpected YAMLs in data/reference/: {sorted(unexpected)}.\n"
        f"If these are intentional, update EXPECTED_YAML_STEMS in this file. "
        f"Do NOT silently add YAMLs without updating the audit."
    )
