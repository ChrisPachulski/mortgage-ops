---
phase: 02-regulatory-reference-data-rules-predicates
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 41
files_reviewed_list:
  - lib/rules/__init__.py
  - lib/rules/_loader.py
  - lib/rules/atr_qm.py
  - lib/rules/conventional_pmi.py
  - lib/rules/fannie_eligibility.py
  - lib/rules/fha_mip.py
  - lib/rules/freddie_eligibility.py
  - lib/rules/irs_pub936.py
  - lib/rules/loan_type.py
  - lib/rules/reg_z.py
  - lib/rules/types.py
  - lib/rules/usda.py
  - lib/rules/va_funding_fee.py
  - lib/rules/va_residual_income.py
  - data/reference/atr-qm-thresholds.yml
  - data/reference/conforming-limits-2026.yml
  - data/reference/fannie-llpa-matrix.yml
  - data/reference/fha-limits-2026.yml
  - data/reference/fha-mip-rates.yml
  - data/reference/freddie-eligibility-matrix.yml
  - data/reference/irs-pub936.yml
  - data/reference/usda-income-limits.yml
  - data/reference/va-funding-fees.yml
  - data/reference/va-residual-income.yml
  - tests/test_reference/test_schema.py
  - tests/test_reference/test_yaml_count_audit.py
  - tests/test_rules/test_atr_qm.py
  - tests/test_rules/test_citation_coverage_mutations.py
  - tests/test_rules/test_citation_coverage.py
  - tests/test_rules/test_conventional_pmi.py
  - tests/test_rules/test_fannie_eligibility.py
  - tests/test_rules/test_fha_mip.py
  - tests/test_rules/test_freddie_eligibility.py
  - tests/test_rules/test_irs_pub936.py
  - tests/test_rules/test_loader.py
  - tests/test_rules/test_loan_type.py
  - tests/test_rules/test_phase2_smoke.py
  - tests/test_rules/test_reg_z.py
  - tests/test_rules/test_usda.py
  - tests/test_rules/test_va_funding_fee.py
  - tests/test_rules/test_va_residual_income.py
findings:
  blocker: 5
  warning: 9
  total: 14
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-04-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 41
**Status:** issues_found

## Summary

Phase 2 ships 11 predicates and 10 reference YAMLs covering conforming/FHA/VA/USDA limits, MIP, funding fees, residual income, IRS Pub 936, GSE matrices, ATR/QM, and Reg Z. Money discipline is broadly sound — Decimal-from-string consistently, `quantize_cents` at boundary, no float arithmetic detected in the predicate bodies. The citation-header / source-URL / effective-date discipline is enforced via the meta-tests, and the mutation tests genuinely exercise the failure paths.

That said, this review found multiple correctness defects that should not ship:

1. **FHA classification fall-through:** `_classify_fha` silently falls back to FHA floor for unlisted counties, contradicting both the YAML's documented intent ("unlisted high-cost counties → MissingCountyDataError") and the analogous behavior in `_classify_conventional`. A real high-cost county not in the shipped subset is misclassified as out-of-program.
2. **VA cash-out refi fee is regulatorily wrong:** `va_funding_fee.compute` routes `cash_out_refi` through the same down-payment-banded purchase table. VA M26-7 Chapter 8 fixes cash-out refi at 2.15%/3.30% (first/subsequent use) regardless of down payment. A caller supplying a 10% down payment with `loan_purpose="cash_out_refi"` gets 1.25% — silently the wrong fee.
3. **FHA MIP table coverage gap:** `_lookup_annual_mip` raises `LookupError` for legitimate combinations (e.g. high-balance term ≤ 15yr at LTV ≤ 0.78; high-balance term > 15yr at LTV exactly 0.78 and below). The YAML rows do not cover all valid (term, LTV, loan_amount) cells for high-balance loans.
4. **Conforming-limits high-cost county YAML missing unit_count keys:** `_county_limit` indexes by `unit_key` (`one_unit`/`two_unit`/...). The YAML high_cost_counties only carry `one_unit`. The current `unit_count != 1` guard in `classify` prevents this from triggering today, but the YAML schema is silently incomplete and any future extension to multi-unit will KeyError. (Conforming-limits has the bug; FHA-limits has the same gap.)
5. **YAML / code disagreement on FHA unlisted-county semantics:** the YAML notes block in `fha-limits-2026.yml` documents the intended "MissingCountyDataError on unlisted high-cost county" behavior; the code does the opposite. Either the YAML notes are wrong or the code is wrong; in either case the source of truth is unstable.

Plus several quality concerns — float-downcast risk on a few unquoted YAML numeric scalars, a couple of fragile boolean coercions, an LTV gap in the bucket schemas at fractional boundaries, and minor robustness issues in the loader.

## Blockers

### BL-01: FHA classification silently falls back to floor for unlisted counties (contradicts YAML intent)

**File:** `lib/rules/loan_type.py:178-186` (and call site `lib/rules/loan_type.py:130-137`)
**Issue:**
`_county_limit_fha` returns `floor` for any county not in `high_cost_counties`. Combined with `_classify_fha`'s logic, an unlisted county with `loan_amount > floor` will hit `loan_amount <= county_limit` → False and raise `NotImplementedError("loan_amount ... exceeds FHA county ceiling ...")`.

But `data/reference/fha-limits-2026.yml` lines 11-12 state: "Per Phase 2 decision D-PHASE2-Q2: subset of high-cost counties shipped (...); unlisted high-cost counties → MissingCountyDataError." The conforming-limits classifier (`_classify_conventional`) does adopt this loud-fail-on-unlisted behavior; the FHA classifier does not.

The user-visible consequence: a Bay Area borrower in a high-cost FHA county that just isn't in our ~30-county subset gets `NotImplementedError("exceeds FHA county ceiling")` — implying their loan is structurally too large for FHA — when the actual cause is a missing data row. They cannot tell the difference between "really exceeds the FHA ceiling" and "your county isn't in our table."

There is no test for "unlisted county + above floor" in `test_loan_type.py`, which is why this slipped through.

**Fix:**
```python
def _county_limit_fha(
    ref: dict[str, Any], county: County, unit_key: str, floor: Decimal
) -> Decimal:
    """Return county-specific FHA ceiling.

    Per data/reference/fha-limits-2026.yml: unlisted counties when loan exceeds
    floor → MissingCountyDataError (matches conforming-limits behavior).
    """
    for entry in ref["limits"]["high_cost_counties"]:
        if entry["state_fips"] == county.state_fips and entry["county_fips"] == county.county_fips:
            return Decimal(entry[unit_key])
    raise MissingCountyDataError(
        f"FHA county ({county.state_fips}/{county.county_fips} {county.name!r}) not "
        f"in shipped high-cost subset; cannot determine ceiling. Add the county "
        f"to data/reference/fha-limits-2026.yml or pass a smaller loan amount."
    )
```
And add a test in `test_loan_type.py`:
```python
def test_fha_unlisted_county_above_floor_raises_missing_county_data() -> None:
    # Hand: $700k > floor $541,287; county Autauga (not in shipped subset).
    # Per fha-limits-2026.yml notes: should raise MissingCountyDataError, NOT
    # NotImplementedError("exceeds FHA county ceiling").
    with pytest.raises(MissingCountyDataError, match="not in shipped high-cost subset"):
        classify(
            Decimal("700000.00"),
            county=County(state_fips="01", county_fips="001", name="Autauga"),
            program="fha",
        )
```

---

### BL-02: VA funding fee for cash-out refi uses purchase down-payment bands (regulatorily wrong)

**File:** `lib/rules/va_funding_fee.py:86-91`
**Issue:**
The `compute` function routes both `purchase` and `cash_out_refi` through `_lookup_purchase_or_cashout_pct`, which selects the fee tier based on `down_payment_pct`. Per VA Lender Handbook M26-7 Chapter 8 (the YAML's own cited source), VA cash-out refi has FIXED fees:
- First use: 2.15%
- Subsequent use: 3.30%

There is no down-payment-tier discount for cash-out refi — the very concept is incoherent because cash-out refis convert equity into cash; there is no "down payment" in the traditional sense.

Today, a caller doing `compute(loan_amount=400_000, down_payment_pct=Decimal("0.10"), is_first_use=True, loan_purpose="cash_out_refi", ...)` gets `1.25% × $400k = $5,000.00`. The correct VA fee is `2.15% × $400k = $8,600.00`. That is a $3,600 understatement of a federally-mandated fee — a money-correctness defect.

The existing test `test_cash_out_subsequent_use_330_pct` only covers `down_payment_pct=0.00`, where the purchase-band-0 row happens to coincide with the cash-out fee. The test never exercises a non-zero down payment with cash-out, so the bug is invisible to the test suite.

**Fix:** Add cash-out refi to the flat-fee branch and shrink the table to purchase-only:

```python
# In compute():
if loan_purpose == "irrrl":
    fee_pct = Decimal(ref["flat_fees"]["irrrl"])
elif loan_purpose == "manufactured_home_non_permanent":
    fee_pct = Decimal(ref["flat_fees"]["manufactured_home_non_permanent"])
elif loan_purpose == "loan_assumption":
    fee_pct = Decimal(ref["flat_fees"]["loan_assumption"])
elif loan_purpose == "cash_out_refi":
    # M26-7 Ch 8: cash-out fee is fixed by use-count, no down-payment tier.
    key = "cash_out_first_use" if is_first_use else "cash_out_subsequent_use"
    fee_pct = Decimal(ref["flat_fees"][key])
elif loan_purpose == "purchase":
    fee_pct = _lookup_purchase_pct(
        table=ref["purchase"],
        down_payment_pct=down_payment_pct,
        is_first_use=is_first_use,
    )
else:
    raise ValueError(f"loan_purpose={loan_purpose!r} not recognized")
```

And restructure `data/reference/va-funding-fees.yml`:
```yaml
flat_fees:
  irrrl: "0.0050"
  manufactured_home_non_permanent: "0.0100"
  loan_assumption: "0.0050"
  cash_out_first_use: "0.0215"
  cash_out_subsequent_use: "0.0330"
purchase:
  - {down_payment_min: "0.00", down_payment_max: "0.05", first_use_pct: "0.0215", subsequent_use_pct: "0.0330"}
  - {down_payment_min: "0.05", down_payment_max: "0.10", first_use_pct: "0.0150", subsequent_use_pct: "0.0150"}
  - {down_payment_min: "0.10", down_payment_max: "1.00", first_use_pct: "0.0125", subsequent_use_pct: "0.0125"}
```

Add a regression test:
```python
def test_cash_out_refi_ignores_down_payment_pct() -> None:
    # Hand: cash-out is flat 2.15%/3.30%; passing 10% down must NOT discount it.
    # 0.0125 (purchase 10%-down rate) != 0.0215 (correct cash-out first-use).
    fee = compute(
        loan_amount=Decimal("400000.00"),
        down_payment_pct=Decimal("0.10"),
        is_first_use=True,
        loan_purpose="cash_out_refi",
        is_exempt_from_funding_fee=False,
    )
    assert fee == Decimal("8600.00")  # NOT $5,000
```

---

### BL-03: FHA MIP table has uncovered (term, LTV) cells for high-balance loans

**File:** `data/reference/fha-mip-rates.yml:25-31` + `lib/rules/fha_mip.py:120-151`
**Issue:**
The `annual_mip_table` rows for the high-balance tier (`loan_amount_max: "999999999"`) only cover:
- term 181-360, LTV 0.78-1.00 (three rows: 0.95-1.00, 0.90-0.95, 0.78-0.90)
- term 1-180, LTV 0.78-1.00 (two rows: 0.90-1.00, 0.78-0.90)

Missing:
- term 181-360, LTV 0.00-0.78
- term 1-180, LTV 0.00-0.78

Furthermore, the lookup logic `if ltv_min == Decimal("0.00")` only treats `ltv_min` as inclusive when it equals exactly 0.00. The lowest high-balance row has `ltv_min: "0.78"`, so the condition `ltv_min < ltv` fires for ltv=0.78 → 0.78 < 0.78 is False → no row matches.

Net: a high-balance FHA loan (loan_amount > $726,200) with LTV ≤ 0.78 raises `LookupError("No annual_mip_table row matched ...")`. While very-low-LTV high-balance FHA loans are rare (FHA's value proposition is small down payments), they ARE permissible (a borrower may make a large additional down payment), and the predicate fails them rather than serving the published rate.

The standard tier has analogous coverage but uses a `0.00-0.78` row that hits the `ltv_min == 0.00` carve-out, so standard tier is OK.

**Fix:** Add the missing rows to the high-balance tier in `data/reference/fha-mip-rates.yml`:

```yaml
# High-balance tier, term > 15yr — full LTV span
- {term_months_min: 181, term_months_max: 360, ltv_min: "0.00", ltv_max: "0.78", loan_amount_max: "999999999", annual_mip_rate: "0.0070"}
# High-balance tier, term ≤ 15yr — full LTV span
- {term_months_min: 1, term_months_max: 180, ltv_min: "0.00", ltv_max: "0.78", loan_amount_max: "999999999", annual_mip_rate: "0.0040"}
```

Verify the actual HUD ML 2023-05 Table B values for the bottom LTV band (the values above are placeholders matched to the existing 0.78-0.90 row's rate, which is the conventional structure but should be confirmed against the HUD source PDF before shipping).

Add a regression test in `test_fha_mip.py` covering an unloaded-balance, low-LTV case:
```python
def test_fha_mip_high_balance_low_ltv_returns_a_rate_not_lookup_error() -> None:
    # Hand: $800k loan / $1.2M property = 0.667 LTV, term 360 → high-balance,
    # term>15, LTV<0.78. Must find a row, not raise LookupError.
    loan = Loan(
        principal=Decimal("800000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
        origination_date=date(2024, 6, 15),
        loan_type="fha",
    )
    result = compute(
        loan=loan,
        original_property_value=Decimal("1200000.00"),
        endorsement_date=date(2024, 6, 15),
    )
    # exact rate to be filled in from HUD ML 2023-05 Table B
    assert result.annual_mip_pct == Decimal("0.0070")
```

---

### BL-04: Conforming-limits high_cost_counties only carry `one_unit` (silent KeyError if multi-unit ever lands)

**File:** `data/reference/conforming-limits-2026.yml:27-91` and `data/reference/fha-limits-2026.yml:24-56`
**Issue:**
The conforming-limits and FHA-limits YAMLs declare baseline/floor and ceiling for `one_unit`, `two_unit`, `three_unit`, `four_unit`. But every entry under `high_cost_counties` only ships `one_unit`. The lookup `Decimal(entry[unit_key])` will `KeyError` when `unit_key != "one_unit"`.

The CURRENT runtime guard in `classify` (`if unit_count != 1: raise NotImplementedError`) prevents this from being reachable today. But:
1. The schema is silently incomplete — the YAML claims to carry per-unit data and does not.
2. Any future code change that drops or relaxes the `unit_count != 1` guard will break with `KeyError` (a confusing failure mode) instead of finding the data.
3. The `_county_limit` helper does not assert `unit_key == "one_unit"`, so the data-discipline contract isn't enforced.

This is borderline between BLOCKER and WARNING — it's not exploitable today, but it's a footgun: the data layer LOOKS like it supports 2-4 unit lookups and silently doesn't.

**Fix:** Either (a) fill in `two_unit`/`three_unit`/`four_unit` for every county entry (matching the per-unit ceiling-vs-baseline ratios from FHFA's published county XLSX) or (b) add an explicit assertion at the helper level so the contract is documented in code:

```python
def _county_limit(ref: dict[str, Any], county: County, unit_key: str, baseline: Decimal) -> Decimal:
    if unit_key != "one_unit":
        raise NotImplementedError(
            f"county-level multi-unit limits not yet shipped in reference YAML; "
            f"got unit_key={unit_key!r}"
        )
    for entry in ref["limits"]["high_cost_counties"]:
        ...
```

Option (a) is the regulatorily correct fix because FHFA publishes per-unit county limits; option (b) is the minimum safety net. Pick one consistently across `_county_limit` and `_county_limit_fha`.

---

### BL-05: YAML notes contradict code on FHA unlisted-county semantics (cross-artifact source-of-truth drift)

**File:** `data/reference/fha-limits-2026.yml:10-12` vs `lib/rules/loan_type.py:178-186`
**Issue:**
The YAML notes explicitly document the intended behavior:

> "Per Phase 2 decision D-PHASE2-Q2: subset of high-cost counties shipped (CA / NY / DC / MA / NJ / HI / AK metros); unlisted high-cost counties → MissingCountyDataError."

The code's docstring says the opposite:

> "Return county-specific FHA ceiling, falling back to floor for unlisted counties (matches HUD's convention: low-cost areas use the floor)."

Pick one as authoritative, fix the other. This is the same defect as BL-01 viewed from the documentation angle — but flagged separately because the YAML notes are themselves a regulatory-grade artifact (annual refresh discipline) and silent drift between them and the code creates a rot vector: a future maintainer reading the YAML "knows" that unlisted counties fail loudly, ships code based on that assumption, and the assumption silently breaks.

**Fix:** Resolve BL-01 (recommend: code → MissingCountyDataError, matching the YAML notes and the conventional path). Then either remove the contradicting docstring on `_county_limit_fha` or update it to match the new behavior.

---

## Warnings

### WR-01: VA residual income table treats `persons_5_to_8` as 8-person base for above-8 uplift

**File:** `lib/rules/usda.py:140-143`
**Issue:**
The 8%-per-extra-member uplift formula multiplies `persons_5_to_8` by `per_extra_pct`. Per USDA RD published policy, the uplift is calculated against the 8-person limit specifically, not a banded 5-8 range. In the YAML, `persons_5_to_8` is a single value covering the band — but conceptually USDA's per-person tables differentiate. This is a deliberate banded simplification per the YAML notes; just flagging that the predicate's accuracy degrades for very large households (>8) compared to USDA's true per-person table.

Acceptable for v1 personal-use scope; noting because it affects a minor population.

**Fix:** Document the simplification in the predicate docstring (already partly there) or fetch the actual per-person table. Defer if scope-bound.

---

### WR-02: `fha-mip-rates.yml` has unquoted integer scalars (term_months_min, term_months_max, 132)

**File:** `data/reference/fha-mip-rates.yml:18-31, 34`
**Issue:**
The YAML discipline (`CLAUDE.md` Reference data discipline + Pitfall 1) requires all numeric scalars to be quoted strings to prevent PyYAML float-downcasting. `term_months_min: 1`, `term_months_max: 360`, `loan_amount_max: "726200"` is mixed — the loan_amount is quoted but term_months are not. The `132` for `ltv_at_or_below_90_pct` is also unquoted.

PyYAML emits these as `int`, not `float`, so there's no precision-loss bug today. But it breaks the project's "all numerics quoted, Decimal-from-string at consumption" invariant — and a future maintainer who copies this row as a template may not notice the inconsistency.

**Fix:** Quote consistently:
```yaml
- {term_months_min: "181", term_months_max: "360", ltv_min: "0.95", ltv_max: "1.00", loan_amount_max: "726200", annual_mip_rate: "0.0055"}
...
termination:
  ltv_above_90_pct: "life_of_loan"
  ltv_at_or_below_90_pct: "132"
```

And update the lookup: `if not (int(row["term_months_min"]) <= term_months <= int(row["term_months_max"]))`. Also adjust `terminates = ref["termination"]["ltv_at_or_below_90_pct"]` to coerce to int.

---

### WR-03: LTV bucket schemas (Fannie + Freddie) leave a fractional gap at `60.005..60.009`

**File:** `data/reference/fannie-llpa-matrix.yml:33-40` + `data/reference/freddie-eligibility-matrix.yml:34-42`
**Issue:**
The LTV bucket boundaries are `0-60.00` then `60.01-70.00`. An LTV of `Decimal("60.005")` (or any value in the open interval `(60.00, 60.01)`) matches NO bucket → `LookupError`.

In practice LTV values are typically quantized to two decimals so the gap is unreachable. But the predicates accept arbitrary `Decimal` LTV from callers; if Phase-4 affordability ever passes in a 4-decimal LTV (e.g., `principal/value = 0.600056` × 100 = 60.0056), the predicates will fail-loud rather than picking a sensible bucket.

This is intentional fail-loud per project discipline, but the contract should be explicit at the API boundary.

**Fix:** Document the LTV-quantization expectation in each predicate's docstring:

```python
def compute_llpa(
    credit_score: int,
    ltv_pct: Decimal,           # MUST be quantized to two decimal places
    ...
```

Optionally add a guard at the top of `_ltv_bucket`:
```python
if ltv_pct.as_tuple().exponent < -2:
    raise ValueError(
        f"ltv_pct must be quantized to <= 2 decimal places (LLPA buckets are "
        f"two-decimal-precision); got exponent={ltv_pct.as_tuple().exponent}"
    )
```

---

### WR-04: `bool(cell["eligible"])` defensively coerces but masks YAML-shape regressions

**File:** `lib/rules/freddie_eligibility.py:122`
**Issue:**
`base_eligible = bool(cell["eligible"])` works correctly when `cell["eligible"]` is a YAML boolean (Python `True`/`False`). But `bool("false")` is `True` (non-empty string is truthy). If a future YAML edit accidentally quotes the eligibility flag (`"false"` instead of `false`), the predicate will silently flip every "ineligible" cell to "eligible" and never raise.

The schema test does not check the type of `eligible`, so the regression is invisible.

**Fix:** Either remove the `bool()` call (PyYAML guarantees the type when unquoted) or make it strict:

```python
raw_eligible = cell["eligible"]
if not isinstance(raw_eligible, bool):
    raise TypeError(
        f"freddie-eligibility-matrix.yml cell {cs_bucket}/{ltv_b} 'eligible' "
        f"must be YAML bool (true/false unquoted); got {type(raw_eligible).__name__} "
        f"with value {raw_eligible!r}"
    )
base_eligible = raw_eligible
```

And add a schema test that asserts every `eligible` cell in the YAML is a Python bool.

---

### WR-05: `_loader.load_reference` does not validate that `effective` is a `date`

**File:** `lib/rules/_loader.py:38-58, 61-72`
**Issue:**
`_check_staleness` does `if effective < threshold_date` directly. If a YAML accidentally quotes the date (`effective: "2026-01-01"` instead of `effective: 2026-01-01`), PyYAML returns a string, and the comparison `"2026-01-01" < date.today() - relativedelta(months=12)` raises `TypeError` rather than producing a clear message.

`tests/test_reference/test_schema.py` enforces `isinstance(raw["effective"], date)` for shipped YAMLs, so the bug is caught by tests. But the loader itself is the single source of truth and should produce a clear error.

**Fix:**
```python
if "effective" not in raw:
    raise MissingReferenceFieldError(...)
if not isinstance(raw["effective"], date):
    raise MissingReferenceFieldError(
        f"{name}.yml `effective:` must be an unquoted YAML date "
        f"(YYYY-MM-DD); got {type(raw['effective']).__name__} "
        f"with value {raw['effective']!r}. Quoted strings are not accepted."
    )
```

---

### WR-06: `_loader` does not validate the `name` argument (theoretical path traversal)

**File:** `lib/rules/_loader.py:38-58`
**Issue:**
`load_reference(name)` builds `REFERENCE_DIR / f"{name}.yml"` from caller-supplied `name`. If a caller (or test fixture) ever passes `name = "../../etc/passwd"`, the resolved path escapes the reference dir.

In a personal-use mortgage tool this is not exploitable — every caller is internal predicates with hardcoded literal names. But the loader is the documented "single source of truth" and a defensive check costs almost nothing.

**Fix:**
```python
import re
_NAME_RX: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9-]*$")

def load_reference(name: str) -> dict[str, Any]:
    if not _NAME_RX.match(name):
        raise ValueError(
            f"reference name must match {_NAME_RX.pattern}; got {name!r}"
        )
    ...
```

---

### WR-07: `lru_cache` in `_loader` retains tmp-path entries across `test_loader.py` tests

**File:** `lib/rules/_loader.py:37` + `tests/test_rules/test_loader.py:35-38, 46-50, 57, 67, 76`
**Issue:**
`load_reference` is cached with `lru_cache(maxsize=None)`. Each `test_loader.py` test calls `load_reference.cache_clear()` BEFORE loading from a tmp_path, but does not clear after. This means the cache may still hold synthetic-test entries (e.g. `synthetic-old`) after the test completes. As long as no other test calls `load_reference("synthetic-old")` against the real `REFERENCE_DIR`, the contamination is harmless. But the discipline of "clear before AND after" is more robust against future test additions.

**Fix:** Use a `pytest` fixture with explicit setup/teardown:
```python
@pytest.fixture(autouse=True)
def _clear_loader_cache() -> Iterator[None]:
    load_reference.cache_clear()
    yield
    load_reference.cache_clear()
```

---

### WR-08: HPA midpoint uses `term_months // 2` — semantics for odd terms not pinned

**File:** `lib/rules/conventional_pmi.py:105`
**Issue:**
`midpoint = loan.term_months // 2`. For `term_months = 360`, midpoint = 180 (correct). For unusual odd-month terms (e.g., 359 due to short-month carryover), midpoint = 179, which means the borrower hits the `§4902(g)` carve-out one month earlier than the strict "half of 359 = 179.5" reading would suggest.

HPA `§4902(g)` says "midpoint of the amortization period" — the regulation does not specify rounding for non-integer halves. Common industry practice is to floor (which matches `//`), but this is uncited in the docstring. A test pinning the convention for an odd term would harden the contract.

**Fix:** Add docstring text:
```python
# §4902(g) midpoint: floor(term_months / 2) per industry convention; HPA is
# silent on rounding for odd-month terms. For canonical 360-month terms this
# is exactly 180 months.
midpoint = loan.term_months // 2
```

And add a smoke test:
```python
def test_high_risk_midpoint_uses_floor_for_odd_term() -> None:
    # Hand: term=359 -> midpoint=179 (floor). months_elapsed=179 -> terminates.
    loan = Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.085"), term_months=359)
    result = status(
        loan=loan, scheduled_balance=Decimal("380000"),
        original_property_value=Decimal("400000"),
        is_high_risk=True, months_elapsed=179,
    )
    assert result == "high_risk_midpoint_terminated"
```

---

### WR-09: VA-funding-fees `purchase_and_cash_out` upper-bound semantics rely on a special-case for the top band

**File:** `lib/rules/va_funding_fee.py:115-117`
**Issue:**
The band-matching logic is `dp_min <= down_payment_pct < dp_max OR (dp_max == 1.00 AND down_payment_pct == 1.00)`. The special-case for `down_payment_pct == 1.00` is correct but fragile: if a future YAML edit changes the top row's `down_payment_max` from `"1.00"` to `"1.0001"` or `"1"`, the special case silently stops applying because of Decimal lexical equality (`Decimal("1") == Decimal("1.00")` is True actually — but the check uses the literal `Decimal("1.00")`).

In practice `Decimal("1") == Decimal("1.00")` IS True, so this isn't a bug today. But the schema relies on a magic literal. A simpler invariant would be to make the top band's upper bound inclusive directly:

**Fix:** Treat the top band's `down_payment_max` as inclusive when iterating reaches the last row, OR use:

```python
in_band = dp_min <= down_payment_pct <= dp_max if dp_max == Decimal("1.00") else (
    dp_min <= down_payment_pct < dp_max
)
```

Or document the >=1.00 invariant in the YAML schema and assert it at load time.

---

## Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| BL-01 | BLOCKER | `lib/rules/loan_type.py` | FHA unlisted-county silently falls back to floor |
| BL-02 | BLOCKER | `lib/rules/va_funding_fee.py` | Cash-out refi uses purchase down-payment bands |
| BL-03 | BLOCKER | `data/reference/fha-mip-rates.yml` | High-balance MIP table missing low-LTV rows |
| BL-04 | BLOCKER | `data/reference/conforming-limits-2026.yml` + `fha-limits-2026.yml` | High_cost_counties missing two_unit/three_unit/four_unit |
| BL-05 | BLOCKER | YAML notes vs code docstring | FHA unlisted-county source-of-truth drift |
| WR-01 | WARNING | `lib/rules/usda.py` | `persons_5_to_8` used as 8-person base for >8-person uplift |
| WR-02 | WARNING | `data/reference/fha-mip-rates.yml` | Unquoted integer scalars violate YAML discipline |
| WR-03 | WARNING | LLPA + Freddie matrices | LTV bucket schemas leave fractional gap |
| WR-04 | WARNING | `lib/rules/freddie_eligibility.py` | `bool(cell["eligible"])` masks YAML shape regressions |
| WR-05 | WARNING | `lib/rules/_loader.py` | Doesn't validate `effective` is a `date` |
| WR-06 | WARNING | `lib/rules/_loader.py` | No `name` validation (theoretical path traversal) |
| WR-07 | WARNING | `tests/test_rules/test_loader.py` | `lru_cache` not cleared after each test |
| WR-08 | WARNING | `lib/rules/conventional_pmi.py` | HPA midpoint floor semantics not pinned |
| WR-09 | WARNING | `lib/rules/va_funding_fee.py` | Top-band inclusive-upper relies on magic literal |

---

_Reviewed: 2026-04-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
