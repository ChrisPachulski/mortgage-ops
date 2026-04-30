---
phase: 03-core-amortization
verified: 2026-04-29T22:30:00Z
status: passed
score: 5/5 success criteria verified
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5 success criteria verified
  gaps_closed:
    - "CR-01: duplicate (period, recurring=True) ExtraPrincipalEntry rows produced order-dependent schedules"
    - "WR-02: scripts/amortize.py emitted two distinct error envelope shapes (3-key float-gate vs 6-key Pydantic)"
  gaps_remaining: []
  regressions: []
gaps_closure_evidence:
  - gap: CR-01
    closure_plan: "03-05"
    commits:
      - "973456c — test(03-05): add CR-01 regression tests for duplicate recurring periods (RED)"
      - "f8c1ddb — fix(03-05): reject duplicate (period, recurring=True) extra_principal entries (CR-01)"
    code_anchor: "lib/amortize.py:196-223 (AmortizeRequest._no_duplicate_recurring_periods)"
    docstring_anchor: "lib/amortize.py:50-63 (D-05 LOCKED DECISION block, 'Uniqueness rider (CR-01 closure)' paragraph)"
    tests_added: 6
    behavioral_proof: "Both [100,200] and [200,100] orderings now raise pydantic.ValidationError with identical message; CLI subprocess on CR-01 reproducer JSON exits 2 with structured 6-key envelope on stderr containing 'duplicate recurring'"
  - gap: WR-02
    closure_plan: "03-06"
    commits:
      - "450d8d9 — test(03-06): tighten float-gate envelope test + add uniformity contract (RED)"
      - "1bb2cc6 — fix(03-06): unify CLI error envelope to 6-key Pydantic shape (WR-02)"
    code_anchor: "scripts/amortize.py:72-122 (_find_json_float_loc tuple shape) + scripts/amortize.py:177-215 (6-key envelope construction)"
    docstring_anchor: "scripts/amortize.py:36-60 (Envelope Shape Contract paragraph naming Phase 9 / Phase 10 consumers)"
    tests_added: 1
    tests_tightened: 1
    behavioral_proof: "Float-gate keyset and Pydantic-native ValidationError keyset are both exactly {ctx, input, loc, msg, type, url}; D-18 fast --help contract preserved (lib.amortize and numpy_financial NOT in sys.modules after --help)"
---

# Phase 3: Core Amortization Verification Report (Re-Verification)

**Phase Goal:** Build the foundational amortization engine wrapping numpy-financial, supporting fixed-rate, biweekly, and arbitrary extra-principal schedules with no float drift.

**Verified:** 2026-04-29T22:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure of CR-01 (plan 03-05) and WR-02 (plan 03-06)

## Re-Verification Summary

The previous verification (2026-04-29T20:00:00Z) marked status `human_needed` with two items pending acceptance:
1. **CR-01** — duplicate `(period, recurring=True)` `ExtraPrincipalEntry` rows produced non-deterministic schedules depending on caller-supplied list order (UAT decision: option (a) — reject at AmortizeRequest boundary).
2. **WR-02** — `scripts/amortize.py` emitted two error envelope shapes (3-key float-gate vs 6-key Pydantic) (UAT decision: option (a) — unify to 6-key Pydantic shape).

Both gaps are now closed by gap-closure plans 03-05 and 03-06. This re-verification confirms the closures behaviorally in the codebase (not just by SUMMARY.md narrative) and verifies zero regressions to the prior 5/5 ROADMAP Success Criteria pass.

| Item | Previous Status | Current Status | Code Evidence |
| --- | --- | --- | --- |
| CR-01 closure | human_needed | VERIFIED | `lib/amortize.py:196-223` validator + 6 new tests + CLI end-to-end reproducer |
| WR-02 closure | human_needed | VERIFIED | `scripts/amortize.py:177-215` 6-key envelope + tightened test + new uniformity test |
| SC1: $400k/30yr/6.5% → 2528.27, balance 0.00 | VERIFIED | VERIFIED (no regression) | `test_fixed_rate_oracle[computed_400k_30yr]` PASS |
| SC2: 4 golden oracles exact-Decimal equality | VERIFIED | VERIFIED (no regression) | All 4 parametrized cases PASS |
| SC3: Biweekly 26 payments/yr, sum-equals-original | VERIFIED | VERIFIED (no regression) | `test_biweekly_*_oracle` PASS |
| SC4: Extra-principal scenarios → 0.00 final | VERIFIED | VERIFIED (no regression) | All 4 extra-principal tests PASS |
| SC5: --help no heavy imports, no-input clear error | VERIFIED | VERIFIED (no regression) | D-18 structural verifier exits 0 with `D-18 OK` |

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| SC1 | `scripts/amortize.py --input <400k/30yr/6.5% loan>` returns JSON with `monthly_pi == "2528.27"` and final-row `balance == "0.00"` | VERIFIED | `test_fixed_rate_oracle[computed_400k_30yr]` PASS; `test_final_payment_cleans_to_zero_fixed[computed_400k_30yr]` PASS |
| SC2 | All 4 golden-fixture tests (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr) pass with exact Decimal equality (no `assertAlmostEqual`) | VERIFIED | `test_fixed_rate_oracle[wikipedia_200k_30yr,cfpb_le_162k_30yr,computed_400k_30yr,computed_200k_15yr]` 4/4 PASS; pinned values 1264.14 / 761.78 / 2528.27 / 1797.66 |
| SC3 | Biweekly schedule produces 26 payments/year via `relativedelta(weeks=2)`; sum of all principal payments equals original principal exactly | VERIFIED | `test_biweekly_true_oracle` + `test_biweekly_half_monthly_oracle` PASS; `lib/amortize.py:449` uses `relativedelta(weeks=2 * period)`; `assert_schedule_invariants` enforces sum-equals-original |
| SC4 | Extra-principal scenarios (single, recurring, per-period) shorten schedule and final balance reaches `Decimal("0.00")` | VERIFIED | `test_extra_oneshot_period_60`, `test_extra_recurring_200_from_period_1`, `test_extra_step_up_200_to_300_at_period_13`, `test_extra_caps_at_remaining_balance_silently` all PASS. CR-01 ambiguity case is now rejected at the boundary (`AmortizeRequest._no_duplicate_recurring_periods`); legitimate D-05 step-up (distinct periods) still validates per `test_amortize_request_accepts_d05_step_up_with_distinct_periods` |
| SC5 | `scripts/amortize.py --help` prints usage without importing heavy deps; running with no input prints clear schema-error message | VERIFIED | `test_cli_help_does_not_import_lib_amortize` PASS; D-18 structural verifier exits 0 with stdout `D-18 OK` (lib.amortize and numpy_financial NOT in sys.modules after --help, even with new `from pydantic import VERSION` lazy-import inside main()); no-input run exits 2 with argparse usage |

**Score:** 5/5 ROADMAP Success Criteria verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `lib/models.py` | Phase-1 models extended with D-10/D-14/D-15: `Payment.cumulative_interest`, `Payment.cumulative_principal`, `Schedule.final_payment_adjusted`, `@model_validator` enforcing `total_interest == payments[-1].cumulative_interest` | VERIFIED (no change since prior verification) | All 4 fields/validator present |
| `lib/amortize.py` | Engine wrapping numpy-financial with `ExtraPrincipalEntry`, `AmortizeRequest` (now with TWO `@model_validator(mode="after")` methods: D-02 + D-05 uniqueness rider), `_resolve_extra`, `_build_fixed_monthly`, `_build_biweekly_true`, `_build_biweekly_half_monthly`, `build_schedule` | VERIFIED | 498 lines (was 461 pre-03-05; +37 for new validator). Two `@model_validator(mode="after")` methods present (`_biweekly_mode_consistency` D-02 + `_no_duplicate_recurring_periods` D-05 rider). D-05 LOCKED DECISION docstring extended with "Uniqueness rider (CR-01 closure)" paragraph at lines 57-63. `_resolve_extra` UNCHANGED (validator catches ambiguous input class before _resolve_extra is invoked) |
| `scripts/amortize.py` | argparse CLI + lazy-import + `AmortizeRequest.model_validate_json` + structured JSON error envelopes (now uniform 6-key Pydantic v2 e.json() shape across all ValidationError-class surfaces) | VERIFIED | 239 lines (was 187 pre-03-06; +52 for envelope refactor + Envelope Shape Contract docstring). `_find_json_float_loc` returns `tuple[list[str | int], str] | None`. Float-gate envelope construction populates all 6 Pydantic v2 keys. Module docstring includes "Envelope Shape Contract (WR-02 closure)" paragraph naming Phase 9 / Phase 10 consumers (lines 36-60). `from pydantic import VERSION as _pydantic_version` is lazy-imported INSIDE `main()` after `parser.parse_args()` — D-18 fast --help preserved |
| `tests/test_amortize.py` | ~22+ tests covering AMRT-01..08 + D-02 + D-05 uniqueness rider + D-15 + month-end + CLI + WR-02 envelope-shape uniformity; `assert_schedule_invariants` helper invoked once per schedule-producing test | VERIFIED | 42 tests (was 35 pre-03-05; +6 from 03-05 + 1 from 03-06 — `test_cli_rejects_float_principal` was tightened in place, not added). All 42 PASS in 1.60s. New tests in file: `test_amortize_request_rejects_duplicate_recurring_periods` (line 250), `test_amortize_request_rejects_duplicate_recurring_periods_reversed` (line 282), `test_amortize_request_rejects_three_way_duplicate_recurring` (line 312), `test_amortize_request_accepts_d05_step_up_with_distinct_periods` (line 340), `test_amortize_request_accepts_duplicate_one_shots_at_same_period` (line 369), `test_amortize_request_accepts_recurring_plus_oneshot_at_same_period` (line 400), `test_cli_error_envelope_uniformity` (line 996) |
| `tests/conftest.py` | `amortize_fixture` factory (filename-stem loader) added; `golden_fixture` preserved | VERIFIED (no change since prior verification) | Both factories present |
| `tests/fixtures/amortize/*.json` | 7 JSON fixtures with engine-emitted values | VERIFIED (no change since prior verification) | All 7 files exist |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `lib/amortize.py:build_schedule` | `numpy_financial.pmt` | `-npf.pmt(period_rate, n, principal)` | WIRED | Two call sites in `_build_fixed_monthly` and `_build_biweekly_true` |
| `lib/amortize.py:build_schedule` | `lib.money.quantize_cents` | end-of-period quantization on every Money assignment | WIRED | 11 `quantize_cents(` calls; no compound mid-expression pattern |
| `lib/amortize.py:build_schedule` | `lib.models.Schedule` | `Schedule(loan=..., monthly_pi=..., total_interest=..., final_payment_adjusted=..., payments=[...])` | WIRED | Both build helpers populate all 5 fields |
| `lib/amortize.py:AmortizeRequest._no_duplicate_recurring_periods` | scripts/amortize.py D-19 error envelope | Pydantic wraps `ValueError` into `ValidationError` -> `e.json()` pass-through at scripts/amortize.py:222-225 | WIRED | CLI subprocess on CR-01 reproducer JSON exits 2 with structured Pydantic envelope on stderr containing `duplicate recurring extra_principal at period 1` |
| `scripts/amortize.py:_find_json_float_loc` | `scripts/amortize.py:main` float-gate envelope construction | returns `tuple[list[str|int], str]` — caller unpacks both `(float_loc, float_input)` at line 189 | WIRED | Float-gate envelope's `input` key populates with `float_input == "400000.00"` (Decimal-string from `str(parsed_decimal)`) |
| `scripts/amortize.py` float-gate envelope | Pydantic v2 e.json() ValidationError shape | `{type: "decimal_type", loc, msg, input, url, ctx}` mirroring `https://errors.pydantic.dev/{MAJOR.MINOR}/v/decimal_type` | WIRED | Manual subprocess invocation produces exact 6-key shape; cross-shape uniformity confirmed empirically (float_keys == d02_keys == {ctx, input, loc, msg, type, url}) |
| `scripts/amortize.py:main` | `lib.amortize.AmortizeRequest` | lazy-import after `argparse.parse_args()` | WIRED | `from lib.amortize import AmortizeRequest, build_schedule` at line 159 INSIDE `def main()` AFTER `args = parser.parse_args()` (line 144). D-18 contract verified by structural verifier |
| `scripts/amortize.py:main` | `lib.amortize.build_schedule` | `build_schedule(request.loan, frequency=..., biweekly_mode=..., extra_principal=...)` | WIRED | Lines 227-232. Passes through validated `request` fields verbatim |
| `scripts/amortize.py:main` | `Schedule.model_dump_json` | `print(schedule.model_dump_json(indent=2))` | WIRED | Line 233 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `lib/amortize.py::build_schedule` | `payments: list[Payment]` | per-period iteration computing interest, principal_paid, extra, balance from `npf.pmt` + scalar Decimal arithmetic | YES — verified by all 4 golden oracles producing exact pinned values + biweekly producing 628 periods + sum(principal+extra) == original | FLOWING |
| `scripts/amortize.py::main` | `schedule: Schedule` | `build_schedule(...)` after Pydantic validation | YES — CLI smoke run produces actual JSON output with monthly_pi=2528.27 + 360 payments + final balance=0.00 | FLOWING |
| `scripts/amortize.py::main` (float-gate envelope) | `envelope: list[dict]` | constructed from `_find_json_float_loc(raw)` tuple unpack + runtime-derived `pydantic.VERSION` | YES — manual run on `principal: 400000.00` (number) produces `{type: "decimal_type", loc: ["loan", "principal"], msg: "Input should be a valid decimal — JSON string required for money/rate fields per D-19 (JSON floats are rejected at the boundary)", input: "400000.00", url: "https://errors.pydantic.dev/2.13/v/decimal_type", ctx: {class: "Decimal", field_path: "loan.principal"}}` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| 4 golden oracles produce pinned monthly_pi exactly (no SC1-2 regression) | `uv run pytest tests/test_amortize.py -k test_fixed_rate_oracle` | 4 passed | PASS |
| Biweekly + extra-principal + month-end edge tests still green | `uv run pytest tests/test_amortize.py -k "biweekly or extra or month_end"` | all PASS | PASS |
| 6 new CR-01 closure tests all pass | `uv run pytest tests/test_amortize.py -k "rejects_duplicate or accepts_d05_step_up or accepts_duplicate_one_shots or accepts_recurring_plus_oneshot or rejects_three_way" -v` | 6 passed | PASS |
| New WR-02 uniformity test passes | `uv run pytest tests/test_amortize.py::test_cli_error_envelope_uniformity -v` | 1 passed | PASS |
| Tightened float-gate test passes (6-key keyset assertion) | `uv run pytest tests/test_amortize.py::test_cli_rejects_float_principal -v` | 1 passed | PASS |
| Phase 3 test file (full count) | `uv run pytest tests/test_amortize.py` | 42 passed in 1.60s | PASS |
| Full project pytest suite | `uv run pytest` | 301 passed, 4 warnings (pre-existing StaleReferenceWarning, unrelated) in 10.14s | PASS |
| `mypy --strict` clean | `uv run mypy --strict .` | Success: no issues found in 50 source files | PASS |
| `ruff check` clean | `uv run ruff check .` | All checks passed! | PASS |
| `ruff format --check` clean | `uv run ruff format --check .` | 50 files already formatted | PASS |
| **CR-01 reproducer end-to-end (Python API):** `[100,200]` order rejects | `uv run python -c "AmortizeRequest(...[100,200]...)"` | `pydantic.ValidationError`: "duplicate recurring extra_principal at period 1; ... (D-05); ..." | PASS |
| **CR-01 reproducer end-to-end (Python API):** `[200,100]` order rejects identically | `uv run python -c "AmortizeRequest(...[200,100]...)"` | `pydantic.ValidationError`: SAME message (no order-dependence; symmetry restored) | PASS |
| **CR-01 reproducer end-to-end (CLI):** ambiguous JSON exits 2 with structured envelope | `uv run python scripts/amortize.py --input /tmp/cr01_cli.json` (where JSON has duplicate recurring at period=1) | exit=2, stderr is parseable JSON list, first error has `msg` containing `duplicate recurring extra_principal at period 1` and 6-key shape | PASS |
| **WR-02 cross-shape uniformity (CLI):** float-gate keyset == D-02 keyset | manual subprocess + json.loads on both stderrs | Both first-error keysets equal `{'ctx','input','loc','msg','type','url'}` (exactly 6) | PASS |
| **WR-02 float-gate envelope shape (CLI):** all 6 Pydantic-shape keys populated correctly | manual subprocess on float-in-principal JSON | `type: "decimal_type"`, `loc: ["loan","principal"]`, `msg: "Input should be a valid decimal..."`, `input: "400000.00"`, `url: "https://errors.pydantic.dev/2.13/v/decimal_type"`, `ctx: {"class":"Decimal","field_path":"loan.principal"}` | PASS |
| D-18 fast --help preserved (regression check after WR-02) | importlib.util harness + sys.argv=['--help'] + assert lib.amortize and numpy_financial NOT in sys.modules | Exit 0 with stdout `D-18 OK` — the new `from pydantic import VERSION` lazy-import inside main() does NOT pull heavy deps onto --help path | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| AMRT-01 | 03-01, 03-02, 03-04 | `lib/amortize.py` wraps numpy-financial PMT/IPMT/PPMT (does NOT reimplement) | SATISFIED | `import numpy_financial as npf` + `npf.pmt(` present; no hand-rolled PMT; `test_amortize_module_uses_numpy_financial` PASS |
| AMRT-02 | 03-02, 03-04 | Schedule generator handles fixed-rate loans (any term, any rate) | SATISFIED | `_build_fixed_monthly` produces correct schedules for all 4 oracles spanning 162k-400k principal, 3.875%-7% rate, 180-360 month term |
| AMRT-03 | 03-02, 03-04 | Schedule generator handles biweekly payment frequency (`relativedelta(weeks=2)`) | SATISFIED | `_build_biweekly_true` uses `relativedelta(weeks=2 * period)`; biweekly-true 200k/6.5/30 → 628 periods; tests `test_biweekly_true_oracle` + `test_biweekly_half_monthly_oracle` + `test_biweekly_mode_defaults_to_true_when_omitted` PASS |
| AMRT-04 | 03-02, 03-04, 03-05 | Schedule generator handles arbitrary extra principal payments (single, recurring, or per-period) WITH determinism — semantically equivalent inputs produce semantically equivalent outputs | SATISFIED (CR-01 closure) | One-shot, recurring, step-up, cap-at-balance scenarios all PASS. `AmortizeRequest._no_duplicate_recurring_periods` validator (lib/amortize.py:196-223) rejects the order-of-list-ambiguous input class at the boundary; 6 new tests pin the contract; D-05 docstring extended with "Uniqueness rider (CR-01 closure)" paragraph; CLI surfaces rejection through `e.json()` pass-through as structured 6-key envelope |
| AMRT-05 | 03-02, 03-04 | Final payment cleanup ensures balance reaches exactly $0.00 (no float drift) | SATISFIED | `test_final_payment_cleans_to_zero_fixed[4 oracles]` + `test_final_payment_cleans_to_zero_biweekly[true,half-monthly]` all PASS |
| AMRT-06 | 03-03, 03-04, 03-06 | `scripts/amortize.py` provides JSON-in / JSON-out CLI for skill use WITH uniform error envelope contract for downstream Phase 9/10 consumers | SATISFIED (WR-02 closure) | 239-line CLI; argparse `--input <path>`; lazy-import per D-18; AmortizeRequest.model_validate_json boundary; **all ValidationError-class surfaces uniformly emit 6-key Pydantic v2 e.json() envelope**: `{type, loc, msg, input, url, ctx}` (verified empirically: float-gate keyset == D-02 keyset == 6 expected keys). Module docstring carries "Envelope Shape Contract (WR-02 closure)" paragraph naming Phase 9 (Node orchestration / DuckDB persistence) and Phase 10 (Claude SKILL.md narration) as consumers. File-not-found and OSError envelopes left on legacy `{error: ...}` shape per explicit out-of-scope clause (not Pydantic ValidationError surfaces) |
| AMRT-07 | 03-04 | Tests assert `sum(principal_payments) == original_principal` exactly | SATISFIED | `assert_schedule_invariants` defined and invoked across schedule-producing tests; uses `Decimal == Decimal` exact equality. No `assertAlmostEqual` anywhere |
| AMRT-08 | 03-04 | Tests pass against all 4 golden fixtures (Wikipedia, CFPB LE, computed $400k, computed $200k/15yr) | SATISFIED | `test_fixed_rate_oracle[wikipedia_200k_30yr|cfpb_le_162k_30yr|computed_400k_30yr|computed_200k_15yr]` 4/4 PASS with exact Decimal equality |

All 8 declared requirement IDs (AMRT-01..AMRT-08) are SATISFIED. REQUIREMENTS.md `Phase 3: Core Amortization | AMRT-01..08 | 8` mapping matches plan frontmatter; no orphans. AMRT-04 and AMRT-06 specifically benefit from the gap-closure plans (03-05 / 03-06).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `lib/amortize.py` | 291 | `assert biweekly_mode == "half-monthly"  # mypy narrowing` (load-bearing assert that elides under `python -O`) | Info | Currently no functional impact — `_build_biweekly_half_monthly` ignores `biweekly_mode`. Future refactor risk only (WR-07 in 03-REVIEW). Not blocking the phase goal |
| `lib/amortize.py` | 284 vs `AmortizeRequest._biweekly_mode_consistency` | Two exception types (`ValueError` vs `pydantic.ValidationError`) for the same logical D-02 violation | Info | Library callers and CLI callers see different error types for one logical contract. Not blocking; WR-08 in 03-REVIEW |
| `lib/models.py` | (D-15 validator) | Validator early-returns on `payments=[]` without checking `total_interest` (WR-01 in 03-REVIEW) | Info | Engine never produces empty payments; consumer-side stub Schedule construction can silently violate D-15 invariant. Not blocking phase goal |
| `tests/test_amortize.py` | (entire) | No test for biweekly+extras (D-06 contract: WR-05); no test for one-shot+recurring stacking on same period (WR-04 — addressed by 03-05's `test_amortize_request_accepts_recurring_plus_oneshot_at_same_period` for the validator scope, but not for engine schedule-output verification); no test for rate=0 / term=1 edge cases (WR-06) | Info | Coverage gaps surfaced by 03-REVIEW. The phase goal does not enumerate these scenarios; current tests cover all stated SC1-5 success criteria |

**Note:** The previous CR-01 anti-pattern entry (`lib/amortize.py` line 203-207, `_resolve_extra` order-dependent behavior) and the previous WR-02 entry (`scripts/amortize.py` two error envelope shapes) are now CLOSED — they have been removed from the post-closure anti-pattern list because the 03-05 validator and the 03-06 envelope refactor eliminated them.

### Gaps Summary

**No gaps remain.** Both items previously surfaced as `human_needed` are now closed in the codebase:

1. **CR-01 (closed by plan 03-05):** `AmortizeRequest._no_duplicate_recurring_periods` validator now rejects duplicate `(period, recurring=True)` `ExtraPrincipalEntry` rows at the request boundary via `pydantic.ValidationError`. The CR-01 reproducer in both `[100, 200]` and `[200, 100]` orderings now produces an identical rejection (no order-dependence). The fix surfaces correctly through `scripts/amortize.py`'s D-19 boundary as a structured Pydantic error envelope on stderr. The D-05 LOCKED DECISION docstring is extended with the "Uniqueness rider (CR-01 closure)" paragraph anchoring the contract. 6 new regression tests pin the determinism contract. `_resolve_extra` is unchanged — the validator catches the ambiguous input class before the engine's resolve-helper is ever invoked, so the 35-case existing test surface is preserved byte-identically.

2. **WR-02 (closed by plan 03-06):** `scripts/amortize.py` now emits a uniform 6-key Pydantic v2 `e.json()` envelope (`{type, loc, msg, input, url, ctx}`) across BOTH the pre-validation float-gate AND every native Pydantic ValidationError surface. The float-gate envelope's `input` is the offending JSON value as a Decimal-string (`"400000.00"`); `url` references the canonical Pydantic decimal_type docs URL with the version segment computed at runtime from `pydantic.VERSION` (so future Pydantic minor upgrades auto-align); `ctx` contains `class:"Decimal"` (mirrors Pydantic native convention) plus a project-specific `field_path` (dotted path for downstream narration). The module docstring carries an explicit "Envelope Shape Contract" paragraph naming Phase 9 (Node orchestration / DuckDB persistence) and Phase 10 (Claude SKILL.md narration) as the downstream consumers — preventing silent drift in future maintenance. File-not-found and OSError surfaces remain on the legacy `{error: ...}` shape (explicit out-of-scope per the gap entry — these are not Pydantic ValidationError surfaces). The new `test_cli_error_envelope_uniformity` test pins the cross-shape uniformity contract; `test_cli_rejects_float_principal` was tightened in place to assert the 6-key keyset and per-key value contracts. D-18 fast --help is preserved (the new `from pydantic import VERSION` is lazy-imported inside `main()`).

The phase goal — "Build the foundational amortization engine wrapping numpy-financial, supporting fixed-rate, biweekly, and arbitrary extra-principal schedules with no float drift" — is fully achieved with zero gaps remaining and zero regressions to the prior 5/5 ROADMAP Success Criteria pass. Phase 3 is ready to close; downstream Phases 4-12 can now build on a fully-determinate engine and a uniformly-shaped CLI error contract.

### Re-Verification Closure Evidence

**Commits verified to exist in `git log`:**
- `973456c` test(03-05): add CR-01 regression tests for duplicate recurring periods (RED)
- `f8c1ddb` fix(03-05): reject duplicate (period, recurring=True) extra_principal entries (CR-01)
- `450d8d9` test(03-06): tighten float-gate envelope test + add uniformity contract (RED)
- `1bb2cc6` fix(03-06): unify CLI error envelope to 6-key Pydantic shape (WR-02)

All four commits contain zero `Co-Authored-By` / Claude / Anthropic attribution per CLAUDE.md global rule.

**Behavioral end-to-end verification performed during this re-verification (not just SUMMARY-trusted):**
- Direct `AmortizeRequest` construction with both CR-01 orderings → both raise `pydantic.ValidationError` with identical message (verified empirically via `uv run python -c "..."`)
- CLI subprocess invocation on CR-01 reproducer JSON → exit 2 + stderr is parseable JSON list with 6-key envelope containing `duplicate recurring extra_principal at period 1`
- CLI subprocess invocation on float-gate reproducer JSON → exit 2 + stderr is parseable JSON list with exact 6-key shape `{ctx, input, loc, msg, type, url}` and correct values for every key
- Cross-shape uniformity programmatically verified: `set(float_err[0].keys()) == set(d02_err[0].keys()) == {"type","loc","msg","input","url","ctx"}` returns True
- D-18 structural verifier (regression check after WR-02): `lib.amortize` and `numpy_financial` NOT in `sys.modules` after `--help` execution, despite the new `from pydantic import VERSION` import inside `main()`
- Full project test suite: 301 passed, 4 warnings (pre-existing StaleReferenceWarning, unrelated to phase 3)
- mypy --strict: no issues found in 50 source files
- ruff check + ruff format --check: all clean

---

_Verified: 2026-04-29T22:30:00Z_
_Verifier: Claude (gsd-verifier, re-verification mode)_
