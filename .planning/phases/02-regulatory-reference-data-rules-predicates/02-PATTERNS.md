# Phase 2: Regulatory Reference Data & Rules Predicates — Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** ~24 new files (+ 2 modifications to existing config) — see File Classification table
**Analogs found:** 11 strong in-repo analogs / 24 new files. Remaining 13 are "ESTABLISHES PATTERN" — Phase 2 is the first to build a YAML loader, a citation-coverage meta-test, the predicate template, and the reference-YAML format. These rely on the canonical patterns quoted in `02-RESEARCH.md` Patterns 1–5, not on existing code.

> **Pattern lineage.** Phase 1 is in. Every Phase 2 file inherits at least one of:
>   - **Decimal discipline** from `lib/money.py` (string-only construction, `quantize_cents` + `localcontext(MONEY_CONTEXT)`, ROUND_HALF_UP).
>   - **Pydantic v2 boundary discipline** from `lib/models.py` (`Annotated[Decimal, Field(strict=True, ...)]`, `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`, `Money`/`Rate` aliases).
>   - **Test discipline** from `tests/test_money.py` and `tests/test_models.py` (module docstring listing coverage, exact `==` for Decimal, hand-calc citation comment in every assertion, `with pytest.raises(...)` for fail-loud cases).
>   - **Fixture-loader discipline** from `tests/conftest.py` (parameterized JSON loader returning a single fixture by `id`).
>   - **Filesystem-introspection meta-test discipline** from `tests/test_block_user_layer.py` (load a sibling-tree script as a module via `importlib.util.spec_from_file_location`, then parametrize over its decisions). The Phase-2 citation-coverage test reuses *exactly this technique* against `lib/rules/*.py`.

---

## File Classification

| Plan/Wave | New or Modified File | Role | Data Flow | Closest In-Repo Analog | Match Quality |
|-----------|----------------------|------|-----------|------------------------|----------------|
| W0 | `pyproject.toml` (modify — add `pyyaml>=6.0.2`) | config (build) | build-time | `pyproject.toml` (existing `[project.dependencies]` block lines 6–10) | exact |
| W0 | `.pre-commit-config.yaml` (optionally modify — add `check-yaml`) | config (hook) | build-time | `.pre-commit-config.yaml` (existing `repos:` block, `local` hook idiom) | exact |
| W0 | `lib/rules/__init__.py` (new, empty marker) | source (package marker) | library | `lib/__init__.py` (empty), `scripts/hooks/__init__.py` (empty) | exact |
| W0 | `tests/test_reference/__init__.py` (new) | test (package marker) | test-only | `tests/__init__.py` (empty), `tests/fixtures/__init__.py` (empty) | exact |
| W0 | `tests/test_rules/__init__.py` (new) | test (package marker) | test-only | same as above | exact |
| W0 | `tests/fixtures/rules/__init__.py` (new) | test (package marker) | test-only | `tests/fixtures/__init__.py` | exact |
| W0 | `lib/rules/_loader.py` (new) | source (loader + cache + warning) | library, lazy-load + cache | NONE in-repo (no module owns a singleton/cache yet) | **ESTABLISHES PATTERN** — see Pattern Block 1 |
| W0 | `lib/rules/types.py` (new) | source (Pydantic v2 type defs) | library | `lib/models.py` lines 22–45 (Money/Rate + frozen BaseModel) | exact (replays Phase-1 model template) |
| W0 | `tests/test_rules/test_loader.py` (new — REF-08) | test (warns + tmp_path) | test-only | `tests/test_block_user_layer.py` (parametrize + monkey-importable module + capsys-shaped assertions) | role-match |
| W0 | `tests/test_reference/test_schema.py` (new — REF-09) | test (filesystem meta) | test-only | `tests/test_block_user_layer.py` lines 36–98 (parametrize idiom over filesystem-derived list); `tests/test_fixtures.py` lines 61–72 (parametrize over JSON-loaded data) | role-match |
| W0 | `tests/test_rules/test_citation_coverage.py` (new — RUL-12 + RUL-13) | test (filesystem meta) | test-only | `tests/test_block_user_layer.py` (importlib-load + parametrize); `tests/test_fixtures.py` (parametrize over discovered fixtures) | role-match — **ESTABLISHES** the lib/rules-introspection convention |
| W1+ | `lib/rules/loan_type.py` (new — RUL-01) | source (predicate, 1 file per citation) | library, request-response | `lib/money.py` (single-purpose docstring + pure functions); `lib/models.py` (Pydantic-typed boundary) | role-match — **ESTABLISHES PREDICATE TEMPLATE** (see Pattern Block 3) |
| W1+ | `lib/rules/fannie_eligibility.py` (RUL-02) | source (predicate) | library, request-response | same template (after 02-01) | template replay |
| W1+ | `lib/rules/freddie_eligibility.py` (RUL-03) | source (predicate) | library, request-response | same template | template replay |
| W1+ | `lib/rules/fha_mip.py` (RUL-04) | source (predicate) | library, request-response | same template | template replay |
| W1+ | `lib/rules/conventional_pmi.py` (RUL-05) | source (predicate) | library, request-response | same template (RESEARCH.md Pattern 3 quotes this file as the worked example) | template replay |
| W1+ | `lib/rules/va_funding_fee.py` (RUL-06) | source (predicate) | library, request-response | same template | template replay |
| W1+ | `lib/rules/va_residual_income.py` (RUL-07) | source (predicate) | library, request-response | same template | template replay |
| W1+ | `lib/rules/usda.py` (RUL-08) | source (predicate) | library, request-response | same template | template replay |
| W1+ | `lib/rules/atr_qm.py` (RUL-09) | source (predicate) | library, request-response | same template | template replay |
| W1+ | `lib/rules/reg_z.py` (RUL-10) | source (predicate, no YAML — pure constants) | library, request-response | same template | template replay |
| W1+ | `lib/rules/irs_pub936.py` (RUL-11) | source (predicate) | library, request-response | same template | template replay |
| W1+ | `data/reference/conforming-limits-2026.yml` (REF-01) | reference (YAML data) | startup-load + cache | NONE — `data/reference/.gitkeep` only | **ESTABLISHES YAML FORMAT** (see Pattern Block 4) |
| W1+ | `data/reference/fha-limits-2026.yml` (REF-02) | reference (YAML data) | startup-load + cache | first YAML once 02-01 lands | template replay |
| W1+ | `data/reference/fha-mip-rates.yml` (REF-03) | reference (YAML data, table) | startup-load + cache | first YAML once 02-01 lands | template replay |
| W1+ | `data/reference/va-funding-fees.yml` (REF-04) | reference (YAML data, table) | startup-load + cache | first YAML once 02-01 lands | template replay |
| W1+ | `data/reference/va-residual-income.yml` (REF-05) | reference (YAML data, 3-D table) | startup-load + cache | first YAML once 02-01 lands | template replay |
| W1+ | `data/reference/usda-income-limits.yml` (REF-06) | reference (YAML data) | startup-load + cache | first YAML once 02-01 lands | template replay |
| W1+ | `data/reference/irs-pub936.yml` (REF-07) | reference (YAML data) | startup-load + cache | first YAML once 02-01 lands | template replay |
| W1+ | `tests/test_rules/test_loan_type.py` (and 10 sibling test files) | test (per-predicate) | test-only | `tests/test_money.py`, `tests/test_models.py` (module docstring + hand-calc-with-citation per assertion + exact `==`) | exact |
| W1+ | `tests/fixtures/rules/loan_type_*.json` (and per-predicate fixtures) | fixture (JSON, hand-calc) | test-only | `tests/fixtures/golden_pmt.json` (single-file form, but field set extends with `citation` and `comment`) | exact form, **adds `citation`/`source_url`/`comment` fields** |

**Total: 24 new files + 2 modifications. In-repo strong analogs: 11. ESTABLISHES PATTERN: 4 (loader, predicate template, YAML format, citation-coverage meta-test).**

---

## Pattern Assignments

For each new file, the analog (or "ESTABLISHES" tag) plus a verbatim 5–25 line excerpt the executor must mirror, plus the convention to carry forward.

---

### `lib/rules/_loader.py` (source, library, lazy-load + lru_cache + warning) — **ESTABLISHES PATTERN**

**Closest analog:** **None in-repo.** The closest "module that owns a singleton + cache" idiom is the way `lib/money.py` exports module-level constants (`CENT`, `MONEY_CONTEXT`) at lines 20–26, but that is plain constants — no caching, no first-load warning. Phase 2 establishes the singleton+lru_cache+warnings.warn idiom for the rest of the project (Phase 9 DuckDB connection pool, Phase 12 FRED cache will both follow it).

**Excerpt to follow verbatim** — `02-RESEARCH.md` Pattern 2 (lines 308–381). The decisive shape:

```python
# lib/rules/_loader.py
@lru_cache(maxsize=None)
def load_reference(name: str) -> dict[str, Any]:
    path = REFERENCE_DIR / f"{name}.yml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text())
    if "source" not in raw:
        raise MissingReferenceFieldError(f"{name}.yml missing required `source:` field")
    if "effective" not in raw:
        raise MissingReferenceFieldError(f"{name}.yml missing required `effective:` field")
    _check_staleness(name, raw["effective"])
    return raw

def _check_staleness(name: str, effective: date) -> None:
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

**Import-block pattern to mirror — quoted verbatim from `lib/money.py` lines 14–18 (the project-wide `from __future__ import annotations` + Final-typed module constants idiom):**

```python
from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Final

CENT: Final[Decimal] = Decimal("0.01")
"""The quantum for end-of-period money rounding."""

MONEY_CONTEXT: Final[Context] = Context(prec=28, rounding=ROUND_HALF_UP)
```

**Conventions established (load-bearing for the rest of Phase 2 and beyond):**
- `from __future__ import annotations` is mandatory per project convention (every Phase 1 source/test file uses it).
- Module constants are `Final[...]`-typed at module scope.
- The loader **never mutates** Python's global state (mirrors the `lib/money.py` `localcontext(MONEY_CONTEXT)` discipline at lines 39–46).
- Warnings use `warnings.warn(..., category=StaleReferenceWarning, stacklevel=2)` — never `print` to stderr, never `logging.warning`. `stacklevel=2` is required so callers see the warning at *their* call site, not inside `_check_staleness`.
- `MissingReferenceFieldError(KeyError)` and `StaleReferenceWarning(UserWarning)` are subclassed from stdlib so consumers can use `pytest.raises(KeyError)` / `pytest.warns(UserWarning)` even without importing the project-specific types.
- `lru_cache(maxsize=None)` (no eviction) — process-lifetime cache; tests call `load_reference.cache_clear()` in fixtures.

---

### `lib/rules/types.py` (source, library, Pydantic v2 type defs)

**Closest analog:** `lib/models.py` lines 22–45 — verbatim template for `Annotated[Decimal, Field(strict=True, ...)]` aliases plus `ConfigDict(strict=True, frozen=True, extra="forbid")` BaseModels.

**Excerpt to mirror — `lib/models.py` lines 14–45 (verbatim):**

```python
from __future__ import annotations

from datetime import date  # noqa: TC003  # Pydantic resolves annotations at runtime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# Public type aliases — Phase 4+ models import these.
Money = Annotated[
    Decimal,
    Field(strict=True, max_digits=14, decimal_places=2, ge=Decimal("0")),
]
"""Non-negative money: up to 12 integer digits + 2 decimal places."""

Rate = Annotated[
    Decimal,
    Field(strict=True, max_digits=7, decimal_places=6, ge=Decimal("0"), le=Decimal("1")),
]
"""A fractional rate in [0, 1] with up to 6 decimal places (e.g. 0.065000 = 6.5%)."""


class Loan(BaseModel):
    """Inputs to an amortization. Phase 3 will use this; Phase 1 just defines it."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    principal: Money
    annual_rate: Rate
    term_months: int = Field(ge=1, le=600)
    origination_date: date | None = None
    loan_type: Literal["fixed", "arm", "fha", "va", "usda", "jumbo"] = "fixed"
```

**Conventions to carry forward into `lib/rules/types.py`:**
- **DO NOT redefine `Money` or `Rate`.** Import them from `lib.models` (`from lib.models import Money, Rate`). Phase 1 froze that surface.
- Every new BaseModel (`County`, `Borrower`, `Property`) gets the SAME `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` — exact line match, not paraphrased.
- Use `Literal[...]` for closed enums (`LoanType`, `Region`); never `str` Enum subclass — Phase 1 set the precedent (`loan_type` Literal at `lib/models.py:45`).
- Add the `# noqa: TC003` on `from datetime import date` so the same ruff `TCH` rule that fires on `lib/models.py:16` does not fire here either.
- The new types are intentionally placed in `lib/rules/types.py` (NOT `lib/models.py`) so the Phase-1-frozen contract surface stays untouched — see Phase 1 PATTERNS § "Conventions to Establish" #2.

---

### `lib/rules/loan_type.py` (and the 10 sibling predicate files) — **ESTABLISHES PREDICATE TEMPLATE**

**Closest analog:** `lib/money.py` (single docstring + pure functions + Decimal arithmetic + exhaustive citation comments) and `lib/models.py` (typed boundary). RESEARCH.md Pattern 3 (lines 386–445) quotes `conventional_pmi.py` as the canonical worked example — the planner should treat that block as the predicate template.

**Excerpt 1 — `lib/money.py` lines 1–46 (verbatim) — for docstring + Decimal-discipline + module-shape:**

```python
"""Money discipline helpers.

Every Decimal in this project is constructed from strings, quantized end-of-period
with ROUND_HALF_UP, and never mixed with float in the same expression.

This module is the single source of truth for project-wide Decimal discipline (FND-01).
Every other module imports `to_money`, `quantize_cents`, `CENT`, and/or `MONEY_CONTEXT`
from here; nobody constructs `Decimal` from a literal in scattered places.

Why ROUND_HALF_UP instead of Python's default ROUND_HALF_EVEN (banker's rounding)?
Banker's rounding is correct for accounting averages but wrong for US consumer mortgage
math; lender amortization schedules use ROUND_HALF_UP. See pitfall 2 in 01-RESEARCH.md.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Final

CENT: Final[Decimal] = Decimal("0.01")
"""The quantum for end-of-period money rounding."""

MONEY_CONTEXT: Final[Context] = Context(prec=28, rounding=ROUND_HALF_UP)
"""Project-wide Decimal context. ..."""


def to_money(value: str) -> Decimal:
    """Construct a money Decimal from a string. ..."""
    return Decimal(value)


def quantize_cents(value: Decimal) -> Decimal:
    """Round a Decimal to two places using ROUND_HALF_UP.

    Call ONCE at end-of-period; never mid-calculation. Uses `localcontext` so the
    global Decimal context is not mutated (pitfall 9).
    """
    with localcontext(MONEY_CONTEXT):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
```

**Excerpt 2 — `02-RESEARCH.md` Pattern 3 lines 386–444 (verbatim, the canonical predicate header):**

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
    """Return PMI termination status per HPA 12 USC §4902."""
    ltv = scheduled_balance / original_property_value
    if ltv <= Decimal("0.78"):
        return "auto_terminated"
    if ltv <= Decimal("0.80"):
        return "request_eligible"
    return "in_force"
```

**Conventions to carry forward (REQUIRED in every `lib/rules/*.py`):**
- Module docstring **must** contain the four header strings the citation-coverage test scans for: `Citation:`, `Source URL:`, `Effective:`, plus an `http(s)://` URL anywhere in the docstring (RESEARCH.md lines 547–559; 02-RESEARCH.md Pattern 5).
- Imports always start with `from __future__ import annotations`.
- Money values: `Decimal("0.78")` constructed from a string literal — never `Decimal(0.78)`. (Same rule as `lib/money.py` docstring lines 11–12.)
- Money returns from any predicate that produces dollars (e.g., `va_funding_fee`, `fha_mip` UFMIP, `usda` guarantee fees) end in **exactly one** call to `quantize_cents(...)` (RESEARCH.md "Project Constraints" line 57; same rule as `lib/money.py:39`).
- Predicate accepts Phase-1 `Loan` plus `Decimal` scalars (or Phase-2 Pydantic types from `lib/rules/types.py`); returns `bool` / `Literal[...]` / `Decimal` / a `frozen=True` BaseModel — no raw dicts cross the boundary.
- One predicate per file. **Do not import from another `lib/rules/*.py`** (RESEARCH.md "Anti-Patterns" lines 575–576).
- For predicates that look up reference data: `from lib.rules._loader import load_reference` then `load_reference("conforming-limits-2026")`.

---

### `data/reference/*.yml` (7 new files) — **ESTABLISHES YAML FORMAT**

**Closest analog:** **None.** `data/reference/` currently contains only an empty `.gitkeep` (Phase 1 created the directory as a seam). Phase 2 establishes the YAML schema for the project.

**Excerpt to follow verbatim — `02-RESEARCH.md` Pattern 1 lines 270–297:**

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
    - state_fips: "06"
      county_fips: "075"
      county_name: "San Francisco"
      one_unit: "1249125"
```

**Conventions established (load-bearing for REF-01..07 plus future v2 reference YAMLs):**
- **Top-level keys (mandatory):** `source:` (URL string, validated by REF-09 schema test), `effective:` (ISO-8601 zero-padded date — PyYAML auto-parses to `datetime.date`), `notes:` (regulator description, link-rot insurance per RESEARCH.md Pitfall 8 line 1090).
- **Quote every numeric scalar** (`"832750"`, `"0.0055"`, `"0.0175"`) so PyYAML emits `str` not `int`/`float`. The loader does `Decimal(str_value)` at consumption time. Unquoted `0.0085` parses as `float(0.008500000000000001)` and silently violates money discipline (RESEARCH.md Pitfall 1, lines 1050–1054).
- **Date is unquoted** — `effective: 2026-01-01` — so PyYAML emits `datetime.date`. The schema test (REF-09) asserts `isinstance(raw["effective"], date)` to catch any quote-the-date regression (RESEARCH.md Pitfall 2 lines 1056–1058; pattern from `tests/test_fixtures.py:71`).
- **Inline citation comments** next to non-obvious table rows: `# Source: HUD ML 2023-05 Table A` — same idiom as the `notes` field on `tests/fixtures/golden_pmt.json` lines 12, 22, 32, 42.
- **High-cost-county subset, not full list** — RESEARCH.md Pitfall 10 (lines 1097–1100) mandates partial ingestion + `MissingCountyDataError` for unlisted counties.

---

### `tests/test_rules/test_loan_type.py` (and 10 sibling per-predicate test modules)

**Closest analog:** `tests/test_money.py` lines 1–69 and `tests/test_models.py` lines 1–158 — the canonical Phase-1 test shape.

**Excerpt to mirror — `tests/test_money.py` lines 1–46 (verbatim):**

```python
"""Tests for lib/money.py — Decimal discipline (FND-01).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - to_money: string-only construction
  - quantize_cents: ROUND_HALF_UP (not banker's ROUND_HALF_EVEN)
  - MONEY_CONTEXT: prec=28, rounding=ROUND_HALF_UP
  - localcontext discipline: global getcontext() unchanged after roundtrip
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext

from lib.money import CENT, MONEY_CONTEXT, quantize_cents, to_money


def test_to_money_from_string_round_trips() -> None:
    # Hand: Decimal("0.065") preserves the exact string form; no float drift.
    assert to_money("0.065") == Decimal("0.065")


def test_quantize_cents_uses_round_half_up_at_0p005() -> None:
    # Hand: ROUND_HALF_UP(0.005, 2) == 0.01.
    # ROUND_HALF_EVEN (Python's default; banker's rounding) would return 0.00.
    # This is the load-bearing assertion for FND-01: prove we are NOT using banker's.
    assert quantize_cents(Decimal("0.005")) == Decimal("0.01")
```

**Excerpt for fail-loud-input pattern — `tests/test_models.py` lines 37–48 (verbatim):**

```python
def test_loan_rejects_float_principal() -> None:
    # Strict=True must reject floats — load-bearing assertion for FND-01 + FND-02.
    # The `# type: ignore[arg-type]` on the call below documents that mypy --strict
    # would catch this at compile time; the runtime test verifies Pydantic catches it too.
    with pytest.raises(ValidationError) as exc:
        Loan(principal=400000.0, annual_rate=Decimal("0.065000"), term_months=360)  # type: ignore[arg-type]
    assert "decimal_type" in str(exc.value) or "Input should be" in str(exc.value)
```

**Conventions to carry forward into every `tests/test_rules/test_*.py`:**
- Module docstring must list (a) the citation under test (mirrors the predicate's `Citation:` header — RESEARCH.md "Per-predicate test discipline" line 980), (b) the phrase "Every assertion includes the hand-calculated expected value and why" (verbatim from `tests/test_money.py:3` — Phase 1 PATTERNS established this).
- Every assertion line carries a `# Hand: ...` comment with the regulator-source derivation (mirror of `tests/test_money.py:30-34`).
- Decimal equality is **exact** — `assert result == Decimal("1264.14")` — never `pytest.approx` (project rule, `lib/money.py` docstring + CLAUDE.md "Testing").
- Fail-loud assertions use `with pytest.raises(MissingCountyDataError):` (mirror of `tests/test_models.py:41`).
- `# type: ignore[...]` is permitted ONLY on negative-test calls that prove mypy --strict would reject the same thing; same comment-block discipline as `tests/test_models.py:42`.
- Per-fixture parametrization preferred over per-fixture function bodies — pattern lifted from `tests/test_block_user_layer.py:36-43` and `tests/test_fixtures.py:61-66`:

```python
@pytest.mark.parametrize(
    "path",
    [
        "config/household.yml",
        "config/profile.yml",
        "modes/_profile.md",
    ],
)
def test_user_layer_pattern_paths_are_blocked(path: str) -> None:
    assert is_user_layer(path) is True
```

- Phase-2 per-predicate tests should load fixtures with a small private helper (`_load(name)`) per RESEARCH.md Pattern 4 lines 473–477 — or extend `tests/conftest.py` with a `rules_fixture` companion to `golden_fixture`. (Plan 02-01 should decide and document; the rest follow.)

---

### `tests/test_rules/test_citation_coverage.py` (new — RUL-12 + RUL-13 meta-test) — **ESTABLISHES PATTERN**

**Closest analog:** `tests/test_block_user_layer.py` lines 1–34 and `tests/test_fixtures.py` lines 61–72 — the project's existing two patterns for "parametrize over a discovered list and assert structural invariants on each item." Phase 2 combines them into a filesystem-introspecting predicate audit.

**Excerpt 1 — `tests/test_block_user_layer.py` lines 14–34 (verbatim) — for the importlib-load-script-by-path idiom:**

```python
import importlib.util
import sys
from pathlib import Path

import pytest

# Load the hook script as a module despite the kebab-case filename.
_HOOK_PATH = Path(__file__).resolve().parent.parent / "scripts" / "hooks" / "block-user-layer.py"
_spec = importlib.util.spec_from_file_location("_block_user_layer", _HOOK_PATH)
assert _spec is not None
assert _spec.loader is not None
_block_user_layer = importlib.util.module_from_spec(_spec)
sys.modules["_block_user_layer"] = _block_user_layer
_spec.loader.exec_module(_block_user_layer)
```

**Excerpt 2 — `tests/test_fixtures.py` lines 47–72 (verbatim) — for the parametrize-over-filesystem-derived-list idiom:**

```python
def test_golden_pmt_fixture_loads() -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    assert "fixtures" in data
    assert isinstance(data["fixtures"], list)
    assert len(data["fixtures"]) == 4


@pytest.mark.parametrize("idx", range(4))
def test_golden_pmt_each_fixture_well_formed(idx: int) -> None:
    data = json.loads(FIXTURE_PATH.read_text())
    fx: dict[str, Any] = data["fixtures"][idx]
    assert fx.keys() >= REQUIRED_FIELDS
```

**Excerpt 3 — `02-RESEARCH.md` Pattern 5 lines 542–567 (verbatim) — the meta-test target:**

```python
RULES_DIR = Path(__file__).parent.parent.parent / "lib" / "rules"
FIX_DIR = Path(__file__).parent.parent / "fixtures" / "rules"

NON_PREDICATE_FILES: frozenset[str] = frozenset({"__init__.py", "_loader.py", "types.py"})


def _predicate_modules() -> list[Path]:
    return sorted(p for p in RULES_DIR.glob("*.py") if p.name not in NON_PREDICATE_FILES)


@pytest.mark.parametrize("path", _predicate_modules(), ids=lambda p: p.stem)
def test_predicate_has_citation_in_docstring(path: Path) -> None:
    src = path.read_text()
    m = re.search(r'^"""(.*?)"""', src, flags=re.DOTALL)
    assert m is not None, f"{path.name} missing module docstring (RUL-12)"
    docstring = m.group(1)
    assert "Citation:" in docstring, f"{path.name} docstring missing 'Citation:' (RUL-12)"
    assert "Source URL:" in docstring, f"{path.name} docstring missing 'Source URL:' (RUL-12)"
    assert "Effective:" in docstring, f"{path.name} docstring missing 'Effective:' (RUL-12)"
    assert re.search(r"https?://", docstring), (
        f"{path.name} docstring 'Source URL:' must contain an http(s) URL (RUL-12)"
    )
```

**Conventions established:**
- **Path resolution:** `Path(__file__).parent.parent.parent / "lib" / "rules"` mirrors the navigation pattern in `tests/test_block_user_layer.py:24` (`.../"scripts"/"hooks"/...`). Three `.parent` levels up from `tests/test_rules/test_citation_coverage.py` reaches the repo root.
- **`NON_PREDICATE_FILES` is a `frozenset`** — same idiom as `tests/test_fixtures.py:26-37` (`REQUIRED_FIELDS: frozenset[str]`, `EXPECTED_IDS: frozenset[str]`).
- **Pytest IDs from filename stem** — `ids=lambda p: p.stem` makes failures read `[loan_type]` not `[PosixPath('/.../loan_type.py')]`.
- **Failure messages name the requirement ID** (`RUL-12`, `RUL-13`) so the executor immediately knows which checklist box went red.
- The test parametrizes at *collection* time — adding a new predicate file produces 1–2 new parametrized cases automatically; missing fixture → red.

---

### `tests/test_rules/test_loader.py` (new — REF-08 staleness)

**Closest analog:** `tests/test_block_user_layer.py` lines 102–121 — the project's existing `tmp_path`-shaped pattern is implicit (the hook test invokes `main(...)` directly), but the full `tmp_path + monkeypatch` pattern is **NEW** — Phase 2 establishes it. The shape RESEARCH.md prescribes does not appear in any Phase 1 file.

**Excerpt 1 — `tests/test_block_user_layer.py` lines 102–121 (verbatim) — for the "exit-code / capsys-shaped" assertion idiom:**

```python
def test_main_exits_zero_with_no_offenders() -> None:
    rc = main(["scripts/hooks/block-user-layer.py", "lib/money.py", "pyproject.toml"])
    assert rc == 0


def test_main_exits_one_with_user_layer_offender() -> None:
    rc = main(["scripts/hooks/block-user-layer.py", "config/household.yml"])
    assert rc == 1
```

**Excerpt 2 — `02-RESEARCH.md` lines 945–970 (verbatim) — the Phase-2 staleness test target:**

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

**Conventions established:**
- `tmp_path` (pytest builtin) for synthetic YAML files — never write to `data/reference/` from a test.
- `monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)` redirects the loader's directory; pair with `load_reference.cache_clear()` so the cached pre-monkeypatch result is discarded (RESEARCH.md Pitfall 12 lines 1107–1110).
- `pytest.warns(StaleReferenceWarning, match="more than 12 months old")` is the Phase-2 idiom for warning-capture; `warnings.simplefilter("error", StaleReferenceWarning)` is the Phase-2 idiom for "assert no warning fires."
- Module docstring follows the same shape as `tests/test_block_user_layer.py:1-13` (lists coverage with bullets + each assertion's expected behavior).

---

### `tests/test_reference/test_schema.py` (new — REF-09)

**Closest analog:** `tests/test_fixtures.py` lines 1–72 (parametrize over JSON-loaded data, assert structural invariants); `tests/test_block_user_layer.py:36-44` (parametrize over a fixed list of paths). Phase 2 combines them into a filesystem-discovery + schema-assertion meta-test.

**Excerpt — `02-RESEARCH.md` lines 921–941 (verbatim) — the schema-test target:**

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
    assert isinstance(raw["effective"], date), f"{path.name} effective must be a date"
```

**Conventions to carry forward:**
- Same `Path(__file__).parent.parent.parent / ...` pattern as `tests/test_block_user_layer.py:24`.
- `ids=lambda p: p.stem` so failures show `[conforming-limits-2026]` not the full path (mirror of citation-coverage test above).
- Failure-message format always names the file (`f"{path.name} missing ..."`) so the executor knows which YAML to fix.
- `_ref_files()` returns a `sorted(...)` list — deterministic test ordering across OSes (same pattern as `_predicate_modules()` in citation-coverage test).

---

### `tests/fixtures/rules/{predicate_stem}_*.json` (per-predicate JSON fixtures)

**Closest analog:** `tests/fixtures/golden_pmt.json` lines 1–45 — the Phase-1 fixture schema. Phase 2 extends it with `citation`, `source_url`, `comment` (hand-calc) fields per RESEARCH.md Pattern 4 line 502–510.

**Excerpt 1 — `tests/fixtures/golden_pmt.json` lines 4–13 (verbatim) — for the JSON shape + `notes`-as-citation idiom:**

```json
{
  "id": "wikipedia_200k_30yr",
  "source": "https://en.wikipedia.org/wiki/Mortgage_calculator",
  "principal": "200000.00",
  "annual_rate": "0.065000",
  "term_months": 360,
  "expected_monthly_pi": "1264.14",
  "rounding": "ROUND_HALF_UP",
  "notes": "Wikipedia worked example; canonical reference."
}
```

**Excerpt 2 — `02-RESEARCH.md` lines 501–510 (verbatim) — the Phase-2 per-predicate fixture target:**

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

**Conventions established:**
- **One file per fixture, not one file with a `fixtures: [...]` array.** Reason: per-predicate fixture files use filename-prefix matching (`{predicate_stem}_*.json`) so the citation-coverage test can verify ≥1 fixture exists per predicate via `FIX_DIR.glob(f"{path.stem}_*.json")` (RESEARCH.md Pattern 5 line 563). This is **DIFFERENT** from Phase 1's single-file `golden_pmt.json` array — the new convention is one-file-per-fixture under `tests/fixtures/rules/`.
- **All money/rate values are JSON strings** (`"200000.00"`, `"0.065000"`) — same convention as Phase 1's `golden_pmt.json:8-9`. Loaded via `Decimal(fx["principal"])` in the test.
- **Required fields:** `citation` (regulator citation, e.g. `"12 USC §4902(b)"`), `source_url` (http(s) URL), `comment` (hand-calc derivation in plain English), plus the predicate-specific input/output keys.
- **Filename convention:** `{predicate_module_stem}_{descriptive_slug}.json` — e.g. `loan_type_high_cost_county_ceiling.json`, `fha_mip_term30_ltv95.json`. Lowercase + underscores throughout (matches `lib/rules/*.py` stems).
- **Hand-calc derivation in `comment`** mirrors the `# Hand: ...` discipline from `tests/test_money.py:30-32`.

---

### `pyproject.toml` (modify — add `pyyaml`)

**Closest analog:** existing `pyproject.toml` lines 6–10 — the live `[project.dependencies]` block.

**Excerpt — `pyproject.toml` lines 1–18 (verbatim, the diff target):**

```toml
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
```

**Diff to apply (RESEARCH.md "Installation" lines 92–95):**
- Insert `"pyyaml>=6.0.2",` into the `dependencies = [...]` list (alongside pydantic/python-dateutil/numpy-financial). pydantic and python-dateutil are already pinned; **do not re-add them.**
- Run `uv add 'pyyaml>=6.0.2'` (which both updates `pyproject.toml` and regenerates `uv.lock`); **do not hand-edit** `uv.lock`.
- Phase-1 conventions to keep: ordered dependency list, version-spec format `>=X.Y.Z`, no extras unless needed.

**`[[tool.mypy.overrides]]` may need an entry** for `yaml` if PyYAML's typeshed stubs are incomplete in the current `mypy>=1.20` — Phase 1 PATTERNS § "pyproject.toml" notes the precedent for `numpy_financial` (`pyproject.toml:57-59`):

```toml
[[tool.mypy.overrides]]
module = "numpy_financial"
ignore_missing_imports = true
```

If `mypy --strict` errors on `import yaml`, add a mirror block for `yaml`. (Resolve at execution time; `pyyaml` ships `py.typed` since 6.0.1, so the override is likely unnecessary — verify.)

---

### `.pre-commit-config.yaml` (optional modify — add `check-yaml` for `data/reference/`)

**Closest analog:** existing `.pre-commit-config.yaml` (full file, 30 lines) — Phase 1 established the local + remote-hooks structure.

**Excerpt — `.pre-commit-config.yaml` lines 4–30 (verbatim — current file):**

```yaml
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
          - pytest>=9.0
        args: [--strict]

  - repo: local
    hooks:
      - id: block-user-layer
        name: Block commits to user-layer files (DATA_CONTRACT.md)
        entry: uv run python scripts/hooks/block-user-layer.py
        language: system
        stages: [pre-commit]
        always_run: true
        pass_filenames: true
```

**Diff to apply (Wave 0 task — see VALIDATION.md Wave-0 line 82, marked "optional but cheap"):**
- Add a `check-yaml` hook (from `pre-commit/pre-commit-hooks`) scoped via `files:` regex to `data/reference/.*\.yml$`. This catches malformed YAML before commit.
- Add `pyyaml>=6.0.2` to the mypy hook's `additional_dependencies` list (mirrors the Phase-1 convention for `pydantic` / `python-dateutil` at lines 14–17). **Required if `lib/rules/_loader.py` is type-checked by the hook.** Phase-1 PATTERNS § "Pre-commit + CI Gate Symmetry" sets this rule.
- Pin `rev:` to a specific tag (mirror Phase-1 lines 6, 13 — `v0.15.12`, `v1.20.2`).

Suggested addition (planner finalizes):

```yaml
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0   # planner: pin to current tag at execution time
    hooks:
      - id: check-yaml
        files: ^data/reference/.*\.yml$
```

**Conventions to carry forward:** lockstep with `pyproject.toml` (Phase 1 PATTERNS Convention #5: "bumping ruff means bumping both files in the same commit"). The mypy hook's `additional_dependencies` array must list every runtime dependency `lib/rules/*.py` imports — adding pyyaml here when it lands in `pyproject.toml`.

---

### `lib/rules/__init__.py`, `tests/test_reference/__init__.py`, `tests/test_rules/__init__.py`, `tests/fixtures/rules/__init__.py` (4 empty markers)

**Closest analog:** `lib/__init__.py` (1 byte, empty), `tests/__init__.py` (empty), `tests/fixtures/__init__.py` (empty), `scripts/hooks/__init__.py` (empty).

**Convention to carry forward:** Empty file. No re-exports. **Do NOT add `from .loan_type import classify`** in `lib/rules/__init__.py` — defeats the per-citation audit trail (RESEARCH.md "Anti-Patterns" line 119, "Things the planner might be tempted to add but should NOT" line 1140). Phase 1 PATTERNS Convention #1 set the precedent ("nobody constructs `Decimal` from a literal in scattered places" — same flat-import discipline).

---

## Shared Patterns

These cross-cutting conventions touch ≥3 Phase 2 files. Planner should reference them once per plan, not repeat per task.

### Decimal Discipline

**Source:** `lib/money.py` lines 1–46 (full file) + Phase 1 PATTERNS § "Decimal Discipline" + RESEARCH.md "Project Constraints" lines 56–58.
**Apply to:** every `lib/rules/*.py` predicate; every `data/reference/*.yml`; every `tests/test_rules/test_*.py`; every `tests/fixtures/rules/*.json`.
**Concrete excerpt — `lib/money.py` lines 39–46:**

```python
def quantize_cents(value: Decimal) -> Decimal:
    """Round a Decimal to two places using ROUND_HALF_UP.

    Call ONCE at end-of-period; never mid-calculation. Uses `localcontext` so the
    global Decimal context is not mutated (pitfall 9).
    """
    with localcontext(MONEY_CONTEXT):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
```

**Rules:**
- All money values in YAML are quoted strings: `"832750"`, `"0.0055"`, never `832750` or `0.0055` (RESEARCH.md Pitfall 1).
- All Decimal construction in Python from strings: `Decimal("0.78")`, never `Decimal(0.78)`.
- Predicate dollar outputs end with **exactly one** `quantize_cents(...)` call.
- Tests use exact `==` for Decimal equality; `pytest.approx` is forbidden (CLAUDE.md "Testing").

### Pydantic v2 Strict Mode at Boundaries

**Source:** `lib/models.py` lines 36–45 + Phase 1 PATTERNS § "Pydantic v2 Strict Mode" + RESEARCH.md "Project Constraints" line 58.
**Apply to:** every BaseModel in `lib/rules/types.py`; every predicate signature in `lib/rules/*.py` that takes a model input.
**Concrete excerpt — `lib/models.py` lines 36–45:**

```python
class Loan(BaseModel):
    """Inputs to an amortization. Phase 3 will use this; Phase 1 just defines it."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    principal: Money
    annual_rate: Rate
    term_months: int = Field(ge=1, le=600)
    origination_date: date | None = None
    loan_type: Literal["fixed", "arm", "fha", "va", "usda", "jumbo"] = "fixed"
```

**Rules:**
- `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` — verbatim, no paraphrases.
- Reuse `Money` and `Rate` aliases from `lib.models` — do not redefine.
- New domain enums use `Literal[...]` not `enum.Enum` (Phase 1 precedent at `lib/models.py:45`).
- `# type: ignore[arg-type]` permitted only in negative tests proving fail-loud (Phase-1 precedent: `tests/test_models.py:42`).

### Test File Discipline

**Source:** `tests/test_money.py` lines 1–10 + `tests/test_models.py` lines 1–13 + Phase 1 PATTERNS § "Test File Discipline".
**Apply to:** every `tests/test_rules/test_*.py` and `tests/test_reference/test_*.py`.

**Concrete excerpt — `tests/test_money.py` lines 1–10 (verbatim):**

```python
"""Tests for lib/money.py — Decimal discipline (FND-01).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - to_money: string-only construction
  - quantize_cents: ROUND_HALF_UP (not banker's ROUND_HALF_EVEN)
  - MONEY_CONTEXT: prec=28, rounding=ROUND_HALF_UP
  - localcontext discipline: global getcontext() unchanged after roundtrip
"""
```

**Rules:**
- Module docstring lists (a) module under test + REQ-IDs covered, (b) phrase "Every assertion includes the hand-calculated expected value and why" verbatim, (c) bullet list of coverage areas.
- Test names read as English sentences (`test_loan_type_classifies_high_cost_ceiling`, `test_loan_type_raises_on_missing_county`).
- Each assertion comment carries the hand-calc derivation citing the regulator (`# Hand: HUD ML 2023-05 Table A row "Term > 15yr, LTV > 95%, ≤ $726,200" → 0.0055`).
- Pinned regulator-published values appear ONLY in fixture JSON files; tests read them via fixture loader, never re-derive inline.

### Citation/Source/Effective Header

**Source:** RESEARCH.md Pattern 3 lines 386–417 + Pattern 5 lines 547–559 + 02-VALIDATION.md REF-08 / RUL-12 rows.
**Apply to:** every `lib/rules/*.py` predicate file; every `tests/fixtures/rules/*.json` fixture file; every `data/reference/*.yml`.

**Three-string contract** (the citation-coverage meta-test scans the docstring for these literal substrings):

| Substring | Where | Required Format |
|-----------|-------|-----------------|
| `Citation:` | predicate docstring | followed by regulator citation (e.g., `12 USC §4902(b)`, `HUD ML 2023-05`) |
| `Source URL:` | predicate docstring | followed by `http(s)://...` URL |
| `Effective:` | predicate docstring | followed by ISO-8601 date |

For YAML files, the same three concepts live as top-level keys (`source:` URL, `effective:` date, `notes:` description). For JSON fixtures, the same three live as `citation`, `source_url`, `comment` keys (RESEARCH.md Pattern 4 line 502).

### Filesystem-Introspecting Meta-Tests

**Source:** `tests/test_block_user_layer.py` lines 14–34 (importlib script load) + `tests/test_fixtures.py` lines 47–72 (parametrize over JSON-loaded data) + RESEARCH.md Pattern 5.
**Apply to:** `tests/test_reference/test_schema.py`, `tests/test_rules/test_citation_coverage.py`, and any future Phase-2-shaped meta-test.

**Rules:**
- Path resolution: `Path(__file__).resolve().parent.parent.parent / ...` to reach repo root (mirror of `tests/test_block_user_layer.py:24`).
- Parametrize over `sorted(...)` filesystem lists for deterministic test ordering across OSes (mirror of citation-coverage `_predicate_modules()` and schema `_ref_files()`).
- `ids=lambda p: p.stem` for human-readable failure IDs.
- Failure messages reference the requirement ID (`RUL-12`, `RUL-13`, `REF-09`) so green/red maps directly to the requirements traceability matrix.
- Exclude package markers and infrastructure files via `frozenset[str]` constants (mirror of `NON_PREDICATE_FILES` in RESEARCH.md Pattern 5; `REQUIRED_FIELDS`/`EXPECTED_IDS` in `tests/test_fixtures.py:26-45`).

---

## No Analog Found (files where Phase 2 establishes the convention from scratch)

These files have no in-repo precedent beyond the Phase-1 conventions they mechanically inherit. Planner should treat the cited RESEARCH.md pattern blocks as the authoritative source.

| File | Role | Why no analog | Authoritative pattern source |
|------|------|---------------|------------------------------|
| `lib/rules/_loader.py` | source (loader + cache + warnings) | Phase 1 has no module that owns a singleton/cache/lazy-load. | RESEARCH.md Pattern 2 (lines 308–381) |
| `data/reference/conforming-limits-2026.yml` (and 6 sibling YAMLs) | reference (YAML data) | `data/reference/` is empty (Phase 1 only created the directory + `.gitkeep`). | RESEARCH.md Pattern 1 (lines 270–297) |
| `tests/test_rules/test_citation_coverage.py` | test (filesystem meta) | Phase 1's filesystem-introspection (`tests/test_block_user_layer.py`) targets a single script; Phase 2 is the first test that introspects `lib/rules/`. | RESEARCH.md Pattern 5 (lines 542–567) |
| `lib/rules/loan_type.py` (and 10 sibling predicate files) | source (predicate template) | Phase 1 has only `lib/money.py` (utility helpers) and `lib/models.py` (Pydantic types). The predicate-per-citation file template is new. | RESEARCH.md Pattern 3 (lines 386–445) |

For the rest of the Phase-2 files (test modules, fixture JSONs, package markers, the schema test, the loader test, pyproject diff, pre-commit diff), in-repo analogs from Phase 1 are strong and listed in the per-file Pattern Assignments above.

---

## Conventions Established by Phase 2

These rules are *new* to the project (not in Phase 1 PATTERNS) and become inheritable by Phases 3–12.

1. **Reference-data layer = YAML, not Python.** `data/reference/*.yml` is the only place regulatory parameters live. Annual refresh = YAML edit + commit. (Inherited by Phase 9 known-loans, Phase 12 FRED cache directory.)
2. **`data/reference/*.yml` schema:** mandatory top-level `source:` (URL), `effective:` (ISO-8601 unquoted date), `notes:` (description for link-rot insurance); body uses regulator-specific keys; all numeric scalars quoted as strings.
3. **Loader-pattern:** `lib/rules/_loader.py` shape — `lru_cache(maxsize=None)` + custom `Warning` subclass for first-load checks + `Path(__file__).parent.parent.parent / "data" / "reference"` for repo-root navigation. Phase 9 DuckDB connection-loader and Phase 12 FRED-cache loader replay this template.
4. **Predicate template:** one file per regulatory citation in `lib/rules/`. Module docstring contains the three-string contract (`Citation:`, `Source URL:`, `Effective:`). Pure functions, Pydantic-typed I/O, exactly one `quantize_cents` per dollar return. No predicate imports another predicate.
5. **Citation-coverage meta-test:** filesystem-introspecting `pytest.mark.parametrize` over `lib/rules/*.py` (excluding `__init__.py`, `_loader.py`, `types.py`) — adding a new predicate file without its docstring header or fixture creates a new failing test case automatically.
6. **Per-predicate fixture-file convention:** **One JSON file per fixture** (not the Phase-1 single-file array shape) under `tests/fixtures/rules/{predicate_stem}_*.json`. Required fields `citation`, `source_url`, `comment`. The citation-coverage test verifies ≥1 file matches each predicate stem.
7. **Custom-warning-as-Library-API:** `StaleReferenceWarning(UserWarning)` sub-class. Tests use `pytest.warns(StaleReferenceWarning)` for fire assertions, `warnings.simplefilter("error", StaleReferenceWarning)` for non-fire assertions. CI does NOT promote `StaleReferenceWarning` to error (VALIDATION.md "Manual-Only Verifications" row 2).
8. **Phase-1 contracts stay frozen:** Phase 2 puts new BaseModels in `lib/rules/types.py`, NOT in `lib/models.py` (RESEARCH.md "Why this layout" line 263). The `Loan`/`Payment`/`Schedule` surface remains exactly as Phase 1 shipped it.

---

## Metadata

**Analog search scope:**
- In-repo: `/Users/cujo253/Documents/mortgage-ops/lib/`, `/tests/`, `/scripts/`, `/data/reference/`, `/.github/workflows/`, `/.pre-commit-config.yaml`, `/pyproject.toml`, `/.gitignore`, `/.python-version`.
- Cross-references: Phase 1 `01-PATTERNS.md` (sibling phase pattern map), `02-RESEARCH.md` Patterns 1–5 (canonical authoritative source for new-pattern files), `02-VALIDATION.md` Wave-0 list.

**Files scanned (full read):**
- `/lib/__init__.py` (empty)
- `/lib/money.py` (46 lines)
- `/lib/models.py` (70 lines)
- `/tests/conftest.py` (35 lines)
- `/tests/test_money.py` (69 lines)
- `/tests/test_models.py` (163 lines)
- `/tests/test_fixtures.py` (122 lines)
- `/tests/test_block_user_layer.py` (121 lines)
- `/tests/test_smoke.py` (13 lines)
- `/tests/fixtures/golden_pmt.json` (45 lines)
- `/scripts/hooks/block-user-layer.py` (67 lines)
- `/pyproject.toml` (65 lines)
- `/.pre-commit-config.yaml` (30 lines)
- `/.gitignore` (29 lines)
- `/.python-version` (1 line)
- `/.planning/phases/01-foundations-money-discipline/01-PATTERNS.md` (405 lines)
- `/.planning/phases/02-regulatory-reference-data-rules-predicates/02-RESEARCH.md` (lines 1–1200 — Patterns 1–5, per-rule design, test discipline, pitfalls)
- `/.planning/phases/02-regulatory-reference-data-rules-predicates/02-VALIDATION.md` (105 lines)
- `/.planning/REQUIREMENTS.md` (357 lines, REF-01..09 + RUL-01..13 sections)
- `/CLAUDE.md` (133 lines, conventions block)

**Confirmed empty / not-yet-existing (Phase 2 will create):**
- `/lib/rules/` (does not exist)
- `/data/reference/` (only `.gitkeep` present)
- `/tests/test_rules/` (does not exist)
- `/tests/test_reference/` (does not exist)
- `/tests/fixtures/rules/` (does not exist)

**Pattern extraction date:** 2026-04-26

## PATTERN MAPPING COMPLETE

**Files mapped:** 24 new + 2 modifications = 26 total
**In-repo strong analogs:** 11
**ESTABLISHES PATTERN tags:** 4 (loader, predicate template, YAML format, citation-coverage meta-test)
