---
phase: 09
plan: 04
type: execute
wave: 4
depends_on:
  - "09-00"
  - "09-01"
  - "09-02"
  - "09-03"
files_modified:
  - orchestration/db-write.mjs
  - tests/test_orchestration/test_render_markdown.py
must_haves:
  truths:
    - "orchestration/db-write.mjs cmdRenderMarkdown handler exists and is wired into the dispatcher"
    - "Render-markdown supports positional targets: loans, scenarios, all (default all)"
    - "Both data/loans.md and data/scenarios.md begin with '<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->'"
    - "Both files are byte-identical across consecutive runs against the same DB state (zero drift)"
    - "All DECIMAL columns are SELECTed via CAST AS VARCHAR (Critical Issue 2 inheritance)"
    - "All SELECTs use explicit ORDER BY id ASC (Pitfall 3: deterministic row order)"
    - "No generated_at timestamp embedded in markdown output (Pitfall 3: byte-equality)"
    - "test_render_markdown_byte_identical xfail flips to passing"
  artifacts:
    - path: "orchestration/db-write.mjs"
      provides: "Extended with cmdRenderMarkdown subcommand (PERS-06 closure)"
      contains: "async function cmdRenderMarkdown"
  key_links:
    - from: "orchestration/db-write.mjs cmdRenderMarkdown"
      to: "data/loans.md, data/scenarios.md"
      via: "writeFileSync of SELECT-driven markdown table"
      pattern: "writeFileSync.*loans.md|writeFileSync.*scenarios.md"
autonomous: true
requirements:
  - PERS-06
tags:
  - phase-09
  - duckdb-orchestration
  - render-markdown
  - byte-identical
---

<objective>
**Goal:** Replace the Wave 3 placeholder `cmdRenderMarkdown` (which throws "Not yet implemented") with a real implementation that regenerates `data/loans.md` and `data/scenarios.md` from DuckDB. The output is byte-identical across runs (PERS-06 + ROADMAP SC-4) by virtue of explicit `ORDER BY id ASC` + no embedded timestamps + the PATTERNS-mandated `<!-- Generated from ... -->` header. Flips `test_render_markdown_byte_identical`.

**Purpose:** PERS-06 + ROADMAP SC-4 close: "data/loans.md and data/scenarios.md regenerate from DuckDB and are byte-identical across runs (no hand-edits possible — file is regenerated from scratch)." This is the load-bearing guard against silent state drift between the canonical DB and the human-readable views.

**Output:** orchestration/db-write.mjs +90 lines (cmdRenderMarkdown + LOANS_MD/SCENARIOS_MD constants + 2 SELECT statements with deterministic ORDER BY); 1 xfail flips. data/loans.md and data/scenarios.md become legitimate generated artifacts (already gitignored in Plan 09-02).
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
@orchestration/db-write.mjs
@orchestration/init-db.mjs
@tests/test_orchestration/test_render_markdown.py

<interfaces>
**Render-markdown subcommand surface:**

```
node orchestration/db-write.mjs render-markdown                    # default: all
node orchestration/db-write.mjs render-markdown loans              # loans only
node orchestration/db-write.mjs render-markdown scenarios          # scenarios only
node orchestration/db-write.mjs render-markdown all                # both
```

**Output files:**
- data/loans.md
- data/scenarios.md

**Header (mandatory; load-bearing per PATTERNS Pattern Assignments line 303):**
`<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->`

**Loans table columns (must SELECT in this order, CAST money/rate via VARCHAR):**
- id (INTEGER)
- principal (DECIMAL CAST AS VARCHAR)
- annual_rate (DECIMAL CAST AS VARCHAR)
- term_months (INTEGER)
- origination_date (DATE -> strftime '%Y-%m-%d' or empty string for NULL)
- loan_type (VARCHAR)
- frequency (VARCHAR)

**Scenarios table columns (must SELECT in this order):**
- id (INTEGER)
- loan_id (INTEGER nullable - render as empty string for NULL)
- kind (VARCHAR)
- computed_at (TIMESTAMP -> strftime '%Y-%m-%d %H:%M:%S' for the data column, NOT for render-time)
- notes (VARCHAR nullable - render as empty for NULL)

  Note: scenarios.computed_at is data captured at insert time, not render time.
  This is FINE for byte-equality because it's a fixed column from the DB row, not a re-evaluated NOW().

**Markdown table format:** GitHub-flavored pipe tables, header + separator + body rows.

**Pitfall 3 inheritance from RESEARCH:**
- Every SELECT MUST include explicit ORDER BY id ASC (no implicit row ordering)
- NO generated_at = NOW() embedded in the markdown output (would change every run)
- The mandatory `<!-- Generated from ... -->` comment is FIXED text (no variable interpolation)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement cmdRenderMarkdown in orchestration/db-write.mjs</name>
  <files>orchestration/db-write.mjs</files>
  <read_first>
    - orchestration/db-write.mjs (Wave 3 state) — find the existing cmdRenderMarkdown stub that throws
    - 09-RESEARCH.md "Code Examples" §Example 3 — render-markdown skeleton
    - 09-PATTERNS.md Pattern Assignments "render-markdown.mjs" section + Pitfall 3 (Render-Markdown Determinism)
    - career-ops/scripts/db-write.mjs:590-648 (cmdRenderMarkdown analog)
  </read_first>
  <action>
    Modify `orchestration/db-write.mjs` to:

    1. Add `writeFileSync` to the existing `import ... from 'fs'` line.
    2. Add module-level constants for the two output paths (just below DB_PATH).
    3. Replace the placeholder `cmdRenderMarkdown` with a real implementation.

    **Step 1 — Update imports** (modify the existing `import { readFileSync, existsSync } from 'fs';` line):

    ```javascript
    import { readFileSync, writeFileSync, existsSync } from 'fs';
    ```

    **Step 2 — Add path constants** (insert after `const DB_PATH = ...` line):

    ```javascript
    const LOANS_MD = join(MORTGAGE_OPS, 'data', 'loans.md');
    const SCENARIOS_MD = join(MORTGAGE_OPS, 'data', 'scenarios.md');
    ```

    **Step 3 — Replace the placeholder cmdRenderMarkdown** with the real implementation. The placeholder body currently throws "Not yet implemented — ships in Plan 09-04". Replace ENTIRELY with:

    ```javascript
    async function cmdRenderMarkdown(db, _flags, positional) {
      // Default to 'all' if no target specified
      const target = positional[0] || 'all';
      const validTargets = new Set(['loans', 'scenarios', 'all']);
      if (!validTargets.has(target)) {
        throw new Error(`Invalid render target: ${target}. Must be one of: loans, scenarios, all`);
      }

      const results = {};

      if (target === 'loans' || target === 'all') {
        // Plan 09-04 D-04-02: every DECIMAL column CAST AS VARCHAR (PATTERNS Critical Issue 2)
        // Plan 09-04 D-04-03: explicit ORDER BY id ASC (Pitfall 3: byte-equality contract)
        const rows = await db.all(`
          SELECT id,
                 CAST(principal AS VARCHAR) AS principal,
                 CAST(annual_rate AS VARCHAR) AS annual_rate,
                 term_months,
                 COALESCE(strftime(origination_date, '%Y-%m-%d'), '') AS origination_date,
                 loan_type,
                 frequency
          FROM loans
          ORDER BY id ASC
        `);
        const header = [
          '<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->',
          '# Loans',
          '',
          '| ID | Principal | Annual Rate | Term (mo) | Origination | Type | Frequency |',
          '|----|-----------|-------------|-----------|-------------|------|-----------|',
        ];
        const body = rows.map(r =>
          `| ${Number(r.id)} | ${r.principal} | ${r.annual_rate} | ${r.term_months} | ${r.origination_date} | ${r.loan_type} | ${r.frequency} |`
        );
        const content = header.concat(body).join('\n') + '\n';
        writeFileSync(LOANS_MD, content, 'utf-8');
        results.loans_md = { path: LOANS_MD, rows: rows.length, bytes: content.length };
      }

      if (target === 'scenarios' || target === 'all') {
        // computed_at IS render-deterministic: it's data-captured-at-insert, not NOW().
        // strftime serializes the stored TIMESTAMP into the markdown body verbatim.
        const rows = await db.all(`
          SELECT id,
                 COALESCE(CAST(loan_id AS VARCHAR), '') AS loan_id,
                 kind,
                 strftime(computed_at, '%Y-%m-%d %H:%M:%S') AS computed_at,
                 COALESCE(notes, '') AS notes
          FROM scenarios
          ORDER BY id ASC
        `);
        const header = [
          '<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->',
          '# Scenarios',
          '',
          '| ID | Loan ID | Kind | Computed At | Notes |',
          '|----|---------|------|-------------|-------|',
        ];
        const body = rows.map(r =>
          `| ${Number(r.id)} | ${r.loan_id} | ${r.kind} | ${r.computed_at} | ${r.notes} |`
        );
        const content = header.concat(body).join('\n') + '\n';
        writeFileSync(SCENARIOS_MD, content, 'utf-8');
        results.scenarios_md = { path: SCENARIOS_MD, rows: rows.length, bytes: content.length };
      }

      console.log(JSON.stringify({ ok: true, target, ...results }));
    }
    ```

    **Step 4 — Update the dispatcher to pass `positional` to handlers**. The current dispatcher passes `(db, flags)` only. Render-markdown needs `positional`. Update the action wrapper:

    Find:
    ```javascript
    const action = async () => {
      const db = await Database.create(DB_PATH);
      try {
        await handler(db, flags);
      } finally {
        await db.close();
      }
    };
    ```

    Replace with:
    ```javascript
    const action = async () => {
      const db = await Database.create(DB_PATH);
      try {
        await handler(db, flags, positional);
      } finally {
        await db.close();
      }
    };
    ```

    Other subcommand handlers (`cmdInsertLoan`, `cmdInsertScenario`, `cmdInsertReport`, `cmdQuery`) take `(db, flags)` and ignore the third argument — that's fine (JavaScript silently drops extra args).

    Also update the `parseArgs` destructure in `run()` to extract `positional` (it's already returned by parseArgs from Wave 3; verify the destructure now exposes it):

    Find:
    ```javascript
    const { command, flags } = parseArgs(argv);
    ```

    Replace with:
    ```javascript
    const { command, flags, positional } = parseArgs(argv);
    ```

    Manual smoke test after writing:

    ```bash
    rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal data/mortgage-ops.duckdb-shm
    rm -f data/loans.md data/scenarios.md
    node orchestration/init-db.mjs
    cat > /tmp/loan_a.json <<EOF
    {"principal":"200000.00","annual_rate":"0.065000","term_months":360,"origination_date":"2026-05-01","loan_type":"fixed"}
    EOF
    cat > /tmp/loan_b.json <<EOF
    {"principal":"350000.00","annual_rate":"0.070000","term_months":180,"origination_date":"2026-05-15","loan_type":"jumbo"}
    EOF
    node orchestration/db-write.mjs insert-loan --json /tmp/loan_a.json
    node orchestration/db-write.mjs insert-loan --json /tmp/loan_b.json
    node orchestration/db-write.mjs render-markdown
    cp data/loans.md /tmp/loans_run1.md
    node orchestration/db-write.mjs render-markdown
    diff data/loans.md /tmp/loans_run1.md && echo "byte-identical"
    ```

    Expected: `byte-identical` printed; `data/loans.md` contains 2 loan rows; `data/scenarios.md` contains 0 rows but valid header.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && node --check orchestration/db-write.mjs && node orchestration/db-write.mjs --help</automated>
  </verify>
  <acceptance_criteria>
    - `node --check orchestration/db-write.mjs` exits 0
    - `grep -c "import.*writeFileSync.*from 'fs'" orchestration/db-write.mjs` returns 1
    - `grep -c "const LOANS_MD" orchestration/db-write.mjs` returns 1
    - `grep -c "const SCENARIOS_MD" orchestration/db-write.mjs` returns 1
    - `grep -c "Not yet implemented" orchestration/db-write.mjs` returns 0 (Wave 3 placeholder fully removed; Warning #5 fix-hint compliance — Task 1 action prose says to remove it, this gate makes failure visible)
    - `grep -c "Generated from data/mortgage-ops.duckdb" orchestration/db-write.mjs` returns at least 2 (one per target)
    - `grep -c "ORDER BY id ASC" orchestration/db-write.mjs` returns at least 2 (loans + scenarios SELECTs)
    - `grep -c "CAST(principal AS VARCHAR)" orchestration/db-write.mjs` returns 1
    - `grep -c "CAST(annual_rate AS VARCHAR)" orchestration/db-write.mjs` returns 1
    - `grep -c "writeFileSync(LOANS_MD" orchestration/db-write.mjs` returns 1
    - `grep -c "writeFileSync(SCENARIOS_MD" orchestration/db-write.mjs` returns 1
    - `grep -c "handler(db, flags, positional)" orchestration/db-write.mjs` returns 1
    - `grep -c "const { command, flags, positional } = parseArgs" orchestration/db-write.mjs` returns 1
  </acceptance_criteria>
  <done>
    cmdRenderMarkdown shipped; dispatcher updated; manual smoke test confirms byte-identical regeneration.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip test_render_markdown_byte_identical xfail</name>
  <files>tests/test_orchestration/test_render_markdown.py</files>
  <read_first>
    - tests/test_orchestration/test_render_markdown.py (Wave 0 stub state)
    - tests/conftest.py — node_orchestration_run helper
  </read_first>
  <action>
    Replace the test_render_markdown_byte_identical xfail stub with a real assertion. REMOVE the @pytest.mark.xfail decorator AND replace the body. Add `import json` at top.

    New file content (replaces entire file):

    ```python
    """Phase 9 markdown view regeneration (PERS-06 + ROADMAP SC-4).

    Wave 4 (Plan 09-04) ships orchestration/db-write.mjs --render-markdown.
    The byte-identical guarantee is the load-bearing contract: two
    consecutive renders against the same DB state produce IDENTICAL bytes.
    """

    from __future__ import annotations

    import json
    from pathlib import Path


    def test_render_markdown_byte_identical(tmp_path: Path) -> None:
        """PERS-06 + ROADMAP SC-4: data/loans.md and data/scenarios.md
        regenerate from DuckDB and are byte-identical across runs. Test:
        1. Pre-init DB and insert >=2 loans
        2. Run `db-write.mjs render-markdown` -> capture bytes_a
        3. Run again -> capture bytes_b
        4. Assert bytes_a == bytes_b for both files
        5. Assert the HTML <!-- Generated from ... --> comment appears at
           line 1 of each file (per PATTERNS load-bearing guard against
           hand-edits).
        Per RESEARCH Pitfall 3: SELECTs must include explicit ORDER BY id ASC;
        no generated_at timestamps embedded in markdown.
        """
        from tests.conftest import node_orchestration_run

        db_path = tmp_path / "test.duckdb"

        # CAVEAT (Warning #8 / D-04-07 / D-03-06 risk acceptance): this test is
        # NOT tmp_path-isolated for the rendered markdown files. Render-markdown
        # writes to data/loans.md + data/scenarios.md (paths baked into
        # orchestration/db-write.mjs as MORTGAGE_OPS / 'data' / ...; not
        # env-var-overridable in v1 per D-04-07). If a developer is mid-session
        # with a populated production DB and this test runs against the real
        # data/ directory, it will OVERWRITE live data/loans.md and
        # data/scenarios.md with the test fixtures' synthetic content. The risk
        # is accepted because (a) those files are gitignored generated artifacts
        # (Plan 09-02), (b) regenerating from the real DB is a single
        # `node orchestration/db-write.mjs render-markdown` away, and (c) the
        # try/finally cleanup unlinks both files at the end of the test, so a
        # subsequent production render starts from a known-empty state. The
        # alternative (env-var-overridable render paths) is deferred to a
        # future phase per D-04-07.
        #
        # We isolate the DB to tmp_path by overriding MORTGAGE_OPS_DB_PATH;
        # only the markdown output paths are not isolated.
        repo_root = Path(__file__).resolve().parent.parent.parent
        loans_md = repo_root / "data" / "loans.md"
        scenarios_md = repo_root / "data" / "scenarios.md"

        # Cleanup any leftovers from prior runs
        if loans_md.exists():
            loans_md.unlink()
        if scenarios_md.exists():
            scenarios_md.unlink()

        try:
            # 1. Init schema in tmp DB
            init = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
            assert init.returncode == 0, f"init failed: {init.stderr}"

            # 2. Insert 2 loans for non-trivial render
            for principal, rate, term, origination, loan_type in [
                ("200000.00", "0.065000", 360, "2026-05-01", "fixed"),
                ("350000.00", "0.070000", 180, "2026-05-15", "jumbo"),
            ]:
                fixture = tmp_path / f"loan_{principal}.json"
                fixture.write_text(json.dumps({
                    "principal": principal,
                    "annual_rate": rate,
                    "term_months": term,
                    "origination_date": origination,
                    "loan_type": loan_type,
                }))
                ins = node_orchestration_run(
                    "orchestration/db-write.mjs", "insert-loan", "--json", str(fixture),
                    db_path=db_path,
                )
                assert ins.returncode == 0, f"insert {principal} failed: {ins.stderr}"

            # 3. First render
            r1 = node_orchestration_run(
                "orchestration/db-write.mjs", "render-markdown", db_path=db_path,
            )
            assert r1.returncode == 0, f"render 1 failed: {r1.stderr}"
            assert loans_md.exists(), f"loans.md not created at {loans_md}"
            assert scenarios_md.exists(), f"scenarios.md not created"
            loans_bytes_a = loans_md.read_bytes()
            scenarios_bytes_a = scenarios_md.read_bytes()

            # 4. Second render against same DB state
            r2 = node_orchestration_run(
                "orchestration/db-write.mjs", "render-markdown", db_path=db_path,
            )
            assert r2.returncode == 0, f"render 2 failed: {r2.stderr}"
            loans_bytes_b = loans_md.read_bytes()
            scenarios_bytes_b = scenarios_md.read_bytes()

            # 5. Byte-identical assertion (the load-bearing contract)
            assert loans_bytes_a == loans_bytes_b, (
                f"loans.md drifted between runs (PERS-06 + SC-4 violation).\n"
                f"  Run 1 bytes: {len(loans_bytes_a)}\n"
                f"  Run 2 bytes: {len(loans_bytes_b)}\n"
                f"  Likely cause: missing ORDER BY id ASC OR generated_at "
                f"timestamp embedded in output (RESEARCH Pitfall 3)."
            )
            assert scenarios_bytes_a == scenarios_bytes_b, (
                "scenarios.md drifted between runs (PERS-06 + SC-4 violation)."
            )

            # 6. Mandatory header (PATTERNS Pattern Assignments load-bearing guard)
            loans_text = loans_md.read_text()
            scenarios_text = scenarios_md.read_text()
            generated_marker = "<!-- Generated from data/mortgage-ops.duckdb"
            assert loans_text.startswith(generated_marker), (
                f"loans.md missing 'Generated from' header at line 1; "
                f"first 80 chars: {loans_text[:80]!r}"
            )
            assert scenarios_text.startswith(generated_marker), (
                "scenarios.md missing 'Generated from' header at line 1"
            )

            # 7. Loans table contains expected money strings (DECIMAL string
            # discipline preserved through render layer)
            assert "200000.00" in loans_text
            assert "350000.00" in loans_text
            assert "0.065000" in loans_text
            assert "0.070000" in loans_text

        finally:
            # Cleanup generated artifacts (gitignored but tidy)
            if loans_md.exists():
                loans_md.unlink()
            if scenarios_md.exists():
                scenarios_md.unlink()
    ```

    The xfail decorator above the function MUST be removed.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_render_markdown.py -v --tb=short 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_orchestration/test_render_markdown.py -v 2>&1 | grep -c PASSED` returns 1
    - `pytest tests/test_orchestration/test_render_markdown.py -v 2>&1 | grep -c XFAIL` returns 0
    - `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_render_markdown.py` returns 0
    - `grep -c "import json" tests/test_orchestration/test_render_markdown.py` returns 1
    - `grep -c "byte_identical" tests/test_orchestration/test_render_markdown.py` returns at least 1 (function name)
    - After the test runs, `test ! -f data/loans.md` exits 0 (cleanup ran)
    - After the test runs, `test ! -f data/scenarios.md` exits 0 (cleanup ran)
  </acceptance_criteria>
  <done>
    test_render_markdown_byte_identical passes; PERS-06 closed; data/ directory clean after test.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero regression + lint</name>
  <files>(verification only)</files>
  <action>
    1. Full pytest suite: at least 442 + 1 = 443 passed; xfail count drops to 5.
    2. mypy --strict tests/test_orchestration/.
    3. ruff check + format on tests/test_orchestration/.
    4. Sanity: db-write.mjs render-markdown smoke test against fresh DB.
    5. Sanity: data/loans.md and data/scenarios.md NOT committed (gitignored per Plan 09-02).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest -q 2>&1 | tail -3 && mypy --strict tests/test_orchestration/ && ruff check tests/test_orchestration/ && ruff format --check tests/test_orchestration/ && git check-ignore data/loans.md data/scenarios.md && echo "gitignored"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows >= 443
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ xfailed'` shows 5
    - mypy + ruff + ruff format all exit 0
    - `git check-ignore data/loans.md` exits 0 (gitignored)
    - `git check-ignore data/scenarios.md` exits 0 (gitignored)
  </acceptance_criteria>
  <done>
    Suite green; PERS-06 closed; generated markdown files gitignored (Plan 09-02 inheritance).
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS:**

- **D-04-01: Mandatory `<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->` header** — rationale: PATTERNS Pattern Assignments line 303 calls this header "load-bearing"; ROADMAP SC-4 requires "no hand-edits possible"; the header is the user-facing signal that the file is generated. Rule-of-three citation: career-ops/scripts/db-write.mjs:610 + 638 use identical pattern; PATTERNS Pattern Assignments render-markdown section; CLAUDE.md skill convention "Do NOT edit by hand".

- **D-04-02: Every DECIMAL column in render SELECTs uses CAST AS VARCHAR** — rationale: inheritance from D-03-02; render is the human-facing surface where money values MUST display exact strings (e.g., "200000.00" not "200000" or "200000.001"). Rule-of-three citation: D-03-02 source (PATTERNS Critical Issue 2 + RESEARCH Pattern 3); test_decimal_string_round_trip_preserves_cents pins the contract; this plan extends to render layer.

- **D-04-03: Every render SELECT has explicit ORDER BY id ASC** — rationale: RESEARCH Pitfall 3 — without ORDER BY, DuckDB row order is non-deterministic; SC-4 byte-equality breaks. id is the synthetic primary key; ASC produces stable monotone order. Rule-of-three citation: RESEARCH Pitfall 3; career-ops db-write.mjs:601 uses ORDER BY in cmdRenderMarkdown; ROADMAP SC-4 explicit "byte-identical across runs".

- **D-04-04: NO generated_at = NOW() embedded in markdown body** — rationale: RESEARCH Pitfall 3 — embedding render-time timestamps breaks byte-equality. Career-ops gets this right (deliberately omits timestamp). scenarios.computed_at IS rendered, but it is data-captured-at-insert, not re-evaluated NOW(). Rule-of-three citation: RESEARCH Pitfall 3; career-ops db-write.mjs:610 has no timestamp; PATTERNS Pattern Assignments render-markdown line 303.

- **D-04-05: Render-markdown is in WRITE_COMMANDS (acquires lock)** — rationale: writes data/loans.md and data/scenarios.md to disk; treating it as a writer prevents concurrent renders from racing on file output. The DB SELECT itself is read-only but the file write is a mutation. Already in the WRITE_COMMANDS Set from Plan 09-03. Rule-of-three citation: career-ops db-write.mjs:668 includes render in WRITE_COMMANDS; Plan 09-03 D-03-01; RESEARCH §Pattern 2.

- **D-04-06: Default target is 'all' when no positional argument given** — rationale: matches `npm run render` mental model (regenerate everything); explicit `loans` or `scenarios` is for CI-style targeted invocations. Rule-of-three citation: career-ops cmdRenderMarkdown defaults to 'all' (db-write.mjs:592); RESEARCH §Code Examples §Example 3 shows full render; ergonomic for the human user.

- **D-04-07: data/loans.md + data/scenarios.md paths are NOT env-var-overridable in v1** — rationale: keeps render simple; tests run cleanup before/after rather than redirecting output. If a future Phase wants per-test render isolation, add MORTGAGE_OPS_RENDER_DIR env var then. Rule-of-three citation: simplicity precedent in career-ops (no override); v1 risk acceptance pattern from RESEARCH §Pitfall 2; testability is preserved via DB env-var override + cleanup.
</locked_decisions>

<verify_block>
**Verify Block:**

```bash
# 1. db-write.mjs syntax + render command
node --check orchestration/db-write.mjs
node orchestration/db-write.mjs --help | grep render-markdown

# 2. End-to-end smoke (init + insert + render twice + diff)
rm -f data/mortgage-ops.duckdb data/mortgage-ops.duckdb-wal data/mortgage-ops.duckdb-shm data/loans.md data/scenarios.md
node orchestration/init-db.mjs
cat > /tmp/loan_a.json <<EOF
{"principal":"200000.00","annual_rate":"0.065000","term_months":360,"origination_date":"2026-05-01","loan_type":"fixed"}
EOF
cat > /tmp/loan_b.json <<EOF
{"principal":"350000.00","annual_rate":"0.070000","term_months":180,"origination_date":"2026-05-15","loan_type":"jumbo"}
EOF
node orchestration/db-write.mjs insert-loan --json /tmp/loan_a.json
node orchestration/db-write.mjs insert-loan --json /tmp/loan_b.json
node orchestration/db-write.mjs render-markdown
cp data/loans.md /tmp/loans_run1.md
cp data/scenarios.md /tmp/scenarios_run1.md
node orchestration/db-write.mjs render-markdown
diff data/loans.md /tmp/loans_run1.md && echo "loans byte-identical"
diff data/scenarios.md /tmp/scenarios_run1.md && echo "scenarios byte-identical"
head -1 data/loans.md | grep -F "<!-- Generated from data/mortgage-ops.duckdb"
head -1 data/scenarios.md | grep -F "<!-- Generated from data/mortgage-ops.duckdb"

# 3. Cleanup
rm -f data/loans.md data/scenarios.md /tmp/loan_a.json /tmp/loan_b.json /tmp/loans_run1.md /tmp/scenarios_run1.md

# 4. test_render_markdown_byte_identical passes
pytest tests/test_orchestration/test_render_markdown.py -v --tb=short

# 5. Full suite green; xfail count drops to 5
pytest -q 2>&1 | tail -3

# 6. Lint hygiene
mypy --strict tests/test_orchestration/
ruff check tests/test_orchestration/
ruff format --check tests/test_orchestration/

# 7. Generated artifacts gitignored
git check-ignore data/loans.md data/scenarios.md && echo "gitignored OK"
```
</verify_block>

<deviation_rules>
**Deviation Rules:**

- **Rule-1 (header text is verbatim):** D-04-01 locks the exact header string `<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->`. If the executor finds career-ops uses an em-dash variant (— vs -), use the ASCII hyphen-minus (`-`) for portability and to avoid encoding ambiguity. The test asserts the prefix `<!-- Generated from data/mortgage-ops.duckdb`; the suffix may evolve.

- **Rule-2 (no derived/computed columns in render):** Render is a faithful view of stored DB state. If the executor sees an opportunity to compute a derived column inline (e.g., principal * annual_rate / 12), STOP. Derived columns belong in scenarios.response_json, not in the render layer. The render layer is "what's in the table".

- **Rule-3 (hygiene-only deviations OK):** ruff format on the Python test file may collapse multi-line expressions; apply minimal fix and document as Rule-3. node --check parse warnings can be ignored if `node --check` exits 0.
</deviation_rules>

<dependencies>
**Dependencies:**

- **Depends on:** Plan 09-00 (test_render_markdown.py xfail stub); Plan 09-01 (lockfile.mjs); Plan 09-02 (init-db.mjs schema; .gitignore for data/loans.md + data/scenarios.md); Plan 09-03 (db-write.mjs dispatcher + cmdRenderMarkdown placeholder slot + WRITE_COMMANDS Set already includes 'render-markdown').
- **Blocks:** None directly. Plan 09-05 (known-loans.yml) and Plan 09-06 (concurrency tests) and Plan 09-07 (references doc) are independent or downstream-only of this plan.
- **Inheritance:** D-03-02 (CAST AS VARCHAR); D-03-04 (transactional discipline — though render is read-only at the DB layer, file-write is the mutation withLock protects).
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| DB rows -> markdown body | DECIMAL columns may carry precision; CAST AS VARCHAR preserves losslessly |
| Two parallel renders -> data/loans.md | Mitigated by withLock (render-markdown is in WRITE_COMMANDS) |
| Render output -> human reader | Header signals "generated"; gitignore prevents accidental commit of stale view |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-18 | Tampering (markdown row order drifts between runs) | SELECT without ORDER BY | mitigate | Explicit ORDER BY id ASC in both SELECTs (D-04-03); test_render_markdown_byte_identical pins the contract |
| T-09-19 | Tampering (timestamp embedded in render output) | NOW() / generated_at in markdown | mitigate | D-04-04 forbids; test asserts byte-identical across runs |
| T-09-20 | Information Disclosure (DECIMAL precision lost in render) | CAST without VARCHAR | mitigate | D-04-02 mandates CAST AS VARCHAR; visible in markdown output (e.g., "200000.00" not "200000") |
| T-09-21 | Repudiation (hand-edit to data/loans.md silently overwritten) | Generated artifact | mitigate | Header comment warns; .gitignore prevents accidental commit |
</threat_model>

<verification>
- cmdRenderMarkdown shipped (replaces Wave 3 placeholder)
- Header `<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->` at line 1 of both files
- Two consecutive renders produce byte-identical output (PERS-06 + SC-4)
- All DECIMAL columns CAST AS VARCHAR; ORDER BY id ASC on every SELECT
- test_render_markdown_byte_identical passes; PERS-06 closed
- Full suite >= 443 passed; xfail count drops to 5
- mypy + ruff clean; data/loans.md + data/scenarios.md gitignored
</verification>

<success_criteria>
- PERS-06 closed (byte-identical regeneration verified by test)
- ROADMAP SC-4 satisfied (no hand-edits possible — file is regenerated from scratch)
- 4 of 5 db-write subcommands now complete (insert-loan, insert-scenario, insert-report, render-markdown, query)
- Wave 5 (known-loans.yml) and Wave 6 (concurrency tests) build on this foundation
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-04-SUMMARY.md` documenting:
- cmdRenderMarkdown line count + SELECT statement summary
- Byte-identical proof (manual smoke + automated test)
- Pass count delta (Wave 3 baseline 442 -> Wave 4 baseline 443; one xfail flipped)
- PERS-06 closure status
- Cumulative phase status: PERS-01, PERS-02, PERS-03 (insert paths), PERS-06 closed; PERS-04, PERS-05 (concurrency end-to-end), PERS-07 remain
</output>
