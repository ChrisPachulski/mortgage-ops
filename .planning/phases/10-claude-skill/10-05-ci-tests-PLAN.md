---
phase: 10
plan: 05
type: execute
wave: 5
depends_on:
  - "10-00"
  - "10-01"
  - "10-02"
  - "10-03"
  - "10-04"
files_modified:
  - tests/test_skill.py
autonomous: true
requirements:
  - SKLL-01
  - SKLL-02
  - SKLL-03
  - SKLL-04
  - SKLL-05
  - SKLL-06
  - SKLL-07
  - SKLL-08
  - SKLL-09
  - SKLL-11
  - SKLL-12
  - SKLL-13
tags:
  - phase-10
  - claude-skill
  - ci-tests
  - xfail-flip
  - skll-01
  - skll-02
  - skll-03
  - skll-04
  - skll-05
  - skll-06
  - skll-07
  - skll-08
  - skll-09
  - skll-11
  - skll-12
  - skll-13
must_haves:
  truths:
    - "All Phase 10 xfail stubs from Wave 0 (Plan 10-00) are flipped to PASS in this wave — including the TWO SKLL-13 stubs per D-13-01..D-13-05 (Phase 10 closes SKLL-13; NOT deferred to Phase 9)"
    - "Test SKLL-01 token budget asserts ≤ 4500 cl100k tokens via tests._skill_helpers.count_tokens (D-02 enforcement)"
    - "Test SKLL-01 line budget asserts ≤ 500 lines"
    - "Test SKLL-02 grep-asserts '## Mode Routing' + 7 mode names appear in first 200 lines (D-12 enforcement)"
    - "Test SKLL-03 parses YAML frontmatter; asserts 4 keys (name, description, license, compatibility) + spec constraints"
    - "Test SKLL-04 asserts LICENSE.txt exists in skill folder"
    - "Test SKLL-05 parametrized over 7 modes asserts each modes/{name}.md exists"
    - "Test SKLL-06 asserts modes/_shared.md contains the 12 mandatory section headings (9 UI-SPEC §i + Profile Loading + Output Formatting + Save Report per D-13/D-NUM/D-PROF-04) AND cites at least one D-NUM example token per directive ($1,264.14 for D-NUM-01, 6.500% for D-NUM-02, 43.0% for D-NUM-03, `<n> bps (<x>.<yy>%)` regex for D-NUM-04) — Round-2 codex MEDIUM 7"
    - "Test SKLL-07 asserts modes/_profile.md is gitignored AND modes/_profile.example.md is committed; the test consumes the `repo_root` fixture from Plan 10-00 Task 3 (Round-2 codex HIGH 1: `skill_root.parent.parent.parent.parent` overshoots repo root by one level)"
    - "NEW Test test_profile_example_md_has_exact_four_keys (D-PROF-01 + D-PROF-02): parses _profile.example.md YAML body and asserts EXACTLY four top-level keys (verbosity, citation_density, save_report, disambiguation); NO extras allowed"
    - "Test SKLL-08 parametrized over 9 references asserts each references/{name}.md exists"
    - "Test SKLL-09 asserts SKILL.md contains the topic→reference table (substring match)"
    - "Test SKLL-11 asserts SKILL.md contains the literal 'ALWAYS shell out' doctrine substring"
    - "Test SKLL-12 asserts each of the 7 RELOCATED calc scripts (amortize, affordability, arm_simulate, refi_npv, apr_reg_z, stress_test, points_breakeven) has a working --help (subprocess; D-18 fast --help) AND SKILL.md contains the run-help-first substring. Round-2 codex MEDIUM 6: 7-script audit closes in Wave 5; not split with Wave 6."
    - "NEW Test test_skll_13_report_filename_format (D-13-02): asserts a saved report filename matches `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md` (or asserts the convention is documented in modes/_shared.md verbatim with parseable regex)"
    - "NEW Test test_skll_13_report_persisted_to_duckdb (D-13-04): asserts the literal REAL CLI invocation `node orchestration/db-write.mjs insert-report --scenario-id` appears in modes/_shared.md (per orchestration/db-write.mjs:296-310; Round-2 codex HIGH 2). Forbidden-substring guards block the fictional `--insert-report --json` and `db-write.mjs --query` flag forms. The reports table per init-db.mjs has no `filename` column — Plan 10-06 end-to-end smoke verifies row presence by `scenario_id`, not `filename`."
    - "Bonus test asserts arm-mechanics.md byte-equality between project root and skill folder (drift protection per 10-PATTERNS CRITICAL #4)"
    - "NEW Bonus test asserts refi-npv.md byte-equality between project root and skill folder (Plan 10-04 Task 2 byte-lift; mirrors arm-mechanics pattern)"
    - "NEW Bonus test asserts apr-reg-z.md byte-equality between project root and skill folder (Plan 10-04 Task 2 byte-lift; mirrors arm-mechanics pattern)"
    - "Bonus test asserts 6-key Pydantic envelope still works for relocated scripts (renamed test_amortize_envelope_smoke OR expanded to cover all relocated scripts — codex MEDIUM concern: prior test name overstated coverage)"
    - "REVISED Bonus test test_profile_md_write_attempt_blocked (Round-2 codex HIGH 3): invokes `python scripts/hooks/block-user-layer.py .claude/skills/mortgage-ops/modes/_profile.md` with the candidate path AS argv[1] (matching the hook's `argv[1:]` interface verified by reading scripts/hooks/block-user-layer.py:46-67), asserts exit code 1 + stderr names the offending file, plus a positive-control invocation with clean paths exits 0. No git staging is needed — that approach was a Round-1 misread of the hook's actual interface."
    - "REVISED Bonus test test_modes_stress_md_subagent_forward_link: asserts modes/stress.md contains LITERAL `if it exists` AND LITERAL path `.claude/agents/stress-test-agent.md` (per D-SUBA-FW-02)"
    - "NEW Bonus test test_skill_md_subagent_section_present: asserts SKILL.md contains the literal heading `## Subagents (Phase 11)` AND all THREE filenames (`amortization-agent`, `refi-npv-agent`, `stress-test-agent`) per D-SUBA-FW-01"
    - "Full pytest suite ≥ 549 baseline + Phase 10 net additions; SKLL-13 is CLOSED (not xfail) per D-13-01..D-13-05"
    - "Wave 5 ships explicit import housekeeping at the start of Task 1: `import re`, `import subprocess`, `import sys`, `import yaml`, `from tests._skill_helpers import count_tokens` re-added at module level (Round-2 codex HIGH 5; deferred from Wave 0 for ruff F401 hygiene). `ruff check tests/test_skill.py` returns 0 errors at Wave 5 commit time."
    - "All Wave 5 tests that need the repo root use the `repo_root` fixture from Plan 10-00 Task 3 (Round-2 codex HIGH 1: NOT `skill_root.parent.parent.parent.parent`, which overshoots by one level since .claude/skills/mortgage-ops is only 3 levels deep)."
    - "All Wave 5 SKLL-13 assertions reference the REAL Phase 9 CLI from `orchestration/db-write.mjs:296-310` (`insert-report --scenario-id <int> --file <path>` and `query --sql \"...\"`); fictional flag forms (`--insert-report --json`, `--query \"...\"`) are forbidden by guard assertions (Round-2 codex HIGH 2)."
  artifacts:
    - path: "tests/test_skill.py"
      provides: "Wave 5 flips all SKLL-01..12 xfails to real assertions; adds 4 bonus tests (byte-equal mirror, envelope smoke, _profile.md write-block, subagent forward-link)"
      contains: "ENCODER = "
  key_links:
    - from: "tests/test_skill.py SKLL-01 token assertion"
      to: ".claude/skills/mortgage-ops/SKILL.md"
      via: "tests._skill_helpers.count_tokens (Wave 0) reads SKILL.md (Wave 2) bytes"
      pattern: "count_tokens"
    - from: "tests/test_skill.py SKLL-08 parametrize"
      to: ".claude/skills/mortgage-ops/references/*.md (Wave 4 9 files)"
      via: "@pytest.mark.parametrize over 9 expected reference filenames"
      pattern: "EXPECTED_REFERENCES"
    - from: "Bonus arm-mechanics drift test"
      to: "Wave 4 byte-identical copy of arm-mechanics.md"
      via: "byte-equality assertion (cp not symlink per CRITICAL #4)"
      pattern: "read_bytes"
---

<objective>
Flip all Wave 0 xfail stubs in `tests/test_skill.py` to real assertions, plus add 4 bonus cross-cutting tests (drift protection for arm-mechanics, 6-key envelope smoke for relocated scripts, User Layer write-block for _profile.md, Phase 11 subagent forward-link substring in modes/stress.md).

This is the "wire the contracts" wave — Waves 1-4 shipped the artifacts (skill folder, scripts, SKILL.md, modes/, references/); Wave 5 turns the scaffold into binding CI. Every xfail removed in this wave permanently gates the SKLL-XX requirement at PR time.

Closes SKLL-01..09 + SKLL-11..13 (Phase 10 closes SKLL-13 per CONTEXT.md
D-13-01..D-13-05 — modes/_shared.md ships the Save Report step writing
reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md and invoking
node orchestration/db-write.mjs --insert-report; Wave 6 adds end-to-end
smoke). SKLL-10 already closed in Wave 1.

Purpose: Without Wave 5 the entire Phase 10 surface ships as XFAIL stubs — the artifacts exist but no CI prevents future drift. After Wave 5, future SKILL.md edits that violate token budget, drop the doctrine substring, or remove a reference file FAIL CI loudly.

Output: 1 test file with ~12 xfails removed + ~7 new bonus tests added;
pre-existing 549 baseline + 16 Wave 0 stubs become ~589 PASS + 0 Phase 10
xfails (SKLL-13 closed in Wave 5 FLIP-B + FLIP-C; final end-to-end
runtime smoke lands in Wave 6).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/10-claude-skill/10-PATTERNS.md
@.planning/phases/10-claude-skill/10-RESEARCH.md
@.planning/phases/10-claude-skill/10-UI-SPEC.md
@CLAUDE.md
@tests/test_skill.py
@tests/_skill_helpers.py
@.claude/skills/mortgage-ops/SKILL.md
@.claude/skills/mortgage-ops/LICENSE.txt
@.claude/skills/mortgage-ops/modes/_shared.md
@.claude/skills/mortgage-ops/modes/_profile.example.md

<interfaces>
LOCKED DECISIONS:
- D-02 = ≤ 4500 cl100k tokens enforcement
- D-12 = SKLL-02 = grep-assert `## Mode Routing` heading + 7 mode names in first 200 lines
- D-13-01..D-13-05 = SKLL-13 closes IN PHASE 10 (NOT deferred). Wave 5 flips both SKLL-13 stubs to PASS.
- D-PROF-01 + D-PROF-02 = `_profile.example.md` has EXACTLY 4 top-level YAML keys.
- D-SUBA-FW-01 = SKILL.md has `## Subagents (Phase 11)` section naming all 3 agent filenames.
- D-SUBA-FW-02 = `modes/stress.md` carries existence-check seam (literal `if it exists` + path `.claude/agents/stress-test-agent.md`).
- D-NUM-01..06 = `_shared.md` has Output Formatting section.

Wave 0 (Plan 10-00) created these xfail stubs (paste verbatim test names — Wave 5 flips each):
1. test_skill_md_under_token_budget — SKLL-01 token (Wave 5 wires)
2. test_skill_md_under_line_budget — SKLL-01 line (Wave 5 wires)
3. test_skill_routing_in_first_200_lines — SKLL-02 (Wave 5 wires)
4. test_skill_md_frontmatter_required_fields — SKLL-03 (Wave 5 wires)
5. test_license_txt_exists_in_skill_folder — SKLL-04 (Wave 5 wires)
6. test_modes_exist — SKLL-05 (Wave 5 wires; convert to parametrize)
7. test_shared_mode_has_required_sections — SKLL-06 (Wave 5 wires)
8. test_profile_md_user_layer_gitignored — SKLL-07 (Wave 5 wires)
9. test_profile_example_md_has_exact_four_keys — D-PROF-01 (Wave 5 wires) — NEW per CONTEXT.md
10. test_references_exist — SKLL-08 (Wave 5 wires; convert to parametrize)
11. test_skill_md_documents_progressive_disclosure — SKLL-09 (Wave 5 wires)
12. test_seven_scripts_in_skill_folder_only — SKLL-10 (ALREADY FLIPPED in Wave 1; do NOT re-flip)
13. test_skill_md_shell_out_doctrine — SKLL-11 (Wave 5 wires)
14. test_each_script_has_help_and_doctrine_documented — SKLL-12 (Wave 5 wires)
15. test_report_filename_format — SKLL-13 (Wave 5 wires per D-13-02; FLIPS to PASS)
16. test_report_persisted_to_duckdb — SKLL-13 (Wave 5 wires per D-13-04; FLIPS to PASS — Plan 10-06 adds end-to-end smoke)

Wave 5 ALSO adds these BONUS tests:
- test_arm_mechanics_skill_mirror_in_sync — drift protection (byte-equality) for arm-mechanics.md
- test_refi_npv_skill_mirror_in_sync — NEW: drift protection for refi-npv.md (Plan 10-04 Task 2 byte-lift)
- test_apr_reg_z_skill_mirror_in_sync — NEW: drift protection for apr-reg-z.md (Plan 10-04 Task 2 byte-lift)
- test_amortize_envelope_smoke OR test_relocated_scripts_envelope_smoke — 6-key envelope smoke (renamed honestly per codex MEDIUM concern OR expanded coverage)
- test_profile_md_write_attempt_blocked — REVISED: real test using temp _profile.md + try/finally (NOT just grep on hook source)
- test_modes_stress_md_subagent_forward_link — REVISED: asserts D-SUBA-FW-02 literal phrases (`if it exists` + path `.claude/agents/stress-test-agent.md`)
- test_skill_md_subagent_section_present — NEW: asserts D-SUBA-FW-01 (`## Subagents (Phase 11)` heading + all 3 agent filenames in SKILL.md)

Test pattern for the parametrized SKLL-05 / SKLL-08 tests (10-PATTERNS `tests/test_skill_structure.py` section + 10-RESEARCH §"Test pattern"):

```python
EXPECTED_MODES = {"evaluate", "compare", "refinance", "affordability", "stress", "amortize", "arm"}
EXPECTED_REFERENCES = {
    "amortization-formulas", "apr-reg-z", "arm-mechanics", "refi-npv",
    "affordability-rules", "gse-limits", "mip-pmi", "tax-deductibility",
    "spreadsheet-conventions",
}

@pytest.mark.parametrize("mode", sorted(EXPECTED_MODES))
def test_mode_file_exists(mode: str, skill_root: Path) -> None:
    assert (skill_root / "modes" / f"{mode}.md").exists(), ...

@pytest.mark.parametrize("ref", sorted(EXPECTED_REFERENCES))
def test_reference_file_exists(ref: str, skill_root: Path) -> None:
    assert (skill_root / "references" / f"{ref}.md").exists(), ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Flip SKLL-01..04 xfails (token + line + routing + frontmatter + LICENSE.txt)</name>
  <files>tests/test_skill.py</files>
  <read_first>
    tests/test_skill.py — find the 5 stubs to flip;
    10-PATTERNS `tests/test_skill_structure.py` section — verbatim assertion bodies;
    10-RESEARCH §"Pinned Oracle Examples" Oracle 1, 2, 4
  </read_first>
  <action>
**STEP 0 — Import housekeeping (Round-2 codex HIGH 5).** Wave 0 (Plan 10-00 Task 4) deliberately deferred `re`, `subprocess`, `sys`, `yaml`, and the `count_tokens` helper out of `tests/test_skill.py` module-level imports to keep `ruff check` F401-clean while every body was just `pytest.fail("Wave 0 stub")`. Wave 5 (this plan) flips assertions that USE all five names. Before flipping any decorator, ADD these imports at the top of `tests/test_skill.py` (after `from pathlib import Path` + `import pytest` block):

```python
import re
import subprocess
import sys

import yaml

from tests._skill_helpers import count_tokens
```

Verify with `ruff check tests/test_skill.py` after the assertions are flipped — there must be ZERO F401 errors at Wave 5 commit time. Each added import MUST be consumed by at least one flipped assertion in Tasks 1-4 below.

If a future Wave 5 revision drops one of the assertions that consume these imports, the matching import MUST also be removed (or `ruff check` will fail F401). The Round-2 codex HIGH 5 contract is: deferred imports return at module level the moment the bodies that need them are wired in.

For each of the 5 Wave 0 stubs in this task, REMOVE the `@pytest.mark.xfail(...)` decorator and REPLACE the body `pytest.fail("Wave 0 stub")` with the real assertion. Use Edit (not Write) to preserve everything else in tests/test_skill.py.

STUB 1 — test_skill_md_under_token_budget (SKLL-01 token):
```python
def test_skill_md_under_token_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1 + D-02: SKILL.md ≤ 4500 cl100k tokens (10% under 5000 Anthropic spec)."""
    skill_md = (skill_root / "SKILL.md").read_text()
    n_tokens = count_tokens(skill_md)
    assert n_tokens <= 4500, (
        f"SKILL.md is {n_tokens} cl100k tokens (budget 4500 = 5000 Anthropic spec − 10% margin per D-02). "
        f"Trim or move detail into modes/ or references/ (progressive disclosure SKLL-09). "
        f"Compaction re-attach budget is 5000 tokens; tokenizer drift would breach it."
    )
```

STUB 2 — test_skill_md_under_line_budget (SKLL-01 line):
```python
def test_skill_md_under_line_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1: SKILL.md ≤ 500 lines per agentskills.io guidance."""
    n_lines = (skill_root / "SKILL.md").read_text().count("\n") + 1
    assert n_lines <= 500, f"SKILL.md is {n_lines} lines (cap 500)"
```

STUB 3 — test_skill_routing_in_first_200_lines (SKLL-02 + D-12):
```python
def test_skill_routing_in_first_200_lines(skill_root: Path) -> None:
    """SKLL-02 + D-12: '## Mode Routing' heading + 7 mode names appear in first 200 lines."""
    head = "\n".join((skill_root / "SKILL.md").read_text().splitlines()[:200])
    assert "## Mode Routing" in head, (
        "SKLL-02: '## Mode Routing' must appear in first 200 lines — survives "
        "Anthropic compaction re-attach (5000-token / first-200-line window)."
    )
    for mode in ("evaluate", "compare", "refinance", "affordability", "stress", "amortize", "arm"):
        assert mode in head, f"SKLL-02: mode '{mode}' not dispatched in first 200 lines"
```

STUB 4 — test_skill_md_frontmatter_required_fields (SKLL-03):
```python
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
```

STUB 5 — test_license_txt_exists_in_skill_folder (SKLL-04):
```python
def test_license_txt_exists_in_skill_folder(skill_root: Path) -> None:
    """SKLL-04 + ROADMAP SC-2 + D-04: LICENSE.txt bundled inside skill folder; references MIT per default."""
    license_path = skill_root / "LICENSE.txt"
    assert license_path.is_file(), f"SKLL-04: LICENSE.txt missing from {license_path}"
    text = license_path.read_text()
    assert "MIT License" in text or "Apache" in text or "BSD" in text or "Copyright" in text, (
        "LICENSE.txt should contain a recognizable license header"
    )
```

REMOVE the `@pytest.mark.xfail(...)` decorator above each of these 5 stubs.

DO NOT touch any other test in this task — Tasks 2-4 handle the rest.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_skill.py::test_skill_md_under_token_budget tests/test_skill.py::test_skill_md_under_line_budget tests/test_skill.py::test_skill_routing_in_first_200_lines tests/test_skill.py::test_skill_md_frontmatter_required_fields tests/test_skill.py::test_license_txt_exists_in_skill_folder -v</automated>
  </verify>
  <acceptance_criteria>
- All 5 specified tests PASS (no xfail decorator on any)
- `grep -c '@pytest.mark.xfail' tests/test_skill.py` decreased by 5 vs Wave 0 baseline (was ~13, now ~8)
- mypy --strict + ruff clean across tests/test_skill.py
  </acceptance_criteria>
  <done>
    SKLL-01..04 closed; 5 xfails flipped to PASS.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip SKLL-05..09 xfails + convert to parametrize (modes + _shared + _profile + references + progressive disclosure)</name>
  <files>tests/test_skill.py</files>
  <read_first>
    tests/test_skill.py — find the 5 stubs;
    10-RESEARCH §"Test pattern" — parametrize-over-glob meta-test idiom;
    10-UI-SPEC §i — _shared.md mandatory section names;
    10-PATTERNS — `EXPECTED_MODES` + `EXPECTED_REFERENCES` constants
  </read_first>
  <action>
First, add module-level constants (after the existing imports, before the test functions):

```python
# Wave 5 (Plan 10-05) parametrize sources
EXPECTED_MODES: frozenset[str] = frozenset({
    "evaluate", "compare", "refinance", "affordability",
    "stress", "amortize", "arm",
})
"""SKLL-05 + ROADMAP SC-4: 7 mode files."""

EXPECTED_REFERENCES: frozenset[str] = frozenset({
    "amortization-formulas", "apr-reg-z", "arm-mechanics", "refi-npv",
    "affordability-rules", "gse-limits", "mip-pmi", "tax-deductibility",
    "spreadsheet-conventions",
})
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
section headings. Earlier draft only listed 9 (UI-SPEC §i baseline) but
the CONTEXT.md must-have at Plan 10-03 line ~54 mandates 12 sections
(adding Profile Loading per D-PROF-04, Output Formatting per D-NUM-01..06,
Save Report per D-13-01..05). The CI assertion here matches the must-have."""

# D-NUM-01..06 example tokens — the Output Formatting section MUST cite at
# least one example per directive (Round-2 codex MEDIUM 7).
SHARED_MD_DNUM_EXAMPLES: tuple[str, ...] = (
    "$1,264.14",      # D-NUM-01 money: 2 decimals + comma + $ prefix
    "6.500%",         # D-NUM-02 rate: 3 decimals + trailing zeros + %
    "43.0%",          # D-NUM-03 ratio (DTI / LTV / CLTV): 1 decimal + %
)
"""D-NUM-01..06 example tokens (Round-2 codex MEDIUM 7). The Output
Formatting section MUST cite at least one example per directive so the
display contract is auditable. ARM bps formatting (D-NUM-04) is matched
separately by the existing `bps (` substring (e.g. `200 bps (2.00%)`)."""
```

Then flip each stub:

STUB 6 — REPLACE test_modes_exist with PARAMETRIZED test_mode_file_exists (REMOVE old; ADD new):
```python
@pytest.mark.parametrize("mode", sorted(EXPECTED_MODES))
def test_mode_file_exists(mode: str, skill_root: Path) -> None:
    """SKLL-05 + ROADMAP SC-4: every expected mode has a modes/{mode}.md file."""
    p = skill_root / "modes" / f"{mode}.md"
    assert p.exists(), f"SKLL-05 mode file missing: modes/{mode}.md"
```

STUB 7 — test_shared_mode_has_required_sections (SKLL-06; Round-2 codex MEDIUM 7: assert all 12 sections + D-NUM example tokens, matching the Plan 10-03 must-have):
```python
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
```

STUB 8 — test_profile_md_user_layer_gitignored (SKLL-07 + D-07). Consume the `repo_root` fixture from Plan 10-00 Task 3 (Round-2 codex HIGH 1: `skill_root.parent.parent.parent.parent` overshoots the repo root by one level — `.claude/skills/mortgage-ops` is only 3 levels deep):
```python
def test_profile_md_user_layer_gitignored(skill_root: Path, repo_root: Path) -> None:
    """SKLL-07 + D-07: modes/_profile.md is gitignored AND modes/_profile.example.md is committed."""
    gitignore = (repo_root / ".gitignore").read_text()
    profile_md_pattern = ".claude/skills/mortgage-ops/modes/_profile.md"
    assert profile_md_pattern in gitignore, (
        f"SKLL-07: .gitignore missing pattern '{profile_md_pattern}' "
        f"(modes/_profile.md is User Layer per DATA_CONTRACT.md)"
    )
    example = skill_root / "modes" / "_profile.example.md"
    assert example.is_file(), (
        f"SKLL-07 + D-07: schema skeleton must exist at {example}"
    )
```

STUB 9 — REPLACE test_references_exist with PARAMETRIZED test_reference_file_exists (REMOVE old; ADD new):
```python
@pytest.mark.parametrize("ref", sorted(EXPECTED_REFERENCES))
def test_reference_file_exists(ref: str, skill_root: Path) -> None:
    """SKLL-08 + ROADMAP SC-5: all 9 reference docs are bundled."""
    p = skill_root / "references" / f"{ref}.md"
    assert p.is_file(), f"SKLL-08 reference missing: references/{ref}.md"
```

STUB 10 — test_skill_md_documents_progressive_disclosure (SKLL-09 + D-09):
```python
def test_skill_md_documents_progressive_disclosure(skill_root: Path) -> None:
    """SKLL-09 + D-09 + ROADMAP SC-5: SKILL.md contains topic→reference table for on-demand reference loading."""
    text = (skill_root / "SKILL.md").read_text()
    assert "load on demand" in text.lower() or "progressive disclosure" in text.lower() or "on demand" in text.lower(), (
        "SKLL-09: SKILL.md must mention on-demand reference loading (D-09 progressive disclosure rule)"
    )
    # All 9 reference filenames must appear in SKILL.md (the topic→reference table)
    for ref in EXPECTED_REFERENCES:
        assert ref in text, f"SKLL-09: reference '{ref}' not listed in SKILL.md topic→reference table"
```

REMOVE all 5 corresponding `@pytest.mark.xfail(...)` decorators.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_skill.py::test_mode_file_exists tests/test_skill.py::test_shared_mode_has_required_sections tests/test_skill.py::test_profile_md_user_layer_gitignored tests/test_skill.py::test_reference_file_exists tests/test_skill.py::test_skill_md_documents_progressive_disclosure -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
- test_mode_file_exists collects 7 cases (one per mode) and ALL pass
- test_reference_file_exists collects 9 cases (one per reference) and ALL pass
- test_shared_mode_has_required_sections passes (all 9 sections found)
- test_profile_md_user_layer_gitignored passes (gitignore + .example.md both verified)
- test_skill_md_documents_progressive_disclosure passes (substring + 9 ref names found)
- Total xfail count decreased by 5 (Wave 0 stubs converted; parametrize doesn't count as new xfail)
  </acceptance_criteria>
  <done>
    SKLL-05..09 closed; modes + references parametrize-cased; progressive disclosure verified.
  </done>
</task>

<task type="auto">
  <name>Task 3: Flip SKLL-11 + SKLL-12 xfails (always-shell-out + run-help-first doctrines)</name>
  <files>tests/test_skill.py</files>
  <read_first>
    tests/test_skill.py — find the 2 stubs;
    .claude/skills/mortgage-ops/SKILL.md — the doctrine substrings (Wave 2 placed them);
    .claude/skills/mortgage-ops/scripts/*.py --help (verify --help works for the 4 relocated scripts)
  </read_first>
  <action>
STUB 11 — test_skill_md_shell_out_doctrine (SKLL-11 + UI-SPEC §g):
```python
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
```

STUB 12 — test_each_script_has_help_and_doctrine_documented (SKLL-12). Round-2 codex MEDIUM 6: SKLL-12 closure asserts `--help` exits 0 for ALL SEVEN relocated calc scripts in this single Wave 5 test. No split between Wave 5 and Wave 6 — the 7-script audit closes here:
```python
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
        assert script.is_file(), f"{name} missing from skill folder (Plan 10-01 should have relocated)"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"SKLL-12: {name} --help failed (exit {result.returncode}). "
            f"stderr: {result.stderr[:500]}"
        )
        # --help output should mention "--input" (the JSON-in CLI shape) — sanity check
        assert "--input" in result.stdout or "--input" in result.stderr, (
            f"{name} --help should document the --input flag"
        )
```

NOTE: `_cli_helpers.py` is NOT in the relocated list — it's an internal helper, not a user-facing CLI; it has no --help (no argparse main).

REMOVE the 2 corresponding `@pytest.mark.xfail(...)` decorators.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_skill.py::test_skill_md_shell_out_doctrine tests/test_skill.py::test_each_script_has_help_and_doctrine_documented -v</automated>
  </verify>
  <acceptance_criteria>
- test_skill_md_shell_out_doctrine PASSES (literal substring found)
- test_each_script_has_help_and_doctrine_documented PASSES (doctrine substring + 3 scripts' --help all exit 0)
- Each script's --help completes in < 10s (timeout)
  </acceptance_criteria>
  <done>
    SKLL-11 + SKLL-12 closed; doctrine substrings asserted; --help works for 3 relocated CLIs.
  </done>
</task>

<task type="auto">
  <name>Task 4: Add bonus cross-cutting tests + flip SKLL-13 stubs + flip D-PROF-01 stub (drift × 3, envelope smoke, real write-block, D-SUBA-FW-01/02, D-PROF-01)</name>
  <files>tests/test_skill.py</files>
  <read_first>
    10-PATTERNS CRITICAL #4 — drift-protection test pattern;
    10-UI-SPEC §f household.yml READ-only enforcement (parallel for _profile.md);
    10-CONTEXT.md D-SUBA-FW-01 (SKILL.md Subagents section);
    10-CONTEXT.md D-SUBA-FW-02 (modes/stress.md existence-check);
    10-CONTEXT.md D-PROF-01 + D-PROF-02 (4-key schema);
    10-CONTEXT.md D-13-01..D-13-05 (Save Report step);
    .claude/skills/mortgage-ops/scripts/amortize.py — float-in-money 6-key envelope behavior (Phase 3 WR-02 unchanged by relocation);
    scripts/hooks/block-user-layer.py — actual hook source so the write-block test can invoke it correctly
  </read_first>
  <action>
APPEND/FLIP these tests at end of tests/test_skill.py. This task addresses codex review HIGH/MEDIUM concerns 1, 2, 3, 5, 7, 8, 11 + closes SKLL-13 per D-13-01..D-13-05:

**FLIP-A — D-PROF-01 four-key schema** (test from Plan 10-00 Task 4; Round-2 codex HIGH 4 Option A producer/consumer fix: `_profile.example.md` is **pure YAML** per Plan 10-03 Task 2 — no fenced ```yaml block. Parsing the entire file body directly with `yaml.safe_load` matches the producer contract; a regex extraction of a fenced block would fail at runtime because the file has no fence):
```python
def test_profile_example_md_has_exact_four_keys(skill_root: Path) -> None:
    """D-PROF-01 + D-PROF-02 + Round-2 codex HIGH 4 Option A:
    _profile.example.md is pure YAML (no fenced block) so the
    user's `cp _profile.example.md _profile.md` produces a
    directly-parseable file. Parse the entire body and assert
    EXACTLY four top-level keys.
    """
    raw = (skill_root / "modes" / "_profile.example.md").read_text()
    assert "```yaml" not in raw, (
        "Round-2 codex HIGH 4: _profile.example.md must NOT contain a "
        "fenced ```yaml block — it must be pure YAML so the user's `cp` "
        "to _profile.md produces a yaml.safe_load-parseable file."
    )
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict), (
        "_profile.example.md must parse as a YAML mapping (D-PROF-01)."
    )
    expected = {"verbosity", "citation_density", "save_report", "disambiguation"}
    actual = set(parsed.keys())
    assert actual == expected, (
        f"D-PROF-01: must have EXACTLY 4 top-level keys {expected}; "
        f"got {actual}. Extras violate D-PROF-02."
    )
```
REMOVE the `@pytest.mark.xfail` decorator that Wave 0 placed on this stub.

NOTE on imports: this revised FLIP-A no longer imports `re` (the prior
fence-extraction body did). Other Wave 5 tests (FLIP-B `test_report_filename_format`,
SKLL-06 `test_shared_mode_has_required_sections` D-NUM-04 bps regex) still
use `re`, so the module-level `import re` from Task 1 STEP 0 stays — F401
would only fire if NO test referenced `re`, which is not the case here.

**FLIP-B — SKLL-13 report filename format** (test from Plan 10-00 Task 4):
```python
def test_report_filename_format(skill_root: Path) -> None:
    """SKLL-13 + D-13-02: Phase 10 closes SKLL-13. modes/_shared.md MUST
    document the filename convention `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md`
    so future report writes match. This test parses _shared.md for the
    convention regex pattern; Plan 10-06 adds an end-to-end smoke that
    actually writes a report and re-asserts the regex against the filename."""
    import re as _re
    shared = (skill_root / "modes" / "_shared.md").read_text()
    # Per CONTEXT.md D-13-02 the filename pattern is reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md
    # Assert _shared.md contains a literal pattern token that documents the convention.
    pattern_tokens = [
        r"reports/\{NNN:03d\}-\{mode\}-\{YYYY-MM-DD\}\.md",
        r"reports/\{NNN\}-\{mode\}-\{YYYY-MM-DD\}\.md",
        r"reports/042-stress-2026-05-08\.md",  # CONTEXT.md D-13-02 example
    ]
    matched = any(_re.search(tok, shared) for tok in pattern_tokens)
    assert matched, (
        "SKLL-13 D-13-02: modes/_shared.md must document the filename convention "
        f"(any of: {pattern_tokens}). Per CONTEXT.md Phase 10 CLOSES SKLL-13; "
        f"the convention must be in _shared.md verbatim."
    )
```
REMOVE the `@pytest.mark.xfail` decorator.

**FLIP-C — SKLL-13 DuckDB persistence** (test from Plan 10-00 Task 4; Round-2 codex HIGH 2: assert the REAL Phase 9 CLI from `orchestration/db-write.mjs:296-310`, NOT the fictional `--insert-report --json` form. The reports table per `orchestration/init-db.mjs:76-82` has NO `filename` column — the file on disk is the durable filename anchor):
```python
def test_report_persisted_to_duckdb(skill_root: Path) -> None:
    """SKLL-13 + D-13-04: Phase 10 closes SKLL-13. modes/_shared.md MUST
    invoke the REAL `node orchestration/db-write.mjs insert-report
    --scenario-id <int> --file <path>` subcommand after each report write.
    This test asserts the literal CLI invocation appears in _shared.md.
    Plan 10-06 adds an end-to-end smoke that actually exercises init-db +
    insert-loan + insert-scenario + insert-report and queries
    `SELECT scenario_id, markdown_blob FROM reports WHERE scenario_id = ?`.

    Round-2 codex HIGH 2: prior draft asserted the fictional flag form
    `--insert-report --json` and queried by a `filename` column that does
    not exist on the schema. Both are forbidden here."""
    shared = (skill_root / "modes" / "_shared.md").read_text()
    assert "node orchestration/db-write.mjs insert-report --scenario-id" in shared, (
        "SKLL-13 D-13-04: modes/_shared.md must invoke the REAL CLI "
        "`node orchestration/db-write.mjs insert-report --scenario-id <int> "
        "--file <path>` (per orchestration/db-write.mjs:296-310 usage block) "
        "to persist the report markdown to DuckDB after writing the .md file."
    )
    # Forbidden-substring guards (Round-2 codex HIGH 2: prior fictional CLI
    # forms must never re-appear in _shared.md)
    assert "--insert-report --json" not in shared, (
        "Round-2 codex HIGH 2: `--insert-report --json` is NOT a real flag on "
        "orchestration/db-write.mjs. Use the `insert-report --scenario-id <int> "
        "--file <path>` subcommand instead."
    )
    assert "db-write.mjs --query" not in shared, (
        "Round-2 codex HIGH 2: `--query` is NOT a real flag. The real "
        "subcommand is `query --sql \"SELECT ...\"`."
    )
    # Also assert the override knob per D-13-05
    assert "save_report: false" in shared, (
        "SKLL-13 D-13-05: modes/_shared.md must document the user-override "
        "knob `save_report: false` (the only escape hatch from D-13-03 unconditional save)."
    )
```
REMOVE the `@pytest.mark.xfail` decorator.

**BONUS 1 — drift protection for arm-mechanics.md** (10-PATTERNS CRITICAL #4 §5; consumes `repo_root` fixture per Round-2 codex HIGH 1):
```python
def test_arm_mechanics_skill_mirror_in_sync(skill_root: Path, repo_root: Path) -> None:
    """10-PATTERNS CRITICAL #4 §5: <repo>/references/arm-mechanics.md MUST stay
    byte-identical to .claude/skills/mortgage-ops/references/arm-mechanics.md
    so Phase 5 docstring path (project root) and SKLL-08 progressive disclosure
    (skill folder) cannot drift apart silently."""
    project_copy = repo_root / "references" / "arm-mechanics.md"
    skill_copy = skill_root / "references" / "arm-mechanics.md"
    assert project_copy.exists(), "Phase 5 source-of-truth missing"
    assert skill_copy.exists(), "Plan 10-04 Task 1 should have copied; SKLL-08 fails"
    assert project_copy.read_bytes() == skill_copy.read_bytes(), (
        f"DRIFT: {project_copy} and {skill_copy} are not byte-identical. "
        f"Update both copies in the same commit (10-PATTERNS CRITICAL #4)."
    )
```

**BONUS 1b — drift protection for refi-npv.md** (NEW; mirrors arm-mechanics; required by Plan 10-04 Task 2 byte-lift; consumes `repo_root` fixture per Round-2 codex HIGH 1):
```python
def test_refi_npv_skill_mirror_in_sync(skill_root: Path, repo_root: Path) -> None:
    """Plan 10-04 Task 2 byte-lift: <repo>/references/refi-npv.md MUST stay
    byte-identical to .claude/skills/mortgage-ops/references/refi-npv.md.
    Phase 6 lib/refinance.py docstring cites the project-root path; Phase 10
    progressive disclosure cites the skill-folder path. Both must agree."""
    project_copy = repo_root / "references" / "refi-npv.md"
    skill_copy = skill_root / "references" / "refi-npv.md"
    assert project_copy.exists(), "Phase 6 source-of-truth missing"
    assert skill_copy.exists(), "Plan 10-04 Task 2 should have copied; SKLL-08 fails"
    assert project_copy.read_bytes() == skill_copy.read_bytes(), (
        f"DRIFT: refi-npv.md project-root and skill-folder copies diverge. "
        f"Update both in the same commit, OR re-cp from project root."
    )
```

**BONUS 1c — drift protection for apr-reg-z.md** (NEW; mirrors arm-mechanics; required by Plan 10-04 Task 2 byte-lift; consumes `repo_root` fixture per Round-2 codex HIGH 1):
```python
def test_apr_reg_z_skill_mirror_in_sync(skill_root: Path, repo_root: Path) -> None:
    """Plan 10-04 Task 2 byte-lift: <repo>/references/apr-reg-z.md MUST stay
    byte-identical to .claude/skills/mortgage-ops/references/apr-reg-z.md.
    Phase 7 lib/apr.py docstring cites the project-root path; Phase 10
    progressive disclosure cites the skill-folder path. Both must agree."""
    project_copy = repo_root / "references" / "apr-reg-z.md"
    skill_copy = skill_root / "references" / "apr-reg-z.md"
    assert project_copy.exists(), "Phase 7 source-of-truth missing"
    assert skill_copy.exists(), "Plan 10-04 Task 2 should have copied; SKLL-08 fails"
    assert project_copy.read_bytes() == skill_copy.read_bytes(), (
        f"DRIFT: apr-reg-z.md project-root and skill-folder copies diverge."
    )
```

**BONUS 2 — 6-key envelope smoke** (RENAMED per codex MEDIUM concern 10: prior name overstated coverage):
```python
def test_amortize_envelope_smoke(skill_root: Path, tmp_path: Path) -> None:
    """Cross-cutting (relocation regression): the Phase 3 WR-02 6-key Pydantic
    envelope contract must SURVIVE the Plan 10-01 relocation. Smoke-tests
    amortize.py only — name renamed honestly per codex review (prior
    `test_relocated_scripts_envelope_smoke` overstated coverage). The other
    relocated scripts have richer JSON shapes; their envelope contracts are
    covered by the per-script test files (test_affordability.py / test_arm.py /
    test_apr.py / test_refinance.py / test_stress.py / test_points.py)."""
    bad_input = tmp_path / "bad.json"
    bad_input.write_text(
        '{"loan": {"principal": 400000.0, "annual_rate": "0.065000", '
        '"term_months": 360, "origination_date": "2026-05-01"}}'
    )
    script = skill_root / "scripts" / "amortize.py"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(bad_input)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0, "float-in-money should fail; got exit 0"
    for key in ("type", "loc", "msg", "input", "url", "ctx"):
        assert key in result.stderr, (
            f"6-key envelope missing key '{key}' in stderr (Phase 3 WR-02 contract)"
        )
```

**BONUS 3 — _profile.md write-block REVISED** (Round-2 codex HIGH 3: prior draft invoked the hook with NO args, which made `argv[1:] == []`, `offenders = []`, and the hook returned 0 — the test passed for the wrong reason. The REAL hook source `scripts/hooks/block-user-layer.py:46-67` reads `argv[1:]` for staged paths, so the test invocation must pass the candidate path AS argv. No git staging needed; this is purely a unit-level invocation):
```python
def test_profile_md_write_attempt_blocked(skill_root: Path, repo_root: Path) -> None:
    """DATA_CONTRACT + UI-SPEC §f: scripts/hooks/block-user-layer.py MUST
    reject any argv invocation that names .claude/skills/mortgage-ops/modes/_profile.md
    as a staged path.

    REVISED per Round-2 codex HIGH 3: the hook reads `argv[1:]` (verified by
    reading scripts/hooks/block-user-layer.py:46-67 — `def main(argv): offenders
    = [a for a in argv[1:] if is_user_layer(a)]; if not offenders: return 0`).
    To trigger the rejection path the test passes the candidate path AS argv.
    No git staging is required; the pre-commit shim invokes the hook with
    staged paths as argv at commit time, which is what we simulate here.

    Round-1 fix (replace grep-on-source) was the right direction but used a
    git-staging approach assuming `git diff --cached`; that doesn't match the
    actual hook source. Round-2 corrects the invocation to argv-based.
    """
    hook = repo_root / "scripts" / "hooks" / "block-user-layer.py"
    assert hook.is_file(), f"hook missing at {hook}"

    target = ".claude/skills/mortgage-ops/modes/_profile.md"
    result = subprocess.run(
        [sys.executable, str(hook), target],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1, (
        f"DATA_CONTRACT violation: hook should reject {target!r} with exit 1; "
        f"got {result.returncode}. stdout: {result.stdout[:500]} stderr: {result.stderr[:500]}"
    )
    # Hook MUST name the offending file in stderr
    assert "_profile.md" in result.stderr, (
        f"hook stderr should name the offending file; got: {result.stderr[:500]}"
    )

    # Sanity: the hook should also accept a clean staging (positive control —
    # confirms the hook is not just always rejecting everything)
    clean_result = subprocess.run(
        [sys.executable, str(hook), "lib/money.py", "pyproject.toml"],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=10,
    )
    assert clean_result.returncode == 0, (
        f"hook false-rejected clean staging; got exit {clean_result.returncode}"
    )
```

**BONUS 4 — D-SUBA-FW-02 existence-check seam in modes/stress.md** (REVISED per codex HIGH concern 4):
```python
def test_modes_stress_md_subagent_forward_link(skill_root: Path) -> None:
    """D-SUBA-FW-02 (CONTEXT.md): modes/stress.md MUST contain the literal
    phrase `if it exists` AND the literal path `.claude/agents/stress-test-agent.md`.
    Phase 11 lands by writing the agent file; modes/stress.md doesn't need
    a follow-up commit — same routing logic activates automatically."""
    text = (skill_root / "modes" / "stress.md").read_text()
    assert "stress-test-agent" in text, (
        "modes/stress.md must reference 'stress-test-agent' (D-SUBA-FW-02)"
    )
    assert "if it exists" in text, (
        "D-SUBA-FW-02: modes/stress.md must contain the LITERAL phrase "
        "'if it exists' (existence-check seam)"
    )
    assert ".claude/agents/stress-test-agent.md" in text, (
        "D-SUBA-FW-02: modes/stress.md must contain the LITERAL path "
        "'.claude/agents/stress-test-agent.md' (Phase 11 forward-link)"
    )
```

**BONUS 5 — D-SUBA-FW-01 SKILL.md Subagents section** (NEW per codex HIGH concern 3):
```python
def test_skill_md_subagent_section_present(skill_root: Path) -> None:
    """D-SUBA-FW-01 (CONTEXT.md): SKILL.md MUST contain a `## Subagents (Phase 11)`
    section naming all THREE Phase 11 subagent filenames as forward-links."""
    text = (skill_root / "SKILL.md").read_text()
    assert "## Subagents (Phase 11)" in text, (
        "D-SUBA-FW-01: SKILL.md must contain the literal heading "
        "'## Subagents (Phase 11)'"
    )
    for name in ("amortization-agent", "refi-npv-agent", "stress-test-agent"):
        assert name in text, (
            f"D-SUBA-FW-01: SKILL.md Subagents section must name '{name}' "
            f"as a forward-link (Phase 11 will create the file)"
        )
```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_skill.py::test_profile_example_md_has_exact_four_keys tests/test_skill.py::test_report_filename_format tests/test_skill.py::test_report_persisted_to_duckdb tests/test_skill.py::test_arm_mechanics_skill_mirror_in_sync tests/test_skill.py::test_refi_npv_skill_mirror_in_sync tests/test_skill.py::test_apr_reg_z_skill_mirror_in_sync tests/test_skill.py::test_amortize_envelope_smoke tests/test_skill.py::test_profile_md_write_attempt_blocked tests/test_skill.py::test_modes_stress_md_subagent_forward_link tests/test_skill.py::test_skill_md_subagent_section_present -v</automated>
  </verify>
  <acceptance_criteria>
- All flipped + bonus tests PASS:
  - FLIP-A test_profile_example_md_has_exact_four_keys (D-PROF-01) — was xfail, now PASS
  - FLIP-B test_report_filename_format (SKLL-13 D-13-02) — was xfail, now PASS
  - FLIP-C test_report_persisted_to_duckdb (SKLL-13 D-13-04) — was xfail, now PASS
  - BONUS 1 test_arm_mechanics_skill_mirror_in_sync — drift protection
  - BONUS 1b test_refi_npv_skill_mirror_in_sync — NEW drift protection
  - BONUS 1c test_apr_reg_z_skill_mirror_in_sync — NEW drift protection
  - BONUS 2 test_amortize_envelope_smoke — RENAMED from test_relocated_scripts_envelope_smoke (codex MEDIUM)
  - BONUS 3 test_profile_md_write_attempt_blocked — REVISED with real staging test
  - BONUS 4 test_modes_stress_md_subagent_forward_link — REVISED with D-SUBA-FW-02 literals
  - BONUS 5 test_skill_md_subagent_section_present — NEW per D-SUBA-FW-01
- Total tests in test_skill.py increased by ≥ 7 vs Wave 0 baseline (3 new flips + 7 net new bonus tests above the previous 4)
- mypy --strict + ruff clean across tests/test_skill.py
  </acceptance_criteria>
  <done>
    SKLL-13 closes (FLIP-B + FLIP-C); D-PROF-01 / D-SUBA-FW-01 / D-SUBA-FW-02 bound by CI; drift protection covers 3 references; _profile.md write-block is a real test (not a grep on hook source); cross-cutting safeguards in place.
  </done>
</task>

<task type="auto">
  <name>Task 5: Final wave verification + commit (SKLL-13 closes IN PHASE 10 per D-13-01..D-13-05)</name>
  <files>(verification only — no file writes beyond commit)</files>
  <read_first>
    Phase 9 baseline (≥ 549 passed per STATE.md); Wave 0 SKLL stubs (≥ 15 xfail at Wave 0 commit; now 0 remaining after Wave 5 — SKLL-13 closes via FLIP-B + FLIP-C in this wave)
  </read_first>
  <action>
PART A — Run full suite:
```
pytest -q 2>&1 | tail -10
```

REQUIRED outcome:
- ≥ 549 passed (Phase 9 baseline preserved)
- 0 xfailed for Phase 10 stubs (every Wave 0 stub now flips to PASS in Wave 5; SKLL-13 closes via FLIP-B + FLIP-C per D-13-01..D-13-05; no SKLL-XX stub remains xfail)
- ≤ 1 xfailed total acceptable (only the inherited Phase 5 ARM Bankrate/Vertex42 cross-source agreement xfail per STATE.md, which is OUTSIDE Phase 10 scope)
- 0 failed, 0 errored
- Phase 10 added tests pass: ~16 SKLL closures (token + line + routing + frontmatter + LICENSE + 7 mode parametrize + 9 ref parametrize + shared sections + profile gitignored + profile-4-keys + progressive disclosure + shell-out + run-help + report filename + report DB + 7-script audit) + 7 bonus (3 drift + 1 envelope smoke + 1 write-block + 2 subagent forward-links) ≈ 40+ new green tests
- Total expected pass: ≥ 549 + 40 ≈ ≥ 589

PART B — Hygiene:
```
mypy --strict tests/test_skill.py tests/_skill_helpers.py
ruff check tests/test_skill.py tests/_skill_helpers.py
ruff format --check tests/test_skill.py tests/_skill_helpers.py
```

ALL must be clean.

PART C — Commit (CLAUDE.md global rule: no AI attribution):
```
git add tests/test_skill.py
git commit -m "$(cat <<'EOF'
phase 10/wave 5: wire ALL SKLL CI assertions + bonus tests (SKLL-13 CLOSED in Phase 10 per D-13-01..D-13-05)

Flipped Wave 0 xfail stubs (Plan 10-00) to real assertions:
- SKLL-01..04: token + line + routing + frontmatter + LICENSE.txt
- SKLL-05..09: parametrized modes + _shared 12 sections (incl. Save Report +
  Output Formatting + Profile Loading per D-13/D-NUM/D-PROF-04) + _profile
  gitignore + _profile.example.md 4-key schema (D-PROF-01) + parametrized
  references + progressive disclosure substring
- SKLL-11..12: ALWAYS-shell-out doctrine + run-help-first doctrine + --help
  smoke for the 7 relocated CLIs
- SKLL-13: report-filename-format (D-13-02) + report-persisted-to-duckdb
  (D-13-04 — asserts modes/_shared.md invokes
  \`node orchestration/db-write.mjs --insert-report\`). Phase 10 CLOSES
  SKLL-13 per CONTEXT.md D-13-01..D-13-05 (NOT deferred to Phase 9).

Added/revised bonus cross-cutting tests:
- test_arm_mechanics_skill_mirror_in_sync (drift protection per
  10-PATTERNS CRITICAL #4)
- test_refi_npv_skill_mirror_in_sync (NEW; Plan 10-04 byte-lift drift protection)
- test_apr_reg_z_skill_mirror_in_sync (NEW; Plan 10-04 byte-lift drift protection)
- test_amortize_envelope_smoke (RENAMED from test_relocated_scripts_envelope_smoke
  — prior name overstated coverage per codex review)
- test_profile_md_write_attempt_blocked (REVISED — real test that stages a temp
  _profile.md, runs the hook, asserts non-zero exit, cleans up via try/finally;
  no longer just a grep on hook source)
- test_modes_stress_md_subagent_forward_link (REVISED per D-SUBA-FW-02 — asserts
  literal \`if it exists\` AND literal path \`.claude/agents/stress-test-agent.md\`)
- test_skill_md_subagent_section_present (NEW per D-SUBA-FW-01 — asserts SKILL.md
  has \`## Subagents (Phase 11)\` section + all 3 agent filenames)

Phase 9 baseline (≥ 549 passed) preserved end-to-end. mypy --strict + ruff
clean across all touched test files.

Closes: SKLL-01, SKLL-02, SKLL-03, SKLL-04, SKLL-05, SKLL-06, SKLL-07,
SKLL-08, SKLL-09, SKLL-11, SKLL-12, SKLL-13 (per D-13-01..D-13-05),
ROADMAP Phase 10 SC-1, SC-2, SC-3 (closed in Wave 1), SC-4, SC-5.
EOF
)"
```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest -q 2&gt;&amp;1 | tail -5 &amp;&amp; mypy --strict tests/test_skill.py tests/_skill_helpers.py &amp;&amp; ruff check tests/test_skill.py tests/_skill_helpers.py &amp;&amp; ruff format --check tests/test_skill.py tests/_skill_helpers.py &amp;&amp; git log -1 --oneline</automated>
  </verify>
  <acceptance_criteria>
- `pytest -q` shows ≥ 589 passed (549 Phase 9 baseline + ~40 new)
- `pytest -q` shows 0 xfailed Phase 10 stubs (every Wave 0 stub flipped; SKLL-13 closed)
- `pytest -q` shows ≤ 1 xfailed total (Phase 5 ARM cross-source agreement xfail OUTSIDE Phase 10 scope is acceptable)
- `pytest -q` shows 0 failed, 0 errored
- mypy + ruff clean
- `ruff check tests/test_skill.py` returns 0 errors (Round-2 codex HIGH 5: deferred imports re-added at module level via Task 1 STEP 0 import-housekeeping)
- Commit exists; subject mentions "phase 10/wave 5"
- Commit body has NO AI attribution (CLAUDE.md global rule)
- ALL 12 SKLL-XX requirements claimed in this plan closed: SKLL-01, 02, 03, 04, 05, 06, 07, 08, 09, 11, 12, 13. (SKLL-10 closed in Wave 1.) SKLL-12 closure covers all 7 relocated calc scripts in Wave 5 per Round-2 codex MEDIUM 6.
  </acceptance_criteria>
  <done>
    All Phase 10 CI assertions wired; only SKLL-13 remains xfail; commit landed without AI attribution.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Wave 0 stubs → Wave 5 real assertions | If a Wave 5 assertion is weaker than the Wave 0 docstring promised, requirement closes silently with reduced gate strength |
| Doctrine substring exact match | If SKILL.md substring drifts even by a punctuation char, SKLL-11/12 fail loudly — that's the desired behavior (force re-sync) |
| Drift-protection test → Phase 5 docstring path | If arm-mechanics drift test fails, Phase 5 docstring (project-root cite) and SKLL-08 (skill-folder cite) split — investigate which is canonical |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-27 | Tampering (assertion weakening) | Wave 5 flips | mitigate | Each flip body uses the assertion from RESEARCH §"Pinned Oracle Examples" or 10-PATTERNS test pattern verbatim — no inventing weaker checks |
| T-10-28 | Information Disclosure (xpass — accidentally-passing xfail not detected) | strict=True flag | mitigate | All Wave 0 xfails were strict=True; flipping them to PASS removes the decorator, eliminating xpass risk |
| T-10-29 | Tampering (Wave 1 SKLL-10 re-flipped) | tests/test_skill.py | mitigate | Task 1-4 explicitly do NOT re-flip SKLL-10 (already PASS from Wave 1); acceptance criteria check it stays green |
| T-10-30 | Repudiation (CLAUDE.md AI attribution rule violation) | commit message | mitigate | Task 5 PART C HEREDOC excludes Co-Authored-By; acceptance criteria asserts |
</threat_model>

<verification>
- All Wave 0 stubs flipped to PASS — SKLL-10 already flipped in Wave 1; in Wave 5: SKLL-01..09, SKLL-11..13 + D-PROF-01 stub (test_profile_example_md_has_exact_four_keys)
- SKLL-13 closes IN Wave 5 (not deferred): test_report_filename_format + test_report_persisted_to_duckdb both PASS per D-13-01..D-13-05
- 7 bonus tests PASS: 3 drift (arm-mechanics + refi-npv + apr-reg-z) + 1 envelope smoke (renamed) + 1 real write-block + 2 subagent forward-links (D-SUBA-FW-01 SKILL.md section + D-SUBA-FW-02 modes/stress.md existence-check)
- Parametrized tests: 7 mode cases + 9 reference cases all PASS
- Full suite: ≥ 589 passed + 0 Phase 10 xfails (≤ 1 total acceptable for Phase 5 ARM legacy) + 0 failed + 0 errored
- mypy + ruff clean
- Commit landed without AI attribution
</verification>

<success_criteria>
- ALL SKLL-01..13 requirements (this plan claims 12: 01-09 + 11-13) have a binding CI assertion (no more xfail; SKLL-13 closes IN PHASE 10 per D-13-01..D-13-05, NOT deferred)
- Doctrine substrings (SKLL-11/12) auditable: future SKILL.md edits that drop them fail CI
- D-PROF-01 + D-PROF-02 bound by CI: _profile.example.md must have EXACTLY 4 top-level keys
- D-SUBA-FW-01 bound by CI: SKILL.md must contain `## Subagents (Phase 11)` section + 3 agent filenames
- D-SUBA-FW-02 bound by CI: modes/stress.md must contain literal `if it exists` + `.claude/agents/stress-test-agent.md`
- Drift protection wired for THREE references (arm-mechanics + refi-npv + apr-reg-z byte-equality)
- 6-key envelope contract (Phase 3 WR-02) survives relocation per smoke test (renamed honestly to test_amortize_envelope_smoke)
- _profile.md write-block test is REAL (stages temp file, runs hook, cleans up via try/finally) — no longer a grep on hook source
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-05-SUMMARY.md` documenting:
- ALL Wave 0 xfails flipped (table: test name → SKLL-XX → flipped/PARAMETRIZED-converted) including SKLL-13 D-13-02 + D-13-04
- 7 bonus tests added/revised (table: test name → contract enforced)
- Final pass count vs Phase 9 baseline (must be ≥ 549 + ~40)
- xfail count after wave (must be 0 for Phase 10; ≤ 1 total acceptable for Phase 5 ARM legacy)
- mypy + ruff status
- SKLL-13 closure note: Phase 10 D-13-01..D-13-05 closes SKLL-13 via _shared.md Save Report step + DuckDB --insert-report invocation. Plan 10-06 adds end-to-end smoke that exercises the Save Report path concretely.
- D-PROF-01 / D-SUBA-FW-01 / D-SUBA-FW-02 closure: each LOCKED DECISION has a binding CI assertion
- Phase 10 SC-1..SC-5 closure status (all closed; full requirement closure)
</output>
