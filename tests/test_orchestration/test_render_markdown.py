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
            fixture.write_text(
                json.dumps(
                    {
                        "principal": principal,
                        "annual_rate": rate,
                        "term_months": term,
                        "origination_date": origination,
                        "loan_type": loan_type,
                    }
                )
            )
            ins = node_orchestration_run(
                "orchestration/db-write.mjs",
                "insert-loan",
                "--json",
                str(fixture),
                db_path=db_path,
            )
            assert ins.returncode == 0, f"insert {principal} failed: {ins.stderr}"

        # 3. First render
        r1 = node_orchestration_run(
            "orchestration/db-write.mjs",
            "render-markdown",
            db_path=db_path,
        )
        assert r1.returncode == 0, f"render 1 failed: {r1.stderr}"
        assert loans_md.exists(), f"loans.md not created at {loans_md}"
        assert scenarios_md.exists(), "scenarios.md not created"
        loans_bytes_a = loans_md.read_bytes()
        scenarios_bytes_a = scenarios_md.read_bytes()

        # 4. Second render against same DB state
        r2 = node_orchestration_run(
            "orchestration/db-write.mjs",
            "render-markdown",
            db_path=db_path,
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
