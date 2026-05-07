---
phase: 09
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/test_orchestration/__init__.py
  - tests/test_orchestration/test_db_lifecycle.py
  - tests/test_orchestration/test_known_loans_smoke.py
  - tests/test_orchestration/test_lockfile.py
  - tests/test_orchestration/test_render_markdown.py
  - tests/conftest.py
autonomous: true
requirements:
  - PERS-01
  - PERS-02
  - PERS-03
  - PERS-04
  - PERS-05
  - PERS-06
  - PERS-07
tags:
  - phase-09
  - duckdb-orchestration
  - test-infrastructure
  - nyquist
must_haves:
  truths:
    - "tests/test_orchestration/ Python package exists and is collected by pytest"
    - "Every PERS-01..PERS-07 requirement has at least one xfail-decorated stub function with strict=True; PERS-03 specifically has three (insert-loan, insert-scenario, insert-report round-trips — revision 2026-05-04 per Blocker #2)"
    - "Stubbed files run (pytest tests/test_orchestration/ -v) without ImportError; xfail tests show as XFAIL not ERROR"
    - "tests/conftest.py exposes a node_orchestration_run pytest helper that shells out to `node` with cwd at repo root"
    - "Phase 9 test scaffold is additive: zero behavior change to Phase 1..5 production code or existing tests"
    - "All 9 xfail stubs use strict=True so a passing stub triggers XPASS at later wave flip time (revision 2026-05-04: count was 7 in Wave 0 v1; bumped to 9 per checker Blocker #2 — insert-scenario + insert-report stubs added)"
  artifacts:
    - path: "tests/test_orchestration/__init__.py"
      provides: "Empty package marker (parallels tests/test_reference/__init__.py)"
    - path: "tests/test_orchestration/test_db_lifecycle.py"
      provides: "7 xfail stubs covering PERS-01/02/03/05/06 (init idempotency, insert-loan round-trip, insert-scenario round-trip, insert-report round-trip, decimal cents round-trip, parallel writes, render byte-identical companion). Revision 2026-05-04: added insert-scenario + insert-report stubs per checker Blocker #2 — PERS-03 ships three insert subcommands; each gets its own stub."
      min_lines: 100
    - path: "tests/test_orchestration/test_lockfile.py"
      provides: "1 xfail stub covering PERS-04 (60s stale-lockfile recovery)"
    - path: "tests/test_orchestration/test_known_loans_smoke.py"
      provides: "1 xfail stub covering PERS-07 (>=7 product entries with required keys)"
    - path: "tests/test_orchestration/test_render_markdown.py"
      provides: "Companion stub for byte-identical markdown view regeneration (paired with PERS-06 SC-4)"
    - path: "tests/conftest.py"
      provides: "node_orchestration_run helper extending existing fixtures"
      contains: "def node_orchestration_run"
  key_links:
    - from: "tests/test_orchestration/*.py"
      to: "tests/conftest.py"
      via: "node_orchestration_run helper for subprocess shellout"
      pattern: "def test_.*\\(.*node_orchestration_run"
    - from: "Wave 1..6 plans"
      to: "tests/test_orchestration/ xfail decorators"
      via: "incremental flip from xfail -> pass as orchestration code lands"
      pattern: "@pytest.mark.xfail"
---

<objective>
**Goal:** Establish the Phase 9 test scaffolding that subsequent waves flip xfail->pass against. Ship the `node_orchestration_run` pytest helper, 7 xfail-decorated stub tests covering every PERS-01..PERS-07 requirement, the `tests/test_orchestration/` package marker, and the four test files that each later wave's verify-block will reference verbatim.

**Purpose:** Nyquist validation gate. Every requirement-closing wave (Plans 01..06) flips a specific xfail to a real assertion. Without Wave 0, downstream plans have no test landing pads — they would either ship code with no test or invent test names ad-hoc.

**Output:** Five new test files (1 package marker + 4 stub modules), one extended `tests/conftest.py` with a Node subprocess helper, zero orchestration code, zero fixture content. Suite remains green at the prior 432 + 4 baseline; new tests show 7 XFAIL.
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
@tests/conftest.py
@tests/test_reference/__init__.py

<interfaces>
<!-- Existing tests/conftest.py (lines 1-91) — Phase 9 EXTENDS, does not modify -->

Existing fixtures: golden_fixture, amortize_fixture, affordability_fixture, arm_fixture.
Pattern: each fixture returns a Callable[[str], dict[str, Any]] that loads JSON by stem.

Phase 9 introduces a NEW pattern: a subprocess helper for invoking Node.
- Helper is a module-level function (not a pytest fixture) imported by tests directly.
- Signature: `def node_orchestration_run(*args: str, db_path: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess`
- Sets `MORTGAGE_OPS_DB_PATH` env var when `db_path` is provided so init-db.mjs / db-write.mjs target a tmp DB.
- cwd is the repo root so `import.meta.url` resolution in the .mjs files works.

Phase 9 production files (Wave 1..6 will create):
- orchestration/lockfile.mjs (Wave 1)
- orchestration/init-db.mjs (Wave 2)
- orchestration/db-write.mjs (Waves 3, 4)
- data/known-loans.yml (Wave 5)
- references/data-layer.md (Wave 7)
</interfaces>

<test_inventory>
<!-- The 7 xfail stubs to be created — MUST contain all of these test names verbatim. -->
<!-- Source: REQUIREMENTS.md PERS-01..PERS-07 + ROADMAP.md Phase 9 success criteria SC-1..SC-5. -->

PERS-01 + PERS-02 (1 stub in test_db_lifecycle.py):
- test_init_db_idempotent

PERS-03 (3 stubs in test_db_lifecycle.py — insert-loan, insert-scenario, insert-report all flip in Wave 3):
- test_insert_loan_round_trip
- test_insert_scenario_round_trip
- test_insert_report_round_trip

PERS-05 (1 stub in test_db_lifecycle.py):
- test_concurrent_writes_serialize

PERS-04 (1 stub in test_lockfile.py):
- test_stale_lockfile_reclaimed_after_60s

PERS-06 (1 stub in test_render_markdown.py):
- test_render_markdown_byte_identical

PERS-07 (1 stub in test_known_loans_smoke.py):
- test_known_loans_catalog_complete

Cross-cutting (1 stub in test_db_lifecycle.py — DECIMAL round-trip discipline per PATTERNS Critical Issue 2):
- test_decimal_string_round_trip_preserves_cents

TOTAL: 9 xfail stubs (revision 2026-05-04: added test_insert_scenario_round_trip + test_insert_report_round_trip per checker Blocker #2 / Warning #7 — PERS-03 ships 3 insert subcommands in Plan 09-03; each must have its own round-trip stub flipped in Wave 3).
</test_inventory>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend tests/conftest.py with node_orchestration_run helper</name>
  <files>tests/conftest.py</files>
  <read_first>
    - tests/conftest.py (full file, 91 lines) — preserve all existing fixtures verbatim
    - 09-PATTERNS.md "tests/test_orchestration/test_db_lifecycle.py (subprocess-based pytest)" section — confirms `subprocess.run(["node", ...])` idiom mirrors tests/test_amortize.py:722-751
    - 09-RESEARCH.md "Test Designs" section — Pre-init/parallel-spawn/stale-lockfile patterns
  </read_first>
  <action>
    Append a module-level helper function (NOT a pytest fixture) plus the `subprocess` and `os` imports to tests/conftest.py. The helper is imported directly by Phase 9 tests via `from tests.conftest import node_orchestration_run`.

    Add to imports near the top (after the existing imports — preserve `from __future__`, `json`, `Path`, `TYPE_CHECKING`, `Any`, `pytest`):

    ```python
    import os
    import subprocess
    ```

    Append at end of file (after the existing arm_fixture function at line 91):

    ```python


    REPO_ROOT: Path = Path(__file__).resolve().parent.parent
    """Project root for cwd of Node subprocesses (parallel to FIXTURE_DIR)."""


    def node_orchestration_run(
        *args: str,
        db_path: Path | None = None,
        timeout: int = 30,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Shell out to `node` with cwd=REPO_ROOT and capture stdout/stderr as text.

        Mirrors tests/test_amortize.py subprocess.run idiom but for the Node
        orchestration scripts shipped in Phase 9. Each call is independent: no
        Database handle is shared; each Node process opens, transacts, closes.

        Args:
            *args: argv for the Node process, e.g. ("orchestration/init-db.mjs",)
                   or ("orchestration/db-write.mjs", "insert-loan", "--json", "fx.json").
            db_path: When provided, sets MORTGAGE_OPS_DB_PATH env var so the .mjs
                     scripts target a throwaway tmp DB. When None, scripts use the
                     default data/mortgage-ops.duckdb (Phase 9 init-db.mjs honors
                     this env-var override per Plan 09-02).
            timeout: subprocess timeout in seconds (default 30; parallel-write
                     test in Plan 09-06 overrides to 60).
            check: When True, raises CalledProcessError on non-zero exit. Default
                   False so tests can assert on the failure envelope themselves.

        Returns:
            subprocess.CompletedProcess with text=True (stdout / stderr as str).
        """
        env = os.environ.copy()
        if db_path is not None:
            env["MORTGAGE_OPS_DB_PATH"] = str(db_path)
        return subprocess.run(
            ["node", *args],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )
    ```

    Do NOT modify the existing golden_fixture, amortize_fixture, affordability_fixture, or arm_fixture functions. Add ONLY the new imports + REPO_ROOT constant + node_orchestration_run function.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python -c "from tests.conftest import node_orchestration_run, REPO_ROOT; print('OK', REPO_ROOT)"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def node_orchestration_run' tests/conftest.py` returns 1
    - `grep -c 'def golden_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'def amortize_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'def affordability_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'def arm_fixture' tests/conftest.py` returns 1 (existing — not removed)
    - `grep -c 'MORTGAGE_OPS_DB_PATH' tests/conftest.py` returns 1
    - `grep -c 'REPO_ROOT: Path' tests/conftest.py` returns 1
    - `pytest tests/test_amortize.py tests/test_affordability.py tests/test_arm.py -x --collect-only 2>&1 | tail -5` shows zero collection errors
  </acceptance_criteria>
  <done>
    node_orchestration_run is importable; existing fixtures unchanged; existing test collection still succeeds.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/test_orchestration/ package marker + 4 xfail stub modules</name>
  <files>tests/test_orchestration/__init__.py, tests/test_orchestration/test_db_lifecycle.py, tests/test_orchestration/test_lockfile.py, tests/test_orchestration/test_known_loans_smoke.py, tests/test_orchestration/test_render_markdown.py</files>
  <read_first>
    - tests/test_reference/__init__.py — confirm zero-byte marker convention
    - tests/test_amortize.py:1-60 — module header + SCRIPT_PATH constant pattern
    - tests/test_arm.py:1-60 — xfail(strict=True) pattern with reason citing the wave that flips it
    - 09-PATTERNS.md test_inventory section
  </read_first>
  <action>
    Create FIVE new files. Each test stub uses `@pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-NN ships ...")` and a body of `pytest.fail("Wave 0 stub")`. The strict flag means accidentally passing tests trigger XPASS, forcing the wave that fixes them to also remove the decorator.

    **File 1: tests/test_orchestration/__init__.py** (zero bytes — empty)
    Use the Write tool with `content=""` (an empty string).

    **File 2: tests/test_orchestration/test_db_lifecycle.py**

    ```python
    """Phase 9 DuckDB orchestration — DB lifecycle test surface (PERS-01/02/03/05/06).

    Per Phase 3 D-17 portability: subprocess invocation only via the
    node_orchestration_run helper from tests.conftest; never `import` the .mjs
    files (they are Node code). The helper sets MORTGAGE_OPS_DB_PATH so each
    test runs against a throwaway DB under tmp_path.

    Wave 0 (Plan 09-00) creates ALL stubs as xfail. Subsequent waves flip:
    - Wave 2 (Plan 09-02 init-db.mjs): test_init_db_idempotent
    - Wave 3 (Plan 09-03 db-write.mjs subcommands): test_insert_loan_round_trip,
      test_decimal_string_round_trip_preserves_cents
    - Wave 6 (Plan 09-06 concurrency tests): test_concurrent_writes_serialize
    - Wave 4 (Plan 09-04 render-markdown): paired with test_render_markdown.py

    Every xfail uses strict=True so accidental passes raise XPASS — the wave
    that flips it MUST also remove the decorator.
    """

    from __future__ import annotations

    from pathlib import Path

    import pytest

    REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    """Repo root for resolving orchestration/ paths in test bodies."""


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-02 ships orchestration/init-db.mjs")
    def test_init_db_idempotent(tmp_path: Path) -> None:
        """PERS-01 + PERS-02 + ROADMAP SC-1: running init-db.mjs twice on a fresh
        checkout produces the same schema with no errors. Verified by:
        1. node orchestration/init-db.mjs against tmp DB -> exit 0
        2. node orchestration/init-db.mjs again -> exit 0 (idempotent; no errors)
        3. Schema introspection: all 6 tables (loans, scenarios, reports,
           payments, applicants, properties) plus schema_version present.
        """
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-03 ships db-write.mjs --insert-loan")
    def test_insert_loan_round_trip(tmp_path: Path) -> None:
        """PERS-03 + ROADMAP SC-2 (write half): writing a loan via
        `db-write.mjs insert-loan --json fixtures/loan.json` succeeds, and a
        subsequent `db-write.mjs query --sql 'SELECT ... FROM loans'` returns
        the row. Money fields round-trip as exact strings (no precision loss).
        """
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-03 ships db-write.mjs --insert-scenario")
    def test_insert_scenario_round_trip(tmp_path: Path) -> None:
        """PERS-03 (insert-scenario surface area): writing a scenario via
        `db-write.mjs insert-scenario --kind <enum> --json fixtures/scen.json`
        succeeds, and a subsequent `db-write.mjs query --sql 'SELECT ... FROM
        scenarios'` returns the row. The request_json + response_json columns
        round-trip as JSON strings; the kind discriminator round-trips
        verbatim. Added in revision 2026-05-04 per checker Blocker #2 — PERS-03
        ships three insert subcommands; each requires its own round-trip stub.
        """
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-03 ships db-write.mjs --insert-report")
    def test_insert_report_round_trip(tmp_path: Path) -> None:
        """PERS-03 (insert-report surface area): writing a report via
        `db-write.mjs insert-report --scenario-id <int> --file fixtures/r.md`
        succeeds, and a subsequent `db-write.mjs query --sql 'SELECT
        markdown_blob FROM reports'` returns the file content byte-exactly.
        The scenario_id foreign-key reference is preserved. Added in revision
        2026-05-04 per checker Blocker #2 — PERS-03 ships three insert
        subcommands; each requires its own round-trip stub.
        """
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-03 enforces CAST AS VARCHAR discipline")
    def test_decimal_string_round_trip_preserves_cents(tmp_path: Path) -> None:
        """PATTERNS Critical Issue 2 + RESEARCH Pitfall 1 + CLAUDE.md money
        discipline: insert principal='200000.01', SELECT CAST(principal AS
        VARCHAR), assert returned string equals '200000.01' exactly.
        Guards against the duckdb-async DECIMAL->bigint coercion bug.
        """
        pytest.fail("Wave 0 stub")


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-06 ships parallel-invocation test")
    def test_concurrent_writes_serialize(tmp_path: Path) -> None:
        """PERS-05 + ROADMAP SC-2 (concurrency half): two parallel
        `db-write.mjs --insert-loan` processes either both succeed (lock waiter
        path) or one fails fast with a lock-timeout error. Final loan count
        equals baseline + 2 (atomicity preserved; no corruption).
        """
        pytest.fail("Wave 0 stub")
    ```

    **File 3: tests/test_orchestration/test_lockfile.py**

    ```python
    """Phase 9 DuckDB orchestration — lockfile semantics (PERS-04).

    Wave 1 (Plan 09-01) ships orchestration/lockfile.mjs with 60s stale
    recovery. Wave 6 (Plan 09-06) flips this stub to a real fixture-based
    assertion that pre-creates a synthetic stale lock and verifies reclaim.
    """

    from __future__ import annotations

    from pathlib import Path

    import pytest


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-06 ships stale-lockfile-recovery test")
    def test_stale_lockfile_reclaimed_after_60s(tmp_path: Path) -> None:
        """PERS-04 + ROADMAP SC-3: a pre-existing lockfile with acquired_at
        more than 60s ago is reclaimed by a fresh writer. Test pre-creates
        data/.lock with acquired_at=Date.now()-65000, then invokes
        `db-write.mjs insert-loan` and asserts:
        1. exit code 0 (write succeeded; stale lock was reclaimed)
        2. lockfile released after the write completes (no leak)
        Per PATTERNS Critical Issue 1: stale check is acquired_at-based, NOT
        mtime-based; test still sets mtime as belt-and-suspenders.
        """
        pytest.fail("Wave 0 stub")
    ```

    **File 4: tests/test_orchestration/test_known_loans_smoke.py**

    ```python
    """Phase 9 known-loans.yml smoke test (PERS-07).

    Wave 5 (Plan 09-05) ships data/known-loans.yml with at least 7 product
    entries; this stub flips to verify catalog completeness + Reference Layer
    discipline (source: URL + effective: ISO date) per REF-09 inheritance.
    """

    from __future__ import annotations

    from pathlib import Path

    import pytest

    KNOWN_LOANS_PATH: Path = (
        Path(__file__).resolve().parent.parent.parent / "data" / "known-loans.yml"
    )
    """Reference Layer file per DATA_CONTRACT.md line 67 (committed; manually refreshed)."""


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-05 ships data/known-loans.yml")
    def test_known_loans_catalog_complete() -> None:
        """PERS-07 + ROADMAP SC-5: data/known-loans.yml contains at least 7
        product entries (30yr fixed conv, 15yr fixed conv, ARM 5/1, ARM 7/1,
        FHA 30yr, VA 30yr, jumbo 30yr) AND has top-level `source:` URL plus
        `effective:` date per Reference Layer discipline (REF-09 inheritance).
        Each product's `loan_type` value MUST be one of the lib.models.Loan
        Literal options ('fixed', 'arm', 'fha', 'va', 'usda', 'jumbo').
        """
        pytest.fail("Wave 0 stub")
    ```

    **File 5: tests/test_orchestration/test_render_markdown.py**

    ```python
    """Phase 9 markdown view regeneration (PERS-06 + ROADMAP SC-4).

    Wave 4 (Plan 09-04) ships orchestration/db-write.mjs --render-markdown.
    The byte-identical guarantee is the load-bearing contract: two
    consecutive renders against the same DB state produce IDENTICAL bytes.
    """

    from __future__ import annotations

    from pathlib import Path

    import pytest


    @pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-04 ships db-write.mjs --render-markdown")
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
        pytest.fail("Wave 0 stub")
    ```

    All five files use `from __future__ import annotations` for forward refs and `pytest.fail("Wave 0 stub")` bodies. No imports of `lib.*` (Phase 9 is orchestration only). No imports of tests.conftest.node_orchestration_run yet — that wiring lands in Wave 6 when stubs flip.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/ -v --tb=no 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_orchestration/__init__.py` exits 0 (file exists, zero bytes)
    - `wc -c tests/test_orchestration/__init__.py` returns 0
    - `test -f tests/test_orchestration/test_db_lifecycle.py` exits 0
    - `test -f tests/test_orchestration/test_lockfile.py` exits 0
    - `test -f tests/test_orchestration/test_known_loans_smoke.py` exits 0
    - `test -f tests/test_orchestration/test_render_markdown.py` exits 0
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_orchestration/test_db_lifecycle.py` returns 6 (revision 2026-05-04: was 4 in Wave 0 v1; added insert-scenario + insert-report stubs per Blocker #2)
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_orchestration/test_lockfile.py` returns 1
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_orchestration/test_known_loans_smoke.py` returns 1
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_orchestration/test_render_markdown.py` returns 1
    - `grep -c 'def test_init_db_idempotent' tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c 'def test_insert_loan_round_trip' tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c 'def test_insert_scenario_round_trip' tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c 'def test_insert_report_round_trip' tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c 'def test_concurrent_writes_serialize' tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c 'def test_decimal_string_round_trip_preserves_cents' tests/test_orchestration/test_db_lifecycle.py` returns 1
    - `grep -c 'def test_stale_lockfile_reclaimed_after_60s' tests/test_orchestration/test_lockfile.py` returns 1
    - `grep -c 'def test_known_loans_catalog_complete' tests/test_orchestration/test_known_loans_smoke.py` returns 1
    - `grep -c 'def test_render_markdown_byte_identical' tests/test_orchestration/test_render_markdown.py` returns 1
    - `pytest tests/test_orchestration/ --collect-only -q 2>&1 | grep -c 'test_'` returns at least 9 (revision 2026-05-04: was 7 in Wave 0 v1)
    - `pytest tests/test_orchestration/ -v --tb=no 2>&1 | grep -c XFAIL` returns 9 (revision 2026-05-04: was 7 in Wave 0 v1)
    - `pytest tests/test_orchestration/ -v --tb=no 2>&1 | grep -E '(FAILED|ERROR)' | wc -l` returns 0
  </acceptance_criteria>
  <done>
    Five files exist; pytest collects 9 tests; all 9 report XFAIL (zero pass, zero fail, zero error). Revision 2026-05-04: was 7 in v1.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero regression to Phase 5 baseline + lint hygiene</name>
  <files>(verification only — no file writes)</files>
  <read_first>
    - .planning/STATE.md "Final test suite: 432 passed + 4 skipped + 1 xfailed" — Phase 5 baseline
  </read_first>
  <action>
    Run the full pytest suite and confirm:
    1. Phase 5 baseline preserved: at least 432 passed + at least 4 skipped (Phase 5 final state per STATE.md)
    2. Phase 9 new stubs add 9 xfails (so total xfailed >= 1 + 9 = 10; Phase 5's lone xfailed test from Plan 05-06 is preserved). Revision 2026-05-04: count was 7 in Wave 0 v1; bumped to 9 per checker Blocker #2 (insert-scenario + insert-report stubs).
    3. Zero failures, zero errors, zero unexpected XPASS

    Run: `pytest -q 2>&1 | tail -5`

    If any pre-existing test fails OR any unexpected error appears, STOP and investigate. Do NOT proceed.

    After verification passes, run mypy + ruff hygiene on the four touched files:
    - `mypy --strict tests/conftest.py tests/test_orchestration/`
    - `ruff check tests/conftest.py tests/test_orchestration/`
    - `ruff format --check tests/conftest.py tests/test_orchestration/`

    All three MUST be clean (zero issues, zero diffs).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest -q 2>&1 | tail -5 && mypy --strict tests/conftest.py tests/test_orchestration/ && ruff check tests/conftest.py tests/test_orchestration/ && ruff format --check tests/conftest.py tests/test_orchestration/</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -5 | grep -oE '[0-9]+ passed'` shows >= 432 passed
    - `pytest -q 2>&1 | tail -5 | grep -oE '[0-9]+ xfailed'` shows >= 10 xfailed (1 prior + 9 new — revision 2026-05-04: 7 -> 9 stubs per Blocker #2)
    - `pytest -q 2>&1 | tail -5 | grep -E '[0-9]+ failed' | wc -l` returns 0 (no "N failed" line)
    - `pytest -q 2>&1 | tail -5 | grep -E '[0-9]+ error' | wc -l` returns 0 (no "N errors" line)
    - `mypy --strict tests/conftest.py tests/test_orchestration/` exits 0 with "Success: no issues found"
    - `ruff check tests/conftest.py tests/test_orchestration/` exits 0 with "All checks passed"
    - `ruff format --check tests/conftest.py tests/test_orchestration/` exits 0
  </acceptance_criteria>
  <done>
    Full suite passes with zero regressions; new tests show 7 XFAIL; mypy + ruff clean.
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS (Wave 0 scope only — broader phase-level decisions live in subsequent plan frontmatter):**

- **D-00-01: Test package lives at tests/test_orchestration/ (NOT tests/test_phase09_*.py)** — rationale: mirrors tests/test_reference/ + tests/test_rules/ (the only existing test sub-packages); short, durable name that survives if Phase 10/11 add more orchestration scripts. Rule-of-three citation: tests/test_reference/__init__.py exists; tests/test_rules/__init__.py exists; tests/test_orchestration/__init__.py is the third instance of this convention.
- **D-00-02: node_orchestration_run is a module-level helper, NOT a pytest fixture** — rationale: each Phase 9 test calls it 1..N times with varying argv; fixture-injection adds zero value over `from tests.conftest import node_orchestration_run`. Rule-of-three citation: subprocess.run is invoked directly in tests/test_amortize.py:722-751 + tests/test_affordability.py CLI tests + tests/test_arm.py CLI tests — none use a fixture wrapper, all use direct subprocess.run.
- **D-00-03: All 7 stubs use @pytest.mark.xfail(strict=True)** — rationale: an accidental pass during stub state raises XPASS; the wave that flips the test MUST also remove the decorator (per Phase 5 LM precedent). Rule-of-three citation: tests/test_arm.py uses strict=True on 32 stubs (Plan 05-00); tests/test_affordability.py used strict=True on 9 stubs (Plan 04-00); this plan adds 9 more (revision 2026-05-04: was 7 in v1; added 2 per Blocker #2).
- **D-00-04: MORTGAGE_OPS_DB_PATH env-var override is the seam between prod DB and tmp DB** — rationale: tests need throwaway DBs under tmp_path; init-db.mjs and db-write.mjs (Waves 2/3) MUST honor this env var. Rule-of-three citation: career-ops db-write.mjs DB_PATH constant is module-level (sole consumer is Node); mortgage-ops adds the env-var seam (second consumer = pytest); Phase 10 skill may become the third consumer for `.claude/skills/.../scripts/` relocation. The env-var contract is locked here so Wave 2 implements it.
</locked_decisions>

<verify_block>
**Verify Block (the exact bash commands the executor runs to confirm the plan landed):**

```bash
# 1. Helper is importable
cd /Users/cujo253/Documents/mortgage-ops && python -c "from tests.conftest import node_orchestration_run, REPO_ROOT; print('OK', REPO_ROOT)"

# 2. Package marker exists, zero bytes
test -f tests/test_orchestration/__init__.py && [ "$(wc -c < tests/test_orchestration/__init__.py)" -eq 0 ] && echo "marker OK"

# 3. All 7 xfail stubs collected
pytest tests/test_orchestration/ --collect-only -q 2>&1 | tail -3

# 4. All 7 report XFAIL (no pass, no fail, no error)
pytest tests/test_orchestration/ -v --tb=no 2>&1 | grep -E "XFAIL|FAILED|ERROR|PASSED" | sort | uniq -c

# 5. Phase 5 baseline preserved (>=432 passed; >=10 xfailed — revision 2026-05-04: was 8 in Wave 0 v1)
pytest -q 2>&1 | tail -5

# 6. Lint hygiene clean
mypy --strict tests/conftest.py tests/test_orchestration/
ruff check tests/conftest.py tests/test_orchestration/
ruff format --check tests/conftest.py tests/test_orchestration/

# 7. Required test names present (one grep per name)
for name in test_init_db_idempotent test_insert_loan_round_trip test_insert_scenario_round_trip test_insert_report_round_trip test_concurrent_writes_serialize test_decimal_string_round_trip_preserves_cents test_stale_lockfile_reclaimed_after_60s test_known_loans_catalog_complete test_render_markdown_byte_identical; do
  count=$(grep -rc "def $name" tests/test_orchestration/ | grep -v ':0$' | wc -l)
  [ "$count" -eq 1 ] && echo "$name: OK" || echo "$name: MISSING"
done
```
</verify_block>

<deviation_rules>
**Deviation Rules** (the standard mortgage-ops Rule-1/Rule-2/Rule-3 framing):

- **Rule-1 (test contract is source of truth):** If the executor finds that a stub name does not match the rule that produced it (e.g., test_init_db_idempotent looks wrong because PERS-02 says "schema bootstrapper"), STOP. Surface as a blocker comment in the task action; do NOT silently rename. The 9 stub names (revision 2026-05-04: was 7 in Wave 0 v1; added insert-scenario + insert-report per Blocker #2) are pinned by REQUIREMENTS.md PERS-01..PERS-07 and ROADMAP SC-1..SC-5; a rename is a CONTEXT-level decision, not an executor-level decision.

- **Rule-2 (preserve existing fixtures):** Phase 9 EXTENDS tests/conftest.py; it does NOT modify the existing golden_fixture, amortize_fixture, affordability_fixture, or arm_fixture. If the executor finds an existing fixture that needs adjustment, STOP and surface as a blocker. Preserving the Phase 1..5 contract is non-negotiable.

- **Rule-3 (hygiene-only deviations are OK):** If mypy --strict surfaces a type-import diff (e.g., `subprocess.CompletedProcess[str]` requires a `from typing import` adjustment) the executor may apply the minimal fix and document it in SUMMARY.md as a Rule-3 deviation. Likewise for ruff format auto-collapse of multi-line expressions. These are hygiene-only and do not affect the test contract.
</deviation_rules>

<dependencies>
**Dependencies (which other waves block this one):**

- **Blocks no waves on entry** (Wave 0 is first; depends on nothing within Phase 9).
- **Depends on Phase 5 completion** (STATE.md reports phase-complete; baseline 432 passed + 4 skipped + 1 xfailed). Phase 9 entry test count assertion uses these as the floor.
- **Blocks all subsequent Phase 9 waves:** Wave 1 (lockfile), Wave 2 (init-db), Wave 3 (db-write subcommands), Wave 4 (render-markdown), Wave 5 (known-loans.yml), Wave 6 (concurrency tests), Wave 7 (references doc) — every later plan's verify-block references one or more of the 7 xfail stubs created here.
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Wave 0 -> Wave 1..6 | Test stubs define the contract that orchestration code must satisfy; mismatch silently leaves a requirement unverified |
| pytest collection -> CI signal | XFAIL must be the outcome state; PASS or FAIL or ERROR all leak signal noise |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-01 | Tampering (test contract drift) | tests/test_orchestration/*.py stub names | mitigate | All 7 stub names are LISTED VERBATIM in test_inventory; acceptance_criteria grep each one to confirm presence |
| T-09-02 | Information Disclosure (false-pass via skipped xfail) | xfail decorators | mitigate | Every xfail uses strict=True -> accidental pass triggers XPASS failure. Wave 1..6 plans MUST remove the decorator when flipping the test |
| T-09-03 | Denial of Service (test-suite slowdown) | new 7 stubs | accept | All stubs are zero-cost pytest.fail("Wave 0 stub"); total runtime impact < 0.1s |
| T-09-04 | Repudiation (silent regression to Phase 5 baseline) | conftest.py extension | mitigate | Task 3 acceptance asserts >=432 passed; mypy + ruff clean |
</threat_model>

<verification>
- All 7 expected stub names present in tests/test_orchestration/ (one grep per name)
- Full pytest suite: >=432 passed + >=8 xfailed + 0 failed + 0 errored
- mypy --strict + ruff clean across conftest.py + test_orchestration/
- node_orchestration_run importable; existing fixtures unchanged
- tests/test_orchestration/__init__.py exists at zero bytes (package marker)
</verification>

<success_criteria>
- 5 new test files exist (1 marker + 4 stub modules); tests/conftest.py extended with helper
- pytest collects 9 new tests; all 9 report XFAIL on first run (revision 2026-05-04: was 7)
- Phase 5 baseline preserved (>=432 passed + >=4 skipped)
- mypy --strict + ruff format clean across all touched files
- Wave 1..6 have a clear contract: each downstream plan flips a known xfail name and removes its decorator
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-00-SUMMARY.md` documenting:
- Number of xfail stubs created (must be 9 — revision 2026-05-04: bumped from 7 per Blocker #2)
- Phase 5 baseline pass count after Wave 0 (must be >= 432)
- mypy + ruff status (must be clean)
- Mapping table: each xfail stub -> wave-and-plan responsible for flipping it
</output>
</content>
</invoke>