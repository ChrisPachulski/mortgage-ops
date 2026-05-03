---
phase: 06
plan: 06
type: execute
wave: 6
depends_on:
  - "06-00"
  - "06-01"
  - "06-04"
  - "06-05"
files_modified:
  - references/refi-npv.md
  - tests/test_refinance.py
autonomous: true
requirements:
  - REFI-09
tags:
  - phase-06
  - refinance-npv
  - references
  - documentation
must_haves:
  truths:
    - "references/refi-npv.md exists at project root /references/"
    - "Document contains literal phrase 'outflows negative, savings positive' in the first H2 section (SC-5 verbatim)"
    - "Document has 7 sections per Plan 06-PATTERNS §'references/refi-npv.md' (Sign Convention, Borrower NPV Formula, Discount-Rate Selection, Rate-and-Term vs Cash-Out, Simple vs NPV Breakeven, After-Tax Mode, Citations)"
    - "scripts/refi_npv.py --help cites references/refi-npv.md (already shipped Wave 4; Wave 6 is the doc body it points to)"
    - "lib/refinance.py module docstring already cites references/refi-npv.md (Wave 1)"
    - "Wave 0 stubs test_refi_npv_doc_sections_present + test_refi_npv_doc_sign_convention_phrase + test_arm_terms_docstring_cites_arm_mechanics-style stub for refi flip from xfail to PASS"
  artifacts:
    - path: "references/refi-npv.md"
      provides: "Sign-convention doc (REFI-09 / SC-5); ≥ 250 lines; cites Investopedia + Federal Reserve + IRS Pub 936"
      min_lines: 250
---

<objective>
Ship `references/refi-npv.md` documenting the borrower-perspective sign convention with the literal phrase "outflows negative, savings positive" verbatim per SC-5. The doc body is what `scripts/refi_npv.py --help` (Wave 4) and `lib/refinance.py` module docstring (Wave 1) already point at — Wave 6 closes the citation loop. Closes REFI-09.

Output: ~250-300 line markdown doc + 2 final Wave-0 stub flips.
</objective>

<context>
@.planning/phases/06-refinance-npv/06-RESEARCH.md
@.planning/phases/06-refinance-npv/06-PATTERNS.md
@references/arm-mechanics.md
@lib/refinance.py
@scripts/refi_npv.py
@tests/test_refinance.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create references/refi-npv.md</name>
  <files>references/refi-npv.md</files>
  <action>
    Create the document with these 7 sections (mirrors references/arm-mechanics.md structure):

    # Refinance NPV — Borrower-Perspective Conventions (REFI-09 / SC-5)

    ## 1. Sign Convention — outflows negative, savings positive
    Headline statement. The literal phrase MUST appear in this section. Worked example showing a $2k closing-cost outflow as `-2000.00` and a $367/mo savings inflow as `+366.57`.

    ## 2. Borrower NPV Formula
    NPV = Σ (CF_t / (1 + r/m)^t) for t = 0 to N. Define each variable. Cite Investopedia.

    ## 3. Discount-Rate Selection (D-05)
    Three plausible defaults: borrower opportunity cost (5-7%), risk-free, OLD loan rate. Recommend "borrower's after-tax marginal opportunity cost". Document the D-05 decision: REQUIRED caller-supplied; no engine default.

    ## 4. Cashflow Inventory: Rate-and-Term vs. Cash-Out
    Two tables (lifted verbatim from 06-RESEARCH.md §"(a) Canonical Refi NPV Formula"). Cite Federal Reserve "Consumer's Guide to Mortgage Refinancing" + CFPB Closing Disclosure conventions.

    ## 5. Simple vs. NPV-Based Breakeven (REFI-03)
    Define both formulas. Document divergence cases (RESEARCH §"(d) Divergence"). Pin the divergence oracle from `tests/fixtures/refinance/breakeven_divergence.json`. Note D-06: NPV-breakeven uses cumulative-NPV scan, NOT npf.irr (bug #131).

    ## 6. After-Tax Optional Mode (D-09)
    When `after_tax_mode=True`: deductible_principal = min(new_principal, qualified_loan_limit). Tax shield = deductible_interest_t × marginal_tax_rate. Cite IRS Pub 936 + RUL-11 (`lib/rules/irs_pub936.py::qualified_loan_limit`). Document grandfathering ($1M cap pre-2017 vs $750k post-2017).

    ## 7. v1 Carve-Outs
    - PMI/MIP recalc on cash-out LTV change is OUT (D-08; caller supplies new_loan_monthly_pi_override per D-10)
    - Closing costs paid out-of-pocket only (D-12; financing-into-loan deferred)
    - pyxirr deferral to Phase 11 (D-07)
    - Competing-offer comparison deferred to Phase 11 SUBA-02

    ## 8. Citations
    - Investopedia "Net Present Value (NPV)" — https://www.investopedia.com/terms/n/npv.asp
    - Federal Reserve "Consumer's Guide to Mortgage Refinancing" — https://www.federalreserve.gov/pubs/refinancings/
    - CFPB Closing Disclosure Examples — https://www.consumerfinance.gov/owning-a-home/closing-disclosure/
    - IRS Publication 936 (2024) — https://www.irs.gov/pub/irs-pdf/p936.pdf
    - numpy-financial v1.0.0 docs (npv signature) — https://numpy.org/numpy-financial/latest/
    - numpy-financial bug #131 (irr arch-dependent) — https://github.com/numpy/numpy-financial/issues/131

    Cross-reference Phase 6 LOCKED DECISIONS D-01..D-16 (full list mirrors the 06-RESEARCH.md §"Locked Decisions" block — copy verbatim for citing inside `lib/refinance.py` module docstring).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && wc -l references/refi-npv.md && grep -c 'outflows negative, savings positive' references/refi-npv.md && grep -c 'irs.gov' references/refi-npv.md && grep -c 'numpy-financial' references/refi-npv.md</automated>
  </verify>
  <acceptance_criteria>
    - File exists; ≥ 250 lines
    - Contains literal phrase `outflows negative, savings positive` ≥ 1 times (SC-5 mandate)
    - All 7 sections present (regex `^## [1-7]\.` matches 7 headers; or `## 1`..`## 7` numbered headers)
    - Section 8 Citations contains links to investopedia + federalreserve + irs.gov + numpy-financial bug #131
    - Cross-references Phase 6 D-01..D-16 (or at least D-04, D-05, D-06, D-07, D-09, D-12 explicitly)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Flip last Wave-0 stubs (test_refi_npv_doc_*)</name>
  <files>tests/test_refinance.py</files>
  <action>
    Remove xfail decorators on:
    - test_refi_npv_doc_sections_present — assert REFI_NPV_DOC_PATH exists, read text, regex-match all 7 section headers
    - test_refi_npv_doc_sign_convention_phrase — assert literal phrase present (SC-5 verbatim)

    Both bodies use the REFI_NPV_DOC_PATH constant from Plan 06-00 module-level constants.
  </action>
  <acceptance_criteria>
    - Both tests PASS
    - All 25 Wave-0 stubs now PASS (zero remaining XFAIL from Phase 6)
    - Phase 5 baseline preserved
    - mypy + ruff clean
  </acceptance_criteria>
</task>

</tasks>

<locked_decisions>
- SC-5 verbatim phrase: "outflows negative, savings positive" — DO NOT paraphrase
- Doc structure mirrors references/arm-mechanics.md (Phase 5 Plan 05-05) — same 7-section pattern, same citation-per-section discipline
</locked_decisions>

<verify_block>
- references/refi-npv.md shipped, ≥ 250 lines, all 7 sections, SC-5 phrase present
- Last 2 Wave-0 stubs flipped to PASS
- All 25 Phase 6 stubs now PASS (Wave 6 closure)
- Phase 5 baseline preserved
- mypy --strict + ruff clean
</verify_block>

<deviation_rules>
- Rule-1: SC-5 literal phrase is LOCKED. If the doc author wants to phrase it differently, STOP — SC-5 is verbatim ROADMAP language and the test asserts the literal string.
- Rule-2: do not abbreviate the citations section. SKLL-08 (Phase 10) ingests this whole doc as a skill reference; full URLs are needed.
- Rule-3: hygiene-only deviations noted in SUMMARY.md.
</deviation_rules>

<success_criteria>
- references/refi-npv.md shipped with all 7 sections + SC-5 verbatim phrase
- All 25 Phase 6 Wave-0 stubs flipped to PASS (zero remaining XFAIL from Phase 6)
- Phase 5 baseline preserved (≥ 432 passed) + 25 net new passing Phase 6 tests = ≥ 457 passed
- REFI-01..09 all closed
- ROADMAP Phase 6 SC-1..SC-5 all pinned by tests
- mypy --strict + ruff clean
</success_criteria>
