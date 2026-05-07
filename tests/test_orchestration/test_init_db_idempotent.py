"""Phase 9 init-db.mjs idempotency end-to-end test (PERS-02 + ROADMAP SC-1).

SC-1: `node orchestration/init-db.mjs` is idempotent. Running it twice
against the same DB file produces an identical schema (no DROP, no
duplicate CREATE error, no schema drift).

Test strategy: invoke init twice; SHA256-hash a deterministic dump of
pragma_table_info() for every table; assert the two hashes match.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from tests.conftest import node_orchestration_run

if TYPE_CHECKING:
    from pathlib import Path

# Tables defined by Plan 09-02 init-db.mjs (RESEARCH §"Pinned schema DDL").
# 6 mortgage tables + schema_version (Plan 09-02 ships all 7).
EXPECTED_TABLES: tuple[str, ...] = (
    "applicants",
    "loans",
    "payments",
    "properties",
    "reports",
    "scenarios",
    "schema_version",
)


def _schema_fingerprint(db_path: Path) -> str:
    """Compute a deterministic SHA256 of the full schema by querying
    pragma_table_info for every table and SHA256-hashing the JSON dump."""
    dump_parts: list[str] = []
    for table in EXPECTED_TABLES:
        result = node_orchestration_run(
            "orchestration/db-write.mjs",
            "query",
            "--sql",
            f'SELECT cid, name, type, "notnull", dflt_value, pk '
            f"FROM pragma_table_info('{table}') ORDER BY cid ASC",
            db_path=db_path,
        )
        assert result.returncode == 0, f"pragma_table_info({table}) failed: {result.stderr}"
        # The query subcommand emits JSON to stdout (per Plan 09-03).
        rows = json.loads(result.stdout)
        dump_parts.append(f"{table}:{json.dumps(rows, sort_keys=True)}")

    dump = "\n".join(dump_parts).encode("utf-8")
    return hashlib.sha256(dump).hexdigest()


def test_init_db_idempotent_across_runs(tmp_path: Path) -> None:
    """PERS-02 + ROADMAP SC-1: two consecutive invocations of
    `node orchestration/init-db.mjs` produce a byte-identical schema
    fingerprint. The CREATE TABLE IF NOT EXISTS pattern (RESEARCH §Pattern 1)
    is the load-bearing mechanism."""
    db_path = tmp_path / "test_idempotent.duckdb"

    # First init: builds the schema from scratch
    run1 = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert run1.returncode == 0, f"init run 1 failed: {run1.stderr}"
    assert db_path.exists(), f"DB file not created at {db_path}"

    fingerprint_1 = _schema_fingerprint(db_path)

    # Second init: must NOT drop or recreate; CREATE IF NOT EXISTS is no-op
    run2 = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert run2.returncode == 0, (
        f"init run 2 (idempotency) failed: {run2.stderr}\n"
        f"This is the SC-1 violation: init is NOT idempotent. Likely cause: "
        f"missing IF NOT EXISTS on a CREATE TABLE statement (RESEARCH Pattern 1)."
    )

    fingerprint_2 = _schema_fingerprint(db_path)

    assert fingerprint_1 == fingerprint_2, (
        f"PERS-02 + SC-1 violation: schema fingerprint drifted between "
        f"consecutive init runs.\n"
        f"  Run 1 SHA256: {fingerprint_1}\n"
        f"  Run 2 SHA256: {fingerprint_2}\n"
        f"Likely cause: a CREATE TABLE without IF NOT EXISTS, or an ALTER "
        f"that runs unconditionally."
    )


def test_init_db_creates_all_expected_tables(tmp_path: Path) -> None:
    """Companion guard: SC-1 idempotency is meaningless if init silently
    skips creating a required table. Verify all PERS-01 tables exist
    after a single init (6 mortgage tables + schema_version)."""
    db_path = tmp_path / "test_tables.duckdb"

    run1 = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
    assert run1.returncode == 0, f"init failed: {run1.stderr}"

    # Query for table existence via information_schema
    result = node_orchestration_run(
        "orchestration/db-write.mjs",
        "query",
        "--sql",
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name",
        db_path=db_path,
    )
    assert result.returncode == 0, f"information_schema query failed: {result.stderr}"
    rows = json.loads(result.stdout)
    actual_tables = {r["table_name"] for r in rows}

    missing = set(EXPECTED_TABLES) - actual_tables
    assert not missing, (
        f"PERS-01 violation: init-db.mjs failed to create tables: "
        f"{sorted(missing)}; have: {sorted(actual_tables)}"
    )
