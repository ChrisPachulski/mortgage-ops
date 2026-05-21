---
phase: 15-property-skill-mode-report-formatter
verified: 2026-05-20T10:00:00Z
status: passed
score: 6/6 success-criteria verified, 5/5 requirements closed
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 15: `property` Skill Mode + Report Formatter — Verification Report

**Phase Goal:** Wire the analysis pipeline into the Claude skill via a new `property` mode; emit the report as a single-page markdown file under `reports/`.

**Verified:** 2026-05-20
**Status:** PASSED
**Re-verification:** No — initial verification

## PHASE VERIFIED

All 6 roadmap Success Criteria proven by direct execution against the codebase. All 5 requirements (MODE-01, MODE-02, MODE-03, RPRT-01, RPRT-02) have observable evidence on disk + green tests + a working end-to-end run that produced a real markdown report with 6 sections and 6 citation footers.

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                              | Status     | Evidence                                                                                                                                                                                            |
| --- | ------------------------------------------------------------------------------------------------------------------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `modes/property.md` exists with URL-pin routing (`zillow.com` OR `analyze listing`)                                | ✓ VERIFIED | `.claude/skills/mortgage-ops/modes/property.md` (9840 bytes) §"When to invoke" lines 6-23 lock the two triggers; §"Special case" handles bare phrase; Examples at line 14-16 show URL-pin behavior. |
| 2   | SKILL.md routing block cross-references `modes/property.md`; ≤ 4500 cl100k tokens preserved                        | ✓ VERIFIED | SKILL.md line 25 has the Zillow URL routing row (first row of table); line 40 has explicit "0. URL pin" precedence; line 138 cross-refs `modes/property.md`. **Token count: 3796** (≤ 4500).        |
| 3   | `scripts/property_analyze.py` orchestrator runs end-to-end with always-exit-0 + envelope                           | ✓ VERIFIED | Live smoke test: orchestrator emits `{"report_path": "...", "verdict": "WATCH", "error": null}` and exits 0. Also tested error path (`output_dir_unwritable`, `fred_cache_cold`) — both exit 0.     |
| 4   | `lib/property_report.py` emits markdown to `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md` with all 6 sections     | ✓ VERIFIED | Live-generated report `/tmp/test_reports/001-property-1-2026-05-21.md` — filename matches pattern. `grep -c "^## "` = **6** sections; matrix table with bold preferred-DP column present.           |
| 5   | Every section ends with citation footer `*Computed by: python .claude/skills/.../property_analyze.py ...*`         | ✓ VERIFIED | `grep -c "^\*Computed by:"` on the live report = **6** footers — exactly one per section. All footers carry full re-runnable invocation with `--listing/--household/--profile/--output-dir`.        |
| 6   | `evals/prompts/property-analysis-01.md` exercises full property mode; `python -m evals.runner` exits 0 with ≥ 0.95 | ✓ VERIFIED | `uv run python -m evals.runner` returns `route_match_rate=1.0`, `numeric_match_rate=1.0`, `failures=[]` across 23 prompts. Property-analysis-01 in eval roster.                                      |

**Score:** 6/6 truths verified (100%).

### Required Artifacts

| Artifact                                                            | Expected                                              | Status     | Details                                                                                                                                                                                                                |
| ------------------------------------------------------------------- | ----------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.claude/skills/mortgage-ops/modes/property.md`                     | URL-pin mode body + extractor recipe + dispatch       | ✓ VERIFIED | 9840 bytes. Contains Pattern-1 `__NEXT_DATA__` extractor prompt verbatim, sentinel-key handling, gap-fill recipe, orchestrator dispatch with full argv, edge-case catalog (7 error codes), worked example.             |
| `.claude/skills/mortgage-ops/scripts/property_analyze.py`           | Orchestrator (Phase 12 envelope; D-15-ORCH-01..04)    | ✓ VERIFIED | 20233 bytes. `--help` returns in <100ms; argparse exit-2 only on parse error; envelope shape verified live; sidecar listing write to `data/property-listings/` + NNN sequencer documented in docstring lines 65-72.    |
| `.claude/skills/mortgage-ops/SKILL.md`                              | Row 0 (URL-pin) at top of routing table; ≤4500 tokens | ✓ VERIFIED | Line 25 of routing table is the Zillow URL row. Line 40 has `"0. URL pin"` precedence. Token count = 3796 (per `tiktoken.encoding_for_model('gpt-4').encode(...)`).                                                    |
| `lib/property_report.py`                                            | AnalysisReport → 6-section markdown formatter         | ✓ VERIFIED | 21670 bytes. Render produces matrix, rate-stress, points, refi, tax, verdict sections with citation footers. Preferred-DP column bold + `(your DP)` annotation present.                                                |
| `evals/prompts/property-analysis-01.md`                             | Eval prompt with oracle (verdict + 3 numerics)        | ✓ VERIFIED | Frontmatter pins `expected_route_keywords=[property, property_analyze.py, WATCH]`; `expected_numbers`: 3 entries (`conv30_preferred_dp_piti=3760.34`, `first_year_interest_conv30=32335.43`, `verdict_reasons_count=3`). |
| `evals/expected/property-analysis-01.json`                          | Oracle JSON                                           | ✓ VERIFIED | 1067 bytes; mirrors prompt frontmatter.                                                                                                                                                                                |
| `evals/fixtures/property/sfh_conforming_001.json` + `.html`         | Synthetic fixture per Phase 11 D-02                   | ✓ VERIFIED | 4748 byte JSON + 795 byte HTML (≤ 2KB budget per D-15-EVAL-01). Synthetic zpid="1"; no PII.                                                                                                                            |
| `tests/test_property_report.py`                                     | 10 functions / 15 collected (RPRT-01, RPRT-02)        | ✓ VERIFIED | 15 tests collected, all pass GREEN after Plan 15-02 shipped.                                                                                                                                                           |
| `tests/test_property_analyze_cli.py`                                | 11 functions (MODE-03)                                | ✓ VERIFIED | 11 tests collected, all pass GREEN after Plan 15-03 shipped.                                                                                                                                                           |
| `tests/test_skill_routing.py`                                       | 8 functions (MODE-01, MODE-02)                        | ✓ VERIFIED | 8 tests collected, all pass GREEN after Plan 15-04 shipped.                                                                                                                                                            |
| `config/household.example.yml` extension                            | `liquid_reserves` + `preferred_down_payment_pct`      | ✓ VERIFIED | Committed in 6359fbc (feat 15-03).                                                                                                                                                                                     |

### Key Link Verification (Wiring)

| From                                                | To                                       | Via                                          | Status     | Details                                                                                                                                       |
| --------------------------------------------------- | ---------------------------------------- | -------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/property_analyze.py`                       | `lib.property_analysis.analyze`          | Direct import + call                         | ✓ WIRED    | Orchestrator composes Phase 14 `analyze()`; live run produces matrix + stress + refi + points + tax + verdict blocks consumed by formatter.   |
| `scripts/property_analyze.py`                       | `lib.property_report.render`             | Direct import + call                         | ✓ WIRED    | Formatter receives AnalysisReport from analyze() and emits markdown string; orchestrator persists to disk.                                    |
| `modes/property.md`                                 | `scripts/property_analyze.py`            | Documented bash invocation lines 126-132     | ✓ WIRED    | Mode body has full skill-relative invocation `python .claude/skills/mortgage-ops/scripts/property_analyze.py --listing ... --household ...`. |
| `SKILL.md` routing table                            | `modes/property.md`                      | Line 138 cross-ref                           | ✓ WIRED    | "then read `modes/{mode}.md` (e.g., `modes/property.md` for Zillow URL-pin dispatch)" — explicit name-cite per D-09 progressive disclosure.    |
| `SKILL.md` precedence section                       | Row 0 URL-pin                            | Lines 40-41 explicit precedence              | ✓ WIRED    | "0. URL pin: `zillow.com` substring OR phrase \"analyze listing\" → `property` (HIGHEST — overrides ALL verbs and explicit slash-commands)".  |
| `evals/prompts/property-analysis-01.md`             | `evals/expected/property-analysis-01.json` | Filename-based runner lookup                 | ✓ WIRED    | `python -m evals.runner` picks up prompt + oracle pair; route_match=1.0, numeric_match=1.0.                                                   |
| `lib/property_report.py` citation-footer generator  | Orchestrator argv (re-runnable)          | `python .claude/skills/...property_analyze.py --listing X --household Y --profile Z --output-dir W` | ✓ WIRED    | Each section's `*Computed by:*` footer carries the exact orchestrator invocation that produced it; full path; orchestrator-only (no per-primitive citations) per D-15-CITATION-02. |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable              | Source                                         | Produces Real Data | Status     |
| --------------------------------- | -------------------------- | ---------------------------------------------- | ------------------ | ---------- |
| Markdown report (live smoke run)  | `report` (AnalysisReport)  | `lib.property_analysis.analyze(...)`           | Yes — verified end-to-end | ✓ FLOWING  |
| Report's YOUR FIT matrix          | `report.matrix.cells`      | `analyze()` fans 4 programs × 6 DPs            | Yes — 18 cells populated on live SFH-conforming run | ✓ FLOWING  |
| Report's RATE STRESS section      | `report.stress_results`    | `analyze()` calls `lib.stress` per program     | Yes — 7 stress rows produced (3 income shocks + 3 rate shocks + 1 ARM peak) | ✓ FLOWING  |
| Report's TAX section              | `report.tax_block`         | `analyze()` calls `lib.rules.irs_pub936`       | Yes — first-year interest computed per program ($32,335.43 Conv30 matches eval oracle) | ✓ FLOWING  |
| Report's REFI section             | `report.refi_results`      | `analyze()` calls `lib.refinance` per program  | Yes — 6 refi rows (3 programs × 2 scenarios) | ✓ FLOWING  |
| Verdict envelope from orchestrator| `verdict_level`            | Pydantic field from `report.verdict.level`     | Yes — "WATCH" emitted on live run with predicate codes in reasons | ✓ FLOWING  |

### Behavioral Spot-Checks

| Behavior                                                                          | Command                                                                                              | Result                                                                       | Status |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ------ |
| Phase 15 test triplet passes                                                      | `uv run pytest tests/test_property_report.py tests/test_property_analyze_cli.py tests/test_skill_routing.py -x` | 34 passed, 2 warnings (stale-ref, unrelated) in 10.68s                       | ✓ PASS |
| Evals runner exits 0 with route_match + numeric_match ≥ 0.95                      | `uv run python -m evals.runner`                                                                       | route_match_rate=1.0, numeric_match_rate=1.0, failures=[]                    | ✓ PASS |
| SKILL.md token budget ≤ 4500                                                      | `tiktoken cl100k count of SKILL.md`                                                                  | 3796 (≤ 4500)                                                                | ✓ PASS |
| SKILL.md routing table has URL-pin row                                            | `grep -n 'zillow.com' SKILL.md`                                                                      | Line 25 (routing-table row) + line 40 (precedence row) + line 138 (cross-ref) | ✓ PASS |
| Orchestrator `--help` returns                                                     | `uv run python .claude/skills/mortgage-ops/scripts/property_analyze.py --help`                       | argparse usage with all 4 flags + envelope-shape docstring                   | ✓ PASS |
| Orchestrator always-exit-0 on `output_dir_unwritable` error                       | run with `--output-dir /tmp/test_reports` (nonexistent)                                              | `exit=0` with error envelope `{"error":{"code":"output_dir_unwritable",...}}` | ✓ PASS |
| Orchestrator always-exit-0 on `fred_cache_cold` error                             | run before populating FRED cache                                                                     | `exit=0` with error envelope `{"error":{"code":"fred_cache_cold",...}}`      | ✓ PASS |
| Orchestrator full end-to-end success run                                          | run with valid listing + household + profile + FRED cache                                            | `exit=0`, `{"report_path":"/private/tmp/test_reports/001-property-1-2026-05-21.md","verdict":"WATCH","error":null}` | ✓ PASS |
| Report filename matches `{NNN}-property-{zpid}-{YYYY-MM-DD}.md`                   | inspect orchestrator output path                                                                     | `001-property-1-2026-05-21.md` ✓                                             | ✓ PASS |
| Report has 6 sections                                                             | `grep -c "^## " /private/tmp/test_reports/001-property-1-2026-05-21.md`                              | 6                                                                            | ✓ PASS |
| Report has 6 citation footers                                                     | `grep -c "^\*Computed by:" /private/tmp/test_reports/001-property-1-2026-05-21.md`                   | 6                                                                            | ✓ PASS |
| Section names match contract (YOUR FIT, RATE STRESS, POINTS BREAKEVEN, REFI OPPORTUNITY, TAX, VERDICT) | `grep "^## " /private/tmp/test_reports/001-property-1-2026-05-21.md`                                 | All 6 sections present in order                                              | ✓ PASS |
| Hand-calc PITI anchor reproduces ($3,760.34 Conv30 @ 20% DP)                      | inspect YOUR FIT matrix row 1                                                                        | `**$3,760/mo ✓**` (rounded display) in preferred-DP column                   | ✓ PASS |
| Hand-calc first-year interest anchor ($32,335.43 Conv30)                          | inspect TAX section                                                                                  | `First-year deductible interest (Conv30): $32,335.43` ✓                      | ✓ PASS |
| Preferred-DP column bold + annotated                                              | inspect YOUR FIT matrix header                                                                       | `**20% DP** *(your DP)*` ✓                                                   | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s)         | Description                                                              | Status      | Evidence                                                                                       |
| ----------- | ---------------------- | ------------------------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------------------- |
| MODE-01     | 15-01, 15-04           | URL-pin routing to `property` mode                                       | ✓ SATISFIED | `modes/property.md` lines 6-23 + 8 tests in `tests/test_skill_routing.py` all GREEN.            |
| MODE-02     | 15-01, 15-04           | SKILL.md cross-references `modes/property.md`; ≤ 4500 token budget       | ✓ SATISFIED | SKILL.md lines 25/40/138 + token count = 3796.                                                 |
| MODE-03     | 15-01, 15-03           | Orchestrator runs end-to-end; always-exit-0 with envelope                | ✓ SATISFIED | 11 tests in `tests/test_property_analyze_cli.py` GREEN + live smoke run produces real report. |
| RPRT-01     | 15-01, 15-02           | Markdown emitter to `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md`; 6 sections | ✓ SATISFIED | 15 tests in `tests/test_property_report.py` GREEN + live report has all 6 sections.            |
| RPRT-02     | 15-01, 15-02           | 6 italic citation footers; orchestrator-only; re-runnable                | ✓ SATISFIED | Live report `grep -c "^\*Computed by:"` = 6; each footer is full re-runnable invocation.       |

**Orphaned requirements:** None — REQUIREMENTS.md `[x]` checklist marks all 5 requirements closed (lines 40-42, 50-51).

### Anti-Patterns Found

| File                                       | Line | Pattern                                                              | Severity | Impact                                                                                                                                                                            |
| ------------------------------------------ | ---- | -------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.planning/REQUIREMENTS.md`                | 76   | Tracking table row `\| MODE-01..03 \| Phase 15 (property-mode) \| Pending \|` | ℹ️ Info  | Docs-staleness: checklist at lines 40-42 says `[x]` closed but tracking table still says `Pending`. Cosmetic only — no functional gap. Recommend table update in follow-up commit. |
| `.planning/REQUIREMENTS.md`                | 78   | Tracking table row `\| RPRT-01..02 \| Phase 15 \| Pending \|`         | ℹ️ Info  | Same as above for RPRT requirements.                                                                                                                                              |
| `lib/rules/fha_mip 2.py`, `fha_mip 3.py`   | N/A  | iCloud-sync duplicate files in `lib/rules/`                          | ℹ️ Info  | Unrelated to Phase 15 (explicitly called out in verification objective). Causes 2 unrelated test failures: `test_phase2_smoke.py::test_filesystem_predicate_count_matches_expected` and `test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring[fha_mip 2/3]`. Recommend: delete the duplicates from the working tree (or extend `.gitignore`/iCloud-exclude rules). NOT a Phase 15 regression. |

No blockers, no warnings tied to Phase 15 deliverables.

### Human Verification Required

None. Phase 15 is fully verifiable programmatically:
- 34 unit/integration tests cover all 5 requirements.
- 1 eval prompt produces real numeric oracle match.
- Live orchestrator smoke run produces a real markdown report.

### Git Hygiene

- 14 atomic commits per task — clean fan-out per plan (15-01..15-05; feat + docs pattern).
- **No `Co-Authored-By` lines, no `🤖 Generated`, no Claude/Anthropic AI attribution** in any Phase 15 commit message (per global CLAUDE.md rule). The substring "anthropic" appears only inside code comments referencing the pip package exclusion list ("no requests/urllib/httpx/anthropic"), NOT in commit attribution.

```
71a6dd5 docs(15-05): complete property-analysis-01 eval prompt + oracle reconciliation plan
d98661f feat(15-05): add property-analysis-01 eval prompt + reconcile oracle against orchestrator
380e6a6 docs(15-04): complete URL-pin modes/property.md + SKILL.md Row 0 plan
4b5067c feat(15-04): insert Row 0 (URL-pin) into SKILL.md routing + precedence
7bbc0b7 feat(15-04): add modes/property.md URL-pin mode body
50d7b0f docs(15-03): complete property_analyze.py orchestrator plan
f95b321 feat(15-03): ship property_analyze.py orchestrator + fix example yamls for Phase 14 contract
6359fbc feat(15-03): extend household.example.yml with Phase 15 liquid_reserves + preferred_down_payment_pct
fd40014 docs(15-02): complete lib/property_report.py formatter plan
f420973 feat(15-02): ship lib/property_report.py AnalysisReport -> markdown formatter
3947357 docs(15-01): complete Wave 0 test scaffolding plan
4b151b4 test(15-01): add Wave 0 RED stubs for CLI orchestrator + skill routing (MODE-01, MODE-02, MODE-03)
2391b3f test(15-01): add Wave 0 RED stubs for lib.property_report.render() (RPRT-01, RPRT-02)
ea3715d feat(15-01): add synthetic property fixture + HTML stub + eval oracle
```

## VERIFICATION GAPS

**None tied to Phase 15.** Two pre-existing repo-level cleanups noted (informational):

1. **iCloud-sync duplicate files in `lib/rules/`** (severity: info; unrelated to Phase 15)
   - Files: `lib/rules/fha_mip 2.py`, `lib/rules/fha_mip 3.py` (space-separated duplicates created by iCloud Drive sync)
   - Impact: Two unrelated test failures in the FULL repo suite — `tests/test_rules/test_phase2_smoke.py::test_filesystem_predicate_count_matches_expected` and `tests/test_rules/test_citation_coverage.py` (+ the mutation harness that wraps it).
   - Remediation: `rm "lib/rules/fha_mip 2.py" "lib/rules/fha_mip 3.py"` and add a `.gitignore` entry (`*.py \?\ *.py`) or an iCloud-exclude rule.
   - **Explicitly out of scope for Phase 15** per verification objective.

2. **REQUIREMENTS.md tracking table out of sync with checklist** (severity: info; cosmetic)
   - Lines 76, 78 show `Pending` while the canonical `[x]` checklist (lines 40-42, 50-51) shows closed.
   - Remediation: 1-line edit to flip both rows to `Closed`. Recommend in a follow-up housekeeping commit (or absorb into Phase 16 docs sweep).

Neither item blocks proceeding to Phase 16. Phase 15 goal is **fully achieved**.

---

_Verified: 2026-05-20_
_Verifier: gsd-verifier (goal-backward verification; FORCE adversarial stance)_
