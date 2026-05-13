"""Phase 12 Wave-4 live tests: EVAL-04 + D-12-SC3-01 + D-12-SC4-01 closed at the
metrics layer.

Plan 12-04 shipped evals/metrics.py with:
  - NumericScore enum (PASS | FAIL | SKIP) per D-12-SC4-01
  - score_numeric_match() returning the three-state enum
  - score_route_match() with Pitfall #2b cross-check (numeric_output present
    AND no subprocess invocation -> route_match fails)
  - detect_hallucinations() crediting numbers as sourced ONLY if they appear
    in STDOUT of a scripts/*.py invocation (D-12-SC3-01 — diverges from
    RESEARCH §Pattern 6 which unioned cmd args + stdin + stdout).

Requirements covered:
  - EVAL-04 + D-12-SC3-01: STDOUT-only number provenance (prose-only fails;
    cmd-arg-only fails; stdout-sourced passes)
  - D-12-SC3-01 exception: `provenance: static` numbers exempt (IRS Pub 936
    $750k cap)
  - D-12-SC4-01: NumericScore enum has exactly three members (PASS, FAIL, SKIP)
"""

from __future__ import annotations


def test_prose_only_number_fails_both_gates() -> None:
    """D-12-SC3-01: a transcript citing $1,264.14 from prose with NO script invocation
    fails BOTH numeric_match (Pitfall #2: hallucinated number) AND route_match
    (Pitfall #2b: parroted number with no script)."""
    from evals.metrics import (
        NumericScore,
        score_numeric_match,
        score_route_match,
    )

    expected = {
        "expected_numbers": [
            {
                "label": "monthly_pi",
                "value": "1264.14",
                "tolerance": "0.005",
                "provenance": "stdout",
            }
        ],
        "expected_scripts": [{"script": "amortize.py", "args_must_include": ["--input"]}],
        "expected_route_keywords": ["amortize"],
    }
    sub_calls: list[dict[str, object]] = []  # no subprocess invocation
    assert (
        score_numeric_match("Your payment is $1,264.14", expected, sub_calls)
        == NumericScore.FAIL
    )
    assert (
        score_route_match("Your payment is $1,264.14", expected, sub_calls) is False
    )


def test_stdout_sourced_number_passes_both_gates() -> None:
    """D-12-SC3-01: number cited AFTER scripts/amortize.py stdout passes."""
    from evals.metrics import (
        NumericScore,
        score_numeric_match,
        score_route_match,
    )

    sub_calls = [
        {
            "type": "subprocess",
            "cmd": [
                "python",
                ".claude/skills/mortgage-ops/scripts/amortize.py",
                "--input",
                "/tmp/x.json",
            ],
            "stdin": (
                '{"loan": {"principal": "200000.00", "annual_rate": "0.065", '
                '"term_months": 360}}'
            ),
            "stdout": '{"monthly_pi": "1264.14"}',
            "stderr": "",
            "returncode": 0,
        }
    ]
    expected = {
        "expected_numbers": [
            {
                "label": "monthly_pi",
                "value": "1264.14",
                "tolerance": "0.005",
                "provenance": "stdout",
            }
        ],
        "expected_scripts": [{"script": "amortize.py", "args_must_include": ["--input"]}],
        "expected_route_keywords": ["amortize"],
    }
    assert (
        score_numeric_match("Your payment is $1,264.14", expected, sub_calls)
        == NumericScore.PASS
    )
    assert (
        score_route_match("Your payment is $1,264.14", expected, sub_calls) is True
    )


def test_cmd_arg_only_number_fails_numeric_match() -> None:
    """D-12-SC3-01: a number that appears ONLY in cmd args (NOT stdout) must NOT
    be credited. Diverges from RESEARCH §Pattern 6 which accepted cmd args. This
    is the tightening."""
    from evals.metrics import (
        NumericScore,
        score_numeric_match,
    )

    sub_calls = [
        {
            "type": "subprocess",
            "cmd": [
                "python",
                "scripts/amortize.py",
                "--principal",
                "400000.00",
                "--rate",
                "0.065",
            ],
            "stdin": "",
            "stdout": '{"monthly_pi": "2528.27"}',  # only this number is sourced
            "stderr": "",
            "returncode": 0,
        }
    ]
    # Model echoed 400000.00 from cmd args, not from stdout
    expected = {
        "expected_numbers": [
            {
                "label": "monthly_pi",
                "value": "400000.00",
                "tolerance": "0.005",
                "provenance": "stdout",
            }
        ],
    }
    assert (
        score_numeric_match("Principal: $400,000.00", expected, sub_calls)
        == NumericScore.FAIL
    )


def test_static_provenance_number_exempt_from_stdout_rule() -> None:
    """D-12-SC3-01 exception: numbers tagged `provenance: static` are exempt
    (e.g. IRS Pub 936 $750k cap)."""
    from evals.metrics import (
        NumericScore,
        score_numeric_match,
    )

    sub_calls: list[dict[str, object]] = []  # no subprocess; static citation only
    expected = {
        "expected_numbers": [
            {
                "label": "irs_cap",
                "value": "750000.00",
                "tolerance": "0.005",
                "provenance": "static",
            }
        ],
    }
    assert (
        score_numeric_match(
            "The IRS Pub 936 cap is $750,000.00", expected, sub_calls
        )
        == NumericScore.PASS
    )


def test_score_numeric_match_returns_three_state_enum() -> None:
    """D-12-SC4-01: score_numeric_match returns one of NumericScore.{PASS, FAIL, SKIP}."""
    from evals.metrics import NumericScore

    # Just enum-shape pinning; semantic tests live in the 4 stubs above
    assert set(NumericScore) == {NumericScore.PASS, NumericScore.FAIL, NumericScore.SKIP}
