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
