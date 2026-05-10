"""Phase 10 cross-cutting integration smoke tests.

These tests do NOT close a specific SKLL-XX requirement; they enforce
SKILL-PORTABILITY — the principle that motivated D-01 (MOVE not symlink/shim).

If a future edit introduces a symlink in the skill folder, or hardcodes an
absolute path that points outside the skill folder, or otherwise breaks the
self-contained property, the portability smoke test FAILS — surfacing the
regression at PR time.

Plan 10-06 also adds the SKLL-13 end-to-end smoke that walks the REAL Phase 9
CLI surface from `orchestration/db-write.mjs:296-310` (init-db -> insert-loan
-> insert-scenario -> insert-report --scenario-id <int> --file <path> ->
query --sql) against an isolated tmp DuckDB. This is the runtime-level
confirmation of SKLL-13's closure (Wave 5 added the unit-level _shared.md
assertions).

Round-2 codex fixes preserved here:
- HIGH 1: every test consumes the `repo_root` fixture from conftest.py;
  no chained-`.parent`-overshoot path arithmetic.
- HIGH 2: SKLL-13 smoke uses the REAL CLI subcommand surface
  (`insert-report --scenario-id <int> --file <path>`); no fictional flag
  forms; no `filename` column lookup (the schema has no such column).
- MEDIUM 9: copyability test renamed to
  `test_skill_artifact_copyability_with_repo_pythonpath` to honestly
  describe the contract (skill folder is copyable + symlink-free, NOT
  bundle-self-contained for full execution because lib/ lives at repo root
  and the copied scripts inject parents[4] for sys.path).
- MEDIUM 13: token-budget test gates at the OFFICIAL cap from
  CONTEXT.md / SKLL-01 / D-02; no stricter sub-cap.
- LOW 15: User Layer leak test has no tautological no-op assertions; the
  `git ls-files` invocation is the real gate.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from typing import TYPE_CHECKING

import pytest

from tests._skill_helpers import count_tokens

if TYPE_CHECKING:
    from pathlib import Path

# 7 calc scripts physically relocated to .claude/skills/mortgage-ops/scripts/
# per Plan 10-01 (SKLL-10) — verified end-to-end here.
RELOCATED_SCRIPTS: tuple[str, ...] = (
    "amortize.py",
    "affordability.py",
    "arm_simulate.py",
    "refi_npv.py",
    "apr_reg_z.py",
    "stress_test.py",
    "points_breakeven.py",
)

# D-13-02 filename regex used by the SKLL-13 smoke when synthesizing the
# next-sequence report path (mode in {7-mode set}, ISO date suffix).
REPORT_FILENAME_PATTERN = (
    r"^reports/\d{3}-(?:evaluate|compare|refinance|affordability|"
    r"stress|amortize|arm)-\d{4}-\d{2}-\d{2}\.md$"
)


def test_skill_artifact_copyability_with_repo_pythonpath(
    skill_root: Path, repo_root: Path, tmp_path: Path
) -> None:
    """Copy .claude/skills/mortgage-ops/ to tmp_path and verify each relocated
    script's --help still works from the copy. ALSO run amortize.py end-to-end
    from the copy with `PYTHONPATH` pointing at the repo root so `lib.*` is
    importable.

    Round-2 codex MEDIUM 9: renamed for honesty — the original name
    overstated the contract. The skill folder is NOT bundle-self-contained
    for full execution because `lib/*` lives at the repo root and the copied
    scripts inject `parents[4]` to find it. From a copy under `/tmp`,
    `parents[4]` no longer points at the repo root, so `from lib.amortize
    import ...` fails unless `PYTHONPATH` is set to the repo root. This
    test is honest: it asserts the skill folder is COPYABLE (no symlinks,
    all artifacts resolved) AND the scripts are RUNNABLE FROM THE COPY
    when `PYTHONPATH` is set. A future bundle that ships `lib/` inside the
    skill folder (or installs it as a pip package) would lift the PYTHONPATH
    dependency, but that is out of scope for Phase 10.

    Round-2 codex HIGH 1: consumes `repo_root` fixture from Plan 10-00 Task 3
    (replaces prior chained-.parent path arithmetic that overshot the repo).
    """
    skill_copy = tmp_path / "mortgage-ops"
    shutil.copytree(skill_root, skill_copy)

    # Verify the copy carries the structural artifacts.
    assert (skill_copy / "SKILL.md").is_file(), "SKILL.md missing from copy"
    assert (skill_copy / "LICENSE.txt").is_file(), "LICENSE.txt missing from copy"
    assert (skill_copy / "scripts").is_dir(), "scripts/ missing from copy"
    assert (skill_copy / "modes").is_dir(), "modes/ missing from copy"
    assert (skill_copy / "references").is_dir(), "references/ missing from copy"

    # D-01 MOVE-not-symlink contract: walk the tree and assert each entry is
    # NOT a symlink. Symlinks would dangle when the folder is copied to
    # another machine, breaking the SKILL-PORTABILITY principle.
    for path in skill_copy.rglob("*"):
        assert not path.is_symlink(), (
            f"Portability violation: {path.relative_to(skill_copy)} is a symlink. "
            f"Per D-01 (Plan 10-01) the skill folder MUST be symlink-free; "
            f"symlinks dangle when the folder is copied to another machine."
        )

    # Smoke A: --help exits 0 from the copy for all 7 relocated calc scripts.
    # Phase 3 D-18 lazy-imports lib/ AFTER argparse, so --help works without
    # requiring the lib package on sys.path.
    for name in RELOCATED_SCRIPTS:
        script = skill_copy / "scripts" / name
        assert script.is_file(), f"Copy missing {name}"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"{name} --help failed from copy (exit {result.returncode}).\n"
            f"stderr: {result.stderr[:500]}\n"
            f"This indicates the skill folder is NOT artifact-self-contained "
            f"(D-01 contract violated)."
        )

    # Smoke B (codex MEDIUM 12 / MEDIUM 9 honest scope): run amortize.py
    # end-to-end from the COPY with PYTHONPATH=<repo_root> so `lib.amortize`
    # resolves. This proves the COPIED script can run end-to-end without
    # breaking on missing companion files (e.g., _cli_helpers.py) inside the
    # skill folder. lib/ is supplied by PYTHONPATH; a future bundled deploy
    # would lift that dependency.
    amortize_input = tmp_path / "amortize-input.json"
    amortize_input.write_text(
        json.dumps(
            {
                "loan": {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                }
            }
        )
    )
    amortize_script = skill_copy / "scripts" / "amortize.py"
    result = subprocess.run(
        [sys.executable, str(amortize_script), "--input", str(amortize_input)],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(repo_root)},
    )
    assert result.returncode == 0, (
        f"Portability smoke B: amortize.py from COPY exited {result.returncode}.\n"
        f"stdout: {result.stdout[:300]}\nstderr: {result.stderr[:500]}\n"
        f"The skill folder is not honestly copyable + runnable with repo PYTHONPATH."
    )
    # Sanity: the JSON payload echoes the input loan principal back into stdout
    # (full schedule output also includes per-period rows).
    assert "200000.00" in result.stdout, (
        f"amortize.py output did not echo input principal; stdout: {result.stdout[:300]}"
    )


def test_skill_md_token_budget_at_phase_end(skill_root: Path) -> None:
    """Final-wave runtime check: SKILL.md is at or under the OFFICIAL <= 4500
    cl100k token cap from CONTEXT.md / SKLL-01 / D-02 (5000 Anthropic spec
    minus 10% margin for cl100k-vs-Anthropic-tokenizer drift).

    Per codex MEDIUM concern 13: this test enforces ONLY the documented cap
    that already binds in CONTEXT.md. No stricter sub-cap is enforced unless
    explicitly tied to a documented CONTEXT.md decision. Plan 10-05
    test_skill_md_under_token_budget already pins this at Wave 5; this is
    the Wave 6 final re-check confirming nothing slipped past during Waves 3-5.
    """
    skill_md = (skill_root / "SKILL.md").read_text()
    n_tokens = count_tokens(skill_md)
    assert n_tokens <= 4500, (
        f"SKILL.md is {n_tokens} cl100k tokens; budget 4500 (CONTEXT.md / SKLL-01 / D-02). "
        f"Reduce SKILL.md or move content to references/ (progressive disclosure SKLL-09)."
    )


def test_no_user_layer_files_committed_in_skill_folder(repo_root: Path) -> None:
    """DATA_CONTRACT enforcement: modes/_profile.md (User Layer) MUST NOT
    appear in the git index. The file MAY exist on a developer machine
    (User Layer; gitignored), but it must NOT be in the committed tree.

    The .gitignore (Plan 10-03 Task 3 PART A) + the pre-commit hook
    (Plan 10-03 Task 3 PART C) together prevent the file from being committed.
    This test is the tertiary backstop in CI: a developer who accidentally
    committed it via `git add -f` would trip both layers; this test catches
    a slip-through.

    Per codex LOW concern 15: prior version had a tautological no-op
    assertion which made the working-tree existence check meaningless.
    Removed that assertion. The git-index check below is the real gate.

    Round-2 codex HIGH 1: consumes `repo_root` fixture from Plan 10-00 Task 3
    (replaces prior chained-.parent path arithmetic that overshot the repo).
    """
    # The real gate: assert the file is NOT in git's index. Working-tree
    # presence is fine (User Layer may exist locally); only the INDEX matters.
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            ".claude/skills/mortgage-ops/modes/_profile.md",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    # Exit 0 = file IS in index (bad — User Layer leak); non-zero = NOT in index (good).
    assert result.returncode != 0, (
        "DATA_CONTRACT violation: .claude/skills/mortgage-ops/modes/_profile.md is "
        "in the git index. This is User Layer per DATA_CONTRACT.md. Run "
        "`git rm --cached .claude/skills/mortgage-ops/modes/_profile.md` and re-commit."
    )

    # Defense-in-depth: also scan committed history for any commit that
    # touched User Layer artifacts INSIDE the skill folder (live duckdb,
    # household.yml, _profile.md). The hook should have prevented these from
    # ever landing; this is a tertiary CI check.
    #
    # `--all` traverses every ref so a User Layer leak on a feature branch
    # would also be caught (matters more once the project has multiple long-
    # lived refs; on a clean linear repo it's fast). Timeout is generous
    # (60s) to absorb cold-cache first runs on machines with deep packfiles.
    leak_patterns = (
        ".claude/skills/mortgage-ops/modes/_profile.md",
        ".claude/skills/mortgage-ops/config/household.yml",
        ".claude/skills/mortgage-ops/data/mortgage-ops.duckdb",
    )
    for path in leak_patterns:
        log_result = subprocess.run(
            ["git", "log", "--all", "--oneline", "--", path],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert log_result.stdout.strip() == "", (
            f"DATA_CONTRACT violation: {path} appears in git history.\n"
            f"Offending commits:\n{log_result.stdout}"
        )


def test_skll_13_end_to_end_save_report_writes_file_and_db_row(
    repo_root: Path, tmp_path: Path
) -> None:
    """SKLL-13 end-to-end smoke (D-13-01..D-13-05): exercises the Save Report
    path concretely against the REAL Phase 9 CLI from
    `orchestration/db-write.mjs:296-310` and the REAL `reports` schema from
    `orchestration/init-db.mjs:76-82`.

    Round-2 codex HIGH 2: prior draft used fictional flag forms (neither
    exists on the real handler) and queried by a `filename` column that does
    NOT exist on the `reports` table. The reports schema is
    `(id PK, scenario_id NOT NULL, markdown_blob TEXT NOT NULL,
    generated_at TIMESTAMP)` — there is no `filename` column; the file on
    disk IS the durable filename anchor and persistence stores
    `(scenario_id, markdown_blob)` keyed by scenario_id.
    Round-2 codex HIGH 1: consumes `repo_root` fixture from Plan 10-00.

    The test runs against an isolated DuckDB under `tmp_path` (via the
    Phase 9 `MORTGAGE_OPS_DB_PATH` env-var override per Plan 09-00 D-00-04),
    so it does not pollute the developer's main `data/mortgage-ops.duckdb`
    nor require try/finally cleanup of rows in the live DB.

    7-step flow (REAL CLI; matches modes/_shared.md Save Report doctrine):
      1. Allocate a tmp DuckDB path
      2. `node orchestration/init-db.mjs` -- bootstrap schema (idempotent;
         loans / scenarios / reports tables exist after this)
      3. `node orchestration/db-write.mjs insert-loan --json <loan.json>` --
         capture loan_id from stdout `{"ok": true, "loan_id": <int>}`
      4. `node orchestration/db-write.mjs insert-scenario --loan-id <id>
         --kind amortize --json <scenario.json>` -- capture scenario_id
         from stdout `{"ok": true, "scenario_id": <int>, ...}`
      5. Construct filename per D-13-02: `reports/{NNN:03d}-{mode}-{date}.md`
         (NNN derived from `query --sql "SELECT COUNT(*)+1 ..."` against
         the temp DB) and write it under tmp_path
      6. `node orchestration/db-write.mjs insert-report --scenario-id <id>
         --file <path>` -- REAL CLI per orchestration/db-write.mjs:306
      7. Verify via `node orchestration/db-write.mjs query --sql "SELECT
         scenario_id, markdown_blob FROM reports WHERE scenario_id = <id>"`
         -- expect 1 row with markdown_blob equal to the file contents.
         Filename is NOT verified in the DB (no such column); the file on
         disk is the anchor.

    NOTE: this test depends on `node` + `orchestration/db-write.mjs` being
    operational (Phase 9 PERS-03). If `which node` returns nothing or the
    handler is missing, the test SKIPS rather than fails (Phase 9 contract
    is the precondition).
    """
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; SKLL-13 end-to-end smoke requires Phase 9 orchestration")

    db_write = repo_root / "orchestration" / "db-write.mjs"
    init_db = repo_root / "orchestration" / "init-db.mjs"
    if not db_write.is_file():
        pytest.skip(f"orchestration/db-write.mjs not found at {db_write}; Phase 9 prerequisite")
    if not init_db.is_file():
        pytest.skip(f"orchestration/init-db.mjs not found at {init_db}; Phase 9 prerequisite")

    # ------------------------------------------------------------
    # STEP 1 - allocate isolated tmp DuckDB; subsequent steps target it
    # via MORTGAGE_OPS_DB_PATH (Plan 09-00 D-00-04 env-var override).
    # ------------------------------------------------------------
    tmp_db = tmp_path / "mortgage-ops-test.duckdb"
    env = {**os.environ, "MORTGAGE_OPS_DB_PATH": str(tmp_db)}

    # ------------------------------------------------------------
    # STEP 2 - bootstrap schema (idempotent per Phase 9 PERS-01)
    # ------------------------------------------------------------
    init_result = subprocess.run(
        ["node", str(init_db)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert init_result.returncode == 0, f"init-db.mjs failed: {init_result.stderr[:500]}"
    assert tmp_db.is_file(), f"DB not created at {tmp_db}"

    # ------------------------------------------------------------
    # STEP 3 - insert a loan (Phase 9 cmdInsertLoan; required fields per
    # lib.models.Loan: principal, annual_rate, term_months, loan_type;
    # money fields MUST be JSON strings per D-03-03)
    # ------------------------------------------------------------
    loan_json = tmp_path / "loan.json"
    loan_json.write_text(
        json.dumps(
            {
                "principal": "200000.00",
                "annual_rate": "0.065000",
                "term_months": 360,
                "origination_date": "2026-05-01",
                "loan_type": "fixed",
                "frequency": "monthly",
            }
        )
    )
    loan_result = subprocess.run(
        ["node", str(db_write), "insert-loan", "--json", str(loan_json)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert loan_result.returncode == 0, f"insert-loan failed: {loan_result.stderr[:500]}"
    loan_payload = json.loads(loan_result.stdout)
    loan_id = int(loan_payload["loan_id"])
    assert loan_id >= 1

    # ------------------------------------------------------------
    # STEP 4 - insert a scenario referencing the loan (Phase 9
    # cmdInsertScenario; payload must have {request, response} keys per
    # PERS-05 contract). Capture scenario_id from stdout.
    # ------------------------------------------------------------
    scenario_json = tmp_path / "scenario.json"
    scenario_json.write_text(
        json.dumps(
            {
                "request": {"mode": "amortize", "loan_id": loan_id},
                "response": {"monthly_payment": "1264.14", "total_interest": "255143.06"},
            }
        )
    )
    scen_result = subprocess.run(
        [
            "node",
            str(db_write),
            "insert-scenario",
            "--loan-id",
            str(loan_id),
            "--kind",
            "amortize",
            "--json",
            str(scenario_json),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert scen_result.returncode == 0, f"insert-scenario failed: {scen_result.stderr[:500]}"
    scen_payload = json.loads(scen_result.stdout)
    scenario_id = int(scen_payload["scenario_id"])
    assert scenario_id >= 1

    # ------------------------------------------------------------
    # STEP 5 - derive next sequence number + write the report file at
    # the D-13-02 path (under tmp_path so we don't pollute repo reports/)
    # ------------------------------------------------------------
    seq_result = subprocess.run(
        [
            "node",
            str(db_write),
            "query",
            "--sql",
            "SELECT COUNT(*)+1 AS next_seq FROM reports",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert seq_result.returncode == 0, f"query failed: {seq_result.stderr[:500]}"
    seq_parsed = json.loads(seq_result.stdout)
    # cmdQuery returns a JSON array (per orchestration/db-write.mjs cmdQuery).
    assert isinstance(seq_parsed, list), f"query did not return a list: {seq_parsed!r}"
    assert seq_parsed, f"query returned no rows: {seq_parsed!r}"
    next_seq = int(seq_parsed[0]["next_seq"])
    assert next_seq >= 1

    today = date.today().isoformat()
    mode = "amortize"
    expected_basename = f"{next_seq:03d}-{mode}-{today}.md"
    expected_relpath = f"reports/{expected_basename}"

    # Validate filename matches D-13-02 regex.
    assert re.match(REPORT_FILENAME_PATTERN, expected_relpath), (
        f"D-13-02 filename violation: {expected_relpath!r} does not match "
        f"{REPORT_FILENAME_PATTERN!r}"
    )

    report_body = "# SKLL-13 End-to-End Smoke\n\nGenerated by Plan 10-06.\n"
    report_path = tmp_path / expected_basename
    report_path.write_text(report_body)
    assert report_path.is_file()

    # ------------------------------------------------------------
    # STEP 6 - REAL CLI: insert-report --scenario-id <int> --file <path>
    # (Round-2 codex HIGH 2: this is the actual subcommand surface;
    # the prior fictional flag forms are forbidden)
    # ------------------------------------------------------------
    ins_result = subprocess.run(
        [
            "node",
            str(db_write),
            "insert-report",
            "--scenario-id",
            str(scenario_id),
            "--file",
            str(report_path),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert ins_result.returncode == 0, f"insert-report failed: {ins_result.stderr[:500]}"
    ins_payload = json.loads(ins_result.stdout)
    assert ins_payload.get("ok") is True
    assert ins_payload.get("scenario_id") == scenario_id

    # ------------------------------------------------------------
    # STEP 7 - verify by query (NOT by filename - schema has no such column)
    # ------------------------------------------------------------
    check_result = subprocess.run(
        [
            "node",
            str(db_write),
            "query",
            "--sql",
            (f"SELECT scenario_id, markdown_blob FROM reports WHERE scenario_id = {scenario_id}"),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert check_result.returncode == 0, f"verify query failed: {check_result.stderr}"
    check_parsed = json.loads(check_result.stdout)
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
    # Filename anchor is the file on disk (already asserted above); the blob
    # round-tripped intact through the handler. No try/finally cleanup needed
    # — the entire DB lives under tmp_path and goes away on fixture teardown.
