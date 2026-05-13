---
phase: 12-fred-eval
plan: 05
subsystem: evals
tags: [phase-12, wave-5, eval-prompts, 22-prompts, mode-coverage, fred-fixture-cache, d-12-sc1-01, d-12-sc4-01]
requirements: [EVAL-01]
dependency-graph:
  requires:
    - evals/runner.py (Plan 12-04 — schema runner reads)
    - evals/metrics.py (Plan 12-04 — NumericScore + scorers)
    - tests/test_evals_runner.py (Plan 12-00 + 12-04 — Wave-0 xfail stubs)
    - tests/fixtures/fred/README.md (Plan 12-00 — Wave-0 README seam)
    - python-frontmatter dev-dep (Plan 12-00)
  provides:
    - evals/prompts/*.md (22 prompt markdown files; 13 anchored + 9 TBD-skip)
    - evals/prompts/live-rate-injection-01.md (SC-1 closure eval — anchored to fixture cache)
    - tests/fixtures/fred/MORTGAGE30US-2026-05-13.json (rate=6.50 — anchored eval target)
    - tests/fixtures/fred/MORTGAGE15US-2026-05-13.json (rate=5.85 — companion fixture)
  affects:
    - Plan 12-06 (oracles) — needs 22 paired evals/expected/{id}.json files; this plan provides the 1:1 stem source
    - Plan 12-07 (CI gate) — eval runner now has the full 22-prompt input set; replay-stub mode can run end-to-end once oracles ship
tech-stack:
  added: []
  patterns:
    - YAML frontmatter schema for eval prompts (python-frontmatter parseable; id/mode/description/expected_route_keywords/expected_scripts/expected_numbers)
    - numeric_status=skip + defer_until_phase pointer for TBD prompts (D-12-SC4-01)
    - provenance=static exemption for fixture-cache-anchored numbers (D-12-SC3-01)
    - synthetic FRED cache fixtures (schema_version=1, redacted api_key=***) for deterministic CI
key-files:
  created:
    - evals/prompts/evaluate-01.md (Wikipedia oracle; $200k @ 6.5%/30yr → $1264.14)
    - evals/prompts/evaluate-02.md (computed; $400k @ 6.5%/30yr → $2528.27)
    - evals/prompts/evaluate-03.md (TBD — APR Reg Z worked example pending)
    - evals/prompts/compare-01.md (computed pair; $2528.27 vs $1797.66)
    - evals/prompts/compare-02.md (CFPB LE vs Wikipedia; $761.78 vs $1264.14)
    - evals/prompts/compare-03.md (TBD — 3-way ranked-NPV pending)
    - evals/prompts/refinance-01.md (Phase 6 positive_npv; NPV=$60705.48)
    - evals/prompts/refinance-02.md (TBD — cash-out pending)
    - evals/prompts/refinance-03.md (TBD — negative-NPV + discount-rate sweep pending)
    - evals/prompts/affordability-01.md (Phase 4 forward conforming; $2528.27)
    - evals/prompts/affordability-02.md (Phase 4 reverse 43% DTI; max_loan=$646322.54)
    - evals/prompts/affordability-03.md (TBD — VA residual income blocker pending)
    - evals/prompts/stress-01.md (Phase 8 rate-shock $400k/30yr; row at 6.5%=$2528.27)
    - evals/prompts/stress-02.md (TBD — 50-scenario subagent dispatch pending)
    - evals/prompts/stress-03.md (TBD — ARM-reset 3-path total-interest pending)
    - evals/prompts/amortize-01.md (Wikipedia; $1264.14)
    - evals/prompts/amortize-02.md (computed 15yr; $1797.66)
    - evals/prompts/amortize-03.md (CFPB LE; $761.78)
    - evals/prompts/arm-01.md (Phase 8 engine-actual 5/1 ARM $400k/6.0%; $2398.20 initial)
    - evals/prompts/arm-02.md (TBD — full-horizon 2/2/5 caps pending)
    - evals/prompts/arm-03.md (TBD — 5/6 SOFR pending)
    - evals/prompts/live-rate-injection-01.md (SC-1 closure; pins to MORTGAGE30US=6.50)
    - tests/fixtures/fred/MORTGAGE30US-2026-05-13.json (rate=6.50)
    - tests/fixtures/fred/MORTGAGE15US-2026-05-13.json (rate=5.85)
  modified:
    - tests/test_evals_runner.py (flipped 2 of 3 remaining xfails: 22-count + per-mode coverage)
    - tests/fixtures/fred/README.md (filename date alignment: 2026-05-10 → 2026-05-13)
decisions:
  - "Fixture cache filenames pinned to 2026-05-13 (current date), not 2026-05-10 (plan body date) per LOCKED objective; this aligns the fixture-shipping date with when prompts go live and avoids reader-confusion. Test correctness is unaffected because tests pin to the fixture *path*, not the date string."
  - "live-rate-injection-01.md uses mode=evaluate (not a new 'live-rate' mode); SKILL.md's existing evaluate routing absorbs current-rate questions. This keeps the 7-mode coverage clean and avoids a one-off mode in the SC-5 mode coverage assertion."
  - "TBD prompts use defer_until_phase: '13.0' (string, not float) — YAML reads cleanly via python-frontmatter regardless, but strings preserve trailing zeros and avoid float-vs-Decimal silent coercion at downstream consumers."
  - "amortize-03 uses CFPB LE oracle (3rd of 4 pinned amortize anchors); the 4th oracle ($400k @ 6.5%/30yr = $2528.27) lives in evaluate-02 and stress-01. The 3 amortize prompts therefore cover Wikipedia + computed-15yr + CFPB LE; no anchor is wasted."
  - "stress-01 baseline rate flipped from plan body 6.5% to 6.0% to match Phase 8 fixture (rate_shock_400k_30yr_grid_5_rates.json baseline=0.060000); the prompt sweeps 5 rates and pins the 6.5% row at $2528.27 — the row-index oracle is more rigorous than the baseline-only check the plan body suggested."
metrics:
  duration-seconds: 480
  duration-minutes: 8.0
  task-count: 2
  file-count: 25
  commit-count: 2
  completed: 2026-05-13T19:00:00Z
---

# Phase 12 Plan 05: 22-prompt v1 eval set + FRED fixture caches Summary

**One-liner:** Shipped 22 eval prompts (13 anchored to existing Phase 3/4/6/8 oracles + 9 TBD with `numeric_status: skip` + `defer_until_phase: "13.0"`) plus 2 FRED fixture caches (MORTGAGE30US=6.50, MORTGAGE15US=5.85) to anchor SC-1 closure deterministically, closing EVAL-01 + SC-5 at the prompt layer and flipping 8 xfails (1 prompt-count + 7 per-mode parametrize cases).

## What Shipped

### 22 prompt files in `evals/prompts/`

Distribution (PINNED by D-12-SC4-01 math: 13 anchored / 9 skip → 100% gate pass on (13+0)):

| Mode | Anchored | TBD-skip | Total |
|------|---------:|---------:|------:|
| evaluate | 2 | 1 | 3 |
| compare | 2 | 1 | 3 |
| refinance | 1 | 2 | 3 |
| affordability | 2 | 1 | 3 |
| stress | 1 | 2 | 3 |
| amortize | 3 | 0 | 3 |
| arm | 1 | 2 | 3 |
| live-rate-injection | 1 | 0 | 1 |
| **TOTAL** | **13** | **9** | **22** |

All 7 SKILL.md modes have ≥1 prompt (SC-5 closure). `evaluate` carries 4 prompts in the count (3 mode-coverage + 1 live-rate-injection) because `live-rate-injection-01.md` reuses `mode: evaluate` — the skill's existing evaluate routing absorbs current-rate questions, so no new mode entry is needed.

### Engine-anchor map (13 anchored prompts)

Each anchored prompt pins to an existing engine-derived oracle from a prior phase:

| Prompt | Anchor | Value | Source |
|--------|--------|------:|--------|
| evaluate-01 | Wikipedia oracle | $1,264.14 | CONVENTIONS.md (Wikipedia $200k @ 6.5%/30yr) |
| evaluate-02 | Computed | $2,528.27 | CONVENTIONS.md (computed $400k @ 6.5%/30yr) |
| compare-01 | Computed pair | $2,528.27 + $1,797.66 | CONVENTIONS.md (two computed oracles) |
| compare-02 | CFPB LE + Wikipedia | $761.78 + $1,264.14 | CONVENTIONS.md (two pinned oracles) |
| refinance-01 | Phase 6 positive_npv | NPV=$60,705.48 | `tests/fixtures/refinance/positive_npv_200bps_drop_2k_costs.json` |
| affordability-01 | Phase 4 forward | $2,528.27 | computed (same as evaluate-02; PI oracle reused) |
| affordability-02 | Phase 4 reverse | $646,322.54 | `tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json` (max_loan_amount) |
| stress-01 | Phase 8 rate-shock row | $2,528.27 | `tests/fixtures/stress/rate_shock_400k_30yr_grid_5_rates.json` (row at 0.065) |
| amortize-01 | Wikipedia | $1,264.14 | CONVENTIONS.md |
| amortize-02 | Computed 15yr | $1,797.66 | CONVENTIONS.md ($200k @ 7%/15yr) |
| amortize-03 | CFPB LE | $761.78 | CONVENTIONS.md ($162k @ 3.875%/30yr) |
| arm-01 | Phase 8 engine-actual | $2,398.20 | `tests/fixtures/stress/rate_shock_400k_30yr_grid_5_rates.json` (row at 0.060 = ARM initial period at 6.0%) |
| live-rate-injection-01 | Fixture cache (D-12-SC1-01) | 6.50% | `tests/fixtures/fred/MORTGAGE30US-2026-05-13.json` (provenance=static) |

All 13 anchors are engine-derived, not hand-calculated independently — every dollar/rate traces back to either a CONVENTIONS.md pinned oracle (4 anchors) or a Phase 4/6/8 fixture JSON (8 anchors) or a Phase 12 fixture cache (1 anchor).

### 9 TBD-skip prompts (Phase-13+ oracle pointers)

| Prompt | Defer reason |
|--------|--------------|
| evaluate-03 | Reg Z worked-example APR oracle pending |
| compare-03 | 3-way ranked-NPV table fixture pending |
| refinance-02 | Cash-out refi richer fixture pending (Phase 6 has cash_out_proceeds_50k but deal terms differ) |
| refinance-03 | Negative-NPV + discount-rate sensitivity sweep pending |
| affordability-03 | VA-residual-income blocker_by citation flow fixture pending |
| stress-02 | 50-scenario transcript-fixture for stress-test-agent dispatch pending |
| stress-03 | ARM-reset 3-path total-interest fixture pending |
| arm-02 | Full-horizon 2/2/5 caps fixture pending |
| arm-03 | 5/6 SOFR cross-validation fixture pending (Phase 5 D-08 Wave 6) |

Each TBD prompt has `numeric_status: skip` + `defer_until_phase: "13.0"` + `expected_numbers: []` so the runner reports it as `NumericScore.SKIP` per D-12-SC4-01 (excluded from gate denominator).

### 2 FRED fixture caches

| File | Series | Rate | Schema |
|------|--------|-----:|--------|
| `tests/fixtures/fred/MORTGAGE30US-2026-05-13.json` | MORTGAGE30US | 6.50 | `lib/fred_cache.py` schema_version=1; api_key=*** redacted |
| `tests/fixtures/fred/MORTGAGE15US-2026-05-13.json` | MORTGAGE15US | 5.85 | same |

The 30yr fixture is the anchor target for `live-rate-injection-01.md` (closes D-12-SC1-01 at prompt+fixture layer). The 15yr is a companion for symmetry — later waves can author a `live-rate-injection-02` for 15-yr questions without needing to re-author the fixture.

### Test-surface flips

| Test | Before | After |
|------|--------|-------|
| `test_evals_prompts_dir_has_22_prompts` | xfail(strict) | live PASS |
| `test_each_mode_has_at_least_one_prompt[evaluate/compare/refinance/affordability/stress/amortize/arm]` (7 variants) | xfail(strict) | live PASS (all 7) |
| `test_every_prompt_has_paired_oracle` | xfail(strict) | xfail(strict) — retained for Plan 12-06 |
| **Full suite** | 625 pass / 10 xfail / 5 skip | **633 pass / 2 xfail / 5 skip** (+8 newly green) |

Net: +8 newly green tests (1 count + 7 per-mode). The 1 retained xfail in `tests/test_evals_runner.py::test_every_prompt_has_paired_oracle` is closed by Plan 12-06 (paired oracles).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixture cache filename date corrected to 2026-05-13**
- **Found during:** Task 1 setup
- **Issue:** Plan body specifies filenames `MORTGAGE30US-2026-05-10.json` + `MORTGAGE15US-2026-05-10.json`, but the LOCKED objective explicitly overrides: filenames must use the *current* date 2026-05-13 (when the prompts ship), not 2026-05-10 (when CONTEXT.md was authored). Reader-clarity concern; test correctness unaffected because tests pin to fixture paths, not date strings.
- **Fix:** Wrote fixtures as `MORTGAGE30US-2026-05-13.json` + `MORTGAGE15US-2026-05-13.json` per LOCKED objective.
- **Files modified:** `tests/fixtures/fred/MORTGAGE30US-2026-05-13.json`, `tests/fixtures/fred/MORTGAGE15US-2026-05-13.json` (created with new names)
- **Commit:** `3942a42`

**2. [Rule 3 - Blocking] Updated `tests/fixtures/fred/README.md` to reflect new filenames**
- **Found during:** After fixture file creation
- **Issue:** Wave-0 README (Plan 12-00) referenced `MORTGAGE30US-2026-05-10.json` + `MORTGAGE15US-2026-05-10.json` in the "Files (populated by later waves)" table and in the live-capture diff example. Leaving the README un-updated would create a doc-vs-fact misalignment that future readers (e.g., `/gsd-audit-uat`) would flag as a stub or staleness signal.
- **Fix:** Three in-place edits in README.md changing all three `-2026-05-10` references to `-2026-05-13`.
- **Files modified:** `tests/fixtures/fred/README.md`
- **Commit:** `3942a42` (bundled with Task 1 fixtures)

**3. [Rule 3 - Blocking] `stress-01` baseline rate flipped from 6.5% to 6.0%**
- **Found during:** Task 1 (authoring stress-01.md)
- **Issue:** Plan body sets baseline at 6.5% with rates [6.0, 6.5, 7.0], but Phase 8 fixture `rate_shock_400k_30yr_grid_5_rates.json` uses baseline=0.060000 with rates `[0.060000, 0.065000, 0.070000, 0.075000, 0.080000]` and pins row index 1 (0.065) to $2528.27. Mismatch means the prompt wouldn't trace cleanly to an engine fixture.
- **Fix:** Authored stress-01.md with baseline 6.0% and full 5-rate sweep `[6.0, 6.5, 7.0, 7.5, 8.0]`, pinning the 6.5% row (index 1) to $2528.27 — exactly matching the Phase 8 fixture's `row_monthly_pi_at_index_1`. Label changed from generic `monthly_pi` to `monthly_pi_at_6_5pct` for row-specificity.
- **Files modified:** `evals/prompts/stress-01.md`
- **Commit:** `3942a42`

**4. [Rule 3 - Blocking] `affordability-01` aligned with `affordability-02` household shape**
- **Found during:** Task 1 (authoring affordability-02.md)
- **Issue:** Plan body's affordability-02 prompt says "single-applicant household" but the Phase 4 fixture `reverse_conventional_80_ltv_43_dti.json` uses 2 applicants ($5k + $5k = $10k joint) to satisfy household.size=2 = len(applicants) BLOCKER from D-09. A single-applicant prompt would not trace to the fixture.
- **Fix:** Rewrote affordability-02 prompt body to "two-applicant household earns $10,000 / month gross combined" — keeps the $10k income anchor that drives the $646,322.54 max_loan oracle but matches the engine fixture's household shape.
- **Files modified:** `evals/prompts/affordability-02.md`
- **Commit:** `3942a42`

### Architectural Changes
None — implementation matched the plan's frontmatter schema and 13/9 distribution verbatim. The 4 inline corrections above are alignment fixes (Rule 3), not architectural deviations.

### Authentication Gates
None — pure markdown + JSON authoring; no external services touched.

## Worked Examples

### Anchored prompt structure (provenance=stdout)

```markdown
---
id: refinance-01
mode: refinance
description: Rate-and-term refi positive-NPV scenario (Phase 6 positive_npv_200bps_drop_2k_costs.json).
expected_route_keywords:
  - refinance
  - refi_npv.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
expected_numbers:
  - label: npv
    value: "60705.48"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
---

I have a $300,000 mortgage at 7.0% / 25-year remaining term. ...
```

### TBD-skip prompt structure (numeric_status=skip)

```markdown
---
id: refinance-03
mode: refinance
description: TBD — negative-NPV scenario with discount-rate sensitivity analysis; oracle deferred...
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - refinance
  - refi_npv.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
---

I have a $300k mortgage at 6.25% / 30yr. ...
```

### Fixture-cache-anchored prompt (provenance=static)

```markdown
---
id: live-rate-injection-01
mode: evaluate
description: SC-1 closure eval — borrower asks current 30-yr rate; skill reads fixture cache (D-12-SC1-01).
expected_route_keywords:
  - data/cache/fred_MORTGAGE30US.json
  - "6.50"
expected_scripts: []
expected_numbers:
  - label: current_30yr_rate
    value: "6.50"
    tolerance: "0.01"
    source_script: fixture_cache
    provenance: static
---

What's the current 30-year fixed mortgage rate? ...
```

The `provenance: static` tag exempts this entry from the D-12-SC3-01 STDOUT-only sourcing rule because the cache is read via the Read tool (not a subprocess); the runner credits the cited value when it appears in the model response regardless of subprocess stdout.

### Fixture cache JSON shape

```json
{
  "schema_version": 1,
  "entries": {
    "MORTGAGE30US": {
      "value": "6.50",
      "observation_date": "2026-05-07",
      "fetched_at": "2026-05-13T12:00:00Z",
      "source_url": "https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key=***&file_type=json&sort_order=desc&limit=1",
      "fred_realtime_start": "2026-05-13",
      "fred_realtime_end": "2026-05-13",
      "error": null
    }
  }
}
```

Matches `lib/fred_cache.py` cache schema (Plan 12-02). `api_key=***` is redacted per Phase 12 RESEARCH §Pitfall 6 + T-12-05-03 threat mitigation. `value` is a JSON string per D-19 money discipline.

## Gate Math Sanity (D-12-SC4-01)

After Plan 12-06 ships the 22 paired oracles, the runner's replay-stub mode will score:

```
HarnessReport(
    n_prompts=22,
    route_match_count=22,         # all 22 reach the right scripts
    numeric_pass_count=13,        # 13 anchored prompts hit their oracles
    numeric_fail_count=0,
    numeric_skip_count=9,         # 9 TBD prompts excluded from denominator
)
numeric_match_rate = 13 / (13 + 0) = 1.0000 ≥ 0.95 → GATE PASSES
```

A single fail among the 13 anchored prompts drops the rate to 12/(12+1) = 92.3% < 95% → GATE FAILS. This is the math the runner enforces, validated by `test_gate_passes_with_13_anchored_pass_and_9_skip` + `test_gate_fails_with_one_anchored_fail_among_13` (both flipped to live by Plan 12-04).

## Commits

| Hash | Description | Files |
|------|-------------|-------|
| `3942a42` | feat(12-05): author 13 anchored eval prompts + 2 FRED fixture caches | 13 prompt .md + 2 fixture .json + README.md (16 total, 308 ins, 5 del) |
| `3af6abf` | feat(12-05): author 9 TBD-skip eval prompts + flip 2 of 3 remaining xfails | 9 prompt .md + tests/test_evals_runner.py (10 total, 178 ins, 20 del) |

## Threat Flags

None — implementation respects the plan's `<threat_model>`:

- T-12-05-01 (Information Disclosure: eval prompts) — **accept**: All prompt content is synthetic ($400k loans, fictional households, no real PII). Verified by inspection of all 22 prompts.
- T-12-05-02 (Tampering: fixture cache values) — **mitigate**: `live-rate-injection-01` oracle pins to 6.50 in the MORTGAGE30US fixture; CI replays this rate deterministically. Synthetic fixture remains the test anchor regardless of upstream FRED drift.
- T-12-05-03 (Information Disclosure: API key leakage in fixture) — **mitigate**: Both fixture cache files contain `api_key=***` redacted source_url; no real keys.

## Verification

All gates green:
- ✅ `evals/prompts/*.md` count = 22 (verified by `ls | wc -l`)
- ✅ 13 anchored prompts have non-empty `expected_numbers` (verified by frontmatter parse loop)
- ✅ 9 TBD prompts have `numeric_status: skip` + `defer_until_phase: "13.0"` + `expected_numbers: []` (verified by grep)
- ✅ All 7 SKILL.md modes have ≥1 prompt (verified by per-mode parametrize test green)
- ✅ `live-rate-injection-01.md` uses `provenance: static` (verified by frontmatter parse)
- ✅ 2 fixture caches at `tests/fixtures/fred/` with schema_version=1 + redacted `api_key=***`
- ✅ MORTGAGE30US fixture value=6.50 (matches prompt oracle)
- ✅ MORTGAGE15US fixture value=5.85 (companion)
- ✅ 2 of 3 remaining xfails flipped in `tests/test_evals_runner.py`; 1 retained for Plan 12-06
- ✅ mypy --strict clean on `tests/test_evals_runner.py`
- ✅ ruff clean on `tests/test_evals_runner.py`
- ✅ Full test suite: 633 passed, 5 skipped, 2 xfailed (was 625 / 5 / 10 — exactly +8 newly green)
- ✅ No regressions to Phases 1-11

## Self-Check: PASSED

- ✅ All 22 prompt files exist in `evals/prompts/`:
  - evaluate-01.md, evaluate-02.md, evaluate-03.md
  - compare-01.md, compare-02.md, compare-03.md
  - refinance-01.md, refinance-02.md, refinance-03.md
  - affordability-01.md, affordability-02.md, affordability-03.md
  - stress-01.md, stress-02.md, stress-03.md
  - amortize-01.md, amortize-02.md, amortize-03.md
  - arm-01.md, arm-02.md, arm-03.md
  - live-rate-injection-01.md
- ✅ Both fixture cache files exist:
  - `tests/fixtures/fred/MORTGAGE30US-2026-05-13.json` (value=6.50)
  - `tests/fixtures/fred/MORTGAGE15US-2026-05-13.json` (value=5.85)
- ✅ `tests/test_evals_runner.py` modified (1 xfail remains, was 3)
- ✅ Commit `3942a42` exists in git log (Task 1)
- ✅ Commit `3af6abf` exists in git log (Task 2)
- ✅ Worktree base unchanged: `c1929b9eb6374838f5717213fa52cc68efb5a73f`

## Hand-Off to Plan 12-06

Plan 12-06 (paired oracles) now has the 22-prompt input set. The 1:1 stem mapping means Plan 12-06 must author exactly 22 `evals/expected/{id}.json` oracle files:

| Anchored (13 — full expected_numbers + numeric_status=anchored) | TBD (9 — numeric_status=skip + defer_until_phase=13.0) |
|--------------------------------------------------------------|---------------------------------------------------------|
| evaluate-01, evaluate-02 | evaluate-03 |
| compare-01, compare-02 | compare-03 |
| refinance-01 | refinance-02, refinance-03 |
| affordability-01, affordability-02 | affordability-03 |
| stress-01 | stress-02, stress-03 |
| amortize-01, amortize-02, amortize-03 | (none) |
| arm-01 | arm-02, arm-03 |
| live-rate-injection-01 | (none) |

After Plan 12-06, the final xfail in `tests/test_evals_runner.py::test_every_prompt_has_paired_oracle` flips to live, and `python -m evals.runner` can run replay-stub mode against the full 22-prompt set and emit the JSON HarnessReport with `numeric_match_rate ≥ 0.95` (13/13 anchored pass, 9 skip). Plan 12-07 then wires the gate into CI.
