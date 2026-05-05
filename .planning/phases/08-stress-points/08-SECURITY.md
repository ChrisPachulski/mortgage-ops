---
phase: 08
slug: stress-points
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-04
---

# Phase 08 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI argv → JSON parser | `scripts/stress_test.py` and `scripts/points_breakeven.py` accept `--input <path>` and read user-supplied JSON | Decimal-string money/rate fields; user-controlled file path |
| JSON → Pydantic v2 model | `TypeAdapter(StressRequest \| PointsRequest).validate_json(raw)` at the boundary | Structured loan/rate/scenario payload |
| Pydantic model → `lib.stress` / `lib.points` engines | Discriminator-dispatched `evaluate(req)` | Validated, frozen, strict-typed Decimal payload |

No new external network surface. No new auth boundaries. No new persistence layer (DuckDB lands Phase 9). No new subprocess invocation outside the test harness.

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| _none_ | — | — | — | — | — |

No `<threat_model>` block was authored in any of the seven Phase 8 PLAN.md files (08-00..08-06), and every SUMMARY.md `## Threat Flags` section explicitly declares "None" with substantive justification (see Inherited Controls below). Phase 8 is composed entirely over Phase 3 / 4 / 5 / 6 / 7 surfaces whose threat models already cleared their respective `/gsd-secure-phase` audits.

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Inherited Controls

Phase 8 inherits the following load-bearing controls from prior phases without modification:

| Control | Origin | Surface in Phase 8 |
|---------|--------|--------------------|
| D-19 JSON-float gate (`scripts/_cli_helpers.find_json_float_loc` + `make_decimal_type_envelope`) | Phase 5 D-19 / Phase 7 D-19 | Both new CLIs run the float-gate BEFORE Pydantic validation; verified by UAT Test 7 (6-key envelope, exit 2, `ctx.class=="Decimal"`) |
| Pydantic strict mode + `extra='forbid'` + `frozen=True` on every BaseModel | Project doctrine since Phase 1 | All 11 new models in `lib/stress.py` + `lib/points.py` carry `ConfigDict(strict=True, frozen=True, extra='forbid')` per Plan 08-01 patterns-established |
| WR-02 Decimal-only money discipline | Phase 1 D-04 / CONVENTIONS.md | `condecimal(max_digits=14, decimal_places=2)` at every boundary; no float math in `lib/stress.py` or `lib/points.py` |
| `args.input.read_text()` file-read pattern | Phase 3 scripts/amortize.py | Both new CLIs reuse this pattern verbatim; OS-level path validation is the user's responsibility (same trust model as the prior 5 CLIs) |
| Lazy-import discipline (D-18) | Phase 5 D-18 / Phase 7 D-19 | `--help` does not import `lib.stress`, `lib.points`, `lib.amortize`, `lib.affordability`, `lib.arm`, or `numpy_financial`; verified by tests `test_cli_stress_help_does_not_import_lib_stress` and `test_pnts_03_cli_help_does_not_import_lib_points_and_rejects_float` |
| CLI-shortcut overlay string-preservation contract (D-04-02) | New in Phase 8 Plan 08-04 | `_parse_decimal_list` returns `list[str]` (no float coercion at argparse layer); the overlay block injects strings into the parsed JSON dict before `json.dumps` re-serializes; the float-gate runs immediately after and would catch any accidental float coercion |
| `xfail(strict=True)` regression gate (D-00-02 / Phase 5 T-05-10) | Phase 5 D-09 / Phase 7 D-00-02 | All 18 Wave-0 stubs carried `strict=True`; flipping a stub without removing the decorator triggers XPASS at CI |

---

## Accepted Risks Log

No accepted risks. All identified Phase 8 surfaces are either (a) covered by inherited controls listed above or (b) expressly out-of-scope per SUMMARY justification.

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| _none_ | — | — | — | — |

---

## Per-Plan Threat Flag Justifications

Each Phase 8 SUMMARY.md `## Threat Flags` section declares "None" with the following substantive reasoning:

| Plan | Surface Type | Justification |
|------|--------------|---------------|
| 08-00 | Test scaffolding | xfail-strict stubs only; no production code modified; no new network/auth/schema surface |
| 08-01 | Pydantic models | Type-contract only; no I/O, no network, no auth, no persistence |
| 08-02 | Pure-engine composition | Composes Phase 3 `build_schedule` + Phase 4 `affordability.evaluate` + Phase 5 `build_arm_schedule`; no new attack surface |
| 08-03 | Pure-math engine | `simple_breakeven` + `npv_breakeven` + `_derive_monthly_savings`; no I/O, no network. The Rule-2 type-contract relaxation (Money → signed Decimal on three fields) preserves `max_digits=14 + decimal_places=2 + strict=True`; only the `ge=0` lower bound is dropped to enable the documented rate-up edge case |
| 08-04 | Thin CLI wrappers | Both new scripts reuse the established `args.input.read_text()` trust pattern from the prior 5 CLIs; CLI-shortcut overlay block is gated by the float-gate that runs immediately after re-serialization (T-04-overlay covered by inherited D-19 control) |
| 08-05 | Fixtures + tests | 14 static JSON files consumed by the test suite via `stress_fixture`/`points_fixture` loaders; citation-coverage meta-test uses standard-library `json` only |
| 08-06 | Documentation | Reference Markdown docs + module-docstring updates + `--help` epilog appends; no executable code paths |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-04 | 0 | 0 | 0 | /gsd-secure-phase 08 (manual artifact-driven verification — no PLAN.md threat model existed; auditor spawn skipped per Step 3 `threats_open: 0` short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer) — N/A: zero threats registered
- [x] Accepted risks documented in Accepted Risks Log — N/A: no accepted risks
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-04
