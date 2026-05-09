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
    - "Skill artifact COPYABILITY test: rsync-copy .claude/skills/mortgage-ops/ into a tmp dir + verify each of the 7 relocated calc scripts still --help-runs from the copy AND amortize.py runs end-to-end from the copy when PYTHONPATH points at the repo root. Round-2 codex MEDIUM 9: renamed from `test_skill_folder_self_contained_portability` to `test_skill_artifact_copyability_with_repo_pythonpath` because the skill folder is NOT bundle-self-contained for full execution (lib/* lives at repo root and the copied scripts inject parents[4] to find it). The honest claim: skill artifacts are copyable AND symlink-free (validating D-01 MOVE choice over symlink/shim) AND scripts are runnable from the copy WITH the repo lib/ on PYTHONPATH. A future bundled deploy would lift the PYTHONPATH dependency."
    - "Copyability test ALSO invokes one full script run from the copied folder (amortize.py against an in-tmp sample input) with PYTHONPATH=<repo_root> so lib.* resolves — not just a --help check (codex MEDIUM 12; Round-2 codex MEDIUM 9 honest naming)"
    - "Runtime SKILL.md token budget: re-run count_tokens at end of phase. Hard cap is the official ≤ 4500 from CONTEXT.md / SKLL-01 / D-02 (5000 Anthropic spec − 10% margin). NO stricter sub-cap is enforced unless explicitly tied to a documented decision (codex MEDIUM concern 13)."
    - "SKLL-13 end-to-end smoke: walks the 7-step flow against an isolated tmp DuckDB (init-db → insert-loan → insert-scenario → write report file at D-13-02 path → insert-report --scenario-id <id> --file <path> → query --sql to verify scenario_id+markdown_blob round-trip). Uses the REAL Phase 9 CLI from orchestration/db-write.mjs:296-310 (Round-2 codex HIGH 2: NOT the fictional `--insert-report --json` form). Schema has no `filename` column — verification is by `scenario_id` plus markdown_blob byte-equality with the file contents."
    - "Full pytest suite green: ≥ 549 passed (Phase 9 baseline) + Phase 10 additions; 0 Phase 10 xfails (SKLL-13 closes via Wave 5 + Wave 6 end-to-end); ≤ 1 xfail acceptable for Phase 5 ARM legacy"
  artifacts:
    - path: "tests/test_skill_integration.py"
      provides: "Cross-cutting copyability + runtime smoke tests + SKLL-13 end-to-end smoke (D-13-01..05). Combines skill-folder copyability/symlink-freedom enforcement (motivated MOVE-not-symlink in D-01) with Save Report end-to-end coverage exercising the REAL Phase 9 CLI surface from orchestration/db-write.mjs:296-310 (Round-2 codex HIGH 2)."
      min_lines: 90
      contains: "def test_skill_artifact_copyability_with_repo_pythonpath"
  key_links:
    - from: "tests/test_skill_integration.py copyability test"
      to: ".claude/skills/mortgage-ops/ entire folder"
      via: "shutil.copytree to tmp dir + invoke scripts with repo-root on PYTHONPATH (Round-2 codex MEDIUM 9: honest naming; skill folder is copyable + symlink-free, NOT bundle-self-contained for full execution)"
      pattern: "copytree\\|repo_root"
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
    tests/conftest.py — `repo_root` fixture from Plan 10-00 Task 3 (Round-2 codex HIGH 1: consume this fixture, NOT `skill_root.parent.parent.parent.parent`);
    .claude/skills/mortgage-ops/scripts/amortize.py — verify --help works without lib/ (D-18 fast --help);
    orchestration/db-write.mjs lines 296-310 — REAL Phase 9 CLI surface for the SKLL-13 end-to-end smoke (insert-loan / insert-scenario / insert-report --scenario-id --file / query --sql); Round-2 codex HIGH 2 forbids the fictional `--insert-report --json` and `--query "..."` flag forms;
    orchestration/init-db.mjs — schema bootstrapper used in STEP 2 of the SKLL-13 smoke; reports table schema is `(id, scenario_id NOT NULL, markdown_blob TEXT NOT NULL, generated_at TIMESTAMP)` with NO `filename` column
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


def test_skill_artifact_copyability_with_repo_pythonpath(
    skill_root: Path, repo_root: Path, tmp_path: Path
) -> None:
    """Copy .claude/skills/mortgage-ops/ to tmp_path and verify each relocated
    script's --help still works from the copy. ALSO run amortize.py end-to-end
    from the copy with `PYTHONPATH` pointing at the repo root so `lib.*` is
    importable.

    Round-2 codex MEDIUM 9: renamed from `test_skill_folder_self_contained_portability`.
    The original name overstated the contract — the skill folder is NOT
    bundle-self-contained for full execution because `lib/*` lives at the
    repo root and the copied scripts inject `parents[4]` to find it. From a
    copy under `/tmp`, `parents[4]` no longer points at the repo root, so
    `from lib.amortize import ...` fails unless `PYTHONPATH` is set to the
    repo root. This test is honest: it asserts the skill folder is
    COPYABLE (no symlinks, all artifacts resolved) AND the scripts are
    RUNNABLE FROM THE COPY when `PYTHONPATH` is set. A future bundle that
    ships `lib/` inside the skill folder (or installs it as a pip package)
    would lift the PYTHONPATH dependency, but that is out of scope for
    Phase 10.

    Round-2 codex HIGH 1: consumes `repo_root` fixture from Plan 10-00 Task 3
    (replacing prior `skill_root.parent.parent.parent.parent` overshoot)."""
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
        env={**__import__("os").environ, "PYTHONPATH": str(repo_root)},
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
            env={**__import__("os").environ, "PYTHONPATH": str(repo_root)},
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


def test_no_user_layer_files_committed_in_skill_folder(
    skill_root: Path, repo_root: Path
) -> None:
    """DATA_CONTRACT enforcement: modes/_profile.md (User Layer) MUST NOT
    appear in the git index. The file MAY exist on a developer machine
    (User Layer; gitignored), but it must NOT be in the committed tree.

    The .gitignore (Plan 10-03 Task 3 PART A) + the pre-commit hook
    (Plan 10-03 Task 3 PART C) together prevent the file from being committed.
    This test is the tertiary backstop in CI: a developer who accidentally
    committed it via `git add -f` would trip both layers; this test catches
    a slip-through.

    Per codex LOW concern 15: prior version had a tautological
    `... or True` assertion which made the working-tree existence check
    meaningless. Removed that assertion. The git-index check below is the
    real gate.

    Round-2 codex HIGH 1: consumes `repo_root` fixture from Plan 10-00 Task 3
    (replacing prior `skill_root.parent.parent.parent.parent` overshoot).
    """
    # The real gate: assert the file is NOT in git's index. Working-tree
    # presence is fine (User Layer may exist locally); only the INDEX matters.
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
    skill_root: Path, repo_root: Path, tmp_path: Path
) -> None:
    """SKLL-13 end-to-end smoke (D-13-01..D-13-05): exercises the Save Report
    path concretely against the REAL Phase 9 CLI from
    `orchestration/db-write.mjs:296-310` and the REAL `reports` schema from
    `orchestration/init-db.mjs:76-82`.

    Round-2 codex HIGH 2: prior draft used the fictional `--query "..."` and
    `--insert-report --json '{...}'` flag forms (neither exists on the real
    handler) and queried by a `filename` column that does NOT exist on the
    `reports` table. The reports schema is `(id PK, scenario_id NOT NULL,
    markdown_blob TEXT NOT NULL, generated_at TIMESTAMP)` — there is no
    `filename` column; the file on disk IS the durable filename anchor and
    persistence stores `(scenario_id, markdown_blob)` keyed by scenario_id.
    Round-2 codex HIGH 1: consumes `repo_root` fixture from Plan 10-00.

    The test runs against an isolated DuckDB under `tmp_path` (via the
    Phase 9 `MORTGAGE_OPS_DB_PATH` env-var override per Plan 09-00 D-00-04),
    so it does not pollute the developer's main `data/mortgage-ops.duckdb`
    nor require try/finally cleanup of rows in the live DB.

    7-step flow (REAL CLI; matches modes/_shared.md Save Report doctrine):
      1. Allocate a tmp DuckDB path
      2. `node orchestration/init-db.mjs` — bootstrap schema (idempotent;
         loans / scenarios / reports tables exist after this)
      3. `node orchestration/db-write.mjs insert-loan --json <loan.json>` —
         capture loan_id from stdout `{"ok": true, "loan_id": <int>}`
      4. `node orchestration/db-write.mjs insert-scenario --loan-id <id>
         --kind amortize --json <scenario.json>` — capture scenario_id
         from stdout `{"ok": true, "scenario_id": <int>, ...}`
      5. Construct filename per D-13-02: `reports/{NNN:03d}-{mode}-{date}.md`
         (NNN derived from `query --sql "SELECT COUNT(*)+1 ..."` against
         the temp DB) and write it under tmp_path
      6. `node orchestration/db-write.mjs insert-report --scenario-id <id>
         --file <path>` — REAL CLI per orchestration/db-write.mjs:306
      7. Verify via `node orchestration/db-write.mjs query --sql "SELECT
         scenario_id, markdown_blob FROM reports WHERE scenario_id = <id>"`
         — expect 1 row with markdown_blob equal to the file contents.
         Filename is NOT verified in the DB (no such column); the file on
         disk is the anchor.

    NOTE: this test depends on `node` + `orchestration/db-write.mjs` being
    operational (Phase 9 PERS-03). If `which node` returns nothing or the
    handler is missing, the test SKIPS rather than fails (Phase 9 contract
    is the precondition).
    """
    import json as _json
    import os as _os
    import shutil as _shutil
    from datetime import date as _date

    if _shutil.which("node") is None:
        pytest.skip("node not on PATH; SKLL-13 end-to-end smoke requires Phase 9 orchestration")

    db_write = repo_root / "orchestration" / "db-write.mjs"
    init_db = repo_root / "orchestration" / "init-db.mjs"
    if not db_write.is_file():
        pytest.skip(f"orchestration/db-write.mjs not found at {db_write}; Phase 9 prerequisite")
    if not init_db.is_file():
        pytest.skip(f"orchestration/init-db.mjs not found at {init_db}; Phase 9 prerequisite")

    # ------------------------------------------------------------
    # STEP 1 — allocate isolated tmp DuckDB; subsequent steps target it
    # via MORTGAGE_OPS_DB_PATH (Plan 09-00 D-00-04 env-var override).
    # ------------------------------------------------------------
    tmp_db = tmp_path / "mortgage-ops-test.duckdb"
    env = {**_os.environ, "MORTGAGE_OPS_DB_PATH": str(tmp_db)}

    # ------------------------------------------------------------
    # STEP 2 — bootstrap schema (idempotent per Phase 9 PERS-01)
    # ------------------------------------------------------------
    init_result = subprocess.run(
        ["node", str(init_db)],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=30, env=env,
    )
    assert init_result.returncode == 0, (
        f"init-db.mjs failed: {init_result.stderr[:500]}"
    )
    assert tmp_db.is_file(), f"DB not created at {tmp_db}"

    # ------------------------------------------------------------
    # STEP 3 — insert a loan (Phase 9 cmdInsertLoan; required fields per
    # lib.models.Loan: principal, annual_rate, term_months, loan_type;
    # money fields MUST be JSON strings per D-03-03)
    # ------------------------------------------------------------
    loan_json = tmp_path / "loan.json"
    loan_json.write_text(_json.dumps({
        "principal": "200000.00",
        "annual_rate": "0.065000",
        "term_months": 360,
        "origination_date": "2026-05-01",
        "loan_type": "fixed",
        "frequency": "monthly",
    }))
    loan_result = subprocess.run(
        ["node", str(db_write), "insert-loan", "--json", str(loan_json)],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=30, env=env,
    )
    assert loan_result.returncode == 0, f"insert-loan failed: {loan_result.stderr[:500]}"
    loan_payload = _json.loads(loan_result.stdout)
    loan_id = int(loan_payload["loan_id"])
    assert loan_id >= 1

    # ------------------------------------------------------------
    # STEP 4 — insert a scenario referencing the loan (Phase 9
    # cmdInsertScenario; payload must have {request, response} keys per
    # PERS-05 contract). Capture scenario_id from stdout.
    # ------------------------------------------------------------
    scenario_json = tmp_path / "scenario.json"
    scenario_json.write_text(_json.dumps({
        "request": {"mode": "amortize", "loan_id": loan_id},
        "response": {"monthly_payment": "1264.14", "total_interest": "255143.06"},
    }))
    scen_result = subprocess.run(
        [
            "node", str(db_write), "insert-scenario",
            "--loan-id", str(loan_id),
            "--kind", "amortize",
            "--json", str(scenario_json),
        ],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=30, env=env,
    )
    assert scen_result.returncode == 0, f"insert-scenario failed: {scen_result.stderr[:500]}"
    scen_payload = _json.loads(scen_result.stdout)
    scenario_id = int(scen_payload["scenario_id"])
    assert scenario_id >= 1

    # ------------------------------------------------------------
    # STEP 5 — derive next sequence number + write the report file at
    # the D-13-02 path (under tmp_path so we don't pollute repo reports/)
    # ------------------------------------------------------------
    seq_result = subprocess.run(
        [
            "node", str(db_write), "query",
            "--sql", "SELECT COUNT(*)+1 AS next_seq FROM reports",
        ],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert seq_result.returncode == 0, f"query failed: {seq_result.stderr[:500]}"
    seq_parsed = _json.loads(seq_result.stdout)
    # cmdQuery returns a JSON array (per orchestration/db-write.mjs cmdQuery)
    assert isinstance(seq_parsed, list) and seq_parsed, f"query returned no rows: {seq_parsed!r}"
    next_seq = int(seq_parsed[0]["next_seq"])
    assert next_seq >= 1

    today = _date.today().isoformat()
    mode = "amortize"
    expected_basename = f"{next_seq:03d}-{mode}-{today}.md"
    expected_relpath = f"reports/{expected_basename}"

    # Validate filename matches D-13-02 regex
    import re as _re
    pattern = (
        r"^reports/\d{3}-(?:evaluate|compare|refinance|affordability|"
        r"stress|amortize|arm)-\d{4}-\d{2}-\d{2}\.md$"
    )
    assert _re.match(pattern, expected_relpath), (
        f"D-13-02 filename violation: {expected_relpath!r} does not match {pattern!r}"
    )

    report_body = "# SKLL-13 End-to-End Smoke\n\nGenerated by Plan 10-06.\n"
    report_path = tmp_path / expected_basename
    report_path.write_text(report_body)
    assert report_path.is_file()

    # ------------------------------------------------------------
    # STEP 6 — REAL CLI: insert-report --scenario-id <int> --file <path>
    # (Round-2 codex HIGH 2: this is the actual subcommand surface;
    # `--insert-report --json '{...}'` is fictional and forbidden)
    # ------------------------------------------------------------
    ins_result = subprocess.run(
        [
            "node", str(db_write), "insert-report",
            "--scenario-id", str(scenario_id),
            "--file", str(report_path),
        ],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=30, env=env,
    )
    assert ins_result.returncode == 0, (
        f"insert-report failed: {ins_result.stderr[:500]}"
    )
    ins_payload = _json.loads(ins_result.stdout)
    assert ins_payload.get("ok") is True
    assert ins_payload.get("scenario_id") == scenario_id

    # ------------------------------------------------------------
    # STEP 7 — verify by query (NOT by filename — schema has no such column)
    # ------------------------------------------------------------
    check_result = subprocess.run(
        [
            "node", str(db_write), "query",
            "--sql", (
                f"SELECT scenario_id, markdown_blob FROM reports "
                f"WHERE scenario_id = {scenario_id}"
            ),
        ],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert check_result.returncode == 0, f"verify query failed: {check_result.stderr}"
    check_parsed = _json.loads(check_result.stdout)
    assert isinstance(check_parsed, list)
    assert len(check_parsed) == 1, (
        f"SKLL-13 D-13-04: expected 1 row in reports for scenario_id={scenario_id}, "
        f"got {len(check_parsed)}"
    )
    row = check_parsed[0]
    assert int(row["scenario_id"]) == scenario_id
    assert row["markdown_blob"] == report_body, (
        "DB markdown_blob should equal the file contents byte-for-byte"
    )
    # Filename anchor is the file on disk (not a column). Verify the file
    # exists at the D-13-02 path (already asserted above) and the blob round-
    # tripped intact through the handler.

    # No try/finally cleanup needed — the entire DB lives under tmp_path
    # and goes away when pytest tears the fixture down.
```

Hygiene constraints:
- mypy --strict clean
- ruff clean (imports sorted; line length ≤ 100)
- subprocess.run timeouts set (max 30s per node invocation)
- shutil.copytree handles the copy (not manual file-by-file)
- pytest.skip used for missing node/db-write.mjs (don't fail when Phase 9 prereq absent)
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_skill_integration.py -v &amp;&amp; mypy --strict tests/test_skill_integration.py &amp;&amp; ruff check tests/test_skill_integration.py &amp;&amp; ruff format --check tests/test_skill_integration.py &amp;&amp; ! grep -F 'or True' tests/test_skill_integration.py &amp;&amp; ! grep -E '4500.*-.*200|4300' tests/test_skill_integration.py &amp;&amp; ! grep -F 'skill_root.parent.parent.parent.parent' tests/test_skill_integration.py &amp;&amp; ! grep -F -- '--insert-report --json' tests/test_skill_integration.py &amp;&amp; ! grep -F 'db-write.mjs --query' tests/test_skill_integration.py &amp;&amp; grep -F 'insert-report --scenario-id' tests/test_skill_integration.py &amp;&amp; grep -F 'test_skill_artifact_copyability_with_repo_pythonpath' tests/test_skill_integration.py</automated>
  </verify>
  <acceptance_criteria>
- File exists with ≥ 90 lines
- 4 test functions defined: copyability (renamed per Round-2 codex MEDIUM 9), token-budget, User-Layer-leak, SKLL-13 end-to-end
- All 4 tests PASS (or SKLL-13 end-to-end SKIPS cleanly if `node`/db-write.mjs/init-db.mjs are absent)
- Copyability test: NO symlinks in skill folder copy
- Copyability test: ALL 7 relocated calc scripts' --help works from copy
- Copyability test: amortize.py runs end-to-end from copy with `PYTHONPATH=<repo_root>` (Round-2 codex MEDIUM 9: honest claim — skill folder is copyable + symlink-free, NOT bundle-self-contained)
- Copyability test renamed to `test_skill_artifact_copyability_with_repo_pythonpath` (Round-2 codex MEDIUM 9)
- All 4 tests consume `repo_root` fixture (Round-2 codex HIGH 1: NOT `skill_root.parent.parent.parent.parent`)
- `grep -F 'skill_root.parent.parent.parent.parent' tests/test_skill_integration.py` returns 0 matches (Round-2 codex HIGH 1)
- Token budget test: SKILL.md ≤ 4500 cl100k tokens (NOT a stricter sub-cap; codex MEDIUM concern 13)
- User Layer leak test: NO `... or True` no-op assertion (codex LOW concern 15: removed)
- User Layer leak test: _profile.md NOT in git index (real assertion)
- SKLL-13 test: walks the 7-step flow against isolated tmp DuckDB (init-db + insert-loan + insert-scenario + write report file + insert-report --scenario-id --file + query --sql). Verification is by scenario_id + markdown_blob byte-equality (NOT by filename — schema has no such column). Round-2 codex HIGH 2.
- `grep -F 'insert-report --scenario-id' tests/test_skill_integration.py` returns ≥ 1 (REAL CLI present)
- `grep -F -- '--insert-report --json' tests/test_skill_integration.py` returns 0 (fictional CLI absent — Round-2 codex HIGH 2)
- `grep -F 'db-write.mjs --query' tests/test_skill_integration.py` returns 0 (fictional flag absent — Round-2 codex HIGH 2)
- mypy --strict + ruff clean
  </acceptance_criteria>
  <done>
    Copyability smoke (with full script run via repo PYTHONPATH; honest claim per Round-2 codex MEDIUM 9) + token budget at official cap + User Layer leak check (no tautology) + SKLL-13 end-to-end smoke against REAL Phase 9 CLI (Round-2 codex HIGH 2) all pass; all four tests consume `repo_root` fixture (Round-2 codex HIGH 1).
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

- test_skill_artifact_copyability_with_repo_pythonpath (RENAMED per Round-2
  codex MEDIUM 9): copytree .claude/skills/mortgage-ops/ to tmp dir, walk
  tree asserting no symlinks, smoke ALL 7 relocated calc scripts' --help
  from the copy, AND run amortize.py end-to-end with PYTHONPATH=<repo_root>
  so lib.* resolves. The honest claim is artifact copyability + symlink
  freedom (validating D-01 MOVE choice over symlink/shim) — NOT bundle
  self-containment for full execution. If a future edit introduces a
  symlink or breaks artifact resolution, this fails at PR time.

- test_skill_md_token_budget_at_phase_end: end-of-phase token re-check at
  the OFFICIAL ≤ 4500 cap from CONTEXT.md / SKLL-01 / D-02. No stricter
  sub-cap is enforced (revised per codex review — prior version had a 4300
  hard gate that was tighter than the documented decision).

- test_no_user_layer_files_committed_in_skill_folder: tertiary backstop for
  the DATA_CONTRACT triple (.gitignore + pre-commit hook + this CI test) —
  asserts modes/_profile.md is NOT in the git index. Removed the prior
  tautological \\`... or True\\` working-tree assertion (codex LOW concern).

- test_skll_13_end_to_end_save_report_writes_file_and_db_row (NEW;
  Round-2 codex HIGH 2): exercises the Save Report path against the REAL
  Phase 9 CLI surface from orchestration/db-write.mjs:296-310 — walks
  init-db -> insert-loan -> insert-scenario -> write report file ->
  \\`insert-report --scenario-id <int> --file <path>\\` -> verify by
  \\`query --sql "SELECT scenario_id, markdown_blob ..."\\`. Runs against
  an isolated tmp DuckDB via MORTGAGE_OPS_DB_PATH (Plan 09-00 D-00-04 env
  override) so no live-DB cleanup is needed. Schema has no \\`filename\\`
  column; verification is by scenario_id + markdown_blob byte-equality.
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
| T-10-44 | Tampering (SKLL-13 closure verified at modes/ layer but not at runtime) | end-to-end smoke | mitigate | Task 1 ships test_skll_13_end_to_end_save_report_writes_file_and_db_row which exercises the REAL Phase 9 CLI surface from orchestration/db-write.mjs:296-310 (insert-report --scenario-id <int> --file <path>) against an isolated tmp DuckDB (MORTGAGE_OPS_DB_PATH override per Plan 09-00 D-00-04). Verification is by `scenario_id + markdown_blob` round-trip (the reports schema has no `filename` column). Round-2 codex HIGH 2 closes the prior gap where the test referenced fictional flag forms. |
| T-10-45 | DoS (token-budget false-fail at strict-than-cap threshold) | SKILL.md token check | mitigate | Task 1 token test pinned at the OFFICIAL 4500 cap from CONTEXT.md; no stricter sub-cap unless added by a documented decision (per codex MEDIUM concern 13) |
| T-10-52 | Tampering (path-arithmetic overshoot in integration tests) | tests/test_skill_integration.py | mitigate | Round-2 codex HIGH 1: all 4 integration tests consume the `repo_root` fixture from Plan 10-00 Task 3 (NOT `skill_root.parent.parent.parent.parent`). Task 1 acceptance grep-blocks the overshoot pattern. |
| T-10-53 | Tampering (skill folder claimed self-contained but actually requires lib/ on PYTHONPATH) | copyability test naming | mitigate | Round-2 codex MEDIUM 9: test renamed to `test_skill_artifact_copyability_with_repo_pythonpath`; must-have describes the honest claim (copyable + symlink-free + runnable WITH repo PYTHONPATH); a future bundle could lift the PYTHONPATH dependency |
</threat_model>

<verification>
- 1 new test file exists with 4 functions
- Copyability copy + tree-walk + 7-script --help + 1 full-script-run with repo PYTHONPATH all pass (renamed per Round-2 codex MEDIUM 9)
- All 4 tests consume `repo_root` fixture (Round-2 codex HIGH 1: NOT `skill_root.parent.parent.parent.parent`)
- Token budget check passes (≤ 4500 cl100k — official cap; no stricter sub-cap)
- User Layer leak check passes (_profile.md not in git index; no `... or True` tautology)
- SKLL-13 end-to-end smoke: walks REAL Phase 9 CLI (init-db + insert-loan + insert-scenario + insert-report --scenario-id --file + query --sql verify by scenario_id+markdown_blob) — Round-2 codex HIGH 2; or skips cleanly if node/db-write.mjs/init-db.mjs missing
- Full suite: ≥ 593 passed + 0 Phase 10 xfails + ≤ 1 total xfail + 0 failed + 0 errored
- All ROADMAP SC-1..SC-5 specifically verified by named test invocations
- mypy + ruff clean across full project surface
- Commit landed without AI attribution
</verification>

<success_criteria>
- Phase 10 SHIPPED end-to-end
- ROADMAP SC-1..SC-5 all closed (audit verified by Task 2 PART B)
- ALL 13 SKLL-XX requirements have binding CI assertions (SKLL-13 closes via Wave 5 unit-level + Wave 6 end-to-end per D-13-01..D-13-05)
- Skill folder is COPYABLE + symlink-free; full script invocation from the copy works WITH repo lib/ on PYTHONPATH (HONEST claim per Round-2 codex MEDIUM 9; renamed test = test_skill_artifact_copyability_with_repo_pythonpath)
- SKILL.md fits the OFFICIAL ≤ 4500 cl100k token cap (no stricter sub-cap)
- DATA_CONTRACT User Layer triple-enforcement verified end-to-end (no tautological assertions)
- Cross-phase contract D-08 RETIRED (all 7 scripts in skill folder)
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-06-SUMMARY.md` documenting:
- 4 integration tests added (copyability with 7-script --help + full-run via repo PYTHONPATH per Round-2 codex MEDIUM 9, token-budget at official cap, User Layer leak without tautology, SKLL-13 end-to-end via REAL Phase 9 CLI per Round-2 codex HIGH 2)
- Final pass count (must be ≥ 593)
- ROADMAP SC-1..SC-5 audit results (each criterion + test name + pass/fail)
- Phase 10 net contribution: lines of code added, tests added, requirements closed
- SKLL-13 closure note: Phase 10 closes SKLL-13 fully via Wave 5 (unit-level _shared.md assertions targeting the REAL `insert-report --scenario-id` CLI) + Wave 6 (end-to-end smoke walking init-db → insert-loan → insert-scenario → insert-report --scenario-id --file → query --sql verify) per CONTEXT.md D-13-01..D-13-05; verification is by scenario_id+markdown_blob (no `filename` column on the schema)
- D-08 retirement note: all 7 calc scripts now in skill folder; no further "ship to root then relocate" pattern
- Open items for Phase 11/12 (Phase 11 subagent files + Phase 12 FRED/eval)
</output>
</content>
</invoke>