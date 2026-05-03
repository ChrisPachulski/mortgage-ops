# Phase 7: Estimated APR (Reg Z Appendix J) - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning (RE-PLAN required — existing 8 plans drafted 2026-05-02 without user context)

<domain>
## Phase Boundary

Build `lib/apr.py` — a Newton-Raphson "estimated APR" solver against the Reg Z Appendix J unit-period equation, layered on top of Phase 3's amortization engine. Ships:

- `lib/apr.py` — `APRRequest` / `APRResponse` Pydantic v2 models (strict + frozen + extra=forbid) + `solve_apr(...)` Newton-Raphson engine with Decimal arithmetic throughout (seed via `npf.rate`, iterate in `MONEY_CONTEXT.prec=28`, converge within `Decimal("0.00001")`, cap at 50 iterations)
- `scripts/apr_reg_z.py` — JSON-in / JSON-out CLI mirroring `scripts/refi_npv.py` (Phase 6) and `scripts/arm_simulate.py` (Phase 5); 6-key Pydantic error envelope on stderr (Phase 3 WR-02); lazy-import `--help`
- `references/apr-reg-z.md` — documents unit-period equation, US 30/360 day-count, odd-first-period (long case only), "estimated APR" literal-text rationale, HMDA Platform oracle methodology
- `tests/test_apr.py` — golden + structural + invariant + CLI subprocess tests; flips Wave 0 xfail stubs as solver capabilities ship
- `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` — Reg Z Appendix J Example J-1 anchor (SC-1: $5000 / 36 / $166.07 → 12.00% APR within `Decimal("0.00001")`)
- `tests/fixtures/apr/oracle/hmda_*.json` — 20+ HMDA-Platform-cross-validated fixtures spanning 30yr fixed × loan amounts, 15yr fixed × rates, balloon, odd-first-period long cases (D-01 below)
- `tests/conftest.py` — extend with `apr_fixture` factory (mirrors `arm_fixture` lines 73-90)

**Delivered this phase:**
- `lib/apr.py` (APRRequest + APRResponse + AdvanceScheduleEntry + PaymentScheduleEntry + `solve_apr` + `_seed_apr` + `_decimal_pow` + `_compute_odd_first_period_fraction`) — APR-01..03
- `scripts/apr_reg_z.py` JSON-in/JSON-out CLI — APR-07
- `tests/test_apr.py` + `tests/fixtures/apr/` (hand-calc + HMDA Platform oracle captures) — APR-04, APR-05
- `tests/test_apr.py` regex meta-tests on the literal "estimated APR" — APR-06
- `references/apr-reg-z.md` with eCFR + CFPB + HMDA Platform citations — APR-08

**NOT delivered this phase** (deferred to consumer phases or v2):
- Multi-advance / construction-loan APR (advances list capped at exactly 1 entry — D-04 below) — v2 / future phase if a real use case emerges
- `actual/365` and `actual/actual` day-count conventions — rejected at Pydantic boundary in v1 (D-03 below); ship when an ARM/treasury use case drives demand
- Short odd-first-period (negative `f`, first payment < 30 days after origination) — engine math supports it; v1 fixtures cover only long cases (Claude's Discretion below)
- §1026.4 finance-charge classifier — caller-supplied `finance_charges: Money` field (orchestrator-locked, RESEARCH §Q(f))
- FFIEC APRWIN binary captures — explicitly skipped (D-02 below); HMDA Platform is sole oracle
- Stress-test APR sweeps across rate paths — Phase 8 (re-invokes `solve_apr` per grid cell)
- DuckDB persistence of APRResponse — Phase 9
- Skill physical relocation: `scripts/apr_reg_z.py` → `.claude/skills/mortgage-ops/scripts/apr_reg_z.py` — Phase 10
- `.claude/skills/mortgage-ops/references/apr-reg-z.md` mirror — Phase 10 (Phase 7 ships at repo root)
- ARM-aware APR (post-reset rate-change re-solving) — modeled trivially via the unit-period equation as a sequence of constant-rate epochs, but the v1 CLI takes a single fixed payment schedule; ARM-aware APR is Phase 8+ if needed

</domain>

<decisions>
## Implementation Decisions

### Oracle strategy (SC-2 / APR-04) — pivot away from FFIEC

- **D-01: HMDA Platform is the sole oracle for v1.** Use the `cfpb/hmda-platform` open-source Reg Z Appendix J implementation as the canonical cross-validation source. It is reproducible, auditable, scriptable, and authored by the same agency that publishes the FFIEC APR Tool — so HMDA Platform IS the reference impl FFIEC ships, just packaged differently.

  - 20+ fixtures live at `tests/fixtures/apr/oracle/hmda_NNN_<descr>.json` with the schema:
    ```json
    {
      "request": { ...APRRequest JSON... },
      "expected": {
        "estimated_apr": "0.071234",
        "oracle": "hmda-platform",
        "oracle_commit_sha": "<full git sha of cfpb/hmda-platform repo at capture time>",
        "oracle_url": "https://github.com/cfpb/hmda-platform",
        "captured_at": "YYYY-MM-DD"
      }
    }
    ```
  - Pin the upstream commit SHA (not a screenshot SHA — Phase 5's PNG-pinning idiom doesn't apply to a code-based oracle). Re-capture on demand when upstream releases a new version; document the SHA bump in a commit message.
  - Plan 07-07 becomes **autonomous** (was human-checkpoint in the existing draft): the planner spins up HMDA Platform locally (Docker or sbt; whichever the upstream README endorses) and generates fixtures via a small shim script.

- **D-02: FFIEC APRWIN is explicitly out of scope as an oracle.** No manual capture, no Windows VM workflow, no screenshot SHAs. Rationale:
  - APRWIN is a 2008-era Windows desktop binary (`https://www.ffiec.gov/aprwin.htm`). Driving it 20× by hand is friction without insight.
  - HMDA Platform and APRWIN share the same Reg Z source (cfpb is FFIEC's parent for HMDA). Cross-checking adds no information.
  - If APRWIN ever gains a programmatic surface, revisit via a backlog phase.

- **D-09: HMDA delta policy — engine is wrong.** If HMDA Platform output diverges from `solve_apr` by more than `Decimal("0.00001")` on any fixture, the engine is presumed wrong. Test fails loudly (`pytest.fail` with HMDA value, engine value, delta). Investigation prioritizes engine bug, not fixture re-capture or tolerance widening. Per-fixture tolerance overrides are NOT permitted in v1.

### ROADMAP / REQUIREMENTS verbatim updates required before re-plan

- **D-10: ROADMAP SC-2 must be re-worded** before plan-phase re-runs. Current text reads "All 20+ FFIEC-captured fixtures..."; the corrected wording is "All 20+ HMDA-Platform-captured fixtures (varying loan amounts, terms, advance schedules) pass with computed APR within `Decimal('0.00001')` of HMDA Platform output". REQUIREMENTS.md APR-04 needs the same edit. ROADMAP entry for Phase 7 still says "validated against FFIEC tool" — replace with "validated against HMDA Platform".
  - **Action required before `/gsd-plan-phase 07` re-run:** edit ROADMAP.md SC-2 + REQUIREMENTS.md APR-04 + Phase 7 description (3 surfaces). Keep the original FFIEC mention in `deferred-items.md` for traceability.

### Day-count convention scope

- **D-03: 30/360 only in v1.** `APRRequest.day_count: Literal["30/360"] = "30/360"`. Passing `"actual/365"` or `"actual/actual"` raises a Pydantic validation error at the request boundary (surfaced via the 6-key envelope on the CLI). Helper `_compute_odd_first_period_fraction(origination, first_payment, day_count)` accepts only `"30/360"`. Documented in `references/apr-reg-z.md` §3 with a "Future work" pointer.
  - Rationale: personal-use mortgages are 30/360 in practice. The two alternative conventions add ~30 + ~50 lines of helper logic with no immediate testable use case. Future phase relaxes the Literal when ARM/treasury demand drives it.

### Multi-advance / construction-loan support

- **D-04: Single advance only in v1.** `APRRequest.advances: list[AdvanceScheduleEntry]` constrained `Field(min_length=1, max_length=1)`. The request schema already uses the U-equation form, so relaxing the bound is a config change (drop `max_length=1`) — no engine rewrite needed.
  - Rationale: PROJECT.md scope is the Pachulski household. No construction loan, no draw-down HELOC. Single-family purchase mortgages are single-advance. Smaller test surface, faster to ship.
  - The example fixture `regz_appendix_j_5000_36_166_07.json` and all 20+ HMDA Platform captures are single-advance.

### APRResponse schema surface

- **D-05: Surface all four diagnostic signals.** `APRResponse` v1 contains:
  ```python
  class APRResponse(BaseModel):
      estimated_apr: Money            # quantize_rate at 6 decimal places
      summary: str                    # Pydantic @model_validator enforces "estimated APR" literal + no bare "APR" (SC-4)
      iterations: int                 # Field(ge=1, le=50) — pinned by SC-3 enforcement
      final_residual: Money           # abs(f(i_final)) in dollars after convergence; debug signal
      tolerance_check: dict[str, Any] | None = None  # populated only when APRRequest.disclosed_apr is supplied
  ```
  - `iterations` and `final_residual` are always emitted. `tolerance_check` is populated only when the optional `APRRequest.disclosed_apr: Money | None` is supplied; shape `{"within_tolerance": bool, "tolerance_used": Decimal, "regulation": "12 CFR §1026.22(a)(2)"}` composing the Phase 2 `lib.rules.reg_z.within_apr_tolerance` predicate.
  - Rationale: full diagnostic surface, no second pass needed when a fixture deviates. Phase 5 D-04 capture-as-fixture pattern wants precise diagnostic fields.

- **D-06: Convergence dual-criterion (engine-internal, not surfaced).** Newton-Raphson terminates only when BOTH:
  - `abs(i_{n+1} - i_n) <= Decimal("0.00001")` (rate tolerance — the SC-1 anchor)
  - `abs(f(i_{n+1})) <= Decimal("0.01")` (one-cent dollar residual — defense-in-depth)

  Prevents the "rate stalled, residual huge" edge case. Phase 7-invented guard, not Reg Z required. Documented in `references/apr-reg-z.md` §5. `final_residual` from D-05 is the second criterion's value; surfaces for debugging but the convergence check is internal to `solve_apr`.

### Carrying forward from earlier phases (already locked, not discussed)

- **D-07: Inherited project-wide conventions:**
  - Decimal money discipline (Phase 1) — construct from strings; `quantize_cents` end-of-period only; never mix float and Decimal in money expressions
  - `quantize_rate` at 6 decimal places (Phase 5 D-14) — used at the final APR result and at every Decimal-power input
  - `numpy-financial` wrap, no reimplementation (Phase 3) — `npf.rate` is the seed; `lib.amortize.build_schedule` is NOT directly reused (APR doesn't need a payment schedule, just the U-equation), but Phase 3's per-period iteration shape inspires `solve_apr`'s loop
  - Pydantic v2 `ConfigDict(strict=True, frozen=True, extra="forbid")` on all models (Phase 1 D-08)
  - 6-key error envelope on CLI ValidationErrors (Phase 3 WR-02 + Phase 4 D-13 inherited via `scripts/_cli_helpers.py`)
  - Subprocess invocation in CLI tests (Phase 3 D-17 — script may relocate in Phase 10)
  - Capture-as-fixture pattern (Phase 5 D-04) — adapted for code-based oracle (commit SHA pin, not PNG sha256)

### Orchestrator-locked decisions (from prior briefs / RESEARCH §Q(f))

- **D-08: Caller-supplied `finance_charges`.** `APRRequest.finance_charges: Money` is required; no §1026.4 classifier in v1. Engine subtracts `finance_charges` from `loan_amount` to form `amount_financed` per Reg Z §1026.18(b). Documented in `lib.apr.APRRequest.finance_charges.__doc__` + `references/apr-reg-z.md` §3 (with the §1026.4 enumeration table for reader reference, but the engine does NOT classify).

### Claude's Discretion

The following sub-decisions were not surfaced because they're implementation-detail-level — Claude chooses based on RESEARCH defaults, with a sentence on rationale per item:

- **Odd-first-period: long case only in v1.** RESEARCH OPEN Q1 noted that §1026.17(c)(4) does not forbid SHORT first periods (negative `f`). Engine math supports `f ∈ [-1, 1)` per the (1 + f·i) factor algebra; v1 test fixtures and HMDA Platform captures cover only `f ∈ [0, 1)` (long cases — origination-to-first-payment ≥ 30 days). Short cases are accepted by the boundary but flagged by an engine-internal warning ("short odd-first-period: not cross-validated in v1") on solve. v2 captures negative-`f` fixtures when a real loan with a short first period appears.
- **Newton iteration logging.** Engine emits a structured `logging.debug(...)` line per iteration with `(iteration, current_rate, residual)`. Off by default; surfaces under `LOG_LEVEL=DEBUG`. Not exposed in APRResponse.
- **Decimal-power helper.** Use `(base.ln() * exponent).exp()` route under `MONEY_CONTEXT.prec=28` per RESEARCH §Finding 7. No `prec=50` localcontext escalation needed.
- **`solve_apr` return on convergence failure.** Raise `APRConvergenceError(ValueError)` with iteration count + last residual in the message. CLI catches via the 6-key envelope and exits non-zero. RESEARCH §Q(c) specifies this; documented in `lib.apr.APRConvergenceError.__doc__`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Inputs (project-level)
- `.planning/PROJECT.md` — household scope, math-correctness-first core value, sibling repo patterns
- `.planning/REQUIREMENTS.md` APR-01..APR-08 — Phase 7 requirement set (NOTE: APR-04 wording requires update before re-plan per D-10)
- `.planning/ROADMAP.md` Phase 7 §SC-1..SC-5 (NOTE: SC-2 wording requires update before re-plan per D-10)
- `CLAUDE.md` — money discipline, calc-engine separation, Decimal-from-string rules
- `DATA_CONTRACT.md` — User/System/Data/Reference layer enforcement

### Phase 7 Existing Artifacts (re-read by re-plan)
- `.planning/phases/07-estimated-apr/07-RESEARCH.md` — eight load-bearing findings + five worked examples + five RESEARCH OPEN Q's; Q4 (FFIEC) closed by D-01/D-02; Q1/Q2/Q3/Q5 closed by D-05/D-06 + Claude's Discretion
- `.planning/phases/07-estimated-apr/07-PATTERNS.md` — pattern map, 10/10 NEW files have analogs in Phases 3/4/5
- `.planning/phases/07-estimated-apr/07-PLAN-CHECK.md` — 11 PASS / 2 CONCERN / 0 BLOCK (both CONCERNs collapse to D-01/D-02 — FFIEC pivot)
- `.planning/phases/07-estimated-apr/07-00-test-infrastructure-PLAN.md` through `07-07-ffiec-fixtures-PLAN.md` — existing 8-plan suite (re-plan must adjust 07-07 to HMDA Platform fixtures, autonomous; reduce 07-04 oracle docs accordingly)

### Prior-Phase CONTEXT.md (read for decisions that affect Phase 7)
- `.planning/phases/05-arm-modeling/05-CONTEXT.md` — D-14 `quantize_rate` promotion; D-04 capture-as-fixture (PNG SHA pin pattern; Phase 7 adapts to commit-SHA pin); ResetEvent / cumulative-totals pattern Phase 7 doesn't reuse but bears stylistic kinship
- `.planning/phases/04-affordability/04-CONTEXT.md` — `evaluate_reverse` seed-then-refine pattern (closest precedent for `solve_apr`)
- `.planning/phases/03-core-amortization/03-CONTEXT.md` — D-09 final-payment cleanup (Phase 7 doesn't reuse — solver doesn't emit a Schedule); D-13/D-17/D-18/D-19 CLI conventions Phase 7 inherits

### Prior-Phase Frozen Surfaces (Phase 7 USES; does NOT modify)
- `lib/money.py` — `MONEY_CONTEXT`, `quantize_cents`, `quantize_rate`, `to_money`, `CENT`
- `lib/models.py` — `Money` (Annotated condecimal), `Rate` (Annotated condecimal at 6 dp)
- `lib/rules/reg_z.py` lines 1-89 — `within_apr_tolerance`, `TOLERANCE_REGULAR = Decimal("0.00125")`, `TOLERANCE_IRREGULAR`; the docstring already references "Phase-7 consumer" (line 43)
- `scripts/_cli_helpers.py` — JSON-float pre-validation gate, 6-key envelope formatter
- `tests/conftest.py` — extend with `apr_fixture` factory (do not modify other fixtures)

### External Sources (regulatory + tool oracles)
- **eCFR 12 CFR Part 1026 Appendix J** (the U-equation, binding algebra): https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026
- **eCFR 12 CFR §1026.17(c)(4)** (basis of disclosures + odd first period): https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.17#p-1026.17(c)(4)
- **eCFR 12 CFR §1026.18(b) and (e)** (amount-financed + APR disclosure label): https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.18
- **eCFR 12 CFR §1026.4** (finance-charge enumeration; Phase 7 does NOT classify but cites for caller reference): https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-A/section-1026.4
- **eCFR 12 CFR §1026.22(a)(2)** (APR tolerance — used by tolerance_check dict per D-05): https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/subpart-C/section-1026.22
- **CFPB Reg Z Small Entity Compliance Guide:** https://files.consumerfinance.gov/f/documents/cfpb_tila-respa-integrated-disclosure-rule_compliance-guide.pdf
- **HMDA Platform (sole oracle per D-01):** https://github.com/cfpb/hmda-platform
- **numpy_financial.rate documentation:** https://numpy.org/numpy-financial/latest/rate.html
- **numpy_financial issue #131** (architecture-dependent IRR — irrelevant to `rate`, noted for context): https://github.com/numpy/numpy-financial/issues/131

### Pattern References (Phase 7 mirrors structure)
- `lib/affordability.py:952-1109` (`evaluate_reverse`) — seed-then-refine numpy_financial pattern
- `lib/arm.py:1-489` — Pydantic model cluster + cross-field validator + per-period iteration shape
- `lib/amortize.py:295-383` (`_build_fixed_monthly`) — scalar Decimal arithmetic loop pattern
- `scripts/refi_npv.py` (Phase 6) — closest CLI shape sibling
- `scripts/arm_simulate.py` (Phase 5) — second CLI sibling for diff
- `references/refi-npv.md` (Phase 6, 630 lines) — closest references/*.md sibling for section structure + citation style + D-16 belt-and-suspenders surfaces idiom

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib.money.MONEY_CONTEXT` (prec=28) — covers Phase 7 Decimal arithmetic without escalation
- `lib.money.quantize_rate` — applied to final APR result and Decimal-power inputs (D-07)
- `lib.money.quantize_cents` — applied to `final_residual: Money` and any dollar-residual reporting
- `lib.rules.reg_z.within_apr_tolerance` — Phase 2 predicate; consumed by `tolerance_check` dict when `disclosed_apr` is supplied (D-05)
- `lib.rules.reg_z.TOLERANCE_REGULAR` (`Decimal("0.00125")` = 1/8 pp) — used as `tolerance_check.tolerance_used` for regular transactions
- `lib.rules.reg_z.TOLERANCE_IRREGULAR` — used for irregular transactions when applicable (out of v1's single-advance scope; reserved for future)
- `lib.models.Money` + `lib.models.Rate` — Annotated condecimal aliases for APRRequest / APRResponse fields
- `numpy_financial.rate` — seed source per APR-02 + RESEARCH §Finding 4
- `scripts._cli_helpers` — JSON-float gate + 6-key envelope formatter; Phase 7 adds zero new helpers (purely consumes)
- `tests/conftest.py` `arm_fixture` factory pattern (lines 73-90) — direct template for `apr_fixture`

### Established Patterns
- **Per-period scalar Decimal loop** with `localcontext(MONEY_CONTEXT)` wrapper (`lib/amortize.py:295-383`) — Phase 7's Newton-Raphson iteration follows this idiom
- **Seed-then-refine numpy_financial** (`lib/affordability.py:952-1109` `evaluate_reverse`) — Phase 7's closest precedent; generalizes single-shot `npf.pv` → multi-iteration Newton on `npf.rate` seed
- **Module docstring with LOCKED DECISION D-01..D-NN blocks** (`lib/affordability.py:1-172`) — Phase 7 lifts this verbatim; D-01..D-09 from this CONTEXT inline at top of `lib/apr.py`
- **Pydantic `ConfigDict(strict=True, frozen=True, extra="forbid")`** on every model (Phase 1 D-08; lifted in Phases 3, 4, 5, 6)
- **Discriminated union via `Field(discriminator=...)`** — NOT applicable to Phase 7 (single APRRequest shape; no mode discriminator)
- **6-key Pydantic envelope** on CLI ValidationErrors (Phase 3 WR-02; consumed via `scripts/_cli_helpers.py`)
- **Capture-as-fixture with provenance pin** (Phase 5 D-04: PNG sha256 + URL + captured_at) — adapted for code oracle: replace `screenshot_sha256` with `oracle_commit_sha`
- **Citation-coverage meta-test** (`tests/test_rules/test_citation_coverage.py` from Phase 2; `tests/test_affordability.py` SC-1..SC-5 idiom) — Phase 7 ships SC-1..SC-5 verbatim coverage tests + APR-01..APR-08 closure tests

### Integration Points
- **Imports from Phase 1:** `lib.money` (MONEY_CONTEXT, quantize_cents, quantize_rate), `lib.models` (Money, Rate)
- **Imports from Phase 2:** `lib.rules.reg_z` (within_apr_tolerance, TOLERANCE_REGULAR, TOLERANCE_IRREGULAR)
- **Imports from Phase 3:** none directly (Newton-Raphson does NOT consume `lib.amortize.build_schedule` — APR equation works on payment-schedule arrays without a fully-realized Schedule object)
- **Imports from Phase 5:** none (ARM modeling is orthogonal to APR computation in v1; ARM-aware APR is deferred)
- **Imports from Phase 6:** none (refi NPV is orthogonal)
- **Consumed by Phase 8:** stress-test parameter sweeps may invoke `solve_apr` per grid cell (rate-shock × loan amount × points)
- **Consumed by Phase 10:** SKILL.md routes `evaluate` mode "what's my APR?" requests to `scripts/apr_reg_z.py`
- **Consumed by Phase 11:** no dedicated subagent (APR is single-shot, not parameter-sweep)
- **Consumed by Phase 12:** evals harness includes APR-route prompts; expected outputs reference `lib.apr.solve_apr` numeric outputs

</code_context>

<specifics>
## Specific Ideas

- **HMDA Platform fixture generation script.** Plan 07-07 should ship a small Python shim (`scripts/_generate_hmda_apr_fixtures.py`, dev-only) that programmatically invokes the HMDA Platform's APR endpoint (Docker container or sbt task per upstream README), captures `(request, expected_apr, oracle_commit_sha)` per fixture, and writes the JSON files. This makes the 20+ captures reproducible without any manual UI driving — a meaningful improvement over Phase 5's external-tool-screenshot-PDF idiom.
- **Reg Z anchor stays anchored to regulatory value.** Plan 07's existing D-25 LOCKED decision (Wave 5 D-25 in 07-PLAN-CHECK §SC-1) has the Reg Z fixture using `expected.estimated_apr = "0.120000"` — the regulatory-publication value, not the engine-emitted value. Re-plan must preserve this. The other 20+ HMDA fixtures use engine-emitted values cross-validated against HMDA Platform per D-09.
- **`references/apr-reg-z.md` mirrors `references/refi-npv.md` structure.** 6 sections per existing PLAN-CHECK SC-5 path: §1 Overview, §2 Unit-period equation (Reg Z Appendix J), §3 Day-count + finance-charge handling (with §1026.4 enumeration table), §4 Newton-Raphson + seed strategy, §5 Convergence + dollar-residual sanity (D-06), §6 "estimated APR" literal-text rationale (project convention + §1026.18 disclosure context).
- **Re-plan instruction priority:** the existing 8 plans are 90% correct. The re-plan's diff is ~15% concentrated in:
  - Plan 07-01 (Pydantic models): reduce `day_count` Literal to `["30/360"]`; reduce `advances` to `Field(min_length=1, max_length=1)`; add `disclosed_apr: Money | None = None` optional field; add `final_residual: Money` to APRResponse; clarify `tolerance_check` only-when-supplied semantics
  - Plan 07-02 (Newton-Raphson engine): add D-06 dual-criterion convergence; document the short-odd-first-period engine-internal warning (Claude's Discretion)
  - Plan 07-04 (CLI): no changes needed (6-key envelope already specced)
  - Plan 07-06 (references doc): rename "FFIEC tool" → "HMDA Platform" throughout; add §1 forward-pointer to ROADMAP-corrected wording
  - Plan 07-07: rewrite from "FFIEC manual capture (autonomous: false)" → "HMDA Platform programmatic capture (autonomous: true)"; ship `scripts/_generate_hmda_apr_fixtures.py`; oracle JSON schema swaps `ffiec_screenshot_path/sha256` → `oracle_commit_sha`
- **Pre-replan ROADMAP / REQUIREMENTS edits (D-10) are mandatory.** Three surfaces to edit:
  1. `.planning/ROADMAP.md` Phase 7 description (line 23): replace "Newton-Raphson solver against FFIEC fixtures" with "Newton-Raphson solver against HMDA Platform fixtures"
  2. `.planning/ROADMAP.md` Phase 7 SC-2 (around line 158): replace "All 20+ FFIEC-captured fixtures..." with "All 20+ HMDA-Platform-captured fixtures..."
  3. `.planning/REQUIREMENTS.md` APR-04: replace "20+ FFIEC APR Tool capture-as-fixture tests" with "20+ HMDA Platform capture-as-fixture tests (commit-SHA pinned)"
- **deferred-items.md addition.** Append a "Phase 7 deferred" block to `.planning/phases/07-estimated-apr/deferred-items.md` (create if missing) capturing: FFIEC APRWIN as future supplemental oracle if it ever gains a programmatic surface; multi-advance / construction-loan support; actual/365 + actual/actual day-count; short odd-first-period (negative `f`) test fixtures; ARM-aware APR.

</specifics>

<deferred>
## Deferred Ideas

- **FFIEC APRWIN as supplemental oracle.** If the FFIEC publishes a programmatic API or open-sources APRWIN, capture 3-5 spot-check fixtures as a tie-out against HMDA Platform. Backlog phase.
- **Multi-advance / construction-loan APR.** Engine math is ready (U-equation form already in v1); only the Pydantic `max_length=1` bound needs relaxing. Reintroduce when a real construction loan or draw-down HELOC scenario emerges. Future phase.
- **`actual/365` + `actual/actual` day-count.** ~30 + ~50 lines of helper logic plus oracle re-capture. Reintroduce when an ARM (which sometimes uses actual/365) or treasury-style product enters scope. Future phase.
- **Short odd-first-period test fixtures (negative `f`).** Engine math supports it; v1 only tests long cases. Capture fixtures when a real loan with origination-to-first-payment < 30 days appears. Backlog.
- **ARM-aware APR (post-reset rate epochs).** Reg Z Appendix J handles this naturally as a sequence of unit-period epochs at different rates, but the v1 CLI takes a single fixed payment schedule. Promote to a Phase 8+ scope item (or ARM-aware mode in `evaluate.md` Phase 10) when ARM-evaluation use cases emerge.
- **§1026.4 finance-charge classifier.** The orchestrator-locked decision is caller-supplied `finance_charges`. If the household ever processes its own Loan Estimates programmatically, add a classifier per Reg Z §1026.4 (origination, points, broker fee, prepaid interest, MI premium classification rules). Future phase or v2 of mortgage-ops.
- **Per-fixture tolerance overrides.** v1 enforces `Decimal("0.00001")` uniformly per D-09. If a real-world precision-loss case ever requires per-fixture relaxation, revisit; until then, divergence == bug.

</deferred>

---

*Phase: 07-estimated-apr*
*Context gathered: 2026-05-03*
