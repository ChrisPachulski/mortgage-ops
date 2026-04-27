---
phase: 2
slug: regulatory-reference-data-rules-predicates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Sourced from `02-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (already configured by Phase 1) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (no changes) |
| **Quick run command** | `uv run pytest tests/ -x --tb=short` |
| **Full suite command** | `uv run pytest && uv run mypy --strict . && uv run ruff check . && uv run ruff format --check .` |
| **Estimated runtime** | ~5–10 seconds (pure-Python predicates over small YAML; no network, no DB) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --tb=short` (suite is fast — no need to subset)
- **After every plan wave:** Run `uv run pytest && uv run mypy --strict . && uv run ruff check . && uv run ruff format --check .`
- **Before `/gsd-verify-work`:** Full suite green AND `mypy --strict --warn-unused-ignores` green AND pre-commit (incl. `check-yaml` if installed) green on `data/reference/*.yml`
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

> Plan/wave/task IDs become concrete once `gsd-planner` writes `02-NN-PLAN.md` files. The mapping below is keyed by REQ-ID; planner is responsible for inheriting the `Automated Command` column verbatim into each task's `<automated>` block.

| Req | Plan (TBD) | Wave (TBD) | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists |
|-----|------------|------------|------------|-----------------|-----------|-------------------|-------------|
| REF-01 | TBD | TBD | — | YAML conforming-limits-2026.yml has `source:` URL, `effective:` date, baseline=$832,750 | schema + fixture | `uv run pytest tests/test_reference/test_schema.py -k conforming-limits-2026 -x` | ❌ W0 |
| REF-02 | TBD | TBD | — | YAML fha-limits-2026.yml has source/effective, floor=$541,287 | schema | `uv run pytest tests/test_reference/test_schema.py -k fha-limits-2026 -x` | ❌ W0 |
| REF-03 | TBD | TBD | — | YAML fha-mip-rates.yml has UFMIP=0.0175 + ≥1 annual MIP row | schema + RUL-04 round-trip | `uv run pytest tests/test_rules/test_fha_mip.py -x` | ❌ W0 |
| REF-04 | TBD | TBD | — | YAML va-funding-fees.yml has IRRRL=0.005, first-use-zero-down=0.0215 | schema + RUL-06 round-trip | `uv run pytest tests/test_rules/test_va_funding_fee.py -x` | ❌ W0 |
| REF-05 | TBD | TBD | — | YAML va-residual-income.yml has 4 regions × ≥5 family sizes × 2 loan bands | schema + RUL-07 round-trip | `uv run pytest tests/test_rules/test_va_residual_income.py -x` | ❌ W0 |
| REF-06 | TBD | TBD | — | YAML usda-income-limits.yml has default 1-4 limit + ≥1 county override + guarantee fees | schema + RUL-08 round-trip | `uv run pytest tests/test_rules/test_usda.py -x` | ❌ W0 |
| REF-07 | TBD | TBD | — | YAML irs-pub936.yml has $750k post-2017 + $1M grandfathered caps + grace period | schema + RUL-11 round-trip | `uv run pytest tests/test_rules/test_irs_pub936.py -x` | ❌ W0 |
| REF-08 | TBD | TBD | T-2-STALE | `StaleReferenceWarning` fires on import when `effective:` > 12 months old (captured via `pytest.warns(...)`) | unit (warns) | `uv run pytest tests/test_rules/test_loader.py::test_staleness_warning_fires_for_old_yaml -x` | ❌ W0 |
| REF-09 | TBD | TBD | — | Every `data/reference/*.yml` has `source:` URL + `effective:` date — meta test parametrizes over filesystem | meta | `uv run pytest tests/test_reference/test_schema.py -x` | ❌ W0 |
| RUL-01 | TBD | TBD | T-2-COUNTY | `loan_type.classify()` returns correct enum for high-cost ceiling, low-cost baseline, FHA floor, FHA ceiling; raises `MissingCountyDataError` when county is None | unit + ≥5 fixtures | `uv run pytest tests/test_rules/test_loan_type.py -x` | ❌ W0 |
| RUL-02 | TBD | TBD | — | `fannie_eligibility` LLPA lookup correct at 700/719/720/739/740 credit-score bucket boundaries | unit + ≥5 boundary fixtures | `uv run pytest tests/test_rules/test_fannie_eligibility.py -x` | ❌ W0 |
| RUL-03 | TBD | TBD | — | `freddie_eligibility` matches Fannie on common cases; differs on Freddie-specific overlay | unit + ≥3 fixtures | `uv run pytest tests/test_rules/test_freddie_eligibility.py -x` | ❌ W0 |
| RUL-04 | TBD | TBD | — | `fha_mip.compute()` correct UFMIP + annual MIP for LTV>90 (life-of-loan) and LTV≤90 (132-mo termination); raises `NotImplementedError` for endorsement_date<2023-03-20 | unit + ≥3 fixtures | `uv run pytest tests/test_rules/test_fha_mip.py -x` | ❌ W0 |
| RUL-05 | TBD | TBD | — | `conventional_pmi.status()` returns `"auto_terminated"` at exactly 0.78 LTV, `"request_eligible"` at 0.80 LTV, `"in_force"` above; high-risk variant uses midpoint | unit + ≥4 fixtures | `uv run pytest tests/test_rules/test_conventional_pmi.py -x` | ❌ W0 |
| RUL-06 | TBD | TBD | — | `va_funding_fee.compute()` returns 0 when exempt; correct % across (purchase/refi, first/subsequent, down-payment bands); IRRRL = 0.005 | unit + ≥6 fixtures | `uv run pytest tests/test_rules/test_va_funding_fee.py -x` | ❌ W0 |
| RUL-07 | TBD | TBD | — | `va_residual_income.evaluate()` returns `pass`/`fail` + `binding_rule_citation` string | unit + ≥4 fixtures (one per region × pass/fail) | `uv run pytest tests/test_rules/test_va_residual_income.py -x` | ❌ W0 |
| RUL-08 | TBD | TBD | — | `usda.evaluate()` distinguishes income-eligible vs not; correct guarantee fee | unit + ≥3 fixtures | `uv run pytest tests/test_rules/test_usda.py -x` | ❌ W0 |
| RUL-09 | TBD | TBD | — | `atr_qm.general_qm_passes()` returns True/False at price-based-test thresholds across all loan-amount tiers | unit + ≥6 fixtures (per (lien × loan-amount-band) cell + boundary) | `uv run pytest tests/test_rules/test_atr_qm.py -x` | ❌ W0 |
| RUL-10 | TBD | TBD | — | `reg_z.within_apr_tolerance()` returns True for ±1/8 pp regular and ±1/4 pp irregular; False above | unit + ≥4 fixtures | `uv run pytest tests/test_rules/test_reg_z.py -x` | ❌ W0 |
| RUL-11 | TBD | TBD | — | `irs_pub936.qualified_loan_limit()` returns $750k post-2017 single, $1M grandfathered, half for MFS, grace-period handling | unit + ≥4 fixtures | `uv run pytest tests/test_rules/test_irs_pub936.py -x` | ❌ W0 |
| RUL-12 | TBD | TBD | — | Every `lib/rules/*.py` predicate has docstring with `Citation:` / `Source URL:` / `Effective:` | meta (parametrized over filesystem) | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring -x` | ❌ W0 |
| RUL-13 | TBD | TBD | — | Every `lib/rules/*.py` predicate has ≥1 `tests/fixtures/rules/{stem}_*.json` fixture | meta (parametrized over filesystem) | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_at_least_one_fixture -x` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · W0 = supplied by Wave 0*

---

## Wave 0 Requirements

- [ ] `tests/test_reference/__init__.py` — empty marker
- [ ] `tests/test_rules/__init__.py` — empty marker
- [ ] `tests/fixtures/rules/__init__.py` — empty marker
- [ ] `tests/test_reference/test_schema.py` — REF-09 parametrized loader (asserts `source:` + `effective:` on every `data/reference/*.yml`)
- [ ] `tests/test_rules/test_citation_coverage.py` — RUL-12 + RUL-13 meta-tests (parametrize over `lib/rules/*.py`, exclude `__init__.py`, `_loader.py`, `types.py`)
- [ ] `tests/test_rules/test_loader.py` — REF-08 staleness via `pytest.warns(StaleReferenceWarning)` (uses `tmp_path` to fabricate a stale YAML, then triggers loader)
- [ ] `lib/rules/__init__.py` — empty (no re-exports — predicate-per-file discipline)
- [ ] `lib/rules/_loader.py` — single shared loader: `lru_cache(maxsize=None)` + `StaleReferenceWarning` + Decimal-from-string parser
- [ ] `lib/rules/types.py` — `LoanType`, `Region`, `County`, `Borrower`, `Property` Pydantic v2 types (kept out of `lib/models.py` so Phase 1's frozen models stay untouched)
- [ ] `pyproject.toml` — add `pyyaml` (≥6.0) to dependencies + regenerate `uv.lock`
- [ ] `.pre-commit-config.yaml` — optionally add `check-yaml` hook scoped to `data/reference/*.yml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Source-URL freshness audit (regulator pages still resolve, current numeric tables still match) | REF-01..07 | Annual data refresh; web fetches not appropriate in CI | Once per year (~Jan), open each `source:` URL listed in `data/reference/*.yml`, confirm 200 OK and the published table still matches the YAML body; if changed, edit YAML + bump `effective:` date + commit |
| Pre-existing `StaleReferenceWarning` for HUD ML 2023-05 (effective 2023-03-20) and VA M26-7 (effective 2023-04-07) is acceptable on import | REF-08 | Regulators have not republished these as of phase planning; warning is informational, not an error | Confirm `python -c "import lib.rules.fha_mip, lib.rules.va_funding_fee"` emits warnings to stderr and exits 0; pytest must NOT promote `StaleReferenceWarning` to error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test infrastructure stubs above)
- [ ] No watch-mode flags in test commands (CI must terminate)
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter once planner has filled in Plan/Wave/Task IDs

**Approval:** pending
