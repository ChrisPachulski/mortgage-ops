---
phase: 09
plan: 03
type: execute
wave: 3
depends_on:
  - "09-00"
  - "09-01"
  - "09-02"
files_modified:
  - orchestration/db-write.mjs
  - tests/test_orchestration/test_db_lifecycle.py
must_haves:
  truths:
    - "orchestration/db-write.mjs exists with subcommand dispatcher (insert-loan, insert-scenario, insert-report, query)"
    - "Argument parser supports both --key value and --key=value forms (mirrors career-ops db-write.mjs:55-83)"
    - "WRITE_COMMANDS Set gates which subcommands acquire the lock (insert-loan, insert-scenario, insert-report); query bypasses the lock"
    - "Every write subcommand wraps mutations in BEGIN TRANSACTION / COMMIT / ROLLBACK try-catch block"
    - "Money fields (DECIMAL columns) are passed as JSON strings ('200000.01'); SELECTs cast every DECIMAL to VARCHAR per PATTERNS Critical Issue 2"
    - "MORTGAGE_OPS_DB_PATH env var overrides default DB path (test seam)"
    - "test_insert_loan_round_trip + test_insert_scenario_round_trip + test_insert_report_round_trip + test_decimal_string_round_trip_preserves_cents xfails flip to passing (revision 2026-05-04: scenario + report stubs added per checker Blocker #2; PERS-03 ships 3 insert subcommands and each gets its own round-trip flip in this wave)"
    - "Both data/scenarios row count and data/reports row count increase by exactly 1 per insert-scenario / insert-report invocation; round-trip preserves request_json/response_json/markdown_blob byte-exactly"
    - "All baseline tests still pass (>=440 + 4 = 444 passed; revision 2026-05-04: was '+2 = 442' before scenario + report stubs were added in Plan 09-00 revision)"
  artifacts:
    - path: "orchestration/db-write.mjs"
      provides: "Central writer CLI with subcommand dispatcher (PERS-03 + PERS-05 closure for insert paths)"
      contains: "import { withLock } from './lockfile.mjs'"
      min_lines: 250
  key_links:
    - from: "orchestration/db-write.mjs WRITE_COMMANDS"
      to: "orchestration/lockfile.mjs withLock"
      via: "import"
      pattern: "import.*withLock.*from.*lockfile.mjs"
    - from: "tests/test_orchestration/test_db_lifecycle.py"
      to: "orchestration/db-write.mjs"
      via: "subprocess invocation"
      pattern: "node_orchestration_run.*db-write.mjs"
autonomous: true
requirements:
  - PERS-03
  - PERS-05
tags:
  - phase-09
  - duckdb-orchestration
  - db-write
  - insert-subcommands
  - decimal-discipline
---

<objective>
**Goal:** Ship `orchestration/db-write.mjs` with the subcommand dispatcher, three INSERT subcommands (`insert-loan`, `insert-scenario`, `insert-report`), and a read-only `query` subcommand. Every write wraps in `withLock()` (Plan 09-01) + `BEGIN TRANSACTION` + `COMMIT/ROLLBACK`. All money fields are passed as JSON strings on INSERT and `CAST AS VARCHAR` on SELECT (PATTERNS Critical Issue 2). Flips two xfails: `test_insert_loan_round_trip` + `test_decimal_string_round_trip_preserves_cents`.

**Purpose:** PERS-03 + PERS-05 require the central writer with the four insert subcommands plus `withLock()` discipline. The DECIMAL string round-trip is the load-bearing money invariant — without it, the project's "every dollar traces to a tested deterministic Python function" promise (CLAUDE.md) fails at the persistence boundary. This plan is the load-bearing wave for the entire phase.

**Output:** orchestration/db-write.mjs (~300 lines including dispatcher + 4 subcommands + arg parser + error envelope); 2 xfails flipped in test_db_lifecycle.py. Render-markdown + concurrency tests deferred to Waves 4 + 6 respectively.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/09-duckdb-orchestration/09-PATTERNS.md
@.planning/phases/09-duckdb-orchestration/09-RESEARCH.md
@CLAUDE.md
@orchestration/lockfile.mjs
@orchestration/init-db.mjs
@tests/conftest.py
@tests/test_orchestration/test_db_lifecycle.py

<interfaces>
**Subcommand surface (this plan ships 4 of 5; render-markdown lives in Wave 4):**

```
node orchestration/db-write.mjs insert-loan      --json <path>
node orchestration/db-write.mjs insert-scenario  --loan-id <int> --kind <enum> --json <path>
node orchestration/db-write.mjs insert-report    --scenario-id <int> --file <path>
node orchestration/db-write.mjs query            --sql "<SELECT ...>"
```

**Insert payload shapes (passed as JSON files; money fields are STRINGS — D-19 inheritance):**

`insert-loan` JSON shape (mirrors lib.models.Loan):
```json
{
  "principal": "200000.00",
  "annual_rate": "0.065000",
  "term_months": 360,
  "origination_date": "2026-05-01",
  "loan_type": "fixed",
  "frequency": "monthly",
  "known_loan_id": null,
  "notes": null
}
```

`insert-scenario` JSON shape:
```json
{
  "request": { ... arbitrary script input envelope ... },
  "response": { ... arbitrary script output envelope ... },
  "notes": null
}
```

`insert-report` reads the file content verbatim; no JSON parsing of the body.

**WRITE_COMMANDS = Set(['insert-loan', 'insert-scenario', 'insert-report', 'render-markdown'])** — query is read-only and bypasses withLock.

**lockfile.mjs API (Plan 09-01):**
```javascript
import { withLock } from './lockfile.mjs';
await withLock(async () => { /* DB work */ }, { reason: 'insert-loan' });
```

**Argument parser** — port career-ops/scripts/db-write.mjs:55-83 verbatim. Supports both `--key value` and `--key=value` forms.

**STDOUT contract:**
- Success: `console.log(JSON.stringify({ ok: true, ... }))` — single JSON line
- Failure: error message to stderr; exit 1 via top-level catch
- Query: `console.log(JSON.stringify(rows))` — full result array as JSON
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create orchestration/db-write.mjs with dispatcher + 4 subcommands</name>
  <files>orchestration/db-write.mjs</files>
  <read_first>
    - /Users/cujo253/Documents/career-ops/scripts/db-write.mjs (full file ~747 lines, focus on lines 19-83 imports + arg parser, lines 346-368 cmdInsertReport pattern, lines 687-740 dispatcher)
    - 09-PATTERNS.md "orchestration/db-write.mjs" + Critical Issue 2 (DECIMAL discipline)
    - 09-RESEARCH.md "Pattern 2: withLock-Wrapped Write" + "Pattern 3: Decimal-Safe SELECT" + "Code Examples" §Example 2 + §Example 3
    - orchestration/lockfile.mjs (Plan 09-01) — withLock signature
    - orchestration/init-db.mjs (Plan 09-02) — DB_PATH + env var pattern
  </read_first>
  <action>
    Create orchestration/db-write.mjs. The file structure: imports + path resolution + arg parser + 4 subcommand handlers + dispatcher + top-level run() with error envelope.

    Render-markdown is intentionally NOT in this plan — it ships in Plan 09-04 (Wave 4). The dispatcher reserves the slot but throws "Not yet implemented" if invoked.

    File content:

    ```javascript
    // orchestration/db-write.mjs
    // Central writer CLI for mortgage-ops Phase 9 (PERS-03 + PERS-05).
    // Subcommands: insert-loan, insert-scenario, insert-report, query
    //              (render-markdown ships in Plan 09-04)
    //
    // Every WRITE subcommand:
    //   1. Acquires the cross-process lock via withLock() from lockfile.mjs
    //   2. Opens DuckDB via duckdb-async Database.create()
    //   3. Wraps mutations in BEGIN TRANSACTION / COMMIT (ROLLBACK on throw)
    //   4. Closes the DuckDB handle in a finally block
    //   5. Releases the lock (via withLock's finally)
    //
    // Plan 09-03 D-03-01: WRITE_COMMANDS gates lock acquisition; query bypasses.
    // Plan 09-03 D-03-02: All DECIMAL columns READ via CAST AS VARCHAR
    //   (PATTERNS Critical Issue 2; RESEARCH Pitfall 1).
    // Plan 09-03 D-03-03: All DECIMAL columns WRITTEN as JSON strings
    //   (matches Phase 1+ Decimal-from-string boundary discipline).

    import { Database } from 'duckdb-async';
    import { readFileSync, existsSync } from 'fs';
    import { join, dirname } from 'path';
    import { fileURLToPath } from 'url';
    import { withLock } from './lockfile.mjs';

    const ORCH_DIR = dirname(fileURLToPath(import.meta.url));
    const MORTGAGE_OPS = dirname(ORCH_DIR);
    const DB_PATH = process.env.MORTGAGE_OPS_DB_PATH ||
                    join(MORTGAGE_OPS, 'data', 'mortgage-ops.duckdb');

    // ===== Arg parser (ported from career-ops/scripts/db-write.mjs:55-83) =====

    function parseArgs(argv) {
      const command = argv[0];
      const rest = argv.slice(1);
      const flags = {};
      const positional = [];
      let i = 0;
      while (i < rest.length) {
        const tok = rest[i];
        if (tok.startsWith('--')) {
          const stripped = tok.slice(2);
          const eqIdx = stripped.indexOf('=');
          if (eqIdx >= 0) {
            // --key=value form
            flags[stripped.slice(0, eqIdx)] = stripped.slice(eqIdx + 1);
            i += 1;
          } else {
            // --key value form (or boolean flag if next is another --foo)
            const next = rest[i + 1];
            if (next === undefined || next.startsWith('--')) {
              flags[stripped] = true;
              i += 1;
            } else {
              flags[stripped] = next;
              i += 2;
            }
          }
        } else {
          positional.push(tok);
          i += 1;
        }
      }
      return { command, flags, positional };
    }

    // ===== Subcommand handlers =====

    async function cmdInsertLoan(db, flags) {
      const { json: jsonPath } = flags;
      if (!jsonPath) throw new Error('--json required');
      if (!existsSync(jsonPath)) throw new Error(`File not found: ${jsonPath}`);

      const payload = JSON.parse(readFileSync(jsonPath, 'utf-8'));

      // Required fields per lib.models.Loan
      const required = ['principal', 'annual_rate', 'term_months', 'loan_type'];
      for (const k of required) {
        if (payload[k] === undefined || payload[k] === null) {
          throw new Error(`Loan payload missing required field: ${k}`);
        }
      }

      // Money/rate fields MUST be strings (Phase 1+ Decimal-from-string discipline)
      for (const k of ['principal', 'annual_rate']) {
        if (typeof payload[k] !== 'string') {
          throw new Error(
            `Loan.${k} must be a JSON string (got ${typeof payload[k]}); ` +
            `Phase 1 D-02 + Phase 9 D-03-03 forbid floats at the boundary.`
          );
        }
      }

      await db.run('BEGIN TRANSACTION');
      try {
        // Parameterized INSERT — DuckDB parses '200000.00' string into DECIMAL(14,2) losslessly.
        // Use RETURNING id to get the auto-generated PK.
        const rows = await db.all(
          `INSERT INTO loans (principal, annual_rate, term_months, origination_date,
                              loan_type, frequency, known_loan_id, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           RETURNING id`,
          payload.principal,
          payload.annual_rate,
          payload.term_months,
          payload.origination_date || null,
          payload.loan_type,
          payload.frequency || 'monthly',
          payload.known_loan_id || null,
          payload.notes || null,
        );
        await db.run('COMMIT');
        const loanId = Number(rows[0].id);
        console.log(JSON.stringify({ ok: true, loan_id: loanId }));
      } catch (e) {
        await db.run('ROLLBACK');
        throw e;
      }
    }

    async function cmdInsertScenario(db, flags) {
      const { json: jsonPath, kind, 'loan-id': loanIdStr } = flags;
      if (!jsonPath) throw new Error('--json required');
      if (!kind) throw new Error('--kind required');
      if (!existsSync(jsonPath)) throw new Error(`File not found: ${jsonPath}`);

      const validKinds = new Set(['amortize', 'affordability', 'arm', 'refi', 'apr', 'stress', 'points']);
      if (!validKinds.has(kind)) {
        throw new Error(`Invalid --kind: ${kind}. Must be one of: ${[...validKinds].sort().join(', ')}`);
      }

      const payload = JSON.parse(readFileSync(jsonPath, 'utf-8'));
      if (!payload.request || !payload.response) {
        throw new Error('Scenario payload must have {request, response} top-level keys');
      }

      const loanId = loanIdStr !== undefined ? Number(loanIdStr) : null;
      if (loanIdStr !== undefined && Number.isNaN(loanId)) {
        throw new Error(`--loan-id must be an integer (got ${loanIdStr})`);
      }

      await db.run('BEGIN TRANSACTION');
      try {
        const rows = await db.all(
          `INSERT INTO scenarios (loan_id, kind, request_json, response_json, notes)
           VALUES (?, ?, ?, ?, ?)
           RETURNING id`,
          loanId,
          kind,
          JSON.stringify(payload.request),
          JSON.stringify(payload.response),
          payload.notes || null,
        );
        await db.run('COMMIT');
        const scenarioId = Number(rows[0].id);
        console.log(JSON.stringify({ ok: true, scenario_id: scenarioId, kind, loan_id: loanId }));
      } catch (e) {
        await db.run('ROLLBACK');
        throw e;
      }
    }

    async function cmdInsertReport(db, flags) {
      const { file, 'scenario-id': scenarioIdStr } = flags;
      if (!file) throw new Error('--file required');
      if (!scenarioIdStr) throw new Error('--scenario-id required');
      if (!existsSync(file)) throw new Error(`File not found: ${file}`);

      const scenarioId = Number(scenarioIdStr);
      if (Number.isNaN(scenarioId)) {
        throw new Error(`--scenario-id must be an integer (got ${scenarioIdStr})`);
      }

      const body = readFileSync(file, 'utf-8');

      await db.run('BEGIN TRANSACTION');
      try {
        const rows = await db.all(
          `INSERT INTO reports (scenario_id, markdown_blob)
           VALUES (?, ?)
           RETURNING id`,
          scenarioId,
          body,
        );
        await db.run('COMMIT');
        const reportId = Number(rows[0].id);
        console.log(JSON.stringify({ ok: true, report_id: reportId, scenario_id: scenarioId, bytes: body.length }));
      } catch (e) {
        await db.run('ROLLBACK');
        throw e;
      }
    }

    async function cmdQuery(db, flags) {
      const { sql } = flags;
      if (!sql) throw new Error('--sql required');
      const rows = await db.all(sql);
      // BigInt JSON serialization workaround: career-ops jsonReplacer pattern.
      // BigInt only appears for INTEGER columns (id, term_months, period). Money
      // columns MUST be SELECTed via CAST AS VARCHAR per D-03-02 — caller's responsibility.
      const replacer = (_key, value) =>
        typeof value === 'bigint' ? Number(value) : value;
      console.log(JSON.stringify(rows, replacer));
    }

    async function cmdRenderMarkdown(_db, _flags) {
      throw new Error(
        'render-markdown not yet implemented — ships in Plan 09-04 (Wave 4). ' +
        'Per Phase 9 plan sequence, this slot is reserved.'
      );
    }

    // ===== Dispatcher =====

    const HANDLERS = {
      'insert-loan': cmdInsertLoan,
      'insert-scenario': cmdInsertScenario,
      'insert-report': cmdInsertReport,
      'render-markdown': cmdRenderMarkdown,
      'query': cmdQuery,
    };

    const WRITE_COMMANDS = new Set([
      'insert-loan', 'insert-scenario', 'insert-report', 'render-markdown',
    ]);

    function usage() {
      return [
        'Usage: node orchestration/db-write.mjs <subcommand> [flags]',
        '',
        'Subcommands:',
        '  insert-loan      --json <path>',
        '  insert-scenario  --loan-id <int> --kind <enum> --json <path>',
        '  insert-report    --scenario-id <int> --file <path>',
        '  render-markdown  [loans|scenarios|all]   (Plan 09-04)',
        '  query            --sql "<SELECT ...>"',
        '',
        'Env: MORTGAGE_OPS_DB_PATH overrides default data/mortgage-ops.duckdb',
      ].join('\n');
    }

    async function run() {
      const argv = process.argv.slice(2);
      if (argv.length === 0 || argv[0] === '--help' || argv[0] === '-h') {
        console.log(usage());
        return;
      }

      const { command, flags } = parseArgs(argv);
      const handler = HANDLERS[command];
      if (!handler) {
        console.error(`Unknown subcommand: ${command}`);
        console.error(usage());
        process.exit(1);
      }

      const action = async () => {
        const db = await Database.create(DB_PATH);
        try {
          await handler(db, flags);
        } finally {
          await db.close();
        }
      };

      if (WRITE_COMMANDS.has(command)) {
        await withLock(action, { reason: command });
      } else {
        await action();
      }
    }

    run().catch(err => {
      console.error('Fatal:', err?.message || err);
      process.exit(1);
    });
    ```

    Manual smoke test after writing:

    ```bash
    rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal data/mortgage-ops.duckdb-shm
    node orchestration/init-db.mjs
    cat > /tmp/loan.json <<EOF
    {"principal":"200000.01","annual_rate":"0.065000","term_months":360,"origination_date":"2026-05-01","loan_type":"fixed"}
    EOF
    node orchestration/db-write.mjs insert-loan --json /tmp/loan.json
    node orchestration/db-write.mjs query --sql "SELECT id, CAST(principal AS VARCHAR) AS principal FROM loans"
    # Expected: [{"id":1,"principal":"200000.01"}]
    ```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && node --check orchestration/db-write.mjs && node orchestration/db-write.mjs --help</automated>
  </verify>
  <acceptance_criteria>
    - `test -f orchestration/db-write.mjs` exits 0
    - `node --check orchestration/db-write.mjs` exits 0
    - `wc -l orchestration/db-write.mjs` returns at least 200
    - `grep -c "import { withLock } from './lockfile.mjs'" orchestration/db-write.mjs` returns 1
    - `grep -c "async function cmdInsertLoan" orchestration/db-write.mjs` returns 1
    - `grep -c "async function cmdInsertScenario" orchestration/db-write.mjs` returns 1
    - `grep -c "async function cmdInsertReport" orchestration/db-write.mjs` returns 1
    - `grep -c "async function cmdQuery" orchestration/db-write.mjs` returns 1
    - `grep -c "WRITE_COMMANDS = new Set" orchestration/db-write.mjs` returns 1
    - `grep -c "BEGIN TRANSACTION" orchestration/db-write.mjs` returns 3 (one per insert subcommand)
    - `grep -c "ROLLBACK" orchestration/db-write.mjs` returns 3
    - `grep -c "process.env.MORTGAGE_OPS_DB_PATH" orchestration/db-write.mjs` returns 1
    - `node orchestration/db-write.mjs --help 2>&1 | grep -c "insert-loan"` returns 1 (help text mentions all subcommands)
  </acceptance_criteria>
  <done>
    db-write.mjs parses, --help works, all 4 subcommand handlers present, withLock + BEGIN/COMMIT/ROLLBACK discipline verified by grep.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip 4 xfails in test_db_lifecycle.py (insert-loan + insert-scenario + insert-report + decimal round-trip)</name>
  <files>tests/test_orchestration/test_db_lifecycle.py</files>
  <read_first>
    - tests/test_orchestration/test_db_lifecycle.py (current state: 1 passing test_init_db_idempotent + 3 xfail stubs)
    - tests/conftest.py — node_orchestration_run helper
  </read_first>
  <action>
    Replace FOUR xfail stubs with real assertions (revision 2026-05-04: was 2 stubs; the two new scenario + report stubs land here per checker Blocker #2):
    1. `test_insert_loan_round_trip` — insert a fixture loan, query it back, assert all fields match
    2. `test_insert_scenario_round_trip` — insert a scenario via `insert-scenario --kind <enum> --json`, query it back, assert kind + request_json + response_json round-trip
    3. `test_insert_report_round_trip` — insert a report via `insert-report --scenario-id <int> --file <path>`, query it back, assert markdown_blob is byte-identical to the source file
    4. `test_decimal_string_round_trip_preserves_cents` — insert principal='200000.01', SELECT CAST AS VARCHAR, assert exact string match

    Leave `test_concurrent_writes_serialize` xfail (Wave 6).

    The two new flips (#2 + #3) follow the same pattern as test_insert_loan_round_trip:
    - tmp_path-isolated DB
    - init via `node orchestration/init-db.mjs`
    - write a fixture JSON to tmp_path
    - invoke the insert subcommand and assert returncode == 0 + parse the
      stdout JSON envelope ({ok: true, scenario_id: ...} or {ok: true, report_id: ...})
    - issue a follow-up `query` subcommand and assert the row round-trips

    Insert-scenario fixture shape (per Plan 09-03 cmdInsertScenario contract):

    ```python
    scenario_fixture = tmp_path / "scenario.json"
    scenario_fixture.write_text(json.dumps({
        "request": {"loan_id": 1, "amortize_options": {"rounding": "half_up"}},
        "response": {"monthly_pi": "1264.14", "schedule_rows": 360},
        "notes": "test fixture",
    }))
    # First create a parent loan (scenarios.loan_id FK is nullable but the test
    # exercises the populated path; use the previously inserted loan_id=1).
    scen_result = node_orchestration_run(
        "orchestration/db-write.mjs", "insert-scenario",
        "--loan-id", "1",
        "--kind", "amortize",
        "--json", str(scenario_fixture),
        db_path=db_path,
    )
    assert scen_result.returncode == 0
    scen_payload = json.loads(scen_result.stdout.strip())
    assert scen_payload["ok"] is True
    assert scen_payload["scenario_id"] == 1
    assert scen_payload["kind"] == "amortize"
    assert scen_payload["loan_id"] == 1

    # Round-trip: query back the row, parse request_json + response_json columns
    scen_query = node_orchestration_run(
        "orchestration/db-write.mjs", "query",
        "--sql", "SELECT id, loan_id, kind, request_json, response_json, notes FROM scenarios ORDER BY id ASC",
        db_path=db_path,
    )
    rows = json.loads(scen_query.stdout.strip())
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "amortize"
    assert row["loan_id"] == 1
    # request_json + response_json may come back as either JSON-string or
    # already-parsed dict depending on duckdb-async JSON-column handling.
    # Normalize before comparing.
    req = json.loads(row["request_json"]) if isinstance(row["request_json"], str) else row["request_json"]
    resp = json.loads(row["response_json"]) if isinstance(row["response_json"], str) else row["response_json"]
    assert req["loan_id"] == 1
    assert req["amortize_options"]["rounding"] == "half_up"
    assert resp["monthly_pi"] == "1264.14"
    assert resp["schedule_rows"] == 360
    assert row["notes"] == "test fixture"
    ```

    Insert-report fixture shape (per Plan 09-03 cmdInsertReport contract):

    ```python
    report_md = tmp_path / "report.md"
    report_body = "# Loan Report\n\nMonthly P&I: $1,264.14\nTotal interest: $255,089.36\n"
    report_md.write_text(report_body)

    rep_result = node_orchestration_run(
        "orchestration/db-write.mjs", "insert-report",
        "--scenario-id", "1",
        "--file", str(report_md),
        db_path=db_path,
    )
    assert rep_result.returncode == 0
    rep_payload = json.loads(rep_result.stdout.strip())
    assert rep_payload["ok"] is True
    assert rep_payload["report_id"] == 1
    assert rep_payload["scenario_id"] == 1
    assert rep_payload["bytes"] == len(report_body)

    # Round-trip: query back markdown_blob and assert byte-identical
    rep_query = node_orchestration_run(
        "orchestration/db-write.mjs", "query",
        "--sql", "SELECT id, scenario_id, markdown_blob FROM reports ORDER BY id ASC",
        db_path=db_path,
    )
    rep_rows = json.loads(rep_query.stdout.strip())
    assert len(rep_rows) == 1
    rep_row = rep_rows[0]
    assert rep_row["scenario_id"] == 1
    assert rep_row["markdown_blob"] == report_body, (
        f"insert-report round-trip lost bytes: "
        f"sent {len(report_body)} got {len(rep_row['markdown_blob'])}"
    )
    ```

    These two new test bodies should be appended to test_insert_scenario_round_trip
    and test_insert_report_round_trip respectively. The xfail decorators ABOVE
    these functions MUST also be removed (same pattern as the existing
    test_insert_loan_round_trip flip).

    New body for `test_insert_loan_round_trip`:

    ```python
    def test_insert_loan_round_trip(tmp_path: Path) -> None:
        """PERS-03 + ROADMAP SC-2 (write half): writing a loan via
        `db-write.mjs insert-loan --json fixtures/loan.json` succeeds, and a
        subsequent `db-write.mjs query --sql 'SELECT ... FROM loans'` returns
        the row. Money fields round-trip as exact strings (no precision loss).
        """
        from tests.conftest import node_orchestration_run

        db_path = tmp_path / "test.duckdb"
        # Bootstrap schema
        init_result = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert init_result.returncode == 0, f"init failed: {init_result.stderr}"

        # Write fixture JSON
        fixture = tmp_path / "loan.json"
        fixture.write_text(json.dumps({
            "principal": "200000.00",
            "annual_rate": "0.065000",
            "term_months": 360,
            "origination_date": "2026-05-01",
            "loan_type": "fixed",
            "frequency": "monthly",
        }))

        # Insert
        insert_result = node_orchestration_run(
            "orchestration/db-write.mjs", "insert-loan", "--json", str(fixture),
            db_path=db_path,
        )
        assert insert_result.returncode == 0, f"insert failed: {insert_result.stderr}"
        insert_payload = json.loads(insert_result.stdout.strip())
        assert insert_payload["ok"] is True
        assert insert_payload["loan_id"] == 1

        # Query back (CAST AS VARCHAR for money/rate columns)
        query_sql = (
            "SELECT id, CAST(principal AS VARCHAR) AS principal, "
            "CAST(annual_rate AS VARCHAR) AS annual_rate, "
            "term_months, "
            "strftime(origination_date, '%Y-%m-%d') AS origination_date, "
            "loan_type, frequency "
            "FROM loans ORDER BY id ASC"
        )
        query_result = node_orchestration_run(
            "orchestration/db-write.mjs", "query", "--sql", query_sql,
            db_path=db_path,
        )
        assert query_result.returncode == 0, f"query failed: {query_result.stderr}"
        rows = json.loads(query_result.stdout.strip())
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == 1
        assert row["principal"] == "200000.00", f"DECIMAL string round-trip broke: {row['principal']!r}"
        assert row["annual_rate"] == "0.065000", f"Rate round-trip broke: {row['annual_rate']!r}"
        assert row["term_months"] == 360
        assert row["origination_date"] == "2026-05-01"
        assert row["loan_type"] == "fixed"
        assert row["frequency"] == "monthly"
    ```

    New body for `test_decimal_string_round_trip_preserves_cents`:

    ```python
    def test_decimal_string_round_trip_preserves_cents(tmp_path: Path) -> None:
        """PATTERNS Critical Issue 2 + RESEARCH Pitfall 1 + CLAUDE.md money
        discipline: insert principal='200000.01', SELECT CAST(principal AS
        VARCHAR), assert returned string equals '200000.01' exactly.
        Guards against the duckdb-async DECIMAL->bigint coercion bug.
        """
        from tests.conftest import node_orchestration_run

        db_path = tmp_path / "test.duckdb"
        node_orchestration_run("orchestration/init-db.mjs", db_path=db_path, check=True)

        # Test multiple boundary values: cent precision, max, mid-range, min positive
        test_cases = [
            "200000.01",   # Cent precision (the load-bearing case)
            "0.01",        # Smallest positive money
            "99999999.99", # Large value where bigint coercion would risk loss
            "1234567.89",  # Random mid-range
        ]
        for principal_str in test_cases:
            fixture = tmp_path / f"loan_{principal_str}.json"
            fixture.write_text(json.dumps({
                "principal": principal_str,
                "annual_rate": "0.060000",
                "term_months": 360,
                "loan_type": "fixed",
            }))
            insert_result = node_orchestration_run(
                "orchestration/db-write.mjs", "insert-loan", "--json", str(fixture),
                db_path=db_path,
            )
            assert insert_result.returncode == 0, (
                f"insert {principal_str} failed: {insert_result.stderr}"
            )

        # Query all back; assert each round-trips byte-exact
        query_result = node_orchestration_run(
            "orchestration/db-write.mjs", "query",
            "--sql", "SELECT CAST(principal AS VARCHAR) AS principal FROM loans ORDER BY id ASC",
            db_path=db_path,
        )
        assert query_result.returncode == 0, f"query failed: {query_result.stderr}"
        rows = json.loads(query_result.stdout.strip())
        actual = [r["principal"] for r in rows]
        assert actual == test_cases, (
            f"DECIMAL string round-trip failed.\n"
            f"  Inserted: {test_cases}\n"
            f"  Got back: {actual}\n"
            f"  This indicates duckdb-async DECIMAL->bigint coercion is bypassing "
            f"the CAST AS VARCHAR discipline (PATTERNS Critical Issue 2)."
        )
    ```

    Add `import json` at the top of the file if not already present (Wave 0 stub used `from pathlib import Path` only).

    REMOVE the `@pytest.mark.xfail(...)` decorators above both flipped tests.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_loan_round_trip tests/test_orchestration/test_db_lifecycle.py::test_decimal_string_round_trip_preserves_cents -v --tb=short 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_loan_round_trip -v 2>&1 | grep -c PASSED` returns 1
    - `pytest tests/test_orchestration/test_db_lifecycle.py::test_decimal_string_round_trip_preserves_cents -v 2>&1 | grep -c PASSED` returns 1
    - `pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_scenario_round_trip -v 2>&1 | grep -c PASSED` returns 1 (revision 2026-05-04: new flip per Blocker #2)
    - `pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_report_round_trip -v 2>&1 | grep -c PASSED` returns 1 (revision 2026-05-04: new flip per Blocker #2)
    - `pytest tests/test_orchestration/test_db_lifecycle.py -v --tb=no 2>&1 | grep -c XFAIL` returns 2 (revision 2026-05-04: Wave 0 v2 has 6 xfails in this file; Wave 3 flips 4 leaving 2 — test_init_db_idempotent + test_concurrent_writes_serialize, both flipped in Wave 6)
    - `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_db_lifecycle.py` returns 2 (revision 2026-05-04: was 1; Wave 0 v2 has 6 xfails; Wave 3 flips 4 leaving 2 — init + concurrent)
    - `grep -c "import json" tests/test_orchestration/test_db_lifecycle.py` returns 1
  </acceptance_criteria>
  <done>
    All four flips pass (loan + scenario + report + decimal); exactly 2 xfails remain in test_db_lifecycle.py (init_db_idempotent + concurrent_writes_serialize, both flipped in Wave 6); PERS-03 fully covered at the integration layer for all three insert subcommands; DECIMAL round-trip discipline verified.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero regression + lint</name>
  <files>(verification only)</files>
  <action>
    1. Full pytest suite: at least 440 + 4 = 444 passed (revision 2026-05-04: +2 from new scenario + report flips per Blocker #2); xfail count drops to 6 (Phase 5 strict + 5 remaining Wave 0 stubs: test_init_db_idempotent + test_concurrent_writes_serialize + test_stale_lockfile_reclaimed_after_60s + test_known_loans_catalog_complete + test_render_markdown_byte_identical).
    2. mypy --strict tests/test_orchestration/.
    3. ruff check + format on tests/test_orchestration/.
    4. Sanity: db-write.mjs --help works without throw.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest -q 2>&1 | tail -3 && mypy --strict tests/test_orchestration/ && ruff check tests/test_orchestration/ && ruff format --check tests/test_orchestration/ && node orchestration/db-write.mjs --help > /dev/null && echo "help OK"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows >= 444 (revision 2026-05-04: was 442; +2 from new scenario + report flips per Blocker #2)
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ xfailed'` shows 6 (revision 2026-05-04: Wave 0 v2 adds 2 stubs → total xfailed at Wave 0 end = 10 (9 Phase 9 + 1 Phase 5); Wave 3 flips 4 leaving 6)
    - `pytest -q 2>&1 | tail -3 | grep -E '[0-9]+ failed' | wc -l` returns 0 OR shows "0 failed"
    - mypy + ruff + ruff format all exit 0
    - `node orchestration/db-write.mjs --help` exits 0
  </acceptance_criteria>
  <done>
    Suite green; PERS-03 partially closed (insert paths); PERS-05 partially closed (withLock wrap verified at grep level; concurrency test in Wave 6).
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS:**

- **D-03-01: WRITE_COMMANDS gates lock acquisition; query bypasses** — rationale: per RESEARCH §Pattern 2, read-only operations don't need the cross-process lock (DuckDB MVCC handles concurrent readers). Career-ops uses identical pattern (db-write.mjs:668). Rule-of-three citation: career-ops db-write.mjs:668; RESEARCH §Pattern 2; PATTERNS Pattern Assignments db-write section line 271.

- **D-03-02: Every DECIMAL column SELECTed via CAST AS VARCHAR** — rationale: PATTERNS Critical Issue 2 + RESEARCH Pitfall 1 — duckdb-async returns DECIMAL as JS bigint; CAST AS VARCHAR forces lossless string round-trip. Project-wide invariant per CLAUDE.md money discipline. Rule-of-three citation: PATTERNS Critical Issue 2 explicit recommendation; RESEARCH Pattern 3 + Pitfall 1; test_decimal_string_round_trip_preserves_cents enforces at every wave going forward.

- **D-03-03: Every DECIMAL column INSERTed as JSON string** — rationale: mirrors Phase 1 D-02 / Phase 3 D-19 / Phase 4 D-13 / Phase 5 D-19 boundary discipline. cmdInsertLoan validates `typeof payload[k] === 'string'` for principal + annual_rate; throws on float. Rule-of-three citation: lib/money.py:29 to_money(value: str); scripts/_cli_helpers.py float-gate envelope; this plan extends the discipline to the Node boundary.

- **D-03-04: BEGIN TRANSACTION + COMMIT/ROLLBACK try-catch around every INSERT subcommand** — rationale: per RESEARCH §Anti-Patterns "Skipping BEGIN TRANSACTION for multi-row inserts" — even single-row inserts use the pattern for consistency + future-proofing (insert-scenario will eventually insert payments rows too). Rule-of-three citation: career-ops db-write.mjs:226-252 + 346-368 use BEGIN/COMMIT/ROLLBACK uniformly; RESEARCH §Anti-Patterns; PATTERNS Pattern Assignments db-write section line 270.

- **D-03-05: insert-scenario stores request_json + response_json as JSON columns** — rationale: per RESEARCH §c table 3, scenarios.request_json + response_json are DuckDB native JSON type; storing the Pydantic envelope as JSON avoids schema-migration churn when Phase 4/5/6/7/8 response shapes evolve. Rule-of-three citation: RESEARCH §c lines 318-321; PATTERNS Critical Issue 3 schema rationale; ROADMAP SC-1 enumerates "scenarios" without column-level specifics, leaving room for JSON escape hatch.

- **D-03-06: render-markdown is RESERVED but not implemented in this plan** — rationale: clean wave separation; Wave 4 owns render-markdown end-to-end including byte-identical contract. The dispatcher has the slot so the help text is complete. Rule-of-three citation: spawn-message wave breakdown explicitly separates Wave 3 (inserts) from Wave 4 (render-markdown); plan sequence preserves this; the explicit "Not yet implemented — ships in Plan 09-04" error message gives a clear signal if invoked early.
</locked_decisions>

<verify_block>
**Verify Block:**

```bash
# 1. db-write.mjs syntax + help
node --check orchestration/db-write.mjs
node orchestration/db-write.mjs --help | grep -E "insert-loan|insert-scenario|insert-report|query"

# 2. End-to-end smoke (init + insert + query round-trip)
rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal data/mortgage-ops.duckdb-shm
node orchestration/init-db.mjs
cat > /tmp/loan.json <<EOF
{"principal":"200000.01","annual_rate":"0.065000","term_months":360,"origination_date":"2026-05-01","loan_type":"fixed"}
EOF
node orchestration/db-write.mjs insert-loan --json /tmp/loan.json
node orchestration/db-write.mjs query --sql "SELECT CAST(principal AS VARCHAR) AS principal FROM loans"
# Expected: [{"principal":"200000.01"}]

# 3. All four flipped tests pass (revision 2026-05-04: was 2; +2 per Blocker #2)
pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_loan_round_trip -v
pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_scenario_round_trip -v
pytest tests/test_orchestration/test_db_lifecycle.py::test_insert_report_round_trip -v
pytest tests/test_orchestration/test_db_lifecycle.py::test_decimal_string_round_trip_preserves_cents -v

# 4. Full suite green; xfail count drops to 6 (Phase 5 strict + 5 Wave 0 stubs remaining; revision 2026-05-04: arithmetic reframed but final count 6 preserved because Wave 0 added 2 stubs that Wave 3 also flips)
pytest -q 2>&1 | tail -3

# 5. Lint hygiene
mypy --strict tests/test_orchestration/
ruff check tests/test_orchestration/
ruff format --check tests/test_orchestration/

# 6. WRITE_COMMANDS + lock + transaction discipline (grep gates)
grep -c "WRITE_COMMANDS = new Set" orchestration/db-write.mjs       # MUST be 1
grep -c "withLock(action" orchestration/db-write.mjs                # MUST be 1
grep -c "BEGIN TRANSACTION" orchestration/db-write.mjs              # MUST be 3
grep -c "ROLLBACK" orchestration/db-write.mjs                       # MUST be 3
grep -c "import { withLock } from './lockfile.mjs'" orchestration/db-write.mjs  # MUST be 1
```
</verify_block>

<deviation_rules>
**Deviation Rules:**

- **Rule-1 (no render-markdown in this plan):** D-03-06 reserves the slot but throws "Not yet implemented". If the executor sees test_render_markdown_byte_identical xfail in test_render_markdown.py, leave it xfail; that flips in Plan 09-04. Implementing render-markdown here would violate the clean wave separation.

- **Rule-2 (DECIMAL string discipline is non-negotiable):** D-03-02 + D-03-03 + the test_decimal_string_round_trip_preserves_cents test together pin the money invariant. If any code path in db-write.mjs SELECTs a DECIMAL without CAST AS VARCHAR, OR INSERTs a non-string value into a DECIMAL column, STOP. This is a CLAUDE.md-level project invariant.

- **Rule-3 (hygiene-only deviations OK):** If `node --check` surfaces a stylistic issue (trailing semicolons, formatter preference), apply minimal fix and document in SUMMARY as Rule-3. Likewise for ruff format auto-fix on the Python test changes.
</deviation_rules>

<dependencies>
**Dependencies:**

- **Depends on:** Plan 09-00 (test_db_lifecycle.py stubs awaiting flip; node_orchestration_run helper); Plan 09-01 (orchestration/lockfile.mjs withLock import target); Plan 09-02 (package.json with duckdb-async installed; orchestration/init-db.mjs schema for INSERTs to land in).
- **Blocks:** Plan 09-04 (render-markdown SELECTs from the schema; uses the same Database.create + close pattern). Plan 09-06 (concurrency tests spawn parallel `db-write.mjs --insert-loan`). Plan 09-05 (known-loans.yml smoke test does not depend on db-write but Plan 09-05 uses the same conftest helper).
- **Inheritance:** Phase 1 D-02 money discipline; Phase 3 D-19 + Phase 5 D-19 JSON-float boundary discipline.
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User JSON file -> cmdInsertLoan | Untrusted input; validated via type checks (string for money fields) before DB binding |
| --sql flag -> cmdQuery | Trusted (developer-only CLI); no skill exposure to user input per RESEARCH §Security Domain |
| Two parallel writers -> withLock | Race window inherited from Plan 09-01; DuckDB OS file lock is second line of defense |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-13 | Tampering (SQL injection via JSON payload) | cmdInsertLoan/Scenario/Report | mitigate | All INSERTs use parameterized `?` placeholders; never string-interpolate user values into SQL |
| T-09-14 | Tampering (DECIMAL->float coercion silently loses precision) | money field handling | mitigate | typeof string check at boundary; CAST AS VARCHAR for SELECT; round-trip test pins the contract |
| T-09-15 | Information Disclosure (SQL injection via --sql flag in cmdQuery) | cmdQuery | accept | Developer-only CLI per RESEARCH §Security Domain; Phase 10 skill never exposes --sql to user input |
| T-09-16 | Denial of Service (orphaned DB handle on throw) | Database.create / close | mitigate | try { handler } finally { db.close() } pattern; ensures cleanup even on subcommand throw |
| T-09-17 | Repudiation (uncommitted partial INSERT survives) | BEGIN/COMMIT/ROLLBACK discipline | mitigate | catch ROLLBACK on every subcommand; transaction is atomic |
</threat_model>

<verification>
- orchestration/db-write.mjs exists with 4 subcommand handlers + dispatcher + arg parser
- WRITE_COMMANDS Set + withLock + BEGIN/COMMIT/ROLLBACK discipline (grep gates)
- 4 xfails flipped (insert_loan + insert_scenario + insert_report + decimal_string_round_trip_preserves_cents); revision 2026-05-04: scenario + report added per Blocker #2
- DECIMAL string round-trip verified for 4 boundary values (cents, min positive, large, mid-range)
- insert-scenario round-trip verified (request_json + response_json + kind + loan_id all preserved)
- insert-report round-trip verified (markdown_blob byte-identical to source file)
- Full suite >= 444 passed (revision 2026-05-04: was 442); xfail count drops to 6
- mypy + ruff clean
- PERS-03 closed for ALL THREE insert subcommands (insert-loan + insert-scenario + insert-report each have a passing round-trip integration test; revision 2026-05-04 per Blocker #2); render-markdown closure follows in Wave 4
- PERS-05 closed at grep level (withLock wrap on WRITE_COMMANDS); concurrency end-to-end test in Wave 6
</verification>

<success_criteria>
- 4 of 5 db-write subcommands shipped (insert-loan, insert-scenario, insert-report, query); each insert subcommand has its own integration round-trip test pinned (revision 2026-05-04 per Blocker #2)
- DECIMAL money discipline verified at the persistence boundary (Critical Issue 2 closure)
- Wave 4 (render-markdown) and Wave 6 (concurrency tests) can build on this foundation
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-03-SUMMARY.md` documenting:
- orchestration/db-write.mjs line count + subcommand inventory
- WRITE_COMMANDS Set contents + withLock wrapping verification
- DECIMAL string round-trip test coverage (4 boundary values)
- Pass count delta (Wave 2 baseline 440 -> Wave 3 baseline 444; revision 2026-05-04: 4 xfails flipped per Blocker #2 — was 2 in v1)
- PERS-03 closure status (all three insert paths complete with round-trip tests: insert-loan, insert-scenario, insert-report; render-markdown deferred to Wave 4)
- PERS-05 status (withLock wrapping verified; concurrency end-to-end test deferred to Wave 6)
</output>
</content>
</invoke>