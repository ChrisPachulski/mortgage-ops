---
phase: 10
plan: 04
type: execute
wave: 4
depends_on:
  - "10-00"
  - "10-02"
files_modified:
  - .claude/skills/mortgage-ops/references/amortization-formulas.md
  - .claude/skills/mortgage-ops/references/apr-reg-z.md
  - .claude/skills/mortgage-ops/references/arm-mechanics.md
  - .claude/skills/mortgage-ops/references/refi-npv.md
  - .claude/skills/mortgage-ops/references/affordability-rules.md
  - .claude/skills/mortgage-ops/references/gse-limits.md
  - .claude/skills/mortgage-ops/references/mip-pmi.md
  - .claude/skills/mortgage-ops/references/tax-deductibility.md
  - .claude/skills/mortgage-ops/references/spreadsheet-conventions.md
  - .claude/skills/mortgage-ops/assets/.gitkeep
autonomous: true
requirements:
  - SKLL-08
  - SKLL-09
tags:
  - phase-10
  - claude-skill
  - references
  - skll-08
  - skll-09
must_haves:
  truths:
    - "All 9 reference files exist under .claude/skills/mortgage-ops/references/ with the EXACT filenames specified by ROADMAP SC-5"
    - ".claude/skills/mortgage-ops/references/arm-mechanics.md is byte-identical to <repo>/references/arm-mechanics.md (Phase 5 source-of-truth COPY per 10-PATTERNS CRITICAL #4 — keeps Phase 5 docstring path valid)"
    - ".claude/skills/mortgage-ops/references/refi-npv.md is byte-identical to <repo>/references/refi-npv.md (Phase 6 SHIPPED per STATE.md; mirrors arm-mechanics drift-protection pattern). Wave 5 ships byte-equality drift test."
    - ".claude/skills/mortgage-ops/references/apr-reg-z.md is byte-identical to <repo>/references/apr-reg-z.md (Phase 7 SHIPPED per STATE.md; mirrors arm-mechanics drift-protection pattern). Wave 5 ships byte-equality drift test."
    - "Phase 6 / Phase 7 / Phase 8 references are COMPLETE per STATE.md — no marker stubs remain. SKLL-08 closes fully (not partially) at Phase 10 ship."
    - "Phase 2-shipped reference content (gse-limits, mip-pmi, tax-deductibility) lifts from already-completed YAMLs (data/reference/*.yml from REF-01..07 closed)"
    - "amortization-formulas.md derives from Phase 3 numpy-financial wraps + 4 golden derivations from CLAUDE.md FND-09 oracle list"
    - "affordability-rules.md derives from Phase 4 lib/affordability.py (already shipped) + Phase 2 predicates (lib/rules/*.py)"
    - "spreadsheet-conventions.md derives from numpy-financial bug notes #130 + #131 (cited in CLAUDE.md ## Technology Stack)"
    - ".claude/skills/mortgage-ops/assets/.gitkeep exists as directory placeholder (per Phase 5 .gitkeep idiom + RESEARCH §b webapp-testing exemplar layout)"
  artifacts:
    - path: ".claude/skills/mortgage-ops/references/arm-mechanics.md"
      provides: "Phase 5 ARM mechanics doc — byte-identical COPY of <repo>/references/arm-mechanics.md"
      contains: "5/1"
    - path: ".claude/skills/mortgage-ops/references/refi-npv.md"
      provides: "Phase 6 source-of-truth byte-identical COPY of <repo>/references/refi-npv.md (Phase 6 SHIPPED; mirror drift-protection pattern from arm-mechanics)"
      contains: "Refinance NPV"
    - path: ".claude/skills/mortgage-ops/references/apr-reg-z.md"
      provides: "Phase 7 source-of-truth byte-identical COPY of <repo>/references/apr-reg-z.md (Phase 7 SHIPPED; mirror drift-protection pattern from arm-mechanics)"
      contains: "Estimated APR"
    - path: ".claude/skills/mortgage-ops/references/amortization-formulas.md"
      provides: "Phase 3 numpy-financial wrap formulas + 4 golden derivations"
      min_lines: 60
    - path: ".claude/skills/mortgage-ops/references/affordability-rules.md"
      provides: "Phase 4 DTI/LTV/CLTV/PITI rules + reverse-affordability derivation + blocker precedence (D-11)"
      min_lines: 60
    - path: ".claude/skills/mortgage-ops/references/gse-limits.md"
      provides: "Phase 2 conforming-limits-2026 + fha-limits-2026 explainer"
      min_lines: 40
    - path: ".claude/skills/mortgage-ops/references/mip-pmi.md"
      provides: "Phase 2 fha-mip-rates + RUL-04/RUL-05 explainer (HPA 78%/80% termination + UFMIP)"
      min_lines: 40
    - path: ".claude/skills/mortgage-ops/references/tax-deductibility.md"
      provides: "Phase 2 irs-pub936 + Phase 6 D-09 after-tax mode (cross-link to references/refi-npv.md which is byte-lifted in Task 2)"
      min_lines: 40
    - path: ".claude/skills/mortgage-ops/references/spreadsheet-conventions.md"
      provides: "numpy-financial bug #130 + #131 + Excel sign convention + biweekly rounding"
      min_lines: 30
    - path: ".claude/skills/mortgage-ops/assets/.gitkeep"
      provides: "Empty directory placeholder per webapp-testing exemplar layout"
  key_links:
    - from: ".claude/skills/mortgage-ops/references/arm-mechanics.md"
      to: "<repo>/references/arm-mechanics.md"
      via: "byte-equality COPY (per 10-PATTERNS CRITICAL #4); Wave 5 ships drift-protection test"
      pattern: "byte-identical"
    - from: "modes/refinance.md"
      to: "references/refi-npv.md"
      via: "progressive-disclosure trigger (modes/refinance.md lists refi-npv.md as related ref)"
      pattern: "refi-npv"
    - from: "Phase 6 lib/refinance.py docstring"
      to: ".claude/skills/mortgage-ops/references/refi-npv.md"
      via: "Phase 6 NPV content is reachable via the byte-lifted skill-folder reference (project-root copy is the citation target; both copies are byte-equal per Wave 5 drift test)"
      pattern: "byte-equal-mirror"
---

<objective>
Ship the 9 reference files inside `.claude/skills/mortgage-ops/references/` plus the `.claude/skills/mortgage-ops/assets/.gitkeep` directory placeholder.

Per 10-RESEARCH §(j) source-mapping table:
- 7 files have FULL CONTENT now (Phase 2/3/4/5 source phases all shipped):
  - amortization-formulas.md (from Phase 3 + FND-09 oracles)
  - arm-mechanics.md (BYTE-IDENTICAL COPY of <repo>/references/arm-mechanics.md per 10-PATTERNS CRITICAL #4)
  - affordability-rules.md (from Phase 4 lib/affordability.py + Phase 2 predicates)
  - gse-limits.md (from REF-01 + REF-02 YAMLs, both shipped)
  - mip-pmi.md (from REF-03 + RUL-04 + RUL-05, all shipped)
  - tax-deductibility.md (Phase 2 portion from REF-07 + RUL-11 shipped; Phase 6 portion CROSS-LINKS to byte-lifted references/refi-npv.md)
  - spreadsheet-conventions.md (numpy-financial bugs #130 + #131 from CLAUDE.md)
- 2 files lifted byte-identically from project-root references/ — Phase 6/7
  are COMPLETE per STATE.md, so refi-npv.md (~630 lines) and apr-reg-z.md
  (~523 lines) ship as full-content byte-equal mirrors (NOT marker stubs).
  This mirrors the arm-mechanics drift-protection pattern from prior phases;
  Wave 5 byte-equality tests close the loop.

Closes SKLL-08 (9 reference files exist) + supports SKLL-09 (progressive disclosure — references load on demand from these files, not eagerly from SKILL.md).

Purpose: Without references/ Claude has no source for "explain the math" / "why does APR work that way?" / "what's the conforming limit?" follow-up questions. Loading on demand keeps SKILL.md within budget.

Output: 9 reference files (most ~40-100 lines authored fresh; arm-mechanics.md + refi-npv.md + apr-reg-z.md byte-lifted from project-root references/ —
~325 / ~630 / ~523 lines respectively, drift-protected by Wave 5 byte-equality
tests).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/10-claude-skill/10-PATTERNS.md
@.planning/phases/10-claude-skill/10-RESEARCH.md
@.planning/phases/10-claude-skill/10-UI-SPEC.md
@CLAUDE.md
@references/arm-mechanics.md
@lib/amortize.py
@lib/affordability.py
@data/reference/conforming-limits-2026.yml
@data/reference/fha-limits-2026.yml
@data/reference/fha-mip-rates.yml
@data/reference/irs-pub936.yml

<interfaces>
LOCKED DECISIONS:
- D-08: RETIRED at Phase 10 ship per Plan 10-01 — all 7 calc scripts and the
  Phase 6/7 reference docs were shipped before Phase 10 landed. Phase 10 lifts
  them byte-identically into the skill folder. No further "ship to root then
  Phase 10 relocates" or "marker stub then Phase N backfills" pattern remains.

10-PATTERNS CRITICAL #4 — arm-mechanics.md strategy:
> COPY (do not symlink, do not move). Leave the original at <repo>/references/arm-mechanics.md (Phase 5 docstring at lib/arm.py cites that path). Add a Wave 5 byte-equality test as drift protection.

10-RESEARCH §(j) per-reference content sources (verbatim table):
| # | Reference filename | Content source | Status of source |
| 1 | amortization-formulas.md | Phase 3 numpy-financial wraps + Phase 1 FND-09 4 golden derivations | VERIFIED Phase 3 complete |
| 2 | apr-reg-z.md | Phase 7 references/apr-reg-z.md | VERIFIED Phase 7 complete (STATE.md) → BYTE-EQUAL LIFT |
| 3 | arm-mechanics.md | Phase 5 references/arm-mechanics.md (byte-identical COPY) | VERIFIED <repo>/references/arm-mechanics.md exists |
| 4 | refi-npv.md | Phase 6 references/refi-npv.md | VERIFIED Phase 6 complete (STATE.md) → BYTE-EQUAL LIFT |
| 5 | affordability-rules.md | Phase 4 lib/affordability.py + Phase 2 predicates | VERIFIED Phase 4 complete |
| 6 | gse-limits.md | Phase 2 conforming-limits-2026.yml + fha-limits-2026.yml | VERIFIED REF-01 + REF-02 complete |
| 7 | mip-pmi.md | Phase 2 fha-mip-rates.yml + lib/rules/conventional_pmi.py + lib/rules/fha_mip.py | VERIFIED REF-03 + RUL-04 + RUL-05 complete |
| 8 | tax-deductibility.md | Phase 2 irs-pub936.yml + lib/rules/irs_pub936.py + Phase 6 D-09 after-tax mode (cross-link via references/refi-npv.md) | VERIFIED Phase 2 + Phase 6 both complete |
| 9 | spreadsheet-conventions.md | numpy-financial bugs #130 + #131 + Excel sign convention | VERIFIED CLAUDE.md cites both bugs |

**Byte-equal lift pattern:** For the three lifted files (arm-mechanics.md,
refi-npv.md, apr-reg-z.md), use `cp` from the project-root references/
counterpart. No template, no editing. Wave 5 drift tests assert exact
byte equality.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Copy arm-mechanics.md from project root → skill folder (byte-identical, NOT symlink)</name>
  <files>.claude/skills/mortgage-ops/references/arm-mechanics.md</files>
  <read_first>
    <repo>/references/arm-mechanics.md (full file) — source of byte-equal copy;
    10-PATTERNS CRITICAL #4 — copy-not-symlink rationale
  </read_first>
  <action>
COPY `<repo>/references/arm-mechanics.md` → `.claude/skills/mortgage-ops/references/arm-mechanics.md` byte-identically.

Use `cp` (not `ln -s`, not `git mv`). The PROJECT-ROOT file STAYS — Phase 5 lib/arm.py docstring cites `references/arm-mechanics.md` (the project-root path) and that citation must remain valid.

Steps:
```
cp references/arm-mechanics.md .claude/skills/mortgage-ops/references/arm-mechanics.md
diff references/arm-mechanics.md .claude/skills/mortgage-ops/references/arm-mechanics.md
# diff MUST exit 0 (no differences)
```

DO NOT modify either copy in this task. Wave 5 will ship a drift-protection test (`test_arm_mechanics_skill_mirror_in_sync`) that asserts byte-equality on every CI run.

DO NOT delete the project-root file.

DO NOT use a symlink (10-PATTERNS CRITICAL #4 forbids — would break portability when skill folder is copied to another machine).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f references/arm-mechanics.md &amp;&amp; test -f .claude/skills/mortgage-ops/references/arm-mechanics.md &amp;&amp; diff references/arm-mechanics.md .claude/skills/mortgage-ops/references/arm-mechanics.md &amp;&amp; test ! -L .claude/skills/mortgage-ops/references/arm-mechanics.md</automated>
  </verify>
  <acceptance_criteria>
- Both files exist (project root + skill folder)
- `diff` exits 0 (byte-identical)
- The skill-folder file is NOT a symlink (`test ! -L` exits 0)
- Project-root file unchanged (mtime preserved if cp -p used; or content unchanged at minimum)
  </acceptance_criteria>
  <done>
    arm-mechanics.md byte-identical copy in skill folder; Phase 5 docstring path remains valid; symlink avoided.
  </done>
</task>

<task type="auto">
  <name>Task 2: Lift refi-npv.md + apr-reg-z.md from project root → skill folder (byte-identical, mirroring arm-mechanics drift-protection)</name>
  <files>.claude/skills/mortgage-ops/references/refi-npv.md, .claude/skills/mortgage-ops/references/apr-reg-z.md</files>
  <read_first>
    <repo>/references/refi-npv.md (full file ~630 lines from Phase 6) — source of byte-equal copy;
    <repo>/references/apr-reg-z.md (full file ~523 lines from Phase 7) — source of byte-equal copy;
    10-PATTERNS CRITICAL #4 — copy-not-symlink rationale (also applies to refi-npv + apr-reg-z);
    STATE.md — confirms Phase 6 and Phase 7 COMPLETE (refi-npv.md and apr-reg-z.md exist with full content)
  </read_first>
  <action>
PER STATE.md: Phase 6 (refinance NPV) and Phase 7 (estimated APR) are COMPLETE. Their reference docs (`<repo>/references/refi-npv.md` and `<repo>/references/apr-reg-z.md`) ship with full content (~630 and ~523 lines respectively). The earlier draft of this plan treated them as marker stubs (anticipating Phase 6/7 had not yet shipped), but that scaffolding is obsolete.

Lift each file BYTE-IDENTICALLY into the skill folder, mirroring the arm-mechanics drift-protection pattern. The PROJECT-ROOT copies STAY — Phase 6 lib/refinance.py and Phase 7 lib/apr.py docstrings cite the project-root paths, and those citations must remain valid.

Steps:

```
cp references/refi-npv.md   .claude/skills/mortgage-ops/references/refi-npv.md
cp references/apr-reg-z.md  .claude/skills/mortgage-ops/references/apr-reg-z.md

diff references/refi-npv.md   .claude/skills/mortgage-ops/references/refi-npv.md
diff references/apr-reg-z.md  .claude/skills/mortgage-ops/references/apr-reg-z.md
# Both diffs MUST exit 0 (no differences)
```

Use `cp` (not `ln -s`, not `git mv`). DO NOT modify either copy in this task. Wave 5 will ship TWO new drift-protection tests (`test_refi_npv_skill_mirror_in_sync` + `test_apr_reg_z_skill_mirror_in_sync`) that assert byte-equality on every CI run, parallel to the existing `test_arm_mechanics_skill_mirror_in_sync` test.

DO NOT delete the project-root files (`<repo>/references/refi-npv.md` + `<repo>/references/apr-reg-z.md` STAY — Phase 6/7 lib docstrings cite those paths).

DO NOT use a symlink (10-PATTERNS CRITICAL #4 forbids — would break portability when skill folder is copied to another machine).

DO NOT author "FORWARD-LINK MARKER STUB" content for these two files. Earlier draft of this plan did that; the marker-stub strategy is now obsolete because Phase 6/7 are COMPLETE.

After both copies land, the rationale documented in modes/_shared.md or the references themselves should note that the skill-folder copies are byte-equal mirrors with Wave 5 drift protection (analogous to arm-mechanics).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f references/refi-npv.md &amp;&amp; test -f references/apr-reg-z.md &amp;&amp; test -f .claude/skills/mortgage-ops/references/refi-npv.md &amp;&amp; test -f .claude/skills/mortgage-ops/references/apr-reg-z.md &amp;&amp; diff references/refi-npv.md .claude/skills/mortgage-ops/references/refi-npv.md &amp;&amp; diff references/apr-reg-z.md .claude/skills/mortgage-ops/references/apr-reg-z.md &amp;&amp; test ! -L .claude/skills/mortgage-ops/references/refi-npv.md &amp;&amp; test ! -L .claude/skills/mortgage-ops/references/apr-reg-z.md</automated>
  </verify>
  <acceptance_criteria>
- Both files (refi-npv.md, apr-reg-z.md) exist in BOTH project-root references/ AND skill folder references/
- `diff <repo>/references/refi-npv.md .claude/skills/mortgage-ops/references/refi-npv.md` exits 0 (byte-identical)
- `diff <repo>/references/apr-reg-z.md .claude/skills/mortgage-ops/references/apr-reg-z.md` exits 0 (byte-identical)
- Skill-folder copies are NOT symlinks (`test ! -L` exits 0)
- Project-root files unchanged (mtime preserved if cp -p used; or content unchanged at minimum)
- Skill-folder refi-npv.md has ≥ 500 lines (full content lifted, NOT a 25-line marker stub)
- Skill-folder apr-reg-z.md has ≥ 400 lines (full content lifted, NOT a 25-line marker stub)
- Neither skill-folder file contains the substring "Forward-Link Stub" or "load-when-Phase-X-lands" (markers are obsolete)
  </acceptance_criteria>
  <done>
    refi-npv.md + apr-reg-z.md byte-identical copies in skill folder; Phase 6/7 docstring paths remain valid; Wave 5 will ship drift-protection tests for both.
  </done>
</task>

<task type="auto">
  <name>Task 3: Author 5 full-content reference files (amortization-formulas, affordability-rules, gse-limits, mip-pmi, spreadsheet-conventions)</name>
  <files>.claude/skills/mortgage-ops/references/amortization-formulas.md, .claude/skills/mortgage-ops/references/affordability-rules.md, .claude/skills/mortgage-ops/references/gse-limits.md, .claude/skills/mortgage-ops/references/mip-pmi.md, .claude/skills/mortgage-ops/references/spreadsheet-conventions.md</files>
  <read_first>
    10-RESEARCH §(j) source-mapping table for each file;
    CLAUDE.md FND-09 4 golden oracles (Wikipedia $200k, CFPB LE $162k, $400k computed, $200k/15yr computed);
    lib/amortize.py docstrings (Phase 3 numpy-financial wrap citations);
    lib/affordability.py docstrings (Phase 4 DTI/LTV/CLTV/PITI explanations);
    data/reference/conforming-limits-2026.yml (high-level: baseline + ceiling + per-county lookup);
    data/reference/fha-limits-2026.yml (floor + ceiling);
    data/reference/fha-mip-rates.yml (UFMIP + annual MIP per term/LTV/loan-amount);
    data/reference/irs-pub936.yml ($750k cap post-2017; $1M grandfathered);
    lib/rules/conventional_pmi.py (HPA 78% auto + 80% request termination);
    CLAUDE.md ## Technology Stack (numpy-financial bugs #130 + #131)
  </read_first>
  <action>
Create 5 reference files. Each is ~40-100 lines. Each follows the same shape as the existing `<repo>/references/arm-mechanics.md`:
- Brief intro (what this doc covers)
- Section per topic with regulatory/source citations (URLs + effective dates where applicable)
- Worked example or formula derivation
- Cross-references to relevant lib/ / scripts/ files

PER FILE:

`.claude/skills/mortgage-ops/references/amortization-formulas.md` (~80 lines):
- Title: `# Amortization Formulas (Phase 3 numpy-financial wrap)`
- Sections:
  - PMT formula: `PMT = P × r × (1+r)^n / ((1+r)^n − 1)` — derived; cite numpy-financial as the wrapped library
  - 4 golden oracles from CLAUDE.md / FND-09:
    - Wikipedia: $200,000 @ 6.5%/30yr → $1,264.14 (with formula trace)
    - CFPB LE: $162,000 @ 3.875%/30yr → $761.78
    - Computed: $400,000 @ 6.5%/30yr → $2,528.27
    - Computed: $200,000 @ 7%/15yr → $1,797.66
  - Biweekly mode: 26 payments/year via `relativedelta(weeks=2)` (AMRT-03)
  - Extra principal: single, recurring, per-period (AMRT-04 + Phase 3 D-05 uniqueness rider)
  - Final payment cleanup: ensures balance == Decimal("0.00") (AMRT-05 + Phase 3 D-09)
- Cross-refs: `.claude/skills/mortgage-ops/scripts/amortize.py`, `lib/amortize.py`

`.claude/skills/mortgage-ops/references/affordability-rules.md` (~70 lines):
- Title: `# Affordability Rules (Phase 4 DTI/LTV/CLTV/PITI + reverse-affordability)`
- Sections:
  - DTI front-end (housing-only) vs back-end (housing + monthly debts)
  - LTV (loan / property_value) and CLTV (loan + junior_liens / property_value)
  - PITI breakdown: P&I + property tax + insurance + HOA + PMI/MIP
  - Reverse-affordability: `npf.pv(rate, nper, -max_pmt, fv=0)` derives max_loan_amount (AFFD-05 + Phase 4 D-09 round-trip closure)
  - Joint-applicant: lower-mid credit score per Fannie/Freddie convention (AFFD-06)
  - Blocker precedence (Phase 4 D-11): classify → USDA-income → LTV/CLTV → DTI → ATR/QM → VA-residual; first-binding-rule wins; output cites BLOCKED_BY_* citation constant
- Cross-refs: `.claude/skills/mortgage-ops/scripts/affordability.py`, `lib/affordability.py`, `lib/rules/{loan_type,fha_mip,conventional_pmi,va_residual_income,atr_qm,usda}.py`

`.claude/skills/mortgage-ops/references/gse-limits.md` (~50 lines):
- Title: `# GSE Loan Limits (FHFA conforming + FHA + VA + USDA)`
- Sections:
  - FHFA baseline conforming limit (2026): {LOOK UP from data/reference/conforming-limits-2026.yml}
  - High-balance counties: per-county lookup table (cite YAML path; do NOT inline the full 3000-county table)
  - Jumbo: above county high-balance ceiling
  - FHA floor / ceiling (2026): {LOOK UP from data/reference/fha-limits-2026.yml}
  - VA: no statutory cap; entitlement model
  - USDA: rural-area + income limits (115% area median)
  - RUL-01 classify() decision tree summary
- Cross-refs: `data/reference/conforming-limits-2026.yml`, `data/reference/fha-limits-2026.yml`, `lib/rules/loan_type.py`

`.claude/skills/mortgage-ops/references/mip-pmi.md` (~60 lines):
- Title: `# Mortgage Insurance (FHA MIP + Conventional PMI)`
- Sections:
  - FHA UFMIP (Up-Front MIP): {RATE from data/reference/fha-mip-rates.yml}; auto-financed into principal (Phase 4 D-03)
  - FHA annual MIP: per term × LTV × loan-amount tier matrix; LTV>90% = life-of-loan; LTV≤90% = 11-year termination (HUD ML 2023-05)
  - Conventional PMI: HPA 78% auto-termination + 80% request-termination (RUL-05)
  - LPMI alternative (lender-paid PMI; not currently modeled but noted)
- Cross-refs: `data/reference/fha-mip-rates.yml`, `lib/rules/fha_mip.py`, `lib/rules/conventional_pmi.py`

`.claude/skills/mortgage-ops/references/spreadsheet-conventions.md` (~40 lines):
- Title: `# Spreadsheet Conventions (Why Our Numbers Differ from Excel)`
- Sections:
  - Excel PMT sign: returns NEGATIVE for outflow (e.g., -$1,264.14); our wrapper negates to surface positive ($1,264.14)
  - numpy-financial bug #130: PMT fv-sign issue (cite GitHub URL); our wrap handles
  - numpy-financial bug #131: IRR architecture-dependent results (cite); pyxirr fallback for batch NPV per CLAUDE.md ## Technology Stack
  - Decimal vs float: we use `Decimal` from STRINGS, ROUND_HALF_UP, end-of-period quantize; Excel uses 64-bit float
  - Biweekly half-monthly mode: 24 payments/year vs true biweekly 26 payments/year
- Cross-refs: `lib/money.py`, `lib/amortize.py`

EVERY reference file MUST:
- Open with brief intro and "Loaded on demand from SKILL.md per the topic→reference table"
- Include at least one cross-reference to a `lib/` or `data/reference/` source
- End with "**Last reviewed:** {today's date YYYY-MM-DD}" (so future maintainers know when to refresh)

DO NOT include real PII, actual account numbers, or anything from User Layer (config/household.yml). Use placeholder values.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; for f in amortization-formulas affordability-rules gse-limits mip-pmi spreadsheet-conventions; do test -f .claude/skills/mortgage-ops/references/$f.md &amp;&amp; test $(wc -l &lt; .claude/skills/mortgage-ops/references/$f.md) -ge 30; done &amp;&amp; grep -q '2528.27' .claude/skills/mortgage-ops/references/amortization-formulas.md &amp;&amp; grep -q 'reverse-affordability\|reverse_affordability\|reverse affordability' .claude/skills/mortgage-ops/references/affordability-rules.md &amp;&amp; grep -q 'numpy-financial\|numpy_financial' .claude/skills/mortgage-ops/references/spreadsheet-conventions.md</automated>
  </verify>
  <acceptance_criteria>
- All 5 files exist
- amortization-formulas.md ≥ 60 lines, contains "$2,528.27" or "2528.27" (oracle value)
- affordability-rules.md ≥ 60 lines, mentions reverse-affordability + npf.pv
- gse-limits.md ≥ 40 lines, references YAML paths
- mip-pmi.md ≥ 40 lines, mentions UFMIP + annual MIP + HPA
- spreadsheet-conventions.md ≥ 30 lines, mentions numpy-financial bugs
- Each file ends with "Last reviewed: YYYY-MM-DD"
- No User Layer PII
  </acceptance_criteria>
  <done>
    5 full-content reference files written; cite Phase 1-5 + Phase 2 source-of-truth artifacts.
  </done>
</task>

<task type="auto">
  <name>Task 4: Author tax-deductibility.md (PARTIAL — Phase 2 portion full + Phase 6 portion forward-linked)</name>
  <files>.claude/skills/mortgage-ops/references/tax-deductibility.md</files>
  <read_first>
    data/reference/irs-pub936.yml (Phase 2 — REF-07 shipped);
    lib/rules/irs_pub936.py (Phase 2 — RUL-11 shipped);
    10-RESEARCH §(j) row 8 — Phase 6 D-09 after-tax mode forward-link
  </read_first>
  <action>
Create `.claude/skills/mortgage-ops/references/tax-deductibility.md` (~50 lines).

This file is HYBRID: Phase 2 portion ships full content; Phase 6 portion is forward-linked.

Sections:

```markdown
# Tax Deductibility — IRS Pub 936 Mortgage Interest

Loaded on demand from SKILL.md per the topic→reference table.

## Qualified Loan Limit

- **Post-2017 (TCJA):** $750,000 cap on combined acquisition indebtedness
  for primary + secondary residence; interest on debt above the cap is
  not deductible (cited from `data/reference/irs-pub936.yml`).
- **Pre-2017 (grandfathered):** $1,000,000 cap; applies to acquisition
  indebtedness incurred before 2017-12-15.

Source: IRS Publication 936 §"Limits on Home Mortgage Interest Deduction".

## Worksheet Logic (RUL-11)

`lib.rules.irs_pub936.qualified_loan_limit_worksheet(...)` implements the
Pub 936 worksheet. Inputs: total acquisition indebtedness, year-of-origination
flag (post-2017 vs grandfathered). Output: deductible interest cap.

## Points Deductibility (Pub 936)

- Loan origination points on a primary residence purchase loan: deductible
  in the year paid (if itemized + meets safe-harbor tests)
- Refinance points: amortized over loan term (UNLESS proceeds funded
  improvements to the secured residence)

## Phase 6 After-Tax Refi NPV (cross-link)

Per STATE.md, Phase 6 (refinance NPV) is COMPLETE. The after-tax `after_tax_mode`
behavior is implemented in `lib/refinance.py` (or documented as deferred there
with rationale — verify by reading the project-root `references/refi-npv.md`
which is byte-equal to the skill-folder copy lifted by Plan 10-04 Task 2).

The high-level rule:

- Marginal tax rate input (per `modes/_profile.md` user override or per-call
  parameter — see `references/refi-npv.md` for the exact API)
- After-tax interest savings = pre-tax savings × (1 − marginal_rate)
- After-tax NPV = sum of after-tax savings discounted at after-tax discount rate

For the AUTHORITATIVE description, load `references/refi-npv.md` (Phase 6
authored that doc as the source-of-truth for refi NPV conventions).

## Cross-References

- `data/reference/irs-pub936.yml` (REF-07; Phase 2)
- `lib/rules/irs_pub936.py` (RUL-11; Phase 2)
- `lib/refinance.py` + `.claude/skills/mortgage-ops/scripts/refi_npv.py` (Phase 6 SHIPPED; relocated by Plan 10-01)
- `.claude/skills/mortgage-ops/references/refi-npv.md` (Phase 6 reference, byte-lifted by Plan 10-04 Task 2)

**Last reviewed:** 2026-05-02
```
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/skills/mortgage-ops/references/tax-deductibility.md &amp;&amp; grep -q '750,000\|750000\|\$750k' .claude/skills/mortgage-ops/references/tax-deductibility.md &amp;&amp; grep -q 'Phase 6' .claude/skills/mortgage-ops/references/tax-deductibility.md &amp;&amp; grep -q 'D-08\|after.tax' .claude/skills/mortgage-ops/references/tax-deductibility.md</automated>
  </verify>
  <acceptance_criteria>
- File exists at `.claude/skills/mortgage-ops/references/tax-deductibility.md`
- Contains "$750,000" or "750000" or "$750k" (Pub 936 cap)
- Contains "after-tax" or "after tax" (mode reference)
- Contains "Last reviewed: 2026-05-02"
- File ≥ 40 lines
- Cross-references `references/refi-npv.md` (Phase 6 source-of-truth for refi NPV doctrine)
  </acceptance_criteria>
  <done>
    File ships with full Phase 2 content + cross-link to the Phase 6 refi-npv doc (no longer a "Phase 6 not yet shipped" forward-link, since Phase 6 is COMPLETE per STATE.md).
  </done>
</task>

<task type="auto">
  <name>Task 5: Create assets/.gitkeep + final wave verification</name>
  <files>.claude/skills/mortgage-ops/assets/.gitkeep</files>
  <read_first>
    10-RESEARCH §(b) webapp-testing exemplar layout (assets/ directory exists);
    Phase 5 .gitkeep idiom (tests/fixtures/arm/.gitkeep)
  </read_first>
  <action>
PART A — Create `.claude/skills/mortgage-ops/assets/.gitkeep` as a zero-byte file. The webapp-testing canonical exemplar (10-RESEARCH §(b)) has an `assets/` directory; Phase 10 mirrors this layout for future-proofing (Phase 11/12 may add chart-rendering assets, eval-harness expected-output captures, etc.). The .gitkeep ensures the directory commits.

PART B — Final wave verification:

Run a comprehensive structure check to confirm all 9 reference files + the assets dir exist:
```
ls -la .claude/skills/mortgage-ops/references/
ls -la .claude/skills/mortgage-ops/assets/
```

Expected output: 9 .md files in references/; 1 .gitkeep file in assets/.

Run the token-budget audit on each reference file (informational; references have no hard cap but UI-SPEC §"Spacing Scale" suggests 3000-10000 cl100k each):
```
for f in .claude/skills/mortgage-ops/references/*.md; do
  echo -n "$f: "
  python -c "from tests._skill_helpers import count_tokens; print(count_tokens(open('$f').read()), 'tokens')"
done
```

Confirm:
- arm-mechanics.md: matches the project-root file's count (byte-equality)
- refi-npv.md + apr-reg-z.md: full-content lifts (~630 / ~523 lines respectively;
  byte-equal mirrors of project-root references/ counterparts; drift-protected
  by Wave 5 tests).
- Other 5: 500-3000 cl100k tokens each (full content)

DO NOT commit yet — wait for Wave 5 (Plan 10-05) to flip the SKLL-08 + SKLL-09 xfails before committing this wave's content. (Or commit this wave standalone if the orchestrator's execution model prefers per-wave commits — the SKLL-08 xfail will simply remain xfail until Wave 5 flips it.)
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f .claude/skills/mortgage-ops/assets/.gitkeep &amp;&amp; test ! -s .claude/skills/mortgage-ops/assets/.gitkeep &amp;&amp; ls .claude/skills/mortgage-ops/references/*.md | wc -l | grep -q '^9$'</automated>
  </verify>
  <acceptance_criteria>
- `.claude/skills/mortgage-ops/assets/.gitkeep` exists, zero bytes
- Exactly 9 .md files in `.claude/skills/mortgage-ops/references/`
- All 9 expected filenames present: amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions
- arm-mechanics.md byte-equals project-root copy
- Pre-existing test suite still green (no regression from this wave's file additions)
  </acceptance_criteria>
  <done>
    9 reference files + assets/ committed; layout matches webapp-testing exemplar.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| references/arm-mechanics.md drift | Skill copy and project-root copy MUST stay in sync; Wave 5 ships byte-equality drift-protection test |
| references/refi-npv.md + references/apr-reg-z.md drift | Skill copies and project-root copies MUST stay in sync; Wave 5 ships byte-equality drift-protection tests for both (mirrors arm-mechanics pattern) |
| Reference file size | No hard cap, but bloated reference files (>10000 tokens) blow context budget when loaded on demand |
| Reference content authority | Phase 2 source-of-truth YAMLs are normative; reference docs MUST cite back to YAML (not invent rates) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-22 | Tampering (arm-mechanics drift) | byte-equal copy | mitigate | Wave 5 ships `test_arm_mechanics_skill_mirror_in_sync` byte-equality test (10-PATTERNS CRITICAL #4 §5) |
| T-10-23 | Tampering (refi-npv drift) | byte-equal copy | mitigate | Wave 5 ships `test_refi_npv_skill_mirror_in_sync` byte-equality test (mirrors arm-mechanics pattern) |
| T-10-43 | Tampering (apr-reg-z drift) | byte-equal copy | mitigate | Wave 5 ships `test_apr_reg_z_skill_mirror_in_sync` byte-equality test (mirrors arm-mechanics pattern) |
| T-10-50 | Drift between skill-folder mirrors and project-root references | three byte-lifted refs (arm-mechanics + refi-npv + apr-reg-z) | mitigate | Project-root references/ updated without skill-folder mirror update → SKILL.md cites stale content. Wave 5 drift tests (test_*_skill_mirror_in_sync) byte-compare each lifted file pair; CI fails on any divergence |
| T-10-24 | Information Disclosure (regulatory misstatement) | reference content | mitigate | Each reference cites the lib/rules/* predicate which carries the regulatory citation; reviewer cross-checks during plan-check |
| T-10-25 | Tampering (reference file PII leak) | _profile.md placeholder values | mitigate | Task 3 + 4 explicitly forbid real PII; values are placeholders only |
| T-10-26 | DoS (oversized reference loaded on demand) | reference token budget | accept | UI-SPEC §"Spacing Scale" recommends 3000-10000 tokens; only one ref loaded per query (D-09 progressive disclosure); risk bounded |
</threat_model>

<verification>
- 9 reference files exist with correct filenames
- arm-mechanics.md byte-equals project-root copy (cp not symlink)
- refi-npv.md byte-equals project-root copy (cp not symlink) — full content, NOT a marker stub
- apr-reg-z.md byte-equals project-root copy (cp not symlink) — full content, NOT a marker stub
- 5 full-content references derive from already-shipped Phase 1-5 + Phase 2 source artifacts
- tax-deductibility.md cross-links to Phase 6 refi-npv.md (Phase 6 COMPLETE per STATE.md)
- assets/.gitkeep committed (webapp-testing layout parity)
- No User Layer PII in any file
</verification>

<success_criteria>
- 9 files in `.claude/skills/mortgage-ops/references/` with exact ROADMAP SC-5 filenames
- THREE references drift-protected (arm-mechanics + refi-npv + apr-reg-z; Wave 5 ships byte-equality tests for all three)
- No marker-stub leftover content (refi-npv + apr-reg-z are full content lifted from project root, not 25-line stubs)
- Reference content is auditable (cites lib/rules/* + data/reference/*)
- Pre-existing test suite green
- SKLL-08 closes FULLY (all 9 references ship with full content; no partial-with-stubs disclosure)
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-04-SUMMARY.md` documenting:
- 9 reference files created (table: filename, line count, cl100k tokens, source phase)
- arm-mechanics.md diff result vs project-root (must be empty)
- refi-npv.md + apr-reg-z.md diff result vs project-root (must be empty; byte-lift verified)
- assets/.gitkeep created confirmation
- Cross-link audit: which mode files reference which references (data flow forward-check)
</output>
