# Phase 2: Regulatory Reference Data & Rules Predicates - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning (replan triggered — existing 4 plans cover only 17 of 23 reqs)

<domain>
## Phase Boundary

Build the cited regulatory data layer (`data/reference/*.yml` with `source:` URL + `effective:` date fields) and the one-predicate-per-citation rules library (`lib/rules/*.py`) that every later calc phase composes.

**Delivered this phase:**
- 7 published reference YAMLs (REF-01..07) + 2 implementation-detail matrix YAMLs (Fannie LLPA, Freddie eligibility) under RUL-02/03
- Shared loader (`lib/rules/_loader.py`) with `lru_cache` + `StaleReferenceWarning` (>12 months on `effective:` field)
- 11 predicate files (`lib/rules/loan_type.py`, `fannie_eligibility.py`, `freddie_eligibility.py`, `fha_mip.py`, `conventional_pmi.py`, `va_funding_fee.py`, `va_residual_income.py`, `usda.py`, `atr_qm.py`, `reg_z.py`, `irs_pub936.py`)
- Per-predicate test files with hand-calc fixtures pinned to regulator-published values
- Schema test (REF-09) and citation-coverage meta-test (RUL-12, RUL-13)
- Pydantic typed extension types in `lib/rules/types.py` (`LoanType`, `Region`, `County`, `Borrower`, `Property`)

**NOT delivered this phase** (deferred to consumer phases):
- Wiring predicates into `lib.affordability` — Phase 4
- Wiring predicates into `lib.amortize` — Phase 3 doesn't need rules
- Live rate fetching — Phase 12 (FRED MCP)
- Annual refresh automation — v2 (AUTO-01)
- County geocoding — caller supplies `(state_fips, county_fips)` tuples

</domain>

<decisions>
## Implementation Decisions

### Scope

- **D-01: Ship all 11 predicates this phase.** No deferral of the matrix-heavy ones (Fannie LLPA, Freddie eligibility). Phase 4 affordability gets the full predicate library day-one with no Phase 4 surprises. Existing plans 02-01..02-04 cover 6 predicates; three new plans are added.
- **D-02: Plan packaging = 7 plans total.** Existing 02-01 (loader + RUL-01) + 02-02 (FHA) + 02-03 (VA) + 02-04 (USDA + IRS) stand as-is. Three new plans:
  - **02-05** — Conventional PMI (RUL-05) + Fannie LLPA (RUL-02) + Freddie eligibility (RUL-03)
  - **02-06** — ATR/QM (RUL-09) + Reg Z (RUL-10)
  - **02-07** — Citation-coverage hardening + final schema audit (RUL-12, RUL-13 final pass; REF-09 final pass)
- **D-03: Plan 02-07 is non-mergeable.** Even if RESEARCH §1162 says "can be merged into 02-06 if scope allows," keep it separate as an audit gate. Final pass = full pytest + mypy --strict + ruff + citation-coverage on all 11 predicates after 02-05/06 ship. This is the gate that protects Phase 4+ from inheriting predicate-library rot.

### Reference Data Scope

- **D-04: Fannie LLPA matrix (RUL-02) ships full matrix.** All FICO-bucket × LTV-bucket × loan-purpose × occupancy × unit-count cells extracted from `singlefamily.fanniemae.com/media/9391/display`. No `NotImplementedError` branches. Annual refresh will be a meaningful YAML edit — accept that maintenance burden.
- **D-05: Fannie LLPA + Freddie eligibility YAMLs are implementation-detail, not new REF-IDs.** `data/reference/fannie-llpa-matrix.yml` and `data/reference/freddie-eligibility-matrix.yml` are added under RUL-02 / RUL-03 silently. `REQUIREMENTS.md` count stays at 22 for Phase 2 / 116 total. Plan rationale documents that "the predicate's reference data lives in `data/reference/{name}.yml` consistent with REF-01..07 discipline."
- **D-06: County subset = top 100 high-cost counties + all WA counties.** Applies to REF-01 (FHFA conforming-limits-2026.yml), REF-02 (fha-limits-2026.yml), REF-06 (usda-income-limits.yml). Top 100 by metro population covers ~95% of high-cost-area mortgage volume; all WA counties cover the Pachulski household location. USDA: WA counties + top 50 nationally. **Unlisted high-cost counties → `MissingCountyDataError` (loud)** so users know to extend rather than silently treating an unlisted high-cost county as baseline-only. YAML `notes:` field documents the subset policy.

### Type System

- **D-07: New Phase 2 Pydantic types live in `lib/rules/types.py` (new file).** Phase 1's `lib/models.py` (Money, Rate, Loan, Schedule, Payment) stays untouched as a frozen surface. New types: `LoanType`, `Region`, `County`, `Borrower`, `Property`. Phase 4+ imports from both `lib.models` and `lib.rules.types`. Promote to `lib/models.py` later only if types prove broadly useful (e.g., Phase 4 affordability uses `County` for property location).
- **D-08: `lib/rules/__init__.py` is empty.** No re-exports. Predicates are imported by full path (`from lib.rules.loan_type import classify`). Defends the citation-per-file audit trail; the citation-coverage meta-test depends on it.

### Predicate I/O Conventions

- **D-09: IRS Pub 936 grace period = per-debt boolean flags, NOT a single `origination_date`.** RUL-11 input takes `binding_contract_signed_before_2017_12_15: bool` AND `binding_contract_closed_before_2018_04_01: bool` per debt. When both `True`, applies grandfathered $1M cap. Caller is responsible for sourcing the truth-values from settlement statements (or marking unknown). Confirms what existing 02-04 plan inferred as `D-PHASE2-Q5`.
- **D-10: USDA missing-county handling = silent default (intentionally asymmetric with RUL-01).** RUL-01 (`loan_type.classify`) raises `MissingCountyDataError` when county is missing AND loan exceeds baseline because the lookup direction is "is this county high-cost?" — a missing county can't be answered. RUL-08 (`usda.evaluate`) silently uses the default income limit when a county lacks an override because USDA's *published policy IS* "default income limit applies unless an override is published." Document the asymmetry in `usda.py` docstring so future readers don't "fix" it into a raise. Confirms what existing 02-04 plan locked.
- **D-11: VA residual-income citation string format is STABLE.** RUL-07 populates `binding_rule_citation` as `f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"` because Phase 4 AFFD-07 reads it as the `blocked_by` sentinel. Format drift breaks Phase 4. Confirms what existing 02-03 plan locked.

### Staleness Policy

- **D-12: No `staleness_acknowledged_until` override field.** YAMLs whose `effective:` is genuinely older than 12 months (FHA MIP from 2023-03-20, VA M26-7 from 2023-04-07) WILL fire `StaleReferenceWarning` on import. The warning is *correct* — these YAMLs ARE old, even if the regulator hasn't republished — and serves as a yearly nudge to re-verify HUD/VA hasn't quietly updated the values. Aligns with the project's "fail loud" discipline. Per-file acknowledgment override deferred to v2 if warning noise becomes a real annoyance.

### Claude's Discretion

- **Loader implementation details:** `lru_cache(maxsize=None)`, returning fresh `dict` per call (immutable contract — predicates never mutate loader results), `cache_clear()` available for test isolation per Pitfall 12.
- **YAML schema validation:** Pydantic v2 + `_loader.py` per-loader validation (no Cerberus / jsonschema dependency).
- **YAML safe-load discipline:** `yaml.safe_load` only — never `yaml.load`. ASVS V10 mitigation; loader test asserts the call site.
- **Test fixture format:** JSON files in `tests/fixtures/rules/` keyed by predicate (e.g., `loan_type_high_balance_san_francisco.json`); `citation` + `source_url` + hand-calc `comment` fields included for audit + tampering-resistance per RESEARCH §V11.
- **Predicate file structure:** Module docstring includes citation + source URL + effective date + cfpb/jumbo-mortgage / HMDA Platform pattern reference. Citation-coverage meta-test parametrizes over filesystem, not a hardcoded list.
- **Sequencing within Phase 2:** Existing plans use Wave 1 = 02-01 (load-bearing template) → Wave 2 = 02-02/03/04 (parallel; each depends only on 02-01). New plans 02-05/06/07 should run in **Wave 3** (sequential after Wave 2 completes), since 02-07 audits everything and 02-05 + 02-06 don't strictly depend on Wave 2 but planner may parallelize them within Wave 3 if no shared file modifications.
- **Plan 02-05 sizing concern:** Full Fannie LLPA matrix + full Freddie eligibility matrix + PMI in one plan is heavy. Planner has discretion to split internally (sub-tasks per predicate within 02-05) but should NOT split into 02-05a / 02-05b without re-discussing — that violates D-02.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Inputs (project-level)

- `.planning/PROJECT.md` — project context, key decisions table, out-of-scope list
- `.planning/REQUIREMENTS.md` — Phase 2 requirements REF-01..09, RUL-01..13 (definitive)
- `.planning/ROADMAP.md` §"Phase 2" — phase goal + success criteria
- `.planning/STATE.md` — current project state, deferred items
- `CLAUDE.md` — money discipline, rules-as-predicates pattern, testing conventions, no Co-Authored-By in commits
- `DATA_CONTRACT.md` — User Layer / System Layer / Data Layer separation; Reference Layer is committed regulatory data

### Phase 2 Research + Patterns

- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-RESEARCH.md` — full research artifact (1492 lines): patterns, per-rule design notes, pitfalls, scope boundaries, suggested decomposition, code examples, sources, assumptions log
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-PATTERNS.md` — analog file mapping for new code
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-VALIDATION.md` — Nyquist validation strategy
- `.planning/research/STACK.md` — full stack verdict matrix (numpy-financial vs alternatives)
- `.planning/research/PITFALLS.md` — "looks done but isn't" checklist; recovery strategies

### Existing Plans (preserved by replan)

- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-01-PLAN.md` — load-bearing vertical slice (REF-01, REF-08, REF-09, RUL-01, RUL-12, RUL-13)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-02-PLAN.md` — FHA limits + MIP (REF-02, REF-03, RUL-04)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-03-PLAN.md` — VA funding fee + residual income (REF-04, REF-05, RUL-06, RUL-07)
- `.planning/phases/02-regulatory-reference-data-rules-predicates/02-04-PLAN.md` — USDA + IRS Pub 936 (REF-06, REF-07, RUL-08, RUL-11)

### Regulatory Sources (HIGH confidence — official publications, all VERIFIED 2026-04-26 in RESEARCH §Sources)

- https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026 — REF-01 source
- https://www.hud.gov/sites/dfiles/hudclips/documents/2025-23hsgml.pdf — HUD ML 2025-23 (2026 FHA limits) — REF-02 source
- https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf — HUD ML 2023-05 (FHA MIP rates) — REF-03 source
- https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf — REF-04 / RUL-06 source
- https://www.rd.usda.gov/files/rd-grhlimitmap.pdf — REF-06 source
- https://www.irs.gov/pub/irs-pdf/p936.pdf — REF-07 / RUL-11 source
- https://singlefamily.fanniemae.com/media/9391/display — Fannie LLPA Matrix (RUL-02 reference data; D-04 ships full matrix)
- *Freddie eligibility matrix URL — planner identifies at YAML-write time; pin specific revision date in `effective:` per RESEARCH Assumption A4*
- https://www.consumerfinance.gov/rules-policy/regulations/1026/22/ — 12 CFR §1026.22 APR tolerances (RUL-10)
- https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition — General QM final rule (RUL-09)
- https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/ — HPA examination procedures (RUL-05)
- https://files.consumerfinance.gov/f/documents/cfpb_combined-reg-z-thresholds-adjustment-rule_2024-11.pdf — Reg Z annual indexed thresholds (RUL-09 ATR/QM loan-amount tiers)

### Pattern References (CITED — implementation pattern source)

- https://github.com/cfpb/hmda-platform — predicate-per-citation pattern
- https://github.com/cfpb/jumbo-mortgage — fail-loud-on-missing-county pattern (verified via WebFetch 2026-04-26)

### Phase 1 Frozen Surface (DO NOT MODIFY in Phase 2)

- `lib/models.py` — Money, Rate, Loan, Payment, Schedule (Phase 1; new Phase 2 types go in `lib/rules/types.py`)
- `lib/money.py` — Decimal money helpers (Phase 1)
- `tests/test_models.py`, `tests/test_money.py` — Phase 1 frozen test surface
- `pyproject.toml` — Phase 2 ADDS `pyyaml>=6.0.2`; do not modify other deps

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`lib/models.py`** (Phase 1): `Money` (Annotated[Decimal, ...] strict-mode-only), `Rate` (Decimal), `Loan` / `Payment` / `Schedule` Pydantic models with `condecimal(max_digits=14, decimal_places=2)`. New `lib/rules/types.py` types compose these (e.g., `Borrower.credit_score: int`, `County.state_fips: str` use Pydantic v2 strict-mode + Field constraints — same shape as Phase 1).
- **`lib/money.py`** (Phase 1): Decimal construction-from-strings + `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` helpers. Predicates that compute fees/MIP/PMI quantize end-of-period using these.
- **`tests/conftest.py`** (Phase 1): existing pytest fixtures pattern. New `tests/test_rules/conftest.py` will follow the same structure (fixture factory for loading JSON-keyed inputs).
- **`tests/fixtures/`** (Phase 1): existing fixture directory. New `tests/fixtures/rules/` is parallel — JSON files keyed by predicate name with `citation` + `source_url` + `comment` fields.
- **`pyproject.toml`** (Phase 1): `[tool.pytest.ini_options]` + `[tool.mypy] strict = true` + `[tool.ruff]` already configured. Phase 2 adds `pyyaml>=6.0.2` via `uv add 'pyyaml>=6.0.2'`.

### Established Patterns

- **Money discipline:** `Decimal` constructed from strings (e.g., `Decimal("0.0175")` for FHA UFMIP rate, NOT `Decimal(0.0175)`). YAML scalars must be QUOTED strings (Pitfall 1: PyYAML downconverts unquoted decimals to float).
- **Pydantic v2 strict mode:** `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` for all domain models. Already established in `lib/models.py`.
- **Test discipline:** Hand-calculated golden-value fixtures with citation comments (card-ops `test_rewards_grocery_cap.py` pattern + Phase 1 `test_fixtures.py` precedent). Use `assert exact_decimal == expected_decimal`, never `assertAlmostEqual` for money.
- **Citation-per-file:** Every `lib/rules/*.py` predicate file has a module docstring with: regulatory citation + source URL + effective date + pattern reference (cfpb/jumbo-mortgage or HMDA Platform). The citation-coverage meta-test (RUL-12, RUL-13) enforces this structurally.
- **Pre-commit hooks:** `.pre-commit-config.yaml` (Phase 1) has ruff + mypy + Phase 1 user-layer block. Plan 02-01 optionally adds `check-yaml` for `data/reference/*.yml`.

### Integration Points

- **`pyproject.toml`** — add `pyyaml>=6.0.2` (Phase 2 first plan)
- **`.pre-commit-config.yaml`** — optional `check-yaml` hook for `data/reference/*.yml`
- **`data/reference/`** — new directory (currently has only `.gitkeep`); Phase 2 ships 9 YAMLs total (7 from REF-01..07 + 2 implementation-detail Fannie/Freddie matrices)
- **`lib/rules/`** — new package directory (currently has only `.gitkeep`); 11 predicate files + `_loader.py` + `types.py` + empty `__init__.py`
- **`tests/test_reference/`** — new test directory for REF-09 schema test
- **`tests/test_rules/`** — new test directory for per-predicate tests + RUL-12 / RUL-13 citation-coverage meta-test
- **`tests/fixtures/rules/`** — new fixture directory (JSON files keyed by predicate)

### Phase 4+ downstream consumers (DO NOT BREAK)

- Phase 3 (Amortization) does NOT consume `lib.rules.*` — schedules don't need predicates
- Phase 4 (Affordability) consumes: `lib.rules.loan_type.classify`, `lib.rules.fha_mip.compute_mip`, `lib.rules.va_residual_income.evaluate` (with stable `binding_rule_citation` per D-11), `lib.rules.fannie_eligibility`, `lib.rules.usda.evaluate`, `lib.rules.atr_qm.passes`
- Phase 6 (Refi NPV) consumes: `lib.rules.conventional_pmi.terminates_at` (HPA at refi: `original_value` resets — Phase 6's job, not RUL-05's)
- Phase 7 (APR) consumes: `lib.rules.reg_z.within_tolerance` (Decimal abs-diff comparison)
- Phase 8 (Stress) does NOT consume `lib.rules.*` directly — re-runs Phase 4 affordability under shock scenarios

</code_context>

<specifics>
## Specific Ideas

- **Wikipedia + CFPB LE oracle fixtures** are Phase 3 (amortization), NOT Phase 2. Phase 2 fixtures are regulator-pinned hand-calc values per HUD ML 2023-05 / VA M26-7 / IRS Pub 936 / FHFA / Fannie LLPA Matrix.
- **`MissingCountyDataError`** (per RUL-01 / cfpb/jumbo-mortgage pattern) is the ONLY user-facing error class in Phase 2 reference-lookup paths. Loader adds `MissingReferenceFieldError` (when YAML missing `source:` / `effective:`) and `StaleReferenceWarning` (>12 months on `effective:`). All "fail loud" per ASVS V7.
- **Citation-coverage test (`tests/test_rules/test_citation_coverage.py`)** is filesystem-introspecting, not a hardcoded list. It auto-discovers new predicates added in plans 02-05, 02-06 and asserts: (a) module docstring contains a non-empty regulatory citation pattern; (b) at least one fixture file in `tests/fixtures/rules/` exists per predicate. Plan 02-07 final-pass verifies the test catches a synthetic "remove citation" + "remove fixture" mutation.
- **Fannie LLPA matrix annual refresh:** D-04 commits to full-matrix shipping. The `effective:` date in `data/reference/fannie-llpa-matrix.yml` should pin the specific Fannie revision date (matrix is published quarterly per RESEARCH Assumption A4); annual refresh = re-extraction from `singlefamily.fanniemae.com/media/9391/display`. Per Pitfall 8, archive the source PDF/page-fetch into `data/reference/sources/` if the planner deems it cheap to do so (otherwise rely on the URL).

</specifics>

<deferred>
## Deferred Ideas

- **`staleness_acknowledged_until` per-file YAML override field** (D-12) — defer to v2 if `StaleReferenceWarning` for FHA MIP 2023 / VA M26-7 2023 becomes noisy in CI. Track as v2 enhancement; do not implement Phase 2.
- **Pre-2023-03-20 FHA MIP rules** — RUL-04 raises `NotImplementedError` for old endorsement dates; full grandfathering deferred to v2 (RESEARCH §Scope Boundaries DEFERRED).
- **Pub 936 points-deductibility (Pub 936 §3)** — RUL-11 returns the loan-limit computation only; points deductibility requires settlement-statement facts the predicate doesn't have. Out of v1.
- **Origination-date grandfathering for HPA high-risk loans** — RUL-05 handles standard + high-risk-midpoint; pre-1999 loans out of scope (HPA is 1999+).
- **Freddie LPA black-box AUS replication** — RUL-03 implements the *published* Eligibility Matrix only, never Freddie's actual LPA AUS decision (per PROJECT.md "Out of Scope").
- **Refi treatment of conventional PMI** — at refi, `original_value` resets; that logic lives in Phase 6 (refi), not in RUL-05.
- **Investment / second-home / cash-out branches in Fannie LLPA matrix** — D-04 ships full matrix, so this becomes IN-SCOPE for Phase 2 (overrides RESEARCH Open Q3's recommendation). No deferral.
- **Annual refresh automation (Playwright scrape of FHFA / HUD / IRS pages)** — v2 (AUTO-01).
- **County geocoding** — caller responsible for `(state_fips, county_fips)` tuples; out of v1.

</deferred>

---

*Phase: 02-regulatory-reference-data-rules-predicates*
*Context gathered: 2026-04-26*
