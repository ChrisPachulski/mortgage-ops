"""Phase 2 final-pass smoke: every predicate imports and returns sensibly.

Catches "predicate B silently broke when predicate A's YAML changed shape"
regressions that per-predicate test files miss because they each load only
ONE module.

Pins the predicate count at exactly 13 — the same set the citation-coverage
meta-test (`tests/test_rules/test_citation_coverage.py`) parametrizes over.
A drift in either direction (a predicate goes missing OR a non-predicate file
sneaks in) fails loud here.

Predicate roster (after plans 02-01..02-06 and Phase 16 reference-data ship):

  | Plan  | Module                              |
  | 02-01 | lib.rules.loan_type                 |
  | 02-02 | lib.rules.fha_mip                   |
  | 02-03 | lib.rules.va_funding_fee            |
  | 02-03 | lib.rules.va_residual_income        |
  | 02-04 | lib.rules.usda                      |
  | 02-04 | lib.rules.irs_pub936                |
  | 02-05 | lib.rules.conventional_pmi          |
  | 02-05 | lib.rules.fannie_eligibility        |
  | 02-05 | lib.rules.freddie_eligibility       |
  | 02-06 | lib.rules.atr_qm                    |
  | 02-06 | lib.rules.reg_z                     |
  | 16-01 | lib.rules.pmi                       |
  | 16-01 | lib.rules.insurance                 |
"""

from __future__ import annotations

import importlib
from pathlib import Path

EXPECTED_PREDICATE_COUNT: int = 13

EXPECTED_PREDICATE_MODULES: tuple[str, ...] = (
    "lib.rules.loan_type",
    "lib.rules.fha_mip",
    "lib.rules.va_funding_fee",
    "lib.rules.va_residual_income",
    "lib.rules.usda",
    "lib.rules.irs_pub936",
    "lib.rules.conventional_pmi",
    "lib.rules.fannie_eligibility",
    "lib.rules.freddie_eligibility",
    "lib.rules.atr_qm",
    "lib.rules.reg_z",
    "lib.rules.pmi",
    "lib.rules.insurance",
)

NON_PREDICATE_FILES: frozenset[str] = frozenset({"__init__.py", "_loader.py", "types.py"})

RULES_DIR: Path = Path(__file__).resolve().parent.parent.parent / "lib" / "rules"


def test_expected_predicate_count_is_13() -> None:
    """Sanity check the EXPECTED_PREDICATE_MODULES tuple itself."""
    assert len(EXPECTED_PREDICATE_MODULES) == EXPECTED_PREDICATE_COUNT
    assert len(set(EXPECTED_PREDICATE_MODULES)) == EXPECTED_PREDICATE_COUNT, (
        "EXPECTED_PREDICATE_MODULES contains duplicates"
    )


def test_filesystem_predicate_count_matches_expected() -> None:
    """The actual `lib/rules/*.py` count (excluding __init__/_loader/types) is 13.

    Catches the case where a NEW predicate file was added without updating this
    audit (which means it also got a fixture but no documented home in this
    smoke roster).
    """
    actual_files = sorted(p for p in RULES_DIR.glob("*.py") if p.name not in NON_PREDICATE_FILES)
    actual_stems = sorted(p.stem for p in actual_files)
    expected_stems = sorted(m.split(".")[-1] for m in EXPECTED_PREDICATE_MODULES)
    assert actual_stems == expected_stems, (
        f"Predicate roster drift.\nActual stems in lib/rules/: {actual_stems}\n"
        f"Expected stems: {expected_stems}\n"
        f"If a new predicate landed, add it to EXPECTED_PREDICATE_MODULES + bump "
        f"EXPECTED_PREDICATE_COUNT and document it in the docstring table."
    )


def test_every_predicate_imports_cleanly() -> None:
    """Every expected predicate module imports without raising.

    Catches:
      - SyntaxError in a predicate file
      - ImportError cascade (predicate B imports from predicate A; A breaks)
      - MissingReferenceFieldError at import time (loader called too eagerly with
        a broken YAML)
      - StaleReferenceWarning is acceptable per CONTEXT.md D-12 — pytest does NOT
        promote it to error here
    """
    failures: list[tuple[str, str]] = []
    for module_name in EXPECTED_PREDICATE_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # we want every failure listed in one assertion
            failures.append((module_name, f"{type(exc).__name__}: {exc}"))
    assert not failures, "One or more predicates failed to import:\n" + "\n".join(
        f"  - {name}: {err}" for name, err in failures
    )


def test_reg_z_within_tolerance_happy_path() -> None:
    """Pure-Python predicate (no YAML); minimal happy-path calls — outside + inside.

    Hand:
      - |0.05 - 0.0515| = 0.0015 > 0.00125 (regular tolerance, §1026.22(a)(2))
        → predicate returns False (outside-tolerance branch).
      - |0.05 - 0.0501| = 0.0001 ≤ 0.00125 → predicate returns True
        (inside-tolerance branch).
    """
    from decimal import Decimal

    from lib.rules.reg_z import within_apr_tolerance

    assert (
        within_apr_tolerance(
            disclosed_apr=Decimal("0.05"),
            actual_apr=Decimal("0.0515"),
            is_irregular_transaction=False,
        )
        is False
    ), "0.0015 ABOVE regular tolerance 0.00125 → predicate returns False"

    assert (
        within_apr_tolerance(
            disclosed_apr=Decimal("0.05"),
            actual_apr=Decimal("0.0501"),
            is_irregular_transaction=False,
        )
        is True
    ), "0.0001 within regular tolerance should be True"


def test_conventional_pmi_status_happy_path() -> None:
    """Pure-Python predicate (no YAML); LTV at 0.78 -> auto_terminated.

    `status` requires a real `Loan` instance (its signature is
    `status(loan: Loan, ...)`, not `Loan | None`); pydantic strict mode
    rejects None at runtime AND mypy --strict rejects passing None where
    `Loan` is annotated. Construct a minimal Loan from `lib.models.Loan`
    (Phase 1 frozen surface) for the smoke call.
    """
    from decimal import Decimal

    from lib.models import Loan
    from lib.rules.conventional_pmi import status

    # original_property_value = 100, scheduled_balance = 78 -> LTV = 0.78
    result = status(
        loan=Loan(
            principal=Decimal("200000.00"),
            annual_rate=Decimal("0.065000"),
            term_months=360,
        ),
        scheduled_balance=Decimal("78.00"),
        original_property_value=Decimal("100.00"),
        is_high_risk=False,
    )
    assert result == "auto_terminated", (
        f"LTV exactly 0.78 should auto-terminate per HPA §4902(b); got {result!r}"
    )
