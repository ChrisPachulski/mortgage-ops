---
phase: 14
slug: property-analysis-pipeline
status: SECURED
threats_total: 5
threats_open: 0
asvs_level: 1
audited: 2026-05-17
auditor: gsd-secure-phase
block_on: high
---

# Phase 14 Security Audit — property-analysis-pipeline

Verifies the 5 declared STRIDE threats from the PLAN.md `<threat_model>` blocks across plans 14-01..14-06. Every mitigation was located in the implementation; nothing was inferred from documentation. Implementation files were read-only during this audit.

## Threat Register

| Threat ID       | Category               | Component                                                                         | Disposition | Status  | Evidence                                                                                           | Files                                                                                                                                                                                              |
| --------------- | ---------------------- | --------------------------------------------------------------------------------- | ----------- | ------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-14-FLOAT      | Tampering              | Money/Rate fields on Household, Profile, ProgramResult, VerdictReason             | mitigate    | CLOSED  | `strict=True` on every Money/Rate field via aliases; test_rejects_float; test_float_rejection      | lib/models.py:23-33; lib/household.py:57-75; lib/profile.py:55-61; lib/property_analysis.py:272,310,325,339,360,365,367,373,386,401,419,441,452,472; tests/test_household.py:74-78; tests/test_property_analysis.py:484-501 |
| T-14-FRED-RACE  | Tampering              | FRED cache reads in `_todays_rate_per_program`                                    | mitigate    | CLOSED  | `with_cache_lock(CACHE_DIR, reason=...)` wraps `get_cached_or_fetch`; test_fred_lock_serialization | lib/fred_cache.py:235-254 (with_cache_lock CM); lib/property_analysis.py:96,536-543; tests/test_property_analysis.py:531-542; tests/test_property_analysis.py:1144-1157                            |
| T-14-STALE-REF  | Tampering              | Reference YAML loads (data/reference/*.yml)                                       | mitigate    | CLOSED  | `_check_staleness` emits `StaleReferenceWarning` when effective < today-12mo; `_NAME_RX` path-traversal guard | lib/rules/_loader.py:34-38,90-101; lib/rules/irs_pub936.py:55,76 (consumes load_reference); data/reference/irs-pub936.yml:3 (effective: 2025-01-01); 10 YAMLs carry `effective:` field            |
| T-14-REASON     | Repudiation            | VerdictReason in lib/property_verdict.py + lib/property_analysis.py               | mitigate    | CLOSED  | `predicate_code: str` + `computed_value: str` REQUIRED (non-Optional); D-14-VERDICT-04; citation-coverage meta-test | lib/property_analysis.py:432-446 (VerdictReason model); lib/property_verdict.py:60-91,162-258 (5 VERDICT_* constants emitted with both fields populated); tests/test_property_verdict.py:391-407 (test_reason_format_compliance); tests/test_property_verdict.py:432-... (test_verdict_code_citation_coverage)              |
| T-14-PII        | Information Disclosure | tests/fixtures/property_analysis/*.json + tests/* model construction              | mitigate    | CLOSED  | Synthetic source_url=`zillow.com/homedetails/synthetic/N_zpid/`, zpid="1|2|3", synthetic fetched_at; no real names/phones/emails; synthetic-only policy in README | tests/fixtures/property_analysis/README.md (synthetic-only policy; "No real addresses", "No AI-attribution", "No raw lender quotes"); tests/fixtures/property_analysis/sfh_conforming_king_county.json:24-26; tests/fixtures/property_analysis/condo_with_hoa_seattle.json:24-26; tests/fixtures/property_analysis/sfh_jumbo_bay_area.json:24-26 |

## Mitigation Evidence

### T-14-FLOAT — Decimal precision loss via silent float→Decimal coercion

**Verified mitigation:**

- `lib/models.py:23-33` defines `Money = Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2, ge=0)]` and `Rate = Annotated[Decimal, Field(strict=True, max_digits=7, decimal_places=6, ge=0, le=1)]`. The `strict=True` parameter is the validation seam that rejects float at the Pydantic boundary.
- All Phase 14 models inherit this discipline: `Household` (lib/household.py:57-75), `Profile` (lib/profile.py:55-61), `ProgramResult` (lib/property_analysis.py:272), `DownPaymentMatrix` (310), `StressRow` (325), `StressBlock` (339), `RefiRow` (360 — uses raw `Decimal = Field(strict=True, ...)` for signed amounts per Pitfall 3), `PointsRow` (386), `TaxBlock` (419), `VerdictReason` (441), `Verdict` (452), `AnalysisReport` (472).
- Test enforcement: `tests/test_household.py:74-78::test_rejects_float_monthly_income_strict_true` constructs `Household(monthly_income=12000.0)` and asserts `ValidationError`. `tests/test_property_analysis.py:484-501::test_float_rejection` constructs `ProgramResult(loan_amount=500000.00)` (float) and asserts `ValidationError`.
- Note: `VerdictReason.computed_value` is intentionally a `str` (lib/property_analysis.py:444) for polymorphic numeric serialization per PATTERNS.md L455. T-14-FLOAT does not apply at that field because no Decimal is in flight — the string is constructed via `str(Decimal(...))` at synthesize() time (lib/property_verdict.py:164,179,209,235,255).

### T-14-FRED-RACE — Cross-process race on FRED cache could corrupt rate data

**Verified mitigation:**

- `lib/fred_cache.py:235-254` defines `with_cache_lock(cache_dir, *, timeout, reason)` as a context manager that wraps `_acquire_lock` (read-back-verify CAS at L177-218) and `_release_lock` (only unlink-if-owned at L221-232). Stale recovery threshold is 60s (`STALE_THRESHOLD`, line 52). Lockfile path `data/cache/.fred-cache.lock` is gitignored per Plan 12-00.
- `lib/property_analysis.py:96` imports `with_cache_lock, get_cached_or_fetch, CACHE_DIR` from `lib.fred_cache`.
- `lib/property_analysis.py:536-543`: `_todays_rate_per_program` body is `with with_cache_lock(CACHE_DIR, reason=f"property-analysis read {series_id}"): entry = get_cached_or_fetch(series_id, fetcher=None)`. Every FRED read serializes through the lock.
- Test enforcement: `tests/test_property_analysis.py:531-542::test_fred_lock_serialization` patches `lib.property_analysis.with_cache_lock`, invokes `_todays_rate_per_program("Conv30")`, and asserts the lock was called with `reason="property-analysis read MORTGAGE30US"`. `tests/test_property_analysis.py:1144-1157::test_analyze_cold_fred_cache_raises_valueerror` verifies the cold-cache path inside `analyze()` re-raises as a `ValueError` with operator guidance instead of corrupting state.
- Test-injection override path: `analyze(..., fred_mortgage_30us=..., fred_mortgage_15us=...)` (lib/property_analysis.py:1480-1488) skips FRED entirely when explicit rates are passed.

### T-14-STALE-REF — Stale regulatory data masquerades as current

**Verified mitigation:**

- `lib/rules/_loader.py:34-38` defines `StaleReferenceWarning(UserWarning)`. `_check_staleness` (line 90-101) raises this warning when `effective < date.today() - relativedelta(months=12)`. `STALENESS_THRESHOLD` is 12 months (line 24).
- `_check_staleness` is invoked inside `load_reference` (line 86), so every reference YAML load is staleness-checked at load-time.
- WR-06 hardening: `_NAME_RX` (line 31) restricts reference name to `^[a-z0-9][a-z0-9-]*$`, blocking path-traversal payloads like `../../etc/passwd` (lib/rules/_loader.py:62-68).
- Phase 14 consumption path: `lib/property_analysis.py:110` imports `qualified_loan_limit as pub936_qualified_loan_limit`; `_build_tax_block` (line 1402) calls it; `lib/rules/irs_pub936.py:55,76` calls `load_reference("irs-pub936")` which triggers the staleness check.
- Reference YAMLs carry the `effective:` field: 10 verified YAMLs (atr-qm-thresholds, conforming-limits-2026, fha-limits-2026, fha-mip-rates, fannie-llpa-matrix, freddie-eligibility-matrix, usda-income-limits, irs-pub936, va-funding-fees, va-residual-income). `data/reference/irs-pub936.yml:3` has `effective: 2025-01-01` (loud at today=2026-05-17 since 16 months > 12mo, will fire the warning — confirmed loud-by-default per project convention).
- Plan 14-03 SUMMARY explicitly notes `test_tax_block_pub936` emits the expected stale warning during pytest run.

### T-14-REASON — VerdictReason missing computed_value lets user trust verdict without falsifiable basis

**Verified mitigation:**

- `lib/property_analysis.py:432-446` defines `VerdictReason(BaseModel)` with `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`. `predicate_code: str` (line 443) and `computed_value: str` (line 444) are REQUIRED (non-Optional, no default). Pydantic strict mode rejects empty/missing values for required str fields. `program: str | None` and `dp_pct: Rate | None` are the only optional fields.
- `lib/property_verdict.py:60-91` declares 5 `Final[str]` VERDICT_* constants with Pitfall 7 prefix discipline (`VERDICT_NO_GO_DTI_ALL_PROGRAMS`, `VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP`, `VERDICT_WATCH_STRESS_INCOME_FAIL`, `VERDICT_WATCH_FHA_MIP_BURDEN`, `VERDICT_GO`).
- `synthesize()` (lib/property_verdict.py:111-258) constructs every VerdictReason with BOTH fields populated. Every emission path: L162-166 (Level 1, `predicate_code=VERDICT_NO_GO_DTI_ALL_PROGRAMS, computed_value=str(min_dti)`); L177-182 (Level 2); L207-212 (Level 3); L233-239 (Level 4); L253-257 (Level 5).
- Test enforcement: `tests/test_property_verdict.py:391-407::test_reason_format_compliance` iterates all 5 cascade scenarios + 2 precedence scenarios and asserts `len(reason.predicate_code) > 0` AND `len(reason.computed_value) > 0` on every emitted reason. `test_verdict_code_citation_coverage` (line 432-) introspects `lib.property_verdict` via `vars()`, collects every `VERDICT_*` constant, and asserts each appears in at least one fixture's `expected_response.verdict.reasons[].predicate_code` OR in-test cascade scenario.

### T-14-PII — Real Zillow listings in fixtures would carry agent contact info / addresses / PII

**Verified mitigation:**

- `tests/fixtures/property_analysis/README.md` declares the synthetic-only policy ("synthetic-only per Phase 11 D-02 inherited", line 22) and the "What NOT to put here" enforcement section (line 61-74): "No real addresses", "No AI-attribution markers", "No raw lender quotes", "No `config/household.yml` values" — synthetic financial profiles only.
- Audit fields verified across all 3 fixtures:
  - `sfh_conforming_king_county.json:24-26`: `source_url="https://www.zillow.com/homedetails/synthetic/1_zpid/"`, `zpid="1"`, `fetched_at="2026-05-17T00:00:00Z"`
  - `condo_with_hoa_seattle.json:24-26`: `source_url=".../synthetic/2_zpid/"`, `zpid="2"`, `fetched_at="2026-05-17T00:00:00Z"`
  - `sfh_jumbo_bay_area.json:24-26`: `source_url=".../synthetic/3_zpid/"`, `zpid="3"`, `fetched_at="2026-05-17T00:00:00Z"`
- Grep for PII patterns (`"phone"`, `"email"`, `"agent"`, `"contact"`, `"name":`) across all 3 fixture JSONs returned zero matches.
- README explicitly retains ZIP codes ("ZIP stays real; the ZIP is not PII on its own; matches Phase 13 README precedent", line 65).
- Tests (test_property_analysis.py, test_property_verdict.py, test_household.py, test_profile.py) use synthetic factory dicts (`_make_clean_household_kwargs`, `_make_clean_listing`, `_make_clean_profile`) with fixed numeric values; no live data references.

## Unregistered Flags

None. SUMMARY files for plans 14-02, 14-03, 14-04 each carry an explicit `## Threat Flags` section reporting "None — Plan 14-XX's changes match the threat surface declared in the PLAN.md `<threat_model>` register". SUMMARY files for plans 14-01, 14-05, 14-06 do not include a `## Threat Flags` section (informational note below), but their PLAN.md threat_model blocks were verified against the 5 phase-wide threats and no new trust boundaries, network endpoints, auth paths, or unmapped attack surface were introduced. The 5 phase-wide threats cover the full attack surface of the implemented code: Money/Rate validation (T-14-FLOAT), FRED cache I/O (T-14-FRED-RACE), reference YAML I/O (T-14-STALE-REF), verdict citation discipline (T-14-REASON), and fixture-data privacy (T-14-PII).

## Accepted Risks

None. All 5 declared threats are dispositioned `mitigate` and all 5 are verified CLOSED. No `accept` or `transfer` dispositions in the phase register.

## Audit Trail

| Date       | Auditor           | Action                                                                                                | Result   |
| ---------- | ----------------- | ----------------------------------------------------------------------------------------------------- | -------- |
| 2026-05-17 | gsd-secure-phase  | Verify each of the 5 STRIDE threats from PLAN.md threat_model blocks against the implemented code     | SECURED  |

## ASVS L1 Coverage Map (V5 — Input Validation)

Per 14-RESEARCH Security Domain section, Phase 14's only applicable ASVS category at Level 1 is V5 (Validation, Sanitization, Encoding). Coverage:

| ASVS-L1 Requirement                                                                       | Mitigation                                                                                                                                            | Evidence                                                                                                                                                            |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| V5.1.1 — Verify input validation is performed on a trusted service layer                  | All Phase 14 Pydantic models declare `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` — validation at the System Layer boundary  | lib/household.py:57; lib/profile.py:55; lib/property_analysis.py:272,310,325,339,360,373,386,401,419,441,452,472; lib/property_listing.py (Phase 13 inheritance)    |
| V5.1.3 — Verify all input is validated using positive validation (allow lists)            | Literal aliases enumerate allowed values: `program ∈ {"Conv30","Conv15","FHA30","VA30","Jumbo30"}`, `MilitaryStatus`, `FilingStatus`, verdict `level` | lib/property_analysis.py:274,328,454; lib/profile.py:44-45                                                                                                          |
| V5.1.4 — Verify structured data types are validated against schema                        | Strict Pydantic v2 schema rejects extra fields, wrong types, out-of-range values; pattern fields for state_fips/county_fips                           | lib/household.py:63-64                                                                                                                                              |
| V5.1.5 — Verify URL redirects/forwards only allow destinations on an allow list           | `lib/rules/_loader.py:_NAME_RX` (line 31) restricts reference YAML stems to `^[a-z0-9][a-z0-9-]*$` blocking path-traversal payloads                  | lib/rules/_loader.py:31,62-68                                                                                                                                       |
| V5.2.x — Sanitization & sandboxing                                                        | Not applicable — Phase 14 is a pure computation engine; no HTML/SQL/shell sinks. Output is structured Pydantic; rendering deferred to Phase 15        | n/a                                                                                                                                                                 |
| V5.3.x — Output Encoding                                                                  | Not applicable at Phase 14 — output is Pydantic JSON via `model_dump_json()` (RFC 8259-conformant). No template/SQL/shell concatenation               | n/a                                                                                                                                                                 |
| V5.4.x — Memory/string/unmanaged code                                                     | Pure Python; no FFI; numpy-financial is the only native dep and operates on validated Decimals                                                        | n/a                                                                                                                                                                 |
| V5.5.x — Deserialization                                                                  | All deserialization paths use `model_validate_json` (strict Pydantic) or `yaml.safe_load` (lib/rules/_loader.py:70) — no `yaml.load` or `pickle`     | lib/rules/_loader.py:70                                                                                                                                             |

Other ASVS L1 categories (V1 architecture, V2 authentication, V3 session, V4 access control, V6 stored crypto, V7 errors/logging, V8 data protection, V9 communications, V10 malicious code, V11 BL, V12 files, V13 API, V14 config) are not in scope for Phase 14 per the RESEARCH Security Domain section — this is a deterministic pure-Python compute engine invoked by a higher-layer CLI (Phase 15) and skill (Phase 10).

## SECURED

**Phase:** 14 — property-analysis-pipeline
**Threats Closed:** 5/5
**ASVS Level:** 1

All 5 declared STRIDE threats (T-14-FLOAT, T-14-FRED-RACE, T-14-STALE-REF, T-14-REASON, T-14-PII) verified CLOSED with disposition `mitigate`. No unregistered attack surface detected in SUMMARY threat-flag sections. No accepted risks. ASVS L1 V5 input-validation coverage proven by `strict=True/frozen=True/extra="forbid"` Pydantic configuration on every Phase 14 model plus the `_NAME_RX` path-traversal guard in `lib/rules/_loader.py`.
