"""Phase 9 render-markdown byte-identical end-to-end test (ROADMAP SC-4).

SC-4: loans.md and scenarios.md regenerate via --render-markdown byte-identical.

This is the END-TO-END companion to Wave 4's
test_render_markdown.py::test_render_markdown_byte_identical (which is
the minimal unit-style assertion). The end-to-end variant runs the full
init -> insert -> render -> render -> hashlib.sha256 compare pipeline,
making the byte-identical contract regression-safe.

Per Wave 4 D-04 inheritance: the byte-equality property depends on
(a) explicit ORDER BY id ASC in render SELECTs, (b) NO generated_at
timestamp embedded in markdown body, (c) the mandatory <!-- Generated
from data/mortgage-ops.duckdb - edit via scripts, not directly --> header
at line 1.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from tests.conftest import node_orchestration_run

if TYPE_CHECKING:
    from pathlib import Path

GENERATED_HEADER: str = "<!-- Generated from data/mortgage-ops.duckdb"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_render_markdown_byte_identical_end_to_end(tmp_path: Path) -> None:
    """ROADMAP SC-4 end-to-end: full pipeline init -> 3 inserts ->
    render -> render -> SHA256-compare. Both files (loans.md +
    scenarios.md) must hash identically across consecutive runs."""
    db_path = tmp_path / "test_render_e2e.duckdb"
    markdown_dir = tmp_path / "markdown"
    markdown_env = {"MORTGAGE_OPS_MARKDOWN_DIR": str(markdown_dir)}
    loans_md = markdown_dir / "loans.md"
    scenarios_md = markdown_dir / "scenarios.md"

    try:
        # 1. Init schema
        init = node_orchestration_run("orchestration/init-db.mjs", db_path=db_path)
        assert init.returncode == 0, f"init failed: {init.stderr}"

        # 2. Insert 3 loans (varying types, principals, terms — non-trivial render)
        fixtures = [
            {
                "principal": "200000.00",
                "annual_rate": "0.065000",
                "term_months": 360,
                "origination_date": "2026-05-01",
                "loan_type": "fixed",
            },
            {
                "principal": "350000.00",
                "annual_rate": "0.070000",
                "term_months": 180,
                "origination_date": "2026-05-15",
                "loan_type": "jumbo",
            },
            {
                "principal": "1000000.00",
                "annual_rate": "0.069500",
                "term_months": 360,
                "origination_date": "2026-06-01",
                "loan_type": "jumbo",
            },
        ]
        for i, loan in enumerate(fixtures):
            fx = tmp_path / f"loan_{i}.json"
            fx.write_text(json.dumps(loan))
            ins = node_orchestration_run(
                "orchestration/db-write.mjs",
                "insert-loan",
                "--json",
                str(fx),
                db_path=db_path,
            )
            assert ins.returncode == 0, f"insert {i} failed: {ins.stderr}"

        # 3. First render
        r1 = node_orchestration_run(
            "orchestration/db-write.mjs",
            "render-markdown",
            db_path=db_path,
            env_overrides=markdown_env,
        )
        assert r1.returncode == 0, f"render run 1 failed: {r1.stderr}"
        assert loans_md.exists(), f"loans.md not created at {loans_md}"
        assert scenarios_md.exists(), f"scenarios.md not created at {scenarios_md}"

        hash_loans_1 = _sha256(loans_md)
        hash_scenarios_1 = _sha256(scenarios_md)

        # 4. Second render against same DB state — must produce identical bytes
        r2 = node_orchestration_run(
            "orchestration/db-write.mjs",
            "render-markdown",
            db_path=db_path,
            env_overrides=markdown_env,
        )
        assert r2.returncode == 0, f"render run 2 failed: {r2.stderr}"

        hash_loans_2 = _sha256(loans_md)
        hash_scenarios_2 = _sha256(scenarios_md)

        # 5. Byte-identical contract (load-bearing)
        assert hash_loans_1 == hash_loans_2, (
            f"ROADMAP SC-4 violation: loans.md drifted between consecutive renders.\n"
            f"  Run 1 SHA256: {hash_loans_1}\n"
            f"  Run 2 SHA256: {hash_loans_2}\n"
            f"Likely cause (per Wave 4 D-04-03/04): missing ORDER BY id ASC, OR "
            f"a generated_at timestamp embedded in render output."
        )
        assert hash_scenarios_1 == hash_scenarios_2, (
            f"ROADMAP SC-4 violation: scenarios.md drifted between consecutive renders.\n"
            f"  Run 1 SHA256: {hash_scenarios_1}\n"
            f"  Run 2 SHA256: {hash_scenarios_2}"
        )

        # 6. Mandatory <!-- Generated from ... --> header at line 1 of both
        # (Wave 4 D-04-01 — load-bearing per Plan 09-PATTERNS.md)
        loans_text = loans_md.read_text()
        scenarios_text = scenarios_md.read_text()
        assert loans_text.startswith(GENERATED_HEADER), (
            f"loans.md missing 'Generated from' header at line 1; "
            f"first 80 chars: {loans_text[:80]!r}"
        )
        assert scenarios_text.startswith(GENERATED_HEADER), (
            f"scenarios.md missing 'Generated from' header at line 1; "
            f"first 80 chars: {scenarios_text[:80]!r}"
        )

        # 7. All three principals appear in the rendered loans body (Decimal-string
        # discipline preserved through render layer per Wave 4 D-04-02)
        for principal in ("200000.00", "350000.00", "1000000.00"):
            assert principal in loans_text, (
                f"principal {principal!r} missing from rendered loans.md; "
                f"likely cause: CAST AS VARCHAR not applied (D-04-02)."
            )

    finally:
        # Cleanup generated artifacts (gitignored but tidy)
        loans_md.unlink(missing_ok=True)
        scenarios_md.unlink(missing_ok=True)
