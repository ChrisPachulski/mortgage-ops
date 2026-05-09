---
phase: 10
review_round: 2
reviewers: [codex]
reviewed_at: 2026-05-09T22:56:12Z
plans_reviewed:
  - 10-00-test-infrastructure-PLAN.md
  - 10-01-scripts-relocation-PLAN.md
  - 10-02-skill-md-scaffold-PLAN.md
  - 10-03-modes-PLAN.md
  - 10-04-references-PLAN.md
  - 10-05-ci-tests-PLAN.md
  - 10-06-integration-smoke-PLAN.md
prior_round:
  reviewed_at: 2026-05-09T05:23:46Z
  outcome: 8 HIGH / 6 MEDIUM / 2 LOW concerns; resolved via revision pass 1 (commit 4a416c9)
skipped_reviewers:
  - claude (running inside Claude Code; skipped for independence)
  - ollama (only nomic-embed-text installed — embedding model, not chat)
  - gemini, opencode, qwen, cursor, coderabbit, lm_studio, llama_cpp (not installed)
---

# Cross-AI Plan Review — Phase 10 (Round 2)

> Single-reviewer review (codex). Treat findings as one strong opinion, not a multi-model consensus.
> Prior round's concerns largely resolved; this round surfaces NEW issues found by reading live
> repository code (orchestration/db-write.mjs, scripts/hooks/block-user-layer.py, lib/rules/).

## Codex Review

## Summary

The revisions address several prior review themes at the planning-summary level, especially seven-script relocation, four-key `_profile.example.md`, subagent forward links, and byte-equal reference copies. However, there are still execution blockers in the task bodies. The largest gaps are SKLL-13 being planned against a `db-write.mjs` interface/schema that does not exist, repeated incorrect `skill_root` parent traversal in tests, and hook/profile parsing tests that will not behave as described.

## Strengths

- The seven-script relocation is now explicit and matches the actual repo: all seven root scripts currently exist.
- The reference-stub issue is mostly corrected: `refi-npv.md` and `apr-reg-z.md` are now planned as byte-equal full-content copies.
- The revised plans explicitly include D-PROF-01, D-SUBA-FW-01, D-SUBA-FW-02, and D-NUM-01..06 surfaces.
- Wave 0 now accounts for ruff F401 hygiene and includes SKLL-13 xfail stubs.
- Stress mode now includes the required `if it exists` seam for `.claude/agents/stress-test-agent.md`.

## Concerns

- [HIGH] [10-01-scripts-relocation-PLAN.md Task 6](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-01-scripts-relocation-PLAN.md:576), [10-05](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-05-ci-tests-PLAN.md:351), and [10-06](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-06-integration-smoke-PLAN.md:294) compute `repo_root` incorrectly as `skill_root.parent.parent.parent.parent`. For `.claude/skills/mortgage-ops`, repo root is three parents up, not four. Several tests will inspect `/Users/.../Documents/scripts` instead of the repo.

- [HIGH] SKLL-13 is still incompatible with shipped Phase 9 code. [10-03 Task 1](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-03-modes-PLAN.md:233) and [10-06 Task 1](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-06-integration-smoke-PLAN.md:356) use `--query` and `--insert-report --json`, but actual `db-write.mjs` supports `query --sql` and `insert-report --scenario-id --file` ([db-write.mjs](/Users/cujo253/Documents/mortgage-ops/orchestration/db-write.mjs:299)). The reports table also has no `filename` column and `scenario_id` is `NOT NULL`.

- [HIGH] The `_profile.md` hook tests will not work. [10-03 Task 3](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-03-modes-PLAN.md:454) and [10-05 Task 4](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-05-ci-tests-PLAN.md:687) run `block-user-layer.py` with no filename args, but the actual hook checks `argv[1:]`, not `git diff --cached` ([block-user-layer.py](/Users/cujo253/Documents/mortgage-ops/scripts/hooks/block-user-layer.py:49)). It will exit 0.

- [HIGH] `_profile.example.md` is internally inconsistent with profile loading. [10-03 Task 1](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-03-modes-PLAN.md:198) says `_shared.md` parses `_profile.md` as YAML, but [Task 2](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-03-modes-PLAN.md:340) creates a Markdown file with a fenced YAML block. If the user copies it as instructed, direct YAML parsing will fail.

- [HIGH] Wave 5 uses imports that Wave 0 deliberately omits, but never adds them back. `count_tokens`, `yaml`, `subprocess`, and `sys` are used in [10-05 Task 1/3/4](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-05-ci-tests-PLAN.md:205), but the plan has no import-edit step after Wave 0’s F401 deferral.

- [MEDIUM] SKLL-12 is claimed as all seven scripts, but the actual Wave 5 test only checks three scripts: [10-05 Task 3](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-05-ci-tests-PLAN.md:439). Wave 6 later checks seven `--help` calls, but Wave 5’s claimed closure and commit message are overstated.

- [MEDIUM] `_shared.md` CI coverage is weaker than the revised requirements. The must-have says 12 sections including `Profile Loading`, `Output Formatting`, and `Save Report` ([10-05](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-05-ci-tests-PLAN.md:54)), but the test constant only lists the original 9 sections ([10-05 Task 2](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-05-ci-tests-PLAN.md:313)). D-NUM formatting can drift without CI failing.

- [MEDIUM] SKILL.md subagent wording is conflicting. [10-02 Task 2](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-02-skill-md-scaffold-PLAN.md:291) says stress “dispatches to subagent if N>5,” while the same plan later says Phase 10 must not include runtime subagent dispatch ([10-02](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-02-skill-md-scaffold-PLAN.md:514)). The existence check belongs in `modes/stress.md`, not unconditional SKILL.md routing copy.

- [MEDIUM] The portability smoke is not actually proving standalone portability. [10-06](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-06-integration-smoke-PLAN.md:94) correctly notes full runs fail without `lib/`, then [Task 1](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-06-integration-smoke-PLAN.md:229) injects the original repo root via `PYTHONPATH`. That is useful, but it should not be described as self-contained skill-folder execution.

- [MEDIUM] [10-00 Task 1](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-00-test-infrastructure-PLAN.md:130) rewrites the dev dependency list from an outdated snapshot and drops existing `pytest-timeout>=2.3`. It also runs `uv sync` but the plan frontmatter omits `uv.lock`.

- [LOW] Existing hook tests are not updated for the new `_profile.md` path. Current tests still expect `modes/_profile.md` to be blocked ([tests/test_block_user_layer.py](/Users/cujo253/Documents/mortgage-ops/tests/test_block_user_layer.py:36)), while [10-03 Task 3](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-03-modes-PLAN.md:435) changes the canonical path.

- [LOW] [10-04 Task 4](/Users/cujo253/Documents/mortgage-ops/.planning/phases/10-claude-skill/10-04-references-PLAN.md:395) documents `qualified_loan_limit_worksheet(...)`, but the actual function is `qualified_loan_limit` ([irs_pub936.py](/Users/cujo253/Documents/mortgage-ops/lib/rules/irs_pub936.py:60)). The same task hardcodes `Last reviewed: 2026-05-02`, now stale relative to the current phase date.

## Suggestions

- Add a `repo_root` fixture in `tests/conftest.py` and replace every `skill_root.parent.parent.parent.parent` with that fixture or `skill_root.parents[2]`.
- Rework SKLL-13 against the shipped Phase 9 API, or explicitly add a Phase 10 schema/CLI migration. Current code wants: create temp DB, run `init-db`, insert loan, insert scenario, write report file, run `insert-report --scenario-id <id> --file <path>`, then query `reports.markdown_blob`.
- Either make `_profile.example.md` pure YAML with comments, or change `_shared.md` to extract a fenced YAML block before parsing. Do not mix the two.
- Fix hook tests by passing the staged path as an argument, or change the hook implementation to inspect `git diff --cached --name-only`. Also update `tests/test_block_user_layer.py`.
- In 10-05, add explicit import edits for `yaml`, `subprocess`, `sys`, and `count_tokens`.
- Expand SKLL-12 to check all seven scripts in Wave 5, not only Wave 6.
- Add CI assertions for `Profile Loading`, `Output Formatting`, `Save Report`, and D-NUM examples in `_shared.md`.
- Remove stale Phase 7 “until then” copy and make SKILL.md subagent text forward-link only.

## Risk Assessment

**HIGH**: the high-level revisions are directionally better, but multiple task bodies still fail against the actual repository interfaces, especially SKLL-13 persistence, path derivation, and User Layer hook validation.

---

## Consensus Summary

Single-reviewer review. Synthesis of codex's findings:

### Net change from Round 1

**Resolved (Round 1 → Round 2):**
- ✓ Seven-script relocation now matches actual repo (all 7 root scripts exist)
- ✓ `refi-npv.md` and `apr-reg-z.md` byte-equal lifts (no longer marker stubs)
- ✓ `_profile.example.md` four-key surface
- ✓ Subagent forward-links present in SKILL.md
- ✓ Stress mode `if it exists` seam
- ✓ Wave 0 ruff F401 hygiene
- ✓ D-NUM-01..06 referenced

**New HIGH concerns (Round 2 found by reading live code):**

1. **Path arithmetic off-by-one** — `skill_root.parent.parent.parent.parent` is one level too deep across 10-01 Task 6, 10-05, 10-06. Should be `skill_root.parents[2]` (or 3 `.parent` calls). Tests will inspect `/Users/.../Documents/scripts` instead of repo root.

2. **SKLL-13 incompatible with shipped `db-write.mjs` CLI** — Plans invoke `db-write.mjs --query` and `--insert-report --json`, but the actual Phase 9 CLI uses `query --sql` and `insert-report --scenario-id <id> --file <path>`. The `reports` table also has no `filename` column and `scenario_id` is `NOT NULL`. The SKLL-13 closure path needs to be reworked against the real Phase 9 API: create temp DB → init-db → insert loan → insert scenario → write report file → `insert-report --scenario-id <id> --file <path>` → query `reports.markdown_blob`.

3. **User Layer hook test design is broken** — `block-user-layer.py` checks `argv[1:]`, not `git diff --cached`. The Wave 5 test runs the hook with no args, so it always exits 0 — the test passes for the wrong reason. Either pass the staged path as an argument, or change the hook to inspect `git diff --cached --name-only`. Existing `tests/test_block_user_layer.py` also still references the old `modes/_profile.md` path.

4. **`_profile.example.md` format vs parser mismatch** — `_shared.md` parses `_profile.md` as YAML, but `_profile.example.md` is a Markdown file with a fenced YAML block. If a user `cp`s the example as instructed, YAML parsing of the result fails. Either make the example pure YAML with `#` comments, OR teach `_shared.md` to extract a fenced YAML block.

5. **Wave 5 import gap** — Wave 0 deliberately defers `yaml`, `subprocess`, `sys`, `count_tokens` to satisfy ruff F401. Wave 5 uses all of them in tests but the plan has no import-edit step. Tests will fail with `NameError`.

### MEDIUM concerns (Round 2)

- **SKLL-12 closure overstated in Wave 5** — Wave 5 test only checks 3 scripts; Wave 6 checks 7. Plan claims SKLL-12 closure in Wave 5 commit message — overstated.
- **`_shared.md` section CI weaker than must-have** — Must-have lists 12 sections including Profile Loading / Output Formatting / Save Report. Test constant only lists the original 9. D-NUM formatting can drift without CI failing.
- **SKILL.md subagent wording self-contradicts** — 10-02 Task 2 says stress "dispatches to subagent if N>5"; same plan later says Phase 10 must not include runtime subagent dispatch. Existence check belongs in `modes/stress.md` only.
- **Portability smoke uses repo PYTHONPATH** — 10-06 Task 1 injects original repo root via `PYTHONPATH` to make tests pass; that's pragmatic but should not be described as self-contained skill-folder execution.
- **10-00 Task 1 dependency rewrite drops `pytest-timeout`** — Plan rewrites dev deps from outdated snapshot and drops `pytest-timeout>=2.3`. Frontmatter omits `uv.lock` despite running `uv sync`.

### LOW concerns (Round 2)

- **`tests/test_block_user_layer.py` not updated for new `_profile.md` path** — Plan changes canonical path; existing tests still expect `modes/_profile.md`.
- **10-04 Task 4 references nonexistent function name** — Plan documents `qualified_loan_limit_worksheet(...)`; actual function is `qualified_loan_limit`. Also hardcodes `Last reviewed: 2026-05-02` (now stale).

### Suggested fixes (verbatim from codex)

- Add a `repo_root` fixture in `tests/conftest.py` and replace every `skill_root.parent.parent.parent.parent` with that fixture or `skill_root.parents[2]`.
- Rework SKLL-13 against the shipped Phase 9 API: create temp DB, run `init-db`, insert loan, insert scenario, write report file, run `insert-report --scenario-id <id> --file <path>`, then query `reports.markdown_blob`.
- Either make `_profile.example.md` pure YAML with comments, or change `_shared.md` to extract a fenced YAML block before parsing. Do not mix the two.
- Fix hook tests by passing the staged path as an argument, OR change the hook to inspect `git diff --cached --name-only`. Update `tests/test_block_user_layer.py` for the new path.
- In 10-05, add explicit import edits for `yaml`, `subprocess`, `sys`, `count_tokens`.
- Expand SKLL-12 Wave 5 test to all seven scripts.
- Add CI assertions for `Profile Loading`, `Output Formatting`, `Save Report`, and D-NUM examples in `_shared.md`.
- Remove stale Phase 7 "until then" copy and make SKILL.md subagent text forward-link only.

## Next Step

To incorporate this feedback into another revision pass:

```
/gsd-plan-phase 10 --reviews
```

The 5 new HIGH issues are concrete bugs (off-by-one, wrong CLI surface, broken hook test design,
format mismatch, missing import edits) — not stylistic or stale-prose problems. They will cause
execution failures if not addressed before `/gsd-execute-phase 10`.
