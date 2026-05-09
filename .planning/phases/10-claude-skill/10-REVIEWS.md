---
phase: 10
reviewers: [codex]
reviewed_at: 2026-05-09T05:24:28Z
plans_reviewed:
  - 10-00-test-infrastructure-PLAN.md
  - 10-01-scripts-relocation-PLAN.md
  - 10-02-skill-md-scaffold-PLAN.md
  - 10-03-modes-PLAN.md
  - 10-04-references-PLAN.md
  - 10-05-ci-tests-PLAN.md
  - 10-06-integration-smoke-PLAN.md
skipped_reviewers:
  - claude (running inside Claude Code; skipped for independence)
  - ollama (only nomic-embed-text installed — embedding model, not chat)
  - gemini, opencode, qwen, cursor, coderabbit, lm_studio, llama_cpp (not installed)
---

# Cross-AI Plan Review — Phase 10

> Single-reviewer review (codex). Treat findings as one strong opinion, not a multi-model consensus.
> Re-run `/gsd-review 10` after installing additional CLIs (gemini, opencode, etc.) to triangulate.

## Codex Review

## Summary

The plans are well-structured as a phased test-first rollout, but they are not yet aligned with the newer `10-CONTEXT.md` decisions. The biggest issue is that several plans still implement the older research/roadmap assumptions: SKLL-13 is deferred, `_profile.example.md` is broad and duplicates calc inputs, subagent forward-links are incomplete, and script/reference plans allow Phase 6/7/8 artifacts to remain as stubs while still claiming Phase 10 success. As written, the phase could pass its own tests while failing the current Phase 10 contract.

## Strengths

- Clear wave ordering: test scaffold → script relocation → `SKILL.md` → modes → references → CI flips → integration smoke.
- Good emphasis on `git mv`, avoiding symlinks, and preserving skill-folder portability.
- Token and line-budget enforcement is planned early and wired into CI.
- The “always shell out” and “run `--help` first” doctrines are treated as testable requirements.
- User Layer protection is considered in `.gitignore`, pre-commit hook, and tests.
- Drift protection for copied `arm-mechanics.md` is a strong safeguard.

## Concerns

- [HIGH] `10-00-test-infrastructure-PLAN.md`, `10-05-ci-tests-PLAN.md`, and `10-06-integration-smoke-PLAN.md` defer SKLL-13, but `10-CONTEXT.md` explicitly says Phase 10 **does close SKLL-13** with auto-written reports and DuckDB ingest. This is the largest contract mismatch.

- [HIGH] `10-03-modes-PLAN.md` Task 2 uses the older broad `_profile.example.md` schema with geography, credit score, rates, loan terms, defaults, etc. This directly violates `D-PROF-01` and `D-PROF-02`, which require exactly four fields: `verbosity`, `citation_density`, `save_report`, `disambiguation`.

- [HIGH] `10-02-skill-md-scaffold-PLAN.md` Task 2 explicitly says not to include subagent dispatch boilerplate, but `D-SUBA-FW-01` requires a `## Subagents (Phase 11)` section in `SKILL.md` naming all three agents. `10-05` only tests `stress-test-agent`, so it would miss two required filenames.

- [HIGH] `10-03-modes-PLAN.md` Task 4 makes stress dispatch unconditional for `scenario_count > 5`, but `D-SUBA-FW-02` requires the exact existence-check seam: defer to `.claude/agents/stress-test-agent.md` **if it exists**, otherwise run inline.

- [HIGH] `10-01-scripts-relocation-PLAN.md` and `10-05-ci-tests-PLAN.md` rename `test_seven_scripts_in_skill_folder_only` while asserting only the three current CLIs plus `_cli_helpers.py`. That can falsely close SKLL-10 / SC-3 even though the requirement says all seven calc scripts must be inside the skill folder.

- [HIGH] `10-04-references-PLAN.md` Task 2 ships `refi-npv.md` and `apr-reg-z.md` as marker stubs. That may be acceptable only if Phase 6/7 are truly not complete, but Phase 10’s roadmap says it depends on Phase 6/7/8/9. The plan should not claim full SKLL-08 completeness if required source phases have already shipped.

- [HIGH] `10-03-modes-PLAN.md` Task 1 does not incorporate `D-13` Save Report behavior into `_shared.md`: filename sequencing, report file write, `node orchestration/db-write.mjs --insert-report --json`, and `_profile.md save_report: false` override.

- [HIGH] `10-00-test-infrastructure-PLAN.md` Task 4 imports `re`, `subprocess`, `sys`, `yaml`, and `count_tokens` before they are used. Task 5 requires `ruff check tests/test_skill.py`, which will likely fail on unused imports in Wave 0.

- [MEDIUM] `10-02-skill-md-scaffold-PLAN.md` Task 2 omits the `D-NUM-01..06` display formatting rules from the load-bearing shared output contract. The mode layer needs explicit money/rate/ratio/bps formatting instructions.

- [MEDIUM] `10-03-modes-PLAN.md` Task 4 says `evaluate` composes affordability but “dispatches via JSON to amortize.py only”; that likely cannot produce DTI/LTV/CLTV/PITI values unless another script or library path is specified.

- [MEDIUM] `10-05-ci-tests-PLAN.md` Task 4 says the envelope smoke covers the relocated scripts, but the code only tests `amortize.py`. The test name/docstring overstate coverage.

- [MEDIUM] `10-05-ci-tests-PLAN.md` Task 4 `test_profile_md_write_attempt_blocked` only checks the hook source contains a string. It does not actually prove forced staging is blocked.

- [MEDIUM] `10-06-integration-smoke-PLAN.md` Task 1 claims portability but only validates `--help` from a copied skill folder. Full script execution still depends on repo-root `lib/`, so the test proves artifact copyability, not standalone skill execution.

- [MEDIUM] `10-06-integration-smoke-PLAN.md` Task 1 adds a stricter `≤ 4300` token headroom gate, while the core decision is `≤ 4500`. This can block a compliant `SKILL.md` without being tied to a requirement.

- [LOW] `10-01-scripts-relocation-PLAN.md` Task 2 acceptance text misunderstands `git status --short` rename output as “exactly 8 R entries.” Git normally reports one rename line per file.

- [LOW] `10-06-integration-smoke-PLAN.md` Task 1 contains a no-op assertion: `... or True`, making that specific check meaningless.

## Suggestions

- Update `10-00`, `10-03`, `10-05`, and `10-06` to close SKLL-13 per `D-13-01..05`: add tests for report filename creation and DuckDB persistence, add the Save Report step to `_shared.md`, and remove “deferred to Phase 9” language.

- Replace `10-03` Task 2 `_profile.example.md` with the exact four-field YAML block from `D-PROF-01`. Add CI assertions that no extra top-level fields appear.

- Amend `10-02` Task 2 to include `## Subagents (Phase 11)` in `SKILL.md` with all three agent filenames. Amend `10-05` to assert the section header and all three names.

- Amend `10-03` Task 4 stress mode to include the literal `.claude/agents/stress-test-agent.md` path and `if it exists` wording.

- Rename or strengthen `test_seven_scripts_in_skill_folder_only`. Either assert all seven scripts are present, or rename it to `test_current_phase_scripts_relocated` and do not claim SC-3/SKLL-10 closure until all seven are available.

- In `10-00`, keep future imports inside the eventual test bodies or mark them with real immediate usage so Wave 0 passes `ruff`.

- In `10-05`, make the User Layer test actually force-stage a temp `_profile.md`, run `scripts/hooks/block-user-layer.py`, then clean up reliably with `try/finally`.

- In `10-06`, either remove the `≤ 4300` hard gate or make it advisory unless `SKILL.md` exceeds the official `≤ 4500` CI cap.

## Risk Assessment

**HIGH**: the execution structure is strong, but the plans currently contradict the latest Phase 10 decisions in multiple requirement-closing areas, especially SKLL-13, `_profile.example.md`, subagent forward-links, and all-seven-script closure.

---

## Consensus Summary

Only one reviewer responded, so "consensus" reduces to the single codex review above. Synthesizing
its top-level signals for the planner:

### Top Concerns (single-reviewer)

The review's HIGH-severity items cluster around **plan/CONTEXT drift**: phase 10 plans still
reflect older roadmap/research assumptions and contradict newer decisions captured in `10-CONTEXT.md`.

1. **SKLL-13 closure** — Plans defer reports + DuckDB ingest to Phase 9, but `D-13-01..05` say
   Phase 10 closes SKLL-13. Affects `10-00`, `10-03`, `10-05`, `10-06`.
2. **`_profile.example.md` schema** — Plan ships broad multi-section schema; `D-PROF-01/02` mandate
   exactly four fields (`verbosity`, `citation_density`, `save_report`, `disambiguation`).
   Affects `10-03` Task 2.
3. **Subagent forward-links** — `D-SUBA-FW-01` requires `## Subagents (Phase 11)` section in
   `SKILL.md` naming all three agents; plan explicitly excludes this. CI test in `10-05` only
   covers stress agent, missing the other two. Affects `10-02`, `10-05`.
4. **Stress dispatch seam** — `D-SUBA-FW-02` requires literal `.claude/agents/stress-test-agent.md`
   with "if it exists" gate; plan uses unconditional `scenario_count > 5` dispatch.
   Affects `10-03` Task 4.
5. **Seven-script closure** — Test renamed to `test_seven_scripts_in_skill_folder_only` but only
   asserts 3 current CLIs + helper, falsely closing SKLL-10/SC-3. Affects `10-01`, `10-05`.
6. **Wave 0 ruff failure** — Test scaffold imports `re/subprocess/sys/yaml/count_tokens` before use;
   `ruff check` gate in Task 5 will fail. Affects `10-00` Task 4–5.
7. **Reference stub legitimacy** — `refi-npv.md` and `apr-reg-z.md` ship as marker stubs even though
   phase 10 depends on Phase 6/7. SKLL-08 may be falsely closed. Affects `10-04` Task 2.
8. **Display formatting in `_shared.md`** — `D-NUM-01..06` (money/rate/ratio/bps formatting) not
   captured in shared output contract. Affects `10-02` / `10-03`.

### Medium Concerns

- `evaluate` mode dispatches only to `amortize.py` but is meant to compose affordability (DTI/LTV/CLTV/PITI).
- Envelope smoke test only covers `amortize.py`; name/docstring overstate coverage.
- Profile-write-block test asserts on hook source string, not on actually-blocked staging.
- Portability smoke only tests `--help`, not full script execution under copied-skill conditions.
- `≤ 4300` token gate in `10-06` is stricter than the official `≤ 4500` requirement.

### Low Concerns

- `git status --short` rename-row interpretation in `10-01` Task 2.
- `... or True` no-op assertion in `10-06` Task 1.

### Divergent Views

N/A — single reviewer.

## Next Step

To incorporate this feedback into a replan:

\`\`\`
/gsd-plan-phase 10 --reviews
\`\`\`

The planner will read this file and produce updated PLAN.md files addressing the HIGH/MEDIUM
concerns above before execution.
