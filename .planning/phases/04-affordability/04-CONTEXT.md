# Phase 4: Affordability - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Compose the Phase 2 rule predicate library (`lib/rules/*`) + the Phase 3 amortization engine (`lib.amortize` → `Schedule.monthly_pi`) into a household-aware affordability surface. Ships:

- `lib/affordability.py` — DTI (front-end + back-end), LTV, CLTV, PITI, plus reverse-affordability ("what loan amount can I qualify for?") via `npf.pv` from a max-affordable PMT
- `scripts/affordability.py` — JSON-in / JSON-out CLI at project root (Phase 10 relocates into `.claude/skills/mortgage-ops/scripts/`)
- `config/household.example.yml` — FINAL Phase 4 schema (AFFD-09); Phase 1's redacted skeleton is replaced
- Joint-applicant aware (income aggregation + dual-credit-score handling per Fannie/Freddie convention)
- Output cites the binding rule when blocking (`blocked_by` field; format compatible with Phase 2 D-11 stable citation strings)
- Tests covering all 9 AFFD requirements, including a fixture-based household.example.yml end-to-end test (SC-4)

**Delivered this phase:**
- `lib/affordability.py` Pydantic request/response models + pure functions for DTI/LTV/CLTV/PITI (AFFD-01..04)
- Reverse-affordability solver that consumes `npf.pv` (AFFD-05)
- Joint-applicant aggregation (income sum, lower-credit-score selection) (AFFD-06)
- `blocked_by` precedence pipeline citing Phase 2 predicate citations (AFFD-07)
- `scripts/affordability.py` CLI mirroring Phase 3 D-17/D-18/D-19 conventions (AFFD-08)
- `config/household.example.yml` FINAL schema with PITI-input fields and applicants[] schema (AFFD-09)
- `tests/test_affordability.py` with hand-calculated golden fixtures + joint-applicant fixtures + blocker-precedence fixtures + CLI smoke (covers AFFD-01..09)

**NOT delivered this phase** (deferred to consumer phases or v2):
- ARM rate-reset re-amortization in affordability — Phase 5
- Refi NPV / breakeven / cash-out — Phase 6
- Estimated APR (Reg Z Appendix J) — Phase 7
- Rate-shock / income-shock / ARM-reset stress sweeps — Phase 8 (consumes affordability)
- DuckDB persistence of affordability scenarios — Phase 9
- ZIP / county-keyed property-tax + insurance lookup — v2 (PROP-02)
- Property valuation (Zestimate) — v2 (PROP-01)
- Three-bureau credit-score schema (mid-of-three) — out of scope (D-09)
- Income-type modeling (W-2 vs self-employed vs 1099 averaging) — out of scope (PROJECT.md)
- Skill physical relocation: `scripts/affordability.py` → `.claude/skills/mortgage-ops/scripts/` — Phase 10

</domain>

<decisions>
## Implementation Decisions

### PITI component sourcing (AFFD-04, AFFD-09)

- **D-01: Caller-supplied monthly $ for tax / insurance / HOA.** `config/household.example.yml` grows three Decimal-string fields under a new top-level block (planner picks the exact block name; recommend `escrow:` to scope from generic income/debt fields):
  - `property_tax_monthly: "$"` — Decimal string
  - `insurance_monthly: "$"` — Decimal string
  - `hoa_monthly: "$"` — Decimal string (default `"0.00"` when no HOA)

  Reason: matches the project's "user enters numbers manually as YAML — they need to read the LE anyway" principle (PROJECT.md "Out of Scope" rationale) and avoids county-keyed % inferences in v1. PMI/MIP are derived from predicates (D-02), so PITI = P&I (from `lib.amortize`) + tax + insurance + HOA + (PMI or MIP).

- **D-02: PMI and MIP derive from Phase 2 predicates — never caller-supplied.** Forward affordability calls:
  - `lib.rules.conventional_pmi.status(ltv_pct, ...)` for conventional loans (returns enum + termination thresholds — HPA: auto at 78% LTV, request at 80% LTV)
  - `lib.rules.fha_mip.compute(loan_amount, ltv_pct, term_months)` for FHA loans (returns UFMIP + annual MIP; convert annual to monthly = `(loan_amount × annual_mip_pct) / 12` quantized to cents)
  - VA / USDA / conventional ≤ 80% LTV → no monthly MI added

  Reason: keeps the rule layer authoritative; caller can't disagree with the predicate. Sequence: classify loan_type via `lib.rules.loan_type.classify` first → branch into the right MI predicate.

- **D-03: UFMIP financing is Claude's discretion at planning time.** FHA UFMIP (1.75% of base loan amount per HUD ML 2023-05) is conventionally rolled into the financed principal, NOT into monthly PITI. Planner picks one of: (a) require caller to pre-finance UFMIP into `loan_amount` and document the convention in CLI `--help`; (b) auto-finance UFMIP inside `lib.affordability` when `loan_type == "fha"` and emit the financed amount in the output. Either is correct — document whichever ships.

- **D-04: `property_value` is a per-request input, not in `household.yml`.** Property value changes per scenario (different houses); `household.yml` only carries household-stable facts (income, debts, credit scores, location, escrow estimates). The affordability JSON request includes `property_value: "$"` alongside `loan_amount` (forward) or `down_payment` (reverse). Planner finalizes the request schema.

### Joint-applicant credit-score model (AFFD-06)

- **D-05: Single `credit_score: int` per applicant — picks lower across applicants.** `household.example.yml` keeps Phase 1's shape: `applicants[].credit_score: int` (FICO 300–850). Phase 4 picks `min(applicant_a.credit_score, applicant_b.credit_score)` for Fannie LLPA + Freddie eligibility predicate calls. Caller is responsible for providing their middle-of-three (or whatever score they consider representative). Document the convention in (a) AFFD-09 schema docstring, (b) a comment block in `config/household.example.yml`, and (c) the `lib/affordability.py` module docstring.

  Reason: matches "fail loud, no inference" + "user enters numbers manually" disciplines. Three-bureau dict adds schema burden without changing decisions for a personal-use tool.

- **D-06: Income aggregation = sum across applicants.** `total_gross_monthly_income = sum(a.gross_monthly_income for a in applicants)`. No income-type modeling (W-2 vs self-employed vs 1099 averaging) — out of scope for v1 personal-use (PROJECT.md "Out of Scope" implicitly via "personal-use, not commercial DU/LPA replication").

- **D-07: Single-applicant case is supported via `applicants` list of length 1.** No special-cased single-applicant code path. The lower-of-credit-scores reduces to `applicant.credit_score` automatically. Test fixture covers both `len(applicants) == 1` and `len(applicants) == 2` cases.

### Reverse-affordability solver (AFFD-05)

- **D-08: One-shot `npf.pv` solve with caller-supplied `down_payment` + `target_loan_type` + `term_months` + `annual_rate` + monthly tax/ins/HOA.** No iteration; LTV is pinned by the input shape. Algorithm:
  1. `max_PITI = max_dti × total_gross_monthly_income − sum(monthly_debts)`
  2. Subtract caller-supplied `monthly_tax + monthly_insurance + monthly_hoa` from `max_PITI` → `max_PI_plus_MI`
  3. Estimate monthly MI given `target_loan_type` and a target LTV bucket (caller passes `target_ltv_pct` OR derive from `down_payment` + an iteratively-refined property_value — recommend caller passes `target_ltv_pct: "0.80"` explicitly to keep the solve one-shot)
  4. `max_PI = max_PI_plus_MI − estimated_monthly_MI`
  5. `max_loan_amount = npf.pv(rate=annual_rate / Decimal("12"), nper=term_months, pmt=−max_PI, fv=0)` — pass `pmt` as negative per numpy-financial convention (cash outflow); always pass `fv=0` (Phase 3 D-09 / numpy-financial bug #130 avoidance)
  6. Round result through `quantize_cents(...)` (NEVER through float)

- **D-09: Acceptance criterion 2 closure (round-trip within `Decimal("0.01")`).** Reverse → forward equality test: take `max_loan_amount` from reverse mode, feed it back into forward affordability with the same household + property_value derived from `(max_loan_amount + down_payment)`, assert `forward.dti_back ≤ max_dti + Decimal("0.0001")` (small tolerance for the cents-level rounding inside MI computation). Hand-calc fixture documents both sides with `source: ROADMAP.md SC-2` comment.

- **D-10: Reverse-mode JSON request shape.** Locked fields:
  ```
  {
    "mode": "reverse",
    "household": { ... per household.yml schema },
    "max_dti": "0.43",                  // Decimal string; caller-supplied (D-12)
    "down_payment": "$",                // Decimal string
    "target_loan_type": "conventional", // Literal: "conventional" | "fha" | "va" | "usda" | "jumbo"
    "target_ltv_pct": "0.80",           // Decimal string; pins MI bucket
    "term_months": 360,
    "annual_rate": "0.0700"             // Decimal string
  }
  ```
  Forward-mode shape mirrors but replaces `down_payment` + `target_ltv_pct` with `loan_amount` + `property_value`.

### Binding-rule blocker precedence (AFFD-07)

- **D-11: Output schema = single `blocked_by: str | None` + `warnings: list[str]`.** `blocked_by` holds the FIRST hard-fail citation in fixed priority order; `warnings` holds non-blocking signals. Default: `blocked = False`, `blocked_by = None`, `warnings = []`. Phase 4's `lib.affordability` evaluates predicates in this order and short-circuits on the first hard-fail:

  1. **Loan-type classification** — `lib.rules.loan_type.classify(loan_amount, county)`. If it raises `MissingCountyDataError`, surface as a hard error (NOT `blocked_by` — bad-input; Pydantic envelope on stderr per Phase 3 D-19). If it returns a loan_type that's outside the requested `target_loan_type`, set `blocked_by = "FHFA-LIMIT-{LOAN_TYPE}-{COUNTY}"` (conventional) or `"HUD-LIMIT-{LOAN_TYPE}-{COUNTY}"` (FHA).
  2. **LTV / CLTV breach loan-type ceiling** — citation: `"LTV-CEILING-{LOAN_TYPE}"` (planner picks final string format; must be stable for downstream skill-routing tests). Conventional: 95% standard / 97% first-time-buyer. FHA: 96.5% (3.5% min down). VA/USDA: 100%. Junior liens push CLTV which has separate ceilings.
  3. **DTI cap exceeded** — citation: `"DTI-CAP-{LOAN_TYPE}"`. DTI cap source = caller-supplied `max_dti` (D-12). Forward mode flags exceed; reverse mode's solver already enforces the cap so it never blocks here.
  4. **ATR/QM general-QM fails** — `lib.rules.atr_qm.general_qm_passes(...)`. Citation: `"ATR-QM-PRICE-FIRST"` or `"ATR-QM-PRICE-SUBORDINATE"`. Caller must supply `apr` + `apor` in the request for first-lien residential to evaluate this — if both are missing, treat as advisory (warning), not hard block.
  5. **VA residual income fails** — `lib.rules.va_residual_income.evaluate(...)` returns a `ResidualIncomeResult` whose `binding_rule_citation` is the stable `"VA-RESIDUAL-{REGION}-FAMILY-{N}"` string (Phase 2 D-11 — DO NOT format-drift). Only evaluated for `target_loan_type == "va"`.

  Soft-blocker / advisory citations go in `warnings`:
  - Fannie LLPA pricing hit (citation: `"FANNIE-LLPA-{FICO_BUCKET}-{LTV_BUCKET}"`)
  - PMI required (citation: `"HPA-PMI-REQUIRED"`)
  - DTI between 50% and 57% with comp-factors path available (FHA), citation: `"FHA-COMP-FACTORS-43"`
  - Stale reference YAMLs (already emit `StaleReferenceWarning` to stderr per Phase 2 D-12 — propagate into `warnings` via captured warnings filter)

- **D-12: DTI cap source = caller-supplied `max_dti` per JSON request, no defaults in v1.** Forces explicit choice every call (matches "fail loud" discipline). ROADMAP SC-2 example uses `max_dti=0.43`. Per-loan-type DTI YAML in `data/reference/` deferred to v2 if a planner finds the bare-input UX painful.

### CLI surface (AFFD-08)

- **D-13: Mirror Phase 3's CLI conventions.** `scripts/affordability.py` lives at project root; uses `--input <path>` only (no stdin); lazy-imports `lib.affordability` after argparse (fast `--help`); validates via `AffordabilityRequest.model_validate_json` at the boundary; emits 6-key Pydantic envelope on validation errors per Phase 3 D-19 (WR-02 closure shape: `type / loc / msg / input / url / ctx`); pretty-prints JSON to stdout. Inherits Phase 3 D-17 (relocate to `.claude/skills/mortgage-ops/scripts/` at Phase 10, NOT Phase 4).

- **D-14: Forward / reverse routing via `mode: "forward" | "reverse"` field on the request.** Pydantic discriminated union under `AffordabilityRequest`. Output is a single Pydantic response model (`AffordabilityResponse`) with optional fields per mode (forward: `dti_front`, `dti_back`, `ltv`, `cltv`, `piti`; reverse: `max_loan_amount`, `implied_pi`, `assumed_ltv_pct`, `assumed_monthly_mi`). Both modes share `blocked: bool`, `blocked_by: str | None`, `warnings: list[str]`, `loan_type: LoanType`, `total_gross_monthly_income`, `total_monthly_debts`. Planner finalizes whether to use Pydantic discriminated unions or one merged model with mode-conditional defaults — both shapes are acceptable.

### household.example.yml schema (AFFD-09)

- **D-15: Phase 4 ships the FINAL `config/household.example.yml`** (replaces Phase 1's redacted skeleton). Schema additions over Phase 1 placeholder (Phase 1 already covered `location`, `applicants[].{name, gross_monthly_income, credit_score}`, `monthly_debts.{auto, student_loans, credit_cards, other}`, `current_housing_payment`):
  - New top-level `escrow:` block with `property_tax_monthly`, `insurance_monthly`, `hoa_monthly` (D-01)
  - Optional `va:` block for VA loans: `region: Literal["northeast","midwest","south","west"]`, `family_size: int`, `actual_residual_income: "$"` (consumed by `va_residual_income.evaluate`)
  - **Field-level docstrings as YAML comments** with units, constraints, and the citation each field feeds (e.g., `# credit_score: FICO 300-850; treated as middle-of-3 score per AFFD-06 D-05; min across applicants is used for Fannie LLPA + Freddie eligibility lookups.`)
  - SC-4 fixture-based test loads this exact file end-to-end through `scripts/affordability.py` and asserts the output JSON shape

- **D-16: User Layer + pre-commit hook discipline preserved.** `config/household.yml` (the real file) stays gitignored + protected by Phase 1's `scripts/hooks/block-user-layer.py` pre-commit hook (FND-04). Phase 4 only modifies `config/household.example.yml`. Adding new fields to the example does NOT break the pre-commit hook; the hook's allowlist already permits `*.example.yml`.

### Test fixture strategy

- **D-17: Hand-calculated golden fixtures with citation comments** (Phase 2 / Phase 3 pattern). New `tests/fixtures/affordability/` directory. Required fixtures:
  - `forward_conventional_80_ltv.json` — forward, no PMI, no blocker
  - `forward_conventional_85_ltv_with_pmi.json` — forward, PMI in PITI, advisory warning
  - `forward_fha_above_dti_cap.json` — forward, blocked_by = `"DTI-CAP-FHA"`
  - `forward_va_residual_fail.json` — forward, blocked_by = `"VA-RESIDUAL-WEST-FAMILY-4"` (matches ROADMAP SC-3 example verbatim)
  - `forward_jumbo_above_county_limit.json` — forward, blocked_by = `"FHFA-LIMIT-CONFORMING-KING"` (or planner-finalized format)
  - `reverse_conventional_80_ltv_43_dti.json` — reverse, round-trips through forward within `Decimal("0.01")` per SC-2
  - `joint_applicants_two_incomes.json` — joint income sum + lower-credit-score selection (SC-5)
  - `single_applicant.json` — len(applicants) == 1
  - `household_example_yml_e2e.json` — invocation manifest pointing at `config/household.example.yml` (SC-4)

- **D-18: Exact Decimal equality, never `assertAlmostEqual`** (Phase 1 / Phase 3 reinforced). All money fields in fixture `expected` blocks are quoted Decimal strings. Compare using `==` against `Decimal("...")` parsed values. The `Decimal("0.0001")` tolerance in D-09 applies ONLY to the round-trip DTI floating math (compounded MI rounding), not to dollar amounts.

### Claude's Discretion

- **`AffordabilityRequest` / `AffordabilityResponse` Pydantic shape** — single class with optional fields vs Pydantic v2 discriminated union by `mode`. Both are valid; planner picks based on which produces cleaner test surface.
- **`blocked_by` citation string formats for non-VA-residual cases** — D-11 lists candidate formats (`FHFA-LIMIT-...`, `LTV-CEILING-...`, `DTI-CAP-...`, `ATR-QM-PRICE-FIRST`). Planner finalizes the exact strings; the only HARD constraint is VA residual stays `VA-RESIDUAL-{REGION}-FAMILY-{N}` per Phase 2 D-11 + ROADMAP SC-3.
- **UFMIP financing convention** — D-03: caller pre-finances vs `lib.affordability` auto-finances. Either is correct. Document whichever ships in CLI `--help` + module docstring.
- **PMI auto-termination modeling** — `conventional_pmi.status` returns thresholds (78% / 80% LTV). Phase 4 PITI assumes "PMI applies if LTV > 80%, drops at 78%". Whether Phase 4 surfaces a `pmi_terminates_at_period: int` advisory (e.g., "PMI auto-drops at month 137") in `warnings` is Claude's discretion — useful but not required by AFFD-04. Phase 8 stress / Phase 6 refi may consume it; if not added now, add when first consumer needs it.
- **CLTV junior-lien input shape** — `junior_liens: list[Money]` (sum) vs structured `list[{lien_holder, balance, position}]`. Recommend the simpler `list[Money]` until a downstream consumer needs structured fields. Phase 4 only computes `cltv = (loan_amount + sum(junior_liens)) / property_value`.
- **`apr` + `apor` ATR/QM gating** — caller-supplied in the JSON request when target loan-type is first-lien residential. Missing → ATR/QM check downgraded from blocker to skipped (advisory only). Document in `--help`.
- **Test runner pattern** — extend `tests/conftest.py` (Phase 1) with an `affordability_fixture` loader mirroring Phase 3's `amortize_fixture` (loads JSON, returns Pydantic `AffordabilityRequest`). Reuse the established pattern; do not invent a new one.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Inputs (project-level)

- `.planning/PROJECT.md` — project context, key decisions table (Decision #1: wrap numpy-financial; Decision #2: Decimal money; Decision #6: rules-as-predicates per citation; Decision #7: reference YAMLs annual refresh; Decision #10: bundled scripts ship with `--help` first)
- `.planning/REQUIREMENTS.md` §"Affordability" — Phase 4 requirements AFFD-01..09 (definitive)
- `.planning/ROADMAP.md` §"Phase 4: Affordability" — phase goal + 5 success criteria (esp. SC-2 round-trip, SC-3 `blocked_by: "VA-RESIDUAL-WEST-FAMILY-4"` example, SC-4 household.example.yml e2e, SC-5 joint applicants)
- `.planning/STATE.md` — current project state (Phase 3 complete, ready to start Phase 4)
- `CLAUDE.md` — money discipline (Decimal from strings, ROUND_HALF_UP, never mix with float), calc-engine separation (Claude never owns numbers), Pydantic v2 condecimal at script boundaries, rules-as-predicates citation pattern, no Co-Authored-By in commits
- `DATA_CONTRACT.md` — User/System/Data/Reference layer separation; `config/household.yml` is User Layer (gitignored, never auto-updated; pre-commit hook blocks edits per FND-04); `scripts/` is System Layer

### Phase 4 Research + Patterns (will be created by gsd-phase-researcher)

- `.planning/phases/04-affordability/04-RESEARCH.md` — to be written; researcher consumes this CONTEXT.md to know what to investigate (PMI/MIP integration shape, GSE DTI conventions, joint-applicant aggregation, npf.pv usage, blocker precedence design)
- `.planning/phases/04-affordability/04-PATTERNS.md` — to be written by gsd-pattern-mapper; identifies Phase 1/2/3 analogs for new Phase 4 files

### Prior-Phase Frozen Surfaces (Phase 4 USES; does NOT modify)

- `lib/models.py` (Phase 1 + Phase 3 D-14 extensions) — `Loan`, `Schedule`, `Payment` (with `cumulative_interest` + `cumulative_principal`), `Money`, `Rate` types. Phase 4 imports `Loan` + `Schedule` only.
- `lib/money.py` (Phase 1) — `to_money(str)`, `quantize_cents(Decimal)`, `CENT`, `MONEY_CONTEXT` (ROUND_HALF_UP). Use in EVERY Decimal cents-rounding inside `lib/affordability.py`.
- `lib/amortize.py` (Phase 3) — `build_schedule(loan)` produces `Schedule.monthly_pi`. Phase 4 calls this for forward-mode P&I; for reverse mode, calls `npf.pv` directly (do not roundtrip through `build_schedule`).
- `lib/rules/types.py` (Phase 2) — `LoanType`, `Region`, `County`, `Borrower`, `Property` typed extension types. Phase 4 imports `LoanType` + `Region` + `County`.
- `lib/rules/loan_type.py` — `classify(loan_amount, county) -> LoanType`. Raises `MissingCountyDataError` (loud) when county is None and loan exceeds baseline. AFFD-07 surfaces this as a hard error, not `blocked_by`.
- `lib/rules/conventional_pmi.py` — `status(ltv_pct, ...)` returns PMI status enum + termination thresholds (78% auto / 80% request).
- `lib/rules/fha_mip.py` — `compute(loan_amount, ltv_pct, term_months) -> {ufmip, annual_mip}`. Convert `annual_mip` to monthly via `(loan_amount × annual_mip_pct) / 12` quantized.
- `lib/rules/va_funding_fee.py` — `compute(...)` for VA funding fee (financed into principal at script boundary; NOT in monthly PITI).
- `lib/rules/va_residual_income.py` — `evaluate(region, family_size, loan_amount, actual_residual_income) -> ResidualIncomeResult`. Stable `binding_rule_citation` format: `f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"` — Phase 4 reads this VERBATIM as `blocked_by` (Phase 2 D-11; DO NOT format-drift).
- `lib/rules/usda.py` — `evaluate(...)` for USDA eligibility.
- `lib/rules/atr_qm.py` — `general_qm_passes(apr, apor, loan_amount, lien_position) -> bool` and `safe_harbor_qm_passes(...)`. Citation strings: `"ATR-QM-PRICE-FIRST"` / `"ATR-QM-PRICE-SUBORDINATE"`.
- `lib/rules/fannie_eligibility.py` — `compute_llpa(...)` returns LLPA pricing hit. Phase 4 surfaces as a soft warning, not a blocker.
- `lib/rules/freddie_eligibility.py` — `evaluate(...)` returns Freddie eligibility.
- `lib/rules/_loader.py` — `load_reference(name)` `lru_cache`d YAML loader; emits `StaleReferenceWarning` (per Phase 2 D-12) when `effective:` is > 12 months old. Phase 4 captures this warning class via `warnings.catch_warnings()` and propagates strings into the `warnings` field of the response (D-11).

### Prior-Phase CONTEXT.md (read for decisions that affect Phase 4)

- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-CONTEXT.md` — Phase 2 D-08 (predicates imported by full path; no re-exports), D-11 (VA residual citation format STABLE), D-12 (no `staleness_acknowledged_until` override; warnings are correct)
- `.planning/phases/03-core-amortization/03-CONTEXT.md` — Phase 3 D-04 (rate-per-period: monthly = annual_rate / 12), D-09 (final-payment cleanup), D-17 (`scripts/` lives at project root for now; Phase 10 relocates), D-18 (`--input <path>` only, lazy-import for fast `--help`), D-19 (Pydantic envelope at boundary)

### Phase 1 Reference YAMLs (Phase 4 reads via predicates)

- `data/reference/conforming-limits-2026.yml` (REF-01) — FHFA conforming + jumbo county limits. Drives loan_type.classify.
- `data/reference/fha-limits-2026.yml` (REF-02) — FHA limits.
- `data/reference/fha-mip-rates.yml` (REF-03) — FHA MIP rates per HUD ML 2023-05.
- `data/reference/va-funding-fees.yml` (REF-04) — VA funding fee tables.
- `data/reference/va-residual-income.yml` (REF-05) — VA M26-7 regional residual income tables.
- `data/reference/usda-income-limits.yml` (REF-06) — USDA income limits.
- `data/reference/atr-qm-thresholds.yml` (RUL-09) — CFPB ATR/QM annual indexed thresholds.
- `data/reference/fannie-llpa-matrix.yml` (RUL-02 implementation-detail) — Fannie LLPA matrix.
- `data/reference/freddie-eligibility-matrix.yml` (RUL-03 implementation-detail) — Freddie eligibility matrix.

### Test Fixtures + Patterns

- `tests/fixtures/golden_pmt.json` (Phase 1) — 4 oracle fixtures. Phase 4 forward-mode tests reuse the $400k @ 6.5% / 30yr → $2,528.27 P&I anchor in fixtures combining it with PITI inputs.
- `tests/conftest.py` (Phase 1) — pytest fixture factory pattern. Extend with `affordability_fixture` loader mirroring Phase 3's `amortize_fixture` (D-17 strategy).
- `tests/test_amortize.py` (Phase 3) — model for `tests/test_affordability.py` structure (golden + structural + invariant + CLI smoke).

### External Sources (already verified by Phase 1/2 research; no fresh WebFetch needed unless researcher disagrees)

- https://numpy.org/numpy-financial/latest/ — `npf.pv` API docs (cash-flow sign convention: pmt is negative for outflows, pv is positive for incoming principal)
- https://github.com/numpy/numpy-financial/issues/130 — pmt fv-sign bug (avoid `fv != 0`; always pass `fv=0` per Phase 3 D-19)
- https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026 — Phase 2 conforming-limits source
- https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf — HUD ML 2023-05 (FHA MIP) — drives `fha_mip.compute`
- https://benefits.va.gov/WARMS/docs/admin26/m26-07/ — VA M26-7 — drives `va_residual_income.evaluate`
- https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/ — HPA (PMI auto-termination at 78% LTV)
- https://en.wikipedia.org/wiki/Debt-to-income_ratio — DTI definitions (front-end vs back-end)
- https://selling-guide.fanniemae.com/ — Fannie Mae Selling Guide (DTI guidance, lower-of-mid credit-score convention)
- https://guide.freddiemac.com/ — Freddie Mac Selling Guide (parallel conventions)

### Pattern References

- `https://github.com/cfpb/hmda-platform` — predicate-per-citation pattern (Phase 2 already follows this; Phase 4 composes the predicates without inventing new ones)
- `tests/test_money.py` (Phase 1) — Decimal-discipline test pattern (string construction, exact equality)
- `tests/test_fixtures.py` (Phase 1) — golden-fixture loader pattern (FND-09)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`lib/models.py`** (Phase 1+3): `Loan`, `Schedule`, `Payment`, `Money`, `Rate`. Phase 4 USES; does NOT modify. New Phase 4 Pydantic models (`AffordabilityRequest`, `AffordabilityResponse`, `Household`, `Applicant`, etc.) live in `lib/affordability.py` (scoped per Phase 2 D-08 / Phase 3 discretion convention) until a second consumer needs them.
- **`lib/money.py`** (Phase 1): `to_money(str)`, `quantize_cents(Decimal)`. Every Decimal cents-rounding in `lib/affordability.py` MUST flow through `quantize_cents`. PITI sum is rounded ONCE at the end, not per-component (Phase 3 D-PITFALLS pattern).
- **`lib/amortize.py`** (Phase 3): `build_schedule(loan)` produces `Schedule.monthly_pi`. Forward affordability calls this. Reverse affordability calls `npf.pv` directly with the rate/term/PMT triple.
- **`lib/rules/*`** (Phase 2): 11 predicates, all imported by full path (Phase 2 D-08). Phase 4 is the FIRST consumer of the rule layer (Phase 3 explicitly skipped it per 03-CONTEXT.md line 119).
- **`lib/rules/_loader.py`** (Phase 2): `load_reference()` cached loader with `StaleReferenceWarning`. Phase 4 inherits the staleness warnings via `warnings.catch_warnings()` propagation (D-11).
- **`config/household.example.yml`** (Phase 1, redacted): Phase 4 EXTENDS in place. Existing fields stay (location, applicants, monthly_debts, current_housing_payment); add `escrow:` block + optional `va:` block.
- **`tests/conftest.py`** (Phase 1) + **`tests/fixtures/golden_pmt.json`** (Phase 1) + **`tests/test_amortize.py`** (Phase 3): patterns + fixtures Phase 4 reuses + extends.
- **`pyproject.toml`** (Phase 1): mypy --strict, ruff, pytest, numpy-financial all configured. Phase 4 ADDS no new deps (pure composition over Phase 1/2/3 surface). If planner finds it needs `freezegun` for date-determinism in fixtures, add then.

### Established Patterns

- **One predicate per citation, imported by full path** (Phase 2 D-08): `from lib.rules.va_residual_income import evaluate as va_residual_evaluate`. NEVER `from lib.rules import va_residual_income.evaluate`.
- **Pydantic v2 strict + frozen + extra=forbid** (Phase 1, reinforced Phase 2/3): `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` for all Phase 4 domain models. Mirror Phase 2's `ResidualIncomeResult` shape for `AffordabilityResponse`.
- **Decimal-from-strings, exact equality, no `assertAlmostEqual`** (Phase 1+3): `Decimal("0.43")` not `Decimal(0.43)`. Test fixture `expected` fields are quoted strings.
- **JSON-in / JSON-out CLI at project root** (Phase 3 D-17/18/19): `scripts/affordability.py` argparse + `--input <path>` + lazy-import + Pydantic 6-key envelope on stderr. Subprocess invocation in tests, NOT direct import (Phase 3 D-17 portability).
- **Hand-calculated golden fixtures with `source` URL + citation comments** (Phase 1+2+3): each affordability fixture JSON has `source: ROADMAP.md SC-N` or regulatory citation in a `notes` block.
- **Quantize end-of-period only** (Phase 1 PITFALLS, Phase 3 D-04): one `quantize_cents()` call per money output; never quantize mid-calculation.
- **Pre-commit user-layer block** (Phase 1 FND-04): `config/household.yml` (real file) is gitignored + pre-commit-protected. `config/household.example.yml` is NOT in the block list.
- **Citation-coverage meta-test pattern** (Phase 2 RUL-12/13): every regulatory-citation string in production code maps to at least one fixture. Phase 4 inherits this implicitly — every `blocked_by` citation string format added in Phase 4 MUST have at least one fixture exercising it (D-17 fixture list covers this).

### Integration Points

- **`pyproject.toml`** — no new deps expected. Phase 4 composes existing `numpy-financial`, `pydantic`, `python-dateutil`. Verify mypy --strict + ruff stay clean.
- **`lib/affordability.py`** — new file. Imports: `numpy_financial as npf`, `decimal`, `pydantic`, `lib.models` (Loan, Schedule), `lib.money` (quantize_cents, CENT, MONEY_CONTEXT), `lib.amortize` (build_schedule), `lib.rules.{loan_type, conventional_pmi, fha_mip, va_funding_fee, va_residual_income, usda, atr_qm, fannie_eligibility, freddie_eligibility}` (selective), `lib.rules.types` (LoanType, Region, County), `lib.rules._loader` (warning capture).
- **`scripts/affordability.py`** — new file at project root. Argparse + `AffordabilityRequest.model_validate_json` + dispatch by `mode` field + `print(response.model_dump_json(indent=2))`. Lazy-import `lib.affordability` after argparse. Lazy-import `numpy_financial` only when `mode == "reverse"`.
- **`lib/models.py`** — NO modifications expected. If a planner finds Phase 4 needs a new shared model (e.g., `Household`), prefer `lib/affordability.py` first; promote to `lib/models.py` only on the second consumer (Phase 2 D-07 / Phase 3 discretion convention).
- **`config/household.example.yml`** — extend in place (D-15). New fields: `escrow:` block (`property_tax_monthly`, `insurance_monthly`, `hoa_monthly`); optional `va:` block (`region`, `family_size`, `actual_residual_income`).
- **`tests/test_affordability.py`** — new file. Cases per D-17 fixture list. Subprocess invocation pattern for CLI smoke per Phase 3.
- **`tests/fixtures/affordability/`** — new directory. JSON fixtures per scenario.
- **`tests/conftest.py`** — extend with `affordability_fixture` loader mirroring Phase 3's `amortize_fixture`.

### Phase 5+ downstream consumers (DO NOT BREAK in Phase 4)

- **Phase 5 (ARM):** ARM affordability uses Phase 4's `lib.affordability` at each reset to recompute DTI under the new payment. Phase 4's `AffordabilityRequest` accepts arbitrary `annual_rate` + `term_months`; Phase 5 calls into forward-mode affordability per reset row. Stable contract: `lib.affordability.evaluate_forward(request) -> AffordabilityResponse`.
- **Phase 6 (Refi NPV):** refi NPV does NOT consume affordability directly (sign-convention layer is independent). However, the SKILL.md `evaluate` mode (Phase 10) chains affordability → refi for combined reports. No Phase 4 contract obligation here.
- **Phase 8 (Stress):** rate-shock + income-shock sweeps re-invoke `lib.affordability.evaluate_forward` per grid cell. Vectorization is OPTIONAL (per-cell Python loop is fine for personal-use stress sweeps < 100 cells).
- **Phase 10 (Skill):** `affordability` mode in `.claude/skills/mortgage-ops/modes/affordability.md` routes to `scripts/affordability.py`. Phase 4 should NOT lock the script path in any test that imports `scripts.affordability` — prefer subprocess invocation with a `SCRIPT_PATH` constant per Phase 3 D-17.

</code_context>

<specifics>
## Specific Ideas

- **PITI inputs = caller-supplied monthly $:** matches PROJECT.md "user enters numbers manually as YAML" + "fail loud, no inference" disciplines. % rates and ZIP-keyed lookups deferred to v2 explicitly.
- **PMI/MIP from predicates only:** `conventional_pmi.status` + `fha_mip.compute` are authoritative; caller cannot override. UFMIP financing convention is Claude's discretion at planning time.
- **Single `credit_score: int` per applicant:** treated as the representative (mid-of-three) score; Phase 4 picks `min` across applicants for Fannie LLPA + Freddie eligibility lookups. Three-bureau dict shape OUT of v1.
- **Reverse affordability is one-shot `npf.pv`:** caller pins LTV via `down_payment` + `target_loan_type` + `target_ltv_pct`. No iterative PMI/MIP solve. Round-trip test (SC-2) closes within `Decimal("0.0001")` rate-of-rounding tolerance, dollar amounts equal exactly.
- **`blocked_by` is a single string + `warnings: list[str]`:** matches ROADMAP SC-3 example syntax verbatim (`"blocked_by": "VA-RESIDUAL-WEST-FAMILY-4"`). Priority: loan-type-classify → LTV/CLTV → DTI → ATR/QM → VA residual.
- **VA residual citation format STABLE:** `f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"` (Phase 2 D-11). `forward_va_residual_fail.json` fixture exercises this verbatim.
- **DTI cap = caller-supplied `max_dti` per request, no defaults.** ROADMAP SC-2 example uses 0.43; per-loan-type defaults YAML deferred to v2.
- **`config/household.example.yml` is FINAL after Phase 4** (AFFD-09). Any subsequent schema growth requires its own discuss-phase pass.
- **CLI shape mirrors Phase 3's `scripts/amortize.py`:** `--input <path>` only, lazy-import, Pydantic 6-key envelope on validation errors (Phase 3 D-19 / WR-02 closure).
- **Tests exercise both joint and single-applicant cases** (SC-5 + D-07 reduce to `applicants` length 1 vs 2 — same code path).

</specifics>

<deferred>
## Deferred Ideas

- **% rate-based PITI inputs (`property_tax_rate_pct`, `insurance_rate_pct`):** v2. Today caller supplies monthly $.
- **ZIP / county-keyed property-tax + insurance lookup tables:** v2 (PROP-02 already in REQUIREMENTS.md "v2 Requirements / Property Valuation").
- **Three-bureau credit-score dict (`equifax / experian / transunion`) per applicant:** out of scope for v1 personal-use. Add only if a real underwriting decision diverges from the single-int approximation.
- **Income-type modeling (W-2 vs self-employed vs 1099 vs alimony 2-year-averaging):** out of scope for v1. PROJECT.md "Out of Scope" implicitly via "personal-use, not commercial DU/LPA replication".
- **Per-loan-type DTI cap YAML in `data/reference/`:** v2 if bare `max_dti` input UX becomes painful. Phase 4 v1 always takes caller-supplied `max_dti`.
- **PMI auto-termination period advisory (`pmi_terminates_at_period: int`):** add when first downstream consumer (Phase 6 refi or Phase 8 stress) needs it. `conventional_pmi.status` already returns the threshold — Phase 4 just doesn't surface it in the response yet.
- **CLTV junior-lien structured shape (`list[{lien_holder, balance, position}]`):** v2. v1 uses `junior_liens: list[Money]` (sum).
- **Iterative PMI-LTV reverse solver (bisection):** out of scope. Caller pins LTV via `target_ltv_pct`. Add if SC-2 round-trip tolerance proves insufficient.
- **`AffordabilityResponse` advisory tier (`soft_blockers` separate from `warnings`):** v2 if `warnings: list[str]` proves too flat. v1 keeps the single warnings list.
- **Auto-finance UFMIP into principal vs caller-pre-finances:** Claude's discretion at planning time (D-03). Document whichever ships.
- **Stdin-based CLI input:** v2 (inherits Phase 3 D-18 deferral).

</deferred>

---

*Phase: 04-affordability*
*Context gathered: 2026-04-30*
