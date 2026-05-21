---
phase: 15-property-skill-mode-report-formatter
plan: 01
subsystem: testing
tags: [pytest, tiktoken, pydantic, decimal, xfail, wave-0, red-bed, evals]

# Dependency graph
requires:
  - phase: 14-property-analysis-pipeline
    provides: "AnalysisReport + analyze() frozen contract (lib/property_analysis.py)"
  - phase: 13-property-ingestion
    provides: "PropertyListing model + skill-folder script precedent (property_fetch.py)"
  - phase: 12-fred-eval
    provides: "always-exit-0 envelope contract + evals.metrics scorers"
  - phase: 11-subagents
    provides: "synthetic-only-in-CI fixture policy (D-02)"
  - phase: 10-claude-skill
    provides: "SKILL.md routing + count_tokens helper + 4500-token D-02 budget"
  - phase: 4-affordability
    provides: "config/household.example.yml multi-applicant schema (Pitfall 2 anchor)"
provides:
  - "Wave 0 RED test bed: 34 test stubs across 3 files (15 + 11 + 8) — xfail/fail until Plans 15-02..15-04 ship"
  - "Synthetic Phase 11-D-02-compliant property eval fixture (sfh_conforming_001.json + .html)"
  - "Eval oracle pinning verdict.level via expected_route_keywords + 3 hand-calc numerics (D-15-EVAL-03)"
  - "Per-task verification commands now point at real test files (validates VALIDATION.md sampling map)"
affects: [15-02, 15-03, 15-04, 15-05]

# Tech tracking
tech-stack:
  added: []  # No new dependencies; uses existing pytest + tiktoken + pydantic
  patterns:
    - "Wave 0 RED guard: module-level pytestmark xfail when target source absent, so collection succeeds"
    - "Per-test xfail decorator (_xfail_unless_*_exists) for fine-grained gating when only some tests depend on the unbuilt source"
    - "type: ignore[import-not-found] on Wave 0 imports of unbuilt lib modules (warn_unused_ignores will force removal when Plan 15-02 ships)"
    - "Subprocess CLI tests use SCRIPT_PATH constant pointing inside skill folder (RESEARCH OQ2 RESOLVED)"

key-files:
  created:
    - "evals/fixtures/property/sfh_conforming_001.json"
    - "evals/fixtures/property/sfh_conforming_001.html"
    - "evals/expected/property-analysis-01.json"
    - "tests/test_property_report.py"
    - "tests/test_property_analyze_cli.py"
    - "tests/test_skill_routing.py"
  modified: []

key-decisions:
  - "Hand-calc anchor conv30_preferred_dp_piti = $3,760.34 derived from $500k loan @ 6.50%/30yr (P&I=$3,160.34) + $500 tax/12 + $100 insurance/12 + $0 HOA + $0 PMI (LTV=0.80)"
  - "Oracle uses expected_route_keywords=['GO'] for verdict.level (per A4 / RESEARCH L775: evals.metrics.NUMBER_REGEX requires decimal point; non-numeric values pin via route keywords — matches live-rate-injection-01.md precedent)"
  - "Wave 0 RED gate confirmed: 3 failed (SKILL.md needs Row 0 from Plan 15-04) + 29 xfailed (modes/property.md + scripts/property_analyze.py + lib/property_report.py unbuilt) + 1 passed + 1 xpassed; collect-only exits 0"
  - "Three guard mechanisms used per file: (a) test_property_report.py — module-level pytestmark xfail on ImportError of lib.property_report; (b) test_property_analyze_cli.py — module-level pytestmark xfail when SCRIPT_PATH absent on disk; (c) test_skill_routing.py — per-test xfail decorator only on tests reading modes/property.md (SKILL.md tests run unconditionally)"

patterns-established:
  - "Synthetic eval fixture shape: mirror Phase 14 unit-test fixture (listing/household/profile/fred_rates/expected_response/_meta) but live under evals/fixtures/property/ with synthetic zpid='1' + synthetic source_url + no PII"
  - "Oracle frontmatter: expected_route_keywords pins non-numeric values (verdict level), expected_numbers pins 3 hand-calc anchors with decimal-point form to satisfy NUMBER_REGEX"
  - "Footer citation prefix: '*Computed by: python .claude/skills/mortgage-ops/scripts/property_analyze.py' (full skill-relative invocation per D-15-CITATION-03 + RESEARCH OQ2 RESOLVED)"

requirements-completed: []  # AUTHORED stubs only; requirements remain pending until Plans 15-02..15-04 ship the GREEN implementation

# Metrics
duration: ~9min
completed: 2026-05-21
---

# Phase 15 Plan 15-01: Wave 0 Test Scaffolding + Synthetic Fixtures + Oracle Stub Summary

**Wave 0 RED bed: 34 pytest stubs (15 + 11 + 8) targeting unbuilt formatter/orchestrator/SKILL-Row-0/mode-file, plus synthetic eval fixture + 2KB HTML stub + oracle pinning verdict.level via route keywords + 3 hand-calc numerics — all xfail/fail until Plans 15-02..15-04 ship.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-21T07:35:25Z
- **Completed:** 2026-05-21T07:44:01Z
- **Tasks:** 3
- **Files created:** 6
- **Files modified:** 0

## Accomplishments

- Synthetic SFH-conforming property fixture (zpid="1", $625k King County WA) with full Phase-14-shape expected_response: 3 programs × 6 DP cells, GO-ALL-GREEN verdict, hand-calc-anchored tax block
- 795-byte HTML stub with `<script id="__NEXT_DATA__">` block (well under 2KB budget per D-15-EVAL-01)
- Eval oracle (`evals/expected/property-analysis-01.json`) pinning verdict.level via `expected_route_keywords=["GO"]` (A4) plus 3 numerics: `conv30_preferred_dp_piti=3760.34` ±0.50, `first_year_interest_conv30=32335.43` ±0.50, `verdict_reasons_count=1.0` ±0.0 (D-15-EVAL-03)
- `tests/test_property_report.py` — 10 functions (15 with parametrize) covering RPRT-01 (6-section render, matrix cells/marks, preferred-DP bold, blocker truncation, arm_reset Conv30-only, tax over-cap CPA callout) + RPRT-02 (6 citation footers, full re-runnable invocation) + Pitfall 4 signed-money format
- `tests/test_property_analyze_cli.py` — 11 functions covering MODE-03 (subprocess help fast path, argparse exit-2, success/error envelopes always-exit-0, Pydantic stderr 6-key, filename NNN format, same-day -r2 suffix, household.yml multi-applicant mapping, --output-dir path-traversal rejection, User Layer mtime invariance, sidecar listing JSON write)
- `tests/test_skill_routing.py` — 8 functions covering MODE-01 (modes/property.md presence, extractor prompt embed, _shared.md load-first, orchestrator dispatch full-path invocation, envelope-code enumeration) + MODE-02 (cl100k token budget ≤4500, Row 0 zillow.com/analyze-listing/property/property_analyze.py keywords in first 200 lines, SKILL.md → modes/property.md cross-reference)
- Wave 0 RED state confirmed: `uv run pytest tests/test_property_report.py tests/test_property_analyze_cli.py tests/test_skill_routing.py` → 3 failed + 1 passed + 29 xfailed + 1 xpassed (non-zero exit); `--collect-only` succeeds (exit 0)

## Task Commits

Each task was committed atomically:

1. **Task 1: Author synthetic fixture (JSON + HTML stub) + eval oracle stub** — `ea3715d` (feat)
2. **Task 2: Author `tests/test_property_report.py` Wave 0 RED stubs (RPRT-01, RPRT-02)** — `2391b3f` (test)
3. **Task 3: Author `tests/test_property_analyze_cli.py` + `tests/test_skill_routing.py` Wave 0 RED stubs (MODE-01, MODE-02, MODE-03)** — `4b151b4` (test)

**Plan metadata commit:** (created after this SUMMARY is written; will cover SUMMARY + STATE + ROADMAP + REQUIREMENTS)

## Files Created

- `evals/fixtures/property/sfh_conforming_001.json` — synthetic PropertyListing + Household + Profile + FRED rates + expected_response (Phase 14 fixture shape; zpid="1", $625k SFH, King County WA, Decimal-as-string discipline throughout; hand-calc anchors per RESEARCH lines 760-767)
- `evals/fixtures/property/sfh_conforming_001.html` — 795-byte synthetic Zillow stub with `__NEXT_DATA__` JSON block mirroring fixture's listing block, no PII, synthetic address
- `evals/expected/property-analysis-01.json` — oracle: `expected_route_keywords=["property", "property_analyze.py", "GO"]` pins verdict.level via A4 string-match path; `expected_numbers` has 3 entries with decimal-point form satisfying NUMBER_REGEX; `numeric_status="anchored"` on every entry per WARNING 5 reconciliation
- `tests/test_property_report.py` — RPRT-01/RPRT-02 unit-test stubs; module-level pytestmark xfail on ImportError of lib.property_report; sample_report fixture loads tests/fixtures/property_analysis/sfh_conforming_king_county.json (Phase 14 canonical anchor; NOT eval fixture per PATTERNS L607-619); sample_report_with_negative_refi fixture mutates AnalysisReport via model_copy for Pitfall 4 coverage
- `tests/test_property_analyze_cli.py` — MODE-03 subprocess CLI stubs; SCRIPT_PATH points at `.claude/skills/mortgage-ops/scripts/property_analyze.py` (skill folder per RESEARCH OQ2 RESOLVED); module-level xfail when SCRIPT_PATH absent
- `tests/test_skill_routing.py` — MODE-01/MODE-02 filesystem-introspection stubs; skill_root fixture points at `.claude/skills/mortgage-ops/`; per-test xfail decorator for the 4 tests that read modes/property.md; SKILL.md token-budget + Row 0 + cross-reference tests run unconditionally and currently RED until Plan 15-04 inserts Row 0

## Hand-Calc Derivation (conv30_preferred_dp_piti = 3760.34)

Per Phase 14 fixture's notes block (carried into Plan 15-01 oracle):

- **Loan amount:** $625,000 × (1 − 0.20) = $500,000 (Conv30 at 20% DP)
- **Rate:** MORTGAGE30US = 0.065000 (FRED-style injection per fixture's fred_rates block)
- **P&I:** $500,000 × `0.005416667 × (1.005416667)^360 / ((1.005416667)^360 − 1)` = $3,160.34 (matches Phase 14 fixture line 70 and Wikipedia oracle $200k@6.5%/30yr ratio)
- **Tax/month:** $6,000 / 12 = $500.00
- **Insurance/month:** $1,200 / 12 = $100.00
- **HOA/month:** $0.00 (SFH; D-15-EVAL-01 explicitly zeros this)
- **PMI/month:** $0.00 (LTV = 0.80 exact; Conv PMI fires only at LTV > 0.80)
- **PITI total:** $3,160.34 + $500.00 + $100.00 + $0.00 + $0.00 = **$3,760.34** ✓

The eval fixture's household differs from the Phase 14 unit fixture (14000/800 vs 15000/400 monthly_income/monthly_obligations) but the **loan/rate/escrow inputs are identical** so the PITI anchor is unchanged. The DTI back-end value (0.325739) and other household-dependent rows are recomputed accordingly in the fixture's expected_response.

## Oracle Frontmatter Shape

```json
{
  "schema_version": 1,
  "id": "property-analysis-01",
  "mode": "property",
  "numeric_status": "anchored",
  "expected_scripts": [{"script": "property_analyze.py", "args_must_include": ["--listing", "--household", "--profile"]}],
  "expected_numbers": [3 entries with numeric_status="anchored", decimal-point values, tolerance="0.50" (PITI/interest) or "0.0" (reasons-count)],
  "expected_route_keywords": ["property", "property_analyze.py", "GO"],
  "v1_frozen_at": "2026-05-20"
}
```

## Test Function Count + Requirement Coverage

| File | def test_ count | Collected (incl. parametrize) | Requirement coverage |
|------|-----------------|-------------------------------|----------------------|
| tests/test_property_report.py | 10 | 15 | RPRT-01, RPRT-02 (14 docstring references) |
| tests/test_property_analyze_cli.py | 11 | 11 | MODE-03 (15 docstring references) |
| tests/test_skill_routing.py | 8 | 8 | MODE-01, MODE-02 (28 docstring references) |
| **Totals** | **29** | **34** | All 5 Phase 15 requirements referenced (57 total) |

## Wave 0 RED State Confirmation

`uv run pytest tests/test_property_report.py tests/test_property_analyze_cli.py tests/test_skill_routing.py 2>&1 | tail -2` →

```
============== 3 failed, 1 passed, 29 xfailed, 1 xpassed in 0.54s ==============
```

**Breakdown:**

| Outcome | Count | Why |
|---------|-------|-----|
| failed | 3 | SKILL.md does not yet contain "zillow.com" / "property_analyze.py" / "modes/property.md" — Plan 15-04 inserts Row 0 |
| passed | 1 | `test_argparse_error_exit_2` — accidentally GREEN because `python /nonexistent.py` exits 2 (matches assertion); harmless XPASS-equivalent, strict=False keeps suite green |
| xfailed | 29 | Module-level pytestmark xfail or per-test xfail decorator on Wave 0 RED tests targeting unbuilt lib.property_report (15) + scripts/property_analyze.py (10) + modes/property.md (4) |
| xpassed | 1 | One subprocess test in test_property_analyze_cli.py xpassed for the same accidental-pass reason; strict=False means harmless |

**Quick-verify (collection succeeds even when tests RED):**

```
$ uv run pytest tests/test_property_report.py tests/test_property_analyze_cli.py tests/test_skill_routing.py --collect-only
========================= 34 tests collected in 0.18s ==========================
```

Exit code 0 ✓ — VALIDATION.md sampling contract satisfied.

## Decisions Made

- **Eval fixture household differs from Phase 14 unit fixture (monthly_income=14000 vs 15000, monthly_obligations=800 vs 400):** Plan-stipulated values used directly; the PITI/loan/rate anchors are identical because loan terms + escrow are unchanged, so the oracle's `conv30_preferred_dp_piti=3760.34` is reproducible.
- **Three guard mechanisms used across files** (vs uniform module-level xfail) so that SKILL.md tests (Plan 15-04 dependency) can run independently of mode-file tests (also Plan 15-04 dependency) and lib.property_report tests (Plan 15-02 dependency) and orchestrator tests (Plan 15-03 dependency). Each test fails at the right wave's source-shipment milestone.
- **`type: ignore[import-not-found]` on lib.property_report import:** Mypy strict mode + warn_unused_ignores will catch the ignore and force its removal when Plan 15-02 ships the module — a built-in hygiene check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved ruff PT018 + ruff-format + mypy import-not-found in test_property_report.py**
- **Found during:** Task 2 commit (pre-commit hooks)
- **Issue:** (a) `assert "see CPA" not in tax and "see cpa" not in tax.lower()` triggered PT018 (compound assertion); (b) `assert "arm_reset" in rate_stress.lower() or "arm reset" in rate_stress.lower()` also PT018; (c) one branch had nonsensical `assert "## RATE STRESS" not in rate_stress` (always-true since `rate_stress` is the post-split substring); (d) mypy strict flagged `from lib.property_report import render` as import-not-found
- **Fix:** Folded the case-insensitive matches into `.lower()` once at the variable level (so the assertion is a single `in` check); for arm_reset added `.replace("_", " ")` normalization; replaced nonsensical assertion with `len(rate_stress.strip()) > 0`; added `# type: ignore[import-not-found]` to the lib.property_report import (mypy's `warn_unused_ignores = true` will force removal at Plan 15-02 ship time)
- **Files modified:** tests/test_property_report.py
- **Verification:** `uv run ruff check tests/test_property_report.py` + `uv run mypy tests/test_property_report.py` both pass; pytest collection still finds 15 tests; all xfail (RED Wave 0)
- **Committed in:** 2391b3f (Task 2 commit, after lint fixes)

**2. [Rule 3 - Blocking] Pre-commit ruff-format auto-reformatted test_property_analyze_cli.py + test_skill_routing.py on first commit attempt**
- **Found during:** Task 3 commit (pre-commit hooks)
- **Issue:** Pre-commit ruff-format hook reformatted multi-line argument lists into more compact form; first commit attempt failed because files were modified post-stage
- **Fix:** Re-staged the reformatted files and re-ran `git commit` — second attempt succeeded with all hooks passing
- **Files modified:** tests/test_property_analyze_cli.py, tests/test_skill_routing.py
- **Verification:** Second commit attempt: all 5 hooks passed (ruff, ruff-format, mypy, check-yaml, block-user-layer)
- **Committed in:** 4b151b4 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking lint/format issues that prevented committing). No functional changes; no scope creep.

**Impact on plan:** Auto-fixes preserved test semantics and required no plan-level changes. The compound-assertion refactoring made tests slightly more readable; the type-ignore comment is self-removing once Plan 15-02 ships.

## Issues Encountered

- **`test_argparse_error_exit_2` accidentally PASSES** even though `SCRIPT_PATH` does not exist: when Python is invoked with a non-existent script path, the interpreter itself exits with code 2 ("can't open file"), which happens to match the assertion. The test is marked under `pytestmark = pytest.mark.xfail(..., strict=False)` so the XPASS doesn't fail the suite — but the test does not actually verify orchestrator behavior in Wave 0; Plan 15-03 will retire the module-level xfail when the orchestrator ships, at which point the test verifies argparse's real exit-2 path. Documented as a known-harmless Wave 0 artifact in the test docstring.

## Threat Flags

None — Plan 15-01 ships only test stubs + synthetic fixtures + an oracle JSON. No new network endpoints, auth paths, file-access patterns, or trust-boundary changes beyond what Phase 11 D-02 (synthetic-only fixture policy) already covers. T-15-01..T-15-03 from the plan's threat model are all `mitigate` (PII) or `accept` (test subprocesses) and remain mitigated: synthetic address ("Synthetic Address"), zpid="1", source_url uses synthetic Zillow path, v1_frozen_at + _meta.citation provide auditable provenance.

## Known Stubs

This plan AUTHORS RED test stubs by design — they are NOT bugs. The following will flip GREEN as Waves 1-2 ship:

| Stub | Target | Resolved by |
|------|--------|-------------|
| `from lib.property_report import render` xfail guard | lib/property_report.py | Plan 15-02 |
| `scripts/property_analyze.py` not-on-disk xfail guard | .claude/skills/mortgage-ops/scripts/property_analyze.py | Plan 15-03 |
| `modes/property.md` not-on-disk per-test xfail decorator | .claude/skills/mortgage-ops/modes/property.md | Plan 15-04 |
| SKILL.md Row 0 absent → 3 currently-failing tests | .claude/skills/mortgage-ops/SKILL.md (Row 0 insertion) | Plan 15-04 |

## User Setup Required

None — Wave 0 test scaffolding requires no external configuration. The synthetic fixture uses no live network calls; the eval oracle uses no FRED cache or live rates.

## Next Phase Readiness

Wave 0 RED bed complete. Plans 15-02 (lib/property_report.py), 15-03 (scripts/property_analyze.py), 15-04 (SKILL.md Row 0 + modes/property.md), and 15-05 (evals/prompts/property-analysis-01.md) can now consume:

- The 6 automated `<verify>` commands from VALIDATION.md per-task verification map
- The 3 hand-calc oracle numerics for end-to-end SC-6 gating
- The synthetic eval fixture as the canonical end-to-end pipeline input

No blockers; all dependencies (Phase 14 AnalysisReport contract, Phase 13 PropertyListing model, Phase 4 household.yml schema, Phase 10 count_tokens helper, Phase 11 D-02 synthetic-only fixture policy, Phase 12 always-exit-0 envelope) are honored.

## Self-Check: PASSED

Verified 2026-05-21:

**Files (7/7 exist):**
- `evals/fixtures/property/sfh_conforming_001.json`
- `evals/fixtures/property/sfh_conforming_001.html`
- `evals/expected/property-analysis-01.json`
- `tests/test_property_report.py`
- `tests/test_property_analyze_cli.py`
- `tests/test_skill_routing.py`
- `.planning/phases/15-property-skill-mode-report-formatter/15-01-SUMMARY.md`

**Commits (3/3 in git log):**
- `ea3715d` — feat(15-01): add synthetic property fixture + HTML stub + eval oracle
- `2391b3f` — test(15-01): add Wave 0 RED stubs for lib.property_report.render() (RPRT-01, RPRT-02)
- `4b151b4` — test(15-01): add Wave 0 RED stubs for CLI orchestrator + skill routing (MODE-01, MODE-02, MODE-03)

---
*Phase: 15-property-skill-mode-report-formatter*
*Completed: 2026-05-21*
