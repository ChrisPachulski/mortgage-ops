"""Phase 7 Estimated APR — Reg Z Appendix J Newton-Raphson solver (Pydantic boundary).

Phase 7 builds an "estimated APR" engine on top of Phase 3 amortization. Wave 1
(this plan) ships ONLY the Pydantic v2 boundary models (APRRequest,
AdvanceScheduleEntry, PaymentScheduleEntry, APRResponse) plus a `solve_apr`
stub that raises NotImplementedError. Wave 2 (Plan 07-02) fills the
Newton-Raphson body. Wave 4 (Plan 07-04) ships the JSON-in / JSON-out CLI
at scripts/apr_reg_z.py.

Phase-7 consumer note: lib/rules/reg_z.py:43-47 already references this
module — `within_apr_tolerance(disclosed, actual, is_irregular)` is the
predicate Phase 7 calls when APRRequest.disclosed_apr is supplied (see
APRResponse.tolerance_check). Phase 7 keeps the "estimated APR" label
because mortgage-ops does not make commercial Reg Z disclosures (ROADMAP
SC-4); the solver is a calc, not a disclosure.

Requirements covered (Plan 07-01 partial; full closure across Waves 2-7):
  APR-01: lib/apr.py Newton-Raphson solver against Reg Z Appendix J
          unit-period equation (this plan: model surface + stub; Wave 2 body).
  APR-02: Newton-Raphson seeded from npf.rate (Wave 2).
  APR-03: Convergence tolerance Decimal("0.00001") (Wave 2).
  APR-04: 20+ HMDA Platform capture-as-fixture cross-validation (Wave 7).
  APR-05: Reg Z Appendix J Example J-1 worked example fixture (Wave 5).
  APR-06: User-facing output uses literal "estimated APR" (this plan
          enforces at the Pydantic boundary via D-05).
  APR-07: scripts/apr_reg_z.py JSON-in / JSON-out CLI (Wave 4).
  APR-08: references/apr-reg-z.md unit-period model + day-count
          conventions documentation (Wave 6).

LOCKED DECISIONS (carried from .planning/phases/07-estimated-apr/07-CONTEXT.md):

- D-01: All four boundary models use ConfigDict(strict=True, frozen=True,
        extra="forbid"). Phase 1 D-08 inheritance — every Pydantic boundary
        in mortgage-ops uses the same trio.

- D-02: APRRequest.day_count defaults to "30/360" per FFIEC tool default
        + RESEARCH §Q(b). The Literal accepts {"30/360", "actual/365",
        "actual/actual"}; v1 cross-validation only covers 30/360 (Wave 7
        captures), but the type surface accepts all three so future ARM /
        treasury phases can extend without a model bump.

- D-03: APRRequest.unit_periods_per_year defaults to 12 (monthly
        mortgage). Settable in [1, 365] for non-monthly products. Phase 8+
        stress-paths may use 26 for biweekly.

- D-04: APRRequest.finance_charges is REQUIRED and CALLER-SUPPLIED
        (orchestrator-locked decision; documented in
        references/apr-reg-z.md §3). The engine subtracts finance_charges
        from loan.principal to form amount_financed per Reg Z §1026.18(b).
        It does NOT classify which closing costs qualify as §1026.4
        finance charges — that determination belongs to the caller.

- D-05: APRResponse.summary literal-text invariant is enforced at the
        Pydantic model boundary via @model_validator(mode="after"), NOT
        only at the CLI. Constructing APRResponse(summary="APR is 7%")
        raises ValidationError. The validator (a) requires the literal
        substring "estimated APR" to appear and (b) forbids any bare
        "APR" word (regex \\bAPR\\b) outside the allowed phrases
        "estimated APR" and "APR tolerance". This pins ROADMAP SC-4 at
        the deepest possible boundary.

- D-06: APRRequest.advance_schedule MUST contain at least one advance at
        unit_period_offset=0 with unit_period_fraction=0 (the t=0
        advance — Reg Z Appendix J §(b)(2)). Reverse-mode "amount-financed
        only" callers pass a single entry
        AdvanceScheduleEntry(unit_period_offset=0,
                             amount=loan.principal - finance_charges).
        Cross-field invariant enforced via
        APRRequest._advance_schedule_has_t0_advance.

- D-07: APRResponse.iterations is Field(ge=1, le=50). Pydantic enforces
        ROADMAP SC-3's 50-iteration cap at the model layer; the solver
        MUST raise APRConvergenceError BEFORE constructing the response
        when the cap is exceeded (so a malformed response with iterations
        > 50 cannot be emitted by the engine — defense in depth against a
        future bug).

- D-08: APRResponse.tolerance_check is dict[str, Any] | None (NOT a typed
        Pydantic submodel). Rationale: keep the schema flexible for
        Phase 8 / Phase 12 extensions (e.g., adding "computed_at" or
        "regulation_subsection" without a model bump). Documented field-by-
        field in the APRResponse.tolerance_check docstring; Wave 4 (CLI)
        documents the canonical shape in scripts/apr_reg_z.py --help.

References (canonical URLs verified 2026-05-02 in 07-RESEARCH.md):
- 12 CFR Part 1026 Appendix J (Reg Z APR computation):
  https://www.ecfr.gov/current/title-12/chapter-X/subchapter-C/part-1026/appendix-J-to-part-1026
- 12 CFR §1026.17(c)(4) (basis of disclosures + odd first period)
- 12 CFR §1026.18(b) and (e) (amount-financed + APR disclosure label)
- 12 CFR §1026.22(a)(2)-(a)(3) (APR tolerance — consumed by tolerance_check)
- HMDA Platform (sole oracle per CONTEXT D-01):
  https://github.com/cfpb/hmda-platform
"""

from __future__ import annotations
