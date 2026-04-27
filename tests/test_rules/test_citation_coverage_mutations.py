"""Mutation tests for the Phase 2 meta-tests (RUL-12, RUL-13, REF-09 final pass).

These are NOT predicates and they have NO regulatory citation. They are second-
order tests that prove the citation-coverage meta-test (`test_citation_coverage.py`)
and the schema meta-test (`test_schema.py`) actually catch the regression classes
they claim to defend against.

A meta-test that has never failed is not yet trustworthy. We synthesize the
failure paths here and assert they fire.

Isolation discipline:
  - Each mutation runs in a `tmp_path`-cloned copy of the repo (`shutil.copytree`).
  - The original meta-test runs in a `subprocess.run(["uv", "run", "pytest", ...])`
    against the clone — never imported in-process.
  - The live source tree is never modified.

Mutations covered:
  1. Strip the `Citation:` line from one predicate -> citation meta-test FAILS
  2. Strip the `Source URL:` line from one predicate -> citation meta-test FAILS
  3. Strip the `Effective:` line from one predicate -> citation meta-test FAILS
  4. Delete one predicate's matching fixture file -> fixture meta-test FAILS
  5. Strip the `source:` field from one reference YAML -> schema meta-test FAILS
  6. Strip the `effective:` field from one reference YAML -> schema meta-test FAILS

Per CONTEXT.md `<specifics>` line 175.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

# Repo root = three parents up from this test file:
#   tests/test_rules/test_citation_coverage_mutations.py
#       -> tests/test_rules -> tests -> <repo root>
REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# Targets we mutate. conventional_pmi is canonical because plan 02-05 ships it
# as the canonical predicate template per RESEARCH §Pattern 3 (lines 386-445).
PREDICATE_TO_MUTATE: Path = REPO_ROOT / "lib" / "rules" / "conventional_pmi.py"
YAML_TO_MUTATE: Path = REPO_ROOT / "data" / "reference" / "conforming-limits-2026.yml"
FIXTURE_TO_DELETE: Path = (
    REPO_ROOT / "tests" / "fixtures" / "rules" / "conventional_pmi_auto_terminate_78ltv.json"
)


def _clone_repo(tmp_path: Path) -> Path:
    """Clone the repo into tmp_path/repo so we can mutate without polluting source."""
    dest = tmp_path / "repo"
    # Skip large/cache directories to keep the clone fast.
    shutil.copytree(
        REPO_ROOT,
        dest,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".mypy_cache",
            ".ruff_cache",
            ".pytest_cache",
            "__pycache__",
            "node_modules",
            "data/mortgage-ops.duckdb",
            "reports",
        ),
        dirs_exist_ok=False,
    )
    return dest


def _run_meta_test(repo: Path, test_node: str) -> subprocess.CompletedProcess[str]:
    """Run the meta-test in a subprocess against the cloned repo.

    `test_node` is the pytest node spec, e.g.
      'tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring'.
    Returns the CompletedProcess so callers can assert returncode != 0.
    """
    return subprocess.run(
        ["uv", "run", "pytest", test_node, "-x", "--tb=short", "--no-header", "-q"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _strip_line(path: Path, line_substring: str, *, anchored: bool = False) -> None:
    """Remove every line containing line_substring from path (in-place in the clone).

    When `anchored=True`, only strip lines that match the needle at the start
    of the (whitespace-stripped) line — i.e. `re.match(rf'^\\s*{re.escape(needle)}', line)`.
    Use `anchored=True` for YAML key mutations (`source:` / `effective:` at the
    start of a line) so substring collisions like `source_url:` are NOT stripped.
    Use the default `anchored=False` for predicate-docstring mutations
    (`Citation:`, `Source URL:`, `Effective:` — these may be indented or appear
    multiple times, and stripping all of them is the desired behavior).
    """
    text = path.read_text()
    if anchored:
        pattern = re.compile(rf"^\s*{re.escape(line_substring)}")
        new_lines = [line for line in text.splitlines() if not pattern.match(line)]
    else:
        new_lines = [line for line in text.splitlines() if line_substring not in line]
    path.write_text("\n".join(new_lines) + "\n")


def test_strip_citation_line_makes_meta_test_fail(tmp_path: Path) -> None:
    """Stripping the `Citation:` line from a predicate must make the meta-test FAIL.

    Hand: the citation meta-test asserts `"Citation:" in docstring`. Removing the
    line removes that substring; the assertion must surface as a non-zero exit.
    """
    repo = _clone_repo(tmp_path)
    target = repo / PREDICATE_TO_MUTATE.relative_to(REPO_ROOT)
    _strip_line(target, "Citation:")
    result = _run_meta_test(
        repo,
        "tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring",
    )
    assert result.returncode != 0, (
        "Stripping `Citation:` did not make the meta-test fail.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "Citation:" in result.stdout or "Citation:" in result.stderr, (
        "Failure message did not mention `Citation:` — meta-test may be failing for a different reason."
    )


def test_strip_source_url_line_makes_meta_test_fail(tmp_path: Path) -> None:
    """Stripping the `Source URL:` line must make the meta-test FAIL."""
    repo = _clone_repo(tmp_path)
    target = repo / PREDICATE_TO_MUTATE.relative_to(REPO_ROOT)
    _strip_line(target, "Source URL:")
    result = _run_meta_test(
        repo,
        "tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring",
    )
    assert result.returncode != 0
    assert "Source URL:" in result.stdout or "Source URL:" in result.stderr


def test_strip_effective_line_makes_meta_test_fail(tmp_path: Path) -> None:
    """Stripping the `Effective:` line must make the meta-test FAIL."""
    repo = _clone_repo(tmp_path)
    target = repo / PREDICATE_TO_MUTATE.relative_to(REPO_ROOT)
    _strip_line(target, "Effective:")
    result = _run_meta_test(
        repo,
        "tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring",
    )
    assert result.returncode != 0
    assert "Effective:" in result.stdout or "Effective:" in result.stderr


def test_delete_fixture_makes_meta_test_fail(tmp_path: Path) -> None:
    """Deleting a predicate's matching fixture must make the fixture meta-test FAIL.

    Hand: the fixture meta-test globs `tests/fixtures/rules/{stem}_*.json`. The
    predicate `conventional_pmi` has multiple fixtures shipped by 02-05; we delete
    ALL of them so the glob returns the empty list and the assertion fires.
    """
    repo = _clone_repo(tmp_path)
    fixture_dir = repo / "tests" / "fixtures" / "rules"
    # Delete every fixture whose stem starts with the canonical predicate name.
    deleted = list(fixture_dir.glob("conventional_pmi_*.json"))
    assert len(deleted) >= 1, (
        f"Expected >=1 conventional_pmi_*.json fixture in clone {fixture_dir} (02-05 should have shipped them)"
    )
    for f in deleted:
        f.unlink()
    result = _run_meta_test(
        repo,
        "tests/test_rules/test_citation_coverage.py::test_predicate_has_at_least_one_fixture",
    )
    assert result.returncode != 0, (
        "Deleting all conventional_pmi fixtures did not make the fixture meta-test fail.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "conventional_pmi" in result.stdout or "conventional_pmi" in result.stderr


def test_strip_yaml_source_makes_schema_test_fail(tmp_path: Path) -> None:
    """Stripping the `source:` field from a reference YAML must make schema test FAIL."""
    repo = _clone_repo(tmp_path)
    target = repo / YAML_TO_MUTATE.relative_to(REPO_ROOT)
    _strip_line(target, "source:", anchored=True)
    result = _run_meta_test(
        repo,
        "tests/test_reference/test_schema.py",
    )
    assert result.returncode != 0
    assert "source" in result.stdout.lower() or "source" in result.stderr.lower()


def test_strip_yaml_effective_makes_schema_test_fail(tmp_path: Path) -> None:
    """Stripping the `effective:` field from a reference YAML must make schema test FAIL."""
    repo = _clone_repo(tmp_path)
    target = repo / YAML_TO_MUTATE.relative_to(REPO_ROOT)
    _strip_line(target, "effective:", anchored=True)
    result = _run_meta_test(
        repo,
        "tests/test_reference/test_schema.py",
    )
    assert result.returncode != 0
    assert "effective" in result.stdout.lower() or "effective" in result.stderr.lower()


def test_meta_tests_pass_unmutated_baseline(tmp_path: Path) -> None:
    """Sanity check: WITHOUT mutation, the meta-tests pass on the cloned repo.

    Without this baseline, a meta-test that fails for an unrelated reason (e.g.,
    clone problem, missing dependency) could give us false confidence that our
    mutation harness works.
    """
    repo = _clone_repo(tmp_path)
    citation_result = _run_meta_test(
        repo,
        "tests/test_rules/test_citation_coverage.py",
    )
    assert citation_result.returncode == 0, (
        "Citation-coverage meta-test failed on UNMUTATED clone — clone integrity issue.\n"
        f"stdout: {citation_result.stdout}\nstderr: {citation_result.stderr}"
    )
    schema_result = _run_meta_test(repo, "tests/test_reference/test_schema.py")
    assert schema_result.returncode == 0, (
        "Schema meta-test failed on UNMUTATED clone — clone integrity issue.\n"
        f"stdout: {schema_result.stdout}\nstderr: {schema_result.stderr}"
    )
