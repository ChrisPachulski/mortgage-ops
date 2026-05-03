"""Tests for scripts/_cli_helpers.py (Phase 5 D-discretion factor-extract).

These tests pin the shared JSON-float gate + 6-key envelope shape that
scripts/amortize.py, scripts/affordability.py, and scripts/arm_simulate.py
all consume. The byte-identical pre-existing inline implementations at
scripts/amortize.py:70-123 + scripts/affordability.py:70-123 are removed
in Plan 05-04a Task 3 once these tests are passing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# scripts/ is intentionally not a Python package; inject project root for imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope  # noqa: E402, I001


# =========================================================================
# find_json_float_loc
# =========================================================================


class TestFindJsonFloatLoc:
    def test_no_floats_returns_none(self) -> None:
        raw = json.dumps({"a": 1, "b": "0.05", "c": [1, 2, 3]})
        assert find_json_float_loc(raw) is None

    def test_single_float_at_top_level(self) -> None:
        raw = '{"principal": 400000.50}'
        hit = find_json_float_loc(raw)
        assert hit is not None
        loc, val = hit
        assert loc == ["principal"]
        assert val == "400000.50"

    def test_multiple_floats_returns_first_depth_first(self) -> None:
        # Dict iteration order is insertion-preserving (Python 3.7+);
        # the walk visits keys in order — "a" first, then "b".
        raw = '{"a": 1.5, "b": 2.5}'
        hit = find_json_float_loc(raw)
        assert hit is not None
        loc, _ = hit
        assert loc == ["a"]

    def test_float_in_nested_list_inside_dict(self) -> None:
        raw = '{"index_path": [{"period": 61, "value": 0.0525}]}'
        hit = find_json_float_loc(raw)
        assert hit is not None
        loc, val = hit
        assert loc == ["index_path", 0, "value"]
        assert val == "0.0525"

    def test_float_in_top_level_list(self) -> None:
        raw = "[1, 2.5, 3]"
        hit = find_json_float_loc(raw)
        assert hit is not None
        loc, val = hit
        assert loc == [1]
        assert val == "2.5"

    def test_invalid_json_returns_none(self) -> None:
        raw = '{"a": 1, "b":'  # truncated, malformed
        assert find_json_float_loc(raw) is None

    def test_empty_object_returns_none(self) -> None:
        assert find_json_float_loc("{}") is None

    def test_empty_array_returns_none(self) -> None:
        assert find_json_float_loc("[]") is None

    def test_deeply_nested_does_not_recurse(self) -> None:
        """WR-05: pathological deep-JSON input must not raise RecursionError.

        Python's default sys.getrecursionlimit() is ~1000; the previous recursive
        walker overflowed and crashed the CLI with an opaque traceback instead of
        the documented {"error": ...} envelope. The iterative LIFO walker handles
        any nesting depth bounded only by available memory.
        """
        depth = 5000  # well past Python's default recursion limit
        raw = ("[" * depth) + "1.5" + ("]" * depth)
        hit = find_json_float_loc(raw)
        assert hit is not None
        loc, val = hit
        assert val == "1.5"
        # loc is the chain of zero indices: [0, 0, 0, ..., 0]
        assert len(loc) == depth
        assert all(i == 0 for i in loc)


# =========================================================================
# make_decimal_type_envelope
# =========================================================================


class TestMakeDecimalTypeEnvelope:
    def test_returns_list_of_one(self) -> None:
        env = make_decimal_type_envelope(["loan", "principal"], "400000.5")
        assert isinstance(env, list)
        assert len(env) == 1

    def test_envelope_has_exactly_six_keys(self) -> None:
        env = make_decimal_type_envelope(["loan", "principal"], "400000.5")
        err = env[0]
        assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}

    def test_envelope_type_is_decimal_type(self) -> None:
        env = make_decimal_type_envelope(["loan", "principal"], "400000.5")
        assert env[0]["type"] == "decimal_type"

    def test_envelope_loc_round_trips(self) -> None:
        loc: list[str | int] = ["index_path", 0, "value"]
        env = make_decimal_type_envelope(loc, "0.0525")
        assert env[0]["loc"] == loc

    def test_envelope_input_round_trips(self) -> None:
        env = make_decimal_type_envelope(["principal"], "12345.67")
        assert env[0]["input"] == "12345.67"

    def test_envelope_url_pattern(self) -> None:
        env = make_decimal_type_envelope(["principal"], "1.5")
        url = env[0]["url"]
        assert url.startswith("https://errors.pydantic.dev/")
        assert url.endswith("/v/decimal_type")

    def test_envelope_url_version_matches_runtime_pydantic(self) -> None:
        from pydantic import VERSION as pv

        major_minor = ".".join(pv.split(".")[:2])
        env = make_decimal_type_envelope(["x"], "1.5")
        assert f"errors.pydantic.dev/{major_minor}/" in env[0]["url"]

    def test_envelope_ctx_class_decimal(self) -> None:
        env = make_decimal_type_envelope(["x"], "1.5")
        assert env[0]["ctx"]["class"] == "Decimal"

    def test_envelope_ctx_field_path_dot_joined(self) -> None:
        env = make_decimal_type_envelope(["loan", "principal"], "1.5")
        assert env[0]["ctx"]["field_path"] == "loan.principal"

    def test_envelope_ctx_field_path_with_int_index(self) -> None:
        env = make_decimal_type_envelope(["index_path", 0, "value"], "0.05")
        assert env[0]["ctx"]["field_path"] == "index_path.0.value"


# =========================================================================
# Round-trip
# =========================================================================


def test_round_trip_finds_float_then_emits_envelope() -> None:
    """Integration: parse JSON with a float, locate it, emit canonical envelope."""
    raw = '{"loan": {"principal": 400000.5}, "rate": "0.05"}'
    hit = find_json_float_loc(raw)
    assert hit is not None
    loc, val = hit
    env = make_decimal_type_envelope(loc, val)
    err = env[0]
    assert err["loc"] == ["loan", "principal"]
    assert err["input"] == "400000.5"
    assert err["ctx"]["field_path"] == "loan.principal"
