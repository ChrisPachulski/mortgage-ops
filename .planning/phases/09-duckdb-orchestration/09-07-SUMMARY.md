---
phase: 09-duckdb-orchestration
plan: 07
subsystem: documentation

tags:
  - phase-09
  - duckdb-orchestration
  - documentation
  - references
  - gitignore
  - data-contract
  - regression-test

# Dependency graph
requires:
  - phase: 09-duckdb-orchestration
    plan: 00
    provides: "tests/test_orchestration/ package + REPO_ROOT export from conftest"
  - phase: 09-duckdb-orchestration
    plan: 01
    provides: "orchestration/lockfile.mjs source-of-truth for the lockfile mechanics section"
  - phase: 09-duckdb-orchestration
    plan: 02
    provides: "orchestration/init-db.mjs DDL_STATEMENTS source-of-truth for the schema overview section"
  - phase: 09-duckdb-orchestration
    plan: 03
    provides: "orchestration/db-write.mjs subcommand surface (insert-loan/insert-scenario/insert-report/query) cited in onboarding walkthrough"
  - phase: 09-duckdb-orchestration
    plan: 04
    provides: "orchestration/db-write.mjs cmdRenderMarkdown source-of-truth for the render-determinism section"
  - phase: 09-duckdb-orchestration
    plan: 05
    provides: "data/known-loans.yml as the canonical Reference Layer artifact in the layer-disambiguation table"
  - phase: 09-duckdb-orchestration
    plan: 06
    provides: "tests/test_orchestration/test_init_db_idempotent.py + test_parallel_invocation.py + test_stale_lockfile_recovery.py + test_render_markdown_byte_identical.py — cited as regression tests in the reference doc"
provides:
  - "references/data-layer.md (358 lines) — Phase 9 onboarding + reference doc with all 5 plan-mandated section headers (Schema Overview, Lockfile Mechanics, Render-Markdown Determinism, Onboarding Walkthrough, Reference Layer vs Data Layer) plus 4 supporting sections (Decimal-String Discipline, When Things Go Wrong, Cross-References, Future Work)"
  - ".gitignore (+5 lines) — explicit per-file entry for data/.mortgage-ops.duckdb.lock under a Plan 09-07 comment header (defensive secondary lockfile name; production data/.lock was already added in Plan 09-02)"
  - "DATA_CONTRACT.md (+29 lines) — Phase 9 Layer Examples section appended after Layer Cross-References; per-artifact layer classification table (10 rows) + critical-rule note + cross-reference to references/data-layer.md"
  - "tests/test_orchestration/test_gitignore_phase09.py (136 lines, 6 tests) — line-presence + behavioral + no-bare-wildcard regression guards"
affects:
  - "10-claude-skill (Phase 10) — references/data-layer.md is the candidate for progressive-disclosure via SKILL.md `references:` frontmatter (decision deferred per D-07-01)"
  - "12-fred-eval (Phase 12) — depends on data/known-loans.yml remaining tracked Reference Layer; the new regression test pins the contract"

# Tech tracking
tech-stack:
  added: []  # No new runtime libraries; documentation + .gitignore + 1 Python regression test
  patterns:
    - "Repo-root references/ directory for skill-style reference docs (joins existing apr-reg-z.md, arm-mechanics.md, refi-npv.md, stress-tests.md, points-breakeven.md)"
    - "Append-only DATA_CONTRACT.md edits — existing 75 lines untouched (D-07-04); Phase 1-8 hook line-number references stay stable"
    - "Explicit per-file .gitignore lines for ephemeral artifacts (NEVER bare data/* wildcards) — D-07-02 enforced by regression test"
    - "Two-mechanism .gitignore regression test: line-presence (catches deletion) + behavioral via git check-ignore (catches over-broad-wildcard semantic regressions)"

key-files:
  created:
    - "references/data-layer.md — 358 lines (Phase 9 onboarding + reference doc)"
    - "tests/test_orchestration/test_gitignore_phase09.py — 136 lines, 6 tests (line-presence + behavioral + no-bare-wildcard guards)"
  modified:
    - ".gitignore — appended 5 lines under a Plan 09-07 comment header (data/.mortgage-ops.duckdb.lock entry; data/.lock was already present from Plan 09-02)"
    - "DATA_CONTRACT.md — appended 29 lines (Phase 9 Layer Examples section after Layer Cross-References); existing 75 lines unchanged"

key-decisions:
  - "D-07-01 LOCKED: references/data-layer.md ships at repo-root references/, NOT under .claude/skills/mortgage-ops/references/ (which does not yet exist) — Phase 10 will decide skill placement"
  - "D-07-02 LOCKED: .gitignore additions are EXPLICIT per-file lines, NOT data/* wildcards — bare data/* would silently un-track data/known-loans.yml (Reference Layer)"
  - "D-07-03 LOCKED: BOTH data/.mortgage-ops.duckdb.lock AND data/.lock entries — production name + defensive catch-all for any future rename"
  - "D-07-04 LOCKED: DATA_CONTRACT.md is APPENDED, not rewritten — preserves Phase 1-8 hook line-number references"
  - "D-07-05 LOCKED: test_gitignore_phase09.py uses BOTH line-presence AND behavioral assertions — line-presence catches deletion; behavioral catches over-broad-wildcard semantic regression"
  - "D-07-06 LOCKED: Plan 09-07 closes ZERO PERS requirements directly (frontmatter requirements: []) — PERS-01..07 closed by Waves 1-6; this plan is documentation + ignore hygiene"
  - "D-07-07 LOCKED: references/ directory at repo root, NOT data/reference/ (which is for regulatory YAMLs)"

patterns-established:
  - "Repo-root references/ doc style — header + framing paragraph + bulleted source artifacts + 5-9 numbered sections + cross-references; matches existing arm-mechanics.md, apr-reg-z.md, refi-npv.md, stress-tests.md, points-breakeven.md"
  - "Two-mechanism .gitignore regression test — line-presence for deletion + behavioral for semantic drift; the load-bearing third test (test_gitignore_no_bare_data_wildcard) is future-proofing against refactors"
  - "Append-only doc-modification discipline for cross-referenced contract docs (DATA_CONTRACT.md, hooks line numbers stay stable)"

requirements-completed: []  # D-07-06: Plan 09-07 is documentation + ignore hygiene; all PERS-01..07 are closed by Waves 1-6

# Metrics
duration: 7min
completed: 2026-05-07
---

# Phase 09 Plan 07: References & Gitignore Summary

**Phase 9 documentation surface complete: references/data-layer.md (358 lines) ships the schema, lockfile, render-determinism, and onboarding contract; DATA_CONTRACT.md gains a Phase 9 Layer Examples section disambiguating Reference (data/known-loans.yml committed) vs Data (data/mortgage-ops.duckdb gitignored); .gitignore gains the defensive lockfile entry; tests/test_orchestration/test_gitignore_phase09.py (6 tests) pins the rule. Pass count 543 -> 549 (+6 net from new regression test); zero regression; Phase 9 ready for /gsd-verify-work.**

## Performance

- **Duration:** ~7 min (start 2026-05-07T17:34:07Z, end 2026-05-07T17:41:13Z; 426s wall-clock; 4 commits)
- **Tasks:** 5 (Task 5 was verification-only — no commit, mirroring Wave 0/1/2/3/4/6 precedent)
- **Files created:** 2 (references/data-layer.md, tests/test_orchestration/test_gitignore_phase09.py)
- **Files modified:** 2 (.gitignore +5 lines, DATA_CONTRACT.md +29 lines)
- **Lines added:** 358 (ref doc) + 136 (test) + 29 (DATA_CONTRACT) + 5 (.gitignore) = 528 lines net

## Documentation Surface

### references/data-layer.md (358 lines, 9 sections)

| # | Section | Plan-mandated? | Content |
|---|---------|---------------|---------|
| 1 | Header + source artifacts list | Yes (mandatory) | Framing paragraph + bullet list of 6 orchestration source files + 4 data artifacts |
| 2 | Schema Overview | **Yes (acceptance gate)** | 7-table table with DECIMAL widths; cites `orchestration/init-db.mjs` DDL_STATEMENTS array |
| 3 | Decimal-String Discipline | Yes | INSERT-as-string + CAST AS VARCHAR + Python re-parse; cites RESEARCH Pitfall 1 + Plan 09-03 D-03-02..03 + regression test |
| 4 | Lockfile Mechanics | **Yes (acceptance gate)** | JSON shape + 4-step acquire + release + 60s threshold + why-not-O_EXCL + 3 regression tests |
| 5 | Render-Markdown Determinism | **Yes (acceptance gate)** | Header + ORDER BY + no NOW() three rules; cites Plan 09-04 D-04-01..04 + 2 regression tests |
| 6 | Reference Layer vs Data Layer | **Yes (acceptance gate)** | 10-row layer table + over-broad-wildcard trap + Plan 09-07 explicit-line solution |
| 7 | Onboarding Walkthrough | **Yes (acceptance gate)** | 8-step bash walkthrough from `uv sync` through rendered markdown |
| 8 | When Things Go Wrong | Yes | 7-row symptom -> cause -> fix table |
| 9 | Cross-References | Yes | Plans, RESEARCH, PATTERNS, DATA_CONTRACT.md, CLAUDE.md, career-ops precedent |
| 10 | Future Work | Yes | Phase 10 progressive disclosure decision, v2 lockfile hardening, v2 Python read access, doc freshness check |

All 5 plan-mandated section headers (Schema Overview, Lockfile Mechanics, Render-Markdown Determinism, Onboarding Walkthrough, Reference Layer vs Data Layer) match the literal `^## ` regex used by the plan's verify-block.

**Length note:** the doc is 358 lines vs the plan's 150-250 target. The over-shoot is intentional — the 7-row When Things Go Wrong table, the 8-step Onboarding Walkthrough, and the 10-row layer-disambiguation table are all called for in the action's content templates and would not compress without losing concrete examples (which is the point of an onboarding doc). Concise without being terse.

### .gitignore additions

Pre-Plan-09-07 state already had (from Plan 09-02):

```
data/*.duckdb                    # covers data/mortgage-ops.duckdb
data/mortgage-ops.duckdb-wal     # sidecar
data/mortgage-ops.duckdb-shm     # sidecar
reports/*                        # generated reports
!reports/.gitkeep                # seam preserved
data/.lock                       # production lockfile (Plan 09-02)
data/loans.md                    # generated view (Plan 09-02)
data/scenarios.md                # generated view (Plan 09-02)
node_modules/                    # Node deps (Plan 09-02)
package-lock.json.bak            # ephemeral backup (Plan 09-02)
```

Plan 09-07 ADDS only the defensive lockfile entry under a new comment header:

```
# Phase 9 (Plan 09-07): DuckDB writer lockfile defensive name (RESEARCH Pitfall 5)
# Production lockfile is the short name above; this entry catches any future
# rename to the longer per-DB convention without breaking Reference Layer commits.
data/.mortgage-ops.duckdb.lock
```

`data/.lock` was NOT re-added (would be a duplicate of the Plan 09-02 entry) — the regression test grep `"data/.lock" in content` matches the existing line.

**Behavioral verification post-edit (`git check-ignore`):**

| Path | Expected exit | Actual exit | Layer |
|------|---------------|-------------|-------|
| `data/mortgage-ops.duckdb` | 0 (ignored) | 0 ✓ | Data |
| `data/.mortgage-ops.duckdb.lock` | 0 (ignored) | 0 ✓ | Data (ephemeral) |
| `data/.lock` | 0 (ignored) | 0 ✓ | Data (ephemeral) |
| `data/known-loans.yml` | 1 (NOT ignored) | 1 ✓ | Reference (committed) |
| `reports/.gitkeep` | 1 (NOT ignored) | 1 ✓ | seam |
| `reports/sample-report.md` | 0 (ignored) | 0 ✓ | Data |

### DATA_CONTRACT.md additions

29 lines appended after the existing "Layer Cross-References" section (line 71). The new section is "## Phase 9 Layer Examples" (line 77) and contains:

- **10-row layer-classification table** covering data/known-loans.yml + DuckDB file + 2 sidecars + lockfile + 2 markdown views + 3 orchestration scripts
- **Critical rule callout** about the over-broad data/* wildcard trap and the explicit-per-file solution
- **Cross-reference** to references/data-layer.md as the schema/lockfile/render onboarding doc

Existing 75 lines (User Layer table line 14-23, System Layer line 27-43, Data Layer line 46-54, Reference Layer line 56-69, Layer Cross-References line 71-75) unchanged per D-07-04. Phase 1-8 hooks (e.g., scripts/hooks/block-user-layer.py) that cross-reference DATA_CONTRACT.md by section keep working.

### tests/test_orchestration/test_gitignore_phase09.py (6 tests)

| Test | Mechanism | Catches |
|------|-----------|---------|
| `test_gitignore_phase09_entries_present` | Line-presence | Accidental deletion of Phase 9 lockfile entries |
| `test_gitignore_known_loans_NOT_ignored` | Behavioral | Reference Layer catalog accidentally un-tracked |
| `test_gitignore_duckdb_file_IS_ignored` | Behavioral | Phase 1 `data/*.duckdb` rule accidentally removed |
| `test_gitignore_lockfile_IS_ignored` | Behavioral | Plan 09-07 lockfile entry missing |
| `test_gitignore_reports_seam_preserved` | Behavioral | Phase 1 `!reports/.gitkeep` whitelist or `reports/*` rule removed |
| `test_gitignore_no_bare_data_wildcard` | Line-pattern | **LOAD-BEARING** future-proofing — catches `data/*` refactors that would silently un-track the catalog |

Module-level `REQUIRED_GITIGNORE_LINES: tuple[str, ...]` typed for mypy --strict; `_git_check_ignore(path) -> int` helper with `subprocess.run(check=False, ...)` so the helper returns the raw exit code (0=ignored, 1=NOT ignored). All 6 tests pass in 0.07s.

## Test Counts

- **Pre-Wave-7 baseline (Plan 09-06 final):** 543 passed + 4 skipped + 1 xfailed
- **Post-Wave-7 (Plan 09-07 final):** **549 passed + 4 skipped + 1 xfailed** (+6 net passes; 0 xfail delta; zero regression)
- **Plan target:** Wave 6 baseline (543) + 6 new gitignore tests = 549. **HIT EXACTLY**.

The 1 remaining xfail is the inherited Phase 5 ARM oracle deferral (`test_oracle_cross_validation_5_1`); it has nothing to do with Phase 9 and remains queued for Phase 8+ post-human-capture.

## Wave-Flip Status (Cumulative — Final)

| Stub | File | Final Status |
|------|------|--------------|
| `test_init_db_idempotent` | test_db_lifecycle.py | PASSED (Wave 2) |
| `test_insert_loan_round_trip` | test_db_lifecycle.py | PASSED (Wave 3) |
| `test_insert_scenario_round_trip` | test_db_lifecycle.py | PASSED (Wave 3) |
| `test_insert_report_round_trip` | test_db_lifecycle.py | PASSED (Wave 3) |
| `test_decimal_string_round_trip_preserves_cents` | test_db_lifecycle.py | PASSED (Wave 3) |
| `test_render_markdown_byte_identical` | test_render_markdown.py | PASSED (Wave 4) |
| `test_known_loans_catalog_complete` | test_known_loans_smoke.py | PASSED (Wave 5) |
| `test_concurrent_writes_serialize` | test_db_lifecycle.py | PASSED (Wave 6) |
| `test_stale_lockfile_reclaimed_after_60s` | test_lockfile.py | PASSED (Wave 6) |

All 9 Wave 0 xfail stubs flipped. Phase 9 has zero remaining xfails.

## Phase 9 Closure Report

| Requirement | Closed by | Pinned by |
|-------------|-----------|-----------|
| **PERS-01** (DB schema bootstrap; 6 tables + DECIMAL widths) | Wave 2 (Plan 09-02 init-db.mjs) | Wave 6 `test_init_db_creates_all_expected_tables` + schema fingerprint via SHA256 of pragma_table_info |
| **PERS-02** (init-db idempotency) | Wave 2 (Plan 09-02 IF NOT EXISTS DDL) | Wave 6 `test_init_db_idempotent_across_runs` (schema-fingerprint hash equality across two runs) |
| **PERS-03** (insert subcommands: loan/scenario/report + render) | Wave 3 (Plan 09-03 db-write.mjs) + Wave 4 (Plan 09-04 cmdRenderMarkdown) | Wave 3 round-trip tests + Wave 4 byte-equality test |
| **PERS-04** (lockfile + 60s stale recovery) | Wave 1 (Plan 09-01 lockfile.mjs) | Wave 6 `test_stale_lockfile_reclaimed_after_60s_threshold` (positive 65s aging) + `test_fresh_lockfile_under_60s_blocks_or_waits` (negative 5s aging) |
| **PERS-05** (parallel writers serialize via lockfile) | Wave 1 lockfile + Wave 3 WRITE_COMMANDS gate | Wave 6 `test_parallel_inserts_serialize_via_lockfile` (concurrent Popen-based insert-loan with race-window-tolerant assertions) |
| **PERS-06** (byte-identical render-markdown) | Wave 4 (Plan 09-04 cmdRenderMarkdown) | Wave 4 `test_render_markdown_byte_identical` (unit) + Wave 6 `test_render_markdown_byte_identical_end_to_end` (full pipeline SHA256) |
| **PERS-07** (data/known-loans.yml ≥ 7 entries) | Wave 5 (Plan 09-05 known-loans.yml) | Wave 5 `test_known_loans_catalog_complete` (REQUIRED_IDS subset + 9-key schema + decimal-string discipline) |

| Success Criterion | Pinned by |
|-------------------|-----------|
| **SC-1** (idempotent init) | Wave 6 `test_init_db_idempotent_across_runs` + `test_init_db_creates_all_expected_tables` |
| **SC-2** (parallel writes serialize) | Wave 6 `test_parallel_inserts_serialize_via_lockfile` |
| **SC-3** (60s stale recovery) | Wave 6 `test_stale_lockfile_reclaimed_after_60s_threshold` + `test_fresh_lockfile_under_60s_blocks_or_waits` |
| **SC-4** (byte-identical render) | Wave 4 unit + Wave 6 end-to-end (D-06-08 dual coverage) |
| **SC-5** (catalog completeness) | Wave 5 `test_known_loans_catalog_complete` |

All 7 PERS + all 5 SC pinned. Documentation surface complete (this wave). **Phase 9 ready for /gsd-verify-work followed by Phase 10.**

## Task Commits

Each task was committed atomically (no Co-Authored-By or AI attribution per global Git Attribution rule):

1. **Task 1: docs(09-07) add references/data-layer.md Phase 9 onboarding doc** — `93510b8`
2. **Task 2: chore(09-07) gitignore data/.mortgage-ops.duckdb.lock defensive name** — `feec3be`
3. **Task 3: docs(09-07) add Phase 9 Layer Examples section to DATA_CONTRACT.md** — `6fa549d`
4. **Task 4: test(09-07) add Phase 9 .gitignore regression test (6 tests)** — `a8559a1`
5. **Task 5: Final verification (suite green, docs shipped, contract updated)** — verification-only, no commit (Wave 0/1/2/3/4/6 precedent)

## Decisions Made

All seven decisions are LOCKED at the plan level (D-07-01..D-07-07) — the executor honored them verbatim. No new plan-level decisions emerged during execution.

- **D-07-01 LOCKED — references/data-layer.md at repo-root references/, NOT under .claude/skills/:** Phase 10 has not yet shipped the skill bundle; doc is reachable today by humans + Claude sessions reading the repo. Phase 10 will decide skill placement (move/symlink/progressive-disclose).
- **D-07-02 LOCKED — Explicit per-file .gitignore lines, NOT data/* wildcards:** bare `data/*` would silently un-track data/known-loans.yml (Reference Layer per D-05-01); explicit per-file pattern preserved + pinned by `test_gitignore_no_bare_data_wildcard`.
- **D-07-03 LOCKED — Both data/.mortgage-ops.duckdb.lock AND data/.lock entries:** production name (data/.lock from Plan 09-02) + defensive catch-all for future renames (data/.mortgage-ops.duckdb.lock added here).
- **D-07-04 LOCKED — DATA_CONTRACT.md APPENDED, not rewritten:** existing 75 lines untouched; Phase 1-8 hooks that cross-reference DATA_CONTRACT.md by section keep working.
- **D-07-05 LOCKED — Test uses BOTH line-presence AND behavioral assertions:** line-presence catches deletion; behavioral catches over-broad-wildcard semantic regression. Six tests cover both surfaces.
- **D-07-06 LOCKED — Plan 09-07 closes ZERO PERS requirements directly:** PERS-01..07 are closed by Waves 1-6; this plan is documentation + ignore hygiene only. Frontmatter `requirements: []` is intentional.
- **D-07-07 LOCKED — references/ at repo root, NOT data/reference/:** namespace separation between skill markdown reference docs (references/) and regulatory data YAMLs (data/reference/).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] references/data-layer.md initial section headers used numbered prefixes**
- **Found during:** Task 1 acceptance-criteria verification
- **Issue:** Initially wrote sections as `## 1. Schema Overview`, `## 3. Lockfile Mechanics`, etc., for readability. The plan's verify-block uses literal regex `^## (Schema Overview|Lockfile Mechanics|Render-Markdown Determinism|Onboarding Walkthrough|Reference Layer vs Data Layer)` which does NOT match numbered headers; my initial verify ran 0 hits against this regex.
- **Fix:** Removed numeric prefix from all 9 `## ` headers (Schema Overview, Decimal-String Discipline, Lockfile Mechanics, Render-Markdown Determinism, Reference Layer vs Data Layer, Onboarding Walkthrough, When Things Go Wrong, Cross-References, Future Work) so the literal plan grep matches each mandatory header. Section ORDERING is unchanged; the doc remains 9 `## ` sections (matches plan's "10 mandatory sections" intent — the header / framing block is unnumbered prose, not a `##` section, which the plan acceptance-counts treat the same way).
- **Files modified:** references/data-layer.md (9 single-line edits to strip numeric prefix)
- **Verification:** `grep -cE '^## (Schema Overview|Lockfile Mechanics|Render-Markdown Determinism|Onboarding Walkthrough|Reference Layer vs Data Layer)' references/data-layer.md` returns 5; each individual header grep returns 1; `grep -cE '^## '` returns 9.
- **Plan acknowledgement:** Plan deviation_rules Rule-5 says "the section headers + ordering are pinned" — matched verbatim after the fix; numbering was a non-mandated authorial choice.
- **Committed in:** `93510b8` (Task 1 commit, applied before commit during acceptance verification)

**2. [Rule 3 - Documentation hygiene] data/.lock was already present in .gitignore from Plan 09-02**
- **Found during:** Task 2 pre-edit `grep -nE 'duckdb|\.lock|reports' .gitignore`
- **Issue:** The plan's prescribed Task 2 action specifies appending BOTH `data/.mortgage-ops.duckdb.lock` AND `data/.lock`, but inspection of .gitignore showed `data/.lock` was already added by Plan 09-02 at line 40 under a Phase 9 comment header. Re-adding it would create a duplicate entry.
- **Fix:** Appended ONLY `data/.mortgage-ops.duckdb.lock` (the missing entry) under a new Plan 09-07 comment header. The plan's `grep -c "data/.lock" .gitignore` acceptance criterion (returns 1) is satisfied by the existing Plan 09-02 line; the `grep -c "data/.mortgage-ops.duckdb.lock"` (returns 1) is satisfied by the new line.
- **Files modified:** .gitignore (5 new lines: comment header + entry; instead of plan's prescribed 3 lines for both entries)
- **Verification:** Both grep counts return 1; `git check-ignore data/.lock` exits 0; `git check-ignore data/.mortgage-ops.duckdb.lock` exits 0; `git check-ignore data/known-loans.yml` exits 1.
- **Plan acknowledgement:** This is Wave 0 SUMMARY's "STATE.md flagged blocker about .gitignore additions duplicated across 09-02 + 09-07" — the duplication has been resolved here by adding only the truly-new entry. The plan's intent (both entries present) is satisfied.
- **Committed in:** `feec3be`

### Documented Plan-Acceptance-Drift (no functional impact)

**3. [Rule 6 - Length target] references/data-layer.md is 358 lines vs plan's 150-250 target**
- **Found during:** Task 1 final verify
- **Issue:** Plan target length is 150-250 lines (concise but complete); shipped doc is 358 lines.
- **Resolution:** The over-shoot is a content-density choice driven by the action's explicit content templates: 10-row layer table (Section 5), 8-step bash walkthrough (Section 6), 7-row symptom-cause-fix table (Section 7), and 4-bullet Future Work (Section 9) are all called for in the action and cannot compress without losing concrete examples (which is the point of an onboarding doc). Concise without being terse. Plan acceptance criterion `wc -l references/data-layer.md reports at least 100 lines (target 150-250)` is satisfied at the floor (≥100); the upper bound is not in the acceptance criteria.
- **Files modified:** None.
- **Plan acknowledgement:** Rule-5 of plan deviation_rules: "the section headers + ordering are pinned. The executor MAY adjust contents to match shipped-code reality." Length adjustment to match shipped reality is explicitly allowed.

---

**Total deviations:** 3 (2 Rule-3 auto-fixes + 1 Rule-6 documented length drift; all hygiene-only).
**Impact on plan:** Zero functional change. The 5 plan-mandated section headers are present verbatim; the .gitignore behavioral contract is satisfied (verified via 6 representative `git check-ignore` paths); DATA_CONTRACT.md is appended without touching existing content; the regression test passes with 6 tests covering both line-presence and behavioral assertions. No Rule-1 (bug), Rule-2 (missing critical functionality), Rule-4 (architectural), or Rule-7 (Node code touched) deviations occurred.

## Issues Encountered

None — execution was clean. The two Rule-3 deviations were minor authorial-choice adjustments to align with the plan's literal acceptance regex (numbered headers) and to avoid duplicating the Plan 09-02 `data/.lock` entry. The Rule-6 length deviation is content-density driven and within the plan's explicit "adjust contents to match shipped-code reality" allowance.

## Lint + Type Hygiene Status

| Check | Result |
|-------|--------|
| `uv run pytest -q` | **549 passed + 4 skipped + 1 xfailed** (was 543+4+1; +6 net passes; zero regression) |
| `uv run pytest tests/test_orchestration/test_gitignore_phase09.py -v` | **6 passed in 0.07s** |
| `uv run mypy --strict tests/test_orchestration/` | Success: no issues found in 11 source files |
| `uv run ruff check tests/test_orchestration/` | All checks passed! |
| `uv run ruff format --check tests/test_orchestration/` | 11 files already formatted |
| `git check-ignore data/known-loans.yml` (must NOT be ignored) | exit 1 ✓ |
| `git check-ignore data/mortgage-ops.duckdb` (must be ignored) | exit 0 ✓ |
| `git check-ignore data/.mortgage-ops.duckdb.lock` (must be ignored) | exit 0 ✓ |
| `git check-ignore reports/.gitkeep` (must NOT be ignored) | exit 1 ✓ |
| `git check-ignore reports/foo.md` (must be ignored) | exit 0 ✓ |
| `git ls-files data/known-loans.yml` (must list it) | `data/known-loans.yml` ✓ |
| `test ! -f data/loans.md` | exit 0 ✓ |
| `test ! -f data/scenarios.md` | exit 0 ✓ |
| `test ! -f data/.mortgage-ops.duckdb.lock` | exit 0 ✓ |
| `test ! -f data/.lock` | exit 0 ✓ |

Pre-commit hooks (ruff legacy alias, ruff format, mypy, check-yaml, block-user-layer) ran on all 4 task commits and passed.

## User Setup Required

None — Plan 09-07 ships documentation + .gitignore + 1 Python regression test. No environment variables, dashboard configuration, credential setup, or schema migrations needed. No production code (lib/, orchestration/) touched.

## Threat Model Coverage

The plan's threat_model section enumerates 6 STRIDE threats (T-09-34..T-09-39). Implementation status:

| Threat ID | Mitigation Implemented | Verified By |
|-----------|------------------------|-------------|
| T-09-34 (Tampering: future refactor adds bare data/* wildcard) | `test_gitignore_no_bare_data_wildcard` reads .gitignore line-by-line and raises if any line equals exactly `data/*` | Test passes; refactor that adds `data/*` will fail CI before merge |
| T-09-35 (Information Disclosure: lockfile JSON content leaks PID + writer reason into git history) | `data/.mortgage-ops.duckdb.lock` + `data/.lock` both gitignored; Plan 09-02 already covered .lock; Plan 09-07 adds the defensive long-form name | `git check-ignore` exit 0 for both lockfile names; `test_gitignore_lockfile_IS_ignored` pins the rule |
| T-09-36 (Repudiation: Reference Layer catalog accidentally untracked) | `test_gitignore_known_loans_NOT_ignored` asserts `git check-ignore data/known-loans.yml` exits 1 (NOT ignored); `test_gitignore_no_bare_data_wildcard` adds the load-bearing future-proofing guard | Both tests pass; explicit per-file lines in .gitignore (D-07-02) avoid the trap |
| T-09-37 (Tampering: DATA_CONTRACT.md rewrite drops a User Layer enumeration) | D-07-04 mandates append-only; existing 75 lines untouched; only 29 lines appended after line 75 | Verified: existing User Layer table at line 14-23 unchanged; Reference Layer table at line 56-69 unchanged; new section at line 77 |
| T-09-38 (Denial of Service: stale lockfile committed to git) | Lockfile gitignored; even if force-committed, Plan 09-01 stale-recovery reclaims at 60s — recovery time bounded | Threat-mitigated; documented in references/data-layer.md "When Things Go Wrong" row 4 |
| T-09-39 (Repudiation: references/data-layer.md goes stale as orchestration evolves) | accept disposition per plan; doc is supplementary to PLAN.md + RESEARCH.md (authoritative); cross-references in §"Cross-References" point readers back to canonical sources | Documented as v1 risk acceptance; "Future Work" §10 lists a possible CI freshness check as future work |

All 6 threats covered. T-09-39 is `accept` disposition (per plan threat register), so the mitigation is cross-reference back to canonical sources, not technical enforcement.

## Self-Check: PASSED

Verified at SUMMARY-write time:

**Files exist:**
- `references/data-layer.md` exists at 358 lines (`wc -l` confirmed)
- `tests/test_orchestration/test_gitignore_phase09.py` exists at 136 lines
- `.gitignore` modified (5 new lines under Plan 09-07 comment header)
- `DATA_CONTRACT.md` modified at 104 lines (was 75; +29 lines for Phase 9 Layer Examples section)

**Commits exist:**
- `93510b8` (Task 1: docs(09-07) references/data-layer.md) — found via `git log --oneline | grep 93510b8`
- `feec3be` (Task 2: chore(09-07) .gitignore lockfile entry) — found via `git log --oneline | grep feec3be`
- `6fa549d` (Task 3: docs(09-07) DATA_CONTRACT.md Phase 9 section) — found via `git log --oneline | grep 6fa549d`
- `a8559a1` (Task 4: test(09-07) regression test) — found via `git log --oneline | grep a8559a1`

**Doc structure (references/data-layer.md):**
- All 5 plan-mandated `## ` headers present (verified via individual greps)
- 9 total `## ` sections (header content + 9 numbered sections per plan's 10-mandatory-section intent — section 1 is the unnumbered prose framing block per existing references/ doc convention)
- ≥3 RESEARCH cross-references (actual: 7); ≥3 known-loans.yml mentions (actual: 6); ≥1 60s mention (actual: 4); ≥1 ORDER BY id ASC mention (actual: 2); ≥1 CAST AS VARCHAR mention (actual: 5)

**Gitignore behavior:**
- 6 representative `git check-ignore` paths verified (3 ignored: duckdb + 2 lockfiles + reports/foo.md; 2 NOT ignored: known-loans.yml + reports/.gitkeep) — all match expected layer rules

**DATA_CONTRACT.md additions:**
- "## Phase 9 Layer Examples" appears at line 77 (AFTER "## Layer Cross-References" at line 71) — append-only discipline preserved
- 1 occurrence of "Phase 9 Layer Examples"; 3 of "data/known-loans.yml" (≥2); 1 of "references/data-layer.md" (≥1); 7 of "Reference Layer" (≥4)

**Tests:**
- All 6 gitignore regression tests pass — `pytest tests/test_orchestration/test_gitignore_phase09.py -v` reports 6 passed in 0.07s
- Full pytest suite: 549 passed + 4 skipped + 1 xfailed (verified)
- mypy --strict + ruff check + ruff format --check all clean across 11 test_orchestration files

**No leaked artifacts:**
- data/loans.md absent ✓
- data/scenarios.md absent ✓
- data/.mortgage-ops.duckdb.lock absent ✓
- data/.lock absent ✓

**No production code touched:**
- `git diff 8c0b80a..HEAD --name-only` shows only `references/data-layer.md`, `.gitignore`, `DATA_CONTRACT.md`, `tests/test_orchestration/test_gitignore_phase09.py` — no `lib/`, no `orchestration/`, no production-code modifications

## Next Phase Readiness

**Phase 9 fully closed: ready for /gsd-verify-work.**

- All 7 PERS requirements (PERS-01..07) closed by Waves 1-6; pinned by passing tests at Wave 6 + Wave 7 documentation surface complete.
- All 5 ROADMAP SC- success criteria pinned by passing tests.
- Phase 9 xfail count = 0 (1 inherited Phase 5 ARM oracle xfail remains, deferred to Phase 8+ post-human-capture).
- Documentation surface complete: references/data-layer.md (Phase 9 onboarding) + DATA_CONTRACT.md (Phase 9 Layer Examples) + .gitignore (lockfile defensive name) + regression test (rule pinning).
- No leaked artifacts; lint clean; no production code modified in this wave.

**Phase 10 (Claude Skill Frontend) unblocked.** Phase 10 will decide whether to:
- Move references/data-layer.md under .claude/skills/mortgage-ops/references/
- Symlink it from the skill bundle to the repo-root location
- Progressive-disclose it via SKILL.md `references:` frontmatter

D-07-01 deliberately deferred this decision to Phase 10. The doc is reachable TODAY by humans + Claude sessions reading the repo at the repo-root references/ path.

**Phase 12 (FRED-eval) unblocked at the catalog layer.** The regression test pins data/known-loans.yml as Reference Layer (committed); any future refactor that breaks this contract will fail CI before downstream phases ingest the catalog.

**Cross-phase contract for Phase 10:**
- `data/known-loans.yml` will remain tracked (Reference Layer); skill routing can read it via Python yaml.safe_load OR Node js-yaml interchangeably (both verified parser-portable in Plan 09-05).
- `orchestration/db-write.mjs` is the canonical writer; skill ingestion paths should call it (not bypass the lockfile/transaction discipline by writing to DuckDB directly).
- `data/loans.md` + `data/scenarios.md` are byte-identical regenerable views; skill rendering MAY display them but MUST NOT hand-edit them (header comment is the user-facing signal; .gitignore prevents accidental commit).

---
*Phase: 09-duckdb-orchestration*
*Plan: 07 (Wave 7 — references doc + gitignore hygiene)*
*Completed: 2026-05-07*
