---
phase: 07
plan: 06
type: execute
wave: 6
depends_on: ["07-05"]
files_modified:
  - references/apr-reg-z.md
  - lib/apr.py
autonomous: true
requirements: [APR-08]
tags:
  - phase-07
  - estimated-apr
  - references
  - documentation
must_haves:
  truths:
    - "references/apr-reg-z.md exists with all 6 sections (cite-from contract, unit-period model, day-count, worked example, Newton convergence, citations)"
    - "lib.apr.APRRequest docstring cites references/apr-reg-z.md (mirrors Phase 5 ARMTerms.__doc__)"
    - "Wave 0 stub test_references_apr_reg_z_doc_present_with_required_sections flips to PASS"
    - "All citation URLs verified against eCFR / CFPB on 2026-05-02 per RESEARCH §Citations"
  artifacts:
    - path: "references/apr-reg-z.md"
      provides: "Phase 7 reference doc cited from APRRequest docstring"
      min_lines: 250
    - path: "lib/apr.py"
      modification: "APRRequest docstring extended with 'See references/apr-reg-z.md ...' citation"
---

## Goal

Ship `references/apr-reg-z.md` documenting the unit-period model,
day-count conventions, odd-first-period handling, Newton-Raphson
convergence, and regulatory citations. Add citation in
`lib.apr.APRRequest.__doc__` (mirrors Phase 5 ARMTerms pattern). Flip
Wave 0 stub.

## Tasks

### Task 1 — Create `references/apr-reg-z.md`

Mirror `references/arm-mechanics.md` six-section template:

```markdown
# Estimated APR — mortgage-ops Phase 7 Reference

This document records the conventions implemented by `lib/apr.py`
(estimated APR solver) and pairs each convention with its regulatory
citation. All section numbers and URLs were verified on 2026-05-02
against the live eCFR + CFPB explainer.

Cited from `lib.apr.APRRequest.__doc__` per ROADMAP SC-5.

---

## 1. Unit-Period Model (12 CFR Part 1026 Appendix J)

The actuarial APR is the periodic rate `i` per unit period that satisfies:

    Σⱼ [Aⱼ × (1 + f·i) × (1+i)^(-t)]  =  Σₖ [Pₖ × (1 + g·i) × (1+i)^(-s)]

where (Aⱼ, t, f) are the j-th advance amount, full unit-period offset, and
fractional unit-period component; (Pₖ, s, g) the analogous payment values.
APR = `i × unit_periods_per_year` (12 for monthly mortgages — the default).

For a regular monthly mortgage with no odd first period, this collapses
to the standard PV equation `loan = pmt · ((1 - (1+i)^(-n)) / i)`.

**Citations:**
- 12 CFR Part 1026 Appendix J §(b)(1)–(b)(5):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026

## 2. Day-Count Conventions

Reg Z does NOT mandate a single day-count convention; the lender's choice
governs. Phase 7 supports three conventions, defaulting to US 30/360
(the FFIEC APR Tool default):

| Convention   | Unit-period days (monthly) | Use case                      |
|--------------|----------------------------|--------------------------------|
| `30/360`     | 30                         | Default for closed-end mortgages |
| `actual/365` | 365 / 12 ≈ 30.4167         | Some adjustable-rate products  |
| `actual/actual` | days(orig→orig+1mo)     | Treasury convention; rare for mortgages |

**Citation:** 12 CFR §1026.17(c)(4) +
https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.17

## 3. Odd First Period Handling (§1026.17(c)(4))

When the first payment is more than one full unit period after origination,
the additional days form a "fractional unit period" denoted `f`:

    f = (days_origination_to_first_payment - unit_period_days) / unit_period_days

This `f` factor enters the U-equation as the simple-interest term `(1 + f·i)`
on the first payment.

**Engine helper:** `_compute_odd_first_period_fraction(origination, first_payment, day_count)`.
**User shortcut:** `APRRequest.odd_first_period_days: int` (engine rewrites
the first PaymentScheduleEntry.unit_period_fraction).

**Negative case (short first period):** the math still works for f ∈ (-1, 0);
documented but not extensively tested in Phase 7 (RESEARCH OPEN Q1).

**Long case (>= 1 unit period):** rejected at the boundary; caller should
insert an extra advance entry instead of stretching the first period.

**Citation:** 12 CFR §1026.17(c)(4) — see URL above.

## 4. Worked Example — Reg Z Appendix J Example J-1

**Inputs:** $5,000 loan, 36 monthly payments of $166.07, no odd first period,
no finance charges.

**U-equation collapses to:**

    5000 = Σ_{k=1}^{36} 166.07 / (1+i)^k

**Seed via `npf.rate(36, -166.07, 5000, 0)`:** ≈ 0.0099991 (~ 1%/month).

**Newton iterations:** 1-2 to reach `Decimal("0.00001")` tolerance.

**Result:** `i = Decimal("0.010000")`, APR = `Decimal("0.120000")` = 12.00%.

This example is the SC-1 anchor pinned by
`tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` and
`test_apr_reg_z_appendix_j_worked_example_returns_12_percent`.

**Citation:** 12 CFR Part 1026 Appendix J §(c)(1) — see URL §1.

## 5. Newton-Raphson Convergence

**Algorithm:** standard Newton iteration `i_{n+1} = i_n - f(i_n) / f'(i_n)`
where `f(i)` is the U-equation residual and `f'(i)` its analytic derivative.

**Seed:** `Decimal(str(npf.rate(...)))` treating the loan as a regular
transaction. Fallback: nominal-rate-of-return when `npf.rate` returns NaN
or out of [0, 1].

**Tolerance:** `Decimal("0.00001")` (10x tighter than Reg Z §1026.22(a)(2)
1/8 percentage-point regular tolerance = `Decimal("0.00125")`; in practice
125x tighter — the project applies the most-conservative bound consistent
with SC-1).

**Convergence test:** combined `abs(i_{n+1} - i_n) <= Decimal("0.00001")`
AND `abs(f(i_n)) <= Decimal("0.01")` (dollar residual). Both must hold —
the dollar residual is a Phase-7-invented defense-in-depth guard.

**Iteration cap:** 50 (ROADMAP SC-3). Engine raises `APRConvergenceError`
on cap breach.

**Decimal vs float:** the entire iteration runs in
`with localcontext(MONEY_CONTEXT)` (prec=28). The seed is the only
float→Decimal transition (cast through `Decimal(str(...))`). `mypy --strict`
enforces no other float in the engine.

**Note on numpy-financial issue #131:** the architecture-dependent IRR
bug in `numpy_financial.irr` does NOT apply to `numpy_financial.rate`,
which uses a deterministic Newton iteration. Phase 7 uses `npf.rate` for
the seed and never `npf.irr` (per `lib/amortize.py:128-131` precedent).

## 6. Citations Summary (verified 2026-05-02)

- **12 CFR Part 1026 Appendix J** — eCFR:
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026
- **12 CFR §1026.17(c)(4)** — basis of disclosures + odd first period
- **12 CFR §1026.18(b), (e)** — amount financed + APR disclosure label
- **12 CFR §1026.4** — finance-charge enumeration (caller-supplied per
  Phase 7 LOCKED DECISION)
- **12 CFR §1026.22(a)(2)–(a)(3)** — APR tolerance (encoded in
  `lib/rules/reg_z.py` Phase 2)
- **CFPB TILA-RESPA Compliance Guide:**
  https://files.consumerfinance.gov/f/documents/cfpb_tila-respa-integrated-disclosure-rule_compliance-guide.pdf
- **FFIEC APR Calculator (APRWIN):** https://www.ffiec.gov/aprwin.htm
- **CFPB Rate Spread Calculator (FFIEC fallback):**
  https://ffiec.cfpb.gov/tools/rate-spread
- **numpy_financial.rate documentation:**
  https://numpy.org/numpy-financial/latest/rate.html
```

### Task 2 — Add citation to `lib.apr.APRRequest.__doc__`

Mirror Phase 5 ARMTerms pattern. Extend Wave 1 docstring with:

```python
class APRRequest(BaseModel):
    """Reg Z Appendix J APR-solve request.

    See `references/apr-reg-z.md` for the unit-period model, day-count
    conventions, odd-first-period handling, and Newton-Raphson convergence
    details with regulatory citations (ROADMAP SC-5).

    Pydantic v2 strict + frozen + forbid per Phase 1 D-08.
    """
    ...
```

### Task 3 — Flip Wave 0 stub `test_references_apr_reg_z_doc_present_with_required_sections`

```python
def test_references_apr_reg_z_doc_present_with_required_sections() -> None:
    """APR-08 + ROADMAP SC-5: references/apr-reg-z.md exists with §1-6."""
    doc_path = Path(__file__).resolve().parent.parent / "references" / "apr-reg-z.md"
    assert doc_path.exists(), f"references/apr-reg-z.md must exist (APR-08 + SC-5); got {doc_path}"
    content = doc_path.read_text()
    required_sections = [
        "## 1. Unit-Period Model",
        "## 2. Day-Count Conventions",
        "## 3. Odd First Period Handling",
        "## 4. Worked Example",
        "## 5. Newton-Raphson Convergence",
        "## 6. Citations Summary",
    ]
    for section in required_sections:
        assert section in content, f"references/apr-reg-z.md missing section: {section}"
    # Cite-from contract: APRRequest docstring must mention the doc
    apr_module = (Path(__file__).resolve().parent.parent / "lib" / "apr.py").read_text()
    assert "references/apr-reg-z.md" in apr_module, \
        "lib/apr.py must cite references/apr-reg-z.md per ROADMAP SC-5"
```

## Acceptance

- `references/apr-reg-z.md` exists, ≥250 lines
- All 6 required section headers present
- `grep -c 'references/apr-reg-z.md' lib/apr.py` returns ≥1 (APRRequest docstring)
- `pytest tests/test_apr.py::test_references_apr_reg_z_doc_present_with_required_sections -v` PASSES
- After this wave: 12 of 13 Wave 0 stubs flipped (APR-04 stays xfail until Wave 7)

## LOCKED DECISIONS

- **D-28:** `references/apr-reg-z.md` six-section structure (mirrors
  `references/arm-mechanics.md` Phase 5 D-08 template). Section reordering
  requires plan revision.
- **D-29:** Cite-from contract: `lib/apr.py` (specifically `APRRequest.__doc__`)
  cites the references doc; pinned by the test above. Mirrors Phase 5 ARM-09
  pattern.
- **D-30:** All citation URLs verified against eCFR / CFPB on 2026-05-02
  (per RESEARCH §Citations). Future re-verification cadence: annual (per
  Phase 2 staleness convention).

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
ls -la references/apr-reg-z.md
wc -l references/apr-reg-z.md
pytest tests/test_apr.py::test_references_apr_reg_z_doc_present_with_required_sections -v
pytest tests/test_apr.py -v --tb=no 2>&1 | tail -20
```

## Deviation Rules

- Rule-1: section header changes require plan revision (the test grep is
  exact-match).
- Rule-3: hygiene only.

## Cross-wave Dependency Notes

- **Upstream:** Wave 5 (fixtures referenced as worked-example anchors).
- **Downstream:** Phase 10 (Claude Skill Frontend) bundles
  `references/apr-reg-z.md` into the skill folder per project convention.
- APR-08 fully closed by this wave.
