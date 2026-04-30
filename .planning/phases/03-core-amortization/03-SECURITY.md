---
phase: 03
slug: core-amortization
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-30
---

# SECURITY.md — Phase 3: core-amortization

**Phase:** 3 — core-amortization
**Threat Register Size:** 46 (across plans 03-01..03-06)
**ASVS Level:** 1
**Block-on policy:** high
**Audit date:** 2026-04-30
**Phase verification status:** PASSED (5/5 success criteria per 03-VERIFICATION.md)

## Summary

| Metric | Count |
|--------|-------|
| Threats CLOSED | 45/46 |
| Threats OPEN | 0/46 |
| Threats CLOSED-with-substitution | 1/46 (T-03-02-08; mitigation substitution accepted) |
| Unregistered threat flags | 0 |
| BLOCKERS | 0 |
| WARNINGS | 1 (informational; mitigation substitution) |

No HIGH-severity threats are open. Block-on=high gate is **clear**.

## Verification methodology

For each threat in plans 03-01..03-06:

- `mitigate` — grep for cited mitigation pattern in cited file(s); confirm test exists and pins the contract.
- `accept` — confirm rationale matches CLAUDE.md / 03-CONTEXT.md personal-use, single-tenant scope.
- `transfer` — none in this phase.

Implementation files (`lib/models.py`, `lib/amortize.py`, `scripts/amortize.py`, `tests/test_models.py`, `tests/test_amortize.py`, `tests/fixtures/amortize/*.json`) were read but not modified.

## Threat verification — Plan 03-01 (Schedule D-15 validator)

| Threat ID | Cat | Disposition | Status | Evidence |
|-----------|-----|-------------|--------|----------|
| T-03-01-01 | T | mitigate | CLOSED | `lib/models.py:76-91` `_total_interest_matches_last_cumulative` raises `ValueError("D-15 invariant: ...")`. Test `tests/test_models.py:205-230` `test_schedule_total_interest_must_match_last_cumulative` asserts ValidationError. |
| T-03-01-02 | I | accept | CLOSED | Personal-use scope per CLAUDE.md. No PII in dollar amounts; rationale consistent. |
| T-03-01-03 | D | accept | CLOSED | Test `tests/test_models.py:233-248` `test_schedule_with_empty_payments_skips_d15_validator` documents the scaffold-mode skip. Empty-payments path is internal Phase 1 convenience; not reachable from Phase 3 boundary. |
| T-03-01-04 | E | mitigate | CLOSED | `lib/models.py:39,51,67` `ConfigDict(strict=True, frozen=True, extra="forbid")` on Loan, Payment, Schedule. Test `tests/test_models.py:85-92` `test_loan_is_frozen_after_construction` confirms post-construction mutation rejected. |

## Threat verification — Plan 03-02 (engine + Pydantic models)

| Threat ID | Cat | Disposition | Status | Evidence |
|-----------|-----|-------------|--------|----------|
| T-03-02-01 | T | mitigate | CLOSED | `lib/amortize.py:184-194` `_biweekly_mode_consistency` validator. Test `tests/test_amortize.py:227-242` `test_amortize_request_rejects_biweekly_mode_when_monthly` asserts substring `"biweekly_mode must be None"`. |
| T-03-02-02 | T | mitigate | CLOSED | `lib/amortize.py:170-171` `period: int = Field(ge=1)` and `amount: Decimal = Field(strict=True, gt=Decimal("0"), ...)`. Tests `tests/test_amortize.py:703-714` reject `period=0` and `amount=0.00`. |
| T-03-02-03 | T | mitigate | CLOSED | `lib/models.py:23-33` Money/Rate Annotated aliases with `strict=True`. Tests `tests/test_models.py:37-48` `test_loan_rejects_float_principal` + `test_loan_rejects_float_annual_rate`. |
| T-03-02-04 | I | accept | CLOSED | Personal-use scope per CLAUDE.md / 03-CONTEXT.md. Validator messages reveal only user-submitted values. |
| T-03-02-05 | D | accept | CLOSED | `lib/models.py:43` `term_months: int = Field(ge=1, le=600)`. Hard cap enforced. |
| T-03-02-06 | D | accept | CLOSED | Personal-use scope per CLAUDE.md. CLI tool, single-tenant. Phase 8 stress (future) may revisit. |
| T-03-02-07 | E | mitigate | CLOSED | All Pydantic models have `frozen=True`. Grep shows zero `global` / `nonlocal` declarations in `lib/amortize.py`. `_resolve_extra` (lib/amortize.py:226-252) takes inputs by parameter, returns a value, holds no module-level state. |
| T-03-02-08 | T | mitigate | CLOSED-WITH-SUBSTITUTION (WARNING, non-blocking) | The named test `test_npf_returns_decimal_when_fed_decimal` is NOT present in `tests/test_amortize.py`. However, the threat is functionally mitigated by exact-Decimal-equality across 4 parametrized golden oracles (`tests/test_amortize.py:107-129` `test_fixed_rate_oracle` × FOUR_ORACLE_IDS) — any future numpy-financial regression that returns float instead of Decimal would fail those exact-equality assertions on the next CI run. Engine has zero `Decimal(str(...))` reconstructions (verified by grep over `lib/amortize.py`). See "Findings & follow-ups" below. |
| T-03-02-09 | I | accept | CLOSED | Deliberate JSON contract per 03-CONTEXT.md D-19. Personal-use; no PII. |

## Threat verification — Plan 03-03 (CLI boundary + JSON parsing)

| Threat ID | Cat | Disposition | Status | Evidence |
|-----------|-----|-------------|--------|----------|
| T-03-03-01 | T | mitigate | CLOSED | `scripts/amortize.py:72-122` `_find_json_float_loc` pre-validation gate using `json.loads(raw, parse_float=Decimal)`. Pydantic v2 strict mode is also engaged on Loan/Money/Rate. Test `tests/test_amortize.py:873-928` `test_cli_rejects_float_principal` pins the 6-key envelope shape. |
| T-03-03-02 | T | mitigate | CLOSED | `extra="forbid"` confirmed on every model: Loan (`lib/models.py:39`), Payment (`:51`), Schedule (`:67`), ExtraPrincipalEntry (`lib/amortize.py:169`), AmortizeRequest (`:178`). Test `tests/test_models.py:63-71` `test_loan_rejects_unknown_field`. |
| T-03-03-03 | T | mitigate | CLOSED | `_biweekly_mode_consistency` validator (`lib/amortize.py:184-194`); CLI surfaces via Pydantic `e.json()`. Test `tests/test_amortize.py:931-962` `test_cli_d02_violation_at_boundary`. |
| T-03-03-04 | I | accept | CLOSED | Personal-use, single-tenant CLI per CLAUDE.md / 03-CONTEXT.md. No multi-user privilege boundary. |
| T-03-03-05 | I | accept | CLOSED | Same scope rationale as above. |
| T-03-03-06 | D | mitigate | CLOSED | Pydantic strict + Loan field constraints (`term_months <= 600`, `extra="forbid"` everywhere). Python json stdlib's default recursion limit (1000) bounds depth. |
| T-03-03-07 | D | accept | CLOSED | Personal-use scope. |
| T-03-03-08 | E | accept | CLOSED | CLI tool, single-tenant; no privilege boundary. |
| T-03-03-09 | T | mitigate | CLOSED | Lazy-imports inside `def main()` (`scripts/amortize.py:159-160, 194`); top-level imports limited to argparse, json, sys, pathlib, typing. Test `tests/test_amortize.py:754-827` `test_cli_help_does_not_import_lib_amortize` (subprocess + importlib structural check). |

## Threat verification — Plan 03-04 (test fixtures + invariants)

| Threat ID | Cat | Disposition | Status | Evidence |
|-----------|-----|-------------|--------|----------|
| T-03-04-01 | T | mitigate | CLOSED | All 7 fixtures in `tests/fixtures/amortize/*.json` have a `source:` field documenting provenance (verified by grep). `tests/fixtures/golden_pmt.json` is externally anchored (Wikipedia, CFPB LE). |
| T-03-04-02 | T | mitigate | CLOSED | 14 occurrences of `assert_schedule_invariants` in `tests/test_amortize.py` (>= 11 threshold). Helper at `tests/test_amortize.py:56-75` enforces AMRT-07 / D-09 / D-15 on every produced schedule. |
| T-03-04-03 | T | mitigate | CLOSED | Zero matches for `assertAlmostEqual` / `almost_equal` in `tests/test_amortize.py` and `tests/test_models.py`. Money discipline (CLAUDE.md) preserved. |
| T-03-04-04 | T | mitigate | CLOSED | Verified programmatically: parsing each `tests/fixtures/amortize/*.json` with `parse_float=Decimal` yields zero JSON-number-with-decimal-point hits across all 7 fixtures. All money values are JSON strings. |
| T-03-04-05 | I | accept | CLOSED | Test stderr is captured by `subprocess.run(..., capture_output=True)` patterns (e.g., `tests/test_amortize.py:830-839, 842-853, 856-870`). Personal-use; no PII. |
| T-03-04-06 | D | accept | CLOSED | Phase 03-VERIFICATION.md confirms test runtime well below threshold. |
| T-03-04-07 | E | mitigate | CLOSED | `Path(__file__).resolve().parent.parent / "..."` patterns in `tests/test_amortize.py:50-51, 781` and `tests/conftest.py:19`. All paths repo-bounded. Subprocess inputs stay in `tmp_path` (pytest fixture). |
| T-03-04-08 | T | mitigate | CLOSED | Zero matches for `RECORDED` placeholder in `tests/fixtures/amortize/*.json` (verified by grep). All values are concrete pinned numbers. |

## Threat verification — Plan 03-05 (CR-01 uniqueness validator)

| Threat ID | Cat | Disposition | Status | Evidence |
|-----------|-----|-------------|--------|----------|
| T-03-05-01 | T | mitigate | CLOSED | `lib/amortize.py:196-223` `_no_duplicate_recurring_periods` validator. 3 negative tests at `tests/test_amortize.py:250-337` (forward, reversed, three-way). 3 positive sibling tests at `:340-426` (step-up distinct periods, duplicate one-shots, recurring+one-shot). |
| T-03-05-02 | T | mitigate | CLOSED | Validator runs at AmortizeRequest model_validator (mode="after"); `_resolve_extra` only invoked from inside `build_schedule` AFTER validator has fired. Negative tests confirm rejection at request-construction time. |
| T-03-05-03 | S | mitigate | CLOSED | 3 positive tests pin legitimate D-05 cases: `test_amortize_request_accepts_d05_step_up_with_distinct_periods`, `test_amortize_request_accepts_duplicate_one_shots_at_same_period`, `test_amortize_request_accepts_recurring_plus_oneshot_at_same_period`. |
| T-03-05-04 | I | accept | CLOSED | Personal-use scope. Message reveals only the period number user submitted. |
| T-03-05-05 | R | mitigate | CLOSED | 3 negative regression tests + grep-anchored docstring `"Uniqueness rider (CR-01 closure):"` at `lib/amortize.py:57`. |
| T-03-05-06 | D | accept | CLOSED | O(n) over ~720 entries; bounded by realistic schedule periods. |
| T-03-05-07 | E | accept | CLOSED | `_resolve_extra` is module-private (leading underscore). Direct external call by callers in same package is out-of-scope per personal-use single-tenant model. |
| T-03-05-08 | T | mitigate | CLOSED | Grep confirms `"Uniqueness rider (CR-01 closure):"` appears at `lib/amortize.py:57`. |

## Threat verification — Plan 03-06 (envelope shape contract)

| Threat ID | Cat | Disposition | Status | Evidence |
|-----------|-----|-------------|--------|----------|
| T-03-06-01 | T | mitigate | CLOSED | Test `tests/test_amortize.py:996-1067` `test_cli_error_envelope_uniformity` asserts both float-gate path and Pydantic ValidationError path produce identical 6-key sets `{type, loc, msg, input, url, ctx}`. |
| T-03-06-02 | T | mitigate | CLOSED | `scripts/amortize.py:194-207` lazy-imports `pydantic.VERSION` and constructs `f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type"` at runtime. Test asserts URL prefix+suffix, version segment floats. |
| T-03-06-03 | T | mitigate | CLOSED | `scripts/amortize.py:108-109` uses `str(Decimal)` to populate `input` key (round-trips losslessly via `Decimal(str(...))`). Test asserts `err["input"] == "400000.00"`. |
| T-03-06-04 | I | accept | CLOSED | Personal-use scope; matches Pydantic native convention. |
| T-03-06-05 | R | mitigate | CLOSED | Grep confirms `"Envelope Shape Contract (WR-02 closure)"` at `scripts/amortize.py:36`. Uniformity test pins the contract. |
| T-03-06-06 | D | accept | CLOSED | O(n) JSON tree walk; bounded by Pydantic model shape. |
| T-03-06-07 | E | mitigate | CLOSED | `pydantic.VERSION` lazy-import is INSIDE the `if float_hit is not None:` block (`scripts/amortize.py:194`), AFTER `argparse.parse_args()` (line 144). Structural verifier (`test_cli_help_does_not_import_lib_amortize`) confirms pydantic is not loaded on the --help path. |
| T-03-06-08 | T | accept | CLOSED | `input` field is JSON-encoded into stderr; downstream consumers (Phase 9 db-write.mjs DuckDB parameter binding, Phase 10 SKILL.md narration) never shell-evaluate the value. |

## Unregistered threat flags

None. All six SUMMARY.md files declare "no new threats discovered during execution":

- `03-01-SUMMARY.md`: "None — plan stayed inside the threat model documented in the PLAN frontmatter (T-03-01-01..04 all addressed)"
- `03-02-SUMMARY.md`: "None. Plan stayed inside the threat model documented in PLAN.md frontmatter (T-03-02-01..09 all addressed)"
- `03-03-SUMMARY.md`: "None. Plan stayed inside the threat model documented in PLAN.md frontmatter (T-03-03-01..09 all addressed)"
- `03-04-SUMMARY.md`: "Threat Surface — No new production-code surface introduced this plan ... STRIDE register from the plan's `<threat_model>` is fully satisfied"
- `03-05-SUMMARY.md`: "No new STRIDE-relevant surface introduced beyond what the plan's `<threat_model>` already documents"
- `03-06-SUMMARY.md`: "No new STRIDE-relevant surface introduced beyond what the plan's `<threat_model>` already documents"

## Findings & follow-ups

**WARNING — non-blocking — T-03-02-08 mitigation substitution**

The plan named a specific test `test_npf_returns_decimal_when_fed_decimal` (originally scoped under Plan 03-04). That named canary test does NOT exist in `tests/test_amortize.py`. However, the threat (numpy-financial regressing from end-to-end Decimal back to float) is functionally covered by:

1. The 4 parametrized golden-oracle tests (`test_fixed_rate_oracle`) using exact `Decimal` equality on `schedule.monthly_pi`. A float-returning regression in `npf.pmt` would fail one of these on the next CI run.
2. The structural test `test_amortize_module_uses_numpy_financial` asserts `import numpy_financial as npf` and `npf.pmt(` are present.
3. Engine has zero `Decimal(str(...))` reconstructions (so any float leak would propagate, not be silently masked).

**Recommendation (non-blocking):** Add an explicit one-line canary test to `tests/test_amortize.py`:

```python
def test_npf_returns_decimal_when_fed_decimal() -> None:
    import numpy_financial as npf
    from decimal import Decimal
    out = npf.pmt(Decimal("0.005417"), 360, Decimal("400000"))
    assert isinstance(out, Decimal), f"npf.pmt regressed to {type(out)}"
```

Cost: ~5 lines. Benefit: explicit regression flag matches the plan's exact wording and produces a clearer failure message than oracle drift would. Logged here so a follow-up phase (Plan 04-01 or a Phase 3 cleanup PR) can add it without re-running the full audit.

## Accepted risks log (personal-use scope)

Rationale source: CLAUDE.md ("mortgage-ops — Personal-use mortgage analysis tool for the Pachulski household"), 03-CONTEXT.md (single-tenant, single-user CLI), 03-PATTERNS.md (no auth, no network, no multi-user). All `accept` dispositions below are consistent with that scope.

| Threat ID | Risk |
|-----------|------|
| T-03-01-02 | Pydantic ValidationError messages may include rejected raw input values. |
| T-03-01-03 | Empty-payments Schedule construction skips D-15 validator (internal scaffold convenience; unreachable from Phase 3 boundary). |
| T-03-02-04 | AmortizeRequest validator messages may include offending values. |
| T-03-02-05 | term_months capped at 600 (50 years); pathological inputs beyond cap rejected at model layer. |
| T-03-02-06 | extra_principal list size unbounded; performance impact only. |
| T-03-02-09 | Schedule.total_interest leaks via JSON output (deliberate contract). |
| T-03-03-04 | --input file path is taken verbatim; CLI runs as the user invoking it. |
| T-03-03-05 | ValidationError messages may surface raw input. |
| T-03-03-07 | extra_principal list size unbounded at JSON-input layer. |
| T-03-03-08 | scripts/amortize.py reads any file the invoking user can read. |
| T-03-04-05 | Test stderr captured by subprocess fixtures; not externally visible. |
| T-03-04-06 | Test runtime budget; no DoS. |
| T-03-05-04 | Validator error messages reveal only the user-submitted period number. |
| T-03-05-06 | Validator runtime O(n) over ~720 entries. |
| T-03-05-07 | _resolve_extra is module-private; direct external call out-of-scope. |
| T-03-06-04 | Envelope `input` key reveals user-submitted JSON value. |
| T-03-06-06 | Walker performance O(n) over JSON tree. |
| T-03-06-08 | `input` value is JSON-encoded, never shell-evaluated downstream. |

## Sign-off

- **block_on=high gate:** clear (no HIGH threats are open)
- **Phase 3 may proceed downstream.** Recommendation in "Findings & follow-ups" is non-blocking.
- **Audit verdict:** SECURED (with one informational warning).
