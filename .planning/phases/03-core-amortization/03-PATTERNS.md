# Phase 3: Core Amortization - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 8 (4 CREATE + 4 MODIFY)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `lib/amortize.py` (CREATE) | production-engine | transform (Loan → Schedule); wraps numpy-financial | `lib/money.py` (Phase 1 stdlib-Decimal wrapper) + `lib/rules/atr_qm.py` (Phase 2 predicate w/ locked decisions in docstring) | role-match (engine wrapper) |
| `scripts/amortize.py` (CREATE) | cli-script | request-response (JSON-in / JSON-out via argparse) | `scripts/hooks/block-user-layer.py` (only `scripts/*.py` in tree; same `if __name__ == "__main__": sys.exit(main())` shape) | partial — only existing CLI is a hook, not a Pydantic-boundary CLI |
| `tests/test_amortize.py` (CREATE) | unit-test + integration-test | invariant assertion + subprocess CLI | `tests/test_money.py` (Decimal-discipline test idiom) + `tests/test_fixtures.py` (golden-fixture loader use) + `tests/test_block_user_layer.py` (subprocess/script-import idiom) | exact (composite) |
| `tests/fixtures/amortize/*.json` (CREATE) | fixture-data | static JSON oracles | `tests/fixtures/golden_pmt.json` (Phase 1 oracle shape: `id`/`source`/`principal`/`annual_rate`/`term_months`/`expected_*`/`rounding`/`notes`) | exact |
| `lib/models.py` (MODIFY) | production-model + model-validator-extension | additive Pydantic field + `@model_validator` | self (Phase 1 frozen surface — extend in place, not replace) | exact (in-place additive) |
| `tests/test_models.py` (MODIFY) | unit-test | additive assertions + one updated fixture-construction | self (extend) | exact |
| `tests/conftest.py` (MODIFY) | unit-test (fixture factory) | additive `pytest.fixture` | self (extend with second loader fixture) | exact |
| `pyproject.toml` (MODIFY) | dev-tooling-config | (no change) — `numpy-financial==1.0.0` already pinned line 9; `[[tool.mypy.overrides]]` for `numpy_financial` already present line 58-60 | self (verify only) | exact (no edit needed) |

---

## Pattern Assignments

### `lib/amortize.py` (production-engine, transform)

**Primary analog:** `lib/money.py` (lines 1-47)
**Secondary analog (docstring-with-locked-decisions idiom):** `lib/rules/atr_qm.py` (lines 1-49)

**Module-docstring pattern** — copy the structure from `lib/money.py` lines 1-13 (purpose → "single source of truth" → why-not-default rationale → reference back to research):

```python
# lib/money.py:1-13
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
```

**Locked-decision-in-docstring pattern** — copy from `lib/rules/atr_qm.py` lines 29-42 for D-01..D-19 (each LOCKED DECISION block names the decision, cites the source, and states the rule):

```python
# lib/rules/atr_qm.py:29-42
"""
LOCKED DECISION - Threshold-unit convention (per CONTEXT.md D-02):
  YAML stores threshold as PERCENTAGE POINTS (e.g. "2.25" = 2.25 pp).
  Predicate divides by 100 at consumption time to compare against the
  fractional spread `apr - apor`. Stays human-readable against CFPB's
  published table while keeping all arithmetic in Decimal.

LOCKED DECISION - Boundary semantics (per RESEARCH.md lines 877-887):
  Loan-amount tier boundaries are INCLUSIVE on the lower bound (`>=`) and
  EXCLUSIVE on the upper bound (`<`). Exactly $66,156 first-lien is in the
  mid band; exactly $110,260 first-lien is in the high band.
"""
```

**Adapt:** Apply this docstring shape to D-01 (both biweekly modes), D-02 (default biweekly_mode="true"), D-04 (rate conversions), D-07 (extra-principal order), D-09 (final-cleanup), and the bug-#130 / bug-#131 avoidance comment block (per RESEARCH §11).

**Imports pattern** — `lib/money.py` lines 15-18 establishes the `from __future__ import annotations` + stdlib + typing convention. `lib/rules/atr_qm.py` lines 44-47 + `lib/rules/_loader.py` lines 11-21 establish the third-party + first-party order:

```python
# lib/rules/_loader.py:11-21
from __future__ import annotations

import re
import warnings
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import yaml
from dateutil.relativedelta import relativedelta
```

**Adapt for `lib/amortize.py`:**

```python
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

import numpy_financial as npf  # type: ignore[import-untyped]  # mirrors pyproject.toml override line 58-60
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.models import Loan, Payment, Schedule
from lib.money import CENT, quantize_cents

if TYPE_CHECKING:
    from collections.abc import Sequence
```

**Notes:**
- `# type: ignore[import-untyped]` for `numpy_financial` is already covered by `pyproject.toml [[tool.mypy.overrides]] module = "numpy_financial"` (lines 58-60). Use `# type: ignore[import-untyped]` only if local mypy still complains; otherwise drop.
- `from __future__ import annotations` is mandatory — every Phase 1+2 module uses it (verified: `lib/money.py:15`, `lib/models.py:14`, `lib/rules/atr_qm.py:51` style).

**`ExtraPrincipalEntry` Pydantic-model pattern** — copy from `lib/models.py` lines 36-45 (`Loan` class):

```python
# lib/models.py:36-45
class Loan(BaseModel):
    """Inputs to an amortization. Phase 3 will use this; Phase 1 just defines it."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    principal: Money
    annual_rate: Rate
    term_months: int = Field(ge=1, le=600)
    origination_date: date | None = None
    loan_type: Literal["fixed", "arm", "fha", "va", "usda", "jumbo"] = "fixed"
```

**Keep:** `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` verbatim — every domain model in this project uses it (verified: `lib/models.py:39, 51, 65`).

**Adapt for `ExtraPrincipalEntry`:**
```python
class ExtraPrincipalEntry(BaseModel):
    """One extra-principal entry. D-05 collapses one-shot/recurring/step-up to one schema."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=1)
    amount: Decimal = Field(strict=True, gt=Decimal("0"), max_digits=14, decimal_places=2)
    recurring: bool = False
```

**Note:** the `amount` field uses `gt=Decimal("0")` (strictly positive) instead of `ge=Decimal("0")` (Phase 1's `Money` alias). Document inline why: extra-principal of zero is meaningless; surface immediately as a validation error.

**`AmortizeRequest` Pydantic-model with `@model_validator` pattern** — copy from `lib/rules/_loader.py` lines 45-87 (the `@lru_cache` + `_NAME_RX` validation idiom). For the validator itself, the canonical Pydantic v2 form is the `@model_validator(mode="after")` shown in RESEARCH §6:

```python
class AmortizeRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    frequency: Literal["monthly", "biweekly"] = "monthly"
    biweekly_mode: Literal["true", "half-monthly"] | None = None
    extra_principal: list[ExtraPrincipalEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _biweekly_mode_consistency(self) -> AmortizeRequest:
        """D-02: biweekly_mode MUST be None when frequency is monthly."""
        if self.frequency == "monthly" and self.biweekly_mode is not None:
            raise ValueError("biweekly_mode must be None when frequency='monthly' (D-02)")
        return self
```

**Quantize-once-at-end-of-period pattern** — copy the `quantize_cents` discipline from `lib/money.py` lines 39-46:

```python
# lib/money.py:39-46
def quantize_cents(value: Decimal) -> Decimal:
    """Round a Decimal to two places using ROUND_HALF_UP.

    Call ONCE at end-of-period; never mid-calculation. Uses `localcontext` so the
    global Decimal context is not mutated (pitfall 9).
    """
    with localcontext(MONEY_CONTEXT):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
```

**Adapt:** every per-period iteration in `build_schedule` calls `quantize_cents` exactly once per Money assignment (`interest`, `principal_paid`, `payment`, `extra`) — never inside a compound expression. Code-review check from RESEARCH §13 risk register: `! grep -E 'quantize_cents.*[+\-*/].*quantize_cents' lib/amortize.py`.

**`build_schedule` function signature** — no direct analog (no engine functions exist yet). Use the keyword-only-args + `Sequence` typing convention from RESEARCH §2:

```python
def build_schedule(
    loan: Loan,
    *,
    frequency: Literal["monthly", "biweekly"] = "monthly",
    biweekly_mode: Literal["true", "half-monthly"] | None = None,
    extra_principal: Sequence[ExtraPrincipalEntry] = (),
) -> Schedule: ...
```

**Anti-patterns to avoid (per CLAUDE.md + PITFALLS.md):**
- ❌ `Decimal(0.065)` — float coercion. Always `Decimal("0.065")` from string.
- ❌ Mid-calculation quantize: `quantize_cents(rate * balance) - quantize_cents(...)`. Quantize each Money assignment exactly once at the end.
- ❌ `npf.pmt(..., fv=non_zero)` — bug #130 sign-flip. Always `fv=0` (default).
- ❌ `npf.irr(...)` — bug #131 arch-dependent. Phase 6 will use `pyxirr`.
- ❌ Float anywhere in the pipeline. numpy-financial 1.0.0 is end-to-end Decimal; if a future numpy-financial regression forces float, isolate with `Decimal(str(value))` reconstruction at the boundary and comment loudly.
- ❌ Re-implementing PMT formula by hand. AMRT-01 contract: WRAP `npf.pmt`, do not reimplement.

---

### `scripts/amortize.py` (cli-script, request-response)

**Closest analog:** `scripts/hooks/block-user-layer.py` (the only existing `scripts/*.py` file in the tree). NB: this is a *partial* match — `block-user-layer.py` is a pre-commit hook reading `argv` paths, not a Pydantic-boundary CLI reading `--input <path>` JSON. We borrow the **shebang + `from __future__` + `def main(argv) -> int` + `sys.exit(main(sys.argv))`** shape; we do NOT borrow the path-list pattern (we use `argparse` instead).

**Imports + entrypoint pattern** — copy from `scripts/hooks/block-user-layer.py` lines 1-15 + 46-67:

```python
# scripts/hooks/block-user-layer.py:1-15
#!/usr/bin/env python3
"""Pre-commit hook: refuse to commit any User Layer file.
...
"""

from __future__ import annotations

import sys
```

```python
# scripts/hooks/block-user-layer.py:46-67
def main(argv: list[str]) -> int:
    """Pre-commit invokes this with `argv[0] == script` and `argv[1:]` = staged paths."""
    offenders = [a for a in argv[1:] if is_user_layer(a)]
    if not offenders:
        return 0
    print(...)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

**Keep:** shebang line `#!/usr/bin/env python3`, `from __future__ import annotations`, `def main(...) -> int` returning explicit exit code, `if __name__ == "__main__": sys.exit(main(...))`.

**Adapt:** `main()` takes no args (argparse parses `sys.argv` itself); add lazy-import per D-18:

```python
#!/usr/bin/env python3
"""scripts/amortize.py — JSON-in / JSON-out CLI for the amortization engine.

Per AMRT-06 + D-17/D-18/D-19:
- File-based input only: --input <path> (no stdin in v1)
- JSON output to stdout (pipe-friendly)
- --help works without importing heavy deps (lazy-import per D-18)
- Pydantic v2 strict-mode validation at the boundary (D-19)

Default biweekly_mode = "true" when frequency is "biweekly" without explicit mode (D-02).
Phase 10 will physically relocate this script to .claude/skills/mortgage-ops/scripts/amortize.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="amortize",
        description="Generate an amortization schedule from a JSON loan input.",
        epilog=(
            "Input JSON shape: a Loan object plus optional 'frequency', "
            '"biweekly_mode" (default "true" when biweekly), and "extra_principal" entries.'
        ),
    )
    parser.add_argument("--input", required=True, type=Path,
                        help="Path to JSON file containing the loan input.")
    args = parser.parse_args()

    # Lazy-import after argparse (D-18: --help is fast)
    from pydantic import ValidationError
    from lib.amortize import AmortizeRequest, build_schedule

    try:
        raw = args.input.read_text()
    except FileNotFoundError as e:
        print(json.dumps({"error": f"input file not found: {e.filename}"}), file=sys.stderr)
        return 2

    try:
        request = AmortizeRequest.model_validate_json(raw)  # D-19
    except ValidationError as e:
        print(e.json(), file=sys.stderr)
        return 2

    schedule = build_schedule(
        request.loan,
        frequency=request.frequency,
        biweekly_mode=request.biweekly_mode,
        extra_principal=request.extra_principal,
    )
    print(schedule.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Anti-patterns to avoid:**
- ❌ Top-level `from lib.amortize import ...` — defeats the lazy-import contract (D-18); makes `--help` slow.
- ❌ Top-level `import numpy_financial` — same: heavy import on the `--help` path.
- ❌ `print(traceback)` — surface Pydantic errors as structured JSON via `e.json()`, not raw tracebacks.
- ❌ Bare `except Exception:` — let unexpected exceptions propagate (loud-fail discipline matches `lib/rules/atr_qm.py` "raise ValueError" idiom).
- ❌ stdin support — D-18 explicitly says `--input <path>` only in v1.

---

### `tests/test_amortize.py` (unit-test + integration-test)

**Primary analog (Decimal-discipline test pattern):** `tests/test_money.py` (lines 1-69)
**Secondary analog (golden-fixture loader use):** `tests/test_fixtures.py` (lines 1-122)
**Tertiary analog (subprocess/script-import idiom for CLI tests):** `tests/test_block_user_layer.py` (lines 1-122)
**Quaternary analog (Pydantic-validation-error test idiom):** `tests/test_models.py` (lines 37-71)

**Test-module docstring pattern** — copy from `tests/test_money.py` lines 1-10 (purpose → coverage list):

```python
# tests/test_money.py:1-10
"""Tests for lib/money.py — Decimal discipline (FND-01).

Every assertion includes the hand-calculated expected value and why.

Coverage:
  - to_money: string-only construction
  - quantize_cents: ROUND_HALF_UP (not banker's ROUND_HALF_EVEN)
  - MONEY_CONTEXT: prec=28, rounding=ROUND_HALF_UP
  - localcontext discipline: global getcontext() unchanged after roundtrip
"""
```

**Adapt for `tests/test_amortize.py`** — list AMRT-01..08 + D-15 + month-end + CLI + invariants in the coverage block.

**Imports** — copy from `tests/test_money.py` lines 12-16 + `tests/test_fixtures.py` lines 12-22:

```python
# tests/test_money.py:12-16
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext

from lib.money import CENT, MONEY_CONTEXT, quantize_cents, to_money
```

```python
# tests/test_fixtures.py:12-22
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
```

**Adapt for `tests/test_amortize.py`:**
```python
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from lib.amortize import AmortizeRequest, ExtraPrincipalEntry, build_schedule
from lib.models import Loan, Payment, Schedule

if TYPE_CHECKING:
    from collections.abc import Callable
```

**Top-of-file `assert_schedule_invariants` helper** — no direct analog (it's a new contract per RESEARCH §10). Place at top of file just below imports; matches the helper-before-tests convention seen in `tests/test_block_user_layer.py` lines 18-33 (where `is_user_layer` and `main` are bound at module top before any test function):

```python
# tests/test_amortize.py (NEW helper, see RESEARCH §10 line 846-858)
def assert_schedule_invariants(schedule: Schedule, original_principal: Decimal) -> None:
    """Asserts AMRT-07 + D-11 + D-15 invariants on every produced schedule."""
    sum_principal = sum((p.principal for p in schedule.payments), start=Decimal("0.00"))
    sum_extra = sum((p.extra_principal for p in schedule.payments), start=Decimal("0.00"))
    assert sum_principal + sum_extra == original_principal, (
        f"AMRT-07/D-11 violated: sum(principal+extra)={sum_principal + sum_extra} != "
        f"original_principal={original_principal}"
    )
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert schedule.total_interest == schedule.payments[-1].cumulative_interest
```

**Exact-Decimal-equality assertion pattern** — copy from `tests/test_money.py` lines 19-46:

```python
# tests/test_money.py:30-34
def test_quantize_cents_uses_round_half_up_at_0p005() -> None:
    # Hand: ROUND_HALF_UP(0.005, 2) == 0.01.
    # ROUND_HALF_EVEN (Python's default; banker's rounding) would return 0.00.
    # This is the load-bearing assertion for FND-01: prove we are NOT using banker's.
    assert quantize_cents(Decimal("0.005")) == Decimal("0.01")
```

**Keep:** every assertion uses `==` against a literal `Decimal("...")` constructed from a string. Comment above each assertion includes "Hand: <calculation>" — established Phase 1 idiom (verified: every test in `tests/test_money.py` has a `# Hand:` comment).

**Anti-pattern reminder:** ❌ NEVER `assertAlmostEqual` for money. CLAUDE.md forbids; PITFALLS.md flags; `! grep -rE 'assertAlmostEqual' tests/test_amortize.py` is a plan acceptance gate.

**Pydantic-`ValidationError` test pattern** — copy from `tests/test_models.py` lines 37-44:

```python
# tests/test_models.py:37-44
def test_loan_rejects_float_principal() -> None:
    # Strict=True must reject floats — load-bearing assertion for FND-01 + FND-02.
    # The `# type: ignore[arg-type]` on the call below documents that mypy --strict
    # would catch this at compile time; the runtime test verifies Pydantic catches it too.
    with pytest.raises(ValidationError) as exc:
        Loan(principal=400000.0, annual_rate=Decimal("0.065000"), term_months=360)  # type: ignore[arg-type]
    assert "decimal_type" in str(exc.value) or "Input should be" in str(exc.value)
```

**Keep:** `with pytest.raises(ValidationError) as exc:` + assert on `str(exc.value)` substring. `# type: ignore[arg-type]` for runtime tests of mypy-rejected calls.

**Adapt for D-15 validator test:**
```python
def test_schedule_total_interest_must_match_last_cumulative() -> None:
    """D-15: validator rejects Schedule where total_interest != payments[-1].cumulative_interest."""
    loan = Loan(principal=Decimal("400000.00"), annual_rate=Decimal("0.065000"), term_months=360)
    p = Payment(
        period=1, payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"), principal=Decimal("361.60"),
        interest=Decimal("2166.67"), balance=Decimal("399638.40"),
        cumulative_interest=Decimal("2166.67"), cumulative_principal=Decimal("361.60"),
    )
    with pytest.raises(ValidationError) as exc:
        Schedule(loan=loan, monthly_pi=Decimal("2528.27"),
                 total_interest=Decimal("999.99"),  # mismatched
                 payments=[p])
    assert "D-15" in str(exc.value) or "total_interest" in str(exc.value)
```

**Golden-fixture loader use pattern** — copy from `tests/test_fixtures.py` lines 104-115:

```python
# tests/test_fixtures.py:104-115
def test_conftest_golden_fixture_loader_finds_each_id(
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Dogfood the conftest.py golden_fixture loader (Plan 01).

    Phase 3+ will use this loader to fetch fixtures; Phase 1 verifies it works on
    the real file before downstream phases depend on it.
    """
    for fixture_id in EXPECTED_IDS:
        fx = golden_fixture(fixture_id)
        assert fx["id"] == fixture_id
        assert fx["rounding"] == "ROUND_HALF_UP"
```

**Adapt — AMRT-08 oracle parametrization:**
```python
@pytest.mark.parametrize("fixture_id", [
    "wikipedia_200k_30yr",
    "cfpb_le_162k_30yr",
    "computed_400k_30yr",
    "computed_200k_15yr",
])
def test_fixed_rate_oracle(
    fixture_id: str,
    golden_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """AMRT-08: build_schedule's monthly_pi matches each pinned oracle exactly."""
    fx = golden_fixture(fixture_id)
    loan = Loan(
        principal=Decimal(fx["principal"]),
        annual_rate=Decimal(fx["annual_rate"]),
        term_months=fx["term_months"],
        origination_date=date(2026, 5, 1),
    )
    sched = build_schedule(loan)
    assert sched.monthly_pi == Decimal(fx["expected_monthly_pi"])
    assert_schedule_invariants(sched, loan.principal)
```

**Subprocess CLI test pattern** — copy the import-by-path idiom from `tests/test_block_user_layer.py` lines 22-33 (handles non-importable scripts), but for round-trip CLI tests prefer `subprocess.run` with `sys.executable`:

```python
# tests/test_block_user_layer.py:22-33  (script-import idiom; reuse if Phase 3 wants in-process tests)
_HOOK_PATH = Path(__file__).resolve().parent.parent / "scripts" / "hooks" / "block-user-layer.py"
_spec = importlib.util.spec_from_file_location("_block_user_layer", _HOOK_PATH)
assert _spec is not None
assert _spec.loader is not None
_block_user_layer = importlib.util.module_from_spec(_spec)
sys.modules["_block_user_layer"] = _block_user_layer
_spec.loader.exec_module(_block_user_layer)
```

**Adapt — subprocess pattern for `scripts/amortize.py` (preferred for AMRT-06 CLI tests, since the script's own module has importable name `scripts.amortize`):**

```python
# tests/test_amortize.py
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "amortize.py"

def test_cli_smoke_subprocess_round_trip(tmp_path: Path) -> None:
    """AMRT-06: write input JSON, run script, parse output JSON; balance lands at 0.00."""
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({
        "loan": {
            "principal": "200000.00",
            "annual_rate": "0.065000",
            "term_months": 360,
            "origination_date": "2026-05-01",
        },
    }))
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(input_path)],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["payments"][-1]["balance"] == "0.00"
```

**Note for Phase 10 readiness:** `SCRIPT_PATH` is computed as a constant; when Phase 10 relocates the script to `.claude/skills/mortgage-ops/scripts/amortize.py`, only this constant updates — no test logic changes (matches CONTEXT.md `code_context` line 173 guidance).

**Anti-patterns to avoid:**
- ❌ Hard-coded `python` instead of `sys.executable` — breaks venv/uv runs.
- ❌ `subprocess.run(..., shell=True)` — security smell; never needed when args is a list.
- ❌ Asserting on `result.stderr` substrings without parsing the Pydantic JSON error structure (use `json.loads(result.stderr)` and assert on field names like `"loc"`, `"type"`).
- ❌ Timing-based "fast --help" tests (flaky under CI). Use the import-mock approach per RESEARCH §7 + Open Question #4: assert `"lib.amortize" not in sys.modules` after `parser.parse_args(["--help"])`.

---

### `tests/fixtures/amortize/*.json` (fixture-data, static JSON)

**Closest analog:** `tests/fixtures/golden_pmt.json` (Phase 1 oracle shape, lines 1-46)

**Top-level structure pattern** — copy from `tests/fixtures/golden_pmt.json` lines 1-13:

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
    }
  ]
}
```

**Keep:**
- All money/rate fields are JSON STRINGS, not numbers (`"200000.00"` not `200000.0`). PITFALLS.md / CLAUDE.md hard rule.
- Every fixture has `id`, `source` (URL or "computed in-tree"), `rounding: "ROUND_HALF_UP"`, `notes`.
- Decimal places preserved (`"0.065000"` not `"0.065"`) — matches Phase 1 `Rate` type's `decimal_places=6` and lets `Decimal(s)` round-trip exactly.

**Adapt — `tests/fixtures/amortize/` schema (per RESEARCH §9):**

Each Phase 3 fixture file is a *single fixture per file* (not the wrapped `{"fixtures": [...]}` array used by `golden_pmt.json` — Phase 3 fixtures are richer with full `loan` block + `expected_schedule_summary` block, so per-file makes diffs readable):

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "id": "fixed_30yr_400k_6_5",
  "source": "computed in-tree with Decimal + ROUND_HALF_UP; cross-verified against Wikipedia oracle scaling",
  "rounding": "ROUND_HALF_UP",
  "notes": "Stress-test scale of Wikipedia oracle (2x principal, same rate/term).",
  "loan": {
    "principal": "400000.00",
    "annual_rate": "0.065000",
    "term_months": 360,
    "origination_date": "2026-05-01",
    "loan_type": "fixed"
  },
  "frequency": "monthly",
  "biweekly_mode": null,
  "extra_principal": [],
  "expected_schedule_summary": {
    "monthly_pi": "2528.27",
    "total_interest": "510176.86",
    "final_payment_adjusted": true,
    "num_payments": 360,
    "first_payment": { ... },
    "last_payment": { ... }
  }
}
```

**File list (per CONTEXT.md `code_context` + RESEARCH §9):**
- `fixed_30yr_400k_6_5.json` (mirror Wikipedia 2x scale)
- `biweekly_true_200k_6_5.json` (D-01 + D-04 true mode)
- `biweekly_half_monthly_200k_6_5.json` (D-01 + D-04 half-monthly mode)
- `extra_oneshot_5k_period_60.json` (D-05 one-shot)
- `extra_recurring_200_30yr.json` (D-05 recurring)
- `extra_step_up_200_to_300.json` (D-05 later-recurring-overrides)
- `extra_caps_at_balance.json` (D-08 silent cap → `final_payment_adjusted=True`)
- `month_end_jan_31.json` (D-13 relativedelta clipping)
- (Plus 3 reused references to `golden_pmt.json` for AMRT-08 fixed-rate oracles loaded via existing `golden_fixture` conftest factory — no new files needed for those.)

**Anti-patterns to avoid:**
- ❌ JSON numbers for money (`"principal": 200000.00` parses as float). Always strings.
- ❌ Pinning all 360 rows in a fixture (brittle, huge diffs). Pin first/last + summary; the AMRT-07 invariant covers middle rows.
- ❌ Missing `source` or `rounding` field — `golden_pmt.json` requires both per `tests/test_fixtures.py:26-37 REQUIRED_FIELDS`.
- ❌ `expected_monthly_pi: 1264.14` (number). Always string `"1264.14"`.

---

### `lib/models.py` (production-model, in-place additive extension)

**Analog:** self (`lib/models.py` lines 48-70 — the `Payment` and `Schedule` classes already exist; we extend them additively with default-valued new fields and a `@model_validator`).

**Existing `Payment` class to extend** — `lib/models.py` lines 48-59:

```python
# lib/models.py:48-59
class Payment(BaseModel):
    """A single period in the schedule."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    period: int = Field(ge=1)
    payment_date: date
    payment: Money
    principal: Money
    interest: Money
    extra_principal: Money = Decimal("0.00")
    balance: Money
```

**Adapt — D-14 additive fields with defaults (backwards-compatible):**
```python
class Payment(BaseModel):
    """A single period in the schedule."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    period: int = Field(ge=1)
    payment_date: date
    payment: Money
    principal: Money
    interest: Money
    extra_principal: Money = Decimal("0.00")
    balance: Money
    cumulative_interest: Money = Decimal("0.00")    # D-14 (default keeps Phase 1 tests green)
    cumulative_principal: Money = Decimal("0.00")   # D-14
```

**Keep:** `model_config` line verbatim. Field ordering: append new fields AFTER `balance` so that the JSON output of `model_dump_json` preserves Phase-1-readable order at the top.

**Existing `Schedule` class to extend** — `lib/models.py` lines 62-70:

```python
# lib/models.py:62-70
class Schedule(BaseModel):
    """Output of an amortization run. Phase 3 produces this; Phase 1 only defines."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    monthly_pi: Money
    total_interest: Money
    payments: list[Payment]
```

**Adapt — D-10 (`final_payment_adjusted`) + D-15 (`@model_validator`):**

```python
from pydantic import BaseModel, ConfigDict, Field, model_validator  # add model_validator

class Schedule(BaseModel):
    """Output of an amortization run. Phase 3 produces this; Phase 1 only defines."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    loan: Loan
    monthly_pi: Money
    total_interest: Money
    final_payment_adjusted: bool = False     # D-10 (default keeps Phase 1 tests green)
    payments: list[Payment]

    @model_validator(mode="after")
    def _total_interest_matches_last_cumulative(self) -> "Schedule":
        """D-15: Schedule.total_interest == payments[-1].cumulative_interest exactly.

        Skipped when payments is empty (constructor convenience; tests still cover
        non-empty schedules).
        """
        if not self.payments:
            return self
        last = self.payments[-1].cumulative_interest
        if self.total_interest != last:
            raise ValueError(
                f"D-15 invariant: Schedule.total_interest ({self.total_interest}) != "
                f"payments[-1].cumulative_interest ({last})"
            )
        return self
```

**Keep:**
- `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` unchanged.
- Existing field types (`loan`, `monthly_pi`, `total_interest`, `payments`) unchanged — Phase 1 frozen surface.
- Existing field order preserved; insert `final_payment_adjusted` BEFORE `payments` so the JSON header reads `loan, monthly_pi, total_interest, final_payment_adjusted, payments` (summary fields first, payment array last).

**Anti-patterns to avoid:**
- ❌ Removing or renaming any Phase 1 field — frozen surface.
- ❌ `final_payment_adjusted: bool` (no default) — would break `tests/test_models.py::test_schedule_aggregates_loan_and_payments` and any other Phase 1 caller. Default `False` keeps backwards compatibility.
- ❌ `cumulative_interest: Money` without default — same: would break Phase 1 `test_payment_constructs_with_phase_3_shape` (lines 119-133 of test_models.py).
- ❌ Putting the validator on `Payment` instead of `Schedule` — D-15 is a Schedule-level invariant.
- ❌ Skipping the `if not self.payments: return self` guard — empty Schedule construction would raise unnecessarily.

---

### `tests/test_models.py` (unit-test, in-place additive)

**Analog:** self — extend with two assertions on new `Payment` fields; UPDATE one existing test (`test_schedule_aggregates_loan_and_payments` lines 136-157) to satisfy the new D-15 validator.

**The test that must be UPDATED** — `tests/test_models.py` lines 136-157:

```python
# tests/test_models.py:136-157 (CURRENT — will fail after D-15 validator added)
def test_schedule_aggregates_loan_and_payments() -> None:
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
    )
    sched = Schedule(
        loan=loan,
        monthly_pi=Decimal("2528.27"),
        total_interest=Decimal("510178.27"),  # ← will mismatch payments[-1].cumulative_interest=0.00
        payments=[p],
    )
    assert sched.loan.principal == Decimal("400000.00")
    assert len(sched.payments) == 1
```

**Update to satisfy D-15 (per RESEARCH §6 Open Question + Recommendation Option 1):**

```python
def test_schedule_aggregates_loan_and_payments() -> None:
    loan = Loan(
        principal=Decimal("400000.00"),
        annual_rate=Decimal("0.065000"),
        term_months=360,
    )
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
        cumulative_interest=Decimal("2166.67"),    # NEW — must match Schedule.total_interest below
        cumulative_principal=Decimal("361.60"),
    )
    sched = Schedule(
        loan=loan,
        monthly_pi=Decimal("2528.27"),
        total_interest=Decimal("2166.67"),         # CHANGED — was 510178.27; now matches p.cumulative_interest
        payments=[p],
    )
    assert sched.loan.principal == Decimal("400000.00")
    assert len(sched.payments) == 1
```

**Keep:** every other test in the file (lines 25-134, 160-163) untouched — they don't construct Schedule with mismatched totals, and `Payment` defaults for the new fields keep them green.

**ADD new test (D-14 verification)** — analog: `test_payment_constructs_with_phase_3_shape` lines 119-133:

```python
def test_payment_carries_cumulative_totals() -> None:
    """D-14: Payment now exposes cumulative_interest + cumulative_principal."""
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
        cumulative_interest=Decimal("2166.67"),
        cumulative_principal=Decimal("361.60"),
    )
    assert p.cumulative_interest == Decimal("2166.67")
    assert p.cumulative_principal == Decimal("361.60")


def test_payment_cumulative_totals_default_to_zero() -> None:
    """D-14: backwards-compat — defaults keep Phase 1 callers green."""
    p = Payment(
        period=1,
        payment_date=date(2026, 5, 1),
        payment=Decimal("2528.27"),
        principal=Decimal("361.60"),
        interest=Decimal("2166.67"),
        balance=Decimal("399638.40"),
    )
    assert p.cumulative_interest == Decimal("0.00")
    assert p.cumulative_principal == Decimal("0.00")
```

**Anti-patterns to avoid:**
- ❌ Removing or renaming any existing test — frozen test surface (CONTEXT.md line 116).
- ❌ Changing the `# Hand:` comment style — Phase 1 idiom.
- ❌ Asserting cumulative_interest using `pytest.approx` or `assertAlmostEqual` — exact `==` only.

---

### `tests/conftest.py` (unit-test fixture factory, additive)

**Analog:** self — extend the existing file with one new `pytest.fixture` factory (`amortize_fixture`) that mirrors the existing `golden_fixture` shape.

**Existing pattern to copy** — `tests/conftest.py` lines 22-35:

```python
# tests/conftest.py:22-35
@pytest.fixture
def golden_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single named fixture by `id` from
    tests/fixtures/golden_pmt.json. Raises KeyError if the id is not present."""

    def _load(fixture_id: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "golden_pmt.json"
        data = json.loads(path.read_text())
        for fx in data["fixtures"]:
            if fx["id"] == fixture_id:
                return fx  # type: ignore[no-any-return]
        raise KeyError(f"fixture id not found in golden_pmt.json: {fixture_id}")

    return _load
```

**Adapt — `amortize_fixture` loader (per RESEARCH §9 + VALIDATION.md Wave 0):**

```python
@pytest.fixture
def amortize_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single amortize fixture by filename stem
    from tests/fixtures/amortize/. Raises FileNotFoundError if the stem doesn't exist."""

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "amortize" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load
```

**Keep:**
- `FIXTURE_DIR` constant (already imported at top of conftest.py via line 19).
- `Callable[[str], dict[str, Any]]` return type.
- `# type: ignore[no-any-return]` comment (Phase 1 idiom, line 32).
- `from __future__ import annotations` (already present line 8).

**Adapt:**
- Phase 3 fixtures are *one fixture per file* (not the wrapped array `{"fixtures": [...]}` of `golden_pmt.json`), so the loader returns `json.loads(path.read_text())` directly — no array-search loop.
- Loader takes a *filename stem* (e.g. `"biweekly_true_200k_6_5"`) not a fixture id, since each file is a single fixture.

**Anti-patterns to avoid:**
- ❌ Replicating `FIXTURE_DIR` (already exists at line 19; reuse).
- ❌ Adding a new `# type: ignore` style different from the existing one.
- ❌ Catching `FileNotFoundError` and re-raising as `KeyError` — let `FileNotFoundError` propagate so the planner test suite gets a clear file-not-found message (different from `golden_fixture`'s `KeyError` because the failure modes are different: "stem typo" vs "id typo within array").
- ❌ Adding `@pytest.fixture(scope="session")` — keep default function scope; matches `golden_fixture`.

---

### `pyproject.toml` (dev-tooling-config, no edit)

**Analog:** self — verify only.

**Already configured** — `pyproject.toml` lines 6-11 + 58-60:

```toml
# pyproject.toml:6-11
dependencies = [
    "pydantic>=2.13.3",
    "python-dateutil>=2.9.0",
    "numpy-financial==1.0.0",
    "pyyaml>=6.0.2",
]
```

```toml
# pyproject.toml:58-60
[[tool.mypy.overrides]]
module = "numpy_financial"
ignore_missing_imports = true
```

**Keep:**
- `numpy-financial==1.0.0` already pinned (verified end-to-end Decimal support per RESEARCH §2 empirical session).
- `dateutil.*` mypy override already present (lines 66-68).
- Ruff `src = ["lib", "tests", "scripts"]` already covers the new `scripts/amortize.py`.
- pytest `testpaths = ["tests"]` already discovers `tests/test_amortize.py`.

**No edit needed for Phase 3** unless the planner adds an optional dev dep. RESEARCH §8 explicitly recommends NOT adding `freezegun` (use `monkeypatch` for the single date-synthesis test).

**Anti-patterns to avoid:**
- ❌ Adding `numpy-financial>=1.0.0` (loosening pin) — STACK.md verdict matrix specifically pins `==1.0.0` because newer versions may regress Decimal support.
- ❌ Adding `freezegun` to dev deps — see RESEARCH §8 + Open Question; use `monkeypatch` instead.
- ❌ Adding `hypothesis` for property-based AMRT-07 — RESEARCH Open Question #5 defers to Phase 8.
- ❌ Touching `[tool.ruff.lint] select` — Phase 3 doesn't need new rules per CONTEXT.md "Claude's Discretion" line 83.

---

## Shared Patterns

### Decimal-from-Strings Discipline (apply to ALL Phase 3 files)
**Source:** `lib/money.py` (lines 29-36) + `tests/test_money.py` (lines 19-46) + CLAUDE.md "Money discipline (non-negotiable)"
**Apply to:** `lib/amortize.py`, `tests/test_amortize.py`, all JSON fixtures, `lib/models.py` updates.

```python
# lib/money.py:29-36 (canonical)
def to_money(value: str) -> Decimal:
    """Construct a money Decimal from a string.

    Floats are rejected at the type level by mypy --strict; runtime callers passing
    a non-str will see a TypeError from Decimal's constructor (we don't catch it —
    failing loud is the contract).
    """
    return Decimal(value)
```

**Rule:** `Decimal("0.065")` always; never `Decimal(0.065)` (float). Strings in JSON; Decimal-from-string in tests; `quantize_cents` end-of-period only.

---

### Pydantic v2 strict + frozen + extra=forbid (apply to ALL new Pydantic models in Phase 3)
**Source:** `lib/models.py` (lines 39, 51, 65 — three occurrences in Phase 1)
**Apply to:** `ExtraPrincipalEntry`, `AmortizeRequest` in `lib/amortize.py`; existing `Loan`/`Payment`/`Schedule` in `lib/models.py` (already comply, keep unchanged).

```python
# lib/models.py:39 (canonical, repeated 3x in Phase 1)
model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
```

**Rule:** every domain model in this project uses this exact `model_config` line. No exceptions. `strict=True` rejects floats; `frozen=True` makes models immutable post-construction; `extra="forbid"` catches typos in JSON inputs.

---

### `from __future__ import annotations` Header (apply to ALL Python files)
**Source:** `lib/money.py:15`, `lib/models.py:14`, `tests/test_money.py:12`, `tests/conftest.py:8`, `scripts/hooks/block-user-layer.py:13` — every existing Python file in the tree.
**Apply to:** `lib/amortize.py`, `scripts/amortize.py`, `tests/test_amortize.py`. Existing files already comply.

```python
"""Module docstring..."""

from __future__ import annotations

# ... rest of imports
```

**Rule:** mandatory project convention; mypy --strict + ruff TCH rule depend on it.

---

### Hand-Calculation Comment Idiom (apply to ALL test assertions)
**Source:** `tests/test_money.py` (every test function has a `# Hand:` comment with the calculation derivation, lines 19-46)
**Apply to:** every test in `tests/test_amortize.py`.

```python
# tests/test_money.py:30-34 (canonical)
def test_quantize_cents_uses_round_half_up_at_0p005() -> None:
    # Hand: ROUND_HALF_UP(0.005, 2) == 0.01.
    # ROUND_HALF_EVEN (Python's default; banker's rounding) would return 0.00.
    # This is the load-bearing assertion for FND-01: prove we are NOT using banker's.
    assert quantize_cents(Decimal("0.005")) == Decimal("0.01")
```

**Rule:** every assertion includes a hand-derivation comment showing where the expected value came from. Trust-but-verify — anyone reading the test should be able to reproduce the math without running the code. CLAUDE.md "Testing" section reinforces.

---

### Pydantic ValidationError Test Pattern (apply to all Phase 3 schema-violation tests)
**Source:** `tests/test_models.py` (lines 37-71 — six different ValidationError tests in Phase 1)
**Apply to:** D-02 violation (biweekly_mode + monthly), D-15 invariant test, CLI float-rejection test, ExtraPrincipalEntry zero-amount test.

```python
# tests/test_models.py:37-44 (canonical)
with pytest.raises(ValidationError) as exc:
    Loan(principal=400000.0, annual_rate=Decimal("0.065000"), term_months=360)  # type: ignore[arg-type]
assert "decimal_type" in str(exc.value) or "Input should be" in str(exc.value)
```

**Rule:**
- `with pytest.raises(ValidationError) as exc:` (always capture, never bare).
- Substring match on `str(exc.value)` — Pydantic error messages can shift; substring assertion is resilient.
- `# type: ignore[arg-type]` for runtime tests of mypy-rejected calls.

---

### Loud-Failure / No-Silent-Defaults (apply to all Phase 3 engine paths)
**Source:** `lib/rules/_loader.py` lines 71-86 (loader raises `MissingReferenceFieldError` instead of returning a None default); `lib/rules/loan_type.py` lines 55-63 (`MissingCountyDataError` instead of silent baseline fallback); CLAUDE.md "Calc engine separation" reinforces "Claude never owns numbers" implies engine never silently defaults numbers.
**Apply to:** `build_schedule` (raise on D-02 violation, raise on negative `period_rate`, raise on `term_months <= 0` post-Loan-validation paranoia); `AmortizeRequest._biweekly_mode_consistency` validator.

```python
# lib/rules/_loader.py:71-74 (canonical loud-fail idiom)
if "source" not in raw:
    raise MissingReferenceFieldError(f"{name}.yml missing required `source:` field")
if "effective" not in raw:
    raise MissingReferenceFieldError(f"{name}.yml missing required `effective:` field")
```

**Rule:** any "this shouldn't happen" branch raises `ValueError` or a domain-specific exception. Never return `None` or `Decimal("0.00")` as a "safe default" for a computed Money field — silent zeros propagate and corrupt downstream sums.

**Exception:** D-08 silent cap of extra-principal at remaining balance is a *documented* exception — surfaced via `final_payment_adjusted=True`. The "silent" word in CONTEXT.md line 51 is *intentional* and per-decision-locked; do NOT extend silent behavior to other paths.

---

### Import-by-Path for Non-Importable Scripts (Phase 3 likely doesn't need this, but reference)
**Source:** `tests/test_block_user_layer.py` lines 22-33 (uses `importlib.util.spec_from_file_location` because the script's filename has a hyphen, not a dot-importable name).
**Apply to:** Phase 3 does NOT need this — `scripts/amortize.py` has an importable module name (`scripts.amortize`); use `subprocess.run([sys.executable, str(SCRIPT_PATH), ...])` for round-trip CLI tests, OR direct `from scripts.amortize import main` for in-process tests if the planner prefers (then patch `sys.argv`).

**Reference only:** if Phase 3 plans grow a need to import a hyphen-named script, this is the idiom.

---

## No Analog Found

(None — every Phase 3 file has a strong analog in Phase 1 or Phase 2 codebase.)

The CLI script (`scripts/amortize.py`) is the *weakest* match because the only existing `scripts/*.py` is a pre-commit hook (`scripts/hooks/block-user-layer.py`), not a Pydantic-boundary CLI. The hook supplies the shebang/main-entrypoint/exit-code shape; the argparse + lazy-import + `model_validate_json` body has no in-tree precedent and must follow RESEARCH §7's recommended skeleton (which is itself anchored in CONTEXT.md D-17/D-18/D-19 + ARCHITECTURE.md "Pattern 1: Claude/Python Calc Split").

---

## Metadata

**Analog search scope:**
- `lib/` (full directory: `money.py`, `models.py`, `rules/*.py`)
- `tests/` (full directory: `conftest.py`, `test_money.py`, `test_models.py`, `test_fixtures.py`, `test_block_user_layer.py`, `test_smoke.py`)
- `tests/fixtures/` (full directory: `golden_pmt.json` + `rules/*.yml`)
- `scripts/` (full directory: `hooks/block-user-layer.py`)
- `pyproject.toml`

**Files scanned:** 12 (read fully) + 14 file listings.
**Pattern extraction date:** 2026-04-29
**Confidence:** HIGH — every analog cited exists in the tree at the line numbers given; every "Apply to" target is named in CONTEXT.md `code_context` or RESEARCH §10 Wave 0 Gaps. No speculation about future Phase 4+ files.

---

## PATTERN MAPPING COMPLETE
