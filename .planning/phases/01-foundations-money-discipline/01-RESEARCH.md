# Phase 1: Foundations & Money Discipline — Research

**Researched:** 2026-04-26
**Domain:** Python project bootstrap + Decimal money discipline + Pydantic v2 domain models + CI/lint/type-check pipeline + Data Contract enforcement
**Confidence:** HIGH

## Summary

Phase 1 is a pure-bootstrap phase: it stands up the entire Python project skeleton (`pyproject.toml`, `lib/`, `tests/`, `scripts/`, `data/`, `config/`, `.github/`, `.pre-commit-config.yaml`) and locks the four invariants every later phase depends on:

1. **Money discipline** — `Decimal` constructed from strings, `ROUND_HALF_UP` quantization at end of period, never mixed with float, enforced at every Pydantic boundary via `condecimal(max_digits=14, decimal_places=2)` in **strict** mode.
2. **Domain models** — `Loan`, `Schedule`, `Payment` Pydantic v2 BaseModels that reject float input on money fields and serialize Decimals as JSON strings.
3. **Strict CI** — `pytest`, `mypy --strict`, and `ruff check`/`ruff format --check` all run on every push via GitHub Actions and via a local `pre-commit` hook.
4. **Data Contract enforcement** — `DATA_CONTRACT.md` declares User/System/Data layer boundaries; `.gitignore` blocks committed PII; a custom pre-commit hook rejects any staged change to user-layer files.

No mortgage math is implemented in this phase. The four golden-value fixtures in FND-09 are pinned as JSON test data only — they exist so Phase 3 (amortization) has a contract to satisfy. I independently re-derived all four values with `Decimal` + `ROUND_HALF_UP` and they match the requirement exactly (Wikipedia 1264.14, CFPB LE 761.78, computed $400k 2528.27, computed $200k/15yr 1797.66) — these are correct and the planner should treat them as immutable test contracts, not derive them.

**Primary recommendation:** Build the skeleton in three logical waves — (W1) `pyproject.toml` + `uv.lock` + tooling config so `uv sync && uv run pytest` works on a fresh clone; (W2) `lib/money.py` + `lib/models.py` + golden-value fixtures + their loader test; (W3) CI workflow + pre-commit hooks + DATA_CONTRACT.md + `.gitignore`. Wave 3 intentionally lands last so the user-layer-write blocker isn't accidentally tripped by the wave that creates the example files.

## User Constraints

No `CONTEXT.md` exists for Phase 1 — this phase ran straight to research without a `/gsd-discuss-phase` step. Project-level constraints from `CLAUDE.md` and `.planning/PROJECT.md` apply and are listed under **Project Constraints (from CLAUDE.md)** below.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FND-01 | Decimal for all money, from strings, `ROUND_HALF_UP` cent quantization at end-of-period | `lib/money.py` helpers (`to_money`, `quantize_cents`, `decimal_context`); CLAUDE.md "Money discipline" section |
| FND-02 | Pydantic v2 models with `condecimal(max_digits=14, decimal_places=2)` for `Loan`, `Schedule`, `Payment` | `lib/models.py` with `Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2)]` |
| FND-03 | `mypy --strict` enforced in CI | `[tool.mypy]` block in pyproject.toml; CI step `uv run mypy --strict .` |
| FND-04 | `pyproject.toml` with `uv` lockfile, reproducible installs | `uv init` → `pyproject.toml` + `uv.lock` committed; `uv sync --locked` in CI |
| FND-05 | `ruff` enforced via pre-commit + CI | `[tool.ruff]` block; pre-commit hook with `ruff` + `ruff-format`; CI step `uv run ruff check .` |
| FND-06 | GitHub Actions CI runs pytest + mypy + ruff on every push | `.github/workflows/ci.yml` with three job steps after `astral-sh/setup-uv@v7` + `uv sync --locked` |
| FND-07 | `DATA_CONTRACT.md` defines User/System/Data Layer with read-only User Layer | Lifted from `/Users/cujo253/Documents/career-ops/DATA_CONTRACT.md` and adapted; cited in this RESEARCH below |
| FND-08 | `.gitignore` excludes `household.yml`, `profile.yml`, `mortgage-ops.duckdb`, `reports/`, user PII paths | Concrete `.gitignore` patterns listed below |
| FND-09 | Golden-value fixtures pinned (4 oracles) | `tests/fixtures/golden_pmt.json` schema below; loader test asserts each fixture has all required fields |
| FND-10 | Pre-commit hook prevents committing user-layer files | Custom local hook script `scripts/hooks/block-user-layer.py` invoked from `.pre-commit-config.yaml` |

## Architectural Responsibility Map

Phase 1 is single-tier (developer tooling + Python library scaffolding). There is no runtime UI/API/database split yet.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Money type discipline | Library (`lib/money.py`) | — | Single source of truth for `Decimal` context, quantization, and validation helpers; every later calc imports from here |
| Domain model validation | Library (`lib/models.py`) | — | Pydantic models are the boundary contract; scripts validate inbound JSON, lib functions trust the parsed model |
| Test fixtures | Test layer (`tests/fixtures/`) | — | JSON files loaded by tests; do not contain logic |
| Build / dependency mgmt | Project root (`pyproject.toml`) | — | uv-managed; one source of truth for runtime + dev deps |
| Static analysis | Tooling (`pyproject.toml` + pre-commit + CI) | — | ruff, mypy, pytest configs all live in `pyproject.toml`; pre-commit and CI are runners |
| Data Contract enforcement | Pre-commit hook + `.gitignore` + `DATA_CONTRACT.md` | CI (optional gate) | Local hook is primary; `.gitignore` is belt-and-suspenders; CI server-side gate is an open question (see Open Questions) |

## Project Constraints (from CLAUDE.md)

These are non-negotiable and apply to every Phase 1 deliverable:

- **Decimal for all money** — never float in money expressions. Construct from strings: `Decimal("0.065")` not `Decimal(0.065)`.
- **`ROUND_HALF_UP` end-of-period only** — never mid-calculation; never default Python rounding (which is `ROUND_HALF_EVEN`).
- **Pydantic v2 `condecimal` at script boundaries** — every JSON-in/JSON-out script validates inputs before lib code touches them.
- **No `Co-Authored-By` or AI attribution in commits** — global user rule from `~/CLAUDE.md`.
- **Calc / LLM separation** — Phase 1 ships no scripts that compute mortgage math; that arrives in Phase 3+. But the *seams* (script entrypoint pattern, JSON in/out contract, Pydantic at boundary) are established here.
- **User Layer is READ-ONLY from system code** — `config/household.yml`, `config/profile.yml`, `modes/_profile.md` are never auto-updated; pre-commit hook enforces.
- **Sibling-repo prior art** — `career-ops` and `card-ops` lack CI/lint/type-check; Phase 1 explicitly adopts what they're missing. Do not depend on or copy code from them — read for *patterns* only.
- **Skill conventions deferred** — `.claude/skills/mortgage-ops/` is Phase 10's territory; Phase 1 must not create skill files.

## Standard Stack

### Core (runtime dependencies — Phase 1 only adds these to pyproject.toml; only `pydantic` and `python-dateutil` are actually imported in Phase 1 code)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.13.3 | `BaseModel`, `condecimal`, `Field(strict=True, max_digits=14, decimal_places=2)` for Loan/Schedule/Payment | First-class `Decimal` support; strict mode rejects float; JSON serializes Decimal as string by default `[VERIFIED: PyPI 2026-04-20]` |
| python-dateutil | >=2.9.0 | Will be used in Phase 3 for `relativedelta(weeks=2)` biweekly scheduling. Adding now keeps the lockfile stable. | De-facto standard; already transitive via pandas in later phases `[VERIFIED: PyPI 2024-03-01]` |
| numpy-financial | >=1.0.0 | Phase 3 oracle for PMT/IPMT/PPMT. Add to pyproject.toml in Phase 1 so the dep is locked; do not import from it yet. | Active main 2025; only release is 1.0.0 from 2019 — pin exact version, accept no type stubs `[VERIFIED: PyPI 2019-10-18]` |

### Dev dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | >=9.0 | Test framework; exact-equality assertions for Decimal `[VERIFIED: PyPI 2026-04-07]` |
| mypy | >=1.20 | `--strict` type checking; first-class `Decimal` type understanding `[VERIFIED: PyPI 2026-04-21]` |
| ruff | >=0.15 | Lint + format (replaces black + isort + flake8) `[VERIFIED: PyPI 2026-04-24]` |
| pre-commit | >=4.6 | Local hook runner; `pre-commit install` wires `.pre-commit-config.yaml` into git `[VERIFIED: PyPI 2026-04-21]` |

### Tools (not Python deps)

| Tool | Version | Purpose |
|------|---------|---------|
| uv | >=0.11.7 | Project + lockfile manager (replaces pip + venv + requirements.txt); pinned in CI `[VERIFIED: PyPI 2026-04-15]` |
| GitHub Actions | n/a | CI runner; uses `astral-sh/setup-uv@v7` and `actions/checkout@v6` `[CITED: docs.astral.sh/uv/guides/integration/github/]` |

### Alternatives Considered (and rejected)

| Instead of | Could Use | Why Rejected |
|------------|-----------|--------------|
| uv | pip + requirements.txt | Slower; no lockfile by default; sibling repos demonstrated the gap. uv is single-tool and the project already chose it. |
| Pydantic v2 + condecimal | dataclasses + manual Decimal validation | Plain dataclasses don't validate; we'd reimplement what Pydantic does first-class. Strictly worse for finance. |
| ruff | black + isort + flake8 | Three tools, slower, more config files. ruff is one binary, one config block. |
| pytest | unittest | unittest works, but pytest fixtures + parametrize make the golden-value tests in FND-09 trivially scalable to Phase 3+. |
| Custom user-layer-write hook | `pre-commit-hooks/no-commit-to-branch` or `detect-secrets` | Neither covers the "block changes to a list of paths" pattern cleanly; a 30-line local Python hook is the cleanest solution. |

### Verified versions (as of 2026-04-26 via PyPI JSON API)

```
pydantic         2.13.3   (released 2026-04-20)
numpy-financial  1.0.0    (released 2019-10-18)  ← only release; track main is academic, no PyPI 1.0.1
python-dateutil  2.9.0    (released 2024-03-01)
ruff             0.15.12  (released 2026-04-24)
mypy             1.20.2   (released 2026-04-21)
uv               0.11.7   (released 2026-04-15)
pytest           9.0.3    (released 2026-04-07)
pre-commit       4.6.0    (released 2026-04-21)
```

### Installation (Phase 1 actually runs this)

```bash
# inside the repo root, after uv is on PATH
uv init --python 3.12 --no-readme    # creates pyproject.toml + .python-version (do NOT use --app, we want a lib layout)
uv add pydantic 'python-dateutil>=2.9' 'numpy-financial==1.0.0'
uv add --dev 'pytest>=9' 'mypy>=1.20' 'ruff>=0.15' 'pre-commit>=4.6'
uv sync --locked
uv run pre-commit install
```

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────────────────┐
   developer ──git─────▶│   pre-commit hooks (local)       │
                        │  • ruff check                    │
                        │  • ruff format --check           │
                        │  • mypy --strict (changed files) │
                        │  • block-user-layer.py (custom)  │
                        └──────────┬───────────────────────┘
                                   │  pass → commit
                                   ▼
                        ┌──────────────────────────────────┐
                        │  GitHub  (push / PR)             │
                        └──────────┬───────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────────────────┐
                        │  .github/workflows/ci.yml        │
                        │  ├─ astral-sh/setup-uv@v7        │
                        │  ├─ uv sync --locked --dev       │
                        │  ├─ uv run ruff check .          │
                        │  ├─ uv run ruff format --check . │
                        │  ├─ uv run mypy --strict .       │
                        │  └─ uv run pytest                │
                        └──────────┬───────────────────────┘
                                   │  green → merge
                                   ▼
            ┌──────────────────────────────────────────────────────────┐
            │                    repo (committed)                      │
            │                                                          │
            │  pyproject.toml + uv.lock        ← W1                    │
            │  lib/                                                    │
            │   ├─ __init__.py    (empty exports)                      │
            │   ├─ money.py       Decimal helpers       ← W2           │
            │   └─ models.py      Loan/Schedule/Payment ← W2           │
            │                                                          │
            │  tests/                                                  │
            │   ├─ conftest.py                                         │
            │   ├─ fixtures/                                           │
            │   │   └─ golden_pmt.json   4 pinned values  ← W2         │
            │   ├─ test_money.py                                       │
            │   ├─ test_models.py                                      │
            │   └─ test_fixtures.py      schema check    ← W2          │
            │                                                          │
            │  .github/workflows/ci.yml          ← W3                  │
            │  .pre-commit-config.yaml           ← W3                  │
            │  scripts/hooks/block-user-layer.py ← W3                  │
            │  DATA_CONTRACT.md                  ← W3                  │
            │  .gitignore                        ← W3                  │
            │                                                          │
            │  config/household.example.yml      ← W3 (committed,      │
            │                                       redacted skeleton) │
            │  config/    (household.yml gitignored)                   │
            │  data/      (mortgage-ops.duckdb gitignored)             │
            │  data/reference/   (empty, .gitkeep) ← seam for Phase 2  │
            │  reports/          (.gitignore'd, .gitkeep retained)     │
            └──────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
mortgage-ops/
├── .github/
│   └── workflows/
│       └── ci.yml                       # FND-06
├── .planning/                           # already exists
├── .pre-commit-config.yaml              # FND-05, FND-10
├── .python-version                      # written by `uv init` — pin to 3.12
├── .gitignore                           # FND-08
├── CLAUDE.md                            # already exists — do not modify
├── DATA_CONTRACT.md                     # FND-07
├── pyproject.toml                       # FND-04, FND-03 (mypy), FND-05 (ruff)
├── uv.lock                              # FND-04 — committed
├── README.md                            # one-paragraph stub; planner can defer to Phase 12
├── lib/
│   ├── __init__.py                      # empty — no exports yet (seam for later phases)
│   ├── money.py                         # FND-01
│   └── models.py                        # FND-02
├── tests/
│   ├── __init__.py                      # marker file, empty
│   ├── conftest.py                      # shared fixtures (Decimal context, fixture loader)
│   ├── fixtures/
│   │   ├── __init__.py                  # marker file, empty
│   │   └── golden_pmt.json              # FND-09 — four pinned monthly P&I oracles
│   ├── test_money.py                    # exercises lib/money.py
│   ├── test_models.py                   # exercises lib/models.py
│   └── test_fixtures.py                 # asserts golden_pmt.json schema is intact
├── scripts/
│   └── hooks/
│       └── block-user-layer.py          # FND-10 — custom pre-commit hook
├── config/
│   ├── household.example.yml            # committed; redacted skeleton with no real values
│   └── household.yml                    # gitignored — created by user later
├── data/
│   ├── reference/
│   │   └── .gitkeep                     # seam for Phase 2; empty directory
│   └── (mortgage-ops.duckdb)            # gitignored — created in Phase 9
└── reports/
    └── .gitkeep                         # seam; reports themselves gitignored
```

**Why this layout:**
- `lib/__init__.py` is empty so Phase 3+ can add `from .amortize import build_schedule` without churning Phase 1's surface.
- `scripts/hooks/` (not `.git/hooks/` directly) keeps the user-layer blocker version-controlled and reusable.
- `tests/fixtures/__init__.py` marker keeps mypy from complaining about implicit namespace packages under `--strict`.
- `data/reference/.gitkeep` and `reports/.gitkeep` exist *only* to keep the seam directories tracked; the wave-3 plan must commit the keep file before any other directory contents.

### Pattern 1: Decimal helper module (FND-01)

**What:** A tiny `lib/money.py` that owns the project's `Decimal` discipline. Every other module imports from here; nobody constructs `Decimal` from a literal in scattered places.

**When to use:** Always. Money fields, rates, ratios — any numeric quantity that must round predictably.

**Example (concrete, copy-pasteable):**

```python
# lib/money.py
"""Money discipline helpers.

Every Decimal in this project is constructed from strings, quantized end-of-period
with ROUND_HALF_UP, and never mixed with float in the same expression.
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext, localcontext, Context
from typing import Final

CENT: Final[Decimal] = Decimal("0.01")
"""The quantum for end-of-period money rounding."""

MONEY_CONTEXT: Final[Context] = Context(prec=28, rounding=ROUND_HALF_UP)
"""Project-wide Decimal context. prec=28 is Python default; we set rounding explicitly
because the global default is ROUND_HALF_EVEN (banker's rounding), which is wrong for
US consumer finance."""


def to_money(value: str) -> Decimal:
    """Construct a money Decimal from a string. Floats are rejected at the type level
    by mypy --strict; runtime callers passing a float will see the str() coercion
    inherit the float error, which is why every entry point should accept str.
    """
    return Decimal(value)


def quantize_cents(value: Decimal) -> Decimal:
    """Round a Decimal to two places using ROUND_HALF_UP. Call ONCE at end-of-period."""
    with localcontext(MONEY_CONTEXT):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
```

**Verification (test_money.py):**

```python
# tests/test_money.py
from decimal import Decimal
import pytest
from lib.money import to_money, quantize_cents, CENT


def test_to_money_from_string() -> None:
    assert to_money("0.065") == Decimal("0.065")


def test_to_money_from_float_string_preserves_string() -> None:
    # the string IS the canonical form; round-trip must not change it
    assert to_money("1264.14") == Decimal("1264.14")


def test_quantize_cents_uses_round_half_up() -> None:
    # Python's default ROUND_HALF_EVEN rounds 0.005 -> 0.00 (banker's)
    # ROUND_HALF_UP rounds 0.005 -> 0.01 (standard)
    assert quantize_cents(Decimal("0.005")) == Decimal("0.01")
    assert quantize_cents(Decimal("0.015")) == Decimal("0.02")
    assert quantize_cents(Decimal("0.025")) == Decimal("0.03")  # NOT 0.02
```

### Pattern 2: Pydantic v2 domain models (FND-02)

**What:** `Loan`, `Schedule`, `Payment` BaseModels with strict, condecimal-typed money fields. The "Annotated" form is preferred over the bare `condecimal()` callable per Pydantic 2.x docs.

**Example:**

```python
# lib/models.py
"""Domain models for mortgage-ops. Phase 1 defines the shapes; later phases populate."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# Money is always non-negative, max 12 digits before decimal + 2 after = 14 total.
# strict=True rejects float input at validation time per Pydantic v2 docs.
Money = Annotated[
    Decimal,
    Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0")),
]

# Rate is a fraction (0.065 = 6.5%), max 7 digits + 6 places (e.g. 0.999999).
Rate = Annotated[
    Decimal,
    Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1")),
]


class Loan(BaseModel):
    """Inputs to an amortization. Phase 3 will use this; Phase 1 just defines it."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    principal: Money
    annual_rate: Rate
    term_months: int = Field(ge=1, le=600)
    origination_date: date | None = None
    loan_type: Literal["fixed", "arm", "fha", "va", "usda", "jumbo"] = "fixed"


class Payment(BaseModel):
    """A single period in the schedule."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    period: int = Field(ge=1)
    payment_date: date
    payment: Money       # P + I + extra_principal
    principal: Money
    interest: Money
    extra_principal: Money = Decimal("0.00")
    balance: Money       # post-payment balance


class Schedule(BaseModel):
    """Output of an amortization run. Phase 3 produces this; Phase 1 only defines."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    monthly_pi: Money               # the headline number every consumer asks for
    total_interest: Money
    payments: list[Payment]
```

**Verification (test_models.py):**

```python
# tests/test_models.py
from decimal import Decimal
import pytest
from pydantic import ValidationError
from lib.models import Loan


def test_loan_accepts_decimal_from_string() -> None:
    loan = Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.065000"), term_months=360)
    assert loan.principal == Decimal("400000.00")


def test_loan_rejects_float_principal() -> None:
    # strict=True must reject floats — this is the load-bearing assertion for FND-01
    with pytest.raises(ValidationError) as exc:
        Loan(principal=400000.0, annual_rate=Decimal("0.065"), term_months=360)  # type: ignore[arg-type]
    assert "decimal_type" in str(exc.value) or "Input should be" in str(exc.value)


def test_loan_rejects_too_many_decimal_places() -> None:
    with pytest.raises(ValidationError):
        Loan(principal=Decimal("400000.001"), annual_rate=Decimal("0.065"), term_months=360)


def test_loan_serializes_decimal_as_string_in_json() -> None:
    loan = Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.065000"), term_months=360)
    j = loan.model_dump_json()
    assert '"principal":"400000.00"' in j
    assert '"annual_rate":"0.065000"' in j
```

### Pattern 3: Golden-value fixtures as JSON (FND-09)

**What:** A single `tests/fixtures/golden_pmt.json` file holding all four pinned monthly P&I oracles. Phase 3's amortization tests load this same file. Phase 1's job is to commit the file with the correct values and a loader test that asserts the schema.

**Schema:**

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "fixtures": [
    {
      "id": "wikipedia_200k_30yr",
      "source": "https://en.wikipedia.org/wiki/Mortgage_calculator",
      "principal": "200000.00",
      "annual_rate": "0.065000",
      "term_months": 360,
      "expected_monthly_pi": "1264.14",
      "rounding": "ROUND_HALF_UP",
      "notes": "Wikipedia worked example; canonical reference."
    },
    {
      "id": "cfpb_le_162k_30yr",
      "source": "https://files.consumerfinance.gov/f/201405_cfpb_loan-estimate-h-24-b.pdf",
      "principal": "162000.00",
      "annual_rate": "0.038750",
      "term_months": 360,
      "expected_monthly_pi": "761.78",
      "rounding": "ROUND_HALF_UP",
      "notes": "CFPB Loan Estimate sample form H-24(B); regulator-published worked example."
    },
    {
      "id": "computed_400k_30yr",
      "source": "computed in-tree with Decimal + ROUND_HALF_UP; cross-verified against any standard amortization calculator",
      "principal": "400000.00",
      "annual_rate": "0.065000",
      "term_months": 360,
      "expected_monthly_pi": "2528.27",
      "rounding": "ROUND_HALF_UP",
      "notes": "Stress-test scale of Wikipedia oracle (2x principal, same rate/term)."
    },
    {
      "id": "computed_200k_15yr",
      "source": "computed in-tree with Decimal + ROUND_HALF_UP",
      "principal": "200000.00",
      "annual_rate": "0.070000",
      "term_months": 180,
      "expected_monthly_pi": "1797.66",
      "rounding": "ROUND_HALF_UP",
      "notes": "Shorter-term sanity check (15yr instead of 30yr)."
    }
  ]
}
```

**Verification (test_fixtures.py):**

```python
# tests/test_fixtures.py
"""Phase 1 only validates the fixture file's SHAPE. Phase 3's test_amortize.py
will compute against it. Keeping these separate prevents Phase 1 from importing
amortization code (which doesn't exist yet)."""
import json
from decimal import Decimal
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden_pmt.json"

REQUIRED_FIELDS = {"id", "source", "principal", "annual_rate", "term_months",
                   "expected_monthly_pi", "rounding", "notes"}
EXPECTED_IDS = {"wikipedia_200k_30yr", "cfpb_le_162k_30yr",
                "computed_400k_30yr", "computed_200k_15yr"}


def test_golden_pmt_fixture_loads() -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    assert "fixtures" in data
    assert isinstance(data["fixtures"], list)
    assert len(data["fixtures"]) == 4


def test_golden_pmt_has_all_four_oracles() -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    ids = {f["id"] for f in data["fixtures"]}
    assert ids == EXPECTED_IDS


@pytest.mark.parametrize("idx", range(4))
def test_golden_pmt_each_fixture_well_formed(idx: int) -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    fx = data["fixtures"][idx]
    assert REQUIRED_FIELDS <= fx.keys()
    # money values must be parseable as Decimal
    Decimal(fx["principal"])
    Decimal(fx["annual_rate"])
    Decimal(fx["expected_monthly_pi"])
    assert fx["rounding"] == "ROUND_HALF_UP"
    assert isinstance(fx["term_months"], int)


def test_pinned_expected_values() -> None:
    """Lock the actual numbers. If anyone edits the file, the test fails loud."""
    data = {f["id"]: f for f in json.loads(FIXTURE_PATH.read_text())["fixtures"]}
    assert data["wikipedia_200k_30yr"]["expected_monthly_pi"] == "1264.14"
    assert data["cfpb_le_162k_30yr"]["expected_monthly_pi"] == "761.78"
    assert data["computed_400k_30yr"]["expected_monthly_pi"] == "2528.27"
    assert data["computed_200k_15yr"]["expected_monthly_pi"] == "1797.66"
```

> **Note on values:** I independently computed all four with `Decimal` + `ROUND_HALF_UP` (`P × r/12 × (1+r/12)^n / ((1+r/12)^n − 1)`) on 2026-04-26. Output exactly matched the four pinned values in FND-09. The planner should treat these as immutable contracts and not derive them at planning time. `[VERIFIED: in-session Python computation]`

### Pattern 4: pyproject.toml (FND-04, FND-03 mypy, FND-05 ruff, pytest)

**What:** Single source of truth for runtime deps, dev deps, and tool config.

**Example:**

```toml
# pyproject.toml
[project]
name = "mortgage-ops"
version = "0.1.0"
description = "Personal-use mortgage analysis: deterministic Python calc engine + Claude skill frontend"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.13.3",
    "python-dateutil>=2.9.0",
    "numpy-financial==1.0.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0",
    "mypy>=1.20",
    "ruff>=0.15",
    "pre-commit>=4.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["lib"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["lib", "tests", "scripts"]

[tool.ruff.lint]
select = [
    "E", "F", "W",   # pycodestyle + pyflakes
    "I",             # isort
    "UP",            # pyupgrade
    "B",             # bugbear
    "SIM",           # simplify
    "RUF",           # ruff-specific
    "TCH",           # type-checking imports
    "PT",            # pytest style
]
ignore = ["E501"]    # ruff-format owns line length

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
files = ["lib", "tests", "scripts"]
plugins = ["pydantic.mypy"]
# Decimal-handling edge cases — see Pitfalls section
warn_unreachable = true
warn_redundant_casts = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "numpy_financial"
ignore_missing_imports = true   # numpy-financial 1.0.0 ships no type stubs (see Pitfalls)

[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
```

### Pattern 5: GitHub Actions workflow (FND-06)

**What:** A single `ci.yml` job that does setup → sync → lint → format-check → typecheck → test, in that order, all gated.

**Example:**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          version: "0.11.7"        # pinned per uv docs best practice
          enable-cache: true        # caches ~/.local/share/uv

      - name: Set up Python
        run: uv python install 3.12

      - name: Sync deps (frozen)
        run: uv sync --locked --dev

      - name: Ruff lint
        run: uv run ruff check .

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Mypy strict
        run: uv run mypy --strict .

      - name: Pytest
        run: uv run pytest
```

`[CITED: docs.astral.sh/uv/guides/integration/github/]` — `astral-sh/setup-uv@v7` is the current recommended action; `enable-cache: true` is the official caching strategy; `uv sync --locked` enforces lockfile reproducibility.

### Pattern 6: Pre-commit hooks (FND-05, FND-10)

**What:** `.pre-commit-config.yaml` runs ruff + mypy + the user-layer-write blocker before any commit. Mypy must run on **changed files only** at the local hook level (running full `--strict` on every commit is slow); CI runs the full sweep.

**Example:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.20.2
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.13.3
          - python-dateutil>=2.9.0
        args: [--strict]
        # mypy hook runs on changed files only by default — CI catches the rest

  - repo: local
    hooks:
      - id: block-user-layer
        name: Block commits to user-layer files (DATA_CONTRACT.md)
        entry: python scripts/hooks/block-user-layer.py
        language: system
        stages: [pre-commit]
        always_run: true        # we need to inspect the staged set, not just changed files
        pass_filenames: true
```

### Pattern 7: User-layer-write blocker (FND-10)

**What:** A 30-line Python script invoked by pre-commit that fails the commit if any staged file matches a User Layer path glob.

**Example:**

```python
# scripts/hooks/block-user-layer.py
#!/usr/bin/env python3
"""Pre-commit hook: refuse to commit any User Layer file.

User Layer is defined in DATA_CONTRACT.md and contains the user's PII / customizations.
This hook is the enforcement mechanism for FND-10.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Exact paths or glob-stems that are NEVER allowed in a commit.
USER_LAYER_PATTERNS: tuple[str, ...] = (
    "config/household.yml",
    "config/profile.yml",
    "modes/_profile.md",
    # DuckDB and reports are gitignored, but block them as belt-and-suspenders
    # in case .gitignore is ever bypassed with `git add -f`.
)
USER_LAYER_GLOB_DIRS: tuple[str, ...] = (
    "reports/",      # any file under reports/ except .gitkeep
)
ALLOWED_KEEP_FILES: frozenset[str] = frozenset({"reports/.gitkeep", "data/reference/.gitkeep"})

DATA_DUCKDB_SUFFIXES: tuple[str, ...] = (".duckdb",)


def is_user_layer(path: str) -> bool:
    if path in ALLOWED_KEEP_FILES:
        return False
    if path in USER_LAYER_PATTERNS:
        return True
    if any(path.startswith(d) for d in USER_LAYER_GLOB_DIRS):
        return True
    if any(path.endswith(s) for s in DATA_DUCKDB_SUFFIXES):
        return True
    return False


def main(argv: list[str]) -> int:
    offenders = [a for a in argv[1:] if is_user_layer(a)]
    if not offenders:
        return 0
    print("ERROR: refusing to commit User Layer files (DATA_CONTRACT.md):", file=sys.stderr)
    for o in offenders:
        print(f"  - {o}", file=sys.stderr)
    print(
        "\nThese paths are User Layer per DATA_CONTRACT.md and must never be committed.\n"
        "If this is a mistake (e.g. you intended to commit `config/household.example.yml`),\n"
        "double-check the path. The example file is committable; the live file is not.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### Pattern 8: DATA_CONTRACT.md (FND-07)

**What:** A markdown document declaring the four-layer split (User / System / Data / Reference) with explicit lists of which paths belong to which layer.

**Outline:**

```markdown
# Data Contract

This document defines which files belong to the **User Layer** (read-only from system code),
the **System Layer** (auto-updatable code & instructions), the **Data Layer** (generated
artifacts), and the **Reference Layer** (committed regulatory data, manually refreshed).

## User Layer (NEVER auto-updated; gitignored)

| Path | Purpose |
|------|---------|
| `config/household.yml` | Household income, applicants, monthly debts, location |
| `config/profile.yml` | User identity, preferences |
| `modes/_profile.md` | (Phase 10) user-specific narrative overrides |
| `data/mortgage-ops.duckdb` | (Phase 9) computed scenarios + reports |
| `reports/*.md` | (Phase 10+) generated reports |

**Rule:** No system process — including pre-commit hooks, CI, scripts, or future Claude skills —
may write to a User Layer path. Pre-commit hook `scripts/hooks/block-user-layer.py` enforces this
for committed changes. Runtime enforcement is each script's responsibility.

## System Layer (auto-updatable; committed)

| Path | Purpose |
|------|---------|
| `lib/**` | Python calc engine |
| `scripts/**` | CLI helpers (Phase 3+) and tooling hooks |
| `tests/**` | Test suite + fixtures |
| `pyproject.toml` / `uv.lock` | Build + deps |
| `.github/workflows/**` | CI |
| `.pre-commit-config.yaml` | Hook config |
| `CLAUDE.md` / `DATA_CONTRACT.md` / `README.md` | Project docs |
| `config/household.example.yml` | Schema example (no real values) |

## Data Layer (generated; gitignored)

| Path | Purpose |
|------|---------|
| `data/mortgage-ops.duckdb` | Phase 9 — single-file persistence |
| `data/market/*.parquet` | Phase 12 — FRED rate cache |
| `reports/{###}-{slug}-{YYYY-MM-DD}.md` | Phase 10+ — generated reports |

## Reference Layer (committed; manually refreshed annually)

| Path | Purpose |
|------|---------|
| `data/reference/*.yml` | Phase 2 — regulatory data with `source:` URL + `effective:` date |
| `data/known-loans.yml` | Phase 9 — product catalog |

Phase 1 commits the User / System / Data / Reference taxonomy and the empty `data/reference/`
directory (with `.gitkeep`). Reference Layer YAML files are added in Phase 2.
```

### Pattern 9: `.gitignore` (FND-08)

```gitignore
# Python
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
*.egg-info/
build/
dist/

# uv
.uv-cache/

# User Layer (DATA_CONTRACT.md) — NEVER commit
config/household.yml
config/profile.yml
modes/_profile.md

# Data Layer (generated)
data/*.duckdb
data/market/
data/mortgage-ops.duckdb-wal
data/mortgage-ops.duckdb-shm

# Reports (generated)
reports/*
!reports/.gitkeep

# OS / editor
.DS_Store
.idea/
.vscode/
```

### Anti-Patterns to Avoid

- **Adding `pyproject.toml` `[project.scripts]` entries in Phase 1.** No CLI scripts exist yet; entry points come in Phase 3.
- **Importing from `lib.amortize` etc. in Phase 1 tests.** None of those modules exist yet. `tests/test_money.py` and `tests/test_models.py` only import from `lib.money` and `lib.models`.
- **Computing the four golden values inside the fixture loader test.** That defeats the contract — Phase 3 must compute and assert against the JSON. Phase 1 only validates the JSON's shape and pinned strings.
- **Running mypy on the whole repo in pre-commit.** Slow. Pre-commit runs on changed files; CI runs the full `mypy --strict .`.
- **Putting `Decimal()` literals in `lib/models.py` field defaults from numbers.** `Decimal("0.00")` is the only safe form — `Decimal(0.00)` introduces float error.
- **`Decimal(rate) * Decimal(principal)` where `rate` is `float`.** Always cast at the boundary; never inside expressions.
- **Auto-formatting `config/household.example.yml` with a YAML formatter pre-commit hook.** Comments would be lost; this file is hand-edited.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Money type validation | Custom Decimal subclass with bounds | Pydantic v2 `Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2)]` | Strict mode + max_digits/decimal_places + JSON-string serialization is already correct; subclassing Decimal has subtle pickle / arithmetic bugs |
| Lockfile | Hand-pinned `requirements.txt` | `uv.lock` | uv resolves cross-platform, hashes wheels, and `uv sync --locked` enforces |
| Lint + format + import-sort | black + isort + flake8 | ruff | One binary, one config block in pyproject.toml |
| Pre-commit hook framework | Shell scripts in `.git/hooks/` | `pre-commit` package | Versioned config, dev-installable, runs on CI too |
| YAML schema validation | jsonschema + handwritten schema for household.yml | Pydantic models with `model_validate` from yaml.safe_load | Same model serves runtime + tests; one source of truth |
| GitHub Actions Python setup | Hand-rolled `setup-python` + `pip install` | `astral-sh/setup-uv@v7` + `uv sync --locked` | Built-in caching; lockfile reproducibility; ~30s faster cold-start |
| User-layer enforcement | Trust the developer not to commit `household.yml` | Custom pre-commit hook + `.gitignore` | Two layers: gitignore stops `git add`, hook catches `git add -f` |

**Key insight:** Phase 1 is mostly *configuration*, not code. The temptation to write helpers (a Decimal subclass, a custom config loader, etc.) is strong and almost always wrong — every problem in this phase has a battle-tested off-the-shelf solution.

## Runtime State Inventory

This is a greenfield phase — no pre-existing runtime state to migrate.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — repo has no databases yet | None |
| Live service config | None — no external services configured | None |
| OS-registered state | None — no scheduled tasks, no installed binaries this phase registers | None |
| Secrets/env vars | None — Phase 1 introduces no env-driven behavior | None |
| Build artifacts | None — `uv.lock` is *new* in this phase, not pre-existing | None |

**Nothing found in any category** — this is a clean greenfield bootstrap. The only thing to track forward is that **Phase 9 will introduce `data/mortgage-ops.duckdb`** and Phase 1's `.gitignore` must already exclude it (FND-08), which it does.

## Common Pitfalls

### Pitfall 1: `Decimal(0.1)` instead of `Decimal("0.1")`

**What goes wrong:** `Decimal(0.1)` yields `Decimal('0.1000000000000000055511151231257827021181583404541015625')` — the float error is preserved permanently.

**Why it happens:** Constructing `Decimal` from a numeric literal looks natural to anyone familiar with `int()` / `float()`.

**How to avoid:** `lib/money.py.to_money(value: str) -> Decimal` is type-annotated to accept *only* `str`. mypy `--strict` rejects calls passing a float. All test fixtures use string-typed JSON (loaded by `json.load`, then `Decimal(str_value)`).

**Warning signs:** A test passes for `Decimal("0.1")` but fails for `0.1` — the latter shouldn't even type-check, so a test that demonstrates float rejection (see `test_loan_rejects_float_principal` above) is required.

### Pitfall 2: Python's default rounding is `ROUND_HALF_EVEN`, not `ROUND_HALF_UP`

**What goes wrong:** `Decimal("0.005").quantize(Decimal("0.01"))` returns `0.00`, not `0.01`. Cents drift in the user-unfriendly direction. Banker's rounding is correct for accounting averages; standard rounding is correct for consumer mortgage math (matches lender amort schedules).

**Why it happens:** The Python docs prominently feature `ROUND_HALF_EVEN`; many tutorials don't pass `rounding=`.

**How to avoid:** `quantize_cents()` always passes `rounding=ROUND_HALF_UP`. The project-wide `MONEY_CONTEXT` is also constructed with `rounding=ROUND_HALF_UP`. Test asserts `quantize_cents(Decimal("0.005")) == Decimal("0.01")`.

**Warning signs:** A computed monthly P&I is one cent below the lender's quoted figure with curiously-half-the-time frequency.

### Pitfall 3: Pydantic v2 `condecimal` JSON output is a string, but consumers expect a number

**What goes wrong:** Phase 3 emits `{"monthly_pi": "1264.14"}` (string); a downstream JS skill consumer parses with `JSON.parse()` and gets a string where it expected a number.

**Why it happens:** Pydantic v2's correct-for-finance default is to JSON-serialize Decimal as string (preserves precision). Most JSON consumers naively assume number. `[VERIFIED: github.com/pydantic/pydantic/issues/7457 — confirms strings are intentional default]`

**How to avoid:** This is a **feature, not a bug** — document it in `DATA_CONTRACT.md` ("All money fields in JSON are strings"). Phase 9's `db-write.mjs` (the Node consumer) must `Decimal(s)` parse incoming strings. Phase 1 just establishes the convention via `model_dump_json` test (see Pattern 2 above).

**Warning signs:** Downstream Node code passes a Pydantic-emitted string into an arithmetic expression — it'll either coerce silently (bad) or NaN (worse).

### Pitfall 4: mypy `--strict` doesn't ship type stubs for `numpy-financial` 1.0.0

**What goes wrong:** `from numpy_financial import pmt` produces `error: Skipping analyzing "numpy_financial": module is installed, but missing library stubs or py.typed marker  [import-untyped]` and breaks Phase 3's CI.

**Why it happens:** `numpy-financial==1.0.0` (released 2019-10-18) predates py.typed; the active main branch has stubs but no PyPI release. `[VERIFIED: PyPI shows 1.0.0 as latest as of 2026-04-26]`

**How to avoid:** Add the override in pyproject.toml (already shown in Pattern 4):
```toml
[[tool.mypy.overrides]]
module = "numpy_financial"
ignore_missing_imports = true
```
Phase 1 ships this override even though no Phase 1 code imports the module — Phase 3 will need it and putting it in now keeps the `mypy --strict` gate green.

**Warning signs:** Phase 3's first `mypy` run fails on `numpy_financial` even though the import is otherwise fine.

### Pitfall 5: pre-commit `mypy` hook runs in its own venv and misses pydantic types

**What goes wrong:** Pre-commit's `mirrors-mypy` runs mypy in a *clean* virtualenv that doesn't see project deps. `lib/models.py` validates fine in CI but the pre-commit hook reports `Argument 1 to "Loan" has incompatible type "Decimal"; expected "..."` for every Pydantic model.

**Why it happens:** mypy needs runtime visibility into pydantic to resolve `Annotated[Decimal, Field(...)]`. The hook isolates by default.

**How to avoid:** Use `additional_dependencies:` on the mypy hook (already shown in Pattern 6 above) listing `pydantic` and `python-dateutil`. Update on pydantic version bumps.

**Warning signs:** mypy passes with `uv run mypy --strict .` but fails inside `pre-commit run mypy --all-files`.

### Pitfall 6: GitHub Actions `astral-sh/setup-uv` cache key invalidation

**What goes wrong:** A change to `pyproject.toml` doesn't bust the cache; CI installs stale deps; tests fail mysteriously.

**Why it happens:** `setup-uv@v7` defaults to keying the cache on `uv.lock` only. If you forget to commit `uv.lock` after `uv add`, the cache wins.

**How to avoid:** Always run `uv sync --locked` in CI (the `--locked` flag fails the build if `uv.lock` is out of date). Document in CONTRIBUTING (or README): "always commit `uv.lock` with `pyproject.toml` changes." `[CITED: docs.astral.sh/uv/guides/integration/github/]`

**Warning signs:** CI fails with `error: The lockfile at uv.lock requires a different version`.

### Pitfall 7: pre-commit hook `stages: [pre-commit]` vs `pre-push` confusion

**What goes wrong:** The user-layer-write blocker hook is configured for `stages: [pre-push]`; the user runs `git commit -m "..."` and the user-layer file slips through to the local repo (caught only when they push).

**Why it happens:** pre-commit 4.x renamed stages — `commit` became `pre-commit`, `push` became `pre-push`. Old tutorials use `commit`.

**How to avoid:** Use `stages: [pre-commit]` (already in Pattern 6). Verify locally with `git commit --allow-empty -m "test"` after `pre-commit install`.

**Warning signs:** A test commit with `git add config/household.yml; git commit` succeeds.

### Pitfall 8: `Decimal` field defaults in Pydantic models computed at class-definition time

**What goes wrong:** `extra_principal: Money = Decimal("0.00")` *looks* fine but `Decimal("0.00")` is mutable in some interpretations; sharing one instance across all model instances is technically safe (Decimal is immutable) but linters sometimes flag it.

**Why it happens:** Pydantic v2 handles this correctly via the validation pipeline; older Pydantic v1 patterns of `Field(default_factory=lambda: Decimal("0.00"))` are unnecessary in v2.

**How to avoid:** `extra_principal: Money = Decimal("0.00")` is fine. If ruff flags it (it won't, but just in case), use `Field(default_factory=lambda: Decimal("0.00"))`. Don't worry about this until/unless mypy or ruff complains.

**Warning signs:** None — flagged only as preventive knowledge.

### Pitfall 9: Cross-platform `ROUND_HALF_UP` consistency

**What goes wrong:** Decimal context inheritance behaves differently across threads / asyncio contexts. A test passes locally on macOS but fails on Linux CI because the global `getcontext()` was modified by an unrelated test.

**Why it happens:** `getcontext()` returns thread-local state. Setting it once at module load doesn't propagate everywhere.

**How to avoid:** `lib/money.py.quantize_cents` always uses `with localcontext(MONEY_CONTEXT):` (already shown in Pattern 1). Never modify the global context.

**Warning signs:** Tests pass individually but fail when run as a suite.

### Pitfall 10: `condecimal()` deprecation vs `Annotated[Decimal, Field(...)]`

**What goes wrong:** Pydantic v2 docs show *both* `condecimal()` and the `Annotated` form; some tutorials use the bare callable. ruff's pydantic plugin may warn about the bare form in future versions.

**Why it happens:** `condecimal()` is the legacy v1 API kept for compatibility; the `Annotated` form is the v2-native canonical form. `[CITED: pydantic.dev/docs/validation/latest/api/pydantic/types/]`

**How to avoid:** Use `Annotated[Decimal, Field(strict=True, max_digits=14, decimal_places=2)]` as shown in Pattern 2. This satisfies FND-02 (the requirement says "with `condecimal(max_digits=14, decimal_places=2)`" but the modern `Annotated` form is the equivalent — call this out in `lib/models.py` docstring so the requirement traces).

**Warning signs:** Pydantic deprecation warning in test output.

## Code Examples

All concrete code is in the Patterns section above. Recap of files Phase 1 produces:

| File | Pattern Reference |
|------|------------------|
| `lib/money.py` | Pattern 1 |
| `lib/models.py` | Pattern 2 |
| `tests/fixtures/golden_pmt.json` | Pattern 3 |
| `tests/test_money.py`, `test_models.py`, `test_fixtures.py` | Patterns 1–3 |
| `pyproject.toml` | Pattern 4 |
| `.github/workflows/ci.yml` | Pattern 5 |
| `.pre-commit-config.yaml` | Pattern 6 |
| `scripts/hooks/block-user-layer.py` | Pattern 7 |
| `DATA_CONTRACT.md` | Pattern 8 |
| `.gitignore` | Pattern 9 |

## Files to Create

The planner can use this list directly to enumerate plan tasks. Order is bootstrap-friendly (W1 / W2 / W3 noted alongside).

| Wave | Path | Purpose | FND |
|------|------|---------|-----|
| W1 | `pyproject.toml` | Project metadata + deps + tool config (ruff, mypy, pytest) | 03, 04, 05 |
| W1 | `uv.lock` | Reproducible install | 04 |
| W1 | `.python-version` | Pin to 3.12 (written by `uv init`) | 04 |
| W1 | `lib/__init__.py` | Empty marker; later phases extend | — |
| W1 | `tests/__init__.py` | Empty marker for mypy --strict | 03 |
| W1 | `tests/conftest.py` | Shared fixtures: Decimal context guard, fixture loader | 01 |
| W2 | `lib/money.py` | `to_money`, `quantize_cents`, `MONEY_CONTEXT`, `CENT` | 01 |
| W2 | `lib/models.py` | `Loan`, `Schedule`, `Payment`, `Money`, `Rate` types | 02 |
| W2 | `tests/test_money.py` | Verify Decimal helpers, ROUND_HALF_UP, float-rejection | 01 |
| W2 | `tests/test_models.py` | Verify Pydantic strict mode, JSON-string serialization | 02 |
| W2 | `tests/fixtures/__init__.py` | Empty marker | 03 |
| W2 | `tests/fixtures/golden_pmt.json` | Four pinned monthly P&I oracles | 09 |
| W2 | `tests/test_fixtures.py` | Schema + pinned-value assertions on golden_pmt.json | 09 |
| W3 | `.gitignore` | Block household.yml, profile.yml, *.duckdb, reports/ | 08 |
| W3 | `.github/workflows/ci.yml` | pytest + mypy + ruff on push | 06 |
| W3 | `.pre-commit-config.yaml` | ruff + mypy + block-user-layer hooks | 05, 10 |
| W3 | `scripts/hooks/block-user-layer.py` | Custom local hook | 10 |
| W3 | `DATA_CONTRACT.md` | User/System/Data/Reference layer declaration | 07 |
| W3 | `config/household.example.yml` | Schema skeleton, no real values, committed | 07, 08 |
| W3 | `data/reference/.gitkeep` | Empty seam for Phase 2 | — |
| W3 | `reports/.gitkeep` | Empty seam; reports/*.md gitignored | — |
| W3 | `README.md` | One-paragraph stub: "see .planning/PROJECT.md"; can defer fuller content | — |

**Total files to create: 23** (counting `.gitkeep` files).

> **Files NOT to create in Phase 1** (reserved for later phases):
> - `lib/amortize.py`, `lib/apr.py`, `lib/refinance.py`, `lib/affordability.py`, `lib/arm.py`, `lib/stress.py`, `lib/points.py` — Phases 3–8
> - `lib/rules/*.py` — Phase 2
> - `data/reference/*.yml` — Phase 2 (only the empty `.gitkeep` seam exists in Phase 1)
> - `scripts/amortize.py` etc. — Phase 3+
> - `orchestration/*.mjs` — Phase 9
> - `.claude/skills/mortgage-ops/**` — Phase 10
> - `.claude/agents/*.md` — Phase 11
> - `evals/**` — Phase 12

## Validation Architecture

> Workflow `nyquist_validation: true` is set in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_money.py tests/test_models.py tests/test_fixtures.py -x` |
| Full suite command | `uv run pytest` |
| Phase gate command | `uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest` |

### Phase Requirements → Test Map

Every requirement maps to one or more verifiable assertions. Tests written in Phase 1 are listed; "CI step" / "file presence" / "grep" gates are listed where they substitute for a unit test.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| FND-01 | `to_money("0.065")` round-trips; floats rejected by mypy --strict | unit | `uv run pytest tests/test_money.py::test_to_money_from_string -x` | Wave 2 |
| FND-01 | `quantize_cents(Decimal("0.005")) == Decimal("0.01")` (`ROUND_HALF_UP`, not banker's) | unit | `uv run pytest tests/test_money.py::test_quantize_cents_uses_round_half_up -x` | Wave 2 |
| FND-02 | `Loan(principal=Decimal("400000"), ...)` constructs | unit | `uv run pytest tests/test_models.py::test_loan_accepts_decimal_from_string -x` | Wave 2 |
| FND-02 | `Loan(principal=400000.0, ...)` raises `ValidationError` | unit | `uv run pytest tests/test_models.py::test_loan_rejects_float_principal -x` | Wave 2 |
| FND-02 | `Loan(...).model_dump_json()` emits `"principal":"400000.00"` (string) | unit | `uv run pytest tests/test_models.py::test_loan_serializes_decimal_as_string_in_json -x` | Wave 2 |
| FND-02 | `Loan(principal=Decimal("400000.001"), ...)` raises (max 2 decimal places) | unit | `uv run pytest tests/test_models.py::test_loan_rejects_too_many_decimal_places -x` | Wave 2 |
| FND-03 | `mypy --strict .` returns 0 with no errors | static | `uv run mypy --strict .` (also a CI step) | Wave 1 (config) + Wave 3 (CI) |
| FND-04 | Fresh clone bootstrap: `uv sync --locked && uv run pytest` exits 0 | smoke | manual: clone, run; covered by CI's `uv sync --locked` + `uv run pytest` | Wave 1 |
| FND-04 | `uv.lock` exists and is committed | file presence | `test -f uv.lock` | Wave 1 |
| FND-05 | `ruff check .` and `ruff format --check .` exit 0 | static | `uv run ruff check . && uv run ruff format --check .` (CI + pre-commit) | Wave 1 (config) + Wave 3 (hooks/CI) |
| FND-06 | CI runs lint + format-check + typecheck + test on push | CI step | `.github/workflows/ci.yml` exists; manual verify push triggers it | Wave 3 |
| FND-07 | DATA_CONTRACT.md exists with all four layer sections | file presence + grep | `test -f DATA_CONTRACT.md && grep -q '## User Layer' DATA_CONTRACT.md && grep -q '## System Layer' DATA_CONTRACT.md && grep -q '## Data Layer' DATA_CONTRACT.md && grep -q '## Reference Layer' DATA_CONTRACT.md` | Wave 3 |
| FND-08 | `.gitignore` excludes household.yml, profile.yml, *.duckdb, reports/* | grep | `grep -q '^config/household.yml$' .gitignore && grep -q '^config/profile.yml$' .gitignore && grep -q '\*.duckdb' .gitignore && grep -q '^reports/\*$' .gitignore` | Wave 3 |
| FND-09 | All four golden fixtures present, well-formed, with pinned values | unit | `uv run pytest tests/test_fixtures.py -x` | Wave 2 |
| FND-10 | Pre-commit hook rejects staged changes to `config/household.yml` | smoke | manual: `git add config/household.yml; pre-commit run --files config/household.yml` returns nonzero (also: `uv run python scripts/hooks/block-user-layer.py config/household.yml` exits 1) | Wave 3 |
| FND-10 | Pre-commit hook accepts staged changes to `config/household.example.yml` | smoke | manual: `pre-commit run --files config/household.example.yml` returns zero | Wave 3 |

### Sampling Rate

- **Per task commit (within a wave):** `uv run pytest -x` plus the wave-specific quick check (W1: `uv sync --locked`; W2: full `pytest`; W3: `pre-commit run --all-files`).
- **Per wave merge:** Full phase gate command: `uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest`.
- **Phase gate (before `/gsd-verify-work`):** Full gate command **plus** GitHub Actions green on the latest pushed commit, **plus** a manual smoke test of FND-10 (commit + reject of `config/household.yml`).

### Wave 0 Gaps

This is a greenfield phase — *everything* is a Wave 0 gap. The "Wave 0" tests/infrastructure are themselves the Phase 1 deliverables:

- [ ] `pyproject.toml` `[tool.pytest.ini_options]` config — sets `testpaths = ["tests"]` so pytest runs reliably
- [ ] `tests/__init__.py` + `tests/fixtures/__init__.py` — package markers for `mypy --strict`
- [ ] `tests/conftest.py` — shared `golden_fixture` fixture loader for `test_fixtures.py` (and Phase 3+ tests)
- [ ] `tests/test_money.py` — unit tests for `lib/money.py`
- [ ] `tests/test_models.py` — unit tests for `lib/models.py`
- [ ] `tests/test_fixtures.py` — schema + pinned-value tests for `golden_pmt.json`
- [ ] Framework install: `uv add --dev 'pytest>=9' 'mypy>=1.20' 'ruff>=0.15' 'pre-commit>=4.6'` (Wave 1)
- [ ] `pre-commit install` to wire `.pre-commit-config.yaml` into local git (Wave 3, manual one-time setup; document in README/DATA_CONTRACT.md)

## Security Domain

> `security_enforcement: true` and `security_asvs_level: 1` are set in `.planning/config.json` — this section is required.

### Applicable ASVS Categories

This phase does *no runtime authentication, authorization, session handling, or cryptography*. The narrow ASVS exposure is around input validation (V5) and configuration / data confidentiality (V12 / V14).

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Phase 1 has no auth surface |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No runtime access control; the closest analog (User Layer protection) is enforced via git pre-commit hook + `.gitignore`, not runtime code |
| V5 Input Validation | yes | Pydantic v2 strict-mode validation at every model boundary; `condecimal` rejects out-of-bounds values |
| V6 Cryptography | no | No crypto in Phase 1 |
| V7 Error Handling & Logging | partial | Pydantic emits structured `ValidationError` on bad input; phase 1 does not log; later phases must avoid logging PII (call out in DATA_CONTRACT.md) |
| V8 Data Protection | yes | `.gitignore` + DATA_CONTRACT.md prevent committing PII (`config/household.yml` contains income, applicants, monthly debts) |
| V12 Files & Resources | yes | Pre-commit hook validates staged file paths against the User Layer denylist |
| V14 Configuration | yes | `pyproject.toml` declares deps with version constraints; `uv.lock` enforces reproducible installs (mitigates supply-chain drift) |

### Known Threat Patterns for Python tooling stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Committed PII (income, names, account numbers in `config/household.yml`) | Information Disclosure | `.gitignore` (FND-08) + pre-commit user-layer-write blocker (FND-10) — two-layer defense |
| Unpinned dependency hijack (typo-squatting on PyPI) | Tampering | `uv.lock` pins exact versions and hashes (`uv` records hashes by default); CI uses `uv sync --locked` |
| Float coercion bypass (caller passes float, gets banker's rounding) | Tampering (data integrity) | Pydantic `strict=True` + mypy --strict — caller can't pass float without it surfacing |
| Pre-commit hook bypass via `git commit --no-verify` | Tampering | CI is the second gate — server-side check that the same files weren't introduced (open question: should ci.yml include a `block-user-layer.py` re-run? See Open Questions) |
| Force-add of gitignored file with `git add -f config/household.yml` | Information Disclosure | Pre-commit hook always runs (`always_run: true`) and inspects the full staged set, not just changed files |
| Malicious Decimal input causing memory blowup (e.g. `Decimal("1E1000000")`) | DoS | Pydantic `max_digits=14` caps the size; rejected at validation |

**Phase 1 security verification commands:**

```bash
# 1. Confirm uv.lock pins everything
uv export --format requirements-txt | grep -c '==' >/dev/null && echo OK

# 2. Confirm User Layer blocker rejects household.yml
uv run python scripts/hooks/block-user-layer.py config/household.yml; test $? -eq 1 && echo OK

# 3. Confirm User Layer blocker accepts the example
uv run python scripts/hooks/block-user-layer.py config/household.example.yml; test $? -eq 0 && echo OK

# 4. Confirm Pydantic strict rejects float
uv run python -c "from decimal import Decimal; from lib.models import Loan; \
  import pydantic; \
  try: Loan(principal=400000.0, annual_rate=Decimal('0.065'), term_months=360); raise SystemExit(1) \
  except pydantic.ValidationError: print('OK')"
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.12+ | All Phase 1 code | ✓ (3.14.3 on system) | 3.14.3 — works for `requires-python = ">=3.12"` | none needed |
| git | repo tooling, pre-commit | ✓ | 2.50.1 | none needed |
| gh (GitHub CLI) | optional, for inspecting CI | ✓ | 2.86.0 | use the GitHub web UI |
| uv | dependency mgmt, env | ✗ | — | **First Wave 1 task is `curl -LsSf https://astral.sh/uv/install.sh \| sh` or `pipx install uv`** then `which uv` to verify |
| ruff | lint + format | ✗ (not on PATH) | — | Will be added as a uv dev-dep; runs via `uv run ruff` |
| mypy | typecheck | ✗ (not on PATH) | — | Will be added as a uv dev-dep; runs via `uv run mypy` |
| pytest | tests | ✗ (not on PATH) | — | Will be added as a uv dev-dep; runs via `uv run pytest` |
| pre-commit | local hooks | ✗ (not on PATH) | — | Will be added as a uv dev-dep; runs via `uv run pre-commit install` |

**Missing dependencies with no fallback:**
- **uv** — must be installed *before* `pyproject.toml` exists. The first Wave 1 task should be: install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`), verify (`uv --version`), then run `uv init`. Document this one-time bootstrap in README.

**Missing dependencies with fallback:**
- ruff / mypy / pytest / pre-commit — all installed by `uv sync` from `pyproject.toml` dev-deps; never needed on the system PATH directly. They run via `uv run <tool>`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pip install -r requirements.txt` + manual venv | `uv sync --locked` | uv 1.0 (2024) → standard by 2026 | Lockfile reproducibility; ~10x faster |
| `condecimal(max_digits=..., decimal_places=...)` callable | `Annotated[Decimal, Field(strict=True, max_digits=..., decimal_places=...)]` | Pydantic 2.0 (2023); confirmed canonical in current docs | Better static analysis; more readable in mypy |
| `black` + `isort` + `flake8` separate tools | `ruff` (single binary) | ruff 0.4 (2024); 0.15 today | One config block, ~50x faster on this size repo |
| `setup-python` + `pip install` in CI | `astral-sh/setup-uv@v7` + `uv sync --locked` | setup-uv v6 (2024) → v7 (2025) | Built-in caching; lockfile-aware |
| `pre-commit-hooks/no-commit-to-branch` for path enforcement | Custom local Python hook with `pass_filenames: true` | n/a — no off-the-shelf hook for "block these specific paths" | Cleaner; testable |
| Decimal default rounding (`ROUND_HALF_EVEN`) for consumer money | Explicit `ROUND_HALF_UP` everywhere | always — Python's default is wrong for US consumer finance | Matches lender amort schedules |

**Deprecated/outdated:**
- `condecimal()` callable — works in Pydantic 2.x but the `Annotated[Decimal, Field(...)]` form is canonical and what static analysis tools understand best. FND-02 says "with `condecimal(max_digits=14, decimal_places=2)`" — this is satisfied by the equivalent `Annotated` form; doc the equivalence in `lib/models.py`.
- `pre-commit` stage names `commit` / `push` — replaced by `pre-commit` / `pre-push` in pre-commit 4.x.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The four golden fixture values in FND-09 are correct as stated | Pattern 3, Files to Create | Verified — re-derived in-session with Decimal + ROUND_HALF_UP, all four match. `[VERIFIED: in-session computation]` Risk: zero. |
| A2 | The planner wants `Annotated[Decimal, Field(...)]` form satisfying FND-02's "condecimal" wording | Pattern 2 | LOW — FND-02 wording is descriptive of *behavior*, not exact API syntax; either form satisfies. Document the equivalence in `lib/models.py` to be safe. |
| A3 | Phase 1 should commit `config/household.example.yml` (a redacted skeleton) | Files to Create, DATA_CONTRACT.md | LOW — AFFD-09 explicitly mentions this file in Phase 4. Phase 1 committing a stub keeps the seam open and lets DATA_CONTRACT.md cite it; Phase 4 fleshes out the schema. |
| A4 | `uv` is the right Python toolchain (vs poetry, hatch, rye) | Stack section | Verified — `.planning/research/STACK.md` decision, repeated in CLAUDE.md. `[VERIFIED: project conventions]` |
| A5 | Pre-commit hook is the right enforcement mechanism for FND-10 (vs server-side hook, vs CI gate, vs trust) | Pattern 7, Open Questions | MEDIUM — pre-commit can be bypassed with `--no-verify`. CI server-side gate would be belt-and-suspenders; flagged as open question. |
| A6 | Phase 1 should NOT create stub Python files for Phase 2+ modules | Files to Create, Anti-Patterns | LOW — keeping `lib/__init__.py` empty avoids exporting unfinished APIs; mypy --strict on empty modules is trivially green. |
| A7 | `numpy-financial==1.0.0` (only release since 2019) is acceptable as a Phase 3+ runtime dep, even though it ships no type stubs | Pitfalls #4 | LOW — STACK.md confirms; the mypy override is the standard fix. `[VERIFIED: PyPI 2026-04-26]` |
| A8 | `python-dateutil` should be in `[project.dependencies]` even though Phase 1 doesn't import it | Stack section | LOW — stabilizes the lockfile; Phase 3 will use it. Adds ~250KB to install. Could move to Phase 3 if planner prefers tighter Phase 1 scope. |
| A9 | The `block-user-layer.py` hook should NOT also block `data/*.duckdb` — those are gitignored | Pattern 7 | LOW — current implementation blocks both via belt-and-suspenders for `git add -f`. No risk in over-blocking. |
| A10 | README.md is in scope for Phase 1 (even as a stub) | Files to Create | LOW — a one-line README that points to `.planning/PROJECT.md` is enough; the requirement doesn't mandate it but a public repo without README is rough. Planner can drop if scope-tight. |

## Open Questions

1. **Should the user-layer-write blocker also run server-side in CI?**
   - What we know: pre-commit can be bypassed with `git commit --no-verify`. CI is a backstop.
   - What's unclear: whether the planner wants belt-and-suspenders here. The hook is 30 lines of Python and trivially re-runnable from `ci.yml`; the cost is near-zero.
   - Recommendation: **YES — add a CI step `uv run python scripts/hooks/block-user-layer.py $(git diff --name-only origin/main...HEAD)` or similar.** It's near-free and closes the bypass. If planner disagrees, document the risk in DATA_CONTRACT.md.

2. **Should `python-dateutil` be a Phase 1 runtime dep or deferred to Phase 3?**
   - What we know: Phase 1 doesn't import it; Phase 3 (AMRT-03) requires it for `relativedelta(weeks=2)`.
   - What's unclear: Whether the planner prefers minimum-deps Phase 1 or stable-lockfile-from-day-one.
   - Recommendation: **Include in Phase 1.** Lockfile churn is a phase-transition pain; better to commit it now.

3. **Should the README.md exist in Phase 1?**
   - What we know: `.planning/PROJECT.md` covers project description; CLAUDE.md covers conventions.
   - What's unclear: Whether a public-facing README is in scope.
   - Recommendation: **One-paragraph stub** — "mortgage-ops: personal-use mortgage analysis. See `.planning/PROJECT.md`. Quick start: `uv sync && uv run pytest`."

4. **Should we write a CONTRIBUTING.md or DEVELOPMENT.md describing the `uv` workflow?**
   - What we know: A new developer cloning the repo needs to know to install uv and run `uv run pre-commit install` once.
   - What's unclear: Whether the planner wants this documented now or deferred.
   - Recommendation: **Defer.** Stub instructions in README.md are sufficient until a second developer joins (which won't happen for this personal project per PROJECT.md).

5. **Should `lib/__init__.py` declare `__version__ = "0.1.0"` or be truly empty?**
   - What we know: pyproject.toml has `version = "0.1.0"`; some projects mirror this in `__init__.py`.
   - What's unclear: Personal preference / convention.
   - Recommendation: **Truly empty.** Phase 12 can add `__version__` if FRED rate-attribution wants to log a version string.

6. **Should the GitHub Actions workflow run on a matrix of Python versions (3.12, 3.13, 3.14) or pin to 3.12?**
   - What we know: System Python is 3.14.3; `pyproject.toml` says `requires-python = ">=3.12"`.
   - What's unclear: Whether a single user wants matrix testing.
   - Recommendation: **Single 3.12 only.** This is a personal-use tool; matrix testing adds CI minutes for negligible benefit. Document that local dev on 3.13/3.14 should also work.

## Out of Scope (deferred to later phases)

Phase 1 explicitly does NOT do these — they belong elsewhere. Phase 1 must, however, leave clean seams.

| Deferred | Reason | Phase 1 seam |
|----------|--------|---------------|
| Amortization math (PMT/IPMT/PPMT, schedules, biweekly, extra principal) | Phase 3 (AMRT-01..08) | `lib/__init__.py` empty; `numpy-financial` already in `[dependencies]`; mypy override for it already in pyproject.toml |
| Regulatory rules predicates (FHA MIP, VA funding fee, etc.) | Phase 2 (REF-01..09, RUL-01..13) | `data/reference/.gitkeep` empty seam; DATA_CONTRACT.md declares Reference Layer |
| Reference YAML files (FHFA limits, FHA MIP, VA funding fee, IRS Pub 936, etc.) | Phase 2 (REF-01..07) | `data/reference/` directory exists; Phase 2 only adds files |
| DuckDB schema, lockfile pattern, db-write.mjs | Phase 9 (PERS-01..07) | `.gitignore` already excludes `data/*.duckdb`; `data/` directory exists |
| Claude skill bundle (`SKILL.md`, modes/, references/, scripts/) | Phase 10 (SKLL-01..13) | None needed in Phase 1 — `.claude/skills/mortgage-ops/` simply doesn't exist yet |
| Subagents (`amortization-agent.md`, `refi-npv-agent.md`, `stress-test-agent.md`) | Phase 11 (SUBA-01..06) | None |
| FRED MCP integration + eval harness | Phase 12 (LIVE-01..04, EVAL-01..04) | None |
| Affordability ratios, ARM modeling, refi NPV, APR Newton-Raphson, stress sweeps, points breakeven | Phases 4–8 | `lib/__init__.py` empty; module files don't exist |
| Markdown reports, scenario persistence | Phase 9, Phase 10 | `reports/` dir with `.gitkeep`; `.gitignore` excludes `reports/*` (allowing `.gitkeep`) |
| Annual regulatory data refresh script (Playwright) | v2 (out of scope per REQUIREMENTS.md) | none |
| LE/CD PDF parsing | v2 (PARSE-01) | none |
| User-facing CLI scripts (`scripts/amortize.py`, etc.) | Phase 3+ | `scripts/hooks/block-user-layer.py` is the only `scripts/*.py` in Phase 1; the directory is created with one tooling helper |

**Crucial invariant:** Phase 1's `lib/__init__.py` exports *nothing*. Every later phase adds its module + its public API; Phase 1 must not pre-declare empty stubs. This keeps the dependency graph honest.

## Sources

### Primary (HIGH confidence)
- `/Users/cujo253/Documents/mortgage-ops/CLAUDE.md` — non-negotiable money discipline + calc/LLM separation
- `/Users/cujo253/Documents/mortgage-ops/.planning/PROJECT.md` — project context, constraints, key decisions
- `/Users/cujo253/Documents/mortgage-ops/.planning/REQUIREMENTS.md` — FND-01..10 verbatim
- `/Users/cujo253/Documents/mortgage-ops/.planning/research/STACK.md` — verified stack + version compatibility
- `/Users/cujo253/Documents/mortgage-ops/.planning/research/PITFALLS.md` — Pitfall #1 (float drift), #10 (User Layer)
- `/Users/cujo253/Documents/mortgage-ops/.planning/research/ARCHITECTURE.md` — three-layer architecture, project structure
- `/Users/cujo253/Documents/career-ops/DATA_CONTRACT.md` — proven sibling-repo Data Contract pattern (lifted + adapted)
- PyPI JSON API queried 2026-04-26 — pydantic 2.13.3, ruff 0.15.12, mypy 1.20.2, uv 0.11.7, pytest 9.0.3, pre-commit 4.6.0, python-dateutil 2.9.0, numpy-financial 1.0.0
- https://docs.astral.sh/uv/guides/integration/github/ — `astral-sh/setup-uv@v7`, `uv sync --locked`, `enable-cache: true`
- https://pydantic.dev/docs/validation/latest/api/pydantic/types/ — `condecimal` signature, `Annotated[Decimal, Field(...)]` canonical form
- https://github.com/pydantic/pydantic/issues/7457 — confirms Decimal JSON-string serialization is intentional default
- In-session Python verification — re-derived all four FND-09 golden values with `Decimal` + `ROUND_HALF_UP` formula

### Secondary (MEDIUM confidence)
- https://docs.pydantic.dev/latest/concepts/serialization/ — `model_dump_json` vs `model_dump` mode behavior
- https://pre-commit.com/#confining-hooks-to-run-at-certain-stages — `pre-commit` / `pre-push` stage names

### Tertiary (LOW confidence)
- *(none — every load-bearing claim verified)*

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package version queried live from PyPI; uv/setup-uv documentation read directly; STACK.md cross-references confirmed.
- Architecture: HIGH — three-layer pattern is repeated across `.planning/research/ARCHITECTURE.md`, `CLAUDE.md`, and `career-ops/DATA_CONTRACT.md`. Phase 1 is mostly project-scaffolding territory with no architectural ambiguity.
- Pitfalls: HIGH — Decimal/Pydantic/uv/pre-commit pitfalls all sourced from authoritative docs or directly verified in this session.
- Validation Architecture: HIGH — every requirement maps to a concrete pytest invocation, file-presence check, or grep.
- Security: HIGH — Phase 1 has narrow security exposure; the User Layer + supply-chain (uv.lock) controls are clearly identified.
- Files to Create: HIGH — exhaustive list, ordered by wave, each item traced to a requirement ID.

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (30 days; Pydantic / ruff / uv release cadence makes minor-version updates likely within a month — re-verify versions if planning slips past late May 2026)

## RESEARCH COMPLETE

**Phase:** 1 — Foundations & Money Discipline
**Confidence:** HIGH

### Files to create: 23

| Wave | Count | Files |
|------|------:|-------|
| Wave 1 (project skeleton) | 5 | `pyproject.toml`, `uv.lock`, `.python-version`, `lib/__init__.py`, `tests/__init__.py` |
| Wave 1.5 (test harness) | 1 | `tests/conftest.py` |
| Wave 2 (money discipline + models + fixtures) | 7 | `lib/money.py`, `lib/models.py`, `tests/test_money.py`, `tests/test_models.py`, `tests/fixtures/__init__.py`, `tests/fixtures/golden_pmt.json`, `tests/test_fixtures.py` |
| Wave 3 (CI / hooks / data contract / .gitignore / seams) | 10 | `.gitignore`, `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `scripts/hooks/block-user-layer.py`, `DATA_CONTRACT.md`, `config/household.example.yml`, `data/reference/.gitkeep`, `reports/.gitkeep`, `README.md`, *(`scripts/__init__.py` if mypy --strict requires it on a directory containing the hook — confirm during planning; lean YES)* |

### FND-01..FND-10 coverage map

| Req | Primary deliverable | Verified by |
|-----|---------------------|-------------|
| FND-01 | `lib/money.py` (Decimal helpers, ROUND_HALF_UP, MONEY_CONTEXT) | `tests/test_money.py` |
| FND-02 | `lib/models.py` (Loan/Schedule/Payment, Money/Rate types, strict mode) | `tests/test_models.py` |
| FND-03 | `[tool.mypy] strict = true` in `pyproject.toml` + CI step + pre-commit hook | `uv run mypy --strict .` in CI |
| FND-04 | `pyproject.toml` + `uv.lock` + `.python-version` | `uv sync --locked` in CI; presence checks |
| FND-05 | `[tool.ruff]` in `pyproject.toml` + pre-commit hooks (`ruff` + `ruff-format`) + CI steps | `uv run ruff check .` and `uv run ruff format --check .` in CI |
| FND-06 | `.github/workflows/ci.yml` running ruff + ruff-format + mypy + pytest | green CI run on push |
| FND-07 | `DATA_CONTRACT.md` declaring User/System/Data/Reference layers | grep + manual review |
| FND-08 | `.gitignore` patterns for household.yml, profile.yml, *.duckdb, reports/* | grep |
| FND-09 | `tests/fixtures/golden_pmt.json` + `tests/test_fixtures.py` | `uv run pytest tests/test_fixtures.py` (4 oracles, all values pinned & verified in-session) |
| FND-10 | `scripts/hooks/block-user-layer.py` + entry in `.pre-commit-config.yaml` | manual smoke test (commit `config/household.yml` is rejected; commit `config/household.example.yml` is accepted) |

All 10 FND requirements have a primary deliverable, an automated or smoke-test verification, and a wave assignment. Planner can proceed.
