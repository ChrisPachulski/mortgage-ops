"""Phase 9 markdown view regeneration (PERS-06 + ROADMAP SC-4).

Wave 4 (Plan 09-04) ships orchestration/db-write.mjs --render-markdown.
The byte-identical guarantee is the load-bearing contract: two
consecutive renders against the same DB state produce IDENTICAL bytes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.xfail(
    strict=True, reason="Wave 0 stub - Plan 09-04 ships db-write.mjs --render-markdown"
)
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
