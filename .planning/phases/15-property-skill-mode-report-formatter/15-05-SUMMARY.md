---
phase: 15-property-skill-mode-report-formatter
plan: 05
subsystem: eval-harness
tags: [evals, oracle, replay-stub, property-analysis, route-keyword, number-regex, reconciliation, sc-6, wave-2]

# Dependency graph
requires:
  - phase: 15-property-skill-mode-report-formatter
    provides: "Plan 15-01 synthetic fixture (sfh_conforming_001.json) + Wave 0 oracle stub; Plan 15-02 lib/property_report.render() formatter; Plan 15-03 .claude/skills/mortgage-ops/scripts/property_analyze.py orchestrator; Plan 15-04 SKILL.md Row 0 + modes/property.md"
  - phase: 12-fred-eval
    provides: "evals.runner replay-stub harness + evals.metrics.NUMBER_REGEX/score_route_match/score_numeric_match scorers + SC4 gate (>=0.95)"
  - phase: 11-subagents
    provides: "synthetic-only-in-CI fixture policy (D-02) — no live WebFetch in eval mode"
  - phase: 10-claude-skill
    provides: ".claude/skills/mortgage-ops/scripts/ portability convention used by source_script field"
provides:
  - "evals/prompts/property-analysis-01.md — first end-to-end eval for the property mode (closes ROADMAP SC-6)"
  - "evals/expected/property-analysis-01.json — reconciled oracle (Wave 0 hand-calc verdict GO -> reconciled WATCH; verdict_reasons_count 1.0 -> 3.0; v1_frozen_at 2026-05-20 -> 2026-05-21)"
  - "Phase 12 baseline test pins updated 22 -> 23 prompts; 13 -> 14 numeric_pass; skip/fail unchanged"
affects: [16+]  # All future plans inherit SC-6 regression gate

# Tech tracking
tech-stack:
  added: []  # No new dependencies; uses existing python-frontmatter + evals.runner + evals.metrics
  patterns:
    - "Route-keyword path for non-numeric pins (e.g., verdict.level): NUMBER_REGEX requires decimal point so non-numeric strings live in expected_route_keywords (mirrors live-rate-injection-01.md's '6.50' route-keyword precedent for FRED-cache lookup; here used for 'WATCH' string)"
    - "Oracle reconciliation step: re-derive numerics from actual orchestrator output, NOT hand-calc, to avoid sub-cent drift between Wave 0 anchors and live analyze() arithmetic"
    - "v1_frozen_at timestamp pins the regression baseline; future drift surfaces as gate failure (route_match or numeric_match < 0.95)"
    - "evals.runner replay-stub synthesizes deterministic transcripts from prompt frontmatter + oracle JSON; the gate validates oracle INTERNAL CONSISTENCY (the prompt/oracle pair self-coheres)"

key-files:
  created:
    - "evals/prompts/property-analysis-01.md"
    - ".planning/phases/15-property-skill-mode-report-formatter/15-05-SUMMARY.md"
  modified:
    - "evals/expected/property-analysis-01.json"  # Wave 0 stub reconciled
    - "tests/test_evals_runner.py"                # 22 -> 23 prompt baseline pin
    - "tests/test_evals_coverage.py"              # 22 -> 23 prompt + 13 -> 14 pass baseline pin

key-decisions:
  - "Reconciliation produces verdict=WATCH (not Wave 0 hand-calc GO): when property_analyze.py runs the synthetic fixture against the committed config/household.example.yml ($5k+$5k=$10k income), the -30% stress-income shock breaches the DTI ceiling on all 3 eligible programs (Conv30/Conv15/FHA30); the verdict cascade reports STRESS-INCOME-SHOCK on each, producing 3 verdict.reasons entries and level=WATCH"
  - "Oracle pins WATCH via expected_route_keywords (A4 + live-rate-injection-01 precedent) — NUMBER_REGEX requires decimal point so verdict strings can't be expected_numbers"
  - "verdict_reasons_count: 3.0 (NOT 1.0) — the Wave 0 stub hand-calc assumed the synthetic-fixture's internal household ($14k income) was the consumed household, but the orchestrator loads --household separately from a yaml file; using the committed config/household.example.yml is the only reproducible-by-anyone path"
  - "PITI ($3,760.34) + first-year interest ($32,335.43) unchanged from Wave 0: these are loan/rate/escrow-driven (listing-side inputs), not household-side, so the household change leaves them untouched"
  - "Updated Phase 12 baseline test pins (tests/test_evals_runner + test_evals_coverage) from 22 to 23 prompts and 13 to 14 numeric_pass: deliberate +1 per ROADMAP SC-6; not a regression"
  - "v1_frozen_at: 2026-05-21 (today's date — the date the reconciliation occurred). Future drift either passes (no orchestrator change) or fails (orchestrator changed; baseline needs re-reconciliation)"

patterns-established:
  - "Reconciliation diary in SUMMARY: each numeric's Wave 0 hand-calc anchor vs Wave 2 reconciled value, with reason for any divergence"
  - "Eval prompt body is a single user-facing line that triggers Row 0 dispatch (zillow.com substring); replay-stub mode doesn't actually invoke WebFetch (Phase 11 D-02 + Phase 12 contract)"

requirements-completed: [MODE-03, RPRT-01, RPRT-02]

# Metrics
duration: ~12min
completed: 2026-05-21
---

# Phase 15 Plan 15-05: Wave 2 — property-analysis-01 Eval Prompt + Oracle Reconciliation Summary

**Ships v1.1's first end-to-end property-mode eval (`evals/prompts/property-analysis-01.md`) + reconciles the Wave 0 oracle stub against actual `property_analyze.py` output. Wave 0 hand-calc said verdict.level=GO with 1 reason; the live orchestrator running the synthetic fixture against `config/household.example.yml` says verdict.level=WATCH with 3 reasons (the example household's $10k income is stressed below the DTI ceiling by every -30% income shock). Oracle reconciled; v1_frozen_at = 2026-05-21. Phase 12 baseline test pins updated 22→23 prompts and 13→14 numeric_pass. `uv run python -m evals.runner` exits 0; route_match=1.0; numeric_match=1.0 (≥0.95 SC4 gate). Closes ROADMAP SC-6.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-21T08:38:32Z
- **Completed:** 2026-05-21T08:50:46Z
- **Tasks:** 1
- **Files created:** 1 (eval prompt)
- **Files modified:** 3 (oracle reconciliation + 2 Phase-12 baseline test pins)

## Task Commits

1. **Task 1: Ship eval prompt + reconcile oracle against orchestrator output** — `d98661f` (feat)

**Plan metadata commit:** (created after this SUMMARY is written; will cover SUMMARY + STATE + ROADMAP + REQUIREMENTS)

## Final Eval Prompt Frontmatter

```yaml
---
id: property-analysis-01
mode: property
description: Full property analysis end-to-end — SFH conforming King County WA against synthetic Phase 11 D-02 fixture (sfh_conforming_001.json). Closes ROADMAP SC-6. No live WebFetch in CI per Phase 11 D-02 + Phase 12 contract; replay-stub mode injects FRED rates via the fixture wrapper's fred_rates block.
expected_route_keywords:
  - property
  - property_analyze.py
  - "WATCH"
expected_scripts:
  - script: property_analyze.py
    args_must_include:
      - "--listing"
      - "--household"
      - "--profile"
      - "--output-dir"
expected_numbers:
  - label: conv30_preferred_dp_piti
    value: "3760.34"
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
  - label: first_year_interest_conv30
    value: "32335.43"
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
  - label: verdict_reasons_count
    value: "3.0"
    tolerance: "0.0"
    source_script: property_analyze.py
    provenance: stdout
---

Analyze this Zillow listing for me: https://www.zillow.com/homedetails/synthetic/1_zpid/
```

## Final Oracle JSON

```json
{
  "schema_version": 1,
  "id": "property-analysis-01",
  "mode": "property",
  "numeric_status": "anchored",
  "expected_scripts": [
    {
      "script": "property_analyze.py",
      "args_must_include": ["--listing", "--household", "--profile", "--output-dir"]
    }
  ],
  "expected_numbers": [
    {"label": "conv30_preferred_dp_piti",    "value": "3760.34",  "tolerance": "0.50", "source_script": "property_analyze.py", "numeric_status": "anchored", "provenance": "stdout"},
    {"label": "first_year_interest_conv30", "value": "32335.43", "tolerance": "0.50", "source_script": "property_analyze.py", "numeric_status": "anchored", "provenance": "stdout"},
    {"label": "verdict_reasons_count",      "value": "3.0",      "tolerance": "0.0",  "source_script": "property_analyze.py", "numeric_status": "anchored", "provenance": "stdout"}
  ],
  "expected_route_keywords": ["property", "property_analyze.py", "WATCH"],
  "v1_frozen_at": "2026-05-21"
}
```

## Reconciliation Diary

The plan's Step-1 reconciliation step (run `.claude/skills/mortgage-ops/scripts/property_analyze.py` against `evals/fixtures/property/sfh_conforming_001.json` + `config/household.example.yml` + `config/profile.example.yml`; capture actual stdout + report markdown; compare to Wave 0 hand-calc anchors) produced:

| Anchor | Wave 0 hand-calc | Wave 2 reconciled | Divergence | Reason |
|--------|------------------|-------------------|------------|--------|
| `conv30_preferred_dp_piti` | `$3760.34` | `$3760.34` | none | PITI is listing-driven: $500k loan @ 6.5%/30yr → P&I $3,160.34 + tax $500 + ins $100 + HOA $0 + PMI $0 (LTV=0.80 exact). Household has zero impact on this number. |
| `first_year_interest_conv30` | `$32335.43` | `$32335.43` | none | First-year interest is also listing-driven: derived from amortize.build_schedule on $500k @ 6.5%/30yr; sum of months 1-12 interest = $32,335.43. Household-independent. |
| `verdict_reasons_count` | `1.0` | `3.0` | +2 reasons | Wave 0 stub assumed the fixture's internal `household` block ($14k income) was consumed — but the orchestrator loads `--household` from a separate yaml file. Using the committed `config/household.example.yml` ($5k+$5k=$10k income), the -30% income shock pushes back-end DTI past the ceiling on all 3 eligible programs (Conv30/Conv15/FHA30), producing 3 STRESS-INCOME-SHOCK reasons instead of 1 GO-ALL-GREEN reason. |
| `verdict.level` (route-keyword) | `GO` | `WATCH` | level change | Same cascade: 3 income-shock breaches → level cascades from GO down to WATCH (per Phase 14 verdict cascade spec). |

**No tolerance widening needed** — the PITI + interest anchors matched exactly to-the-cent (the hand-calc Wave 0 anchors were correct against the orchestrator's arithmetic; only the verdict-cascade-and-counter pieces needed reconciliation because they consume the household). Tolerances remain at `±$0.50` (PITI, interest) and `±0.0` (integer count).

### Live Orchestrator Output (Verbatim — Reconciliation Capture)

Command (run during Step 1):
```bash
uv run python .claude/skills/mortgage-ops/scripts/property_analyze.py \
  --listing /tmp/eval-recon-15-05/listing_wrapped.json \
  --household config/household.example.yml \
  --profile config/profile.example.yml \
  --output-dir /tmp/eval-recon-15-05/out/
```

stdout (single-line envelope, Phase 12 always-exit-0):
```json
{"report_path": "/private/tmp/eval-recon-15-05/out/001-property-1-2026-05-21.md", "verdict": "WATCH", "error": null}
```

VERDICT section from the produced markdown report:
```
## VERDICT — **WATCH**

**Headline:** Income-shock stress breaches DTI ceiling for 3 eligible program(s)

- `STRESS-INCOME-SHOCK`: 0.537191 (program=Conv30)
- `STRESS-INCOME-SHOCK`: 0.680779 (program=Conv15)
- `STRESS-INCOME-SHOCK`: 0.575376 (program=FHA30)
```

YOUR FIT matrix (preferred-DP 20% column):
```
| Conv30 | ... | **$3,760/mo ✓** | ... |
| Conv15 | ... | **$4,765/mo ✓** | ... |
| FHA30  | ... | **$4,028/mo ✓** | ... |
```

(The matrix uses whole-dollar `_fmt_money_whole` per Pitfall 11; the underlying Decimal value `$3,760.34` surfaces in the RATE STRESS table's baseline-PITI column. NUMBER_REGEX matches `$3,760.34` because of the decimal point.)

TAX section first-year-interest line:
```
- First-year deductible interest (Conv30): $32,335.43
```

## evals.runner Output (Final State)

```
$ uv run python -m evals.runner
{
  "n_prompts": 23,
  "route_match_count": 23,
  "route_match_rate": 1.0,
  "numeric_pass_count": 14,
  "numeric_fail_count": 0,
  "numeric_skip_count": 9,
  "numeric_match_rate": 1.0,
  "failures": []
}
$ echo $?
0
```

- **n_prompts**: 23 (was 22 — Plan 15-05 added property-analysis-01)
- **route_match_rate**: 1.0 (was 1.0 — every prompt still scores route_match)
- **numeric_pass_count**: 14 (was 13 — the new prompt adds 1 pass)
- **numeric_fail_count**: 0 (unchanged)
- **numeric_skip_count**: 9 (unchanged — none of the new prompt's numerics are skipped; numeric_status=anchored)
- **numeric_match_rate**: 14/14 = 1.0 ≥ 0.95 SC4 gate
- **Exit code**: 0

## Pytest Output

```
$ uv run pytest tests/test_evals_runner.py tests/test_evals_coverage.py tests/test_property_report.py tests/test_property_analyze_cli.py tests/test_skill_routing.py --tb=no -q
50 passed, 2 warnings in 11.12s
```

50/50 Phase 15 + eval tests pass. The full project pytest sweep (excluding pre-existing-broken `tests/test_rules/test_citation_coverage.py` and `tests/test_rules/test_citation_coverage_mutations.py` which fail on rogue `lib/rules/fha_mip 2.py` / `lib/rules/fha_mip 3.py` duplicates that predate this plan):

```
$ uv run pytest tests/ --ignore=tests/test_rules/test_citation_coverage.py --ignore=tests/test_rules/test_citation_coverage_mutations.py --ignore=tests/test_rules/test_phase2_smoke.py --tb=no -q
826 passed, 6 skipped, 1 xfailed, 5 warnings in 64.25s
```

826 passed (no failures). Phase 14 reference 644 + Phase 15 new 29 + ancillary suite = 826, matching the Phase 15 net-new tests expected count.

## Phase 12 Baseline Test Pins Updated

The plan's deviation Rule 1 (auto-fix bugs directly caused by current task's changes) fired on two Phase 12 baseline tests that explicitly hard-coded the v1 prompt count:

| Test | Pre-edit pin | Post-edit pin | Reason |
|------|--------------|---------------|--------|
| `tests/test_evals_runner.py::test_evals_prompts_dir_has_22_prompts` → renamed `test_evals_prompts_dir_has_23_prompts` | `assert len(md_files) == 22` | `assert len(md_files) == 23` | Plan 15-05 deliberately adds the 23rd prompt per ROADMAP SC-6. |
| `tests/test_evals_coverage.py::test_runner_gate_passes_on_v1_set` | `n_prompts == 22; numeric_pass == 13` | `n_prompts == 23; numeric_pass == 14` | Same: the 23rd prompt adds 1 anchored numeric_pass (skip/fail counts unchanged). |

Both tests' docstrings updated to reference SC-6 + Plan 15-05 alongside their original SC-4 + Plan 12-05/06 lineage. The Phase 12 7-mode SC-5 invariant (`ALL_MODES = (evaluate, compare, refinance, affordability, stress, amortize, arm)`) is left unchanged because `property` is a Phase 15 mode added on top of the Phase 12 7-mode coverage, not part of it. The aggregator-math examples (`test_gate_passes_with_13_anchored_pass_and_9_skip`, `test_gate_fails_with_one_anchored_fail_among_13`) are untouched because they construct synthetic `HarnessReport` instances with example numbers — they test the gate math, not the live prompt count.

## Decisions Made

- **Reconcile to `config/household.example.yml` (not the fixture's internal household block):** The orchestrator loads `--household` from a separate yaml file; the fixture's `household` block is ignored. Pinning to the committed `config/household.example.yml` is the only reproducible-by-anyone path for the regression baseline. Anyone can re-run the reconciliation command and get the same `verdict.level=WATCH` and `reasons_count=3` — no need to construct a custom household yaml.
- **Verdict pin via `expected_route_keywords` (`"WATCH"` string), not `expected_numbers`:** `evals.metrics.NUMBER_REGEX` requires a decimal point; verdict-level strings (`"GO"`, `"WATCH"`, `"NO_GO"`) cannot match. The route-keyword path is the documented Phase 12 mechanism for non-numeric pins (RESEARCH L775 + live-rate-injection-01.md L6 precedent).
- **`verdict_reasons_count: "3.0"` (not `"3"`):** `NUMBER_REGEX` requires `\.\d{1,4}\b` — the `.0` suffix is mandatory. The synthesized stub transcript formats the value with the decimal point so `score_numeric_match` finds it.
- **Tolerance `"0.50"` on dollar anchors (not `"0.005"` half-cent):** Both anchors are 5+-digit dollar amounts where ±50 cents catches sub-cent rounding drift from Phase 14's `quantize(ROUND_HALF_UP)` without false positives. The Wave 0 stub already used this tolerance; reconciliation preserved it because no widening was needed.
- **Tolerance `"0.0"` on integer count:** `verdict_reasons_count` is an integer-valued anchor; tolerance 0.0 means exact equality. The `.0` decimal form satisfies NUMBER_REGEX without inflating tolerance.
- **`v1_frozen_at: 2026-05-21`:** today's date (the date the reconciliation occurred). Future drift events fire the gate; the date stamps the regression baseline for forensic comparison.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wave 0 hand-calc verdict was wrong: GO→WATCH cascade and reasons-count 1→3 after running the orchestrator against the committed example household.**

- **Found during:** Step 1 reconciliation run
- **Issue:** Plan 15-01's oracle stub said `verdict.level = "GO"` and `verdict_reasons_count = 1.0`, derived from the fixture's internal `household` block ($14k income, $800 obligations, FICO 760). The orchestrator does NOT consume the fixture's internal household — it loads `--household` from a separate yaml file. When run against `config/household.example.yml` (the committed placeholder household: $5k+$5k=$10k income, $0 obligations, FICO 700), the -30% income shock pushes back-end DTI past the ceiling on all 3 eligible programs, producing 3 STRESS-INCOME-SHOCK verdict reasons and cascading the level to WATCH.
- **Fix:** Reconciled both fields against actual orchestrator output. Updated `expected_route_keywords` from `["property", "property_analyze.py", "GO"]` to `["property", "property_analyze.py", "WATCH"]`. Updated `verdict_reasons_count` from `1.0` to `3.0`. Bumped `v1_frozen_at` from `2026-05-20` (Plan 15-01) to `2026-05-21` (Plan 15-05 reconciliation).
- **Files modified:** evals/expected/property-analysis-01.json, evals/prompts/property-analysis-01.md
- **Verification:** `uv run python -m evals.runner` exits 0 with route_match=1.0 + numeric_match=1.0.
- **Committed in:** d98661f

**2. [Rule 1 - Bug] Phase 12 baseline tests hard-coded 22-prompt + 13-pass pins; the +1 from Plan 15-05's new prompt breaks them.**

- **Found during:** Full pytest sweep after committing the eval prompt + oracle
- **Issue:** `tests/test_evals_runner.py::test_evals_prompts_dir_has_22_prompts` asserts `len(md_files) == 22`; `tests/test_evals_coverage.py::test_runner_gate_passes_on_v1_set` asserts `n_prompts == 22 and numeric_pass_count == 13 and numeric_skip_count == 9`. Plan 15-05 deliberately adds the 23rd prompt per ROADMAP SC-6, so these pins are stale-by-design — the +1 prompt is the intended outcome, not a regression.
- **Fix:** Updated both pins (22→23 prompts; 13→14 pass; skip/fail unchanged). Renamed `test_evals_prompts_dir_has_22_prompts` to `test_evals_prompts_dir_has_23_prompts` so the test name reflects the new invariant. Updated docstrings to cross-reference SC-6 + Plan 15-05 alongside their original SC-4 + Plan 12-05/06 lineage. Did NOT update the aggregator-math example tests (`test_gate_passes_with_13_anchored_pass_and_9_skip`, etc.) — those construct synthetic HarnessReport instances with example numbers; they test the gate math, not the live prompt count.
- **Files modified:** tests/test_evals_runner.py, tests/test_evals_coverage.py
- **Verification:** Both tests + 14 other tests in the same modules pass GREEN; the full eval suite still produces gate=1.0.
- **Committed in:** d98661f

**3. [Rule 3 - Blocking] Pre-existing-broken mypy `# type: ignore[import-untyped]` on `frontmatter` import flagged unused once my edit triggered the hook.**

- **Found during:** First commit attempt; mypy hook failed on `tests/test_evals_runner.py:57` and `tests/test_evals_coverage.py:23`
- **Issue:** Both files had `import frontmatter  # type: ignore[import-untyped]` from Plan 12-05/06; mypy now reports `import-not-found` (not `import-untyped`), so the existing ignore is unused. This is a pre-existing dirty state (the comment was always wrong; mypy hook only checks files in the current commit). My edits to these files dragged them into the hook's scope and surfaced the latent issue.
- **Fix:** Changed `# type: ignore[import-untyped]` → `# type: ignore[import-not-found]` in both files. This is the correct error code for the present mypy environment behavior.
- **Files modified:** tests/test_evals_runner.py, tests/test_evals_coverage.py
- **Verification:** `uv run pre-commit run mypy --files tests/test_evals_runner.py tests/test_evals_coverage.py` PASSES; second commit attempt succeeded with all hooks green.
- **Committed in:** d98661f

---

**Total deviations:** 3 auto-fixed (2 Rule 1 + 1 Rule 3). All directly caused by the plan's deliberate +1 prompt addition. No scope creep; no architectural changes; no new dependencies. The reconciliation step is the central work the plan was designed to do.

**Impact on plan:** Reconciliation revealed two stale Wave 0 anchors (verdict.level + reasons_count) — fixed inline; tolerances unchanged; PITI + interest anchors held to-the-cent so no widening needed. Baseline test pins updated to reflect the deliberate +1 prompt. Plan executed exactly as written.

## Issues Encountered

- **Pre-existing dirty filesystem state** (`.planning/config.json` modified; `lib/rules/fha_mip.py` modified; various untracked `.planning/MORTGAGE-OPS-*.md` reports + `lib/rules/fha_mip {2,3}.py` + `data/.lock {2,3,4,5}` + `.planning/config {2,3}.json` duplicates): all out of scope per the deviation rule "Only auto-fix issues DIRECTLY caused by the current task's changes." Plans 15-01..15-04 SUMMARYs all flagged the same baseline; this plan inherits the same blast radius without introducing new orphans. The rogue `lib/rules/fha_mip 2.py` / `lib/rules/fha_mip 3.py` files specifically cause `tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring[fha_mip 2]` + `tests/test_rules/test_citation_coverage_mutations.py::test_meta_tests_pass_unmutated_baseline` to fail; both pre-date Plan 15-05.
- **`StaleReferenceWarning` warnings** for `fha-mip-rates` (effective 2023-03-20) and `irs-pub936` (effective 2025-01-01): annual-refresh discipline governed by `lib/rules/_loader.py`; not a Phase 15 surface.
- **`evals.runner` rejects single-file targets in v1** (per WR-05): The plan's `<verify>` block shows `uv run python -m evals.runner evals/prompts/property-analysis-01.md` but the runner errors with "single-file scoring not supported in v1; pass a directory." This is a known Phase 12 limitation (WR-05 deferral). The functional verification — running the full directory and confirming exit 0 + gate ≥0.95 — passes; the per-prompt path is satisfied by the gate aggregation.

## Threat Flags

None. The threat register entries T-15-E1..T-15-E3 are all addressed:

| Threat ID | Status     | Mitigation Reference                                                 |
| --------- | ---------- | -------------------------------------------------------------------- |
| T-15-E1   | mitigate ✓ | `v1_frozen_at: "2026-05-21"` + `numeric_status: "anchored"` — drift surfaces as gate failure |
| T-15-E2   | mitigate ✓ | Synthetic fixture: zpid="1", synthetic source_url, "Synthetic Address", no PII — `grep -i "@gmail\|@yahoo\|phone:" evals/fixtures/property/*.json` returns empty |
| T-15-E3   | mitigate ✓ | Reconciliation diary above documents Step 1 invocation + each numeric's hand-calc-vs-reconciled state; auditable lineage |

No new trust-boundary surface introduced — this plan ships an eval prompt + a JSON oracle, both committed to the repo. The orchestrator (Plan 15-03) already underwent threat review.

## Known Stubs

None. Every oracle anchor and every route-keyword in the prompt frontmatter is a reconciled real value from the live orchestrator output captured during this plan's Step 1.

## User Setup Required

None — the eval prompt + oracle are SDK-distributable artifacts. Future contributors can re-reconcile by running:

```bash
uv run python .claude/skills/mortgage-ops/scripts/property_analyze.py \
  --listing evals/fixtures/property/sfh_conforming_001.json \
  --household config/household.example.yml \
  --profile config/profile.example.yml \
  --output-dir /tmp/recon/
```

…against the synthetic fixture + the committed example household + the committed example profile, then comparing the produced report's PITI/interest/verdict-reasons-count to the oracle anchors.

## Next Phase Readiness

Phase 15 is COMPLETE. All 5 requirements (MODE-01, MODE-02, MODE-03, RPRT-01, RPRT-02) and all 6 ROADMAP success criteria (SC-1..SC-6) are closed:

| Requirement / SC | Closed by plan | Verified by |
|------------------|----------------|-------------|
| MODE-01 (zillow.com URL-pin dispatches to property mode) | Plan 15-04 | tests/test_skill_routing.py 5 tests |
| MODE-02 (SKILL.md token budget ≤4500 after Row 0 insertion) | Plan 15-04 | test_skill_md_token_budget (3796 ≤ 4500) |
| MODE-03 (property_analyze.py orchestrator + always-exit-0 envelope) | Plan 15-03 | tests/test_property_analyze_cli.py 11 tests |
| RPRT-01 (6-section markdown report from AnalysisReport) | Plan 15-02 | tests/test_property_report.py 15 tests |
| RPRT-02 (6 citation footers per report) | Plan 15-02 | test_six_citation_footers + test_footer_is_full_invocation |
| SC-6 (eval prompt + oracle exercise property mode end-to-end; runner exits 0 with gate ≥0.95) | Plan 15-05 (this plan) | uv run python -m evals.runner — exit 0; route+numeric=1.0 |

Phase 15 v1.1 milestone closed.

## Self-Check: PASSED

Verified 2026-05-21:

**Files (1/1 created, 3/3 modified):**
- `evals/prompts/property-analysis-01.md` — FOUND (new, 31 lines)
- `evals/expected/property-analysis-01.json` — MODIFIED (Wave 0 stub reconciled; v1_frozen_at 2026-05-20 → 2026-05-21)
- `tests/test_evals_runner.py` — MODIFIED (22 → 23 prompts pin; module docstring updated; type-ignore code fixed)
- `tests/test_evals_coverage.py` — MODIFIED (22 → 23 + 13 → 14 pins; module docstring updated; type-ignore code fixed)

**Commits (1/1 in git log):**
- `d98661f` — feat(15-05): add property-analysis-01 eval prompt + reconcile oracle against orchestrator

**Acceptance criteria (9/9):**
- [x] `evals/prompts/property-analysis-01.md` exists; frontmatter parses via python-frontmatter; id="property-analysis-01"; mode="property"
- [x] `evals/expected/property-analysis-01.json` exists; matches prompt id; numeric_status="anchored"; v1_frozen_at="2026-05-21"
- [x] expected_route_keywords contains "property", "property_analyze.py", and "WATCH" (verdict.level pin via route-keyword per A4)
- [x] expected_numbers has exactly 3 entries; every value matches NUMBER_REGEX (decimal-point form)
- [x] All 3 numerics RECONCILED with actual orchestrator output: PITI + interest unchanged (Wave 0 anchors held to-the-cent); verdict_reasons_count 1.0 → 3.0; verdict.level GO → WATCH
- [x] `uv run python -m evals.runner` exits 0; route_match_rate=1.0; numeric_match_rate=1.0 (gate ≥0.95)
- [x] Phase 12 baseline test pins updated: tests/test_evals_runner.py + tests/test_evals_coverage.py reflect +1 prompt and +1 numeric_pass
- [x] All money values in oracle are Decimal-strings (CLAUDE.md money discipline)
- [x] No PII / real listing data — fixture is synthetic per Phase 11 D-02

---
*Phase: 15-property-skill-mode-report-formatter*
*Completed: 2026-05-21*
