# Phase 9: DuckDB Persistence & Node Orchestration — Research

**Researched:** 2026-05-02
**Domain:** DuckDB single-file persistence + Node orchestration with cross-process lockfile
**Confidence:** HIGH

## Summary

Phase 9 wires DuckDB v1.4.x as the single-file ACID store for `loans`, `scenarios`,
`reports`, `payments`, `applicants`, and `properties` and ports the canonical career-ops
`db-write.mjs` + `lockfile.mjs` pattern verbatim into `orchestration/`, with one critical
mortgage-ops-specific deviation: **DECIMAL columns must be retrieved via `CAST(col AS
VARCHAR)`** because the duckdb-async binding returns DECIMAL as a JavaScript `bigint`
(scaled by `10^scale`), which we cannot safely round-trip back into a Python `Decimal`
without precision loss if anyone ever calls `Number()` on the result.

The lockfile is `data/.mortgage-ops.duckdb.lock` (career-ops uses `.career-ops.lock` —
note the rename) with the same JSON `{pid, acquired_at, reason}` payload, 60-second
stale-recovery threshold, and `withLock()` wrapper. **The career-ops lockfile is NOT
race-free** — it uses `writeFileSync` (without `O_EXCL`) followed by a read-back
verification, which has a known race window of milliseconds. For a single-user desktop
tool this is acceptable; for production it is not. We document the window and adopt the
career-ops behavior unchanged (PERS-04 says "career-ops pattern" verbatim).

DuckDB enforces the single-writer constraint at the OS file-lock level: while
`db-write.mjs` holds the connection, **no other process can open it for read or write**
— so Python `lib/` cannot read the DB while Node writers run. The recommended stance:
**Python lib/ never opens DuckDB**; all DB access flows through `node orchestration/db-write.mjs query --sql ...`. Python remains the calc engine that emits JSON to stdout; Node
is the only process that owns the file.

**Primary recommendation:** Copy `career-ops/scripts/{db-write,lockfile,init-db}.mjs`
verbatim into `mortgage-ops/orchestration/`, rename the lockfile constant, swap the
schema for the mortgage-ops tables documented below, and add a single SQL discipline:
**every DECIMAL SELECT casts to VARCHAR before crossing the JS boundary.** Pin
`duckdb-async@1.4.2` (latest stable as of 2025-11-13).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema DDL (CREATE TABLE) | Node (`init-db.mjs`) | — | Career-ops pattern; idempotent CLI. Python `lib/` never owns schema. |
| ACID writes (loans, scenarios, payments) | Node (`db-write.mjs` + `withLock()`) | — | DuckDB is single-writer-per-process; `withLock()` serializes writes across script invocations. |
| Money DECIMAL retrieval | Node SQL `CAST(col AS VARCHAR)` | — | duckdb-async returns DECIMAL as JS bigint; VARCHAR round-trips losslessly to Python `Decimal(str)`. |
| Calc (amortize/affordability/ARM) | Python `lib/` | — | Existing engine; emits JSON to stdout. Never touches DuckDB directly. |
| Calc → DB ingest | Node `db-write.mjs --insert-loan/scenario/report` | — | Node reads JSON from disk or stdin and INSERTs. Python emits, Node persists. |
| Markdown view regeneration | Node `db-write.mjs --render-markdown` | — | Career-ops pattern; views are SELECT-driven, deterministic ORDER BY. |
| `known-loans.yml` parsing | Node (`js-yaml`) | Python smoke test | YAML lives in repo (Reference Layer); Node loads it for DB seeding; Python test asserts shape. |
| Lockfile coordination | Node `lockfile.mjs` (`withLock()`) | — | All write commands acquire before opening DuckDB; release after `db.close()`. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `duckdb-async` | `1.4.2` | Promise-wrapped DuckDB Node binding | [VERIFIED: npm view duckdb-async version → 1.4.2, published 2025-11-13]; same major as career-ops `^1.4.2` (`/Users/cujo253/Documents/career-ops/package.json:38`); wraps the official `duckdb` Node binding with Promises. |
| `duckdb` (transitive) | `1.4.4` | Underlying native binding | [VERIFIED: npm view duckdb version → 1.4.4, published 2026-01-30]; pulled in by `duckdb-async`. |
| `js-yaml` | `4.1.1` | Parse `data/known-loans.yml` | [VERIFIED: npm view js-yaml version → 4.1.1, published 2025-11-12]; same major as career-ops `^4.1.1`. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Node built-in `fs` (`writeFileSync`, `readFileSync`, `unlinkSync`, `existsSync`) | — | Lockfile primitives | All file operations; no external dep needed for the simple read-then-write lockfile. |
| Node built-in `crypto` (`createHash`) | — | SHA-256 of report bodies (optional, mirrors career-ops `insert-pdf`) | Phase 10 may need it for report deduplication; Phase 9 does not. |
| Node built-in `path`, `url` | — | Resolve `__dirname` from `import.meta.url` (ESM) | Career-ops pattern (`db-write.mjs:21-27`). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `duckdb-async` | `@duckdb/node-api` (the next-gen "neo" binding) | [CITED: https://www.npmjs.com/package/@duckdb/node-api] Newer API surface, but career-ops uses `duckdb-async` and PERS-03/04/05 say "career-ops pattern" verbatim. Stay aligned. |
| `duckdb-async` | Python `duckdb` package called from Python `lib/` directly | DuckDB takes a file-level lock that excludes cross-process access ([CITED: https://duckdb.org/docs/current/connect/concurrency]). If Node ever holds the writer, Python read-only opens fail. Single-language ownership (Node) is simpler. |
| Custom `lockfile.mjs` (read-then-write + mtime) | `proper-lockfile` npm package | [CITED: https://github.com/moxystudio/node-proper-lockfile] `proper-lockfile` uses `mkdir` for cross-platform atomic acquire and is more correct on NFS, but career-ops doesn't use it and PERS-04 says "career-ops pattern". Note the deviation if we ever harden against multi-machine concurrency. |
| Pure Python `duckdb` writer | Node `db-write.mjs` | PERS-03/04/05 require Node; the career-ops pattern is the load-bearing convention. Python can read JSON from `db-write.mjs query` if needed. |

**Installation (root `package.json`, recommended location per point (j)):**

```bash
cd /Users/cujo253/Documents/mortgage-ops
npm init -y
npm pkg set type=module
npm install duckdb-async@1.4.2 js-yaml@4.1.1
```

Then add scripts:

```json
{
  "scripts": {
    "init-db": "node orchestration/init-db.mjs",
    "db-write": "node orchestration/db-write.mjs"
  }
}
```

**Version verification (re-run before locking the plan):**

```bash
npm view duckdb-async version
npm view js-yaml version
```

## Architecture Patterns

### System Architecture Diagram

```
                ┌─────────────────────────────────────────────────────┐
                │  scripts/{amortize,affordability,arm_simulate}.py   │
                │  (Python calc engine — emits JSON on stdout)        │
                └──────────────────────┬──────────────────────────────┘
                                       │ JSON envelope
                                       ▼
            ┌──────────────────────────────────────────────────────────┐
            │  orchestration/db-write.mjs <subcmd> --json <path>       │
            │  (Single Node writer; one process at a time)             │
            │                                                          │
            │  1. acquireLock() ← lockfile.mjs                         │
            │     └─ read data/.mortgage-ops.duckdb.lock                │
            │        ├─ absent or mtime > 60s → write {pid,acquired_at}│
            │        └─ else: poll every 100ms up to 30s timeout       │
            │                                                          │
            │  2. Database.create(data/mortgage-ops.duckdb)            │
            │     └─ duckdb-async opens with OS file lock              │
            │                                                          │
            │  3. BEGIN TRANSACTION                                    │
            │     ├─ INSERT into loans / scenarios / payments / ...    │
            │     ├─ DECIMAL columns: parameterized inserts pass strings│
            │     └─ COMMIT  (rollback on throw)                       │
            │                                                          │
            │  4. db.close()                                           │
            │  5. releaseLock() ← unlinkSync(lock path)                │
            └──────────────────────────┬───────────────────────────────┘
                                       │ writes
                                       ▼
            ┌──────────────────────────────────────────────────────────┐
            │  data/mortgage-ops.duckdb  (single-file ACID)            │
            │  + .duckdb-wal  (write-ahead log; gitignored)            │
            │  + .duckdb-shm  (shared mem; gitignored)                 │
            └──────────────────────────┬───────────────────────────────┘
                                       │ SELECT (ORDER BY id, CAST AS VARCHAR)
                                       ▼
            ┌──────────────────────────────────────────────────────────┐
            │  orchestration/db-write.mjs --render-markdown            │
            │  → data/loans.md, data/scenarios.md (regenerated views;  │
            │    byte-identical across runs; no hand-edits)            │
            └──────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
mortgage-ops/
├── package.json                 # NEW: type=module, deps duckdb-async + js-yaml
├── orchestration/               # NEW (System Layer per DATA_CONTRACT.md)
│   ├── init-db.mjs              # idempotent CREATE TABLE IF NOT EXISTS
│   ├── db-write.mjs             # central writer with subcommands
│   └── lockfile.mjs             # acquireLock/releaseLock/withLock
├── data/
│   ├── known-loans.yml          # NEW: 7 product entries (Reference Layer)
│   ├── mortgage-ops.duckdb      # generated; gitignored
│   ├── .mortgage-ops.duckdb.lock  # ephemeral; should be gitignored
│   ├── loans.md                 # NEW: regenerated view; gitignored
│   └── scenarios.md             # NEW: regenerated view; gitignored
├── tests/
│   └── test_phase09_persistence.py  # NEW: parallel-invocation + stale-lock tests
└── lib/, scripts/, ...          # unchanged
```

### Pattern 1: Idempotent Schema Init

**What:** `init-db.mjs` runs `CREATE TABLE IF NOT EXISTS` for every table; running twice on a fresh checkout produces zero errors and a deterministic schema.

**When to use:** Every `npm run init-db` invocation (post-clone, post-schema-bump). Schema bumps are forward-only via the `schema_version` table.

**Example (career-ops uses `runSafe()` to swallow Catalog errors; mortgage-ops adopts the cleaner `IF NOT EXISTS` form supported by DuckDB):**

```javascript
// Source: career-ops/scripts/init-db.mjs:184-210 (runSafe pattern)
// Mortgage-ops simplification: prefer IF NOT EXISTS where DuckDB supports it.
const TABLES = [
  `CREATE TABLE IF NOT EXISTS schema_version (
     version INTEGER PRIMARY KEY,
     applied_at TIMESTAMP NOT NULL DEFAULT now()
   )`,
  // ... see "Pinned Schema DDL" below for all tables
];

for (const stmt of TABLES) {
  await db.run(stmt);
}

// Stamp the current schema version (idempotent INSERT)
await db.run(
  `INSERT INTO schema_version (version) VALUES (1)
   ON CONFLICT (version) DO NOTHING`
);
```

### Pattern 2: withLock-Wrapped Write

**What:** Every write subcommand is wrapped in `withLock()` so two parallel `node db-write.mjs --insert-loan ...` invocations serialize.

**When to use:** Any subcommand that mutates the DB (`insert-loan`, `insert-scenario`, `insert-report`, `render-markdown`). Read-only subcommands (`query --sql "SELECT ..."`) skip the lock.

**Example:**

```javascript
// Source: career-ops/scripts/db-write.mjs:719-740 (lock dispatcher pattern)
const WRITE_COMMANDS = new Set([
  'insert-loan', 'insert-scenario', 'insert-report',
  'render-markdown',
]);

const action = async () => {
  const db = await Database.create(DB_PATH);
  try {
    await handler(db);
  } finally {
    await db.close();
  }
};

if (WRITE_COMMANDS.has(command)) {
  await withLock(action, { reason: command });
} else {
  await action();
}
```

### Pattern 3: Decimal-Safe SELECT (mortgage-ops-specific)

**What:** Every SELECT that returns a money column wraps it in `CAST(col AS VARCHAR)` so duckdb-async hands JavaScript a string, not a `bigint`.

**When to use:** Always, for `loans.principal`, `loans.apr`, `payments.principal_paid`, `payments.interest_paid`, `payments.balance`, `applicants.income`, `applicants.monthly_debts`, `properties.value`, and any other DECIMAL column. (See "Pitfall 1" below.)

**Example:**

```javascript
// CORRECT — money round-trips losslessly:
const rows = await db.all(`
  SELECT id,
         CAST(principal AS VARCHAR) AS principal,
         CAST(apr AS VARCHAR) AS apr,
         term_months,
         strftime(origination_date, '%Y-%m-%d') AS origination_date,
         loan_type
  FROM loans
  ORDER BY id ASC
`);
// rows[0].principal === "200000.00"  (string; safe to write to YAML/JSON or feed back to Python)

// WRONG — silent precision loss:
const rows = await db.all(`SELECT principal FROM loans`);
// rows[0].principal === 20000000n  (bigint; scale=2 means "divide by 100")
//                                  if anyone calls Number(20000000n) → 20000000 → /100 → 200000
//                                  but for huge values the round-trip is lossy.
```

### Anti-Patterns to Avoid

- **Returning DECIMAL as bigint and converting in JS via `Number(value) / 100`:** Works for small values, breaks silently for principals > Number.MAX_SAFE_INTEGER / 10^scale. Always `CAST AS VARCHAR` in SQL.
- **Skipping `BEGIN TRANSACTION` for multi-row inserts:** Career-ops wraps every batch in `BEGIN/COMMIT` with rollback (`db-write.mjs:226-252`). A scenario insert that touches `scenarios` + `reports` + `payments` MUST be a transaction.
- **Hand-editing `data/loans.md`:** It is a regenerated view. Career-ops adds the comment `<!-- Generated from data/career-ops.duckdb — edit via scripts, not directly -->` on line 1 (`db-write.mjs:610`). Mortgage-ops should mirror this.
- **Opening the DuckDB file from Python while Node holds the writer:** DuckDB's OS-level file lock excludes cross-process access. Either close the Node connection first or use `db-write.mjs query --sql ...` from Python via subprocess.
- **Skipping `ORDER BY id ASC` in render-markdown SELECTs:** Without an explicit ORDER BY, row order is non-deterministic; SC-4 (byte-identical regeneration) breaks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-process write coordination | Custom semaphore in Python | `withLock()` from career-ops `lockfile.mjs` (port verbatim) | Career-ops already shipped this; race window known and documented; scope creep risk if we re-design. |
| DuckDB file format | Custom JSON-on-disk store | DuckDB single file | DuckDB gives us SQL, ACID, MVCC, and `--render-markdown` via SELECT. JSON-on-disk loses all of that. |
| YAML parsing | Custom YAML in Node | `js-yaml@4.1.1` | Same version as career-ops; well-trodden. |
| Idempotent CREATE TABLE | Catch-and-ignore exceptions | DuckDB native `CREATE TABLE IF NOT EXISTS` | Cleaner than career-ops `runSafe()`; DuckDB supports it. (Career-ops did it the other way because some objects like sequences/types in older DuckDB lacked IF NOT EXISTS.) |
| Decimal arithmetic in JS | Custom big-decimal lib in Node | Push everything to Python via JSON envelope | Node never owns numbers per CLAUDE.md "Calc engine separation." Node only persists strings. |

**Key insight:** Mortgage-ops Phase 9 is a **persistence and orchestration phase**, not a calc phase. Resist any temptation to compute in Node. Node receives Python JSON, INSERTs the values as strings into DECIMAL columns, and SELECTs them back as strings.

## Pinned Schema DDL

Copy these CREATE statements verbatim into `orchestration/init-db.mjs`. All money columns are `DECIMAL(14,2)` to match Pydantic v2 `condecimal(max_digits=14, decimal_places=2)` (PERS-01 / FND-02 / `lib/models.py:23-26`). Rate columns are `DECIMAL(7,6)` to match `lib/models.py:30-33`.

```sql
-- 1. Schema version (forward-only migrations)
CREATE TABLE IF NOT EXISTS schema_version (
  version    INTEGER PRIMARY KEY,
  applied_at TIMESTAMP NOT NULL DEFAULT now()
);

-- 2. Loans (top-level scenario subject)
CREATE SEQUENCE IF NOT EXISTS loans_id_seq START 1;
CREATE TABLE IF NOT EXISTS loans (
  id                INTEGER       PRIMARY KEY DEFAULT nextval('loans_id_seq'),
  principal         DECIMAL(14,2) NOT NULL,
  apr               DECIMAL(7,6)  NOT NULL CHECK (apr >= 0 AND apr <= 1),
  -- 'apr' here is the contractual annual interest rate (lib.models.Loan.annual_rate);
  -- the Reg-Z "estimated APR" lives in scenarios.response_json (Phase 7 product).
  term_months       INTEGER       NOT NULL CHECK (term_months BETWEEN 1 AND 600),
  origination_date  DATE,
  loan_type         VARCHAR       NOT NULL CHECK (loan_type IN
                      ('fixed','arm','fha','va','usda','jumbo')),
  frequency         VARCHAR       NOT NULL DEFAULT 'monthly'
                      CHECK (frequency IN ('monthly','biweekly')),
  known_loan_id     VARCHAR,           -- nullable FK to data/known-loans.yml entries
  notes             VARCHAR,
  created_at        TIMESTAMP     NOT NULL DEFAULT now(),
  updated_at        TIMESTAMP     NOT NULL DEFAULT now()
);

-- 3. Scenarios (one row per calc invocation: amortize, affordability, refi, arm, stress, points, apr)
CREATE SEQUENCE IF NOT EXISTS scenarios_id_seq START 1;
CREATE TABLE IF NOT EXISTS scenarios (
  id            INTEGER       PRIMARY KEY DEFAULT nextval('scenarios_id_seq'),
  loan_id       INTEGER,                                  -- nullable for affordability (no loan yet)
  kind          VARCHAR       NOT NULL CHECK (kind IN
                  ('amortize','affordability','arm','refi','apr','stress','points')),
  request_json  JSON          NOT NULL,                   -- the Python script's input envelope
  response_json JSON          NOT NULL,                   -- the Python script's output envelope
  computed_at   TIMESTAMP     NOT NULL DEFAULT now(),
  notes         VARCHAR
);

-- 4. Reports (markdown blobs generated downstream by the Claude skill in Phase 10)
CREATE SEQUENCE IF NOT EXISTS reports_id_seq START 1;
CREATE TABLE IF NOT EXISTS reports (
  id              INTEGER     PRIMARY KEY DEFAULT nextval('reports_id_seq'),
  scenario_id     INTEGER     NOT NULL,
  markdown_blob   TEXT        NOT NULL,
  generated_at    TIMESTAMP   NOT NULL DEFAULT now()
);

-- 5. Payments (amortization schedule rows; one row per (loan_id, period))
CREATE TABLE IF NOT EXISTS payments (
  loan_id              INTEGER       NOT NULL,
  period               INTEGER       NOT NULL CHECK (period >= 1),
  payment_date         DATE          NOT NULL,
  payment              DECIMAL(14,2) NOT NULL,
  principal_paid       DECIMAL(14,2) NOT NULL,
  interest_paid        DECIMAL(14,2) NOT NULL,
  extra_principal      DECIMAL(14,2) NOT NULL DEFAULT 0,
  balance              DECIMAL(14,2) NOT NULL,
  cumulative_interest  DECIMAL(14,2) NOT NULL DEFAULT 0,
  cumulative_principal DECIMAL(14,2) NOT NULL DEFAULT 0,
  PRIMARY KEY (loan_id, period)
);

-- 6. Applicants (one row per applicant per loan; supports joint applications)
CREATE SEQUENCE IF NOT EXISTS applicants_id_seq START 1;
CREATE TABLE IF NOT EXISTS applicants (
  id                     INTEGER       PRIMARY KEY DEFAULT nextval('applicants_id_seq'),
  loan_id                INTEGER       NOT NULL,
  credit_score           INTEGER       NOT NULL CHECK (credit_score BETWEEN 300 AND 850),
  gross_monthly_income   DECIMAL(14,2) NOT NULL,
  monthly_debts          DECIMAL(14,2) NOT NULL DEFAULT 0,
  applicant_label        VARCHAR                                  -- e.g. 'primary', 'co-borrower'
);

-- 7. Properties (one row per loan; v1 single-property, v2 may relax)
CREATE SEQUENCE IF NOT EXISTS properties_id_seq START 1;
CREATE TABLE IF NOT EXISTS properties (
  id           INTEGER       PRIMARY KEY DEFAULT nextval('properties_id_seq'),
  loan_id      INTEGER       NOT NULL,
  value        DECIMAL(14,2) NOT NULL,
  state_fips   VARCHAR(2)    NOT NULL CHECK (state_fips ~ '^\d{2}$'),
  county_fips  VARCHAR(3)    NOT NULL CHECK (county_fips ~ '^\d{3}$'),
  property_tax_monthly DECIMAL(14,2) NOT NULL DEFAULT 0,
  insurance_monthly    DECIMAL(14,2) NOT NULL DEFAULT 0,
  hoa_monthly          DECIMAL(14,2) NOT NULL DEFAULT 0
);

-- 8. Indexes (named so init-db.mjs can pre-check existence per career-ops:172-182)
CREATE INDEX IF NOT EXISTS idx_loans_loan_type     ON loans(loan_type);
CREATE INDEX IF NOT EXISTS idx_scenarios_loan      ON scenarios(loan_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_kind      ON scenarios(kind);
CREATE INDEX IF NOT EXISTS idx_reports_scenario    ON reports(scenario_id);
CREATE INDEX IF NOT EXISTS idx_payments_loan       ON payments(loan_id);
CREATE INDEX IF NOT EXISTS idx_applicants_loan     ON applicants(loan_id);
CREATE INDEX IF NOT EXISTS idx_properties_loan     ON properties(loan_id);

-- 9. Stamp schema version
INSERT INTO schema_version (version) VALUES (1)
ON CONFLICT (version) DO NOTHING;
```

**Notes on schema choices:**

- **No FOREIGN KEY constraints.** DuckDB does not enforce FKs at write time the way Postgres does ([CITED: https://duckdb.org/docs/current/sql/data_types/overview]); they're parsed but not validated. We rely on application-level invariants in `db-write.mjs` instead. This matches career-ops which has no FKs (`init-db.mjs:36-150`).
- **Sequences vs `INTEGER PRIMARY KEY` autoincrement.** Career-ops uses explicit `CREATE SEQUENCE` + `DEFAULT nextval(...)` (`init-db.mjs:26-33`); we adopt the same pattern for portability and explicit control.
- **`payments` has no synthetic id.** `(loan_id, period)` is the natural key. This matches `lib.models.Payment.period` semantics.
- **`apr` precision.** `DECIMAL(7,6)` matches `lib/models.py:30-33` `Rate = Annotated[Decimal, Field(max_digits=7, decimal_places=6, ge=0, le=1)]`. Rates expressed as fractions (0.065 = 6.5%).
- **`apr` column name.** The roadmap spec called it `apr`; for the **Loan** table this is the contractual annual interest rate (Pydantic field name `annual_rate`). The Reg-Z "estimated APR" computed in Phase 7 is a derived value that lives in `scenarios.response_json` for `kind='apr'`. **Open question:** rename column to `annual_rate` to match `lib.models.Loan.annual_rate` and avoid confusion with Reg-Z APR? (See Open Questions §1.)

## Sample `data/known-loans.yml`

This file lives in the **Reference Layer** (committed; per `DATA_CONTRACT.md` line 67). Each entry must include `source:` URL and `effective:` date per the staleness convention. Sample with all 7 required products:

```yaml
# data/known-loans.yml
# mortgage-ops product catalog. Reference Layer (committed; manually refreshed).
# Each entry is a representative product, not a live offer; rates from FRED PMMS week
# of 2026-04-24 (MORTGAGE30US 6.81%, MORTGAGE15US 6.05%) for the conforming products,
# and from agency rate-sheet samples for FHA/VA/jumbo/ARM.

source: https://www.freddiemac.com/pmms
effective: 2026-04-24

products:
  - id: conv-30yr-fixed
    label: "Conventional 30-year fixed"
    type: fixed
    principal: "400000.00"
    apr: "0.068100"             # FRED MORTGAGE30US 2026-04-24
    term_months: 360
    frequency: monthly
    origination_date: 2026-05-01
    citation_url: https://fred.stlouisfed.org/series/MORTGAGE30US

  - id: conv-15yr-fixed
    label: "Conventional 15-year fixed"
    type: fixed
    principal: "400000.00"
    apr: "0.060500"             # FRED MORTGAGE15US 2026-04-24
    term_months: 180
    frequency: monthly
    origination_date: 2026-05-01
    citation_url: https://fred.stlouisfed.org/series/MORTGAGE15US

  - id: arm-5-1
    label: "5/1 ARM (5-year initial fixed, annual reset thereafter)"
    type: arm
    principal: "400000.00"
    apr: "0.062500"             # initial 5yr fixed rate (representative)
    term_months: 360
    frequency: monthly
    origination_date: 2026-05-01
    citation_url: https://www.consumerfinance.gov/owning-a-home/loan-options/adjustable-rate-mortgages/

  - id: arm-7-1
    label: "7/1 ARM (7-year initial fixed, annual reset thereafter)"
    type: arm
    principal: "400000.00"
    apr: "0.064000"             # initial 7yr fixed rate (representative)
    term_months: 360
    frequency: monthly
    origination_date: 2026-05-01
    citation_url: https://www.consumerfinance.gov/owning-a-home/loan-options/adjustable-rate-mortgages/

  - id: fha-30yr
    label: "FHA 30-year fixed"
    type: fha
    principal: "400000.00"
    apr: "0.066500"             # representative; FHA typically slightly below conv
    term_months: 360
    frequency: monthly
    origination_date: 2026-05-01
    citation_url: https://www.hud.gov/program_offices/housing/sfh/ins/sfh203b

  - id: va-30yr
    label: "VA 30-year fixed"
    type: va
    principal: "400000.00"
    apr: "0.063500"             # representative; VA often lowest
    term_months: 360
    frequency: monthly
    origination_date: 2026-05-01
    citation_url: https://www.benefits.va.gov/HOMELOANS/

  - id: jumbo-30yr-fixed
    label: "Jumbo 30-year fixed (above 2026 conforming limit)"
    type: jumbo
    principal: "1000000.00"     # > 2026 conforming baseline ($806,500)
    apr: "0.069500"             # representative; jumbo varies widely
    term_months: 360
    frequency: monthly
    origination_date: 2026-05-01
    citation_url: https://www.fhfa.gov/news/news-release/conforming-loan-limit-values-2026
```

**Smoke test (per SC-5):**

```python
# tests/test_phase09_known_loans.py
import yaml
from pathlib import Path

REQUIRED_IDS = {
    "conv-30yr-fixed", "conv-15yr-fixed",
    "arm-5-1", "arm-7-1",
    "fha-30yr", "va-30yr", "jumbo-30yr-fixed",
}

def test_known_loans_catalog_complete():
    path = Path("data/known-loans.yml")
    catalog = yaml.safe_load(path.read_text())
    assert "source" in catalog and "effective" in catalog
    ids = {p["id"] for p in catalog["products"]}
    assert REQUIRED_IDS.issubset(ids), f"missing: {REQUIRED_IDS - ids}"
    for p in catalog["products"]:
        assert {"id","label","type","principal","apr","term_months",
                "frequency","origination_date","citation_url"} <= set(p.keys())
```

## Test Designs

### Parallel-Invocation Test (SC-2)

**Goal:** Two concurrent `db-write.mjs --insert-loan` processes — one succeeds, the other either waits-then-succeeds (preferred) or fails with a clear lock-timeout error. Final SELECT count is exactly 2 (atomicity preserved).

```python
# tests/test_phase09_parallel_writes.py
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
ORCH = REPO / "orchestration"
DB = REPO / "data" / "mortgage-ops.duckdb"

def _spawn_insert(fixture_path: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        ["node", str(ORCH / "db-write.mjs"), "insert-loan",
         "--json", str(fixture_path)],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

def test_parallel_inserts_dont_corrupt(tmp_path: Path):
    # Pre-init the DB
    subprocess.run(["node", str(ORCH / "init-db.mjs")], check=True, cwd=REPO)
    # Snapshot baseline count via Node query
    result = subprocess.run(
        ["node", str(ORCH / "db-write.mjs"), "query",
         "--sql", "SELECT count(*) AS n FROM loans"],
        capture_output=True, text=True, cwd=REPO, check=True,
    )
    baseline = json.loads(result.stdout)[0]["n"]

    # Two distinct fixture loans
    fx_a = tmp_path / "loan_a.json"
    fx_b = tmp_path / "loan_b.json"
    fx_a.write_text(json.dumps({
        "principal": "200000.00", "apr": "0.0650", "term_months": 360,
        "origination_date": "2026-05-01", "loan_type": "fixed",
    }))
    fx_b.write_text(json.dumps({
        "principal": "300000.00", "apr": "0.0675", "term_months": 360,
        "origination_date": "2026-05-01", "loan_type": "fixed",
    }))

    # Spawn both simultaneously
    p1 = _spawn_insert(fx_a)
    p2 = _spawn_insert(fx_b)
    rc1 = p1.wait(timeout=60)
    rc2 = p2.wait(timeout=60)

    # Both must exit cleanly (lock waiter is the expected behavior; fail-fast is acceptable)
    # If either failed, the failure must be a lock timeout, not a DB corruption error.
    assert rc1 == 0 and rc2 == 0, (
        f"rc1={rc1} stderr={p1.stderr.read().decode()} "
        f"rc2={rc2} stderr={p2.stderr.read().decode()}"
    )

    # Atomicity: final count is baseline + 2 (no partial inserts, no double inserts)
    result = subprocess.run(
        ["node", str(ORCH / "db-write.mjs"), "query",
         "--sql", "SELECT count(*) AS n FROM loans"],
        capture_output=True, text=True, cwd=REPO, check=True,
    )
    final = json.loads(result.stdout)[0]["n"]
    assert final == baseline + 2, f"baseline={baseline} final={final}"

    # Lockfile must be released (no leak)
    assert not (REPO / "data" / ".mortgage-ops.duckdb.lock").exists()
```

**Race window note:** The career-ops `acquireLock` (`lockfile.mjs:34-55`) reads the lock, then writes. Between read and write, another process could write its own lock and we would clobber it. Read-back verification (`readBack.pid === process.pid`) closes most of the window but not all of it. For two processes spawned milliseconds apart, the polling loop with 100ms intervals (`POLL_INTERVAL_MS`) means one will typically get the lock and the other will see it on the next poll. **The test must tolerate either ordering** — the assertion is on the final state, not on which process won.

### Stale-Lockfile-Recovery Test (SC-3)

**Goal:** A pre-existing lockfile with `mtime > 60s ago` is reclaimed by a fresh `db-write.mjs` invocation; the write proceeds.

```python
# tests/test_phase09_stale_lockfile.py
import json
import os
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
ORCH = REPO / "orchestration"
LOCK = REPO / "data" / ".mortgage-ops.duckdb.lock"

def test_stale_lockfile_is_reclaimed(tmp_path: Path):
    subprocess.run(["node", str(ORCH / "init-db.mjs")], check=True, cwd=REPO)

    # Pre-create a stale lockfile (acquired_at = 65s ago)
    stale_acquired_at = int((time.time() - 65) * 1000)  # JS Date.now() is ms
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({
        "pid": 99999,                # bogus PID
        "acquired_at": stale_acquired_at,
        "reason": "stale-test-fixture",
    }, indent=2))

    # Belt-and-suspenders: also set the file's mtime to 65s ago, in case any
    # implementation prefers mtime over the JSON acquired_at field.
    sixty_five_s_ago = time.time() - 65
    os.utime(LOCK, (sixty_five_s_ago, sixty_five_s_ago))

    # Now run a write — it should reclaim the lock and succeed
    fx = tmp_path / "loan.json"
    fx.write_text(json.dumps({
        "principal": "150000.00", "apr": "0.0700", "term_months": 180,
        "origination_date": "2026-05-01", "loan_type": "fixed",
    }))

    result = subprocess.run(
        ["node", str(ORCH / "db-write.mjs"), "insert-loan", "--json", str(fx)],
        capture_output=True, text=True, cwd=REPO, timeout=30,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert not LOCK.exists(), "lock should be released after the write completes"
```

## Common Pitfalls

### Pitfall 1: DECIMAL Coercion Through duckdb-async (CRITICAL)

**What goes wrong:** A SELECT on a DECIMAL column returns a JavaScript `bigint` containing the raw integer (scaled by `10^scale`), not the decimal value. If we later `JSON.stringify(rows)` or feed the value back to Python, we silently lose information — either the bigint serialization fails (default `JSON.stringify` throws on bigint) or someone writes a `Number(value) / 100` workaround that loses precision for large values.

**Why it happens:** [VERIFIED via web search 2026-05-02] DuckDB stores DECIMAL with width ≤ 18 as INT64 internally; the Node binding returns it as `bigint`. The career-ops `jsonReplacer` (`db-write.mjs:651-657`) coerces bigint → Number, which is *acceptable for IDs* (small integers) but **wrong for money**. Career-ops sidesteps this by `CAST(score AS DOUBLE)` in the dashboard JSON SELECT (`db-write.mjs:567`); for mortgage-ops, DOUBLE is also lossy.

**How to avoid:**
- **Every SELECT touching a money/rate column wraps it in `CAST(col AS VARCHAR)`.** The Node code never sees a decimal as a number.
- INSERT statements pass strings (`"200000.00"`); DuckDB parses them into DECIMAL during binding.
- If a JSON serializer encounters a DECIMAL value (defensive belt-and-suspenders), serialize it as a string, never via `Number()`.

**Warning signs:**
- `JSON.stringify` throws "Do not know how to serialize a BigInt".
- A round-trip Python → Node → DuckDB → Node → Python changes a money value.
- Tests pass for `principal=200000` but fail for `principal=200000.01`.

### Pitfall 2: Lockfile Race Window (DOCUMENTED — INHERITED FROM CAREER-OPS)

**What goes wrong:** Two `db-write.mjs` processes started within 1ms of each other could both observe "lock absent or stale" and both call `writeFileSync`. The second write clobbers the first; the read-back check (`readBack.pid === process.pid`) on the loser fails, so the loser retries. In the worst case, both winners proceed past `acquireLock` simultaneously and DuckDB itself has to serialize via its OS file lock (which it does — DuckDB's lock kicks in inside `Database.create`).

**Why it happens:** `lockfile.mjs:42` uses `writeFileSync(path, ..., { flag: 'w' })` rather than `'wx'` (which would be `O_EXCL | O_CREAT | O_WRONLY` and fail if the file exists). The flag `'w'` truncates and writes unconditionally. The author chose this because `O_EXCL` is broken on NFS ([CITED: https://lwn.net/Articles/251004/]) and the simpler approach is good enough for a single-machine, single-user tool.

**How to avoid (for v1, we accept the risk):**
- DuckDB's own OS file lock is the second line of defense. If both processes pass `acquireLock`, only one will get past `Database.create()`; the second blocks until the first closes.
- The test in SC-2 verifies that the **end state** is correct (count == 2, no corruption), not that one specific process wins.

**How to fix later (v2 if needed):**
- Switch `writeFileSync` to `openSync(path, 'wx')` and catch `EEXIST` as "lock held". Loses NFS support, gains true atomicity on local FS.
- Or adopt `proper-lockfile` ([CITED: https://github.com/moxystudio/node-proper-lockfile]) which uses `mkdir` for cross-platform atomicity.

**Warning signs:**
- The SC-2 test exhibits flakiness when run in tight CI loops.
- Stale lockfiles accumulate (would indicate `releaseLock` is being skipped — different bug).

### Pitfall 3: Render-Markdown Determinism

**What goes wrong:** SC-4 requires `data/loans.md` and `data/scenarios.md` to be **byte-identical** across runs. Two failure modes:
1. SELECT without `ORDER BY` — DuckDB can return rows in any order based on internal pagination.
2. `generated_at` timestamps embedded in the markdown — every regeneration changes the timestamp, breaking byte-equality.

**Why it happens:** Career-ops embeds the comment `<!-- Generated from data/career-ops.duckdb — edit via scripts, not directly -->` (`db-write.mjs:610`) but **no timestamp** — that's deliberate. The `applications.md` body uses `ORDER BY applied_date, id` (`db-write.mjs:601`).

**How to avoid:**
- **Every render-markdown SELECT has explicit `ORDER BY id ASC`** (or `ORDER BY (loan_id, period)` for payments).
- **Do not embed `generated_at` in the markdown output.** Career-ops gets this right; mortgage-ops must too.
- If a "last regenerated" timestamp is wanted for human readability, store it in a sidecar file (e.g., `data/loans.md.generated_at`) that is NOT compared for byte-equality.

**Warning signs:**
- SC-4 test passes the first time but fails the second.
- `git diff data/loans.md` shows row reordering with no schema change.

### Pitfall 4: Cross-Process DuckDB Access Excluded

**What goes wrong:** Python `lib/` opens `data/mortgage-ops.duckdb` for read while Node holds the writer; DuckDB raises `IO Error: Could not set lock on file`. ([CITED: https://github.com/duckdb/duckdb/issues/17158])

**Why it happens:** [CITED: https://duckdb.org/docs/current/connect/concurrency] DuckDB's process-level file lock is exclusive — even read-only opens fail when a writer is active in another process.

**How to avoid:**
- Default stance for v1: **Python `lib/` never opens DuckDB.** All reads go through `node orchestration/db-write.mjs query --sql "..."` from a Python `subprocess.run` call, parsing the JSON output.
- If a future phase requires direct Python read access (e.g., for performance), it must be gated on Node having no active writer (a separate `withLock`-aware reader pattern).

**Warning signs:**
- Python tests intermittently fail with `IO Error` when run in CI alongside Node integration tests.

### Pitfall 5: Lockfile Path Not Gitignored

**What goes wrong:** `data/.mortgage-ops.duckdb.lock` ends up tracked by git after a developer runs `db-write.mjs` mid-commit; subsequent CI clones see a stale lock blocking writes for 60s.

**Why it happens:** The current `.gitignore` (`/Users/cujo253/Documents/mortgage-ops/.gitignore`) covers `data/*.duckdb`, `data/mortgage-ops.duckdb-wal`, `data/mortgage-ops.duckdb-shm` but **not** `.mortgage-ops.duckdb.lock`.

**How to avoid:** Add the lockfile to `.gitignore` in Phase 9:

```
# Phase 9: DuckDB writer lockfile (ephemeral)
data/.mortgage-ops.duckdb.lock
```

**Warning signs:** `git status` shows `data/.mortgage-ops.duckdb.lock` as untracked (it should be ignored, not just untracked).

## Code Examples

### Example 1: Loading `known-loans.yml` in Node (SC-5 smoke)

```javascript
// orchestration/db-write.mjs (excerpt)
import yaml from 'js-yaml';
import { readFileSync } from 'fs';

function loadKnownLoans() {
  const path = join(MORTGAGE_OPS, 'data', 'known-loans.yml');
  const raw = readFileSync(path, 'utf-8');
  const catalog = yaml.load(raw);
  if (!catalog.products || !Array.isArray(catalog.products)) {
    throw new Error(`known-loans.yml missing 'products' array`);
  }
  return catalog;
}
```

### Example 2: insert-loan Subcommand (with money discipline)

```javascript
// orchestration/db-write.mjs (excerpt)
async function cmdInsertLoan(db, flags) {
  const { json: jsonPath } = flags;
  if (!jsonPath) throw new Error('--json required');
  const payload = JSON.parse(readFileSync(jsonPath, 'utf-8'));
  // payload comes from a Python script's JSON envelope; money fields are STRINGS.
  // We pass them through untouched; DuckDB parses them into DECIMAL during binding.

  await db.run('BEGIN TRANSACTION');
  try {
    const row = await db.all(
      `INSERT INTO loans (principal, apr, term_months, origination_date, loan_type, frequency)
       VALUES (?, ?, ?, ?, ?, ?)
       RETURNING id`,
      payload.principal,        // string "200000.00" → DECIMAL(14,2)
      payload.apr,              // string "0.065000"  → DECIMAL(7,6)
      payload.term_months,
      payload.origination_date,
      payload.loan_type,
      payload.frequency || 'monthly',
    );
    await db.run('COMMIT');
    console.log(JSON.stringify({ ok: true, loan_id: Number(row[0].id) }));
  } catch (e) {
    await db.run('ROLLBACK');
    throw e;
  }
}
```

### Example 3: render-markdown for `data/loans.md` (deterministic)

```javascript
// orchestration/db-write.mjs (excerpt)
async function cmdRenderMarkdown(db) {
  const rows = await db.all(`
    SELECT id,
           CAST(principal AS VARCHAR) AS principal,
           CAST(apr AS VARCHAR)       AS apr,
           term_months,
           strftime(origination_date, '%Y-%m-%d') AS origination_date,
           loan_type,
           frequency
    FROM loans
    ORDER BY id ASC
  `);
  const header = [
    `<!-- Generated from data/mortgage-ops.duckdb — edit via scripts, not directly -->`,
    `# Loans`,
    ``,
    `| ID | Principal | APR | Term (mo) | Origination | Type | Frequency |`,
    `|----|-----------|-----|-----------|-------------|------|-----------|`,
  ];
  const body = rows.map(r =>
    `| ${r.id} | ${r.principal} | ${r.apr} | ${r.term_months} | ${r.origination_date} | ${r.loan_type} | ${r.frequency} |`
  ).join('\n');
  writeFileSync(LOANS_MD, header.join('\n') + '\n' + body + '\n', 'utf-8');
  console.log(`loans.md: ${rows.length} rows`);
}
```

### Example 4: Calling Node Reader From Python (recommended cross-language pattern)

```python
# scripts/_db_reader.py (suggested helper for any Python script that needs DB data)
import json
import subprocess
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).parent.parent
ORCH = REPO / "orchestration" / "db-write.mjs"

def query_loans() -> list[dict]:
    result = subprocess.run(
        ["node", str(ORCH), "query",
         "--sql", "SELECT id, CAST(principal AS VARCHAR) AS principal, "
                  "CAST(apr AS VARCHAR) AS apr, term_months "
                  "FROM loans ORDER BY id ASC"],
        capture_output=True, text=True, check=True, cwd=REPO,
    )
    rows = json.loads(result.stdout)
    # Money fields come back as strings (per Pitfall 1 discipline); promote to Decimal.
    for r in rows:
        r["principal"] = Decimal(r["principal"])
        r["apr"] = Decimal(r["apr"])
    return rows
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `duckdb@0.9.x` returning BIGINT as Number | `duckdb@1.x` returns BIGINT/DECIMAL as bigint | DuckDB v0.10+ (early 2024) | Breaking; required `jsonReplacer` workarounds in career-ops `db-write.mjs:651-657`. |
| Lockfile via `fcntl` (POSIX advisory locks) | Lockfile via JSON file + mtime staleness | career-ops design choice | Simpler; cross-platform; race window accepted. |
| `CREATE TABLE` + try/catch for "already exists" | `CREATE TABLE IF NOT EXISTS` | DuckDB has supported `IF NOT EXISTS` for tables since early versions; sequences gained `IF NOT EXISTS` more recently | Cleaner code; fewer try/catch swallows. |

**Deprecated/outdated:**
- `node-duckdb` (npm) — abandoned; use `duckdb-async` or `@duckdb/node-api` (the "neo" binding).
- DOUBLE-cast for money — was a viable workaround in 2024 when bigint serialization was uncertain; not acceptable now that we know `CAST AS VARCHAR` round-trips losslessly.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The career-ops `lockfile.mjs` race window is acceptable for mortgage-ops single-user desktop use | Pitfall 2 | If two writers slip past acquireLock, DuckDB's internal lock catches them; failure mode is "second writer blocks", not "data corruption". Acceptable. |
| A2 | Python `lib/` will not need direct DuckDB read access in v1 | Architectural Map; Pitfall 4 | If a future calc phase needs in-process SQL, we'll need a reader-coordination protocol (or accept that Node must be quiesced first). |
| A3 | DECIMAL(14,2) is sufficient for all money fields in all phases | Pinned Schema DDL | Matches `lib/models.py:25` Money type; matches Pydantic `condecimal(max_digits=14, decimal_places=2)` per FND-02. Caps at $99,999,999,999.99 — enough for any household scenario. |
| A4 | The `apr` column on `loans` should be `DECIMAL(7,6)` to match Rate type | Pinned Schema DDL | Matches `lib/models.py:31`. If we ever want to store rates with more precision, schema bump required. |
| A5 | `known-loans.yml` rates as of 2026-04-24 are the right anchor | Sample yaml | Phase 12 wires live FRED data; the catalog rates are representative samples, not live offers. Annual refresh by user. |
| A6 | `package.json` lives at repo root (point j) | Standard Stack §Installation | Two-package setup (`orchestration/package.json` separate) would avoid leaking `node_modules` into root, but is more complex; root-level matches career-ops. |
| A7 | The `apr` column on `loans` represents the **contractual annual rate** (Pydantic `Loan.annual_rate`), not Reg-Z estimated APR | Pinned Schema DDL | If misunderstood, downstream consumers might double-count APR adjustments. See Open Questions §1 — propose renaming to `annual_rate` for clarity. |

## Open Questions

1. **Rename `loans.apr` to `loans.annual_rate`?**
   - What we know: The roadmap success criteria spell it `apr DECIMAL(8,6)` (we tightened to `(7,6)` to match Rate type). But `lib/models.py:42` calls the Loan field `annual_rate`, and Phase 7 will introduce a separate "estimated APR" derived value (Reg Z Appendix J).
   - What's unclear: Will mixing the two cause confusion?
   - Recommendation: **Rename the column to `annual_rate`** for clarity and store Reg-Z APR exclusively in `scenarios.response_json` for `kind='apr'`. Surface this to the user during plan-discuss.

2. **Should `payments` carry the canonical `Payment.payment_date` from `lib.models.Payment`, or compute it on render?**
   - What we know: `lib/models.py:55` defines `payment_date: date` on `Payment`. Storing it makes joins simpler.
   - What's unclear: Do we ever need to recompute the schedule from the loan alone (e.g., when origination_date is updated)?
   - Recommendation: **Store it.** If origination_date changes, the entire schedule is invalidated and must be re-inserted — that's the v1 contract.

3. **Should `applicants` and `properties` use a `loan_id` FK, or a `scenario_id` FK?**
   - What we know: Affordability scenarios may not have a loan yet (reverse mode solves for loan amount). `scenarios.loan_id` is nullable for that reason.
   - What's unclear: For an affordability scenario, do we want to persist the candidate applicants/properties even though no loan row exists?
   - Recommendation: **Keep `loan_id` FK** for v1 (matches the roadmap success criterion). For affordability scenarios, persist the request envelope in `scenarios.request_json` and skip the `applicants`/`properties` rows. Phase 4 reverse-mode results live entirely in `scenarios.response_json`. Surface to user if they want richer applicant analytics.

4. **Does `db-write.mjs query` need a `--format markdown` option?**
   - What we know: Career-ops `cmdQuery` (`db-write.mjs:659-664`) returns JSON only.
   - What's unclear: For ad-hoc human inspection, JSON is harder to read than a markdown table.
   - Recommendation: Defer. Phase 9 ships `--format json` only; `--format markdown` can be added later if pain emerges.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | All `orchestration/*.mjs` scripts | ✓ (assumed; check `node --version` ≥ 18) | varies | None — install via system package manager. |
| npm | Installing `duckdb-async`, `js-yaml` | ✓ (assumed; ships with Node) | varies | `pnpm` or `yarn` would also work. |
| `duckdb-async@1.4.2` | All write paths | ✗ (not yet installed) | 1.4.2 | None — `npm install duckdb-async@1.4.2` |
| `js-yaml@4.1.1` | `known-loans.yml` parsing in Node | ✗ (not yet installed) | 4.1.1 | None — `npm install js-yaml@4.1.1` |
| Python `duckdb` (transitive via `pip show duckdb`) | NOT used by Phase 9 (Pitfall 4) | ✓ (1.4.4 installed) | 1.4.4 | N/A — Python should NOT touch DuckDB in v1. |
| Python `pyyaml` | Smoke test of `known-loans.yml` | ✓ (in `pyproject.toml` deps line 6) | ≥6.0.2 | None — already pinned. |

**Missing dependencies with no fallback:**
- `duckdb-async@1.4.2`, `js-yaml@4.1.1` — must be installed via `npm install` in the first plan of Phase 9.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` ≥9.0 (per `pyproject.toml` dev deps); Node has no test framework — use `pytest` to drive Node subprocesses |
| Config file | `pyproject.toml` (no separate pytest.ini in repo) |
| Quick run command | `uv run pytest tests/test_phase09_*.py -x` |
| Full suite command | `uv run pytest && uv run mypy --strict . && uv run ruff check .` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERS-01 | Schema has loans/scenarios/reports/payments/applicants/properties tables | integration | `pytest tests/test_phase09_schema.py::test_all_tables_present -x` | ❌ Wave 0 |
| PERS-02 | `init-db.mjs` is idempotent (run twice, no errors, same schema) | integration | `pytest tests/test_phase09_schema.py::test_init_db_idempotent -x` | ❌ Wave 0 |
| PERS-03 | `db-write.mjs --insert-loan --json fixtures/loan.json` succeeds | integration | `pytest tests/test_phase09_subcommands.py::test_insert_loan_basic -x` | ❌ Wave 0 |
| PERS-04 | Stale lockfile (mtime > 60s) is reclaimed | integration | `pytest tests/test_phase09_stale_lockfile.py::test_stale_lockfile_is_reclaimed -x` | ❌ Wave 0 |
| PERS-05 | Two parallel writers don't corrupt | integration | `pytest tests/test_phase09_parallel_writes.py::test_parallel_inserts_dont_corrupt -x` | ❌ Wave 0 |
| PERS-06 | `data/loans.md` regenerates byte-identically | integration | `pytest tests/test_phase09_render.py::test_render_markdown_byte_identical -x` | ❌ Wave 0 |
| PERS-07 | `data/known-loans.yml` has all 7 entries with required fields | unit | `pytest tests/test_phase09_known_loans.py::test_known_loans_catalog_complete -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_phase09_*.py -x` (~5-10s; spawns Node subprocesses)
- **Per wave merge:** `uv run pytest && uv run mypy --strict . && uv run ruff check .` (full suite green)
- **Phase gate:** Full suite + manual `node orchestration/init-db.mjs && node orchestration/init-db.mjs` (idempotency demo) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_phase09_schema.py` — covers PERS-01, PERS-02
- [ ] `tests/test_phase09_subcommands.py` — covers PERS-03 (insert-loan, insert-scenario, query)
- [ ] `tests/test_phase09_stale_lockfile.py` — covers PERS-04
- [ ] `tests/test_phase09_parallel_writes.py` — covers PERS-05
- [ ] `tests/test_phase09_render.py` — covers PERS-06 (byte-identical regeneration)
- [ ] `tests/test_phase09_known_loans.py` — covers PERS-07
- [ ] `tests/conftest.py` — shared fixtures: `repo_root`, `clean_db`, helper to spawn `node` subprocesses with timeout
- [ ] Framework install: `npm install duckdb-async@1.4.2 js-yaml@4.1.1` (first plan of Phase 9)
- [ ] `package.json` at repo root with `"type": "module"` (first plan of Phase 9)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user desktop tool; no auth surface |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | OS-level file perms only |
| V5 Input Validation | yes | All Python script inputs go through Pydantic v2 (FND-02); JSON envelopes from Python → Node use parameterized SQL inserts (`db.run(sql, ...args)`) — no string concatenation |
| V6 Cryptography | no | No secrets persisted; no encryption requirement (User Layer file is gitignored) |

### Known Threat Patterns for Node + DuckDB

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via crafted `--sql` flag | Tampering | `cmdQuery` (`career-ops db-write.mjs:659-664`) is read-only, but ad-hoc; documented as developer-only. Phase 10 skill never exposes `--sql` to user input. |
| SQL injection via JSON payload | Tampering | All INSERT/UPDATE use parameterized `?` placeholders; never string-interpolate user values into SQL. |
| Lockfile tampering | DoS | Stale recovery (60s) bounds the impact. Lockfile is in `data/` which is User Layer (read-only by system code, write-only by `db-write.mjs`). |
| Path traversal in `--json fixture.json` | Information Disclosure | `db-write.mjs` runs as the user; no privilege boundary to cross. Documented as developer-only CLI. |
| Symlink in `data/.mortgage-ops.duckdb.lock` redirecting `unlinkSync` | Tampering | Single-user desktop tool; OS file perms protect `data/`. |

## Sources

### Primary (HIGH confidence)
- **career-ops/scripts/db-write.mjs** (`/Users/cujo253/Documents/career-ops/scripts/db-write.mjs`) — canonical writer pattern (lines 19-746).
- **career-ops/scripts/lockfile.mjs** (`/Users/cujo253/Documents/career-ops/scripts/lockfile.mjs`) — canonical lockfile (lines 1-77).
- **career-ops/scripts/init-db.mjs** (`/Users/cujo253/Documents/career-ops/scripts/init-db.mjs`) — canonical idempotent init (lines 1-258).
- **career-ops/package.json** (`/Users/cujo253/Documents/career-ops/package.json`) — pinned versions duckdb-async@^1.4.2, js-yaml@^4.1.1.
- **mortgage-ops/lib/models.py** (`/Users/cujo253/Documents/mortgage-ops/lib/models.py`) — Money/Rate type aliases (lines 23-33); Loan/Payment/Schedule shapes.
- **mortgage-ops/lib/affordability.py** (`/Users/cujo253/Documents/mortgage-ops/lib/affordability.py`) — Applicant/MonthlyDebts/EscrowInputs/LocationFIPS shapes (lines 339-440).
- **mortgage-ops/DATA_CONTRACT.md** — Layer assignments; `data/mortgage-ops.duckdb` is User Layer + Data Layer.
- **mortgage-ops/CLAUDE.md** — Money discipline (Decimal, ROUND_HALF_UP, condecimal); calc-engine separation rule.
- **DuckDB official docs — Concurrency** (https://duckdb.org/docs/current/connect/concurrency) — single-writer; cross-process file lock.
- **DuckDB official docs — Numeric Types** (https://duckdb.org/docs/current/sql/data_types/numeric) — DECIMAL(prec,scale); INT64 storage for width ≤ 18.
- **npm registry** — `npm view duckdb-async version` → 1.4.2 (2025-11-13); `npm view js-yaml version` → 4.1.1 (2025-11-12).

### Secondary (MEDIUM confidence)
- **Web search 2026-05-02** — DECIMAL returned as bigint in duckdb-node (corroborated by GitHub issue #82, deepwiki.com/duckdb/duckdb-node-neo).
- **DuckDB GitHub Issue #17158** (https://github.com/duckdb/duckdb/issues/17158) — `IO Error: Could not set lock on file` for cross-process opens.
- **DuckDB GitHub Issue #1330** (https://github.com/duckdb/duckdb/issues/1330) — single-writer multiple-readers semantics.
- **node-proper-lockfile** (https://github.com/moxystudio/node-proper-lockfile) — alternative atomic lockfile via `mkdir`; rationale for rejecting `O_EXCL` on NFS.
- **LWN: O_EXCL|O_CREAT over NFS** (https://lwn.net/Articles/251004/) — race-condition documentation.

### Tertiary (LOW confidence)
- **The Dench Blog: DuckDB Data Types** (https://www.dench.com/blog/duckdb-data-types) — DECIMAL precision overview; corroborated by official docs.

## Project Constraints (from CLAUDE.md)

The following directives from `/Users/cujo253/Documents/mortgage-ops/CLAUDE.md` constrain Phase 9 implementation:

1. **Decimal money discipline (NON-NEGOTIABLE)** — All money values are `Decimal` constructed from strings; quantize with `ROUND_HALF_UP` end-of-period only. Phase 9's INSERT path passes Python-emitted strings through to DuckDB DECIMAL; SELECT path uses `CAST AS VARCHAR` to preserve precision back into Python.
2. **Calc engine separation** — Claude (and now: Node) never owns numbers. Phase 9 Node code only persists strings; never computes derived money values.
3. **Pydantic v2 `condecimal(max_digits=14, decimal_places=2)`** at all script boundaries (FND-02). Schema choice `DECIMAL(14,2)` matches.
4. **Data Contract layer enforcement** — `data/mortgage-ops.duckdb` is both User Layer (gitignored, contains user-private state) and Data Layer (regenerated). `orchestration/` is System Layer (committed). `data/known-loans.yml` is Reference Layer (committed; `source:` URL + `effective:` date).
5. **No Co-Authored-By or AI attribution in commits** (per global rule, also restated in CLAUDE.md). The CLAUDE.md at user-global level (`/Users/cujo253/CLAUDE.md`) reinforces this.
6. **GSD workflow** — All file edits enter through `/gsd-execute-phase`; no direct repo edits outside the workflow.
7. **Reference Layer staleness** — Phase 2 startup-time staleness check warns when YAML `effective:` > 12 months old. `known-loans.yml` should follow the same convention (`source:` + `effective:` keys).

## Metadata

**Confidence breakdown:**
- Standard stack (`duckdb-async@1.4.2` + `js-yaml@4.1.1`): HIGH — versions verified via `npm view` 2026-05-02; pattern verified verbatim against career-ops.
- Architecture (lockfile + transaction + render-markdown): HIGH — direct port from working career-ops code.
- DECIMAL bigint pitfall: HIGH — confirmed via web search and DuckDB official docs; verified bigint behavior is the duckdb-node default for width ≤ 18 INT64-backed DECIMAL.
- Lockfile race window: HIGH (correctly identified as INHERITED from career-ops); LOW on whether the v1 risk acceptance is correct for mortgage-ops production posture (we assume single-user desktop is sufficient).
- Schema DDL (table shapes): HIGH for loans/scenarios/payments (matches `lib.models`); MEDIUM for applicants/properties (best-fit interpretation of Phase 4 affordability shapes).
- Sample `known-loans.yml` rates: MEDIUM — anchored to 2026-04-24 PMMS; FHA/VA/jumbo/ARM rates are representative not live (Phase 12 will live-source).

**Research date:** 2026-05-02
**Valid until:** 2026-06-02 (30 days; stable domain — DuckDB and the career-ops pattern do not move quickly)
