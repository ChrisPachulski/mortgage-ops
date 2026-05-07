"""Phase 9 DuckDB orchestration — DB lifecycle test surface (PERS-01/02/03/05/06).

Per Phase 3 D-17 portability: subprocess invocation only via the
node_orchestration_run helper from tests.conftest; never `import` the .mjs
files (they are Node code). The helper sets MORTGAGE_OPS_DB_PATH so each
test runs against a throwaway DB under tmp_path.

Wave 0 (Plan 09-00) creates ALL stubs as xfail. Subsequent waves flip:
- Wave 2 (Plan 09-02 init-db.mjs): test_init_db_idempotent
- Wave 3 (Plan 09-03 db-write.mjs subcommands): test_insert_loan_round_trip,
  test_insert_scenario_round_trip, test_insert_report_round_trip,
  test_decimal_string_round_trip_preserves_cents
- Wave 6 (Plan 09-06 concurrency tests): test_concurrent_writes_serialize
- Wave 4 (Plan 09-04 render-markdown): paired with test_render_markdown.py

Every xfail uses strict=True so accidental passes raise XPASS — the wave
that flips it MUST also remove the decorator.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    fixture.write_text(
        json.dumps(
            {
                "principal": "200000.00",
                "annual_rate": "0.065000",
                "term_months": 360,
                "origination_date": "2026-05-01",
                "loan_type": "fixed",
                "frequency": "monthly",
            }
        )
    )

    # Insert
    insert_result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "insert-loan",
        "--json",
        str(fixture),
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
        "orchestration/db-write.mjs",
        "query",
        "--sql",
        query_sql,
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


def test_insert_scenario_round_trip(tmp_path: Path) -> None:
    """PERS-03 (insert-scenario surface area): writing a scenario via
    `db-write.mjs insert-scenario --kind <enum> --json fixtures/scen.json`
    succeeds, and a subsequent `db-write.mjs query --sql 'SELECT ... FROM
    scenarios'` returns the row. The request_json + response_json columns
    round-trip as JSON strings; the kind discriminator round-trips
    verbatim. Added in revision 2026-05-04 per checker Blocker #2 — PERS-03
    ships three insert subcommands; each requires its own round-trip stub.
    """
    from tests.conftest import node_orchestration_run

    db_path = tmp_path / "test.duckdb"
    # Bootstrap schema + parent loan (scenarios.loan_id is nullable but the
    # test exercises the populated path).
    init_result = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert init_result.returncode == 0, f"init failed: {init_result.stderr}"

    loan_fixture = tmp_path / "loan.json"
    loan_fixture.write_text(
        json.dumps(
            {
                "principal": "200000.00",
                "annual_rate": "0.065000",
                "term_months": 360,
                "loan_type": "fixed",
            }
        )
    )
    loan_result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "insert-loan",
        "--json",
        str(loan_fixture),
        db_path=db_path,
    )
    assert loan_result.returncode == 0, f"loan insert failed: {loan_result.stderr}"

    # Scenario fixture
    scenario_fixture = tmp_path / "scenario.json"
    scenario_fixture.write_text(
        json.dumps(
            {
                "request": {"loan_id": 1, "amortize_options": {"rounding": "half_up"}},
                "response": {"monthly_pi": "1264.14", "schedule_rows": 360},
                "notes": "test fixture",
            }
        )
    )

    scen_result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "insert-scenario",
        "--loan-id",
        "1",
        "--kind",
        "amortize",
        "--json",
        str(scenario_fixture),
        db_path=db_path,
    )
    assert scen_result.returncode == 0, f"scenario insert failed: {scen_result.stderr}"
    scen_payload = json.loads(scen_result.stdout.strip())
    assert scen_payload["ok"] is True
    assert scen_payload["scenario_id"] == 1
    assert scen_payload["kind"] == "amortize"
    assert scen_payload["loan_id"] == 1

    # Round-trip: query back the row, parse request_json + response_json columns
    scen_query = node_orchestration_run(
        "orchestration/db-write.mjs",
        "query",
        "--sql",
        "SELECT id, loan_id, kind, request_json, response_json, notes "
        "FROM scenarios ORDER BY id ASC",
        db_path=db_path,
    )
    assert scen_query.returncode == 0, f"scenario query failed: {scen_query.stderr}"
    rows = json.loads(scen_query.stdout.strip())
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "amortize"
    assert row["loan_id"] == 1
    # request_json + response_json may come back as either JSON-string or
    # already-parsed dict depending on duckdb-async JSON-column handling.
    # Normalize before comparing.
    req = (
        json.loads(row["request_json"])
        if isinstance(row["request_json"], str)
        else row["request_json"]
    )
    resp = (
        json.loads(row["response_json"])
        if isinstance(row["response_json"], str)
        else row["response_json"]
    )
    assert req["loan_id"] == 1
    assert req["amortize_options"]["rounding"] == "half_up"
    assert resp["monthly_pi"] == "1264.14"
    assert resp["schedule_rows"] == 360
    assert row["notes"] == "test fixture"


def test_insert_report_round_trip(tmp_path: Path) -> None:
    """PERS-03 (insert-report surface area): writing a report via
    `db-write.mjs insert-report --scenario-id <int> --file fixtures/r.md`
    succeeds, and a subsequent `db-write.mjs query --sql 'SELECT
    markdown_blob FROM reports'` returns the file content byte-exactly.
    The scenario_id foreign-key reference is preserved. Added in revision
    2026-05-04 per checker Blocker #2 — PERS-03 ships three insert
    subcommands; each requires its own round-trip stub.
    """
    from tests.conftest import node_orchestration_run

    db_path = tmp_path / "test.duckdb"
    # Bootstrap schema + parent loan + parent scenario
    init_result = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert init_result.returncode == 0, f"init failed: {init_result.stderr}"

    loan_fixture = tmp_path / "loan.json"
    loan_fixture.write_text(
        json.dumps(
            {
                "principal": "200000.00",
                "annual_rate": "0.065000",
                "term_months": 360,
                "loan_type": "fixed",
            }
        )
    )
    loan_result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "insert-loan",
        "--json",
        str(loan_fixture),
        db_path=db_path,
    )
    assert loan_result.returncode == 0, f"loan insert failed: {loan_result.stderr}"

    scenario_fixture = tmp_path / "scenario.json"
    scenario_fixture.write_text(
        json.dumps(
            {
                "request": {"loan_id": 1},
                "response": {"monthly_pi": "1264.14"},
            }
        )
    )
    scen_result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "insert-scenario",
        "--loan-id",
        "1",
        "--kind",
        "amortize",
        "--json",
        str(scenario_fixture),
        db_path=db_path,
    )
    assert scen_result.returncode == 0, f"scenario insert failed: {scen_result.stderr}"

    # Report body — byte-identical contract
    report_md = tmp_path / "report.md"
    report_body = "# Loan Report\n\nMonthly P&I: $1,264.14\nTotal interest: $255,089.36\n"
    report_md.write_text(report_body)

    rep_result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "insert-report",
        "--scenario-id",
        "1",
        "--file",
        str(report_md),
        db_path=db_path,
    )
    assert rep_result.returncode == 0, f"report insert failed: {rep_result.stderr}"
    rep_payload = json.loads(rep_result.stdout.strip())
    assert rep_payload["ok"] is True
    assert rep_payload["report_id"] == 1
    assert rep_payload["scenario_id"] == 1
    assert rep_payload["bytes"] == len(report_body)

    # Round-trip: query back markdown_blob and assert byte-identical
    rep_query = node_orchestration_run(
        "orchestration/db-write.mjs",
        "query",
        "--sql",
        "SELECT id, scenario_id, markdown_blob FROM reports ORDER BY id ASC",
        db_path=db_path,
    )
    assert rep_query.returncode == 0, f"report query failed: {rep_query.stderr}"
    rep_rows = json.loads(rep_query.stdout.strip())
    assert len(rep_rows) == 1
    rep_row = rep_rows[0]
    assert rep_row["scenario_id"] == 1
    assert rep_row["markdown_blob"] == report_body, (
        f"insert-report round-trip lost bytes: "
        f"sent {len(report_body)} got {len(rep_row['markdown_blob'])}"
    )


def test_decimal_string_round_trip_preserves_cents(tmp_path: Path) -> None:
    """PATTERNS Critical Issue 2 + RESEARCH Pitfall 1 + CLAUDE.md money
    discipline: insert principal='200000.01', SELECT CAST(principal AS
    VARCHAR), assert returned string equals '200000.01' exactly.
    Guards against the duckdb-async DECIMAL->bigint coercion bug.
    """
    from tests.conftest import node_orchestration_run

    db_path = tmp_path / "test.duckdb"
    init_result = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert init_result.returncode == 0, f"init failed: {init_result.stderr}"

    # Test multiple boundary values: cent precision, max, mid-range, min positive
    test_cases = [
        "200000.01",  # Cent precision (the load-bearing case)
        "0.01",  # Smallest positive money
        "99999999.99",  # Large value where bigint coercion would risk loss
        "1234567.89",  # Random mid-range
    ]
    for principal_str in test_cases:
        fixture = tmp_path / f"loan_{principal_str}.json"
        fixture.write_text(
            json.dumps(
                {
                    "principal": principal_str,
                    "annual_rate": "0.060000",
                    "term_months": 360,
                    "loan_type": "fixed",
                }
            )
        )
        insert_result = node_orchestration_run(
            "orchestration/db-write.mjs",
            "insert-loan",
            "--json",
            str(fixture),
            db_path=db_path,
        )
        assert insert_result.returncode == 0, (
            f"insert {principal_str} failed: {insert_result.stderr}"
        )

    # Query all back; assert each round-trips byte-exact
    query_result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "query",
        "--sql",
        "SELECT CAST(principal AS VARCHAR) AS principal FROM loans ORDER BY id ASC",
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


def test_concurrent_writes_serialize(tmp_path: Path) -> None:
    """PERS-05 + ROADMAP SC-2: parallel writers serialize via lockfile.
    This is the Wave 0 stub flipped by Plan 09-06; the full implementation
    lives in tests/test_orchestration/test_parallel_invocation.py
    (test_parallel_inserts_serialize_via_lockfile)."""
    from tests.test_orchestration.test_parallel_invocation import (
        test_parallel_inserts_serialize_via_lockfile,
    )

    test_parallel_inserts_serialize_via_lockfile(tmp_path)
