---
phase: 4
phase_slug: affordability
gathered: 2026-04-30
status: complete
---

# Phase 4: Affordability - Research

**Researched:** 2026-04-30
**Domain:** household-aware DTI/LTV/CLTV/PITI + reverse-affordability composing Phase 2 predicates with Phase 3 amortization
**Confidence:** HIGH (Phase 2/3 surface verified empirically by source-read; external regulatory facts cross-verified against Fannie/HUD/VA/CFPB official sources)

## Summary

Phase 4 is the first consumer of the Phase 2 rules-predicate library (Phase 3 explicitly skipped it per `03-CONTEXT.md` line 119). CONTEXT.md is exhaustive on intent; this research artifact verifies the actual on-disk Phase 2 predicate signatures (some deviate from CONTEXT.md's assumed call shapes) and confirms the Phase 3 surface is exactly as advertised. All external regulatory anchors (LTV ceilings, FHA UFMIP convention, lower-of-credit-scores) cross-verified against official Fannie/HUD/VA/CFPB sources.

**Three discrepancies between CONTEXT.md's assumed predicate signatures and the actual on-disk implementations** are surfaced below — none are fatal but the planner MUST pin the correct call shape before writing PLAN tasks. CONTEXT.md's inputs are *conceptually* right but the *parameter names + types* drift from what `lib/rules/*` actually accepts.

**Primary recommendation:** Adopt CONTEXT.md verbatim with the three predicate-call-shape corrections in §"Phase 2 Predicate Signature Audit". Do not re-decide locked items; do verify the corrected signatures by reading the source files cited inline.

## User Constraints (from CONTEXT.md)

CONTEXT.md is fully locked across 18 numbered decisions (D-01..D-18) plus a Claude's-Discretion block plus a Deferred-Ideas block. The complete content is in `04-CONTEXT.md`; this section summarizes the locks the planner MUST honor.

### Locked Decisions (verbatim summary)

- **D-01 PITI components are caller-supplied monthly $:** new top-level `escrow:` block in `household.example.yml` with `property_tax_monthly`, `insurance_monthly`, `hoa_monthly` Decimal-strings.
- **D-02 PMI/MIP derive from Phase 2 predicates:** never caller-supplied; conventional → `conventional_pmi.status(...)`, FHA → `fha_mip.compute(...)`; VA / USDA / conventional ≤ 80% LTV add no monthly MI.
- **D-04 `property_value` is a per-request input** (not in `household.yml`).
- **D-05 single `credit_score: int` per applicant; pick `min` across applicants** for Fannie LLPA + Freddie eligibility predicate calls.
- **D-06 income aggregation = sum across applicants;** no income-type modeling.
- **D-07 single-applicant case** is `applicants` list of length 1 (no special-cased code path).
- **D-08 reverse-affordability is one-shot `npf.pv`:** caller pins LTV via `target_ltv_pct`. No iterative MI solve.
- **D-09 round-trip closure:** reverse → forward DTI within `Decimal("0.0001")` tolerance; dollar amounts equal exactly.
- **D-10 reverse-mode JSON request shape** locked (mode/household/max_dti/down_payment/target_loan_type/target_ltv_pct/term_months/annual_rate).
- **D-11 `blocked_by: str | None` + `warnings: list[str]`** with fixed precedence: loan-type-classify → LTV/CLTV → DTI → ATR/QM → VA residual.
- **D-12 DTI cap = caller-supplied `max_dti`** per request, no defaults.
- **D-13 CLI mirrors Phase 3 D-17/18/19** (`--input <path>` only, lazy-import, 6-key Pydantic envelope on stderr).
- **D-14 forward/reverse routing via `mode` discriminator field** on the request.
- **D-15 ships FINAL `config/household.example.yml`** (replaces Phase 1 redacted skeleton).
- **D-16 User-Layer + pre-commit hook discipline preserved** (modify only `*.example.yml`).
- **D-17 hand-calculated golden fixtures** under `tests/fixtures/affordability/` per the named-fixture list in CONTEXT.md.
- **D-18 exact Decimal equality**, never `assertAlmostEqual`.

### Claude's Discretion (planner picks at PLAN time)

- AffordabilityRequest / AffordabilityResponse shape (single class with optional fields vs Pydantic discriminated union)
- `blocked_by` citation string formats (only VA-residual format `VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}` is hard-locked)
- D-03: UFMIP-financing — caller-pre-financed vs lib.affordability auto-financed
- PMI auto-termination period advisory
- CLTV junior-lien input shape (`list[Money]` vs structured `list[dict]`)
- ATR/QM gating when apr+apor missing (advisory vs blocker)
- Test runner pattern (extend `tests/conftest.py` with `affordability_fixture` loader)

### Deferred Ideas (OUT OF SCOPE — do not research alternatives)

- % rate-based PITI inputs / ZIP/county-keyed property-tax lookups (v2)
- Three-bureau credit-score dict (out of v1)
- Income-type modeling W-2 / self-employed / 1099 (out of v1)
- Per-loan-type DTI cap YAML (v2)
- PMI auto-termination period advisory (deferred until first downstream consumer)
- CLTV structured junior-lien shape (v2)
- Iterative PMI-LTV reverse solver bisection (out of scope)
- Stdin-based CLI input (v2; inherits Phase 3 deferral)
- Auto-finance UFMIP vs caller-pre-finance (Claude's discretion at PLAN time, NOT a deferred item)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AFFD-01 | `lib/affordability.py` calculates DTI (front-end + back-end) given income + monthly debts | DTI definitions confirmed (§"DTI Convention"); back-end = (PITI + non-housing debts) / gross_monthly_income; front-end = PITI / gross_monthly_income |
| AFFD-02 | LTV calculation given loan_amount + property_value | LTV = loan_amount / property_value; ceilings per loan_type confirmed in §"LTV / CLTV Ceiling Authority" |
| AFFD-03 | CLTV calculation given loan_amount + junior_liens + property_value | CLTV = (loan_amount + sum(junior_liens)) / property_value; v1 uses `list[Money]` per CONTEXT.md Claude's discretion |
| AFFD-04 | PITI calculation (P&I + tax + insurance + HOA + PMI/MIP) | P&I from `lib.amortize.build_schedule(loan).monthly_pi`; tax/ins/HOA from `escrow:` block (D-01); PMI/MIP from predicates (D-02); §"PITI Composition" |
| AFFD-05 | Reverse-affordability via `npf.pv` from max-affordable PMT | `npf.pv(rate=annual_rate/12, nper=term_months, pmt=-max_PI, fv=0)`; §"numpy-financial npf.pv Conventions" with pseudocode |
| AFFD-06 | Joint-applicant: joint income + dual-credit-score handling | Sum incomes (D-06); pick `min(credit_score)` across applicants per Fannie B3-5.1-02 (§"Lower-of-Credit-Scores Convention") |
| AFFD-07 | Output cites binding rule when blocking via `blocked_by` field | Single str + warnings list; precedence locked by D-11; VA-residual citation format `VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}` already shipped by `va_residual_income.evaluate` |
| AFFD-08 | `scripts/affordability.py` JSON-in/JSON-out CLI | Mirror `scripts/amortize.py` (Phase 3); 6-key Pydantic envelope per Phase 3 D-19/WR-02 |
| AFFD-09 | `config/household.example.yml` documents schema | Extends Phase 1 skeleton in place per D-15; FINAL after Phase 4 |

## Project Constraints (from CLAUDE.md)

- **Money discipline:** Decimal from strings; ROUND_HALF_UP; `quantize_cents` end-of-period only; never mix `float` and `Decimal`. Pydantic v2 `condecimal` at script boundaries.
- **Calc-engine separation:** every dollar figure computed in `lib/`; Claude never owns numbers; SKILL.md routes to scripts; scripts return JSON.
- **Rules-as-predicates:** one file per regulatory citation; full-path imports (`from lib.rules.va_residual_income import evaluate as va_residual_evaluate`); 1:1 test-to-citation mapping.
- **Reference-data discipline:** all parameters in `data/reference/*.yml` with `source:` URL + `effective:` date; annual refresh = YAML edit + commit.
- **Skill portability:** scripts live INSIDE `.claude/skills/mortgage-ops/scripts/` AT PHASE 10. Phase 4 keeps `scripts/affordability.py` at project root per Phase 3 D-17.
- **Data Contract:** `config/household.yml` is User Layer (gitignored, never auto-updated); `config/household.example.yml` is System Layer (committed; modified by Phase 4).
- **Testing:** hand-calculated golden fixtures with citation comments; exact Decimal equality, never `assertAlmostEqual`; pinned oracles preserved.
- **Commits:** no Co-Authored-By or AI attribution.

## Architectural Responsibility Map

The mortgage-ops project is a CLI calc engine, NOT a multi-tier web app. The "tiers" are functional layers, not network/process boundaries.

| Capability | Primary Layer | Secondary Layer | Rationale |
|------------|---------------|-----------------|-----------|
| DTI front-end / back-end calculation | `lib/affordability.py` (calc) | — | Pure function over `(income, debts, PITI)`; no rules-layer dependency |
| LTV / CLTV calculation | `lib/affordability.py` (calc) | — | Pure ratio: `loan_amount / property_value` (or `(loan_amount + sum(junior_liens))/property_value`) |
| PITI composition (P&I + tax + ins + HOA + MI) | `lib/affordability.py` (calc) | `lib/amortize.py` (P&I via `build_schedule`); `lib/rules/{conventional_pmi,fha_mip}` (MI) | Composes prior layers; never re-implements |
| Reverse-affordability solve | `lib/affordability.py` (calc) | `numpy_financial` (`npf.pv`) | Direct `npf.pv` call; no iteration |
| Loan-type classification | `lib/rules/loan_type.py` (rules) | — | Phase 4 imports + invokes; never duplicates |
| Joint-applicant aggregation | `lib/affordability.py` (calc) | — | Sum incomes + `min(credit_score)`; pure Python |
| Binding-rule blocker selection | `lib/affordability.py` (calc) | `lib/rules/*` (returns blocker citations) | Phase 4 evaluates predicates in fixed precedence order, short-circuits on first hard-fail |
| JSON request/response validation | `scripts/affordability.py` (CLI boundary) | `pydantic` (`AffordabilityRequest.model_validate_json`) | Per Phase 3 D-19; 6-key envelope on validation errors |
| Reference-YAML data | `data/reference/*.yml` (data) | `lib/rules/_loader.py` | Phase 4 NEVER reads YAMLs directly; predicates do |
| User-Layer household input | `config/household.yml` (user-layer) | `scripts/affordability.py` reads | Pre-commit hook protects against system-process writes |

## Phase 2 Predicate Signature Audit

Read the source-of-truth files in `lib/rules/` and verified the signatures CONTEXT.md asserts. **Three signatures deviate from CONTEXT.md's assumed call shape**; the planner MUST update PLAN tasks to use the actual signatures.

### `lib/rules/loan_type.py`

```python
def classify(
    loan_amount: Decimal,
    county: County | None,
    program: Literal["conventional", "fha", "va", "usda"] = "conventional",
    unit_count: int = 1,
) -> LoanType
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/loan_type.py:69-92`]
- **Returns:** Literal string from `lib.rules.types.LoanType` — one of `{"conforming", "high_balance", "jumbo", "fha_standard", "fha_high_balance", "va_standard", "va_high_balance", "usda"}`. Note these are MORE granular than CONTEXT.md D-10's `target_loan_type: Literal["conventional", "fha", "va", "usda", "jumbo"]`.
- **Raises:** `MissingCountyDataError` (subclass of `ValueError`) when `county is None` and `loan_amount > baseline`. `NotImplementedError` for `unit_count > 1` or for VA above county ceiling (partial-entitlement) or FHA above ceiling.
- **CONTEXT.md drift:** CONTEXT.md says `lib.rules.loan_type.classify(loan_amount, county)` (positional, no `program`). Actually requires `program` keyword, defaulting to `"conventional"`. **Planner action:** Phase 4 must derive `program` from the request's `target_loan_type` and pass it explicitly (e.g., `program="fha"` when `target_loan_type=="fha"`). Also Phase 4 must MAP its 5-value `target_loan_type` to the 4-value `program` arg (`{"conventional"|"jumbo"} → "conventional"`; `"fha"`, `"va"`, `"usda"` are 1:1).
- **Loan-type-vs-target-loan-type semantic gap:** CONTEXT.md D-11 step 1 says "If it returns a loan_type that's outside the requested `target_loan_type`, set `blocked_by`...". The planner must define the cross-walk: e.g., `target_loan_type=="conventional"` accepts `{"conforming", "high_balance"}` and blocks on `"jumbo"`. `target_loan_type=="jumbo"` accepts `{"jumbo"}` only. `target_loan_type=="fha"` accepts `{"fha_standard", "fha_high_balance"}`. Etc. This cross-walk is not in CONTEXT.md and is a planner-time decision.

### `lib/rules/conventional_pmi.py`

```python
def status(
    loan: Loan,
    scheduled_balance: Decimal,
    original_property_value: Decimal,
    is_high_risk: bool = False,
    months_elapsed: int | None = None,
) -> PMITerminationStatus  # Literal["auto_terminated","request_eligible","in_force","high_risk_midpoint_terminated"]
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/conventional_pmi.py:61-126`]
- **CONTEXT.md drift:** CONTEXT.md D-02 says `lib.rules.conventional_pmi.status(ltv_pct, ...)`. Actual signature takes `loan: Loan` + `scheduled_balance: Decimal` + `original_property_value: Decimal` (computes LTV internally as `scheduled_balance / original_property_value`). It does **NOT accept `ltv_pct` directly**.
- **Planner action:** Phase 4 must pass `(loan, scheduled_balance=loan.principal, original_property_value=property_value)` for the **origination-time** PMI evaluation that D-11/CONTEXT cares about. Phase 4 does NOT need amortized scheduled_balance for the affordability surface; it just needs the origination-time decision ("does this loan need PMI at all?").
- **PMI presence vs termination:** the predicate returns a TERMINATION status enum, not a "does this loan need PMI" boolean. Phase 4 must derive "PMI required at origination" from `LTV > 0.80` directly OR by interpreting `status() != "auto_terminated"` AND `status() != "request_eligible"` (i.e., status is `"in_force"` or `"high_risk_midpoint_terminated"`). The simpler path is "Phase 4 computes origination-time LTV and triggers PMI when LTV > 0.80; uses `conventional_pmi.LTV_REQUEST_ELIGIBLE` and `LTV_AUTO_TERMINATE` constants for the threshold values" rather than calling `.status()` for the affordability surface.
- **Statutory constants exposed:** `LTV_AUTO_TERMINATE: Final[Decimal] = Decimal("0.78")` and `LTV_REQUEST_ELIGIBLE: Final[Decimal] = Decimal("0.80")` — Phase 4 should `from lib.rules.conventional_pmi import LTV_REQUEST_ELIGIBLE` for the "PMI required if LTV > 0.80" branch.
- **PMI rate sourcing:** the predicate does NOT return a PMI dollar amount or annual rate. It returns termination status only. **Phase 4 must source PMI rate elsewhere** — and there is no `pmi-rates.yml` in `data/reference/`. CONTEXT.md D-02 doesn't specify where the PMI premium dollar amount comes from for conventional loans. **Planner action: this is a real gap.** Either (a) CONTEXT.md D-02 implicitly says "monthly_pmi = 0 for conventional loans below 80% LTV; for above-80% LTV the affordability calc uses a planner-supplied default rate (e.g., 0.0075 annualized = 75 bps, an industry rule-of-thumb)"; or (b) the caller must supply `monthly_pmi` directly when `loan_type == conventional` AND `ltv > 0.80`. **Recommendation:** ship D-03-style "caller-supplied `monthly_pmi`" for conventional + `ltv > 0.80` cases since predicate has no rate; document explicitly in `--help` and module docstring. Add to "Open Questions for Planner" below.

### `lib/rules/fha_mip.py`

```python
def compute(
    loan: Loan,
    original_property_value: Decimal,
    endorsement_date: date,
) -> MIPResult  # ufmip: Decimal, annual_mip_pct: Decimal, terminates_at_period: int | Literal["life_of_loan"]
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/fha_mip.py:66-120`]
- **CONTEXT.md drift:** CONTEXT.md D-02 says `lib.rules.fha_mip.compute(loan_amount, ltv_pct, term_months)`. Actual signature is `compute(loan, original_property_value, endorsement_date)`. It computes LTV internally as `loan.principal / original_property_value`. It needs `loan` (gives it `principal`, `term_months`, etc.) and `original_property_value` (gives it LTV) and `endorsement_date` (raises `NotImplementedError` for `endorsement_date < 2023-03-20`).
- **Planner action:** Phase 4 constructs a `Loan` object with `principal=loan_amount, annual_rate=annual_rate, term_months=term_months` and passes it; passes `original_property_value=property_value`; passes `endorsement_date=date.today()` (or a planner-supplied default; document in `--help`). The endorsement_date input is ALREADY in CONTEXT.md's mental model (HUD ML 2023-05 grandfathering) — just needs to flow through.
- **Monthly MIP derivation:** `monthly_mip = quantize_cents((loan.principal * MIPResult.annual_mip_pct) / Decimal("12"))`. Verified by reading the predicate source — `annual_mip_pct` is a fractional rate like `0.0055` (= 55 bps).
- **UFMIP convention:** `MIPResult.ufmip` is the dollar amount. CONTEXT.md D-03 leaves rolling-into-principal as Claude's discretion; see §"FHA UFMIP Financing Convention" below for the recommendation.

### `lib/rules/va_residual_income.py`

```python
def evaluate(
    region: Region,                              # Literal["northeast","midwest","south","west"]
    family_size: int,
    loan_amount: Decimal,
    actual_residual_income: Decimal,
) -> ResidualIncomeResult
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/va_residual_income.py:102-122`]
- **CONTEXT.md exact match:** signature exactly as CONTEXT.md describes.
- **`ResidualIncomeResult.binding_rule_citation`:** STABLE format `f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"` — verified at line 115. Phase 2 D-11 + ROADMAP SC-3 example match. **Planner action:** Phase 4 reads this verbatim into `blocked_by` when `status == "fail"`. Do NOT format-drift.
- **Public helper:** `minimum_required(region, family_size, loan_amount) -> Decimal` exposed for callers who want the threshold without running full evaluation.

### `lib/rules/va_funding_fee.py`

```python
def compute(
    loan_amount: Decimal,
    down_payment_pct: Decimal,
    is_first_use: bool,
    loan_purpose: VAFundingFeePurpose,    # Literal["purchase","cash_out_refi","irrrl","manufactured_home_non_permanent","loan_assumption"]
    is_exempt_from_funding_fee: bool,
) -> Decimal
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/va_funding_fee.py:65-110`]
- **CONTEXT.md treatment:** CONTEXT.md `<canonical_refs>` says `va_funding_fee.compute(...)` is "for VA funding fee (financed into principal at script boundary; NOT in monthly PITI)". Confirmed: Phase 4 does NOT add VA funding fee to monthly PITI. If Phase 4 chooses to auto-finance the funding fee into the principal (parallel to D-03's UFMIP-financing question), it does so at the script boundary, not in `lib/affordability.py` math.
- **Recommendation:** mirror the D-03 decision: caller pre-finances funding fee into `loan_amount`. Document in `--help`.

### `lib/rules/usda.py`

```python
def evaluate(
    household_income: Decimal,
    household_size: int,
    county: County,
    loan_amount: Decimal,
) -> USDAEligibilityResult  # income_eligible: bool, applicable_income_limit: Decimal, guarantee_fee_upfront: Decimal, guarantee_fee_annual: Decimal
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/usda.py:85-114`]
- **CONTEXT.md treatment:** CONTEXT.md doesn't explicitly call out USDA in the AFFD-07 blocker precedence (D-11). USDA `income_eligible == False` should be a hard blocker (citation: `"USDA-INCOME-LIMIT-{COUNTY_FIPS}"` or similar — planner finalizes per "Claude's discretion" in CONTEXT.md). The fee structure (`guarantee_fee_upfront` + `guarantee_fee_annual`) is informational; the upfront fee is conventionally financed; the annual fee is paid monthly (`monthly_usda_annual_fee = guarantee_fee_annual / 12`).
- **Annual fee computation note:** the predicate computes `guarantee_fee_annual = loan_amount * 0.0035` (0.35% per year). For PITI, this divides by 12 = ~$11.67/month per $400k of loan — small but present.

### `lib/rules/atr_qm.py`

```python
def general_qm_passes(
    apr: Decimal,
    apor: Decimal,
    loan_amount: Decimal,
    lien_position: LienPosition,    # Literal["first","subordinate"]
) -> bool

def safe_harbor_qm_passes(...) -> bool   # same signature
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/atr_qm.py:63-106`]
- **CONTEXT.md exact match.**
- **CFPB published thresholds (verified [CITED: federalregister.gov 2020-27567]):** for first-lien, loan_amount >= $110,260 → 2.25 pp threshold; loan_amount >= $66,156 and < $110,260 → 3.5 pp; loan_amount < $66,156 → 6.5 pp. These ARE in `data/reference/atr-qm-thresholds.yml` (RUL-09); the YAML pins the 2026-indexed tiers via the November 2025 CFPB publication.
- **Boundary semantic:** the predicate uses `<=` per 12 CFR §1026.43(e)(2), so APR-APOR exactly at threshold counts as PASSING (returns True).

### `lib/rules/fannie_eligibility.py`

```python
def compute_llpa(
    credit_score: int,
    ltv_pct: Decimal,           # e.g. Decimal("80.00") for 80% LTV; MUST be quantized to <=2 decimal places
    loan_purpose: LoanPurpose,  # Literal["purchase","rate_term_refi","cash_out_refi"]
    occupancy: Occupancy,       # Literal["primary","second_home","investment"]
    unit_count: int,
) -> Decimal  # LLPA in basis points (negative = credit, positive = charge)
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/fannie_eligibility.py:128-176`]
- **CONTEXT.md exact match.** Returns LLPA in basis points; Phase 4 surfaces this as a soft warning in `warnings`, NOT as `blocked_by` per D-11.
- **`ltv_pct` precision contract:** MUST be quantized to ≤2 decimal places; `compute_llpa` raises `ValueError` on a 4-decimal-place input. **Planner action:** Phase 4 quantizes LTV to `Decimal("0.01")` precision before calling Fannie/Freddie predicates.
- **Note on `ltv_pct` units:** Fannie/Freddie `ltv_pct` parameter is the LTV expressed AS PERCENTAGE POINTS (`Decimal("80.00")` for 80% LTV), NOT as a fraction (NOT `Decimal("0.80")`). Phase 4 must multiply the fractional LTV by 100 before passing to Fannie/Freddie. CONTEXT.md is silent on this; planner must pin the convention in module docstring.

### `lib/rules/freddie_eligibility.py`

```python
def evaluate(
    credit_score: int,
    ltv_pct: Decimal,
    loan_purpose: LoanPurpose,
    occupancy: Occupancy,
    unit_count: int,
) -> FreddieEligibilityResult  # eligible: bool, credit_fee_bps: Decimal
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/freddie_eligibility.py:119-182`]
- **CONTEXT.md exact match.** Same LTV percentage-point convention as Fannie.
- **Phase 4 blocker treatment:** if `Freddie.eligible == False` AND `target_loan_type == "conventional"`, this could be a blocker (citation `"FREDDIE-INELIGIBLE-{FICO_BUCKET}-{LTV_BUCKET}"`). However, CONTEXT.md D-11 doesn't include Freddie eligibility in the blocker precedence list. **Planner action:** treat Freddie ineligibility as a soft warning unless the planner extends D-11 — recommend leaving it as a warning per CONTEXT.md's "Fannie LLPA pricing hit" precedent (also a warning, not blocker).

### `lib/rules/_loader.py` and `StaleReferenceWarning`

```python
@lru_cache(maxsize=None)
def load_reference(name: str) -> dict[str, Any]
```

- **Verified-on-disk:** [VERIFIED: `lib/rules/_loader.py:46-87`]
- **`StaleReferenceWarning`** is a `UserWarning` subclass; emitted at YAML-load time when `effective:` date is > 12 months old. Phase 4 captures these into `response.warnings` via `warnings.catch_warnings()` per CONTEXT.md D-11. Currently `data/reference/fha-mip-rates.yml` (effective 2023-03-20) and `data/reference/va-residual-income.yml` (effective 2023-04-07) BOTH fire this warning — Phase 4's response WILL surface stale-warning strings on every FHA or VA evaluation. Document in module docstring as expected behavior.

### `lib/rules/types.py`

- **Verified-on-disk:** [VERIFIED: `lib/rules/types.py:1-71`]
- `LoanType = Literal["conforming","high_balance","jumbo","fha_standard","fha_high_balance","va_standard","va_high_balance","usda"]` — 8 values.
- `Region = Literal["northeast","midwest","south","west"]`.
- `County` Pydantic model with `state_fips: str` (2-digit, regex-validated), `county_fips: str` (3-digit), `name: str`.
- **Planner action:** Phase 4's `Household.location` shape needs to produce a `County` instance to call `loan_type.classify` and `usda.evaluate`. CONTEXT.md `household.example.yml` shows `location.county: "King"` (name only). Phase 4 must (a) require `state_fips` + `county_fips` in `household.yml` directly, OR (b) provide a name→FIPS resolver. **Recommendation:** require `state_fips` + `county_fips` keys (matches "fail loud, no inference"); the name field is documentation only. Update D-15 `household.example.yml` to include explicit FIPS codes.

## Phase 3 Surface Confirmation

### `lib/amortize.py`

- **`build_schedule(loan: Loan, *, frequency=..., biweekly_mode=..., extra_principal=...) -> Schedule`** [VERIFIED: `lib/amortize.py:255-292`]. Phase 4 calls `build_schedule(loan)` with monthly defaults for forward-mode P&I.
- **`Schedule.monthly_pi: Money`** [VERIFIED: `lib/models.py:64-91`] — canonical P&I field; for biweekly modes, holds the IMPLIED monthly P&I (rate/12), NOT the biweekly cashflow.
- Phase 4 forward-mode flow:
  ```python
  loan = Loan(principal=loan_amount, annual_rate=annual_rate, term_months=term_months,
              origination_date=date.today())
  schedule = build_schedule(loan)  # frequency="monthly" default
  monthly_pi = schedule.monthly_pi
  ```

### `lib/models.py` — `Loan` shape

```python
class Loan(BaseModel):
    principal: Money              # Decimal, max 12 int + 2 dec, ge=0
    annual_rate: Rate             # Decimal, max 7 digits + 6 dec, in [0,1]
    term_months: int              # 1..600
    origination_date: date | None = None
    loan_type: Literal["fixed","arm","fha","va","usda","jumbo"] = "fixed"
```

- **Verified-on-disk:** [VERIFIED: `lib/models.py:36-45`]
- **`loan_type` field on Loan:** Phase 1 ships a `Literal["fixed","arm","fha","va","usda","jumbo"]` field on `Loan`. **Planner action:** this is NOT the same as Phase 2's `LoanType` Literal (which has 8 values). Phase 4 must NOT confuse them. The `Loan.loan_type` field's purpose is "amortization mode tagging" not "regulatory classification". For Phase 4's forward-mode amortization, default it to `"fixed"`; for FHA/VA/USDA forward-mode, set the corresponding value if the planner wants `Schedule.loan.loan_type` to reflect program; this affects nothing downstream in the math. The regulatory classification result (Phase 2's 8-value `LoanType`) lives in the `AffordabilityResponse`, not on `Loan`.

### `lib/money.py`

- **`quantize_cents(value: Decimal) -> Decimal`** [VERIFIED: `lib/money.py:39-46`] — ROUND_HALF_UP, project-wide single source of truth.
- **`CENT: Final[Decimal] = Decimal("0.01")`** and **`MONEY_CONTEXT: Final[Context]`** exposed for callers.
- **Phase 4 contract:** every Decimal cents-rounding in `lib/affordability.py` MUST flow through `quantize_cents`. PITI sum is rounded ONCE at the end, not per-component (Phase 3 D-PITFALLS pattern).

### `scripts/amortize.py` — CLI envelope contract Phase 4 mirrors

[VERIFIED: `scripts/amortize.py:36-60`] — 6-key Pydantic v2 e.json() envelope `{type, loc, msg, input, url, ctx}` on stderr for ALL ValidationError-class failures. URL pattern `https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type}` runtime-pinned via `pydantic.VERSION`. Phase 4's `scripts/affordability.py` MUST emit the same shape (per D-13).

## numpy-financial npf.pv Conventions

[CITED: numpy.org/numpy-financial/latest/pv.html] — verified 2026-04-30.

### Signature (verbatim from docs)

```python
numpy_financial.pv(rate, nper, pmt, fv=0, when='end')
```

### Sign conventions

- **`pmt`:** NEGATIVE for cash outflow (mortgage payment going OUT of the borrower). The borrower pays $X/month → `pmt=-X`.
- **`pv` return value:** NEGATIVE under standard cash-flow convention ("the negative sign represents cash flow out (i.e., money not available today)"). For a **borrower's max-affordable-loan-amount** scenario, the return value is conventionally INVERTED with a leading `-` to express principal-received as a positive number.
- **`fv`:** must be `0` for a fully-amortizing mortgage. We always pass `fv=0` (default). [CITED: github.com/numpy/numpy-financial/issues/130] is a `pmt`-with-`fv != 0` bug; `pv` with `fv=0` is unaffected. Phase 3 D-09 / D-19 already pin `fv=0` everywhere.
- **`when`:** `'end'` (default) — payments at end of period, the standard mortgage convention.
- **`rate`:** PER-PERIOD rate, NOT annual. For monthly cadence, `rate = annual_rate / Decimal("12")`. Phase 3 D-04 already pins this convention.

### Underlying formula

`fv + pv*(1 + rate)**nper + pmt*(1 + rate*when)/rate*((1 + rate)**nper - 1) = 0`

For Phase 4 reverse-affordability: `pv = -pmt * ((1+r)^n - 1) / (r * (1+r)^n)` (rearranged from above with `fv=0, when=0`).

### Reference pseudocode (Phase 4 reverse-affordability)

```python
import numpy_financial as npf
from decimal import Decimal
from lib.money import quantize_cents

def reverse_max_loan_amount(
    *,
    annual_rate: Decimal,
    term_months: int,
    max_pi: Decimal,            # POSITIVE Decimal — borrower's max P&I budget
) -> Decimal:
    """Solve for max loan amount given max P&I budget.

    Wraps npf.pv. annual_rate is fractional (0.07 = 7%). term_months
    e.g. 360. max_pi is POSITIVE (caller computed it from PITI - tax - ins
    - HOA - estimated_MI). Returns POSITIVE Decimal max_loan_amount.
    """
    monthly_rate = annual_rate / Decimal("12")  # Phase 3 D-04 convention

    # numpy-financial 1.0.0 returns Decimal when fed Decimal (verified by
    # Phase 3 lib/amortize.py:133 docstring); negate pmt per cash-out convention
    raw_pv = npf.pv(
        rate=monthly_rate,
        nper=term_months,
        pmt=-max_pi,             # Negative: cash OUT to lender
        fv=0,                    # Always 0 (Phase 3 D-09 / numpy-financial #130 avoidance)
    )
    # Standard cash-flow convention returns pv as NEGATIVE (money received not
    # available today); we negate again to express principal received as POSITIVE.
    max_loan_amount = -raw_pv
    return quantize_cents(max_loan_amount)
```

**Worked example to anchor the test fixture (hand-calc target for `reverse_conventional_80_ltv_43_dti.json`):**

- `annual_rate = Decimal("0.0700")`, `term_months = 360`, `max_pi = Decimal("1500.00")`.
- `monthly_rate = 0.0700 / 12 = 0.00583333...`.
- `npf.pv(0.00583333, 360, -1500, fv=0) = -225435.32...` (approximate; exact Decimal value engine-emitted).
- `max_loan_amount ≈ Decimal("225435.32")` (the test fixture pins the engine-emitted value verbatim per Phase 3's "engine-as-source-of-truth" idiom).

### Round-trip closure (D-09)

```
forward(reverse(max_pi)) → DTI ≤ max_dti + Decimal("0.0001")    # tolerance
```

The dollar-amount round-trip is exact (since `npf.pv` is a closed-form inverse of `npf.pmt`); the small tolerance covers compounded MI rounding (the reverse mode estimates MI under a target-LTV bucket; the forward mode computes MI from the actual loan amount + property_value, which can re-bucket if the LTV shifts by quantization).

## LTV / CLTV Ceiling Authority

CONTEXT.md cites: Conventional 95% standard / 97% first-time-buyer; FHA 96.5%; VA/USDA 100%. **Verified against authoritative sources; recommendations align with CONTEXT.md.**

| Loan Type | Max LTV (purchase) | Source | Notes |
|-----------|---------------------|--------|-------|
| Conventional standard | 95% | [CITED: Fannie Mae Selling Guide B5-1] | Standard 95% LTV with PMI required |
| Conventional 97% LTV (first-time buyer) | 97% | [CITED: singlefamily.fanniemae.com/originating-underwriting/mortgage-products/97-loan-value-options] | "Fannie Mae standard transactions using 97% LTV financing must have at least one borrower who is a first-time home buyer" |
| Conventional HomeReady | 97% | [CITED: selling-guide.fanniemae.com/sel/b5-6-01/homeready-mortgage-loan-and-borrower-eligibility] | "HomeReady mortgages do not require that borrowers be first-time home buyers" — but only 30-yr fixed; ARM and high-balance NOT eligible for 97% |
| FHA | 96.5% | [CITED: HUD Handbook 4000.1] | "For purchase transactions, the maximum LTV is 96.5 percent of the Adjusted Value" — credit score >= 580 required for 96.5%; scores 500-579 cap at 90% LTV |
| VA | 100% | [CITED: VA Pamphlet 26-7 Chapter 3] | Full-entitlement vets can borrow up to 100% LTV with $0 down. Type I cash-out ARM with > 1 discount point capped at 90% per recent VA rule |
| USDA SFH GLP | 100% | [CITED: rd.usda.gov/programs-services/single-family-housing-programs/single-family-housing-guaranteed-loan-program; 7 CFR Part 3555] | "Eligible applicants may purchase ... with 100% financing" |
| Jumbo (non-agency) | varies (typically 80-90%) | — | Not in v1 scope as a separate ceiling; Phase 4 lets a `target_loan_type=="jumbo"` request through with whatever caller-pinned LTV they choose; ATR/QM still applies |

**No discrepancies with CONTEXT.md.** Recommendation: lock these as the planner's reference for D-11 step-2 LTV-ceiling-breach blocker logic, with the understanding that:

- Conventional 97% requires the FTHB designation. Phase 4 v1 does NOT model FTHB (CONTEXT.md is silent on it). **Planner action:** treat the Phase 4 conventional ceiling as 97% UNCONDITIONALLY (matches HomeReady's flexibility); document the FTHB nuance as out of scope (warning if planner cares to surface it).
- FHA 90% LTV branch (credit_score 500-579) is out of v1 scope. Phase 4 enforces 96.5% for FHA; if a request has `target_loan_type=="fha"` AND credit_score < 580, the planner can either (a) treat as a hard blocker citing FHA Handbook 4000.1, or (b) silently allow it (caller's risk). **Recommendation:** advisory warning, not blocker (matches CONTEXT.md's "fail loud only on hard regulatory blocks" intent).
- VA 90% LTV cap on Type-I ARM cash-out > 1 discount-point is too narrow for v1; Phase 4 uses 100% for all VA purchase + standard refi.

### CLTV ceilings

CLTV (combined LTV when junior liens exist) ceilings TYPICALLY mirror the first-mortgage ceilings (e.g., conventional CLTV cap 97%; FHA 96.5%; HomeReady 105% with Community Seconds), but Phase 4 v1 doesn't model Community Seconds. **Recommendation:** Phase 4 enforces CLTV against the same per-loan-type ceiling table as LTV. Junior-lien shape is `list[Money]` (sum) per CONTEXT.md Claude's discretion. CLTV blocker uses the same `LTV-CEILING-{LOAN_TYPE}` citation prefix (or planner-finalized `CLTV-CEILING-{LOAN_TYPE}`).

## FHA UFMIP Financing Convention

CONTEXT.md D-03 leaves UFMIP-financing-convention as Claude's discretion at planning time, with two options:
- (a) caller pre-finances UFMIP into `loan_amount` (CLI documents convention)
- (b) `lib/affordability` auto-finances UFMIP when `loan_type == "fha"` and emits the financed amount in the output

### Industry default

[CITED: HUD 4000.1 Chapter II.A.5.c (UFMIP)] — UFMIP is "binary": pay the full premium in cash OR finance it. HUD policy does NOT allow partial financing. Industry default is **financed into the loan**: "The upfront FHA mortgage insurance premium (UFMIP) is usually added to your loan balance, so you don't have to pay it out of pocket at closing" [CITED: rocketmortgage.com/learn/ufmip; amerisave.com 2026 UFMIP guide]. Per HUD 4000.1, when financed, the UFMIP becomes part of the principal balance and amortizes over the life of the loan.

### Recommendation for D-03

**Adopt option (b): `lib/affordability.py` auto-finances UFMIP when `target_loan_type == "fha"`.** This matches industry default, removes a foot-gun from the caller (forgetting to add UFMIP to `loan_amount` produces an under-stated PITI by ~1.75% of principal divided by 360 months ≈ $20-50/mo for typical FHA loans — small but non-zero), and aligns with the project's "fail loud, no inference" discipline by making the UFMIP-financing convention an explicit lib-side calculation rather than a caller-side ritual.

Implementation pseudocode:
```python
if target_loan_type == "fha":
    base_principal = request.loan_amount
    mip_result = fha_mip.compute(loan=Loan(principal=base_principal, ...),
                                 original_property_value=request.property_value,
                                 endorsement_date=date.today())
    financed_principal = base_principal + mip_result.ufmip
    response.financed_loan_amount = financed_principal  # surfaced in output
    # Forward amortization uses financed_principal, not base_principal
    schedule = build_schedule(Loan(principal=financed_principal, ...))
    monthly_pi = schedule.monthly_pi
    monthly_mip = quantize_cents((financed_principal * mip_result.annual_mip_pct) / Decimal("12"))
```

The CONTEXT.md "either is correct" statement still holds; the recommendation above is the simpler-to-document and lower-foot-gun choice.

**Same pattern for VA funding fee:** mirror this convention for `target_loan_type == "va"` — auto-finance the VA funding fee into the principal at the script boundary. Document in `--help` and module docstring.

## Blocker Precedence — Domain Validation

CONTEXT.md D-11 locks: loan-type-classify → LTV/CLTV → DTI → ATR/QM → VA-residual.

### Domain-expert validation

This is the correct order from a regulatory-blocker-impact perspective:

1. **Loan-type classification** logically gates everything (you can't evaluate FHA-MIP if the loan is jumbo).
2. **LTV/CLTV** is a hard regulatory ceiling per loan type (FHA 96.5%, conventional 97%, etc.) — independent of borrower's repayment capacity.
3. **DTI** comes next: `max_dti` is the borrower's repayment-capacity cap (caller-supplied per D-12).
4. **ATR/QM** is a Reg-Z compliance layer that gates loan eligibility for QM safe-harbor or rebuttable-presumption status. Ordered after DTI because ATR/QM's input is APR, which depends on the loan's pricing post-DTI. (In practice, lenders evaluate ATR/QM in parallel with DTI; ordering matters only for the `blocked_by` first-hit short-circuit.)
5. **VA residual** is loan-type-specific and only applies when `target_loan_type == "va"`.

### Commonly-cited blockers NOT in CONTEXT.md (and recommendation)

- **Property-type ineligibility:** condos, manufactured homes, and rural-non-USDA properties have separate eligibility rules. **Recommendation:** out of scope for v1 (matches CONTEXT.md's "single-family residential" implicit assumption). Document in PROJECT.md "Out of Scope".
- **Flood-insurance / HMDA flags:** require flood-zone determinations; not modeled in v1. **Recommendation:** out of scope.
- **Mortgage insurance availability:** PMI is not always available for high-LTV loans (e.g., LTV > 95% requires specific PMI carrier approval). v1 assumes PMI is available whenever LTV > 80% and `target_loan_type == "conventional"`.
- **USDA income eligibility:** the `usda.evaluate(...)` predicate computes `income_eligible: bool`. CONTEXT.md D-11 doesn't include it in the blocker list. **Recommendation:** add as a hard blocker BEFORE the LTV/CLTV step when `target_loan_type == "usda"` (citation: `"USDA-INCOME-LIMIT-{COUNTY_FIPS}"` or planner-finalized format). Open question for planner — see §"Open Questions".
- **Freddie Mac eligibility:** `freddie_eligibility.evaluate(...).eligible == False` could be a blocker for conventional. CONTEXT.md leaves it out. **Recommendation:** soft warning, not blocker (matches the Fannie LLPA precedent in CONTEXT.md D-11).

### Confirmation

CONTEXT.md D-11 precedence is correct as locked. Add USDA income eligibility as a sixth step (USDA-only) at planner discretion. Other potential blockers are correctly deferred.

## Lower-of-Credit-Scores Convention

CONTEXT.md D-05 says: "picks lower across applicants" (single int per applicant; min selected for Fannie LLPA + Freddie eligibility).

### Fannie Mae confirmation

[CITED: Fannie Mae Selling Guide B3-5.1-02 "Determining the Credit Score for a Mortgage Loan" — current revision dated 2026-04-22]:

> "When multiple borrowers exist on a loan application ... select the lowest applicable score from the group as the representative credit score for the loan."

The borrower-level rule is:
- 2 scores → lower of the 2
- 3 scores → middle of the 3

Then the LOAN-level rule is: "select the lowest applicable score from all borrowers as the representative credit score for the mortgage."

**CONTEXT.md D-05 is correct.** Phase 4's `min(applicant.credit_score for applicant in applicants)` reduction matches Fannie's loan-level rule, GIVEN the caller-supplied per-applicant score is already the borrower-level representative score (mid-of-3 if 3 scores are pulled, lower-of-2 if 2 scores). CONTEXT.md D-05 documents this responsibility explicitly: "Caller is responsible for providing their middle-of-three (or whatever score they consider representative)".

### Freddie Mac confirmation

[CITED: Freddie Mac Single-Family Seller/Servicer Guide §5202 "Indicator Score"; sf.freddiemac.com/general/credit-score-models]: Freddie's "Indicator Score" follows the same convention — borrower-level uses middle-of-three (or lower-of-two), loan-level uses the lowest indicator score across borrowers. Matches Fannie's rule 1:1; sources cite "lowest applicable indicator score" for multi-borrower transactions. **Both GSEs follow the same lower-of-mid-scores rule.**

### Important nuance (out of v1 scope)

Fannie's guide also notes: "the representative credit score is always used for loan delivery and pricing purposes, while most loans with more than one borrower use the average median credit score to determine eligibility." For DU eligibility (Desktop Underwriter), the AVERAGE MEDIAN credit score is used. CONTEXT.md D-05 says we use `min` for both LLPA-pricing AND eligibility; this is a slight conservative deviation from Fannie DU eligibility (which would use average median). **This is acceptable for v1 personal-use** — using `min` for everything is more conservative (gates more borrowers as ineligible), which matches "fail loud, no inference". Document the deviation in module docstring.

## Reference YAML Schema Confirmation

### `data/reference/fha-mip-rates.yml`

[VERIFIED: 50-line read]

```yaml
source: "https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf"
effective: 2023-03-20
ufmip_rate: "0.0175"   # 1.75% — Decimal-string per Pitfall 1
annual_mip_table:      # list of brackets keyed by (term, ltv, loan_amount_max)
  - {term_months_min: "181", term_months_max: "360", ltv_min: "0.95", ltv_max: "1.00",
     loan_amount_max: "726200", annual_mip_rate: "0.0055"}
  # ... 12 more rows covering term × LTV × loan-amount tiers
termination:
  ltv_above_90_pct: "life_of_loan"
  ltv_at_or_below_90_pct: "132"   # 11 years × 12 months
grandfathering:
  pre_2023_endorsement_handling: "raise_NotImplementedError"
  earliest_supported_endorsement_date: 2023-03-20
```

- All numeric scalars are quoted strings (Pitfall 1; predicate coerces via `Decimal(...)` / `int(...)`).
- 12-month staleness threshold WILL fire `StaleReferenceWarning` (effective 2023-03-20 is > 12 months old — by design per `notes:`).
- Phase 4's `fha_mip.compute(...)` consumes the predicate output, not this YAML directly.

### `data/reference/va-residual-income.yml`

[VERIFIED: full read]

```yaml
source: "https://benefits.va.gov/WARMS/docs/admin26/m26-07/"
effective: 2023-04-07
regions: [northeast, midwest, south, west]
loan_band_threshold: "80000"           # split between table_above_80k / table_below_80k
per_extra_member_increment: "80"        # per family member above 5
table_above_80k:
  northeast: {"1": "450", "2": "755", "3": "909", "4": "1025", "5": "1062"}
  midwest:   {"1": "441", "2": "738", "3": "889", "4": "1003", "5": "1039"}
  south:     {"1": "441", "2": "738", "3": "889", "4": "1003", "5": "1039"}
  west:      {"1": "491", "2": "823", "3": "990", "4": "1117", "5": "1158"}
table_below_80k: {...}
```

- Family sizes 1-5 covered explicitly; sizes >5 add `per_extra_member_increment` per additional member (predicate-side; verified at `va_residual_income.py:96-99`).
- Phase 4's `va_residual_income.evaluate(...)` consumes the predicate output, not this YAML directly. Phase 4 needs `region`, `family_size`, `loan_amount`, `actual_residual_income` in the request — all present in CONTEXT.md D-15's optional `va:` block.

### `data/reference/conforming-limits-2026.yml`

[VERIFIED: 80-line read]

```yaml
source: "https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026"
effective: 2026-01-01
limits:
  baseline:
    one_unit: "832750"        # 2026 baseline
    two_unit: "1066250"
    three_unit: "1289100"
    four_unit: "1601650"
  ceiling:
    one_unit: "1249125"        # 150% × baseline (high-cost)
    ...
  high_cost_counties:          # subset of ~232 high-cost counties (top metros)
    - {state_fips: "06", county_fips: "001", county_name: "Alameda CA", one_unit: "1249125"}
    - {state_fips: "06", county_fips: "037", county_name: "Los Angeles CA", one_unit: "1249125"}
    # ... ~54 entries covering CA/NY/DC/FL/WA/MA/VA/NJ/CT/HI/AK metros + WA counties
```

- Each high-cost county requires `(state_fips, county_fips)` for lookup. Phase 4's `Household.location` MUST surface these as discrete fields, not just a county `name` string.
- WA counties (Pachulski household location) — King WA is NOT in the high-cost list at full ceiling; King WA falls under baseline ($832,750) per the FHFA 2026 publication. **Planner action:** verify the YAML's WA coverage when constructing the planner's hand-calc fixtures. The "King" county example in the existing `household.example.yml` is well-formed (WA state + King county); Phase 4's `loan_type.classify(loan_amount=$400k, county=King_WA)` returns `"conforming"` as expected.

## ATR/QM Gating Subtleties

### CFPB published thresholds (verified)

[CITED: federalregister.gov/documents/2020/12/29/2020-27567 — General QM final rule]:

| Loan-amount tier (first-lien) | General QM threshold | Safe Harbor threshold |
|-------------------------------|----------------------|------------------------|
| ≥ $110,260 (2026 indexed) | 2.25 pp | 1.50 pp |
| ≥ $66,156 and < $110,260 | 3.50 pp | 2.50 pp |
| < $66,156 | 6.50 pp | 6.50 pp (same) |
| First-lien manufactured home | 6.50 pp | n/a |
| Subordinate-lien | 3.50 pp | 3.50 pp |

CFPB indexes the loan-amount tiers annually; the Q4 2025 publication (Reg-Z annual threshold adjustments) sets the 2026 values: $110,260 / $66,156 (verified — `data/reference/atr-qm-thresholds.yml` ships these values).

### Boundary semantics

The predicate uses `<=` per 12 CFR §1026.43(e)(2) — a spread EXACTLY at threshold counts as PASSING. A loan with `apr - apor == 2.25 pp` and `loan_amount >= 110260` PASSES general QM.

### First-lien vs subordinate-lien

- **First-lien** is the primary mortgage on the property.
- **Subordinate-lien** is a second mortgage / HELOC.
- Phase 4 v1 handles ONLY first-lien residential purchase. Subordinate liens factor into CLTV (sum of `junior_liens`); they do NOT trigger their own ATR/QM evaluation in Phase 4. The CONTEXT.md `apr` + `apor` fields refer to the FIRST-LIEN loan being evaluated.

### Residential vs non-residential

ATR/QM applies only to "covered transactions" — closed-end consumer credit secured by a dwelling [CITED: 12 CFR §1026.43(b)(1)]. Phase 4 v1 assumes ALL evaluations are residential covered transactions (matches PROJECT.md scope: "personal household mortgage analysis").

### Missing apr/apor — advisory vs blocker

CONTEXT.md D-11 says: "if both apr+apor missing, advisory not blocker". **This is reasonable** because:

- The borrower's APR isn't always known at the affordability-screening stage (lender hasn't priced the loan yet).
- ATR/QM compliance is the LENDER's responsibility, not the borrower's. The Phase 4 affordability tool is borrower-side; flagging a borrower's affordability calc as "blocked" because they don't yet know the APR would be over-conservative.
- Treating it as a blocker would force callers to fabricate APR/APOR values just to get past the gate, defeating the "fail loud, no inference" principle.

**Confirmation:** keep as advisory warning when both `apr` and `apor` are missing. **However:** if ONLY ONE is supplied (e.g., `apr` is supplied but `apor` is null), this is suspicious — the caller is mid-fabrication. **Recommendation:** require BOTH or NEITHER; reject the half-supplied case at the request boundary as a Pydantic validation error.

### Phase 4 ATR/QM call shape

```python
if request.apr is not None and request.apor is not None:
    # First-lien per Phase 4 v1 scope
    qm_pass = atr_qm.general_qm_passes(
        apr=request.apr,
        apor=request.apor,
        loan_amount=loan_amount,            # post-UFMIP-financing if FHA per D-03 recommendation
        lien_position="first",
    )
    if not qm_pass:
        # Citation: planner-finalized format
        return AffordabilityResponse(blocked=True, blocked_by="ATR-QM-PRICE-FIRST", ...)
else:
    response.warnings.append("ATR-QM-NOT-EVALUATED-MISSING-APR-OR-APOR")
```

## Validation Architecture

> Nyquist validation enabled. This section is REQUIRED.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (existing — see Phase 1 + 2 + 3) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_affordability.py -x` |
| Full suite command | `uv run pytest && uv run mypy --strict . && uv run ruff check .` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AFFD-01 | DTI front-end + back-end exact Decimal | unit | `pytest tests/test_affordability.py::test_dti_calculations -x` | ❌ Wave 0 (file new) |
| AFFD-02 | LTV ratio | unit | `pytest tests/test_affordability.py::test_ltv_calculation -x` | ❌ Wave 0 |
| AFFD-03 | CLTV with junior liens | unit | `pytest tests/test_affordability.py::test_cltv_with_junior_liens -x` | ❌ Wave 0 |
| AFFD-04 | PITI = P&I + tax + ins + HOA + MI | unit | `pytest tests/test_affordability.py::test_piti_composition -x` | ❌ Wave 0 |
| AFFD-05 | Reverse-affordability via npf.pv + round-trip | unit + invariant | `pytest tests/test_affordability.py::test_reverse_round_trip -x` | ❌ Wave 0 |
| AFFD-06 | Joint-applicant: sum income + min credit score | unit | `pytest tests/test_affordability.py::test_joint_applicants -x` | ❌ Wave 0 |
| AFFD-07 | blocked_by citation when blocking | unit | `pytest tests/test_affordability.py::test_blocked_by_va_residual_west_family_4 -x` | ❌ Wave 0 |
| AFFD-08 | scripts/affordability.py CLI subprocess | integration (subprocess) | `pytest tests/test_affordability.py::test_cli_smoke -x` | ❌ Wave 0 |
| AFFD-09 | household.example.yml e2e | integration | `pytest tests/test_affordability.py::test_household_example_yml_e2e -x` | ❌ Wave 0 |

### Test Dimensions Phase 4 MUST cover

CONTEXT.md D-17 enumerates the named fixture list; the Validation Architecture extends with the dimensions the planner mirrors into PLAN tasks.

#### Boundary fixtures (LTV / DTI / VA region × family-size / FHA MIP)

- **LTV ceilings (per loan_type):** one fixture each at-ceiling (passes), one at ceiling-plus-Decimal("0.0001") (blocks):
  - Conventional at 0.95 → passes; at 0.9501 → `blocked_by="LTV-CEILING-CONVENTIONAL"` (or planner-finalized).
  - Conventional 97% LTV → passes if FTHB-flag-supplied; if FTHB out of scope, the at-ceiling case is 0.97 fixed.
  - FHA at 0.965 → passes; at 0.9651 → `blocked_by="LTV-CEILING-FHA"`.
  - VA at 1.00 → passes; at 1.0001 → `blocked_by="LTV-CEILING-VA"`.
  - USDA at 1.00 → passes; at 1.0001 → `blocked_by="LTV-CEILING-USDA"`.
- **DTI cap:** at-cap (passes), at-cap-plus-Decimal("0.0001") (blocks). One fixture per loan_type since CONTEXT.md ships per-loan-type DTI in `blocked_by` citation (`DTI-CAP-{LOAN_TYPE}`).
- **VA region × family_size:** at-minimum (passes), at-minimum-minus-$0.01 (fails). Fixture for `(WEST, 4)` (matches ROADMAP SC-3 example verbatim) is mandatory; one additional region+family-size pair recommended for matrix coverage.
- **FHA MIP table:** one fixture per row in `data/reference/fha-mip-rates.yml` (12 rows). The MIP is a derived value; the fixture asserts the predicate-emitted `annual_mip_pct` and Phase 4-derived `monthly_mip` match the YAML row. **Recommendation:** generate fixture programmatically by iterating `annual_mip_table` rows; pin one canonical per row.

#### Round-trip fixture (SC-2)

- One fixture: `reverse_conventional_80_ltv_43_dti.json`.
- Reverse mode produces `max_loan_amount`.
- Forward mode with same inputs (income, debts, max_dti=0.43) feeds back into forward affordability with `loan_amount=max_loan_amount`, `property_value=(max_loan_amount + down_payment)`.
- Asserts: `forward.dti_back ≤ max_dti + Decimal("0.0001")` (D-09 tolerance) AND `forward.loan_amount == reverse.max_loan_amount` exactly (Decimal equality on dollars).

#### Citation-coverage meta-test (RUL-12/13 inheritance)

Every `blocked_by` citation string format Phase 4 emits in production code MUST be exercised by at least one fixture. Inherits Phase 2's `tests/test_rules/test_citation_coverage.py` filesystem-introspecting pattern.

- New file: `tests/test_affordability.py::test_blocked_by_citation_coverage` (or `tests/test_rules/test_affordability_citation_coverage.py`).
- Discovers all `blocked_by` string format constants exported from `lib/affordability.py` (e.g., `BLOCKED_BY_LTV_CEILING_CONVENTIONAL`, `BLOCKED_BY_DTI_CAP_FHA`, etc.).
- Asserts each constant is the `blocked_by` value of at least one fixture in `tests/fixtures/affordability/`.
- The VA-residual citation format is dynamically constructed (not a constant), so the meta-test asserts at least one fixture has `blocked_by` matching `r"^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$"`.

#### Joint-applicant (D-07)

- 1-applicant fixture (`single_applicant.json`): `applicants=[{...}]` length 1; `min(...)` reduces to `applicant.credit_score`; income aggregation is `applicant.gross_monthly_income`.
- 2-applicant fixture (`joint_applicants_two_incomes.json`): `applicants=[A, B]` with different credit scores and incomes; lower credit score is selected; incomes sum.
- Both fixtures route through the same code path (CONTEXT.md D-07: "no special-cased single-applicant code path").

#### End-to-end (SC-4)

- Fixture: `household_example_yml_e2e.json`.
- Loads `config/household.example.yml` directly (not a JSON fixture; YAML).
- Subprocess invocation: `python scripts/affordability.py --input <generated-json-file>`.
- Asserts response shape (Pydantic schema match) + key fields present + no Pydantic envelope on stderr.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_affordability.py -x` (~5-10 sec — under 30s)
- **Per wave merge:** `uv run pytest && uv run mypy --strict . && uv run ruff check .` (~30-60 sec)
- **Phase gate:** Full suite green before `/gsd-verify-work` (Phase 4 totality re-verifies SC-1..SC-5).

### Wave 0 Gaps

- [ ] `tests/test_affordability.py` — covers AFFD-01..09; new file
- [ ] `tests/fixtures/affordability/` — directory; new
- [ ] `tests/fixtures/affordability/forward_conventional_80_ltv.json` — new
- [ ] `tests/fixtures/affordability/forward_conventional_85_ltv_with_pmi.json` — new
- [ ] `tests/fixtures/affordability/forward_fha_above_dti_cap.json` — new
- [ ] `tests/fixtures/affordability/forward_va_residual_fail.json` — new (matches SC-3)
- [ ] `tests/fixtures/affordability/forward_jumbo_above_county_limit.json` — new
- [ ] `tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json` — new (round-trip; SC-2)
- [ ] `tests/fixtures/affordability/joint_applicants_two_incomes.json` — new
- [ ] `tests/fixtures/affordability/single_applicant.json` — new
- [ ] `tests/fixtures/affordability/household_example_yml_e2e.json` — new (SC-4)
- [ ] `tests/conftest.py` — extend with `affordability_fixture` loader (mirrors `amortize_fixture` pattern)
- [ ] Plus one fixture per LTV-ceiling boundary (5 loan-types × 2 (at / over) = ~10) — planner finalizes count
- [ ] Plus FHA-MIP-row coverage (12 rows) — planner finalizes (recommend programmatic parametrize)

(Framework install: not needed; pytest already in `pyproject.toml` since Phase 1.)

## Security Domain

`security_enforcement` is enabled by absence of explicit `false` in config — applies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | CLI-only personal tool, no auth surface |
| V3 Session Management | no | Stateless CLI |
| V4 Access Control | yes | DATA_CONTRACT.md User Layer enforcement; pre-commit hook blocks `config/household.yml` writes |
| V5 Input Validation | yes | Pydantic v2 strict + frozen + extra=forbid on all request/response models; 6-key envelope on validation errors per Phase 3 D-19/WR-02 |
| V6 Cryptography | no | No crypto operations in Phase 4 |
| V10 Code Integrity | yes | `yaml.safe_load` ONLY (Phase 2 _loader.py asserts this); no `eval()`/exec on user input |
| V11 Business Logic | yes | Math correctness IS business logic; AMRT-07 invariant + D-15 `total_interest` invariant + D-09 round-trip pin the contract |
| V14 Configuration | yes | `_NAME_RX` regex on `load_reference()` defends against path-traversal payloads (Phase 2 WR-06) |

### Known Threat Patterns for Phase 4 stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Float-money silent coercion (Pydantic JSON path) | Tampering | Float-gate pre-validation walker per Phase 3 D-19 (`_find_json_float_loc`); 6-key envelope on rejection |
| Stale reference data (silently using >12-month-old YAML) | Repudiation | `StaleReferenceWarning` per Phase 2 D-12; warnings list in response surfaces it loudly |
| Missing-county silent fallback to baseline (Pitfall 7) | Tampering | `MissingCountyDataError` (loud) per RUL-01; Phase 4 surfaces as Pydantic envelope on stderr (not as `blocked_by`) |
| Negative or zero `loan_amount`/`property_value`/`income` | Tampering | Pydantic `Field(strict=True, ge=Decimal("0"))` on Money type; loud rejection at boundary |
| `extra=forbid` violations (typo'd field name silently accepted) | Tampering | Phase 1 ConfigDict pattern: `extra="forbid"` on every domain model |
| User-Layer write (a system process writes `config/household.yml`) | Tampering | Pre-commit hook + `.gitignore` per FND-04; documented in DATA_CONTRACT.md |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 43% DTI hard cap (legacy QM) | Price-based ATR/QM test (APR-APOR spread) | 2020-12 final rule, mandatory 2022-10-01 | Phase 4 uses caller-supplied `max_dti` (D-12); ATR/QM is its own predicate |
| Hand-rolled amortization formula | numpy-financial PMT/IPMT/PPMT wrap | Project Decision #1 (PROJECT.md) | Phase 3 wraps; Phase 4 reuses `Schedule.monthly_pi` |
| Float for money | Decimal-from-strings + ROUND_HALF_UP | Project Decision #2 (CLAUDE.md) | All Phase 4 math stays in Decimal |
| Baker's rounding (ROUND_HALF_EVEN, Python default) | ROUND_HALF_UP (US consumer mortgage convention) | Phase 1 (`lib/money.py`) | `quantize_cents` is the project-wide single source of truth |
| Three-bureau credit-score dict | Single int per applicant | CONTEXT.md D-05 | Caller supplies their middle-of-three; Phase 4 takes `min` across applicants |

**Deprecated/outdated:**
- 43% DTI ATR/QM hard cap — replaced 2022-10-01 by price-based test.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 4 conventional LTV ceiling = 97% UNCONDITIONALLY (FTHB designation out of v1 scope) | LTV / CLTV Ceiling Authority | Some borrowers w/o FTHB designation might be marked eligible at 97% LTV when in reality they're capped at 95%. v1 personal-use; user inspects report. Low risk. |
| A2 | FHA UFMIP financing convention: `lib/affordability` auto-finances when `target_loan_type == "fha"` (D-03 option (b)) | FHA UFMIP Financing Convention | Pure planner-time decision; either option is defensible. Medium risk. |
| A3 | VA funding fee mirrors UFMIP convention (auto-financed into principal) | FHA UFMIP Financing Convention | Same as A2. |
| A4 | USDA `income_eligible == False` is added as a hard blocker step at planner discretion | Blocker Precedence — Domain Validation | Phase 4 v1 might silently approve income-ineligible USDA loans. Medium risk; recommend escalating to D-11 with planner. |
| A5 | Phase 4 PMI rate sourcing for conventional > 80% LTV: caller-supplied `monthly_pmi` (no `pmi-rates.yml` predicate exists) | Phase 2 Predicate Signature Audit (conventional_pmi) | Critical: PMI is currently UN-DERIVED for conventional loans. Without resolution, forward-mode PITI for conventional > 80% LTV is missing the PMI line item. **MUST be resolved at PLAN time.** |
| A6 | Phase 4's request shape requires explicit `(state_fips, county_fips)` codes in `household.location`, not just county name | Phase 2 Predicate Signature Audit (types) | Without explicit FIPS, can't construct `County(state_fips=..., county_fips=...)` for `loan_type.classify`. CONTEXT.md is silent; planner must extend D-15 schema. |
| A7 | ATR/QM `apr`-only or `apor`-only (one supplied, other null) is rejected at request boundary | ATR/QM Gating Subtleties | Slightly stricter than CONTEXT.md D-11 ("if both apr+apor missing, advisory not blocker"). Defensible but optional. |

## Open Questions for Planner

1. **PMI rate sourcing for conventional > 80% LTV**
   - What we know: `lib/rules/conventional_pmi.py` returns termination status only, not a rate. There is no `pmi-rates.yml` reference YAML.
   - What's unclear: does Phase 4 ship a hardcoded default PMI rate (e.g., 75 bps annualized) for the affordability surface, OR does the caller supply `monthly_pmi` directly when conventional + LTV > 80%?
   - Recommendation: caller-supplied `monthly_pmi: Decimal | None` request field; required when `target_loan_type == "conventional"` AND `target_ltv_pct > 0.80`; document in `--help` and module docstring. Add to D-01 / D-02 amendments at PLAN time.

2. **`Household.location` schema must include FIPS codes**
   - What we know: `lib/rules/types.py:42-44` requires `County(state_fips: str, county_fips: str, name: str)`. CONTEXT.md `household.example.yml` shows only `county: "King"` (name).
   - What's unclear: should D-15 schema add `state_fips` and `county_fips` keys?
   - Recommendation: yes; matches "fail loud, no inference". Update `household.example.yml` with explicit FIPS codes. Document the mapping (e.g., King WA → state_fips=53, county_fips=033) in YAML comments.

3. **Loan-type-vs-target-loan-type cross-walk**
   - What we know: Phase 2's `loan_type.classify(...)` returns one of 8 LoanType values; CONTEXT.md D-10 has 5 `target_loan_type` values.
   - What's unclear: which classified values count as "matching" each requested `target_loan_type`? E.g., does `target_loan_type=="conventional"` accept both `"conforming"` and `"high_balance"` (yes, recommended) but block `"jumbo"`?
   - Recommendation: planner pins the cross-walk in `lib/affordability.py` module docstring as a literal table. Suggested cross-walk:
     - `conventional` → accepts `{"conforming", "high_balance"}`
     - `jumbo` → accepts `{"jumbo"}`
     - `fha` → accepts `{"fha_standard", "fha_high_balance"}`
     - `va` → accepts `{"va_standard", "va_high_balance"}`
     - `usda` → accepts `{"usda"}`

4. **USDA income-eligibility blocker placement in D-11 precedence**
   - What we know: `usda.evaluate(...)` returns `income_eligible: bool`; CONTEXT.md D-11 doesn't include USDA in the blocker list.
   - What's unclear: should USDA income-ineligible be a hard blocker, and where in the precedence?
   - Recommendation: hard blocker, as a sub-step of "loan-type classification" (step 1) — only fires when `target_loan_type == "usda"`. Citation: `"USDA-INCOME-LIMIT-{COUNTY_FIPS}"` (planner finalizes format).

5. **VA funding fee financing convention (parallel to D-03)**
   - What we know: `va_funding_fee.compute(...)` returns the fee dollar amount; CONTEXT.md `<canonical_refs>` says "financed into principal at script boundary".
   - What's unclear: who finances? `lib/affordability.py` (auto-financing) or the caller?
   - Recommendation: mirror the D-03 recommendation (auto-finance in `lib/affordability.py`); document in `--help`.

6. **Endorsement-date input for `fha_mip.compute(...)`**
   - What we know: predicate requires `endorsement_date: date`; raises `NotImplementedError` for dates before 2023-03-20.
   - What's unclear: where does Phase 4 source this? Caller-supplied? Defaults to `date.today()`?
   - Recommendation: default to `date.today()`; allow override via optional request field `fha_endorsement_date: date | None`. Document in module docstring that pre-2023-03-20 dates raise NotImplementedError per HUD ML 2023-05 grandfathering.

7. **VA region / family_size / actual_residual_income — required vs optional**
   - What we know: D-15 says "Optional `va:` block for VA loans"; predicate requires all three.
   - What's unclear: when `target_loan_type == "va"` AND `va:` block missing, do we fail-fast (Pydantic validation) or treat as advisory?
   - Recommendation: fail-fast — Pydantic `model_validator(mode="after")` on `AffordabilityRequest` enforces "if `target_loan_type == 'va'` then `va` block required". Matches "fail loud, no inference".

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.12+ (Phase 1 verified) | — |
| `numpy-financial` | `npf.pv` (reverse mode) | ✓ | 1.0.0 (per Phase 3 lib/amortize.py:133) | — |
| `pydantic` | All Pydantic v2 models | ✓ | ≥2.6 (Phase 1 PROJECT.md) | — |
| `python-dateutil` | `relativedelta` (already used in Phase 3) | ✓ | (Phase 1 dependency) | — |
| `pyyaml` | `lib/rules/_loader.py` (Phase 2) | ✓ | ≥6.0.2 (Phase 2 dependency) | — |
| `pytest` | testing | ✓ | (Phase 1 dependency) | — |
| `mypy --strict` | type checking | ✓ | (Phase 1 dependency) | — |
| `ruff` | linting | ✓ | (Phase 1 dependency) | — |

**No new external dependencies expected.** Phase 4 is pure composition over Phase 1/2/3 surface.

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Sources

### Primary (HIGH confidence — verified empirically by source-read)

- `lib/rules/loan_type.py:69-92` — signature + behavior of `classify(...)`
- `lib/rules/conventional_pmi.py:61-126` — `status(loan, scheduled_balance, original_property_value, ...)` signature; `LTV_AUTO_TERMINATE` and `LTV_REQUEST_ELIGIBLE` constants
- `lib/rules/fha_mip.py:66-120` — `compute(loan, original_property_value, endorsement_date)` signature; `MIPResult` shape
- `lib/rules/va_residual_income.py:102-122` — `evaluate(...)` signature; STABLE `binding_rule_citation` format at line 115
- `lib/rules/va_funding_fee.py:65-110` — `compute(...)` signature; flat-fee branches
- `lib/rules/usda.py:85-114` — `evaluate(...)` signature; `USDAEligibilityResult` shape; locked silent-fallback decision
- `lib/rules/atr_qm.py:63-106` — `general_qm_passes(...)` and `safe_harbor_qm_passes(...)` signatures; `<=` boundary semantic
- `lib/rules/fannie_eligibility.py:128-176` — `compute_llpa(...)` signature; ltv_pct percentage-points convention
- `lib/rules/freddie_eligibility.py:119-182` — `evaluate(...)` signature; FreddieEligibilityResult shape
- `lib/rules/types.py:1-71` — LoanType, Region, County, Borrower, Property
- `lib/rules/_loader.py:46-87` — `load_reference(...)` + `StaleReferenceWarning`
- `lib/amortize.py:255-292` — `build_schedule(...)` dispatch
- `lib/models.py:36-91` — Loan / Payment / Schedule / Money / Rate
- `lib/money.py:1-46` — `quantize_cents`, `CENT`, `MONEY_CONTEXT`
- `data/reference/fha-mip-rates.yml` — REF-03 schema
- `data/reference/va-residual-income.yml` — REF-05 schema
- `data/reference/conforming-limits-2026.yml` — REF-01 schema
- `scripts/amortize.py:36-60` — Envelope Shape Contract (WR-02 closure)

### Secondary (MEDIUM confidence — verified via official docs)

- [Fannie Mae Selling Guide B3-5.1-02 "Determining the Credit Score for a Mortgage Loan"](https://selling-guide.fanniemae.com/sel/b3-5.1-02/determining-credit-score-mortgage-loan) — current revision 2026-04-22
- [Fannie Mae 97% LTV Options](https://singlefamily.fanniemae.com/originating-underwriting/mortgage-products/97-loan-value-options)
- [Fannie Mae HomeReady eligibility](https://selling-guide.fanniemae.com/sel/b5-6-01/homeready-mortgage-loan-and-borrower-eligibility)
- [HUD Single Family Housing Policy Handbook 4000.1](https://www.hud.gov/sites/dfiles/OCHCO/documents/4000.1hsghhdbk103123.pdf)
- [VA Pamphlet 26-7 Chapter 3](https://www.benefits.va.gov/WARMS/docs/admin26/handbook/ChapterLendersHanbookChapter3.pdf)
- [USDA Single Family Housing Guaranteed Loan Program](https://www.rd.usda.gov/programs-services/single-family-housing-programs/single-family-housing-guaranteed-loan-program)
- [CFPB General QM Final Rule 2020-12](https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition)
- [numpy_financial.pv documentation](https://numpy.org/numpy-financial/latest/pv.html) — verified 2026-04-30
- [numpy-financial issue #130 (pmt fv-sign bug)](https://github.com/numpy/numpy-financial/issues/130) — affects pmt with fv != 0; pv with fv=0 unaffected
- [HPA Examination Procedures (CFPB)](https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/)
- [Freddie Mac Single-Family Seller/Servicer Guide §5202](https://guide.freddiemac.com/app/guide/section/5202) and [Credit Score Models Initiative](https://sf.freddiemac.com/general/credit-score-models)

### Tertiary (LOW confidence — community sources; cross-verified above where possible)

- Industry-standard UFMIP-financed-into-principal convention: confirmed via multiple secondary sources (Rocket Mortgage, Amerisave, fhahandbook.com), aligned with HUD 4000.1 binary-payment policy.
- DTI front-end / back-end definitions: confirmed via Bankrate, Rocket Mortgage, Citizens Bank — all consistent with Fannie Mae Selling Guide B3-6-02.

## Metadata

**Confidence breakdown:**
- Phase 2 predicate signatures: HIGH — verified by source-read
- Phase 3 surface confirmation: HIGH — verified by source-read
- numpy-financial conventions: HIGH — verified against official numpy-financial docs
- LTV ceilings: HIGH — verified against Fannie/HUD/VA/USDA official sources
- FHA UFMIP financing convention: HIGH — verified against HUD 4000.1 + multiple secondary sources
- Lower-of-credit-scores: HIGH — verified against Fannie B3-5.1-02 + Freddie §5202
- Blocker precedence: MEDIUM — domain reasoning supported by predicate-signature audit; planner judgment required for USDA-eligibility placement
- ATR/QM thresholds: HIGH — verified against CFPB published thresholds + on-disk YAML
- Reference YAML schemas: HIGH — verified by source-read

**Research date:** 2026-04-30
**Valid until:** 2026-07-30 (90 days for stable regulatory data; the 12-month staleness threshold applies to the YAMLs themselves)

## RESEARCH COMPLETE
