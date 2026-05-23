# tests/e2e — End-to-end snapshot tests

Four full-CLI scenario snapshots that exercise the relocated skill scripts
under `.claude/skills/mortgage-ops/scripts/` via `subprocess.run`. Each
test:

1. Loads its YAML input fixture from `fixtures/inputs/`.
2. Serialises the `request:` body to a tempfile JSON.
3. Invokes the matching CLI with `--input <tempfile>`.
4. Parses stdout as JSON.
5. Deep-equals the result against the committed snapshot in
   `fixtures/snapshots/` (after dynamic-field scrubbing).

## Scenarios

| Test file                              | CLI                | What it exercises                                 |
| -------------------------------------- | ------------------ | ------------------------------------------------- |
| `test_scenario_a_conv30.py`            | `affordability.py` | Conv 30yr median market, $500k SFH @ 20% down, King WA. |
| `test_scenario_b_fha_ftb.py`           | `affordability.py` | FHA, UFMIP auto-financed + annual MIP active.     |
| `test_scenario_c_jumbo_bay.py`         | `affordability.py` | True jumbo classification (Solano CA, $900k loan).|
| `test_scenario_d_arm51_refi.py`        | `refi_npv.py`      | 5/1 ARM refi NPV vs. existing 7.5% conv30.        |

## Running

```bash
# Just the E2E suite (slow — subprocess + lazy imports per CLI):
uv run pytest tests/e2e/ -v --timeout=120

# Full suite, including E2E (slow tests run by default — marker is descriptive
# only, not exclusionary):
uv run pytest --timeout=60 -q

# Skip E2E for fast inner-loop iteration:
uv run pytest -m "not e2e" --timeout=60 -q
```

Each scenario file carries both `pytest.mark.e2e` AND `pytest.mark.slow` so
either marker filters the suite.

## Snapshot regeneration

When the calc engine output legitimately changes (e.g., a regulatory YAML
refresh, a rounding-rule clarification, an APR-band cutoff move), regenerate
the affected snapshot:

```bash
# Regenerate a single scenario:
uv run python tests/e2e/_regenerate_snapshots.py scenario_a_conv30_median

# Regenerate all four:
uv run python tests/e2e/_regenerate_snapshots.py --all
```

Then `git diff tests/e2e/fixtures/snapshots/` and review the change. If the
diff aligns with the engine change you intended, commit. If not, the
regeneration surfaced an unintended engine regression — investigate before
overwriting the snapshot.

## Dynamic-field scrubbing

Some engine outputs embed clock-driven strings. The `conftest.scrub_dynamic_fields`
helper normalises these on BOTH sides of the equality assertion:

- `threshold: YYYY-MM-DD` inside any StaleReferenceWarning string is replaced
  with `threshold: <DATE>`. The threshold is computed as
  `date.today() - relativedelta(months=12)` inside `lib.rules` reference-data
  loaders, so it drifts daily.
- Top-level keys named `run_id`, `ts`, `timestamp`, `started_at`, `ended_at`,
  `fetched_at`, `log_path`, `as_of`, `duration_ms` are STRIPPED at every
  depth. No CLI in the v1 surface puts these on stdout (observability writes
  to stderr + file only), but we strip defensively.

The scrub is idempotent — applying twice gives the same result — so it is
safe to apply to the snapshot file as well as the live output.

The snapshot files are committed WITH the clock-driven values present (so a
human reviewer can read them). The scrubber normalises at compare time.

## Hermetic isolation

E2E tests **must not** touch:

- `data/mortgage-ops.duckdb`
- `data/cache/`
- `reports/`

The four shipped scenarios use only `affordability.py` and `refi_npv.py`,
which are **pure JSON-in / JSON-out** (no disk writes at all). They are
hermetic by construction.

### Hermetic gaps (documented, not patched)

Per the task spec ("Do NOT modify production code in `lib/` or any CLI
script… If a CLI doesn't support an env-var-based output dir override and
you need one to run E2E hermetically, document the gap rather than patching
the CLI"):

- **`property_analyze.py`** writes a sidecar listing to
  `data/property-listings/{zpid}-{date}.json` (resolved from `parents[4]`
  of the script's own location — the repo root, NOT a CLI argument). The
  report itself goes wherever `--output-dir` points, but the sidecar is
  hardcoded to the repo's `data/` tree. There is no env-var override.
  Future E2E coverage for `property_analyze` will need a
  `MORTGAGE_OPS_DATA_DIR` (or equivalent) override added to `lib.property_analyze.py`
  / the CLI before it can be exercised here without polluting `data/`.

- **`fred_cli.py`** reads / writes a parquet cache under `data/cache/`.
  Live-API mode requires a key; the staleness-aware cache path already
  honors a `FRED_CACHE_DIR` env var (per Phase 12), so future E2E coverage
  is straightforward — just no scenario in the user-approved four needed it.

- **`stress_test.py`** and **`points_breakeven.py`** are pure
  JSON-in / JSON-out; no hermetic gap.

## Why subprocess?

The task spec ("These exercise FULL CLI journeys via subprocess") rules out
the faster `import .main; main()` shortcut used by some unit tests in
`tests/`. The point of the E2E suite is to catch:

- argparse drift (a kwarg renames its flag and silently breaks every skill
  routing).
- `sys.path` injection breakage (the relocated CLIs depend on
  `parents[4]` to find `lib/` — a folder shuffle would break only here).
- Lazy-import ordering bugs (`--help` fast-path discipline; the test
  exercises the FULL parse-and-run pipeline).
- Stdout vs. stderr leakage (observability bugs that put run-metadata on
  stdout would corrupt downstream Claude-skill narration; the snapshot
  asserts pure JSON-only stdout).

The trade-off is wall-clock: each subprocess pays ~250-500ms of Python
interpreter startup + lazy-import-on-first-use latency. Four scenarios at
that cost is acceptable; the suite is marker-gated for fast inner loops.
