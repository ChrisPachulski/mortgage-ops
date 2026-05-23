# Observability

Per-run structured logging for every `.claude/skills/mortgage-ops/scripts/*.py`
CLI. The standard is Python stdlib `logging` + a JSON formatter. Logs go to a
per-run JSONL file (always) and to stderr (opt-in). **stdout stays clean** --
only the existing machine-readable JSON envelopes that callers parse.

## The standard

- **Library:** `lib.observability` -- stdlib only, no third-party deps.
- **Format:** one JSON object per line (JSONL).
- **File:** `data/logs/<cli>/<run_id>.jsonl` -- one file per invocation, named
  by UUID4 hex.
- **stderr emission:** off by default. Set `MORTGAGE_OPS_LOG_STDERR=1` to mirror
  the same JSON lines to stderr for live tailing. Kept off in the default mode
  because the project's existing 6-key Pydantic ValidationError envelope (the
  WR-02 contract) is the sole contents of stderr on error -- consumers
  (`json.loads(result.stderr)`, the Phase 9 Node orchestrator, the Phase 10
  SKILL.md narration) depend on that contract.
- **stdout:** ALWAYS the same machine-readable JSON envelope each CLI emitted
  before observability landed. Observability NEVER prints to stdout. If you
  see a log line on stdout from one of these CLIs, that's a bug.

## Where logs land

```
data/logs/
  amortize/
    <uuid4-hex>.jsonl
    <uuid4-hex>.jsonl
  affordability/
    <uuid4-hex>.jsonl
  apr_reg_z/
  arm_simulate/
  fred_cli/
  points_breakeven/
  property_analyze/
  property_fetch/
  refi_npv/
  stress_test/
```

`data/logs/` is gitignored -- logs are ephemeral artifacts.

Override the root for testing or sandboxed runs via the
`MORTGAGE_OPS_LOG_DIR` env var (e.g. a `tmp_path` in pytest):

```bash
MORTGAGE_OPS_LOG_DIR=/tmp/mo-logs ./scripts/amortize.py --input loan.json
```

## How to grep for a run

Every log line carries `run_id` (UUID4 hex) and `cli`. Use `jq` to pull a
single run out of the directory tree:

```bash
# All events from one run, by UUID:
jq 'select(.run_id == "3108d5726be74aaea36830f97a4b5fae")' \
   data/logs/*/*.jsonl

# Just the run_complete events across all amortize runs in the last hour:
jq 'select(.event == "run_complete")' data/logs/amortize/*.jsonl

# All runs that ended in error_validation:
jq 'select(.event == "run_complete" and .exit_status != "success")' \
   data/logs/*/*.jsonl
```

To tail live during dev (single shell):

```bash
MORTGAGE_OPS_LOG_STDERR=1 ./scripts/affordability.py --input req.json 2>&1 \
  | jq .
```

## Event schema

Every log line includes:

| Field          | Type    | Description                                                          |
|----------------|---------|----------------------------------------------------------------------|
| `ts`           | string  | ISO-8601 UTC, `Z` suffix.                                            |
| `run_id`       | string  | UUID4 hex (32 chars). Stable for the entire invocation.              |
| `cli`          | string  | CLI name (e.g. `"amortize"`).                                        |
| `input_hash`   | string  | sha256 of canonical-JSON input snapshot. Same for all events in a run. |
| `level`        | string  | `INFO`, `WARNING`, `ERROR`, `DEBUG`, `CRITICAL`.                     |
| `msg`          | string  | Human-readable summary.                                              |
| `event`        | string  | Short event name (e.g. `"run_started"`, `"validation_pydantic"`).    |
| ...per-event fields | any | CLI-specific structured fields.                                  |

### Run-lifecycle events (always present)

- **`run_started`** -- emitted on `observe()` enter. Carries `started_at`,
  `log_path`.
- **`run_complete`** -- emitted on clean exit. Carries:
  - `duration_ms` -- wall time of the wrapped block.
  - `output_hash` -- sha256 of the canonical-JSON output payload (or `null`
    if the CLI never called `ctx.set_output(...)`).
  - `warning_count` -- count of WARNING-level events emitted during the run.
  - `exit_status` -- one of:
    - `"success"`
    - `"error_validation"` -- caller marked the run as a validation failure
      via `log_event(ctx, "ERROR", ..., exit_status="error_validation")` (the
      6-key Pydantic envelope path, the pre-validation float-gate, the
      MissingCountyDataError catch, the APRConvergenceError catch, ...).
    - `"error_unexpected"` -- the wrapped block raised an exception that
      escaped `observe()`'s context. The exception propagates after the
      event is emitted.
- **`run_error`** -- emitted in place of `run_complete` when an unhandled
  exception escapes the `observe()` block. Carries `error_type`,
  `error_message`, plus the same `duration_ms` / `warning_count` /
  `exit_status="error_unexpected"`.

### Per-CLI events

The instrumented CLIs emit events at each meaningful decision point so a
post-mortem `jq` over the log directory tells you *why* a run ended where it
did. Common events:

- `input_file_missing` / `input_file_unreadable`
- `validation_float_gate` (the JSON-float pre-validation gate fired)
- `validation_pydantic` (Pydantic ValidationError)
- `missing_county_data` (affordability only; County FIPS not in conforming
  limits YAML)
- `apr_convergence_error` (apr_reg_z only; solver did not converge)
- `fred_cache_hit` / `fred_fetch_succeeded` / `fred_fetch_failed`
- `schedule_built`, `affordability_evaluated`, `arm_schedule_built`,
  `refi_evaluated`, `stress_evaluated`, `points_evaluated`, `apr_solved`,
  `report_written`, `property_fetch_success` -- happy-path completion markers.

## The contract: stdout vs stderr vs file

| Channel | Default | When `MORTGAGE_OPS_LOG_STDERR=1` | Used for |
|---------|---------|----------------------------------|----------|
| stdout  | The CLI's documented JSON envelope (unchanged) | Same | What callers parse. NEVER mix logs here. |
| stderr  | The 6-key Pydantic ValidationError envelope on error, otherwise empty | Same envelope PLUS JSONL log lines | Failure surface for `json.loads(result.stderr)`. |
| file    | Always JSONL log lines | Same | Durable per-run record. Source of truth for audits. |

**Never** print log lines to stdout. Every consumer that parses CLI output
(Phase 9 Node orchestration, Phase 10 SKILL.md narration, Phase 11 subagents,
the integration test suite) depends on stdout being either the success
envelope or empty -- nothing else.

## Programmatic use (lib.observability)

If you write a new CLI:

```python
from lib.observability import log_event, observe

def main() -> int:
    args = parser.parse_args()
    with observe(cli="my_new_cli", inputs={"args": vars(args)}) as ctx:
        try:
            result = do_work(args)
        except ValidationError as e:
            log_event(
                ctx,
                "ERROR",
                "validation failed",
                event="validation_pydantic",
                exit_status="error_validation",
                error_count=e.error_count(),
            )
            print(e.json(), file=sys.stderr)
            return 2
        ctx.set_output(result.model_dump(mode="json"))
        log_event(ctx, "INFO", "work completed", event="work_done")
        print(result.model_dump_json(indent=2))
        return 0
```

Key points:

- `inputs` is the canonical input snapshot. Don't put secrets in it -- the
  dict is hashed AND `input_hash` lands in every event.
- `ctx.set_output(payload)` lets `run_complete` carry `output_hash` so a
  caller can correlate a logged run with the JSON they observed on stdout.
- `log_event(ctx, ..., exit_status="error_validation")` is how you signal
  the final event status without raising. Without this, `run_complete`
  defaults to `exit_status="success"`.
- Decimal money values are stringified by the JSON encoder (canonical
  Decimal repr), never floats.
- Field keys that collide with Python's `logging.LogRecord` reserved
  attributes (`filename`, `module`, `lineno`, ...) are auto-prefixed with
  `_` in the JSON output so a CLI passing `filename=e.filename` from a
  FileNotFoundError doesn't crash mid-run.
