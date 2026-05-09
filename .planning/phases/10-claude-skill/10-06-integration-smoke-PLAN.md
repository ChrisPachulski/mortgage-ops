---
phase: 10
plan: 06
type: execute
wave: 6
depends_on:
  - "10-00"
  - "10-01"
  - "10-02"
  - "10-03"
  - "10-04"
  - "10-05"
files_modified:
  - tests/test_skill_integration.py
autonomous: true
requirements:
  - SKLL-13
tags:
  - phase-10
  - claude-skill
  - integration
  - portability
  - smoke
  - skll-13
must_haves:
  truths:
    - "tests/test_skill_integration.py exists and runs end-to-end portability smoke + SKLL-13 end-to-end smoke (Plan 10-06 contributes the SKLL-13 end-to-end coverage on top of Plan 10-05's unit-level assertions per CONTEXT.md D-13-01..D-13-05)"
    - "Portability test: rsync-copy .claude/skills/mortgage-ops/ into a tmp dir + verify each of the 7 relocated calc scripts still --help-runs from the copy (proves skill is self-contained per Anthropic spec; symlinks would fail this check, validating Plan 10-01 D-01 MOVE choice)"
    - "Portability test ALSO invokes one full script run from the copied folder (e.g., amortize.py --principal 200000 --rate 0.065 --term 360 against an in-tmp tmp dir) to make the 'self-contained' claim honest — not just a --help check (codex MEDIUM concern 12)"
    - "Runtime SKILL.md token budget: re-run count_tokens at end of phase. Hard cap is the official ≤ 4500 from CONTEXT.md / SKLL-01 / D-02 (5000 Anthropic spec − 10% margin). NO stricter sub-cap is enforced unless explicitly tied to a documented decision (codex MEDIUM concern 13)."
    - "SKLL-13 end-to-end smoke: actually invokes the Save Report path (writes a temp report file, runs `node orchestration/db-write.mjs --insert-report --json {meta}`, queries DuckDB with `SELECT COUNT(*) FROM reports WHERE filename = ?` returning 1)"
    - "Full pytest suite green: ≥ 549 passed (Phase 9 baseline) + Phase 10 additions; 0 Phase 10 xfails (SKLL-13 closes via Wave 5 + Wave 6 end-to-end); ≤ 1 xfail acceptable for Phase 5 ARM legacy"
  artifacts:
    - path: "tests/test_skill_integration.py"
      provides: "Cross-cutting portability + runtime smoke tests + SKLL-13 end-to-end smoke (D-13-01..05). Combines skill-portability enforcement (motivated MOVE-not-symlink in D-01) with Save Report end-to-end coverage."
      min_lines: 90
      contains: "def test_skill_folder_self_contained_portability"
  key_links:
    - from: "tests/test_skill_integration.py portability test"
      to: ".claude/skills/mortgage-ops/ entire folder"
      via: "rsync to tmp dir + invoke scripts in isolation"
      pattern: "rsync\\|copytree"
---

<objective>
Add cross-cutting integration smoke tests that prove the skill folder is self-contained + portable per Anthropic spec. These tests do not close a specific SKLL-XX requirement; they enforce the SKILL-PORTABILITY principle (CLAUDE.md ## Conventions, Anthropic agentskills.io spec) that motivated D-01 (MOVE not symlink not shim).

Specifically:
1. **Portability smoke** — copy `.claude/skills/mortgage-ops/` to a tmp dir + invoke scripts from the copy + verify they still work. If symlinks were used (rejected per D-01), this test would fail because symlinks dangle on copy.
2. **Runtime token re-check** — after all 6 waves shipped, verify SKILL.md token budget headroom remains (defends against late-wave token bloat).
3. **Final wave gate** — full suite verification one more time before Phase 10 ships.

Closes nothing new (no SKLL-XX requirement maps here); the wave's job is QUALITY ASSURANCE for the principles Wave 1-5 implemented.

Purpose: A skill that fails portability silently breaks when the user copies it to another machine or shares it (contradicting the whole point of `.claude/skills/`). This test catches regressions where future edits introduce symlinks, hardcoded absolute paths, or out-of-skill-folder references.

Output: 1 new test file (~80 lines) with 2-3 test functions; full suite stays green.
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

<interfaces>
LOCKED DECISIONS in scope:
- D-01 = MOVE relocation. Symlinks/shims rejected partly BECAUSE they break portability. This wave's test is the assertion that proves D-01 was the right call.

CLAUDE.md ## Conventions (Skill portability):
> `scripts/`, `references/`, `assets/`, `LICENSE.txt` all INSIDE `.claude/skills/mortgage-ops/`.

Anthropic agentskills.io spec:
> Skills are portable, version-controlled folders that agents load on demand.

The "portability" property = the skill folder, copied verbatim to another location/machine, still functions. A symlink-based scheme breaks this; a shim-based scheme breaks it; the MOVE scheme (D-01) preserves it.

Test approach for portability:
1. Use `shutil.copytree(skill_root, tmp_path / "mortgage-ops")` to copy the folder
2. Invoke each of the 4 relocated scripts from the COPY (not the original)
3. Verify --help still works (because no symlinks dangle)
4. The test does NOT validate that scripts produce the same OUTPUT (that's tested by the existing test_amortize.py / test_affordability.py / test_arm.py via SCRIPT_PATH); it validates that the COPIED scripts are runnable

Edge case: the copied scripts' sys.path injection uses `parents[4]` to find the repo root. When running from tmp_path/mortgage-ops/scripts/, `parents[4]` no longer points to the original repo (it points to /tmp). So `from lib.amortize import ...` would FAIL from the copy.

This is INTENTIONAL — the copy is for testing portability of the SKILL FOLDER, not the WHOLE PROJECT. Production use of a skill copied to another machine REQUIRES the lib/ to be installed (e.g., as a pip package). The portability test verifies that the SKILL ARTIFACTS (markdown + script files) survive copy intact, NOT that they execute end-to-end without their lib/ dependency.

What we CAN smoke-test from the copy:
- Each script's --help works WITHOUT lib/* imports (D-18 fast --help — argparse runs BEFORE lazy lib import)
- Each markdown file (SKILL.md, modes/*.md, references/*.md) is readable and parseable
- Frontmatter still parses
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tests/test_skill_integration.py with portability smoke + token-headroom + final-gate tests</name>
  <files>tests/test_skill_integration.py</files>
  <read_first>
    tests/test_skill.py — for shape/imports parallel;
    tests/_skill_helpers.py — count_tokens helper;
    .claude/skills/mortgage-ops/scripts/amortize.py — verify --help works without lib/ (D-18 fast --help)
  </read_first>
  <action>
Create `tests/test_skill_integration.py` (~90 lines):

```python
"""Phase 10 cross-cutting integration smoke tests.

These tests do NOT close a specific SKLL-XX requirement; they enforce
SKILL-PORTABILITY — the principle that motivated D-01 (MOVE not symlink/shim).

If a future edit introduces a symlink in the skill folder, or hardcodes an
absolute path that points outside the skill folder, or otherwise breaks the
self-contained property, the portability smoke test FAILS — surfacing the
regression at PR time.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests._skill_helpers import count_tokens


def test_skill_folder_self_contained_portability(skill_root: Path, tmp_path: Path) -> None:
    """Copy .claude/skills/mortgage-ops/ to tmp_path and verify each relocated
    script's --help still works from the copy.

    This test passes ONLY because Plan 10-01 chose MOVE (D-01) — a symlink-based
    scheme would have dangling links in the copy; a shim scheme would have
    broken relative-path computations. The MOVE scheme keeps every artifact
    self-contained inside the skill folder.

    NOTE: We test --help only (not full --input runs). Phase 3 D-18 ensures
    --help runs WITHOUT importing lib.* (argparse runs before lazy import),
    so --help works from any location. Full --input runs require lib/* on
    sys.path, which a true off-machine copy would need to install separately.
    """
    skill_copy = tmp_path / "mortgage-ops"
    shutil.copytree(skill_root, skill_copy)

    # Verify the copy is byte-equal at the structural level
    assert (skill_copy / "SKILL.md").is_file(), "SKILL.md missing from copy"
    assert (skill_copy / "LICENSE.txt").is_file(), "LICENSE.txt missing from copy"
    assert (skill_copy / "scripts").is_dir(), "scripts/ missing from copy"
    assert (skill_copy / "modes").is_dir(), "modes/ missing from copy"
    assert (skill_copy / "references").is_dir(), "references/ missing from copy"

    # Verify NO symlinks anywhere in the copy (D-01 MOVE choice; symlinks
    # would dangle on copy). Walk the tree and assert each file is a regular
    # file, not a symlink.
    for path in skill_copy.rglob("*"):
        assert not path.is_symlink(), (
            f"Portability violation: {path.relative_to(skill_copy)} is a symlink. "
            f"Per D-01 (Plan 10-01) the skill folder MUST be symlink-free; "
            f"symlinks dangle when the folder is copied to another machine."
        )

    # Smoke A: each of the 7 relocated calc scripts' --help exits 0 from the copy
    relocated = (
        "amortize.py", "affordability.py", "arm_simulate.py",
        "refi_npv.py", "apr_reg_z.py", "stress_test.py", "points_breakeven.py",
    )
    for name in relocated:
        script = skill_copy / "scripts" / name
        assert script.is_file(), f"Copy missing {name}"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # --help should exit 0 because Phase 3 D-18 lazy-imports lib/ AFTER
        # argparse. If --help fails, either D-18 broke (regression) OR the
        # copy is missing a non-script file the script imports (e.g.,
        # _cli_helpers.py — which DOES live in the same dir, so should copy).
        assert result.returncode == 0, (
            f"{name} --help failed from copy (exit {result.returncode}).\n"
            f"stderr: {result.stderr[:500]}\n"
            f"This indicates the skill folder is NOT self-contained — D-01 contract violated."
        )

    # Smoke B (codex MEDIUM concern 12): make the "self-contained" claim honest.
    # Run amortize.py with a real --input from the COPY. This exercises the
    # full lazy-import path (sys.path injection + lib.amortize import). If the
    # repo has lib/ on the import path (which it does in CI from project root),
    # the call returns valid JSON. The value of this test is NOT validating
    # the math (other tests do that) but proving the COPIED script CAN run
    # end-to-end without breaking on a missing companion file inside the
    # skill folder. If a future PR introduces a relative-path bug or an
    # absolute-path-outside-skill-folder reference, this fails.
    #
    # NOTE on lib/ dependency: a true off-machine deploy of the skill folder
    # would require lib/ to be importable (e.g., installed as a pip package).
    # On THIS test box, lib/ is on sys.path because pyproject.toml
    # `[tool.pytest.ini_options].pythonpath = [".", ".claude/skills/mortgage-ops"]`
    # adds the repo root. So the COPY can resolve `from lib.amortize import ...`
    # because parents[4] of the script (now at tmp_path) does NOT lead to the
    # repo root, but the running pytest process already has lib/ on sys.path
    # via PYTHONPATH inheritance. This is intentional — the smoke is about
    # the SKILL FOLDER being self-contained for its INTERNAL imports, NOT
    # about lib/ being relocated.
    amortize_script = skill_copy / "scripts" / "amortize.py"
    result = subprocess.run(
        [
            sys.executable, str(amortize_script),
            "--principal", "200000",
            "--rate", "0.065",
            "--term", "360",
        ],
        capture_output=True, text=True, timeout=30,
        env={**__import__("os").environ, "PYTHONPATH": str(skill_root.parent.parent.parent.parent)},
    )
    # Either the script supports positional CLI args OR it requires --input
    # JSON file. If --principal isn't recognized, fall back to --input mode.
    if result.returncode != 0 and "--principal" in result.stderr:
        # Script uses --input JSON mode; build a minimal JSON input
        import json
        sample = tmp_path / "sample-input.json"
        sample.write_text(json.dumps({
            "loan": {
                "principal": "200000.00",
                "annual_rate": "0.065000",
                "term_months": 360,
                "origination_date": "2026-05-01",
            }
        }))
        result = subprocess.run(
            [sys.executable, str(amortize_script), "--input", str(sample)],
            capture_output=True, text=True, timeout=30,
            env={**__import__("os").environ, "PYTHONPATH": str(skill_root.parent.parent.parent.parent)},
        )
    assert result.returncode == 0, (
        f"Portability smoke B: amortize.py from COPY exited {result.returncode}.\n"
        f"stdout: {result.stdout[:300]}\nstderr: {result.stderr[:500]}\n"
        f"The skill folder is not honestly self-contained for full execution."
    )


def test_skill_md_token_budget_at_phase_end(skill_root: Path) -> None:
    """Final-wave runtime check: SKILL.md is at or under the OFFICIAL ≤ 4500
    cl100k token cap from CONTEXT.md / SKLL-01 / D-02 (5000 Anthropic spec
    minus 10% margin for cl100k-vs-Anthropic-tokenizer drift).

    Per codex MEDIUM concern 13: this test enforces ONLY the 4500 cap that
    already binds in CONTEXT.md. No stricter sub-cap (e.g., 4300) is enforced
    unless explicitly tied to a documented CONTEXT.md decision. Plan 10-05
    test_skill_md_under_token_budget already pins 4500 at Wave 5; this is
    the Wave 6 final re-check confirming nothing slipped past during Waves 3–5.
    """
    skill_md = (skill_root / "SKILL.md").read_text()
    n_tokens = count_tokens(skill_md)
    assert n_tokens <= 4500, (
        f"SKILL.md is {n_tokens} cl100k tokens; budget 4500 (CONTEXT.md / SKLL-01 / D-02). "
        f"Reduce SKILL.md or move content to references/ (progressive disclosure SKLL-09)."
    )


def test_no_user_layer_files_committed_in_skill_folder(skill_root: Path) -> None:
    """DATA_CONTRACT enforcement: modes/_profile.md (User Layer) MUST NOT
    appear in the git index. The file MAY exist on a developer machine
    (User Layer; gitignored), but it must NOT be in the committed tree.

    The .gitignore (Plan 10-03 Task 3 PART A) + the pre-commit hook
    (Plan 10-03 Task 3 PART B) together prevent the file from being committed.
    This test is the tertiary backstop in CI: a developer who accidentally
    committed it via `git add -f` would trip both layers; this test catches
    a slip-through.

    Per codex LOW concern 15: prior version had a tautological
    `... or True` assertion which made the working-tree existence check
    meaningless. Removed that assertion. The git-index check below is the
    real gate.
    """
    # The real gate: assert the file is NOT in git's index. Working-tree
    # presence is fine (User Layer may exist locally); only the INDEX matters.
    repo_root = skill_root.parent.parent.parent.parent
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".claude/skills/mortgage-ops/modes/_profile.md"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    # Exit code 1 = file NOT in git index (good); exit 0 = file IS in index (bad — User Layer leak)
    assert result.returncode != 0, (
        "DATA_CONTRACT violation: .claude/skills/mortgage-ops/modes/_profile.md is "
        "in the git index. This is User Layer per DATA_CONTRACT.md. Run "
        "`git rm --cached .claude/skills/mortgage-ops/modes/_profile.md` and re-commit."
    )
```

Note on the third test: `git ls-files --error-unmatch FILE` exits 0 if the file is tracked, non-zero if it isn't. We invert: tracked = bad (User Layer leak), not-tracked = good.

ALSO append the SKLL-13 end-to-end smoke test (codex HIGH concern 1; CONTEXT.md D-13-01..D-13-05 closure on top of Plan 10-05's unit-level assertions):

```python
def test_skll_13_end_to_end_save_report_writes_file_and_db_row(
    skill_root: Path, tmp_path: Path
) -> None:
    """SKLL-13 end-to-end smoke (D-13-01..D-13-05): exercises the Save Report
    path concretely.

    1. Construct a sample report markdown body
    2. Compute the next sequence number via `node orchestration/db-write.mjs --query`
    3. Build the filename per D-13-02: reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md
    4. Write the file under tmp_path (NOT under repo's reports/ — gitignored
       there but we keep this test side-effect-free)
    5. Invoke `node orchestration/db-write.mjs --insert-report --json {meta}`
       per D-13-04
    6. Query DuckDB: SELECT COUNT(*) FROM reports WHERE filename = ? — must
       return 1
    7. Clean up via try/finally: DELETE the inserted row to keep the DB
       deterministic for other tests

    This test confirms the Save Report path is END-TO-END operational at
    Phase 10 ship — closing SKLL-13 per D-13-01..D-13-05 (Phase 10 closes
    SKLL-13; NOT deferred to Phase 9). Plan 10-05 has the unit-level
    assertion (modes/_shared.md documents the invocation); this is the
    runtime proof.

    NOTE: this test depends on `node` + `orchestration/db-write.mjs` being
    operational (Phase 9 PERS-03). If `which node` returns nothing, the
    test SKIPS rather than fails (Phase 9 contract is the precondition).
    """
    import json as _json
    import shutil as _shutil
    from datetime import date as _date

    if _shutil.which("node") is None:
        pytest.skip("node not on PATH; SKLL-13 end-to-end smoke requires Phase 9 orchestration")

    repo_root = skill_root.parent.parent.parent.parent
    db_write = repo_root / "orchestration" / "db-write.mjs"
    if not db_write.is_file():
        pytest.skip(f"orchestration/db-write.mjs not found at {db_write}; Phase 9 prerequisite")

    # PART A — get next sequence number
    seq_result = subprocess.run(
        ["node", str(db_write), "--query", "SELECT COUNT(*)+1 AS next_seq FROM reports"],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=15,
    )
    assert seq_result.returncode == 0, (
        f"Phase 9 cmdQuery failed: {seq_result.stderr[:500]}"
    )
    # parse next_seq; handler returns JSON like {"next_seq": <int>} or [{"next_seq": <int>}]
    parsed = _json.loads(seq_result.stdout) if seq_result.stdout.strip() else {}
    if isinstance(parsed, list) and parsed:
        next_seq = parsed[0].get("next_seq", 1)
    elif isinstance(parsed, dict):
        next_seq = parsed.get("next_seq", 1)
    else:
        next_seq = 1
    assert isinstance(next_seq, int) and next_seq >= 1, f"bad next_seq: {next_seq!r}"

    # PART B — construct the filename per D-13-02
    today = _date.today().isoformat()  # YYYY-MM-DD
    mode = "amortize"
    filename = f"reports/{next_seq:03d}-{mode}-{today}.md"

    # Validate the filename matches D-13-02 regex
    import re as _re
    pattern = r"^reports/\d{3}-(?:evaluate|compare|refinance|affordability|stress|amortize|arm)-\d{4}-\d{2}-\d{2}\.md$"
    assert _re.match(pattern, filename), (
        f"D-13-02 filename violation: {filename!r} does not match {pattern!r}"
    )

    # PART C — write the report to a tmp location (test side-effect-free)
    report_body = "# SKLL-13 End-to-End Smoke\n\nGenerated by Plan 10-06.\n"
    report_path = tmp_path / "report.md"
    report_path.write_text(report_body)

    # PART D — invoke INSERT (D-13-04)
    payload = _json.dumps({
        "scenario_id": None,
        "kind": mode,
        "markdown_blob": report_body,
        "filename": filename,
    })
    inserted = False
    try:
        ins_result = subprocess.run(
            ["node", str(db_write), "--insert-report", "--json", payload],
            cwd=str(repo_root),
            capture_output=True, text=True, timeout=15,
        )
        assert ins_result.returncode == 0, (
            f"D-13-04 INSERT failed: {ins_result.stderr[:500]}"
        )
        inserted = True

        # PART E — query DuckDB and verify the row exists
        check_result = subprocess.run(
            [
                "node", str(db_write),
                "--query", f"SELECT COUNT(*) AS n FROM reports WHERE filename = '{filename}'",
            ],
            cwd=str(repo_root),
            capture_output=True, text=True, timeout=15,
        )
        assert check_result.returncode == 0, f"COUNT query failed: {check_result.stderr}"
        check_parsed = _json.loads(check_result.stdout) if check_result.stdout.strip() else {}
        if isinstance(check_parsed, list) and check_parsed:
            n = check_parsed[0].get("n", 0)
        elif isinstance(check_parsed, dict):
            n = check_parsed.get("n", 0)
        else:
            n = 0
        assert n == 1, (
            f"SKLL-13 D-13-04: expected 1 row in reports for filename={filename!r}, got {n}"
        )
    finally:
        # PART F — clean up to keep DB deterministic
        if inserted:
            subprocess.run(
                [
                    "node", str(db_write),
                    "--query", f"DELETE FROM reports WHERE filename = '{filename}'",
                ],
                cwd=str(repo_root),
                capture_output=True, text=True, timeout=15,
            )
```

Hygiene constraints:
- mypy --strict clean
- ruff clean (imports sorted; line length ≤ 100)
- subprocess.run timeouts set (max 30s per node invocation)
- shutil.copytree handles the copy (not manual file-by-file)
- pytest.skip used for missing node/db-write.mjs (don't fail when Phase 9 prereq absent)
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_skill_integration.py -v &amp;&amp; mypy --strict tests/test_skill_integration.py &amp;&amp; ruff check tests/test_skill_integration.py &amp;&amp; ruff format --check tests/test_skill_integration.py &amp;&amp; ! grep -F 'or True' tests/test_skill_integration.py &amp;&amp; ! grep -E '4500.*-.*200|4300' tests/test_skill_integration.py</automated>
  </verify>
  <acceptance_criteria>
- File exists with ≥ 90 lines
- 4 test functions defined: portability, token-budget, User-Layer-leak, SKLL-13 end-to-end
- All 4 tests PASS (or SKLL-13 end-to-end SKIPS cleanly if `node` is absent)
- Portability test: no symlinks in skill folder copy
- Portability test: ALL 7 relocated calc scripts' --help works from copy
- Portability test: at least ONE script (amortize.py) runs end-to-end with real --input from copy (codex MEDIUM concern 12: honest "self-contained" claim)
- Token budget test: SKILL.md ≤ 4500 cl100k tokens (NOT a stricter sub-cap; codex MEDIUM concern 13)
- User Layer leak test: NO `... or True` no-op assertion (codex LOW concern 15: removed)
- User Layer leak test: _profile.md NOT in git index (real assertion)
- SKLL-13 test: report file written + DuckDB row appears + filename matches D-13-02 regex + cleanup runs in finally
- mypy --strict + ruff clean
  </acceptance_criteria>
  <done>
    Portability smoke (with full script run) + token budget at official cap + User Layer leak check (no tautology) + SKLL-13 end-to-end smoke all pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Final phase verification + commit Wave 6</name>
  <files>(verification only — no file writes beyond commit)</files>
  <read_first>
    Phase 9 baseline (≥ 549 passed per STATE.md); Wave 5 final state (≥ 589 passed + 0 Phase 10 xfail)
  </read_first>
  <action>
PART A — Full suite, expecting Phase 10 final state:
```
pytest -q 2>&1 | tail -10
```

REQUIRED:
- ≥ 593 passed (Wave 5 left ≥ 589; this wave adds 4 integration tests = ≥ 593, may be slightly less if SKLL-13 end-to-end skips for missing node)
- 0 Phase 10 xfail (SKLL-13 closes via Wave 5 + this wave's end-to-end smoke per D-13-01..D-13-05)
- ≤ 1 xfail total acceptable (Phase 5 ARM legacy outside Phase 10 scope)
- 0 failed, 0 errored

PART B — Phase 10 SC-1..SC-5 audit. Verify each ROADMAP success criterion satisfied:

```
# SC-1: SKILL.md ≤ 500 lines + ≤ 5000 tokens (we use 4500 cl100k as proxy with margin)
pytest tests/test_skill.py::test_skill_md_under_token_budget tests/test_skill.py::test_skill_md_under_line_budget -v

# SC-2: SKILL.md frontmatter has 4 keys + LICENSE.txt bundled
pytest tests/test_skill.py::test_skill_md_frontmatter_required_fields tests/test_skill.py::test_license_txt_exists_in_skill_folder -v

# SC-3: 7 calc scripts INSIDE skill folder (4 currently shipped; 3 from Phase 6/7/8 will land per D-08)
pytest tests/test_skill.py::test_seven_scripts_in_skill_folder_only -v

# SC-4: 7 mode files + _shared + _profile.example present
pytest tests/test_skill.py::test_mode_file_exists tests/test_skill.py::test_shared_mode_has_required_sections tests/test_skill.py::test_profile_md_user_layer_gitignored -v

# SC-5: 9 references + always-shell-out + run-help-first doctrines
pytest tests/test_skill.py::test_reference_file_exists tests/test_skill.py::test_skill_md_shell_out_doctrine tests/test_skill.py::test_each_script_has_help_and_doctrine_documented tests/test_skill.py::test_skill_md_documents_progressive_disclosure -v
```

ALL must PASS.

PART C — Hygiene:
```
mypy --strict tests/ .claude/skills/mortgage-ops/scripts/
ruff check tests/ .claude/skills/mortgage-ops/scripts/
ruff format --check tests/ .claude/skills/mortgage-ops/scripts/
```

ALL must be clean.

PART D — Commit (CLAUDE.md global rule: no AI attribution):
```
git add tests/test_skill_integration.py
git commit -m "$(cat <<'EOF'
phase 10/wave 6: portability + token-budget + User Layer leak + SKLL-13 end-to-end smoke

Four cross-cutting integration tests:

- test_skill_folder_self_contained_portability: rsync-copy
  .claude/skills/mortgage-ops/ to tmp dir, walk tree asserting no symlinks,
  smoke ALL 7 relocated calc scripts' --help from the copy, AND run amortize.py
  end-to-end with real --input from the copy (honest self-contained claim).
  If a future edit introduces a symlink or breaks self-containment, this
  fails at PR time.

- test_skill_md_token_budget_at_phase_end: end-of-phase token re-check at
  the OFFICIAL ≤ 4500 cap from CONTEXT.md / SKLL-01 / D-02. No stricter
  sub-cap is enforced (revised per codex review — prior version had a 4300
  hard gate that was tighter than the documented decision).

- test_no_user_layer_files_committed_in_skill_folder: tertiary backstop for
  the DATA_CONTRACT triple (.gitignore + pre-commit hook + this CI test) —
  asserts modes/_profile.md is NOT in the git index. Removed the prior
  tautological \\`... or True\\` working-tree assertion (codex LOW concern).

- test_skll_13_end_to_end_save_report_writes_file_and_db_row (NEW): exercises
  the Save Report path concretely per CONTEXT.md D-13-01..D-13-05 — writes a
  report file, invokes \\`node orchestration/db-write.mjs --insert-report\\`,
  queries DuckDB confirming the row appears, cleans up via try/finally.
  Phase 10 CLOSES SKLL-13 (NOT deferred).

Phase 10 final state:
- All 5 ROADMAP SC-1..SC-5 closed
- ALL 13 SKLL-XX requirements have binding CI assertions (incl. SKLL-13)
- SKLL-10 closed in Wave 1 (all 7 calc scripts relocated)
- Phase 9 baseline (≥ 549 passed) preserved end-to-end
- Total Phase 10 net additions: ~44 new green tests; 0 Phase 10 xfails

Per LOCKED DECISIONS D-13-01..D-13-05 / D-PROF-01 / D-SUBA-FW-01 / D-SUBA-FW-02
/ D-NUM-01..06 / D-08 retired (all 7 scripts now in skill folder).
EOF
)"
```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest -q 2&gt;&amp;1 | tail -5 &amp;&amp; mypy --strict tests/ .claude/skills/mortgage-ops/scripts/ &amp;&amp; ruff check tests/ .claude/skills/mortgage-ops/scripts/ &amp;&amp; ruff format --check tests/ .claude/skills/mortgage-ops/scripts/ &amp;&amp; git log -2 --oneline</automated>
  </verify>
  <acceptance_criteria>
- `pytest -q` shows ≥ 593 passed (or ≥ 592 if SKLL-13 end-to-end skips for missing node)
- `pytest -q` shows 0 Phase 10 xfailed; ≤ 1 total xfail acceptable (Phase 5 ARM legacy)
- `pytest -q` shows 0 failed, 0 errored
- ROADMAP SC-1..SC-5 audit subcommand all PASS
- mypy --strict + ruff clean across all of `tests/` + relocated scripts
- Wave 6 commit landed; subject mentions "phase 10/wave 6"
- Commit body has NO AI attribution (CLAUDE.md global rule)
- `git log -2 --oneline` shows Wave 5 + Wave 6 commits
  </acceptance_criteria>
  <done>
    Phase 10 fully shipped: portability smoke green, token headroom verified, User Layer enforcement audited, ROADMAP SC-1..SC-5 closed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Skill folder copy → real-world deploy | Portability test simulates the copy-to-another-machine scenario; if it fails, real-world skill sharing fails too |
| SKILL.md token-budget headroom → late-wave creep | Without headroom, even small future edits push past 4500; with headroom, future maintenance has runway |
| User Layer leak → CI gate | Triple-check (gitignore + pre-commit hook + this CI test) means a User Layer commit must defeat all three layers to ship |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-31 | Tampering (symlink introduced silently) | future skill-folder edits | mitigate | Portability test walks tree asserting no symlinks; would catch a future PR that introduces them |
| T-10-32 | DoS (token bloat to spec limit) | SKILL.md late edits | mitigate | 200-token headroom check forces explicit conversation if SKILL.md grows past 4300 cl100k |
| T-10-33 | Information Disclosure (User Layer leak) | _profile.md commit | mitigate | Triple-layer enforcement; this Wave's test is layer 3 |
| T-10-34 | Spoofing (CI false-pass via test bug) | git ls-files invocation | accept | Subprocess invocation is straightforward; bug risk is low; manual verification of test behavior during plan-check is the backup |
| T-10-35 | Repudiation (CLAUDE.md AI attribution rule violation) | commit message | mitigate | Task 2 PART D HEREDOC excludes Co-Authored-By; acceptance criteria asserts |
| T-10-44 | Tampering (SKLL-13 closure verified at modes/ layer but not at runtime) | end-to-end smoke | mitigate | Task 1 ships test_skll_13_end_to_end_save_report_writes_file_and_db_row which actually invokes the node handler + queries DuckDB; closes the gap between Wave 5 unit-level grep assertions and runtime behavior |
| T-10-45 | DoS (token-budget false-fail at strict-than-cap threshold) | SKILL.md token check | mitigate | Task 1 token test pinned at the OFFICIAL 4500 cap from CONTEXT.md; no stricter sub-cap unless added by a documented decision (per codex MEDIUM concern 13) |
</threat_model>

<verification>
- 1 new test file exists with 4 functions
- Portability copy + tree-walk + 7-script --help + 1 full-script-run all pass
- Token budget check passes (≤ 4500 cl100k — official cap; no stricter sub-cap)
- User Layer leak check passes (_profile.md not in git index; no `... or True` tautology)
- SKLL-13 end-to-end smoke: report file written + DuckDB row appears + filename matches D-13-02 regex (or skips cleanly if node missing)
- Full suite: ≥ 593 passed + 0 Phase 10 xfails + ≤ 1 total xfail + 0 failed + 0 errored
- All ROADMAP SC-1..SC-5 specifically verified by named test invocations
- mypy + ruff clean across full project surface
- Commit landed without AI attribution
</verification>

<success_criteria>
- Phase 10 SHIPPED end-to-end
- ROADMAP SC-1..SC-5 all closed (audit verified by Task 2 PART B)
- ALL 13 SKLL-XX requirements have binding CI assertions (SKLL-13 closes via Wave 5 unit-level + Wave 6 end-to-end per D-13-01..D-13-05)
- Skill folder is self-contained + portable + symlink-free (with HONEST claim — full script invocation from copy, not just --help)
- SKILL.md fits the OFFICIAL ≤ 4500 cl100k token cap (no stricter sub-cap)
- DATA_CONTRACT User Layer triple-enforcement verified end-to-end (no tautological assertions)
- Cross-phase contract D-08 RETIRED (all 7 scripts in skill folder)
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-06-SUMMARY.md` documenting:
- 4 integration tests added (portability with 7-script + full-run, token-budget at official cap, User Layer leak without tautology, SKLL-13 end-to-end)
- Final pass count (must be ≥ 593)
- ROADMAP SC-1..SC-5 audit results (each criterion + test name + pass/fail)
- Phase 10 net contribution: lines of code added, tests added, requirements closed
- SKLL-13 closure note: Phase 10 closes SKLL-13 fully via Wave 5 (unit-level _shared.md assertions) + Wave 6 (end-to-end smoke writing file + querying DuckDB) per CONTEXT.md D-13-01..D-13-05
- D-08 retirement note: all 7 calc scripts now in skill folder; no further "ship to root then relocate" pattern
- Open items for Phase 11/12 (Phase 11 subagent files + Phase 12 FRED/eval)
</output>
</content>
</invoke>