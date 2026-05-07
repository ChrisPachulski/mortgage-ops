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


def test_init_db_idempotent(tmp_path: Path) -> None:
    """PERS-01 + PERS-02 + ROADMAP SC-1: running init-db.mjs twice on a fresh
    checkout produces the same schema with no errors. Verified by:
    1. node orchestration/init-db.mjs against tmp DB -> exit 0
    2. node orchestration/init-db.mjs again -> exit 0 (idempotent; no errors)
    3. Schema introspection: all 6 tables (loans, scenarios, reports,
       payments, applicants, properties) plus schema_version present.
    """
    import json as _json
    import os
    import subprocess

    from tests.conftest import node_orchestration_run

    db_path = tmp_path / "test.duckdb"

    # First run: creates schema
    result_a = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert result_a.returncode == 0, f"first run failed: stderr={result_a.stderr}"
    assert db_path.exists(), f"DB file not created at {db_path}"

    # Second run: idempotent
    result_b = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert result_b.returncode == 0, (
        f"second run failed (idempotency violation): stderr={result_b.stderr}"
    )

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
    env = os.environ.copy()
    env["MORTGAGE_OPS_DB_PATH"] = str(db_path)
    introspect = subprocess.run(
        ["node", "--input-type=module", "-e", introspect_script],
        cwd=str(Path(__file__).resolve().parent.parent.parent),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert introspect.returncode == 0, f"introspect failed: stderr={introspect.stderr}"
    tables = set(_json.loads(introspect.stdout.strip()))
    expected = {
        "schema_version",
        "loans",
        "scenarios",
        "reports",
        "payments",
        "applicants",
        "properties",
    }
    assert expected.issubset(tables), f"missing tables: {expected - tables}; got {tables}"


@pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-03 ships db-write.mjs --insert-loan")
def test_insert_loan_round_trip(tmp_path: Path) -> None:
    """PERS-03 + ROADMAP SC-2 (write half): writing a loan via
    `db-write.mjs insert-loan --json fixtures/loan.json` succeeds, and a
    subsequent `db-write.mjs query --sql 'SELECT ... FROM loans'` returns
    the row. Money fields round-trip as exact strings (no precision loss).
    """
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub - Plan 09-03 ships db-write.mjs --insert-scenario"
)
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


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub - Plan 09-03 ships db-write.mjs --insert-report"
)
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


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub - Plan 09-03 enforces CAST AS VARCHAR discipline"
)
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
