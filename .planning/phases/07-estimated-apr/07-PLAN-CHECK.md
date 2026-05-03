# Phase 7: Estimated APR — Plan Check (Goal-Backward Verification)

**Verified:** 2026-05-02
**Verifier:** orchestrator-emulating gsd-plan-checker
**Plans verified:** 07-00, 07-01, 07-02, 07-03, 07-04, 07-05, 07-06, 07-07
**Source-of-truth:** ROADMAP.md Phase 7 success criteria SC-1..SC-5 + REQUIREMENTS.md APR-01..APR-08

## Verdict Summary

| Criterion / Requirement | Verdict | Notes |
|---|---|---|
| **SC-1** ($5000/36/$166.07 → 12.00% within Decimal("0.00001")) | **PASS** | Wave 5 ships fixture; Wave 2 solver targets `Decimal("0.00001")` exactly; Wave 5 test asserts SC-1 verbatim. |
| **SC-2** (20+ FFIEC fixtures pass within Decimal("0.00001")) | **CONCERN** | Wave 7 is a human checkpoint; FFIEC tool deliverability is the residual risk (RESEARCH OPEN Q4). Fallback substitution chain documented. Partial closure path documented per Phase 5 precedent. |
| **SC-3** (Newton iterations <= 50 for all fixtures, seeded from npf.rate) | **PASS** | Wave 2 hard cap encoded; Wave 5 + Wave 7 parametric tests assert iterations <= 50; APRConvergenceError raises on cap breach. APRResponse.iterations is `Field(ge=1, le=50)` — Pydantic enforces at the model level. |
| **SC-4** (User-facing strings include "estimated APR" never bare "APR" — regex test on JSON output) | **PASS** | Wave 1 D-05 enforces literal at Pydantic model boundary (`@model_validator` on APRResponse.summary); Wave 4 D-22 enforces at CLI epilog; Wave 0 + Wave 4 regex test pinned. |
| **SC-5** (references/apr-reg-z.md documents unit-period model + day-count + odd-first with citations) | **PASS** | Wave 6 ships the doc with all 6 sections; lib.apr.APRRequest docstring cites doc; Wave 0 stub flips with section-presence + cite-from check. |
| **APR-01** (lib/apr.py Newton-Raphson solver) | **PASS** | Wave 1 ships models; Wave 2 ships solver body with explicit Newton-Raphson loop. |
| **APR-02** (Newton seeded from npf.rate) | **PASS** | Wave 2 D-11 + Task 4 `_seed_apr` uses npf.rate with NaN/range fallback. Test pins exact `Decimal(str(npf.rate(...)))` equivalence on regular fixture. |
| **APR-03** (Tolerance Decimal("0.00001"), 10x tighter than Reg Z 0.005%) | **PASS** | Wave 2 D-09 + D-10 encode tolerance; Wave 5 SC-1 anchor test pins it. **Note: orchestrator brief contained a decimal-point error** ("0.005% / Decimal('0.0000125')"); RESEARCH §Finding 1 and PATTERNS §Watch-out #2 reconcile — Reg Z 1/8 pp regular is `Decimal("0.00125")` per `lib/rules/reg_z.py:62`, so `Decimal("0.00001")` is **125x tighter**, not 100x. SC-3's "10x tighter" goal is satisfied trivially. No engine-level conflict. |
| **APR-04** (20+ FFIEC fixtures) | **CONCERN** | Same as SC-2 — Wave 7 human checkpoint; FFIEC tool deliverability risk; fallback chain documented. |
| **APR-05** (Reg Z worked example fixture) | **PASS** | Wave 5 ships fixture + flips test stub. |
| **APR-06** (Output labeled "estimated APR" not "APR") | **PASS** | Same enforcement chain as SC-4. |
| **APR-07** (scripts/apr_reg_z.py JSON-in/JSON-out CLI) | **PASS** | Wave 4 ships CLI mirroring `scripts/arm_simulate.py`; subprocess round-trip test pinned. |
| **APR-08** (references/apr-reg-z.md) | **PASS** | Same as SC-5. |

**Counts:** PASS = 11, CONCERN = 2, BLOCK = 0.

## Detailed per-criterion analysis

### SC-1 — PASS

**Path to satisfaction:**
1. Wave 0 stubs `test_apr_reg_z_appendix_j_worked_example_returns_12_percent` (xfail, strict).
2. Wave 1 ships `APRRequest` model.
3. Wave 2 ships `solve_apr` body with `TOLERANCE = Decimal("0.00001")` constant
   and `Decimal("0.120000")` empirically reachable on the SC-1 fixture (RESEARCH §Worked Example 1).
4. Wave 5 ships `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` with
   `expected.estimated_apr = "0.120000"` (regulatory value, not engine-emitted —
   Wave 5 D-25 LOCKED).
5. Wave 5 flips the stub. Test asserts `abs(response.estimated_apr - Decimal("0.120000")) <= Decimal("0.00001")`.

**Risk:** if `_decimal_pow` (Wave 2 D-13) is implemented incorrectly, the
worked example may return a value off by more than 0.00001. Mitigation:
Wave 5 ships `test_decimal_pow_fractional_exponent_correctness` as a sibling
unit test that catches `_decimal_pow` regressions before they reach the
SC-1 anchor.

### SC-2 — CONCERN

**Path to satisfaction:** Wave 7 manual capture protocol. ≥20 fixtures
written to `tests/fixtures/apr/oracle/`; parametric test asserts each
within `Decimal("0.00001")`.

**Concern:** the FFIEC APR Tool (`https://www.ffiec.gov/aprwin.htm`) is
historically a Windows desktop binary; the agent cannot drive it
headlessly. Wave 7 is explicitly an `autonomous: false` human-checkpoint
plan. If FFIEC primary unreachable, the fallback chain (CFPB Rate Spread
→ Bankrate → HMDA Platform per RESEARCH §Q(d)) is documented but each
substitute is from a different implementation, and may not agree with
FFIEC to the `Decimal("0.00001")` precision SC-2 demands.

**Recommended human action:** before executing Wave 7, the operator
should verify FFIEC tool accessibility AND identify at least one
substitute that can be cross-validated against the FFIEC tool on a
single test case. If both the primary AND no substitute can deliver the
required precision, partial-closure of SC-2 is acceptable per Phase 5
precedent (ARM-06 partial), but the project should formally accept this
as a pre-execution decision via `/gsd-discuss-phase` re-entry.

**No engine-level concern** — the solver itself is correct (proven by
the Reg Z anchor + the regular-monthly Wikipedia anchor). The concern
is purely about oracle availability for cross-validation.

### SC-3 — PASS

**Path to satisfaction:**
1. Wave 0 stub `test_newton_raphson_iterations_under_50_for_all_fixtures` (xfail).
2. Wave 2 D-12 encodes `MAX_ITER = 50` constant.
3. Wave 2 D-07 (Wave 1 model) `APRResponse.iterations` is `Field(ge=1, le=50)` —
   Pydantic enforces at the model boundary; cap breach raises before
   APRResponse construction.
4. Wave 2 ships `APRConvergenceError` (`ValueError` subclass) on cap breach.
5. Wave 5 + Wave 7 parametric tests iterate all fixtures and assert
   `response.iterations <= 50`.
6. Wave 4 CLI catches APRConvergenceError + surfaces as 6-key envelope
   (operator-visible failure mode).

**No risk** — multiple defense layers (constant, Pydantic field,
exception, parametric test).

### SC-4 — PASS

**Path to satisfaction:**
1. Wave 1 D-05 `APRResponse._summary_contains_literal_estimated_apr`
   `@model_validator` enforces:
   - `"estimated APR" in self.summary` — required substring
   - `re.search(r'\bAPR\b(?!\s*tolerance)', summary.replace("estimated APR", ""))` is None — no bare "APR"
2. Wave 4 D-22 enforces in CLI epilog text + module docstring.
3. Wave 0 + Wave 4 stubs flipped:
   - `test_apr_response_uses_literal_estimated_apr_text` (Wave 4): regex
     test on actual solver output.
4. Wave 2 `solve_apr` constructs summary via f-string template
   `f"estimated APR: {pct}% (...)"` — compile-time guarantee.

**Risk (low):** if `tolerance_check` dict ever contains a string with
bare "APR", that value is in a `dict[str, Any]` field, not in `summary`,
so the model validator does NOT inspect it. **Mitigation:** Wave 1
`tolerance_check` shape uses keys "within_tolerance", "tolerance_used",
"regulation" — no "APR" literal in any value. The string "12 CFR §1026.22(a)(2)"
is the only place "APR" might appear (in URL or regulatory citation
text). The regex `\bAPR\b(?!\s*tolerance)` matches "APR " followed by
non-"tolerance" tokens; `tolerance_check` is OUT of the regex's scope
(only `summary` is checked). This is by design — regulatory citations
necessarily contain "APR" and labeling them "estimated APR" would be
incorrect.

### SC-5 — PASS

**Path to satisfaction:**
1. Wave 6 ships `references/apr-reg-z.md` with 6 required sections.
2. Wave 6 modifies `lib.apr.APRRequest.__doc__` to cite the doc.
3. Wave 0 + Wave 6 stub `test_references_apr_reg_z_doc_present_with_required_sections`
   asserts both (file exists with sections + lib.apr.py grep cites doc).
4. RESEARCH §Citations verifies all URLs against eCFR + CFPB on 2026-05-02.

**No risk.**

### APR-01..APR-08 — see table; same paths as SCs they map to

---

## Cross-cutting concerns

### Decimal-vs-float discipline (load-bearing for SC-1)

Wave 2 D-11 + D-13 encode the rule: float only at the `_seed_apr` boundary
(`npf.rate` returns float; cast through `Decimal(str(...))` once). Newton
iteration is pure Decimal in `MONEY_CONTEXT`. Pinned by:
- `mypy --strict` (no float in iteration code paths)
- Wave 5 `test_decimal_pow_fractional_exponent_correctness`
- Wave 5 SC-1 anchor (would fail if float drift exceeded `Decimal("0.00001")`)

**No risk.** RESEARCH §Finding 7 also notes that even pure float WOULD
satisfy SC-1 in practice (`np.float64` precision ~15-17 digits >>
required 5 digits), so Decimal is conservative belt-and-suspenders.

### Plan execution ordering

Plans declare `depends_on:` frontmatter forming a strict chain:
00 → 01 → 02 → 03 → 04 → 05 → 06 → 07. The project config
(`parallelization: false`) requires sequential execution; even if parallel
were enabled, the dependency chain forces the same order.

### Phase 5 baseline preservation

Every wave's Verify Block runs `pytest -q | tail -5` and asserts ≥432
passed (Phase 5 baseline). Phase 7 is **purely additive** — it touches:
- 1 NEW lib file (`lib/apr.py`)
- 1 NEW script (`scripts/apr_reg_z.py`)
- 1 NEW test file (`tests/test_apr.py`)
- 1 NEW reference doc (`references/apr-reg-z.md`)
- 24+ NEW fixture files (4 hand-calc + 20+ FFIEC)
- 1 conftest.py extension (additive — `apr_fixture` fixture)

No modifications to Phase 1-5 production code. **No regression risk.**

---

## Concerns and Open Questions for the human

1. **CONCERN-1 (SC-2 / APR-04): FFIEC tool deliverability.** The plans
   document a fallback chain, but the fallback substitutes (CFPB Rate
   Spread, Bankrate, HMDA Platform) are independent implementations that
   may not agree with the FFIEC tool to `Decimal("0.00001")` precision.
   **Recommended human action:** before Wave 7 execution, verify FFIEC
   primary tool accessibility OR formally accept partial-closure of
   SC-2 via `/gsd-discuss-phase`. Mirrors Phase 5 BLOCKER-1 precedent.

2. **TOLERANCE RECONCILIATION (informational, NOT a blocker):** the
   orchestrator brief stated Reg Z 1/8 pp regular = `0.0125%`; the
   correct value is `0.125%` = `Decimal("0.00125")` fractional (per
   `lib/rules/reg_z.py:62`, already shipped Phase 2). Net effect:
   `Decimal("0.00001")` is 125x tighter than Reg Z (not 100x). The
   "10x tighter" ROADMAP goal is satisfied with significant headroom.
   **No plan revision needed** — the SC-1 tolerance and the engine
   tolerance both correctly use `Decimal("0.00001")`. RESEARCH §Finding 1
   and PATTERNS §Watch-out-for #2 document the correction for posterity.

3. **OPEN Q (Wave 5 / Wave 6):** Should the Wave 5 hand-calc fixtures
   ship with engine-emitted `expected.estimated_apr` values OR with
   regulatory-publication values where they exist? **Plan decision (D-24
   + D-25):** SC-1 anchor uses the regulatory `0.120000`; sibling fixtures
   use engine-emitted (consistent with Phase 4 04-06 idiom). Documented.

4. **OPEN Q (Wave 4 D-22):** Should `tolerance_check` dict values be
   inspected by the literal-text invariant? **Plan decision:** NO —
   regulatory citations necessarily contain "APR"; labeling them
   "estimated APR" would be incorrect. Documented in SC-4 risk note.

## Final Verdict

**Phase 7 plans PASS goal-backward verification with 2 CONCERN items, 0 BLOCK items.**

Both CONCERNs (SC-2 and APR-04 — same root cause: FFIEC deliverability)
have documented mitigation paths and partial-closure precedent from
Phase 5. The plans are **executable** as-is; the only required human
action before Wave 7 is to verify FFIEC tool accessibility.

The Wave 0-6 chain is fully autonomous (`autonomous: true`); Wave 7 is
a human checkpoint (`autonomous: false`).

Recommendation: **proceed with execution of Wave 0-6**; pause for human
gate before Wave 7.
