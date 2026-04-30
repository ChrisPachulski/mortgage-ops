---
phase: 4
slug: affordability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing — Phase 1) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_affordability.py -x --tb=short` |
| **Full suite command** | `pytest -x` |
| **Estimated runtime** | ~10 seconds (affordability targeted); ~20 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run quick command (`pytest tests/test_affordability.py -x --tb=short`)
- **After every plan wave:** Run full suite (`pytest -x`)
- **Before `/gsd-verify-work`:** Full suite must be green + `mypy --strict lib/affordability.py scripts/affordability.py` clean + `ruff check lib/affordability.py scripts/affordability.py tests/test_affordability.py` clean
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

> Filled by planner per PLAN.md task. Each task gets a row mapped to its requirement (AFFD-XX) and threat ref (if applicable).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 04-00..04-05 | 0..5 | AFFD-01..09 | T-04-XX-XX | Per-plan threat models | unit + integration + subprocess | `pytest tests/test_affordability.py -x --tb=short` | tests/test_affordability.py | ⬜ pending |
| 04-06 Task 2 Test 19 | 04-06 | 6 | AFFD-08 | T-04-02-03 | scripts/affordability.py catches MissingCountyDataError → 6-key envelope (BLOCKER 1) | subprocess | `pytest tests/test_affordability.py::test_cli_missing_county_data_emits_six_key_envelope -x` | tests/test_affordability.py + tests/fixtures/affordability/forward_missing_county_data.json | ⬜ pending |
| 04-06 Task 2 Test 20 | 04-06 | 6 | AFFD-07 | T-04-04-01 | VA-residual citation VERBATIM across all 4 regions × {1,4,5} family sizes (BLOCKER 4 + VALIDATION §1) | parametrized unit | `pytest tests/test_affordability.py::test_va_residual_citation_format -x` | tests/test_affordability.py + data/reference/va-residual-income.yml | ⬜ pending |
| 04-06 Task 2 Test 21 | 04-06 | 6 | AFFD-04 | T-04-02-XX | FHA MIP table cells (4 cells per HUD ML 2023-05) all produce non-None monthly_mi (BLOCKER 4 + VALIDATION §1) | parametrized unit | `pytest tests/test_affordability.py::test_fha_mip_compute_per_table_row -x` | tests/test_affordability.py + data/reference/fha-mip-rates.yml | ⬜ pending |
| 04-06 Task 2 Test 22 | 04-06 | 6 | AFFD-07 | T-04-04-XX | LTV ceiling boundary per loan_type (6 loan_types × 2 boundary cases; jumbo over-ceiling skipped) (BLOCKER 4 + VALIDATION §1) | parametrized unit | `pytest tests/test_affordability.py::test_ltv_ceiling_boundary -x` | tests/test_affordability.py + lib/affordability.py LTV_CEILING_BY_TARGET | ⬜ pending |
| 04-06 Task 2 W5 | 04-06 | 6 | AFFD-08 | T-04-01-02 | LTV>0.80 + monthly_pmi=null raises ValidationError (W5 companion to Test 14) | subprocess | `pytest tests/test_affordability.py::test_cli_rejects_missing_monthly_pmi_when_required -x` | tests/test_affordability.py | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Validation Dimensions (from RESEARCH §"Validation Architecture")

### 1. Boundary Fixtures
- **LTV ceilings per loan_type:** Conventional 95% / 97% (FTB), FHA 96.5%, VA 100%, USDA 100%, Jumbo 100%
- **DTI cap:** caller-supplied `max_dti` (no defaults); fixtures exercise pass / exceed paths
- **VA region × family_size:** at least one fixture per region (Northeast, Midwest, South, West) at family_size 1, 4, 5+
- **FHA MIP table rows:** ≤ $726,200 (≤95% LTV / >95% LTV), > $726,200 (≤95% LTV / >95% LTV)
- **Conforming loan-amount limits:** baseline + high-cost county boundary fixtures

### 2. Round-Trip Fixture (SC-2)
- **Reverse → Forward equality:** `Decimal("0.01")` for $ amounts, `Decimal("0.0001")` for DTI rate-of-rounding tolerance
- Fixture: `reverse_conventional_80_ltv_43_dti.json` runs reverse mode, then forwards `max_loan_amount + down_payment` back through forward mode and asserts dti_back ≤ max_dti + 0.0001

### 3. Citation-Coverage (Phase 2 RUL-12/13 inheritance)
Every `blocked_by` citation string format introduced in Phase 4 production code MUST be exercised by ≥ 1 fixture:
- `FHFA-LIMIT-{LOAN_TYPE}-{COUNTY}` or `HUD-LIMIT-...`
- `LTV-CEILING-{LOAN_TYPE}`
- `DTI-CAP-{LOAN_TYPE}`
- `ATR-QM-PRICE-FIRST` / `ATR-QM-PRICE-SUBORDINATE`
- `VA-RESIDUAL-{REGION}-FAMILY-{N}` (verbatim per Phase 2 D-11)

### 4. Joint-Applicant
- 1-applicant fixture (`single_applicant.json`): list of length 1 reduces to single income / single credit_score
- 2-applicant fixture (`joint_applicants_two_incomes.json`): income sum + lower credit_score selection (SC-5)

### 5. End-to-End (SC-4)
- Fixture `household_example_yml_e2e.json` invokes `scripts/affordability.py --input <generated_request_pointing_at_household.example.yml>`
- Subprocess invocation pattern (Phase 3 D-17 portability) — does NOT import `scripts.affordability`

---

## Wave 0 Requirements

- [ ] `tests/test_affordability.py` — file exists with import skeleton + `affordability_fixture` loader signature
- [ ] `tests/conftest.py` — extended with `affordability_fixture` mirroring Phase 3's `amortize_fixture`
- [ ] `tests/fixtures/affordability/` — directory created with `.gitkeep` (or first fixture)
- [ ] No new framework install required (pytest already configured Phase 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--help` text reads cleanly to a human | AFFD-08 (Decision #10) | Subjective UX read | Run `python scripts/affordability.py --help`; verify it documents `mode`, `--input`, both forward and reverse usage examples, and the UFMIP financing convention chosen (per D-03) |
| `config/household.example.yml` field-level docstring comments are accurate and pedagogically clear | AFFD-09 D-15 | Readability judgement | Open the file; verify each new field has a `# unit / constraint / which citation it feeds` comment block per D-15 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (tests/test_affordability.py, tests/conftest.py extension, tests/fixtures/affordability/)
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
