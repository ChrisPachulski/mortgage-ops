"""Phase 12 eval scoring module.

Pure functions; no I/O. Imported by evals/runner.py.

Three contracts pinned by CONTEXT.md D-12-* locks:

  D-12-SC4-01: score_numeric_match returns NumericScore.{PASS | FAIL | SKIP}.
  The aggregator in evals/runner.py filters SKIP out of the gate denominator
  (numeric_match_rate = pass / (pass + fail)).

  D-12-SC3-01: detect_hallucinations + score_route_match credit numbers as
  "sourced" ONLY if they appear in the STDOUT of a scripts/*.py invocation.
  Diverges from RESEARCH §Pattern 6 (which accepted cmd args + stdin).
  Exception: expected_numbers entries with `provenance: static` are exempt
  (e.g., IRS Pub 936 $750,000 cap is a static citation, not a computed number).

  D-12-SC4-01 + D-12-SC3-01 interaction: route_match cross-check — if model
  response contains numeric output AND no subprocess invocation occurred,
  the prompt fails BOTH numeric_match (Pitfall #2: hallucinated number) AND
  route_match (Pitfall #2b: parroted number with no script).

Money discipline (CLAUDE.md inherited):
  - All numeric comparisons use Decimal (constructed from strings).
  - tolerance values are JSON strings parsed via Decimal(...).
  - NUMBER_REGEX returns string matches; normalize_num converts to Decimal.
"""

from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from typing import Any

NUMBER_REGEX: re.Pattern[str] = re.compile(r"\$?(\d{1,3}(?:,\d{3})*|\d+)\.\d{1,4}\b")
"""Matches $1,234.56 / 1234.56 / $0.50. Requires at least one decimal digit
to avoid matching integers (term_months=360 etc.). Documented in
RESEARCH §Pattern 6 line 451; lifted verbatim."""

DEFAULT_TOLERANCE: Decimal = Decimal("0.005")
"""Half-cent slack for last-digit rounding (Phase 3 quantize-to-cent ± 0.005)."""


class NumericScore(StrEnum):
    """D-12-SC4-01: three-state scorer.

    PASS — model response cited the expected number within tolerance AND
           (provenance != 'static' → number also appears in some subprocess STDOUT)
    FAIL — model response missing the expected number OR number unsourced
    SKIP — expected oracle is TBD (numeric_status='skip' OR expected_numbers==[])
    """

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


def normalize_num(s: str) -> Decimal:
    """`$1,234.56` → Decimal('1234.56'). Strips `$` and `,` thousands separators."""
    cleaned = s.replace("$", "").replace(",", "")
    return Decimal(cleaned)


def extract_numbers(text: str) -> set[Decimal]:
    """Return the set of numeric tokens in text, normalized to Decimal."""
    return {normalize_num(m.group(0)) for m in NUMBER_REGEX.finditer(text)}


def _sourced_via_stdout(
    target: Decimal,
    tolerance: Decimal,
    subprocess_calls: list[dict[str, Any]],
) -> bool:
    """D-12-SC3-01: True iff target appears (within tolerance) in some subprocess STDOUT.

    Tightening vs RESEARCH §Pattern 6: cmd args + stdin are NOT credited.
    Only `call.get("stdout", "")` is searched.
    """
    for call in subprocess_calls:
        if call.get("type") != "subprocess":
            continue
        stdout_nums = extract_numbers(str(call.get("stdout", "")))
        if any(abs(n - target) <= tolerance for n in stdout_nums):
            return True
    return False


def score_numeric_match(
    model_response: str,
    expected: dict[str, Any],
    subprocess_calls: list[dict[str, Any]],
) -> NumericScore:
    """D-12-SC4-01 + D-12-SC3-01 three-state scorer.

    Returns:
      SKIP if expected.numeric_status == "skip" OR expected.expected_numbers == [].
      PASS if every expected_number:
        - appears in model_response within its `tolerance`
        - AND (provenance == "static" OR appears in some subprocess STDOUT)
      FAIL otherwise.
    """
    # SKIP gate per D-12-SC4-01
    if expected.get("numeric_status") == "skip":
        return NumericScore.SKIP
    expected_numbers = expected.get("expected_numbers") or []
    if not expected_numbers:
        return NumericScore.SKIP

    response_nums = extract_numbers(model_response)

    for entry in expected_numbers:
        target = Decimal(str(entry["value"]))
        tolerance = Decimal(str(entry.get("tolerance", DEFAULT_TOLERANCE)))
        provenance = entry.get("provenance", "stdout")

        # Check 1: target appears in response within tolerance
        if not any(abs(n - target) <= tolerance for n in response_nums):
            return NumericScore.FAIL

        # Check 2: D-12-SC3-01 source requirement
        if provenance == "static":
            continue  # exempt from STDOUT-only rule
        if not _sourced_via_stdout(target, tolerance, subprocess_calls):
            return NumericScore.FAIL

    return NumericScore.PASS


def score_route_match(
    model_response: str,
    expected: dict[str, Any],
    subprocess_calls: list[dict[str, Any]],
) -> bool:
    """Route-match: did the agent invoke the right scripts AND mention the right keywords?

    D-12-SC3-01 Pitfall #2b cross-check: if model_response contains ANY numeric
    output AND no subprocess invocation occurred, route_match FAILS (the model
    parroted a number without computing it).

    Returns True iff:
      - every expected_route_keyword appears in response OR in some subprocess.cmd[*]
      - AND every expected_scripts entry has a matching subprocess invocation
        (script name in cmd AND args_must_include flags all present)
      - AND Pitfall #2b check passes: numeric output present → subprocess invocation present
    """
    sub_calls = [c for c in subprocess_calls if c.get("type") == "subprocess"]

    # D-12-SC3-01 Pitfall #2b cross-check
    has_numeric_output = bool(extract_numbers(model_response))
    has_any_subprocess = len(sub_calls) > 0
    if has_numeric_output and not has_any_subprocess:
        return False

    # Keyword check (substring match against response OR cmd args)
    for kw in expected.get("expected_route_keywords", []) or []:
        in_response = kw in model_response
        in_cmd = any(kw in " ".join(map(str, c.get("cmd", []))) for c in sub_calls)
        if not in_response and not in_cmd:
            return False

    # Script invocation check
    for spec in expected.get("expected_scripts", []) or []:
        script_name = spec.get("script", "")
        matching = [
            c
            for c in sub_calls
            if any(script_name in str(arg) for arg in c.get("cmd", []))
        ]
        if not matching:
            return False
        for must_inc in spec.get("args_must_include", []) or []:
            if not any(must_inc in c.get("cmd", []) for c in matching):
                return False

    return True


def detect_hallucinations(
    model_response: str,
    subprocess_calls: list[dict[str, Any]],
    tolerance: Decimal = DEFAULT_TOLERANCE,
) -> list[Decimal]:
    """D-12-SC3-01: return the list of numbers in model_response that do NOT appear
    in any subprocess STDOUT (Pitfall #2 detector — tightened).

    Diverges from RESEARCH §Pattern 6:
      - RESEARCH unioned stdout + cmd + stdin → ACCEPTED cmd args (false positives)
      - D-12-SC3-01: STDOUT-only

    Returns the offending numbers (empty list = no hallucinations detected).
    """
    response_nums = extract_numbers(model_response)
    stdout_nums: set[Decimal] = set()
    for call in subprocess_calls:
        if call.get("type") != "subprocess":
            continue
        stdout_nums.update(extract_numbers(str(call.get("stdout", ""))))

    return [
        n
        for n in response_nums
        if not any(abs(n - s) <= tolerance for s in stdout_nums)
    ]
