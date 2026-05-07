---
phase: 09
plan: 02
type: execute
wave: 2
depends_on:
  - "09-00"
  - "09-01"
files_modified:
  - package.json
  - .gitignore
  - orchestration/init-db.mjs
must_haves:
  truths:
    - "package.json exists at repo root with type='module', engines.node>='18.0.0', dependencies duckdb-async@1.4.2 + js-yaml@4.1.1, and minimal scripts (init-db, db-write)"
    - "node_modules/ + data/.lock + data/loans.md + data/scenarios.md + data/mortgage-ops.duckdb-wal + data/mortgage-ops.duckdb-shm appended to .gitignore"
    - "orchestration/init-db.mjs creates 6 tables (loans, scenarios, reports, payments, applicants, properties) + schema_version table per RESEARCH §c DDL"
    - "init-db.mjs honors MORTGAGE_OPS_DB_PATH env var (test seam from Plan 09-00 D-00-04)"
    - "Running init-db.mjs twice produces identical schema with zero errors (idempotent via CREATE TABLE IF NOT EXISTS + CREATE SEQUENCE IF NOT EXISTS + ON CONFLICT DO NOTHING)"
    - "test_init_db_idempotent xfail in tests/test_orchestration/test_db_lifecycle.py flips to passing"
  artifacts:
    - path: "package.json"
      provides: "Node manifest pinning duckdb-async + js-yaml; scripts entry points"
      contains: "duckdb-async"
      min_lines: 15
    - path: "orchestration/init-db.mjs"
      provides: "Idempotent schema bootstrapper (PERS-01 + PERS-02 closure)"
      contains: "CREATE TABLE IF NOT EXISTS loans"
      min_lines: 100
    - path: ".gitignore"
      provides: "Updated to include node_modules/ + lockfile + generated markdown views + duckdb sidecars"
      contains: "node_modules/"
  key_links:
    - from: "tests/test_orchestration/test_db_lifecycle.py::test_init_db_idempotent"
      to: "orchestration/init-db.mjs"
      via: "subprocess invocation via node_orchestration_run helper"
      pattern: "node_orchestration_run.*init-db.mjs"
    - from: "orchestration/init-db.mjs DB_PATH constant"
      to: "process.env.MORTGAGE_OPS_DB_PATH"
      via: "env-var override per D-00-04"
      pattern: "process.env.MORTGAGE_OPS_DB_PATH"
autonomous: true
requirements:
  - PERS-01
  - PERS-02
tags:
  - phase-09
  - duckdb-orchestration
  - schema
  - idempotent-init
---

<objective>
**Goal:** Ship the Node manifest (`package.json`), update `.gitignore` for Phase 9 generated artifacts, and create the idempotent schema bootstrapper (`orchestration/init-db.mjs`) that creates all 6 mortgage-domain tables (loans, scenarios, reports, payments, applicants, properties) plus the schema_version table. Closes PERS-01 + PERS-02; flips the `test_init_db_idempotent` xfail to passing.

**Purpose:** Schema is the foundation for Wave 3 (insert subcommands) and Wave 4 (render-markdown SELECT). Idempotency is non-negotiable — running `node orchestration/init-db.mjs` twice on a fresh checkout MUST produce identical schema with zero errors. The DDL is pinned verbatim from RESEARCH §c (already-vetted with explicit schema decisions citing lib/models.py + lib/affordability.py).

**Output:** package.json (~25 lines, `type=module`, engines.node>=18, two deps); .gitignore (+5 lines for Phase 9 artifacts); orchestration/init-db.mjs (~150 lines including the verbatim DDL block from RESEARCH §c). One xfail flips: test_init_db_idempotent.
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
@DATA_CONTRACT.md
@.gitignore
@tests/conftest.py
@tests/test_orchestration/test_db_lifecycle.py

<interfaces>
**Pinned schema DDL** — copy VERBATIM from RESEARCH.md "Pinned Schema DDL" section (lines 281-385). The 9-block sequence is:

1. schema_version table (forward-only migration tracking)
2. loans table (PK auto-increment via sequence; matches lib/models.py:36-45 Loan)
3. scenarios table (cross-cutting analysis; loan_id nullable for affordability reverse mode)
4. reports table (markdown blobs from Phase 10 skill output)
5. payments table (one row per (loan_id, period); matches lib/models.py:48-61 Payment)
6. applicants table (matches lib/affordability.py:354-365 Applicant; FK loan_id)
7. properties table (matches lib/affordability.py:339-351 LocationFIPS + escrow inputs)
8. 7 named indexes via CREATE INDEX IF NOT EXISTS
9. INSERT INTO schema_version (version) VALUES (1) ON CONFLICT (version) DO NOTHING

**Note on column naming:** RESEARCH §c uses `loans.apr` for the contractual annual interest rate (Pydantic field name `Loan.annual_rate`). RESEARCH Open Question §1 recommends renaming to `annual_rate` for clarity. **This plan locks `annual_rate`** (D-02-04 below) — match the Pydantic field name 1:1 to eliminate cross-language confusion.

**Career-ops analog for the .mjs skeleton structure (imports, path resolution, top-level run() error envelope):** career-ops/scripts/init-db.mjs lines 1-15 + 212-258. We adopt a simpler approach than career-ops's `runSafe()`: use DuckDB native `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` + `ON CONFLICT DO NOTHING` per RESEARCH §Pattern 1 (DuckDB supports IF NOT EXISTS for tables/sequences/indexes; runSafe was a pre-IF-NOT-EXISTS workaround).

**MORTGAGE_OPS_DB_PATH env-var override** — per Plan 09-00 D-00-04, init-db.mjs MUST honor this env var so tests can target a tmp DB:

```javascript
const DB_PATH = process.env.MORTGAGE_OPS_DB_PATH ||
                join(MORTGAGE_OPS, 'data', 'mortgage-ops.duckdb');
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create root package.json pinning Node deps + scripts</name>
  <files>package.json</files>
  <read_first>
    - /Users/cujo253/Documents/career-ops/package.json (full, ~40 lines) — canonical reference
    - 09-PATTERNS.md "package.json (Node manifest at repo root)" + Critical Issue 4
    - 09-RESEARCH.md "Standard Stack" Installation block
  </read_first>
  <action>
    Create /Users/cujo253/Documents/mortgage-ops/package.json. Pin exact versions per RESEARCH §Standard Stack (verified via `npm view` 2026-05-02). Pin `engines.node` to >=18.0.0 since this is the FIRST Node code in the repo (per spawn-message constraint).

    File content:

    ```json
    {
      "name": "mortgage-ops",
      "version": "0.1.0",
      "private": true,
      "description": "Personal-use mortgage analysis: deterministic Python calc engine + Claude skill orchestration with DuckDB persistence (Phase 9)",
      "type": "module",
      "engines": {
        "node": ">=18.0.0"
      },
      "scripts": {
        "init-db": "node orchestration/init-db.mjs",
        "db-write": "node orchestration/db-write.mjs"
      },
      "dependencies": {
        "duckdb-async": "1.4.2",
        "js-yaml": "4.1.1"
      }
    }
    ```

    Notes on version pinning:
    - `duckdb-async` is pinned to EXACT `1.4.2` (no caret) per RESEARCH §Standard Stack [VERIFIED: 2025-11-13]; Phase 9 wants reproducible installs (mirroring `uv.lock` Python discipline).
    - `js-yaml` is pinned to EXACT `4.1.1` per RESEARCH §Standard Stack [VERIFIED: 2025-11-12].
    - `private: true` prevents accidental `npm publish` (this is a personal tool, not a published package).
    - `type: "module"` so `.mjs` files use ESM imports natively.
    - `engines.node >= 18.0.0` is the floor for native fetch + ESM stable + duckdb-async support.

    After writing the file, run `npm install` to generate node_modules/ and package-lock.json:

    ```bash
    cd /Users/cujo253/Documents/mortgage-ops && npm install
    ```

    This downloads duckdb-async (which pulls in the duckdb native binding ~30MB) + js-yaml. Verify the lockfile (`package-lock.json`) is created. Do NOT commit node_modules/ (the next task adds it to .gitignore).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && test -f package.json && test -f package-lock.json && test -d node_modules && node -e "import('duckdb-async').then(m => console.log('duckdb-async OK', !!m.Database))" && node -e "import('js-yaml').then(m => console.log('js-yaml OK', !!m.default.load))"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f package.json` exits 0
    - `test -f package-lock.json` exits 0
    - `test -d node_modules` exits 0
    - `grep -c '"type": "module"' package.json` returns 1
    - `grep -c '"node": ">=18.0.0"' package.json` returns 1
    - `grep -c '"duckdb-async": "1.4.2"' package.json` returns 1
    - `grep -c '"js-yaml": "4.1.1"' package.json` returns 1
    - `node -e "import('duckdb-async').then(m => process.exit(m.Database ? 0 : 1))"` exits 0
    - `node -e "import('js-yaml').then(m => process.exit(m.default.load ? 0 : 1))"` exits 0
  </acceptance_criteria>
  <done>
    package.json + package-lock.json + node_modules/ all exist; both deps importable.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update .gitignore with Phase 9 generated artifacts</name>
  <files>.gitignore</files>
  <read_first>
    - .gitignore (full, ~30 lines) — preserve all existing entries
    - DATA_CONTRACT.md lines 18-23 — Phase 9 artifact enumeration
    - 09-RESEARCH.md "Pitfall 5: Lockfile Path Not Gitignored"
  </read_first>
  <action>
    Append a Phase 9 block to .gitignore. Preserve all existing entries (Python, uv, User Layer, Data Layer, Reports, OS/editor sections).

    Append exactly this block at the end of the file (after the existing OS/editor section):

    ```

    # Phase 9: Node orchestration artifacts
    node_modules/
    package-lock.json.bak

    # Phase 9: DuckDB writer lockfile (ephemeral; per PATTERNS Critical Issue 1)
    data/.lock

    # Phase 9: Generated markdown views (regenerated from DuckDB; never hand-edited)
    data/loans.md
    data/scenarios.md
    ```

    Notes:
    - **DO NOT add `package-lock.json`** — it MUST be committed for reproducible installs (mirrors career-ops convention).
    - `data/mortgage-ops.duckdb-wal` and `data/mortgage-ops.duckdb-shm` are ALREADY covered by the existing `data/mortgage-ops.duckdb-wal` and `data/mortgage-ops.duckdb-shm` lines (verified pre-existing in current .gitignore).
    - `data/*.duckdb` already covers the main DB file.
    - `reports/*` already excluded.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && grep -c "node_modules/" .gitignore && grep -c "data/.lock" .gitignore && grep -c "data/loans.md" .gitignore && grep -c "data/scenarios.md" .gitignore</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^node_modules/" .gitignore` returns 1
    - `grep -c "^data/.lock" .gitignore` returns 1
    - `grep -c "^data/loans.md" .gitignore` returns 1
    - `grep -c "^data/scenarios.md" .gitignore` returns 1
    - `grep -c "^data/\*.duckdb" .gitignore` returns 1 (existing — preserved)
    - `grep -c "^package-lock.json$" .gitignore` returns 0 (lockfile MUST be committed)
    - `git check-ignore node_modules/foo 2>/dev/null && echo "ignored"` shows "ignored"
    - `git check-ignore data/.lock 2>/dev/null && echo "ignored"` shows "ignored"
  </acceptance_criteria>
  <done>
    .gitignore has 5 new entries; node_modules + data/.lock + generated markdown all ignored; package-lock.json NOT ignored.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create orchestration/init-db.mjs with verbatim RESEARCH §c DDL</name>
  <files>orchestration/init-db.mjs</files>
  <read_first>
    - /Users/cujo253/Documents/career-ops/scripts/init-db.mjs lines 1-15 + 212-258 — skeleton + run() error envelope
    - 09-RESEARCH.md "Pinned Schema DDL" section (lines 281-385) — copy verbatim with annual_rate rename per D-02-04
    - 09-PATTERNS.md "orchestration/init-db.mjs (schema bootstrapper)" — mortgage-domain context
    - 09-PATTERNS.md Critical Issue 3 — six-table normalized schema rationale
  </read_first>
  <action>
    Create `orchestration/init-db.mjs`. The file structure: imports + path resolution + DDL constants + main run() function + top-level error envelope.

    Apply two divergences from RESEARCH §c verbatim DDL:
    1. **Rename `apr` -> `annual_rate`** in the loans table (D-02-04 below).
    2. **Add `MORTGAGE_OPS_DB_PATH` env-var override** on DB_PATH (D-00-04 inheritance).

    File content:

    ```javascript
    // orchestration/init-db.mjs
    // Idempotent DuckDB schema bootstrapper for mortgage-ops Phase 9.
    // PERS-01 + PERS-02 + ROADMAP SC-1: running this script twice on a fresh
    // checkout produces the same schema with no errors.
    //
    // Tables created (per RESEARCH §c Pinned Schema DDL):
    //   schema_version, loans, scenarios, reports, payments, applicants, properties
    // Plus 7 named indexes; INSERT INTO schema_version (version) VALUES (1)
    // is ON CONFLICT DO NOTHING so re-run is a no-op.
    //
    // Plan 09-02 D-02-04: column `loans.annual_rate` (not `apr`) — matches
    //   lib/models.py:42 Loan.annual_rate exactly to eliminate cross-language
    //   naming confusion. Reg-Z estimated APR (Phase 7 product) lives in
    //   scenarios.response_json for kind='apr'.
    // Plan 09-00 D-00-04: MORTGAGE_OPS_DB_PATH env-var override for test seam.

    import { Database } from 'duckdb-async';
    import { join, dirname } from 'path';
    import { fileURLToPath } from 'url';
    import { existsSync, mkdirSync } from 'fs';

    const MORTGAGE_OPS = dirname(dirname(fileURLToPath(import.meta.url)));
    const DB_PATH = process.env.MORTGAGE_OPS_DB_PATH ||
                    join(MORTGAGE_OPS, 'data', 'mortgage-ops.duckdb');

    // Ensure parent directory exists (DB_PATH may be under tmp_path in tests).
    {
      const parentDir = dirname(DB_PATH);
      if (!existsSync(parentDir)) {
        mkdirSync(parentDir, { recursive: true });
      }
    }

    // ===== DDL — verbatim from 09-RESEARCH.md Pinned Schema DDL with one rename
    //       (apr -> annual_rate per D-02-04). =====

    const DDL_STATEMENTS = [
      // 1. Schema version (forward-only migrations)
      `CREATE TABLE IF NOT EXISTS schema_version (
         version    INTEGER PRIMARY KEY,
         applied_at TIMESTAMP NOT NULL DEFAULT now()
       )`,

      // 2. Loans (top-level scenario subject; mirrors lib.models.Loan)
      `CREATE SEQUENCE IF NOT EXISTS loans_id_seq START 1`,
      `CREATE TABLE IF NOT EXISTS loans (
         id                INTEGER       PRIMARY KEY DEFAULT nextval('loans_id_seq'),
         principal         DECIMAL(14,2) NOT NULL,
         annual_rate       DECIMAL(7,6)  NOT NULL CHECK (annual_rate >= 0 AND annual_rate <= 1),
         term_months       INTEGER       NOT NULL CHECK (term_months BETWEEN 1 AND 600),
         origination_date  DATE,
         loan_type         VARCHAR       NOT NULL CHECK (loan_type IN
                             ('fixed','arm','fha','va','usda','jumbo')),
         frequency         VARCHAR       NOT NULL DEFAULT 'monthly'
                             CHECK (frequency IN ('monthly','biweekly')),
         known_loan_id     VARCHAR,
         notes             VARCHAR,
         created_at        TIMESTAMP     NOT NULL DEFAULT now(),
         updated_at        TIMESTAMP     NOT NULL DEFAULT now()
       )`,

      // 3. Scenarios (cross-cutting analysis; loan_id nullable for affordability reverse mode)
      `CREATE SEQUENCE IF NOT EXISTS scenarios_id_seq START 1`,
      `CREATE TABLE IF NOT EXISTS scenarios (
         id            INTEGER       PRIMARY KEY DEFAULT nextval('scenarios_id_seq'),
         loan_id       INTEGER,
         kind          VARCHAR       NOT NULL CHECK (kind IN
                         ('amortize','affordability','arm','refi','apr','stress','points')),
         request_json  JSON          NOT NULL,
         response_json JSON          NOT NULL,
         computed_at   TIMESTAMP     NOT NULL DEFAULT now(),
         notes         VARCHAR
       )`,

      // 4. Reports (markdown blobs from Phase 10 skill output)
      `CREATE SEQUENCE IF NOT EXISTS reports_id_seq START 1`,
      `CREATE TABLE IF NOT EXISTS reports (
         id              INTEGER     PRIMARY KEY DEFAULT nextval('reports_id_seq'),
         scenario_id     INTEGER     NOT NULL,
         markdown_blob   TEXT        NOT NULL,
         generated_at    TIMESTAMP   NOT NULL DEFAULT now()
       )`,

      // 5. Payments (one row per (loan_id, period); mirrors lib.models.Payment)
      `CREATE TABLE IF NOT EXISTS payments (
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
       )`,

      // 6. Applicants (one row per applicant per loan; supports joint applications)
      `CREATE SEQUENCE IF NOT EXISTS applicants_id_seq START 1`,
      `CREATE TABLE IF NOT EXISTS applicants (
         id                     INTEGER       PRIMARY KEY DEFAULT nextval('applicants_id_seq'),
         loan_id                INTEGER       NOT NULL,
         credit_score           INTEGER       NOT NULL CHECK (credit_score BETWEEN 300 AND 850),
         gross_monthly_income   DECIMAL(14,2) NOT NULL,
         monthly_debts          DECIMAL(14,2) NOT NULL DEFAULT 0,
         applicant_label        VARCHAR
       )`,

      // 7. Properties (one row per loan; v1 single-property)
      `CREATE SEQUENCE IF NOT EXISTS properties_id_seq START 1`,
      `CREATE TABLE IF NOT EXISTS properties (
         id           INTEGER       PRIMARY KEY DEFAULT nextval('properties_id_seq'),
         loan_id      INTEGER       NOT NULL,
         value        DECIMAL(14,2) NOT NULL,
         state_fips   VARCHAR(2)    NOT NULL,
         county_fips  VARCHAR(3)    NOT NULL,
         property_tax_monthly DECIMAL(14,2) NOT NULL DEFAULT 0,
         insurance_monthly    DECIMAL(14,2) NOT NULL DEFAULT 0,
         hoa_monthly          DECIMAL(14,2) NOT NULL DEFAULT 0
       )`,

      // 8. Indexes (named so subsequent runs are no-ops via IF NOT EXISTS)
      `CREATE INDEX IF NOT EXISTS idx_loans_loan_type     ON loans(loan_type)`,
      `CREATE INDEX IF NOT EXISTS idx_scenarios_loan      ON scenarios(loan_id)`,
      `CREATE INDEX IF NOT EXISTS idx_scenarios_kind      ON scenarios(kind)`,
      `CREATE INDEX IF NOT EXISTS idx_reports_scenario    ON reports(scenario_id)`,
      `CREATE INDEX IF NOT EXISTS idx_payments_loan       ON payments(loan_id)`,
      `CREATE INDEX IF NOT EXISTS idx_applicants_loan     ON applicants(loan_id)`,
      `CREATE INDEX IF NOT EXISTS idx_properties_loan     ON properties(loan_id)`,

      // 9. Stamp schema version (ON CONFLICT DO NOTHING for idempotency)
      `INSERT INTO schema_version (version) VALUES (1) ON CONFLICT (version) DO NOTHING`,
    ];

    async function run() {
      console.log(`init-db: opening ${DB_PATH}`);
      const db = await Database.create(DB_PATH);
      try {
        for (const stmt of DDL_STATEMENTS) {
          // Truncate stmt to first 60 chars for log clarity
          const label = stmt.replace(/\s+/g, ' ').slice(0, 60);
          await db.run(stmt);
          console.log(`  ok  ${label}${stmt.length > 60 ? '...' : ''}`);
        }
        console.log('init-db: schema ready');
      } finally {
        await db.close();
      }
    }

    run().catch(err => {
      console.error('Fatal:', err?.message || err);
      process.exit(1);
    });
    ```

    After writing, run a manual smoke test to verify idempotency:

    ```bash
    rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal data/mortgage-ops.duckdb-shm
    node orchestration/init-db.mjs && node orchestration/init-db.mjs && echo "idempotent OK"
    ```

    Both runs MUST exit 0. The second run produces zero "already exists" errors because every `CREATE` uses `IF NOT EXISTS` and the INSERT uses `ON CONFLICT DO NOTHING`.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && node --check orchestration/init-db.mjs && rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal data/mortgage-ops.duckdb-shm && node orchestration/init-db.mjs && node orchestration/init-db.mjs && echo "idempotent OK"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f orchestration/init-db.mjs` exits 0
    - `node --check orchestration/init-db.mjs` exits 0
    - `grep -c "CREATE TABLE IF NOT EXISTS schema_version" orchestration/init-db.mjs` returns 1
    - `grep -c "CREATE TABLE IF NOT EXISTS loans" orchestration/init-db.mjs` returns 1
    - `grep -c "CREATE TABLE IF NOT EXISTS scenarios" orchestration/init-db.mjs` returns 1
    - `grep -c "CREATE TABLE IF NOT EXISTS reports" orchestration/init-db.mjs` returns 1
    - `grep -c "CREATE TABLE IF NOT EXISTS payments" orchestration/init-db.mjs` returns 1
    - `grep -c "CREATE TABLE IF NOT EXISTS applicants" orchestration/init-db.mjs` returns 1
    - `grep -c "CREATE TABLE IF NOT EXISTS properties" orchestration/init-db.mjs` returns 1
    - `grep -c "annual_rate" orchestration/init-db.mjs` returns at least 1 (D-02-04 rename)
    - `grep -c "process.env.MORTGAGE_OPS_DB_PATH" orchestration/init-db.mjs` returns 1 (D-00-04 env seam)
    - `grep -c "ON CONFLICT (version) DO NOTHING" orchestration/init-db.mjs` returns 1
    - First `node orchestration/init-db.mjs` exits 0
    - Second `node orchestration/init-db.mjs` exits 0 (idempotent)
  </acceptance_criteria>
  <done>
    init-db.mjs creates 6 tables + schema_version; running twice produces zero errors; all DDL constraints in place.
  </done>
</task>

<task type="auto">
  <name>Task 4: Flip test_init_db_idempotent xfail in test_db_lifecycle.py</name>
  <files>tests/test_orchestration/test_db_lifecycle.py</files>
  <read_first>
    - tests/test_orchestration/test_db_lifecycle.py (current Wave 0 stub state)
    - tests/conftest.py — node_orchestration_run helper signature
  </read_first>
  <action>
    Replace the test_init_db_idempotent stub with a real assertion. REMOVE the @pytest.mark.xfail decorator AND replace the body. Keep all 3 OTHER stubs (insert_loan_round_trip, decimal_string_round_trip, concurrent_writes_serialize) untouched.

    New body for test_init_db_idempotent:

    ```python
    def test_init_db_idempotent(tmp_path: Path) -> None:
        """PERS-01 + PERS-02 + ROADMAP SC-1: running init-db.mjs twice on a fresh
        checkout produces the same schema with no errors. Verified by:
        1. node orchestration/init-db.mjs against tmp DB -> exit 0
        2. node orchestration/init-db.mjs again -> exit 0 (idempotent; no errors)
        3. Schema introspection: all 6 tables (loans, scenarios, reports,
           payments, applicants, properties) plus schema_version present.
        """
        from tests.conftest import node_orchestration_run

        db_path = tmp_path / "test.duckdb"

        # First run: creates schema
        result_a = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert result_a.returncode == 0, f"first run failed: stderr={result_a.stderr}"
        assert db_path.exists(), f"DB file not created at {db_path}"

        # Second run: idempotent
        result_b = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert result_b.returncode == 0, f"second run failed (idempotency violation): stderr={result_b.stderr}"

        # Schema introspection: list all tables; assert 7 expected names present
        # (6 mortgage tables + schema_version)
        introspect_script = """
        import { Database } from 'duckdb-async';
        const db = await Database.create(process.env.MORTGAGE_OPS_DB_PATH);
        try {
          const rows = await db.all(
            "SELECT table_name FROM information_schema.tables " +
            "WHERE table_schema='main' ORDER BY table_name"
          );
          console.log(JSON.stringify(rows.map(r => r.table_name)));
        } finally {
          await db.close();
        }
        """
        import os
        import subprocess
        env = os.environ.copy()
        env["MORTGAGE_OPS_DB_PATH"] = str(db_path)
        introspect = subprocess.run(
            ["node", "--input-type=module", "-e", introspect_script],
            cwd=str(Path(__file__).resolve().parent.parent.parent),
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert introspect.returncode == 0, f"introspect failed: stderr={introspect.stderr}"
        import json as _json
        tables = set(_json.loads(introspect.stdout.strip()))
        expected = {"schema_version", "loans", "scenarios", "reports",
                    "payments", "applicants", "properties"}
        assert expected.issubset(tables), f"missing tables: {expected - tables}; got {tables}"
    ```

    Remove the `@pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-02 ships orchestration/init-db.mjs")` decorator above this test.

    Other tests in this file remain xfail until their respective waves land.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_db_lifecycle.py::test_init_db_idempotent -v --tb=short 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_orchestration/test_db_lifecycle.py::test_init_db_idempotent -v 2>&1 | grep -c PASSED` returns 1
    - `pytest tests/test_orchestration/test_db_lifecycle.py -v --tb=no 2>&1 | grep -c XFAIL` returns 3 (was 4; one flipped)
    - `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_db_lifecycle.py` returns 3 (was 4)
    - `grep -c "def test_init_db_idempotent" tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -B 1 "def test_init_db_idempotent" tests/test_orchestration/test_db_lifecycle.py | grep -c xfail` returns 0 (decorator removed)
  </acceptance_criteria>
  <done>
    test_init_db_idempotent passes; 3 other test_db_lifecycle.py stubs remain xfail; PERS-01 + PERS-02 closed.
  </done>
</task>

<task type="auto">
  <name>Task 5: Verify zero regression + lint</name>
  <files>(verification only)</files>
  <action>
    1. Full pytest suite: at least 432 + 7 (Wave 1 lockfile unit) + 1 (Wave 2 init-db idempotent flip) = 440 passed.
    2. xfailed count: 1 (Phase 5 strict xfail) + 6 remaining Wave 0 stubs = 7 (was 8 after Wave 0; one flipped).
    3. mypy --strict tests/test_orchestration/.
    4. ruff check + format on tests/test_orchestration/.
    5. Sanity: package.json + .gitignore + orchestration/init-db.mjs + lockfile.mjs all present.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest -q 2>&1 | tail -3 && mypy --strict tests/test_orchestration/ && ruff check tests/test_orchestration/ && ruff format --check tests/test_orchestration/ && test -f package.json && test -f orchestration/init-db.mjs && test -f orchestration/lockfile.mjs && echo "all artifacts present"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows >= 440
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ xfailed'` shows 7
    - `pytest -q 2>&1 | tail -3 | grep -E '[0-9]+ failed' | wc -l` returns 0 OR shows "0 failed"
    - mypy + ruff + ruff format all exit 0
  </acceptance_criteria>
  <done>
    Full suite green; PERS-01 + PERS-02 closed; one xfail flipped.
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS:**

- **D-02-01: package.json lives at repo root** — rationale: PATTERNS Critical Issue 4 (5 reasons including career-ops convention, npm run from repo root, single node_modules, parallel to pyproject.toml). Rule-of-three citation: career-ops/package.json at root; mortgage-ops/pyproject.toml at root; user spawn-message constraint #2 ("This is the FIRST Node code in the repo — pin Node version requirement (>=18 for native fetch + ESM); document in package.json `engines` field").

- **D-02-02: Pin EXACT versions duckdb-async@1.4.2 + js-yaml@4.1.1 (no caret)** — rationale: reproducible installs mirror the uv.lock Python discipline; the spawn message recommends these exact versions per RESEARCH §Standard Stack (verified via `npm view` 2026-05-02). Rule-of-three citation: pyproject.toml uses exact `numpy-financial==1.0.0`; spawn-message Important constraint pins these versions; RESEARCH §Standard Stack [VERIFIED] entries.

- **D-02-03: engines.node >= 18.0.0** — rationale: spawn-message constraint requires Node >=18 for native fetch + stable ESM + duckdb-async support. Rule-of-three citation: spawn-message constraint #2; Node 18 LTS expired April 2025 but Node 20/22 LTS satisfy >=18 floor; duckdb-async 1.4.x requires Node >=14 (we set tighter floor for fetch).

- **D-02-04: loans.annual_rate (NOT loans.apr)** — rationale: matches lib/models.py:42 Loan.annual_rate field name 1:1. Reg-Z estimated APR (Phase 7 product) lives in scenarios.response_json for kind='apr'; mixing the two terms in column names creates persistent cross-language confusion. Resolves RESEARCH Open Question §1 in favor of clarity. Rule-of-three citation: lib/models.py:42 uses `annual_rate`; scripts/amortize.py request envelope uses `annual_rate`; tests/test_amortize.py + tests/test_affordability.py use `annual_rate`.

- **D-02-05: Use DuckDB native CREATE TABLE/SEQUENCE/INDEX IF NOT EXISTS, NOT career-ops runSafe()** — rationale: per RESEARCH §Pattern 1, modern DuckDB supports IF NOT EXISTS on tables/sequences/indexes; career-ops's runSafe() exception-swallow pattern was a workaround for older DuckDB. Cleaner code; fewer try/catch swallows. Rule-of-three citation: RESEARCH §Pattern 1 explicit recommendation; PATTERNS Pattern Assignments init-db section line 156 ("mortgage-ops adopts the cleaner IF NOT EXISTS form"); spawn-message constraint says "init-db.mjs (idempotent CREATE TABLE IF NOT EXISTS + schema_version table per RESEARCH §c DDL)".

- **D-02-06: Six-table normalized schema, not single-blob** — rationale: PATTERNS Critical Issue 3 + ROADMAP SC-1 verbatim list. Cross-scenario SQL queries require joinable foreign-key relationships; result_json TEXT in scenarios is the escape hatch for shape-evolving response payloads. Rule-of-three citation: ROADMAP.md:180 explicit table list; PATTERNS Critical Issue 3 detailed schema sketch; RESEARCH §c verbatim DDL.

- **D-02-07: No FOREIGN KEY constraints in DDL** — rationale: per RESEARCH §c notes, DuckDB does not enforce FKs at write time; they're parsed but not validated. Application-level invariants in db-write.mjs handle integrity. Career-ops has no FKs either. Rule-of-three citation: RESEARCH §c "No FOREIGN KEY constraints" note; career-ops/scripts/init-db.mjs:36-150 has no FKs; PATTERNS Critical Issue 3 schema sketch omits FKs.
</locked_decisions>

<verify_block>
**Verify Block:**

```bash
# 1. Manifest + deps
test -f package.json && test -f package-lock.json && test -d node_modules
node -e "import('duckdb-async').then(m => process.exit(m.Database ? 0 : 1))"
node -e "import('js-yaml').then(m => process.exit(m.default.load ? 0 : 1))"

# 2. .gitignore additions
for entry in "node_modules/" "data/.lock" "data/loans.md" "data/scenarios.md"; do
  grep -qE "^$entry" .gitignore && echo "$entry: ignored"
done
grep -c "^package-lock.json$" .gitignore  # MUST return 0

# 3. init-db.mjs syntax + idempotency
node --check orchestration/init-db.mjs
rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal data/mortgage-ops.duckdb-shm
node orchestration/init-db.mjs && node orchestration/init-db.mjs && echo "idempotent OK"

# 4. All 6 tables + schema_version present
node --input-type=module -e "import {Database} from 'duckdb-async'; const db = await Database.create('data/mortgage-ops.duckdb'); const rows = await db.all(\"SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name\"); console.log(rows.map(r => r.table_name).join(',')); await db.close();"
# Expected output (sorted): applicants,loans,payments,properties,reports,scenarios,schema_version

# 5. annual_rate (not apr) in DDL
grep -c "annual_rate" orchestration/init-db.mjs  # >=1
grep -c "loans.apr" orchestration/init-db.mjs    # 0 (rename complete)

# 6. PERS-01 + PERS-02 test passes
pytest tests/test_orchestration/test_db_lifecycle.py::test_init_db_idempotent -v --tb=short

# 7. Full suite green; xfail count drops by 1
pytest -q 2>&1 | tail -3

# 8. Lint hygiene
mypy --strict tests/test_orchestration/
ruff check tests/test_orchestration/
ruff format --check tests/test_orchestration/
```
</verify_block>

<deviation_rules>
**Deviation Rules:**

- **Rule-1 (apr vs annual_rate):** D-02-04 locks `annual_rate`. If the executor finds RESEARCH §c verbatim text using `apr`, apply the rename — this is a documented LOCKED DECISION resolving RESEARCH Open Question §1, NOT a verbatim-only port.

- **Rule-2 (no schema additions):** Six tables + schema_version, period. If the executor thinks an additional table would be useful (e.g., `audit_log`), STOP. Schema additions are CONTEXT-level decisions; this plan ships exactly what RESEARCH §c + ROADMAP SC-1 enumerate.

- **Rule-3 (npm install duration):** `npm install` may take 30-90s due to duckdb native binding download. If install times out at 120s default, the executor may extend the timeout to 180s. If install fails with native-build errors, surface as a blocker (likely Node version mismatch) — do NOT downgrade duckdb-async version unilaterally.
</deviation_rules>

<dependencies>
**Dependencies:**

- **Depends on:** Plan 09-00 (test infrastructure: test_db_lifecycle.py with the test_init_db_idempotent stub awaiting flip; conftest.py with node_orchestration_run helper); Plan 09-01 (orchestration/ directory exists). Note: init-db.mjs does NOT import lockfile.mjs (init is one-shot, no concurrency); but the directory must exist.
- **Blocks:** Plan 09-03 (db-write.mjs imports duckdb-async installed here; depends on schema existing for INSERT statements). Plan 09-04 (render-markdown SELECTs from this schema). Plan 09-06 (parallel-write tests need DB to exist).
- **No version updates required:** uv.lock (Python deps) unchanged. pyproject.toml unchanged.
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User CLI -> init-db.mjs | Trusted (developer-only); MORTGAGE_OPS_DB_PATH env var controls target |
| init-db.mjs -> DuckDB native binding | OS file lock; init-db is single-process (no withLock needed) |
| package.json + lockfile -> npm registry | Trust npm; pin exact versions for reproducibility |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-09 | Tampering (schema drift between runs) | DDL_STATEMENTS array | mitigate | All CREATE statements use IF NOT EXISTS; schema_version INSERT uses ON CONFLICT DO NOTHING; second run is byte-identical no-op |
| T-09-10 | Information Disclosure (leak DB path via error message) | run() catch block | accept | Error message includes DB_PATH which may include tmp_path; tmp_path is per-test ephemeral; not a real PII leak |
| T-09-11 | Tampering (npm dependency confusion) | package.json | mitigate | Exact version pins (no caret); package-lock.json committed; integrity hashes verified by npm |
| T-09-12 | Denial of Service (init takes long on huge DB) | DDL execution loop | accept | DDL is idempotent; subsequent runs are <100ms; first run is <500ms on empty DB |
</threat_model>

<verification>
- package.json + package-lock.json + node_modules/ exist; both deps importable
- .gitignore has 5 new entries; node_modules + data/.lock + generated markdown ignored
- orchestration/init-db.mjs creates 6 tables + schema_version; DDL uses annual_rate (not apr)
- node orchestration/init-db.mjs is idempotent (run twice, both exit 0, byte-identical schema)
- test_init_db_idempotent xfail flipped to passing; PERS-01 + PERS-02 closed
- Full pytest suite >= 440 passed; xfail count drops to 7
- mypy + ruff clean
</verification>

<success_criteria>
- PERS-01 closed (schema has 6 tables + schema_version per ROADMAP SC-1)
- PERS-02 closed (init-db.mjs is idempotent)
- node_modules + data/.lock + generated markdown gitignored
- Wave 3 (db-write.mjs) can import duckdb-async + lockfile.mjs and INSERT into the schema created here
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-02-SUMMARY.md` documenting:
- package.json contents (deps + scripts + engines)
- .gitignore additions (5 new entries)
- orchestration/init-db.mjs DDL block summary (6 tables + indexes + schema_version)
- Idempotency demo command-line proof
- Pass count delta (Wave 1 baseline 439 -> Wave 2 baseline 440; one xfail flipped)
- PERS-01 + PERS-02 closure status
- Open question deferred to Wave 3: column naming (annual_rate vs apr) — locked here as annual_rate
</output>
</content>
</invoke>