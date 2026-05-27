"""Shared CLI helpers for JSON-in/JSON-out scripts (Phase 3 D-19 / WR-02 closure inheritance).

Phase 5 introduced this module when factoring _find_json_float_loc out of
scripts/amortize.py + scripts/affordability.py to a single source of truth
(RESEARCH Q8 + Plan-Checker note line 480).

Phase 10 may relocate to .claude/skills/mortgage-ops/scripts/_cli_helpers.py
following the script-relocation pattern; Phase 5 keeps it at project root
per D-17 portability.

Note: scripts/ is NOT a Python package by project convention (no __init__.py);
consumers import from scripts._cli_helpers AFTER inserting project root into
sys.path inside their main() body (Phase 3 / Phase 4 sys.path-injection idiom).
"""

from __future__ import annotations

import json
from typing import Any

DECIMAL_JSON_NUMBER_FIELDS = frozenset(
    {
        "actual_residual_income",
        "annual_rate",
        "apor",
        "apr",
        "assumed_index_rate",
        "assumed_ltv_pct",
        "assumed_monthly_mi",
        "auto",
        "balance",
        "cash_out_amount",
        "closing_costs",
        "credit_cards",
        "cumulative_interest",
        "cumulative_principal",
        "current_balance",
        "current_housing_payment",
        "delta_vs_baseline_monthly",
        "delta_vs_baseline_pct",
        "discount_rate_annual",
        "disclosed_apr",
        "down_payment",
        "dti_threshold",
        "extra_principal",
        "finance_charges",
        "financed_loan_amount",
        "floor_rate",
        "fred_15_override",
        "fred_30_override",
        "gross_monthly_income",
        "highest_rate",
        "implied_pi",
        "insurance_monthly",
        "interest",
        "junior_liens",
        "loan_amount",
        "marginal_tax_rate",
        "max_dti",
        "max_loan_amount",
        "max_payment",
        "monthly_mi",
        "monthly_pi",
        "monthly_pmi",
        "monthly_savings",
        "new_annual_rate",
        "new_loan_monthly_pi_override",
        "new_principal",
        "note_rate",
        "old_annual_rate",
        "old_loan_balance",
        "other",
        "payment",
        "piti",
        "points_cost",
        "principal",
        "property_tax_monthly",
        "property_value",
        "rates",
        "reductions",
        "student_loans",
        "target_ltv_pct",
        "total_gross_monthly_income",
        "total_interest",
        "total_monthly_debts",
        "unit_period_fraction",
        "value",
    }
)


def _path_targets_decimal_field(path: list[str | int]) -> bool:
    for part in reversed(path):
        if isinstance(part, str):
            return part in DECIMAL_JSON_NUMBER_FIELDS
    return False


def find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    """Walk parsed JSON and return the first JSON number used for a Decimal field.

    Pydantic v2 strict mode accepts JSON numbers for Decimal fields by design
    (https://docs.pydantic.dev/2.13/concepts/json/#json-parsing) — JSON has no
    distinct decimal type, so Pydantic permissively coerces JSON numbers. But
    the project's money-discipline contract (CLAUDE.md FND-01) and D-19 require
    money/rate fields to be JSON STRINGS (e.g. "400000.00"). So we pre-parse
    with `parse_float=Decimal` to mark JSON-numbers-with-decimal-points as
    Decimal instances, then walk the parsed tree to find the first Decimal or
    integer JSON number at a known Decimal field path. Its loc-path identifies
    the offending field.

    Returns None if the input has no offending JSON numbers or fails JSON parsing
    (in the latter case, Pydantic surfaces its canonical error downstream).

    Lifted verbatim from scripts/amortize.py:70-123 + scripts/affordability.py:70-123
    (byte-identical) on 2026-04-30 per Phase 5 D-discretion factor-extract.
    """
    from decimal import Decimal as _Decimal  # local-import: keeps --help fast (D-18)

    try:
        parsed = json.loads(raw, parse_float=_Decimal)
    except json.JSONDecodeError:
        return None

    # WR-05: iterative LIFO walker (was recursive). Recursion overflowed Python's default
    # `sys.getrecursionlimit()` (~1000) on pathological deep-JSON inputs, raising an
    # uncaught RecursionError instead of the documented {"error": ...} envelope.
    # We push children in REVERSED order so that LIFO pop visits keys/indices in the
    # original dict-insertion / list-positional order — preserving the recursive
    # walker's depth-first contract pinned by test_multiple_floats_returns_first_depth_first.
    stack: list[tuple[Any, list[str | int]]] = [(parsed, [])]
    while stack:
        node, path = stack.pop()
        if isinstance(node, _Decimal):
            return (path, str(node))
        if (
            isinstance(node, int)
            and not isinstance(node, bool)
            and _path_targets_decimal_field(path)
        ):
            return (path, str(node))
        if isinstance(node, dict):
            for k, v in reversed(list(node.items())):
                stack.append((v, [*path, k]))
        elif isinstance(node, list):
            for i in range(len(node) - 1, -1, -1):
                stack.append((node[i], [*path, i]))
    return None


def make_decimal_type_envelope(
    loc: list[str | int],
    input_str: str,
) -> list[dict[str, Any]]:
    """Construct the 6-key Pydantic-shape envelope for a JSON-number rejection.

    Single source of truth for the WR-02 envelope shape. Mirrors the inline
    construction at scripts/amortize.py:196-213 + scripts/affordability.py:236-273
    (byte-identical) lifted on 2026-04-30 per Phase 5 D-discretion factor-extract.

    URL pattern: the canonical Pydantic docs URL with MAJOR.MINOR computed at
    call time via lazy pydantic.VERSION import (preserves D-18 fast --help —
    pydantic must NOT load on the help path).

    Pinned by tests at:
    - tests/test_amortize.py::test_cli_rejects_float_principal
    - tests/test_affordability.py::test_cli_rejects_float_in_loan_amount
    - tests/test_arm.py::test_cli_rejects_float_principal (and 3 siblings) — Plan 05-04b
    - tests/test_cli_helpers.py (parametric coverage of this helper itself)
    """
    from pydantic import VERSION as _pydantic_version  # local-import: D-18

    _major_minor = ".".join(_pydantic_version.split(".")[:2])
    return [
        {
            "type": "decimal_type",
            "loc": loc,
            "msg": (
                "Input should be a valid decimal — JSON string required "
                "for money/rate fields per D-19 (JSON numbers are rejected "
                "at the boundary)"
            ),
            "input": input_str,
            "url": f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type",
            "ctx": {
                "class": "Decimal",
                "field_path": ".".join(str(p) for p in loc),
            },
        }
    ]
