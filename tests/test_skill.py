"""Phase 10 Claude Skill Frontend — full test surface (SKLL-01..13).

Wave 0 (Plan 10-00) creates ALL ≥ 15 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 1 (Plan 10-01 scripts relocation):    SKLL-10                     (1 test)
- Wave 2 (Plan 10-02 SKILL.md scaffold):      SKLL-01..04, SKLL-11..12   (7 tests)
- Wave 3 (Plan 10-03 modes/*):                SKLL-05..07                (3 tests)
- Wave 4 (Plan 10-04 references/*):           SKLL-08..09                (2 tests)
- Wave 5 (Plan 10-05 CI tests + ports):       SKLL-13 (per D-13-01..05; 2 stubs)

Per LOCKED DECISION D-02: the token-budget assertion uses
tests._skill_helpers.count_tokens (tiktoken cl100k_base) with a 10% safety
margin against the 5000-token Anthropic spec recommendation; effective
threshold = 4500 cl100k tokens.

Per LOCKED DECISION D-12: SKLL-02 enforcement parses the first 200 lines of
SKILL.md and asserts the mode dispatch table marker (`## Mode Routing`) is
present.

Per CONTEXT.md D-13-01..D-13-05: Phase 10 CLOSES SKLL-13 (NOT deferred to
Phase 9). Two new stubs ship in Wave 0 and flip in Wave 5: filename-format
test (reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md per D-13-02) and DuckDB-row
persistence test (per D-13-04 — `node orchestration/db-write.mjs insert-report
--scenario-id <int> --file <path>`, the REAL Phase 9 CLI from
`orchestration/db-write.mjs` usage block lines 296-310).

Each xfail decorator carries `strict=True` so a passing test in xfail state
raises XPASS at collection time — the wave that flips it MUST also remove
the decorator. This prevents accidental "fixed but still marked xfail" drift
(Phase 5 D-XX hygiene contract inherited).

Note: imports for `re`, `subprocess`, `sys`, `yaml`, `count_tokens` are NOT
included at module level in Wave 0 — they would trigger ruff F401
(unused-import) since stub bodies use only `pytest.fail`. Wave 5 (Plan 10-05)
adds these imports at module level when the flipped assertions consume them
(via an explicit "import housekeeping" step per Round-2 codex HIGH 5).
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
import yaml

from tests._skill_helpers import count_tokens

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Wave 5 (Plan 10-05) parametrize sources + section/example constants.
# ---------------------------------------------------------------------------

EXPECTED_MODES: frozenset[str] = frozenset(
    {
        "evaluate",
        "compare",
        "refinance",
        "affordability",
        "stress",
        "amortize",
        "arm",
    }
)
"""SKLL-05 + ROADMAP SC-4: 7 mode files."""

EXPECTED_REFERENCES: frozenset[str] = frozenset(
    {
        "amortization-formulas",
        "apr-reg-z",
        "arm-mechanics",
        "refi-npv",
        "affordability-rules",
        "gse-limits",
        "mip-pmi",
        "tax-deductibility",
        "spreadsheet-conventions",
    }
)
"""SKLL-08 + ROADMAP SC-5: 9 reference files."""

SHARED_MD_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Sources of Truth",
    "Profile Loading",
    "Money Discipline",
    "Always Cite the Script",
    "Never Invent Numbers",
    "Estimated APR Literal Text",
    "Script Invocation Doctrine",
    "Error Narration Template",
    "Output File Naming",
    "Output Formatting",
    "Save Report",
    "Forbidden Behaviors",
)
"""SKLL-06 + UI-SPEC §i + Round-2 codex MEDIUM 7: 12 mandatory _shared.md
section headings (9 UI-SPEC §i baseline + Profile Loading per D-PROF-04 +
Output Formatting per D-NUM-01..06 + Save Report per D-13-01..05)."""

SHARED_MD_DNUM_EXAMPLES: tuple[str, ...] = (
    "$1,264.14",  # D-NUM-01 money: 2 decimals + comma + $ prefix
    "6.500%",  # D-NUM-02 rate: 3 decimals + trailing zeros + %
    "43.0%",  # D-NUM-03 ratio (DTI / LTV / CLTV): 1 decimal + %
)
"""D-NUM-01..06 example tokens (Round-2 codex MEDIUM 7). The Output
Formatting section MUST cite at least one example per directive so the
display contract is auditable. ARM bps formatting (D-NUM-04) is matched
separately by the `<n> bps (<x>.<yy>%)` regex."""

# ---------------------------------------------------------------------------
# SKLL-01 (2 stubs) — flipped in Wave 5 (CI tests). Uses count_tokens helper
# from Wave 0; threshold per D-02.
# ---------------------------------------------------------------------------


def test_skill_md_under_token_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1 + D-02: SKILL.md ≤ 4500 cl100k tokens (10% under 5000 Anthropic spec)."""
    skill_md = (skill_root / "SKILL.md").read_text()
    n_tokens = count_tokens(skill_md)
    assert n_tokens <= 4500, (
        f"SKILL.md is {n_tokens} cl100k tokens (budget 4500 = 5000 Anthropic spec - 10% margin per D-02). "
        f"Trim or move detail into modes/ or references/ (progressive disclosure SKLL-09). "
        f"Compaction re-attach budget is 5000 tokens; tokenizer drift would breach it."
    )


def test_skill_md_under_line_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1: SKILL.md ≤ 500 lines per agentskills.io guidance."""
    n_lines = (skill_root / "SKILL.md").read_text().count("\n") + 1
    assert n_lines <= 500, f"SKILL.md is {n_lines} lines (cap 500)"


# ---------------------------------------------------------------------------
# SKLL-02 (1 stub) — flipped in Wave 5; per D-12 grep-assert mode-routing
# in first 200 lines.
# ---------------------------------------------------------------------------


def test_skill_routing_in_first_200_lines(skill_root: Path) -> None:
    """SKLL-02 + D-12: '## Mode Routing' heading + 7 mode names appear in first 200 lines."""
    head = "\n".join((skill_root / "SKILL.md").read_text().splitlines()[:200])
    assert "## Mode Routing" in head, (
        "SKLL-02: '## Mode Routing' must appear in first 200 lines — survives "
        "Anthropic compaction re-attach (5000-token / first-200-line window)."
    )
    for mode in ("evaluate", "compare", "refinance", "affordability", "stress", "amortize", "arm"):
        assert mode in head, f"SKLL-02: mode '{mode}' not dispatched in first 200 lines"


# ---------------------------------------------------------------------------
# SKLL-03 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


def test_skill_md_frontmatter_required_fields(skill_root: Path) -> None:
    """SKLL-03 + ROADMAP SC-2 + D-03: frontmatter has name + description + license + compatibility per agentskills.io spec."""
    skill_md = (skill_root / "SKILL.md").read_text()
    parts = skill_md.split("---\n", 2)
    assert len(parts) >= 3, "SKILL.md missing YAML frontmatter delimiters"
    fm = yaml.safe_load(parts[1])

    for key in ("name", "description", "license", "compatibility"):
        assert key in fm, f"SKLL-03 frontmatter missing key '{key}'"

    assert fm["name"] == "mortgage-ops", (
        f"frontmatter 'name' must equal parent dir 'mortgage-ops'; got {fm['name']!r}"
    )
    assert len(fm["description"]) <= 1024, (
        f"description {len(fm['description'])} chars > 1024 spec cap"
    )
    assert len(fm["compatibility"]) <= 500, (
        f"compatibility {len(fm['compatibility'])} chars > 500 spec cap"
    )


# ---------------------------------------------------------------------------
# SKLL-04 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


def test_license_txt_exists_in_skill_folder(skill_root: Path) -> None:
    """SKLL-04 + ROADMAP SC-2 + D-04: LICENSE.txt bundled inside skill folder; references MIT per default."""
    license_path = skill_root / "LICENSE.txt"
    assert license_path.is_file(), f"SKLL-04: LICENSE.txt missing from {license_path}"
    text = license_path.read_text()
    assert "MIT License" in text or "Apache" in text or "BSD" in text or "Copyright" in text, (
        "LICENSE.txt should contain a recognizable license header"
    )


# ---------------------------------------------------------------------------
# SKLL-05 (1 stub) — flipped in Wave 5; parametrized over 7 modes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", sorted(EXPECTED_MODES))
def test_mode_file_exists(mode: str, skill_root: Path) -> None:
    """SKLL-05 + ROADMAP SC-4: every expected mode has a modes/{mode}.md file."""
    p = skill_root / "modes" / f"{mode}.md"
    assert p.exists(), f"SKLL-05 mode file missing: modes/{mode}.md"


# ---------------------------------------------------------------------------
# SKLL-06 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


def test_shared_mode_has_required_sections(skill_root: Path) -> None:
    """SKLL-06 + UI-SPEC §i + Round-2 codex MEDIUM 7: modes/_shared.md contains
    all 12 mandatory section headings (9 UI-SPEC §i + Profile Loading per
    D-PROF-04 + Output Formatting per D-NUM-01..06 + Save Report per
    D-13-01..05) AND each D-NUM-XX directive cites at least one example
    token so the display contract is auditable."""
    text = (skill_root / "modes" / "_shared.md").read_text()
    for section in SHARED_MD_REQUIRED_SECTIONS:
        assert section in text, f"SKLL-06 _shared.md missing section: {section!r}"
    # D-NUM-01..03 example tokens (Round-2 codex MEDIUM 7)
    for example in SHARED_MD_DNUM_EXAMPLES:
        assert example in text, (
            f"D-NUM (Round-2 codex MEDIUM 7): _shared.md Output Formatting "
            f"section must cite the example token {example!r}"
        )
    # D-NUM-04 ARM bps example: any `<n> bps (<x>.<yy>%)` token suffices
    assert re.search(r"\d+\s*bps\s*\(\d+\.\d{2}%\)", text), (
        "D-NUM-04 (Round-2 codex MEDIUM 7): _shared.md must include an ARM "
        "bps example like `200 bps (2.00%)` or `250 bps (2.50%)`."
    )


# ---------------------------------------------------------------------------
# SKLL-07 (1 stub) — flipped in Wave 5; per D-07 .example.md pattern
# ---------------------------------------------------------------------------


def test_profile_md_user_layer_gitignored(skill_root: Path, repo_root: Path) -> None:
    """SKLL-07 + D-07: modes/_profile.md is gitignored AND modes/_profile.example.md is committed."""
    gitignore = (repo_root / ".gitignore").read_text()
    profile_md_pattern = ".claude/skills/mortgage-ops/modes/_profile.md"
    assert profile_md_pattern in gitignore, (
        f"SKLL-07: .gitignore missing pattern '{profile_md_pattern}' "
        f"(modes/_profile.md is User Layer per DATA_CONTRACT.md)"
    )
    example = skill_root / "modes" / "_profile.example.md"
    assert example.is_file(), f"SKLL-07 + D-07: schema skeleton must exist at {example}"


# ---------------------------------------------------------------------------
# SKLL-07 / D-PROF-01 (1 stub) — _profile.example.md schema enforcement.
# Asserts the example schema parses as YAML AND has EXACTLY the four
# top-level keys (verbosity, citation_density, save_report, disambiguation),
# no extras. Flipped in Wave 5.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-03 ships D-PROF-01 schema; Plan 10-05 wires assertion",
)
def test_profile_example_md_has_exact_four_keys(skill_root: Path) -> None:
    """D-PROF-01 + D-PROF-02: _profile.example.md YAML body has EXACTLY these
    four top-level keys: verbosity, citation_density, save_report, disambiguation.
    No extras (calc inputs stay in config/household.yml + config/profile.yml)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-08 (1 stub) — flipped in Wave 5; parametrized over 9 references
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ref", sorted(EXPECTED_REFERENCES))
def test_reference_file_exists(ref: str, skill_root: Path) -> None:
    """SKLL-08 + ROADMAP SC-5: all 9 reference docs are bundled."""
    p = skill_root / "references" / f"{ref}.md"
    assert p.is_file(), f"SKLL-08 reference missing: references/{ref}.md"


# ---------------------------------------------------------------------------
# SKLL-09 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


def test_skill_md_documents_progressive_disclosure(skill_root: Path) -> None:
    """SKLL-09 + D-09 + ROADMAP SC-5: SKILL.md contains topic→reference table for on-demand reference loading."""
    text = (skill_root / "SKILL.md").read_text()
    text_lower = text.lower()
    assert (
        "load on demand" in text_lower
        or "progressive disclosure" in text_lower
        or "on demand" in text_lower
    ), (
        "SKLL-09: SKILL.md must mention on-demand reference loading "
        "(D-09 progressive disclosure rule)"
    )
    # All 9 reference filenames must appear in SKILL.md (the topic→reference table)
    for ref in EXPECTED_REFERENCES:
        assert ref in text, (
            f"SKLL-09: reference '{ref}' not listed in SKILL.md topic→reference table"
        )


# ---------------------------------------------------------------------------
# SKLL-10 (1 stub) — flipped in Wave 1 (relocation); per D-01 + D-06 + D-08.
# Asserts ALL SEVEN calc scripts live INSIDE the skill folder. Phase 6/7/8
# scripts (refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py)
# are confirmed shipped per STATE.md (Phase 6/7/8 COMPLETE) so all 7 scripts
# can be relocated together in Plan 10-01 Task 2.
# ---------------------------------------------------------------------------


def test_seven_scripts_in_skill_folder_only(skill_root: Path, repo_root: Path) -> None:
    """SKLL-10 + ROADMAP SC-3 + D-01 + D-06 + D-08: ALL SEVEN calc CLIs —
    amortize.py, affordability.py, arm_simulate.py, refi_npv.py, apr_reg_z.py,
    stress_test.py, points_breakeven.py — live ONLY in
    .claude/skills/mortgage-ops/scripts/, NOT at project-root scripts/.
    _cli_helpers.py also lives in skill folder.

    Stay-at-root files (D-06): _generate_arm_fixtures.py +
    _generate_apr_oracle_fixtures.py + scripts/hooks/*.

    SC-3 / SKLL-10 close FULLY in Phase 10 (all 7 scripts relocated together;
    Phase 6/7/8 COMPLETE per STATE.md so all 7 scripts existed at root pre-move).

    Round-2 codex HIGH 1: this test consumes the `repo_root` fixture from
    Plan 10-00 Task 3 instead of chaining four .parent calls off skill_root.
    Four chained .parent attribute accesses overshoot the repo root by one
    level — .claude/skills/mortgage-ops is only 3 levels deep, so .parents[3]
    lands above the repo. The correct equivalents are `repo_root` (this
    fixture) or `skill_root.parents[2]`.
    """
    project_scripts = repo_root / "scripts"
    skill_scripts = skill_root / "scripts"

    # Sanity: confirm repo_root fixture resolves correctly. If it doesn't,
    # everything below produces meaningless "missing file" errors instead of
    # surfacing the real bug.
    assert (repo_root / "pyproject.toml").is_file(), (
        f"repo_root fixture broken: pyproject.toml not at {repo_root}; "
        f"path arithmetic in tests/conftest.py needs review"
    )

    relocated = [
        "amortize.py",
        "affordability.py",
        "arm_simulate.py",
        "refi_npv.py",
        "apr_reg_z.py",
        "stress_test.py",
        "points_breakeven.py",
        "_cli_helpers.py",
    ]
    for name in relocated:
        assert (skill_scripts / name).is_file(), (
            f"SKLL-10 violation: {name} missing from skill folder "
            f"(expected at {skill_scripts / name})"
        )
        assert not (project_scripts / name).is_file(), (
            f"SKLL-10 + D-01 violation: {name} STILL at project-root scripts/ "
            f"(should have been relocated). Re-run Plan 10-01 Task 2."
        )

    # D-06: stay-at-root files MUST still exist at project root
    stay_at_root = ["_generate_arm_fixtures.py", "hooks/block-user-layer.py"]
    for name in stay_at_root:
        assert (project_scripts / name).is_file(), (
            f"D-06 violation: {name} should remain at project-root scripts/ "
            f"(it is dev tooling, not a user-facing CLI)"
        )

    # D-06: stay-at-root files MUST NOT have been duplicated to skill folder
    for name in stay_at_root:
        assert not (skill_scripts / name).exists(), (
            f"D-06 violation: {name} should NOT exist in skill folder"
        )


# ---------------------------------------------------------------------------
# SKLL-11 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


def test_skill_md_shell_out_doctrine(skill_root: Path) -> None:
    """SKLL-11 + ROADMAP SC-5 + UI-SPEC §g: SKILL.md instructs Claude to ALWAYS shell out for math; never compute inline."""
    text = (skill_root / "SKILL.md").read_text()
    # The exact substring is placed by Plan 10-02 Task 2; assert literal presence.
    canonical = "ALWAYS shell out to scripts/ for math; NEVER compute numbers inline."
    assert canonical in text, (
        f"SKLL-11 violation: substring not found in SKILL.md.\n"
        f"Expected: {canonical!r}\n"
        f"This is the load-bearing math-discipline doctrine; if you reword it, "
        f"reword test+SKILL.md together to keep the contract auditable."
    )


# ---------------------------------------------------------------------------
# SKLL-12 (1 stub) — flipped in Wave 5; per webapp-testing exemplar doctrine
# ---------------------------------------------------------------------------


def test_each_script_has_help_and_doctrine_documented(skill_root: Path) -> None:
    """SKLL-12 + ROADMAP SC-5 + webapp-testing exemplar: each of the SEVEN
    relocated calc scripts has a working `--help` (D-18 fast --help inherited
    from Phase 3) AND SKILL.md has the run-help-first doctrine substring.

    Round-2 codex MEDIUM 6: prior draft only ran --help for 3 of 7 scripts
    (amortize, affordability, arm_simulate) and the commit message claimed
    SKLL-12 closure. That overstates coverage. This Wave 5 test runs --help
    for all 7 relocated calc scripts (amortize, affordability, arm_simulate,
    refi_npv, apr_reg_z, stress_test, points_breakeven). _cli_helpers.py is
    NOT in the list — it has no argparse main."""
    text = (skill_root / "SKILL.md").read_text()
    # Doctrine substring (paraphrased from webapp-testing per Plan 10-02 Task 2).
    assert "run `--help` first" in text or "Always run scripts with `--help` first" in text, (
        "SKLL-12: SKILL.md must instruct 'run --help first; do not read source' "
        "(doctrine lifted from anthropics/skills/skills/webapp-testing/SKILL.md per RESEARCH §b)"
    )

    # Each of the 7 relocated user-facing calc scripts must --help exit 0
    relocated = [
        "amortize.py",
        "affordability.py",
        "arm_simulate.py",
        "refi_npv.py",
        "apr_reg_z.py",
        "stress_test.py",
        "points_breakeven.py",
    ]
    for name in relocated:
        script = skill_root / "scripts" / name
        assert script.is_file(), (
            f"{name} missing from skill folder (Plan 10-01 should have relocated)"
        )
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, (
            f"SKLL-12: {name} --help failed (exit {result.returncode}). "
            f"stderr: {result.stderr[:500]}"
        )
        # --help output should mention "--input" (the JSON-in CLI shape) — sanity check
        assert "--input" in result.stdout or "--input" in result.stderr, (
            f"{name} --help should document the --input flag"
        )


# ---------------------------------------------------------------------------
# SKLL-13 (2 stubs per D-13-05) — Phase 10 CLOSES SKLL-13. NOT deferred.
# Per CONTEXT.md D-13-01..05: modes/_shared.md ships a "Save Report" step
# that writes reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md and persists via
# `node orchestration/db-write.mjs insert-report --scenario-id <id> --file
# <path>` (REAL Phase 9 CLI per orchestration/db-write.mjs:296-310). Wave 5
# flips both. NOTE: the `reports` table schema (orchestration/init-db.mjs
# lines 76-82) is `(id, scenario_id, markdown_blob, generated_at)` — NO
# filename column. The file on disk IS the durable filename anchor;
# persistence stores the markdown body + the scenario_id link.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-03 ships Save Report step in _shared.md (D-13-01..05); Plan 10-05 wires assertion (modes/_shared.md grep for the real CLI invocation)",
)
def test_report_filename_format(skill_root: Path) -> None:
    """SKLL-13 + D-13-02: report filenames follow reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md
    convention (3-digit zero-padded sequence, mode slug from {evaluate, compare,
    refinance, affordability, stress, amortize, arm}, ISO date). Wave 5 wires
    by parsing modes/_shared.md for the convention regex. Plan 10-06 adds an
    end-to-end smoke that actually writes a report file under the convention."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-03 ships db-write.mjs insert-report integration (D-13-04); Plan 10-05 wires assertion (Plan 10-06 adds end-to-end smoke)",
)
def test_report_persisted_to_duckdb(skill_root: Path) -> None:
    """SKLL-13 + D-13-04: after writing reports/{NNN}-{mode}-{date}.md, the
    skill calls `node orchestration/db-write.mjs insert-report --scenario-id
    <int> --file <path>` (the REAL Phase 9 CLI per orchestration/db-write.mjs
    usage block lines 296-310). The reports table schema has no filename
    column — the persistence step stores `(scenario_id, markdown_blob)` and
    the file on disk is the durable filename anchor.

    Wave 5 ships the unit-level assertion that modes/_shared.md documents the
    REAL CLI invocation literal (`node orchestration/db-write.mjs
    insert-report`). Plan 10-06 ships an end-to-end smoke that actually
    invokes init-db + insert-loan + insert-scenario + insert-report and
    queries `SELECT scenario_id, markdown_blob FROM reports WHERE
    scenario_id = ?` returning 1 row."""
    pytest.fail("Wave 0 stub")
