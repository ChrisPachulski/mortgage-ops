"""Phase 15 Plan 15-01 Wave 0 RED stubs for the property_analyze.py orchestrator.

Subprocess-driven CLI tests targeting
``.claude/skills/mortgage-ops/scripts/property_analyze.py`` (skill folder, per
Phase 13 ``property_fetch.py`` precedent + RESEARCH OQ2 RESOLVED).

Covers MODE-03 (orchestrator contract):
  - --help fast path (D-18 lazy-import)
  - argparse parse error → exit 2 (Phase 12 WR-02 documented exception)
  - Success envelope shape (D-15-ORCH-03)
  - Error envelope ALWAYS exits 0 (D-15-ORCH-03 key invariant)
  - Pydantic 6-key envelope on stderr (Phase 3/10/12 WR-02 closure)
  - Filename format reports/NNN-property-{zpid}-{YYYY-MM-DD}.md (D-15-ORCH-04 + RPRT-01)
  - Same-day same-zpid -r2 suffix (Pitfall 6)
  - household.yml multi-applicant → flat Phase-14 Household mapping (Pitfall 2)
  - --output-dir outside project root rejected (ASVS V5 path-traversal)
  - User Layer (config/household.yml + config/profile.yml) read-only (DATA_CONTRACT)
  - Sidecar listing JSON written to data/property-listings/ (Pitfall 10 + A3)

Module-level xfail guard: when SCRIPT_PATH doesn't exist (Wave 0 RED state),
the whole module is xfailed so pytest collection succeeds. Plan 15-03 SHIPS
the orchestrator and this entire module flips GREEN.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Skill-folder script path (RESEARCH OQ2 RESOLVED — matches Phase 13
# property_fetch.py precedent: scripts live INSIDE the skill folder for
# portability per CLAUDE.md "Skill portability").
# ---------------------------------------------------------------------------

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "property_analyze.py"
)
"""Phase 12 idiom: absolute path to the CLI under test. Plan 15-03 ships this."""

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Wave 0 RED guard — Plan 15-03 ships property_analyze.py.
# ---------------------------------------------------------------------------

if not SCRIPT_PATH.exists():
    pytestmark = pytest.mark.xfail(
        reason=(
            "Wave 1 — .claude/skills/mortgage-ops/scripts/property_analyze.py "
            "not yet shipped (Plan 15-03)"
        ),
        strict=False,
    )


def _run_cli(
    *args: str,
    env: dict[str, str] | None = None,
    timeout: float = 15,
) -> subprocess.CompletedProcess[str]:
    """Run property_analyze.py with given args; return CompletedProcess.

    Mirrors tests/test_property_fetch.py:_run_cli (PATTERNS.md L639-649).
    """
    cmd = [sys.executable, str(SCRIPT_PATH), *args]
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged_env,
        check=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_reports(tmp_path: Path) -> Iterator[Path]:
    """MODE-03: scratch reports/ dir for the orchestrator so its NNN sequencer
    starts at 1 each test (no cross-test pollution).

    The directory MUST live inside the project root because property_analyze.py
    enforces project-root containment on --output-dir (ASVS V5 path-traversal
    hardening). We create a unique subdir under <project_root>/reports/.test-tmp/
    keyed off the pytest tmp_path's basename so parallel runs don't collide,
    and clean it up at teardown.
    """
    import shutil

    base = PROJECT_ROOT / "reports" / ".test-tmp"
    base.mkdir(parents=True, exist_ok=True)
    out = base / tmp_path.name
    out.mkdir()
    try:
        yield out
    finally:
        shutil.rmtree(out, ignore_errors=True)


@pytest.fixture
def golden_listing() -> Path:
    """D-15-EVAL-01: synthetic eval fixture authored by Task 1 of this plan."""
    return PROJECT_ROOT / "evals" / "fixtures" / "property" / "sfh_conforming_001.json"


@pytest.fixture
def household_yml() -> Path:
    """MODE-03 + Pitfall 2: real multi-applicant household.example.yml from
    Phase 4 — exercises the YAML→flat-Household mapping the orchestrator must
    implement (D-15-ORCH-01)."""
    return PROJECT_ROOT / "config" / "household.example.yml"


@pytest.fixture
def profile_yml() -> Path:
    """MODE-03: real profile.example.yml (Phase 1 skeleton)."""
    return PROJECT_ROOT / "config" / "profile.example.yml"


# ---------------------------------------------------------------------------
# MODE-03 — D-18 lazy-import smoke test (--help fast path)
# ---------------------------------------------------------------------------


def test_help_fast_no_heavy_imports() -> None:
    """MODE-03 + D-18: --help completes in <300ms and returncode 0; the
    orchestrator must defer pydantic / yaml / lib.property_analysis imports
    until AFTER argparse so the --help fast path is unaffected (PATTERNS L840-865)."""
    start = time.perf_counter()
    result = _run_cli("--help")
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert elapsed < 0.3, f"--help took {elapsed:.3f}s; D-18 violated (cap 0.3s)"


def test_argparse_error_exit_2() -> None:
    """MODE-03 + Phase 12 WR-02 + D-15-ORCH-03: argparse parse error
    (no required --listing/--household/--profile/--output-dir) returns the
    one documented exit-2 exception. All other failure modes exit 0 with
    envelope."""
    result = _run_cli()  # no args at all
    assert result.returncode == 2, (
        f"argparse missing-required-args expected exit 2; got {result.returncode}"
    )


# ---------------------------------------------------------------------------
# MODE-03 — envelope contracts (success + error + Pydantic stderr)
# ---------------------------------------------------------------------------


def test_success_envelope_shape(
    tmp_reports: Path,
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
) -> None:
    """MODE-03 + D-15-ORCH-03: success envelope = {report_path: str ending .md,
    verdict: 'GO'|'WATCH'|'NO_GO', error: null}; returncode 0; the
    report_path file actually exists on disk."""
    result = _run_cli(
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        str(tmp_reports),
    )
    assert result.returncode == 0, (
        f"orchestrator returned {result.returncode}; stderr={result.stderr}"
    )
    env = json.loads(result.stdout)
    assert env["error"] is None
    assert env["verdict"] in ("GO", "WATCH", "NO_GO")
    assert isinstance(env["report_path"], str)
    assert env["report_path"].endswith(".md")
    assert Path(env["report_path"]).is_file()


def test_error_envelope_always_exit_0(tmp_path: Path, tmp_reports: Path) -> None:
    """MODE-03 + D-15-ORCH-03 KEY INVARIANT: bad listing input → error
    envelope on stdout + returncode 0 (NOT exit 2 — that's reserved for
    argparse only per Phase 12 WR-02 + D-15-ORCH-03)."""
    bad = tmp_path / "bad.json"
    bad.write_text("{}")  # missing required PropertyListing fields
    result = _run_cli(
        "--listing",
        str(bad),
        "--household",
        str(PROJECT_ROOT / "config" / "household.example.yml"),
        "--profile",
        str(PROJECT_ROOT / "config" / "profile.example.yml"),
        "--output-dir",
        str(tmp_reports),
    )
    assert result.returncode == 0, (
        f"D-15-ORCH-03 violated: returncode={result.returncode}; envelope must "
        f"exit 0 on bad input (only argparse parse errors exit 2)"
    )
    env = json.loads(result.stdout)
    assert env["error"] is not None
    assert env["error"]["code"]
    assert env["error"]["message"]
    assert env["report_path"] is None
    assert env["verdict"] is None


def test_pydantic_validation_envelope_on_stderr(tmp_path: Path, tmp_reports: Path) -> None:
    """MODE-03 + WR-02 closure: when listing JSON violates PropertyListing
    Pydantic contract (e.g., float price violates Money/Decimal discipline),
    the 6-key Pydantic envelope (type/loc/msg/input/url + optional ctx) is
    emitted to stderr. The stdout envelope still has error.code +
    error.message + report_path=null + verdict=null. returncode = 0."""
    bad = tmp_path / "bad.json"
    # JSON float for price violates Money's Decimal-from-string contract
    bad.write_text('{"price": 625000.00}')
    result = _run_cli(
        "--listing",
        str(bad),
        "--household",
        str(PROJECT_ROOT / "config" / "household.example.yml"),
        "--profile",
        str(PROJECT_ROOT / "config" / "profile.example.yml"),
        "--output-dir",
        str(tmp_reports),
    )
    assert result.returncode == 0
    stderr_envelope = json.loads(result.stderr)
    assert isinstance(stderr_envelope, list)
    required_keys = {"type", "loc", "msg", "input", "url"}
    for err in stderr_envelope:
        assert set(err.keys()) >= required_keys, (
            f"Pydantic stderr envelope missing required keys: {required_keys - set(err.keys())}"
        )


# ---------------------------------------------------------------------------
# RPRT-01 + D-15-ORCH-04 — filename format + NNN sequencer
# ---------------------------------------------------------------------------


def test_filename_format(
    tmp_reports: Path,
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
) -> None:
    """RPRT-01 + D-15-ORCH-04: successful run produces report_path matching
    reports/NNN-property-{zpid}-{YYYY-MM-DD}.md (NNN = zero-padded 3-digit
    counter, computed by max-existing-NNN + 1 per PATTERNS L264-280)."""
    result = _run_cli(
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        str(tmp_reports),
    )
    assert result.returncode == 0
    env = json.loads(result.stdout)
    # Match either absolute or relative path; just require the tail conforms.
    pattern = re.compile(r"\d{3}-property-\w+-\d{4}-\d{2}-\d{2}\.md$")
    assert pattern.search(env["report_path"]), (
        f"report_path {env['report_path']!r} does not match "
        f"NNN-property-{{zpid}}-{{YYYY-MM-DD}}.md (D-15-ORCH-04)"
    )


def test_same_day_zpid_suffix(
    tmp_reports: Path,
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
) -> None:
    """RPRT-01 + Pitfall 6: two consecutive runs with the same listing+date →
    second report_path ends with '-r2.md' (NNN sequencer collision suffix
    per PATTERNS L267-280)."""
    args = (
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        str(tmp_reports),
    )
    r1 = _run_cli(*args)
    assert r1.returncode == 0, f"first run failed: stderr={r1.stderr}"
    r2 = _run_cli(*args)
    assert r2.returncode == 0, f"second run failed: stderr={r2.stderr}"
    env2 = json.loads(r2.stdout)
    assert env2["report_path"].endswith("-r2.md"), (
        f"same-day same-zpid second run report_path={env2['report_path']!r} "
        f"missing '-r2.md' suffix (Pitfall 6)"
    )


# ---------------------------------------------------------------------------
# MODE-03 — household.yml multi-applicant → flat Household mapping (Pitfall 2)
# ---------------------------------------------------------------------------


def test_household_yaml_mapping(
    tmp_reports: Path,
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
) -> None:
    """MODE-03 + Pitfall 2: orchestrator loads the real Phase 4
    config/household.example.yml multi-applicant shape (applicants[].
    gross_monthly_income, monthly_debts.{auto,student_loans,credit_cards,other})
    and maps it to the flat Phase 14 Household model
    (monthly_income, monthly_obligations, fico) per PATTERNS L237-260.

    Test passes when the orchestrator runs to completion without YAML or
    Pydantic ValidationError — i.e., the mapping logic is wired correctly."""
    result = _run_cli(
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        str(tmp_reports),
    )
    assert result.returncode == 0, (
        f"household.yml mapping crashed orchestrator; stderr={result.stderr!r}; Pitfall 2 violated"
    )
    env = json.loads(result.stdout)
    assert env["error"] is None, (
        f"household.yml mapping produced error envelope: {env['error']!r}; Pitfall 2 violated"
    )


# ---------------------------------------------------------------------------
# MODE-03 — ASVS V5 path-traversal hardening (--output-dir outside project)
# ---------------------------------------------------------------------------


def test_output_dir_outside_project_rejected(
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
) -> None:
    """MODE-03 + ASVS V5 (PATTERNS L920-930): --output-dir paths that escape
    the project root return an error envelope with code='output_dir_unwritable'
    (defense-in-depth path-traversal rejection)."""
    result = _run_cli(
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        "/tmp/foo-property-out",
    )
    assert result.returncode == 0  # always-exit-0 envelope (D-15-ORCH-03)
    env = json.loads(result.stdout)
    assert env["error"] is not None
    assert env["error"]["code"] == "output_dir_unwritable", (
        f"out-of-project --output-dir should return code='output_dir_unwritable'; "
        f"got {env['error']['code']!r}"
    )


def test_existing_out_of_tree_output_dir_rejected(
    tmp_path: Path,
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
) -> None:
    """MODE-03 + ASVS V5: containment guard rejects an EXISTING directory that
    lives outside the project root (the previous gate only checked is_dir() and
    so accepted any writable directory anywhere on disk). pytest's tmp_path
    resolves to /private/var/folders/... on macOS — strictly outside the repo.
    """
    out_dir = tmp_path / "outside-project-reports"
    out_dir.mkdir()
    result = _run_cli(
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        str(out_dir),
    )
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["error"] is not None
    assert env["error"]["code"] == "output_dir_unwritable", (
        f"existing-but-out-of-tree --output-dir should return "
        f"code='output_dir_unwritable'; got {env['error']['code']!r}"
    )
    assert "project root" in env["error"]["message"].lower(), (
        f"error message should reference project-root containment; got {env['error']['message']!r}"
    )


# ---------------------------------------------------------------------------
# MODE-03 — DATA_CONTRACT User Layer read-only invariant
# ---------------------------------------------------------------------------


def test_user_layer_files_unmodified(
    tmp_reports: Path,
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
) -> None:
    """MODE-03 + DATA_CONTRACT (CLAUDE.md User Layer): orchestrator NEVER
    writes config/household.yml or config/profile.yml. We capture mtime
    before + after and assert unchanged."""
    h_before = household_yml.stat().st_mtime_ns
    p_before = profile_yml.stat().st_mtime_ns
    result = _run_cli(
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        str(tmp_reports),
    )
    assert result.returncode == 0
    h_after = household_yml.stat().st_mtime_ns
    p_after = profile_yml.stat().st_mtime_ns
    assert h_before == h_after, (
        f"household.yml mtime changed ({h_before} → {h_after}); "
        f"DATA_CONTRACT User Layer is read-only (CLAUDE.md)"
    )
    assert p_before == p_after, (
        f"profile.yml mtime changed ({p_before} → {p_after}); "
        f"DATA_CONTRACT User Layer is read-only (CLAUDE.md)"
    )


# ---------------------------------------------------------------------------
# MODE-03 — Sidecar listing JSON (Pitfall 10 + Assumption A3)
# ---------------------------------------------------------------------------


def test_sidecar_listing_written(
    tmp_reports: Path,
    golden_listing: Path,
    household_yml: Path,
    profile_yml: Path,
    tmp_path: Path,
) -> None:
    """MODE-03 + Pitfall 10 + A3: successful run writes the validated
    listing JSON to data/property-listings/{zpid}-{YYYY-MM-DD}.json so the
    citation footer's full re-runnable invocation references a STABLE path
    (not the ephemeral /tmp tempfile the mode-body originally fed in)."""
    result = _run_cli(
        "--listing",
        str(golden_listing),
        "--household",
        str(household_yml),
        "--profile",
        str(profile_yml),
        "--output-dir",
        str(tmp_reports),
    )
    assert result.returncode == 0
    sidecar_dir = PROJECT_ROOT / "data" / "property-listings"
    # Sidecar pattern: {zpid}-{YYYY-MM-DD}.json; zpid="1" from fixture.
    matches = list(sidecar_dir.glob("1-*.json")) if sidecar_dir.exists() else []
    assert matches, (
        f"Pitfall 10 + A3: orchestrator did not write sidecar listing JSON to "
        f"data/property-listings/1-{{YYYY-MM-DD}}.json (searched: {sidecar_dir})"
    )
