---
phase: 02-regulatory-reference-data-rules-predicates
fixed_at: 2026-04-26T00:00:00Z
review_path: .planning/phases/02-regulatory-reference-data-rules-predicates/02-REVIEW.md
iteration: 1
findings_in_scope: 14
fixed: 14
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-04-26T00:00:00Z
**Source review:** `.planning/phases/02-regulatory-reference-data-rules-predicates/02-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 14 (5 blocker + 9 warning; info findings out of scope per `fix_scope=critical_warning`)
- Fixed: 14
- Skipped: 0
- Test suite: 224/224 baseline -> 254/254 post-fix (+30 new regression tests)

## Fixed Issues

### BL-01: FHA classification silently falls back to floor for unlisted counties (contradicts YAML intent)

**Files modified:** `lib/rules/loan_type.py`, `tests/test_rules/test_loan_type.py`
**Commit:** 19ab9d3
**Applied fix:** Rewrote `_county_limit_fha` to raise `MissingCountyDataError` for unlisted high-cost counties (matching the YAML notes and the conventional `_county_limit` semantics), with an explanatory docstring. Updated module-level edge-case docs. Added regression test `test_fha_unlisted_county_above_floor_raises_missing_county_data` exercising Autauga AL (unlisted) at $700k > floor.

### BL-02: VA funding fee for cash-out refi uses purchase down-payment bands (regulatorily wrong)

**Files modified:** `lib/rules/va_funding_fee.py`, `data/reference/va-funding-fees.yml`, `tests/test_rules/test_va_funding_fee.py`, `tests/fixtures/rules/va_funding_fee_cash_out_subsequent.json`
**Commit:** 983a2e4
**Applied fix:** Added cash-out refi as a flat-fee branch (`flat_fees.cash_out_first_use=0.0215`, `cash_out_subsequent_use=0.0330`) per VA M26-7 Chapter 8. Renamed YAML key `purchase_and_cash_out` -> `purchase` (purchase-only DP-banded table) and renamed helper `_lookup_purchase_or_cashout_pct` -> `_lookup_purchase_pct`. Updated module docstring and the existing cash-out fixture comment. Added two regression tests pinning that cash-out fees ignore `down_payment_pct`.

### BL-03: FHA MIP table has uncovered (term, LTV) cells for high-balance loans

**Files modified:** `data/reference/fha-mip-rates.yml`, `tests/test_rules/test_fha_mip.py`
**Commit:** c9f447b
**Applied fix:** Added two missing rows to the high-balance tier covering `LTV 0.00-0.78` for term > 15yr (rate `0.0070`) and term ≤ 15yr (rate `0.0040`), matching the existing 0.78-0.90 high-balance rates per HUD ML 2023-05 Table B structure. Added three regression tests (term 360 low-LTV, term 180 low-LTV, and the boundary case at exactly LTV=0.78).

### BL-04: Conforming-limits high_cost_counties only carry `one_unit` (silent KeyError if multi-unit ever lands)

**Files modified:** `lib/rules/loan_type.py`, `data/reference/conforming-limits-2026.yml`, `data/reference/fha-limits-2026.yml`, `tests/test_rules/test_loan_type.py`
**Commit:** 3c8d955
**Applied fix:** Chose option (b) from the review (defense-in-depth assertion) since v1 ships unit_count=1 only and filling in 50+ counties × 3 unit-counts is disproportionate to scope. Added `NotImplementedError` guards to `_county_limit` and `_county_limit_fha` that raise BEFORE the YAML KeyError, with an actionable message pointing maintainers at the FHFA / HUD county XLSXs. Documented the data-shape constraint in both YAML notes blocks. Added two helper-level regression tests (one for each helper).

### BL-05: YAML notes contradict code on FHA unlisted-county semantics (cross-artifact source-of-truth drift)

**Files modified:** `data/reference/fha-limits-2026.yml`
**Commit:** 6cb91c8
**Applied fix:** BL-01 already aligned the code to match the YAML notes. This commit pins the alignment in the YAML notes block itself with an explicit "if you edit one side you MUST edit the other" reminder, preventing silent re-divergence between the regulatory-grade YAML annotation and the predicate behavior.

### WR-01: VA residual income table treats `persons_5_to_8` as 8-person base for above-8 uplift

**Files modified:** `lib/rules/usda.py`
**Commit:** 5bd4c47
**Applied fix:** Documented the banded-uplift simplification in the module docstring with explicit deferral rationale: USDA's published per-person table differentiates 5/6/7/8; we ship the banded value. For typical (≤8) households this is exact; for >8 households the result deviates slightly. Acceptable for v1 personal-use scope; flagged for v2 if multi-generational eligibility becomes in-scope.

### WR-02: `fha-mip-rates.yml` has unquoted integer scalars

**Files modified:** `data/reference/fha-mip-rates.yml`, `lib/rules/fha_mip.py`, `tests/test_rules/test_fha_mip.py`
**Commit:** 0fff503
**Applied fix:** Quoted `term_months_min`/`term_months_max` in every annual_mip_table row and the `132`-month termination period. Updated `_lookup_annual_mip` and the termination read in `compute()` to coerce strings to int. Added a regression test that walks every numeric scalar in `fha-mip-rates.yml` and asserts each is a quoted string per project Pitfall 1.

### WR-03: LTV bucket schemas (Fannie + Freddie) leave a fractional gap

**Files modified:** `lib/rules/fannie_eligibility.py`, `lib/rules/freddie_eligibility.py`, `tests/test_rules/test_fannie_eligibility.py`, `tests/test_rules/test_freddie_eligibility.py`
**Commit:** 2e30802
**Applied fix:** Added an explicit `ValueError` guard at the top of both `_ltv_bucket` helpers when `ltv_pct.as_tuple().exponent < -2`, with a message that tells the caller exactly how to quantize. Separate guard for NaN/Infinity exponent sentinels per mypy --strict. Documented the 2-decimal contract in both module docstrings. Added three regression tests on the Fannie side (rejects 4-decimal, accepts 2-decimal, accepts 1-decimal) and two on the Freddie side.

### WR-04: `bool(cell["eligible"])` defensively coerces but masks YAML-shape regressions

**Files modified:** `lib/rules/freddie_eligibility.py`, `tests/test_rules/test_freddie_eligibility.py`
**Commit:** 120b85a
**Applied fix:** Replaced `bool(cell["eligible"])` with an explicit `isinstance(raw, bool)` check that raises `TypeError` pointing at the YAML cell coordinates. Added two regression tests: a schema-level scan that asserts every `eligibility[cs][ltv].eligible` cell in the shipped YAML is a Python bool, and an integration test that materializes a YAML with quoted `'false'` (in tmp_path) and confirms the predicate fails loud.

### WR-05: `_loader.load_reference` does not validate that `effective` is a `date`

**Files modified:** `lib/rules/_loader.py`, `tests/test_rules/test_loader.py`
**Commit:** e6478bb
**Applied fix:** Added an `isinstance(raw["effective"], date)` check after the existence check, raising `MissingReferenceFieldError` with a clear "must be an unquoted YAML date" message that explicitly rejects quoted strings. Added a regression test materializing a YAML with quoted `'2026-01-01'` effective.

### WR-06: `_loader` does not validate the `name` argument (theoretical path traversal)

**Files modified:** `lib/rules/_loader.py`, `tests/test_rules/test_loader.py`
**Commit:** 62d8b57
**Applied fix:** Added module-level `_NAME_RX = re.compile(r"^[a-z0-9][a-z0-9-]*$")` matching the naming convention all 10 shipped YAMLs already follow. `load_reference` raises `ValueError` on mismatch with a message describing the allowed pattern. Added a parametrized regression test covering 10 invalid name shapes (path traversal, absolute paths, spaces, uppercase, leading-hyphen, empty, dotted names, underscore-names).

### WR-07: `lru_cache` in `_loader` retains tmp-path entries across `test_loader.py` tests

**Files modified:** `tests/test_rules/test_loader.py`
**Commit:** 2411fff
**Applied fix:** Added an autouse pytest fixture `_clear_loader_cache` that yields between `cache_clear()` (before) and `cache_clear()` (after), ensuring synthetic-tmp-path entries from one test never bleed into another. The explicit `cache_clear()` calls in individual tests stay in place as defense-in-depth (harmless and paired with monkeypatch ordering).

### WR-08: HPA midpoint uses `term_months // 2` — semantics for odd terms not pinned

**Files modified:** `lib/rules/conventional_pmi.py`, `tests/test_rules/test_conventional_pmi.py`
**Commit:** c88800d
**Applied fix:** Documented the rounding decision and rationale in a multi-line comment at the call site (HPA §4902(g) is silent on rounding for odd-month terms; we use floor per industry convention and borrower-favorability). Added two regression tests pinning the convention: term=359, months_elapsed=179 fires (= floor midpoint); months_elapsed=178 does not.

### WR-09: VA-funding-fees `purchase_and_cash_out` upper-bound semantics rely on a special-case for the top band

**Files modified:** `lib/rules/va_funding_fee.py`, `tests/test_rules/test_va_funding_fee.py`
**Commit:** 55b10f5
**Applied fix:** Refactored `_lookup_purchase_pct` to identify the top band by row position (`index == len(table) - 1`) and apply inclusive-upper to that row only, instead of conditioning on the literal `dp_max == Decimal("1.00")`. This matches the YAML schema's actual invariant ("the last row covers the top of the range"). Added a regression test confirming 100%-down maps to the top band cleanly post-refactor.

---

_Fixed: 2026-04-26T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
