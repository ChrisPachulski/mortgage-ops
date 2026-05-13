---
phase: 12-fred-eval
plan: 06
subsystem: evals
tags: [phase-12, wave-6, eval-oracles, paired-expected, sc-3-sc-4-close, eval-02-close, eval-04-close, gate-100-pct]
requirements: [EVAL-02]
dependency-graph:
  requires:
    - evals/runner.py (Plan 12-04 — HarnessReport + three-bucket aggregator)
    - evals/metrics.py (Plan 12-04 — NumericScore + STDOUT-only sourcing)
    - evals/prompts/*.md (Plan 12-05 — 22 prompts paired by stem)
    - tests/fixtures/fred/MORTGAGE30US-2026-05-13.json (Plan 12-05 — fixture cache value=6.50)
    - python-frontmatter dev-dep (Plan 12-00)
  provides:
    - evals/expected/*.json (22 oracle JSON files; 13 anchored + 9 skipped)
    - tests/test_evals_coverage.py (3 citation-coverage + end-to-end gate tests)
    - evals/expected/live-rate-injection-01.json (fixture-cache anchor with provenance=static)
    - SC-4 gate closure end-to-end (numeric_match_rate=1.0 >= 0.95)
  affects:
    - Plan 12-07 (CI wiring) — runner now exits 0 with rate=1.0 on v1 set; CI gate can lock at 0.95
    - Phase 12 EVAL-01..04 + SC-3 + SC-4 + SC-5 + D-12-SC1-01 closed end-to-end at this layer
    - Future regression: any anchored oracle drift drops gate below 95% -> CI fail
tech-stack:
  added: []
  patterns:
    - paired oracle JSON pinned by stem to prompts (1:1 EVAL-02 contract)
    - uniform v1_frozen_at="2026-05-10" across all 22 oracles (RESEARCH §Pattern 4 line 361 idiom)
    - static-provenance exemption for fixture-cache-sourced numbers (live-rate-injection-01)
    - citation-coverage meta-test (every stdout-provenance source_script must exist in skill bundle)
    - end-to-end gate meta-test pinned to exact 13/0/9 distribution
key-files:
  created:
    - evals/expected/evaluate-01.json (anchored; monthly_pi=1264.14 @ tol 0.005)
    - evals/expected/evaluate-02.json (anchored; monthly_pi=2528.27)
    - evals/expected/evaluate-03.json (skipped; defer_until_phase=13.0)
    - evals/expected/compare-01.json (anchored; 2 expected_numbers — 2528.27 + 1797.66)
    - evals/expected/compare-02.json (anchored; 2 expected_numbers — 761.78 + 1264.14)
    - evals/expected/compare-03.json (skipped)
    - evals/expected/refinance-01.json (anchored; npv=60705.48 @ tol 0.01)
    - evals/expected/refinance-02.json (skipped)
    - evals/expected/refinance-03.json (skipped)
    - evals/expected/affordability-01.json (anchored; monthly_pi=2528.27)
    - evals/expected/affordability-02.json (anchored; max_loan_amount=646322.54 @ tol 0.01)
    - evals/expected/affordability-03.json (skipped)
    - evals/expected/stress-01.json (anchored; monthly_pi_at_6_5pct=2528.27)
    - evals/expected/stress-02.json (skipped)
    - evals/expected/stress-03.json (skipped)
    - evals/expected/amortize-01.json (anchored; monthly_pi=1264.14)
    - evals/expected/amortize-02.json (anchored; monthly_pi=1797.66)
    - evals/expected/amortize-03.json (anchored; monthly_pi=761.78)
    - evals/expected/arm-01.json (anchored; initial_period_monthly_pi=2398.20 @ tol 0.01)
    - evals/expected/arm-02.json (skipped)
    - evals/expected/arm-03.json (skipped)
    - evals/expected/live-rate-injection-01.json (anchored; current_30yr_rate=6.50 provenance=static)
    - tests/test_evals_coverage.py (95 lines; 3 tests covering SC-3/SC-4/schema-consistency)
  modified:
    - tests/test_evals_runner.py (final xfail flipped to live; module docstring -> Wave-6 complete)
decisions:
  - "Used Write tool per oracle file (22 separate calls) rather than a single Python generator script — matches plan's explicit per-file content blocks and gives reviewer-friendly atomic diffs. Each oracle is a literal mirror of the plan body's locked JSON content."
  - "Uniform v1_frozen_at=2026-05-10 across all 22 oracles, per RESEARCH §Pattern 4 line 361 idiom and plan body Rule. Date matches Phase 12 CONTEXT.md authorship date even though fixture cache filenames are 2026-05-13; the freeze-date is a contract version tag, not a timestamp."
  - "Ruff auto-fixed import sort in tests/test_evals_coverage.py (moved `from evals.runner import ...` adjacent to the third-party `frontmatter` + `pytest` imports per project ruff config). Confirmed mypy --strict + ruff clean after auto-fix; no behavioral change."
  - "Task 2 collapsed RED/GREEN into a single commit: prompts + oracles already shipped pre-task, so authoring tests/test_evals_coverage.py was authoring already-passing assertions (verification layer, not feature TDD). Plan-level RED gate provenance lives in Plan 12-00 Wave-0 xfail stubs; Plan 12-06 is the GREEN ship."
metrics:
  duration-seconds: 260
  duration-minutes: 4.3
  task-count: 2
  file-count: 24
  commit-count: 2
  completed: 2026-05-13T18:42:21Z
---

# Phase 12 Plan 06: 22 paired oracle JSON files + end-to-end gate closure Summary

**One-liner:** Shipped 22 paired oracle JSON files under `evals/expected/` (13 anchored + 9 skipped) mirroring Plan 12-05 prompt frontmatter byte-for-byte, flipped the final xfail in `tests/test_evals_runner.py`, and added a 3-test `tests/test_evals_coverage.py` module that closes SC-3 (citation coverage) + SC-4 (numeric_match_rate=1.0 >= 0.95 on 13 anchored / 9 skipped) + schema-consistency end-to-end — `python -m evals.runner` exits 0.

## What Shipped

### 22 paired oracle JSON files in `evals/expected/`

Distribution (PINNED by D-12-SC4-01 math — 13 anchored / 9 skipped → 100% gate pass on (13+0)):

| Mode | Anchored | Skipped | Total |
|------|---------:|--------:|------:|
| evaluate | 2 | 1 | 3 |
| compare | 2 | 1 | 3 |
| refinance | 1 | 2 | 3 |
| affordability | 2 | 1 | 3 |
| stress | 1 | 2 | 3 |
| amortize | 3 | 0 | 3 |
| arm | 1 | 2 | 3 |
| live-rate-injection | 1 | 0 | 1 |
| **TOTAL** | **13** | **9** | **22** |

Each oracle mirrors its paired prompt's frontmatter byte-for-byte, with the addition of `schema_version: 1`, `numeric_status: "anchored"|"skip"`, and `v1_frozen_at: "2026-05-10"`. 1:1 stem-matching with `evals/prompts/` is verified by the runner and by `test_every_prompt_has_paired_oracle` (now live, was xfail).

### Citation-coverage meta-test (`tests/test_evals_coverage.py`)

Three new tests, all green on first run (verification-layer; no RED iteration needed because Plan 12-05 + 12-06 shipped the contracts in parallel):

| Test | Closes | What it asserts |
|------|--------|-----------------|
| `test_every_stdout_provenance_has_existing_source_script` | SC-3 | Every anchored expected_number with `provenance: "stdout"` cites a `source_script` that exists at `.claude/skills/mortgage-ops/scripts/{source_script}`. Defends against future script-relocations / renames. |
| `test_prompt_mode_matches_oracle_mode` | Schema consistency | For every prompt stem, `frontmatter.load(prompt).metadata["mode"]` equals `json.loads(oracle)["mode"]`. Pins Plan 12-05 + Plan 12-06's parallel authoring contract. |
| `test_runner_gate_passes_on_v1_set` | SC-4 + D-12-SC4-01 | `evals.runner.run_all(PROMPTS_DIR)` produces `numeric_pass_count=13`, `numeric_fail_count=0`, `numeric_skip_count=9`, `numeric_match_rate == pytest.approx(1.0)`, `>= 0.95`. The end-to-end gate closure. |

### Test surface flips

| File | Before | After | Delta |
|------|--------|-------|-------|
| `tests/test_evals_runner.py` | 1 xfail | 0 xfail | +1 newly green |
| `tests/test_evals_coverage.py` | (did not exist) | 3 live tests | +3 newly green |
| **Full suite** | 633 pass / 5 skip / 2 xfail | **637 pass / 5 skip / 1 xfail** | +4 newly green; 1 xfail remains (Phase 8+ ARM oracle, unrelated) |

The remaining 1 xfail is `tests/test_arm.py::test_oracle_cross_validation_5_1`, deferred to Phase 8+ for human Bankrate/Vertex42 captures. Not in scope for Plan 12-06.

## Citation-Coverage Source-Script Audit

Every anchored stdout-provenance oracle cites a script that exists in the skill bundle:

| Oracle | source_script | Skill bundle path | Exists? |
|--------|---------------|-------------------|---------|
| evaluate-01 (monthly_pi=1264.14) | amortize.py | `.claude/skills/mortgage-ops/scripts/amortize.py` | OK |
| evaluate-02 (monthly_pi=2528.27) | amortize.py | same | OK |
| compare-01 (2 entries) | amortize.py | same | OK |
| compare-02 (2 entries) | amortize.py | same | OK |
| refinance-01 (npv=60705.48) | refi_npv.py | `.claude/skills/mortgage-ops/scripts/refi_npv.py` | OK |
| affordability-01 (monthly_pi=2528.27) | affordability.py | `.claude/skills/mortgage-ops/scripts/affordability.py` | OK |
| affordability-02 (max_loan=646322.54) | affordability.py | same | OK |
| stress-01 (monthly_pi_at_6_5pct=2528.27) | stress_test.py | `.claude/skills/mortgage-ops/scripts/stress_test.py` | OK |
| amortize-01 (monthly_pi=1264.14) | amortize.py | same | OK |
| amortize-02 (monthly_pi=1797.66) | amortize.py | same | OK |
| amortize-03 (monthly_pi=761.78) | amortize.py | same | OK |
| arm-01 (initial_period_monthly_pi=2398.20) | arm_simulate.py | `.claude/skills/mortgage-ops/scripts/arm_simulate.py` | OK |
| live-rate-injection-01 (current_30yr_rate=6.50) | fixture_cache | (static — exempt) | N/A |

12 stdout-provenance citations + 1 static-provenance citation = 13 anchored oracles total. Source-script existence enforced by `test_every_stdout_provenance_has_existing_source_script`.

## Gate Math (D-12-SC4-01) — Worked End-to-End

`python -m evals.runner` on the shipped 22-prompt + 22-oracle set:

```json
{
  "n_prompts": 22,
  "route_match_count": 12,
  "route_match_rate": 0.5455,
  "numeric_pass_count": 13,
  "numeric_fail_count": 0,
  "numeric_skip_count": 9,
  "numeric_match_rate": 1.0,
  "failures": [...]
}
```

Gate math (D-12-SC4-01):
```
numeric_match_rate = numeric_pass_count / (numeric_pass_count + numeric_fail_count)
                   = 13 / (13 + 0)
                   = 1.0
                   >= 0.95  =>  SC-4 GATE PASSES
```

Exit code: 0.

### Why route_match_count is 12, not 22

The replay-stub runner's `synthesize_stub_transcript` produces transcripts whose `model_response` is the prompt body + label/value lines. The route_match scorer requires every `expected_route_keyword` to appear either in the response OR in a subprocess cmd. Some keywords (e.g., the word "evaluate" for evaluate-01, or "compare" for compare-01) do not naturally appear in the prompt body, so they fail the stub's lenient route-substring check. **This is expected for v1 replay-stub mode** — it validates internal consistency of prompt/oracle pairs, not the production agent's routing prose. Live-mode replay (Phase 13+) will exercise the real agent and route_match will land near 1.0.

What matters for SC-4 closure is the numeric_match_rate, which is the gate-locked metric per D-12-SC4-01. That metric is 1.0 on the shipped set.

### live-rate-injection-01 deep-dive (D-12-SC1-01 closure)

```json
{
  "schema_version": 1,
  "id": "live-rate-injection-01",
  "mode": "evaluate",
  "numeric_status": "anchored",
  "expected_scripts": [],
  "expected_numbers": [
    {
      "label": "current_30yr_rate",
      "value": "6.50",
      "tolerance": "0.01",
      "source_script": "fixture_cache",
      "provenance": "static"
    }
  ],
  "expected_route_keywords": ["data/cache/fred_MORTGAGE30US.json", "6.50"],
  "v1_frozen_at": "2026-05-10"
}
```

- `provenance: "static"` exempts the rate from the D-12-SC3-01 STDOUT-only sourcing rule (cache values are read via the Read tool, not subprocess stdout).
- `value: "6.50"` matches `tests/fixtures/fred/MORTGAGE30US-2026-05-13.json` `entries.MORTGAGE30US.value: "6.50"`.
- `expected_scripts: []` — no calc-script invocation expected; the skill reads the cache file directly.
- Closes D-12-SC1-01 end-to-end: the fresh-session injection eval now ships, anchored to the synthetic fixture cache (NOT live FRED) for CI determinism.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff auto-fixed import sort in `tests/test_evals_coverage.py`**
- **Found during:** Task 2 verification (ruff check)
- **Issue:** I001 — `from evals.runner import ...` was separated from the third-party imports (`frontmatter`, `pytest`) by a blank line; ruff's import-grouping rule wants first-party imports grouped with third-party in this project's config.
- **Fix:** Ran `ruff check --fix` once; the linter regrouped the imports without behavioral change. Re-verified mypy --strict + ruff both clean.
- **Files modified:** `tests/test_evals_coverage.py`
- **Commit:** `79c3fe6` (bundled with Task 2)

### Architectural Changes
None — implementation matched the plan's 22-oracle content blocks verbatim, and the test additions matched the plan's behavior + action sketches.

### Authentication Gates
None — pure file authoring and Python tests; no external services.

## Convention: v1_frozen_at uniformity

Every one of the 22 oracles carries `"v1_frozen_at": "2026-05-10"` per RESEARCH §Pattern 4 line 361 idiom and plan body Rule. This date is a *contract version tag* (when the v1 oracle set was authored, locking schema + values), NOT a timestamp of file modification. The fixture cache filenames are dated 2026-05-13 because they were shipped in Plan 12-05 on that date, but the oracle freeze-date stays 2026-05-10 to mark Phase 12 CONTEXT.md authorship as the contract anchor.

## End-to-End Requirement Closure Receipt

| Requirement | Pre-Plan 12-06 status | Post-Plan 12-06 status |
|-------------|-----------------------|------------------------|
| EVAL-01 (22 prompts) | closed by Plan 12-05 | closed (unchanged) |
| EVAL-02 (paired oracles) | open (oracles missing) | **closed** — 22 oracles, 1:1 stem-paired |
| EVAL-03 (runner exit 0 on v1 set) | closed at aggregator layer by Plan 12-04; end-to-end open | **closed end-to-end** — `python -m evals.runner` exits 0 |
| EVAL-04 (citation coverage) | open | **closed** — `test_every_stdout_provenance_has_existing_source_script` |
| SC-3 (numbers traceable to script or static) | partial (scorer layer by Plan 12-04) | **closed end-to-end** via citation-coverage meta-test |
| SC-4 (numeric_match_rate >= 0.95) | partial (math by Plan 12-04; D-12-SC4-01 three-bucket gate) | **closed end-to-end** — rate=1.0 on shipped set |
| SC-5 (every mode covered) | closed by Plan 12-05 | closed (unchanged) |
| D-12-SC1-01 (live-rate-injection eval) | partial (prompt + fixture by Plan 12-05) | **closed end-to-end** — oracle ships, anchors to fixture |
| LIVE-01..04 | closed across Plans 12-02 + 12-03 | closed (unchanged) |

All Phase 12 functional requirements (LIVE-01..04, EVAL-01..04) and the three D-12-* gate locks (SC1-01, SC3-01, SC4-01) close end-to-end at this layer. Plan 12-07 (CI wiring) is the remaining surface for this phase.

## Commits

| Hash | Description | Files | Insertions |
|------|-------------|-------|-----------:|
| `9e373ca` | feat(12-06): ship 22 paired eval oracle JSON files (13 anchored + 9 skipped) | 22 oracle .json | ~290 |
| `79c3fe6` | feat(12-06): flip final xfail + add citation-coverage end-to-end gate tests | tests/test_evals_runner.py + tests/test_evals_coverage.py | 101 ins / 17 del |

## Threat Flags

None — the implementation respects the plan's `<threat_model>`:

- **T-12-06-01 (Tampering: oracle JSON drift)** — **mitigated**: `test_runner_gate_passes_on_v1_set` pins the exact 13/0/9 distribution; any future oracle edit that flips an anchored prompt out of PASS triggers `assert numeric_pass_count == 13` failure in CI.
- **T-12-06-02 (Tampering: source_script renames)** — **mitigated**: `test_every_stdout_provenance_has_existing_source_script` walks `.claude/skills/mortgage-ops/scripts/` and asserts existence for every cited script. Renaming `amortize.py` without updating oracle.source_script trips the test immediately.
- **T-12-06-03 (Information Disclosure: live-rate fixture pinning)** — **accepted**: Oracle pins to fixture cache 6.50% (NOT live FRED rate); rationale: CI determinism per D-12-SC1-01; documented in Plan 12-05 fixture README. The static-provenance tag exempts the value from STDOUT-only sourcing.

## Verification

All gates green:
- ✅ 22 oracle files in `evals/expected/` (1:1 paired with prompts by stem)
- ✅ 13 anchored + 9 skipped distribution (verified by JSON parse loop)
- ✅ All 22 files parse cleanly as JSON
- ✅ `live-rate-injection-01.json` has `provenance: "static"` + value=6.50
- ✅ `python -m evals.runner` exits 0 with `numeric_match_rate: 1.0`
- ✅ 0 xfails remain in `tests/test_evals_runner.py` (was 1)
- ✅ 3 new tests in `tests/test_evals_coverage.py` PASS
- ✅ `mypy --strict tests/test_evals_coverage.py` clean
- ✅ `ruff check tests/test_evals_coverage.py` clean (auto-fix applied during Task 2)
- ✅ Full suite: 637 passed, 5 skipped, 1 xfailed (was 633 / 5 / 2 — exactly +4 newly green)
- ✅ No regressions across Phases 1-11
- ✅ No file deletions in either commit

## Self-Check: PASSED

- ✅ `evals/expected/evaluate-01.json` exists
- ✅ `evals/expected/evaluate-02.json` exists
- ✅ `evals/expected/evaluate-03.json` exists
- ✅ `evals/expected/compare-01.json` exists
- ✅ `evals/expected/compare-02.json` exists
- ✅ `evals/expected/compare-03.json` exists
- ✅ `evals/expected/refinance-01.json` exists
- ✅ `evals/expected/refinance-02.json` exists
- ✅ `evals/expected/refinance-03.json` exists
- ✅ `evals/expected/affordability-01.json` exists
- ✅ `evals/expected/affordability-02.json` exists
- ✅ `evals/expected/affordability-03.json` exists
- ✅ `evals/expected/stress-01.json` exists
- ✅ `evals/expected/stress-02.json` exists
- ✅ `evals/expected/stress-03.json` exists
- ✅ `evals/expected/amortize-01.json` exists
- ✅ `evals/expected/amortize-02.json` exists
- ✅ `evals/expected/amortize-03.json` exists
- ✅ `evals/expected/arm-01.json` exists
- ✅ `evals/expected/arm-02.json` exists
- ✅ `evals/expected/arm-03.json` exists
- ✅ `evals/expected/live-rate-injection-01.json` exists
- ✅ `tests/test_evals_coverage.py` exists
- ✅ Commit `9e373ca` exists in git log (Task 1)
- ✅ Commit `79c3fe6` exists in git log (Task 2)
- ✅ Worktree base unchanged: `64a04cd4808e2e77664a6642b6a998bfc6f757f0`

## TDD Gate Compliance

Plan 12-06 follows the project's xfail → live flip discipline:

- ✅ **RED (Wave-0 stubs, Plan 12-00):** `tests/test_evals_runner.py::test_every_prompt_has_paired_oracle` shipped as `@pytest.mark.xfail(strict=True)` — deterministic acceptance contract pre-existed
- ✅ **GREEN (this plan, Task 2):** authoring the 22 oracles in Task 1 made the xfail body's loop pass; Task 2 removed the decorator (single-commit flip — no separate `test(...)` commit because the test assertions are unchanged)
- ➖ **REFACTOR:** none — no implementation iteration was needed

The new `tests/test_evals_coverage.py` adds 3 verification-layer assertions that were green on first run because the underlying prompt/oracle contracts shipped in Plans 12-05 + 12-06 are internally consistent. No separate RED commit was required for these new tests because they verify already-shipped contracts (not new feature behavior). The plan-level RED gate (Wave-0 xfail) is closed; this plan is the GREEN ship for EVAL-02.

## Hand-Off to Plan 12-07

Plan 12-07 (CI wiring) now has:
- A green eval harness (`python -m evals.runner` exits 0 with rate=1.0)
- A locked SC-4 gate threshold (0.95) — invoke via `--gate 0.95` flag (default)
- A pinned 13/0/9 distribution — any drift trips `test_runner_gate_passes_on_v1_set`
- 22 prompt + 22 oracle files in place — ready for replay-stub mode in CI

The remaining CI integration work in Plan 12-07 is:
- Add `uv run python -m evals.runner` step to `.github/workflows/ci.yml`
- Decide on JSON report archival (currently stdout)
- Optionally split a `evals-nightly.yml` workflow for live-mode runs (deferred per CONTEXT.md "Claude's Discretion")

After Plan 12-07, Phase 12 closes end-to-end and v1.0 milestone unlocks.
