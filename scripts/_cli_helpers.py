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


def find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    """Walk parsed JSON and return (loc-path, decimal-string) of the first JSON float.

    Pydantic v2 strict mode accepts JSON numbers for Decimal fields by design
    (https://docs.pydantic.dev/2.13/concepts/json/#json-parsing) — JSON has no
    distinct decimal type, so Pydantic permissively coerces JSON numbers. But
    the project's money-discipline contract (CLAUDE.md FND-01) and D-19 require
    money/rate fields to be JSON STRINGS (e.g. "400000.00"). So we pre-parse
    with `parse_float=Decimal` to mark JSON-numbers-with-decimal-points as
    Decimal instances, then walk the parsed tree to find the first Decimal —
    its loc-path identifies the offending field.

    Returns None if the input has no JSON floats or fails JSON parsing
    (in the latter case, Pydantic surfaces its canonical error downstream).

    Lifted verbatim from scripts/amortize.py:70-123 + scripts/affordability.py:70-123
    (byte-identical) on 2026-04-30 per Phase 5 D-discretion factor-extract.
    """
    from decimal import Decimal as _Decimal  # local-import: keeps --help fast (D-18)

    try:
        parsed = json.loads(raw, parse_float=_Decimal)
    except json.JSONDecodeError:
        return None

    def _walk(node: Any, path: list[str | int]) -> tuple[list[str | int], str] | None:
        if isinstance(node, _Decimal):
            return (path, str(node))
        if isinstance(node, dict):
            for k, v in node.items():
                hit = _walk(v, [*path, k])
                if hit is not None:
                    return hit
        elif isinstance(node, list):
            for i, v in enumerate(node):
                hit = _walk(v, [*path, i])
                if hit is not None:
                    return hit
        return None

    return _walk(parsed, [])


def make_decimal_type_envelope(
    loc: list[str | int],
    input_str: str,
) -> list[dict[str, Any]]:
    """Construct the 6-key Pydantic-shape envelope for a JSON-float rejection.

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
                "for money/rate fields per D-19 (JSON floats are rejected "
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
