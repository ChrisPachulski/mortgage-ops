---
phase: 09
plan: 07
type: execute
wave: 7
depends_on:
  - "09-00"
  - "09-01"
  - "09-02"
  - "09-03"
  - "09-04"
  - "09-05"
  - "09-06"
files_modified:
  - references/data-layer.md
  - .gitignore
  - DATA_CONTRACT.md
  - tests/test_orchestration/test_gitignore_phase09.py
must_haves:
  truths:
    - "references/data-layer.md exists with sections: Schema Overview, Lockfile Mechanics, Render-Markdown Determinism, Onboarding Walkthrough"
    - ".gitignore appends explicit per-file lines (NOT data/* wildcards): data/.mortgage-ops.duckdb.lock + data/.lock; reports/*.md already covered by Phase 1 reports/* with !reports/.gitkeep whitelist preserved"
    - "data/known-loans.yml remains tracked by git after the .gitignore changes (Reference Layer placement preserved per D-05-01)"
    - "DATA_CONTRACT.md updated with explicit Phase 9 Layer Examples section: data/known-loans.yml is Reference Layer (committed) vs data/mortgage-ops.duckdb is Data Layer (gitignored)"
    - "tests/test_orchestration/test_gitignore_phase09.py asserts: each Phase 9 .gitignore entry exists; data/known-loans.yml is NOT ignored; data/mortgage-ops.duckdb IS ignored; reports/.gitkeep is NOT ignored; reports/foo.md IS ignored"
    - "references/data-layer.md is NOT loaded by any skill yet (D-01 — Phase 10 will progressive-disclose); it lives at repo root references/ directory, not under .claude/skills/"
    - "Phase 9 documentation surface complete and ready for Phase 10 to depend on"
  artifacts:
    - path: "references/data-layer.md"
      provides: "Phase 9 data layer reference doc — schema, lockfile, render determinism, onboarding"
      contains: "Schema Overview"
    - path: ".gitignore"
      provides: "Phase 9 entries appended (explicit per-file, no wildcards that block known-loans.yml)"
      contains: "data/.mortgage-ops.duckdb.lock"
    - path: "DATA_CONTRACT.md"
      provides: "Updated with concrete Reference vs Data Layer enforcement examples for Phase 9 artifacts"
      contains: "Phase 9 Layer Examples"
    - path: "tests/test_orchestration/test_gitignore_phase09.py"
      provides: "Regression guard for .gitignore correctness; catches accidental data/* wildcard regressions"
      contains: "def test_gitignore_phase09_entries_present"
  key_links:
    - from: ".gitignore"
      to: "data/.mortgage-ops.duckdb.lock + reports/*.md"
      via: "explicit per-file gitignore lines"
      pattern: "data/.mortgage-ops.duckdb.lock"
    - from: "DATA_CONTRACT.md"
      to: "data/known-loans.yml (Reference) vs data/mortgage-ops.duckdb (Data)"
      via: "layer-classification table + cross-reference notes"
      pattern: "Reference.*known-loans"
    - from: "tests/test_orchestration/test_gitignore_phase09.py"
      to: "git check-ignore subprocess calls + .gitignore line parsing"
      via: "subprocess.run(git check-ignore) + Path('.gitignore').read_text()"
      pattern: "git.*check-ignore"
autonomous: true
requirements: []
tags:
  - phase-09
  - duckdb-orchestration
  - documentation
  - gitignore
  - data-contract
  - references
---

<objective>
**Goal:** Ship the Phase 9 documentation + ignore-hygiene closure: (1) `references/data-layer.md` describing the schema, lockfile mechanics, render determinism, and onboarding walkthrough; (2) explicit `.gitignore` entries for the lockfile (using per-file lines, NOT `data/*` wildcards which would block `data/known-loans.yml`); (3) `DATA_CONTRACT.md` cross-reference clarifying Reference vs Data Layer for Phase 9 artifacts; (4) a regression test that pins the .gitignore correctness so future edits cannot silently break Reference-Layer commits.

**Purpose:** Phase 9 closure is more than passing tests. The system needs (a) onboarding documentation so a future developer (or a future Claude session) can understand the lockfile/init/render-markdown contracts without re-reading 1000-line PLANs, (b) gitignore entries that the orchestration layer expects to exist (data/.mortgage-ops.duckdb.lock leaks into git status if not ignored — RESEARCH §Pitfall 5), and (c) a load-bearing regression test that catches the most-common gitignore mistake: an over-broad `data/*` wildcard that silently un-tracks `data/known-loans.yml` (which would break Phase 10 + Phase 12 routing).

**Output:** 1 new reference doc (~150-250 lines under `references/`), 2-4 new lines appended to `.gitignore`, 1 new section appended to `DATA_CONTRACT.md`, 1 new regression test (~80-120 lines under `tests/test_orchestration/`).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/09-duckdb-orchestration/09-PATTERNS.md
@.planning/phases/09-duckdb-orchestration/09-RESEARCH.md
@CLAUDE.md
@DATA_CONTRACT.md
@.gitignore
@orchestration/init-db.mjs
@orchestration/db-write.mjs
@orchestration/lockfile.mjs

<interfaces>
**Reference doc target path:** `references/data-layer.md` (repo-root `references/` directory, NOT `.claude/skills/.../references/`).

**Why repo-root references/ and not skills/:** D-07-01 — Phase 10 has not yet shipped `.claude/skills/mortgage-ops/`; Phase 9 references live at repo-root for now. Phase 10 will EITHER move them under the skill OR symlink them OR progressive-disclose them via SKILL.md `references:` frontmatter. Decision deferred to Phase 10.

**Existing repo-root `references/` directory state (verify before writing):**
- `ls references/` — if missing, create with `mkdir -p references`.
- Phase 2 created `data/reference/` (different — that is the Reference Layer YAML directory, not the skill references directory).

**.gitignore current state (relevant Phase 9 lines, from earlier phases):**
```
# Data Layer (generated)
data/*.duckdb
data/market/
data/mortgage-ops.duckdb-wal
data/mortgage-ops.duckdb-shm

# Reports (generated)
reports/*
!reports/.gitkeep
```

`data/*.duckdb` already covers `data/mortgage-ops.duckdb` via wildcard. Phase 9 must ADD explicit lines for the lockfile + ensure data/known-loans.yml is NOT ignored. Per D-02 (NOT data/* wildcard), use explicit per-file additions.

**.gitignore Phase 9 additions (D-02 — verbatim):**
```
# Phase 9: DuckDB writer lockfile (ephemeral) — RESEARCH Pitfall 5
data/.mortgage-ops.duckdb.lock
data/.lock
```

The existing `data/*.duckdb` already handles `data/mortgage-ops.duckdb`. The existing `reports/*` + `!reports/.gitkeep` already handles `reports/*.md`. What this plan ADDS is just the lockfile entries.

**Sanity post-edit (must hold):**
| Path | Expected git check-ignore exit |
|------|-------------------------------|
| data/mortgage-ops.duckdb | 0 (ignored) |
| data/mortgage-ops.duckdb-wal | 0 (ignored) |
| data/mortgage-ops.duckdb-shm | 0 (ignored) |
| data/.mortgage-ops.duckdb.lock | 0 (ignored) |
| data/known-loans.yml | 1 (NOT ignored — Reference Layer) |
| reports/.gitkeep | 1 (NOT ignored — seam file) |
| reports/foo.md | 0 (ignored — generated) |

**DATA_CONTRACT.md update target:** the existing file (75 lines) already enumerates Reference Layer (line 56-69) including `data/known-loans.yml` (line 67). What this plan ADDS is a "Phase 9 Layer Examples" section after the existing "Layer Cross-References" (around line 75) clarifying that Phase 9 artifacts are split: catalog YAML = Reference (committed); DuckDB file = Data (gitignored AND User Layer dual-classification per existing line 50).

**Test naming convention (Wave 0 D-00 Rule-1 inheritance):** new tests under `tests/test_orchestration/` follow `test_<noun>_<verb>.py` pattern; this plan adds `test_gitignore_phase09.py` (ignore-rule regression).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create references/data-layer.md (Phase 9 documentation)</name>
  <files>references/data-layer.md</files>
  <read_first>
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md (full RESEARCH document — Pinned schema DDL, Lockfile mechanics, Render determinism, Pitfalls)
    - .planning/phases/09-duckdb-orchestration/09-PATTERNS.md (Pattern Assignments + Critical Issues)
    - DATA_CONTRACT.md (layer definitions — link from references back to the contract)
    - orchestration/init-db.mjs (final shipped schema; cite line ranges)
    - orchestration/lockfile.mjs (final shipped lockfile primitives; cite line ranges)
    - orchestration/db-write.mjs (final shipped subcommand list; cite cmdRenderMarkdown line range)
  </read_first>
  <action>
    Create `references/data-layer.md` as the Phase 9 onboarding + reference document. Target ~150-250 lines.

    **Step 1 — Verify directory exists** (create if missing):
    ```
    mkdir -p references
    ```

    **Step 2 — Write `references/data-layer.md`** with the following 8 mandatory sections (in order). Section content templates below; the executor MUST cross-reference the actual line numbers / file ranges / subcommand names from the shipped Phase 9 code and update placeholder citations to concrete refs.

    Mandatory sections:

    1. **Header** — title + 1-paragraph framing + bullet list of source artifacts (init-db.mjs, db-write.mjs, lockfile.mjs, known-loans.yml, mortgage-ops.duckdb, loans.md/scenarios.md, .mortgage-ops.duckdb.lock).

    2. **Schema Overview** — list the 6 tables (loans, scenarios, reports, payments, applicants, properties); describe primary columns + DECIMAL widths (DECIMAL(14,2) for money, DECIMAL(10,6) for rates); cite `orchestration/init-db.mjs` as source of truth; note IF NOT EXISTS idempotency.

    3. **Decimal-String Discipline** — explain the bigint-on-SELECT problem; CAST AS VARCHAR rule; INSERT-as-string rule; Python re-parse to Decimal from strings; cite RESEARCH Pitfall 1 + Plan 09-03 D-03-02 + the regression test `test_decimal_string_round_trip_preserves_cents`.

    4. **Lockfile Mechanics** — JSON shape (pid + acquired_at + reason); 4-step acquire protocol (read, check stale via 60s threshold, write, read-back verify); release protocol (unconditional unlinkSync in finally); race window analysis (RESEARCH Pitfall 2); 60s stale-recovery threshold; why not O_EXCL (NFS broken); cite `tests/test_orchestration/test_parallel_invocation.py` + `test_stale_lockfile_recovery.py`.

    5. **Render-Markdown Determinism** — three rules: explicit ORDER BY id ASC; no generated_at NOW() in body; mandatory `<!-- Generated from data/mortgage-ops.duckdb - edit via scripts, not directly -->` header at line 1; cite Plan 09-04 D-04-01..04 + tests `test_render_markdown.py` (Wave 4) + `test_render_markdown_byte_identical.py` (Wave 6).

    6. **Reference Layer vs Data Layer (Phase 9 disambiguation)** — table mapping each Phase 9 artifact to layer + commit status + purpose; mention common mistake (over-broad data/* wildcard); cite `tests/test_orchestration/test_gitignore_phase09.py` as the regression guard.

    7. **Onboarding Walkthrough** — numbered step-by-step from fresh clone through first insert + render: `npm install`, `uv sync`, `node orchestration/init-db.mjs`, write a fixture loan to /tmp/loan.json, `node orchestration/db-write.mjs insert-loan --json /tmp/loan.json`, `node orchestration/db-write.mjs render-markdown`, `cat data/loans.md`, verify catalog with Python yaml.safe_load.

    8. **When Things Go Wrong** — symptom -> cause -> fix table covering: IO Error file lock (DuckDB OS lock), bigint serialize error (missing CAST), loans.md drift (missing ORDER BY or generated_at), lockfile not in gitignore, known-loans.yml accidentally ignored.

    9. **Cross-References** — link to plans, RESEARCH, PATTERNS, DATA_CONTRACT.md, CLAUDE.md, career-ops precedent paths.

    10. **Future Work** — Phase 10 progressive disclosure decision, v2 lockfile hardening (proper-lockfile), v2 cross-process Python read access.

    **Step 3 — Adjust based on shipped reality.** Cross-reference actual line numbers / file ranges / subcommand names from shipped Phase 9 code. Replace placeholder citations (e.g., "RESEARCH Pattern 1") with concrete line ranges where possible. The 10-section structure is mandatory; contents are guided by shipped reality. Length target 150-250 lines (concise but complete).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && test -f references/data-layer.md && wc -l references/data-layer.md && grep -cE '^## ' references/data-layer.md</automated>
  </verify>
  <acceptance_criteria>
    - `test -f references/data-layer.md` exits 0
    - `wc -l references/data-layer.md` reports at least 100 lines (target 150-250)
    - `grep -cE '^## Schema Overview' references/data-layer.md` returns 1
    - `grep -cE '^## Lockfile Mechanics' references/data-layer.md` returns 1
    - `grep -cE '^## Render-Markdown Determinism' references/data-layer.md` returns 1
    - `grep -cE '^## Onboarding Walkthrough' references/data-layer.md` returns 1
    - `grep -cE '^## Reference Layer vs Data Layer' references/data-layer.md` returns 1
    - `grep -c 'data/known-loans.yml' references/data-layer.md` returns at least 3
    - `grep -cE '60s|60 seconds|60_000' references/data-layer.md` returns at least 1
    - `grep -c 'ORDER BY id ASC' references/data-layer.md` returns at least 1
    - `grep -cE 'CAST AS VARCHAR|CAST.*VARCHAR' references/data-layer.md` returns at least 1
    - `grep -c 'RESEARCH' references/data-layer.md` returns at least 3
  </acceptance_criteria>
  <done>
    references/data-layer.md exists with all 10 mandatory sections; cites lockfile threshold, render determinism rules, decimal discipline; cross-references DATA_CONTRACT.md and shipped orchestration code.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append Phase 9 .gitignore entries (lockfile only — no data/* wildcards)</name>
  <files>.gitignore</files>
  <read_first>
    - .gitignore (current state — verify what is already present from Phase 1/2)
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md Pitfall 5 (gitignore for lockfile)
    - DATA_CONTRACT.md line 67 (data/known-loans.yml MUST remain committed)
  </read_first>
  <action>
    Append Phase 9 entries to `.gitignore`. Use explicit per-file lines (D-02 — NOT `data/*` wildcards).

    **Step 1 — Verify current .gitignore state** to determine what is already covered:

    Run: `grep -nE 'duckdb|\.lock|reports' .gitignore`

    Expected from earlier phases:
    - `data/*.duckdb` (Phase 1) — already covers `data/mortgage-ops.duckdb`
    - `data/mortgage-ops.duckdb-wal` (Phase 1) — sidecar
    - `data/mortgage-ops.duckdb-shm` (Phase 1) — sidecar
    - `reports/*` + `!reports/.gitkeep` (Phase 1) — already covers `reports/*.md` with seam preserved

    **Step 2 — Append the Phase 9 lockfile entries** (the only NEW entries needed):

    Use the Edit tool to APPEND to the end of `.gitignore` (do NOT rewrite the file). Add this exact block:

    ```
    # Phase 9: DuckDB writer lockfile (ephemeral) — RESEARCH Pitfall 5
    data/.mortgage-ops.duckdb.lock
    data/.lock
    ```

    **Why both `.mortgage-ops.duckdb.lock` AND `.lock`:** `.mortgage-ops.duckdb.lock` is the production lockfile name (per orchestration/lockfile.mjs); `.lock` is a defensive catch-all in case a future refactor renames the file. Both are explicit per-file names, neither is a `data/*.lock` wildcard (which would also be safe but is less explicit; we prefer explicit lines for greppability).

    **Step 3 — Sanity-check post-edit:**

    Run each of these commands and verify expected exit codes:
    - `git check-ignore data/mortgage-ops.duckdb` — expect exit 0 (ignored — was already covered by data/*.duckdb)
    - `git check-ignore data/.mortgage-ops.duckdb.lock` — expect exit 0 (ignored — NEW)
    - `git check-ignore data/known-loans.yml` — expect exit 1 (NOT ignored — Reference Layer)
    - `git check-ignore reports/.gitkeep` — expect exit 1 (NOT ignored — seam preserved)
    - `git check-ignore reports/foo.md` — expect exit 0 (ignored)

    **CRITICAL:** if `git check-ignore data/known-loans.yml` returns exit 0 (ignored), STOP — there is an over-broad rule in .gitignore (likely a stray `data/*`). The plan's load-bearing constraint (D-05-01: known-loans.yml MUST be committed as Reference Layer) is violated. Add a `!data/known-loans.yml` whitelist line BEFORE proceeding, OR investigate which existing rule is over-broad and fix it.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && grep -c "data/.mortgage-ops.duckdb.lock" .gitignore && grep -c "data/.lock" .gitignore && (git check-ignore data/known-loans.yml; test $? -eq 1) && git check-ignore data/mortgage-ops.duckdb && git check-ignore data/.mortgage-ops.duckdb.lock && echo "all ignore-checks pass"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "data/.mortgage-ops.duckdb.lock" .gitignore` returns 1
    - `grep -c "data/.lock" .gitignore` returns 1
    - There is no bare `data/*` wildcard line in .gitignore (verify manually with `grep -nE '^data/\*\s*$' .gitignore` returning empty)
    - `git check-ignore data/mortgage-ops.duckdb` exits 0 (ignored — Data Layer)
    - `git check-ignore data/.mortgage-ops.duckdb.lock` exits 0 (ignored — ephemeral)
    - `git check-ignore data/known-loans.yml` exits 1 (NOT ignored — Reference Layer)
    - `git check-ignore reports/.gitkeep` exits 1 (NOT ignored — seam)
    - `git check-ignore reports/foo.md` exits 0 (ignored — generated)
    - `grep -c "Phase 9" .gitignore` returns at least 1 (section comment for archeology)
  </acceptance_criteria>
  <done>
    .gitignore appended with Phase 9 lockfile entries; data/known-loans.yml remains tracked; data/mortgage-ops.duckdb + lockfile remain ignored; seam files preserved.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update DATA_CONTRACT.md with Phase 9 layer disambiguation</name>
  <files>DATA_CONTRACT.md</files>
  <read_first>
    - DATA_CONTRACT.md (current state — 75 lines)
    - .planning/phases/09-duckdb-orchestration/09-05-known-loans-catalog-PLAN.md (Plan 09-05 D-05-01: data/known-loans.yml is Reference Layer)
    - .planning/phases/09-duckdb-orchestration/09-PATTERNS.md (Pattern Assignments for Phase 9 artifacts)
  </read_first>
  <action>
    Add a Phase 9 disambiguation section to DATA_CONTRACT.md. The existing file already enumerates `data/known-loans.yml` (line 67) and `data/mortgage-ops.duckdb` (lines 20, 50). What this plan ADDS is a new "Phase 9 Layer Examples" section AFTER the existing "Layer Cross-References" section (current line 71-75). Use the Edit tool to APPEND; do NOT rewrite the file.

    Append exactly this block to the end of DATA_CONTRACT.md:

    ```
    ## Phase 9 Layer Examples

    Phase 9 ships artifacts that span three layers; the per-artifact rules:

    | Artifact | Layer(s) | Committed? | Rationale |
    |----------|----------|------------|-----------|
    | `data/known-loans.yml` | Reference | YES | Product catalog (7 entries); manually refreshed; carries `source:` + `effective:` keys per line 69 convention |
    | `data/mortgage-ops.duckdb` | Data + User (dual) | NO (gitignored) | Generated by `orchestration/init-db.mjs`; contains user-private scenarios (User Layer rule applies); regenerable from System Layer + User Layer + Reference Layer (Data Layer rule applies) |
    | `data/mortgage-ops.duckdb-wal` | Data | NO (gitignored) | DuckDB write-ahead log sidecar |
    | `data/mortgage-ops.duckdb-shm` | Data | NO (gitignored) | DuckDB shared-memory sidecar |
    | `data/.mortgage-ops.duckdb.lock` | Data (ephemeral) | NO (gitignored) | Writer coordination via Plan 09-01 lockfile.mjs; appears only while a writer is active; 60s stale-recovery threshold |
    | `data/loans.md` | Data | NO (gitignored) | Generated view of `loans` table; regenerated by `orchestration/db-write.mjs render-markdown`; byte-identical contract |
    | `data/scenarios.md` | Data | NO (gitignored) | Generated view of `scenarios` table; same regeneration contract |
    | `orchestration/init-db.mjs` | System | YES | Schema bootstrapper |
    | `orchestration/db-write.mjs` | System | YES | Central writer (insert-loan, insert-scenario, insert-report, render-markdown, query) |
    | `orchestration/lockfile.mjs` | System | YES | acquireLock/releaseLock/withLock primitives |

    **Critical rule:** `data/known-loans.yml` is Reference Layer (committed),
    NOT Data Layer (gitignored). An over-broad `data/*` entry in `.gitignore`
    would silently un-track the catalog and break Phase 10 + Phase 12 routing.
    Plan 09-07 uses explicit per-file `.gitignore` lines
    (`data/.mortgage-ops.duckdb.lock`, `data/.lock`) to avoid this trap.
    The regression test `tests/test_orchestration/test_gitignore_phase09.py`
    pins the rule.

    **Cross-reference:** the Phase 9 reference doc `references/data-layer.md`
    contains the full schema overview, lockfile mechanics, render
    determinism, and onboarding walkthrough.
    ```

    **Sanity-check post-edit:**
    - `grep -c "Phase 9 Layer Examples" DATA_CONTRACT.md` returns 1
    - `grep -c "data/known-loans.yml" DATA_CONTRACT.md` returns at least 2 (existing line 67 + new section)
    - `grep -c "references/data-layer.md" DATA_CONTRACT.md` returns at least 1 (cross-reference)
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && grep -c "Phase 9 Layer Examples" DATA_CONTRACT.md && grep -c "data/known-loans.yml" DATA_CONTRACT.md && grep -c "references/data-layer.md" DATA_CONTRACT.md && grep -c "60s stale-recovery" DATA_CONTRACT.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "## Phase 9 Layer Examples" DATA_CONTRACT.md` returns 1
    - `grep -c "data/known-loans.yml" DATA_CONTRACT.md` returns at least 2
    - `grep -c "references/data-layer.md" DATA_CONTRACT.md` returns at least 1
    - `grep -c "60s stale-recovery" DATA_CONTRACT.md` returns at least 1
    - `grep -c "Reference Layer" DATA_CONTRACT.md` returns at least 4 (existing 3 + new section)
    - `grep -c "data/mortgage-ops.duckdb" DATA_CONTRACT.md` returns at least 4 (existing 3 + new table row)
    - The "Phase 9 Layer Examples" section appears AFTER the existing "Layer Cross-References" section (verify with `grep -n` line numbers)
  </acceptance_criteria>
  <done>
    DATA_CONTRACT.md updated with Phase 9 Layer Examples table + critical rule + cross-reference; existing sections preserved unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 4: Write tests/test_orchestration/test_gitignore_phase09.py (regression guard)</name>
  <files>tests/test_orchestration/test_gitignore_phase09.py</files>
  <read_first>
    - .gitignore (post-Task-2 state)
    - tests/conftest.py (REPO_ROOT helper)
    - tests/test_orchestration/test_init_db_idempotent.py (Plan 09-06 — for subprocess.run pattern reference)
  </read_first>
  <action>
    Write a NEW file `tests/test_orchestration/test_gitignore_phase09.py` that pins the .gitignore correctness via two complementary mechanisms:

    1. **Line-presence checks** — read .gitignore as text, assert the Phase 9 entries appear verbatim. Catches accidental deletion.
    2. **Behavioral checks** — invoke `git check-ignore` on representative paths, assert each path's ignore status matches the layer rule. Catches over-broad-wildcard regressions (e.g., someone replaces explicit lines with `data/*`).

    File content:

    ```python
    """Phase 9 .gitignore regression test (Plan 09-07).

    Two complementary mechanisms:

    1. Line-presence: assert specific Phase 9 entries appear in .gitignore.
       Catches accidental deletion.
    2. Behavioral: invoke `git check-ignore` on representative paths; assert
       each path's ignore status matches its DATA_CONTRACT layer rule.
       Catches over-broad-wildcard regressions (e.g., someone replaces
       explicit per-file lines with `data/*` which would silently un-track
       data/known-loans.yml — Plan 09-05 D-05-01 violation).
    """

    from __future__ import annotations

    import subprocess
    from pathlib import Path

    from tests.conftest import REPO_ROOT

    GITIGNORE: Path = REPO_ROOT / ".gitignore"

    # Line-presence assertions (Phase 9 additions per Plan 09-07 D-02)
    REQUIRED_GITIGNORE_LINES: tuple[str, ...] = (
        "data/.mortgage-ops.duckdb.lock",
        "data/.lock",
    )


    def _git_check_ignore(path: str) -> int:
        """Invoke `git check-ignore` from REPO_ROOT; return the exit code.
        Exit 0 = path IS ignored. Exit 1 = path is NOT ignored.
        """
        result = subprocess.run(
            ["git", "check-ignore", path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        return result.returncode


    def test_gitignore_phase09_entries_present() -> None:
        """Plan 09-07 D-02: explicit per-file lockfile entries appear in
        .gitignore. Catches accidental deletion."""
        assert GITIGNORE.exists(), f".gitignore not found at {GITIGNORE}"
        content = GITIGNORE.read_text()

        for line in REQUIRED_GITIGNORE_LINES:
            assert line in content, (
                f"Plan 09-07 violation: .gitignore is missing required Phase 9 "
                f"entry {line!r}; ephemeral lockfile would leak into git status. "
                f"See RESEARCH Pitfall 5."
            )


    def test_gitignore_known_loans_NOT_ignored() -> None:
        """Plan 09-05 D-05-01 + DATA_CONTRACT.md line 67: data/known-loans.yml
        is Reference Layer and MUST be committed. An over-broad `data/*`
        wildcard in .gitignore would silently un-track it, breaking Phase 10
        and Phase 12 product routing.
        """
        rc = _git_check_ignore("data/known-loans.yml")
        assert rc == 1, (
            f"Plan 09-05 D-05-01 violation: data/known-loans.yml is being "
            f"ignored by git (check-ignore exit {rc}). Likely cause: an "
            f"over-broad `data/*` wildcard in .gitignore. Fix: replace with "
            f"explicit per-file lines OR add `!data/known-loans.yml` whitelist."
        )


    def test_gitignore_duckdb_file_IS_ignored() -> None:
        """DATA_CONTRACT.md line 50: data/mortgage-ops.duckdb is Data Layer
        (gitignored). Existing Phase 1 rule `data/*.duckdb` covers this."""
        rc = _git_check_ignore("data/mortgage-ops.duckdb")
        assert rc == 0, (
            f"data/mortgage-ops.duckdb is NOT ignored (check-ignore exit {rc}); "
            f"Data Layer file is at risk of accidental commit. Likely cause: "
            f"the Phase 1 `data/*.duckdb` line was removed from .gitignore."
        )


    def test_gitignore_lockfile_IS_ignored() -> None:
        """Plan 09-07 D-02 + RESEARCH Pitfall 5: data/.mortgage-ops.duckdb.lock
        is ephemeral writer state and MUST be ignored to prevent stale locks
        being committed (which would block CI for 60s on every clone)."""
        rc = _git_check_ignore("data/.mortgage-ops.duckdb.lock")
        assert rc == 0, (
            f"data/.mortgage-ops.duckdb.lock is NOT ignored "
            f"(check-ignore exit {rc}); ephemeral lockfile is at risk of "
            f"being committed. Plan 09-07 Task 2 missed adding this entry."
        )


    def test_gitignore_reports_seam_preserved() -> None:
        """Phase 1 invariant: reports/.gitkeep MUST be tracked (it preserves
        the empty reports/ directory in git); reports/*.md MUST be ignored
        (generated artifacts)."""
        rc_keeper = _git_check_ignore("reports/.gitkeep")
        assert rc_keeper == 1, (
            f"reports/.gitkeep is being ignored (check-ignore exit {rc_keeper}); "
            f"the seam file would be lost on next clone. Likely cause: the "
            f"`!reports/.gitkeep` whitelist line was removed from .gitignore."
        )

        rc_report = _git_check_ignore("reports/sample-report.md")
        assert rc_report == 0, (
            f"reports/sample-report.md is NOT ignored "
            f"(check-ignore exit {rc_report}); generated user reports could "
            f"leak into git. Likely cause: the `reports/*` Phase 1 line was "
            f"removed from .gitignore."
        )


    def test_gitignore_no_bare_data_wildcard() -> None:
        """Defensive guard: a bare `data/*` line would un-track
        data/known-loans.yml. Plan 09-07 D-02 explicitly forbids this pattern.
        Reading .gitignore as text and grepping for the exact pattern.
        """
        content = GITIGNORE.read_text()
        # Match a line that is exactly `data/*` (with optional surrounding whitespace)
        # but NOT `data/*.duckdb` or `data/*.parquet` (which are scoped).
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "data/*":
                raise AssertionError(
                    f"Plan 09-07 D-02 violation: .gitignore contains a bare "
                    f"`data/*` wildcard line. This silently un-tracks "
                    f"data/known-loans.yml (Reference Layer). Use explicit "
                    f"per-file lines instead, or add `!data/known-loans.yml` "
                    f"whitelist."
                )
    ```

    **Note on the negative test (`test_gitignore_no_bare_data_wildcard`):** this is the load-bearing guard. The other tests catch CURRENT misconfiguration; this one catches FUTURE refactors that "simplify" the .gitignore. Both layers are needed.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_gitignore_phase09.py -v --tb=short 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_orchestration/test_gitignore_phase09.py` exits 0
    - `pytest tests/test_orchestration/test_gitignore_phase09.py -v 2>&1 | grep -c PASSED` returns at least 6 (entries_present + known_loans_NOT + duckdb_IS + lockfile_IS + reports_seam + no_bare_wildcard)
    - `pytest tests/test_orchestration/test_gitignore_phase09.py -v 2>&1 | grep -c FAILED` returns 0
    - `grep -c "REQUIRED_GITIGNORE_LINES" tests/test_orchestration/test_gitignore_phase09.py` returns at least 2
    - `grep -c "git check-ignore\|_git_check_ignore" tests/test_orchestration/test_gitignore_phase09.py` returns at least 6
    - `grep -c "data/known-loans.yml" tests/test_orchestration/test_gitignore_phase09.py` returns at least 2
    - `mypy --strict tests/test_orchestration/test_gitignore_phase09.py` exits 0
    - `ruff check tests/test_orchestration/test_gitignore_phase09.py` exits 0
  </acceptance_criteria>
  <done>
    test_gitignore_phase09.py passes; pins line-presence + behavioral + no-bare-wildcard regression guards.
  </done>
</task>

<task type="auto">
  <name>Task 5: Final verification — Phase 9 closure (suite green, docs shipped, contract updated)</name>
  <files>(verification only)</files>
  <action>
    Final Phase 9 closure verification. After this task, Phase 9 is ready for `/gsd-verify-work`.

    1. Full pytest suite green; xfail count = 0 (was 7 at Wave 0; flipped progressively through Waves 3, 4, 5, 6).
    2. mypy --strict on all of `tests/test_orchestration/`.
    3. ruff check + ruff format --check on all of `tests/test_orchestration/`.
    4. references/data-layer.md exists and has the 10 mandatory sections.
    5. .gitignore has the Phase 9 lockfile entries; data/known-loans.yml is NOT ignored.
    6. DATA_CONTRACT.md has the new "Phase 9 Layer Examples" section.
    7. No leaked artifacts: data/loans.md, data/scenarios.md, data/.mortgage-ops.duckdb.lock all absent post-suite.
    8. Sanity: data/known-loans.yml is tracked (`git ls-files data/known-loans.yml` returns the path).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest -q 2>&1 | tail -3 && mypy --strict tests/test_orchestration/ && ruff check tests/test_orchestration/ && ruff format --check tests/test_orchestration/ && test -f references/data-layer.md && grep -c "## Phase 9 Layer Examples" DATA_CONTRACT.md && (git check-ignore data/known-loans.yml; test $? -eq 1) && git ls-files data/known-loans.yml | grep -q "data/known-loans.yml" && test ! -f data/loans.md && test ! -f data/scenarios.md && test ! -f data/.mortgage-ops.duckdb.lock && echo "PHASE 9 READY FOR VERIFY"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows >= 456 (Wave 6 baseline) + 6-8 (Wave 7 new tests) = >= 462
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ xfailed'` returns no match (zero xfails)
    - `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ failed'` returns no match (zero failures)
    - `mypy --strict tests/test_orchestration/` exits 0
    - `ruff check tests/test_orchestration/` exits 0
    - `ruff format --check tests/test_orchestration/` exits 0
    - `test -f references/data-layer.md` exits 0
    - `grep -c "## Phase 9 Layer Examples" DATA_CONTRACT.md` returns 1
    - `git check-ignore data/known-loans.yml` exits 1 (NOT ignored)
    - `git ls-files data/known-loans.yml` outputs `data/known-loans.yml`
    - `test ! -f data/loans.md` exits 0
    - `test ! -f data/scenarios.md` exits 0
    - `test ! -f data/.mortgage-ops.duckdb.lock` exits 0
  </acceptance_criteria>
  <done>
    Phase 9 fully closed: PERS-01..07 all done; SC-1..SC-5 all pinned; documentation shipped; .gitignore correct; DATA_CONTRACT updated; suite green; no leaked artifacts. Ready for /gsd-verify-work and Phase 10.
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS:**

- **D-07-01: references/data-layer.md is documentation-only — NOT loaded by any skill yet** — rationale: Phase 10 has not yet shipped `.claude/skills/mortgage-ops/SKILL.md`; until it does, there is no skill to load references from. Phase 10 will decide whether to (a) progressive-disclose this doc via SKILL.md `references:` frontmatter, (b) move it under `.claude/skills/mortgage-ops/references/`, or (c) symlink. Plan 09-07 ships the doc at repo-root `references/data-layer.md` so it is reachable today by humans + Claude sessions reading the repo, without prejudging the Phase 10 architecture. Rule-of-three citation: Phase 10 SKLL-08 + SKLL-09 (references load on demand); CLAUDE.md "Skill portability" (references inside `.claude/skills/`); Anthropic skill convention (progressive disclosure).

- **D-07-02: .gitignore Phase 9 additions are EXPLICIT per-file lines (NOT data/* wildcards)** — rationale: a bare `data/*` would silently un-track `data/known-loans.yml` (which is Reference Layer per Plan 09-05 D-05-01 + DATA_CONTRACT.md line 67); the consequence is Phase 10 + Phase 12 routing breaking with no warning until a developer notices the catalog is gone. Explicit per-file lines (`data/.mortgage-ops.duckdb.lock`, `data/.lock`) trade slight verbosity for greppability + safety. Rule-of-three citation: Plan 09-05 D-05-01 (catalog must be committed); RESEARCH Pitfall 5 (lockfile gitignore example uses explicit line); the regression test `test_gitignore_no_bare_data_wildcard` pins this rule.

- **D-07-03: Both `data/.mortgage-ops.duckdb.lock` AND `data/.lock` are added** — rationale: `.mortgage-ops.duckdb.lock` is the production name (per Plan 09-01 lockfile.mjs); `.lock` is a defensive catch-all in case a future refactor renames or adds a sibling lockfile. Two explicit lines is cheaper than debugging a stray .lock file leaking into git status three months from now. Rule-of-three citation: Plan 09-01 lockfile path constant; defensive-engineering pattern (career-ops .gitignore has both `.career-ops.lock` and a generic `.lock` entry); future-proofing against rename refactors.

- **D-07-04: DATA_CONTRACT.md is APPENDED, not rewritten** — rationale: the existing 75 lines are load-bearing for Phases 1-8; rewriting risks subtle regression (e.g., dropping a User Layer enumeration). The new "Phase 9 Layer Examples" section is purely additive — it cross-references existing rules with concrete Phase 9 examples. Rule-of-three citation: established codebase convention (additive doc edits over rewrites); existing DATA_CONTRACT.md "Layer Cross-References" section already uses additive cross-references; the existing User Layer table (line 14-23) is referenced by Plan 1 hooks and must not be touched.

- **D-07-05: test_gitignore_phase09.py uses BOTH line-presence AND behavioral assertions** — rationale: line-presence catches deletion (someone removes the lockfile entry); behavioral catches semantic regression (someone adds `data/*` which un-tracks known-loans.yml). Either alone is insufficient; together they cover both failure surfaces. Rule-of-three citation: defensive testing pattern (positive + negative assertions); Plan 09-06 tests use the same pattern (positive stale-recovery + negative fresh-blocks); the no-bare-wildcard test is the load-bearing future-proofing guard.

- **D-07-06: Plan 09-07 closes ZERO PERS requirements directly (frontmatter `requirements: []`)** — rationale: PERS-01..07 are all closed by Waves 1-6. Plan 09-07 is documentation + ignore hygiene; it ships infrastructure that Phase 9 needs (gitignore correctness, onboarding doc, contract clarity) but does not directly close any REQUIREMENTS.md ID. The empty requirements field is intentional and accurate. Rule-of-three citation: REQUIREMENTS.md PERS-01..07 are all about orchestration code or data, not docs/gitignore; Phase 1's hooks-and-config plans had similar "infrastructure-only" plans with empty requirements; Phase 5's fixtures plan had requirements (because fixtures pin requirement IDs) — by contrast, Plan 09-07 ships docs/hygiene only.

- **D-07-07: references/ directory at repo root, NOT data/reference/** — rationale: `data/reference/` already exists from Phase 2 and contains regulatory YAMLs (conforming-limits, fha-mip-rates, etc.); mixing skill references (markdown docs) with regulatory data (YAMLs) is a categorization error. Skill references go under `references/` at repo root (D-07-01 placement); Phase 10 may later move them under `.claude/skills/mortgage-ops/references/`. Rule-of-three citation: Phase 2 `data/reference/` purpose (YAMLs only); CLAUDE.md "Skill portability" (skill refs under `.claude/skills/.../references/`); the namespace separation is intentional.
</locked_decisions>

<verify_block>
**Verify Block:**

```bash
# 1. references/data-layer.md exists with mandatory sections
test -f references/data-layer.md
wc -l references/data-layer.md
grep -cE '^## (Schema Overview|Lockfile Mechanics|Render-Markdown Determinism|Onboarding Walkthrough|Reference Layer vs Data Layer)' references/data-layer.md  # expect at least 5

# 2. .gitignore has Phase 9 entries; layer rules behave correctly
grep -c "data/.mortgage-ops.duckdb.lock" .gitignore
grep -c "data/.lock" .gitignore
git check-ignore data/mortgage-ops.duckdb        # exit 0 expected
git check-ignore data/.mortgage-ops.duckdb.lock  # exit 0 expected
git check-ignore data/known-loans.yml; test $? -eq 1 && echo "OK known-loans.yml not ignored"
git check-ignore reports/.gitkeep; test $? -eq 1 && echo "OK seam file not ignored"
git check-ignore reports/foo.md                  # exit 0 expected

# 3. DATA_CONTRACT.md has Phase 9 disambiguation
grep -c "## Phase 9 Layer Examples" DATA_CONTRACT.md
grep -c "references/data-layer.md" DATA_CONTRACT.md

# 4. Regression test passes
pytest tests/test_orchestration/test_gitignore_phase09.py -v --tb=short

# 5. Full Phase 9 suite green; xfail = 0
pytest tests/test_orchestration/ -v 2>&1 | tail -30

# 6. Full project suite green
pytest -q 2>&1 | tail -3

# 7. Lint clean
mypy --strict tests/test_orchestration/
ruff check tests/test_orchestration/
ruff format --check tests/test_orchestration/

# 8. data/known-loans.yml is TRACKED by git (Reference Layer)
git ls-files data/known-loans.yml | grep -q "data/known-loans.yml" && echo "OK tracked"

# 9. No leaked artifacts after suite
test ! -f data/loans.md
test ! -f data/scenarios.md
test ! -f data/.mortgage-ops.duckdb.lock

# 10. Phase 9 closure summary
echo "PERS-01..07: ALL CLOSED"
echo "SC-1..SC-5: ALL PINNED"
echo "Phase 9 ready for /gsd-verify-work and Phase 10"
```
</verify_block>

<deviation_rules>
**Deviation Rules:**

- **Rule-1 (no data/* wildcard ever):** D-07-02 forbids bare `data/*` in .gitignore. If the executor sees an opportunity to "simplify" by collapsing the explicit lines into a wildcard + whitelist (`data/* + !data/known-loans.yml`), STOP — the explicit-line pattern is the load-bearing safety net per the regression test. Adding the wildcard + whitelist also works but adds a foot-gun (the whitelist must always sort AFTER the wildcard); explicit lines are simpler.

- **Rule-2 (DATA_CONTRACT.md is appended, not rewritten):** D-07-04. If the executor sees the existing DATA_CONTRACT.md as "messy" and wants to refactor, STOP — Phases 1-8 depend on the exact line numbers in this file (e.g., `scripts/hooks/block-user-layer.py` cross-references DATA_CONTRACT.md by section; refactoring breaks the cross-reference). Append-only.

- **Rule-3 (references/ at repo root for now):** D-07-01 + D-07-07 lock the placement. If the executor wants to "do the right thing" by putting the doc directly under `.claude/skills/mortgage-ops/references/`, STOP — that directory does not exist yet (Phase 10 ships it). Repo-root `references/` is the correct interim placement; Phase 10 will decide the move.

- **Rule-4 (test must include the negative wildcard guard):** D-07-05. If the executor writes only positive tests (line-presence + check-ignore == expected), STOP — the `test_gitignore_no_bare_data_wildcard` is the load-bearing future-proofing guard. Without it, a future refactor can silently break Reference Layer commits.

- **Rule-5 (10 mandatory sections in references/data-layer.md):** Task 1's section structure is non-negotiable. The executor MAY adjust contents to match shipped-code reality, but the section headers + ordering are pinned. If the executor finds a section has nothing useful to say (e.g., "Future Work" is empty), put a 1-2 line placeholder rather than deleting the section.

- **Rule-6 (lint hygiene as Rule-3 deviation):** ruff format may reflow the test file; apply minimal fixes. mypy --strict may flag `subprocess.run` return type — the test uses returncode only; explicit type narrowing via assert isinstance is acceptable.

- **Rule-7 (no Node code touched):** Plan 09-07 is DOC + .gitignore + Python test only. Do NOT modify orchestration/*.mjs files. If the doc reveals a contract bug in the shipped code, surface as a blocker comment — fixes belong in a follow-up wave.
</deviation_rules>

<dependencies>
**Dependencies:**

- **Depends on:** All prior Phase 9 plans (09-00 through 09-06) — the references doc describes shipped behavior, the .gitignore complements shipped artifacts, the test guards shipped layer placement, and DATA_CONTRACT updates cross-reference all shipped Phase 9 surfaces.
- **Blocks:** None within Phase 9. Phase 10 + Phase 12 depend on `data/known-loans.yml` remaining a tracked Reference Layer artifact, which this plan's regression test enforces.
- **Inheritance:** D-05-01 (known-loans.yml is Reference Layer); D-04-01..07 (render determinism contract); D-01..03 (lockfile primitives); CLAUDE.md "Data Contract" + "Money discipline".
- **Forward dependencies:** Phase 10 (SKILL.md may progressive-disclose `references/data-layer.md`). Phase 10 will decide whether to move/symlink the doc into `.claude/skills/mortgage-ops/references/`.
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .gitignore -> tracked vs untracked file set | An over-broad rule silently un-tracks Reference Layer artifacts (catalog, hooks); regression test is the load-bearing guard |
| Reference doc -> human reader | Outdated doc misleads onboarding; cross-references to plans + RESEARCH provide a recovery path |
| DATA_CONTRACT.md -> hooks + CI enforcement | scripts/hooks/block-user-layer.py reads DATA_CONTRACT layer enumeration; mismatches cause hook misbehavior |
| Test fixtures -> production data/ | The gitignore test invokes `git check-ignore` on real paths; non-mutating, no risk |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-34 | Tampering (over-broad data/* wildcard added in future refactor) | .gitignore | mitigate | test_gitignore_no_bare_data_wildcard pins the no-wildcard rule (D-07-02 + D-07-05) |
| T-09-35 | Information Disclosure (data/.mortgage-ops.duckdb.lock leaks PID + writer reason into git history) | lockfile JSON content | mitigate | .gitignore entry prevents commit; even if forced, lockfile contents are non-PII (just PID + timestamp + subcommand name) |
| T-09-36 | Repudiation (Reference Layer catalog accidentally untracked, silently breaking Phase 10/12 routing) | data/known-loans.yml | mitigate | test_gitignore_known_loans_NOT_ignored asserts tracked status; D-07-02 explicit lines (no wildcards) |
| T-09-37 | Tampering (DATA_CONTRACT.md rewrite drops a User Layer enumeration, weakening hook coverage) | DATA_CONTRACT.md | mitigate | D-07-04 mandates append-only; the hooks test (Phase 1) cross-references line numbers and would catch removal |
| T-09-38 | Denial of Service (stale lockfile committed to git; CI clones see 60s+ old lock blocking writes) | lockfile commit | mitigate | .gitignore entry prevents commit; even if forced, Plan 09-01 stale-recovery reclaims at 60s — recovery time bounded |
| T-09-39 | Repudiation (references/data-layer.md goes stale as orchestration evolves) | reference doc freshness | accept | Doc is supplementary to PLAN.md + RESEARCH.md (which are the authoritative sources); cross-references in the doc point readers back to canonical sources; v1 risk acceptance — Phase 10 progressive disclosure may add a freshness check |
</threat_model>

<verification>
- references/data-layer.md exists with all 10 mandatory sections (Header, Schema, Decimal, Lockfile, Render, Layer Disambiguation, Onboarding, Troubleshooting, Cross-Refs, Future Work)
- .gitignore has the Phase 9 lockfile entries (data/.mortgage-ops.duckdb.lock + data/.lock)
- .gitignore has NO bare data/* wildcard line (D-07-02 enforced via regression test)
- DATA_CONTRACT.md has the new Phase 9 Layer Examples section (additive — existing content preserved)
- data/known-loans.yml is tracked by git (Reference Layer placement preserved)
- data/mortgage-ops.duckdb + lockfile + reports/*.md remain ignored
- reports/.gitkeep seam file remains tracked
- test_gitignore_phase09.py passes (6+ tests)
- Full Phase 9 suite green; xfail count = 0; lint clean
- No leaked artifacts: data/loans.md + data/scenarios.md + data/.mortgage-ops.duckdb.lock all absent post-suite
</verification>

<success_criteria>
- Phase 9 documentation surface complete: references/data-layer.md ships
- .gitignore Phase 9 hygiene complete: lockfile entries added without breaking Reference Layer commits
- DATA_CONTRACT.md updated with concrete Phase 9 layer examples
- Regression test prevents future .gitignore mistakes from silently un-tracking known-loans.yml
- Phase 9 closure: PERS-01..07 all closed; SC-1..SC-5 all pinned; doc + hygiene + test layers complete
- Phase 9 ready for /gsd-verify-work followed by Phase 10
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-07-SUMMARY.md` documenting:
- references/data-layer.md line count + section list
- .gitignore additions (2 lines: data/.mortgage-ops.duckdb.lock + data/.lock)
- DATA_CONTRACT.md additions (Phase 9 Layer Examples section)
- test_gitignore_phase09.py test count (6 tests)
- Pass count delta (Wave 6 baseline ~456 -> Wave 7 baseline ~462)
- Full Phase 9 closure report:
  - PERS-01: closed (Wave 2 + Wave 6 fingerprint test)
  - PERS-02: closed (Wave 2 + Wave 6 idempotency test)
  - PERS-03: closed (Wave 3 + Wave 6 wrapper)
  - PERS-04: closed (Wave 1 + Wave 6 stale-recovery test)
  - PERS-05: closed (Wave 1 + Wave 6 parallel-invocation test)
  - PERS-06: closed (Wave 4 + Wave 6 byte-identical test)
  - PERS-07: closed (Wave 5 catalog test)
  - SC-1..SC-5: all pinned
- Documentation surface ready for Phase 10 progressive-disclosure decision
- Note: Phase 9 ready for /gsd-verify-work
</output>
</content>
