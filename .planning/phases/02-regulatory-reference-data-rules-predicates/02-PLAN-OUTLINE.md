# Phase 02 — Plan Outline (Additive)

**Phase:** 02 — Regulatory Reference Data & Rules Predicates
**Mode:** chunked outline-only — additive (existing plans 02-01..02-04 frozen)
**Created:** 2026-04-26
**Source artifacts honored:**
- `.planning/REQUIREMENTS.md` (Phase 2 reqs REF-01..09 + RUL-01..13)
- `.planning/ROADMAP.md` Phase 2 success criteria (lines 54–59)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-CONTEXT.md` (D-01..D-12 locked decisions)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-RESEARCH.md` (per-rule design notes lines 780–913)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-PATTERNS.md` (predicate template + analog files)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-VALIDATION.md` (Nyquist gates per RUL)

## Existing Plans (kept — DO NOT touch)

| Plan ID | Status | Wave | Requirements | Files Owned (high-level) |
|---------|--------|------|--------------|---------------------------|
| 02-01-PLAN.md | [EXISTING — skip] | 1 | REF-01, REF-08, REF-09, RUL-01, RUL-12, RUL-13 | `lib/rules/_loader.py`, `lib/rules/types.py`, `lib/rules/loan_type.py`, `data/reference/conforming-limits-2026.yml`, schema + citation-coverage meta-tests |
| 02-02-PLAN.md | [EXISTING — skip] | 2 | REF-02, REF-03, RUL-04 | `lib/rules/fha_mip.py`, `data/reference/fha-limits-2026.yml`, `data/reference/fha-mip-rates.yml`, FHA branch of `loan_type.py` |
| 02-03-PLAN.md | [EXISTING — skip] | 2 | REF-04, REF-05, RUL-06, RUL-07 | `lib/rules/va_funding_fee.py`, `lib/rules/va_residual_income.py`, `data/reference/va-funding-fees.yml`, `data/reference/va-residual-income.yml`, VA branch of `loan_type.py` |
| 02-04-PLAN.md | [EXISTING — skip] | 2 | REF-06, REF-07, RUL-08, RUL-11 | `lib/rules/usda.py`, `lib/rules/irs_pub936.py`, `data/reference/usda-income-limits.yml`, `data/reference/irs-pub936.yml`, USDA branch of `loan_type.py` |

**Resume confirmation for orchestrator:** the four existing plans cover 17 of 23 Phase 2 requirements (all REF-01..09; RUL-01, RUL-04, RUL-06, RUL-07, RUL-08, RUL-11, RUL-12, RUL-13). Missing 6 of 13 RUL IDs: RUL-02, RUL-03, RUL-05, RUL-09, RUL-10. (RUL-12 and RUL-13 are continuous-coverage requirements that re-validate every time a new predicate ships; the new plans below extend their coverage and the audit-gate plan 02-07 re-verifies them.)

## New Plans (proposed)

| Plan ID | Objective | Wave | Depends On | Requirements |
|---------|-----------|------|------------|--------------|
| **02-05** | Conventional PMI (HPA) + Fannie LLPA matrix + Freddie eligibility matrix | 3 | [02-01] | RUL-02, RUL-03, RUL-05 |
| **02-06** | ATR/QM General-QM price-based test + Reg Z APR tolerances | 3 | [02-01] | RUL-09, RUL-10 |
| **02-07** | Citation-coverage hardening + final schema audit (non-mergeable per D-03) | 4 | [02-01, 02-02, 02-03, 02-04, 02-05, 02-06] | RUL-12 (final pass), RUL-13 (final pass), REF-09 (final pass) |

**Plan-packaging rationale (D-02 + D-03 verbatim from CONTEXT.md):**

- D-02 locked the 3-new-plans split (02-05 = PMI + LLPA + Freddie, 02-06 = ATR/QM + Reg Z, 02-07 = audit). The user explicitly chose this packaging over the planner-side preference for "one plan per missing predicate"; honoring locked decisions per `<context_fidelity>`.
- D-03 locked 02-07 as non-mergeable (separate audit gate even if RESEARCH §1162 says it can fold into 02-06). The audit gate protects Phase 4+ from inheriting predicate-library rot.
- 02-05 ships heavy (full Fannie LLPA matrix per D-04, full Freddie matrix, plus PMI). D-02 explicitly forbids splitting into 02-05a/02-05b without re-discussion. The brief below shows the plan stays within budget by structuring the matrices as YAML data files (not code), keeping the predicate logic itself thin (2D lookup + bucket helpers).
- 02-06 is small (Reg Z is ~30 lines of code, two Decimal constants; ATR/QM is a small threshold table) — comfortably within budget.
- 02-07's `requirements` field includes RUL-12 and RUL-13 because it RE-VALIDATES citation/fixture coverage across the full 11-predicate library after 02-05 and 02-06 ship. RUL-12/RUL-13 are continuous-coverage reqs (the citation-coverage meta-test must remain green after every new predicate); the final-pass plan asserts the meta-test catches synthetic mutation per CONTEXT.md `<specifics>` line 175.

**Wave assignment rationale (per CONTEXT.md `<decisions>` line 68):**
- 02-01 was Wave 1 (load-bearing template).
- 02-02, 02-03, 02-04 were Wave 2 (parallel after 02-01; each depends only on the loader from 02-01).
- 02-05 and 02-06 are Wave 3 — they could in principle run in Wave 2 (they only depend on the loader infra in 02-01, not on FHA/VA/USDA), but per CONTEXT.md they are sequenced into Wave 3 to land after the existing Wave-2 plans complete. 02-05 and 02-06 may run in PARALLEL within Wave 3 — they share zero `files_modified` (PMI/Fannie/Freddie touches `lib/rules/conventional_pmi.py`, `fannie_eligibility.py`, `freddie_eligibility.py` + their YAMLs; ATR/QM + Reg Z touches `lib/rules/atr_qm.py`, `reg_z.py` + an ATR/QM YAML). The only cross-cutting file is `tests/test_rules/test_citation_coverage.py` and `tests/test_reference/test_schema.py`, but those are filesystem-introspecting (no edits — they auto-discover the new files), so concurrent additions to `lib/rules/` and `data/reference/` from different plans do not create write conflicts.
- 02-07 must be Wave 4 — it is a global audit pass that depends on every predicate file being final.

**Coverage union check:** Across all NEW plans the union of requirements directly addressing the 5 missing predicates is `{RUL-02, RUL-03, RUL-05, RUL-09, RUL-10}` — exactly the missing set. Plan 02-07 carries RUL-12/RUL-13/REF-09 as final-pass entries (already first-introduced by 02-01); these are continuous-coverage reqs, not new ones.

## Per-Plan Briefs

### Plan 02-05 — Conventional PMI + Fannie LLPA + Freddie eligibility

**Objective:** Ship three predicates that together complete the conventional-loan eligibility surface: HPA termination (RUL-05), Fannie LLPA matrix lookup (RUL-02), and Freddie LPA-published eligibility (RUL-03). Phase 4 affordability and Phase 6 refi consume all three.

**Citations:**
- **RUL-05** — 12 USC §4901–4910 (Homeowners Protection Act of 1998), specifically §4902(a) (request termination at 80% LTV) and §4902(b) (auto termination at 78% LTV); §4902(g) high-risk midpoint carve-out.
  - Source URLs:
    - https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/
    - https://www.fdic.gov/consumer-compliance-examination-manual/v-5-homeowners-protection-act
  - Effective: 1999-07-29 (HPA original effective date; no material amendment since)
  - **Reference YAML:** NONE — pure Python predicate. HPA values (`Decimal("0.78")`, `Decimal("0.80")`) are statutory constants embedded as named constants in the predicate file with citation comments. CONTEXT.md `<decisions>` D-02 confirms "no new YAML; HPA values are in code." 02-PATTERNS.md line 35 confirms RESEARCH.md Pattern 3 quotes `conventional_pmi.py` as the canonical predicate template — the predicate is the worked example.

- **RUL-02** — Fannie Mae LLPA Matrix, Single-Family Selling Guide §B5-1.
  - Source URL [VERIFIED]: https://singlefamily.fanniemae.com/media/9391/display
  - Effective: 2026-01-28 (latest matrix revision per RESEARCH §Sources A4; pin specific revision date in YAML).
  - **Reference YAML:** `data/reference/fannie-llpa-matrix.yml` — full credit-score × LTV × loan-purpose × occupancy × unit-count matrix per D-04 (no `NotImplementedError` branches; full-matrix shipped). D-05 documents this YAML as implementation-detail under RUL-02 (NOT a new REF-ID).

- **RUL-03** — Freddie Mac Single-Family Seller/Servicer Guide §4203.4 + Credit Fee Cap matrix.
  - Source URL: https://guide.freddiemac.com/app/guide/section/4203.4 + https://sf.freddiemac.com/working-with-us/origination-underwriting/eligibility-criteria
  - Effective: pinned at YAML-write time per RESEARCH Assumption A4 (planner identifies specific revision date).
  - **Reference YAML:** `data/reference/freddie-eligibility-matrix.yml` — Freddie's Credit Fee Cap matrix (analog of Fannie LLPA; same 5-dim shape per RESEARCH §RUL-03). D-05 documents this YAML as implementation-detail under RUL-03.

**Files to create / modify (high-level):**
- `lib/rules/conventional_pmi.py` (new — pure Python; HPA constants 0.78/0.80 with citation comments; `status(loan, scheduled_balance, original_property_value, is_high_risk=False)` returning `Literal["auto_terminated", "request_eligible", "in_force", "high_risk_midpoint_terminated"]`)
- `lib/rules/fannie_eligibility.py` (new — `compute_llpa(...)` returns `Decimal` LLPA in basis points; private `_credit_score_bucket(score) -> str` and `_ltv_bucket(ltv) -> str` helpers; calls `load_reference("fannie-llpa-matrix")`)
- `lib/rules/freddie_eligibility.py` (new — `evaluate(...)` returns structured `{eligible: bool, credit_fee_bps: Decimal}`; calls `load_reference("freddie-eligibility-matrix")`)
- `data/reference/fannie-llpa-matrix.yml` (new — full LLPA matrix per D-04; `source:` + `effective:` + matrix rows keyed by `[credit_score_bucket][ltv_bucket]` + add-on adjustments per loan_purpose/occupancy/unit_count; all numeric values quoted strings per Pitfall 1)
- `data/reference/freddie-eligibility-matrix.yml` (new — Freddie Credit Fee Cap matrix; same shape/discipline as Fannie YAML)
- `tests/test_rules/test_conventional_pmi.py` (new — ≥4 fixtures: auto-terminate at 0.78 LTV exact, request at 0.80 LTV exact, in-force at 0.81 LTV, high-risk midpoint variant)
- `tests/test_rules/test_fannie_eligibility.py` (new — ≥5 boundary fixtures at credit-score buckets {700, 719, 720, 739, 740} per Pitfall 6 + LTV-bucket boundaries + at least one purchase, one rate-term refi, one cash-out refi case)
- `tests/test_rules/test_freddie_eligibility.py` (new — ≥3 fixtures including one shared-with-Fannie common case + one Freddie-specific overlay differing from Fannie)
- `tests/fixtures/rules/conventional_pmi_auto_terminate_78ltv.json`
- `tests/fixtures/rules/conventional_pmi_request_80ltv.json`
- `tests/fixtures/rules/conventional_pmi_in_force_81ltv.json`
- `tests/fixtures/rules/conventional_pmi_high_risk_midpoint.json`
- `tests/fixtures/rules/fannie_llpa_credit_score_700.json` (boundary: 700 → 660–699 bucket)
- `tests/fixtures/rules/fannie_llpa_credit_score_719.json` (boundary: 719 → 700–719 bucket high end)
- `tests/fixtures/rules/fannie_llpa_credit_score_720.json` (boundary: 720 → 720–739 bucket low end)
- `tests/fixtures/rules/fannie_llpa_credit_score_739.json` (boundary: 739 → 720–739 high end)
- `tests/fixtures/rules/fannie_llpa_credit_score_740.json` (boundary: 740 → 740–759 low end)
- `tests/fixtures/rules/fannie_llpa_cash_out_refi.json` (loan-purpose add-on cell)
- `tests/fixtures/rules/freddie_eligibility_common_case.json` (matches Fannie outcome)
- `tests/fixtures/rules/freddie_eligibility_overlay_diff.json` (Freddie-specific overlay differs from Fannie)
- `tests/fixtures/rules/freddie_eligibility_credit_fee_bps.json` (numeric Credit Fee Cap fixture)

Estimated files modified: 14 (3 predicates + 2 YAMLs + 3 test files + 9 fixture JSONs). Within the ≤12-files bundling guideline if fixture files are counted as one logical group; planner discretion to split fixture creation across tasks.

**Validation hooks each predicate must expose:**
- `conventional_pmi.status` — pure logic; raises `ValueError` if `original_property_value <= 0` (loud — money-discipline guard); does not call the loader (no YAML).
- `fannie_eligibility.compute_llpa` — calls `load_reference("fannie-llpa-matrix")` (so emits `StaleReferenceWarning` if the matrix YAML's `effective:` is >12 months old; raises `MissingReferenceFieldError` if YAML lacks `source:`/`effective:`); raises `LookupError` (loud) when no matrix row matches the (credit_score_bucket, ltv_bucket) cell — never silently returns 0 bps.
- `freddie_eligibility.evaluate` — calls `load_reference("freddie-eligibility-matrix")`; same loader-side guarantees as Fannie; raises `LookupError` when no matrix row matches.
- All three modules must have `Citation:` / `Source URL:` / `Effective:` triples in their docstrings so `tests/test_rules/test_citation_coverage.py` (auto-discovering the new files via filesystem introspection per `<specifics>` line 175) passes without code change.
- The two new YAML files must satisfy `tests/test_reference/test_schema.py` (REF-09) — `source:` URL present + `effective:` date present — automatically because the schema test parametrizes over `data/reference/*.yml`.

**Downstream-consumer contract:**
- Phase 4 (affordability) imports `lib.rules.fannie_eligibility.compute_llpa` and `lib.rules.conventional_pmi.status` per `<code_context>` lines 162–163.
- Phase 6 (refi) imports `lib.rules.conventional_pmi.status` (HPA at refi resets `original_value` — Phase 6's job, not RUL-05's; RUL-05 just exposes the status given the inputs).
- Per CONTEXT.md `<deferred>` line 187: refi-time `original_value` reset is OUT of Phase 2; predicate is a function of caller-supplied inputs, period.

**Acceptance-criteria seeds (concrete enough for downstream single-plan generator):**
- `data/reference/fannie-llpa-matrix.yml` parses with `yaml.safe_load`, has `source: "https://singlefamily.fanniemae.com/media/9391/display"`, has `effective: 2026-01-28` (or planner-pinned current date), has at minimum 35 matrix rows covering all 5 credit-score buckets × 7 LTV buckets in standard tier.
- `data/reference/freddie-eligibility-matrix.yml` parses, has Freddie source URL + planner-pinned effective date, has `credit_fee_cap_bps` rows.
- `lib/rules/conventional_pmi.py` exports `status` + `PMITerminationStatus = Literal[...]`; module docstring contains literal `Citation: 12 USC §4901–4910` substring.
- `lib/rules/fannie_eligibility.py` exports `compute_llpa` + `_credit_score_bucket` + `_ltv_bucket`; calls `load_reference("fannie-llpa-matrix")`.
- `lib/rules/freddie_eligibility.py` exports `evaluate`; calls `load_reference("freddie-eligibility-matrix")`.
- `uv run pytest tests/test_rules/test_conventional_pmi.py tests/test_rules/test_fannie_eligibility.py tests/test_rules/test_freddie_eligibility.py tests/test_rules/test_citation_coverage.py tests/test_reference/test_schema.py -x` exits 0.
- `uv run pytest --collect-only -q tests/test_rules/test_citation_coverage.py 2>&1 | grep -qE '\[(conventional_pmi|fannie_eligibility|freddie_eligibility)\]'` shows three new parametrized cases.
- `uv run mypy --strict . && uv run ruff check . && uv run ruff format --check .` exits 0.

### Plan 02-06 — ATR/QM General-QM Price-Based Test + Reg Z APR Tolerances

**Objective:** Ship the two final predicates closing out the predicate library: General QM price-based test (RUL-09 — replaces the legacy 43% DTI cap with the APR–APOR spread test from CFPB's Mar 2021 final rule) and Reg Z APR-tolerance check (RUL-10 — 1/8 pp regular, 1/4 pp irregular).

**Citations:**
- **RUL-09** — 12 CFR §1026.43(e)(2) — General QM Loan Definition, as amended by the CFPB's Dec 2020 final rule (replacing the 43% DTI gate with a price-based APR–APOR spread test).
  - Source URL [VERIFIED]: https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition
  - Annual indexed thresholds source [VERIFIED]: https://files.consumerfinance.gov/f/documents/cfpb_combined-reg-z-thresholds-adjustment-rule_2024-11.pdf
  - Effective: 2022-10-01 (mandatory compliance date after CFPB extension)
  - **Reference YAML:** `data/reference/atr-qm-thresholds.yml` (new) — encodes the (lien × loan-amount-band → APR-APOR threshold-pp) table from RESEARCH §RUL-09 (lines 877–887). Loan-amount tiers ($110,260, $66,156 — 2026 indexed values per Assumption A5) are in YAML so the annual CFPB threshold update is a YAML edit per `<conventions>` reference-data discipline. Threshold percentages (2.25 pp, 3.5 pp, 6.5 pp; Safe-Harbor variants 1.5/3.5/6.5 pp) are quoted-string Decimals.

- **RUL-10** — 12 CFR §1026.22 — Determination of annual percentage rate; tolerance §1026.22(a)(2)–(a)(3).
  - Source URL [VERIFIED]: https://www.consumerfinance.gov/rules-policy/regulations/1026/22/ + https://www.ecfr.gov/current/title-12/chapter-X/part-1026/subpart-C/section-1026.22
  - Effective: current Reg Z (last amended 2025; tolerance text unchanged for years).
  - **Reference YAML:** NONE per CONTEXT.md D-02 ("tolerances are Decimal constants in code with citation; no YAML needed"). The two tolerance constants (`Decimal("0.00125")` = 1/8 pp regular; `Decimal("0.0025")` = 1/4 pp irregular) live in `lib/rules/reg_z.py` as module-level named constants with §1026.22(a)(2)/(a)(3) citation comments.

**Files to create / modify (high-level):**
- `lib/rules/atr_qm.py` (new — exports `general_qm_passes(apr, apor, loan_amount, lien_position) -> bool`; optional `safe_harbor_qm_passes(...)` per RESEARCH §RUL-09 line 887; calls `load_reference("atr-qm-thresholds")`)
- `lib/rules/reg_z.py` (new — exports `within_apr_tolerance(disclosed_apr, actual_apr, is_irregular_transaction) -> bool` plus `TOLERANCE_REGULAR = Decimal("0.00125")` / `TOLERANCE_IRREGULAR = Decimal("0.0025")` module-level constants with §1026.22(a)(2) citation comments; pure Python, no YAML)
- `data/reference/atr-qm-thresholds.yml` (new — `source:` + `effective:` + threshold table rows keyed by `(lien_position, loan_amount_min, loan_amount_max)` → `apr_apor_threshold_pp` and `safe_harbor_threshold_pp`; numeric values quoted strings)
- `tests/test_rules/test_atr_qm.py` (new — ≥6 fixtures: each (lien × loan-amount-band) cell from the RESEARCH table, plus boundary cases at $66,156 and $110,260, plus one APR exactly at threshold case)
- `tests/test_rules/test_reg_z.py` (new — ≥4 fixtures: regular within tolerance, regular outside tolerance, irregular within tolerance, irregular outside tolerance; plus one fixture exactly AT tolerance to pin half-up boundary)
- `tests/fixtures/rules/atr_qm_first_lien_high_loan_within.json` (loan ≥ $110,260, APR–APOR < 2.25 pp → pass)
- `tests/fixtures/rules/atr_qm_first_lien_high_loan_outside.json` (loan ≥ $110,260, APR–APOR > 2.25 pp → fail)
- `tests/fixtures/rules/atr_qm_first_lien_mid_loan.json` ($66,156 ≤ loan < $110,260; threshold 3.5 pp)
- `tests/fixtures/rules/atr_qm_first_lien_low_loan.json` (loan < $66,156; threshold 6.5 pp)
- `tests/fixtures/rules/atr_qm_subordinate_lien_high.json` (subordinate, loan ≥ $66,156; threshold 3.5 pp)
- `tests/fixtures/rules/atr_qm_subordinate_lien_low.json` (subordinate, loan < $66,156; threshold 6.5 pp)
- `tests/fixtures/rules/atr_qm_loan_amount_boundary_66156.json` (boundary case at exact tier transition)
- `tests/fixtures/rules/reg_z_regular_within_tolerance.json` (`abs(disclosed - actual) = 0.001 < 0.00125` → pass)
- `tests/fixtures/rules/reg_z_regular_outside_tolerance.json` (`abs(disclosed - actual) = 0.0015 > 0.00125` → fail)
- `tests/fixtures/rules/reg_z_irregular_within_tolerance.json` (`abs(disclosed - actual) = 0.002 < 0.0025` → pass)
- `tests/fixtures/rules/reg_z_irregular_outside_tolerance.json` (`abs(disclosed - actual) = 0.003 > 0.0025` → fail)
- `tests/fixtures/rules/reg_z_regular_exactly_at_tolerance.json` (`abs(disclosed - actual) = 0.00125` exactly → pass per `<=` boundary in §1026.22(a)(2))

Estimated files modified: 12 (2 predicates + 1 YAML + 2 test files + 12 fixtures). Plan size is comfortable; no split needed.

**Validation hooks each predicate must expose:**
- `atr_qm.general_qm_passes` — calls `load_reference("atr-qm-thresholds")` (so emits `StaleReferenceWarning` if YAML's `effective:` is >12 months old per CFPB's annual indexed update); raises `LookupError` (loud) when no row matches the `(lien_position, loan_amount)` cell — never silently returns False.
- `atr_qm.safe_harbor_qm_passes` (optional second exported function) — same loader behavior; uses Safe-Harbor threshold column from the same YAML.
- `reg_z.within_apr_tolerance` — pure Python; no loader; no YAML; raises `ValueError` if `disclosed_apr < 0` or `actual_apr < 0` (loud invalid-input guard). Per Pitfall 11: predicate accepts `Decimal` inputs, uses `abs(a - b) <= tolerance` — Decimal arithmetic is exact, no precision drift.
- Both modules must have `Citation:` / `Source URL:` / `Effective:` triples in docstrings so `test_citation_coverage.py` auto-discovers and passes.
- The new `atr-qm-thresholds.yml` file must satisfy `test_schema.py` (REF-09) automatically.

**Downstream-consumer contract:**
- Phase 4 (affordability) imports `lib.rules.atr_qm.general_qm_passes` per `<code_context>` line 163. (Note: AFFD callers compute APR via Phase 7's APR solver before calling this predicate; Phase 2 just exposes the gate.)
- Phase 7 (APR) imports `lib.rules.reg_z.within_apr_tolerance` per `<code_context>` line 165 — used to verify "our estimated APR is within Reg Z tolerance of the lender's disclosed APR."
- Phase 8 (Stress) does NOT consume directly per `<code_context>` line 166.

**Acceptance-criteria seeds:**
- `data/reference/atr-qm-thresholds.yml` parses, has source URL = CFPB final-rule federalregister.gov URL or CFPB threshold-adjustment URL, has `effective:` date pinned to the most recent CFPB threshold-adjustment publication, has at least 5 threshold rows covering all (lien × loan-amount-band) cells from RESEARCH lines 877–884.
- `lib/rules/atr_qm.py` exports `general_qm_passes`; calls `load_reference("atr-qm-thresholds")`; module docstring contains literal `Citation: 12 CFR §1026.43(e)(2)` substring.
- `lib/rules/reg_z.py` exports `within_apr_tolerance`, `TOLERANCE_REGULAR`, `TOLERANCE_IRREGULAR`; module docstring contains literal `Citation: 12 CFR §1026.22` substring; constants are `Decimal("0.00125")` and `Decimal("0.0025")` exactly.
- `uv run pytest tests/test_rules/test_atr_qm.py tests/test_rules/test_reg_z.py tests/test_rules/test_citation_coverage.py tests/test_reference/test_schema.py -x` exits 0.
- `uv run pytest --collect-only -q tests/test_rules/test_citation_coverage.py 2>&1 | grep -qE '\[(atr_qm|reg_z)\]'` shows two new parametrized cases.
- `uv run mypy --strict . && uv run ruff check . && uv run ruff format --check .` exits 0.

### Plan 02-07 — Citation-Coverage Hardening + Final Schema Audit (non-mergeable per D-03)

**Objective:** Final-pass audit gate that runs AFTER all 11 predicates ship (02-01..06). Verifies the citation-coverage meta-test catches mutation, runs the full pytest + mypy --strict + ruff matrix on the complete predicate library, and confirms `tests/test_reference/test_schema.py` passes for all 9 reference YAMLs (7 from REF-01..07 + 2 implementation-detail Fannie/Freddie matrices + 1 ATR/QM thresholds = total 10 if ATR/QM YAML is added per 02-06; planner reconciles count at audit time).

**Citation:** Not applicable — this is a meta-test / audit-gate plan, not a new predicate. The "citation" backing this plan is the project's own `<conventions>` rule "1:1 test-to-citation mapping" (CLAUDE.md line 53–54) and Phase 2 success criteria #5 from ROADMAP.md line 59: *"Every predicate file has a docstring with a regulatory citation, and every citation has at least one passing test fixture (verified by `tests/test_rules/test_citation_coverage.py`)."*

**D-03 rationale (verbatim from CONTEXT.md):** "Plan 02-07 is non-mergeable. Even if RESEARCH §1162 says 'can be merged into 02-06 if scope allows,' keep it separate as an audit gate. Final pass = full pytest + mypy --strict + ruff + citation-coverage on all 11 predicates after 02-05/06 ship. This is the gate that protects Phase 4+ from inheriting predicate-library rot."

**Files to create / modify (high-level):**
- `tests/test_rules/test_citation_coverage_mutation.py` (new — small mutation-test harness that snapshots a predicate file, deletes the `Citation:` line, asserts `test_citation_coverage.py` would fail, restores the file; same for fixture deletion. Confirms the meta-test is not asleep. Per CONTEXT.md `<specifics>` line 175.)
- `tests/test_reference/test_yaml_count_audit.py` (new — small audit asserting `data/reference/*.yml` count equals expected total: 7 REF-01..07 YAMLs + 2 implementation-detail matrices (Fannie LLPA, Freddie eligibility) + 1 ATR/QM thresholds YAML = 10 total. Planner reconciles count at audit time and pins it.)
- (No modifications to existing predicate files.) (No new predicates.)
- `tests/test_rules/test_phase2_smoke.py` (new — single integration smoke test that imports all 11 predicates and calls each with a minimal happy-path input, asserting no `ImportError` / `MissingCountyDataError` / `MissingReferenceFieldError` cascades. Catches "predicate B silently broke when predicate A's YAML changed shape" regressions.)
- (Optionally) `data/reference/sources/` archive directory per CONTEXT.md `<specifics>` line 176 if planner deems it cheap to snapshot the source PDFs/page-fetches at audit time. Pitfall 8 protection. Optional — planner discretion.

Estimated files modified: 3 new test files + 0 production-code edits. Smallest plan in the phase. Comfortably within budget.

**Validation hooks:**
- The mutation test runs the citation-coverage check as a subprocess (`uv run pytest tests/test_rules/test_citation_coverage.py -x` against a temp-mutated `lib/rules/` snapshot) and asserts non-zero exit. This is the gate that proves the meta-test isn't asleep.
- The YAML-count audit test fails loud if `data/reference/*.yml` count drifts from the pinned audit total without a corresponding test update.
- The smoke test is the final-cross-check that Phase 4+ won't inherit a silently broken predicate.

**Acceptance-criteria seeds:**
- `cd /Users/cujo253/Documents/mortgage-ops && uv run pytest -x` exits 0 with at minimum: 11 predicate test files green + `test_citation_coverage.py` parametrized over 11 modules green + `test_schema.py` parametrized over 10 YAMLs green + new mutation test green + new YAML-count audit green + new smoke test green.
- `cd /Users/cujo253/Documents/mortgage-ops && uv run mypy --strict .` exits 0 across the full repo.
- `cd /Users/cujo253/Documents/mortgage-ops && uv run ruff check . && uv run ruff format --check .` exits 0.
- `find /Users/cujo253/Documents/mortgage-ops/lib/rules -name "*.py" -not -name "_*" -not -name "__*" -not -name "types.py" | wc -l` returns exactly 11 (the 11 predicate files).
- `find /Users/cujo253/Documents/mortgage-ops/data/reference -name "*.yml" | wc -l` returns the planner-pinned audit total (10 if ATR/QM ships a YAML; 9 otherwise — 02-07 reconciles).
- `cd /Users/cujo253/Documents/mortgage-ops && uv run pytest tests/test_rules/test_citation_coverage_mutation.py -x` exits 0 (mutation test catches both citation-deletion and fixture-deletion mutations).

**Why non-mergeable into 02-06 (D-03 reaffirmed):**
- 02-06 ships the LAST production predicates (atr_qm, reg_z). If the audit lived inside 02-06, an executor running 02-06 would have to validate ITS OWN newly-added predicates plus retroactively audit 02-01..05's predicates — a single-plan executor's context cost balloons past 50%.
- The audit needs to run AFTER 02-05 and 02-06 BOTH complete (it depends on every predicate file being final per D-03). Bundling into 02-06 forces 02-06 to depend on 02-05's completion, serializing what could be parallel Wave-3 work.
- A separate audit gate documents the project's "fail loud at the boundary" discipline architecturally (CLAUDE.md `<conventions>` "Reference data discipline" — staleness check, citation discipline are first-class concerns).

## Source Audit (multi-source coverage check)

Per planner self-check, every Phase-2 source-artifact item is COVERED by either an existing or new plan:

| Source Type | Item | Covered By |
|-------------|------|------------|
| GOAL (ROADMAP §Phase 2) | Cited regulatory data layer (`source:` + `effective:` discipline) | 02-01 (loader infra) + 02-05 (Fannie/Freddie YAMLs) + 02-06 (ATR/QM YAML) |
| GOAL | One-predicate-per-citation library | 02-01..02-04 (8 predicates) + 02-05 (3 predicates) + 02-06 (2 predicates) = 13 predicates total ≥ 11 required (extras: `_loader.py`, `types.py` — non-predicate per `NON_PREDICATE_FILES` constant in citation-coverage test) |
| REQ | REF-01..09 | 02-01 (REF-01, REF-08, REF-09) + 02-02 (REF-02, REF-03) + 02-03 (REF-04, REF-05) + 02-04 (REF-06, REF-07) |
| REQ | RUL-01 | 02-01 (loan_type vertical slice) + 02-02 (FHA branch) + 02-03 (VA branch) + 02-04 (USDA branch — already wired) |
| REQ | RUL-02 | **02-05** (Fannie LLPA — NEW) |
| REQ | RUL-03 | **02-05** (Freddie eligibility — NEW) |
| REQ | RUL-04 | 02-02 (fha_mip — existing) |
| REQ | RUL-05 | **02-05** (conventional_pmi — NEW) |
| REQ | RUL-06 | 02-03 (va_funding_fee — existing) |
| REQ | RUL-07 | 02-03 (va_residual_income — existing) |
| REQ | RUL-08 | 02-04 (usda — existing) |
| REQ | RUL-09 | **02-06** (atr_qm — NEW) |
| REQ | RUL-10 | **02-06** (reg_z — NEW) |
| REQ | RUL-11 | 02-04 (irs_pub936 — existing) |
| REQ | RUL-12 | 02-01 (initial citation-coverage meta-test) + 02-07 (final-pass mutation audit) |
| REQ | RUL-13 | 02-01 (initial fixture-coverage meta-test) + 02-07 (final-pass audit) |
| RESEARCH | Architectural Responsibility Map: predicate tier (citations) | 02-05, 02-06 honor the predicate template per RESEARCH §Pattern 3 (lines 386–445) |
| RESEARCH | Pitfall 6 (LLPA tier-boundary off-by-one) | 02-05 ≥5 boundary fixtures for credit-score buckets {700, 719, 720, 739, 740} |
| RESEARCH | Pitfall 11 (Reg Z tolerance Decimal precision) | 02-06 fixtures include exact-at-tolerance case + Decimal-only inputs |
| RESEARCH | "Data is the algorithm" (RESEARCH line 593) | 02-05 / 02-06 ship all matrices as YAML-loaded reference data (not hardcoded Python) |
| CONTEXT | D-01 (ship all 11 predicates) | 02-05 + 02-06 ship 5 of 5 missing predicates → all 11 land in Phase 2 |
| CONTEXT | D-02 (3 new plans = 02-05/06/07) | This outline matches D-02 verbatim |
| CONTEXT | D-03 (02-07 non-mergeable) | 02-07 brief explicitly justifies non-merge per D-03 |
| CONTEXT | D-04 (full Fannie LLPA matrix) | 02-05 brief commits to full-matrix shipping (no `NotImplementedError` branches) |
| CONTEXT | D-05 (Fannie/Freddie YAMLs are impl-detail under RUL-02/03) | 02-05 brief documents this; no new REF-IDs |
| CONTEXT | D-06 (county subset for REF-01/02/06) | Already honored by existing 02-01/02/04 |
| CONTEXT | D-07 (`lib/rules/types.py`) | Already shipped by 02-01 |
| CONTEXT | D-08 (`lib/rules/__init__.py` empty) | Already enforced by 02-01; new plans 02-05/06 must respect it (no re-exports) |
| CONTEXT | D-09 (IRS Pub 936 grace-period booleans) | Already implemented in 02-04 |
| CONTEXT | D-10 (USDA missing-county silent default vs RUL-01 raise asymmetry) | Already implemented in 02-01 + 02-04 |
| CONTEXT | D-11 (VA residual stable citation format) | Already implemented in 02-03 |
| CONTEXT | D-12 (no per-file staleness override) | Already enforced in 02-01 loader; 02-05/06 inherit; 02-07 audits |
| CONTEXT (Claude's Discretion: loader details) | `lru_cache(maxsize=None)`, fresh dict per call | Honored by 02-01; 02-05/06 use the loader as-shipped |
| CONTEXT (Claude's Discretion: Pydantic v2 + per-loader validation, no Cerberus) | New YAMLs in 02-05/06 use `lib/rules/_loader.py` + Pydantic shapes | 02-05 + 02-06 |
| CONTEXT (Claude's Discretion: yaml.safe_load only) | All new YAMLs loaded via existing safe-loader | 02-05 + 02-06 |
| CONTEXT (Claude's Discretion: fixture format = JSON with citation/source_url/comment) | All new fixtures follow this shape | 02-05 + 02-06 fixture briefs |
| CONTEXT (Claude's Discretion: Wave-3 sequencing) | 02-05 + 02-06 in Wave 3, optionally parallel; 02-07 in Wave 4 | This outline's Wave column |
| CONTEXT (Claude's Discretion: 02-05 sizing concern) | 02-05 stays in one plan per D-02; planner has internal task-split discretion | 02-05 brief lists 14 files, structurable as 2–3 internal tasks |

**No source-audit gaps detected.** The 5 missing predicate REQ IDs are all directly assigned. Continuous-coverage REQs (RUL-12, RUL-13, REF-09) extend automatically through 02-05/06 and re-audit at 02-07 per D-03.

## Status Summary

- Existing plans (kept): 4 (02-01, 02-02, 02-03, 02-04)
- New plans proposed: 3 (02-05, 02-06, 02-07)
- Total Phase 2 plans after this outline expands: 7 (matches D-02 packaging)
- Wave structure after expansion: W1 = {02-01}; W2 = {02-02, 02-03, 02-04}; W3 = {02-05, 02-06} (parallel); W4 = {02-07} (audit)
- Coverage of MISSING REQ IDs from planning_context: 5/5 = 100% (RUL-02, RUL-03, RUL-05, RUL-09, RUL-10)
- Locked decisions honored: D-01 through D-12 (all 12 user-locked decisions traceable to plans 02-01..02-07)

---

*Outline created: 2026-04-26*
*Mode: chunked outline-only (additive replan)*
*Next step: orchestrator confirms outline, then spawns single-plan generators for 02-05, 02-06, 02-07 in sequence*
