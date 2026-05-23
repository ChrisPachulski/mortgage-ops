"""Tests for ``lib.observability`` -- the per-run JSONL logger that wraps every CLI.

The standard (user-approved): Python stdlib logging + JSON formatter, logs to
stderr and per-run file under ``data/logs/<cli>/<run_id>.jsonl``. **stdout MUST
stay clean** -- this file's smoke test asserts the key invariant by comparing
the JSON envelope from an instrumented CLI against the same envelope shape on
``--help``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from lib.observability import RunContext, log_event, observe, sha256_json

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
AMORTIZE_SCRIPT: Path = (
    REPO_ROOT / ".claude" / "skills" / "mortgage-ops" / "scripts" / "amortize.py"
)


@pytest.fixture
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``observe`` writes to a tmp_path so we don't pollute data/logs/."""
    monkeypatch.setenv("MORTGAGE_OPS_LOG_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# sha256_json — canonical-JSON determinism
# ---------------------------------------------------------------------------


def test_sha256_json_is_deterministic_across_key_orders() -> None:
    """Two dicts with the same contents but different insertion orders hash equal."""
    a = {"loan_amount": "400000.00", "rate": "0.065", "term_months": 360}
    b = {"term_months": 360, "rate": "0.065", "loan_amount": "400000.00"}
    assert sha256_json(a) == sha256_json(b)


def test_sha256_json_distinguishes_different_payloads() -> None:
    assert sha256_json({"x": 1}) != sha256_json({"x": 2})


def test_sha256_json_handles_decimal_without_floats() -> None:
    """Money discipline: Decimal must round-trip as its canonical string form,
    NOT as a float. ``Decimal("0.10")`` and ``0.10`` are NOT the same value;
    coercing one to the other would silently corrupt hashes that the
    auditing layer relies on to correlate runs."""
    d_hash = sha256_json({"amount": Decimal("0.10")})
    s_hash = sha256_json({"amount": "0.10"})
    # str(Decimal("0.10")) == "0.10", so the two payloads canonicalize the same.
    assert d_hash == s_hash


def test_sha256_json_handles_path_and_datetime() -> None:
    """No exception when encoding stdlib types we routinely pass through inputs."""
    from datetime import UTC, datetime

    payload = {
        "path": Path("/tmp/x.json"),
        "ts": datetime(2026, 1, 1, tzinfo=UTC),
        "nested": {"frozen": frozenset({"a", "b"})},
    }
    # Just assert it doesn't raise + returns 64 hex chars.
    h = sha256_json(payload)
    assert isinstance(h, str)
    assert len(h) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", h)


# ---------------------------------------------------------------------------
# observe — RunContext + JSONL file invariants
# ---------------------------------------------------------------------------


def test_observe_assigns_uuid4_run_id(log_dir: Path) -> None:
    """run_id is UUID4 hex (32 lowercase hex chars; standard uuid4().hex form)."""
    with observe(cli="test_cli", inputs={"k": "v"}) as ctx:
        assert isinstance(ctx, RunContext)
        assert re.fullmatch(r"[0-9a-f]{32}", ctx.run_id), (
            f"run_id should be uuid4 hex; got {ctx.run_id!r}"
        )
        # spec says "24+ hex chars"; UUID4 hex is 32. Both satisfied.
        assert len(ctx.run_id) >= 24


def test_observe_log_path_uses_cli_subdir_and_run_id(log_dir: Path) -> None:
    with observe(cli="test_cli", inputs={"k": "v"}) as ctx:
        expected = log_dir / "test_cli" / f"{ctx.run_id}.jsonl"
        assert ctx.log_path == expected
        # File should already exist (handler opened on enter).
        assert ctx.log_path.is_file()


def test_observe_emits_run_started_then_run_complete_on_success(log_dir: Path) -> None:
    with observe(cli="test_cli", inputs={"k": "v"}) as ctx:
        log_path = ctx.log_path
        ctx.set_output({"result": "ok"})
    events = _read_jsonl(log_path)
    assert events[0]["event"] == "run_started"
    assert events[-1]["event"] == "run_complete"
    assert events[-1]["exit_status"] == "success"
    assert events[-1]["warning_count"] == 0
    assert events[-1]["output_hash"] == sha256_json({"result": "ok"})
    assert events[-1]["duration_ms"] >= 0


def test_observe_run_complete_without_set_output_has_null_hash(log_dir: Path) -> None:
    """If the CLI never set an output, output_hash is null (not absent, not blank)."""
    with observe(cli="test_cli", inputs={}):
        pass
    log_path = next((log_dir / "test_cli").glob("*.jsonl"))
    events = _read_jsonl(log_path)
    assert events[-1]["event"] == "run_complete"
    assert events[-1]["output_hash"] is None


def test_observe_exception_emits_run_error_and_reraises(log_dir: Path) -> None:
    class _Boom(RuntimeError):
        pass

    log_path: Path | None = None
    with pytest.raises(_Boom), observe(cli="test_cli", inputs={}) as ctx:  # noqa: PT012
        log_path = ctx.log_path
        raise _Boom("kaboom")
    assert log_path is not None
    events = _read_jsonl(log_path)
    final = events[-1]
    assert final["event"] == "run_error"
    assert final["exit_status"] == "error_unexpected"
    assert final["error_type"] == "_Boom"
    assert "kaboom" in final["error_message"]


def test_observe_logs_are_well_formed_jsonl(log_dir: Path) -> None:
    """Every line in the log file must be a parseable JSON object."""
    with observe(cli="test_cli", inputs={"x": 1}) as ctx:
        log_event(ctx, "INFO", "hello", event="midrun", k="v")
        log_event(ctx, "WARNING", "soft", event="soft_warn")
        log_path = ctx.log_path
    for line in log_path.read_text().splitlines():
        # Each line must round-trip as JSON.
        obj = json.loads(line)
        assert isinstance(obj, dict)
        # Required keys on every record.
        assert "ts" in obj
        assert "level" in obj
        assert "msg" in obj


def test_log_event_warning_count_propagates_to_run_complete(log_dir: Path) -> None:
    with observe(cli="test_cli", inputs={}) as ctx:
        log_event(ctx, "WARNING", "first warn", event="x")
        log_event(ctx, "WARNING", "second warn", event="y")
        log_event(ctx, "INFO", "not a warn", event="z")
        log_path = ctx.log_path
    events = _read_jsonl(log_path)
    final = events[-1]
    assert final["event"] == "run_complete"
    assert final["warning_count"] == 2


def test_log_event_explicit_error_validation_status(log_dir: Path) -> None:
    """A caller can mark the run as validation-failed by passing exit_status."""
    with observe(cli="test_cli", inputs={}) as ctx:
        log_event(
            ctx,
            "ERROR",
            "validation failed",
            event="validation_pydantic",
            exit_status="error_validation",
        )
        log_path = ctx.log_path
    events = _read_jsonl(log_path)
    assert events[-1]["event"] == "run_complete"
    assert events[-1]["exit_status"] == "error_validation"


def test_observe_input_hash_changes_with_inputs(log_dir: Path) -> None:
    with observe(cli="test_cli", inputs={"args": {"input": "a.json"}}) as ctx_a:
        hash_a = ctx_a.input_hash
    with observe(cli="test_cli", inputs={"args": {"input": "b.json"}}) as ctx_b:
        hash_b = ctx_b.input_hash
    assert hash_a != hash_b


def test_log_event_reserved_keys_are_renamed_not_raised(log_dir: Path) -> None:
    """Python's logging refuses ``extra=`` keys that collide with LogRecord
    attribute names (``filename``, ``module``, ``lineno`` etc.) — it raises
    ``KeyError("Attempt to overwrite ...")`` mid-flight. ``log_event`` MUST
    sanitize those keys so a CLI passing ``filename=e.filename`` from a
    FileNotFoundError doesn't abort the run."""
    with observe(cli="test_cli", inputs={}) as ctx:
        log_event(
            ctx,
            "ERROR",
            "input file not found",
            event="input_file_missing",
            filename="/tmp/does_not_exist.json",  # would collide
            module="some_module",  # would collide
        )
        log_path = ctx.log_path
    events = _read_jsonl(log_path)
    fnf_event = next(e for e in events if e.get("event") == "input_file_missing")
    # Renamed under underscore prefix so the value still lands in the JSON.
    assert fnf_event["_filename"] == "/tmp/does_not_exist.json"
    assert fnf_event["_module"] == "some_module"


def test_observe_decimal_values_logged_as_strings(log_dir: Path) -> None:
    """Money discipline: Decimal must be logged as its canonical str form,
    never coerced to float."""
    with observe(cli="test_cli", inputs={}) as ctx:
        log_event(ctx, "INFO", "money", event="m", amount=Decimal("123456.78"))
        log_path = ctx.log_path
    events = _read_jsonl(log_path)
    money_event = next(e for e in events if e.get("event") == "m")
    assert money_event["amount"] == "123456.78"
    assert isinstance(money_event["amount"], str)


# ---------------------------------------------------------------------------
# CLI smoke test — stdout unchanged invariant
# ---------------------------------------------------------------------------


def test_amortize_help_stdout_unchanged_and_no_log_dir_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--help`` is the fast path that argparse SystemExits BEFORE observe()
    runs. Therefore: (a) exit 0, (b) stdout matches the documented argparse
    output, (c) NO log file is written. This is the load-bearing invariant
    that protects every downstream consumer from accidental stdout
    pollution."""
    # Route observability writes to a tmp dir so even if observe() did run,
    # we wouldn't pollute data/logs/.
    env = os.environ.copy()
    env["MORTGAGE_OPS_LOG_DIR"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(AMORTIZE_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    # Stdout must contain the argparse usage line and not a JSON envelope.
    assert "usage: amortize" in result.stdout
    assert "--input INPUT" in result.stdout
    # The --help path must NOT print observability events anywhere (argparse
    # SystemExits before observe() is entered).
    assert "run_started" not in result.stdout
    assert "run_started" not in result.stderr
    # No log files written for --help.
    assert not (tmp_path / "amortize").exists()


def test_amortize_run_writes_log_and_keeps_stdout_and_stderr_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end smoke (default mode, stderr emission OFF):
    an actual amortize run (a) exits 0, (b) emits the schedule JSON to
    stdout (parseable as JSON, unchanged from baseline), (c) emits NOTHING
    to stderr by default -- the project's existing CLI tests parse
    ``result.stderr`` as a single Pydantic ValidationError envelope, so
    unconditionally appending JSONL log lines would break the WR-02
    contract; the stderr handler is gated on MORTGAGE_OPS_LOG_STDERR=1
    (covered by the next test), (d) the per-run log file ALWAYS lands
    under data/logs/<cli>/<run_id>.jsonl."""
    loan_input = tmp_path / "loan.json"
    loan_input.write_text(
        json.dumps(
            {
                "loan": {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                }
            }
        )
    )
    env = os.environ.copy()
    env["MORTGAGE_OPS_LOG_DIR"] = str(tmp_path / "logs")
    # Ensure stderr emission is OFF (default), not inherited from caller env.
    env.pop("MORTGAGE_OPS_LOG_STDERR", None)
    result = subprocess.run(
        [sys.executable, str(AMORTIZE_SCRIPT), "--input", str(loan_input)],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"

    # (b) stdout parses as a Schedule JSON envelope (the existing contract).
    parsed = json.loads(result.stdout)
    assert "loan" in parsed
    assert "payments" in parsed
    assert len(parsed["payments"]) == 360

    # (c) stderr is empty by default — preserves WR-02 envelope-only contract
    # that the rest of the test suite asserts via json.loads(result.stderr).
    assert result.stderr == "", f"expected clean stderr by default; got: {result.stderr!r}"

    # (d) the per-run log file landed under tmp_path/logs/amortize/<run_id>.jsonl.
    log_dir = tmp_path / "logs" / "amortize"
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) == 1
    log_file = log_files[0]
    # File contents are well-formed JSONL with run_started + run_complete.
    file_events = _read_jsonl(log_file)
    assert file_events[0]["event"] == "run_started"
    last = file_events[-1]
    assert last["event"] == "run_complete"
    assert last["exit_status"] == "success"
    assert last["output_hash"] is not None
    assert last["warning_count"] == 0
    assert last["duration_ms"] >= 0
    # Filename matches run_id.
    assert log_file.stem == last["run_id"]


def test_amortize_stderr_emission_opt_in_via_env_var(tmp_path: Path) -> None:
    """When MORTGAGE_OPS_LOG_STDERR=1 is set, the stderr handler is attached
    and emits the same JSONL lines that land in the file. Operators tailing
    logs in a dev terminal use this; CI / the rest of the test suite leave
    it unset."""
    loan_input = tmp_path / "loan.json"
    loan_input.write_text(
        json.dumps(
            {
                "loan": {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                }
            }
        )
    )
    env = os.environ.copy()
    env["MORTGAGE_OPS_LOG_DIR"] = str(tmp_path / "logs")
    env["MORTGAGE_OPS_LOG_STDERR"] = "1"
    result = subprocess.run(
        [sys.executable, str(AMORTIZE_SCRIPT), "--input", str(loan_input)],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0
    # stdout is still the Schedule envelope.
    parsed = json.loads(result.stdout)
    assert "payments" in parsed
    # stderr is JSONL — every non-empty line parses as a dict with the
    # run-correlation keys.
    stderr_lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert stderr_lines
    for line in stderr_lines:
        obj = json.loads(line)
        assert obj["cli"] == "amortize"
        assert "run_id" in obj


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse a JSONL file into a list of dicts. Skips blank lines."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
