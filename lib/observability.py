"""Operational observability for mortgage-ops CLIs.

Standard (user-approved): Python stdlib ``logging`` + JSON formatter. Logs go
to **stderr** and a **per-run JSONL file** under ``data/logs/<cli>/<run_id>.jsonl``.

**stdout MUST stay clean** -- only the existing machine-readable JSON envelopes
that callers parse. Observability is strictly a side channel.

Public surface
==============

- :class:`RunContext` (frozen dataclass): ``run_id``, ``started_at``, ``cli``,
  ``input_hash``, ``log_path``. Carries a mutable wrapper internally so
  CLIs can stash the canonical output payload via :meth:`RunContext.set_output`
  before the context manager emits the final ``run_complete`` event.
- :func:`observe`: context manager that wraps a CLI invocation. On enter it
  assigns a fresh ``run_id``, hashes the canonical input, opens the JSONL
  file logger + a stderr handler, and emits ``run_started``. On exit it
  emits ``run_complete`` (or ``run_error`` if an unhandled exception escapes)
  with ``duration_ms``, ``output_hash``, ``warning_count``, ``exit_status``.
- :func:`log_event`: structured logger that emits one JSONL record per call.
- :func:`sha256_json`: canonical-JSON (sorted keys, no whitespace) sha256 hex
  digest. Used to hash both the input snapshot and the output payload so a
  caller can correlate a logged run with the JSON it observed on stdout.

Constraints
-----------

- **Stdlib only.** No third-party dependencies.
- ``data/logs/`` is created on demand; parents are mkdir'd as needed.
- The stderr handler emits the **same JSON lines** so CI and humans see the
  identical record that lands in the file -- **gated** on the
  ``MORTGAGE_OPS_LOG_STDERR`` env var (default off). Reason: the project's
  existing CLI tests parse ``result.stderr`` as a single Pydantic
  ValidationError envelope (the 6-key WR-02 contract); unconditionally
  appending JSONL log lines to stderr would break that contract for every
  downstream consumer. Operators who want live tailing set the env var.
- Decimal / money values logged via :func:`log_event` are stringified by the
  JSON encoder (canonical Decimal repr), never converted to floats.
- ``exit_status`` on the final event is one of ``"success"``,
  ``"error_validation"``, or ``"error_unexpected"``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

# Project root resolution: lib/observability.py -> lib/ -> repo root.
# The default log directory is anchored at <repo_root>/data/logs/ so
# every CLI (regardless of cwd) writes to the same shared location.
# Tests can override via the MORTGAGE_OPS_LOG_DIR env var so a tmp_path
# absorbs the writes instead of polluting the real data/logs/.
_REPO_ROOT: Path = Path(__file__).resolve().parents[1]
_LOG_DIR_ENV: str = "MORTGAGE_OPS_LOG_DIR"
_LOG_STDERR_ENV: str = "MORTGAGE_OPS_LOG_STDERR"
_DEFAULT_LOG_DIR: Path = _REPO_ROOT / "data" / "logs"


def _resolve_log_dir() -> Path:
    """Return the active log root directory.

    Honors the ``MORTGAGE_OPS_LOG_DIR`` environment variable so tests can
    redirect writes to a tmp_path without polluting the real
    ``data/logs/``. Resolved on every call so per-test monkeypatching of
    the env var works without import-time caching.
    """
    override = os.environ.get(_LOG_DIR_ENV)
    if override:
        return Path(override)
    return _DEFAULT_LOG_DIR


# ---------------------------------------------------------------------------
# Canonical JSON encoding + hashing
# ---------------------------------------------------------------------------


class _CanonicalJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, datetime, Path, and pydantic-style objects.

    - ``Decimal`` -> canonical str (e.g., ``Decimal("0.065")`` -> ``"0.065"``);
      never a float. This preserves the money-discipline contract: dollar /
      rate values logged here keep their exact textual form.
    - ``datetime`` -> ISO-8601 string (UTC ``Z`` suffix when tzinfo is UTC).
    - ``Path`` -> ``str(path)``.
    - Anything else falls back to ``repr()`` so a stray object never breaks
      a log emission. Logging that crashes the run is worse than logging
      that emits a degraded representation.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat().replace("+00:00", "Z")
        if isinstance(o, Path):
            return str(o)
        # set/frozenset -> list (sorted for determinism)
        if isinstance(o, (set, frozenset)):
            return sorted(o, key=repr)
        if isinstance(o, bytes):
            return o.decode("utf-8", errors="replace")
        return repr(o)


def sha256_json(payload: Any) -> str:
    """Return the sha256 hex digest of the canonical-JSON encoding of ``payload``.

    Canonical-JSON here means: sorted keys, no whitespace between tokens
    (``separators=(",", ":")``), Decimals/datetimes/Paths handled by
    :class:`_CanonicalJSONEncoder`. Equivalent dicts with different key
    insertion orders produce the same digest.
    """
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        cls=_CanonicalJSONEncoder,
        ensure_ascii=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# RunContext + mutable output slot
# ---------------------------------------------------------------------------


@dataclass
class _OutputSlot:
    """Mutable container for the output payload.

    ``RunContext`` is a frozen dataclass so callers cannot accidentally
    overwrite its load-bearing identity fields (``run_id``, ``started_at``,
    ``log_path``). The output payload, however, is set AFTER the work
    completes -- so we expose a single mutable slot via this helper that
    ``observe`` reads on exit to compute ``output_hash``.
    """

    payload: Any = None
    is_set: bool = False


@dataclass(frozen=True)
class RunContext:
    """Per-run identity + paths handed to instrumented CLI code.

    Attributes:
        run_id: UUID4 hex (32 chars). Stable identifier for the entire run;
            grep across ``data/logs/*/*.jsonl`` by this to reconstruct a
            single invocation.
        started_at: UTC datetime when ``observe`` entered.
        cli: Name of the CLI being instrumented (e.g., ``"amortize"``).
        input_hash: sha256 of the canonical-JSON encoding of the input
            snapshot passed to ``observe(inputs=...)``.
        log_path: Concrete file path of the per-run JSONL log file.
        warning_count: Mutable counter (via the internal _OutputSlot
            sibling) so the completion event can report how many WARNING
            -level events fired during the run. Exposed as a plain int
            attribute set after the run completes; do NOT increment from
            user code.
    """

    run_id: str
    started_at: datetime
    cli: str
    input_hash: str
    log_path: Path
    # Mutable companion slots (field with default_factory keeps the dataclass
    # frozen-on-identity while still allowing the output payload + counters
    # to be assigned by the context manager).
    _output_slot: _OutputSlot = field(default_factory=_OutputSlot, repr=False, compare=False)

    def set_output(self, payload: Any) -> None:
        """Stash the canonical output payload for ``output_hash`` computation.

        Call this once with the JSON envelope you printed to stdout (or the
        in-memory dict it was serialized from). On exit, ``observe`` reads
        this slot, computes :func:`sha256_json` of it, and emits the digest
        in the ``run_complete`` event so downstream tooling can correlate
        a logged run with the output a caller observed.
        """
        self._output_slot.payload = payload
        self._output_slot.is_set = True


# ---------------------------------------------------------------------------
# JSON formatter + warning counter
# ---------------------------------------------------------------------------


class _JSONFormatter(logging.Formatter):
    """Render a ``logging.LogRecord`` as one JSON line.

    The record's ``msg`` is the human-readable summary; any extra fields
    attached via ``logging.Logger.log(extra=...)`` (or our :func:`log_event`
    wrapper) are merged in at the top level. The output schema is:

        {"ts": "<iso-8601 UTC>",
         "run_id": "<hex>",
         "cli": "<name>",
         "level": "INFO" | "WARNING" | "ERROR" | ...,
         "msg": "<human readable>",
         "event": "<event-name>",
         ...per-event fields...}
    """

    def format(self, record: logging.LogRecord) -> str:
        # We don't want logging's standard attributes leaking into the JSON
        # output -- only the fields we explicitly attached via ``extra=...``.
        # ``record.__dict__`` contains both, so we filter against the known
        # logging-internal attribute names.
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "taskName",
        }
        # Filter against logging's reserved LogRecord attribute names. We
        # KEEP underscore-prefixed keys (those are caller fields that
        # ``log_event`` renamed to dodge LogRecord collisions like
        # ``filename``; see ``_RESERVED_LOGRECORD_ATTRS`` in ``log_event``).
        extras: dict[str, Any] = {k: v for k, v in record.__dict__.items() if k not in reserved}
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        payload.update(extras)
        return json.dumps(payload, cls=_CanonicalJSONEncoder, ensure_ascii=False)


class _WarningCounter(logging.Handler):
    """Counts WARNING-level log records routed through the run's logger.

    The completion event surfaces this so a caller scanning stdout can see
    at a glance whether the run emitted any soft-failure warnings without
    grepping the JSONL file. The handler does NOT emit anything itself; it
    only increments a counter on emit().
    """

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.count: int = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.WARNING:
            self.count += 1


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


def log_event(ctx: RunContext, level: str, message: str, **fields: Any) -> None:
    """Emit one structured JSONL log line under the run's logger.

    Args:
        ctx: The active :class:`RunContext`.
        level: One of ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``,
            ``"CRITICAL"`` (case-insensitive). Anything else falls back to
            INFO.
        message: Free-form human-readable summary.
        **fields: Arbitrary structured fields merged into the JSON record.
            Conventional keys: ``event`` (short event name like
            ``"input_validated"`` or ``"output_serialized"``), plus any
            domain-specific fields a CLI cares about.

    The emitted record always carries ``ts``, ``run_id``, ``cli``,
    ``input_hash``, ``level``, ``msg`` plus the caller's extra fields.

    Keys colliding with Python's logging LogRecord internal attributes
    (``filename``, ``name``, ``module``, ``lineno``, ``message``, etc.) are
    auto-prefixed with ``"_"`` to avoid the ``KeyError("Attempt to
    overwrite ... in LogRecord")`` that the stdlib raises. The renamed key
    still lands in the JSON output (with the underscore prefix) so the
    caller's intent survives.
    """
    logger = logging.getLogger(_logger_name(ctx.cli, ctx.run_id))
    numeric = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    # Merge the per-run identity into the record so every line carries the
    # correlation keys. Avoids requiring callers to pass them on every call.
    extras: dict[str, Any] = {
        "run_id": ctx.run_id,
        "cli": ctx.cli,
        "input_hash": ctx.input_hash,
    }
    # Sanitize caller-supplied keys against logging's reserved attribute set.
    # Without this guard, passing ``filename=...`` (a natural field name when
    # logging an OSError with .filename) raises KeyError inside
    # ``Logger.makeRecord`` and aborts the run mid-flight.
    for key, value in fields.items():
        if key in _RESERVED_LOGRECORD_ATTRS:
            extras[f"_{key}"] = value
        else:
            extras[key] = value
    logger.log(numeric, message, extra=extras)


# Pre-computed set of LogRecord attribute names that ``logger.log(extra=...)``
# refuses to let callers overwrite. Source: CPython's Logger.makeRecord. We
# rename any caller-supplied key in this set to avoid the runtime KeyError.
_RESERVED_LOGRECORD_ATTRS: frozenset[str] = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
        "asctime",
    }
)


def _logger_name(cli: str, run_id: str) -> str:
    """Compose the per-run logger name.

    Each run gets its own logger so handlers are scoped to that run only;
    cleanup at exit just detaches them. The dotted-prefix keeps the names
    grep-friendly when multiple runs interleave inside a single process.
    """
    return f"mortgage_ops.observability.{cli}.{run_id}"


# ---------------------------------------------------------------------------
# observe — the main context manager
# ---------------------------------------------------------------------------


@contextmanager
def observe(cli: str, inputs: dict[str, Any]) -> Iterator[RunContext]:
    """Wrap a CLI invocation with structured per-run logging.

    On enter:
      - assigns a fresh UUID4 ``run_id``;
      - computes the input ``sha256_json`` digest;
      - opens ``data/logs/<cli>/<run_id>.jsonl`` (parents created on demand)
        with a JSON file handler;
      - attaches a stderr StreamHandler emitting the same JSON lines;
      - emits a ``run_started`` event.

    On exit:
      - if the wrapped block raised, emits a ``run_error`` event whose
        ``exit_status`` is ``"error_unexpected"`` and re-raises;
      - otherwise emits ``run_complete`` with ``exit_status="success"``,
        ``duration_ms``, ``output_hash`` (computed from the slot set via
        :meth:`RunContext.set_output`, or ``None`` if unset), and
        ``warning_count`` (count of WARNING-level events emitted during
        the run).

    The ``exit_status`` value ``"error_validation"`` is reserved for CLI
    callers that catch a Pydantic ``ValidationError`` themselves and want
    to mark the run as a validation failure rather than an unexpected
    crash. Callers express this via :func:`log_event(ctx, "ERROR", ...,
    exit_status="error_validation")`` immediately before returning the
    error exit code; the context manager prefers an explicit caller-set
    status over its own default.

    Args:
        cli: Short CLI identifier (e.g. ``"amortize"``); becomes the
            subdirectory under ``data/logs/`` and the ``cli`` field on
            every emitted event.
        inputs: Canonical input snapshot to hash. The dict is rendered
            through :class:`_CanonicalJSONEncoder` so Decimals/Paths/etc.
            don't break the hash. **Do not log secrets here** — the dict
            is hashed AND the ``input_hash`` lands in the file.
    """
    run_id = uuid.uuid4().hex
    started_at = datetime.now(UTC)
    input_hash = sha256_json(inputs)

    log_root = _resolve_log_dir() / cli
    log_path = log_root / f"{run_id}.jsonl"

    # Build a dedicated logger per run so handlers are scoped + easy to
    # detach on exit. Parents will not propagate to the root logger so we
    # never accidentally inherit stray handlers (e.g., pytest's caplog).
    logger_name = _logger_name(cli, run_id)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = _JSONFormatter()
    try:
        log_root.mkdir(parents=True, exist_ok=True)
        file_handler: logging.Handler = logging.FileHandler(
            str(log_path), mode="w", encoding="utf-8"
        )
    except OSError:
        file_handler = logging.NullHandler()
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    # Warning counter — reads emit calls; never emits itself.
    warning_counter = _WarningCounter()
    # Stderr handler — same JSON lines visible in CI / terminal. Gated on
    # MORTGAGE_OPS_LOG_STDERR=1 because every CLI's existing test suite
    # parses ``result.stderr`` as a single Pydantic ValidationError envelope
    # (WR-02 6-key contract); unconditionally appending JSONL log lines on
    # stderr would break that contract. Operators tailing logs in dev set
    # the env var; CI keeps it off.
    stderr_handler: logging.Handler | None = None
    if os.environ.get(_LOG_STDERR_ENV):
        stderr_handler = logging.StreamHandler(stream=sys.stderr)
        stderr_handler.setLevel(logging.INFO)
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)
    logger.addHandler(file_handler)
    logger.addHandler(warning_counter)

    ctx = RunContext(
        run_id=run_id,
        started_at=started_at,
        cli=cli,
        input_hash=input_hash,
        log_path=log_path,
    )

    # Track explicit exit_status set via log_event(... exit_status=...).
    # We do NOT rely on _output_slot for this because a caller may want to
    # mark the run as a validation failure even when they did set_output.
    explicit_exit_status: dict[str, str] = {}

    # Hijack log_event so a caller-provided exit_status field is captured
    # for use in the final completion event. We do this by attaching a
    # filter that scrapes the field; logging filters are a clean way to
    # observe-without-mutate the records flowing through.
    class _ExitStatusFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            es = getattr(record, "exit_status", None)
            if isinstance(es, str):
                explicit_exit_status["value"] = es
            return True

    logger.addFilter(_ExitStatusFilter())

    start_perf = time.perf_counter()
    log_event(
        ctx,
        "INFO",
        "run started",
        event="run_started",
        started_at=started_at,
        log_path=log_path,
    )
    try:
        yield ctx
    except BaseException as exc:
        duration_ms = int((time.perf_counter() - start_perf) * 1000)
        log_event(
            ctx,
            "ERROR",
            "run errored",
            event="run_error",
            exit_status="error_unexpected",
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
            error_message=str(exc),
            warning_count=warning_counter.count,
        )
        # Detach handlers BEFORE re-raise so the file handle is released
        # cleanly; otherwise a long-running parent process could keep an
        # open file descriptor around indefinitely on Windows.
        _detach(logger, _active_handlers(stderr_handler, file_handler, warning_counter))
        raise
    else:
        duration_ms = int((time.perf_counter() - start_perf) * 1000)
        output_payload = ctx._output_slot.payload if ctx._output_slot.is_set else None
        output_hash = sha256_json(output_payload) if ctx._output_slot.is_set else None
        exit_status = explicit_exit_status.get("value", "success")
        log_event(
            ctx,
            "INFO" if exit_status == "success" else "ERROR",
            "run complete",
            event="run_complete",
            exit_status=exit_status,
            duration_ms=duration_ms,
            output_hash=output_hash,
            warning_count=warning_counter.count,
        )
        _detach(logger, _active_handlers(stderr_handler, file_handler, warning_counter))


def _active_handlers(
    stderr_handler: logging.Handler | None,
    file_handler: logging.Handler,
    warning_counter: logging.Handler,
) -> list[logging.Handler]:
    """Compose the list of handlers to detach on exit.

    The stderr handler is optional (gated on env var); the file handler and
    warning counter are always present. Helper exists so the detach call
    sites read cleanly under both gated configurations.
    """
    handlers: list[logging.Handler] = [file_handler, warning_counter]
    if stderr_handler is not None:
        handlers.append(stderr_handler)
    return handlers


def _detach(logger: logging.Logger, handlers: list[logging.Handler]) -> None:
    """Remove + close every handler/filter from ``logger``.

    Closing the file handler flushes any buffered records so the JSONL
    file is consistent on disk before the context manager returns. This
    is important for tests that subprocess-invoke a CLI and immediately
    open the log file -- without an explicit close, the last events may
    still be buffered in the StreamHandler when the test reads.
    """
    for h in handlers:
        try:
            logger.removeHandler(h)
            h.close()
        except Exception:
            # Handler cleanup MUST NOT break the caller. If close() raises
            # we still want the next handler to be detached. The original
            # exception is intentionally swallowed; the run is already
            # over.
            pass
    for f in list(logger.filters):
        with suppress(Exception):
            logger.removeFilter(f)
    logging.Logger.manager.loggerDict.pop(logger.name, None)
