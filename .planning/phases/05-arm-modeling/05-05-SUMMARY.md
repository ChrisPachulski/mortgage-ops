---
phase: 05
plan: 05
subsystem: arm-modeling
tags:
  - phase-05
  - arm-modeling
  - documentation
  - selling-guide-citations
  - arm-09
  - roadmap-sc-5
requirements:
  - ARM-09
dependency-graph:
  requires:
    - 05-00
    - 05-02
    - 05-03
  provides:
    - references/arm-mechanics.md
    - ARMTerms docstring citation (ROADMAP SC-5)
    - ARM-09 closure
    - SC-5 closure
  affects:
    - lib/arm.py (ARMTerms docstring +1 citation block)
    - tests/test_arm.py (3 ARM-09 stubs flipped)
tech-stack:
  added: []
  patterns:
    - "D-08 [REVISED 2026-04-30] citation block: 7 sections (reset month convention, cap precedence, floor algebra, quantization, neg-am out-of-scope, index_series_id semantics, teaser-ARM lifetime cap base)"
    - "Regression-guard test pattern: forbidden-token assertions on B5-3.5-01 + §4404 prevent accidental revert to broken legacy citations"
    - "Docstring-as-discoverability: ARMTerms.__doc__ embeds load-bearing 'references/arm-mechanics.md' token grep-discoverable from help(ARMTerms) + Phase 11 amortization-agent context"
    - "Annual revalidation cadence: appendix table records last-verified date per URL"
key-files:
  created:
    - references/arm-mechanics.md
  modified:
    - lib/arm.py
    - tests/test_arm.py
decisions:
  - "Rule 1 deviation: rephrased the 'Citation correction note' callout to OMIT the literal forbidden tokens (B5-3.5-01, §4404) inline. The plan's literal action body included the broken tokens in prose, but the Task 3 forbidden_fragments assertion forbids them anywhere in the file. Rephrased to 'a Fannie subsection in the B5 chapter' / 'a four-digit Freddie section number that is now stale' — preserves historical narrative without violating the regression test."
  - "Rule 1 deviation: rephrased two 'CLAUDE.md' references in Sections 3 + 4 of the doc to 'project root coding-standards file, money discipline section'. The plan's literal action body contained 'CLAUDE.md money discipline' which would be matched (case-insensitively) by the 'no AI attribution' acceptance criterion grep -ci 'claude' returns 0. The references in question were to the project's coding-standards file (not AI attribution), but the criterion is strict; rephrasing preserves meaning and discoverability while honoring the literal acceptance gate."
metrics:
  duration: "~7 minutes"
  completed: "2026-04-30"
  tasks: 4
  commits: 3
  tests-flipped: 3
  lines-added: 261
---

# Phase 5 Plan 05: References + Docstring Summary

`references/arm-mechanics.md` shipped at repo root with the 7 D-08 [REVISED 2026-04-30] sections (reset month convention, cap precedence, floor algebra, quantization, neg-am out-of-scope, `index_series_id` semantics, teaser-ARM lifetime cap base). All citation URLs use the verified-correct sections (Fannie B2-1.4-02, Freddie 6302.7(b) + SOFR-Indexed-ARMs product page, CFPB §1951, AmericU 5/6 disclosure) and explicitly do NOT carry forward the broken legacy citations (Fannie B5-3.5-01 returns 404; Freddie §4404 is stale). `lib/arm.py` ARMTerms docstring extended with a one-line citation pointer per ROADMAP SC-5, providing grep-discoverability from `help(ARMTerms)` + Phase 11 amortization-agent context. 3 ARM-09 Wave-0 stubs in `tests/test_arm.py` flipped to passing tests; xfail count drops from 14 to 11.

## What Shipped

### references/arm-mechanics.md (NEW, 195 lines)

Pure Markdown reference doc at repo root (Phase 10 will mirror or symlink into `.claude/skills/mortgage-ops/references/`).

7 sections per D-08 [REVISED 2026-04-30]:

1. **Reset Month Convention** — first-reset = month 61 (5/1, 5/6) / month 85 (7/1) / month 121 (10/1); second reset on 5/6 = month 67. Ties to PITFALL 5 + ROADMAP SC-3. Cites Fannie B2-1.4-02 + Freddie 6302.7(b) + Freddie SOFR-Indexed-ARMs page + AmericU 5/6 disclosure.

2. **Cap Precedence** — initial_cap at first reset (epoch_idx == 1); periodic_cap at every subsequent reset; lifetime_cap measured against `note_rate`. Binding ceiling = `min(applicable_cap_ceiling, lifetime_ceiling)`. `applied_cap` Literal records which constraint bound (D-10 citation-coverage). Cites Fannie B2-1.4-02 + Freddie 6302.7(b) + CFPB §1951.

3. **Floor Algebra** — `effective_floor = max(margin_bps/10000, floor_rate)`; `floor_rate` REQUIRED on ARMTerms (D-02; no default; "fail loud, no inference"). Quotes Fannie B2-1.4-02 verbatim ("interest rates may never decrease to less than the ARM's margin").

4. **Quantization** — 6-decimal-place `lib.money.quantize_rate` per Phase 4 D-09 / Phase 5 D-14 promoted helper. Engine choice; not regulator-mandated.

5. **Negative Amortization OUT of Scope** — Phase 5 ships fully-amortizing ARMs only per CONTEXT.md D-12. Option ARM / payment-cap ARMs explicitly deferred.

6. **`index_series_id` Semantics** — metadata-only string in v1; Phase 12 maps to FRED MCP `MORTGAGE30US`. Free-form string until Phase 12 may tighten to Literal/enum.

7. **Teaser-ARM Lifetime Cap Base — Engine Choice (LM-3)** — engine uses `note_rate` (post-teaser) as lifetime base, NOT `loan.annual_rate` (teaser). For a 3% teaser with 5% note + 5% lifetime cap, ceiling = 10% (engine) not 8% (CFPB §1951 alternative reading). Discloses CFPB phrasing as a consumer-explainer simplification; locks engine convention as industry-aligned with Fannie B2-1.4-02 worked examples.

Plus appendix table with last-verified date per URL for annual revalidation cadence.

**Verified URL fragments present:**

- `selling-guide.fanniemae.com/sel/b2-1.4-02` (Fannie ARMs section, last updated 2025-12-10)
- `sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms` (Freddie SOFR-Indexed ARMs product page)
- `consumerfinance.gov/ask-cfpb/what-are-rate-caps` (CFPB Ask CFPB §1951 explainer)
- `5_6-SOFR-ARM-Program-Disclosure` (AmericU 5/6 SOFR ARM 2/1/5 caps PDF)

**Forbidden legacy fragments absent (regression guard):**

- `B5-3.5-01` — broken; returns 404 (RESEARCH §Q4 verified)
- `§4404` — stale Freddie section number (RESEARCH §Q4 verified)

### lib/arm.py ARMTerms docstring (MODIFIED, +4/-3 lines)

Added a 3-line citation block at the head of the ARMTerms class docstring (before the field-schema description) containing:

> See references/arm-mechanics.md for reset/cap/floor convention, including
> Selling Guide citations (Fannie B2-1.4-02, Freddie 6302.7(b)), CFPB §1951,
> and the AmericU 5/6 SOFR ARM disclosure (Phase 5 ARM-09 + ROADMAP SC-5).

Load-bearing token `references/arm-mechanics.md` is what `test_arm_terms_docstring_cites_arm_mechanics` greps for. Engine code (build_arm_schedule, _compute_new_rate, _compute_reset_triggers) untouched.

### tests/test_arm.py — 3 ARM-09 stubs flipped (xfail → pass)

1. **`test_arm_mechanics_doc_sections_present`** — file-existence + 7 section-token check (case-insensitive) + at least 7 `## ` headings.

2. **`test_arm_terms_docstring_cites_arm_mechanics`** — ARMTerms.__doc__ contains `references/arm-mechanics.md` token + at least one of (B2-1.4-02 / Fannie / Selling Guide).

3. **`test_arm_mechanics_citations`** — required URL fragments present; forbidden legacy fragments (B5-3.5-01, §4404) absent; Freddie 6302.7(b) section cited.

xfail count: **14 → 11** (3 ARM-09 stubs flipped).

## Test Results

| Suite | Pre-Plan | Post-Plan | Delta |
|-------|----------|-----------|-------|
| Full suite passed | 419 | 422 | +3 (ARM-09 stubs flipped) |
| Full suite xfailed | 14 | 11 | -3 |
| Full suite skipped | 4 | 4 | 0 |
| Full suite failed | 0 | 0 | 0 |
| Full suite errors | 0 | 0 | 0 |
| `tests/test_amortize.py` (Phase 3) | 42 passed | 42 passed | 0 (preserved) |
| `tests/test_affordability.py` (Phase 4) | 78 passed + 4 skipped | 78 passed + 4 skipped | 0 (preserved) |

> Plan's predicted final count was 421; actual is 422. The +1 delta vs plan prediction is because the plan was authored against an old baseline of 418 passed (predating one upstream test added in Wave 4b). The +3 delta from this plan is exactly as predicted.

`mypy --strict` clean across all 11 Phase 5 files (per-file invocation, matching project pre-commit hook config; combined invocation surfaces a pre-existing mypy module-name collision on `scripts/_cli_helpers.py` unrelated to this plan).

`ruff check` + `ruff format --check` clean across all 11 files.

## Acceptance Gates — All Pass

- references/arm-mechanics.md exists with 195 lines (≥ 120 required).
- 8 `## ` headings (≥ 7 required: 7 D-08 sections + appendix).
- All 7 D-08 [REVISED] section tokens present (reset month convention, cap precedence, floor algebra, quantization, negative amortization, index_series_id, teaser).
- All 4 verified URL fragments present (Fannie B2-1.4-02, Freddie SOFR-Indexed ARMs, CFPB ask-cfpb rate-caps, AmericU 5/6 disclosure PDF).
- Both forbidden legacy tokens absent (B5-3.5-01, §4404).
- Zero AI-attribution tokens (co-authored, claude, anthropic) per CLAUDE.md global rule.
- ARMTerms.__doc__ contains 'references/arm-mechanics.md' load-bearing string.
- ARMTerms.__doc__ contains at least one regulatory citation (B2-1.4-02 + Fannie + Selling Guide all present).
- 3 ARM-09 stubs pass.
- xfail count = 11 (was 14).
- Full suite green; Phase 3 + Phase 4 baselines preserved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Citation Hygiene] Rephrased Citation Correction Note to omit literal forbidden tokens**

- **Found during:** Task 1 (immediately after first Write of references/arm-mechanics.md)
- **Issue:** The plan's literal action body included a "Citation correction note" callout that quoted the forbidden tokens `B5-3.5-01` and `§4404` inline as part of the historical narrative ("originally cited Fannie §B5-3.5-01 ... and Freddie §4404"). Task 3's `test_arm_mechanics_citations` asserts these tokens MUST NOT appear ANYWHERE in the file (regression guard). Keeping the literal tokens would have failed the forbidden_fragments assertion in Task 3.
- **Fix:** Rephrased the correction note to describe the legacy citations without naming them: "cited a Fannie subsection in the B5 chapter (which returned 404; that section group is about VA-related underwriting, not ARMs) and a four-digit Freddie section number that is now stale". Added a final sentence noting the forbidden tokens are deliberately omitted to support the regression test.
- **Files modified:** references/arm-mechanics.md
- **Commit:** b01a8b2

**2. [Rule 1 - AI-Attribution Hygiene] Rephrased two CLAUDE.md references in Sections 3 + 4**

- **Found during:** Task 1 (initial acceptance-criteria sweep after first Write)
- **Issue:** The plan's literal action body referenced "CLAUDE.md money discipline" twice. The Task 1 acceptance criterion `grep -c -i 'claude' references/arm-mechanics.md returns 0` is case-insensitive and would match `CLAUDE.md` even though the references are to the project's coding-standards file (not AI attribution).
- **Fix:** Rephrased both occurrences to "project root coding-standards file, money discipline section". Preserves the cross-reference intent without tripping the case-insensitive grep gate.
- **Files modified:** references/arm-mechanics.md
- **Commit:** b01a8b2

### Plan-Prediction Variance (informational, not a deviation)

- Plan predicted "Final expected: 421 passed". Actual: 422 passed. The plan was authored against a stale baseline of 418 passed; the actual pre-plan baseline (after Wave 4b) was 419 passed. This plan's intended +3 delta (ARM-09 stubs flipped) was achieved exactly. No remediation needed.

## Closure Status

- **ARM-09** — CLOSED. references/arm-mechanics.md ships with corrected D-08 [REVISED 2026-04-30] citations; 3 ARM-09 stubs pass; forbidden-legacy regression guard active.
- **ROADMAP SC-5** — CLOSED. ARMTerms docstring cites references/arm-mechanics.md via load-bearing token; reciprocal links verified.
- **Phase 5 Wave 5 complete.** Wave 6 (Plan 05-06: fixtures + oracle) is the only remaining wave to close Phase 5.

## Citation Correction History

D-08 was originally locked with citations Fannie B5-3.5-01 + Freddie §4404. RESEARCH §Q4 (recorded 2026-04-30) verified that B5-3.5-01 returns 404 (the B5-3 chapter group is about VA-related underwriting, not ARMs) and §4404 is a stale section number (modern Freddie URLs use §6302.7(b) + Chapter 4203). D-08 [REVISED 2026-04-30] locked the corrected citations: Fannie B2-1.4-02 (last updated 2025-12-10), Freddie 6302.7(b) + SOFR-Indexed-ARMs product page, CFPB §1951, AmericU 5/6 disclosure. This plan ships the corrected citations verbatim and adds a regression-guard test asserting the broken legacy tokens cannot reappear.

## Commits

- `b01a8b2` — `docs(05-05): add references/arm-mechanics.md with corrected D-08 citations`
- `35e3bc5` — `docs(05-05): cite references/arm-mechanics.md from ARMTerms docstring`
- `75b0dbc` — `test(05-05): flip 3 ARM-09 doc/citation stubs to passing`

(Final SUMMARY.md commit follows.)

## Self-Check: PASSED

- references/arm-mechanics.md: FOUND
- lib/arm.py: FOUND
- tests/test_arm.py: FOUND
- .planning/phases/05-arm-modeling/05-05-SUMMARY.md: FOUND
- Commit b01a8b2: FOUND
- Commit 35e3bc5: FOUND
- Commit 75b0dbc: FOUND
