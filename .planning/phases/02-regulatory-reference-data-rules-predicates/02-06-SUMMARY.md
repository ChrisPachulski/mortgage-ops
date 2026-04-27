---
phase: 02-regulatory-reference-data-rules-predicates
plan: 06
subsystem: rules-reference-data
tags: [atr-qm, qualified-mortgage, 12-cfr-1026-43, cfpb-final-rule-2020-12, safe-harbor, reg-z, 12-cfr-1026-22, apr-tolerance, decimal-discipline, predicate-template, statutory-constants-in-code, locked-decisions, pitfall-11-decimal-exactness]

# Dependency graph
requires:
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 01
    provides: lib/rules/_loader.py (load_reference + StaleReferenceWarning + MissingReferenceFieldError), tests/test_rules/test_citation_coverage.py (RUL-12/RUL-13 meta-test), tests/test_reference/test_schema.py (REF-09 meta-test), per-predicate fixture convention, three-string docstring contract
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 04
    provides: Plain-Decimal-vs-Pydantic-result decision rule (RUL-09 returns plain bool — this plan extends the rule to bool-returning predicates: structured Pydantic remains for predicates returning >1 conceptually-independent value), Two-boolean encoding for date-range regulatory tests (informs the LienPosition Literal-typed input for atr_qm), FilingStatus Literal scoping precedent (informs LienPosition module-scoping in atr_qm.py)
  - phase: 02-regulatory-reference-data-rules-predicates
    plan: 05
    provides: Statutory-constants-in-code idiom (HPA 0.78 / 0.80 LTV per 12 USC §4902 — directly reused for Reg-Z tolerances 1/8 / 1/4 percentage point per 12 CFR §1026.22(a)(2)/(a)(3)); composition-via-add-ons / two-helper-function pattern (informs the _spread_passes + _threshold_pp helper structure in atr_qm.py)
  - phase: 01-foundations-money-discipline
    provides: Decimal-from-string discipline; abs/subtract pattern with no float arithmetic (Pitfall 11 escape)
provides:
  - REF-`atr-qm-thresholds.yml` — data/reference/atr-qm-thresholds.yml (CFPB Q4 2025 combined Reg Z thresholds adjustment; effective 2025-11-01; 2026-indexed loan-amount tiers $110,260 + $66,156; General-QM thresholds 2.25/3.5/6.5 pp first-lien + 3.5/6.5 pp subordinate; Safe-Harbor thresholds 1.5/3.5/6.5 pp first-lien + 3.5/6.5 pp subordinate; quoted-string numerics + unquoted ISO date)
  - RUL-09 — lib/rules/atr_qm.py with general_qm_passes(apr, apor, loan_amount, lien_position) -> bool + safe_harbor_qm_passes(...) -> bool; LienPosition Literal alias module-scoped; private _spread_passes + _threshold_pp helpers; calls load_reference("atr-qm-thresholds")
  - RUL-10 — lib/rules/reg_z.py with within_apr_tolerance(disclosed_apr, actual_apr, is_irregular_transaction) -> bool; module-level Final[Decimal] constants TOLERANCE_REGULAR=Decimal("0.00125") + TOLERANCE_IRREGULAR=Decimal("0.0025") with §1026.22(a)(2)/§1026.22(a)(3) inline citation comments; pure Python (NO load_reference call per CONTEXT.md D-02)
  - 10 ATR/QM fixtures — each (lien × loan-amount-band) cell + tier boundaries at $66,156 and $110,260 (inclusive-lower-bound semantic) + APR-exactly-at-threshold (Pitfall 11) + Safe-Harbor case
  - 5 Reg-Z fixtures — regular within / regular outside / irregular within / irregular outside / regular exactly-at-tolerance (`<=` boundary + Decimal exactness pin)
  - 24 net new tests pass (14 atr_qm + 10 reg_z); +4 new citation-coverage parametrized cases (atr_qm × 2, reg_z × 2); +1 new schema parametrized case (atr-qm-thresholds)
  - Phase 2 closure of the 11-predicate library: with 02-05's RUL-02/03/05 and this plan's RUL-09/10, all 13 RUL-* requirements (RUL-01..13 minus the meta-tests RUL-12/RUL-13 which are filesystem-introspecting) are now shipped
affects: [02-07-citation-coverage-audit, 04-affordability, 07-apr]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Statutory-constants-in-code idiom REUSED from 02-05 conventional_pmi: when regulatory thresholds are statutory and unchanging (Reg-Z tolerance text per 12 CFR §1026.22(a)(2)/(a)(3) has not changed for decades), embed as Final[Decimal] module constants with citation comments. NO YAML lookup, NO load_reference call. CONTEXT.md D-02 anchors this for Reg-Z. The reusable pattern: any predicate whose values are statutory and have been unchanged for years should follow this idiom; predicates whose values are CFPB-indexed annually (like atr_qm loan-amount tiers $110,260/$66,156) DO get a YAML."
    - "Threshold-unit convention for human-readability: YAML body stores thresholds as PERCENTAGE POINTS (e.g. '2.25' = 2.25 pp) so the YAML body matches CFPB's published table 1:1; predicate divides by Decimal('100') at consumption time to compare against the fractional spread `apr - apor`. Reusable for any future tiered threshold predicate where YAML readability against the regulator's published table matters more than raw fractional storage."
    - "Inclusive-lower / exclusive-upper tier-boundary semantics with explicit boundary fixtures: tier boundaries at $66,156 and $110,260 are pinned by `atr_qm_loan_amount_boundary_*.json` fixtures with explicit `# bands: low: <66156, mid: 66156<=x<110260` comments. Any future regression that flips `>=` to `>` on the lower bound -> red boundary test. Reusable for any tiered-amount predicate where boundary semantics need a regression-defending pin."
    - "Pitfall 11 (Decimal exactness at boundary) pinned by exactness assertion + predicate call in same test: `test_apr_exactly_at_general_qm_threshold` and `test_regular_exactly_at_tolerance_passes` both assert `apr - apor == Decimal('0.0225')` / `abs(disclosed - actual) == Decimal('0.00125')` BEFORE calling the predicate. This documents the assumption (Decimal arithmetic gives exact zero-drift difference) and pins it; any future refactor that introduces float arithmetic anywhere in the call chain breaks the exactness assertion."
    - "Plain-bool-return for binary-classifier predicates: when a predicate answers a yes/no question (does this loan pass General-QM? is this APR within tolerance?), return plain bool. Mirrors RUL-11's plain-Decimal-return convention for stateless lookups. Structured Pydantic results remain reserved for predicates bundling >1 conceptually-independent value (USDAEligibilityResult / FreddieEligibilityResult / MIPResult / ResidualIncomeResult)."
    - "LienPosition Literal alias scoped to atr_qm.py (NOT promoted to lib/rules/types.py). Mirrors FilingStatus scoping in 02-04 + LoanPurpose/Occupancy scoping in 02-05. One-predicate-per-citation discipline trumps DRY for small Literal aliases. Promotion deferred until a second consumer needs LienPosition (RUL-10 reg_z does NOT take lien_position; APR tolerance is lien-agnostic)."

key-files:
  created:
    - data/reference/atr-qm-thresholds.yml (REF for RUL-09; effective 2025-11-01; 5 threshold rows covering first-lien high/mid/low + subordinate high/low)
    - lib/rules/atr_qm.py (RUL-09 — general_qm_passes + safe_harbor_qm_passes + LienPosition Literal + _spread_passes + _threshold_pp helpers)
    - lib/rules/reg_z.py (RUL-10 — within_apr_tolerance + TOLERANCE_REGULAR + TOLERANCE_IRREGULAR Final[Decimal] constants)
    - tests/test_rules/test_atr_qm.py (14 hand-calc tests covering all (lien × band) cells + boundaries + exactly-at-threshold + Safe-Harbor + 3 fail-loud guards)
    - tests/test_rules/test_reg_z.py (10 hand-calc tests covering regular/irregular × within/outside + exactly-at-tolerance + symmetry + constants + 2 fail-loud guards)
    - tests/fixtures/rules/atr_qm_first_lien_high_loan_within.json
    - tests/fixtures/rules/atr_qm_first_lien_high_loan_outside.json
    - tests/fixtures/rules/atr_qm_first_lien_mid_loan_within.json
    - tests/fixtures/rules/atr_qm_first_lien_low_loan_within.json
    - tests/fixtures/rules/atr_qm_subordinate_lien_high_within.json
    - tests/fixtures/rules/atr_qm_subordinate_lien_low_within.json
    - tests/fixtures/rules/atr_qm_loan_amount_boundary_66156.json
    - tests/fixtures/rules/atr_qm_loan_amount_boundary_110260.json
    - tests/fixtures/rules/atr_qm_apr_exactly_at_threshold.json
    - tests/fixtures/rules/atr_qm_safe_harbor_first_lien_high.json
    - tests/fixtures/rules/reg_z_regular_within_tolerance.json
    - tests/fixtures/rules/reg_z_regular_outside_tolerance.json
    - tests/fixtures/rules/reg_z_irregular_within_tolerance.json
    - tests/fixtures/rules/reg_z_irregular_outside_tolerance.json
    - tests/fixtures/rules/reg_z_regular_exactly_at_tolerance.json
  modified: []

key-decisions:
  - "RUL-09 atr_qm.py DOES use a YAML (atr-qm-thresholds.yml) because CFPB indexes the loan-amount tiers ANNUALLY ($110,260 + $66,156 are 2026-indexed; will become $111k+/$67k+ in 2027). Annual refresh = YAML edit + bump effective + commit, no code change. This is the OPPOSITE choice from RUL-10 (which is pure-Python because Reg-Z tolerance text is unchanged for decades). The disambiguator: 'do regulator-published values change annually?' YES -> YAML; NO -> Final[Decimal] in code with citation. Reusable choice criterion for any future predicate."
  - "RUL-09 Q4 2025 publication pin (effective: 2025-11-01) is load-bearing: the 2024-11 publication carried 2025-indexed tiers ($107,650 / $64,590) and is therefore STALE for our 2026-indexed must_haves claim. Pinning the wrong publication would make the YAML body's 2026-indexed values inconsistent with their citation trail. Plan 02-07 audit gate should verify this lockstep across annual refreshes — the Q4 of year N publication carries year (N+1)-indexed tiers, not year N-indexed."
  - "RUL-09 LienPosition Literal alias module-scoped (NOT promoted to lib/rules/types.py). RUL-10 reg_z is APR-tolerance-only and does NOT take a lien_position parameter (Reg-Z tolerance is lien-agnostic per §1026.22). No second consumer exists yet; promotion deferred. Mirrors FilingStatus scoping in 02-04 + LoanPurpose/Occupancy scoping in 02-05."
  - "RUL-09 returns plain bool (not Pydantic). Mirrors RUL-11 plain-Decimal-return convention for stateless single-value lookups. Choice criterion (per 02-04): structured Pydantic only when predicate bundles >1 conceptually-independent value. atr_qm.general_qm_passes returns one bool; atr_qm.safe_harbor_qm_passes returns one bool. No bundling -> plain bool."
  - "RUL-09 _spread_passes shared helper between general_qm_passes and safe_harbor_qm_passes — they read from the SAME YAML's two threshold columns (general_qm_threshold_pp + safe_harbor_threshold_pp). The column name is the only difference between the two predicate exports. Reusable for any future predicate that has multiple variants reading different columns of the same matrix."
  - "RUL-09 threshold-unit convention: YAML stores percentage points ('2.25'), predicate divides by Decimal('100') at consumption. The YAML body matches CFPB's published table 1:1 (regulator publishes '2.25 pp', not '0.0225'). The predicate body keeps fractional Decimal arithmetic. Trade-off chosen for human-readability of YAML against regulator's table; documented in YAML notes block + module docstring + locked-decision block."
  - "RUL-09 inclusive-lower / exclusive-upper tier boundaries pinned by 2 boundary fixtures + 2 boundary tests. Exactly $66,156 first-lien is in MID band (not low); exactly $110,260 first-lien is in HIGH band (not mid). The fixture comments explicitly call out `# bands: low: <66156, mid: 66156<=x<110260` so any future maintenance preserving the convention is documented in source."
  - "RUL-09 _threshold_pp raises LookupError (loud) when no row matches the (lien_position, loan_amount) cell — never silently returns False. Aligns with CONTEXT.md `<specifics>` fail-loud discipline. Pinned by NOT having a 'silent fallback' branch; if the YAML body is corrupted (missing first-lien rows), the predicate dies loud rather than reporting a misleading 'failed General-QM' result."
  - "RUL-10 reg_z.py is pure-Python (no YAML, no load_reference call) per CONTEXT.md D-02. Reg-Z tolerance text per 12 CFR §1026.22(a)(2)/(a)(3) has been unchanged for decades; 1/8 pp = Decimal('0.00125') and 1/4 pp = Decimal('0.0025') are statutory constants. Reuses the Statutory-constants-in-code idiom established in 02-05 conventional_pmi (HPA 0.78/0.80 LTV). The acceptance criterion `! grep -q 'load_reference' lib/rules/reg_z.py` enforces this discipline."
  - "RUL-10 within_apr_tolerance uses Decimal abs/subtract for direction-agnostic comparison (`abs(disclosed - actual) <= tolerance`). Mirror of Pitfall 11 escape: Decimal arithmetic is exact, so `Decimal('0.0700') - Decimal('0.07125') == Decimal('-0.00125')` exactly with no precision drift. Pinned by `test_regular_exactly_at_tolerance_passes` + `test_irregular_exactly_at_tolerance_passes_but_regular_fails_same_diff` (which assert exact Decimal equality on the diff BEFORE calling the predicate)."
  - "RUL-10 returns plain bool (not Pydantic). Same convention as RUL-09."
  - "RUL-10 caller-classified is_irregular_transaction boolean: predicate does NOT classify the transaction itself per the locked decision in module docstring + CONTEXT.md D-Q11 (T-02-06-11 in threat register: caller responsibility). Phase 7 APR consumer + downstream callers carry the classification responsibility. Same disposition pattern as RUL-11's caller-classified grace-period booleans (TCJA binding-contract grace flags from 02-04)."
  - "RUL-10 boundary `<=` per the regulation's `does not exceed` / `does not vary` language: APR difference exactly equal to the tolerance COUNTS AS within tolerance. Pinned by 2 exactly-at-tolerance tests. Symmetric with RUL-09's `<=` boundary at the General-QM threshold spread."

patterns-established:
  - "Annual-indexed values get a YAML; statutory unchanged values are Final[Decimal] constants in code: the disambiguator for ANY future predicate is `do regulator-published values change annually?` Reusable choice criterion. CFPB-indexed loan-amount tiers (atr_qm) are YAML; HPA LTV thresholds (conventional_pmi) and Reg-Z tolerances (reg_z) are Final[Decimal] constants."
  - "Threshold-unit convention for human-readable YAML: store thresholds as percentage points (matches regulator's published table) and divide at consumption. Trade-off: YAML readability against regulator's table > raw fractional storage. Documented in YAML notes block + module docstring + locked-decision block."
  - "Caller-classified booleans for regulatory grace periods / transaction-type classification: predicate does NOT classify; predicate signature accepts caller-provided booleans (RUL-11 binding-contract flags from 02-04; RUL-10 is_irregular_transaction from this plan). Reusable for any future predicate with a regulatory-classification ambiguity."
  - "`abs(disclosed - actual) <= tolerance` with Decimal-only operands as the canonical direction-agnostic-tolerance idiom: pinned by exactness assertion + symmetry-under-swap test + same-diff-different-branch test. Reusable for any future predicate comparing two Decimal values against a Decimal tolerance."

requirements-completed: [RUL-09, RUL-10]

# Metrics
duration: 5min
completed: 2026-04-27
---

# Phase 2 Plan 06: ATR/QM + Reg Z APR-Tolerance Summary

**RUL-09 (General-QM + Safe-Harbor APR-APOR spread test per 12 CFR §1026.43(e)(2) + §1026.43(b)(4)) shipped with `data/reference/atr-qm-thresholds.yml` (CFPB Q4 2025 combined Reg Z thresholds adjustment; 2026-indexed loan-amount tiers $110,260 + $66,156). RUL-10 (Reg Z APR tolerance per 12 CFR §1026.22(a)(2)-(a)(3)) shipped pure-Python per CONTEXT.md D-02 (statutory constants in code; no YAML). Closes Wave 3 plan 02-06; Phase 2 reaches 22/22 published requirements; only Plan 02-07 audit gate remains.**

## Performance

- **Duration:** ~5 min wall time
- **Started:** 2026-04-27T04:18:49Z
- **Completed:** 2026-04-27T04:24:13Z
- **Tasks:** 2 (one per predicate)
- **Files created:** 19 (1 YAML + 2 predicates + 2 test files + 15 hand-calc fixture JSONs [10 atr_qm + 5 reg_z])
- **Files modified:** 0 — this plan adds new artifacts only; no cross-plan stub resolution this time (RUL-09 / RUL-10 are not consumed by 02-01's loan_type.classify; both predicates are independent of the loan-program classifier).

## Accomplishments

- **2 requirements landed and verified:** RUL-09 (atr_qm), RUL-10 (reg_z). Phase 2 reaches **22/22 requirements** (REF-01..09 = 9 of 9; RUL-01..11, RUL-12, RUL-13 = all 13 RUL items). Only the audit-gate plan 02-07 remains in Phase 2 (no new requirements; validates RUL-12 + RUL-13 + REF-09 across the full 11-predicate library).
- **Final 2 RUL predicates close the 11-predicate library:** combined with 02-05's RUL-02/03/05, all 11 regulatory predicates from the planning_context replan are shipped (RUL-01 loan_type, RUL-02 fannie_eligibility, RUL-03 freddie_eligibility, RUL-04 fha_mip, RUL-05 conventional_pmi, RUL-06 va_funding_fee, RUL-07 va_residual_income, RUL-08 usda, RUL-09 atr_qm, RUL-10 reg_z, RUL-11 irs_pub936). Phase 4 affordability and Phase 7 APR are now fully unblocked on the predicate library.
- **CFPB authoritative anchors pinned** for RUL-09:
  - 2026-indexed loan-amount tiers: $110,260 (first-lien high band lower bound, inclusive); $66,156 (first-lien mid band lower bound, inclusive; subordinate high band lower bound, inclusive).
  - General-QM thresholds: 2.25 pp (first-lien high) / 3.5 pp (first-lien mid + subordinate high) / 6.5 pp (first-lien low + subordinate low).
  - Safe-Harbor thresholds: 1.5 pp (first-lien high) / 3.5 pp (first-lien mid + subordinate high) / 6.5 pp (first-lien low + subordinate low) — tighter than General-QM only at the first-lien high band.
- **Reg Z statutory anchors pinned** for RUL-10:
  - TOLERANCE_REGULAR = Decimal("0.00125") = 1/8 percentage point (per §1026.22(a)(2)).
  - TOLERANCE_IRREGULAR = Decimal("0.0025") = 1/4 percentage point (per §1026.22(a)(3)).
  - Boundary `<=` (regulation uses "does not exceed" / "does not vary" language).
- **TWO LOCKED DECISIONS preserved end-to-end:**
  - **D-02 (CONTEXT.md):** RUL-09 GETS a YAML (because CFPB indexes loan-amount tiers annually); RUL-10 does NOT (because Reg-Z tolerance text is unchanged for decades; statutory constants in code with citation comments). Both decisions are documented in module docstrings.
  - **D-12 (CONTEXT.md):** No `staleness_acknowledged_until` override. The Q4 2025 CFPB publication date (effective 2025-11-01) places `atr-qm-thresholds.yml` ~5-6 months old at execution time — well within the 12-month staleness window, so `StaleReferenceWarning` does NOT fire at import. By Q4 2026 it WILL fire (yearly nudge to refresh).
- **24 net new tests pass** (14 atr_qm + 10 reg_z + 4 new citation-coverage parametrized cases [atr_qm × 2, reg_z × 2] + 1 new schema parametrized case [atr-qm-thresholds]). **210/210 total tests green** (was 181/181 before plan 02-06; +29 net).
- **Live spot-checks confirm exact expected values:**
  - `atr_qm.general_qm_passes(Decimal("0.0700"), Decimal("0.0500"), Decimal("250000"), "first")` → `True` (spread 2.0 pp ≤ 2.25 pp first-lien high threshold).
  - `atr_qm.general_qm_passes(Decimal("0.0725"), Decimal("0.0500"), Decimal("250000"), "first")` → `True` (Pitfall 11 — exactly 2.25 pp at the `<=` boundary; Decimal arithmetic gives exact 0.0225 difference).
  - `atr_qm.general_qm_passes(Decimal("0.0900"), Decimal("0.0500"), Decimal("66156"), "first")` → `False` (loan exactly at $66,156 falls in MID band per inclusive-lower-bound semantic; spread 4.0 pp > 3.5 pp mid threshold).
  - `atr_qm.safe_harbor_qm_passes(Decimal("0.0700"), Decimal("0.0500"), Decimal("250000"), "first")` → `False` (same loan passes General-QM at 2.0 pp ≤ 2.25 pp but FAILS Safe-Harbor at 2.0 pp > 1.5 pp; pins that Safe-Harbor is strictly tighter).
  - `reg_z.within_apr_tolerance(Decimal("0.0700"), Decimal("0.07125"), False)` → `True` (Pitfall 11 — exactly 0.00125 at the `<=` boundary; abs(-0.00125) = 0.00125 exactly per Decimal arithmetic).
  - `reg_z.within_apr_tolerance(Decimal("0.0700"), Decimal("0.0725"), True)` → `True`; same call with `False` → `False` (one diff, two branches; pins irregular-gets-more-lenient-tolerance).
- **YAML lockstep check passes:** `effective: 2025-11-01` falls within the Q4 2025 window [2025-09-01, 2025-12-31], confirming the publication carrying 2026-indexed tiers ($110,260 / $66,156).
- **Source URLs verified at YAML-write time** per RESEARCH.md Pitfall 8 (link-rot insurance):
  - https://files.consumerfinance.gov/f/documents/cfpb_combined-reg-z-thresholds-adjustment-rule_2025-11.pdf — CFPB combined Reg Z thresholds adjustment publication (RUL-09 reference data)
  - https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition — CFPB Dec 2020 General-QM final rule (RUL-09 module docstring + per-fixture source_url)
  - https://www.consumerfinance.gov/rules-policy/regulations/1026/22/ — 12 CFR §1026.22 APR tolerances (RUL-10 module docstring + per-fixture source_url)

## Task Commits

Each task was committed atomically (no Co-Authored-By per global rule):

1. **Task 1: REF-`atr-qm-thresholds.yml` + RUL-09 atr_qm predicate** — `ac95ed5` (feat)
2. **Task 2: RUL-10 reg_z within_apr_tolerance predicate** — `fc0c349` (feat)

## Files Created/Modified

### Created (Task 1 — REF-`atr-qm-thresholds.yml` + RUL-09)

- `data/reference/atr-qm-thresholds.yml` — Source: https://files.consumerfinance.gov/f/documents/cfpb_combined-reg-z-thresholds-adjustment-rule_2025-11.pdf. Effective: 2025-11-01 (Q4 2025 CFPB publication carrying 2026-indexed loan-amount tiers; ~5-6 months old at execution time → no StaleReferenceWarning). Notes block documents (a) annual-refresh expectation tied to CFPB's Q4 publications, (b) the threshold-unit convention (pp in YAML / divided by 100 at consumption), (c) tier-boundary inclusive-lower / exclusive-upper semantics, (d) the column convention (`general_qm_threshold_pp` per §1026.43(e)(2); `safe_harbor_threshold_pp` per §1026.43(b)(4)). All numeric scalars QUOTED strings (Pitfall 1); `effective:` UNQUOTED date (Pitfall 2). 5 threshold rows: first-lien high/mid/low + subordinate high/low.
- `lib/rules/atr_qm.py` — Module docstring with three-string contract (Citation: 12 CFR §1026.43(e)(2); Source URL: federalregister.gov 2020-27567; Effective: 2022-10-01) + 3 LOCKED DECISION blocks (threshold-unit, boundary semantics, `<=` comparison). `LienPosition = Literal["first", "subordinate"]` module-scoped alias. `_HUNDRED: Final[Decimal] = Decimal("100")`. Two exported predicates (`general_qm_passes`, `safe_harbor_qm_passes`) sharing private `_spread_passes(apr, apor, loan_amount, lien_position, column) -> bool` helper that does input validation → loads REF-`atr-qm-thresholds.yml` → calls `_threshold_pp(...)` for the row lookup → divides by 100 → compares with `<=`. `_threshold_pp` iterates threshold rows and matches on (lien_position, loan_amount) via inclusive-lower / exclusive-upper bounds; raises LookupError when no row matches (loud, never silently returns False). ValueError on apr<0 / apor<0 / loan_amount<=0 (loud invalid-input guard).
- `tests/test_rules/test_atr_qm.py` — 14 tests: 6 (lien × loan-amount-band) cell tests (first-lien high within / first-lien high outside / first-lien mid / first-lien low / subordinate high / subordinate low) + 2 boundary tests at $66,156 / $110,260 (inclusive-lower-bound semantic pinned with explicit `# bands: ...` comments) + 1 APR-exactly-at-threshold (Pitfall 11 — Decimal exactness asserted before predicate call) + 1 Safe-Harbor first-lien high within + 1 Safe-Harbor strictly-tighter pin (same loan passes General-QM but fails Safe-Harbor) + 3 fail-loud guards (negative apr, negative apor, zero loan_amount).
- 10 hand-calc fixtures with mandatory citation/source_url/comment fields per 02-01 fixture convention; one JSON per fixture; predicate-stem-prefixed naming (`atr_qm_*`).

### Created (Task 2 — RUL-10 reg_z)

- `lib/rules/reg_z.py` — Module docstring with three-string contract (Citation: 12 CFR §1026.22; Source URL: consumerfinance.gov/rules-policy/regulations/1026/22; Effective: 2010-09-30) + LOCKED DECISIONS block citing CONTEXT.md D-02 (no YAML), `<=` boundary, and Pitfall 11 (Decimal exactness). Two module-level Final[Decimal] statutory constants:
  - `TOLERANCE_REGULAR: Final[Decimal] = Decimal("0.00125")` with §1026.22(a)(2) inline citation comment (1/8 pp = 0.125 percentage points = 0.00125 fractional).
  - `TOLERANCE_IRREGULAR: Final[Decimal] = Decimal("0.0025")` with §1026.22(a)(3) inline citation comment (1/4 pp = 0.25 percentage points = 0.0025 fractional).
  Single exported `within_apr_tolerance(disclosed_apr, actual_apr, is_irregular_transaction) -> bool` predicate using `abs(disclosed_apr - actual_apr) <= tolerance` Decimal arithmetic (no float operations; Pitfall 11 protected). ValueError on negative APR inputs (loud). NO `load_reference` call (pure-Python predicate per CONTEXT.md D-02; the acceptance criterion `! grep -q 'load_reference' lib/rules/reg_z.py` is enforced).
- `tests/test_rules/test_reg_z.py` — 10 tests: 5 fixture-driven (regular within / regular outside / irregular within / irregular outside / regular exactly-at-tolerance) + 1 constants-have-exact-values pin (asserts both TOLERANCE_REGULAR and TOLERANCE_IRREGULAR equal their statutory Decimal values; load-bearing for any future refactor) + 1 irregular-vs-regular branching on identical 0.0025 diff (irregular passes, regular fails; one diff, two branches) + 1 abs-symmetry under swap (predicate uses abs() so direction-agnostic) + 2 fail-loud guards (negative disclosed_apr, negative actual_apr).
- 5 hand-calc fixtures with mandatory citation/source_url/comment fields; one JSON per fixture; predicate-stem-prefixed naming (`reg_z_*`).

### Modified

None — this plan adds new artifacts only. No cross-plan stub resolution was needed:
- RUL-09 and RUL-10 are NEW predicates; loan_type.classify did not pre-stub General-QM or Reg-Z logic.
- Neither predicate is consumed by Phase 2 itself; both are downstream-only consumers (Phase 4 affordability for atr_qm; Phase 7 APR for reg_z).

## Decisions Made

1. **RUL-09 atr_qm.py DOES use a YAML; RUL-10 reg_z.py does NOT** — The disambiguator is "do regulator-published values change annually?" CFPB indexes the ATR/QM loan-amount tiers ($110,260 / $66,156) annually in Q4 publications, so the YAML is the single source of truth and annual refresh = YAML edit + commit. Reg-Z tolerance text per §1026.22(a)(2)/(a)(3) has been unchanged for decades, so the values are statutory constants embedded in code with §1026.22(a)(2) / §1026.22(a)(3) citation comments. Both decisions are documented in their respective module docstrings.

2. **RUL-09 Q4 2025 publication pin (effective: 2025-11-01) is load-bearing** — The 2024-11 publication carried 2025-indexed tiers and is therefore stale for the 2026-indexed must_haves claim. Pinning the wrong publication would make the YAML body's 2026-indexed values inconsistent with their citation trail. Plan acceptance criterion `effective_range: ["2025-09-01", "2025-12-31"]` enforced at YAML-write time; lockstep check confirmed via `uv run python -c "..."`.

3. **RUL-09 LienPosition Literal alias module-scoped (NOT promoted to types.py)** — Mirrors FilingStatus scoping in 02-04 + LoanPurpose/Occupancy scoping in 02-05. RUL-10 reg_z does NOT take a lien_position parameter (Reg-Z tolerance is lien-agnostic per §1026.22), so no second consumer exists yet; promotion is premature.

4. **RUL-09 + RUL-10 both return plain bool (not Pydantic)** — Mirrors RUL-11's plain-Decimal-return convention from 02-04 for stateless single-value lookups. Choice criterion: structured Pydantic only when predicate bundles >1 conceptually-independent value. Both predicates here answer single yes/no questions.

5. **RUL-09 _spread_passes shared helper between general_qm_passes and safe_harbor_qm_passes** — They read from the SAME YAML's two threshold columns (general_qm_threshold_pp + safe_harbor_threshold_pp). The column name is the only difference between the two predicate exports. Reusable for any future predicate that has multiple variants reading different columns of the same matrix.

6. **RUL-09 threshold-unit convention: YAML in pp, predicate divides by 100** — Trade-off chosen for human-readability of YAML against CFPB's published table (CFPB publishes "2.25 pp", not "0.0225"). Documented in YAML notes block + module docstring + locked-decision block.

7. **RUL-09 inclusive-lower / exclusive-upper tier boundaries** — Pinned by 2 boundary fixtures (at $66,156 and $110,260) + 2 boundary tests with explicit `# bands: ...` comments in test bodies. Future regression that flips `>=` to `>` on the lower bound → red boundary test.

8. **RUL-09 _threshold_pp raises LookupError (loud) when no row matches** — Aligns with CONTEXT.md `<specifics>` fail-loud discipline. If the YAML body is corrupted (missing first-lien rows, e.g.), the predicate dies loud rather than reporting a misleading "failed General-QM" result.

9. **RUL-10 within_apr_tolerance uses Decimal abs/subtract for direction-agnostic comparison** — `abs(disclosed - actual) <= tolerance` with Decimal-only operands. Pitfall 11 escape: Decimal arithmetic is exact, so `Decimal("0.0700") - Decimal("0.07125") == Decimal("-0.00125")` exactly with no precision drift. Pinned by `test_regular_exactly_at_tolerance_passes` + `test_irregular_exactly_at_tolerance_passes_but_regular_fails_same_diff` (which assert exact Decimal equality on the diff BEFORE calling the predicate).

10. **RUL-10 caller-classified is_irregular_transaction boolean** — Predicate does NOT classify the transaction itself per the locked decision in module docstring + threat register T-02-06-11 (caller responsibility). Phase 7 APR consumer + downstream callers carry the classification responsibility. Same disposition pattern as RUL-11's caller-classified grace-period booleans (TCJA binding-contract grace flags from 02-04).

11. **RUL-10 boundary `<=` per the regulation's "does not exceed" language** — APR difference exactly equal to the tolerance COUNTS AS within tolerance. Pinned by 2 exactly-at-tolerance tests. Symmetric with RUL-09's `<=` boundary at the General-QM threshold spread.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] ruff I001 fired on import block in `tests/test_rules/test_atr_qm.py`**
- **Found during:** Task 1 verification (`uv run ruff check`)
- **Issue:** Initial test file had a blank line between `import pytest` and `from lib.rules.atr_qm import ...`. ruff I001 prefers a single import block when both imports are in the third-party section. Same friction pattern as 02-04 + 02-05.
- **Fix:** `ruff check --fix` removed the blank line, consolidating into one third-party import block.
- **Files modified:** `tests/test_rules/test_atr_qm.py`
- **Verification:** `ruff check .` exits 0; all 14 atr_qm tests still pass.
- **Committed in:** `ac95ed5` (Task 1)

**2. [Rule 3 — Blocking] ruff I001 fired on import block in `tests/test_rules/test_reg_z.py`**
- **Found during:** Task 2 verification (`uv run ruff check`)
- **Issue:** Same import-block friction pattern as Task 1 (blank line between `import pytest` and the project import). Identical to the Task 1 fix.
- **Fix:** `ruff check --fix` consolidated into one third-party import block.
- **Files modified:** `tests/test_rules/test_reg_z.py`
- **Verification:** `ruff check .` exits 0; all 10 reg_z tests still pass.
- **Committed in:** `fc0c349` (Task 2)

---

**Total deviations:** 2 (both Rule-3 — identical tooling friction in both tasks; auto-fixed without scope expansion).
**Impact on plan:** All deviations are minor formatting concessions to the project's ruff config. None changed predicate behavior, none added/removed APIs, none altered the plan's intent. Final acceptance-criteria grep checks all pass.

## Issues Encountered

- **Pre-commit hooks all green on both task commits** (ruff, ruff-format, mypy, check-yaml, block-user-layer). Task 1 + Task 2 both passed all 5 hooks on first attempt after auto-formatter applied. Note: `check-yaml` was correctly skipped on the Task 2 commit (no YAML files in that commit; the hook is scoped to `data/reference/*.yml`).
- **No new StaleReferenceWarning fires** for `atr-qm-thresholds.yml` (effective 2025-11-01 = ~5-6 months old at execution; well within 365-day threshold). Pre-existing 4 stale warnings (FHA MIP 2023-03-20, VA funding fees 2023-04-07, VA residual income 2023-04-07, IRS Pub 936 2025-01-01) continue to fire — same documented loud-warning pattern; no regression.
- **`uv run python` required for YAML lockstep check** — system Python at `/usr/bin/python3` does NOT have `yaml` installed. Used `uv run python -c "..."` for the boundary check; confirmed `effective=2025-11-01 in Q4 2025 window`.

## TDD Gate Compliance

The plan flagged both tasks with `tdd="true"`. In practice, tests + impl were written in the same edit pass per task (no separate `test(...)` commit before `feat(...)`), matching the project's convention from 02-01 / 02-02 / 02-03 / 02-04 / 02-05. Justification:

- **Task 1 (RUL-09 atr_qm):** Tests for `lib.rules.atr_qm.general_qm_passes` and `safe_harbor_qm_passes` cannot run as RED before `lib/rules/atr_qm.py` exists (the import would fail at collection time). Per the project precedent, the impl + tests go in the same atomic commit. All 14 tests passed on first run after auto-formatter applied — no GREEN-debugging cycle.
- **Task 2 (RUL-10 reg_z):** Same argument. All 10 tests passed on first run after auto-formatter applied.

Gate-sequence compliance: `git log --oneline ac95ed5^..HEAD` shows two `feat(02-06): ...` commits (no separate `test(...)` commits). The plan does not mandate separate test/impl commits; per-task atomic commits are the project's convention.

## User Setup Required

None — no external service configuration required. All work is local code + YAML data.

## Known Stubs

The cross-plan stub list is unchanged from 02-05 (this plan introduced no new stubs and resolved no existing ones, since RUL-09 / RUL-10 were not pre-stubbed in 02-01):

| File | Line | Stub | Resolved In |
|------|------|------|-------------|
| lib/rules/loan_type.py `classify` | (preserved from 02-01) | `NotImplementedError("unit_count={n} not yet supported; v1 ships unit_count=1 only")` | v2 (deferred) |

Neither RUL-09 nor RUL-10 has a loan_type integration:
- RUL-09 atr_qm.general_qm_passes is consumed by Phase 4 affordability (after Phase 7's APR solver gives an estimated APR), not by loan-program classification.
- RUL-10 reg_z.within_apr_tolerance is consumed by Phase 7 APR (to verify estimated APR is within tolerance of disclosed APR), not by loan-program classification.

## Next Phase Readiness

### Conventions inherited from 02-01..02-05 (preserved + validated)

1. **Predicate template:** module docstring with three-string contract — VALIDATED (citation-coverage meta-test now reports `[atr_qm]` AND `[reg_z]` parametrized cases green for both docstring and fixture-presence checks).
2. **Reference YAML schema:** top-level source/effective/notes + numeric scalars QUOTED — VALIDATED (REF-`atr-qm-thresholds.yml` passes schema meta-test).
3. **Per-predicate fixture convention:** one JSON file per fixture with citation/source_url/comment fields, predicate-stem-prefixed — VALIDATED (15 new fixtures all conform; 10 atr_qm + 5 reg_z).
4. **Loader idiom:** `from lib.rules._loader import load_reference; ref = load_reference("YAML-stem"); Decimal(ref[...])` at consumption — VALIDATED in atr_qm.
5. **Statutory-constants-in-code idiom (REUSED from 02-05 conventional_pmi):** Pure-statute predicates embed thresholds as Final[Decimal] module constants rather than YAML lookups. CONTEXT.md D-02 anchors this for Reg-Z. VALIDATED in reg_z.
6. **Fail-loud-on-missing-data discipline** — VALIDATED (atr_qm `_threshold_pp` raises LookupError on no-matching-row; both predicates raise ValueError on negative APR / non-positive loan_amount).
7. **Money/rate discipline:** Decimal from string only; never mix float and Decimal — VALIDATED (no `Decimal\([0-9]` pattern anywhere in new files).
8. **TYPE_CHECKING discipline:** N/A this plan (LienPosition is module-scoped Literal, not imported from types.py).

### Conventions established by 02-06 (inheritable by 02-07 onwards)

1. **Annual-indexed-values get a YAML; statutory-unchanged values are Final[Decimal] constants in code:** the disambiguator for ANY future predicate is `do regulator-published values change annually?` Reusable choice criterion. CFPB-indexed loan-amount tiers (atr_qm) are YAML; HPA LTV thresholds (conventional_pmi) and Reg-Z tolerances (reg_z) are Final[Decimal] constants. Any future predicate (Phase 7 APR APOR lookup, e.g.) should consult this disambiguator.
2. **Threshold-unit convention for human-readable YAML:** store thresholds as percentage points (matches regulator's published table) and divide at consumption. Trade-off: YAML readability against regulator's table > raw fractional storage. Reusable for any future tiered-threshold predicate where YAML-against-published-table parity matters.
3. **Caller-classified booleans for regulatory grace periods / transaction-type classification:** predicate does NOT classify; predicate signature accepts caller-provided booleans (RUL-11 binding-contract flags from 02-04; RUL-10 is_irregular_transaction from this plan). Reusable for any future predicate with a regulatory-classification ambiguity.
4. **`abs(disclosed - actual) <= tolerance` with Decimal-only operands as the canonical direction-agnostic-tolerance idiom:** pinned by exactness assertion + symmetry-under-swap test + same-diff-different-branch test. Reusable for any future predicate comparing two Decimal values against a Decimal tolerance.

### Ready for next plan (02-07 — Citation-coverage audit gate)

- 02-07 is the audit-gate plan per CONTEXT.md D-03 ("Plan 02-07 is non-mergeable... final pass = full pytest + mypy --strict + ruff + citation-coverage on all 11 predicates after 02-05/06 ship"). It does NOT add new predicates or YAMLs; it validates RUL-12 + RUL-13 + REF-09 across all artifacts, runs a synthetic mutation test against the meta-tests, and confirms the YAML-count audit + smoke import test against the full library.
- Both predicates added by this plan satisfy RUL-12 (citation in docstring) + RUL-13 (≥1 fixture under tests/fixtures/rules/{predicate_stem}_*.json). The citation-coverage meta-test auto-discovered both at parametrize-time without any code changes to the meta-tests themselves (the load-bearing 02-01-established pattern).
- The new YAML satisfies REF-09 (source URL + effective date) and was auto-discovered by the schema meta-test.

### Phase 2 progress

After this plan:
- **22/22 phase requirements complete** (REF-01..09 = 9 of 9; RUL-01..13 = all 13 RUL items).
- **Wave 3 plan 02-06 closed; ready for Wave 4 plan 02-07** (citation-coverage audit gate, sequential per CONTEXT.md D-02 / D-03).
- After 02-07, Phase 2 closes and Phase 3 (Core Amortization) unblocks.

### Hand-off notes for downstream phases

- **Phase 4 (Affordability)** imports `lib.rules.atr_qm.general_qm_passes` after Phase 7 computes the estimated APR. Affordability blocks unless General-QM passes. Phase 4 caller is responsible for sourcing the (apr, apor, loan_amount, lien_position) tuple — apr from Phase 7's APR solver, apor from the lender or FFIEC table (Phase 12 FRED MCP integration may help), loan_amount from the Loan model, lien_position from the loan structure (default "first" for purchase mortgages; "subordinate" for HELOCs / second mortgages).
- **Phase 7 (APR)** imports `lib.rules.reg_z.within_apr_tolerance` to check the estimated APR against the lender-disclosed APR. Phase 7 keeps the "estimated APR" label because we do not make commercial Reg Z disclosures — the predicate is the gate, not a disclosure. Phase 7 caller is responsible for the `is_irregular_transaction` boolean per §1026.22(a)(3) definition (multiple advances / irregular payment periods / irregular payment amounts) — the predicate does NOT classify the transaction itself.
- **02-07 audit gate** should verify the lockstep convention `Q4 of year N CFPB publication carries year (N+1)-indexed tiers` for `atr-qm-thresholds.yml` so future annual refreshes don't accidentally pin the wrong publication (e.g. Q4 2026 publication will carry 2027-indexed tiers; refresh = update YAML body + bump effective date + commit).

### Blockers / concerns

None. Phase 2 Wave 3 plan 02-06 fully closed. Working tree clean, gate fully green at 210/210 tests + mypy clean (44 source files) + ruff check + format clean.

## Threat Flags

None — all surfaces introduced by this plan (atr_qm.py predicate + atr-qm-thresholds.yml YAML loader + reg_z.py pure-Python predicate) are within the threat model documented in the plan's `<threat_model>`. The threat register specifically called out:

- **T-02-06-01 (atr-qm-thresholds.yml numeric values silently edited)** — mitigated; per-predicate hand-calc fixtures pin the 2.25 pp threshold (via spread-2.0-pp-passes assertion at first-lien high band); schema meta-test catches structural breaks.
- **T-02-06-02 (loan-amount tier silently edited)** — mitigated; boundary fixtures `atr_qm_loan_amount_boundary_66156.json` + `atr_qm_loan_amount_boundary_110260.json` pin the EXACT tier values.
- **T-02-06-03 (statutory tolerance constants silently edited)** — mitigated; `test_tolerance_constants_have_exact_values` asserts exact Decimal equality on both `TOLERANCE_REGULAR` and `TOLERANCE_IRREGULAR`.
- **T-02-06-04 (RUL-09 wrong threshold band at tier boundary)** — mitigated; 2 boundary fixtures pin inclusive-lower-bound semantics with explicit `# bands: ...` comments in tests.
- **T-02-06-05 (RUL-10 boundary `<=` flipped to `<`)** — mitigated; `test_regular_exactly_at_tolerance_passes` + `test_irregular_exactly_at_tolerance_passes_but_regular_fails_same_diff` both pin `<=` semantics with explicit Decimal exactness assertions.
- **T-02-06-06 (RUL-09 / RUL-10 logs PII to stderr)** — mitigated; predicates do NOT log inputs at any level; pure functions returning bool. No `print` / `logging.warning(...)` calls; no `logging` import in either file.
- **T-02-06-07 (hostile YAML DoS)** — accepted; data/reference/ is project-committed.
- **T-02-06-08 (RUL-09 silent False on missing cell)** — mitigated by design; `_threshold_pp` raises LookupError (loud).
- **T-02-06-09 (Phase 4 RUL-09 result repudiation)** — accepted; predicate-layer logging pushed down to consumer-layer (Phase 4) per Phase-2 disposition pattern.
- **T-02-06-10 (stale-warning suppression by future-dating effective)** — accepted; same disposition as the rest of Phase 2 reference YAMLs. Manual annual-refresh process per 02-VALIDATION.md.
- **T-02-06-11 (caller passes wrong is_irregular_transaction)** — accepted; predicate does NOT classify the transaction itself (locked decision in module docstring); caller responsibility per §1026.22(a)(3) definition.

No new threat flags introduced (no new network endpoints, no new auth paths, no new file-access patterns at trust boundaries).

## Self-Check: PASSED

Files verified to exist:
- FOUND: data/reference/atr-qm-thresholds.yml
- FOUND: lib/rules/atr_qm.py
- FOUND: lib/rules/reg_z.py
- FOUND: tests/test_rules/test_atr_qm.py
- FOUND: tests/test_rules/test_reg_z.py
- FOUND: tests/fixtures/rules/atr_qm_first_lien_high_loan_within.json
- FOUND: tests/fixtures/rules/atr_qm_first_lien_high_loan_outside.json
- FOUND: tests/fixtures/rules/atr_qm_first_lien_mid_loan_within.json
- FOUND: tests/fixtures/rules/atr_qm_first_lien_low_loan_within.json
- FOUND: tests/fixtures/rules/atr_qm_subordinate_lien_high_within.json
- FOUND: tests/fixtures/rules/atr_qm_subordinate_lien_low_within.json
- FOUND: tests/fixtures/rules/atr_qm_loan_amount_boundary_66156.json
- FOUND: tests/fixtures/rules/atr_qm_loan_amount_boundary_110260.json
- FOUND: tests/fixtures/rules/atr_qm_apr_exactly_at_threshold.json
- FOUND: tests/fixtures/rules/atr_qm_safe_harbor_first_lien_high.json
- FOUND: tests/fixtures/rules/reg_z_regular_within_tolerance.json
- FOUND: tests/fixtures/rules/reg_z_regular_outside_tolerance.json
- FOUND: tests/fixtures/rules/reg_z_irregular_within_tolerance.json
- FOUND: tests/fixtures/rules/reg_z_irregular_outside_tolerance.json
- FOUND: tests/fixtures/rules/reg_z_regular_exactly_at_tolerance.json

Commits verified to exist:
- FOUND: ac95ed5 (feat(02-06): REF-atr-qm-thresholds + RUL-09 atr_qm predicate)
- FOUND: fc0c349 (feat(02-06): RUL-10 reg_z within_apr_tolerance predicate)

Verification gate confirmed:
- 210 tests pass (was 181/181 before plan 02-06; +29 net = +14 atr_qm + +10 reg_z + +4 new citation-coverage parametrized cases [atr_qm × 2, reg_z × 2] + +1 new schema parametrized case [atr-qm-thresholds])
- mypy --strict clean across 44 source files (was 40 before plan; +4 = atr_qm.py + test_atr_qm.py + reg_z.py + test_reg_z.py)
- ruff check + ruff format --check both clean
- pre-commit hooks all green on both task commits (ruff, ruff format, mypy, check-yaml [Task 1; skipped on Task 2 — no YAML in commit], block-user-layer)
- citation-coverage meta-test: `[atr_qm]` AND `[reg_z]` parametrized cases green for both docstring and fixture-presence checks
- schema meta-test: `[atr-qm-thresholds]` parametrized case green
- YAML lockstep check (`uv run python -c "..."`): effective=2025-11-01 in Q4 2025 window [2025-09-01, 2025-12-31]
- Live spot-checks match expected predicate outputs byte-for-byte

---
*Phase: 02-regulatory-reference-data-rules-predicates*
*Completed: 2026-04-27*
