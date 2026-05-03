# Phase 7: Estimated APR (Reg Z Appendix J) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 07-estimated-apr
**Areas discussed:** Plans-exist disposition, FFIEC oracle strategy, FFIEC sample capture, HMDA delta policy, Day-count convention scope, Multi-advance support, APRResponse schema surface

**Triggering context:** Phase 7 plans (07-00 through 07-07) were drafted on 2026-05-02 in a parallel orchestration sweep without going through `/gsd-discuss-phase`. PLAN-CHECK identified 2 CONCERNs (both rooted in FFIEC tool deliverability for SC-2 / APR-04). User invoked `/gsd-discuss-phase 07` to formally lock decisions before re-plan.

---

## Plans-exist disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Discuss + replan after | Capture decisions in CONTEXT.md, then run /gsd-plan-phase 07 to refresh plans | ✓ |
| Discuss without replan | Capture CONTEXT.md but leave existing plans untouched | |
| View concerns first | Walk through 2 PLAN-CHECK concerns before deciding | |
| Cancel | Exit and revisit later | |

**User's choice:** Discuss + replan after.
**Notes:** PLAN-CHECK explicitly recommends `/gsd-discuss-phase` re-entry to formally accept partial-closure for SC-2 (FFIEC deliverability). User chose the cleanest path: discuss, then re-plan.

---

## Gray areas selected for discussion

| Option | Description | Selected |
|--------|-------------|----------|
| FFIEC oracle strategy | SC-2 demands 20+ FFIEC fixtures; FFIEC APRWIN is Windows binary | ✓ |
| Day-count convention scope | 30/360 only vs add actual/365 + actual/actual | ✓ |
| Multi-advance / construction-loan support | Single advance vs multi-advance in v1 | ✓ |
| APRResponse schema surface area | Which diagnostic fields belong in v1 schema | ✓ |

**User's choice:** All four — full lock-down before replanning.

---

## FFIEC oracle strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Pivot to HMDA Platform as primary oracle | cfpb/hmda-platform open-source Reg Z impl as v1 oracle (reproducible, scriptable). FFIEC optional spot-check on 1-3 cases. SC-2 reframed: 20+ fixtures cross-validated against HMDA Platform. Plan 07-07 becomes autonomous. | ✓ |
| FFIEC primary, multi-source fallback | Try FFIEC APRWIN manually (5-10 captures on Windows VM), fall back to CFPB Rate Spread + HMDA Platform + Bankrate. Mixed-source per-fixture. Risk: cross-source delta exceeds Decimal('0.00001'). | |
| Pre-accept partial closure | Ship 5-10 hand-calc + HMDA fixtures; formally accept SC-2 partial-closure (mirror Phase 5 ARM-06 partial). Move SC-2 full closure to backlog. | |
| Drop the count requirement | Replace '20+' with '3 hand-calc + 3 cross-source' (6 total). Update ROADMAP SC-2 + APR-04 verbatim. | |

**User's choice:** Pivot to HMDA Platform as primary oracle.
**Notes:** Reframes SC-2 + APR-04 around a reproducible, code-based oracle. Plan 07-07 transitions from human-checkpoint to autonomous via a fixture-generation shim script. Requires ROADMAP.md + REQUIREMENTS.md edits before re-plan (D-10 in CONTEXT.md).

---

## FFIEC sample capture (sub-decision under HMDA pivot)

| Option | Description | Selected |
|--------|-------------|----------|
| Skip FFIEC entirely | HMDA Platform IS the cfpb's Reg Z impl — same source. Spot-checking adds friction without insight. | ✓ |
| Capture 1 FFIEC sample as sanity tie-out | One APRWIN run on Windows VM for the Reg Z worked example. Belt-and-suspenders. Wave 7 stays 1-fixture human checkpoint. | |
| 3 FFIEC samples spanning the feature space | 1 fixed-rate + 1 odd-first-period + 1 multi-advance. Wave 7 stays human-checkpoint with 3 captures. | |

**User's choice:** Skip FFIEC entirely.
**Notes:** Locked as D-02 in CONTEXT.md. APRWIN is explicitly out of scope as an oracle for v1.

---

## HMDA Platform delta policy

| Option | Description | Selected |
|--------|-------------|----------|
| Engine is wrong — fix it | HMDA Platform is ground truth for Reg Z Appendix J. Any delta > Decimal('0.00001') is a regression. Test fails loudly. Investigation prioritizes engine bug. | ✓ |
| Document delta, ship with looser tolerance per-fixture | Allow per-fixture tolerance override (default Decimal('0.00001'), can widen to Decimal('0.0001') with documented rationale). Risk: erodes SC-1 tightness over time. | |
| Investigate before deciding | First-divergence triggers forensic gsd-debug session; outcome locks the policy. | |

**User's choice:** Engine is wrong — fix it.
**Notes:** Locked as D-09 in CONTEXT.md. Per-fixture tolerance overrides explicitly forbidden in v1.

---

## Day-count convention scope

| Option | Description | Selected |
|--------|-------------|----------|
| 30/360 only — reject others at Pydantic boundary | APRRequest.day_count is Literal['30/360'] with default; passing other values raises validation error. Smallest correct surface. Defer actual/365 + actual/actual when there's a real ARM/treasury use case. | ✓ |
| 30/360 + actual/365 | Covers most fixed-rate + most ARMs. actual/actual deferred. ~30 lines of helper logic for 30.4167-day approximation. | |
| All three conventions | Full Reg Z coverage. Risk: actual/actual requires relativedelta-driven actual_days_in_unit_period computation that's hard to validate without an oracle. | |

**User's choice:** 30/360 only.
**Notes:** Locked as D-03 in CONTEXT.md. Personal-use mortgages are 30/360 in practice. Future phase relaxes the Literal when ARM/treasury demand drives it.

---

## Multi-advance / construction-loan support

| Option | Description | Selected |
|--------|-------------|----------|
| Single advance only in v1 | APRRequest.advances accepts exactly 1 entry (Pydantic min_length=1, max_length=1). Engine still uses U-equation form. Smaller test surface, faster to ship. | ✓ |
| Multi-advance in v1, capped at 5 entries | advances: list with min_length=1, max_length=5. Ships Example 3 as test fixture. ~50 extra lines of engine code. | |
| Unbounded multi-advance | advances: list with no max bound. Fullest Reg Z coverage. Risk: convergence behavior degrades with many irregular advances; testing surface explodes. | |

**User's choice:** Single advance only in v1.
**Notes:** Locked as D-04 in CONTEXT.md. PROJECT.md scope is the Pachulski household — no construction loan, no draw-down HELOC. Engine schema already uses U-equation form so relaxing the bound later is a config change, not a rewrite.

---

## APRResponse schema surface area (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| iterations: int | Required for SC-3 enforcement. Pydantic Field(ge=1, le=50). Cheap to surface. | ✓ |
| final_residual: Money | abs(f(i_final)) in dollars after convergence. Useful debug signal. | ✓ |
| tolerance_check dict (when disclosed_apr supplied) | APRRequest.disclosed_apr: Money | None optional. When supplied, response surfaces {within_tolerance, tolerance_used, regulation}. Composes Phase 2 lib.rules.reg_z.within_apr_tolerance. | ✓ |
| Convergence dollar-residual sanity (engine-internal) | Inside solver, require abs(f(i)) <= Decimal('0.01') AND rate-tolerance for convergence. Prevents 'rate stalled but residual huge' edge case. | ✓ |

**User's choice:** All four.
**Notes:** Locked as D-05 (the three response-surface fields) and D-06 (engine-internal dual-criterion convergence) in CONTEXT.md. Full diagnostic surface, no second pass needed when a fixture deviates.

---

## Claude's Discretion

The following sub-decisions were made by Claude based on RESEARCH defaults rather than user discussion (documented in CONTEXT.md `<decisions>` § Claude's Discretion):

- **Odd-first-period: long case only in v1.** Engine math accepts negative `f` (short first period); v1 fixtures cover only `f ∈ [0, 1)`. Engine emits `warnings.warn("short odd-first-period: not cross-validated in v1")` when invoked with a short first period. Promote to v2 with HMDA Platform captures when a real loan with a short first period emerges.
- **Newton iteration logging.** Engine emits `logging.debug(...)` per iteration with `(iteration, current_rate, residual)`. Off by default; surfaces under `LOG_LEVEL=DEBUG`. Not exposed in APRResponse.
- **Decimal-power helper.** `(base.ln() * exponent).exp()` route under `MONEY_CONTEXT.prec=28` (RESEARCH §Finding 7). No `prec=50` localcontext escalation.
- **`solve_apr` failure mode.** Raise `APRConvergenceError(ValueError)` with iteration count + last residual in message. CLI catches via 6-key envelope and exits non-zero.

## Deferred Ideas

- FFIEC APRWIN as supplemental oracle (if it ever gains a programmatic surface)
- Multi-advance / construction-loan APR (engine ready; only Pydantic bound needs relaxing)
- `actual/365` + `actual/actual` day-count conventions
- Short odd-first-period test fixtures (negative `f`)
- ARM-aware APR (post-reset rate epochs)
- §1026.4 finance-charge classifier (currently caller-supplied per orchestrator lock)
- Per-fixture tolerance overrides (v1 enforces `Decimal("0.00001")` uniformly)
