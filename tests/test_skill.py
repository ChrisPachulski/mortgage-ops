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

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# SKLL-01 (2 stubs) — flipped in Wave 5 (CI tests). Uses count_tokens helper
# from Wave 0; threshold per D-02.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships SKILL.md; Plan 10-05 wires assertion",
)
def test_skill_md_under_token_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1: SKILL.md ≤ 4500 cl100k tokens (10% under 5000 Anthropic spec)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships SKILL.md; Plan 10-05 wires assertion",
)
def test_skill_md_under_line_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1: SKILL.md ≤ 500 lines."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-02 (1 stub) — flipped in Wave 5; per D-12 grep-assert mode-routing
# in first 200 lines.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships routing skeleton; Plan 10-05 wires assertion",
)
def test_skill_routing_in_first_200_lines(skill_root: Path) -> None:
    """SKLL-02 + D-12: '## Mode Routing' + 7 mode names appear in first 200 lines of SKILL.md."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-03 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships frontmatter; Plan 10-05 wires assertion",
)
def test_skill_md_frontmatter_required_fields(skill_root: Path) -> None:
    """SKLL-03 + ROADMAP SC-2: frontmatter has name, description, license, compatibility."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-04 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships LICENSE.txt; Plan 10-05 wires assertion",
)
def test_license_txt_exists_in_skill_folder(skill_root: Path) -> None:
    """SKLL-04 + ROADMAP SC-2: LICENSE.txt bundled inside skill folder (D-04 = MIT default)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-05 (1 stub) — flipped in Wave 5; parametrized over 7 modes
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-03 ships modes/*.md; Plan 10-05 wires parametrize",
)
def test_modes_exist(skill_root: Path) -> None:
    """SKLL-05 + ROADMAP SC-4: 7 mode files (evaluate, compare, refinance, affordability,
    stress, amortize, arm) exist under modes/."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-06 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-03 ships modes/_shared.md; Plan 10-05 wires assertion",
)
def test_shared_mode_has_required_sections(skill_root: Path) -> None:
    """SKLL-06 + ROADMAP SC-4: modes/_shared.md defines scoring + report structure
    (career-ops pattern + UI-SPEC §i)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-07 (1 stub) — flipped in Wave 5; per D-07 .example.md pattern
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-03 ships .example.md template + gitignore; Plan 10-05 wires assertion",
)
def test_profile_md_user_layer_gitignored(skill_root: Path) -> None:
    """SKLL-07 + D-07: modes/_profile.md gitignored AND modes/_profile.example.md committed."""
    pytest.fail("Wave 0 stub")


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


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-04 ships references/*.md; Plan 10-05 wires parametrize",
)
def test_references_exist(skill_root: Path) -> None:
    """SKLL-08 + ROADMAP SC-5: 9 reference files (amortization-formulas, apr-reg-z,
    arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi,
    tax-deductibility, spreadsheet-conventions) exist under references/."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-09 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships progressive-disclosure rule; Plan 10-05 wires assertion",
)
def test_skill_md_documents_progressive_disclosure(skill_root: Path) -> None:
    """SKLL-09 + ROADMAP SC-5 + D-09: SKILL.md contains a topic→reference table
    for on-demand reference loading."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-10 (1 stub) — flipped in Wave 1 (relocation); per D-01 + D-06 + D-08.
# Asserts ALL SEVEN calc scripts live INSIDE the skill folder. Phase 6/7/8
# scripts (refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py)
# are confirmed shipped per STATE.md (Phase 6/7/8 COMPLETE) so all 7 scripts
# can be relocated together in Plan 10-01 Task 2.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-01 relocates 7 calc scripts (amortize, affordability, arm_simulate, refi_npv, apr_reg_z, stress_test, points_breakeven) + _cli_helpers; flipped same wave",
)
def test_seven_scripts_in_skill_folder_only(skill_root: Path) -> None:
    """SKLL-10 + ROADMAP SC-3 + D-01 + D-06 + D-08: ALL SEVEN calc scripts —
    amortize.py, affordability.py, arm_simulate.py, refi_npv.py, apr_reg_z.py,
    stress_test.py, points_breakeven.py — live ONLY in
    .claude/skills/mortgage-ops/scripts/, NOT at project root scripts/.
    _cli_helpers.py also relocates with them.

    _generate_arm_fixtures.py + scripts/hooks/ STAY at project root (D-06,
    dev tooling, not user-facing CLIs).

    STATE.md confirms Phases 6/7/8 COMPLETE — all 7 scripts exist at project
    root and CAN be relocated together. SC-3 / SKLL-10 close FULLY in Phase 10."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-11 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships math-discipline doctrine in SKILL.md; Plan 10-05 wires assertion",
)
def test_skill_md_shell_out_doctrine(skill_root: Path) -> None:
    """SKLL-11 + ROADMAP SC-5 + UI-SPEC §g: SKILL.md contains the literal substring
    'ALWAYS shell out' (or near-equivalent — assert by regex match per UI-SPEC
    narration template)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-12 (1 stub) — flipped in Wave 5; per webapp-testing exemplar doctrine
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Wave 0 stub — Plan 10-02 ships --help-first doctrine; Plan 10-05 wires assertion",
)
def test_each_script_has_help_and_doctrine_documented(skill_root: Path) -> None:
    """SKLL-12 + ROADMAP SC-5: each relocated script's `--help` exits 0 in < 200ms,
    AND SKILL.md contains 'run --help first; do not read source' (or near-equivalent
    literal text). Wave 5 covers all 7 relocated calc scripts (Round-2 codex MEDIUM
    6: SKLL-12 closure NOT split between waves)."""
    pytest.fail("Wave 0 stub")


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
