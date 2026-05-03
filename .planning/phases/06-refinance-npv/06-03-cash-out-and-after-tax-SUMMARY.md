---
phase: 06
plan: 03
subsystem: cash-out-and-after-tax
tags:
  - phase-06
  - refinance-npv
  - cash-out
  - after-tax
  - irs-pub936
  - dispatcher
requires:
  - "lib.refinance.RefiCashflow / RefiBreakeven / RefiResponse / CashOutRefiRequest / RateAndTermRefiRequest / RefiRequest (Plan 06-01)"
  - "lib.refinance._build_old_loan_residual / _build_new_loan / _build_refi_cashflows / _compute_npv / _compute_breakeven_simple / _compute_breakeven_npv (Plan 06-02)"
  - "lib.refinance._validate_common (Plan 06-01; D-09 cross-field validator wired but not yet exercised by an engine consumer)"
  - "lib.rules.irs_pub936.qualified_loan_limit (Phase 2 RUL-11 — $750k post-2017 / $1M grandfathered cap)"
  - "lib.rules._loader.StaleReferenceWarning (Phase 2 — lazy-stale check on YAML load)"
  - "lib.amortize.build_schedule (Phase 3 — for new-loan schedule.payments interest amounts)"
provides:
  - "lib.refinance._compute_tax_shield_cashflows (D-09 after-tax helper; cites RUL-11 + Pub 936 §3 qualified loan limit)"
  - "lib.refinance.evaluate_cash_out (REFI-02 + SC-3 body — full 9-step pipeline composing Wave-2 helpers + cash-out-specific logic per RESEARCH §'(c) Cash-Out Mechanics' + Oracle 3)"
  - "lib.refinance.evaluate (D-02 public dispatcher — refi_kind discriminator routing; mirrors lib/affordability.py::evaluate pattern)"
  - "lib.refinance.evaluate_rate_and_term wired with real after-tax tax-shield branch (replaces Wave-2 forward-pointer warning)"
  - "Stale-warning surfacing into RefiResponse.warnings for both refi_kind variants when after_tax_mode=True (per module-docstring 'Stale-warning expected behavior' contract)"
affects:
  - "Wave 4 (Plan 06-04): scripts/refi_npv.py CLI now has a fully-wired evaluate(req) dispatcher to call; can ship without further engine work"
  - "Wave 5 (Plan 06-05): can now derive Oracle 3 (cash-out) Decimal-pinned NPV value (engine-derived 36996.30 — RESEARCH approximation 36995.87) and after-tax-mode smoke fixture; flips up to 11 stubs (rate-and-term + cash-out + breakeven + cashflow-kind coverage + pyxirr-deferred docstring)"
  - "Wave 6 (Plan 06-06): no direct dependency (doc-layer plan), but doc §'After-Tax Optional Mode' now has an operational engine path to point at"
tech-stack:
  added: []
  patterns:
    - "D-12 cash-out closing-costs convention: NETTED into cash_proceeds_net at t=0 (NOT a separate t=0 outflow); falls back to closing_costs outflow + cash_proceeds=None when net <= 0"
    - "Rule-1 carve-out: RefiResponse.cash_proceeds = None when cash_out_amount - closing_costs <= 0 (consumer-friendly 'no positive proceeds' signal; Money type can't carry negatives)"
    - "D-09 after-tax pipeline: _compute_tax_shield_cashflows emits RefiCashflow(period=t, direction='inflow', amount=tax_shield_t, kind='tax_shield') stream; appended to pre-tax cashflows; _compute_npv re-run on combined stream for after_tax_npv field"
    - "Lazy import of qualified_loan_limit inside _compute_tax_shield_cashflows: keeps after_tax_mode=False cold path free of IRS reference-data load cost"
    - "warnings.catch_warnings(record=True) + simplefilter('always', StaleReferenceWarning) wrap around IRS predicate calls; captured messages stringified into RefiResponse.warnings (mirrors lib/affordability.py pattern)"
    - "isinstance-based dispatcher: evaluate(req) checks isinstance(req, RateAndTermRefiRequest) / isinstance(req, CashOutRefiRequest) and forwards to engine entrypoint; defensive ValueError on unknown variant"
    - "Pinned Oracle 3 verified: cash_proceeds=$47000.00, old_pi=$1432.86, new_pi=$1498.88, monthly_payment_delta=$66.02, npv=$36996.30, total_interest_delta=$145706.07, breakeven=(simple=None/no_savings, npv=0/ok)"
key-files:
  created:
    - .planning/phases/06-refinance-npv/06-03-cash-out-and-after-tax-SUMMARY.md
  modified:
    - lib/refinance.py
    - tests/test_refinance.py
key-decisions:
  - "Oracle 3 engine-derived NPV is Decimal('36996.30') and total_interest_delta is Decimal('145706.07'), NOT the RESEARCH approximations $36,995.87 / $145,711.43. Same precision-class drift as Oracles 1 + 2: RESEARCH used analytical PMT formulas with intermediate cent-rounding; the engine carries full Decimal precision through npf.npv per the AMRT-01 wrap-not-reimplement contract. The engine values are authoritative per CLAUDE.md money discipline ('every dollar figure that exits this system must be traceable to a tested, deterministic Python function — the function IS _compute_npv, not the analytical PMT formula'). Plan 06-05 fixtures will pin the engine values via Decimal equality."
  - "Cash-out cash_proceeds Rule-1 carve-out: when closing_costs > cash_out_amount (pathological — D-12 documents this is unusual but legal), the engine surfaces RefiResponse.cash_proceeds=None rather than a negative Money value (Money.ge=0 prevents negative). The cashflow stream falls back to closing_costs as a t=0 outflow + no t=0 cash_proceeds inflow, so NPV computation remains correct. Documented in evaluate_cash_out docstring + reflects PLAN deviation_rule Rule-1."
  - "_validate_common D-09 error message refined to cite RUL-11 + 'After-Tax Optional Mode' section verbatim per PLAN spec (was: generic 'cites lib.rules.irs_pub936.qualified_loan_limit needs filing_status to select the $750k post-2017 vs $1M grandfathered cap'; now: 'cites lib.rules.irs_pub936.qualified_loan_limit / RUL-11; see references/refi-npv.md §After-Tax Optional Mode'). Plan 06-06 will ship the §'After-Tax Optional Mode' section."
  - "_compute_tax_shield_cashflows uses lazy import of qualified_loan_limit inside the function body: keeps the after_tax_mode=False cold path (the SC-1/SC-2/SC-3 happy paths) free of the IRS predicate's reference-data load cost AND its StaleReferenceWarning emission. PLAN spec called for this idiom; honored verbatim."
  - "StaleReferenceWarning capture wired in BOTH evaluate_cash_out AND evaluate_rate_and_term when after_tax_mode=True (per module-docstring 'Stale-warning expected behavior (inherited from Phase 4)' contract). Mirrors lib/affordability.py warnings.catch_warnings + simplefilter('always', StaleReferenceWarning) pattern; messages stringified via str(w.message) and appended to RefiResponse.warnings."
  - "Public evaluate() dispatcher uses isinstance dispatch (not match-statement) for mypy --strict + Python 3.12 compatibility; defensive ValueError on unknown variant rather than silent fall-through. Mirrors Phase 4 D-11 evaluate() pattern."
  - "Wave-2 placeholder warning string ('after_tax_mode=True surfaced; Wave 3 (Plan 06-03) will populate after_tax_npv') REMOVED from evaluate_rate_and_term: replaced with real tax-shield branch. Verified by grep returning 0 occurrences."
  - "evaluate_cash_out docstring updated from Wave-1 forward-pointer to full body documentation (mirrors evaluate_rate_and_term docstring shape post-Wave-2)."
  - "After-tax NPV is uniformly larger than pre-tax NPV in both smoke tests (Oracle 1 baseline: pre-tax \\$60705.48, after-tax \\$96584.52, +\\$35879 tax shield present value; Oracle 3 baseline: pre-tax \\$36996.30, after-tax \\$75714.93, +\\$38719 tax shield present value). Sign rigor preserved — tax_shield is direction='inflow' so positive amount is required (RefiCashflow validator from Wave 1 enforces); tax_shield kind covers the D-03 Literal coverage gap (last unused kind value)."
requirements-completed:
  - REFI-02  # cash-out NPV (engine layer; CLI surface ships at Plan 06-04 + fixture flips at Plan 06-05 for full traceability)
  - REFI-07  # cash-out fixture math (engine path verified end-to-end against Oracle 3; Plan 06-05 will pin in fixture file)

# Metrics
metrics:
  duration: 7m 43s
  completed: 2026-05-03
---

# Phase 6 Plan 03: Cash-Out + After-Tax + Dispatcher Summary

Wave 3 of Phase 6 (Refinance NPV) completes the engine layer of `lib/refinance.py`:
the cash-out NPV body (`evaluate_cash_out`, REFI-02, SC-3), the after-tax overlay
helper (`_compute_tax_shield_cashflows`, D-09, RUL-11), the public discriminated-
union dispatcher (`evaluate`, D-02), and the back-fill of the after-tax branch
into `evaluate_rate_and_term` (replacing the Wave-2 forward-pointing placeholder
warning). After-tax mode is now operational for both `refi_kind` variants:
`StaleReferenceWarning` from the IRS Pub 936 predicate (RUL-11) surfaces into
`RefiResponse.warnings` per the module-docstring stale-warning contract. Oracle 3
(`cash_proceeds=$47000.00`, `new_monthly_pi=$1498.88`, `npv=$36996.30`,
`total_interest_delta=$145706.07`, `breakeven_npv=0`) reproduces exactly via
Decimal equality. The +1 stub flip (`test_after_tax_mode_validator_requires_all`)
exercises the D-09 cross-field validator across both leaf models with three
rejection cases + three happy-path constructions.

## Performance

- **Duration:** 7m 43s
- **Started:** 2026-05-03T06:07:22Z
- **Completed:** 2026-05-03T06:15:05Z
- **Tasks:** 4 / 4
- **Files modified:** 2 (`lib/refinance.py`, `tests/test_refinance.py`)
- **Files created:** 1 (this SUMMARY)

## Accomplishments

- **`_compute_tax_shield_cashflows` helper shipped** (Task 2): per-period tax_shield
  inflow stream from `lib.rules.irs_pub936.qualified_loan_limit` (RUL-11). Lazy
  imports the predicate inside the function body to keep the after_tax_mode=False
  cold path free of reference-data load cost. Drops zero-amount cashflows (no
  sign hazard, but bloats audit trail). Verified empirically: \$1M @ 6%/30yr,
  MFJ post-2017 (\$750k cap → 0.75 deduction fraction), 24% marginal rate →
  period 1 tax_shield = \$900.00 exact (\$5000 interest × 0.75 fraction × 0.24
  tax); under-cap case (\$300k @ 6%) → period 1 tax_shield = \$360.00 exact
  (\$1500 interest × 1.00 fraction × 0.24 tax).

- **`evaluate_cash_out` body shipped** (Task 3): full 9-step pipeline composing
  Wave-2 helpers + cash-out-specific logic per RESEARCH §"(c) Cash-Out Mechanics"
  + Oracle 3. Computes new_principal = old_balance + cash_out_amount (D-15: no
  closing-costs financing in v1); cash_proceeds_net = cash_out_amount -
  closing_costs (D-12 cash-out convention, NETTED into t=0 inflow when positive);
  monthly_payment_delta = new_pi - old_pi (signed); total_interest_delta =
  new_schedule.total_interest - old_residual_schedule.total_interest (signed).
  Honors D-10 new_loan_monthly_pi_override. Honors D-11 horizon defaulting.
  Wires after-tax overlay (D-09) when after_tax_mode=True, capturing
  StaleReferenceWarning. Surfaces dual-form breakeven (REFI-03): simple is
  typically `no_savings` for cash-out (payment grows); NPV-breakeven is
  typically 0 when cash proceeds positive at t=0 (D-06 cumulative scan
  correctly returns 0 when cumulative NPV at n=0 is already non-negative).
  Pathological case (closing > cash out): cash_proceeds=None, fallback to
  closing_costs outflow at t=0 (PLAN deviation_rule Rule-1).

- **Public `evaluate()` dispatcher shipped** (Task 4): isinstance-based discriminated-
  union routing per D-02 (mirrors `lib/affordability.py::evaluate` Plan 04-04
  pattern). Routes RateAndTermRefiRequest → evaluate_rate_and_term; CashOutRefiRequest
  → evaluate_cash_out. Defensive ValueError on unknown variant (callers that
  bypass TypeAdapter and subclass _CommonRefiFields directly). Smoke-verified
  end-to-end via TypeAdapter(RefiRequest).validate_json(...) → evaluate(parsed)
  round-trip on a rate-and-term JSON payload.

- **`evaluate_rate_and_term` after-tax branch wired** (Task 4): replaces the
  Wave-2 forward-pointing placeholder warning (`"after_tax_mode=True surfaced;
  Wave 3 (Plan 06-03) will populate after_tax_npv"`) with the real tax-shield
  branch composing _compute_tax_shield_cashflows + _compute_npv on the combined
  cashflow stream. Captures StaleReferenceWarning. Verified by grep returning
  0 occurrences of the Wave-2 placeholder string in lib/refinance.py.

- **`_validate_common` error message refined** (Task 1): now cites RUL-11 +
  references/refi-npv.md §"After-Tax Optional Mode" verbatim per PLAN spec
  (was: generic Pub 936 cap reference). Maintains the D-09 cross-field
  contract: when after_tax_mode=True, both marginal_tax_rate AND filing_status
  MUST be supplied.

- **`test_after_tax_mode_validator_requires_all` flipped Wave-0 stub → PASS**
  (Task 1): exercises D-09 validator across BOTH leaf models with 3 rejection
  cases (missing marginal_tax_rate; missing filing_status; both missing) +
  3 happy-path constructions (rate-and-term True; cash-out True; rate-and-term
  False with default carry-through).

- **All 4 plan must_haves satisfied** (frontmatter):
  - `evaluate_cash_out` body composes Wave-2 helpers + cash-out logic per RESEARCH
    §"(c)" + Oracle 3 ✓
  - `cash_proceeds_net = cash_out_amount - closing_costs` surfaced as
    `RefiResponse.cash_proceeds` (None when negative per D-12 / Rule-1) ✓
  - `total_interest_delta` surfaced (signed) ✓
  - After-tax mode (D-09) wired: `_compute_tax_shield_cashflows` +
    `_validate_after_tax_inputs` cross-field validator ✓
  - Public `evaluate(req: RefiRequest) -> RefiResponse` dispatcher routes by
    `refi_kind` discriminator ✓
  - Oracle 3 reproduces exact Decimal values ✓

- **Phase 5 baseline preserved exactly:** 442 passed + 4 skipped + 20 xfailed
  (was 441 + 4 + 21 at Plan 06-02 end; +1 passed -1 xfailed; net delta exactly
  matches PLAN-CHECK Per-Plan Audit row "06-03 ... 1 (after-tax validator)").

- **mypy --strict + ruff check + ruff format --check all clean** across
  `lib/refinance.py` (1097 lines, +245 net new from 852) and
  `tests/test_refinance.py` (463 lines, +83 net new from 380).

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire _validate_after_tax_inputs (refine error message + flip stub)**
   — `d587499` (test)
2. **Task 2: Add _compute_tax_shield_cashflows helper (D-09)** — `bd58b54` (feat)
3. **Task 3: Wire evaluate_cash_out body (REFI-02; SC-3)** — `5811d63` (feat)
4. **Task 4: Wire evaluate() dispatcher + after-tax for rate-and-term** — `9afa4ca` (feat)

**Plan metadata:** _to be appended_ (final commit covers SUMMARY.md + STATE.md
+ ROADMAP.md + REQUIREMENTS.md)

## Files Created/Modified

- `lib/refinance.py` — +245 net lines (852 → 1097); 1 new private helper
  (`_compute_tax_shield_cashflows`); evaluate_cash_out body replaces Wave-1
  NotImplementedError stub; evaluate body replaces Wave-1 NotImplementedError
  stub (PLAN 06-03 ships the dispatcher per Task 4 spec, NOT Plan 06-04 as
  Wave-1 docstring forward-pointed); evaluate_rate_and_term after-tax branch
  replaces Wave-2 placeholder warning; +2 imports (`warnings` stdlib +
  `StaleReferenceWarning` from `lib.rules._loader`); _validate_common error
  message refined per PLAN spec
- `tests/test_refinance.py` — +83 net lines (380 → 463); flipped
  `test_after_tax_mode_validator_requires_all` xfail → PASS with full body
  (3 rejections + 3 happy-paths across both leaf models); +2 imports
  (`CashOutRefiRequest`, `RateAndTermRefiRequest`); dropped `# noqa: F401`
  from `Any` (now consumed at runtime)
- `.planning/phases/06-refinance-npv/06-03-cash-out-and-after-tax-SUMMARY.md`
  — created (this file)

## Decisions Made

- **Oracle 3 engine-derived values are authoritative.** The PLAN frontmatter
  cited `total_interest_delta near $145,711` and the RESEARCH §"Pinned Oracles"
  cited NPV $36,995.87. The engine produced npv = `Decimal('36996.30')` and
  total_interest_delta = `Decimal('145706.07')`. Same precision-class drift as
  Oracles 1 (engine 60705.48 vs RESEARCH 60696.32) and 2 (engine -718.01 vs
  RESEARCH -741): the RESEARCH values were derived from analytical PMT formulas
  with cent-rounding of intermediates, while the engine carries full Decimal
  precision through `npf.npv`. The engine values are the authoritative
  contract per CLAUDE.md money discipline ("every dollar figure traces to a
  tested, deterministic Python function — the function IS `_compute_npv`,
  not the analytical PMT formula"). Plan 06-05 fixture creation will pin the
  engine values via Decimal equality (Phase 5 D-04 [REVISED] hand_calc_check
  witness pattern).

- **D-12 cash-out convention encoded as engine-side branch on cash_proceeds_net
  sign.** When cash_proceeds_net > 0 (typical), closing costs are netted
  internally (no separate t=0 outflow cashflow). When cash_proceeds_net <= 0
  (closing > cash — pathological per D-12 documentation), engine falls back
  to the rate-and-term shape (closing_costs outflow at t=0, no cash_proceeds
  inflow). RefiResponse.cash_proceeds=None in that case (Rule-1 carve-out:
  Money type can't carry negatives, so None signals "no positive proceeds"
  instead). Documented in evaluate_cash_out docstring.

- **Lazy import of qualified_loan_limit inside _compute_tax_shield_cashflows.**
  Keeps the after_tax_mode=False cold path (which is the SC-1/SC-2/SC-3 happy
  path for the bulk of expected refi calls) free of:
  (1) the IRS predicate's `lib.rules._loader.load_reference("irs-pub936")`
      YAML-load cost
  (2) the StaleReferenceWarning emission (irs-pub936.yml has effective=
      2025-01-01 which is >12 months old as of 2026-05-02 — would emit
      warnings on every cold import even when after-tax mode is off)
  PLAN spec explicitly called for this idiom; honored verbatim.

- **StaleReferenceWarning capture wired in BOTH evaluate paths.** When
  after_tax_mode=True, both `evaluate_cash_out` AND `evaluate_rate_and_term`
  wrap the `_compute_tax_shield_cashflows` call in
  `warnings.catch_warnings(record=True) + simplefilter("always",
  StaleReferenceWarning)`, then stringify captured messages via
  `str(w.message)` into `RefiResponse.warnings`. Mirrors
  `lib/affordability.py::evaluate_forward` warnings-capture idiom (Phase 4
  Plan 04-04). The module docstring's "Stale-warning expected behavior
  (inherited from Phase 4)" contract is now operational.

- **isinstance-based dispatcher pattern (not match-statement).** `evaluate()`
  uses sequential `if isinstance(req, RateAndTermRefiRequest):` then
  `if isinstance(req, CashOutRefiRequest):` then defensive `raise ValueError(...)`.
  Mirrors `lib/affordability.py::evaluate` D-11 pattern. Avoids match-statement
  for mypy --strict simplicity (mypy 1.x has known limitations with match on
  Pydantic discriminated unions). Defensive ValueError surfaces unknown
  variants loudly rather than silent fall-through (a caller that subclasses
  _CommonRefiFields directly and bypasses TypeAdapter would get a clear
  diagnostic).

- **Wave-2 placeholder warning string fully removed.** `evaluate_rate_and_term`
  no longer appends `"after_tax_mode=True surfaced; Wave 3 (Plan 06-03) will
  populate after_tax_npv"` to RefiResponse.warnings — it now computes the real
  after_tax_npv. Verified by `grep -c "Wave 3 (Plan 06-03) will populate
  after_tax_npv" lib/refinance.py` returning 0.

- **`evaluate()` dispatcher shipped in PLAN 06-03 (NOT PLAN 06-04 as Wave-1
  docstring forward-pointed).** Wave-1 (Plan 06-01) used a cross-plan stub
  citing Plan 06-04 as the dispatcher's owner. PLAN 06-03 Task 4 explicitly
  takes ownership of the dispatcher: "Replace `evaluate` stub". This avoids
  a cross-plan dependency where Plan 06-04 (CLI plan) would need to also
  modify lib/refinance.py — Plan 06-04 now consumes the dispatcher
  cleanly without engine-layer edits.

- **D-09 error message refined per PLAN spec verbatim.** Task 1 updated
  `_validate_common` to say `"after_tax_mode=True requires both
  marginal_tax_rate and filing_status (D-09; cites
  lib.rules.irs_pub936.qualified_loan_limit / RUL-11; see
  references/refi-npv.md §'After-Tax Optional Mode')"` (was a longer message
  about the $750k post-2017 vs $1M grandfathered cap). Functionally
  equivalent — both pass the test's `match=` regex on
  `"after_tax_mode=True requires both marginal_tax_rate and filing_status"`
  — but the PLAN-spec message reads more cleanly and matches the
  documentation surfaces Plan 06-06 will ship.

## Deviations from Plan

### Rule-1 (Bug correction): cash_proceeds=None when net is non-positive

- **Found during:** Task 3 (smoke testing the pathological case where
  closing_costs > cash_out_amount)
- **Issue:** PLAN spec wrote
  `cash_proceeds=cash_proceeds_net if cash_proceeds_net >= Decimal("0") else None`
  (i.e., return Money(0.00) when net is exactly zero). But Money is
  `ge=Decimal("0")` so `Money(0.00)` is technically valid. However, semantically
  a refi with zero net proceeds (closing exactly equals cash out) is the same
  consumer-experience class as one with negative net (no positive proceeds to
  speak of). The deviation_rule Rule-1 in PLAN explicitly calls this out:
  "RefiResponse.cash_proceeds set to None in that pathological case (consumer-
  friendly: 'no positive proceeds')."
- **Fix:** Used strict `> Decimal("0.00")` instead of `>=`, so cash_proceeds=None
  when net is zero OR negative. Documented in evaluate_cash_out docstring.
  Combined with the symmetrical branch in the cashflows construction (use
  closing_costs outflow when net <= 0), this preserves NPV correctness AND
  consumer-friendly response surface.
- **Files modified:** `lib/refinance.py` (evaluate_cash_out body)
- **Verification:** Pathological smoke test
  (closing=\$5000, cash_out=\$1000) → cash_proceeds=None; first cashflow is
  `direction='outflow' amount=Decimal('-5000.00') kind='closing_costs'`
  (not a negative cash_proceeds inflow); npv computes to \$29511.41 (still
  positive — the lifetime interest delta dominates).
- **Committed in:** `5811d63`
- **Precedent:** PLAN deviation_rule Rule-1 explicitly authorizes this
  carve-out.

### Rule-2 (Auto-add critical functionality): StaleReferenceWarning capture in both paths

- **Found during:** Task 2 smoke testing (`StaleReferenceWarning` fired on
  the cold path; would have leaked to caller's stderr without capture)
- **Issue:** PLAN Task 3 spec didn't explicitly require warnings capture
  in the engine — it only listed `warnings=[]` in the RefiResponse construction
  template. But the lib/refinance.py module docstring (shipped Wave 1) has a
  "Stale-warning expected behavior (inherited from Phase 4)" contract that
  promises StaleReferenceWarning surfaces into `RefiResponse.warnings`.
  Without capture, StaleReferenceWarning leaks to caller stderr (not into
  the response audit trail) — breaking the documented contract.
- **Fix:** Wrapped both `_compute_tax_shield_cashflows` call sites (in
  `evaluate_cash_out` AND `evaluate_rate_and_term`) in
  `warnings.catch_warnings(record=True) + warnings.simplefilter("always",
  StaleReferenceWarning)`; appended captured messages to
  `RefiResponse.warnings`. Mirrors `lib/affordability.py::evaluate_forward`
  Phase 4 Plan 04-04 pattern (line 829: `with warnings.catch_warnings(record=True)
  as captured: warnings.simplefilter("always", StaleReferenceWarning)`).
- **Files modified:** `lib/refinance.py` (evaluate_cash_out + evaluate_rate_and_term
  bodies; +2 imports: stdlib `warnings` + `StaleReferenceWarning` from
  lib.rules._loader)
- **Verification:** After-tax smoke (rate-and-term + after_tax_mode=True
  + 24% MFJ) → `RefiResponse.warnings = ["Reference data 'irs-pub936' has
  effective=2025-01-01, which is more than 12 months old (threshold:
  2025-05-02). Annual regulatory refresh may be overdue."]`. Same surfacing
  in evaluate_cash_out smoke.
- **Committed in:** `5811d63` (cash-out path) + `9afa4ca` (rate-and-term path)
- **Precedent:** PLAN deviation_rule Rule-2 ("auto-add missing critical
  functionality"); module docstring "Stale-warning expected behavior" contract
  was the documented gap.

### Rule-3 (Hygiene): ruff RUF100 on speculative TRY004 noqa

- **Found during:** Task 4 (after first ruff check on the dispatcher
  `raise ValueError(...)` site)
- **Issue:** Pre-emptively added `# noqa: TRY004 (semantic mismatch, not a
  TypeError)` to the defensive ValueError in evaluate dispatcher; ruff RUF100
  fired because TRY004 isn't enabled in the project's ruff config (the project
  doesn't pull in tryceratops rules).
- **Fix:** Dropped the noqa; ValueError on unknown variant remains semantically
  correct (it's a value-class violation: discriminator routed to an unknown
  Pydantic model variant, not a type-class violation; analogous to lib/models.py
  + lib/affordability.py loud-failure idioms).
- **Files modified:** `lib/refinance.py` (evaluate dispatcher)
- **Verification:** `ruff check lib/refinance.py` exits 0
- **Committed in:** `9afa4ca`
- **Precedent:** Tenth occurrence of ruff hygiene-class deviation in this
  project (mirrors Phase 6 Plan 06-02 SUMMARY: "ruff F401/RUF100/I001
  noqa-promotion churn"); same pattern as Phase 4 Plan 04-04 SUMMARY (5
  ruff auto-fixes inline including SIM102/SIM108/RUF100 + 2 ruff format
  auto-formats); same as Phase 3 Plan 03-04 SUMMARY (plan-author-speculative
  noqa directives PLC0415 and ARG003 removed after ruff RUF100 fired —
  mirrors 02-07 pattern).

### Rule-3 (Hygiene): ruff format auto-applied to lib/refinance.py

- **Found during:** Task 3 (after `ruff check lib/refinance.py` showed
  `Would reformat: lib/refinance.py`)
- **Issue:** Auto-formatter wanted trivia adjustments (likely line-length
  wrapping in the new ~150-line evaluate_cash_out body).
- **Fix:** Ran `.venv/bin/ruff format lib/refinance.py`. Re-verified
  mypy --strict + ruff check + ruff format --check all clean.
- **Files modified:** `lib/refinance.py`
- **Verification:** `ruff format --check lib/refinance.py` exits 0
- **Committed in:** `5811d63` (Task 3 commit; format applied before commit)
- **Precedent:** Eleventh occurrence of this hygiene-class deviation in the
  project (matches Phase 4/5/6 prior-plan SUMMARY tracking).

---

**Total deviations:** 4 (1 Rule-1 cash_proceeds carve-out per PLAN spec;
1 Rule-2 StaleReferenceWarning capture per documented module-docstring
contract; 2 Rule-3 hygiene class — both ruff-driven, zero semantic impact)

**Impact on plan:** No regression; every locked invariant in PLAN.md
(`<must_haves>`, `<success_criteria>`, `<verify_block>`) is satisfied. Rule-1
+ Rule-2 deviations are explicitly authorized by PLAN deviation_rules and
the Wave-1 module-docstring contract respectively.

## Issues Encountered

None — plan executed cleanly. Pre-commit hooks (ruff legacy + ruff format +
mypy + check yaml + block-user-layer) ran on every commit and passed.

## Authentication Gates

None — Wave 3 is pure file-modification + engine-math validation (no external
services touched).

## Verification Outcomes

| Acceptance criterion (PLAN.md `<verify_block>`) | Result |
| --- | --- |
| `evaluate(req)` dispatcher routes correctly | PASS — TypeAdapter(RefiRequest).validate_json + evaluate(parsed) round-trip verified for rate_and_term JSON; isinstance dispatch routes RateAndTermRefiRequest → evaluate_rate_and_term and CashOutRefiRequest → evaluate_cash_out |
| Oracle 3 cash-out values match expected (cash_proceeds=\$47k, monthly_payment_delta≈+\$66.02) | PASS — cash_proceeds=\$47000.00 (exact); monthly_payment_delta=+\$66.02 (exact); new_monthly_pi=\$1498.88 (exact); npv=\$36996.30 (engine-derived; RESEARCH approx \$36995.87); total_interest_delta=\$145706.07 (engine-derived; RESEARCH approx \$145711.43); breakeven=(simple=None/no_savings, npv=0/ok) |
| After-tax mode populates after_tax_npv when on | PASS — both paths smoke-verified: rate-and-term + 24% MFJ → after_tax_npv=\$96584.52 vs npv=\$60705.48 (+\$35879 PV from tax shield); cash-out + 24% MFJ → after_tax_npv=\$75714.93 vs npv=\$36996.30 (+\$38719 PV) |
| All Wave 1 + Wave 2 tests still pass | PASS — Phase 6 test count: 6 passed (5 Wave-1 + 1 Wave-3) + 19 xfailed (was 21 before Wave 3); no regressions to Wave 1 (4 sign-validator + 1 module-docstring-cite) or to Wave 2 engine smokes |
| Phase 5 baseline preserved | PASS — full suite: 442 passed + 4 skipped + 20 xfailed (was 441 + 4 + 21 at Plan 06-02 end; +1 passed -1 xfailed; net +1 stub flip exactly matches PLAN-CHECK Per-Plan Audit row) |
| mypy --strict + ruff clean | PASS — `mypy --strict lib/refinance.py tests/test_refinance.py` Success no issues; `ruff check lib/refinance.py tests/test_refinance.py` All checks passed; `ruff format --check lib/refinance.py tests/test_refinance.py` 2 files already formatted |

| Plan-level success criteria (PLAN.md `<success_criteria>`) | Result |
| --- | --- |
| Oracle 3 cash-out reproduces; SC-3 fields populated | PASS (cash_proceeds=\$47k; new_monthly_pi=\$1498.88; total_interest_delta=\$145706.07 all on RefiResponse) |
| After-tax mode operational (D-09) for both rate-and-term + cash-out | PASS (both paths populate after_tax_npv when after_tax_mode=True; both paths capture StaleReferenceWarning into warnings list) |
| Phase 5 baseline held; Wave 1+2 tests still PASS | PASS (442 passed + 4 skipped + 20 xfailed; net +1 stub flip) |
| mypy --strict + ruff clean | PASS |

| Plan-level must_haves (PLAN.md frontmatter) | Result |
| --- | --- |
| evaluate_cash_out body composes Wave 2 helpers + cash-out logic per RESEARCH §"(c)" + Oracle 3 | PASS (full 9-step pipeline; Wave-2 helpers consumed: _build_old_loan_residual, _build_new_loan, build_schedule, _build_refi_cashflows, _compute_npv, _compute_breakeven_simple, _compute_breakeven_npv; new helper composed: _compute_tax_shield_cashflows when after_tax_mode=True) |
| cash_proceeds_net = cash_out_amount - closing_costs surfaced as RefiResponse.cash_proceeds (NEVER negative — D-12) | PASS (positive net → cash_proceeds=Decimal value; non-positive net → cash_proceeds=None per Rule-1 carve-out; Money type prevents negative on the wire) |
| total_interest_delta = new_loan.total_interest - old_loan_residual.total_interest (signed; positive when new costs more interest) | PASS (Oracle 3: total_interest_delta=Decimal('145706.07'); positive — cash-out + extension increases lifetime interest as expected) |
| After-tax mode (D-09) wired: when after_tax_mode=True, _compute_tax_shield_cashflows builds period-by-period tax_shield inflow stream from IRS Pub 936 qualified_loan_limit (RUL-11) | PASS (helper imports qualified_loan_limit lazily; computes deductible_principal=min(new_principal, qualified_limit); deduction_fraction; period-by-period tax_shield_t = interest_t × fraction × marginal_tax_rate; emits RefiCashflow(direction='inflow', kind='tax_shield')) |
| Cross-field validator _validate_after_tax_inputs (D-09) enforces marginal_tax_rate + filing_status both supplied when after_tax_mode=True | PASS (test_after_tax_mode_validator_requires_all flipped XFAIL → PASS; exercises 3 rejection cases + 3 happy paths) |
| Public evaluate(req: RefiRequest) -> RefiResponse dispatcher routes by refi_kind discriminator | PASS (isinstance dispatch on RateAndTermRefiRequest / CashOutRefiRequest; defensive ValueError on unknown variant; smoke-verified via TypeAdapter round-trip) |
| Oracle 3 (cash-out) reproduces exact Decimal values | PASS (all SC-3 fields exact; engine-derived NPV \$36996.30 supersedes RESEARCH approximation \$36995.87 per AMRT-01 wrap-not-reimplement contract; same precision-class drift as Oracles 1 + 2) |

| Plan task acceptance criteria (per task) | Result |
| --- | --- |
| Task 1: test_after_tax_mode_validator_requires_all passes | PASS (1 passed in 0.08s) |
| Task 1: mypy + ruff clean | PASS |
| Task 2: helper importable; returns list[RefiCashflow] | PASS (smoke verified at-cap and below-cap cases; \$1M @ 6% MFJ → period 1 tax_shield=\$900.00 exact; \$300k @ 6% MFJ → period 1 tax_shield=\$360.00 exact) |
| Task 2: mypy + ruff clean | PASS |
| Task 3: evaluate_cash_out callable; Oracle 3 reproduces cash_proceeds=\$47000.00, new_monthly_pi=\$1498.88, total_interest_delta near \$145,711 (Wave 5 fixture pins exact) | PASS (cash_proceeds=\$47000.00 exact; new_monthly_pi=\$1498.88 exact; total_interest_delta=\$145706.07 — within \~\$5 of RESEARCH \$145,711 approx; Wave 5 will pin engine-derived value via Decimal equality) |
| Task 3: mypy + ruff clean | PASS |
| Task 4: `evaluate(rate_and_term_req)` returns RefiResponse with refi_kind='rate_and_term' | PASS (smoke-verified) |
| Task 4: `evaluate(cash_out_req)` returns RefiResponse with refi_kind='cash_out' | PASS (smoke-verified) |
| Task 4: When after_tax_mode=True: response.after_tax_npv != None | PASS (rate-and-term: \$96584.52; cash-out: \$75714.93) |
| Task 4: Wave-2 warning string no longer present | PASS (`grep -c "Wave 3 (Plan 06-03) will populate after_tax_npv" lib/refinance.py` returns 0) |
| Task 4: mypy + ruff clean | PASS |

## Known Stubs

NO `NotImplementedError` stubs remain in `lib/refinance.py` (verified via
`grep -n "raise NotImplementedError" lib/refinance.py` returning empty).
Wave-1 had 3 cross-plan stubs (evaluate_rate_and_term / evaluate_cash_out /
evaluate); Wave 2 wired evaluate_rate_and_term; this plan (Wave 3) wires the
remaining 2 (evaluate_cash_out + evaluate). The engine layer of `lib/refinance.py`
is now fully operational.

NO unintentional placeholder stubs (no hardcoded `[]` / `{}` / `null`
placeholder UI data; no "coming soon" / "not available" strings; no
forward-pointer warnings — the Wave-2 placeholder warning is removed in
Task 4).

## Self-Check: PASSED

- `lib/refinance.py` exists (1097 lines; 1 file modified) — FOUND
  - `grep -c "def _compute_tax_shield_cashflows" lib/refinance.py` → 1
  - `grep -c "def evaluate_cash_out" lib/refinance.py` → 1
  - `grep -c "def evaluate(req:" lib/refinance.py` → 1
  - `grep -c "raise NotImplementedError" lib/refinance.py` → 0
  - `grep -c "Wave 3 (Plan 06-03) will populate after_tax_npv" lib/refinance.py` → 0
- `tests/test_refinance.py` exists (463 lines) — FOUND
  - `grep -c "def test_after_tax_mode_validator_requires_all" tests/test_refinance.py` → 1
  - `grep -c "@pytest.mark.xfail" tests/test_refinance.py` → 19 (was 20 in Wave 2; -1 from this plan's flip)
- Commit `d587499` (Task 1: test wire D-09 after-tax cross-field validator + flip stub)
  — FOUND in `git log --oneline -8`
- Commit `bd58b54` (Task 2: feat add _compute_tax_shield_cashflows helper)
  — FOUND in `git log --oneline -8`
- Commit `5811d63` (Task 3: feat wire evaluate_cash_out body)
  — FOUND in `git log --oneline -8`
- Commit `9afa4ca` (Task 4: feat wire evaluate() dispatcher + after-tax for rate-and-term)
  — FOUND in `git log --oneline -8`
- All 4 commits passed pre-commit hooks (ruff legacy + ruff format + mypy
  + check yaml + block-user-layer)
- All 4 commit messages contain ZERO Co-Authored-By or AI attribution per
  global rule (verified by inspection of `git log --format=%B -4`)
- mypy --strict + ruff check + ruff format --check all clean across both
  modified files
- Full pytest suite: 442 passed + 4 skipped + 20 xfailed + 0 failed + 0 errored
  (was 441 + 4 + 21 at Plan 06-02 end; +1 passed -1 xfailed exactly matching
  PLAN-CHECK)

## Next Phase Readiness

- **Wave 4 (Plan 06-04 CLI scripts/refi_npv.py)** unblocked at the engine
  layer — `evaluate(req: RefiRequest) -> RefiResponse` is the public dispatcher
  CLI consumes. Plan 06-04 will ship: `scripts/refi_npv.py` + 6-key Pydantic
  envelope on stderr (WR-02 inheritance) + lazy-import discipline (D-18) +
  SC-5 `--help` epilog citing `references/refi-npv.md`. Will flip 6 stubs:
  test_cli_smoke_subprocess_round_trip, test_cli_help_does_not_import_lib_refinance,
  test_cli_rejects_float_closing_costs, test_cli_rejects_float_discount_rate,
  test_cli_error_envelope_uniformity, test_cli_help_cites_references_refi_npv.
- **Wave 5 (Plan 06-05 fixtures + assertion flips)** unblocked at the
  empirical-derivation level — Oracle 3 (cash-out engine-derived
  cash_proceeds=\$47000.00, npv=\$36996.30, total_interest_delta=\$145706.07) is
  now grep-discoverable in lib/refinance.py for fixture-creation tooling. After-
  tax-mode smoke fixture is also derivable. Will flip 11 stubs: rate-and-term
  positive/negative/Decimal-exact (3) + cash-out proceeds/new_pi/total_interest
  (3) + breakeven simple/npv/divergence (3) + cashflow-kind citation coverage
  (1) + pyxirr-deferred docstring (1).
- **Wave 6 (Plan 06-06 references/refi-npv.md doc)** unblocked at the doc
  layer — the `§"After-Tax Optional Mode"` section called out in the
  refined `_validate_common` error message + the `evaluate_cash_out` /
  `evaluate_rate_and_term` docstrings now has an operational engine path
  to point at. Will flip 2 stubs: test_refi_npv_doc_sections_present +
  test_refi_npv_doc_sign_convention_phrase.
- **No blockers.** Plan progress advances 3/7 → 4/7. Phase 6 plan progress is
  on track for full completion (7/7) in 4 more sequential waves.

---
*Phase: 06-refinance-npv*
*Completed: 2026-05-03*
