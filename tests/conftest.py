"""Shared pytest fixtures for the mortgage-ops test suite.

The `golden_fixture` factory loads pinned monthly P&I oracles from
`tests/fixtures/golden_pmt.json` (committed in Plan 05). Phase 1 only validates
shape; Phase 3+ uses the same loader to compute and assert against the values.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURE_DIR: Path = Path(__file__).parent / "fixtures"


@pytest.fixture
def golden_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single named fixture by `id` from
    tests/fixtures/golden_pmt.json. Raises KeyError if the id is not present."""

    def _load(fixture_id: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "golden_pmt.json"
        data = json.loads(path.read_text())
        for fx in data["fixtures"]:
            if fx["id"] == fixture_id:
                return fx  # type: ignore[no-any-return]
        raise KeyError(f"fixture id not found in golden_pmt.json: {fixture_id}")

    return _load


@pytest.fixture
def amortize_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single amortize fixture by filename stem
    from tests/fixtures/amortize/. Raises FileNotFoundError if the stem doesn't exist.

    Phase 3 fixtures are one-fixture-per-file (richer schemas than the wrapped
    array shape used by golden_pmt.json) so diffs stay readable. Loader takes a
    filename stem like "biweekly_true_200k_6_5", not a fixture id within an array.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "amortize" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


@pytest.fixture
def affordability_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single affordability fixture by filename
    stem from tests/fixtures/affordability/. Mirrors `amortize_fixture` —
    one-fixture-per-file shape; loader takes a filename stem like
    "forward_va_residual_fail", not an id within an array.

    Per CONTEXT.md D-17: every Phase 4 fixture lives under
    tests/fixtures/affordability/ as one .json per scenario.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "affordability" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


@pytest.fixture
def arm_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single ARM fixture by filename stem
    from tests/fixtures/arm/. Mirrors `amortize_fixture` and
    `affordability_fixture` — one-fixture-per-file shape; loader takes a
    filename stem like "arm_5_1_payment_jump_at_61", not an id within an array.

    Per Phase 5 CONTEXT.md D-09: every Phase 5 fixture lives under
    tests/fixtures/arm/ as one .json per scenario. Oracle capture pairs
    (Bankrate/Vertex42/AmericU per D-04) live under tests/fixtures/arm/oracle/;
    callers pass "oracle/bankrate_5_1_capture_2026" as the stem to load those.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "arm" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


@pytest.fixture
def refinance_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single refi fixture by filename stem
    from tests/fixtures/refinance/. Mirrors arm_fixture / affordability_fixture
    / amortize_fixture — one-fixture-per-file shape; loader takes a filename
    stem like "positive_npv_200bps_drop_2k_costs", not an id within an array.

    Per Phase 6 D-15: every Phase 6 fixture lives under tests/fixtures/refinance/
    as one .json per scenario.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "refinance" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


@pytest.fixture
def apr_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single APR fixture by filename stem
    from tests/fixtures/apr/. Mirrors arm_fixture / refinance_fixture —
    one-fixture-per-file shape; loader takes a filename stem like
    "regz_appendix_j_5000_36_166_07", not an id within an array.

    Per Phase 7 D-00-03: every Phase 7 fixture lives under tests/fixtures/apr/
    as one .json per scenario. FFIEC oracle captures (Wave 7 human checkpoint
    per CONTEXT.md D-01: HMDA Platform pivot) live under
    tests/fixtures/apr/oracle/; callers pass
    "oracle/ffiec_001_30yr_400k_6_5" as the stem to load those.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "apr" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


@pytest.fixture
def stress_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single stress fixture by filename stem
    from tests/fixtures/stress/. Mirrors arm_fixture / affordability_fixture.

    Per Phase 8 Plan 08-05: every Phase 8 stress fixture lives under
    tests/fixtures/stress/ as one .json per scenario. Oracle pairs (if any
    v2 capture-as-fixture lands) live under tests/fixtures/stress/oracle/.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "stress" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


@pytest.fixture
def points_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single points-breakeven fixture by
    filename stem from tests/fixtures/points/. Mirrors arm_fixture /
    affordability_fixture / stress_fixture. Plan 08-05 ships fixtures here.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "points" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


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


@pytest.fixture
def skill_root() -> Path:
    """Return the absolute path to .claude/skills/mortgage-ops/ for cross-test reuse.

    Phase 10 ships this fixture so every Phase 10/11/12 test that introspects
    the skill folder (SKILL.md, modes/, references/, scripts/, LICENSE.txt)
    has a single source of truth for the path. The folder may not exist at
    Wave 0 time (Plans 10-01 through 10-05 create it); tests that depend on
    existence MUST assert that explicitly.

    Per LOCKED DECISION D-01: the skill folder lives at
    .claude/skills/mortgage-ops/ (project-relative).
    """
    return Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops"


@pytest.fixture
def repo_root() -> Path:
    """Return the absolute path to the repo root for cross-test reuse.

    Round-2 codex HIGH 1: prior Wave 5/6 drafts used
    `skill_root.parent.parent.parent.parent` (four chained .parent calls)
    to derive the repo root. That goes one level too high — `.claude/skills/
    mortgage-ops` is only THREE levels deep (mortgage-ops → skills → .claude
    → repo root). The correct equivalents are `skill_root.parents[2]` or
    this `repo_root` fixture. Wave 5/6 tests MUST use one of these two
    forms.

    Implementation: `Path(__file__).resolve().parents[1]` (conftest.py lives
    in tests/, so parents[0] = tests/, parents[1] = repo root).
    """
    return Path(__file__).resolve().parents[1]
