# Phase 2: Regulatory Reference Data & Rules Predicates — Research

**Researched:** 2026-04-26
**Domain:** Cited regulatory reference data (YAML) + one-predicate-per-citation rules library that every later calc phase composes
**Confidence:** HIGH for reference-data shapes / loader / staleness / test-discipline; HIGH for citation URLs; MEDIUM for the *exact 2026 numeric tables* (planner SHOULD treat the published PDFs/XLSXs as the system of record and re-extract; this research pins the structure, not every cell)

## Summary

Phase 2 builds the **regulatory backbone** of mortgage-ops. It ships:

1. **Seven YAML files** under `data/reference/` (REF-01..07), each carrying a `source:` URL pointing to the regulator's primary publication and an `effective:` ISO-8601 date. These files are the single source of truth for the 2026 conforming/FHA/VA/USDA/IRS parameters.
2. **One Python loader module** (`lib/rules/_loader.py`) that reads any reference YAML, caches it, validates schema, and emits a `stderr` warning when `effective:` is older than 12 months (REF-08).
3. **Eleven rules predicates** (RUL-01..11) under `lib/rules/`, each a single file tied to a single regulatory citation (12 CFR §X.Y, HUD ML, Pub. 936 worksheet, etc.) with a docstring header that captures the citation, source URL, and effective date.
4. **One citation-coverage test** (`tests/test_rules/test_citation_coverage.py`, RUL-12+RUL-13) that enumerates every `lib/rules/*.py` file and asserts each has (a) a regulatory-citation docstring and (b) at least one fixture file under `tests/fixtures/rules/`.
5. **One schema test** (`tests/test_reference/test_schema.py`, REF-09) that loads every `data/reference/*.yml` and asserts `source:` (URL) and `effective:` (date) are present.

No mortgage *math* is computed here. Predicates return booleans, enums, or numeric-rate-table values — never amortization rows, never PMTs. Phases 4 (affordability), 5 (ARM), 6 (refi), 8 (stress) compose these predicates; Phase 2 only wires the contracts.

**Primary recommendation:** Decompose into seven plans organized by regulatory regime (not by file count) so each plan ships one or two YAML files plus the rules predicates that read them — keeps the regulator → reference-YAML → predicate → fixture → test chain tight in each plan. Plan 02-01 builds the loader + first reference file (conforming limits) + RUL-01 loan_type as a vertical slice that proves the whole pattern; subsequent plans fan out to FHA, VA, USDA, IRS, and ATR/QM-Reg-Z; the final plan ships only the citation-coverage test.

## User Constraints

No `CONTEXT.md` exists for Phase 2 — phase ran straight to research without `/gsd-discuss-phase`. Project-level constraints from `CLAUDE.md`, `.planning/PROJECT.md`, and the four immutable-contract artifacts shipped in Phase 1 (`lib/money.py`, `lib/models.py`, `tests/conftest.py::golden_fixture`, `tests/fixtures/golden_pmt.json`) apply. They are listed under **Project Constraints (from CLAUDE.md)** below.

## Phase Requirements

| ID | Description | Research Support (where in this RESEARCH the planner reads) |
|----|-------------|-------------------------------------------------------------|
| REF-01 | `data/reference/conforming-limits-2026.yml` — FHFA baseline + ceiling + per-county lookup, source URL, effective date | §"Reference YAML — REF-01 conforming-limits-2026.yml"; FHFA news release URL pinned [VERIFIED] |
| REF-02 | `data/reference/fha-limits-2026.yml` — FHA floor/ceiling + per-county lookup | §"Reference YAML — REF-02"; HUD ML 2025-23 URL pinned [VERIFIED] |
| REF-03 | `data/reference/fha-mip-rates.yml` — UFMIP + annual MIP per term/LTV/loan-amount tier | §"Reference YAML — REF-03"; HUD ML 2023-05 URL pinned [VERIFIED] |
| REF-04 | `data/reference/va-funding-fees.yml` — first-use/subsequent-use/IRRRL/cash-out tables | §"Reference YAML — REF-04"; VA M26-7 Chapter 8 URL pinned [VERIFIED] |
| REF-05 | `data/reference/va-residual-income.yml` — geographic × family-size × loan-amount table | §"Reference YAML — REF-05"; VA Lender Handbook M26-7 [CITED] |
| REF-06 | `data/reference/usda-income-limits.yml` — 115%-of-AMI thresholds | §"Reference YAML — REF-06"; USDA RD income limits PDF URL pinned [VERIFIED] |
| REF-07 | `data/reference/irs-pub936.yml` — $750k cap (post-2017), $1M cap (grandfathered), points deductibility | §"Reference YAML — REF-07"; IRS Pub 936 PDF URL pinned [VERIFIED] |
| REF-08 | Startup-time staleness check warns when any reference YAML's `effective:` is > 12 months old | §"Loader pattern — Staleness check (REF-08)" |
| REF-09 | Tests assert every reference YAML has `source:` URL and `effective:` date fields | §"Test discipline — Schema test (REF-09)" |
| RUL-01 | `lib/rules/loan_type.py` classifies conforming / high-balance / jumbo / FHA / FHA-HB / VA / VA-HB / USDA based on county; fails loud when county missing | §"Per-rule design — RUL-01 loan_type" |
| RUL-02 | `lib/rules/fannie_eligibility.py` — LLPA matrix lookup (credit-score × LTV × loan-purpose) | §"Per-rule design — RUL-02 fannie_eligibility" |
| RUL-03 | `lib/rules/freddie_eligibility.py` — equivalent LPA-published checks | §"Per-rule design — RUL-03 freddie_eligibility" |
| RUL-04 | `lib/rules/fha_mip.py` — UFMIP + annual MIP per HUD ML 2023-05 with origination-date grandfathering | §"Per-rule design — RUL-04 fha_mip" |
| RUL-05 | `lib/rules/conventional_pmi.py` — HPA auto-termination at 78% LTV, request at 80% LTV | §"Per-rule design — RUL-05 conventional_pmi" |
| RUL-06 | `lib/rules/va_funding_fee.py` — VA funding fee per M26-7 | §"Per-rule design — RUL-06 va_funding_fee" |
| RUL-07 | `lib/rules/va_residual_income.py` — residual income vs geographic × family-size × loan-amount table | §"Per-rule design — RUL-07 va_residual_income" |
| RUL-08 | `lib/rules/usda.py` — 115% AMI income limit + guarantee fee | §"Per-rule design — RUL-08 usda" |
| RUL-09 | `lib/rules/atr_qm.py` — General QM price-based test (Mar 2021 final rule) | §"Per-rule design — RUL-09 atr_qm" |
| RUL-10 | `lib/rules/reg_z.py` — Reg Z disclosure tolerances (1/8 pct regular, 1/4 pct irregular) | §"Per-rule design — RUL-10 reg_z" |
| RUL-11 | `lib/rules/irs_pub936.py` — qualified loan limit worksheet ($750k post-2017 cap) | §"Per-rule design — RUL-11 irs_pub936" |
| RUL-12 | Every rules predicate has docstring with regulatory citation | §"Test discipline — Citation-coverage test (RUL-12 + RUL-13)" |
| RUL-13 | 1:1 test-to-citation: every predicate has at least one fixture per citation | §"Test discipline — Citation-coverage test (RUL-12 + RUL-13)" |

## Project Constraints (from CLAUDE.md)

These are non-negotiable for every Phase 2 deliverable:

- **Decimal for all money** — no float in money expressions. The MIP rates, LLPA bps, funding-fee percentages, USDA income limits all parse as `Decimal(str_value)`. YAML scalar types yield strings if quoted; **always quote money/rate values in the YAML** so PyYAML doesn't downconvert to float.
- **`ROUND_HALF_UP` end-of-period only** — predicates that compute fees (e.g., `va_funding_fee.compute()`, `fha_mip.compute_annual_premium()`) must call `lib.money.quantize_cents()` exactly once per dollar return value.
- **Pydantic v2 at boundaries** — predicates accept Pydantic model inputs (e.g., `Loan`, an extended `Property` or `Borrower` model) and return Pydantic model outputs or simple typed values (`bool`, `Decimal`, `Literal[...]` enum). No raw dicts crossing the predicate API.
- **Rules-as-predicates (HMDA Platform pattern, ALREADY DECIDED)** — one file per regulatory citation in `lib/rules/`. Docstring includes citation. 1:1 test-to-citation mapping. Big rule engines forbidden.
- **Reference data discipline** — all regulatory parameters in `data/reference/*.yml` with `source:` URL and `effective:` date. **Annual refresh = YAML edit + commit, never code change.** Startup-time staleness check warns when `effective:` is > 12 months old.
- **Hand-calculated golden fixtures with citation comments** — every test fixture has a comment naming the regulatory source (HUD ML 2023-05 Table A; FHFA news release of 2025-12-04; etc.). Exact Decimal equality, never `pytest.approx`.
- **Fail loud on missing inputs** — `lib/rules/loan_type.py` raises `MissingCountyDataError` when county is None. Adopt the cfpb/jumbo-mortgage `{success: false, needCounty: true}` shape but in Pythonic exception form. No silent baseline fallback.
- **No Co-Authored-By or AI attribution in commits** — global user rule.
- **Sibling-repo prior art** — `cfpb/hmda-platform` (Scala, predicate-per-citation), `cfpb/jumbo-mortgage` (JS, fail-loud-on-missing-county). Read for shape; do not vendor code.
- **Phase-1 contracts are immutable** — `lib/money.py` exports `to_money`, `quantize_cents`, `CENT`, `MONEY_CONTEXT`. `lib/models.py` exports `Money`, `Rate`, `Loan`, `Payment`, `Schedule` with `ConfigDict(strict=True, frozen=True, extra="forbid")`. Phase 2 imports from these; never duplicates them.

## Architectural Responsibility Map

Phase 2 is single-tier (Python library — no UI/API split yet). The "tiers" here correspond to the project's library-internal layers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Regulatory data storage | Reference Layer (`data/reference/*.yml`) | — | Annually-refreshed YAML; committed; auditable history; loader only reads |
| Reference loading + caching + staleness | Library (`lib/rules/_loader.py`) | — | Single shared loader so all 11 predicates use the same cache + warning behavior |
| Regulatory predicates | Library (`lib/rules/*.py`) | — | One file per citation; pure functions; predicates return bool / Decimal / enum |
| Domain-model extensions for rules | Library (`lib/models.py` extension or `lib/rules/types.py`) | — | New input/output types (`LoanType` enum, `Property` model, `Borrower` model with credit_score/family_size/region); add to `lib/models.py` so Phase 4+ shares them |
| Citation/schema discipline | Test layer (`tests/test_rules/test_citation_coverage.py`, `tests/test_reference/test_schema.py`) | — | Meta-tests that scan filesystem for predicate files + reference YAML and assert structural invariants |
| Hand-calc golden fixtures | Test fixture layer (`tests/fixtures/rules/*.json` and/or `*.yml`) | — | Per-citation fixtures with regulator-source comments; consumed by per-predicate test files |

**No Claude/skill surface in Phase 2.** Skill (Phase 10) and subagents (Phase 11) consume these predicates indirectly via Phase 4+ scripts.

## Standard Stack

### Core (already in pyproject.toml from Phase 1; Phase 2 ADDS pyyaml)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyyaml | >=6.0.2 | Parse `data/reference/*.yml` | De-facto YAML lib; safe_load; no eval risk; CLAUDE.md/STACK.md call this out by name [VERIFIED: STACK.md "Supporting Libraries"] |
| pydantic | >=2.13.3 (already pinned) | Validate loaded YAML against schemas; type the predicate inputs/outputs | First-class Decimal; strict mode rejects coerced types [CITED: docs.pydantic.dev/2.x] |
| python-dateutil | >=2.9.0 (already pinned) | `relativedelta(months=12)` for staleness check | Handles month-end edges; already in lockfile [VERIFIED: PyPI 2024-03-01] |

**Installation:**
```bash
uv add 'pyyaml>=6.0.2'
# (pydantic and python-dateutil are already in Phase 1's pyproject.toml — do not re-add)
```

**Version verification:**
```bash
uv run python -c "import yaml; print(yaml.__version__)"   # expect 6.0.2 or newer
```

### Supporting (test-only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0 (already pinned) | Test framework | Per-predicate fixture files + parametrize for table tests |
| pytest's `caplog` / `capsys` fixtures | builtin | Capture stderr to assert staleness warning fires | REF-08 test |

### Alternatives Considered (and rejected)

| Recommended | Alternative | Why Rejected |
|-------------|-------------|--------------|
| pyyaml `safe_load` | tomli + TOML format | YAML supports comments inline (we want `# Source: HUD ML 2023-05 Table A` next to each rate); TOML doesn't support inline structured comments as cleanly. Project decision (CONVENTIONS.md) is YAML. |
| pyyaml `safe_load` | json | Same comment problem; YAML chosen project-wide for reference data |
| Pydantic-validated YAML | unvalidated dict | Phase 1 set the precedent: every boundary validated. Annual refreshes will introduce typos if unvalidated. |
| `warnings.warn` for staleness | `logging.warning` | `warnings` is the Python convention for "library tells caller something is off"; `logging` would require user to configure handlers. `warnings.warn(..., stacklevel=2)` integrates with pytest's `recwarn` fixture for test capture. |
| Functional caching with `functools.lru_cache` on path | Module-level dict cache | `lru_cache` is the Python idiom; thread-safe; introspectable for cache_clear in tests. **Use `lru_cache(maxsize=None)`** so the cache survives the process. |
| One-file-per-predicate | `lib/rules/__init__.py` re-exports + flat namespace | HMDA Platform pattern is per-citation files; flat namespace defeats the audit trail. Keep one file per citation; `__init__.py` empty (no re-exports — predicates import directly). |

## Architecture Patterns

### System Architecture Diagram

```
                   ┌─────────────────────────────────────────────────┐
                   │            data/reference/  (committed)         │
                   │   conforming-limits-2026.yml                    │
                   │   fha-limits-2026.yml                           │
                   │   fha-mip-rates.yml                             │
                   │   va-funding-fees.yml                           │
                   │   va-residual-income.yml                        │
                   │   usda-income-limits.yml                        │
                   │   irs-pub936.yml                                │
                   │   each: source: URL  +  effective: YYYY-MM-DD   │
                   └────────────────────┬────────────────────────────┘
                                        │  yaml.safe_load
                                        ▼
                   ┌─────────────────────────────────────────────────┐
                   │   lib/rules/_loader.py                          │
                   │   • load_reference(name) -> dict (lru_cache)    │
                   │   • _check_staleness(effective: date)           │
                   │     warnings.warn to stderr if > 12mo old       │
                   └────────────────────┬────────────────────────────┘
                                        │  module-import-time
                                        ▼
            ┌──────────────────────────────────────────────────────────────┐
            │                    lib/rules/  (one file per citation)       │
            │                                                              │
            │  loan_type.py             ← FHFA + HUD limits (REF-01,02)    │
            │  fannie_eligibility.py    ← Fannie LLPA matrix               │
            │  freddie_eligibility.py   ← Freddie LPA-published checks     │
            │  fha_mip.py               ← HUD ML 2023-05 (REF-03)          │
            │  conventional_pmi.py      ← HPA 1998 §4901-4910              │
            │  va_funding_fee.py        ← VA M26-7 Ch.8 (REF-04)           │
            │  va_residual_income.py    ← VA M26-7 (REF-05)                │
            │  usda.py                  ← USDA RD GLP (REF-06)             │
            │  atr_qm.py                ← 12 CFR §1026.43 General QM       │
            │  reg_z.py                 ← 12 CFR §1026.22 tolerances       │
            │  irs_pub936.py            ← IRS Pub 936 (REF-07)             │
            │                                                              │
            │  Each: docstring with citation; pure functions;              │
            │        Pydantic-typed I/O; quantize_cents on $ output        │
            └────────────────────┬─────────────────────────────────────────┘
                                 │  imported by Phase 4+ scripts
                                 ▼
                          ┌──────────────────────────────────────┐
                          │  Phase 4 (affordability) composes    │
                          │  Phase 5 (ARM) composes              │
                          │  Phase 6 (refi) composes             │
                          │  Phase 8 (stress) composes           │
                          └──────────────────────────────────────┘

            ┌──────────────────────────────────────────────────────────────┐
            │                       tests/                                 │
            │                                                              │
            │  test_reference/test_schema.py    REF-09 (every YAML has     │
            │                                            source+effective) │
            │                                                              │
            │  test_rules/                                                 │
            │   ├─ test_loan_type.py     RUL-01 + fixtures/rules/loan_*.json│
            │   ├─ test_fha_mip.py       RUL-04 + fixtures/rules/fha_mip_*.json│
            │   ├─ test_conventional_pmi.py …                              │
            │   ├─ ...one test file per citation...                        │
            │   ├─ test_loader.py        REF-08 staleness via capsys       │
            │   └─ test_citation_coverage.py  RUL-12 + RUL-13              │
            │                                                              │
            │  fixtures/rules/                                             │
            │   ├─ loan_type_high_cost_ceiling.json                        │
            │   ├─ loan_type_low_cost_baseline.json                        │
            │   ├─ fha_mip_term30_ltv95.json                               │
            │   ├─ ...one or more per citation...                          │
            └──────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (Phase 2 additions)

```
mortgage-ops/
├── data/
│   └── reference/                            # already exists from Phase 1 (.gitkeep only)
│       ├── conforming-limits-2026.yml        # REF-01
│       ├── fha-limits-2026.yml               # REF-02
│       ├── fha-mip-rates.yml                 # REF-03
│       ├── va-funding-fees.yml               # REF-04
│       ├── va-residual-income.yml            # REF-05
│       ├── usda-income-limits.yml            # REF-06
│       └── irs-pub936.yml                    # REF-07
├── lib/
│   ├── models.py                             # Phase 1 file — extend with new types here
│   └── rules/                                # NEW
│       ├── __init__.py                       # empty (no re-exports)
│       ├── _loader.py                        # YAML loader + staleness check (REF-08)
│       ├── types.py                          # NEW Pydantic types (LoanType enum, Region enum, Borrower, Property)
│       ├── loan_type.py                      # RUL-01
│       ├── fannie_eligibility.py             # RUL-02
│       ├── freddie_eligibility.py            # RUL-03
│       ├── fha_mip.py                        # RUL-04
│       ├── conventional_pmi.py               # RUL-05
│       ├── va_funding_fee.py                 # RUL-06
│       ├── va_residual_income.py             # RUL-07
│       ├── usda.py                           # RUL-08
│       ├── atr_qm.py                         # RUL-09
│       ├── reg_z.py                          # RUL-10
│       └── irs_pub936.py                     # RUL-11
└── tests/
    ├── test_reference/
    │   ├── __init__.py
    │   └── test_schema.py                    # REF-09
    ├── test_rules/
    │   ├── __init__.py
    │   ├── test_loader.py                    # REF-08 (staleness)
    │   ├── test_loan_type.py                 # RUL-01 fixtures
    │   ├── test_fannie_eligibility.py        # RUL-02
    │   ├── test_freddie_eligibility.py       # RUL-03
    │   ├── test_fha_mip.py                   # RUL-04
    │   ├── test_conventional_pmi.py          # RUL-05
    │   ├── test_va_funding_fee.py            # RUL-06
    │   ├── test_va_residual_income.py        # RUL-07
    │   ├── test_usda.py                      # RUL-08
    │   ├── test_atr_qm.py                    # RUL-09
    │   ├── test_reg_z.py                     # RUL-10
    │   ├── test_irs_pub936.py                # RUL-11
    │   └── test_citation_coverage.py         # RUL-12 + RUL-13 (meta-test)
    └── fixtures/
        └── rules/                            # NEW
            ├── __init__.py                   # empty marker (mypy --strict)
            ├── loan_type_*.json              # per-citation fixtures
            ├── fha_mip_*.json
            ├── conventional_pmi_*.json
            ├── va_funding_fee_*.json
            ├── va_residual_*.json
            ├── usda_*.json
            ├── atr_qm_*.json
            ├── reg_z_*.json
            ├── irs_pub936_*.json
            ├── fannie_llpa_*.json
            └── freddie_eligibility_*.json
```

**Why this layout:**
- `lib/rules/_loader.py` underscored = private; per-predicate files import `from ._loader import load_reference` only. Test files import `from lib.rules._loader import load_reference` for the staleness test.
- `lib/rules/types.py` is added so `LoanType`, `Region`, `Borrower`, `Property` types are shared across predicates without churning `lib/models.py`'s Phase-1-locked surface (Loan/Schedule/Payment).
- `tests/test_rules/` and `tests/test_reference/` mirror the source layout per pytest convention.
- `tests/fixtures/rules/` holds per-citation JSON files; the citation-coverage test uses filename-prefix matching (`{rule_module}_*.json`) to enforce 1:1 fixture-to-citation.

### Pattern 1: Cited Reference YAML

**What:** Every regulatory YAML carries `source:` (URL) and `effective:` (ISO-8601 date) at top level, plus a `notes:` field for regulator commentary. The data body sits under regulator-specific keys.

**Skeleton:**
```yaml
# data/reference/conforming-limits-2026.yml
source: "https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026"
effective: 2026-01-01
notes: "FHFA news release of 2025-12-04. Effective for loans with pool issue dates on or after 2026-01-01."
limits:
  baseline:
    one_unit: "832750"
    two_unit: "1066250"
    three_unit: "1289100"
    four_unit: "1601650"
  ceiling:
    one_unit: "1249125"
    two_unit: "1599375"
    three_unit: "1933200"
    four_unit: "2402625"
  high_cost_counties:
    # Per-county overrides where county-CLL exceeds baseline. Source: FHFA county XLSX.
    # Each entry: state_fips + county_fips → one_unit limit (other unit counts derivable).
    # NOTE: we ship the high-cost subset only; baseline applies to all unlisted counties.
    - state_fips: "06"
      county_fips: "075"
      county_name: "San Francisco"
      one_unit: "1249125"
    # ...etc; ~232 high-cost counties for 2026 per FHFA map
```

**Quoting convention:** Money/rate values are quoted strings so PyYAML emits `str` not `int`/`float`. The loader does `Decimal(str_value)`. Dates are unquoted (PyYAML emits `datetime.date`).

### Pattern 2: Loader with lru_cache + staleness warning

**What:** A single `load_reference(name: str) -> dict` function reads any YAML by file stem, caches it for the process lifetime, and emits a `warnings.warn` to stderr at first load if `effective:` is > 12 months old.

**Why one shared loader:** Otherwise 11 predicates each need their own caching + warning logic, and the warning fires N times. Centralizing also lets the test suite assert staleness via `capsys`/`recwarn` once.

**Concrete:**
```python
# lib/rules/_loader.py
"""Reference-data loader for lib/rules/ predicates.

Single source of truth for YAML loading + staleness checks (REF-08). Every
lib/rules/*.py imports load_reference from here; no module rolls its own loader.

Annual regulatory refresh = edit data/reference/*.yml + bump `effective:` field.
No code change. Predicates auto-pick up the new values on next process start
because lru_cache lives across tests but resets per pytest session.
"""
from __future__ import annotations

import warnings
from datetime import date
from decimal import Decimal  # noqa: F401  # re-export hint for predicate consumers
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import yaml
from dateutil.relativedelta import relativedelta

REFERENCE_DIR: Final[Path] = Path(__file__).parent.parent.parent / "data" / "reference"
STALENESS_THRESHOLD: Final[relativedelta] = relativedelta(months=12)


class StaleReferenceWarning(UserWarning):
    """Emitted at module-load time when a reference YAML's effective date is
    more than 12 months in the past. Loud-by-default; never suppressed by
    library code. Tests use `pytest.warns(StaleReferenceWarning)` to assert.
    """


class MissingReferenceFieldError(KeyError):
    """Raised when a reference YAML is missing `source:` or `effective:` (REF-09)."""


@lru_cache(maxsize=None)
def load_reference(name: str) -> dict[str, Any]:
    """Load data/reference/{name}.yml, validate top-level fields, warn if stale.

    Args:
        name: stem of the YAML file (e.g. "conforming-limits-2026").

    Returns:
        Parsed dict. `source` is str; `effective` is datetime.date.

    Raises:
        FileNotFoundError: if the file does not exist
        MissingReferenceFieldError: if `source:` or `effective:` is missing
    """
    path = REFERENCE_DIR / f"{name}.yml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text())
    if "source" not in raw:
        raise MissingReferenceFieldError(f"{name}.yml missing required `source:` field")
    if "effective" not in raw:
        raise MissingReferenceFieldError(f"{name}.yml missing required `effective:` field")
    _check_staleness(name, raw["effective"])
    return raw


def _check_staleness(name: str, effective: date) -> None:
    """Emit StaleReferenceWarning to stderr if effective is > 12 months old (REF-08)."""
    threshold_date = date.today() - STALENESS_THRESHOLD
    if effective < threshold_date:
        warnings.warn(
            f"Reference data {name!r} has effective={effective.isoformat()}, which is "
            f"more than 12 months old (threshold: {threshold_date.isoformat()}). "
            f"Annual regulatory refresh may be overdue.",
            category=StaleReferenceWarning,
            stacklevel=2,
        )
```

**Loader test (`tests/test_rules/test_loader.py`) covers REF-08 + REF-09 minimally; the per-file schema check is in `tests/test_reference/test_schema.py`.**

### Pattern 3: Predicate File Template

Every `lib/rules/*.py` follows this header shape so the citation-coverage test can introspect:

```python
# lib/rules/conventional_pmi.py
"""Conventional PMI auto-termination and request-termination rules.

Citation: 12 USC §4901–4910 (Homeowners Protection Act of 1998) — sections 4902(a)
(borrower-requested cancellation at 80% LTV) and 4902(b) (automatic termination at
78% LTV based on amortization schedule).

Source URL: https://www.consumerfinance.gov/rules-policy/regulations/1026/  (CFPB
HPA examination procedures)  https://www.ecfr.gov/current/title-12/chapter-X
Effective: 1999-07-29 (HPA original effective date; no material amendment since)

What this predicate decides:
  Given a Loan, current scheduled balance, and original property value, return
  whether PMI auto-terminates (78% LTV trigger), is request-terminable (80% LTV
  trigger), or remains in force.

Inputs (Pydantic-typed via lib.rules.types.PMIInput):
    loan: Loan                       (Phase-1 Pydantic model)
    scheduled_balance: Money         (current scheduled balance per amort schedule)
    original_property_value: Money

Outputs (lib.rules.types.PMITerminationStatus):
    Literal["auto_terminated", "request_eligible", "in_force"]

Edge cases handled:
  - High-risk loans: HPA carve-out; see PMITerminationStatus.high_risk_midpoint case
  - Refi treatment: original_value resets at refi; caller's responsibility
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from lib.models import Loan, Money
from lib.money import quantize_cents

PMITerminationStatus = Literal["auto_terminated", "request_eligible", "in_force"]


def status(
    loan: Loan,
    scheduled_balance: Decimal,
    original_property_value: Decimal,
) -> PMITerminationStatus:
    """Return PMI termination status per HPA 12 USC §4902.

    Auto-termination (4902(b)): scheduled_balance / original_value <= 0.78
    Request-eligible (4902(a)): scheduled_balance / original_value <= 0.80
    """
    ltv = scheduled_balance / original_property_value
    if ltv <= Decimal("0.78"):
        return "auto_terminated"
    if ltv <= Decimal("0.80"):
        return "request_eligible"
    return "in_force"
```

**Required header anatomy** (introspected by `test_citation_coverage.py`):
1. Module docstring exists (non-empty)
2. Docstring contains the literal substring `Citation:` followed by a regulatory citation
3. Docstring contains the literal substring `Source URL:` followed by an http(s) URL
4. Docstring contains the literal substring `Effective:`
5. At least one fixture file exists at `tests/fixtures/rules/{module_stem}_*.json`

### Pattern 4: Per-Predicate Test with Hand-Calc Fixture

```python
# tests/test_rules/test_conventional_pmi.py
"""Tests for lib/rules/conventional_pmi.py — HPA 12 USC §4901-4910.

Every fixture pins values from the actual statute or worked example.
Exact Decimal equality. Hand-calc citation in fixture comment.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from lib.models import Loan
from lib.rules.conventional_pmi import status

FIX_DIR = Path(__file__).parent.parent / "fixtures" / "rules"


def _load(name: str) -> dict:
    return json.loads((FIX_DIR / name).read_text())


def test_auto_terminates_at_78_ltv() -> None:
    fx = _load("conventional_pmi_auto_terminate_78ltv.json")
    loan = Loan(
        principal=Decimal(fx["loan"]["principal"]),
        annual_rate=Decimal(fx["loan"]["annual_rate"]),
        term_months=fx["loan"]["term_months"],
    )
    result = status(
        loan=loan,
        scheduled_balance=Decimal(fx["scheduled_balance"]),
        original_property_value=Decimal(fx["original_property_value"]),
    )
    assert result == "auto_terminated"


def test_request_eligible_at_80_ltv() -> None:
    fx = _load("conventional_pmi_request_80ltv.json")
    # ...same shape...
```

Fixture file shape:
```json
{
  "citation": "12 USC §4902(b)",
  "source_url": "https://www.consumerfinance.gov/rules-policy/regulations/1026/",
  "comment": "Hand-calc: $200k orig value, $156k balance = 0.78 LTV exactly → auto_terminated",
  "loan": {"principal": "200000.00", "annual_rate": "0.065000", "term_months": 360},
  "scheduled_balance": "156000.00",
  "original_property_value": "200000.00",
  "expected_status": "auto_terminated"
}
```

### Pattern 5: Citation-Coverage Meta-Test

The single test that enforces RUL-12 + RUL-13 across all 11 predicate files:

```python
# tests/test_rules/test_citation_coverage.py
"""RUL-12 + RUL-13: every lib/rules/ predicate file has a regulatory-citation
docstring AND at least one fixture file under tests/fixtures/rules/ matching
its module stem.

This is a meta-test: failing it means a new predicate was added without its
citation header or its fixture. The fix is to add the missing artifact, never
to skip the test.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RULES_DIR = Path(__file__).parent.parent.parent / "lib" / "rules"
FIX_DIR = Path(__file__).parent.parent / "fixtures" / "rules"

# Files in lib/rules/ that are NOT regulatory predicates (loader, type aliases,
# package marker). Everything else is a predicate and must satisfy the contract.
NON_PREDICATE_FILES: frozenset[str] = frozenset({"__init__.py", "_loader.py", "types.py"})


def _predicate_modules() -> list[Path]:
    return sorted(p for p in RULES_DIR.glob("*.py") if p.name not in NON_PREDICATE_FILES)


@pytest.mark.parametrize("path", _predicate_modules(), ids=lambda p: p.stem)
def test_predicate_has_citation_in_docstring(path: Path) -> None:
    src = path.read_text()
    # Module docstring is the first triple-quoted block.
    m = re.search(r'^"""(.*?)"""', src, flags=re.DOTALL)
    assert m is not None, f"{path.name} missing module docstring (RUL-12)"
    docstring = m.group(1)
    assert "Citation:" in docstring, f"{path.name} docstring missing 'Citation:' (RUL-12)"
    assert "Source URL:" in docstring, f"{path.name} docstring missing 'Source URL:' (RUL-12)"
    assert "Effective:" in docstring, f"{path.name} docstring missing 'Effective:' (RUL-12)"
    assert re.search(r"https?://", docstring), (
        f"{path.name} docstring 'Source URL:' must contain an http(s) URL (RUL-12)"
    )


@pytest.mark.parametrize("path", _predicate_modules(), ids=lambda p: p.stem)
def test_predicate_has_at_least_one_fixture(path: Path) -> None:
    matches = list(FIX_DIR.glob(f"{path.stem}_*.json"))
    assert len(matches) >= 1, (
        f"{path.name} has no matching fixture under {FIX_DIR}/{path.stem}_*.json (RUL-13)"
    )
```

This single test parametrizes over all predicate files; adding a new predicate without artifacts produces 1-2 immediately failing test cases named after the missing module.

### Anti-Patterns to Avoid

- **Big-rules-engine** — no `lib/rules/qualification.py` with all 11 functions. The whole point of HMDA Platform pattern is one citation per file.
- **Silent baseline fallback for missing county** — `loan_type.classify(amount, county=None)` must raise `MissingCountyDataError`, never default to baseline conforming. Adopt cfpb/jumbo-mortgage's "needCounty" sentinel as a Python exception.
- **Float in fee/MIP/funding-fee tables** — every numeric value in `data/reference/*.yml` is a quoted string parsed by `Decimal(str)`. PyYAML's default `safe_load` will deserialize unquoted `0.0085` as `float`, which silently violates money discipline.
- **Importing one predicate from another** — predicates are independent. If two predicates need a shared helper (e.g., LTV computation), the helper goes in `lib/rules/types.py` or `lib/affordability.py` (Phase 4); predicates do not depend on predicates.
- **`pytest.approx` for any predicate output** — predicates return Decimal; use exact equality. `assertAlmostEqual` is forbidden by CLAUDE.md.
- **Hardcoding 2026 numbers in Python** — every regulatory parameter goes in YAML. The predicate file may name a tier ("high-cost county", "loan amount tier 1") but the *number* lives in YAML.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom regex parser | `yaml.safe_load` | Standard, safe, no eval |
| Date arithmetic for staleness | `(today - effective).days > 365` | `dateutil.relativedelta(months=12)` | Handles leap years and month-boundary edges; consistent with Phase 3+ amortization scheduling |
| Loud warnings | print to stderr | `warnings.warn(..., category=StaleReferenceWarning, stacklevel=2)` | Test-capturable via `pytest.warns`/`recwarn`; respects `-W` filter; conventional for libraries |
| Cache invalidation | Module-level dict | `functools.lru_cache(maxsize=None)` | Standard; introspectable; `cache_clear()` available for tests that need to re-read YAML |
| Loan-type classification | Big if/else cascade | Look up county in `conforming-limits-2026.yml` `high_cost_counties` list; default to baseline; classify by tier | The complexity is in the data table, not the algorithm — see cfpb/jumbo-mortgage which is ~50 lines of JS over a much bigger lookup table |
| LLPA matrix | Nested if/else | YAML 2D table indexed by `[ltv_bucket][credit_score_bucket]` | Fannie publishes the table verbatim; the predicate is a 2D lookup, not logic |
| FHA MIP table | Hand-coded constants | YAML table with rows `{term_months, ltv_bucket, loan_amount_tier} → {ufmip, annual_mip_bps, terminates_at_months}` | HUD ML 2023-05 publishes one table; the predicate is a lookup by tier |
| Reg Z tolerance check | Recomputing 1/8 vs 1/4 inline | YAML constants (`tolerance_regular_pct`, `tolerance_irregular_pct`) + a small predicate that picks based on transaction type | The values rarely change, but isolating them in YAML means a future amendment is a YAML edit |

**Key insight:** In a regulatory rules library, **the data is the algorithm**. Almost every predicate is a 1-D, 2-D, or 3-D lookup against a table the regulator publishes verbatim. Custom branching logic should be limited to the few cases where the regulator's *prose* requires it (origination-date grandfathering for FHA MIP; HPA high-risk carve-out for PMI; QM small-creditor exceptions for ATR/QM). Everything else is `dict[tuple[bucket_key], value]`.

## Per-Rule Design Notes

### REF-01 — `data/reference/conforming-limits-2026.yml` (FHFA)

**Source URL [VERIFIED]:** https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026
**Effective:** 2026-01-01
**Numeric anchors [VERIFIED via FHFA news release]:**
- Baseline 1-unit: $832,750
- Ceiling 1-unit (high-cost): $1,249,125 (= 150% × baseline)
- 2-unit baseline: $1,066,250 / 3-unit: $1,289,100 / 4-unit: $1,601,650
- 2-unit ceiling: $1,599,375 / 3-unit: $1,933,200 / 4-unit: $2,402,625
- High-cost county count: ~232 counties; FHFA publishes XLSX with per-county limits

**YAML structure:** see Pattern 1 above. Plan must extract the per-county XLSX (or the subset of counties where the limit ≠ baseline) into the `high_cost_counties` list. A practical scope-limiter: ship the 50-100 highest-volume high-cost counties; document this in the YAML `notes:` field; `loan_type.classify()` raises `MissingCountyDataError` for unlisted counties so users know to extend the table.

### REF-02 — `data/reference/fha-limits-2026.yml` (HUD/FHA)

**Source URL [VERIFIED]:** https://www.hud.gov/news/hud-no-25-145 (announcement) and https://www.hud.gov/sites/dfiles/hudclips/documents/2025-23hsgml.pdf (Mortgagee Letter 2025-23)
**Effective:** 2026-01-01 (FHA case numbers assigned on or after)
**Numeric anchors [VERIFIED via HUD ML 2025-23]:**
- Floor 1-unit: $541,287 (= 65% × FHFA baseline of $832,750)
- Ceiling 1-unit: $1,249,125 (= same as conforming ceiling)
- 2-unit floor/ceiling: $693,050 / $1,599,375
- 3-unit floor/ceiling: $837,700 / $1,933,200
- 4-unit floor/ceiling: $1,041,125 / $2,402,625

**Pitfall:** FHA limits are computed per MSA, not per county; the HUD announcement publishes per-county tables but the underlying methodology is MSA-driven. YAML can use county-keying for symmetry with REF-01.

### REF-03 — `data/reference/fha-mip-rates.yml` (HUD ML 2023-05)

**Source URL [VERIFIED]:** https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf
**Effective:** 2023-03-20 (mortgages endorsed on or after) — **note this is older than 12 months as of 2026-04-26, so the staleness warning will fire**. This is the correct behavior — the YAML is current (HUD has not republished); the warning prompts a manual check.

**The 30bps reduction announced in 2023-05** changed the post-2013 annual MIP table. The current rates (post-2023-03-20) are roughly:
- Term > 15 years, LTV > 95%: 0.55% annual (previously 0.85%) [CITED: HUD ML 2023-05 §III]
- Term > 15 years, LTV ≤ 95%, > 90%: 0.50% annual
- Term > 15 years, LTV ≤ 90%: 0.50% annual
- Term ≤ 15 years, LTV > 90%: 0.40%
- Term ≤ 15 years, LTV ≤ 90%: 0.15%
- UFMIP: 1.75% across all forward mortgages

**Termination rule (HUD ML 2013-04, unchanged by 2023-05):**
- Loans with LTV > 90% at origination: MIP for life of loan
- Loans with LTV ≤ 90% at origination: MIP terminates at 11 years

**YAML structure:**
```yaml
source: "https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf"
effective: 2023-03-20
notes: "Annual MIP reduced 30bps per HUD ML 2023-05 §III. Termination rules per HUD ML 2013-04 unchanged."
ufmip_rate: "0.0175"
annual_mip_table:
  # term_months, ltv_lower_exclusive, ltv_upper_inclusive, loan_amount_tier, annual_mip_rate
  - {term_months: 360, ltv_min: "0.95", ltv_max: "1.00", loan_amount_max: "726200", annual_mip_rate: "0.0055"}
  - {term_months: 360, ltv_min: "0.90", ltv_max: "0.95", loan_amount_max: "726200", annual_mip_rate: "0.0050"}
  - {term_months: 360, ltv_min: "0.00", ltv_max: "0.90", loan_amount_max: "726200", annual_mip_rate: "0.0050"}
  - {term_months: 180, ltv_min: "0.90", ltv_max: "1.00", loan_amount_max: "726200", annual_mip_rate: "0.0040"}
  - {term_months: 180, ltv_min: "0.00", ltv_max: "0.90", loan_amount_max: "726200", annual_mip_rate: "0.0015"}
  # ...high-balance tier (loan_amount > 726200) has higher rates per HUD ML 2023-05 Table B
termination:
  ltv_above_90_pct: "life_of_loan"
  ltv_at_or_below_90_pct: 132   # 11 years × 12 months
```

### REF-04 — `data/reference/va-funding-fees.yml` (VA Lender Handbook M26-7)

**Source URL [VERIFIED]:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf
**Effective:** 2023-04-07 (VA last republished funding-fee table; same caveat as REF-03 — staleness warning will fire, that's correct)

**Numeric anchors [VERIFIED via VA M26-7 + corroborating sources]:**

| Loan Type | Down Payment | First Use | Subsequent Use |
|-----------|-------------|-----------|----------------|
| Purchase | 0% | 2.15% | 3.30% |
| Purchase | 5% to <10% | 1.50% | 1.50% |
| Purchase | ≥10% | 1.25% | 1.25% |
| Cash-out refi | n/a | 2.15% | 3.30% |
| IRRRL (streamline) | n/a | 0.50% | 0.50% |
| Manufactured home (not on permanent foundation) | n/a | 1.00% | 1.00% |
| Loan assumption | n/a | 0.50% | 0.50% |

**Exemption flag:** Veterans receiving VA disability compensation (any rating) are exempt; predicate must accept `is_exempt: bool`.

### REF-05 — `data/reference/va-residual-income.yml` (VA M26-7 Topic 7)

**Source URL [CITED]:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/ (M26-7 lender handbook, residual income section)
**Effective:** 2023-04-07 (or whenever VA last republished — verify)

**Structure:** 3D lookup `[region][family_size][loan_amount_band] → minimum_residual_income_dollars`
- Regions: `northeast`, `midwest`, `south`, `west` (VA's four regions)
- Family sizes: 1, 2, 3, 4, 5+ (with per-additional-member increment)
- Loan amount bands: `< 80000` and `>= 80000`
- Cell value example [VERIFIED]: Midwest, family of 4, loan ≥ $80,000 → $1,003

**YAML structure:**
```yaml
source: "https://benefits.va.gov/WARMS/docs/admin26/m26-07/"
effective: 2023-04-07
notes: "VA Lender Handbook M26-7. Per-region tables for loans ≥ $80k vs < $80k. Add $80 per family member above 5."
regions: [northeast, midwest, south, west]
loan_band_threshold: "80000"
table_above_80k:
  northeast:
    1: "450"
    2: "755"
    3: "909"
    4: "1025"
    5: "1062"
  midwest:
    1: "441"
    2: "738"
    3: "889"
    4: "1003"
    5: "1039"
  # ...south, west
table_below_80k:
  # ...similar shape with smaller dollar minimums
per_extra_member_increment: "80"
```

(Cell values above are illustrative; planner must extract from M26-7.)

### REF-06 — `data/reference/usda-income-limits.yml` (USDA RD GLP)

**Source URL [VERIFIED]:** https://www.rd.usda.gov/files/rd-grhlimitmap.pdf and https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do
**Effective:** check USDA RD's last update date (often Q3-Q4 each year)
**Anchor values [CITED]:** Default (most areas) 1-4 person household: ~$119,850; 5-8 person: ~$158,250 (varies by county)

**Structure:** county-keyed `[state_fips][county_fips] → {1_4_person_limit, 5_8_person_limit}` plus default.
**Guarantee fee:** USDA SFH GLP charges a 1.0% upfront guarantee fee + 0.35% annual fee on the average outstanding balance. These belong in REF-06 too:
```yaml
source: "https://www.rd.usda.gov/files/rd-grhlimitmap.pdf"
effective: 2025-10-01  # USDA fiscal year start
guarantee_fee:
  upfront_pct: "0.0100"
  annual_pct: "0.0035"
income_limits:
  default:
    persons_1_to_4: "119850"
    persons_5_to_8: "158250"
  by_county:
    # state_fips, county_fips → overrides
    - {state_fips: "06", county_fips: "075", persons_1_to_4: "211800", persons_5_to_8: "279600"}
```

### REF-07 — `data/reference/irs-pub936.yml` (IRS Publication 936)

**Source URL [VERIFIED]:** https://www.irs.gov/pub/irs-pdf/p936.pdf and https://www.irs.gov/publications/p936
**Effective:** Annually (Pub 936 is republished each tax year; 2025 edition out)

**Anchor values [VERIFIED]:**
- Post-2017 acquisition debt cap: $750,000 (single or MFJ); $375,000 MFS
- Pre-2017 grandfathered cap: $1,000,000 (single/MFJ); $500,000 MFS
- Grandfather cutoff date: 2017-12-15 (acquisition debt incurred on or before; binding contract before 2017-12-15 + close before 2018-04-01 also qualifies)
- Points deductibility: prepaid interest deductible in year of purchase if (a) loan secured by primary residence, (b) points paid as fee, (c) computed as % of loan, (d) settlement statement shows points

**YAML structure:**
```yaml
source: "https://www.irs.gov/pub/irs-pdf/p936.pdf"
effective: 2025-01-01  # current Pub 936 edition for tax year 2025
notes: "IRS Pub 936 — Home Mortgage Interest Deduction. TCJA $750k cap effective for debt incurred after 2017-12-15."
caps:
  post_2017:
    single_or_mfj: "750000"
    mfs: "375000"
    effective_for_debt_after: 2017-12-15
  pre_2017_grandfathered:
    single_or_mfj: "1000000"
    mfs: "500000"
    effective_for_debt_on_or_before: 2017-12-15
    binding_contract_grace_period:
      contract_signed_before: 2017-12-15
      close_before: 2018-04-01
points_deductibility:
  must_be_secured_by_primary_residence: true
  must_be_computed_as_pct_of_loan: true
  must_be_on_settlement_statement: true
```

### RUL-01 — `lib/rules/loan_type.py` (Loan-type classification)

**Citation:** FHFA conforming loan limits per 12 USC §1717 + HUD FHA limits per NHA §203(b)(2); per-county overrides per FHFA & HUD annual publications.
**Source URL:** combined REF-01 + REF-02 sources.
**Effective:** 2026-01-01.
**Inputs:** `loan_amount: Decimal`, `county: County` (Pydantic model with `state_fips: str`, `county_fips: str`, `name: str`), `program: Literal["conventional", "fha", "va", "usda"]`, `unit_count: int = 1`.
**Output:** `LoanType` enum: `"conforming"`, `"high_balance"`, `"jumbo"`, `"fha_standard"`, `"fha_high_balance"`, `"va_standard"`, `"va_high_balance"`, `"usda"`.
**Logic:**
1. Look up county-specific limit from REF-01 (or REF-02 for FHA).
2. If `program == "conventional"`: if `loan_amount <= baseline` → `conforming`; if `<= county_limit` (when county is high-cost) → `high_balance`; else → `jumbo`.
3. FHA: if `<= floor` → `fha_standard`; if `<= ceiling` and county allows → `fha_high_balance`; else → out of FHA program (raise).
4. VA: same shape as conventional (since VA uses the FHFA limit for full-entitlement vets).
5. USDA: no loan-amount classification; this predicate just returns `usda` flag if program selected.

**Edge case (cfpb/jumbo-mortgage pattern):** if `county is None` AND `loan_amount > baseline`, raise `MissingCountyDataError` (loud) — never silently default to baseline. The classifier may still answer correctly when `loan_amount ≤ baseline` because every county gets at least the baseline; surface this as a "fast path" if desired but the safer default is to require county for every call.

**Pitfall — RESEARCH.md/PITFALLS.md Pitfall 7:** $830k loan in low-cost county is jumbo even though $830k < $832,750 baseline (because that county's limit IS the baseline). Test fixtures must cover: high-cost county at ceiling, low-cost county at baseline, FHA floor, FHA ceiling, missing-county-error.

### RUL-02 — `lib/rules/fannie_eligibility.py` (LLPA matrix)

**Citation:** Fannie Mae LLPA Matrix, Single-Family Selling Guide §B5-1.
**Source URL [VERIFIED]:** https://singlefamily.fanniemae.com/media/9391/display (current matrix PDF)
**Effective [VERIFIED]:** 2026-01-28 (latest matrix revision)
**Inputs:** `credit_score: int`, `ltv_pct: Decimal`, `loan_purpose: Literal["purchase", "rate_term_refi", "cash_out_refi"]`, `occupancy: Literal["primary", "second_home", "investment"]`, `unit_count: int`, `term_months: int`.
**Output:** `Decimal` LLPA in **basis points** (negative = credit, positive = charge).
**Logic:** 2D lookup against the matrix `[credit_score_bucket][ltv_bucket]` plus add-on adjustments per `loan_purpose`/`occupancy`/`unit_count` per Selling Guide §B5-1.
**Pitfall:** the matrix has **buckets** (e.g., 740–759, 720–739) not continuous; `_bucket_for_credit_score(score: int) -> str` is a private helper that translates 750 → "740-759". Off-by-one at bucket boundaries is the most common bug. Test at every boundary (700, 719, 720, 739, 740).

**Reference YAML:** consider a separate `data/reference/fannie-llpa-matrix.yml` (which arguably should have been REF-08 in the requirements list but was not enumerated). For Phase 2, embed the matrix in `lib/rules/fannie_eligibility.py` as a YAML loaded from `data/reference/fannie-llpa-matrix.yml` (planner: this is an acceptable extension since RUL-02 explicitly says "implements LLPA matrix lookup" — the matrix IS reference data and fits the discipline).

### RUL-03 — `lib/rules/freddie_eligibility.py` (Freddie LPA-equivalent checks)

**Citation:** Freddie Mac Single-Family Seller/Servicer Guide §4203.4 + LPA-published Eligibility Matrix.
**Source URL:** https://guide.freddiemac.com/app/guide/section/4203.4 + https://sf.freddiemac.com/working-with-us/origination-underwriting/eligibility-criteria
**Effective:** check current quarter
**Inputs:** same as Fannie; output is **eligibility booleans + credit-fee-bps** (Freddie's structure is similar but not identical to Fannie's LLPA matrix; use Freddie's published Credit Fee Cap matrix).
**Notes:** for personal-use, Freddie and Fannie often produce identical eligibility outcomes; the predicate exists separately for citation discipline. If Freddie's published matrix is materially the same, the YAML can mirror Fannie's with a different `source:` field.

### RUL-04 — `lib/rules/fha_mip.py` (FHA MIP)

**Citation:** HUD ML 2023-05 (annual MIP rates) + HUD ML 2013-04 (termination rules).
**Source URL [VERIFIED]:** https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf
**Effective:** 2023-03-20 (post-2013 endorsements); pre-2013 endorsements use older rules (deferred — flag as out-of-scope-for-v1 with a comment in the predicate).
**Inputs:** `loan: Loan`, `original_property_value: Decimal`, `endorsement_date: date`.
**Outputs:** dataclass-or-dict `{ufmip: Decimal, annual_mip_pct: Decimal, terminates_at_period: int | Literal["life_of_loan"]}`.
**Logic:**
1. Compute LTV at origination = principal / property_value.
2. UFMIP = principal × `ufmip_rate` (1.75% per REF-03).
3. Look up annual MIP from REF-03 table by (term_months, ltv_bucket, loan_amount_tier).
4. Termination: `life_of_loan` if origination LTV > 90%; else month 132 (= 11yrs × 12).
5. Origination-date grandfathering: if `endorsement_date < 2023-03-20`, predicate raises `NotImplementedError("pre-2023-03-20 MIP rates deferred — see REF-03 notes")`.

**Pitfall — RESEARCH.md/PITFALLS.md Pitfall 6:** FHA ≠ conventional PMI. Don't conflate. Test fixtures for both LTV>90% and LTV≤90% scenarios are required (citation-coverage test only checks ≥1; planner should add both for robustness).

### RUL-05 — `lib/rules/conventional_pmi.py` (HPA termination)

**Citation:** 12 USC §4901-4910 (Homeowners Protection Act of 1998), specifically §4902(a) (request) and §4902(b) (auto).
**Source URL [VERIFIED]:** https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/ + https://www.fdic.gov/consumer-compliance-examination-manual/v-5-homeowners-protection-act
**Effective:** 1999-07-29
**Inputs:** `loan: Loan`, `scheduled_balance: Decimal`, `original_property_value: Decimal`, `is_high_risk: bool = False`.
**Output:** `Literal["auto_terminated", "request_eligible", "in_force", "high_risk_midpoint_terminated"]`.
**Logic:**
- Standard loans: LTV ≤ 0.78 → auto; LTV ≤ 0.80 → request; else in_force.
- High-risk loans (HPA §4902(g) carve-out): PMI terminates no later than midpoint of amortization period; the 78%/80% triggers do NOT apply.
**Pitfall:** the LTV here is `scheduled_balance / ORIGINAL property value`, NOT current value. PMI cancellation tied to original value is the HPA-mandated default; some lenders allow re-appraisal-based cancellation but that's outside the statute and not in scope for v1.

### RUL-06 — `lib/rules/va_funding_fee.py` (VA Funding Fee)

**Citation:** 38 USC §3729 + VA Lender Handbook M26-7 Chapter 8.
**Source URL [VERIFIED]:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf
**Effective:** 2023-04-07
**Inputs:** `loan_amount: Decimal`, `down_payment_pct: Decimal`, `is_first_use: bool`, `loan_purpose: Literal["purchase", "cash_out_refi", "irrrl", "assumption"]`, `is_exempt_from_funding_fee: bool` (disability comp recipients).
**Output:** `Decimal` funding fee dollar amount (after `quantize_cents`).
**Logic:** if `is_exempt`: return `Decimal("0.00")`; else look up `fee_pct` from REF-04 table by `(loan_purpose, is_first_use, down_payment_band)`; return `quantize_cents(loan_amount * fee_pct)`.

### RUL-07 — `lib/rules/va_residual_income.py` (VA Residual Income)

**Citation:** VA Lender Handbook M26-7, residual income tables.
**Source URL:** https://benefits.va.gov/WARMS/docs/admin26/m26-07/
**Effective:** 2023-04-07
**Inputs:** `region: Literal["northeast", "midwest", "south", "west"]`, `family_size: int`, `loan_amount: Decimal`, `actual_residual_income: Decimal`.
**Output:** `Literal["pass", "fail"]` plus a structured object with `minimum_required: Decimal` and (if fail) the `binding_rule_citation: str` for AFFD-07's "blocked_by" field.
**Logic:** Pick `table_above_80k` or `table_below_80k` based on loan amount; pick row by region+family_size; if family_size > 5, add `(family_size - 5) * per_extra_member_increment`; compare actual to required.
**Hand-off note for Phase 4:** When AFFD-07 says "binding rule citation" (e.g., `"VA-RESIDUAL-WEST-FAMILY-4"`), this predicate's output object should populate that string in a stable format like `f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"`.

### RUL-08 — `lib/rules/usda.py` (USDA SFH GLP)

**Citation:** USDA Rural Development Single Family Housing Guaranteed Loan Program — 7 CFR Part 3555.
**Source URL [VERIFIED]:** https://www.rd.usda.gov/files/rd-grhlimitmap.pdf + 7 CFR §3555
**Effective:** USDA FY start (2025-10-01 typically)
**Inputs:** `household_income: Decimal`, `household_size: int`, `county: County`, `loan_amount: Decimal` (for guarantee fee).
**Outputs:** `{income_eligible: bool, upfront_guarantee_fee: Decimal, annual_guarantee_fee: Decimal}`.
**Logic:** Look up county income limit from REF-06 (default if county not listed); compute `income_eligible = household_income <= limit_for_household_size`; compute fees using REF-06 percentages.

### RUL-09 — `lib/rules/atr_qm.py` (General QM Price-Based Test)

**Citation:** 12 CFR §1026.43(e)(2) — General QM, as amended by Mar 2021 final rule (replaces 43% DTI cap).
**Source URL [VERIFIED]:** https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition
**Effective:** 2022-10-01 (mandatory compliance date after CFPB extension)
**Inputs:** `apr: Decimal`, `apor: Decimal`, `loan_amount: Decimal`, `lien_position: Literal["first", "subordinate"]`.
**Output:** `bool` (True = passes QM price test).
**Logic [VERIFIED — thresholds from CFPB 2021 final rule]:**

| Lien | Loan Amount Band | APR-APOR Threshold |
|------|-----------------|--------------------|
| First | ≥ $110,260 (indexed for inflation) | 2.25 pp |
| First | $66,156 ≤ x < $110,260 | 3.5 pp |
| First | < $66,156 | 6.5 pp |
| Subordinate | ≥ $66,156 | 3.5 pp |
| Subordinate | < $66,156 | 6.5 pp |

(Loan-amount thresholds are indexed annually; CFPB publishes the updated numbers — REF-08 staleness check will catch.)
**Output predicate:** True if `(apr - apor) ≤ threshold`.
**Note:** Safe Harbor QM uses tighter 1.5 pp threshold (3.5 pp for subordinate); planner can model both `general_qm_passes()` and `safe_harbor_qm_passes()` from the same threshold table.

### RUL-10 — `lib/rules/reg_z.py` (Reg Z APR tolerances)

**Citation:** 12 CFR §1026.22 — Determination of annual percentage rate; tolerance §1026.22(a)(2).
**Source URL [VERIFIED]:** https://www.consumerfinance.gov/rules-policy/regulations/1026/22/ + https://www.ecfr.gov/current/title-12/chapter-X/part-1026/subpart-C/section-1026.22
**Effective:** current Reg Z (last amended 2025; ATR/QM thresholds updated annually; tolerance text unchanged for years)
**Inputs:** `disclosed_apr: Decimal`, `actual_apr: Decimal`, `is_irregular_transaction: bool`.
**Output:** `bool` (True = within tolerance).
**Logic:** tolerance = `Decimal("0.00125")` (1/8 pp) if regular; `Decimal("0.0025")` (1/4 pp) if irregular. Return `abs(disclosed_apr - actual_apr) <= tolerance`.
**Definition of irregular transaction (§1026.22(a)(3)):** any of multiple advances, irregular payment periods, or irregular payment amounts (other than an irregular first period or first/final payment).
**For Phase 7's APR work:** this predicate is the gate that says "our estimated APR is within tolerance of the lender's disclosed APR" — Phase 7's "estimated" label still applies because we don't make commercial disclosures.

### RUL-11 — `lib/rules/irs_pub936.py` (Mortgage interest deduction qualified loan limit)

**Citation:** IRC §163(h)(3) (mortgage interest deduction) as amended by TCJA 2017; computational worksheet in IRS Publication 936 Table 1.
**Source URL [VERIFIED]:** https://www.irs.gov/pub/irs-pdf/p936.pdf
**Effective:** 2025-01-01 for current Pub 936 edition (republished annually).
**Inputs:** `total_acquisition_debt: Decimal`, `debt_origination_dates: list[date]`, `filing_status: Literal["single", "mfj", "mfs", "hoh"]`.
**Output:** `{qualified_loan_limit: Decimal, fully_deductible: bool, partial_pct: Decimal | None}`.
**Logic (simplified Pub 936 Table 1 worksheet):**
1. Sum debt with origination ≤ 2017-12-15 → grandfathered bucket.
2. Sum debt with origination > 2017-12-15 → post-2017 bucket.
3. Apply per-bucket caps from REF-07 (1M / 750k / MFS halves).
4. Return fully deductible if total ≤ applicable cap; else compute partial deductibility ratio.
**Edge case:** binding-contract grace period (signed before 2017-12-15, closed before 2018-04-01) gets pre-2017 cap — encode as a per-debt flag.
**Out of scope:** points deductibility computation (Pub 936 §3); deductibility hinges on facts the predicate doesn't have. RUL-11 returns the loan-limit ratio only.

## Test Discipline

### REF-09 — Schema test (`tests/test_reference/test_schema.py`)

Tiny meta-test that loads every YAML in `data/reference/` and asserts `source` (str + URL pattern) and `effective` (date) are present:

```python
import re
import yaml
from datetime import date
from pathlib import Path
import pytest

REF_DIR = Path(__file__).parent.parent.parent / "data" / "reference"

def _ref_files() -> list[Path]:
    return sorted(p for p in REF_DIR.glob("*.yml"))

@pytest.mark.parametrize("path", _ref_files(), ids=lambda p: p.stem)
def test_reference_yaml_has_source_and_effective(path: Path) -> None:
    raw = yaml.safe_load(path.read_text())
    assert isinstance(raw, dict), f"{path.name} must parse to a dict"
    assert "source" in raw, f"{path.name} missing `source:`"
    assert "effective" in raw, f"{path.name} missing `effective:`"
    assert re.match(r"^https?://", raw["source"]), f"{path.name} source must be a URL"
    assert isinstance(raw["effective"], date), f"{path.name} effective must be a date (PyYAML auto-parses YYYY-MM-DD)"
```

### REF-08 — Staleness warning test (`tests/test_rules/test_loader.py`)

```python
import warnings
from datetime import date, timedelta
import pytest
from lib.rules._loader import load_reference, StaleReferenceWarning

def test_staleness_warning_fires_for_old_yaml(tmp_path, monkeypatch) -> None:
    """Write a synthetic YAML with effective: 2 years ago; assert warning fires."""
    old = (date.today() - timedelta(days=730)).isoformat()
    fake = tmp_path / "synthetic-old.yml"
    fake.write_text(f"source: 'https://example.test/'\neffective: {old}\nbody: stub\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    with pytest.warns(StaleReferenceWarning, match="more than 12 months old"):
        load_reference("synthetic-old")

def test_no_warning_for_fresh_yaml(tmp_path, monkeypatch) -> None:
    fresh = (date.today() - timedelta(days=30)).isoformat()
    fake = tmp_path / "synthetic-fresh.yml"
    fake.write_text(f"source: 'https://example.test/'\neffective: {fresh}\nbody: stub\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    with warnings.catch_warnings():
        warnings.simplefilter("error", StaleReferenceWarning)
        load_reference("synthetic-fresh")  # raises if any warning fires
```

### RUL-12 + RUL-13 — Citation-coverage test

See Pattern 5 above. The single test parametrizes over `lib/rules/*.py` (excluding `__init__.py`, `_loader.py`, `types.py`) and asserts each has the citation header and ≥1 fixture.

### Per-predicate test discipline (consumed by Phase 4+ verification too)

Every `tests/test_rules/test_{predicate}.py` follows:

1. Module docstring lists the citation under test (mirrors the predicate's docstring header).
2. One test function per regulatory edge case identified in the per-rule design notes above.
3. All fixtures loaded from `tests/fixtures/rules/{predicate}_*.json`.
4. Every fixture has `citation`, `source_url`, and `comment` (hand-calc derivation) fields.
5. Exact Decimal equality. No `pytest.approx`. No `assertAlmostEqual`.
6. Fixtures pin the regulator's published values (e.g., HUD ML 2023-05 Table A row "Term > 15yr, LTV > 95%, ≤ $726,200" → `0.0055`).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x (already configured in pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (Phase 1; no changes) |
| Quick run command | `uv run pytest tests/ -x --tb=short` |
| Full suite command | `uv run pytest && uv run mypy --strict . && uv run ruff check . && uv run ruff format --check .` |
| Estimated runtime | ~5-10 seconds (pure Python predicates over small YAML; no network, no DB) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REF-01 | conforming-limits-2026.yml exists, parseable, has expected baseline=$832,750 | schema + fixture | `uv run pytest tests/test_reference/test_schema.py::test_reference_yaml_has_source_and_effective[conforming-limits-2026] -x` | ❌ Wave 0 |
| REF-02 | fha-limits-2026.yml exists, parseable, floor=$541,287 | schema | same parametrized test | ❌ Wave 0 |
| REF-03 | fha-mip-rates.yml has UFMIP=0.0175, ≥1 annual MIP row | schema + RUL-04 round-trip | `uv run pytest tests/test_rules/test_fha_mip.py -x` | ❌ Wave 0 |
| REF-04 | va-funding-fees.yml has IRRRL=0.005, first-use-purchase-zero-down=0.0215 | schema + RUL-06 round-trip | `uv run pytest tests/test_rules/test_va_funding_fee.py -x` | ❌ Wave 0 |
| REF-05 | va-residual-income.yml has all 4 regions × ≥5 family sizes × 2 loan bands | schema + RUL-07 | `uv run pytest tests/test_rules/test_va_residual_income.py -x` | ❌ Wave 0 |
| REF-06 | usda-income-limits.yml has default 1-4 limit + ≥1 county override + guarantee fees | schema + RUL-08 | `uv run pytest tests/test_rules/test_usda.py -x` | ❌ Wave 0 |
| REF-07 | irs-pub936.yml has $750k post-2017 + $1M pre-2017 caps + grace period | schema + RUL-11 | `uv run pytest tests/test_rules/test_irs_pub936.py -x` | ❌ Wave 0 |
| REF-08 | Staleness warning fires when effective > 12 months old | unit (warns capture) | `uv run pytest tests/test_rules/test_loader.py::test_staleness_warning_fires_for_old_yaml -x` | ❌ Wave 0 |
| REF-09 | Every reference YAML has source URL + effective date | meta (parametrized over filesystem) | `uv run pytest tests/test_reference/test_schema.py -x` | ❌ Wave 0 |
| RUL-01 | loan_type.classify returns correct enum for high-cost ceiling, low-cost baseline, FHA floor, FHA ceiling; raises MissingCountyDataError when county None | unit + 5 fixtures | `uv run pytest tests/test_rules/test_loan_type.py -x` | ❌ Wave 0 |
| RUL-02 | fannie LLPA lookup at credit-score and LTV bucket boundaries (700/719/720/739/740) | unit + ≥5 boundary fixtures | `uv run pytest tests/test_rules/test_fannie_eligibility.py -x` | ❌ Wave 0 |
| RUL-03 | freddie eligibility lookup matches Fannie on common cases; differs on Freddie-specific overlay | unit + ≥3 fixtures | `uv run pytest tests/test_rules/test_freddie_eligibility.py -x` | ❌ Wave 0 |
| RUL-04 | fha_mip.compute correct UFMIP + annual MIP for LTV>90 (life of loan) and LTV≤90 (132-month termination); raises NotImplementedError for endorsement_date<2023-03-20 | unit + ≥3 fixtures | `uv run pytest tests/test_rules/test_fha_mip.py -x` | ❌ Wave 0 |
| RUL-05 | conventional_pmi.status returns "auto_terminated" at exactly 0.78 LTV, "request_eligible" at exactly 0.80 LTV, "in_force" above; high_risk variant returns midpoint termination | unit + ≥4 fixtures | `uv run pytest tests/test_rules/test_conventional_pmi.py -x` | ❌ Wave 0 |
| RUL-06 | va_funding_fee.compute returns 0 when exempt; correct % across (purchase/refi, first/subsequent, down-payment bands); IRRRL = 0.005 | unit + ≥6 fixtures | `uv run pytest tests/test_rules/test_va_funding_fee.py -x` | ❌ Wave 0 |
| RUL-07 | va_residual_income.evaluate returns "pass"/"fail" + binding_rule_citation string | unit + ≥4 fixtures (one per region × pass/fail) | `uv run pytest tests/test_rules/test_va_residual_income.py -x` | ❌ Wave 0 |
| RUL-08 | usda.evaluate income-eligible vs not, correct guarantee fees | unit + ≥3 fixtures | `uv run pytest tests/test_rules/test_usda.py -x` | ❌ Wave 0 |
| RUL-09 | atr_qm.general_qm_passes returns True/False at price-based-test thresholds across all loan-amount tiers | unit + ≥6 fixtures (one per (lien × loan-amount-band) cell, plus boundary cases) | `uv run pytest tests/test_rules/test_atr_qm.py -x` | ❌ Wave 0 |
| RUL-10 | reg_z.within_apr_tolerance returns True for ±1/8pp regular and ±1/4pp irregular; False for excess | unit + ≥4 fixtures | `uv run pytest tests/test_rules/test_reg_z.py -x` | ❌ Wave 0 |
| RUL-11 | irs_pub936.qualified_loan_limit returns $750k for post-2017 single, $1M for grandfathered, half for MFS, grace-period flag handling | unit + ≥4 fixtures | `uv run pytest tests/test_rules/test_irs_pub936.py -x` | ❌ Wave 0 |
| RUL-12 | Every lib/rules/*.py predicate has docstring with Citation:/Source URL:/Effective: | meta (parametrized over filesystem) | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring -x` | ❌ Wave 0 |
| RUL-13 | Every lib/rules/*.py predicate has ≥1 fixture file under tests/fixtures/rules/{stem}_*.json | meta (parametrized over filesystem) | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_at_least_one_fixture -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x --tb=short` (full suite — fast, no need to subset)
- **Per wave merge:** `uv run pytest && uv run mypy --strict . && uv run ruff check . && uv run ruff format --check .`
- **Phase gate:** Full suite green before `/gsd-verify-work`; mypy --strict --warn-unused-ignores green; pre-commit hook green on `data/reference/*.yml` lint

### Wave 0 Gaps

- [ ] `tests/test_reference/__init__.py` — empty marker
- [ ] `tests/test_rules/__init__.py` — empty marker
- [ ] `tests/fixtures/rules/__init__.py` — empty marker
- [ ] `tests/test_reference/test_schema.py` — REF-09 parametrized loader
- [ ] `tests/test_rules/test_citation_coverage.py` — RUL-12 + RUL-13 meta-test
- [ ] `tests/test_rules/test_loader.py` — REF-08 staleness via `pytest.warns`
- [ ] `lib/rules/__init__.py` — empty (no re-exports)
- [ ] `lib/rules/_loader.py` — single shared loader with `lru_cache` + `StaleReferenceWarning`
- [ ] `lib/rules/types.py` — `LoanType`, `Region`, `County`, `Borrower`, `Property` Pydantic types
- [ ] PyYAML added to pyproject.toml dependencies + uv.lock regenerated
- [ ] `.pre-commit-config.yaml` consider adding `check-yaml` hook for `data/reference/*.yml` lint (optional but cheap)

## Pitfalls and Landmines

### Pitfall 1: PyYAML downconverts unquoted decimal scalars to float

**What goes wrong:** `0.0085` in YAML parses as `float(0.0085)` = `0.008500000000000001` (literal float-precision artifact), which then poisons every Decimal computed downstream.
**Why it happens:** PyYAML's `safe_load` follows YAML 1.1 spec; bareword decimal numbers are floats.
**How to avoid:** **Quote every numeric value in `data/reference/*.yml`.** `annual_mip_rate: "0.0055"` (quoted str) → `Decimal("0.0055")` after lookup. Add a unit test that asserts `isinstance(raw["body"]["some_rate"], str)` to catch regression.
**Warning sign:** Test fixture passes for a "round" number ($1,000) but fails for $1,000.01.

### Pitfall 2: `effective:` field auto-parses to date but planner forgets to format YAML correctly

**What goes wrong:** `effective: 2026-1-1` (no zero-pad) is technically valid YAML 1.1 but produces unpredictable behavior across PyYAML versions.
**How to avoid:** Always ISO-8601 zero-padded: `effective: 2026-01-01`. The schema test asserts `isinstance(raw["effective"], datetime.date)` which catches non-date input.

### Pitfall 3: Staleness warning fires in CI for legitimate old-but-unchanged YAML (e.g., HPA 1998)

**What goes wrong:** `data/reference/fha-mip-rates.yml` has `effective: 2023-03-20` (HUD has not republished); CI fails or gets noisy because of the warning.
**How to avoid:** The warning is `warnings.warn`, not `raise`; `pytest -W error::lib.rules._loader.StaleReferenceWarning` should NOT be set globally. Tests for staleness use `pytest.warns(...)` to assert it fires for old YAML. **CI does not treat StaleReferenceWarning as an error.** Document this in `pyproject.toml`'s `[tool.pytest.ini_options]` `filterwarnings` if needed.
**Acceptable behavior:** every test run prints a small stderr block listing stale references. This is a feature (it reminds you to refresh annually); tests that need clean stderr use `capsys`/`recwarn` to swallow it.

### Pitfall 4: County-data-missing handling drifts between predicates

**What goes wrong:** `loan_type.classify(county=None)` raises; `usda.evaluate(county=None)` silently uses default. Predicates inconsistent → consumer (Phase 4) doesn't know which calls need pre-validation.
**How to avoid:** Document in `lib/rules/types.py` that `County` is non-`Optional`; predicates accept `County` not `County | None`. If a higher layer doesn't know the county, it raises before calling. Consistent: every predicate fails loud on missing required input.

### Pitfall 5: MIP origination-date grandfathering silently uses wrong rates

**What goes wrong:** Loan endorsed 2014-08 (post-HUD-ML-2013-04 termination rules but pre-HUD-ML-2023-05 rate cut); predicate uses 2026's reduced rate, overstating customer's MIP savings.
**How to avoid:** RUL-04 raises `NotImplementedError` for `endorsement_date < 2023-03-20` rather than silently apply current rates. Document as v2 work. Test: pass an old date, assert raises.

### Pitfall 6: LLPA tier-boundary off-by-one

**What goes wrong:** Credit-score 720 is at the boundary; matrix says "720-739"; predicate accidentally puts 720 in "700-719" bucket. Customer underpriced.
**How to avoid:** Test fixtures at every boundary: 700, 719, 720, 739, 740, 759, 760. Bucket helper `_credit_score_bucket(720) == "720-739"` is unit-tested independently of the LLPA lookup.

### Pitfall 7: Time-zone for effective-date comparison

**What goes wrong:** `effective: 2026-01-01` (interpreted as midnight UTC) vs `date.today()` (system local date). At UTC offset boundaries, staleness check could fire one day early/late.
**How to avoid:** Compare `date` to `date`, not `datetime`. Loader uses `date.today()`. YAML `effective:` parses to `datetime.date`. No timezone in the comparison.

### Pitfall 8: Source-URL freshness — links rot

**What goes wrong:** FHFA reorganizes website; `https://www.fhfa.gov/news/news-release/...` 404s. The YAML still has the old URL.
**How to avoid:** Annual refresh process includes a link-check step (out of scope for Phase 2 itself; deferred to v2 AUTO-01). For Phase 2, make the planner verify each URL in REF-01..07 returns 200 at the time of writing.
**Mitigation:** `notes:` field can include a description/title that survives URL rot ("FHFA news release of 2025-12-04: 'FHFA Announces Conforming Loan Limit Values for 2026'"); future archeology can find the document by name.

### Pitfall 9: Citing the wrong section (CFR vs HUD ML vs IRS Pub)

**What goes wrong:** Predicate docstring says "12 CFR §1026.43(e)(2)(vi)" but the actual rule lives in §1026.43(e)(2). Audit fails.
**How to avoid:** Each per-rule design note above lists the exact citation. The planner must copy these verbatim into predicate docstrings, not paraphrase. The citation-coverage test only checks "Citation:" appears, not whether it's accurate — accuracy is a code-review concern.

### Pitfall 10: Per-county YAML grows unboundedly

**What goes wrong:** REF-01 conforming limits has ~232 high-cost counties; if planner ships the full list, YAML is ~5000 lines and hard to review.
**How to avoid:** Ship the high-cost-county subset only; `loan_type.classify` defaults unlisted counties to baseline. Add a test that asserts at least N (e.g., 50) high-cost counties are present so partial ingestion isn't accidental. Add a `notes:` field documenting the subset policy.

### Pitfall 11: Reg Z tolerance Decimal precision

**What goes wrong:** `Decimal("0.00125")` (1/8 pp) — but APR is computed with more precision; tolerance check uses absolute difference, so precision mismatch would cause spurious "outside tolerance" reports.
**How to avoid:** Predicate accepts `Decimal` inputs (from caller's APR computation, which is Phase 7's territory) and compares with `abs(a - b) <= tolerance`. Decimal arithmetic is exact; no precision drift. Test with values at exactly `tolerance` and just over.

### Pitfall 12: `lru_cache` interaction with test isolation

**What goes wrong:** Test A loads `conforming-limits-2026.yml` and modifies the returned dict (it shouldn't, but might). Test B gets the modified dict from cache.
**How to avoid:** Loader returns a fresh `dict` (use `copy.deepcopy(yaml.safe_load(...))` if mutation worry is real; otherwise discipline = "predicates never mutate loader results"). Tests that need fresh state call `load_reference.cache_clear()` in a fixture.

## Scope Boundaries

### IN SCOPE for Phase 2

- 7 reference YAML files with source/effective fields and structured data bodies
- Shared loader with lru_cache + 12-month staleness warning
- 11 predicate files with citation-header docstrings and Pydantic-typed I/O
- Per-predicate test files with hand-calc fixtures
- Schema test (REF-09) and citation-coverage test (RUL-12/13)
- Pydantic-typed extension types in `lib/rules/types.py` (`LoanType`, `Region`, `County`, `Borrower`, `Property`) — added now because they're shared by ≥3 predicates
- A small `lib/rules/__init__.py` (empty, no re-exports)

### DEFERRED (explicitly out of scope for Phase 2)

- **Wiring rules into Phase 4 affordability** — `lib.affordability` composes predicates; that's Phase 4 (AFFD-07 specifically: "blocked_by VA-RESIDUAL-WEST-FAMILY-4")
- **Wiring rules into Phase 3 amortization** — Phase 3 doesn't need rules; it just emits schedules
- **Live data fetching** — FRED MCP for live rates is Phase 12 (LIVE-01..04). Phase 2 uses YAML-published-by-regulator only.
- **Annual refresh automation** — Playwright scrape of FHFA/HUD/IRS pages is v2 (AUTO-01)
- **County geocoding** — caller is responsible for (state_fips, county_fips) tuples; we don't geocode addresses
- **Pre-2023-03-20 FHA MIP rules** — RUL-04 raises NotImplementedError for old endorsement dates; full grandfathering deferred to v2
- **Pub 936 points-deductibility computation** — RUL-11 returns the loan-limit computation only; points deductibility (Pub 936 §3) requires settlement-statement facts the predicate doesn't have
- **Origination-date grandfathering for HPA high-risk loans** — RUL-05 handles standard + high-risk-midpoint; pre-1999 loans are out of scope (HPA is 1999+)
- **Freddie LPA black-box** — RUL-03 implements the *published* Eligibility Matrix only, not Freddie's actual LPA AUS decision (per PROJECT.md "Out of Scope")
- **Refi treatment of conventional PMI** — at refi, `original_value` resets; that logic lives in Phase 6 (refi), not in RUL-05
- **Property valuation models / Zestimate** — out of v1 entirely

### Things the planner might be tempted to add but should NOT

- A `lib/rules/__init__.py` that re-exports all 11 predicates as `from lib.rules import classify_loan, compute_mip, ...` — defeats the citation-per-file audit trail. Keep `__init__.py` empty.
- A "rules engine" abstraction (`Rule.evaluate(context)`) — overengineering; predicates are functions.
- A YAML schema validator like Cerberus or jsonschema — Pydantic + per-loader validation is sufficient and avoids a new dependency.
- Auto-fetching county data from a geocoding API — wrong scope (PROJECT.md "Out of Scope": "Real-time household sync ... single-machine").

## Suggested Plan Decomposition

The planner can use this as a starting frame. Each plan corresponds to one regulatory regime + its predicates so the regulator → YAML → predicate → fixture → test chain ships in one commit-set.

| Plan | Title | Requirements | Notes |
|------|-------|--------------|-------|
| **02-01** | Reference loader + first reference YAML + RUL-01 (vertical slice) | REF-01 (conforming-limits-2026.yml), REF-08 (staleness — initial impl), REF-09 (schema test — initial), RUL-01 (loan_type), RUL-12 (cited docstring on loan_type), RUL-13 (≥1 fixture) | This is the **pattern-establishing plan**. Ships the loader, the first YAML, the first predicate, the first per-predicate test, the schema test, the citation-coverage test infrastructure. Subsequent plans plug into this skeleton. Depends on Phase 1 only. |
| **02-02** | FHA reference data + classification & MIP predicates | REF-02 (fha-limits), REF-03 (fha-mip-rates), RUL-04 (fha_mip), extends RUL-01 (FHA branches in loan_type if not done in 02-01) | One plan because FHA limits and MIP are tightly coupled (loan-amount tier in MIP table references the limit values). |
| **02-03** | VA reference data + funding fee + residual income | REF-04 (va-funding-fees), REF-05 (va-residual-income), RUL-06 (va_funding_fee), RUL-07 (va_residual_income), extends RUL-01 (VA branches) | VA is its own regime; one plan. |
| **02-04** | USDA + IRS Pub 936 reference + predicates | REF-06 (usda-income-limits), REF-07 (irs-pub936), RUL-08 (usda), RUL-11 (irs_pub936) | These two are smaller; bundling keeps plan count manageable. |
| **02-05** | Conventional PMI (HPA) + Fannie LLPA + Freddie eligibility | RUL-05 (conventional_pmi — no new YAML; HPA values are in code), RUL-02 (fannie_eligibility — adds `data/reference/fannie-llpa-matrix.yml`), RUL-03 (freddie_eligibility — adds `data/reference/freddie-eligibility-matrix.yml` if needed) | **Note to planner:** RUL-02 will likely need a new reference YAML (Fannie LLPA matrix). This is consistent with the "annual refresh = YAML edit" discipline. Treat as REF-08 (Fannie) and REF-09 (Freddie) extensions even though not in the original numbered REF list. |
| **02-06** | ATR/QM + Reg Z tolerances | RUL-09 (atr_qm — adds `data/reference/atr-qm-thresholds.yml` if loan-amount thresholds are extracted; otherwise hardcoded with a CFPB citation), RUL-10 (reg_z — tolerances are Decimal constants in code with citation; no YAML needed) | Smallest plan; finishes the predicate library. |
| **02-07** | Citation-coverage hardening + final schema + integration tests | RUL-12 final, RUL-13 final, REF-09 final, audit pass | Final plan: ensures every predicate from 02-01..06 satisfies the meta-tests; adds any missing fixtures; runs the full suite + mypy + ruff one last time. May be merged into 02-06 if scope allows. |

**Rationale for this decomposition:**
- Plan 02-01 establishes the pattern with a vertical slice (loader + YAML + predicate + test + meta-tests) so subsequent plans are template-replays.
- Plans 02-02..06 group by regulatory regime so a refresh of (e.g.) FHA limits later only touches one plan's worth of code.
- Plan 02-07 is a meta-pass; if the planner is confident the meta-tests have been maintained throughout, it can be merged into 02-06.
- The order respects rule dependencies in *consumer phases* (Phase 4 affordability needs loan_type early, then PMI/MIP, then VA/USDA programs, then ATR/QM at the end), which gives the planner a natural Wave-by-Wave merge order if execution is parallelized later.

**Alternate decomposition (if planner prefers fewer, larger plans):** combine 02-01+02 (reference data + loader + classification + FHA), 02-03+04 (VA + USDA + IRS), 02-05+06+07 (PMI + LLPA + ATR/QM + Reg Z + meta-tests). Three plans total. Per-plan size grows; per-plan complexity stays manageable.

## Code Examples

Verified patterns from official sources:

### Pydantic Annotated Decimal field reuse (from Phase 1 lib/models.py)

```python
# lib/rules/types.py — extension types for Phase 2
from __future__ import annotations
from typing import Annotated, Literal
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from lib.models import Money, Rate

LoanType = Literal[
    "conforming", "high_balance", "jumbo",
    "fha_standard", "fha_high_balance",
    "va_standard", "va_high_balance",
    "usda",
]
Region = Literal["northeast", "midwest", "south", "west"]


class County(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    state_fips: str = Field(min_length=2, max_length=2, pattern=r"^\d{2}$")
    county_fips: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    name: str = Field(min_length=1)


class Borrower(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    credit_score: int = Field(ge=300, le=850)
    family_size: int = Field(ge=1, le=20)
    region: Region | None = None  # required for VA residual income; optional otherwise
    is_va_funding_fee_exempt: bool = False
```

### YAML loader usage in a predicate (from `lib/rules/loan_type.py`)

```python
# lib/rules/loan_type.py
"""Loan-type classification (conforming/jumbo/FHA/VA/USDA).

Citation: 12 USC §1717 (FHFA conforming loan limit authority) + NHA §203(b)(2)
(FHA limits). Per-county overrides from FHFA + HUD annual publications.
Source URL: https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026
Effective: 2026-01-01

Adopts the cfpb/jumbo-mortgage 'fail loud on missing county' pattern: when a
county-specific limit is required to make a determination, this predicate raises
MissingCountyDataError rather than silently defaulting to baseline.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from lib.rules._loader import load_reference
from lib.rules.types import County, LoanType


class MissingCountyDataError(ValueError):
    """Raised when classification requires county-specific limits but caller
    passed county=None and loan_amount > baseline."""


def classify(
    loan_amount: Decimal,
    county: County | None,
    program: Literal["conventional", "fha", "va", "usda"] = "conventional",
    unit_count: int = 1,
) -> LoanType:
    """Classify a loan into one of the LoanType enum values.

    Raises MissingCountyDataError if county is None and loan_amount exceeds the
    baseline (where county-specific high-cost limits would otherwise apply).
    """
    if program == "usda":
        return "usda"
    if program == "conventional":
        ref = load_reference("conforming-limits-2026")
        baseline = Decimal(ref["limits"]["baseline"][f"{_unit_word(unit_count)}_unit"])
        if loan_amount <= baseline:
            return "conforming"
        if county is None:
            raise MissingCountyDataError(
                f"loan_amount {loan_amount} exceeds baseline {baseline}; "
                f"county required to classify as high_balance vs jumbo"
            )
        county_limit = _county_limit(ref, county, unit_count)
        if loan_amount <= county_limit:
            return "high_balance"
        return "jumbo"
    # ...fha + va branches similar...
    raise NotImplementedError(f"program={program} not yet wired")


def _unit_word(n: int) -> str:
    return {1: "one", 2: "two", 3: "three", 4: "four"}[n]


def _county_limit(ref: dict, county: County, unit_count: int) -> Decimal:
    for entry in ref["limits"]["high_cost_counties"]:
        if entry["state_fips"] == county.state_fips and entry["county_fips"] == county.county_fips:
            return Decimal(entry[f"{_unit_word(unit_count)}_unit"])
    return Decimal(ref["limits"]["baseline"][f"{_unit_word(unit_count)}_unit"])
```

### Per-predicate test (from `tests/test_rules/test_loan_type.py`)

```python
# tests/test_rules/test_loan_type.py
"""Tests for lib/rules/loan_type.py.

Citation under test: 12 USC §1717 + NHA §203(b)(2). Per-county subset shipped in
data/reference/conforming-limits-2026.yml.
"""
from __future__ import annotations
import json
from decimal import Decimal
from pathlib import Path
import pytest
from lib.rules.loan_type import classify, MissingCountyDataError
from lib.rules.types import County

FIX = Path(__file__).parent.parent / "fixtures" / "rules"


def _fx(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def test_conforming_baseline_no_county_required() -> None:
    fx = _fx("loan_type_conforming_baseline.json")
    assert classify(Decimal(fx["loan_amount"]), county=None) == "conforming"


def test_high_balance_in_high_cost_county() -> None:
    fx = _fx("loan_type_high_balance_san_francisco.json")
    county = County(state_fips="06", county_fips="075", name="San Francisco")
    assert classify(Decimal(fx["loan_amount"]), county=county) == "high_balance"


def test_jumbo_above_county_ceiling() -> None:
    fx = _fx("loan_type_jumbo_above_ceiling.json")
    county = County(state_fips="06", county_fips="075", name="San Francisco")
    assert classify(Decimal(fx["loan_amount"]), county=county) == "jumbo"


def test_missing_county_when_above_baseline_raises() -> None:
    """RUL-01 fail-loud-on-missing-county per cfpb/jumbo-mortgage pattern."""
    with pytest.raises(MissingCountyDataError, match="county required"):
        classify(Decimal("900000.00"), county=None)


def test_low_cost_county_baseline_loan_treated_as_conforming() -> None:
    """Even though loan < ceiling, low-cost county's limit IS baseline; sub-baseline = conforming."""
    fx = _fx("loan_type_low_cost_county_baseline.json")
    county = County(state_fips="01", county_fips="001", name="Autauga AL")
    assert classify(Decimal(fx["loan_amount"]), county=county) == "conforming"
```

### YAML lint hook (optional pre-commit add)

```yaml
# .pre-commit-config.yaml addition (optional)
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v6.0.0
  hooks:
    - id: check-yaml
      files: ^data/reference/.*\.yml$
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded regulatory constants in Python source | YAML reference data with source/effective fields | This project (precedent: HMDA Platform) | Annual refresh = YAML edit, never code change |
| Big rules engine class with all rules | One predicate per regulatory citation | HMDA Platform pattern (cfpb/hmda-platform Scala) | Audit trail per citation; tests 1:1 with citations |
| Float for fees/rates | Decimal-from-quoted-string in YAML | Phase 1 money discipline | No precision drift across thousands of MIP/LLPA computations |
| 43% DTI cap as gate (pre-2021) | Price-based General QM test (APR-APOR spread) | CFPB Mar 2021 final rule, mandatory 2022-10-01 | Predicate logic is comparison, not DTI math |
| FHA MIP 0.85% annual (post-2013) | 0.55% annual (post-2023-03-20) | HUD ML 2023-05 | 30bps reduction across all >15yr FHA forward mortgages; downstream affordability calculations now show meaningfully lower MIP burdens |
| FHFA 2025 baseline $806,500 | FHFA 2026 baseline $832,750 | FHFA news release 2025-12-04 | $26,250 increase; high-cost ceiling $1,249,125 |

**Deprecated / out-of-current-scope:**
- Pre-2013 FHA MIP rules (different termination — life-of-loan threshold was different; out of v1)
- Pre-1999 PMI rules (HPA didn't exist; out of v1)
- Manual DTI cap for QM (replaced by price-based test; we don't model DTI cap in atr_qm)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | VA M26-7 Chapter 8 funding-fee values listed (2.15% / 3.30% / 1.50% / 1.25% / 0.50% IRRRL) are still current as of 2026-04-26 | REF-04 / RUL-06 | If VA republished M26-7 with different values, all VA fixtures need refresh. **Mitigation:** planner verifies the M26-7 PDF at https://benefits.va.gov/WARMS/docs/admin26/m26-07/ at YAML-write time; staleness warning will fire if effective < 2025-04-26. |
| A2 | VA residual income table cell example ($1,003 for Midwest family of 4, ≥$80k loan) is current per M26-7 | REF-05 / RUL-07 | Same as A1 — verify at YAML-write time. |
| A3 | USDA RD income default ($119,850 / $158,250) and guarantee fees (1.0% upfront, 0.35% annual) are current per USDA RD's last publication | REF-06 / RUL-08 | USDA updates limits annually. Verify against https://www.rd.usda.gov/files/rd-grhlimitmap.pdf at YAML-write time. |
| A4 | Fannie LLPA matrix 2026-01-28 revision is the matrix Phase 2 should encode | RUL-02 | Fannie publishes quarterly updates; matrix is a moving target. Pin to a specific revision date in `effective:`. |
| A5 | ATR/QM loan-amount thresholds ($110,260 / $66,156) are the current indexed values for 2026 | RUL-09 | CFPB indexes annually; verify the latest CFPB Reg Z thresholds adjustment rule (typically published Q4) before pinning. URL [VERIFIED]: https://files.consumerfinance.gov/f/documents/cfpb_combined-reg-z-thresholds-adjustment-rule_2024-11.pdf |
| A6 | RUL-02 (Fannie LLPA) and RUL-03 (Freddie eligibility) should each reference their own published matrix YAML; the 7 reference files in REQUIREMENTS.md (REF-01..07) do not include Fannie/Freddie matrices but the predicates need them | Suggested plan decomposition / Plan 02-05 | If the planner reads requirements as "only 7 reference files, period", the LLPA matrix gets hardcoded in Python — violating reference-data discipline. **Recommendation:** add `data/reference/fannie-llpa-matrix.yml` and `data/reference/freddie-eligibility-matrix.yml` as sub-requirements under RUL-02 / RUL-03 (no separate REF-IDs needed; the discipline is the same). User confirmation desirable. |
| A7 | The `effective:` for FHA MIP (2023-03-20) and VA funding fees (2023-04-07) is intentionally older than the staleness threshold; the warning firing is correct behavior | Pitfall 3 | If the user prefers the warning NOT fire for genuinely-unchanged-by-regulator data, they may want a per-file `staleness_acknowledged_until: YYYY-MM-DD` override field. Phase 2 does not implement this; flag for v2 if noisy. |
| A8 | Pub 936 binding-contract grace period is correctly modeled as a per-debt flag rather than a date-range check | REF-07 / RUL-11 | The grace period (signed before 2017-12-15, closed before 2018-04-01) requires *both* dates — a single `origination_date` field can't capture it. RUL-11 input must include `binding_contract_signed_before_2017_12_15: bool` per debt. Hand-confirm with user. |

## Open Questions

1. **Planner question — should Fannie/Freddie matrices get their own REF-IDs?**
   - What we know: REF-01..07 covers 7 named files; RUL-02 (Fannie) and RUL-03 (Freddie) need matrix data that fits the reference-data pattern.
   - What's unclear: does the user want REF-08 (fannie-llpa-matrix.yml) and REF-09 (freddie-eligibility-matrix.yml) as new requirement IDs (which would change the 22-requirement total to 24), or treat them as implementation details under RUL-02/03?
   - Recommendation: treat as implementation details — don't expand REQUIREMENTS.md mid-flight. Add the two YAMLs as needed under their respective predicate plans. Document in plan rationale that "the predicate's reference data lives in `data/reference/{name}.yml` consistent with REF-01..07 discipline".

2. **Planner question — county subset policy for REF-01 / REF-02**
   - What we know: ~232 high-cost counties exist; shipping all is verbose.
   - What's unclear: which subset to ship? Top 50 by metro population? All California + NY + DC counties?
   - Recommendation: ship the top 50-100 high-cost counties, document subset policy in YAML `notes:`, raise `MissingCountyDataError` for unlisted high-cost counties so users know to extend (better than silently treating an unlisted high-cost county as baseline-only).

3. **Planner question — Fannie LLPA matrix scope**
   - What we know: full matrix is large (FICO buckets × LTV buckets × loan-purpose × occupancy × unit-count = ~hundreds of cells).
   - What's unclear: ship the full primary-residence-purchase 2D table only (~50 cells) and treat investment / second-home / refi as deferred?
   - Recommendation: ship primary-residence-purchase + rate-and-term refi (the two most-common consumer flows). Defer investment + second-home + cash-out adjustments to v2 with `NotImplementedError` raising on those branches.

4. **Planner question — should the `lib/rules/types.py` extensions live there or in `lib/models.py`?**
   - What we know: `lib/models.py` already has `Money`, `Rate`, `Loan`, `Payment`, `Schedule` (Phase 1 frozen surface).
   - What's unclear: adding `LoanType`, `County`, `Borrower`, `Region`, `Property` to `lib/models.py` would extend a frozen-surface file (could be perceived as touching Phase 1 contracts).
   - Recommendation: put new types in `lib/rules/types.py` to keep Phase 1's `lib/models.py` untouched. Phase 4+ imports from both `lib.models` and `lib.rules.types`. If types prove broadly useful (Phase 4 affordability uses County for property location), they can be promoted to `lib/models.py` then.

5. **Planner question — USDA county subset**
   - Same as REF-01 question: USDA has thousands of counties; ship a default + small subset of overrides; document policy.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python ≥3.12 | Phase 2 (already required by Phase 1) | ✓ | 3.12 (per `.python-version`) | — |
| pyyaml | All Phase 2 YAML loaders | ✗ (not in pyproject.toml yet) | needs ≥6.0.2 | Plan 02-01 adds via `uv add 'pyyaml>=6.0.2'` |
| pydantic ≥2.13.3 | All predicate I/O | ✓ (Phase 1) | 2.13.3+ | — |
| python-dateutil ≥2.9.0 | Loader staleness via `relativedelta` | ✓ (Phase 1) | 2.9.0+ | — |
| pytest ≥9 | All tests | ✓ (Phase 1) | 9.0.3+ | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — pyyaml is the one dep to add and there is no fallback (project standardized on YAML for reference data per CONVENTIONS.md). Plan 02-01 must add it.

## Security Domain

(`security_enforcement: true` per `.planning/config.json` — ASVS Level 1.)

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture | yes | Documented in DATA_CONTRACT.md (Phase 1) — Reference Layer is committed regulatory data, not user PII |
| V2 Authentication | no | Library code, no auth surface |
| V3 Session | no | No sessions |
| V4 Access Control | no | Single-user library |
| V5 Input Validation | yes | Pydantic v2 strict-mode + Annotated[Decimal, Field(...)] from Phase 1; predicate I/O validated. YAML inputs validated by `_loader.py` for required fields. |
| V6 Cryptography | no | No crypto |
| V7 Error Handling | yes | `MissingReferenceFieldError`, `MissingCountyDataError`, `StaleReferenceWarning` — fail loud, no silent fallbacks |
| V8 Data Protection | yes | No PII in `data/reference/*.yml`; YAML files contain only published regulatory data. Pre-commit hook from Phase 1 blocks user-layer files |
| V9 Communication | no | No network |
| V10 Malicious Code | yes | `yaml.safe_load` (NOT `yaml.load`) prevents arbitrary code execution from a malicious YAML payload |
| V11 Business Logic | yes | Citation-coverage test enforces audit discipline; predicate-per-citation prevents rule conflation |
| V12 Files | yes | YAML loader reads only from `data/reference/`; no path traversal — file stem is whitelisted by predicate name |
| V13 API | no | No HTTP API |
| V14 Configuration | yes | uv lockfile (Phase 1) ensures reproducible YAML parser version |

### Known Threat Patterns for {data/reference YAML + Python loader}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary code execution via crafted YAML (e.g., `!!python/object/apply:os.system`) | T (Tampering) | **Use `yaml.safe_load`, never `yaml.load` or `yaml.unsafe_load`** — safe_load only emits primitive types and dict/list. Test asserts `Loader is yaml.SafeLoader` (or that `safe_load` is the only call site). |
| Float coercion of unquoted YAML scalars violating money discipline | T | Quote all numeric YAML values as strings; loader test asserts `isinstance(value, str)` for known-money fields |
| Path traversal via predicate filename input (`load_reference("../../etc/passwd")`) | T | Loader takes a `name: str` (file stem); concatenated path is `REFERENCE_DIR / f"{name}.yml"`; filename whitelist could be added (Pydantic Literal of known names) but is overkill for library code where callers are predicates we author |
| Schema drift (missing `source:` or `effective:` after refresh) | T | `MissingReferenceFieldError` raised at load time; REF-09 schema test parametrized over filesystem |
| Stale regulatory data → user makes wrong financial decision | I (Information disclosure / wrong information) | `StaleReferenceWarning` to stderr at every load; future v2 adds annual refresh automation |
| Citation drift (predicate updated, docstring still says old citation) | I | Code-review concern; citation-coverage test only checks structural presence. Mitigation = treat regulatory refresh as a planned deliverable with explicit docstring update step. |
| Loud-failure regression (silent default introduced) | E (Elevation) | RUL-01 test pins `MissingCountyDataError`; future regressions caught immediately |
| Test-fixture tampering (someone "fixes" a fixture to make a failing predicate pass) | T | Fixtures include `citation` and `source_url` and `comment` (hand-calc derivation); code review requires fixture changes to cite a new regulator publication |

## Sources

### Primary (HIGH confidence — official regulator publications)

- https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026 — FHFA 2026 limits announcement [VERIFIED 2026-04-26]
- https://www.hud.gov/news/hud-no-25-145 — HUD 2026 FHA limits announcement [VERIFIED 2026-04-26]
- https://www.hud.gov/sites/dfiles/hudclips/documents/2025-23hsgml.pdf — HUD Mortgagee Letter 2025-23 (2026 FHA forward mortgage limits) [VERIFIED 2026-04-26]
- https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf — HUD Mortgagee Letter 2023-05 (current FHA MIP rates) [VERIFIED 2026-04-26]
- https://benefits.va.gov/WARMS/docs/admin26/m26-07/m26-7-chapter8-borrower-fees-and-charges-and-the-va-funding-fee.pdf — VA M26-7 Chapter 8 funding fees [VERIFIED 2026-04-26]
- https://www.consumerfinance.gov/rules-policy/regulations/1026/22/ — 12 CFR §1026.22 APR tolerances [VERIFIED 2026-04-26]
- https://www.ecfr.gov/current/title-12/chapter-X/part-1026/subpart-C/section-1026.22 — eCFR mirror of §1026.22 [VERIFIED 2026-04-26]
- https://www.federalregister.gov/documents/2020/12/29/2020-27567/qualified-mortgage-definition-under-the-truth-in-lending-act-regulation-z-general-qm-loan-definition — CFPB 2020 General QM final rule (price-based test) [VERIFIED 2026-04-26]
- https://www.consumerfinance.gov/compliance/supervision-examinations/homeowners-protection-act-hpa-or-pmi-cancellation-act-examination-procedures/ — CFPB HPA examination procedures [VERIFIED 2026-04-26]
- https://www.fdic.gov/consumer-compliance-examination-manual/v-5-homeowners-protection-act — FDIC HPA reference [VERIFIED 2026-04-26]
- https://singlefamily.fanniemae.com/media/9391/display — Fannie Mae LLPA Matrix (current revision) [VERIFIED 2026-04-26]
- https://www.rd.usda.gov/files/rd-grhlimitmap.pdf — USDA RD income limit map [VERIFIED 2026-04-26]
- https://eligibility.sc.egov.usda.gov/eligibility/incomeEligibilityAction.do — USDA SFH GLP eligibility worksheet [VERIFIED 2026-04-26]
- https://www.irs.gov/pub/irs-pdf/p936.pdf — IRS Publication 936 [VERIFIED 2026-04-26]
- https://www.irs.gov/publications/p936 — IRS Pub 936 web edition [VERIFIED 2026-04-26]
- https://files.consumerfinance.gov/f/documents/cfpb_combined-reg-z-thresholds-adjustment-rule_2024-11.pdf — CFPB Reg Z thresholds adjustment rule (annual) [VERIFIED 2026-04-26]
- https://github.com/cfpb/hmda-platform — CFPB HMDA Platform (predicate-per-citation pattern reference) [CITED]
- https://github.com/cfpb/jumbo-mortgage — CFPB jumbo-mortgage (fail-loud-on-missing-county pattern) [VERIFIED — pattern confirmed via WebFetch 2026-04-26]

### Secondary (MEDIUM confidence — corroborating community sources)

- https://www.veteransunited.com/valoans/va-funding-fee/ — VA funding fee corroboration
- https://valoannetwork.com/va-residual-income-chart/ — VA residual income table corroboration
- https://www.amerisave.com/learn/fha-mortgage-insurance-premium-mip-in-complete-cost-breakdown-and-removal-strategies — FHA MIP termination corroboration

### Tertiary (LOW confidence — should be re-verified by planner before pinning)

- The exact 2026-indexed ATR/QM loan-amount thresholds ($110,260 / $66,156) — these were the 2021 values; verify 2026 indexed values from the latest CFPB threshold-adjustment rule before encoding in YAML.
- Per-county high-cost limits in REF-01/02 — extract from FHFA's per-county XLSX, not from search-result summaries.
- Specific cell values in REF-05 (VA residual income) — extract from M26-7, not from search-result summaries.

## Metadata

**Confidence breakdown:**
- Loader pattern + staleness check: HIGH — Python idioms; warnings/lru_cache/dateutil are stdlib-grade
- Predicate template + citation-coverage meta-test: HIGH — pattern lifted from HMDA Platform + cfpb/jumbo-mortgage; test code is straightforward filesystem introspection
- Reference YAML schema: HIGH — `source` + `effective` + body is the documented project convention (CONVENTIONS.md)
- Specific 2026 numeric tables (FHFA/FHA/VA/USDA/IRS): MEDIUM — top-line values verified via official URLs; per-cell values (full LLPA matrix, full residual income table, full county XLSX) require extraction by planner from regulator PDFs/XLSXs at YAML-write time
- Plan decomposition: MEDIUM — based on regulatory-regime grouping; planner may consolidate or split based on plan-bounce feedback

**Research date:** 2026-04-26
**Valid until:** 2027-04-26 for pattern + structure; **annual** for numeric values (FHFA/FHA/USDA refresh in late Q4 each year; IRS Pub 936 republishes annually for tax year; HUD ML 2023-05 unchanged unless HUD republishes; VA M26-7 unchanged unless VA republishes).

## RESEARCH COMPLETE
