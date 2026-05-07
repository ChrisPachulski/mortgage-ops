# Data Layer — mortgage-ops Phase 9 Reference

This document is the onboarding + reference doc for the Phase 9
DuckDB orchestration surface. It describes the schema, the lockfile
mechanics, the render-markdown determinism contract, and the layer
classification of every Phase 9 artifact. It pairs with
`DATA_CONTRACT.md` (which is authoritative for layer rules) and
points back to the source-of-truth orchestration code in
`orchestration/`.

Source artifacts:

- `orchestration/init-db.mjs` — idempotent schema bootstrapper.
- `orchestration/db-write.mjs` — central writer CLI (insert-loan,
  insert-scenario, insert-report, render-markdown, query).
- `orchestration/lockfile.mjs` — cross-process mutex primitive.
- `data/known-loans.yml` — Reference Layer product catalog (committed).
- `data/mortgage-ops.duckdb` — Data + User Layer single-file persistence (gitignored).
- `data/loans.md` + `data/scenarios.md` — Data Layer rendered views (gitignored).
- `data/.mortgage-ops.duckdb.lock` + `data/.lock` — ephemeral writer lockfiles (gitignored).

---

## Schema Overview

The DuckDB file `data/mortgage-ops.duckdb` contains 7 tables defined by
`orchestration/init-db.mjs` (lines ~37-134, the `DDL_STATEMENTS` array).
Every CREATE uses `IF NOT EXISTS`, every sequence uses `IF NOT EXISTS`,
and the schema_version row is `ON CONFLICT DO NOTHING` — re-running
init-db on an existing DB is a no-op.

| Table             | Rows / scope                                | Key columns / DECIMAL widths                                                |
|-------------------|---------------------------------------------|------------------------------------------------------------------------------|
| `schema_version`  | one row per schema generation (v1)          | `version INTEGER PK`, `applied_at TIMESTAMP`                                |
| `loans`           | one row per modeled loan                    | `principal DECIMAL(14,2)`, `annual_rate DECIMAL(7,6)`, `term_months INTEGER` |
| `scenarios`       | one row per analysis (amortize, arm, refi…) | `kind VARCHAR CHECK`, `request_json JSON`, `response_json JSON`             |
| `reports`         | one row per markdown report blob            | `markdown_blob TEXT`, `generated_at TIMESTAMP`                              |
| `payments`        | one row per (loan_id, period)               | All money fields `DECIMAL(14,2)`; PK `(loan_id, period)`                    |
| `applicants`      | one row per applicant per loan              | `credit_score INTEGER CHECK 300-850`, income/debts `DECIMAL(14,2)`          |
| `properties`      | one row per loan (v1 single-property)       | `value DECIMAL(14,2)`, FIPS codes, escrow components `DECIMAL(14,2)`        |

Width conventions (matched 1:1 to Pydantic `condecimal` constraints in
`lib/models.py`):

- Money: `DECIMAL(14,2)` — covers up to $999,999,999,999.99 with cent precision.
- Rates: `DECIMAL(7,6)` — six decimal places for basis-point precision (1bp = 0.0001).
- Indexes: 7 named indexes (idx_loans_loan_type, idx_scenarios_loan,
  idx_scenarios_kind, idx_reports_scenario, idx_payments_loan,
  idx_applicants_loan, idx_properties_loan) all use `IF NOT EXISTS`.

**Source of truth:** `orchestration/init-db.mjs` `DDL_STATEMENTS` array.
RESEARCH §"Pinned schema DDL" derived this layout from career-ops
precedent + the ROADMAP SC-1 enumeration.

---

## Decimal-String Discipline

DuckDB DECIMAL columns return as JavaScript `BigInt` from
`duckdb-async` SELECTs — silently. A naive `Number(row.principal)`
truncates large values and drops trailing zeros (`200000.00` becomes
`200000`). The discipline that closes this trap (RESEARCH Pitfall 1):

1. **INSERT as string.** Every DECIMAL bind uses a JSON string
   (e.g., `"200000.01"`, `"0.065000"`). `db-write.mjs` cmdInsertLoan
   rejects floats at the boundary (`typeof === 'string'` guard). See
   Plan 09-03 D-03-03.

2. **SELECT via `CAST AS VARCHAR`.** Every read of a DECIMAL column
   wraps it: `CAST(principal AS VARCHAR)`. This forces DuckDB to
   serialize losslessly to text. See Plan 09-03 D-03-02.

3. **Re-parse to Decimal in Python.** Consumers do
   `Decimal(row["principal"])` — never `Decimal(float(...))`.

The regression test
`tests/test_orchestration/test_db_lifecycle.py::test_decimal_string_round_trip_preserves_cents`
exercises four boundary values (`200000.01`, `0.01`, `99999999.99`,
`1234567.89`) to pin the contract at every cent of precision.

---

## Lockfile Mechanics

DuckDB takes an OS-level file lock for the duration of an open
connection — a second writer process gets an `IO Error: Could not
set lock on file` if it tries to open the same DB concurrently. To
serialize writers without crashing, every WRITE subcommand wraps its
DB open + work + close in `withLock()` from
`orchestration/lockfile.mjs`.

**Lock file location:** `data/.lock` (the production lockfile name
shipped by Plan 09-01; D-01-03). The defensive secondary path
`data/.mortgage-ops.duckdb.lock` is also gitignored to catch any
future rename. See Plan 09-07 D-07-03.

**JSON shape:**

```json
{
  "pid": 12345,
  "acquired_at": 1715098247123,
  "reason": "insert-loan"
}
```

`acquired_at` is `Date.now()` in milliseconds at write time
(LOAD-BEARING per D-01-02 — `isStale` reads this field, NOT mtime,
so the check is immune to filesystem `touch` and clock-skew).

**Acquire protocol (`acquireLock`, lockfile.mjs:51-74):**

1. Read existing lock (if any).
2. If no existing lock OR existing lock is stale (acquired_at older
   than `STALE_THRESHOLD_MS = 60_000`), proceed.
3. `writeFileSync(LOCK_PATH, JSON.stringify(myLock), { flag: 'w' })`
   — flag `'w'` (NOT `'wx'`/O_EXCL — see D-01-01); we deliberately
   overwrite stale locks, and O_EXCL would crash on every acquire
   while a stale lock sits on disk.
4. Read the file back; verify `readBack.pid === my pid` AND
   `readBack.acquired_at === my acquired_at`. This is the
   poor-man's compare-and-swap that closes the race window
   (RESEARCH Pitfall 2). If verification fails, sleep 100ms and
   retry until `timeoutMs` (default 30s).

**Release protocol (`releaseLock`, lockfile.mjs:76-86):**

- Read existing lock; only `unlinkSync` if `pid` AND `acquired_at`
  both still match this process. This prevents process A from
  deleting process B's lock when A's grace period crossed B's
  acquire.
- `withLock(fn, opts)` wraps `acquireLock` + `fn()` + `releaseLock`
  in a try/finally so the lock is released even on throw.

**Stale recovery (60s threshold):** `STALE_THRESHOLD_MS = 60_000`
is non-negotiable per ROADMAP SC-3 + PERS-04. The
`isStale` function (lockfile.mjs:45-49) returns `true` if the
existing lock's `acquired_at` is more than 60s old (or null/
malformed) — at which point `acquireLock` overwrites it.

**Why not O_EXCL?** RESEARCH §Pitfall 2 + Plan 09-01 D-01-01: O_EXCL
on POSIX is documented broken on NFS; even on local filesystems it
would EEXIST-crash on every retry-loop iteration while a stale lock
sat on disk. The read-back-and-verify pattern works on every
filesystem and survives stale locks.

**Regression tests:**

- `tests/test_orchestration/test_lockfile_unit.py` — 7 unit tests
  exercising acquire/release/stale/race/timeout (lockfile.mjs in
  isolation).
- `tests/test_orchestration/test_parallel_invocation.py` — N
  concurrent `db-write.mjs insert-loan` Popen processes
  (Plan 09-06 SC-2 PERS-05).
- `tests/test_orchestration/test_stale_lockfile_recovery.py` —
  positive (65s-aged lock reclaimed) + negative (5s-aged lock NOT
  reclaimed) end-to-end (Plan 09-06 SC-3 PERS-04).

---

## Render-Markdown Determinism

`orchestration/db-write.mjs::cmdRenderMarkdown` (lines 216-283)
produces `data/loans.md` and `data/scenarios.md` byte-identically
across runs. Three rules close this contract (RESEARCH Pitfall 3 +
Plan 09-04 D-04-01..04):

1. **Mandatory verbatim header at line 1.** Every rendered file
   starts with the exact comment:

   ```
   <!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->
   ```

   This text is the user-facing signal that the file is generated and
   is also what regression tests grep on. See Plan 09-04 D-04-01.

2. **Explicit `ORDER BY id ASC` on every render SELECT.** Without
   it, DuckDB row order is unspecified and SHA-equality across runs
   breaks. Both the loans render SELECT (db-write.mjs:238) and the
   scenarios render SELECT (db-write.mjs:265) include the clause.
   See Plan 09-04 D-04-03.

3. **No `NOW()` / `generated_at` / render-time timestamps in the
   body.** The header is fixed text; row timestamps come from
   `scenarios.computed_at` (data captured at insert time, not
   re-evaluated at render time) via `strftime('%Y-%m-%d %H:%M:%S')`.
   See Plan 09-04 D-04-04.

DECIMAL columns in render SELECTs use `CAST AS VARCHAR` (D-04-02);
this is what preserves user-facing strings like `200000.00` and
`0.065000` exactly through to the markdown body.

**Regression tests:**

- `tests/test_orchestration/test_render_markdown.py` — Wave 4
  unit-style byte-equality across two consecutive renders.
- `tests/test_orchestration/test_render_markdown_byte_identical.py`
  — Wave 6 end-to-end SHA256 byte-equality across the full pipeline
  (init -> insert -> render -> hash) per ROADMAP SC-4.

---

## Reference Layer vs Data Layer (Phase 9 Disambiguation)

Phase 9 ships artifacts spanning three layers. The classification
table below is the same table appended to `DATA_CONTRACT.md` under
"Phase 9 Layer Examples":

| Artifact                            | Layer(s)                | Committed? | Why                                                               |
|-------------------------------------|-------------------------|------------|-------------------------------------------------------------------|
| `data/known-loans.yml`              | Reference               | YES        | Product catalog; manually refreshed; carries `source:` + `effective:` |
| `data/mortgage-ops.duckdb`          | Data + User (dual)      | NO         | Generated; user-private scenarios; regenerable from System + User + Reference |
| `data/mortgage-ops.duckdb-wal`      | Data                    | NO         | DuckDB write-ahead log sidecar                                    |
| `data/mortgage-ops.duckdb-shm`      | Data                    | NO         | DuckDB shared-memory sidecar                                      |
| `data/.lock` + `data/.mortgage-ops.duckdb.lock` | Data (ephemeral) | NO    | Writer coordination via lockfile.mjs; appears only while a writer runs |
| `data/loans.md`                     | Data                    | NO         | Generated view of `loans` table; byte-identical contract          |
| `data/scenarios.md`                 | Data                    | NO         | Generated view of `scenarios` table; byte-identical contract      |
| `orchestration/init-db.mjs`         | System                  | YES        | Schema bootstrapper                                               |
| `orchestration/db-write.mjs`        | System                  | YES        | Central writer CLI                                                |
| `orchestration/lockfile.mjs`        | System                  | YES        | Cross-process mutex primitive                                     |

**The trap:** a bare `data/*` line in `.gitignore` would silently
un-track `data/known-loans.yml` (which is Reference Layer per
DATA_CONTRACT.md line 67 + Plan 09-05 D-05-01), breaking Phase 10
+ Phase 12 routing with no warning. The `.gitignore` therefore uses
explicit per-file entries
(`data/.mortgage-ops.duckdb.lock`, `data/.lock`,
`data/loans.md`, `data/scenarios.md`) plus the
already-existing `data/*.duckdb` wildcard scoped to the DB suffix
only. The regression test
`tests/test_orchestration/test_gitignore_phase09.py` asserts both
the entries are present AND that `data/known-loans.yml` remains
NOT-ignored. See Plan 09-07 D-07-02 + D-07-05.

---

## Onboarding Walkthrough

A fresh-clone path from zero to a rendered markdown view:

```bash
# 1. Install Python + Node dependencies
uv sync                           # Python (lib/ + tests/)
npm install                       # Node (orchestration/)

# 2. Bootstrap the schema (idempotent — safe to run repeatedly)
node orchestration/init-db.mjs
# init-db: schema ready

# 3. Write a loan fixture
cat > /tmp/loan.json <<'JSON'
{
  "principal": "200000.00",
  "annual_rate": "0.065000",
  "term_months": 360,
  "origination_date": "2026-05-01",
  "loan_type": "fixed"
}
JSON

# 4. Insert via the lock-protected writer
node orchestration/db-write.mjs insert-loan --json /tmp/loan.json
# {"ok":true,"loan_id":1}

# 5. Render the markdown view
node orchestration/db-write.mjs render-markdown
# {"ok":true,"target":"all","loans_md":{...},"scenarios_md":{...}}

# 6. Verify the rendered file
head -2 data/loans.md
# <!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->
# # Loans

# 7. Read DECIMAL strings back via query (optional)
node orchestration/db-write.mjs query \
  --sql "SELECT id, CAST(principal AS VARCHAR) AS principal FROM loans"
# [{"id":1,"principal":"200000.00"}]

# 8. Inspect the Reference Layer catalog (read-only Python)
uv run python -c "
import yaml
d = yaml.safe_load(open('data/known-loans.yml'))
print(len(d['products']), 'products;', d['products'][0]['id'])
"
# 7 products; conv-30yr-fixed
```

The DB file (`data/mortgage-ops.duckdb`), markdown views (`data/loans.md`,
`data/scenarios.md`), and lockfile (`data/.lock`) are all gitignored —
your working tree shows them after step 5 but `git status` stays clean.

---

## When Things Go Wrong

| Symptom                                                             | Likely cause                                                       | Fix                                                                                |
|---------------------------------------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| `IO Error: Could not set lock on file ... data/mortgage-ops.duckdb` | Another writer holds the OS lock (a node process is mid-insert)     | Wait — `withLock` will retry up to 30s. If permanent, kill orphaned `node` PIDs.   |
| `Cannot serialize bigint to JSON` from query                        | A DECIMAL column was SELECTed without `CAST AS VARCHAR`             | Wrap every DECIMAL column: `SELECT CAST(principal AS VARCHAR) AS principal ...`    |
| `data/loans.md` differs across runs (SHA drift)                     | Missing `ORDER BY id ASC` OR a render-time `NOW()` slipped into body | Add the explicit ORDER BY (D-04-03); remove any timestamp not stored at insert time |
| `git status` shows `data/.lock` as untracked                        | The lockfile is missing from `.gitignore`                           | Add `data/.lock` (and ideally `data/.mortgage-ops.duckdb.lock`) explicitly         |
| `data/known-loans.yml` not visible to Phase 10/12 routing           | An over-broad `data/*` was added to `.gitignore`                    | Replace with explicit per-file lines; the regression test `test_gitignore_phase09` catches this |
| Lockfile sits at 60s+ age and writer never recovers                  | `acquired_at` is missing or non-numeric in the JSON                 | Delete the lockfile manually; `isStale` defends against malformed but only if `acquired_at` is missing |
| `principal: 200000.0` (float) appears in YAML or JSON               | Money value was unquoted in YAML or passed as JS number            | Re-quote as string: `"200000.00"`. Pydantic `condecimal` rejects float at boundary |

---

## Cross-References

- **Plans:** `.planning/phases/09-duckdb-orchestration/09-{00..07}-*-PLAN.md` —
  the canonical authority for every Phase 9 design decision (D-XX-NN).
- **RESEARCH:** `.planning/phases/09-duckdb-orchestration/09-RESEARCH.md` —
  Pinned schema DDL, lockfile pattern provenance, the 5 Pitfalls.
- **PATTERNS:** `.planning/phases/09-duckdb-orchestration/09-PATTERNS.md` —
  Pattern Assignments + Critical Issues (lockfile #1, DECIMAL string #2,
  schema normalization #3).
- **DATA_CONTRACT.md:** layer rules; the "Phase 9 Layer Examples"
  section is the authoritative cross-reference for layer
  classification of Phase 9 artifacts.
- **CLAUDE.md:** Money discipline (Decimal-from-string,
  ROUND_HALF_UP), Reference Layer convention (`source:` +
  `effective:`), Skill portability (Phase 10 may move this doc
  under `.claude/skills/mortgage-ops/references/`).
- **career-ops precedent:** `career-ops/scripts/lockfile.mjs` and
  `career-ops/scripts/db-write.mjs` are the verbatim ports
  underlying Phase 9 with three renames (CAREER_OPS -> MORTGAGE_OPS,
  `.career-ops.lock` -> `.lock`, header citation block).

---

## Future Work

- **Phase 10 progressive disclosure (D-07-01).** This doc lives at
  repo-root `references/` for now. Phase 10 will decide whether to
  (a) progressive-disclose it via `.claude/skills/mortgage-ops/SKILL.md`
  `references:` frontmatter, (b) move it under
  `.claude/skills/mortgage-ops/references/`, or (c) symlink. Until
  Phase 10 ships, the doc is reachable today by humans + Claude
  sessions reading the repo.
- **v2 lockfile hardening.** Replace the bespoke read-back pattern
  with `proper-lockfile` (npm) when the project takes a hard
  dependency on it for other reasons. The current primitive works
  on every filesystem and survives stale locks; v2 would buy
  cleaner semantics (signal-handling, exit hooks) at the cost of a
  new dep.
- **v2 cross-process Python read access.** The DB is opened
  read-write by Node only. If Python code needs read access (e.g.,
  a future test harness that introspects the DB without shelling
  out to `db-write.mjs query`), use DuckDB's Python bindings in
  read-only mode (`duckdb.connect(path, read_only=True)`). v1
  intentionally keeps Python out of the DB to avoid the
  Pitfall 4 (Cross-Process DuckDB Access) trap.
- **Doc freshness check.** This doc is supplementary to PLAN.md +
  RESEARCH.md (which are the authoritative sources). A future plan
  may add a CI check that diffs section headers here against the
  shipped subcommand list in db-write.mjs to catch staleness as the
  orchestration evolves.
