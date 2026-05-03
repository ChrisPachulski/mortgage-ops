---
phase: 05
slug: arm-modeling
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-02
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| ARMRequest model_validate_json | Untrusted JSON from CLI input crosses here; float-gate + Pydantic validation are the two-layer defense | Money/Rate Decimal fields (principal, annual_rate, floor_rate, assumed_index_rate, index_path[].value) |
| scripts/arm_simulate.py --help fast path | D-18 contract: lib.arm + lib.amortize + numpy_financial must NOT load on the help path | None — argparse only |
| sys.path injection in arm_simulate.main() | Project root must be inserted BEFORE scripts._cli_helpers and lib.arm imports | None — module resolution |
| Wave 0 stubs → Wave 2..6 flip contract | xfail stubs define the landing pad each engine wave must satisfy; mismatch silently leaves a requirement unverified | Test contract |
| Phase 4 regression boundary | quantize_rate promotion is a pure-internal refactor; public evaluate() API of lib.affordability must remain unchanged | Rounding behavior (ROUND_HALF_UP, 6 decimal places) |
| references/arm-mechanics.md citation correctness | Broken URLs mislead compliance investigation; stale section numbers (B5-3.5-01, §4404) point to wrong/missing docs | Regulatory traceability |
| tests/fixtures/arm/*.json expected values | Engine-emitted Decimal-string fixture values; source field + regenerator script provide provenance chain | ARM amortization math (payment, rate, balance, applied_cap) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-09 | Tampering (test contract drift) | tests/test_arm.py stub names | mitigate | All 32 stub names from test_inventory present; verified by grep count (16+16=32 names found) | VERIFIED |
| T-05-10 | Information Disclosure (false-pass via skipped xfail) | xfail decorators | mitigate | Every xfail uses strict=True; 1 remaining xfail (test_oracle_cross_validation_5_1) confirmed strict=True at tests/test_arm.py:711 | VERIFIED |
| T-05-11 | Denial of Service (test-suite slowdown) | new 32 stubs | accept | See Accepted Risks Log — zero-cost stubs; all subsequently flipped to real assertions | ACCEPTED |
| T-05-12 | Repudiation (silent regression to Phase 4 baseline) | conftest.py extension | mitigate | arm_fixture added (1 occurrence); golden_fixture + amortize_fixture + affordability_fixture all preserved (3 occurrences); tests/conftest.py verified | VERIFIED |
| T-05-08 | Tampering (Phase 4 regression) | _quantize_rate semantic | mitigate | _quantize_rate count=0 in lib/affordability.py; _RATE_QUANTUM count=0; quantize_rate count=5 (1 import + 4 call sites) in lib/affordability.py | VERIFIED |
| T-05-13 | Tampering (silent rounding-mode change) | quantize_rate body | mitigate | test_quantize_rate_round_half_up present in tests/test_money.py (1 occurrence); Decimal("0.0654995") boundary assertion present (2 occurrences) | VERIFIED |
| T-05-14 | Information Disclosure (private import leak) | downstream import path | mitigate | _quantize_rate count=0 in lib/affordability.py; _RATE_QUANTUM count=0 confirmed | VERIFIED |
| T-05-15 | Repudiation (mypy --strict regression) | type checking | mitigate | SUMMARY 05-01 reports mypy --strict clean across lib/money.py, lib/affordability.py, tests/test_money.py | VERIFIED |
| T-05-02 | Tampering (index-path period misalignment) | ARMRequest._index_path_periods_align_to_reset_triggers | mitigate | _index_path_periods_align_to_reset_triggers present 2x in lib/arm.py; @model_validator(mode="after") present 1x; raises ValueError on misaligned periods | VERIFIED |
| T-05-16 | Tampering (silent floor_rate omission via default) | ARMTerms.floor_rate field | mitigate | floor_rate: Rate (no None, no default) at lib/arm.py:56; grep -c 'floor_rate: Rate | None' returns 0 | VERIFIED |
| T-05-17 | Information Disclosure (extra fields silently accepted) | ARMTerms/ARMRequest model_config | mitigate | model_config = ConfigDict(strict=True, frozen=True, extra="forbid") present 6 times in lib/arm.py (one per model class) | VERIFIED |
| T-05-18 | Tampering (ARMPayment fields drift from Phase 1 Payment) | ARMPayment subclass relationship | mitigate | class ARMPayment(Payment) present 1x in lib/arm.py; model_config re-specified (counted in 6 total) | VERIFIED |
| T-05-19 | Repudiation (model_config not enforced because not re-specified) | ARMPayment model_config inheritance | accept | See Accepted Risks Log — RESEARCH LM-4 confirms Pydantic v2 auto-inherits; re-specification confirmed present for grep-discoverability | ACCEPTED |
| T-05-03 | Tampering (cap precedence error) | _compute_new_rate is_first_reset branch | mitigate | is_first_reset = epoch_idx == 1 at lib/arm.py:272; initial_cap_bps if is_first_reset else periodic_cap_bps at lib/arm.py:273; applied_cap = "initial" if is_first_reset else "periodic" at lib/arm.py:302 | VERIFIED |
| T-05-04 | Tampering (floor breach) | _compute_new_rate effective_floor | mitigate | effective_floor = max(margin_rate, terms.floor_rate) at lib/arm.py:270, computed BEFORE clamp; also at lib/arm.py:243 in docstring example | VERIFIED |
| T-05-05 | Tampering (off-by-one reset month) | _compute_reset_triggers period start | mitigate | period = arm_terms.initial_period_months + 1 at lib/arm.py:221; also in boundaries list at lib/arm.py:341 | VERIFIED |
| T-05-06 | Tampering (cumulative-totals drift) | build_arm_schedule cum_int_carry stitching | mitigate | cum_int_carry + cum_prin_carry initialized at lib/arm.py:352-353; stitched at lib/arm.py:397-398; carried forward at lib/arm.py:434-435 | VERIFIED |
| T-05-07 | Elevation of Privilege (silent payoff at every reset) | synthetic_loan.term_months | mitigate | remaining_full_term = loan.term_months - start + 1 at lib/arm.py:376; term_months=remaining_full_term at lib/arm.py:380; grep for term_months=*reset_period_months returns 0 | VERIFIED |
| T-05-20 | Tampering (slice off-by-one) | sliced = synthetic.payments[:epoch_window] | mitigate | epoch_window = end - start at lib/arm.py:358; sliced = synthetic.payments if is_final_epoch else synthetic.payments[:epoch_window] at lib/arm.py:392 | VERIFIED |
| T-05-21 | Tampering (index_value_used wrong) | _compute_new_rate index resolution | mitigate | for-loop at lib/arm.py:261-263 with explicit entry.period == period match + break; D-01 override-wins semantics | VERIFIED |
| T-05-22 | Information Disclosure (note_rate leak when None) | _compute_new_rate note_rate_eff fallback | mitigate | note_rate_eff = terms.note_rate if terms.note_rate is not None else loan_annual_rate at lib/arm.py:276; test_note_rate_defaults_to_loan_annual_rate passes | VERIFIED |
| T-05-01 (helper) | Tampering (JSON-float coercion bypass) | scripts/_cli_helpers.find_json_float_loc | mitigate | find_json_float_loc + make_decimal_type_envelope present in scripts/_cli_helpers.py (2 functions); tests/test_cli_helpers.py has 19 parametric tests (>=18 required); Phase 3+4 byte-equivalent confirmed | VERIFIED |
| T-05-23 | Tampering (envelope shape divergence across CLIs) | scripts/_cli_helpers.make_decimal_type_envelope | mitigate | Single source of truth; tests/test_cli_helpers.py::TestMakeDecimalTypeEnvelope pins 6-key shape; _find_json_float_loc removed from amortize.py (count=0) and affordability.py (count=0) | VERIFIED |
| T-05-25 | Repudiation (Phase 3/4 regression after factor) | scripts/amortize.py + scripts/affordability.py refactor | mitigate | from scripts._cli_helpers import present in both scripts (1x each); SUMMARY 05-04a reports 42 passed (amortize) + 78 passed + 4 skipped (affordability) byte-equivalent | VERIFIED |
| T-05-01 (CLI) | Tampering (JSON-float coercion bypass via ARM CLI) | scripts/arm_simulate.py float-gate invocation | mitigate | find_json_float_loc(raw) present 1x in scripts/arm_simulate.py; make_decimal_type_envelope( present 1x; from scripts._cli_helpers import present 1x; 4 float-reject tests pin all ARM money/rate fields | VERIFIED |
| T-05-24 | Information Disclosure (lib.arm imported on --help path) | scripts/arm_simulate.py main() lazy imports | mitigate | from lib.arm import at line 69 is AFTER parser.parse_args() at line 59; test_cli_help_does_not_import_lib_arm asserts lib.arm + lib.amortize + numpy_financial NOT in sys.modules after --help | VERIFIED |
| T-05-26 | Tampering (sys.path injection ordering) | scripts/arm_simulate.py main() | mitigate | sys.path.insert at line 66 is BEFORE from lib.arm import at line 69 and from scripts._cli_helpers import at line 71; test_cli_smoke_subprocess_round_trip pins last reset trigger at period 349 | VERIFIED |
| T-05-27 | Information Disclosure (broken citation) | references/arm-mechanics.md citation URLs | mitigate | All 4 required URL fragments present: selling-guide.fanniemae.com/sel/b2-1.4-02, sf.freddiemac.com/...sofr-indexed-arms, consumerfinance.gov/ask-cfpb/what-are-rate-caps, abt.bank/.../Early-ARM-Disclosure (ABT substituted for AmericU after URL rot; see T-05-34) | VERIFIED |
| T-05-28 | Tampering (citation regression) | references/arm-mechanics.md vs D-08 [REVISED] | mitigate | B5-3.5-01 count=0; §4404 / 4404 count=0 in references/arm-mechanics.md; test_arm_mechanics_citations pins forbidden fragments; 6302.7(b) present | VERIFIED |
| T-05-29 | Repudiation (docstring drift from doc file) | lib/arm.py ARMTerms.__doc__ | mitigate | "See references/arm-mechanics.md" present 1x in lib/arm.py; test_arm_terms_docstring_cites_arm_mechanics passes | VERIFIED |
| T-05-30 | Information Disclosure (LM-3 teaser-ARM convention silent) | references/arm-mechanics.md Section 7 | mitigate | "teaser" token found 11x in references/arm-mechanics.md (case-insensitive); test_arm_mechanics_doc_sections_present greps for teaser token | VERIFIED |
| T-05-31 | Tampering (AI attribution in docs) | references/arm-mechanics.md content | mitigate | co-authored count=0; anthropic count=0; claude count=0 (case-insensitive) in references/arm-mechanics.md | VERIFIED |
| T-05-32 | Tampering (fixture expected blocks) | tests/fixtures/arm/*.json expected blocks | mitigate | 11 JSON fixtures found in tests/fixtures/arm/; all 11 have "source" field; scripts/_generate_arm_fixtures.py committed | VERIFIED |
| T-05-33 | Information Disclosure (oracle cross-validation) | test_oracle_cross_validation_5_1/5_6 | mitigate | test_oracle_cross_validation_5_6 passes with exact Decimal equality vs ABT Bank disclosure (AmericU substituted; see T-05-34); test_oracle_cross_validation_5_1 stays xfailed (Phase 8+ deferral, see T-05-34) | VERIFIED |
| T-05-34 | Tampering (oracle URL/PDF staleness) | tests/fixtures/arm/oracle/*.pdf | accept | See Accepted Risks Log — AmericU URL 404'd; ABT Bank substituted (Rule-4-A); Bankrate/Vertex42 browser captures deferred Phase 8+ (Rule-4-B); test_oracle_cross_validation_5_1 stays xfailed with strict=True | ACCEPTED |
| T-05-35 | Tampering (D-10 citation-coverage meta-test) | test_applied_cap_citation_coverage | mitigate | test_applied_cap_citation_coverage walks tests/fixtures/arm/*.json directory and asserts 5 Literal values {initial, periodic, lifetime, floor, none} are all present; test passes; D-10 coverage matrix confirmed in SUMMARY 05-06 | VERIFIED |
| T-05-36 | Repudiation (arm_5_1_payment_jump_at_61 applied_cap) | tests/fixtures/arm/arm_5_1_payment_jump_at_61.json | mitigate | 25 applied_cap="none" entries confirmed in arm_5_1_payment_jump_at_61.json (inputs chosen to produce open-interval result per LM-5) | VERIFIED |
| T-05-37 | Tampering (arm_5_1_off_by_one_negative.json off-by-one) | tests/fixtures/arm/arm_5_1_off_by_one_negative.json | mitigate | Fixture periods 58+59 confirm rate_in_effect=0.050000 (still old); period 61 confirms rate_in_effect=0.077500 (already new); test_arm_5_1_off_by_one_negative asserts BOTH schedule.payments[58] (old rate) and schedule.payments[60] (new rate) | VERIFIED |

*Status: open · closed · verified · accepted*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-11 | All 32 Wave-0 stubs were zero-cost pytest.fail("Wave 0 stub") calls; total runtime impact was < 0.5s per SUMMARY 05-00. Subsequent waves replaced stubs with real assertions. No residual slowdown risk remains — all stubs have been flipped. | Phase 05 executor | 2026-04-30 |
| AR-05-02 | T-05-19 | RESEARCH LM-4 confirmed Pydantic v2 auto-inherits model_config from parent class. ARMPayment re-specifies model_config = ConfigDict(strict=True, frozen=True, extra="forbid") for grep-discoverability and Pydantic v3 forward-compatibility. The re-specification is present (counted in the 6-total grep gate); the accept disposition acknowledges that the inheritance guarantee is RESEARCH-verified, not a mitigation gap. | Phase 05 executor | 2026-04-30 |
| AR-05-03 | T-05-34 | AmericU 5/6 SOFR ARM Disclosure URL returned HTTP 404 after URL rot. Substituted ABT Bank's functionally-equivalent "5/6, 7/6 & 10/6 SOFR ARM Disclosure" (same 2/1/5 caps, same month-61 first reset, same every-6-months cadence, same SOFR index, same rounding convention). ABT PDF verified live 2026-04-30 (HTTP 200, 112 KB, SHA256 891e70b7bc9de8a9804f53f32d1cb05488e381dd9b147bcd76d466555da2d83b). Bankrate (5/1, 7/1, 10/1) and Vertex42 (5/1) browser/spreadsheet captures require human interaction; deferred to Phase 8+. test_oracle_cross_validation_5_1 stays xfailed with strict=True to prevent silent XPASS drift. Phase 8+ backlog item created in SUMMARY 05-06. | Phase 05 executor | 2026-05-02 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Threat Flags

None. All SUMMARY ## Threat Flags sections are either absent or explicitly "None." No new attack surface was introduced during implementation without a corresponding threat registration.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Accepted | Run By |
|------------|---------------|--------|------|----------|--------|
| 2026-05-02 | 36 | 33 | 0 | 3 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (AR-05-01, AR-05-02, AR-05-03)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-02
