# Phase 9: DuckDB Persistence & Node Orchestration — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 8 NEW + 3 MODIFIED (orchestration/, data/known-loans.yml, references/data-layer.md, tests/test_orchestration/, package.json, .gitignore append, pyproject.toml append, DATA_CONTRACT.md cross-ref)
**Analogs found:** 7 / 8 strong — career-ops `scripts/{init-db,db-write,lockfile}.mjs` is the canonical reference per `mortgage-ops/CLAUDE.md` line 24 ("Mirror career-ops/scripts/db-write.mjs and lockfile.mjs patterns") and `.planning/PROJECT.md:91`.

> **Important context shift vs. earlier phases.** Phases 1–8 were Python-only and treated career-ops as a *soft-reference only* (Phase 1 PATTERNS line 5: "Where a sibling pattern exists, it is cited as a soft reference"). Phase 9 *inverts* that: career-ops is the **direct copy-target** for all three Node `.mjs` files. The skill-level instruction at `mortgage-ops/CLAUDE.md:24` is unambiguous — "Mirror" means line-for-line port with renames (`career-ops` → `mortgage-ops`, applications/reports/pipeline tables → loans/scenarios/reports/payments/applicants/properties tables). Do *not* reinvent the lockfile or the dispatcher; port them.

> **Hard pre-condition for the planner:** the four critical issues raised in the spawn message (lockfile mechanics, DECIMAL round-trip, schema normalization, package.json placement) are answered in the dedicated **§Critical Issues Surfaced** section at the bottom; planner MUST read that before drafting plan-level decisions.

---

## File Classification

### NEW files (Phase 9 creates)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `orchestration/init-db.mjs` | schema bootstrapper (idempotent CREATE) | one-shot batch (no I/O after run) | `career-ops/scripts/init-db.mjs` | exact |
| `orchestration/lockfile.mjs` | concurrency primitive (`acquireLock` / `releaseLock` / `withLock`) | utility (filesystem-backed mutex) | `career-ops/scripts/lockfile.mjs` | exact |
| `orchestration/db-write.mjs` | central writer CLI (subcommand dispatcher) | request-response (CLI args → DuckDB transaction → JSON/markdown) | `career-ops/scripts/db-write.mjs` | exact |
| `orchestration/render-markdown.mjs` *(or fold into `db-write.mjs --render-markdown`)* | report renderer (DB → `data/loans.md`, `data/scenarios.md`) | transform (SQL SELECT → markdown table) | `career-ops/scripts/db-write.mjs:590-648` (`cmdRenderMarkdown`) | exact |
| `data/known-loans.yml` | reference catalog (≥ 7 product entries) | static reference data | `data/reference/conforming-limits-2026.yml` (shape + `source:`/`effective:` discipline) | role-match (Reference Layer convention; product-catalog content itself is new) |
| `tests/test_orchestration/__init__.py` | test pkg marker | n/a | `tests/test_reference/__init__.py` (empty) | exact |
| `tests/test_orchestration/test_db_lifecycle.py` | pytest harness shelling out to Node via subprocess | request-response (subprocess → DuckDB inspection) | `tests/test_amortize.py:718-840` (`test_cli_smoke_subprocess_round_trip`) | role-match (subprocess is reused; target binary is `node` not `python`) |
| `tests/test_orchestration/test_known_loans_smoke.py` | YAML loader smoke test | static-data validation | `tests/test_reference/test_schema.py` (parametrized YAML iter + `source:`/`effective:` assertion) | exact |
| `references/data-layer.md` | progressive-disclosure reference doc | static doc | `references/arm-mechanics.md` (Phase 5; only existing `references/*.md`) | exact (format), partial (content is new) |
| `package.json` *(repo root)* | Node manifest pinning `duckdb-async` + `js-yaml` | build-time | `career-ops/package.json` | exact |

### MODIFIED files (Phase 9 touches existing)

| Modified File | Modification | Rationale |
|---|---|---|
| `pyproject.toml` | Append `duckdb>=1.4` to `[project].dependencies` | ROADMAP `.planning/ROADMAP.md` line 21 lists DuckDB in the calc-engine stack; spawn message confirms "Phase 9 adds duckdb to Python side too". Add `[[tool.mypy.overrides]] module = "duckdb"` ignore-block (mirrors existing `numpy_financial` / `yaml` overrides at `pyproject.toml:58-68`). |
| `.gitignore` | Add `data/.lock` and `node_modules/` (DATA_CONTRACT already lists `data/*.duckdb` and the `-wal`/`-shm` sidecars at lines 21–25) | DATA_CONTRACT.md lines 20–22 already enumerate the duckdb files; `.gitignore:22` already has `data/*.duckdb`; need only the lockfile + node_modules additions. |
| `DATA_CONTRACT.md` | Append `data/.lock` row to User Layer table (or to Data Layer if user-content-free); add `package.json` + `package-lock.json` + `node_modules/` to System Layer; add `orchestration/**` row (already present at line 39) cross-reference | The contract already names `orchestration/**` (Phase 9) at line 39 and the duckdb files in User Layer at lines 20–22; the lockfile is a new artifact this phase introduces. |

---

## Pattern Assignments

### `orchestration/lockfile.mjs` (concurrency primitive)

**Analog:** `career-ops/scripts/lockfile.mjs` (full file, 78 lines) — port verbatim, change three constants only.

**Imports + module setup** (`career-ops/scripts/lockfile.mjs:1-12`):
```javascript
import { writeFileSync, readFileSync, unlinkSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const CAREER_OPS = dirname(dirname(fileURLToPath(import.meta.url)));
const LOCK_PATH = join(CAREER_OPS, 'data', '.career-ops.lock');
const STALE_THRESHOLD_MS = 60_000;
const DEFAULT_TIMEOUT_MS = 30_000;
const POLL_INTERVAL_MS = 100;
```

**Renames for mortgage-ops:** `CAREER_OPS` → `MORTGAGE_OPS`; `'.career-ops.lock'` → `'.lock'` (DATA_CONTRACT.md line 22 implies the file name; the spawn message says `data/.lock`). The 60s `STALE_THRESHOLD_MS` is *required by ROADMAP.md:182* ("Stale lockfile recovery triggers at 60s") — do not change.

**Core acquire pattern** (`career-ops/scripts/lockfile.mjs:34-55`) — keep all four moving parts:
```javascript
export async function acquireLock({ timeoutMs = DEFAULT_TIMEOUT_MS, reason = '' } = {}) {
  const deadline = Date.now() + timeoutMs;
  const myLock = { pid: process.pid, acquired_at: Date.now(), reason };

  while (Date.now() < deadline) {
    const existing = readLock();
    if (!existing || isStale(existing)) {
      try {
        writeFileSync(LOCK_PATH, JSON.stringify(myLock, null, 2), { flag: 'w' });
        const readBack = readLock();
        if (readBack && readBack.pid === process.pid && readBack.acquired_at === myLock.acquired_at) {
          return myLock;
        }
      } catch (e) {
        // Race: another process wrote between our read and write.
      }
    }
    await sleep(POLL_INTERVAL_MS);
  }
  const blocker = readLock();
  throw new Error(`Lock acquire timeout after ${timeoutMs}ms. Blocker: ${JSON.stringify(blocker)}`);
}
```

**`withLock` wrapper** (`career-ops/scripts/lockfile.mjs:70-77`) — the public API every db-write subcommand calls:
```javascript
export async function withLock(fn, opts = {}) {
  const lock = await acquireLock(opts);
  try {
    return await fn();
  } finally {
    releaseLock(lock);
  }
}
```

**Conventions established (planner must enforce):**
- Lock content is JSON `{ pid, acquired_at, reason }` — `pid` for diagnostics, `acquired_at` (epoch ms) for staleness, `reason` (subcommand name) for blocker error messages.
- Stale detection is **mtime-equivalent via `acquired_at` field** — *not* `fs.statSync(LOCK_PATH).mtimeMs`. Prefer the JSON-content timestamp because it survives `touch` and is set deterministically by the writer.
- `releaseLock` checks `pid + acquired_at` match before `unlink` — prevents process A from deleting process B's lock during a clock-skew race.
- The "read back after write" verification (lines 43–46) is the *poor-man's compare-and-swap* — required because `writeFileSync` with `flag: 'w'` is **not** atomic-or-fail; the post-write read confirms ownership.

---

### `orchestration/init-db.mjs` (schema bootstrapper)

**Analog:** `career-ops/scripts/init-db.mjs` (full file, 259 lines) — port the structural skeleton; replace the `ENUMS` / `SEQUENCES` / `TABLES` / `INDEXES` / `POST_SETUP` arrays with mortgage-domain content.

**Imports + path resolution** (`career-ops/scripts/init-db.mjs:1-15`):
```javascript
import { Database } from 'duckdb-async';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, mkdirSync } from 'fs';

const CAREER_OPS = dirname(dirname(fileURLToPath(import.meta.url)));
const DB_PATH = join(CAREER_OPS, 'data', 'career-ops.duckdb');

if (!existsSync(join(CAREER_OPS, 'data'))) {
  mkdirSync(join(CAREER_OPS, 'data'), { recursive: true });
}
```

**Idempotency pattern — "try then catch already-exists"** (`career-ops/scripts/init-db.mjs:184-210`):
```javascript
async function runSafe(db, statement, label) {
  // For index creation, pre-check existence to avoid DuckDB's corrupted error message
  const indexMatch = statement.match(/CREATE (?:UNIQUE )?INDEX (\w+)/i);
  if (indexMatch) {
    if (await indexExists(db, indexMatch[1])) {
      console.log(`  skip ${label} (already exists)`);
      return;
    }
  }

  try {
    await db.all(statement);
    console.log(`  ok  ${label}`);
  } catch (e) {
    const msg = String(e?.message ?? '');
    const isAlreadyExists =
      e?.errorType === 'Catalog' ||
      msg.includes('already exists') ||
      msg.includes('Duplicate name');
    if (isAlreadyExists) {
      console.log(`  skip ${label} (already exists)`);
    } else {
      console.error(`  FAIL ${label}: errorType=${e?.errorType} msg=${JSON.stringify(msg)}`);
      throw e;
    }
  }
}
```

**Convention established:** The plan should **not** use `CREATE TABLE IF NOT EXISTS` everywhere — `runSafe` catches DuckDB's `Catalog: already exists` error and treats it as a skip. This is required because `CREATE INDEX IF NOT EXISTS` corrupts DuckDB's error message (career-ops comment line 185); index creation does an explicit `indexExists()` pre-check via `duckdb_indexes()` (lines 172–182). ROADMAP success-criterion #1 ("running it twice on a fresh checkout produces the same schema") is satisfied by this pattern.

**Five-phase sequencing** (`career-ops/scripts/init-db.mjs:212-253`): ENUMS → SEQUENCES → TABLES → INDEXES → POST_SETUP. Mortgage-ops likely needs ENUMs for `loan_type` (`fixed`/`arm`/`fha`/`va`/`usda`/`jumbo`, mirrors `lib/models.py:45`) and `scenario_kind` (`amortization`/`affordability`/`arm`/`refinance`/`stress`/`points`/`apr`).

**Schema design — see §Critical Issue 3 below for the loans/scenarios/reports/payments/applicants/properties table sketch derived from `lib/models.py` + `lib/affordability.py`.**

---

### `orchestration/db-write.mjs` (CLI dispatcher — main writer)

**Analog:** `career-ops/scripts/db-write.mjs` (full file, 747 lines) — port the dispatcher skeleton, write-vs-read command split, lock-or-bare action wrapper, and per-subcommand `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK` discipline. Replace the eleven career-ops subcommands with the four PERS-03 subcommands plus `query`.

**Imports + boundary constants** (`career-ops/scripts/db-write.mjs:19-32`):
```javascript
import { Database } from 'duckdb-async';
import { readFileSync, writeFileSync, existsSync, statSync, readdirSync, unlinkSync, mkdirSync } from 'fs';
import { join, dirname, basename } from 'path';
import { fileURLToPath } from 'url';
import { createHash } from 'crypto';
import { withLock } from './lockfile.mjs';

const SCRIPTS_DIR = dirname(fileURLToPath(import.meta.url));
const CAREER_OPS = dirname(SCRIPTS_DIR);
const DB_PATH = join(CAREER_OPS, 'data', 'career-ops.duckdb');
```

**Argument parser** (`career-ops/scripts/db-write.mjs:55-83`) — supports both `--key value` and `--key=value` forms; **port verbatim**. The comment at line 512 ("`--dir` must NOT be used as a flag name") is a load-bearing trap — `node-pre-gyp` (pulled in by the duckdb native binding) prefix-matches `--dir` to its own `--directory` flag and crashes on module load before user code runs. Mortgage-ops's `--insert-loan` subcommand uses `--json` for fixture path (mirrors the spawn message: `--insert-loan --json fixtures/loan.json`).

**Subcommand handler — INSERT with transaction wrapping** (`career-ops/scripts/db-write.mjs:346-368`, `cmdInsertReport`):
```javascript
async function cmdInsertReport(db, flags) {
  const { file } = flags;
  if (!file) throw new Error('--file required');
  if (!existsSync(file)) throw new Error(`File not found: ${file}`);

  const parsed = parseReport(file);
  if (!parsed.company || !parsed.role) {
    throw new Error(`Could not parse company/role from first line of ${file}. ...`);
  }

  await db.run('BEGIN TRANSACTION');
  try {
    const { applicationId, reportId, seqNum } = await insertReportCore(db, parsed);
    await db.run('COMMIT');
    console.log(`insert-report: application=${applicationId} report=${reportId} seq_num=${seqNum}`);
  } catch (e) {
    await db.run('ROLLBACK');
    throw e;
  }
}
```

**Apply to mortgage-ops:**
- `cmdInsertLoan(db, flags)` — read `flags.json`, JSON.parse, validate against the loans table schema, INSERT … RETURNING id, COMMIT or ROLLBACK. Loan fields map 1:1 from `lib/models.py:36-45` (`Loan.principal`, `annual_rate`, `term_months`, `origination_date`, `loan_type`).
- `cmdInsertScenario(db, flags)` — accept `--loan-id N --kind {amortization|affordability|arm|...} --json result.json`, INSERT into scenarios table with the JSON blob in a `result_json TEXT` (or DuckDB JSON) column, COMMIT.
- `cmdInsertReport(db, flags)` — accept `--scenario-id N --file reports/foo.md`, INSERT body verbatim into reports table.
- `cmdRenderMarkdown(db, positional)` — direct port of career-ops `cmdRenderMarkdown` (lines 590–648); see next section.

**Dispatcher — write-vs-read split + lock-or-bare action** (`career-ops/scripts/db-write.mjs:687-740`):
```javascript
async function run() {
  const { command, flags, positional } = parseArgs(process.argv.slice(2));
  // ... usage check ...

  const handlers = {
    'insert-pipeline': (db) => cmdInsertPipeline(db, flags),
    // ... other subcommand handlers ...
    'query': (db) => cmdQuery(db, flags),
  };

  const handler = handlers[command];
  if (!handler) {
    console.error(`Unknown command: ${command}`);
    process.exit(1);
  }

  const needsLock = WRITE_COMMANDS.has(command);
  const action = async () => {
    const db = await Database.create(DB_PATH);
    try {
      await handler(db);
      // Auto-refresh derived artifacts after any write
      // ... domain-specific refresh hooks ...
    } finally {
      await db.close();
    }
  };

  if (needsLock) {
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

**Conventions established:**
- `WRITE_COMMANDS` Set (career-ops line 668) gates which subcommands acquire the lock — mortgage-ops's `--insert-loan`, `--insert-scenario`, `--insert-report`, `--render-markdown` are all writes; `--query` is read-only and bypasses the lock.
- Every write subcommand wraps its mutations in explicit `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK try/catch` — DuckDB single-writer semantics + transaction rollback are *layered* on top of `withLock`. Both layers are required (lockfile prevents process collision; transaction prevents mid-write crash from leaving partial rows).
- `Database.create(DB_PATH)` followed by `try { await handler(db); } finally { await db.close(); }` — never leak the connection; close in a `finally` so an exception still releases the duckdb handle.
- Top-level `run().catch(err => { console.error('Fatal:', ...); process.exit(1); })` — error envelope every callable script needs.

---

### `orchestration/render-markdown.mjs` *(or `db-write.mjs --render-markdown` subcommand)*

**Analog:** `career-ops/scripts/db-write.mjs:590-648` (`cmdRenderMarkdown`).

**Renderer pattern** (`career-ops/scripts/db-write.mjs:590-628`):
```javascript
async function cmdRenderMarkdown(db, positional) {
  const target = positional[0] || 'all';
  if (target === 'applications' || target === 'all') {
    const rows = await db.all(`
      SELECT row_number() OVER (ORDER BY applied_date, id) AS num,
             strftime(applied_date, '%Y-%m-%d') AS date, company, role,
             CAST(score AS DOUBLE) AS score,
             CAST(status AS VARCHAR) AS status,
             has_pdf, latest_report_id, notes
      FROM applications
      ORDER BY applied_date, id
    `);
    // ... build map of supporting joins ...
    const header = [
      `<!-- Generated from data/career-ops.duckdb — edit via scripts, not directly -->`,
      `# Applications Tracker`,
      ``,
      `| # | Date | Company | Role | Score | Status | PDF | Report | Notes |`,
      `|---|------|---------|------|-------|--------|-----|--------|-------|`,
    ];
    const body = rows.map(r => {
      // ... row → markdown table line ...
    }).join('\n');
    writeFileSync(APPLICATIONS_MD, header.join('\n') + '\n' + body + '\n', 'utf-8');
    console.log(`applications.md: ${rows.length} rows → ${APPLICATIONS_MD}`);
  }
  // ... other targets ...
}
```

**Conventions established:**
- The `<!-- Generated from data/...duckdb — edit via scripts, not directly -->` HTML comment (line 610, 638) is **load-bearing** — both ROADMAP success-criterion #4 ("byte-identical across runs (no hand-edits possible — file is regenerated from scratch)") and the existing `mortgage-ops/CLAUDE.md` "Do NOT edit by hand -- rerun npm run render to rebuild from DuckDB" doctrine (career-ops CLAUDE.md inherited). Carry the comment to mortgage-ops.
- **Cast every DuckDB DECIMAL to a string before string-templating** (see §Critical Issue 2 below). The career-ops renderer dodges the issue with `CAST(score AS DOUBLE)` — that is *wrong* for money fields. Mortgage-ops must use `CAST(loan.principal AS VARCHAR)` for any DECIMAL(14,2) that enters a markdown line.
- Apply to mortgage-ops: render `data/loans.md` (loans table summary) and `data/scenarios.md` (scenarios + latest report link). Targets are positional args: `node orchestration/db-write.mjs render-markdown loans` / `... scenarios` / `... all`.

---

### `package.json` (Node manifest at repo root — see §Critical Issue 4)

**Analog:** `career-ops/package.json` (full file, 41 lines).

**Excerpt to copy** (`career-ops/package.json:1-40`):
```json
{
  "name": "mortgage-ops",
  "version": "0.1.0",
  "description": "Personal-use mortgage analysis: deterministic Python calc engine + Claude skill orchestration",
  "scripts": {
    "init": "node orchestration/init-db.mjs",
    "render": "node orchestration/db-write.mjs render-markdown all",
    "query": "node orchestration/db-write.mjs query"
  },
  "dependencies": {
    "duckdb-async": "^1.4.2",
    "js-yaml": "^4.1.1"
  }
}
```

**Pinned versions:**
- `duckdb-async ^1.4.2` — locked from `career-ops/package.json:36`.
- `js-yaml ^4.1.1` — locked from `career-ops/package.json:37`. Required for parsing `data/known-loans.yml` from the Node side at scenario-construction time.
- **Do not** add `playwright` (career-ops needs it for PDF generation; mortgage-ops does not).

---

### `data/known-loans.yml` (Reference Layer catalog)

**Analog:** `data/reference/conforming-limits-2026.yml` (head excerpt at `data/reference/conforming-limits-2026.yml:1-30`) — same `source:` + `effective:` discipline, same all-numeric-as-quoted-strings rule, same load-via-`lib.rules._loader` future path.

**Excerpt to copy structure** (`data/reference/conforming-limits-2026.yml:1-15`):
```yaml
# data/known-loans.yml
source: "https://www.fanniemae.com/singlefamily/originating-underwriting/products"  # placeholder; planner picks the canonical product-glossary URL
effective: 2026-01-01
notes: |
  Catalog of seven baseline mortgage products covering the Phase 9 ROADMAP
  success-criterion #5 list (30yr fixed conv, 15yr fixed conv, ARM 5/1, ARM 7/1,
  FHA 30yr, VA 30yr, jumbo 30yr). Each entry pins term_months + product_class +
  default rate-source notes. All numeric scalars are quoted strings so PyYAML
  emits str (not float); loader callers wrap in Decimal(...) at consumption
  time (mirrors data/reference/conforming-limits-2026.yml Pitfall 1 note).
products:
  - id: conv-30yr-fixed
    label: "30-Year Fixed Conventional"
    loan_type: fixed
    term_months: 360
    notes: "Conforming; standard amortization; FRED MORTGAGE30US is the canonical rate source"
  # ... 6 more entries ...
```

**Conventions established:**
- File lives under `data/known-loans.yml` (NOT `data/reference/known-loans.yml`) per DATA_CONTRACT.md line 67 ("`data/known-loans.yml` (Phase 9) product catalog" listed as Reference Layer).
- Reference Layer rules apply: `source:` URL + `effective:` ISO date both mandatory; the existing `tests/test_reference/test_schema.py` (parametrized over `data/reference/*.yml`) does **NOT** cover `data/known-loans.yml` because it globs only the `reference/` subdir. The new `tests/test_orchestration/test_known_loans_smoke.py` mirrors that test's shape but globs `data/known-loans.yml` directly.
- All seven products required by ROADMAP success-criterion #5: `30yr fixed conv`, `15yr fixed conv`, `ARM 5/1`, `ARM 7/1`, `FHA 30yr`, `VA 30yr`, `jumbo 30yr`. Field schema must round-trip into `lib/models.py:Loan` (so `loan_type` value MUST be one of the Literal options at `lib/models.py:45`: `"fixed" | "arm" | "fha" | "va" | "usda" | "jumbo"`).

---

### `tests/test_orchestration/test_db_lifecycle.py` (subprocess-based pytest)

**Analog:** `tests/test_amortize.py:718-840` (`test_cli_smoke_subprocess_round_trip` + siblings) — same `subprocess.run([sys.executable, str(SCRIPT_PATH), ...], capture_output=True, text=True, check=True)` idiom; substitute `["node", "orchestration/init-db.mjs"]`.

**Excerpt to adapt** (`tests/test_amortize.py:722-751`):
```python
def test_cli_smoke_subprocess_round_trip(tmp_path: Path) -> None:
    """AMRT-06: write input JSON, invoke script via subprocess, parse output JSON."""
    input_path = tmp_path / "loan.json"
    input_path.write_text(
        json.dumps({"loan": {"principal": "200000.00", "annual_rate": "0.065000",
                              "term_months": 360, "origination_date": "2026-05-01"}})
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(input_path)],
        capture_output=True, text=True, check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["monthly_pi"] == "1264.14"
    assert out["payments"][-1]["balance"] == "0.00"
```

**Apply to Phase 9** — three test cases at minimum, all using `subprocess.run(["node", ...])`:

1. **`test_init_db_idempotent`** — invoke `node orchestration/init-db.mjs` twice in a row against a `tmp_path` DB; second run exits 0 and prints "skip" lines. Implements ROADMAP success-criterion #1.
2. **`test_insert_loan_round_trip`** — write a fixture JSON file, invoke `node orchestration/db-write.mjs insert-loan --json <path>`, then invoke `... query --sql "SELECT principal FROM loans"` and assert the returned string equals the input string (validates DECIMAL round-trip per §Critical Issue 2).
3. **`test_concurrent_write_serializes`** — `subprocess.Popen` two `insert-loan` invocations in parallel; assert both succeed, neither corrupts, and the second one either waited (took > 0.1s) or failed fast with the "Lock acquire timeout" string. Implements ROADMAP success-criterion #2.
4. **`test_stale_lock_recovery`** — write a synthetic `data/.lock` with `acquired_at: <Date.now() - 65000>` to `tmp_path/data/`, invoke `insert-loan`, assert it succeeds and the stale lock was reclaimed. Implements ROADMAP success-criterion #3.

**Convention established:** Use `tmp_path` + a `MORTGAGE_OPS_DB_PATH` env var (not yet present in `init-db.mjs` — Phase 9 must add an env-var override on the `DB_PATH` const so tests can point the Node script at a throwaway DB). Career-ops did NOT need this because it had no Python tests; mortgage-ops's pytest harness is the *new* requirement that forces the env-var seam.

---

### `tests/test_orchestration/test_known_loans_smoke.py` (Reference Layer smoke test)

**Analog:** `tests/test_reference/test_schema.py` (full file, 36 lines) — port verbatim, change the path glob.

**Excerpt to copy** (`tests/test_reference/test_schema.py:18-36`):
```python
REF_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data" / "reference"

def _ref_files() -> list[Path]:
    return sorted(p for p in REF_DIR.glob("*.yml"))

@pytest.mark.parametrize("path", _ref_files(), ids=lambda p: p.stem)
def test_reference_yaml_has_source_and_effective(path: Path) -> None:
    raw = yaml.safe_load(path.read_text())
    assert isinstance(raw, dict), f"{path.name} must parse to a dict (REF-09)"
    assert "source" in raw, f"{path.name} missing `source:` (REF-09)"
    assert "effective" in raw, f"{path.name} missing `effective:` (REF-09)"
    assert re.match(r"^https?://", raw["source"]), (...)
    assert isinstance(raw["effective"], date), (...)
```

**Apply to Phase 9** — narrow scope to `data/known-loans.yml`, add product-list assertions:

```python
KNOWN_LOANS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "known-loans.yml"

def test_known_loans_has_source_and_effective() -> None:
    raw = yaml.safe_load(KNOWN_LOANS_PATH.read_text())
    assert "source" in raw and "effective" in raw  # PERS-07 + REF-09 inheritance
    # ROADMAP success-criterion #5: at least seven product entries
    assert len(raw["products"]) >= 7
    # Every product's loan_type round-trips into lib.models.Loan.loan_type Literal
    valid_types = {"fixed", "arm", "fha", "va", "usda", "jumbo"}
    for p in raw["products"]:
        assert p["loan_type"] in valid_types, f"{p['id']} has invalid loan_type"
```

---

### `references/data-layer.md` (progressive-disclosure doc)

**Analog:** `references/arm-mechanics.md` (the only existing `references/*.md`; head excerpt above).

**Conventions to copy from `references/arm-mechanics.md:1-10`:**
- Top-line `# X — mortgage-ops Phase N Reference` heading.
- Numbered conceptual sections (`## 1. ...`, `## 2. ...`).
- Each section ends with a `**Citations:**` block linking to authoritative external sources.
- "Cited from `lib.<module>.<class>.__doc__` per ROADMAP SC-N" backlink to the calling code.

**Apply to `references/data-layer.md`:** sections for (1) lockfile mechanics + 60s stale recovery, (2) DuckDB single-writer semantics + transaction layering, (3) DECIMAL string round-trip rule (single most-load-bearing entry — see §Critical Issue 2), (4) schema overview (loans/scenarios/reports/payments/applicants/properties), (5) markdown-render contract (regenerated; never hand-edit). Cite the career-ops files as "ported from" and `lib/models.py` / `lib/affordability.py` as the schema-source-of-truth.

---

## Shared Patterns

### DuckDB single-writer + lockfile layering
**Sources:** `career-ops/scripts/db-write.mjs:719-740`, `career-ops/scripts/lockfile.mjs:70-77`
**Apply to:** every write subcommand in `orchestration/db-write.mjs`
**Rule:** `withLock(action, { reason: command })` wraps a function whose body opens DuckDB, runs `BEGIN TRANSACTION`, executes the SQL, runs `COMMIT` or `ROLLBACK` on exception, and closes the connection in a `finally`. Both layers are mandatory; neither alone suffices.

### "fail loud, no inference" boundary discipline
**Sources:** `lib/affordability.py:407-429` (Household.size docstring — "size is REQUIRED ... no inference from len(applicants)"), `lib/arm.py:36-38` (ARMTerms — "Every field is REQUIRED except note_rate; floor_rate has NO default per D-02 (forces explicit caller choice)")
**Apply to:** every CLI flag in `db-write.mjs` and every column in the loans/scenarios schema
**Rule:** No silent defaults for inputs the caller could reasonably specify. If `--insert-loan` is missing `--json`, throw `Error('--json required')` (career-ops `db-write.mjs:189` shows the canonical idiom). The schema mirrors this — every Loan column derived from `lib/models.py:36-45` is `NOT NULL` except `origination_date` (the lone Optional in the Pydantic model).

### Decimal string round-trip discipline
**Sources:** `lib/money.py:29-36` (`to_money(value: str) -> Decimal`), `scripts/_cli_helpers.py:67-106` (D-19 envelope rejecting JSON floats), `lib/models.py:23-33` (`Money` / `Rate` Annotated alias)
**Apply to:** every DECIMAL column read or written via `db-write.mjs`
**Rule:** mortgage-ops's project-wide invariant is "money values are always strings at boundaries; only inside Python `Decimal` arithmetic are they Decimal". The DuckDB layer is just another boundary. See §Critical Issue 2 for the duckdb-async-specific concretization.

### Reference Layer YAML discipline
**Sources:** `data/reference/conforming-limits-2026.yml:1-23`, `tests/test_reference/test_schema.py` (parametrized REF-09 enforcement)
**Apply to:** `data/known-loans.yml`
**Rule:** Mandatory `source:` (http(s) URL) + `effective:` (unquoted ISO date). All numeric values quoted as strings so PyYAML returns `str`, not `float` (Pitfall 1 in the existing reference YAMLs).

---

## No Analog Found

| File | Role | Reason |
|---|---|---|
| (none) | — | Every Phase 9 file has a strong analog, either in career-ops (Node) or in the existing mortgage-ops codebase (Python tests, reference YAML, references doc). |

---

## Critical Issues Surfaced

The four issues raised in the spawn message are answered here for the planner's plan-level decisions.

### Critical Issue 1 — career-ops `withLock()` implementation details

**Read from `career-ops/scripts/lockfile.mjs:34-77`. Three findings:**

1. **No `O_EXCL` flag.** The acquire loop uses `writeFileSync(LOCK_PATH, ..., { flag: 'w' })` (line 42) — that is `O_TRUNC | O_CREAT | O_WRONLY`, not `O_EXCL`. The "atomicity" comes from the **read-back-and-verify** at lines 43–46 (`readBack.pid === process.pid && readBack.acquired_at === myLock.acquired_at`), which acts as a poor-man's compare-and-swap. **Recommendation for mortgage-ops:** keep the `flag: 'w'` + read-back idiom. Switching to `flag: 'wx'` (O_EXCL+O_CREAT) would crash on every acquire because the file likely exists from a prior stale-but-still-on-disk lock; the existing code intentionally OVERWRITES stale locks (lines 40–42: `if (!existing || isStale(existing))`).

2. **Lock content is `{ pid: process.pid, acquired_at: Date.now(), reason }`** (line 36). Three fields, JSON-serialized, pretty-printed (`JSON.stringify(myLock, null, 2)`). `pid` for diagnostics, `acquired_at` (epoch milliseconds) for staleness math, `reason` (subcommand name) for blocker error messages.

3. **Stale recovery is `acquired_at`-based, not `mtime`-based.** Line 28-32: `function isStale(lock) { ... const age = Date.now() - lock.acquired_at; return age > STALE_THRESHOLD_MS; }` with `STALE_THRESHOLD_MS = 60_000` at line 10. This is **deliberate**: `mtime` would be vulnerable to filesystem `touch` and clock-skew between filesystem-clock and process-clock. The JSON-content timestamp is set deterministically by the writer in the same wall-clock domain that reads it back. **Recommendation for mortgage-ops:** mirror exactly. ROADMAP success-criterion #3 ("a lockfile with `mtime > 60s ago` is reclaimed") is mis-worded — the actual check is `acquired_at > 60s ago`. Plan should clarify the success criterion in the test name.

### Critical Issue 2 — DuckDB DECIMAL(14,2) round-trip via duckdb-async

**This is the load-bearing risk for the entire phase.** mortgage-ops's project-wide invariant is "money values are Decimal-from-string; never float". DuckDB stores DECIMAL(14,2) as a fixed-point integer internally — but `duckdb-async` (the Node binding) returns DECIMALs as **JavaScript numbers** for small-precision values and as **bigint** for values exceeding 2^53, neither of which preserves Decimal semantics through JSON.stringify.

**Evidence from career-ops:**
- `career-ops/scripts/db-write.mjs:567-579` (`cmdRefreshDashboardJson`) uses `CAST(a.score AS DOUBLE) AS score` — DOUBLE is float, which is why career-ops tolerated it (scores are `DECIMAL(3,1)` in `[0, 5.0]` — never lose precision at that scale).
- `career-ops/scripts/db-write.mjs:594-601` (`cmdRenderMarkdown`) similarly uses `CAST(score AS DOUBLE) AS score`.
- `career-ops/scripts/db-write.mjs:650-657` (`jsonReplacer`) handles `bigint` (`return Number(value)`) and `Buffer` (`return [bytes:N]`) but NOT DECIMAL — confirming DOUBLE was the workaround.

**For mortgage-ops, DOUBLE is unacceptable** — the Phase 1 D-15 invariant (`Schedule.total_interest == payments[-1].cumulative_interest` *exactly*; see `lib/models.py:76-91`) requires that a 360-payment schedule with interest accumulation around $300k preserves cents to the last digit, which DOUBLE cannot do (53-bit mantissa = ~15 decimal digits, but accumulation drift over 360 ROUND_HALF_UP operations is real).

**The required workaround** — every DECIMAL column read out of DuckDB MUST be cast to VARCHAR in the SELECT statement, and every DECIMAL value written in MUST be passed as a JSON string. The Python boundary already enforces this via `lib/money.py:29` and `scripts/_cli_helpers.py:67-106`; the Node boundary must do the same.

```javascript
// Correct: SELECT ... CAST(principal AS VARCHAR) AS principal_str ...
// Then in the markdown renderer: ... | ${r.principal_str} | ...
// Never: const x = r.principal * 100;  // r.principal is a JS number — already lost precision
```

For INSERTs, mortgage-ops can pass the JSON string directly to a DECIMAL parameter (`db.run('INSERT INTO loans (principal) VALUES (?)', '200000.00')`) — DuckDB parses the string into its fixed-point representation losslessly. This must be tested with a round-trip assertion (`test_insert_loan_round_trip` above): "the string in equals the string out, byte-for-byte".

**Plan-level decision required:** add a `references/data-layer.md` section explicitly documenting this rule, AND add a lint-style pytest that greps `orchestration/*.mjs` for `CAST.*AS DOUBLE` against any column drawn from a DECIMAL(14,2) field — failing if it appears. (Mirrors the pattern of `tests/test_reference/test_yaml_count_audit.py` which is a static repository introspection test.)

### Critical Issue 3 — Schema design for cross-scenario analysis

**ROADMAP success-criterion #1 enumerates SIX tables: `loans`, `scenarios`, `reports`, `payments`, `applicants`, `properties`.** That is a **normalized** schema, not a single-blob `loans` table. Analysis of `lib/models.py` + `lib/affordability.py` confirms this is the right shape:

- **`loans`** mirrors `lib/models.py:36-45` (`Loan`): `principal DECIMAL(14,2)`, `annual_rate DECIMAL(7,6)`, `term_months INTEGER`, `origination_date DATE`, `loan_type ENUM`. PK on auto-increment `id`.
- **`payments`** mirrors `lib/models.py:48-61` (`Payment`): one row per period, FK to `loan_id` (or `scenario_id` for scenario-specific schedules), `period INTEGER`, `payment_date DATE`, `payment/principal/interest/extra_principal/balance/cumulative_interest/cumulative_principal DECIMAL(14,2)`. The cumulative-interest invariant (Phase 1 D-15, `lib/models.py:76-91`) is enforced by Python before the row is INSERTed; SQL CHECK constraints would be redundant and slower.
- **`applicants`** mirrors `lib/affordability.py:354-365` (`Applicant`): `name VARCHAR`, `gross_monthly_income DECIMAL(14,2)`, `credit_score INTEGER CHECK (credit_score BETWEEN 300 AND 850)`. Many-to-one with `loans` via a join table OR a `loan_id` FK if v1 assumes one Household per Loan.
- **`properties`** derives from `lib/affordability.py:339-351` (`LocationFIPS`): `state_fips VARCHAR(2)`, `county_fips VARCHAR(3)`, `county_name VARCHAR`, `state VARCHAR(2)`, `zip VARCHAR`. This is per-property-per-scenario, so FK from `scenarios.property_id`.
- **`scenarios`** is the cross-cutting analysis table — links a `loan_id` + `kind ENUM('amortization','affordability','arm','refinance','stress','points','apr')` + `result_json TEXT` (the full Pydantic response from `lib/affordability.py:547-592` `AffordabilityResponse`, `lib/arm.py:214-236` `ARMSchedule`, etc., serialized to JSON). PK on `id`; `created_at TIMESTAMP DEFAULT now()`.
- **`reports`** mirrors career-ops `reports` table (`career-ops/scripts/init-db.mjs:83-101`): `seq_num INTEGER UNIQUE`, `scenario_id INTEGER FK`, `report_date DATE`, `body TEXT NOT NULL`, `is_latest BOOLEAN DEFAULT TRUE`, `created_at TIMESTAMP`.

**Why normalized over single-blob:** ROADMAP success-criterion #4 mentions `data/scenarios.md` as a regenerated view; cross-scenario SQL queries (the explicit Phase 9 goal in the spawn message) require joinable foreign-key relationships, not opaque JSON blobs in a single `loans` table. The `result_json TEXT` column in `scenarios` is the escape hatch for shape-evolving response payloads (Phase 4 `AffordabilityResponse` has 22 fields; Phase 5 `ARMSchedule` has different fields; storing as JSON avoids schema-migration churn while still allowing `loans` + `payments` + `applicants` + `properties` to be queried with joins).

**Plan-level decision required:** lock the six-table normalized schema in CONTEXT.md before drafting plans; the planner should derive every column from a specific `lib/*.py:lineno` citation and document the citation in the `init-db.mjs` table-creation comment.

### Critical Issue 4 — package.json placement (root vs. orchestration/)

**Recommendation: repo root.**

**Rationale:**
1. **Career-ops puts it at root** (`career-ops/package.json` is at `/Users/cujo253/Documents/career-ops/package.json`) — direct mirror of the canonical reference per `mortgage-ops/CLAUDE.md:24`.
2. **`npm run` semantics** — running `npm run init` from the repo root discovers `package.json` in the cwd; users always invoke from the repo root in mortgage-ops's documented workflows. Putting it under `orchestration/` would force `cd orchestration && npm run init` which breaks the mental model and doubles the cognitive load.
3. **`node_modules` lives next to `package.json`** — at root means one `node_modules/` (gitignored, easy single-line `.gitignore` entry); under `orchestration/` would either leave `node_modules/` in `orchestration/` (DATA_CONTRACT.md violation: System Layer should not contain machine-generated artifacts) or require a workspace setup, which is overkill for two dependencies.
4. **`pyproject.toml` is also at root** (`/Users/cujo253/Documents/mortgage-ops/pyproject.toml`) — keeping both manifests at the same level mirrors monorepo convention and makes the project structure legible at first `ls`.
5. **The Reference Layer at `data/known-loans.yml`** (also Phase 9) is at root-level `data/`, not under `orchestration/` — co-locating Phase 9 artifacts under one subdirectory is not a goal.

**Counter-argument considered and rejected:** "Put `package.json` under `orchestration/` because that is where the Node code lives." This conflates *source-code organization* with *manifest-and-deps organization*. The `pyproject.toml` lives at root even though `lib/` and `scripts/` are subdirs; the same principle applies to Node.

**Plan-level decision required:** lock `package.json` at repo root in CONTEXT.md. Add `node_modules/` to `.gitignore` in the same plan that creates `package.json`.

---

## Metadata

**Analog search scope:** `/Users/cujo253/Documents/career-ops/scripts/`, `/Users/cujo253/Documents/career-ops/package.json`, `/Users/cujo253/Documents/career-ops/CLAUDE.md`; `/Users/cujo253/Documents/mortgage-ops/lib/`, `/Users/cujo253/Documents/mortgage-ops/scripts/`, `/Users/cujo253/Documents/mortgage-ops/tests/`, `/Users/cujo253/Documents/mortgage-ops/data/reference/`, `/Users/cujo253/Documents/mortgage-ops/references/`, `/Users/cujo253/Documents/mortgage-ops/.planning/{ROADMAP,REQUIREMENTS,PROJECT}.md`, `/Users/cujo253/Documents/mortgage-ops/DATA_CONTRACT.md`, `/Users/cujo253/Documents/mortgage-ops/.gitignore`, `/Users/cujo253/Documents/mortgage-ops/pyproject.toml`, `/Users/cujo253/Documents/mortgage-ops/.planning/phases/01-foundations-money-discipline/01-PATTERNS.md` (format reference), `/Users/cujo253/Documents/mortgage-ops/.planning/phases/05-arm-modeling/05-PATTERNS.md` (format reference).

**Files scanned:** 14 in career-ops (3 read in full + 11 listed); 27 in mortgage-ops (full + targeted reads).

**Pattern extraction date:** 2026-05-02.
