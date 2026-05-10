# Phase 11 Plan-Check (Re-verification)

**Phase:** 11 — Subagents
**Verified:** 2026-05-02 (re-run after 11-04/05/06 landed)
**Status:** PASS WITH CONCERNS — 0 blockers, 4 concerns; ready to execute with concern acknowledgment

> **SUPERSEDES** prior `11-PLAN-CHECK.md` which ran before 11-04, 11-05, 11-06 landed and recorded outdated BLOCKERs (missing-plan errors, no SUBA-04/05/06 coverage). All prior BLOCKERs are now resolved.

## Tally (replaces prior count)

| Severity | Count | Topics |
|---|---|---|
| **BLOCKER** | **0** | (prior tally: 5; all resolved by 11-04/05/06 landing) |
| **CONCERN** | **4** | (1) Phase 10 hard dependency persists for executable verification; (2) Plan 11-04 branch-(b) selection protocol creates a documented-but-conditional SC-2 closure; (3) SC-3 transcript fixture is synthetic-deferred-to-live — Plan 11-05 D-02 explicitly defers live capture to nightly eval, not CI; (4) `anthropic.count_tokens` requires `ANTHROPIC_API_KEY` — SUBA-06 SKIPs in airgapped CI |
| **PASS** | **5 SCs + 6 Reqs** | All 5 ROADMAP success criteria + all 6 SUBA-01..06 requirements have traceable plan coverage |

---

## Per-Success-Criterion Verdicts

### SC-1 — Three agent files with valid frontmatter (`model:`, `skills: [mortgage-ops]`, description)

**Verdict:** PASS

**Plans delivering:**
- 11-01 Task 1 (`.claude/agents/amortization-agent.md` — name=amortization-agent, model=haiku, skills=[mortgage-ops], description >30 chars)
- 11-02 Task 1 (`.claude/agents/refi-npv-agent.md` — model=sonnet, skills=[mortgage-ops])
- 11-03 Task 1 (`.claude/agents/stress-test-agent.md` — model=haiku per D-01, skills=[mortgage-ops], description starts with literal "Use proactively for stress sweeps with >5 scenarios" per D-04)

**Test gate:** Plan 11-00 ships 6 xfail stubs; Plans 11-01, 11-02, 11-03 each flip their respective frontmatter test (test_SUBA_01/02/03_..._frontmatter_*) — assertions cover required keys, name=stem, model whitelisted, skills==["mortgage-ops"], description >30 chars. Plan 11-05 Task 2 Flip 1 adds a parametrized SC-5 reinforcement test that re-asserts skills field across all three agents.

**Justification:** All three agent files have explicit, verbatim frontmatter content embedded in the action sections of 11-01..03. Acceptance criteria grep each required field. The 6-key requirement coverage list (REQUIRED_FRONTMATTER_KEYS) from Wave 0 makes the test parametrizable across agents.

---

### SC-2 — Stress mode in SKILL.md routes any sweep with >5 scenarios to stress-test-agent

**Verdict:** PASS (with conditional path documented)

**Plans delivering:**
- 11-04 Task 1 (always-shipped TODO marker `11-04-SUBA-05-TODO.md` documenting the cross-phase contract with verbatim insertion text)
- 11-04 Task 2 branch (a) — IF Phase 10 has shipped `.claude/skills/mortgage-ops/{SKILL.md,modes/stress.md}` at execution time, edits both files in place to insert the SUBA-05 routing block matching the regex `(scenarios? (>|more than|greater than) 5|scenario_count > 5).*(stress-test-agent|subagent)` and a SKILL.md cross-reference
- 11-04 Task 2 branch (b) — IF Phase 10 has NOT shipped, defers the file edits to Phase 10 with the TODO marker as the canonical contract; updates the SUBA-05 xfail reason to point at the marker

**Test gate:** Wave 0 stub `test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent` is flipped in 11-04 branch (a) to a regex check matching the literal SC-2 wording; in branch (b) the test remains xfail-skip with a documented forward-pointer.

**Justification:** Threshold is strictly `>5` (D-01 in 11-04) — matches verbatim ROADMAP SC-2 + REQUIREMENTS SUBA-05. The cross-phase TODO marker is the canonical record regardless of branch, so SC-2 is either CLOSED (branch a) or DEFERRED-WITH-CONTRACT (branch b). Either outcome fulfills the planning gate; the executable closure happens when Phase 10 ships.

---

### SC-3 — 50-scenario rate-shock summary < 1,000 tokens via the eval harness

**Verdict:** PASS (CI determinism via synthetic fixture — see Concern #3)

**Plans delivering:**
- 11-00 (anthropic SDK pinned exactly per Pitfall 4; xfail stub for SUBA-06 with skipif on ANTHROPIC_API_KEY)
- 11-05 Task 1 (synthetic transcript `tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl` hand-authored to ~600 tokens with 40% headroom)
- 11-05 Task 2 Flip 4 (flips test_SUBA_06_stress_summary_under_1000_tokens to call `anthropic.Anthropic().messages.count_tokens(model="claude-haiku-4-5", messages=[{role: assistant, content: <fixture>}])` and assert `response.input_tokens < 1000`)

**Test gate:** Per D-01 + D-03 in 11-05: tokenizer = anthropic.count_tokens (tiktoken explicitly REJECTED per RESEARCH Standard Stack); threshold strictly `<1000` (matches ROADMAP SC-3 verbatim).

**Justification:** Strict threshold + correct tokenizer + committed fixture + skipif graceful degradation = SC-3 has a green-bar regression gate when ANTHROPIC_API_KEY is present. Synthetic-vs-live concern noted below (Concern #3).

---

### SC-4 — refi-npv-agent ranked NPV table; amortization-agent CSV/markdown

**Verdict:** PASS

**Plans delivering:**
- 11-05 Task 1 (synthetic transcripts: `refi_3_offers.transcript.jsonl` with 3 offers ranked descending; `amort_single_loan.transcript.jsonl` with markdown-table-OR-CSV-path content)
- 11-05 Task 2 Flip 2 (test_SUBA_04_refi_handoff_returns_ranked_table — 4 shape assertions: lender+NPV columns; ≥4 rows; descending NPV; "Computed by:" + refi_npv.py citation)
- 11-05 Task 2 Flip 3 (test_SUBA_04_amort_handoff_returns_csv_or_markdown — markdown-table OR csv-path regex `reports/\d{3}-amortization-\d{4}-\d{2}-\d{2}\.csv`; "Computed by:" + amortize.py citation)

**Justification:** Both refi and amort output shapes have explicit assertion functions tied to canonical agent body specs from 11-02 and 11-01. NPV-descending ordering enforced (catches a real failure mode); markdown-OR-csv disjunction matches Plan 11-01 Hard rule #4.

---

### SC-5 — Each subagent's `skills:` resolves to mortgage-ops skill at spawn (smoke test)

**Verdict:** PASS (with cross-phase tolerance — see Concern #1)

**Plans delivering:**
- 11-05 Task 2 Flip 1 (test_SUBA_04_skills_field_resolves_for_each_agent, parametrized over EXPECTED_AGENTS)
  - Part (a) frontmatter `skills == ["mortgage-ops"]` — passes when 11-01..03 ship
  - Part (b) `os.path.exists('.claude/skills/mortgage-ops/scripts/{amortize,refi_npv,stress_test}.py')` — gracefully skips if Phase 10 hasn't relocated scripts (D-04 in 11-05; mirrors 11-04 branch-(b) cross-phase tolerance)

**Justification:** RESEARCH Pitfall 1 was correctly internalized — SC-5 is a filesystem-reachability check, NOT a context-inclusion check. The skipif on script existence is the right tolerance pattern (CI noise prevention without sacrificing correctness once Phase 10 lands).

---

## Per-Requirement Verdicts

| Req | Plan(s) | Verdict | Justification |
|---|---|---|---|
| **SUBA-01** | 11-01 Task 1 + Task 2 (test flip) | PASS | amortization-agent.md with model=haiku, body shells out to scripts/amortize.py, output contract = markdown table OR CSV path under reports/{NNN}-amortization-{YYYY-MM-DD}.csv |
| **SUBA-02** | 11-02 Task 1 + Task 2 | PASS | refi-npv-agent.md with model=sonnet, multi-offer ranking workflow, borrower-perspective sign convention pinned (Phase 6 REFI-09); tools=[Read,Bash] (no Write per RESEARCH Open Q1 v1) |
| **SUBA-03** | 11-03 Task 1 + Task 2 | PASS | stress-test-agent.md with model=haiku per LOCKED D-01 (resolves PATTERNS #1a item 2); description starts with D-04 trigger phrase; tools=[Read,Bash,Write] for CSV escape hatch; pins ≤1000-token budget + Phase 8 scenario_summary input contract + "Computed by:" citation discipline |
| **SUBA-04** | 11-05 Task 2 Flip 1 (parametrized) | PASS | Each agent's skills field asserted ==["mortgage-ops"]; bundled-script reachability assertion gracefully skips when Phase 10 hasn't relocated scripts |
| **SUBA-05** | 11-04 (branch a OR b) | PASS conditional | Branch (a): regex-test passes against modes/stress.md. Branch (b): TODO marker is canonical contract; xfail-with-pointer; Phase 10 closes the loop on landing. Both outcomes satisfy the planning gate |
| **SUBA-06** | 11-05 Task 1 + Task 2 Flip 4 | PASS | anthropic.count_tokens against synthetic 50-scenario transcript fixture; strict <1000 threshold; skipif on ANTHROPIC_API_KEY for airgap-friendly CI |

---

## Cross-Cutting Concerns

### Concern #1 — Phase 10 hard dependency persists (executable verification deferred)

**Severity:** CONCERN (not BLOCKER)

**Detail:** modes/stress.md, SKILL.md, and the relocated scripts at `.claude/skills/mortgage-ops/scripts/{amortize,refi_npv,stress_test}.py` do not exist until Phase 10 ships (SKLL-01/05/10). Phase 11 plans correctly document this as a soft dependency for SHIPPING (frontmatter is static text; xfail flips for SUBA-01/02/03 are filesystem-only against the agent files themselves) and a hard dependency for live dispatch verification.

**Concrete impact:**
- 11-04 may execute branch (b), deferring the SUBA-05 file edits to Phase 10 with a documented contract
- 11-05 SC-5 part (b) script-existence checks gracefully SKIP until Phase 10 lands SKLL-10
- Live agent dispatch verification (which exercises Bash → script invocation → JSON output) is impossible until Phase 10 ships SKILL.md + scripts

**Mitigation in plans:** Documented in every plan's `<dependencies>` section; 11-04 explicit branch protocol; 11-05 D-04 explicit skipif tolerance. No plan lies about being self-sufficient.

**Recommended action:** Acknowledge at execution time. If Phase 10 has shipped, branch (a) closes SC-2 fully. If not, branch (b) is sufficient for Phase 11 closeout per the cross-phase contract; a follow-up plan (Phase 10 closeout or Phase 11 cleanup) flips the SUBA-05 xfail when Phase 10 lands.

---

### Concern #2 — Plan 11-04 branch-(a)-vs-(b) execution protocol

**Severity:** CONCERN (not BLOCKER)

**Detail:** 11-04 Task 2 selects between two execution paths via `test -f .claude/skills/mortgage-ops/modes/stress.md && test -f .claude/skills/mortgage-ops/SKILL.md`. This is a valid cross-phase update protocol but introduces dual-path acceptance criteria — the Phase 11 closeout state varies by execution-time facts.

**Concrete impact:** SUBA-05 requirement closure is conditional. Branch (a) → CLOSED. Branch (b) → DEFERRED-WITH-CONTRACT (TODO marker file is the binding artifact). Two correct end-states for the same plan.

**Mitigation in plans:** Both paths have explicit acceptance criteria; the TODO marker is shipped in both branches as the canonical contract record; the executor's branch selection is recorded in the marker's "Branch" section.

**Recommended action:** At Phase 11 verification time, the verifier (`/gsd-verify-work`) MUST inspect the TODO marker's filled-in Status header to determine which branch executed and apply the correct closure semantics. Phase 11 SUMMARY should explicitly state the branch taken.

---

### Concern #3 — Transcript-fixture determinism: synthetic for SC-3/SC-4 (live capture deferred to nightly eval)

**Severity:** CONCERN (not BLOCKER)

**Detail:** Per 11-05 D-02, the three transcript fixtures are SYNTHETIC (hand-authored to mirror canonical agent output shapes from 11-01..03), not live captures. SC-3 (1000-token budget) and SC-4 (refi/amort shape) are measured against synthetic content. Live capture is documented in `tests/fixtures/subagent_transcripts/README.md` as a quarterly regeneration ritual via `claude -p`, but is NOT run in CI.

**Concrete impact:** The SC gates measure what we WANT the agents to produce, not what they actually produce in a live session. Drift between synthetic and live agent output is unmonitored without nightly eval regeneration (deferred to Phase 12 EVAL-03 / EVAL-04).

**Mitigation in plans:** D-02 rationale explicit (CI determinism + free + airgap-safe + contract-is-shape). README documents the live-capture recipe + the quarterly + post-prompt-change regeneration cadence. T-11-28 + T-11-32 in 11-05 threat model address fixture drift via the quarterly ritual. Synthetic content includes "Computed by:" cite + script reference, so the test can't pass on LLM-fabricated numbers without breaking the citation assertion.

**Recommended action:** Acknowledge the trade-off explicitly in Phase 11 SUMMARY and at Phase 12 planning time — Phase 12 EVAL-03 / EVAL-04 must pick up the nightly live-capture + diff-against-synthetic workflow. If the user wants stronger v1 guarantees (live capture in CI, accepting paid-tier API costs), surface as a follow-up plan, not a Phase 11 blocker.

---

### Concern #4 — `anthropic.count_tokens` API key requirement

**Severity:** CONCERN (not BLOCKER)

**Detail:** SUBA-06 (SC-3 token-budget gate) requires `ANTHROPIC_API_KEY` at test time because `anthropic.Anthropic().messages.count_tokens(...)` is a network call. Per Anthropic docs the call is FREE (separate rate limit, no content billing), but the key + network round-trip are required.

**Concrete impact:** In airgapped CI or local dev without the key, SUBA-06 reports SKIPPED (not FAILED) per `@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"))`. SC-3 is unverifiable in those environments.

**Mitigation in plans:** Skipif is explicit and documented; CI is expected to inject the key as a secret per 11-05 D-01 + RESEARCH Standard Stack. tiktoken explicitly rejected per RESEARCH (OpenAI-specific, drifts ~5-20% on the <1k boundary), so there is no offline alternative.

**Recommended action:** Confirm CI has `ANTHROPIC_API_KEY` injected as a repository secret before Phase 11 verification. If the user runs Phase 11 verification locally without the key, SC-3 will SKIP — note this in the verify-work output.

---

## Recommended Actions (in execution order)

1. **Confirm Phase 10 status before execution.** If Phase 10 has shipped SKILL.md + modes/stress.md + relocated scripts, all 7 Phase 11 waves execute fully and SC-1..SC-5 all close green-bar. If Phase 10 has NOT shipped, Phase 11 ships with branch (b) deferral on SUBA-05 + skipif on SC-5 part (b); Phase 11 SUMMARY records the deferred state and the cross-phase TODO contract.

2. **Inject `ANTHROPIC_API_KEY` into CI secrets before Phase 11 verification.** Otherwise SC-3 SKIPs and the budget gate is unverified.

3. **At Phase 12 planning time, ensure EVAL-03 / EVAL-04 pick up the live-capture nightly regeneration of the transcript fixtures.** This closes the synthetic-vs-live drift gap that Concern #3 identifies.

4. **Execute Phase 11 in wave order: 11-00 → 11-01/02/03 (parallelizable) → 11-04 → 11-05 → 11-06.** Wave 0 is the test scaffold; Waves 1-3 are independent agent files; Wave 4 wires the routing seam (or defers); Wave 5 closes SUBA-04+06; Wave 6 documents.

5. **At Phase 11 verification time, the verifier should:**
   - Read `.planning/phases/11-subagents/11-04-SUBA-05-TODO.md` Status header to determine SUBA-05 branch closure
   - Confirm the count of passing tests matches expectations (5 SUBA tests passing or 4 + 1 deferred)
   - Confirm no orphan xfails remain except (possibly) the SUBA-05 deferred xfail with the TODO marker reason

---

## Why this re-verification supersedes the prior check

The prior `11-PLAN-CHECK.md` ran when only 11-00, 11-01, 11-02, 11-03 existed in the phase directory. It correctly flagged:
- SUBA-04 had no implementing plan (BLOCKER) — **NOW RESOLVED** by 11-05 Task 2 Flip 1
- SUBA-05 had no implementing plan (BLOCKER) — **NOW RESOLVED** by 11-04 (with cross-phase branch protocol)
- SUBA-06 had no implementing plan (BLOCKER) — **NOW RESOLVED** by 11-05 Task 2 Flip 4
- SC-2 / SC-3 / SC-4 had no test gates planned (BLOCKERs) — **NOW RESOLVED** by 11-04 (regex test) + 11-05 (count_tokens + shape tests)
- No Phase 11 documentation surface (concern) — **NOW RESOLVED** by 11-06 (subagent-routing.md + .claude/agents/README.md + CLAUDE.md cross-link)

All prior BLOCKERs are resolved. The 4 remaining items are CONCERNs (operational acknowledgments), not BLOCKERs (planning gaps).

---

*Re-verified: 2026-05-02 by gsd-plan-checker re-run after 11-04/05/06 landed.*
