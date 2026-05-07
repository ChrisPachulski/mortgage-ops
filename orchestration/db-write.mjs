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
// Plan 09-03 D-03-04: BEGIN TRANSACTION / COMMIT / ROLLBACK around every
//   INSERT subcommand (career-ops parallel; future-proofs multi-row inserts).
// Plan 09-03 D-03-05: insert-scenario stores request_json + response_json as
//   DuckDB native JSON columns (RESEARCH §c table 3).
// Plan 09-03 D-03-06: render-markdown is RESERVED but not implemented in this
//   plan (Wave 4 owns it end-to-end including byte-identical contract).

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
    'Not yet implemented (--render-markdown ships in Plan 09-04). ' +
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
