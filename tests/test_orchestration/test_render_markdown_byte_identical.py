"""Phase 9 render-markdown byte-identical end-to-end test (ROADMAP SC-4).

SC-4: data/loans.md and data/scenarios.md regenerate via --render-markdown
byte-identical.

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

from tests.conftest import REPO_ROOT, node_orchestration_run

if TYPE_CHECKING:
    from pathlib import Path

# The render-markdown subcommand writes to FIXED paths under data/
# (Plan 09-04 D-04-07: paths NOT env-var-overridable in v1).
LOANS_MD: Path = REPO_ROOT / "data" / "loans.md"
SCENARIOS_MD: Path = REPO_ROOT / "data" / "scenarios.md"
GENERATED_HEADER: str = "<!-- Generated from data/mortgage-ops.duckdb"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_render_markdown_byte_identical_end_to_end(tmp_path: Path) -> None:
    """ROADMAP SC-4 end-to-end: full pipeline init -> 3 inserts ->
    render -> render -> SHA256-compare. Both files (loans.md +
    scenarios.md) must hash identically across consecutive runs."""
    db_path = tmp_path / "test_render_e2e.duckdb"

    # Cleanup any leftover render artifacts (Plan 09-04 D-04-07: render
    # writes to fixed paths under data/, regardless of DB location).
    for f in (LOANS_MD, SCENARIOS_MD):
        if f.exists():
            f.unlink()

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
            "orchestration/db-write.mjs", "render-markdown", db_path=db_path
        )
        assert r1.returncode == 0, f"render run 1 failed: {r1.stderr}"
        assert LOANS_MD.exists(), f"loans.md not created at {LOANS_MD}"
        assert SCENARIOS_MD.exists(), f"scenarios.md not created at {SCENARIOS_MD}"

        hash_loans_1 = _sha256(LOANS_MD)
        hash_scenarios_1 = _sha256(SCENARIOS_MD)

        # 4. Second render against same DB state — must produce identical bytes
        r2 = node_orchestration_run(
            "orchestration/db-write.mjs", "render-markdown", db_path=db_path
        )
        assert r2.returncode == 0, f"render run 2 failed: {r2.stderr}"

        hash_loans_2 = _sha256(LOANS_MD)
        hash_scenarios_2 = _sha256(SCENARIOS_MD)

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
        loans_text = LOANS_MD.read_text()
        scenarios_text = SCENARIOS_MD.read_text()
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
        for f in (LOANS_MD, SCENARIOS_MD):
            if f.exists():
                f.unlink()
